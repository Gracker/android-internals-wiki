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

App 冷启动、Activity/Task 过渡、IME、旋转、分屏和桌面窗口 resize 都会改变窗口状态。跟踪数据只看 App 主线程或 SurfaceFlinger，会漏掉 system_server 与 WM Shell 之间的状态收集、同步和几何 transaction。

WMS 负责维护 WindowContainer/WindowState 树，并把 Activity/Task 状态转换成窗口 bounds、可见性、层级、Insets、focus、input window info 与 `SurfaceControl` 属性。它不绘制 App 像素，也不执行最终合成。

一次窗口变化可拆成四段排查：

1. App 的 `ViewRootImpl` traversal、relayout IPC 与新 buffer；
2. system_server 的窗口状态、锁、layout/surface placement 与 transition collect；
3. WM Shell 的 starting surface、transition handler 与 leash 动画；
4. SurfaceFlinger/HWC 的 transaction、buffer latch、composition 与 present。

四段里最先偏离目标时间的对象，才是下一步需要继续追的方向。

## WMS 的定位：窗口状态与 Surface 拓扑

从图形架构看，WMS 位于 App、Input 系统和 SurfaceFlinger 之间。它维护 WindowContainer/WindowState 树，决定窗口的层级、可见性、bounds、focus、Insets 和动画状态。SurfaceFlinger 负责把 App 提交的内容合成上屏；WMS 的 `InputMonitor` 则把可触摸区域、层级、focusability 与 input channel token 写入 `InputWindowHandle`，通过 transaction 附着到对应 layer。SurfaceFlinger 提交 layer 状态后，再把窗口快照交给 InputDispatcher。

WMS 运行在 system_server 进程中，但性能问题不能简化成“AMS、IMS、WMS 共用一条主线程”。Android 17 的线程边界需要按调用方式判断：

- `WindowManagerService.main()` 在 `DisplayThread` 上构造 WMS，因此 WMS 的 `mH` 绑定该线程；
- `IWindowSession` 等 Binder 调用先在 `Binder:*` 线程执行。同步 `relayout()` 与 oneway `relayoutAsync()` 最终都进入 `WindowManagerService.relayoutWindow()`；该方法持有 `mGlobalLock` 时直接调用 `performSurfacePlacement(true)`，不会为了 placement 自动切到 DisplayThread；
- WMS 的 `mAnimationHandler` 绑定 `AnimationThread`。`WindowSurfacePlacer.requestTraversal()` 把常规的延后 placement 投递到这个 handler，`WindowAnimator` 的帧推进也使用该线程；
- `initPolicy()` 在 `UiThread` 执行，并把它登记为 `WindowManagerPolicyThread`。

这些线程会围绕 `mGlobalLock` 和共享窗口状态互相等待。看到 `relayoutWindow`、StartingWindow 切换或窗口动画掉帧时，应先确认耗时在哪条线程执行，再判断函数执行、锁等待 policy/animation 侧状态推进各占多少时间。

WMS 与其他主要组件的职责可以这样分：

- **AMS/ATMS**：负责 Activity 和 Task 的生命周期推进；当 Activity 需要显示、隐藏、切换或调整窗口模式时，把窗口侧约束交给 WMS 处理
- **SurfaceFlinger**：负责 layer 创建、transaction 消费和最终合成；WMS 管理窗口容器与 `SurfaceControl` 属性，不直接负责像素合成
- **Input 系统**：WMS 把可见区域、层级、focusability 和 input channel token 写入 layer 的 input info；SurfaceFlinger 从已提交的 layer snapshot 生成 `WindowInfosUpdate`，InputDispatcher 再用这份按 Display 划分的缓存做 hit-test

### 多窗口先按共享域分组

“屏幕上有多个窗口”不能直接说明它们竞争哪条线程或哪份显示资源。应按 Display、进程和 ViewRoot 分组：

| 拓扑关系 | 共享对象 | 各自独立的对象 | 常见瓶颈 |
|---------|---------|---------------|---------|
| 同进程、同一 UI 线程的多个 ViewRoot | UI Looper；`Choreographer.getInstance()` 返回该线程的 ThreadLocal 实例 | 每个 ViewRoot 的 traversal、窗口 Surface 与 BLAST 队列 | 一个窗口的主线程工作挤占其他窗口的 traversal 时段 |
| 同进程的多个硬件加速窗口 | 进程内 `RenderThread::getInstance()` 单例 | 各窗口的渲染目标、buffer 队列和 fence | RenderThread 排队、GPU 上下文与内存带宽竞争 |
| 不同进程、位于同一 Display | SurfaceFlinger 的该 Display layer 集合、HWC/overlay、输出带宽和本轮 present | App UI 线程、进程 RenderThread、窗口 buffer 队列 | 单个慢窗口拖延同步组，或合成资源不足 |
| 位于不同 Display | 设备级 GPU/HWC 资源仍可能共享 | 各 Display 的 layer 集合、时序和 present fence | 只看默认屏会漏掉外接屏的掉帧 |

因此，多窗口 trace 的第一层索引应是 Display，第二层是 Window/ViewRoot，第三层才是进程、UI 线程、RenderThread 和内容 producer。每个 ViewRoot 有自己的 Surface/BLAST 内容通道；同进程只表示部分执行资源共享，多个窗口仍各有自己的 BufferQueue。

## Window 与 Surface 的关系

每个应用窗口在 WMS 侧对应一个 `WindowState`。服务端维护窗口元数据与 `SurfaceControl` 关系，App 侧通过 `Surface` 写像素，SurfaceFlinger 内部维护 layer snapshot 与输出。几个对象的职责不同：

