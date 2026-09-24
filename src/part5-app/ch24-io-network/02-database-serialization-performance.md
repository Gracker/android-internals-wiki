---
title: 数据库与序列化性能
chapter: '24.2'
section: '24.2'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1; AndroidX Room 2.8.4 and Room 3.0.1 source/release notes; AndroidX SQLite 2.7.0 source/release notes; SQLite official documentation; MongoDB Atlas Device SDK deprecation and Realm Kotlin repository
confidence: high
sources:
- type: aosp
  path: frameworks/base/core/java/android/database/sqlite/SQLiteDatabase.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/database/sqlite/SQLiteConnectionPool.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/database/sqlite/SQLiteSession.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/database/sqlite/SQLiteGlobal.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/database/CursorWindow.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/libs/androidfw/CursorWindow.cpp @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/res/res/values/config.xml @ android-17.0.0_r1
- type: official
  path: https://developer.android.com/topic/performance/sqlite-performance-best-practices
- type: official
  path: https://developer.android.com/training/data-storage/room
- type: official
  path: https://developer.android.com/training/data-storage/room/migrating-db-versions
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/room3
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/room
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/sqlite
- type: official
  path: https://developer.android.com/blog/posts/modernizing-the-room
- type: official
  path: https://developer.android.com/kotlin/multiplatform/room
- type: official
  path: https://developer.android.com/reference/androidx/room/RoomDatabase.JournalMode
- type: official
  path: https://dl.google.com/dl/android/maven2/androidx/room/room-runtime-android/2.8.4/room-runtime-android-2.8.4-sources.jar
- type: official
  path: https://dl.google.com/dl/android/maven2/androidx/room/room-runtime/2.8.4/room-runtime-2.8.4-sources.jar
- type: official
  path: https://dl.google.com/dl/android/maven2/androidx/room3/room3-runtime-android/3.0.1/room3-runtime-android-3.0.1-sources.jar
- type: official
  path: https://source.android.com/docs/core/perf/compatibility-wal
- type: official
  path: https://sqlite.org/wal.html
- type: official
  path: https://sqlite.org/eqp.html
- type: official
  path: https://sqlite.org/walformat.html
- type: official
  path: https://sqlite.org/withoutrowid.html
- type: official
  path: https://www.mongodb.com/docs/atlas/device-sdks/deprecation/
- type: upstream
  path: https://github.com/realm/realm-kotlin
- type: clippings
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: clippings
  path: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md
- type: clippings
  path: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md
- type: aosp
  path: frameworks/base/core/java/android/os/Parcel.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/os/TransactionTooLargeException.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/native/libs/binder/ProcessState.cpp @ android-17.0.0_r1
- type: aosp-kernel
  path: drivers/android/binder_alloc.c @ android17-6.18-2026-06_r6
- type: official
  path: https://developer.android.com/reference/android/os/Parcelable
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview
- type: official
  path: https://github.com/google/gson/blob/main/README.md
- type: official
  path: https://github.com/google/gson/blob/main/Troubleshooting.md
- type: official
  path: https://github.com/square/moshi/blob/master/README.md
- type: official
  path: https://square.github.io/moshi/1.x/moshi/moshi/com.squareup.moshi/-json-adapter/index.html
- type: official
  path: https://github.com/Kotlin/kotlinx.serialization/blob/master/README.md
- type: official
  path: https://kotlinlang.org/docs/serialization.html
- type: legacy-reference-preserved
  path: https://square.github.io/moshi/
- type: legacy-reference-preserved
  path: https://android.googlesource.com/platform/external/kotlinx.serialization/+/refs/heads/upstream-1.2.0-release/docs/json.md
- type: official
  path: https://protobuf.dev/overview/
- type: official
  path: https://protobuf.dev/programming-guides/proto3/
- type: official
  path: https://protobuf.dev/programming-guides/field_presence/
- type: official
  path: https://protobuf.dev/reference/java/java-generated/
- type: official
  path: https://github.com/google/flatbuffers/blob/master/README.md
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/microbenchmark-write
- type: official
  path: https://developer.android.com/guide/components/activities/parcelables-and-bundles
- type: official
  path: https://developer.android.com/kotlin/parcelize
- type: official
  path: https://developer.android.com/topic/performance/vitals/launch-time
- type: clippings
  path: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md
- type: clippings
  path: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md
tags:
- sqlite
- room
- wal
- database-index
- query-optimization
- serialization
- json
- protobuf
- parcelable
- flatbuffers
related_chapters:
- '24.1'
- '9.2'
- '6.2'
- '15.1'
- '24.5'
- '1.9'
- '21.1'
pipeline_stage: finalized
last_review_finalize_at: '2026-08-15T09:33:20+08:00'
last_review_finalize_run_id: 20260815-093320-gracker-writing-review
last_draft_polish_at: '2026-08-15T09:33:20+08:00'
last_draft_polish_run_id: 20260815-093320-gracker-writing
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch10-memory-perf/07-sqlite-room-performance.md
- src/part5-app/ch24-io-network/17-room3-sqlitedriver-kmp-performance.md
- src/part5-app/ch24-io-network/02-database-optimization.md
- src/part5-app/ch24-io-network/03-serialization-performance.md
---

# 数据库与序列化性能

数据持久化包含对象序列化、数据库事务、索引查询和结果反序列化。数据库慢不一定来自 SQL，格式转换、对象分配和主线程等待也可能占据主要时间。

## 事务、索引、查询计划与并发

### 数据库性能问题的等待边界

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。Room 属于独立发布的 AndroidX 组件，行为应以项目锁定的 Room 版本为准，不能只用 Android API 级别推断。涉及 WAL 同步和文件持久性时，沿用 [24.1 文件 I/O、SAF 与 ContentResolver 性能](01-file-io-saf-contentresolver.md)中的 `android17-6.18-2026-06_r6` 内核锚点。

数据库慢通常不会表现成 CPU 满载。常见现象是主线程等待查询、工作线程排队申请连接、Migration（数据库结构迁移）占用首次打开时间，或者列表滚动时 `CursorWindow`（分段保存查询结果的内存窗口）反复填充。Perfetto 和线程栈中常见 `SQLiteConnectionPool.waitForConnection()`、`SQLiteSession.executeForCursorWindow()`、DAO（Data Access Object，数据访问对象）生成代码，或 `ContentResolver.query()` 的 Binder 跨进程等待。

排查时先确认线程是在执行 SQL、等待连接、等待 Binder，还是等待数据库首次打开；再结合 SQLite 并发、`CursorWindow`、Room 执行模型和 ANR 现场，决定是否修改日志模式、查询、索引、事务或迁移。

### SQLite WAL 模式与并发优化

回滚日志模式会在修改主库页之前保存旧内容，写事务需要排除读者时，新的读写访问会受锁状态限制。WAL（Write-Ahead Logging，预写式日志）改为把新页追加到 `-wal` 文件：读事务记录自己的 end mark（当前快照可见的 WAL 终点），再用主库与该位置之前的 WAL frame（记录一次数据库页变更的帧）组成一致快照；写者可以在既有读者读取旧快照时继续追加。两种模式都只有一个活跃写者，WAL 提供读写并发，不提供并行写入。

Android 官方性能文档建议：除使用 `ATTACH DATABASE` 的场景外启用 WAL，并在 WAL 下使用 `synchronous=NORMAL`。这个选择改变持久性边界：应用进程崩溃后事务仍可恢复，但设备断电或内核崩溃可能回滚已经返回成功的事务。订单、支付或跨库依赖不能只按吞吐量选择同步级别。

#### Android 9 的 Compatibility WAL 到 Android 17 的变化

