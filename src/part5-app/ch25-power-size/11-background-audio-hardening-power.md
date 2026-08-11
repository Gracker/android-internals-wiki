---
title: "Android 17 后台音频硬化与播放功耗治理"
chapter: "25.11"
section: "25.11"
status: finalized
drafted_date: "2026-05-24"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-02"
last_verified_against: "Android Developers background audio hardening / Media3 / audio focus docs 2026-05；AOSP android-17.0.0_r1 AudioManagerShellCommand/AudioManager/AudioService/HardeningEnforcer/AudioFlinger Tracks.cpp"
confidence: medium
sources:
- type: official
  path: https://developer.android.com/about/versions/17/changes/bg-audio
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/media/media3/session/background-playback
- type: official
  path: https://developer.android.com/media/optimize/audio-focus
- type: official
  path: https://developer.android.com/media/media3/exoplayer/battery-consumption
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/audio/HardeningEnforcer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/audio/AudioManagerShellCommand.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/audio/MediaFocusControl.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/Tracks.cpp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_audio/LeAudioService.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/system/bta/le_audio/codec_manager.cc
- type: official
  path: https://developer.android.com/tools/perfetto
- type: official
  path: https://developer.android.com/studio/command-line/dumpsys
tags: [[power, audio, foreground-service, android-17, media-playback]]
related_chapters: ["1.16", "5.8", "18.21", "11.2", "16.5", "25.15", "26.14"]
created_by: "task2a-knowledge-gap"
drafted_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "官方文档/已有章节深挖/每日信息"
task9_state: reviewed
task9_result: pass-tech-review
reviewed_by: "openclaw-task6"
reviewed_date: "2026-07-05"
task6_result: "pass-light-edit"
last_task6_at: 2026-07-05T02:13:44+08:00
last_task6_audit: "2026-06-28"
last_task6_review_log: "logs/review/2026-07-05-02-review.md"
task6_review_notes: "2026-05-24 Task6 首次 review: pass-light-edit。L1/L2 小修 3 处（补 Task6/section/drafted_by 元数据与 FGS service-type 来源、首次展开 WIU 缩写、修正锚点标题一致性）。无新增 Task6 回炉；转 Task9 技术复核。 | 2026-07-05 Task6 复审 (round 2): pass-light-edit。Task2B 已补充 targetSdk 36→37 迁移路径四步法与行为差异表。L1 仅 2 处 frontmatter 修正（title/chapter/section 引号转义、p0 计数校正）。L2/L3/L4 全部通过。task9 已通过 + queue 无 pending → 自动晋升 finalized。 | 2026-07-05 Task6 复审 (round 3): pass-light-edit。Task2B Lite 验证 set-hardening enable/throw/clear-hardening 命令锚定 AudioManagerShellCommand.java:182-185,517-563，无需修改。L1 禁用词扫描全清、CN-EN 间距零问题、高频词全部 ≤1 次。L2/L3/L4 全部通过。queue 两条目均 completed。task9_result 补录 pass-tech-review。无 B 类问题 → 自动晋升 finalized。"

task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-05"
last_task9_at: "2026-07-02T14:29:53+08:00"
last_task9_audit: "2026-07-02"
last_task9_review_log: "logs/deep-review/2026-07-02-14-audit.md"
task9_review_notes: "2026-05-24 07:40 Task9 deep-review: pass-tech-review。无 P0/P1；P2 0 项；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-02 Task9 闲时抽检 AUTO-FIX: 修正 Android 17 后台音频 hardening shell 命令为 `cmd audio set-hardening`/`clear-hardening`；`disable` 是强制关闭 override，不是恢复默认行为；回到 Task6 复审。"
p0: 0
p1: 0
p2: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-05
last_task9_audit_log: "logs/deep-review/2026-07-02-14-audit.md"
last_task9_autofix_at: "2026-07-02"
updated_by: openclaw-task9
updated_date: "2026-07-02"
last_task2b_at: 2026-07-05T00:53:38+08:00
last_task2b_by: task2b-main
task2b_lite_note: "2026-07-04 Task2B Lite 验证: set-hardening enable/throw/clear-hardening 命令已正确，无需修改。证据锚定 AudioManagerShellCommand.java:182-185,517-563。queue P90 条目标记 skipped-false-positive。"
task2b_verifier_normalize: "2026-07-04T23:28:57+08:00 Verifier: status revisiting→ready-for-review, task2b_state fixed-skipped→fixed (standardized for Task6 pickup). task6_state=revisiting, task9_state=pending, pipeline_stage=task6_pending confirmed correct."
task2b_result: fixed-lite
task2b_state: fixed
task6_state: reviewed
pipeline_stage: ready-to-publish
last_task2b_lite_at: 2026-07-05
---