- **WMS 端**：关联或更新窗口 `SurfaceControl`，维护 bounds、crop、alpha、layer、visibility、Insets 等属性
- **App 端**：通过 `ViewRootImpl` 和 `BLASTBufferQueue` 获取可绘制 `Surface`，决定何时调用 `dequeueBuffer`、绘制和 `queueBuffer`
- **SurfaceFlinger 端**：根据 `SurfaceControl.Transaction` 和 buffer latch 结果完成合成

Android 17 同时保留两种 relayout surface 协议：

- service-surface 路径通过同步 `relayout()` 返回 `WindowRelayoutResult` 与 `SurfaceControl`；
- client-surface 路径由 `ViewRootImpl.updateSurfaceControl()` 在客户端创建/复用 `SurfaceControl`，再经 `relayout2()`/`relayoutAsync2()` 传给 WMS。

两条路径最终都要让客户端 render target 与 BLAST backing 对齐。`ViewRootImpl` 根据有效的 `SurfaceControl` 更新 renderer 和 `BLASTBufferQueue`，App 后才通过可绘制 `Surface` dequeue/draw/queue。分析前必须确认 `WindowManager.useClientSurface()` 与相关 feature flag，不能把某一分支写成 Android 17 的唯一实现。

### Surface 创建流程

Activity 首次显示时，可按以下稳定边界理解：

1. App 的 `performTraversals()` 因 `mFirst=true` 进入 relayout；
2. `Session.relayout()` / `relayout2()` 调用 `WindowManagerService.relayoutWindow()`；
3. WMS 更新 `WindowState`、frames、Insets、可见性、sync 与 surface 状态；
4. service-surface 分支返回服务端 SurfaceControl，client-surface 分支使用客户端传入的 control；
5. `ViewRootImpl` 更新 frame/Insets、render target 和 BLAST；
6. App 绘制第一帧并 queue buffer，SurfaceFlinger 才能在后续周期 latch 并显示。

WMS 管窗口容器与 layer 控制关系；App 生成窗口内容；SurfaceFlinger 管 layer 状态消费和合成。Binder 传递控制对象、frame 和同步元数据，不传递已经绘制好的像素。

### SurfaceControl.Transaction 的批量提交

WMS 用 `SurfaceControl.Transaction` 批量提交 layer 属性。一个 Transaction 可以包含位置、buffer size、alpha、crop、reparent 等多个操作，调用 `apply()` 后整体交给 SurfaceFlinger。

```java
// frameworks/base/core/java/android/view/SurfaceControl.java
// 伪代码：Transaction 的典型使用方式
SurfaceControl.Transaction t = new SurfaceControl.Transaction();
t.setPosition(surfaceControl, x, y);
t.setBufferSize(surfaceControl, width, height);
t.setAlpha(surfaceControl, 0.5f);
t.apply(); // 一次性提交给 SurfaceFlinger
```

这段代码展示属性批处理，不表 buffer 内容已完成或 panel 已显示。`Transaction.apply()` 的常规路径经 JNI 进入 native `SurfaceComposerClient::apply()`，再通过 Binder 交给 SurfaceFlinger；调用通常不等待本次合成上屏。同步场景要单独检查 `apply(true)`、BLAST sync、transaction committed/completed listener 与 present fence。首帧耗时还要拆到 layer 创建、relayout、buffer 分配和 fence。

### 三类 transaction 的职责不同

窗口 resize 或 transition 中经常同时出现三类 transaction：

| 类型 | 表达的内容 | 典型持有者 |
|------|-----------|-----------|
| `WindowContainerTransaction`（WCT） | Task、Activity、DisplayArea 等 WindowContainer 的 bounds、窗口模式和层级操作 | WM Shell、ATMS/WMS organizer 路径 |
| `SurfaceControl.Transaction` | layer 的位置、crop、alpha、变换、reparent、visibility 和 input info | WMS、WM Shell、App 或其他系统组件 |
| BLAST buffer transaction | 新内容 buffer 及 acquire fence，与目标 layer 的内容更新配套 | App producer、BLASTBufferQueue、SurfaceFlinger |

WCT 是“窗口容器要变成什么状态”的管理请求，处理后可能引发一个或多个 SurfaceControl transaction；它不属于 SurfaceFlinger 的几何 transaction。几何与内容分属两路输入：resize 时可以短暂出现新 geometry 配旧 buffer，或新 buffer 已到但同步组尚未放行 geometry。遇到拉伸、黑边或一帧错位，需要分别核对 container 状态、layer geometry、buffer 尺寸和 fence，笼统搜索“transaction”无法确定问题位置。

## StartingWindow 与启动性能

冷启动期间，进程创建、Runtime/Application/Activity 初始化和首帧绘制尚未完成。StartingWindow 在这段空档提供可见内容，避免用户只看到桌面、空白或旧画面。

### StartingWindow 的工作原理

Android 12 之后，StartingWindow 的决策与实际创建分在两侧。ATMS/WMS 负责判断本次 Activity 启动是否需要 starting surface，`StartingSurfaceController` 根据 SplashScreen 或 TaskSnapshot 路径生成 starting data；WM Shell 的 starting-surface 组件负责创建 SplashScreen/TaskSnapshot 窗口并挂到对应 Task 上。常用源码锚点包括：

- `frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java`：服务端发起 starting surface 请求
- `frameworks/base/services/core/java/com/android/server/wm/SplashScreenStartingData.java`：保存 SplashScreen starting data
- `frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java`：Shell 侧接收 `TaskOrganizer.addStartingWindow` 回调
- `StartingSurfaceDrawer.java`/`SplashscreenWindowCreator.java`：Shell 侧创建并绘制 SplashScreen window

