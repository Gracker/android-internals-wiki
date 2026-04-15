---
title: "App 启动全流程"
chapter: "8.2"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-01"
last_verified_against: "AOSP android-15.0.0_r1"
confidence: medium
sources:
  - type: blog
    path: "Cubox/启动优化 ·  基础论 ·  浅析Android启动优化-2022-12-31.md"
  - type: blog
    path: "Cubox/FullyDrawnReporter—一个官方冷启动耗时统计小工具 - 掘金-2023-12-24.md"
  - type: blog
    path: "Cubox/Activity 启动速度分析方法（启动流程分析） - Light.Moon-2022-04-11.md"
  - type: blog
    path: "Cubox/Android 强推的 Baseline Profiles 国内能用吗？我找 Google 工程师求证了！ - 掘金-2022-07-17.md"
  - type: official
    path: "developer.android.com/topic/performance/vitals/launch-time"
tags: [cold-start, warm-start, hot-start, TTID, TTFD, launch, startup, reportFullyDrawn, baseline-profiles, app-startup, contentprovider, process-creation]
related_chapters: ["8.1", "1.2", "1.10", "2.4", "2.5", "7.1"]
section: "8.2"
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-16"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
task9_state: pending
task2b_state: idle
---

# App 启动全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 冷启动 / 温启动 / 热启动的定义与区别
- 🔹 冷启动完整流程：Process.start → ActivityThread → Application.onCreate → Activity.onCreate → 首帧绘制
- 🔹 TTID（Time To Initial Display）与 TTFD（Time To Full Display / reportFullyDrawn）的定义
- 🔹 启动耗时的度量方法：adb am start -W、Logcat ActivityTaskManager、Perfetto
- 🔹 Application.onCreate 中常见的耗时操作：SDK 初始化、数据库初始化、多 Dex 加载
- 🔹 首帧绘制的关键路径：inflate → measure → layout → draw

### 扩展（可选深入）

- 🔸 Baseline Profile 与 Cloud Profile 对启动速度的提升
- 🔸 App Startup Library（AndroidX）的使用与原理
- 🔸 Zygote preload 对启动速度的贡献量化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 App 启动流程

我们在 Perfetto 中打开一个冷启动的 Trace，看到的是一段横跨 system_server、SurfaceFlinger 和目标 App 三个进程的长长的时间线。从用户点击桌面图标到界面显示出来，中间经历了进程创建、Binder 通信、Application 初始化、Activity 生命周期、View 树构建、第一帧绘制、SurfaceFlinger 合成——整个过程可能超过 2 秒，而我们真正能优化的部分只占其中一段。

这就是我们需要完整理解启动流程的原因。如果我们只知道 Application.onCreate 里不能做太多事，那我们能优化的范围就很有限。但如果我们知道从点击到首帧的完整路径，就能找到所有可能的优化切入点：哪些是系统开销我们无法改变的，哪些是应用侧可以加速的，哪些是可以通过缓存机制绕过的。

了解完整流程之后，我们能做之前做不到的事：在 Perfetto 中精确定位启动耗时的瓶颈环节，区分系统耗时和应用耗时，有针对性地制定优化策略，而不是盲目地在 Application.onCreate 里删几行代码。

## 冷启动、温启动、热启动：三种启动状态

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

Android 把应用的启动分为三种状态：冷启动（Cold Start）、温启动（Warm Start）和热启动（Hot Start）。它们的区别在于系统需要做多少工作，理解这三种状态的本质，是后续所有优化工作的基础——因为不同状态下的优化策略完全不同。

### 冷启动：从零开始

冷启动是指应用的进程不存在（从未启动过，或者被系统杀死回收了），用户点击图标后系统需要从头创建进程并初始化一切。这是耗时最长的启动方式，也是 Android Vitals 等监控平台衡量应用启动性能的基准。

[来源: obsidian/Cubox/启动优化 ·  基础论 ·  浅析Android启动优化-2022-12-31.md]

冷启动需要经历的完整路径：

1. 用户点击桌面图标 → Launcher 通过 Binder IPC 调用 startActivity
2. system_server 中的 ActivityTaskManagerService 收到请求，创建 ActivityRecord
3. system_server 发现目标进程不存在，通过 Socket 通知 Zygote fork 新进程
4. 新进程启动 ActivityThread.main()，创建主线程 Looper
5. 通过 Binder 回调 system_server，执行 bindApplication → 创建 Application 对象
6. 依次调用 Application.attachBaseContext() → Application.onCreate()
7. system_server 通过 ClientLifecycleManager 向 App 发送 LaunchActivityItem
8. App 创建 Activity 对象，依次执行 onCreate → onStart → onResume
9. 在 onResume 中创建 ViewRootImpl，注册 Choreographer 回调
10. 下一个 VSync 到来时执行 performTraversals：measure → layout → draw
11. RenderThread 通过 queueBuffer 将帧提交给 SurfaceFlinger
12. SurfaceFlinger 合成并送显

