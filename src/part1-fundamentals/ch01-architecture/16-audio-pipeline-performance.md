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
last_verified: "2026-04-22"
last_verified_against: "AOSP android-16.0.0_r1 + developer.android.com"
confidence: medium
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-27"
last_task6_review_log: "logs/review/2026-05-27-15-review.md"
last_task6_at: "2026-05-27T15:08:00+08:00"
last_task6_audit: "2026-05-19"
task6_result: pass-light-edit
task9_result: auto-fixed
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
  - type: aosp
    path: "frameworks/av/services/audioflinger/Threads.cpp (android-16.0.0_r1)"
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-05-27T14:50:00+08:00"
task9_reviewed_date: "2026-05-27"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-27T15:22:00+08:00"
section: "1.16"
task9_review_notes: "2026-05-24 08:20 Task9 idle audit: needs-rework；P0: FastMixer.cpp 与 AAudio service AOSP 路径错误，已写入 metadata/queue.json。 | 2026-05-24 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 1；Android 16 AIDL CAP/IConfig 强制口径仍过硬，需收窄为 AIDL HAL fully supports CAP、legacy/HIDL 兼容与 XML 转 AIDL reference implementation；另有 AAudio offloaded 与 Android 17 WIU FGS 条件混写的 P2 建议。 | 2026-05-25 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0；Android 17 background audio hardening 的 visible Activity/非 SHORT_SERVICE FGS、target API 37 WIU、USAGE_ALARM exact alarm 豁免条件与 AAudio offloaded playback 前提混写，已写入 metadata/queue.json。 | 2026-05-27 15:22 Task9 auto-fix：收窄 AAudio Power Saving Offloaded 与 DSP 解码表述，避免把省电 output path 写成无条件 DSP 解码；回到 Task6 复审。"
review_type: "task6-writing-quality-review"
last_task9_audit: "2026-05-24"
last_task9_review_log: "logs/deep-review/2026-05-27-15-deep-review.md"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-25 Task6：revisiting 写作质检通过；未新增 L1/L2 小修；沿用 Task9 2026-05-25 P1 技术回炉，章节保持 task2b_pending。 | 2026-05-27 15:08 Task6：revisiting 写作质检通过；未新增 L1/L2 正文问题；Task2B 修复后的 Android 17 后台音频与 AAudio offloaded 边界已进入正文；Task9 result 仍为 needs-rework，送 Task9 复审。"
task2b_notes: "2026-05-27 Task2B fallback：修复 Task9 2026-05-25 P1；拆开 Android 17 后台音频 hardening 生命周期条件与 AAudio Power Saving Offloaded 输出路径，补 targetSdk 37+ WIU / USAGE_ALARM 豁免和 cmd audio 强制测试语义。"
last_task9_autofix_at: "2026-05-27"
---

# 1.16 Audio Pipeline 延迟与性能

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Audio Pipeline 的整体数据流，以及 AudioFlinger / AudioPolicyService 的角色分工
- 🔹 延迟分解：输出延迟、往返延迟与缓冲区大小
- 🔹 FAST Mixer 的工作机制、进入条件与线程调度
- 🔹 AAudio、MMAP 与 Oboe 的低延迟路径差异
- 🔹 Audio Pipeline 在 Perfetto 中的关键 Track、Slice 与常见问题特征

### 扩展（可选深入）

- 🔸 Android 17 音频行为变更
- 🔸 蓝牙音频延迟与游戏音频实践

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 扩展内容可以结合素材深挖，但不要替代主线叙述。
> 若某个延迟数字或设备能力具有明显平台差异，应优先标注 `[待验证]`，不要写成无条件结论。
<!-- outline-end -->

## 为什么需要了解 Audio Pipeline

讨论 Android 性能时，注意力通常集中在渲染管线上——帧率、掉帧、VSync。但用户的感知不止来自视觉。点击一个钢琴 App 的琴键，如果声音在手指触摸后 100ms 才响起，用户会觉得这台设备「卡了」。在视频会议中，200ms 的往返延迟会让对话变得不自然。游戏里 50ms 的音效延迟，足以让打击感明显变弱。

