---
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
chapter: 8.8
confidence: medium
created_by: task2a-knowledge-gap
created_date: '2026-04-06'
drafted_by: openclaw-task2a
drafted_date: '2026-04-06'
gap_score: 16/20
gap_source: AOSP结构+官方文档+读者需求
last_task2b_at: 2026-06-06T02:57:42+08:00
last_task9_at: "2026-06-06T04:21:00+08:00"
last_verified: '2026-04-13'
last_verified_against: AOSP android-16.0.0_r1 + androidx/media release
pipeline_stage: "ready-to-publish"
related_chapters:
- '2.6'
- '2.13'
- '2.15'
- '2.16'
- '8.4'
- '14.9'
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-06"
section: '8.8'
sources:
- path: https://developer.android.com/reference/android/media/MediaCodec
  type: official
- path: https://developer.android.com/ndk/guides/audio/aaudio/low-latency-audio
  type: official
- path: https://developer.android.com/jetpack/androidx/releases/media3
  type: official
- path: https://android-developers.googleblog.com/ (Media3 1.10 Release)
  type: blog
- path: https://github.com/androidx/media/blob/release/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/DefaultLoadControl.java
  type: source
- path: frameworks/av/media/libstagefright/
  type: aosp
- path: frameworks/av/services/audioflinger/
  type: aosp
tags:
- MediaCodec
- Media3
- Surface
- AudioFlinger
- 视频性能
- 音频延迟
- ExoPlayer
task2b_result: fixed
task2b_state: fixed
task6_result: "pass-light-edit"
task6_reviewed_at: "2026-05-14T20:10:00+08:00"
task6_reviewed_by: openclaw-task6
task6_state: reviewed
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-06"
task9_state: reviewed
title: Android 多媒体管线性能
task9_review_notes: "2026-06-06 Task9 04 auto-fix: 修正 tunneled playback 核心 API/sideband 路径、移除 AudioPresentation/BUFFER_FLAG_TUNNEL/IHapticStream 误锚点，修正 AV1 dav1d 默认路径表述、Media3 日期和未证数值；回到 Task6 复审。"
last_task9_review_log: logs/deep-review/2026-06-06-04-deep-review.md
last_task6_at: "2026-06-06T05:12:48+08:00"
last_task6_review_log: "logs/review/2026-06-06-05-review.md"
task6_review_notes: "2026-06-06 Task6 revisiting-review #6: L1/L2 clean (禁用词0/高频词0-2功能性/元叙述0/物理动词0). L3/L4 pass (论据有验证标注/知识输出有深度/实战案例完整/工程师对话口吻). No B-class issues. task6=pass-light-edit + task9=auto-fixed + queue empty → promote finalized."
last_task2b_lite_at: 2026-06-05T13:35
last_task2b_by: openclaw-task2b-main
task2b_notes: "2026-06-06 Task2B main 回炉 #3：P0 Media3 ABR 源码方法修正（AdaptiveTrackSelection+DefaultBandwidthMeter 实际API），删除2026-05-12/21旧附录（含不可溯源伪代码和已被后文否定结论），清理CCodec::initialize伪代码和ABR错误调用链，P1 16KB页面声明降级为待验证。"
last_task9_autofix_at: 2026-06-06
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-23
last_task6_audit: "2026-07-14"
---
# 8.8 Android 多媒体管线性能

多媒体问题很少只属于某个线程。一次视频首帧要经过网络或文件读取、解复用、解密、解码、图形队列、合成和显示；一段音频还要经过应用缓冲、AudioFlinger 或 MMAP、HAL、DSP 与输出设备。任一阶段背压、排队或调度不及时，都可能表现为等待、掉帧、音画漂移、underrun 或功耗升高。

分析时先给现象分类。播放器显示 buffering，优先检查数据供应与 ABR；解码输出已经产生但画面晚到，继续看 Surface、fence 和合成；音频断续则从回调周期、mixer thread 与 HAL 路径追查。把所有卡顿都归到 `MediaCodec`，往往会在错误的层次花时间。

本章以 Android 17 / API 37 / `android-17.0.0_r1` 为平台源码锚点，Media3 以 2026-07-30 的稳定版 1.10.1 为库锚点。历史演进保留到 Android 8，所有固定参数都注明对应版本或改为设备测量值。
<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 视频播放管线的数据流、零拷贝路径与 `Surface` / `BufferQueue` 的角色
- 🔹 `MediaCodec` 的 Buffer 管理、同步 / 异步模式，以及音视频同步的基本思路
- 🔹 `MediaCodec` 与 `Surface`、Sync Fence、tunneled playback 的协同方式
- 🔹 Media3 / ExoPlayer 的 ABR、缓冲策略、动态调度与 Player 池化
- 🔹 AudioFlinger、AAudio、MMAP 与端到端音频延迟的构成
- 🔹 在 Perfetto 中抓取和分析 `MediaCodec` / `AudioFlinger` 性能问题的方法

