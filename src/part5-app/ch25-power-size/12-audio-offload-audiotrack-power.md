---
title: "音频 Offload 与 AudioTrack 精确控制功耗实践"
chapter: "25.12"
section: "25.12"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); AAudio offload API 36+, AudioTrack flush/provenance API 37"
last_verified: "2026-05-24"
last_verified_against: "Android Developers AudioTrack / AAudio / Android 17 features / Media3 docs 2026-05；AOSP Android 17 源码待复核"
confidence: medium
tags: [audio, power, aaudio, audiotrack, offload, android17]
related_chapters: ["1.16", "18.21", "25.11", "26.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
sources:
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]"
  - type: research
    path: "intake/research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md"
  - type: official
    path: "https://developer.android.com/ndk/reference/group/audio"
  - type: official
    path: "https://developer.android.com/reference/android/media/AudioTrack"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/media/media3/exoplayer/battery-consumption"
  - type: official
    path: "https://developer.android.com/media/media3/exoplayer/track-selection"
---

# 音频 Offload 与 AudioTrack 精确控制功耗实践

## 音频 Offload 的适用范围

长音频播放的耗电常出现在屏幕关闭之后。用户在听播客、有声书、长视频背景音或语音助手响应时，界面已经不再绘制，但播放器仍可能持续做网络、解码、写入、埋点和 WakeLock 管理。此时继续用 CPU 解码和高频写入，会把一个本该低占用的任务变成稳定耗电源。

Audio offload 解决的是这类长时间播放的 CPU 参与度问题。平台把音频处理交给专用硬件或 DSP，应用可以一次写入更长的数据，框架侧数据管道暂停，CPU 有机会进入睡眠。它不是低延迟方案。游戏音效、乐器、语音通话、实时互动仍应看 AAudio low latency、MMAP、buffer size、callback 稳定性和线程调度，详见 1.16 节。

这里讨论应用侧怎么判断、怎么接入、怎么验证和怎么灰度。AudioFlinger / AAudio / MMAP 的机制详见 1.16 节；MediaCodec、Media3 与播放管线详见 18.21 节；Android 17 后台音频限制详见 25.11 节。

## 场景边界：什么时候值得开启 Offload

Offload 的收益来自少唤醒、少 CPU 解码和少数据搬运。适用场景一般有三个特征：播放时间长、屏幕关闭或界面参与少、媒体格式和设备硬件支持 offload。只满足其中一项，收益可能被兼容代价抵消。

| 场景 | 建议策略 | 判断依据 | 不适合的原因 |
| --- | --- | --- | --- |
| 音乐、播客、有声书锁屏播放 | 优先评估 Offload | 长时间连续播放，用户对毫秒级延迟不敏感 | 倍速、跳过静音、音效处理可能限制 Offload |
| 长视频后台音频 | 可灰度开启 | 屏幕关闭后画面不再参与，音频仍持续 | 视频前台播放时显示和解码成本常高于音频成本 |
| 短音效、按钮声、提示音 | 禁用 | 播放时间短，创建和切换成本占比高 | CPU 省电收益太小，延迟稳定性更要紧 |
| 游戏、乐器、K 歌、实时语音 | 禁用 | 需要低延迟和稳定 callback | Offload 面向省电，不面向低延迟 |
| Assistant 回复音频 | 分场景处理 | 短回复更看延迟，长回复可评估省电 | Android 17 音量流隔离和后台资格要分开判断 |
| 闹钟、提醒 | 按 `USAGE_ALARM` 单独处理 | 与后台音频 hardening 的豁免相关 | 不应把媒体播放伪装成 alarm usage |

Media3 文档建议：短音频或亮屏播放时，音频通常不是主要耗电项；长时间、屏幕关闭后的播放可以评估 ExoPlayer audio offload。官方也说明设备和格式支持会变化，Offload 会限制变速、跳过静音等效果能力，所以不能只看 API level 下结论。


## AAudio Power Saving Offloaded 的探测流程

AAudio 的 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 从 API 36 可用，并且只支持输出流。API 36 同时为 AAudio 公开 MP3、AAC LC、AAC HE V1/V2、AAC ELD、AAC xHE 和 Opus 等压缩格式。Android 17 又定义了可选的 MMAP PCM offload；设备若声明该能力，必须满足 CDD 对 PCM 格式、采样率、声道与缓冲的要求。因此“offloaded”不再等同于“压缩格式”，能力探测必须带上完整格式。