音频延迟和渲染延迟在技术结构上有一个有趣的对称关系：SurfaceFlinger 负责画面的合成与显示，AudioFlinger 负责声音的混音与输出。两者都是 Android 框架层中承上启下的核心服务，都通过 HAL 与硬件交互，都对延迟极其敏感。理解其中之一的架构后，再看另一个会更容易。

人类对音频延迟的感知阈值比视觉更严苛：超过 20ms 的往返延迟就能被训练过的耳朵察觉，专业音乐制作要求低于 10ms。Android 设备的音频延迟，也从早期的 100ms 以上逐步压到如今 Pixel 设备的 10ms 以下。

了解 Audio Pipeline 的内部机制后，后续分析音频性能瓶颈时，可以在 Perfetto 中识别声音卡顿或延迟的来源，并为不同场景选择合适的音频 API。

## Audio Pipeline 架构全景

Android 音频管线的整体数据流可以概括为：

```
App (AudioTrack/AAudio)
    ↓  write()
AudioFlinger (AudioServer)
    ↓  混音 + 重采样
Audio HAL（AIDL/HIDL，取决于 Android 版本与平台实现）
    ↓  ALSA/TinyALSA
DSP / Codec
    ↓
Speaker / Headphone
```

这个管线看起来只有几层，但每一层都有影响延迟的关键设计决策。

### AudioFlinger 的角色

AudioFlinger 是 Android 音频子系统的核心服务，运行在 `audioserver` 进程中（自 Android 8.0 起从 `mediaserver` 分离）。Android 16 起 AIDL Audio HAL 完整支持 CAP（Core Audio Policy），AIDL 实现可通过 `IConfig.getEngineConfig()` 等接口提供音频策略配置，音频策略得以随 APEX 更新独立演进。HIDL/legacy 产品仍有兼容路径：厂商可继续使用 XML 配置文件并通过 AIDL reference implementation 转换为 AIDL 数据。是否强制使用 `IConfig.aidl` 取决于具体发布要求和设备迁移状态，不能一律写成所有 Android 16 新设备必须。它的职责包括：

1. **接收来自所有 App 的音频数据**——通过共享内存（SharedMemory）和 Binder IPC
2. **混音（Mixing）**——将多个 App 的音频流合并为一路输出
3. **重采样（Resampling）**——当 App 的采样率与输出设备不匹配时，进行采样率转换
4. **音量控制与路由**——根据 AudioPolicyService 的决策，将音频路由到正确的输出设备
5. **将混音后的数据写入 Audio HAL**——最终由 HAL 驱动硬件输出

[已验证: AOSP android-16.0.0_r1, frameworks/av/services/audioflinger/]

### AudioPolicyService：音频路由决策

AudioFlinger 负责「怎么播放」，AudioPolicyService 负责「播放到哪里」。当 App 创建一条音频流时，AudioPolicyService 根据音频类型（stream type）、用途（usage）、设备连接状态（耳机、蓝牙、扬声器）做出路由决策。

路由决策本身不直接产生延迟，但路由切换会。当用户插入耳机时，AudioPolicyService 会重新路由音频流，这个过程涉及关闭旧的输出流、打开新的输出流、重新协商缓冲区大小——在 Perfetto 中表现为一段短暂的音频中断。

## 延迟分解：从 App 到扬声器

理解音频延迟的来源，要把整个路径拆开看。

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

### 缓冲区大小：延迟的主要决定因素

音频延迟的基础公式是：

```
单次缓冲延迟 = buffer_size / sample_rate
```

一个 480 帧、48000Hz 的缓冲区，延迟就是 480/48000 = 10ms。但音频系统通常使用双缓冲甚至多缓冲，所以实际延迟是缓冲区大小的 2-3 倍。

在 Normal Mixer 路径下，AudioFlinger 的默认缓冲区大小由 HAL 层决定，通常在 480-960 帧之间（10-20ms）。这个值在不同设备上差异很大——同一台设备上扬声器输出和蓝牙输出的缓冲区大小也不同。

