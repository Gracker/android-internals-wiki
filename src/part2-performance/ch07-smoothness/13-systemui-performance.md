---
title: "SystemUI 性能分析"
chapter: "7.13"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [systemui, jank, launcher, statusbar, navigationbar, notification-shade, perfetto]
related_chapters: ["2.4", "2.5", "7.1", "7.3", "7.4", "13.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
gap_source: "AOSP结构+读者需求+素材驱动"
gap_score: 18
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/packages/SystemUI/"
  - type: aosp
    path: "packages/apps/Launcher3/"
  - type: official
    path: "https://source.android.com/docs/core/display"
---

# 7.13 SystemUI 性能分析

我们在前面几节分析卡顿原因和方法论时，关注点主要在普通 App 进程内部。但 Android 设备上有一组特殊的 UI 组件——StatusBar、NavigationBar、Notification Shade、Recent Apps——它们运行在 SystemUI 进程中，永远占据屏幕的一部分。这些组件一旦出现 jank，用户感知比任何单个 App 的卡顿都强烈，因为 SystemUI 不在屏幕上的时候几乎没有。

对 OEM 系统性能团队来说，SystemUI 优化通常占用比任何单个 App 更多的工程资源。对 App 开发者而言，理解 SystemUI 的性能特征也很有必要——你发出的每一条 Notification，最终都是 SystemUI 在渲染。

## 为什么 SystemUI 性能值得关注

普通 App 的 jank 发生在用户主动操作那个 App 的时候。用户可以切走、杀掉、或者干脆不用它。但 SystemUI 不一样：StatusBar 永远在屏幕顶部显示信号强度、电池、时间；NavigationBar 永远在屏幕底部提供导航按钮或手势区域；用户每次下拉通知栏、切换 App、查看最近任务，都在和 SystemUI 交互。

SystemUI 的 jank 之所以影响更大，原因有三：

第一，**曝光率极高**。从用户解锁屏幕到锁屏，StatusBar 和 NavigationBar 始终可见。如果 StatusBar 的通知图标更新导致掉帧，用户在看任何 App 的时候都会注意到。

第二，**性能影响范围广**。App 发送的 Notification 会在 SystemUI 的主线程上执行 RemoteViews inflate（参见 §7.4）。一个 App 发出布局复杂的 Notification，可能导致整个通知栏卡顿——这不仅是那个 App 的问题，还拖累了 SystemUI 进程的渲染。

第三，**进程架构特殊**。SystemUI（`com.android.systemui`）和 Launcher（通常是 `com.android.launcher3`）是两个独立进程，但它们在 App 启动动画、多任务切换等场景中需要紧密协作。分析这些场景时，单看一个进程的 Trace 是不够的。

[待补充：SystemUI 进程与 Launcher 进程在 Perfetto 中的 Track 概览截图]

## SystemUI 架构与渲染路径

### 多 Surface 架构

SystemUI 并不是一个统一的 Surface。StatusBar、NavigationBar、Notification Shade 各自拥有独立的 Surface，由 SurfaceFlinger 独立合成。这意味着：

- **StatusBar** 有自己的 Window（`StatusBarWindow`），在 SurfaceFlinger 中对应一个独立的 Layer。StatusBar 的布局变化不会触发 Notification Shade 的重绘，反之亦然。
- **NavigationBar** 同样有独立的 Window。在gesture navigation 模式下，NavigationBar 的实际可见区域可能非常小（仅底部一条窄边），但它仍然拥有一个完整的 Surface。
- **Notification Shade** 是最复杂的部分。展开时它覆盖整个屏幕，内部是一个包含多个子 View 的 NotificationStackScrollLayout。Shade 从折叠到全屏展开的过程涉及 SurfaceControl 的事务操作——改变 Layer 的 z-order、alpha、position 等属性。

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/shade/ — NotificationShadeWindowView 管理多个子 Window 的 Surface]