### 扩展（可选深入）

- 🔸 HDR / Dolby Vision 带来的额外渲染开销
- 🔸 Camera → `MediaCodec` 编码管线的零拷贝与 GPU 处理权衡

<!-- outline-end -->
## 先建立端到端时间线

视频播放可以拆成以下阶段：

| 阶段 | 主要组件 | 典型等待 | 观测入口 |
| --- | --- | --- | --- |
| 数据到达 | Media3 `DataSource`、网络栈、文件系统 | DNS/TLS、吞吐波动、磁盘读取 | Media3 load 事件、网络日志、Perfetto I/O |
| 解复用与 DRM | Extractor、MediaDrm、Crypto | manifest、license、sample 解密 | Media3 analytics、DRM 回调、进程 slice |
| 解码输入 | MediaCodec input buffer | 上游没数据、buffer 所有权未归还 | callback/dequeue 时间、codec metrics |
| 解码执行 | Codec2/厂商 codec、VPU 或 CPU | codec 初始化、帧重排、资源竞争 | MediaCodec 回调、vendor trace、`dumpsys media.codec` |
| 图形排队 | Surface、BufferQueue、fence | consumer 慢、队列满、fence 未 signal | FrameTimeline、SurfaceFlinger、fence |
| 合成与显示 | SurfaceFlinger、HWC、显示驱动 | GPU/HWC 合成、vsync、present | Perfetto gfx、FrameTimeline、Winscope |

音频路径可按“应用生产数据 → AudioTrack/AAudio → AudioFlinger 或 MMAP → Audio HAL/DSP → 输出设备”分段分析。视频和音频在播放器的 media clock 处汇合；Bluetooth、USB、HDMI 和机身扬声器还会引入不同的设备侧缓冲。

这张时间线用于定位归属，不表示每个阶段都在独立进程中串行执行。解码、加载、合成和音频播放会并行推进，队列把它们隔开；队列过深会增加延迟，队列过浅又更容易因抖动而耗尽。

## 视频输出：Surface、BufferQueue 与 copy-avoiding 路径

### 从压缩 sample 到显示 layer

典型播放数据流如下：

`MediaExtractor / Media3 → MediaCodec input → decoder output Surface → BufferQueue 或 sideband → SurfaceFlinger / HWC → display`

配置 output `Surface` 后，应用仍负责把压缩 sample 交给 codec，也仍会收到 output index；区别是解码后的像素不会以普通 `ByteBuffer` 交给应用读取。应用调用 `releaseOutputBuffer()` 后，codec 把图形 buffer 提交给 Surface 对应的下游。

这条路径减少了应用侧 CPU 像素读回与再次上传，适合称为 copy-avoiding。平台仍可能因颜色格式、缩放、受保护内容、GPU 特效或厂商实现发生转换与复制，不能把“传入 Surface”写成端到端零拷贝保证。

`Surface` 表示 BufferQueue 的 producer 入口。consumer 由 Surface 的来源决定：

| 显示目标 | consumer 与后续路径 | 性能特征 | 适用场景 |
| --- | --- | --- | --- |
| `SurfaceView` | SurfaceFlinger layer 消费图形 buffer，再交 HWC 或 GPU 合成 | 视频 layer 与应用 UI layer 分开，具备 HWC overlay 机会 | 常规播放、HDR、TV、受保护内容 |
| `TextureView` | `SurfaceTexture` 消费 buffer，应用 UI 渲染再采样外部纹理 | 可做裁剪、旋转、alpha 与复杂动画，但增加应用 GPU 工作 | 必须把视频嵌入 View 变换的界面 |
| tunneled playback | codec 通过 sideband handle 把视频交给 HWC | framework 与应用减少逐帧参与，依赖设备能力 | 支持该能力的 TV、机顶盒和特定播放场景 |

`SurfaceView` 也不保证每帧都走 overlay。遮挡、透明度、缩放、色彩空间、受保护路径、显示能力和厂商 HWC 策略都可能让 layer 改走 GPU composition。`TextureView` 也不能仅凭类型判定某一帧的耗时，仍要观察 RenderThread、SurfaceFlinger 与 GPU/HWC 的当前决策。

### Buffer 所有权比“有几个 buffer”更有用

同步模式下，应用通过 `dequeueInputBuffer()` 取得 input index，填充 sample 后调用 `queueInputBuffer()` 归还；codec 用 `dequeueOutputBuffer()` 返回 output index，应用消费或安排渲染后再调用 `releaseOutputBuffer()`。等待时间由 dequeue 的 timeout 控制，不能笼统写成永久阻塞。

