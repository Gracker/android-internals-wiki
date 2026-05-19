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
related_chapters: ["2.20", "18.18", "22.1", "22.3", "22.13"]
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

<!-- outline-start -->
## 要点

### 🔹 桌面窗口化的应用侧性能问题
梳理外接显示器、自由窗口、最大化窗口、多实例和键鼠输入带来的渲染成本变化，区分系统窗口管理机制与应用侧布局、绘制、资源加载责任。

### 🔹 可调整尺寸与配置变更边界
覆盖窗口 resize、方向变化、宽高比限制被系统忽略、`smallestScreenWidth >= 600dp` 设备基线变化，以及 Activity 重建和状态保存对帧稳定性的影响。

### 🔹 Adaptive UI 的布局成本控制
围绕 Compose adaptive layouts、WindowSizeClass、list-detail、supporting pane 和 View 体系约束布局，分析断点切换、重组范围、measure/layout 次数和过度绘制风险。

### 🔹 多实例、拖拽与跨窗口数据流
整理多实例 Activity、drag-and-drop、复制粘贴、跨窗口状态同步的性能风险，明确主线程回调、序列化、图片解码和数据库事务的避让位置。

### 🔹 外接显示器与输入设备观察点
建立 Perfetto 观察清单：InputDispatcher、Choreographer、FrameTimeline、RenderThread、SurfaceFlinger、WindowManager 相关 trace，用于判断键鼠输入延迟、resize 抖动和窗口切换慢帧来源。

### 🔹 工程治理清单
给出大屏与桌面窗口化上线前检查项：manifest resizable 口径、布局断点测试、状态恢复、资源分桶、窗口尺寸压力测试、辅助输入设备测试和低端平板降级策略。

## 扩展

### 🔸 ChromeOS 与 Android 桌面窗口差异
对比 ChromeOS window management、Android tablet desktop windowing 和 Android 16 connected displays 的行为边界。

### 🔸 Predictive Back 与桌面窗口
补充桌面窗口下返回手势、键盘快捷键和窗口关闭事件的优先级关系，关联 22.13 节。

### 🔸 大屏性能自动化测试
整理 Macrobenchmark、UIAutomator、Screenshot testing 与 Perfetto TraceConfig 在不同窗口尺寸下的组合方案。

<!-- outline-end -->

桌面窗口化把 Android 应用从“单个全屏画布”推到“可连续调整尺寸的窗口”。渲染性能的风险点也跟着移动：窗口拖拽时的配置变更、断点切换时的布局重算、多实例带来的状态复制、外接显示器上的输入延迟，都会压到同一帧预算里。系统侧的 window / layer / display 会话见 2.20 节，freeform resize 与 BLAST 同步见 18.18 节；本节只写应用侧该怎么做、怎么测、怎么把问题归因到主线程、RenderThread 或 SurfaceFlinger。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md] 参考书把速度问题拆成 CPU 指令、缓存命中和任务调度三类成本，本节沿用这条思路：大屏不是简单把 UI 放大，而是让同一帧里出现更多 measure / layout / draw、更多图片与资源分桶选择、更多输入和窗口管理回调。[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md][结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md] 参考书对线程池、闲时预加载和 IO 等待的拆法，也适合放到窗口 resize：能提前准备的资源放到空闲阶段，用户拖拽窗口时只做尺寸计算和轻量状态切换。

## 桌面窗口化改变的是工作负载形态

Android 16 QPR3 的 connected display 让受支持手机或折叠屏连接外部显示器后启动桌面会话，应用可运行在 free-form 或 maximized window 中；受支持平板连接外屏时，桌面会话可跨两个显示器扩展，窗口、内容和光标能在显示器之间移动。[已验证: Android Developers Blog, android-developers.googleblog.com/2026/03/android-devices-extend-seamlessly-to.html]

这件事对 App 的压力集中在四个位置：

- **窗口尺寸不稳定**：用户拖动边缘时，`WindowMetrics`、`LocalConfiguration`、资源限定符和布局断点可能连续变化。每次变化都可能触发 `ViewRootImpl.performTraversals()` 或 Compose 重组。
- **可见内容更多**：桌面宽度下常见两栏、三栏甚至四栏布局。列表、详情、辅助面板同时可见，图片解码、分页加载和动画对象数量都会增加。
- **输入频率更高**：鼠标 hover、滚轮、键盘快捷键、拖拽手势进入已有输入队列。触屏时代被忽略的 pointer move 和 focus 变化，在桌面窗口里会变成稳定输入源。
- **状态副本更多**：多实例让同一个业务页面可能在两个 task 中同时打开。单例缓存、内存态草稿、数据库事务和通知跳转都要重新审查。

