## [研究] Frame Timeline API 33 Perfetto 可视化分析指南：Expected vs Actual Timeline
- **来源**: https://perfetto.dev/docs / https://developer.android.com/reference/android/view/Choreographer / https://androidperformance.com
- **作者/机构**: Perfetto Team / Google Android Developers / Gracker (androidperformance.com)
- **日期**: 2025-2026（持续更新文档）
- **四维评分**: 相关性 5/5 · 技术深度 3/5 · 时效性 4/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**: 2.4 Choreographer 与渲染流水线
- **映射锚点**: Perfetto 可视化部分（行340-368）、Frame Timeline Track 描述、VSYNC-app/App target/SF actual 三条时间线对比
- **摘要**: API 33 引入的 Frame Timeline 在 Perfetto 中通过 Expected Timeline 和 Actual Timeline 两条 Track 可视化呈现。Expected Timeline 反映平台基于 Choreographer.getPreferredFrameTimeline() 的帧调度计划，Actual Timeline 记录应用实际渲染耗时。两者的偏差即为 jank。

### 关键发现

1. **Perfetto 中的三条关键 Track**：
   - **Expected Timeline**：系统为应用分配的帧时间窗口。每个 slice 的起始时间对应 Choreographer 回调的预期调度时间。这直接由 getPreferredFrameTimeline() API 决定。
   - **Actual Timeline**：应用实际完成帧渲染（含 GPU 工作）并发送给 SurfaceFlinger 合成的真实耗时。
   - **Choreographer#doFrame**：在应用主线程 Track 中可见，起始时间通常与 Actual Timeline slice 对齐。

2. **颜色编码规则**：
   - 绿色：帧在预期时间内完成，无 jank
   - 红色：应用导致 jank——Actual Timeline 超出 Expected Timeline 边界
   - 黄色：SurfaceFlinger 合成延迟导致的 jank（非应用责任）

3. **抓取命令**：
   ```bash
   adb shell perfetto -o /data/misc/perfetto-traces/trace.perfetto-trace -t 15s \
     sched freq idle am wm gfx view binder_driver hal
   ```

4. **Frame Timeline API 33 核心类**：
   - `Choreographer.FrameData`（API 33+）：`getFrameTimeNanos()`, `getLastFrameTimeNanos()`, `getIntervalNanos()`, `getDeadlineNanos()` 四个方法
   - `FrameTimeline` 类：`getPreferredFrameTimeline()` 和 `getFrameTimelines()` 通过 Choreographer 实例获取

5. **Expected Timeline 的物理含义**：Expected Timeline 并非简单的 VSync-app 时刻，而是综合考虑了 VSync offset、SurfaceFlinger 合成时间、Display 显示延迟后的"最优帧呈现时间"。这解释了为什么 Expected Timeline 和 VSYNC-app 之间存在可观测的时间差。

### 可直接引用段落

> When analyzing a Perfetto trace, two crucial tracks for understanding frame pacing are the "Expected Timeline" and the "Actual Timeline". The Expected Timeline visualizes the time allotted to an application for rendering each frame. The start time of a slice in this track corresponds to when the Choreographer callback was scheduled to run. This expected timing is directly influenced by the platform's preferred frame timeline, which Choreographer.getPreferredFrameTimeline() provides.

> By comparing these two timelines, developers can identify instances of jank — when the actual frame presentation time deviates from the predicted (expected) time. Perfetto uses color codes: green for a good frame, red for a janky frame where the app missed its deadline, and yellow if SurfaceFlinger caused the jank.

### 与 queue.json 联动
- 优先级调整建议：此素材直接回应 §2.4 deep tech review 中"Frame Timeline（帧时间线）缺少实际 Perfetto trace 示例"的 gap
- 素材路径建议：补充到 §2.4 的 material_paths
