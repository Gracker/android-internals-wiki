---
title: "Adaptive Layout 与多形态设备渲染适配性能"
chapter: "22.27"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37); Jetpack WindowManager / Compose Material 3 adaptive APIs"
tags: [adaptive, layout, desktop, foldable, large-screen, window-size-class, performance]
related_chapters: ["22.1", "22.3", "22.14", "2.28", "2.30"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "官方文档/每日信息/AOSP结构"
drafted_date: "2026-07-01"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; Android Developers large-screen/adaptive UI docs; Jetpack WindowManager and Compose adaptive docs"
confidence: medium
pipeline_stage: ready-for-review
task6_state: rework-ready
task9_state: rework-fixed
last_rework_at: "2026-07-25T21:35:11+08:00"
last_rework_run_id: "20260725-213511-rework-cbda85dc"
path: "src/part5-app/ch22-rendering-practice/27-adaptive-layout-multi-form-factor-performance.md"
sources:
  - type: official
    path: "https://developer.android.com/guide/topics/large-screens"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/support-multi-window-mode"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing"
  - type: official
    path: "https://developer.android.com/reference/androidx/window/layout/FoldingFeature"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: local
    path: "src/part1-fundamentals/ch02-rendering/2.28-Compose-Pausable-Composition-深度分析.md"
  - type: local
    path: "src/part2-rendering/ch02-rendering/2.30-android17-frametimeline.md"
  - type: local
    path: "src/part5-app/ch22-rendering-practice/14-desktop-windowing-large-screen-performance.md"
---

# 22.27 Adaptive Layout 与多形态设备渲染适配性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：WindowSizeClass 是布局分支，不是性能保证

WindowSizeClass（Compact / Medium / Expanded）适合作为大屏、折叠屏、桌面窗口和多窗口场景的布局分支输入。性能风险不来自分类计算本身，而来自分类变化后应用选择了多少新 UI、资源和状态重建。

**应用侧计算链路：**
- 平台 `WindowMetrics` 描述当前窗口边界，应用或 Jetpack WindowManager 再把宽高映射到 size class。
- Material 3 adaptive 文档采用常见宽度断点：Compact（小于 600dp）、Medium（600dp 到小于 840dp）、Expanded（840dp 及以上）。
- 在自由窗口、分屏和折叠状态变化中，窗口尺寸可能连续变化；应把 size class 当作低频布局状态，而不是每帧直接驱动复杂重组。

**性能守则：**
- 只在跨越断点时切换主导航结构；断点内的连续 resize 优先调整约束、间距和可见区域。
- `remember` / `derivedStateOf` / 稳定参数边界用于限制 Compose recomposition 范围。
- View 体系下，把 size class 映射到少量布局模式，避免每次 `onConfigurationChanged` 都重建整棵 View 树。
- 对复杂 list-detail / supporting pane 页面，用基准测试验证断点切换时的 `measure/layout/draw` 分布，而不是只看最终帧率。

[适用版本: Android 13 - Android 17]
[结构参考: developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes]

### 🔹 锚点 2：多窗口 resize 的成本主要落在应用布局树

多窗口和桌面窗口化场景会让 Activity 在更多尺寸下运行。系统负责窗口边界、Configuration 和 Surface 状态分发；应用侧的主要成本是响应这些变化时触发的布局测量、重组、资源切换和状态恢复。

**风险路径：**
- 窗口尺寸变化 → Configuration / WindowMetrics 更新 → Compose 或 View 布局约束变化。
- 约束变化会触发 measure/layout；如果页面存在深层嵌套、同步图片解码、过大的首屏列表或全局状态读取，慢帧会集中出现在 resize、最大化/还原和分屏切换期间。
- 对 Compose，`BoxWithConstraints`、`SubcomposeLayout`、Lazy 组件和 adaptive navigation 组件都可能成为重组边界；问题通常不是 API 本身，而是约束变化后执行了过多业务计算。

**优化策略：**
- 把 resize 期间必须同步完成的工作限制在布局约束和轻量状态映射；图片解码、数据库查询、网络请求应异步或预取。
- 用稳定 key 保持 Lazy 列表和 pane 内容身份，避免断点切换时丢失滚动位置或重建整页。
- 对可折叠、可展开、图片预览等非关键内容使用延迟组合/延迟加载，只测量当前可见区域。
- 对 View 布局，减少过深 ConstraintLayout/LinearLayout 嵌套，并检查 `requestLayout()` 是否被业务回调重复触发。

### 🔹 锚点 3：折叠屏铰链状态变化需要稳定状态模型

Jetpack WindowManager 通过 `WindowLayoutInfo` 暴露显示特征，`FoldingFeature` 可描述折叠区域、方向和状态。折叠状态变化可能导致布局从单 pane 切到双 pane，或改变内容避让区域。

**状态建模：**
- 把 `FoldingFeature` 视为布局输入：是否分隔内容、铰链方向、是否处于 half-opened 等状态。
- 状态变化不应直接清空页面数据；内容状态应提升到 ViewModel 或可保存状态容器中。
- 折叠/展开可能伴随 Activity 配置变化或重建，必须覆盖状态保存、恢复和滚动位置恢复。

**性能风险：**
- 单 pane ↔ 双 pane 切换时，导航栈、列表选择态、图片预览和详情页可能同时重组。
- 铰链区域避让计算如果散落在多个组件，会扩大重组范围。
- 折叠过程中重复读取传感器或窗口状态并启动同步业务逻辑，会把布局问题放大为主线程卡顿。

**实践建议：**
- 使用单一的 adaptive state（窗口 size class + folding feature + posture）生成页面模式。
- 在模式切换处保持内容身份稳定，优先移动已有内容而不是重新创建内容。
- 为折叠、展开、半开、外屏/内屏切换分别建立 Macrobenchmark 或手工 Perfetto 采样场景。

[结构参考: developer.android.com/reference/androidx/window/layout/FoldingFeature]

### 🔹 锚点 4：大屏渲染成本按像素和层数放大

大屏、外接显示器和桌面窗口会提高像素数量、可见内容数量和多窗口叠加概率。应用性能优化的重点是控制过度绘制、位图尺寸、文本列表密度和 Surface 合成压力。

**绘制与资源风险：**
- 4K 显示面积约为 1080p 的 4 倍；同样的 overdraw 在大屏上会消耗更多填充率和内存带宽。
- 大图如果按窗口最大尺寸同步解码，容易在 resize 或 pane 切换时制造内存峰值和 GC 压力。
- 平板/桌面同时展示更多列表项和详情内容，字体、图标和阴影缓存的工作集都会扩大。

**优化策略：**
- 图片按展示尺寸请求，使用缩略图、分级加载和缓存上限，不把手机资源简单放大到桌面窗口。
- 减少半透明全屏蒙层、重复背景和不必要的阴影；用 Layout Inspector / GPU overdraw 观察热点。
- 对大屏列表使用分页、占位骨架和可见区域预取，避免首屏一次性构建所有 pane 内容。
- 对多窗口应用，检查非焦点窗口是否仍在高频刷新动画、播放器预览或轮询任务。

### 🔹 锚点 5：Compose adaptive API 的边界使用

Compose adaptive layouts、WindowSizeClass、list-detail、supporting pane、navigation suite 等 API 适合表达多形态布局，但仍需遵守 Compose 性能基本原则：稳定输入、局部状态、惰性布局和可观测的重组范围。

**组件级关注点：**
- `BoxWithConstraints` 能根据约束分支 UI，但约束变化会重新执行其内容 lambda；复杂计算应移出组合阶段。
- Lazy 列表、pane 内容和导航项需要稳定 key，避免窗口尺寸变化时重建项目。
- Navigation rail / drawer / bottom bar 的切换应集中在高层 adaptive scaffold，避免多个子组件各自判断 size class。
- 动画过渡应有可取消和低端设备降级策略；不要让 resize 期间的动画与大图解码同时竞争主线程。

**验证方法：**
- 使用 Compose Layout Inspector 观察 recomposition 次数和布局层级。
- 使用 Macrobenchmark 覆盖启动、滚动、窗口模式切换、方向变化和典型 pane 切换。
- 用 Perfetto FrameTimeline 区分 App、RenderThread 和 SurfaceFlinger 侧慢帧，避免把系统合成问题误判为业务布局问题。

### 🔹 锚点 6：资源限定符和配置变更应服务于少量布局模式

大屏适配常用 `sw<N>dp`、`w<N>dp`、方向和密度限定符。限定符能降低运行时代码分支，但过多资源桶会提高维护成本，并在配置变化时扩大资源切换范围。

**资源治理：**
- 优先把资源限定符映射到少量产品模式：phone、foldable/tablet、expanded/desktop，而不是为每个尺寸单独维护布局。
- 大图、插画和视频封面不要仅依赖资源目录切换；应结合运行时目标尺寸和缓存策略。
- 把只影响间距、列数、pane 宽度的值放入 values 资源或 Compose token，避免复制整份布局。
- 配置变化时，确认是否真的需要重新 inflate 页面；可保存状态和局部重绘通常比整页重建更稳定。

**工程检查：**
- 清点 `layout-sw*dp`、`values-w*dp`、`drawable-*dpi` 的覆盖关系，删除重复或不可达资源。
- 在平板横竖屏、分屏、自由窗口和外接显示器下验证资源是否误匹配。
- 用启动 trace 检查首次 inflate、图片解码和字体加载是否集中在主线程。

### 🔹 锚点 7：性能验证要覆盖窗口形态 CUJ

Adaptive 布局不能只靠 Preview 验证。Preview 能发现视觉问题，性能仍需在真实设备、模拟器或可调整窗口环境中通过 trace 和 benchmark 观察。

**建议 CUJ：**
- Phone compact：启动、列表滚动、详情切换。
- Tablet / foldable medium-expanded：单 pane ↔ 双 pane、横竖屏、半开姿态切换。
- Multi-window：分屏进入/退出、窗口拖动 resize、焦点窗口切换。
- Desktop / external display：最大化、还原、拖拽到外接显示器、键鼠输入。

**指标与工具：**
- Macrobenchmark：启动、滚动、用户操作链路和 FrameTiming 指标。
- Perfetto FrameTimeline：定位 App、RenderThread、GPU/SurfaceFlinger 侧慢帧。
- Android Studio Layout Inspector：检查布局层级、recomposition 和过度嵌套。
- 内存分析：关注大图解码、资源切换、Activity 重建和多窗口并存时的峰值。

### 🔹 锚点 8：桌面窗口化下的应用责任边界

Android 17 基线下，桌面窗口化和大屏策略要求应用默认接受更多可调整尺寸。系统窗口管理、Z-order、SurfaceControl 事务和显示拓扑属于平台责任；应用侧应关注自身窗口内容如何在持续 resize、键鼠输入和多实例中保持稳定。

**应用侧风险：**
- 仍假设固定方向或固定宽高比，导致 expanded/desktop 宽度下内容拉伸或空白。
- 窗口最大化/还原时同步刷新全局主题、导航栈和大量图片。
- 多实例或多窗口中共享单例 UI 状态，导致焦点窗口切换后错误刷新。
- 非触摸输入路径没有单独测试，键鼠滚动、hover、快捷键可能触发额外重绘。

**治理清单：**
- Manifest、方向限制、可调整大小策略与 Android 16/17 大屏行为保持一致。
- 关键页面提供 compact、medium、expanded 三类布局验收标准。
- 多窗口下隔离 Activity / window 级状态，避免全局单例驱动所有窗口刷新。
- 在 Perfetto 中同时观察 Input、Choreographer、FrameTimeline、RenderThread 和 SurfaceFlinger 轨迹。

## 扩展

### 🔸 扩展点 1：Compose Multiplatform 共享 UI 的适配边界

Compose Multiplatform 可共享 UI 思路和部分组件，但 Android 应用性能结论仍应以 Android 运行时、Android Compose、RenderThread、SurfaceFlinger 和平台输入链路为准。跨平台桌面渲染后端的指标不能直接外推到 Android 大屏。

**AIW 口径：**本章只把 Compose Multiplatform 作为工程边界提醒，不使用未验证的桌面端 benchmark 推导 Android 17 主线结论。

### 🔸 扩展点 2：多显示器拓扑与应用侧观察点

多显示器由 DisplayManagerService、WindowManager 和 SurfaceFlinger 协同管理。应用侧应把外接显示器视为尺寸、密度、输入方式和生命周期组合变化，而不是只看分辨率变大。

**观察点：**
- 跨显示器移动后，资源、字体缩放、窗口 size class 和输入设备状态是否同步更新。
- 外接显示器断开时，Activity 状态能否回到内屏并保持内容身份。
- 大屏高分辨率下，图片、视频、动画和列表预取是否按当前窗口尺寸降级。

### 🔸 扩展点 3：Adaptive App Quality 的工程化验收

Adaptive App Quality 更适合作为验收清单，而不是单一分数。团队可以把它拆成可执行门禁：布局完整性、状态恢复、慢帧、内存峰值、输入延迟和多窗口兼容性。

**门禁建议：**
- 每个关键页面至少覆盖 compact、medium、expanded 三类宽度。
- 每个核心 CUJ 有 phone 与 large-screen 两组 benchmark 或 trace 样本。
- resize、方向变化、折叠姿态变化不丢失用户输入、滚动位置和导航状态。
- 所有性能结论标注测试设备、Android 版本、窗口模式和工具来源。

<!-- outline-end -->

> 本节内容已完成 rework：移除占位复查标记和未注明来源的绝对化数值，保留 Android 17 / android-17.0.0_r1 基线下可安全复查的应用侧性能实践。
