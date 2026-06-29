---
title: "SQLite/Room 数据库性能优化"
chapter: "10.7"
status: ready-for-review
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-29"
last_verified_against: "AOSP android-17.0.0_r1, AndroidX Room 2.8.4 sources"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteDatabase.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteConnectionPool.java"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteSession.java"
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
    path: "androidx.room:room-runtime:2.8.4 sources.jar (RoomDatabase / DatabaseConfiguration)"
  - type: official
    path: "androidx.room:room-paging:2.8.4 sources.jar (LimitOffsetPagingSource / RoomPagingUtil.kt)"
  - type: official
    path: "developer.android.com/training/data-storage/room"
  - type: official
    path: "developer.android.com/topic/libraries/architecture/paging/v3-paged-data"
  - type: official
    path: "developer.android.com/reference/android/database/sqlite/SQLiteDatabase"
  - type: official
    path: "perfetto.dev/docs/analysis/stdlib-docs#androidmonitor_contention"
  - type: blog
    path: "intake/research-feeds/2026-04-05-07-cursorwindow-binder-performance.md"
  - type: blog
    path: "intake/research-feeds/2026-04-06-15-perfetto-monitor-contention-art-lock-analysis.md"
tags: [SQLite, Room, database, ANR, CursorWindow, WAL, performance]
related_chapters: ["1.10", "4.1", "9.1", "10.1", "10.6"]
section: "10.7"
task9_result: auto-fixed
last_task9_at: "2026-06-29T13:27:23+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-29"
task9_review_notes: "2026-05-08 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 1；WAL autocheckpoint 默认值与 Room transaction executor 口径需回炉。 | 2026-05-08 Task9 14:32：needs-rework。P0 0 / P1 2 / P2 1；WAL checkpoint 线程口径与 Room transaction executor 口径仍需回炉。 | 2026-05-08 Task9 20:30：pass-tech-review。P0 0 / P1 0 / P2 0；WAL autocheckpoint、WAL sync mode、Room transaction executor 三处前轮回炉点已闭合；剩余 benchmark 待补充均已标为待验证，不构成发布阻塞。 自动晋升 finalized。 | 2026-06-06 Task9 闲时抽检：auto-fixed。P0 0 / P1 0 / P2 0；将 CursorWindow 默认大小的源码锚点从 AOSP main 改为 android-16.0.0_r1，符合 Android 17/API 37 以内边界，回到 Task6 复审。 | 2026-06-07 Task9 04: auto-fixed。P0/P1 0；将 AOSP 锚点从不可见 android-17-beta3 降为 android-16.0.0_r1，并修正 WAL autocheckpoint 页大小口径为 SQLite PRAGMA page_size / /data block size，回到 Task6 复审。 | 2026-06-07 Task9 05: pass-tech-review。P0/P1 0；前次 CursorWindow / WAL checkpoint auto-fix 已复核通过；记录 P2 1（EXPLAIN QUERY PLAN 示例输出建议收敛），Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-29 Task9 闲时抽检：auto-fixed。P0 0 / P1 1 / P2 0；android-17.0.0_r1 tag 已发布后复核 SQLite/CursorWindow/WAL 参数与 SQLiteOpenHelper 异步 API 边界，将章节主线源码锚点从 android-16.0.0_r1 升级为 android-17.0.0_r1，回到 Task6 复审。"

