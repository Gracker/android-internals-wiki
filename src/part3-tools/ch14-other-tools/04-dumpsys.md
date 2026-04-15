---
title: "dumpsys 系列命令"
chapter: "14.4"
section: "14.4"
status: ready-for-review
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 6.0 (API 23) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/cmds/dumpsys/"
  - type: official
    path: "developer.android.com/studio/profile/battery-historian"
  - type: blog
    path: "source.android.com/docs/core/graphics/surfaceflinger-windowmanager"
tags: [dumpsys, meminfo, gfxinfo, activity, window, batterystats, SurfaceFlinger, debugging]
related_chapters: ["4.1", "4.5", "7.3", "13.1", "14.1"]
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-14"
task6_result: needs-rework
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

在分析 Android 性能问题的过程中，我们经常需要快速了解系统某一时刻的"状态快照"——比如某个进程占用了多少内存、当前屏幕上叠加了多少个 Layer、哪个窗口持有焦点、最近 120 帧的渲染耗时分布如何。Perfetto 可以告诉我们"过程"（事情是怎么一步步发生的），但如果我们需要的是一个"截面"（此刻系统长什么样），dumpsys 就是最趁手的工具。

可以把 dumpsys 看成一个桥梁。它会遍历 Android 系统中所有注册到 ServiceManager 的系统服务，调用每个服务的 `dump()` 方法，再把服务内部状态以文本形式输出到终端。

因为每个系统服务都实现了自己的 `dump()` 方法，dumpsys 的输出覆盖了 Android 系统的多个关键面向，从 Activity 栈到电池统计，从内存分配到图形合成，都能拿到对应的状态快照。

本章不打算穷举 dumpsys 支持的所有子命令（在设备上运行 `adb shell dumpsys -l` 就能列出完整列表），而是聚焦于性能分析中最常用的六个子命令，逐个讲清楚它的用途、输出结构、关键指标的含义，以及在实际性能分析中怎么用。

[已验证: AOSP android-16.0.0_r1, frameworks/native/cmds/dumpsys/dumpsys.cpp]

## dumpsys activity：Activity 栈、进程与 ANR 信息

### 基本用法

`dumpsys activity` 是 ActivityManagerService（AMS）的状态输出窗口。在性能分析中，我们主要关注它的三个子项：

- `dumpsys activity activities`：查看所有 Task 和 Activity 的栈信息
- `dumpsys activity processes`：查看所有进程的优先级和状态
- `dumpsys activity lastanr`：查看最近一次 ANR 的详细信息

### 读懂 Activity 栈

当我们怀疑某个场景的卡顿或 ANR 与 Activity 生命周期有关时，Activity 栈是第一手线索。执行 `adb shell dumpsys activity activities` 后，输出会按照 Task 分组，每个 Task 下列出从底到顶的 Activity 栈。关键的几个字段：

- `TaskRecord` 中的 `affinity` 和 `taskId` 告诉我们这个 Task 属于哪个应用
- `ActivityRecord` 中的 `state` 表示 Activity 当前状态（resumed、paused、stopped 等）
- `mFocusedActivity` 和 `mFocusedApp` 标记当前获得焦点的 Activity 和应用

在分析启动速度时，我们可以反复执行这个命令，观察目标 Activity 从 `initiating` 到 `resumed` 的状态变化，来确认各阶段的耗时是否正常。

### 进程优先级与 ANR

`dumpsys activity processes` 会列出所有进程的 `oom_adj` 值和调度优先级。当分析 Low Memory Killer 误杀问题时，这里的 `oom_adj` 值就是最直接的证据：一个本应处于 `VISIBLE_APP_LVL`（优先级 200）的进程，如果显示为 `FOREGROUND_APP`（优先级 100），说明系统的进程优先级计算可能出了问题。

`dumpsys activity lastanr` 输出最近一次 ANR 发生时的调用栈和系统状态。当我们拿到一个用户反馈的 ANR 问题，但手头没有完整的 Trace 文件时，先看看 `lastanr` 里是否还有残留信息，有时可以直接定位到阻塞主线程的代码行。

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java: dump()]

## dumpsys meminfo：系统和进程内存全景

### 基本用法

`dumpsys meminfo` 是 Android 上最经典的内存分析命令。它可以查看系统全局内存概况，也可以查看单个进程的详细内存分布：

```bash
# 系统全局内存概况
adb shell dumpsys meminfo

# 指定进程的详细内存分布
adb shell dumpsys meminfo <package_name>

# 按 slab 排序查看内核内存
adb shell dumpsys meminfo --slab
```

