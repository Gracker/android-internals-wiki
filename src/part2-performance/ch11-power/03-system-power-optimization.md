---
title: 系统级功耗优化
chapter: '11.3'
status: finalized
section: '11.3'
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 6.0 (API 23) - Android 16 (API 36)
last_verified: '2026-04-20'
last_verified_against: AOSP android-16.0.0_r1, Android Developers Doze / location
  / foreground service docs
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
rework_count: 3
rework_date: '2026-05-07'
rework_by: task2b-rework
confidence: medium
sources:
- type: official
  path: https://developer.android.com/training/monitoring-device-state/doze-standby
- type: official
  path: https://developer.android.com/topic/performance/appstandby
- type: official
  path: https://developer.android.com/topic/performance/power/power-details#app-stdby-bucket
- type: official
  path: https://developer.android.com/guide/components/activities/background-starts
- type: official
  path: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- type: official
  path: https://developer.android.com/training/location/background
- type: official
  path: https://source.android.com/docs/core/power
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java
- type: aosp
  path: frameworks/base/services/usage/java/com/android/server/usage/UsageStatsService.java
- type: aosp
  path: frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityOptions.java
- type: aosp
  path: frameworks/base/core/java/android/os/PowerManager.java
- type: official
  path: https://dontkillmyapp.com/
- type: official
  path: https://developer.android.com/topic/performance/app-hibernation
- type: official
  path: https://source.android.com/docs/core/storage/app-archiving
- type: official
  path: https://developer.android.com/about/versions/oreo/background
- type: official
  path: https://developer.android.com/topic/performance/power
- type: official
  path: https://developer.android.com/about/versions
tags:
- doze
- standby
- battery-saver
- background-restriction
- oem-power
- adaptive-battery
- foreground-service
related_chapters:
- '5.6'
- '11.1'
- '11.2'
- '1.3'
- '4.4'
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: '2026-05-06'
task6_result: pass-light-edit
task6_state: reviewed
last_task2b_at: '2026-04-26T10:41:09+08:00'
repaired_date: '2026-04-26'
repaired_by: openclaw-task2b
last_task6_at: '2026-05-06T22:05:00+08:00'
last_task6_review_log: logs/review/2026-05-06-22-review.md
last_task6_audit: '2026-05-24'
review_notes: '2026-05-13 task9 deep-review: pass-tech-review。P0 0，P1 0，P2 1；厂商功耗策略数据建议写入 suggestions，不阻塞发布；自动晋升 finalized。'
review_round: 4
pipeline_stage: ready-to-publish
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task9_reviewed_date: '2026-05-13'
task9_reviewed_by: openclaw-task9
last_task9_at: '2026-05-13T15:31:00+08:00'
last_task9_review_log: logs/deep-review/2026-05-13-15-deep-review.md
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-27
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-30
---


# 系统级功耗优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Doze 模式的分阶段触发与维护窗口机制
- 🔹 App Standby Buckets（Active/Working/Frequent/Rare/Restricted）的调度差异
- 🔹 系统级限后台策略：Background Activity Starts 限制、后台定位限制
- 🔹 省电模式下的系统行为变化
- 🔹 厂商级功耗管理：后台冻结、自启动管理、后台杀进程策略

### 扩展（可选深入）

- 🔸 Adaptive Battery 的 ML 模型工作原理
- 🔸 电池健康管理（Adaptive Charging）与性能的关系

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解系统级功耗管理

在 §11.2 中，我们讨论了 App 侧可以做的功耗优化：减少 WakeLock 持有时间、合理使用 WorkManager、优化网络请求频率等。这些都是在 App 主动配合的前提下完成的。即便一个 App 自身做得很好，系统依然可能替它"省电"——在用户不知情的情况下限制它的后台行为、推迟它的任务执行、甚至直接杀掉它的进程。

Android 从 6.0 开始就内置了系统级功耗管理策略，经过 Android 9 的 App Standby Buckets、Android 12 的 Restricted 桶，到各厂商自研的后台管控机制，系统级功耗管理的能力越来越强、粒度越来越细。

如果我们不了解这些机制，就会遇到一些令人困惑的现象：推送延迟到达、后台任务没有按预期执行、用户投诉 App "吃电" 但代码里找不到问题。这些问题的根因往往不在 App 内部，而在系统级功耗策略对外部行为的约束上。

理解这些机制后，我们能做的事情包括：在 Perfetto/Battery Historian 中识别系统级限制导致的延迟；根据 Standby Bucket 的不同配额调整后台任务策略；在用户反馈"后台被杀"时判断是 AOSP 行为还是厂商定制行为；有针对性地引导用户在系统设置中为 App 豁免某些限制。

