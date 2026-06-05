---


title: SystemUI 性能分析
chapter: '7.13'
section: '7.13'
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags:
- systemui
- jank
- launcher
- statusbar
- navigationbar
- notification-shade
- perfetto
related_chapters:
- '2.4'
- '2.5'
- '7.1'
- '7.3'
- '7.4'
- '13.3'
created_by: task2a-knowledge-gap
created_date: '2026-04-09'
drafted_date: '2026-04-09'
drafted_by: openclaw-task2a
gap_source: AOSP结构+读者需求+素材驱动
gap_score: 18
confidence: medium
last_verified: "2026-04-26"
last_verified_against: "AOSP android-16.0.0_r1 SystemUI SceneContainerFlag / SceneContainer / SceneTransitionLayout / ContainerReveal；PunchHole.kt 未作为 android-16.0.0_r1 锚点"
sources:
- type: aosp
  path: frameworks/base/packages/SystemUI/res/layout/super_notification_shade.xml
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/shade/NotificationShadeWindowView.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/stack/NotificationStackScrollLayout.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/collection/NotifInflaterImpl.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/collection/inflation/NotificationRowBinderImpl.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/row/NotificationContentInflater.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/phone/StatusBarNotificationPresenter.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/icon/ui/viewmodel/NotificationIconContainerStatusBarViewModel.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/icon/ui/viewbinder/NotificationIconContainerStatusBarViewBinder.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/phone/ui/StatusBarIconControllerImpl.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/views/NavigationBarView.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java
- type: aosp
  path: frameworks/base/packages/SystemUI/src/com/android/systemui/scene/shared/flag/SceneContainerFlag.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/compose/features/src/com/android/systemui/scene/ui/composable/SceneContainer.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/SceneTransitionLayout.kt
- type: aosp
  path: frameworks/base/packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/reveal/ContainerReveal.kt
- type: aosp
  path: frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java
- type: aosp
  path: frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/transition/Transitions.java
- type: aosp
  path: packages/apps/Launcher3/quickstep/src/com/android/quickstep/views/RecentsView.java
- type: official
  path: https://developer.android.com/develop/ui/views/notifications
- type: official
  path: https://developer.android.com/guide/topics/ui/splash-screen
pipeline_stage: task6_pending
finalized_date: '2026-04-29'
finalized_by: openclaw-task6-auto-promote
task6_state: revisiting
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
reviewed_by: "openclaw-task6"
reviewed_date: 2026-06-04
last_task6_audit: "2026-05-21"
task6_result: "pass-light-edit"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-05"
last_task9_at: "2026-06-05T18:32:25+08:00"
last_task2b_at: "2026-06-04T14:54:52+08:00"
last_task9_audit: "2026-05-21"
last_task9_audit_at: "2026-05-21T17:28:40+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-21-17-audit.md"
last_task9_review_log: "logs/deep-review/2026-06-05-18-deep-review.md"
task9_review_notes: "2026-06-05 Task9 深度复审 AUTO-FIX: 将 Flexiglass/SceneContainer 旧主线锚点收敛到 android-16.0.0_r1；移除未量化的默认视觉特效与内存增幅结论；Foldable 多 Display 性能影响改为需设备基线验证。回到 Task6 复审。"
last_task2b_by: openclaw-task2b-main
task2b_fix_summary: "2026-06-04 Task2B main: P0 SystemUI multi-display source anchors corrected (NavigationBarController path/SparseArray, DisplayContent.isSystemDecorationsSupported, TaskbarDelegate wallpaper visibility, DesktopTasksController et al.); P1 version coverage updated for Android 12-16 desktop windowing branch; unverified CPU/Mem growth claims downgraded."
last_task6_at: "2026-06-04T15:21:59.742576+08:00"
task6_reviewed_date: 2026-06-04
task6_reviewed_by: "openclaw-task6"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 1
task6_review_notes: "2026-06-04 Task6 revisiting review: pass-light-edit。L1 小修 1 处（形容词+冒号起手式 1）。L3 问题单 1 条（Foldable 多 Display 附录未融入主叙述）。"
last_task9_autofix_at: "2026-06-05"
p0: 0
p1: 1
p2: 3
---

# 7.13 SystemUI 性能分析

前面几节讨论的重点是普通 App 进程里的卡顿。到了 SystemUI，问题会换一种形态。状态栏、通知抽屉、导航栏、Overview 转场几乎天天在用户眼前出现，一旦掉帧，体感会比单个 App 的局部卡顿更刺眼。

本节只讨论 Android 12-17 的现行实现。这个范围里，StatusBar、Notification Shade、NavigationBar 仍在 `com.android.systemui` 进程，Recents / Overview 已经放在 Launcher3 Quickstep。把 Overview 继续算进 SystemUI，会把进程边界、窗口归属和 Perfetto 观察点一起带偏。

