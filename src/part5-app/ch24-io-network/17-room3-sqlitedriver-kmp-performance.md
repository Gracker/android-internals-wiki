---
title: "Room 3.0 与 SQLiteDriver 迁移性能边界"
chapter: "24.17"
section: "24.17"
status: "ready-for-review"
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
related_chapters: ["10.7", "14.1", "19.14", "24.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息"
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task2b_result: "fixed-lite"
last_task2b_lite_at: "2026-06-01"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-01"
last_task6_review_log: "logs/review/2026-06-01-06-review.md"
last_task6_at: "2026-06-01T06:05:00+08:00"
task6_result: "pass-light-edit"
task6_l1_l2_fixes: 1
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
task6_review_notes: "2026-06-01 Task6 06:05：回炉后写作复审；完成 L1/L2 小修 1 处，锚点覆盖完整，未新增 L3/L4 回炉项，送 Task9 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-13
---

# 24.17 Room 3.0 与 SQLiteDriver 迁移性能边界

Room 3.0 不是一次普通依赖升级。它把包名移到 `androidx.room3`，把后端收敛到 `SQLiteDriver`，把编译链路收敛到 KSP，并把数据库操作接口推向协程和 Kotlin Multiplatform。Android App 团队迁移时要分开评估三类成本：运行期数据库 I/O、构建期 schema / KSP 输出、以及旧 `SupportSQLite` 扩展点的替换成本。

本文只处理应用侧迁移动作。SQLite 锁、WAL、CursorWindow、Room 2.x 线程模型和 ANR 观察详见 10.7 节；传统 SQLite / Room 查询、索引和事务优化详见 24.2 节；Profiler 与 Perfetto 工具入口详见 14.1 节。

<!-- outline-start -->
## 要点

### 🔹 Room 3.0 的变化边界
梳理 `androidx.room3` 新坐标、KMP 定位、SQLiteDriver 后端、KSP-only 编译链路和 Kotlin-only 生成代码，把它和 Room 2.x 的 SupportSQLite / KAPT / Java AP 路径区分清楚。

### 🔹 SQLiteDriver 对数据库 I/O 路径的影响
说明 Room 3.0 背后的 `androidx.sqlite` driver API 如何改变打开连接、事务执行、statement 复用和跨平台封装边界，避免把 API 迁移误写成单纯依赖升级。

### 🔹 KSP 与 schema 输出对构建性能的影响
覆盖 Room Gradle Plugin、schemaDirectory、可缓存构建、flavor 维度 schema 输出和 CI 校验，把编译耗时、增量构建和自动迁移验证放在同一个迁移清单里。

### 🔹 SupportSQLite 兼容层的使用策略
说明 `room3-sqlite-wrapper` 只适合迁移期兜底，哪些旧代码可以短期通过 wrapper 适配，哪些数据库访问应该直接迁到 driver API。

### 🔹 迁移前后的性能验证方法
给出查询耗时、事务耗时、主线程 I/O、数据库锁等待、冷启动打开数据库和 schema migration 的验证指标，连接到 Macrobenchmark、Perfetto、StrictMode 和 Android Studio Profiler。

### 🔹 KMP 场景的边界
说明 Android App 团队引入 Room 3.0 时应优先验证 Android 端数据路径；iOS、Desktop、Web/WASM 支持属于架构边界，不应反向污染 Android 端性能结论。

### 🔹 常见风险与回滚策略
整理 alpha 版本引入、KSP 配置缺失、旧 SupportSQLite 扩展点失效、自动迁移 schema 漏提交、DAO Java 源码处理和多模块迁移拆分等风险。

## 扩展

### 🔸 Room 2.x 到 Room 3.0 迁移 checklist
可整理依赖坐标、KSP、Gradle Plugin、schema、driver、wrapper 和测试用例的分步清单。

### 🔸 Room 3.0 与 DataStore / 原生 SQLite 选型
可补充不同数据量、查询复杂度、跨平台需求和启动路径敏感度下的选型边界。

### 🔸 Web/WASM SQLiteDriver 的跨端同步问题
可作为 KMP 扩展材料，讨论 WebWorkerSQLiteDriver 与离线同步策略，不作为 Android 端主线。

<!-- outline-end -->

## Room 3.0 的变化边界

截至 2026-06-21，Room 3.0 最新公开版本是 `3.0.0-rc01`（2026-06-17 发布）。alpha04（2026-05-06）引入 connection pool 配置，alpha05（2026-05-19）新增 `@Relation`/`@Junction` 复合关系键支持，alpha06（2026-06-03）新增 `@Entity.withoutRowId`，rc01 新增 DAO 查询结果 data class 默认值支持，并把 `@TypeConverter` 重命名为 `@ColumnTypeConverter`。本文按 rc01 复核；Room 3.0 仍处预发布阶段，生产接入需固定版本。官方 release notes 把它定义为 Room 2.x 的大版本更新，包名从 `androidx.room` 迁到 `androidx.room3`，Maven 坐标也相应改为 `androidx.room3:room3-*`。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/room3]