系统负责窗口边框、taskbar、display 会话和 layer 合成；应用负责声明自己能否调整尺寸、在任意 viewport 下给出稳定布局、把主线程回调压在帧预算内。应用侧写错时，trace 通常会出现 `Choreographer#doFrame` 变长、`performTraversals` 密集、RenderThread `DrawFrame` 排队、FrameTimeline 标记 App Deadline Missed。系统侧压力过高时，SurfaceFlinger 或 HWC 会成为慢帧来源。二者不要混在同一个结论里。

## 可调整尺寸与配置变更：把 resize 当成常态输入

Android 16 起，targetSdk 为 36 的应用在 `smallestScreenWidth >= 600dp` 的显示环境中，方向、宽高比和 resizability 限制会被系统忽略；Android 17 对 targetSdk 37+ 继续推进这条大屏基线。[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16][已验证: 官方文档, developer.android.com/about/versions/17/changes/ff-restrictions-ignored] 旧项目依赖 `screenOrientation="portrait"`、固定 `minAspectRatio` 或 `resizeableActivity="false"` 保持页面形态，在大屏和外接显示器上会失效。

应用要把窗口尺寸变化拆成三类处理：

| 变化类型 | 典型触发 | 性能风险 | 应用侧处理 |
|----------|----------|----------|------------|
| 连续 resize | 用户拖动窗口边缘 | 高频 `measure/layout`、断点来回切换、图片重新取样 | 用稳定断点和轻量 viewport state；不要在每次像素变化时重建页面模型 |
| 配置变更 | 方向、屏幕尺寸、密度、键盘可用性变化 | Activity 重建、状态恢复、资源重新选择 | 保存 UI state；把耗时恢复拆到异步任务；首帧只恢复骨架 |
| display 切换 | 内屏、外屏、跨屏移动 | buffer 重新分配、资源分桶变化、输入焦点变化 | 按 display / window 维度缓存渲染参数；不要假设全局只有一个窗口尺寸 |

`android:configChanges` 能减少 Activity 重建，但代价是应用自己处理资源、布局和状态更新。只为了“避免重建”把 `screenSize|smallestScreenSize|orientation` 全部接管，容易把重建成本改成一串不可控的手动刷新。更稳的做法是保留可恢复的状态模型，让 Activity 重建成本可预测；只有播放器、编辑器、复杂绘图页这类重建代价高的页面，再为特定配置项接管更新。

窗口拖拽期间要避免三类同步工作：

- 从主线程读取大文件、数据库或跨进程服务，尤其是根据新尺寸同步拉取内容。
- 在每次尺寸回调里重新 decode bitmap、重新创建 `Paint` / shader / path 缓存。
- 把断点变化直接绑定到网络分页、数据库查询或复杂排序。

[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md] 参考书从缓存命中率解释速度问题；桌面窗口里也一样，资源和布局参数要按使用频率分层。窗口连续变化时，热路径只读取当前断点、可见 pane 和轻量尺寸数据；图片、富文本、图表数据放到 resize 结束后或空闲阶段补齐。

## Adaptive UI：控制断点切换成本

Jetpack WindowManager 1.5.0 增加 Large 与 Extra-large 宽度窗口 size class：Large 覆盖 1200dp 到 1600dp，Extra-large 覆盖 1600dp 及以上。[已验证: Android Developers Blog, android-developers.googleblog.com/2026/03/android-devices-extend-seamlessly-to.html] Compose Material 3 Adaptive 的 `currentWindowAdaptiveInfo()` 支持通过 `supportLargeAndXLargeWidth = true` 纳入这两档断点。[已验证: 官方文档, developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes]

大屏布局的性能问题通常不在“用了几个 pane”，而在断点切换带来的副作用。比如从单栏切到 list-detail，再切到 supporting pane，如果每个 pane 都重新创建 view model、重新订阅流、重新拉取图片，resize 会被业务初始化成本拖住。

Compose 场景建议按下面的边界写：