整个过程横跨三个进程（Launcher、system_server、目标 App）和一次 Zygote fork，涉及大量的 Binder IPC 和初始化工作。

### 温启动：进程在，Activity 不在

温启动是指应用的进程还活着（没有被 LMK 杀掉），但 Activity 已经被销毁了。典型场景是用户按返回键退出应用后再次打开。温启动跳过了进程创建和 Application 初始化的步骤，直接从创建 Activity 对象开始。

判断条件从代码层面看：system_server 中有目标进程的 ProcessRecord（`hasThread()` 返回 true，表示 ActivityThread 已绑定），但没有目标 Activity 的 ActivityRecord（或者 ActivityRecord 不可复用）。

温启动的路径从上面的第 7 步开始，省去了 fork 进程、创建 Application 的开销。在 Perfetto 中我们会看到没有 "BindApplication" 这段，对于一个中等复杂度的应用，温启动通常比冷启动快 30%-50%。

### 热启动：进程和 Activity 都在

热启动是指应用进程存在且 Activity 对象也存在（通常在后台栈中）。典型场景是用户按 Home 键切到桌面后再次打开应用。这种情况下 Activity 只需要走 onRestart → onStart → onResume 生命周期，在 Perfetto 的 am 子系统中，热启动被标记为 HOT_LAUNCH。

热启动是最快的，因为连 Activity 对象都不需要重新创建。但如果系统因内存不足回收了 Activity 中的部分资源（如 Bitmap），热启动时可能需要重建这些对象，这时开销会接近温启动。

[来源: obsidian/Cubox/Activity 启动速度分析方法（启动流程分析） - Light.Moon-2022-04-11.md]

### 在 Perfetto 中区分三种启动

在 Perfetto 中，我们可以通过以下方式判断启动类型：

- **冷启动**：存在 "BindApplication" slice，且能看到新进程的创建
- **温启动**：没有 "BindApplication"，但有 "activityStart" 或 "launching" 标记
- **热启动**：只有 "activityResume" 或 "activityRestart" 标记，注意，logcat 中的 "Displayed" 信息在热启动时不会打印。

[待补充：三种启动类型在 Perfetto 中的 Trace 对比截图]

## 冷启动完整流程详解

我们以冷启动为线索，把从用户点击到首帧绘制的完整路径走一遍。这不是源码级的堆栈追踪——那是 Debug 工具做的事——而是一个工程师给另一个工程师讲"每一步在干什么、为什么需要这一步、耗时大头在哪里"。

[来源: obsidian/Cubox/Activity 启动速度分析方法（启动流程分析） - Light.Moon-2022-04-11.md]

### 第一阶段：从点击到 fork 进程

用户在桌面上点击应用图标，Launcher 的 onClick 回调被触发。这看似一个简单的函数调用，背后却涉及多个系统组件的协调。

Launcher 调用 startActivity()，经过几层封装后通过 Binder IPC 发送请求到 system_server 中的 ActivityTaskManagerService（ATMS）。ATMS 的 ActivityStarter 收到请求后，首先通过 ActivityMetricsLogger 记录一个时间戳——这个时间戳就是后续所有启动耗时度量的起点（TTID 的起点）。

然后 ATMS 创建 ActivityRecord 和 TaskRecord，检查是否有可以复用的 Activity。冷启动场景下，答案是没有。ATMS 接着会向前一个处于 Resumed 状态的 Activity（通常是 Launcher）发送 Pause 请求。这个 Pause 请求通过 ClientLifecycleManager 机制发送到 Launcher 进程，Launcher 处理 onPause 后通过 Binder 通知 ATMS 完成。

ATMS 确认 Pause 完成后，检查目标进程是否存在。冷启动场景下，目标进程不存在，于是通过 Local Socket 向 Zygote 发送 fork 请求。Zygote fork 出子进程后，将 PID 返回给 system_server。

这一阶段的开销主要是：Binder IPC（2 次跨进程调用）、Zygote fork（创建新进程）、以及 system_server 内部的调度逻辑。在 Perfetto 中，我们可以在 system_server 进程中看到 "launching: xxx" 的 slice，在 app 进程中看到 "BindApplication" 的开始。

