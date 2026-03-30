## [研究] Android 13+ Vsync-AppSF 信号与 EventThread 架构重构

- **来源**: AOSP EventThread.cpp + SurfaceFlinger.cpp (googlesource.com) + Android Developers Blog
- **作者/机构**: Google AOSP
- **日期**: 2022-08 (Android 13) 至今持续演进
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**: 2.3 VSync 机制
- **映射锚点**: EventThread, vsync-appSf, vsync-sf, Choreographer NDK API, 版本演进
- **摘要**: Android 13 引入的 vsync-appSf 信号解决了旧架构中 sf EventThread 的双重职责问题，将 SurfaceFlinger 唤醒和 Choreographer 客户端同步彻底解耦。

### 关键发现

1. **vsync-appSf 解决的核心问题**：在 Android 13 之前，sf EventThread 同时承担两个职责——唤醒 SurfaceFlinger 进行合成、服务需要与 SurfaceFlinger 紧密同步的 Choreographer 客户端。这种双重职责导致时序歧义。vsync-appSf 将这两个职责分离：vsync-sf 专用于驱动 SurfaceFlinger 合成，vsync-appSf 专用于需要与 SurfaceFlinger 内部状态紧密同步的 Choreographer 客户端。

2. **NDK Choreographer API (API 33+)**：从 API 33 开始，应用可通过 `AChoreographer_vsyncCallback` 使用 NDK Choreographer API，支持正确的帧节奏 (frame pacing) 和选择未来帧进行渲染。提供多个可能的帧时间线信息，允许 App 根据渲染截止时间和期望的展示时间选择时间线。

3. **D-VSync 架构概念**：解耦渲染与显示 (Decoupled VSync) 允许帧在物理显示时间之前提前渲染，为计算密集型帧提供更大的时间窗口容忍负载波动，减少帧丢弃和渲染延迟。此概念在 Google Pixel 5 上有实现，集成在 Choreographer 内部。

### 可直接引用段落

> Introduced in Android 13, Vsync-AppSF addresses a previous design flaw where the SurfaceFlinger EventThread had dual responsibilities. This new signal decouples these roles, with Vsync-SF exclusively waking SurfaceFlinger for composition and Vsync-AppSF serving Choreographer clients requiring tight synchronization with SurfaceFlinger's internal state, eliminating timing ambiguities.
>
> — Android Platform Architecture Documentation

> As of API level 33, applications can utilize the NDK Choreographer API (AChoreographer_vsyncCallback) to follow proper frame pacing and even select a future frame for rendering. This provides information about multiple possible frame timelines, allowing apps to choose a timeline based on their rendering deadlines and desired presentation times.
>
> — Android NDK Documentation

### 与 queue.json 联动
- 优先级调整建议：无（2.3 已有素材在积累中）
- 素材路径建议：可补充到 2.3 的 material_paths + 2.9 渲染机制的版本演进
