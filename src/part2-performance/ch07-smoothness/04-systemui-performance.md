---
title: SystemUI 性能分析
chapter: '7.4'
section: '7.4'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
tags:
- systemui
- jank
- launcher
- statusbar
- navigationbar
- notification-shade
- perfetto
related_chapters:
- '2.3'
- '2.4'
- '7.1'
- '7.2'
- '13.2'
confidence: medium-high
last_verified: '2026-08-19'
last_verified_against: 'AOSP android-17.0.0_r1 SystemUI/WM Shell/Launcher3 anchors: systemui.aconfig; super_notification_shade.xml / scene_window_root.xml; ShadeViewProviderModule / ShadeWindowLayoutParams / NotificationShadeWindowView; SceneContainerFlag / SceneContainerFrameworkModule / SceneWindowRootViewBinder; NotificationStackScrollLayout / NotificationRowContentBinderImpl / BigPictureIconManager / notification icon binder; StatusBarWindowControllerImpl / NavigationBar / NavigationBarView / DisplayBackGestureHandler / EdgeBackGestureHandler / SysUIConcurrencyModule / DisplayContent; Transitions / StartingWindowController / RecentsView; Android notification, SplashScreen and aconfig official docs checked 2026-08-19.'
last_rework_at: '2026-08-19T13:51:21+08:00'
last_rework_run_id: 20260819-135121-rework-68502f5f
sources:
- type: aosp
  path: frameworks/base/packages/SystemUI/aconfig/systemui.aconfig
- type: aosp
  path: frameworks/base/packages/SystemUI/res/layout/super_notification_shade.xml
- type: aosp
  path: frameworks/base/packages/SystemUI/res/layout/scene_window_root.xml
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/shade/ShadeViewProviderModule.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/shade/ShadeWindowLayoutParams.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/shade/NotificationShadeWindowView.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/stack/NotificationStackScrollLayout.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/collection/NotifInflaterImpl.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/collection/inflation/NotificationRowBinderImpl.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/row/NotificationRowContentBinderImpl.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/row/BigPictureIconManager.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/icon/ui/viewmodel/NotificationIconContainerStatusBarViewModel.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/icon/ui/viewbinder/NotificationIconContainerStatusBarViewBinder.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/phone/ui/StatusBarIconControllerImpl.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/window/StatusBarWindowControllerImpl.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/views/NavigationBar.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/views/NavigationBarView.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/DisplayBackGestureHandler.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/util/concurrency/SysUIConcurrencyModule.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/scene/shared/flag/SceneContainerFlag.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/scene/SceneContainerFrameworkModule.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/scene/ui/view/SceneWindowRootViewBinder.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/compose/features/src/com/android/systemui/scene/ui/composable/SceneContainer.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/SceneTransitionLayout.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/reveal/ContainerReveal.kt
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/DisplayContent.java
- type: aosp
  path: frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java
- type: aosp
  path: frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/transition/Transitions.java
- type: aosp
  path: packages/apps/Launcher3/quickstep/src/com/android/quickstep/views/RecentsView.java
- type: official
  path: https://source.android.com/docs/setup/build/feature-flagging/flip-a-flag
- type: official
  path: https://developer.android.com/develop/ui/views/notifications
- type: official
  path: https://developer.android.com/develop/ui/views/launch/splash-screen
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# SystemUI 性能分析

普通 App 卡顿时，受影响的画面往往局限在一个任务内。SystemUI 负责的状态栏、通知抽屉、锁屏和导航区域覆盖面更大；同一段阻塞还可能与 Launcher（桌面与最近任务组件）、WM Shell（窗口管理的交互与动画组件）和目标 App 的动画重叠。只查看 `com.android.systemui` 的主线程，很容易混淆窗口由谁创建、工作在哪个线程执行，以及最终画面何时呈现。

Android 12—16 的演进用于说明版本差异，现行结论统一以 Android 17 / API 37 / `android-17.0.0_r1` 为平台版本。涉及输入、调度和显示栅栏时，内核版本采用 `android17-6.18-2026-06_r6`。

Android 17 同时保留 legacy shade（传统通知面板）与 SceneContainer（基于场景切换的新容器）路径，并加入状态栏、通知抽屉、返回手势专用 UI 线程等开关。分析前需要记录目标构建的 flag（功能开关）、窗口和线程，不能只凭系统版本推断实际执行路径。

## 版本、flag、窗口和线程

Android 17 的 SystemUI 不能用一张固定架构图概括。`scene_container`、`dual_shade`、`status_bar_for_desktop`、`status_bar_root_modernization`、`status_bar_system_status_icons_in_compose`、`status_bar_ui_thread`、`notification_shade_ui_thread` 与 `edge_back_gesture_handler_thread` 都会改变应当观察的窗口、线程或 UI 实现。AOSP tag 只能证明代码存在；目标产品是否执行该分支，仍由构建配置和运行时 flag 决定。

下面的只读命令用于保存设备身份、相关 aconfig 状态、线程名和窗口名：