### 第二阶段：进程初始化与 Application 创建

fork 出来的子进程从 ActivityThread.main() 开始执行。这个 main() 函数做了两件关键的事：

**创建主线程 Looper**。调用 Looper.prepareMainLooper() 和 Looper.loop()，建立起 Android 主线程的消息循环。此后所有与 UI 相关的操作都通过这个 Looper 分发。

**通知 system_server 进程已就绪**。通过 Binder 调用 ATMS 的 attachApplication() 和 AMS 的 attachApplication()。ATMS 收到通知后，会继续后续的 Activity 启动流程。注意，这个时候主线程的 Looper.loop() 还没真正开始循环（或者刚开始），因为 attachApplication 的调用是在 main() 函数中同步完成的，而后续的消息处理要等 loop() 跑起来才行。

AMS 的 attachApplication 会触发 bindApplication，这会向主线程发送一条 BIND_APPLICATION 消息。Looper 开始循环后处理这条消息时，创建 Application 对象。如果我们在 AndroidManifest.xml 中声明了自定义的 Application 类，系统会通过反射创建 Application 实例，然后依次调用：

1. Application.attachBaseContext()——这是我们能最早介入的回调
2. Application.onCreate()——大多数 SDK 初始化代码放在这里

[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java: handleBindApplication]

这个阶段是应用侧启动耗时的重灾区。一个中等规模的应用可能在 Application.onCreate 中初始化 10-20 个 SDK（埋点、推送、网络、图片加载、数据库等），每个 SDK 几十到几百毫秒，加起来可能超过 1 秒。我们在后面的章节会专门讨论 Application.onCreate 的优化策略。

### 第三阶段：Activity 创建与生命周期

Application 初始化完成后，system_server 通过 ClientLifecycleManager 向 App 发送 ClientTransaction，其中包含 LaunchActivityItem（设置在 mActivityCallbacks 中）和 ResumeActivityItem（设置在 mLifecycleStateRequest 中）。

App 的 ActivityThread 在主线程处理 EXECUTE_TRANSACTION 消息。TransactionExecutor 按顺序执行：

**先执行 callback**：LaunchActivityItem.execute() → 调用 handleLaunchActivity() → performLaunchActivity()。这一步创建 Activity 对象（通过反射），调用 Activity.attach() 初始化（创建 PhoneWindow），然后调用 Activity.onCreate()。在 onCreate 中我们必须调用 setContentView()，否则后续绘制会报错。setContentView 的本质是创建 DecorView（根 View），并将布局文件 inflate 后挂载到 DecorView 下面的 mContentParent 中。

**然后执行生命周期路径补全**：从 ON_CREATE 到 ON_RESUME，中间需要补 ON_START。依次调用 Activity.onStart()、Activity.onResume()。

[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/app/servertransaction/TransactionExecutor.java]

### 第四阶段：首帧绘制

Activity.onResume() 执行完后，并不是立刻就能看到界面。真正的绘制操作是延后执行的。

在 onResume 的处理过程中，WindowManager 会将 DecorView 添加到 WindowManagerGlobal 中，这会创建 ViewRootImpl。ViewRootImpl 做了两件事：

**请求布局**：调用 requestLayout()，这实际上是通过 Choreographer 向主线程 post 一个回调（TRAVERSAL）。注意，这个回调不会立即执行——它要等下一个 VSync 信号到来。

**创建 SurfaceSession 连接**：通过 IWindowSession.addWindow() 向 WindowManagerService 注册窗口。WMS 会与 SurfaceFlinger 建立连接，为这个窗口创建 Layer 和 BufferQueue。

当下一个 VSync 信号到来时，Choreographer 回调触发 ViewRootImpl.performTraversals()。这里开始执行实际的绘制操作：

**relayoutWindow**：第一次执行时，会向 SurfaceFlinger 申请创建 Surface（如果还没有的话）。SurfaceFlinger 创建 BufferQueueLayer，返回 IGraphicBufferProducer 给应用端。

**performMeasure**：从 DecorView 开始递归测量整棵 View 树，确定每个 View 的大小。

**performLayout**：从 DecorView 开始递归布局，确定每个 View 在父容器中的位置。

**performDraw**：在硬件加速开启的情况下（Android 4.4+ 默认开启），View 的 onDraw() 并不真正执行绘制命令，而是将绘制指令记录到 DisplayList 中。然后 ViewRootImpl 向 RenderThread post 一个 DrawFrameTask，由 RenderThread 统一执行 OpenGL 绘制命令。

