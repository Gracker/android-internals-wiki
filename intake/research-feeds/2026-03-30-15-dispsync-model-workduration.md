## [研究] DispSync VsyncModel 内部模型与现代 WorkDuration 抽象

- **来源**: AOSP googlesource.com (DispSync.cpp, VsyncConfiguration.cpp, SurfaceFlinger.cpp)
- **作者/机构**: Google AOSP
- **日期**: 2024-2026（AOSP main 分支持续演进）
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 2.3 VSync 机制
- **映射锚点**: DispSync 内部模型, VsyncConfiguration, WorkDuration, PhaseOffsets 遗留路径, VsyncConfigSet, DispVsyncSource
- **摘要**: AOSP 最新分支中 DispSync 的内部 VsyncModel 参数详解，以及从 legacy PhaseOffsets 向现代 WorkDuration 抽象演进的关键架构变更。

### 关键发现

1. **DispSync 内部模型参数**：
   - `mPeriod`：刷新间隔（如 60Hz = 16,666,667ns）
   - `mPhase`：从时间零点到初始 VSync 事件的相位偏移（纳秒）
   - `mReferenceTime`：重新同步后第一个 VSync 事件的时间戳
   - 模型通过 `addResyncSample` 持续接收硬件 VSync 时间戳来校正

2. **VsyncConfiguration + WorkDuration 替代 PhaseOffsets**：在 AOSP main 分支中，`VsyncConfiguration` 抽象正取代 legacy PhaseOffsets 路径。新的 `WorkDuration` 方法基于 SurfaceFlinger 和 App 的工作时长来内部计算偏移配置，而非手动配置固定纳秒值。提供 `VsyncConfigSet` 按不同场景组织配置。

3. **DispVsyncSource 作为中间层**：SurfaceFlinger 创建 `DispVsyncSource` 实例，作为 DispSync 和 EventThread 实际回调之间的中间层。源码路径：`frameworks/native/services/surfaceflinger/`。

4. **SurfaceFlinger 模型精度监控**：SurfaceFlinger 持续评估 DispSync 模型精度，当检测到不准确时可触发通过 addResyncSample 重建模型。硬件 VSync (HW_VSYNC_0) 通常只在需要精确同步时才启用，以节省功耗。

### 可直接引用段落

> The internal model within DispSync is constructed by incorporating consecutive hardware VSYNC timestamps via the addResyncSample method. Key parameters of this model include mPeriod (the refresh interval), mPhase (the phase offset in nanoseconds from time zero to the initial VSYNC event), and mReferenceTime (the timestamp of the first VSYNC event after a resync).
>
> — AOSP DispSync.cpp analysis

> In the latest AOSP main branch, the VsyncConfiguration abstraction is becoming more prominent. It provides VsyncConfigSet organized by different scenarios, where WorkDuration is a modern approach to internally calculate offset configurations based on SurfaceFlinger and app work durations, replacing the legacy PhaseOffsets path.
>
> — AOSP Source Code Analysis

### 与 queue.json 联动
- 优先级调整建议：无
- 素材路径建议：补充到 2.3 VSync 机制的 material_paths
