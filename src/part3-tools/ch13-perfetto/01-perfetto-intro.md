---
title: Perfetto 简介与演进
chapter: '13.1'
section: '13.1'
status: ready-for-review
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
reviewed_date: "2026-05-28"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
polish_count: 2
polish_date: '2026-04-10'
polish_by: task2b-polish
applicable_versions: Android 9 (API 28) - Android 17 (API 37, Beta)
last_verified: '2026-04-14'
last_verified_against: perfetto.dev docs, source.android.com/docs/core/debug/perfetto,
  developer.android.com/profileable
confidence: high
sources:
- type: official
  path: https://perfetto.dev/docs/
- type: official
  path: https://source.android.com/docs/core/debug/perfetto
- type: blog
  path: https://www.androidperformance.com/2019/12/01/Android-Systrace(Perfetto)-Basic/
tags:
- perfetto
- systrace
- tracing
- trace-processor
- traced
- ftrace
- atrace
- heapprofd
- performance-analysis
related_chapters:
- '13.2'
- '13.3'
- '2.1'
- '7.1'
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task9_result: "needs-rework"
task2b_state: "fixed"
task2b_result: "fixed"
task2b_rework_date: "2026-05-28T06:50:00+08:00"
task9_reviewed_date: "2026-05-25"
task9_reviewed_by: "openclaw-task9"
review_notes: '2026-04-24 task6 re-review (revisiting): pass-light-edit. L1 fix: 2处否定纠正式句型已改为直接陈述；1处口水过渡词已删除。
  评分: 结构5/5·措辞4/5·一致性5/5·验证4/5·元数据5/5。；2026-05-06 task6 re-review: pass-light-edit。L1/L2
  小修 19 处；移动尾部注入块到正文/参考资料；无新增 B 类回炉问题，等待 Task 9 复审。；2026-05-06 04 task6 re-review:
  pass-light-edit。L1/L2 小修 8 处；无新增 B 类回炉问题，等待 Task 9 复审。 | 2026-05-06 05 task9 deep-review:
  pass-tech-review。P0 0 / P1 0 / P2 3。Task6 已通过且 queue 无 pending，自动晋升 finalized。'
last_task9_at: "2026-05-25T08:32:00+08:00"
task9_review_notes: "2026-05-25 Task9 deep-review: needs-rework。P0 1 / P1 1 / P2 0。Trace Processor metric 示例包含不可用的 android_jank；logcat in trace 的 userdebug 边界缺失。2026-05-28 Task2B fallback 已修复 metric 名、android.log userdebug 边界与 Android 10/11 normal mode 配置输入边界，回流 Task6/Task9。"
last_task6_at: "2026-05-28T07:05:00+08:00"
last_task6_audit: '2026-05-24'
task6_reviewed_date: "2026-05-25"
last_task9_review_log: "logs/deep-review/2026-05-25-08-deep-review.md"
last_task9_audit: '2026-05-25'
last_task9_audit_log: 'logs/deep-review/2026-05-25-05-audit.md'
last_task6_review_log: "logs/review/2026-05-28-07-review.md"
task6_review_notes: "2026-05-28 Task6：Task2B 回流后写作复审通过；L1/L2 小修 2 处，压掉否定纠正式句型和限制句式；无 L3/L4 回炉项，送 Task9 复核。"
p0: 1
p1: 1
p2: 0
updated_by: "openclaw-task9"
updated_date: "2026-05-25"
task6_l3_l4_issues: 0
task6_l1_l2_fixes: 2
---

# Perfetto 简介与演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Perfetto 是什么：Google 的下一代系统级 tracing 工具，Systrace 的继任者
- 🔹 Perfetto 与 Systrace 的关系与区别
- 🔹 Perfetto 的架构：traced、traced_probes、heapprofd / traced_perf 等 profiling 组件、Perfetto UI
- 🔹 核心概念：TraceConfig、Data Source、Track、Slice、Counter
- 🔹 为什么性能分析离不开 Perfetto

### 扩展（可选深入）

- 🔸 Perfetto 在 Chrome / Linux 上的跨平台支持
- 🔸 Perfetto SDK 嵌入 App 的能力（Custom Data Sources）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Perfetto

做过 Android 性能优化的人一定遇到过这样的场景：App 明明卡了，但拿到的日志毫无头绪；滑动掉帧了，却不知道时间花在哪里；ANR 堆栈指向的是 Binder 调用，但我们不知道对端进程在做什么。这些问题有一个共同特征，它们跨越了多个进程、多个线程，甚至多个系统层级。单看任何一个进程的日志，都无法拼出完整图景。

Perfetto 就是解决这类问题的工具。它提供的是系统级时间线视角：所有进程的 CPU 调度、所有线程的状态、内核的事件、图形管线的每一帧、内存的变化曲线，全部统一在同一根时间线上。有了这根时间线，我们可以按时间顺序还原系统在任意时间窗口里发生了什么。

如果之前用的是 Systrace，那么 Perfetto 是它的继任者，能力是 Systrace 的严格超集。如果之前没有用过任何系统级 tracing 工具，那么 Perfetto 就是现在应该开始掌握的工具。

## Perfetto 是什么