[图：Perfetto 进程视图概览。上半部分标出 `com.android.systemui` 的 MainThread、RenderThread、`NotificationShadeWindowView#onMeasure`；下半部分标出 `com.android.launcher3` 的 MainThread、RenderThread 和 Overview 相关 slice。用于区分 SystemUI 与 Launcher3 Quickstep 的职责边界。]

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **Android 12-17 的组件边界**：SystemUI 负责 StatusBar / Notification Shade / NavigationBar，Overview 属于 Launcher3 Quickstep。
- 🔹 **窗口拓扑**：`super_notification_shade.xml` 把 `status_bar_expanded` 放进 `NotificationShadeWindowView`，NavigationBar 才是稳定独立窗口。
- 🔹 **通知更新与内容绑定**：通知内容绑定在 Android 12-17 已经转向异步 apply / reapply；左侧通知图标则要区分 Android 12-14 的 presenter/controller 入口和 Android 15+ 的 icon/ui 路线。
- 🔹 **输入路径拆分**：三按钮导航看 `NavigationBarView`，手势返回看 `EdgeBackGestureHandler + InputMonitorCompat("edge-swipe")`。
- 🔹 **启动转场观察法**：Launcher3 Quickstep、WM Shell `Transitions`、`StartingWindowController`、目标 App 第一帧、SurfaceFlinger 要一起看。
- 🔹 **Perfetto 定位方法**：优先确认窗口归属、MainThread/RenderThread、SurfaceFlinger Layers，再回到具体源码锚点。

### 扩展（可选深入）

- 🔸 **通知负载形态**：普通模板、自定义 `RemoteViews`、大图通知对 SystemUI 的压力差异。
- 🔸 **OEM 定制变量**：状态栏层级、主题动画、插件体系会放大 AOSP 基线之外的开销。
<!-- outline-end -->

## Android 15+ SceneContainer (Flexiglass)：通知栏架构的 Compose 化重构

> ⚠️ **状态**：此部分描述的 Flexiglass / Scene Framework 截至 Android 15/16 开发阶段仍为**实验性功能**，默认关闭。不同分支可能通过 aconfig、device_config override 或工程编译开关打开；验证时以目标构建上的 flag dump 和对应 AOSP 分支为准，不要只按一个 `device_config.get_boolean(...)` 判断。以下内容已按 AOSP android-16.0.0_r1 源码核对，适用于已启用该框架的 Android 15/16 设备；Android 17 需要按目标分支重新核对 flag 和路径。

### 核心变化：从重叠 View 层级到 Scene Graph

传统 SystemUI 的通知栏基于 `NotificationShadeWindowView`（一个超大 `FrameLayout`），锁屏、通知列表、Quick Settings 都通过 `setVisibility()` 在同一个 View Tree 中切换。这种架构的问题在于：状态逻辑分散、动画与 UI 声明耦合、OEM 定制困难。

Flexiglass（内部代号，亦称 Scene Framework）将通知栏、锁屏、Bouncer、Quick Settings 各自封装为独立的 **Scene**，通过 **SceneTransitionLayout** 统一管理场景切换和过渡动画。

**核心概念对照：**

| 传统架构 | Flexiglass |
|----------|------------|
| `NotificationShadeWindowView`（单一重叠 ViewTree） | `SceneContainer`（Scene Graph 根节点） |
| `setVisibility()` 控制显隐 | `SceneKey` 切换当前活跃 Scene |
| 动画逻辑散落在 `PanelView.onTouchEvent()` 等各处 | `SceneContainerTransitions` 集中声明过渡动画 |
| View 层级直接对应 UI 结构 | Scene 是独立 Composable，互不直接引用 |
| `ScrimController` 控制 Scrim 透明度 | SceneTransitionLayout 内置 Element 动画系统 |

### 源码文件索引

| 文件路径（AOSP android-16.0.0_r1） | 职责 |
|---------------------------|------|
| `packages/SystemUI/compose/features/src/com/android/systemui/scene/ui/composable/SceneContainer.kt` | Scene Graph 根 Composable，接收 scene / overlay / transition / data source 等配置 |
| `packages/SystemUI/src/com/android/systemui/scene/shared/flag/SceneContainerFlag.kt` | 框架总开关，封装 aconfig 主开关与 secondary flags 依赖 |
| `packages/SystemUI/src/com/android/systemui/scene/ui/viewmodel/SceneContainerViewModel.kt` | 控制场景的 `isVisible` 状态 |
| `packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/SceneTransitionLayout.kt` | 底层 Compose 过渡组件，封装 Scene Graph 和 Transition |
| `packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/SceneTransitionLayoutState.kt` | 管理当前 Scene（`currentScene: SceneKey`）、`transitions`、`transitionState` |
| `packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/SceneTransitions.kt` | 集中声明每对 Scene 之间的过渡动画（如 `lockscreenToShadeTransition`） |
| `packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/reveal/ContainerReveal.kt` | AOSP android-16.0.0_r1 可核对的 reveal 相关实现入口，用于容器揭示类过渡效果 |
| `packages/SystemUI/compose/scene/src/com/android/compose/animation/scene/transformation/` | 现有基础变换集合，例如 anchored、translate、fade、scale 等；不要把不存在的 `PunchHole.kt` 写成 android-16.0.0_r1 锚点 |

