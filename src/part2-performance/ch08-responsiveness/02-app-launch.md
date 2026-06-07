---

status: finalized
title: App 启动全流程
chapter: '8.2'
applicable_versions: Android 8.0 (API 26) - Android 16 (API 36)
last_verified: '2026-04-20'
last_verified_against: AOSP android-15.0.0_r1, AndroidX Activity release notes, Perfetto
  atrace docs, Android Developers baseline profiles docs
confidence: medium
sources:
- type: blog
  path: Cubox/启动优化 ·  基础论 ·  浅析Android启动优化-2022-12-31.md
- type: blog
  path: Cubox/FullyDrawnReporter-一个官方冷启动耗时统计小工具 - 掘金-2023-12-24.md
- type: blog
  path: Cubox/Activity 启动速度分析方法(启动流程分析) - Light.Moon-2022-04-11.md
- type: blog
  path: Cubox/Android 强推的 Baseline Profiles 国内能用吗?我找 Google 工程师求证了! - 掘金-2022-07-17.md
- type: official
  path: developer.android.com/topic/performance/vitals/launch-time
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/activity
- type: official
  path: https://perfetto.dev/docs/getting-started/atrace
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles
tags:
- cold-start
- warm-start
- hot-start
- TTID
- TTFD
- launch
- startup
- reportFullyDrawn
- baseline-profiles
- app-startup
- contentprovider
- process-creation
related_chapters:
- '8.1'
- '1.2'
- '1.10'
- '2.4'
- '2.5'
- '7.1'
section: '8.2'
drafted_date: '2026-04-01'
drafted_by: openclaw-task2a
reviewed_date: "2026-05-24"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
pipeline_stage: ready-to-publish
task6_state: reviewed  # updated by task2b-verifier 2026-06-08
task6_result: "pass-light-edit"
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-06-04T10:50:00+08:00"
last_task2b_at: "2026-05-19T11:32:33+08:00"
task9_reviewed_date: "2026-06-05"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-05T18:32:25+08:00"
task9_review_notes: "2026-06-05 Task9 深度复审: pass-tech-review。P0 0 / P1 0 / P2 0；ApplicationStartInfo 常量、16KB page size 数据、Perfetto/TTID 口径核对通过；无 queue pending。"
last_task9_review_log: "logs/deep-review/2026-06-05-18-deep-review.md"
p0: 0
p1: 0
p2: 0
last_task6_at: "2026-05-24T13:10:00+08:00"
last_task6_review_log: "logs/review/2026-05-24-13-review.md"
task6_review_notes: "2026-05-24 13:10 Task6 复审：pass-light-edit。L1/L2 小修 18 处；既有 Task9 P1/P2 pending 队列继续由 Task2B 处理，Task6 未新增回炉。"
last_task9_audit: "2026-05-24"
last_task9_audit_log: "logs/deep-review/2026-05-24-02-audit.md"
task6_reviewed_date: "2026-05-24"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-05
---


# App 启动全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 冷启动 / 温启动 / 热启动的定义与区别
- 🔹 冷启动完整流程:Process.start → ActivityThread → Application.onCreate → Activity.onCreate → 首帧绘制
- 🔹 TTID(Time To Initial Display)与 TTFD(Time To Full Display / reportFullyDrawn)的定义
- 🔹 启动耗时的度量方法:adb am start -W、Logcat ActivityTaskManager、Perfetto
- 🔹 Application.onCreate 中常见的耗时操作:SDK 初始化、数据库初始化、多 Dex 加载
- 🔹 首帧绘制的关键路径:inflate → measure → layout → draw

### 扩展(可选深入)

- 🔸 Baseline Profile 与 Cloud Profile 对启动速度的提升
- 🔸 App Startup Library(AndroidX)的使用与原理
- 🔸 Zygote preload 对启动速度的贡献量化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 App 启动流程

在 Perfetto 中打开一个冷启动 Trace,会看到一段横跨 system_server、SurfaceFlinger 和目标 App 三个进程的长时间线。从用户点击桌面图标到界面显示出来,中间经历了进程创建、Binder 通信、Application 初始化、Activity 生命周期、View 树构建、第一帧绘制、SurfaceFlinger 合成——整个过程可能超过 2 秒,而应用侧能优化的部分只占其中一段。

这就是完整理解启动流程的原因。如果只知道 Application.onCreate 里不能做太多事,优化范围就很有限。掌握从点击到首帧的完整路径后,才能找到所有可能的优化切入点:哪些是系统开销无法改变,哪些是应用侧可以加速,哪些是可以通过缓存机制绕过。

完整理解这条路径后,Perfetto 中的启动耗时才能被拆成具体瓶颈:区分系统耗时和应用耗时,针对不同环节制定优化策略,而不是盲目地在 Application.onCreate 里删几行代码。

## 冷启动、温启动、热启动:三种启动状态

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

Android 把应用的启动分为三种状态:冷启动(Cold Start)、温启动(Warm Start)和热启动(Hot Start)。它们的区别在于系统需要做多少工作,理解这三种状态的本质,是后续所有优化工作的基础——因为不同状态下的优化策略完全不同。

### 冷启动:从零开始

冷启动是指应用的进程不存在(从未启动过,或者被系统杀死回收了),用户点击图标后系统需要从头创建进程并初始化一切。这是耗时最长的启动方式,也是 Android Vitals 等监控平台衡量应用启动性能的基准。

[来源: obsidian/Cubox/启动优化 ·  基础论 ·  浅析Android启动优化-2022-12-31.md]

冷启动需要经历的完整路径:

1. 用户点击桌面图标 → Launcher 通过 Binder IPC 调用 startActivity
2. system_server 中的 ActivityTaskManagerService 收到请求,创建 ActivityRecord
3. system_server 发现目标进程不存在,通过 Socket 通知 Zygote fork 新进程
4. 新进程启动 ActivityThread.main(),创建主线程 Looper
5. 通过 Binder 回调 system_server,执行 bindApplication → 创建 Application 对象
6. 依次调用 Application.attachBaseContext() → Application.onCreate()
7. system_server 通过 ClientLifecycleManager 向 App 发送 LaunchActivityItem
8. App 创建 Activity 对象,依次执行 onCreate → onStart → onResume
9. 在 onResume 中创建 ViewRootImpl,注册 Choreographer 回调
10. 下一个 VSync 到来时执行 performTraversals:measure → layout → draw
11. RenderThread 通过 queueBuffer 将帧提交给 SurfaceFlinger
12. SurfaceFlinger 合成并送显

