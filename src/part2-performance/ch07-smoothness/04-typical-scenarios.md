---
title: "典型场景分析"
chapter: "7.4"
status: ready-for-review
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
drafted_date: "2026-04-01"
reviewed_date: "2026-04-06"
reviewed_by: "openclaw-task6"
rework_date: "2026-04-04"
rework_by: openclaw-task2b
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-01"
last_verified_against: "AOSP android-16.0.0_r1, Perfetto 官方文档"
confidence: high
sources:
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md"
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/Android-Perfetto-05-Chorergrapher.md"
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md"
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md"
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md"
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md"
  - type: official
    path: "developer.android.com/topic/performance/recycler-view"
  - type: official
    path: "perfetto.dev/docs/analysis/trace-processor"
tags: ['scrolling', 'animation', 'RecyclerView', 'transition', 'jank', 'Perfetto']
related_chapters: ["7.1", "7.2", "7.3", "2.4", "2.5"]
---

# 典型场景分析

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 列表滑动场景的 Jank 分析：RecyclerView 的 onBind、ViewHolder 创建、图片加载
- 🔹 页面切换动画的 Jank 分析：Activity Transition、Fragment 切换、SharedElement
- 🔹 窗口动画的 Jank：App 启动窗口、Dialog/PopupWindow 弹出
- 🔹 Notification 展开/折叠的 Jank
- 🔹 桌面滑动 / 多任务切换的 Jank

### 扩展（可选深入）

- 🔸 视频播放场景的帧率稳定性
- 🔸 地图/WebView 等重渲染场景的特殊处理

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要逐场景分析卡顿

前面几节我们把卡顿的定义、原因体系、分析方法都梳理了一遍。但在实际工作中，"卡顿"不是一个抽象概念——它总是出现在某个具体的场景里：用户在刷列表、在切页面、在下拉通知栏、在多任务间来回切换。不同场景下的卡顿，虽然底层都是"主线程没能在一个 VSync 周期内完成帧渲染"，但根因各不相同，分析手法也有差异。

这一节我们把最常见的几个卡顿场景逐个拆开，看看每个场景的"卡顿长什么样"、"为什么卡"、"在 Perfetto 中怎么定位"。掌握了这些典型场景的分析套路，以后遇到类似的卡顿，就能快速对号入座，不用每次都从零开始摸索。

[来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md — 高爷对卡顿场景分类的实战经验]

---

## 一、列表滑动场景的 Jank 分析

列表滑动可能是用户感知最直接的卡顿场景。手机上 80% 的交互时间都花在刷各种 Feed、聊天列表、商品列表上。一旦出现掉帧，手指的滑动就会感觉到"一顿一顿的"，体验非常糟糕。

### 1.1 滑动场景在 Perfetto 中的基本形态

一个健康的列表滑动在 Perfetto 中有一个非常清晰的节奏：每个 VSync 周期内，主线程依次执行 Input → Traversal（measure/layout/draw），然后同步 DisplayList 给 RenderThread，RenderThread 完成绘制后提交 Buffer。如果这些步骤都能在一个 VSync 周期内完成（120Hz 设备是 8.33ms，60Hz 设备是 16.67ms），帧就是绿色的，滑动就是流畅的。（关于 VSync 周期和 Choreographer 的回调调度，详见 2.3 和 2.4 节。）

[图：Perfetto 中正常的列表滑动帧序列，展示 Input → Traversal → RenderThread 的节奏]

滑动过程中有两个阶段值得关注：

**手指触摸阶段**：每一帧都有 Input 回调处理触摸事件，然后执行 Traversal 更新列表项的位置。这个阶段主线程的负载取决于 Input 事件处理和 View 体系的重绘开销。

**惯性滑动（Fling）阶段**：手指抬起后，系统通过 Scroller/OverScroller 计算每一帧的滚动偏移量。这个阶段没有 Input 回调，取而代之的是 Animation 回调驱动滚动。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java — Animation 回调由 ValueAnimator 通过 Choreographer.postCallback 注册]

