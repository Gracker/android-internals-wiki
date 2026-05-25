---
title: "Android 17 allow-while-idle Listener Alarm 与短生命周期唤醒治理"
chapter: "25.20"
section: "25.20"
status: ready-for-review
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
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java"
pipeline_stage: task6_pending
task2a_result: draft-ready-for-review
last_task2a_at: "2026-05-25T20:04:00+08:00"
---

# 25.20 Android 17 allow-while-idle Listener Alarm 与短生命周期唤醒治理

<!-- outline-start -->
## 要点

### 🔹 API 37 新增了什么
解释 `AlarmManager.setExactAndAllowWhileIdle(int, long, String, Executor, OnAlarmListener)` 与既有 `PendingIntent` 版本、`setExact()` Listener 版本的差异，明确它只适合进程仍在的短生命周期任务。

### 🔹 它解决的 WakeLock 问题
围绕长连接保活、短周期重试、消息同步和临时后台任务，说明 callback 型 allow-while-idle alarm 如何减少应用为了等待下一次任务而持有连续 WakeLock 的需求。

### 🔹 权限与生命周期边界
核对 `SCHEDULE_EXACT_ALARM`、`USE_EXACT_ALARM`、`OnAlarmListener` 豁免、进程被系统清理后的取消行为，以及 Android 14 之后 exact alarm 默认拒绝的迁移影响。

### 🔹 与 WorkManager、JobScheduler、Handler 延迟任务的选型
建立任务选型表：可延迟周期任务走 WorkManager / JobScheduler，进程内短延迟走 Handler / coroutine delay，必须熄屏精确唤醒才考虑 allow-while-idle alarm。

### 🔹 电量归因与 tag 设计
整理 tag、Executor、任务类型、屏幕状态、前后台状态、WakeLock 持有时长和 Android Vitals 过度 WakeLock 指标之间的证据关联。

### 🔹 迁移与验证流程
给出从连续 WakeLock / 轮询线程迁移到 Listener Alarm 的实验设计：构造熄屏场景、记录触发延迟、检查 batterystats、确认漏触发和重复触发边界。

## 扩展

### 🔸 socket 保活与 FCM / push 的边界
对比主动维持 socket、FCM 高优先级消息、exact alarm 唤醒和后台网络限制的适用场景。

### 🔸 Android Vitals WakeLock 指标联动
把本节与 25.19 的 excessive partial wake lock 治理合并成后台唤醒门禁规则。

<!-- outline-end -->

Android 17 给 `setExactAndAllowWhileIdle()` 增加了 `OnAlarmListener` 版本。它把“Doze 中到点唤醒”和“进程内回调”放到同一个 API 里，适合替代一部分为了等下一次短任务而持续持有 WakeLock 的写法。

本节只讨论 API 37 的 listener allow-while-idle alarm。WakeLock 基础规范见 25.3，系统 WakeLock 机制见 11.5，JobScheduler pending reason 见 25.14，Android Vitals excessive partial wake lock 口径见 25.19。

Clippings 的《Android 性能优化》没有单独讲 AlarmManager，但任务调度章节给了本节的写法：先区分任务类型，再决定线程、优先级和等待策略；CPU 闲时章节提醒后台预加载不能抢关键路径资源；线程池章节提醒延时任务和周期任务不要散落成野线程。本节借用这个组织方式，把 listener alarm 放进后台唤醒治理，而不复用参考书原文和代码。[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md][结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md][结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]

## API 37 新增了什么

Android 17 新增的方法签名是：

```java
public void setExactAndAllowWhileIdle(
        int type,
        long triggerAtMillis,
        String tag,
        Executor executor,
        AlarmManager.OnAlarmListener listener)
```

它和 API 23 的 `setExactAndAllowWhileIdle(int, long, PendingIntent)` 一样允许低功耗 idle 模式下触发，但交付对象从 `PendingIntent` 变成了当前进程内的 `OnAlarmListener`。官方 API reference 明确标注该重载 added in API level 37，并说明 `tag` 用于日志和电量归因，`onAlarm()` 会在传入的 `Executor` 上执行。[已验证: 官方文档, developer.android.com/reference/android/app/AlarmManager]

