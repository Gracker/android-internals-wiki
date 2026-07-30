---
title: "SQLite/Room 数据库性能优化"
chapter: "10.7"
status: finalized
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1, AndroidX Room 2.8.4 sources, SQLite upstream WAL/locking/query-planner docs"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteDatabase.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteConnectionPool.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteSession.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteGlobal.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteCursor.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteQuery.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/CursorWindow.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/CursorToBulkCursorAdaptor.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/BulkCursorDescriptor.java"
  - type: aosp
    path: "frameworks/base/core/res/res/values/config.xml"
  - type: aosp
    path: "libs/androidfw/CursorWindow.cpp"
  - type: official
    path: "androidx.room:room-runtime:2.8.4 sources.jar (RoomDatabase / RoomConnectionManager / DatabaseConfiguration)"
  - type: official
    path: "androidx.room:room-paging:2.8.4 sources.jar (LimitOffsetPagingSource / RoomPagingUtil.kt)"
  - type: official
    path: "developer.android.com/training/data-storage/room"
  - type: official
    path: "developer.android.com/topic/libraries/architecture/paging/v3-paged-data"
  - type: official
    path: "developer.android.com/reference/android/database/sqlite/SQLiteDatabase"
  - type: official
    path: "sqlite.org/lockingv3.html"
  - type: official
    path: "sqlite.org/wal.html"
  - type: official
    path: "sqlite.org/walformat.html"
  - type: official
    path: "sqlite.org/eqp.html"
  - type: official
    path: "sqlite.org/withoutrowid.html"
  - type: official
    path: "perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention"
  - type: blog
    path: "intake/research-feeds/2026-04-05-07-cursorwindow-binder-performance.md"
  - type: blog
    path: "intake/research-feeds/2026-04-06-15-perfetto-monitor-contention-art-lock-analysis.md"
tags: [SQLite, Room, database, ANR, CursorWindow, WAL, performance]
related_chapters: ["1.10", "4.1", "9.1", "10.1", "10.6"]
section: "10.7"
task9_result: pass-tech-review
last_task9_at: "2026-06-29T20:26:01+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-29"
task9_review_notes: "2026-05-08 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 1；WAL autocheckpoint 默认值与 Room transaction executor 口径需回炉。 | 2026-05-08 Task9 14:32：needs-rework。P0 0 / P1 2 / P2 1；WAL checkpoint 线程口径与 Room transaction executor 口径仍需回炉。 | 2026-05-08 Task9 20:30：pass-tech-review。P0 0 / P1 0 / P2 0；WAL autocheckpoint、WAL sync mode、Room transaction executor 三处前轮回炉点已闭合；剩余 benchmark 待补充均已标为待验证，不构成发布阻塞。 自动晋升 finalized。 | 2026-06-06 Task9 闲时抽检：auto-fixed。P0 0 / P1 0 / P2 0；将 CursorWindow 默认大小的源码锚点从 AOSP main 改为 android-16.0.0_r1，符合 Android 17/API 37 以内边界，回到 Task6 复审。 | 2026-06-07 Task9 04: auto-fixed。P0/P1 0；将 AOSP 锚点从不可见 android-17-beta3 降为 android-16.0.0_r1，并修正 WAL autocheckpoint 页大小口径为 SQLite PRAGMA page_size / /data block size，回到 Task6 复审。 | 2026-06-07 Task9 05: pass-tech-review。P0/P1 0；前次 CursorWindow / WAL checkpoint auto-fix 已复核通过；记录 P2 1（EXPLAIN QUERY PLAN 示例输出建议收敛），Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-29 Task9 闲时抽检：auto-fixed。P0 0 / P1 1 / P2 0；android-17.0.0_r1 tag 已发布后复核 SQLite/CursorWindow/WAL 参数与 SQLiteOpenHelper 异步 API 边界，将章节主线源码锚点从 android-16.0.0_r1 升级为 android-17.0.0_r1，回到 Task6 复审。 | 2026-06-29 Task9 confirmation: pass-tech-review。P0 0 / P1 0 / P2 0；复核 ThreadLocal SQLiteSession、waitForConnection、CursorWindow 默认 2048KB、WAL autocheckpoint 100 页与 sync NORMAL；未发现新 P0/P1。 Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-06-29-20-deep-review.md。"