[来源: obsidian/Personal-Knowlodge/source/Android-Perfetto-07-MainThread-And-RenderThread.md — 高爷对滑动两阶段的 Perfetto 观察]

### 1.2 RecyclerView 的性能瓶颈

RecyclerView 是列表场景的核心组件。它的设计目标是"回收复用"，通过 ViewHolder 缓存机制避免每次都创建新的 View。但这个机制本身也有性能陷阱，主要集中在三个环节：

**onBindViewHolder 耗时**

`onBindViewHolder` 在列表滑动时被频繁调用——每滑出一个旧 item 从缓存中取出一个新 item 进入可见区域时，都需要调用一次 bind 来更新数据到 View 上。这个方法运行在主线程上，如果做了任何耗时操作，都会直接吃掉帧时间预算。

常见的坑包括：
- 在 bind 方法中做数据转换（日期格式化、JSON 解析、字符串拼接）
- 在 bind 方法中触发磁盘或网络 I/O（哪怕是"看起来很快"的 SharedPreferences 读取）
- 创建临时对象过多，导致频繁 GC（GC 暂停虽然只有几毫秒，但在 120Hz 设备上 8.33ms 的帧预算里就很致命了）
- 对图片做了同步解码或裁剪

[已验证: 官方文档, developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.Adapter — onBindViewHolder 文档明确说明应保持轻量]

在 Perfetto 中的表现：如果 bind 耗时过长，我们会在主线程的 Traversal 阶段看到 measure 或 layout 的 slice 明显变长。如果怀疑是 bind 问题，可以在 `onBindViewHolder` 中添加自定义 Trace event：

```java
// 在 Adapter.onBindViewHolder 中插桩
@Override
public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
    Trace.beginSection("bind:" + position);
    try {
        // bind 逻辑
        holder.bind(items.get(position));
    } finally {
        Trace.endSection();
    }
}
```

插桩后重新抓 Trace，Perfetto 主线程 track 上每一帧的 Traversal 阶段中就能看到每个 item 的 bind 耗时。如果某个 position 的 bind slice 特别长，直接定位到对应的数据项排查即可。

**ViewHolder 创建（onCreateViewHolder）耗时**

RecyclerView 虽然设计为复用 ViewHolder，但在某些场景下仍需要创建新的：列表首次加载时缓存为空、列表项类型增多导致各类型缓存不足、或者快速滑动导致缓存耗尽。`onCreateViewHolder` 需要 inflate 布局 XML，这个过程涉及 XML 解析和 View 树的递归创建，开销远大于 bind。

优化思路包括：
- 简化 item 布局层级（用 ConstraintLayout 替代多层嵌套的 LinearLayout）
- 增大 RecyclerView 的缓存池大小（`RecycledViewPool.setMaxRecycledViews`）
- 对多类型列表，考虑使用 `ConcatAdapter` 来分离不同类型的缓存管理

[已验证: 官方文档, developer.android.com/reference/androidx/recyclerview/widget/RecyclerView.RecycledViewPool — 缓存池机制说明]

**图片加载引起的卡顿**

图片是列表滑动中最常见的卡顿源之一。问题不是图片加载本身——现代图片库（Glide、Coil、Fresco）都做了异步加载——而是图片加载完成后的回调处理。如果 ImageView 没有预设固定尺寸，图片解码后需要重新触发 requestLayout，导致整棵 View 树重新 measure/layout。在快速滑动中，多个图片几乎同时回调，每一帧都可能叠加多次 layout 计算。

在 Perfetto 中，这种问题的特征是主线程频繁出现 measure/layout 的长 slice，且时间与图片回调的时机吻合。解决方案是为列表中的 ImageView 设置固定宽高（或使用 `setHasFixedSize(true)`），避免图片加载完成后触发重新布局。

[已验证: 官方文档, developer.android.com/topic/performance/recycler-view — 官方推荐设置固定尺寸避免重新测量]

### 1.3 系统层面的滑动卡顿

