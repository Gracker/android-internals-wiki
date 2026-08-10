---
title: Audio Pipeline 延迟与性能
chapter: '1.16'
section: '1.16'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 API 37 official documentation
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/audio"
  - type: official
    path: "https://source.android.com/docs/core/audio/latency/design"
  - type: official
    path: "https://source.android.com/docs/core/audio/latency/measurements"
  - type: official
    path: "https://source.android.com/docs/core/audio/aaudio"
  - type: official
    path: "https://source.android.com/docs/core/audio/debugging"
  - type: official
    path: "https://source.android.com/docs/core/audio/aidl-hidl-comp"
  - type: official
    path: "https://developer.android.com/ndk/guides/audio/audio-latency"
  - type: official
    path: "https://developer.android.com/ndk/guides/audio/aaudio/aaudio"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/bg-audio"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/reference/android/media/AudioTrack"
  - type: official
    path: "https://perfetto.dev/docs/reference/perfetto-cli"
  - type: aosp
    path: "frameworks/av/services/audioflinger/Threads.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/av/services/audioflinger/fastpath/FastMixerState.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/av/services/audioflinger/fastpath/FastMixerState.h @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/av/media/libaaudio/include/aaudio/AAudio.h @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/media/java/android/media/AudioTrack.java @ android-17.0.0_r1"
tags:
  - android
  - audio
  - audioflinger
  - aaudio
  - mmap
  - fastmixer
  - latency
  - perfetto
related_chapters:
  - '1.4'
  - '5.1'
  - '5.6'
  - '16.5'
created_date: '2026-04-09'
drafted_date: '2026-04-09'
reviewed_date: '2026-07-25'
reviewed_by: Codex
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
deepseek_cn_review_state: done
created_by: "task2a-knowledge-gap"
drafted_by: "openclaw-task2a"
last_task6_review_log: "logs/review/2026-05-27-16-review.md"
last_task6_at: 2026-06-16T20:10:00+08:00
last_task6_audit: "2026-06-11"
last_task2b_at: "2026-05-27T14:50:00+08:00"
task9_reviewed_date: "2026-06-16"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-16T15:25:46+08:00"
task9_review_notes: "2026-05-24 08:20 Task9 idle audit: needs-rework；P0: FastMixer.cpp 与 AAudio service AOSP 路径错误，已写入 metadata/queue.json。 | 2026-05-24 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 1；Android 16 AIDL CAP/IConfig 强制口径仍过硬，需收窄为 AIDL HAL fully supports CAP、legacy/HIDL 兼容与 XML 转 AIDL reference implementation；另有 AAudio offloaded 与 Android 17 WIU FGS 条件混写的 P2 建议。 | 2026-05-25 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0；Android 17 background audio hardening 的 visible Activity/非 SHORT_SERVICE FGS、target API 37 WIU、USAGE_ALARM exact alarm 豁免条件与 AAudio offloaded playback 前提混写，已写入 metadata/queue.json。 | 2026-05-27 15:22 Task9 auto-fix：收窄 AAudio Power Saving Offloaded 与 DSP 解码表述，避免把省电 output path 写成无条件 DSP 解码；回到 Task6 复审。 | 2026-05-27 16:21 Task9 deep-review: pass-tech-review；P0 0 / P1 0 / P2 0 新增；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-16 15:25 Task9 idle audit AUTO-FIX：收窄 FastMixer fast track slot 上限；android-16.0.0_r1 默认 8（index 0 预留，应用侧默认 7），但 ro.audio.max_fast_tracks 可配置 2-32，回到 Task6 复审。"
review_type: "task6-writing-quality-review"
last_task9_audit: "2026-06-16"
last_task9_review_log: "logs/deep-review/2026-06-16-15-audit.md"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-25 Task6：revisiting 写作质检通过；未新增 L1/L2 小修；沿用 Task9 2026-05-25 P1 技术回炉，章节保持 task2b_pending。 | 2026-05-27 15:08 Task6：revisiting 写作质检通过；未新增 L1/L2 正文问题；Task2B 修复后的 Android 17 后台音频与 AAudio offloaded 边界已进入正文；Task9 result 仍为 needs-rework，送 Task9 复审。 | 2026-05-27 16:08 Task6：复审 Task9 auto-fix 后内容；删除开头主观填充词，维持 Android 17 后台音频与 AAudio offloaded 边界表述；无新增 L3/L4 回炉项，Task9 result 为 auto-fixed，继续送 Task9 复审。"
task2b_notes: "2026-05-27 Task2B fallback：修复 Task9 2026-05-25 P1；拆开 Android 17 后台音频 hardening 生命周期条件与 AAudio Power Saving Offloaded 输出路径，补 targetSdk 37+ WIU / USAGE_ALARM 豁免和 cmd audio 强制测试语义。"
last_task9_autofix_at: "2026-06-16"
last_task2b_verifier_at: "2026-05-27T15:34:00+08:00"
task2b_verifier_result: ready-for-task6
task6_reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-05-27"
last_deepseek_cn_review_at: 2026-06-21
---