```bash
adb shell getprop ro.build.fingerprint
adb shell aflags list | grep -E 'com\.android\.systemui\.(scene_container|dual_shade|status_bar_for_desktop|status_bar_root_modernization|status_bar_system_status_icons_in_compose|status_bar_ui_thread|notification_shade_ui_thread|edge_back_gesture_handler_thread)'
adb shell ps -A -T | grep -E 'systemui|launcher|ShellMain|ShellAnimation|Splashscreen|BackPanelUiThread|NotifInflation|RenderThread'
adb shell dumpsys window windows | grep -E 'NotificationShade|StatusBar|NavigationBar'
```

这组输出应与 Perfetto trace（系统跟踪）一起保存。`aflags list` 只说明 aconfig（Android 平台功能开关系统）中的 flag 值；窗口列表和线程列表才能证明对应实现已经创建。量产设备还可能隐藏部分调试信息，此时需要借助 userdebug（可调试系统构建）或厂商内部符号补充证据。

### 组件边界

| 画面或工作 | Android 17 的主要实现 | 分析时要确认的窗口或线程 |
| --- | --- | --- |
| 状态栏窗口 | `StatusBarWindowControllerImpl`、状态栏 View/Compose root（根节点）、通知与系统图标绑定 | `StatusBar` 或 `StatusBar(displayId=N)` 窗口；主线程或专用 UI 线程 |
| 通知抽屉与锁屏主窗口 | legacy `NotificationShadeWindowView`，或 `SceneWindowRootView` 承载的 View/Compose 混合树 | `NotificationShade` 窗口；主线程或专用 UI 线程 |
| 通知列表 | `SharedNotificationContainer` 与 `NotificationStackScrollLayout`（简称 NSSL，通知列表容器） | Scene 与 legacy 两条路径都可能出现 NSSL |
| 三按钮导航 | `NavigationBar`、`NavigationBarView` | `NavigationBarN` 窗口及其 ViewRoot |
| 边缘返回 | `EdgeBackGestureHandler`、`DisplayBackGestureHandlerImpl`、Back Panel（返回手势箭头面板） | `edge-swipe` input monitor（输入监听器）；`BackPanelUiThread` 或主线程 |
| Overview / Recents | Launcher3 Quickstep 的 `RecentsView` 等组件 | 设备当前 Launcher 进程，包名不必然是 `com.android.launcher3` |
| 窗口转场与起始窗口 | WM Shell `Transitions`、`StartingWindowController` | Shell main/animation/splashscreen executor（主逻辑/动画/启动画面执行器）所在线程及宿主进程 |
| 最终合成与显示 | SurfaceFlinger、HWC（Hardware Composer，硬件合成器）、显示驱动 | SurfaceFlinger、FrameTimeline（逐帧时间线）、fence（同步栅栏）与显示时序 |

WM Shell 指的是一组组件，并不固定对应一个独立进程。目标产品可以把 Shell 组件装入 SystemUI 宿主，也可以改变宿主方式。Perfetto 中应根据进程的 `cmdline`（命令行标识）和线程名定位，不能预设总有一个固定的“WM Shell 进程”。

## Android 17 的窗口拓扑

`super_notification_shade.xml` 的根节点是 `NotificationShadeWindowView`，并通过 `<include>` 引入 `status_bar_expanded`。`status_bar_expanded` 是展开面板的布局名，不代表屏幕顶部的状态栏窗口。Android 17 中，状态栏、通知抽屉/锁屏主窗口和三按钮导航栏都通过各自的 `WindowManager.addView()` 路径创建窗口。

Android 17 的三个窗口入口可以直接从 `WindowManager.LayoutParams` 对上：

| 窗口 | 类型 | AOSP 标题 | 源码入口 |
| --- | --- | --- | --- |
| 顶部状态栏 | `TYPE_STATUS_BAR` | 默认屏为 `StatusBar`，辅助屏为 `StatusBar(displayId=N)` | `StatusBarWindowControllerImpl.getBarLayoutParamsForRotation()` |
| 通知抽屉/锁屏主窗口 | `TYPE_NOTIFICATION_SHADE` | `NotificationShade` | `ShadeWindowLayoutParams.create()` |
| 三按钮导航栏 | `TYPE_NAVIGATION_BAR` | `NavigationBarN` | `NavigationBar.getBarLayoutParams()` |

三者都有各自的 `WindowManager.addView()` 路径。一个窗口也可能在 SurfaceFlinger 中产生多个 Layer（图层），因此窗口名与 Layer 数量没有一一对应关系。窗口由谁创建应通过 `dumpsys window` 确认；合成阶段再根据名称和时间，在 SurfaceFlinger Layers 中找到相应图层。

### Legacy shade 的树

`ShadeViewProviderModule` 在 `SceneContainerFlag.isEnabled == false` 时直接 inflate（从布局资源创建 View）`super_notification_shade.xml`。这棵根树包含：