与普通 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING` 相比，offloaded 模式允许应用在短时间写入数秒压缩数据。数据进入硬件缓冲区后，应用播放线程和框架数据管道可以暂停，让 CPU 获得更长的休眠机会。这里的“数秒”来自 NDK 接口说明，不是设备必须提供的固定缓冲深度。

请求值不能作为生效证据。流打开后要读取 `AAudioStream_getPerformanceMode(stream)`；代码还要使用媒体本身的压缩格式、采样率和声道掩码构造 builder。

下面的函数展示能力探测所需的关键字段，调用方传入从媒体轨道读取的真实配置：

```c
bool openOffloadProbe(
        aaudio_format_t format,
        int32_t sampleRate,
        aaudio_channel_mask_t channelMask) {
    AAudioStreamBuilder* builder = NULL;
    if (AAudio_createStreamBuilder(&builder) != AAUDIO_OK) {
        return false;
    }

    AAudioStreamBuilder_setDirection(builder, AAUDIO_DIRECTION_OUTPUT);
    AAudioStreamBuilder_setUsage(builder, AAUDIO_USAGE_MEDIA);
    AAudioStreamBuilder_setFormat(builder, format);
    AAudioStreamBuilder_setSampleRate(builder, sampleRate);
    AAudioStreamBuilder_setChannelMask(builder, channelMask);
    AAudioStreamBuilder_setPerformanceMode(
            builder,
            AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED);

    AAudioStream* stream = NULL;
    const aaudio_result_t result =
            AAudioStreamBuilder_openStream(builder, &stream);

    bool granted = false;
    if (result == AAUDIO_OK) {
        granted = AAudioStream_getPerformanceMode(stream)
                == AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED;
        AAudioStream_close(stream);
    }
    AAudioStreamBuilder_delete(builder);
    return granted;
}
```

这个返回值只能说明探测流获得了 offloaded 模式。正式播放器还要处理 open 失败、断开、路由变化和普通路径回退，并记录 `result`、实际模式、格式、采样率、声道、设备路由和播放器功能开关。示例为了说明探测流程而立即关闭 stream；产品代码应在正式创建路径中记录结果，避免额外创建一条探测流。

API 36 的 `AAudioStreamBuilder_setPresentationEndCallback()` 会在应用请求停止后，等待系统与硬件中已排队的数据播放完，再通知结束。若应用提前关闭 stream，回调不会发生；若它和数据回调共用框架的实时线程，回调中也不能执行阻塞工作。

Android 17 / API 37 又增加了 `AAudio_getFlushFromFrameSupport(builder)` 和 `AAudioStream_flushFromFrame()`。前者必须在打开流前查询，并要求 builder 已设置 offloaded 性能模式、格式、采样率与声道掩码；后者通过 `inOutPosition` 传入目标 frame，并在成功时写回实际 flush 位置。调用返回前不能并发写数据；成功后剩余数据不足时要立即补写，否则会 underrun。若要求 `AAUDIO_FLUSH_FROM_FRAME_ACCURATE` 而设备无法从指定位置处理，r1 返回 `AAUDIO_ERROR_OUT_OF_RANGE`，且不会把一次失败当作成功 flush。


## AudioTrack Offload 的 API 37 新边界

Android 17 为 `AudioTrack` 增加了 codec provenance、写入 frame 计数和按写入位置 flush。它们解决配置来源与深缓冲定位问题，不能单独证明 DSP 正在工作。

| API | 适用范围 | 能回答的问题 | 不能回答的问题 |
| --- | --- | --- | --- |
| `AudioTrack.Builder.setCodecProvenance()` / `getCodecProvenance()` | API 37，配置阶段写入，实例上读取 | 原始内容的 codec media type；未设置时返回空字符串 | 不会替应用检测 codec，也不能证明当前走 DSP 或 offload |
| `getWrittenFramesCount()` | API 37，`MODE_STREAM` | 成功写入后维护的逻辑 frame 坐标；成功 flush 后改为实际 flush 位置 | 不是渲染位置，`pause()`、`stop()` 和普通 `flush()` 也不会重置它 |
| `getFlushWrittenFramesFromPositionSupport(format, attributes)` | API 37，创建 offload `AudioTrack` 前查询 | 给定 `AudioFormat` / `AudioAttributes` 创建的 offload track 是否支持按位置 flush | 不能保证所有设备、所有格式都支持 |
| `flushWrittenFramesFromPosition(positionInFrames, accuracy)` | API 37，只允许 offload mode | 从指定写入 frame 附近丢弃已写入但未播放的数据，返回实际 flush 位置 | 不是普通 PCM `AudioTrack` 的通用 seek API |

codec provenance 由应用在 Builder 中设置，例如原始内容是 Dolby Atmos 的 E-AC3 JOC，但交给 `AudioTrack` 的数据格式已经转换，此时可以传入相应的 `MediaFormat` MIME 常量。它是来源提示，不是运行时探测结果。

`flushWrittenFramesFromPosition()` 的 `positionInFrames` 必须位于 0 到 `getWrittenFramesCount()` 之间。`FLUSH_FROM_ACCURACY_BEST_EFFORT` 允许系统选择不小于目标的位置；`FLUSH_FROM_ACCURACY_EXACT` 要求从目标位置开始。以 `android-17.0.0_r1` 为准，exact 无法满足时返回 `ERROR_BAD_VALUE`；非法 accuracy 或越界输入抛 `IllegalArgumentException`；非 offload 或未初始化抛 `IllegalStateException`；设备不支持则抛 `UnsupportedOperationException`。调用期间不能写入；成功且 Track 仍活跃时，要根据剩余数据及时补写。

需要区分三种坐标：

- `getWrittenFramesCount()` 是应用写入坐标。
- `flushWrittenFramesFromPosition()` 返回新的写入坐标。
- `getTimestamp()` 提供已呈现或承诺呈现的 frame 及其时间估计。

断点续播和 seek 应以媒体时间线为主，把 frame 坐标作为底层执行证据。不能把写入计数直接保存成“用户已经听到的位置”。


这些 API 对四类产品动作有价值：

- 有声书断点续播：记录用户听到的位置、已写入 frame、实际 flush 位置，避免章节跳转后重复播放或少播。
- 切歌和 seek：在 offload buffer 较深时，把“业务目标位置”和“系统实际 flush 位置”都上报，方便定位误差。
- 广告插入：广告前后切换时确认原内容 buffer 是否已丢弃，避免广告后串音。
- 线上兼容：用 support bitmask 和异常类型分桶，识别只在某些设备 / 格式 / 蓝牙路由上失败的组合。

## Media3 / ExoPlayer 如何映射到平台 Offload

Media3 提供的是播放器层偏好，平台决定能否满足。Track selection 文档建议通过 `TrackSelectionParameters` 设置 `AudioOffloadPreferences`；只有 renderers 与 selected tracks 的组合支持时，offload 才会被启用。

这段代码用于表达 Media3 侧 offload 偏好，实际是否启用仍要通过播放器事件、平台 `AudioTrack` 状态和系统取证确认。

```kotlin
val audioOffloadPreferences = AudioOffloadPreferences.Builder()
    .setAudioOffloadMode(AudioOffloadPreferences.AUDIO_OFFLOAD_MODE_ENABLED)
    .setIsGaplessSupportRequired(true)
    .build()

