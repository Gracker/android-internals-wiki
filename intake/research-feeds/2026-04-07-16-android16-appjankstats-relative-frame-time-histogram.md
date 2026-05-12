---
tags:
  - android
  - jank
  - research
---

# [研究] Android 16 AppJankStats 与 RelativeFrameTimeHistogram API

- **来源**: https://developer.android.com/develop/ui/performance/jankstats + Android 16 Beta 2 Release Notes
- **作者/机构**: Google (Android Platform Team)
- **日期**: 2026-04-07
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**: 7.9 感知流畅性 / 14.5 三方性能库
- **映射锚点**: 平台级 jank 检测 API、RelativeFrameTimeHistogram 帧时间分布、无掉帧卡顿的量化方法
- **摘要**: Android 16 Beta 2 引入了 AppJankStats 和 RelativeFrameTimeHistogram 两个平台级 API，提供系统级 jank 统计数据，无需集成第三方库。这些 API 可用于检测感知流畅性问题，包括无掉帧卡顿。

### 关键发现

1. **AppJankStats 平台级 API**: Android 16 新增的 AppJankStats API 提供系统级 jank 统计，无需集成 Jetpack JankStats 库。该 API 自动收集帧渲染时间和 jank 标记，应用可查询指定时间范围内的 jank 数据。核心优势：零代码侵入，系统自动收集。

2. **RelativeFrameTimeHistogram 帧时间分布直方图**: RelativeFrameTimeHistogram API 提供帧渲染时间的直方图分布，不仅标识 jank 帧，还展示所有帧的时间分布。这对于检测"步幅波动"至关重要——通过观察帧时间分布的方差和偏度，可以量化感知流畅性（即使没有超过 VSync 预算的帧）。

3. **与 Jetpack JankStats 的互补关系**: AppJankStats 提供系统级聚合数据（无需代码侵入），Jetpack JankStats 提供带 UI 状态上下文的逐帧数据（需代码集成）。两者互补：AppJankStats 用于快速发现 jank 问题窗口，JankStats 用于定位 jank 发生时的具体 UI 场景。

### 可直接引用段落

> Android 16 introduces platform-level APIs for identifying UI jank at runtime, specifically AppJankStats and RelativeFrameTimeHistogram. These are expected to integrate with the Jetpack JankStats library, indicating ongoing enhancements in platform-level jank detection. AppJankStats provides aggregated jank statistics at the system level without requiring library integration, while RelativeFrameTimeHistogram offers frame time distribution data that goes beyond simple jank/non-jank classification.
> -- Android 16 Developer Features (developer.android.com)

### 与 queue.json 联动
- 优先级调整建议: 无
- 素材路径建议: 追加到 section 7.9 和 section 14.5 的 material_paths