RenderThread 完成绘制后，通过 IGraphicBufferProducer.queueBuffer() 将帧提交给 SurfaceFlinger。queueBuffer 返回后，ViewRootImpl 通知 system_server 的 ActivityMetricsLogger 记录 "首帧绘制完成" 的时间戳——这就是 TTID 的终点。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

[图：冷启动完整时序图——从用户点击到首帧显示，标注 system_server、Zygote、App 主线程、RenderThread、SurfaceFlinger 各进程的参与环节]

> 注意：queueBuffer 返回并不等于用户在屏幕上看到了画面。SurfaceFlinger 还需要等到下一个 VSync-sf 信号到来时，进行合成（compose）和送显。这中间还有一到两个 VSync 周期的延迟。但从系统度量角度，TTID 统计到 queueBuffer 完成就结束了。

## TTID 与 TTFD：两个关键的启动指标

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

理解了启动流程之后，我们来看如何度量启动性能。Android 定义了两个关键指标：

### TTID（Time To Initial Display）

TTID 是从用户触发启动（点击图标）到应用首帧绘制完成的时间。它涵盖了冷启动的完整路径：进程创建、Application 初始化、Activity 创建和首帧绘制。系统通过 ActivityMetricsLogger 自动统计这个时间，我们可以在 logcat 中通过过滤 "Displayed" 关键字看到：

```
ActivityTaskManager: Displayed com.example.app/.MainActivity: +1s234ms
```

或者通过 `adb shell am start -W` 命令的 TotalTime 字段获取。

TTID 是 Android Vitals 等平台监控的核心指标。Google 建议 TTID 不应超过 5 秒（冷启动），否则被视为性能过差。

### TTFD（Time To Full Display）

TTID 只统计到首帧绘制，但很多应用的界面在首帧绘制时并没有显示完整内容——数据还在从网络加载，或者数据库还在查询。用户看到的是一个加载骨架或者空白区域。为了让度量更贴近用户实际感知，Android 提供了 TTFD（Time To Full Display）指标。

TTFD 需要开发者在代码中主动调用 `Activity.reportFullyDrawn()` 来告诉系统"我的界面完全准备好了"。调用后 logcat 中会出现：

```
ActivityTaskManager: Fully drawn com.example.app/.MainActivity: +2s156ms
```

[来源: obsidian/Cubox/FullyDrawnReporter—一个官方冷启动耗时统计小工具 - 掘金-2023-12-24.md]

### FullyDrawnReporter：多条件 TTFD 统计

如果应用的界面需要等待多个异步任务（比如同时发起 A、B、C 三个网络请求，全部完成后才算界面完整），AndroidX Activity 1.8.0 引入了 FullyDrawnReporter 工具来简化这种场景：

```kotlin
// 在每个异步任务开始前注册 reporter
override fun onResume() {
    super.onResume()
    
    lifecycleScope.launch {
        fullyDrawnReporter.addReporter()  // 注册：任务 A 开始
        val resultA = fetchNetworkDataA()
        fullyDrawnReporter.removeReporter()  // 完成：任务 A 结束
    }
    
    lifecycleScope.launch {
        fullyDrawnReporter.addReporter()  // 注册：任务 B 开始
        val resultB = fetchNetworkDataB()
        fullyDrawnReporter.removeReporter()  // 完成：任务 B 结束
    }
}
// 当所有 reporter 都被移除时，自动调用 reportFullyDrawn()
```

FullyDrawnReporter 内部维护一个计数器（reporterCount），每次 addReporter 加 1，每次 removeReporter 减 1。当计数器归零时，自动调用 reportFullyDrawn()。这比手动在多个回调中协调 reportFullyDrawn() 的调用时机更可靠，避免了多异步任务间的时序竞争。

[已验证: 官方文档, developer.android.com/develop/ui/views/launch/ttfd]

## 启动耗时的度量方法

了解了指标定义之后，我们来看具体的度量工具。不同的工具有不同的精度和适用场景。

### adb am start -W：最直接的线下测量

```bash
adb shell am start -W com.example.app/.MainActivity
```

输出：

```
Status: ok
LaunchState: COLD
Activity: com.example.app/.MainActivity
TotalTime: 1234
WaitTime: 1250
Complete
```

这里有几个关键信息：

