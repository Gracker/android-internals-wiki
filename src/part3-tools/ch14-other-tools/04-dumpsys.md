---
title: dumpsys 系列命令
chapter: '14.4'
section: '14.4'
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 6.0 (API 23) - Android 16 (API 36)
last_verified: '2026-04-15'
last_verified_against: AOSP android-16.0.0_r1
confidence: medium
sources:
- type: aosp
  path: frameworks/native/cmds/dumpsys/
- type: official
  path: developer.android.com/studio/profile/battery-historian
- type: blog
  path: source.android.com/docs/core/graphics/surfaceflinger-windowmanager
tags:
- dumpsys
- meminfo
- gfxinfo
- activity
- window
- batterystats
- SurfaceFlinger
- debugging
related_chapters:
- '4.1'
- '4.5'
- '7.3'
- '13.1'
- '14.1'
task9_result: "needs-rework"
last_task2b_at: "2026-04-30T17:46:37.750688"
task9_reviewed_date: "2026-05-24"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-24T01:38:24+08:00"
repaired_date: "2026-04-26"
repaired_by: openclaw-task2b
review_notes: "2026-05-23 task9 idle audit: found P0 source path error (`LayerHierarchyBuilder.h` does not exist; class is defined in `LayerHierarchy.h`); reopened to Task2B."
last_task9_audit: "2026-05-23"
last_task9_audit_log: "logs/deep-review/2026-05-23-01-audit.md"
status: "ready-for-review"
pipeline_stage: "task2b_pending"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "pending"
task2b_result: "fixed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-24"
task6_result: "pass-light-edit"
last_task6_at: "2026-05-24T01:08:00+08:00"
last_task6_review_log: "logs/review/2026-05-24-01-review.md"
task6_review_notes: "2026-05-24 Task6 revisiting review: pass-light-edit。L1/L2 小修 3 处（清理 AIW 编辑注释、标题措辞、无条件量化收益）。无新增 Task6 回炉；Task9 P0 已由 Task2B 修复，等待 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-05-24-01-deep-review.md"
task9_review_notes: "2026-05-24 Task9 deep review: needs-rework。P0 0 / P1 1 / P2 0；gfxinfo framestats 版本边界需修正：FrameDeadline/FrameInterval 并非 Android 14+，WorkloadTarget 为 Android 16+；详见 logs/deep-review/2026-05-24-01-deep-review.md。"
---
# dumpsys 系列命令

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 dumpsys activity：查看 Activity 栈、进程信息、ANR 信息
- 🔹 dumpsys meminfo：查看系统和进程内存使用
- 🔹 dumpsys gfxinfo：查看帧渲染统计
- 🔹 dumpsys window：查看窗口层级和焦点
- 🔹 dumpsys batterystats：查看电池使用统计
- 🔹 dumpsys SurfaceFlinger：查看 Layer 信息和合成状态

### 扩展（可选深入）

- 🔸 dumpsys package / dumpsys alarm / dumpsys jobscheduler
- 🔸 自定义 Service 实现 dump 接口

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要 dumpsys

在分析 Android 性能问题的过程中，我们经常需要快速了解系统某一时刻的"状态快照"——比如某个进程占用了多少内存、当前屏幕上叠加了多少个 Layer、哪个窗口持有焦点、最近 120 帧的渲染耗时分布如何。Perfetto 可以告诉我们"过程"（事情是怎么一步步发生的），但如果我们需要的是一个"截面"（此刻系统长什么样），dumpsys 更适合先取状态快照。

dumpsys 会遍历 Android 系统中所有注册到 ServiceManager 的系统服务，调用每个服务的 `dump()` 方法，把服务内部状态以文本形式输出到终端。

每个系统服务都实现了自己的 `dump()` 方法，因此 dumpsys 的输出覆盖了 Android 系统的多个关键面向，从 Activity 栈到电池统计，从内存分配到图形合成，都能拿到对应的状态快照。

在设备上运行 `adb shell dumpsys -l` 就能列出完整子命令列表；这里聚焦性能分析中最常用的六个子命令，逐个讲清楚它的用途、输出结构、关键指标的含义，以及在实际性能分析中怎么用。

[已验证: AOSP android-16.0.0_r1, frameworks/native/cmds/dumpsys/dumpsys.cpp]

## dumpsys activity：Activity 栈、进程与 ANR 信息

### 基本用法

`dumpsys activity` 是 ActivityManagerService（AMS）的状态输出窗口。在性能分析中，我们主要关注它的三个子项：

- `dumpsys activity activities`：查看所有 Task 和 Activity 的栈信息
- `dumpsys activity processes`：查看所有进程的优先级和状态
- `dumpsys activity exit-info`：查看进程退出历史，ANR / Crash / LMK 归因优先从这里取证
- `dumpsys activity lastanr`：遗留快照，只保留最近一次 ANR，作为没有 `exit-info` 历史时的兜底