### 源码入口与开关依赖

`SceneContainer` 是 Scene Graph 的 Compose 根节点。AOSP android-16.0.0_r1 的参数级签名仍在变化，正文只保留可核对的入参分组，避免把某个开发分支的签名写成稳定 API：

| 入参分组 | 用途 |
| --- | --- |
| `sceneByKey: Map<SceneKey, Scene>` | 注册可切换的 Scene 实例 |
| `overlayByKey: Map<OverlayKey, Overlay>` | 注册浮层与临时覆盖层 |
| `initialSceneKey` | 指定初始活跃 Scene |
| `sceneTransitions` | 声明 Scene 之间的过渡规则 |
| `dataSourceDelegator` / `qsSceneAdapter` | 连接 SystemUI 现有状态源与 QS 适配层 |
| `modifier` 等 Compose 参数 | 控制布局、绘制和外部修饰 |

`SceneContainerFlag.kt` 不直接读取单个 `device_config.get_boolean("systemui", "com.android.systemui.scene_container", false)`。AOSP android-16.0.0_r1 使用 aconfig 生成的 `Flags.sceneContainer()` 作为主开关，并要求一组 secondary flags 同时满足，例如 Keyguard bottom area refactor、Keyguard WM state refactor、migrate clocks to blueprint、notification throttle HUN、predictive back SystemUI flag。读源码时应把它看成“主开关 + 依赖开关”的组合；单个布尔值不足以判断该框架生效。

引用这个开关的组件包括 Scrim、QS、Keyguard、Overview latency tracking、锁屏滚动手势等分支。定位 Flexiglass 是否生效时，先核对这些依赖开关，再看对应组件是否切到了 SceneContainer 路径。

### 过渡动画机制

每个 Scene 切换的动画在 `SceneTransitions` 中声明，而非写在 Composable 函数体内：

```kotlin
// 示意（SceneContainerTransitions.kt）
val lockscreenToShadeTransition = transitionBuilder(
    fromScene = SceneKey.Lockscreen,
    toScene = SceneKey.Shade,
) {
    // tween 插值，300ms，FastOutSlowIn
    // 标签为 ElementKey 的元素同步位移
    element(elementKey) { translateY(it) }
}
```

AOSP android-16.0.0_r1 当前可核对的相邻实现是 `scene/reveal/ContainerReveal.kt` 和 `transformation/` 目录下的 anchored、translate、fade、scale 等基础变换。正文不能再把 `PunchHole.kt` 或 `SceneTransitions.kt` 里的 punchHole 符号写成 android-16.0.0_r1 已验证路径；如果目标厂商分支或历史分支存在类似 punch-hole 效果，需要在引用处标出具体分支或 commit。

### Flexiglass 对性能分析的影响

1. **Trace 观测变化**：`NotificationShadeWindowView#onMeasure` 在 Flexiglass 启用后权重下降。此时更该看 `SceneTransitionLayout` 相关的 Compose recomposition、layout / draw 记录和 animation slice。

2. **UI thread 与 RenderThread 分工**：`SceneTransitionLayout` 是 Compose 组件。Scene 切换会在 UI thread 上触发状态读取、recomposition、layout / draw 记录；进入 RenderNode / GPU 的属性动画和合成阶段才更多落到 RenderThread / GPU。没有 trace 证据时，不应把整段过渡写成“不会阻塞 UI thread”。

3. **OEM 定制影响**：Scene 独立性使 OEM 更容易替换或移除单个场景，但同时要理解 SceneGraph 的根节点结构和过渡声明方式才能正确定制。

4. **Perfetto 追踪重点**：启用 Flexiglass 后，分析 Shade 展开要同时看 `com.android.systemui` UI thread 上的 Compose recomposition、layout / draw slice，RenderThread 上的动画提交，以及 SurfaceFlinger Layers。`NotificationShadeWindowView#onMeasure` 只是入口之一；兼容层、旧 View 容器和 OEM 插件仍可能参与 traversal。

5. **窗口层边界**：Flexiglass 改的是 SystemUI 内部 UI 组织方式，SurfaceFlinger 侧通常仍落在 `NotificationShade` 对应的大窗口上。做窗口数量、Layer 顺序或 fence 分析时，先定位 `NotificationShade` surface，再回到 SystemUI 主线程关联 Compose / Scene 相关 slice。

<!-- AIW-源码调研-2026-04-24 -->


## 先分清谁负责什么

