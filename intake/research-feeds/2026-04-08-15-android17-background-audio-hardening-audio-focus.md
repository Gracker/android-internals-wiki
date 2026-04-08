## [研究] Android 17 (API 37) 后台音频强化：Audio Focus 与播放管控全面收紧
- **来源**: https://developer.android.com/about/versions/17/behavior-changes-17#audio-hardening
- **作者/机构**: Google Android Team
- **日期**: 2026-04-08
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 1.16 Audio Pipeline 延迟与性能 · 16.5 Android 17 性能行为变更
- **映射锚点**: AudioFlinger 后台播放限制 · Audio Focus 强制执行 · 前台服务 WIU 能力
- **摘要**: Android 17 对后台音频播放实施严格管控，要求应用必须通过带 WIU 能力的前台服务才能在后台操作音频 API。未合规的音频播放静默失败，Audio Focus 请求返回 AUDIOFOCUS_REQUEST_FAILED。

### 关键发现
1. **后台音频 API 强制限制**: Android 17 对 AudioTrack/AudioRecord 播放、Audio Focus 请求、音量变更 API 全部增加后台执行限制。无合规前台服务时，播放静默失败，Audio Focus 返回 AUDIOFOCUS_REQUEST_FAILED
2. **WIU 前台服务机制**: 前台服务必须具备 "while-in-use" 能力（通过 MediaSessionEvent 启动或在 App 可见时启动）。SHORT_SERVICE 类型前台服务不具备 WIU 能力
3. **测试与调试**: Android 16+ 已可通过 `adb shell cmd audio set-enable-hardening` 启用测试。logcat 中 AudioHardening 前缀日志标识违规调用，`adb dumpsys audio` 可查详细状态
4. **对性能分析的影响**: 不合规后台播放可能导致 App 被冻结后意外恢复音频、音频卡顿（运行时限制波动）、泄漏的播放会话

### 可直接引用段落
> Starting in Android 17, the audio framework enforces stricter restrictions on background audio playback, audio focus requests, and volume change APIs. Attempts to call audio playback and volume change APIs when the app is not in a valid lifecycle will fail silently. Audio focus requests will return AUDIOFOCUS_REQUEST_FAILED. To control audio without a visible activity, developers should ensure their app has a foreground service (not of type SHORT_SERVICE) that was started with "while-in-use" (WIU) capabilities.

### 与 queue.json 联动
- 优先级调整建议: 无，维持 priority 80
- 素材路径建议: 可补充到 1.16 和 16.5 的 material_paths
