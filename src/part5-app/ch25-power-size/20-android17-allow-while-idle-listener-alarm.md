---
title: "Android 17 allow-while-idle Listener Alarm 与短生命周期唤醒治理"
chapter: "25.20"
section: "25.20"
status: finalized
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-25"
last_verified_against: "Android Developers AlarmManager API 37 / Schedule alarms / Android 14 exact alarm changes / Android 17 Beta 3 blog; AOSP main AlarmManagerService"
confidence: medium-high
tags: [power, alarmmanager, wakelock, android17, background-work]
related_chapters: ["11.5", "25.3", "25.14", "25.19"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/Android 17 API 变更/Clippings结构参考"
gap_score: 16
material_count: 5
sources:
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]"
  - type: official-blog
    path: "https://developer.android.com/blog/posts/the-third-beta-of-android-17"
  - type: official
    path: "https://developer.android.com/reference/android/app/AlarmManager#setExactAndAllowWhileIdle(int,long,java.lang.String,java.util.concurrent.Executor,android.app.AlarmManager.OnAlarmListener)"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/alarms"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/schedule-exact-alarms"
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/AlarmManagerService.java"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2a_result: draft-ready-for-review
last_task2a_at: "2026-05-25T20:04:00+08:00"
task6_result: pass-light-edit
task6_reviewed_at: "2026-05-31T10:08:00+08:00"
task6_reviewed_by: openclaw-task6
last_task6_at: "2026-05-31T10:08:00+08:00"
last_task6_review_log: "logs/review/2026-05-31-10-review.md"
last_task6_audit: "2026-07-03"
---

# 25.20 Android 17 allow-while-idle Listener Alarm 与短生命周期唤醒治理

Android 17 给 `setExactAndAllowWhileIdle()` 增加了公开的 `OnAlarmListener` 重载。它把“低功耗 idle 中允许唤醒”和“当前进程内直接回调”放进同一个 API，主要用于替换一类错误设计：任务已经由活跃组件管理，却为了等待下一次短动作而连续持有 partial WakeLock。

这个 API 的适用范围很窄。它不能让已死亡的进程重新接收回调，也不提供持久化任务、网络成功、固定周期或无限执行时间。WakeLock 基础规范见 25.3，系统 WakeLock 机制见 11.5，JobScheduler 诊断见 25.14，Android Vitals excessive partial wake lock 口径见 25.19。

## API 37 新增了什么

Android 17 / API 37 的最终公开签名如下：

```java
public void setExactAndAllowWhileIdle(
        int type,
        long triggerAtMillis,
        String tag,
        Executor executor,
        AlarmManager.OnAlarmListener listener)
```

`tag`、`executor` 和 `listener` 都不能为 `null`。`triggerAtMillis` 使用哪种时间基准由 `type` 决定；相对时长一般配合 `ELAPSED_REALTIME_WAKEUP` 和 `SystemClock.elapsedRealtime()`，避免墙钟或时区调整改变语义。回调在线程池的哪条线程执行，由传入的 `Executor` 决定。

Android 17 Beta 3 博客说明了该能力的动机，但文中的四参数 Kotlin 片段来自 Beta 阶段，不是 `android-17.0.0_r1` 的最终签名。生产代码应以 API 37 reference 和 r1 源码中的五参数重载为准。

三个相近重载的差异如下：

| API | 交付对象 | 低功耗 idle 中交付 | 进程消失后交付 | Android 17 上的 exact alarm 权限 |
| --- | --- | --- | --- | --- |
| `setExact(..., OnAlarmListener, Handler)` | 进程内 callback | 否 | 否 | listener 版本不要求 `SCHEDULE_EXACT_ALARM` |
| `setExactAndAllowWhileIdle(..., PendingIntent)` | 系统保存的 `PendingIntent` | 是 | 是，可重新启动目标组件 | target 31+ 通常需要 `SCHEDULE_EXACT_ALARM`、`USE_EXACT_ALARM` 或豁免 |
| API 37 listener 重载 | 进程内 callback | 是 | 否 | 不要求 `SCHEDULE_EXACT_ALARM` |

API 24 的 listener `setExact()` 与 API 37 重载都受进程生命周期约束；区别是后者带 `FLAG_ALLOW_WHILE_IDLE`，可以穿过低功耗 idle 策略，但仍受 listener 专用 quota、进程状态和厂商策略影响。

## 它解决的 WakeLock 问题