- `WindowAdaptiveInfo` 和断点判断放在页面壳层，业务组件接收稳定的 layout mode，而不是直接读取窗口像素宽度。
- list-detail / supporting pane 的 pane 可见性变化只改变布局结构，不重建数据源。列表滚动位置、选中项、草稿内容放进可保存状态。
- `remember` / `derivedStateOf` 只包住会被频繁读取的轻量状态；图表、富文本解析、图片尺寸计算不要放在 composition 阶段。
- Lazy 列表在大屏上会同时展示更多 item，要复核 `key`、`contentType`、图片请求尺寸和 placeholder。否则窗口放大时会把 item 复用失败、图片解码和布局重算叠在一起。

View 场景的治理点更直接：减少无意义的层级嵌套，避免深层 `ConstraintLayout` 在连续 resize 中重复求解；隐藏 pane 不要继续参与测量；图片容器在断点变化后更新目标尺寸，但解码任务放到后台线程池。22.1 节已经覆盖布局层级、`ViewStub`、`merge`、异步 inflate 和 Compose / View 互操作，本节只补大屏差异：窗口尺寸变化会让这些成本重复发生。

这段 Compose 代码展示一个低成本断点入口；重点是把窗口信息压成 `DesktopLayoutMode`，不要让每个子组件各自订阅窗口尺寸。

```kotlin
enum class DesktopLayoutMode { SinglePane, ListDetail, SupportingPane, MultiPane }

@Composable
fun rememberDesktopLayoutMode(): DesktopLayoutMode {
    val adaptiveInfo = currentWindowAdaptiveInfo(
        supportLargeAndXLargeWidth = true
    )
    val widthClass = adaptiveInfo.windowSizeClass.windowWidthSizeClass

    return remember(widthClass) {
        when {
            widthClass.isWidthAtLeastBreakpoint(WIDTH_DP_EXTRA_LARGE_LOWER_BOUND) -> DesktopLayoutMode.MultiPane
            widthClass.isWidthAtLeastBreakpoint(WIDTH_DP_LARGE_LOWER_BOUND) -> DesktopLayoutMode.SupportingPane
            widthClass.isWidthAtLeastBreakpoint(WIDTH_DP_EXPANDED_LOWER_BOUND) -> DesktopLayoutMode.ListDetail
            else -> DesktopLayoutMode.SinglePane
        }
    }
}
```

这段代码是示意写法，断点常量以实际引入的 WindowManager / Material 3 Adaptive 版本为准。工程里更要关注它后面的数据流：`DesktopLayoutMode` 变化不应该让 repository、database observer 或图片 pipeline 全量重建。[已验证: 官方文档, developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes]

## 多实例、拖拽与跨窗口数据流

桌面窗口化鼓励用户把同一个 App 当成桌面软件使用。官方 desktop windowing 文档描述了多实例、可调整窗口、header bar、drag-and-drop 等能力；系统 UI 可根据 manifest 中的多实例声明暴露 “New Window” 入口。[已验证: 官方文档, developer.android.com/develop/adaptive-apps/guides/support-desktop-windowing]

多实例的性能风险来自共享状态：

- **全局单例缓存**：两个窗口同时编辑同一对象时，内存态缓存如果没有版本号或 owner，会互相覆盖。性能问题表现为重复刷新、重复 diff、重复数据库写入。
- **图片和大对象传递**：跨窗口拖拽图片、文件或富文本时，不要把大 bitmap 放进主线程回调。回调里只接收 URI / ClipData / MIME 类型，解码、校验和缩略图生成放到后台。
- **数据库事务**：两个窗口并行写入同一张表时，主线程 observer 可能收到密集 invalidation。需要把列表 diff、搜索索引更新、缩略图生成与 UI 帧分开。
- **跨 task 导航**：通知、deep link、分享入口可能命中已有窗口，也可能打开新窗口。路由层要能识别目标实例，避免所有窗口都响应同一事件。

[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md] 参考书用 Bitmap 创建和回收说明图片内存治理；桌面窗口里的图片风险更常见，因为窗口变大后请求尺寸上升，多 pane 又会提高同屏图片数量。图片加载库要按实际显示尺寸请求，不要因为外屏分辨率高就加载原图。大图拖拽时，先展示低分辨率预览，后台完成解码和色彩空间处理。

多窗口生命周期也要改观念。Android 多窗口和 multi-resume 下，可见 Activity 不一定失去 `RESUMED` 状态；焦点变化与可见性变化要分开处理，`onTopResumedActivityChanged()` 用来判断当前 Activity 是否拥有最高优先级输入焦点。[已验证: 官方文档, developer.android.com/develop/ui/views/layout/support-multi-window-mode] 视频播放、相机预览、地图定位和实时协作页面，不能只靠 `onPause()` 停止昂贵任务。更稳的策略是用窗口可见性、top-resumed、业务订阅人数和电量状态共同决定更新频率。