reviewed_date: "2026-06-29"
reviewed_by: "openclaw-task6"
task2b_state: fixed
task2b_result: fixed
task6_state: reviewed
task6_result: "pass-light-edit"
task9_state: reviewed
pipeline_stage: ready-to-publish
last_task2b_at: "2026-05-08T19:44:22"
task6_reviewed_date: "2026-06-29"
last_task6_at: "2026-06-29T20:15:13+08:00"
last_task6_review_log: "logs/review/2026-06-29-20-review.md"
last_task6_audit: "2026-07-16"
review_notes: "2026-05-08 task6 revisiting review: pass-light-edit。按写作规范修正禁用/填充词、结构性元叙述与中英文格式；无新增 B 类回炉问题。 | 2026-05-08 Task6 14:05：复审 Task2B 修复后的文稿，完成 frontmatter 去重、代码围栏语言标注与 L1/L2 小修；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-05-08 Task6 20:05：复审 Task2B 修复后的文稿，完成 L1/L2 轻量精修（重复句、用途句、口语化表达与结构性提示）；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-06-07 Task6 05:18：revisiting 复审 Task9 auto-fix 后文稿；L1/L2 全部通过，无禁用词命中，无 B 类回炉问题。auto-fix 涉及的源码锚点和口径修正写作质量合格。task9_result=auto-fixed，需 Task9 正式 pass-tech-review 后再晋升。 | 2026-06-29 Task6 复审（Task9 auto-fix 后）：pass-light-edit。L1/L2 全部通过；禁用词零命中；高频词在阈值内。Task9 auto-fix 涉及的源码锚点升级（android-16→17.0.0_r1）写作质量合格。无 B 类回炉项，送 Task9 确认。"
last_task9_review_log: "logs/deep-review/2026-06-29-20-deep-review.md"
last_task9_audit: "2026-06-29"
last_task9_autofix_at: "2026-06-29"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-06
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
---

# 10.7 SQLite/Room 数据库性能优化

数据库栈上的一次长等待，可能来自 SQL 扫描、事务占用写者、连接池排队、CursorWindow refill、跨进程 Binder 往返，或首次打开数据库时执行的 Migration。它们在 ANR trace 里经常挤在相邻的几层栈上，处理方式却各不相同。

排查时应同时回答四个问题：哪条线程发起访问，等待的是哪类资源，SQL 访问了多少数据，以及数据库打开与版本迁移发生在哪条路径。固定的“慢查询毫秒线”无法替代帧、输入事件和 ANR 时间线；同一条查询放在后台导入线程与主线程，风险等级完全不同。

<!-- outline-start -->
- 🔹 WAL 模式、锁层级与 `SQLiteDatabase` 同步机制
- 🔹 CursorWindow、跨进程 Cursor 与翻页重查
- 🔹 Room 的线程模型、事务与 Paging 3
- 🔹 索引、`WITHOUT ROWID` 与 PRAGMA 调优
- 🔹 数据库与 ANR / Perfetto 的关联分析
- 🔹 异步线程池、加密数据库与多进程访问
<!-- outline-end -->

## 1. SQLite 并发模型：先辨认等待的资源

### 1.1 回滚日志与 WAL 的差别

回滚日志模式在修改数据库页前保存旧页。写事务取得 `RESERVED` 锁后，其他连接仍可持有或取得 `SHARED` 读锁；提交阶段进入 `PENDING`、`EXCLUSIVE` 后，新的读者和其他写者才会受阻。把整个写事务描述成“数据库全程独占”会高估它对读者的影响。

WAL 模式把新页追加到 `-wal` 文件。读事务记录自己的 WAL end mark，并从主库与不超过该位置的 WAL frame 组成一致快照。写者可以在已有读者继续读取旧快照时追加 frame，但同一数据库仍只有一个 WAL 写者。长写事务会延长其他写者的等待，WAL 不会提供并行写入。

下面的查询用于确认当前连接看到的 journal mode：

```sql
PRAGMA journal_mode;
```

返回值才是当前模式；配置代码里曾经请求 `WAL`，不等于后续每个进程和连接都处于一致配置。Room 2.8.4 的 `RoomDatabase.JournalMode` 只定义 `TRUNCATE` 与 `WRITE_AHEAD_LOGGING`，Builder 默认值为 `WRITE_AHEAD_LOGGING`。旧版本 Room 曾采用过 `AUTOMATIC` 选择逻辑，阅读历史代码时应按对应版本判断。