理解多 Surface 架构对性能分析很重要。在 Perfetto 的 SurfaceFlinger Layers Track 中，我们可以看到 StatusBar、NavigationBar、Shade 各自的 Layer。如果某个 Layer 的合成时间异常，可以直接定位到对应的 SystemUI 子组件。

### Shade 展开动画的渲染路径

Notification Shade 的展开是 SystemUI 中对帧率要求最高的动画之一。从用户手指触摸屏幕顶部开始下拉，到 Shade 完全展开覆盖屏幕，整个过程的帧预算分配如下：

1. **Input 事件阶段**（~2ms）：触摸事件从内核经过 InputDispatcher 到达 SystemUI 主线程。SystemUI 的 `NotificationPanelViewController` 判断是否触发 Shade 展开。
2. **布局计算阶段**（~4-8ms）：Shade 展开过程中需要不断重新计算 NotificationStackScrollLayout 的子 View 位置。如果可见通知数量多（比如 20+），这一步可能成为瓶颈。
3. **渲染阶段**（~4-8ms）：主线程完成 measure/layout/draw 后，RenderThread 将 DisplayList 提交给 GPU。
4. **SurfaceFlinger 合成阶段**（~2-4ms）：Shade 的 Surface 从小变大、从透明到不透明，SurfaceFlinger 需要处理 Layer 属性变化并合成最终帧。

在 120Hz 屏幕上，每帧预算只有 8.33ms。上面四个阶段的任何一个超出预算，用户就会感知到 Shade 展开不流畅。这就是为什么 Shade 展开是 SystemUI jank 的高发场景。

### Launcher 与 SystemUI 的交互

App 启动动画涉及 Launcher 和 SystemUI 的三方协作：

1. 用户点击 Launcher 中的 App 图标，Launcher 进程发起 startActivity 请求。
2. system_server 通知 SystemUI 准备启动动画（StatusBar 的图标可能需要变化）。
3. Launcher 渲染 App 启动 splash screen 的第一帧，同时 SystemUI 确保 StatusBar 不会遮挡启动窗口。
4. SurfaceFlinger 合成 Launcher、App 启动窗口、StatusBar 三个 Layer。

这个过程中，Launcher 进程和 SystemUI 进程在 CPU 上是并行运行的。如果两者恰好同时有重计算（比如 Launcher 正在加载 Widget，同时 SystemUI 正在处理通知更新），CPU 竞争可能导致双方都掉帧。

## StatusBar 与 NavigationBar 的性能陷阱

StatusBar 和 NavigationBar 看起来简单——不就是一行图标加几个按钮吗？但它们的性能陷阱隐藏在"频繁更新"中。

### 通知图标的 measure/layout 开销

StatusBar 左侧的通知图标区域（Notification Icon Area）是一个自定义的 ViewGroup。每次有新通知到来、通知更新、或通知被移除，这个区域都需要重新布局。具体流程：

1. `StatusBarNotificationPresenter` 收到通知更新通知。
2. 调用 `NotificationIconController.updateNotificationIcons()`。
3. 遍历所有 active notification，决定显示哪些图标（StatusBar 空间有限，需要裁剪）。
4. 对每个显示的图标调用 `ImageView.setImageDrawable()`，如果 drawable 发生变化，触发 requestLayout()。
5. requestLayout() 导致整个 StatusBar 的 measure/layout 树被遍历一次。

如果 App 在短时间内频繁更新 Notification（比如下载进度每秒更新 50 次），StatusBar 的图标区域每秒要重新布局 50 次。每次 layout 的开销取决于 StatusBar 的 View 树深度——OEM 定制的 StatusBar 通常比 AOSP 原生更深。

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/phone/StatusBarIconController.java — NotificationIconList 管理图标列表]

### 系统图标的更新频率

StatusBar 右侧的系统图标（信号强度、WiFi、电池、时钟等）也值得关注。这些图标的更新触发源各不相同：

