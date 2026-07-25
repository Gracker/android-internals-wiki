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
    path: "https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp"
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
last_task6_audit: "2026-06-25"
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

App 冷启动、Activity/Task 过渡、IME、旋转、分屏和桌面窗口 resize 都会改变窗口状态。Trace 里如果只盯 App 主线程或 SurfaceFlinger，很容易漏掉 system_server 与 WM Shell 之间的状态收集、同步和几何 transaction。

WMS 负责维护 WindowContainer/WindowState 树，并把 Activity/Task 状态转换成窗口 bounds、可见性、层级、Insets、focus、input window info 与 `SurfaceControl` 属性。它不绘制 App 像素，也不执行最终合成。

本章的排查目标是把一次窗口变化拆成四段：

1. App 的 `ViewRootImpl` traversal、relayout IPC 与新 buffer；
2. system_server 的窗口状态、锁、layout/surface placement 与 transition collect；
3. WM Shell 的 starting surface、transition handler 与 leash 动画；
4. SurfaceFlinger/HWC 的 transaction、buffer latch、composition 与 present。

四段里最先偏离目标时间的对象，才是下一步需要继续追的方向。

## WMS 的定位：窗口状态与 Surface 拓扑

从图形架构看，WMS 夹在 App、Input 系统和 SurfaceFlinger 三者之间。它维护 WindowContainer / WindowState 树，决定窗口的层级、可见性、bounds、focus、Insets 和动画状态。SurfaceFlinger 负责把 App 提交的内容合成上屏；WMS 的 `InputMonitor` 则把可触摸区域、层级、focusability 与 input channel token 写入 `InputWindowHandle`，通过 transaction 发布给 InputDispatcher。

WMS 运行在 system_server 进程中，但性能问题不能简化成“AMS、IMS、WMS 共用一条主线程”。现代实现更接近“同进程、多线程、全局锁耦合”：`Binder:*` 线程接收 `IWindowSession` 和 `IWindow` 调用，`DisplayThread` 承载大量窗口管理逻辑，策略相关初始化和回调会经过 `UiThread` / `WindowManagerPolicyThread`，动画推进挂在 `AnimationThread`。Perfetto 里更常见的阻塞形态是这些线程围绕 `mGlobalLock` 和共享窗口状态互相等待，不是单个 `android.server` 线程把所有事务串行做完。

这直接影响排查方法。看到 `relayoutWindow`、StartingWindow 切换、窗口动画掉帧时，先判断耗时发生在 Binder 线程执行本身、等待 `mGlobalLock`，还是等待策略线程和动画线程推进共享状态。

WMS 与其他主要组件的职责可以这样分：

- **AMS / ATMS**：负责 Activity 和 Task 的生命周期推进；当 Activity 需要显示、隐藏、切换或调整窗口模式时，把窗口侧约束交给 WMS 处理
- **SurfaceFlinger**：负责 layer 创建、transaction 消费和最终合成；WMS 管的是窗口容器与 `SurfaceControl` 属性，不直接负责像素合成
- **Input 系统**：InputDispatcher 依赖 WMS 提供的可见区域、Z-order 和 focus 信息做 hit-test；窗口焦点切换和输入命中测试因此会直接受 WMS 状态影响

## Window 与 Surface 的关系

每个应用窗口在 WMS 侧对应一个 `WindowState`。服务端维护窗口元数据与 `SurfaceControl` 关系，App 侧通过 `Surface` 写像素，SurfaceFlinger 内部维护 layer snapshot 与输出。几个对象的职责不同：

- **WMS 端**：关联或更新窗口 `SurfaceControl`，维护 bounds、crop、alpha、layer、visibility、Insets 等属性
- **App 端**：通过 `ViewRootImpl` 和 `BLASTBufferQueue` 获取可绘制 `Surface`，决定何时 `dequeueBuffer`、绘制、`queueBuffer`
- **SurfaceFlinger 端**：根据 `SurfaceControl.Transaction` 和 buffer latch 结果完成合成

Android 17 同时保留两种 relayout surface 协议：

