---
title: "Audio Pipeline 延迟与性能"
chapter: "1.16"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [audio, audioflinger, aaudio, latency, perfetto, scheduling]
related_chapters: ["1.4", "5.1", "5.6", "16.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-09"
drafted_date: "2026-04-09"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-09"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "https://source.android.com/docs/core/audio/latency"
  - type: official
    path: "https://source.android.com/docs/core/audio/architecture"
  - type: official
    path: "https://developer.android.com/ndk/guides/audio"
  - type: research
    path: "intake/research-feeds/2026-04-08-15-audioflinger-fast-mixer-aaudio-mmap-pipeline-architecture.md"
  - type: research
    path: "intake/research-feeds/2026-04-08-15-android17-background-audio-hardening-audio-focus.md"
  - type: research
    path: "intake/research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md"
---

# 1.16 Audio Pipeline 延迟与性能

## 为什么需要了解 Audio Pipeline

当我们讨论 Android 性能时，注意力通常集中在渲染管线上——帧率、掉帧、VSync。但用户的感知不止来自视觉。点击一个钢琴 App 的琴键，如果声音在手指触摸后 100ms 才响起，用户会觉得这台设备「卡了」。在视频会议中，200ms 的往返延迟会让对话变得不自然。游戏里 50ms 的音效延迟，足以让打击感消失殆尽。

音频延迟和渲染延迟在技术结构上有一个有趣的对称关系：SurfaceFlinger 负责画面的合成与显示，AudioFlinger 负责声音的混音与输出。两者都是 Android 框架层中承上启下的核心服务，都通过 HAL 与硬件交互，都对延迟极其敏感。理解了其中之一的架构，学习另一个会事半功倍。

人类对音频延迟的感知阈值比视觉更严苛：超过 20ms 的往返延迟就能被训练过的耳朵察觉，专业音乐制作要求低于 10ms。而 Android 设备的音频延迟，从早期的 100ms 以上到如今 Pixel 设备的 10ms 以下，经历了漫长而曲折的优化历程。

了解 Audio Pipeline 的内部机制，能帮助我们在 Perfetto 中识别音频相关的性能瓶颈，理解为什么某些场景下声音会卡顿或延迟，以及如何为不同场景选择正确的音频 API。

## Audio Pipeline 架构全景

Android 音频管线的整体数据流可以概括为：

```
App (AudioTrack/AAudio)
    ↓  write()
AudioFlinger (AudioServer)
    ↓  混音 + 重采样
Audio HAL (AIDL, Android 14+)
    ↓  ALSA/TinyALSA
DSP / Codec
    ↓
Speaker / Headphone
```

这个管线看起来简单，但每一层都有影响延迟的关键设计决策。

### AudioFlinger 的角色

AudioFlinger 是 Android 音频子系统的核心服务，运行在 `audioserver` 进程中（自 Android 8.0 起从 `mediaserver` 分离）。它的职责包括：

1. **接收来自所有 App 的音频数据**——通过共享内存（SharedMemory）和 Binder IPC
2. **混音（Mixing）**——将多个 App 的音频流合并为一路输出
3. **重采样（Resampling）**——当 App 的采样率与输出设备不匹配时，进行采样率转换
4. **音量控制与路由**——根据 AudioPolicyService 的决策，将音频路由到正确的输出设备
5. **将混音后的数据写入 Audio HAL**——最终由 HAL 驱动硬件输出

[已验证: AOSP android-16.0.0_r1, frameworks/av/services/audioflinger/]

### AudioPolicyService：音频路由的大脑

AudioFlinger 负责「怎么播放」，AudioPolicyService 负责「播放到哪里」。当 App 创建一条音频流时，AudioPolicyService 根据音频类型（stream type）、用途（usage）、设备连接状态（耳机、蓝牙、扬声器）做出路由决策。

路由决策本身不直接产生延迟，但路由切换会。当用户插入耳机时，AudioPolicyService 会重新路由音频流，这个过程涉及关闭旧的输出流、打开新的输出流、重新协商缓冲区大小——在 Perfetto 中表现为一段短暂的音频中断。

## 延迟分解：从 App 到扬声器

要理解音频延迟的来源，我们需要把整个路径拆开来看。

### 输出延迟（Output Latency）

输出延迟是从 App 调用 `write()` 写入音频数据到声音从扬声器发出的时间。它由以下几部分组成：

| 阶段 | 典型延迟 | 说明 |
|------|----------|------|
| App 缓冲区 | 2-20ms | App 写入的缓冲区大小，取决于 API 配置 |
| AudioFlinger 混音 | 2-5ms | Normal Mixer 的处理周期 |
| HAL 缓冲区 | 2-10ms | HAL 层缓冲，与硬件协商 |
| DSP 处理 | 1-5ms | 硬件编解码和信号处理 |
| DAC + 输出 | <1ms | 数模转换和扬声器响应 |

[待验证: 上表数值为综合多设备的大致范围，不同 SoC 平台差异较大]

输出延迟的典型值在普通设备上为 20-50ms，在优化较好的设备（如 Pixel）上可以低至 10ms 以下。

### 往返延迟（Round-Trip Latency）

往返延迟是输入延迟加输出延迟的总和——声音从麦克风进入，经过处理，从扬声器输出的完整周期。这是音乐制作和视频会议场景最关键的指标。

2017 年，Android 设备的平均往返延迟约为 109ms。到 2021 年，这个数字降到了 40ms 以下。Pixel 3a（2019）是第一款达到 10ms 往返延迟的 Android 设备。但这个成绩依赖硬件支持——不是所有设备都能达到。

[已验证: 来源见 research-feeds/2026-04-08-15-audioflinger-fast-mixer-aaudio-mmap-pipeline-architecture.md，数据来自 Google 官方统计]

### 缓冲区大小：延迟的根本决定因素

音频延迟的核心公式很简单：

```
单次缓冲延迟 = buffer_size / sample_rate
```

一个 480 帧、48000Hz 的缓冲区，延迟就是 480/48000 = 10ms。但音频系统通常使用双缓冲甚至多缓冲，所以实际延迟是缓冲区大小的 2-3 倍。

在 Normal Mixer 路径下，AudioFlinger 的默认缓冲区大小由 HAL 层决定，通常在 480-960 帧之间（10-20ms）。这个值在不同设备上差异很大——同一台设备上扬声器输出和蓝牙输出的缓冲区大小也不同。

## FAST Mixer：低延迟的秘密

Android 4.1（Project Butter）引入了 FAST Mixer，这是 Android 音频低延迟的关键机制。

### Normal Mixer vs FAST Mixer

普通应用使用 Normal Mixer 路径。多个音频流在这里被混音、重采样、应用音量调节后，写入 HAL。Normal Mixer 的处理周期较长（通常 20ms），因为它需要处理重采样和混音等 CPU 密集型操作。

FAST Mixer 是一条专门的低延迟路径。它的设计哲学是：**尽可能少做事情**。

- 不做混音——只服务单一音频流
- 不做重采样——要求 App 的采样率与输出设备完全匹配
- 不做复杂的音量曲线——使用简化的音量控制
- 使用更小的缓冲区——通常为 192-240 帧（4-5ms）

[已验证: AOSP, frameworks/av/services/audioflinger/FastMixer.cpp]

### 进入 FAST Mixer 的条件

不是所有音频流都能进入 FAST Mixer。进入条件相当严格：

1. App 使用 `AudioTrack` 并设置 `PERFORMANCE_MODE_LOW_LATENCY`
2. 或使用 AAudio 并设置 `AAUDIO_PERFORMANCE_MODE_LOW_LATENCY`
3. 音频流的采样率与 HAL 输出设备的原生采样率一致（通常是 48000Hz）
4. 设备 HAL 支持低延迟输出（`AUDIO_OUTPUT_FLAG_FAST`）
5. 当前没有其他低延迟流占用 FAST Mixer（通常只有一个 FAST Mixer 实例）

这意味着，如果 App 请求了 44100Hz 而设备输出是 48000Hz，即使设置了低延迟模式，也不会进入 FAST Mixer 路径。

### FAST Mixer 的线程调度

FAST Mixer 运行在一个专用线程上，使用 `SCHED_FIFO` 实时调度策略（而非普通应用的 `SCHED_NORMAL`）。这个优先级设置确保了即使在系统负载较高时，音频数据的写入也能准时完成。

在 Perfetto 中，我们可以通过 CPU scheduling track 观察到 FAST Mixer 线程的调度行为。如果发现这个线程频繁被抢占或无法及时唤醒，通常意味着系统负载过高或 CPU 频率调度策略不适合音频场景。

[图：Perfetto 中 AudioFlinger FAST Mixer 线程的 CPU scheduling slice，标注 SCHED_FIFO 优先级]

## AAudio 与 MMAP：绕过混音器

### AAudio：面向低延迟的 C API

AAudio 是 Android 8.0 引入的原生音频 C API，专为低延迟音频场景设计（游戏、音乐制作、实时音频处理）。相比传统的 OpenSL ES（已标记为废弃）和 Java 层的 AudioTrack，AAudio 提供了更底层的控制和更低的延迟。

AAudio 的核心设计原则是简洁：创建流（`AAudioStream`）、写入数据（`aaudio_stream_write`）、关闭流。没有复杂的回调层级，没有 Java 层的额外开销。

[已验证: developer.android.com/ndk/guides/audio/aaudio]

### MMAP 模式：直接写入硬件缓冲区

Android 8.1 引入了 MMAP（Memory Mapped）模式，这是 Android 音频延迟优化的终极武器。

在传统路径中，音频数据需要经过：App 缓冲区 → Binder IPC → AudioFlinger 混音 → HAL 缓冲区 → 硬件。每经过一层，延迟就多积累一些。

MMAP 模式改变了这个流程。App 通过内存映射直接与 ALSA 驱动共享一个缓冲区，写入的数据直接被硬件消费。在 EXCLUSIVE 模式下，AudioFlinger 的混音器完全被绕过：

```
传统路径:  App → AudioFlinger → HAL → 硬件    (~20-50ms)
FAST路径:  App → FastMixer → HAL → 硬件       (~10-20ms)
MMAP路径:  App → [共享内存] → 硬件              (~5-10ms)
```

[已验证: 来源见 research-feeds/2026-04-08-15-audioflinger-fast-mixer-aaudio-mmap-pipeline-architecture.md，引用 Google AOSP 文档]

MMAP 模式有两个子模式：

- **SHARED 模式**：AudioServer 仍然参与管理，但使用 MMAP 缓冲区替代传统的 Binder 传输。延迟比传统路径低，但不是最低。
- **EXCLUSIVE 模式**：App 独占硬件缓冲区，AudioServer 混音器完全绕过。这是延迟最低的路径。

MMAP 模式的效果高度依赖硬件厂商的实现——不是所有设备都支持。这也是为什么同样的 AAudio 代码在不同设备上延迟差异巨大的原因。

### Oboe：Google 推荐的跨版本封装

Google 的 Oboe 库封装了 AAudio（Android 8.0+）和 OpenSL ES（回退），提供统一的低延迟音频 API。它的核心价值在于：自动检测设备能力，选择最优路径（MMAP EXCLUSIVE → MMAP SHARED → FAST Mixer → Normal Mixer），并处理各种设备兼容性问题。

对于需要在多种 Android 设备上实现低延迟音频的开发者，Oboe 是比直接使用 AAudio 更稳妥的选择。

## 在 Perfetto 中的表现

分析音频性能问题时，Perfetto 是首选工具。

### 抓取音频 Trace

```bash
adb shell perfetto -t 10s \
  --atrace-categories audio,sched,freq,idle \
  --buffer 64mb -o /data/misc/perfetto-traces/trace
```

[已验证: 来源见 research-feeds/2026-04-08-15-audioflinger-fast-mixer-aaudio-mmap-pipeline-architecture.md]

### 关键 Track 与 Slice

在 Perfetto 中，音频相关的关键信息分布在几个位置：

1. **AudioFlinger 线程**：搜索 `AudioFlinger` 可以找到混音线程和 FAST Mixer 线程。观察它们是否在预期的时间间隔内被唤醒和执行。

2. **AudioTrack 写入**：`atrace` 的 `audio` 类别会追踪 AudioTrack 的写入操作。如果在主线程上看到频繁的 AudioTrack write slice，说明音频写入可能在阻塞主线程。

3. **CPU Scheduling**：检查 FAST Mixer 线程的 CPU 调度状态。`SCHED_FIFO` 线程应该有稳定的执行周期。如果看到频繁的 `Task State: Runnable` 但未被调度执行，说明系统负载过高。

4. **缓冲区水位线（Underrun）**：音频 underrun 是最常见的音频性能问题。当 AudioFlinger 需要读取数据但 App 还没来得及写入时，就会发生 underrun——用户听到的就是「咔嗒」声或断续的播放。在 Perfetto 中可以通过 SQL 查询检测：

```sql
SELECT slice.name, slice.ts, slice.dur
FROM slice
JOIN track ON slice.track_id = track.id
WHERE track.name LIKE '%Audio%'
  AND slice.name LIKE '%underrun%'
ORDER BY slice.ts
```

[待验证: SQL 查询中的 track.name 和 slice.name 需要根据实际设备上的 atrace 标签调整]

### 常见音频性能问题的 Trace 特征

| 问题 | Trace 表现 | 典型原因 |
|------|-----------|----------|
| 音频断续 | AudioFlinger 线程执行间隔不均匀 | CPU 被其他高优先级任务抢占 |
| 延迟过大 | App write → 声音输出间隔过长 | 走了 Normal Mixer 路径而非 FAST |
| Underrun | AudioFlinger 读取时缓冲区为空 | App 写入不及时或缓冲区太小 |
| 后台音频卡顿 | AudioFlinger 线程被冻结 | Android 17 后台限制（见下节） |

[图：Perfetto 中音频 underrun 的 Trace 表现，标注缓冲区空的时间段]

## Android 17 音频性能变更

Android 17（API 37）对音频子系统引入了多项重要变更，对 App 开发和性能分析都有直接影响。

### 后台音频强化（Audio Hardening）

Android 17 对后台音频播放实施了严格管控。这是 Android 持续收紧后台执行限制的又一举措，影响范围比以往更广：

**受影响的 API**：
- `AudioTrack` / `AudioRecord` 的播放和录制
- `AudioManager.requestAudioFocus()` ——音频焦点请求
- `AudioManager` 的音量变更 API

**新规则**：App 在后台（无可见的 Activity）调用上述 API 时，必须通过具备「while-in-use」（WIU）能力的前台服务。`SHORT_SERVICE` 类型的前台服务不具备 WIU 能力。不合规的调用行为：

- 播放/录制操作静默失败（不抛异常，但无声音输出）
- `requestAudioFocus()` 返回 `AUDIOFOCUS_REQUEST_FAILED`

[已验证: developer.android.com/about/versions/17/behavior-changes-17#audio-hardening]

**调试方法**：

```bash
# 在 Android 16+ 设备上提前测试
adb shell cmd audio set-enable-hardening

# 查看违规日志
adb logcat -s AudioHardening

# 查看详细音频状态
adb dumpsys audio
```

**对性能分析的影响**：这个变更可能导致一些意想不到的性能表现。例如，App 被冻结后意外恢复音频会触发运行时限制波动，表现为短暂的音频卡顿后突然静音。在 Perfetto 中，这看起来像是 AudioFlinger 线程先恢复正常执行、随后又停止——需要在 logcat 中配合 AudioHardening 日志才能准确诊断。

### AudioTrack 新增精确 Flush 控制

Android 17 新增 `flushWrittenFramesFromPosition(long, int)` 方法，支持从指定位置精确 flush 已写入的音频帧。配套 `FLUSH_FROM_ACCURACY_BEST_EFFORT` 和 `FLUSH_FROM_ACCURACY_EXACT` 两种精度模式。

这个 API 的应用场景是音频 seek 操作：当用户在音乐播放器中拖动进度条时，App 需要 flush 已缓冲的旧数据并从新位置开始播放。精确 flush 可以减少这个切换过程中的静音间隙。

[已验证: developer.android.com/sdk/api_diff/37/changes, Android 17 API diff]

### 编解码器来源查询

新增 `getCodecProvenance()` 方法，允许 App 查询当前音频数据使用的编解码器类型——硬件解码、软件解码还是 offload 模式。这个信息对性能优化决策有直接帮助：

- 硬件解码功耗最低，但不是所有格式都支持
- Offload 模式将压缩数据直接透传给 DSP，CPU 几乎不参与
- 软件解码延迟最低，但 CPU 占用高

### Assistant 独立音量流

Android 17 引入了 `USAGE_ASSISTANT` 专用音量流，将语音助手的音频与标准媒体流解耦。用户可以独立控制 Assistant 音量和媒体音量，不会出现「调低音乐音量后 Assistant 也听不到了」的问题。

配套 `MODE_ASSISTANT_CONVERSATION` 音频模式进一步提升音量控制的一致性。

[已验证: research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md]

### AAudio Offload 支持

Android 16 起支持 AAudio Offload，允许通过 AAudio 直接将压缩音频数据（如 AAC/MP3）透传至硬件 DSP 解码。这意味着 CPU 不再需要参与解码过程，在长音频播放场景下可以节省可观的功耗。

## API 选择指南

根据不同场景的延迟和功能需求，Android 音频 API 的选择策略如下：

| 场景 | 推荐 API | 目标延迟 | 说明 |
|------|----------|----------|------|
| 游戏音效 | Oboe / AAudio | 小于20ms | 使用 LOW_LATENCY 模式 |
| 音乐制作/DAW | Oboe / AAudio (MMAP) | 小于10ms | 需要 EXCLUSIVE 模式和硬件支持 |
| 视频会议 | Oboe / AAudio | 小于50ms | 往返延迟需同时优化输入 |
| 音乐播放 | MediaPlayer / ExoPlayer | 不敏感 | Offload 模式优先，降低功耗 |
| 语音助手 | AudioTrack + USAGE_ASSISTANT | 小于30ms | Android 17 独立音量流 |
| 普通音效 | SoundPool | 不敏感 | 短音效预加载，延迟可接受 |

[适用版本: Android 8.0+，MMAP 需要 Android 8.1+ 和硬件支持]

## 与其他机制的关系

Audio Pipeline 与全书其他章节的关联点：

- **§1.4 Binder IPC**：AudioFlinger 与 App 之间通过 Binder IPC 和共享内存传输音频数据。传统路径下 Binder 调用的开销是延迟的一部分。
- **§5.1 CPU 调度**：FAST Mixer 使用 `SCHED_FIFO` 实时调度策略。音频线程的调度行为直接影响延迟稳定性。
- **§5.6 功耗管理**：持续的音频播放会阻止 CPU 进入低功耗状态。AAudio Offload 模式通过将解码工作交给 DSP 来降低 CPU 功耗。
- **§16.5 Android 17 变更**：后台音频强化是该版本最重要的音频相关行为变更。
- **§2.6 SurfaceFlinger**：SurfaceFlinger 和 AudioFlinger 是 Android 框架层中对称的两个核心服务，理解其中一个的架构有助于学习另一个。

## 版本演进

| 版本 | 变更 | 性能影响 |
|------|------|----------|
| Android 4.1 | FAST Mixer 引入（Project Butter） | 低延迟路径首次出现 |
| Android 5.0 | 采样率转换优化 | Normal Mixer 延迟降低 |
| Android 8.0 | AAudio API 引入 | 原生低延迟 C API |
| Android 8.1 | MMAP 模式 | 绕过 AudioFlinger，延迟进一步降低 |
| Android 9 | Audio HAL 从 HIDL 迁移 | AIDL 过渡准备 |
| Android 12 | Audio HAL AIDL 化开始 | 模块化架构 |
| Android 14 | Audio HAL 全面 AIDL | Treble 架构完善 |
| Android 16 | AAudio Offload 支持 | 压缩音频透传 DSP，降低 CPU 功耗 |
| Android 17 | 后台音频强化 + 精确 flush + 编解码器来源查询 | 更严格的后台管控，更精细的播放控制 |

[待验证: Audio HAL AIDL 全面过渡的时间线在不同 SoC 平台上可能有差异]

## 常见问题与误区

**误区：所有设备都支持 FAST Mixer 和 MMAP。**

事实是：FAST Mixer 的可用性取决于 HAL 是否声明 `AUDIO_OUTPUT_FLAG_FAST`。MMAP 模式需要硬件厂商实现 Audio HAL 中的 MMAP 支持。许多中低端设备虽然运行最新的 Android 版本，但 HAL 层并未实现这些低延迟特性。Google Play 上 Oboe 团队的统计数据显示，支持低延迟路径的设备比例在逐年增长，但远未达到 100%。

**误区：Java AudioTrack 的延迟总是比 AAudio 高。**

不完全准确。AudioTrack 在设置 `PERFORMANCE_MODE_LOW_LATENCY` 后，也会走 FAST Mixer 路径。在这种情况下，Java 层的开销主要是 JNI 跨调用的成本（约 100-200 微秒），在总延迟中占比很小。真正的延迟差异来自 API 的灵活性——AAudio 可以直接配置 MMAP EXCLUSIVE 模式，而 AudioTrack 不支持。

**误区：音频延迟只与缓冲区大小有关。**

缓冲区大小是主要因素，但不是唯一因素。调度延迟（线程何时被 CPU 执行）、Binder IPC 延迟、重采样开销、HAL 层的内部缓冲策略，都会叠加到总延迟上。在系统负载较高时，即使配置了很小的缓冲区，调度延迟也可能导致实际延迟远超理论值。

## 扩展

### 🔸 蓝牙音频延迟分析

蓝牙音频增加了额外的编码和传输延迟，这使得整体延迟显著高于有线输出：

- **A2DP（SBC 编码）**：100-200ms 额外延迟。这是蓝牙音频的基本模式，延迟最高。
- **aptX**：50-80ms。高通的蓝牙编码方案，延迟优于 SBC。
- **LDAC**：30-50ms。索尼的高品质蓝牙编码，延迟在三者中最低，但功耗最高。
- **LE Audio（LC3 编码）**：20-40ms。蓝牙 5.2 引入的新一代低延迟音频协议，代表了蓝牙音频延迟的未来方向。

蓝牙音频的额外延迟来源包括：编码/解码处理时间、无线传输的协议开销、Bluetooth Audio HAL 内部的额外缓冲区。空间音频（Spatial Audio）结合头部追踪功能对延迟的要求更高——头部转动到声音位置更新的延迟需要低于 20ms 才能避免感知错位。

[待验证: LE Audio 的实际部署比例和设备支持情况，2026 年数据]

### 🔸 游戏音频性能最佳实践

为游戏场景配置低延迟音频时的核心清单：

1. **使用 Oboe 库**，而非直接调用 AAudio 或 OpenSL ES。Oboe 会自动选择最优路径。
2. **设置 `PerformanceMode::LowLatency`**，同时设置 `SharingMode::Exclusive`（如果不需要混音）。
3. **匹配设备原生采样率**。调用 `AAudio_getSampleRate()` 获取设备输出采样率，用这个值创建流。不匹配的采样率会导致无法进入 FAST Mixer。
4. **使用回调模式**（`setCallback`）而非阻塞写入。回调模式由 AudioFlinger 在需要数据时主动拉取，减少了 App 侧的调度延迟。
5. **避免在音频回调中做重计算**。音频回调运行在 AudioFlinger 的高优先级线程上，任何阻塞操作（如内存分配、文件 I/O、锁等待）都会直接影响延迟。预分配所有需要的缓冲区，使用无锁数据结构。
6. **监控 underrun**。调用 `AAudioStream_getXRunCount()` 持续监控。如果 underrun 持续增加，说明缓冲区太小或 App 侧处理太慢——适当增大缓冲区是更务实的做法。

[适用版本: Android 8.0+，Oboe 要求 minSdk 16+]

## 参考资料

- [Android Audio Latency](https://source.android.com/docs/core/audio/latency) — Google AOSP 官方文档
- [Android Audio Architecture](https://source.android.com/docs/core/audio/architecture) — 架构全景
- [AAudio API Guide](https://developer.android.com/ndk/guides/audio/aaudio) — 开发者指南
- [Oboe Library](https://github.com/google/oboe) — Google 推荐的低延迟音频封装库
- AOSP: `frameworks/av/services/audioflinger/` — AudioFlinger 源码
- AOSP: `frameworks/av/services/audiopolicy/` — AudioPolicyService 源码
- [Android 17 Behavior Changes: Audio](https://developer.android.com/about/versions/17/behavior-changes-17#audio-hardening) — 后台音频强化