Perfetto 是 Google 开源的系统级 tracing 平台。它最初服务 Android，后来扩展到 Linux 和 Chrome。在 Android 端，Android 9 已把 `traced` / `traced_probes` 等基础设施放进 system image；Android 9 和 Android 10 的非 Pixel 设备常见还要手动 enable；Android 11 起，大多数设备默认启用，日常系统追踪也基本都转到 Perfetto 体系。[已验证: 官方文档, source.android.com/docs/core/debug/perfetto]

Perfetto 是一整套 tracing 基础设施，包含三个核心模块：

- **采集层**：负责从系统各处收集 trace 数据，包括内核的 ftrace 事件、用户空间的 atrace 标注、/proc 和 /sys 文件的轮询数据、以及 App 自定义的 trace 事件。
- **分析层**：基于 SQL 的 trace 分析引擎（Trace Processor），可以用结构化查询语言对 trace 数据做任意维度的分析。
- **可视化层**：Web 端的 Perfetto UI（ui.perfetto.dev），支持打开数 GB 的大型 trace 文件，完全在浏览器本地运行，无需上传数据。

这三层彼此解耦。我们可以只用采集层把数据抓到文件里，用 Trace Processor 写 SQL 查询；也可以只用 UI 打开别人给的 trace 文件做可视化分析。

## 从 Systrace 到 Perfetto：为什么要换

Systrace 是 Android 4.1（2012 年）引入的 tracing 工具，它基于 Linux 内核的 ftrace 机制和用户空间的 atrace 注解来收集系统事件，最终生成一个可以在 Chrome 中查看的 HTML 报告。在很长一段时间里，Systrace 是 Android 性能分析的标配工具。

但 Systrace 有几个明显限制，在实际工作中经常卡住分析。

**采集时长严重受限。** Systrace 把所有数据先写进内存缓冲区，结束时一次性输出到文件。因此 trace 时长受限于内存大小，通常只能抓 10-30 秒。如果想复现一个需要操作好几分钟才会出现的问题，Systrace 很难覆盖这类场景。

**数据源覆盖面窄。** Systrace 主要依赖 ftrace 和 atrace，覆盖的是 CPU 调度、Binder 调用、图形管线等基础事件。如果想看内存分配细节、Java 堆的使用情况，或者每个硬件子系统的功耗，Systrace 都不支持。

**缺少结构化分析能力。** Systrace 的 HTML 报告是一个"所见即所得"的视图，主要操作是缩放、点选、看信息面板，缺少对数据做聚合、过滤、统计的入口。面对一个包含几百个进程的 trace 文件，只能靠肉眼在时间线上来回滚动，效率很低。

Perfetto 从架构和数据模型两边一起改了这件事。Producer 先把事件写进与 `traced` 共享的 shared memory，`traced` 再把这些数据汇聚到 central trace buffers。默认模式下，trace 仍然主要待在内存里，录制结束后一次性写出；只有显式开启 `write_into_file` / `file_write_period_ms`，才会周期性刷到文件，适合 long trace。它还能接入更多 data source，并把结果直接送进 SQL 分析引擎和 Perfetto UI。

下表总结了二者的关键差异：

| 维度 | Systrace | Perfetto |
|------|---------|---------|
| 引入阶段 | Android 4.1 (2012) | Android 9 服务进 system image，Android 11+ 大多数设备默认启用 |
| 采集模型 | atrace / ftrace 生成 HTML 报告 | shared memory + central buffers，默认内存 buffer，可选 long trace 周期刷盘 |
| 采集时长 | 更适合短时抓取 | 默认仍受 buffer 限制，开启 `write_into_file` 后可延长到磁盘容量 |
| 配置方式 | category + 命令行为主 | simple mode flags 或 normal mode `TraceConfig` |
| 数据源 | ftrace + atrace | ftrace + atrace + heap / log / process stats / power 等 |
| 分析方式 | HTML 报告，交互能力有限 | SQL 查询 + Web UI + 脚本 |
| UI 承载能力 | 大文件更容易卡顿 | 可以处理更大的 trace 文件 |
| 跨平台 | 主要 Android | Android + Linux + Chrome |
| 当前定位 | 兼容旧流程 | Android tracing 主线平台 |

