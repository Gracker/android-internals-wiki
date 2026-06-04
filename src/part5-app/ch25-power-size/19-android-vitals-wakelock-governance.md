---

title: "Android Vitals 过度 WakeLock 指标与治理"
chapter: "25.19"
section: "25.19"
status: ready-for-review
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36); Google Play Android vitals wake lock metric updated 2026-05"
last_verified: "2026-05-25"
last_verified_against: "Android Developers excessive/stuck wake lock docs updated 2026-05, Android Developers Blog 2025-10-02, AOSP android-16.0.0_r3 / android16-qpr2-release"
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
pipeline_stage: task6_pending
task2a_result: draft-ready-for-review
last_task2a_at: "2026-05-25T06:04:00+08:00"
task6_state: pending
task9_state: pending
---

# 25.19 Android Vitals 过度 WakeLock 指标与治理

<!-- outline-start -->
## 要点

### 🔹 指标口径：Android Vitals 到底统计什么
围绕非豁免 partial wake lock、后台/前台服务、熄屏、24 小时累计时长、28 天会话占比建立口径表，区分单次持有时长、应用会话占比和 Play 质量阈值。

### 🔹 豁免边界：audio、location、JobScheduler 用户发起 API
解释 Android Vitals 对部分有用户收益场景的豁免规则，拆开音频播放、定位、用户发起数据传输、Foreground Service 与手动 `PowerManager.WakeLock` 的责任边界。

### 🔹 归因链路：从 wake lock 名称到代码调用点
覆盖 wake lock 命名规范、PII / 混淆导致的 `_UNKNOWN`、第三方 SDK 间接持锁、WorkSource 归因和 BatteryStats 侧记录，说明 Play Console 只能给出问题入口，不能替代端侧堆栈采集。

### 🔹 本地验证：dumpsys、Batterystats 与 Battery Historian
建立开发阶段验证流程：重置 batterystats、构造后台熄屏场景、采集 bugreport、读取 partial wakelock、核对充电状态和屏幕状态，避免把前台活跃耗电误判为 Vitals 风险。

### 🔹 治理策略：替代 API、超时释放和异常兜底
按「不要持锁」「缩短持锁」「可观测持锁」三层处理：优先使用系统托管 API，手动持锁必须设置 timeout，释放路径覆盖异常、取消、进程退出和生命周期切换。

### 🔹 线上监控：比 Vitals 多拿现场
参考 Clippings 中的耗电监控结构，补充端侧采集：申请堆栈、释放堆栈、持锁时长、前后台状态、充电状态、电量、任务类型、SDK 来源，用内部阈值提前发现 Vitals 风险。

### 🔹 版本与分发影响：2026 Play 质量信号
整理 2025/2026 Android Vitals wake lock 指标的分发影响、beta 状态、店铺警告风险，以及国内渠道缺少 Vitals 数据时如何用自建指标替代。

## 扩展

### 🔸 Stuck partial wake lock 与 excessive wake lock 的差异
补充长时间未释放和累计时长过高两类问题的诊断差异。

### 🔸 Alarm / Wi-Fi scan / background network 的联合耗电规则
把 WakeLock 与 Android Vitals 其他电量指标放在同一套后台耗电治理框架中处理。

### 🔸 厂商后台限制与 Play Vitals 阈值的冲突
讨论 OEM 省电策略、白名单、前台服务展示和 Play 质量阈值之间的差异。

<!-- outline-end -->

## 为什么要单独处理 Android Vitals WakeLock

25.3 节已经覆盖 `PowerManager.WakeLock` 和 Alarm 的 API 使用，11.5 节覆盖系统 WakeLock 机制。25.19 只处理一个更窄的工程问题：当 Play Console 报出 excessive partial wake lock 后，团队怎样判断它是否真实影响发布质量，怎样把一个 wake lock tag 找回到业务代码或 SDK 调用点。

Android Vitals 的价值在于外部质量裁决。它按 Google Play 的采集口径统计用户设备上的耗电风险，能告诉团队“哪些 tag 已经越线”，但不会给出完整堆栈、任务上下文、充电状态、业务 trace id 或 SDK 版本。线上治理必须同时依赖 Play 指标和端侧监控。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md]

## 指标口径：Android Vitals 统计的是非豁免 partial wake lock

Android Vitals 的 excessive partial wake lock 口径包含四个条件：`PARTIAL_WAKE_LOCK`、非豁免、熄屏、应用在后台或处于 foreground service。统计窗口是 24 小时内所有符合条件 wake lock 的累计时长，达到 2 小时及以上就进入 excessive 判定；如果 28 天内超过 5% 的 app sessions 命中该问题，Play 质量信号可能影响推荐面和店铺提示。[已验证: 官方文档, developer.android.com/topic/performance/vitals/excessive-wakelock][已验证: 官方博客, developer.android.com/blog/posts/optimize-your-app-battery-using-android-vitals-wake-lock-metric]

