---
title: 后台音频、AudioTrack 与 Offload 功耗
chapter: '25.9'
section: '25.9'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-08-15'
last_source_verified_at: '2026-08-15'
last_verified_against: Android Developers background audio hardening docs updated 2026-08-13 + current Media3/audio focus/battery docs retrieved 2026-08-15；AOSP android-17.0.0_r1 AudioManagerShellCommand/AudioManager/AudioService/HardeningEnforcer/AudioFlinger Tracks.cpp/LeAudioService/codec_manager
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
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]'
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]'
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]'
- type: research
  path: intake/research-feeds/2026-04-08-15-android17-audiotrack-api-assistant-volume-stream.md
- type: official
  path: https://developer.android.com/ndk/reference/group/audio
- type: official
  path: https://developer.android.com/reference/android/media/AudioTrack
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/media/media3/exoplayer/track-selection
- type: official
  path: https://source.android.com/docs/compatibility/17/android-17-cdd#5_5_4_audio_offload
- type: official
  path: https://developer.android.com/reference/androidx/media3/exoplayer/ExoPlayer.AudioOffloadListener
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/libaaudio/include/aaudio/AAudio.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/media/java/android/media/AudioTrack.java
tags:
- power
- audio
- foreground-service
- android-17
- media-playback
- aaudio
- audiotrack
- offload
- android17
related_chapters:
- '1.11'
- '5.3'
- '18.10'
- '11.2'
- '16.1'
- '25.2'
- '26.11'
- '26.1'
task9_state: reviewed
task2b_state: fixed
task6_state: reviewed
pipeline_stage: ready-to-publish
last_draft_polish_at: '2026-08-15T15:46:55+08:00'
last_draft_polish_run_id: 20260815-154655-gracker-writing-452
last_review_finalize_at: '2026-08-15T15:46:55+08:00'
last_review_finalize_run_id: 20260815-154655-gracker-writing-452
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch25-power-size/11-background-audio-hardening-power.md
- src/part5-app/ch25-power-size/12-audio-offload-audiotrack-power.md
---

# 后台音频、AudioTrack 与 Offload 功耗

后台音频需要同时满足媒体会话、前台服务和音频焦点规则；播放管线再决定使用 AudioTrack、低延迟路径或硬件 Offload。稳定性、时延和功耗目标不能用同一配置同时最大化。

## 后台播放资格、生命周期与功耗

### 后台音频的治理范围

这里的“硬化”（hardening）指平台强制执行后台音频的生命周期条件，与音质或编码处理无关。Android 17 同时限制后台音频播放、音频焦点（系统在多个应用之间协调播放、暂停和降低音量）请求、音量与铃声模式修改。应用不满足生命周期条件时，播放器仍可能报告“正在播放”，但用户听不到声音；与此同时，下载、解码、WakeLock（阻止设备休眠的唤醒锁）和前台服务还可能继续运行。播放器状态因此不能单独证明声音已经输出。

排查时要回答两组问题：

- 系统是否允许这次音频交互：页面是否可见、前台服务（foreground service，FGS）是否存在、服务有没有 while-in-use（WIU，通常在应用可见或明确用户操作触发服务时授予）能力、音频用途是否符合豁免条件。
- 播放失效后是否仍消耗资源：网络请求、解码线程、WakeLock、MediaSession（向系统发布播放状态和控制入口的媒体会话）和前台服务是否按停止原因释放。

源码判断以 Android 17 / API 37 / `android-17.0.0_r1` 为版本依据。AudioFlinger（原生音频混音与输出服务）、AAudio（原生低延迟音频 API）和音频线程调度参见 1.11；后台执行规则参见 5.3 与 25.2；Media3（Jetpack 媒体库）、Codec2（Android 多媒体编解码框架）和多媒体管线参见 18.12。

### 两级限制：FGS 基础门槛与 WIU 附加门槛

Android 17 的规则需要分两级理解。文章用 target 简称 `targetSdkVersion`，即应用声明的目标 API 版本。把两级条件合成一句“target 37 才限制后台音频”，会漏掉旧 target 应用也要满足的基础门槛。

#### 所有应用都要满足的基础门槛

任何运行在 Android 17 上的应用，只要在后台播放、申请音频焦点或修改音量，就必须满足以下任一条件：

- Activity 对用户可见；画中画（PiP）也属于可见场景。
- 应用正在运行一个类型不是 `shortService`（短时任务前台服务类型）的前台服务。

这条规则与 `targetSdkVersion` 无关。没有可见 Activity，也没有合格前台服务时，target 35、36 和 37 都会受到限制。

#### target 37 增加的 WIU 门槛

当应用以 API 37 为 target 且位于后台时，前台服务还要具有 WIU 能力。常见的获得方式是：在应用可见时启动服务，或由通知点击、桌面小组件、媒体按键等明确的用户操作触发后台启动。

