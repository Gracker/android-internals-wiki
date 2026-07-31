---
title: "Perfetto pprof 与 Simpleperf 原生可视化分析"
chapter: "13.21"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [Perfetto, pprof, Simpleperf, CPU Profiling, Flamegraph]
related_chapters: ["13.12", "13.14", "14.24"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "研究素材"
confidence: medium
---

# 13.21 Perfetto pprof 与 Simpleperf 原生可视化分析

<!-- outline-start -->
## 要点

### 🔹 pprof 原生可视化（Perfetto v53+）
- Perfetto UI 直接导入和可视化 pprof profile 数据，无需第三方工具转换
- 支持在同一 Trace 中同时分析 system trace 和 CPU profiling 数据
- 专用 pprof 分析页面

### 🔹 Simpleperf protobuf 格式导入
- Perfetto 支持 Simpleperf 的 protobuf 格式直接导入
- 命名空间与符号解析流程
- 与 simpleperf report 命令行工具的对比

### 🔹 TrackEvent Callstack 与 Flamegraph 聚合
- 转换 trace 时可为事件附加 callstack
- 选择区域后自动聚合为 flamegraph
- inline functions 可视化区分：识别编译器优化对性能的影响

### 🔹 Custom Sorting（process_sort_index / thread_sort_index）
- 通过 JSON 字段控制 track 排列顺序
- 解决社区长期请求的 track 排序问题（issues #378, #555, #764）
- 对大型 trace 可读性的显著提升

### 🔹 Perfetto Rust SDK（初始版本）
- contrib/ 目录下第一个社区维护项目
- crates.io 发布（perfetto-sdk）
- 由 Rivos 工程师贡献，适用于非 Android 平台

### 🔹 Lock-free Task Runner
- 非 Android 平台启用的无锁任务运行器
- 减少锁竞争开销，对高吞吐量数据源有性能提升

## 扩展

### 🔸 pprof + system trace 混合分析工作流
- 在同一时间轴上关联 CPU profile 与系统事件
- 典型场景：启动耗时分析中的 CPU 热点 + Binder 调用关联

### 🔸 Perfetto 版本演进路线（v53 → v57）
- 版本特性矩阵
- Android 17 内置的 Perfetto 版本与 UI 版本的对应关系

<!-- outline-end -->

平台锚点采用 Android 17 / API 37 / `android-17.0.0_r1`。Perfetto 能力分别核对 v53.0 首发状态、Android 17 平台快照和 v57.2 分析端行为。涉及 perf event、采样权限和调用栈采集的内核行为时，内核锚点是 `android17-6.18-2026-06_r6`。这些能力属于 Perfetto 导入器、Trace Processor 和 Web UI 的演进，并不是从某个 Android API 级别开始提供的应用 API。分析端可以使用比设备内置版本更新的 Perfetto UI 或 `trace_processor_shell`，所以还要把“采集端版本”和“打开 trace 的工具版本”分开记录。

§13.12 已经介绍 CPU profile、火焰图和符号化的完整操作路径。容易混淆的边界有四组：

- pprof、Simpleperf protobuf 与 Perfetto `linux.perf` 各自保存了什么数据；
- 哪类 profile 能与调度、Binder、FrameTimeline 在同一时间轴上关联；
- v53 的 callstack、JSON 排序、Rust SDK 与 Lock-free Task Runner 改动影响了哪一层；
- Android 17 固定源码与较新的 Perfetto UI 应如何配对。

## 1. v53 这组改动分别落在哪一层

[Perfetto v53.0 发布说明](https://github.com/google/perfetto/releases/tag/v53.0)把六项容易被写在一起的能力放进了同一个版本。它们的作用域并不相同：

| 能力 | 所在层 | 解决的问题 | 不负责的事情 |
|---|---|---|---|
| pprof 原生导入 | Trace Processor + 专用 UI | 读取 `profile.proto`，按指标生成聚合调用栈 | 不会凭空补出调度、Binder 或帧时间线 |
| Simpleperf protobuf 导入 | Trace Processor + UI | 读取 `report-sample --protobuf` 结果、样本时间戳和调用栈 | v57.2 仍不生成 context-switch 调度片段，也不公开样本的事件类型、事件计数和丢样记录 |
| TrackEvent callstack | trace 转换协议 + UI | 给带时间戳事件附加调用栈，按选区聚合火焰图 | 不等同于周期性 CPU sampling |
| `process_sort_index` / `thread_sort_index` | Chrome JSON 导入器 | 给进程、线程 track 提供初始排序提示 | 不作用于原生 Perfetto protobuf |
| Rust SDK 初始版本 | `contrib/rust-sdk` | 让 Rust 程序接入 Perfetto tracing | 不是 Android Framework SDK，也不替代 `androidx.tracing` |
| Lock-free Task Runner | Perfetto 基础设施 | 降低非 Android 平台即时任务投递时的锁竞争 | 不是所有 Task Runner 操作都无锁，也不是应用侧性能开关 |

这里的“原生导入”表示 Perfetto 可以直接解析相应文件格式。它不表示采样数据自动获得 system trace 的全部上下文。

## 2. 三种 CPU profile 的数据模型

选择工具前，先确认分析是否依赖时间轴：

| 输入 | 样本形态 | 时间信息 | 进程/线程信息 | 与 system trace 同轴分析 |
|---|---|---|---|---|
| pprof `profile.proto` | 按调用栈和指标聚合 | 通常没有逐样本时间戳 | 取决于生产者，标准模型不以 Android 线程时间线为中心 | 单独导入时不能；需要额外采集或合并 |
| Simpleperf protobuf | 离散 CPU 样本 | 有样本时间戳 | 有进程、线程及调用栈 | 可观察样本分布；仍需另一份 system trace 提供可靠的调度上下文 |
| Perfetto `linux.perf` | system trace 内的离散 CPU 样本 | 与 trace 使用同一时钟域 | 通过 `utid` / `upid` 接入 Trace Processor 数据模型 | 可以直接与 `sched`、Binder、FrameTimeline 等轨道关联 |

pprof 的火焰图宽度是某个 sample type 的累计值，例如 CPU 纳秒数、allocation 次数或字节数。宽度不是该函数在 Android 时间轴上连续运行了多长时间。一个 profile 还可以携带多个 sample type；Perfetto 的 pprof 页面允许切换指标，分析时应把指标名称和单位写进结论。

Simpleperf protobuf 保留单个样本的时间戳。Android 17 的格式注释把它定义为纳秒级 monotonic clock，旧于 4.1 的内核才可能使用 perf clock；Perfetto v57.2 导入器按 `CLOCK_MONOTONIC` 转为 trace time。样本写入公开表 `cpu_profile_stack_sample`，调用栈则经 `stack_profile_callsite`、`stack_profile_frame` 和 `stack_profile_mapping` 关联。

这条导入路径还有几处容易漏掉的限制。v57.2 只在样本带有可用 `callchain` 时插入 `cpu_profile_stack_sample`；它会读取 `event_type` 列表，却没有把每个样本的 `event_type_id`、`event_count` 暴露到该表，也没有处理丢样记录。context-switch 记录参与时间排序，但解析器随后直接返回，不会生成 `sched_slice`。Simpleperf 样本间的空白不能解释成线程被抢占、休眠或阻塞；同一文件混录多种 perf event 时，也不能用这张表按事件类型拆分热点。

`linux.perf` 数据源把 perf event 样本写进原生 Perfetto trace。在 Android 15 及以上版本上，它适合“某段主线程为何变慢”“CPU 热点是否和 Binder 等待重叠”这类需要统一时钟的问题。`user` 构建通常只允许 profileable 或 debuggable 应用被采样；`userdebug` / `eng` 构建的限制较少。采样频率会影响设备负载，官方文档建议非 native 场景按每个 CPU 低于 200 Hz 控制，命令示例使用 100 Hz。

## 3. pprof 页面能告诉你什么

将 pprof 文件拖入 Perfetto UI 后，UI 会识别 `profile.proto`，进入专用 profile 页面。解析器会读取：

- mapping 的地址范围、文件名和 build ID；
- function、文件名与源码行；
- location 与 line 关系；
- 每个 sample type 对应的单位和值；
- sample 到调用栈的引用。

同一个 machine instruction location 可以包含多条 line 记录，这通常来自编译器内联。Perfetto 会保留这些 inline frame，并在火焰图中使用不同样式标识。阅读时应把内层 inline frame 理解为编译器展开后的逻辑调用关系，不能当作一次独立的运行时函数调用。

pprof 适合以下任务：

- 比较优化前后 CPU 或 allocation 聚合分布；
- 检查热点是否集中到某条调用链；
- 验证符号、build ID 和 inline frame 是否被正确恢复；
- 查看 Go、C++ 或其他工具输出的标准 pprof profile。

若目标是解释一次 Android 启动中的时间空洞，只打开 pprof 不够。该问题需要带时间戳的 CPU 样本和 system trace。可以改用 `linux.perf` 采集，或分别采集 profile 与 trace 后，在确认时钟可对齐的前提下合并。缺少时钟映射时，只能做统计对照，不能声称两类事件发生在同一时刻。

## 4. Simpleperf protobuf 导入流程

下面的命令用于采集一个 debuggable 或 profileable 应用，并输出 Perfetto 能直接读取的 Simpleperf protobuf。`app_profiler.py` 应取自 Android 17 Simpleperf 工具集，录制端二进制和符号文件还要与目标设备 ABI、build ID 匹配：

```bash
python3 system/extras/simpleperf/scripts/app_profiler.py \
  --app com.example.app \
  -r "-e task-clock:u -f 100 -g --duration 10" \
  -o perf.data

simpleperf report-sample \
  --protobuf \
  --show-callchain \
  --symdir binary_cache \
  -i perf.data \
  -o simpleperf.proto
```

`-g` 让录制阶段保存 callchain；`--show-callchain` 让 `report-sample` 把 callchain 写入 protobuf。两者缺少任意一个，Perfetto 里的栈深度都可能只剩叶函数。`--symdir binary_cache` 指向拉取并整理过的 ELF 文件；Java/Kotlin 混淆符号还可以按工具版本补充 `--proguard-mapping-file`。生成的 `simpleperf.proto` 可以直接拖入 Perfetto UI。

示例使用单一 `task-clock:u` 事件和每秒 100 次采样。100 Hz 来自 Perfetto CPU profiling 文档的示例，也低于该文档为非 native 调用栈建议的每 CPU 200 Hz 上限；10 秒只是演示窗口，应按复现时长调整，并在目标设备上核对采样丢失与附加负载。

固定源码 `android-17.0.0_r1` 中，`cmd_report_sample.cpp` 为 protobuf 写入 `SIMPLEPERF` magic 和格式版本 1，并实现了上述参数。这个格式版本是 Simpleperf 文件协议版本，和 Android API 37、Perfetto v53 都不是同一套版本号。需要比较多个 perf event 时，建议每个文件只录一种事件，或回到 `simpleperf report` 读取事件和权重；v57.2 的公开采样表不能完成这项拆分。

导入后，可以用下面的 SQL 检查各 PID/TID 成功导入了多少条调用栈样本。该查询不依赖可能缺失的进程名，也不计算函数热点：

```sql
SELECT
  p.pid,
  p.name AS process_name,
  t.tid,
  t.name AS thread_name,
  COUNT(*) AS sample_count,
  MIN(s.ts) / 1e9 AS first_sample_s,
  MAX(s.ts) / 1e9 AS last_sample_s
FROM cpu_profile_stack_sample AS s
JOIN thread AS t USING (utid)
LEFT JOIN process AS p USING (upid)
GROUP BY p.pid, p.name, t.tid, t.name
ORDER BY sample_count DESC, p.pid, t.tid;
```

Simpleperf v57.2 导入器会用 Thread record 更新 PID、TID 和线程名，却没有用 `MetaInfo.app_package_name` 设置 `process.name`，因此纯 Simpleperf protobuf 的 `process_name` 可能为 `NULL`。用录制时保存的目标 PID/TID 识别进程和线程，不能把包名过滤作为前提。这里的 `sample_count` 只统计带可用 `callchain` 并进入公开表的样本；数值很低时，火焰图宽度容易受采样随机性影响。`first_sample_s` 与 `last_sample_s` 可以暴露采集窗口过短、目标进程启动过晚等问题。函数聚合优先使用 Perfetto 的 profile/flamegraph 视图或公开的标准库模块，不要依赖以 `__intrinsic_` 开头的内部表，它们不承诺查询兼容性。

### 4.1 与 `simpleperf report` 的分工

| 工具 | 强项 | 适合的检查 |
|---|---|---|
| `simpleperf report` | 终端内快速聚合、按 DSO/符号排序、脚本化输出 | 采集是否成功、热点排名、CI 对比 |
| `simpleperf report-sample --protobuf` + Perfetto | 时间分布、线程筛选、调用栈交互、与其他可导入数据联合查看 | 某个时间区间的样本和栈形态 |
| `simpleperf annotate` | 反汇编/源码行级热点 | 指令、源码行和编译优化 |

Perfetto 导入没有淘汰 Simpleperf 命令行工具。命令行适合稳定、可复现的批处理；UI 适合探索时间区间和调用关系。严谨的性能记录通常会保留 `perf.data`、符号目录、生成的 protobuf、命令行参数和 Perfetto 版本。

## 5. system trace 与 CPU profile 的联合分析

“同一 Trace 中分析 system trace 和 CPU profiling”有三种含义，证据强度不同：

1. **原生同轴采集**：使用 Perfetto `linux.perf` 与 `linux.ftrace`、FrameTimeline、TrackEvent 等数据源一起录制。它们共享 trace 时钟，是 Android 15—17 上优先采用的路径。
2. **带 callstack 的 TrackEvent**：转换外部带时间戳事件时，为事件附加 callstack。选中时间区域后，UI 可以把这些栈聚合成火焰图。它表达“这些事件携带了哪些栈”，不表达固定频率 CPU 占用。
3. **文件合并或并排对照**：pprof、Simpleperf profile 与 system trace 来自不同采集器。只有确认 clock snapshot、启动时刻或其他可靠映射后，才能把它们放到同一时间坐标。缺少映射时，应分别报告统计热点和系统时序。

启动分析可以按下面的证据链展开：

- 用 FrameTimeline 或应用 TrackEvent 定位慢启动区间；
- 用 `sched_slice` 判断主线程处于 Running、Runnable 还是 Sleeping；
- 用 `linux.perf` 样本检查 Running 区间内的 native/Java 热点；
- 用 Binder 轨道确认 Sleeping 是否对应同步事务；
- 返回源码验证热点函数的版本、调用入口和线程约束。

火焰图只能说明采样命中的栈分布。没有 `sched` 证据时，不要把样本稀少解释为“线程在等待 Binder”；没有符号与 build ID 对齐时，也不要把 `[unknown]` 归因到某个库。

## 6. TrackEvent callstack 与区域火焰图

Perfetto v53 扩展了外部 trace 转换路径：转换器可以给 TrackEvent 事件附加 callstack，UI 对时间区域内的事件栈做聚合。这个设计适合编译器事件、任务调度器事件或自研 runtime 事件，因为生产者已经知道每个事件的时间戳和栈。

分析时要区分三类宽度：

- **事件计数**：某个调用栈出现了多少次；
- **事件持续时间**：带 duration 的事件在选区内累计多长；
- **profile sample value**：CPU 时间、allocation 次数或字节等 profile 指标。

三者都能画成火焰图，数值含义却不相同。截图或评审结论应同时记录数据源、聚合指标、选区和单位。

inline function 的可视化解决了另一个常见误读。若 `foo()` 被内联进 `bar()`，profile 可能同时显示逻辑上的 `foo` frame 与物理上承载指令的 `bar` frame。这是在保留 DWARF inline 信息，不代表运行时又执行了一次普通的 `call foo`。判断优化效果还应结合反汇编、源码行和编译参数。

## 7. 用 JSON metadata 固定 track 初始顺序

`process_sort_index` 和 `thread_sort_index` 只属于 Chrome JSON Trace Event 导入格式。下面的最小文件把 Renderer 进程和 MainThread 线程放到较靠前的位置：

```json
{
  "traceEvents": [
    {
      "name": "process_name",
      "ph": "M",
      "pid": 100,
      "tid": 0,
      "args": {"name": "Renderer"}
    },
    {
      "name": "process_sort_index",
      "ph": "M",
      "pid": 100,
      "tid": 0,
      "args": {"sort_index": -20}
    },
    {
      "name": "thread_name",
      "ph": "M",
      "pid": 100,
      "tid": 101,
      "args": {"name": "MainThread"}
    },
    {
      "name": "thread_sort_index",
      "ph": "M",
      "pid": 100,
      "tid": 101,
      "args": {"sort_index": -10}
    }
  ]
}
```

`ph: "M"` 表示 metadata event。进程排序事件按 `pid` 生效，线程排序事件按 `pid` + `tid` 生效，`args.sort_index` 接受数值并在解析时转成整数。较小的 index 通常排在前面；相同 index 的最终顺序还会受 UI 默认规则影响。用户在 UI 中手动调整 track 后，界面状态也可能覆盖导入时的初始顺序。

这两个字段不应写入原生 Perfetto protobuf，也不能通过 Trace Processor SQL 改写已导入 trace 的物理 track 顺序。对大型自研 JSON trace，建议把编号策略固化在转换器里，例如按“关键进程、关键线程、工作线程、后台线程”分段留出 index 区间。

## 8. Perfetto Rust SDK 的边界

v53 在 `contrib/rust-sdk` 中加入第一个社区维护的 Rust SDK，并以 `perfetto-sdk` 发布到 crates.io。初始实现由 Rivos 工程师贡献。到 v57.2 源码时，`perfetto-sdk` crate 已经演进到 1.0.2，支持 Track Event、自定义 DataSource 和 TracingSession 等接口。Android 17 固定源码位于两者之间，crate 版本是 0.3.0。

| 版本点 | `perfetto-sdk` crate | 能力与维护边界 |
|---|---:|---|
| Perfetto v53.0 | 0.1.2 | 初始社区维护版本，位于 `contrib/rust-sdk` |
| `android-17.0.0_r1` | 0.3.0 | Android 17 平台快照中的源码状态 |
| Perfetto v57.2 | 1.0.2 | 提供 Track Event、DataSource、TracingSession；仍属 `contrib` 项目 |

它面向使用 Rust 的原生程序和非 Android 平台集成。Android 应用的 Java/Kotlin 业务埋点仍应优先使用平台 tracing API 或 `androidx.tracing`；Android 系统组件若要引入 Rust SDK，还要核对构建系统、NDK/平台链接、ABI 和产品允许的依赖，不能因 crates.io 上存在包就直接加入平台模块。

版本号也要固定在工程依赖和分析报告里。`contrib` 项目演进速度可以与 Android 固定平台分支不同，主线 v57.2 的 crate 状态不能反推到 `android-17.0.0_r1`。

## 9. Lock-free Task Runner 改了什么

v53 在非 Android 平台启用了 `LockFreeTaskRunner`。其即时任务队列采用多生产者、单消费者模型，用 slab 和位图协调任务发布，降低多个 tracing producer 同时投递任务时的互斥锁竞争。设计文档中的微基准显示了明显收益，但微基准结果不能换算成应用帧率或端到端 tracing 开销。

“Lock-free”还有明确边界：

- 优化重点是即时任务投递热路径；
- delayed task 和文件描述符 watch 仍需要切回 runner 线程处理；
- 队列容量扩展、`std::function` 捕获对象等路径仍可能发生内存分配；
- 单消费者线程仍负责按序执行任务，耗时回调照样会阻塞后续任务；
- v53 发布说明明确写的是非 Android 平台启用，不能据此宣称 Android 17 默认走该实现。

Android 17 固定源码中，`MaybeLockFreeTaskRunner` 通过 `PERFETTO_FLAGS(USE_LOCKFREE_TASKRUNNER)` 在 `LockFreeTaskRunner` 与 `UnixTaskRunner` 之间选择；Android 构建的值来自 aconfig，其他构建使用编译期开关。`use_lockfree_taskrunner` 是 fixed read-only flag，不是应用可在运行时切换的性能选项。产品构建值、运行平台和对应分支实现共同决定实际路径。排查 tracing service 自身开销时，应核对当前二进制的构建 flag 与源码版本，再结合 trace 证据判断。

## 10. Android 17 与 Perfetto UI 的版本关系

Android 平台 tag、Perfetto 上游 release 和浏览器中的 UI 可以处于不同版本。版本关系如下：

| 版本点 | 能力与用途 | 与 Android 17 的关系 |
|---|---|---|
| Perfetto v53.0 | 发布说明中的六项能力首次成组发布 | Android 17 固定源码已包含这些上游能力 |
| Perfetto v54.0 | 增加 collapsed stack、Firefox JSON、R8 retracing、`traceconv profile` 自动识别等 | `android-17.0.0_r1` 的 changelog 已到 v54，并含后续 AOSP 改动 |
| `android-17.0.0_r1` | Android 17 / API 37 平台源码锚点 | 属于 v54 时代快照，不能简单标记为纯 v54.0 |
| Perfetto v57.2 | 复核导入器和 Trace Processor 行为时使用的较新分析端 | 可以作为宿主机 UI/CLI；不能写成 Android 17 内置版本 |

Perfetto UI 通常能向后打开旧 trace。团队保存 trace 时，至少记录设备 build fingerprint、Android tag、采集配置、采集端 Perfetto 版本、分析端 UI/Trace Processor 版本。若新 UI 能打开而设备端命令不认识某个 data source，问题在采集端能力；若 trace 已经包含 packet 而旧 UI 不显示，才优先检查分析端版本。

## 11. 常见误判与核查方法

### 11.1 “pprof 已经和 system trace 合并”

核查 trace 是否同时存在 `sched_slice`、Binder、FrameTimeline 和 `cpu_profile_stack_sample`，并确认它们的时钟来源。只看到 pprof 火焰图，不足以证明完成同轴采集。

### 11.2 “火焰图最宽的函数耗时最长”

先读 sample type 和 unit。allocation count、bytes、CPU nanoseconds、事件计数的宽度含义不同；采样 profile 还存在统计误差。

### 11.3 “Simpleperf protobuf 已经包含完整调度信息”

即使 protobuf 生产者写入 context-switch，Perfetto v57.2 导入器也没有把它生成 `sched_slice`。调度状态应由 `linux.ftrace`/`sched` 数据源提供。

### 11.4 “出现 inline frame 就是重复调用”

查看 frame 的 inline 标记、DWARF line 信息和反汇编。inline frame 表达优化后的源码归属，不能按普通调用次数相加。

### 11.5 “用了最新 Perfetto UI，设备就支持最新 data source”

UI 负责解析和展示，设备上的 `traced`、producer 与内核负责采集。运行 `perfetto --query-raw` 或检查数据源描述，再决定配置能否下发。

## 12. 推荐的分析记录

一次可以复核的 profile 分析应留下以下信息：

- 设备 build fingerprint、Android 版本与固定源码 tag；
- 内核版本；涉及 perf event 行为时固定到 `android17-6.18-2026-06_r6`；
- `record` / Perfetto config 的完整参数、采样频率和持续时间；
- pprof sample type 与 unit，或 Simpleperf event 名称；
- 符号目录、build ID、APK/JAR 混淆 mapping；
- 选区起止时间与对应 system trace 事件；
- Perfetto UI 或 `trace_processor_shell` 版本；
- 对照组、重复次数和样本数量。

这些记录可以把“火焰图看起来像热点”收敛成可重复验证的工程结论。

## 参考源码与文档

- [Perfetto v53.0 release notes](https://github.com/google/perfetto/releases/tag/v53.0)
- [Perfetto v54.0 release notes](https://github.com/google/perfetto/releases/tag/v54.0)
- [Perfetto v57.2 release](https://github.com/google/perfetto/releases/tag/v57.2)
- [Perfetto：导入 pprof 与 Simpleperf 等外部格式](https://perfetto.dev/docs/getting-started/other-formats)
- [Perfetto：CPU profiling 数据源](https://perfetto.dev/docs/getting-started/cpu-profiling)
- [Perfetto：转换带时间戳的外部数据](https://perfetto.dev/docs/getting-started/converting)
- [Android 17 Simpleperf `app_profiler.py`](https://android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/scripts/app_profiler.py)
- [Android 17 Simpleperf `cmd_report_sample.cpp`](https://android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/cmd_report_sample.cpp)
- [Android 17 Simpleperf protobuf 协议](https://android.googlesource.com/platform/system/extras/+/android-17.0.0_r1/simpleperf/cmd_report_sample.proto)
- [Android 17 Perfetto changelog](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/CHANGELOG)
- [Android 17 Perfetto `use_lockfree_taskrunner` flag](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/perfetto_flags.aconfig)
- [Perfetto v57.2 pprof reader](https://github.com/google/perfetto/blob/v57.2/src/trace_processor/importers/pprof/pprof_trace_reader.cc)
- [Perfetto v57.2 Simpleperf protobuf parser](https://github.com/google/perfetto/blob/v57.2/src/trace_processor/importers/simpleperf_proto/simpleperf_proto_parser.cc)
- [Perfetto v57.2 JSON metadata parser](https://github.com/google/perfetto/blob/v57.2/src/trace_processor/importers/json/json_trace_parser.cc)
- [Perfetto v57.2 Rust SDK](https://github.com/google/perfetto/tree/v57.2/contrib/rust-sdk)
- [Perfetto Lock-free Task Runner 设计](https://github.com/google/perfetto/blob/v57.2/docs/design-docs/lock-free-task-runner.md)
