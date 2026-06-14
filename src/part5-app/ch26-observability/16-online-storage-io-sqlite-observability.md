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

<!-- outline-start -->
## 要点

### 🔹 观测对象边界
区分文件 I/O、数据库操作、存储容量、文件损坏与资源泄漏，先确定每类问题应采集的事件、字段和触发条件。

### 🔹 I/O 采集路径选择
对比 Java Hook、Native Hook、插桩、Perfetto/ftrace 的覆盖范围、成本和线上可用边界。结构参考：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 14.md]

### 🔹 不良 I/O 规则模板
整理主线程 I/O、小 buffer 高频读写、重复读、文件句柄泄漏等规则，说明阈值如何按设备档位和业务场景调整。

### 🔹 SQLite 耗时、损坏与查询计划
覆盖 SQLite/Room 的慢查询、busy、损坏、索引缺失与 `EXPLAIN QUERY PLAN` 本地验证路径。结构参考：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 17.md]

### 🔹 存储容量与文件损坏指标
建立文件总量、文件数、目录树剪枝、CRC 校验、损坏率和远程清理策略的采集模板。结构参考：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 16.md]

### 🔹 上报、采样与隐私边界
说明路径脱敏、SQL 参数脱敏、采样率、批量上报、弱网缓存和用户隐私边界。

### 🔹 与现有章节的分工
定位为线上可观测性与诊断：文件 I/O 优化策略详见 24.1，SQLite/Room 性能优化详见 24.2，指标采集框架详见 26.3，线上排查流程详见 26.5。

## 扩展

### 🔸 Matrix I/O Canary 与 SQLiteLint
补充开源方案的接入边界、AGP 版本风险、Hook 覆盖范围和误报处理。

### 🔸 AndroidX SQLite/Room 新版本诊断能力
跟踪 AndroidX SQLite release notes 中 extended error codes、BundledSQLiteDriver 性能变更和 Room 诊断能力。

### 🔸 Perfetto 文件系统 trace 与线上指标对照
补充线下 Perfetto 证据如何映射到线上 I/O 事件字段。

<!-- outline-end -->

存储类线上问题很少只表现为“慢”。同一条用户反馈里，可能同时有主线程 I/O、数据库锁等待、缓存目录膨胀、文件损坏和句柄泄漏。这个章节只讨论线上观测和诊断字段，不重复展开文件 I/O 优化、SQLite/Room 调优和通用上报框架；优化策略详见 24.1、24.2，指标采集框架详见 26.3，线上排查流程详见 26.5。

本节的任务是把存储问题拆成可采集、可聚合、可回放的事件。端上只采集必要字段，后台只保留脱敏后的指纹和统计视图，线下再用 Perfetto、`sqlite3`、`EXPLAIN QUERY PLAN` 复核具体根因。

## 观测对象边界

线上存储可观测性先按问题类型建模。不要把所有事件都塞进一个 “storage slow” 指标，否则后台只能看到 P90 上升，看不到该找 I/O、数据库、缓存清理还是资源泄漏。

| 问题类型 | 端侧事件 | 关键字段 | 触发条件 | 诊断入口 |
|---|---|---|---|---|
| 文件 I/O 慢 | `storage_io_op` | 操作类型、路径分类、线程、耗时、字节数、buffer 大小、调用栈指纹 | 单次或连续读写超过阈值 | 24.1、Perfetto 文件系统 trace |
| 不良 I/O 形态 | `storage_io_rule_hit` | 规则名、命中次数、累计耗时、路径哈希、业务场景 | 主线程 I/O、小 buffer 高频读写、重复读 | Matrix I/O Canary、线下复现 |
| SQLite / Room 慢 | `sqlite_query_slow` | SQL 指纹、耗时、线程、事务状态、Room DAO 或调用栈指纹 | 查询、写入、事务提交超过阈值 | 24.2、`EXPLAIN QUERY PLAN` |
| SQLite 异常 | `sqlite_error` | 异常类型、错误码、数据库别名、WAL 状态、恢复动作 | locked、busy、corrupt、disk full | SQLite 官方文档、Room 日志 |
| 空间膨胀 | `storage_tree_snapshot` | 目录分类、总大小、文件数、Top-K 文件、年龄分布 | 应用私有目录超过档位阈值 | 后台聚合、远程清理规则 |
| 文件损坏 | `storage_file_corrupt` | 文件类型、校验类型、损坏形态、恢复结果 | CRC / header / length 校验失败 | 业务恢复链路 |
| 资源泄漏 | `storage_resource_leak` | 资源类型、创建栈、线程、存活时长 | fd、Cursor、流对象未关闭 | StrictMode、CloseGuard、fd 快照 |

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 14.md] [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 16.md] [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 17.md]

