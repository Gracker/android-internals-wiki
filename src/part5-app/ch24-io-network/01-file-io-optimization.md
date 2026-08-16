---

title: "文件 I/O 优化"
chapter: "24.1"
section: "24.1"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1 (SharedPreferencesImpl / QueuedWork / ActivityThread / StrictMode / AtomicFile); Android common kernel android17-6.18-2026-06_r6; Android Developers DataStore and 16 KiB page documentation; Tencent MMKV design"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/SharedPreferencesImpl.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/QueuedWork.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/StrictMode.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/util/AtomicFile.java @ android-17.0.0_r1"
  - type: official
    path: "https://developer.android.com/reference/android/os/StrictMode"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/datastore"
  - type: official
    path: "https://developer.android.com/reference/android/content/SharedPreferences.Editor"
  - type: legacy-reference-preserved
    path: "https://developer.android.com/reference/android/app/QueuedWork"
  - type: official
    path: "https://developer.android.com/reference/kotlin/androidx/datastore/core/MultiProcessDataStoreFactory"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/sync.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/filemap.c"
  - type: blog
    path: "https://github.com/Tencent/MMKV/wiki/design_eng"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识内存.md"
tags: [file-io, sharedpreferences, datastore, mmkv, strictmode]
related_chapters: ["24.2", "6.1", "6.3", "6.5", "9.2"]
pipeline_stage: finalized
last_review_finalize_at: "2026-08-15T09:21:12+08:00"
last_review_finalize_run_id: "20260815-092112-gracker-writing-review"
last_draft_polish_at: "2026-08-15T09:21:12+08:00"
last_draft_polish_run_id: "20260815-092112-gracker-writing"
task9_state: reviewed
task2b_state: fixed
task6_state: reviewed
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part5-app/ch24-io-network/08-io-network-case-studies.md"
---

# 文件 I/O 优化

## 文件 I/O 的性能边界

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。涉及页缓存、回写和 `fsync()` 时，内核锚点是 `android17-6.18-2026-06_r6`。

文件 I/O 的等待时间不一定表现为大量 CPU 计算。CPU 火焰图（按调用栈汇总 CPU 采样的图）里可能看不到明显热点，主线程却会停在 `read()`、`write()`、`fsync()`、缺页（所需文件页尚未驻留内存）或 `QueuedWork.waitToFinish()`。Perfetto 中，线程可能显示为可中断睡眠、等待内核 I/O 的不可中断睡眠，或等待锁；用户看到的结果是启动变慢、点击无响应和页面切换掉帧。

Android 存储栈、I/O 调度、页缓存和 SharedPreferences 的内部路径见 [6.1 Android 存储架构](../../part1-fundamentals/ch06-storage/01-storage-architecture.md)、[6.3 I/O 调度与性能](../../part1-fundamentals/ch06-storage/03-io-scheduling.md)和 [6.4 SharedPreferences/DataStore](../../part1-fundamentals/ch06-storage/04-sharedpreferences-datastore.md)。应用侧要回答四个取舍：哪些 I/O 不能放在主线程，哪些键值数据该迁移，什么时候 MMKV 合适，普通文件读写怎样避免并发和同步持久化放大尾延迟（少量最慢操作的延迟）。

## 主线程 I/O 的危害与 StrictMode 检测

主线程 I/O 的风险来自不可预估的尾延迟。读路径可能命中页缓存，也可能触发缺页、存储读取和目录遍历；写路径通常先写入页缓存，需要持久化时还会通过 `fsync()` 等待文件系统完成相应回写。线程等待期间不一定消耗很多 CPU，却无法继续处理输入、布局和绘制。对应到 ANR（Application Not Responding，应用无响应），就是主线程没有及时返回消息循环，详见 [9.2 ANR 类型与触发条件](../../part2-performance/ch09-anr/02-anr-types.md)。

StrictMode 是开发阶段检测线程磁盘、网络等策略违规的工具。Android 17 的 `StrictMode.ThreadPolicy.Builder.detectAll()` 会启用 `detectDiskReads()` 和 `detectDiskWrites()`；框架也会在明确知道线程可能等待磁盘的位置触发检测，例如 `SharedPreferencesImpl.awaitLoadedLocked()` 在等待 XML 加载前调用 `BlockGuard.getThreadPolicy().onReadFromDisk()`。