- service-surface 路径通过同步 `relayout()` 返回 `WindowRelayoutResult` 与 `SurfaceControl`；
- client-surface 路径由 `ViewRootImpl.updateSurfaceControl()` 在客户端创建/复用 `SurfaceControl`，再经 `relayout2()` / `relayoutAsync2()` 传给 WMS。

两条路径最终都要让客户端 render target 与 BLAST backing 对齐。`ViewRootImpl` 根据有效的 `SurfaceControl` 更新 renderer 和 `BLASTBufferQueue`，App 后续才通过可绘制 `Surface` dequeue/draw/queue。文档或 trace 必须先确认 `WindowManager.useClientSurface()` 与相关 feature flag，不能把某一分支写成 Android 17 的唯一实现。

### Surface 创建流程

Activity 首次显示时，可以按下面的稳定边界理解：

1. App 的 `performTraversals()` 因 `mFirst=true` 进入 relayout；
2. `Session.relayout()` / `relayout2()` 调用 `WindowManagerService.relayoutWindow()`；
3. WMS 更新 `WindowState`、frames、Insets、可见性、sync 与 surface 状态；
4. service-surface 分支返回服务端 surface control，client-surface 分支使用客户端传入的 control；
5. `ViewRootImpl` 更新 frame/Insets、render target 和 BLAST；
6. App 绘制第一帧并 queue buffer，SurfaceFlinger 才能在后续周期 latch 与 present。

WMS 管窗口容器与 layer 控制关系；App 生成窗口内容；SurfaceFlinger 管 layer 状态消费和合成。Binder 传递的是控制对象、frame 和同步元数据，不是已绘制好的像素。

[已验证: AOSP android-17.0.0_r1, `ViewRootImpl.java` / `WindowManagerService.java` / `android_view_SurfaceControl.cpp`]

### SurfaceControl.Transaction 的批量提交

WMS 用 `SurfaceControl.Transaction` 批量提交 layer 属性。一个 Transaction 可以包含位置、buffer size、alpha、crop、reparent 等多个操作，调用 `apply()` 后作为一个 transaction 交给 SurfaceFlinger。

```java
// frameworks/base/core/java/android/view/SurfaceControl.java
// 伪代码：Transaction 的典型使用方式
SurfaceControl.Transaction t = new SurfaceControl.Transaction();
t.setPosition(surfaceControl, x, y);
t.setBufferSize(surfaceControl, width, height);
t.setAlpha(surfaceControl, 0.5f);
t.apply(); // 一次性提交给 SurfaceFlinger
```

这段代码展示的是属性批处理，不代表 buffer 内容已完成或 panel 已显示。`Transaction.apply()` 的常规路径经 JNI 进入 native `SurfaceComposerClient::apply()`，再通过 Binder 交给 SurfaceFlinger；调用通常不等待本次合成上屏。同步场景要单独看 `apply(true)`、BLAST sync、transaction committed/completed listener 与 present fence。首帧耗时还要拆到 layer 创建、relayout、buffer 分配和 fence。

## StartingWindow 与启动性能

冷启动期间，进程创建、Runtime/Application/Activity 初始化和首帧绘制尚未完成。StartingWindow 在这段空档提供可见内容，避免用户只看到桌面、空白或旧画面。

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

主 Window 首帧完成后，服务端才具备移除 StartingWindow 的内容条件。服务端通过 `finishDrawing` / `reportDrawFinished` 收到信号，再走 `removeStartingWindow` 路径让 Shell 移除 starting surface。分析启动 Trace 时，`reportDrawFinished` 只说明 App 首帧完成；视觉切换还要看 Shell 移除、SurfaceFlinger 消费 transaction 和后续 present。

## relayoutWindow：重新协商窗口契约

`relayoutWindow()` 重新协商窗口属性、frame、Insets、surface 与同步序列。它可能嵌在 App traversal 的同步 Binder 调用里，也可能由 oneway `relayoutAsync()` 送到 system_server。两种调用都需要 WMS 处理，差别在于客户端是否等待返回结果。

### 什么触发 relayoutWindow

`ViewRootImpl.performTraversals()` 不会每帧跨进程调用 WMS。Android 17 `ViewRootImpl.java` 的直接条件是下面五类：