WIU 不是应用可以自行声明的布尔值。ActivityManager（系统的进程和应用生命周期管理服务）根据前台状态、前台服务的启动来源和系统授予的例外条件维护能力状态，音频服务再读取 AppOps（系统按操作检查调用方是否获准的机制）结果。`HardeningEnforcer` 不解析应用的 `startForeground()` 调用栈，也不自行检查 `PendingIntent`（可由其他组件代为触发的延迟操作）的创建者或某个固定的“最近交互窗口”。

#### 精确闹钟只豁免第二级

API 37 应用同时满足两个条件时，可以免除 WIU 要求：

- 已获准使用 exact alarm（精确闹钟），即持有 `USE_EXACT_ALARM`，或拥有 `SCHEDULE_EXACT_ALARM` 特殊访问。
- 本次音频使用 `AudioAttributes.USAGE_ALARM`。

该豁免不取消第一级要求。后台闹钟仍需要可见 Activity 或非 `shortService` 前台服务。普通媒体内容也不能借用 `USAGE_ALARM` 规避限制；用途声明应与用户可感知的功能一致。

#### 版本差异表

| 状态 | target 35–36 | target 37 |
| --- | --- | --- |
| Activity 可见 | 允许 | 允许 |
| 后台且没有非 `shortService` FGS | 播放静音、焦点失败、音量修改无效 | 同左 |
| 后台，有 FGS，但 FGS 没有 WIU | 通过 target 兼容豁免，只要求基础 FGS | 受到完整限制 |
| 后台，有带 WIU 的 FGS | 允许 | 允许 |
| 后台闹钟，有 FGS、exact alarm 权限和 `USAGE_ALARM` | 不需要 API 37 的闹钟豁免 | 免除 WIU 要求 |

这里的“允许”只表示通过后台音频硬化检查，不保证一定获得焦点、成功路由到目标设备或完成播放。焦点锁定、设备断开、播放器错误仍要按各自规则处理。

### 三类 API 的失败表现

后台音频硬化刻意让多数失败保持静默，避免不合规应用通过异常改变系统行为。应用必须把返回值、系统日志和播放状态放在一起判断。

| 交互 | 默认限制模式 | `throw`（显式失败）测试模式 |
| --- | --- | --- |
| 音频播放 | 输出被静音；播放 API 不提供对应异常或失败消息 | 有显式写入的接口持续返回错误；没有显式写入点的播放模式可能导致进程崩溃 |
| `requestAudioFocus()` | 返回 `AUDIOFOCUS_REQUEST_FAILED`，且不会获得焦点 | 抛出 `IllegalStateException` |
| 音量与铃声模式 API | 调用被忽略，目标状态不变 | 抛出 `IllegalStateException` |

`AudioTrack.write()` 返回成功只能说明数据被客户端提交，不能证明系统把声音送到了输出设备。Media3 的 `playWhenReady`、`playbackState` 也表达播放器状态机，而不是平台授权状态。线上诊断应额外记录焦点结果、前台服务状态、Activity 可见性、音频用途和 `AudioHardening` 日志。

### FGS 和 MediaSession 的正确职责

Android 17 的最低条件是“非 `shortService` 前台服务”，但媒体应用不应随意选择一个无关类型。持续音乐、播客和锁屏视频音频应使用 `mediaPlayback`（媒体播放）类型，并通过 MediaSession 对接系统媒体控件。

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

#### 何时保留或停止 FGS

用户已开始播放后，短暂缓冲、临时网络故障或 `AUDIOFOCUS_LOSS_TRANSIENT` 不代表播放意图结束。Android 17 官方建议在不足 10 分钟的暂时性失败中保留 `mediaPlayback` FGS，便于恢复播放。

内容播放完成、收到永久 `AUDIOFOCUS_LOSS`、用户明确暂停且不再继续、或发生无法恢复的错误时，应停止音频交互、结束 MediaSession 并停止 FGS。Media3 的 `MediaSessionService` 在播放器暂停、停止或失败超过 10 分钟且没有新的用户交互后，也会退出前台服务状态。

这个 10 分钟边界不应解释为应用可以固定空闲 10 分钟。能确认播放意图已经结束时应立即释放；只有失败仍被判断为暂时性时，才保留恢复所需状态。

### 从 target 36 迁移到 target 37

升级 target 没有要求业务改用新的 Java 或 Kotlin 音频 API，改动集中在播放入口和服务生命周期。

#### 建立入口清单

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

#### 给一次播放会话补齐证据

每次会话建议记录：

- 系统 API level、`targetSdkVersion`、应用版本和设备型号。
- 用户入口、Activity 可见性、FGS 类型、FGS 启动时间和启动结果。
- MediaSession 标识与状态、音频 `usage`、焦点请求结果和播放器错误。
- 当前音频路由（声音实际输出到扬声器、耳机等设备的路径）、蓝牙设备类别、网络状态、停止原因和资源释放结果。

同一台 Android 17 设备上的 target 36 与 target 37 行为不同。数据分析至少按 `(API level, targetSdkVersion)` 分组，不能只看系统版本。

### Android 17 r1 的源码执行路径

`android-17.0.0_r1` 把三类交互放在不同位置检查。它们共享同一个 hardening override（后台音频限制的测试覆盖状态），但不是每个 API 都由 Java 和 C++ 重复判断。