- **信号强度**：由 TelephonyCallback 驱动，信号变化时更新。在信号不稳定的区域，更新频率可能达到每秒数次。
- **电池图标**：由 BatteryController 驱动，通常变化不频繁，但充电状态下会随电量百分比更新。
- **时钟**：每分钟更新一次（显示分钟级别的时钟），开销很小。
- **WiFi/Bluetooth**：状态变化时更新，正常情况下不频繁。

系统图标本身的开销不大，但 OEM 往往在 StatusBar 中添加运营商名称、网速指示器等自定义元素。这些元素的更新频率如果控制不好，会和通知图标的 layout 开销叠加。

### NavigationBar 的触摸响应延迟

NavigationBar（尤其是三按钮导航模式下的 Back/Home/Recents 按钮）的触摸事件处理有一个额外的跳转：Input 事件从 `InputDispatcher` 发送到 SystemUI 进程。这和普通 App 的 Input 事件路径是一样的，但 SystemUI 的 Input 处理涉及跨进程通信（通过 `InputConsumer` 机制），增加了一层延迟。

在手势导航模式下，这个问题更加明显。手势操作的识别和响应需要 `InputDispatcher` 将事件同时分发给 App 和 SystemUI 的手势检测器。如果 SystemUI 主线程正忙于处理通知更新，手势响应就会出现延迟。

[待验证: Android 17 手势导航对 NavigationBar 渲染的优化——NavigationBar 区域可能改为完全由 InputConsumer 在 system_server 中处理，不再经过 SystemUI 主线程]

## Notification Shade 展开性能

Notification Shade 的展开性能是 SystemUI 中被分析最多的场景之一，因为它是用户每天操作几十次的功能。

### Shade 展开/收起的关键路径

Shade 展开的关键路径从用户手指触碰屏幕顶部开始：

1. **Input 事件拦截**：`NotificationPanelViewController` 的 `onTouchEvent()` 方法拦截 ACTION_DOWN 事件，判断拖拽方向是否为向下。这个判断需要在同一帧内完成，否则用户会感觉到"触摸没反应"。
2. **拖拽过程中**：每个 MOVE 事件都触发 `setExpandedHeight()` 调用，更新 Shade 的展开高度。这个方法内部会调用 `NotificationStackScrollLayout` 的 `setExpansion()` → `requestLayout()`。
3. **动画阶段**：手指抬起后，如果 Shade 展开高度超过阈值，ValueAnimator 将展开高度平滑动画到全屏。动画的每一帧都触发 layout。

这个过程中最大的性能风险在于 `NotificationStackScrollLayout` 的 layout 开销。这个自定义 ViewGroup 需要计算所有可见通知的位置（包括堆叠效果、间距、圆角裁剪等），计算复杂度与可见通知数量成正比。

### RemoteViews inflate 开销

App 通过 `NotificationManager.notify()` 发送通知时，实际发送的是一个 `RemoteViews` 对象。这个对象描述了通知的布局结构，但真正的 inflate 发生在 SystemUI 进程的主线程上。

RemoteViews 的 inflate 过程：

1. SystemUI 收到通知后，`NotificationEntryManager` 创建一个 `NotificationEntry`。
2. `NotificationInflater` 在主线程上调用 `RemoteViews.apply()` 创建 View 树。
3. 如果通知使用了自定义布局（`Notification.Builder.setCustomContentView()`），inflate 开销取决于布局复杂度。
4. inflate 完成后，View 被添加到 `NotificationStackScrollLayout` 中。

关键问题在于：**每次 App 调用 `notify()` 更新通知，SystemUI 都可能需要 re-inflate RemoteViews。** 虽然系统对 RemoteViews 做了缓存（`NotificationInflater` 会检查内容是否变化），但如果 `RemoteViews` 的布局 ID 或内容发生变化，缓存就失效了。

