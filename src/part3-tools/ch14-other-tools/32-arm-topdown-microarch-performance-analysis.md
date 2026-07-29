---
title: "ARM Topdown 微架构性能分析方法论与 Android 实践"
chapter: "14.32"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1 (simpleperf)"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/ndk/guides/simpleperf"
  - type: aosp
    path: "platform/system/extras/simpleperf/"
  - type: aosp
    path: "kernel.org/doc/Documentation/admin-guide/perf.rst"
  - type: blog
    path: "community.arm.com/developer/research"
  - type: paper
    path: 'Yasin, A. "A Top-Down Method for Performance Analysis and Counters Architecture", ISPASS 2014'
tags: ['arm-topdown', 'microarchitecture', 'perf', 'simpleperf', 'performance-analysis', 'pmu']
related_chapters: ['5.28', '14.24']
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "研究素材 + 每日信息"
gap_score: "15/20"
processed_by: "task2a-draft"
---
# 14.32 ARM Topdown 微架构性能分析方法论与 Android 实践

<details>
<summary>历史 outline（Hermes 流水线保留）</summary>

<!-- outline-start -->

## 🔹 锚点 1：Topdown 方法论模型（Slot / Frontend-Bound 等四象限）

[待验证] Topdown 分析最初由 Yasin 等人在 2014 年 ISPASS 论文中针对 Intel/AMD 微架构提出 [引用: Yasin, A. ISPASS 2014]。该方法把 CPU pipeline slot 划分为四类：

- **Retiring**：真正完成有用工作的 slot（IPC ≈ Retiring 占比）
- **Bad Speculation**：被错误预测浪费的 slot（分支预测失败 / 流水线冲刷）
- **Frontend Bound**：前端无法喂饱后端的 slot（i-cache miss / BTB miss / 解码瓶颈）
- **Backend Bound**：后端执行单元空闲的 slot（d-cache miss / 执行单元端口争用 / 长延迟指令）

> ⚠️ 注意：ARM 公开文档未像 Intel TMAM 那样给出官方方法论白皮书。但 ARM 在 ARMv8 PMU 中预留了与 Topdown 等价的 PMU 事件组（Cortex-A77 之后正式可用）。本节所述 ARM Topdown 属社区/工具厂商（Arm Telemetry Solution / Streamline / Linaro 工具链）的实现，需区分 v1（slot-based, Cortex-A77 起）和 v2（ARMv9, Level 1 抽象）。

[适用版本: Android 14 (API 34) - Android 17 (API 37)] Android 端推荐通过 `simpleperf record -e ...` 采集 PMU 原始计数器，再在 `simpleperf report --print-sample-period` 中查看 front-end / back-end 占位 [待验证: 具体 CLI 参数]。

与 x86 的差异（社区共识，L4 交叉验证）：

| 维度 | x86 Intel TMAM | ARM Topdown |
|------|----------------|-------------|
| 抽象层级 | L1~L3 三层 | v1 单层 / v2 三层 |
| 事件完备性 | 完备事件集（教科书级定义） | 需要多颗 CPU 微架构分别定义事件映射 |
| 工具链 | perf + toplev (likwid) | Arm Telemetry + simpleperf |
| Android 原生支持 | 无 | 无（需手动配置 PMU 事件） |

## 🔹 锚点 2：ARM Telemetry Solution 工具链

[待验证: 工具链当前所有权] ARM Telemetry Solution 原本由 ARM 公司提供，是 Topdown 分析的官方工具链，组成部分：

- `topdown_tool` —— 把 PMU 原始事件转换为 Topdown 分类指标
- `telemetry-solution` —— Linux perf 后端 + 浏览器可视化前端
- Streamline —— ARM DS-5/Development Studio 自带的 GUI 采集器

在 Android 端的集成路径（已知可行）：

```
adb shell simpleperf record -e ...   →  本机 .data 文件
        ↓ adb pull
streamline-cli (host)   →  .apc 报告
        ↓ 浏览器
可视化四象限 + 逐函数分解
```

> [已验证: AOSP android-17.0.0_r1, platform/system/extras/simpleperf/] simpleperf 自身不直接计算 Topdown 分类，需要外部工具（如 Arm Telemetry Solution 或 toplev 移植）把 PMU 事件归并到四象限。