reviewed_date: "2026-06-29"
reviewed_by: "openclaw-task6"
task2b_state: fixed
task2b_result: fixed
task6_state: "reviewed"
task6_result: "pass-light-edit"
task9_state: "pending"
pipeline_stage: "task9_pending"
last_task2b_at: "2026-05-08T19:44:22"
task6_reviewed_date: "2026-06-29"
last_task6_at: "2026-06-29T20:15:13+08:00"
last_task6_review_log: "logs/review/2026-06-29-20-review.md"
last_task6_audit: "2026-05-26"
review_notes: "2026-05-08 task6 revisiting review: pass-light-edit。按写作规范修正禁用/填充词、结构性元叙述与中英文格式；无新增 B 类回炉问题。 | 2026-05-08 Task6 14:05：复审 Task2B 修复后的文稿，完成 frontmatter 去重、代码围栏语言标注与 L1/L2 小修；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-05-08 Task6 20:05：复审 Task2B 修复后的文稿，完成 L1/L2 轻量精修（重复句、用途句、口语化表达与结构性提示）；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-06-07 Task6 05:18：revisiting 复审 Task9 auto-fix 后文稿；L1/L2 全部通过，无禁用词命中，无 B 类回炉问题。auto-fix 涉及的源码锚点和口径修正写作质量合格。task9_result=auto-fixed，需 Task9 正式 pass-tech-review 后再晋升。 | 2026-06-29 Task6 复审（Task9 auto-fix 后）：pass-light-edit。L1/L2 全部通过；禁用词零命中；高频词在阈值内。Task9 auto-fix 涉及的源码锚点升级（android-16→17.0.0_r1）写作质量合格。无 B 类回炉项，送 Task9 确认。"
last_task9_review_log: logs/deep-review/2026-06-29-13-audit.md
last_task9_audit: "2026-06-29"
last_task9_autofix_at: "2026-06-29"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-28
---

# 10.7 SQLite/Room 数据库性能优化

在分析 ANR 和卡顿问题时，我们经常看到线程停在数据库路径上。一个耗时 200ms 的查询，如果发生在主线程，就是一次用户可感知的卡顿；如果它又把其他线程带到同一条数据库等待路径，ANR traces 和 Perfetto 里就会出现一串线程一起等待连接、事务或远端 Provider 回复。

数据库操作之所以容易成为性能瓶颈，根源在于 SQLite 的并发模型和 Android 在其上叠加的 connection pool。SQLite 在同一时刻只允许一个写者，Android 侧再用 `SQLiteSession`、`SQLiteConnectionPool` 和 helper open 流程把查询、事务、Migration 组织起来。把这几层分清楚，才能判断慢点究竟出在 SQL、本地窗口 refill、跨进程 Cursor 传输，还是连接池争用。

数据库性能问题可以沿着四层看：SQLite 并发模型、CursorWindow 跨进程传输、Room 线程模型，以及最终在 ANR / Perfetto 里的表现。

<!-- outline-start -->
- 🔹 WAL 模式、锁层级与 `SQLiteDatabase` 同步机制
- 🔹 CursorWindow、跨进程 Cursor 与翻页重查
- 🔹 Room 的线程模型、事务与 Paging 3
- 🔹 索引、`WITHOUT ROWID` 与 PRAGMA 调优
- 🔹 数据库与 ANR / Perfetto 的关联分析
- 🔹 异步线程池、加密数据库与多进程访问
<!-- outline-end -->

## 1. SQLite 内部机制与并发模型

### 1.1 WAL 模式 vs 回滚日志模式

SQLite 默认使用回滚日志（rollback journal）模式：每次写操作前先把将被修改的数据页复制到独立的回滚日志文件，再写入新数据。这个模式的代价很直接：**写操作期间数据库整体被锁定，读写互相阻塞**。

WAL（Write-Ahead Logging）模式反转了这个模型。写操作不再直接修改数据库文件，而是将变更追加到一个独立的 WAL 文件（`.db-wal`）中。读操作可以从数据库文件和 WAL 文件中同时读取，但看到的是各自一致的快照。这样，一个写者可以持续追加变更，多个读者也能同时读取，读写不再互斥。

启用 WAL 通常通过这条 PRAGMA 完成：

```sql
-- 启用 WAL 模式
PRAGMA journal_mode=WAL;
```

WAL 的收益来自两条底层改进。

其一，事务提交路径里的 `fsync()` 次数通常更少。回滚日志模式先回写原页再提交事务，WAL 把改动追加到 `-wal` 文件，检查点再把脏页并回主库。具体收益受文件系统、闪存控制器、检查点策略和事务大小影响，不宜用固定倍数概括。

其二，WAL 把大部分写入变成 append-only I/O。它少了一次“先复制旧页再覆盖新页”的往返，对频繁小事务和批量写入都更友好。Room 在默认 `JournalMode.AUTOMATIC` 配置下，通常也会优先选择 WAL；最终行为仍然取决于 API 级别、低内存设备判定和具体打开配置。

WAL 有三条边界要记住：同一时刻仍然只有一个活跃写者（写操作串行），WAL 文件不及时做检查点可能无限增长，以及不适用于网络文件系统（需要共享内存）。