它和 API 24 的 `setExact(int, long, String, OnAlarmListener, Handler)` 也不同。API 24 listener exact alarm 只是精确回调，不具备 allow-while-idle 语义；API 37 的新重载允许 Doze / idle 下唤醒，同时仍保留 listener alarm 的进程生命周期边界。[已验证: 官方文档, developer.android.com/reference/android/app/AlarmManager]

三类 API 的边界如下：

| API | 交付对象 | idle 模式下触发 | 进程被清理后是否仍可交付 | 典型用途 |
| --- | --- | --- | --- | --- |
| `setExact(..., OnAlarmListener, Handler)` | 当前进程 callback | 否 | 否 | Activity / Service 存活期间的精确短计时 |
| `setExactAndAllowWhileIdle(..., PendingIntent)` | `PendingIntent` | 是 | 是 | 闹钟、日历提醒、用户承诺的到点通知 |
| `setExactAndAllowWhileIdle(..., String, Executor, OnAlarmListener)` | 当前进程 callback | 是 | 否 | 长连接已在运行、进程内短延迟重试、临时同步窗口 |

Android Developers Blog 把这个新能力定位为减少 idle alarm 场景下的连续 WakeLock，示例场景包括消息应用维护 socket 连接这类周期性短任务。这个定位要读窄：它服务于“进程已经活着，只想在 idle 下短暂叫醒 callback”的场景，不能承担进程死亡后的可靠恢复。[已验证: 官方博客, developer.android.com/blog/posts/the-third-beta-of-android-17]

## 它解决的 WakeLock 问题

旧写法里，长连接、短重试和轻量同步经常有两种极端：要么用线程或定时器在进程内轮询，要么为了等下一次网络心跳持有 `PARTIAL_WAKE_LOCK`。前者在 Doze 下可能被延后，后者会直接拉高后台持锁时长。listener allow-while-idle alarm 给了第三种选择：不在等待阶段持锁，到点后让系统唤醒，再在一个短窗口里执行真正的工作。

它适合的任务有三个共同点：进程仍有组件存活，下一次动作很短，漏掉后可以由上层状态机恢复。例如：

| 场景 | 旧风险 | Listener Alarm 写法 | 失败恢复 |
| --- | --- | --- | --- |
| IM socket 心跳重试 | 线程 sleep + WakeLock 等下一次重试 | 当前连接仍在时安排下一次 idle callback | 下次前台、FCM、网络重连后重建状态 |
| 短周期消息同步 | 固定周期 wakeup + 后台轮询 | 有待同步窗口时安排一次 callback，完成后按结果决定是否再排 | 服务端增量游标兜底 |
| 临时后台任务收尾 | `onReceive()` 后手动持锁等待异步完成 | callback 中执行短收尾，超时后放弃或转 Job | JobScheduler / WorkManager 重试 |
| FGS 内部 watchdog | FGS 持续运行时附带线程计时 | FGS 存活期间使用 listener 计时 | FGS 停止时取消 listener |

这类 API 不会消除执行阶段的耗电。它减少的是等待阶段的连续持锁；真正执行时，如果要做网络、磁盘或 Binder 调用，仍然要控制任务长度、超时和取消路径。API 23 的 allow-while-idle 文档说明，alarm dispatch 后应用会进入约 10 秒的临时电源豁免窗口，可用于获取进一步 WakeLock 完成工作；AOSP main 中 `AlarmManagerService` 的默认 `allow_while_idle_whitelist_duration` 也是 10 秒。[已验证: 官方文档, developer.android.com/reference/android/app/AlarmManager][已验证: AOSP main, frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java]

## 权限与生命周期边界

listener alarm 的第一条边界是进程生命周期。官方文档说明，基于 listener 的 alarm 可能在调用进程不再有 `Activity`、`Service` 或 `ContentProvider` 运行时被系统取消；如果需要在组件结束后仍收到 alarm，应使用 `PendingIntent` 版本。Android 14 起，系统还会在调用 App 退出 lifecycle 后显式丢弃这类 exact listener alarm。[已验证: 官方文档, developer.android.com/reference/android/app/AlarmManager]