## Doze 模式：分阶段触发与维护窗口机制

Doze 模式是 Android 6.0（API 23）引入的低功耗状态管理机制，核心思想是：当设备长时间不被使用时，系统主动限制后台 App 的 CPU 和网络活动，将它们集中到短暂的"维护窗口"中执行，其余时间设备尽可能保持深度睡眠。

### 两种 Doze：Light Doze 与 Deep Doze

Android 7.0（API 24）将 Doze 拆分为两个层级：

**Light Doze** 的触发条件比较宽松——只要屏幕关闭且设备未在充电，即使设备在移动中也会进入。它的限制力度相对温和：推迟非关键的网络请求和 JobScheduler 任务，但仍然允许高优先级 FCM 消息到达、允许精确闹钟（有速率限制）、允许前台服务运行。

**Deep Doze** 则是原始的、更严格的 Doze。它需要设备满足三个条件：屏幕关闭、未在充电、且设备处于静止状态（通过加速度计判断）。一旦进入 Deep Doze，系统会实施大幅度的限制：网络访问被暂停、标准 AlarmManager 闹钟被推迟、WakeLock 大部分被忽略、JobScheduler 任务和 SyncAdapter 同步被延迟、后台 Wi-Fi 扫描停止。


### 维护窗口：递增长度的呼吸机制

Doze 在限制后台活动的同时，会周期性地进入短暂的维护窗口（Maintenance Window），在这个窗口内临时解除大部分限制，让 App 有机会完成积压的工作。

维护窗口的关键特征是**间隔递增**。设备刚进入 Doze 时，维护窗口相对更密；空闲时间继续拉长后，窗口之间的间隔会逐步变长，后期可能相隔数小时。具体数值受 Android 版本、设备配置和白名单状态影响，不适合把 1 小时、2 小时、4 小时写成固定常量。

在维护窗口内，系统会短暂放开一部分限制，集中处理被延后的工作：

- 执行被推迟的 JobScheduler 任务和 SyncAdapter 同步
- 允许被延迟的 AlarmManager 闹钟触发
- 临时恢复网络访问
- WakeLock 正常工作

这也是为什么常会出现这样的用户反馈：“我的 App 后台同步有时候能工作，有时候不行。”如果同步恰好赶上了维护窗口，它就能完成；如果错过了，就要等下一个窗口。

### 在 Perfetto 中的表现

Doze 的取证不要依赖某个固定名字的 Track。更稳的做法，是把 Trace、`dumpsys deviceidle`、`dumpsys jobscheduler` 和 Battery Historian 对在一起看。

抓取 Trace 时，至少打开这几类信号：

- ftrace：`sched/*`、`power/suspend_resume`、`power/cpu_frequency`、`power/cpu_idle`
- framework atrace category：`power`、`am`、`wm`、`view`
- 如果要看任务延迟，再补 `dumpsys jobscheduler`、`dumpsys alarm` 和 Battery Historian

一组可复核的 Doze 证据通常有三步：

1. 用 `adb shell dumpsys deviceidle` 确认设备已经进入 `LIGHT`、`IDLE` 或 `IDLE_MAINTENANCE`，必要时用 `force-idle` / `step` / `unforce` 主动驱动状态迁移。
2. 非维护窗口阶段，后台线程几乎没有 runnable slice，网络与 Job 分发明显收缩，`suspend_resume` 和 `cpu_idle` 驻留时间上升。
3. 进入维护窗口后，系统会出现一小段批量唤醒，被延后的 Job、Alarm 或网络 I/O 集中执行；窗口结束后，又回到低活跃状态。


### Doze 的豁免与例外

并非所有场景都适合被 Doze 限制。以下情况 Doze 不会生效或可以豁免：

- **设备在充电时**：Doze 完全不激活
- **高优先级 FCM 消息**：可以在 Doze 期间唤醒 App（这是 Google 推荐的紧急通知方式）
- **用户在设置中手动豁免的 App**：设置 → 电池 → 未受限
- **前台服务**：前台服务能提高进程优先级，降低因后台执行限制被回收的概率，但它不等于 Doze 豁免。设备进入 Doze 后，网络、JobScheduler、普通 Alarm 和同步限制仍按 device idle policy 生效。
- **紧急闹钟**（`setAndAllowWhileIdle` / `setExactAndAllowWhileIdle`）：可以在 Doze 期间触发，但每个 App 有速率限制（大约每 9 分钟一次）


## App Standby：从二元状态到分桶调度

