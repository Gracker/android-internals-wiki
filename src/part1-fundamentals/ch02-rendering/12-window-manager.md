---
title: "Window Manager Service 与窗口管理"
chapter: "2.12"
section: "2.12"
status: finalized
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1 + kernel android17-6.18-2026-06_r6 + Android 17 official windowing/configuration documentation + rendering_pipelines S06"
confidence: high
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowManagerService.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowState.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/StartingSurfaceController.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/TransitionController.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/InputMonitor.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowSurfacePlacer.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/SurfaceSyncGroup.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/"
  - type: official
    path: "https://developer.android.com/develop/ui/views/launch/splash-screen"
  - type: official
    path: "https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored"
  - type: official
    path: "https://developer.android.com/guide/topics/resources/runtime-changes"
  - type: official
    path: "https://developer.android.com/reference/android/window/SurfaceSyncGroup"
  - type: material
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S06_multi_window_type.md"
tags: [WMS, WindowManagerService, Surface, Window, StartingWindow, Window动画, 多窗口, SurfaceControl, WindowInsets, Desktop Windowing]
related_chapters: ["2.1", "2.6", "3.1", "8.2", "8.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+读者需求"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-07-02
task6_reviewed_date: 2026-07-02
task6_result: pass-light-edit
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-04
last_task9_at: "2026-05-04T12:41:40+08:00"
last_task9_audit: "2026-07-02"
last_task2b_at: "2026-05-04T07:45:27.214044+08:00"
review_notes: "2026-04-27 task2b: fixed Task9 P95 issues for StartingWindow Shell boundary, modern transition path, and Predictive Back version line."
review_log: "logs/review/2026-04-11-11-review.md"
task9_review_notes: "2026-05-04 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；满足 Task6 pass 与 queue 无 pending 条目，自动晋升 finalized。 2026-06-13 Task9 idle audit: pass-tech-audit。P0 0 / P1 0 / P2 3（仅日志：InputDispatcher WindowInfo 快照表述、源码参考 master 链接、recreateOnConfigChanges 版本归因）。未改正文。 2026-07-02 Task9 idle audit auto-fix: anchored AOSP source references and verification labels to android-17.0.0_r1; returned to Task6 revisiting."
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-01
last_task9_audit_log: "logs/deep-review/2026-07-02-04-audit.md"
last_task9_autofix_at: "2026-07-02"
last_task6_audit: "2026-07-14"
---
# 2.12 Window Manager Service 与窗口管理

## 为什么要了解 WMS

应用冷启动、Activity/Task 过渡、IME、旋转、分屏和桌面窗口尺寸调整都会改变窗口状态。跟踪数据只看应用主线程或 SurfaceFlinger，会漏掉 system_server 与 WM Shell 之间的状态收集、同步和几何事务。

WMS 负责维护 WindowContainer/WindowState 树，并把 Activity/Task 状态转换成窗口边界、可见性、层级、Insets、焦点、输入窗口信息与 `SurfaceControl` 属性。它不绘制应用像素，也不执行最终合成。

一次窗口变化可拆成四段排查：

1. 应用的 `ViewRootImpl` 遍历、relayout IPC 与新缓冲；
2. system_server 的窗口状态、锁、布局/表面放置与过渡收集；
3. WM Shell 的启动表面、过渡处理器与 leash 动画；
4. SurfaceFlinger/HWC 的事务、缓冲锁存、合成与显示。

四段里最先偏离目标时间的对象，才是下一步需要继续追的方向。

## WMS 的定位：窗口状态与 Surface 拓扑

从图形架构看，WMS 位于应用、输入系统和 SurfaceFlinger 之间。它维护 WindowContainer/WindowState 树，决定窗口的层级、可见性、边界、焦点、Insets 和动画状态。SurfaceFlinger 负责把应用提交的内容合成上屏；WMS 的 `InputMonitor` 则把可触摸区域、层级、可聚焦性与输入通道令牌写入 `InputWindowHandle`，通过事务附着到对应图层。SurfaceFlinger 提交图层状态后，再把窗口快照交给 InputDispatcher。

WMS 运行在 system_server 进程中，但性能问题不能简化成“AMS、IMS、WMS 共用一条主线程”。Android 17 的线程边界需要按调用方式判断：

- `WindowManagerService.main()` 在 `DisplayThread` 上构造 WMS，因此 WMS 的 `mH` 绑定该线程；
- `IWindowSession` 等 Binder 调用先在 `Binder:*` 线程执行。同步 `relayout()` 与单向 `relayoutAsync()` 最终都进入 `WindowManagerService.relayoutWindow()`；该方法持有 `mGlobalLock` 时直接调用 `performSurfacePlacement(true)`，不会为了表面放置自动切到 DisplayThread；
- WMS 的 `mAnimationHandler` 绑定 `AnimationThread`。`WindowSurfacePlacer.requestTraversal()` 把常规的延后表面放置投递到这个处理器，`WindowAnimator` 的帧推进也使用该线程；
- `initPolicy()` 在 `UiThread` 执行，并把它登记为 `WindowManagerPolicyThread`。

这些线程会围绕 `mGlobalLock` 和共享窗口状态互相等待。看到 `relayoutWindow`、StartingWindow 切换或窗口动画掉帧时，应先确认耗时在哪条线程执行，再判断函数执行、锁等待和策略/动画侧状态推进各占多少时间。

WMS 与其他主要组件的职责可以这样分：

- **AMS/ATMS**：负责 Activity 和 Task 的生命周期推进；当 Activity 需要显示、隐藏、切换或调整窗口模式时，把窗口侧约束交给 WMS 处理
- **SurfaceFlinger**：负责图层创建、事务消费和最终合成；WMS 管理窗口容器与 `SurfaceControl` 属性，不直接负责像素合成
- **输入系统**：WMS 把可见区域、层级、可聚焦性和输入通道令牌写入图层的输入信息；SurfaceFlinger 从已提交的图层快照生成 `WindowInfosUpdate`，InputDispatcher 再用这份按显示划分的缓存做命中测试

### 多窗口先按共享域分组

“屏幕上有多个窗口”不能直接说明它们竞争哪条线程或哪份显示资源。应按显示、进程和 ViewRoot 分组：

| 拓扑关系 | 共享对象 | 各自独立的对象 | 常见瓶颈 |
|---------|---------|---------------|---------|
| 同进程、同一 UI 线程的多个 ViewRoot | UI Looper；`Choreographer.getInstance()` 返回该线程的 ThreadLocal 实例 | 每个 ViewRoot 的遍历、窗口 Surface 与 BLAST 队列 | 一个窗口的主线程工作挤占其他窗口的遍历时段 |
| 同进程的多个硬件加速窗口 | 进程内 `RenderThread::getInstance()` 单例 | 各窗口的渲染目标、缓冲队列和栅栏 | RenderThread 排队、GPU 上下文与内存带宽竞争 |
| 不同进程、位于同一显示 | SurfaceFlinger 的该显示图层集合、HWC/叠加层、输出带宽和本轮显示 | 应用 UI 线程、进程 RenderThread、窗口缓冲队列 | 单个慢窗口拖延同步组，或合成资源不足 |
| 位于不同显示 | 设备级 GPU/HWC 资源仍可能共享 | 各显示的图层集合、时序和显示栅栏 | 只看默认屏会漏掉外接屏的掉帧 |

因此，多窗口跟踪数据的第一层索引应是显示，第二层是 Window/ViewRoot，第三层才是进程、UI 线程、RenderThread 和内容生产者。每个 ViewRoot 有自己的 Surface/BLAST 内容通道；同进程只表示部分执行资源共享，多个窗口仍各有自己的 BufferQueue。

## Window 与 Surface 的关系

每个应用窗口在 WMS 侧对应一个 `WindowState`。服务端维护窗口元数据与 `SurfaceControl` 关系，应用侧通过 `Surface` 写像素，SurfaceFlinger 内部维护图层快照与输出。几个对象的职责不同：

- **WMS 端**：关联或更新窗口 `SurfaceControl`，维护边界、裁剪、透明度、图层、可见性、Insets 等属性
- **应用端**：通过 `ViewRootImpl` 和 `BLASTBufferQueue` 获取可绘制 `Surface`，决定何时调用 `dequeueBuffer`、绘制和 `queueBuffer`
- **SurfaceFlinger 端**：根据 `SurfaceControl.Transaction` 和缓冲锁存结果完成合成

Android 17 同时保留两种 relayout 表面协议：

- 服务端表面路径通过同步 `relayout()` 返回 `WindowRelayoutResult` 与 `SurfaceControl`；
- 客户端表面路径由 `ViewRootImpl.updateSurfaceControl()` 在客户端创建/复用 `SurfaceControl`，再经 `relayout2()`/`relayoutAsync2()` 传给 WMS。

两条路径最终都要让客户端渲染目标与 BLAST 底层载体对齐。`ViewRootImpl` 根据有效的 `SurfaceControl` 更新渲染器和 `BLASTBufferQueue`，应用随后才通过可绘制 `Surface` 出队、绘制和入队。分析前必须确认 `WindowManager.useClientSurface()` 与相关功能开关，不能把某一分支写成 Android 17 的唯一实现。

### Surface 创建流程

Activity 首次显示时，可按以下稳定边界理解：

1. 应用的 `performTraversals()` 因 `mFirst=true` 进入 relayout；
2. `Session.relayout()` / `relayout2()` 调用 `WindowManagerService.relayoutWindow()`；
3. WMS 更新 `WindowState`、帧、Insets、可见性、同步与表面状态；
4. 服务端表面分支返回服务端 SurfaceControl，客户端表面分支使用客户端传入的控制对象；
5. `ViewRootImpl` 更新帧/Insets、渲染目标和 BLAST；
6. 应用绘制第一帧并把缓冲入队，SurfaceFlinger 才能在后续周期锁存并显示。

WMS 管窗口容器与图层控制关系；应用生成窗口内容；SurfaceFlinger 管图层状态消费和合成。Binder 传递控制对象、帧和同步元数据，不传递已经绘制好的像素。

### SurfaceControl.Transaction 的批量提交

WMS 用 `SurfaceControl.Transaction` 批量提交图层属性。一个事务可以包含位置、缓冲尺寸、透明度、裁剪和重挂载等多个操作，调用 `apply()` 后整体交给 SurfaceFlinger。

```java
// frameworks/base/core/java/android/view/SurfaceControl.java
// 伪代码：Transaction 的典型使用方式
SurfaceControl.Transaction t = new SurfaceControl.Transaction();
t.setPosition(surfaceControl, x, y);
t.setBufferSize(surfaceControl, width, height);
t.setAlpha(surfaceControl, 0.5f);
t.apply(); // 一次性提交给 SurfaceFlinger
```

这段代码展示属性批处理，不表示缓冲内容已完成或面板已显示。`Transaction.apply()` 的常规路径经 JNI 进入原生 `SurfaceComposerClient::apply()`，再通过 Binder 交给 SurfaceFlinger；调用通常不等待本次合成上屏。同步场景要单独检查 `apply(true)`、BLAST 同步、事务提交/完成监听器与显示栅栏。首帧耗时还要拆到图层创建、relayout、缓冲分配和栅栏。

### 三类事务的职责不同

窗口尺寸调整或过渡中经常同时出现三类事务：

| 类型 | 表达的内容 | 典型持有者 |
|------|-----------|-----------|
| `WindowContainerTransaction`（WCT） | Task、Activity、DisplayArea 等 WindowContainer 的边界、窗口模式和层级操作 | WM Shell、ATMS/WMS 组织器路径 |
| `SurfaceControl.Transaction` | 图层的位置、裁剪、透明度、变换、重挂载、可见性和输入信息 | WMS、WM Shell、应用或其他系统组件 |
| BLAST 缓冲事务 | 新内容缓冲及获取栅栏，与目标图层的内容更新配套 | 应用生产者、BLASTBufferQueue、SurfaceFlinger |

WCT 是“窗口容器要变成什么状态”的管理请求，处理后可能引发一个或多个 SurfaceControl 事务；它不属于 SurfaceFlinger 的几何事务。几何与内容分属两路输入：尺寸调整时可以短暂出现新几何配旧缓冲，或新缓冲已到但同步组尚未放行几何。遇到拉伸、黑边或一帧错位，需要分别核对容器状态、图层几何、缓冲尺寸和栅栏，笼统搜索“transaction”无法确定问题位置。

## StartingWindow 与启动性能

冷启动期间，进程创建、Runtime/Application/Activity 初始化和首帧绘制尚未完成。StartingWindow 在这段空档提供可见内容，避免用户只看到桌面、空白或旧画面。

### StartingWindow 的工作原理

Android 12 之后，StartingWindow 的决策与实际创建分在两侧。ATMS/WMS 负责判断本次 Activity 启动是否需要启动表面，`StartingSurfaceController` 根据 SplashScreen 或 TaskSnapshot 路径生成启动数据；WM Shell 的启动表面组件负责创建 SplashScreen/TaskSnapshot 窗口并挂到对应 Task 上。常用源码锚点包括：

- `frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java`：服务端发起启动表面请求
- `frameworks/base/services/core/java/com/android/server/wm/SplashScreenStartingData.java`：保存 SplashScreen 启动数据
- `frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java`：Shell 侧接收 `TaskOrganizer.addStartingWindow` 回调
- `StartingSurfaceDrawer.java`/`SplashscreenWindowCreator.java`：Shell 侧创建并绘制 SplashScreen 窗口

冷启动路径可以按这组边界读：

1. ATMS 推进 Activity 启动，WMS 在 `ActivityRecord`/Task 可见性变化中判断是否需要启动表面。
2. `StartingSurfaceController` 生成请求，SplashScreen 路径使用 `SplashScreenStartingData`，历史任务恢复路径可能使用 TaskSnapshot 启动数据。
3. Android 12+ 的 Shell 启动表面组件收到 `addStartingWindow` 回调后，在 Shell/SystemUI 侧创建 SplashScreen 或 TaskSnapshot 窗口。
4. 应用进程启动并绘制主窗口第一帧。
5. 应用通过 `finishDrawing`/`reportDrawFinished` 让服务端知道主窗口已完成首帧，随后走 `removeStartingWindow` 路径通知 Shell 移除启动表面。

Perfetto 里要把三段分开看：system_server 侧是启动数据、Activity/Task 状态和移除请求；Shell/SystemUI 侧负责启动表面的创建与绘制；应用侧的 `reportDrawFinished` 标记主窗口首帧完成。把启动表面的绘制职责放在 system_server，会混淆服务端、Shell 和应用进程边界。

### Android 12 SplashScreen API

在 Android 12 之前，StartingWindow 的外观主要由 `windowBackground` 决定，OEM 定制差异较大。Android 12 引入 SplashScreen API（`android.window.SplashScreen`），把启动页主题、图标、背景色、退出动画等配置收敛到统一接口：

- 开发者通过 `Theme.SplashScreen` 配置图标、背景色、动画等元素。
- 退出动画通过 `setOnExitAnimationListener` 接入，移除时机仍要和主窗口首帧完成信号配合。
- `androidx.core:core-splashscreen` 向后支持 Android 5.0+，但 Android 12+ 的系统启动表面创建仍落在 Shell 启动表面路径。

这套 API 的性能价值在于减少应用自建 SplashActivity。自建启动页会多一次 Activity 启动、窗口切换和可能的 relayout；系统 SplashScreen 则复用启动表面生命周期，不增加应用侧 Activity 数量。

### StartingWindow 的时机陷阱

StartingWindow 的移除时机会影响启动体感：

- **过早移除**：应用主窗口第一帧还没准备好时移除启动表面，用户可能看到短暂闪白或闪黑。
- **过晚移除**：主窗口已经完成首帧，启动表面仍停留在前台，用户会把这段时间感知为启动变慢。

主窗口首帧完成后，服务端才具备移除 StartingWindow 的内容条件。服务端通过 `finishDrawing`/`reportDrawFinished` 收到信号，再走 `removeStartingWindow` 路径让 Shell 移除启动表面。分析启动跟踪数据时，`reportDrawFinished` 只说明应用首帧完成；视觉切换还要看 Shell 移除、SurfaceFlinger 消费事务和后续显示。

## relayoutWindow：重新协商窗口契约

`relayoutWindow()` 重新协商窗口属性、帧、Insets、表面与同步序列。它可能嵌在应用遍历的同步 Binder 调用里，也可能由单向 `relayoutAsync()` 送到 system_server。两种调用都需要 WMS 处理，差别在于客户端是否等待返回结果。

### 什么触发 relayoutWindow

`ViewRootImpl.performTraversals()` 不会每帧跨进程调用 WMS。Android 17 `ViewRootImpl.java` 的直接条件有五类：

- **`mFirst`**：窗口首次显示，必须向 WMS 申请初始 `SurfaceControl`、帧和 Insets
- **`windowShouldResize`**：`requestLayout()` 后测量结果改变了窗口尺寸，常见于旋转、多窗口尺寸调整、Dialog `WRAP_CONTENT` 长大
- **`viewVisibilityChanged`**：窗口从隐藏到显示、从显示到隐藏，或 `mNewSurfaceNeeded=true`
- **`params != null`**：`setLayoutParams()`、system UI visibility、keepScreenOn 等窗口属性变化
- **`mForceNextWindowRelayout`**：WMS 通过 `resized()`/配置变化回调强制下一次遍历重新 relayout

Insets 变化会先走 `mApplyInsetsRequested`、`dispatchApplyInsets()`，并可能引起测量/布局、窗口属性变化或强制 relayout，但 `insetsChanged` 不是 Android 17 这段 `if` 的独立布尔条件。`invalidate()` 的纯绘制不会因此进入 WMS；`requestLayout()` 也只有在上述条件成立时才跨进程。

Android 14+ 增加了 `relayoutAsync()`。Android 17 的 `canRelayoutAsync()` 会检查启动窗口、待处理同步/序列、AM/WMS `WindowConfiguration` 差异等条件；随后客户端用本地 `InsetsState` 和 `WindowConfiguration` 计算帧。若位置和尺寸同时变化、需要取得新的同步序列，就回到同步 relayout。启用流式尺寸调整/客户端表面相关开关后，分支还会不同，分析必须以目标构建的功能开关为准。

服务端实现很薄：`Session.relayoutAsync()`/`relayoutAsync2()` 复用 `relayout(...)`，只把 `outRelayoutResult` 设为 `null`，随后仍进入 `WindowManagerService.relayoutWindow()`。跟踪数据上的区别是应用 UI 线程不等待帧、Insets、SurfaceControl 和同步序列返回；system_server 仍要处理属性变化、`mGlobalLock` 与后续表面放置。分析时要把当前遍历和之后的 `IWindow.resized()`/Insets 回调放在同一段时间线里。

### relayoutWindow 内部流程

WMS 侧的执行过程不能简化成“`relayoutWindow()` 直接调 `performLayout()`”。现代实现更接近下面这条路径：

1. 应用侧 `performTraversals()` 判断本轮是否需要同步 relayout，随后通过 Binder 进入 `WindowManagerService.relayoutWindow()`
2. WMS 在 `mGlobalLock` 保护下更新 `WindowState`、可见性、布局参数、Insets 请求和表面生命周期状态
3. `relayoutWindow()` 会在当前 Binder 线程内直接调用 `mWindowPlacerLocked.performSurfacePlacement(true)`；同步与单向异步 relayout 都经过这里，其他状态变化可由 `requestTraversal()` 把常规表面放置投到 AnimationThread
4. 同步路径返回 `ClientWindowFrames`、`MergedConfiguration`、`InsetsState`、`InsetsSourceControl` 与同步序列；SurfaceControl 由服务端表面路径返回或由客户端表面路径传入
5. 应用侧收到同步结果后继续 relayout 后的测量/布局/绘制；异步路径则等待后续尺寸/Insets/配置回调更新本地状态

同样是遍历，有的帧只在应用主线程执行测量/布局/绘制；有的帧会发起 system_server Binder 线程上的 relayout 和强制表面放置，其中同步调用会嵌套在应用 UI 线程等待区间内；另一些窗口状态更新则由 DisplayThread 的 WMS 处理器或 AnimationThread 的常规表面放置继续处理。判断线程要看调用栈和可运行任务来源，不能从函数名推断。

### 应用侧遍历与 WMS relayout 的对应关系

| 场景 | 是否跨进程进入 WMS | Perfetto 观察重点 |
|------|------------------|------------------|
| `invalidate()` 触发的纯重绘 | 否 | 应用主线程 `performDraw` 与 RenderThread |
| `requestLayout()` 但窗口尺寸未变 | 通常否 | 应用主线程测量/布局/绘制 |
| 首帧、窗口尺寸调整、需要服务端新帧/Insets 状态 | 同步或异步 | 应用 relayout 调用、system_server Binder 执行；两种服务端路径都可能直接强制表面放置 |
| 只改不会影响帧同步的窗口属性，且命中 `relayoutAsync()` 条件 | 异步 | 应用当前遍历不等 `RelayoutResult`；后续 `W.resized()`/Insets 回调再刷新本地状态 |

### scheduleTraversals() 与 performTraversals() 的职责边界

`ViewRootImpl.scheduleTraversals()` 是应用侧调度入口，不跨进程。它向 Choreographer 投递 `TraversalRunnable`，在下一次 VSync 时触发 `doTraversal()` → `performTraversals()`。WMS 跨进程调用只发生在 `performTraversals()` 内部条件满足时。

以下代码从 Android 17 `ViewRootImpl.java` 抽取等价逻辑，只保留调度与 relayout 条件：

```java
// 调度入口 — 应用进程内，不跨进程
void scheduleTraversals() {
    if (!mTraversalScheduled) {
        mTraversalScheduled = true;
        mChoreographer.postCallback(Choreographer.CALLBACK_TRAVERSAL,
                mTraversalRunnable, null);
    }
}

// performTraversals 内部的条件判断 — 跨进程阈值
final boolean relayoutRequested = mFirst || windowShouldResize
        || viewVisibilityChanged || params != null
        || mForceNextWindowRelayout;

if (relayoutRequested) {
    // 这里才跨进程 → WMS
    relayoutWindow(params, viewVisibility, insetsPending);
}
```

这段代码只抽取调度与 relayout 分支。`requestLayout()` → `scheduleTraversals()` → `performTraversals()` 先在应用进程内执行；命中前述五类条件后，才从 `performTraversals()` 调用 WMS。

**Perfetto 区分表**：

| 切片名称 | 进程 | 线程 | 含义 |
|-----------|------|------|------|
| `ViewRootImpl#doTraversal` | 应用 | UI 线程 | 应用侧测量/布局/绘制调度 |
| `ViewRootImpl#performTraversals` | 应用 | UI 线程 | 完整测量、布局和绘制，内部可能嵌套 `relayoutWindow` |
| `relayoutWindow` | system_server | `Binder:*` 入口 | WMS 侧窗口属性更新；同步/单向异步入口都可在当前线程内执行强制表面放置 |

**时序判读**：

- 应用发起：`performTraversals` 内嵌同步或异步 relayout，常见于首次显示、尺寸或 LayoutParams 变化；
- system_server 发起状态变化：WMS 通过 `IWindow.resized()`、Insets/配置等回调通知客户端，客户端再调度遍历；下一次遍历是否回调 relayout，仍由上述五类条件决定。

### 在 Perfetto 中的表现

查看 WMS 相关跟踪数据时，应确认采集配置是否打开 `wm`、`view`、`am`、`input`、`gfx`、`surfaceflinger` 这些类别。没有这些类别时，system_server 侧只会留下零散 Binder 切片，很难还原 relayout 路径。

切片名也不能写死。`wm.relayout_window`、`SurfaceControl.Transaction.apply`、`animator`、`reportDrawFinished` 都可能因 Android 版本、atrace 类别、Perfetto 配置和 OEM 定制而变化。应先枚举实际跟踪数据中出现的切片名，再写针对性 SQL。

```sql
SELECT DISTINCT s.name
FROM slice s
JOIN track t ON s.track_id = t.id
JOIN thread_track tt ON tt.id = t.id
JOIN thread th ON th.utid = tt.utid
JOIN process p ON p.upid = th.upid
WHERE p.name = 'system_server'
  AND (
    s.name GLOB '*relayout*'
    OR s.name GLOB '*window*'
    OR s.name GLOB '*surface*'
    OR s.name GLOB '*anim*'
  )
ORDER BY s.name;
```

枚举完实际名字后，再围绕三个问题继续分析：

- 当前帧有没有同步 relayout IPC；
- system_server 里的耗时来自 Binder 执行、`mGlobalLock` 等待，还是动画/策略相关线程；
- 返回应用之后，额外成本落在重新测量、Insets 分发，还是首帧绘制。

## Window 动画与过渡性能

切换应用、回到桌面、打开最近任务和预测返回都属于窗口过渡。现代 Android 已由多个组件共同驱动动画。旧兼容路径仍可能出现 `AppTransition`，Android 17 的主线入口是 `TransitionController`/`Transition` 收集 WindowContainer 变化，再由 WM Shell 过渡、远程过渡或服务端表面动画执行。

### 动画路径如何分工

Activity 切换、回到桌面、打开最近任务和预测返回几乎都需要 ATMS/WMS、WM Shell、SurfaceFlinger 三层协作：

1. ATMS/WMS 更新 `ActivityRecord`、Task、DisplayContent 等 WindowContainer 状态，并由 `TransitionController` 收集打开、关闭和变化操作。
2. `Transition` 把参与过渡的窗口、leash、起止边界和可见性变化整理成一次过渡。
3. 如果本轮过渡交给 Shell，WM Shell 过渡处理器或远程过渡会根据 leash 构建动画；最近任务、跨 Task、桌面模式和预测返回常走这条路径。
4. 服务端动画仍会用到 `SurfaceAnimator`/`SurfaceAnimationRunner` 等组件，把每帧变换、透明度和裁剪写入 `SurfaceControl.Transaction`。
5. SurfaceFlinger 在后续 `commit`/`composite` 中消费这些事务，完成合成与显示。

过渡包含两类成本：开始前的参与者收集、绘制同步与就绪；播放期间的 Shell/远程处理器、leash 事务和 SurfaceFlinger 合成。120 Hz 屏幕的周期约 8.33 ms，播放阶段任何一帧迟交事务或迟完成合成，都会错过目标显示时间。

这里还要区分两个名字相近的同步机制：

- system_server 内部的 `BLASTSyncEngine` 收集参与变化的 WindowContainer，等待需要重绘的窗口通过 `finishDrawing` 交付内容，再把各子树的待处理事务合并给 `TransactionReadyListener`。窗口过渡、旋转和同步尺寸调整常从这里追；
- API 34 引入的公开 `SurfaceSyncGroup` 面向 `AttachedSurfaceControl`、`SurfaceView`、`SurfaceControlViewHost` 等表面，可跨组件甚至跨进程等待多个表面就绪后一起应用事务。

两者都在解决“多个表面何时一起可见”，但调用方和对象层级不同。跟踪数据中出现同步 ID 时，应确认它属于 WMS 的 WindowContainer 同步还是应用/组件侧的 `SurfaceSyncGroup`，再查超时和缺帧参与者。

源码阅读可从这些入口进入：

- `frameworks/base/services/core/java/com/android/server/wm/TransitionController.java`：收集和调度 WindowContainer 过渡
- `frameworks/base/services/core/java/com/android/server/wm/Transition.java`：记录参与过渡的窗口变化
- `frameworks/base/services/core/java/com/android/server/wm/SurfaceAnimator.java`：对表面 leash 执行动画
- `frameworks/base/services/core/java/com/android/server/wm/SurfaceAnimationRunner.java`：驱动表面动画的帧推进
- `frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/transition/`：Shell 过渡处理器与远程过渡接入

### Activity 切换动画

Activity open / close 动画可以按版本分层理解：

| 版本范围 | 主线口径 | 排查重点 |
|----------|----------|----------|
| Android 12—14 | 旧版 `AppTransition` 仍覆盖一部分路径，`TransitionController` 和 Shell 过渡逐步接管 Task/Activity 级过渡 | 同时看 `wm`、`transition`、`android.anim*`、Shell 进程和 SurfaceFlinger 事务 |
| Android 15—17 | `TransitionController`/Shell 过渡是 Activity、最近任务、预测返回、桌面模式等场景的主要分析入口 | 先定位过渡 ID，再看 Shell 处理器、远程过渡、leash 事务与 SF `commit`/`composite` |

一次 Activity 切换里，旧 Activity 和新 Activity 的窗口往往会被包到 leash 表面下。动画过程更新 leash 的变换、透明度、裁剪和图层，应用不需要每帧重绘 Activity 内容。应用侧首帧准备慢、Shell 动画线程慢、system_server 过渡状态收集慢或 SurfaceFlinger 合成慢，都会表现成切换掉帧，但根因落点不同。

Perfetto 里不能只看 `android.anim`。如果掉帧发生在 Activity 打开/关闭期间，应按这个顺序拆：

1. 应用主线程和 RenderThread 是否按时提交首帧。
2. system_server 里的过渡收集、就绪和结束阶段是否被锁等待或 Binder 调用拖长。
3. Shell/SystemUI 进程里的过渡处理器是否每帧稳定产出事务。
4. SurfaceFlinger 的 `commit`、`composite` 和显示阶段是否及时消化这些事务。

### Predictive Back 动画

Predictive Back 的版本线要拆开读：

- **Android 13**：引入 `OnBackInvokedCallback` 和预测返回早期能力，系统动画可通过开发者选项测试。
- **Android 14**：完善跨 Activity、跨 Task 和自定义过渡接入，开发者仍经常通过开发者选项验证预测返回动画。
- **Android 15**：开发者选项不再是系统动画显示前提；对已经选择启用的应用或 Activity，返回桌面、跨 Task、跨 Activity 等系统动画会按系统策略显示。未启用的应用仍按传统返回行为处理。
- **Android 16**：目标版本 36 的应用默认启用预测返回，`android:enableOnBackInvokedCallback` 默认值改为 `true`；旧 `OnBackPressed`/`KEYCODE_BACK` 调用在该行为下被忽略，同时新增 `finishAndRemoveTaskCallback`、`moveTaskToBackCallback` 等 API。
- **Android 17**：沿用该过渡/Shell 主路径；应用仍需按目标 SDK、清单与 AndroidX 回调的实际配置判断，不能从系统版本单独推断是否参与预测动画。

它的性能路径跨输入系统、ATMS/WMS、Shell 过渡和 SurfaceFlinger。手势开始后，输入侧持续上报返回进度；WMS/Shell 根据返回目标更新当前窗口和目标窗口的 leash；手势完成或取消时，过渡进入结束或取消状态。分析卡顿时要同时看输入事件节奏、Shell 过渡处理器、system_server 过渡状态，以及 SurfaceFlinger 是否在同一时间段出现事务堆积。

## 多窗口、折叠屏与桌面模式

分屏、自由窗口、画中画、Activity Embedding 和多显示会改变 WindowContainer 树、可见图层集合与窗口边界。性能压力来自参与本轮变化的对象、同步范围和更新频率，不能只按屏幕上有几个窗口估算。

### 多窗口模式下的 WMS 工作量

多窗口常增加下面几类工作：

- 多个可见 Task/Window 的边界、Insets、焦点与输入窗口快照；
- WindowContainerTransaction、过渡参与者与 leash；
- 尺寸/配置回调和应用的新尺寸缓冲；
- 标题栏、IME、暗化层、壁纸、PiP 与叠加层引起的合成策略变化；
- 同进程多个 ViewRoot 对 UI Looper 与 RenderThread 的竞争。

静止且没有状态变化的可见窗口不一定持续触发 relayout。拖拽分隔线、调整自由窗口尺寸、跨显示移动、IME 动画和过渡更容易形成高频更新。应记录每轮参与的 WindowContainer、同步 ID、事务和缓冲，不用总窗口数替代证据。

排查时按下面的对象顺序取证：

1. **显示**：确认物理/逻辑显示、刷新周期、图层集合和本轮显示栅栏；
2. **窗口**：找发生边界、Insets、可见性、焦点或图层变化的 WindowState/ViewRoot；
3. **执行资源**：确认它属于哪个进程、UI 线程和 RenderThread，是否与其他窗口共享；
4. **内容通道**：检查该窗口自己的 BLAST 队列、缓冲尺寸、获取栅栏和锁存；
5. **合成结果**：回到该显示的 SurfaceFlinger 合成与 HWC 显示阶段。

同一显示的不同进程拥有独立的应用执行链，但最终仍在该显示的同一轮合成和显示阶段汇合。不同显示要分别核对显示栅栏；默认屏正常不能证明外接屏也按时显示。

### 折叠屏与大屏配置变更

折叠、展开或跨显示移动会改变显示区域、窗口边界、Insets 与配置。应用是否重建 Activity，取决于变化类型、目标 SDK、兼容性变更、`configChanges` 与 Android 17 的新默认行为。

目标版本 37 的应用运行在 `sw >= 600dp` 的大屏时，固定方向、`resizeableActivity` 和最小/最大宽高比限制会被忽略；游戏、小于 600 dp 的屏幕以及用户显式选择应用默认比例的情况属于例外。窗口因此更可能经历尺寸调整、旋转和配置回调，但 BLAST/SF 主线没有换代。

Android 17 还减少了部分配置变化的 Activity 重建：`CONFIG_KEYBOARD`、`CONFIG_KEYBOARD_HIDDEN`、`CONFIG_NAVIGATION`、`CONFIG_TOUCHSCREEN`、`CONFIG_COLOR_MODE`，以及进入/离开 `UI_MODE_TYPE_DESK` 的 `CONFIG_UI_MODE` 默认改为 `onConfigurationChanged()`。

固定标签的 `attrs_manifest.xml` 为 `android:recreateOnConfigChanges` 定义了 `mcc`、`mnc`、`touchscreen`、`keyboard`、`keyboardHidden`、`navigation`、`colorMode`，没有 `uiMode`。因此：

- 对已列出的标志，应用依赖重建刷新资源时可用 `recreateOnConfigChanges` 显式启用；
- 不要把 `uiMode` 写进该属性；进入/离开桌面模式应在 `onConfigurationChanged()` 更新依赖配置的资源和组件；
- `recreateOnConfigChanges` 与声明应用自行处理变化的 `android:configChanges` 方向相反，同一标志同时出现在两者时不会重建。

### Android 16 QPR3 外接显示桌面模式

外接显示桌面窗口功能在 Android 16 QPR3 对受支持设备正式可用。它仍受设备能力、OEM 配置、外接显示器与用户入口约束，不能从 `Build.VERSION` 推断某台设备已经启用。

对 WMS 来说，自由窗口、标题栏 Insets、多实例和跨显示移动会增加 WindowContainer、WCT、过渡与尺寸调整工作。应用还要处理不同显示的密度、刷新率、颜色模式、输入与资源。

这类场景里的 Binder 线程只是入口。还要分别检查 DisplayThread 上的 WMS 处理器工作、AnimationThread 上的常规表面放置/动画、WM Shell 过渡、应用遍历/RenderThread，以及每个显示的 SF/HWC/显示阶段。

## 在 Perfetto 中的综合表现

在 Perfetto 中分析 WMS 时，应先按线程和阶段分组，再识别切片名。

### 先看哪些线程

| 线程 / 进程 | 常见职责 | 观察意义 |
|-----------|---------|---------|
| system_server `Binder:*` | `relayoutWindow`、可见性、窗口事务入口；relayout 可直接执行强制表面放置 | 看 IPC、`mGlobalLock` 等待和 `performSurfacePlacement(true)` 调用栈 |
| system_server DisplayThread | WMS `mH` 消息与显示服务工作 | 看显示变更和 WMS 处理器队列，不要默认把所有表面放置归到这里 |
| system_server `android.anim*`/AnimationThread | `requestTraversal()` 投递的常规表面放置、WindowAnimator 和表面动画 | 看表面放置/动画任务是否过期或被锁阻塞 |
| system_server UiThread/WindowManagerPolicyThread | 策略初始化与策略回调 | 只在调用栈涉及策略时纳入关键路径 |
| 应用主线程 | `performTraversals`、尺寸回调、首帧绘制 | 看遍历是否因 relayout 变重 |
| RenderThread | `syncAndDrawFrame` | 区分 WMS 问题和渲染问题 |
| SurfaceFlinger | 事务应用、锁存、合成 | 看缓冲/事务是否在合成侧堆积 |

### 先枚举切片，再做专项查询

`wm.pause_timeout`、`wm.relayout_window`、`SurfaceControl.Transaction.apply` 并非所有版本都有。查询顺序如下：

1. 枚举 system_server、应用、SurfaceFlinger 中实际出现的 `relayout`、`window`、`surface`、`anim`、`draw` 相关切片
2. 再按线程聚类，确认这一帧落在哪个进程和哪条线程
3. 只对当前跟踪数据里存在的切片名写 SQL

### 典型分析场景

**场景 1：冷启动**

1. 在应用主线程确认首帧 `performTraversals` 是否命中 `mFirst`
2. 在 system_server Binder 线程找首次 relayout 及其内嵌的强制表面放置；另查 AnimationThread 是否还有延后表面放置
3. 回看应用的首帧绘制完成点，再确认 StartingWindow 退出时机

**场景 2：多窗口切换掉帧**

1. 从掉帧帧号回看应用主线程和 RenderThread
2. 查看 system_server 的 Binder 线程、AnimationThread 和 DisplayThread，按调用栈区分强制表面放置、常规表面放置与处理器工作
3. 如果同时出现窗口尺寸或 Insets 变化，再把 relayout 和动画拆开计时

**场景 3：旋转或桌面模式尺寸调整卡顿**

1. 确认窗口边界变化是否触发同步 relayout
2. 查看 `performSurfacePlacement(true)` 之后的额外成本落在帧/Insets 返回还是应用侧重新测量
3. 结合 SurfaceFlinger 的事务/锁存情况，判断缓冲尺寸调整是否放大合成侧成本

## 与其他机制的关系

WMS 的性能表现同时受多个上下游影响：

- **§2.1 渲染架构全景**：WMS 连接应用绘制与 SurfaceFlinger 合成
- **§2.6 SurfaceFlinger 与合成**：WMS 通过 SurfaceControl.Transaction 与 SurfaceFlinger 交互，事务执行时机影响合成效率
- **§2.13 图形缓冲区管理**：Surface 的创建涉及 BufferQueue 分配，BufferQueue 的生产者/消费者模型决定应用与 SurfaceFlinger 的协作方式
- **§3.1 输入事件分发**：WMS 维护的窗口 Z 序和焦点信息是 InputDispatcher 进行命中测试的基础
- **§8.2 启动速度分析**：StartingWindow 的创建和移除时机直接影响启动体感
- **§8.4 其他响应速度场景**：旋转屏幕、多窗口切换等场景中 WMS 的 relayout 是性能关键路径

## 版本演进

下表只保留对当前 WMS 调试口径影响最大的版本节点。

| 版本 | 变化 | 性能影响 | 参考锚点 |
|------|------|---------|---------|
| Android 12 (API 31) | SplashScreen API 统一 StartingWindow | 启动反馈路径更标准，但 Android 12+ 的 SplashScreen/TaskSnapshot 启动窗口创建与绘制主要落在 WM Shell 启动表面路径 | `developer.android.com/develop/ui/views/launch/splash-screen` |
| Android 13 (API 33) | `OnBackInvokedCallback` 与预测返回早期能力 | 应用可接入新的返回回调；系统预测返回动画多处仍需要开发者选项辅助测试 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture` |
| Android 14 (API 34) | 预测返回的跨 Activity/自定义过渡能力继续完善 | 返回手势进入实时预览，输入系统、WMS 过渡与 Shell 过渡需要放在同一段时间轴内分析 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture` |
| Android 15 (API 35) | 预测返回系统动画不再依赖开发者选项；边到边强制范围扩大 | 已启用的应用/Activity 会显示返回桌面、跨 Task、跨 Activity 等系统动画；Insets 分发也更常见 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture`/`developer.android.com/about/versions/15/behavior-changes-15` |
| Android 16 (API 36) | 目标版本 36 默认启用预测返回；大屏自适应行为；QPR3 外接显示桌面模式在受支持设备正式可用 | 返回过渡、标题栏、外接显示器和自由窗口会增加过渡/尺寸调整路径 | `developer.android.com/about/versions/16/summary`/Android Developers 外接显示正式版说明 |
| Android 17 (API 37) | 目标版本 37 的大屏移除方向/可调整窗口退出选项；减少键盘、导航、触摸、颜色和桌面模式等配置变化的 Activity 重建 | 尺寸/配置变化更频繁，但部分外设/桌面模式变化转为 `onConfigurationChanged()`；需要重建时使用 `recreateOnConfigChanges` | `developer.android.com/about/versions/17/changes/ff-restrictions-ignored`/`developer.android.com/guide/topics/resources/runtime-changes` |

## 常见问题与误区

### 误区 1："WMS 在主线程上运行，所以很慢"

WMS 横跨 system_server 内的 Binder 线程、DisplayThread、UiThread/WindowManagerPolicyThread 和 AnimationThread。常见耗时来自 `mGlobalLock` 竞争、共享窗口状态更新、表面放置或动画推进。Perfetto 里要按调用方式归属：`relayoutWindow()` 直接执行的强制表面放置在 Binder 线程，`requestTraversal()` 调度的常规表面放置在 AnimationThread，WMS `mH` 消息在 DisplayThread，策略工作在 UiThread。函数属于 WMS，不表示它固定运行在某条“WMS 线程”。

### 误区 2："Window 数量越多越卡"

窗口数量会增加状态和内存，但不能单独预测帧耗时。需要关注本轮参与布局、过渡、同步、输入快照和事务的可见窗口，以及它们更新的频率。隐藏窗口仍有服务端状态，通常不会像正在调整尺寸的窗口那样持续进入显示关键路径。

### 误区 3："StartingWindow 是应用画的"

StartingWindow 独立于应用主窗口第一帧。ATMS/WMS 判断是否需要启动表面并发出生命周期请求；Android 12+ 的 SplashScreen/TaskSnapshot 启动窗口多由 WM Shell 启动表面组件创建和绘制。应用进程完成主窗口首帧之前，Shell 侧启动表面已经挂到 Task 上。

### 误区 4："relayoutWindow 慢一定是 WMS 的问题"

`relayoutWindow` 慢可能来自 WMS 自身计算，也可能来自窗口树更新后的连带成本。常见放大源包括：等待 `mGlobalLock`、`performSurfacePlacement(true)` 处理过多可见窗口、Insets/配置返回触发应用侧重新测量、表面尺寸调整让 SurfaceFlinger 的事务/锁存变重。排查时至少同时看应用主线程、system_server 多条线程和 SurfaceFlinger。

### 误区 5："预测返回动画延迟是输入系统的问题"

预测返回动画涉及输入系统、应用回调、ATMS/WMS、WM Shell 与 SurfaceFlinger。对系统返回桌面、跨 Task、跨 Activity 动画，不能只查 WMS `WindowAnimator`：`TransitionController`/`Transition` 收集窗口状态，Shell 的 `BackAnimationController` 或过渡处理器生成 leash 事务。排查应分四段：输入进度、应用/返回回调、ATMS/WMS 过渡、Shell 事务与 SurfaceFlinger 显示。

## 扩展

### 🔸 WindowInsets 与布局性能

WMS/InsetsStateController 维护状态栏、导航栏、IME、标题栏、屏幕缺口等来源，客户端 `InsetsController` 接收 relayout 结果或独立的 Insets 回调，再由 `ViewRootImpl` 分发给 View 层级。Insets 变化不必每次都通过同步 relayout 返回。

布局成本取决于应用怎样消费 Insets：

- 监听器修改内边距/外边距并调用 `requestLayout()`，会触发测量/布局；
- IME/系统栏动画若每帧改布局，成本会持续到动画结束；
- View 与 Compose 同时应用相同 Insets，可能出现重复内边距；
- PlatformView、SurfaceView、相机预览还需要同步内容裁剪/变换。

应先确定哪个容器拥有 Insets，再选择 View 监听器或 Compose 修饰符。只有该边界已完整处理且子树不再需要同一 Insets 时才消费；无条件返回 `WindowInsets.CONSUMED` 会让子 View 丢失所需信息。边到边场景还应把布局成本与 SurfaceControl/IME 动画分开测量。

### 🔸 WMS 与输入系统的协作

Android 17 `InputMonitor.UpdateInputWindows` 使用 WMS 的 `mAnimationHandler`，在 `mGlobalLock` 下按从上到下的窗口顺序填充 `InputWindowHandle`，再通过 `SurfaceControl.Transaction.setInputWindowInfo()` 把变化绑定到对应 SurfaceControl。非立即路径会把这批输入事务合并进 `DisplayContent` 的待处理事务，并调度下一轮动画/表面放置。

SurfaceFlinger 消费事务后，从已经提交的图层快照构造 `WindowInfo` 和 `DisplayInfo`。`updateInputFlinger()` 把 `WindowInfosUpdate` 交给窗口信息监听器；InputDispatcher 的 `onWindowInfosChanged()` 随即按显示拆分窗口列表，调用 `setInputWindowsLocked()` 替换缓存并唤醒轮询循环。`onWindowInfosReported()` 一类回调表示监听器已经处理完这次更新，用于完成通知；InputDispatcher 更新窗口缓存时不需要等待该回调。

InputDispatcher 处理触摸时使用当前显示的窗口快照做命中测试，再通过已注册的 InputChannel 投递。它不会为每个触摸事件同步调用 WMS 拉取窗口列表。

窗口移动、过渡、焦点或可触摸区域变化时，需要对齐：

1. WMS 何时标记并发布新的输入窗口信息；
2. SurfaceFlinger 在哪次事务提交后生成新的图层/窗口快照；
3. InputDispatcher 何时收到 `WindowInfosUpdate`、替换窗口缓存并处理焦点请求；
4. 窗口信息监听器何时报告完成；
5. 应用输入通道何时收到事件。

“点击没有响应”可能来自旧快照、目标窗口不可触摸、焦点请求未完成、应用通道积压或应用主线程迟到。焦点切换本身不表示事件必然丢失。§3.1 会继续展开 InputDispatcher 的队列与超时证据。

## 参考资料

- [AOSP WindowManagerService 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java) ，`relayoutWindow()` 和窗口状态管理入口
- [AOSP WindowSurfacePlacer 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowSurfacePlacer.java) ，`performSurfacePlacement(true)` 的主执行点
- [AOSP StartingSurfaceController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java) ，服务端启动表面请求入口
- [AOSP WM Shell StartingWindowController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java) ，Shell 侧 `addStartingWindow` / `removeStartingWindow` 入口
- [AOSP TransitionController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/TransitionController.java) ，WindowContainer transition 收集与调度入口
- [AOSP ViewRootImpl 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/ViewRootImpl.java) ，应用侧遍历、`relayout()` 判定和 `updateBlastSurfaceIfNeeded()`
- [AOSP IWindowSession / Session 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/IWindowSession.aidl) ，同步 `relayout`、oneway `relayoutAsync` 与 `relayout2` 协议
- [AOSP InputMonitor 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/InputMonitor.java) ，`InputWindowHandle` 填充与事务发布
- [AOSP SurfaceFlinger 输入窗口发布](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp) ，`updateInputFlinger()` 从图层快照生成 `WindowInfosUpdate`
- [AOSP InputDispatcher 源码](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp) ，`onWindowInfosChanged()` 更新按显示划分的窗口缓存
- [AOSP BLASTSyncEngine 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java)/[SurfaceSyncGroup 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/SurfaceSyncGroup.java) ，服务端 WindowContainer 同步与公开表面同步 API 的边界
- [Android API 参考，SurfaceSyncGroup](https://developer.android.com/reference/android/window/SurfaceSyncGroup) ，API 34 起公开的跨表面同步接口
- [AOSP SurfaceControl JNI 路径](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/jni/android_view_SurfaceControl.cpp) ，原生 `createSurfaceChecked(...)` 入口
- [AOSP BLASTBufferQueue 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/graphics/java/android/graphics/BLASTBufferQueue.java) ，客户端表面实体化
- [内核 dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)/[sync_file](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c) ，窗口缓冲与显示同步边界
- [Android 官方文档，SplashScreen API](https://developer.android.com/develop/ui/views/launch/splash-screen) ，StartingWindow 与统一启动体验
- [Android 官方文档，Predictive Back](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture) ，返回手势动画与过渡回调
- [Android 16 QPR3 外接显示正式版说明](https://developer.android.com/blog/posts/android-devices-extend-seamlessly-to-connected-displays) ，受支持设备上的桌面窗口功能
- [Android 官方文档，Android 16 Behavior Changes](https://developer.android.com/about/versions/16/behavior-changes-all) ，大屏自适应与 orientation / resizable 行为变化
- [Android 17 大屏方向与可调整窗口变化](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored) ，target 37 的适用范围与例外
- [Android 17 configuration changes](https://developer.android.com/guide/topics/resources/runtime-changes#android-17) ，减少 Activity recreation 与 `recreateOnConfigChanges`
- [Android 官方文档，WindowInsets](https://developer.android.com/develop/ui/views/layout/window-insets) ，Insets 分发与适配实践