| 交互 | 主要实现位置 | 判断内容 |
| --- | --- | --- |
| 音频焦点 | `AudioService` 调用 `HardeningEnforcer.blockFocusMethod()` | `OP_TAKE_AUDIO_FOCUS`、`OP_CONTROL_AUDIO`、target、闹钟及权限豁免 |
| 音量与铃声模式 | `AudioService` 调用 `HardeningEnforcer.blockVolumeMethod()` | `OP_CONTROL_AUDIO_PARTIAL`、`OP_CONTROL_AUDIO`、target 和权限豁免 |
| 播放 | AudioFlinger `Tracks.cpp` 的 `getHardeningDecision()` 与 `AfPlaybackCommon` | 播放 Track（音频播放轨道）创建时确定限制级别，并持续观察两级 AppOps |

音频焦点请求先经过 `HardeningEnforcer`，通过后才进入 `MediaFocusControl` 的焦点仲裁。后台硬化返回 `AUDIOFOCUS_REQUEST_FAILED` 时，请求没有进入常规焦点竞争；这与“另一应用占用了焦点”是两种原因。

#### partial 与 full 的含义

AudioFlinger 为播放 Track 观察 `OP_CONTROL_AUDIO_PARTIAL` 和 `OP_CONTROL_AUDIO`：

- partial（基础级）对应所有应用都要满足的生命周期条件，典型失败原因是没有合格 FGS。
- full（完整级）增加 API 37 的 WIU 条件，典型失败原因是已有 FGS，但服务没有 WIU。

这也解释了官方日志：

- `level: partial`：应用没有运行合格的前台服务。
- `level: full`：应用有前台服务，但该服务缺少 WIU。

限制级别还会受平台兼容条件影响。r1 的 C++ 决策在严格模式下，对 target 小于 37 的应用、符合条件的闹钟以及持有 `BLUETOOTH_CONNECT` 的调用者采用 partial 级别；系统音频用途和具有路由或电话特权的调用者可以豁免。应用不应依赖内部兼容分支代替公开的后台播放模型。

#### Offload 和 MMap 没有绕过限制

`AfPlaybackCommon` 在 Track 创建时注册两条异步 AppOps 会话。Offload 指把音频处理交给专用音频处理器，MMap 指使用内存映射的低延迟音频路径。对于这两类 Track，源码使用 40 ms 的 `asyncBroadcast` 异步唤醒延迟，让 partial 与 full 两个权限回调都有机会在音频线程唤醒前到达。该延迟是权限状态传播的实现细节，不是应用可调的播放缓冲参数。

每条 Track 只记录一次对应的后台播放限制事件，避免同一 Track 反复上报。新的 Track 会重新计算决策，因此重新创建播放器并不能修复不合规生命周期，只会生成新的受限 Track。

#### Java 与原生层的权限判断不能拼成“矛盾结果”

Java 的焦点和音量入口使用 AppOps，AudioFlinger 的播放路径既根据权限与 target 选择限制级别，也通过异步 AppOps 判断当前是否允许输出。不能根据 `PermissionEnum` 的静态权限检查推导出“音量被禁，但 Track 一定有声”；是否静音还取决于 Track 的 AppOps 状态、限制级别和豁免结果。

### 调试命令存在版本差异

Android 17 官方页面在 2026-08-13 的当前版本中使用 `set-enable-hardening`，而 `android-17.0.0_r1` 的 `AudioManagerShellCommand` 使用 `set-hardening` 与 `clear-hardening`。因此不能把某个命令名视为所有 Android 17 系统镜像都相同。

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

r1 的 `clear-hardening` 与 `set-hardening default` 都恢复平台默认行为；`set-hardening disable` 是强制关闭限制，并不等同于恢复默认。新命令中的 `disable` 也表示关闭全部限制。r1 的测试覆盖状态会同步写入 `system_server`（承载多数 Java 系统服务的进程）与 `audioserver`（承载原生音频服务的进程），但不会持久化。只提供新命令、没有 `clear` 或 `default` 子命令的系统镜像，应按设备帮助确认恢复方式，必要时重启专用测试设备。测试报告还要记录命令和构建号。

`enable` 会把完整限制应用到所有应用，并取消 target 与闹钟豁免，适合寻找潜在问题；它不能替代默认行为下的 target 36/37 对照测试。`throw` 还会把静默失败改成异常、持续写入错误或崩溃，只能用于开发与回归环境。

### 取证：把许可状态和功耗放在一条时间线上

这些命令用于保存复现现场。`dumpsys` 导出系统服务状态，`logcat` 导出系统日志。`batterystats --reset` 会清除设备上已有的电量统计，只应在专用测试设备上执行。

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

这批文件要使用统一的会话标识，并按同一时钟关联事件。`dumpsys audio` 说明平台为何限制交互，`media_session` 和服务记录说明应用宣告了什么状态，`batterystats` 说明播放停止后是否仍有 WakeLock、网络和后台活动。