一个典型的性能陷阱：音乐播放器每秒更新一次播放进度的 Notification。如果每次更新都创建了新的 `RemoteViews`（而不是复用同一个），SystemUI 主线程每秒要 inflate 一次自定义布局。在低端设备上，这直接导致持续的 jank。

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/statusbar/notification/row/NotificationInflater.java — inflateSynchronous() 方法在主线程执行 RemoteViews.apply()]

### Heads-up Notification（HUN）的阻塞风险

Heads-up Notification 是出现在屏幕顶部的浮动通知（比如来电、短信）。HUN 的特殊之处在于它有自己的 Window（`HeadsUpStatusBarView`），需要在 StatusBar 上方浮动显示。

HUN 的渲染性能风险在于它的出现和消失都有动画，而且动画运行期间 SystemUI 需要同时处理 Shade 的状态变化和 StatusBar 的图标更新。如果多个 HUN 短时间内连续出现，SystemUI 主线程的动画回调队列会快速积压。

### 大视图通知的渲染

`BigPictureStyle`、`InboxStyle`、`MessagingStyle` 等大视图通知在展开时需要渲染更多内容。`BigPictureStyle` 需要加载和显示一张 Bitmap，如果图片尺寸大（比如 1080p 的截图），解码和上传到 GPU 的开销可能达到 10-20ms，直接超过一帧的预算。

## Launcher 性能分析

Launcher 虽然是独立进程，但它的性能与 SystemUI 紧密关联——App 启动动画、多任务切换都需要两者协作。Android 12+ 的 QuickStep 模式更是把 Recents 功能从 SystemUI 移到了 Launcher 进程。

### Workspace 页面滑动

Launcher 的桌面页面滑动使用的是自定义的 `Workspace` 组件（不是 RecyclerView）。每个页面（`CellLayout`）可能包含 App 快捷方式、文件夹、Widget 等多种元素。滑动的性能特征：

- **双页面渲染**：滑动过程中，当前页和相邻页需要同时可见。这意味着两页的所有子 View 都需要 measure/layout。
- **Widget 更新**：如果桌面有 App Widget（如天气、时钟），Widget 的 `RemoteViews` 更新通过 `AppWidgetHost` 在 Launcher 主线程上执行。Widget 更新频率高时，会挤占滑动帧的时间。
- **Wallpaper 偏移**：桌面滑动通常伴随 Wallpaper 的视差偏移效果，这需要跨进程通知 WallpaperService 更新，开销很小但需要关注。

### App 启动动画的帧同步

App 启动动画的帧同步是 Android 性能分析中少数需要同时观察三个进程（Launcher、SystemUI、目标 App）的场景之一。

动画流程：

1. Launcher 收到 startActivity 的回调，开始缩小当前 App 图标、显示 splash screen。
2. 目标 App 进程启动（冷启动时需要 Zygote fork），创建第一帧。
3. SurfaceFlinger 在 Launcher 的 Layer 和 App 的 Window Layer 之间做 cross-fade。
4. SystemUI 确保 StatusBar 在动画过程中保持正确的 z-order。

在 Perfetto 中分析 App 启动动画卡顿，需要同时看 Launcher 进程的 MainThread（是否完成启动回调）、App 进程的 MainThread（是否完成第一帧渲染）、和 SurfaceFlinger 的 Layers Track（Layer 切换是否流畅）。单看任何一个进程都无法定位完整的问题。

### AllApps 列表

Launcher 的 AllApps 界面通常使用 `BaseRecyclerView`（Launcher 自己的 RecyclerView 子类）实现。当安装的 App 数量达到数百甚至上千时，列表滑动的性能取决于：

- **字母索引**：AllApps 通常有快速滚动的字母索引，滚动条的更新频率需要控制。
- **图标加载**：每个 App 的图标需要从 PackageManager 加载，如果图标缓存命中率低，I/O 开销会增大。
- **搜索过滤**：如果用户在搜索框输入，每次按键都需要过滤列表。过滤逻辑如果在主线程执行且数据量大，会导致输入延迟。

## 在 Perfetto 中分析 SystemUI 性能

