---
tags:
  - android
  - jank
  - research
---

## [研究] Android View 层级性能：measure/layout 开销与 Perfetto 诊断方法

- **来源**: https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies + https://developer.android.com/topic/performance/vitals/measure-layout
- **作者/机构**: Google Android Team
- **日期**: 2025（持续更新）
- **四维评分**: 相关性 5/5 · 技术深度 3/5 · 时效性 3/5 · 可验证性 5/5 · **总分 16/20**
- **映射章节**: 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销
- **映射锚点**: performTraversals 管线、measure/layout 双 pass、ConstraintLayout vs RelativeLayout、Perfetto FrameTimeline、JankStats
- **摘要**: Android View 渲染管线中 measure/layout 阶段是 jank 的主要来源之一。深嵌套的 View 层级（特别是 RelativeLayout 和带 layout_weight 的 LinearLayout）会导致 O(n²) 的测量复杂度。ConstraintLayout 通过消除嵌套将层级扁平化，是官方推荐的基础优化手段。Perfetto 的 FrameTimeline 数据源可精确追踪每帧的 measure/layout/draw 耗时。

### 关键发现

1. **measure/layout 时间预算**：60fps 目标下每帧 16ms、90fps 下 11ms、120fps 下 8.33ms。measure + layout 阶段必须在这个预算内完成。RelativeLayout 和带 layout_weight 的 LinearLayout 会触发多次 measure pass，嵌套后复杂度指数级增长。

2. **ConstraintLayout 的核心优势**：通过单层约束系统消除嵌套，将传统的 LinearLayout 套 RelativeLayout 的多层结构扁平化为一层。Google 2017 年的 benchmark 数据显示，在相同 UI 下 ConstraintLayout 的 measure/layout 时间比传统嵌套布局快约 40%。

3. **Perfetto 诊断方法**：
   - `performTraversals` 在主线程 Trace 中可见，其子切片 `measure`、`layout`、`draw` 可分别看到耗时
   - FrameTimeline 数据源追踪帧从 App 渲染到 SurfaceFlinger 合成到 Display 上屏的全链路
   - SQL 查询可批量分析：`SELECT name, dur FROM slice WHERE name IN ('measure', 'layout', 'draw') AND track_id = (main thread track)`

4. **JankStats 库**：Jetpack 的 JankStats 库可在运行时检测 jank 并报告，包含帧耗时数据和当时的 UI 状态（哪个页面、哪个交互），用于线上监控而非开发调试。

5. **ViewStub 延迟加载**：对于不立即显示的 UI 区域，ViewStub 是零成本占位符（不创建 View 对象），调用 `inflate()` 或 `setVisibility(VISIBLE)` 时才真正创建 View。适合错误页、高级设置面板等低频 UI。

### 可直接引用段落

> The layout inflation and measure/layout phases are among the most expensive operations in the Android rendering pipeline. Each level of nesting increases the complexity of measure, layout, and draw passes, as the system must traverse the entire view tree multiple times per frame. RelativeLayout and LinearLayout with layout_weight can trigger multiple measure and layout passes of their children, leading to exponentially increased costs (O(n²) behavior) with each nesting level.
>
> — Source: https://developer.android.com/topic/performance/rendering/optimizing-view-hierarchies

> 在 Perfetto 中，View 的 performTraversals 调用链对应主线程上的一个 slice，其子切片 measure、layout、draw 分别标注了各阶段耗时。通过 FrameTimeline 数据源，可以追踪单帧从 App 侧的 Choreographer.doFrame() 到 SurfaceFlinger 的 Composition 再到 Display 上屏的完整生命周期，精确定位掉帧发生在哪个环节。
>
> — Source: https://perfetto.dev/docs/data-sources/frametimeline

### 与 queue.json 联动

- 优先级调整建议：维持 80。此素材提供了基础的 Perfetto 诊断方法论和层级优化策略，是该章节的入门级核心素材
- 素材路径建议：追加到 7.12 的 material_paths。需补充 AOSP 源码分析（ViewRootImpl.performTraversals、View.measure/layout 源码路径）和高爷博客的实际案例
- 交叉引用：与 2.5 Main/RenderThread（渲染管线全景）、7.8 RecyclerView（列表滑动的四级缓存）、8.6 Coroutine Performance（异步 inflate 的协程实践）直接关联