### 关键指标：PSS、USS、Private Dirty

在 meminfo 的输出中，最核心的三个指标是 PSS、USS 和 Private Dirty。理解它们的区别，是用好这个命令的前提。

**PSS（Proportional Set Size）** 是我们最关注的指标。它衡量的是一个进程"实际占用"的物理内存。PSS 的特殊之处在于，对于被多个进程共享的内存页（比如共享库的代码段），它会按比例分摊：如果一张 4KB 的内存页被两个进程共享，每个进程的 PSS 只计入 2KB。把所有进程的 PSS 加起来，结果就接近系统实际使用的总物理内存。在判断一个 App "占了多少内存"时，PSS 是最准确的标准。

**USS（Unique Set Size）** 是进程独占的物理内存，不被任何其他进程共享。如果这个进程被杀掉，USS 这部分内存会被完全释放。USS 帮助我们评估一个进程的"可回收价值"——LMK 在选择杀谁时，会参考这个值。

**Private Dirty** 是已经被修改过的私有内存页。这部分内存不能被换出到磁盘（Android 默认不用 swap），必须常驻物理 RAM。在内存分析中，Private Dirty 持续增长通常是内存泄漏的信号。

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

**Janky frames** 是超过帧预算的帧数（60Hz 设备上超过 16.67ms，120Hz 设备上超过 8.33ms）。Janky frames 占比超过 5% 就值得调查了。

**90th / 95th / 99th percentile** 是帧耗时的分位值。如果 99th percentile 是 50ms，意味着有 1% 的帧耗时超过 50ms——在 60Hz 设备上这就是连续掉 3 帧，用户能明显感知到卡顿。

**Number Slow UI thread** 告诉我们有多少帧的瓶颈在主线程——也就是 `measure`/`layout`/`draw` 阶段耗时过长。如果这个数字很高，说明我们需要优化布局层次或减少 `onDraw()` 中的计算。

**Number Slow RenderThread** 表示有多少帧的瓶颈在 RenderThread——GPU 命令提交或光栅化阶段耗时过长。如果这个数字高而 Slow UI thread 低，说明瓶颈在渲染管线的后半段，需要减少过度绘制或简化绘制指令。

### framestats：逐帧时间线

`framestats` 输出最近 120 帧的逐帧时间戳。每一行是一帧，各列代表渲染管线中的关键时间节点：`IntendedVsync`、`Vsync`、`HandleInputStart`、`AnimationStart`、`PerformTraversalsStart`、`DrawStart`、`SyncQueued`、`SyncStart`、`IssueDrawCommandsStart`、`SwapBuffers`、`FrameCompleted`。

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

## dumpsys window：窗口层级与焦点

### 基本用法

```bash
# 完整的 WindowManager 状态
adb shell dumpsys window

# 窗口列表（含 Z-order）
adb shell dumpsys window windows

# 当前焦点窗口
adb shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'
```

### 关键信息

在性能分析中，dumpsys window 主要用于两类场景。

**第一类是确认窗口焦点。** 当用户报告"点了没反应"或"触摸不灵敏"时，可能是焦点不在预期的窗口上。`mCurrentFocus` 显示当前获得输入焦点的窗口，`mFocusedApp` 显示获得焦点的是哪个 App。注意这两个不一定一致：比如用户拉下通知栏时，`mCurrentFocus` 会切换到 SystemUI 的通知面板，但 `mFocusedApp` 仍然是之前使用的 App。

**第二类是排查 Input ANR。** 当 Input 系统无法将事件投递到目标窗口时（比如窗口已经不存在但系统没有及时清理），会导致 Input ANR。通过 `dumpsys window windows` 可以检查目标窗口的状态——是否还存在、是否可触摸（`NOT_TOUCHABLE` 标志）、touchable region 是否正确。

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

dumpsys batterystats 本身输出的是原始数据，真正发挥威力需要配合 Battery Historian 工具做可视化。标准工作流如下：

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
# 完整的 SurfaceFlinger 状态
adb shell dumpsys SurfaceFlinger

# 仅查看 Layer 列表（Android 14 及更早版本）
adb shell dumpsys SurfaceFlinger --list