第二条边界是 exact alarm 权限。Android 12 引入 `SCHEDULE_EXACT_ALARM`，Android 13 起可在 `SCHEDULE_EXACT_ALARM` 和 `USE_EXACT_ALARM` 中按场景选择，Android 14 起多数新安装且 target 33+ 的应用默认拿不到 `SCHEDULE_EXACT_ALARM`。官方 schedule alarms 文档同时写明，使用 `OnAlarmListener` 对象设置 exact alarm 时不需要 `SCHEDULE_EXACT_ALARM`。[已验证: 官方文档, developer.android.com/develop/background-work/services/alarms][已验证: 官方文档, developer.android.com/about/versions/14/changes/schedule-exact-alarms]

这并不代表 API 37 listener allow-while-idle alarm 可以绕过所有后台限制。它仍是 exact + idle 唤醒能力，应只用于用户可理解、时间敏感、短生命周期的任务。若目标是用户设定的闹钟、日历提醒、服药提醒、到点通知，`PendingIntent` 版本或 `setAlarmClock()` 更符合“进程可不在”的需求；若目标是静默后台同步，优先用 WorkManager / JobScheduler 或非精确 alarm。

权限和生命周期组合如下：

| 需求 | 推荐 API | 权限处理 | 生命周期处理 |
| --- | --- | --- | --- |
| 进程内 30-120 秒短重试，idle 下也要触发 | API 37 listener `setExactAndAllowWhileIdle()` | listener exact alarm 不要求 `SCHEDULE_EXACT_ALARM` | 组件结束时 `cancel(listener)` |
| 用户设置的到点提醒，进程可能已死 | `PendingIntent` `setExactAndAllowWhileIdle()` | 检查 `canScheduleExactAlarms()` 或走 `USE_EXACT_ALARM` 适用场景 | 数据库持久化，重启后重建 |
| 闹钟类强提醒 | `setAlarmClock()` | exact alarm 权限和产品政策一起评估 | 用户可见入口、系统闹钟 UI |
| 可推迟同步 / 日志上传 | WorkManager / JobScheduler | 无 exact alarm 权限 | 系统托管重试和约束 |

## 与 WorkManager、JobScheduler、Handler 延迟任务的选型

选型的第一步是判断“任务是否必须在设备 idle 时被唤醒”。如果答案是否，listener allow-while-idle alarm 不应进入方案。Android 官方 alarms 文档给出的替代路径很清楚：App 存活期间的计时用 `Handler.postDelayed()` 等 uptime 计时 API；可延迟周期后台工作用 WorkManager；需要某个时间附近执行但不要求精确，用 `set()`、`setWindow()` 或 `setAndAllowWhileIdle()`；只有精确时间才用 exact alarm。[已验证: 官方文档, developer.android.com/develop/background-work/services/alarms]

| 任务属性 | 推荐方案 | 不建议 |
| --- | --- | --- |
| 页面内倒计时、连接内短 timeout | `Handler`、协程 delay、业务 Executor 定时 | AlarmManager |
| 周期同步、日志上传、缓存清理 | WorkManager / JobScheduler | exact alarm + 手动重试 |
| 用户不关心秒级精度的提醒 | `setWindow()` / `setAndAllowWhileIdle()` | `setExactAndAllowWhileIdle()` |
| 用户承诺的精确时间提醒 | `PendingIntent` exact alarm 或 `setAlarmClock()` | listener alarm |
| 进程仍在、idle 下必须短暂唤醒 | API 37 listener allow-while-idle alarm | 连续 WakeLock / 自旋线程 |

下面是一个最小的 API 37 用法。读者看四处：稳定 tag、单线程 Executor、组件停止时取消、callback 内只做短任务。

