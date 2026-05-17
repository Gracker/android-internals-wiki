---
title: Simpleperf
chapter: '14.2'
section: '14.2'
status: finalized
reviewed_date: '2026-04-15'
reviewed_by: openclaw-task6
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 5.0 (API 21) - Android 16 (API 36)
last_verified: '2026-04-22'
last_verified_against: NDK r29 simpleperf docs + Perfetto external format docs + Android profileable docs
confidence: high
sources:
- type: official
  path: android.googlesource.com/platform/system/extras/+/master/simpleperf/doc/README.md
- type: official
  path: developer.android.com/ndk/guides/simpleperf
- type: official
  path: perfetto.dev/docs/getting-started/other-formats
- type: blog
  path: 'Web research: simpleperf usage guide 2025-2026'
tags:
- simpleperf
- pmu
- cpu-profiling
- flamegraph
- native-profiling
related_chapters:
- '13.1'
- '13.2'
- '13.6'
- '14.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task6_result: pass-light-edit
task9_result: pass-tech-review
task2b_result: fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-04-20"
last_task9_at: "2026-04-20T03:17:47+08:00"
last_task2b_at: "2026-04-22T08:06:44+08:00"
last_task6_audit: "2026-05-17"
last_task6_audit_log: "logs/review/2026-05-17-15-audit.md"
---
# Simpleperf

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Simpleperf 是什么：Android 的 CPU profiling 工具（基于 Linux perf）
- 🔹 基本用法：simpleperf record / simpleperf report
- 🔹 采样类型：cpu-clock、task-clock、硬件 PMU 事件
- 🔹 火焰图生成与解读：FlameGraph / Speedscope
- 🔹 与 Perfetto callstack sampling 的对比

### 扩展（可选深入）

- 🔸 Simpleperf 用于 Native 代码性能分析
- 🔸 内核符号解析与 kallsyms

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Simpleperf

在 Perfetto 中分析性能问题时，我们经常能定位到某个线程 CPU 占用很高——比如主线程有一段很长的 Running 状态，或者 RenderThread 耗时异常。但 Perfetto 的 atrace 事件只能看到系统级别的函数调用（如 `Choreographer#doFrame`、`draw`），无法告诉我们具体是 App 代码中的哪个方法吃掉了 CPU。

这时候就需要 CPU profiling 工具了。Android Studio Profiler 的 Callstack Sample 功能底层用的就是 Simpleperf（详见 14.1 节），但 IDE 集成的方案有时不够灵活——比如需要在 CI 环境中自动采集、需要 profiling 系统进程、或者需要使用特定的硬件 PMU 事件做深度分析。这些场景下，命令行的 Simpleperf 是不可替代的。

Simpleperf 是 Android NDK 中自带的 CPU profiling 工具，它的设计思路来源于 Linux 的 `perf` 工具，但针对 Android 做了大量适配：能识别 APK 内嵌的 so 库、能生成带符号解析的 HTML 报告，Android 9+ 还能直接采样解释执行和 JIT 的 Java/Kotlin 栈。Android 7-8 对 Java 层的支持还停留在 fully compiled code，Android 5-6 基本以 Native/C++ 采样为主。如果我们在 Linux 上用过 `perf record` + `perf report` 的工作流，上手 Simpleperf 会非常自然。

[已验证: 官方文档, developer.android.com/ndk/guides/simpleperf]

## Simpleperf 的工作原理

理解 Simpleperf 的采样机制，有助于判断分析结果的边界。

Simpleperf 基于 Linux 内核的 `perf_event_open` 系统调用。这个系统调用允许用户态程序请求内核定期采样 CPU 的状态——具体来说，内核会以一定的频率（比如每秒 4000 次）中断正在运行的线程，记录当前的调用栈和程序计数器（PC）。采样的频率越高，结果越精确，但开销也越大。

整个流程是这样的：Simpleperf 向内核注册采样事件，内核按频率触发中断，中断处理函数收集当前 CPU 状态（PC、调用栈），Simpleperf 将收集到的样本写入 `perf.data` 文件。最后我们用 `simpleperf report` 分析这个文件，就能看到各个函数被采样到的频率——频率越高，说明 CPU 在这个函数上花的时间越多。