整个过程横跨三个进程(Launcher、system_server、目标 App)和一次 Zygote fork,涉及大量的 Binder IPC 和初始化工作。

### 温启动:进程在,Activity 不在

温启动是指应用的进程还活着(没有被 LMK 杀掉),但 Activity 已经被销毁了。典型场景是用户按返回键退出应用后再次打开。温启动跳过了进程创建和 Application 初始化的步骤,直接从创建 Activity 对象开始。

判断条件从代码层面看:system_server 中有目标进程的 ProcessRecord(`hasThread()` 返回 true,表示 ActivityThread 已绑定),但没有目标 Activity 的 ActivityRecord(或者 ActivityRecord 不可复用)。

温启动的路径从上面的第 7 步开始,省去了 fork 进程、创建 Application 的开销。在 Perfetto 中不会看到 "BindApplication" 这段,对于一个中等复杂度的应用,温启动通常比冷启动快 30%-50%。

### 热启动:进程和 Activity 都在

热启动是指应用进程存在且 Activity 对象也存在(通常在后台栈中)。典型场景是用户按 Home 键切到桌面后再次打开应用。这种情况下 Activity 只需要走 onRestart → onStart → onResume 生命周期,在 Perfetto 的 am 子系统中,热启动被标记为 HOT_LAUNCH。

热启动是最快的,因为连 Activity 对象都不需要重新创建。但如果系统因内存不足回收了 Activity 中的部分资源(如 Bitmap),热启动时可能需要重建这些对象,这时开销会接近温启动。

[来源: obsidian/Cubox/Activity 启动速度分析方法(启动流程分析) - Light.Moon-2022-04-11.md]

### 在 Perfetto 中区分三种启动

在 Perfetto 中可以通过以下方式判断启动类型:

- **冷启动**:存在 "BindApplication" slice,且能看到新进程的创建
- **温启动**:没有 "BindApplication",但有 "activityStart" 或 "launching" 标记
- **热启动**:只有 "activityResume" 或 "activityRestart" 标记,注意,logcat 中的 "Displayed" 信息在热启动时不会打印。

## 冷启动完整流程详解

以冷启动为线索,把从用户点击到首帧绘制的完整路径走一遍。这里关注工程化理解:每一步在干什么、为什么需要这一步、耗时大头在哪里;源码级堆栈追踪交给 Debug 工具。

[来源: obsidian/Cubox/Activity 启动速度分析方法(启动流程分析) - Light.Moon-2022-04-11.md]

### 第一阶段:从点击到 fork 进程

用户在桌面上点击应用图标,Launcher 的 onClick 回调被触发。这看似一个简单的函数调用,背后却涉及多个系统组件的协调。

Launcher 调用 startActivity(),经过几层封装后通过 Binder IPC 发送请求到 system_server 中的 ActivityTaskManagerService(ATMS)。ATMS 的 ActivityStarter 收到请求后,会通过 ActivityMetricsLogger 记录一个时间戳——这个时间戳就是后续所有启动耗时度量的起点(TTID 的起点)。

然后 ATMS 创建 ActivityRecord 和 Task(旧版本/Android 10 前后资料中常写 TaskRecord,Android 15 源码中任务容器类为 `services/core/java/com/android/server/wm/Task.java`),检查是否有可以复用的 Activity。冷启动场景下,答案是没有。ATMS 接着会向前一个处于 Resumed 状态的 Activity(通常是 Launcher)发送 Pause 请求。这个 Pause 请求通过 ClientLifecycleManager 机制发送到 Launcher 进程,Launcher 处理 onPause 后通过 Binder 通知 ATMS 完成。

ATMS 确认 Pause 完成后,检查目标进程是否存在。冷启动场景下,目标进程不存在,于是通过 Local Socket 向 Zygote 发送 fork 请求。Zygote fork 出子进程后,将 PID 返回给 system_server。

这一阶段的开销主要是:Binder IPC(2 次跨进程调用)、Zygote fork(创建新进程)、以及 system_server 内部的调度逻辑。在 Perfetto 中,可以在 system_server 进程中看到 "launching: xxx" 的 slice,在 app 进程中看到 "BindApplication" 的开始。

#### 16KB Page Size 对启动 I/O 的削峰作用

Android 15 在部分设备上引入了 16KB 内存页(传统为 4KB)。页表项减少约 75%,TLB 覆盖范围扩大约 4 倍（单条 TLB entry 覆盖的地址空间从 4KB 变为 16KB）。这对冷启动中涉及大 so 库加载的环节有直接的 I/O 削峰效果。

冷启动的进程创建阶段需要通过 `mmap` 加载 `libart.so`(~10MB)、`libwebviewchromium.so`(~50MB)等大型共享库。在 4KB 页环境下,每个库的页表条目数量庞大,内核需要完成大量 page fault 处理才能建立完整的地址映射。16KB 页将映射粒度放大 4 倍,相同范围的虚拟地址只需要 1/4 的页表条目,减少了 page fault 中断次数和内核态耗时。

根据 Google 公布的基准测试数据,16KB 页在冷启动场景下的平均提速幅度约 3.16%,对于依赖大型本地库的应用(如集成 WebView 或 ML 推理引擎的应用),提升更为明显。Zygote 的 Copy-on-Write 机制同样受益:虽然单页拷贝的数据量变大(16KB vs 4KB),但触发 COW 的 page fault 次数减少,对于依赖大量静态资源的 App,冷启动的内核态损耗会降低。

在 Perfetto 中可以通过对比 4KB 和 16KB 设备上同一 App 的 `BindApplication` 前置耗时来验证这一收益。重点关注 fork 到 `ActivityThread.main()` 之间的时间差。

### 第二阶段:进程初始化与 Application 创建