## Perfetto 观察：按输入、主线程、渲染提交、合成四段切开

桌面窗口的慢帧不要只看 App 主线程。外接显示器、自由窗口和高分辨率 monitor 可能把压力推到 SurfaceFlinger / HWC；键鼠输入又可能让 InputDispatcher 先排队。Perfetto 里建议按四段排查：

| 段落 | 观察对象 | 常见异常 | 判断方向 |
|------|----------|----------|----------|
| 输入 | InputDispatcher、InputReader、主线程 input callback | 鼠标移动、滚轮、拖拽事件密集；主线程消费慢 | 减少 pointer move 中的业务逻辑；节流 hover / drag 回调 |
| 主线程 | `Choreographer#doFrame`、`ViewRootImpl.performTraversals`、Compose trace、Binder callback | resize 时连续 traversals；composition 或 measure 变长 | 缩小重组范围；避免同步 IO；拆分断点切换副作用 |
| 渲染提交 | RenderThread `DrawFrame`、GPU completion、buffer dequeue / queue | 纹理上传、shader 编译、大图 draw 变长 | 预热 shader；限制图片尺寸；复用渲染对象 |
| 合成 | SurfaceFlinger、FrameTimeline、HWC composition | 多窗口 layer 增多、外屏分辨率高、HWC 资源不足 | 回到 2.20 / 18.18 判断系统合成压力，避免把系统瓶颈归咎给 App |

[来源: DeepResearch/2026-05-18-perfetto-jank-cuj-datagrid-scope-boundary.md] 本地调研确认，FrameTimeline 与 JankTracker 相关源码可从 `frameworks/base/libs/hwui/JankTracker.cpp`、`frameworks/base/core/java/android/view/ViewRootImpl.java`、`frameworks/native/libs/gui/include/gui/JankInfo.h` 和 Perfetto SQL 模块 `external/perfetto/src/trace_processor/metrics/sql/android/jank/cujs_boundaries.sql` 追踪。[已验证: AOSP/Perfetto source paths, local DeepResearch 2026-05-18]

第三方 App 不要依赖系统 CUJ 表一定有数据。本地调研记录里，Perfetto 的 `android.cujs.base` 默认更偏系统 UI / Google 进程的 CUJ marker；第三方 App 可以用 AndroidX JankStats、自定义 `Trace.beginSection()`，或者直接 join FrameTimeline 表做窗口 resize 区间分析。[来源: DeepResearch/2026-05-18-perfetto-jank-cuj-datagrid-scope-boundary.md]

下面的 SQL 用于从 FrameTimeline 看某个进程的实际帧与预期帧差值，字段名需按当前 Perfetto 版本校对。

```sql
SELECT
  a.name AS vsync,
  a.ts AS actual_start,
  a.ts + a.dur AS actual_end,
  e.ts AS expected_start,
  a.ts + a.dur - e.ts AS deadline_delta
FROM actual_frame_timeline_slice a
JOIN expected_frame_timeline_slice e
  ON a.name = e.name AND a.upid = e.upid
WHERE a.upid = $target_upid
ORDER BY a.ts;
```

窗口 resize 的 trace 建议同时记录 `wm`、`view`、`input`、`gfx`、`sched`、`freq`、`binder_driver`、`frame_timeline` 和 SurfaceFlinger 相关数据源。抓 trace 时要标记窗口尺寸变化的开始和结束，例如在测试代码中用 `Trace.beginSection("desktop_resize_start")` / `Trace.endSection()` 包住手动或自动 resize 步骤，后续 SQL 才能把帧数据限定到目标区间。

## 工程治理清单

桌面窗口化适配不要等到产品说“外屏体验不好”再查。上线前至少覆盖下面这组检查：