- **`mFirst`**：窗口首次显示，必须向 WMS 申请初始 `SurfaceControl`、frames 和 Insets
- **`windowShouldResize`**：`requestLayout()` 后测量结果改变了窗口尺寸，常见于旋转、多窗口 resize、Dialog `WRAP_CONTENT` 长大
- **`viewVisibilityChanged`**：窗口从隐藏到显示、从显示到隐藏，或 `mNewSurfaceNeeded=true`
- **`params != null`**：`setLayoutParams()`、system UI visibility、keepScreenOn 等窗口属性变化
- **`mForceNextWindowRelayout`**：WMS 通过 `resized()` / 配置变化回调强制下一次 traversal 重新 relayout

Insets 变化会先走 `mApplyInsetsRequested`、`dispatchApplyInsets()`，并可能引起 measure/layout、窗口属性变化或强制 relayout，但 `insetsChanged` 不是 Android 17 这段 `if` 的独立布尔条件。`invalidate()` 的纯 draw 不会因此进入 WMS；`requestLayout()` 也只有在上述条件成立时才跨进程。

Android 14+ 增加了 `relayoutAsync()`。Android 17 的 `canRelayoutAsync()` 会检查 starting window、待处理 sync/seq、AM/WMS `WindowConfiguration` 差异等条件；随后客户端用本地 `InsetsState` 和 `WindowConfiguration` 计算 frame。若位置和尺寸同时变化、需要取得新的 sync seq，就回到同步 relayout。启用 fluid-resize/client-surface 相关 flag 后，分支还会不同，Review 必须以目标 build 的 feature flags 为准。

服务端实现很薄：`Session.relayoutAsync()` / `relayoutAsync2()` 复用 `relayout(...)`，只把 `outRelayoutResult` 设为 `null`，随后仍进入 `WindowManagerService.relayoutWindow()`。Trace 上的区别是 App UI 线程不等待 frames、Insets、surface control 和 sync seq 返回；system_server 仍要处理属性变化、`mGlobalLock` 与后续 placement。分析时要把当前 traversal 和之后的 `IWindow.resized()` / Insets callback 放在同一段时间线里。

### relayoutWindow 内部流程

WMS 侧的执行过程不能简化成“`relayoutWindow()` 直接调 `performLayout()`”。现代实现更接近下面这条路径：

1. App 侧 `performTraversals()` 判断本轮是否需要同步 relayout，随后通过 Binder 进入 `WindowManagerService.relayoutWindow()`
2. WMS 在 `mGlobalLock` 保护下更新 `WindowState`、可见性、布局参数、Insets 请求和 surface 生命周期状态
3. 需要重新摆放窗口树时，WMS 会走 `mWindowPlacerLocked.performSurfacePlacement(true)`，由 `WindowSurfacePlacer` 统一完成布局、layer 调整、Insets 计算和 transaction 应用
4. 同步路径返回 `ClientWindowFrames`、`MergedConfiguration`、`InsetsState`、`InsetsSourceControl` 与 sync 序列；surface control 由 service-surface 返回或 client-surface 传入
5. App 侧收到同步结果后继续 post-relayout 的 measure/layout/draw；异步路径则等待后续 resize/Insets/configuration callback 更新本地状态

这条路径解释了一个常见现象：同样叫 traversal，有的帧只是在 App 主线程做 measure / layout / draw，有的帧会把耗时扩散到 App 主线程、system_server Binder 线程、DisplayThread 和动画线程。两类 trace 长得完全不同。

### App 侧 traversal 与 WMS relayout 的对应关系

| 场景 | 是否跨进程进入 WMS | Perfetto 观察重点 |
|------|------------------|------------------|
| `invalidate()` 触发的纯重绘 | 否 | App 主线程 `performDraw` 与 RenderThread |
| `requestLayout()` 但窗口尺寸未变 | 通常否 | App 主线程 measure / layout / draw |
| 首帧、窗口 resize、需要服务端新 frame/Insets 状态 | 同步或异步 | App relayout 调用，加 system_server Binder / DisplayThread 配套工作 |
| 只改不会影响 frame 同步的窗口属性，且命中 `relayoutAsync()` 条件 | 异步 | App 当前 traversal 不等 `RelayoutResult`；后续 `W.resized()` / Insets 回调再刷新本地状态 |