| 维度 | Android Vitals excessive 口径 | 本地排查口径 |
| --- | --- | --- |
| WakeLock 类型 | 非豁免 partial wake lock | 所有 partial wake lock 都可纳入排查 |
| 应用状态 | 后台或 foreground service，且屏幕关闭 | 前台、后台、FGS、屏幕状态都记录 |
| 时间窗口 | 24 小时累计 >= 2 小时 | 单次时长、累计时长、任务维度、版本维度 |
| 发布阈值 | 28 天 sessions 占比 > 5% 可能影响 Play 可见度 | 内部阈值通常应低于 Play 阈值 |
| 证据粒度 | wake lock 名称、受影响 sessions、持续时间 | 堆栈、trace id、任务类型、SDK、版本、设备、电量 |

这个口径不能直接等同于“所有 WakeLock 都违规”。音频播放、定位、JobScheduler 用户发起任务等场景有明确用户收益，Android Vitals 会对部分系统或 API 创建的 wake lock 做豁免；但本地监控仍要记录它们的时长，原因是 OEM 省电策略、国内渠道和用户投诉不会完全按 Play 的豁免表执行。[已验证: 官方文档, developer.android.com/topic/performance/vitals/excessive-wakelock]

## Stuck 与 excessive 是两类告警

Stuck partial wake lock 指单个 partial wake lock 在后台持续持有达到小时级。官方 stuck 页面给出的 Vitals 判定是 24 小时内出现至少一次后台 1 小时的 partial wake lock。Excessive partial wake lock 关心累计量：多个短 wake lock 叠加到 2 小时，也会进入 excessive 判定。[已验证: 官方文档, developer.android.com/topic/performance/vitals/stuck-wakelock]

| 告警 | 触发形态 | 常见原因 | 处理方向 |
| --- | --- | --- | --- |
| Stuck partial wake lock | 单次持有过长 | 异常路径未释放、协程取消未进入释放、服务生命周期漏处理 | 找单个 tag 的申请/释放配对和异常路径 |
| Excessive partial wake lock | 24 小时累计过长 | 频繁后台轮询、重试风暴、SDK 间接持锁、任务切片太碎 | 降低唤醒频率，合并任务，改用系统调度 API |

本地门禁要同时设两条线：单次时长线用于抓 stuck，累计时长线用于抓 excessive。只看单次时长会漏掉高频短任务，只看累计时长会延迟发现未释放缺陷。

## 豁免边界：用户可感知任务也要保留责任边界

Android Vitals 对 audio、location、JobScheduler user-initiated API 有豁免，是因为这些场景通常存在用户可感知收益或系统托管的任务语义。豁免不代表应用可以任意持锁；它只说明这部分时间不进入 Vitals excessive partial wake lock 的计算。

治理时按责任边界拆开：

| 场景 | 推荐处理 | 排查重点 |
| --- | --- | --- |
| 音频播放 | 使用媒体播放栈和 foreground service 通知承载用户可感知任务 | 播放停止、耳机断开、路由切换后是否释放 |
| 定位 | 使用定位 API 的电量模式、批处理、被动定位和前台提示 | 后台定位频率、任务结束后的 request 移除 |
| JobScheduler / WorkManager 用户发起任务 | 用系统调度 API 表达约束、网络、电量和重试策略 | `getStopReason()`、频繁失败重试、超时 |
| 手动 `PowerManager.WakeLock` | 只保留系统 API 无法表达的短任务 | timeout、`finally`、取消路径、tag 稳定性 |

Foreground service 只能说明任务对用户可见，不会自动把手动 wake lock 变成合理。官方 best practices 要求 wake lock 使用期间让用户知道设备正在耗电，实际工程上就是 FGS 通知、任务入口和停止入口都可解释。[已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices]

## 归因链路：Play Console 给 tag，端侧补堆栈

Play Console 的入口通常是 wake lock 名称。命名不稳定时，排查会断在第一步。手动 wake lock tag 应使用固定字符串，保留 package / feature / task 三级信息；不要把邮箱、手机号、用户 id、订单号等 PII 放进 tag；不要把动态计数器或随机 id 放进 tag；不要通过反射或 `Class.getName()` 自动拼接混淆后的类名。官方文档说明 PII 命中后可能显示为 `_UNKNOWN`，动态或唯一 tag 也会破坏聚合。[已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices]

推荐格式：

```text
com.example.sync:message-refresh
com.example.media:upload-session
com.example.ble:firmware-transfer
```

系统和库也会替应用持锁。`AlarmManager` 触发广播时会用调用方归因持锁，WorkManager/JobScheduler 可能出现 `*job*/<package>/androidx.work.impl.background.systemjob.SystemJobService` 这类名称。看到这类 tag 时，不要在代码里搜索同名字符串；应回到对应 API 的任务 id、worker 名称、stop reason、重试次数和约束配置。[已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls]

