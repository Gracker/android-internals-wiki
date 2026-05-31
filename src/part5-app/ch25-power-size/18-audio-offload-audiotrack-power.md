---
title: "音频 Offload 与 AudioTrack 精确控制功耗实践"
chapter: "25.18"
section: "25.18"
status: ready-for-review
drafted_date: "2026-05-24"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); AAudio offload API 36+, AudioTrack flush/provenance API 37"
last_verified: "2026-05-24"
last_verified_against: "Android Developers AudioTrack / AAudio / Android 17 features / Media3 docs 2026-05；AOSP Android 17 源码待复核"
confidence: medium
tags: [audio, power, aaudio, audiotrack, offload, android17]
related_chapters: ["1.16", "8.8", "18.23", "25.17", "26.3"]
created_by: "task2a-knowledge-gap"
drafted_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "研究素材/官方文档/AOSP结构/Clippings结构参考"
gap_score: 16
material_count: 6
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task9_result: auto-fixed
task9_autofix_at: "2026-05-31"
task6_autofix_trigger: true
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

# 25.18 音频 Offload 与 AudioTrack 精确控制功耗实践

<!-- outline-start -->
## 要点

### 🔹 场景边界：什么时候音频播放值得走 Offload
区分长音频播放、短音效、语音/助手、低延迟互动和后台播放场景，明确 Offload 适合压缩音频长时间播放，低延迟互动仍优先关注 AAudio/MMAP 与缓冲区策略。

### 🔹 AAudio compressed Offload 的能力探测
围绕 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED`、压缩格式、设备能力和 `AAudioStream_getPerformanceMode(stream)` 建立探测流程，避免把请求 Offload 等同于实际走到 DSP 路径。

### 🔹 AudioTrack Offload 的 API 37 新边界
覆盖 `getCodecProvenance()`、`getFlushWrittenFramesFromPositionSupport()`、`flushWrittenFramesFromPosition(long, int)`、`FLUSH_FROM_ACCURACY_EXACT` / `BEST_EFFORT`，说明它们对音频定位、切歌、广告插入和有声书断点续播的影响。

### 🔹 功耗收益的验证方式
用 CPU 时间、音频线程唤醒、batterystats、Perfetto power/audio 相关轨道和播放器侧指标验证收益；只记录可复现实验条件，不用单次主观听感下结论。

### 🔹 延迟、音质与兼容性代价
说明 Offload 可能带来的 seek 精度、音效链、倍速播放、空间音频、设备 HAL 差异和 回退代价，给出「可开启」「灰度开启」「禁用」三档策略。

### 🔹 Assistant 与后台音频的版本交叉
衔接 Android 17 `USAGE_ASSISTANT` 专用音量流、`MODE_ASSISTANT_CONVERSATION` 和 25.17 后台音频 hardening，避免把音量流隔离、后台播放资格和 Offload 能力混在一起判断。

### 🔹 线上监控与回滚开关
设计播放器侧埋点：请求模式、实际性能模式、编解码器来源、回退原因、音频定位/flush 失败、播放中断和功耗实验分组，用于灰度与回滚。

## 扩展

### 🔸 Media3 / ExoPlayer 与平台 Offload 能力映射
梳理 Media3 offload 相关配置如何落到平台 `AudioTrack` / `AudioAttributes`，以及哪些播放器特性会阻断 Offload。

### 🔸 DSP Offload 与 Sound Dose / 音量安全边界
结合 Android 音频框架对压缩音频和 DSP 的处理边界，标注声压、音量安全和 HAL 上报能力的验证点。

### 🔸 不同 SoC / OEM 音频 HAL 差异
记录高通、联发科、Tensor 等设备上 Offload 支持和 fallback 的差异，只作为测试矩阵，不写未验证结论。

<!-- outline-end -->

## 为什么把音频 Offload 单独写成实践章节

长音频播放的耗电常出现在屏幕关闭之后。用户在听播客、有声书、长视频背景音或语音助手响应时，界面已经不再绘制，但播放器仍可能持续做网络、解码、写入、埋点和 WakeLock 管理。此时继续用 CPU 解码和高频写入，会把一个本该低占用的任务变成稳定耗电源。

Audio offload 解决的是这类长时间播放的 CPU 参与度问题。平台把音频处理交给专用硬件或 DSP，应用可以一次写入更长的数据，框架侧数据管道暂停，CPU 有机会进入睡眠。它不是低延迟方案。游戏音效、乐器、语音通话、实时互动仍应看 AAudio low latency、MMAP、buffer size、callback 稳定性和线程调度，详见 1.16 节。

本节只讨论应用侧怎么判断、怎么接入、怎么验证和怎么灰度。AudioFlinger / AAudio / MMAP 的机制详见 1.16 节；MediaCodec、Media3 与播放管线详见 8.8 和 18.23 节；Android 17 后台音频限制详见 25.17 节。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]
[已验证: 官方文档, developer.android.com/media/media3/exoplayer/battery-consumption]

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

Media3 文档给出的边界很清楚：短音频或亮屏播放时，音频通常不是主要耗电项；长时间、屏幕关闭后的播放可以评估 ExoPlayer audio offload。官方也说明设备和格式支持会变化，Offload 会限制变速、跳过静音等效果能力，所以不能只看 API level 下结论。

[已验证: 官方文档, developer.android.com/media/media3/exoplayer/battery-consumption]

## AAudio Power Saving Offloaded 的探测流程

AAudio 的 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 从 API 36 可用。官方 NDK 文档对它的描述是：省电优先，不支持输入流，输出会走 offloaded audio path；与普通 `POWER_SAVING` 相比，它允许应用在短时间内写入数秒数据，数据排入硬件 buffer 后，应用播放线程或进程可以暂停，框架数据管道也会自动暂停，CPU 因此可以睡眠。

请求这个模式不等于系统一定给到这个模式。`AAudioStreamBuilder_setPerformanceMode()` 文档写明，应用可能拿不到请求的模式，打开流后要用 `AAudioStream_getPerformanceMode(stream)` 查询最终结果。这个返回值才是线上日志里的“实际模式"。

这段代码只保留探测骨架。重点是请求后读取实际模式，不把请求参数当作事实。

```c
AAudioStreamBuilder* builder = NULL;
AAudio_createStreamBuilder(&builder);