### 读懂 Activity 栈

当我们怀疑某个场景的卡顿或 ANR 与 Activity 生命周期有关时，Activity 栈是第一手线索。执行 `adb shell dumpsys activity activities` 后，输出会按照 Task 分组，每个 Task 下列出从底到顶的 Activity 栈。关键的几个字段：

- `Task`（旧版资料中常写作 `TaskRecord`）中的 `affinity` 和 `taskId` 告诉我们这个 Task 属于哪个应用
- `ActivityRecord` 中的 `state` 表示 Activity 当前状态（resumed、paused、stopped 等）
- `mFocusedActivity` 和 `mFocusedApp` 标记当前获得焦点的 Activity 和应用

在分析启动速度时，我们可以反复执行这个命令，观察目标 Activity 从 `initiating` 到 `resumed` 的状态变化，来确认各阶段的耗时是否正常。

### 进程优先级与 ANR

`dumpsys activity processes` 会列出所有进程的 `oom_adj` 值和调度优先级。当分析 Low Memory Killer 误杀问题时，这里的 `oom_adj` 值就是最直接的证据。AOSP `ProcessList.java` 中定义了各级别的 `adj` 值。以 Android 10+ 为例，`FOREGROUND_APP_ADJ=0`（前台进程，优先级最高）、`VISIBLE_APP_ADJ=100`（可见但非前台）、`PERCEPTIBLE_APP_ADJ=200`（可感知但不可见）。Android 10 之前的常见资料里，`VISIBLE_APP_ADJ` 通常写成 `1`，只是数值尺度不同，优先级顺序没有变。`oom_adj` 值越低，进程优先级越高，越不容易被 LMK 杀掉。

举个例子：如果一个 App 当前在前台展示界面，本应处于 `adj=0`（FOREGROUND），但 dumpsys 显示它的 `oom_adj=100`（VISIBLE），说明系统的进程优先级计算出了问题——进程被错误降级，LMK 在内存紧张时会优先杀掉它。

Android 11+ 的 ANR 快照优先看 `dumpsys activity exit-info`。它来自 `ApplicationExitInfo` 历史记录，同一包名下可以保留多次退出原因，适合区分 `REASON_ANR`、Crash、LMK、用户强停等场景，也能和系统记录的 trace 文件路径、进程状态放在一起看。

```bash
# 查看全部进程退出历史
adb shell dumpsys activity exit-info

# 查看指定包名的退出历史
adb shell dumpsys activity exit-info <package_name>
```

`dumpsys activity lastanr` 仍可作为遗留兜底：它只保留最近一次 ANR 的文本快照，设备重启、日志轮转或新 ANR 出现后都可能覆盖旧现场。排查线上问题时，`exit-info` 负责确认“这个进程为什么退出”，Perfetto / bugreport / ANR traces 负责还原“退出前线程在等什么”。

[已验证: AOSP android-16.0.0_r1, `frameworks/base/services/core/java/com/android/server/wm/Task.java`、`ActivityRecord.java`；`ActivityManagerService.java` 分发 `exit-info` 到 `mAppExitInfoTracker.dumpHistoryProcessExitInfo()`]

## dumpsys meminfo：系统和进程内存全景

### 基本用法

`dumpsys meminfo` 是 Android 上最经典的内存分析命令。它可以查看系统全局内存概况，也可以查看单个进程的详细内存分布：

```bash
# 系统全局内存概况
adb shell dumpsys meminfo

# 指定进程的详细内存分布
adb shell dumpsys meminfo <package_name>

# 输出更完整的系统和进程内存明细
adb shell dumpsys meminfo -a
```

`dumpsys meminfo` 没有 `--slab` 参数。AOSP `dumpApplicationMemoryUsage()` 支持的是 `-a/-d/-c/-s/-S/-p/--unreachable/--oom/--local/--package/--checkin/--proto/--logstats` 这组参数，不包含 `--slab`。全局输出里可能包含 slab 汇总；要深入看内核 slab，先读 `/proc/meminfo` 里的 `Slab`、`SReclaimable`、`SUnreclaim`，root 或 debuggable 环境下再看 `/proc/slabinfo`。

### 关键指标：PSS、USS、Private Dirty

在 meminfo 的输出中，最核心的三个指标是 PSS、USS 和 Private Dirty。理解它们的区别，是用好这个命令的前提。

**PSS（Proportional Set Size）** 是我们最关注的指标。它衡量的是一个进程"实际占用"的物理内存。PSS 的特殊之处在于，对于被多个进程共享的内存页（比如共享库的代码段），它会按比例分摊：如果一张 4KB 的内存页被两个进程共享，每个进程的 PSS 只计入 2KB。把所有进程的 PSS 加起来，结果就接近系统实际使用的总物理内存。在判断一个 App "占了多少内存"时，PSS 是最准确的标准。