[适用版本: Android 14 (API 34) - Android 17 (API 37)] simpleperf 已在 Android 12+ 持续维护，对 PMU 事件支持随 CPU 演进扩展。但 ARM Telemetry Solution 与 Android 集成的官方文档较少，社区主要靠 Linaro / CodeLinaro 邮件列表与开发者博客。

## 🔹 锚点 3：simpleperf Topdown 采集工作流

[已验证: AOSP android-17.0.0_r1, platform/system/extras/simpleperf/] simpleperf 是 Android 自带的 perf 命令行实现，位于 `platform/system/extras/simpleperf/`，主入口 `simpleperf.cpp`。常用子命令：

- `record`：采集样本（基于采样或 tracepoint）
- `report`：聚合样本，输出热点函数/汇编
- `stat`：类似 `perf stat`，输出 PMU 计数器增量

Topdown 采集的关键在 **PMU 事件选择**：

```bash
# 示意：在 ARMv8.2 设备上采集 Topdown 一级指标
adb shell simpleperf stat     -e cpu-cycles,instructions,branch-misses,cache-misses     -- app_process -D <class>
```

> [待验证: android-17.0.0_r1 上 simpleperf 对 ARMv9 BRBE / SPE 等高级特性的支持矩阵] ARMv9 引入的 Branch Record Buffer Extension（BRBE）可在 simpleperf 中作为 `brbe` 后端使用，理论上能给 Topdown 提供精准分支信息，但 simpleperf 主线合入 BRBE 后端的时间点需要单独验证。

不同 Cortex-A 系列的事件映射（已知差异）：

| CPU 微架构 | 主要厂商 | Topdown 事件可用性 |
|-----------|----------|---------------------|
| Cortex-A55/A75 | ARM | 部分（社区维护事件映射） |
| Cortex-A76/A77/A78 | ARM | 完整（v1 Topdown） |
| Cortex-A710/A715 | ARM | 完整（v1 + 部分 v2） |
| Cortex-X1/X2/X3 | ARM | 完整（v1 + 部分 v2） |
| Cortex-X4/A720 | ARMv9.2 | v2 三层抽象完整 |
| Kryo / Oryon | 高通 / 自研 | 仅厂商内部事件，公开 Topdown 不直接可用 |

## 🔹 锚点 4：从 Topdown 指标到代码优化

按四象限给出代码层面对应（社区共识 + ARM 官方文档）：

### Frontend Bound 优化

- **i-cache miss**：
  - 把热点汇编拆出 `.text.hot` 段（`-ffunction-sections` + 链接脚本）
  - `-fno-jump-tables` → switch 改写为 if-else 链（减少 i-cache footprint）
  - Profile-Guided Optimization（PGO） / AutoFDO 反馈重排基本块

- **BTB miss**：
  - 函数内联克制（避免 i-cache 与 BTB 双压力）
  - `-mllvm -align-all-functions=N`（LLVM 后端 force 函数对齐提升 BTB 命中率）

### Backend Bound 优化

- **d-cache miss**：
  - 数据结构 SoA（Structure of Arrays）替换 AoS
  - 预取指令 `__builtin_prefetch`
  - 关键路径上 `__attribute__((aligned(64)))` 避免 cache line 跨越

- **内存延迟**：
  - 软件流水（software pipelining）
  - 关键循环用 `restrict` 提示编译器无别名

### Retiring 优化

- **向量化**：
  - NEON / SVE intrinsics
  - `-O3 -ftree-vectorize` + `-mllvm -force-vector-width=N`
  - BOLT 二进制后链接优化（详见 🔸 扩展 1）

- **指令融合**：
  - 编译器配合，热点手写 asm 优化关键路径

### Speculation 优化

- **分支预测**：
  - 不可预测分支改写为无分支代码（cmov / 位运算）
  - `-fno-jump-tables -mllvm -unroll-threshold=...` 控制循环展开阈值

> [适用版本: Android 14 (API 34) - Android 17 (API 37)] 上述每条优化都有基准可证收益，但具体阈值因 CPU 而异。Android 端做 CPU 微架构敏感优化，建议至少覆盖一颗 ARMv8 大核与一颗 ARMv9 中核。