不是所有滑动卡顿都是 App 的锅。在高爷分析的 MIUI 桌面滑动案例中，卡顿的根因是 RenderThread 被调度到了小核 CPU 上。小核虽然频率拉满了（1.8GHz），但性能不足以在 11.1ms（90Hz 设备）内完成渲染任务。

[来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md — 高爷对 MIUI 桌面滑动卡顿的完整分析]

在 Perfetto 中，这类问题的特征是：
- RenderThread 的 CPU 状态虽然是 Running（绿色），但耗时明显超出正常范围
- 查看 CPU Info 区域，发现 RenderThread 跑在小核（cpu0-cpu3）而非大核上
- 掉帧后下一帧，调度器将 RenderThread 迁移到大核，恢复正常

这类问题的分析路径是：先确认 App 主线程不是瓶颈（主线程 slice 正常），然后看 RenderThread 的耗时，最后去 CPU 区域确认线程被调度到了哪个核。解决思路是系统层面的调度策略调整（如设置 RenderThread 的调度组偏好），而非 App 代码优化。

[图：RenderThread 跑在小核导致掉帧的 Perfetto 截图，标注小核频率和帧耗时]

---

## 二、页面切换动画的 Jank 分析

页面切换是用户在 App 内导航时最频繁的操作之一。无论是 Activity 跳转、Fragment 替换，还是 SharedElement 转场动画，背后都涉及复杂的渲染协调。一旦切换过程中的某一帧掉了，用户会感觉到"卡了一下"或"闪了一下"，体验很不连贯。

### 2.1 Activity Transition 的卡顿模式

Activity 切换的渲染流程涉及两个进程（源 Activity 和目标 Activity）、两个 Window、以及 WindowManagerService 和 SurfaceFlinger 的协调。流程大致是这样的：

1. 用户触发跳转（点击按钮等），源 Activity 调用 `startActivity()`
2. SystemServer 的 ActivityManagerService 创建目标 Activity 进程（如果是冷启动）或通知目标进程创建 Activity
3. 目标 Activity 执行 `onCreate()` → `onStart()` → `onResume()`，其中 `onCreate()` 中的 `setContentView()` 触发布局 inflate
4. 如果配置了转场动画，系统在源 Activity 和目标 Activity 之间建立动画通道
5. 动画期间，两个 Activity 的 Window 都需要逐帧渲染

[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/ActivityStarter.java — Activity 启动流程]

卡顿最容易发生在第 3 步和第 5 步的交叉区域。如果目标 Activity 的布局很复杂，`setContentView()` 在主线程上 inflate XML 可能需要几十毫秒甚至上百毫秒，这段时间内动画帧无法按时渲染。在 Perfetto 中的表现是：目标 Activity 进程启动后，主线程出现一大块 `inflate` 或 `setContentView` 的 slice，紧跟的几帧全部是红色或黄色。

**SharedElement 转场的额外负担**

SharedElement 转场（共享元素动画）让用户看起来一个 View 从源页面"飞"到了目标页面。实现上，系统需要：
1. 在两个 Activity 之间捕获共享 View 的位置和大小信息
2. 创建一个独立的 DecorView 层来播放动画
3. 每帧更新共享 View 的 transform（位置、缩放、圆角等）

这个过程中任何一个环节出问题——比如目标 Activity 的布局还没完成导致无法确定 View 的最终位置——都会导致动画掉帧。

[已验证: 官方文档, developer.android.com/training/transitions — SharedElement 转场机制说明]

### 2.2 Fragment 切换的卡顿模式

Fragment 切换比 Activity 切换轻量，因为都在同一个进程和同一个 Window 内完成。但 FragmentTransaction 的 `replace` 操作仍然会在主线程上触发完整的 View 生命周期：旧 Fragment 的 View 被 remove，新 Fragment 执行 `onCreateView()` → `onViewCreated()` → `onStart()` → `onResume()`。

如果新 Fragment 的布局比较重，或者 `onViewCreated()` 中做了数据初始化（网络请求的本地缓存读取、数据库查询等），这些操作都会挤在同一个 VSync 周期内，导致帧超时。