**USS（Unique Set Size）** 是进程独占的物理内存，不被任何其他进程共享。如果这个进程被杀掉，USS 这部分内存会被完全释放。USS 适合用来估算一个进程被杀掉后理论上能回收多少私有内存，也适合做线下泄漏分析和方案对比。LMKD 运行时不会去计算 USS，目标选择仍要回到 `oom_score_adj`、RSS 和 PSI 这类实时决策线索。

**Private Dirty** 是已经被修改过的私有内存页。这部分内存不能像 clean file-backed page 一样直接丢弃；在启用 zRAM 的设备上，部分脏页可能被压缩换出，并在 `dumpsys meminfo` 中体现为 `SwapPss` / `Swapped Dirty`。分析泄漏时不要只看单列，需同时看 PSS、Private Dirty、SwapPss 和设备的 zRAM 状态。

[已验证: 官方文档, developer.android.com/topic/performance/memory]

### 内存分类与性能关联

meminfo 输出把进程的内存使用分为多个类别。在性能分析中，我们需要重点关注以下几类：

**Dalvik Heap / ART Heap** 是 Java/Kotlin 对象的驻留之地。如果 `Heap Alloc` 持续增长而不回落，很可能存在内存泄漏。频繁的大对象分配则会导致 `memory churn`（内存抖动），引发频繁 GC，进而导致主线程暂停、帧丢失。在 Perfetto 中，这对应于 Main Thread 上出现的 GC slice。

**Native Heap** 是 C/C++ 代码通过 `malloc` 分配的内存。图形缓冲区（GraphicBuffer）、第三方 native 库（如图片解码库）、JNI 代码分配的对象都在这里。如果 Native Heap 增长但 ART Heap 稳定，说明泄漏发生在 native 层，需要用 `heapprofd`（§14.3）或 `ddms` 的 Native Heap Dump 来定位。

**Graphics** 包括 GL surface、纹理缓冲区、EGL 相关的图形资源。在图片密集型 App 或游戏中，这个值可能很大。如果退出一个界面后 Graphics 内存没有下降，说明纹理或 surface 没有被正确释放。

### 实战用法：追踪内存趋势

单次 dumpsys meminfo 只是一个快照。要发现内存泄漏，我们需要追踪趋势：

```bash
# 第一次抓取，记录基线
adb shell dumpsys meminfo <package_name>

# 执行一轮操作（如反复进出某个界面 20 次）

# 第二次抓取，对比变化
adb shell dumpsys meminfo <package_name>
```

比较两次输出的 `TOTAL PSS` 和 `Private Dirty`，如果数值持续上升且不回落，就是泄漏的信号。对于更精确的趋势分析，建议使用 Android Studio Memory Profiler（§14.1）连续采样，它可以把 PSS 随时间的变化画成曲线。

[来源: Obsidian Personal-Knowledge/source/Android-Jank-Debug.md]

## dumpsys gfxinfo：帧渲染统计与 Jank 定位

### 基本用法

`dumpsys gfxinfo` 是 Android 提供的帧渲染性能快照工具。它最常见的三种用法如下：

```bash
# 聚合统计（Janky frames 百分比、百分位耗时等）
adb shell dumpsys gfxinfo <package_name>

# 逐帧行时间（最近 120 帧的详细时间线）
adb shell dumpsys gfxinfo <package_name> framestats

# 重置统计（在测试前执行，确保数据干净）
adb shell dumpsys gfxinfo <package_name> reset
```

[已验证: 官方文档, developer.android.com/topic/performance/vitals/render]

### 聚合统计：快速判断渲染健康度

不带 `framestats` 参数时，gfxinfo 输出聚合指标。最重要的几个：

**Janky frames** 是超过帧预算的帧数。Android 15/16 的 HWUI 统计同时保留 legacy 判定和 deadline 判定：legacy 主要按固定帧间隔估算，deadline 判定会读取每帧的 `FrameDeadline` / `FrameInterval`，在 90Hz、120Hz、LTPO 自适应刷新率设备上更接近真实渲染预算。聚合输出里如果出现 `Number Frame deadline missed`，优先把它作为 VRR 场景的掉帧入口，再回到 Perfetto 的 FrameTimeline 核对该帧的 deadline。

**90th / 95th / 99th percentile** 是帧耗时的分位值。如果 99th percentile 是 50ms，意味着有 1% 的帧耗时超过 50ms——在 60Hz 设备上这就是连续掉 3 帧，用户能明显感知到卡顿。

**Number Slow UI thread** 告诉我们有多少帧的瓶颈在主线程——也就是 `measure`/`layout`/`draw` 阶段耗时过长。如果这个数字很高，说明我们需要优化布局层次或减少 `onDraw()` 中的计算。