[已验证: 官方文档, perfetto.dev/docs/#systrace-vs-perfetto]

还有一个兼容性细节：Perfetto UI 可以直接打开 Systrace 格式的 trace 文件。之前积累的 Systrace 文件不需要丢弃，全部可以在 Perfetto UI 中继续分析。反过来，Perfetto 也提供了 `traceconv` 工具，可以把 Perfetto 格式的 trace 转换为 Systrace 文本格式。

## Perfetto 的架构

理解 Perfetto 的架构，有助于在遇到问题时知道问题出在哪一层。Producer 先把事件写进与 `traced` 共享的 shared memory，`traced` 再把这些数据汇聚到 central trace buffers；Consumer 负责发起采集、停止采集，并决定结果是录制结束后一次性写出，还是按 long trace 配置周期性刷到文件。

[图：Perfetto 架构示意图，Producer shared memory page → `traced` central buffers → Consumer / 输出文件]

### traced：核心守护进程

`traced` 是 Perfetto 的 tracing service。它负责管理会话、接收 Producer 提交的数据页，再把这些数据归并到 TraceConfig 定义的 central trace buffers。

拆开看，`traced` 主要做两件事：

- **管理采集会话**：接收 Consumer 发来的 TraceConfig，决定开启哪些 data source、buffer 多大、录制多久、结果写到哪里。
- **汇聚与写出数据**：Producer 先把事件写到和 `traced` 共享的 shared memory page。`traced` 收到提交通知后，把这些 page 归并到 central trace buffers，并在会话结束时写成 `.perfetto-trace` 文件，或者按 long trace 配置周期性刷盘。

需要分清三个层次：

1. **Producer shared memory**：每个 Producer 的低开销写入区。
2. **central trace buffers**：`traced` 统一管理的会话 buffer。
3. **输出文件**：默认在录制结束时一次性写出；只有显式设置 `write_into_file: true` 和 `file_write_period_ms`，才会定期刷到磁盘。

所以，默认 Perfetto 不是“边采边写盘”。短 trace 仍然主要依赖内存 buffer；长时录制需要专门的 long trace 配置。抓长时 trace 时，buffer 大小和 `file_write_period_ms` 要一起看。

`traced` 不可用时，依赖 system backend 的 normal mode 不能工作。这时如果只需要受限的 ftrace / atrace 子集，要显式改用 perfetto simple mode，或者回到旧的 systrace 类流程；这不是系统自动回退出来的路径。

Android 9 和 Android 10 的非 Pixel 设备上，Perfetto services 常常还需要手动 enable；Android 11 起，大多数设备默认就会启动 `traced` / `traced_probes`。

### traced_probes：系统数据源代理

`traced_probes` 是另一个系统服务，它负责采集那些需要特权访问的系统级数据源，具体包括 ftrace（内核事件）和 /proc、/sys 文件系统的轮询数据。

为什么不直接让 `traced` 来采集？因为 `traced` 以普通用户权限运行，而读取 ftrace 和某些 /proc、/sys 节点需要 root 或 system 权限。`traced_probes` 以更高的权限运行，专门负责这些特权数据源的采集，采集到的数据通过共享内存传递给 `traced`。

`traced_probes` 支持的主要数据源包括：

- **ftrace**：内核级事件，如 CPU 调度（sched_switch、sched_wakeup）、系统调用、中断等。这是 trace 中 CPU 行为数据的来源。
- **atrace**：用户空间标注事件，Android Framework 和 App 通过 `android.os.Trace` API 写入的事件。
- **/proc 和 /sys 轮询器**：定期采样进程级别的 CPU 使用率、内存使用量、系统级计数器等。
- **功耗计数器**：从 Android 10 开始，集成了电池和能耗相关的硬件计数器，包括总电流和 ODPM（On-Device Power Rails Monitor，各硬件子系统的独立功耗）。

[已验证: 官方文档, perfetto.dev/docs/data-sources]

这些数据源默认处于空闲状态，只有在显式启动一次 trace 采集时才会激活。这和一直开着日志系统不同，Perfetto 不会在不需要的时候产生任何开销。

### heapprofd / java_hprof_producer / traced_perf：专用 profiling 组件

`traced_probes` 负责通用系统数据源，但 Perfetto 的 profiling 能力还有一组独立组件：

- `heapprofd`：负责 Native heap sampling，抓 `malloc` / `free` 相关分配栈，源码位于 `external/perfetto/src/profiling/memory/`。
- `java_hprof_producer`：负责 Java heap dump 和 retained graph 这类对象图数据，也在 `external/perfetto/src/profiling/memory/` 目录下。Java heap dump 的完整触发链是：Consumer 在 TraceConfig 中配置 `android.java_hprof` 数据源（Android 11 引入） → `JavaHprofProducer` 收到启动指令后向目标进程发送 `__SIGRTMIN+6` 信号 → 目标进程内已注册的 ART 插件 `art/perfetto_hprof/perfetto_hprof.cc` 捕获信号，在进程内执行 heap 快照并写回 shared memory。JavaHprofProducer 在发送 `__SIGRTMIN+6` 前会先调用 `CanProfile(...)` 检查目标 App 的 `profileable` / `debuggable` / installer gate 状态；不满足条件时不会向目标进程发信号，而非发送后由内核丢弃。[已验证: external/perfetto/src/profiling/memory/java_hprof_producer.cc SendSignal(), art/perfetto_hprof/perfetto_hprof.cc]
- `traced_perf` / `perf_producer`：负责通过 Linux `perf_event_open` 做 CPU sampling 和调用栈采集，源码位于 `external/perfetto/src/profiling/perf/`。

这些组件仍然通过 `traced` 管理的会话 buffer 汇聚数据，只是各自负责不同的 profiling 路径。后面看到 Native heap、Java heap 或 CPU profiling data source 时，先判断它属于哪类 producer 组件，再决定该查权限、配置还是设备支持。

### Perfetto UI：可视化界面

Perfetto UI 是一个纯前端的 Web 应用，托管在 ui.perfetto.dev，但所有数据都在浏览器本地处理，不会上传到任何服务器。它基于 WebAssembly 和 Web Workers 实现，可以在浏览器中流畅地打开和渲染数 GB 大小的 trace 文件。

在 UI 中，我们会看到：

- **时间线视图**：每个进程、每个线程、每个 CPU 核心对应一条水平轨道（Track），轨道上的色块代表事件（Slice）。
- **计数器图表**：CPU 频率、内存使用量等随时间变化的数值，以折线图的形式叠加显示。
- **SQL 查询面板**：直接在 UI 中写 SQL 语句查询 trace 数据，结果以表格形式返回。

我们将在 13.3 节详细介绍 Perfetto UI 的使用方法。

### Trace Processor：SQL 分析引擎

Trace Processor 是 Perfetto 的分析核心。它把二进制的 trace 文件解析后加载为一个 SQLite 数据库，我们可以用标准 SQL 对其中的数据进行查询。这比在 UI 上手动点选更适合复杂分析。我们可以写脚本自动化分析流程，也可以批量处理大量 trace 文件。

Trace Processor 的分析能力分为三层，从高层到底层依次是：

1. **内置 Metrics**：`trace_processor_shell --run-metrics android_cpu,android_startup,android_frame_timeline_metric` 可以直接输出 CPU、启动、Frame Timeline 等维度的结构化指标报告。Perfetto 当前可核到的 Android 指标包括 `android_frame_timeline_metric`、`android_hwui_metric`、`android_jank_cuj` 等；不要把 `android_jank` 当成内置 metric 名使用。
2. **Standard Library + Trace Summary v2**：PerfettoSQL Standard Library 封装了常用分析逻辑为可复用的 MODULE（如 `linux.memory.process`）。Trace Summary v2 通过 `referenced_modules` 字段声明依赖的官方模块，避免重复实现同一套分析逻辑。优先复用官方模块；只有缺口指标才写自定义 PerfettoSQL。
3. **原始 SQL 查询**：直接对 `slice`、`sched`、`counter` 等底层表写 SQL，灵活度最高，但需要熟悉表结构。

例如，想统计某个 trace 中所有帧的耗时分布，一条 SQL 就能完成：

```sql
-- Perfetto 内部时间单位为纳秒（ns），除以 1e6 转为毫秒
SELECT
  name,
  COUNT(*) as frame_count,
  AVG(dur) / 1e6 as avg_ms,
  MAX(dur) / 1e6 as max_ms
FROM slice
WHERE name LIKE 'doFrame%'
GROUP BY name;
```

Trace Processor 可以通过命令行工具（`trace_processor_shell`）使用，也可以嵌入到自己的分析脚本中。我们将在后续章节中详细讲解其用法。

## 核心概念

使用 Perfetto 前，需要先区分几个核心概念。这些概念贯穿了 Perfetto 的采集、分析和可视化三个阶段。

### TraceConfig：采集配置

每次 trace 会话都由一个 TraceConfig 定义。TraceConfig 的格式是 protobuf message，不是 JSON。对 perfetto normal mode 来说，设备侧接收的是 protobuf 配置：Android 10 起可以用 `--txt` 让 CLI 读取人类可读的 pbtx / pbtxt；Android 9 只有 binary protobuf 输入。与之相对，simple mode 不读 TraceConfig 文件，而是直接吃命令行 flags，只覆盖 ftrace / atrace 子集。

TraceConfig 至少要回答四件事：

- 开哪些 data source
- buffer 多大、写到哪个 buffer
- 录多久
- 结束时一次性写文件，还是按 long trace 配置周期性刷盘

这是一份能直接给 perfetto normal mode 用的最小 pbtx 示例：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: DISCARD
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "input"
      atrace_categories: "sched"
    }
  }
}