Doze 模式解决的是"设备空闲"场景的功耗问题。但很多时候，设备并不是空闲的——用户正在刷微博，但后台还有一个从来不用的购物 App 在频繁拉取数据。这就是 App Standby 要解决的问题。

**Android 6-8（API 23-27）** 已经有 App Standby 机制，但只有 idle / active 两个状态：被判定为 idle 的 App，后台网络访问、Job 和 Sync 会被推迟，充电时释放。判定依据是 App 是否有前台进程、是否最近被用过、是否被用户显式豁免。这时的限制相对粗粒度——要么限制，要么不限制。

**Android 9（API 28）** 把二元模型扩展为 App Standby Buckets，根据用户对每个 App 的使用频率，将它们分为五个优先级桶，每个桶拥有不同的后台资源配额。与 Doze 不同，App Standby 不需要设备处于空闲状态，它随时都在工作。API 31 新增了 Restricted 桶，进一步收紧长期不互动 App 的后台配额。

### 五个桶的定义与调度差异

五个桶的作用，是把“最近是否真的被用户用到”翻译成后台资源预算。官方文档把这些额度当作近似指导值，不保证实际执行时长，设备是否充电、进程是否可见、前台服务、用户手动 unrestricted 都会覆盖桶限制。

| Bucket | 典型场景 | Regular jobs | Expedited jobs | Alarms | Network |
|------|------|------|------|------|------|
| Active | 正在使用、刚用过、或用户刚点过通知的 App | Android 16 起约 `20 min / 60 min`，Android 15 及更早没有这条显式上限 | 约 `30 min / 24h` | 不限 | 不限 |
| Working set | 经常使用，但当前不在前台 | 约 `10 min / 4h` | 约 `15 min / 24h` | `10 次 / 小时` | 不限 |
| Frequent | 会规律使用，但不是每天都打开 | 约 `10 min / 12h` | 约 `10 min / 24h` | `2 次 / 小时` | 不限 |
| Rare | 很少打开 | 约 `10 min / 24h` | 约 `10 min / 24h` | `1 次 / 小时` | 后台禁用 |
| Restricted | Android 12 引入，系统认为资源消耗异常或长期不互动 | 每天 1 次，最多 10 分钟，且与其他 Job 合批 | `5 min / 24h` | `1 次 / 天` | 后台禁用 |

Android 16 还改变了一个常见判断：FGS 运行期间启动的 regular job 仍会消耗 Job quota。`Active` 桶不再等于后台任务无限额；如果业务依赖 FGS 包住 Job 执行，需要用 `dumpsys jobscheduler <pkg>` 查看 quota 用量，不能只看 App 是否处于 Active。

Restricted 桶的触发条件要按版本拆开。Android 12 / 12L 的“不互动”阈值是 45 天，Android 13 起缩短到 8 天；设备关机的时长不计入这段天数。Android 13 以后，高优先级 FCM 配额也不再由桶直接决定。

除了桶配额之外，Android 15 引入了独立的能效维度。当系统判断当前能量预算不足（例如设备未充电且电量持续下降），即使 App 还在 Active 桶，Job 也可能因能效原因被挂起。排查时用 `adb shell dumpsys jobscheduler <pkg>` 查看 pending reason，可关注 `PENDING_JOB_REASON_DEVICE_STATE`（设备状态不适宜执行）、`PENDING_JOB_REASON_JOB_SCHEDULER_OPTIMIZATION`（系统优化决策）和 `PENDING_JOB_REASON_QUOTA`（配额耗尽）三类标识。不要把这些 pending 直接等同于"桶配额用完"——它们对应的是不同层面的约束。


### 桶的动态分配：Adaptive Battery 的角色

App 不会被固定在某个桶里。系统会根据用户行为持续调整。这个分配决策背后是 Android 9 引入的 **Adaptive Battery** 机制。

Adaptive Battery 使用一个运行在本地的机器学习模型来预测用户在未来几小时内可能使用哪些 App。[待验证：部分来源提及基于 TensorFlow Lite 的 CNN + 前馈网络架构，但具体网络结构未在 AOSP 源码或官方文档中确认] 模型基于以下信号做预测：

- App 的历史启动频率和时间分布
- App 在前台的使用时长
- App 的通知交互情况（用户是否点击通知打开 App）
- 设备的整体状态（时间、位置等）

所有训练数据都在设备本地处理，个人身份信息在训练前被移除。模型的输出直接用于决定 App 应该被放入哪个 Standby Bucket。对于模型预测"用户近期不会打开"的 App，系统会将其放入更低优先级的桶，从而限制它的后台资源消耗。