迁移评估先看破坏性变化，不看新平台覆盖。Room 3.0 保留 `@Database`、`@Entity`、`@Dao`、`@Query` 这类注解模型，但运行期和编译期的基础设施已经换掉：

| 维度 | Room 2.x 常见路径 | Room 3.0 路径 | 迁移含义 |
| --- | --- | --- | --- |
| 包名与坐标 | `androidx.room:*` | `androidx.room3:room3-*` | import、依赖和传递依赖要分批迁移 |
| 数据库后端 | `SupportSQLite` / Android `Cursor` | `androidx.sqlite` `SQLiteDriver` | 旧 openHelper、raw query、callback 签名要替换 |
| 编译器 | KAPT / Java AP / KSP | KSP only | 模块必须能接入 Kotlin Gradle Plugin 与 KSP |
| 生成代码 | Java 或 Kotlin | Kotlin only | Java-only 模块需要迁移边界或拆模块 |
| 数据库操作 | 同步、Executor、协程混用 | 协程 API 为主 | DAO 执行位置要重新核对 |
| KMP | Android 为主，已有部分 KMP 轨道 | Android、iOS、Desktop、JS、WASM 方向 | 跨端是架构收益，不等于 Android 端自动变快 |

官方文档明确说 Room 3.0 不再支持 `SupportSQLite` API，除非使用 `androidx.room3:room3-sqlite-wrapper`。它还要求使用 KSP，且只生成 Kotlin 代码；Java 源文件可以被 KSP 处理，但编译器输出仍是 Kotlin。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/room3]

迁移边界要落到模块层。数据库定义、DAO、Entity、Migration、Room builder、测试 helper、调试工具代码都要归入同一个迁移包；不要只改 app 模块依赖，让旧 feature 模块继续通过 `SupportSQLiteDatabase` 或 `RoomDatabase.openHelper` 访问数据库。

## SQLiteDriver 对数据库 I/O 路径的影响

`SQLiteDriver` 改的是 Room 与 SQLite 之间的抽象层。Room 2.x 时代，许多应用侧扩展点围绕 Android `SupportSQLiteDatabase`、`SupportSQLiteOpenHelper`、`Cursor`、`SQLiteDatabase` 编写；Room 3.0 转向 `SQLiteDriver`、`SQLiteConnection`、`SQLiteStatement` 后，这些扩展点要按连接和 statement 重新组织。[已验证: 官方文档, developer.android.com/reference/androidx/sqlite/SQLiteConnection]

`SQLiteConnection` 是需要关闭的数据库连接资源，公开的基础操作包括 `prepare(sql)`、`inTransaction()` 和 `close()`；`SQLiteStatement` 是需要关闭的 prepared statement，支持绑定参数、`step()`、读取列值和清理绑定。[已验证: 官方文档, developer.android.com/reference/androidx/sqlite/SQLiteStatement]

直接数据库访问的迁移不应停在函数名替换。Room 3.0 文档给出的方向是把 `runInTransaction`、`query(Cursor)` 这类入口换成 writer / reader connection 与 prepared statement。Android 端仍要验证这些点：

- 连接打开：首次 open 是否发生在冷启动、ContentProvider 初始化或首屏请求路径。
- 事务范围：写事务里是否夹带 JSON 解析、文件读写、网络回调或长时间计算。
- statement 生命周期：高频查询是否复用稳定 SQL 模板，是否在使用后关闭 statement。
- 参数绑定：是否继续使用 bind 参数，避免字符串拼接导致 SQL 注入和 plan 抖动。
- 异步边界：DAO suspend / Flow 是否把磁盘等待从主线程移走，但又没有把写连接长期占住。