WAL 依赖同一主机上的共享内存协调机制，不适合把数据库文件放在普通网络文件系统上。备份、复制或恢复时也要把 `-wal`、`-shm` 与主库的一致性纳入流程，不能在活跃事务期间只复制 `.db` 文件。

### 1.2 WAL checkpoint 不等同于数据库独占

checkpoint 把已提交 WAL frame 写回主库。`PASSIVE` checkpoint 可以与读者并行，它会推进到活跃读事务允许的位置，然后停止；持有较老 end mark 的长读事务会阻止更多 frame 被写回。后续写入仍可追加 WAL，结果可能是 WAL 长时间不缩小，这类现象通常称为 checkpoint starvation。

WAL 自己有写锁、checkpoint 锁和读标记等共享内存锁。常规 checkpoint 不能笼统描述为“取得主数据库 EXCLUSIVE 锁后执行”。切换 journal mode、恢复尾部或执行带截断语义的操作，所需锁与普通 `PASSIVE` checkpoint 不同。

下面的命令用于观测一次非阻塞 checkpoint 的进展：

```sql
PRAGMA wal_checkpoint(PASSIVE);
```

结果行包含 busy 状态、WAL frame 数和已 checkpoint frame 数。若后两者长期拉开，应同时检查长读事务、事务生命周期和 checkpoint 调用时机；只调小阈值可能增加写回频率，却不能越过活跃读者的 end mark。

### 1.3 Android 17 的 Session 与连接池

平台 `SQLiteDatabase` 为每条线程保存一个 `SQLiteSession`。Session 在需要执行语句时向 `SQLiteConnectionPool` 申请连接，池内的 `mLock` 保护池状态；无可用连接时，线程进入 `waitForConnection()` 的等待队列。

下面的摘录用于定位 Android 17 平台栈中的两个源码锚点：

```java
// SQLiteDatabase.java
private final ThreadLocal<SQLiteSession> mThreadSession = ThreadLocal
        .withInitial(this::createSession);

// SQLiteConnectionPool.java
public SQLiteConnection acquireConnection(String sql, int connectionFlags,
        CancellationSignal cancellationSignal) {
    SQLiteConnection con = waitForConnection(sql, connectionFlags, cancellationSignal);
    synchronized (mLock) {
        if (mIdleConnectionHandler != null) {
            mIdleConnectionHandler.connectionAcquired(con);
        }
    }
    return con;
}
```

这段代码说明了两类不同等待：Java monitor 竞争可能发生在维护池状态的短临界区，连接耗尽则会停在 `waitForConnection()`。WAL 打开后，平台池可提供非主连接服务只读工作；写事务仍需要主连接亲和性。连接数更多也无法增加 SQLite 的写者数量。

Room 2.8.4 另有自己的 `RoomConnectionManager`。该版本源码在 WAL 配置下把池上限映射为 4 个 reader、1 个 writer，在 `TRUNCATE` 下各为 1 个。这是当前 AndroidX 实现参数，应用代码不应依赖固定 reader 数；后续版本、驱动或平台配置都可能调整它。

`SQLiteOpenHelper.getWritableDatabase()` 与 `getReadableDatabase()` 仍是同步打开 API。`onCreate()`、`onUpgrade()`、`onDowngrade()` 和连接配置都属于 open 路径。Android 17 没有 `getWritableDatabaseAsync()`；应用若要避免启动线程受阻，需要在自己的协程或 executor 中触发首次打开，并明确失败、重试与就绪状态。

### 1.4 Android 17 与 Room 2.8.4 的默认值

下表中的值都有明确版本边界，不能当作所有 Android 版本和所有 SQLite 构建的统一常量。

| 项目 | Android 17 / Room 2.8.4 锚点 | 使用时的边界 |
|---|---|---|
| 平台 `CursorWindow` 默认容量 | `config_cursorWindowSize = 2048` KB | OEM 资源覆盖与显式构造参数可能改变容量 |
| 平台 WAL autocheckpoint | `db_wal_autocheckpoint = 100` 个数据库页 | SQLite 上游默认值是 1000 页；Android 资源覆盖了它 |
| 普通应用的 WAL sync mode | `db_wal_sync_mode = NORMAL` | system process 可由 `SQLiteGlobal` 选择 `FULL`；系统属性也可覆盖 |
| Room journal mode | `WRITE_AHEAD_LOGGING` | 这里指 Room 2.8.4 Builder 默认值 |
| Room WAL reader/writer 上限 | 4 / 1 | 属于当前 `RoomConnectionManager` 实现参数 |