这里有两个边界要先定住。

第一，线上事件不上传原始路径、SQL 参数、文件内容和用户数据。路径只保留分类与哈希，例如 `app_db/main`、`cache/image`、`files/config`；SQL 只保留归一化后的语句指纹，例如 `SELECT name FROM user WHERE id=?`。

第二，端侧采集只负责发现“发生了什么”。是否要改用 mmap、调大 buffer、补索引、拆库或清理缓存，是 24.1 和 24.2 的职责。本节只留下能把问题定位到那些章节的证据。

## I/O 采集路径选择

文件 I/O 的采集方案要在覆盖率、稳定性和线上成本之间取舍。没有一种方案适合全部场景。

| 方案 | 覆盖范围 | 线上成本 | 适用场景 | 边界 |
|---|---|---|---|---|
| Java 层封装 | 业务自己封装的 `FileInputStream`、Okio、缓存组件 | 低 | 新代码、SDK 内部模块、规则灰度 | 覆盖不到系统库、三方库和 Native I/O |
| Java Hook / `BlockGuardOs` 路径 | Java 层经 libcore 进入 `open/read/write/close` 的路径 | 中到高 | 实验室、灰度验证、老代码补盲 | 依赖非 SDK 接口，Android P 之后有隐藏 API 风险 [已验证: AOSP master, libcore/luni/src/main/java/libcore/io/BlockGuardOs.java] |
| Native Hook | libc `open/open64/read/write/close` 等函数 | 中 | 需要覆盖 Java + Native I/O 的线上监控 | 需要处理已加载库、后加载库、线程安全、崩溃兜底 |
| 编译期插桩 | 自有代码的 I/O API、Room DAO、存储 SDK | 低到中 | 大型工程统一规范、能控制源码入口 | 覆盖不到运行时动态调用和系统内部 I/O |
| Perfetto / ftrace | 文件系统、调度、block、线程状态 | 线下为主 | 复现问题、验证规则阈值、解释系统层等待 | 普通线上不能全量开；Android 15+ ProfilingManager 可作为受控采集入口，详见 26.12 |

[已验证: AOSP master, libcore/luni/src/main/java/libcore/io/BlockGuardOs.java] [已验证: 官方文档, developer.android.com/reference/android/os/StrictMode]