- 背景、通知区和前景 Scrim（半透明遮罩）；
- `status_bar_expanded`；
- `KeyguardRootView`；
- `SharedNotificationContainer`；
- bouncer（锁屏认证界面）、light reveal（亮屏揭示动画）等兼容内容。

`NotificationShadeWindowView` 会在 `onMeasure()` 中写入 `NotificationShadeWindowView#onMeasure` slice（时间区间），并在 `requestLayout()` 时写入 instant event（瞬时事件）。它的类注释也说明了边界：该 View 可以担任主 SystemUI 窗口根节点，但调用者不能假定它始终处于根节点位置。

### Scene shade 是 Compose 与 View 的混合树

Scene flag 开启时，`ShadeViewProviderModule` 会 inflate `scene_window_root.xml`。该 XML 以 `SceneWindowRootView` 为根，内部仍通过 include 包含完整的 `super_notification_shade.xml`。随后，`SceneWindowRootViewBinder` 完成三件与性能分析直接相关的工作：

1. 创建承载 `SceneContainer` 的 `ComposeView`。
2. 将 `legacy_window_root`（传统窗口根节点）设为不可见。
3. 把包含 NSSL 的 `SharedNotificationContainer` 从旧父节点移出，放到 Scene ComposeView 之后，作为同一窗口中的兄弟 View。

因此，Scene 开启后仍要保留 NSSL 相关观察点。锁屏、Shade、QS（Quick Settings，快捷设置）等场景切换进入 Compose，但通知行仍可以走 View 体系。一次展开可能同时包含 Compose 的 recomposition/layout/draw（重组/布局/绘制）、NSSL 的 View 测量与状态计算、RenderThread 的绘制记录和提交，以及 SurfaceFlinger 合成。

## SceneContainer：按 Android 17 源码理解

`SceneContainerFlag.isEnabled` 在 `android-17.0.0_r1` 中等于 `Flags.sceneContainer() && isEnabledOnVariant`，不要求一组 secondary flags（辅助开关）同时满足。Automotive 等 SystemUI variant（产品变体）可以通过 `isEnabledOnVariant` 强制关闭；普通产品仍要以目标构建的 aconfig 值为准。

`SceneContainerFrameworkModule` 注册的场景包括 `Gone`、`Communal`、`Dream`、`Occluded`、`Lockscreen`、`QuickSettings` 和 `Shade`；overlay（覆盖层）包括通知 Shade、QS Shade、Quick Actions 与 Bouncer。Dual Shade（双面板通知/快捷设置）生效后，某些大屏配置会省去 Shade/QS scene，改用两类 overlay。这个差异会改变 Compose 节点数量、过渡路径和 trace 名称。

### 性能观察点

- `SceneWindowRootViewBinder` 的绑定 trace 名为 `SceneWindowRootViewBinder`，适合确认 Scene 根节点是否建立，不能用来表示每次过渡的耗时。
- `SceneJankMonitor` 将特定 scene transition（场景过渡）映射到 `InteractionJankMonitor` 的 CUJ（Critical User Journey，关键用户操作流程）。
- `SceneTransitionLatencyMonitor` 记录 scene transition 的开始、结束和延迟。
- `SceneTransitionBlurViewModel.requestWindowBackgroundBlur()` 根据 transition state（过渡状态）和进度请求窗口背景模糊；`WindowBackgroundBlur` log buffer（日志缓冲区）会记录请求值和支持状态。
- `status_bar_root_modernization` 与 `status_bar_system_status_icons_in_compose` 是状态栏自身的迁移开关，不能从 `scene_container` 的值推导。

模糊成本需要根据目标设备的 RenderThread、GPU 和 SurfaceFlinger 数据判断。`debug.hwui.disable_blur_visual_feedback` 在 Android 17 参考源码中没有形成稳定的 SystemUI 诊断接口，不适合作为通用诊断入口。工程验证可以在可控分支中关闭具体的 blur flag，或把模糊半径设为零进行实验，同时保留同一设备、同一场景、同一热状态下的对照 trace。

Compose 路径的 PSS（按比例分摊的进程内存）也没有固定增幅。Scene 数量、always-compose（始终保持组合）策略、状态对象、缓存和 OEM 内容都会影响初始值。应按 flag 组合分别记录冷启动后、稳定待机、展开 Shade、通知集中到达后的内存，再检查对象以及 native/GPU（原生/GPU）内存来自哪里。

## 通知从入库到显示的 Android 17 路径

通知列表性能至少包含“集合变化、通知行内容绑定、列表状态计算、窗口绘制”四段工作。Android 17 的主要调用关系如下：