数据库页大小要从数据库本身读取。下面的查询用于把 autocheckpoint 的“页数”换算成字节规模：

```sql
PRAGMA page_size;
PRAGMA wal_autocheckpoint;
```

两项相乘只能估算触发阈值对应的 frame 数据量，WAL 还有 header 与 frame header。Android 17 的 `SQLiteGlobal.getDefaultPageSize()` 以 `/data` 文件系统 block size 为新库默认值，并允许 `debug.sqlite.pagesize` 覆盖；已有数据库仍以文件头中的 page size 为准。Linux 内存页、文件系统 block 和 SQLite 数据库页是三个概念。

`synchronous=NORMAL` 在 WAL 模式下维持数据库一致性。进程崩溃通常不会让已提交事务消失；掉电或硬重启发生在同步窗口内时，最近提交的事务可能回滚。需要掉电后也保留每次提交的业务，应评估 `FULL` 的写入代价，并用目标设备与目标存储条件验证。

## 2. CursorWindow 与跨进程 Cursor

### 2.1 Window 只保存结果片段

`SQLiteCursor` 不要求把全部结果同时放进内存。目标行超出当前窗口覆盖范围时，`SQLiteCursor.onMove()` 调用 `fillWindow()`，继续进入 `SQLiteQuery.fillWindow()` 与 `SQLiteSession.executeForCursorWindow()`。因此，大结果集可能表现为多次填充和多次 SQL 步进，不一定在第一次 `query()` 时付清全部成本。

Android 17 的默认窗口大小来自系统资源。下面的源码摘录用于确认 2048 KB 的来源：

```java
private static int getCursorWindowSize() {
    if (sCursorWindowSize < 0) {
        sCursorWindowSize = Resources.getSystem().getInteger(
                com.android.internal.R.integer.config_cursorWindowSize) * 1024;
    }
    return sCursorWindowSize;
}
```

这里是默认容量，不是单行允许无限增长的保证。单行各列放不进当前窗口时，缩短结果集行数没有帮助；需要减少该行的文本、BLOB 或 projection 宽度。

### 2.2 跨进程返回路径

ContentProvider 跨进程查询通过 `BulkCursorDescriptor` 和 `IBulkCursor` 暴露窗口。Provider 侧的 `CursorToBulkCursorAdaptor.getWindow(position)` 先检查现有窗口是否覆盖目标位置，缺失时调用 Cursor 的 `fillWindow()`。

Android 17 的 native `CursorWindow::writeToParcel()` 有两条传输路径：

- window 由 ashmem 支持时，Parcel 写入复制后的文件描述符；
- 没有 ashmem FD 时，native 层按已使用容量压缩数据并写入 Parcel。

因此，`CursorWindow` 与 Binder 大小问题不能只用一句“窗口通过共享内存传输”概括。要根据异常、窗口创建方式和调用路径辨认数据走了 FD 还是内联 Parcel。

常见故障可分为三组：

- **单行过宽或窗口分配失败**：常见于大文本、大 BLOB、列数过多，异常靠近 CursorWindow 填充或分配。
- **refill 频繁**：窗口能够创建，但滚动或随机定位不断跨越窗口边界，跨进程场景还会增加 Binder 往返。
- **`TransactionTooLargeException`**：Binder 事务的内联数据、extras、Bundle 或并发事务总占用过高；它不自动等价于 2 MB CursorWindow 溢出。

工程上的优先动作通常是缩小 projection、把大对象从列表查询移出、关闭不再使用的 Cursor、给可取消查询传递 `CancellationSignal`，再根据 trace 评估窗口 refill。盲目放大 CursorWindow 会增加进程内存和跨进程资源占用，也不能修复单行结构设计。

### 2.3 Room Paging 3 仍可能使用 OFFSET

Room 2.8.4 的 `LimitOffsetPagingSource` 会计算总数，并由 `RoomPagingUtil.kt` 包装 DAO 原查询。生成的分页形态如下：