## FAST Mixer：低延迟路径

Android 4.1（Project Butter）引入了 FAST Mixer，这是 Android 音频低延迟的关键机制。

### Normal Mixer vs FAST Mixer

普通应用默认走 Normal Mixer 路径。多个音频流在这里完成混音、重采样、音量曲线和效果处理，然后再写入 HAL。它的处理周期通常在 20ms 左右，因为每个周期里要做的事情很多。

FAST Mixer 是绑定在某个 output 上的低延迟混音线程。AudioFlinger 会先把普通 tracks 交给 Normal Mixer 混成一路 sub-mix，再由 FAST Mixer 把这路 sub-mix 和最多 7 条 client fast tracks 一起送进 HAL 缓冲区。

FAST Mixer 省掉的是每条 fast track 的 sample rate conversion、per-track effects 和其他高开销处理，而不是把 mixing 这件事完全删掉。它保留最小必要的混音和音量衰减，把周期压到更短的 2-3ms 左右，所以低延迟播放听起来会更跟手。

[已验证: AOSP audio latency 文档与 `frameworks/av/services/audioflinger/fastpath/FastMixer.cpp` / `FastMixerState.h`]

### 进入 FAST Mixer 的条件

`PERFORMANCE_MODE_LOW_LATENCY` 或 `AAUDIO_PERFORMANCE_MODE_LOW_LATENCY` 只是“请求低延迟”，不是保证一定拿到 fast path。选路分成两步。

第一步是策略层。App 创建 `AudioTrack` 或 `AAudioStream` 时，framework 会把 usage、flags、sample rate、sharing mode 交给 AudioPolicyService / AudioPolicyManager 选 output profile。只有策略层给出的 output 带有 `AUDIO_OUTPUT_FLAG_FAST`，后面才有资格继续往 fast path 走。

第二步由 AudioFlinger 在创建 track 时完成筛选。常见的硬条件包括：这个 output 上存在 fast mixer thread；请求的 sample rate、format、channel mask 和设备 mix port 匹配；client 侧能用 callback 线程按时供数；track 的 frame count 落在 fast track 可接受的范围；fast track slot 还有空位。任何一个条件不满足，都会退回 Normal Mixer。

这里的 slot 是硬约束。android-16.0.0_r1 的 `PlaybackThread` 构造里把 `mFastTrackAvailMask` 初始化为 `((1 << FastMixerState::sMaxFastTracks) - 1) & ~1`，源码注释直接写明 index 0 预留给 normal mixer 的 submix。也就是说 FastMixer 的槽位数是固定的，应用侧实际最多同时占用 7 个 fast track；槽位打满时，新流会直接降回 normal track，即使 sample rate 和 buffer 配置都匹配。

这就是为什么同样都写着“LOW_LATENCY”，有的流能进 fast track，有的流还是普通 track。最常见的失败原因就是 44100Hz 请求落在 48000Hz 输出设备上，或者 buffer/frame count 配得太保守。

### FAST Mixer 的线程调度

FAST Mixer 运行在一个专用线程上，使用 `SCHED_FIFO` 实时调度策略（而非普通应用的 `SCHED_NORMAL`）。这个优先级设置确保了即使在系统负载较高时，音频数据的写入也能准时完成。

在 Perfetto 中，可以通过 CPU scheduling track 观察 FAST Mixer 线程的调度行为。如果发现这个线程频繁被抢占或无法及时唤醒，通常意味着系统负载过高或 CPU 频率调度策略不适合音频场景。

[图：Perfetto 中 AudioFlinger FAST Mixer 线程的 CPU scheduling slice，标注 SCHED_FIFO 优先级]

### 从创建流到选路：为什么这条流没有进入 fast path