## 🔹 锚点 5：与 Perfetto 的集成：PMU 计数器轨道可视化

[已验证: AOSP android-17.0.0_r1, external/perfetto/] Perfetto 是 Android 原生 trace 系统，自 Android 10 起成为 systrace 替代品。Topdown 集成路径：

1. **采集**：simpleperf 在 trace 模式下输出 `.perfetto-trace`
2. **解析**：Perfetto 自定义 track（`track_event` proto）
3. **可视化**：UI.perfetto.dev / studio 都能渲染 counter track

```protobuf
# 示意：自定义 counter track
track_descriptor {
  name: "ARM Topdown: Frontend Bound"
  counter: SOFT
}
counter {
  track_id: ...
  timestamp: ...
  value: 0.18   # 18% slots
}
```

[自动发现] 关联分析上，推荐把 Topdown counter track 与 `sched_switch` / `fence` / `cpu_frequency` track 叠加，能直接看到"某次 CPU 降频后 Retiring 暴跌"或"某次内核睡眠唤醒后 Backend Bound 飙升"的关联事件。

> [适用版本: Android 14 (API 34) - Android 17 (API 37)] Perfetto 在 Android 14+ 已可声明式 schema 注册 custom track；早期版本需要 hack `track_event` proto 注入。

## 扩展

### 🔸 扩展点 1：BOLT 二进制优化与 Topdown 验证

[待补充] Facebook BOLT（Binary Optimization and Layout Tool）支持 aarch64 后端，可对 .text 段做函数级重排与对齐，目标是提升 i-cache / i-TLB 命中率。BOLT 与 Topdown 配合的标准用法：

1. 用 Topdown 工具识别 Frontend Bound 主导工作负载
2. 对热点函数 `.text.hot` 段重排
3. 重测 Topdown，验证 Frontend Bound 下降、Retiring 上升

> [待验证: BOLT 在 Android 平台 NDK 工具链的可用性] Facebook 已公开 BOLT 的 aarch64 支持，但 Android NDK 默认未集成；需要自建工具链或在 OLLVM/BOLT 分支基础上做交叉编译。

### 🔸 扩展点 2：AutoFDO 与 Topdown Feedback 循环

[适用版本: Android 14 (API 34) - Android 17 (API 37)] AutoFDO 是 Android 主线已经引入的采样反馈优化（`Android.bp` 中 `optimization: "feedback-...`），使用 Last Branch Record（LBR）或 BRBE 采样编译器 PGO。

与 Topdown 的关联：

- LBR 采样主要用于"分支概率"，对 Backend Bound 改善有限
- BRBE（含目标地址）则可补全到 Topdown 全套指标
- ARMv9 上的 BRBE + AutoFDO 配合预期能让 Retiring 占比提升 5~15%（社区基准，L4 交叉验证 [争议]）

> [争议] 不同基准下 AutoFDO 收益差异较大；Google 自家 SoC 与第三方 SoC 上结果不可简单外推。建议结合自家 workload 在 NDK build 中实测 `samples` 与 `train` 两个阶段。

<!-- outline-end -->

</details>

## 14.32.1 Topdown 能回答什么

一次 CPU 性能分析通常会遇到两个不同的问题：

- 处理器把可用的执行机会消耗在了哪里；
- 哪段代码、哪条指令或哪类数据访问造成了这些消耗。

Topdown 处理前一个问题。它把处理器流水线的执行机会归入少量类别，帮助工程师决定下一轮该查取指、分支、数据访问，还是执行单元。函数热点、调用栈、指令地址和内存地址仍要交给采样工具定位。

因此，Topdown 是诊断顺序，不是优化处方。看到 Backend Bound 偏高后直接加预取，或者看到 Frontend Bound 偏高后直接改链接布局，都缺少中间的归因证据。

本章以 Android 17 / API 37、AOSP `android-17.0.0_r1` 中的 simpleperf 为平台锚点。Arm Telemetry Solution 的示例公式来自它支持的具体 CPU 数据库；这些公式不能自动套到任意 Android SoC。

## 14.32.2 Intel TMAM 与 Arm Topdown 的关系