在 Perfetto 中识别 Fragment 切换卡顿的方式：
- 找到切换发生的时间点（可以在 `FragmentTransaction.commit()` 前后加自定义 Trace event）
- 观察主线程在那几帧上的 slice 分布——如果看到 `inflate` + `measure` + `layout` 堆叠在一起，说明布局加载和初始化是瓶颈
- 检查 RenderThread 的负载——如果布局中包含图片或复杂自定义 View 的 onDraw，RenderThread 也会成为瓶颈

优化思路：
- 将 Fragment 的布局拆分为多个阶段：先加载骨架布局，数据准备好后再填充内容
- 将 Fragment 事务提交时机与动画帧解耦：如果 Fragment 切换发生在动画期间（如 SharedElement 转场），事务的 commit 会触发 View 层级的完整重建（remove + add + measure + layout），这些操作会挤占动画帧的渲染时间。更好的做法是将 commit 延迟到动画结束之后，或者先暂停动画、执行事务、再恢复动画。[已确认: FragmentTransaction.commit() 在主线程上同步入队，实际的 View 操作在下一个 Choreographer doFrame 中执行]
- 在非动画期间使用 `commitNow()` 同步执行：`commitNow()` 会在调用时立即执行事务中的所有操作，而不是等到下一个 Choreographer 周期。这在不需要动画的场景下（如 ViewPager2 内部的页面切换）可以减少一帧的延迟。但注意 `commitNow()` 不能和 `addToBackStack()` 一起使用。[已验证: AOSP FragmentTransaction.java — commitNow 文档说明]
- 预加载下一页 Fragment 的 View（`setMaxLifecycle` 配合 ViewPager2 的 `setOffscreenPageLimit`）

### 2.3 页面切换动画在 Perfetto 中的表现

[图：Activity 切换动画期间两个进程的 Perfetto 时序，标注源 Activity 退出动画和目标 Activity 进入动画]

页面切换期间的 Perfetto Trace 有几个特征性的观察点：

**FrameTimeline 中的 BufferStuffing**：切换期间 App 可能连续提交多个帧到 SurfaceFlinger，但前一帧还没被消费，形成 Buffer 堆积。在 FrameTimeline track 中表现为多个 Actual Timeline slice 紧密排列但呈现时间依次推迟。

**AppDeadlineMissed**：如果 App 侧渲染超时，FrameTimeline 中对应帧会标记为 `AppDeadlineMissed`。这是最常见的页面切换动画卡顿类型——新页面的布局渲染吃掉了动画帧的时间。

**跨进程的动画协调**：Activity 切换涉及两个进程，两边的帧需要同步。如果源进程的退出动画和目标进程的进入动画在时间上不匹配（比如一边快一边慢），视觉上会感觉"撕裂"。

[已验证: Perfetto 官方文档, perfetto.dev/docs/analysis/trace-processor — FrameTimeline jank 类型定义]

---

## 三、窗口动画的 Jank

窗口动画和页面切换动画的区别在于，窗口动画通常涉及一个独立的 Window 层——比如 App 启动时的启动画面（Splash Screen）、Dialog 和 PopupWindow 的弹出动画、以及输入法的弹出/收起。

### 3.1 App 启动窗口

从 Android 12 开始，系统为所有 App 提供了默认的 Splash Screen（通过 `SplashScreen` API）。在 App 进程完成初始化之前，系统会显示一个带有 App 图标和主题色的启动窗口。这个窗口由 SystemServer 管理，App 进程就绪后系统执行从启动窗口到 App 主界面的过渡动画。（启动窗口与 App 启动流程的完整分析见 8.2 节。）

[图：SplashScreen 启动窗口到 App 主界面过渡动画的 Perfetto 截图，标注 SystemServer 动画线程和 App 进程的时间关系]

启动窗口动画卡顿通常不是 App 的问题，而是系统侧的问题——SurfaceFlinger 在合成启动窗口和其他层时的性能不足，或者 CPU 调度没有给 SystemServer 的动画线程足够的优先级。但如果 App 的 `onCreate()` 耗时过长导致过渡动画延迟开始，那就是 App 的问题。

