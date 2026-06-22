---
title: "数据库性能优化（SQLite/Room）"
chapter: "24.2"
section: "24.2"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-14"
last_verified_against: "AOSP master snapshot 2026-05-14 + Android Developers docs + AndroidX Room source"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteDatabase.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteConnectionPool.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteGlobal.java"
  - type: aosp
    path: "frameworks/base/core/res/res/values/config.xml"
  - type: official
    path: "https://developer.android.com/topic/performance/sqlite-performance-best-practices"
  - type: official
    path: "https://developer.android.com/training/data-storage/room"
  - type: official
    path: "https://developer.android.com/training/data-storage/room/migrating-db-versions"
  - type: official
    path: "https://source.android.com/docs/core/perf/compatibility-wal"
  - type: official
    path: "https://sqlite.org/wal.html"
  - type: official
    path: "https://sqlite.org/eqp.html"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
tags: [sqlite, room, wal, database-index, query-optimization]
related_chapters: ["24.1", "10.7", "6.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-14
last_task9_at: 2026-05-14T07:24:00+08:00
last_task9_audit: "2026-06-08"
task9_review_notes: "2026-05-14 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；源码锚点需 pin 到稳定 tag，16KB page size 与 SQLite page_size/checkpoint 数据量关系需补 PRAGMA 验证。"
task2b_state: fixed
last_task2a_at: "2026-05-14T07:12:00+08:00"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_reviewed_date: "2026-05-14"
last_task6_at: "2026-05-14T08:11:00+08:00"
last_task6_audit: "2026-06-06"
last_task6_review_log: logs/review/2026-05-14-08-review.md
task6_review_notes: "2026-05-14 Task6：四层质检通过；L1/L2 无需正文改动。满足 task6_result=pass-light-edit、task9_result=pass-tech-review、queue 无 pending，自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-11
---

# 数据库性能优化（SQLite/Room）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SQLite WAL 模式与并发优化
- 🔹 Room 的正确使用与性能陷阱
- 🔹 索引设计与查询优化
- 🔹 数据库迁移与版本管理

### 扩展（可选深入）

- 🔸 SQLite vs Realm vs ObjectBox 选型

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解数据库性能优化（SQLite/Room）

数据库慢通常不会表现成 CPU 打满。更常见的现象是主线程等一次查询、多个后台线程排队拿连接、Migration 卡住首次 open，或者列表滚动时 CursorWindow 反复 refill。Perfetto 里线程可能停在 `SQLiteConnectionPool.waitForConnection()`、`SQLiteSession.executeForCursorWindow()`、DAO 生成代码或 `ContentResolver.query()` 的 Binder 等待上。

机制篇 10.7 已经讲过 SQLite 并发模型、CursorWindow、Room 线程模型和 ANR 分析路径。24.2 只处理应用侧动作：怎样配置 WAL，怎样写 Room DAO，怎样设计索引和查询，怎样把迁移风险挡在发版前。底层锁模型、CursorWindow 跨进程细节和 Perfetto SQL 分析详见 10.7 节；文件 I/O、StrictMode 与 SP/DataStore 的关系详见 24.1 节。


## SQLite WAL 模式与并发优化

WAL (Write-Ahead Logging) 将写操作追加到 `-wal` 文件，checkpoint 再把变更合并回主库。它给应用带来的收益是读写并发更好、提交路径通常更短、频繁小写入更容易被合并成追加写。Android 官方 SQLite 性能文档也将 WAL 列为基础配置项，并建议启用 WAL 时将 `synchronous` 设为 `NORMAL`。

Android 9 引入了 Compatibility WAL：在保持每个数据库最多一个连接的前提下使用 `journal_mode=WAL`；普通 `SQLiteDatabase` 默认可受这个兼容模式影响。Room 使用 `JournalMode.AUTOMATIC` 时，在 API 16+ 且非低内存设备上会启用完整 WAL。

WAL 不会把写操作变成并行写。SQLite 仍然只允许一个写者活跃；读者能和写者并发，多个写事务仍要排队。Android `SQLiteDatabase` 通过每线程 `SQLiteSession` 向 `SQLiteConnectionPool` 申请连接，连接池里让线程等待的位置是 `waitForConnection()`。看到连接池等待时，要回头查长事务、慢 Migration、写连接被占用，或者连接池规模与访问模型不匹配。

Android 默认 WAL 参数也会影响尾延迟。AOSP `SQLiteGlobal.getWALSyncMode()` 读取 `db_wal_sync_mode`，`config.xml` 当前默认是 `NORMAL`；`getWALAutoCheckpoint()` 读取 `db_wal_autocheckpoint`，当前默认是 100 页。配置注释说明，WAL 文件越大，checkpoint 可能越慢，所以平台把默认阈值设得较小。

这段代码用于表达应用侧的 Room 打开配置。重点看三处：保留 `JournalMode.AUTOMATIC`，给查询和事务配置有界线程池，把 Migration 明确注册到 builder。

```kotlin
private val dbQueryExecutor = Executors.newFixedThreadPool(4) { runnable ->
 Thread(runnable, "db-query").apply {
 priority = Thread.NORM_PRIORITY - 1
 }
}

private val dbTransactionExecutor = Executors.newSingleThreadExecutor { runnable ->
 Thread(runnable, "db-transaction").apply {
 priority = Thread.NORM_PRIORITY - 1
 }
}

val database = Room.databaseBuilder(context, AppDatabase::class.java, "app.db")
 .setJournalMode(RoomDatabase.JournalMode.AUTOMATIC)
 .setQueryExecutor(dbQueryExecutor)
 .setTransactionExecutor(dbTransactionExecutor)
 .addMigrations(MIGRATION_7_8, MIGRATION_8_9)
 .build()
```

查询线程池可以并发处理读请求，事务线程池建议从单线程开始。单写者模型下，给写事务开很多线程不会增加写吞吐，反而会把等待和锁竞争变复杂。批量导入、索引重建、清理任务这类重写路径要排进低优先级队列，避开启动、页面切换和用户输入路径。

WAL 的应用侧检查项：

- 确认是否使用 Room 默认 `AUTOMATIC`，不要为了“兼容”随手切回 `TRUNCATE` 或 `DELETE`。
- 如果使用 `ATTACH DATABASE`，重新评估 WAL；Android 官方 SQLite 性能文档把 `ATTACH DATABASE` 列为启用 WAL 的例外条件。
- 大事务后观察 `-wal` 文件增长和 checkpoint 耗时。在 16KB page size 的设备上，默认 100 页 checkpoint 阈值的实际数据量是 4KB page size 设备的 4 倍。
- 不在主线程首次 open 数据库。首次 open 可能触发 schema 校验、Migration、预置库复制或 checkpoint。

## Room 的正确使用与性能陷阱

Room 的收益是编译期 SQL 校验、DAO 抽象、迁移路径和协程/Flow 适配，不是自动把所有数据库访问变快。官方 Room 文档也把 Room 描述为 SQLite 之上的抽象层，底层仍然要遵守 SQLite 的连接、事务和查询代价。

Room 性能问题多出在四类调用点：同步 DAO 被 UI 路径调用、首次 open 发生在启动主线程、事务范围过大、Flow/LiveData 失效后重查过重。`allowMainThreadQueries()` 只能关掉保护，不能降低查询耗时。它可以出现在测试代码里，不该进入正式包。

DAO 方法按执行模型分开设计：

| DAO 形态 | 执行位置 | 使用场景 | 风险 |
| --- | --- | --- | --- |
| 普通同步方法 | 调用线程 | 测试、极少量工具代码 | UI 线程调用会被 Room 拦截；关闭拦截后会卡 UI |
| `suspend` 方法 | Room / 协程适配层调度 | 单次读写、批量写入 | 事务范围过大会占用写连接 |
| `Flow` | 观察表失效后重查 | UI 订阅数据变化 | 查询列过宽、重查太频繁会拖慢渲染 |
| PagingSource | 分页列表 | 大列表、离线缓存 | Offset 深翻页仍然变慢，Keyset 要自己写 SQL |

这段 DAO 代码用于区分“列表展示查询”和“详情查询”。重点看 projection：列表只取渲染所需列，详情页再按主键读取大字段。

```kotlin
data class MessageRow(
 val id: Long,
 val conversationId: Long,
 val senderName: String,
 val preview: String,
 val sentAt: Long
)

@Dao
interface MessageDao {
 @Query(
 """
 SELECT id, conversation_id AS conversationId, sender_name AS senderName,
 preview, sent_at AS sentAt
 FROM messages
 WHERE conversation_id = :conversationId
 ORDER BY sent_at DESC
 LIMIT :limit
 """
 )
 suspend fun latestRows(conversationId: Long, limit: Int): List<MessageRow>

 @Query("SELECT * FROM messages WHERE id = :id")
 suspend fun detail(id: Long): MessageEntity?
}
```

列表查询不要返回 `SELECT *`。大文本、JSON、BLOB 和冗余字段会挤占 CursorWindow，也会增加反序列化成本。Android 官方 SQLite 性能文档给出的第一条原则就是少读行、少读列，并把过滤、排序、聚合交给 SQLite 引擎完成。

事务使用要按业务边界收敛。批量插入、删除、状态切换适合放进一个事务；网络回调、文件读取、复杂计算不该包在事务内。事务体里做慢 I/O，会占着写连接等待磁盘或网络，其他查询和写入都会被拖慢。

这段代码用于表达批量写入的事务边界。重点看事务内只保留数据库写入，数据解析和网络请求在进入事务前完成。

```kotlin
class MessageRepository(
 private val database: AppDatabase,
 private val dao: MessageDao
) {
 suspend fun replaceConversationMessages(
 conversationId: Long,
 rows: List<MessageEntity>
 ) {
 database.withTransaction {
 dao.deleteByConversation(conversationId)
 dao.insertAll(rows)
 }
 }
}
```

事务把多次写入合并成一次提交，能减少锁获取、WAL 写入和事务状态切换。它也会拉长单次写连接占用时间，所以事务内代码越短越好。

Room 线上排查还要加可观测入口：

- 打开 Room `QueryCallback` 做灰度采样，记录 SQL 模板、耗时、线程名和业务场景；参数里可能包含用户数据，默认不要上报原始参数。
- 记录首次 open 和 Migration 耗时，把它们和冷启动、首屏、ContentProvider 初始化分开统计。
- 对高频 Flow 查询统计重查次数。某张表每秒多次更新时，观察者可能被重复触发。
- 记录连接池等待栈。Perfetto 里看到 `waitForConnection()` 时，要能反查当前持有写连接的任务。

## 索引设计与查询优化

索引设计从查询形状出发，不从字段名出发。一个字段看起来像 ID，不代表它该单独建索引；一个查询同时按 `conversation_id` 过滤、按 `sent_at` 排序，单列索引可能仍然要回表或额外排序。SQLite 官方 `EXPLAIN QUERY PLAN` 文档说明，`EXPLAIN QUERY PLAN` 可以展示查询使用的扫描策略，包含 `SCAN`、`SEARCH`、`USING INDEX`、`USING COVERING INDEX` 等信息。

这段 Room 实体代码用于表达复合索引的设计方式。重点看索引列顺序要和查询里的过滤、排序顺序匹配。

```kotlin
@Entity(
 tableName = "messages",
 indices = [
 Index(
 value = ["conversation_id", "sent_at"],
 name = "idx_messages_conversation_sent_at"
 ),
 Index(
 value = ["server_id"],
 unique = true,
 name = "idx_messages_server_id_unique"
 )
 ]
)
data class MessageEntity(
 @PrimaryKey(autoGenerate = true) val id: Long = 0,
 @ColumnInfo(name = "conversation_id") val conversationId: Long,
 @ColumnInfo(name = "server_id") val serverId: String,
 @ColumnInfo(name = "sender_name") val senderName: String,
 val preview: String,
 @ColumnInfo(name = "sent_at") val sentAt: Long,
 val body: String
)
```

`conversation_id, sent_at` 适合支撑“某个会话内按时间倒序取消息”的查询。`server_id` 用唯一索引表达去重约束，让 SQLite 在写入时直接校验唯一性。Android 官方 SQLite 性能文档也建议使用索引加速查询、使用唯一约束让数据库处理数据约束，并提醒不要维护未使用索引，因为写入时也要更新索引表。

索引和查询优化按这张清单检查：

| 检查项 | 做法 | 目标 |
| --- | --- | --- |
| 只读必要列 | 列表页使用 DTO projection，详情页再读全文 | 降低 CursorWindow 与对象构造成本 |
| 只读必要行 | 加 `LIMIT`，分页查询不要一次取全量 | 控制单次查询时间和内存占用 |
| 把计算交给 SQL | 过滤、排序、计数、去重用 SQL 表达 | 避免把大量行搬到 Kotlin/Java 后再处理 |
| 复合索引匹配查询形状 | 过滤列在前，排序列跟在后面 | 减少全表扫描和临时排序 |
| 批量写入进事务 | 多条 insert/update/delete 合并提交 | 减少事务切换和写锁竞争 |
| 清理无效索引 | 用线上 SQL 采样和 `EXPLAIN QUERY PLAN` 反查 | 降低写入维护成本 |

这段命令用于在本地验证查询计划。重点看输出里是否出现 `SEARCH messages USING INDEX idx_messages_conversation_sent_at`，如果还是 `SCAN messages`，说明索引没有按预期命中。

```sql
EXPLAIN QUERY PLAN
SELECT id, conversation_id, sender_name, preview, sent_at
FROM messages
WHERE conversation_id = 42
ORDER BY sent_at DESC
LIMIT 50;
```

`EXPLAIN QUERY PLAN` 的结果要和真实数据量一起看。空库、小样本库、测试库都可能给出看似正常的查询计划。索引上线前要在接近线上分布的数据集上验证：单会话消息数、长文本比例、删除比例、冷热数据分布都会影响收益。

查询优化可以进 CI。做法是给关键 DAO 准备一组固定数据，跑 `EXPLAIN QUERY PLAN` 并断言不得出现未预期的全表扫描。CI 不替代线上监控，但能防止一次 schema 改动把列表查询从索引查找改成全表扫描。

## 数据库迁移与版本管理

Migration 的性能风险和稳定性风险绑在一起。Room 打开数据库时会校验 schema，并按版本执行自动或手写 Migration。官方迁移文档说明，自动迁移适合基础 schema 改动；复杂改动，例如拆表、合并表、数据搬迁，需要手写 `Migration`。Room 还建议导出 schema JSON 并提交到版本库，用于自动迁移和迁移测试。

迁移设计分三层：

- schema 改动：新增表、列、索引、视图，尽量使用可回放、可验证的 SQL。
- 数据回填：大表回填要分批，避免在首次 open 里一次处理全量历史数据。
- 发布策略：缓存库可以接受破坏性迁移，用户资产库不能使用默认清库兜底。

这段 Migration 代码用于展示“只做 schema 改动 + 小规模补值”的写法。重点看 SQL 明确、版本范围明确，不依赖线上当前数据的隐含状态。

```kotlin
val MIGRATION_8_9 = object : Migration(8, 9) {
 override fun migrate(db: SupportSQLiteDatabase) {
 db.execSQL("ALTER TABLE messages ADD COLUMN sync_state INTEGER NOT NULL DEFAULT 0")
 db.execSQL(
 """
 CREATE INDEX IF NOT EXISTS idx_messages_sync_state_sent_at
 ON messages(sync_state, sent_at)
 """.trimIndent()
 )
 }
}
```

新增列带默认值、创建索引和重建表都可能产生 I/O。表越大，首次打开数据库时的等待越长。启动路径如果同步触发 Room open，这段等待会直接算进冷启动或首屏耗时。更稳的处理方式是把首次 open 放到可控后台时机，并在 UI 真要读库前暴露“数据库已准备好”的状态。

这段测试代码用于验证迁移路径。重点看 `runMigrationsAndValidate()`，它会跑指定 Migration 并校验最终 schema。

```kotlin
@RunWith(AndroidJUnit4::class)
class AppDatabaseMigrationTest {
 @get:Rule
 val helper = MigrationTestHelper(
 InstrumentationRegistry.getInstrumentation(),
 AppDatabase::class.java
 )

 @Test
 fun migrate8To9() {
 helper.createDatabase("migration-test", 8).apply {
 execSQL(
 """
 INSERT INTO messages(id, conversation_id, server_id, sender_name, preview, sent_at, body)
 VALUES(1, 42, 's-1', 'alice', 'hello', 1000, 'hello body')
 """.trimIndent()
 )
 close()
 }

 helper.runMigrationsAndValidate(
 "migration-test",
 9,
 true,
 MIGRATION_8_9
 )
 }
}
```

迁移测试不能只测相邻版本。线上用户可能从 6 升到 9，也可能从 7 升到 9。Room 官方文档建议加入覆盖所有已定义迁移路径的测试；这类测试应进入 release CI，不要等灰度后靠崩溃发现缺迁移。

`fallbackToDestructiveMigration()` 只适合可丢数据的缓存库。它会在缺少迁移路径时破坏性重建表。用户草稿、离线内容、支付状态、消息记录这类数据不该依赖这个兜底。对缓存库使用破坏性迁移，也要记录命中次数和库大小，避免一次版本遗漏让大量用户重新拉取数据。

迁移发版前的门禁：

- `exportSchema = true`，schema JSON 提交到版本库。
- 所有历史版本到当前版本的迁移路径可测试。
- 大表回填有批处理策略，首次 open 不做全量重算。
- Migration 耗时进入启动监控，按版本、设备、库大小分桶。
- 破坏性迁移只出现在缓存库，并有埋点记录。

## 扩展：SQLite vs Realm vs ObjectBox 选型

SQLite/Room 仍然是 Android 本地结构化数据的默认选项。它的优势是平台稳定、生态成熟、SQL 表达能力强、可用系统工具和 Perfetto/trace 路径排查；代价是 schema 设计、索引、迁移和 SQL 性能都要工程团队自己负责。

Realm 和 ObjectBox 更偏对象数据库。它们能降低一部分对象持久化和观察更新的样板代码，但会引入新的文件格式、查询模型、同步语义、包体积和长期维护成本。本项目当前没有针对 Realm/ObjectBox 的近期实测数据，所以这里只给选型维度，不给性能结论。

| 维度 | SQLite/Room | Realm | ObjectBox |
| --- | --- | --- | --- |
| 查询表达 | SQL，适合复杂过滤、聚合、排序 | 对象查询 API | 对象查询 API |
| 迁移控制 | Room schema + Migration，控制细 | 依赖库自身迁移模型 | 依赖库自身迁移模型 |
| 排查工具 | SQLite shell、DB Browser、Perfetto、ANR trace | 依赖库工具和日志 | 依赖库工具和日志 |
| 团队成本 | Android 工程师普遍熟悉 | 要学习库语义 | 要学习库语义 |
| 适合场景 | 离线缓存、消息、配置、关系型数据 | 对象图、实时观察模型 | 对象图、嵌入式 KV/对象存储 |

选型结论要落到数据形状：关系清楚、查询复杂、需要长期维护，优先 Room；对象图强、查询简单、团队愿意承担第三方库升级和排查成本，再评估 Realm 或 ObjectBox。涉及金融、订单、消息这类资产数据时，迁移可控性和可排查性优先于 API 简洁。

## 小结

数据库优化的应用侧路径很明确：WAL 给读写并发提供基础，但写事务仍然串行；Room 要用异步 DAO、有界执行器和可测试 Migration；索引从查询形状出发，并用 `EXPLAIN QUERY PLAN` 验证；迁移要在 CI 和灰度监控里提前暴露风险。机制细节已经放在 10.7，24.2 的价值是把这些约束变成代码、门禁和线上指标。