fork 出来的子进程从 ActivityThread.main() 开始执行。这个 main() 函数做了两件关键的事:

**创建主线程 Looper**。调用 Looper.prepareMainLooper() 和 Looper.loop(),建立起 Android 主线程的消息循环。此后所有与 UI 相关的操作都通过这个 Looper 分发。

**通知 system_server 进程已就绪**。通过 Binder 调用 ATMS 的 attachApplication() 和 AMS 的 attachApplication()。ATMS 收到通知后,会继续后续的 Activity 启动流程。注意,这个时候主线程的 Looper.loop() 还没开始循环(或者刚开始),因为 attachApplication 的调用是在 main() 函数中同步完成的,而后续的消息处理要等 loop() 跑起来才行。

AMS 的 attachApplication 会触发 bindApplication,这会向主线程发送一条 BIND_APPLICATION 消息。Looper 开始循环后处理这条消息时,创建 Application 对象。如果 AndroidManifest.xml 中声明了自定义的 Application 类,系统会通过反射创建 Application 实例,然后依次调用:

1. Application.attachBaseContext()——这是应用侧最早能介入的回调
2. Application.onCreate()——大多数 SDK 初始化代码放在这里

[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java: handleBindApplication]

这个阶段通常是应用侧启动耗时的集中区域。一个中等规模的应用可能在 Application.onCreate 中初始化 10-20 个 SDK(埋点、推送、网络、图片加载、数据库等),每个 SDK 几十到几百毫秒,加起来可能超过 1 秒。后续 8.3 会专门讨论 Application.onCreate 的优化策略。

### 第三阶段:Activity 创建与生命周期

Application 初始化完成后,system_server 通过 ClientLifecycleManager 向 App 发送 ClientTransaction,其中包含 LaunchActivityItem(设置在 mActivityCallbacks 中)和 ResumeActivityItem(设置在 mLifecycleStateRequest 中)。

App 的 ActivityThread 在主线程处理 EXECUTE_TRANSACTION 消息。TransactionExecutor 按顺序执行:

**先执行 callback**:LaunchActivityItem.execute() → 调用 handleLaunchActivity() → performLaunchActivity()。这一步创建 Activity 对象(通过反射),调用 Activity.attach() 初始化(创建 PhoneWindow),然后调用 Activity.onCreate()。常规有 UI 的 Activity 通常在 onCreate 中调用 `setContentView()`(或 Compose 的 `setContent {}`)来安装首屏内容。`setContentView` 的本质是将布局文件 inflate 后挂载到 `PhoneWindow` 的 `mContentParent` 中。Activity 框架并不强制要求调用 `setContentView`——不调用时 Activity 会显示空窗口;无 UI Activity(如只做后台操作的 Activity)或延迟安装内容的设计也是合法的。

**然后执行生命周期路径补全**:从 ON_CREATE 到 ON_RESUME,中间需要补 ON_START。依次调用 Activity.onStart()、Activity.onResume()。

[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/app/servertransaction/TransactionExecutor.java]

### 第四阶段:首帧绘制

Activity.onResume() 执行完后,并不是立刻就能看到界面。绘制操作是延后执行的。

在 onResume 的处理过程中,WindowManager 会将 DecorView 添加到 WindowManagerGlobal 中,这会创建 ViewRootImpl。ViewRootImpl 做了两件事:

**请求布局**:调用 requestLayout(),这是通过 Choreographer 向主线程 post 一个回调(TRAVERSAL)。注意,这个回调不会立即执行——它要等下一个 VSync 信号到来。

**创建 SurfaceSession 连接**:通过 IWindowSession.addWindow() 向 WindowManagerService 注册窗口。WMS 会与 SurfaceFlinger 建立连接,为这个窗口创建 Layer 和 BufferQueue。

当下一个 VSync 信号到来时,Choreographer 回调触发 ViewRootImpl.performTraversals()。这里开始执行实际的绘制操作:

**relayoutWindow**:第一次执行时,向 SurfaceFlinger 申请完成窗口 Surface 的布局和属性设置。Surface 创建路径因 Android 版本而异:

- **Android 10 及之前**:ViewRootImpl 通过 `IWindowSession.relayout()` 向 WMS 申请创建 Surface,WMS 在 SurfaceFlinger 侧创建 `BufferQueueLayer`,返回 `IGraphicBufferProducer`。
- **Android 11+**:ViewRootImpl 改为 `updateBlastSurfaceIfNeeded()`,围绕 `SurfaceControl` 创建/更新 `BLASTBufferQueue`。`BLASTBufferQueue` 负责管理应用端的 BufferQueue producer,SurfaceFlinger 侧由 `BufferStateLayer`(替换旧 `BufferQueueLayer`)接管消费者逻辑。

**performMeasure**:从 DecorView 开始递归测量整棵 View 树,确定每个 View 的大小。

**performLayout**:从 DecorView 开始递归布局,确定每个 View 在父容器中的位置。

**performDraw**:在硬件加速开启的情况下(Android 4.4+ 默认开启),View 的 onDraw() 并不直接执行绘制命令,而是将绘制指令记录到 DisplayList 中。然后 ViewRootImpl 向 RenderThread post 一个 DrawFrameTask,由 RenderThread 统一执行 OpenGL 绘制命令。

RenderThread 完成绘制后,通过 IGraphicBufferProducer.queueBuffer() 将帧提交给 SurfaceFlinger。queueBuffer 返回后,系统在 WMS/ActivityRecord 中记录 windows drawn 时间戳,这就是系统统计的 TTID 终点。SurfaceFlinger 在下一个 VSync-sf 信号到来时完成合成和送显,用户才能在屏幕上看到画面。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time, AOSP ActivityRecord.java]

[图:冷启动完整时序图——从用户点击到首帧显示,标注 system_server、Zygote、App 主线程、RenderThread、SurfaceFlinger 各进程的参与环节]