Simpleperf 是**统计性采样**，不是全量追踪。它记录的是"CPU 在哪些函数上花了时间"的概率分布，而不是每一次函数调用的精确耗时。对于执行频率非常低但每次都很慢的函数，Simpleperf 可能采样不到。如果需要精确追踪每一帧每个函数的耗时，应该用 AS Profiler 的 Java Method Trace（详见 14.1 节）。

[已验证: 官方文档, android.googlesource.com/platform/system/extras/+/master/simpleperf/README.md]

## 基本用法

### 准备工作

使用 Simpleperf 之前，需要先确认设备与 App 是否满足采样权限。

NDK 环境要先就位。Simpleperf 的可执行文件在 NDK 目录的 `simpleperf/` 子目录下，随 NDK 一起安装。

App 侧的权限边界要按版本看。debug build 自带 `debuggable`，本地排查最省事。release build 的工作流从 Android 10 开始明显变好，可以在 `AndroidManifest.xml` 里声明 `<profileable android:shell="true" />`，adb 下发的 simpleperf 会转调系统镜像里的 simpleperf 做采样。Android 8-9 如果没有 root，常见做法是保留 `debuggable` 并配合 `wrap.sh`；再早的版本，或者需要看系统进程、内核栈时，通常要 root 或 userdebug / eng 设备。

[已验证: 官方文档, developer.android.com/topic/performance/profileable]

### 版本能力边界

| Android 版本 | Java/Kotlin 栈 | release build 入口 | 常见限制 |
|------|----------------|--------------------|----------|
| Android 5-6 | 以 Native/C++ 为主，Java 栈基本不可用 | debuggable 或 root | Android 7 之前的内核经常过旧，DWARF call graph 能力也更受限 |
| Android 7-8 | 只支持 fully compiled Java | debuggable；Android 8 release 常配合 `wrap.sh`；root 更稳妥 | 解释执行与 JIT Java 栈还拿不到 |
| Android 9 | 支持 interpreted / JIT / compiled Java | debuggable 或 root | `profileable from shell` 还没进入公开工作流 |
| Android 10+ | 支持 interpreted / JIT / compiled Java | debug build，或声明 `<profileable android:shell="true" />` 的 release build | 非 root 设备仍受 shell / profileable 边界限制 |

`--trace-offcpu` 还取决于内核能力，文档给出的门槛是 kernel 4.2+。PMU 事件是否可用，则受 SoC 和 kernel 配置影响。

[已验证: NDK simpleperf `doc/README.md` + `doc/android_application_profiling.md`]

### simpleperf stat：快速查看事件计数

如果想快速了解某个进程的 CPU 活动概况，`simpleperf stat` 是最轻量的入口：

```bash
# 统计某个进程的 CPU 事件，持续 5 秒
adb shell simpleperf stat -p <pid> --duration 5
```

输出类似这样：

```
Performance counter statistics:

  3,456,789  cpu-cycles  # CPU 周期数
    987,654  instructions  # 指令数（IPC = 0.29）
     45,678  cache-references  # 缓存引用
      3,456  cache-misses  # 缓存未命中（命中率 92.4%）
```

`stat` 命令不会记录调用栈，只给出事件的总计数。它适合在做深度分析之前快速确认：这个进程的 CPU 活动是否正常？IPC（Instructions Per Cycle）是不是特别低？缓存命中率有没有问题？

[已验证: 官方文档, android.googlesource.com NDK simpleperf stat 用法]

### simpleperf record：采集调用栈样本

`simpleperf record` 是最核心的命令，它会采集调用栈样本并写入 `perf.data` 文件：

```bash
# 最常用的方式：对指定 App 采样 10 秒
python <ndk-path>/simpleperf/app_profiler.py \
    --app com.example.myapp \
    -r "-g --duration 10"
```

这里我们用的是 NDK 提供的 `app_profiler.py` 脚本，而不是直接调用 `simpleperf record`。原因在于 `app_profiler.py` 会自动处理很多琐碎的事情：把 Simpleperf 推送到设备、设置正确的权限、找到目标进程、启动采样、完成后拉取 `perf.data` 文件。直接用 `simpleperf record` 当然也可以，但需要手动处理这些步骤。

