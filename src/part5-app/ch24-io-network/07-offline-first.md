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
last_task9_audit: "2026-06-20"
last_task9_audit_log: "logs/deep-review/2026-06-20-20-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-14
---

# 离线优先架构

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 离线优先的设计原则
- 🔹 Room + WorkManager 的离线架构
- 🔹 冲突解决策略
- 🔹 渐进式加载与乐观更新

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解离线优先架构

离线优先处理数据层约束：读取路径必须有不依赖网络的数据源，写路径必须能在网络不可用时保住用户操作，并在恢复连接后完成同步。Android 官方架构文档把离线优先放在数据层讨论。UI 不需要关心数据来自网络、数据库还是同步队列，它只消费 Repository 暴露出来的状态。[已验证: 官方文档, developer.android.com/topic/architecture/data-layer/offline-first]

24.6 已经讲过 HTTP 缓存、磁盘缓存和业务缓存的边界。24.7 往前走一步：把缓存从“加速读取”升级成“支撑产品流程”。如果用户在地铁、电梯、海外漫游、弱网切换时仍要浏览、收藏、提交、撤销，缓存层就不能只保存接口响应快照，还要保存操作日志、同步状态、冲突元数据和错误恢复入口。
离线优先的性能收益来自减少等待。页面先读本地，网络同步转成后台任务；用户操作先落本地，远端提交转成可重试队列。代价也会增加：本地数据可能过期，同一对象可能被多端修改，后台任务会受电量、网络、系统调度限制。设计时要先挑出“必须离线可用”的业务对象，别把所有接口都塞进同一套同步框架。

## 离线优先的设计原则

离线优先的读取入口是本地数据源。Repository 向上层暴露 `Flow`、`StateFlow` 或 Paging 数据流，UI 从 Room、DataStore 或文件索引拿数据；网络请求只负责刷新本地数据源。Android 官方文档明确建议：离线优先场景下，Repository 至少要有一个不依赖网络的数据源，本地数据源应作为 App 的权威事实源。[已验证: 官方文档, developer.android.com/topic/architecture/data-layer/offline-first]

工程上可以按三类数据拆开处理：

| 数据类型 | 本地载体 | 同步策略 | 用户感知 |
|----------|----------|----------|----------|
| 只读列表 | Room 表 + 分页游标 | 前台按需拉取，后台定期刷新 | 允许展示旧数据，但要显示刷新状态 |
| 用户配置 | Room / DataStore | 本地先写，恢复网络后上传 | 需要保证操作不丢失 |
| 交易类操作 | Room outbox 表 | 必须服务端确认后才完成 | 失败要给明确恢复入口 |

离线优先还要把读写模型分开。读模型面向 UI 展示，强调快速、可观察、可分页；写模型面向同步，强调幂等、顺序、重试和冲突处理。不要让“提交按钮”直接调用网络层再更新 UI，也不要让 UI 直接拼同步状态。Repository 负责把本地表、网络模型、同步队列映射成稳定的业务模型。[已验证: 官方文档, developer.android.com/topic/architecture/data-layer]

离线优先架构的收益要靠指标来验证。参考 24.6 的缓存命中率思路，离线优先也要记录本地命中率、冷启动首屏可读比例、同步成功率、冲突率、队列堆积时长、失败重试次数。只看接口成功率会漏掉同步问题：用户已经看到本地数据，但同步队列可能连续失败；或者本地列表能打开，但数据已经长时间没有刷新。
## Room + WorkManager 的离线架构

Room 适合作为离线优先的结构化本地数据源。官方 Room 文档说明，Room 基于 SQLite 提供抽象层，适合保存非平凡结构化数据；当设备无法访问网络时，用户仍能浏览本地缓存内容。24.2 已经讲过 WAL、索引、DAO 和 Migration，这里只引用结论：离线优先的数据表要按查询路径和同步路径共同设计，别只照接口 JSON 建表。[已验证: 官方文档, developer.android.com/training/data-storage/room；详见 24.2 节]

一个可维护的最小架构通常包含四组表：

- entity 表：保存 UI 可直接读取的业务对象，例如 `note`、`article`、`message`。
- remote key 表：保存分页游标、服务端版本号、增量同步 token，避免列表刷新时丢失下一页位置。
- outbox 表：保存待上传操作，字段至少包含本地操作 ID、对象 ID、操作类型、payload、幂等 key、重试次数、创建时间、状态。
- 同步状态表：保存每类数据的最近同步时间、失败原因、下一次重试窗口和服务端水位。

这段代码是 outbox 表的建模骨架，用来说明字段边界。重点看 `idempotencyKey`、`attemptCount` 和 `status`，它们决定任务能否安全重试。