冷启动路径可以按这组边界读：

1. ATMS 推进 Activity 启动，WMS 在 `ActivityRecord`/Task 可见性变化中判断是否需要 starting surface。
2. `StartingSurfaceController` 生成请求，SplashScreen 路径使用 `SplashScreenStartingData`，历史任务恢复路径可能使用 TaskSnapshot starting data。
3. Android 12+ 的 Shell starting-surface 组件收到 `addStartingWindow` 回调后，在 Shell/SystemUI 侧创建 SplashScreen 或 TaskSnapshot 窗口。
4. App 进程启动并绘制主 Window 第一帧。
5. App 通过 `finishDrawing`/`reportDrawFinished` 让服务端知道主窗口已完成首帧，随后走 `removeStartingWindow` 路径通知 Shell 移除 starting surface。

Perfetto 里要把三段分开看：system_server 侧是 starting data、Activity/Task 状态和移除请求；Shell/SystemUI 侧负责启动 surface 的创建与绘制；App 侧的 `reportDrawFinished` 标记主 Window 首帧完成。把 starting surface 的绘制职责放在 system_server，会混淆服务端、Shell 和 App 进程边界。

### Android 12 SplashScreen API

在 Android 12 之前，StartingWindow 的外观主要由 `windowBackground` 决定，OEM 定制差异较大。Android 12 引入 SplashScreen API（`android.window.SplashScreen`），把启动页主题、icon、背景色、退出动画等配置收敛到统一接口：

- 开发者通过 `Theme.SplashScreen` 配置 icon、背景色、动画等元素。
- 退出动画通过 `setOnExitAnimationListener` 接入，移除时机仍要和主 Window 首帧完成信号配合。
- `androidx.core:core-splashscreen` 向后支持 Android 5.0+，但 Android 12+ 的系统 starting surface 创建仍落在 Shell starting-surface 路径。

这套 API 的性能价值在于减少 App 自建 SplashActivity。自建启动页会多一次 Activity 启动、窗口切换和可能的 relayout；系统 SplashScreen 则复用 starting surface 生命周期，不增加 App 侧 Activity 数量。

### StartingWindow 的时机陷阱

StartingWindow 的移除时机会影响启动体感：

- **过早移除**：App 主 Window 第一帧还没准备好时移除 starting surface，用户可能看到短暂闪白或闪黑。
- **过晚移除**：主 Window 已经完成首帧，starting surface 仍停留在前台，用户会把这段时间感知为启动变慢。

主 Window 首帧完成后，服务端才具备移除 StartingWindow 的内容条件。服务端通过 `finishDrawing`/`reportDrawFinished` 收到信号，再走 `removeStartingWindow` 路径让 Shell 移除 starting surface。分析启动 Trace 时，`reportDrawFinished` 只说明 App 首帧完成；视觉切换还要看 Shell 移除、SurfaceFlinger 消费 transaction 和后续 present。

## relayoutWindow：重新协商窗口契约

`relayoutWindow()` 重新协商窗口属性、frame、Insets、surface 与同步序列。它可能嵌在 App traversal 的同步 Binder 调用里，也可能由 oneway `relayoutAsync()` 送到 system_server。两种调用都需要 WMS 处理，差别在于客户端是否等待返回结果。

### 什么触发 relayoutWindow

`ViewRootImpl.performTraversals()` 不会每帧跨进程调用 WMS。Android 17 `ViewRootImpl.java` 的直接条件有五类：

- **`mFirst`**：窗口首次显示，必须向 WMS 申请初始 `SurfaceControl`、frames 和 Insets
- **`windowShouldResize`**：`requestLayout()` 后测量结果改变了窗口尺寸，常见于旋转、多窗口 resize、Dialog `WRAP_CONTENT` 长大
- **`viewVisibilityChanged`**：窗口从隐藏到显示、从显示到隐藏，或 `mNewSurfaceNeeded=true`
- **`params != null`**：`setLayoutParams()`、system UI visibility、keepScreenOn 等窗口属性变化
- **`mForceNextWindowRelayout`**：WMS 通过 `resized()`/配置变化回调强制下一次 traversal 重新 relayout

Insets 变化会先走 `mApplyInsetsRequested`、`dispatchApplyInsets()`，并可能引起 measure/layout、窗口属性变化或强制 relayout，但 `insetsChanged` 不是 Android 17 这段 `if` 的独立布尔条件。`invalidate()` 的纯 draw 不会因此进入 WMS；`requestLayout()` 也只有在上述条件成立时才跨进程。

Android 14+ 增加了 `relayoutAsync()`。Android 17 的 `canRelayoutAsync()` 会检查 starting window、待处理 sync/seq、AM/WMS `WindowConfiguration` 差异等条件；随后客户端用本地 `InsetsState` 和 `WindowConfiguration` 计算 frame。若位置和尺寸同时变化、需要取得新的 sync seq，就回到同步 relayout。启用 fluid-resize/client-surface 相关 flag 后，分支还会不同，核对时必须以目标 build 的 feature flags 为准。

服务端实现很薄：`Session.relayoutAsync()`/`relayoutAsync2()` 复用 `relayout(...)`，只把 `outRelayoutResult` 设为 `null`，随后仍进入 `WindowManagerService.relayoutWindow()`。Trace 上的区别是 App UI 线程不等待 frames、Insets、SurfaceControl 和 sync seq 返回；system_server 仍要处理属性变化、`mGlobalLock` 与后续 placement。分析时要把当前 traversal 和之后的 `IWindow.resized()`/Insets / Insets callback 放在同一段时间线里。

### relayoutWindow 内部流程