duration_ms: 10000
```

对应的抓取命令因 Android 版本而异：

```bash
# Android 12+（推荐）
# /data/misc/perfetto-configs/ 由 Perfetto init 确保存在且 SELinux 可读
adb push config.pbtx /data/misc/perfetto-configs/config.pbtx
adb shell perfetto --txt -c /data/misc/perfetto-configs/config.pbtx \
  -o /data/misc/perfetto-traces/trace.perfetto-trace

# Android 10/11 非 root 设备
# SELinux 限制使 Perfetto 无法直接读取任意路径的配置文件，通过 stdin 传入
cat config.pbtx | adb shell perfetto -c - --txt \
  -o /data/misc/perfetto-traces/trace.perfetto-trace

# Android 9
# 不支持 --txt，必须用 binary protobuf
perfetto_to_pb -i config.pbtx -o config.bin  # 在主机上用 Perfetto SDK 工具编译
cat config.bin | adb shell perfetto -c - \
  -o /data/misc/perfetto-traces/trace.perfetto-trace
```

如果设备还是 Android 9，就要先把同一份 TraceConfig 编成 binary protobuf 再传给 `perfetto`，因为这一代还不支持 `--txt`。Record trace 页面和 Android Studio 这类图形入口，本身也在替我们生成同一类 TraceConfig，只是输入方式更友好。

### Data Source：数据的来源

Data Source 是 Perfetto 对“可采集能力”的抽象。一个 data source 可以是内核事件、用户空间标记、进程统计、堆分析，也可以是功耗或图形时间线。系统级 data source 多数由 `traced_probes` 这类系统进程代采；App 自定义 trace 则由 App 自己充当 Producer。

除了 `linux.ftrace` 之外，入门阶段最容易混淆的是这些能力：

- **Native heap sampling**：看“谁在分配 native 内存”，常见入口是 heapprofd。
- **Java allocation sampling**：看“谁在频繁分配 Java 对象”，通常也走 heapprofd，但配置里要加 `heaps: "com.android.art"`。
- **Java heap dump / retained graph**：看“谁把对象留在堆里”，走 `android.java_hprof`。
- **logcat in trace**：把日志写进同一时间窗里，方便和 Binder、调度、渲染事件一起读；官方 `android.log` data source 标注为 Android userdebug builds 支持，普通 user build 不应默认视为可用。
- **power / rail counters**：能不能抓到，要看设备和 HAL 是否实现了对应能力。

只知道名字还不够，排查效率取决于“这台设备能不能用”。先把常见能力的版本和门槛摆清楚：

### 常见 data source 可用性对照表

| 能力 | 典型前提 | user build 额外门槛 | 适合看什么 |
| --- | --- | --- | --- |
| ftrace + atrace（调度、Binder、gfx、view、input 等） | Android 9+ 有 Perfetto services；Android 9/10 非 Pixel 设备常见要手动 enable | 常规系统追踪一般不要求 App manifest gate | CPU 调度、Binder、渲染、输入、系统服务时序 |
| FrameTimeline | Android 12+ | 无额外 App gate | 帧级 jank 分类、`Expected/Actual Timeline` |
| logcat in trace | Android 10+ 常用；官方 `android.log` data source 标注为 userdebug builds 支持 | 普通 user build 不应默认可用，先以设备实测能力为准 | 把日志与同一时间窗里的系统事件放在一起看 |
| Native heap sampling | Android 10+ | 目标 App 通常要 `profileable` 或 `debuggable`；`userdebug` / root 可以扩大到更多系统进程 | native alloc / free 调用栈 |
| Java allocation sampling | Android 12+ | 和上面一样，目标 App 需要 `profileable` 或 `debuggable` | Java 对象分配热点 |
| Java heap dump / retained graph | Android 11+ | 目标 App 通常要 `profileable` 或 `debuggable` | retained graph、泄漏保留关系 |
| power / rail counters | Android 10+，并且设备实现了对应 HAL / energy 接口 | 机型能力决定是否有数据 | 电源 rail、子系统能耗 |

这张表只解决“有没有入口”。真要选采集方式，还要把 Consumer 放进来一起看。Traceur、`adb shell perfetto`、`record_android_trace` 和 Android Studio Profiler 能看到的范围并不一样。


<!-- AIW-源码调研-2026-04-20: lmkd trace 事件补充 -->
<!-- Task2B rework 2026-05-25: P0 修正 LMKD Perfetto 事件名，P1 补版本化观测路径 -->
### LMKD 行为追踪 [自动发现]

Perfetto 可以追踪 lmkd（Low Memory Killer Daemon）的杀死行为，但观测路径取决于 Android 版本和内核配置。

**Legacy kernel LMK（Android 9 及更早，部分设备延续到 Android 10）**：通过 ftrace 事件 `lowmemorykiller/lowmemory_kill` 记录。Perfetto 导入 ftrace 数据后，可在 `instant` 表中查询 `instant.name = 'mem.lmk'`。在设备上先验证该事件是否存在：

```bash
adb shell cat /sys/kernel/tracing/events/lowmemorykiller/enable
```

如果路径不存在，说明设备已切换到用户空间 lmkd。

**Modern lmkd（Android 10+）**：lmkd 已迁移至 `system/memory/lmkd/`（C++ 实现），默认使用 PSI（Pressure Stall Information）监控内存压力。Perfetto 没有独立的 `android_lmk_proc_state` 或 `linux.lowmemorykiller` data source；lmkd 行为需要结合多条证据链交叉验证：

- `lmkd atrace` 标记（如果设备编译了对应 atrace tag）
- `logcat | grep lmkd` 查看杀死决策日志
- `statsd` 的 `ProcessKilled` atom（通过 `dumpsys stats` 或 Perfetto `statsd` data source）
- PSI stall 事件（`some` / `full` 行的 `avg10` / `avg60` / `avg300`）
- `ProcessList.java` 中 `TRIM_MEMORY_*` 级别回调（通过 App 侧 `ComponentCallbacks2.onTrimMemory()` 触发）

当这些信号密集出现时，说明系统内存压力持续升高，可能间接导致渲染帧超时或 GC 停顿。在 Perfetto UI 中结合 CPU 调度、内存 Counter（`mem.used` / `mem.available`）和 `lmkd` 相关日志一起观察效果最好。

详细源码分析见 §7.3「卡顿分析方法论」。

[源码验证: lmkd.cpp (android-16.0.0_r1), Perfetto ftrace parser — instant.name='mem.lmk', Perfetto 官方 memory counters 文档]

### Track：时间线上的一条轨道

打开 Perfetto UI，我们会看到很多水平排列的轨道，每个进程一条、每个线程一条、每个 CPU 核心一条。这些轨道就是 Track。

Track 是事件的容器。属于同一类上下文的事件被组织到同一个 Track 上。例如：

- 一个线程的所有 trace 事件（measure、layout、draw 等）在同一个线程 Track 上。
- 每个 CPU 核心的调度事件（哪个进程在运行、运行了多久）在对应的 CPU Track 上。
- 系统级的计数器数据（CPU 频率、内存用量）有各自独立的 Counter Track。

Track 的组织方式是分层的：进程 Track 是父 Track，线程 Track 是子 Track。在 UI 中，我们可以展开/折叠进程来查看/隐藏其下的线程 Track。

### Slice：时间段内的事件

Slice 是 Perfetto 中最常见的事件类型。它代表一个有开始、有结束的时间段操作。在 UI 中，Slice 显示为轨道上的色块，色块的长度代表持续时间，颜色和标注代表事件类型。

一个典型的例子是 `Choreographer#doFrame`。当主线程执行一帧的渲染工作时，这个 Slice 从 VSync 回调开始，到渲染完成结束。它的内部可能包含多个子 Slice：`measure`、`layout`、`draw`、`syncAndDrawFrame` 等，形成嵌套结构。