**Number Slow RenderThread** 表示有多少帧的瓶颈在 RenderThread——GPU 命令提交或光栅化阶段耗时过长。如果这个数字高而 Slow UI thread 低，说明瓶颈在渲染管线的后半段，需要减少过度绘制或简化绘制指令。

### framestats：逐帧时间线

`framestats` 输出最近 120 帧的逐帧时间戳。每一行是一帧，各列代表渲染管线中的关键时间节点：`IntendedVsync`、`Vsync`、`InputEventId`、`HandleInputStart`、`AnimationStart`、`PerformTraversalsStart`、`DrawStart`、`FrameDeadline`（Android 14+ 新增）、`FrameStartTime`、`FrameInterval`（Android 14+ 新增）、`WorkloadTarget`（Android 14+ 新增）、`SyncQueued`、`SyncStart`、`IssueDrawCommandsStart`、`SwapBuffers`、`FrameCompleted`、`GpuCompleted` 等。

所有时间戳均为纳秒（ns）。固定刷新率设备上可以用 60Hz 的 16667000ns（约 16.67ms）或 120Hz 的 8333000ns（约 8.33ms）做粗略基准；VRR / ARR 设备要读每行的 `FrameInterval` 和 `FrameDeadline`，不能把整段测试都按一个固定 VSync 周期判定。

通过计算相邻时间点的差值，我们可以精确知道每一帧的时间花在了哪里。例如 `PerformTraversalsStart` 到 `DrawStart` 的差值就是主线程 `measure`/`layout` 的耗时；`SyncStart` 到 `IssueDrawCommandsStart` 是 RenderThread 执行 OpenGL 命令的时间。

在实践中，我们通常不会手动解析这些数字，而是借助工具：Android Studio 的 System Trace 可以可视化这些时间线，JankStats 库（AndroidX）可以在运行时监控并上报 Jank。

### 实战示例：定位滑动卡顿

当我们收到一个"列表滑动卡顿"的 bug 时，用 gfxinfo 可以快速判断卡顿发生在哪个阶段：

```bash
# 第一步：重置统计
adb shell dumpsys gfxinfo com.example.app reset

# 第二步：复现问题（快速滑动列表 10-15 秒）

# 第三步：抓取聚合统计
adb shell dumpsys gfxinfo com.example.app
```

如果输出显示 `Number Slow UI thread` 很高，说明是主线程做了太多工作（比如 `onBindViewHolder` 中有耗时操作）。如果 `Number Slow bitmap uploads` 很高，说明图片解码阻塞了渲染。如果 `Number Slow RenderThread` 高但 UI thread 正常，可能是因为视图层次太复杂导致 GPU 合成压力过大。

确认了阶段之后，再用 Perfetto 抓 Trace 做精确定位——gfxinfo 帮我们缩小了排查范围。

## dumpsys cpuinfo：CPU 占用快速排查

### 基本用法

`dumpsys cpuinfo` 提供系统当前各进程的 CPU 使用率快照，是快速判断"谁在吃 CPU"的第一步：

```bash
# 查看所有进程的 CPU 占用
adb shell dumpsys cpuinfo

# 持续监控（每秒刷新）
adb shell top -H -p <pid>
```

### 关键指标

输出中每行是一个进程的 CPU 占用百分比，分为几个部分：

- **User**：用户态 CPU 时间占比（应用代码执行）
- **System**：内核态 CPU 时间占比（系统调用、I/O 等待）
- **IRQ / SoftIRQ**：中断处理时间占比（硬件中断和软中断）

在性能排查中，如果一个后台进程的 CPU 占用持续超过 5%，就值得调查。常见的异常模式：

- User 占用高 → 应用层在做密集计算（如 JSON 解析、图片解码）
- System 占用高 → 大量系统调用（如频繁的 IPC、文件 I/O）
- IRQ 占用高 → 硬件中断频繁（可能是驱动问题）

`dumpsys cpuinfo` 的局限在于它只提供瞬时快照，无法看到趋势。如果需要持续监控 CPU 占用随时间的变化，建议使用 Perfetto 的 CPU 采样功能（通过 `perfetto` 命令抓取 `cpu` track），或者在终端使用 `adb shell top` 做持续观察。

如果输出里带有 `minor faults` / `major faults`，跨设备对比时要把 page size 放进测试条件。Android 15/16 已支持 16KB page size，单页覆盖范围变大后，同样访问模式下的 minor faults 次数可能低于 4KB 设备。这个数字下降不一定来自 I/O 或内存访问优化，先用 `adb shell getconf PAGESIZE` 确认页大小，再做同条件对比。

[已验证: Android 16 中 dumpsys cpuinfo 仍保留按进程输出 CPU 快照；16KB page size 设备需单独标注 page size 条件]

## dumpsys window：窗口层级与焦点

### 基本用法