SystemUI 不是“所有系统 UI 的总包”。在 Android 12-17 里，SystemUI 更接近一组常驻窗口和控制器：状态栏、通知抽屉、锁屏相关视图、导航栏，以及围绕这些窗口的动画、输入、通知绑定过程。Overview / Recents 已经在 Launcher3 Quickstep 侧实现，本章分析 App 启动或最近任务切换时，至少要同时观察 `com.android.systemui`、`com.android.launcher3`、目标 App、SurfaceFlinger，有时还要把 WM Shell 单独拎出来看。

这个边界直接决定排查顺序。通知抽屉掉帧，优先看 SystemUI。最近任务切换掉帧，Launcher3 Quickstep 和 WM Shell 往往比 SystemUI 更靠近根因。把问题一股脑归到 SystemUI，后面的 Trace 会很难读。

### Android 16 桌面模式：SystemUI 的双重角色

Android 16 引入了原生桌面窗口管理（Desktop Windowing）。在此模式下，SystemUI 不再只负责手机端单一的状态栏和通知——它需要同时渲染外部显示器的任务栏（Taskbar）、多桌面视图以及通用光标（Universal Cursor）。

WM Shell 的 desktop mode 组件（当前可核对锚点为 `DesktopTasksController.kt`、`DesktopDisplayEventHandler.kt`、`DesktopRepository.kt`、`DesktopMode.java`）与 SystemUI 频繁交互。连接外部显示器时，SystemUI 进程可能出现 CPU 和显存增长——具体幅度取决于设备、分辨率和同时渲染的桌面节点数量，缺少 Perfetto trace 或设备基线时不写成固定阶跃数据。在做性能基线和 Trace 分析时，需要区分两个场景：

- **手机单屏模式**：SystemUI 的角色与传统 Android 一致，承担状态栏、通知、导航栏
- **桌面模式**：SystemUI 额外承担 Taskbar 渲染、桌面切换动画、光标绘制，与 WM Shell 的交互频率大幅上升

排查 SystemUI 性能问题时，如果设备处于桌面模式，Perfetto 中 SystemUI 进程的 CPU 和内存基线应单独建基，不能直接与单屏模式的数据对比。桌面模式下 CPU 和显存的增长量属于待验证范围——目前没有公开的 Perfetto trace 或设备基线能支撑具体数值，建议在目标设备上单独采集后再写入结论。

## 窗口拓扑不要先入为主

旧资料常把 StatusBar、NavigationBar、Notification Shade 写成三个彼此独立的 Surface。这种写法放到 Android 12-17 已经不稳。`super_notification_shade.xml` 里，`status_bar_expanded` 就在 `NotificationShadeWindowView` 下面，状态栏展开态和 Shade 本来就在同一个大窗口里；稳定独立的窗口主要是 NavigationBar。

因此，Perfetto 里更可靠的理解框架是两层：

- `NotificationShadeWindowView` 负责状态栏展开态、通知抽屉、锁屏相关容器。
- NavigationBar 作为单独窗口存在，三按钮模式和手势模式共用一套窗口框架，但输入处理过程不同。

读 Layers Track 时，不要先假设一定能看到三个名字固定的 layer。更稳妥的做法是先从 WindowManager / SurfaceFlinger 中找到 `NotificationShade` 和 `NavigationBar` 相关窗口，再回头检查 `com.android.systemui` 主线程上的 `NotificationShadeWindowView#onMeasure`、`NotificationStackScrollLayout#onMeasure` 这些 slice。

## StatusBar 与通知更新，源码入口要按版本分代看

### 左侧通知图标：Android 12-14 和 Android 15+ 不是同一套入口

这一段最容易被 Android 15+/16 的新路径带偏。`statusbar/notification/icon/ui/` 目录下的 `NotificationIconContainerStatusBarViewModel` 和 `NotificationIconContainerStatusBarViewBinder` 只适合 Android 15+ / 16 当前主线。Android 12-14 读源码时，更稳的入口仍是 `StatusBarNotificationPresenter` 这一代控制链，再沿着状态栏图标更新逻辑继续查。

- Android 12-14：先看 `StatusBarNotificationPresenter`，再结合 `StatusBarIconControllerImpl` 和状态栏容器遍历判断通知图标更新是否把主线程拖长。
- Android 15+ / 16：看 `NotificationIconContainerStatusBarViewModel.icons`、`NotificationIconContainerStatusBarViewBinder.bindWhileAttached()` 和 `StatusBarNotificationIconViewStore`，重点放在图标集合变化后的重绑、重测量、重布局。
- 两代实现的共同观察点没有变：图标批量增删之后，状态栏容器有没有反复 traversal。

这样分开写，Android 12-14 读者不会去找 15+ 才出现的 ViewModel/Binder，Android 15+ 读者也不会被旧版 presenter/controller 路径拖回去。

### 右侧系统图标：仍由 `StatusBarIconControllerImpl` 一类控制器管理

右侧信号、电池、时钟这组系统图标仍有 `StatusBarIconControllerImpl` 这类控制器。它们和左侧通知图标不是一回事。把两边混在一起，会把“通知洪峰导致的重绑开销”和“系统状态变化导致的图标刷新”写成同一类问题。