这解释了一个常见的开发困惑："我的 App 昨天后台任务还正常，今天就执行不了了。"原因可能是 Adaptive Battery 根据用户几天的使用模式，将 App 从 Working Set 降到了 Rare 桶。


### Bucket、Quota、Power Saver 的归属关系

Android 13 到 Android 16 的功耗策略分散在多个控制器中。排查后台任务问题时，需要先分清是 bucket 降级、quota 耗尽、device idle 触发还是全局 Battery Saver 打开——它们的证据入口各不相同。

| 机制 | 控制器 | Android 16 入口 | 开发者验证入口 |
|------|--------|-----------------|----------------|
| Doze / Device Idle | `DeviceIdleController` | `frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java` | `adb shell dumpsys deviceidle`，再和 Trace 的 `suspend_resume` / `cpu_idle` 对时 |
| App Standby Bucket 评估 | `AppStandbyController` | `frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java` | `adb shell am get-standby-bucket <pkg>`，`adb shell dumpsys usagestats appstandby` |
| Usage 统计与事件上报 | `UsageStatsService` | `frameworks/base/services/usage/java/com/android/server/usage/UsageStatsService.java` | `adb shell dumpsys usagestats` |
| Job quota 执行 | `JobSchedulerService` | `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java` | `adb shell dumpsys jobscheduler <pkg>`，Android 16 可再看 `getPendingJobReasons()` |
| Battery Saver / low power mode | `PowerManagerService` | `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java` | `adb shell settings get global low_power`，`adb shell dumpsys power`，App 侧用 `PowerManager.isPowerSaveMode()` |

看到后台任务没跑时，先分清是 bucket 变低、quota 用完、device idle 命中，还是全局 Battery Saver 打开；四种情况的证据入口并不相同。

### 如何在开发中应对 Standby Buckets

了解了 Buckets 机制后，我们的策略应该是：

1. **不要试图影响 Bucket 分配**——这是系统根据用户行为自动决定的，API 层面没有"请把我放到 Active 桶"的调用
2. **适配而非对抗**——确保 App 在每个桶的限制下都能正常工作，尤其是 Rare 和 Restricted 桶
3. **测试覆盖**——使用 ADB 命令模拟不同桶的状态：
   ```bash
   # 将 App 设置为 Rare 桶
   adb shell am set-standby-bucket com.example.app rare
   # 查看当前桶
   adb shell am get-standby-bucket com.example.app
   ```
4. **使用 WorkManager 而非直接使用 JobScheduler**——WorkManager 内部已经处理了 Standby Bucket 的配额差异

## 系统级限后台策略

Doze 和 Standby Buckets 会根据设备状态和用户行为限制后台活动。除此之外，Android 还有一类更直接的后台限制，不管设备状态如何，都会生效。这些限制从 Android 8.0 开始逐步加强，到 Android 14 已经形成了一套比较完整的后台管控体系。

### Background Activity Starts 限制

从 Android 10（API 29）开始，后台 App 不能随意 `startActivity()`。Android 14 之后，这条限制对 `PendingIntent` 也从“默认沿用例外场景”改成了“显式 opt-in”。

如果后台 App 作为 `PendingIntent` 的发送方想拉起 Activity，targetSdk 34+ 需要在 `PendingIntent.send()` 时附带 `ActivityOptions`，并调用 `setPendingIntentBackgroundActivityStartMode(...)`。Android 14 和 Android 15 使用 `MODE_BACKGROUND_ACTIVITY_START_ALLOWED`；Android 16 把它拆成 `MODE_BACKGROUND_ACTIVITY_START_ALLOW_IF_VISIBLE` 和 `MODE_BACKGROUND_ACTIVITY_START_ALLOW_ALWAYS`，默认仍是不授予这项能力。

如果 App 是 `PendingIntent` 的创建方，targetSdk 35+ 也不能再默认把这项能力连同 `PendingIntent` 一起交出去。需要在 `PendingIntent.getActivity()` 等创建点通过 `setPendingIntentCreatorBackgroundActivityStartMode(...)` 明确授予。

这里没有新增 manifest 权限，也不是运行时权限。变化点是 `ActivityOptions` 的显式授权模式。

常见豁免场景包括：

- App 当前有可见窗口，或者刚刚结束一个可见 Activity
- 用户刚刚完成明确交互，例如点击通知里的 Activity `PendingIntent`
- 系统绑定服务或可见 App 绑定服务，并通过对应 opt-in 授予后台拉起 Activity 的能力；Android 14+ 可见 App 绑定时要使用 `BIND_ALLOW_ACTIVITY_STARTS`
- App 是当前输入法、`VoiceInteractionService`、设备所有者等系统认可角色