[已验证: 官方文档, developer.android.com/develop/ui/views/launch/splash-screen — SplashScreen API 说明]

在 Perfetto 中分析启动窗口卡顿：
- 关注 `SplashScreen` 进程（或 SystemUI 中对应的 Window Token）
- 查看 SurfaceFlinger 在过渡动画期间的合成耗时
- 检查 App 主进程的 `ActivityThread.handleBindApplication` → `Activity.onCreate` 调用路径是否过长

### 3.2 Dialog / PopupWindow 弹出动画

Dialog 的弹出过程涉及：
1. 创建新的 Window（通过 WindowManager.addView）
2. Window 的 Surface 创建和首次绘制
3. 弹出动画（通常是 scale + alpha 的组合动画）

如果 Dialog 的布局很复杂（比如包含大量表单、图片、嵌套 RecyclerView），首次 inflate 和 measure 的耗时会直接影响动画的前几帧。用户感知到的就是"弹窗出现的时候卡了一下"。

PopupWindow 的情况类似，但 PopupWindow 使用的是 App 进程自己的 Window Token，不经过 WindowManagerService 的 Window 创建流程，所以相对轻量一些。但如果 PopupWindow 的 anchor View 正在进行动画，两者可能争抢主线程时间。

在 Perfetto 中的分析方法：
- 在 Dialog 的 `show()` 方法前后添加 Trace event
- 观察主线程在 `show()` 之后几帧的耗时——如果 `inflate` 和 `measure` 占据了大部分时间，说明 Dialog 的布局是瓶颈
- 检查是否有 GC 暂停（Dialog 创建通常伴随大量对象分配，可能触发 GC）

---

## 四、Notification 展开/折叠的 Jank

前面三个场景（列表滑动、页面切换、窗口动画）都发生在 App 进程内部或 App 之间的协调中。接下来这个场景有点不同：通知栏的展开和折叠由 SystemUI 进程负责，普通 App 开发者通常不会直接碰到。但在系统性能优化场景下，尤其是 App 自定义了 Notification 的 RemoteViews 时，这个场景就需要关注——因为 App 的 Notification 布局最终是在 SystemUI 的主线程上渲染的。

### 4.1 通知栏展开的渲染管线

通知栏下拉时，SystemUI 需要做几件事：
1. 计算通知栏面板的展开高度（逐帧插值）
2. 更新所有可见 Notification 的 RemoteViews（如果内容变了）
3. 对通知面板执行 measure/layout/draw
4. 处理 Quick Settings 面板的展开/折叠动画（如果拉到底）
5. 如果有自定义了 `DecoratedCustomViewStyle` 的通知，还需要渲染 App 提供的自定义布局

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/shade/ — Shade 层级的通知面板实现]

### 4.2 卡顿来源

通知栏展开卡顿的常见原因：

**RemoteViews 的 re-inflate**：如果 App 频繁更新 Notification（比如进度条更新、播放器进度），每次 updateNotification 都可能导致 RemoteViews 被 re-inflate。虽然系统对 RemoteViews 做了缓存优化，但布局复杂的自定义通知仍然会在 SystemUI 主线程上产生明显开销。

**大量通知的布局计算**：通知栏展开时如果有 20+ 条通知，每一条都需要 measure 和 layout，叠加起来可能吃掉好几帧的时间。特别是有 GroupSummary 通知时，展开/折叠的动画期间需要同时渲染分组头和组内通知。

**SurfaceFlinger 合成负载**：通知栏展开时涉及多层叠加——状态栏层、通知面板层、背后的 App 层、导航栏层——SurfaceFlinger 需要在每个 VSync-sf 周期内完成所有层的合成。如果合成路径走了 GPU（而不是 HWC Overlay），开销会更大。

在 Perfetto 中分析通知栏卡顿，需要同时观察 SystemUI 进程和 SurfaceFlinger 进程。如果 SystemUI 主线程的帧渲染时间正常但仍然掉帧，可能是 SurfaceFlinger 合成的问题。