# Android 17 后台音频硬化与播放功耗治理

## 后台音频的治理范围

Android 17 同时限制后台音频播放、音频焦点请求、音量与铃声模式修改。应用不满足生命周期条件时，播放器仍可能报告“正在播放”，但用户听不到声音；与此同时，下载、解码、WakeLock 和前台服务还可能继续运行。播放器状态因此不能单独证明播放有效。

排查时要回答两组问题：

- 系统是否允许这次音频交互：页面是否可见、前台服务是否存在、服务有没有 while-in-use（WIU）能力、音频用途是否符合豁免条件。
- 播放失效后是否仍消耗资源：网络请求、解码线程、WakeLock、MediaSession 和前台服务是否按停止原因释放。

平台源码基线为 Android 17 / API 37 / `android-17.0.0_r1`。AudioFlinger、AAudio 和音频线程调度参见 1.16；后台执行规则参见 5.8 与 25.15；Media3、Codec2 和多媒体管线参见 18.21。

## 两级限制：先看 FGS，再看 WIU

Android 17 的规则需要分两级理解。把两级条件合成一句“target 37 才限制后台音频”，会漏掉旧 target 应用也要满足的基础门槛。

### 所有应用都要满足的基础门槛

任何运行在 Android 17 上的应用，只要在后台播放、申请音频焦点或修改音量，就必须满足以下任一条件：

- Activity 对用户可见；画中画（PiP）也属于可见场景。
- 应用正在运行一个类型不是 `shortService` 的前台服务。

这条规则与 `targetSdkVersion` 无关。没有可见 Activity，也没有合格前台服务时，target 35、36 和 37 都会受到限制。

### target 37 增加的 WIU 门槛

当应用以 API 37 为 target 且位于后台时，前台服务还要具有 WIU 能力。常见的获得方式是：在应用可见时启动服务，或由通知点击、桌面小组件、媒体按键等明确的用户操作触发后台启动。

WIU 不是应用可以自行声明的布尔值。ActivityManager 根据前台状态、前台服务的启动来源和系统授予的例外条件维护能力状态，音频服务通过 AppOps 结果消费这个状态。`HardeningEnforcer` 并不解析应用的 `startForeground()` 调用栈，也不自行检查 `PendingIntent` 创建者或某个固定的“最近交互窗口”。

### exact alarm 只豁免第二级

API 37 应用同时满足下面两个条件时，可以免除 WIU 要求：

- 已获准使用 exact alarm，即持有 `USE_EXACT_ALARM`，或拥有 `SCHEDULE_EXACT_ALARM` 特殊访问。
- 本次音频使用 `AudioAttributes.USAGE_ALARM`。

该豁免不取消第一级要求。后台闹钟仍需要可见 Activity 或非 `shortService` 前台服务。普通媒体内容也不能借用 `USAGE_ALARM` 规避限制；用途声明应与用户可感知的功能一致。

### 版本差异表

| 状态 | target 35–36 | target 37 |
| --- | --- | --- |
| Activity 可见 | 允许 | 允许 |
| 后台且没有非 `shortService` FGS | 播放静音、焦点失败、音量修改无效 | 同左 |
| 后台，有 FGS，但 FGS 没有 WIU | 通过 target 兼容豁免，只要求基础 FGS | 受到完整限制 |
| 后台，有带 WIU 的 FGS | 允许 | 允许 |
| 后台闹钟，有 FGS、exact alarm 权限和 `USAGE_ALARM` | 不需要 API 37 的闹钟豁免 | 免除 WIU 要求 |

这里的“允许”只表示通过后台音频硬化检查，不保证一定获得焦点、成功路由到目标设备或完成播放。焦点锁定、设备断开、播放器错误仍要按各自规则处理。

## 三类 API 的失败表现

后台音频硬化刻意让多数失败保持静默，避免不合规应用通过异常改变系统行为。应用必须把返回值、系统日志和播放状态放在一起判断。