- **LaunchState**：启动类型（COLD/WARM/HOT），帮助确认当前测试的是哪种启动场景
- **TotalTime**：从 startActivity 发起（ActivityMetricsLogger 记录的起始时间）到首帧绘制完成的时间，等于 TTID
- **WaitTime**：从命令调用到命令返回的总等待时间，比 TotalTime 略多，因为包含了命令本身的调度开销

加 `-S` 参数可以强制先 kill 进程再启动，确保一定是冷启动：

```bash
adb shell am start -W -S com.example.app/.MainActivity
```

[来源: obsidian/Cubox/Activity 启动速度分析方法（启动流程分析） - Light.Moon-2022-04-11.md]

### Logcat：快速查看启动时间

在启动应用后过滤 logcat：

```bash
adb logcat | grep -E "Displayed|Fully drawn"
```

- `Displayed` 对应 TTID
- `Fully drawn` 对应 TTFD（需要应用主动调用 reportFullyDrawn）

### Perfetto：精确定位每个阶段

Perfetto 是分析启动性能最重要的工具，因为它能让我们看到启动过程中每个阶段的精确耗时。

抓取启动 Perfetto 的推荐配置：

```bash
adb shell perfetto \
  -c - --txt \
<<EOF
buffers: {
    size_kb: 63488
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
            atrace_categories: "am"
            atrace_categories: "view"
            atrace_categories: "gfx"
            atrace_categories: "dalvik"
            atrace_categories: "res"
        }
    }
}
duration_ms: 10000
EOF
```

在 Perfetto 中，我们应该关注这些关键 slice：

| Slice 名称 | 所在进程 | 含义 |
|---|---|---|
| `launching: xxx` | system_server | ATMS 记录的启动过程，从 startActivity 返回到首帧完成 |
| `BindApplication` | App 进程 | Application 对象创建和初始化 |
| `activityCreate` / `activityStart` / `activityResume` | App 进程 | Activity 生命周期的各阶段 |
| `performTraversals` | App 主线程 | View 树的 measure/layout/draw |
| `DrawFrame` | RenderThread | GPU 渲染 |
| `queueBuffer` | RenderThread | 帧提交给 SurfaceFlinger |

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

### 各度量方法的差异

这些度量方法的统计起止时间有微妙差异：

- **Displayed / am start -W TotalTime**：从 ActivityMetricsLogger.notifyActivityLaunching() 到 ViewRootImpl 报告的首帧绘制完成时间
- **Perfetto "launching: xxx"**：从 notifyActivityLaunched()（在 startActivity() 返回之后）到首帧绘制完成。比 Displayed 少了 startActivity() 内部的处理时间
- **reportFullyDrawn()**：起始时间同 TTID，但结束时间由应用决定

所以我们发现 Perfetto 中的 "launching" 时间总是比 logcat 中的 "Displayed" 时间少一些。这不是 Bug，是统计口径的差异。

[来源: obsidian/Cubox/Activity 启动速度分析方法（启动流程分析） - Light.Moon-2022-04-11.md]

## Application.onCreate 中常见的耗时操作

理解了度量方法，我们来看应用侧优化的重点区域。Application.onCreate 是应用启动流程中开发者能控制的第一个回调，也是最常见的性能瓶颈所在。

### SDK 初始化：最大的耗时黑洞

一个中等规模的应用可能在 Application.onCreate 中初始化以下 SDK：

- 埋点/分析（友盟、神策等）：通常 50-200ms
- 推送服务（FCM、华为/小米推送）：50-150ms
- 网络库初始化（OkHttp 配置、证书固定）：20-50ms
- 图片加载库（Glide/Coil 配置）：10-30ms
- 数据库初始化（Room/SQLCipher）：50-200ms
- 热修复框架：100-300ms
- APM 监控：20-50ms

单独看每个 SDK 的初始化时间都不长，但 10-20 个 SDK 串行初始化的累积效果可能达到 1-2 秒。而且很多 SDK 的初始化并不需要在首帧显示前完成——它们只是"习惯性"地放在了 Application.onCreate 里。

优化思路不是本节的重点（在 8.3 启动优化策略中会详细讨论），但核心原则是：**区分哪些初始化是首帧必需的，哪些可以延迟**。只有影响首帧显示的初始化才需要在 Application.onCreate 中同步执行，其余的都应该延迟到首帧之后。

### 多 Dex 加载

[适用版本: Android 5.0 之前, API < 21]