```sql
SELECT * FROM (
    SELECT id, conversation_id, created_at, preview
    FROM message
    WHERE conversation_id = :conversationId
    ORDER BY created_at DESC, id DESC
)
LIMIT :limit OFFSET :offset;
```

Paging 负责 load、refresh、预取和失效通知，深页的 OFFSET 跳过成本仍由 SQLite 承受。projection 里的列也会进入 CursorWindow；在列表阶段读取正文或 BLOB，会同时放大 SQL、对象构造和窗口压力。

长列表若具备稳定排序键，可以由 DAO 提供 keyset 查询。下面的查询用 `(created_at, id)` 处理时间相同的记录：

```sql
SELECT id, conversation_id, created_at, preview
FROM message
WHERE conversation_id = :conversationId
  AND (
      created_at < :cursorCreatedAt
      OR (created_at = :cursorCreatedAt AND id < :cursorId)
  )
ORDER BY created_at DESC, id DESC
LIMIT :limit;
```

对应索引应以 `conversation_id, created_at, id` 的顺序服务过滤与排序。Keyset 不支持用页码随机跳到任意位置，刷新和锚点恢复也要由业务定义；这是一项数据接口选择，不能只替换一行 SQL。

## 3. Room 2.8.4：API 形态决定执行路径

### 3.1 同步、挂起与观察查询

Room 的主线程保护会拒绝同步 DAO 在主线程访问数据库，除非 Builder 显式调用 `allowMainThreadQueries()`。该开关只移除检查，不会提供调度，也不会缩短 SQL、open 或 Migration。

Room 2.8.4 的执行模型已经转向 coroutine context 与 reader/writer connection API：

- 同步 DAO 在调用线程执行，并遵守主线程访问检查；
- `suspend` DAO 在 Room 配置的查询协程上下文中申请 reader 或 writer connection；
- `Flow` 收集后执行查询，表失效时触发重查；
- `useReaderConnection()` 与 `useWriterConnection()` 是当前公开的显式连接入口；
- `@Transaction` 或 transaction API 在 writer connection 上维护事务范围。

旧文档里的 query executor、transaction executor 适用于相应历史版本和 Android 专用实现。检查现代 Room 代码时，应以当前依赖的生成代码、`DatabaseConfiguration` 和 sources.jar 为准，避免把旧 executor 结论套到 2.8.4。

### 3.2 批量写入要减少事务边界

逐条调用独立 DAO 写方法，会反复进入写事务、更新索引并提交 WAL。Room 支持集合参数，优先让生成代码在一个调用中处理批量数据；涉及“删旧数据再写新数据”时，再用事务保证中间状态不对外可见。

下面的 DAO 用一个事务更新某天的缓存：

```kotlin
@Dao
interface EventDao {
    @Query("DELETE FROM event WHERE day = :day")
    suspend fun deleteDay(day: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(rows: List<EventEntity>)

    @Transaction
    suspend fun replaceDay(day: String, rows: List<EventEntity>) {
        deleteDay(day)
        insertAll(rows)
    }
}
```

这里的收益来自更少的事务边界和一致的可见状态。耗时改善幅度受索引数量、触发器、行宽、存储设备、sync mode 与批次大小影响，应以 Benchmark 或生产 trace 记录为准。单个超大事务也会长时间占用 writer，并扩大回滚或 checkpoint 工作量，批次上限要通过测量确定。

事务体内不要等待网络、锁住与数据库无关的共享对象，或执行耗时未知的回调。协程挂起不会自动释放 SQLite 事务；只要事务范围尚未退出，writer connection 仍可能被占用。

### 3.3 首次打开与 Migration

`Room.databaseBuilder(...).build()` 创建数据库对象，首次读写才常会触发底层打开。Migration、schema 校验、回调和索引创建都可能落在这次访问的线程链上。启动页第一次收集 `Flow`、ContentProvider 初始化或同步 DAO 调用，都可能成为 first open 的入口。

可控的做法是在后台启动阶段主动打开，并把“数据库尚未就绪”当作状态处理。下面的代码只展示调度边界：

```kotlin
class DatabaseWarmup(
    private val database: AppDatabase,
    private val appScope: CoroutineScope,
) {
    fun start() {
        appScope.launch(Dispatchers.IO) {
            database.openHelper.writableDatabase
        }
    }
}
```