### 1.2 SQLite 的锁层级

SQLite 使用五级锁模型，从松到紧依次为：

- **UNLOCKED**：数据库未被访问
- **SHARED**：读操作持有，多个读者可以同时处于 SHARED 状态
- **RESERVED**：写操作的准备阶段，此时仍然允许其他读者进入 SHARED 状态
- **PENDING**：写操作等待所有现有读者退出，不再接受新的读者
- **EXCLUSIVE**：写操作独占数据库，所有其他访问被阻塞

在回滚日志模式下，写操作会从 RESERVED → PENDING → EXCLUSIVE 逐步升级锁。在 PENDING 状态时，已经持有 SHARED 锁的读者可以继续读取，但新的读请求会被阻塞。这是回滚日志模式下读写互斥的根源——一个长事务持有 EXCLUSIVE 锁时，所有其他访问都必须等待。

WAL 模式改善了这个问题。写操作在 RESERVED 状态后直接写入 WAL 文件，不需要升级到 EXCLUSIVE。读操作通过读取 WAL 文件的快照，与写操作并行。只有检查点（checkpoint）操作才需要短暂获取 EXCLUSIVE 锁。

### 1.3 Android SQLiteDatabase 的同步机制

当前 AOSP 用的是“每个线程拿自己的 `SQLiteSession`，再向 `SQLiteConnectionPool` 申请连接”这套模型。执行 SQL 时并不存在一个覆盖所有查询的 Java 全局锁，`SQLiteDatabase` 里维护的是 `ThreadLocal<SQLiteSession>`，事务、`prepare()` 和 `executeForCursorWindow()` 最终都沿着这条路径往下走。

```java
// frameworks/base/core/java/android/database/sqlite/SQLiteDatabase.java
private final ThreadLocal<SQLiteSession> mThreadSession = ThreadLocal
        .withInitial(this::createSession);

// frameworks/base/core/java/android/database/sqlite/SQLiteConnectionPool.java
public SQLiteConnection acquireConnection(String sql, int connectionFlags,
        CancellationSignal cancellationSignal) {
    SQLiteConnection con = waitForConnection(sql, connectionFlags, cancellationSignal);
    synchronized (mLock) {
        ...
    }
    return con;
}
```

要分清两个层次。`mLock` 保护的是连接池元数据，让线程进入等待的位置是 `waitForConnection()`；长事务、独占写连接或连接池规模过小，都会让后续线程在这里排队。Perfetto 和 ANR trace 里更值得找的是 `beginTransaction`、`executeForCursorWindow()`、`waitForConnection()` 这条链。

`SQLiteOpenHelper` 的数据库打开路径仍然是串行的。`getWritableDatabase()` 会把 `onCreate()`、`onUpgrade()`、`onDowngrade()` 串在一次 open 流程里，所以慢 Migration 一样会把后续打开者挡在门外。这里的阻塞点更接近 helper open 和 connection acquisition。

Android 17（API 37）没有提供 `getWritableDatabaseAsync()` 这样的异步打开 API。把 open / Migration 从主线程移走的做法是应用侧自己包装：用 dedicated executor、协程或 App Startup Initializer 在后台线程调用 `getWritableDatabase()`，拿到数据库句柄后再切回主线程。16KB 数据库页转换场景下（页大小变化需要整库重写），同步 `getWritableDatabase()` 可能需要数秒到数十秒，必须确保这条路径不进入主线程。

## 2. CursorWindow 与跨进程 Cursor 传输

### 2.1 CursorWindow 的内部结构

CursorWindow 是一块“装查询结果片段”的窗口，不是“整条查询结果”的镜像。窗口大小不是写死在某个 `CURSOR_WINDOW_SIZE` 常量里的固定 2MB，当前 AOSP 通过 `config_cursorWindowSize` 资源读取；在 `android-17.0.0_r1` 中，该资源默认值是 2048KB。

```java
// frameworks/base/core/java/android/database/CursorWindow.java
private static int getCursorWindowSize() {
    if (sCursorWindowSize < 0) {
        sCursorWindowSize = Resources.getSystem().getInteger(
                com.android.internal.R.integer.config_cursorWindowSize) * 1024;
    }
    return sCursorWindowSize;
}
```