> 注意:`queueBuffer` 返回 ≠ 用户看到画面。SurfaceFlinger 合成和物理送显还有一到两个 VSync 周期的延迟。Android 11+ 的 BLAST 路径中,应用端通过 `BLASTBufferQueue` 提交帧后,SurfaceFlinger 还需要完成 `Layer::onPostComposition()` 和硬件 composer 的 `onPresent()`。追踪完整送显链路时,Android 15 的 `ApplicationStartInfo` 提供了 `START_TIMESTAMP_SURFACEFLINGER_COMPOSITION_COMPLETE` 和 `START_TIMESTAMP_INITIAL_RENDERTHREAD_FRAME`。

## TTID 与 TTFD:两个关键的启动指标

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

启动流程明确之后,下一步是度量启动性能。Android 定义了两个关键指标:

### TTID(Time To Initial Display)

TTID 是从用户触发启动(点击图标)到首帧绘制完成的时间。系统通过 ActivityMetricsLogger 自动统计这个时间,logcat 中的 "Displayed" 行和 `am start -W` 的 TotalTime 都对应这个口径:

```text
ActivityTaskManager: Displayed com.example.app/.MainActivity: +1s234ms
```

或者通过 `adb shell am start -W` 命令的 TotalTime 字段获取。

TTID 是 Android Vitals 等平台监控的核心指标。Google 建议 TTID 不应超过 5 秒(冷启动),否则被视为性能过差。

[已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java]

### TTFD(Time To Full Display)

TTID 只统计到首帧绘制,但很多应用的界面在首帧绘制时并没有显示完整内容——数据还在从网络加载,或者数据库还在查询。用户看到的是一个加载骨架或者空白区域。为了让度量更贴近用户实际感知,Android 提供了 TTFD(Time To Full Display)指标。

TTFD 需要开发者在代码中主动调用 `Activity.reportFullyDrawn()` 来告诉系统"我的界面完全准备好了"。调用后 logcat 中会出现:

```text
ActivityTaskManager: Fully drawn com.example.app/.MainActivity: +2s156ms
```

[来源: obsidian/Cubox/FullyDrawnReporter-一个官方冷启动耗时统计小工具 - 掘金-2023-12-24.md]

### FullyDrawnReporter:多条件 TTFD 统计

如果应用的界面需要等待多个异步任务(比如同时发起 A、B、C 三个网络请求,全部完成后才算界面完整),AndroidX Activity 1.7.0 就已经提供了 `FullyDrawnReporter`。1.8.x 主要是后续修复和兼容性调整,不是首次引入。

`ComponentActivity` 持有 `fullyDrawnReporter`,Activity Compose 1.7.0 还提供了 `ReportDrawn`、`ReportDrawnWhen`、`ReportDrawnAfter` 这组辅助 API,用来把多个就绪信号汇总到同一个 reporter:

```kotlin
// 在每个异步任务开始前注册 reporter
override fun onResume() {
    super.onResume()

    lifecycleScope.launch {
        fullyDrawnReporter.addReporter()  // 注册:任务 A 开始
        val resultA = fetchNetworkDataA()
        fullyDrawnReporter.removeReporter()  // 完成:任务 A 结束
    }

    lifecycleScope.launch {
        fullyDrawnReporter.addReporter()  // 注册:任务 B 开始
        val resultB = fetchNetworkDataB()
        fullyDrawnReporter.removeReporter()  // 完成:任务 B 结束
    }
}
// 当所有 reporter 都被移除时,自动调用 reportFullyDrawn()
```

FullyDrawnReporter 内部维护一个计数器(reporterCount),每次 addReporter 加 1,每次 removeReporter 减 1。当计数器归零时,自动调用 reportFullyDrawn()。这比手动在多个回调中协调 reportFullyDrawn() 的调用时机更可靠,避免了多异步任务间的时序竞争。

[已验证: 官方文档, developer.android.com/develop/ui/views/launch/ttfd]

## Android 15+ 启动诊断:ApplicationStartInfo

Android 15 引入了 ApplicationStartInfo 结构化启动诊断能力,为启动性能分析提供了更细粒度的数据支撑。[已验证: AOSP android-15.0.0_r1, android.app.ApplicationStartInfo]

ApplicationStartInfo 是 AOSP 历史上首次将进程 fork 开始时间暴露给应用层的 API。配合 Perfetto,它可以补齐"从点击图标到 Zygote 开始工作"这段系统黑盒时间。

#### 关键字段与含义

获取入口:`ActivityManager.getHistoricalProcessStartReasons(int maxCount)` 返回 `List<ApplicationStartInfo>`,API 35(Android 15)新增。

| 字段 | 类型 | 含义 |
|---|---|---|
| `getStartType()` | int | 启动类型:`START_TYPE_COLD`(1)、`START_TYPE_WARM`(2)、`START_TYPE_HOT`(3) |
| `getStartupState()` | int | 启动当前阶段：`STARTUP_STATE_STARTED`(0) / `STARTUP_STATE_ERROR`(1) / `STARTUP_STATE_FIRST_FRAME_DRAWN`(2)。没有 `NOT_STARTED` 和 `FULLY_DRAWN` 状态——“fully drawn”通过 `START_TIMESTAMP_FULLY_DRAWN` timestamp key 表达，不是 startup state |
| `getStartupTimestamps()` | Map<Integer, Long> | 返回各阶段时间戳(clock monotonic 纳秒), AOSP 多数字段来自 `SystemClock.uptimeNanos()`,通过常量 key 读取(见下表) |
| `getReason()` | int | 启动原因常量（如 `START_REASON_ALARM`、`START_REASON_BOOT_COMPLETE`、`START_REASON_JOB`、`START_REASON_LAUNCHER`、`START_REASON_SERVICE`、`START_REASON_CONTENT_PROVIDER` 等） |

`getStartupTimestamps()` 返回的 Map 中可用的 timestamp key:

| 常量 | 含义 |
|---|---|
| `START_TIMESTAMP_LAUNCH` | 系统发起启动的时间点 |
| `START_TIMESTAMP_FORK` | Zygote fork 子进程的时间点 |
| `START_TIMESTAMP_INITIAL_RENDERTHREAD_FRAME` | 首帧在 RenderThread 完成绘制（`eglSwapBuffers` 或 `queueBuffer` 返回）的时间点 |
| `START_TIMESTAMP_BIND_APPLICATION` | 开始绑定 Application 的时间点 |
| `START_TIMESTAMP_APPLICATION_ONCREATE` | Application.onCreate() 的时间点 |
| `START_TIMESTAMP_FIRST_FRAME` | 首帧绘制完成的时间点 |
| `START_TIMESTAMP_FULLY_DRAWN` | reportFullyDrawn() 调用的时间点(未调用时 Map 中不含此 key) |
| `START_TIMESTAMP_SURFACEFLINGER_COMPOSITION_COMPLETE` | SurfaceFlinger 合成完成的时间点(API 35+) |

#### 各阶段耗时计算

通过 `getStartupTimestamps()` 中的多个时间戳,可以拆解启动各阶段的耗时:

```java
// API 35+ / Android 15+
ActivityManager am = getSystemService(ActivityManager.class);
List<ApplicationStartInfo> history = am.getHistoricalProcessStartReasons(1);
if (history != null && !history.isEmpty()) {
    ApplicationStartInfo latest = history.get(0);
    Map<Integer, Long> timestamps = latest.getStartupTimestamps();
    if (timestamps != null) {
        Long launch = timestamps.get(ApplicationStartInfo.START_TIMESTAMP_LAUNCH);
        Long fork = timestamps.get(ApplicationStartInfo.START_TIMESTAMP_FORK);
        Long bindApp = timestamps.get(ApplicationStartInfo.START_TIMESTAMP_BIND_APPLICATION);
        Long oncreate = timestamps.get(ApplicationStartInfo.START_TIMESTAMP_APPLICATION_ONCREATE);
        Long firstFrame = timestamps.get(ApplicationStartInfo.START_TIMESTAMP_FIRST_FRAME);

        // STARTUP_STATE_ERROR 不保证所有 timestamp key 都存在;
        // 即使非 ERROR 状态,某些 key 也可能缺失(如冷启动才有 FORK)
        if (launch != null && fork != null) {
            long systemForkMs = (fork - launch) / 1_000_000;
            Log.d("Startup", "System launch→fork: " + systemForkMs + "ms");
        }
        if (bindApp != null && oncreate != null) {
            long bindToOncreateMs = (oncreate - bindApp) / 1_000_000;
            Log.d("Startup", "Bind→onCreate: " + bindToOncreateMs + "ms");
        }
        Log.d("Startup", "Start type: " + latest.getStartType());
        if (launch != null && firstFrame != null) {
            long ttidMs = (firstFrame - launch) / 1_000_000;
            Log.d("Startup", "TTID: " + ttidMs + "ms");
        }
    }
}
```

#### 与 Perfetto 的联动

ApplicationStartInfo 的 timestamp 是 clock monotonic 纳秒,AOSP 内部多数字段通过 `SystemClock.uptimeNanos()` 记录（`ActivityMetricsLogger.LaunchingState.mStartUptimeNs`、`ActivityThread.handleBindApplication()` 的 `timestampApplicationOnCreateNs` 等）。Perfetto Android trace packet 默认使用 `CLOCK_BOOTTIME`，与 uptime clock 之间存在 suspend offset 差异（设备休眠期间 uptime 停止计时，boottime 继续）。直接把 `getStartupTimestamps()` 返回的原始 ns 值叠到 Perfetto UI/SQL 时间轴，在经历过 suspend 的设备上会偏移。

推荐的对齐方式：优先通过 trace_processor 的 `ClockSnapshot` 做跨时钟域转换，把 ApplicationStartInfo 的 uptime ns 映射到 Perfetto 的 boottime 时间轴；或只在 ApplicationStartInfo 内部 timestamp 之间做差（同属 uptime clock domain，差值不受 suspend 影响）。

推荐的分析流程:

1. 在 Perfetto 中找到 `launchingActivity#...` 的起点(system_server 侧),这是系统视角的启动起点
2. 用 `START_TIMESTAMP_LAUNCH` 对齐到同一时间轴
3. 用 `START_TIMESTAMP_FORK` 与 `START_TIMESTAMP_BIND_APPLICATION` 的差值,量化 Zygote fork + 进程初始化的系统开销
4. 在 Perfetto 中定位 App 进程的 `BindApplication` slice 开始位置,验证两者一致性
5. 用 `START_TIMESTAMP_FIRST_FRAME` 与 `START_TIMESTAMP_SURFACEFLINGER_COMPOSITION_COMPLETE` 拆分首帧绘制和送显两个阶段

[已验证: AOSP android-15.0.0_r1, android.app.ApplicationStartInfo, API 35]

## 启动耗时的度量方法

指标定义明确之后,还要选择合适的度量工具。不同的工具有不同的精度和适用场景。

### adb am start -W:最直接的线下测量

```bash
adb shell am start -W com.example.app/.MainActivity
```

输出:

```text
Status: ok
LaunchState: COLD
Activity: com.example.app/.MainActivity
TotalTime: 1234
WaitTime: 1250
Complete
```

这里有几个关键信息:

- **LaunchState**:启动类型(COLD/WARM/HOT),帮助确认当前测试的是哪种启动场景
- **TotalTime**:从 startActivity 发起(ActivityMetricsLogger 记录的起始时间)到首帧绘制完成的时间,等于 TTID
- **WaitTime**:从命令调用到命令返回的总等待时间,比 TotalTime 略多,因为包含了命令本身的调度开销

加 `-S` 参数可以强制先 kill 进程再启动,确保一定是冷启动:

```bash
adb shell am start -W -S com.example.app/.MainActivity
```

[来源: obsidian/Cubox/Activity 启动速度分析方法(启动流程分析) - Light.Moon-2022-04-11.md]

### Logcat:快速查看启动时间

在启动应用后过滤 logcat:

```bash
adb logcat | grep -E "Displayed|Fully drawn"
```

- `Displayed` 对应 TTID
- `Fully drawn` 对应 TTFD(需要应用主动调用 reportFullyDrawn)

### Perfetto:精确定位每个阶段

Perfetto 是分析启动性能最重要的工具,因为它能展示启动过程中每个阶段的精确耗时。