只看输出侧，容易把 round-trip latency 讲成半截。完整路径是：`AudioTrack` / `AAudio` 输出先经 AudioPolicyService 选 output profile，再由 `AudioFlinger::createTrack()` / `PlaybackThread::createTrack_l()` 决定是 normal track、fast track、direct/offload 还是 MMAP output；输入侧 `AudioRecord` / `AAudio` input 则先经 AudioPolicyService 选 input profile，再落到 `RecordThread`，设备支持时再进一步走 `FastCapture` 或 input MMAP。

所以 round-trip latency = input path + app processing + output path。输出侧已经拿到 FAST Mixer，只能说明扬声器这半边更快；如果输入侧还停留在普通 `RecordThread`，麦克风到 App 的这一半仍然会拖慢总延迟。分析乐器、KTV、视频会议这类场景时，需要同时看 `AudioFlinger` 的 playback thread 和 `RecordThread` / `FastCapture` 的调度节奏，不能只盯着输出线程。

[图：AudioTrack/AAudio 输出选路与 AudioRecord/AAudio 输入选路示意图，标注 AudioPolicyService、PlaybackThread、FastMixer、RecordThread、FastCapture、MMAP output、input MMAP]

## AAudio 与 MMAP：低延迟数据路径

### AAudio：面向低延迟的 C API

AAudio 是 Android 8.0 引入的原生音频 C API，专为低延迟音频场景设计（游戏、音乐制作、实时音频处理）。相比传统的 OpenSL ES（已标记为废弃）和 Java 层的 AudioTrack，AAudio 提供了更底层的控制和更低的延迟。

AAudio 的核心设计原则是简洁：创建流（`AAudioStream`）、写入数据（`AAudioStream_write()`）、关闭流。没有复杂的回调层级，没有 Java 层的额外开销。

[已验证: developer.android.com/ndk/guides/audio/aaudio]

### MMAP 模式：减少数据面拷贝，控制面仍在

Android 8.1 引入了 MMAP（Memory Mapped）模式。它缩短的是数据面的搬运路径，不是把 audioserver 完全拿掉。

传统 PCM 播放通常是：

```text
数据面: App 缓冲区 → Binder / 共享内存 → AudioFlinger Mixer → HAL 缓冲区 → DSP / Codec
```

MMAP 打开后，App 仍然要先通过 AAudio / Oboe 向 audioserver 内的 AAudioService 申请 endpoint，由 service 和 HAL 协商设备、采样率、buffer 大小、timestamp 与 xrun 统计。变化主要发生在数据面：

```text
控制面: App → AAudio / Oboe → AAudioService / AudioFlinger → Audio HAL → MMAP endpoint
数据面（SHARED）: App → audioserver 侧 timing model / mixer → MMAP buffer → DSP / Codec
数据面（EXCLUSIVE）: App → MMAP buffer → DSP / Codec
```

SHARED 模式仍然保留 audioserver 侧的 timing model 和混音管理，只是把传统的多级拷贝换成 MMAP buffer。EXCLUSIVE 模式会绕过普通 mixer，让单个 App 独占 endpoint，但 stream 的打开、状态切换、设备路由和错误恢复仍然经过 service / HAL 控制通道。

EXCLUSIVE 模式下，App 仍然要持续根据 timing model 校正硬件读写位置。NOIRQ MMAP 没有共享读写计数器，audioserver 会持续把 timestamp 和 xrun 状态送回流端，App 再据此修正 `AAudioStream_getTimestamp()` 看到的硬件位置。少了这层同步，exclusive stream 很容易在 callback 节奏上漂掉，进而出现 underrun 或 overrun。

所以 `App → 驱动` 只适合描述 EXCLUSIVE 模式下的数据面，不能拿来概括整个 MMAP 机制。MMAP 的收益也不是无条件成立，设备不支持、format 不匹配、endpoint 被占用时，AAudio / Oboe 仍会回退到 FAST 或 Normal 输出。

[已验证: AAudio 文档、AOSP audio latency 文档；服务端 `frameworks/av/services/oboeservice/AAudioService.cpp`，客户端/绑定层 `frameworks/av/media/libaaudio/src/binding/` / `src/client/` / `src/core/`]

### AAudio Power Saving Offloaded 模式

