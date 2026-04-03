## [研究] Media3 1.10 动态调度 + Compose 性能最佳实践：视频 Feed 优化
- **来源**：https://android-developers.googleblog.com/ (Media3 1.10 release); https://developer.android.com/media/media3
- **作者/机构**：Google Media3 Team
- **日期**：2026-03-30
- **四维评分**：相关性 3/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 16/20**
- **映射章节**：§7.7 Compose 性能优化 / §2.11 Flutter 渲染管线与性能（跨框架对比）
- **映射锚点**：Compose 性能最佳实践、视频播放性能、Player 预热与池化
- **摘要**：Media3 1.10（2026-03-30 发布）引入实验性动态调度（experimentalSetDynamicSchedulingEnabled()），通过 ExoPlayer.Builder 启用更高效的播放循环调度。同时 media3-ui-compose-material3 模块新增 Player/ProgressSlider/PlaybackSpeedControl 等 Material3 组件，推荐使用原生 PlayerSurface 替代 AndroidView 嵌入。Player 池化和预热（prepare() 在视频进入视口前调用）可显著减少视频加载时间和启动延迟。

### 关键发现
1. **动态调度机制**：Media3 1.10 通过 experimentalSetDynamicSchedulingEnabled() 优化核心播放循环的调度，减少不必要的唤醒和 CPU 开销。这对长视频播放和后台音频场景的功耗优化尤为关键。
2. **Compose 原生集成**：推荐从 AndroidView 嵌入迁移到 media3-ui-compose 的 PlayerSurface，避免 View-Compose 互操作开销。新增的 Material3 Composable 组件（Player/ProgressSlider/PlaybackSpeedControl）提供开箱即用的播放 UI。
3. **视频 Feed 性能优化模式**：Player 池化（复用 ExoPlayer 实例）+ 预热（prepare() 在视口外调用）+ derivedStateOf 延迟状态读取 + remember 缓存昂贵计算，是视频 Feed 场景的标准性能模式。低内存设备上需注意 Player 实例数量限制。

### 可直接引用段落
> Media3 1.10 includes experimental support for a more efficient scheduling of the core playback loop, which developers can enable using experimentalSetDynamicSchedulingEnabled() via ExoPlayer.Builder. Player pooling and prewarming (calling exoPlayer.prepare() before a video enters the viewport) are crucial techniques for optimizing performance in video feeds, significantly reducing video loading times and startup latency.
>
> — 来源：Google Android Developers Blog, Media3 1.10 Release, 2026-03-30

### 与 queue.json 联动
- 优先级调整建议：freshness-007 (ch07-smoothness/07-compose-performance.md) 可标记为已研究并补充素材
- 素材路径建议：可补充到 §7.7 Compose 性能优化的 material_paths
