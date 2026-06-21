---

title: "文件 I/O 优化"
chapter: "24.1"
section: "24.1"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-14"
last_verified_against: "AOSP android-16.0.0_r1 (SharedPreferencesImpl / QueuedWork / ActivityThread / StrictMode / AtomicFile) + Android Developers docs"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/SharedPreferencesImpl.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/QueuedWork.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/StrictMode.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/util/AtomicFile.java @ android-16.0.0_r1"
  - type: official
    path: "https://developer.android.com/reference/android/os/StrictMode"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/datastore"
  - type: official
    path: "https://developer.android.com/reference/android/content/SharedPreferences.Editor"
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
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-08"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-08T08:25:05+08:00"
last_task9_review_log: "logs/deep-review/2026-06-08-08-audit.md"
last_task9_audit: "2026-06-08"
last_task9_autofix_at: "2026-06-08"
task9_review_notes: "2026-05-14 Task9 06: pass-tech-review。无 P0/P1；P2 2：AOSP master 需 pin tag，24.2 draft 交叉引用需处理。未自动晋升：Task6 尚未通过。 已写入 logs/deep-review/2026-05-14-06-deep-review.md。 | 2026-06-08 Task9 idle audit: auto-fixed。P0 0 / P1 2 / P2 0；将 AOSP master snapshot 源码锚点统一 pin 到 android-16.0.0_r1；将 QueuedWork 生命周期等待口径收窄到 Android 10-16 ActivityThread 路径，现代 App 主要在 onStop 等待，onPause 仅为 pre-Honeycomb 兼容路径。"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
last_task6_at: "2026-06-08T16:14:59+08:00"
last_task6_review_log: "logs/review/2026-06-08-16-review.md"
last_task6_audit: "2026-06-08"
last_task6_audit_log: "logs/review/2026-06-06-09-audit.md"
task6_state: reviewed
last_task6_at: "2026-06-08T16:14:59+08:00"
last_task6_review_log: "logs/review/2026-06-08-16-review.md"
last_task6_audit: "2026-06-08"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
---

# 文件 I/O 优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 主线程 I/O 的危害与 StrictMode 检测
- 🔹 SharedPreferences 的坑与 DataStore 迁移
- 🔹 MMKV 的原理与适用场景
- 🔹 文件读写的线程安全与性能

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解文件 I/O 优化

文件 I/O 在 App 性能里很容易被低估。CPU 火焰图里看不到多少计算量，主线程却卡在 `read()`、`write()`、`fsync()` 或 `QueuedWork.waitToFinish()`；Perfetto 里线程状态变成 D 状态或 Sleeping，用户看到的是点击无响应、启动变慢、页面切换掉帧。

Android 存储栈、I/O 调度、Page Cache、SharedPreferences 和 DataStore 的内部路径见 6.1、6.3、6.5 节。应用侧要回答四个取舍：哪些 I/O 不能放在主线程，哪些 KV 数据该迁移，什么时候 MMKV 合适，普通文件读写怎样避免并发和同步落盘把延迟放大。

## 主线程 I/O 的危害与 StrictMode 检测

主线程 I/O 的风险来自两个延迟源。读路径可能触发磁盘读取、缺页和目录遍历；写路径还可能触发 `fsync()`，等待文件系统把数据刷到存储设备。这个等待不消耗多少 CPU，却会让主线程无法处理输入、布局和绘制。对应到 ANR，就是主线程没有及时返回消息循环，详见 9.2 节。

StrictMode 是开发期最直接的检测入口。AOSP `StrictMode.ThreadPolicy.Builder.detectAll()` 会启用 `detectDiskReads()` 和 `detectDiskWrites()`；框架内部也会在关键位置主动触发检测，例如 `SharedPreferencesImpl.awaitLoadedLocked()` 在等待 XML 加载前调用 `BlockGuard.getThreadPolicy().onReadFromDisk()`。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/StrictMode.java][已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/SharedPreferencesImpl.java]

这段代码用于在 Debug 包里暴露主线程磁盘读写。重点看 `detectDiskReads()`、`detectDiskWrites()` 和 `penaltyLog()`，线上包不要直接开启崩溃惩罚。

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

这类配置只能发现当前线程触发的违规。异步任务已经切到后台线程后，StrictMode 不会自动判断“这次 I/O 是否拖慢了首帧”。首帧、点击、页面切换这类路径，还要结合 Perfetto 的线程状态、slice 耗时和 block I/O 事件判断，详见 6.3 节。[已验证: 官方文档, developer.android.com/reference/android/os/StrictMode]

应用侧处理主线程 I/O，可以按三类场景拆：