# 1.16 Audio Pipeline 延迟与性能

音频性能问题不能只看“一个 buffer 有多少帧”。从 App 生成一个 sample，到扬声器发声，中间可能经过客户端队列、AudioFlinger、HAL、DSP、Codec 和换能器；录放同时进行时，还要再加输入路径、App 算法和两套并不严格同步的音频时钟。

以下分析以 Android 17 / API 37、AOSP `android-17.0.0_r1` 为当前锚点，回答四个工程问题：

1. 这条流最终走了 Normal、Fast、MMAP 还是 Offload？
2. 延迟来自排队、调度、重采样、算法处理，还是硬件路径？
3. 出现 underrun/ overrun 时，谁没有按时交付数据？
4. Android 17 的后台音频限制或新 offload API，是否改变了现象的含义？

## 1. 先统一“延迟”的口径

官方 NDK 文档把音频延迟分成四类：

- **输出延迟**：App 生成 sample，到它从扬声器或耳机播放出来的时间。
- **输入延迟**：声音到达麦克风等输入端，到对应数据可被 App 读取的时间。
- **往返延迟**：输入延迟 + App 处理时间 + 输出延迟。
- **预热延迟**：首次入队后，整条音频管线从关闭或 standby 状态启动所需的时间。

这四个指标不能混用。播放器报告的写入耗时，不是输出延迟；`AudioTimestamp` 或 AAudio timestamp 描述的是 frame position 与时钟的对应关系，也不等于麦克风到扬声器的声学往返时间。

### 1.1 buffer 时长只是一个局部量

单个缓冲区承载的音频时长为：

```text
buffer_duration = frame_count / sample_rate
```

例如 48kHz 下 240 frames 对应 5ms。它只说明这个 buffer 覆盖多少音频，不代表端到端输出延迟就是 5ms。真实路径还可能包含：

```text
App 已排队数据
+ client/server 共享队列
+ mixer 周期
+ HAL / driver 队列
+ DSP 算法延迟
+ Codec / 无线传输缓冲
+ 调度抖动
```

“双缓冲所以乘 2”也不是通用公式。不同 output profile、路由、HAL、DSP 和设备会形成不同深度的队列，必须测实际路径。

### 1.2 不要拿机型经验值冒充平台保证

Android 没有公共 API 能返回任意路由的完整端到端延迟。可用的 feature 只表达设备声明的能力：

- `android.hardware.audio.low_latency`：声明连续输出延迟不高于 45ms。
- `android.hardware.audio.pro`：声明连续往返延迟不高于 20ms，并以前一项为前提。

它们是兼容性能力声明，不是对当前蓝牙耳机、当前 effects 配置或当前系统负载的实时测量。专业音频 App 仍应在目标设备和目标路由上做 loopback 测试。

```kotlin
val pm = context.packageManager
val lowLatency = pm.hasSystemFeature(
    PackageManager.FEATURE_AUDIO_LOW_LATENCY
)
val proAudio = pm.hasSystemFeature(
    PackageManager.FEATURE_AUDIO_PRO
)
```

## 2. Android 音频架构：控制面与数据面

先把“建流和选路”与“持续搬运 PCM”分开。

```text
控制面
App
  └─ AudioTrack / AudioRecord / AAudio / Oboe
       ├─ AudioPolicyService：选设备、output/input profile 与 flags
       ├─ AudioFlinger：创建对应 playback/record thread 与 track
       └─ Audio HAL：打开 stream、配置 route、buffer 与 capability

数据面（典型 PCM legacy path）
App buffer
  └─ client/server shared memory
       └─ AudioFlinger mixer/ record thread
            └─ Audio HAL
                 └─ driver / DSP / Codec / transducer
```

Binder 主要负责建流、状态、路由、参数和控制操作；高频 PCM 数据通常通过共享内存队列传输。把整条链描述成“每个音频 buffer 都走一次 Binder 序列化”并不准确。

### 2.1 AudioPolicyService 决定“用哪条路”

策略侧根据 `AudioAttributes`、设备连接状态、产品音频策略和可用 profile，选择输出或输入。它会影响：

- 扬声器、USB、蓝牙、HDMI 等目标设备。
- primary、fast、deep-buffer、direct、offload、MMAP 等 output/input profile。
- usage 对应的音量组和路由策略。
- 设备切换时重新打开或迁移流。

路由切换常伴随 stream 重配、旧 endpoint 关闭和新 endpoint 启动，因此可能出现短暂静音或 discontinuity。分析切换问题时，必须把“切换前”和“切换后”当作两条不同路径。

### 2.2 AudioFlinger 决定“这条 track 怎么跑”

AudioFlinger 运行在 `audioserver` 中。Android 7 起，音频服务已从原来的 `mediaserver` 进程拆出；不能写成 Android 8 才分离。

按输出类型，AudioFlinger 会使用不同线程或 endpoint：