WMS 侧的执行过程不能简化成“`relayoutWindow()` 直接调 `performLayout()`”。现代实现更接近下面这条路径：

1. App 侧 `performTraversals()` 判断本轮是否需要同步 relayout，随后通过 Binder 进入 `WindowManagerService.relayoutWindow()`
2. WMS 在 `mGlobalLock` 保护下更新 `WindowState`、可见性、布局参数、Insets 请求和 surface 生命周期状态
3. `relayoutWindow()` 会在当前 Binder 线程内直接调用 `mWindowPlacerLocked.performSurfacePlacement(true)`；同步与 oneway 异步 relayout 都经过这里，其他状态变化可由 `requestTraversal()` 把常规 placement 投到 AnimationThread
4. 同步路径返回 `ClientWindowFrames`、`MergedConfiguration`、`InsetsState`、`InsetsSourceControl` 与 sync 序列；SurfaceControl 由 service-surface 返回或 client-surface 传入
5. App 侧收到同步结果后继续 post-relayout 的 measure/layout/draw；异步路径则等待后续 resize/Insets/configuration callback 更新本地状态

同样是 traversal，有的帧只在 App 主线程执行 measure/ layout / draw；有的帧会发起 system_server Binder 线程上的 relayout 和强制 placement，其中同步调用会嵌套在 App UI 线程等待区间内；另一些窗口状态更新则由 DisplayThread 的 WMS handler 或 AnimationThread 的常规 placement 继续处理。判断线程要看调用栈和 runnable 来源，不能从函数名推断。

### App 侧 traversal 与 WMS relayout 的对应关系

| 场景 | 是否跨进程进入 WMS | Perfetto 观察重点 |
|------|------------------|------------------|
| `invalidate()` 触发的纯重绘 | 否 | App 主线程 `performDraw` 与 RenderThread |
| `requestLayout()` 但窗口尺寸未变 | 通常否 | App 主线程 measure/ layout / draw |
| 首帧、窗口 resize、需要服务端新 frame/Insets 状态 | 同步或异步 | App relayout 调用、system_server Binder 执行；两种服务端路径都可能直接强制 placement |
| 只改不会影响 frame 同步的窗口属性，且命中 `relayoutAsync()` 条件 | 异步 | App 当前 traversal 不等 `RelayoutResult`；后续 `W.resized()`/Insets 回调再刷新本地状态 |

### scheduleTraversals() 与 performTraversals() 的职责边界

`ViewRootImpl.scheduleTraversals()` 是 App 侧调度入口，不跨进程。它向 Choreographer 投递 `TraversalRunnable`，在下一次 VSync 时触发 `doTraversal()` → `performTraversals()`。WMS 跨进程调用只发生在 `performTraversals()` 内部条件满足时。

以下代码从 Android 17 `ViewRootImpl.java` 抽取等价逻辑，只保留调度与 relayout 条件：

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
| `ViewRootImpl#performTraversals` | App | UI Thread | 完整 measure+layout+draw，内部可能嵌套 `relayoutWindow` |
| `relayoutWindow` | system_server | `Binder:*` 入口 | WMS 侧 Window 属性更新；同步/oneway 异步入口都可在当前线程内执行强制 placement |

**时序判读**：

- App 发起：`performTraversals` 内嵌同步或异步 relayout，常见于首次显示、尺寸或 LayoutParams 变化；
- system_server 发起状态变化：WMS 通过 `IWindow.resized()`、Insets/configuration 等 callback 通知客户端，客户端再 schedule traversal；下一次 traversal 是否回调 relayout，仍由上述五类条件决定。

### 在 Perfetto 中的表现

查看 WMS 相关 trace，应确认 capture 配置是否打开 `wm`、`view`、`am`、`input`、`gfx`、`surfaceflinger` 这些类别。没有这些类别时，system_server 侧只会留下零散 Binder slice，很难还原 relayout 路径。

切片名也不能写死。`wm.relayout_window`、`SurfaceControl.Transaction.apply`、`animator`、`reportDrawFinished` 都可能因 Android 版本、atrace category、Perfetto config 和 OEM 定制而变化。应先枚举实际 trace 中出现的 slice 名，再写针对性 SQL。

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
- system_server 里卡在 Binder 执行、等 `mGlobalLock`，还是等 animation / policy 相关线程
- 返回 App 之后，额外成本落在 re-measure、Insets 分发，还是首帧 draw

## Window 动画与过渡性能

切换 App、回到桌面、打开 Recents 和预测返回都属于窗口过渡。现代 Android 已由多个组件共同驱动动画。旧兼容路径仍可能出现 `AppTransition`，Android 17 的主线入口是 `TransitionController`/`Transition` 收集 WindowContainer 变化，再由 WM Shell transition、remote transition 或服务端 surface animation 执行。

### 动画路径如何分工

Activity 切换、回到桌面、打开最近任务和预测返回几乎都需要 ATMS/WMS、WM Shell、SurfaceFlinger 三层协作：

1. ATMS/WMS 更新 `ActivityRecord`、Task、DisplayContent 等 WindowContainer 状态，并由 `TransitionController` 收集 open / close / change。
2. `Transition` 把参与过渡的窗口、leash、起止 bounds、可见性变化整理成一次 transition。
3. 如果本轮过渡交给 Shell，WM Shell transition handler 或 remote transition 根据 leash 构建动画；Recents、跨 Task、桌面模式和 predictive back 常走这条路径。
4. 服务端动画仍会用到 `SurfaceAnimator`/`SurfaceAnimationRunner` 等组件，把每帧 transform、alpha、crop 写入 `SurfaceControl.Transaction`。
5. SurfaceFlinger 在后续 `commit`/`composite` 中消费这些 transaction，完成合成与 present。