抓取启动 Perfetto 的推荐配置:

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
            atrace_apps: "com.example.app"
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

system_server 和应用进程的采集条件要分开看。`atrace_categories: "am"` 负责拿到 system_server 里的启动切片;应用侧的 `performTraversals`、`DrawFrame`、`queueBuffer`、自定义 `Trace` marker 要靠 `atrace_apps` 打开目标进程的 atrace 通道。只配 category 不配 app,App 进程里的 `view` / `gfx` / `dalvik` slice 往往不会稳定出现。排查单个应用时填包名,做通用模板时可以改成 `atrace_apps: "*"`。

在 Perfetto 中应关注这些关键 slice:

| Slice 名称 | 所在进程 | 含义 |
|---|---|---|
| `launchingActivity#...` / `launching: xxx` | system_server | ActivityMetricsLogger 的启动区间,从 `notifyActivityLaunching()` 建立 `LaunchingState` 到首帧完成 |
| `BindApplication` | App 进程 | Application 对象创建和初始化 |
| `activityCreate` / `activityStart` / `activityResume` | App 进程 | Activity 生命周期的各阶段 |
| `performTraversals` | App 主线程 | View 树的 measure/layout/draw |
| `DrawFrame` | RenderThread | GPU 渲染 |
| `queueBuffer` | RenderThread | 帧提交给 SurfaceFlinger |

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

### 各度量方法的口径

这几种工具共享同一条启动主线,但展示粒度不同:

- **Displayed / am start -W TotalTime**:以 `ActivityMetricsLogger.notifyActivityLaunching()` 建立启动记录的时刻为起点,到首帧绘制完成结束
- **Perfetto `launching: xxx` / `launchingActivity#...`**:复用同一份 `LaunchingState`,起点同样是 `notifyActivityLaunching()`;`notifyActivityLaunched()` 负责把已解析的目标 Activity 挂到这次启动记录上,不是计时起点
- **`reportFullyDrawn()`**:起点和 TTID 一样,结束时间由应用主动声明

三者的差别主要在可观测粒度和结束点:`notifyActivityLaunched()` 负责把已解析的目标 Activity 挂到启动记录上,不是计时起点。想拆分 system_server、App 主线程、RenderThread 各段耗时,用 Perfetto;想做批量回归或自动化门禁,用 `am start -W` 和 `Displayed` 更直接。

[来源: obsidian/Cubox/Activity 启动速度分析方法(启动流程分析) - Light.Moon-2022-04-11.md]

## Application.onCreate 中常见的耗时操作

度量方法明确之后,再看应用侧优化的重点区域。Application.onCreate 是应用启动流程中开发者能控制的第一个回调,也是最常见的性能瓶颈所在。

### SDK 初始化:常见耗时来源

一个中等规模的应用可能在 Application.onCreate 中初始化以下 SDK:

- 埋点/分析(友盟、神策等):通常 50-200ms
- 推送服务(FCM、华为/小米推送):50-150ms
- 网络库初始化(OkHttp 配置、证书固定):20-50ms
- 图片加载库(Glide/Coil 配置):10-30ms
- 数据库初始化(Room/SQLCipher):50-200ms
- 热修复框架:100-300ms
- APM 监控:20-50ms

单独看每个 SDK 的初始化时间都不长,但 10-20 个 SDK 串行初始化的累积效果可能达到 1-2 秒。而且很多 SDK 的初始化并不需要在首帧显示前完成——它们只是"习惯性"地放在了 Application.onCreate 里。

优化思路不是本节的重点(在 8.3 启动优化策略中会详细讨论),但核心原则是:**区分哪些初始化是首帧必需的,哪些可以延迟**。只有影响首帧显示的初始化才需要在 Application.onCreate 中同步执行,其余的都应该延迟到首帧之后。

### 多 Dex 加载

[适用版本: Android 5.0 之前, API < 21]

在 Android 5.0(API 21)之前,系统使用 Dalvik 运行时,且只支持单个 DEX 文件。方法数超过 65536 限制的应用需要使用 Multidex 支持。在冷启动时,系统需要加载主 DEX,然后由 MultiDex.install() 在主线程上从 APK 中提取并加载其他 DEX 文件。这个过程涉及大量的 IO 操作,在低端设备上可能耗时数秒。

Android 5.0+ 使用 ART 运行时,原生支持多 DEX,这个问题基本消失。但由于 Android 5.0 以下的市场份额已经极低,大多数应用不再需要处理这个问题。

### 数据库初始化

数据库初始化(尤其是使用 SQLCipher 加密数据库时)是一个常见的耗时操作。SQLCipher 的首次加载需要初始化 OpenSSL 库,这可能在低端设备上消耗 100-300ms。优化方式是将数据库初始化推迟到需要访问数据时,或者在后台线程预加载。

### ContentProvider 初始化的隐藏陷阱

许多第三方 SDK 通过 ContentProvider 实现自动初始化,而 ContentProvider 的初始化发生在 Application.onCreate 之前(在 `installContentProviders` 中)。即使应用没有在 Application.onCreate 中显式初始化某个 SDK,它也可能已经通过 ContentProvider 悄悄初始化。

这个问题可以通过 AndroidX App Startup(`startup-runtime`,支持 API 14+)来统一管理(见扩展小节)。App Startup 是 Jetpack 库,不是 Android 11 的平台能力,在 Android 11 之前同样可以使用。但它基于单个 `InitializationProvider`,无法自动接管未适配的三方 ContentProvider,未适配的 SDK 仍然需要手动排查 Manifest。

## 首帧绘制的关键路径

首帧绘制是从 Activity.onResume 到用户看到画面的收尾路径。看清这段路径,才能优化启动感知。

### inflate:布局文件的解析

setContentView() 调用后,系统会将 XML 布局文件解析成 View 对象树。这个过程使用 LayoutInflater,通过反射创建 XML 中声明的每个 View。对于一个中等复杂度的页面(50-100 个 View),inflate 操作在高端设备上可能只需 5-10ms,但在低端设备上可能达到 30-50ms。

优化策略包括使用 AsyncLayoutInflater(异步 inflate,不阻塞主线程的首帧)、使用 ViewStub 延迟加载非首屏必要的布局、减少布局层级。

