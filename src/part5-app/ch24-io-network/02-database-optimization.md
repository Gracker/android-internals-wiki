---
title: "数据库性能优化（SQLite/Room）"
chapter: "24.2"
section: "24.2"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-30"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers SQLite/Room docs + AndroidX Room source"
last_verified_android17: "2026-06-30"
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
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-30
last_task9_at: 2026-06-30T14:25:47+08:00
last_task9_audit: "2026-06-30"
last_task9_autofix_at: "2026-06-30"
last_task9_audit_log: "logs/deep-review/2026-06-30-14-audit.md"
task9_review_notes: "2026-06-30 idle audit auto-fixed: AOSP SQLite/Room source baseline pinned to android-17.0.0_r1; WAL checkpoint sentence narrowed to actual SQLite DB page_size / PRAGMA page_size; Task6 revisiting required after localized technical edits."
task2b_state: fixed
task2b_result: auto-fixed
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
last_deepseek_cn_review_at: 2026-07-15
---

# 数据库性能优化（SQLite/Room）

## 为什么要了解数据库性能优化（SQLite/Room）

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。Room 属于独立发布的 AndroidX 组件，行为应以项目锁定的 Room 版本为准，不能只用 Android API 级别推断。涉及 WAL 同步和文件持久性时，沿用 [24.1 文件 I/O 优化](01-file-io-optimization.md)中的 `android17-6.18-2026-06_r6` 内核锚点。

数据库慢通常不会表现成 CPU 满载。更常见的现象是主线程等待查询、工作线程排队申请连接、Migration 占住首次打开，或者列表滚动时 `CursorWindow` 反复填充。Perfetto 和线程栈中常见 `SQLiteConnectionPool.waitForConnection()`、`SQLiteSession.executeForCursorWindow()`、DAO 生成代码，或 `ContentResolver.query()` 的 Binder 等待。

机制篇 [10.7 SQLite 与 Room 性能](../../part2-performance/ch10-memory-perf/07-sqlite-room-performance.md)介绍 SQLite 并发、`CursorWindow`、Room 执行模型和 ANR 归因。应用侧还要决定怎样选择 WAL，怎样写 DAO，怎样按查询设计索引，以及怎样在发版前验证迁移。

## SQLite WAL 模式与并发优化

WAL（Write-Ahead Logging）把事务变更追加到 `-wal` 文件，checkpoint 再把页面合并回主库。它允许读事务与写事务并发，提交也常能受益于追加写。WAL 仍只有一个活跃写者，多个写事务会依次等待。

Android 官方性能文档建议：除使用 `ATTACH DATABASE` 的场景外启用 WAL，并在 WAL 下使用 `synchronous=NORMAL`。这个选择改变持久性边界：应用进程崩溃后事务仍可恢复，但设备断电或内核崩溃可能回滚已经返回成功的事务。订单、支付或跨库依赖不能只按吞吐量选择同步级别。

### Android 9 的 Compatibility WAL 到 Android 17 的变化

