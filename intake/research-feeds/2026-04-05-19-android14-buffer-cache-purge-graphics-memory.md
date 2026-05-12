## [研究] Android 14 Buffer Cache 强制清除：GraphicBuffer 内存优化
- **来源**：https://source.android.com/docs/core/graphics/bufferqueue (Android 14 changes)
- **作者/机构**：Google AOSP 团队
- **日期**：2023-2024（Android 14 变更，持续影响后续版本）
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**：2.2 BufferQueue 与缓冲区管理 / 7.3 内存泄漏检测与治理
- **映射锚点**：BufferQueue buffer cache、GraphicBuffer 生命周期、Composer HAL v3.2、MediaCodec Surface disconnect

### 摘要
Android 14 引入了 per-layer buffer cache 强制清除机制。此前，当 GraphicBufferProducer（如 MediaCodec）从 SurfaceFlinger 的 GraphicBufferConsumer 断开时（如停止播放视频），Composer HAL 和 SurfaceFlinger 之间的 buffer cache 会保留 buffer 不释放，导致显存浪费。新机制在 disconnect 时强制 purge 该 cache，减少高分辨率屏幕设备的显存消耗。

### 关键发现
1. **问题场景**：MediaCodec 断开 SurfaceView 的 Surface 时，Composer HAL 与 SurfaceFlinger 之间的 per-layer buffer cache 不释放，频繁启停视频的设备（高分辨率屏+内存受限）显存持续增长
2. **解决方案**：需要实现 Composer HAL API v3.2 才能获得最大内存节省；也可启用向后兼容选项
3. **BufferQueue 架构要点**：BufferQueue 分配 GraphicBuffer 通过 Gralloc allocator（vendor-specific HIDL），按 width/height/pixel format/usage flags 参数分配；buffer 通过 handle 传递避免内存拷贝
4. **Android 13 AutoSingleLayer**：Android 13 引入 AutoSingleLayer 配置，允许 SurfaceFlinger 在仅单个 layer 更新时 latch 未 signal 的 buffer

### 可直接引用段落
> Starting with Android 14, the system can forcefully purge a per-layer buffer cache. This cache, located between the Composer HAL and SurfaceFlinger, previously retained buffers even after a GraphicBufferProducer disconnected from SurfaceFlinger's GraphicBufferConsumer (e.g., when a MediaCodec disconnected from a SurfaceView). By purging this cache, Android 14 aims to reduce graphics memory consumption, particularly benefiting devices with high-resolution displays and limited memory when frequently starting and stopping videos.
> — AOSP Documentation, Android 14 Graphics Changes

### 与 queue.json 联动
- 素材路径建议：可补充到 2.2 BufferQueue 节