这段代码用于表达 Room 3.0 迁移后的直接查询形态。重点看 reader connection、prepared statement 和 bind 参数，示例只保留 I/O 边界，不包含完整仓库封装。

```kotlin
suspend fun findUserName(db: AppDatabase, userId: Long): String? {
    return db.useReaderConnection { connection ->
        connection.prepare("SELECT name FROM users WHERE id = ?").use { statement ->
            statement.bindLong(1, userId)
            if (statement.step()) statement.getText(0) else null
        }
    }
}
```

这类代码的性能风险和 Room 2.x 一样来自查询形状、索引、事务和线程等待。`SQLiteDriver` 不会自动解决慢 SQL，也不会让单写者模型变成并行写；它减少的是 Room 对 Android 平台 `SupportSQLite` 类型的绑定，让同一套数据库 API 更适合 KMP。

## KSP 与 schema 输出对构建性能的影响

Room 3.0 的构建迁移要和运行期迁移分开验收。官方文档要求使用 KSP，并推荐 Room Gradle Plugin 配置 schema 输出。使用插件时必须设置 `schemaDirectory`，插件会把 schema 输出配置到编译任务里，使 generated schema 适合可复现、可缓存构建；带 flavor 的项目会输出到带变体名的目录，例如 `schemas/flavorOneDebug/.../1.json`。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/room3]

这段 Gradle 配置用于表达最小迁移面。重点看 `androidx.room3` 插件、`room3-runtime`、`room3-compiler` 和 schema 输出目录。

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
    id("androidx.room3")
}

dependencies {
    val roomVersion = "3.0.0-rc01"
    implementation("androidx.room3:room3-runtime:$roomVersion")
    ksp("androidx.room3:room3-compiler:$roomVersion")

    // Android 端用平台 SQLite 驱动；KMP commonMain 改用 BundledSQLiteDriver
    implementation("androidx.sqlite:sqlite-framework:$sqliteDriverVersion")
}