当查询发生在同一进程时，`SQLiteCursor` 直接在这块窗口里填充数据。查询跨进程穿过 ContentProvider 时，客户端先拿到 `BulkCursorDescriptor`，后续再通过 `CursorToBulkCursorAdaptor` / `IBulkCursor` 请求窗口。窗口本体通过 `CursorWindow.writeToParcel()` 序列化，底层走的是 ashmem FD 共享，不是把整块窗口直接塞进一次 Binder payload。

### 2.2 SQLiteCursor 的 refill 调用链

Cursor refill 和业务分页 SQL 是两件事。当前 AOSP 的 in-process 路径是：

```java
// frameworks/base/core/java/android/database/sqlite/SQLiteCursor.java
public boolean onMove(int oldPosition, int newPosition) {
    if (mWindow == null || newPosition < mWindow.getStartPosition()
            || newPosition >= (mWindow.getStartPosition() + mWindow.getNumRows())) {
        fillWindow(newPosition);
    }
    return true;
}
```

`fillWindow(newPosition)` 之后会进入 `SQLiteQuery.fillWindow()`，再由 `SQLiteSession.executeForCursorWindow()` 把结果写进当前窗口。跨进程时，Provider 侧的 `CursorToBulkCursorAdaptor.getWindow(position)` 会先看已有窗口是否覆盖目标位置，不够再调用 `mCursor.fillWindow(position, window)`。CursorWindow refill 发生在 Cursor / Provider 这一层，Room Paging 是另一层更高的装载协议。

### 2.3 CursorWindow、ashmem 与 TransactionTooLargeException

把“大查询”直接等同为“Binder buffer 溢出”太粗。跨进程 Cursor 返回时，常见路径是 `BulkCursorDescriptor` 携带窗口描述信息，窗口内容通过 ashmem FD 共享。容易混在一起的有三类问题：

- **CursorWindowAllocationException / row too big**：单行太宽，或者窗口分配失败，数据无法塞进当前窗口。
- **频繁 refill 带来的卡顿**：窗口本身能创建，但因为 projection 过宽、目标位置太深或跨进程往返太多，列表滚动时不断触发 refill。
- **TransactionTooLargeException**：更常见于同一次 Binder 事务里还夹带了大 `Bundle`、大 `Cursor` extras、多个并发事务共享 buffer，或者把非 Cursor 数据一起塞进回复包。

看到 `TransactionTooLargeException` 时，先区分“Binder reply 负载过大”还是“CursorWindow 太大 / 单行太宽”；看到滚动卡顿时，再去判断是不是 refill 次数过多。

### 2.4 分页策略：Room Paging 与 Keyset 要分开看

Paging 3 负责“什么时候加载下一页”，SQL 负责“这一页怎么取”。这两层不要混在一起。

**Room + Paging 3 的默认集成**，通常走的是 `PagingSource<Int, T>` + `LimitOffsetPagingSource`，底层由 `RoomPagingUtil.kt` 生成 `LIMIT / OFFSET` 查询。它解决了列表装载、失效通知和预取协同，但没有把深翻页自动变成 Keyset。

```sql
-- Limit/Offset: Room Paging 默认更接近这一类
SELECT * FROM messages ORDER BY id LIMIT 20 OFFSET 1000;

-- Keyset: 需要业务自己设计查询条件
SELECT * FROM messages
WHERE id > :last_id
ORDER BY id
LIMIT 20;
```

如果列表会翻到很深的位置，Offset 成本仍然会随页数增长。Keyset 的优势在于利用索引直接定位起点，但它要求业务提供稳定排序键和游标条件。Paging 3 可以承载这两种查询，决定成本的是 DAO SQL，不是 Paging 3 这个框架名字本身。

## 3. Room 的性能特性与优化

### 3.1 Room 的线程模型

Room 不会无条件把所有数据库操作搬到后台线程，API 形态决定执行模型。

- **同步 DAO 方法**：就在调用线程执行。如果发生在主线程，Room 会直接抛异常；只有显式 `allowMainThreadQueries()` 才会关掉这层保护。
- **`suspend` DAO / `withTransaction`**：走 Room 的 coroutine / executor 适配层，在 query executor 或 transaction executor 上执行。
- **`Flow` / `LiveData` / Rx 返回类型**：Room 负责生成观察与重查逻辑，SQL 执行仍然落到它配置的 executor 上。