Ahmad Yasin 在 2014 年 ISPASS 论文中提出了面向 Intel 乱序处理器的 Top-Down 分析方法。论文用 pipeline slot 统计 Retiring、Bad Speculation、Frontend Bound 和 Backend Bound。后来 Intel 将这套体系扩展为多级 TMAM。

Arm 当前也有官方 Topdown Methodology，并由 Arm Telemetry Solution 提供事件定义、CPU 数据库和 `topdown-tool`。Arm 官方的跨平台说明保留了相同的四个一级名称，同时明确指出 Arm 与 Intel 使用不同的 PMU 事件、计算公式和工具。

| 项目 | Intel TMAM | Arm Topdown |
| --- | --- | --- |
| 一级分类 | Retiring、Bad Speculation、Frontend Bound、Backend Bound | 同名四类 |
| 计数事件 | Intel 型号专属事件与 perf metric | Arm CPU 对应的 PMU 事件 |
| 公式参数 | 由 Intel 微架构定义 | 由 Arm CPU telemetry specification 定义 |
| 官方工具 | Linux perf 的 Topdown/metric 支持及 Intel 工具 | Arm Telemetry Solution 的 `topdown-tool` |
| Android 17 现成入口 | 没有通用入口 | simpleperf 可采集设备支持的事件，但不计算四类指标 |

四个名称相同，不表示分母、流水线宽度、错误分支恢复代价也相同。把 Intel 的公式换成 Arm 事件名，结果通常没有物理含义。

### Slot 不是 CPU cycle

Slot 表示一个周期内处理器理论上可以接收或处理的一次操作机会。超标量处理器每周期有多个 slot。某个公式若采用 8 slots/cycle，分母就可能写成 `8 × CPU_CYCLES`。

这个 8 属于具体 CPU 定义。它不能根据 Armv8、Armv9 或 Android API 级别推导，也不能从 IPC 值反推。IPC 统计每周期退休的架构指令；Retiring 指标统计公式定义下的退休 slot 占比，两者不是同一个量。

### 四个一级类别

| 类别 | 计量含义 | 下一轮常查方向 | 常见误读 |
| --- | --- | --- | --- |
| Frontend Bound | 前端没有及时向后端提供操作所损失的 slot | I-cache、I-TLB、取指、解码、分支预测与代码布局 | 一律归因于 I-cache miss |
| Backend Bound | 后端资源约束导致无法发射操作所损失的 slot | 数据 cache、D-TLB、内存延迟、依赖链、执行端口 | 一律归因于 DRAM |
| Bad Speculation | 已推测执行但未退休的操作，以及公式计入的流水线恢复开销 | 错误分支、机器清空、输入相关的分支行为 | 等同于 `branch-misses` 计数 |
| Retiring | 公式认定为已退休操作的 slot | 指令组合、向量化、冗余工作、算法成本 | 数值越高，代码就一定没有优化空间 |

同一次、同一 CPU 上取得的有效计数代入匹配公式后，四类通常应接近 100%。出现负值、明显超过 100% 或各类相加大幅偏离 100% 时，应先检查 CPU 公式、事件支持、计数复用、线程迁移和采集时段。

## 14.32.3 公式属于 CPU，不属于 Arm64

Arm Telemetry Solution 把公式放在每款 CPU 的 telemetry 数据中。以仓库中的 Neoverse V1 r1p2 定义为例，一级公式包含以下参数：

| 指标 | Neoverse V1 r1p2 示例公式 |
| --- | --- |
| Backend Bound | `100 × STALL_SLOT_BACKEND / (8 × CPU_CYCLES)` |
| Frontend Bound | `100 × (STALL_SLOT_FRONTEND / (8 × CPU_CYCLES) - 4 × BR_MIS_PRED / CPU_CYCLES)` |
| Retiring | `100 × (1 - STALL_SLOT / (8 × CPU_CYCLES)) × OP_RETIRED / OP_SPEC` |
| Bad Speculation | `100 × ((1 - OP_RETIRED / OP_SPEC) × (1 - STALL_SLOT / (8 × CPU_CYCLES)) + 4 × BR_MIS_PRED / CPU_CYCLES)` |

表里的 8 和 4 都来自 Neoverse V1 定义。复制这些公式到 Cortex、C1、Kryo、Oryon、Tensor 自研核或其他厂商核，没有充分依据。即使两个 CPU 都能计数 `STALL_SLOT_FRONTEND`，它们的公式也可能不同。