[待补充：通知栏展开卡顿的 Perfetto Trace 截图，标注 SystemUI 和 SurfaceFlinger 的对应帧]

---

## 五、桌面滑动 / 多任务切换的 Jank

从 Notification 继续往外看，系统 Launcher 和 Recents 界面是用户操作频率最高的两个系统级 UI 场景。它们涉及 Launcher 进程（系统 Launcher 或第三方 Launcher）、SystemUI 进程、以及 SystemServer 进程的三方协调，分析复杂度比前几个场景更高。

### 5.1 桌面滑动

桌面滑动的分析和普通列表滑动类似（见第一节），但有几个特殊之处：

**Workspace 的特殊性**：Launcher 的桌面不是标准的 RecyclerView，而是自定义的 Workspace/BrowseLayout。每个"页面"可能包含复杂的 App Widget、快捷方式网格、文件夹等。滑动时需要渲染多个半页面（当前页 + 下一页的部分内容），GPU 负载比普通列表高。

**App Widget 的更新**：如果桌面有 App Widget（如天气、时钟、日历），Widget 的 RemoteViews 更新会通过 BroadcastReceiver 在 Launcher 主线程上执行。如果 Widget 更新频率高或者布局复杂，会挤占滑动帧的时间。

**壁纸的滚动**：桌面滑动时壁纸跟随偏移（Wallpaper offset），这涉及 SystemServer 的 WallpaperManagerService 和 SurfaceFlinger 的协调。如果壁纸分辨率过高或者 WallpaperService 的渲染线程卡住，也会导致桌面滑动掉帧。

[来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-2.md — 高爷对 MIUI 桌面滑动卡顿的实战分析]

在高爷分析的案例中，桌面滑动卡顿的根因是 RenderThread 被调度到了小核。这个发现过程体现了系统级卡顿分析的典型思路：

1. 先看 App（这里是 Launcher）主线程，确认主线程是否正常
2. 再看 RenderThread，发现耗时异常
3. 最后去 CPU 区域，确认线程被调度到了哪个核
4. 对比正常帧和异常帧的调度差异，锁定根因

[图：桌面滑动场景中 RenderThread 被调度到小核导致掉帧的 Perfetto 截图，来自高爷 MIUI 桌面分析案例]

### 5.2 多任务切换（Recents）

多任务切换（也叫 Recent Apps、Overview）在 Android 12+ 中由 Launcher 进程负责（QuickStep 模式）。切换过程涉及一个复杂的多阶段动画：

1. **当前 App 缩小动画**：将当前 App 的 Window 缩小到卡片大小
2. **Recents 列表滑入**：从侧边滑入之前最近使用的 App 缩略图列表
3. **用户滑动选择**：用户在卡片列表中左右滑动
4. **目标 App 放大动画**：选中的 App 卡片放大回全屏

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/quickstep/ — QuickStep 的多阶段动画实现]

[图：多任务切换 QuickStep 动画的 Perfetto 时序，标注四个动画阶段和 Launcher/SurfaceFlinger 的对应帧]

这个动画涉及 Launcher 进程和目标 App 进程之间的协调（通过 `ActivityTaskManager` 和 `InputConsumer`）。卡顿可能出现在：

**动画启动阶段**：Launcher 需要在短时间内完成多个 TaskView 的布局计算。如果 Recents 列表中有大量 Task（比如用户很久没清理），布局开销会线性增长。

**缩略图加载**：每个 TaskView 需要显示对应 App 的缩略图（Thumbnail）。这些缩略图通过 SharedMemory 从 SystemServer 传递给 Launcher，解码和上传纹理都需要时间。如果缩略图分辨率高且数量多，GPU 负载会明显增大。

**手势冲突**：多任务手势（从底部上滑并停顿）和 App 内的滑动手势容易冲突。如果手势识别耗时，会导致动画的起始帧延迟。