Perfetto 是 Android 的系统级跟踪工具，采集应覆盖音频、调度、CPU 频率、电源、Binder（Android 跨进程调用机制）和 ActivityManager 相关轨迹。阅读顺序可以固定为：用户操作、FGS 启动、MediaSession 激活、焦点结果、Track 创建、页面退后台或锁屏、网络或路由变化、播放停止、资源释放。若声音消失后 CPU、网络或 WakeLock 仍活跃，说明声音停止后的资源清理不足。

### 长时播放的功耗检查

后台音频的能耗由多条路径叠加。应先用测量确认主要消耗来源，再改配置。

| 资源 | 观察信号 | 处理方向 |
| --- | --- | --- |
| 解码 | 播放线程 CPU 时间、Media3 offload 事件、设备与格式支持情况 | 长音频可评估 audio offload；音效、倍速等功能不兼容时保留普通解码 |
| 缓冲 | underrun（缓冲数据未能及时供给播放端）、加载频率、内存占用和恢复耗时 | 按内容与网络条件配置，不复制视频的缓冲参数 |
| 网络 | 失败码、重试间隔、重复下载字节、播放停止后的流量 | 使用有上限的重试退避（连续失败时逐步延长间隔）；不可恢复时停止预取 |
| WakeLock | tag（用于识别持有者的标签）、持有时长、播放结束后的残留 | 为持有设置超时，并在每个终止路径释放 |
| 非播放任务 | 歌词、封面、推荐、埋点线程的 CPU 时间与唤醒 | 降低非必要任务频率，避免与解码和输出线程竞争 |
| 蓝牙 | 路由变更、断连重连、设备类别、控制器活动 | 把路由故障和播放器故障分开统计 |

Audio offload 改变解码与输出所使用的计算资源，后台硬化检查的是应用生命周期。两者相互独立：offload Track 仍受 hardening 控制；未匹配 ADSP（Audio Digital Signal Processor，音频数字信号处理器）的 LC3（Low Complexity Communication Codec，低复杂度通信编解码器）配置，也不等于应用会因处于后台而被静音。

`codec_manager.cc` 的 `IsLc3ConfigMatched()` 比较采样率、帧时长、每条 ISO（Isochronous，等时）流的通道数和每帧字节数，用于判断 LC3 配置是否匹配。匹配失败影响编解码执行路径，不直接决定 FGS 或 WIU。`target_latency` 表示 Bluetooth LE Audio（低功耗蓝牙音频）配置期望的时延等级，它参与配置选择，但仅凭“低延迟”无法推算设备能耗，仍需在具体控制器、耳机和媒体参数上测量。

Android 17 r1 的 `LeAudioService.setSystemSuspended()` 会在系统进入 suspend（低功耗挂起）状态时停止后台扫描，并在恢复且确有扫描需求时重新启动。这是平台蓝牙服务的省电行为，不是第三方播放器可调用的控制接口。应用侧应记录路由和连接事件，不要用持续扫描或高频重连掩盖系统状态变化。

### 验证场景与线上指标

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

线上指标应同时覆盖“用户想听却没有声音”和“用户不再听但资源仍运行”。P90、P99 表示 90% 和 99% 的样本不超过对应数值，用于观察平均值容易掩盖的高耗电会话：

| 指标 | 主要维度 |
| --- | --- |
| 后台播放中断率 | API level、target、入口、FGS 状态、ROM（厂商系统版本） |
| 音频焦点失败率 | `AudioAttributes.usage`（音频用途）、焦点类型、页面可见性、FGS 与 WIU |
| `AudioHardening` 命中 | partial/full、包名、入口、是否设置测试覆盖状态 |
| MediaSession 异常结束 | Player 状态、Session 状态、停止原因、网络 |
| 后台耗电 P90/P99 | 会话时长、网络、路由、offload、设备 |
| 用户手动恢复播放比例 | 页面、通知、媒体键、蓝牙设备 |

小流量发布时应同时比较 target 36 与 37。若中断率上升，要按 partial/full 区分缺 FGS 与缺 WIU；若声音已经停止但耗电上升，则检查资源释放与重试状态机。两类问题需要分别定位原因。

### 后台音频小结

Android 17 后台音频硬化有清晰的两级条件：所有应用都需要可见 Activity 或非 `shortService` FGS；target 37 的后台应用还需要带 WIU 的 FGS，真实闹钟可以在满足权限和 `USAGE_ALARM` 时免除 WIU。

应用适配的重点是让播放入口、MediaSession、`mediaPlayback` FGS 和资源生命周期表达同一份用户意图。平台限制播放后，业务也要停止无效的网络、解码和保活。验收不能只看播放器有没有报错，还要确认声音、焦点、通知、路由和资源释放都可由证据解释。

## AudioTrack 缓冲、Offload 与设备能力

后台执行资格确定后，音频路径按格式、效果、延迟和硬件支持选择 Offload。回退到混音路径时要重新评估 CPU 和 WakeLock。

### 音频 Offload 的适用范围

长音频播放的耗电常出现在屏幕关闭之后。用户在听播客、有声书、长视频背景音或语音助手响应时，界面已经不再绘制，但播放器仍可能持续做网络、解码、写入、埋点和 WakeLock（阻止设备休眠的唤醒锁）管理。此时继续用 CPU 解码和高频写入，会让本应低占用的任务持续耗电。