Android 16 引入了 AAudio Power Saving Offloaded 模式（`AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED`），请求省电型 offloaded output path。NDK r29 的 `aaudio/AAudio.h` 描述该模式会走 offloaded audio path，可向 hardware buffer 写入数秒数据、让 framework data pipe 暂停并允许 CPU sleep。该模式面向长音频省电，不是低延迟 MMAP 的替代方案。两者不能同时生效。

这个模式本身不要求 App 持有 while-in-use（WIU）能力的前台服务。WIU 是 Android 17 后台音频硬化的生命周期条件，和 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 的省电输出路径是两组问题。使用该模式后仍要用 `AAudioStream_getPerformanceMode()`、`dumpsys audio` 和 output profile 核对最终是否进入 offloaded path。

[待验证: 最终 API 入口、最小 API level、支持格式组合、设备覆盖范围需结合 Android 16/17 API diff 与实机确认。"解码完全交给 DSP"、"功耗降低 75%" 等量化结论需要补 AOSP 版本提交或独立功耗测试条件后方可写入正文。]

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
| 后台音频卡顿 | App 侧 write/callback 停止，随后 track 在 `dumpsys audio` 中变为 inactive 或被 teardown | Android 17 后台音频硬化：无可见 Activity、无合规 FGS，或 targetSdk 37+ 未满足 WIU / `USAGE_ALARM` 豁免条件 |

[图：Perfetto 中音频 underrun 的 Trace 表现，标注缓冲区空的时间段]

## Android 17 音频性能变更

Android 17（API 37）对音频子系统引入了多项重要变更，对 App 开发和性能分析都有直接影响。

### 后台音频强化（Audio Hardening）

Android 17 对后台音频播放实施更严格的管控，影响范围包括播放写入、音频焦点和音量变更：

**受影响的主线 API**：
- 播放写入路径（以 `AudioTrack` 为代表）
- `AudioManager.requestAudioFocus()`
- 音量与铃声相关的 `AudioManager` API

这里先只讨论播放侧硬化。`AudioRecord`、Telecom 和录音权限相关行为是另一组约束，不能直接和这组后台播放限制混成一类。

**新规则**：运行在 Android 17 上的 App，如果在后台调用这些 API，需要有可见 Activity，或运行非 `SHORT_SERVICE` 类型的前台服务。targetSdk 37+ 还要满足额外条件：前台服务具备 while-in-use（WIU）能力，或者 App 已获 exact alarm 权限并且操作的是 `USAGE_ALARM` 音频流。不合规时，播放和音量变更会静默失败，`requestAudioFocus()` 返回 `AUDIOFOCUS_REQUEST_FAILED`。

[已验证: developer.android.com/about/versions/17/changes/bg-audio]

**调试方法**：

```bash
# 对所有 app 打开约束，提前做兼容性测试；该模式会强制应用 WIU 要求，并且不会放过 exact alarm + USAGE_ALARM 豁免
adb shell cmd audio set-enable-hardening enable

# 打开 loud failure：volume/focus 抛 IllegalStateException，播放 write 持续返回错误
adb shell cmd audio set-enable-hardening throw

# 临时关闭约束，做 A/B 对比
adb shell cmd audio set-enable-hardening disable

# 查看违规日志
adb logcat -s AudioHardening

# 查看详细音频状态
adb dumpsys audio
```

**对性能分析的影响**：这个变更的主体是 app 生命周期与音频 API 可用性，不是 AudioFlinger 线程被冻结。Perfetto 里更常见的现象是应用自己的写入线程、AAudio callback 或播放器工作线程先停止推数据，随后对应 track 在 `dumpsys audio` 里变成 inactive，必要时还会被 teardown。定位这类问题时，先对照 `logcat -s AudioHardening` 看是否命中后台限制，再用 `dumpsys audio` 核对 output / track 状态，再回看 trace 中的 app 写入停止时点。用 `cmd audio set-enable-hardening enable` 得到的问题要单独标注为强制测试结果，不能直接等同于默认发布行为。

### AudioTrack 新增精确 Flush 控制