在 Android 5.0（API 21）之前，系统使用 Dalvik 运行时，且只支持单个 DEX 文件。方法数超过 65536 限制的应用需要使用 Multidex 支持。在冷启动时，系统需要加载主 DEX，然后由 MultiDex.install() 在主线程上从 APK 中提取并加载其他 DEX 文件。这个过程涉及大量的 IO 操作，在低端设备上可能耗时数秒。

Android 5.0+ 使用 ART 运行时，原生支持多 DEX，这个问题基本消失。但由于 Android 5.0 以下的市场份额已经极低，大多数应用不再需要处理这个问题。

### 数据库初始化

数据库初始化（尤其是使用 SQLCipher 加密数据库时）是一个常见的耗时操作。SQLCipher 的首次加载需要初始化 OpenSSL 库，这可能在低端设备上消耗 100-300ms。优化方式是将数据库初始化推迟到真正需要访问数据时，或者在后台线程预加载。

### ContentProvider 初始化的隐藏陷阱

[自动发现: 许多第三方 SDK 通过 ContentProvider 实现自动初始化，而 ContentProvider 的初始化发生在 Application.onCreate 之前（在 installContentProviders 中）。这意味着即使我们没有在 Application.onCreate 中显式初始化某个 SDK，它可能已经通过 ContentProvider 悄悄初始化了。来源: Android Developers Blog]

这个问题在 Android 11（API 30）开始可以通过声明工具 androidx.startup 来统一管理（见扩展小节），但在之前的版本上需要手动排查 Manifest 中声明的 ContentProvider。

## 首帧绘制的关键路径

首帧绘制是从 Activity.onResume 到用户看到画面的最后一段旅程。理解这段路径，是优化启动感知的前提。

### inflate：布局文件的解析

setContentView() 调用后，系统会将 XML 布局文件解析成 View 对象树。这个过程使用 LayoutInflater，通过反射创建 XML 中声明的每个 View。对于一个中等复杂度的页面（50-100 个 View），inflate 操作在高端设备上可能只需 5-10ms，但在低端设备上可能达到 30-50ms。

优化策略包括使用 AsyncLayoutInflater（异步 inflate，不阻塞主线程的首帧）、使用 ViewStub 延迟加载非首屏必要的布局、减少布局层级。

### measure → layout：View 树的测量和布局

inflate 完成后，View 树已经构建好，但每个 View 的大小和位置还没有确定。performTraversals 中的 performMeasure 和 performLayout 就是做这件事。

measure 阶段从 DecorView 开始递归调用每个 View/ViewGroup 的 onMeasure()，确定每个 View 的期望大小。layout 阶段从 DecorView 开始递归调用每个 View/ViewGroup 的 onLayout()，确定每个 View 在屏幕上的实际位置。

这两个阶段的开销取决于 View 树的复杂度。嵌套的 LinearLayout（尤其是 weight 属性）会导致多次 measure，RelativeLayout 也可能触发二次测量。优化布局结构（使用 ConstraintLayout 替代嵌套布局）可以显著减少这部分的耗时。

### draw：真正画出像素

measure 和 layout 完成后，就进入 draw 阶段。在硬件加速开启的情况下，这个过程分为两步：

**主线程记录 DisplayList**：performDraw() 遍历 View 树，每个 View 的 onDraw() 不是真正执行绘制命令，而是将绘制操作记录到一个 DisplayList 中（"画一条线"、"填充一个矩形" 等）。

**RenderThread 执行绘制**：DrawFrameTask 在 RenderThread 中执行，将 DisplayList 中的命令翻译为 OpenGL/Vulkan 绘制调用，渲染到从 SurfaceFlinger 申请的 Buffer 上。完成后通过 queueBuffer 提交给 SurfaceFlinger。

首帧绘制完成后，system_server 的 ActivityMetricsLogger 记录完成时间，这就是 TTID 的终点。至此，整个冷启动流程结束。

[图：首帧绘制的关键路径——从 performTraversals 到 queueBuffer，标注主线程和 RenderThread 的分工]

## Baseline Profile 与 Cloud Profile

[来源: obsidian/Cubox/Android 强推的 Baseline Profiles 国内能用吗？我找 Google 工程师求证了！ - 掘金-2022-07-17.md]

在 Android 7.0（API 24）之前，ART 采用的是 AOT（Ahead-Of-Time）全量编译策略——安装时将所有 DEX 字节码编译为本地机器码。这带来了运行时的性能提升，但代价是安装时间极长和存储空间占用巨大。