```bash
# 完整的 WindowManager 状态
adb shell dumpsys window

# 窗口列表（含 Z-order）
adb shell dumpsys window windows

# DisplayContent 视角的焦点，适合 Android 15+ 和多屏场景
adb shell dumpsys window displays
adb shell dumpsys window displays | grep -E 'DisplayContent|mCurrentFocus|mFocusedApp'

# InputDispatcher 视角的焦点
adb shell dumpsys input | grep -E 'FocusedWindow|FocusedApplication'
```

### 关键信息

在性能分析中，dumpsys window 主要用于两类场景。

**第一类是确认窗口焦点。** 当用户报告"点了没反应"或"触摸不灵敏"时，优先从 `adb shell dumpsys window displays` 看每个 `DisplayContent` 下的 `mCurrentFocus` 和 `mFocusedApp`。Android 15+ 的焦点状态已经明显转向显示器维度；多屏、投屏、车机、副屏场景下，直接在全局输出里 grep `mCurrentFocus` 容易拿到非目标显示器的窗口。它们不一定一致：比如用户拉下通知栏时，`mCurrentFocus` 会切换到 SystemUI 的通知面板，但 `mFocusedApp` 仍然是之前使用的 App。

**第二类是排查 Input ANR。** `dumpsys window` 只能回答 WMS 视角的窗口状态，决定触摸事件去向的是 InputDispatcher。遇到窗口看起来有焦点、点击却没有反应的场景，要再执行 `adb shell dumpsys input`，联动查看 `FocusedWindow` 和 `FocusedApplication`。如果两边不一致，或者 InputDispatcher 指向了意料之外的窗口，再回头检查 `NOT_TOUCHABLE`、InputChannel 和覆盖层拦截。

`dumpsys window` 的输出还包含 Z-order 信息，窗口从上到下排列。在排查覆盖层问题时（比如 Dialog 没有正确 dismiss 导致遮挡了底下的 Activity），Z-order 列表可以直观看到哪些窗口叠加在目标窗口上面。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java: dump()]

## dumpsys batterystats：电池使用与功耗分析

### 基本用法

```bash
# 查看电池使用统计
adb shell dumpsys batterystats

# 重置统计（在功耗测试前执行）
adb shell dumpsys batterystats --reset

# 启用完整 wakelock 历史
adb shell dumpsys batterystats --enable full-wake-history
```

### 功耗分析工作流

dumpsys batterystats 本身输出的是原始数据，要发挥作用需要配合 Battery Historian 工具做可视化。标准工作流如下：

第一步，重置统计。在开始测试前执行 `adb shell dumpsys batterystats --reset`，清除历史数据，确保接下来的测试数据是干净的。

第二步，断开 USB（或至少断开充电），执行要测试的操作。如果测试的是后台功耗，可以让设备静置一段时间，模拟真实使用场景。

第三步，导出数据。执行 `adb bugreport > bugreport.zip` 生成完整的 bug report，其中包含 batterystats 的输出。

第四步，使用 Battery Historian 分析。Battery Historian 是 Google 提供的 Web 工具，可以把 batterystats 的原始数据渲染成时间线图表。在图表上可以直观看到 CPU 唤醒、wakelock 持有、网络活动、GPS 使用等事件与电量下降的对应关系。

[已验证: 官方文档, developer.android.com/studio/profile/battery-historian]

### Wakelock 分析

在功耗优化中，最常见的问题之一是"后台唤醒过多"。设备在息屏后本应进入低功耗的 suspend 状态，但如果某个 App 持有 wakelock，CPU 就无法入睡，电量就会快速流失。

在 batterystats 输出中，`All partial wake locks` 表格列出了每个 App 持有 wakelock 的累计时长和次数。如果一个 App 在后台持有了数小时的 partial wakelock，那就是功耗优化的首要目标。

`Battery Historian` 的图表中有一个专门的 `wake_lock` 行，用彩色条段标记 wakelock 被持有的时段。结合 `running` 行（CPU 是否在运行）一起看，可以快速判断"CPU 被谁唤醒了"和"为什么没有重新入睡"。

Battery Historian 工具本身已经不再积极维护（Google 已将重点转向 Android Studio Energy Profiler），但它对于分析 wakelock 和系统级功耗事件仍然是最直观的工具之一。

## dumpsys SurfaceFlinger：Layer 信息与合成状态

### 基本用法

```bash
# SurfaceFlinger 状态快照；Android 15+ 默认以 Frontend 可见快照为主
adb shell dumpsys SurfaceFlinger

# Android 15+：查看全部 Frontend LayerSnapshot / Input list / Hierarchy
adb shell dumpsys SurfaceFlinger --frontend

# 仅列出 Layer 名称
adb shell dumpsys SurfaceFlinger --list

# 查看 HWC 视角的 Layer minidump
adb shell dumpsys SurfaceFlinger --hwclayers

# 查看特定 Layer 的历史 present 时间戳
adb shell dumpsys SurfaceFlinger --latency <layer_name>
```

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp: dump()]