这个区分直接影响排查路径：主线程卡在数据库上，不一定是 Room 失效，更常见的是调用点本身选了同步 API，或者数据库第一次 open / migration 就发生在主线程。

在日志与 trace 里，我们更应该找三件事：DAO 是同步还是异步、第一次 open 发生在哪个线程、事务和查询各自用了哪个 executor。至于 WAL，Room 的 `JournalMode.AUTOMATIC` 通常会在 API 16+ 且非低内存设备上选择 WAL，这给读写并发提供了更好的默认起点，但不改变“只有一个写者”的基本约束。

### 3.2 Room 的 @Transaction 与 suspend 函数

Room 的 `@Transaction` 注解确保方法在一个数据库事务中执行。对于 `suspend` 函数，Room 使用 `withTransaction` 扩展函数，它在内部通过 Room 的 transaction executor（或协程上下文）调度事务体的执行。

使用事务的收益除了原子性，也体现在性能上。以下面的批量插入为例：

```kotlin
// 不使用事务：1000 次插入 = 1000 次独立事务，每次都要获取写锁、写入 WAL
items.forEach { dao.insert(it) }

// 使用事务：1000 次插入 = 1 次事务，1 次锁获取 + 1 次 WAL 提交
@Transaction
suspend fun insertAll(items: List<Item>) {
    items.forEach { dao.insert(it) }
}
```

没有事务时，每次 `insert()` 都是独立的事务：获取 SQLite 写锁 → 写入 WAL → 提交。1000 次插入意味着 1000 次这样的循环。每次提交是否触发 `fsync()` 取决于 WAL sync mode：Android 默认 `db_wal_sync_mode` 为 `NORMAL`（参见 AOSP `frameworks/base/core/res/res/values/config.xml`），提交时只写 WAL 页缓存但不强制 `fsync`。超过 `wal_autocheckpoint` 阈值（AOSP 默认 100 页）时，checkpoint 在提交路径或显式 checkpoint 路径发生——因此仍可能把 I/O 成本落到当前写线程，不存在一个可依赖的独立后台 checkpoint 线程。即便如此，1000 次独立事务的开销仍然来自锁获取、WAL 写入和事务状态切换的累积——即使每次只有微秒级，乘以 1000 后也会很可观。如果 sync mode 被设为 `FULL`，则每次提交都会 `fsync`，代价更高。

使用事务后，锁获取和 WAL 提交只发生一次，1000 条数据批量写入 WAL 文件。批量插入的速度提升可达数量级差异（常见 10x-100x），具体幅度取决于事务大小、sync mode、存储栈和设备性能。

### 3.3 Paging 3 的懒加载与预取策略

Room 对 Paging 3 的支持通常通过 `PagingSource<Int, T>` 暴露，但默认实现不等于 Keyset。AndroidX `room-paging` 当前提供的是 `LimitOffsetPagingSource`，`RoomPagingUtil.kt` 会基于 DAO 查询生成 `LIMIT / OFFSET` 形式的分页 SQL。

这套实现的好处是和失效通知、预取、刷新锚点配合得很顺，代价也很直接：如果 Offset 很深，数据库仍然要跳过前面的记录，查询成本不会因为用了 Paging 3 就自动消失。只有当业务自己把 SQL 设计成 `WHERE id > :lastId ORDER BY id LIMIT N` 这类游标条件时，才是在做 Keyset pagination。

`prefetchDistance` 和 `loadSize` 仍然值得调。过大的 `loadSize` 会让单次查询返回更多列和更多行，在宽表、大文本列或跨进程 Cursor 场景下，更容易把 refill 成本放大。

### 3.4 Migration 的性能风险

Migration 发生在数据库 open 过程中。Room 最终还是通过 `SupportSQLiteOpenHelper` / `SQLiteOpenHelper` 打开数据库，所以谁触发第一次 open，谁就承担 Migration 的时间成本。