room3 {
    schemaDirectory("$projectDir/schemas")
}
```

`SQLiteDriver` 是 Room 3.0 打开数据库的入口。Android 端可选 `AndroidSQLiteDriver`（委托平台 `SQLiteDatabase`）或 `BundledSQLiteDriver`（内嵌 SQLite，KMP commonMain 共享）；构建时通过 `RoomDatabase.Builder.setDriver(...)` 指定。[已验证: developer.android.com/reference/androidx/sqlite/SQLiteDriver]

alpha04 起，连接池不再只是内部实现细节。`RoomDatabase.Builder.setSingleConnectionPool()` 和 `setMultipleConnectionPool(readers, writers)` 可以显式控制连接池；只有 `SQLiteDriver.hasConnectionPool()` 返回 `false` 的 driver 才会使用 Room 侧连接池。默认策略跟 `JournalMode` 绑定：`TRUNCATE` 使用单连接，`WRITE_AHEAD_LOGGING` 使用 4 个 reader + 1 个 writer；配置多个 writer 时要把 `SQLITE_BUSY` 与 `busy_timeout` 纳入压测和线上错误验收。[已验证: Android Developers Room 3.0 alpha04 release notes + RoomDatabase.Builder API]

schema 是迁移验证输入，不是构建产物垃圾。自动迁移、schema diff、CI 校验都依赖它；漏提交 schema 文件，后续版本的迁移测试会失去基线。多 flavor 项目要把各变体输出目录纳入 CI artifact 或仓库管理，避免只在 debug 变体验证通过。

KSP 性能评估要记录两组数据：

| 指标 | 采集方式 | 判断口径 |
| --- | --- | --- |
| clean build 编译时间 | Gradle Build Scan 或 CI 计时 | 观察 Room compiler、KSP task、Kotlin compile 的耗时变化 |
| 增量构建时间 | 改 DAO / Entity / 普通 Kotlin 文件各跑一次 | 判断 schema 输出和 KSP 是否扩大 invalidation |
| cache 命中率 | CI 远端缓存日志 | `schemaDirectory` 配置后 generated schema 是否破坏可缓存性 |
| schema diff | migration test + git diff | 确认 schema JSON 已提交，自动迁移验证可重复 |

KSP 能处理 Java 源声明，但 Room 3.0 只生成 Kotlin 代码。Java-only 数据库模块要么引入 Kotlin Gradle Plugin 和 KSP，要么把 Room 使用收敛到一个 Kotlin 数据模块，再通过接口暴露给 Java 调用方。把 KSP 插到所有业务模块会扩大构建影响面，多模块项目更适合先迁移数据层边界。

## SupportSQLite 兼容层的使用策略

`androidx.room3:room3-sqlite-wrapper` 的价值是迁移期兜底。官方文档说明它能把 `RoomDatabase` 转换成 `SupportSQLiteDatabase`，典型替换点是把旧的 `roomDatabase.openHelper.writableDatabase` 改成 `roomDatabase.getSupportWrapper()`。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/room3]

wrapper 不适合继续承载新代码。旧路径可以分三类处理：

| 旧代码类型 | 处理策略 | 原因 |
| --- | --- | --- |
| 调试面板、一次性导出、灰度诊断 | 可短期包 wrapper | 调用频率低，迁移风险小于停发风险 |
| 旧 Migration / callback 里接收 `SupportSQLiteDatabase` | 按 release notes 改成 `SQLiteConnection` 形态 | 回调签名变更会影响 schema 迁移路径 |
| 高频业务查询、批量写入、离线同步 | 直接迁到 DAO 或 driver API | wrapper 会保留旧抽象，难以复核连接和 statement 生命周期 |
| 第三方库硬依赖 `SupportSQLite` | 隔离在单独 adapter 模块 | 防止旧 API 继续扩散到 Room 3 数据层 |

迁移期不要把 wrapper 藏在全局工具类里。更稳的做法是建立 `legacy-db-bridge` 包，只允许列入白名单的调用点进入；每个调用点写清替换目标、负责人和删除日期。这样 Task 6 / Task 9 复审时能判断哪些旧口径仍在影响性能结论。

## 迁移前后的性能验证方法

Room 3.0 迁移后的性能验收不能只看“编译通过”和“测试通过”。数据库迁移对用户可感知性能的影响集中在冷启动 open、首屏查询、批量写事务、Flow 重查和 Migration。官方 Macrobenchmark 支持冷启动等端到端场景，并会输出 Perfetto trace；StrictMode 可用于暴露主线程磁盘读写；Android 性能文档也把 Perfetto、Macrobenchmark、Profiler 放在性能检查入口里。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-overview][已验证: 官方文档, developer.android.com/reference/android/os/StrictMode][已验证: 官方文档, developer.android.com/topic/performance/inspecting-overview]

验证分成四条线：

| 验证线 | 采集指标 | 工具 |
| --- | --- | --- |
| 冷启动数据库打开 | app start 到 database ready 的耗时、Migration 耗时、首次 query 耗时 | Macrobenchmark + app 自定义 trace |
| 查询与事务 | P50 / P90 / P99 查询耗时、写事务耗时、statement 数量 | DAO/Repository 包装层采样、SQLiteStatement 包装埋点、Perfetto |
| 线程与锁等待 | 主线程 disk read/write、数据库线程 runnable / sleeping、连接等待栈 | StrictMode、Perfetto、ANR traces |
| 构建与 CI | clean build、增量构建、KSP task 耗时、schema diff | Gradle Build Scan、CI 日志 |

这段测试配置用于把冷启动和数据库打开放到同一个量测场景。重点看 `StartupMode.COLD`，官方文档说明 cold startup 会在 setup 和 measure 之间杀掉目标进程，适合验证首次 open 是否进入启动路径。

```kotlin
@RunWith(AndroidJUnit4::class)
class DatabaseStartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartWithDatabaseOpen() = benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(StartupTimingMetric()),
        iterations = 10,
        startupMode = StartupMode.COLD,
        setupBlock = {
            pressHome()
        }
    ) {
        startActivityAndWait()
    }
}
```

应用侧还要加自定义 trace。围住 database builder、Migration、首次 DAO 查询、批量写入和 Flow 首次收集，Perfetto 才能把数据库时间和主线程、RenderThread、Binder、磁盘等待放在同一条时间线上。Clippings 中关于 I/O 等待的结构提醒了一个实践边界：数据库慢经常表现为线程等待时间变长，而不是 CPU 时间变高；只看 CPU 火焰图会漏掉锁等待和磁盘等待。

性能验收至少要跑三类数据集：空库、线上中位数库、线上大库。只用空库验证，Migration 和索引代价会被低估；只用大库验证，普通用户的启动路径又可能被误判。数据集要标注表规模、索引数量、数据库文件大小、WAL 文件大小、设备型号、系统版本、Room 版本和是否启用 R8 / Baseline Profile。

## KMP 场景的边界

Room 3.0 的 KMP 价值在于减少跨端数据层重复实现。官方文档说明 Room 3.0 增加 JavaScript 和 WasmJs 支持，并配合 `androidx.sqlite:sqlite-web` 里的 `WebWorkerSQLiteDriver` 覆盖 Web/WASM 场景。[已验证: 官方文档, developer.android.com/jetpack/androidx/releases/room3]

Android App 团队不要把 KMP 目标反向写进 Android 性能结论。Android 端迁移验收只回答这些问题：

- Android 端使用哪个 driver，首次 open、查询、事务、Migration 的数据是否回归。
- 协程 dispatcher 是否和现有数据库线程策略一致，是否造成写连接占用时间变长。
- 共享代码是否迫使 Android 端放弃平台已有优化，例如 WAL 配置、预置库复制策略或 Android 专用诊断。
- Web/WASM / iOS / Desktop 目标是否引入 schema、类型映射和同步策略差异，但不拿这些差异解释 Android 端耗时。

跨端同步是另一类问题。WebWorkerSQLiteDriver、离线同步、冲突合并、加密、文件系统限制都会影响产品架构，但这些不属于 Android 本地数据库 I/O 优化主线。要写也应拆到扩展或新章节，避免把 24.17 写成 KMP 总览。

## 常见风险与回滚策略

Room 3.0 在本轮复核时已进入 rc01，但仍未稳定发布。生产接入应默认使用灰度、双版本 schema 测试和可回滚数据层开关，不要把 Room 2.x 到 3.0 放进一个不可拆分的大版本改造。

| 风险 | 触发条件 | 回滚策略 |
| --- | --- | --- |
| alpha API 变化 | 后续 alpha / beta 改签名或行为 | 固定版本到当前验证版本，升级单独开分支 |
| KSP 配置缺失 | 模块未接入 KSP 或 Kotlin Gradle Plugin | 数据层模块先迁移，业务模块通过接口调用 |
| schema 漏提交 | flavor 输出目录未纳入仓库或 CI | CI 强制检查 schema diff，缺文件直接失败 |
| SupportSQLite 扩展点失效 | 旧 helper、callback、raw query 工具仍依赖旧类型 | 白名单 wrapper，逐项迁到 driver / DAO |
| Java DAO / Entity 处理差异 | Java 源由 KSP 处理但生成 Kotlin | 建立 Java 调用 smoke test，必要时拆 Kotlin 数据模块 |
| Migration 慢 | 大库 schema 改动、索引重建、预置库复制 | 大库基准测试，Migration 分批，必要时延迟非阻塞索引创建 |
| 多模块一次性切换 | 依赖树里 Room 2.x / 3.x 混用 | 从数据模块开始，禁止业务模块直接拿 RoomDatabase |

回滚不能只回滚依赖。schema 一旦前进，用户设备上的数据库版本也前进了；回滚版本必须能识别新 schema，或者通过服务端开关停用触发新 schema 的功能。发版前要跑“升级到 Room 3.0 → 写入新数据 → 回滚到旧版本”的兼容测试。无法兼容时，灰度范围要小到可承受数据修复成本。

## 版本边界

Room 3.0 预发布阶段的 API 变化节奏较快，几个关键版本的边界要记住：

| 版本 | 变化 | 迁移影响 |
| --- | --- | --- |
| 3.0.0-alpha02 | `@Fts5` 支持 | 搜索类业务可评估 FTS5，单独验证索引构建时间 |
| 3.0.0-alpha04 | `setSingleConnectionPool()` / `setMultipleConnectionPool(...)` | 按 `hasConnectionPool()`、WAL 默认 4 reader + 1 writer、`SQLITE_BUSY` / `busy_timeout` 验收连接池边界 |
| 3.0.0-alpha05 | `@Relation`/`@Junction` 数组化 `parentColumns`/`entityColumns` | 支持复合关系键；旧写法是否仍兼容需单独验证 |
| 3.0.0-alpha06 | `@Entity.withoutRowId` | 使用 `WITHOUT ROWID` 表时，单独验证主键约束、查询计划、文件体积和迁移兼容性 |
| 3.0.0-rc01 | DAO 查询结果 data class 默认值、`@ColumnTypeConverter`、provided custom DAO return types | converter import、结果映射和自定义返回类型是升级清单新增项；升级后重跑编译、schema diff 和 DAO smoke test |

预发布阶段建议固定版本号，不要用动态版本；升级时逐版本跑 migration test 和 benchmark。

## Room 2.x 到 Room 3.0 迁移 checklist

迁移按这个顺序执行，避免运行期问题和构建期问题混在一起：

- 依赖：把数据模块依赖改为 `androidx.room3:room3-runtime`、`androidx.room3:room3-compiler`，接入 KSP 和 Room Gradle Plugin。
- imports：批量替换 `androidx.room.*` 到 `androidx.room3.*`，保留可编译提交。
- schema：配置 `room3 { schemaDirectory(...) }`，提交所有变体 schema，CI 增加 schema diff 检查。
- DAO：把同步 DAO、Executor 依赖和旧 callback 改到协程 / Flow / driver 形态。
- driver：在 builder 中设置 `SQLiteDriver`（Android 端用 `AndroidSQLiteDriver` 或 `BundledSQLiteDriver`），确认是否需要 `setSingleConnectionPool()` / `setMultipleConnectionPool(...)`，并为直接 SQL 路径补 `SQLiteConnection` / `SQLiteStatement` 生命周期测试。
- wrapper：只为迁移期白名单调用点添加 `room3-sqlite-wrapper`，每个调用点登记删除计划。
- 测试：跑 MigrationTestHelper、DAO 单测、Macrobenchmark、StrictMode 主线程 I/O 检查和大库回放。
- 灰度：数据库 ready、Migration 耗时、查询 P90、事务 P90、crash-free、ANR rate 进入灰度看板。

## Room 3.0 与 DataStore / 原生 SQLite 选型

Room 3.0 不改变数据库选型原则。结构化关系数据、复杂查询、事务一致性、离线缓存和可迁移 schema 仍适合 Room；简单 key-value 配置、用户偏好和小体积状态适合 DataStore；极端高频写入、自定义虚表、特殊 SQLite 扩展或跨语言复用可能更适合直接 driver / 原生 SQLite。

选型表可以这样看：

| 场景 | 优先选择 | 判断依据 |
| --- | --- | --- |
| 用户配置、开关、轻量状态 | DataStore | 查询简单，schema 演进轻，避免数据库 open 进入启动路径 |
| 关系数据、列表、离线缓存 | Room 3.0 | SQL 校验、Migration、Flow / Paging 适配完整 |
| 大批量写入或自定义 SQLite 能力 | Room + driver API 或原生 SQLite | 需要更细的事务、statement 和连接控制 |
| KMP 共享数据层 | Room 3.0 | 共享 schema 和 DAO 收益高于迁移成本 |
| 启动首帧敏感、数据量小 | DataStore 或延迟 Room open | 避免冷启动被 database open / Migration 拖慢 |

Room 3.0 自 `3.0.0-alpha02` 起支持 FTS5，包括 `@Fts5`、FTS5 tokenizer 常量和 detail 选项。搜索类业务迁移时可评估 FTS5，但要单独验证索引构建时间、数据库文件增长和查询计划——FTS5 不是所有搜索场景的默认方案。

## Web/WASM SQLiteDriver 的跨端同步问题

Web/WASM 支持适合作为架构扩展，不应进入 Android 性能基线。WebWorkerSQLiteDriver 的线程模型、浏览器存储、同步协议、冲突合并和离线恢复都和 Android 本地 SQLite 不同。Android 端只需要保留接口边界：共享 DAO 和 entity 可以复用，平台 driver、诊断、加密、备份和迁移策略由各端实现。

项目进入 KMP 数据层后，验收文档至少拆成三份：Android 性能基线、跨端 schema / 类型映射、同步协议。24.17 的 Android 结论只引用第一份，其他两份作为架构材料，不参与 Android 查询耗时和启动耗时判断。

## 小结

Room 3.0 迁移要按“后端抽象、编译链路、旧扩展点、性能验收”四个面拆开看。`SQLiteDriver` 给的是新的数据库访问边界，KSP 和 schemaDirectory 给的是新的构建与迁移验证边界，KMP 给的是共享代码边界。Android 端性能是否变好，要用冷启动、查询、事务、锁等待和 Migration 数据回答，不能只靠版本升级推断。
