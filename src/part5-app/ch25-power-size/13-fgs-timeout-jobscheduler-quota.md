---
title: "Foreground Service 超时与 JobScheduler 配额治理"
chapter: "25.13"
status: ready-for-review
drafted_date: "2026-05-21"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-05-21"
last_verified_against: "Android Developers docs 2026-02/03；AOSP android-16.0.0_r1 源码待复核"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/timeout"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/fgs/service-types"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/topic/performance/power/power-details"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/uidt"
  - type: official
    path: "https://developer.android.com/about/versions/15/changes/datasync-migration"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]"
tags: [foreground-service, jobscheduler, power, background-work, android-16]
related_chapters: ["5.8", "5.10", "11.2", "25.2", "25.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "官方文档/AOSP结构/热点变更"
---

# 25.13 Foreground Service 超时与 JobScheduler 配额治理

## 两套预算，两个系统组件

前台服务（Foreground Service，FGS）和 Job 都能承载后台工作，但系统管理它们的依据不同：

- FGS 先受启动资格、服务类型、通知和类型权限约束。部分类型还有运行时长限制，超时后由 ActivityManager 直接通知服务退出。
- Job 由 JobScheduler 根据约束、应用待机分组（App Standby Bucket）、运行时长配额和并发容量安排执行。WorkManager 与 DownloadManager 的部分任务最终也会进入这条调度路径。

因此，“启动一个 FGS，再让 Job 或 WorkManager 执行耗时工作”不能合并两边的预算。Android 16 起，与 FGS 同时运行的 Job 仍计入 Job 运行时长配额。FGS 只表达用户可感知的持续工作及其生命周期，不会给同进程的 Job 增加无限执行时间。

源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。版本边界如下：

| 系统版本 | 规则 |
| --- | --- |
| Android 14 / API 34 | 引入 `shortService` 类型及 `Service.onTimeout(int)`；面向 Android 14 的应用还要为每个 FGS 声明适当类型和相应权限 |
| Android 15 / API 35 | 对目标版本为 Android 15 及以上的应用，为 `dataSync`、`mediaProcessing` 增加后台累计时长限制；增加 `Service.onTimeout(int, int)` |
| Android 16 / API 36 | 所有运行在 Android 16 及以上设备上的应用都受新的 Job 配额规则影响，不取决于 `targetSdkVersion`；增加待执行原因历史查询 |
| Android 17 / API 37 | 延续以上公开行为；用 `android-17.0.0_r1` 的 ActivityManager 与 JobScheduler 实现核对执行路径，不添加无公开依据的新配额规则 |

## FGS 超时要区分两条路径

### `shortService`：单次短时运行，超时后是 ANR

`shortService` 从调用 `startForeground()` 时开始计时，通常只能运行约 3 分钟。它没有类型专属权限，但仍需声明基础的 `FOREGROUND_SERVICE` 权限。该类型不支持粘性重启，也不能启动其他 FGS。

超时后的顺序很明确：

1. 系统调用 `Service.onTimeout(int)`。Android 15 及以上还会调用 `Service.onTimeout(int, int)`。
2. 服务若未停止，应用会在短暂等待后降到缓存进程状态。
3. 服务仍未停止时，系统报告 ANR，信息包含 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE`。

Android 17 的 `ActiveServices.onShortFgsTimeout()` 负责派发回调并安排进程状态下调和 ANR 计时器；`onShortFgsAnrTimeout()` 最终调用 ActivityManager 的 ANR 路径。默认 3 分钟来自 `ActivityManagerConstants.DEFAULT_SHORT_FGS_TIMEOUT_DURATION`，该值可由系统配置覆盖，应用不应把本地计时器当作系统剩余时间查询接口。

用户正在与应用交互，或应用满足后台启动 FGS 的豁免条件时，再次以 `shortService` 调用 `startForeground()` 可以延长一次时限。应用不满足启动资格时，这个调用会抛出 `ForegroundServiceStartNotAllowedException`。关闭电池优化也不会取消 `shortService` 超时。

### `dataSync` 与 `mediaProcessing`：按类型累计，超时后是崩溃

当应用目标版本为 Android 15 或更高时，`dataSync` 与 `mediaProcessing` FGS 在应用处于后台期间，各自可在 24 小时窗口内累计运行 6 小时：

- 两种类型分别记账。
- 同一应用内相同类型的所有 FGS 共享该类型预算。
- 用户把应用带回前台后，系统重置计时。
- 某类型预算已经用完时，再启动该类型 FGS 会抛出 `ForegroundServiceStartNotAllowedException`。

到达限制后，系统调用 `Service.onTimeout(int, int)`，并撤销该服务的前台服务身份。服务只有几秒时间停止。Android 17 的 `ActiveServices.onFgsTimeout()` 先更新该 UID、该 FGS 类型的累计运行记录，再通过应用主线程派发超时回调；如果服务仍未退出，`onFgsCrashTimeout()` 以 `ForegroundServiceDidNotStopInTimeException` 终止应用进程。官方超时总览在 Logcat 示例中把它显示为内部 `RemoteServiceException`。这条路径与 `shortService` 的 ANR 路径不同。

`mediaProcessing` 类型页面仍保留了“未停止会 ANR”的旧文案，但 Android 17 源码和通用 FGS 超时页面均指向崩溃路径。排查 Android 15—17 设备时，应以实际异常类型和 `ActiveServices` 实现为准。

下面的实现示例只负责在超时回调中取消工作并停止服务。任务进度应在每个已确认分片结束时持久化，不能等到回调到来后再集中写入。

```kotlin
class TransferService : Service() {
    private val stopping = AtomicBoolean(false)
    private val workScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // Android 14 的 shortService 超时回调。
    override fun onTimeout(startId: Int) {
        stopAfterTimeout(
            startId,
            ServiceInfo.FOREGROUND_SERVICE_TYPE_SHORT_SERVICE
        )
    }

    // Android 15+ 的按类型超时回调。
    @RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
    override fun onTimeout(startId: Int, fgsType: Int) {
        stopAfterTimeout(startId, fgsType)
    }

    private fun stopAfterTimeout(startId: Int, fgsType: Int) {
        if (!stopping.compareAndSet(false, true)) return

        recordTimeout(startId, fgsType)
        workScope.cancel(CancellationException("FGS timeout: type=$fgsType"))
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
}
```

Android 15 及以上系统可能为 `shortService` 调用两个重载，因此示例用原子标记保证停止逻辑只执行一次。`onTimeout()` 在应用主线程接收回调，不适合等待数据库事务、网络请求或线程结束。协程取消也需要任务代码配合：网络调用、文件写入和转码循环应响应取消，并在平时就提交可恢复进度。

应用没有公开 API 可以查询 `dataSync` 或 `mediaProcessing` 的系统剩余预算。应用侧可以记录自身 FGS 的运行区间，用于提前结束新分片和分析异常；这份记录无法感知系统配置、其他进程中的同类型服务以及系统计时重置，只能作为保守估计。

## Android 16 起，FGS 不再豁免 Job 运行时长配额

Android 16 的 JobScheduler 配额变化适用于所有应用。普通 Job 和加急 Job（expedited job）的运行时长会受到三类因素影响：

- 应用所在的应用待机分组。Android 16 开始，Active 分组也有较宽松的运行时长配额。
- Job 在应用处于顶部可见状态时启动，随后继续在后台运行。离开可见状态后，后续运行时间进入配额计算。
- Job 与 FGS 同时运行。FGS 进程状态不再让 Job 免费运行。

该变化覆盖直接使用 JobScheduler 的任务，也覆盖通过 WorkManager 和 DownloadManager 调度的相应工作。应用进程当前可见时，普通 Job 不受这张后台配额表限制；仅有 FGS 的进程在 Android 16 及以上仍按应用待机分组计算。

官方资源限制表给出的当前近似值如下。它是排查和容量设计参考，不是 API 契约；系统可以通过 DeviceConfig 和设备策略调整参数。

| 应用待机分组 | 普通 Job 近似运行额度 | 加急 Job 近似运行额度 |
| --- | --- | --- |
| Active | 滚动 60 分钟内最多 20 分钟 | 滚动 24 小时内最多 30 分钟 |
| Working set | 滚动 4 小时内最多 10 分钟 | 滚动 24 小时内最多 15 分钟 |
| Frequent | 滚动 12 小时内最多 10 分钟 | 滚动 24 小时内最多 10 分钟 |
| Rare | 滚动 24 小时内最多 10 分钟 | 滚动 24 小时内最多 10 分钟 |
| Restricted | 每天一次、最多 10 分钟 | 滚动 24 小时内最多 5 分钟 |

用户在系统设置中允许应用“不受电池限制”会给 Job 更宽松的执行额度；Android 16 及以上仍不能据此假定执行时间无限。充电、热状态、内存压力、网络约束和系统健康策略仍会改变任务何时启动、何时停止。

### Android 17 源码怎样表达这项规则

Android 17 把 JobScheduler 服务端代码放在 `frameworks/base/apex/jobscheduler` 下。配额和并发由不同组件负责：

- `QuotaController` 记录包在各待机分组中的执行会话，计算普通 Job 与加急 Job 是否仍有运行额度，并把结果写回 Job 的配额约束条件。
- `JobConcurrencyManager` 根据设备内存、当前内存压力、屏幕状态和工作类型分配同时运行的槽位。它限制“此刻能并行多少 Job”，不负责计算某个包在时间窗口内还剩多少运行额度。
- `JobPackageTracker` 记录待执行、活动和已停止 Job 的统计信息，供诊断与转储使用；它不是配额决策器。

`QuotaController` 中两个兼容性变更默认关闭：`OVERRIDE_QUOTA_ENFORCEMENT_TO_TOP_STARTED_JOBS` 和 `OVERRIDE_QUOTA_ENFORCEMENT_TO_FGS_JOBS`。关闭状态对应 Android 16 的新行为。测试时启用它们，会恢复顶部状态启动 Job 或 FGS 并发 Job 的旧豁免，用于做前后对照。

源码中的 `isWithinQuotaLocked()` 还明确放行 `shouldTreatAsUserInitiatedJob()`。这说明用户发起的数据传输 Job 不走普通 Job 的待机分组运行时长配额；它仍受自身最长执行时间、声明约束和系统健康限制。`QuotaController` 的窗口与额度可以由 `DeviceConfig.NAMESPACE_JOB_SCHEDULER` 更新，因此业务代码不应复制源码默认常量来预测停止时刻。

`android-17.0.0_r1` 中不存在 `JobConcurrencyLimiter`、`checkUidQuota()`、`recordForegroundServiceTimeout()`、`FLAG_EXPEDED`，也没有“AI 智能配额调度”或“紧急任务绕过配额”这类行为。相关伪代码不能作为实现依据。

## 任务类型选择

选型时依次确认：工作是否由用户明确触发，用户是否需要持续看到进度，任务能否推迟或中断，系统是否已有专用 API。

| 场景 | 建议 API | 选择理由 | 需要注意的边界 |
| --- | --- | --- | --- |
| 用户点击上传、下载，传输可能持续较久 | User-Initiated Data Transfer Job（UIDT） | Android 14+ 提供立即启动、通知和进度展示语义；不计入普通 Job 的待机分组运行时长配额 | 只能在应用可见或其他允许条件下调度；必须声明权限并设置通知；仍受系统健康限制 |
| 后台同步、日志上传、可推迟且可重试的数据传输 | WorkManager | 提供持久任务、约束、退避和重试管理 | Android 官方把短时且可中断的后台传输作为主要适用范围；运行在 JobScheduler 上时会继承系统配额 |
| 需要 UIDT、预取、命名空间或待执行原因等平台能力 | JobScheduler | 直接使用平台 Job 能力，诊断信息更完整 | 应用自行管理 `JobService` 异步生命周期、`jobFinished()`、停止和恢复 |
| 数分钟内完成且必须立即执行的关键工作 | FGS `shortService` | 用户可看到通知，适合短时、不可推迟的收尾工作 | 约 3 分钟；不支持粘性重启；超时未停会 ANR |
| 用户可感知的媒体转码 | FGS `mediaProcessing` | 服务类型与媒体处理用途一致 | 目标版本为 Android 15+ 时受后台 6 小时累计限制；长转码仍要分段恢复 |
| 连续连接外设并传输数据 | 专用 API 或 FGS `connectedDevice` | Companion Device Manager 等专用能力通常更符合持续连接语义 | 先检查蓝牙、USB、投屏等场景是否已有专用 API |
| 到准确时刻提醒用户 | AlarmManager | 负责时间触发 | Alarm 只负责唤醒或发出事件，不应在接收器中执行长任务；精确闹钟规则见 25.3 |

UIDT 在 Android 14 / API 34 引入，目前没有统一封装它的 Jetpack API。低版本可以使用 WorkManager 的前台工作方案。UIDT 要求 `RUN_USER_INITIATED_JOBS` 权限、`JobInfo.Builder.setUserInitiated(true)`，并在执行期间通过 `JobService.setNotification()` 展示通知；传输结束后必须调用 `jobFinished()`。

WorkManager 适合作为普通持久后台工作的默认选择，但它不会取消平台限制。任务进入 SystemJobService 后，网络、电量、待机分组和运行时长配额仍由系统判断。需要平台特有诊断或 UIDT 时，直接使用 JobScheduler 更清楚。

## 停止不是失败：先记录原因，再决定是否重试

系统停止 Job 时，`JobParameters.getStopReason()` 提供公开停止原因。Android 16 文档还建议记录 `WorkInfo.getStopReason()`；采用该字段时要确认项目使用的 WorkManager 版本已经提供相应 API。Android 16 / API 36 增加的 `JobScheduler.getPendingJobReasonsHistory()` 用于解释 Job 为何迟迟没有启动，两类信息不能混用：

- 停止原因描述一次已经开始的执行为何结束。
- 待执行原因历史描述 Job 在一段时间内被哪些条件阻挡。

直接实现 `JobService` 的应用还要注意 Android 16 的 `STOP_REASON_TIMEOUT_ABANDONED`。如果与正在运行 Job 对应的 `JobParameters` 已被垃圾回收，而应用又没有调用 `jobFinished()`，系统会把它视为被遗弃的 Job 并停止。WorkManager、DownloadManager 等框架会管理这段生命周期，通常不受该问题影响。

重试策略应按原因分组：

| 原因类别 | 处理方式 |
| --- | --- |
| 约束变化，如网络断开、充电条件失效 | 保存当前分片，等待约束再次满足 |
| 运行时长配额或系统超时 | 停止派发新分片，等待下一次系统调度或用户入口 |
| 用户取消 | 清除继续执行意图，保留是否删除临时文件的产品语义 |
| 应用升级、进程退出、内存压力 | 从持久化游标恢复，不能依赖内存队列 |
| 业务不可恢复错误，如鉴权失效或文件损坏 | 停止自动重试，向用户说明所需操作 |

所有取消都需要向执行代码传播。`onStopJob()` 返回值只告诉 JobScheduler 是否需要重新调度，不会替应用停止线程、协程、网络请求或编解码器。如果旧执行仍在运行，新一轮 Job 又从同一游标启动，就会出现重复上传、重复写文件或资源竞争。

## 线上观测应覆盖完整执行记录

配额问题常表现为“任务偶尔没有完成”。一次执行至少要能回答：谁启动、何时进入后台、系统为何停止、保存到哪个游标、下一次如何恢复。

| 事件 | 建议字段 | 用途 |
| --- | --- | --- |
| FGS 启动/停止 | FGS 类型、入口、系统版本、目标版本、基于 `elapsedRealtime` 的开始/结束时间、是否处于应用前台 | 计算应用侧运行区间，区分用户操作与后台恢复 |
| FGS 超时 | `startId`、`fgsType`、回调到停止调用的耗时、最近确认的分片 | 判断回调是否及时退出，确认恢复位置 |
| Job 启动/停止 | Job ID、命名空间、待机分组、停止原因、是否与 FGS 同时运行 | 区分配额、约束和生命周期问题 |
| Job 待执行 | 当前 pending reasons、API 36+ 的 reason history、约束快照 | 解释长时间未启动 |
| WorkManager | 唯一工作名、标签、`runAttemptCount`、停止原因、退避策略 | 检查重试是否持续增加耗电 |
| 数据传输 | 已确认字节或分片、总量估计、网络类型、服务端幂等键 | 支持断点续传并识别重复请求 |
| 用户恢复 | 通知或页面入口、恢复前游标、恢复结果 | 评估系统停止对用户体验的影响 |

不要把 URL、文件名、账号或随机任务 ID 直接用作指标维度。它们适合进入受控日志或追踪记录；聚合指标只保留任务类型、系统版本、设备型号、ROM 版本、网络类型、待机分组和停止原因等有限集合。

告警阈值应来自本产品基线。可以按系统版本与 ROM 比较 FGS 超时率、`STOP_REASON_QUOTA` 占比、待执行时长和用户手动恢复率。单个信号上涨只能说明现象，多个指标在同一版本同时偏离基线时，再进入任务模型、配额或厂商策略排查。

## 把长任务改造成可恢复执行

### 每个确认点都持久化

下载可按 Range 与校验块记录，上传可按服务端确认的分片记录，转码可按输入时间段和输出文件校验记录。持久化游标应代表“服务端或文件系统已经确认完成”的位置，不能只记录“准备开始”的位置。

每个分片应具备幂等语义。系统在写入结果后、更新本地状态前终止进程时，下一轮可能重复提交当前分片；服务端幂等键、临时文件加原子重命名、内容哈希都能避免重复产生副作用。

### 超时回调只做停止动作

应用不能准确读取系统剩余 FGS 预算，所以迁移策略不能依赖“还剩多少分钟”。任务循环可以根据应用侧保守计时决定是否领取下一个分片，但已领取分片也必须允许取消。`onTimeout()` 负责记录事件、发出取消、释放资源并停止服务。

### FGS 与 Job 共享状态，不同时执行同一份工作

FGS、UIDT、Job 和 WorkManager 都应读取同一份持久任务记录，并通过租约或原子状态更新取得执行权。任务从 FGS 转交给 WorkManager 时，先停止旧执行并提交游标，再安排恢复任务。通知中的继续按钮也走同一套取得执行权流程。

“FGS 展示进度，Job 在后台做相同工作”会同时消耗资源，还可能产生两个执行者。若产品需要 FGS 通知，应让通知观察当前执行状态；计算和传输仍只有一个执行者。

### 约束与任务价值匹配

用户等待的 UIDT 不应添加与产品承诺冲突的充电或空闲约束。周期同步可以等待未计费网络或充电；安全上报可能允许任意网络但限制重试次数。约束过多会导致长期待执行，约束过少会增加唤醒和电量消耗。

## 厂商限制属于第二层证据

AOSP 定义平台基线，厂商还可能调整后台启动、通知、待机分组、电池管理和后台网络策略。问题记录至少应包含设备型号、ROM 完整版本、系统构建号、电池优化状态、通知权限、应用待机分组、是否锁屏以及复现步骤。

厂商行为应按设备和版本保存证据。单台设备上的停止不能直接归因于某品牌；先检查公开停止原因、ANR/崩溃信息、`dumpsys` 与系统日志，再记录厂商设置页面和复现差异。

## 调试与复现

下面的命令用于缩短 FGS 时间限制、触发或停止 Job，并对比 Android 16 配额兼容开关。占位符需替换为测试包名和 Job ID；这些设置只应在测试设备使用。

```bash
# 在测试包上启用 Android 15 的限时 FGS 行为，并把窗口临时缩短。
adb shell am compat enable FGS_INTRODUCE_TIME_LIMITS APP_PACKAGE_NAME
adb shell device_config put activity_manager data_sync_fgs_timeout_duration 60000
adb shell device_config put activity_manager media_processing_fgs_timeout_duration 60000

# 触发一个已调度 Job；-s 要求所有约束均已满足，-f 会忽略部分技术约束。
adb shell cmd jobscheduler run -s APP_PACKAGE_NAME JOB_ID
adb shell cmd jobscheduler run -f APP_PACKAGE_NAME JOB_ID

# 让正在运行的 Job 按执行超时路径停止。
adb shell cmd jobscheduler timeout APP_PACKAGE_NAME JOB_ID

# 改变并读取应用待机分组。
adb shell am set-standby-bucket APP_PACKAGE_NAME restricted
adb shell am get-standby-bucket APP_PACKAGE_NAME

# 启用旧豁免做对照；开关名中的 OVERRIDE 表示覆盖 Android 16 默认执行方式。
adb shell am compat enable OVERRIDE_QUOTA_ENFORCEMENT_TO_TOP_STARTED_JOBS APP_PACKAGE_NAME
adb shell am compat enable OVERRIDE_QUOTA_ENFORCEMENT_TO_FGS_JOBS APP_PACKAGE_NAME

# 查看 FGS、JobScheduler 和 Doze 状态。
adb shell dumpsys activity services APP_PACKAGE_NAME
adb shell dumpsys jobscheduler
adb shell dumpsys deviceidle

# 测试结束后恢复上述配置。
adb shell device_config delete activity_manager data_sync_fgs_timeout_duration
adb shell device_config delete activity_manager media_processing_fgs_timeout_duration
adb shell am compat reset FGS_INTRODUCE_TIME_LIMITS APP_PACKAGE_NAME
adb shell am compat reset OVERRIDE_QUOTA_ENFORCEMENT_TO_TOP_STARTED_JOBS APP_PACKAGE_NAME
adb shell am compat reset OVERRIDE_QUOTA_ENFORCEMENT_TO_FGS_JOBS APP_PACKAGE_NAME
adb shell am set-standby-bucket APP_PACKAGE_NAME active
```

`jobscheduler run -s` 与 `-f` 不能同时使用。`timeout` 只作用于正在执行的 Job，相当于以公开停止原因 `STOP_REASON_TIMEOUT` 触发停止。具体设备支持的选项应再用 `adb shell cmd jobscheduler help` 核对。

复现用例至少覆盖：

- 页面内启动后退到后台，确认顶部状态结束后 Job 开始计入配额。
- FGS 与 Job 同时运行，对比默认行为和 `OVERRIDE_QUOTA_ENFORCEMENT_TO_FGS_JOBS`。
- 网络中断、锁屏、切换待机分组后，确认取消能到达执行代码且游标可恢复。
- 缩短 `dataSync` / `mediaProcessing` 时限，确认 `onTimeout(int, int)` 立即停止服务。
- `shortService` 超时，确认先收到回调；测试构建可以继续观察 ANR，线上逻辑不得故意等待 ANR。

## 小结

FGS 时长限制和 Job 运行时长配额是两套独立规则。`shortService` 超时未停会触发 ANR；目标版本为 Android 15 及以上的 `dataSync`、`mediaProcessing` 在后台共享各自的 6 小时窗口，超时未停会导致应用崩溃。Android 16 起，顶部状态启动后转入后台的 Job、与 FGS 同时运行的 Job，都不能继续使用旧的配额豁免。

稳定的长任务依赖可恢复设计：分片、已确认游标、幂等提交、取消传播、停止原因和用户恢复入口。系统允许任务开始，只代表当前条件满足；每次执行仍要准备在任意确认点结束。

## 参考资料

- [Foreground service timeouts | Android Developers](https://developer.android.com/develop/background-work/services/fgs/timeout)
- [Foreground service types | Android Developers](https://developer.android.com/develop/background-work/services/fgs/service-types)
- [Behavior changes: all apps | Android 16 | Android Developers](https://developer.android.com/about/versions/16/behavior-changes-all)
- [Power management resource limits | Android Developers](https://developer.android.com/topic/performance/power/power-details)
- [User-initiated data transfer | Android Developers](https://developer.android.com/develop/background-work/background-tasks/uidt)
- [Data transfer background task options | Android Developers](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)
- [`Service.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/Service.java)
- [`ActiveServices.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java)
- [`ActivityManagerConstants.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java)
- [`QuotaController.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/controllers/QuotaController.java)
- [`JobConcurrencyManager.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/JobConcurrencyManager.java)
- [`JobPackageTracker.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/JobPackageTracker.java)
- [`JobSchedulerShellCommand.java` | AOSP `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerShellCommand.java)