| 交互 | 默认限制模式 | `throw` 测试模式 |
| --- | --- | --- |
| 音频播放 | 输出被静音；播放 API 不提供对应异常或失败消息 | 有显式写入的接口持续返回错误；没有显式写入点的播放模式可能导致进程崩溃 |
| `requestAudioFocus()` | 返回 `AUDIOFOCUS_REQUEST_FAILED`，且不会获得焦点 | 抛出 `IllegalStateException` |
| 音量与铃声模式 API | 调用被忽略，目标状态不变 | 抛出 `IllegalStateException` |

`AudioTrack.write()` 返回成功只能说明数据被客户端提交，不能证明系统把声音送到了输出设备。Media3 的 `playWhenReady`、`playbackState` 也表达播放器状态机，而不是平台授权状态。线上诊断应额外记录焦点结果、前台服务状态、Activity 可见性、音频用途和 `AudioHardening` 日志。

## FGS 和 MediaSession 的正确职责

Android 17 的最低条件是“非 `shortService` 前台服务”，但媒体应用不应随意选择一个无关类型。持续音乐、播客和锁屏视频音频应使用 `mediaPlayback` 类型，并通过 MediaSession 对接系统媒体控件。

使用 Media3 时，`MediaSessionService` 负责把 `Player` 与 `MediaSession` 放进服务生命周期，提供媒体通知以及外部控制入口。清单至少要声明对应的前台服务权限和服务类型。

下面的清单片段用于声明后台媒体播放服务：

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission
    android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />

<application>
    <service
        android:name=".PlaybackService"
        android:exported="true"
        android:foregroundServiceType="mediaPlayback">
        <intent-filter>
            <action android:name="androidx.media3.session.MediaSessionService" />
        </intent-filter>
    </service>