异步模式从 API 21 可用。`setCallback()` 必须在 `configure()` 前设置；指定 `Handler` 的重载从 API 23 可用。回调通知所有权变化，应用不再混用 dequeue API。下面的骨架把 callback 放到独立 Looper，避免默认落到主线程：

```kotlin
val codecThread = HandlerThread("VideoCodec").apply { start() }
val codecHandler = Handler(codecThread.looper)
val codec = MediaCodec.createDecoderByType(mimeType)

codec.setCallback(
    object : MediaCodec.Callback() {
        override fun onInputBufferAvailable(codec: MediaCodec, index: Int) {
            inputFeeder.onBufferAvailable(codec, index)
        }

        override fun onOutputBufferAvailable(
            codec: MediaCodec,
            index: Int,
            info: MediaCodec.BufferInfo,
        ) {
            frameScheduler.releaseWhenDue(codec, index, info.presentationTimeUs)
        }

        override fun onOutputFormatChanged(codec: MediaCodec, format: MediaFormat) {
            outputFormatObserver.onChanged(format)
        }

        override fun onError(codec: MediaCodec, error: MediaCodec.CodecException) {
            errorObserver.onCodecError(error)
        }
    },
    codecHandler,
)
codec.configure(format, outputSurface, null, 0)
codec.start()
```

`inputFeeder` 与 `frameScheduler` 是应用自己的非阻塞组件。低层播放器需要把 media PTS 映射到接近 `System.nanoTime()` 的呈现时刻，再使用 `releaseOutputBuffer(index, renderTimestampNs)`；直接把从零开始的 PTS 乘成纳秒会得到错误的系统时间。若不自行维护时钟，应让 Media3 处理调度。异步模式调用 `flush()` 后还要再次 `start()` 才会继续收到 input callback。

异步模式减少轮询和专用等待线程，不会让硬件解码本身加速。回调里做网络 I/O、等待锁、长时间持有 index 或串行处理大量工作，同样会让 codec 缺少可用 buffer。排查时记录“input index 可用 → sample 入队”和“output index 可用 → release”的间隔，比只看 callback 名称更有信息量。

### A/V sync 与视频呈现

每个压缩 sample 带 media presentation timestamp（PTS）。播放器还要维护播放速度、seek discontinuity、live offset 与系统单调时钟之间的映射。音频连续播放时常被选作 media clock，`AudioTrack.getTimestamp()` 或 renderer 的音频位置帮助估算当前媒体位置；视频 renderer 据此等待、按时 release 或丢弃已经过晚的帧。

低层实现不能只比较“视频 PTS 大于 AudioTimestamp 就 sleep”。还要处理音频未启动、timestamp 暂不可用、播放速度变化、seek 后时间线重置、输出设备切换和 codec reorder。Media3 的 audio/video renderer 与 `MediaClock` 已处理这些状态，应用更适合记录 drift、dropped frame 和 first-frame 事件。

## Fence 与图形队列背压

BufferQueue 依靠 acquire、release 与 present fence 协调生产者、consumer 和显示硬件：

| Fence | 谁等待 | 表达的条件 |
| --- | --- | --- |
| acquire fence | SurfaceFlinger/HWC 等 consumer | producer 对当前 buffer 的写入结束，可以读取 |
| release fence | 下一次要复用该 buffer 的 producer | consumer 已不再读取旧 buffer |
| present fence | 显示管线的观察者 | 当前合成已经呈现，或上一帧资源可以回收，具体语义由显示类型决定 |

Fence 允许设备在 GPU、VPU 和 HWC 之间异步排队，避免应用线程忙等。Fence 等待仍会贡献端到端延迟：decoder 迟交 acquire fence、HWC 迟交 release fence、显示 present 推迟，都可能让队列积压或 buffer 复用变慢。

一次“codec output 正常但屏幕掉帧”的排查顺序是：

1. 用播放器事件确认 sample 已到达、decoder 已初始化、output buffer 已返回。
2. 检查应用是否及时 release output，Surface 是否仍有效。
3. 在 FrameTimeline 中对齐 expected/actual present 与 jank 标记。
4. 看对应 layer 的 acquire/release/present fence，以及 SurfaceFlinger 的 composition decision。
5. 若 TextureView 路径还有 RenderThread/GPU 排队，再对比同一内容的 SurfaceView 基线。
6. 若厂商 codec 内部没有 trace，结合 output callback、`dumpsys media.codec` 与 vendor 日志缩小区间。

“SurfaceView 一定修复掉帧”也不成立。若根因是网络、decoder、DRM、显示刷新率切换或 HDR tone mapping，换 View 类型不会消除等待。

## Tunneled playback：硬件 A/V sync 与 sideband