前台服务通知本身不是通用豁免。它能提示用户 App 正在工作，但不能单独授予后台拉起 Activity 的能力。


### 后台定位限制

位置信息本身耗电高，平台对“后台取位置”的限制也越来越明确，排查时要把权限、可见性和前台服务拆开看：

**Android 8.0（API 26）**——后台 App 的位置更新频率被限制为“每小时几次”，与 targetSdkVersion 无关。

**Android 10（API 29）**——引入 `ACCESS_BACKGROUND_LOCATION`。应用如果要在不可见状态下持续取位置，需要单独申请这项权限；仅有 `ACCESS_COARSE_LOCATION` / `ACCESS_FINE_LOCATION` 只覆盖 while-in-use 场景。

**Android 11（API 30）**——前台服务不再被当成后台位置权限的替代品。应用退到后台后，如果用户没有授予“始终允许”，location access 仍然拿不到。

**Android 14（API 34）**——系统在创建 `location` 类型的 foreground service 时就会检查前置条件。若应用已经在后台，且用户只给了 while-in-use 位置权限，启动这类服务可能直接抛 `SecurityException`。如果应用此时有可见 Activity，并且已经拿到前台位置权限，则可以启动 location FGS；只有“后台持续取位置”这条路径才要求 `ACCESS_BACKGROUND_LOCATION`。Manifest 里还要声明 `android:foregroundServiceType="location"` 和 `FOREGROUND_SERVICE_LOCATION`。

对性能优化的影响是：轨迹记录、后台导航、地理围栏回传这类场景，要把权限流程、前后台状态和 FGS 生命周期一起设计。否则在新系统上，问题看起来像定位偶发失效，根因往往是权限条件没有配齐。


### 后台服务限制（Android 8.0+）

Android 8.0（API 26）对后台服务做了关键限制：**当 App 处于后台超过几分钟，系统不再允许它创建后台服务**。已有的后台服务会在几分钟内被停止。

这让 `JobScheduler` 和后来的 `WorkManager` 成为后台任务的首选方案。如果 App 需要在后台持续执行任务，必须使用前台服务（Foreground Service），它会显示一个持续通知告知用户。但这也会增加功耗和用户的感知负担。

Android 14 对前台服务进一步增加了限制：某些类型的前台服务（如位置相关的）需要声明特定的前台服务类型（foreground service type），并在 Manifest 中声明对应权限。


### App Archiving：物理清除而非冻结（Android 15+）

上述限制——Doze 推迟任务、Standby Buckets 压缩配额、Restricted 桶限制后台活动、厂商冻结进程——都仍然保留着 App 的安装状态和数据。Android 15 引入了更激进的手段：**自动归档（Auto-Archiving）**。

当设备存储空间紧张且用户长时间未使用某个 App 时，系统可以自动归档该 App。归档操作会：
- 移除 APK 文件和缓存，释放大部分存储空间
- 保留用户数据（账号、偏好、本地数据库）
- 在 Launcher 中保留灰色图标，点击后从 Play Store 重新下载安装

与 Restricted 桶和厂商冻结相比，App Archiving 不是"暂停执行"而是"物理清除"。归档后的 App：
- 不再占据运行时资源（没有进程、没有 WakeLock、没有 Job）
- 取消所有已注册的定时任务和通知监听
- 不再接收 FCM 或厂商推送

开发者不需要为归档做特殊适配——系统保证用户数据不丢、恢复后状态一致。但需要了解归档的存在，因为用户反馈"我的 App 不见了"可能不是卸载而是归档。排查路径是按包名查询 `adb shell pm get-archived-package-metadata <package>`（Android 15+），或用 `adb shell pm list packages -u --show-versioncode` 查看已卸载但保留数据的应用。后者不等于 archived 列表，但能覆盖未安装/保留数据的包。


## 省电模式下的系统行为变化

上面讨论的 Doze 和 Standby Buckets 是系统自动触发的。省电模式（Battery Saver）则是由用户手动开启（或系统在电量低于一定阈值时建议开启）的更激进的功耗管理策略。

### 省电模式的核心行为

Battery Saver 是全局 low power mode，由 `PowerManagerService` 统一发布状态，各子系统再决定要不要限制对应能力。它不会把所有 App 的桶标签改写成 Rare，也不等于“后台一律断网”。

在 AOSP 这层，能稳定确认的影响主要有四类：