Audio offload（音频卸载）解决的是这类长时间播放的 CPU 参与度问题。平台把音频处理交给专用硬件或 DSP（Digital Signal Processor，数字信号处理器），应用可以一次写入更多数据；硬件 buffer（缓冲区）保存待播放内容后，框架数据管道可以暂停，CPU 因而有机会休眠。低延迟场景不适合这条路径。游戏音效、乐器、语音通话和实时互动仍应关注 AAudio（原生低延迟音频 API）的低延迟模式、MMAP（应用和硬件通过共享内存交换音频数据的路径）、缓冲区大小、callback（数据回调）的稳定性与线程调度，详见 1.11 节。

应用侧需要完成能力探测、接入、验证和小流量发布。AudioFlinger（原生音频混音与输出服务）、AAudio 与 MMAP 的机制详见 1.11 节；MediaCodec（编解码接口）、Media3（Jetpack 媒体库）与播放管线详见 18.12 节；Android 17 后台音频 hardening（生命周期限制）见本文前半部分。

### 场景边界：什么时候值得开启 Offload

Offload 的收益来自少唤醒、少 CPU 解码和少数据搬运。适用场景一般有三个特征：播放时间长、屏幕关闭或界面参与少、媒体格式和设备硬件支持 offload。只满足其中一项，收益可能被兼容代价抵消。

| 场景 | 建议策略 | 判断依据 | 不适合的原因 |
| --- | --- | --- | --- |
| 音乐、播客、有声书锁屏播放 | 优先评估 Offload | 长时间连续播放，用户对毫秒级延迟不敏感 | 倍速、跳过静音、音效处理可能限制 Offload |
| 长视频后台音频 | 可小流量验证 | 屏幕关闭后画面不再参与，音频仍持续 | 视频前台播放时显示和解码成本常高于音频成本 |
| 短音效、按钮声、提示音 | 禁用 | 播放时间短，创建和切换成本占比高 | CPU 省电收益太小，延迟稳定性更要紧 |
| 游戏、乐器、K 歌、实时语音 | 禁用 | 需要低延迟和稳定 callback | Offload 面向省电，不面向低延迟 |
| Assistant（系统语音助手）回复音频 | 分场景处理 | 短回复更看延迟，长回复可评估省电 | Android 17 音量流隔离和后台资格要分开判断 |
| 闹钟、提醒 | 按 `USAGE_ALARM` 单独处理 | 与后台音频 hardening 的豁免相关 | 不应把媒体播放伪装成 alarm usage |

Media3 文档建议：短音频或亮屏播放时，音频通常不是主要耗电项；长时间、屏幕关闭后的播放可以评估 ExoPlayer audio offload。官方也说明设备和格式支持会变化，Offload 会限制变速、跳过静音等效果能力，所以不能只看 API level 下结论。

### AAudio Power Saving Offloaded 的探测流程