微信 Matrix I/O Canary 的思路是 Native Hook：在端上拦截文件打开、读写和关闭，记录路径、buffer、耗时和调用栈，再把主线程 I/O、小 buffer、重复读、资源泄漏抽象成规则。这个方案的价值在于覆盖广，风险也在 Hook 本身：不同 Android 版本、不同 ABI、不同 libc 符号、AGP 和混淆配置都要单独验证。新工程接入 Matrix 时，不要只看采集能力，还要检查当前 Matrix Android 模块和 Gradle 插件是否适配 AGP 8+；老插件仍可能依赖已移除的 Transform API。 [引用: https://github.com/Tencent/matrix/tree/master/matrix/matrix-android/matrix-io-canary]

端侧最小 I/O 事件可以按下面字段落盘。字段越少，越容易长期打开；需要全量调用栈时再靠采样或远程调试开关补齐。

| 字段 | 示例 | 用途 |
|---|---|---|
| `op` | `open` / `read` / `write` / `close` | 区分耗时发生在打开、读写还是关闭 |
| `path_class` | `db` / `cache` / `config` / `media` | 脱敏后的路径分类，支持后台聚合 |
| `path_hash` | SHA-256 截断值 | 同一文件聚合，不暴露原始路径 |
| `thread` | `main` / `RenderThread` / business thread | 判断是否影响交互线程 |
| `duration_ms` | 12.4 | 单次调用耗时 |
| `continuous_ms` | 96.0 | 连续读写耗时，用于识别一次性读完整文件 |
| `bytes` | 614400 | 读写数据量 |
| `buffer_size` | 4096 | 判断小 buffer 高频系统调用 |
| `callsite_id` | 调用栈哈希 | 聚合同一代码位置 |
| `scene` | startup / foreground / background | 区分启动、前台交互和后台维护 |

## 不良 I/O 规则模板

I/O 规则不要写死一个全局阈值。低端机、慢闪存、冷启动、前台交互、后台同步面对的成本不同；阈值应该按设备档位、场景和采样成本分层。

| 规则 | 默认触发条件 | 上报字段 | 调整口径 | 处理方向 |
|---|---|---|---|---|
| 主线程 I/O | `thread=main` 且 `continuous_ms >= 100` | 路径分类、调用栈指纹、CPU/内存水位、前后台状态 | 启动阶段可降到 50ms；后台恢复可放宽 | 移出主线程、预读、延迟写、批量提交 |
| 小 buffer 高频读写 | `buffer_size < block_size` 且 read/write 次数 >= 5 | buffer 大小、调用次数、累计字节、文件类型 | `/data` 常见 block size 为 4KB，实际以 `StatFs.getBlockSizeLong()` 采集 | 用 `BufferedInputStream`、Okio buffer、批量读写 |
| 重复读 | 同一 `path_hash + callsite_id` 短时间读 >= 3 次，期间无写入 | 读取次数、内容长度、调用栈指纹 | 配置文件、AB 参数、设备信息读取可降低阈值 | 加进程内缓存或启动阶段统一加载 |
| 目录遍历过重 | 单次目录扫描文件数 >= 1000 或耗时 >= 100ms | 目录分类、文件数、最大子目录、耗时 | 媒体类 App 单独建档位；缓存目录看文件年龄 | 分页、索引、增量扫描、后台清理 |
| fd / Cursor 泄漏 | fd 数持续升高或资源对象超过生命周期未关闭 | 资源类型、创建栈、存活时长、进程 fd 数 | Debug 包可严格；Release 只采样告警 | `use` / try-with-resources、生命周期绑定 |

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 14.md]

资源泄漏的官方入口是 StrictMode。`StrictMode.VmPolicy.Builder` 提供 `detectLeakedClosableObjects()`、`detectLeakedSqlLiteObjects()` 等检测能力，适合 debug、灰度和自动化测试。线上如果要替换 `CloseGuard` reporter，必须按隐藏 API 风险处理；Android 版本、targetSdk、灰度比例和异常兜底都要先验证。 [已验证: 官方文档, developer.android.com/reference/android/os/StrictMode] [已验证: AOSP master, libcore/dalvik/src/main/java/dalvik/system/CloseGuard.java]

这些规则的后台聚合维度建议固定成四组：`app_version + device_tier + scene + callsite_id`。先看同一调用点是否在多个版本稳定出现，再看是否集中在某类设备；不要把偶发慢 I/O 直接推给业务方。

## SQLite 耗时、损坏与查询计划

数据库事件要拆成慢查询、锁等待、损坏和空间问题四类。慢查询关注 SQL 与索引；锁等待关注并发和事务；损坏关注恢复链路；空间问题关注 WAL、临时文件和业务表膨胀。