AAudioStreamBuilder_setDirection(builder, AAUDIO_DIRECTION_OUTPUT);
AAudioStreamBuilder_setUsage(builder, AAUDIO_USAGE_MEDIA);
AAudioStreamBuilder_setPerformanceMode(
        builder,
        AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED);

AAudioStream* stream = NULL;
aaudio_result_t openResult = AAudioStreamBuilder_openStream(builder, &stream);
if (openResult == AAUDIO_OK) {
    aaudio_performance_mode_t actualMode = AAudioStream_getPerformanceMode(stream);
    bool offloadEnabled =
            actualMode == AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED;
    // Record requested mode, actualMode, format, usage, device, and fallback reason.
}

AAudioStreamBuilder_delete(builder);
```

打开成功后还要记录格式、声道、采样率、设备路由、是否蓝牙、是否屏幕关闭、写入模式和回退原因。没有这些字段，线上只能看到“请求过 Offload”，看不到设备为什么没走这条路径。

[已验证: 官方文档, developer.android.com/ndk/reference/group/audio]

AAudio offloaded stream 还有两个 API 36 相关能力值得纳入状态机：`AAudioStreamBuilder_setPresentationEndCallback()` 可在 offloaded stream 中所有已排队 buffer 播放完时回调；`AAudioStream_flushFromFrame()` 只在 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 下工作，可从指定 frame 刷掉后续数据，并返回实际 flush 位置。它适合有声书章节跳转、广告插入后恢复、长音频 seek 等场景，但调用成功后如果剩余数据不足，应用要立刻补数据，否则会发生 underrun。

[已验证: 官方文档, developer.android.com/ndk/reference/group/audio]

## AudioTrack Offload 的 API 37 新边界

Android 17 为 `AudioTrack` 补了两个和 Offload 直接相关的能力：codec provenance 查询，以及按已写入 frame 位置 flush。它们都服务于“长音频控制更细”这个方向，但不能混成同一个判断。

| API | 适用范围 | 能回答的问题 | 不能回答的问题 |
| --- | --- | --- | --- |
| `getCodecProvenance()` | API 37，`AudioTrack` 配置阶段 | 这条 track 配置时记录的 codec media type；未设置时返回空字符串 | 不能单独证明当前已走 DSP、硬解或 offload |
| `getFlushWrittenFramesFromPositionSupport(format, attributes)` | API 37，创建 offload `AudioTrack` 前查询 | 给定 `AudioFormat` / `AudioAttributes` 创建的 offload track 是否支持按位置 flush | 不能保证所有设备、所有格式都支持 |
| `flushWrittenFramesFromPosition(positionInFrames, accuracy)` | API 37，只允许 offload mode | 从指定写入 frame 附近丢弃已写入但未播放的数据，返回实际 flush 位置 | 不是普通 PCM `AudioTrack` 的通用 seek API |

`flushWrittenFramesFromPosition()` 的约束会影响播放器状态机。`positionInFrames` 必须在 0 到已写入 frame 之间；`FLUSH_FROM_ACCURACY_BEST_EFFORT` 表示系统尽量接近请求位置但不低于该位置；`FLUSH_FROM_ACCURACY_EXACT` 表示必须从请求位置 flush。若 exact 模式做不到，方法返回 `ERROR_BAD_VALUE`。调用期间不能继续写入，否则数据可能损坏；调用成功且 stream 仍活跃时，如果剩余音频太少，要马上补写，避免 underrun。

[已验证: 官方文档, developer.android.com/reference/android/media/AudioTrack]

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

[已验证: 官方文档, developer.android.com/media/media3/exoplayer/track-selection]

## 功耗收益怎么验证

Offload 的验收指标不是“听起来没问题”，而是 CPU、唤醒、电量和用户体验都可复查。参考书里把速度优化拆成 CPU 指令、等待、调度和缓存几个维度；迁移到音频省电场景后，观察对象变成 CPU 时间、线程唤醒、buffer 深度、系统电量统计和播放状态。

| 指标 | 采集方式 | 看什么 | 解释边界 |
| --- | --- | --- | --- |
| 应用 CPU time | `/proc/<pid>/stat`、Perfetto `sched`、线上线程 CPU 采样 | offload 组的解码 / 写入线程 CPU 时间是否下降 | 不能和网络、埋点、歌词线程混在一起算 |
| 音频线程唤醒 | Perfetto `audio,sched,freq,idle` | App 写入线程、AAudio callback、AudioFlinger 相关线程唤醒间隔 | 设备路由切换会改变线程形态 |
| CPU 频率与 idle | Perfetto `freq,idle,power` | 屏幕关闭后 CPU 是否更常进入低频或 idle | 受后台任务、网络和蓝牙影响 |
| 电量统计 | `dumpsys batterystats`、Battery Historian | 长时间播放后的 uid 耗电、WakeLock、网络、蓝牙 | 单次短测噪声大，至少做同机 A/B |
| 播放体验 | 播放中断率、seek 误差、underrun、用户手动重启播放 | 省电组是否引入可感知问题 | 体验指标必须和功耗指标一起看 |

这组 Perfetto 命令用于线下 A/B。A 组关闭 offload，B 组开启 offload；两组使用同一设备、同一媒体、同一路由、同一音量、同一网络状态和同一播放时长。

```bash
adb shell perfetto -t 1800s \
  --atrace-categories audio,sched,freq,idle,am,binder_driver \
  --buffer 128mb \
  -o /data/misc/perfetto-traces/audio_offload_ab.pftrace