长连接、外设通信和短重试代码容易把“计时”和“保持 CPU 唤醒”混为一件事。线程 sleep、`Handler.postDelayed()` 和协程 `delay()` 都不会阻止设备 suspend；为确保计时器醒来而跨越整个等待期持有 `PARTIAL_WAKE_LOCK`，又会让 CPU 长时间无法进入低功耗状态。

API 37 listener alarm 把等待责任交给 AlarmManager。等待期间应用不持锁；到点时系统唤醒设备并投递进程内 callback。合适的任务同时满足四个条件：

- 从设定 alarm 到收到 callback，应用有持续运行的 `Activity`、`Service` 或 `ContentProvider`；后台 socket 通常意味着用户可感知且合规的 FGS；
- idle 中的唤醒时间对用户任务有明确意义；
- callback 能在很短时间内同步完成；
- callback 丢失后，上层状态机能在前台恢复、重连或下一次可靠事件到来时校正。

| 场景 | 可以使用的条件 | 不合适时的替代 |
| --- | --- | --- | --- |
| FGS 管理的长连接心跳 | 连接正在服务用户，心跳短且失败可重建 | 可用 FCM 的下行消息优先 FCM；普通同步用 JobScheduler |
| 用户正在进行的外设通信 | 活跃 Service 仍在，设备 suspend 会中断用户任务 | Companion Device API、对应蓝牙 API 或 WorkManager |
| 活跃组件内一次短重试 | 必须穿过 idle，重试结果可丢弃或恢复 | 不必穿过 idle 时使用 `Handler`、协程 delay 或 Executor |
| 到点提醒 | 只要进程仍在就足够 | 进程死亡后也必须交付时使用 `PendingIntent` exact alarm |

它减少的是等待阶段的连续持锁，不会让网络、磁盘或 Binder 操作免费。callback 仍需设置业务超时，避免在 Executor 中形成队列。

## Android 17 源码：系统在 callback 期间管理 WakeLock

Android 17 已把 AlarmManager 的 framework 与服务实现放到 `frameworks/base/apex/jobscheduler/`。在 `android-17.0.0_r1` 中，API 37 重载最终调用 `setImpl()`，参数包含：

- `WINDOW_EXACT`，表示单次 exact alarm；
- `FLAG_ALLOW_WHILE_IDLE`，允许低功耗 idle 中交付；
- `operation = null`，说明不是 `PendingIntent`；
- listener Binder、tag 和 Executor。

服务端 `AlarmManagerService.set()` 通过 `directReceiver != null` 识别 listener alarm。Android 17 对这种 exact listener 不要求 exact alarm 权限，并把允许原因记录为 `EXACT_ALLOW_REASON_LISTENER`。

到达交付时间后，`DeliveryTracker.deliverLocked()` 会先按 `WorkSource` 或 creator UID 设置归因，再获取 AlarmManager 共享的 `mWakeLock`，然后调用 listener Binder。应用侧 `ListenerWrapper` 把工作提交给指定 Executor，并在 `onAlarm()` 返回的 `finally` 中调用 `alarmComplete()`。所有在途 alarm 完成，或 listener 交付超时后，服务端释放共享 WakeLock。

这段调用关系带来三个工程结论：

- 简短、同步的 `onAlarm()` 已由 AlarmManager 的交付 WakeLock 保护，通常不需要再获取一把应用 WakeLock；
- `onAlarm()` 返回后另起异步线程，系统会认为本次投递已经完成，后续工作不再由这把 WakeLock 保护；
- Executor 排队时间也占用服务端等待 callback 完成的区间，不能把 listener 提交到拥塞的通用线程池。

`android-17.0.0_r1` 的默认源码值是 listener callback timeout 5 秒、临时电源 allowlist 10 秒。两者用途不同，也都可由系统配置调整：timeout 限制 AlarmManager 等待 listener 完成的时间；临时 allowlist 放宽一部分电源与后台启动限制。它们都不是应用可以依赖的任务时长承诺。

## Listener 专用 quota：不要沿用旧版固定频率结论

Android 16 及以下的通用 Doze 文档对 allow-while-idle alarm 给出较严格的频率限制。Android 17 r1 为 listener + `FLAG_ALLOW_WHILE_IDLE` 增加了独立分支：当 `allow_alarms_with_relaxed_quota` flag 生效时，服务使用 `ALLOW_WHILE_IDLE_LISTENER_QUOTA`、`ALLOW_WHILE_IDLE_LISTENER_WINDOW` 和单独的历史记录。

r1 源码默认值为每小时 72 个 listener allow-while-idle 唤醒点，两个值都可通过 AlarmManager DeviceConfig 修改。这个数字解释了 Android 17 Beta 3 为什么用消息 socket 的周期任务作为示例，但它不是 SDK 合同。应用不能根据“72 次”承诺固定间隔，也不能假设所有 Android 17 设备、后续补丁和 OEM 配置完全相同。

