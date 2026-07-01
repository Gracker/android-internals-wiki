---
title: "Window Manager Service 与窗口管理"
chapter: "2.12"
section: "2.12"
status: finalized
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-04-26"
last_verified_against: "AOSP android-17.0.0_r1 ViewRootImpl/IWindowSession/Session + BLASTBufferQueue + Android 16/17 official docs + external review"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowState.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowSurfacePlacer.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/SplashScreenStartingData.java"
  - type: aosp
    path: "frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java"
  - type: aosp
    path: "frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingSurfaceDrawer.java"
  - type: aosp
    path: "frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/SplashscreenWindowCreator.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/IWindowSession.aidl"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/Session.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/SurfaceControl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TransitionController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/Transition.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/SurfaceAnimator.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/SurfaceAnimationRunner.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BLASTBufferQueue.java"
  - type: aosp
    path: "frameworks/base/core/jni/android_view_SurfaceControl.cpp"
  - type: official
    path: "developer.android.com/reference/android/view/WindowManager"
  - type: official
    path: "developer.android.com/develop/ui/views/layout/splash-screen"
  - type: official
    path: "developer.android.com/guide/navigation/custom-back/predictive-back-gesture"
  - type: official
    path: "developer.android.com/about/versions/16/features"
  - type: official
    path: "developer.android.com/about/versions/16/behavior-changes-all"
  - type: official
    path: "developer.android.com/about/versions/17/behavior-changes-all"