过渡包含两类成本：开始前的 participant collect、draw sync 与 ready；播放期间的 Shell/remote handler、leash transaction 和 SurfaceFlinger composition。120 Hz 屏幕的周期约 8.33 ms，播放阶段任何一帧迟交 transaction 或迟完成合成，都会错过目标 present。

这里还要区分两个名字相近的同步机制：

- system_server 内部的 `BLASTSyncEngine` 收集参与变化的 WindowContainer，等待需要重绘的窗口通过 `finishDrawing` 交付内容，再把各子树的 pending transaction 合并给 `TransactionReadyListener`。窗口 transition、旋转和同步 resize 常从这里追；
- API 34 引入的公开 `SurfaceSyncGroup` 面向 `AttachedSurfaceControl`、`SurfaceView`、`SurfaceControlViewHost` 等 surface，可跨组件甚至跨进程等待多个 surface ready 后一起应用 transaction。

两者都在解决“多个 surface 何时一起可见”，但调用方和对象层级不同。Trace ID 时，应确认它属于 WMS 的 WindowContainer 同步还是 App/组件侧的 `SurfaceSyncGroup`，再查超时和缺帧参与者。

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
| Android 12—14 | legacy `AppTransition` 仍覆盖一部分路径，`TransitionController` 和 Shell transition 逐步接管 Task/Activity 级过渡 | 同时看 `wm`、`transition`、`android.anim*`、Shell 进程和 SurfaceFlinger transaction |
| Android 15—17 | `TransitionController`/Shell / Shell transition 是 Activity、Recents、predictive back、桌面模式等场景的主要分析入口 | 先定位 transition id，再看 Shell handler、remote transition、leash transaction 与 SF `commit`/`composite` |

一次 Activity 切换里，旧 Activity 和新 Activity 的 Window 往往会被包到 leash surface 下。动画过程更新 transform、alpha、crop 和 layer，App 不需要每帧重绘 Activity 内容。App 侧首帧准备慢、Shell 动画线程慢、system_server transition 状态收集慢或 SurfaceFlinger 合成慢，都会表现成切换掉帧，但根因落点不同。

Perfetto 里不能只看 `android.anim`。如果掉帧发生在 Activity open/ close 期间，应按这个顺序拆：

1. App 主线程和 RenderThread 是否按时提交首帧。
2. system_server 里 transition collect / ready / finish 是否被锁等待或 Binder 调用拖长。
3. Shell/SystemUI 进程里的 transition handler 是否每帧稳定产出 transaction。
4. SurfaceFlinger 的 `commit`、`composite` / present 是否及时消化这些 transaction。

### Predictive Back 动画

Predictive Back 的版本线要拆开读：

- **Android 13**：引入 `OnBackInvokedCallback` 和预测返回早期能力，系统动画可通过开发者选项测试。
- **Android 14**：完善跨 Activity、跨 Task 和自定义过渡接入，开发者仍经常通过开发者选项验证 predictive back animation。
- **Android 15**：开发者选项不再是系统动画显示前提；对已经 opt-in 的应用或 Activity，back-to-home、cross-task、cross-activity 等系统动画会按系统策略显示。未 opt-in 的应用仍按传统返回行为处理。
- **Android 16**：target 36 36 的应用默认启用 predictive back，`android:enableOnBackInvokedCallback` 默认值改为 `true`；旧 `OnBackPressed`/`KEYCODE_BACK` 调用在该行为下被忽略，同时新增 `finishAndRemoveTaskCallback`、`moveTaskToBackCallback` 等 API。
- **Android 17**：沿用该 transition/Shell 主路径；应用仍需按目标 SDK、manifest 与 AndroidX callback 实际配置判断，不能从系统版本单独推断是否参与预测动画。

它的性能路径跨 Input、ATMS/WMS、Shell transition 和 SurfaceFlinger。手势开始后，Input 侧持续上报 back progress；WMS/Shell 根据返回目标更新当前窗口和目标窗口的 leash；手势完成或取消时，transition 进入 finish 或 cancel。分析卡顿时要同时看 Input 事件节奏、Shell transition handler、system_server transition 状态，以及 SurfaceFlinger 是否在同一时间段出现 transaction 堆积。

## 多窗口、折叠屏与 Desktop Mode

Split-screen、freeform、Picture-in-Picture、Activity Embedding 和多 Display 会改变 WindowContainer 树、可见 layer 集合与窗口 bounds。性能压力来自参与本轮变化的对象、同步范围和更新频率，不能只按屏幕上有几个窗口估算。

### 多窗口模式下的 WMS 工作量

多窗口常增加下面几类工作：

- 多个可见 Task/Window 的 bounds、Insets、focus 与 input window snapshot；
- WindowContainerTransaction、transition participant 与 leash；
- resize/configuration callback 和 App 新尺寸 buffer；
- caption、IME、dim、wallpaper、PiP 与 overlay 引起的 composition strategy 变化；
- 同进程多个 ViewRoot 对 UI Looper 与 RenderThread 的竞争。

静止且没有状态变化的可见窗口不一定持续触发 relayout。拖拽分隔线、调整自由窗口 resize、跨 Display 移动、IME 动画和 transition 更容易形成高频更新。应记录每轮参与的 WindowContainer、sync id、transaction 和 buffer，不用总窗口数替代证据。

排查时按下面的对象顺序取证：