</application>
```

这些声明解决服务类型和权限问题，不会自动赋予 WIU。服务仍应在用户开始播放时启动，并让 `Player`、`MediaSession`、通知和 FGS 状态随同一份播放意图变化。

### 何时保留或停止 FGS

用户已开始播放后，短暂缓冲、临时网络故障或 `AUDIOFOCUS_LOSS_TRANSIENT` 不代表播放意图结束。Android 17 官方建议在不足 10 分钟的暂时性失败中保留 `mediaPlayback` FGS，便于恢复播放。

内容播放完成、收到永久 `AUDIOFOCUS_LOSS`、用户明确暂停且不再继续、或发生无法恢复的错误时，应停止音频交互、结束 MediaSession 并停止 FGS。Media3 的 `MediaSessionService` 在播放器暂停、停止或失败超过 10 分钟且没有新的用户交互后，也会退出前台服务状态。

这个 10 分钟边界不应解释为应用可以固定空闲 10 分钟。能确认播放意图已经结束时应立即释放；只有失败仍被判断为暂时性时，才保留恢复所需状态。

## 从 target 36 迁移到 target 37

升级 target 没有要求业务改用新的 Java 或 Kotlin 音频 API，改动集中在播放入口和服务生命周期。

### 建立入口清单

列出所有可能开始或恢复播放的来源，并记录该来源能否表达用户当下的操作：

| 入口 | 处理建议 |
| --- | --- |
| 可见页面内的播放按钮 | 在该操作中启动 `mediaPlayback` FGS，然后开始播放 |
| 通知播放按钮、桌面小组件、媒体按键 | 保留用户操作来源，交给 MediaSession 或受支持的后台启动路径 |
| `BOOT_COMPLETED` | 不自动发声；提供播放恢复入口，等待用户操作 |
| 后台任务、网络恢复广播 | 可以准备轻量状态，但不要自行恢复音频交互 |
| 投屏断开后回到本机 | 若没有新的用户操作，不要假设原 FGS 仍具有 WIU；按当前服务状态决定继续或提示用户 |
| exact alarm | 只用于确有闹钟语义的功能，并同时核对权限、`USAGE_ALARM` 和 FGS |

如果 `mediaPlayback` FGS 本身不能从后台启动，系统可能在音频硬化之前就拒绝服务启动。排查时应先查 `ForegroundServiceStartNotAllowedException` 或 ActivityManager 的拒绝记录，再查 WIU 和音频日志。

### 给一次播放会话补齐证据

每次会话建议记录：

- 系统 API level、`targetSdkVersion`、应用版本和设备型号。
- 用户入口、Activity 可见性、FGS 类型、FGS 启动时间和启动结果。
- MediaSession 标识与状态、音频 `usage`、焦点请求结果和播放器错误。
- 当前音频路由、蓝牙设备类别、网络状态、停止原因和资源释放结果。

同一台 Android 17 设备上的 target 36 与 target 37 行为不同。数据分析至少按 `(API level, targetSdkVersion)` 分组，不能只看系统版本。

## Android 17 r1 的源码执行路径

`android-17.0.0_r1` 把三类交互放在不同位置检查。它们共享同一个 hardening override，但不是每个 API 都由 Java 和 C++ 重复判断。

| 交互 | 主要实现位置 | 判断内容 |
| --- | --- | --- |
| 音频焦点 | `AudioService` 调用 `HardeningEnforcer.blockFocusMethod()` | `OP_TAKE_AUDIO_FOCUS`、`OP_CONTROL_AUDIO`、target、闹钟及权限豁免 |
| 音量与铃声模式 | `AudioService` 调用 `HardeningEnforcer.blockVolumeMethod()` | `OP_CONTROL_AUDIO_PARTIAL`、`OP_CONTROL_AUDIO`、target 和权限豁免 |
| 播放 | AudioFlinger `Tracks.cpp` 的 `getHardeningDecision()` 与 `AfPlaybackCommon` | Track 创建时确定限制级别，并持续观察两级 AppOps |

音频焦点请求先经过 `HardeningEnforcer`，通过后才进入 `MediaFocusControl` 的焦点仲裁。后台硬化返回 `AUDIOFOCUS_REQUEST_FAILED` 时，请求没有进入常规焦点竞争；这与“另一应用占用了焦点”是两种原因。

### partial 与 full 的含义

AudioFlinger 为播放 Track 观察 `OP_CONTROL_AUDIO_PARTIAL` 和 `OP_CONTROL_AUDIO`：

- partial 级别对应所有应用都要满足的基础生命周期条件，典型失败原因是没有合格 FGS。
- full 级别增加 API 37 的 WIU 条件，典型失败原因是已有 FGS，但服务没有 WIU。

这也解释了官方日志：

- `level: partial`：应用没有运行合格的前台服务。
- `level: full`：应用有前台服务，但该服务缺少 WIU。

限制级别还会受平台兼容条件影响。r1 的 C++ 决策在严格模式下，对 target 小于 37 的应用、符合条件的闹钟以及持有 `BLUETOOTH_CONNECT` 的调用者采用 partial 级别；系统音频用途和具有路由或电话特权的调用者可以豁免。应用不应依赖内部兼容分支代替公开的后台播放模型。

### Offload 和 MMap 没有绕过硬化

`AfPlaybackCommon` 在 Track 创建时注册两条异步 AppOps 会话。对于 Offload 或 MMap Track，源码使用 40 ms 的 `asyncBroadcast` 延迟，让 partial 与 full 两个权限回调都有机会在音频线程唤醒前到达。该延迟是权限状态传播的实现细节，不是应用可调的播放缓冲参数。

每条 Track 只记录一次对应的 playback hardening 事件，避免同一 Track 反复上报。新的 Track 会重新计算决策，因此重新创建播放器并不能修复不合规生命周期，只会生成新的受限 Track。

### Java 与 native 权限判断不能拼成“矛盾结果”

Java 的焦点和音量入口使用 AppOps，AudioFlinger 的播放路径既根据权限与 target 选择限制级别，也通过异步 AppOps 判断当前是否允许输出。不能根据 `PermissionEnum` 的静态权限检查推导出“音量被禁，但 Track 一定有声”；是否静音还取决于 Track 的 AppOps 状态、限制级别和豁免结果。

## 调试命令存在版本差异

Android 17 官方页面在 2026-07-14 更新后使用 `set-enable-hardening`，而 `android-17.0.0_r1` 的 `AudioManagerShellCommand` 使用 `set-hardening` 与 `clear-hardening`。因此不要把某个命令名视为所有 Android 17 镜像都相同。

这组命令先读取设备自己的帮助，再按匹配分支启用测试模式：

```bash
# 先确认当前镜像提供的 hardening 子命令
adb shell cmd audio help | grep -i hardening

# android-17.0.0_r1
adb shell cmd audio set-hardening enable
adb shell cmd audio set-hardening throw
adb shell cmd audio clear-hardening