- **后台执行更保守**：Job、Alarm、网络和同步会把 low power mode、standby bucket、设备是否充电、进程重要性一起算进去。排查时要把这几层分开看。
- **位置策略会变化**：App 可以用 `PowerManager.getLocationPowerSaveMode()` 查看系统当前采用的节电位置策略。常见模式是屏幕熄灭后限制定位，而不是所有设备都完全关掉定位。
- **App 能收到显式状态信号**：App 可通过 `PowerManager.isPowerSaveMode()` 和 `ACTION_POWER_SAVE_MODE_CHANGED` 调整自己的轮询、上报和动画策略。
- **厂商可以继续加码**：刷新率、GPU 频率、传感器、Motion Sense、Crash Detection 这类行为取决于设备实现，不能当成 Android 通用基线。

涉及 Pixel 或 OEM 机型的显示降频、传感器关闭、特殊安全功能收缩时，最好把机型、ROM 版本和来源写在同一段；拿不到来源，就保留 `[待验证]`。


### 自适应省电（Adaptive Battery Saver）

这里需要区分两个容易混淆的机制：

- **Adaptive Battery**（Android 9 引入）：运行在本地的 ML 模型预测用户对各个 App 的使用频率，输出直接影响 App Standby Bucket 分配。它影响的是单个 App 的后台资源配额（Job、Alarm、网络），不是全局省电开关。
- **Routine Battery Saver**（Android 10 引入）：根据用户的日常充电习惯（比如"每天晚上 11 点充电"），在电量低于阈值且用户不太可能使用设备时自动启用 Battery Saver。OEM 需要通过 `config_batterySaverScheduleProvider` 配置一个 provider app 来提供调度策略；AOSP 默认不提供这个 provider，所以是否默认开启取决于 OEM 实现而非 Android 版本。

两者共享用户行为数据作为输入，但作用层面不同：Adaptive Battery 影响单个 App 的后台配额（微观），Routine Battery Saver 决定全局省电模式的开关（宏观）。

### 在 Perfetto 中观察省电模式

省电模式也不要靠“PowerManagerService Track”这种名字判断。更稳的取证方式，是把 `low_power` 状态、CPU / 调度变化和任务延迟放到同一时间线上。

建议的组合是：

- 先记一份状态快照，至少保留 `adb shell settings get global low_power` 和 `adb shell dumpsys power`
- Trace 打开 `sched/*`、`power/cpu_frequency`、`power/cpu_idle`、`power/suspend_resume`，再补 `am`、`wm`、`view`、`power` 这些 framework 侧 category
- 如果怀疑是后台任务被压缩，再把 `dumpsys jobscheduler`、`dumpsys alarm`、Battery Historian 一起留档

一段能说明问题的证据，通常包含三部分：`low_power` 从 0 变 1 的时间点；CPU 频率上限和后台 runnable slice 密度同时下降；Job / Alarm 触发节奏变稀或被合批。


### 对 App 性能分析的影响

当我们在做性能测试和分析时，省电模式是一个必须控制的变量。如果测试时设备处于省电模式，所有的帧率、启动时间、滑动流畅度数据都会偏慢，可能导致错误的优化方向。

建议的做法：

- 性能测试前确认设备未开启省电模式
- 使用 `adb shell settings put global low_power 0` 确保省电模式关闭
- 在测试报告中注明设备是否开启了省电模式

## 厂商级功耗管理：Android 生态中的"灰色地带"

AOSP 提供的功耗管理机制（Doze、Standby、省电模式）只是“官方基线”。在中国市场，几乎所有主流厂商都会在此基础上叠加自研的、更激进的后台管控策略。这些策略通常不在 AOSP 代码中，也不遵循标准的 Standby Bucket 配额，是 Android 碎片化问题中最让开发者头疼的一环。

网站 dontkillmyapp.com 专门跟踪了各大厂商的后台杀进程行为，并给出了"杀伤力"评分，从侧面反映了这个问题的严重性。

### 小米（MIUI / HyperOS）

小米的功耗管理在业界以"激进"著称：

**自启动管理**——默认禁止所有 App 自启动（开机自动运行和被其他 App 唤醒）。用户需要手动为每个 App 开启"后台自启动"权限。如果 App 的核心功能依赖自启动（如消息推送的长连接），会直接受到影响。

**后台冻结**——MIUI 的 `com.miui.powerkeeper` 服务会在后台持续扫描 App 活动。对于被标记为"可优化"的 App，系统会在它们进入后台一段时间后（通常 10 分钟左右）直接冻结进程，使其无法执行任何代码。

**电池优化策略**——在设置 → 电池 → 应用智能省电中，用户可以为每个 App 选择"无限制"、"智能限制"或"后台运行 10 分钟后限制"。默认选择通常是"智能限制"。