```text
Choreographer#doFrame (16.2ms)
  ├── measure (2.1ms)
  ├── layout (1.8ms)
  └── draw (10.3ms)
       ├── syncAndDrawFrame (1.2ms)
       └── RenderThread (8.5ms)
```

通过分析 Slice 的嵌套关系和持续时间，就能定位一帧的耗时花在了哪个环节。这是 Perfetto 性能分析中最常用的基本操作。

### Counter：随时间变化的数值

Counter 记录的是一个数值随时间的变化。和 Slice 不同，Counter 没有明确的开始和结束，它是对某个指标的连续采样。

在 Perfetto UI 中，Counter 以折线图的形式显示。常见的 Counter 包括：

- CPU 频率（每个核心独立追踪）
- 进程的内存使用量（RSS、PSS）
- 线程的 CPU 使用率
- 硬件功耗计数器

Counter 和 Slice 通常配合使用。比如发现某帧的 `doFrame` Slice 特别长（卡顿），同时看到对应的 CPU 频率 Counter 在那个时间段很低，原因很可能是 CPU 降频导致渲染超时。

## 为什么性能分析离不开 Perfetto

对于还在用 log + 断点做性能分析的读者，Perfetto 的学习曲线可能稍陡。但一旦掌握了它，很多性能问题都能回到同一个问题：**时间花在哪里。** Perfetto 提供的是系统中多个维度的精确时间记录。