# Android 17 当前官方文档所述的新命令
adb shell cmd audio set-enable-hardening enable
adb shell cmd audio set-enable-hardening throw
adb shell cmd audio set-enable-hardening disable
```

r1 的 `clear-hardening` 恢复平台默认行为；`set-hardening disable` 是强制关闭限制，并不等同于恢复默认。新命令中的 `disable` 也表示关闭全部限制。r1 的 override 同步写入 system_server 与 audioserver 的运行时状态，但没有持久化；没有 `clear` 或 `default` 子命令的镜像应按设备帮助确认恢复方式，必要时重启专用测试设备。测试报告还要记录命令和构建号。

`enable` 会把完整限制应用到所有应用，并取消 target 与闹钟豁免，适合寻找潜在问题；它不能替代默认行为下的 target 36/37 对照测试。`throw` 还会把静默失败改成异常、持续写入错误或崩溃，只能用于开发与回归环境。

## 取证：把许可状态和功耗放在一条时间线上

下面的命令用于保存复现现场。`batterystats --reset` 会清除设备上已有的电量统计，只应在专用测试设备上执行。

```bash
# 音频策略、焦点、音量和 hardening 事件
adb shell dumpsys audio > audio.txt
adb logcat -b all -v threadtime \
  | grep -Ei "AudioHardening|AudioFocus|AudioTrack" > audio-log.txt

# MediaSession 与前台服务
adb shell dumpsys media_session > media-session.txt
adb shell dumpsys activity services YOUR_PACKAGE_NAME > services.txt