1. `NotifInflaterImpl.inflateViews()` 或 `rebindViews()` 把 entry（SystemUI 中的一条通知记录）交给 `NotificationRowBinderImpl`。
2. `NotificationRowBinderImpl` 创建或复用 `ExpandableNotificationRow`（可展开的通知行 View），更新图标，并通过 `RowContentBindStage` 请求需要的 contracted、expanded、public、single-line（折叠、展开、隐私、单行）等内容形态。
3. `NotificationRowContentBinderImpl` 创建 `AsyncInflationTask`，在 `@NotifInflation Executor`（通知创建工作线程执行器）上构建通知内容、加载所需图片并等待预加载任务。
4. `RemoteViews`（可跨进程描述界面内容的对象）新建视图时走 `applyAsync()`，复用现有视图时走 `reapplyAsync()`。
5. 异步 apply 失败时，`OnViewAppliedListener.onError()` 会在 UI 回调路径尝试同步 `apply()` 或 `reapply()`，以区分异步框架异常与通知内容本身无法 inflate。
6. 所需内容全部完成后，更新后的 row 进入 View 树，引起后续的测量、布局、动画和绘制。

Android 17 已没有旧路径中的 `NotificationContentInflater.java`。实现类迁移为 Kotlin 的 `NotificationRowContentBinderImpl.kt`，但 `doInBackground()` 仍保留历史 trace 名 `NotificationContentInflater.AsyncInflationTask#doInBackground`。搜索 trace 时要区分“为了兼容保留的 slice 名称”和“当前源码中是否仍存在同名类”。

### 异步绑定没有消除 UI 线程成本

`AsyncInflationTask` 把 Builder 恢复（从通知数据还原模板构建器）、模板生成、部分图片工作和 RemoteViews inflate 移到 `NotifInflation` 线程。UI 线程仍要处理完成回调、把 View 加入界面树、wrapper（内容包装 View）更新、`requestLayout()`、动画状态和窗口 traversal（界面遍历）。大量通知在短时间到达时，常见的时序是：

- `NotifInflation` 队列持续工作；
- 多个异步结果在相近时刻完成；
- UI 线程集中把通知 row 加入 View 树；
- NSSL 与状态栏图标容器在随后几帧反复更新；
- RenderThread 或 SurfaceFlinger 在同一时间段承接更大的绘制与合成负载。

同步 fallback（后备路径）也要单独标记。若 trace 或日志显示 `applyAsync()` 失败后频繁回到同步处理，耗时位置会从 worker（工作线程）转移到 UI 回调。此时，降低通知更新频率只能减少发生次数；还应查清自定义 `RemoteViews`、资源、URI 权限或厂商控件为何导致异步 apply 失败。

### NSSL 的测量成本与“屏幕上可见几条”不同

`NotificationStackScrollLayout#onMeasure` 在 Android 17 中会遍历全部 child（子 View），并明确测量 `GONE` child，因为算法需要这些高度来估算可容纳的通知数量。通知行在视觉上被隐藏，不表示测量工作归零。以下条件都会改变一帧中的工作量：

- entry 与 row 总数；
- 分组展开/折叠和 heads-up（悬浮通知）状态；
- public、contracted、expanded、single-line 等内容变体是否已绑定；
- OEM 增加的包装层和装饰 View；
- 配置变化、字体缩放、屏幕形态切换触发的重新测量。

NSSL 在 legacy 路径中通过 pre-draw listener（绘制前监听器）调用 `updateChildren()`；Scene 路径则会在绘制前的 `onJustBeforeDraw()` 处理待更新状态。两条路径都保留 `NSSL#updateChildren` slice。这个方法会运行 stack algorithm（通知堆叠布局算法）、应用当前状态，或启动状态动画，并处理通知之间的重叠。

### 普通模板、自定义 RemoteViews 与大图

| 负载 | 主要风险 | 证据入口 |
| --- | --- | --- |
| 标准模板高频更新 | entry 反复 rebind（重新绑定）、图标变化、多个完成回调集中到达 | `NotifInflation` 队列、row bind 日志、NSSL requestLayout |
| 自定义 `RemoteViews` | 层级复杂、资源异常、异步 apply fallback、内存校验失败 | `applyAsync/reapplyAsync`、`onError`、`CustomViewMemorySizeExceededException` |
| 大图通知 | 解码与缩放、像素常驻、异步预加载等待、纹理上传 | worker CPU、bitmap/native（位图/原生）内存、RenderThread 与 GPU |
| 分组通知 | summary/child（摘要/子通知）内容形态、展开状态与动画、更多 row 参与测量 | group 状态变化、NSSL measure/updateChildren |

`BigPictureIconManager` 对部分 URI/resource（资源）类型支持延迟加载；bitmap、adaptive bitmap（自适应位图）和 data 类型会跳过这套延迟策略，因为像素仍会常驻内存。`NotificationRowContentBinderImpl` 的 worker 最多等待图片预加载 1000 ms。这个超时发生在异步任务中，不能写成 UI 线程一定卡住一秒；但队列延迟、完成回调集中到达和后续纹理上传仍可能影响可见帧。

App 侧的改进通常更直接：合并高频进度更新，保持通知 ID 与模板稳定，减少内容未变化时的 `notify()`，避免每秒替换大图，控制自定义 RemoteViews 层级，并利用通知分组减少不必要的结构变化。SystemUI 侧则要保留异步路径，修复触发 fallback 的原因，限制同一帧中的状态更新量，并用设备数据验证任何缓存策略。