Android 17 新增 `flushWrittenFramesFromPosition(long, int)`。官方 API 文档在方法详情里直接写的是“only allowed in offload mode”，所以它只适用于显式调用 `Builder.setOffloadedPlayback(true)` 创建的 offload `AudioTrack`。调用前还要先用 `getFlushWrittenFramesFromPositionSupport(AudioFormat, AudioAttributes)` 查询设备支持度；这个静态探测接口查的也是“给定 format / attributes 创建的 offload track”是否支持该能力，返回 0 就不能用。`accuracy` 参数仍然只有 `FLUSH_FROM_ACCURACY_BEST_EFFORT` 和 `FLUSH_FROM_ACCURACY_EXACT` 两档。

它适合的场景是 offload 播放中的 seek 或章节跳转：App 需要丢弃已经写进 DSP 或硬件队列、但还没播出的那部分数据，并尽量从指定 frame 重新开始。普通 PCM `AudioTrack` 不在这套语义里，不能把这个 API 当成通用 seek 工具直接套用。

[已验证: `AudioTrack` API 37 参考文档，`flushWrittenFramesFromPosition()` / `getFlushWrittenFramesFromPositionSupport()`]

### 编解码器来源查询

`getCodecProvenance()` 返回的是配置阶段确定的 codec provenance，也就是编解码器实现来源字符串，例如系统组件名或厂商 codec 名。它表达的是“这条播放流最终绑定了哪套编解码器实现”，方便 framework 或 HAL 在空间音频、渲染策略这类场景里保留来源信息；它本身不直接给出“当前一定走硬解 / 软解 / offload”这类执行路径结论。

如果要判断执行路径，是不是 offload、是不是 hardware decoder、DSP 有没有接管，应该另外看 offload 配置、`dumpsys audio`、播放器管线和设备能力。不能把 `getCodecProvenance()` 直接当成执行路径探针。

[已验证: `AudioTrack.getCodecProvenance()` API 37 文档]

### Assistant 独立音量流

Android 17 引入了 `USAGE_ASSISTANT` 专用音量流，将语音助手的音频与标准媒体流解耦。用户可以独立控制 Assistant 音量和媒体音量，不会出现「调低音乐音量后 Assistant 也听不到了」的问题。

配套 `MODE_ASSISTANT_CONVERSATION` 音频模式进一步提升音量控制的一致性。

[已验证: research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md]

### 四类 output path 放在一起看

前面已经出现 FAST、MMAP、offload 这几个词，如果不放在同一张表里，很容易把低延迟播放和省电播放写混。

| 输出类型 | 典型线程 / 组件 | 常见 payload | 目标 | 常见入口 |
|----------|-----------------|-------------|------|----------|
| Normal | `MixerThread` / `PlaybackThread` | PCM | 兼容性、通用播放 | 默认 `AudioTrack` / AAudio 输出 |
| Fast | `FastMixer` + fast track | 与设备 mix port 匹配的 PCM | 降低输出延迟 | `PERFORMANCE_MODE_LOW_LATENCY`，且 output profile / sample rate / frame count / slot 条件满足 |
| MMAP | `MmapPlaybackThread` / MMAP endpoint | PCM | 压低 round-trip latency | AAudio / Oboe 请求 MMAP shared 或 exclusive，设备需支持 |
| Direct / Offload | `DirectOutputThread` / `OffloadThread` | 以压缩音频为主，部分新平台资料还提到 offloaded PCM [待验证] | 降低 CPU 唤醒和长时播放功耗 | `AudioTrack.Builder.setOffloadedPlayback(true)`；AAudio offloaded playback 入口见下文 [待验证] |

`flushWrittenFramesFromPosition()` 和 `getCodecProvenance()` 这类 API 应放在 Direct / Offload 这一栏理解。它们服务的是 seek、codec 来源保留、power-saving playback 这类问题，不属于 MMAP low-latency 方案。

### AAudio offloaded playback 的边界