具体来说，Perfetto 在以下场景中不可替代：

**流畅性分析。** 掉帧、卡顿的本质是某帧的渲染超时。Perfetto 可以让我们看到每一帧从 VSync 到上屏的完整流程，Choreographer 的 doFrame 用了多久、RenderThread 耗时多少、SurfaceFlinger 合成是否及时。这些信息分散在 App 进程、system_server 进程和 SurfaceFlinger 进程中，只有系统级的 trace 才能把它们关联起来。

**启动速度分析。** 冷启动涉及 Zygote fork → Application 创建 → ContentProvider 初始化 → Activity 创建 → 首帧渲染等十几个步骤，跨越多个进程。Perfetto 可以按时间线展示每个步骤的耗时和依赖关系，一眼看出瓶颈在哪。

**ANR 分析。** ANR 是主线程阻塞的结果，但阻塞的原因可能在其他进程（比如 Binder 对端正在做耗时操作）。Perfetto 的 Binder 事件追踪能把完整的 Binder 调用路径摆出来：谁发起的、发给了谁、对端处理了多久。

**功耗分析。** 从 Android 10 开始，Perfetto 可以采集 ODPM（On-Device Power Rails Monitor）数据，追踪每个硬件子系统（CPU、GPU、显示屏、Modem 等）的独立功耗。这在优化电池续航时非常有用。

**内存分析。** 通过 heapprofd 和 java_hprof 数据源，Perfetto 可以在 trace 中同时记录内存分配行为和系统状态变化，帮助我们理解"什么时候分配了内存、分配了多少、触发了什么后续事件"。

这些场景都有一个共同特征：问题跨越了单个进程、单个线程的边界。遇到这类系统级问题时，Perfetto 往往是首选工具，因为只有它能把 App、system_server、SurfaceFlinger 和内核事件放到同一根时间线上。日志、FrameMetrics、Android Studio Profiler 仍然有价值，但它们更适合局部验证，不能替代这条系统级时间线。

## Perfetto 的跨平台能力

Perfetto 不止服务于 Android。作为一个开源项目，它的设计目标是成为一个通用的 tracing 基础设施。

在 Chrome 中，Perfetto 是 `chrome://tracing` 背后的引擎。Chrome 的各个组件（渲染、网络、GPU 等）通过 Perfetto 的数据源接口上报 trace 事件，开发者可以在 Perfetto UI 中查看完整的浏览器行为时间线。

在 Linux 桌面/服务器上，Perfetto 提供了完整的系统级 tracing 能力，包括 ftrace 数据源、/proc 和 /sys 轮询、以及 Native 应用的 CPU 和堆 Profiling。一个叫 `tracebox` 的单文件可执行程序把所有必要工具打包在一起，方便在不同 Linux 机器上部署。

