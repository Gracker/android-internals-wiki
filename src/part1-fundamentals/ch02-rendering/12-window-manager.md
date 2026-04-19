---
title: "Window Manager Service 与窗口管理"
chapter: "2.12"
section: "2.12"
status: ready-for-review
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-04-05"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowState.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/SurfaceControl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: official
    path: "developer.android.com/reference/android/view/WindowManager"
  - type: official
    path: "developer.android.com/develop/ui/views/layout/splash-screen"
tags: [WMS, WindowManagerService, Surface, Window, StartingWindow, Window动画, 多窗口, SurfaceControl, WindowInsets, Desktop Windowing]
related_chapters: ["2.1", "2.6", "3.1", "8.2", "8.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+读者需求"
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: fixed
task2b_result: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-19"
task6_result: "pass-light-edit"
task9_result: "needs-rework"
review_log: "logs/review/2026-04-11-11-review.md"
---

# 2.12 Window Manager Service 与窗口管理

## 为什么要了解 WMS

当我们分析 App 启动速度、界面切换卡顿、或者多窗口场景下的掉帧问题时，最终的线索往往都指向同一个地方——system_server 中的 WindowManagerService。

这并不是偶然。WMS 是 Android 窗口系统的中枢神经：从我们点击桌面图标那一刻起，WMS 就开始了一连串的工作——创建 StartingWindow 给用户即时的视觉反馈，为 App 分配 Surface 用于绘制，在 Activity 切换时管理过渡动画，在旋转屏幕时触发整个窗口树的 relayout。我们日常在 Perfetto 中看到的大量 system_server 活动，有相当一部分是 WMS 在工作。

不了解 WMS，我们在分析 Perfetto Trace 时遇到 system_server 的 Binder 调用就只能"看个热闹"。而理解了 WMS 的工作方式之后，我们就知道 `wm.relayout_window` 这个 Slice 对应的是什么操作，为什么它可能耗时，以及如何优化。简单来说，这是把"system_server 好像很忙"变成"我知道它在忙什么"的关键一步。

[待补充：Trace 截图 — 一段典型的冷启动 Trace，标注 WMS 相关的 Slice]

## WMS 的定位：窗口世界的调度员

我们先从宏观角度理解 WMS 在 Android 图形架构中的位置。在 §2.1 中我们看到了渲染管线的全景图，在那里 SurfaceFlinger 是合成者，App 是绘制者。WMS 则是这两者之间的协调者——它管理所有 Window 的创建、销毁、层级（Z-order）和大小，并确保 Surface 的分配和属性设置在正确的时机发生。

WMS 运行在 system_server 进程中。这意味着它的所有操作都和其他系统服务（AMS、IMS 等）共享同一个进程，也共享同一个主线程（`android.server` 线程）。这个设计在性能分析时尤其重要——如果 AMS 在处理一个耗时的 Activity 启动请求，可能会阻塞 WMS 处理另一个 App 的 relayout 请求，导致后者出现掉帧。

WMS 与其他关键组件的协作关系可以这样概括：

- **AMS（Activity Manager Service）**：AMS 负责 Activity 的生命周期管理，当 Activity 需要显示时，AMS 通知 WMS 创建或更新对应的 Window。WMS 不关心 Activity 的业务逻辑，只关心"这个 Window 应该多大、在什么位置、什么层级"。
- **SurfaceFlinger**：WMS 持有每个 Window 的 SurfaceControl（控制 Surface 的属性），SurfaceFlinger 负责实际的合成和显示。WMS 通过 SurfaceControl.Transaction 向 SurfaceFlinger 提交属性变更，SurfaceFlinger 在下一个 VSync 周期应用这些变更。
- **Input 系统**：WMS 维护所有 Window 的 Z-order 和区域信息，InputDispatcher 使用这些信息进行 hit-test（确定触摸事件应该发给哪个 Window）。我们在 §3.1 中详细分析了 Input 分发链路，其中焦点 Window 的切换就是 WMS 和 Input 系统协作的结果。

[图：WMS 与 AMS、SurfaceFlinger、Input 系统的交互关系图]

## Window 与 Surface 的关系

理解 WMS 的工作方式，最核心的一步是搞清楚 Window 和 Surface 的关系。这两个概念经常被混淆，但它们在架构上是完全不同的东西。

每个 Window 在 WMS 中对应一个 WindowState 对象，WindowState 持有一个 SurfaceControl。SurfaceControl 是一个句柄，它代表 SurfaceFlinger 中的一个 Layer——但 SurfaceControl 本身不能用来绘制。可以绘制的 Surface 通过 `relayoutWindow()` 返回给 App 端。所以准确的职责分工是：

- **WMS 端**：持有 SurfaceControl，控制 Surface 的位置、大小、透明度、Z-order 等元数据
- **App 端**：持有 Surface（通过 ViewRootImpl），用于实际的绘制（Canvas 或 GPU 渲染）
- **SurfaceFlinger 端**：持有 Layer，负责将 Surface 的内容和 SurfaceControl 的元数据合成到屏幕上

这三者的关系可以用一个不太精确但很好理解的类比：Surface 是画布（画家在上面画画），SurfaceControl 是画框（控制画的位置和大小），SurfaceFlinger 是画廊（把所有画按顺序挂好展示给观众）。

### Surface 创建流程

当我们启动一个 Activity 时，Surface 的创建经历了这样一个链路：

1. AMS 启动 Activity → 通知 WMS 准备 Window
2. App 进程创建 ViewRootImpl，调用 `WindowSession.relayout()` 发起 Binder 调用到 WMS
3. WMS 在 `relayoutWindow()` 中检查该 Window 是否已有 SurfaceControl
4. 如果没有，调用 `WindowStateAnimator.createSurfaceLocked()` 创建 SurfaceControl
5. SurfaceControl 的创建通过 JNI 调用到 native 层的 `SurfaceControl::create`，最终通过 Binder 调用 SurfaceFlinger 的 `createLayer()`
6. SurfaceFlinger 创建 Layer 并返回 handle
7. WMS 将 SurfaceControl 包装成 Surface 通过 Binder 返回给 App
8. App 的 ViewRootImpl 拿到 Surface，开始第一帧的绘制

[已验证: AOSP android-17-beta3, frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java — relayoutWindow() 方法签名包含 Session、IWindow client、LayoutParams attrs 等参数]

这个流程中最值得注意的性能点是第 5-6 步——SurfaceControl 的创建涉及一次到 SurfaceFlinger 的 Binder 调用和 Layer 的分配。在冷启动场景下，这个调用和 App 进程初始化、ContentProvider 初始化是并行还是串行，会直接影响启动速度。通常 WMS 会尽早地通过 StartingWindow 预创建 Surface，以减少冷启动时用户感知到的延迟。

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

`Transaction.apply()` 的执行方式值得说明：它在 framework 层通过 JNI 调用到 native 的 `SurfaceComposerClient::apply()`，后者将所有操作打包成一个 `transaction` 通过 Binder 发送给 SurfaceFlinger。SurfaceFlinger 在下一个合成周期（VSYNC_SF）处理这个 transaction。所以 `apply()` 本身不是同步阻塞等待 SurfaceFlinger 完成的——它更像是"发送一个命令然后返回"。

[待验证: SurfaceControl.Transaction.apply() 是否在某些情况下会同步等待 SurfaceFlinger 的回复，特别是在 Surface 首次创建时]

## StartingWindow 与启动性能

冷启动是用户最直接感知到性能的场景之一。当我们点击一个 App 的图标到看到 App 内容之间，系统需要做很多工作：fork 进程、初始化 Runtime、加载 APK、执行 Application.onCreate()、创建 Activity、inflate View hierarchy、绘制第一帧。这个过程可能需要几百毫秒甚至几秒。

WMS 在这个过程中的角色是提供"即时反馈"——在 App 进程还没准备好之前，就给用户一个视觉上的回应。这就是 StartingWindow 的作用。

### StartingWindow 的工作原理

StartingWindow 的创建流程大致如下：

1. AMS 决定启动一个 Activity → 通知 WMS
2. WMS 发现目标 App 进程尚未启动（冷启动）
3. WMS 立即创建一个 StartingWindow（类型为 `TYPE_APPLICATION_STARTING`）
4. StartingWindow 的内容来自 App 的主题配置（`windowBackground`）或 Android 12+ 的 SplashScreen API 配置
5. StartingWindow 显示在屏幕上，用户看到了 App 的 splash screen
6. App 进程启动完成后，App 的主 Window 准备好第一帧
7. WMS 移除 StartingWindow，显示 App 的主 Window

这个过程在 Perfetto 中表现为：我们在 system_server 进程中可以看到 WindowState 的创建和 visibility 变化。在 App 进程中，`reportDrawFinished` 这个 Slice 标记着 App 的第一帧绘制完成，此后 WMS 会安排 StartingWindow 的移除。

[待补充：Trace 截图 — StartingWindow 创建和移除在 Perfetto 中的表现]

### Android 12 SplashScreen API

在 Android 12 之前，StartingWindow 的外观完全由 `windowBackground` 决定，各家 OEM 也做了大量定制（有些甚至添加了广告 splash screen）。Android 12 引入了 SplashScreen API（`android.window.splashscreen`），统一了 StartingWindow 的行为：

- 开发者可以通过 `Theme.SplashScreen` 主题配置 icon、背景色、动画等
- SplashScreen 支持自定义退出动画（`setOnExitAnimationListener`）
- 向后兼容库 `androidx.core:splashscreen` 支持 Android 5.0+

从性能角度，SplashScreen API 最大的好处是标准化了 StartingWindow 的生命周期。在此之前，不少 App 自己实现一个 SplashActivity 作为启动页，这实际上增加了 Activity 启动的数量（先启动 SplashActivity，再跳转到 MainActivity），反而拖慢了启动速度。SplashScreen API 让 StartingWindow 成为系统层面的即时反馈，不增加 App 侧的 Activity 数量。

### StartingWindow 的时机陷阱

StartingWindow 的移除时机是一个性能调优的关键点：

- **过早移除**：如果 App 第一帧还没准备好就移除了 StartingWindow，用户会看到短暂的闪白/闪黑（取决于 Window 背景）
- **过晚移除**：如果 StartingWindow 持续显示太久，用户会感觉"App 启动好慢"，即使 App 内容早已准备好

理想情况下，StartingWindow 应该在 App 第一帧绘制完成的那一刻无缝切换。WMS 内部通过 `reportDrawFinished` 信号来协调这个时机——App 完成第一帧绘制后通知 WMS，WMS 在下一个 VSync 中移除 StartingWindow 并显示 App 主 Window。

## relayoutWindow：WMS 最频繁的操作

`relayoutWindow()` 是 WMS 中被调用次数最多的方法之一，也是性能分析中最常见的 WMS 相关 Slice。理解它的工作方式，是在 Perfetto 中解读 system_server 行为的关键。

### 什么触发 relayoutWindow

每当 App 需要更新 Window 的属性时，都会通过 `ViewRootImpl` 调用 `WindowSession.relayout()`，这是一个 Binder 调用，最终走到 WMS 的 `relayoutWindow()`。典型的触发场景包括：

- **Window 首次显示**：Activity 启动后，ViewRootImpl 首次调用 relayout 请求创建 Surface
- **大小变化**：屏幕旋转、多窗口切换、键盘弹出导致 Window 大小变化
- **Visibility 变化**：Window 从隐藏到显示，或从显示到隐藏
- **配置变更**：如 `configChanges` 触发的配置更新

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// @ AOSP android-16.0.0_r1 / android-17-beta3
private int relayoutWindow(WindowManager.LayoutParams params, int viewVisibility,
        boolean insetsPending) throws RemoteException {
    // ...
    int relayoutResult = mWindowSession.relayout(mWindow, mSeq, params,
            (int) (mView.getMeasuredWidth() * appScale + 0.5f),
            (int) (mView.getMeasuredHeight() * appScale + 0.5f),
            viewVisibility,
            insetsPending ? WindowManagerGlobal.RELAYOUT_INSETS_PENDING : 0,
            frameNumber, mTmpFrame, mTmpRect, mTmpRect, mTmpRect,
            mPendingBackDropFrame, mPendingDisplayCutout,
            mPendingMergedConfiguration, mSurfaceControl, mTempInsets,
            mTempControls, mSurfaceSize, mBlastSurfaceControl);
    // ...
}
```

注意这里的 `mWindowSession` 是 App 进程到 WMS 的 Binder 通道。每个 App 进程有一个 Session 对象（`IWindowSession`），所有 Window 操作都通过这个通道完成。一个 App 中多个 Window 的 relayout 请求在 WMS 端是串行处理的。

### relayoutWindow 内部流程

在 WMS 端，`relayoutWindow()` 的核心流程大致如下：

1. **参数校验**：检查 Window 的 LayoutParams 是否合法，调用者是否有权限
2. **WindowState 更新**：更新 WindowState 的布局参数、可见性等属性
3. **SurfaceControl 操作**：如果需要创建新的 Surface，调用 `WindowStateAnimator.createSurfaceLocked()`
4. **布局计算**：调用 `performLayout()` 计算所有 Window 的新位置和大小
5. **Surface 大小调整**：如果 Window 大小变化，通过 SurfaceControl.Transaction 调整 Surface 的尺寸
6. **构建返回值**：将新的 SurfaceControl、Window frames、Insets 等打包返回给 App

步骤 4 的 `performLayout()` 在 Window 数量较多时可能耗时较长。在桌面模式或多窗口场景下，一个 relayout 可能需要计算数十个 Window 的布局，这就是为什么这些场景下 system_server 的 CPU 占用会明显上升。

[图：relayoutWindow 的内部流程图]

### 在 Perfetto 中的表现

在 Perfetto Trace 中，`relayoutWindow` 对应的 Slice 通常出现在 system_server 进程的 Binder 线程上。我们可以通过以下方式定位和分析：

- **Slice 名称**：`wm.relayout_window` 或 `relayoutWindow`
- **所在进程**：system_server
- **所在线程**：通常是 `Binder:XXX_X` 线程

如果一个 `relayoutWindow` Slice 持续时间较长（例如超过 16ms），可能意味着：
- performLayout() 计算量大（Window 树复杂）
- SurfaceControl 创建/销毁耗时
- system_server 主线程被其他操作阻塞（锁竞争）

我们可以通过 Perfetto SQL 查询来定位耗时较长的 relayout 操作：

```sql
-- 查询耗时超过 16ms 的 relayoutWindow 调用
SELECT slice.name, slice.ts, slice.dur, track.name as track_name
FROM slice
JOIN track ON slice.track_id = track.id
WHERE slice.name LIKE '%relayout%'
  AND slice.dur > 16e6
ORDER BY slice.dur DESC
```

[待验证: 上述 SQL 查询在 Perfetto 中的实际 Slice 命名是否准确，不同 Android 版本可能有差异]

## Window 动画与过渡性能

当我们切换 App、回到桌面、或打开 Recent 页面时，屏幕上出现的过渡动画由 WMS 的 WindowAnimator 统一调度。这些动画不仅仅是视觉装饰——它们的性能直接影响用户对"流畅度"的感知。

### 动画的工作方式

WindowAnimator 负责系统级别的 Window 动画。在每一帧动画中，WindowAnimator 计算所有参与动画的 Window 的 transform（缩放、平移、透明度），然后通过 SurfaceControl.Transaction 提交给 SurfaceFlinger。

这意味着每帧动画都涉及：
1. WindowAnimator 在 system_server 中计算 transform
2. 构建 SurfaceControl.Transaction
3. 通过 Binder 提交给 SurfaceFlinger
4. SurfaceFlinger 在下一个 VSYNC_SF 合成

整个过程在 120Hz 屏幕上需要在 8.33ms 内完成（一个 VSync 周期）。如果 system_server 在某帧中因为锁竞争或其他操作导致 WindowAnimator 延迟，就会出现动画掉帧。

[已验证: AOSP android-17-beta3, WindowAnimator 运行在 system_server 的动画线程（`android.anim` 和 `android.anim.lf`）上，而非主线程。这是 Android 的一个重要设计决策——将动画计算从主线程剥离，避免主线程的耗时操作影响动画流畅度。]

### Activity 切换动画

Activity 切换动画（open/close）是 WMS 动画中最常见的一种。当启动一个新的 Activity 时：

1. AMS 通知 WMS 准备切换动画
2. WMS 创建一个 AppWindowAnimator，配置动画参数（如缩放动画、淡入动画）
3. 旧 Activity 的 Window 逐渐缩小/淡出，新 Activity 的 Window 逐渐放大/淡入
4. 动画期间，两个 Window 的 SurfaceControl transform 每帧更新
5. 动画结束后，旧 Window 的 visibility 设为 GONE

在 Perfetto 中，我们可以在 `android.anim` 线程中看到动画的帧调度。如果动画期间出现掉帧，通常需要检查 system_server 的整体负载——是否有其他 Binder 调用占用了主线程导致动画线程被阻塞。

### Predictive Back 动画

Android 14 引入、Android 15 默认启用的 Predictive Back 是 WMS 动画的一个重要演进。与传统的一按就返回不同，Predictive Back 允许用户在手指滑动过程中实时预览返回后的界面，松手后才执行实际的返回操作。

这个功能对 WMS 的影响在于：WMS 需要与 Input 系统紧密协作，在手势进行过程中实时更新当前 Window 和目标 Window 的 SurfaceControl transform。具体来说：

- 用户开始返回手势 → Input 系统通知 WMS
- WMS 识别返回目标（前一个 Activity / 桌面 / 上一个 Task）
- 手势滑动过程中，WMS 每帧更新当前 Window 的偏移量和透明度
- 手势完成（松手）→ WMS 执行完整的过渡动画或取消动画

Android 16 进一步完善了这个机制，引入了 `finishAndRemoveTaskCallback` 和 `moveTaskToBackCallback` 等新的回调 API，让 WMS 能更精确地控制不同返回场景的动画行为。

[已验证: 官方文档, developer.android.com/guide/navigation/custom-back/predictive-back-gesture]

## 多窗口、折叠屏与 Desktop Mode

Android 的多窗口能力经历了从实验性功能到核心特性的演变。如今 Split-screen、Freeform、Picture-in-Picture（PiP）已经全面铺开，Android 16 更是将 Desktop Windowing 推向了 GA（Generally Available）。这些模式对 WMS 的工作方式产生了深远影响。

### 多窗口模式下的 WMS 工作量

在单窗口模式下，WMS 主要管理一个前台 App 的 Window 和几个系统 Window（状态栏、导航栏等）。但在多窗口模式下：

- **Split-screen**：WMS 需要同时管理两个 App 的 Window，计算它们的分屏边界
- **Freeform**：每个自由窗口都有自己的 WindowState、SurfaceControl 和 Window frames
- **PiP**：画中画窗口虽然是缩小版，但它的 Window 生命周期和 Surface 更新逻辑和全屏 Window 一样完整

这意味着 WMS 的 `performLayout()` 需要处理的 Window 数量成倍增加，每个 SurfaceControl.Transaction 包含的操作也更多。在低端设备上，多窗口模式是 system_server CPU 占用上升的常见原因。

### 折叠屏的配置变更

折叠屏设备的折叠/展开会触发屏幕尺寸变化，这对 WMS 来说是一次大规模的 relayout 操作：

1. DisplayManager 检测到显示区域变化 → 通知 WMS
2. WMS 触发所有可见 Window 的 `onConfigurationChanged`
3. 如果 App 没有声明处理配置变更，AMS 会销毁并重建 Activity
4. 即使 App 声明了处理配置变更（`configChanges`），WMS 仍然需要为所有 Window 执行 relayout

Android 17 引入的 `recreateOnConfigChanges` 属性进一步优化了这个场景：对于屏幕尺寸变化、屏幕方向变化等 6 种配置变更，默认不再强制重启 Activity，而是通过 WMS 的 relayout + App 端的 `onConfigurationChanged` 回调来处理。这大大减少了折叠屏展开/折叠时的开销。

[待验证: recreateOnConfigChanges 在 Android 17 中的具体行为和 manifest 配置方式，当前基于 Android 17 Developer Preview 的公开信息]

### Android 16 Desktop Windowing

Android 16（2025 年 6 月发布）将 Desktop Windowing 推向了 GA。在外接显示器场景下，WMS 需要管理自由窗口的拖拽、缩放、层级——这和传统 PC 操作系统的窗口管理很接近。

Desktop Windowing 对 WMS 的核心挑战：

- **窗口 Z-order 管理**：自由窗口可以重叠，WMS 需要维护正确的 Z-order，并确保 Input 系统的 hit-test 与 Z-order 一致
- **拖拽过程中的实时 relayout**：用户拖动窗口时，WMS 需要每帧更新 SurfaceControl 的 position
- **窗口缩放的 Surface 大小调整**：窗口缩放涉及 Surface 的 resize，可能触发 SurfaceFlinger 的 Layer 重建
- **多显示器支持**：Android 16 QPR3 支持跨显示器拖拽窗口，WMS 需要处理跨 Display 的 Window 迁移

从性能分析的角度，Desktop Windowing 场景下的 Perfetto Trace 会比传统移动场景复杂得多。system_server 的 Binder 线程上可能出现密集的 `relayoutWindow` 调用，而 SurfaceFlinger 的合成负担也因为 Layer 数量的增加而上升。

## 在 Perfetto 中的综合表现

我们把前面散落提到的 WMS 相关 Trace 事件汇总一下，方便在 Perfetto 中系统性地定位。

### 关键 Slice 和 Track

| Slice 名称 | 所在位置 | 含义 |
|-----------|---------|------|
| `wm.relayout_window` | system_server / Binder 线程 | Window relayout 操作 |
| `wm.set_visibility` | system_server / Binder 线程 | Window visibility 变更 |
| `wm.pause_timeout` | system_server / 主线程 | Activity pause 超时 |
| `WindowManager` | system_server | WMS 相关的通用 trace tag |
| `SurfaceControl.Transaction.apply` | system_server / 各线程 | SurfaceControl Transaction 提交 |
| `animator` | system_server / `android.anim` 线程 | Window 动画帧 |
| `reportDrawFinished` | App 进程 | App 第一帧绘制完成 |

### 典型分析场景

**场景 1：冷启动分析**

1. 在 system_server 中定位到 Activity 启动相关的 Slice
2. 查找 `wm.relayout_window` — 对应 StartingWindow 的创建
3. 在 App 进程中找到 `reportDrawFinished` — App 第一帧完成
4. 两个事件之间的时间差就是"StartingWindow 显示到 App 内容显示"的延迟
5. 检查中间是否有 system_server 主线程被阻塞的迹象

**场景 2：多窗口切换掉帧**

1. 在 SurfaceFlinger 进程中定位到掉帧的 VSync 周期
2. 回溯到 system_server 的 `android.anim` 线程，检查是否有动画帧延迟
3. 检查同一时段 system_server 主线程上是否有耗时的 AMS 操作（如 Activity pause）
4. 检查 `wm.relayout_window` 是否在掉帧时段有异常耗时的调用

**场景 3：旋转屏幕卡顿**

1. 在 system_server 中搜索 `wm.relayout_window` 和 `performLayout` 相关 Slice
2. 检查 relayout 的耗时——如果超过一帧（16ms@60Hz / 8ms@120Hz），可能导致掉帧
3. 检查 App 进程是否因为配置变更触发了 Activity 重建
4. 如果 App 声明了 `configChanges`，检查 `onConfigurationChanged` 的执行时间

## 与其他机制的关系

WMS 不是一个孤立的系统服务，它的性能表现受到多个上下游的影响：

- **§2.1 渲染架构全景**：WMS 是 App 绘制和 SurfaceFlinger 合成之间的桥梁
- **§2.6 SurfaceFlinger 与合成**：WMS 通过 SurfaceControl.Transaction 与 SurfaceFlinger 交互，Transaction 的执行时机影响合成效率
- **§2.13 图形缓冲区管理**：Surface 的创建涉及 BufferQueue 的分配，BufferQueue 的 producer/consumer 模型决定了 App 和 SurfaceFlinger 的协作方式
- **§3.1 Input 事件分发**：WMS 维护的 Window Z-order 和焦点信息是 InputDispatcher 进行 hit-test 的基础
- **§8.2 启动速度分析**：StartingWindow 的创建和移除时机直接影响启动体感
- **§8.4 其他响应速度场景**：旋转屏幕、多窗口切换等场景中 WMS 的 relayout 是性能关键路径

## 版本演进

| 版本 | 变化 | 性能影响 |
|------|------|---------|
| Android 7.0 (API 24) | 多窗口模式正式支持 | WMS 首次需要同时管理多个 App Window |
| Android 8.0 (API 26) | 画中画（PiP）模式 | PiP Window 的 Surface 大小动态变化 |
| Android 10 (API 29) | 折叠屏支持，屏幕尺寸动态变化 | 大规模 Window relayout 场景增加 |
| Android 12 (API 31) | SplashScreen API 统一 StartingWindow | 标准化了启动视觉反馈，减少自定义 SplashActivity 的开销 |
| Android 12 (API 31) | SurfaceControl.Transaction 成为标准 API | 批量操作减少 Binder 调用次数 |
| Android 14 (API 34) | Predictive Back 引入 | WMS 需要在手势过程中实时更新 Window transform |
| Android 15 (API 35) | Predictive Back 默认启用 | 所有 App 的返回手势都涉及 WMS 动画 |
| Android 15 (API 35) | Edge-to-Edge 强制执行 | WindowInsets 分发频率增加，不当处理可能触发额外 relayout |
| Android 16 (API 36) | Desktop Windowing GA | 自由窗口管理成为 WMS 的核心职责之一 |
| Android 16 (API 36) | 大屏强制可调整（Adaptive Apps） | screenOrientation/resizableActivity 限制被忽略，relayout 场景增加 |
| Android 17 (API 37) | recreateOnConfigChanges | 6 种配置变更不再强制重启 Activity，减少 Window 重建开销 |
| Android 17 (API 37) | Bubbles for all apps | 浮动窗口模式增加 WMS 管理的 Window 数量 |

## 常见问题与误区

### 误区 1："WMS 在主线程上运行，所以很慢"

WMS 的部分操作确实在 system_server 主线程上执行，但动画相关的操作在独立的 `android.anim` 和 `android.anim.lf` 线程上。此外，大部分 relayoutWindow 调用在 Binder 线程上处理，不直接阻塞主线程。但如果主线程持有 WMS 需要的锁（如 `mGlobalLock`），Binder 线程上的 relayout 也会被阻塞。

### 误区 2："Window 数量越多越卡"

Window 数量本身不是问题。真正需要关注的是有多少 Window 参与 `performLayout()` 的计算。一个后台 App 的隐藏 Window 几乎不消耗 WMS 的资源。真正的性能瓶颈是"同时可见的、需要频繁 relayout 的 Window 数量"——这正是多窗口和 Desktop 模式下需要关注的。

### 误区 3："StartingWindow 是 App 画的"

StartingWindow 不是由 App 进程绘制的。它的内容由 WMS 直接创建，使用 App 主题中定义的 `windowBackground` 或 SplashScreen API 配置的资源。App 进程启动期间，StartingWindow 已经在屏幕上了。这就是为什么即使 App 启动很慢，用户也能立即看到 splash screen——因为那是 system_server 画的，不是 App 画的。

### 误区 4："relayoutWindow 慢一定是 WMS 的问题"

`relayoutWindow` 的耗时可能是 WMS 内部的问题（如 performLayout 计算量大），但也可能是被其他操作阻塞了。常见的阻塞源包括：AMS 在主线程上处理 Activity pause（持有全局锁）、其他 Binder 调用占用了 WMS 的锁、或者 SurfaceControl 创建时 SurfaceFlinger 响应慢。分析 relayout 慢的问题时，需要同时看 system_server 主线程和 SurfaceFlinger 的情况。

### 误区 5："Predictive Back 动画延迟是 Input 系统的问题"

Predictive Back 动画涉及 Input 系统和 WMS 的协作。手势事件的分发是 Input 系统负责的，但动画的计算和 SurfaceControl 更新是 WMS 的 WindowAnimator 负责的。如果手势响应延迟，需要分别检查 Input 通道的延迟和 WindowAnimator 的帧调度情况。

## 扩展

### 🔸 WindowInsets 与布局性能

WindowInsets 是 WMS 向 App 传递系统 UI 元素（状态栏、导航栏、键盘、刘海屏）占用空间的机制。理解它的分发链路对优化布局性能很重要。

分发链路是这样的：WMS 计算每个 Window 的 Insets → 通过 `relayoutWindow` 的返回值传递给 ViewRootImpl → ViewRootImpl 触发 View hierarchy 的 `dispatchApplyWindowInsets` → 各 View 根据 Insets 调整自己的 padding/margin。

性能风险在于：如果 App 在 Insets 处理中调用了 `requestLayout()`，会触发整棵 View 树的 measure/layout pass。如果 WindowInsets 频繁变化（如动画过程中），这个开销可能很可观。Android 15 强制 Edge-to-Edge 后，更多 App 需要主动处理 Insets，这个问题变得更加普遍。

优化建议：使用 Compose 的 `Modifier.windowInsetsPadding()` 替代手动 padding 计算；在 View 系统中使用 `setOnApplyWindowInsetsListener` 精确处理，避免使用 `fitsSystemWindows="true"` 的盲目全局处理；处理完 Insets 后调用 `WindowInsets.CONSUMED` 防止不必要的向下分发。

### 🔸 WMS 与 Input 系统的协作

WMS 维护的 Window Z-order 和区域信息是 InputDispatcher 进行 hit-test 的基础。当用户触摸屏幕时：

1. InputDispatcher 从 WMS 获取当前所有可见 Window 的区域和 Z-order
2. 按照从上到下的 Z-order 遍历 Window，找到第一个包含触摸坐标的 Window
3. 将触摸事件通过 InputChannel 发送给该 Window 所属的 App 进程

窗口焦点（focus）切换的性能影响容易被忽视。当焦点从一个 App 切换到另一个 App 时（如启动新 Activity），Input 通道也需要切换。在切换的瞬间（通常只有几毫秒），可能会有 Input 事件丢失。这在快速操作场景（如连续快速点击）中可能导致"点了没反应"的用户体验。

这个问题在 §3.1 中有更详细的分析，包括如何在 Perfetto 中追踪 Input 通道的切换过程。

## 参考资料

- [AOSP WindowManagerService 源码](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java) — WMS 主类，包含 relayoutWindow 等核心方法
- [AOSP SurfaceControl 源码](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/java/android/view/SurfaceControl.java) — SurfaceControl 和 Transaction API
- [AOSP ViewRootImpl 源码](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/java/android/view/ViewRootImpl.java) — App 端 Window 操作的发起者
- [Android 官方文档 - SplashScreen API](https://developer.android.com/develop/ui/views/layout/splash-screen) — StartingWindow 和 SplashScreen 的官方指南
- [Android 官方文档 - Predictive Back](https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture) — 预测性返回手势的实现指南
- [Android 官方文档 - WindowInsets](https://developer.android.com/develop/ui/views/layout/window-insets) — WindowInsets 的处理最佳实践
- [Android 官方文档 - Desktop Windowing](https://developer.android.com/about/versions/16/features#desktop-windowing) — Android 16 桌面窗口模式
- [源码路径: frameworks/base/services/core/java/com/android/server/wm/] — WMS 相关所有类的源码目录
- [源码路径: frameworks/base/core/java/android/view/SurfaceControl.java] — SurfaceControl 和 Transaction 的完整实现

### Android 16 ViewRootImpl Traversal 与 Relayout 内部机制深度解析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android 16 ViewRootImpl Traversal 与 Relayout 内部机制深度解析.md
- 类型：DeepResearch 调研结果
- 摘要：调研从 scheduleTraversals、sync barrier、Choreographer CALLBACK_TRAVERSAL 讲到 performTraversals 和 relayoutWindow 判定条件，系统梳理了 ViewRootImpl 与 WMS 的协作边界及性能诊断切口。
- 注入时间：2026-04-18
- 价值：适合补强 2.12 对 App 侧窗口根节点和 relayout 触发矩阵的覆盖。