player.trackSelectionParameters = player.trackSelectionParameters
    .buildUpon()
    .setAudioOffloadPreferences(audioOffloadPreferences)
    .build()
```

`setIsGaplessSupportRequired(true)` 会提高无缝播放要求，也可能缩小可 offload 的设备和格式组合。音乐 App、播客 App、有声书 App 的取舍不同：音乐更在意 gapless；播客更常用倍速和跳过静音；有声书更在意章节 seek 和断点续播。灰度开关不要只按“是否开启 Offload”一档设计，至少要把 gapless、倍速、跳过静音、空间音频、蓝牙路由分开。

Media3 的实际状态应通过 `ExoPlayer.AudioOffloadListener` 观察。`onOffloadedPlayback()` 报告当前是否为 offloaded playback，`onSleepingForOffloadChanged()` 报告播放器主循环是否因 offload scheduling 暂停。该 listener 标记为 `@UnstableApi`，升级 Media3 时要重新核对接口兼容性。


## 功耗收益怎么验证

Offload 的验收不能停在“听起来没问题”。CPU、唤醒、电量和用户体验要使用同一次播放会话对齐。观察对象包括应用 CPU 时间、线程唤醒、缓冲深度、系统电量统计和播放状态。

| 指标 | 采集方式 | 看什么 | 解释边界 |
| --- | --- | --- | --- |
| 应用 CPU time | `/proc/<pid>/stat`、Perfetto `sched`、线上线程 CPU 采样 | offload 组的解码 / 写入线程 CPU 时间是否下降 | 不能和网络、埋点、歌词线程混在一起算 |
| 音频线程唤醒 | Perfetto 的 ftrace 调度事件与 `audio` atrace 类别 | App 写入线程、AAudio 回调和 AudioFlinger 线程的运行间隔 | 设备路由切换会改变线程形态 |
| CPU 频率与 idle | Perfetto 的 CPU frequency、idle 与 power 数据源 | 屏幕关闭后 CPU 的频率和空闲状态是否变化 | 受后台任务、网络和蓝牙影响 |
| 电量统计 | `dumpsys batterystats`、Battery Historian | 播放窗口内的 uid 估算、WakeLock、网络和蓝牙活动 | 不是音频轨的直接电表读数，需要同机 A/B |
| 播放体验 | 播放中断率、seek 误差、underrun、用户手动重启播放 | 省电组是否引入可感知问题 | 体验指标必须和功耗指标一起看 |

实验组和对照组要使用同一设备、媒体、路由、音量、网络状态、屏幕状态和播放时长。Perfetto 的录制时长按场景设置，并在两组保持一致，不把某个示例时长当成通用标准。

下面的命令保存音频服务、AudioFlinger、MediaSession 和电量统计。`batterystats --reset` 会清除既有统计，只能在专用测试设备上执行：

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys audio > audio.txt
adb shell dumpsys media.audio_flinger > audio_flinger.txt
adb shell dumpsys media_session > media_session.txt
# 完成一次条件固定的播放后再导出
adb shell dumpsys batterystats > batterystats.txt
```