对于 Android 开发者来说，这个跨平台能力的实际意义在于：我们掌握的 Perfetto 使用技巧（UI 操作、SQL 查询、配置方法）在所有平台上通用。如果将来需要在 Linux 或 Chrome 上做性能分析，不需要重新学习一套工具。[已验证: 官方文档, perfetto.dev/docs]

## [扩展] Perfetto SDK：在 App 中嵌入自定义 Trace

Perfetto 提供了一个 C++17 的 Tracing SDK，允许 App 开发者在自己的代码中添加自定义的 trace 点。它的能力范围比 `android.os.Trace` 更大，后者最终落到 atrace：

- **自定义事件类型**：除简单的 begin/end 外，还可以定义带结构化数据的复杂事件。
- **自定义 Counter**：可以追踪 App 特有的指标（队列长度、缓存命中率等），和系统级数据在同一时间线上展示。
- **两种运行模式**：
  - *In-process 模式*：Perfetto 服务运行在 App 进程内部，只采集 App 自己的事件，不需要特殊权限。支持 Android、Linux、macOS、Windows。
  - *System 模式*：App 通过 UNIX socket 连接到系统的 `traced` 守护进程，这样 App 的自定义事件就和系统级事件（CPU 调度、内存变化等）放在同一时间线上。这类组合更适合做全栈性能分析。

SDK 的使用方式是继承 `perfetto::DataSource` 类，定义自己的事件 schema。采集到的事件数据可以直接在 Perfetto UI 中查看，也可以通过 Trace Processor 用 SQL 查询。

定义完全自定义的数据格式时，可能需要在 Trace Processor 和 UI 中做对应的适配工作，才能正确解析和展示自定义事件。对于大多数 Android 性能分析场景，`android.os.Trace` API（atrace）已经足够，SDK 主要面向有深度定制需求的应用和引擎开发者。[已验证: 官方文档, perfetto.dev/docs/instrumentation/tracing-sdk]

## 版本演进与抓取入口对照表 [自动发现]

把 Android P / Q / R+ 的边界列清，前面的命令和 data source 才不会混。

### Android 版本对照表

| 版本 | `traced` / `traced_probes` 状态 | normal mode 配置输入 | 配置文件读取路径 / SELinux | 常见启用条件 | 这一章该怎么理解 |
| --- | --- | --- | --- | --- | --- |
| Android 9 (P) | 服务已进 system image | binary protobuf（仅 stdin） | 不支持 `--txt`，无配置文件路径问题 | 非 Pixel 设备常见要手动 enable `persist.traced.enable=1` | 不是“只能用 Systrace”，只是文本 `--txt` 还不可用 |
| Android 10 (Q) | 服务仍可能未默认 enable | binary protobuf + `--txt` | 非 root 设备 SELinux 限制配置文件读取，需用 stdin 传入 | 非 Pixel 设备仍常见手动 enable | heapprofd 开始进入常用工作流 |
| Android 11 (R) | 大多数设备默认启用 | binary protobuf + `--txt` | 同 Android 10，非 root 设备建议 stdin | 一般不用再手动 enable | Perfetto 成为日常 Android 系统追踪主入口 |
| Android 12 (S) | 默认启用 | binary protobuf + `--txt` | `/data/misc/perfetto-configs/` 可用，SELinux 已放行 | FrameTimeline 成为帧级 jank 分类的主入口 | Perfetto 组件（`traced`/`traced_probes`）仍为平台二进制部署；部分设备通过 Mainline 机制提供更新，具体包名和覆盖范围因设备和 build 而异 [待验证] |
| Android 15 (V, API 35) | 默认启用 | binary protobuf + `--txt` | `/data/misc/perfetto-configs/` 可用 | `ProfilingManager` (API 35) 允许 App 请求系统采集 trace；`com.android.profiling` APEX 部分组件 min_sdk 35 | 从手动 adb 抓取转向 App 发起、系统执行的触发式 profiling |
| Android 16 (API 36) | 默认启用 | binary protobuf + `--txt` | `/data/misc/perfetto-configs/` 可用 | System Triggered Profiling 覆盖 ANR 等场景的背景 trace 捕获 | Profiling 能力从主动采集扩展到被动捕获 |
| Android 17 (API 37, Beta) | 默认启用 | binary protobuf + `--txt` | `/data/misc/perfetto-configs/` 可用 | system-triggered profiling 继续扩展 anomaly / OOM / excessive CPU 触发方向 | 版本表按能力来源拆分，避免把 15-17 的 profiling 变化混成一行 |

注意：`traced` / `traced_probes` 仍以平台二进制方式部署（`/system/bin/traced`、`/system/bin/traced_probes`），不在独立 APEX 包内。Android 12+ 部分设备将 Perfetto 组件通过 Mainline 机制提供更新，但 AOSP `external/perfetto/Android.bp` 中并未定义 `com.android.os.perfetto` APEX 模块——实际 Mainline 更新的载体和覆盖范围因设备 build 而异。Android 15 (API 35) 起 `ProfilingManager` 相关组件通过 `com.android.profiling` APEX 单独部署（`min_sdk 35`）。具体设备上的 APEX 包名和可更新边界以实际 `/apex/` 目录和 build manifest 核对为准。[已验证: external/perfetto/Android.bp, external/perfetto/src/traced/traced.rc, AOSP android-16.0.0_r1]