- `MixerThread`：通用 PCM 混音。
- `FastMixer`：与某个 mixer output 关联的短周期快速混音线程。
- `DirectOutputThread` / `OffloadThread`：绕过通用软件 mixer 的 direct 或 offload 输出。
- `MmapPlaybackThread`：MMAP 输出的服务端管理路径。
- `RecordThread`、`FastCapture`、`MmapCaptureThread`：输入侧对应路径。

AudioFlinger 负责创建 track、维护共享缓冲区状态、混音或转交数据、与 HAL 交互，并记录 underrun 等状态。AudioPolicyService 做出的选路决定与 AudioFlinger 的 track 接纳条件共同决定最终路径。

### 2.3 HAL 不能只写成“AIDL”

Android 14 起，官方鼓励厂商从 HIDL Audio HAL 迁移到 AIDL；framework 仍同时支持两者。AIDL Core HAL 的 `IConfig` 承接一部分原先来自 HIDL XML 的系统级配置。

Android 16 扩展了 AIDL Audio HAL 对 Configurable Audio Policy（CAP）的支持，但这不等于所有运行 Android 16/17 的产品都已强制完成迁移。看具体设备时应确认：

- vendor 使用 AIDL 还是 HIDL Audio HAL。
- 策略来自 AIDL `IConfig`、XML，还是兼容转换路径。
- product audio policy 中实际声明了哪些 mix ports、routes 和 flags。

## 3. 四类输出路径不要混在一起

| 路径 | 常见 payload | 主要目标 | 关键约束 |
| --- | --- | --- | --- |
| Normal Mixer | PCM | 功能完整、兼容性 | 可重采样、混音、挂 effects，周期与队列通常更深 |
| Fast Mixer | PCM | 降低交互式输出延迟 | 线性 PCM、硬件采样率、可接受声道布局、FastMixer/slot/effect 条件 |
| AAudio MMAP | PCM | 降低输入、输出或往返延迟 | HAL/driver/profile 必须支持；shared/exclusive 语义不同 |
| Direct / Offload | 压缩音频或设备支持的 direct 格式 | 降低软件处理与长播放功耗，或保持特殊格式 | 设备能力、format、attributes 和独占资源决定是否可用 |

低延迟和低功耗是两套目标。MMAP / Fast 为交互式音频缩短排队；offload 允许硬件队列承接更多数据，让 CPU 与 framework 数据管道休眠更久。不能因为两者都“绕过了部分普通 mixer 工作”就把它们视为同一路径。

## 4. FastMixer：请求只是 hint，以接纳结果为准

Android 4.1 引入 FastMixer。官方设计文档给出的推荐周期是 2–3ms；如果调度稳定性需要，也可用约 5ms。这个数值是设计建议，不是所有 Android 17 设备的固定周期。

FastMixer 保留：

- Normal Mixer 的 submix。
- client fast tracks 的混音。
- 每条 track 的衰减。

它主要省去每条 fast track 的重采样、per-track effects 和 per-mix effects，但仍会执行混音。Normal Mixer 先把普通 tracks 混成 submix，再通过 index 0 送给 FastMixer；FastMixer 将其与 client fast tracks 合并后写向 HAL。

### 4.1 Android 17 源码里的接纳条件

`android-17.0.0_r1` 的 `PlaybackThread::createTrack_l()` 明确写着：

```cpp
// client expresses a preference for FAST, but we get the final say
if (*flags & AUDIO_OUTPUT_FLAG_FAST) {
    if (audio_is_linear_pcm(format)
            && /* channel conversion is acceptable */
            sampleRate == mSampleRate
            && hasFastMixer()
            && mFastTrackAvailMask != 0) {
        // 再检查 effect compatibility
    } else {
        *flags &= ~AUDIO_OUTPUT_FLAG_FAST;
    }
}
```

因此 `PERFORMANCE_MODE_LOW_LATENCY`、`AAUDIO_PERFORMANCE_MODE_LOW_LATENCY` 或 `AUDIO_OUTPUT_FLAG_FAST` 都只是请求。最终是否成为 fast track，要同时满足：

1. AudioPolicy 选出的 output 允许 low-latency / fast 路径。
2. 数据是 linear PCM。
3. sample rate 等于当前 output 的硬件采样率。
4. channel mask 不需要昂贵的 downmix。
5. 这个 mixer output 有关联的 FastMixer。
6. fast track slot 仍有空位。
7. session、output stage 或 device 上的 effect chain 不会移除 FAST flag。

“frame count 不匹配就一定拒绝 FAST”也是一种误写。Android 17 对流式 fast track 会把 frame count 至少抬到 `mFrameCount * fast_track_multiplier`；它会改变实际缓冲配置，但不是上述第一层硬拒绝条件。打开 track 后应读取实际配置，不能假定 builder 请求原样生效。

### 4.2 默认为什么最多看到 7 条 client fast tracks

Android 17 的 `FastMixerState`：