1. **Display**：确认物理/逻辑 Display、刷新周期、layer 集合和本轮 present fence；
2. **Window**：找发生 bounds、Insets、visibility、focus 或 layer 变化的 WindowState/ViewRoot；
3. **执行资源**：确认它属于哪个进程、UI 线程和 RenderThread，是否与其他窗口共享；
4. **内容通道**：检查该窗口自己的 BLAST 队列、buffer 尺寸、acquire fence 和 latch；
5. **合成结果**：回到该 Display 的 SurfaceFlinger composition 与 HWC present。

同一 Display 的不同进程拥有独立的 App 执行链，但最终仍在该 Display 的同一轮合成和 present 汇合。不同 Display 要分别核对 present fence；默认屏正常不能证明外接屏也按时显示。

### 折叠屏与大屏配置变更

折叠、展开或跨 Display 移动会改变 display area、window bounds、Insets 与 configuration。App 是否重建 Activity，取决于变化类型、target SDK、compat change、`configChanges` 与 Android 17 的新默认行为。

target 37 的应用运行在 `sw >= 600dp` 的大屏时，固定方向、`resizeableActivity` 和 min/max aspect ratio 限制会被忽略；游戏、小于 600 dp 的屏幕以及用户显式选择 App 默认比例的情况属于例外。窗口因此更可能经历 resize、旋转和 configuration callback，但 BLAST/SF 主线没有换代。

Android 17 还减少了部分配置变化的 Activity 重建：`CONFIG_KEYBOARD`、`CONFIG_KEYBOARD_HIDDEN`、`CONFIG_NAVIGATION`、`CONFIG_TOUCHSCREEN`、`CONFIG_COLOR_MODE`，以及进入/离开 `UI_MODE_TYPE_DESK` 的 `CONFIG_UI_MODE` 默认改为 `onConfigurationChanged()`。

固定 tag 的 `attrs_manifest.xml` 为 `android:recreateOnConfigChanges` 定义了 `mcc`、`mnc`、`touchscreen`、`keyboard`、`keyboardHidden`、`navigation`、`colorMode`，没有 `uiMode`。因此：

- 对已列出的 flag，App 依赖重建刷新资源时可用 `recreateOnConfigChanges` 显式 opt-in；
- 不要把 `uiMode` 写进该属性；进入/离开 desk mode 应在 `onConfigurationChanged()` 更新依赖配置的资源和组件；
- `recreateOnConfigChanges` 与声明 App 自行处理变化的 `android:configChanges` 方向相反，同一 flag 同时出现在两者时不会重建。

### Android 16 QPR3 Connected Display Desktop

Connected-display desktop windowing 在 Android 16 QPR3 对受支持设备正式可用。它仍受设备能力、OEM 配置、外接显示器与用户入口约束，不能从 `Build.VERSION` 推断某台设备已经启用。

对 WMS 来说，自由窗口、caption bar Insets、多实例和跨 Display 移动会增加 WindowContainer、WCT、transition 与 resize 工作。App 还要处理不同 Display 的密度、刷新率、color mode、input 与资源。

这类场景里的 Binder 线程只是入口。还要分别检查 DisplayThread 上的 WMS handler 工作、AnimationThread 上的常规 surface placement/动画、WM Shell transition、App traversal/RenderThread，以及每个 Display 的 SF/HWC/present。

## 在 Perfetto 中的综合表现

在 Perfetto 中分析 WMS 时，应先按线程和阶段分组，再识别 slice 名。

### 先看哪些线程

| 线程 / 进程 | 常见职责 | 观察意义 |
|-----------|---------|---------|
| system_server `Binder:*` | `relayoutWindow`、visibility、window transaction 入口；relayout 可直接执行强制 placement | 看 IPC、`mGlobalLock` 等待和 `performSurfacePlacement(true)` 调用栈 |
| system_server DisplayThread | WMS `mH` 消息与 display 服务工作 | 看 display 变更和 WMS handler 队列，不要默认把所有 placement 归到这里 |
| system_server `android.anim*`/AnimationThread | `requestTraversal()` 投递的常规 placement、WindowAnimator 和 surface animation | 看 placement/动画任务是否过期或被锁阻塞 |
| system_server UiThread/WindowManagerPolicyThread | policy 初始化与策略回调 | 只在调用栈涉及 policy 时纳入关键路径 |
| App 主线程 | `performTraversals`、resize callback、首帧 draw | 看 traversal 是否因 relayout 变重 |
| RenderThread | `syncAndDrawFrame` | 区分 WMS 问题和渲染问题 |
| SurfaceFlinger | transaction apply、latch、composition | 看 buffer/ transaction 是否在合成侧堆积 |

### 先枚举 slice，再做专项查询

`wm.pause_timeout`、`wm.relayout_window`、`SurfaceControl.Transaction.apply` 并非所有版本都有。查询顺序如下：

1. 枚举 system_server、App、SurfaceFlinger 中实际出现的 `relayout`、`window`、`surface`、`anim`、`draw` 相关 slice
2. 再按线程聚类，确认这一帧落在哪个进程和哪条线程
3. 只对当前 trace 里存在的 slice 名写 SQL

### 典型分析场景

**场景 1：冷启动**

1. 在 App 主线程确认首帧 `performTraversals` 是否命中 `mFirst`
2. 在 system_server Binder 线程找首次 relayout 及其内嵌的强制 placement；另查 AnimationThread 是否还有延后 placement
3. 回看 App 的首帧 draw 完成点，再确认 StartingWindow 退出时机

**场景 2：多窗口切换掉帧**

1. 从掉帧帧号回看 App 主线程和 RenderThread
2. 查看 system_server 的 Binder 线程、AnimationThread 和 DisplayThread，按调用栈区分强制 placement、常规 placement 与 handler 工作
3. 如果同时出现窗口 resize 或 Insets 变化，再把 relayout 和 animation 拆开计时