- 初始化读取：启动必需的小配置保留在内存快照里，磁盘读取提前到冷启动前段或 Splash 等待窗口内；非首屏配置延后到首帧后。
- 用户交互写入：点击、滑动、输入回调里只改内存状态，把落盘交给串行 I/O 队列；必须持久化的支付、草稿、登录态再单独做同步确认。
- 批量文件处理：图片、日志、缓存清理放到后台任务，并限制并发数。I/O 线程不是越多越好，过多线程会增加调度、锁竞争和存储队列排队。

## SharedPreferences 的坑与 DataStore 迁移

SharedPreferences（SP）的性能坑集中在两个位置：首次读取和写入收尾。首次读取时，`getString()`、`getAll()` 这类 API 会进入 `awaitLoadedLocked()` 等待 XML 加载完成；如果调用发生在主线程，StrictMode 会记录磁盘读风险。写入时，`apply()` 会先更新内存，再把写文件任务交给 `QueuedWork`；`commit()` 会等待 `writtenToDiskLatch`，同步拿到写入结果。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/SharedPreferencesImpl.java]

`apply()` 的误区在于“调用点很快返回”不等于“生命周期切换不等待”。AOSP `QueuedWork` 的注释说明，这个机制最初服务于 SharedPreferences 异步写入；在 Android 10-16 的 `ActivityThread` 中，普通现代 App 主要在 `handleStopActivity()` 里等待 `QueuedWork.waitToFinish()`，`handlePauseActivity()` 只对 pre-Honeycomb 兼容路径等待。于是某个页面里频繁 `apply()`，当 Activity 停止、广播结束或 Service 命令结束等关键生命周期点到来时，主线程仍可能被 `QueuedWork.waitToFinish()` 拖住。SP 与 ANR 的完整路径见 6.5 节，这里只引用结论。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/QueuedWork.java; frameworks/base/core/java/android/app/ActivityThread.java]

SP 适合少量、低频、轻量配置。以下场景应迁移或拆分：

| 场景 | 风险 | 处理方式 |
| --- | --- | --- |
| 单个 XML 超过几十 KB，启动路径读取多次 | 首次加载等待时间被主线程吸收 | 拆文件，首屏只读必要键，其他键延后读取 |
| 高频写入埋点开关、实验参数、草稿状态 | `apply()` 堆积，生命周期收尾等待 | 合并写入，切到 DataStore 或专用文件队列 |
| 多进程同时读写同一份配置 | SP 多进程一致性弱，状态容易过期 | 改用带多进程语义的存储方案 |
| 结构化对象被序列化成字符串塞进 SP | XML 体积膨胀，解析成本上升 | Proto DataStore 或数据库 |

DataStore 的价值在于把持久化模型换掉。官方文档描述 DataStore 使用 Kotlin coroutines 和 Flow 异步、事务化地保存数据，提供 Preferences DataStore 和 Proto DataStore 两种形态。Preferences DataStore 适合无 schema 的小型键值配置；Proto DataStore 适合有 schema 的结构化配置。[已验证: 官方文档, developer.android.com/topic/libraries/architecture/datastore]

迁移时不要只把 API 名称从 SP 换成 DataStore。更稳的做法是先梳理键的访问路径：启动强依赖键、首屏可延后键、后台刷新键分开处理。启动强依赖键可以保留一份内存态默认值，DataStore 的 Flow 更新后再刷新 UI；必须阻塞启动的键要单独评估收益，因为从任何持久化介质同步等待都会吃掉启动预算。

这段代码用于表达从 SP 到 Preferences DataStore 的迁移形态。重点看 `SharedPreferencesMigration` 和 `edit` 的挂起写入，业务层不再直接调用同步 XML 写入。

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

DataStore 也不是数据库替代品。多表查询、条件检索、分页、事务关系交给 Room/SQLite；少量配置、强类型设置、迁移 SP 的 KV 数据，DataStore 更合适。

## MMKV 的原理与适用场景

MMKV 的设计路线和 SP、DataStore 不同。Tencent MMKV 文档说明，它用 `mmap` 把文件映射成内存区域，应用写入映射内存后由操作系统负责回写文件；值编码使用 protobuf；频繁更新时采用追加写，新版本 key 写在尾部，初始化时扫描并保留同一 key 的末次值；文件空间不足时做去重整理或扩容；同时用 CRC 校验发现损坏。[已验证: MMKV design wiki, github.com/Tencent/MMKV/wiki/design_eng]

`mmap` 带来的收益是减少传统 `read()` / `write()` 复制路径上的一部分开销，并把随机小写转换成内存写入。但它不会让落盘成本消失。映射页被写脏后仍要回写；进程崩溃、系统回收、存储压力都会影响最终刷盘时机。MMKV 适合热路径的小型 KV 数据，不适合大对象、复杂查询和必须逐条确认刷盘成功的交易型数据。