每次 callback 完成后再按当前协议状态安排下一次 one-shot alarm，并记录 requested time 与 fired time。遇到 quota、Doze 深度变化或厂商策略时，实际触发可能变晚；不要用它实现必须保持恒定节拍的计时协议。

## 权限与生命周期边界

listener alarm 的核心限制是“请求进程必须从设定时一直运行到交付时”。官方 reference 说明，当调用进程不再有运行中的 `Activity`、`Service` 或 `ContentProvider` 时，系统可以取消 listener alarm。Android 14 起的兼容性变更会在应用进入 cached/frozen 状态时移除 exact listener alarm；Android 17 r1 的移除原因记录为 `listener_cached`。listener Binder 死亡时也会以 `listener_binder_died` 移除。

因此，“进程还在”不等于“listener 一定还在”。仅有 Application 对象或被系统保留的 cached process 不满足可靠交付要求。若功能在组件结束或进程死亡后仍要工作，应使用 `PendingIntent` 版本并持久化任务状态。

权限边界需要按交付对象判断：

- Android 17 的 `OnAlarmListener` exact alarm 不要求 `SCHEDULE_EXACT_ALARM`，服务端也不会对 direct listener 执行该权限检查；
- `PendingIntent` exact alarm 对 target 31+ 应检查 `SCHEDULE_EXACT_ALARM`、`USE_EXACT_ALARM` 或平台豁免；Android 14 起，新安装且 target 33+ 的应用通常不会预授予 `SCHEDULE_EXACT_ALARM`；
- listener 免权限不代表可以规避后台规则。它用“进程必须保持活跃、进入 cached 后删除 alarm”换取了更小的持久化与滥用面。

| 需求 | 推荐 API | 生命周期处理 |
| --- | --- | --- | --- |
| 活跃组件内短动作，idle 中也需唤醒 | API 37 listener 重载 | 组件结束、连接关闭或任务取消时 `cancel(listener)` |
| 用户设定的到点提醒，进程可能已死 | `PendingIntent` `setExactAndAllowWhileIdle()` | 持久化状态，检查 exact alarm 权限，开机或权限恢复后重建 |
| 闹钟类高可见提醒 | `setAlarmClock()` | 提供用户可见入口，并按 exact alarm 政策处理 |
| 可推迟同步或日志上传 | WorkManager / JobScheduler | 让系统管理约束、重试与进程恢复 |

## 与 WorkManager、JobScheduler、Handler 延迟任务的选型

选型时依次确认：是否需要唤醒设备、是否需要接近指定时间、进程死亡后是否仍要交付、工作能否在 callback 内很快结束。

| 任务属性 | 推荐方案 | 不建议 |
| --- | --- | --- |
| 页面内倒计时、连接内 timeout，设备醒着即可 | `Handler`、协程 delay、业务 Executor 定时 | AlarmManager |
| 周期同步、日志上传、缓存清理 | WorkManager / JobScheduler | exact alarm + 手动重试 |
| idle 中允许延迟的用户动作 | `setAndAllowWhileIdle()` | exact alarm |
| 用户承诺的精确时间提醒 | `PendingIntent` exact alarm 或 `setAlarmClock()` | listener alarm |
| 活跃组件仍在、idle 下需要一次短 callback | API 37 listener allow-while-idle alarm | 跨等待期持有 WakeLock |

下面的封装只安排一次 callback，并把取消动作交给拥有该连接或任务的组件：

```kotlin
@RequiresApi(37)
class OneShotIdleCallback(
    context: Context,
    private val task: () -> Unit,
) : Closeable {
    private val alarmManager = context.getSystemService(AlarmManager::class.java)
    private val stateLock = Any()
    private var closed = false
    private var scheduled = false
    private val executor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "idle-alarm-callback").apply {
            priority = Thread.NORM_PRIORITY
        }
    }

    private val alarmListener = AlarmManager.OnAlarmListener {
        val shouldRun = synchronized(stateLock) {
            scheduled = false
            !closed
        }
        if (shouldRun) task()
    }

    fun scheduleAtElapsedRealtime(triggerAtMillis: Long) {
        require(triggerAtMillis > SystemClock.elapsedRealtime())

        synchronized(stateLock) {
            check(!closed)
            check(!scheduled)
            alarmManager.setExactAndAllowWhileIdle(
                AlarmManager.ELAPSED_REALTIME_WAKEUP,
                triggerAtMillis,
                "com.example.connection:idle-callback",
                executor,
                alarmListener,
            )
            scheduled = true
        }
    }

    fun cancelPending() {
        synchronized(stateLock) {
            if (scheduled) {
                alarmManager.cancel(alarmListener)
                scheduled = false
            }
        }
    }

    override fun close() {
        val shouldShutdown = synchronized(stateLock) {
            if (closed) {
                false
            } else {
                closed = true
                if (scheduled) {
                    alarmManager.cancel(alarmListener)
                    scheduled = false
                }
                true
            }
        }
        if (shouldShutdown) {
            executor.shutdown()
        }
    }
}
```