下面的配置用于在调试构建中暴露主线程磁盘读写。`penaltyLog()` 记录违规但不结束进程，适合开发期持续启用；不要把可能改变用户流程的惩罚直接带入发布构建。

```kotlin
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) {
            StrictMode.setThreadPolicy(
                StrictMode.ThreadPolicy.Builder()
                    .detectDiskReads()
                    .detectDiskWrites()
                    .detectNetwork()
                    .penaltyLog()
                    .build()
            )
        }
    }
}
```

这段策略只报告受该线程策略约束的调用。I/O 已切到工作线程后，StrictMode 不会判断它是否占满存储队列、持有主线程需要的锁，或让主线程等待结果。首帧、点击和页面切换还要结合 Perfetto 的线程状态、应用自定义 trace 区间（标记业务操作的起止时间），以及采集配置中可用的文件系统或块设备事件判断。

[源码锚点：[`StrictMode.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/StrictMode.java)、[`SharedPreferencesImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/SharedPreferencesImpl.java)]

应用侧处理主线程 I/O，可分为三类场景：

- 初始化读取：在工作线程读取并显式协调依赖；非首屏配置延后到首帧后。内存默认值只适用于允许短暂使用默认值的界面状态，认证、隐私和迁移开关不能用陈旧默认值越过校验。
- 用户交互写入：点击、滑动和输入回调只更新界面状态，把持久化交给串行 I/O 队列。确需确认成功的草稿或交易状态，应在工作线程等待持久化结果并向用户呈现失败，不能在主线程 `fsync()`。
- 批量文件处理：图片、日志和缓存清理放到后台任务，并限制并发数。过多 I/O 任务会增加锁竞争和存储队列排队；协程切到 `Dispatchers.IO` 也不代表并发量已经受业务约束。

## SharedPreferences 的风险与 DataStore 迁移

SharedPreferences（SP）的性能风险集中在首次读取和写入完成阶段。Android 17 的 `getString()`、`getAll()` 等 API 会进入 `awaitLoadedLocked()`；后台 XML 加载未完成时，调用线程就在这里等待。写入时，`apply()` 先提交内存变更，再把磁盘任务交给框架内部、未纳入公开 SDK 的 `QueuedWork`；`commit()` 等待 `writtenToDiskLatch`（写盘完成同步信号），并返回本次持久化结果。

`apply()` 调用点很快返回，不代表后续组件切换无需等待。`apply()` 会向 `QueuedWork` 登记 finisher（等待磁盘任务完成的收尾回调）。Android 17 的 `ActivityThread` 对 Android 3.0（Honeycomb）及之后的 Activity 在 `handleStopActivity()` 中等待，对更早版本的 Activity 则在 `handlePauseActivity()` 中等待；Service 命令完成和 Service 停止等位置也会调用 `QueuedWork.waitToFinish()`。框架 API 文档明确警告，未完成的 `apply()` 可能在 Activity 或 Service 状态切换时阻塞主线程。页面里连续写入许多状态，代价可能在稍后的组件边界集中出现。