AOSP 侧的调用路径提供了端侧归因的边界。`PowerManagerService.acquireWakeLockInternal()` 创建或更新服务内的 `WakeLock` 记录，随后在获取内核 wake lock 之后调用 `notifyWakeLockAcquiredLocked()`；释放路径走 `releaseWakeLockInternal()` 删除记录。BatteryStats 记账由 `BatteryStatsService.noteStartWakelock()` / `noteStartWakelockFromSource()` 接收 uid、pid、name、historyName、type 和 WorkSource 信息，再写入统计对象。[已验证: AOSP android-16.0.0_r3, frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java#acquireWakeLockInternal][已验证: AOSP android16-qpr2-release, frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java#noteStartWakelock]

这条调用路径说明两件事：Vitals 和 batterystats 能看到 tag、UID、WorkSource 和时长；业务上下文、调用堆栈、任务参数、SDK 版本必须由应用侧补采。

## 本地验证：复现 Vitals 的状态条件

本地验证要复现 Vitals 关心的状态：设备未充电、屏幕关闭、应用在后台或 FGS、任务持续运行。只在前台点按钮观察耗电排名，不能证明 Vitals 风险消失。

建议流程：

```bash
adb shell dumpsys batterystats --reset
adb shell am force-stop com.example.app
adb shell monkey -p com.example.app 1
# 触发目标后台任务后熄屏，断开 USB 或确认设备未充电
adb shell dumpsys batterystats --charged com.example.app > batterystats.txt
adb bugreport bugreport.zip
```

`dumpsys batterystats` 的 checkin 输出中，`wl` 段代表 wake lock，字段包含 full/partial/window 的时间和次数；`kwl` 代表 kernel wake lock，`wr` 代表 wakeup reason。Battery Historian 能把 bugreport 中的电量事件画成时间轴，但它仍然缺少业务堆栈，适合确认“何时持锁、持了多久、屏幕和充电状态如何”。[已验证: 官方文档, developer.android.com/tools/dumpsys][已验证: 官方文档, developer.android.com/topic/performance/power/setup-battery-historian]

Perfetto 适合补齐时间线证据。对手动 wake lock 或系统 API 间接持锁，采集时打开 `power:PowerManagement` atrace category，查看 Device State 下的 WakeLocks、Long Wake locks、Jobs、Screen state、Top app。Android 15(API 35)+ 还可用 `ProfilingManager` 做现场系统 trace 采集，但系统进程和其他应用会被脱敏，线上分析仍要依赖应用侧事件关联。[已验证: 官方博客, developer.android.com/blog/posts/optimize-your-app-battery-using-android-vitals-wake-lock-metric]

## 治理策略：少持锁、短持锁、可观测持锁

手动 wake lock 的默认结论应是删除。屏幕常亮用 `WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON` 或 Compose/视图层对应能力；可延迟任务用 WorkManager / JobScheduler；网络传输用用户发起数据传输或 FGS 类型表达；定位、音频、传感器优先使用对应平台 API 的批处理和电量策略。手动 `PowerManager.WakeLock` 只保留给系统 API 无法表达、且设备 suspend 会破坏用户任务的短窗口。[已验证: 官方博客, developer.android.com/blog/posts/optimize-your-app-battery-using-android-vitals-wake-lock-metric]

保留手动持锁时，代码约束写进封装层：

```kotlin
inline fun <T> PowerManager.WakeLock.useFor(
    timeoutMs: Long,
    block: () -> T,
): T {
    acquire(timeoutMs)
    return try {
        block()
    } finally {
        if (isHeld) release()
    }
}
```

这段封装只解决同步代码的释放问题。协程、Rx、线程池、callback 和 Binder 回调还要处理取消、超时、重复释放、进程死亡、任务迁移和生命周期切换。复杂状态机里散落 `acquire()` / `release()`，是 stuck wake lock 的高风险写法。[已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices]

对 excessive 问题，减少唤醒频率比压缩单次执行更有效。周期任务增加间隔和约束；网络重试加入指数退避和最大次数；传感器使用 batching；定位优先缓存位置、被动定位和合理精度；Alarm 使用 inexact alarm，只有用户承诺的精确时间才申请 exact alarm。详见 25.2、25.3、25.5。

## 线上监控：比 Vitals 多拿现场

参考耗电监控的结构，内部 SDK 应记录“系统关心的资源”和“排查需要的现场”。WakeLock 事件至少包含：tag、task type、业务 trace id、申请堆栈 hash、释放堆栈 hash、持锁时长、前后台状态、FGS 类型、屏幕状态、充电状态、电量、网络类型、进程名、版本、SDK 来源、WorkManager job id 或 Alarm request code。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md]