**场景 3：旋转或桌面模式 resize 卡顿**

1. 确认窗口边界变化是否触发同步 relayout
2. 查看 `performSurfacePlacement(true)` 之后的额外成本落在 frames/Insets 返回还是 App 侧 re-measure
3. 结合 SurfaceFlinger 的 transaction/ latch 情况，判断 buffer resize 是否放大合成侧成本

## 与其他机制的关系

WMS 的性能表现同时受多个上下游影响：

- **§2.1 渲染架构全景**：WMS 连接 App 绘制与 SurfaceFlinger 合成
- **§2.6 SurfaceFlinger 与合成**：WMS 通过 SurfaceControl.Transaction 与 SurfaceFlinger 交互，事务执行时机影响合成效率
- **§2.13 图形缓冲区管理**：Surface 的创建涉及 BufferQueue 分配，BufferQueue 的 producer/consumer 模型决定 App 与 SurfaceFlinger 的协作方式
- **§3.1 Input 事件分发**：WMS 维护的 Window Z-order 和焦点信息是 InputDispatcher 进行 hit-test 的基础
- **§8.2 启动速度分析**：StartingWindow 的创建和移除时机直接影响启动体感
- **§8.4 其他响应速度场景**：旋转屏幕、多窗口切换等场景中 WMS 的 relayout 是性能关键路径

## 版本演进

下表只保留对当前 WMS 调试口径影响最大的版本阶段。

| 版本 | 变化 | 性能影响 | 参考锚点 |
|------|------|---------|---------|
| Android 12 (API 31) | SplashScreen API 统一 StartingWindow | 启动反馈路径更标准，但 Android 12+ 的 SplashScreen/TaskSnapshot / TaskSnapshot starting window 创建与绘制主要落在 WM Shell starting-surface 路径 | `developer.android.com/develop/ui/views/launch/splash-screen` |
| Android 13 (API 33) | `OnBackInvokedCallback` 与 Predictive Back 早期能力 | 应用可接入新的 back callback；系统预测返回动画多处仍需要开发者选项辅助测试 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture` |
| Android 14 (API 34) | Predictive Back 跨 Activity/自定义过渡能力继续完善 | 返回手势进入实时预览，Input、WMS transition 与 Shell transition 需要放在同一段时间轴内分析 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture` |
| Android 15 (API 35) | Predictive Back 系统动画不再依赖开发者选项；Edge-to-Edge enforcement 扩大 | 已 opt-in 的应用/Activity 会显示 back-to-home、cross-task、cross-activity 等系统动画；Insets 分发也更常见 | `developer.android.com/guide/navigation/custom-back/predictive-back-gesture`/`developer.android.com/about/versions/15/behavior-changes-15` |
| Android 16 (API 36) | target 36 默认启用 Predictive Back；大屏 adaptive behavior；QPR3 connected-display desktop 在受支持设备 GA | 返回过渡、caption、外接显示器和自由窗口会增加 transition/ resize 路径 | `developer.android.com/about/versions/16/summary`/Android Developers / Android Developers connected-display GA |
| Android 17 (API 37) | target 37 大屏移除 orientation/resizability opt-out；减少 keyboard/navigation/touch/color/desk-mode 等配置变化的 Activity 重建 | resize/configuration 更频繁，但部分外设/desk-mode 变化转为 `onConfigurationChanged()`；需要重建时使用 `recreateOnConfigChanges` | `developer.android.com/about/versions/17/changes/ff-restrictions-ignored`/`developer.android.com/guide/topics/resources/runtime-changes` |

## 常见问题与误区

### 误区 1："WMS 在主线程上运行，所以很慢"

WMS 横跨 system_server 内的 Binder 线程、DisplayThread、UiThread/WindowManagerPolicyThread 和 AnimationThread。常见耗时来自 `mGlobalLock` 竞争、共享窗口状态更新、surface placement 或动画推进。Perfetto 里要按调用方式归属：`relayoutWindow()` 直接执行的强制 placement 在 Binder 线程，`requestTraversal()` 调度的常规 placement 在 AnimationThread，WMS `mH` 消息在 DisplayThread，policy 工作在 UiThread。函数属于 WMS，不表示它固定运行在某条“WMS 线程”。

### 误区 2："Window 数量越多越卡"

Window 数量会增加状态和内存，但不能单独预测帧耗时。需要关注本轮参与 layout、transition、sync、input snapshot 和 transaction 的可见 Window，以及它们更新的频率。隐藏 Window 仍有服务端状态，通常不会像正在 resize 的 Window 那样持续进入显示关键路径。

### 误区 3："StartingWindow 是 App 画的"

StartingWindow 独立于 App 主 Window 第一帧。ATMS/WMS 判断是否需要 starting surface 并发出生命周期请求；Android 12+ 的 SplashScreen/TaskSnapshot / TaskSnapshot starting window 多由 WM Shell starting-surface 组件创建和绘制。App 进程完成主 Window 首帧之前，Shell 侧 starting surface 已经挂到 Task 上。

### 误区 4："relayoutWindow 慢一定是 WMS 的问题"

`relayoutWindow` 慢可能来自 WMS 自身计算，也可能来自窗口树更新后的连带成本。常见放大源包括：等待 `mGlobalLock`、`performSurfacePlacement(true)` 处理过多可见窗口、Insets / configuration 返回触发 App 侧 re-measure、surface resize 让 SurfaceFlinger 的 transaction/ latch 变重。排查时至少同时看 App 主线程、system_server 多条线程和 SurfaceFlinger。

### 误区 5："Predictive Back 动画延迟是 Input 系统的问题"