工程上更常见的情况是两种压力叠加：左侧在做通知图标增删，右侧还有网络指示器、热点、蓝牙等状态跳动，结果都压到同一个状态栏容器的遍历里。OEM 再叠几层自定义 View，主线程时间就不够用了。

## 通知内容绑定，主路径已经是异步 apply / reapply

把通知内容绑定写成 `NotificationEntryManager + NotificationInflater + 主线程 RemoteViews.apply()`，会把现在的 SystemUI 讲回旧时代。Android 16 当前实现更接近下面这个过程：

- `NotifInflaterImpl.inflateViews()` 负责把一次内容绑定交给 row binder。
- `NotificationRowBinderImpl` 把 entry、row 和绑定参数组织起来。
- `NotificationContentInflater` 创建 `AsyncInflationTask`，并在常规路径上通过 executor 执行。
- 真正应用 `RemoteViews` 时，优先走 `applyAsync()` / `reapplyAsync()`；只有 `inflateSynchronously` 测试路径或异步失败后的兜底才会回到同步 apply。

Android 14+ / 16 当前主线里，`NotificationContentInflater` 通过构造函数接收 `@NotifInflation Executor`，`AsyncInflationTask` 统一走这个 executor，避免每条通知各自开散乱线程。通知洪峰到来时，并发 inflate 会被集中调度；这能避免 I/O、图片预加载和 RemoteViews 解析同时把 CPU 撑满。

这段差异决定了 Perfetto 的观察方式。排查通知更新卡顿时，不要只盯主线程是否直接卡在 `RemoteViews.apply()`；更常见的情况是异步绑定已经启动，但主线程仍要承担 View 树重新挂接、测量、布局、动画回调，结果首帧或展开帧超预算。可观察的 slice 包括 `NotificationContentInflater.AsyncInflationTask#doInBackground`、主线程 `applyAsync` 回调以及后续 traversal。

大图通知也别写成固定数字。`BigPictureStyle` 的图片解码、像素拷贝、上传 GPU 是否会拖慢一帧，取决于图片尺寸、压缩格式、Hardware Bitmap 策略、热路径还是冷路径。这里给定值很容易误导，工程上应该把它写成条件化结论。

## 导航输入要拆成两条路径

### 三按钮导航

三按钮模式更接近传统 View 输入。`NavigationBarView` 自己实现了 `onInterceptTouchEvent()` 和 `onTouchEvent()`，内部把事件交给 `mTouchHandler`，再分发给 back/home/recents 这些按钮。排查这一路时，关注点是：事件有没有及时进入导航栏窗口，按钮点击后的主线程处理有没有被其他 UI 工作压住。

### 手势导航

手势返回不是把同样的事件再走一遍 `NavigationBarView`。当前实现里，`EdgeBackGestureHandler` 会创建 `InputMonitorCompat("edge-swipe")`，再通过 `getInputReceiver(..., this::onInputEvent)` 接收边缘手势输入。它还会向 WindowManager 注册 system gesture exclusion listener，用来处理应用的手势排除区域。

所以，手势延迟和三按钮延迟的排查入口不同：

- 三按钮导航，先看导航栏窗口和 `NavigationBarView` 的触摸处理。
- 手势返回，先看 `edge-swipe` 这条 input monitor、`EdgeBackGestureHandler`、back animation 相关 slice，再看 SystemUI 主线程是否被别的工作拖慢。

当前证据只够支持“手势路径独立于三按钮按钮点击路径”，不够支持更大的版本结论。

[图：同一份 Perfetto 中并排标出两条输入路径。左侧是三按钮导航，标注 `NavigationBarView` 所在窗口与主线程 slice；右侧是手势返回，标注 `edge-swipe` input monitor、`EdgeBackGestureHandler`、back animation 相关 slice。]

## App 启动转场，要把 Launcher3、WM Shell、StartingWindow 放到一张图里

SystemUI 和 Launcher3 在启动动画里确实要协作，但中间不能跳过 WM Shell。Android 12-17 的实际流程是：

1. Launcher3 Quickstep 接收点击或手势，发起启动请求。
2. WM Shell `Transitions` 接管窗口转场，安排过渡动画。
3. `StartingWindowController` 决定起始窗口 / SplashScreen 何时出现、何时让位给目标 App 第一帧。
4. 目标 App 画出首帧。
5. SurfaceFlinger 合成 Launcher、StartingWindow、目标 App，以及仍然悬在顶部的系统栏。

这个过程里，SystemUI 不该被写成“system_server 通知一下就结束”。它在系统栏层级、通知头部状态、锁屏切换场景里仍会参与画面组织；但转场的调度中枢已经明显偏向 Quickstep + WM Shell。

Overview 侧的源码锚点可以先看 `RecentsView.applyLoadPlan()`。它不等于一个稳定的 Trace tag，但足够告诉我们：最近任务切换时，Launcher3 自己也在做任务列表加载和视图更新，不能把所有掉帧都算到 SystemUI 头上。