`dumpsys audio` 侧重 AudioService 的策略与路由，`media.audio_flinger` 用于观察输出线程和 Track，MediaSession 说明播放器对系统公开的状态，batterystats 提供播放窗口内的系统统计。Perfetto 另行使用相同时间戳录制调度、CPU frequency/idle、power、Binder、ActivityManager 和 audio 事件。播放器事件负责补齐请求模式、实际模式、underrun 与回退原因。

## 延迟、音质与兼容性代价

Offload 会把更多数据排入硬件 buffer，也会让部分处理从应用和框架侧移到硬件侧。省电收益来自这一步，代价也来自这一步。

| 代价 | 典型表现 | 处理策略 |
| --- | --- | --- |
| seek / flush 精度差异 | 跳转后重复播放或少播放一段内容 | API 37 用能力查询和实际 flush 位置修正；旧版本按播放器实现选择重建 Track |
| 音效能力受限 | 均衡器、音量归一、空间音频、跳过静音不可用或退回 PCM | 产品能力优先时禁用 offload；省电优先时关闭相关效果 |
| 倍速播放受限 | 非 1.0 倍速时可能退出 offload，或受设备的 speed/pitch 能力与 fallback 模式约束 | 倍速场景允许回退普通路径，单独观测耗电 |
| 蓝牙路由差异 | 某些耳机或车机上 offload 支持变化 | 按 route / device type 分桶灰度 |
| HAL 差异 | 同一格式在不同 SoC 上支持不同 | 不写机型外推结论，按设备能力表下发开关 |
| underrun 风险 | flush 后或数据补给慢时出现断续 | flush 成功后立即补数据，监控 underrun 和短写入 |

因此开关建议拆成三档：

| 档位 | 条件 | 动作 |
| --- | --- | --- |
| 可开启 | 长音频、屏幕关闭、格式支持、无倍速 / 跳过静音、目标设备 A/B 通过 | 默认启用，保留远程关闭 |
| 灰度开启 | 设备支持但功能组合复杂，例如蓝牙、gapless、章节 seek、广告插入 | 小流量开启，按路由和格式分桶 |
| 禁用 | 短音效、实时互动、倍速刚需、空间音频刚需、目标设备异常率高 | 保持 PCM / low latency 路径 |

## Assistant 与后台音频的版本交叉

Android 17 引入 `USAGE_ASSISTANT` 专用音量流，Assistant 回复音量可以和标准媒体音量分开。`MODE_ASSISTANT_CONVERSATION` 可以提示系统当前处于 Assistant 会话，从而改善 Assistant stream 的音量控制一致性，尤其是播放前后和蓝牙外设参与时。

这件事只解决音量控制归属，不解决后台播放资格，也不证明音频走了 offload。Assistant 音频要分三条线判断：

- 音量线：是否使用 `USAGE_ASSISTANT`，应用是否属于可使用 `MODE_ASSISTANT_CONVERSATION` 的 Assistant 集成。
- 后台线：退后台或锁屏后是否满足 Android 17 后台音频 hardening、FGS 与 while-in-use 规则，详见 25.11 节。
- 省电线：长回复或长内容播放是否满足 offload 条件，短回复优先保证延迟和可打断性。


## 线上监控与回滚开关