拥有者应在 Service 停止、连接关闭或任务取消时调用 `close()`，而不是在通用的 `LifecycleOwner.onStop()` 中无条件取消。Activity 或 `ProcessLifecycleOwner` 的 `onStop()` 常常表示界面进入后台；在那里取消会让本来要在熄屏 idle 中运行的 alarm 永远收不到。`cancel()` 也无法中止已经进入 callback 的工作，因此 `task` 自身仍需支持取消和超时。

callback 不应执行下载、数据库迁移、批量上传或没有上限的重试。若工作需要持久化、约束或进程恢复，把输入先写入持久存储，再交给 WorkManager / JobScheduler；不要先返回 callback，再假定 CPU 会继续保持唤醒。

## 电量归因与 tag 设计

API 37 强制传入 `tag`。它用于日志和电量归因，应稳定、低基数并能定位功能；不要加入用户 ID、会话 ID、订单号、URL、随机数或递增序号。下面是三个合适的格式：

```text
com.example.messaging:socket-heartbeat
com.example.sync:short-retry
com.example.call:ring-timeout
```

这些 tag 能按功能聚合，却不会暴露个人数据。单次连接或消息的 trace id 应写入应用日志，再通过 elapsed realtime 与 alarm 事件关联。

Android 17 r1 的 `Alarm.makeTag()` 会给 wakeup alarm 的统计 tag 添加 `*walarm*:` 前缀，非 wakeup alarm 使用 `*alarm*:`。AlarmManagerService 在投递时把 `statsTag` 设为共享 WakeLock 的 history tag，并把 `WorkSource` 或 creator UID 用于电量归因。因此系统侧能观察到 UID、tag、请求时间、实际交付和唤醒次数，但不了解连接状态、重试原因和服务端游标。

建议记录的内部事件：

| 字段 | 用途 |
| --- | --- |
| `alarm_tag` | 与 AlarmManager 和电量归因一致 |
| `task_type` | 区分 heartbeat、short retry、message sync、call timeout |
| `requested_elapsed_ms` / `fired_elapsed_ms` | 计算系统交付延迟 |
| `callback_start_ms` / `callback_end_ms` | 区分 AlarmManager 延迟和 Executor 排队/执行 |
| `interactive` / `charging` / `process_state` | 复现 Doze、Vitals 与 cached 删除条件 |
| `next_action` | complete、reschedule、handoff、drop |
| `user_result` | 记录该次唤醒是否产生连接恢复、消息到达等结果 |

只统计 listener alarm 次数还不够。要同时计算“有用户结果的唤醒占比”：连接恢复、消息到达、外设操作完成或提醒展示。没有结果的 wakeup 即使单次很短，也会增加后台 active 时间。

## 迁移与验证流程

迁移前记录旧实现的连续 WakeLock 时长、wakeup alarm 次数、任务成功率、消息或连接延迟、网络重连、CPU active 时间和 Vitals tag。迁移后的目标不是只让 WakeLock 时长下降，还要避免 wakeup alarm 频次、失败率和用户延迟恶化。

一轮验证至少覆盖以下场景：

- 活跃 Service 存在、设备进入 Doze 时能收到 callback；
- 组件停止后 alarm 被取消，或在进程进入 cached/frozen 后被系统移除；
- 杀死进程后 listener 不会像 `PendingIntent` 一样重新交付；
- Executor 正常与拥塞时，排队和 callback 时长都可观察；
- 重复安排、主动取消、网络断开和 callback 抛异常时，状态能够恢复；
- 旧版连续 WakeLock 与新版短唤醒在同一设备、同一任务负载下比较。

下面的命令用于专用测试机；测试结束的恢复命令也包含在内：

```bash
APP_PACKAGE=com.example.app

adb shell dumpsys batterystats --reset
adb shell dumpsys deviceidle force-idle

# 在活跃组件中安排 alarm，等待 callback 后采集。
adb shell dumpsys alarm > alarm.txt
adb shell dumpsys batterystats --charged "$APP_PACKAGE" > batterystats.txt
adb bugreport bugreport.zip

adb shell dumpsys deviceidle unforce
adb shell dumpsys battery reset
```

