---
title: "离线优先架构"
chapter: "24.7"
section: "24.7"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Android Developers offline-first, Room, WorkManager, HiltWorker and Paging docs current through 2026-08-15; AndroidX stable Room 2.8.4, WorkManager 2.11.2 and Paging 3.5.1 release notes; RFC 9110"
confidence: high
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
  - type: official
    path: "https://developer.android.com/training/data-storage/room/referencing-data"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/manage-work"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/states"
  - type: official
    path: "https://developer.android.com/reference/androidx/hilt/work/HiltWorker"
  - type: official
    path: "https://developer.android.com/reference/androidx/work/Data"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/room"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/work"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/paging"
  - type: standard
    path: "https://www.rfc-editor.org/rfc/rfc9110.html"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [offline-first, sync, conflict-resolution, optimistic-update, room, workmanager]
related_chapters: ["24.6", "24.2", "25.4"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_review_finalize_at: "2026-08-15T10:49:38+08:00"
last_review_finalize_run_id: "20260815-104938-gracker-writing-review"
last_draft_polish_at: "2026-08-15T10:49:38+08:00"
last_draft_polish_run_id: "20260815-104938-gracker-writing"
---

# 离线优先架构

## 离线优先先保证什么

离线优先把网络中断、变慢和暂时不可用视为数据层的常见条件。Android 官方给出的最低要求是：应用的主要内容在没有网络时仍可读取。离线优先不要求每一种写操作都支持离线提交，转账、权限授予或需要实时库存确认的操作仍可采用仅在线写入。

平台锚点是 Android 17（API 37）/ `android-17.0.0_r1`。Room 是基于 SQLite 的持久化库，WorkManager 用于持久后台调度，Paging 用于分页加载；它们都属于 AndroidX，能力随库版本变化。示例只使用这些库的稳定公开接口，不把 AndroidX 行为归因于平台版本。

24.6 区分了可删除缓存与持久数据。离线优先还要保存用户操作、同步进度、服务端版本和失败状态。本地权威数据源是界面与业务逻辑唯一读取的数据副本；它可能暂时落后于服务端，但应用不会因网络状态不同而读取两套相互冲突的数据。Outbox 是数据库中的待发送操作表，服务端幂等协议则用固定标识识别同一次操作的重复请求。两者共同保证写入可恢复。

设计离线能力前，要逐项回答：

- 哪些页面在首次安装且无网络时仍应可用？
- 哪些写操作只能在线确认，哪些可以排队，哪些允许先改本地？
- 本地与服务端都修改了同一资源时，由谁检测和处理冲突？
- 进程在服务端成功之后、本地确认之前终止，重发会不会产生重复结果？
- 账号退出、租户切换和令牌失效时，旧队列怎样停止与清理？

## 离线优先的设计原则

### 本地数据源是读取入口

离线优先的 `Repository` 是协调本地与网络数据源的数据访问组件。`Flow` 表示可持续发出新值的异步数据流，`StateFlow` 还会保留当前值，Paging 数据流则按页提供列表。界面与业务逻辑只观察本地数据；网络读取完成后先写入本地，再由本地数据变化通知界面。它们不应绕过 `Repository` 直接读取网络数据源。

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

“延迟写入”也常称为乐观更新：服务端确认前先改变本地状态，并把失败或冲突保留下来供后续处理。支付或订单可以在本地显示“已提交”，但不能在服务端确认前显示“已支付”或“已下单成功”。提前反馈的对象是提交动作，不能把尚未成立的业务结果标为成功。

### 分开保存四类状态

结构化离线数据通常需要四组表或等价持久结构：

- 业务实体：界面查询的用户数据；
- Outbox：尚未得到服务端确认的本地操作；
- 远端分页键或增量水位：分页键记录某组查询从哪个游标继续取下一页，增量水位记录本地已经同步到哪个版本、时间点或令牌；
- 同步状态：账号、数据域、成功时间、错误分类和下一次可尝试时间。

HTTP 缓存不能替代这些表。WorkManager 自己的数据库也不是业务队列：它保存工作调度状态，不保存业务冲突、账号版本和用户可见失败。

## Room + WorkManager 的离线架构

### Room 表按读取和同步方式建模

Room 适合保存结构化本地数据。表结构应来自界面查询、同步顺序、冲突字段和账号隔离，不能逐字段照搬接口响应。数据库索引会额外保存可快速查找的列值，适合“某账号下可立即发送的 Outbox 项”这类高频查询；索引也会增加写入与存储成本。数据库迁移还要覆盖升级前遗留的待同步操作。

这个实体骨架展示 Outbox 需要表达的协议状态。字段名仅用于说明边界，业务应按服务端协议调整：

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

重试同一操作时必须复用同一个 `idempotencyKey`；用户发起新的业务操作时生成新键。服务端需要记录这个键及处理结果，再次收到同一键时返回已有结果或避免重复产生副作用。`expectedServerVersion` 表示本次修改依据的服务端版本，用于发现“读取之后又被别人修改”的并发冲突。幂等键识别重复操作，版本字段识别数据变化，两者不能互相替代。

`localSequence` 由数据库生成，用于稳定选择本地操作顺序；`createdAtMillis` 用于展示和观测，不能独自决定先后。服务端确认后，可以删除 Outbox 行；若业务要求保留审计记录，应转入字段更受控、保留规则独立的历史表。

Room 2.3 及以上在没有自定义转换器时，会把枚举名称转换为字符串保存；自定义 `@TypeConverter` 的优先级更高。当前稳定版 Room 2.8.4 仍保留该行为。枚举常量改名后，旧字符串可能无法解析；需要长期演进的数据库格式应使用稳定编码，并为已有数据提供迁移。

`payloadJson` 可能包含用户输入或凭据派生信息。存储前要限定字段、保留时间和日志输出；需要加密时，还要设计密钥失效后的清理路径。不要把访问令牌保存进 Outbox。

### 本地变更与 Outbox 同事务写入

这个函数用一次 Room 事务同时更新收藏状态和插入待发送操作：

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

`pendingOperationId` 让远端确认能够对应到具体本地操作。用户快速切换两次收藏状态时，较早请求的确认不能清除较新操作的待同步标记。服务端版本读取、业务实体更新与 Outbox 插入都在同一事务中：三项写入一起提交或一起回滚，账号也参与每次查询。

调度调用位于事务之后。如果进程恰好在事务提交后、调用 `ensureScheduled()` 前终止，Outbox 记录仍在；应用启动、登录恢复或其他同步入口必须再次安排“唯一工作”。唯一工作以固定名称避免重复调度同一逻辑任务。Outbox 保存待发送这一业务事实，`WorkRequest` 只记录何时、在什么约束下运行 `Worker`。

网络请求不能包在 Room 事务里。发送前用短事务选择可发送记录，响应回来后再用短事务更新实体、服务端版本和 Outbox 状态，避免网络等待期间占用数据库事务。

### WorkManager 负责持久调度

WorkManager 会持久保存调度记录，适合离开界面、进程退出或设备重启后仍需执行的同步。`NetworkType.CONNECTED` 约束只能说明系统判断当前有可用网络，不能保证鉴权有效、DNS 成功或源站可访问，`Worker` 仍要分类处理请求结果。

这个 `Worker` 骨架只从输入数据读取账号标识，业务请求数据仍保存在 Room：

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

带业务依赖的 `Worker` 需要 `HiltWorkerFactory` 或自定义 `WorkerFactory`。Hilt 是依赖注入库；使用 `@HiltWorker` 时，“辅助注入”表示 `Context` 与 `WorkerParameters` 由 WorkManager 在运行时提供，Hilt 注入其余应用依赖。这些应用依赖必须能由 `SingletonComponent` 提供，也就是处于应用生命周期范围。没有使用 Hilt 的项目，可以让 `Worker` 从应用级依赖容器获取 `Repository`。

WorkManager 的输入与输出 `Data` 存在序列化大小上限，由 `Data.MAX_DATA_BYTES` 定义。它适合传账号或队列标识，不适合复制整批请求数据。队列内容保存在 Room 后，重新安排工作、进程恢复和账号清理都能使用同一份状态。

同步工作应按账号或租户设置唯一名称，并明确选择 `ExistingWorkPolicy`。`KEEP` 保留已有工作并忽略新请求，适合“同一账号已有一个队列处理器”的场景；`REPLACE` 会取消旧 `Worker`；`APPEND` 把新工作接到旧工作之后，也会继承前置工作的失败或取消状态。若新工作不应受前置失败影响，可评估 `APPEND_OR_REPLACE`。策略要结合队列顺序与取消语义测试，不能只为避免重复启动而随意替换。

唯一工作只限制同名 WorkManager 工作，不能限制页面协程、其他调度入口或另一个进程同时读取 Outbox。所有发送入口还要经过同一同步协调器，或在数据库事务中“原子认领”记录：用带状态条件的更新把待发送行标为已认领，只有更新成功的调用方可以发送。若实现持久的“发送中”状态，还要定义 `Worker` 被取消或进程终止后的重新认领规则；服务端幂等仍然不可省略。

Worker 运行期间约束失效时，WorkManager 会停止它；Worker 收到停止信号后返回的 `Result` 会被忽略。协程代码应保留取消传播，网络、文件和数据库操作也要能停止。不要捕获 `CancellationException` 后转换成普通成功或失败。

WorkManager 不保证精确开始时间。需要用户立即等待结果的前台操作应走页面生命周期内的请求；同时需要进程退出后继续完成时，再把持久 Outbox 交给 WorkManager。

### 失败分类决定队列状态

统一把所有失败返回 `Result.retry()` 会制造无效请求，也会让用户看不到需要操作的错误。指数退避是每次临时失败后逐步延长等待时间，它只适用于预期稍后可能恢复的错误。队列状态可以按以下边界处理：

| 结果 | 队列处理 | 调度处理 |
| --- | --- | --- |
| 连接中断、超时、可重试的服务端错误 | 保留待发送状态，增加尝试记录 | 按退避策略重试 |
| `429` | 读取合法的 `Retry-After`；该响应头给出服务端允许重试的时间或等待秒数 | 记录下次可尝试时间，到时再安排 |
| `401` 或登录失效 | 改为等待登录或令牌恢复 | 不进行无限退避重试 |
| 请求数据校验失败 | 标记永久失败并保存可展示原因 | 结束本次 Worker |
| `412 Precondition Failed` | 标记版本冲突并拉取远端版本 | 进入冲突策略 |
| `409 Conflict` | 按服务端定义的业务冲突处理 | 不默认当作临时网络错误 |
| 删除返回资源不存在 | 按删除协议判断是否可视为幂等成功 | 完成或转为业务失败 |

表中的临时传输错误、身份失效、数据错误与版本冲突会进入不同队列状态。退避时间、服务端限流时间和业务重试上限也属于不同约束。服务端明确给出等待时间时，业务队列要保存它；WorkManager 的退避只负责工作级重新调度。

为了处理“服务端已成功、本地尚未确认时进程终止”，发送端必须复用原操作的幂等键。服务端返回已有结果后，本地按普通成功确认。仅靠 WorkManager 的唯一工作不能防止这种重复请求。

## 冲突解决策略

### 幂等与并发控制解决不同问题

幂等键识别“同一个操作被重发”，服务端版本识别“操作基于旧数据”。前者防止重复执行副作用，后者防止旧副本覆盖新数据。两者都需要：

- 同一 Outbox 项每次重试使用相同幂等键；
- 用户再次发起操作时使用新幂等键；
- 本地保存最近确认的服务端版本；
- 写请求携带它所依据的版本；
- 服务端原子地检查版本并执行写入。

使用 HTTP `ETag`（实体标签）作为版本时，修改请求可以发送 `If-Match`。弱 ETag 以 `W/` 开头，只表示两个响应在语义上等价；强 ETag 才能标识完全匹配的表示。RFC 9110 要求 `If-Match` 做强比较，因此弱 ETag 无法满足这项写入前置条件。版本不匹配通常返回 `412 Precondition Failed`；`409 Conflict` 表示资源当前状态与业务操作冲突，具体含义由接口协议定义。客户端要分别处理，测试不能只覆盖 `409`。

### 冲突策略按业务风险选择

| 策略 | 适用情况 | 服务端与本地需要保存 | 失败方式 |
| --- | --- | --- | --- |
| 服务端版本覆盖 | 公告、推荐、只读配置 | 服务端版本、同步水位 | 本地旧副本被替换 |
| 服务端判定的后写覆盖 | 低风险且允许覆盖的字段 | 服务端接收序列或可信时间 | 较早编辑可能丢失 |
| 字段级合并 | 字段互相独立的资料或设置 | 字段版本、修改来源 | 同字段仍可能冲突 |
| 操作级合并 | 可交换或可累积的业务操作 | 操作标识与合并规则 | 错误规则会重复或漏算 |
| 用户处理 | 文档编辑、审批和高风险业务 | 本地副本、远端副本、差异与恢复入口 | 用户需要明确选择 |

“后写覆盖”表示服务端保留它判定为较晚的修改。若直接比较设备时间，结果会受到用户改时钟、时区、离线时长和设备漂移影响。可以由服务端分配版本或接收序列；若产品必须保留用户编辑发生时间，它只作为展示与策略输入之一，不能充当唯一并发条件。

删除操作需要“墓碑”或等价的服务端删除版本。墓碑保留资源标识、删除版本和时间，不再保留正常业务内容，用于告诉其他副本“该资源已经删除”。只从本地表移除记录，会让下一次增量同步把服务端旧对象重新写回；墓碑也需要保留期限和服务端确认规则。

同一资源存在多个待发送操作时，应定义顺序与合并条件。操作合并是把多个尚未发送、业务含义可替代的变更压成一个目标状态。例如，“设置收藏状态”可以只保留较新的目标值；已经发送的请求必须等待确认、依靠版本条件，或由服务端按操作序列处理。订单、转账和审计事件不能按资源标识合并。

同步批量不使用通用固定条数。选择量要结合请求数据大小、单次数据库事务时间、服务端限流、Worker 可用时间和失败隔离能力。网络调用在事务外执行，服务端响应对应的数据与分页键在短事务中一起提交。

## 渐进式加载与乐观更新

### Paging 3 仍以数据库驱动界面

`RemoteMediator` 是 Paging 在本地数据不足或需要刷新时调用的网络加载器，它把远端结果写入 Room，不直接把网络响应交给界面。`PagingSource` 是本地分页读取接口，只从 Room 取数据并提供给界面。网络成功但数据库事务失败时，界面不应显示那一页；数据库写入成功后，Room 使旧 `PagingSource` 失效，再由新实例从本地读出更新后的分页数据。

远端分页键记录某组查询下一次应使用的服务端游标。它与对应数据要在同一个事务中更新，否则进程可能只保存了下一页键，却没有保存这一页数据，恢复后会跳过内容；也可能只保存数据而重复请求同一页。

`RemoteMediator.initialize()` 返回值决定首次创建分页流时是否访问网络。`REFRESH` 表示重建或刷新列表，`APPEND` 和 `PREPEND` 分别表示向列表末尾和开头加载：

- `LAUNCH_INITIAL_REFRESH` 发起远端刷新，并让远端 `APPEND` 与 `PREPEND` 等待该刷新成功；
- `SKIP_INITIAL_REFRESH` 跳过这次远端刷新，直接使用已有本地数据。

缓存是否需要刷新由数据域的过期规则决定，不应复制文档示例中的固定时长。刷新失败时保留本地列表，通过 `LoadState` 或业务状态给出重试入口。`LoadState` 用 `Loading`、`Error` 和 `NotLoading` 表示一次分页加载正在进行、已经失败或当前没有加载。

分页键必须包含查询条件、账号和排序方式。只用一个全局 `nextKey`，会让不同搜索词或账号共享分页位置。服务端改变排序或游标格式时，还要清理相应分页键并启动完整刷新。

### 乐观更新需要持久状态机

状态机为每项操作规定允许的状态及转换，例如“待同步 → 已确认”或“待同步 → 冲突”。把当前状态持久化后，应用进程重建仍能恢复同一语义。乐观更新适合收藏、已读、草稿和其他可回滚或可解释失败的动作。界面状态应区分：

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

这里的“可观测性”指能通过指标和日志回答队列积压多久、同步卡在哪一类状态，以及用户当前看到的数据有多旧。接口成功率无法单独说明离线体验，应分层记录：

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

- 读取：界面与业务逻辑只从本地权威数据源观察数据，刷新状态与数据状态分开表达。
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
- [AndroidX · Room release notes](https://developer.android.com/jetpack/androidx/releases/room)
- [AndroidX · WorkManager release notes](https://developer.android.com/jetpack/androidx/releases/work)
- [AndroidX · Paging release notes](https://developer.android.com/jetpack/androidx/releases/paging)
- [RFC 9110 · HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