# 查看特定 Layer 的详细信息
adb shell dumpsys SurfaceFlinger --latency <layer_name>
```

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp: dump()]

### Layer 列表与合成方式

dumpsys SurfaceFlinger 的核心输出是当前屏幕上所有可见 Layer 的列表及其合成方式。每个 Layer 代表一个可视化表面——一个 Activity 的窗口、一个 Dialog、StatusBar、NavigationBar，各自都是一个独立的 Layer。

在输出中，每个 Layer 旁边标注了它的合成方式：`HWC`（Hardware Composer）或 `GLES`（GPU 合成）。HWC 合成意味着这个 Layer 由显示硬件直接叠加输出，不需要 GPU 参与，功耗低、效率高。GLES 合成意味着 SurfaceFlinger 需要用 GPU 把这个 Layer 绘制到帧缓冲区，再交给 HWC 显示。

在实际分析中，如果我们发现大量 Layer 退回到 GLES 合成（理想情况下，大多数 Layer 应该由 HWC 处理），那可能意味着 HWC overlay 数量不够、或者某些 Layer 的属性（如圆角、混合模式）超出了 HWC 的硬件能力。这时就需要检查 App 端是否可以减少 Layer 数量或简化视觉效果。

### Android 15+ 的输出变化

从 Android 15（AOSP 15）开始，`dumpsys SurfaceFlinger` 的输出格式发生了较大变化。以前版本会直接列出所有 Layer 的详细信息（包括 Source Crop、Display Frame、Composition Type 等），Android 15 引入了新的 Frontend 架构，输出分为 `Composition list`（按合成优先级排列）和 `Input list`（按触摸优先级排列），每个 Layer 的信息更加结构化，包含了 `bounds`、`input` 标志和 `toDisplayTransform` 等字段。

如果在 Android 15+ 设备上执行 dumpsys SurfaceFlinger 后看不到 Layer 信息，通常是因为新架构需要额外的参数或权限。在实际调试中，Winscope 工具（Android Studio 集成）通常是查看 Layer 层次结构更好的选择——它提供可视化的时间线视图，比文本输出更容易理解。

[来源: Obsidian Personal-Knowledge/source/2026-03-05_wechat_aosp15上SurfaceFlinger的dump部分新特性]

### 帧延迟信息

`dumpsys SurfaceFlinger --latency <layer_name>` 输出三列数据：`desired_present_time`、`actual_present_time` 和 `frame_ready_time`。通过对比 desired 和 actual 的差值，可以判断这个 Layer 是否存在掉帧。如果 actual 频繁晚于 desired 超过一个 VSync 周期，说明这个 Layer 的生产者（App 端渲染线程）跟不上显示刷新率。

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

**"dumpsys 输出太多，不知道看哪里"**——这是新手最常见的问题。正确做法是先明确分析目标，再选择对应的子命令。分析内存看 `meminfo`，分析卡顿看 `gfxinfo`，分析 ANR 看 `activity lastanr`，分析功耗看 `batterystats`。不要一上来就执行 `adb shell dumpsys` 不带参数——那会输出所有服务的 dump，几千行文本，几乎不可读。

**"gfxinfo 的 Janky frames 总是很多，是不是系统有问题"**——Janky frames 的判定标准是超过一个 VSync 周期。在 120Hz 设备上，超过 8.33ms 就算 Jank。一些合理的长帧（如页面切换时的布局重建）也会被计入。关注 Janky frames 占比而不是绝对值，如果占比低于 5%，通常不需要优化。

**"dumpsys meminfo 显示的内存和 Android Studio Profiler 不一样"**——两者统计口径不同。dumpsys meminfo 报告的是操作系统视角的 PSS/USS（包含共享库按比例分摊），而 Android Studio Profiler 报告的是 Java Heap 的分配量（只统计 ART 管理的对象）。两者互为补充，不能互相替代。

**"dumpsys batterystats 就够了，不需要 Battery Historian"**——batterystats 的原始输出是一堆数字和时间戳，几乎不可能直接从中发现功耗问题的根因。Battery Historian 的可视化图表可以直观展示 CPU 唤醒、wakelock、网络活动等事件与电量下降的对应关系，这是纯文本做不到的。

## 参考资料

- AOSP 源码：`frameworks/native/cmds/dumpsys/dumpsys.cpp`
- AOSP 源码：`frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`（dump 方法）
- AOSP 源码：`frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`（dump 方法）
- 官方文档：[Investigate RAM usage](https://developer.android.com/studio/profile/investigate-ram)
- 官方文档：[Profile GPU Rendering](https://developer.android.com/studio/profile/dev-options-rendering)
- 官方文档：[Battery Historian](https://developer.android.com/studio/profile/battery-historian)
- 官方文档：[SurfaceFlinger and WindowManager](https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager)