Android 5 起为 on-demand 播放定义了 tunneled playback。应用创建 `SurfaceView`，让 `AudioTrack` 与 `MediaCodec` 使用同一个 audio session，并在 codec format 中设置 `MediaFormat.KEY_AUDIO_SESSION_ID`。支持 `FEATURE_TunneledPlayback` 的 decoder 会获得硬件 A/V sync ID，建立 sideband stream；SurfaceFlinger 把 sideband handle 传给 HWC，HWC 按音频时钟取得和呈现视频帧。

Android 11 起 Codec2 支持 tunneled playback，也为 Tuner live playback 定义了硬件同步 ID 路径。Android 17 源码中，Codec2 入口仍可在 [`CCodec::configureTunneledVideoPlayback()`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/codec2/sfplugin/CCodec.cpp) 找到。

启用前要同时满足 decoder、audio sink、SurfaceView、内容格式和设备产品配置。Media3 可以通过 `DefaultTrackSelector.Parameters.Builder.setTunnelingEnabled(true)` 表达偏好；不支持的组合会走普通播放路径。API 31 的 `PARAMETER_KEY_TUNNEL_PEEK` 控制暂停音频时首个 tunnel frame 是否提前显示，不能拿它当作启用 tunnel 的开关。

Tunneled playback 适合受控设备与长时间播放。复杂 UI 变换、截图、逐帧特效、某些字幕/overlay、录屏和设备兼容性都可能限制使用。验收必须覆盖 seek、暂停、变速、DRM、音轨切换与 Surface 重建，不能只测连续播放功耗。

## 低延迟解码

Android 11 / API 30 增加低延迟 decoder 能力。平台只在 codec 声明 `FEATURE_LowLatency` 时承诺识别该模式。下面的配置在 `configure()` 前查询能力并设置 format：

```kotlin
val capabilities = codecInfo.getCapabilitiesForType(mimeType)
if (capabilities.isFeatureSupported(
        MediaCodecInfo.CodecCapabilities.FEATURE_LowLatency
    )
) {
    format.setInteger(MediaFormat.KEY_LOW_LATENCY, 1)
}
```

启用后，decoder 应避免持有超出编码标准要求的 input/output 数据；运行中可用 `MediaCodec.PARAMETER_KEY_LOW_LATENCY` 切换。它不能删除 B-frame 重排、网络 jitter buffer、Surface 排队或显示 vsync，也不会保证某个固定首帧毫秒数。低延迟模式还可能减少 codec 的功耗优化空间，需要在目标 SoC 上同时测 latency、dropped frames 与能耗。

## HDR、Dolby Vision 与 Android 17 Eclipsa video

HDR 路径要同时检查内容、extractor、decoder profile、显示能力与合成路径。`Display.getHdrCapabilities()` 描述显示支持；`MediaCodecInfo.CodecCapabilities.profileLevels` 与 `isFormatSupported()` 用于检查 decoder；HDR10 静态元数据、HDR10+ 动态元数据及 Dolby Vision 数据还要沿 extractor、codec 与 surface 传递。

Tone mapping 可能发生在 HWC、SurfaceFlinger 的 RenderEngine、应用 shader 或厂商显示管线。HDR layer 与 SDR UI 混合时，系统还会处理 SDR white point 和 headroom。由此不能把 HDR 播放的额外开销固定归到 GPU。Perfetto 中应对比 layer composition、GPU/HWC 工作、显示模式切换与 frame timeline；画面错误则同时核对 metadata 和色彩空间。

Android 17 / API 37 引入 Eclipsa video 的平台级播放与采集支持，格式基于 SMPTE ST 2094-50 动态元数据。Media3 ExoPlayer 能解析并应用相应 metadata；Camera2 采集侧使用兼容的 dynamic range profile。性能测试仍要区分硬件加速映射与软件/GPU 路径，不能因为 API 可用就推断所有显示都具有相同开销。

## Media3 1.10.1：ABR、缓冲、调度与预加载

### 先固定库版本与线程模型

截至 2026-07-30，Media3 稳定版是 1.10.1。本章不把 1.11.0 的候选版行为写进稳定基线。播放器、renderer、track selector、load control 与 analytics 都可能在版本升级中改变默认值，性能报告应记录完整 artifact 版本。

`ExoPlayer` 的公开调用受 application Looper 约束。跨线程直接访问 player 会抛出 wrong-thread `IllegalStateException`。网络加载、codec callback 和渲染各有内部线程，应用侧 listener 也要避免在 application Looper 上执行长任务。

### ABR 决策要同时看带宽和 buffer

`DefaultBandwidthMeter` 产生带宽估计，`AdaptiveTrackSelection.updateSelectedTrack()` 结合估计带宽、播放速度、当前 buffer、live edge、可用轨道和已排队 chunk 选择格式。`DefaultTrackSelector` 还会应用分辨率、bitrate、MIME、显示大小、decoder 支持和应用 override。