Android 9 引入 Compatibility WAL 时，[官方历史文档](https://source.android.com/docs/core/perf/compatibility-wal)描述的是“WAL 日志模式 + 每库最多一个连接”。Android 17 源码不能继续套用这个连接数结论：

- `SQLiteCompatibilityWalFlags` 从 `Settings.Global.SQLITE_COMPATIBILITY_WAL_FLAGS` 读取 `legacy_compatibility_wal_enabled`；
- 只有应用没有显式指定日志/同步模式（`journal/sync mode`）时，旧兼容开关（`legacy compatibility flag`）才生效；
- `SQLiteDatabaseConfiguration.resolveJournalMode()` 会把它解析成 WAL；
- `SQLiteConnectionPool` 看到解析结果为 WAL 后，使用 `SQLiteGlobal.getWALConnectionPoolSize()`，而 `android-17.0.0_r1` 的资源默认值是 4，厂商和调试属性仍可覆盖。

“Compatibility WAL 永远单连接”只适用于 Android 9 的历史说明。调查 Android 17 设备时，应读取当前连接池诊断输出和生效配置，不按旧文档猜连接数。该全局兼容开关属于平台内部配置，不是应用可依赖的 SDK 契约；应用应通过实际使用的数据库 API 明确选择日志模式。

[源码锚点：[`SQLiteCompatibilityWalFlags.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteCompatibilityWalFlags.java)、[`SQLiteDatabaseConfiguration.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabaseConfiguration.java)、[`SQLiteConnectionPool.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnectionPool.java)]

#### Android 17 的 WAL 默认参数

在 `android-17.0.0_r1` 中：

| 参数 | AOSP 默认值 | 含义 |
| --- | ---: | --- |
| `db_wal_sync_mode` | `NORMAL` | WAL 连接默认同步模式 |
| `db_wal_autocheckpoint` | 100 | 自动 checkpoint 阈值，单位是数据库页 |
| `db_connection_pool_size` | 4 | framework WAL 连接池资源默认值 |

这些是 AOSP 资源默认值，不是所有设备和所有 Room 驱动的固定值。系统属性、资源覆盖、应用显式配置和 AndroidX 驱动都可能改变结果。100 页也不能直接按 4 KiB 内存页换算；应查询该数据库的 `PRAGMA page_size`。

[源码锚点：[`SQLiteGlobal.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteGlobal.java)、[`config.xml`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml)]

#### Checkpoint（检查点）、长读事务与生效值

checkpoint 把已提交的 WAL frame 写回主库。`PASSIVE` checkpoint 可以推进到活跃读事务允许的位置；持有较老 end mark 的长读事务会让它提前停止，而后续写入仍可继续追加，于是 `-wal` 文件可能持续增长。调小自动 checkpoint 阈值不能结束这些读事务；应先找到没有结束的读事务和生命周期过长的 Cursor。

```sql
PRAGMA journal_mode;
PRAGMA page_size;
PRAGMA wal_autocheckpoint;
PRAGMA wal_checkpoint(PASSIVE);
```

`wal_checkpoint` 的结果包含 busy 状态（仍有活跃事务阻止完全推进）、WAL frame 数和已写回主库的 frame 数。后两者长期拉开时，应关联长读事务、写入批次和 checkpoint 时机。普通 checkpoint 使用 WAL 共享内存中的写锁、checkpoint 锁与读标记协调，不能概括为“先取得主数据库 EXCLUSIVE 锁”。切换日志模式、恢复和带截断语义的操作另有锁边界。

#### Room 怎样选择日志模式

判断 Room 2.8.4 的日志模式必须区分 `source set`（Kotlin Multiplatform 按目标平台区分的源码集合）。Android `actual` 实现有 `AUTOMATIC`、`TRUNCATE` 和 `WRITE_AHEAD_LOGGING`，Builder 默认是 `AUTOMATIC`；它在普通设备解析为 WAL，在低内存设备解析为 `TRUNCATE`。common/KMP（Kotlin Multiplatform）声明只有后两项，Builder 默认 WAL。官网聚合 API 可能同时呈现不同 `source set` 的说明，因此 Android 项目应核对 `RoomDatabase.android.kt`，KMP 或自定义驱动项目则核对实际目标和依赖源码。

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

使用 Room 3 / `SQLiteDriver`（Room 连接具体 SQLite 引擎的驱动接口）的项目不能照搬 framework `SQLiteConnectionPool` 的连接数和 `CursorWindow` 结论。驱动会改变 Room 使用的 SQLite 实现与数据传递路径，具体边界见 [Room 3 与 SQLiteDriver 迁移边界](#room-3-与-sqlitedriver-迁移边界)。

#### Session、连接池与等待对象

Android framework 的 `SQLiteDatabase` 为每个线程保存一个 `SQLiteSession`。Session 只维护事务与连接使用状态；执行语句时仍要向 `SQLiteConnectionPool` 申请连接。线程停在 `waitForConnection()` 表示当前没有符合要求的连接可用，不等于它长时间卡在保护连接池状态的 Java 对象监视器锁上。

WAL 下，平台池可用非主连接服务只读工作，写事务通常要使用主连接；增加只读连接也不会增加 SQLite 写连接数量。Room 2.8.4 的默认 SupportSQLite 兼容路径使用 passthrough pool（只转交连接请求、不自行管理物理连接的池），实际连接仍由 Android framework 管理；只有驱动本身没有连接池时，`RoomConnectionManager` 才自建池，并把 WAL 映射为最多 4 个只读连接、1 个写连接，`TRUNCATE` 下各为 1 个。

这些数字是特定路径的当前实现，不是应用可依赖的稳定契约。看到连接等待时，先查长事务、耗时过长的读取、未关闭资源、写入队列和首次打开，不要先扩池。

WAL 的应用侧检查项：

- 在目标设备读取实际生效的日志/同步模式，不把 Builder 选项当作运行结果。
- 如果使用 `ATTACH DATABASE`，重新评估 WAL；官方文档把 `ATTACH DATABASE` 列为启用 WAL 的例外条件。
- 大事务后观察 `-wal` 文件增长、读事务持续时间和 checkpoint 耗时；长期读事务可能阻止 checkpoint 推进。
- 不在主线程首次打开数据库。首次打开可能触发模式校验、Migration、预置库复制或 checkpoint。
- 连接池等待先查长事务、慢查询和连接持有者，再考虑改变池大小。

[官方文档：[SQLite 性能建议](https://developer.android.com/topic/performance/sqlite-performance-best-practices)、[`RoomDatabase.JournalMode`](https://developer.android.com/reference/androidx/room/RoomDatabase.JournalMode)、[SQLite WAL](https://sqlite.org/wal.html)]

### Room 执行模型与常见性能问题

Room 提供编译期 SQL 校验、DAO 生成、迁移管理和异步 API 适配，不会自动降低 SQL、连接等待和事务提交的成本。`allowMainThreadQueries()` 只是关闭主线程保护，不会降低查询耗时；它可以用于受控测试，不应进入发布数据库配置。

Room 性能问题常出现在四类位置：同步 DAO 被界面路径调用、首次打开落在启动主线程、事务范围过大，以及可观察查询在表失效后反复执行。

DAO 方法按执行模型分开设计：

| DAO 形态 | 执行位置 | 使用场景 | 风险 |
| --- | --- | --- | --- |
| 普通同步方法 | 调用线程 | 测试、极少量工具代码 | UI 线程调用会被 Room 拦截；关闭拦截后会卡 UI |
| `suspend` 方法 | Room 异步执行机制 | 单次读写、批量写入 | 事务范围过大会长期占用连接 |
| `Flow`（异步数据流） | 观察表失效后重新查询 | UI 订阅数据变化 | 表中任意行变化都可能触发重查 |
| `PagingSource`（分页数据源） | 分页列表 | 大列表、离线缓存 | 深 offset（跳过大量前置行）仍可能扫描许多行，游标分页需按查询设计 |

Room 2.8.4 已提供显式的读写连接 API：同步 DAO 在调用线程执行；`suspend` DAO 通过 Room 的协程上下文申请连接；`Flow` 在开始收集后查询，并在相关表失效时重查；`useReaderConnection()`、`useWriterConnection()` 是显式连接入口。Android 兼容路径仍保留 `queryExecutor` / `transactionExecutor`，驱动路径和 common/KMP 路径则不应套用同一套执行器结论。排障时要看项目实际 `source set`、驱动、生成代码和 `sources.jar`（依赖附带的源码包）。

下面的 DAO 演示列表投影（projection，只读取指定列）与详情实体的区别。列表只选择渲染所需列，正文等大字段留到详情查询；调用方还要限制 `limit` 的合法范围。

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

在 framework SQLite 驱动下，少读列能降低 `CursorWindow` 填充、跨 JNI（Java Native Interface，Java 与原生代码的调用接口）复制和对象构造成本；使用其他 AndroidX SQLite 驱动时，保存查询结果的数据结构可能不同，但“少读行、少读列”仍成立。过滤、排序和聚合也应尽量在 SQL 中完成。

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

为了让生产环境中的 Room 问题可以定位，还需要记录这些信息：

- Room `QueryCallback` 会为每条查询增加回调成本，且回调本身只给出 SQL 与绑定参数，不直接提供执行耗时。若做短期受控采样，应先去除字面参数，再对 SQL 计算散列值（hash，用于归并相同语句）并记录线程，不上传原始参数；耗时应在 DAO/仓库边界或 Perfetto 中另行测量。
- 记录首次打开和 Migration 耗时，把它们和冷启动、首屏、ContentProvider 初始化分开统计。
- 对高频 Flow 查询统计重查次数。某张表每秒多次更新时，观察者可能被重复触发。
- 记录连接池等待栈。Perfetto 里看到 `waitForConnection()` 时，要能反查当前持有写连接的任务。

Android 17 的 `dumpsys meminfo <package>` 在 `DATABASES` 和 `POOL STATS` 中提供 SQLite 页、连接与语句缓存统计。该版本的单连接行与池汇总行中，`cache size` 都表示当前缓存的预编译语句数量。Android 16 的单连接行也是这个含义，但 `POOL STATS` 中的同名列是累计 prepare 次数，也就是命中与未命中之和；跨版本监控必须按行类型和平台版本解释字段。

#### CursorWindow 只保存结果片段

framework 驱动下，`SQLiteCursor` 不要求一次把全部结果装入内存。目标行离开现有窗口时，`SQLiteCursor.onMove()` 会经 `fillWindow()`、`SQLiteQuery.fillWindow()` 进入 `SQLiteSession.executeForCursorWindow()`，所以大结果集可能表现为多轮 SQL 步进与窗口重填。Android 17 的系统资源默认值是 2048 KB；OEM 资源覆盖和显式构造仍可能改变容量。

窗口容量不保证任意大小的单行都能装入。单行文本或 BLOB（二进制大对象）放不进窗口时，减少结果总行数没有帮助，应缩小该行和投影列集合。窗口能够创建、但滚动时不断跨边界，则要减少结果宽度、改进分页，并在 trace 中统计 refill（窗口重新填充）次数，而不是盲目放大窗口。调用方还应及时关闭 Cursor，并给允许取消的查询传入 `CancellationSignal`。

ContentProvider 跨进程返回 Cursor 时，Provider 侧的 `CursorToBulkCursorAdaptor` 按位置获取或重新填充窗口。原生函数 `CursorWindow::writeToParcel()` 会为基于 ashmem（anonymous shared memory，匿名共享内存）的窗口传递一份文件描述符副本；没有 ashmem FD（file descriptor，文件描述符）时，则按已用容量把数据写入 Parcel（Binder 传输的数据容器）。因此，`TransactionTooLargeException`、单行过宽和窗口反复填充是三类问题，不能都归因为“2 MB Binder 限制”。

#### 从 ANR 还原数据库等待

数据库 ANR 可以按停点依次缩小范围：

1. 主线程直接进入生成 DAO 或 `executeForCursorWindow()`：检查首次打开、SQL 计划、返回行数与投影列集合。
2. 线程停在 `waitForConnection()`：寻找持有读连接或写连接的线程、事务起止和未关闭资源。
3. 客户端停在 `ContentResolver.query()` 的 Binder 响应：转到 Provider 进程，追踪同一事务的 SQL、Migration 或连接等待。
4. 写连接遇到 `SQLITE_BUSY` / `SQLITE_LOCKED`：结合另一连接或进程的事务、WAL 与 checkpoint 时间判断锁的来源。
5. Cursor 移动时卡住：确认是否跨窗口触发重新填充，以及 Provider 端是否重新执行或继续步进 SQL。

`StrictMode.detectDiskReads()` / `detectDiskWrites()` 可以提前暴露主线程磁盘访问，但不能发现“主线程等待后台数据库”的所有间接路径。Perfetto 的 Java 对象锁竞争也不覆盖 SQLite 文件锁、WAL 共享内存锁或 `waitForConnection()` 中的线程挂起等待。结论至少应保存 trace 时间戳、SQL、查询计划、数据库与 Room 版本、日志模式、数据库页大小和数据规模。

[官方文档：[异步 DAO 查询](https://developer.android.com/training/data-storage/room/async-queries)、[`RoomDatabase.Builder`](https://developer.android.com/reference/androidx/room/RoomDatabase.Builder)、[SQLite 性能排查工具](https://developer.android.com/topic/performance/sqlite-performance-best-practices)]

### 索引设计与查询优化

索引设计应根据查询形状（过滤、排序、分组所使用的列及顺序）和数据分布决定。查询同时按 `conversation_id` 等值过滤、按 `sent_at` 排序时，两个互不相关的单列索引通常不能同时完成过滤与排序。`EXPLAIN QUERY PLAN` 可显示 `SCAN`、`SEARCH`、`USING INDEX` 和 `USING COVERING INDEX` 等策略，但输出格式不属于稳定的应用接口。

下面的 Room 实体用于展示与前述查询配套的复合索引。等值过滤列放在索引前缀，随后是排序列；SQLite 可以反向扫描 B-tree（按键有序组织数据的树形索引），因此这个索引也可服务 `sent_at DESC`。

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
| 只读必要列 | 列表页使用 DTO（Data Transfer Object，数据传输对象）投影，详情页再读全文 | 降低 CursorWindow 与对象构造成本 |
| 只读必要行 | 加 `LIMIT`，分页查询不要一次取全量 | 控制单次查询时间和内存占用 |
| 把计算交给 SQL | 过滤、排序、计数、去重用 SQL 表达 | 避免把大量行搬到 Kotlin/Java 后再处理 |
| 复合索引匹配查询形状 | 结合等值、范围、排序和选择性决定列顺序 | 减少无关行访问和临时排序 |
| 批量写入进事务 | 多条插入、更新或删除合并提交 | 减少独立提交，但控制事务时长 |
| 清理无效索引 | 用生产环境中的 SQL 采样和 `EXPLAIN QUERY PLAN` 反查 | 降低写入维护成本 |

下面的 SQL 用于在接近真实分布的本地数据库上检查查询计划。预期能按 `conversation_id` 搜索复合索引，并利用索引顺序返回时间序结果。

```sql
EXPLAIN QUERY PLAN
SELECT id, conversation_id, sender_name, preview, sent_at
FROM messages
WHERE conversation_id = 42
ORDER BY sent_at DESC
LIMIT 50;
```

即使输出出现 `SCAN`，也不能脱离被扫描的对象断定它一定是错误选择：小表扫描、覆盖索引扫描或统计信息变化都可能使扫描成为合理选择。应同时检查扫描对象、临时 B-tree、返回行数和实际耗时。空库或均匀小样本也不能代表线上偏斜分布。

查询回归可以进入 CI（Continuous Integration，持续集成）：为关键 DAO 准备有代表性的规模与分布，验证结果正确性、索引是否存在，并对明显的计划退化和耗时变化报警。不要断言完整的 `EXPLAIN QUERY PLAN` 文本；SQLite 明确不保证该输出格式跨版本稳定。

#### Paging 的 OFFSET 与基于排序键的分页边界

Room 2.8.4 的 `LimitOffsetPagingSource` 会包装 DAO 原查询并使用 `LIMIT ... OFFSET ...`。Paging 负责加载、刷新、预取和失效通知；读取深页时，SQLite 仍需扫描并跳过前面的行，投影中的正文或 BLOB 也仍会写入查询结果。

当列表有稳定的复合排序键时，可以在 DAO 中显式提供基于排序键的查询（也称 `keyset` 分页，以上一页末行的排序键作为下一页边界）：

```sql
SELECT id, conversation_id, sent_at, preview
FROM messages
WHERE conversation_id = :conversationId
  AND (
      sent_at < :cursorSentAt
      OR (sent_at = :cursorSentAt AND id < :cursorId)
  )
ORDER BY sent_at DESC, id DESC
LIMIT :limit;
```

对应索引应覆盖 `conversation_id, sent_at, id` 的过滤与排序顺序。基于排序键的分页避免深 OFFSET，却不支持按页码任意跳转；刷新锚点（`refresh anchor`，刷新时选择的重新加载位置）、数据插入和相同时间值都要按业务语义处理。

#### `WITHOUT ROWID` 与 PRAGMA 的适用边界

普通表的 `INTEGER PRIMARY KEY` 已是 rowid 别名。`WITHOUT ROWID` 更适合较短的非整数或复合主键，以及查询频繁沿主键访问的表；它不支持 `AUTOINCREMENT`，大主键还会复制进二级索引。迁移前必须用真实数据比较库大小与读写耗时，不能把它当作通用省空间开关。

PRAGMA 同时包含持久状态与每连接状态。`journal_mode`、`synchronous`、`wal_autocheckpoint`、`busy_timeout`、`cache_size` 和 `page_size` 的生效范围不同；Room 或平台连接池创建多个连接后，在一个临时连接执行 per-connection PRAGMA（仅对当前连接生效的配置）不代表其他连接继承。配置应通过受支持的 Builder、驱动或 open callback（数据库打开回调）统一下发，并逐连接验证。`busy_timeout` 只能把锁冲突改成等待，无法消除长事务，还可能把 UI 或 Binder 路径上的快速失败变成长卡顿。

[SQLite 文档：[`EXPLAIN QUERY PLAN`](https://sqlite.org/eqp.html)、[Query Planner](https://sqlite.org/queryplanner.html)、[`WITHOUT ROWID`](https://sqlite.org/withoutrowid.html)]

### 调度、多进程与加密数据库

SQLite 在同一数据库上同一时间只允许一个写事务，这项约束不会替应用安排业务写入的先后顺序和优先级。高频写入可以先进入一个有容量上限的队列；队列接近满载时，应让生产者减速或拒绝新任务，这就是背压。若同一对象的旧状态可由较新状态覆盖，还可以合并等待中的更新。

事务只包住不可分割的数据变更，不在其中等待网络、结果不确定的回调或无关锁。

读连接数也要根据目标设备的吞吐、P95/P99 延迟（第 95/99 百分位耗时，即 95%/99% 的请求耗时不超过对应数值）、I/O 和数据库页缓存确定；同时启动更多读连接，可能只会让多次大表扫描一起争用存储。

多个进程打开同一数据库文件时，日志模式（例如 WAL）、数据库结构版本（`schema version`）和连接配置必须一致。SQLite 文件锁与 WAL 负责数据库级协调。Room 的多实例失效通知（`multi-instance invalidation`）只告诉其他数据库实例“哪些表发生了变化”，既不提供跨进程事务，也不规定不同进程写入的先后顺序。高频写入宜交给一个职责明确的进程统一接收；数据库迁移、备份、恢复和清库也只能有一个协调者。

若客户端线程停在 Binder 调用，应同时采集实际访问数据库的 ContentProvider 所在进程，不能只看调用端调用栈。

SQLCipher 会在数据库打开、密钥派生和数据页读写路径上增加工作。具体代价取决于 SQLCipher 版本、加密页大小（`cipher_page_size`）、密钥派生函数（KDF，Key Derivation Function）参数、硬件、短期频繁访问的数据页、页缓存与索引，不能套用固定百分比。对比实验至少覆盖冷打开、热查询、批量事务、WAL 检查点、数据库迁移和低端设备，并保持持久性配置相同。Android Keystore 可以保护或封装密钥材料，数据库页面是否透明加密仍由 SQLCipher 等数据库实现负责。

### 数据库迁移与版本管理

Room 第一次打开数据库时会校验数据库结构，并根据版本之间的升级路径执行自动或手写 `Migration`（数据库迁移）。自动迁移适合 Room 能明确推导的简单改动；重命名、删除、拆表、合表和数据转换通常需要 `AutoMigrationSpec`（为自动迁移补充重命名、删除等信息的规范类）或手写 `Migration`。导出的数据库结构 JSON 既用于生成自动迁移，也让 `MigrationTestHelper` 能创建历史版本数据库。

迁移设计分三层：

- 数据库结构改动：新增表、列、索引或视图，SQL 必须与导出的目标结构一致。
- 数据转换：能在短事务内完成的小规模转换随 `Migration` 执行；大表转换应让新旧结构共存一段时间，再由后台任务分批把旧数据补写到新结构。这类“后台回填”必须能在中断后继续，不能把尚未完成的数据库结构暴露给只理解旧结构的代码。
- 发布策略：只有明确可重建的数据才允许破坏性重建，用户资产库必须提供完整迁移路径。

大表转换可以跨两个应用版本完成。版本 N（这里表示任意一个起始版本）先增加可空的新列或新表，新代码同时兼容新旧数据表示，写入时维护两份表示；后台任务按稳定主键分批回填，并记录最近处理完的主键等进度位置。进程被终止后，任务从已确认的位置继续。回填期间的读取必须能识别“新表示尚未生成”，不能把空值当作业务结果。等监控确认所有受支持版本的回填已经完成，后续版本再增加非空约束、停止写旧表示并删除旧列或旧表。若仍需支持从更早版本直接升级，迁移路径和读取逻辑也要覆盖这种情况。

下面的 Migration 只新增带默认值的列和索引。它适合展示明确的 8→9 升级路径，但不代表对任意大小的 `messages` 表都足够快。

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

创建索引和重建表都可能扫描或重写大量数据。让工作线程负责首次打开，只能避免主线程直接执行迁移，不能消除 I/O，也可能与冷启动争用 CPU 和存储。应用应明确数据库何时可用；对无法在可接受的启动时间内完成的大迁移，应采用兼容新旧字段的分阶段版本和可恢复回填。

下面的设备端测试（`instrumented test`，在真机或模拟器内运行）用于验证 8→9 的数据库结构和数据。`runMigrationsAndValidate()` 校验目标结构，测试代码还要查询旧行，确认默认值与用户数据都被保留。

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

这个测试只覆盖一条相邻迁移。发布检查还要从所有受支持的历史版本打开当前数据库，走完每条升级路径，并验证关键业务数据。缺少路径时，Room 会在打开阶段抛出异常，不应等分阶段发布已经出现崩溃才发现。

`fallbackToDestructiveMigration()` 只适合经过产品确认可以重建的数据。缺少迁移路径时，它会删除数据库表中的数据并重建。用户草稿、离线内容、支付状态和消息记录不能使用这项配置。缓存库采用它时，也应记录触发版本和重建成本。

迁移发版前的检查：

- `exportSchema = true`，数据库结构 JSON 提交到版本库。
- 所有历史版本到当前版本的迁移路径可测试。
- 大表转换有兼容阶段、进度记录和中断恢复方案。
- `Migration` 耗时按起始版本、设备和库大小观察。
- 破坏性重建只用于可恢复数据，并记录触发情况。

[官方文档：[迁移 Room 数据库](https://developer.android.com/training/data-storage/room/migrating-db-versions)、[`MigrationTestHelper`](https://developer.android.com/reference/androidx/room/testing/MigrationTestHelper)]

### Room 3 与 SQLiteDriver 迁移边界

Room 3 不是 Room 2 的普通小版本升级。它保留 `@Database`、`@Entity`、`@Dao` 与 `@Query` 的基本模型，但改变了 Maven 坐标（依赖的 `group:artifact` 标识）、运行期 SQLite 接口、代码生成链和异步 API。截至 2026-08-15，稳定版本仍是 [Room 3.0.1](https://developer.android.com/jetpack/androidx/releases/room3) 与 [SQLite 2.7.0](https://developer.android.com/jetpack/androidx/releases/sqlite)；两个库要分别固定版本，不能因为同属 AndroidX 就假设版本号会同步递增。

| 维度 | Room 2.x 常见用法 | Room 3.0.1 | 迁移检查 |
| --- | --- | --- | --- |
| 包名与坐标 | `androidx.room:*` | `androidx.room3:room3-*` | 更新依赖、导入、反射类名与混淆规则 |
| SQLite 接口 | `SupportSQLiteDatabase`、`Cursor` | `SQLiteDriver`、`SQLiteConnection`、`SQLiteStatement` | 替换直接查询、回调与迁移签名 |
| 代码生成 | KAPT（Kotlin 注解处理）、Java AP（Java 注解处理）或 KSP（Kotlin 符号处理） | 只支持 KSP，生成 Kotlin | 数据模块启用 Kotlin 与 KSP，检查增量编译 |
| DAO 调用 | 同步、Executor、协程并存 | 数据库操作使用协程或响应式接口 | DAO 改为 `suspend`、`Flow` 等类型 |
| 失效通知 | `InvalidationTracker.Observer` | `InvalidationTracker.createFlow()` | 改写观察者注册与注销 |
| 多平台 | 以 Android 为主 | Android、Apple、JVM、JS、WasmJS | 每个平台分别选择驱动与建立基线 |

Room 3 只生成 Kotlin，但 KSP 仍能处理 Java 编写的数据库、DAO 和实体；Java 调用方也可调用生成代码。包含这些声明的模块仍必须启用 Kotlin 编译器与 KSP。`androidx.room` 与 `androidx.room3` 可以同时出现在依赖图中，主要用于避免 WorkManager 等库间接引入旧 Room 后造成类冲突；这不表示两个 Room 实例可以并发打开同一个数据库文件。

#### 固定依赖、驱动与数据库结构输出

下面的最小配置选择平台 `AndroidSQLiteDriver`。若使用 `BundledSQLiteDriver`，替换为 `androidx.sqlite:sqlite-bundled:2.7.0`；不要同时引入两个实现，再让不同模块各自选择引擎。

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
    id("androidx.room3")
}

val roomVersion = "3.0.1"
val sqliteVersion = "2.7.0"

dependencies {
    implementation("androidx.room3:room3-runtime:$roomVersion")
    ksp("androidx.room3:room3-compiler:$roomVersion")
    implementation("androidx.sqlite:sqlite-framework:$sqliteVersion")
}

room3 {
    schemaDirectory("$projectDir/schemas")
}
```

Room Gradle Plugin 要求配置 `schemaDirectory`。带构建变体（由 build type、product flavor 等组合出的构建版本）的项目会在对应目录生成数据库结构 JSON；这些文件是自动迁移与迁移测试的输入，必须提交仓库，并由 CI 检查是否出现未提交的结构变化。构建性能要分别测完整构建、DAO/Entity 增量构建、普通 Kotlin 增量构建和远端构建缓存命中。只有 Gradle、JDK、Kotlin、KSP 与缓存条件相同，测量结果才有可比性。

Android 上的两种驱动不能共用一套未经验证的性能结论：

| 项目 | `AndroidSQLiteDriver` | `BundledSQLiteDriver` |
| --- | --- | --- |
| SQLite 引擎 | Android 系统提供 | AndroidX 随应用携带一份原生 SQLite 库 |
| 版本一致性 | 随系统变化 | 各受支持平台更一致 |
| 连接池 | 驱动内部已有连接池 | 驱动本身没有连接池，Room 配置连接池 |
| 线程边界 | 平台连接池处理并发 | 单个连接不能被多个线程同时使用 |
| 工程代价 | 不增加一份 SQLite 原生库 | 增加安装包体积、动态库装载和不同 CPU 架构的兼容成本 |

`AndroidSQLiteDriver.hasConnectionPool` 为 `true`，Room 的 `setSingleConnectionPool()` 与 `setMultipleConnectionPool(...)` 对它不生效。`BundledSQLiteDriver.hasConnectionPool` 为 `false`；默认情况下，Room 对 `TRUNCATE` 使用单连接，对 WAL 使用读写连接池。增加连接数不等于吞吐提升，写入仍受 SQLite 串行化约束，配置不当还可能得到 `SQLITE_BUSY`。Android 专用应用应在相同数据库、日志模式、设备和构建类型下比较两种驱动，再决定是否接受随库 SQLite 的体积与初始化代价。

```kotlin
fun buildAppDatabase(context: Context): AppDatabase =
    Room.databaseBuilder(
        context.applicationContext,
        AppDatabase::class.java,
        "app.db"
    )
        .setDriver(AndroidSQLiteDriver())
        .build()
```

若配置 `setQueryCoroutineContext(...)`，上下文必须包含决定协程在哪些线程执行的 `CoroutineDispatcher`。增加调度器线程数不能修复慢查询、长事务或连接长期占用。

#### 直接查询与兼容包装层

Room 3 中，`RoomDatabase.useReaderConnection()` / `useWriterConnection()` 交给调用方的是受池管理的连接。直接查询应在作用域内调用 `usePrepared()`，不能把 `connection` 或 `statement` 保存到成员变量，也不能在占用连接时执行网络、JSON 解析或大段业务计算。

```kotlin
suspend fun findUserName(
    db: AppDatabase,
    userId: Long,
): String? = db.useReaderConnection { connection ->
    connection.usePrepared(
        "SELECT name FROM users WHERE id = ?"
    ) { statement ->
        statement.bindLong(1, userId)
        if (statement.step()) statement.getText(0) else null
    }
}
```

参数绑定可以避免把外部值直接拼入 SQL 所造成的注入风险，也能让同一种查询保持稳定的 SQL 文本，便于复用预编译语句；它不会替应用修正索引、数据分布或事务范围。等待连接超过内部期限会抛出 `SQLiteException`，应纳入稳定性监控。跨数据库事务也要明确规定调用顺序；SQLite 的单库事务不能保证多个数据库同时提交或同时回滚。

Room 3 移除了 Room 接口中的 `SupportSQLiteDatabase`、`SupportSQLiteOpenHelper` 和 Android `Cursor`。`androidx.room3:room3-sqlite-wrapper:3.0.1` 可在迁移期通过 `getSupportWrapper()` 提供临时兼容层，用来适配调试面板、一次性导出或尚未改造的第三方库。`Migration`、`Callback`、高频查询和批量写入应迁移到 `SQLiteConnection`、DAO 或受连接池管理的 API；不要把这个兼容层放进新的全局工具类，让新代码继续依赖旧接口。

#### 数据库结构、跨平台与回退验收

每个仍受支持的历史数据库结构都要经过 `MigrationTestHelper`。测试除确认目标结构完全一致外，还应覆盖非空列、默认值、索引、外键、触发器、FTS5 全文检索表、`WITHOUT ROWID` 表、复合关系键、大数据集重建与迁移中断。Room 2 与 Room 3 包名可以共存，但迁移同一个数据库文件时只能有一个打开者。

应用版本回退比改回 Maven 依赖版本更困难。新应用把设备上的数据库结构从 N 升到 N+1 后，旧应用必须能识别 N+1，或提供验证过的降级迁移；远程开关不能撤销已经写入数据库的结构变化。`fallbackToDestructiveMigrationOnDowngrade()` 只适用于明确允许丢失的数据。分阶段发布前应执行“旧版本写入 → 新版本迁移并读写 → 旧版本重新打开”的完整测试。

Room 3 支持 JavaScript 与 WasmJS（以 WebAssembly 为目标的 Kotlin/JS 运行方式）。SQLite 2.7.0 的 `WebWorkerSQLiteDriver` 可把数据库操作放进 Web Worker，并将文件保存到 OPFS（Origin Private File System，浏览器为站点提供的私有文件系统），但项目要自行提供符合消息协议的 Worker 脚本。Web 与非 Web 平台共用代码时，可以评估异步 SQLite 接口 `androidx.sqlite:sqlite-async:2.7.0`；Android、Web、Apple 与桌面 JVM 必须分别建立性能基线，共享 DAO 不会消除驱动、文件系统和线程模型的差异。

迁移性能要分别观察应用启动、数据库首次打开、每段 `Migration`、首个关键 DAO、稳定期查询和连接等待。为这些阶段添加自定义 trace（可在 Perfetto 时间轴上定位的事件区间），再用固定数据集的 Macrobenchmark（Android 宏基准测试）、Perfetto、查询计划和数据库测试交叉验证。记录表行数、索引、数据库/WAL 大小、驱动、日志模式、Room 版本、设备、构建类型、R8 代码优化状态与 Baseline Profile（预先指定热点代码的编译配置）；平均值不能替代 P95/P99 延迟和迁移失败率。

迁移时依次检查这些事项：固定 Room 3.0.1 与 SQLite 2.7.0；启用 Kotlin/KSP 和数据库结构输出；选择并验证一种驱动；改造同步 DAO、回调以及直接使用 SupportSQLite 接口的代码；从每个受支持版本执行升级与应用版本回退测试；在分阶段发布期间观察迁移失败、`SQLiteException`、ANR、数据库损坏与关键操作耗时。

### SQLite、Realm 与 ObjectBox 选型

SQLite/Room 仍是 Android 本地结构化数据的常用选择。它有稳定的 SQL 语义、明确的迁移路径，也能结合 SQLite shell（命令行客户端）、数据库检查器、Perfetto 追踪和 ANR 栈排查。团队仍需负责表结构、索引、迁移和查询性能。

Realm 与 ObjectBox 采用不同于 SQLite 的对象存储和查询接口，也会带来专有文件格式、原生库、迁移工具和版本兼容责任。本项目没有针对它们当前版本的同机、同数据、同查询基准，因此不能给出性能排名。

Realm 还存在产品生命周期边界。MongoDB 已在 2025 年 9 月 30 日终止 Atlas Device SDKs 和 Device Sync；本地 Realm 数据库继续以开源项目存在。复核时，Realm Kotlin 仓库建议无同步功能的项目使用 3.0.0 以上版本或 `community` 分支。新项目若仍考虑 Realm，必须先确认所选依赖包、维护分支、Kotlin/Gradle 兼容范围和升级负责人，不能把已终止的云端同步能力列入方案。

| 核查维度 | SQLite/Room | Realm 系列 | ObjectBox |
| --- | --- | --- | --- |
| 存储与查询 | 验证 SQL、事务、关系与全文检索需求 | 验证对象关系、查询限制和线程语义 | 验证对象关系、查询限制和事务语义 |
| 生命周期 | 锁定 Room、驱动和 SQLite 版本 | 明确本地数据库分支；排除已终止的 Device Sync | 核对当前依赖包、许可证与支持周期 |
| Android 17 兼容 | 测试所用 Room/驱动，不只看 API 级别 | 测试 Kotlin/Gradle、ABI（应用二进制接口，对应不同 CPU 架构）和原生库 | 测试插件、ABI 和原生库 |
| 16 KiB 页设备 | 检查所有自带 SQLite 原生库 | 验证 Realm Core（Realm 的原生存储引擎）依赖包 | 验证 ObjectBox 原生依赖包 |
| 升级与恢复 | 覆盖历史迁移、备份和损坏恢复 | 演练文件迁移、回滚和导出 | 演练模型 UID（模型属性的稳定标识）、文件迁移和回滚 |
| 性能验证 | 用目标查询和数据分布建立基线 | 使用相同数据、事务边界与持久性配置 | 使用相同数据、事务边界与持久性配置 |

选型应依据数据关系、查询复杂度、持久性要求和团队维护周期。涉及订单、支付状态、用户草稿或消息记录时，先验证迁移、回滚、损坏恢复和监控手段，再比较接口代码量。任何带原生库的方案还要针对 Android 17 支持的目标 CPU 架构和 16 KiB 内存页设备，执行安装、打开、读写、升级与恢复测试。

[生命周期资料：[Atlas Device SDKs 弃用说明](https://www.mongodb.com/docs/atlas/device-sdks/deprecation/)、[Realm Kotlin 仓库说明](https://github.com/realm/realm-kotlin)]

### 数据库小结

WAL 允许读写并发，但不提供并行写入；Android 17 的 Compatibility WAL、连接池和 checkpoint 参数应按源码与设备生效值解释。Room 要分清 AndroidX 版本与平台版本，使用异步 DAO，控制事务范围，并观察查询失效与连接等待。索引必须对应查询和数据分布，不能只凭 `EXPLAIN QUERY PLAN` 中的一个词判断。数据库升级要覆盖所有受支持的升级路径，大表转换应让新旧结构分阶段共存并支持中断后继续，同时验证用户数据的迁移、回滚和恢复能力。

## 编码格式、对象分配与兼容性

数据库访问确定行和列后，序列化负责把数据转换为内存或网络格式。选择时要同时比较体积、CPU、分配和 schema 演进。

### 序列化成本出现在哪里

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`；涉及 Binder 驱动时，内核锚点是 `android17-6.18-2026-06_r6`。JSON、Protocol Buffers、FlatBuffers 等库独立于 Android 平台发布，行为要以项目锁定的依赖版本为准。

序列化把内存中的对象编码成可传输或保存的数据，反序列化则把这些数据还原成运行时对象。两步都会消耗 CPU、产生临时对象，还会影响安装包体积、代码优化规则和协议升级方式。问题通常表现为冷启动解析配置时在 Perfetto（Android 系统追踪工具）中出现较长区段、网络响应后频繁分配对象并触发 GC（Garbage Collection，垃圾回收）、Binder 调用两侧花时间编解码，或者字段只在经过 R8 缩减、优化与混淆的发布包中丢失。

选型要先确定数据边界：

- 进程内函数调用直接传对象，不需要序列化。
- 网络与持久化需要可演进、跨版本的格式，例如 JSON 或 Protocol Buffers。
- Android 组件参数、瞬时状态和跨进程调用使用 `Parcelable`、`Bundle` 或 AIDL（Android Interface Definition Language，Android 接口定义语言）支持的类型。
- 大型二进制内容应通过文件描述符、Content URI（由 ContentProvider 授权访问的数据地址）或分页接口传递，不应内嵌进一个 Binder 事务。

Binder 机制见 [1.9 Android IPC 全景与 Binder 性能](../../part1-fundamentals/ch01-architecture/09-ipc-binder-performance.md)，启动观测见 [21.1 App 启动路径、监控与度量](../ch21-startup/01-app-startup-path-monitoring.md)，网络协议设计见 [24.5 移动网络架构、连接与容灾](05-mobile-network-connection-resilience.md)。

### JSON（Gson / Moshi / kotlinx.serialization）性能对比

JSON 便于抓包、日志检查和跨语言协作。解析端仍要扫描括号、字段名、数字等词法单元，解码字符串、匹配字段并构造对象；若先建立 `JsonElement` 等表示完整 JSON 层级的树，再转换成业务对象，还会多分配一批节点对象。小响应的解析时间可能低于网络等待，大列表、配置恢复和启动预读则需要单独测量。

#### 三个库的当前边界

截至本轮复核，Gson 仍处于维护模式：项目会继续修复已有问题，但通常不再增加大型功能。其项目说明明确指出：Gson 以 Java 为主要目标，不支持 Kotlin 非空类型和默认参数等语言语义；它还会在运行时反射任意模型字段，这种开放式反射难以与 Android 发布包的缩减、优化和混淆配合，因此官方不再推荐用 Gson 处理 Android JSON。

存量项目不必仅因这段说明立即重写，但应限制允许反射的模型、用 `@SerializedName` 为字段声明稳定名称，并用经过 R8 处理的发布 APK 或 AAB 验证字段名、构造方式和泛型适配器。新 Kotlin 数据模型宜优先评估代码生成方案。

[Gson 项目说明](https://github.com/google/gson)

Moshi 同时支持 Java 和 Kotlin。Kotlin 类可以使用反射适配器，也可以通过 KSP（Kotlin Symbol Processing，Kotlin 符号处理）在编译期生成适配器；`@JsonClass(generateAdapter = true)` 会让 Moshi 选择生成代码。代码生成减少运行时反射依赖，并让 R8 规则更容易审计，但不保证在每种数据形状上都比其他库快。迁移 Gson 时还要逐项验证空值、默认值、枚举、时间格式和自定义适配器，不能因为方法名和用法看起来相近就直接替换。

[Moshi 项目说明](https://github.com/square/moshi)

`kotlinx.serialization` 通过 Kotlin 编译器插件为 `@Serializable` 类型生成序列化器，适合受控的 Kotlin 与 Kotlin Multiplatform 数据模型。截至 2026-08-15，官方格式列表中仍只有 JSON API 稳定；CBOR（二进制对象表示）、Protocol Buffers、HOCON（面向人工编辑的配置格式）和 Properties（键值配置）都是实验 API，调用接口可能继续变化。`kotlinx-serialization-protobuf` 也不同于由 `protoc`（Protocol Buffers 编译器）生成的 Java/Kotlin API，跨端协议采用它之前要单独验证二进制格式和升级规则。

[Kotlin 序列化格式状态](https://kotlinlang.org/docs/serialization.html)

#### 先验证语义，再比较速度

同一份 JSON 在不同库中未必得到相同对象。基准测试前要固定以下规则：

| 规则 | 需要验证的内容 |
| --- | --- |
| 未知字段 | 忽略、报警还是拒绝 |
| 缺失与 `null` | 是否使用默认值，非空字段如何失败 |
| 数字 | 整数范围、浮点特殊值、字符串数字是否接受 |
| 枚举 | 未知枚举值的处理 |
| 多态 | 类型判别字段、未知子类型与安全范围 |
| 字段名 | `@SerializedName`、`@Json`、`@SerialName` 是否完全对应 |
| 发布包 | R8 后生成代码、反射规则和自定义适配器是否仍可用 |

只有这些行为一致，速度结果才是在比较实现成本；若一个库忽略未知字段、另一个库直接失败，耗时差异也包含了语义差异。

应用场景可以按下面的顺序筛选：

| 场景 | 候选方案 | 工程判断 |
| --- | --- | --- |
| 新 Kotlin 模块，模型可加注解 | kotlinx.serialization JSON 或 Moshi KSP | 对比协议语义、构建插件、包体积与目标路径数据 |
| Java/Kotlin 混合 | Moshi 代码生成或经过约束的 Gson | Java 模型覆盖率与迁移回归成本更重要 |
| 存量 Gson | 保留并补发布包测试，按路径迁移 | 不把一次性全量替换当作性能优化 |
| 大响应，只读取少量字段 | 流式读取或拆分接口 | 避免构造完整 JSON 树和全部传输对象 |
| 客户端与服务端共同维护协议 | Protocol Buffers | 评估字段演进、运行库、压缩后大小和调试工具 |

这张表只用于缩小候选范围。项目仍要用相同数据、相同发布配置和相同设备验证结果。

#### 用可复现的基准测试比较

下面的设备端 Microbenchmark 只比较“同一字符串解码成同一对象”的稳态成本；稳态指代码完成预热后重复执行时的表现。两个数据类同时启用 kotlinx.serialization 和 Moshi 代码生成。固定输入样本（`test fixture`，下称测试样本）的结果校验放在计时循环之外，`BlackHole.consume()` 则让编译器和 R8 不能因为结果无人使用而删除被测代码。

```kotlin
@Serializable
@JsonClass(generateAdapter = true)
data class BenchmarkFeed(
    val items: List<BenchmarkItem> = emptyList()
)

@Serializable
@JsonClass(generateAdapter = true)
data class BenchmarkItem(
    val id: Long,
    val title: String,
    val tags: List<String> = emptyList()
)

@RunWith(AndroidJUnit4::class)
class FeedJsonBenchmark {
    @get:Rule
    val benchmarkRule = BenchmarkRule()

    private val fixture = InstrumentationRegistry.getInstrumentation()
        .context.assets.open("feed_payload.json")
        .bufferedReader()
        .use { it.readText() }

    private val kotlinxJson = Json {
        ignoreUnknownKeys = true
    }

    private val moshi = Moshi.Builder().build()
    private val moshiAdapter = moshi.adapter(BenchmarkFeed::class.java)

    @Before
    fun verifyFixture() {
        val kotlinxResult = kotlinxJson.decodeFromString<BenchmarkFeed>(fixture)
        val moshiResult = checkNotNull(moshiAdapter.fromJson(fixture))
        assertEquals(kotlinxResult, moshiResult)
    }

    @Test
    fun decodeWithKotlinxSerialization() = benchmarkRule.measureRepeated {
        val result = kotlinxJson.decodeFromString<BenchmarkFeed>(fixture)
        BlackHole.consume(result)
    }

    @Test
    fun decodeWithMoshiCodegen() = benchmarkRule.measureRepeated {
        val result = checkNotNull(moshiAdapter.fromJson(fixture))
        BlackHole.consume(result)
    }
}
```

这段测试没有测首次类加载、读取文件、网络等待或对象到业务模型的转换，也没有比较编码。它适合隔离解码函数，不代表启动或接口从输入到结果的完整耗时。项目还应分别建立编码用例、小型与大型测试样本、正常与缺字段样本；库配置必须与发布代码一致。

Jetpack Microbenchmark 会预热代码，记录执行时间和对象分配次数，并把明细写入 JSON 报告。使用 Benchmark 1.3.0-beta01 以上和 Android Gradle Plugin 8.4.0 以上版本时，`androidx.benchmark` 插件默认对基准测试 APK 做 AOT（Ahead-of-Time，运行前）完整编译；这不等于 R8 缩减与混淆。若要验证 R8 处理后的差异，库模块需使用 AGP 8.3 以上并单独启用测试最小化。

不要用可调试包或模拟器结果决定生产环境选型；首次使用成本和完整用户路径仍要由 Macrobenchmark（从应用外部测量启动、滚动等场景）与 Perfetto 系统追踪验证。

[Microbenchmark 概览](https://developer.android.com/topic/performance/benchmarking/microbenchmark-overview) · [编写 Microbenchmark](https://developer.android.com/topic/performance/benchmarking/microbenchmark-write) · [`BlackHole`](https://developer.android.com/reference/kotlin/androidx/benchmark/BlackHole)

### Protocol Buffers 与 FlatBuffers

Protocol Buffers 为每个字段分配唯一编号，并把编号写入二进制数据，再为各语言生成读写代码。它适合客户端、服务端和缓存格式由同一套协议定义管理的场景。是否比 JSON 更小、更快，仍取决于字段类型、字符串比例、压缩方式、运行库和访问方式；应比较生产网络实际压缩后的字节数与编解码全程的 CPU 时间，不能直接引用公开排名。

协议结构怎样升级比格式名称更重要。字段编号发布后不能改作其他含义；删除字段时应同时保留编号和名称，阻止后续复用。Proto3 解析二进制消息时会保存当前代码不认识的字段，并在重新编码同一消息时写回；转换成 JSON，或逐字段复制到新消息，都可能丢失这些未知字段。数字、布尔值、字符串等基本类型还要决定是否显式记录字段存在性（`presence`，即区分“没有提供”与“提供了默认值”）。

下面的 `.proto` 定义演示字段删除和存在性处理。`legacy_title` 与编号 4 都被保留；`subtitle` 使用 `optional`，使生成代码能够区分缺失和空字符串。

```proto
syntax = "proto3";

package feed.v1;

message FeedItem {
  reserved 4;
  reserved "legacy_title";

  int64 id = 1;
  string title = 2;
  optional string subtitle = 3;
  repeated string tags = 5;
}
```

这个片段只是二进制协议的一部分。发布检查还要让新旧客户端互相读写固定测试样本，验证未知字段、枚举、默认值和重新编码路径。Android 端可以评估 Protocol Buffers `lite` 精简运行库；官方生成代码文档说明，它更适合资源受限设备，但不提供描述符（运行时描述消息与字段的元数据）、嵌套 Builder 和反射能力。运行库与 `protoc` 编译器版本也要一起固定。

[Protocol Buffers 概览](https://protobuf.dev/overview/) · [Proto3 演进规则](https://protobuf.dev/programming-guides/proto3/#updating) · [Java lite 运行库](https://protobuf.dev/reference/java/java-generated/#runtime-library)

FlatBuffers 的目标是直接从序列化字节中读取字段，省去先解析或解包成完整对象的步骤。它适合结构稳定、读多写少、经常只访问局部字段的大型数据，例如离线索引或资源清单。它不会自动调用 `mmap`（把文件映射到进程虚拟地址空间）；应用要自行提供可访问的字节缓冲区，而内存映射仍可能因页面尚未载入而触发页错误和存储 I/O。生成访问器、构建器、协议结构升级、输入校验和调试工具都要一起评估。

[FlatBuffers 项目说明](https://github.com/google/flatbuffers)

选型时可用下面的比较维度：

| 维度 | JSON | Protocol Buffers | FlatBuffers |
| --- | --- | --- | --- |
| 人工检查 | 直接可读 | 需要 `.proto` 与解码工具 | 需要 `.fbs` 与工具 |
| 访问方式 | 解析为对象或流式读取 | 解析为生成消息 | 可从字节缓冲区按字段访问 |
| 演进约束 | 由字段名与应用规则管理 | 字段编号、字段存在性、未知字段 | 数据结构兼容规则与生成代码 |
| Android 代价 | 解析、字符串和对象分配 | 运行库、生成代码和消息分配 | 原生/Java 依赖包、构建器与缓冲区生命周期 |
| 适用判断 | 协议变化快、可读性重要 | 跨端稳定协议、高频编解码 | 大型稳定数据、局部读取 |

不要把现有 JSON 传输对象逐字段改写成 `.proto` 或 `.fbs` 后直接复用为界面对象。网络协议、持久化结构和界面状态的升级周期不同；在仓储层（连接数据来源与业务模型的边界）显式转换，才能明确由哪一层处理默认值和兼容逻辑。

### Parcelable 与 Serializable

`Parcel` 是 Android 为 IPC（Inter-Process Communication，进程间通信）设计的高效传输容器，不是通用序列化格式。Android 17 的 `Parcel.java` 明确禁止把 Parcel 数据写入持久化存储，因为底层实现变化可能让旧数据无法读取。磁盘缓存和网络协议不应在 Parcelable 与 Serializable 之间二选一，而应使用有版本规则的持久化格式。

在组件参数或跨进程接口中，优先使用 Android SDK 和 AIDL 直接支持的基础类型，或明确的 Parcelable。`writeParcelable()` 会同时写类名和数据；`writeTypedObject()`、`writeTypedList()` 等类型明确的 API 由读取方提供 `Parcelable.Creator`，不写对象类信息，因此更紧凑。AIDL 已知参数类型时会生成相应编解码代码，业务层不应再把对象包进 `Serializable` 或无类型的嵌套容器。

Android 17 的 `writeValue()` 在其他已支持类型都不匹配时才处理 `Serializable`，并注明通用 Java 序列化开销很大。它需要处理类描述和对象图（对象及其互相引用形成的结构），还会受类结构、`serialVersionUID`（Java 序列化版本标识）与混淆影响。已有低频接口可以在测量后保留，新接口不应只因 `implements Serializable` 写起来短就选择它。

下面的代码展示 `@Parcelize` 数据对象和一个调试期大小估算函数。`writeTypedObject()` 与读取端已知类型的场景一致；`Parcel.dataSize()` 给出本地编码后的字节数。

```kotlin
@Parcelize
data class UserCard(
    val id: Long,
    val name: String,
    val avatarUrl: String?
) : Parcelable

fun parcelSizeBytes(card: UserCard): Int {
    val parcel = Parcel.obtain()
    return try {
        parcel.writeTypedObject(card, 0)
        parcel.dataSize()
    } finally {
        parcel.recycle()
    }
}
```

这个数值只用于观察对象随数据增长的趋势。它不包括 Binder 命令元数据、标记 Binder 对象和文件描述符位置的偏移表、同一进程正在处理的其他事务或返回值，因此不能当作安全阈值。`@Parcelize` 也只生成读写代码，不提供持久化版本协议。使用 `@RawValue` 时，插件会改用 `Parcel.writeValue()`；高频 IPC 中要确认该属性在运行时进入哪一种类型分支。

[Android 17 `Parcel.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Parcel.java) · [Parcelize 文档](https://developer.android.com/kotlin/parcelize)

### 序列化在启动和 IPC 中的性能影响

#### 启动路径：区分稳态速度和首次使用成本

`Application.onCreate()`、初始化 `ContentProvider`、首屏配置恢复和接口返回后的批量对象构造，都可能影响 `TTID`（Time to Initial Display，从启动到初始画面显示）或 `TTFD`（Time to Full Display，从启动到应用报告内容已完整显示）。官方启动文档也把反序列化列为启动变慢时应检查的工作。处理顺序是：

- 只解析首帧或可交互状态需要的数据，其余数据延后或分页。
- 若只读取少量字段，使用流式读取或调整接口，不先构建完整 JSON 树。
- 复用应用级格式配置和 Moshi 适配器；Moshi 提供的适配器可以安全地供多个线程共用，自定义适配器也必须满足线程安全要求。
- 在真实冷启动中测首次类加载、生成序列化器初始化、磁盘读取、解析和业务模型转换。
- 若解析后的内容需要跨启动复用，把它写成有版本的数据库或文件格式，不能持久化 Parcel。

Microbenchmark 的预热与完整编译适合比较预热后的函数；Macrobenchmark 和 Perfetto 才能回答“这次解析是否延迟初始画面或可交互状态”。可以添加只包围解析调用的自定义追踪区段，再结合采样调用栈、对象分配与 GC，判断时间花在 JSON 扫描、对象构造还是业务转换。

[应用启动性能](https://developer.android.com/topic/performance/vitals/launch-time)

#### Android 17 Binder 缓冲区边界

“Binder 每笔事务有 1 MB”是不准确的。Android 17 的 `ProcessState.cpp` 把普通 `/dev/binder` 映射大小定义为 `1 MiB - 2 × 运行时页大小`；MiB 是二进制兆字节，1 MiB 等于 1,048,576 字节。`android17-6.18-2026-06_r6` 的 `binder_alloc.c` 允许的映射上限是 4 MiB，但实际缓冲区取用户空间请求值与该上限的较小者。Android 平台原生层请求约 1 MiB，所以 `TransactionTooLargeException` 文档将当前容量概括为 1 MB；在 16 KiB 内存页设备上，表达式还会扣除两个 16 KiB 页。

这块空间属于进程，并由该进程正在处理的 Binder 事务共享，不是某次调用的独占配额。单个参数看起来很小，也可能在并发调用、返回值和其他系统交互同时发生时失败。`TransactionTooLargeException` 不能指出失败发生在发送请求还是返回结果；重试会修改数据的调用前，必须采用幂等协议（同一请求重复执行不会产生重复副作用）或先查询提交状态。

`rememberSaveable` / `onSaveInstanceState()` 保存的状态也会经由系统进程参与 Binder 传输。Android 官方建议把这类状态控制在 50 KB 以下；这个数值只针对状态保存，不是所有 Binder 接口的通用上限。状态中应保存恢复界面所需的标识和少量输入，不保存列表、位图或完整接口响应。

[Android 17 `ProcessState.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/binder/ProcessState.cpp) · [6.18 内核 `binder_alloc.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/android/binder_alloc.c) · [Android 17 `TransactionTooLargeException.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/TransactionTooLargeException.java) · [Parcelable 与 Bundle 建议](https://developer.android.com/guide/components/activities/parcelables-and-bundles)

大型结果应改变接口形状：

- 列表使用稳定的续页标记分页，让下一次请求从已返回位置继续，避免重复传输已有数据。
- 大型二进制数据通过受权限保护的 Content URI，或 `ParcelFileDescriptor`（Android 对文件描述符的封装）读取。
- 进程间只传记录标识，让接收方通过明确的数据接口查询。
- 高频小调用可以在事务时长仍可控时合并成批，并验证 P95/P99 延迟（第 95/99 百分位耗时）与失败后能否安全重试。

### 建立序列化选型基线

公开基准测试只能用于发现候选项。应用自己的字段分布、字符串长度、R8 配置、依赖版本、设备 CPU 和协议压缩都会改变结果。至少建立四组可复现数据：

| 基线 | 记录内容 | 回答的问题 |
| --- | --- | --- |
| 编解码 Microbenchmark | 时间、分配次数、发布配置、设备与测试样本哈希（内容指纹） | 单个函数预热后的差异 |
| 冷启动 Macrobenchmark | `TTID`、`TTFD`、解析追踪区段、GC 与类加载 | 首次解析是否影响用户路径 |
| 网络或磁盘端到端测试 | 压缩前后字节数、读写时间、业务模型转换 | 格式变化是否降低从读取到业务对象的总耗时 |
| IPC 压力测试 | 本地 Parcel 估算、并发数、往返延迟、失败与重试 | 接口是否需要分页或外部数据通道 |

发布前还要运行协议兼容性回归测试：

- 当前解码器读取所有仍受支持的历史测试样本。
- 新旧编码器与解码器交叉验证，检查缺失字段、未知字段和默认值。
- 经过 R8 处理的发布 APK 或 AAB 执行相同测试，覆盖反射、生成代码和自定义适配器。
- 目标设备覆盖 Android 10 / API 29 与 Android 17 / API 37；包含 16 KiB 页设备时，额外观察 Binder 缓冲区与原生序列化库。
- 格式错误、体积过大或嵌套层级过深的输入能够受控失败，不把原始用户数据写入性能日志。

### 序列化小结

JSON 库先比较协议语义和发布包稳定性，再比较速度；Gson 存量代码可以渐进迁移，新 Kotlin 模型宜优先评估生成代码。Protocol Buffers 依赖严格的字段编号与兼容测试，FlatBuffers 的直接访问优势只在目标数据形状中成立。Parcelable 服务于 Android 瞬时传输，不能用于持久化；Android 17 的 Binder 容量还是进程共享资源。优化顺序应从减少数据、延迟非必要解析、分页和调整接口开始，换库必须由同一业务路径上的测量结果支持。

## 全文小结

数据库与序列化共同决定一次数据操作的等待、复制和兼容成本。先用事务、查询计划、投影和索引控制数据库实际读取的数据，再用符合协议生命周期的格式完成编码；不要用扩连接池、放大 `CursorWindow` 或单纯更换 JSON 库掩盖数据边界问题。

验收时应把首次打开、迁移、SQL、连接等待、编解码、对象分配和 IPC 分段记录。Room/SQLite 驱动、格式库和协议版本都独立于 Android API 级别，升级必须同时覆盖历史数据、发布包优化、跨版本读写与失败恢复。