## 状态栏图标：通知图标与系统状态图标分开看

Android 12—14 的资料常从 presenter/controller 追踪左侧通知图标。Android 17 的当前实现位于 `statusbar/notification/icon/ui`：

- `NotificationIconContainerStatusBarViewModel.icons` 从 `iconsInteractor.statusBarNotifs` 生成 `NotificationIconsViewData`，在后台 context（协程执行上下文）中执行 map（数据转换），随后通过 `conflate()`（来不及处理时只保留最新值）与 `distinctUntilChanged()`（相邻结果相同时不再发送）控制更新。
- `NotificationIconContainerStatusBarViewBinder.bindWhileAttached()` 按 `displayId` 选择图标 View store，再绑定到 `NotificationIconContainer`。
- 默认屏复用通知处理流程保存的 status bar icon；辅助屏使用 `ConnectedDisplaysStatusBarNotificationIconViewStore`，按通知 key 缓存为目标 display context 创建的 `StatusBarIconView`。

`NICStatusBar#bindWhileAttached` 只覆盖绑定关系建立的过程。每次通知变化产生的帧耗时，仍要从 Flow（异步数据流）更新、View 容器变化、ViewRoot traversal 与 FrameTimeline 中观察。

右侧网络、电池、时钟和其他系统状态图标，仍由状态图标处理流程与 `StatusBarIconControllerImpl` 等组件管理。Android 17 还有 `status_bar_system_status_icons_in_compose` 开关，目标产品可能把部分区域迁到 Compose。排查大量通知同时到达的场景时，应把两类输入分开：

- 左侧压力来自通知集合和图标 View 增删；
- 右侧压力来自网络、电话、热点、隐私指示、OEM 扩展等状态变化；
- 两者可在同一状态栏窗口帧内叠加，但原因和限制更新频率的位置不同。

## 导航输入的两条路径

### 三按钮导航

`NavigationBarView.onInterceptTouchEvent()` 和 `onTouchEvent()` 把事件交给 `mTouchHandler`，按钮再触发 back、home、recents（返回、主页、最近任务）等行为。定位三按钮延迟时，时间线应包含：

`InputDispatcher` 投递 → `NavigationBarN` 窗口 UI 线程 → 按钮回调 → WM/Launcher 或目标 App 状态变化 → 导航栏反馈帧。

如果 Input 已送达，而按钮 pressed（按下状态）或动画迟到，应检查该窗口的 UI 线程和 ViewRoot。若按钮反馈及时、窗口切换迟到，则继续查看 WM Shell、Launcher 或目标 App，不能把整段延迟都归到 `NavigationBarView`。

### 边缘返回手势

Android 17 把 per-display（每块显示屏独立）的资源放到 `DisplayBackGestureHandlerImpl`。它为每个 display 创建 `InputMonitorCompat("edge-swipe", displayId)`，使用 `UiThreadContext` 的 looper（消息循环）与 Choreographer 建立 input receiver（输入接收器），并注册 system gesture exclusion listener（系统手势排除区域监听器）。

`EdgeBackGestureHandler` 保存多个 `DisplayBackGestureHandler`，处理跨 display 的共享状态和回调。

`edge_back_gesture_handler_thread` 开启时，`SysUIConcurrencyModule` 创建具有显示相关优先级的 `BackPanelUiThread`；关闭时，同一个 `UiThreadContext` 改用 SystemUI 主线程。由此得到两个诊断分支，外加一条后续检查：

- trace 中有 `BackPanelUiThread`：检查 input receiver、手势判定、Back Panel 绘制与该线程的 Choreographer；
- trace 没有该线程：检查 aconfig 值，并在 SystemUI 主线程寻找同一路径；
- 手势进入 back animation 后：继续看 WM Shell back transition、目标窗口与 SurfaceFlinger。

三按钮路径和边缘返回共享部分窗口管理结果，但输入入口不同。只搜索 `NavigationBarView`，会漏掉 gesture mode（手势导航模式）的 input monitor 和 Back Panel。

## 多显示、折叠屏与桌面窗口模式

Android 17 已具备 per-display status bar（每块显示屏独立状态栏）的基础设施。`StatusBarWindowControllerImpl` 持有 `mDisplayId`，辅助屏窗口标题带 display id；`MultiDisplayStatusBarWindowControllerStore` 按 display 提供 controller；通知图标 binder（绑定器）也接受 `displayId`。因此，不能再假设 StatusBar 只有一个实例。

这不表示每个 display 都一定创建状态栏。`DisplayContent.isSystemDecorationsSupported()` 会排除 VR 2D display 和不可信 display，再检查 display window settings（显示窗口设置）、`FLAG_SHOULD_SHOW_SYSTEM_DECORATIONS`，以及旧 display-content-mode 管理路径下的强制桌面条件。产品 flag、display 类型、信任属性和系统策略共同决定结果。