```kotlin
@Entity(tableName = "sync_outbox")
data class SyncOutboxEntity(
    @PrimaryKey val localOpId: String,
    val objectId: String,
    val operation: String,
    val payloadJson: String,
    val idempotencyKey: String,
    val attemptCount: Int,
    val status: SyncStatus,
    val createdAtMillis: Long,
    val updatedAtMillis: Long,
)
```

`SyncStatus` 如果作为 Room 字段保存，需要用 `@TypeConverter` 转成 `Int/String` 等可持久化类型；示例省略转换器，只保留同步队列字段。`idempotencyKey` 要传给服务端或参与请求去重；没有服务端幂等支持时，客户端重试可能制造重复评论、重复订单或重复埋点。`attemptCount` 和 `status` 不只是调试字段，WorkManager 重启、进程被杀、设备重启后都要靠它们恢复状态。[已验证: 官方文档, developer.android.com/topic/architecture/data-layer/offline-first]

WorkManager 负责执行持久化同步任务。官方文档把 WorkManager 定位为 persistent work，支持约束条件、重试、backoff、周期任务和 expedited work；当约束在任务运行中失效时，Worker 会停止，满足约束后再重试。离线同步正好匹配这种模型：任务不要求立刻完成，但不能因为进程结束就丢失。[已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work；详见 25.4 节]

同步任务的接入方式建议分两层：

- 前台触发：用户完成写操作后，本地事务先更新 entity 表和 outbox 表，再 enqueue 一次 `OneTimeWorkRequest`。约束通常设为 `NetworkType.CONNECTED`，弱网下返回 `Result.retry()`。涉及删除、多账号或跨设备编辑时，outbox 还要记录 `accountId`、操作顺序或 tombstone 标记，避免删除后被旧同步恢复，或队列跨账号继续执行。
- 后台补偿：应用启动、登录态恢复、网络可用、周期窗口到达时，enqueue 唯一同步任务，批量处理 outbox 和过期数据。周期任务要设置合理的 flex window，避免频繁唤醒。

这段 Worker 代码用于说明离线队列入口。这里要关注事务边界：本地状态变更和 outbox 状态更新必须成对发生；生产接入时，Repository 依赖要通过 Hilt Worker、WorkerFactory 或 DelegatingWorker 注入。

```kotlin
class SyncOutboxWorker(
    appContext: Context,
    params: WorkerParameters,
    private val repository: OfflineRepository,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        return when (repository.drainOutbox(limit = 50)) {
            SyncResult.Drained -> Result.success()
            SyncResult.TemporaryFailure -> Result.retry()
            SyncResult.PermanentFailure -> Result.failure()
        }
    }
}
```

Worker 不应直接拼 SQL、直接调用 Retrofit、直接更新 UI 状态。实践中，让 Worker 调 Repository 的同步接口，Repository 再协调 DAO、网络数据源和冲突处理器。默认 WorkManager 不能直接实例化带 Repository 参数的构造函数，上面的写法需要配合依赖注入或自定义 WorkerFactory。这样单元测试可以绕开 WorkManager，直接验证 `drainOutbox()` 在成功、超时、401、409、服务端幂等命中时如何更新本地状态。

分页列表建议使用 Paging 3 的 `RemoteMediator`。官方文档说明，`RemoteMediator` 在本地分页数据耗尽或缓存失效时从网络加载新数据，并写入 Room；UI 仍从 Room 生成的 `PagingSource` 读取。这个模式适合 feed、消息列表、商品列表：列表读取不被网络阻塞，远端刷新通过数据库失效通知推给 UI。[已验证: 官方文档, developer.android.com/topic/libraries/architecture/paging/v3-network-db]

本地写入和远端同步的框架搭建好之后，下一个必须面对的问题是冲突。

## 冲突解决策略

冲突的根源很简单：本地可以先写，远端也可能被别的设备修改。Android 官方离线优先文档把 conflict resolution 放在同步之后讨论，并给出 versioning 和 last write wins 作为常见方向。工程里不能只写“服务端为准”四个字，要把冲突类型、检测字段、自动合并条件和人工处理入口写进协议。[已验证: 官方文档, developer.android.com/topic/architecture/data-layer/offline-first]

常见策略可以按风险分层：

| 策略 | 适用场景 | 必要元数据 | 风险 |
|------|----------|------------|------|
| 服务端覆盖本地 | 公告、配置、推荐内容 | 服务端版本号、更新时间 | 用户本地编辑会丢失 |
| 本地覆盖服务端 | 单端草稿、弱协作数据 | 本地更新时间、设备 ID | 多端编辑容易互相覆盖 |
| Last write wins | 低价值字段，如昵称、主题色 | 毫秒级时间戳、服务端接收时间 | 客户端时钟漂移会误判顺序 |
| 字段级 merge | 可拆字段的资料页、设置页 | 字段版本、修改来源 | 协议和测试成本高 |
| 人工处理 | 文档、订单、库存、审批 | 冲突副本、差异摘要、回滚入口 | 产品流程成本高 |