```cpp
static constexpr unsigned kMinFastTracks = 2;
static constexpr unsigned kMaxFastTracks = 32;
static constexpr unsigned kDefaultFastTracks = 8;
```

`PlaybackThread` 把 index 0 留给 Normal Mixer submix，所以默认配置下可供 client 使用的是 7 个 slot。厂商可以用只读属性 `ro.audio.max_fast_tracks` 在 2–32 之间配置总数。结论应写成：

- AOSP 默认总数 8，client 默认最多 7。
- 设备可能覆盖这个值。
- slot 用完后，新请求会降级；不能只凭 API 参数判断。

### 4.3 FastMixer 的实时调度解决什么

FastMixer 使用提升后的 `SCHED_FIFO` 优先级，目标是减少唤醒抖动。它仍然会在 HAL `write()` 处等待，不能据此认为它永远不会阻塞。

client fast track 的供数线程也很关键。Android 17 在接纳 fast track 且拿到 client tid 后，会请求 ActivityManager 为该线程配置音频优先级；这个请求仍可能失败。FastMixer 准时醒来但 client 没有按时生产数据，照样会 underrun。

## 5. AAudio、MMAP 与 Oboe

### 5.1 AAudio 是 API，不等于 MMAP

AAudio 从 Android 8.0 / API 26 提供。它是面向高性能音频的 C API，但同一套 API 可以落到不同数据路径：

- 设备支持并成功打开 MMAP：走 MMAP。
- MMAP 不可用或 AUTO 模式打开失败：回退到 legacy AudioFlinger 路径。

因此“使用 AAudio”不能直接推出“已经绕过 AudioFlinger mixer”。Android 16 / API 36 起，可以用公开 NDK API 直接核对：

```cpp
bool mmapUsed = AAudioStream_isMMapUsed(stream);
```

较早平台上要结合设备属性、AAudio 日志和 `dumpsys audio` / `dumpsys media.audio_flinger` 判断。

### 5.2 low-latency builder 要留出协商空间

最低延迟通常需要 `LOW_LATENCY` 与 data callback：

```cpp
AAudioStreamBuilder* builder = nullptr;
AAudio_createStreamBuilder(&builder);

AAudioStreamBuilder_setDirection(
        builder, AAUDIO_DIRECTION_OUTPUT);
AAudioStreamBuilder_setPerformanceMode(
        builder, AAUDIO_PERFORMANCE_MODE_LOW_LATENCY);
AAudioStreamBuilder_setSharingMode(
        builder, AAUDIO_SHARING_MODE_EXCLUSIVE);
AAudioStreamBuilder_setDataCallback(
        builder, DataCallback, userData);

AAudioStream* stream = nullptr;
aaudio_result_t result =
        AAudioStreamBuilder_openStream(builder, &stream);
AAudioStreamBuilder_delete(builder);
// 继续使用 stream 前必须检查 result == AAUDIO_OK。
```

`EXCLUSIVE` 只是请求：endpoint 已被占用或设备不支持时，系统可能给出 shared stream。除业务必须固定的字段外，可让 sample rate、format、channel count 使用 `AAUDIO_UNSPECIFIED`，打开后读取实际值，再让业务适配：

```cpp
int32_t sampleRate = AAudioStream_getSampleRate(stream);
int32_t channelCount = AAudioStream_getChannelCount(stream);
aaudio_format_t format = AAudioStream_getFormat(stream);
aaudio_sharing_mode_t sharing =
        AAudioStream_getSharingMode(stream);
aaudio_performance_mode_t performance =
        AAudioStream_getPerformanceMode(stream);
```

“请求成功”与“拿到预期路径”是两件事。日志和性能报告必须记录打开后的实际配置。

### 5.3 MMAP 缩短数据面，不删除控制面

Android 8.1 扩展了 AAudio MMAP。设备需要在 Audio HAL 和 driver 中声明并实现 MMAP/NOIRQ 能力，还要提供对应的 audio policy profile。

- **EXCLUSIVE**：App 可写入与 ALSA driver 共享的 memory-mapped buffer，绕过普通软件 mixer；延迟最低，但 endpoint 更容易因路由变化或资源竞争断开。
- **SHARED**：多个流共享 endpoint，由系统侧负责混合与管理；它不等于 App 独占硬件 buffer。

无论哪种模式，建流、权限、路由、状态切换、timestamp、xrun 和错误恢复仍要通过 AAudio service、AudioFlinger/AudioPolicy 与 HAL 的控制路径。把 MMAP 画成“App 直接打开 `/dev/snd/*`，audioserver 完全不参与”是错误模型。

AAudio 的 MMAP 策略通常允许 AUTO 回退。只有在专用验证环境里才适合强制 MMAP 并禁止 fallback；面向用户的代码要能处理 legacy path。

### 5.4 Oboe 解决跨版本 API 差异，不承诺固定选路顺序

Oboe 是 Google 的 C++ 封装：

- 平台可用时调用 AAudio。
- AAudio 不可用时回退 OpenSL ES。
- 统一 stream builder、callback、error recovery 和一部分设备兼容处理。