### Layer 列表与合成方式

`dumpsys SurfaceFlinger` 在 Android 15+ 上不能再按旧资料理解成“默认输出完整 Layer 属性表”。AOSP android-16.0.0_r1 的默认 dump 会输出 `Composition list`、`Input list`、Layer Hierarchy 和 HWC minidump，主要来自 Frontend 计算后的 `LayerSnapshot`；这和旧版从 `Layer` 对象直接展开 Source Crop、Display Frame、Composition Type 的文本格式不同。

读 Layer 时先分清三个视角：

| 视角 | 命令 / 输出 | 适合回答的问题 |
|------|-------------|----------------|
| 名称列表 | `dumpsys SurfaceFlinger --list` | 当前有哪些 Layer，`--latency` 应该传哪个 layer name |
| Frontend 快照 | `dumpsys SurfaceFlinger --frontend` 或默认 dump 的 `Composition list` / `Input list` | 当前参与合成和输入命中的 LayerSnapshot、LayerStack、bounds、transform、触摸相关属性 |
| HWC 视角 | `dumpsys SurfaceFlinger --hwclayers` / 默认 dump 的 HWC minidump | 哪些 Layer 交给 HWC，哪些回退到 GPU 合成 |

`RequestedLayerState` 存的是客户端通过 transaction 请求的服务端状态；`LayerSnapshot` 是 SurfaceFlinger Frontend 在当前帧计算出的快照。排查“为什么某个窗口没有显示 / 没有接触摸”时，先看 `Composition list` 和 `Input list` 是否出现目标 Layer，再对比 HWC minidump 中的合成方式。

在实际分析中，如果我们发现大量 Layer 退回到 GPU 合成，常见原因是 HWC overlay 数量不够，或某些 Layer 的属性（如圆角、混合模式、颜色空间、保护内容）超出了 HWC 的硬件能力。这时再回到 App 端检查 Layer 数量和视觉效果复杂度。

### Android 15+ 的输出变化

从 Android 15（AOSP 15）开始，SurfaceFlinger Frontend 成为默认路径，dump 输出从旧版“逐 Layer 展开属性”转为快照化输出。`Composition list` 按合成顺序组织，`Input list` 按输入命中顺序组织，两者都围绕 `LayerSnapshot` 展开；源码入口在 `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp::dumpFrontEnd()` 和 `FrontEnd/LayerSnapshot.h`。

AOSP android-16.0.0_r1 的公开 dumper 参数包括 `--frontend`、`--list`、`--hwclayers`、`--latency`，没有 `--all-layer`。如果厂商系统或调试资料里出现额外参数，以该设备的 `dumpsys SurfaceFlinger --help` 和对应源码分支为准。

在实际调试中，Winscope 工具（Android Studio 集成）更适合查看 Layer 层次结构和跨帧变化。文本 dump 适合取当前快照，Winscope 适合看一段时间内的 transaction、Layer 层级、可见性和输入区域变化。

[来源: Obsidian Personal-Knowledge/source/2026-03-05_wechat_aosp15上SurfaceFlinger的dump部分新特性]

### FrontEnd 架构补充（源码级）

> 以下内容基于 AOSP 源码（android.googlesource.com mainline）深度调研，补充正文未覆盖的 FrontEnd 内部机制。

**FrontEnd 组件清单：**

| 组件 | 源码位置 | 核心职责 |
|------|---------|---------|
| `RequestedLayerState` | `FrontEnd/RequestedLayerState.h` | 存储客户端请求的层状态，含 21 种 `Changes` 位掩码（Created/Destroyed/Geometry/Buffer 等） |
| `LayerLifecycleManager` | `FrontEnd/LayerLifecycleManager.h` | 管理 RequestedLayerState 的增删改，追踪 Handle 生命周期 |
| `TransactionHandler` | `FrontEnd/TransactionHandler.h` | 通过 `LocklessQueue` 异步收集事务，按 `ApplyToken` 排序过滤 |
| `LayerHierarchyBuilder` | `FrontEnd/LayerHierarchy.h` | 将 RequestedLayerState 列表构建为 z-order 层图（graph 结构支持 mirror 共享节点） |
| `LayerSnapshotBuilder` | `FrontEnd/LayerSnapshotBuilder.h` | 从 LayerHierarchy 生成可消费的 `LayerSnapshot`，含 `tryFastUpdate()` 快速路径 |

**热路径无锁设计（核心设计原则）：**

`SurfaceFlinger.cpp` 的 `commit()` 阶段协作顺序（约行 2455-2493）：