tags: [WMS, WindowManagerService, Surface, Window, StartingWindow, Window动画, 多窗口, SurfaceControl, WindowInsets, Desktop Windowing]
related_chapters: ["2.1", "2.6", "3.1", "8.2", "8.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+读者需求"
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-04"
task6_reviewed_date: "2026-05-04"
task6_result: "pass-light-edit"
last_task6_audit: "2026-06-25"
task9_result: auto-fixed
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
---
# 2.12 Window Manager Service 与窗口管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **WMS 的定位**：说明 WMS 位于 App、Input 系统、SurfaceFlinger 之间，并解释 system_server 多线程与 `mGlobalLock` 的排查意义
- 🔹 **Window 与 Surface 的关系**：区分 `WindowState`、`SurfaceControl`、`Surface`、SurfaceFlinger layer 和 BLASTBufferQueue 的职责边界
- 🔹 **StartingWindow 与启动性能**：说明 Android 12+ SplashScreen / TaskSnapshot starting window 在 ATMS/WMS、WM Shell、App 三侧的分工
- 🔹 **relayoutWindow 触发条件与内部流程**：区分纯 App traversal、同步 relayout、`relayoutAsync()` 和 WMS surface placement 的成本来源
- 🔹 **窗口动画与 Predictive Back**：说明现代 transition 路径、Shell / remote transition、leash transaction 和 SurfaceFlinger present 的排查顺序
- 🔹 **多窗口、折叠屏与 Desktop Mode**：解释自由窗口、caption bar、外接显示器和大屏适配如何提高 relayout / resize 频率
- 🔹 **Perfetto 综合分析与误区**：按 App、system_server、Shell、SurfaceFlinger 分段分析 WMS 相关性能问题

### 扩展（可选深入）

- 🔸 **WindowInsets 与布局性能**：说明 Insets 分发和 `requestLayout()` 如何放大布局成本
- 🔸 **WMS 与 Input 系统协作**：说明 Window Z-order、可见区域和 focus 信息如何影响 InputDispatcher hit-test
<!-- outline-end -->

## 为什么要了解 WMS

当我们分析 App 启动速度、界面切换卡顿、或者多窗口场景下的掉帧问题时，最终的线索往往都指向同一个地方——system_server 中的 WindowManagerService。

这并不是偶然。WMS 是 Android 窗口系统的中枢神经：从我们点击桌面图标那一刻起，WMS 就开始了一连串的工作——创建 StartingWindow 给用户即时的视觉反馈，为 App 分配 Surface 用于绘制，在 Activity 切换时管理过渡动画，在旋转屏幕时触发整个窗口树的 relayout。我们日常在 Perfetto 中看到的大量 system_server 活动，有相当一部分是 WMS 在工作。

不了解 WMS，我们在分析 Perfetto Trace 时遇到 system_server 的 Binder 调用就只能"看个热闹"。而理解了 WMS 的工作方式之后，我们就知道 `wm.relayout_window` 这个 Slice 对应的是什么操作，为什么它可能耗时，以及如何优化。这是把"system_server 好像很忙"变成"我知道它在忙什么"的关键一步。

[待补充：Trace 截图 — 一段典型的冷启动 Trace，标注 WMS 相关的 Slice]

## WMS 的定位：窗口世界的调度员

从图形架构看，WMS 夹在 App、Input 系统和 SurfaceFlinger 三者之间。它维护 WindowContainer / WindowState 树，决定窗口的层级、可见性、bounds、focus、Insets 和动画状态。SurfaceFlinger 负责把 App 提交的绘制内容合成上屏，InputDispatcher 则依赖 WMS 给出的可见区域和 Z-order 做命中测试——谁在最上面、谁能响应触摸，全看 WMS。

WMS 运行在 system_server 进程中，但性能问题不能简化成“AMS、IMS、WMS 共用一条主线程”。现代实现更接近“同进程、多线程、全局锁耦合”：`Binder:*` 线程接收 `IWindowSession` 和 `IWindow` 调用，`DisplayThread` 承载大量窗口管理逻辑，策略相关初始化和回调会经过 `UiThread` / `WindowManagerPolicyThread`，动画推进挂在 `AnimationThread`。Perfetto 里更常见的阻塞形态是这些线程围绕 `mGlobalLock` 和共享窗口状态互相等待，不是单个 `android.server` 线程把所有事务串行做完。

这直接影响排查方法。看到 `relayoutWindow`、StartingWindow 切换、窗口动画掉帧时，先判断耗时发生在 Binder 线程执行本身、等待 `mGlobalLock`，还是等待策略线程和动画线程推进共享状态。

WMS 与其他主要组件的协作关系可以这样概括：

- **AMS / ATMS**：负责 Activity 和 Task 的生命周期推进；当 Activity 需要显示、隐藏、切换或调整窗口模式时，把窗口侧约束交给 WMS 处理
- **SurfaceFlinger**：负责 layer 创建、transaction 消费和最终合成；WMS 管的是窗口容器与 `SurfaceControl` 属性，不直接负责像素合成
- **Input 系统**：InputDispatcher 依赖 WMS 提供的可见区域、Z-order 和 focus 信息做 hit-test；窗口焦点切换和输入命中测试因此会直接受 WMS 状态影响

## Window 与 Surface 的关系

每个应用窗口在 WMS 侧对应一个 `WindowState`。服务端持有的是 `SurfaceControl` 和窗口元数据，App 侧写像素的是 `Surface`，SurfaceFlinger 内部对应的是 layer / layer tree。三者分别负责的内容不同：

- **WMS 端**：创建或更新 `SurfaceControl`，维护 bounds、crop、alpha、layer、visibility、Insets 等属性
- **App 端**：通过 `ViewRootImpl` 和 `BLASTBufferQueue` 获取可绘制 `Surface`，决定何时 `dequeueBuffer`、绘制、`queueBuffer`
- **SurfaceFlinger 端**：根据 `SurfaceControl.Transaction` 和 buffer latch 结果完成合成

`relayoutWindow()` 返回给客户端的重点是 frames、Insets、`SurfaceControl` 和同步元数据。现代 BLAST 路径下，WMS 不会把一个“已经能画的 Surface 对象”直接打包回给 App；客户端的 `ViewRootImpl` 会基于 relayout 返回的 `SurfaceControl` 调用 `updateBlastSurfaceIfNeeded()` 创建或更新 `BLASTBufferQueue`，再用 `mSurface.transferFrom(...)` 把可绘制 `Surface` 句柄切到新的 backing surface。

### Surface 创建流程

Activity 首次显示时，窗口创建过程更接近下面这个顺序：

1. App 侧 `ViewRootImpl.performTraversals()` 发现 `mFirst=true`，通过 `IWindowSession.relayout()` 发起首次 relayout
2. WMS 在 `relayoutWindow()` 中更新 `WindowState`，判断是否需要创建或替换 `SurfaceControl`
3. 服务端创建 surface 相关对象时，Java / JNI 路径会落到 `android_view_SurfaceControl.cpp`，再经 `SurfaceComposerClient::createSurfaceChecked(...)` 请求 SurfaceFlinger 创建 layer
4. WMS 把新的 frames、Insets、`SurfaceControl`、sync 序列等放进 `RelayoutResult` 返回给 App
5. App 侧 `ViewRootImpl.updateBlastSurfaceIfNeeded()` 根据返回的 `SurfaceControl` 创建或更新 `BLASTBufferQueue`
6. `mSurface` 通过 `transferFrom(...)` 绑定到新的 BLAST backing surface，后续绘制再通过 `dequeueBuffer` / `queueBuffer` 提交第一帧

职责分界要记住：WMS 管窗口容器和 `SurfaceControl`，SurfaceFlinger 管 layer 创建与合成，App 侧负责把 relayout 返回的 `SurfaceControl` 转成可绘制的 `Surface`。不要写成“WMS 把 Surface 包好通过 Binder 返回给 App”——这句话把三层职责搅在一起了。

[已验证: AOSP android-17.0.0_r1, `ViewRootImpl.java` / `WindowManagerService.java` / `android_view_SurfaceControl.cpp`]

### SurfaceControl.Transaction 的批量提交

SurfaceControl 不是逐个属性去更新 Surface 的。WMS 使用 `SurfaceControl.Transaction` 机制来批量提交属性变更。一个 Transaction 可以包含多个操作（设置位置、设置大小、设置透明度等），调用 `Transaction.apply()` 时，所有操作原子性地提交给 SurfaceFlinger。

```java
// frameworks/base/core/java/android/view/SurfaceControl.java
// 伪代码：Transaction 的典型使用方式
SurfaceControl.Transaction t = new SurfaceControl.Transaction();
t.setPosition(surfaceControl, x, y);
t.setSize(surfaceControl, width, height);
t.setAlpha(surfaceControl, 0.5f);
t.apply(); // 一次性提交给 SurfaceFlinger
```

`Transaction.apply()` 的常规路径是在 framework 层经 JNI 进入 native `SurfaceComposerClient::apply()`，把 transaction 通过 Binder 交给 SurfaceFlinger，随后由 SurfaceFlinger 在后续合成周期消费。它通常不等待本次合成上屏。同步场景要单独看：`apply(true)`、BLAST sync transaction、`TransactionCommittedListener`、present fence 等路径可能让调用方等待提交确认或显示完成。首帧创建的耗时也要拆到 layer 创建、relayout 返回、buffer 分配和 fence 等位置，不宜只归因到 `apply()`。

## StartingWindow 与启动性能

冷启动是用户最直接感知到性能的场景之一。当我们点击一个 App 的图标到看到 App 内容之间，系统需要做很多工作：fork 进程、初始化 Runtime、加载 APK、执行 Application.onCreate()、创建 Activity、inflate View hierarchy、绘制第一帧。这个过程可能需要几百毫秒甚至几秒。

WMS 在这个过程中的角色是提供"即时反馈"——在 App 进程还没准备好之前，就给用户一个视觉上的回应。这就是 StartingWindow 的作用。

### StartingWindow 的工作原理

Android 12 之后，StartingWindow 的决策与实际创建分在两侧。ATMS/WMS 负责判断本次 Activity 启动是否需要 starting surface，`StartingSurfaceController` 根据 SplashScreen 或 TaskSnapshot 路径生成 starting data；WM Shell 的 starting-surface 组件负责创建 SplashScreen / TaskSnapshot 窗口并挂到对应 Task 上。常用源码锚点包括：

- `frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java`：服务端发起 starting surface 请求
- `frameworks/base/services/core/java/com/android/server/wm/SplashScreenStartingData.java`：保存 SplashScreen starting data
- `frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java`：Shell 侧接收 `TaskOrganizer.addStartingWindow` 回调
- `StartingSurfaceDrawer.java` / `SplashscreenWindowCreator.java`：Shell 侧创建并绘制 SplashScreen window

冷启动路径可以按这组边界读：

1. ATMS 推进 Activity 启动，WMS 在 `ActivityRecord` / Task 可见性变化中判断是否需要 starting surface。
2. `StartingSurfaceController` 生成请求，SplashScreen 路径使用 `SplashScreenStartingData`，历史任务恢复路径可能使用 TaskSnapshot starting data。
3. Android 12+ 的 Shell starting-surface 组件收到 `addStartingWindow` 回调后，在 Shell / SystemUI 侧创建 SplashScreen 或 TaskSnapshot 窗口。
4. App 进程启动并绘制主 Window 第一帧。
5. App 通过 `finishDrawing` / `reportDrawFinished` 让服务端知道主窗口已完成首帧，随后走 `removeStartingWindow` 路径通知 Shell 移除 starting surface。

Perfetto 里要把三段分开看：system_server 侧是 starting data、Activity/Task 状态和移除请求；Shell / SystemUI 侧才是 starting surface 的创建与绘制；App 侧的 `reportDrawFinished` 标记主 Window 首帧完成。把 starting surface 的绘制职责放在 system_server，会混淆服务端、Shell 和 App 进程边界。

[待补充：Trace 截图 — StartingWindow 创建和移除在 Perfetto 中的表现]

### Android 12 SplashScreen API

在 Android 12 之前，StartingWindow 的外观主要由 `windowBackground` 决定，OEM 定制差异较大。Android 12 引入 SplashScreen API（`android.window.splashscreen`），把启动页主题、icon、背景色、退出动画等配置收敛到统一接口：

- 开发者通过 `Theme.SplashScreen` 配置 icon、背景色、动画等元素。
- 退出动画通过 `setOnExitAnimationListener` 接入，移除时机仍要和主 Window 首帧完成信号配合。
- `androidx.core:splashscreen` 向后支持 Android 5.0+，但 Android 12+ 的系统 starting surface 创建仍落在 Shell starting-surface 路径。

这套 API 的性能价值在于减少 App 自建 SplashActivity。自建启动页会多一次 Activity 启动、窗口切换和可能的 relayout；系统 SplashScreen 则复用 starting surface 生命周期，不增加 App 侧 Activity 数量。

### StartingWindow 的时机陷阱

StartingWindow 的移除时机会影响启动体感：

- **过早移除**：App 主 Window 第一帧还没准备好时移除 starting surface，用户可能看到短暂闪白或闪黑。
- **过晚移除**：主 Window 已经完成首帧，starting surface 仍停留在前台，用户会把这段时间感知为启动变慢。

合理的切换点是 App 主 Window 首帧完成之后。服务端通过 `finishDrawing` / `reportDrawFinished` 收到首帧完成信号，再走 `removeStartingWindow` 路径让 Shell 移除 starting surface。分析启动 Trace 时，`reportDrawFinished` 只说明 App 首帧完成；视觉切换还要看 Shell 移除 starting surface、SurfaceFlinger 消费 transaction 和后续 present。

## relayoutWindow：WMS 最频繁的操作

`relayoutWindow()` 是 WMS 中调用最频繁的方法之一，Perfetto 里最常见到的 WMS Slice 也基本跟它有关。搞清楚它干了什么，是读懂 system_server 行为的前提。

### 什么触发 relayoutWindow

`ViewRootImpl.performTraversals()` 并不是每一帧都跨进程调用 WMS。只有命中 relayout 条件时，当前 traversal 才会走 `IWindowSession.relayout()`。主判断可以压成 6 个条件：

- **`mFirst`**：窗口首次显示，必须向 WMS 申请初始 `SurfaceControl`、frames 和 Insets
- **`windowShouldResize`**：`requestLayout()` 后测量结果改变了窗口尺寸，常见于旋转、多窗口 resize、Dialog `WRAP_CONTENT` 长大
- **`insetsChanged`**：IME、系统栏或 caption bar 的 Insets 状态变化，需要刷新窗口边界
- **`viewVisibilityChanged`**：窗口从隐藏到显示、从显示到隐藏，或 `mNewSurfaceNeeded=true`
- **`params != null`**：`setLayoutParams()`、system UI visibility、keepScreenOn 等窗口属性变化
- **`mForceNextWindowRelayout`**：WMS 通过 `resized()` / 配置变化回调强制下一次 traversal 重新 relayout

因此，`invalidate()` 只会触发 draw 的场景，不一定碰到 WMS；`requestLayout()` 也不等于一定跨进程。把所有 traversal 都解释成 `relayoutWindow`，Perfetto 诊断就会失真。

Android 14+ 增加了 `relayoutAsync()`，适用范围很窄。`ViewRootImpl.relayoutWindow()` 会先用客户端持有的 `InsetsState` 和 `WindowConfiguration` 计算一份临时 frame；只有窗口可见性未变化、窗口类型不是 `TYPE_APPLICATION_STARTING`、客户端没有等待新的 sync seq、AM 与 WMS 看到的 `WindowConfiguration` 无差异，并且本地算出的 frame 没有同时改变位置和尺寸时，才会调用 `IWindowSession.relayoutAsync()`。只改 `FLAG_KEEP_SCREEN_ON`、`screenBrightness` 这类不会触发窗口 frame 同步的属性时，较容易命中这条路径；如果变化会影响窗口可见性、尺寸、Insets、`SurfaceControl` 或 BLAST sync，仍走同步 `relayout()`。

服务端实现很薄：`Session.relayoutAsync()` 复用 `relayout(...)`，只是 `outRelayoutResult` 传 `null`，随后仍进入 `WindowManagerService.relayoutWindow()`。Trace 上的区别是 App UI 线程不用等待返回 frames、Insets、`SurfaceControl` 和 sync seq；system_server 侧仍会处理属性变化、`mGlobalLock` 和 surface placement。分析时要把当前 traversal 与后续 `W.resized()` / Insets 回调放在同一段时间线里。

### relayoutWindow 内部流程

WMS 侧的执行过程不能简化成“`relayoutWindow()` 直接调 `performLayout()`”。现代实现更接近下面这条路径：

1. App 侧 `performTraversals()` 判断本轮是否需要同步 relayout，随后通过 Binder 进入 `WindowManagerService.relayoutWindow()`
2. WMS 在 `mGlobalLock` 保护下更新 `WindowState`、可见性、布局参数、Insets 请求和 surface 生命周期状态
3. 需要重新摆放窗口树时，WMS 会走 `mWindowPlacerLocked.performSurfacePlacement(true)`，由 `WindowSurfacePlacer` 统一完成布局、layer 调整、Insets 计算和 transaction 应用
4. 返回给客户端的结果不只是窗口大小，还包括 `ClientWindowFrames`、`MergedConfiguration`、`InsetsState`、`InsetsSourceControl`、`SurfaceControl` 与 sync 序列
5. App 侧收到结果后会继续完成 post-relayout 的 measure / layout / draw；尺寸变化、Insets 变化或新 surface 建立时，还可能发生一轮额外 measure

这条路径解释了一个常见现象：同样叫 traversal，有的帧只是在 App 主线程做 measure / layout / draw，有的帧会把耗时扩散到 App 主线程、system_server Binder 线程、DisplayThread 和动画线程。两类 trace 长得完全不同。

### App 侧 traversal 与 WMS relayout 的对应关系

| 场景 | 是否跨进程进入 WMS | Perfetto 观察重点 |
|------|------------------|------------------|
| `invalidate()` 触发的纯重绘 | 否 | App 主线程 `performDraw` 与 RenderThread |
| `requestLayout()` 但窗口尺寸未变 | 通常否 | App 主线程 measure / layout / draw |
| 首帧、窗口 resize、Insets 变化 | 是 | App 主线程 Binder 等待，加 system_server Binder / DisplayThread 配套工作 |
| 只改不会影响 frame 同步的窗口属性，且命中 `relayoutAsync()` 条件 | 异步 | App 当前 traversal 不等 `RelayoutResult`；后续 `W.resized()` / Insets 回调再刷新本地状态 |

### scheduleTraversals() 与 performTraversals() 的职责边界

`ViewRootImpl.scheduleTraversals()` 是 App 侧调度入口，不跨进程。它向 Choreographer 投递 `TraversalRunnable`，在下一次 VSync 时触发 `doTraversal()` → `performTraversals()`。WMS 跨进程调用只发生在 `performTraversals()` 内部条件满足时。

**关键源码路径**（android-17.0.0_r1，`ViewRootImpl.java`）：

```java
// 调度入口 — App 进程内，不跨进程
void scheduleTraversals() {
    if (!mTraversalScheduled) {
        mTraversalScheduled = true;
        mChoreographer.postCallback(Choreographer.CALLBACK_TRAVERSAL,
                mTraversalRunnable, null);
    }
}

// performTraversals 内部的条件判断 — 跨进程阈值
final boolean relayoutRequested = mFirst || windowShouldResize
        || viewVisibilityChanged || insetsChanged || params != null
        || mForceNextWindowRelayout;

if (relayoutRequested) {
    // 这里才跨进程 → WMS
    relayoutWindow(mAttributes, viewVisibilityChanged, insetsFlags, ...);
}
```

**因此**：`requestLayout()` → `scheduleTraversals()` → `performTraversals()`，全程在 App 进程内执行；只有当窗口尺寸、Insets 或属性实际变化时，才在 `performTraversals()` 内部触发 `relayoutWindow()` 跨进程调用 WMS。

**Perfetto 区分表**：

| Slice 名称 | 进程 | 线程 | 含义 |
|-----------|------|------|------|
| `ViewRootImpl#doTraversal` | App | UI Thread | App 侧 measure/layout/draw 调度 |
| `ViewRootImpl#performTraversals` | App | UI Thread | 完整 measure+layout+draw，内可能嵌套 `relayoutWindow` |
| `relayoutWindow` | system_server | WMS 线程 | WMS 侧 Window 属性更新，跨进程入口 |

**时序判读**：
- WMS 发起 → App：`relayoutWindow` 先于 `doTraversal`（键盘弹出、屏幕旋转等系统事件）
- App 发起 → WMS：`performTraversals` 内嵌套 `relayoutWindow`（App 的 LayoutParams 变化驱动）

### 在 Perfetto 中的表现

看 WMS 相关 trace，先确认 capture 配置里是否打开了 `wm`、`view`、`am`、`input`、`gfx`、`surfaceflinger` 这些类别。没有这些类别时，system_server 侧只会留下零散 Binder slice，很难还原 relayout 路径。

切片名也不要写死。`wm.relayout_window`、`SurfaceControl.Transaction.apply`、`animator`、`reportDrawFinished` 都可能因 Android 版本、atrace category、Perfetto config 和 OEM 定制而变化。更稳妥的办法是先枚举实际 trace 里出现的 slice 名，再写针对性 SQL。

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
- 当前帧有没有同步 relayout IPC
- system_server 里卡在 Binder 执行、等 `mGlobalLock`，还是等 animation / policy 相关线程
- 返回 App 之后，额外成本落在 re-measure、Insets 分发，还是首帧 draw

## Window 动画与过渡性能

切换 App、回到桌面、打开 Recent 页面和预测返回都属于窗口过渡。现代 Android 不能再按“WMS 创建某个 Activity 专用 animator，然后统一调度切换动画”来理解。Android 12-14 仍能看到 legacy `AppTransition` 与 `TransitionController` 并存；到 Android 16，主线口径已经转向 `TransitionController` / `Transition` 收集 WindowContainer 变化，再由 WM Shell transition、remote transition 或服务端 surface animation 路径执行动画。

### 动画路径如何分工

Activity 切换、回到桌面、打开 Recents、predictive back——这些过渡几乎都跨 ATMS/WMS、WM Shell、SurfaceFlinger 三层协作：

1. ATMS/WMS 更新 `ActivityRecord`、Task、DisplayContent 等 WindowContainer 状态，并由 `TransitionController` 收集 open / close / change。
2. `Transition` 把参与过渡的窗口、leash、起止 bounds、可见性变化整理成一次 transition。
3. 如果本轮过渡交给 Shell，WM Shell transition handler 或 remote transition 根据 leash 构建动画；Recents、跨 Task、桌面模式和 predictive back 常走这条路径。
4. 服务端动画仍会用到 `SurfaceAnimator` / `SurfaceAnimationRunner` 等组件，把每帧 transform、alpha、crop 写入 `SurfaceControl.Transaction`。
5. SurfaceFlinger 在后续 `commit` / `composite` 中消费这些 transaction，完成合成与 present。

每帧成本主要落在三处：transition 状态收集、Shell / remote transition handler 计算动画、`SurfaceControl.Transaction` 应用与 SurfaceFlinger 合成。120Hz 屏幕下单帧预算约 8.33ms，任何一层把 transaction 或合成拖长，过渡都会出现掉帧。

源码阅读可从这些入口进入：

- `frameworks/base/services/core/java/com/android/server/wm/TransitionController.java`：收集和调度 WindowContainer transition
- `frameworks/base/services/core/java/com/android/server/wm/Transition.java`：记录参与过渡的窗口变化
- `frameworks/base/services/core/java/com/android/server/wm/SurfaceAnimator.java`：对 surface leash 执行动画
- `frameworks/base/services/core/java/com/android/server/wm/SurfaceAnimationRunner.java`：驱动 surface animation 的帧推进
- `frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/transition/`：Shell transition handler 与 remote transition 接入

### Activity 切换动画

Activity open / close 动画可以按版本分层理解：

| 版本范围 | 主线口径 | 排查重点 |
|----------|----------|----------|
| Android 12-14 | legacy `AppTransition` 仍覆盖一部分路径，`TransitionController` 和 Shell transition 逐步接管 Task / Activity 级过渡 | 同时看 `wm`、`transition`、`android.anim*`、Shell 进程和 SurfaceFlinger transaction |
| Android 15-16 | `TransitionController` / Shell transition 成为 Activity、Recents、predictive back、桌面模式等场景的主要分析入口 | 先定位 transition id，再看 Shell handler、remote transition、leash transaction 与 SF `commit` / `composite` |

一次 Activity 切换里，旧 Activity 和新 Activity 的 Window 往往会被包到 leash surface 下。动画过程更新的是 leash 的 transform、alpha、crop 和 layer，而不是让 App 每帧重绘 Activity 内容。App 侧首帧准备慢、Shell 动画线程慢、system_server transition 状态收集慢、SurfaceFlinger 合成慢，都会表现成切换掉帧，但根因落点不同。

Perfetto 里不要只看 `android.anim`。如果掉帧发生在 Activity open / close 期间，应按这个顺序拆：

1. App 主线程和 RenderThread 是否按时提交首帧。
2. system_server 里 transition collect / ready / finish 是否被锁等待或 Binder 调用拖长。
3. Shell / SystemUI 进程里的 transition handler 是否每帧稳定产出 transaction。
4. SurfaceFlinger 的 `commit` / `composite` / present 是否消化了这些 transaction。

### Predictive Back 动画

Predictive Back 的版本线要拆开读：

- **Android 13**：引入 `OnBackInvokedCallback` 和预测返回早期能力，系统动画可通过开发者选项测试。
- **Android 14**：完善跨 Activity、跨 Task 和自定义过渡接入，开发者仍经常通过开发者选项验证 predictive back animation。
- **Android 15**：开发者选项不再是系统动画显示前提；对已经 opt-in 的应用或 Activity，back-to-home、cross-task、cross-activity 等系统动画会按系统策略显示。未 opt-in 的应用仍按传统返回行为处理。
- **Android 16**：继续补充 `finishAndRemoveTaskCallback`、`moveTaskToBackCallback` 等回调，便于区分 finish、move task to back 等返回结尾场景。

它的性能路径跨 Input、ATMS/WMS、Shell transition 和 SurfaceFlinger。手势开始后，Input 侧持续上报 back progress；WMS / Shell 根据返回目标更新当前窗口和目标窗口的 leash；手势完成或取消时，transition 进入 finish 或 cancel。分析卡顿时要同时看 Input 事件节奏、Shell transition handler、system_server transition 状态，以及 SurfaceFlinger 是否在同一时间段出现 transaction 堆积。

[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/predictive-back-gesture]

## 多窗口、折叠屏与 Desktop Mode

Android 的多窗口能力经历了从实验性功能到核心特性的演变。如今 Split-screen、Freeform、Picture-in-Picture（PiP）已经全面铺开，Android 16 更是将 Desktop Windowing 推向了 GA（Generally Available）。这些模式会让 WMS 同时处理更多可见窗口、更多 bounds 变化和更多 relayout 请求。

### 多窗口模式下的 WMS 工作量

在单窗口模式下，WMS 主要管理一个前台 App 的 Window 和几个系统 Window（状态栏、导航栏等）。但在多窗口模式下：

- **Split-screen**：WMS 需要同时管理两个 App 的 Window，计算它们的分屏边界
- **Freeform**：每个自由窗口都有自己的 WindowState、SurfaceControl 和 Window frames
- **PiP**：画中画窗口虽然是缩小版，但它的 Window 生命周期和 Surface 更新逻辑和全屏 Window 一样完整

WMS 的 `performLayout()` 需要处理的 Window 数量因此成倍增加，每个 SurfaceControl.Transaction 包含的操作也更多。在低端设备上，多窗口模式是 system_server CPU 占用上升的常见原因。

### 折叠屏与大屏配置变更

折叠、展开、拖到外接显示器，都会让 WMS 处理一次窗口边界和显示区域变化。路径通常是 DisplayManager / WindowOrganizer 通知 WMS，WMS 更新可见窗口的 frames、Insets 和 configuration，再把结果回送给 App。App 是否重建 Activity，取决于目标 API、compat 行为和自身声明的配置变化处理方式。

Android 16 针对 `sw >= 600dp` 设备强化了 adaptive behavior。target API 36 的应用在大屏上更可能被系统忽略 `screenOrientation`、`resizeableActivity`、aspect ratio 等限制，窗口尺寸变化会更频繁地落到 WMS relayout 和 App configuration callback。Android 17 的 `android:recreateOnConfigChanges` 需要和传统 `android:configChanges` 分开读：`configChanges` 声明应用自行处理某类变化（keyboard、navigation、screenSize、uiMode 等），避免系统重建；`recreateOnConfigChanges` 在 AOSP `attrs_manifest.xml` 中只声明了 `mcc` 和 `mnc`，是 API 37 Beta 中面向部分配置变化的重建策略信号，当前不能外推到其他配置类型。Android 17 对大屏的主要影响是 orientation / resizability opt-out 的移除——这会提高窗口尺寸变化和 configuration callback 的频率，而非扩展 `recreateOnConfigChanges` 的覆盖范围。

### Android 16 Desktop Windowing

Android 16 把 connected display desktop windowing 作为正式特性公开。对 WMS 来说，自由窗口、caption bar insets、多实例和跨 display 移动都会提高 relayout 频率，也会让 `performSurfacePlacement(true)` 处理更多可见 window。

从性能分析的角度看，这类场景里的 system_server Binder 线程只是入口。DisplayThread 的窗口摆放、AnimationThread 的过渡推进，以及 SurfaceFlinger 对 transaction 和 buffer resize 的处理，都需要放到同一时间线上看。

## 在 Perfetto 中的综合表现

把 WMS 放回 Perfetto 时，先按线程和阶段分组，不要先背 slice 名。

### 先看哪些线程

| 线程 / 进程 | 常见职责 | 观察意义 |
|-----------|---------|---------|
| system_server `Binder:*` | `relayoutWindow`、visibility、window transaction 入口 | 看 IPC 本身和锁等待 |
| system_server DisplayThread | 窗口摆放、display 相关更新 | 看 `performSurfacePlacement(true)` 和 display 变更 |
| system_server `android.anim*` | 窗口动画、transition 推进 | 看动画帧是否被别的线程拖慢 |
| App 主线程 | `performTraversals`、resize callback、首帧 draw | 看 traversal 是否因 relayout 变重 |
| RenderThread | `syncAndDrawFrame` | 区分 WMS 问题和渲染问题 |
| SurfaceFlinger | transaction apply、latch、composition | 看 buffer / transaction 是否在合成侧堆积 |

### 先枚举 slice，再做专项查询

不要把 `wm.pause_timeout`、`wm.relayout_window`、`SurfaceControl.Transaction.apply` 当成所有版本都稳定存在的名字。更稳妥的顺序是：

1. 先枚举 system_server、App、SurfaceFlinger 中实际出现的 `relayout`、`window`、`surface`、`anim`、`draw` 相关 slice
2. 再按线程聚类，确认这一帧落在哪个进程和哪条线程
3. 随后只对当前 trace 里存在的 slice 名写 SQL

### 典型分析场景

**场景 1：冷启动**

1. 在 App 主线程确认首帧 `performTraversals` 是否命中 `mFirst`
2. 在 system_server Binder 线程和 DisplayThread 找首次 relayout / surface placement
3. 回看 App 的首帧 draw 完成点，再确认 StartingWindow 退出时机

**场景 2：多窗口切换掉帧**

1. 从掉帧帧号回看 App 主线程和 RenderThread
2. 再看 system_server 的 AnimationThread、Binder 线程、DisplayThread 是否在同一时段变重
3. 如果同时出现窗口 resize 或 Insets 变化，再把 relayout 和 animation 拆开计时

**场景 3：旋转或桌面模式 resize 卡顿**

1. 先确认是不是窗口边界变化触发了同步 relayout
2. 再看 `performSurfacePlacement(true)` 之后的额外成本落在 frames / Insets 返回还是 App 侧 re-measure
3. 结合 SurfaceFlinger 的 transaction / latch 情况，判断是否还有 buffer resize 带来的合成侧放大成本

## 与其他机制的关系

WMS 不是一个孤立的系统服务，它的性能表现受到多个上下游的影响：

- **§2.1 渲染架构全景**：WMS 是 App 绘制和 SurfaceFlinger 合成之间的桥梁
- **§2.6 SurfaceFlinger 与合成**：WMS 通过 SurfaceControl.Transaction 与 SurfaceFlinger 交互，Transaction 的执行时机影响合成效率
- **§2.13 图形缓冲区管理**：Surface 的创建涉及 BufferQueue 的分配，BufferQueue 的 producer/consumer 模型决定了 App 和 SurfaceFlinger 的协作方式
- **§3.1 Input 事件分发**：WMS 维护的 Window Z-order 和焦点信息是 InputDispatcher 进行 hit-test 的基础
- **§8.2 启动速度分析**：StartingWindow 的创建和移除时机直接影响启动体感
- **§8.4 其他响应速度场景**：旋转屏幕、多窗口切换等场景中 WMS 的 relayout 是性能关键路径

## 版本演进

下表只保留对当前 WMS 调试口径影响最大的版本节点。

| 版本 | 变化 | 性能影响 | 参考锚点 |
|------|------|---------|---------|
| Android 12 (API 31) | SplashScreen API 统一 StartingWindow | 启动反馈路径更标准，但 Android 12+ 的 SplashScreen / TaskSnapshot starting window 创建与绘制主要落在 WM Shell starting-surface 路径 | `developer.android.com/develop/ui/views/layout/splash-screen` |
| Android 13 (API 33) | `OnBackInvokedCallback` 与 Predictive Back 早期能力 | 应用可接入新的 back callback；系统预测返回动画多处仍需要开发者选项辅助测试 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture` |
| Android 14 (API 34) | Predictive Back 跨 Activity / 自定义过渡能力继续完善 | 返回手势进入实时预览，Input、WMS transition 与 Shell transition 需要放在同一段时间轴内分析 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture` |
| Android 15 (API 35) | Predictive Back 系统动画不再依赖开发者选项；Edge-to-Edge enforcement 扩大覆盖面 | 已 opt-in 的应用 / Activity 会显示 back-to-home、cross-task、cross-activity 等系统动画；Insets 分发也更常见 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture` / `developer.android.com/about/versions/15/behavior-changes-15` |
| Android 16 (API 36) | Desktop Windowing 与大屏 adaptive behavior | 自由窗口、caption bar、外接显示器和强制可调整窗口会提高 relayout / resize 频率 | `developer.android.com/about/versions/16/features` / `developer.android.com/about/versions/16/behavior-changes-all` |
| Android 17 (API 37) | orientation / resizability opt-out 移除，窗口尺寸变化和 configuration callback 频率提高；`recreateOnConfigChanges` 仅覆盖 `mcc`/`mnc`，不能外推到其他配置类型 | `developer.android.com/about/versions/17/behavior-changes-all` |

## 常见问题与误区

### 误区 1："WMS 在主线程上运行，所以很慢"

WMS 横跨 system_server 内的 Binder 线程、DisplayThread、UiThread / WindowManagerPolicyThread 和 AnimationThread。慢的根源通常是 `mGlobalLock` 竞争、共享窗口状态更新、surface placement 或动画推进——不是一句“主线程忙”能概括的。Perfetto 里要同时看 Binder 入口、DisplayThread 的布局摆放、AnimationThread 的过渡推进，以及主线程上是否有策略或 AMS 相关工作交叉干扰。

### 误区 2："Window 数量越多越卡"

Window 数量本身不是问题。需要关注的是有多少 Window 参与 `performLayout()` 的计算。一个后台 App 的隐藏 Window 几乎不消耗 WMS 的资源。性能瓶颈是"同时可见的、需要频繁 relayout 的 Window 数量"——这正是多窗口和 Desktop 模式下需要关注的。

### 误区 3："StartingWindow 是 App 画的"

StartingWindow 不是 App 主 Window 的第一帧。现代 Android 的边界是：ATMS/WMS 判断是否需要 starting surface 并发出生命周期请求；Android 12+ 的 SplashScreen / TaskSnapshot starting window 多由 WM Shell starting-surface 组件创建和绘制。App 进程完成主窗口首帧之前，Shell 侧 starting surface 已经挂到 Task 上。

### 误区 4："relayoutWindow 慢一定是 WMS 的问题"

`relayoutWindow` 慢可能是 WMS 自身计算重，也可能是窗口树更新后的连带成本大。常见放大源包括：等待 `mGlobalLock`、`performSurfacePlacement(true)` 处理过多可见窗口、Insets / configuration 返回触发 App 侧 re-measure、surface resize 让 SurfaceFlinger 的 transaction / latch 变重。排查时至少同时看 App 主线程、system_server 多条线程和 SurfaceFlinger。

### 误区 5："Predictive Back 动画延迟是 Input 系统的问题"

Predictive Back 动画涉及 Input 系统和 WMS 的协作。手势事件的分发由 Input 系统负责，但动画的计算和 SurfaceControl 更新**不是** WMS 的 `WindowAnimator` 在做——那是旧 AppTransition 架构的职责。Android 12+ 的 predictive back 主线路径是：ATMS/WMS 的 `TransitionController` / `Transition` 收集窗口状态变化，再由 WM Shell 的 `BackAnimationController` 或 transition handler 构建动画并提交 leash transaction。如果手势响应延迟，排查分四段：Input progress（事件是否及时到达 App）、ATMS/WMS transition 状态（是否已收集到状态变更）、WM Shell BackAnimationController / transition handler（动画是否在构建和执行）、SurfaceFlinger transaction/present（leash 变更是否在预期 VSync 生效）。

## 扩展

### 🔸 WindowInsets 与布局性能

WindowInsets 是 WMS 向 App 传递系统 UI 元素（状态栏、导航栏、键盘、刘海屏）占用空间的机制。理解它的分发路径对优化布局性能很重要。

分发路径是这样的：WMS 计算每个 Window 的 Insets → 通过 `relayoutWindow` 的返回值传递给 ViewRootImpl → ViewRootImpl 触发 View hierarchy 的 `dispatchApplyWindowInsets` → 各 View 根据 Insets 调整自己的 padding/margin。

性能风险在于：如果 App 在 Insets 处理中调用了 `requestLayout()`，会触发整棵 View 树的 measure/layout pass。如果 WindowInsets 频繁变化（如动画过程中），这个开销会在 Insets 动画期间被放大。Android 15 强制 Edge-to-Edge 后，更多 App 需要主动处理 Insets，这个问题变得更加普遍。

优化建议：使用 Compose 的 `Modifier.windowInsetsPadding()` 替代手动 padding 计算；在 View 系统中使用 `setOnApplyWindowInsetsListener` 精确处理，避免使用 `fitsSystemWindows="true"` 的盲目全局处理；处理完 Insets 后调用 `WindowInsets.CONSUMED` 防止不必要的向下分发。

### 🔸 WMS 与 Input 系统的协作

WMS 维护的 Window Z-order 和区域信息是 InputDispatcher 进行 hit-test 的基础。当用户触摸屏幕时：

1. InputDispatcher 从 WMS 获取当前所有可见 Window 的区域和 Z-order
2. 按照从上到下的 Z-order 遍历 Window，找到第一个包含触摸坐标的 Window
3. 将触摸事件通过 InputChannel 发送给该 Window 所属的 App 进程

窗口焦点（focus）切换的性能影响容易被忽视。当焦点从一个 App 切换到另一个 App 时（如启动新 Activity），Input 通道也需要切换。在切换的瞬间（通常只有几毫秒），可能会有 Input 事件丢失。这在快速操作场景（如连续快速点击）中可能导致"点了没反应"的用户体验。

这个问题在 §3.1 中有更详细的分析，包括如何在 Perfetto 中追踪 Input 通道的切换过程。

## 参考资料

- [AOSP WindowManagerService 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java) ，`relayoutWindow()` 和窗口状态管理入口
- [AOSP WindowSurfacePlacer 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowSurfacePlacer.java) ，`performSurfacePlacement(true)` 的主执行点
- [AOSP StartingSurfaceController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java) ，服务端 starting surface 请求入口
- [AOSP WM Shell StartingWindowController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java) ，Shell 侧 `addStartingWindow` / `removeStartingWindow` 入口
- [AOSP TransitionController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/TransitionController.java) ，WindowContainer transition 收集与调度入口
- [AOSP ViewRootImpl 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/ViewRootImpl.java) ，App 侧 traversal、`relayout()` 判定和 `updateBlastSurfaceIfNeeded()`
- [AOSP SurfaceControl JNI 路径](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/jni/android_view_SurfaceControl.cpp) ，native `createSurfaceChecked(...)` 入口
- [AOSP BLASTBufferQueue 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/graphics/java/android/graphics/BLASTBufferQueue.java) ，客户端 surface materialization
- [Android 官方文档，SplashScreen API](https://developer.android.com/develop/ui/views/layout/splash-screen) ，StartingWindow 与统一启动体验
- [Android 官方文档，Predictive Back](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture) ，返回手势动画与过渡回调
- [Android 官方文档，Android 16 Features](https://developer.android.com/about/versions/16/features) ，Desktop Windowing 与 connected display 特性
- [Android 官方文档，Android 16 Behavior Changes](https://developer.android.com/about/versions/16/behavior-changes-all) ，大屏自适应与 orientation / resizable 行为变化
- [Android 官方文档，Android 17 Behavior Changes](https://developer.android.com/about/versions/17/behavior-changes-all) ，`recreateOnConfigChanges` 的 API 37 Beta 口径
- [Android 官方文档，WindowInsets](https://developer.android.com/develop/ui/views/layout/window-insets) ，Insets 分发与适配实践