这段预热仍会执行全部 Migration，异常也必须由应用记录和处理。预热时间不能靠猜测；应准备接近线上体量的旧版本数据库，在目标设备上测量每条迁移，并验证中断后的重开、磁盘空间不足和 schema 校验失败。

Migration 中的表重建、数据回填和 `CREATE INDEX` 可能放大 WAL 与临时空间。采用分阶段迁移时，要保证每个已发布 schema 版本都有明确迁移路径；为了启动速度直接启用 destructive migration 会丢数据，只适合数据能够可靠重建且产品已经接受该行为的库。

## 4. SQL、索引与 PRAGMA

### 4.1 索引设计来自访问模式

复合索引遵循左侧列约束。等值过滤列通常放在范围或排序列前面；一旦前缀出现未约束列或范围条件，后续列能否继续用于查找和排序要看具体查询计划。

下面的索引服务“按会话过滤，并按时间与 ID 倒序分页”：

```sql
CREATE INDEX idx_message_conversation_time
ON message(conversation_id, created_at DESC, id DESC);
```

该索引适合上一节的列表查询。若 projection 只包含索引列，SQLite 还有机会使用 covering index，减少回表；查询正文时仍需访问表数据。每个额外索引都会增加插入、更新、删除和存储成本，低选择性单列索引也可能不被 planner 采用。

### 4.2 用目标数据库运行 EXPLAIN QUERY PLAN

查询计划受 SQLite 版本、统计信息、绑定值形态、索引和数据分布影响。文章里的模拟输出无法证明线上数据库会选择同一计划。

下面的命令用于检查一条确定 SQL 的 planner 结果：

```sql
ANALYZE;

EXPLAIN QUERY PLAN
SELECT id, created_at, preview
FROM message
WHERE conversation_id = 42
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

读取 `detail` 列时，关注 `SCAN`、`SEARCH`、`USING COVERING INDEX` 与 `USE TEMP B-TREE`。`SCAN` 不一定有错，小表顺序扫描可能更便宜；`SEARCH ... USING INDEX` 也不保证快，索引返回大量行后仍会产生回表和对象构造成本。应把计划与返回行数、实际耗时和 I/O trace 放在一起判断。

数据库持续变化时要维护统计信息。SQLite 的 `PRAGMA optimize` 可在合适的生命周期点按当前版本建议运行；不要在每次查询前调用 `ANALYZE`。

### 4.3 `WITHOUT ROWID` 的适用范围

普通 rowid 表若声明 `INTEGER PRIMARY KEY`，该列就是 rowid 的别名，主键查找已经很直接。`WITHOUT ROWID` 更适合非整数主键或复合主键，并且主键列较短、按主键访问频繁的表；它把主键 B-tree 同时作为表存储，可能省去普通表“主键索引定位 rowid，再访问表 B-tree”的一次查找。

下面的定义适合用实验比较复合主键映射表：

```sql
CREATE TABLE account_permission (
    account_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    granted_at INTEGER NOT NULL,
    PRIMARY KEY (account_id, permission_id)
) WITHOUT ROWID;
```

`WITHOUT ROWID` 不支持 `AUTOINCREMENT`，`last_insert_rowid()` 对它没有常规主键语义，incremental BLOB I/O 也不可用。大主键会复制到二级索引中，可能增加空间。迁移现有表前要用真实数据比较库大小、读写耗时和所需 API。

### 4.4 PRAGMA 是连接状态与持久状态的混合体

以下项目适合观测和实验，不存在适用于所有应用的推荐数值：

| PRAGMA | 用途 | 风险与边界 |
|---|---|---|
| `journal_mode` | 选择回滚日志或 WAL | journal mode 需要同一数据库的各实例保持一致；切换时可能受活跃连接影响 |
| `synchronous` | 调整提交的同步保证 | `NORMAL` 与 `FULL` 的差异涉及掉电耐久性，不能只按速度选 |
| `wal_autocheckpoint` | 设定自动 checkpoint frame 阈值 | 值太小会增加写回频率，值太大可能拉长 WAL 扫描和恢复 |
| `busy_timeout` | SQLite 锁冲突时等待一段时间 | 这是每连接状态；长超时会把失败改成更长等待，无法消除锁竞争 |
| `cache_size` | 调整每连接 page cache 的建议上限 | 负值以 KiB 表示；多连接会分别占用缓存，增加值会推高内存 |
| `page_size` | 读取或设置数据库页大小 | 既有库的变更受 journal mode、`VACUUM` 和 SQLite 版本规则约束 |

Room 或平台连接池会创建多个 SQLite connection。只在某个临时连接执行 per-connection PRAGMA，不能保证其他池连接继承。要通过 Room 驱动、open callback 或受支持的 Builder 配置统一设置，并在每个连接上验证；直接修改内部连接也可能与 Room 的配置流程冲突。

## 5. 从 ANR 与 Perfetto 还原等待链

### 5.1 常见栈只说明“停在哪里”

数据库相关 ANR 常见以下停点：

- 主线程直接进入生成 DAO、`SQLiteQuery.fillWindow()` 或 `executeForCursorWindow()`；
- 线程停在 `SQLiteConnectionPool.waitForConnection()`，等待池连接；
- 客户端停在 `ContentResolver.query()` 的 Binder reply，Provider 进程仍在执行 SQL；
- writer 遇到 `SQLITE_BUSY` 或 `SQLITE_LOCKED`，等待另一连接或进程释放锁；
- Cursor 移动触发 refill，Provider 侧重新填充窗口。

单看客户端主线程的 Binder 栈，无法判断远端进程在等连接、跑 Migration，还是执行无索引查询。分析 ANR 时要同时取客户端和 Provider 进程的 trace，并按同一时间段对齐 Binder transaction、线程调度和数据库 slice。

`waitForConnection()` 也不自动等于连接池太小。常见上游原因包括长事务、未关闭资源、慢 reader 占住连接、writer 队列积压，以及首次 open 尚未结束。扩池可能把更多查询送入存储层，同时增加 page cache 与调度竞争。

### 5.2 StrictMode 提前暴露主线程磁盘访问

下面的 Debug 配置用于记录主线程磁盘读写：

```kotlin
if (BuildConfig.DEBUG) {
    StrictMode.setThreadPolicy(
        StrictMode.ThreadPolicy.Builder()
            .detectDiskReads()
            .detectDiskWrites()
            .penaltyLog()
            .build()
    )
}
```

它会报告数据库之外的磁盘 I/O，也不能发现所有“主线程等待后台数据库”的间接路径。把 violation 栈映射到 first open、DAO 类型和调用生命周期，才有可执行的修复方向。`penaltyDeath()` 适合专门的测试构建，不宜未经评估放进日常开发或发布包。

### 5.3 Perfetto：Java monitor 只是其中一层

下面的 Trace Processor 查询用于列出进程内持续时间较长的 Java monitor 竞争：

```sql
INCLUDE PERFETTO MODULE android.monitor_contention;