[图：Launcher3 Quickstep、WM Shell `Transitions`、`StartingWindowController`、目标 App 首帧、SurfaceFlinger Layers 的联合 Trace。标出 StartingWindow 出现、App 首帧提交、Launcher layer 退出的先后关系。]

## Perfetto 里先看哪些 Track

把“关键 Trace 点”写成一串未经核对的 event 名很危险。更稳妥的写法是“先看哪条 Track，再用哪个源码锚点核对”。下面这张表只保留已经能在当前 AOSP 源码里对上的项。

| 场景 | Perfetto 先看哪里 | 源码锚点 | 正常表现 | 异常表现 |
| --- | --- | --- | --- | --- |
| Shade 展开 / 收起 | `com.android.systemui` MainThread、RenderThread、SurfaceFlinger Layers | `NotificationShadeWindowView#onMeasure`、`NotificationStackScrollLayout#onMeasure`、`NSSL#updateChildren` | 主线程 slice 跟手指移动同步，Layers 变化连续 | `onMeasure` 或 `NSSL#updateChildren` 长时间占用，SurfaceFlinger 合成出现空洞 |
| 通知内容绑定 | `com.android.systemui` MainThread + 绑定相关异步任务 | `NotifInflaterImpl`、`NotificationContentInflater.AsyncInflationTask`、`applyAsync()` / `reapplyAsync()` | 异步绑定启动后，主线程只承担有限的挂接和布局工作 | 异步任务堆积，或异步完成后主线程再被批量 requestLayout 压住 |
| 状态栏通知图标更新 | `com.android.systemui` MainThread、ViewRootImpl traversal | `Android 12-14: StatusBarNotificationPresenter`；`Android 15+: NotificationIconContainerStatusBarViewModel.icons`、`NotificationIconContainerStatusBarViewBinder.bindWhileAttached()` | 版本对应的源码入口清楚，图标增删量小，状态栏遍历时间稳定 | 读错版本入口，或图标批量变更后状态栏容器反复测量、布局 |
| 三按钮导航点击 | `com.android.systemui` MainThread、Input 轨道 | `NavigationBarView.onInterceptTouchEvent()`、`onTouchEvent()` | 触摸到按钮反馈间隔稳定 | Input 到达后，主线程被别的窗口工作阻塞 |
| 手势返回 | Input 轨道、`com.android.systemui` MainThread | `EdgeBackGestureHandler`、`InputMonitorCompat("edge-swipe")` | 边缘滑动、back animation、窗口切换时间靠得很紧 | input receiver 已收到事件，但手势判定或动画回调滞后 |
| Overview / 最近任务 | `com.android.launcher3` MainThread、RenderThread、SurfaceFlinger Layers | `RecentsView.applyLoadPlan()` | Launcher 与 SurfaceFlinger 时间分布平稳 | Launcher 自己的视图更新过重，和系统栏动画一起争 CPU |

## 常见卡顿形态与排查办法

### Notification Shade 展开不顺

这类问题先检查 `NotificationShadeWindowView#onMeasure` 和 `NotificationStackScrollLayout#onMeasure`。如果这两段 slice 在展开阶段持续拉长，根因通常在通知数量、分组样式、OEM 附加层级，或者展开动画里混入了别的状态更新。再往下一层看 RenderThread 和 Layers Track，确认是主线程布局过重，还是大窗口变化把合成也拖慢了。

### 通知洪峰把状态栏和抽屉一起拖慢

用户经常只感知到“通知一来，整个上半屏都变钝了”。排查时要把图标更新和内容绑定分开。图标更新偏状态栏容器遍历，内容绑定偏 `RemoteViews` 异步应用后的挂接与重排。两者如果在同一时间片叠到一起，体感会非常像“SystemUI 主线程突然卡死了一下”。

### Launcher3 与 SystemUI 同时忙

App 启动、Overview 切换、返回桌面都可能碰到这个形态。Launcher3 正在做任务视图更新，SystemUI 还在处理通知、状态栏或导航栏动画，WM Shell 又在安排转场，结果多个进程一起抢 CPU。此时单看某一个进程通常得不出结论，要把 Launcher3、SystemUI、目标 App、SurfaceFlinger 摆在同一段时间轴上读。

### 输入已经到了，反馈还是慢

这类问题常见于导航手势。Input 轨道已经把事件送到 SystemUI，`EdgeBackGestureHandler` 也收到了输入，但主线程后面跟着一串通知更新、布局遍历或动画回调，反馈还是晚了。三按钮导航也会遇到类似情况，不过入口更接近 `NavigationBarView` 自己的触摸处理。

## 优化动作要和观察信号一一对应

### 看到 `NotificationShadeWindowView#onMeasure` / `NotificationStackScrollLayout#onMeasure` 过长

优先收缩通知抽屉里的层级和工作量。减少一次展开需要同时参与布局的通知数量，检查分组样式、锁屏插件、OEM 装饰 View。优化目标：减少单帧里要测量和摆放的节点数。