### scheduleTraversals() 与 performTraversals() 的职责边界

`ViewRootImpl.scheduleTraversals()` 是 App 侧调度入口，不跨进程。它向 Choreographer 投递 `TraversalRunnable`，在下一次 VSync 时触发 `doTraversal()` → `performTraversals()`。WMS 跨进程调用只发生在 `performTraversals()` 内部条件满足时。

下面是从 Android 17 `ViewRootImpl.java` 抽出的等价简化，只保留调度与 relayout 条件：

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
        || viewVisibilityChanged || params != null
        || mForceNextWindowRelayout;

if (relayoutRequested) {
    // 这里才跨进程 → WMS
    relayoutWindow(params, viewVisibility, insetsPending);
}
```

这段代码只抽取调度与 relayout 分支。`requestLayout()` → `scheduleTraversals()` → `performTraversals()` 先在 App 进程内执行；命中前述五类条件后，才从 `performTraversals()` 调用 WMS。

**Perfetto 区分表**：

| Slice 名称 | 进程 | 线程 | 含义 |
|-----------|------|------|------|
| `ViewRootImpl#doTraversal` | App | UI Thread | App 侧 measure/layout/draw 调度 |
| `ViewRootImpl#performTraversals` | App | UI Thread | 完整 measure+layout+draw，内可能嵌套 `relayoutWindow` |
| `relayoutWindow` | system_server | `Binder:*` 入口 | WMS 侧 Window 属性更新；后续可能联动 DisplayThread/AnimationThread |

**时序判读**：

- App 发起：`performTraversals` 内嵌同步或异步 relayout，常见于首次显示、尺寸或 LayoutParams 变化；
- system_server 发起状态变化：WMS 通过 `IWindow.resized()`、Insets/configuration 等 callback 通知客户端，客户端再 schedule traversal；下一次 traversal 是否回调 relayout，仍由上述五类条件决定。

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

切换 App、回到桌面、打开 Recents 和预测返回都属于窗口过渡。现代 Android 不能再按“WMS 创建 Activity animator 后独自驱动动画”来理解。旧兼容路径仍可能出现 `AppTransition`，Android 17 的主线入口是 `TransitionController` / `Transition` 收集 WindowContainer 变化，再由 WM Shell transition、remote transition 或服务端 surface animation 执行动画。

### 动画路径如何分工

Activity 切换、回到桌面、打开 Recents、predictive back——这些过渡几乎都跨 ATMS/WMS、WM Shell、SurfaceFlinger 三层协作：

1. ATMS/WMS 更新 `ActivityRecord`、Task、DisplayContent 等 WindowContainer 状态，并由 `TransitionController` 收集 open / close / change。
2. `Transition` 把参与过渡的窗口、leash、起止 bounds、可见性变化整理成一次 transition。
3. 如果本轮过渡交给 Shell，WM Shell transition handler 或 remote transition 根据 leash 构建动画；Recents、跨 Task、桌面模式和 predictive back 常走这条路径。
4. 服务端动画仍会用到 `SurfaceAnimator` / `SurfaceAnimationRunner` 等组件，把每帧 transform、alpha、crop 写入 `SurfaceControl.Transaction`。
5. SurfaceFlinger 在后续 `commit` / `composite` 中消费这些 transaction，完成合成与 present。

过渡包含两类成本：开始前的 participant collect、draw sync 与 ready；播放期间的 Shell/remote handler、leash transaction 和 SurfaceFlinger composition。120Hz 屏幕的周期约 8.33ms，播放阶段任何一帧迟交 transaction 或迟完成合成，都会错过目标 present。

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
| Android 15-17 | `TransitionController` / Shell transition 是 Activity、Recents、predictive back、桌面模式等场景的主要分析入口 | 先定位 transition id，再看 Shell handler、remote transition、leash transaction 与 SF `commit` / `composite` |

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
- **Android 16**：target 36 应用默认启用 predictive back，`android:enableOnBackInvokedCallback` 默认值改为 `true`；旧 `OnBackPressed` / `KEYCODE_BACK` 调用在该行为下被忽略，同时新增 `finishAndRemoveTaskCallback`、`moveTaskToBackCallback` 等 API。
- **Android 17**：沿用该 transition/Shell 主路径；应用仍需按目标 SDK、manifest 与 AndroidX callback 实际配置判断，不应从系统版本单独推断是否参与预测动画。