Offload 接入必须能远程回滚。播放器侧至少记录一条 session 级事件和若干状态变更事件，保证线上能回答四个问题：有没有请求、系统有没有给到、为什么回退、体验是否变差。

| 字段 | 示例 | 用途 |
| --- | --- | --- |
| `offload_requested` | true / false | 区分实验组和对照组 |
| `offload_actual_mode` | AAudio 实际 performance mode，或 Media3 的 offloaded / non-offloaded / unknown | 判断实际路径；PCM 也可能 offload，不能用 `PCM` 表示普通路径 |
| `api_family` | `Media3` / `AudioTrack` / `AAudio` | 区分播放器入口 |
| `format` | MIME、sample rate、channel count、bitrate | 分析格式支持差异 |
| `route` | speaker、wired、Bluetooth、car | 分析输出设备差异 |
| `codec_provenance` | API 37 返回字符串或空 | 辅助分析配置来源，不能当作 offload 证据 |
| `flush_support` | `0` / `FLUSH_WRITTEN_FRAMES_SUPPORTED` | 统计设备能力 |
| `flush_result` | actual frame、`ERROR_BAD_VALUE`、exception | 发现 seek / 切歌问题 |
| `fallback_reason` | unsupported format、effect enabled、speed changed、route changed | 指导开关分桶 |
| `power_bucket` | offload_on / offload_off / disabled_by_config | 关联耗电 P90 / P99 |

远程开关建议按“功能组合”而不是单个布尔值设计：

- `audio_offload_enabled`: 总开关，异常时一键关闭。
- `audio_offload_bluetooth_enabled`: 蓝牙单独开关。
- `audio_offload_gapless_required`: 音乐类 App 单独控制。
- `audio_offload_speed_policy`: 按设备的 speed-change offload 能力选择保留或退出 offload。
- `audio_offload_flush_api37_enabled`: API 37+ 精确 flush 单独灰度。
- `audio_offload_assistant_long_response_enabled`: Assistant 长回复单独实验。

回滚标准也要提前定好：后台播放中断率上升、seek 误差投诉上升、underrun 上升、手动重启播放比例上升、单设备族异常集中，都应触发降级。省电收益再好，也不能用播放体验换。

## 扩展：DSP Offload、Sound Dose 与 HAL 差异

DSP offload 改变音频数据经过的处理路径，但不会取消音量安全、Sound Dose、路由或空间音频规则。应用也不能从 `getCodecProvenance()` 或 offload 生效状态推导这些能力是否启用。验证时应检查系统音量行为、路由切换、空间化状态和长时播放告警，异常再下沉到 AudioFlinger、audio policy 与 HAL 日志。

设备清单可按 SoC、Android 构建、音频 HAL、输出路由、格式、DRM、蓝牙 codec 和空间音频状态组织。高通、联发科、Tensor 或 OEM 定制路径只是分组维度；结论只适用于已经完成同条件测试的组合。

## 小结

音频 Offload 的目标是长时间播放省电，不是低延迟。接入时要把请求模式、实际模式、设备能力、播放器功能和用户体验放在同一套指标里：AAudio 用 `AAudioStream_getPerformanceMode(stream)` 确认实际模式；AudioTrack API 37 用 support bitmask、实际 flush 位置和 codec provenance 辅助判断；Media3 用 `AudioOffloadPreferences` 表达偏好，再由平台决定是否满足。

上线前做同机 A/B，线上保留远程回滚。只有 CPU 时间、线程唤醒、batterystats 和播放体验同时过线，Offload 才算进入可发布状态。

## 参考资料

- [Android NDK AAudio reference](https://developer.android.com/ndk/reference/group/audio)
- [AudioTrack API reference](https://developer.android.com/reference/android/media/AudioTrack)
- [`AAudio.h` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/libaaudio/include/aaudio/AAudio.h)
- [`AudioTrack.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/media/java/android/media/AudioTrack.java)
- [Android 17 CDD：Audio Offload](https://source.android.com/docs/compatibility/17/android-17-cdd#5_5_4_audio_offload)
- [Android 17 features: Dedicated Assistant volume stream](https://developer.android.com/about/versions/17/features)
- [Media3 ExoPlayer battery consumption](https://developer.android.com/media/media3/exoplayer/battery-consumption)
- [Media3 ExoPlayer track selection](https://developer.android.com/media/media3/exoplayer/track-selection)
- [Media3 `ExoPlayer.AudioOffloadListener`](https://developer.android.com/reference/androidx/media3/exoplayer/ExoPlayer.AudioOffloadListener)
