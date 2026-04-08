## [研究] Android 音频管线架构：AudioFlinger FAST Mixer 与 AAudio MMAP 低延迟路径
- **来源**: https://source.android.com/docs/core/audio/latency + https://source.android.com/docs/core/audio/architecture + https://developer.android.com/ndk/guides/audio
- **作者/机构**: Google AOSP / Android Developer Documentation
- **日期**: 2026-04-08
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 3/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**: 1.16 Audio Pipeline 延迟与性能
- **映射锚点**: AudioFlinger 架构 · FAST Mixer 低延迟路径 · AAudio MMAP 直接写入 · 延迟分层分析
- **摘要**: Android 音频管线以 AudioFlinger 为核心，FAST Mixer（Android 4.1+）为低延迟应用提供快速混音路径，AAudio MMAP（Android 8.1+）通过内存映射直接与 ALSA 驱动共享缓冲区，EXCLUSIVE 模式下完全绕过 AudioServer 混音器。

### 关键发现
1. **AudioFlinger 三层架构**: Normal Mixer（默认路径，高延迟）-> FAST Mixer（低延迟路径，Android 4.1+）-> MMAP Direct Path（最低延迟，Android 8.1+，需 HAL 支持）
2. **FAST Mixer 设计**: 专用线程，最小化与外部组件交互。仅服务于使用 Java AudioTrack 或 AAudio 且配置 LOW_LATENCY 的应用。目标是减少到几十毫秒延迟
3. **AAudio MMAP 双模式**: SHARED 模式通过 AudioServer 内部混音器使用 MMAP 缓冲区；EXCLUSIVE 模式完全绕过 AudioServer 混音器，应用直接写入与 ALSA 驱动共享的内存映射缓冲区
4. **Perfetto 音频追踪**: `adb shell perfetto -t 10s --atrace-categories audio,sched,freq,idle --buffer 64mb`；SQL 查询 slice 表过滤 AudioFlinger/FastMixer 关键词；分析线程调度确认音频线程获得足够 CPU 时间
5. **延迟量化**: 2017 年 Android 平均往返延迟 109ms -> 2021 年降至 40ms 以下。Pixel 3a (2019) 首次达到 10ms。专业音频应用目标为 10ms 往返延迟，20ms 为当前及格线

### 可直接引用段落
> AAudio MMAP mode, introduced in Android 8.1, allows native applications to achieve even lower latency by sharing memory-mapped buffers directly between the application and the ALSA device mixer or driver, bypassing various levels of internal processing. In EXCLUSIVE mode, this bypasses the AudioServer mixer entirely, providing significantly lower latency. The effectiveness heavily relies on hardware manufacturers implementing these features, which is not universally done.

### 与 queue.json 联动
- 优先级调整建议: 无，维持 priority 80
- 素材路径建议: 可补充到 1.16 的 material_paths，作为核心架构参考