不能把 Oboe 简化成固定的“MMAP EXCLUSIVE → MMAP SHARED → FAST → Normal”决策表。最终路径仍受 API level、builder 参数、设备 profile、endpoint 占用和厂商实现影响。

Oboe 的工程价值在于减少跨版本分支，并提供 `getAudioApi()`、`getSharingMode()`、`getPerformanceMode()` 等结果查询。它不会让不支持 MMAP 的 HAL 凭空获得 MMAP，也不会替 App 修复 callback 中的锁等待。

## 6. buffer、callback 与 xrun

### 6.1 区分 capacity、size 和 burst

AAudio 中三个概念容易混淆：

- **buffer capacity**：这条 stream 最多可容纳多少 frames。
- **buffer size**：当前填充/阻塞阈值，可在 capacity 内调节。
- **frames per burst**：设备每个硬件 burst 处理的 frames，由系统与设备决定。

低延迟输出通常让 buffer size 保持为 burst 的整数倍。太大增加排队，太小则在一次调度延迟后立即欠载。常用调优方法是：

1. 从能稳定播放的大小开始。
2. 以一个 burst 为单位减小。
3. 观察 `AAudioStream_getXRunCount()`。
4. 一旦 xrun 增长，回退一到数个 burst，并在真实负载、热机和后台干扰下复测。

对输入流，官方文档不建议照搬这套“逐步增大 size 防 underrun”的输出调法；输入端会尽快搬运数据，App 更应关注读取是否及时以及 overrun。

### 6.2 callback 线程不能执行可能阻塞的操作

AAudio/Oboe 的 data callback 运行在高优先级线程上。callback 内应避免：

- `malloc` / `new` 和不可控的对象构造。
- 文件、网络或 Binder I/O。
- mutex、condition variable、sleep。
- 停止、关闭当前 stream。
- 在触发 callback 的同一 stream 上再次调用 `read()` / `write()`。
- 日志洪泛和复杂 trace 字符串拼接。

更稳的结构是：

```text
普通 worker
  └─ 解码 / 网络 / 文件 / 模型计算
       └─ lock-free ring buffer
            └─ audio callback：只取固定数量 frames + 轻量 DSP
```

“无锁”也不等于安全。生产者和消费者必须定义清楚容量、读写索引、内存序、欠载填零策略和 stream 关闭时序。

### 6.3 输入和输出时钟不保证同步

即便两边都报告 48kHz，capture clock 与 playback clock 也可能来自不同晶振，实际速率略有差异。长时间 loopback 时，固定大小 FIFO 会逐渐积满或耗空。

实时通话、KTV 和乐器处理需要：

- 用 timestamp 估计输入/输出 frame position。
- 监控 ring buffer 水位。
- 用异步采样率转换或细粒度补偿吸收 clock drift。
- 把算法固有延迟与系统排队延迟分开记录。

只把输入 callback 的 buffer 原样塞给输出 callback，短测可能正常，长测仍会出现周期性 xrun。

## 7. Android 17 / API 37 音频边界

### 7.1 后台音频 hardening

Android 17 对后台播放、audio focus 请求、音量与铃声修改施加生命周期限制。

对所有运行在 Android 17 上的 App：

- 有可见 Activity；或
- 正在运行非 `SHORT_SERVICE` 类型的前台服务。

目标 targetSdk 37+ 的后台 App 还要满足更严格条件：

- 前台服务具有 while-in-use（WIU）能力；或
- App 获得 exact alarm 权限，且操作的是 `USAGE_ALARM` stream。

不满足时：

- 播放和音量修改通常静默失败。
- `requestAudioFocus()` 返回 `AUDIOFOCUS_REQUEST_FAILED`。

这不是“AudioFlinger 被系统调度器降频”的性能问题。更常见的证据是 App 供数、write 返回错误、callback 不再推进或 focus 请求失败。

```bash
# 强制对所有 App 启用完整限制；WIU 和 alarm 豁免也被收紧
adb shell cmd audio set-enable-hardening enable

# 在完整限制基础上启用 loud failure
adb shell cmd audio set-enable-hardening throw

# 关闭限制，用于 A/B 对照
adb shell cmd audio set-enable-hardening disable

adb logcat -s AudioHardening
adb shell dumpsys audio
```

`throw` 模式下，volume/focus 交互可抛出 `IllegalStateException`；显式播放 write 会持续返回错误，某些没有显式 write 的播放模式可能直接让 App 崩溃。测试模式比默认发布行为更严格，报告里必须写明使用了哪个开关。

### 7.2 AAudio Power Saving Offloaded：Android 16 引入，Android 17 继续扩展

`AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 从 API 36 提供。Android 17 的 `AAudio.h` 对它的定义是：

- 只支持 output。
- 走 offloaded audio path。
- 可在短时间内向 hardware buffer 写入数秒数据。
- framework data pipe 随后可暂停，CPU 获得更长 sleep 时间。

它服务于长音频省电，不服务于交互式低延迟，也不能与 `LOW_LATENCY` 同时成立。成功打开后仍应读取实际 performance mode，并通过 dumpsys 确认 output 类型；“offloaded”不能自动证明具体 DSP 型号或硬件解码实现。

Android 17 / API 37 又为 AAudio offload 增加 `AAudio_getFlushFromFrameSupport()` 和 `AAudioStream_flushFromFrame()` 一类按 frame 位置刷新能力。使用前要用完整 builder 查询 capability。

### 7.3 `AudioTrack.flushWrittenFramesFromPosition()`

API 37 的 Java `AudioTrack` 增加按 frame 位置丢弃已写数据的能力，只允许用于：

```java
new AudioTrack.Builder()
        .setOffloadedPlayback(true)
        // format / attributes / buffer...
        .build();
```

创建 track 前先查询：

```java
int support =
        AudioTrack.getFlushWrittenFramesFromPositionSupport(
                format, attributes);
```

支持后仍要处理两种精度：

- `FLUSH_FROM_ACCURACY_BEST_EFFORT`：尽量从不早于请求位置的可实现位置刷新，并返回实际位置。
- `FLUSH_FROM_ACCURACY_EXACT`：不能精确满足时不得做近似刷新，调用方要处理失败结果。

调用期间不能并发 write；成功后如果活动 stream 剩余数据很少，应及时续写，避免 underrun。它解决 offload 队列中的 seek/ partial flush，不是普通 PCM AudioTrack 的通用 seek API。

### 7.4 codec provenance 不是“codec 实现名”

API 37 的 `AudioTrack.Builder.setCodecProvenance()` 接收 `audio/...` MIME media type，例如 `MediaFormat.MIMETYPE_AUDIO_EAC3_JOC`。它告诉 framework /HAL：送进 AudioTrack 的数据源自哪种 codec，尤其当当前 track format 与原始 codec 不同时，可辅助选择空间音频 renderer。

`getCodecProvenance()` 返回的是配置时保存的媒体类型；未设置时返回空字符串。它不返回 Codec2 component 名、厂商模块名，也不能证明软件解码、硬件解码或 offload 路径。

### 7.5 Assistant 独立音量

Android 17 为 `USAGE_ASSISTANT` 增加独立的 Assistant volume stream，使 Assistant 音量与 media 音量分离。具有相应权限/角色的 Assistant App 可使用 `MODE_ASSISTANT_CONVERSATION` 向系统表明活动对话，从而改善无活动播放或蓝牙外设场景下的音量控制一致性。

这是一项路由与音量产品语义变化，不代表 `USAGE_ASSISTANT` 自动获得 low-latency path。

## 8. 观测：Perfetto 不是唯一证据

### 8.1 先记录不可变条件

抓 trace 前先写下：

- build fingerprint、Android 版本、是否为 userdebug 构建。
- output/input device 与连接方式。
- App API、usage、format、sample rate、channel count。
- 请求与实际 sharing/performance mode。
- buffer capacity、size、frames per burst。
- 是否启用 effects、spatial audio、hardening 测试开关。
- 复现时设备是否切路由、熄屏、发热或有并发音频。

音频路径对路由非常敏感。没记录这些信息，两个 trace 很可能来自不同 pipeline。

### 8.2 先用 dumpsys 确认路径

```bash
adb shell dumpsys media.audio_flinger
adb shell dumpsys audio
adb shell getprop ro.audio.max_fast_tracks
```

重点核对：

- App pid/uid 对应的 track。
- output thread 类型、sample rate、format、frame count。
- track flags 中是否接受 FAST；官方调试文档也建议用 track 列中的 `F` 确认 fast track。
- fast track avail mask 和 underrun counter。
- output 是 mixer、direct、offload 还是 MMAP。
- 当前 route、device 与 active/inactive 状态。

AAudio 侧同时打印：

```text
getPerformanceMode()
getSharingMode()
getSampleRate()
getFramesPerBurst()
getBufferSizeInFrames()
getBufferCapacityInFrames()
getXRunCount()
isMMapUsed()  // API 36+
```

### 8.3 Perfetto 看调度与因果顺序

简单抓取可使用 Perfetto lightweight mode：

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/audio.perfetto-trace \
  -t 10s -b 64mb \
  -a com.example.app \
  audio sched freq idle

adb pull \
  /data/misc/perfetto-traces/audio.perfetto-trace
```

设备支持的 atrace category 会随版本和产品变化，可先运行 `adb shell atrace --list_categories`。不能假定所有 vendor audio slice 都有统一名称。

在 trace 里按这条顺序检查：

1. App callback / write 线程是否按周期运行。
2. 线程被唤醒后，是立即上 CPU，还是长时间处于 runnable。
3. callback 内是否出现锁、Binder、I/O、分配或长计算。
4. FastMixer / MixerThread / RecordThread / FastCapture 的唤醒是否稳定。
5. 路由、standby、stream start/stop 是否恰好与缺口重合。
6. CPU 频率、thermal throttling 或更高优先级 RT 线程是否改变调度窗口。