**应对策略**：对于需要后台持续运行的 App（如即时通讯、导航），需要在文档中引导用户：将 App 设为"无限制"电池策略、在最近任务界面锁定 App、开启自启动权限。

### 华为（EMUI / HarmonyOS）

华为的功耗管控同样以严格闻名：

**应用启动管理**——设置 → 电池 → 应用启动管理中，华为为每个 App 提供了"自动管理"和"手动管理"两种模式。自动管理模式下，系统会根据使用频率决定是否允许 App 在后台运行。手动管理模式允许用户分别控制"自启动"、"关联启动"和"后台活动"三个开关。

**PowerGenie**——公开机型经验里，PowerGenie 常被当作华为 ROM 的后台清理与限活跃策略之一。它会主动扫描长期不活跃的后台进程。面向普通用户的处理路径通常还是系统设置里的电池优化、应用启动管理和后台活动开关；部分开发者会用 `adb shell pm uninstall -k --user 0 com.huawei.powergenie` 做实验隔离，但这只是调试手段，不是所有版本都适用的通用解法。

**超级省电模式**——极端省电模式下，系统只保留电话、短信等核心功能，所有第三方 App 被暂停。

### OPPO / vivo（ColorOS / OriginOS）

OPPO 和 vivo 的策略类似：

**应用冻结/睡眠**——ColorOS 的"睡眠待机优化"会在设备空闲时限制后台 App 活动。在电池管理中，用户可以为每个 App 设置"允许后台活动"开关。

**自启动管理**——与小米类似，默认禁止 App 自启动。需要在"手机管家"或"安全中心"中手动开启。

**关联启动限制**——限制 App 之间的相互唤醒（A App 启动后拉起 B App），这是国内厂商特有的管控维度。

### 厂商策略对性能分析的影响

做功耗和后台行为分析时，厂商策略的影响主要体现在：

1. **后台任务执行不稳定**——同一个 WorkManager 任务，在 Pixel 上能按时执行，在小米上可能被推迟数小时，根因通常是厂商的进程冻结策略。
2. **推送延迟**——FCM 在国内不可用，App 通常使用厂商推送通道（小米推送、华为推送等）或第三方推送（如极光推送）。这些推送通道能否正常工作，取决于 App 是否被厂商系统"放行"。
3. **功耗数据差异巨大**——同一 App 在不同厂商设备上的电池消耗报告可能差 3-5 倍，大部分差异来自厂商的后台管控策略，而非 App 本身的行为差异。

**分析建议**：

- Trace 里优先看 `sched/*`、`power/cpu_frequency`、`binder_driver`、`am`，确认进程是单纯没拿到 quota，还是进入了长时间不被调度的冻结状态。
- 同步保存 `dumpsys activity processes`、`dumpsys jobscheduler <pkg>`、`dumpsys alarm` 和厂商电池策略设置页。只有把系统状态和 Trace 对起来，才能分清是 AOSP bucket / quota 触发，还是 ROM 额外的后台冻结。
- 如果 Trace 中只剩 Binder / epoll wait，几乎没有 runnable slice，而同一时间窗口又看到了 pending job 或 delayed alarm，更像是厂商冻结或延迟分发，不要直接归因到 WorkManager。
- `Process State` 只能当辅助信号，不要把它当成所有设备都存在的固定 Track。


## 与其他机制的关系

系统级功耗管理并非孤立存在，它和全书讨论的多个机制都有交叉：

**与进程管理（§1.3）的关系**——LMK（Low Memory Killer）杀进程和厂商的后台杀进程策略是两套独立的机制，但它们会叠加影响。一个 App 可能先被厂商冻结，然后因为内存压力被 LMK 回收。

**与 CPU 调度与功耗管理（§5.6）的关系**——§5.6 讨论的是 CPU 调度层面的功耗优化（EAS、UClamp、Doze 底层的 Idle 状态管理）。本节讨论的是应用框架层的功耗策略，是 §5.6 底层机制的上层体现。当本节提到的省电模式导致 CPU 降频时，实际的频率限制通过 §5.6 中讨论的 cpufreq 机制执行；Doze 模式下 CPU 进入深度 Idle 状态，对应的也是 §5.6 中介绍的 CPU Idle 状态管理。

**与 App 耗电优化（§11.2）的关系**——§11.2 是"App 主动配合"，本节是"系统强制约束"。两者是互补关系：即便 App 做好了所有主动优化，系统策略仍然会限制它的后台行为。

**与 Perfetto 工具（§13.1-13.7）的关系**——分析系统级功耗限制时，Perfetto 是最核心的工具。通过 Trace 能观察到进程调度状态、CPU 频率变化、网络活动窗口等信息，帮助区分问题来自 App 自身还是系统策略。

