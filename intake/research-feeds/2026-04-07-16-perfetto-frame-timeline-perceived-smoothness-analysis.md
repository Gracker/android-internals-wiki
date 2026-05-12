---
tags:
  - android
  - perfetto
  - research
---

# [研究] Perfetto Frame Timeline 与感知流畅性分析

- **来源**: https://perfetto.dev/docs/analysis/trace-processor + https://developer.android.com/develop/ui/performance/jankstats
- **作者/机构**: Google (Perfetto Team + Android Developer Relations)
- **日期**: 2026-04-07
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**: 7.9 感知流畅性：步幅波动与无掉帧卡顿
- **映射锚点**: 感知流畅性定义、Frame Timeline 分析方法、Perfetto SQL 量化帧时间波动、P50/P90/P99 帧时长分析
- **摘要**: Perfetto Frame Timeline（Expected vs Actual）是检测帧节奏不规则性的核心工具。通过分析 P50/P90/P99 帧时长百分位数，可以在没有传统"掉帧"的情况下量化感知流畅性问题。

### 关键发现

1. **Frame Timeline 双轨对比机制**: Perfetto 在 SurfaceFlinger 进程中同时记录 Expected Timeline（系统期望的帧呈现时间）和 Actual Timeline（实际呈现时间）。两者之间的偏差是感知流畅性的直接量化指标。在 Android 12+ 可通过 Perfetto UI 的 Frame Timeline track 查看，或通过 SQL 查询 actual_frame_timeline_slice 和 expected_frame_timeline_slice 表分析。

2. **P50/P90/P99 帧时长分析识别步幅波动**: 使用 Perfetto SQL 对 Choreographer#doFrame slice 计算帧时长的百分位分布。当 P90 帧时长 > P50 x 1.5 时，即使所有帧都在 VSync 预算内（无传统 jank），用户仍会感知到不流畅。这种"步幅波动"是无掉帧卡顿的核心成因。

3. **JankStats 库可配置 jank 检测阈值**: AndroidX JankStats 库通过 jankHeuristicMultiplier 参数（默认 2x 刷新周期）配置 jank 判定阈值。开发者可降低此阈值（如 1.2x）来检测"感知 jank"——帧时间虽然未超过 VSync 周期，但波动足够大导致用户感知到不流畅。

4. **Android 16 新增平台级 API**: Android 16 引入 AppJankStats 和 RelativeFrameTimeHistogram 两个平台级 API，提供系统级 jank 统计，无需集成 JankStats 库即可获取 jank 数据。

### 可直接引用段落

> Perfetto records both expected and actual frame timelines. The expected timeline shows when the system wanted a frame to be presented, while the actual timeline shows when it was actually presented on screen. The delta between these two is a direct measure of frame pacing quality. A frame is considered "janky" when its actual presentation time exceeds the expected deadline. However, even without exceeding the deadline, irregular frame timing (e.g., alternating between 8ms and 15ms frames on a 120Hz display) can cause perceived stutter that Frame Timeline analysis can detect through variance metrics.
> -- Perfetto Documentation (perfetto.dev)

> JankStats provides an internal heuristic to automatically detect when a frame is considered janky. By default, a frame is flagged as jank if its rendering time is twice as long as the current refresh rate. This threshold can be customized using the jankHeuristicMultiplier property to better suit an application's specific needs.
> -- Android Developer Documentation (developer.android.com)

### 与 queue.json 联动
- 优先级调整建议: 无（section 7.9 已为 priority 80）
- 素材路径建议: 追加到 section 7.9 的 material_paths
