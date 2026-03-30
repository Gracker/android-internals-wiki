## [研究] Android VSync/DispSync 管线架构（官方源码级）

- **来源**: https://source.android.com/docs/core/display/improve-performance + https://cs.android.com (DispSync.cpp, SurfaceFlinger.cpp, Choreographer.java)
- **作者/机构**: Google AOSP / Android Source
- **日期**: 2026-03-30（持续更新的核心架构文档）
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**: 2.3 VSync 机制
- **映射锚点**: DispSync PLL, VSYNC-app/VSYNC-sf offset, HW_VSYNC_0, phase offset 配置, EventThread, 三缓冲管线
- **摘要**: Android 显示管线中 VSync 信号的完整分发架构，从硬件 VSync 到 DispSync 软件锁相环，再到 EventThread 分发给 Choreographer 和 SurfaceFlinger 的全链路机制。

### 关键发现

1. **DispSync 是软件锁相环 (PLL)**：它不直接转发硬件 VSync，而是通过 addResyncSample 接收 HW_VSYNC_0 时间戳，构建内部模型（mPeriod, mPhase, mReferenceTime），然后基于模型生成精确的周期性回调。核心源码路径：`frameworks/native/services/surfaceflinger/DispSync.cpp`。

2. **三信号架构 (HW_VSYNC_0 / VSYNC / SF_VSYNC)**：HW_VSYNC_0 标识显示器开始显示下一帧；VSYNC (VSYNC-app) 触发 App 读取输入并渲染；SF_VSYNC (VSYNC-sf) 触发 SurfaceFlinger 合成。三者周期相同但相位偏移不同，理想流水线状态：显示器展示帧 N、SurfaceFlinger 合成帧 N+1、App 渲染帧 N+2。

3. **Phase Offset 配置**：偏移量通过 `VSYNC_EVENT_PHASE_OFFSET_NS` 和 `SF_VSYNC_EVENT_PHASE_OFFSET_NS` 在 `BoardConfig.mk` 中配置，单位纳秒。默认为零（导致两帧延迟），非零配置可将延迟降低到一帧以内。偏移量过短会导致 App 来不及渲染，过长则抵消优化效果。

4. **DispSync 使用 retire fence 反馈**：HWC 的 retire fence 信号时间戳作为 DispSync 模型的反馈源，用于持续校正模型精度。当检测到模型偏差时，SurfaceFlinger 通过 addResyncSample 重建模型。

### 可直接引用段落

> DispSync acts as a software phase-locked loop (PLL) that maintains a model of the display's periodic hardware-based VSync events. It uses this model to schedule callbacks at precise phase offsets from the hardware VSync. DispSync takes HW_VSYNC_0 as a reference and utilizes feedback from retire fence signal timestamps from the HWC to refine its internal model.
>
> Key parameters of this model include mPeriod (the refresh interval), mPhase (the phase offset in nanoseconds from time zero to the initial VSYNC event), and mReferenceTime (the timestamp of the first VSYNC event after a resync).
>
> — source.android.com + AOSP DispSync.cpp

> The main source code for DispSync is at frameworks/native/services/surfaceflinger/DispSync.cpp, and EventThread at frameworks/native/services/surfaceflinger/EventThread.cpp. SurfaceFlinger registers with HWC to receive HW_VSYNC_0 events via onVsyncReceived, feeds them to mPrimaryDispSync via addResyncSample.
>
> — AOSP Source Code

### 与 queue.json 联动
- 优先级调整建议：2.3 VSync 机制从 priority 75 保持不变（已有核心素材）
- 素材路径建议：可补充到 2.3 的 material_paths