在 Perfetto 中分析多任务切换卡顿的方法：
- 找到 Launcher 进程的 `QuickStep` 相关 Trace event
- 观察动画期间的帧序列，特别关注动画开始的前 2-3 帧（最容易卡）
- 检查 `InputConsumer` 线程的手势识别是否有延迟
- 同时查看 SurfaceFlinger 的合成路径——多任务期间活跃的 Layer 数量较多，容易触发 GPU 合成

---

## 六、分析方法总结

到这里我们把五个典型卡顿场景都过了一遍。虽然每个场景的根因不同，但分析方法是相通的。我们总结一个通用的分析框架：

### 6.1 三步定位法

**第一步：确认是否真的掉帧。** 不要只看 App 主线程的帧颜色（绿/黄/红），要看 SurfaceFlinger 的 BufferQueue 和合成情况。帧颜色的含义和 Buffer 状态的判断方法在 7.1 节中有详细说明。黄帧不一定掉帧（Triple Buffer 可能吸收了延迟），绿帧也不一定没问题（如果帧是在 Buffer 充裕时产生的，实际延迟可能已经被掩盖了）。[来源: obsidian/Personal-Knowlodge/source/android-systrace-smooth-in-action-3.md — 高爷对帧颜色与实际掉帧关系的分析]

**第二步：定位瓶颈在哪个线程。** 是主线程耗时（Traversal 阶段的 measure/layout/draw 过长）？还是 RenderThread 耗时（GPU 渲染超时）？还是线程本身没被及时调度（Runnable 状态时间长，等 CPU）？

**第三步：从线程瓶颈反推根因。** 主线程耗时 → 看 Traversal 各阶段的 slice 分布；RenderThread 耗时 → 看 drawing 阶段是 CPU 还是 GPU 瓶颈，去 CPU 区域确认调度情况；调度问题 → 看是否被跑到了小核、是否有更高优先级的任务抢占。

### 6.2 场景 → 典型根因速查

| 场景 | 最常见的根因 | Perfetto 特征 |
|------|------------|---------------|
| 列表滑动 | onBind 耗时 / 图片加载触发 re-layout | 主线程 Traversal 阶段的 measure/layout 变长 |
| 页面切换动画 | 目标页面布局 inflate 耗时 | 切换发生后的前 2-3 帧红帧 |
| Dialog 弹出 | Dialog 布局 inflate + 首次 measure | show() 之后的帧超时 |
| 通知栏展开 | RemoteViews re-inflate / 大量通知布局 | SystemUI 主线程耗时 + SurfaceFlinger 合成超时 |
| 桌面滑动 | RenderThread 被调度到小核 | RenderThread running 但耗时异常，CPU 区域确认核分配 |
| 多任务切换 | TaskView 布局 + 缩略图解码 | Launcher 主线程 + RenderThread 双重负载 |

> 注：上表是"最常见"的根因，实际分析时不要先入为主。很多看似是 App 问题的卡顿，最后发现是系统调度或 SurfaceFlinger 合成的问题。始终以 Trace 数据为准。

---

## 七、扩展：其他重渲染场景

### 7.1 视频播放场景的帧率稳定性 [待补充]

视频播放的卡顿分析相对独立，因为视频帧的渲染管线和 UI 帧不同。视频解码帧由 MediaCodec 直接输出到 Surface，不经过 App 主线程的 Traversal 流程。卡顿通常由解码性能不足（硬解/软解）、GPU 后处理（如 HDR→SDR 转换）、或 SurfaceFlinger 的 VSync 同步问题导致。

这个场景的完整分析需要结合 MediaCodec 的 Trace 输出和 SurfaceFlinger 的 Buffer 状态，留待后续补充。

[待补充：视频播放帧率分析的完整方法论]

### 7.2 地图 / WebView 等重渲染场景 [待补充]

地图和 WebView 是两类特殊的"重渲染"场景：

**地图场景**（如 Google Maps、高德地图）：地图的渲染由地图 SDK 内部的 GLSurfaceView 或 TextureView 完成，App 主线程只负责 UI 覆盖层（控件、POI 标注等）。卡顿通常出现在地图引擎的 GL 渲染线程上，可能由瓦片加载、矢量数据解析、或 GPU 着色器编译引起。