```kotlin
@RequiresApi(37)
class SocketHeartbeatController(
    context: Context,
    private val socket: MessageSocket,
) : DefaultLifecycleObserver {
    private val alarmManager = context.getSystemService(AlarmManager::class.java)
    private val executor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "socket-heartbeat-alarm").apply {
            priority = Thread.NORM_PRIORITY
        }
    }

    private val alarmListener = AlarmManager.OnAlarmListener {
        if (!socket.isConnected()) return@OnAlarmListener

        socket.sendHeartbeat(timeoutMs = 3_000)
        scheduleNextHeartbeat(delayMs = 60_000)
    }

    fun scheduleNextHeartbeat(delayMs: Long) {
        val triggerAt = SystemClock.elapsedRealtime() + delayMs
        alarmManager.setExactAndAllowWhileIdle(
            AlarmManager.ELAPSED_REALTIME_WAKEUP,
            triggerAt,
            "com.example.messaging:socket-heartbeat",
            executor,
            alarmListener,
        )
    }

    override fun onStop(owner: LifecycleOwner) {
        alarmManager.cancel(alarmListener)
    }

    override fun onDestroy(owner: LifecycleOwner) {
        alarmManager.cancel(alarmListener)
        executor.shutdownNow()
    }
}
```

这段代码不适合长耗时下载、数据库迁移、图片上传或批量重试。callback 里如果发现任务会超过短窗口，应把任务参数持久化，然后转给 WorkManager / JobScheduler。否则 listener alarm 只是把 WakeLock 泄漏换成了 alarm 唤醒风暴。

## 电量归因与 tag 设计

API 37 强制传入 `tag`，这对治理很有价值。tag 会用于日志和电量归因，应该稳定、低基数、能定位到功能，不应包含用户 ID、会话 ID、订单号、URL、随机数或递增序号。建议格式和 25.19 的 WakeLock tag 对齐：

```text
com.example.messaging:socket-heartbeat
com.example.sync:short-retry
com.example.call:ring-timeout
```

AOSP `AlarmManagerService` 使用 `*alarm*` partial WakeLock 分发 alarm，并通过 WorkSource / creatorUid / statsTag 做归因；dispatch 时会记录 wakeup alarm 到包名和 UID，listener callback 也有超时管理。这个路径说明 alarm 侧能给出 UID、tag、唤醒次数和分发窗口，但拿不到业务 trace id、连接状态、重试原因和服务端游标，这些字段要由应用侧补采。[已验证: AOSP main, frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java]

建议记录的内部事件：

| 字段 | 用途 |
| --- | --- |
| `alarm_tag` | 对齐 AlarmManager 和电量归因 |
| `task_type` | 区分 heartbeat、short_retry、message_sync、call_timeout |
| `scheduled_elapsed_ms` / `fired_elapsed_ms` | 计算触发延迟，避开墙钟调整 |
| `screen_state` / `charging_state` / `app_state` | 复现 Vitals 和 Doze 条件 |
| `executor_queue_depth` | 判断 callback 是否被自己的 Executor 堵住 |
| `callback_duration_bucket` | 控制执行窗口，不上传原始高精度耗时 |
| `next_action` | complete、reschedule、handoff_to_workmanager、drop |
| `wakelock_held_ms` | 和 25.19 excessive partial wake lock 口径关联 |

线上门禁不要只看 listener alarm 次数。更有价值的是“每次唤醒是否真的产生用户收益”：有消息到达、有连接恢复、有通话提醒、有任务完成。没有用户收益的唤醒，即使单次耗电很小，累计后也会推高后台 active 时间和 Vitals 风险。

## 迁移与验证流程

迁移前先建立基线。旧实现需要记录连续 WakeLock 持有时长、后台唤醒次数、消息延迟、漏消息率、网络重连次数、CPU active 时间和 Android Vitals tag 分布。没有基线，改成 listener alarm 后只能看到“代码更现代”，无法证明功耗改善。

建议按四步验证：