上报策略分两层：

| 层级 | 触发条件 | 上报内容 |
| --- | --- | --- |
| 事件采样 | 每次 acquire/release 配对 | tag、任务、时长、状态、版本，低采样率 |
| 异常上报 | 单次超阈值、累计超阈值、未释放、FGS 停止后仍持锁 | 完整堆栈、trace id、最近任务事件、设备状态，高优先级 |

内部阈值要低于 Play 阈值。例如单次 20 分钟、后台 24 小时累计 60 分钟即可报警；进入灰度发布时，再看版本维度、设备维度和渠道维度的 P90/P99 持锁时长。等 Play 28 天窗口越线再处理，修复反馈会被发布周期和统计延迟拉长。

第三方 SDK 持锁要建立 SDK 白名单和隔离策略。SDK 的 wake lock tag、版本、初始化入口、任务类型要进入监控字段；无法解释的 `_UNKNOWN` 或动态 tag，按发布风险处理，要求 SDK 供应方提供命名修复或开关。

## 版本与 Play 分发影响

Google 在 2025-10-02 的 Android Developers Blog 中公告：从 2026-03-01 起，未满足 excessive wake lock 质量阈值的 title 可能被排除在推荐等 prominent discovery surfaces 之外，部分场景还可能在 store listing 展示耗电警告。当前页面同时保留“metric out of beta 后影响可见度”的说明，因此状态以 Play Console 中对应指标为准；工程门禁应按已执行风险处理。[已验证: 官方博客, developer.android.com/blog/posts/optimize-your-app-battery-using-android-vitals-wake-lock-metric][已验证: 官方文档, developer.android.com/topic/performance/vitals/excessive-wakelock]

| 分发场景 | Vitals 可用性 | 治理策略 |
| --- | --- | --- |
| Google Play | 可看 Android Vitals wake lock dashboard | 用 Vitals 做外部门禁，用内部监控补现场 |
| 国内应用商店 | 通常拿不到 Play Vitals | 自建后台耗电指标，叠加 OEM 投诉和用户反馈 |
| 企业分发 / 预装 | Play 指标不完整 | 按厂商后台资源规则、bugreport 和实验室待机测试评估 |
| 小流量灰度 | 28 天 sessions 不稳定 | 内部 P90/P99、单次 stuck、累计时长更可信 |

## Alarm、Wi-Fi scan、background network 要放在同一套规则里

WakeLock 很少单独出现。后台 Alarm 会唤醒 CPU，任务执行期间可能持 partial wake lock；WorkManager/JobScheduler 会用系统 wake lock 承载执行窗口；后台 Wi-Fi scan、定位、网络重试会拉长设备 active 时间。Android Vitals 已把 excessive wakeups、background Wi-Fi scans、background network usage 和 excessive partial wake locks 放在电量类指标中，内部治理也应按同一套后台资源预算管理。

发布门禁建议按版本输出一张表：后台唤醒次数、partial wake lock 累计时长、单次最长持锁、后台网络活跃时间、Wi-Fi scan 次数、FGS 总时长、WorkManager retry 次数。单项未越线但多项同时上升，通常说明后台任务模型需要重构，详见 25.2、25.3、25.14 和 26.15。

## 厂商后台限制与 Play 阈值的差异

OEM 省电策略通常比 Play Vitals 更短周期、更强硬。Play 关注 28 天 sessions 占比；厂商策略可能在单设备、单晚待机、白名单状态和后台启动权限上做限制。国内渠道缺少 Vitals 数据时，用户投诉、系统耗电榜、厂商后台限制弹窗和实验室待机耗电要进入同一张问题单。

处理厂商冲突时保留三类证据：bugreport / batterystats 的系统时间线、应用侧 wake lock 事件、业务任务说明。确有用户收益的 FGS 或定位任务，要给产品侧明确展示和停止入口；无用户收益的后台轮询、保活、频繁拉取，按删除或系统调度改造处理。

## 发布门禁清单

- Play Console：确认 excessive partial wake lock sessions 占比、top tag、版本和设备分布。
- 本地复现：未充电、熄屏、后台/FGS 状态下采集 batterystats、bugreport、Perfetto。
- 代码约束：手动 wake lock 统一封装，必须带 timeout、`finally` 和稳定 tag。
- 任务约束：WorkManager/JobScheduler 记录 stop reason、retry、约束和 job id。
- 线上监控：单次 stuck、24 小时累计、版本 P90/P99、SDK 来源都可回查。
- 发布策略：内部阈值低于 Play 阈值，灰度期发现异常即停放量。

Android Vitals WakeLock 治理的重点，是把外部质量指标还原成可执行的工程证据：哪个 tag、哪个任务、哪段代码、哪个版本、哪个设备状态导致 CPU 在屏幕关闭后继续运行。
