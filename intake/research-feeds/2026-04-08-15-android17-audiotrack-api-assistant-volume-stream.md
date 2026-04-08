## [研究] Android 17 AudioTrack 新 API 与 Assistant 独立音量流
- **来源**: https://developer.android.com/sdk/api_diff/37/changes + https://developer.android.com/about/versions/17/features
- **作者/机构**: Google Android Team
- **日期**: 2026-04-08
- **四维评分**: 相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**: 1.16 Audio Pipeline 延迟与性能 · 16.5 Android 17 性能行为变更
- **映射锚点**: AudioTrack flush 精确控制 · 编解码器来源查询 · Assistant 音量独立
- **摘要**: Android 17 (API 37) 为 AudioTrack 新增精确 flush 控制（flushWrittenFramesFromPosition）、编解码器来源查询（getCodecProvenance）、以及 Assistant 专用音量流（USAGE_ASSISTANT），实现 Assistant 音量与媒体音量独立控制。

### 关键发现
1. **AudioTrack flush 精确控制**: 新增 flushWrittenFramesFromPosition(long, int) 方法，支持从指定位置精确 flush 已写入帧。配套 FLUSH_FROM_ACCURACY_BEST_EFFORT 和 FLUSH_FROM_ACCURACY_EXACT 两种精度模式，以及 getFlushWrittenFramesFromPositionSupport() 查询设备支持能力
2. **编解码器来源查询**: 新增 getCodecProvenance() 方法，允许应用查询音频数据使用的编解码器类型（硬件/软件/offload），对音频性能优化决策有直接影响
3. **Assistant 独立音量流**: Android 17 引入 USAGE_ASSISTANT 专用音量流，Assistant 音频与标准媒体流解耦。MODE_ASSISTANT_CONVERSATION 音频模式进一步提升音量控制一致性
4. **AAudio Offload 支持**: Android 16 起支持 AAudio Offload，允许直接将压缩音频数据（如 AAC/MP3）透传至硬件 DSP 解码，减少 CPU 占用和功耗

### 可直接引用段落
> Android 17 introduces a specific Assistant volume stream for applications utilizing USAGE_ASSISTANT. This decouples Assistant audio from the standard media stream, allowing users to independently control both volumes. Assistant apps can further improve volume control consistency by using the new MODE_ASSISTANT_CONVERSATION audio mode.

### 与 queue.json 联动
- 优先级调整建议: 无
- 素材路径建议: 可补充到 1.16 和 16.5 的 material_paths