它的性能路径跨 Input、ATMS/WMS、Shell transition 和 SurfaceFlinger。手势开始后，Input 侧持续上报 back progress；WMS / Shell 根据返回目标更新当前窗口和目标窗口的 leash；手势完成或取消时，transition 进入 finish 或 cancel。分析卡顿时要同时看 Input 事件节奏、Shell transition handler、system_server transition 状态，以及 SurfaceFlinger 是否在同一时间段出现 transaction 堆积。

[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/predictive-back-gesture]

## 多窗口、折叠屏与 Desktop Mode

Split-screen、freeform、Picture-in-Picture、Activity Embedding 和多 Display 会改变 WindowContainer 树、可见 layer 集合与窗口 bounds。性能压力来自参与本轮变化的对象、同步范围和更新频率，不能只按屏幕上有几个窗口估算。

### 多窗口模式下的 WMS 工作量

多窗口常增加下面几类工作：

- 多个可见 Task/Window 的 bounds、Insets、focus 与 input window snapshot；
- WindowContainerTransaction、transition participant 与 leash；
- resize/configuration callback 和 App 新尺寸 buffer；
- caption、IME、dim、wallpaper、PiP 与 overlay 引起的 composition strategy 变化；
- 同进程多个 ViewRoot 对 UI Looper 与 RenderThread 的竞争。

静止且没有状态变化的可见窗口不一定持续触发 relayout。拖拽分隔线、自由窗口 resize、跨 Display 移动、IME 动画和 transition 才更容易形成高频更新。应记录每轮参与的 WindowContainer、sync id、transaction 和 buffer，不用总窗口数替代证据。

### 折叠屏与大屏配置变更

折叠、展开或跨 Display 移动会改变 display area、window bounds、Insets 与 configuration。App 是否重建 Activity，取决于变化类型、target SDK、compat change、`configChanges` 与 Android 17 的新默认行为。

target 37 应用运行在 `sw >= 600dp` 的大屏时，固定方向、`resizeableActivity` 和 min/max aspect ratio 限制会被忽略；游戏、小于 600dp 的屏幕以及用户显式选择 App 默认比例的情况属于例外。窗口因此更可能经历 resize、旋转和 configuration callback，但 BLAST/SF 主线没有换代。

Android 17 还减少了部分配置变化的 Activity 重建：`CONFIG_KEYBOARD`、`CONFIG_KEYBOARD_HIDDEN`、`CONFIG_NAVIGATION`、`CONFIG_TOUCHSCREEN`、`CONFIG_COLOR_MODE`，以及进入/离开 `UI_MODE_TYPE_DESK` 的 `CONFIG_UI_MODE` 默认改为 `onConfigurationChanged()`。

固定 tag 的 `attrs_manifest.xml` 为 `android:recreateOnConfigChanges` 定义了 `mcc`、`mnc`、`touchscreen`、`keyboard`、`keyboardHidden`、`navigation`、`colorMode`，没有 `uiMode`。因此：

- 对已列出的 flag，App 依赖重建刷新资源时可用 `recreateOnConfigChanges` 显式 opt-in；
- 不要把 `uiMode` 写进该属性；进入/离开 desk mode 应在 `onConfigurationChanged()` 更新依赖配置的资源和组件；
- `recreateOnConfigChanges` 与声明 App 自行处理变化的 `android:configChanges` 方向相反，同一 flag 同时出现在两者时不会重建。

### Android 16 QPR3 Connected Display Desktop

Connected-display desktop windowing 在 Android 16 QPR3 对受支持设备达到 GA。它仍受设备能力、OEM 配置、外接显示器与用户入口约束，不能从 `Build.VERSION` 推断某台设备已经启用。

对 WMS 来说，自由窗口、caption bar Insets、多实例和跨 Display 移动会增加 WindowContainer、WCT、transition 与 resize 工作。App 还要处理不同 Display 的密度、刷新率、color mode、input 与资源。