关键参数说明：

- `-g`：记录调用图（call graph）。这是生成火焰图的前提。Simpleperf 支持两种调用栈展开方式：DWARF-based（默认，准确但有开销）和 frame-pointer-based（需要编译时加 `-fno-omit-frame-pointer`，开销更低）。
- `--duration N`：采样持续 N 秒。
- `-e <event>`：指定采样事件，下一节详细讲。
- `-p <pid>`：指定目标进程 PID。
- `--trace-offcpu`：同时记录线程离开 CPU 的时间（off-CPU profiling），对于分析线程阻塞很有用。

如果不想用 Python 脚本，也可以直接通过 adb shell 调用：

```bash
# 直接在设备上执行（需要 root 或 debuggable/profileable App）
adb shell simpleperf record -p <pid> --call-graph dwarf --duration 10 -o /data/local/tmp/perf.data

# 然后拉取数据文件
adb pull /data/local/tmp/perf.data .
```

[已验证: 官方文档, developer.android.com/ndk/guides/simpleperf#record]

### simpleperf report：分析采样数据

采集完 `perf.data` 后，下一步是分析。最基本的方式是命令行报告：

```bash
# 按函数排序，显示每个函数被采样的次数和占比
python <ndk-path>/simpleperf/report.py -i perf.data --symfs binary_cache
```

输出类似：

```
Overhead  Command    Shared Object        Symbol
  35.2%   myapp      libmyapp.so          myapp::Renderer::drawFrame()
  18.7%   myapp      libmyapp.so          myapp::Scene::update()
  12.1%   myapp      libmyapp.so          myapp::Mesh::transform()
   8.4%   myapp      libart.so            art::interpreter::Execute()
   ...
```

从这个结果可以直接定位首要热点：`Renderer::drawFrame()` 占了 35% 的 CPU 时间。`--symfs binary_cache` 参数告诉 Simpleperf 去哪里找带调试符号的二进制文件，这决定报告能否显示有意义的函数名。

不过命令行报告对于复杂的调用关系不够直观。实际分析中我们更多使用火焰图或 HTML 报告，后面会详细讲。

[已验证: 官方文档, android.googlesource.com NDK simpleperf report 用法]

## 采样类型：CPU 时间 vs 硬件 PMU 事件

Simpleperf 的一大优势在于它不仅能采样 CPU 时间，还能利用 ARM 处理器的 PMU（Performance Monitoring Unit）硬件事件做深度分析。理解不同采样类型的区别，是用好 Simpleperf 的关键。

### 软件事件：cpu-clock 和 task-clock

默认情况下，`simpleperf record` 使用 `cpu-cycles` 事件采样。但在按时间看热点或做 off-CPU 分析时，`cpu-clock` 和 `task-clock` 更常见：

- **cpu-cycles**：CPU 周期数。它直接反映某段代码消耗了多少时钟周期，适合找 CPU 密集型热点。
- **task-clock**：目标 task 真正被调度运行的 on-CPU 时间，单位纳秒。它只在目标线程占用 CPU 时累计。
- **cpu-clock**：软件时钟事件，sample period 表示经过的纳秒数。Simpleperf 在 `--trace-offcpu` 模式下会用它生成 on-CPU 样本。

`task-clock` 和 `cpu-clock` 都是时间型事件。它们单独使用时只能描述 on-CPU 样本，阻塞、等待 I/O、等锁、被别的线程抢占出去的那段时间，要靠 `--trace-offcpu` 追加的 `sched_switch` 样本和 context switch 记录来分析。

`--trace-offcpu` 的计算基础是调度切换。simpleperf 订阅 `sched_switch` 后，拿线程被换出 CPU 到下一次被换回来的时间差，折算成 off-CPU 样本并写进 profile。火焰图里看到的等待热点，就是这样补出来的。

只想找 CPU 热点时，默认的 `cpu-cycles` 就够用。要按时间观察线程执行，或需要把 on-CPU / off-CPU 一起看时，再切到 `task-clock` 或 `cpu-clock`。

### 硬件 PMU 事件

ARM 处理器的 PMU 提供了大量硬件级事件，常见的有：

| 事件 | 含义 | 分析场景 |
|------|------|----------|
| `cpu-cycles` | CPU 周期 | CPU 热点定位（默认） |
| `instructions` | 执行的指令数 | 计算 IPC |
| `cache-references` | 缓存访问次数 | 内存访问模式 |
| `cache-misses` | 缓存未命中 | 内存瓶颈分析 |
| `branch-misses` | 分支预测失败 | 分支密集代码优化 |
| `bus-cycles` | 总线周期 | 总线带宽分析 |

使用方法：

```bash
# 同时采样 CPU 周期和缓存未命中
python <ndk-path>/simpleperf/app_profiler.py \
    --app com.example.myapp \
    -r "-g --duration 10 -e cpu-cycles,cache-misses,cache-references"
```

在分析结果时，如果某个函数的 cache-misses 占比异常高，即使它的 cpu-cycles 占比不高，也值得关注——因为缓存未命中意味着 CPU 在等内存，这部分时间在 cpu-cycles 采样中可能被分散到调用者的样本中，不容易发现。

这组事件有权限边界。user build 设备通常把 `kernel.perf_event_paranoid` 设得很高，非 Root shell 很难直接访问 `cache-misses`、`branch-misses` 这类硬件 PMU 事件。`profileable` 和 `debuggable` 解决的是 App 侧采样入口，不会放开 PMU。遇到 `EACCES` 或 `Permission denied` 时，先回到 `cpu-clock` / `task-clock`；要看真实 PMU，再换 Root、userdebug 或 eng 设备。

可以用以下命令查看设备上支持的所有事件：

```bash
adb shell simpleperf list
```

[已验证: 官方文档, android.googlesource.com NDK simpleperf event list]
[待验证: 不同 ARM SoC 上 PMU 事件名称可能不完全一致，MTK/高通/三星有差异]

## 火焰图生成与解读

命令行的 `report` 输出虽然精确，但面对几百个函数、多层嵌套的调用栈时，很难快速把握整体情况。火焰图（Flame Graph）是解决这个问题的最佳可视化方式。

### 什么是火焰图

火焰图是一种将采样数据可视化的方法，由 Brendan Gregg 在 2011 年提出。它的核心思路是：每一层代表一个函数调用，宽度代表这个函数（及其子调用）被采样到的频率，宽度越大说明 CPU 在这里花的时间越多。整个图形看起来像倒置的火焰——底部宽（入口函数），顶部窄（叶子函数）。

火焰图有一个重要特性：**调用关系是从下到上的**。最下面一行通常是入口函数（如 `main` 或线程的入口），上面每一层都是被调用的函数。如果同一层有多个方块并排，说明这个函数被多个不同的调用者调用。

### 使用 report_html.py 生成 HTML 报告

最方便的方式是用 Simpleperf 自带的 `report_html.py` 脚本：

```bash
python <ndk-path>/simpleperf/report_html.py \
    -i perf.data \
    --symfs binary_cache \
    -o report.html
```

打开生成的 `report.html`，会看到一个包含多个 Tab 的交互式页面：

- **Flamegraph Tab**：交互式火焰图，支持点击放大、搜索、按线程/库过滤
- **Sample Table Tab**：按函数排序的采样表
- **Chart Statistics Tab**：按时间分布的采样统计

[图：report_html.py 生成的 HTML 报告截图，标注火焰图 Tab 和关键的 hot path 区域]

### 使用 Speedscope 查看火焰图

如果偏好更轻量的在线工具，可以把 Simpleperf 的数据转换后用 [Speedscope](https://www.speedscope.app/) 查看：

```bash
# 方法一：转为 folded stacks 格式
python <ndk-path>/simpleperf/stackcollapse.py \
    -i perf.data --symfs binary_cache > out.perf.folded

# 方法二：转为 perf script 格式
python <ndk-path>/simpleperf/report_sample.py \
    --symfs binary_cache > out.perf
```

然后打开 speedscope.app，直接拖入生成的文件即可。Speedscope 提供三种视图：Time Order（按时间顺序）、Left Heavy（左重排序，将相同调用栈合并）和 Sandwich（调用者/被调用者视图）。Left Heavy 视图特别适合快速定位热点——它会把所有相似的调用栈合并在一起，不管它们出现在时间线的哪个位置。

### 火焰图解读技巧

解读火焰图时，有几个经验值得注意：

第一，**看"平台"**。火焰图中如果一个函数上方有一个很宽的平台（plateau），说明这个函数本身（不含子调用）消耗了大量 CPU。这种"自顶向下"的热点是最容易优化的——直接看这个函数在做什么，是否有优化空间。

第二，**看"尖塔"**。如果某个调用路径从底部一直延伸到顶部，形成一个又窄又高的塔，说明这是一个深层的调用链，其中某个叶子函数是热点。这种情况需要沿着塔逐层查看，找到最窄但最热的那一层。

第三，**对比采样数**。火焰图中每个方块的宽度代表采样数，鼠标悬停时会显示具体数值。优化之前先记录总采样数和热点函数的采样数，优化之后再跑一次，对比数值变化，用数据说话。

[已验证: 官方文档, android.googlesource.com NDK simpleperf visualization]

## 与 Perfetto Callstack Sampling 的对比

在 Android 性能分析的语境下，Simpleperf 和 Perfetto 的 callstack sampling 功能有相当程度的重叠——两者底层都使用 `perf_event_open` 系统调用来采集 CPU 调用栈。但它们的定位和使用场景有明显区别。

### 功能对比

从分析视角看，最核心的区别在于"深度"和"广度"的权衡。

Simpleperf 是**深度型**工具。它专注于回答"CPU 时间花在了哪里"这一个问题。它的采样更灵活（支持各种 PMU 事件），符号解析更完善（尤其是 Native 代码），火焰图是原生输出。当我们需要深入分析某个函数的热点、对比不同编译选项的性能差异、或者用 cache-misses 等硬件事件做微架构级分析时，Simpleperf 是更好的选择。

Perfetto 是**广度型**工具。它的 callstack sampling 只是众多数据源之一，可以和 ftrace、atrace、proc stats 等数据放在同一条时间线上查看。分析时不仅能看到"CPU 花在了哪里"，还能同时看到"这时候系统在做什么"、"GC 是否在运行"、"是否发生了调度切换"。当需要理解一个性能问题的上下文——比如"这个函数慢是因为它在和另一个进程的 Binder 调用竞争 CPU"——Perfetto 提供的全景视角无可替代。

| 维度 | Simpleperf | Perfetto Callstack Sampling |
|------|-----------|---------------------------|
| 核心定位 | CPU 热点分析 | 系统全景追踪 + CPU 热点 |
| 采样灵活性 | 高（PMU 事件、off-CPU、自定义频率） | 中（固定几种配置） |
| 符号解析 | 强（Native + Java，支持 binary_cache） | 中（依赖调试符号部署） |
| 火焰图 | 原生支持（HTML / Speedscope） | UI 内嵌，可交互 |
| 系统上下文 | 几乎无（只看 CPU 采样） | 丰富（ftrace/atrace/proc） |
| SQL 分析 | 不支持 | PerfettoSQL 支持复杂查询 |
| 开销 | 较低（仅采样） | 中等（多数据源叠加） |
| 典型场景 | 定位 CPU 密集型热点、微架构分析 | 理解性能问题的上下文和因果链 |

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-profiler + developer.android.com/ndk/guides/simpleperf]

### 什么时候用哪个

用一个实际场景来说明：假设我们在 Perfetto 中发现主线程有一段 50ms 的 Running 状态，导致了掉帧。

**第一步**：在 Perfetto 中看上下文。这段 Running 期间，其他线程在做什么？有没有 GC？有没有 Binder 调用？如果 Perfetto 中的 atrace 事件已经能定位到具体的函数（比如 `Choreographer#doFrame` 里面的某个 section），问题就清楚了。

**第二步**：如果 Perfetto 只能告诉我们"主线程在执行用户代码"，但不知道是哪个方法，那就需要 CPU profiling。这时用 Simpleperf 的 `record` + 火焰图，能直接看到函数级别的热点。

**第三步**：如果火焰图显示热点在 Native 代码中（比如 Skia 的光栅化函数），而且需要进一步分析是不是缓存问题，就可以用 Simpleperf 的 PMU 事件（`cache-misses` 等）做更深入的分析。

简单来说：Perfetto 回答"发生了什么"，Simpleperf 回答"为什么这么慢"。两者的配合使用才是最有效的工作流。

[已验证: 官方文档, 综合分析]

## Simpleperf 用于 Native 代码性能分析

Simpleperf 最初是为 Native（C/C++）代码 profiling 设计的，在 Native 代码的分析上它有着天然的优势。对于 Android Framework 开发者或使用 JNI/NDK 的 App 开发者，Simpleperf 是分析 Native 代码性能的首选工具。

### 符号解析

Native 代码 profiling 最常见的障碍是：火焰图中只看到一堆十六进制地址，看不到函数名。这通常是因为符号信息缺失。

解决方法是确保 Simpleperf 能找到带调试符号的 so 文件。如果使用的是 `app_profiler.py`，它会自动在 `binary_cache/` 目录中收集需要的文件。如果需要手动指定：

```bash
# 构建 binary_cache
python <ndk-path>/simpleperf/binary_cache_builder.py \
    -i perf.data \
    -lib <path/to/unstripped/libs>
```

这里的 `-lib` 参数指向未 strip 的 so 文件目录。对于 release build，通常需要在构建产物中找到带符号的版本（Gradle 的 `intermediates` 或 `merged_native_libs` 目录下）。

### off-CPU Profiling

除了分析"CPU 在忙什么"，有时候我们还要看线程离开 CPU 以后去了哪里。`--trace-offcpu` 会在 on-CPU samples 之外，再记录 `sched:sched_switch` 和 context switch 数据：

```bash
python <ndk-path>/simpleperf/app_profiler.py \
    --app com.example.myapp \
    -r "-g -e cpu-clock:u --duration 10 --trace-offcpu"
```

`--trace-offcpu` 只允许和 `cpu-clock` 或 `task-clock` 搭配使用，文档示例默认用 `cpu-clock`。off-CPU 时间覆盖的是线程离开 CPU 到再次被调度回来之间的整段区间，其中既可能是等锁、等 I/O、等 Binder，也可能只是被其他线程抢占。

报告阶段可以切到 `on-cpu`、`off-cpu`、`on-off-cpu` 或 `mixed-on-off-cpu` 四种视图。分析 ANR、长尾卡顿、线程池饥饿时，这类样本很有用。这项能力还依赖 kernel 4.2+。

[已验证: NDK simpleperf `doc/executable_commands_reference.md` --trace-offcpu 段]
[待补充: off-CPU profiling 的火焰图解读示例，标注 on/off 区域的对比]

## 内核符号解析与 kallsyms

当 profiling 涉及内核代码（比如系统调用、驱动、调度器）时，我们需要内核符号信息才能看到有意义的函数名。Android 设备上的 `/proc/kallsyms` 文件包含了内核符号表。

默认情况下，出于安全考虑，Android 设备的 `/proc/kallsyms` 对非 root 用户不可读。需要 root 权限才能访问。如果我们有 root 设备或使用 userdebug build：

```bash
# 导出内核符号
adb shell cat /proc/kallsyms > kallsyms.txt

# 在 report 时使用
python <ndk-path>/simpleperf/report.py \
    -i perf.data --symfs binary_cache \
    --kallsyms kallsyms.txt
```

启用内核符号后，火焰图中会显示内核函数名（如 `sys_read`、`do_page_fault`、`schedule`），这对于分析系统级性能问题——比如 Binder 调用的内核侧耗时、内存分配的内核路径——非常关键。

如果无法获取 root 权限，可以使用设备的预编译内核的 symbol 文件（通常在 AOSP 对应版本的 `vmlinux` 中）。

[已验证: 官方文档, Linux perf kallsyms 用法]
[待验证: Android 16 对 /proc/kallsyms 的权限是否有变化]

## 常见问题与误区

### 误区一：火焰图中的比例就是精确的函数耗时

火焰图展示的是**采样统计**，不是精确计时。一个函数占 30% 的火焰图宽度，意思是"在所有采样样本中，有 30% 的样本落在了这个函数上"，而不是"这个函数精确地消耗了 30% 的 CPU 时间"。采样频率越高，统计越接近真实值，但永远不是精确值。

对于执行时间极短（低于采样间隔）但调用频率极高的函数，Simpleperf 的统计可能不准确。这种情况下，如果需要精确的方法级耗时，应该使用 Java Method Trace（AS Profiler 的 Instrumented Trace 模式，详见 14.1 节）。

### 误区二：Simpleperf 只能分析 C/C++ 代码

这是一个过时的认知。从 Android 9（API 28）开始，Simpleperf 已经支持对 JIT 编译和解释执行的 Java/Kotlin 代码进行采样。因此，Java 方法在火焰图中也能看到——虽然因为 JIT 内联和去优化等原因，Java 代码的调用栈可能不如 C++ 代码那么清晰完整，但对于定位 Java 层的 CPU 热点已经足够。

### 误区三：采样开销可以忽略不计

Simpleperf 的默认采样频率是 4000 Hz（每秒 4000 次）。在大多数情况下这个开销可以接受（通常 < 5%），但如果同时启用 DWARF 调用栈展开（`-g`）和 PMU 事件，开销可能上升到 10-15%。对于延迟极度敏感的场景（如游戏渲染、实时音频处理），建议降低采样频率（如 `-f 1000`）或使用 frame-pointer-based 展开方式来减小开销。

### 误区四：profileable 和 debuggable 的 profiling 结果一样

profileable 模式下，Simpleperf 只能采集 CPU 采样数据，无法录制 Java/Kotlin 的内存分配（allocation tracking）、无法抓取 heap dump。这些功能需要 debuggable 模式。但对于 CPU profiling 来说，profileable 模式下的结果和 debuggable 模式一样准确；因为跳过了调试器的额外开销，profileable 模式下的数据反而更接近真实性能。

## 在 Perfetto 中的表现

虽然 Simpleperf 自成体系，但有些场景需要把 CPU 采样接到别的查看器里。这里把“导出格式”和“原生消费端”分开看：

- **Firefox Profiler 路径**：用 `gecko_profile_generator.py` 把 `perf.data` 转成 Gecko JSON，交给 `profiler.firefox.com`。这是 Gecko Profile 的原生入口，火焰图和多线程时间轴体验更完整。
- **Perfetto 直接导入路径**：用 `simpleperf report-sample --protobuf -i perf.data -o report_sample.trace` 导出 simpleperf proto，再拖到 `ui.perfetto.dev`。要和 system trace、Perfetto SQL 放在一起看时，优先选这条。
- **perf script / folded stack 路径**：用 `report_sample.py` 导出文本格式，再接 FlameGraph、Speedscope 或 Perfetto 支持的 perf script importer。

Perfetto 的 external format importer 也能读取 Firefox Profiler JSON，但支持点集中在 CPU samples。要避开格式兼容差异，Gecko JSON 直接给 Firefox Profiler；要在 Perfetto 里做 SQL 查询或和系统 trace 联查时，用 simpleperf proto 更稳妥。

[已验证: Perfetto `other-formats` 文档 + NDK simpleperf `view_the_profile.md` / `scripts_reference.md`]

[图：Perfetto UI 中的 CPU Callstack 视图，标注火焰图入口和数据来源说明]

## 参考资料

- Simpleperf 官方文档：[developer.android.com/ndk/guides/simpleperf](https://developer.android.com/ndk/guides/simpleperf)
- AOSP Simpleperf 源码与 README：[android.googlesource.com/platform/system/extras/+/master/simpleperf/](https://android.googlesource.com/platform/system/extras/+/master/simpleperf/)
- Brendan Gregg 火焰图原始论文与工具：[www.brendangregg.com/flamegraphs.html](http://www.brendangregg.com/flamegraphs.html)
- Speedscope 在线工具：[www.speedscope.app](https://www.speedscope.app)
- Firefox Profiler：[profiler.firefox.com](https://profiler.firefox.com/)
- Perfetto CPU Profiler 文档：[perfetto.dev/docs/data-sources/cpu-profiler](https://perfetto.dev/docs/data-sources/cpu-profiler)
- profileable 清单配置：[developer.android.com/topic/performance/profileable](https://developer.android.com/topic/performance/profileable)