AAudio 的 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING_OFFLOADED` 从 API 36 可用，并且只支持输出流。API 36 同时为 AAudio 公开 MP3、AAC LC、AAC HE V1/V2、AAC ELD、AAC xHE 和 Opus 等压缩格式。Android 17 又定义了可选的 MMAP PCM（Pulse-Code Modulation，脉冲编码调制，即未压缩采样数据）offload；设备若声明该能力，必须满足 CDD 对 PCM 格式、采样率、声道与缓冲的要求。因此“offloaded”不再等同于“压缩格式”，能力探测必须带上完整格式。

与普通 `AAUDIO_PERFORMANCE_MODE_POWER_SAVING` 相比，offloaded 模式允许应用在短时间写入数秒压缩数据。数据进入硬件缓冲区后，应用播放线程和框架数据管道可以暂停，让 CPU 获得更长的休眠机会。这里的“数秒”来自 NDK 接口说明，不是设备必须提供的固定缓冲深度。

请求值不能作为生效证据。音频流对象（代码中的 `stream`）打开后要读取 `AAudioStream_getPerformanceMode(stream)`；代码还要使用媒体本身的压缩格式、采样率和声道掩码构造 builder（流配置构建器）。

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

这个返回值只能说明探测流获得了 offloaded 模式。正式播放器还要处理打开失败、断开、路由变化和常规播放路径回退，并记录 `result`、实际模式、格式、采样率、声道、设备路由和播放器功能开关。示例为了说明探测流程而立即关闭 stream；产品代码应在正式创建路径中记录结果，避免额外创建一条探测流。

API 36 的 `AAudioStreamBuilder_setPresentationEndCallback()` 会在应用请求停止后，等待系统与硬件中已排队的数据播放完，再通知结束。若应用提前关闭 stream，回调不会发生；若它和数据回调共用框架的实时线程，回调中也不能执行阻塞工作。

Android 17 / API 37 又增加了 `AAudio_getFlushFromFrameSupport(builder)` 和 `AAudioStream_flushFromFrame()`。flush 指丢弃已经写入但尚未播放的数据，frame（音频帧）是这里的位置计数单位。前者必须在打开流前查询，并要求 builder 已设置 offloaded 性能模式、格式、采样率与声道掩码；后者通过 `inOutPosition` 传入目标 frame，并在成功时写回实际 flush 位置。调用返回前不能并发写数据；成功后剩余数据不足时要立即补写，否则会出现 underrun（数据供给不及时造成的播放断续）。若要求 `AAUDIO_FLUSH_FROM_FRAME_ACCURATE` 而设备无法从指定位置处理，r1 返回 `AAUDIO_ERROR_OUT_OF_RANGE`，且不会把一次失败当作成功 flush。

### AudioTrack Offload 的 API 37 新边界

Android 17 为 `AudioTrack` 增加了 codec provenance（原始内容的编解码格式来源）、写入 frame 计数和按写入位置 flush。它们解决配置来源与深缓冲定位问题，不能单独证明 DSP 正在工作。

| API | 适用范围 | 能回答的问题 | 不能回答的问题 |
| --- | --- | --- | --- |
| `AudioTrack.Builder.setCodecProvenance()` / `getCodecProvenance()` | API 37，配置阶段写入，实例上读取 | 原始内容的 codec media type（编解码格式 MIME 类型）；未设置时返回空字符串 | 不会替应用检测 codec，也不能证明当前走 DSP 或 offload |
| `getWrittenFramesCount()` | API 37，`MODE_STREAM` | 成功写入后维护的逻辑 frame 坐标；成功 flush 后改为实际 flush 位置 | 不是渲染位置，`pause()`、`stop()` 和普通 `flush()` 也不会重置它 |
| `getFlushWrittenFramesFromPositionSupport(format, attributes)` | API 37，创建 offload `AudioTrack` 前查询 | 给定 `AudioFormat` / `AudioAttributes` 创建的 offload track 是否支持按位置 flush | 不能保证所有设备、所有格式都支持 |
| `flushWrittenFramesFromPosition(positionInFrames, accuracy)` | API 37，只允许 offload mode | 从指定写入 frame 附近丢弃已写入但未播放的数据，返回实际 flush 位置 | 不是普通 PCM `AudioTrack` 的通用 seek API |

codec provenance 由应用在 Builder 中设置。例如原始内容是 Dolby Atmos 的 E-AC3 JOC，但交给 `AudioTrack` 的数据格式已经转换，此时可以传入相应的 `MediaFormat` MIME 常量。它是来源提示，不是运行时探测结果。

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
- 线上兼容：用 support bitmask（支持位掩码，以二进制位表示能力）和异常类型分组统计，识别只在某些设备、格式或蓝牙路由上失败的组合。

### Media3 / ExoPlayer 如何映射到平台 Offload

Media3 提供的是播放器层偏好，平台决定能否满足。轨道选择文档建议通过 `TrackSelectionParameters` 设置 `AudioOffloadPreferences`；只有 renderer（实际执行解码或输出的组件）与所选媒体轨道的组合支持时，offload 才会启用。

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

`setIsGaplessSupportRequired(true)` 要求歌曲或章节之间 gapless（无缝衔接），也可能缩小可 offload 的设备和格式组合。音乐、播客、有声书应用的取舍不同：音乐更在意 gapless；播客更常用倍速和跳过静音；有声书更在意章节 seek（跳转）和断点续播。发布开关不能只有“是否开启 Offload”一档，至少要把 gapless、倍速、跳过静音、空间音频和蓝牙路由分开。

Media3 的实际状态应通过事件监听器 `ExoPlayer.AudioOffloadListener` 观察。`onOffloadedPlayback()` 报告当前是否采用 offloaded playback，`onSleepingForOffloadChanged()` 报告播放器主循环是否因 offload scheduling（卸载调度）而暂停。该 listener 标记为 `@UnstableApi`，表示接口仍可能变化；升级 Media3 时要重新核对兼容性。

### 功耗收益怎么验证

Offload 的验收不能停在“听起来没问题”。CPU、唤醒、电量和用户体验数据要来自同一次播放会话。Perfetto 是 Android 的系统级跟踪工具，可把应用 CPU 时间、线程唤醒、缓冲深度、系统电量统计和播放状态放到同一条时间线上。

| 指标 | 采集方式 | 看什么 | 解释边界 |
| --- | --- | --- | --- |
| 应用 CPU 时间 | `/proc/<pid>/stat`（`pid` 是进程 ID）、Perfetto `sched`、线上线程 CPU 采样 | offload 组的解码与写入线程 CPU 时间是否下降 | 不能和网络、埋点、歌词线程混在一起算 |
| 音频线程唤醒 | Perfetto 的 ftrace（内核跟踪）调度事件与 `audio` atrace（Android 跟踪标记）类别 | 应用写入线程、AAudio 回调和 AudioFlinger 线程的运行间隔 | 设备路由切换会改变线程形态 |
| CPU 频率与 idle | Perfetto 的 CPU frequency、idle（空闲状态）与 power 数据源 | 屏幕关闭后 CPU 的频率和空闲状态是否变化 | 受后台任务、网络和蓝牙影响 |
| 电量统计 | `dumpsys batterystats`、Battery Historian（电量统计可视化工具） | 播放窗口内按 UID（应用对应的 Linux 用户 ID）估算的耗电、WakeLock、网络和蓝牙活动 | 不是音频轨的直接电表读数，需要同机 A/B 对照 |
| 播放体验 | 播放中断率、seek 误差、underrun、用户手动重启播放 | 省电组是否引入可感知问题 | 体验指标必须和功耗指标一起看 |

实验组和对照组要使用同一设备、媒体、路由、音量、网络状态、屏幕状态和播放时长。Perfetto 的录制时长按场景设置，并在两组保持一致，不把某个示例时长当成通用标准。

这些 `dumpsys` 命令用于导出音频服务、AudioFlinger、MediaSession 和电量统计。`batterystats --reset` 会清除既有统计，只能在专用测试设备上执行：

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys audio > audio.txt
adb shell dumpsys media.audio_flinger > audio_flinger.txt
adb shell dumpsys media_session > media_session.txt
# 完成一次条件固定的播放后再导出
adb shell dumpsys batterystats > batterystats.txt
```