```cpp
// 1. 异步收集事务（主线程外）
mTransactionHandler.collectTransactions();

// 2. 新增层
mLayerLifecycleManager.addLayers(std::move(update.newLayers));

// 3. Flush 事务
update.transactions = mTransactionHandler.flushTransactions();

// 4. 应用事务
mLayerLifecycleManager.applyTransactions(update.transactions);

// 5. Handle 销毁
mLayerLifecycleManager.onHandlesDestroyed(update.destroyedHandles);

// 6. 构建 Hierarchy（此时无锁）
mLayerHierarchyBuilder.update(mLayerLifecycleManager);

// 7. 生成 Snapshot（此时无锁）
mLayerSnapshotBuilder.update();

// ===== mStateLock 在 commitTransactionsLocked() 前才持有（约行 2501）=====

// 8. 持有 mStateLock
Mutex::Autolock lock(mStateLock);

// 9. 提交事务
commitTransactionsLocked();
```

`mStateLock` 延迟到事务应用完毕后才持有，确保热路径（commit/composite）不因锁竞争而卡顿。

**`RequestedLayerState::Changes` 位掩码设计：**

```cpp
enum class Changes : uint32_t {
    Created = 1u << 0,    // 新建层
    Destroyed = 1u << 1, // 销毁层
    Hierarchy = 1u << 2,  // 父子关系变更
    Geometry = 1u << 3,  // 位置/尺寸/变换
    Content = 1u << 4,   // Buffer 内容更新
    Input = 1u << 5,     // 输入配置变更
    Z = 1u << 6,         // Z-order 变更
    Mirror = 1u << 7,    // 镜像
    Parent = 1u << 8,    // 父层变更
    RelativeParent = 1u << 9,
    Metadata = 1u << 10,
    Visibility = 1u << 11,
    AffectsChildren = 1u << 12,
    FrameRate = 1u << 13,
    VisibleRegion = 1u << 14,
    Buffer = 1u << 15,   // Buffer 引用变更
    SidebandStream = 1u << 16,
    Animation = 1u << 17,
    BufferSize = 1u << 18,
    GameMode = 1u << 19,
    BufferUsageFlags = 1u << 20,
};
```

`kMustComposite` 标志定义了必须触发布局计算的变更类型子集，其他变更（如纯 Buffer 更新）可走快速路径。

**LayerSnapshotBuilder.tryFastUpdate() 快速路径：**

当检测到 `RequestedLayerState` 只有 `Buffer` 变更时，跳过几何计算直接更新 snapshot：

```cpp
// LayerSnapshotBuilder.h
bool tryFastUpdate(const Args& args);  // 返回 true 表示快速路径成功
```

这个设计让"只有画布刷新"的场景少走一部分几何重算路径；具体收益仍要在目标设备上用 trace 或 benchmark 复核。

**源码索引（均来自 AOSP mainline）：**

- `RequestedLayerState.h` — Changes enum + 层状态结构体
- `LayerLifecycleManager.h` — 生命周期管理接口
- `TransactionHandler.h` — 无锁事务队列
- `LayerSnapshotBuilder.h` — 快速路径 + Snapshot 生成
- `SurfaceFlinger.cpp` — commit() 中 FrontEnd 协作代码，约行 2455-2533

### 帧延迟信息

`dumpsys SurfaceFlinger --latency <layer_name>` 的输出需要特别注意格式。第一行是 **refresh period**（刷新周期），单位为纳秒，表示屏幕的 VSync 间隔——60Hz 设备上为 16666666ns（约 16.67ms），120Hz 设备上为 8333333ns（约 8.33ms）。

从第二行开始，每行是一帧的三个时间戳（均为纳秒）：

| 列 | 字段 | 含义 |
|---|---|---|
| 第一列 | `desired_present_time` | 该帧期望的呈现时间 |
| 第二列 | `actual_present_time` | 该帧实际呈现时间 |
| 第三列 | `frame_ready_time` | AOSP 记录的帧就绪时间，表示帧提交给 HWC 的时间点（非 GPU 完成时间） |

判断掉帧的方法：计算 `actual_present_time - desired_present_time`，如果差值大于 refresh period（第一行的值），说明这一帧被延迟了至少一个 VSync 周期。如果 actual 频繁晚于 desired 超过一个 refresh period，说明这个 Layer 的生产者（App 端渲染线程）跟不上显示刷新率。

在 VRR / ARR 场景下，第一行 refresh period 只能代表 dump 当下的 pacesetter VSync 周期，不能代表每一帧的动态预算。Android 15+ 设备上分析 `--latency` 时，把它作为粗筛：发现 actual 晚于 desired 后，再回到 Perfetto FrameTimeline、`dumpsys gfxinfo framestats` 的 `FrameDeadline` / `FrameInterval`，或 SurfaceFlinger scheduler / vsync 轨道确认该帧对应的真实 deadline。

当 desired_present_time 为 0 时，表示该帧没有期望呈现时间（通常是未使用的缓冲区槽位），应跳过不计。