[源码锚点：[`SharedPreferencesImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/SharedPreferencesImpl.java)、[`QueuedWork.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/QueuedWork.java)、[`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)]

SP 适合少量、低频、轻量配置。以下场景应迁移或拆分：

| 场景 | 风险 | 处理方式 |
| --- | --- | --- |
| XML 持续增长，启动路径又同步读取 | 首次加载与解析时间落在主线程 | 按访问域拆分，首屏只等待必要数据 |
| 高频写入埋点开关、实验参数、草稿状态 | `apply()` 堆积，生命周期收尾等待 | 合并写入，切到 DataStore 或专用文件队列 |
| 多进程同时读写同一份配置 | SP 不支持跨进程一致性 | 使用 `MultiProcessDataStoreFactory`、数据库或单进程服务 |
| 结构化对象被序列化成字符串塞进 SP | XML 体积膨胀，解析成本上升 | Proto DataStore 或数据库 |

DataStore 用协程和 `Flow`（按时间发出数据的 Kotlin 异步流）提供异步读取与事务性更新；同一次事务更新要么写入新值，要么保留原值。Preferences DataStore 适合没有固定字段模式的小型键值设置；Proto DataStore 适合由 Protocol Buffers 模式定义字段和类型的结构化设置。它仍面向小型数据，不支持 Room 那样的局部更新、条件查询和表关系。

迁移时应先按一致性要求和读取时机分组：启动必须确认的键、界面可延后键、后台刷新键不能共用一种等待策略。允许先显示默认值的设置可在 `Flow` 发出数据后更新界面；认证、隐私和数据迁移状态要在进入相关业务前完成异步读取与校验。不要用 `runBlocking` 把 DataStore 重新变成主线程同步 I/O。

下面的代码用于展示 SP 到 Preferences DataStore 的迁移形态。创建 DataStore 的属性委托应在顶层只声明一次，`SharedPreferencesMigration` 会在 DataStore 对外提供数据前执行，写入方通过挂起的 `edit` 等待更新结果。

```kotlin
val Context.settingsStore by preferencesDataStore(
    name = "settings",
    produceMigrations = { context ->
        listOf(SharedPreferencesMigration(context, "legacy_settings"))
    }
)

private val launchFlagKey = booleanPreferencesKey("launch_flag")

suspend fun updateLaunchFlag(context: Context, enabled: Boolean) {
    context.settingsStore.edit { prefs ->
        prefs[launchFlagKey] = enabled
    }
}

fun observeLaunchFlag(context: Context): Flow<Boolean> =
    context.settingsStore.data.map { prefs -> prefs[launchFlagKey] ?: false }
```

这段代码没有在调用方同步打开 XML 文件，但业务仍需处理 `data` 流中的读取异常和迁移失败。默认的 `preferencesDataStore` 委托面向单进程；多个进程访问同一文件时，要让所有进程统一使用官方多进程工厂，不能混用单进程与多进程实例。

DataStore 面向少量配置、强类型设置和 SP 键值迁移；多表查询、条件检索、分页和关系事务应交给 Room/SQLite。

[官方文档：[`SharedPreferences`](https://developer.android.com/reference/android/content/SharedPreferences)、[`SharedPreferences.Editor`](https://developer.android.com/reference/android/content/SharedPreferences.Editor)、[DataStore](https://developer.android.com/topic/libraries/architecture/datastore)]

### 从 `QueuedWork.waitToFinish()` 还原 SharedPreferences ANR

看到页面停止、应用进入后台或 Service 回调结束时的 ANR，主线程停在 `QueuedWork.waitToFinish()`，不能因为业务代码使用了 `apply()` 就排除 SharedPreferences。`apply()` 只是把调用点与磁盘写入分开：它先更新内存，再向 `QueuedWork` 登记等待磁盘完成的收尾回调；框架稍后在 Activity 停止、Service 命令结束和 Service 销毁等边界等待这些工作。`commit()` 则会直接等待 `writtenToDiskLatch`，没有其他磁盘写入时，当前调用线程还可能参与写文件。

排查要把同一时间窗口里的五类证据拼在一起：

| 证据 | 观测方式 | 判断点 |
| --- | --- | --- |
| ANR 主线程 | ANR trace、bugreport（系统诊断包） | 是否停在 `QueuedWork.waitToFinish()` 或首次加载等待 |
| 磁盘线程 | Perfetto 与同窗口线程栈 | 是否在 XML 序列化、`writeToFile()`、`FileUtils.sync()` 或块设备等待 |
| 写入来源 | 统一存储封装 | 偏好文件类别、调用线程、生命周期阶段、写入类型和次数 |
| 文件状态 | 应用内部诊断 | XML 大小、键值条目数、备份文件是否存在 |
| 生命周期 | Activity、Service 与广播时序 | 写入是否集中在停止、销毁或回调返回前 |

日志只记录经过分类的业务来源，或只用于同类来源聚合的稳定散列标识，不输出原始键和值。StrictMode 能发现主线程同步磁盘访问，却不能证明此前的 `apply()` 是否会在生命周期边界造成等待；两类证据不能互相替代。

治理时先按数据语义决定迁移方向：小型设置进入 Preferences/Proto DataStore，结构化和可查询数据进入 Room，高频瞬时状态尽量只保留在内存，需要确认的用户操作必须暴露持久化失败，跨进程数据使用明确支持跨进程一致性的存储或单进程服务。不要用固定防抖时间窗冒充持久化保证；只有“中间状态可丢，只需保留较新值”的数据才允许合并写入，并且要写明进程终止后的恢复规则。

验收也不要记录无法公开观测的“`apply()` 完成耗时”。应比较同一偏好文件的大小、键值条目数和写入次数，生命周期结束前后的写入分布，Perfetto 中 `queued-work-looper` 与主线程等待，以及 `QueuedWork.waitToFinish()` 相关 ANR 数量除以会话数或活跃用户数后的比例；同一报表要固定分母。回归场景至少覆盖冷启动首次读取、连续修改后立即切后台、Service 停止、进程终止、存储压力、升级迁移和多进程误用。

## MMKV 的原理与适用场景

MMKV 的设计路线和 SP、DataStore 不同。Tencent MMKV 的设计文档说明，它用 `mmap`（把文件映射进进程虚拟地址空间）读写文件，值使用 Protocol Buffers（protobuf）二进制编码；更新采用追加写，同名键以末次值为准；空间不足时整理有效数据或扩容，并用 CRC（循环冗余校验）检测文件损坏。

`mmap` 能减少传统 `read()` / `write()` 路径上的部分复制，并把小写入转成映射页修改，但不会取消文件 I/O。首次访问仍可能触发缺页；脏页（已修改但尚未写回存储的内存页）仍要回写；初始化还要校验并解析文件。同步读取放在主线程，不等于延迟一定稳定，StrictMode 也未必把映射缺页报告成普通磁盘读取。

MMKV API 返回与数据已到达持久化介质不是同一件事。若业务需要断电或进程异常下的明确持久性，应核对所用 MMKV 版本的同步接口、返回值与恢复策略，并做故障注入（主动模拟进程终止、存储错误等失败）；不能从“使用 `mmap` 文件映射”推导出它满足交易数据的持久性要求。

MMKV 适合这些位置：

- 高频读取的开关、实验参数、轻量运行态标记：读路径短，避免 SP XML 首次解析拖住启动。
- 对启动延迟敏感的小配置：控制键数量和文件大小，并测量冷启动首次缺页与解码。
- 多进程共享的小型状态：显式启用 MMKV 多进程模式，并验证进程锁、变更检测和异常恢复。

不建议放在这些位置：

- 大 JSON、图片、二进制包：文件膨胀和内存映射会增加页缓存与进程地址空间压力。
- 需要范围查询、排序、分页的数据：数据库更合适。
- 要求明确持久化确认的交易数据：应使用能表达事务、失败和恢复语义的存储。

MMKV 与 DataStore 的选择应基于访问行为和一致性要求。需要 Jetpack 组件、`Flow` 订阅、SP 迁移或官方多进程一致性时，可优先评估 DataStore；读写频繁的小型键值数据经过真实设备基准证明 MMKV 更合适，并且团队能维护第三方库与恢复策略时，再选 MMKV。不要拿库作者提供的一次基准结果代替本应用的冷启动、尾延迟、内存和异常恢复测试。

[项目来源：[Tencent/MMKV](https://github.com/Tencent/MMKV)、[MMKV Design](https://github.com/Tencent/MMKV/wiki/design_eng)]

## 文件读写的线程安全与性能

普通文件 I/O 的难点在于并发、可见性和持久性。多个线程同时写一个文件、读取方看到半成品，或写入失败后只留下损坏版本，都会把性能问题变成数据问题。

Android 17 的 `AtomicFile` 把新内容写到 `.new` 文件，`finishWrite()` 对流调用 `FileUtils.sync()`、关闭文件，再用 rename（同一文件系统内的重命名）替换目标文件；调用 `failWrite()` 时会关闭流并删除 `.new`。它保护的是“读到旧版本或完整新版本”，不提供文件锁。源码注释要求调用方为所有并发访问建立互斥条件。

下面的代码用于展示“工作线程 + 单进程互斥 + 原子替换”的形态。`withContext(ioDispatcher)` 负责执行线程，`Mutex` 才负责同一个文件的写入顺序。

```kotlin
class JsonFileStore(
    private val file: File,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    private val writeMutex = Mutex()

    suspend fun writeJson(content: String) = withContext(ioDispatcher) {
        writeMutex.withLock {
            val atomicFile = AtomicFile(file)
            var stream: FileOutputStream? = null
            try {
                stream = atomicFile.startWrite()
                stream.write(content.toByteArray(Charsets.UTF_8))
                atomicFile.finishWrite(stream)
            } catch (t: Throwable) {
                if (stream != null) {
                    atomicFile.failWrite(stream)
                }
                throw t
            }
        }
    }
}
```

这段实现只覆盖共享同一个 `JsonFileStore` 实例的进程内写入。若读取也可能与写入协议并发，应让读取走同一互斥边界。多个实例或多个进程仍可能互相覆盖；更合适的方案是把写入集中到单进程 Service 或 ContentProvider，或改用具备跨进程事务语义的数据库。

`AtomicFile.finishWrite()` 返回 `void`，内部同步或 rename 失败主要写日志，不能向业务提供丰富的持久化失败信息。支付、订单等需要确认提交的状态不应只依赖这段简单封装。

[源码锚点：[`AtomicFile.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/util/AtomicFile.java)]

