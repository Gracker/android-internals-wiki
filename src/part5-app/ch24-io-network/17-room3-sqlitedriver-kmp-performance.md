---
title: "Room 3.0 与 SQLiteDriver 迁移性能边界"
chapter: "24.17"
section: "24.17"
status: "finalized"
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); Room 3.0.0-rc01"
last_verified: "2026-06-21"
last_verified_against: "AndroidX Room3 3.0.0-rc01 release notes + androidx.sqlite API reference + Android Developers performance docs"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/room3"
  - type: official
    path: "https://android-developers.googleblog.com/2026/03/room-30-modernizing-room.html"
  - type: official
    path: "https://developer.android.com/reference/androidx/room3/RoomDatabase.Builder"
  - type: official
    path: "https://developer.android.com/reference/androidx/sqlite/SQLiteConnection"
  - type: official
    path: "https://developer.android.com/reference/androidx/sqlite/SQLiteStatement"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/reference/android/os/StrictMode"
  - type: official
    path: "https://developer.android.com/topic/performance/inspecting-overview"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: daily-info
    path: "intake/daily-info/2026-05-22.md"
tags: [room3, sqlite, sqlitedriver, kmp, ksp, database-performance]
related_chapters: ["14.1", "19.14", "24.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task2b_result: "fixed-lite"
last_task2b_lite_at: "2026-06-01"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-21"
last_task6_review_log: "logs/review/2026-06-21-08-review.md"
last_task6_at: "2026-06-21T08:09:43+08:00"
task6_result: "pass-light-edit"
task6_l1_l2_fixes: 2
task6_l3_l4_issues: 0
review_type: "task6-writing-quality-review"
last_task9_at: "2026-06-21T05:26:42+08:00"
last_task9_review_log: "logs/deep-review/2026-06-21-05-audit.md"
task9_p0_issues: 0
task9_p1_issues: 1
task9_reviewed_date: "2026-06-21"
task9_reviewed_by: "openclaw-task9"
task9_review_notes: "2026-06-21 Task9 idle audit: auto-fixed。官方 Room 3.0 release notes 已到 3.0.0-rc01；补齐 alpha06/rc01 版本边界、converter 命名变化和 WITHOUT ROWID 迁移影响；回到 Task6 复审。"
task9_p2_issues: 0
last_task9_audit: "2026-06-21"
last_task9_autofix_at: "2026-06-21"
task6_new_rework: false
task6_review_notes: "2026-06-21 Task6 复审（revisiting→reviewed）：L1 小修 1 处（「落到」→「在…明确」），锚点 7/7 覆盖，无 L3/L4 回炉项。Task9 auto-fixed 已完成，queue 无 pending，自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
---

# 24.17 Room 3.0 与 SQLiteDriver 迁移性能边界

Room 3.0 改变了包名、数据库驱动、代码生成器和异步接口。迁移工作因此不能只改依赖版本，还要检查运行期数据库 I/O、KSP 与 schema 输出、旧 `SupportSQLite` 扩展点，以及数据库升级后的应用降级能力。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，依赖基线为 Room 3.0.1 与 SQLite 2.7.0。`AndroidSQLiteDriver` 使用 Android 17 平台 SQLite；`BundledSQLiteDriver` 使用随库发布的原生 SQLite，两者不能共用一套未经实测的性能结论。分析不涉及内核接口，因此没有内核源码锚点。SQLite 锁、WAL、CursorWindow、Room 2.x 线程模型、ANR 观察、查询、索引和事务优化统一见 24.2 节；Profiler 与 Perfetto 的使用详见 14.1 节。

## Room 3.0 的变化边界

截至 2026-07-29，Room 的稳定版是 3.0.1。3.0.0 于 2026-07-01 发布，3.0.1 修复了注解处理期间多余的标准输出，以及一个数据库的事务中混入另一个数据库操作时可能出现的未定义行为。SQLite 驱动库的稳定版是 2.7.0。版本号要分别声明，不能因为二者同属 AndroidX 就假设它们同步递增。

Room 3 保留 `@Database`、`@Entity`、`@Dao` 和 `@Query` 这些核心注解，破坏性变化集中在运行期接口与编译链：

| 维度 | Room 2.x 常见用法 | Room 3.0.1 | 迁移检查 |
| --- | --- | --- | --- |
| 包名与 Maven 坐标 | `androidx.room:*` | `androidx.room3:room3-*` | 更新依赖和导入；排查反射类名与混淆规则 |
| SQLite 接口 | `SupportSQLiteDatabase`、`Cursor` | `SQLiteDriver`、`SQLiteConnection`、`SQLiteStatement` | 替换直接查询、回调和迁移签名 |
| 代码生成 | KAPT、Java 注解处理器或 KSP | 只支持 KSP，生成 Kotlin | 数据模块需要 Kotlin 插件与 KSP |
| DAO 调用 | 同步、Executor、协程并存 | 数据库操作采用协程接口 | DAO 应为 `suspend`，或返回 `Flow` 等响应式类型 |
| 失效通知 | `InvalidationTracker.Observer` | `InvalidationTracker.createFlow()` | 将观察者的注册与注销改为 Flow 收集 |
| 多平台 | Android 为主 | Android、Apple、JVM、JS、WasmJS | 各平台驱动分别验证，不能复用 Android 耗时数据 |

Room 3 只生成 Kotlin，但 KSP 仍可处理 Java 编写的数据库、DAO 和实体声明。Java 调用方可以继续调用生成代码；包含这些声明的模块仍须启用 Kotlin 编译器和 KSP。官方建议把 Room 使用集中在少量数据模块中，避免无关业务模块增加 KSP 配置与增量编译成本。

`androidx.room` 与 `androidx.room3` 包名不同，Room 2.x 和 Room 3 可以出现在同一依赖图中。这项设计主要解决 WorkManager 等库传递依赖旧版 Room 时的类冲突。它不表示两个 Room 实例可以同时操作同一个数据库文件；应用数据库仍需明确唯一的打开者、schema 版本与升级顺序。

这些边界来自 [Room 3.0.1 发布说明](https://developer.android.com/jetpack/androidx/releases/room3) 和 [Room 3 迁移说明](https://developer.android.com/blog/posts/modernizing-the-room)。版本升级时还应查看 3.0.1 对应提交 `4762f876` 下的 [AndroidX Room 3 源码](https://android.googlesource.com/platform/frameworks/support/+/4762f876f4d43c4c8853d8887f9b110fe25777e6/room3/)。

## 先固定依赖与 schema 输出

下面的配置用于建立 Room 3.0.1、SQLite 2.7.0、KSP 和 schema 导出的最小基线。`androidx.room3` 插件版本应在根工程统一声明；示例假定插件管理已经完成。

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

这里选择了 `sqlite-framework`，对应 `AndroidSQLiteDriver`。如果应用决定使用 `BundledSQLiteDriver`，应把这一项替换为 `androidx.sqlite:sqlite-bundled:2.7.0`。同时引入两个实现没有性能收益，还容易让不同模块选择不同引擎。

使用 Room Gradle Plugin 时，`schemaDirectory` 是必填项。带构建变体的工程会写入类似 `schemas/flavorOneDebug/<数据库类名>/<版本>.json` 的目录。schema JSON 是自动迁移与迁移测试的输入，应提交到仓库，并由 CI 检查是否存在未提交的变化。它不属于可以随构建目录清理的临时文件。

构建性能需要分开观察：

| 场景 | 修改内容 | 需要观察的任务 |
| --- | --- | --- |
| 完整构建 | 清理全部输出后编译 | Room compiler、KSP、Kotlin compile 的耗时 |
| DAO 增量构建 | 修改 SQL 或返回类型 | 受影响模块、schema 输出与下游 Kotlin 编译 |
| Entity 增量构建 | 修改列或索引 | schema 变化、自动迁移检查与依赖模块重编译 |
| 普通 Kotlin 增量构建 | 修改无关业务代码 | KSP 是否被无关修改触发 |
| 远端构建缓存 | 相同提交重复构建 | KSP 与 schema 任务是否命中缓存 |

编译速度的结论要来自同一 Gradle、JDK、Kotlin、KSP 配置和相同缓存条件。只比较一次本地构建，无法区分代码生成变化与缓存冷热造成的差异。

## Android 17 上两种驱动的边界

Android 应用可以在构建数据库时选择平台驱动或随库驱动。下面的代码用于指定 `AndroidSQLiteDriver`，让 Room 通过 Android 17 平台的 `SQLiteDatabase` 打开数据库。

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

`RoomDatabase.Builder` 没有配置查询协程上下文时会使用自身默认配置；如果应用调用 `setQueryCoroutineContext(...)`，传入的协程上下文必须包含 `CoroutineDispatcher`。不要用这项设置掩盖 DAO 内的长事务或慢查询。

两种 Android 驱动的差异如下：

| 项目 | `AndroidSQLiteDriver` | `BundledSQLiteDriver` |
| --- | --- | --- |
| 依赖 | `androidx.sqlite:sqlite-framework:2.7.0` | `androidx.sqlite:sqlite-bundled:2.7.0` |
| SQLite 引擎 | Android 系统提供 | AndroidX 随库携带的原生 SQLite |
| 版本一致性 | 随系统版本变化 | 各受支持平台更一致 |
| 连接池 | 驱动内部已有连接池 | 驱动本身没有连接池 |
| 线程约束 | 打开的连接可用于多线程并发环境 | 默认按 SQLite multithread 模式编译，单个连接不可被多个线程同时使用 |
| 工程代价 | 不增加一份 SQLite 原生库 | 增加原生库体积和装载工作 |
| 适用判断 | Android 专用应用可优先评估 | KMP 或需要一致 SQLite 特性时优先评估 |

`AndroidSQLiteDriver.hasConnectionPool` 返回 `true`，其 `open()` 调用 `SQLiteDatabase.openOrCreateDatabase()`。因此 Room 的 `setSingleConnectionPool()` 和 `setMultipleConnectionPool()` 对它不生效。Android 17 上的平台实现可从 [`SQLiteDatabase.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteDatabase.java) 与 [`SQLiteConnectionPool.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/database/sqlite/SQLiteConnectionPool.java) 继续追踪。

`BundledSQLiteDriver.hasConnectionPool` 返回 `false`，Room 才会应用自己的连接池配置。没有显式配置时，Room 对 `TRUNCATE` 使用单连接，对 `WRITE_AHEAD_LOGGING` 使用四个读连接和一个写连接；内存数据库始终使用单连接。多个写连接可能返回 `SQLITE_BUSY`，调用方要处理错误，并依据业务验证是否配置 `busy_timeout`。不能把连接数增加等同于吞吐提升。

上述判断可在 3.0.1 源码中核对：

- [`RoomDatabase.kt`](https://android.googlesource.com/platform/frameworks/support/+/4762f876f4d43c4c8853d8887f9b110fe25777e6/room3/room3-runtime/src/commonMain/kotlin/androidx/room3/RoomDatabase.kt) 定义连接池配置及其生效条件。
- [`AndroidSQLiteDriver.android.kt`](https://android.googlesource.com/platform/frameworks/support/+/4762f876f4d43c4c8853d8887f9b110fe25777e6/sqlite/sqlite-framework/src/androidMain/kotlin/androidx/sqlite/driver/AndroidSQLiteDriver.android.kt) 声明驱动内部已有连接池。
- [`BundledSQLiteDriver.jvmAndAndroid.kt`](https://android.googlesource.com/platform/frameworks/support/+/4762f876f4d43c4c8853d8887f9b110fe25777e6/sqlite/sqlite-bundled/src/jvmAndAndroidMain/kotlin/androidx/sqlite/driver/bundled/BundledSQLiteDriver.jvmAndAndroid.kt) 声明驱动没有连接池，并记录单连接的线程限制。

官方 KMP 指南推荐 `BundledSQLiteDriver`，理由是各平台获得较新且一致的 SQLite 版本。这是兼容性建议，不是 Android 查询性能排名。Android 专用应用应在相同数据库、journal 模式、设备和构建类型下比较两种驱动，再决定是否接受原生库体积与初始化代价。

## 直接查询要使用 PooledConnection API

Room 3 的公开连接接口分为两层。`SQLiteConnection.prepare()` 属于底层驱动连接；`RoomDatabase.useReaderConnection()` 传给调用方的是 `Transactor`，它继承 `PooledConnection`。这里应调用 `usePrepared()`，由连接池管理预编译语句的释放。

下面的函数用于演示 Room 3 中一次带参数的只读查询。它假定 `users.name` 为非空列。

```kotlin
suspend fun findUserName(
    db: AppDatabase,
    userId: Long
): String? = db.useReaderConnection { connection ->
    connection.usePrepared(
        "SELECT name FROM users WHERE id = ?"
    ) { statement ->
        statement.bindLong(1, userId)
        if (statement.step()) {
            statement.getText(0)
        } else {
            null
        }
    }
}
```

`connection` 和 `statement` 都不能从代码块中返回或保存到成员变量。Room 把连接限制在对应协程中；预编译语句使用期间连接也处于占用状态。网络请求、JSON 解析和大段业务计算应放在连接代码块之外。等待连接超过内部期限时，API 会抛出 `SQLiteException`，这类错误需要进入稳定性监控。

参数通过 `bindLong()` 写入，避免字符串拼接带来的注入风险与 SQL 文本变化。查询是否快仍由索引、数据分布、返回列、事务范围和磁盘状态决定。驱动接口不会替应用修正查询计划，也不会改变 SQLite 写入串行化的约束。

Room 3.0.1 还修复了跨数据库事务混用问题。即使使用该版本，也不应在数据库 A 的 `withWriteTransaction` 中调用数据库 B，并依赖某个隐含的事务顺序。多个数据库需要显式规定调用顺序；跨库原子性要由业务协议处理，SQLite 的单库事务不能提供跨库提交。

`usePrepared()` 的声明及协程限制可查看 [`Transactor.kt`](https://android.googlesource.com/platform/frameworks/support/+/4762f876f4d43c4c8853d8887f9b110fe25777e6/room3/room3-runtime/src/commonMain/kotlin/androidx/room3/Transactor.kt) 与 [`RoomDatabase.kt`](https://android.googlesource.com/platform/frameworks/support/+/4762f876f4d43c4c8853d8887f9b110fe25777e6/room3/room3-runtime/src/commonMain/kotlin/androidx/room3/RoomDatabase.kt)。

## SupportSQLite 兼容包装层

Room 3 移除了 `SupportSQLiteDatabase`、`SupportSQLiteOpenHelper` 和 Android `Cursor` 相关的 Room 接口。`androidx.room3:room3-sqlite-wrapper:3.0.1` 提供迁移期兼容能力，可用 `roomDatabase.getSupportWrapper()` 取得 `SupportSQLiteDatabase`。

兼容包装层适合调用频率低、改造范围清楚的旧接口：

| 旧代码 | 建议 |
| --- | --- |
| 调试面板、一次性导出、短期诊断 | 可暂用 `getSupportWrapper()`，并记录删除条件 |
| `Migration`、`Callback` 接收 `SupportSQLiteDatabase` | 改为 Room 3 的 `SQLiteConnection` 参数 |
| 高频业务查询、批量写入 | 改为 DAO，必要时使用 `useReaderConnection()` 或 `useWriterConnection()` |
| 第三方库只接受 `SupportSQLiteDatabase` | 放入独立适配模块，限制调用入口 |

不要把 `getSupportWrapper()` 放入全局数据库工具类供新代码调用。这样会继续扩大旧接口的使用范围，也会让连接与预编译语句的生命周期难以审查。官方的替换范围见 [Room 3.0.1 发布说明](https://developer.android.com/jetpack/androidx/releases/room3#3.0.0)。

## schema 迁移与应用回退

数据库升级需要覆盖每个仍受支持的来源版本。`MigrationTestHelper` 应从每个来源 schema 创建数据库，写入能触发约束和类型转换的代表数据，再执行到当前版本的完整迁移链。只测试“前一版到当前版”会遗漏长期未升级用户走过的路径。

迁移验收至少包括：

- schema identity hash 与导出的 JSON 一致。
- 新增非空列、默认值、索引、外键和触发器符合设计。
- `WITHOUT ROWID`、FTS5、复合关系键等新特性有独立迁移用例。
- 大数据集上的建索引、表重建和数据回填耗时可接受。
- 迁移中断后再次打开数据库不会得到半完成的业务状态。
- 3.0.1 修复涉及的跨数据库调用有回归测试。

回退应用版本比回退 Maven 依赖更难。新版本一旦把设备上的 schema 从版本 N 升到 N+1，旧应用必须能识别 N+1，或提供经过验证的降级迁移。远程开关只能阻止新功能继续使用数据库，不能自动还原已经写入的 schema。

`fallbackToDestructiveMigrationOnDowngrade()` 会删除数据后重建表，只适用于明确允许丢失的数据库。用户内容、离线草稿、认证材料等数据不能把破坏性降级当作发布保障。更可靠的做法是让旧应用在灰度期兼容新 schema，或把不可逆 schema 变化安排在确认无需二进制回退的版本。

Room 2.x 与 Room 3 的包可以共存，但迁移同一个数据库文件时仍应只有一个版本负责打开。发版前要执行“旧版本写入 → 新版本迁移并读写 → 旧版本重新打开”的测试，结果按数据类型逐项核对。

## 性能验证要回答什么

数据库迁移的性能验收应区分应用启动、数据库打开、迁移、首个查询和稳定运行期查询。`StartupTimingMetric` 只能给出应用启动指标，不能单独证明数据库打开变快。需要在应用中为建库、首次触发打开、每段迁移和首个关键 DAO 查询添加自定义 trace，再用 Macrobenchmark 触发固定场景。

| 问题 | 量测方式 | 解释限制 |
| --- | --- | --- |
| 数据库是否进入启动关键路径 | 冷启动 Macrobenchmark + 自定义 trace | 应同时记录进程状态、启动入口和数据集 |
| 首次打开与迁移耗时 | 迁移回调、首次 DAO 查询 trace | `build()` 可能尚未触发数据库 I/O，不能只围住 builder |
| 查询与事务是否回归 | 固定数据集的 DAO 基准与查询计划 | 平均值会隐藏长尾，分位数由项目基线决定 |
| 连接等待是否增加 | Perfetto 调度、I/O、锁事件与应用 trace | CPU 占用低不代表没有等待 |
| 是否发生主线程磁盘访问 | StrictMode 与调用栈 | StrictMode 用于诊断，不是性能基准 |
| KSP 是否扩大重编译范围 | Gradle Build Scan 或 CI 任务时间 | 要固定缓存、JDK、Gradle 与机器条件 |

Profiler 适合交互式定位，Perfetto 适合把线程调度、文件 I/O、锁等待和应用 trace 放到同一时间轴。二者都不能代替 `EXPLAIN QUERY PLAN`、索引检查和真实数据分布分析。看到数据库线程处于 sleeping 状态时，还要结合连接等待、锁与 I/O 判断，不能只看 CPU 火焰图。

测试数据应覆盖空库、常见规模和大规模数据库，并记录表行数、索引、数据库与 WAL 文件大小、设备、Android 版本、驱动、journal 模式、Room 版本、构建类型以及 R8 和 Baseline Profile 状态。迭代次数、分位数和门槛应由线上分布与性能预算决定，不设脱离业务数据的固定数字。

相关工具的官方入口包括 [Macrobenchmark 概览](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)、[StrictMode API](https://developer.android.com/reference/android/os/StrictMode) 和 [Android 性能检查工具](https://developer.android.com/topic/performance/inspecting-overview)。

## KMP 与 Web/WASM 的独立边界

Room 3 支持 JS 与 WasmJS，SQLite 2.7.0 在 `androidx.sqlite:sqlite-web` 中提供 `WebWorkerSQLiteDriver`。该驱动通过 Web Worker 执行操作，并可使用 OPFS 保存数据库，但库中没有可直接使用的默认 worker；项目需要提供符合其消息协议的实现。

Web 平台的数据库操作是异步接口。只面向非 Web 目标的公共代码可以使用同步 `SQLiteDriver` 接口；同时面向 Web 与非 Web 的公共代码可引入 `androidx.sqlite:sqlite-async:2.7.0`，使用 `androidx.sqlite.async` 包中的顶层挂起函数。只面向 Web 的代码则直接使用 Web 源集接口，不必增加这一层适配。

Android 性能报告只记录 Android 使用的驱动、设备、系统和数据库。Web Worker、OPFS、Apple 平台文件系统和桌面 JVM 的结果应放在各自基线中。共享 DAO 和实体能减少重复代码，却不能消除平台驱动、文件系统与线程模型的差异。

这些限制记录在 [SQLite 2.7.0 发布说明](https://developer.android.com/jetpack/androidx/releases/sqlite#2.7.0) 与 [Room KMP 配置指南](https://developer.android.com/kotlin/multiplatform/room)。

## 版本演进

Room 3 的预发布版本可用于理解 API 来源，正式依赖应固定到已验证的稳定版本：

| 版本 | 主要变化 | 迁移检查 |
| --- | --- | --- |
| 3.0.0-alpha02 | `@Fts5`；`clearAllTables()` 跨平台并改为挂起函数 | 评估 FTS5 索引与现有清库调用 |
| 3.0.0-alpha04 | `setSingleConnectionPool()`、`setMultipleConnectionPool(...)` | 按驱动的 `hasConnectionPool` 判断是否生效 |
| 3.0.0-alpha05 | `@Relation`、`@Junction` 支持复合关系列 | 复核关系查询与 schema |
| 3.0.0-alpha06 | `@Entity.withoutRowId` | 验证主键约束、查询计划和迁移 |
| 3.0.0-rc01 | 查询结果数据类默认值；`@ColumnTypeConverter`；自定义 DAO 返回类型；`PrimaryKey.algorithm` | 更新导入、结果映射和转换器注册 |
| 3.0.0 | 首个稳定版 | 按稳定 API 完成迁移与基准测试 |
| 3.0.1 | 修复处理器输出和跨数据库事务混用问题 | 升级后执行多数据库回归测试 |

`PrimaryKey.Algorithm.ROWID` 允许复用已经删除的整数主键，开销较低；`AUTOINCREMENT` 避免复用，但 SQLite 需要维护额外状态。只有业务协议要求“曾使用过的主键永不再分配”时才应选择 `AUTOINCREMENT`，不能把它当作通用的数据安全选项。

## Room 2.x 到 Room 3.0 迁移清单

- 盘点数据库、DAO、实体、迁移、回调、测试以及直接使用 `SupportSQLite` 的代码。
- 将数据模块切换到 Kotlin、KSP、`androidx.room3` 插件和 Room 3.0.1。
- 配置 `schemaDirectory`，提交所有构建变体的 schema，并让 CI 检查差异。
- 迁移包名、回调参数、同步 DAO、Executor 配置与失效观察者。
- 在 `AndroidSQLiteDriver` 和 `BundledSQLiteDriver` 中选择一个，记录选择依据。
- 只为明确的旧调用点引入 `room3-sqlite-wrapper`，不允许新业务代码使用。
- 从每个受支持的来源版本运行迁移测试，另做应用降级测试。
- 用固定数据集测量启动、打开、迁移、关键查询、批量事务和连接等待。
- 灰度期间观察迁移失败、`SQLiteException`、ANR、数据库损坏报告和关键操作耗时。

## Room、DataStore 与直接 SQLite 的选择

Room 3 没有改变存储工具的职责：

| 场景 | 常用选择 | 判断依据 |
| --- | --- | --- |
| 用户偏好、开关、小量键值数据 | DataStore | 无关系查询与多表事务需求 |
| 关系数据、复杂查询、离线数据 | Room 3 | 有 SQL 校验、迁移、DAO、Flow 或 Paging 需求 |
| 特殊虚表、SQLite 扩展、精细连接控制 | Room 配合驱动 API，或直接 SQLite | 团队能够负责资源管理与迁移测试 |
| KMP 共享数据层 | Room 3 + 各平台驱动 | 共享 schema 和 DAO 的收益高于平台适配成本 |

FTS5、`WITHOUT ROWID` 和自定义返回类型扩大了 Room 3 的适用范围，但每项能力都需要查询计划、文件大小、迁移和设备兼容性验证。选择 Room 3 也不意味着必须使用随库 SQLite；驱动应依据平台覆盖、SQLite 特性与实测结果决定。

## 小结

Room 3.0.1 迁移包含四项独立工作：改用 `androidx.room3` 与 KSP，选择并验证 SQLite 驱动，迁移 `SupportSQLite` 调用，以及建立 schema 升级和应用降级测试。Android 17 上，平台驱动使用系统 `SQLiteDatabase` 及其内部连接池；随库驱动使用独立原生 SQLite，并由 Room 管理连接池。两条路径的版本、线程与体积条件不同，性能结论必须来自相同场景下的测量。

直接访问连接时，应通过 `useReaderConnection()`、`useWriterConnection()` 与 `usePrepared()` 管理资源。查询计划、索引、事务范围和磁盘等待仍决定数据库表现。完成编译和功能测试只是迁移起点，启动、首次打开、迁移、查询、连接等待与二进制回退都要有可重复的验证记录。