AOSP Android 17 的 `simpleperf/event_table.json` 收录了 Arm64 通用原始事件名，也为若干已知 CPU 型号维护了事件支持表。simpleperf 会结合 MIDR 与实际 `perf_event_open()` 探测结果过滤事件。这个数据库说明工具认识某个事件，不能替代 CPU 的 telemetry specification。

分析前要通过四道门：

1. 精确识别采集落在哪种 CPU 核上；
2. 目标核暴露了公式需要的全部事件；
3. 手里有这款核对应的官方或厂商公式；
4. 这些事件在一致的 workload 时段内得到可信计数。

任何一道门没有通过，都应把结果降级为普通 PMU 线索，不能标成完整的 Arm Topdown 百分比。

## 14.32.4 Android 17 中各工具的边界

### simpleperf stat：计数

`simpleperf stat` 通过 Linux `perf_event_open()` 读取事件计数。Android 17 的命令支持：

- `simpleperf list raw`：列出当前设备可用的 Arm CPU PMU 原始事件；
- `--group`：让一组事件同时调度和退出调度；
- `--print-hw-counter`：探测每个 CPU 可用的硬件计数器数量；
- `--per-core`：按 CPU 输出计数；
- `--cpu`：选择在哪些 CPU 上监控后续事件；
- `--csv`：输出便于脚本解析的结果。

`--cpu` 只限制监控 CPU，不会设置目标线程的 affinity。需要固定线程时，应在测试程序中调用 `sched_setaffinity()`，或对独立 native benchmark 使用 `taskset`。给线上 App 强行绑核会改变调度行为，测试结果只代表该实验条件。

### simpleperf record/report：采样归因

`record` 周期性记录样本，`report` 按 DSO、函数、线程或调用栈聚合。它们适合回答“热点在哪”。事件计数与样本数不能混用：

- `stat` 输出某段时间内累计发生多少次事件；
- `record` 输出抽样位置，样本还会受采样周期、skid 和调用栈质量影响。

原稿提到用 `record` 和 `report --print-sample-period` 直接读取 Topdown 四类占比，这条路径在 `android-17.0.0_r1` 中不存在。

### Arm topdown-tool：Linux perf 上的公式引擎

Arm 官方 `topdown-tool` 自动选择 CPU telemetry 数据，调用 Linux perf 采集事件，再计算指标。它支持按 metric 或 group 组织采集，也能在事件过多时按配置拆分采集。

官方安装与用法面向 Arm Linux 系统，采集后端是 Linux `perf`。当前文档没有承诺它能读取 simpleperf 的 `perf.data`，也没有 simpleperf `.data` 转 Streamline `.apc` 的标准步骤。要在 Android 上复用该工具，需要单独验证 Python 运行环境、perf 兼容性、CPU 数据库、权限和采集接口。

### Perfetto：系统时序上下文

Perfetto 擅长记录调度、CPU 频率、idle、热状态、线程状态和应用 trace marker。它能解释某个计数窗口是否发生迁核、降频或长时间阻塞。

simpleperf 不会自动产出 `.perfetto-trace`，Topdown 百分比也不会自动变成 Perfetto counter track。常用做法是并行采集、用同一 workload marker 对齐窗口，再分别读取 PMU 结果与系统时序。若项目需要把派生指标写入 Perfetto，应显式实现 counter track 生产端，并记录公式、CPU 型号和采集窗口。

### Arm SPE：可选的归因来源

Android 17 simpleperf 源码包含 `SPERecorder` 与 `SPEDecoder`，`simpleperf list arm_spe` 会检查内核是否暴露 SPE PMU。SPE 可给内存操作、延迟或数据源归因提供更细的样本，前提是 SoC、内核、权限和 simpleperf 解码路径都支持。

SPE 不是一级 Topdown 公式的替代品。它更适合在 Backend Bound 已由计数确认后，帮助定位延迟落在哪些指令或地址。Android 17 该版本源码中没有名为 `brbe` 的 simpleperf 后端，不能把 BRBE 写成通用可用的采集选项。

## 14.32.5 一套可复现的 Android 工作流