### 看到通知内容绑定频繁重做

先查 App 侧通知更新策略。高频 `notify()`、频繁更换自定义 `RemoteViews`、大图通知反复刷新，都会把 SystemUI 推进无效重绑。App 侧能做的动作包括降低更新频率、复用通知模板、避免把大图刷新做成秒级任务。SystemUI 侧则要确认异步 apply / reapply 没被同步兜底和失败回退拖回主线程。

### 看到状态栏图标容器反复遍历

把左侧通知图标和右侧系统图标分开限流。通知图标的变化频率高，优先从通知筛选和容器重绑下手；系统图标的变化频率通常低，重点在 OEM 定制是否额外引入了网速指示、运营商文本、动态装饰图标之类的附加负担。

### 看到 Launcher3、WM Shell、SystemUI 在同一时间片一起抬头

这里别急着在某一边做局部微调。先确定谁占了最长时间，再决定是减 Launcher3 的视图工作、减 SystemUI 的通知/系统栏压力，还是优化转场动画本身。启动与 Overview 场景里，错把协作问题当成单进程问题，往往会反复返工。

### 看到手势事件到了但回馈慢

把输入路径和 UI 路径拆开。Input monitor 已经收到了事件，问题多半不在“手势没识别到”，而在识别后的主线程处理、back animation 回调、窗口转场调度。这个时候继续盯 `NavigationBarView` 反而会浪费时间。

### 模糊与弹簧动画特效过载

如果目标构建在 Flexiglass / SceneContainer 路径上启用了实时模糊、弹簧动画等视觉效果，120Hz 下的大面积模糊可能把 RenderThread 的 `DrawFrame` 拉长；折叠屏展开态因绘制面积更大，需要用目标设备 trace 验证，不能直接写成默认瓶颈。

排查方法：

```bash
# 临时禁用模糊视觉反馈，验证是否是模糊导致的瓶颈
adb shell setprop debug.hwui.disable_blur_visual_feedback 1
```

如果在禁用模糊后掉帧消失或明显减少，实时模糊就是候选瓶颈。优化方向包括：缩小模糊区域、降低模糊半径、用预渲染的静态模糊图替代实时计算。

### Compose 化后的内存基线偏移

启用 Compose / Flexiglass 路径后，SystemUI 的内存基线可能相对传统 View 路径上移。做内存分析时需要注意：这不一定是泄露，也可能来自 SlotTable、Recomposition 记录、Compose Node 树和 SceneContainer 状态管理。当前章节没有公开 trace / PSS 基线支撑固定百分比，不能写成固定增幅。

排查 SystemUI 内存问题时，先确认设备版本和 Flexiglass 是否启用，再建立对应版本的基线。直接用 Android 14 及以下的 SystemUI PSS 数据作为对比基线，会把架构差异误判为泄露。

## 与其他章节的关系

- **§2.5 MainThread 与 RenderThread 协作**：SystemUI 的主线程与 RenderThread 分工和普通 App 一样，但窗口更多，动画协作也更复杂。
- **§7.1 卡顿的定义与分类**：本节的掉帧形态仍然可以落回主线程、RenderThread、SurfaceFlinger 三类基本框架。
- **§7.4 典型卡顿场景**：通知栏展开、启动转场、导航手势在那一节是现象层，本节补的是 SystemUI / Launcher / WM Shell 的责任边界。
- **§13.3 Perfetto View 解读**：本节的方法默认读者已经能熟练切进程、切线程、切 Layers Track。

## 参考资料

- AOSP：`packages/SystemUI/res/layout/super_notification_shade.xml`
- AOSP：`packages/SystemUI/src/com/android/systemui/shade/NotificationShadeWindowView.java`
- AOSP：`packages/SystemUI/src/com/android/systemui/statusbar/notification/stack/NotificationStackScrollLayout.java`
- AOSP：`packages/SystemUI/src/com/android/systemui/statusbar/notification/collection/NotifInflaterImpl.java`
- AOSP：`packages/SystemUI/src/com/android/systemui/statusbar/notification/row/NotificationContentInflater.java`
- AOSP：`packages/SystemUI/src/com/android/systemui/statusbar/phone/StatusBarNotificationPresenter.java`
- AOSP：`packages/SystemUI/src/com/android/systemui/navigationbar/views/NavigationBarView.java`
- AOSP：`packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java`
- AOSP：`libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java`
- AOSP：`libs/WindowManager/Shell/src/com/android/wm/shell/transition/Transitions.java`
- AOSP：`packages/apps/Launcher3/quickstep/src/com/android/quickstep/views/RecentsView.java`
- Android Developers：Notification 设计与性能相关文档 `https://developer.android.com/develop/ui/views/notifications`
- Android Developers：Splash Screen API `https://developer.android.com/guide/topics/ui/splash-screen`

## Foldable 设备多 Display 渲染模型源码分析 <!-- AIW-源码调研-2026-04-29 -->