`dumpsys alarm` 中检查应用的 `*walarm*:<tag>`、requested/when elapsed、quota 调整和 removed alarm history；`batterystats` 与 bugreport 用来对齐屏幕、充电、WakeLock 和 wakeup。若测试中断，也要执行 `deviceidle unforce` 和 `battery reset`，避免设备继续留在模拟状态。

Pixel 或 AOSP 设备用于核对平台语义，厂商设备用于验证进程冻结、后台限制和 quota 配置差异。listener 漏交付若由进程被清理造成，增加 alarm 次数不会修复，应改用 `PendingIntent`、推送、合规 FGS 或系统调度。

## socket 保活与 FCM / push 的边界

主动维持 socket、FCM 和 exact alarm 解决的问题不同。Android 官方 Doze 指南建议下行消息优先使用 FCM，让多个应用共享系统连接。高优先级 FCM 只应用于时间敏感且会产生用户可见通知的消息；静默内容刷新应使用普通优先级，并接受 Doze maintenance window 的延迟。

| 需求 | 推荐能力 | 主要代价 | 风险 |
| --- | --- | --- | --- |
| 服务端有新消息通知用户 | FCM high priority + 用户可见通知 | 推送配额和通知质量要求 | 静默滥用不符合优先级语义 |
| 活跃 FGS 内连接已建立，协议需要短心跳 | listener allow-while-idle alarm | wakeup alarm 与网络唤醒 | 进程 cached 后不交付 |
| 用户设定的到点提醒 | `PendingIntent` exact alarm / `setAlarmClock()` | exact alarm 权限和电量成本 | 权限被拒绝后功能降级 |
| 非用户可见后台同步 | WorkManager / JobScheduler | 受约束和配额影响 | 不能承诺精确时间 |
| 实时通话、导航或音频 | 合规 FGS + 对应平台 API | 通知、权限和前台资源 | 停止路径不完整会持续耗电 |

如果业务要求设备 idle 时仍能快速收到服务端消息，应先审查推送、通知展示和用户可见性。listener alarm 只能作为活跃组件期间的补充计时，不能代替 Push 基础设施，也不能在进程死亡后拉起应用。

## Android Vitals WakeLock 指标联动

25.19 的 excessive partial wake lock 指标关心熄屏时应用在后台或运行 FGS 的非豁免 partial WakeLock 累计时长。listener alarm 把等待阶段从“持续持锁”改成“到点由 AlarmManager 短暂唤醒”，但 wakeup alarm 本身也有电量成本。门禁要同时观察两边：

| 门禁项 | 目标 |
| --- | --- |
| 后台 partial WakeLock 单次最长 | 防 stuck wake lock |
| 后台 partial WakeLock 24 小时累计 | 防 Vitals excessive |
| wakeup alarm 次数 / 有结果次数 | 发现无收益唤醒 |
| requested-to-fired 延迟 | 发现 quota、Doze 或厂商策略影响 |
| Executor 排队与 callback 时长 | 防止交付超时 |
| listener cached / binder died 移除次数 | 发现生命周期选型错误 |
| WorkManager handoff 成功率 | 防止长工作留在 callback |

灰度期按相同设备与任务负载比较新旧版本。若 WakeLock 时长下降而 wakeup alarm 大幅增加，问题只是从连续持锁转成了频繁唤醒，应回到任务合并、推送策略和系统调度。

API 37 listener allow-while-idle alarm 的判断条件可以压缩成一句话：活跃组件仍在、idle 中必须唤醒、callback 很短、失败能够恢复。缺少任一条件，就应选择其他 API。

## 参考资料

- [AlarmManager API reference：API 37 listener overload](https://developer.android.com/reference/android/app/AlarmManager#setExactAndAllowWhileIdle(int,long,java.lang.String,java.util.concurrent.Executor,android.app.AlarmManager.OnAlarmListener))
- [The Third Beta of Android 17](https://developer.android.com/blog/posts/the-third-beta-of-android-17)
- [Schedule alarms](https://developer.android.com/develop/background-work/services/alarms)
- [Android 14：Schedule exact alarms are denied by default](https://developer.android.com/about/versions/14/changes/schedule-exact-alarms)
- [Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [AlarmManager.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/framework/java/android/app/AlarmManager.java#1430)
- [AlarmManagerService.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java#2449)
- [Alarm.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/alarm/Alarm.java#153)