### 步骤一：固定问题和 workload

先写清测试对象：

- 业务阶段，例如图片解码的第 20 至 120 帧；
- 目标进程与线程；
- 输入数据；
- 冷启动、热启动或稳态；
- 设备温度、供电方式与后台负载；
- 是否允许绑核；
- 每组至少重复多少次。

应丢弃预热轮次，并保存每轮耗时。若耗时本身波动很大，PMU 百分比的差异也很难解释。大核与小核上的计数不要相加后套单一公式。

### 步骤二：在设备上发现能力

下面三条命令分别确认原始事件、硬件计数器数量和 SPE 设备；它们只读取能力，不会开始长时间采集。

```bash
adb shell simpleperf list raw
adb shell simpleperf stat --print-hw-counter
adb shell simpleperf list arm_spe
```

输出中没有 `raw-stall-slot-backend`、`raw-stall-slot-frontend`、`raw-stall-slot`、`raw-op-retired` 或 `raw-op-spec` 时，不应构造完整一级 Topdown。`list raw` 还可能按 CPU 标出支持范围，异构 SoC 应逐簇核对。

### 步骤三：用通用事件建立基线

下面的示例针对可由 shell profile 的 App 采集 10 秒，并按 CPU 输出 CSV。事件仍要以本机 `simpleperf list` 的结果为准。

```bash
adb shell simpleperf stat \
  --app com.example.app \
  -e cpu-cycles,instructions,branch-misses,cache-misses \
  --duration 10 \
  --per-core \
  --csv
```

这组数据可以计算 IPC、分支错误的相对变化和 cache miss 的相对变化，但不能生成 Arm Topdown 四类。非 root 设备上的 App 通常需要是 debuggable 或允许 shell profiling；系统范围 `-a` 采集通常需要 root。

基线至少回答这些问题：

- workload 是否运行在预期 CPU 簇；
- 每轮 CPU cycles 与 instructions 是否稳定；
- 目标线程是否频繁迁核；
- 分支或 cache 指标是否随回归同步变化；
- 内核态是否应该计入。只看用户态时可给事件加 `:u` 修饰符。

### 步骤四：只在完整支持时采集一级事件

若设备列出了全部事件，并且目标 CPU 公式要求它们在同一窗口计数，可以尝试把七个事件放进一个 group。下面的命令会在 group 无法同时调度时暴露问题。

```bash
adb shell simpleperf stat \
  --app com.example.app \
  --group raw-cpu-cycles,raw-stall-slot-backend,raw-stall-slot-frontend,raw-stall-slot,raw-br-mis-pred,raw-op-retired,raw-op-spec \
  --duration 10 \
  --per-core \
  --csv
```

group 所需的计数器超过硬件能力时，内核可能拒绝调度，或者普通非 group 采集会发生 multiplexing。simpleperf 文档明确提醒：复用时各事件只在部分时间内计数，彼此甚至可能不在相同时段运行。不能忽略警告后照常计算比例。

若完整 group 放不下，应按 CPU 公式所需事件拆分：

| 诊断项 | Neoverse V1 示例所需事件 |
| --- | --- |
| Backend Bound | `CPU_CYCLES`、`STALL_SLOT_BACKEND` |
| Frontend Bound | `CPU_CYCLES`、`STALL_SLOT_FRONTEND`、`BR_MIS_PRED` |
| Retiring | `CPU_CYCLES`、`STALL_SLOT`、`OP_RETIRED`、`OP_SPEC` |
| Bad Speculation | `CPU_CYCLES`、`STALL_SLOT`、`OP_RETIRED`、`OP_SPEC`、`BR_MIS_PRED` |

每组要在可重复的 workload 上独立运行，且每组内部同时计数。跨轮拼接会引入输入、调度、温度和 DVFS 差异；应报告重复次数与离散程度。Arm `topdown-tool` 的 `--max-events` 与按 metric 采集也是在处理这一约束，不能把拆分带来的误差藏起来。

### 步骤五：用 CPU 专属定义计算

计算脚本应把这些信息一并写入结果：

- SoC、CPU MIDR、CPU 编号与簇；
- Android build 与内核版本；
- 事件名、原始编码和用户态/内核态修饰符；
- enabled time、running time 与是否 multiplex；
- 公式来源及版本；
- workload 标记和持续时间；
- 原始计数、派生值与重复轮次。