Media3 1.10.1 的 `AdaptiveTrackSelection` 默认值如下：

| 常量 | 1.10.1 值 | 作用 |
| --- | --- | --- |
| `DEFAULT_BANDWIDTH_FRACTION` | 0.7 | 只把估算带宽的一部分用于选轨，给估算误差留余量 |
| `DEFAULT_MIN_DURATION_FOR_QUALITY_INCREASE_MS` | 10,000 | 升档通常要求的最小 buffer |
| `DEFAULT_MAX_DURATION_FOR_QUALITY_DECREASE_MS` | 25,000 | 降档判断使用的最大 buffer 阈值 |
| `DEFAULT_MIN_DURATION_TO_RETAIN_AFTER_DISCARD_MS` | 25,000 | 为加快升档而丢弃旧 chunk 时至少保留的时长 |

这些常量是算法 guard，不构成“10 秒升档、25 秒降档”的时间表。chunk 边界、live window、播放速度、当前格式、blacklist 与带宽估计都会改变决策。优化 ABR 时要同时记录 selected format、bitrate estimate、buffered duration、load time、rebuffer 和 dropped frames。

### LoadControl 还有字节阈值

Media3 1.10.1 的远程播放默认值为 `minBufferMs=50,000`、`maxBufferMs=50,000`、`bufferForPlaybackMs=1,000`、`bufferForPlaybackAfterRebufferMs=2,000`。`DEFAULT_PRIORITIZE_TIME_OVER_SIZE_THRESHOLDS=false`，player 还会依据 renderer 计算 target buffer bytes；达到字节目标后，实际 buffer 不一定增长到 50 秒。

短视频把 start threshold 调小，可能缩短点击到播放，也可能增加弱网下的二次 buffering。长视频把 buffer 调大，会增加内存、网络预取和用户未观看流量。调整时保持 CDN、segment duration、码率梯度和网络模型一致，分别报告首帧、rebuffer ratio、平均码率、峰值内存与流量浪费。

### 动态调度不能脱离版本讨论

1.10.1 的 `experimentalSetDynamicSchedulingEnabled(true)` 是实验性 opt-in，该版本默认关闭。它让 playback loop 尽量只在 renderer 可推进时唤醒，目标是减少无效轮询；自定义 `AudioSink` 还要提供可靠的 buffer duration 查询。实验 API 的默认值与名称可能在后续版本变化，升级后需重新查 API/source 并测 CPU wakeup、音频稳定性和播放状态切换。

### 预加载优先于无界 Player 池

Feed 场景需要缩短切换等待，可以用 `DefaultPreloadManager` 按当前 item 距离预取 source、选轨或加载指定时长。它把预加载量显式化，比同时 prepare 多个完整 Player 更容易控制网络、内存和 codec 资源。

MediaCodec 的 `getMaxSupportedInstances()` 只是并发上限提示，运行时可用实例还受分辨率、codec、secure session、其他应用与内存压力影响。Player 池若必须存在，应设置很小的上限，离屏 item 及时解绑 Surface，并记录 codec 创建失败与内存水位。维护多个 active decoder 只为“预热”会在低端设备上适得其反。

Media3 还提供实验性的 secondary `MediaCodecVideoRenderer` prewarming，当前 API 要求 Android 14 / API 34+，默认关闭。它减少连续 media item 的 renderer 切换等待，却会额外占用 codec 资源。应与普通 preload、单 Player 复用和小型 Player 池分别做 A/B，而后选择目标设备上稳定的一种。

### 用 Analytics 先划分网络、decoder 和 renderer

在抓系统 trace 前，播放器至少记录：

- prepare、play request、first sample 与 first rendered frame 的时刻；
- decoder name、hardware acceleration、初始化耗时与 codec error；
- selected track、bandwidth estimate、load duration 与 response bytes；
- playback state、rebuffer 次数和时长；
- dropped video frames、video size、audio underrun；
- Surface 创建、替换、销毁和 player release。

`AnalyticsListener`、`EventLogger` 与 `PlaybackStatsListener` 可以提供其中大部分事件；first sample 和 Surface 生命周期可用应用 trace 补齐。业务埋点要使用单调时钟，并给同一次播放分配 session ID，之后才能和 Perfetto 时间轴对齐。

## AudioFlinger、AAudio 与 MMAP

### 两条常见输出路径

Android 17 中，AudioFlinger 位于 `audioserver`，源码锚点是 [`frameworks/av/services/audioflinger/`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/)。应用的 `AudioTrack` 或 AAudio legacy path 把 PCM 交给 AudioFlinger thread，再经 Audio HAL、DSP 和驱动输出。