| 事件 | 触发条件 | 关键字段 | 线下复核 |
|---|---|---|---|
| `sqlite_query_slow` | 查询或写入超过阈值 | SQL 指纹、耗时、调用栈、表名集合、线程、是否事务内 | `sqlite3` + `EXPLAIN QUERY PLAN` |
| `sqlite_transaction_slow` | 事务持续时间超过阈值 | 事务类型、SQL 数量、写入行数、持有线程 | Perfetto sched + 应用 trace |
| `sqlite_busy_locked` | busy / locked / retry | 数据库别名、线程、事务状态、重试次数、等待时长 | WAL 状态、连接池、调用栈 |
| `sqlite_corrupt` | `SQLiteDatabaseCorruptException` 或校验失败 | 数据库别名、大小、WAL/SHM 是否存在、恢复动作 | 备份恢复、导出修复、重建策略 |
| `sqlite_disk_full` | 写入失败且空间不足 | 剩余空间、数据库大小、WAL 大小、缓存大小 | 空间清理策略 |

Android 官方 SQLite 性能文档建议在目标设备上用 `adb shell sqlite3` 运行查询计划，避免桌面 SQLite 与设备 SQLite 行为差异影响判断。`EXPLAIN QUERY PLAN` 输出能区分 `SCAN` 和 `SEARCH ... USING INDEX`，用来确认查询有没有走索引。 [已验证: 官方文档, developer.android.com/topic/performance/sqlite-performance-best-practices] [已验证: 官方文档, sqlite.org/eqp.html]

下面这段命令用于验证慢查询是否走索引。重点看输出里是 `SCAN` 还是 `SEARCH ... USING INDEX`。

```sql
EXPLAIN QUERY PLAN
SELECT id, name
FROM message
WHERE conversation_id = ?
  AND create_time >= ?
ORDER BY create_time DESC
LIMIT 50;
```

如果输出是 `SCAN message`，线上慢查询事件里的 `sql_fingerprint`、表名和调用栈就能直接指向索引缺失或查询写法问题；如果输出已经使用复合索引，下一步再看结果集大小、排序、事务持有时间和设备 I/O 状态。

Room 工程可先打开 `RoomDatabase.Builder#setQueryCallback()` 采集 SQL 文本和绑定参数个数，参数值不要上传。这个回调能告诉端上“执行了哪条 SQL”，但不自带耗时统计；耗时需要在 DAO 层、数据库封装层或自定义 driver 周围补计时。 [已验证: 官方文档, developer.android.com/reference/androidx/room/RoomDatabase.QueryCallback]

使用 AndroidX SQLite 的工程还要跟踪版本差异。AndroidX SQLite release notes 已记录 BundledSQLiteDriver 的 JNI 性能优化，以及连接启用 extended error codes 的变化。线上事件里保留 `androidx_sqlite_version`、driver 类型和错误码，后续才能区分系统 SQLite、BundledSQLiteDriver、Room 版本升级带来的行为差异。 [已验证: 官方文档, developer.android.com/jetpack/androidx/releases/sqlite]