App 代码可用 `android.os.Trace` 或 `<android/trace.h>` 标记生产、callback 与消费区间，但单个 trace event 本身也有开销；不要在每个 sample 或极细循环里插桩。

### 8.4 underrun 要结合 counter，不能只搜字符串

Perfetto 不保证每次 xrun 都出现名为 `underrun` 的标准 slice。更可靠的组合是：

- AAudio `getXRunCount()` 前后差值。
- `AudioTrack.getUnderrunCount()`。
- `dumpsys media.audio_flinger` 的 track / FastMixer underrun counter。
- trace 中 App 供数间隙与 server thread 消费时点。
- 可控 build 上的 AudioFlinger 日志或 tee sink。

如果 counter 增长，同时 callback 在 deadline 前长期 runnable 未执行，应优先检查调度；callback 已按时完成但 counter 仍增长，再检查 buffer、HAL write、route 和设备侧。

### 8.5 声学延迟需要 loopback

Perfetto 能解释软件时序，却看不到扬声器振膜何时发声，也看不到麦克风声学信号何时到达。端到端往返延迟应使用：

- CTS Verifier/OboeTester 等 loopback 测试。
- 支持的物理 loopback dongle 或受控声学回路。
- 明确的输入/输出 route 与关闭信号处理的测试配置。

报告至少给出 median、P95、样本数、route 和测试方法。单个最佳值不能代表稳定延迟。

## 9. 常见故障的证据链

| 现象 | 先查 | 进一步验证 |
| --- | --- | --- |
| 点击后很久才发声 | warmup、queued frames、实际 output path | 首次与稳态分开测；检查 standby/start 与 buffer size |
| 持续延迟大但无杂音 | Normal/deep-buffer/offload、重采样、effects | 用 dumpsys 核对 flags/rate/output thread |
| 间歇爆音或断续 | xrun counter、callback deadline | 用 Perfetto 检查可运行延迟、锁、I/O、频率 |
| 同时录放越久越不稳 | input/output timestamp、FIFO 水位 | 检查 clock drift 与异步重采样 |
| LOW_LATENCY 请求无效 | 打开后的 mode、rate、sharing、FAST flag | 检查槽位、音效链、配置和 slot、effect chain、profile、MMAP fallback |
| 切耳机时短暂静音 | route/open/close 时序 | `dumpsys audio` + AudioPolicy/AudioFlinger trace |
| Android 17 后台突然无声 | App 生命周期、FGS/WIU、write/focus 结果 | `AudioHardening` 日志和强制测试开关 |

## 10. 蓝牙音频：不要按 codec 名称给固定延迟

蓝牙路径会增加编码、packetization、无线调度、抖动缓冲、耳机解码和本地 DSP。SBC、AAC、aptX、LDAC、LC3 只是其中一部分变量；同一 codec 在不同 buffer 配置、耳机固件、链路质量和模式下也会有明显差异。

因此不应写成：

```text
LDAC 固定 30–50ms
aptX 固定 50–80ms
```

这类数值既不能代表 Android 平台，也容易把音质模式和低延迟模式混为一谈。更可靠的做法是：

1. 固定手机、耳机、codec、profile 与场景模式。
2. 记录实际 Bluetooth route 和协商结果。
3. 用高速摄像、外部采集或声学 loopback 测试测量端到端延迟。
4. 分开报告 median、尾延迟与断续率。

对节奏游戏或虚拟乐器，内置扬声器、有线/USB 路径通常更容易获得稳定的交互延迟。必须支持蓝牙时，产品应做校准或按实测提供 latency compensation；FastMixer 或 MMAP 在手机侧成功，并不能消除无线和耳机端缓冲。

## 11. API 选择

| 场景 | 优先考虑 | 关键验证 |
| --- | --- | --- |
| 游戏、合成器、实时音效 | Oboe/AAudio callback + LOW_LATENCY | 实际 rate/mode/sharing/MMAP、xrun、触摸到声音实测 |
| DAW、吉他效果、KTV | Oboe/AAudio input + output | round-trip loopback、clock drift、FastCapture/MMAP input |
| 视频会议/VoIP | Telecom/通信栈配合 AAudio/Oboe | route、AEC/NS 算法延迟、输入输出同步、FGS |
| 长音乐/播客 | Media3/ExoPlayer，设备支持时 offload | gapless/seek、route、功耗、offload capability |
| 短音效 | 预加载的 SoundPool 或低延迟音频引擎 | 首次预热与稳态分开测 |
| Assistant | 正确的 `USAGE_ASSISTANT` 与 Assistant 角色能力 | Android 17 独立音量语义、focus 与后台生命周期 |

表中没有写死“必须小于 10ms/20ms”，因为目标取决于设备能力和产品交互。API 负责提出请求，测量才能证明结果。

## 12. 版本演进