现有公开资料已经出现 AAudio offloaded playback / `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 这类能力描述，但 API level、支持格式、PCM/压缩边界和设备覆盖范围还要结合 Android 16/17 API diff 与实机确认。现阶段更稳妥的理解是：它请求的是省电型 output path，不是低延迟 MMAP；讨论它时要单独看 output profile、offload capability 和 `dumpsys audio` 中的 offload output 状态。

[待验证: AAudio offloaded playback 的最终 API 入口、最小 API level、payload 支持范围]

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
- **§5.6 功耗管理**：持续的音频播放会阻止 CPU 进入低功耗状态。AAudio Power Saving Offloaded 模式请求省电型 offloaded output path，通过减少长时播放中的 framework data pipe 活跃时间和 CPU 唤醒来降低功耗。
- **§16.5 Android 17 变更**：后台音频强化是该版本最重要的音频相关行为变更。
- **§2.6 SurfaceFlinger**：SurfaceFlinger 和 AudioFlinger 是 Android 框架层中对称的两个核心服务，理解其中一个的架构有助于学习另一个。

## 版本演进

| 版本 | 变更 | 性能影响 |
|------|------|----------|
| Android 4.1 | FAST Mixer 引入（Project Butter） | 低延迟播放第一次有了独立 fast path |
| Android 5.0 | 采样率转换与混音路径持续优化 | Normal Mixer 的稳定性继续改善 |
| Android 8.0 | AAudio API 引入 | 原生低延迟 C API |
| Android 8.1 | MMAP 模式 | 绕过部分 AudioServer 处理，延迟继续下降 |
| Android 9 | HIDL Audio HAL 仍是主流实现 | 低延迟能力仍主要取决于厂商 HAL 质量 |
| Android 12 | AIDL Audio HAL 已可用于新实现，迁移开始进入可用阶段 | 为后续模块化迁移铺路 |
| Android 14 | 平台明确鼓励迁移到 AIDL，framework 同时支持 HIDL/AIDL；Android 14 之后的新 HAL API 只继续加到 AIDL | 降低后续音频 HAL 演进分叉 |
| Android 16 | AAudio Power Saving Offloaded 模式；AIDL Audio HAL 完整支持 CAP，可通过 IConfig 提供音频策略配置 | 长音频省电播放；音频策略配置可随 APEX 独立更新；HIDL/legacy 产品仍有 XML + reference implementation 兼容路径 |
| Android 17 | 后台音频强化 + 精确 flush + codec provenance | 后台播放约束更严，播放控制更细 |

[待验证: Android 9/12 的迁移节奏在不同 SoC 上差异很大，表中描述的是平台方向，不等于所有设备在对应版本统一完成迁移]

## 常见问题与误区

**误区：所有设备都支持 FAST Mixer 和 MMAP。**

事实是：FAST Mixer 的可用性取决于 HAL 是否声明 `AUDIO_OUTPUT_FLAG_FAST`。MMAP 模式需要硬件厂商实现 Audio HAL 中的 MMAP 支持。许多中低端设备虽然运行最新的 Android 版本，但 HAL 层并未实现这些低延迟特性。Google Play 上 Oboe 团队的统计数据显示，支持低延迟路径的设备比例在逐年增长，但远未达到 100%。

**误区：Java AudioTrack 的延迟总是比 AAudio 高。**

这句话下得过满。`AudioTrack` 把 `PERFORMANCE_MODE_LOW_LATENCY` 作为低延迟请求交给策略层和 `PlaybackThread::createTrack_l()`，只有 output profile 带 `AUDIO_OUTPUT_FLAG_FAST`，并且 sample rate、frame count、fast track slot 条件都满足时，才有机会进入 fast path。条件不满足时，它仍然回到 Normal Mixer。AAudio 的优势主要在于 API 更接近 MMAP 以及新平台上的 offloaded playback 请求，不在于“Java 一定慢”。

**误区：音频延迟只与缓冲区大小有关。**

缓冲区大小是主要因素，但不是唯一因素。调度延迟（线程何时被 CPU 执行）、Binder IPC 延迟、重采样开销、HAL 层的内部缓冲策略，都会叠加到总延迟上。在系统负载较高时，即使配置了很小的缓冲区，调度延迟也可能导致实际延迟远超理论值。

## 扩展

### 🔸 蓝牙音频延迟分析

蓝牙音频增加了额外的编码和传输延迟，这使得整体延迟显著高于有线输出：

- **A2DP（SBC 编码）**：100-200ms 额外延迟。这是蓝牙音频的基本模式，延迟最高。
- **aptX**：50-80ms。高通的蓝牙编码方案，延迟优于 SBC。
- **LDAC**：30-50ms。索尼的高品质蓝牙编码，延迟在三者中最低，但功耗最高。
- **LE Audio（LC3 编码）**：日常使用延迟 80-110ms，游戏模式可降至 40ms 以下。蓝牙 5.2 引入的新一代低延迟音频协议，代表了蓝牙音频延迟的未来方向。

蓝牙音频的额外延迟来源包括：编码/解码处理时间、无线传输的协议开销、Bluetooth Audio HAL 内部的额外缓冲区。空间音频（Spatial Audio）结合头部追踪功能对延迟的要求更高——头部转动到声音位置更新的延迟需要低于 20ms 才能避免感知错位。

不同编解码器配置、耳机固件和连接状态会显著改变实际延迟，上述数值更适合作为经验范围，而不是统一结论。

### 🔸 游戏音频性能最佳实践

为游戏场景配置低延迟音频时的核心清单：

1. **使用 Oboe 库**，而非直接调用 AAudio 或 OpenSL ES。Oboe 会自动选择最优路径。
2. **设置 `PerformanceMode::LowLatency`**，同时设置 `SharingMode::Exclusive`（如果不需要混音）。
3. **匹配设备原生采样率**。预判时可读取 `AudioManager.PROPERTY_OUTPUT_SAMPLE_RATE`，打开流后再用 `AAudioStream_getSampleRate()` 或 Oboe 的 `stream->getSampleRate()` 读取实际采样率。不匹配的采样率会导致无法进入 FAST Mixer。
4. **使用回调模式**（`setCallback`）而非阻塞写入。AAudio/Oboe 的 data callback 运行在应用进程侧的高优先级音频线程中，系统会通过共享内存、timing model 与唤醒机制消费数据。相比 App 侧主动 `write()` 阻塞等待，callback 模式减少了调度延迟带来的不确定性。
5. **避免在音频回调中做重计算**。音频 callback 运行在应用进程的高优先级音频线程中，必须避免锁等待、内存分配、文件 I/O 和重计算。任何阻塞操作都会直接影响该帧的音频数据交付，造成 underrun。预分配所有需要的缓冲区，使用无锁数据结构。
6. **监控 underrun**。调用 `AAudioStream_getXRunCount()` 持续监控。如果 underrun 持续增加，说明缓冲区太小或 App 侧处理太慢——适当增大缓冲区是更务实的做法。

[适用版本: Android 8.0+，Oboe 要求 minSdk 16+]

## 参考资料

- [Background audio hardening](https://developer.android.com/about/versions/17/changes/bg-audio) — Android 17 后台音频强化
- [AudioTrack API reference](https://developer.android.com/reference/android/media/AudioTrack) — `flushWrittenFramesFromPosition()` / `getCodecProvenance()`
- [NDK Audio reference](https://developer.android.com/ndk/reference/group/audio) — `AAudioStream_getSampleRate()`
- [Android Audio Latency](https://source.android.com/docs/core/audio/latency) — Google AOSP 官方文档
- [Android Audio Architecture](https://source.android.com/docs/core/audio/architecture) — 架构全景
- [AAudio API Guide](https://developer.android.com/ndk/guides/audio/aaudio) — 开发者指南
- [Oboe Library](https://github.com/google/oboe) — Google 推荐的低延迟音频封装库
- AOSP: `frameworks/av/services/audioflinger/` — AudioFlinger 源码
- AOSP: `frameworks/av/services/audiopolicy/` — AudioPolicyService 源码