公式里任何分母为零时都应返回无效值。派生值要保留未裁剪结果；直接把负值裁成 0、把超过 100% 的值裁成 100%，会掩盖采集或公式错误。

### 步骤六：按方向做二级归因

Topdown 只给调查方向。下一轮要选择能区分原因的证据：

| 一级结果 | 可继续采集的证据 | 要验证的假设 |
| --- | --- | --- |
| Frontend Bound 高 | L1I/LL cache refill、I-TLB walk、branch miss、代码地址样本 | 取指、翻译、分支恢复或代码体积谁占主导 |
| Backend Bound 高 | L1D/L2/LL cache refill、D-TLB walk、内存延迟、SPE 样本、依赖链 | 内存子系统或执行资源谁在限制发射 |
| Bad Speculation 高 | branch miss、分支地址样本、输入分布、机器清空相关事件 | 哪类分支和哪组输入造成浪费 |
| Retiring 高但耗时仍长 | 指令数、操作混合、向量化报告、算法工作量 | 是否退休了过多但可省掉的工作 |

下面的 simpleperf 采样示例用 CPU cycles 定位热点函数。它用于归因，不参与一级百分比计算。

```bash
adb shell simpleperf record \
  -p <PID> \
  -e cpu-cycles:u \
  -g \
  --duration 10 \
  -o /data/local/tmp/topdown-hot.data

adb shell simpleperf report \
  -i /data/local/tmp/topdown-hot.data \
  --sort dso,symbol
```

调用栈质量取决于 unwind 信息、帧指针和运行时。硬件事件采样还可能发生 skid：记录到的 PC 会落在触发事件的指令之后。需要精确定位内存延迟时，可在设备支持的前提下评估 SPE；需要源码行时，应保留未剥离符号与匹配 build id。

### 步骤七：用 Perfetto解释运行环境

与 simpleperf 同步采集的 Perfetto trace 至少应覆盖：

- `sched_switch` 与线程状态；
- CPU frequency 与 idle；
- thermal 或 power 相关轨道；
- 业务阶段的应用 trace marker。

如果 Backend Bound 上升的那轮同时发生了迁到小核、热降频或 workload 窗口错位，应先修正实验。频率降低会改变 cycles、耗时和内存等待的相对表现；它不是某个 Topdown 类别的单一原因。

## 14.32.6 从指标到修改：保持假设可证伪

### Frontend Bound

调查顺序可采用：

1. 用 I-cache、I-TLB 和 branch 相关计数区分取指与预测；
2. 用热点地址确认问题集中在哪个二进制和函数；
3. 查看函数布局、内联膨胀、异常冷路径和间接分支；
4. 只改一个变量，再复测耗时、一级指标与二级事件。

PGO、函数重排和 BOLT 可能改善代码局部性，但 Android NDK 默认工作流不等于已经集成 BOLT。`-fno-jump-tables`、强制函数对齐或扩大内联也可能增加指令数与代码体积，不应作为固定模板。

### Backend Bound

Backend Bound 要继续拆成 memory-bound 与 core-bound。cache miss 偏高仍不足以证明 DRAM 是限制项，还要看 miss 层级、每千指令 miss、TLB、内存延迟和并行未决请求。

SoA、预取、对齐、`restrict`、向量化和软件流水都有适用条件。固定 64 字节对齐可能浪费空间，错误预取会抢带宽和 cache，`restrict` 用错会触发未定义行为。修改前应有事件或指令级证据，修改后应同时检查耗时与副作用。

### Bad Speculation

分支无关写法不保证更快。它可能引入更多指令、额外 load，或阻碍编译器生成目标核更合适的代码。先找到高错误率分支，再用真实输入分布比较分支版、查表版或条件选择版。

### Retiring

Retiring 占比高说明流水线大部分可计量 slot 在退休操作，不代表这些操作都值得执行。解码同一数据两次、复制多余缓冲区或使用标量循环，都可能产生很高的 Retiring。此时应把 instructions、业务工作量与耗时一起看。

## 14.32.7 常见失真来源

### 异构 CPU 聚合