### 常见抓取入口对照表

| 入口 | 运行位置 | 输入方式 | 结果形式 | 适合场景 | 备注 |
| --- | --- | --- | --- | --- | --- |
| Traceur / 系统追踪 | 设备端 UI | UI 开关、预置模板 | 设备上的 `.perfetto-trace` 文件 | 现场快速抓一份设备级 trace | 依赖系统 tracing services |
| `adb shell perfetto` simple mode | 设备 shell | 命令行 flags | `.perfetto-trace` | 只抓 ftrace / atrace 子集，命令最短 | 适合快速抓取，或者能力受限时的兜底方案 |
| `adb shell perfetto` normal mode | 设备 shell | TraceConfig protobuf；Android 10+ 可 `--txt` 读 pbtx | `.perfetto-trace` | 全量 data source、long trace、精细 buffer 配置 | 依赖 `traced` / `traced_probes` |
| `record_android_trace` | 主机脚本 + 设备 | 脚本 flags 或 config file | 自动 pull 到本地的 trace 文件 | 高频 adb 工作流 | 它只是对 device-side perfetto 的包装 |
| Android Studio Profiler | Android Studio | Studio 预置配置 | Profiler session / trace | App 局部定位、开发期快速查看 | 方便，但设备级观测面不如直接用 Perfetto UI 全 |
| tracebox | Linux 主机 | CLI / config file | Linux trace | Linux 桌面 / 服务器 tracing | 不是 Android 设备抓取入口 |

用哪个入口，取决于这次要抓的是整机时序、单 App，还是 Linux 主机。确认这一点，后面的命令、权限和结果文件格式就不会混。

## 常见问题与误区

**“Perfetto 需要 root 权限才能用。”** 不是。常规的系统追踪、Traceur、`adb shell perfetto` 抓调度 / gfx / view / input 这类数据，在 user build 上就能做。需要额外条件的是堆分析这类 data source：`android.heapprofd` 在 Android 10+ 的 user build 上，目标 App 通常要带 `profileable` 或 `debuggable`；root / userdebug 主要是把范围扩到更多 system process。

**“Perfetto 和 Android Studio Profiler 是什么关系？”** Android Studio Profiler 复用了 Perfetto 的采集与解析能力，但它更偏 App 开发期的局部视角。Perfetto UI 更适合把 App、system_server、SurfaceFlinger 和内核事件放到同一时间窗里一起看。做局部 CPU / memory 调试时，Studio 更顺手；做系统级排查时，Perfetto UI 更完整。

**“Systrace 还能用吗？”** 旧设备和旧流程当然还能用，但版本线要说准：Android 9 已经把 Perfetto services 放进 system image，只是 Android 9/10 的 non-Pixel 设备常见要手动 enable；Android 11+ 大多数设备默认就是 Perfetto 体系。新项目如果要抓系统级 trace，优先用 Perfetto。

**“抓 trace 会影响性能吗？”** 空闲时 Perfetto 几乎不做采集。录制开销来自启用了哪些 data source、buffer 多大、有没有打开 heapprofd / Java heap dump / 高频 sampling。只抓常见的调度和渲染类别，干扰通常明显小于堆分析和高频采样；要做 benchmark 或长时录制，还是要按目标设备实测。

## 下一步

Perfetto 的定位、架构和核心概念已经铺开。接下来的章节进入实操层面：13.2 节讲解如何在设备上抓取 trace，13.3 节讲解 Perfetto UI 的使用方法。如果对渲染管线还不熟悉，可以先回顾 2.1 节的渲染架构全景，那里介绍的每个组件在 Perfetto 中都有对应的 Track。

## 参考资料

- 《从 Trace 到洞察：SmartPerfetto AI Agent 的 Harness Engineering 实战》，博客文章，https://androidperformance.com/2026/04/10/SmartPerfetto-Architecture-Deep-Dive/（关键词：perfetto、agent、trace；入库时间：2026-04-11）
- 《Perfetto 2026 架构级深度技术分析》，DeepResearch 调研结果，/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Perfetto 2026 架构级深度技术分析  .md（摘要：Perfetto v51-v54 在 Android 13-16 的架构演进，覆盖 Mainline APEX、Trace Summary v2、FrameTimeline/CUJ/monitor contention 联动、CI 自动化与多级 buffer 丢包诊断；注入时间：2026-04-19）
- Perfetto 官方文档：https://perfetto.dev/docs/
- Android 官方 Perfetto 指南：https://source.android.com/docs/core/debug/perfetto
- Perfetto GitHub 仓库：https://github.com/google/perfetto
- Perfetto UI：https://ui.perfetto.dev
- AOSP `traced` 服务源码路径：`external/perfetto/src/traced/service/`
- AOSP `traced_probes` 服务源码路径：`external/perfetto/src/traced/probes/`
- AOSP `heapprofd` / `java_hprof_producer` 源码路径：`external/perfetto/src/profiling/memory/`
- AOSP `traced_perf` / `perf_producer` 源码路径：`external/perfetto/src/profiling/perf/`
- 高爷 Systrace / Perfetto 系列教程：https://www.androidperformance.com/2019/12/01/Android-Systrace(Perfetto)-Basic/