如果首次 open 出现在主线程，例如 App 启动早期直接调用同步 DAO，或者 ContentProvider / Application 初始化链里提前访问数据库，大型 `ALTER TABLE`、回填脚本和 `CREATE INDEX` 就会直接卡住当前线程。`allowMainThreadQueries()` 只会关闭 Room 的主线程访问检查，不会让 Migration 变快。

```kotlin
// 危险：首次 open 发生在 UI 路径，Migration 成本会直接落在当前线程
val db = Room.databaseBuilder(context, AppDb::class.java, "app.db")
    .addMigrations(MIGRATION_3_4)
    .build()
```

更稳妥的做法是把“首次 open + migration”提前到可控的后台时机，例如启动前置预热、冷启动后的 dedicated executor，或者由 App Startup 触发一次后台 prewarm。App Startup 在这里是调度手段，不是 Room 的专用优化开关。

## 4. 索引与查询优化

### 4.1 索引策略

索引是 SQLite 查询优化最有效的手段。但索引不是免费的——每个索引在写入时需要额外维护，在 WAL 模式下也不例外。

**复合索引的列顺序**对查询计划有直接影响。SQLite 使用最左前缀匹配规则：复合索引 `(A, B, C)` 可以加速 `WHERE A=?`、`WHERE A=? AND B=?`、`WHERE A=? AND B=? AND C=?` 三种查询，但不能加速 `WHERE B=? AND C=?`。

```sql
-- 创建复合索引
CREATE INDEX idx_msg_conv_date ON messages(conversation_id, date);

-- 命中索引：最左前缀匹配
SELECT * FROM messages WHERE conversation_id = 42 ORDER BY date;

-- 不命中索引：跳过了最左列
SELECT * FROM messages WHERE date > '2025-01-01';
```

### 4.2 EXPLAIN QUERY PLAN 的使用

`EXPLAIN QUERY PLAN` 是判断查询是否命中索引的直接工具：

```sql
EXPLAIN QUERY PLAN SELECT * FROM messages WHERE conversation_id = 42;

-- 输出：
-- SCAN messages USING INDEX idx_msg_conv_date
```

解读时看三类输出：

- `SCAN TABLE`（不带 `USING INDEX`）→ 全表扫描，通常需要优化
- `SCAN TABLE USING INDEX` → 索引扫描，正常
- `SEARCH TABLE USING INDEX` → 索引精确查找，最优

### 4.3 WITHOUT ROWID 表

对于没有按 `rowid` 查询需求的表（比如只通过主键查询的关联表），`WITHOUT ROWID` 可以减少存储开销和查询层级：

```sql
CREATE TABLE user_prefs (
    user_id TEXT PRIMARY KEY,
    pref_key TEXT,
    pref_value TEXT
) WITHOUT ROWID;
```

`WITHOUT ROWID` 表将数据直接存储在索引的叶子节点中，省去了一次 B-tree 查找。适合小表、频繁按主键查询的场景。

### 4.4 PRAGMA 调优

排查和调优时常看的 PRAGMA 设置：

| PRAGMA | 推荐值 | 说明 |
|--------|--------|------|
| `journal_mode` | `WAL` | 读写并发（Room 已默认启用） |
| `synchronous` | `NORMAL` | WAL 模式下兼顾安全性和性能 |
| `busy_timeout` | `3000` | 写冲突时等待 3 秒而非立即返回 `SQLITE_BUSY` |
| `cache_size` | `-8000` | 页缓存 8MB（默认约 2MB），减少磁盘读取 |

**16KB Page Size 下的 checkpoint 调优**：SQLite 上游默认 `wal_autocheckpoint` 为 1000 页，但 Android 通过 `frameworks/base/core/res/res/values/config.xml` 中的 `db_wal_autocheckpoint` 资源覆盖为 **100 页**（可通过 `SQLiteGlobal.getWALAutoCheckpoint()` 读取）。这里的页数指 SQLite 数据库页，不是直接等同于 Linux 内存页；Android 默认数据库页大小来自 `SQLiteGlobal.getDefaultPageSize()`，也就是 `/data` 文件系统的 block size（可被 `debug.sqlite.pagesize` 覆盖）。因此 checkpoint 写回规模应按 `PRAGMA page_size` 实测值计算：4KB 数据库页约 400KB，16KB 数据库页约 1.6MB。如果应用或 SDK 通过 `PRAGMA wal_autocheckpoint` 修改了这个值，需要按实际页大小重算 checkpoint 规模。建议按设备 I/O 能力和事务模式实测后调整，而不是直接套用固定数值。