### `write()`、页缓存与 `fsync()` 的区别

普通缓冲文件写入返回时，数据通常已经复制到内核页缓存，但不等于已经到达持久化介质。Android 17 对应的 Linux 6.18 common kernel 中，`fsync` 系统调用进入 `do_fsync()`，再经 `vfs_fsync()` / `vfs_fsync_range()` 调用具体文件系统的 `fsync` 实现。尾延迟受脏页数量、用于故障恢复的文件系统日志、存储设备和当时 I/O 负载影响。

这带来两条工程规则：

- 可重建的日志、埋点和缓存索引可以合并写入与同步，减少频繁 `fsync()`；
- 不可丢状态要在工作线程等待明确的提交结果，并把失败反馈给上层，不能只看 `write()` 成功。

合并同步的前提是业务接受对应时间窗的数据丢失。不能用一套固定批次和间隔覆盖所有文件。

[内核锚点：[`fs/sync.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/sync.c)、[`mm/filemap.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/filemap.c)]

读路径的优化目标是减少主线程等待和重复解析：

- 大文件按块读，避免一次性分配大字节数组。图片、音频和日志交给流式 API 或专用库处理。
- 热数据保留内存快照，文件修改后再刷新；不要每次 UI 绘制都重新打开文件。
- 读取结果和解析结果分开缓存。文件内容没变时，复用已解析对象，避免 CPU 解析和 I/O 等待同时发生。
- 缓冲区大小用真实负载做基准，不把“更大缓冲区”当成固定优化。过小会增加调用次数，过大则增加内存和复制成本。