从 Android 7.0 开始，ART 转向了混合编译策略（Profile-Guided Compilation）：应用首次安装时只做解释执行（不编译），在运行过程中收集"热点代码"的 Profile（哪些方法被频繁调用），然后在设备空闲时根据 Profile 对热点代码进行后台编译。

Baseline Profile 的核心思想是：与其等系统自动收集 Profile，不如由开发者主动提供一份"启动时一定会用到的代码路径"的 Profile，让系统在安装时（或下次后台优化时）就提前编译这些代码路径。

实测数据表明，对于中大型应用，Baseline Profile 可以将冷启动时间缩短 20%-40%。效果取决于应用自身的复杂度——越复杂的应用，DEX 中"冷路径"越多，Baseline Profile 带来的提升越明显。

### Cloud Profile：不依赖应用更新的 Profile 下发

Baseline Profile 需要打包在 APK 中（或通过 AndroidX BaselineProfile Gradle 插件生成），这意味着开发者需要在应用更新中才能更新 Profile。Android 15 引入了 Cloud Profile 机制：Google Play 可以下发由平台收集的聚合 Profile（基于大量用户的使用数据），不需要应用更新。这意味着即使没有在自己的 APK 中打包 Baseline Profile，Google Play 也能提供一份。

但需要注意的是，Cloud Profile 在国内的 Google Play 服务不可用的环境下无法使用。

## App Startup Library：统一初始化入口

[已验证: 官方文档, developer.android.com/topic/libraries/app-startup]

AndroidX App Startup 库解决的问题是：多个 SDK 通过 ContentProvider 初始化导致的启动开销。

没有 App Startup 时，每个 SDK 声明自己的 ContentProvider，每个 ContentProvider 在 Application.onCreate 之前独立初始化。假设有 10 个 SDK 各声明一个 ContentProvider，系统就需要创建 10 个 ContentProvider 实例，10 个 ContentProvider 实例的创建开销可达 50-100ms，不容忽视。

App Startup 的做法是：所有 SDK声明同一个 InitializationProvider（App Startup 提供的），在自己的 AndroidManifest 中通过 meta-data 声明依赖关系。App Startup 按拓扑排序顺序初始化所有 SDK，只创建一个 ContentProvider。

使用方式：

1. SDK 侧实现 Initializer 接口：

```kotlin
class MySdkInitializer : Initializer<MySdk> {
    override fun create(context: Context): MySdk {
        MySdk.init(context)
        return MySdk.getInstance()
    }
    override fun dependencies(): List<Class<out Initializer<*>>> {
        return emptyList() // 声明依赖的其他 Initializer
    }
}
```

2. 在 AndroidManifest 中声明：

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge">
    <meta-data
        android:name="com.example.MySdkInitializer"
        android:value="androidx.startup" />
