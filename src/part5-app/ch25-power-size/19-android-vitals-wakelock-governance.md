---
title: "Android Vitals 过度 WakeLock 指标与治理"
chapter: "25.19"
section: "25.19"
status: finalized
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); Google Play Android vitals wake lock metric checked 2026-07"
last_verified: "2026-07-09"
last_verified_against: "Android Developers excessive/stuck/identify wake lock docs checked 2026-07-09, Android Developers Blog 2025-10-02, AOSP android-17.0.0_r1"
confidence: high
tags: [power, wakelock, android-vitals, battery, play-console]
related_chapters: ["11.5", "25.2", "25.3", "25.13", "25.14", "26.3", "26.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/Clippings结构参考/已有队列缺口"
gap_score: 17
material_count: 8
sources:
  - type: clippings-structure
    path: "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md]"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/stuck-wakelock"
  - type: official-blog
    path: "https://developer.android.com/blog/posts/optimize-your-app-battery-using-android-vitals-wake-lock-metric"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/set"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls"
  - type: official
    path: "https://developer.android.com/topic/performance/power/setup-battery-historian"
  - type: official
    path: "https://developer.android.com/tools/dumpsys"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java"
pipeline_stage: ready-to-publish
task2a_result: draft-ready-for-review
last_task2a_at: "2026-05-25T06:04:00+08:00"
task6_state: reviewed
task9_state: reviewed
reviewed_by: "openclaw-task6"
reviewed_date: 2026-07-09
task6_result: pass-light-edit
last_task6_at: "2026-07-09T09:11:00+08:00"
last_task6_audit: "2026-07-09"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-09"
last_task9_at: "2026-07-09T08:27:37+08:00"
last_task9_autofix_at: "2026-07-09"
last_task9_review_log: "logs/deep-review/2026-07-09-08-deep-review.md"
task9_review_notes: "2026-07-09 Task9：复核 Android 17/AOSP 与当前 Android Developers 文档；auto-fix JobScheduler/WorkManager tag 版本差异、batterystats checkin 命令和 Play policy beta 旧口径，回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-09
last_task9_audit: "2026-06-22"
last_task9_audit_at: "2026-06-22T15:25:24+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-22-15-audit.md"
last_task9_audit_result: "pass-idle-audit"
task2b_result: fixed-lite
task2b_state: fixed
last_task2b_lite_at: "2026-07-09"
---

# 25.19 Android Vitals 过度 WakeLock 指标与治理

## Android Vitals WakeLock 的治理范围

25.3 节已经覆盖 `PowerManager.WakeLock` 和 Alarm 的 API 使用，11.5 节覆盖系统 WakeLock 机制。这里处理一个更窄的工程问题：Play Console 报出 excessive partial wake lock 后，团队怎样判断影响范围，又怎样把一个 wake lock tag 追到业务代码、平台 API 或第三方 SDK。

先划清边界：Android Vitals 是 Google Play 的质量指标，不是 Android 17 framework 的运行时限制。它能给出非豁免 tag、受影响会话和持有时长，却不会提供完整调用栈、任务参数、业务 trace id 或 SDK 版本。排查时需要把 Play Console、端侧日志、`batterystats` 和系统 trace 放在一起看。

## 指标口径：Android Vitals 统计的是非豁免 partial wake lock

移动设备上的 excessive partial wake lock 指标只累计同时满足以下条件的时间：

- 锁类型是 partial wake lock；
- 该锁不在 Vitals 的豁免范围内；
- 屏幕关闭；
- 应用位于后台，或者正在运行 foreground service。

在一个 24 小时周期内，所有符合条件的 partial wake lock 相加达到 2 小时，即记为一次 excessive 会话。按 28 天计算，如果问题影响超过 5% 的应用会话，应用在 Play 上的可见度可能受到影响。这里的“相加”很重要：十几个短锁也可能累积越线，不要求某一个 tag 连续持有 2 小时。

| 维度 | Android Vitals excessive 口径 | 工程排查建议 |
| --- | --- | --- |
| WakeLock 类型 | 非豁免 partial wake lock | 所有 partial wake lock 都可纳入排查 |
| 设备与应用状态 | 熄屏，且应用在后台或运行 FGS | 同时记录交互状态、进程状态、FGS 类型和充电状态 |
| 时间口径 | 24 小时内累计达到 2 小时 | 同时观察单次时长、累计时长、频次和重叠区间 |
| Play 质量阈值 | 28 天内影响超过 5% 的应用会话 | 依据自身基线设置更早的灰度告警 |
| Play 证据 | tag、受影响会话和持续时间 | 再补调用栈、任务、SDK、版本和设备信息 |

“不计入 Vitals”与“耗电合理”不是同一结论。豁免锁仍可能造成设备发热、待机下降或厂商后台限制，本地监控不应删除这部分数据。

## Stuck 与 excessive 是两类告警

Stuck partial wake lock 关注单次长持有：24 小时内出现至少一次在后台持续 1 小时的 partial wake lock。Excessive partial wake lock 关注累计量：多个短锁在 24 小时内累计达到 2 小时，也会命中。

| 告警 | 触发形态 | 常见原因 | 处理方向 |
| --- | --- | --- | --- |
| Stuck | 某一次持有达到 1 小时 | 异常路径漏释放、回调未返回、状态机停滞 | 检查该次 acquire/release 配对和超时保护 |
| Excessive | 多次持有累计达到 2 小时 | 后台轮询、连续重试、SDK 间接持锁、任务过于零碎 | 减少任务频次，合并工作，改用系统调度 API |

因此，本地指标至少要同时保留“单次最长时长”和“窗口累计时长”。只看单次时长会漏掉高频短任务，只看累计时长又会延迟发现未释放缺陷。

## 豁免边界：豁免的是 API 创建的锁

当前官方口径豁免 audio API、location API 和 JobScheduler user-initiated API 创建的 wake lock。豁免跟“由哪个 API 创建”有关，不跟业务给手动锁起了什么名字有关。应用在音频、定位或用户发起传输流程中自行调用 `PowerManager.newWakeLock()`，不会因为用途相似而自动获得豁免。用 `Audio...` 作为手动 tag 也不能改变归因结果。

按创建者和生命周期区分责任：

| 场景 | 推荐处理 | 排查重点 |
| --- | --- | --- |
| 音频 | 让媒体栈管理所需的锁；播放结束时关闭 session 和对应 FGS | 暂停、播放完成、路由切换后资源是否停止 |
| 定位 | 使用定位 API 的超时、批处理、被动定位和精度选项 | 请求频率、回调处理时长、任务结束后是否移除请求 |
| JobScheduler 用户发起任务 | 使用 user-initiated job 或 UIDT API 表达用户发起传输 | stop reason、超时、网络约束和失败重试 |
| WorkManager / 普通 JobScheduler | 让系统管理执行窗口，不额外叠加手动锁 | 周期、约束、重试和任务能否及时结束 |
| 手动 `PowerManager.WakeLock` | 仅用于其他平台 API 无法表达的短暂防 suspend 区间 | timeout、`finally`、取消路径、所有权和 tag |

Foreground service 也不是豁免项。Vitals 明确统计应用运行 FGS 时的非豁免 partial wake lock；FGS 通知只让用户知道任务正在运行，不能替代必要性判断。

## 归因路径：Play Console 给 tag，端侧补堆栈

Play Console 的常用入口是 wake lock 名称。手动锁应使用稳定的常量字符串，包含足够的 package、feature 或 task 信息。不要把邮箱、手机号、用户 ID、订单号等个人信息写入 tag，不要加入随机数或递增计数器，也不要用 `Class.getName()` 生成可能被 R8 改写的名称。调试工具怀疑 tag 含个人信息时，可能只显示 `_UNKNOWN`；每次生成唯一 tag 还会让相同调用点无法聚合。

下面三个 tag 展示了可聚合、可搜索的命名方式：

```text
com.example.sync:message-refresh
com.example.media:upload-session
com.example.ble:firmware-transfer
```

这些名称不携带一次任务的动态 ID。需要定位单次执行时，把业务 trace id 放入应用日志，再用时间戳与 wake lock 事件关联。

系统或库创建的锁也可能记在应用名下。`AlarmManager` 在 alarm 到达时以调用应用归因持有 `*alarm*`，并在广播的 `onReceive()` 返回后释放；因此不要在 `onReceive()` 中执行长任务。JobScheduler 的 tag 随系统版本和任务类型变化：

| 系统版本 | JobScheduler 类型 | tag 形态 |
| --- | --- | --- |
| Android 15 及以下 | 用户发起 | `*job*u/@<namespace>@/<package>/<class>` |
| Android 15 及以下 | 其他 job | `*job*/@<namespace>@/<package>/<class>` |
| Android 16 QPR2 至 Android 17 | 用户发起 | `*job*u/@<namespace>@/#<trace_tag>#/<package>/<class>` |
| Android 16 QPR2 至 Android 17 | expedited | `*job*e/@<namespace>@/#<trace_tag>#/<package>/<class>` |
| Android 16 QPR2 至 Android 17 | regular | `*job*r/@<namespace>@/#<trace_tag>#/<package>/<class>` |

WorkManager 的格式不同：

| 系统版本 | WorkManager 类型 | tag 形态 |
| --- | --- | --- |
| Android 15 及以下 | 所有 worker | `*job*/<package>/androidx.work.impl.background.systemjob.SystemJobService` |
| Android 16 QPR2 至 Android 17 | expedited | `*job*e/#<trace_tag>#/<package>/androidx.work.impl.background.systemjob.SystemJobService` |
| Android 16 QPR2 至 Android 17 | regular | `*job*r/#<trace_tag>#/<package>/androidx.work.impl.background.systemjob.SystemJobService` |

在 Android 16 QPR2 及以上，WorkManager 默认用 worker 名称作为 `trace_tag`；官方示例要求 WorkManager 2.10.0 或更高版本。看到 `*job*` tag 时，搜索同名字符串往往没有结果，应回查 worker/job 类、任务 ID、约束、重试次数和 `getStopReason()`。

## Android 17 源码路径：保持唤醒与电量归因是两条线

在 `android-17.0.0_r1` 中，应用进程里的 `PowerManager.WakeLock.acquire()` 通过 Binder 调到 `PowerManagerService.acquireWakeLockInternal()`。服务端以 Binder token 为键创建或更新 `mWakeLocks` 中的记录，设置 `DIRTY_WAKE_LOCKS` 后调用 `updatePowerStateLocked()`。

`updatePowerStateLocked()` 会重新计算 `mWakeLockSummary`。只要摘要中还包含 `WAKE_LOCK_CPU`，`updateSuspendBlockerLocked()` 就持有服务级 `mWakeLockSuspendBlocker`；所有相关条件消失后才释放它。也就是说，framework 保存每个应用锁的 tag、UID、flags 和 `WorkSource`，但 CPU 防 suspend 在这一层是汇总状态，不能把 Play 中的每个应用 tag 理解为同名的一把独立 kernel wake lock。

记账经由 `notifyWakeLockAcquiredLocked()` 进入 `Notifier`。`Notifier` 根据是否存在 `WorkSource`，调用 `BatteryStatsService.noteStartWakelock()` 或 `noteStartWakelockFromSource()`；停止时调用对应的 `noteStop...()`。因此归因可能落在 owner UID，也可能按 `WorkSource` 转移到实际工作 UID。

这条源码路径给出了观测边界：系统统计能保留 tag、UID、类型、`WorkSource` 和时间，业务参数、调用栈、SDK 版本仍需应用自行记录。进程死亡时 Binder death 会促使服务端移除记录，这个兜底不能替代正常路径的 `release()`；依赖进程死亡收回锁，意味着任务生命周期已经失控。

## 本地验证：复现 Vitals 的状态条件

本地验证要复现 Vitals 关心的状态：测试区间由电池供电、屏幕关闭，应用在后台或运行 FGS。只在亮屏前台点按钮，无法验证移动端 Vitals 的统计区间。

下面是一轮最小采集流程；`com.example.app` 需要替换为待测包名：

```bash
adb shell dumpsys batterystats --reset
adb shell am force-stop com.example.app
adb shell monkey -p com.example.app 1

# 触发目标任务，令应用进入后台并熄屏。
# 断开 USB，在电池供电状态下完成测试；随后重新连接设备采集。
adb shell dumpsys batterystats --charged com.example.app > batterystats.txt
adb shell dumpsys batterystats -c com.example.app > batterystats-checkin.csv
adb bugreport bugreport.zip
```

`--reset` 会清除既有统计，只应在专用测试机上执行。`--charged` 表示输出“自上次充满电以来”的数据，并不是“只输出未充电时段”。`-c` 输出当前统计的 checkin 格式；不要把它换成 `--checkin`，后者还涉及读取并清除上一份已完成的旧统计。解析脚本要按目标 Android 版本做回归测试，不要假定各版本的 checkin 字段永远不变。

Battery Historian 可以把 bugreport 中的事件画成时间轴，但官方已经说明该工具不再积极维护；新排查流程应优先使用系统 trace、Power Profiler 或合适的功耗基准测试。Battery Historian 仍适合查看历史数据，以及核对屏幕、充电、进程和 wake lock 时间是否重叠。

对手动锁和 API 间接创建的锁，Perfetto 采集需启用 `power:PowerManagement` atrace category。打开 trace 后，重点对齐 Device State 下的 WakeLocks、Long Wake locks、Jobs、Screen state 与 Top app。Android 15（API 35）起还可用 `ProfilingManager` 在受限频率下采集现场系统 trace；系统进程和其他应用会被脱敏，所以仍需用应用事件补充业务关联。

## 治理策略：少持锁、短持锁、可观测持锁

评审手动 wake lock 时，先问 suspend 是否会破坏用户正在等待的任务，再问平台是否已有负责保持唤醒的 API。屏幕常亮使用 `WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON`；可延迟任务使用 WorkManager 或 JobScheduler；用户主动发起的长传输考虑 UIDT API；定位、音频和传感器优先采用各自 API 的超时、批处理与电量选项。只有其他平台能力无法表达、而 suspend 会直接中断用户任务的短区间，才保留手动 `PARTIAL_WAKE_LOCK`。

下面的同步封装展示了“一次 acquire 对应一次 release”，timeout 只作为保险：

```kotlin
inline fun <T> PowerManager.WakeLock.useFor(
    timeoutMillis: Long,
    block: () -> T,
): T {
    require(timeoutMillis > 0)
    acquire(timeoutMillis)
    return try {
        block()
    } finally {
        release()
    }
}
```

这段代码有两个前提：`block` 不自行释放同一把锁；同一个 `WakeLock` 实例不会被多个任务并发调用。异步任务应由单一所有者管理 acquire/release，并把取消、回调丢失和生命周期切换纳入同一状态机。

这里不能写成 `if (isHeld) release()`。Android 17 r1 的 `WakeLock` 同时维护 `mInternalCount` 和 `mExternalCount`：timeout 回调使用 `RELEASE_FLAG_TIMEOUT`，会减少内部计数并释放服务端状态，却不会减少调用方应配对的外部计数。业务结束时仍应执行一次 `release()`。无条件配对也消除了 `isHeld` 检查与 timeout 回调之间的竞态。

timeout 不是任务时限管理器。它只能限制 CPU 最长被该锁保持唤醒的时间；超时后工作线程仍可能继续运行，只是设备此时允许进入 suspend。任务自身还需取消、网络超时和结果状态。若预计任务可能超过 timeout，应重新设计任务边界，而不是循环续锁。

对 excessive 问题，减少唤醒频率往往比只压缩单次执行更有效。周期任务增加合理间隔和约束；网络重试使用指数退避并设停止条件；传感器使用 batching；定位优先读取缓存、使用被动定位并降低不必要的精度；Alarm 默认使用 inexact alarm，只有明确的用户时间承诺才使用 exact alarm。相关限制见 25.2、25.3 和 25.5。

## 线上监控：比 Vitals 多拿现场

内部监控应记录两组信息：资源状态包括时长、锁类型、应用状态、交互状态和充电状态；调用现场包括 tag、task type、业务 trace id、申请与释放栈的 hash、进程、版本、SDK 来源，以及 Worker/Job/Alarm 的标识。

上报策略分两层：

| 层级 | 触发条件 | 上报内容 |
| --- | --- | --- |
| 事件采样 | 每次 acquire/release 配对 | tag、任务、时长、状态、版本，低采样率 |
| 异常上报 | 单次超阈值、累计超阈值、未释放、FGS 停止后仍持锁 | 完整堆栈、trace id、最近任务事件、设备状态，高优先级 |

不要在缺少数据时照搬一个固定的内部分钟数。先从稳定版本统计单次时长、窗口累计时长和频次分布，再按业务任务的服务等级、历史分位数和灰度容错范围设置告警；配置值要按任务类型版本化，并说明为什么比 Play 的 2 小时门槛更早。灰度阶段同时比较新旧版本、设备和渠道分布，避免等 28 天窗口给出结果后才开始定位。

第三方 SDK 的 wake lock tag、版本、初始化入口和任务类型也要进入监控字段。无法解释的 `_UNKNOWN` 或动态 tag 需要在发布前定位；供应方至少应提供稳定命名、版本说明和停用开关。白名单只能标识负责人，不能让超长持锁从报表消失。

## 版本与 Play 分发影响

Google 在 2025-10-02 的 Android Developers Blog 中公告：自 2026-03-01 起，未满足 excessive wake lock 质量阈值的应用可能被排除在推荐等显著发现入口之外，部分商店详情页还可能展示耗电警告。当前官方页面给出的门槛仍是“28 天内影响超过 5% 的应用会话”。这是已经生效的 Play 质量信号，具体状态以 Play Console 为准。

| 分发场景 | Vitals 可用性 | 治理策略 |
| --- | --- | --- |
| Google Play | 可查看 Android Vitals wake lock 面板 | 用 Vitals 判断分发风险，用内部监控补调用现场 |
| 国内应用商店 | 通常没有 Play Vitals 数据 | 自建后台耗电指标，结合厂商耗电榜和用户反馈 |
| 企业分发或预装 | Play 指标可能缺失 | 依据厂商规则、bugreport 和实验室待机测试评估 |
| 小流量灰度 | 28 天会话样本可能不足 | 重点比较新旧版本的分位数、stuck 次数和累计时长 |

## Alarm、Wi-Fi scan、background network 要放在同一套规则里

WakeLock 很少单独出现。后台 Alarm 会唤醒 CPU，任务执行期间可能继续持有 partial wake lock；WorkManager 和 JobScheduler 会在执行窗口内代表应用持锁；Wi-Fi scan、定位和网络重试又会延长设备 active 时间。单独降低某个 tag 的时长，但把工作迁移为更频繁的 alarm，不一定改善待机。

发布报表应按版本并列展示后台唤醒次数、partial wake lock 累计时长、单次最长持锁、后台网络活跃时间、Wi-Fi scan 次数、FGS 总时长和 WorkManager 重试次数。单项没有命中门槛而多项同时上升，仍需检查后台任务设计。相关内容见 25.2、25.3、25.14 和 26.15。

## 厂商后台限制与 Play 阈值的差异

OEM 省电策略通常采用比 Play Vitals 更短的观察周期。Play 关注 28 天应用会话占比；厂商策略可能针对单设备、单晚待机、后台启动权限和省电白名单采取措施。国内渠道缺少 Vitals 数据时，需要同时收集用户反馈、系统耗电榜、厂商限制提示和实验室待机测试。

处理厂商差异时保留三类证据：bugreport 或 system trace 的系统时间线、应用侧 wake lock 事件、业务任务说明。用户可感知的 FGS 或定位任务应有明确展示与停止入口；后台轮询、保活和频繁拉取若没有可说明的用户收益，应删除或改用系统调度。

## 发布门禁清单

- Play Console：确认 excessive partial wake lock 会话占比、top tag、版本和设备分布。
- 本地复现：未充电、熄屏、后台/FGS 状态下采集 batterystats、bugreport、Perfetto。
- 代码约束：手动 wake lock 有明确所有者，带 timeout、`finally` 和稳定 tag，不共享给并发任务。
- 任务约束：WorkManager/JobScheduler 记录 stop reason、retry、约束和 job id。
- 线上监控：可以回查单次 stuck、24 小时累计、版本分位数、SDK 来源和任务现场。
- 发布策略：内部阈值有历史基线与业务依据，灰度异常阻止继续扩大范围。

Android Vitals WakeLock 治理要回答一组可以验证的问题：哪个 tag 由谁创建，归因到哪个 UID，在什么设备与应用状态下持有，哪个任务让 CPU 在熄屏后继续运行，修复版本是否同时降低单次时长和累计时长。

## 参考资料

- [Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [Stuck partial wake locks](https://developer.android.com/topic/performance/vitals/stuck-wakelock)
- [Identify and optimize wake lock use cases](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls)
- [Follow wake lock best practices](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices)
- [Debug wake locks locally](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/debug-locally)
- [Optimize your app battery using Android vitals wake lock metric](https://developer.android.com/blog/posts/optimize-your-app-battery-using-android-vitals-wake-lock-metric)
- [Profile battery usage with Batterystats and Battery Historian](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [PowerManager.WakeLock（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PowerManager.java#4326)
- [PowerManagerService（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/power/PowerManagerService.java#1740)
- [BatteryStatsService（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BatteryStatsService.java#1519)