其他三个边界也要保持清楚：

- `NavigationBarControllerImpl` 用 `SparseArray<NavigationBar>` 按 display 管理导航栏，并通过 WMS（WindowManagerService，窗口管理服务）查询该 display 是否有 navigation bar/taskbar（导航栏/任务栏）。连接屏的 Taskbar 可能由 Launcher 管理，SystemUI 的 `TaskbarDelegate` 负责协调状态与回调。
- AOSP Shade 是 display-aware（能够识别不同显示屏）的单例主窗口，可以在 display 之间移动，或在 display 移除时重新挂到默认屏。不能从 per-display StatusBar 推导出“每块屏都有一套 NotificationShade”。
- 桌面任务布局、窗口装饰与转场主要属于 WM Shell desktop mode；桌面任务 View 和光标不能统称为 SystemUI 渲染内容。

多显示性能至少要分别记录：单屏折叠态、单屏展开态、外屏连接但休眠、双屏点亮、桌面窗口模式，以及导航栏与 Taskbar 两种界面形态。实验记录还要包含分辨率、刷新率、Layer 数、状态栏实例数和通知 Shade 所在 display。CPU、GPU、显存或 PSS 增幅只能根据同一设备上的对照数据得出。

## App 启动与 Overview 的参与者

一次从桌面或 Overview 启动 App，至少跨越以下参与者：

1. Launcher/Quickstep 接收点击或手势，更新 workspace（桌面工作区）、任务卡片或 Overview 状态。
2. system_server 的窗口管理核心创建并推进 transition（窗口过渡）。
3. WM Shell `Transitions` 接收 request/ready（请求/就绪）回调，选择 transition handler（过渡处理器），在 Shell main/animation executor 上推进动画。
4. `StartingWindowController` 调用 `StartingWindowTypeAlgorithm` 选择 snapshot（任务快照）、solid-color splash（纯色启动画面）、SplashScreen 或无起始窗口，并在 splashscreen executor 上创建或移除起始 Surface。
5. 目标 App 提交首批 buffer。
6. SystemUI 更新状态栏、导航栏、锁屏或 Shade 的相关状态。
7. SurfaceFlinger 合成 Launcher、starting window、目标 App 与系统栏，并交给 HWC 和显示设备呈现。

`Transitions.java` 在 Android 17 中保留 `dispatchRequest: <type>`、`playTransition: <type>` 与 `<Handler>#startAnimation animated <type>` 等 WM trace。`StartingWindowController` 同时使用 Shell main executor 和 splashscreen executor，因此不能把起始窗口工作全部算到 Shell main。

Overview 的 `RecentsView.applyLoadPlan()` 会增删、复用并绑定任务卡片，但该方法名本身不是稳定的 trace slice；源码中的方法与设备上实际出现的 trace 证据应分开说明。

Launcher 的包名和进程名受产品实现影响。AOSP 的参考实现是 Launcher3 Quickstep，Pixel 或 OEM 构建可能使用不同包名。应通过默认 HOME activity、进程 `cmdline` 和窗口 owner（所有者）找到当前宿主，不能只搜索固定的 `com.android.launcher3`。

## 把 SystemUI 放回标准渲染管线

SystemUI 的特殊之处在于窗口数量多、状态来源多，并且可以通过开关选择专用线程；HWUI 主路径仍遵循 Android 17 的标准时序：

`VSync` → Choreographer 的 `INPUT`、`ANIMATION`、`INSETS_ANIMATION`、`TRAVERSAL`、`COMMIT` 回调 → View/Compose 状态处理与 traversal → RenderThread/HWUI → BLAST buffer queue（窗口缓冲队列）→ SurfaceFlinger → HWC/present。

这条路径带来几条诊断约束：

- `doFrame` 很长只能说明 UI 线程在这一帧占用时间较多，不能直接等同于 layout 慢。
- `Traversal` 包含 measure/layout、绘制记录和向 RenderThread 同步等工作。其尾部的 `syncAndDrawFrame()` 可能等待 RenderThread 状态同步；后续阶段处理不及时造成的 backpressure（反压）也可能延长 traversal。
- Compose 的 recomposition、layout 和 draw 记录仍在对应窗口的 UI 线程；GPU 工作与 display 合成要到 RenderThread、SurfaceFlinger 和 HWC 中继续确认。
- `requestLayout` instant event 只说明请求已经发出，不能表示当场完成了一次 layout。
- App `SurfaceFrame` 使用 `surface_frame_token`，Display `DisplayFrame` 使用 `display_frame_token`。二者是不同命名空间，不能拿相同数值直接做关联。

### Perfetto 中的观察顺序