# 为本次场景建立单独的电量统计窗口
adb shell dumpsys batterystats --reset
# 完成复现后导出
adb shell dumpsys batterystats > batterystats.txt
```

这批文件要用统一的会话标识和时间戳对齐。`dumpsys audio` 说明平台为何限制交互，`media_session` 和服务记录说明应用宣告了什么状态，`batterystats` 说明播放停止后是否仍有 WakeLock、网络和后台活动。

Perfetto 采集应覆盖音频、调度、CPU 频率、电源、Binder 和 ActivityManager 相关轨迹。阅读顺序可以固定为：用户操作、FGS 启动、MediaSession 激活、焦点结果、Track 创建、页面退后台或锁屏、网络或路由变化、播放停止、资源释放。若声音消失后 CPU、网络或 WakeLock 仍活跃，说明停止态清理不足。

## 长时播放的功耗检查

后台音频的能耗由多条路径叠加。应先用测量确认主要消耗来源，再改配置。

| 资源 | 观察信号 | 处理方向 |
| --- | --- | --- |
| 解码 | 播放线程 CPU 时间、Media3 offload 事件、设备与格式支持情况 | 长音频可评估 audio offload；音效、倍速等功能不兼容时保留普通解码 |
| 缓冲 | underrun、加载频率、内存占用和恢复耗时 | 按内容与网络条件配置，不复制视频的缓冲参数 |
| 网络 | 失败码、重试间隔、重复下载字节、播放停止后的流量 | 使用有上限的退避；不可恢复时停止预取 |
| WakeLock | tag、持有时长、播放结束后的残留 | 为持有设置超时，并在每个终止路径释放 |
| 非播放任务 | 歌词、封面、推荐、埋点线程的 CPU 时间与唤醒 | 降低非必要任务频率，避免与解码和输出线程竞争 |
| 蓝牙 | 路由变更、断连重连、设备类别、控制器活动 | 把路由故障和播放器故障分开统计 |

Audio offload 改变解码与输出所使用的计算资源，后台硬化检查的是应用生命周期。两者相互独立：offload Track 仍受 hardening 控制；未匹配 ADSP 的 LC3 配置也不等于应用会因处于后台而被静音。

`codec_manager.cc` 的 `IsLc3ConfigMatched()` 比较采样率、帧时长、每条 ISO 流的通道数和每帧字节数，用于判断 LC3 配置是否匹配。匹配失败影响编解码执行路径，不直接决定 FGS 或 WIU。`target_latency` 参与 LE Audio 配置选择，但仅凭“低延迟”无法推算设备能耗，仍需在具体控制器、耳机和媒体参数上测量。

Android 17 r1 的 `LeAudioService.setSystemSuspended()` 会在系统挂起时停止后台扫描，并在恢复且确有扫描需求时重新启动。这是平台蓝牙服务的省电行为，不是第三方播放器可调用的控制接口。应用侧应记录路由和连接事件，不要用持续扫描或高频重连掩盖系统状态变化。

## 验证场景与线上指标

回归测试要覆盖入口、target、音频用途和路由组合。用例时长按产品的预期会话设计；除平台规定的 10 分钟暂时性失败边界外，不需要编造固定分钟数。

| 用例 | 操作 | 预期 |
| --- | --- | --- |
| 可见页面播放 | 页面可见时开始播放 | 焦点成功，正常出声 |
| 锁屏继续播放 | 用户开始播放后锁屏 | `mediaPlayback` FGS 与 MediaSession 保持，通知可控制 |
| 无 FGS 的后台播放 | 停止 FGS 后继续写音频 | target 36 与 37 都受到 partial 限制 |
| FGS 没有 WIU | 从不带用户意图的后台入口启动服务并播放 | target 36 走兼容行为；target 37 受到 full 限制 |
| 暂时性弱网或焦点丢失 | 在平台建议窗口内恢复 | 保留播放意图；恢复成功后继续播放 |
| 永久焦点丢失或不可恢复错误 | 触发终止条件 | 停止播放器、MediaSession、FGS、网络和 WakeLock |
| exact alarm | 以 `USAGE_ALARM` 触发真实闹钟 | 权限和 FGS 满足时，target 37 免 WIU |
| 通知、媒体键恢复 | 从系统媒体控件或外设恢复 | 形成新的用户播放意图并启动所需服务 |
| 蓝牙与 LE Audio 切换 | 连接、断开并改变输出设备 | 状态和路由一致；不把路由断开统计为 hardening |
| hardening `enable` / `throw` | 对相同场景分别执行 | 静默失败和显式失败路径都有可解释记录 |

线上指标应同时覆盖“用户想听却没有声音”和“用户不再听但资源仍运行”：

| 指标 | 主要维度 |
| --- | --- |
| 后台播放中断率 | API level、target、入口、FGS 状态、ROM |
| 音频焦点失败率 | usage、焦点类型、页面可见性、FGS 与 WIU |
| `AudioHardening` 命中 | partial/full、包名、入口、是否测试 override |
| MediaSession 异常结束 | Player 状态、Session 状态、停止原因、网络 |
| 后台耗电 P90/P99 | 会话时长、网络、路由、offload、设备 |
| 用户手动恢复播放比例 | 页面、通知、媒体键、蓝牙设备 |

灰度时应同时比较 target 36 与 37。若中断率上升，要先按 partial/full 区分缺 FGS 与缺 WIU；若声音已经停止但耗电上升，则检查资源释放与重试状态机。两类问题需要分开定责。

## 小结

Android 17 后台音频硬化有清晰的两级条件：所有应用都需要可见 Activity 或非 `shortService` FGS；target 37 的后台应用还需要带 WIU 的 FGS，真实闹钟可以在满足权限和 `USAGE_ALARM` 时免除 WIU。

应用适配的重点是让播放入口、MediaSession、`mediaPlayback` FGS 和资源生命周期表达同一份用户意图。平台限制播放后，业务也要停止无效的网络、解码和保活。验收不能只看播放器有没有报错，还要确认声音、焦点、通知、路由和资源释放都可由证据解释。

## 参考资料

- [Background audio hardening | Android Developers](https://developer.android.com/about/versions/17/changes/bg-audio)
- [Behavior changes: Apps targeting Android 17 or higher | Android Developers](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Background playback with a MediaSessionService | Android Developers](https://developer.android.com/media/media3/session/background-playback)
- [Manage audio focus | Android Developers](https://developer.android.com/media/optimize/audio-focus)
- [Battery consumption | Android media | Android Developers](https://developer.android.com/media/media3/exoplayer/battery-consumption)
- [`HardeningEnforcer.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/audio/HardeningEnforcer.java)
- [`AudioManagerShellCommand.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/audio/AudioManagerShellCommand.java)
- [`MediaFocusControl.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/audio/MediaFocusControl.java)
- [`Tracks.cpp` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/services/audioflinger/Tracks.cpp)
- [`LeAudioService.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_audio/LeAudioService.java)
- [`codec_manager.cc` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/system/bta/le_audio/codec_manager.cc)
- [Perfetto | Android Developers](https://developer.android.com/tools/perfetto)
- [dumpsys | Android Developers](https://developer.android.com/studio/command-line/dumpsys)