| 版本 | 变化 | 分析重点 |
| --- | --- | --- |
| Android 4.1 | 引入 FastMixer | 为低延迟 PCM 输出建立 fast path |
| Android 7 | AudioFlinger / AudioPolicyService 所在音频服务从 mediaserver 拆到 audioserver | 进程与权限边界变化 |
| Android 8.0（API 26） | 引入 AAudio | 原生高性能音频 C API |
| Android 8.1（API 27） | AAudio 增加 MMAP/NOIRQ 低延迟路径 | 需要 HAL、driver 和 policy profile 支持 |
| Android 14（API 34） | 官方鼓励新实现迁移 AIDL Audio HAL；framework 兼容 AIDL/HIDL | 不能仅凭系统版本断言 HAL 类型 |
| Android 16（API 36） | AIDL HAL 扩展 CAP；AAudio 增加 Power Saving Offloaded；公开 `isMMapUsed()` | 省电 offload 与低延迟 MMAP 分开验证 |
| Android 17（API 37） | 后台音频 hardening；AudioTrack/AAudio partial flush；codec provenance；Assistant 独立音量 | 当前源码锚定 `android-17.0.0_r1` |

## 13. 常见误区

### “用了 AAudio 就一定是 MMAP”

不成立。AAudio 可以回退到旧 legacy AudioFlinger path。API 36+ 用 `AAudioStream_isMMapUsed()` 核对。

### “请求 LOW_LATENCY 就一定是 fast track”

不成立。它只是 hint；sample rate、channel、FastMixer、slot 和 effects 都会影响接纳。

### “FastMixer 不做 mixing”

不成立。它混合 Normal Mixer submix 与 client fast tracks，只是功能比 Normal Mixer 精简。

### “buffer 是 5ms，所以输出延迟就是 5ms”

不成立。这个数只描述一个 buffer 的音频时长，不包含其他队列、DSP、硬件和调度。

### “EXCLUSIVE 意味着系统其他声音都消失”

不成立。它独占的是一个 endpoint；系统声音可能通过另一 endpoint 继续播放。请求也可能被降级为 SHARED。

### “xrun 一定是 buffer 太小”

不成立。callback 锁等待、线程没及时获得 CPU、HAL 阻塞、路由切换和 clock drift 都能造成 xrun。增大 buffer 只是以延迟换容错。

### “`getCodecProvenance()` 能判断硬解或软解”

不成立。它返回配置的编解码器 codec MIME media type，不是 codec component 或执行路径探针。

### “Perfetto 能直接量出扬声器发声时间”

不成立。Perfetto 解释软件时序；声学端到端延迟要做 loopback。

## 14. 排查清单

1. 固定设备、build、route 和测试内容。
2. 区分预热、稳态输出、输入与往返延迟。
3. 记录 builder 请求与打开后的实际 stream 参数。
4. 用 dumpsys 确认 Normal/ Fast / MMAP / Offload 路径。
5. 同时记录 App xrun counter 与 AudioFlinger underrun。
6. 用 Perfetto 对齐 callback、server thread、调度、频率和路由事件。
7. callback 内移除分配、锁、I/O 和无界计算。
8. 以 burst 为单位调 buffer，并在真实压力下复测尾延迟。
9. 输入输出同时运行时处理时钟漂移。
10. Android 17 后台问题先查 FGS/WIU 与 `AudioHardening`，不要误判为 mixer 性能退化。
11. 最终用 loopback 或外部测量验证端到端指标。

## 参考资料

- [AOSP：Audio architecture](https://source.android.com/docs/core/audio)
- [AOSP：Design for reduced latency](https://source.android.com/docs/core/audio/latency/design)
- [AOSP：Audio latency measurements](https://source.android.com/docs/core/audio/latency/measurements)
- [AOSP：AAudio and MMAP](https://source.android.com/docs/core/audio/aaudio)
- [AOSP：Audio debugging](https://source.android.com/docs/core/audio/debugging)
- [AOSP：AIDL and HIDL Audio HAL comparison](https://source.android.com/docs/core/audio/aidl-hidl-comp)
- [Android NDK：Audio latency](https://developer.android.com/ndk/guides/audio/audio-latency)
- [Android NDK：AAudio](https://developer.android.com/ndk/guides/audio/aaudio/aaudio)
- [Android 17：Background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Android 17：Features and APIs](https://developer.android.com/about/versions/17/features)
- [Android API：AudioTrack](https://developer.android.com/reference/android/media/AudioTrack)
- [Oboe：Full Guide](https://github.com/google/oboe/blob/main/docs/FullGuide.md)
- [Perfetto CLI reference](https://perfetto.dev/docs/reference/perfetto-cli)
- [AOSP：Threads.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/Threads.cpp)
- [AOSP：FastMixerState.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/fastpath/FastMixerState.cpp)
- [AOSP：FastMixerState.h（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/fastpath/FastMixerState.h)
- [AOSP：AAudio.h（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/libaaudio/include/aaudio/AAudio.h)
- [AOSP：AudioTrack.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/media/java/android/media/AudioTrack.java)