Android 9 引入 Compatibility WAL 时，[官方历史文档](https://source.android.com/docs/core/perf/compatibility-wal)描述的是“WAL 日志模式 + 每库最多一个连接”。Android 17 源码不能继续套用这个连接数结论：

- `SQLiteCompatibilityWalFlags` 从 `Settings.Global.SQLITE_COMPATIBILITY_WAL_FLAGS` 读取 `legacy_compatibility_wal_enabled`；
- 只有应用没有显式指定 journal/sync mode 时，legacy compatibility flag 才生效；
- `SQLiteDatabaseConfiguration.resolveJournalMode()` 会把它解析成 WAL；
- `SQLiteConnectionPool` 看到解析结果为 WAL 后，使用 `SQLiteGlobal.getWALConnectionPoolSize()`，而 `android-17.0.0_r1` 的资源默认值是 4，厂商和调试属性仍可覆盖。

所以，“Compatibility WAL 永远单连接”只应放在 Android 9 的版本历史里。调查 Android 17 设备时，应读取当前连接池 dump 和生效配置，不按旧文档猜连接数。该全局兼容开关默认也不是应用可以依赖的 SDK 契约，应用应通过自己使用的数据库 API 明确选择日志模式。

[源码锚点：[`SQLiteCompatibilityWalFlags.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteCompatibilityWalFlags.java)、[`SQLiteDatabaseConfiguration.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabaseConfiguration.java)、[`SQLiteConnectionPool.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnectionPool.java)]

### Android 17 的 WAL 默认参数

在 `android-17.0.0_r1` 中：

| 参数 | AOSP 默认值 | 含义 |
| --- | ---: | --- |
| `db_wal_sync_mode` | `NORMAL` | WAL 连接默认同步模式 |
| `db_wal_autocheckpoint` | 100 | 自动 checkpoint 阈值，单位是数据库页 |
| `db_connection_pool_size` | 4 | framework WAL 连接池资源默认值 |

这些是 AOSP 资源默认值，不是所有设备和所有 Room 驱动的固定值。系统属性、资源覆盖、应用显式配置和 AndroidX 驱动都可能改变结果。100 页也不能直接按 4 KiB 内存页换算；应查询该数据库的 `PRAGMA page_size`。

[源码锚点：[`SQLiteGlobal.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteGlobal.java)、[`config.xml`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml)]

### Room 怎样选择 journal mode

`JournalMode.AUTOMATIC` 的当前 API 契约是：API 低于 16 或低内存设备选择 `TRUNCATE`，其余情况选择 `WRITE_AHEAD_LOGGING`。这是 AndroidX Room 的契约，不是 Android 17 平台保证；升级 Room 时仍要复核依赖版本的 API 文档和 release notes。

下面的配置用于展示一个可审计的 Room 打开入口。日志模式和 Migration 都在同一个 builder 中明确声明；执行器先保留 Room 默认值，只有追踪结果证明默认调度不符合业务需求时才自定义。

```kotlin
val database = Room.databaseBuilder(
    context.applicationContext,
    AppDatabase::class.java,
    "app.db"
)
    .setJournalMode(RoomDatabase.JournalMode.AUTOMATIC)
    .addMigrations(MIGRATION_7_8, MIGRATION_8_9)
    .build()
```

这段代码不会保证一定启用 WAL，低内存设备可能得到 `TRUNCATE`。若自定义执行器，Room 文档要求查询执行器有线程上限且不能运行在主线程；事务最多同时执行一个。共享事务执行器还要遵守文档中的死锁约束，不应复制一套固定线程数到所有应用。

使用 Room 3 / `SQLiteDriver` 的项目不能照搬 framework `SQLiteConnectionPool` 的连接数和 `CursorWindow` 结论。驱动会改变 Room 下方的 SQLite 实现与数据传递路径，具体边界见 [24.17 Room 3、SQLiteDriver 与 KMP 性能](17-room3-sqlitedriver-kmp-performance.md)。

WAL 的应用侧检查项：

- 在目标设备读取生效的 journal/sync mode，不把 builder 选项当作运行结果。
- 如果使用 `ATTACH DATABASE`，重新评估 WAL；官方文档把 `ATTACH DATABASE` 列为启用 WAL 的例外条件。
- 大事务后观察 `-wal` 文件增长、读事务持续时间和 checkpoint 耗时；长期读事务可能阻止 checkpoint 推进。
- 不在主线程首次打开数据库。首次打开可能触发模式校验、Migration、预置库复制或 checkpoint。
- 连接池等待先查长事务、慢查询和连接持有者，再考虑改变池大小。

[官方文档：[SQLite 性能建议](https://developer.android.com/topic/performance/sqlite-performance-best-practices)、[`RoomDatabase.JournalMode`](https://developer.android.com/reference/androidx/room/RoomDatabase.JournalMode)、[SQLite WAL](https://sqlite.org/wal.html)]

## Room 的正确使用与性能陷阱

Room 提供编译期 SQL 校验、DAO 生成、迁移管理和异步 API 适配，不会自动降低 SQL、连接等待和事务提交的成本。`allowMainThreadQueries()` 只是关闭主线程保护，不会降低查询耗时；它可以用于受控测试，不应进入发布数据库配置。

Room 性能问题常出现在四类位置：同步 DAO 被界面路径调用、首次打开落在启动主线程、事务范围过大，以及可观察查询在表失效后反复执行。

DAO 方法按执行模型分开设计：

| DAO 形态 | 执行位置 | 使用场景 | 风险 |
| --- | --- | --- | --- |
| 普通同步方法 | 调用线程 | 测试、极少量工具代码 | UI 线程调用会被 Room 拦截；关闭拦截后会卡 UI |
| `suspend` 方法 | Room 异步执行机制 | 单次读写、批量写入 | 事务范围过大会长期占用连接 |
| `Flow` | 观察表失效后重新查询 | UI 订阅数据变化 | 表中任意行变化都可能触发重查 |
| `PagingSource` | 分页列表 | 大列表、离线缓存 | 深 offset 仍可能扫描许多行，游标分页需按查询设计 |

下面的 DAO 用来区分列表投影和详情实体。列表只选择渲染所需列，正文等大字段留到详情查询；调用方还要限制 `limit` 的合法范围。

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

在 framework SQLite 驱动下，少读列能降低 `CursorWindow` 填充、跨 JNI 复制和对象构造成本；使用其他 AndroidX SQLite 驱动时，具体承载结构可能不同，但“少读行、少读列”仍成立。过滤、排序和聚合也应尽量在 SQL 中完成。

可观察查询按“引用到的表”失效，不按结果集中的具体行判断。表中任意相关写入都可能让查询重跑；`distinctUntilChanged()` 可以减少相同结果向下游发射，不能省掉已经发生的 SQL 查询。高频更新表应拆小观察范围或减少无关写入。

事务范围应以不可分割的数据变更为边界。批量插入、删除和状态切换适合放进一个事务；网络请求、文件读取和复杂计算应在事务外完成。Room 同时最多执行一个事务，事务内等待外部工作会让后续事务持续排队，也可能延迟需要连接的查询。

下面的代码用于展示批量替换的事务边界。传入的 `rows` 应在进入事务前完成网络读取、解码和业务校验。

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

事务保证删除与插入要么一起成功，要么一起回滚，并减少多次独立提交。代价是写连接在整个事务期间被占用，因此批次大小要用真实数据量和尾延迟验证，不能无限扩大。

Room 线上排查还要加可观测入口：

- Room `QueryCallback` 会为每条查询增加回调成本，且回调本身只给出 SQL 与绑定参数，不直接提供执行耗时。若做短期受控采样，只记录归一化 SQL 标识和线程，不上传原始参数；耗时应在 DAO/仓库边界或 Perfetto 中另行测量。
- 记录首次打开和 Migration 耗时，把它们和冷启动、首屏、ContentProvider 初始化分开统计。
- 对高频 Flow 查询统计重查次数。某张表每秒多次更新时，观察者可能被重复触发。
- 记录连接池等待栈。Perfetto 里看到 `waitForConnection()` 时，要能反查当前持有写连接的任务。

Android 17 的 `dumpsys meminfo <package>` 在 `DATABASES` 和 `POOL STATS` 中提供 SQLite 页、连接与语句缓存统计。该版本里 `cache size` 表示已缓存预编译语句的数量；较早版本的同名列可能只是命中与未命中计数之和。跨版本看板必须按平台版本解释字段。

[官方文档：[异步 DAO 查询](https://developer.android.com/training/data-storage/room/async-queries)、[`RoomDatabase.Builder`](https://developer.android.com/reference/androidx/room/RoomDatabase.Builder)、[SQLite 性能排查工具](https://developer.android.com/topic/performance/sqlite-performance-best-practices)]

## 索引设计与查询优化

索引设计从查询形状和数据分布出发，不从字段名出发。查询同时按 `conversation_id` 等值过滤、按 `sent_at` 排序时，两个互不相关的单列索引通常不能同时完成过滤与排序。`EXPLAIN QUERY PLAN` 可显示 `SCAN`、`SEARCH`、`USING INDEX` 和 `USING COVERING INDEX` 等策略，但输出格式不属于稳定的应用接口。

下面的 Room 实体用于展示与前述查询配套的复合索引。等值过滤列放在索引前缀，随后是排序列；SQLite 可以反向扫描 B-tree，因此这个索引也可服务 `sent_at DESC`。

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

`conversation_id, sent_at` 适合“某个会话内按时间取消息”的查询。`server_id` 的唯一索引让数据库执行唯一性约束。每个索引都会占用空间并增加插入、更新和删除成本，因此要用查询记录确认它确有使用。

索引和查询优化按这张清单检查：

| 检查项 | 做法 | 目标 |
| --- | --- | --- |
| 只读必要列 | 列表页使用 DTO projection，详情页再读全文 | 降低 CursorWindow 与对象构造成本 |
| 只读必要行 | 加 `LIMIT`，分页查询不要一次取全量 | 控制单次查询时间和内存占用 |
| 把计算交给 SQL | 过滤、排序、计数、去重用 SQL 表达 | 避免把大量行搬到 Kotlin/Java 后再处理 |
| 复合索引匹配查询形状 | 结合等值、范围、排序和选择性决定列顺序 | 减少无关行访问和临时排序 |
| 批量写入进事务 | 多条 insert/update/delete 合并提交 | 减少独立提交，但控制事务时长 |
| 清理无效索引 | 用线上 SQL 采样和 `EXPLAIN QUERY PLAN` 反查 | 降低写入维护成本 |

下面的 SQL 用于在接近真实分布的本地数据库上检查查询计划。预期能按 `conversation_id` 搜索复合索引，并利用索引顺序返回时间序结果。

```sql
EXPLAIN QUERY PLAN
SELECT id, conversation_id, sender_name, preview, sent_at
FROM messages
WHERE conversation_id = 42
ORDER BY sent_at DESC
LIMIT 50;
```

即使输出出现 `SCAN`，也不能脱离对象判断它一定错误：小表扫描、覆盖索引扫描或统计信息变化都可能使扫描成为合理选择。应同时检查扫描对象、临时 B-tree、返回行数和实际耗时。空库或均匀小样本也不能代表线上偏斜分布。

查询回归可以进入 CI：为关键 DAO 准备有代表性的规模与分布，验证结果正确性、索引是否存在，并对明显的计划退化和耗时变化报警。不要断言完整的 `EXPLAIN QUERY PLAN` 文本；SQLite 明确不保证该输出格式跨版本稳定。

[SQLite 文档：[`EXPLAIN QUERY PLAN`](https://sqlite.org/eqp.html)、[Query Planner](https://sqlite.org/queryplanner.html)]

## 数据库迁移与版本管理

Room 第一次打开数据库时会校验模式，并按版本图执行自动或手写 Migration。自动迁移适合 Room 能明确推导的简单改动；重命名、删除、拆表、合表和数据转换通常需要 `AutoMigrationSpec` 或手写 `Migration`。导出的模式 JSON 既服务于自动迁移，也让 `MigrationTestHelper` 能创建历史版本。

迁移设计分三层：

- 模式改动：新增表、列、索引或视图，SQL 必须与导出的目标模式一致。
- 数据转换：能在短事务内完成的小规模转换随 Migration 执行；大表转换应设计分阶段兼容、可恢复的后台回填，不能把一个未完成的模式状态暴露给旧代码。
- 发布策略：只有明确可重建的数据才允许破坏性重建，用户资产库必须提供完整迁移路径。

大表转换可以跨两个应用版本完成。版本 N 先增加可空的新列或新表，新代码同时兼容新旧表示，写入时维护两份表示；后台任务按稳定主键分批回填并记录游标，进程被终止后从已确认的位置继续。回填期间的读取必须能识别“新表示尚未生成”，不能把空值当作业务结果。等监控确认受支持版本的回填已经完成，后续版本再增加非空约束、停止写旧表示并删除旧列或旧表。若仍需支持直接从更早版本升级，迁移图和读取逻辑也要保留这条路径。

下面的 Migration 只新增带默认值的列和索引。它适合展示明确的 8→9 版本边，但不代表对任意大小的 `messages` 表都足够快。

```kotlin
val MIGRATION_8_9 = object : Migration(8, 9) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL(
            "ALTER TABLE messages " +
                "ADD COLUMN sync_state INTEGER NOT NULL DEFAULT 0"
        )
        db.execSQL(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_sync_state_sent_at
            ON messages(sync_state, sent_at)
            """.trimIndent()
        )
    }
}
```

创建索引和重建表都可能扫描或重写大量数据。把首次打开移到工作线程只能移开主线程等待，不能消除 I/O，也可能与冷启动争用 CPU 和存储。应用应明确数据库就绪状态；对无法在启动预算内完成的大迁移，采用兼容新旧字段的分阶段版本和可恢复回填。

下面的仪器测试用于验证 8→9 的模式和数据。`runMigrationsAndValidate()` 校验目标模式，测试代码还要查询旧行，确认默认值与用户数据都被保留。

```kotlin
@RunWith(AndroidJUnit4::class)
class AppDatabaseMigrationTest {
    @get:Rule
    val helper = MigrationTestHelper(
        InstrumentationRegistry.getInstrumentation(),
        AppDatabase::class.java.canonicalName,
        FrameworkSQLiteOpenHelperFactory()
    )

    @Test
    fun migrate8To9() {
        helper.createDatabase("migration-test", 8).apply {
            execSQL(
                """
                INSERT INTO messages(
                    id, conversation_id, server_id, sender_name, preview, sent_at, body
                ) VALUES(1, 42, 's-1', 'alice', 'hello', 1000, 'hello body')
                """.trimIndent()
            )
            close()
        }

        helper.runMigrationsAndValidate(
            "migration-test",
            9,
            true,
            MIGRATION_8_9
        ).use { db ->
            db.query("SELECT body, sync_state FROM messages WHERE id = 1").use { cursor ->
                assertTrue(cursor.moveToFirst())
                assertEquals("hello body", cursor.getString(0))
                assertEquals(0, cursor.getInt(1))
            }
        }
    }
}
```

这个测试只覆盖一条相邻迁移。发布检查还要从所有受支持的历史版本打开当前数据库，走完整迁移图，并验证关键业务数据。缺少路径时，Room 会在打开阶段抛出异常，不应等灰度崩溃后才发现。

`fallbackToDestructiveMigration()` 只适合经过产品确认可以重建的数据。缺少迁移路径时，它会删除数据库表中的数据并重建。用户草稿、离线内容、支付状态和消息记录不能使用这项配置。缓存库采用它时，也应记录触发版本和重建成本。

迁移发版前的检查：

- `exportSchema = true`，模式 JSON 提交到版本库。
- 所有历史版本到当前版本的迁移路径可测试。
- 大表转换有兼容阶段、进度记录和中断恢复方案。
- Migration 耗时按起始版本、设备和库大小观察。
- 破坏性重建只用于可恢复数据，并记录触发情况。

[官方文档：[迁移 Room 数据库](https://developer.android.com/training/data-storage/room/migrating-db-versions)、[`MigrationTestHelper`](https://developer.android.com/reference/androidx/room/testing/MigrationTestHelper)]

## 扩展：SQLite vs Realm vs ObjectBox 选型

SQLite/Room 仍是 Android 本地结构化数据的常用选择。它有稳定的 SQL 语义、明确的迁移路径，也能结合 SQLite shell、数据库检查器、Perfetto 追踪和 ANR 栈排查。团队仍需负责表结构、索引、迁移和查询性能。

Realm 与 ObjectBox 采用不同于 SQLite 的对象存储和查询接口，也会带来专有文件格式、原生库、迁移工具和版本兼容责任。本项目没有针对它们当前版本的同机、同数据、同查询基准，因此不能给出性能排名。

Realm 还存在产品生命周期边界。MongoDB 已在 2025 年 9 月 30 日终止 Atlas Device SDKs 和 Device Sync；本地 Realm 数据库继续以开源项目存在。Realm Kotlin 仓库建议无同步功能的项目使用 3.0.0 以上版本或 `community` 分支。新项目若仍考虑 Realm，必须先确认所选制品、维护分支、Kotlin/Gradle 兼容范围和升级负责人，不能把已终止的云端同步能力列入方案。

| 核查维度 | SQLite/Room | Realm 系列 | ObjectBox |
| --- | --- | --- | --- |
| 存储与查询 | 验证 SQL、事务、关系与全文检索需求 | 验证对象关系、查询限制和线程语义 | 验证对象关系、查询限制和事务语义 |
| 生命周期 | 锁定 Room、驱动和 SQLite 版本 | 明确本地数据库分支；排除已终止的 Device Sync | 核对当前制品、许可证与支持周期 |
| Android 17 兼容 | 测试所用 Room/驱动，不只看 API 级别 | 测试 Kotlin/Gradle、ABI 和原生库 | 测试插件、ABI 和原生库 |
| 16 KiB 页设备 | 检查所有自带 SQLite 原生库 | 验证 Realm Core 制品 | 验证 ObjectBox 原生制品 |
| 升级与恢复 | 覆盖历史迁移、备份和损坏恢复 | 演练文件迁移、回滚和导出 | 演练模型 UID、文件迁移和回滚 |
| 性能验证 | 用目标查询和数据分布建立基线 | 使用相同数据、事务边界与持久性配置 | 使用相同数据、事务边界与持久性配置 |

选型应依据数据关系、查询复杂度、持久性要求和团队维护周期。涉及订单、支付状态、用户草稿或消息记录时，先验证迁移、回滚、损坏恢复和可观测性，再比较接口代码量。任何带原生库的方案还要在 Android 17 目标 ABI 和 16 KiB 页设备上做安装、打开、读写、升级与恢复测试。

[生命周期资料：[Atlas Device SDKs 弃用说明](https://www.mongodb.com/docs/atlas/device-sdks/deprecation/)、[Realm Kotlin 仓库说明](https://github.com/realm/realm-kotlin)]

## 小结

WAL 允许读写并发，但不提供并行写入；Android 17 的 Compatibility WAL、连接池和 checkpoint 参数应按源码与设备生效值解释。Room 要分清 AndroidX 版本与平台版本，使用异步 DAO，控制事务范围，并观察查询失效与连接等待。索引必须对应查询和数据分布，不能只凭 `EXPLAIN QUERY PLAN` 中的一个词判断。数据库升级则要覆盖完整迁移图，大表转换采用兼容版本与可恢复回填，并对用户数据验证迁移、回滚和恢复能力。