`dumpsys audio` 侧重 AudioService 的策略与路由，`media.audio_flinger` 用于观察输出线程和 Track，MediaSession 说明播放器对系统公开的状态，batterystats 提供播放窗口内的系统统计。Perfetto 另行按同一时钟和播放窗口录制调度、CPU frequency/idle、power、Binder（Android 跨进程调用机制）、ActivityManager（应用进程与生命周期管理服务）和 audio 事件。播放器事件负责补齐请求模式、实际模式、underrun 与回退原因。

### 延迟、音质与兼容性代价

Offload 会把更多数据排入硬件 buffer，也会让部分处理从应用和框架侧移到硬件侧。省电收益来自这一步，代价也来自这一步。

| 代价 | 典型表现 | 处理策略 |
| --- | --- | --- |
| seek / flush 精度差异 | 跳转后重复播放或少播放一段内容 | API 37 用能力查询和实际 flush 位置修正；旧版本按播放器实现选择重建 Track |
| 音效能力受限 | 均衡器、音量归一、空间音频、跳过静音不可用或退回 PCM | 产品能力优先时禁用 offload；省电优先时关闭相关效果 |
| 倍速播放受限 | 非 1.0 倍速时可能退出 offload，或受设备的 speed/pitch（速度/音调）能力与 fallback（参数不受支持时的回退策略）模式约束 | 倍速场景允许回退常规播放路径，单独观测耗电 |
| 蓝牙路由差异 | 某些耳机或车机上 offload 支持变化 | 按输出路由和设备类型分组做小流量验证 |
| HAL（硬件抽象层）差异 | 同一格式在不同 SoC（System on Chip，片上系统）上支持不同 | 不把单一机型结论外推，按设备能力表下发开关 |
| underrun 风险 | flush 后或数据补给慢时出现断续 | flush 成功后立即补数据，监控 underrun 和短写入 |

发布策略可以分成三档：

| 档位 | 条件 | 动作 |
| --- | --- | --- |
| 可开启 | 长音频、屏幕关闭、格式支持、无倍速 / 跳过静音、目标设备 A/B 通过 | 默认启用，保留远程关闭 |
| 小流量开启 | 设备支持但功能组合复杂，例如蓝牙、gapless、章节 seek、广告插入 | 按路由和格式分组验证 |
| 禁用 | 短音效、实时互动、倍速刚需、空间音频刚需、目标设备异常率高 | 保持 PCM / low latency 路径 |

复杂功能组合应先按对应路由和格式完成同机 A/B；未满足体验与功耗阈值的组合继续使用 PCM 或低延迟路径。

### Assistant 与后台音频的版本交叉

Android 17 引入 `USAGE_ASSISTANT` 专用音量流，Assistant 的回复音量可以和标准媒体音量分开。`MODE_ASSISTANT_CONVERSATION` 可以提示系统当前处于 Assistant 会话，从而改善 Assistant 音量流的控制一致性，尤其是播放前后和蓝牙外设参与时。

这件事只解决音量控制归属，不解决后台播放资格，也不证明音频走了 offload。Assistant 音频要分三条线判断：

- 音量线：是否使用 `USAGE_ASSISTANT`，应用是否属于可使用 `MODE_ASSISTANT_CONVERSATION` 的 Assistant 集成。
- 后台线：退后台或锁屏后是否满足 Android 17 后台音频 hardening、FGS（前台服务）与 while-in-use（WIU，应用可见或明确用户操作触发时授予的能力）规则，见本文前半部分。
- 省电线：长回复或长内容播放是否满足 offload 条件，短回复优先保证延迟和可打断性。

### 线上监控与远程关闭

Offload 接入必须能远程关闭并回到普通播放路径。播放器至少为每次播放会话记录一条汇总事件和若干状态变更事件，让线上数据回答四个问题：应用是否请求、系统是否满足、为何回退、体验是否变差。P90、P99 表示 90% 和 99% 的样本不超过对应值，用来观察少量高耗电会话。