`synchronous=NORMAL` 在 WAL 模式下是安全的：正常使用时数据不会丢失，只有在系统崩溃（非应用崩溃）的极端情况下才可能丢失最近一次检查点之后的事务。对于绝大多数应用来说，这个风险可以接受。

## 5. 数据库与 ANR 的关联分析

### 5.1 主线程数据库操作的连锁反应

ANR traces 中更常见的数据库相关模式是：

1. 主线程或 Binder 调用线程触发了一次慢查询、慢事务，或者首次 open 命中了 Migration。
2. 后续线程在 `SQLiteConnectionPool.waitForConnection()` 上排队，或者客户端主线程在 `ContentResolver.query()` 的 Binder reply 上等待远端 Provider。
3. Provider / 后台线程继续执行长事务、`CREATE INDEX`、大 projection 查询或频繁 refill。
4. 同一路径上的其他线程也被拖住，最终形成连锁阻塞。

在 ANR traces 中，我们更可能看到下面这种栈形态：

```text
"main" prio=5 tid=1 Native
  at android.database.sqlite.SQLiteConnectionPool.waitForConnection(...)
  at android.database.sqlite.SQLiteSession.executeForCursorWindow(...)
  at android.database.sqlite.SQLiteQuery.fillWindow(...)
```

### 5.2 ContentProvider + SQLiteConnectionPool 的组合阻塞

这是比“单进程慢查询”更难查的一类问题。

1. 客户端进程在主线程调用 `ContentResolver.query()`，等待远端 Provider 的 Binder reply。
2. Provider 进程里的工作线程已经被一个长事务或 Migration 占住了可用连接。
3. 新的 `query()` / `insert()` 在 Provider 侧排队到 `SQLiteConnectionPool.waitForConnection()`。
4. 客户端主线程表面上像卡在 Binder，根因却在 Provider 侧数据库连接池。

如果 Provider 里又夹着应用自定义锁或回调，问题才可能进一步演变成严格意义上的循环等待。线上更常见的是“Binder 等远端，远端等数据库连接”这类组合阻塞。

解决方向有三个：Provider 和 App 共享同一套 helper / open 策略，避免冷启动时重复 open；把长事务、Migration、批量导入移出高频 query 路径；跨进程查询尽量缩 projection，减少 refill 和 Binder 往返。

### 5.3 在 Perfetto 中定位数据库问题

在 Perfetto 里看数据库问题，先分三层：调用线程是不是直接执行 SQL、是不是在等 Java monitor、是不是在等远端 Provider 或连接池。

**第一步**：找主线程或 Binder 调用线程上的长 slice。调用栈如果直接落在 `SQLiteQuery`、`executeForCursorWindow()`、`beginTransaction()` 或 DAO 生成代码，先看 SQL 本身和事务时长。

