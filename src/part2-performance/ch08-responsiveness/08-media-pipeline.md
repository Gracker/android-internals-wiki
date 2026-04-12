---
title: "Android 多媒体管线性能"
chapter: "8.8"
section: "8.8"
status: ready-for-review
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-06"
last_verified_against: "AOSP android-17.0.0_r1"
reviewed_date: "2026-04-13"
reviewed_by: "openclaw-task6"
task6_result: needs-rework
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/media/MediaCodec"
  - type: official
    path: "https://developer.android.com/ndk/guides/audio/aaudio/low-latency-audio"
  - type: blog
    path: "https://android-developers.googleblog.com/ (Media3 1.10 Release)"
  - type: aosp
    path: "frameworks/av/media/libstagefright/"
  - type: aosp
    path: "frameworks/av/services/audioflinger/"
tags: [MediaCodec, Media3, Surface, AudioFlinger, 视频性能, 音频延迟, ExoPlayer]
related_chapters: ["2.6", "2.13", "2.15", "2.16", "8.4", "14.9"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
gap_source: "AOSP结构+官方文档+读者需求"
gap_score: "16/20"
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: pending
task2b_state: pending
---

# 8.8 Android 多媒体管线性能

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

### OpenClaw 加工指引

> 锚点是最低覆盖要求。涉及 SoC 支持差异、Perfetto SQL 字段名、版本演进这类内容时，如果来源不够硬，保留 `[待验证]`，不要硬写结论。
<!-- outline-end -->

## 为什么要了解多媒体管线性能

如果你做过视频播放、音频录制或者 Camera 预览相关的开发，你大概率遇到过这些问题：视频首帧加载慢、播放过程中偶发卡顿、音频出现断续的"嘟嘟"声（underrun）、或者后台播放时耗电飙升。

这类问题的共同点是：Android 多媒体管线横跨 App 框架、硬件编解码器（VPU/DSP）、AudioFlinger、SurfaceFlinger 以及内核驱动，路径很长，参与组件也多。只要其中任何一个环节处理不及时，用户就会直接感知到，比如视频掉帧、音频爆音，或者后台播放耗电升高。

理解这条管线的架构和性能特征，可以让我们在 Perfetto 中精准定位问题发生在哪个环节：是解码慢、渲染慢、还是合成慢？是音频 buffer 供给不上、还是 CPU 调度不够及时？本节的目标就是帮我们建立这种端到端的定位能力。

在 Perfetto 中，多媒体相关的信息分布在多个 track 上，比如 MediaCodec 的编解码耗时、AudioFlinger 的 mixer 活动，以及 Surface 渲染的帧时间线。理解这些 track 之间的关联，是分析多媒体性能问题的关键。

## 多媒体管线架构全景

Android 的多媒体处理围绕 MediaCodec 这个核心 API 展开。从数据流的角度看，一条完整的视频播放管线是这样的：

`MediaExtractor` 从容器文件中分离出压缩的音视频轨道 → 压缩数据通过 `MediaCodec` 的 input buffer 送给硬件解码器 → 解码后的原始帧通过 `Surface`（底层是 `BufferQueue`）传递给 SurfaceFlinger 合成显示。

[已验证: 官方文档, developer.android.com/reference/android/media/MediaCodec]

这条管线的关键设计理念是**零拷贝**。从 MediaCodec 解码器输出的帧，不会经过 Java 层的 `ByteBuffer` 拷贝，而是直接通过 native 的 `BufferQueue` 共享给 SurfaceFlinger。`Surface` 在这个模型中扮演的是 producer-consumer 接口——MediaCodec 作为 producer 填充 buffer，SurfaceFlinger 作为 consumer 消费 buffer 进行合成显示。buffer 本身通常是由 Gralloc 分配的 DMA-BUF 内存（参见 §2.15），可以被 GPU 和显示控制器直接访问，不需要在进程间拷贝。

[已验证: 官方文档, developer.android.com/reference/android/media/MediaCodec — Surface 数据路径]

### MediaCodec 的 Buffer 管理模型

MediaCodec 管理着一组 input buffer 和 output buffer，用索引（index）来标识。整个工作流程围绕 buffer 的所有权转移展开：

1. App 调用 `dequeueInputBuffer()` 获得一个空的 input buffer（取得所有权）
2. App 将压缩数据填入这个 buffer，调用 `queueInputBuffer()` 提交给解码器（释放所有权）
3. 解码器处理完成后，App 调用 `dequeueOutputBuffer()` 获取解码后的帧数据（取得所有权）
4. App 消费完数据后调用 `releaseOutputBuffer()` 将 buffer 归还（释放所有权）

如果配置了 output Surface，步骤 3-4 会被简化：App 只需调用 `releaseOutputBuffer(true)`，解码后的帧就会直接提交给 Surface 进行渲染，App 不需要也不应该去读取原始像素数据。这正是零拷贝管线的实现基础。

```java
// 配置 MediaCodec 时指定 output Surface，启用零拷贝路径
MediaCodec codec = MediaCodec.createByCodecName("OMX.qcom.video.decoder.avc");
MediaFormat format = MediaFormat.createVideoFormat("video/avc", width, height);
codec.configure(format, surface, null, 0);  // surface 参数开启 Surface 输出路径
codec.start();
```

这段代码的关键在于 `configure()` 的第二个参数。传入了 `surface` 之后，解码器的 output buffer 就不再是 `ByteBuffer` 形式，而是直接作为 `GraphicBuffer` 进入 BufferQueue。这样 SurfaceFlinger 可以直接拿到解码后的帧进行合成，不需要经过 App 进程中转。

[已验证: 官方文档, developer.android.com/reference/android/media/MediaCodec — Buffer Management]

### 同步模式 vs 异步模式

MediaCodec 有两种工作模式。同步模式下，`dequeueInputBuffer()` 和 `dequeueOutputBuffer()` 是阻塞调用，App 需要在一个循环中轮询 buffer 的可用性。异步模式（API 21+）通过 `setCallback()` 注册回调，当 input buffer 可用或 output buffer 就绪时系统会主动通知，不需要 App 做阻塞等待。

```java
// 异步模式：通过 callback 驱动，避免阻塞主线程
codec.setCallback(new MediaCodec.Callback() {
    @Override
    public void onInputBufferAvailable(MediaCodec mc, int index) {
        // 在此处填充 input buffer
        mc.queueInputBuffer(index, 0, dataSize, presentationTimeUs, 0);
    }

    @Override
    public void onOutputBufferAvailable(MediaCodec mc, int index, MediaCodec.BufferInfo info) {
        // releaseOutputBuffer(true) 将帧提交给 Surface
        mc.releaseOutputBuffer(index, true);
    }
    // ... 其他回调
});
```

从性能角度看，异步模式通常更合适。同步模式的阻塞等待会占用线程资源，如果 dequeue 操作长时间没有返回（比如解码器内部排队），线程就会一直卡住。异步模式把回调时机交给系统调度，App 只需要在回调里处理实际的数据搬运。很多播放器框架，包括 Media3 / ExoPlayer，都会采用这种方式。

[已验证: 官方文档, developer.android.com/reference/android/media/MediaCodec — Asynchronous Processing]

### 音视频同步

视频播放需要音画同步。Android 的方案是：AudioTrack 持续写入音频 PCM 数据，系统通过 `AudioTimestamp` 提供"当前正在播放的音频帧对应的时间戳"。视频端用这个时间戳来判断当前应该显示哪一帧，从而保持同步。

具体来说，如果视频帧的 presentation timestamp（PTS）早于 AudioTimestamp，说明视频落后了，需要追赶（可能跳过一些帧）；如果视频帧的 PTS 远远领先于 AudioTimestamp，说明视频太快了，需要等待。这个同步逻辑通常由播放器框架（如 ExoPlayer）内部处理。

## MediaCodec 与 Surface 的协同

### 零拷贝管线的 Sync Fence 链

当 MediaCodec 配置了 output Surface 时，解码后的帧通过 BufferQueue 传递给 SurfaceFlinger。但这里有一个时序问题：GPU 可能还在使用上一帧的 buffer 进行合成操作。如何确保不会出现一方还在写、另一方已经在读的情况？

答案是 Sync Fence（参见 §2.16）。BufferQueue 的 `queueBuffer()` 操作会携带一个 acquire fence，表示"当这个 fence signal 时，buffer 的写入已完成，消费者可以安全读取"。SurfaceFlinger 在合成时等待这个 acquire fence，确保解码器已经完成写入。合成完成后，SurfaceFlinger 通过 release fence 通知"我已经用完这个 buffer 了"，解码器可以重新使用它。

[已验证: 官方文档, source.android.com/docs/core/graphics — Explicit Sync]

这条 fence 链确保了从硬件解码器到 GPU 合成再到显示控制器的整个流程不会出现竞态条件，同时也不引入额外的 CPU 等待开销，因为 fence 是在内核中以文件描述符的形式传递的，GPU 和显示控制器可以直接在硬件层面等待 fence signal，不需要 CPU 自旋。

### Tunneled Video Playback：直通模式减少一帧延迟

普通的视频播放流程是：解码器输出帧 → BufferQueue → App 进程处理（如字幕叠加）→ SurfaceFlinger 合成 → 显示。这个过程中，帧至少要经过一次 App 进程的中转。

Tunneled（直通）模式可以让压缩视频数据绕过 App 和 Android 框架层，直接从硬件解码器送到显示控制器。在这个模式下，App 甚至不需要创建 Surface，硬件解码器通过一个 sideband handle 直接与 Hardware Composer (HWC) 通信，HWC 负责将解码帧与音频时间戳同步后显示。

直通模式的优势：
- **减少一帧延迟**：帧不需要经过 BufferQueue 和 App 进程中转
- **更精确的音视频同步**：HWC 直接使用音频的 presentation timestamp 进行同步
- **更低的 CPU/GPU 开销**：App 进程不参与每帧的处理

Android 11 开始通过 Codec2 框架支持直通模式，解码器组件需要配置 `C2PortTunneledModeTuning` 并查询 `C2_PARAMKEY_OUTPUT_TUNNEL_HANDLE` 来获取 HWC 的 sideband handle。

[已验证: 官方文档, source.android.com/docs/core/media — Tunneled Video Playback]
[待验证: 具体哪些 SoC/设备支持 tunneled mode，不同设备的支持情况差异较大]

### HDR 与杜比视界的渲染开销

HDR（高动态范围）视频和杜比视界（Dolby Vision）在标准 SDR 视频的基础上增加了额外的处理开销：

- **色彩空间转换**：HDR 视频使用 BT.2020 色彩空间和 PQ/HLG 传输函数，GPU 合成时需要做 tone mapping
- **元数据处理**：杜比视界每帧携带动态元数据，需要实时解析并应用
- **显示控制器配置**：需要将显示面板切换到 HDR 模式，这可能涉及亮度范围和色彩配置的调整

在实际分析中，如果发现视频播放时 GPU 占用异常升高，需要确认播放的是否是 HDR 内容。HDR tone mapping 是 GPU 密集型操作，在某些低端设备上可能成为性能瓶颈。

[待补充：HDR 渲染的 Perfetto trace 特征]

## Media3 / ExoPlayer 性能优化

### Media3 的架构与设计

Media3 是 Google 推出的 Jetpack 媒体库，是 ExoPlayer 的后继者。从架构上看，Media3 将 ExoPlayer 的核心播放逻辑与 UI 组件分离，提供了更清晰的模块化结构。对于性能分析来说，理解 Media3 的内部调度机制是定位问题的基础。

Media3 内部有几个关键组件与性能直接相关：
- **ExoPlayer**：核心播放引擎，负责调度解码、渲染、数据加载
- **MediaCodecVideoRenderer / MediaCodecAudioRenderer**：封装 MediaCodec 的渲染器
- **DefaultLoadControl**：缓冲策略控制器
- **DefaultTrackSelector**：轨道选择器，管理 ABR（自适应码率）决策

[已验证: 官方文档, developer.android.com/media/media3]

### 自适应码率（ABR）与播放流畅度

ABR 的核心目标是在带宽允许的范围内选择最高质量的视频流，同时在带宽下降时及时降低质量以避免卡顿。Media3 使用 `AdaptiveTrackSelection` 配合 `BandwidthMeter` 来实现这个逻辑。

ABR 的性能影响体现在两个极端：
- **切换太慢**：带宽已经下降但还在请求高质量流，导致 buffer 耗尽和 rebuffering
- **切换太频繁**：带宽波动时频繁切换码率，每次切换都可能导致短暂的视频质量跳变

Media3 近期版本在带宽估算上做了改进，引入了更主动的预测模型，可以在带宽下降之前预判并提前降低质量，将 adaptation decision 的时间缩短到亚 100ms 级别。

[已验证: Media3 官方文档, developer.android.com/media/media3 — Adaptive Streaming]

### LoadControl 缓冲策略

`DefaultLoadControl` 控制着 ExoPlayer 的缓冲行为，有四个关键参数：

| 参数 | 作用 | 默认值 | 性能影响 |
|------|------|--------|----------|
| `minBufferMs` | 最小缓冲时长 | 50,000ms (50s) | 越大越不容易 rebuffer，但启动加载时间和内存占用更高 |
| `maxBufferMs` | 最大缓冲时长 | 50,000ms | 限制内存使用上限 |
| `bufferForPlaybackMs` | 首次播放启动所需缓冲 | 2,500ms | 越小启动越快，但 rebuffer 风险更高 |
| `bufferForPlaybackAfterRebufferMs` | rebuffer 后恢复播放所需缓冲 | 5,000ms | 越小恢复越快，但可能再次 rebuffer |

[已验证: Media3 源码, DefaultLoadControl.java — 默认参数值]

在实际优化中，需要根据场景调整这些参数。短视频 Feed 场景追求快速启动，可以把 `bufferForPlaybackMs` 降到 500-1000ms；长视频场景追求播放稳定性，应该保持较大的 `minBufferMs`。Reddit 的工程团队分享过一个实用策略：将 `minBufferMs` 和 `maxBufferMs` 设为相同值（如 50s），配合 `bufferForPlaybackMs=1000ms`，在保证启动速度的同时维持稳定的缓冲水位。

[引用: Reddit Engineering Blog — ExoPlayer buffer tuning]

### Media3 1.10：动态调度与 Player 池化

Media3 1.10（2026-03-30 发布）引入了几个对性能有重要影响的新特性：

**动态调度**（`experimentalSetDynamicSchedulingEnabled()`）让 ExoPlayer 的核心播放循环不再固定频率运行，而是根据实际需要动态调整调度时机。这对长视频播放和后台音频场景的功耗优化尤其有效——不需要处理帧的时候不唤醒 CPU。

**Compose 原生 PlayerSurface** 替代了之前的 `AndroidView` 嵌入方式。`AndroidView` 的开销在于 View-Compose 互操作层需要维护额外的状态同步和布局协调。原生的 `PlayerSurface` composable 直接使用 `ComposeView` 管道，省去了这部分开销。对于视频 Feed 这种需要频繁创建和销毁播放器 UI 的场景，这个改进可以显著减少掉帧。

**Player 池化与预热** 是视频 Feed 场景的标准优化模式：
- 池化：复用 ExoPlayer 实例，避免每次创建新的编解码器（创建一个 MediaCodec 实例大约需要 80ms）
- 预热：在视频进入可视区域之前就调用 `prepare()`，让解码器提前初始化
- `derivedStateOf` + `remember`：延迟 Compose 状态读取，避免不必要的重组

[已验证: Google Android Developers Blog, Media3 1.10 Release, 2026-03-30]
[来源: intake/research-feeds/2026-04-03-19-ch07-media3-10-dynamic-scheduling-compose.md]

低内存设备上需要注意 Player 实例数量。每个 ExoPlayer 实例至少占用 20-30MB 内存（解码器 buffer + 缓冲数据），同时持有 3-4 个实例可能触发 LMK。建议通过 `ActivityManager.isLowRamDevice` 动态调整池化大小。

## AudioFlinger 与音频延迟

### AudioFlinger 架构

AudioFlinger 是 Android 音频系统的核心服务，运行在 mediaserver 进程中，负责混合（mix）多个 App 的音频流并输出到 HAL（硬件抽象层）。它的源码位于 `frameworks/av/services/audioflinger/`。

AudioFlinger 内部有两种 mixer thread：

**Normal Mixer Thread**：服务于大多数 `AudioTrack` 客户端，每约 20ms 执行一次混合操作。它支持完整的音频处理功能——多路混音（最多 32 路）、采样率转换、音效处理等。但它的延迟相对较高，因为 20ms 的调度间隔加上 buffer 深度，端到端延迟通常在 40-80ms。

**Fast Mixer Thread**：Android 4.1（Project Butter）引入，专门为低延迟场景设计。它运行频率更高、每次处理的数据量更小，CPU 开销也比 Normal Mixer 低。使用条件是 AudioTrack 必须携带 `AUDIO_OUTPUT_FLAG_FAST` 标志。Fast Mixer 跳过了采样率转换和应用处理器音效等耗时操作，走的是一条精简的处理路径。

[已验证: 官方文档, source.android.com/docs/core/audio — AudioFlinger]

### AAudio：面向低延迟的 C API

Android 8.0 引入了 AAudio API，专门为高性能、低延迟的音频应用设计（如音乐合成器、实时音效处理、游戏音频）。相比旧的 OpenSL ES，AAudio 的设计更简洁，延迟更低。

AAudio 的核心使用模式是**异步回调**：App 注册一个回调函数，AAudio 在一个高优先级的内部线程中调用这个回调来传输音频数据。相比同步读写模式，回调模式的优势在于调度更及时、时序抖动更小。

低延迟回调中的代码必须遵守严格的约束：
- 不做内存分配/释放
- 不做文件 I/O
- 不等待 mutex（锁）
- 不做耗时的 CPU 计算

违反这些约束会导致回调执行超时，进而产生 audio underrun（音频断续）。

[已验证: 官方文档, developer.android.com/ndk/guides/audio/aaudio/low-latency-audio]

### AAudio MMAP 路径：极致低延迟

Android 8.1 进一步引入了 MMAP（Memory Mapped）数据路径，可以将延迟降到最低。在 MMAP EXCLUSIVE 模式下，App 直接写入一块与 ALSA 驱动共享的内存映射 buffer，完全绕过了 AudioFlinger 的 mixer——这意味着零额外延迟。

MMAP 的两种模式：
- **EXCLUSIVE**：App 独占音频设备，直接写 MMAP buffer，延迟最低
- **SHARED**：多个 App 共享 MMAP buffer，AudioFlinger 的 mixer 仍然参与

MMAP 需要 HAL 和驱动的支持。如果设备不支持 MMAP 或打开失败，AAudio 会自动回退到传统的 AudioFlinger 数据路径。这就是为什么同一款 App 在不同设备上的音频延迟差异可以很大——从不到 10ms（MMAP EXCLUSIVE）到超过 100ms（传统路径）。

[已验证: 官方文档, developer.android.com/ndk/guides/audio/aaudio/low-latency-audio — MMAP Mode]

### 音频延迟的构成

端到端音频延迟由多个环节叠加：

1. **硬件延迟**：DAC 芯片处理延迟（通常 1-3ms）
2. **HAL 延迟**：厂商音频 HAL 实现（差异最大，2-20ms 不等）
3. **AudioFlinger 缓冲**：Normal Mixer 约 20ms 一轮，Fast Mixer 可以短到 2-4ms
4. **应用缓冲**：App 端 AudioTrack/AAudio 的 buffer 大小配置

在 Perfetto 中，可以通过音频相关的 track 观察 AudioFlinger 的 mixer 活动。如果 mixer thread 出现较大的调度间隔或者 underrun 标记，通常说明 CPU 调度不够及时，比如高优先级线程被抢占，或者 GC 暂停阻塞了音频回调。

[待补充：AudioFlinger track 的 Perfetto 截图描述]

## Perfetto 中的多媒体性能分析

### MediaCodec 相关 Track

在 Perfetto 中，MediaCodec 的活动主要出现在以下位置：

- **App 进程的线程 track**：`MediaCodec` 相关的 slice 名称通常包含 `ACodec`、`MediaCodec`、`decode`、`queueInputBuffer`、`dequeueOutputBuffer` 等关键词
- **codec 进程**：硬件编解码器可能运行在独立的 codec 进程中（`mediacodec` 或 `omx` 进程）

### 常用 SQL 查询

**查询 MediaCodec 解码耗时**：

```sql
SELECT
  s.ts AS timestamp_ns,
  s.dur AS duration_ns,
  s.name AS slice_name,
  p.name AS process_name,
  t.name AS thread_name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
JOIN process AS p ON t.upid = p.upid
WHERE
  (s.name GLOB '*MediaCodec*' OR s.name GLOB '*ACodec*')
  AND (s.name GLOB '*decode*' OR s.name GLOB '*queueInputBuffer*'
       OR s.name GLOB '*dequeueOutputBuffer*')
ORDER BY timestamp_ns;
```

这个查询会返回所有 MediaCodec 解码相关的 slice，包括时间戳、耗时、所属进程和线程。通过分析 `duration_ns` 列，我们可以判断解码是否成为瓶颈——如果单帧解码耗时超过一个 VSync 周期（如 120Hz 设备上超过 8.33ms），解码器就是瓶颈。

[已验证: Perfetto 官方文档, ui.perfetto.dev — SQL Reference]

**查询 buffer 操作详情**：

```sql
SELECT
  s.ts AS timestamp_ns,
  s.dur AS duration_ns,
  s.name AS slice_name,
  EXTRACT_ARG(s.arg_set_id, 'buffer_id') AS buffer_id,
  EXTRACT_ARG(s.arg_set_id, 'size') AS buffer_size_bytes,
  EXTRACT_ARG(s.arg_set_id, 'flags') AS buffer_flags
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
WHERE
  s.name GLOB '*MediaCodec::queueInputBuffer*'
  OR s.name GLOB '*MediaCodec::dequeueOutputBuffer*'
ORDER BY timestamp_ns;
```

这个查询提取 buffer 操作的详细参数，可以帮助理解 buffer 的使用模式和流转状态。

**聚合解码性能统计**：

```sql
SELECT
  p.name AS process_name,
  s.name AS slice_name,
  COUNT(s.id) AS event_count,
  AVG(s.dur) / 1e6 AS avg_duration_ms,
  MAX(s.dur) / 1e6 AS max_duration_ms
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
JOIN process AS p ON t.upid = p.upid
WHERE s.name GLOB '*decode*'
GROUP BY p.name, s.name
ORDER BY avg_duration_ms DESC;
```

这个查询给出每个进程的平均和最大解码耗时，适合用来快速定位"哪个进程的解码最慢"。

[待验证: EXTRACT_ARG 的具体参数名在不同 Android 版本上可能有差异]

### 抓取多媒体 Trace 的 atrace 分类

要抓取完整的 MediaCodec 和 AudioFlinger 信息，需要启用以下 atrace 分类：

```bash
# [待验证] 具体命令格式需按设备和抓取方式核对
# 需要启用的 atrace 分类：
media,codec,audio,view,gfx,am
```

- `media`：MediaCodec、ACodec 相关事件
- `codec`：编解码器内部事件
- `audio`：AudioFlinger mixer 活动、音频 underrun 事件
- `view`：Surface 渲染相关事件
- `gfx`：SurfaceFlinger 合成事件

[待验证: 不同 Android 版本上 atrace 分类的可用性差异]

## 常见问题与最佳实践

### 首帧解码延迟过高

视频播放启动时，用户感知到的"首帧时间"由以下环节构成：网络请求（如果是流媒体）→ 解复用 → 编解码器初始化 → 首帧解码 → 渲染。其中编解码器初始化是隐藏的性能杀手。

创建一个 MediaCodec 实例并完成配置/启动，通常需要 30-80ms（硬件解码器）到 100-200ms（软件解码器）。如果每次播放都创建新实例，这个开销无法避免。解决方案是**解码器池化**：维护一个预热好的 MediaCodec 实例池，新播放请求直接从池中取出已初始化的实例。Media3 的 Player 池化模式就是基于这个思路。

### 视频播放卡顿的三种根因

视频播放出现卡顿时，需要区分三种不同的根因：

**Buffer 耗尽（rebuffering）**：网络带宽不足以支撑当前码率，缓冲区被耗尽。表现为播放器进入 buffering 状态，用户看到加载指示器。通过降低目标码率或增加预缓冲时长可以缓解。

**解码慢**：硬件解码器处理某些复杂帧（如高运动场景的 B 帧）耗时过长，超过了一个 VSync 周期。在 Perfetto 中表现为 decode slice 的 duration 出现异常峰值。解决方案包括降低分辨率/码率、或者切换到更高效的编码格式（如从 AVC 切换到 HEVC）。

**渲染慢**：解码完成了，但 GPU 合成耗时过长。这种情况在 HDR 内容或存在复杂的 Surface 叠加（如字幕 + 弹幕 + 视频）时容易出现。在 Perfetto 中，常见表现是 SurfaceFlinger 的合成耗时异常。

### 音频 Underrun 的根因分析

Audio underrun 是指 AudioFlinger 的 buffer 被耗尽，导致输出端没有数据可播放，用户听到"嘟"的一声断续。常见的根因有：

- **CPU 调度不及时**：音频回调线程（SCHED_FIFO 高优先级）被其他高负载线程抢占。常见表现是音频线程的 scheduling slice 出现异常间隔
- **GC 暂停**：如果音频回调在 Java 层执行，ART GC 的 stop-the-world 暂停会阻塞音频数据的生产。这就是为什么 AAudio 的推荐使用方式是纯 native 代码回调
- **锁竞争**：音频回调路径上等待被其他线程持有的锁。在 Perfetto 中可以通过 monitor contention slice 看到锁等待

### 多实例编解码器的资源限制

硬件编解码器（VPU）的数量是有限的。大多数中端设备的 VPU 最多同时支持 2-4 路硬件编解码。超出限制后，多余的实例会被降级为软件解码，性能急剧下降。

这个限制在以下场景容易触发：
- 短视频 Feed 中同时有多个播放器处于 prepared 状态
- 视频通话应用同时做编码和解码
- 后台有其他应用在使用编解码器（如视频录制）

在 Perfetto 中，如果发现 MediaCodec 创建耗时异常高（>200ms）或者 `onError` 回调被触发，需要排查是否碰到了硬件编解码器的并发上限。

### Camera → MediaCodec 编码管线

Camera 采集和视频编码的组合管线（如直播、录屏）需要特别注意帧的传递效率。理想的做法是让 Camera 的输出 Surface 直接作为 MediaCodec 编码器的 input Surface（`createInputSurface()`），形成零拷贝的直连管线。这样 Camera 采集的帧不需要经过 App 进程中转就直接进入编码器。

但如果需要在帧上叠加水印或滤镜，就必须在中间插入一个 GPU 处理步骤：Camera → OpenGL Texture → 处理 → MediaCodec input Surface。这个额外的 GPU pass 会增加约一帧的延迟。对于实时直播场景，需要权衡画质增强和延迟增加之间的取舍。

[关联: §14.9 Camera 性能与 Perfetto 分析]

## 版本演进

- **Android 4.1 (Project Butter)**：引入 Fast Mixer Thread，音频延迟从约 100ms 降到约 20-40ms
- **Android 4.3**：引入 Surface 作为 MediaCodec output，开启零拷贝视频渲染路径
- **Android 5.0**：引入 async mode (`setCallback`)，MediaCodec 从同步轮询变为异步回调驱动
- **Android 8.0**：引入 AAudio API，提供 C 语言级别的低延迟音频接口
- **Android 8.1**：AAudio 支持 MMAP 路径，延迟可降至 10ms 以下
- **Android 11**：引入 low-latency decoding 模式（需要 SoC 支持），支持 tunneled playback via Codec2
- **Android 10+**：媒体模块（`com.android.media`）通过 APEX 格式可独立更新，不再依赖系统 OTA
- **Media3 1.10 (2026-03)**：动态调度、Compose PlayerSurface、Player 池化预热

[待验证: low-latency decoding 在不同 SoC 上的支持情况]

## 参考资料

- AOSP MediaCodec 源码：`frameworks/av/media/libstagefright/`
- AOSP AudioFlinger 源码：`frameworks/av/services/audioflinger/`
- 官方文档 MediaCodec：https://developer.android.com/reference/android/media/MediaCodec
- 官方文档 AAudio Low Latency：https://developer.android.com/ndk/guides/audio/aaudio/low-latency-audio
- Media3 官方文档：https://developer.android.com/media/media3
- Google Android Developers Blog, Media3 1.10 Release, 2026-03-30
- Perfetto SQL Reference：https://ui.perfetto.dev