### 概述

Foldable 设备上的 SystemUI 多 Display 渲染模型建立在 `DisplayId` 分片管理 + `NavigationBarController` 双映射架构之上。 StatusBar（通知侧）在 Foldable 场景下无多实例实现，仅支持 NavigationBar 和 Wallpaper 在 Secondary Display 上显示。

### 核心源码架构

#### 1. NavigationBarController - 多 Display 导航栏实例管理

- **源码位置**：`packages/SystemUI/src/com/android/systemui/navigationbar/NavigationBarController.java`
- **关键方法**：`getNavigationBarView(int displayId)`
- **数据结构**：`NavigationBarControllerImpl` 使用 `SparseArray<NavigationBar> mNavigationBars`

`NavigationBarControllerImpl` 维护一个 `SparseArray<NavigationBar>`，键为 `displayId`，值为该 Display 上的 `NavigationBar` 实例。`getNavigationBarView(displayId)` 是多 Display 路由的核心方法，可实现不同物理 Display 的独立导航栏管理。

调用链：
```
WindowManagerService → DisplayContent → StatusBar/NavigationBar → 
NavigationBarController.getNavigationBarView(displayId) → NavigationBarView
```

#### 2. NavigationBarControllerImpl - Foldable 形态标志

- **源码位置**：`packages/SystemUI/src/com/android/systemui/navigationbar/NavigationBarControllerImpl.java`
- **关键字段**：
  - `mIsLargeScreen: Boolean` — 包含 Foldable 展开态的大屏判定
  - `mIsPhone: Boolean` — 区分标准手机与其他形态
- **数据结构**：`SparseArray<NavigationBar> mNavigationBars`

`NavigationBarControllerImpl` 在构造时根据 Display 属性初始化这两个标志，共同决定导航栏的布局策略。

#### 3. DisplayContent - WindowManager 中的 Display 层级

- **源码位置**：`services/core/java/com/android/server/wm/DisplayContent.java`
- **关键方法**：`isSystemDecorationsSupported()`
- **配置读取**：`DisplayWindowSettings.shouldShowSystemDecorsLocked(DisplayContent)`

`DisplayContent` 是代表 Display 的核心类，`isSystemDecorationsSupported()` 判断系统装饰支持。Android 16 desktop windowing 引入了 force desktop 和 trusted display 分支，仅在满足条件时才返回 true；单一口径"Android 10+ 仅支持 NavigationBar/Wallpaper"不覆盖 Android 12-16 的 desktop mode 分支。

#### 4. TaskbarDelegate - Foldable 设备的 Wallpaper 可见性

- **源码位置**：`packages/SystemUI/src/com/android/systemui/navigationbar/TaskbarDelegate.java`
- **关键方法**：`updateWallpaperVisibility(boolean visible, int displayId)`

`TaskbarDelegate` 在 Foldable / 多 Display 场景下根据 displayId 更新 wallpaper 的可见性状态。`CentralSurfacesImpl` 中未命中带 `displayId` 的 `onWallpaperVisibilityChanged`；当前可核对的 displayId 感知 wallpaper visibility 入口是 `TaskbarDelegate`。

#### 5. 多 Display 限制的版本演进

- **Android 10-11**：Secondary Display 不支持 StatusBar（通知侧），仅支持 NavigationBar 和 Wallpaper
- **Android 12-14**：NavigationBar 和 Wallpaper 在 Secondary Display 上的支持延续，但仍无通知侧多实例
- **Android 15-16**：Desktop Windowing (Android 16) 引入了 `isSystemDecorationsSupported()` 的 force desktop / trusted display 分支，在多 Display 场景下的系统装饰策略比 Android 10-11 的口径更复杂，不能只按"仅 NavigationBar/Wallpaper"概括

#### 6. Android 15+ 增强特性

- **Edge-to-Edge**：StatusBar 默认透明，应用默认在系统栏下方绘制
- **Taskbar**：Pixel Fold 首发的功能合入 AOSP，支持 Foldable 展开态下固定/取消固定任务栏
- **FoldingFeature**：通过 Jetpack WindowManager 向应用层发布折叠状态信息

### 性能影响与观测点

1. **多 NavigationBarView / Taskbar 实例内存占用**：每增加一个 Display，都会增加对应 View、Surface 和状态管理对象，实际幅度取决于分辨率、导航模式和 OEM 定制，需要用 `dumpsys meminfo` 或 Perfetto 建基线
2. **Display 切换时 View 重建**：Foldable 展开/折叠切换时，触发 `onMeasure`/`onLayout`
3. **双 Display 同时亮屏**：功耗需要单独计入两个显示电源轨和合成负载，不能只按单屏基线外推

### Perfetto 观测点

- `WindowInsets` 变化信号
- `performTraversals`（多 Display 各自触发）
- PowerManager 的 `setDisplayPowerState` 调用链
- `NavigationBarView` 的实例创建与销毁