| 步骤 | 要回答的问题 | 主要轨道或证据 |
| --- | --- | --- |
| 确认呈现异常 | 哪个 display frame missed（错过截止时间），异常在 deadline 还是 present 环节 | FrameTimeline `DisplayFrame`、VSYNC、HWC |
| 找到受影响 Surface | 是 NotificationShade、StatusBar、NavigationBar、Launcher 还是目标 App | `SurfaceFrame`、SurfaceFlinger Layers、窗口 owner |
| 确认生产者线程 | 哪个进程和 ViewRoot 产生该 buffer | 目标进程 UI 线程、RenderThread、BLAST |
| 细分应用或系统 UI 工作 | 输入、动画、绑定、measure/layout、绘制记录中哪段变长 | slice、sched（调度）、binder、CPU frequency（频率） |
| 检查后续阶段的反压 | UI 是否等待 RenderThread，RenderThread 是否等待 GPU/buffer，SurfaceFlinger 是否错过合成 | `syncAndDrawFrame`、dequeue/queue（出队/入队）、fence、SurfaceFlinger/HWC |
| 回到源码 | trace 名对应哪个 Android 17 方法，目标 flag 是否选择该实现 | `android-17.0.0_r1` 源码、aflags、产品差异 |

下面的 Trace Processor SQL 用于列出 SystemUI 中三个已核对的通知列表 slice：

```sql
SELECT
  p.name AS process_name,
  t.name AS thread_name,
  s.ts,
  s.dur,
  s.name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE p.name GLOB '*systemui*'
  AND s.name IN (
    'NotificationShadeWindowView#onMeasure',
    'NotificationStackScrollLayout#onMeasure',
    'NSSL#updateChildren'
  )
ORDER BY s.ts;
```

查询结果只给出 slice 的线程耗时。还要在同一时间范围内核对 `SurfaceFrame`、`DisplayFrame`、RenderThread、SurfaceFlinger 与调度状态，才能判断这段 CPU 工作是否造成用户可见的 missed frame。

## 四类常见现场

### Shade 展开掉帧

先在 FrameTimeline 中选中 missed display frame，再定位 `NotificationShade` SurfaceFrame。随后检查当前窗口的 UI 线程：

- legacy 路径关注 `NotificationShadeWindowView#onMeasure`、NSSL measure 和 `NSSL#updateChildren`；
- Scene 路径还要加入 Compose recomposition/layout/draw、scene transition/CUJ、blur 请求；
- 两条路径都要检查 NSSL，因为 Android 17 Scene 仍保留 View 通知容器；
- UI 线程没有超过该帧可用时间时，继续查看 RenderThread、buffer queue、SurfaceFlinger 和 GPU。

若 NSSL measure 随通知总数增长，优化目标是减少参与测量的 row、内容形态和层级。若 `NSSL#updateChildren` 变长，应检查分组、heads-up、动画状态与同一帧中的更新次数。若 UI 与 RenderThread 都没有异常，而 display frame 仍然 miss，则继续检查 SurfaceFlinger/HWC、其他高层 Surface 或显示模式切换。

### 通知集中到达

应分别检查三组信号：`NotifInflation` worker、SystemUI 窗口 UI 线程，以及状态栏/NotificationShade 的 FrameTimeline。常见原因包括 worker 排队、图片预加载、异步 apply fallback、完成回调集中到达、row 批量挂接、图标批量变化和 NSSL 连续重新计算。

“主线程没有 `RemoteViews.apply()`”不能排除通知绑定。异步的主要工作本来就在 worker 上；用户可见的卡顿往往发生在任务完成后的 View 树更新阶段。反过来，worker 队列变长但没有影响可见帧，也不能直接判定它是 jank 的原因。

### 返回手势反馈迟缓

以 input event 到达 `edge-swipe` receiver 为起点，以 Back Panel 首帧或目标窗口 transition 为终点。若 `BackPanelUiThread` 存在，主线程上的通知工作不一定会直接阻塞箭头绘制；两条线程仍可能通过共享状态、WM 调用和合成资源相互影响。若 input receiver 很快、Back Panel 也按时出帧，只有窗口切换阶段变慢，就应检查 WM Shell 和目标 App。

### 启动动画不连贯

应把 Launcher、Shell、starting window、目标 App、SystemUI 和 SurfaceFlinger 的轨道放在同一时间范围内比较，并区分：

- Launcher 任务卡或 workspace 自身掉帧；
- Shell handler 选择或动画执行延迟；
- starting window 创建慢或移除时机不合适；
- 目标 App 首 buffer 晚；
- StatusBar/NavigationBar 同期更新超预算；
- SurfaceFlinger/HWC 合成或 present 延迟。

只看 SystemUI CPU 使用率的峰值，无法判断责任。只有当受影响的系统栏 SurfaceFrame 与其 UI/RenderThread 工作在时间上相互对应，才能把该帧归因到 SystemUI。

## OEM 差异的处理方式

厂商经常改动状态栏层级、QS、锁屏、通知模板、插件、模糊、动画和线程开关。AOSP 方法可以提供稳定的分析起点，但具体类名与 trace slice 仍可能变化。审查厂商实现时应保留三类证据：