Matrix SQLiteLint 提供另一条路径：运行时收集 SQL、表结构和执行信息，再用规则识别 `SELECT *`、索引使用不当等问题。它适合做智能诊断和灰度验证，但接入前要评估 Hook 覆盖、AGP 版本、SQL 参数脱敏、误报处理和上报体积。 [引用: https://github.com/Tencent/matrix/wiki/Matrix-Android-SQLiteLint]

## 存储容量与文件损坏指标

存储容量监控不应该只报一个目录总大小。线上排查需要知道是哪类目录、哪类文件、哪一代版本开始膨胀，以及清理策略是否生效。

| 指标 | 采集方式 | 聚合用途 | 边界 |
|---|---|---|---|
| 应用私有目录总大小 | 周期性扫描 `files/cache/databases/no_backup` 分类 | 发现 ROM 异常率 | 扫描要限频，前台交互时避开 |
| 文件总数 | 目录树遍历计数 | 识别小文件爆炸和目录遍历 ANR 风险 | 大目录用分批扫描 |
| Top-K 目录 | 每层保留最大 N 个子目录 | 后台定位膨胀来源 | 只上传分类名和哈希 |
| Top-K 文件 | 保留最大 N 个文件 + 随机样本 | 避免只看到固定大文件 | 文件名脱敏，媒体内容不上传 |
| 文件年龄分布 | mtime / ctime 分桶 | 判断清理策略是否覆盖历史残留 | 厂商文件系统时间戳可能异常 |
| 损坏率 | header、长度、CRC、业务 magic 校验 | 评估存储模块可靠性 | 校验逻辑必须随文件格式版本演进 |
| 清理结果 | 清理规则、删除大小、失败原因 | 验证远程清理策略 | 删除动作必须可回滚或只作用于可再生缓存 |

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 16.md]

目录树上报建议用“剪枝 + 随机样本”。每层只保留最大的几个子目录，再随机保留少量文件样本。这样既能定位常见膨胀来源，又不把用户的完整文件结构上传到后台。用户投诉或专项灰度时，再通过远程调试开关拉取更细的证据包，且必须受账号、时长、采样率和隐私策略限制。

文件损坏要按业务格式采集。简单缓存文件可以用长度和 magic header；配置、索引、数据库旁路文件要增加版本号、CRC 或 hash；关键数据写入时采用临时文件、`fsync(fd)`、同卷 `rename`、父目录 `fsync` 的协议，损坏事件里记录上一次写入阶段。这里不展开写入协议实现，相关稳定性链路可回到 20.7 和 24.1。

## 上报、采样与隐私边界

存储可观测性的上报量容易失控。I/O 调用频率高，SQL 执行频率高，目录树也可能很大；采集策略要从第一天就按预算设计。

| 数据 | 上报策略 | 隐私处理 | 降级策略 |
|---|---|---|---|
| I/O 单次事件 | 只上报规则命中和慢调用，普通事件本地滚动缓存 | 路径分类 + 哈希，调用栈符号化后只保留应用帧 | 弱网只保留计数；后台态延迟上报 |
| SQL 事件 | 慢查询、异常、采样查询 | SQL 归一化，参数值丢弃或只保留类型 | 只上报指纹、耗时和表名集合 |
| 目录树 | 周期低频 + 用户投诉触发 | 文件名哈希，目录按业务分类 | 只保留 Top-K 和文件数分布 |
| 损坏事件 | 必报但限速 | 不上传文件内容 | 同一文件同一版本合并 |
| 资源泄漏 | Debug / 灰度高采样，Release 低采样 | 调用栈裁剪到应用包名 | fd 水位异常时再打开详细采集 |

端侧还要给采集 SDK 做自监控：采集耗时、上报队列长度、本地缓存大小、丢弃条数、压缩后包体大小、上传失败原因。存储监控本身也会写文件、读文件、占用线程；如果没有自监控，很容易让诊断工具变成新的性能问题。详见 26.3。

## 与现有章节的分工

本节只保留线上诊断字段和规则模板，具体优化动作回到对应章节：

- 文件 I/O 优化详见 24.1：主线程 I/O、SharedPreferences、MMKV、线程安全、文件读写策略都在那里展开。
- SQLite/Room 性能优化详见 24.2：WAL、连接池、索引、事务、Room 使用方式在那里展开。
- MediaStore 和外部媒体扫描详见 24.12：媒体库访问、FUSE、Scoped Storage、缩略图成本不在本节重复写。
- 指标采集、P90/P99、劣化检测详见 26.3：本节只给存储类字段，不重新设计上报框架。
- 线上排查流程详见 26.5：证据包、远程日志、灰度隔离在那里展开。

## 扩展：Matrix I/O Canary 与 SQLiteLint