Predictive Back 动画涉及 Input、App callback、ATMS/WMS、WM Shell 与 SurfaceFlinger。对系统返回桌面、跨 back-to-home/cross-task/cross-activity 动画，不能只查 WMS `WindowAnimator`：`TransitionController`/`Transition` 收集窗口状态，Shell 的 `BackAnimationController` 或 transition handler 生成 leash transaction。排查应分四段：Input progress、App/back callback、ATMS/WMS transition、Shell transaction 与 SurfaceFlinger present。

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

Android 17 `InputMonitor.UpdateInputWindows` 使用 WMS 的 `mAnimationHandler`，在 `mGlobalLock` 下按从上到下的窗口顺序填充 `InputWindowHandle`，再通过 `SurfaceControl.Transaction.setInputWindowInfo()` 把变化绑定到对应 SurfaceControl。非立即路径会把这批 input transaction 合并进 `DisplayContent` 的 pending transaction，并调度下一轮 animation/placement。

SurfaceFlinger 消费 transaction 后，从已经提交的 layer snapshot 构造 `WindowInfo` 和 `DisplayInfo`。`updateInputFlinger()` 把 `WindowInfosUpdate` 交给 window-info listeners；InputDispatcher 的 `onWindowInfosChanged()` 随即按 Display 拆分窗口列表，调用 `setInputWindowsLocked()` 替换缓存并唤醒 poll loop。`onWindowInfosReported()` 一类 callback 表示监听器已经处理完这次更新，用于完成通知；InputDispatcher 更新窗口缓存时不需要等待该回调。

InputDispatcher 处理触摸时使用当前 display 的 window snapshot 做 hit-test，再通过已注册的 InputChannel 投递。它不会为每个触摸事件同步调用 WMS 拉取窗口列表。

窗口移动、transition、focus 或 touchable region 变化时，需要对齐：

1. WMS 何时标记并发布新的 input window info；
2. SurfaceFlinger 在哪次 transaction 提交后生成新的 layer/window snapshot；
3. InputDispatcher 何时收到 `WindowInfosUpdate`、替换窗口缓存并处理 focus request；
4. window-info listeners 何时 reported；
5. App input channel 何时收到事件。

“点击没有响应”可能来自旧 snapshot、目标 window 不可触摸、focus request 未完成、App channel backlog 或 App 主线程迟到。focus 切换本身不表示事件必然丢失。§3.1 会继续展开 InputDispatcher 的队列与超时证据。

## 参考资料

- [AOSP WindowManagerService 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java) ，`relayoutWindow()` 和窗口状态管理入口
- [AOSP WindowSurfacePlacer 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/WindowSurfacePlacer.java) ，`performSurfacePlacement(true)` 的主执行点
- [AOSP StartingSurfaceController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java) ，服务端 starting surface 请求入口
- [AOSP WM Shell StartingWindowController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java) ，Shell 侧 `addStartingWindow` / `removeStartingWindow` 入口
- [AOSP TransitionController 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/services/core/java/com/android/server/wm/TransitionController.java) ，WindowContainer transition 收集与调度入口
- [AOSP ViewRootImpl 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/view/ViewRootImpl.java) ，App 侧 traversal、`relayout()` 判定和 `updateBlastSurfaceIfNeeded()`
- [AOSP IWindowSession / Session 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/IWindowSession.aidl) ，同步 `relayout`、oneway `relayoutAsync` 与 `relayout2` 协议
- [AOSP InputMonitor 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/InputMonitor.java) ，`InputWindowHandle` 填充与 transaction 发布
- [AOSP SurfaceFlinger 输入窗口发布](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp) ，`updateInputFlinger()` 从 layer snapshot 生成 `WindowInfosUpdate`
- [AOSP InputDispatcher 源码](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp) ，`onWindowInfosChanged()` 更新按 Display 划分的窗口缓存
- [AOSP BLASTSyncEngine 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java)/[SurfaceSyncGroup 源码](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/window/SurfaceSyncGroup.java) ，服务端 WindowContainer 同步与公开 surface 同步 API 的边界
- [Android API reference，SurfaceSyncGroup](https://developer.android.com/reference/android/window/SurfaceSyncGroup) ，API 34 起公开的跨 surface 同步接口
- [AOSP SurfaceControl JNI 路径](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/jni/android_view_SurfaceControl.cpp) ，native `createSurfaceChecked(...)` 入口
- [AOSP BLASTBufferQueue 源码](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/graphics/java/android/graphics/BLASTBufferQueue.java) ，客户端 surface materialization
- [Kernel dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)/[sync_file](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c) ，窗口 buffer 与显示同步边界
- [Android 官方文档，SplashScreen API](https://developer.android.com/develop/ui/views/launch/splash-screen) ，StartingWindow 与统一启动体验
- [Android 官方文档，Predictive Back](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture) ，返回手势动画与过渡回调
- [Android 16 QPR3 connected-display GA](https://developer.android.com/blog/posts/android-devices-extend-seamlessly-to-connected-displays) ，受支持设备上的 Desktop Windowing
- [Android 官方文档，Android 16 Behavior Changes](https://developer.android.com/about/versions/16/behavior-changes-all) ，大屏自适应与 orientation / resizable 行为变化
- [Android 17 大屏方向与可调整窗口变化](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored) ，target 37 的适用范围与例外
- [Android 17 configuration changes](https://developer.android.com/guide/topics/resources/runtime-changes#android-17) ，减少 Activity recreation 与 `recreateOnConfigChanges`
- [Android 官方文档，WindowInsets](https://developer.android.com/develop/ui/views/layout/window-insets) ，Insets 分发与适配实践
