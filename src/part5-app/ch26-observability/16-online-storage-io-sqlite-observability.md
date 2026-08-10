---
title: "线上存储、I/O 与 SQLite 可观测性"
chapter: "26.16"
status: ready-for-review
drafted_date: "2026-05-21"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-21"
last_verified_against: "AOSP master / Android Developers docs / SQLite docs"
confidence: medium
sources:
  - type: clipping
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 14.md"
  - type: clipping
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 16.md"
  - type: clipping
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 17.md"
  - type: official
    path: "https://developer.android.com/topic/performance/sqlite-performance-best-practices"
  - type: official
    path: "https://developer.android.com/reference/android/os/StrictMode"
  - type: official
    path: "https://developer.android.com/reference/androidx/room/RoomDatabase.QueryCallback"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/sqlite"
  - type: official
    path: "https://www.sqlite.org/eqp.html"
  - type: aosp
    path: "frameworks/base/core/java/android/database/sqlite/SQLiteConnection.java"
  - type: aosp
    path: "libcore/luni/src/main/java/libcore/io/BlockGuardOs.java"
  - type: aosp
    path: "libcore/dalvik/src/main/java/dalvik/system/CloseGuard.java"
tags: [observability, storage, io, sqlite, matrix]
related_chapters: ["24.1", "24.2", "24.12", "26.3", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "Clippings参考书/研究盲区/官方文档/AOSP结构"
---

# 26.16 线上存储、I/O 与 SQLite 可观测性

存储故障很少只有一个症状。一次“打开页面卡住”可能包含主线程读文件、SQLite 连接等待和目录扫描；一次“数据丢了”可能来自磁盘空间不足、损坏恢复策略或尚未持久化的写入。这里关注如何留下足以区分这些路径的线上证据。文件 I/O 和 SQLite 的优化方法分别见 24.1、24.2，通用采集预算见 26.3。

平台源码以 `android-17.0.0_r1` 为准，涉及内核 tracepoint 时以 `android17-6.18-2026-06_r6` 为准。AndroidX SQLite、Room 和 Matrix 并不随 API 37 固定版本：应用使用哪一种 driver、库版本和 Hook 实现，必须作为事件字段保存。

## 观测对象边界

存储指标应先按失败层次分类。单一的 `storage_slow` 只能说明耗时上升，无法判断应检查文件调用、数据库并发还是设备空间。

| 问题 | 建议事件 | 最小字段 | 诊断目的 |
|---|---|---|---|
| 文件调用慢 | `storage_io_operation` | 操作类别、路径类别、线程、wall time、CPU time、字节数、调用点、场景 | 区分调用方耗时、线程被抢占和疑似 I/O 等待 |
| 不良访问形态 | `storage_io_pattern` | 规则、窗口内次数、累计字节、累计耗时、文件指纹、调用点 | 找到主线程访问、细碎调用、重复读取和大目录遍历 |
| SQLite 执行慢 | `sqlite_operation` | scope、SQL 指纹、操作类型、线程、事务状态、wall time、driver | 区分查询本身、排队、事务和连接等待 |
| SQLite 错误 | `sqlite_error` | 异常类、主错误码/扩展码（若可得）、数据库别名、事务状态、恢复动作 | 分开处理 busy/locked、I/O error、full、corrupt 和约束错误 |
| 空间增长 | `storage_snapshot` | 目录类别、总字节数、文件数、年龄桶、扫描覆盖率 | 找出增长来源，并判断快照是否完整 |
| 业务文件损坏 | `file_validation_failure` | 格式版本、校验阶段、校验类型、文件类别、最近写入状态、恢复结果 | 区分下载不完整、写入中断、版本不兼容和内容损坏 |
| 资源未关闭 | `resource_leak_signal` | 资源类型、创建调用点、进程 fd 水位、发现方式 | 定位 Cursor、stream、ParcelFileDescriptor 等生命周期问题 |

Wall time 与 CPU time 应分开。wall time 很长而当前线程 CPU time 很短，可能是调度、锁或 I/O 等待；两者都高则更像用户态计算。这个判断只能用于选择下一步证据，不能仅凭两个时长宣告内核 I/O 是根因。

事件还要标注观测范围。围绕 DAO 方法计时得到的是调用端到端时长，可能包含协程调度和连接等待；在 driver 执行边界计时更接近 SQLite 操作；Native `read()`/`write()` Hook 看到的是系统调用，不包含所有页缓存回写。若字段里只写 `duration`，后台会把不同 scope 的数据错误合并。

路径、SQL 和文件内容都可能包含用户数据。默认只采集稳定类别、受控指纹和应用调用点；需要原始证据时，应走 26.5 的受限诊断流程，而不是提高常规事件的敏感度。

## I/O 采集路径选择

采集路径决定了覆盖面，也决定了升级风险。优先选择公开 API 和应用可控边界，只有确认缺口值得引入额外兼容成本时，才使用 Hook。

| 路径 | 能看到什么 | 看不到什么 | 建议使用范围 |
|---|---|---|---|
| 应用封装或库提供的回调 | 自有文件组件、Okio/FileSystem、缓存 SDK、导入导出任务 | 绕过封装的三方库和系统内部调用 | 生产环境长期采集的主路径 |
| 编译期插桩 | 自有字节码中的文件入口、DAO 调用、事务方法 | Native、反射调用、已编译三方库和系统内部 I/O | 可控模块的低采样观测；升级 AGP 时做字节码回归 |
| StrictMode / BlockGuard | 经 libcore OS 层上报的线程磁盘读写，以及未缓冲 I/O、SQLite/Closable 泄漏信号 | 三方 Native 代码直接调用 libc 的全部 I/O；精确字节数和设备耗时 | debug、自动化测试、dogfood；生产仅在评估成本后受控开启 |
| Native interposition / Hook | 命中的 libc 或目标库 I/O 符号，可覆盖部分 Java 与 Native 路径 | 内联调用、直接 syscall、未命中符号、mmap 后缺页、异步回写 | 专项灰度；必须按 API、ABI、加载顺序和目标库验证 |
| adb Perfetto | sched、频率、应用 trace、database atrace，以及设备允许的 ftrace/block/filemap 数据 | 没有启用或无权限的数据源；一次 trace 之外的长期分布 | 实验室复现和开发设备诊断 |
| `ProfilingManager` system trace | Android 15+ 受系统限流的应用请求采集；Android 17 还可结合部分系统 trigger | 不保证每次请求成功，也不等同于任意 adb Perfetto 配置 | 线上小范围诊断，版本细节见 26.12 |

### StrictMode 能证明什么

Android 17 的 [`BlockGuardOs`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/luni/src/main/java/libcore/io/BlockGuardOs.java) 在 `open`、`read`、`write`、`fsync`、`stat`、`rename` 等 libcore OS 操作前调用线程策略的 `onReadFromDisk()` 或 `onWriteToDisk()`。因此 StrictMode 擅长回答“这个受监控线程是否触发磁盘操作”，不负责测量存储设备完成一次请求的时间。

下面的配置用于 debug 或 dogfood 包，让主线程磁盘访问、未缓冲 I/O 和资源未关闭进入日志。它只是发现入口，生产策略应另行评估。

```kotlin
StrictMode.setThreadPolicy(
    StrictMode.ThreadPolicy.Builder()
        .detectDiskReads()
        .detectDiskWrites()
        .detectUnbufferedIo()
        .penaltyLog()
        .build()
)

StrictMode.setVmPolicy(
    StrictMode.VmPolicy.Builder()
        .detectLeakedSqlLiteObjects()
        .detectLeakedClosableObjects()
        .penaltyLog()
        .build()
)
```

`setThreadPolicy()` 作用于调用它的线程；若只在主线程安装，就不能据此声称覆盖全部工作线程。`detectUnbufferedIo()` 从 API 26 提供，`detectLeakedSqlLiteObjects()` 从 API 9 提供。`detectResourceMismatches()` 检查资源类型读取不匹配，从 API 23 已存在，与文件句柄泄漏无关，更不是 Android 17 新增的存储能力。

[`CloseGuard.setReporter()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/dalvik/src/main/java/dalvik/system/CloseGuard.java) 在 Android 17 仍标记为隐藏/System API。普通应用不应通过反射替换 reporter 来建设长期监控；这会同时引入 non-SDK 限制和版本兼容风险。公开的 StrictMode VM policy 更适合测试与受控诊断。

### Native Hook 的工程边界

Native Hook 不是 Android 平台保证的扩展点。即使某版能够拦截 `open`、`read`、`write` 和 `close`，也要逐项验证：

- 已加载和延迟加载的共享库是否都进入 Hook。
- 32/64 位 ABI、不同 Android 版本和厂商链接器行为是否一致。
- `pread`/`pwrite`、`readv`/`writev`、`mmap`、`sendfile`、直接 syscall 是否在覆盖清单中。
- Hook 内部是否有递归保护，采集和上报自身的 I/O 是否会再次触发 Hook。
- 路径、fd 生命周期和调用栈采集是否线程安全，卸载或失败时能否回到原函数。
- 远程关闭、采样和崩溃隔离是否在 Hook 初始化前可用。

Hook 覆盖不完整并不表示数据无用，但事件必须带 `collector` 和 `coverage_version`。没有这两个字段，就无法区分业务回归与采集器升级造成的数量变化。

## 不良 I/O 规则模板

通用规则可以固定，阈值不能跨设备和场景照搬。闪存、文件系统、加密层、温控、后台压力和数据规模都会改变耗时。规则至少要按设备档、前后台、业务场景和 App 版本建立基线。

| 规则 | 判断信号 | 必要上下文 | 容易误判的情况 |
|---|---|---|---|
| 主线程 I/O | StrictMode violation，或主线程文件调用与交互卡顿时间重叠 | 生命周期阶段、调用点、操作类型、wall/CPU time | 启动框架内部一次性访问、采集器本身写日志 |
| 细碎 I/O | 单位字节对应的系统调用数偏高，连续窗口内多次短 read/write | 总字节数、调用数、buffer、文件类型、调用点 | 协议要求的小记录、设备已在页缓存中 |
| 重复读取 | 同一文件版本和调用点在短业务窗口内重复读取，期间没有有效写入 | 文件指纹、mtime/业务版本、调用点、场景 | 文件被外部进程或 ContentProvider 更新 |
| 大目录遍历 | 扫描耗时、访问文件数或主线程阻塞相对基线异常 | 已扫描/总量估计、深度、剪枝原因、目录类别 | 首次迁移、媒体导入、用户主动全量扫描 |
| fd 水位增长 | `/proc/self/fd` 数量在稳定场景中持续上升，离开场景后不回落 | 进程、场景、资源类型、StrictMode/CloseGuard 信号 | 网络连接池、动态加载和诊断采集临时占用 |
| 同步写入放大 | 单次业务提交对应多次 write/fsync，且交互时延同步升高 | 事务、文件协议、WAL 状态、调用点 | 明确要求持久性的关键数据 |

不要用 `StatFs.getBlockSizeLong()` 推导 Java buffer 的统一下限。文件系统块大小不等于存储设备页、内核合并粒度或应用最佳 buffer；小 buffer 是否有问题，应由调用次数、总字节数、CPU 开销和目标设备实验共同判断。

阈值治理可以遵循同一流程：在无回归版本采集分布，固定事件 scope 和分母；按设备档与场景建立基线；用对照版本差值和置信区间触发告警；检查样本量、采集覆盖与上报缺口；修复后验证同一分组是否恢复。业务有明确体验预算时，可以增加绝对上限，但要记录预算来源。

主线程磁盘访问可以在 debug 阶段按“发生即检查”处理，线上告警仍不应把每次访问等同于用户卡顿。调用发生时数据可能已在页缓存，耗时也可能短于一次帧预算；关联 FrameTimeline、主线程 slice 和用户操作后再确定优先级。

## SQLite 耗时、损坏与查询计划

SQLite 可观测性应区分执行、事务、连接等待、错误和恢复。一个 DAO 方法慢，不代表 SQL 计划一定慢；它也可能在等待 writer、调度到数据库线程，或在结果映射阶段消耗 CPU。

| 事件 scope | 起止位置 | 可以解释什么 | 不能直接解释什么 |
|---|---|---|---|
| DAO end-to-end | 调用 DAO 到结果返回 | 用户路径中的总等待 | SQLite 内部执行占比 |
| transaction | `begin` 到 commit/rollback 返回 | 锁持有窗口、批量写范围 | 每条语句成本 |
| driver statement | prepare/step 到完成 | 接近 SQL 执行和取数成本 | 调用前排队与结果业务处理 |
| query callback | Room 通知某条 SQL 已执行 | SQL 文本、bind 参数和调用频率 | 精确耗时；回调可能在另一个 Executor 上 |
| exception/recovery | 捕获异常到恢复动作结束 | 错误类别、数据可用性和恢复结果 | 错误发生前所有磁盘状态 |

### Room QueryCallback 不是慢查询计时器

`RoomDatabase.QueryCallback#onQuery()` 提供 SQL 和可用的 bind arguments。官方文档明确提示它有额外成本，除非需要，否则应避免在 production build 使用。回调本身没有开始时间和结束时间；在 callback Executor 里计时，只会得到回调处理时长。

下面的片段只用于生成 SQL 指纹和参数类型，不保存参数值。实际工程还应限制队列长度并对回调自身做采样。

```kotlin
val callback = RoomDatabase.QueryCallback { sql, bindArgs ->
    queryObserver.record(
        sqlFingerprint = normalizer.fingerprint(sql),
        bindTypes = bindArgs.map { value -> value?.javaClass?.simpleName ?: "null" }
    )
}

Room.databaseBuilder(context, AppDatabase::class.java, "main.db")
    .setQueryCallback(callback, queryCallbackExecutor)
    .build()
```

SQL 文本也可能通过字符串拼接包含账号、搜索词或 URL，不能只丢弃 `bindArgs`。`normalizer` 应先完成词法归一化和敏感字面量删除，再计算受控指纹。若使用 DAO 外围计时，字段名应明确写成 `dao_end_to_end`，避免与 driver 执行耗时合并。

### Android 17 framework 内部有哪些诊断信息

[`SQLiteConnection.OperationLog`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnection.java#1705) 是 Android 17 framework 的私有内部类。下面两项常量说明它保留 20 条最近操作，并把严格超过 2 秒的操作放入另一组长操作记录。

```java
private static final int MAX_RECENT_OPERATIONS = 20;
private static final long LONG_OPERATION_THRESHOLD_MS = 2_000;
```

这段实现服务于 framework 调试和 dump，不是普通 App 的采集接口。2 秒也是 framework 内部“long operation”分类值，不应复制成业务慢查询门禁。源码还保存最近 10 条长操作，并对相关日志做限速；“20 条最近操作”“10 条长操作”和累计长操作数是三个不同概念。

Android 17 的 [`SQLiteConnectionPool#getStatementCacheMissRate()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnectionPool.java#1248) 从各可用连接的 prepared statement cache hit/miss 计算 miss rate，但该方法带 `@hide`。每个 framework connection 的默认 cache size 在 [`SQLiteDatabaseConfiguration`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabaseConfiguration.java#70) 中是 25，公开 `SQLiteDatabase#setMaxSqlCacheSize()` 允许的上限是 100。应用不应通过隐藏方法读取 miss rate，也不应在没有内存与命中率证据时把 cache 调到上限。

开发设备可用 `adb shell dumpsys meminfo <package>` 查看 SQLite 的 cache hit、miss、cache size 和部分连接统计；Android 官方 SQLite 性能文档给出了该输出。它适合复现时观察，不是无需权限的线上 API。

[`SQLiteDebug.shouldLogSlowQuery()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDebug.java#99) 读取 `db.log.slow_query_threshold` 及 UID 后缀的系统属性，并且相关日志还受 `SQLiteSlowQueries` log tag 控制。这个隐藏的 adb/系统调试开关不能作为普通 App 动态下发慢查询阈值的方案。官方另有 `log.tag.SQLiteTime` 的开发设备查询计时日志，两条机制也不要混为一个开关。

Android 17 仍提供 lookaside 和 idle connection timeout 配置，但不能从“可配置”推导出“应在线上调整”。`SQLiteDatabase.OpenParams.Builder#setIdleConnectionTimeout()` 已废弃，文档明确警告重建连接会清除 per-connection PRAGMA 状态，系统又没有供 App 恢复这些状态的回调。`setLookasideConfig(0, 0)` 可以请求禁用 lookaside，但系统可能按设备选择不同值；只有在目标 driver、内存和查询基准都证明收益时才考虑修改。

### 查询计划应在同一 SQLite 实现上验证

下面的 SQL 用于检查筛选与排序是否得到合适的访问计划。占位符应在同一 schema 和具有代表性数据量的副本上绑定。

```sql
EXPLAIN QUERY PLAN
SELECT id, name
FROM message
WHERE conversation_id = ?
  AND create_time >= ?
ORDER BY create_time DESC
LIMIT 50;
```

输出中的 `SCAN` 表示扫描，`SEARCH ... USING INDEX` 表示使用索引；`USE TEMP B-TREE` 说明排序、分组或去重可能需要临时 B-tree。它们只是计划节点，不是自动修复指令：小表扫描可能合理，索引会增加写入和空间成本，复合索引的列顺序还要结合过滤、排序和选择性判断。

Android 官方建议用目标设备的 `adb shell sqlite3`，因为不同 Android 版本使用的 SQLite revision 不同。使用 `BundledSQLiteDriver` 时，设备自带 `sqlite3` 又不一定等于应用内 bundled SQLite；此时应使用同一 driver 和同一 schema 的测试工具执行计划。

### 错误、损坏和恢复必须分开

`busy`/`locked` 说明并发或锁状态，`full` 说明写入空间不足，`IOERR` 指向 I/O 路径，`CORRUPT`/`NOTADB` 才更接近数据库内容或格式问题。只按异常 message 搜索 “corrupt” 容易把不同错误合并。

事件至少记录数据库别名、driver、库版本、异常类、主/扩展错误码（driver 提供时）、事务状态、WAL/SHM 是否存在及大小、剩余空间、恢复动作和恢复结果。异常 message 也可能带 SQL 或路径，进入日志前要做脱敏。

完整 `PRAGMA integrity_check` 会读取大量页面，不适合在前台或每次启动执行。需要验证时，可在维护窗口、数据库副本或用户明确发起的诊断流程中运行，并记录检查覆盖。恢复策略应区分可再生缓存、可从服务器重建的数据和唯一用户数据；默认删除数据库会让“恢复成功”掩盖数据丢失。

## 存储容量与文件损坏指标

目录总大小只能说明空间被占用。诊断增长来源还需要文件数、年龄、类别和扫描覆盖率。

| 指标 | 采集方式 | 需要记录的边界 |
|---|---|---|
| 空间余量 | `StatFs` 获取目标卷可用字节和总字节 | 记录卷与采集时间；不要只看全局百分比 |
| 私有目录大小 | 对 `files`、`cache`、`databases`、`no_backup` 等受控类别分别扫描 | 记录扫描是否完成、忽略项和符号链接策略 |
| 文件数与深度 | 有预算的增量遍历 | 记录已访问节点、剩余游标和耗时，避免把部分结果当全量 |
| 大文件/目录 | 只保留受控类别与 Top-K 统计 | K 由上报预算决定，不上传原始文件名 |
| 年龄分布 | 按业务允许的时间字段分桶 | `mtime` 可能被迁移、恢复或外部写入改变 |
| 文件格式校验 | magic、版本、长度、CRC/hash 或业务结构校验 | 校验算法必须属于文件格式协议，不能给所有文件统一加 CRC |
| 清理效果 | 规则版本、候选字节、删除字节、失败原因、再次扫描结果 | 只操作明确可再生且在 allowlist 内的文件 |

全量目录扫描本身会产生 I/O 和 CPU 开销。大目录应保存扫描游标，分批进行，并在前台交互、低电量或系统压力不合适时停止。事件中的 `coverage`、`visited_count` 和 `complete` 与大小值同等重要。

“目录树剪枝 + 受控样本”比上传完整路径更安全。每层保留聚合后的最大目录类别，其他节点归入 `other`；若业务必须关联同一对象，可以使用服务端不可逆的 keyed digest，并设置轮换周期。普通 SHA-256 截断并不能可靠匿名化可枚举的短路径。

业务文件损坏需要与写入协议一起设计。每种格式应定义 magic、版本、长度和校验范围；事件记录写入阶段、临时文件状态和恢复来源。对于应用私有的可替换文件，可使用 `AtomicFile` 或经过验证的 temp-write/rename 协议；数据库文件应交给 SQLite 的事务与 journal/WAL 机制，不要自行对 `.db`、`-wal`、`-shm` 做拼装或远程删除。

远程清理是破坏性能力，应采用固定 allowlist、规则版本、dry-run 统计、幂等执行和远程关闭。未知文件、唯一用户数据、正在打开的数据库文件与当前格式不认识的目录都不能按“疑似缓存”处理。

## 上报、采样与隐私边界

I/O 和 SQL 都是高频事件，采集器必须在设计阶段设定 CPU、内存、磁盘、网络和隐私预算。

| 数据 | 默认保留 | 默认丢弃 | 放大条件 |
|---|---|---|---|
| 文件操作 | 类别、调用点、scope、耗时、字节、采集器版本 | 原始绝对路径、文件内容 | 同调用点持续回归，且远程策略仍满足预算 |
| SQL | 归一化指纹、语句类别、表集合、参数类型、driver | bind 值、未处理字面量、完整结果 | 受限诊断会话；仍不得上传业务数据 |
| 目录快照 | 分类大小、文件数、年龄桶、coverage | 完整目录树和文件名 | 用户授权的问题诊断 |
| 错误 | 类型、错误码、恢复状态、受控 message 指纹 | 数据库内容、原始 SQL、账号路径 | 严重数据不可用事件，按事件限速 |
| 调用栈 | 应用帧指纹、mapping 版本 | 全量系统帧、线程局部变量 | 调用点无法归因的专项灰度 |

采样单位要写清楚。按事件采样会偏向高频调用点；按 session 或 device 采样更适合估算用户影响；触发后采样适合收集异常上下文。后台聚合不能把三种采样结果当作同一分母。

上报 SDK 还需自监控：采集耗时、被采集事件数、采样后保留数、队列深度、本地缓存字节、压缩后大小、上传结果和丢弃原因。文件 Hook 与日志落盘之间必须有递归保护；空间不足时诊断缓存应优先丢弃，不能与业务数据争用剩余空间。

隐私处理要尽可能靠近数据源。Room callback 收到 bind 参数后立即转成类型并丢弃值；路径在离开调用线程前转成类别；URL、账号、搜索词或 token 不应进入 tag、文件名和 SQL 指纹。哈希只减少明文暴露，不自动满足匿名化要求。

## 与现有章节的分工

- 24.1 负责文件 I/O、SharedPreferences、线程与持久化策略的优化。
- 24.2 负责 WAL、事务、索引、连接并发和 Room 使用方式。
- 24.12 负责 MediaStore、Scoped Storage、FUSE 与媒体扫描成本。
- 26.3 负责指标分位数、采样、上报预算和劣化检测。
- 26.5 负责远程证据包、受限诊断、灰度隔离和问题单流程。
- 26.12 负责 `ProfilingManager` 与 trigger 的系统版本边界。

这些事件字段用于把问题导航到对应章节，不重复给出另一套优化规则。

## 扩展：Matrix I/O Canary 与 SQLiteLint

Matrix I/O Canary 和 SQLiteLint 仍适合作为规则设计参考，但不能把历史文档当作 Android 17 兼容性声明。

| 模块 | 可借鉴内容 | 现代工程必须重验的部分 |
|---|---|---|
| I/O Canary | 从文件调用重建主线程 I/O、细碎访问、重复读和泄漏规则 | Hook 符号、链接器/ABI、mmap 缺口、采集递归、当前 AGP 与打包链路 |
| SQLiteLint | 基于运行时 SQL、schema 和 `EXPLAIN QUERY PLAN` 检查索引及临时 B-tree 等问题 | 2019 wiki 所述 `sqlite3_profile` Hook、Room/SQLiteDriver 覆盖、SQLite 新版计划文本和误报 |

SQLiteLint 的 wiki 明确说明其系统 SQLite 路径通过 Hook 向 C 层 `sqlite3_profile` 注册回调。该说明的上次编辑时间为 2019 年，不能推导出它在 API 37、所有 driver 或所有 ABI 上仍有相同覆盖。使用 BundledSQLiteDriver、WCDB 或自带 SQLite 时，目标库甚至不是系统 framework 打开的同一份 SQLite。

接入评审至少要求：固定 Matrix revision；列出支持的 API/ABI/driver；在目标构建工具链跑启动、查询、并发、进程退出和崩溃测试；验证关闭开关；对采集前后 CPU、内存、I/O 与 crash rate 做对照。达不到这些条件时，可以复用规则思想，在应用封装或 Room/driver 回调上重新实现。

自动分析 `EXPLAIN QUERY PLAN` 也要允许例外。小表的 `SCAN`、联接的外层扫描和一次性迁移不一定需要索引；看到 `SEARCH` 也不表示结果集、排序和回表成本合格。规则输出应包含 schema 版本、表行数范围、计划文本和人工处置状态。

## 扩展：AndroidX SQLite/Room 新版本诊断能力

截至 2026 年 7 月，AndroidX SQLite 稳定版为 2.7.0，Room 稳定版为 2.8.4。它们是独立于 Android 17 / API 37 的库版本，不应写成“Room 3.x”或由系统版本推断。

与观测直接相关的变化包括：

- AndroidX SQLite 2.6.2 为 `BundledSQLiteDriver` 创建的连接启用 extended error codes，并用 `@FastNative` 降低部分 JNI 调用成本。
- AndroidX SQLite 2.7.0 已发布，但是否采用应根据该版本 release notes、目标平台和回归测试决定，不能只因它更新而替换线上 driver。
- Room 2.8.4 在使用内部没有连接池的 `SQLiteDriver`（例如 `BundledSQLiteDriver`）时，为 Room 连接池增加 prepared statement cache；这与 Android 17 framework connection 自带的 cache 不是同一层。
- `RoomDatabase.QueryCallback` 仍会为每条执行的查询触发回调，官方继续提示 production cost。开启前应按实际查询量测试。

线上事件建议保留 `room_version`、`androidx_sqlite_version`、driver 类型、是否 bundled、journal mode 和 schema version。更换系统 `AndroidSQLiteDriver`、`BundledSQLiteDriver` 或其他实现后，性能基线和错误码能力都可能变化，时间序列应标记切换点。

## 扩展：Perfetto 文件系统 trace 与线上指标对照

Android 官方 SQLite 性能文档给出的 Perfetto 配置是在 `linux.ftrace` 数据源中加入 `atrace_categories: "database"`，用于显示单条查询轨迹。应用还应在业务入口放置受控 `Trace` slice，这样才能把 DAO、事务和页面场景与 database track 对齐。

| 线上信号 | 开发设备 trace 证据 | 可以排除或确认什么 |
|---|---|---|
| 主线程文件调用 wall time 高 | 应用 slice、sched state、CPU freq、相关 syscall/ftrace | 线程是在运行、runnable、锁等待还是疑似 I/O 阻塞 |
| SQLite end-to-end 高 | DAO/transaction slice、database atrace、连接等待附近线程 | SQL 执行、调度和事务等待各占多少 |
| write/fsync 集中 | 文件调用 slice、writeback 与 block 事件、设备状态 | 写入是否到达 block 层，是否伴随较长设备请求 |
| 读取慢但 block 事件少 | filemap/page fault、sched、CPU 和应用处理 | 数据可能来自页缓存，或耗时发生在用户态/锁等待 |
| 目录扫描影响交互 | 扫描 slice、主线程、binder、GC、文件系统事件 | 遍历、对象分配和系统调用哪个阶段占主导 |

内核锚点 [`block.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/block.h) 定义了 `block_rq_issue`、`block_rq_complete` 等请求事件；[`filemap.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/filemap.h) 和 [`writeback.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/writeback.h) 提供缺页与回写相关事件。设备是否开放这些事件取决于内核配置、trace 配置和权限，不能假设所有量产机都可采。

应用调用与 block request 不是一一对应。页缓存会让 read 不到设备，延迟回写会让 write 与 block I/O 分离，多个请求还可能合并；文件系统、dm-crypt 和存储驱动又会增加层次。trace 的目标是建立时序证据，不是按相同时间戳强行配对每个 Java 调用和每个 block event。

Android 15+ 的 `ProfilingManager` 可以请求受控 system trace，Android 17 的 trigger 能覆盖更多系统事件，但请求受系统限流且可能没有产物。线上应上传采集请求、结果状态和 trace 关联 ID；原始 trace 的合规、保留和访问控制沿用 26.12，不在存储事件里额外保存一份。

## 小结

存储可观测性的产物应是一组定义清楚的证据：文件调用 scope、SQLite 执行层次、空间快照覆盖率、文件格式校验、资源生命周期和采集器自身成本。Android 17 framework 内部的 OperationLog、cache 统计和慢查询属性能帮助理解平台诊断，但其中多项是 private 或 `@hide`，不能直接变成普通 App API。

线上用公开边界和低成本字段发现分布，开发设备再用同一 SQLite 实现、`EXPLAIN QUERY PLAN`、`dumpsys meminfo` 和 Perfetto 验证原因。这样既保留源码依据，也不会让诊断工具依赖未经平台保证的实现细节。

## 参考资料

- [SQLite performance best practices](https://developer.android.com/topic/performance/sqlite-performance-best-practices)
- [SQLite `EXPLAIN QUERY PLAN`](https://www.sqlite.org/eqp.html)
- [StrictMode API reference](https://developer.android.com/reference/android/os/StrictMode)
- [RoomDatabase.QueryCallback](https://developer.android.com/reference/androidx/room/RoomDatabase.QueryCallback)
- [RoomDatabase.Builder#setQueryCallback](https://developer.android.com/reference/androidx/room/RoomDatabase.Builder#setQueryCallback(androidx.room.RoomDatabase.QueryCallback,java.util.concurrent.Executor))
- [AndroidX SQLite release notes](https://developer.android.com/jetpack/androidx/releases/sqlite)
- [Room release notes](https://developer.android.com/jetpack/androidx/releases/room)
- [SQLiteConnection.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnection.java)
- [SQLiteConnectionPool.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnectionPool.java)
- [SQLiteDatabase.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabase.java)
- [SQLiteDebug.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDebug.java)
- [BlockGuardOs.java（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/luni/src/main/java/libcore/io/BlockGuardOs.java)
- [CloseGuard.java（android-17.0.0_r1）](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/dalvik/src/main/java/dalvik/system/CloseGuard.java)
- [Matrix I/O Canary source](https://github.com/Tencent/matrix/tree/master/matrix/matrix-android/matrix-io-canary)
- [Matrix SQLiteLint wiki](https://github.com/Tencent/matrix/wiki/Matrix-Android-SQLiteLint)