Matrix 的两个模块适合当成结构参考，不适合不经验证直接放进现代工程。

| 模块 | 能力 | 接入前检查 | 常见误报 |
|---|---|---|---|
| I/O Canary | 文件 I/O Hook、主线程 I/O、小 buffer、重复读、泄漏规则 | Android 版本、ABI、Hook 稳定性、采样开关、AGP 版本 | 启动阶段不可避免的短 I/O、业务主动预热 |
| SQLiteLint | SQL 执行信息、表结构、规则诊断 | SQL 参数脱敏、Room/WCDB/系统 SQLite 覆盖、Hook 风险 | 小表全表扫描、一次性迁移 SQL、后台维护任务 |

建议先在 debug 和 dogfood 包打开全量规则，再把线上规则收敛成“慢调用 + 高频调用点 + 异常”三类。规则上线后看三个指标：命中量是否可控、调用栈是否能归因、修复后指标是否下降。只会报警但不能指导修复的规则，要么补字段，要么下线。

## 扩展：AndroidX SQLite/Room 新版本诊断能力

Room 和 AndroidX SQLite 的诊断能力在持续变化，章节维护时至少跟踪三类信息：

- Room release notes：`setQueryCallback()`、KSP、schema 导出、AutoMigration、查询验证行为变化会影响 SQL 采集和本地复现。
- AndroidX SQLite release notes：BundledSQLiteDriver、extended error codes、JNI 调用优化会影响错误归因和性能基线。
- 系统 SQLite 差异：不同 Android 版本、不同厂商系统的 SQLite 编译选项和默认行为可能不同；关键结论要在目标设备上用 `adb shell sqlite3` 或应用内复现验证。

[待补充] Room 3.x 多平台能力与 Android 17 系统 SQLite 版本差异需要下一轮跟踪官方 release notes 和 AOSP tag。

## 扩展：Perfetto 文件系统 trace 与线上指标对照

线上事件只能告诉后台“哪个调用点慢”。Perfetto 用来解释“为什么慢”。一次复现建议同时打开应用自定义 trace、sched、freq、binder、文件系统或 block 相关数据源，再把线上事件里的 `callsite_id` 映射到 trace marker。

| 线上字段 | Perfetto 对照 | 判断 |
|---|---|---|
| `thread=main` + `continuous_ms` 高 | 主线程 slice、sched runnable/blocked | 区分 CPU 忙、I/O 等待和锁等待 |
| `buffer_size` 小 + 调用次数高 | 系统调用密集、线程频繁唤醒 | 判断是否需要 buffer 合并 |
| `sqlite_transaction_slow` | 应用 trace + sched + binder | 判断事务持有期间是否被其他工作打断 |
| `storage_tree_snapshot` 文件数高 | 目录扫描 trace、主线程卡顿 | 判断遍历是否影响交互 |

[自动发现] Android 15+ 的 `ProfilingManager` 和 Android 16+ 的触发式 profiling 可以把线下 Perfetto 能力往线上受控迁移，但采集频率、用户授权、rate limiter 和结果文件生命周期要按 26.12 的版本边界处理，不要在本节重复展开。

## AIW 源码调研：Android 17 SQLite 可观测性实现机制（2026-06-14）

<!-- AIW-源码调研-2026-06-14 -->

### 核心发现：三层可观测性架构

通过 AOSP 源码分析，Android 17 SQLite 可观测性通过三层机制实现：

1. **Connection 层执行追踪**：SQLiteConnection.OperationLog 提供 20 条环形缓冲区设计，自动记录最近操作和长操作（>2秒）
2. **Pool 层性能监控**：SQLiteConnectionPool 提供 StatementCache 命中率追踪，mTotalPrepareStatements vs mTotalPrepareStatementCacheMiss
3. **系统级资源检测**：BlockGuard + StrictMode 实现磁盘 IO 检测和 SQLite 对象泄露检测

### 关键源码机制