## 版本演进

系统级功耗管理在不同 Android 版本中的演进路径：

| 版本 | 关键变化 |
|------|---------|
| Android 6.0 (API 23) | 引入 Doze 模式和 App Standby |
| Android 7.0 (API 24) | 拆分为 Light Doze 和 Deep Doze |
| Android 8.0 (API 26) | 限制后台服务创建、限制后台定位频率、限制隐式广播 |
| Android 9 (API 28) | 引入 App Standby Buckets（四桶：Active/Working/Frequent/Rare）、Adaptive Battery |
| Android 10 (API 29) | Background Activity Starts 限制、`ACCESS_BACKGROUND_LOCATION` 权限 |
| Android 11 (API 30) | 前台服务也不能无权限获取后台位置 |
| Android 12 (API 31) | 新增 Restricted 桶、Exact Alarm 需要声明权限 |
| Android 13 (API 33) | Restricted 桶触发条件从 45 天缩短到 8 天、FCM 配额不再与桶绑定 |
| Android 14 (API 34) | PendingIntent 后台启动改为显式 opt-in API、前台服务类型强制声明 |
| Android 15 (API 35) | App Archiving（自动归档）：存储紧张时物理清除长期未用 App 的 APK 和缓存，保留用户数据；能效维度纳入 Job 调度决策（`PENDING_JOB_REASON_DEVICE_STATE` / `JOB_SCHEDULER_OPTIMIZATION`），Job 因能量预算不足被挂起直至条件改善 |
| Android 16 (API 36) | Active 桶开始引入 regular job 指导额度（约 20 min / 60 min），并补充 Job pending reason introspection |


## 常见问题与误区

### "后台被杀是 Android 的 Bug"

不是。Android 的后台管控策略是有意为之。Doze、Standby Buckets、省电模式都是系统为了延长电池续航而设计的正常机制。厂商的后台管控虽然更激进，但也是在其 ROM 中有明确设置项供用户调整的。正确的心态是：理解这些机制，适配它们，而不是对抗它们。

### "WorkManager 能保证任务一定执行"

WorkManager 保证的是"最终一致性"——任务最终会被执行，但不保证在什么时候执行。在 Rare 或 Restricted 桶中，WorkManager 任务可能被推迟数小时甚至一天。如果业务需要精确的时间控制，需要结合前台服务或其他手段。

### "用户不会手动调整电池设置"

用户手动调整电池设置的比例并不低。尤其当系统提示“XX App 正在耗电”时，用户很可能会选择“限制”。我们的 App 也就可能随时从 Active 桶被手动降到 Restricted 桶，因此需要在设置页或帮助文档里说明后台运行权限的用途。

### "Doze 只在晚上才会生效"

不完全准确。Deep Doze 需要设备静止，但 Light Doze 只要屏幕关闭且未充电就会触发。如果用户习惯性地锁屏但不充电（比如开会时），Light Doze 在白天也会频繁生效。

### "国产厂商的后台管控都是负面的"

厂商的激进后台管控会给开发者带来适配负担，但从用户角度看，它也在换取更长的续航。更实际的做法是理解这些策略，并告诉用户如何在系统设置里放行我们的 App。

## 参考资料

### AOSP 源码路径

- `frameworks/base/apex/jobscheduler/service/java/com/android/server/DeviceIdleController.java` — Doze / Device Idle 状态机
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/usage/AppStandbyController.java` — App Standby Bucket 评估
- `frameworks/base/services/usage/java/com/android/server/usage/UsageStatsService.java` — usage 统计与事件上报
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java` — Job quota 与 pending reason
- `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java` — Battery Saver / low power mode
- `frameworks/base/core/java/android/app/ActivityOptions.java` — PendingIntent 后台启动 opt-in API
- `frameworks/base/core/java/android/os/PowerManager.java` — `isPowerSaveMode()` / `getLocationPowerSaveMode()`

### 官方文档

- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [About App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Power management resource limits](https://developer.android.com/topic/performance/power/power-details#app-stdby-bucket)
- [Power usage optimization](https://developer.android.com/topic/performance/power)
- [Background execution limits](https://developer.android.com/about/versions/oreo/background)
- [Restrictions on starting activities from the background](https://developer.android.com/guide/components/activities/background-starts)
- [Request background location](https://developer.android.com/training/location/background)
- [Android power management](https://source.android.com/docs/core/power)

### 其他参考

- [Don't kill my app!](https://dontkillmyapp.com/) — 各厂商后台管控策略追踪
