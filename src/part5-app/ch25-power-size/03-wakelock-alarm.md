---
title: "WakeLock 与 Alarm 管理"
chapter: "25.3"
section: "25.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-14"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers wake lock / alarm docs + Clippings structure references"
confidence: medium-high
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/set"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/alarms"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/schedule-exact-alarms"
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerManager.WakeLock"
  - type: official
    path: "https://developer.android.com/reference/android/app/AlarmManager"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [wakelock, alarm, exact-alarm, wakelock-leak, power]
related_chapters: ["25.2", "11.5", "5.6", "25.4"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
last_task9_review_log: "logs/deep-review/2026-05-14-16-deep-review.md"
last_task9_at: "2026-05-14T16:30:00+08:00"
last_task9_audit: "2026-06-08"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-14"
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_result: pass-light-edit
last_task6_review_log: logs/review/2026-05-14-16-review.md
last_task6_audit: "2026-05-25"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-13
---

# WakeLock 与 Alarm 管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 WakeLock 类型与使用规范
- 🔹 WakeLock 泄漏检测与治理
- 🔹 AlarmManager 最佳实践
- 🔹 Exact Alarm 权限变化（Android 12+）

### 扩展（可选深入）

- 🔸 功耗回归守门

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 WakeLock 与 Alarm 管理

本节讲 App 侧怎么使用 WakeLock 和 Alarm，不重复系统电源状态机、内核 `wakeup_source` 或 Doze 实现。底层机制见 §5.6 和 §11.5；后台任务分层见 §25.2；WorkManager 的调度实战放到 §25.4。

WakeLock 和 Alarm 很容易被写成“保活工具”，这类写法会把功耗问题带进线上：锁忘记释放，灭屏后 CPU 不能休眠；Alarm 频繁唤醒，Doze 维护窗口被不断打散；Exact Alarm 权限没处理好，Android 14 之后直接抛 `SecurityException` 或功能降级失控。

后台任务的治理可以按一条顺序展开：先按用户可见度判断任务类型，是用户正在等的结果还是可以延后的收尾；再选择调度 API；最后补齐观测字段。WakeLock 与 Alarm 的管理也要落进这条顺序。

## WakeLock 类型与使用规范

App 侧常用的 WakeLock 只有一个：`PARTIAL_WAKE_LOCK`。它保持 CPU 运行，允许屏幕关闭，适合短时间完成用户已经触发的后台收尾工作，例如一段上传、一次加密写盘、一个必须落完的本地索引更新。屏幕相关的 `SCREEN_DIM_WAKE_LOCK`、`SCREEN_BRIGHT_WAKE_LOCK`、`FULL_WAKE_LOCK` 已废弃；保持屏幕常亮应交给 `FLAG_KEEP_SCREEN_ON` 或具体组件能力。 [已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/PowerManager.java] [已验证: 官方文档, developer.android.com/reference/android/os/PowerManager.WakeLock]

WakeLock 的默认规则可以归纳成四条：少用、短持有、命名稳定、异常路径必释放。Android Developers 明确要求只有没有合适替代 API 时才使用 WakeLock，并且持有时间越短越好；tag 推荐包含包名、类名或方法名，不要包含个人信息，也不要加随机数或计数器，否则系统和排查工具无法聚合同一处代码的耗电。 [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/set] [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices]

| 场景 | 推荐做法 | 不建议的做法 |
|------|----------|--------------|
| 屏幕保持常亮 | `WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON` 或 View 的 `keepScreenOn` | 用屏幕类 WakeLock 控制亮屏 |
| 用户触发的短任务 | `PARTIAL_WAKE_LOCK` + 超时 + `try/finally` | 后台线程里手动 `acquire()` 后靠回调释放 |
| 可延后的后台同步 | WorkManager / JobScheduler | 用 WakeLock 保持线程池常驻 |
| 周期性提醒 | AlarmManager，默认用非精确 Alarm | 每个业务固定精确唤醒 |
| 长时间用户可感知任务 | 合适类型的前台服务 + 通知 + 取消入口 | 静默持锁运行 |

下面这段代码只处理“同步执行的一小段工作”。读者要看三处：固定 tag、超时、`finally` 释放。

```kotlin
private const val SYNC_WAKELOCK_TAG = "com.example.app:SyncWorker"
private const val WAKELOCK_TIMEOUT_MS = 30_000L

inline fun <T> Context.withPartialWakeLock(block: () -> T): T {
    val powerManager = getSystemService(PowerManager::class.java)
    val wakeLock = powerManager.newWakeLock(
        PowerManager.PARTIAL_WAKE_LOCK,
        SYNC_WAKELOCK_TAG
    ).apply {
        setReferenceCounted(false)
        acquire(WAKELOCK_TIMEOUT_MS)
    }

    return try {
        block()
    } finally {
        if (wakeLock.isHeld) {
            wakeLock.release()
        }
    }
}
```

这段代码只适合 `block()` 内部同步完成的工作。如果 `block()` 里只是启动协程、提交线程池任务或发起异步网络请求，函数返回时 WakeLock 会被释放，后续异步工作得不到保护；如果把释放挪到异步回调里，又会把持锁生命周期分散到多个状态分支，泄漏风险会升高。更稳的做法是把可延后的工作交给 WorkManager，把必须用户可见的长任务交给前台服务。 [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices]

`setReferenceCounted(false)` 也有边界。它适合“一个对象拥有一把锁，一次 acquire 对应一次 release”的封装；如果多个调用方共享同一把锁，非引用计数会让其中一个调用方提前释放锁。工程里不要把 WakeLock 做成全局单例给多个业务复用，tag 看起来省事，排查时会丢掉来源。

## WakeLock 泄漏检测与治理

WakeLock 泄漏通常不来自 `release()` 这一行代码缺失，而来自生命周期不清：异常提前返回、回调没回来、取消路径没走、任务迁移到线程池后没有归属。治理时要把 WakeLock 当成资源句柄处理，和文件、数据库事务一样写入统一封装。

排查时可以按三层看：当前状态、历史统计、线上聚合。

| 工具 | 观察对象 | 用法 |
|------|----------|------|
| `adb shell dumpsys power` | 当前仍活跃的 WakeLock | 看 tag、uid、pid、持有状态，适合复现场景后立刻确认 |
| `adb shell dumpsys batterystats --history` | 一段时间内的持锁历史 | 看 acquire / release 是否成对，适合查灭屏后持续耗电 |
| Battery Historian / Android Studio App Inspection | BatteryStats 聚合结果 | 看后台持锁时长、唤醒次数、UID 归因 |
| Perfetto | CPU 运行、suspend、Alarm 唤醒附近的时序 | 把 WakeLock 与 CPU active、Doze、Alarm 触发放到同一条时间线上 |
| Play Console Android Vitals | 线上过度持锁趋势 | 看版本、设备、场景分布，作为发布守门输入 |

Android Developers 的 WakeLock 归因文档还提醒了一类容易漏掉的情况：App 没有直接调用 `PowerManager.newWakeLock()`，但系统 API 或三方库替 App 持有了锁。`AlarmManager` 触发广播时会获取名为 `*alarm*` 的 WakeLock，并把归因记到调用 App；`JobScheduler`、WorkManager、定位、FCM、媒体播放等也可能在系统侧产生可归因到 App 的 WakeLock。 [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls]

`AlarmManager` 的广播持锁窗口只覆盖 `BroadcastReceiver.onReceive()`。API 文档写明，Alarm 触发时系统会持有 CPU WakeLock，直到 `onReceive()` 返回；如果接收器里启动 service 或提交异步任务，`onReceive()` 返回后系统会释放这把锁，后续工作要有自己的调度或持锁策略。 [已验证: 官方文档, developer.android.com/reference/android/app/AlarmManager]

实战里可以把 WakeLock 接入统一审计表，字段不要只记 tag：

| 字段 | 用途 |
|------|------|
| `wakelock_tag` | 对应系统统计和 `dumpsys power` 输出 |
| `owner_module` | 区分业务来源，避免同一 tag 被多个模块复用 |
| `trigger_source` | 记录来自用户动作、推送、Alarm、WorkManager 还是重试 |
| `acquire_uptime_ms` / `release_uptime_ms` | 计算持锁时长，不受系统时间调整影响 |
| `timeout_ms` | 判断是否依赖超时兜底释放 |
| `visible_to_user` | 区分用户感知任务和静默后台任务 |
| `failure_reason` | 记录异常、取消、超时、进程退出等释放路径 |

治理规则也要写成可执行的门禁：新增 WakeLock 必须走封装；tag 固定且可归因；默认带超时；单次持锁超过业务阈值要上报；后台持锁必须有用户可见理由或调度替代方案；线上 Vitals 或 BatteryStats 出现版本回归时阻断发布。阈值不要写死成全公司统一数字，下载、媒体、导航、同步各自有不同的正常区间。

## AlarmManager 最佳实践

AlarmManager 解决的是“到了某个时间点要唤醒 App”，不是后台任务执行框架。Android Developers 对 Alarm 的定位很明确：如果只是 App 存活期间的计时，用 `Handler.postDelayed()`、协程 delay 或定时器；如果是可延后的周期后台工作，用 WorkManager；只有用户指定的时间点、日历提醒、闹钟、到点通知这类需求，才进入 AlarmManager。 [已验证: 官方文档, developer.android.com/develop/background-work/services/alarms]

Alarm 的选择顺序可以按精度从低到高排列：

| API | 触发精度 | 适用场景 | 功耗代价 |
|-----|----------|----------|----------|
| `set()` | 不早于触发时间，Android 12+ 通常可在一小时内触发，受省电状态影响 | 到点附近执行即可的用户动作 | 低 |
| `setWindow()` | 在指定窗口内触发；Android 12+ 小于 10 分钟的窗口会被裁剪到 10 分钟 | 需要时间范围，但不要求精确到秒 | 中 |
| `setInexactRepeating()` | 大致周期触发，系统可批处理 | 周期刷新、低频清理 | 低 |
| `setAndAllowWhileIdle()` | Doze 中也可触发的非精确 Alarm | 空闲状态下的近似提醒 | 中高 |
| `setExact()` | 接近指定时间触发，仍可能受部分省电策略影响 | 用户指定的精确提醒 | 高 |
| `setExactAndAllowWhileIdle()` | Doze 中也尽量按精确时间触发 | 闹钟、日历提醒等用户强预期任务 | 最高 |
| `setAlarmClock()` | 用户可见的精确闹钟，系统会为它离开低功耗模式 | 闹钟类功能 | 最高 |

非精确 Alarm 是默认选项。官方文档明确说大多数 App 可以用非精确 Alarm；Exact Alarm 会让系统难以批处理请求，在省电模式下尤其耗资源。长任务也不要直接塞进 `BroadcastReceiver.onReceive()`，应在接收器里启动 WorkManager / JobScheduler，并把业务输入持久化。 [已验证: 官方文档, developer.android.com/develop/background-work/services/alarms]

下面的写法把“到某个时间附近提醒用户”做成非精确 Alarm。读者看 `setWindow()` 的窗口长度和 `PendingIntent` 的稳定 request code。

```kotlin
fun scheduleReminderWindow(
    context: Context,
    triggerAtMillis: Long,
    reminderId: Long
) {
    val alarmManager = context.getSystemService(AlarmManager::class.java)
    val intent = Intent(context, ReminderReceiver::class.java).apply {
        action = "com.example.app.ACTION_REMINDER"
        putExtra("reminder_id", reminderId)
    }
    val pendingIntent = PendingIntent.getBroadcast(
        context,
        reminderId.hashCode(),
        intent,
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )

    alarmManager.setWindow(
        AlarmManager.RTC_WAKEUP,
        triggerAtMillis,
        10 * 60 * 1000L,
        pendingIntent
    )
}
```

这段代码允许系统在 10 分钟窗口内合并唤醒。用户不会感知秒级偏差的提醒、营销触达、低优先级日程预热，都应优先走这个模型。若任务需要下载、写库或多次网络请求，接收器只做参数校验和任务入队。

Alarm 还要处理重启和取消。设备重启后普通 Alarm 会丢失，需要在 `BOOT_COMPLETED` 后根据本地数据库重建；取消 Alarm 时必须使用与创建时等价的 `Intent` / request code / flags，否则旧 Alarm 仍会触发。业务删除提醒、用户退出登录、关闭某个功能开关时，都要同步取消对应 Alarm。

## Exact Alarm 权限变化（Android 12+）

Android 12 引入 `SCHEDULE_EXACT_ALARM` 特殊 App 访问权限；Android 13 起，目标 API 33+ 的应用可在 `SCHEDULE_EXACT_ALARM` 与 `USE_EXACT_ALARM` 中选择；Android 14 起，多数新安装且目标 API 33+、声明 `SCHEDULE_EXACT_ALARM`、又不属于豁免或预授权场景的 App，权限默认拒绝。 [已验证: 官方文档, developer.android.com/develop/background-work/services/alarms] [已验证: 官方文档, developer.android.com/about/versions/14/changes/schedule-exact-alarms]

`USE_EXACT_ALARM` 是普通权限，但只能给符合政策的日历或闹钟类应用使用；`SCHEDULE_EXACT_ALARM` 由用户或系统授予，也可能被撤销。调用 `setExact()`、`setExactAndAllowWhileIdle()`、`setAlarmClock()` 之前应检查权限；如果没有权限还直接调用，系统会抛 `SecurityException`。官方还说明，使用 `OnAlarmListener` 形式的进程内 `setExact()` 不需要 `SCHEDULE_EXACT_ALARM`，但它依赖进程存活，不适合进程被杀后仍要触发的提醒。 [已验证: 官方文档, developer.android.com/about/versions/14/changes/schedule-exact-alarms]

下面的代码只适合用户明确要求“精确时间提醒”的场景。读者看权限检查、设置页跳转和降级出口。

```kotlin
fun scheduleExactReminder(
    context: Context,
    triggerAtMillis: Long,
    reminderId: Long
) {
    val alarmManager = context.getSystemService(AlarmManager::class.java)

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
        !alarmManager.canScheduleExactAlarms()
    ) {
        val intent = Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM).apply {
            data = Uri.parse("package:${context.packageName}")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
        return
    }

    val intent = Intent(context, ReminderReceiver::class.java).apply {
        action = "com.example.app.ACTION_EXACT_REMINDER"
        putExtra("reminder_id", reminderId)
    }
    val pendingIntent = PendingIntent.getBroadcast(
        context,
        reminderId.hashCode(),
        intent,
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )

    alarmManager.setExactAndAllowWhileIdle(
        AlarmManager.RTC_WAKEUP,
        triggerAtMillis,
        pendingIntent
    )
}
```

这段代码不能单独作为产品交互。用户拒绝权限时，业务必须有降级路径：改用 `setWindow()`、延后到 WorkManager、在 App 打开时补偿提醒，或者明确告诉用户该功能依赖精确提醒权限。Android 14 的行为变更页也要求监听 `AlarmManager.ACTION_SCHEDULE_EXACT_ALARM_PERMISSION_STATE_CHANGED`，权限被授予后重新检查并重建必要的精确 Alarm。 [已验证: 官方文档, developer.android.com/about/versions/14/changes/schedule-exact-alarms]

Exact Alarm 在工程上需要审查六项：

- 是否由用户明确设置了精确时间，例如闹钟、日历、药物提醒；如果只是后台同步，改用 WorkManager。
- 是否能接受时间窗口；能接受就用 `setWindow()`，窗口不小于 10 分钟。
- 是否声明了正确权限；日历和闹钟类才评估 `USE_EXACT_ALARM`，普通应用使用 `SCHEDULE_EXACT_ALARM` 并处理授权。
- 是否在调用前检查 `canScheduleExactAlarms()`；缺权限时不要让 `SecurityException` 进入线上崩溃。
- 是否持久化了提醒数据；进程死亡、重启、权限变更后可以重建。
- 是否统计了触发次数和失败原因；同一用户、同一业务不要排出大量相邻精确 Alarm。

## 扩展：功耗回归守门

WakeLock 和 Alarm 的问题不能只靠代码审查。它们经常在功能上线几天后才出现：某个推送策略调大频率、某个异常路径不断重试、某个机型在 Doze 下延迟更长。发布前应把功耗回归守门接进 CI 和灰度监控。

| 守门项 | 检查方式 | 失败处理 |
|--------|----------|----------|
| 新增 WakeLock | 静态扫描 `newWakeLock()` 和封装入口 | 没有固定 tag、超时、释放路径时退回修改 |
| Exact Alarm 新增 | 扫描 `setExact*` / `setAlarmClock()` | 没有用户精确时间需求说明和权限降级方案时退回修改 |
| 灭屏功耗回归 | 自动化脚本灭屏 30 分钟，采集 batterystats / Perfetto | CPU active、WakeLock 时长或唤醒次数超阈值时阻断灰度 |
| 线上聚合 | Play Console Vitals + 自建 APM | 按版本、设备、业务入口定位回归来源 |
| 权限拒绝率 | 统计 `canScheduleExactAlarms()` 失败和设置页返回结果 | 拒绝率高时调整交互或降级策略 |

和 §25.2 的后台功耗治理连起来看，WakeLock 是“这段时间别睡”，Alarm 是“到点把我叫醒”。工程规范要把这两件事拆清楚：能延后就交给系统调度，必须准点才申请 Exact Alarm，必须短时间持续运行才持有 WakeLock。这样写，功耗问题才有排查入口，也有发布前拦截点。