#### OperationLog 三级缓冲设计
```java
// frameworks/base/core/java/android/database/sqlite/SQLiteConnection.java L1650
private final class OperationLog {
    private static final int MAX_RECENT_OPERATIONS = 20;  // 最近操作数量限制
    private static final long LONG_OPERATION_THRESHOLD_MS = 2_000;  // 长操作阈值
}
```

#### StatementCache 命中率统计
```java
// frameworks/base/core/java/android/database/sqlite/SQLiteConnectionPool.java L1247
public double getStatementCacheMissRate() {
    if (mTotalPrepareStatements == 0) return 0;
    return (double) mTotalPrepareStatementCacheMiss / (double) mTotalPrepareStatements;
}
```

#### SlowQuery 动态阈值控制
```java
// frameworks/base/core/java/android/database/sqlite/SQLiteDebug.java
public static boolean shouldLogSlowQuery(long elapsedTimeMillis) {
    final int slowQueryMillis = Math.min(
        SystemProperties.getInt(NoPreloadHolder.SLOW_QUERY_THRESHOLD_PROP, Integer.MAX_VALUE),
        SystemProperties.getInt(NoPreloadHolder.SLOW_QUERY_THRESHOLD_UID_PROP, Integer.MAX_VALUE));
    return elapsedTimeMillis >= slowQueryMillis;
}
```

### Android 17 演进特性

- **WAL 自动检查点**：SQLiteCompatibilityWalFlags 全局配置管理，平衡性能和空间
- **Idle 连接池超时**：SQLiteConnectionPool.getIdleConnectionTimeout() 默认 60s，可动态配置
- **StrictMode 增强检测**：新增 detectResourceMismatches() 资源类型不匹配检测

### 实际应用建议

1. **长列表场景**：启用 StatementCache，设置合理的 maxCacheSize（默认 50）
2. **内存受限设备**：禁用 lookaside pool，使用 setLookasideConfig(0, 0)
3. **慢查询监控**：动态配置 db.log.slow_query_threshold 实现分 UID 阈值控制
4. **连接池优化**：设置合理的 idleConnectionTimeout 平衡性能和内存使用

本结论基于 AOSP 源码 frameworks/base/core/java/android/database/sqlite/ 中的关键实现，为 Matrix SDK 提供了可直接落地的性能监控指标采集方案。





## 参考资料

### Android 17 SQLite 性能可观测性与 IO 监测核心机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-14-android17-sqlite-performance-observability-io-monitoring.md
- 类型：DeepResearch 调研结果
- 摘要：Android 17 SQLite 性能可观测性三层机制源码分析：Connection 层 OperationLog 20 条环形缓冲区 + 2 秒慢查询阈值自动归类；Pool 层 StatementCache 命中率追踪与动态内存池配置；系统级 BlockGuard/StrictMode 检测 IO 操作与 SQLite 对象泄露。涵盖 SQLiteDebug 动态阈值（全局/UID 级别）、WAL 自动检查点配置、SQLiteOpenHelper OpenParams 优化选项（lookaside/idle connection timeout/WAL）。
- 注入时间：2026-06-14
- 价值：为本节 SQLite 可观测性内容提供 AOSP 源码级支撑，OperationLog 环形缓冲区设计与 StatementCache 命中率监控可直接落地为端侧采集方案

## 小结

存储可观测性的关键产物不是更多日志，而是一套能稳定聚合的字段：I/O 事件、SQLite 事件、目录树、损坏率、资源泄漏和采集 SDK 自监控。端上先按规则筛选，后台按调用点和设备档位聚合，线下再用 Perfetto 与 `EXPLAIN QUERY PLAN` 复核。

本节状态可以进入评审。后续评审重点建议放在三处：Matrix 在 AGP 8+ 工程的接入边界、AndroidX SQLite extended error codes 的版本口径、以及 Android 15/16 profiling 能力是否需要从 26.12 回连到本节。