冲突检测不要只依赖 `updatedAt`。更可靠的做法是在对象上保存服务端版本 `serverVersion` 或 ETag，客户端提交时带上“基于哪个版本修改”。服务端发现版本不匹配时返回冲突，客户端再决定自动合并、保留本地副本或让用户选择。交易类数据还要加幂等 key，把“同一操作重试”与“用户再次提交”区分开。

本地事务要保证 UI 状态和同步状态一致。用户点击收藏时，可以立刻把 `bookmarked=true` 写入 entity 表，同时写入 outbox；如果远端返回永久失败，再把 entity 表回滚或标记为 `syncFailed`。不要只在内存里记一个 pending 状态，进程被杀后 UI 会显示成功，队列里却没有任务。

冲突处理还有一个性能边界：同步批量越大，单次事务越重，数据库锁持有时间越长；批量越小，网络和唤醒开销越高。初始窗口不要写死，可以从较小批量开始压测，再按 payload 大小、失败率、服务端限流和低端机数据库耗时调整；20-100 条只能作为没有业务基线时的试验范围。Perfetto 里如果看到同步任务长时间占用数据库连接，回到 24.2 检查事务范围、索引和 WAL checkpoint。

## 渐进式加载与乐观更新

渐进式加载的目标是让屏幕先有可解释的内容。第一次进入页面时，UI 先展示 Room 中的缓存、上次同步时间和刷新状态；Repository 同时发起刷新。刷新成功后写回本地，Room 的 invalidation 让 UI 自动更新；刷新失败时保留旧数据，显示可重试状态。这条路径适合弱网，也更容易定位问题：读本地、拉网络、写数据库、通知 UI 每一步都能单独打点。[已验证: 官方文档, developer.android.com/topic/architecture/data-layer/offline-first]

Paging 3 的 `RemoteMediator` 适合列表渐进式加载。它把“UI 从本地读”和“网络补数据”拆开：`PagingSource` 从 Room 读，`RemoteMediator.load()` 拉网络并写库，remote key 表记录下一页位置。刷新时要处理缓存过期和竞态条件（race condition）；官方文档说明，`initialize()` 可以决定跳过本次远端刷新或触发完整刷新，Room 会在数据插入后让旧 `PagingSource` 失效。[已验证: 官方文档, developer.android.com/topic/libraries/architecture/paging/v3-network-db]

乐观更新适合低风险、可回滚的动作，例如收藏、点赞、草稿保存、已读状态。流程是：本地先写成功态和 pending 标记，UI 立即反馈；Repository 写 outbox；WorkManager 上传；远端确认后清除 pending；远端拒绝后改成 failed 并给用户恢复入口。支付、下单、权限变更、库存扣减不适合直接乐观完成，只能展示“已提交，等待确认”。

这段代码也是事务边界骨架。重点看 `withTransaction` 内部：entity 更新和 outbox 插入在同一个事务里。

```kotlin
suspend fun bookmarkArticle(articleId: String, bookmarked: Boolean) {
    database.withTransaction {
        articleDao.setBookmarkPending(
            articleId = articleId,
            bookmarked = bookmarked,
            pendingSync = true,
        )
        outboxDao.insert(
            SyncOutboxEntity(
                localOpId = UUID.randomUUID().toString(),
                objectId = articleId,
                operation = "bookmark",
                payloadJson = json.encodeToString(BookmarkPayload(bookmarked)),
                idempotencyKey = "bookmark:$articleId:$bookmarked",
                attemptCount = 0,
                status = SyncStatus.Pending,
                createdAtMillis = clock.nowMillis(),
                updatedAtMillis = clock.nowMillis(),
            )
        )
    }
    syncScheduler.enqueueOutboxSync()
}
```

这段代码不能直接复制到业务里使用：`idempotencyKey` 的生成规则必须和服务端约定，`clock` 要考虑测试替身，`SyncStatus` 要覆盖永久失败和冲突状态。它只说明一个边界：用户可见状态和待同步操作必须一起落盘。

上线前至少做五组验证：飞行模式下新增和编辑、网络恢复后自动同步、服务端返回 409 冲突、进程被杀后继续同步、设备时间错误时冲突策略是否仍可解释。再加一组低电量和省电模式验证，确认 WorkManager 约束没有把同步任务无限期延后。

## 小结

离线优先落在数据层：Room 提供可观察、可持久的本地事实源，WorkManager 处理可重试的持久同步，Repository 负责把网络、本地和冲突策略收敛成稳定 API。缓存命中率、队列堆积、同步成功率和冲突率要一起看；只看接口耗时，容易漏掉用户已经离线操作但远端迟迟没有收敛的问题。