- AOSP Android 17 的基准源码与 flag；
- 产品分支相对 AOSP 的 diff；
- 目标设备的窗口、线程、Layer、Perfetto 和日志。

文档结论也应带上适用条件。例如，“Scene path 的 NSSL 仍参与通知行布局”有 AOSP Android 17 源码直接支持；“某机型在 120 Hz 下展开通知面板时 blur 是瓶颈”需要该机型的对照 trace；“连接显示器后会创建第二个 StatusBar”还需要 display policy（显示策略）与运行时窗口列表证明。

## 实战检查清单

采集前：

- 记录 build fingerprint（系统构建指纹）、刷新率、分辨率、导航模式、折叠状态和外接屏状态。
- 保存相关 aconfig 值。
- 保存 `dumpsys window` 中三个系统栏窗口及 display id（显示屏标识）。
- 保存 SystemUI、Launcher、Shell 相关线程分别属于哪个进程。
- 固定通知集合、分组、图片和更新频率，控制温度与电源状态。

读 trace 时：

- 从 missed `DisplayFrame` 开始，找到对应的 Surface 和 owner。
- 区分 MainThread、专用窗口 UI 线程、`NotifInflation`、RenderThread 和 Shell executor。
- 将 `requestLayout` 当成触发信号，将 measure/layout/draw 与 `syncAndDrawFrame` 分开。
- 对照 legacy/Scene、View/Compose、三按钮/手势、单屏/多屏分支。
- 检查 CPU 调度、频率、binder、GPU、buffer queue、SurfaceFlinger/HWC，避免只凭一条 slice 判断责任。

形成结论时：

- 写明 Android 17 tag（源码版本标签）、产品分支、flag 和 display 条件。
- 给出 FrameTimeline 与线程 slice 的时间关系。
- 标明直接源码事实、trace 观察和工程推断。
- 优化后复测同一场景，并报告分位数、missed frame 类型和 thermal（温控）状态。

## 与其他章节的关系

- **§2.4 MainThread 与 RenderThread 协作**：介绍标准 HWUI、BLAST 与 SurfaceFlinger 的分工；SystemUI 还需检查专用 UI 线程。
- **§7.1 卡顿的定义与分类**：SystemUI 仍需从 FrameTimeline 的用户可见帧开始判断责任。
- **§7.2 典型卡顿场景**：Shade、导航、启动和 Overview 的现象，需要结合这里的窗口与组件边界进一步分析。
- **§13.2 Perfetto View 解读**：线程、FrameTimeline、Layer 和 SQL 操作可参考该章。

## Android 17 源码与官方资料

- AOSP [`systemui.aconfig`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/aconfig/systemui.aconfig)
- AOSP [`super_notification_shade.xml`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/res/layout/super_notification_shade.xml)
- AOSP [`scene_window_root.xml`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/res/layout/scene_window_root.xml)
- AOSP [`ShadeViewProviderModule.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/shade/ShadeViewProviderModule.kt)
- AOSP [`ShadeWindowLayoutParams.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/shade/ShadeWindowLayoutParams.kt)
- AOSP [`NotificationShadeWindowView.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/shade/NotificationShadeWindowView.java)
- AOSP [`SceneContainerFlag.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/scene/shared/flag/SceneContainerFlag.kt)
- AOSP [`SceneContainerFrameworkModule.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/scene/SceneContainerFrameworkModule.kt)
- AOSP [`SceneWindowRootViewBinder.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/scene/ui/view/SceneWindowRootViewBinder.kt)
- AOSP [`NotificationStackScrollLayout.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/statusbar/notification/stack/NotificationStackScrollLayout.java)
- AOSP [`NotificationRowContentBinderImpl.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/statusbar/notification/row/NotificationRowContentBinderImpl.kt)
- AOSP [`NotificationIconContainerStatusBarViewBinder.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/statusbar/notification/icon/ui/viewbinder/NotificationIconContainerStatusBarViewBinder.kt)
- AOSP [`StatusBarWindowControllerImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/statusbar/window/StatusBarWindowControllerImpl.java)
- AOSP [`NavigationBarControllerImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/navigationbar/NavigationBarControllerImpl.java)
- AOSP [`DisplayBackGestureHandler.kt`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/DisplayBackGestureHandler.kt)
- AOSP [`DisplayContent.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/DisplayContent.java)
- AOSP [`Transitions.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/transition/Transitions.java)
- AOSP [`StartingWindowController.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java)
- AOSP Launcher3 [`RecentsView.java`](https://android.googlesource.com/platform/packages/apps/Launcher3/+/android-17.0.0_r1/quickstep/src/com/android/quickstep/views/RecentsView.java)
- Android Open Source Project：[读取和修改 aconfig flag](https://source.android.com/docs/setup/build/feature-flagging/flip-a-flag)
- Android Developers：[通知概览](https://developer.android.com/develop/ui/views/notifications)
- Android Developers：[SplashScreen API](https://developer.android.com/develop/ui/views/launch/splash-screen)