### measure → layout:View 树的测量和布局

inflate 完成后,View 树已经构建好,但每个 View 的大小和位置还没有确定。performTraversals 中的 performMeasure 和 performLayout 就是做这件事。

measure 阶段从 DecorView 开始递归调用每个 View/ViewGroup 的 onMeasure(),确定每个 View 的期望大小。layout 阶段从 DecorView 开始递归调用每个 View/ViewGroup 的 onLayout(),确定每个 View 在屏幕上的实际位置。

这两个阶段的开销取决于 View 树的复杂度。嵌套的 LinearLayout(尤其是 weight 属性)会导致多次 measure,RelativeLayout 也可能触发二次测量。优化布局结构(使用 ConstraintLayout 替代嵌套布局)可以显著减少这部分的耗时。

### draw:记录与提交绘制命令

measure 和 layout 完成后,就进入 draw 阶段。在硬件加速开启的情况下,这个过程分为两步:

**主线程记录 DisplayList**:performDraw() 遍历 View 树,每个 View 的 onDraw() 不执行绘制命令,而是将绘制操作记录到一个 DisplayList 中("画一条线"、"填充一个矩形" 等)。

**RenderThread 执行绘制**:DrawFrameTask 在 RenderThread 中执行,将 DisplayList 中的命令翻译为 OpenGL/Vulkan 绘制调用,渲染到从 SurfaceFlinger 申请的 Buffer 上。完成后通过 queueBuffer 提交给 SurfaceFlinger。

首帧绘制完成后,system_server 的 ActivityMetricsLogger 记录完成时间,这就是 TTID 的终点。至此,整个冷启动流程结束。

[图:首帧绘制的关键路径——从 performTraversals 到 queueBuffer,标注主线程和 RenderThread 的分工]

## Baseline Profile 与 Cloud Profile

[来源: obsidian/Cubox/Android 强推的 Baseline Profiles 国内能用吗?我找 Google 工程师求证了! - 掘金-2022-07-17.md]

在 Android 7.0(API 24)之前,ART 采用的是 AOT(Ahead-Of-Time)全量编译策略——安装时将所有 DEX 字节码编译为本地机器码。这带来了运行时的性能提升,但代价是安装时间极长和存储空间占用巨大。

从 Android 7.0 开始,ART 转向了混合编译策略(Profile-Guided Compilation):应用首次安装时只做解释执行(不编译),在运行过程中收集"热点代码"的 Profile(哪些方法被频繁调用),然后在设备空闲时根据 Profile 对热点代码进行后台编译。

Baseline Profile 的核心思想是:与其等系统自动收集 Profile,不如由开发者主动提供一份"启动时一定会用到的代码路径"的 Profile,让系统在安装时(或下次后台优化时)就提前编译这些代码路径。

实测数据表明,对于中大型应用,Baseline Profile 可以将冷启动时间缩短 20%-40%。效果取决于应用自身的复杂度——越复杂的应用,DEX 中"冷路径"越多,Baseline Profile 带来的提升越明显。

### Cloud Profile:不依赖应用更新的 Profile 下发

Baseline Profile 需要打包在 APK 中(或通过 AndroidX BaselineProfile Gradle 插件生成),开发者发版时就能把启动关键路径一起交付给用户。Cloud Profile 不是 Android 15 才出现的新机制。Android 9 及以上的 Google Play 安装流程就会把聚合后的运行时 Profile 分发给后续安装或更新的设备,用来补齐真实用户热点执行路径。

Cloud Profile 依赖 Google Play 的安装和分发流程。国内常见的无 Play 环境通常拿不到这部分,只能依赖 APK 内自带的 Baseline Profile,以及设备本地运行后逐步生成的 ART Profile。

## App Startup Library:统一初始化入口

[已验证: 官方文档, developer.android.com/topic/libraries/app-startup]

AndroidX App Startup 库针对的是多个 SDK 通过 ContentProvider 初始化导致的启动开销。

没有 App Startup 时,每个 SDK 声明自己的 ContentProvider,每个 ContentProvider 在 Application.onCreate 之前独立初始化。假设有 10 个 SDK 各声明一个 ContentProvider,系统就需要创建 10 个 ContentProvider 实例,10 个 ContentProvider 实例的创建开销可达 50-100ms,不容忽视。

App Startup 的做法是:所有 SDK声明同一个 InitializationProvider(App Startup 提供的),在自己的 AndroidManifest 中通过 meta-data 声明依赖关系。App Startup 按拓扑排序顺序初始化所有 SDK,只创建一个 ContentProvider。

使用方式:

1. SDK 侧实现 Initializer 接口:

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

2. 在 AndroidManifest 中声明:

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

对于已经通过 ContentProvider 初始化的第三方 SDK,可以通过 App Startup 的手动初始化模式来接管它们的初始化时机,从而将初始化推迟到需要的时候。

## Zygote Preload 的贡献

[待验证: Zygote preload 列表在不同 Android 版本上的变化]

Android 系统启动时,Zygote 进程会预加载一批常用的类和资源。预加载类列表定义在 `frameworks/base/config/preloaded-classes`;预加载 Drawable 和 ColorStateList 定义在 `frameworks/base/core/res/res/values/arrays.xml` 的 `preloaded_drawables` 和 `preloaded_color_state_lists` 数组中。当 Zygote fork 出 App 进程时,这些预加载的类和资源通过 Copy-on-Write 机制共享给子进程。

这些预加载内容让应用在冷启动时不需要重新加载 Java 基础类、Android Framework 核心类、常用的 Drawable 资源等。对于大多数应用来说,Zygote preload 覆盖了 80% 以上的类加载需求。这也是为什么冷启动的进程创建阶段(fork + init)通常只需要几十到一百多毫秒——如果每次都从零加载所有类,这个时间会翻好几倍。

Zygote preload 的局限性在于:它只预加载系统级的类和资源,不会预加载应用自身的代码。Application 类、Activity 类、第三方 SDK 的类,都需要在 fork 后由子进程自己加载。这就是 Baseline Profile 的优化空间所在——通过提前编译应用侧的热点代码,减少类加载和 JIT 编译的开销。