可以把 MMKV 放在这些位置：

- 高频读取的开关、实验参数、轻量运行态标记：读路径短，避免 SP XML 首次解析拖住启动。
- 对启动延迟敏感的小配置：和启动框架配合，控制 key 数量和文件大小。
- 多进程共享的小型状态：启用 MMKV 的多进程模式，并在设计上接受跨进程同步成本。

不建议放在这些位置：

- 大 JSON、图片、二进制包：文件膨胀和内存映射会把内存压力转嫁到 Page Cache 与进程地址空间。
- 需要范围查询、排序、分页的数据：数据库更合适。
- 强一致交易数据：要明确写入确认、失败恢复和审计路径，普通 KV 组件不够。

MMKV 与 DataStore 的选择可以按访问模型判断：需要官方 Jetpack 组件、Flow 订阅、SP 平滑迁移，优先 DataStore；追求热路径 KV 读写延迟，并愿意承担第三方库、多进程模式和文件整理策略的维护成本，再考虑 MMKV。

## 文件读写的线程安全与性能

普通文件 I/O 的难点不是 API，而是并发语义。多个线程同时写同一个文件、一个线程读半成品、写入失败后留下损坏文件，都会把性能问题变成稳定性问题。Android `AtomicFile` 的注释也写明：如果另一个线程正在写，新的写入可能替换前一个写入结果；调用者必须自己做线程保护。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/util/AtomicFile.java]

可靠写入要满足三个条件：单写者、临时结果不可见、失败可恢复。`AtomicFile` 提供了 `startWrite()`、`finishWrite()`、`failWrite()` 这套写入协议，但它不负责跨线程排队。应用侧仍要用单线程队列、`Mutex` 或仓库层串行化，避免两个写入同时进入。

这段代码用于展示“串行队列 + 原子写文件”的形态。重点看 `withContext(ioDispatcher)` 只负责切线程，`Mutex` 才负责同一文件的写入互斥。

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

这段代码只解决单进程内的同一文件写入互斥。跨进程写同一文件时，还要引入文件锁或把写入收敛到 ContentProvider / Service；如果业务已经需要跨进程事务，数据库通常比手写文件协议更稳。

读路径的优化目标是减少主线程等待和重复解析：

- 大文件按块读，避免一次性分配大 byte array。图片、音频、日志这类文件交给流式 API 或专用库处理。
- 热数据保留内存快照，文件修改后再刷新；不要每次 UI 绘制都重新打开文件。
- 读取结果和解析结果分开缓存。文件内容没变时，复用已解析对象，避免 CPU 解析和 I/O 等待同时发生。
- `fsync()` 合并。日志、埋点、缓存索引这类可丢少量数据的场景，按批次刷盘；用户草稿、支付状态等不可丢数据，再做同步确认。

[自动发现] 文件 I/O 优化要保留可观测入口。最少记录三类指标：单次读写耗时、文件大小、调用线程。Debug 包用 StrictMode 抓主线程读写；灰度包用轻量采样记录超过阈值的文件操作；线上排查时把慢 I/O 与页面、设备存储剩余空间、低内存状态一起分析。只记录“某接口慢”不够，必须知道它慢在读、写、解析、锁等待还是 `fsync()`。

## 扩展：线上文件 I/O 观测清单

文件 I/O 的线上监控可以从低成本项开始：

- 慢读写采样：记录路径类型、文件大小、耗时、线程名、业务场景，不上传用户文件内容。
- 主线程违规：Debug 和内测包打开 StrictMode，线上只做采样埋点，避免惩罚策略影响用户。
- 队列积压：记录 I/O 队列长度、最老任务等待时间、丢弃或合并次数。
- SP 遗留风险：统计 SP 文件大小、单次 `apply()` 次数、启动阶段读取 key 数量，为迁移 DataStore 或 MMKV 排优先级。
- 存储环境：关联剩余空间、低内存、设备型号和 Android 版本。同一段代码在低端 eMMC、UFS 3.x、UFS 4.0 上的尾延迟差异会很大。

这些指标不需要一次收全。先覆盖启动、页面切换、登录态更新、草稿保存、日志写入五类路径，就能定位大多数应用侧文件 I/O 问题。

## 小结

文件 I/O 优化可以按风险排序：主线程不做磁盘读写，SP 风险先识别再迁移，热 KV 读写按访问模型选择 DataStore 或 MMKV，普通文件写入用串行化和原子写协议兜住一致性。机制细节交给 6.1、6.3、6.5 节，应用工程里要把它们变成约束和检查项。