这类场景里的 Binder 线程只是入口。DisplayThread/AnimationThread、WM Shell transition、App traversal/RenderThread 和每个 Display 的 SF/HWC/present 都需要放到对应时间线上。

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
| Android 16 (API 36) | target 36 默认启用 Predictive Back；大屏 adaptive behavior；QPR3 connected-display desktop 在受支持设备 GA | 返回过渡、caption、外接显示器和自由窗口会增加 transition / resize 路径 | `developer.android.com/about/versions/16/summary` / Android Developers connected-display GA |
| Android 17 (API 37) | target 37 大屏移除 orientation/resizability opt-out；减少 keyboard/navigation/touch/color/desk-mode 等配置变化的 Activity 重建 | resize/configuration 更频繁，但部分外设/desk-mode 变化转为 `onConfigurationChanged()`；需要重建时使用 `recreateOnConfigChanges` | `developer.android.com/about/versions/17/changes/ff-restrictions-ignored` / `developer.android.com/guide/topics/resources/runtime-changes` |

## 常见问题与误区

### 误区 1："WMS 在主线程上运行，所以很慢"

WMS 横跨 system_server 内的 Binder 线程、DisplayThread、UiThread / WindowManagerPolicyThread 和 AnimationThread。常见耗时来自 `mGlobalLock` 竞争、共享窗口状态更新、surface placement 或动画推进。Perfetto 里要同时看 Binder 入口、DisplayThread 的布局摆放、AnimationThread 的过渡推进，以及主线程上是否有策略或 AMS 工作交叉干扰。

### 误区 2："Window 数量越多越卡"

Window 数量会增加状态和内存，但不能单独预测帧耗时。需要关注本轮参与 layout、transition、sync、input snapshot 和 transaction 的可见 Window，以及它们更新的频率。隐藏 Window 仍有服务端状态，通常不会像正在 resize 的 Window 那样持续进入显示关键路径。

### 误区 3："StartingWindow 是 App 画的"

StartingWindow 不是 App 主 Window 的第一帧。现代 Android 的边界是：ATMS/WMS 判断是否需要 starting surface 并发出生命周期请求；Android 12+ 的 SplashScreen / TaskSnapshot starting window 多由 WM Shell starting-surface 组件创建和绘制。App 进程完成主窗口首帧之前，Shell 侧 starting surface 已经挂到 Task 上。

### 误区 4："relayoutWindow 慢一定是 WMS 的问题"

`relayoutWindow` 慢可能是 WMS 自身计算重，也可能是窗口树更新后的连带成本大。常见放大源包括：等待 `mGlobalLock`、`performSurfacePlacement(true)` 处理过多可见窗口、Insets / configuration 返回触发 App 侧 re-measure、surface resize 让 SurfaceFlinger 的 transaction / latch 变重。排查时至少同时看 App 主线程、system_server 多条线程和 SurfaceFlinger。

### 误区 5："Predictive Back 动画延迟是 Input 系统的问题"

Predictive Back 动画涉及 Input、App callback、ATMS/WMS、WM Shell 与 SurfaceFlinger。对系统 back-to-home/cross-task/cross-activity 动画，不能只查 WMS `WindowAnimator`：`TransitionController` / `Transition` 收集窗口状态，Shell 的 `BackAnimationController` 或 transition handler 生成 leash transaction。排查应分四段：Input progress、App/back callback、ATMS/WMS transition、Shell transaction 与 SurfaceFlinger present。

## 扩展

### 🔸 WindowInsets 与布局性能

WMS/InsetsStateController 维护状态栏、导航栏、IME、caption、cutout 等 source，客户端 `InsetsController` 接收 relayout 结果或独立的 Insets callback，再由 `ViewRootImpl` 分发给 View hierarchy。Insets 变化不必每次都通过同步 relayout 返回。

布局成本取决于 App 怎样消费 Insets：

- listener 修改 padding/margin 并调用 `requestLayout()`，会触发 measure/layout；
- IME/系统栏动画若每帧改布局，成本会持续到动画结束；
- View 与 Compose 同时应用相同 Insets，可能出现重复 padding；
- PlatformView、SurfaceView、camera preview 还需要同步内容 crop/transform。