| 字段 | 示例 | 用途 |
| --- | --- | --- |
| `offload_requested` | true / false | 区分实验组和对照组 |
| `offload_actual_mode` | AAudio 实际 performance mode，或 Media3 的 offloaded / non-offloaded / unknown | 判断实际路径；PCM 也可能 offload，不能用 `PCM` 表示未启用 offload |
| `api_family` | `Media3` / `AudioTrack` / `AAudio` | 区分播放器入口 |
| `format` | MIME、sample rate、channel count、bitrate | 分析格式支持差异 |
| `route` | speaker、wired、Bluetooth、car | 分析输出设备差异 |
| `codec_provenance` | API 37 返回字符串或空 | 辅助分析配置来源，不能当作 offload 证据 |
| `flush_support` | `0` / `FLUSH_WRITTEN_FRAMES_SUPPORTED` | 统计设备能力 |
| `flush_result` | actual frame、`ERROR_BAD_VALUE`、exception | 发现 seek / 切歌问题 |
| `fallback_reason` | unsupported format、effect enabled、speed changed、route changed | 按回退原因控制开关 |
| `power_bucket` | offload_on / offload_off / disabled_by_config | 标记实验分组并关联耗电 P90 / P99 |

远程开关建议按“功能组合”而不是单个布尔值设计：

- `audio_offload_enabled`：总开关，异常时一键关闭。
- `audio_offload_bluetooth_enabled`：蓝牙单独开关。
- `audio_offload_gapless_required`：音乐类应用单独控制。
- `audio_offload_speed_policy`：按设备的 speed-change offload 能力选择保留或退出 offload。
- `audio_offload_flush_api37_enabled`：API 37+ 精确 flush 单独做小流量验证。
- `audio_offload_assistant_long_response_enabled`：Assistant 长回复单独实验。

远程关闭条件要提前确定：后台播放中断率、seek 误差投诉、underrun 或手动重启播放比例上升，以及异常集中在单一设备族时，都应让对应组合回到普通播放路径。省电收益不能以播放体验变差为代价。

### 扩展：DSP Offload、Sound Dose 与 HAL 差异

DSP offload 改变音频数据经过的处理路径，但不会取消音量安全、Sound Dose（累计声音暴露剂量）、路由或空间音频规则。应用也不能从 `getCodecProvenance()` 或 offload 生效状态推导这些能力是否启用。验证时应检查系统音量行为、路由切换、空间化状态和长时播放告警；出现异常后，再检查 AudioFlinger、audio policy（音频策略）与 HAL 日志。

设备清单可按 SoC、Android 构建、音频 HAL、输出路由、格式、DRM（Digital Rights Management，数字版权管理）、蓝牙 codec 和空间音频状态组织。高通、联发科、Tensor 或 OEM（设备厂商）定制路径只是分组维度；结论只适用于已经完成同条件测试的组合。

### Offload 小结

音频 Offload 的目标是降低长时间播放的耗电，低延迟场景应使用相应的实时音频路径。接入时要把请求模式、实际模式、设备能力、播放器功能和用户体验放在同一套指标里：AAudio 用 `AAudioStream_getPerformanceMode(stream)` 确认实际模式；AudioTrack API 37 用 support bitmask、实际 flush 位置和 codec provenance 辅助判断；Media3 用 `AudioOffloadPreferences` 表达偏好，再由平台决定是否满足。

上线前做同机 A/B，线上保留远程关闭能力。CPU 时间、线程唤醒、batterystats 和播放体验同时满足验收阈值后，Offload 才进入可发布状态。

## 全文小结

后台音频先要证明这次播放具备可见页面、合格前台服务和必要的 WIU 条件，再选择普通混音、低延迟或 Offload 路径。前一层决定系统是否允许持续发声，后一层决定如何在时延、功能和功耗之间取舍；任何一层失败，都要同步停止无效的网络、解码、WakeLock 与服务状态。发布验证应把入口、MediaSession、FGS、实际音频路径、路由和单位会话功耗放到同一条时间线上。

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

- [Android NDK AAudio reference](https://developer.android.com/ndk/reference/group/audio)
- [AudioTrack API reference](https://developer.android.com/reference/android/media/AudioTrack)
- [`AAudio.h` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/av/+/refs/tags/android-17.0.0_r1/media/libaaudio/include/aaudio/AAudio.h)
- [`AudioTrack.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/media/java/android/media/AudioTrack.java)
- [Android 17 CDD：Audio Offload](https://source.android.com/docs/compatibility/17/android-17-cdd#5_5_4_audio_offload)
- [Android 17 features: Dedicated Assistant volume stream](https://developer.android.com/about/versions/17/features)
- [Media3 ExoPlayer battery consumption](https://developer.android.com/media/media3/exoplayer/battery-consumption)
- [Media3 ExoPlayer track selection](https://developer.android.com/media/media3/exoplayer/track-selection)
- [Media3 `ExoPlayer.AudioOffloadListener`](https://developer.android.com/reference/androidx/media3/exoplayer/ExoPlayer.AudioOffloadListener)