## 与其他章节的关系

- **8.1 响应速度原理**:本章的启动流程是 8.1 中讨论的"响应速度"概念在启动场景下的具体展开。
- **1.2 系统启动全流程**:1.2 讲的是设备开机到桌面就绪的全过程,其中 Zygote 的启动和预加载为本节的冷启动奠定了基础。
- **2.4 Choreographer 与渲染流水线**:首帧绘制中的 VSync 等待和 performTraversals 由 Choreographer 驱动,详细机制在 2.4 中讲解。
- **2.5 MainThread 与 RenderThread 协作**:首帧绘制的 draw 阶段涉及主线程记录 DisplayList 和 RenderThread 执行渲染,这是 2.5 中讨论的协作模式。
- **7.1 卡顿的定义与分类**:启动超时是卡顿的一种特殊形式——首帧耗时超过了用户可接受的范围。

## 常见问题与误区

**误区一:"冷启动优化就是优化 Application.onCreate"**

Application.onCreate 只是冷启动的一个环节。完整路径包括系统侧的进程调度、Binder 通信、Activity 生命周期,以及首帧绘制。如果 Application.onCreate 只花了 200ms,但冷启动仍然超过 2 秒,问题可能在布局复杂度(inflate 慢)、View 树层级过深(measure/layout 慢)或者首帧绘制等待了太多 VSync 周期。

**误区二:"am start -W 测出来的时间就是用户感知的时间"**

am start -W 的 TotalTime 不包含用户点击到 Input 系统响应的这段时间(约几十毫秒),也不包含 SurfaceFlinger 合成和 LCD 更新的时间(1-2 个 VSync 周期)。用户感知时间比 TotalTime 多 30-50ms 左右。对于追求极致体验的场景,需要在 Trace 中手动加上这两个时间段。

**误区三:"reportFullyDrawn 调用越早越好"**

reportFullyDrawn 的调用时机应该反映"界面准备好"的时刻。为了追求 TTFD 数字好看而过早调用,会导致监控数据失去意义。正确的做法是在界面内容(数据、图片、交互)全部就绪后调用。

**误区四:"温启动和热启动不需要优化"**

虽然温启动和热启动比冷启动快,但在低端设备上温启动仍然可能超过 1 秒。而且对于频繁切换应用的用户来说,热启动的体验同样重要。优化思路与冷启动类似:减少 onCreate/onStart 中的不必要工作。

**误区五:"ContentProvider 初始化不影响启动"**

ContentProvider 的初始化发生在 Application.onCreate 之前,是启动流程的一部分。许多第三方 SDK 通过声明 ContentProvider 实现"无代码初始化",这些隐藏的初始化开销会直接计入启动时间,而且很难在代码中直接发现。检查 AndroidManifest 中声明的 ContentProvider 是排查启动耗时的必要步骤。

## 参考资料

- [App startup time | Android Developers](https://developer.android.com/topic/performance/vitals/launch-time) [已验证: 官方文档]
- [Activity 启动速度分析方法(启动流程分析) | Light.Moon](http://light3moon.com/2021/01/19/Activity%20%E5%90%AF%E5%8A%A8%E9%80%9F%E5%BA%A6%E5%88%86%E6%9E%90%E6%96%B9%E6%B3%95%EF%BC%88%E5%90%AF%E5%8A%A8%E6%B5%81%E7%A8%8B%E5%88%86%E6%9E%90%EF%BC%89/) [来源: obsidian/Cubox/Activity 启动速度分析方法(启动流程分析) - Light.Moon-2022-04-11.md]
- [启动优化 · 基础论 · 浅析Android启动优化 | 小木箱](https://juejin.cn/post/7183144743411384375) [来源: obsidian/Cubox/启动优化 ·  基础论 ·  浅析Android启动优化-2022-12-31.md]
- [FullyDrawnReporter-一个官方冷启动耗时统计小工具 | 掘金](https://juejin.cn/post/7315265525772124223) [来源: obsidian/Cubox/FullyDrawnReporter-一个官方冷启动耗时统计小工具 - 掘金-2023-12-24.md]
- [Android 强推的 Baseline Profiles 国内能用吗? | 朱涛·沉思录](https://juejin.cn/post/7104230480391864356) [来源: obsidian/Cubox/Android 强推的 Baseline Profiles 国内能用吗?我找 Google 工程师求证了! - 掘金-2022-07-17.md]
- [AndroidX Activity release notes](https://developer.android.com/jetpack/androidx/releases/activity) [已验证: 官方文档]
- [Instrumenting Android apps/platform with atrace | Perfetto](https://perfetto.dev/docs/getting-started/atrace) [已验证: 官方文档]
- [Baseline Profiles | Android Developers](https://developer.android.com/topic/performance/baselineprofiles) [已验证: 官方文档]
- [Jetpack App Startup | Android Developers](https://developer.android.com/topic/libraries/app-startup) [已验证: 官方文档]
- [AOSP ActivityThread.java](https://cs.android.com/android/platform/superproject/+/android-15.0.0_r1:frameworks/base/core/java/android/app/ActivityThread.java) [已验证: AOSP android-15.0.0_r1]
- [AOSP TransactionExecutor.java](https://cs.android.com/android/platform/superproject/+/android-15.0.0_r1:frameworks/base/core/java/android/app/servertransaction/TransactionExecutor.java) [已验证: AOSP android-15.0.0_r1]
### Android 安装优化机制与厂商定制边界
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-14-android-install-optimization-aosp-mechanism.md
- 类型:DeepResearch 调研结果
- 摘要:Android 安装优化存在两套并行机制:AOSP 标准 staged install 和厂商私有实现。核心路径链从 PackageInstallerSession.commit() 到 dex2oat,厂商在用户态调度层面介入(vivo 缩短 idle 等待窗口、小米强制 speed 全量 AOT),不涉及内核级修改。
- 注入时间:2026-05-15
- 价值:首次系统梳理安装优化完整路径链与厂商差异点,补充 ch08 启动前序环节的安装耗时分析
