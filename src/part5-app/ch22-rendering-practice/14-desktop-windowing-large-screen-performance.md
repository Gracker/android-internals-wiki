---
title: "桌面窗口化与大屏渲染性能实践"
chapter: "22.14"
section: "22.14"
status: ready-for-review
drafted_date: "2026-05-19"
applicable_versions: "Android 12L (API 32) - Android 17 (API 37); Jetpack WindowManager 1.3+; Jetpack Compose adaptive layouts"
last_verified: "2026-05-19"
last_verified_against: "Android Developers adaptive app docs; Android 16/17 behavior changes; Android Developers Blog 2026 desktop windowing; Perfetto FrameTimeline docs; AOSP/Perfetto source paths from local DeepResearch"
confidence: medium
tags: [desktop-windowing, large-screen, rendering, adaptive-ui, multi-window]
related_chapters: ["2.20", "18.5", "22.1", "22.3", "22.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "每日信息/官方文档/Android Developers Blog"
sources:
  - type: official
    path: "https://developer.android.com/develop/adaptive-apps/guides/support-desktop-windowing"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/support-multi-window-mode"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/app-orientation-aspect-ratio-resizability"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/03/android-devices-extend-seamlessly-to.html"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/03/Get-inspired-and-take-your-apps-to-desktop.html"
  - type: local
    path: "intake/daily-info/2026-05-19.md"
  - type: local
    path: "DeepResearch/2026-05-18-perfetto-jank-cuj-datagrid-scope-boundary.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
  - type: clipping
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
---

# 22.14 桌面窗口化与大屏渲染性能实践

桌面窗口化让一个 Activity 的可用区域在运行中连续变化。窗口拖拽会触发布局计算，跨显示器移动可能带来 density、Insets 与资源选择变化，多实例还会让同一份业务数据被多个 task 同时观察。分析这些现象时，需要同时保留应用线程、WindowManager、SurfaceFlinger 和目标 Display 四个视角。

平台源码固定为 Android 17 / API 37 / `android-17.0.0_r1`，kernel 调度与 fence 观察固定为 `android17-6.18-2026-06_r6`。版本沿革只用于解释兼容行为。系统侧窗口树与 Display 拓扑见 [2.20 多窗口与桌面模式渲染性能](../../part1-fundamentals/ch02-rendering/20-multiwindow-desktop-rendering.md)，PiP/freeform 的 geometry 与 BLAST 同步见 [18.5 多窗口、PiP 与自由窗口渲染](../../part2-performance/ch18-rendering-pipelines/05-android-view-multi-window.md#pip-与-freeform-的特殊边界)；以下集中讨论应用实现、测试与归因。

大屏不会凭空产生一种新渲染管线。它会增加同一帧中的 `measure`、`layout`、`draw`、图片请求、输入回调和窗口状态变化，也会放大缓存失效与线程排队。优化时仍按执行成本、等待时间、缓存命中和提交时序逐项取证。

## 桌面窗口化改变了哪些工作负载

[Android 16 QPR3 connected display](https://android-developers.googleblog.com/2026/03/android-devices-extend-seamlessly-to.html) 已进入正式可用阶段。受支持的手机或折叠屏连接外部显示器后，会在外屏启动桌面会话；支持桌面窗口化的平板可把会话扩展到两个显示器，窗口、内容和光标可跨屏移动。设备支持情况、厂商实现和显示器能力仍需实机确认。

应用侧压力通常落在四处：

- **viewport 连续变化**：`WindowMetrics`、`LocalConfiguration`、Insets 和资源限定符会随窗口变化，View 可能重复进入 `performTraversals()`，Compose 可能重新组合、测量和绘制。
- **同屏内容增加**：list-detail、supporting pane 或多列布局会扩大可见 item 数量，也会增加图片解码、文本布局、动画对象和内存占用。
- **输入事件变密**：鼠标移动、hover、滚轮、右键、键盘焦点和拖拽进入现有输入链。若每个 pointer move 都触发查询或大范围状态更新，主线程会在下一次 VSync 前积压。
- **状态并发增加**：两个 task 可以显示同一个文档、会话或数据库记录。进程级缓存、草稿、路由事件和写事务都要定义并发规则。

系统绘制 caption、维护 task 与 display 会话，并把各窗口 layer 交给 SurfaceFlinger 合成。应用负责根据当前 window bounds 布局内容、正确处理 Insets 和配置变化，并控制主线程工作量。`Choreographer#doFrame` 变长、`performTraversals()` 密集或 RenderThread 排队指向应用侧压力；多个应用都按时交 buffer 而 DisplayFrame 迟到时，才把重点转向 Shell、SurfaceFlinger、HWC 或显示驱动。

## Android 16 与 Android 17 的适配边界

方向、宽高比与 resizability 规则要按 targetSdk 和显示环境分开记录：

| 平台与 targetSdk | 适用显示环境 | 固定方向、宽高比和不可调整尺寸声明 | 迁移含义 |
|---|---|---|---|
| Android 16 / target 36 | `smallestScreenWidth >= 600dp` | 默认忽略；可临时声明 `android.window.PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY` 退出新行为 | 该属性只用于过渡，不能当长期方案 |
| Android 17 / target 37+ | 显示器 smallest width `> 600dp` | `screenOrientation`、固定方向的 `setRequestedOrientation()`、`resizeableActivity`、`minAspectRatio`、`maxAspectRatio` 等限制被忽略；Android 16 的临时 opt-out 已移除 | 页面必须填充可用窗口，不能依赖 pillarbox 保持旧比例 |

Android 17 仍有例外：按 `android:appCategory` 识别的游戏、用户在设备宽高比设置中显式选择应用默认行为，以及 smallest width 小于 `sw600dp` 的屏幕，不受这项变更约束。`600dp` 边界在 Android 16 与 Android 17 两份文档中的表述并不相同，测试用例应覆盖 600dp 附近并以目标版本设备的行为为准。规则详情见 [Android 16 行为变更](https://developer.android.com/about/versions/16/behavior-changes-16) 与 [Android 17 大屏限制变更](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored)。

桌面窗口兼容模式还要单独看。当前 [desktop windowing 指南](https://developer.android.com/develop/adaptive-apps/guides/support-desktop-windowing) 说明：锁定方向的应用在桌面窗口中仍可自由调整到不同方向；声明 `resizeableActivity="false"` 的应用可能由系统保持原宽高比并整体缩放。这个缩放行为属于桌面窗口兼容处理，不能据此推断 target 37 在大屏全屏/多窗口模式下仍会使用 pillarbox。

## 把 resize、configuration 与 display 切换分开处理

三类变化可能相邻发生，但成本和恢复责任不同：

| 变化 | 常见信号 | 风险 | 应用处理 |
|---|---|---|---|
| 连续 resize | window bounds、Insets、Compose configuration 连续更新 | 重复测量、断点抖动、图片请求尺寸反复变化 | 热路径只计算 viewport 与 layout mode；耗时数据准备移出尺寸回调 |
| configuration change | orientation、screen size、density、keyboard 等字段变化 | Activity 重建或 `onConfigurationChanged()`；资源重新选择 | 状态可保存、恢复可重复；首帧不等待大对象重建 |
| display 切换 | `displayId`、density、刷新率、color mode 或 window context 变化 | surface/buffer 重建、资源分桶和输入焦点变化 | 缓存按 window/display 能力建 key，禁止把首个显示器参数当进程常量 |

是否重建 Activity 取决于配置变化以及 manifest 中接管的 `configChanges`。在连续 resize 中，系统可能多次发送新配置；应用若声明自己处理某个字段，就必须更新该字段影响的资源、布局与状态。把 `screenSize|smallestScreenSize|orientation` 全部接管，只是把框架重建工作改为应用自行维护，并不会消除布局成本。

窗口拖拽期间，主线程避免执行以下操作：

- 同步读取文件、数据库或跨进程服务；
- 为每次像素变化重新解码 bitmap，或重建 `Paint`、shader、path 和文本布局缓存；
- 把断点变化直接绑定到分页、搜索、排序或网络请求；
- 在 `onConfigurationChanged()` 中重建整个依赖图。

resize 热路径只需要当前 bounds、Insets、断点和可见 pane。图片、富文本、图表等数据可按稳定业务 key 复用；目标尺寸变化时取消过期请求，并在后台生成新结果。若业务要求拖拽期间实时预览，可使用降采样或较低更新频率，同时用 trace 验证是否仍在帧预算内。

## Adaptive UI：断点只决定布局，不重建业务

截至 2026-07-29，Jetpack WindowManager 稳定版为 `1.5.1`；Large 与 Extra-large 断点在 `1.5.0` 加入。五档宽度定义如下：

| 宽度类别 | 当前 window 宽度 |
|---|---|
| Compact | `< 600dp` |
| Medium | `600dp ..< 840dp` |
| Expanded | `840dp ..< 1200dp` |
| Large | `1200dp ..< 1600dp` |
| Extra-large | `>= 1600dp` |

这些值描述应用当前可用窗口，不能替代设备类型判断。同一台平板会随分屏、自由窗口和旋转跨越多个 size class。Compose Material 3 Adaptive 可通过 `currentWindowAdaptiveInfo(supportLargeAndXLargeWidth = true)` 启用 Large 与 Extra-large；接口和断点见 [window size class 指南](https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes) 与 [WindowManager release notes](https://developer.android.com/jetpack/androidx/releases/window)。

下面的示例把 size class 映射成页面级布局模式。常量使用 `WindowSizeClass` 命名空间，避免依赖不明确的顶层导入。

```kotlin
enum class DesktopLayoutMode {
    SinglePane,
    ListDetail,
    SupportingPane,
    MultiPane,
}

@Composable
fun desktopLayoutMode(): DesktopLayoutMode {
    val widthClass = currentWindowAdaptiveInfo(
        supportLargeAndXLargeWidth = true,
    ).windowSizeClass

    return when {
        widthClass.isWidthAtLeastBreakpoint(
            WindowSizeClass.WIDTH_DP_EXTRA_LARGE_LOWER_BOUND
        ) -> DesktopLayoutMode.MultiPane
        widthClass.isWidthAtLeastBreakpoint(
            WindowSizeClass.WIDTH_DP_LARGE_LOWER_BOUND
        ) -> DesktopLayoutMode.SupportingPane
        widthClass.isWidthAtLeastBreakpoint(
            WindowSizeClass.WIDTH_DP_EXPANDED_LOWER_BOUND
        ) -> DesktopLayoutMode.ListDetail
        else -> DesktopLayoutMode.SinglePane
    }
}
```

这个映射只是产品策略示例。Medium 是否使用双栏、Large 是否展示 supporting pane，要由信息密度、最小 pane 宽度和 compact height 共同决定。`DesktopLayoutMode` 变化应复用同一 repository、数据库观察流和页面状态；它只改变内容如何排布。

Compose 页面还要检查这些细节：

- 页面壳层读取 `WindowAdaptiveInfo`，子组件接收稳定的 layout mode 和数据，避免每一层都读取原始宽度。
- `remember` 只能保存计算结果，不能把过期窗口信息固定住；`derivedStateOf` 适合减少派生状态的无效通知，不负责把解析或 IO 移出主线程。
- pane 切换时保留 list key、滚动位置、选中项和草稿；若隐藏内容仍留在 composition 中，要确认其测量、动画和订阅是否仍在运行。
- Lazy 列表扩大可见范围后，检查稳定 `key`、`contentType`、图片请求尺寸与预取量，防止窗口放大时同时出现复用失败和解码峰值。

View 页面应减少深层重复测量。不可见 pane 若无需保留当前 View 状态，可从活动层级移除或使用 `GONE`；仅设置透明度不会阻止测量、布局或绘制相关工作。图片容器可以在布局稳定后提交目标尺寸，解码仍放后台线程。[22.1 布局优化](01-layout-optimization.md) 与 [22.3 Compose 性能优化](03-compose-performance.md) 继续覆盖通用布局和重组问题。

`WindowEngagementInfo.EngagementMode.PRECISE_POINTER` 可用于识别精确指针参与，但截至复核时它属于 WindowManager `1.6.0-alpha05` 预览线。稳定版项目不应把该 API 当作 `1.5.1` 能力；可以继续用输入事件、`InputDevice` 和产品配置选择交互密度，并在升级预览依赖时单独隔离兼容代码。

## 多实例、拖拽与共享状态

Android 15 起，应用可在 `<application>` 中声明 `android.window.PROPERTY_SUPPORTS_MULTI_INSTANCE_SYSTEM_UI=true`，让支持的系统 UI 提供 “New Window” 等入口。它表达的是系统 UI 可以发起多实例，并不自动解决 launch mode、task 路由、状态隔离或并发写入。桌面窗口中新 task 通常对应新窗口，任何主动创建多个 task 的路径都要重新走一遍用户流程。

多实例状态建议分为三层：

- **实例内 UI 状态**：滚动位置、临时选择、pane 展开状态归当前 task/Activity，使用稳定实例 key 保存。
- **共享业务状态**：文档、会话和数据库记录由 repository 提供单一数据源，并使用版本号、事务或冲突策略处理并发写入。
- **进程级资源**：图片缓存、连接池和线程池可以共享；缓存条目不能隐含“当前窗口”或“当前编辑者”。

进程级 singleton 与数据库一致性属于两个问题。给内存对象加锁无法替代数据库事务；数据库串行写入也不会阻止两个窗口在 UI 层覆盖彼此的临时草稿。每个可编辑对象都要明确 owner、revision 和冲突提示。

拖拽回调中只传递轻量描述：

- 文本和小型元数据使用 `ClipData`；
- 图片、文件和富内容使用 URI，并按来源请求 drag-and-drop 权限；
- bitmap 解码、MIME 校验、缩略图生成和导入事务放到后台；
- 不把大对象序列化进 Intent 或跨 Binder 传递。

Android 15 的 `DRAG_FLAG_GLOBAL_SAME_APPLICATION` 允许同一应用的可见窗口参与跨窗口拖拽；`DRAG_FLAG_START_INTENT_SENDER_ON_UNHANDLED_DRAG` 可在空白区域未处理 drop 时通过 `IntentSender` 启动新实例。两者的适用条件和权限处理见 [desktop windowing 多实例指南](https://developer.android.com/develop/adaptive-apps/guides/support-desktop-windowing#multitasking-and-multi-instance-support)。

多 pane 会同时增加图片数量，外屏也可能提高单张图的目标尺寸。图片加载应按控件显示尺寸请求，并设置可解释的内存/磁盘缓存策略；高分辨率显示器不等于每张图都要解码为原图。

## Multi-resume：可见、RESUMED、焦点与独占资源

Android 10 / API 29 起，多窗口和多显示器支持 multi-resume，多个 Activity 可以同时处于 `RESUMED`。Activity 仍可能因透明窗口、不可聚焦状态或 PiP 等条件进入暂停；通知栏打开时也可能没有 Activity 获得焦点。

`onTopResumedActivityChanged()` 表示 Activity 获得或失去 top-resumed 位置，适合协调相机、麦克风等独占资源。它不是通用的“窗口可见”回调，也不能保证 Activity 一定经历 `true` 状态；官方 API 允许 Activity 从 `onResume()` 直接进入 `onPause()`。生命周期细节见 [multi-window 与 multi-resume 指南](https://developer.android.com/develop/ui/views/layout/support-multi-window-mode) 和 [`Activity.onTopResumedActivityChanged()`](https://developer.android.com/reference/android/app/Activity#onTopResumedActivityChanged%28boolean%29)。

视频、地图、协作光标和实时数据页面要分别定义：

- 不可见时是否停止；
- 可见但未 top-resumed 时是否降帧、静音或降低订阅频率；
- 独占硬件被其他应用抢占时如何响应 availability callback；
- 多个本应用窗口是否允许同时播放或采集。

只在 `onPause()` 中停止所有工作，会遗漏 multi-resume 下仍需降载的可见窗口；只看 top-resumed 又可能错误停止可见内容。策略应由可见性、生命周期、top-resumed、资源可用性和业务意图共同决定。

## 从 resize 输入到 Display present 的证据链

多窗口慢帧按以下顺序观察：

| 阶段 | 关键证据 | 可以回答的问题 |
|---|---|---|
| 输入 | InputReader/InputDispatcher、目标窗口、主线程 input callback | 事件是否送达正确窗口，主线程是否来不及消费 |
| UI | `Choreographer#doFrame`、`performTraversals()`、Compose composition/layout/draw、Binder 调用 | 哪次状态变化触发了布局，CPU 时间花在哪里 |
| RenderThread / buffer | `DrawFrame`、GPU submit/completion、`dequeueBuffer`、`queueBuffer`、`BufferTX - <layer>` | 应用何时画完并提交，是否等待 slot、fence 或 GPU |
| WMS / Shell | configuration、relayout、WCT、transition leash、sync group、bounds/crop | task geometry 与应用内容何时更新 |
| SF / Display | SurfaceFrame、DisplayFrame、layer latch、composition type、present fence | 本帧是否被采纳并在目标 Display 的合成周期中 present |

这里有三个不能合并的概念：

- **geometry**：Task/window bounds、leash position/crop 和 layer transform；
- **buffer**：应用按某个尺寸绘制并通过 BLAST/BufferQueue 提交的内容；
- **present**：SurfaceFlinger 针对目标 Display 完成该轮合成并交给显示栈的时间边界。

resize 期间可以暂时出现“新 geometry + 旧 buffer”，系统会缩放旧内容或使用 snapshot 覆盖重绘间隙。`queueBuffer()` 返回只证明 Producer 完成 CPU 侧提交；GPU 可能仍在写，transaction 可能尚未被 SurfaceFlinger latch，该帧也可能错过目标 present。判断“用户已经看到”至少要继续核对 `BufferTX`、latch、FrameTimeline actual slice 和目标 Display 的 present timing。

同一进程有多个窗口时，每个窗口拥有自己的 `ViewRootImpl` 和 buffer 周转，但主线程 Looper 与进程级 RenderThread 可能共享。窗口 B 的 `DrawFrame` 很短，也可能因排在窗口 A 后面而错过 deadline。跨进程时则先分别证明各应用 SurfaceFrame 是否按时，再检查它们汇入的 DisplayFrame。

## FrameTimeline：按 token 关联，禁止按 name 猜

[Perfetto FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline) 提供 `expected_frame_timeline_slice` 与 `actual_frame_timeline_slice`。App SurfaceFrame 用 `surface_frame_token` 对齐预期和实际工作；SurfaceFlinger DisplayFrame 使用 `display_frame_token`。一个 DisplayFrame 可以包含多个进程的 SurfaceFrame，两种 token 负责的含义不同。

下面的 SQL 只比较目标应用窗口的 actual SurfaceFrame 与 expected SurfaceFrame。`$layer_glob` 应包含目标 Activity/window 的稳定片段，例如 `*com.example/.MainActivity*`。

```sql
WITH actual_app AS (
  SELECT
    upid,
    surface_frame_token,
    display_frame_token,
    layer_name,
    ts AS actual_start_ns,
    ts + dur AS actual_end_ns,
    jank_type,
    present_type
  FROM actual_frame_timeline_slice
  WHERE upid = $target_upid
    AND surface_frame_token != 0
    AND layer_name GLOB $layer_glob
),
expected_app AS (
  SELECT
    upid,
    surface_frame_token,
    ts AS expected_start_ns,
    ts + dur AS expected_end_ns
  FROM expected_frame_timeline_slice
  WHERE upid = $target_upid
    AND surface_frame_token != 0
)
SELECT
  a.surface_frame_token,
  a.display_frame_token,
  a.layer_name,
  e.expected_start_ns,
  e.expected_end_ns,
  a.actual_start_ns,
  a.actual_end_ns,
  a.actual_end_ns - e.expected_end_ns AS overrun_ns,
  a.jank_type,
  a.present_type
FROM actual_app AS a
JOIN expected_app AS e
  USING (upid, surface_frame_token)
ORDER BY a.actual_start_ns;
```

`overrun_ns > 0` 只表示 actual end 晚于 expected end，原因仍要回到 `jank_type`、UI/RenderThread、GPU 和系统线程。若同一 token 出现多个 layer 记录，应进一步限定 `layer_name` 或在聚合前去重。随后用 `display_frame_token` 查 SurfaceFlinger 行，确认该应用帧对应的 DisplayFrame 是否也迟到。原先按 `name + upid` 关联会把同名或相邻帧配错，不能用于 deadline 计算。

第三方应用也不应假设系统 CUJ 表总有 marker。可以使用 AndroidX JankStats、自定义稳定 trace section，或直接按 FrameTimeline token 分析。自定义 section 名保持低基数，例如在自动化 resize 动作外层使用 `Trace.beginSection("desktop_resize")` 与 `Trace.endSection()`；尺寸、文档 ID 等高变化值放日志或测试参数，不拼进 section 名。

采集配置要区分数据源：

- `android.surfaceflinger.frametimeline` 记录 FrameTimeline；
- ftrace 记录 `sched_switch`、wakeup、CPU frequency、binder driver 等内核事件；
- atrace 类别按需要启用 `gfx`、`view`、`wm`、`input` 等；
- SurfaceFlinger、WindowManager/Shell 与 GPU 数据源按设备和 Perfetto 版本选择。

只写一串类别名并不能保证 trace 中有对应数据。抓取后先检查目标线程、FrameTimeline 表和 SurfaceFlinger 轨是否存在，再开始计算。

## Android 17 源码与 kernel 锚点

应用侧结论可沿以下 Android 17 源码入口核对：

| 核查点 | 固定源码 | 关注内容 |
|---|---|---|
| traversal 与 relayout | [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java) | configuration、Insets、`performTraversals()`、relayout 条件和 draw |
| task 与 Activity 状态 | [`Task.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/Task.java)、[`ActivityRecord.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityRecord.java) | bounds、windowing mode、configuration 与生命周期 |
| WindowManager | [`WindowManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowManagerService.java)、[`BLASTSyncEngine.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java) | relayout、surface placement、参与同步的 WindowContainer |
| buffer 提交 | [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp) | buffer transaction、frame timeline info 与回调 |
| SF 帧归因 | [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp) | SurfaceFrame、DisplayFrame、present/jank 分类 |

kernel 锚点只回答调度、频率和 fence 层问题：

- [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c) 与 [`drivers/cpufreq/cpufreq.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/cpufreq.c)：线程运行/等待和 CPU 频率事件；
- [`drivers/dma-buf/dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)：GPU、显示和 buffer 同步所用 fence 基础。

公共 common kernel 无法说明某台设备的 DPU、HWC plane、GPU 驱动或外接显示链路。此类结论需要 vendor trace、设备驱动符号和实机对照。

## 上线前的检查表

- **平台规则**：target 36 和 target 37 分开测试；不要依赖固定方向、宽高比或不可调整尺寸维持布局。
- **连续尺寸**：窗口宽度反复跨过 600dp、840dp、1200dp、1600dp，记录断点抖动、布局次数、慢帧和图片请求。
- **极端 viewport**：桌面窗口最小尺寸、compact height、超宽窗口、caption/IME/cutout Insets 都要覆盖。
- **状态恢复**：旋转、resize、跨显示器移动、进程重建、多实例打开后，验证滚动位置、选中项、草稿和播放状态。
- **多实例一致性**：两个窗口并发编辑、删除、撤销和接收 deep link，确认 revision 与冲突策略。
- **图片与内存**：按显示尺寸请求资源，限制并发解码；比较单窗与多 pane 的 Java/native/GPU 峰值。
- **输入设备**：hover、右键、滚轮、Tab focus、快捷键、文件/文本拖拽和权限拒绝路径都要测。
- **性能证据**：关键页面保存全屏、分屏、freeform 和外接显示器 trace，并记录 displayId、分辨率、刷新率、窗口 bounds 与设备版本。
- **弱设备策略**：根据测量结果减少同时可见 pane、图片质量或装饰动画；不要仅凭设备名称决定。

资源分桶仍按实际需求设计。外屏分辨率高不代表密度一定更高；选择 drawable、图片请求尺寸和缓存 key 时，应使用当前 window/display 的 density 与控件像素尺寸。

## ChromeOS、平板桌面窗口与 connected display

ChromeOS 的 Android 运行环境是 ARC。旧设备曾使用 ARC++ 容器，当前架构主要是 ARCVM：完整 Android 栈运行在基于 crosvm/KVM 的虚拟机中，并与 ChromeOS host 集成。Waydroid 不属于 ChromeOS 官方 Android App 运行架构。架构说明见 [ChromeOS.dev 的 ARCVM 介绍](https://chromeos.dev/en/posts/making-android-runtime-on-chromeos-more-secure-and-easier-to-upgrade-with-arcvm)。

三类环境可以共用一套 adaptive layout model，但验证重点不同：

- **ChromeOS**：ARCVM/host 交互、x86 设备、自由窗口、文件系统、键盘鼠标与 ChromeOS 生命周期策略；
- **Android 平板 desktop windowing**：本机 freeform、taskbar/caption、Insets、触控与指针混合输入；
- **Android 16 QPR3 connected display**：内外屏会话关系、跨 display 移动、密度/刷新率变化和外屏输入。

不要根据 “Chromebook”“tablet” 或 “external display” 直接选择页面结构。布局由当前 window size class 和 posture 决定；文件、输入与会话差异由能力检测和平台测试补充。若采用 `WindowEngagementInfo` 的精确指针模式，还要遵守前述预览依赖边界。

## Predictive Back、键盘返回与关闭窗口

桌面窗口中的离开动作可能来自边缘手势、系统返回键、Esc、Alt+Left、应用快捷键或 caption 的关闭按钮。它们不一定拥有相同语义：

- Predictive Back 可带连续 progress，动画回调只做轻量属性更新，提交后再改变导航状态；
- 键盘返回通常是离散事件，不应伪造 progress 驱动手势动画；
- 关闭窗口针对当前 task/实例，未必等价于导航栈 `pop`；
- 未保存内容的确认流程要归一，避免每种入口维护一份保存逻辑。

磁盘保存和远端同步不应阻塞返回或关闭回调。先把轻量草稿写入内存状态或可靠队列，再异步持久化；若业务要求确认写入成功才能关闭，要给出明确等待状态和失败处理。[22.13 Predictive Back](13-predictive-back-performance.md) 继续说明回调顺序与动画预算。

## 大屏性能自动化

自动化建议分为三层：

- **Macrobenchmark**：测启动、滚动、pane 切换等可重复交互，输出 frame timing 与 Perfetto trace。
- **UIAutomator / instrumentation**：驱动窗口尺寸、焦点、键盘、拖拽和多实例入口；设备不开放某项窗口控制时，记录该限制并使用受支持的 shell/测试 API。
- **Screenshot testing**：覆盖五档宽度、compact height、Insets 和字体缩放，发现溢出、遮挡、不可达控件与异常空白。

静态截图不能发现连续 resize 的断点抖动，自动化 trace 也不能覆盖所有外屏链路。外接显示器的分辨率、刷新率、线缆、厂商桌面实现和输入设备会改变行为，应保留实机手测，并让失败报告携带完整环境信息。

## 小结

桌面窗口化的核心要求，是把 window bounds 当运行时输入，把实例状态与共享业务状态分开，并用 SurfaceFrame/DisplayFrame 证据判断慢帧发生在哪一层。应用线程迟到时回到布局、重组、资源和数据流；应用按时提交而目标 DisplayFrame 迟到时，再进入 WindowManager/Shell、SurfaceFlinger、HWC 和设备驱动。Android 17 扩大了应用必须适配自由尺寸的范围，但没有替换 BLAST、FrameTimeline 或 SurfaceFlinger 的主路径。