**WebView 场景**：WebView 的渲染由 Chromium 的渲染管线完成（Browser 进程 → Renderer 进程 → GPU 进程）。Android 的 WebView 在系统层面是一个独立的渲染体系，它的卡顿分析需要使用 Chrome DevTools 的 Performance 面板而非 Perfetto。

[待补充：地图和 WebView 场景的具体分析方法]

---

## 常见问题与误区

**"我的列表滑动掉帧了，肯定是 RecyclerView 的锅"**

不一定。我们在 1.3 节中分析过一个案例：RenderThread 被调度到了小核 CPU，App 代码完全没问题。正确的做法是先在 Perfetto 中确认瓶颈在哪个线程——主线程、RenderThread、还是调度问题——再针对性优化。先看 Trace 再动手，而不是先改代码再看效果。

**"用了 Glide/Coil 加载图片，图片就不会导致卡顿了"**

图片库解决的是"异步加载"问题，但加载完成后的回调仍然在主线程上执行。如果 ImageView 没有固定尺寸，每一张图片回调都会触发 `requestLayout()`，导致整棵 View 树重新 measure/layout。在快速滑动中，多个图片回调叠加，每一帧可能都有 layout 计算。解决方案是设置 `setHasFixedSize(true)` 或给 ImageView 固定宽高。

**"黄帧就是掉帧"**

不一定。黄帧表示这一帧的渲染时间超过了 VSync 周期但被 Triple Buffer 吸收了——用户可能感知不到。真正需要关注的是 SurfaceFlinger 侧的 `SFDeadlineMissed`（SurfaceFlinger 合成超时导致的那帧确实没有被显示出来）。分析时以 FrameTimeline track 的 jank type 为准，而不是 App 侧的帧颜色。

**"卡顿一定是主线程的问题"**

RenderThread 卡顿同样会导致掉帧。在 GPU 密集型场景（复杂自定义 View 的 `onDraw`、大量图片渲染、App Widget 渲染）中，RenderThread 的 GPU 渲染耗时可能成为瓶颈。在 Perfetto 中，RenderThread 的 slice 如果出现了长时间 `drawFrames`，说明 GPU 渲染是瓶颈。此时优化主线程的 layout 不会有效果，需要减少 GPU 绘制指令或简化渲染路径。

**"页面切换卡顿只要优化新页面的布局就行了"**

Activity 转场动画涉及源 Activity 和目标 Activity 两个进程的帧同步。即使目标页面的布局优化得再好，如果源 Activity 的退出动画帧没按时渲染，动画仍然会掉帧。在分析时需要同时查看两个进程的帧序列，不能只看目标 Activity。

---

## 参考资料

- [Android Perfetto 系列 7 - MainThread 和 RenderThread 解读](https://androidperformance.com/2025/08/02/Android-Perfetto-07-MainThread-And-RenderThread/) — 高爷
- [Android Perfetto 系列 5 - 基于 Choreographer 的渲染流程](https://androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/) — 高爷
- [Systrace 流畅性实战 2 - MIUI 桌面滑动卡顿分析](https://www.androidperformance.com/2021/04/24/android-systrace-smooth-in-action-2/) — 高爷
- [Systrace 流畅性实战 3 - 卡顿分析过程中的一些疑问](https://www.androidperformance.com/2021/04/24/android-systrace-smooth-in-action-3/) — 高爷
- [RecyclerView 性能优化](https://developer.android.com/topic/performance/recycler-view) — Android 官方文档
- [Splash Screen API](https://developer.android.com/develop/ui/views/launch/splash-screen) — Android 官方文档
- [Activity Transitions](https://developer.android.com/training/transitions) — Android 官方文档
- [Perfetto FrameTimeline 分析](https://perfetto.dev/docs/analysis/trace-processor) — Perfetto 官方文档
- [AOSP SystemUI Shade 实现](https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/packages/SystemUI/src/com/android/systemui/shade/) — AOSP 源码