SELECT
  process_name,
  blocked_thread_name,
  blocking_thread_name,
  short_blocked_method,
  short_blocking_method,
  dur / 1e6 AS wait_ms
FROM android_monitor_contention
ORDER BY dur DESC
LIMIT 50;
```

`android_monitor_contention` 解释 Java monitor 的 owner 与 waiter，不覆盖 SQLite 文件锁、WAL 共享内存锁或连接池中的 `LockSupport.parkNanos()`。查询没有结果时，仍需查看线程状态、`sched`、Binder slice、Provider 进程、I/O 和 SQLite/Room 自定义 trace。

一条可复用的定位顺序是：

1. 按时间线确认 UI 线程等待区间，记录进入数据库或 Binder 的最上层业务调用。
2. 若主线程直接执行 SQL，检查查询计划、返回行数、projection 与 first open。
3. 若停在连接池，寻找持有 reader/writer connection 的线程和事务起止。
4. 若停在 Binder，转到 Provider 进程，继续追踪同一 transaction。
5. 对照 WAL 大小、checkpoint 进展、磁盘 I/O 与长读事务，判断等待是否来自写入和维护工作。

每一步都要留下可复查证据：trace 时间戳、SQL、查询计划、数据库版本、journal mode、page size 和测试数据规模。仅记录“数据库慢”无法支持回归验证。

## 6. 调度、多进程与加密数据库

### 6.1 写入队列解决顺序与背压

SQLite 只有一个 writer。应用可以用单一写队列建立业务顺序、限制待处理任务数量，并在队列过长时合并或丢弃可替代更新。这个队列是业务并发策略，Room 的一个 writer connection 只保证数据库写互斥，不负责业务优先级、幂等和背压。

读并发也应受控。多个 reader 能提高独立短查询的吞吐，但大扫描会竞争 CPU、I/O、page cache 和对象分配。查询协程上下文的并发度应以目标设备上的吞吐、尾延迟和内存一起评估。

`busy_timeout` 只能改变 SQLite 锁冲突时的等待策略。它不会取消超时后的业务重试，也不会保证公平；把数秒等待放在 Binder 或 UI 路径上，可能把快速失败变成长卡顿。优先缩短写事务、统一写入口并记录冲突来源。

### 6.2 多进程失效通知不负责写互斥

多个进程打开同一数据库文件时，journal mode、schema 版本和连接配置必须一致。SQLite 文件锁与 WAL 协调单写者，Room 的多实例 invalidation 机制只通知其他实例哪些表已经变化，以便观察查询重查。失效通知不提供分布式事务，也不会修复跨进程写冲突。

多进程设计可从下面几项约束开始：

- 选定一个进程负责高频写入，其他进程通过稳定 IPC 接口提交批次；
- Provider 的批量接口要定义事务范围、失败语义和调用超时；
- 进程被杀后重连时重新确认数据库版本与观察订阅；
- 备份、恢复、清库和 Migration 由一个明确的 owner 协调；
- Perfetto 同时采集各进程，锁等待要追到持锁进程。

如果多进程只为隔离一项后台任务，引入共享数据库前应比较“独立数据库 + 消息同步”的复杂度。共享文件减少数据复制，同时增加打开、迁移、锁与进程死亡恢复的协调工作。

### 6.3 SQLCipher 的成本必须在项目配置上测量

SQLCipher 在页读写、数据库打开和密钥派生路径增加密码学工作。成本受 SQLCipher 版本、cipher page size、KDF 参数、硬件、查询工作集、page cache 和索引影响，不能使用固定百分比描述。

评估时至少覆盖冷打开、热查询、批量事务、checkpoint、Migration 和低端设备，并记录 SQLCipher 与明文 SQLite 的完整配置。列级加密与全库加密提供的泄露边界不同，不能只凭性能选择；Android Keystore 适合保护密钥材料，它本身不提供 SQLite 页级透明加密。

## 7. 发布前检查表

- 主线程、Binder 调用线程和 Provider 线程的数据库访问都已列出。
- first open、Migration、schema 校验和索引创建已有独立测量。
- journal mode、`synchronous`、page size、autocheckpoint 来自运行时查询。
- 长事务不包含网络请求、未知回调或与数据库无关的锁等待。
- 批量写入使用受控事务，批次大小由设备测试确定。
- 列表 projection 排除了正文和 BLOB，CursorWindow refill 次数可从 trace 解释。
- Paging SQL 已确认属于 OFFSET 或 keyset，并有匹配的复合索引。
- `EXPLAIN QUERY PLAN` 在接近线上体量的数据库上运行，输出与耗时共同保存。
- 多进程 invalidation、SQLite 锁和业务写入顺序没有混为同一种机制。
- 调整 PRAGMA 后，所有池连接的值和掉电耐久性要求都已复核。

## 参考资料

- [Android 17 `SQLiteDatabase.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabase.java)
- [Android 17 `SQLiteConnectionPool.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnectionPool.java)
- [Android 17 `SQLiteGlobal.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteGlobal.java)
- [Android 17 `CursorWindow.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/CursorWindow.java)
- [Android 17 `CursorWindow.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/androidfw/CursorWindow.cpp)
- [Android 17 SQLite 资源默认值](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/config.xml)
- [Room 版本说明](https://developer.android.com/jetpack/androidx/releases/room)
- [Paging 3 分页数据](https://developer.android.com/topic/libraries/architecture/paging/v3-paged-data)
- [SQLite WAL](https://www.sqlite.org/wal.html)
- [SQLite WAL 锁格式](https://www.sqlite.org/walformat.html)
- [SQLite v3 文件锁](https://www.sqlite.org/lockingv3.html)
- [SQLite EXPLAIN QUERY PLAN](https://www.sqlite.org/eqp.html)
- [SQLite WITHOUT ROWID](https://www.sqlite.org/withoutrowid.html)
- [Perfetto `android.monitor_contention`](https://perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention)