这个数据在分析滑动流畅度时非常有用。结合 gfxinfo 的帧统计一起看，可以区分"是 App 没画完"还是"是 SurfaceFlinger 合成慢了"。

## 进阶用法

### dumpsys package / alarm / jobscheduler

虽然这三个子命令不直接属于性能分析的核心工具，但在特定场景下很有用：

- `dumpsys package <package_name>` 可以查看 App 申请的所有权限、注册的 ContentProvider 和 Service。当怀疑一个 App 后台行为异常时，先看看它注册了什么后台组件。
- `dumpsys alarm` 列出所有已注册的 Alarm，包括触发时间和目标 App。频繁触发的 Alarm 是后台功耗的常见来源。
- `dumpsys jobscheduler` 显示当前所有 Job 的状态和执行历史。在分析后台任务调度是否合理时有用。

[待补充: 这三个命令的详细输出示例和关键字段解读]

### 自定义 Service 的 dump 接口

dumpsys 不只是系统服务的专利。任何应用或服务都可以实现自己的 `dump()` 方法，通过 `adb shell dumpsys <service_name>` 输出自定义的调试信息。

对于系统服务，在 AOSP 中实现 dump 只需要重写 `Binder.dump()` 方法。对于应用内部的 Service，可以通过 `adb shell dumpsys activity service <package_name>/<service_class>` 触发 Service 的 `dump()` 回调。

[自动发现] 这个机制在 MTK/高通等厂商的定制系统服务中广泛使用。例如 MTK 的 `perfboost` 服务就实现了 dump 接口，可以通过 `adb shell dumpsys perfboost` 查看当前的 CPU/GPU 频率策略和 boost 配置。在做平台级性能调试时，这类厂商自定义 dump 往往能直接给出关键线索。

[待补充: 自定义 dump 接口的代码示例和最佳实践]

## 常见问题与误区

**"dumpsys 输出太多，不知道看哪里"**——这是新手最常见的问题。正确做法是先明确分析目标，再选择对应的子命令。分析内存看 `meminfo`，分析卡顿看 `gfxinfo`，分析 ANR 优先看 `activity exit-info`，`lastanr` 只做遗留兜底，分析功耗看 `batterystats`。不要一上来就执行 `adb shell dumpsys` 不带参数——那会输出所有服务的 dump，几千行文本，几乎不可读。

**"gfxinfo 的 Janky frames 总是很多，是不是系统有问题"**——Janky frames 的判定标准是超过一个 VSync 周期。在 120Hz 设备上，超过 8.33ms 就算 Jank。一些合理的长帧（如页面切换时的布局重建）也会被计入。关注 Janky frames 占比而不是绝对值，如果占比低于 5%，通常不需要优化。

**"dumpsys meminfo 显示的内存和 Android Studio Profiler 不一样"**——两者统计口径不同。dumpsys meminfo 报告的是操作系统视角的 PSS/USS（包含共享库按比例分摊），而 Android Studio Profiler 报告的是 Java Heap 的分配量（只统计 ART 管理的对象）。两者互为补充，不能互相替代。

**"dumpsys batterystats 就够了，不需要 Battery Historian"**——batterystats 的原始输出是一堆数字和时间戳，几乎不可能直接从中发现功耗问题的根因。Battery Historian 的可视化图表可以直观展示 CPU 唤醒、wakelock、网络活动等事件与电量下降的对应关系，这是纯文本做不到的。

## 参考资料

- AOSP 源码：`frameworks/native/cmds/dumpsys/dumpsys.cpp`
- AOSP 源码：`frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`（dump 方法）
- AOSP 源码：`frameworks/base/services/core/java/com/android/server/wm/Task.java`、`ActivityRecord.java`（现代 Task / Activity 栈结构）
- AOSP 源码：`frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`（dump / `--frontend` / `--hwclayers` / `--latency`）
- AOSP 源码：`frameworks/native/services/surfaceflinger/FrontEnd/LayerSnapshot.h`（Frontend 快照结构）
- AOSP 源码：`frameworks/base/services/core/java/com/android/server/wm/DisplayContent.java`（分显示器焦点状态）
- AOSP 源码：`frameworks/base/libs/hwui/JankTracker.cpp`（`FrameDeadline` 与 `kMissedDeadline` 判定）
- AOSP 源码：`frameworks/base/libs/hwui/service/GraphicsStatsService.cpp`（`Number Frame deadline missed` 输出）
- 官方文档：[Investigate RAM usage](https://developer.android.com/studio/profile/investigate-ram)
- 官方文档：[Profile GPU Rendering](https://developer.android.com/studio/profile/dev-options-rendering)
- 官方文档：[Battery Historian](https://developer.android.com/studio/profile/battery-historian)
- 官方文档：[SurfaceFlinger and WindowManager](https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager)