AudioFlinger 会根据设备、format、sample rate、channel mask、effect、flag 和共享状态选择 normal、fast、direct、offload 等路径。请求 `PERFORMANCE_MODE_LOW_LATENCY` 或 fast flag 只是意图；sample rate 转换、格式转换、音效链或资源冲突都可能让流改走别的 thread。用 `dumpsys media.audio_flinger` 检查 stream 与 thread 的当前归属。

### AAudio 与 MMAP 边界

AAudio 在 Android 8.0 / API 26 提供 native C 音频 API。Android 8.1 增加 MMAP/NOIRQ 低延迟路径：

| 模式 | 数据路径 | 特征 |
| --- | --- | --- |
| MMAP EXCLUSIVE | 应用与 ALSA driver 共享映射 buffer，绕过 AudioFlinger mixer | 延迟潜力最低，设备与资源条件严格 |
| MMAP SHARED | 映射 buffer 由 audioserver 中的 mixer 协调 | 支持共享，仍有 mixer 工作 |
| legacy | 经 AudioFlinger 常规队列 | 兼容面最广，可在 MMAP 不可用时回退 |

请求 `EXCLUSIVE` 后要读取打开结果，不能假定成功。设备可能只支持 SHARED，或完全回退 legacy。AOSP 提供 `AAudioStream_isMMapUsed()` 测试接口帮助 OEM/userdebug 验证路径；应用侧更常借助 Oboe、stream 属性和 AudioFlinger dump 判断。

### 低延迟回调的约束

Google 面向应用开发者推荐 Oboe：Android 8.1+ 走 AAudio，旧平台可回退 OpenSL ES。低延迟流请求 `PerformanceMode::LowLatency` 与 `SharingMode::Exclusive`，使用设备原生 sample rate 和合适的 frames-per-burst。

音频 data callback 中不要分配内存、读写文件、等待 mutex、调用可能阻塞的 binder API 或执行无界计算。控制线程通过无锁队列或固定大小 ring buffer 交换参数；回调只消费/生产当前 burst。输出 buffer 耗尽会产生 underrun，输入消费不及时会产生 overrun。

端到端音频延迟由这些项相加：

- 应用 ring buffer 与 callback 调度；
- AudioFlinger/mixer 或 MMAP queue；
- sample-rate conversion、effect 与 DSP 算法延迟；
- HAL、driver 与硬件 FIFO；
- speaker、USB、Bluetooth/LE Audio 等输出 transport。

任何统一的“Fast Mixer 为 2～4 ms”“端到端低于 10 ms”都会越过设备与测量口径。音乐与通话应用应使用 loopback 测 round-trip latency；播放器还要分别记录 output latency、underrun 和 A/V drift。

## Camera 到 encoder：避免应用 CPU 读回

Camera2/CameraX 录制可把 `MediaCodec.createInputSurface()` 返回的 Surface 作为 camera session target。相机 producer 把图形 buffer 交给 encoder consumer，应用不需要把 YUV 读入 CPU `ByteBuffer` 再写回 codec。这依然是 copy-avoiding 描述；ISP、颜色转换、缩放和厂商 buffer 管理可能包含内部复制。

若要做水印、滤镜或几何变换，常见路径变为：

`Camera Surface → GPU texture/effect pass → MediaCodec input Surface`

GPU pass 会增加命令、buffer 和 fence 依赖，增加多少延迟取决于 pipeline depth 与呈现策略，不能固定写成“一帧”。性能验收要同时测 camera timestamp、encoder input/output PTS、GPU duration、encode latency 与 dropped frame；多路相机、编码和解码还要考虑 codec 并发上限。

## Perfetto：从可用 trace 开始

### 抓取配置

Android 17 的 `atrace.cpp` 仍定义 `audio`、`video`、`camera`、`gfx` 与 `view` 分类，但厂商 codec 不一定暴露相同 slice。抓取前先列出目标设备支持的 category，再用 Perfetto 官方脚本同时记录调度和应用 trace。

这组命令用于采集 20 秒媒体 trace：

```bash
adb shell atrace --list_categories

python3 record_android_trace \
  -o media.perfetto-trace \
  -t 20s \
  -b 64mb \
  -a com.example.player \
  sched freq idle gfx view audio video camera
```

`sched/freq/idle` 解释线程为什么没及时运行，`gfx/view` 覆盖应用与 SurfaceFlinger 图形事件，`audio/video/camera` 打开平台媒体标记，`-a` 打开目标应用的 `android.os.Trace` 事件。目标设备没有某个 category 时删掉它，不要虚构 `media` 或 `codec` 分类。

trace 前后再保存服务状态。这组命令用于确认 codec、AudioFlinger 和 layer 配置：

```bash
adb shell dumpsys media.codec > media-codec.txt
adb shell dumpsys media.audio_flinger > audio-flinger.txt
adb shell dumpsys SurfaceFlinger > surface-flinger.txt
```