- **manifest 口径**：targetSdk 36/37 后，不再依赖方向、宽高比和不可调整尺寸声明维持页面形态；多实例只给能承受状态副本的 Activity 开启。
- **断点覆盖表**：至少覆盖 Compact、Medium、Expanded、Large、Extra-large 五类宽度；每类记录首帧时间、resize 过程慢帧、图片峰值内存和列表滚动稳定性。
- **状态恢复**：旋转、拖拽 resize、外接显示器插拔、多实例打开、进程被杀后恢复，都要验证选中项、滚动位置、草稿和正在播放内容。
- **资源分桶**：大屏图片按实际显示尺寸请求；低频大资源延迟加载；多 dpi 资源去重和图片压缩沿用 25 章包体积治理策略。[结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md]
- **输入设备**：鼠标 hover、右键、滚轮、键盘快捷键、Tab focus、拖拽文件和文本都要测；pointer move 回调不能直接触发业务查询。
- **低端平板降级**：在 CPU / GPU / 内存弱的设备上限制同时可见 pane 数、降低图片并发、关闭非必要动画，避免把桌面布局当成高端设备专属场景。
- **trace 基线**：每个关键页面保存全屏、分屏、freeform、外接显示器四组 trace。没有 trace 基线，后续回归只能靠主观感受。

这组清单里，最容易被忽略的是“窗口尺寸压力测试”。移动端测试常停留在几组静态尺寸，但桌面窗口的风险来自连续变化。测试脚本要让窗口宽度在 600dp、840dp、1200dp、1600dp 附近来回穿过，观察断点抖动、布局重算和数据源重建。

## 扩展：ChromeOS、Android 平板桌面窗口与 connected display

ChromeOS 上的 Android App 运行在 ARC / Waydroid 类容器环境中，窗口管理、输入设备和文件系统体验长期按桌面习惯设计；Android tablet desktop windowing 更接近 Android 原生窗口栈；Android 16 connected display 则把手机 / 折叠屏外接显示器纳入桌面会话。三者都要求应用可调整尺寸，但验证重点不同：

- ChromeOS 更关注键盘、鼠标、文件拖放、窗口最小尺寸和生命周期兼容。
- Android tablet desktop windowing 更关注平板本体的 freeform、多窗口和任务栏交互。
- Android 16 connected display 更关注内屏与外屏 session 关系、display 切换、外屏高分辨率和输入设备切换。[已验证: Android Developers Blog, android-developers.googleblog.com/2026/03/android-devices-extend-seamlessly-to.html]

工程上不要为三条线维护三套 UI。更稳的分法是统一用 adaptive layout model 表达窗口能力，再按平台差异补输入、文件、display 和生命周期测试。

## 扩展：Predictive Back、键盘返回与窗口关闭

桌面窗口里，“返回”不只来自边缘手势。用户可能按 Esc、Alt + Left、系统返回键，也可能点击窗口关闭按钮。22.13 节已经覆盖 predictive back 的手势进度和动画成本；桌面窗口场景要补两条边界：

- 键盘快捷键通常没有连续 progress，不能复用依赖 `progress` 的手势动画路径。应走离散返回或关闭流程。
- 窗口关闭要区分“关闭当前实例”和“回到上一页”。编辑器、表单、播放器这类页面要先确认未保存状态，再决定关闭窗口还是只 pop 当前页面。

返回处理的性能规则不变：progress 回调只做属性更新，提交阶段再做导航；键盘和关闭事件也不要在主线程做同步保存。需要保存草稿时，把轻量状态先落到内存模型，磁盘写入交给后台任务。

## 扩展：大屏性能自动化测试

大屏性能测试建议拆成三层：

- **Macrobenchmark**：覆盖页面启动、滚动、断点切换前后的关键交互。每轮输出 frame timing 和 trace，作为回归基线。
- **UIAutomator / instrumentation**：覆盖拖拽、键盘快捷键、焦点移动、复制粘贴和多窗口入口。窗口尺寸变化可结合测试设备能力或平台脚本完成。
- **Screenshot testing**：覆盖 Compact 到 Extra-large 的静态布局正确性，提前发现 pane 溢出、按钮不可达和空白区域过大。

自动化不能替代手工外屏测试。外接显示器的刷新率、分辨率、线缆、厂商桌面实现和输入设备组合会改变 trace 形态。自动化负责守住回归，外屏手测负责发现系统和设备差异。

## 小结

桌面窗口化的应用侧优化，要把窗口尺寸当成高频输入，把多实例当成常见状态，把键鼠和外屏当成基础测试环境。布局断点、状态恢复、图片尺寸、数据流和 trace 基线都写清楚后，慢帧归因会简单很多：App 主线程慢，就回到 22.1 / 22.3 修布局和重组；freeform / display 合成慢，就回到 2.20 / 18.18 看窗口、layer 和 SurfaceFlinger。