分析 SystemUI 性能时，需要在 Perfetto 中找到正确的 Track 和 tracepoint。

### Track 识别

SystemUI 进程在 Perfetto 中的进程名通常是 `com.android.systemui`。需要关注的 Track：

- **主线程（MainThread/UI Thread）**：看 `Choreographer#doFrame` 的耗时，如果超过帧预算，说明 SystemUI 主线程负担过重。
- **RenderThread**：看 `DrawFrame` 的耗时。如果 RenderThread 耗时长而 MainThread 正常，说明渲染管线本身是瓶颈（比如 Shade 展开时 Layer 过大）。
- **SurfaceFlinger Layers Track**：观察 StatusBar、NavigationBar、Shade Layer 的合成时间。

Launcher 进程的进程名通常是 `com.android.launcher3`（系统 Launcher）或包名（第三方 Launcher），Track 结构类似。

### 关键 Trace 点

SystemUI 中的关键 tracepoint（AOSP 14+）：

| 场景 | Trace Event | 所在类 |
|------|------------|--------|
| 通知图标更新 | `StatusBar.updateNotificationIcons` | StatusBarIconController |
| Shade 展开/收起 | `NotificationPanelViewController.onTouchEvent` | NotificationPanelViewController |
| 通知 inflate | `NotificationInflater.inflate` | NotificationInflater |
| 通知列表滚动 | `NotificationStackScrollLayout` | NotificationStackScrollLayout |

Launcher 中的关键 tracepoint：

| 场景 | Trace Event | 所在类 |
|------|------------|--------|
| 页面滑动 | `Workspace.snapToPage` | Workspace |
| App 启动回调 | `QuickStep.appTransition` | QuickStep (Launcher3 QuickStep) |
| Recents 动画 | `RecentsView` | RecentsView |

### 常见 jank 模式在 Trace 中的特征

**模式 1：通知更新导致的 StatusBar jank**
- 表现：SystemUI 主线程 `doFrame` 耗时突增，紧跟在 `updateNotificationIcons` trace 之后。
- 原因：大量通知同时更新，图标区域的 measure/layout 耗时超过帧预算。

**模式 2：Shade 展开时通知 inflate 阻塞**
- 表现：Shade 展开的第一帧耗时特别长（可能 30-50ms），`NotificationInflater.inflate` 占了大部分时间。
- 原因：展开时多个通知需要同时 inflate，且都是自定义布局。

**模式 3：Launcher + SystemUI CPU 竞争**
- 表现：Launcher 和 SystemUI 的 `doFrame` 在同一时间段同时超时。
- 原因：两个进程同时需要 CPU，在大核调度不及时时互相拖累。需要在 CPU Scheduling Track 中确认是否有 core migration 延迟。

**模式 4：App 启动动画期间的 Layer 切换 jank**
- 表现：SurfaceFlinger Layers Track 中，Launcher Layer 到 App Layer 的切换不连续，中间出现空帧。
- 原因：App 第一帧渲染延迟或 SurfaceFlinger 的 Layer 事务提交时机不对。

[待补充：每种 jank 模式的 Perfetto Trace 截图]

## SystemUI 优化策略

### 异步布局

将 StatusBar 和 NavigationBar 中不需要在主线程完成的 inflate 操作移到后台线程。具体做法：

- 使用 `AsyncLayoutInflater` 或自定义的 inflate 线程池预加载 Notification 的 View 模板。
- 对于 RemoteViews，SystemUI 可以在收到通知后先在后台线程调用 `RemoteViews.apply()` 的预计算步骤（测量布局参数），主线程只负责添加到 View 树。

但这里有一个限制：`RemoteViews.apply()` 内部可能创建 Handler 等需要 Looper 的对象，必须在有 Looper 的线程上执行。实际上 AOSP 的 `NotificationInflater` 从 Android 13 开始支持 `inflateAsync()` 模式，使用一个单独的 HandlerThread 处理 inflate。