</provider>
```

对于已经通过 ContentProvider 初始化的第三方 SDK，我们可以通过 App Startup 的手动初始化模式来接管它们的初始化时机，从而将初始化推迟到需要的时候。

## Zygote Preload 的贡献

[待验证: Zygote preload 列表在不同 Android 版本上的变化]

Android 系统启动时，Zygote 进程会预加载一批常用的类和资源（定义在 frameworks/base/config/preloaded-classes 和 frameworks/base/config/preloaded-drawables 中）。当 Zygote fork 出 App 进程时，这些预加载的类和资源通过 Copy-on-Write 机制共享给子进程。

这意味着应用在冷启动时不需要重新加载 Java 基础类、Android Framework 核心类、常用的 Drawable 资源等。对于大多数应用来说，Zygote preload 覆盖了 80% 以上的类加载需求。这也是为什么冷启动的进程创建阶段（fork + init）通常只需要几十到一百多毫秒——如果每次都从零加载所有类，这个时间会翻好几倍。

Zygote preload 的局限性在于：它只预加载系统级的类和资源，不会预加载应用自身的代码。Application 类、Activity 类、第三方 SDK 的类，都需要在 fork 后由子进程自己加载。这就是 Baseline Profile 的优化空间所在——通过提前编译应用侧的热点代码，减少类加载和 JIT 编译的开销。

## 与其他章节的关系

- **8.1 响应速度原理**：本章的启动流程是 8.1 中讨论的"响应速度"概念在启动场景下的具体展开。
- **1.2 系统启动全流程**：1.2 讲的是设备开机到桌面就绪的全过程，其中 Zygote 的启动和预加载为本节的冷启动奠定了基础。
- **2.4 Choreographer 与渲染流水线**：首帧绘制中的 VSync 等待和 performTraversals 由 Choreographer 驱动，详细机制在 2.4 中讲解。
- **2.5 MainThread 与 RenderThread 协作**：首帧绘制的 draw 阶段涉及主线程记录 DisplayList 和 RenderThread 执行渲染，这是 2.5 中讨论的协作模式。
- **7.1 卡顿的定义与分类**：启动超时是卡顿的一种特殊形式——首帧耗时超过了用户可接受的范围。

## 常见问题与误区

**误区一："冷启动优化就是优化 Application.onCreate"**

Application.onCreate 只是冷启动的一个环节。完整路径包括系统侧的进程调度、Binder 通信、Activity 生命周期，以及首帧绘制。如果 Application.onCreate 只花了 200ms，但冷启动仍然超过 2 秒，问题可能在布局复杂度（inflate 慢）、View 树层级过深（measure/layout 慢）或者首帧绘制等待了太多 VSync 周期。

**误区二："am start -W 测出来的时间就是用户感知的时间"**

am start -W 的 TotalTime 不包含用户点击到 Input 系统响应的这段时间（约几十毫秒），也不包含 SurfaceFlinger 合成和 LCD 更新的时间（1-2 个 VSync 周期）。真正的用户感知时间比 TotalTime 多 30-50ms 左右。对于追求极致体验的场景，需要在 Trace 中手动加上这两个时间段。

**误区三："reportFullyDrawn 调用越早越好"**

reportFullyDrawn 的调用时机应该反映"界面真正准备好"的时刻。为了追求 TTFD 数字好看而过早调用，会导致监控数据失去意义。正确的做法是在界面内容（数据、图片、交互）全部就绪后调用。

**误区四："温启动和热启动不需要优化"**

虽然温启动和热启动比冷启动快，但在低端设备上温启动仍然可能超过 1 秒。而且对于频繁切换应用的用户来说，热启动的体验同样重要。优化思路与冷启动类似：减少 onCreate/onStart 中的不必要工作。

**误区五："ContentProvider 初始化不影响启动"**

ContentProvider 的初始化发生在 Application.onCreate 之前，是启动流程的一部分。许多第三方 SDK 通过声明 ContentProvider 实现"无代码初始化"，这些隐藏的初始化开销会直接计入启动时间，而且很难在代码中直接发现。检查 AndroidManifest 中声明的 ContentProvider 是排查启动耗时的必要步骤。

## 参考资料

- [App startup time | Android Developers](https://developer.android.com/topic/performance/vitals/launch-time) [已验证: 官方文档]
- [Activity 启动速度分析方法（启动流程分析） | Light.Moon](http://light3moon.com/2021/01/19/Activity%20%E5%90%AF%E5%8A%A8%E9%80%9F%E5%BA%A6%E5%88%86%E6%9E%90%E6%96%B9%E6%B3%95%EF%BC%88%E5%90%AF%E5%8A%A8%E6%B5%81%E7%A8%8B%E5%88%86%E6%9E%90%EF%BC%89/) [来源: obsidian/Cubox/Activity 启动速度分析方法（启动流程分析） - Light.Moon-2022-04-11.md]
- [启动优化 · 基础论 · 浅析Android启动优化 | 小木箱](https://juejin.cn/post/7183144743411384375) [来源: obsidian/Cubox/启动优化 ·  基础论 ·  浅析Android启动优化-2022-12-31.md]
- [FullyDrawnReporter—一个官方冷启动耗时统计小工具 | 掘金](https://juejin.cn/post/7315265525772124223) [来源: obsidian/Cubox/FullyDrawnReporter—一个官方冷启动耗时统计小工具 - 掘金-2023-12-24.md]
- [Android 强推的 Baseline Profiles 国内能用吗？ | 朱涛·沉思录](https://juejin.cn/post/7104230480391864356) [来源: obsidian/Cubox/Android 强推的 Baseline Profiles 国内能用吗？我找 Google 工程师求证了！ - 掘金-2022-07-17.md]
- [Jetpack App Startup | Android Developers](https://developer.android.com/topic/libraries/app-startup) [已验证: 官方文档]
- [AOSP ActivityThread.java](https://cs.android.com/android/platform/superproject/+/android-15.0.0_r1:frameworks/base/core/java/android/app/ActivityThread.java) [已验证: AOSP android-15.0.0_r1]
- [AOSP TransactionExecutor.java](https://cs.android.com/android/platform/superproject/+/android-15.0.0_r1:frameworks/base/core/java/android/app/servertransaction/TransactionExecutor.java) [已验证: AOSP android-15.0.0_r1]