1. 构造场景：未充电、熄屏、进入 Doze，保持 socket 或临时后台任务处于可重试状态。
2. 采集基线：旧版本记录 `dumpsys batterystats --reset` 后的 partial WakeLock、wakeup alarm、网络和 CPU active。
3. 替换实现：等待阶段取消连续 WakeLock，用 listener allow-while-idle alarm 安排下一次短 callback。
4. 对比结果：检查触发延迟、callback 成功率、重复触发、漏触发、WakeLock 累计时长和用户可见延迟。

常用命令如下：

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys deviceidle force-idle
adb shell dumpsys alarm | sed -n '/com.example.app/,+80p'
adb shell dumpsys batterystats --history com.example.app > alarm-history.txt
adb shell dumpsys batterystats --charged com.example.app > batterystats.txt
```

验证结果要按设备分组。Pixel / AOSP 设备能验证平台语义，国内 ROM 能验证后台限制、清理策略和厂商省电策略。listener alarm 依赖进程存活，OEM 清理进程后不会像 `PendingIntent` alarm 那样可靠交付；这类漏触发不能用更多 alarm 解决，应回到推送、前台服务、用户可见入口或系统调度。

## socket 保活与 FCM / push 的边界

主动维持 socket、FCM 高优先级消息和 exact alarm 唤醒处在不同层级。FCM 适合服务端有新消息时唤醒 App，Android 官方 Doze 文档明确建议需要下行消息时优先使用 FCM，避免每个 App 都维护自己的持久网络连接；高优先级 FCM 适合用户可见、时间敏感的通知，系统会给临时网络和 partial WakeLock 访问窗口。[已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

| 需求 | 推荐能力 | 主要代价 | 风险 |
| --- | --- | --- | --- |
| 服务端有新消息通知用户 | FCM high priority + 用户可见通知 | 推送配额和通知质量要求 | 滥用高优先级会被降级或影响 standby 行为 |
| App 前台/FGS 内连接已建立，短间隔保活 | listener allow-while-idle alarm | wakeup alarm 次数 | 进程被清理后不交付 |
| 用户设定的到点提醒 | `PendingIntent` exact alarm / `setAlarmClock()` | exact alarm 权限和电量成本 | 权限被拒绝后功能降级 |
| 非用户可见后台同步 | WorkManager / JobScheduler | 受约束和配额影响 | 不能承诺精确时间 |
| 长时间实时通话 / 导航 / 音频 | 合规 FGS + 对应平台 API | 通知、权限、前台资源 | 停止路径不完整会变成功耗问题 |

如果业务希望“任何时候都能秒级收消息”，优先审查服务端推送策略、通知展示和用户可见性。listener alarm 可作为进程存活期间的补充心跳，不应承担 Push 基础设施的职责。

## Android Vitals WakeLock 指标联动

25.19 的 excessive partial wake lock 口径关心后台或 FGS、熄屏、24 小时累计的非豁免 partial WakeLock。listener allow-while-idle alarm 的价值，是把等待阶段从“持续持锁”改成“到点短唤醒”。接入门禁时，把两类指标放在同一张表里：

| 门禁项 | 目标 |
| --- | --- |
| 后台 partial WakeLock 单次最长 | 防 stuck wake lock |
| 后台 partial WakeLock 24 小时累计 | 防 Vitals excessive |
| wakeup alarm 次数 / 用户收益次数 | 防 alarm 唤醒风暴 |
| listener callback P95 时长 | 防 callback 执行超出短窗口 |
| listener 取消率 | 防组件结束后遗留 alarm |
| WorkManager handoff 成功率 | 防长任务留在 callback 内 |

上线策略建议分三阶段：dogfood 打开详细采样，灰度阶段只保留低基数字段，正式发布后把 `alarm_tag` 和 WakeLock tag 聚合到同一个后台耗电看板。若 WakeLock 时长下降但 wakeup alarm 次数翻倍，说明只是把问题从持锁迁移到了频繁唤醒，需要回到任务合并、推送策略和系统调度。

API 37 listener allow-while-idle alarm 是一个窄工具。用对了，它能去掉一类“等下一次短任务”的连续 WakeLock；用宽了，它会变成新的后台唤醒入口。判断标准很简单：进程仍在、任务很短、用户收益清楚、失败可恢复，才值得使用。