dump 内容会包含设备和厂商信息，分享前要做隐私检查。`dumpsys` 是状态快照，Perfetto 是时间线；两者要对应同一次复现。

### SQL 先枚举 slice，再写设备专用查询

旧式查询经常假定 slice 名一定包含 `MediaCodec::queueInputBuffer`，还假定 `arg_set_id` 里存在 `buffer_id`、`size`。平台 tag、Media3 版本和厂商 instrumentation 都会改变名称与参数。Perfetto 当前推荐先引入 `slices.with_context`，枚举本次 trace 中可见的媒体 slice：

```sql
INCLUDE PERFETTO MODULE slices.with_context;

SELECT
  process_name,
  thread_name,
  name,
  COUNT(*) AS occurrences,
  ROUND(AVG(dur) / 1e6, 3) AS avg_ms,
  ROUND(MAX(dur) / 1e6, 3) AS max_ms
FROM thread_or_process_slice
WHERE
  name GLOB '*Codec*'
  OR name GLOB '*Audio*'
  OR name GLOB '*Buffer*'
  OR name GLOB '*Frame*'
GROUP BY process_name, thread_name, name
ORDER BY max_ms DESC;
```

结果用于发现名称和线程，不能直接把包含 `decode` 的 slice 当作单帧硬件解码耗时。找到目标 slice 后，再检查其嵌套关系、`args` 表与相邻 sched/thread_state；只有本次 trace 确认存在参数时才使用 `EXTRACT_ARG()`。

### 读 trace 的顺序

1. 在时间轴标出 play request、buffering、first frame、seek、underrun 等应用事件。
2. 对齐网络 load、extract/DRM、codec init 与 output callback，判断数据是否及时到 decoder。
3. 对齐 output release、BufferQueue、fence、FrameTimeline 与 SurfaceFlinger composition。
4. 检查相关线程的 running/runnable/sleeping 状态、唤醒者、CPU 频率与 thermal counter。
5. 音频问题再看 AudioFlinger thread、callback 周期、underrun 与输出设备切换。
6. 只有在区间已经收窄后，才用 vendor codec/HAL trace 或 userdebug 日志继续深入。

视频内容帧率可能是 24/30 fps，显示刷新率可能是 60/120 Hz。不能用“每个 vsync 都必须有新视频帧”的规则判断掉帧；应以 PTS、播放器 dropped-frame 事件和目标 cadence 为准。

## 症状到证据的映射

| 症状 | 先确认 | 常见归属 | 不应直接下的结论 |
| --- | --- | --- | --- |
| 首帧慢 | manifest/DRM、first sample、codec init、first output、first present | 网络、DRM、decoder 初始化、Surface 未就绪 | “MediaCodec 创建一定是主因” |
| 播放中 buffering | load duration、带宽估计、buffered duration、selected bitrate | CDN、弱网、ABR、LoadControl | “视频 decoder 掉帧” |
| decoder 有 output 但画面晚 | output release、Surface 生命周期、fence、FrameTimeline | 应用调度、BufferQueue、GPU/HWC、显示 | “硬解太慢” |
| dropped frames 增多 | late frame、CPU/GPU、composition、刷新率 | renderer、调度、GPU/HWC、热限制 | “降低码率就会修复” |
| A/V drift | audio clock、PTS discontinuity、seek、输出路由 | timestamp 映射、renderer、设备切换 | “AudioTimestamp 不准” |
| 音频 underrun | callback 周期、thread_state、mixer thread、buffer size | 回调阻塞、调度、buffer、HAL | “GC 是唯一原因” |
| 功耗偏高 | codec name、hardware acceleration、GPU composition、wakeups | 软解、TextureView/特效、轮询、transport | “tunneling 在所有手机都省电” |

## 并发与资源限制

`MediaCodecInfo.CodecCapabilities.getMaxSupportedInstances()` 返回的是上限提示。当前能创建多少实例还取决于 MIME/profile、分辨率、帧率、secure/non-secure、encoder/decoder 组合、内存和其他进程。应用必须处理 `CodecException` 与资源回收，不能用一个固定 Player 池大小覆盖所有设备。

遇到创建慢或失败时：

- 记录 codec name、API 29+ 的 `isHardwareAccelerated()`、profile/level 与 format；
- 对比单实例和并发实例基线；
- 检查离屏 Player 是否仍持有 Surface、decoder 或 DRM session；
- 观察 `dumpsys media.codec`、内存水位和系统中其他媒体会话；
- 降低预加载阶段，优先只准备 source/track，避免提前占用 decoder。

## 版本边界