[待验证: Android 13+ NotificationInflater 的异步 inflate 模式在所有 OEM 设备上是否默认启用]

### 图标缓存与预加载

StatusBar 的通知图标和系统图标都应该建立完善的缓存机制：

- **Drawable 缓存**：通知图标的 `Icon.loadDrawable()` 结果应该缓存。同一个 Notification 的图标通常不变，不需要每次都重新加载。
- **预加载常用图标**：信号强度、电池等系统图标的 drawable 应该在 SystemUI 启动时预加载，避免首次显示时的延迟。
- **图标更新限流**：对高频更新的系统图标（如信号强度），使用 debounce 机制，将更新频率限制在每 500ms 一次。

### SurfaceControl 事务批处理

Shade 展开动画涉及大量的 SurfaceControl 属性变更（position、alpha、layer stack 等）。每个 `SurfaceControl.Transaction.apply()` 都是一次跨进程 IPC 到 SurfaceFlinger。如果动画过程中每帧都单独 apply 多次事务，IPC 开销会累积。

优化方式：将同一帧内的所有 SurfaceControl 属性变更合并到一个 Transaction 中，只 apply 一次。AOSP 的 Shade 动画实现从 Android 14 开始使用 `SyncRtSurfaceTransactionApplier`，在 RenderThread 的 sync 时机统一提交事务。

[已验证: AOSP android-14.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/surfaceeffects/surfaceeffects/ — SurfaceControl 事务批处理实现]

### 视图层级扁平化

StatusBar 和 NavigationBar 的 View 层级在 AOSP 原生版本中已经相对扁平，但 OEM 定制往往增加了大量嵌套。每增加一层嵌套，measure/layout 的遍历成本就增加一个数量级。

减少层级的方法：
- 使用 `ConstraintLayout` 替代多层嵌套的 `LinearLayout`。
- 移除不必要的 Wrapper ViewGroup（OEM 有时为了方便主题切换会添加额外的容器）。
- 使用 `merge` 标签减少 inflate 后的层级。

### 通知限流

对 App 开发者而言，减少通知更新频率是帮助 SystemUI 性能最直接的方式：

- **进度条通知**：不要每帧都调用 `notify()`。使用 `setProgress()` 并控制更新频率在 500ms-1s 之间。
- **复用 RemoteViews**：更新通知时复用同一个 `RemoteViews` 对象（调用 `setTextViewText()` 等方法更新内容），而不是每次都创建新的 `RemoteViews`。这样 SystemUI 可以利用缓存，避免 re-inflate。
- **使用标准样式**：尽量使用 `NotificationCompat.BigTextStyle()`、`InboxStyle()` 等标准样式，而不是自定义布局。标准样式在 SystemUI 中有专门的优化路径。

## 与其他章节的关联

- **§2.5 MainThread 与 RenderThread 协作**：SystemUI 的渲染管线遵循同样的 MainThread → RenderThread 模型。理解 Choreographer 和 VSync 机制是分析 SystemUI jank 的前提。
- **§7.1 卡顿的定义与分类**：SystemUI jank 的分类（主线程耗时、RenderThread 耗时、SurfaceFlinger 合成超时）直接对应卡顿的分类体系。
- **§7.4 典型卡顿场景**：通知栏展开、Launcher 滑动等场景在 §7.4 中有初步覆盖，本节从 SystemUI 架构角度进行了更深入的分析。
- **§13.3 Perfetto View 解读**：分析 SystemUI 性能需要熟练使用 Perfetto 的 Track 筛选和 SQL 查询功能。

## 参考资料

- AOSP SystemUI 源码：`frameworks/base/packages/SystemUI/`
- AOSP Launcher3 源码：`packages/apps/Launcher3/`
- Android 官方文档：Notification 最佳实践 `https://developer.android.com/develop/ui/views/notifications`
- [待补充：Google I/O 演讲链接 — SystemUI 性能优化主题]