**第二步**：如果线程卡在 Java monitor 竞争上，先加载 Perfetto stdlib 的 `android.monitor_contention` 模块，再查表 `android_monitor_contention`：

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
WHERE process_name = 'your.process'
ORDER BY dur DESC
LIMIT 20;
```

模块名是 `android.monitor_contention`，表名是 `android_monitor_contention`。这组数据只覆盖 Java monitor 竞争，不会直接告诉我们 SQLite 原生文件锁或 connection pool 等待。

**第三步**：如果主线程停在 Binder reply、Provider query 或 `Object.wait()`，而 `android_monitor_contention` 没给出明显的 owner / waiter 关系，就回到 `sched`、Binder slices 和 Provider 侧线程看有没有长事务、Migration 或 `waitForConnection()` 排队。对数据库问题来说，这一步通常更贴近当前实现，因为主要热点往往出在连接池争用。

### 5.4 StrictMode 检测

在开发阶段启用 `StrictMode` 可以提前发现主线程数据库操作：

```kotlin
StrictMode.setThreadPolicy(
    StrictMode.ThreadPolicy.Builder()
        .detectDiskReads()
        .detectDiskWrites()
        .penaltyLog()     // 输出到 Logcat
        .penaltyDeath()   // 直接崩溃，确保不会遗漏
        .build()
)
```

注意 `penaltyDeath()` 只应在 Debug 构建中启用。`detectDiskReads()` 会捕获所有磁盘 I/O，包括数据库读操作。

## 6. 异步数据库操作的线程池设计

### 6.1 单线程串行 vs 并发写入

由于 SQLite 在同一时刻只允许一个写者（即使在 WAL 模式下），数据库写操作的线程池设计有两条路径：

**单线程串行写入**：SQLite 在同一时刻只允许一个写者，Room 的事务通过 transaction executor 进入事务路径并保持事务互斥与顺序。这里分三层看：SQLite 内核层保证单写者；Room 的 `withTransaction` 在 transaction executor 上执行事务体并持有数据库互斥；应用如果需要全局写入顺序和背压控制，仍应显式设计单写队列或受控 executor——Room 的 transaction executor 是可配置的，默认可能与 query executor 共用底层线程池，不等于自动建立一个 dedicated single-thread 写队列。

```kotlin
val dbWriteExecutor = Executors.newSingleThreadExecutor()
// 所有写操作提交到这个线程池
dbWriteExecutor.execute { dao.insertAll(items) }
```

**并发写入（谨慎使用）**：使用多线程写入，依赖 SQLite 内部的 `SQLITE_BUSY` 处理机制。需要设置 `PRAGMA busy_timeout` 来避免立即返回错误：

```sql
-- 等待 3 秒而非立即返回 SQLITE_BUSY
PRAGMA busy_timeout=3000;
```

在 WAL 模式下，读操作可以与写操作并发执行，因此读操作的线程池可以适当增加并发度。但写操作仍然推荐串行化。

### 6.2 把排查路径收成一个真实场景

假设首页冷启动后立即查消息列表，主线程在 `ContentResolver.query()` 等 Binder reply，Provider 侧同时在做一次大 Migration。这个场景里，排查顺序通常是：

1. 先确认数据库 first open / Migration 落在哪个线程。
2. 再看 Provider 侧有没有长事务、`CREATE INDEX` 或大 projection 导致 `executeForCursorWindow()` 太慢。
3. 如果列表使用 Room + Paging 3，确认 DAO SQL 到底是 `LIMIT / OFFSET` 还是业务自定义 Keyset，不要把 Paging 3 的框架名当成性能担保。
4. 再回到数据设计：projection 是否过宽、BLOB 是否外置、写操作是否串行化、跨进程查询是否真的有必要。

按这个顺序排查，前面各节的建议会对应到具体动作：同步 DAO 避免进主线程，批量写入放进事务，长 Migration 提前预热，深翻页场景改成稳定排序键 + Keyset，跨进程 Cursor 缩小窗口压力。回到 ANR / Perfetto 场景时，读者可以直接拿这套路径排查，而不是只对着清单打勾。

## 扩展

### 🔸 扩展点 1：SQLCipher 加密数据库的性能开销

SQLCipher 在 SQLite 之上增加了加密层，每次读写操作都需要进行加解密。性能影响主要体现在：

- 写入速度降低约 5-15%（取决于加密算法和硬件加速支持）
- 读取速度影响较小（解密是流式的，且有页级缓存）
- 数据库打开时间增加（密钥派生操作）
- 首次访问每个数据页时需要解密，之后缓存在内存中

在性能敏感的场景中，可以考虑只在特定表或列上使用加密，而非全库加密。Android Keystore + 自定义加密方案是另一种思路。

### 🔸 扩展点 2：多进程数据库访问

多进程场景下的数据库访问需要特别注意：

- **WAL 模式是多进程友好的**：多个进程可以同时读取数据库，写操作仍然串行
- **`enableMultiInstanceInvalidation()`**：Room 提供的 API，确保多进程间数据变更的实时同步
- **避免多进程写冲突**：建议使用单一进程写、多进程读的模式，或者使用 `ContentResolver.applyBatch()` 将写操作聚合

多进程场景下的数据库问题在 Perfetto 中通常表现为：一个进程持有 SQLite 锁，另一个进程的线程在 `sqlite3BusyWait()` 或 `usleep()` 中等待。如果看到这种模式，需要检查是否有跨进程的写冲突。