Android 17 设备可能采用 4 KiB 或 16 KiB 页。使用 `mmap()`、NDK 库或自定义文件格式时，不要把页大小硬编码为 4096；对齐要求应取运行时页大小。Java 流式 I/O 的业务分块大小也不必等于内核页大小，两者应分别验证。

[官方边界：[支持 16 KiB 页大小](https://developer.android.com/guide/practices/page-sizes)]

文件 I/O 优化要保留可观测入口。至少记录单次读写耗时、数据量、调用线程和业务场景。调试构建用 StrictMode 抓主线程读写；分阶段发布版本可对慢操作采样。分析时区分读取、写入、编码/解析、锁等待和 `fsync()`，并关联存储剩余空间与同期系统负载。不要记录用户文件内容、完整路径或敏感键值。

## 生产环境文件 I/O 观测清单

文件 I/O 的生产监控可以从低成本项开始：

- 慢读写采样：记录路径类型、文件大小、耗时、线程名、业务场景，不上传用户文件内容。
- 主线程违规：调试和内测构建打开 StrictMode，生产环境只做采样记录，避免惩罚策略影响用户。
- 队列积压：记录 I/O 队列长度、最老任务等待时间、丢弃或合并次数。
- SP 遗留风险：统计 SP 文件大小、单次 `apply()` 次数和启动阶段读取键数量，为迁移 DataStore 或 MMKV 排优先级。
- 存储环境：关联剩余空间、设备型号、Android 版本、温度和同期 I/O 负载，解释设备间尾延迟差异。

采集范围可以从启动、页面切换、登录态更新、草稿保存和日志写入等高频路径逐步扩大。慢操作阈值应来自同类设备和同一业务场景的基线，不使用一套毫秒值覆盖所有文件。

## 小结

文件 I/O 优化可以按风险排序：主线程不做磁盘读写；SP 先确认首次加载和 `QueuedWork` 等待，再决定迁移；键值存储按一致性和访问行为选择 DataStore 或 MMKV；普通文件用单写者、互斥和原子替换保护内容完整性。需要持久化确认时，还要在工作线程等待明确结果，并验证故障恢复。
