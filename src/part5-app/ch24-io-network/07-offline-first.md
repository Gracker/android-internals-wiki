---
title: "离线优先架构"
chapter: "24.7"
section: "24.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-14"
last_verified_against: "Android Developers docs 2026-05-14 + AndroidX Room/WorkManager/Paging docs + Clippings 结构参考"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 1
sources:
  - type: official
    path: "https://developer.android.com/topic/architecture/data-layer/offline-first"
  - type: official
    path: "https://developer.android.com/topic/architecture/data-layer"
  - type: official
    path: "https://developer.android.com/training/data-storage/room"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/paging/v3-network-db"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [offline-first, sync, conflict-resolution, optimistic-update, room, workmanager]
related_chapters: ["24.6", "24.2", "25.4"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_reviewed_date: "2026-05-14"
task6_reviewed_by: openclaw-task6
task9_state: reviewed
task2b_state: fixed
last_task2a_at: "2026-05-14T12:17:00+08:00"
task9_result: pass-tech-review
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: 2026-05-14
last_task9_at: "2026-05-14T12:37:27+08:00"
last_task6_at: "2026-05-14T13:06:00+08:00"
last_task6_audit: "2026-06-06"
last_task6_review_log: logs/review/2026-05-14-13-review.md
task6_review_notes: "2026-05-14 Task6：四层质检通过；吸收 Task9 P2 的示例代码接入边界，轻修术语和无数据基线的批量窗口表述。满足 Task6/Task9 通过且 queue 无 pending，自动晋升 finalized。"
last_task9_audit: "2026-07-10"
last_task9_audit_log: "logs/deep-review/2026-07-10-22-audit.md"
last_task9_audit_result: "pass-idle-audit"
last_task9_audit_notes: "idle audit: 维度1（官方来源/示例 API）和维度3（Android 10-17 版本边界）快速复核通过；offline-first、Room、WorkManager、Paging RemoteMediator 口径仍与 Android Developers 文档一致；无 Android 18/API 38+ 内容，无 P0/P1。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-14
---

# 离线优先架构

## 为什么要了解离线优先架构

离线优先把网络不可靠视为数据层的常态。Android 官方定义的最低要求是：应用的关键读取在没有网络时仍能工作。它不要求每一种写操作都支持离线提交。转账、权限授予或需要实时库存确认的操作，可以继续采用仅在线写入。

平台锚点是 Android 17（API 37）/ `android-17.0.0_r1`。Room、WorkManager 和 Paging 属于 AndroidX，能力随库版本变化；示例使用这些库的稳定公开接口，不把 AndroidX 行为归因于平台版本。

24.6 讨论了可删除缓存与持久数据的区别。离线优先还要保存用户操作、同步进度、服务端版本和失败状态。它带来的读取体验来自本地权威数据源，写入可靠性来自持久待发送队列（Outbox）与服务端幂等协议。

设计离线能力前，要逐项回答：

- 哪些页面在首次安装且无网络时仍应可用？
- 哪些写操作只能在线确认，哪些可以排队，哪些允许先改本地？
- 本地与服务端都修改了同一资源时，由谁检测和处理冲突？
- 进程在服务端成功之后、本地确认之前终止，重发会不会产生重复结果？
- 账号退出、租户切换和令牌失效时，旧队列怎样停止与清理？

## 离线优先的设计原则

### 本地数据源是读取入口

离线优先的 `Repository` 同时依赖本地与网络数据源。上层通过 `Flow`、`StateFlow` 或 Paging 数据流观察本地数据；网络读取完成后写入本地，再由本地数据变化通知界面。上层不应绕过 `Repository` 直接读取网络数据源。

界面仍需要同步语义。只暴露业务实体而没有刷新状态，会让“旧数据可读”和“数据已经同步”混为一谈。建议把以下信息作为界面状态的一部分：

- 本地是否有可展示数据；
- 最近一次成功同步时间；
- 当前是否刷新；
- 最近一次刷新是否失败；
- 用户操作处于待同步、待登录、冲突还是永久失败。

### 为每类写入选择策略

Android 官方离线优先指南给出三类写入。策略应按业务风险选择，本地队列的实现能力不能决定业务结果：

| 写入策略 | 适用情况 | 本地行为 | 用户看到的结果 |
| --- | --- | --- | --- |
| 仅在线写入 | 转账、实时库存、权限变更 | 服务端确认后再更新权威本地数据 | 成功或失败均明确返回 |
| 排队写入 | 日志、遥测、非时效上报 | 操作进入持久队列，稍后发送 | 通常不阻塞当前操作 |
| 延迟写入 | 草稿、待办、可离线编辑内容 | 先更新本地，再把变更加入 Outbox | 立即可见，同时显示同步状态 |

支付或订单可以在本地显示“已提交”，但不能在服务端确认前显示“已支付”或“已下单成功”。乐观反馈的对象应是提交动作，不是尚未成立的业务结果。

### 分开保存四类状态

结构化离线数据通常需要四组表或等价持久结构：

- 业务实体：界面查询的用户数据；
- Outbox：尚未得到服务端确认的本地操作；
- 远端分页键或增量水位：服务端下一页游标、版本或同步令牌；
- 同步状态：账号、数据域、成功时间、错误分类和下一次可尝试时间。

HTTP 缓存不能替代这些表。WorkManager 自己的数据库也不是业务队列：它保存工作调度状态，不保存业务冲突、账号版本和用户可见失败。

## Room + WorkManager 的离线架构

### Room 表按读取和同步方式建模

Room 适合保存结构化本地数据。表结构应来自界面查询、同步顺序、冲突字段和账号隔离，不能逐字段照搬接口响应。索引要对应高频查询，例如“某账号下可立即发送的 Outbox 项”，迁移则要覆盖旧的待同步操作。

下面的实体骨架展示 Outbox 需要表达的协议状态。字段名仅作边界说明，业务应按服务端协议调整：

```kotlin
enum class OutboxStatus {
    PENDING,
    WAITING_FOR_AUTH,
    CONFLICT,
    PERMANENT_FAILURE,
}

@Entity(
    tableName = "sync_outbox",
    indices = [
        Index(
            value = ["localOperationId"],
            unique = true,
        ),
        Index(
            value = [
                "accountId",
                "status",
                "nextAttemptAtMillis",
                "localSequence",
            ],
        ),
    ],
)
data class SyncOutboxEntity(
    @PrimaryKey(autoGenerate = true)
    val localSequence: Long = 0,
    val localOperationId: String,
    val accountId: String,
    val resourceType: String,
    val resourceId: String,
    val operation: String,
    val payloadJson: String,
    val idempotencyKey: String,
    val expectedServerVersion: String?,
    val status: OutboxStatus,
    val attemptCount: Int,
    val nextAttemptAtMillis: Long?,
    val lastErrorCategory: String?,
    val createdAtMillis: Long,
    val updatedAtMillis: Long,
)
```

重试同一操作时必须复用同一个 `idempotencyKey`；用户发起新的业务操作时生成新键。幂等键只有在服务端保存并执行去重语义后才有效。`expectedServerVersion` 用于并发修改检测，不能用幂等键代替。

`localSequence` 由数据库生成，用于稳定选择本地操作顺序；`createdAtMillis` 用于展示和观测，不能独自决定先后。服务端确认后，可以删除 Outbox 行；若业务要求保留审计记录，应转入字段更受控、保留规则独立的历史表。

Room 2.3 及以上默认支持枚举转换，因此 `OutboxStatus` 不一定需要自定义 `@TypeConverter`。如果数据库格式要求枚举名可长期演进，可提供显式稳定编码和迁移，避免重命名枚举后无法读取旧值。

`payloadJson` 可能包含用户输入或凭据派生信息。存储前要限定字段、保留时间和日志输出；需要加密时，还要设计密钥失效后的清理路径。不要把访问令牌保存进 Outbox。

### 本地变更与 Outbox 同事务写入

下面的函数用一次 Room 事务同时更新收藏状态和插入待发送操作：

```kotlin
suspend fun setBookmarked(
    accountId: String,
    articleId: String,
    bookmarked: Boolean,
) {
    val operationId = idGenerator.newId()
    val nowMillis = clock.nowMillis()

    database.withTransaction {
        val operation = SyncOutboxEntity(
            localOperationId = operationId,
            accountId = accountId,
            resourceType = "article",
            resourceId = articleId,
            operation = "set_bookmarked",
            payloadJson = payloadEncoder.encodeBookmark(bookmarked),
            idempotencyKey = operationId,
            expectedServerVersion = articleDao.serverVersion(
                accountId = accountId,
                articleId = articleId,
            ),
            status = OutboxStatus.PENDING,
            attemptCount = 0,
            nextAttemptAtMillis = null,
            lastErrorCategory = null,
            createdAtMillis = nowMillis,
            updatedAtMillis = nowMillis,
        )

        articleDao.setBookmarkLocally(
            accountId = accountId,
            articleId = articleId,
            bookmarked = bookmarked,
            pendingOperationId = operationId,
        )
        outboxDao.insert(operation)
    }

    syncScheduler.ensureScheduled(accountId)
}
```

`pendingOperationId` 让远端确认能够对应到具体本地操作。用户快速切换两次收藏状态时，较早请求的确认不能清除较新操作的待同步标记。服务端版本读取、业务实体更新与 Outbox 插入都在事务内，账号也参与每次查询。

调度调用位于事务之后。如果进程恰好在事务提交后、调用 `ensureScheduled()` 前终止，Outbox 记录仍在；应用启动、登录恢复或其他同步入口必须再次安排唯一工作。Outbox 才是业务事实，WorkRequest 只是触发器。

网络请求不能包在 Room 事务里。发送前用短事务选择可发送记录，响应回来后再用短事务更新实体、服务端版本和 Outbox 状态，避免网络等待期间占用数据库事务。

### WorkManager 负责持久调度

WorkManager 适合离开界面、进程退出或设备重启后仍需执行的同步。`NetworkType.CONNECTED` 约束只能说明存在可用网络，不保证鉴权有效、DNS 成功或源站可访问，Worker 仍要分类处理请求结果。

下面的 Worker 骨架只从输入数据读取账号标识，业务请求数据仍保存在 Room：

```kotlin
@HiltWorker
class OutboxSyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val repository: OfflineRepository,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val accountId = inputData.getString(INPUT_ACCOUNT_ID)
            ?: return Result.failure()

        return when (repository.drainReadyOutbox(accountId)) {
            DrainResult.DRAINED -> Result.success()
            DrainResult.WAITING_FOR_USER -> Result.success()
            DrainResult.RETRYABLE_FAILURE -> Result.retry()
            DrainResult.INVALID_CONFIGURATION -> Result.failure()
        }
    }
}
```

带业务依赖的 Worker 需要 `HiltWorkerFactory` 或自定义 `WorkerFactory`。使用 `@HiltWorker` 时，`Context` 与 `WorkerParameters` 按 Hilt Work 约定采用辅助注入，其他参数只能注入 `SingletonComponent` 可提供的依赖。若项目没有 Hilt，也可以让 Worker 从应用级依赖容器获取 `Repository`。

WorkManager 的输入数据有大小限制，适合传账号或队列标识，不适合复制整批请求数据。队列内容保存在 Room 后，重新安排工作、进程恢复和账号清理都能使用同一份状态。

同步工作应按账号或租户设置唯一名称，并明确选择 `ExistingWorkPolicy`。用于“保证同一账号已有一个队列处理器”的常见选择是 `KEEP`；`REPLACE` 会取消旧 Worker，`APPEND` 还会继承前置工作的失败或取消状态。选项要结合队列语义测试，不能只为避免重复启动而随意替换。

唯一工作只限制同名 WorkManager 工作，不能限制页面协程、其他调度入口或另一个进程同时读取 Outbox。所有发送入口还要经过同一同步协调器，或在数据库事务中原子认领记录。若实现持久的“发送中”状态，还要定义 Worker 被取消或进程终止后的重新认领规则；服务端幂等仍然不可省略。

Worker 运行期间约束失效时，WorkManager 会停止它；Worker 收到停止信号后返回的 `Result` 会被忽略。协程代码应保留取消传播，网络、文件和数据库操作也要能停止。不要捕获 `CancellationException` 后转换成普通成功或失败。

WorkManager 不保证精确开始时间。需要用户立即等待结果的前台操作应走页面生命周期内的请求；同时需要进程退出后继续完成时，再把持久 Outbox 交给 WorkManager。

### 失败分类决定队列状态

统一把所有失败返回 `Result.retry()` 会制造无效请求，也会让用户看不到需要操作的错误。可以按以下边界处理：

| 结果 | 队列处理 | 调度处理 |
| --- | --- | --- |
| 连接中断、超时、可重试的服务端错误 | 保留待发送状态，增加尝试记录 | 按退避策略重试 |
| `429` | 读取合法的 `Retry-After`，记录下次可尝试时间 | 到达允许时间后再安排 |
| `401` 或登录失效 | 改为等待登录或令牌恢复 | 不进行无限退避重试 |
| 请求数据校验失败 | 标记永久失败并保存可展示原因 | 结束本次 Worker |
| `412 Precondition Failed` | 标记版本冲突并拉取远端版本 | 进入冲突策略 |
| `409 Conflict` | 按服务端定义的业务冲突处理 | 不默认当作临时网络错误 |
| 删除返回资源不存在 | 按删除协议判断是否可视为幂等成功 | 完成或转为业务失败 |

退避时间、服务端限流时间和业务重试上限属于不同约束。服务端明确给出等待时间时，业务队列要保存它；WorkManager 的退避只负责工作级重新调度。

为了处理“服务端已成功、本地尚未确认时进程终止”，发送端必须复用原操作的幂等键。服务端返回已有结果后，本地按普通成功确认。仅靠 WorkManager 的唯一工作不能防止这种重复请求。

## 冲突解决策略

### 幂等与并发控制解决不同问题

幂等键识别“同一个操作被重发”，服务端版本识别“操作基于旧数据”。两者都需要：

- 同一 Outbox 项每次重试使用相同幂等键；
- 用户再次发起操作时使用新幂等键；
- 本地保存最近确认的服务端版本；
- 写请求携带它所依据的版本；
- 服务端原子地检查版本并执行写入。

使用 HTTP ETag 作为版本时，修改请求可以发送 `If-Match`。RFC 9110 对 `If-Match` 使用强比较；弱 ETag 不能直接充当这项写入前置条件。条件不成立时返回 `412 Precondition Failed`。`409 Conflict` 用于资源当前状态与业务操作冲突，具体含义由接口协议定义。客户端要分别处理，测试不能只覆盖 `409`。

### 冲突策略按业务风险选择

| 策略 | 适用情况 | 服务端与本地需要保存 | 失败方式 |
| --- | --- | --- | --- |
| 服务端版本覆盖 | 公告、推荐、只读配置 | 服务端版本、同步水位 | 本地旧副本被替换 |
| 服务端判定的后写覆盖 | 低风险且允许覆盖的字段 | 服务端接收序列或可信时间 | 较早编辑可能丢失 |
| 字段级合并 | 字段互相独立的资料或设置 | 字段版本、修改来源 | 同字段仍可能冲突 |
| 操作级合并 | 可交换或可累积的业务操作 | 操作标识与合并规则 | 错误规则会重复或漏算 |
| 用户处理 | 文档编辑、审批和高风险业务 | 本地副本、远端副本、差异与恢复入口 | 用户需要明确选择 |

“后写覆盖”若直接比较设备时间，会受到用户改时钟、时区、离线时长和设备漂移影响。可以由服务端分配版本或接收序列；若产品必须保留用户编辑发生时间，它只作为展示与策略输入之一，不能充当唯一并发条件。

删除操作需要墓碑或等价的服务端删除版本。只从本地表删除记录，会让下一次增量同步把服务端旧对象重新写回；墓碑也需要保留期限和服务端确认规则。

同一资源存在多个待发送操作时，应定义顺序与合并条件。尚未发送的“设置收藏状态”可以保留较新的目标值；已经发送的请求必须等待确认、依靠版本条件，或由服务端按操作序列处理。订单、转账和审计事件不能按资源标识合并。

同步批量不使用通用固定条数。选择量要结合请求数据大小、单次数据库事务时间、服务端限流、Worker 可用时间和失败隔离能力。网络调用在事务外执行，服务端响应对应的数据与分页键在短事务中一起提交。

## 渐进式加载与乐观更新

### Paging 3 仍以数据库驱动界面

`RemoteMediator` 从网络加载并写入 Room，`PagingSource` 只从 Room 读取并提供给界面。网络成功但数据库事务失败时，界面不应显示那一页；数据库写入成功后，Room 使旧 `PagingSource` 失效，新的分页数据再从本地读出。

远端分页键与对应数据要在同一个事务中更新。否则进程可能只保存了下一页键，却没有保存这一页数据，恢复后会跳过内容；也可能只保存数据而重复请求同一页。

`RemoteMediator.initialize()` 返回值有明确语义：

- `LAUNCH_INITIAL_REFRESH` 发起远端刷新，并让远端 `APPEND` 与 `PREPEND` 等待该刷新成功；
- `SKIP_INITIAL_REFRESH` 跳过这次远端刷新，直接使用已有本地数据。

缓存是否需要刷新由数据域的过期规则决定，不应复制文档示例中的固定时长。刷新失败时保留本地列表，通过 `LoadState` 或业务状态给出重试入口。

分页键必须包含查询条件、账号和排序方式。只用一个全局 `nextKey`，会让不同搜索词或账号共享分页位置。服务端改变排序或游标格式时，还要清理相应分页键并启动完整刷新。

### 乐观更新需要持久状态机

乐观更新适合收藏、已读、草稿和其他可回滚或可解释失败的动作。界面状态应区分：

| 状态 | 界面含义 | 后续动作 |
| --- | --- | --- |
| 待同步 | 本地已更新，服务端尚未确认 | 允许继续浏览，显示轻量状态 |
| 已确认 | 服务端接受了对应操作 | 清除对应待同步标识 |
| 待登录 | 操作仍保留，需要恢复身份 | 引导登录后重新安排同步 |
| 冲突 | 服务端版本已变化 | 自动合并或让用户处理 |
| 永久失败 | 服务端拒绝且不会自动重试 | 回滚或保留失败副本 |

确认响应必须匹配 `pendingOperationId`。较早操作的迟到响应不能覆盖较新本地状态。永久失败时采用回滚还是保留本地副本，由业务可逆性决定；无论哪种，都要持久化结果，不能只显示一次短暂提示。

仅在线高风险操作也可以提供渐进反馈，但文案必须保持“处理中”或“等待服务端确认”。网络断开、页面退出和进程终止后，界面从本地状态恢复同一语义。

## 同步可观测性与恢复验证

接口成功率无法单独说明离线体验。建议分层记录：

- 首次本地可读耗时、本地为空与本地陈旧的比例；
- 最近成功同步时间与数据年龄；
- Outbox 条目数量、年龄分布和账号归属；
- 成功、临时失败、待登录、冲突与永久失败的数量；
- `412`、`409`、限流和服务端幂等命中的结果；
- WorkManager 工作状态、停止原因和重试次数；
- Room 事务耗时、分页键异常与数据库迁移失败。

日志中只记录内部操作标识和错误分类，不记录令牌、完整请求数据或用户正文。账号退出时要取消该账号的唯一工作，删除或隔离它的业务数据、分页键和 Outbox，并验证已经运行的请求返回后不会写回已退出账号。

恢复测试应覆盖：

- 首次安装后在飞行模式进入页面；
- 有旧数据时刷新失败；
- 本地事务提交后、安排 WorkRequest 前终止进程；
- 服务端成功后、本地确认前终止进程；
- Worker 运行期间失去网络约束或收到取消；
- 设备重启、进程重建和数据库迁移；
- 令牌失效、账号切换与退出登录；
- `429`、`412`、`409`、永久校验错误和重复幂等键；
- 设备时间错误、多端乱序写入与删除后同步；
- 用户连续修改同一资源，远端响应按不同顺序返回。

## 设计审查清单

- 读取：上层只从本地权威数据源观察数据，刷新状态与数据状态分开表达。
- 写入：每类操作明确选择仅在线、排队或延迟写入，不把高风险结果提前标成成功。
- 事务：用户可见本地变更与 Outbox 同事务；网络调用不占用 Room 事务。
- 幂等：同一操作重试复用键，新操作使用新键，服务端提供对应去重保证。
- 冲突：版本条件、`412` 和 `409` 语义写入接口协议；设备时间不是唯一顺序依据。
- 调度：WorkManager 只处理持久调度，业务请求数据与状态保存在 Room。
- 多账号：队列、唯一工作、分页键和数据均按账号隔离，退出登录有清理与迟到响应防护。
- Paging：远端分页键与数据同事务，查询条件与排序参与分页键范围。
- 乐观更新：待同步、待登录、冲突和永久失败均能在进程重建后恢复。
- 隐私：Outbox 不保存访问令牌，日志不输出完整请求数据，敏感内容有保留和清理规则。

## 参考与验证

- [Android Developers · Build an offline-first app](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [Android Developers · Data layer](https://developer.android.com/topic/architecture/data-layer)
- [Android Developers · Save data in a local database using Room](https://developer.android.com/training/data-storage/room)
- [Android Developers · Referencing complex data using Room](https://developer.android.com/training/data-storage/room/referencing-data)
- [Android Developers · Task scheduling with WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Android Developers · Define work requests](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Android Developers · Manage work](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/manage-work)
- [Android Developers · Work states](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/states)
- [Android Developers · HiltWorker](https://developer.android.com/reference/androidx/hilt/work/HiltWorker)
- [Android Developers · WorkManager Data](https://developer.android.com/reference/androidx/work/Data)
- [Android Developers · Page from network and database](https://developer.android.com/topic/libraries/architecture/paging/v3-network-db)
- [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