应先确定哪个容器拥有 Insets，再选择 View listener 或 Compose modifier。只有该边界已完整处理且子树不再需要同一 Insets 时才消费；无条件返回 `WindowInsets.CONSUMED` 会让子 View 丢失所需信息。Edge-to-edge 场景还应把 layout 成本与 SurfaceControl/IME 动画分开测量。

### 🔸 WMS 与 Input 系统的协作

Android 17 `InputMonitor.UpdateInputWindows` 在 `mGlobalLock` 下遍历可能接收输入的窗口，填充 `InputWindowHandle`，并用 `SurfaceControl.Transaction.setInputWindowInfo()` 绑定到对应 SurfaceControl。transaction 的 window-info listener 完成后，native 侧更新 InputDispatcher 的窗口 snapshot。

InputDispatcher 处理触摸时使用当前 display 的 window snapshot 做 hit-test，再通过已注册的 InputChannel 投递。它不会为每个触摸事件同步 Binder 调用 WMS 拉取窗口列表。

窗口移动、transition、focus 或 touchable region 变化时，需要对齐：

1. WMS 何时标记并发布新的 input window info；
2. window-info transaction 何时 reported；
3. InputDispatcher 何时切换 focus/target；
4. App input channel 何时收到事件。

“点击没有响应”可能来自旧 snapshot、目标 window 不可触摸、focus request 未完成、App channel backlog 或 App 主线程迟到。focus 切换本身不等于事件必然丢失。§3.1 会继续展开 InputDispatcher 的队列与超时证据。

## 参考资料

- [AOSP WindowManagerService 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java) ，`relayoutWindow()` 和窗口状态管理入口
- [AOSP WindowSurfacePlacer 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowSurfacePlacer.java) ，`performSurfacePlacement(true)` 的主执行点
- [AOSP StartingSurfaceController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java) ，服务端 starting surface 请求入口
- [AOSP WM Shell StartingWindowController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java) ，Shell 侧 `addStartingWindow` / `removeStartingWindow` 入口
- [AOSP TransitionController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/TransitionController.java) ，WindowContainer transition 收集与调度入口
- [AOSP ViewRootImpl 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/ViewRootImpl.java) ，App 侧 traversal、`relayout()` 判定和 `updateBlastSurfaceIfNeeded()`
- [AOSP IWindowSession / Session 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/IWindowSession.aidl) ，同步 `relayout`、oneway `relayoutAsync` 与 `relayout2` 协议
- [AOSP InputMonitor 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/InputMonitor.java) ，`InputWindowHandle` 填充与 transaction 发布
- [AOSP SurfaceControl JNI 路径](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/jni/android_view_SurfaceControl.cpp) ，native `createSurfaceChecked(...)` 入口
- [AOSP BLASTBufferQueue 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/graphics/java/android/graphics/BLASTBufferQueue.java) ，客户端 surface materialization
- [Kernel dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c) / [sync_file](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c) ，窗口 buffer 与显示同步边界
- [Android 官方文档，SplashScreen API](https://developer.android.com/develop/ui/views/launch/splash-screen) ，StartingWindow 与统一启动体验
- [Android 官方文档，Predictive Back](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture) ，返回手势动画与过渡回调
- [Android 16 QPR3 connected-display GA](https://developer.android.com/blog/posts/android-devices-extend-seamlessly-to-connected-displays) ，受支持设备上的 Desktop Windowing
- [Android 官方文档，Android 16 Behavior Changes](https://developer.android.com/about/versions/16/behavior-changes-all) ，大屏自适应与 orientation / resizable 行为变化
- [Android 17 大屏方向与可调整窗口变化](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored) ，target 37 的适用范围与例外
- [Android 17 configuration changes](https://developer.android.com/guide/topics/resources/runtime-changes#android-17) ，减少 Activity recreation 与 `recreateOnConfigChanges`
- [Android 官方文档，WindowInsets](https://developer.android.com/develop/ui/views/layout/window-insets) ，Insets 分发与适配实践

本章的 Display→Window→进程→内容对象分组方式还对照了 `rendering_pipelines/S06_multi_window_type.md`。Writer 系列用于补齐多窗口对象拓扑，Android 17 与 kernel 固定 tag 用于确认当前 relayout、transition、input window 和 fence 边界。