adb shell dumpsys audio > audio.txt
adb shell dumpsys media_session > media_session.txt
adb shell dumpsys batterystats > batterystats.txt
```

`dumpsys audio` 用来确认 output、track、offload 状态和路由；Perfetto 用来观察线程与 CPU；batterystats 用来做长时间电量对比。三者缺一项，结论都容易偏：只有 Perfetto 可能看不到用户体验，只有 batterystats 很难定位到播放器内部原因，只有播放器日志则无法证明系统省电。

[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]
[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]

## 延迟、音质与兼容性代价

Offload 会把更多数据排入硬件 buffer，也会让部分处理从应用和框架侧移到硬件侧。省电收益来自这一步，代价也来自这一步。

| 代价 | 典型表现 | 处理策略 |
| --- | --- | --- |
| seek / flush 精度差异 | 用户跳转后重复听到几百毫秒，或少听一小段 | API 37+ 用 flush 支持查询和实际 flush 位置修正；旧版本按播放器重建 track 兜底 |
| 音效能力受限 | 均衡器、音量归一、空间音频、跳过静音不可用或退回 PCM | 产品能力优先时禁用 offload；省电优先时关闭相关效果 |
| 倍速播放受限 | 播客 1.5x / 2x 后无法保持 offload | 倍速场景默认回退普通路径，单独观测耗电 |
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

- 音量线：是否使用 `USAGE_ASSISTANT`，是否有 `MODE_ASSISTANT_CONVERSATION` 权限和接入资格。
- 后台线：退后台或锁屏后是否满足 Android 17 后台音频 hardening、FGS 与 while-in-use 规则，详见 25.17 节。
- 省电线：长回复或长内容播放是否满足 offload 条件，短回复优先保证延迟和可打断性。

[已验证: 官方文档, developer.android.com/about/versions/17/features]
[来源: intake/research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md]

## 线上监控与回滚开关

Offload 接入必须能远程回滚。播放器侧至少记录一条 session 级事件和若干状态变更事件，保证线上能回答四个问题：有没有请求、系统有没有给到、为什么回退、体验是否变差。

| 字段 | 示例 | 用途 |
| --- | --- | --- |
| `offload_requested` | true / false | 区分实验组和对照组 |
| `offload_actual_mode` | `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` / `PCM` / `unknown` | 判断实际路径 |
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
- `audio_offload_disable_when_speed_changed`: 播客和有声书默认开启。
- `audio_offload_flush_api37_enabled`: API 37+ 精确 flush 单独灰度。
- `audio_offload_assistant_long_response_enabled`: Assistant 长回复单独实验。

回滚标准也要提前定好：后台播放中断率上升、seek 误差投诉上升、underrun 上升、手动重启播放比例上升、单设备族异常集中，都应触发降级。省电收益再好，也不能用播放体验换。

## 扩展：DSP Offload、Sound Dose 与 HAL 差异

DSP offload 会让音频处理更靠近硬件，音量、安全和声压相关能力也更依赖 HAL 上报。Android 音频框架里还有 Sound Dose、音量安全、设备路由、空间音频等能力，它们和 offload 的组合需要设备侧验证。当前公开文档足以支撑“需要验证”这个判断，不足以支撑某一类 SoC 的固定结论。

测试矩阵至少按 SoC、Android 版本、音频 HAL、输出路由、格式、DRM、蓝牙 codec、是否空间音频拆开。高通、联发科、Tensor 或 OEM 定制路径只能作为测试维度，不能写成未验证的性能结论。

[待验证: 不同 SoC / OEM 音频 HAL 对 offload、Sound Dose、空间音频和蓝牙路由的组合支持]

## 小结

音频 Offload 的目标是长时间播放省电，不是低延迟。接入时要把请求模式、实际模式、设备能力、播放器功能和用户体验放在同一套指标里：AAudio 用 `AAudioStream_getPerformanceMode(stream)` 确认实际模式；AudioTrack API 37 用 support bitmask、实际 flush 位置和 codec provenance 辅助判断；Media3 用 `AudioOffloadPreferences` 表达偏好，再由平台决定是否满足。

上线前做同机 A/B，线上保留远程回滚。只有 CPU 时间、线程唤醒、batterystats 和播放体验同时过线，Offload 才算进入可发布状态。

## 参考资料

- [Android NDK AAudio reference](https://developer.android.com/ndk/reference/group/audio)
- [AudioTrack API reference](https://developer.android.com/reference/android/media/AudioTrack)
- [Android 17 features: Dedicated Assistant volume stream](https://developer.android.com/about/versions/17/features)
- [Media3 ExoPlayer battery consumption](https://developer.android.com/media/media3/exoplayer/battery-consumption)
- [Media3 ExoPlayer track selection](https://developer.android.com/media/media3/exoplayer/track-selection)
- [来源: intake/research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md]
- [结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
- [结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]
- [结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]