Android SoC 常有多种 CPU 核。不同簇的事件支持、流水线宽度和公式可能不同。按 SoC 汇总 raw count 后套一个公式，会把不同物理含义的计数混在一起。使用 `--per-core` 保存原始结果，并按同构簇分别解释。

### 计数器复用

事件数超过 PMU 可用计数器后，内核会进行时间复用。缩放计数可估计总量，却不能恢复事件间完全同步的关系。Topdown 公式依赖多个事件的比值，group 和可重复 workload 很重要。

### 调度、DVFS 与热状态

线程迁核会更换 PMU 语义；频率变化会改变周期分母；热节流会改变 workload 进度。Perfetto 的调度与频率轨道应和 PMU 结果一起归档。

### 统计口径

`:u` 只统计用户态，`:k` 只统计内核态。App 的系统调用、缺页和驱动等待可能出现在内核态或睡眠时间里。报告要说明口径，不能把用户态 PMU 百分比当作端到端耗时分解。

### 样本与计数混淆

一个函数占 30% 的 samples，不表示它制造了 30% 的全部 cache miss，更不表示它占 30% 的 Backend Bound。采样周期、事件精度、skid、调用栈丢失和符号解析都会影响归因。

### 只看百分比

优化后 Backend Bound 百分比可能上升，同时总 cycles 大幅下降。这可能是其他类别下降得更快。每轮都要同时保存墙钟耗时、cycles、instructions、绝对事件数和派生百分比。

## 14.32.8 审校结论

Android 17 上可执行的可靠路径是：

1. 用 `simpleperf list raw` 识别目标 CPU 暴露的事件；
2. 用 `simpleperf stat` 取得按核、同窗口的计数；
3. 只采用目标 CPU telemetry specification 中的公式；
4. 用 `record/report` 或 SPE 把方向定位到代码与数据访问；
5. 用 Perfetto核对调度、频率、idle、热状态和业务窗口；
6. 每次修改后复测端到端耗时、绝对计数与派生指标。

缺少 CPU 专属公式时，保留“前端 stall 事件升高”“分支错误增加”这类可核验描述，比生成看似完整的四个百分比更可靠。

## 参考资料

- [A Top-Down Method for Performance Analysis and Counters Architecture（ISPASS 2014）](https://cris.haifa.ac.il/en/publications/a-top-down-method-for-performance-analysis-and-counters-architect/)
- [AOSP android-17.0.0_r1：simpleperf](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/)
- [AOSP android-17.0.0_r1：simpleperf 命令参考](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/executable_commands_reference.md)
- [AOSP android-17.0.0_r1：cmd_stat.cpp](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/cmd_stat.cpp)
- [AOSP android-17.0.0_r1：cmd_list.cpp](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/cmd_list.cpp)
- [AOSP android-17.0.0_r1：Arm64 PMU 事件表](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table.json)
- [Android Developers：Simpleperf](https://developer.android.com/ndk/guides/simpleperf)
- [Arm：Topdown Methodology L1 Events](https://learn.arm.com/learning-paths/servers-and-cloud-computing/triggering-pmu-events-2/topdown/)
- [Arm：Telemetry Solution / topdown-tool](https://learn.arm.com/install-guides/topdown-tool/)
- [Arm：Neoverse V1 Top-down Methodology](https://developer.arm.com/community/arm-community-blogs/b/servers-and-cloud-computing-blog/posts/arm-neoverse-v1-top-down-methodology)
- [Arm：Arm 与 Intel Topdown 对照](https://learn.arm.com/learning-paths/cross-platform/topdown-compare/2-code-examples/)
- [Arm Telemetry Solution：Neoverse V1 r1p2 指标定义](https://gitlab.arm.com/telemetry-solution/telemetry-solution/-/blob/main/data/pmu/cpu/specifications/neoverse/neoverse_v1_r1p2_pmu.json)
- [Perfetto：TraceConfig](https://perfetto.dev/docs/concepts/config)

## 元信息

- **适用读者**：Android 系统/性能工程师，需要 CPU 微架构视角优化 hot path。
- **前置知识**：参见 5.28（CPU 调度）、14.24（simpleperf 基础）。
- **平台锚点**：Android 17 / API 37 / `android-17.0.0_r1`。