| 版本 | 与本章相关的变化 |
| --- | --- |
| Android 8.0 / API 26 | AAudio native API |
| Android 8.1 / API 27 | AAudio MMAP/NOIRQ 低延迟路径 |
| Android 10 / API 29 | updatable Media/Media Codec 模块与 Codec2 迁移阶段 |
| Android 11 / API 30 | `KEY_LOW_LATENCY` / `FEATURE_LowLatency`；Codec2 tunneled playback 支持 |
| Android 15 / API 35 | dav1d AV1 software decoder 可按名称 opt-in，并可通过 Mainline 回溯到部分 Android 11+ 设备 |
| Android 17 / API 37 | Eclipsa video 平台级播放与采集支持 |
| Media3 1.10.1 | 本章 ABR、LoadControl、动态调度与预加载的稳定库锚点 |

平台版本不能推导 codec 是否硬件加速、MMAP 是否可用、tunneling 是否稳定或 HDR 是否由 HWC 处理。能力查询、目标设备复现和端到端测量仍是验收依据。

## Android 17 源码锚点

- [`frameworks/av android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/)：MediaCodec、Codec2、AudioFlinger 与 AAudio 主仓。
- [`MediaCodec.cpp`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/libstagefright/MediaCodec.cpp)：framework native codec 状态机与组件桥接。
- [`CCodec.cpp`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/codec2/sfplugin/CCodec.cpp)：Codec2 framework adapter、Surface 与 tunneled 配置。
- [`AudioFlinger`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/)：mixer、track、thread 与输出管理。
- [`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp) 与 [`BufferQueueConsumer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp)：图形 buffer 所有权与 fence 流转。
- [`atrace.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/cmds/atrace/atrace.cpp)：Android 17 可用的系统 atrace category 定义。

本章没有依赖某个 Linux scheduler 或驱动实现的固定时延结论。涉及 fence driver、DMA-BUF、音频 ALSA 或 codec driver 的设备定向分析时，内核源码统一以 `android17-6.18-2026-06_r6` 为锚点。

## 参考资料

### Android 与 AOSP 官方文档

- [MediaCodec API](https://developer.android.com/reference/android/media/MediaCodec)
- [MediaCodec low-latency decoding](https://source.android.com/docs/core/media/low-latency-media)
- [Multimedia tunneling](https://source.android.com/docs/devices/tv/multimedia-tunneling)
- [Updatable media modules](https://source.android.com/docs/core/media/media-modules)
- [BufferQueue and Gralloc](https://source.android.com/docs/core/graphics/arch-bq-gralloc)
- [Synchronization framework](https://source.android.com/docs/core/graphics/sync)
- [HDR video playback](https://source.android.com/docs/core/display/hdr)
- [Eclipsa video on Android 17](https://developer.android.com/media/platform/integrate-eclipsa-video)
- [Android 15 dav1d AV1 decoder](https://developer.android.com/about/versions/15/features)
- [AAudio and MMAP](https://source.android.com/docs/core/audio/aaudio)
- [Audio latency for app developers](https://source.android.com/docs/core/audio/latency/app)
- [Audio debugging](https://source.android.com/docs/core/audio/debugging)

### Media3 1.10.1

- [Media3 release notes](https://developer.android.com/jetpack/androidx/releases/media3)
- [AdaptiveTrackSelection API](https://developer.android.com/reference/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection)
- [DefaultLoadControl API](https://developer.android.com/reference/androidx/media3/exoplayer/DefaultLoadControl)
- [DefaultPreloadManager guide](https://developer.android.com/media/media3/exoplayer/preloading-media/preloadmanager)
- [AdaptiveTrackSelection 1.10.1 source](https://github.com/androidx/media/blob/1.10.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection.java)
- [DefaultLoadControl 1.10.1 source](https://github.com/androidx/media/blob/1.10.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/DefaultLoadControl.java)
- [ExoPlayer 1.10.1 source](https://github.com/androidx/media/blob/1.10.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/ExoPlayer.java)
- [DefaultRenderersFactory 1.10.1 source](https://github.com/androidx/media/blob/1.10.1/libraries/exoplayer/src/main/java/androidx/media3/exoplayer/DefaultRenderersFactory.java)

### Perfetto

- [Record Android system traces](https://perfetto.dev/docs/getting-started/system-tracing)
- [ATrace data source](https://perfetto.dev/docs/data-sources/atrace)
- [PerfettoSQL with context](https://perfetto.dev/docs/analysis/perfetto-sql-getting-started)

### 交叉章节

- [GraphicBuffer 与 BufferQueue 内存复用](../../part1-fundamentals/ch02-rendering/32-graphic-buffer-memory-pool.md)
- [SurfaceView 与 TextureView 选型](../../part5-app/ch22-rendering-practice/42-surfaceview-textureview-rendering-performance.md)
- [Media3 视频播放管线实战](../../part5-app/ch22-rendering-practice/43-media3-video-rendering-pipeline-performance.md)
