---
title: "Android 17 监控降级：内存约束与隐私限制下的性能数据采集"
chapter: "26.22"
status: finalized
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
drafted_date: "2026-06-27"
last_verified: "2026-07-31"
last_verified_against: "Android Developers docs + AOSP android-17.0.0_r1"
confidence: medium-high
last_rework_at: "2026-07-31T09:37:47+08:00"
last_rework_run_id: "20260731-093747-rework-bc7d7877"
reviewed_date: "2026-07-31"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-31T10:10:00+08:00"
last_review_finalize_run_id: "20260731-100508-3e642a8b"
pipeline_stage: "finalized"
task6_state: "reviewed"
task9_state: "reviewed"
tags: [observability, monitoring, memory-limiter, privacy, android17, apm]
related_chapters: ["26.1", "26.3", "26.9", "26.12", "23.6", "4.5", "4.11", "5.8", "5.17", "15.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "研究素材/官方文档/AOSP结构/知识盲区"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ProfilingManager"
  - type: official
    path: "https://developer.android.com/develop/background-work/services/foreground-service-types"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-management"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Debug.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
---

# 26.22 Android 17 监控降级：内存约束与隐私限制下的性能数据采集

APM 不能假设进程会一直运行、系统会按固定周期调度任务，也不能把系统诊断权限当成普通 App 能力。Android 14 的 cached app freezer、Android 17 的 MemoryLimiter、长期存在的后台调度与日志权限边界，会共同暴露依赖定时轮询、常驻进程和跨进程抓取的监控设计缺陷。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。涉及 cgroup memory controller 与 freezer 时，内核锚点为 `android17-6.18-2026-06_r6`。重点是监控 SDK 怎样在资源与隐私边界内保持可解释的数据，不重复 23.6 的 MemoryLimiter 实现细节和 26.12 的 ProfilingManager 完整版本表。

## 三类约束要分开处理

| 约束 | 平台行为 | App 能观察什么 | 设计结论 |
|---|---|---|---|
| 进程资源 | MemoryLimiter、LMKD、GC、回收与进程状态变化 | 当前进程内存快照、trim 状态、退出记录、可选 profile | 采集器自身也属于内存负载 |
| 执行机会 | cached freezer、后台启动限制、JobScheduler/WorkManager 配额 | 生命周期、任务实际开始/停止、调度结果 | 后台定时器没有准点保证 |
| 数据访问 | App sandbox、`READ_LOGS`/`DUMP` 权限、profiling 脱敏 | 自有进程数据、公开回执、用户授权的数据 | 不以跨进程 `/proc`、logcat 或 dumpsys 作为线上依赖 |

资源不足、没有执行机会和没有读取权限会产生相似的“样本缺口”，处理方式却不同。每条记录都应带 `source`、`scope`、`supported`、采样时间和跳过原因，让服务端区分“值为零”“未采到”和“该设备不支持”。

## Android 17 MemoryLimiter 的准确边界

[Android 17 行为变更](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)说明，应用内存限制只在部分设备上实施，限制配置与设备总 RAM 有关，但没有向 App 承诺可依赖的固定门槛。它影响运行在 Android 17 上的所有 App，不取决于 `targetSdkVersion`。

命中该限制后的公开归因协议是：

- `ApplicationExitInfo.reason == REASON_OTHER`；
- `ApplicationExitInfo.description` 包含精确字符串 `"MemoryLimiter:AnonSwap"`；
- 注册 Android 17 的 `TRIGGER_TYPE_ANOMALY` 后，系统可能提供与内存限制相关的 heap dump。

`getDescription()` 通常只面向人工阅读。这里能匹配精确字符串，是因为 Android 17 官方文档专门规定了该标记。不能把所有 `REASON_OTHER`、所有 `SIGKILL` 或所有高 PSS 会话归为 MemoryLimiter。

### cgroup 限制与终止决定不是同一件事

Android 17 的 [`MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)和 [JNI 实现](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)使用 cgroup v2 内存接口监视进程。`android17-6.18-2026-06_r6` 的 [cgroup v2 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)把 `memory.high` 定义为节流边界：越过它会增加回收压力，但这个控制文件本身不会调用 OOM killer。Android 用户空间在满足 MemoryLimiter 条件后执行 profiling 与终止流程。

因此，PSS 上升、分配变慢或线程停顿只能说明内存现象，不能单独证明 MemoryLimiter 已经触发。归因要以退出记录的精确标记为主，再关联退出前内存趋势、业务场景和可用 heap dump。

### SDK 内存也要计入基线

嵌入宿主进程的 SDK 对象、native allocation、线程栈、映射、ring buffer 和队列都会增加该进程的内存。单独创建 `:apm` 进程也不会获得稳定的常驻权：新进程有自己的进程状态和限制，还会增加一份 runtime、代码、线程与 IPC 成本。

监控开销没有通用的安全百分比。评估时应比较同一场景启用和禁用 SDK 的：

- RSS、PSS、Java heap、native heap 与 graphics；
- 线程数、stack reservation、mmap 和文件缓存；
- MemoryLimiter、LMK、Java OOM 与 native allocation failure 分布；
- 前台、FGS、后台和 cached 状态；
- 设备 RAM、page size、ABI、系统 build 与 App 版本。

平均值会掩盖峰值和尾部。发布门禁至少检查高分位、最大连续增长、进程退出率和设备分层。

### 用 adb 复现，不在 App 中猜限制

下面的命令用于专用 Android 17 测试设备。它们会改变当前设备的 MemoryLimiter 测试状态，运行前应保存基线，测试后恢复。

```bash
adb shell am memory-limiter status
adb shell am memory-limiter manual "$TEST_PID" "$TEST_LIMIT_MB"

# 清除手动限制，恢复设备默认配置。
adb shell am memory-limiter manual "$TEST_PID" none
```

这些命令只在实施 MemoryLimiter 的设备上有效，`manual` 作用于指定 PID。测试脚本必须先把 `TEST_PID` 和 `TEST_LIMIT_MB` 设为当前用例的明确输入。`status` 输出用于记录设备当时是否实施限制以及 visible/non-visible 配置，不能把一次实验参数写成所有设备的生产门槛。

## Android 14 以后不能依赖旧的 trim 压力等级

旧监控代码常用 `TRIM_MEMORY_RUNNING_MODERATE`、`RUNNING_LOW`、`RUNNING_CRITICAL` 和 `COMPLETE` 调整采样频率。这个策略不适用于 Android 14-17：

- 从 API 34 起，App 不再收到这些 running/moderate/complete 等级；
- 这些常量在 API 35 被废弃；
- 有可见 Activity 的 App 在 UI 隐藏时会收到 `TRIM_MEMORY_UI_HIDDEN`；
- 保持非 UI 工作的进程，例如含 FGS 的进程，可能收到 `TRIM_MEMORY_BACKGROUND`；
- cached 进程可能很快被冻结，冻结后不能执行 GC、回调或采样。

官方 [`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)文档还提醒调用方不要只按精确值比较，因为以后可能加入中间等级。Android 14-17 的 SDK 可以用 `UI_HIDDEN` 和 `BACKGROUND` 释放可重建资源，却不能把已废弃的 running 等级当成实时压力传感器。

`ActivityManager.getMyMemoryState()` 能返回当前进程的 `importance` 与 `lastTrimLevel`，适合在一次状态快照中记录上下文。它也不能预测 MemoryLimiter 还剩多少空间。

## Cached App Freezer 改变了后台监控模型

Cached app freezer 从 Android 11 开始存在。[AOSP freezer 文档](https://source.android.com/docs/core/perf/cached-apps-freezer)规定，Android 14 及以上设备可在进程进入 cached 状态约 10 秒后冻结它；设备配置和豁免仍可能不同。冻结时所有线程停止获得 CPU 时间，定时器、采集线程、GC 与普通用户态代码都不会运行。

这一行为带来几条直接结论：

- 缓存进程没有“继续低频采样”的能力，采样缺口是预期状态；
- 解冻后只能记录一段不可观测窗口，不能补造冻结期间的 CPU、内存或网络样本；
- `RunningAppProcessInfo.importance >= IMPORTANCE_CACHED` 只表示进程重要性，不能证明该设备启用了 freezer 或进程已经冻结；
- 普通 App 没有公开的 freezer 状态查询 API；
- Android 14 以后，cached 状态下动态注册的广播通常排队到解冻后再投递；
- 向 frozen 进程发送同步 Binder 调用可能导致接收方被系统终止，退出原因为 `REASON_FREEZER`。

独立监控进程若进入 cached，也会面临相同问题。多进程 SDK 应避免让前台业务同步等待 cached 监控进程，并给 oneway 事件设置有界队列、时效和丢弃策略。

## 内存数据应使用公开 API，并保留测量语义

### PSS、RSS 与 heap 回答不同问题

| 指标 | 公开入口 | 含义与限制 |
|---|---|---|
| PSS | `Debug.getMemoryInfo()`、`Debug.getPss()`、`ActivityManager.getProcessMemoryInfo()` | 共享页按引用进程分摊；计算成本较高，会随共享关系变化 |
| RSS | API 35+ `Debug.getRss()`、退出记录 `getRss()` | 当前驻留页总量，包含共享页，不能跨进程直接相加 |
| Java heap | `Runtime`、`Debug.MemoryInfo.dalvik*` | 只描述 ART 管理的堆，不能代表 native、graphics 和映射 |
| native heap | `Debug.getNativeHeapAllocatedSize()` 等 | 主要描述 native allocator，不覆盖全部 native 映射与 graphics |
| 退出前 PSS/RSS | `ApplicationExitInfo` | 系统最近一次样本，可能为 0，也不是死亡瞬间值 |

Android 官方说明 PSS 计算较慢，RSS 更适合观察变化。PSS 不是“更高频就更准确”；连续调用可能增加 CPU 与 I/O 成本，页面共享变化还会改变分摊结果。

`ActivityManager.getProcessMemoryInfo()` 从 Android 10 起只向普通 App 返回同 UID 进程数据，并显著限制采样速率；调用过快会得到上一次结果。它是同步 Binder 调用，不适合作为热路径计时器。

下面的 Kotlin 代码用于在工作线程上采集当前进程的一份低频快照。字段名显式写出 kB，避免与 native heap 的 byte 单位混用。

```kotlin
data class ProcessMemorySnapshot(
    val elapsedRealtimeMs: Long,
    val totalPssKb: Int,
    val totalPrivateDirtyKb: Int,
    val rssKb: Long?,
    val nativeHeapAllocatedBytes: Long,
    val javaHeapUsedBytes: Long,
)

fun captureCurrentProcessMemory(): ProcessMemorySnapshot {
    val memoryInfo = Debug.MemoryInfo()
    Debug.getMemoryInfo(memoryInfo)

    val runtime = Runtime.getRuntime()
    return ProcessMemorySnapshot(
        elapsedRealtimeMs = SystemClock.elapsedRealtime(),
        totalPssKb = memoryInfo.totalPss,
        totalPrivateDirtyKb = memoryInfo.totalPrivateDirty,
        rssKb = if (Build.VERSION.SDK_INT >= 35) {
            Debug.getRss().takeIf { it > 0L }
        } else {
            null
        },
        nativeHeapAllocatedBytes = Debug.getNativeHeapAllocatedSize(),
        javaHeapUsedBytes = runtime.totalMemory() - runtime.freeMemory(),
    )
}
```

`Debug.getMemoryInfo()` 直接读取当前进程的低层数据，公开文档说明它可能看不到 graphics 等受保护分配。需要系统补充 memtrack 的同 UID 多进程调试时，可低频调用 `getProcessMemoryInfo()`，同时保留它的限速与重复样本语义。

### 不把 `/proc` 文件格式当成 App 兼容协议

`Debug.getPss()` 的公开说明指向 smaps。API 35 的 `Debug.getRss()` 以 status 中的 RSS 为基础；`android-17.0.0_r1` 的 JNI 实现还会加入可获得的 graphics memtrack 数据。平台内部怎样读取与聚合仍可随版本演进，普通 App 应优先使用公开 API，并以公开字段语义作为兼容边界。

`/proc/self/status`、`smaps` 和 `maps` 在某些设备上可读，不表示所有字段、权限和格式都是 Android SDK 契约。直接解析 `/proc` 的 native 组件必须把缺失、权限拒绝、字段变化和读取成本作为正常分支，并按系统 build 验证。跨进程 `/proc/<pid>` 不能作为第三方 APM 的线上数据源。

## 后台任务不提供持续采样时钟

### Foreground Service 不能只为 APM 常驻

从 Android 14 起，target 34+ 的 App 启动 FGS 时必须声明有效类型并满足该类型前提。“监控”不是现有标准 FGS 类型。`specialUse` 需要在 manifest 解释用途，并可能接受 Google Play 审核，它也不是通用常驻许可。

APM 可以在业务已经合法运行的可见或前台服务场景中记录该业务的性能，但不能为了维持监控而冒用 `dataSync`、`location`、`mediaPlayback` 等类型，也不能把监控需求当作启动 FGS 的用户价值。

### WorkManager 与 JobScheduler 只负责可延期工作

WorkManager 适合上传已持久化的诊断批次。任务仍受 App Standby、Doze、设备负载、内存和配额影响，执行时间不等于请求时间。expedited work 面向用户重要、需要尽快开始的短任务，也受系统配额控制；诊断上传不应默认占用 expedited 配额。

上报任务应：

- 设置网络、充电或存储等与产品要求一致的约束；
- 支持重复执行和服务端幂等；
- 在 quota 不足、进程重启和网络失败后按 WorkManager 语义重试；
- 记录 enqueue、实际开始、停止原因和成功确认；
- 不以 periodic work 的触发间隔计算性能指标时间轴。

前台运行期间可以由生命周期内的轻量调度器采集。进入后台后停止轮询，保留业务事件、系统回执和已落盘队列；进入前台或任务获得执行机会时再恢复。

## 一套可执行的降级状态机

| 状态 | 采集 | 本地处理 | 上报 |
|---|---|---|---|
| Foreground | 用户旅程、帧、网络、低频内存与业务指标 | 有界聚合、采样和脱敏 | 可直接批量发送或入队 |
| UI hidden / Background | 停止周期轮询，只保留必要业务事件 | 释放可重建缓存，写入小型状态摘要 | 普通 WorkManager，等待约束满足 |
| Cached / Frozen | 无用户态执行保证 | 不补采样 | 等待系统解冻 |
| Restart / Resume | 查询退出记录，注册 profiling 结果监听，读取待传队列 | 标记不可观测区间，去重与恢复 | 先传关键小记录，再按预算传大文件 |
| Memory pressure observed | 停止大对象和高成本 profile 请求 | 缩小 buffer、拒绝新批次、保存丢弃计数 | 不因压力立即启动额外网络工作 |

状态转换要由生命周期、任务回调和系统结果驱动。App 无法可靠探测“当前已被冻结”，因为被冻结时也没有执行代码的机会。

## ApplicationExitInfo 是事后证据，不是退出回调

Android 11 / API 30 起，`ActivityManager.getHistoricalProcessExitReasons()`提供历史退出记录。Android 17 还新增 `ApplicationExitInfo.AnrInfo`。使用时要保留以下限制：

- 历史记录数量与保留时间没有跨设备保证；
- `getPss()`、`getRss()` 是系统最近一次样本，0 表示可能尚未采样；
- `getTraceInputStream()` 可能为 `null`；
- ANR trace 与 API 31+ native crash tombstone protobuf 是不同格式；
- trace 位于全局循环缓冲，可能被新事件覆盖；
- 读取到记录不表示 APM 自己在退出前获得了运行机会。

下面的代码只识别官方规定的 Android 17 MemoryLimiter 标记，并把 0 内存值转成缺失值。

```kotlin
private const val MEMORY_LIMITER_MARKER = "MemoryLimiter:AnonSwap"

data class ExitSummary(
    val processName: String,
    val timestampMs: Long,
    val reason: Int,
    val status: Int,
    val pssKb: Long?,
    val rssKb: Long?,
    val memoryLimiterAnonSwap: Boolean,
)

fun readExitSummaries(
    context: Context,
    maxRecords: Int,
): List<ExitSummary> {
    require(maxRecords > 0)
    if (Build.VERSION.SDK_INT < 30) return emptyList()

    val activityManager = context.getSystemService(ActivityManager::class.java)
    return activityManager.getHistoricalProcessExitReasons(
        context.packageName,
        0,
        maxRecords,
    ).map { info ->
        ExitSummary(
            processName = info.processName,
            timestampMs = info.timestamp,
            reason = info.reason,
            status = info.status,
            pssKb = info.pss.takeIf { it > 0L },
            rssKb = info.rss.takeIf { it > 0L },
            memoryLimiterAnonSwap =
                Build.VERSION.SDK_INT >= 37 &&
                    info.reason == ApplicationExitInfo.REASON_OTHER &&
                    info.description?.contains(MEMORY_LIMITER_MARKER) == true,
        )
    }
}
```

读取端应保存包、进程、PID、UID、系统 build、App 版本和读取时间，并用进程、时间、reason、status 等组合字段去重。不要长期上传完整 `description`；除了有文档保证的精确标记，其余内容只用于受控诊断。

## ProfilingManager 补充系统证据，但不保证每次有文件

版本边界如下：

- API 35：`ProfilingManager.requestProfiling()`，App 主动请求 system trace、Java heap dump、heap profile 或 stack sampling；
- API 36：`ProfilingTrigger`、`addProfilingTriggers()` 和 ANR / fully-drawn trigger；
- API 37：增加 OOM、anomaly、cold start、excessive CPU、app compat 等 trigger。

Android 17 的 `TRIGGER_TYPE_ANOMALY` 可用于 MemoryLimiter 事件，公开文档说明该场景可能返回 heap dump。Java `OutOfMemoryError` 对应 `TRIGGER_TYPE_OOM`，两者不能合并。OOM trigger 还要求自定义 `UncaughtExceptionHandler` 继续调用系统默认 handler。

下面的代码用于在 Android 17 注册两类内存 trigger。应用定义的最小间隔由产品配置传入，系统还会应用自己的限流。

```kotlin
@RequiresApi(37)
fun registerMemoryProfilingTriggers(
    context: Context,
    executor: Executor,
    minPeriodHours: Int,
    listener: Consumer<ProfilingResult>,
) {
    require(minPeriodHours >= 0)

    val manager = context.getSystemService(ProfilingManager::class.java)
    manager.registerForAllProfilingResults(executor, listener)
    manager.addProfilingTriggers(
        listOf(
            ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANOMALY)
                .setRateLimitingPeriodHours(minPeriodHours)
                .build(),
            ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_OOM)
                .setRateLimitingPeriodHours(minPeriodHours)
                .build(),
        )
    )
}
```

系统 trigger 的结果只能通过全局监听器接收。若产生文件时 App 不在运行，系统可能在下次启动并重新注册监听器后投递。处理器必须检查 `ProfilingResult.errorCode`、`triggerType`、`tag` 和 `resultFilePath`，不能拼接内部目录，也不能按 trigger 名预设文件格式。

profiling 请求与 trigger 都受系统限流、设备覆盖、后台 trace 是否运行、存储与后处理状态影响。注册成功只表示系统知道 App 的兴趣，不表示每次事件都生成产物。

## Crash 与 ANR 的最低可用记录

“Crash、ANR、启动一定能完整采到”是不成立的。进程可被 `SIGKILL`、MemoryLimiter 或 LMKD 直接终止；Java OOM 时可能无法再分配对象；native signal handler 也有严格限制。

Java 未捕获异常处理器应：

- 只写入已经脱敏、结构固定、大小受限的最小记录；
- 避免在崩溃线程上发网络请求、等待锁或执行复杂序列化；
- 保留并调用原默认 handler，让平台完成正常 crash 处置；
- 允许写入失败，下一次启动再用 `ApplicationExitInfo` 补充。

Native crash handler 只能调用 async-signal-safe 操作。不能在 signal handler 中使用 JVM、分配器、普通日志、锁或复杂 `/proc/maps` 解析。需要自有 minidump 时，应采用经过验证的 crash reporter，并继续让 debuggerd/系统 handler 生成平台 tombstone。API 31+ 还可在下次启动从 `ApplicationExitInfo` 获取可选 tombstone protobuf。

ANR 依赖系统的 exit record、可选 trace、Android 16+ ANR profiling trigger，以及 App 在运行时已有的主线程和业务状态。任何一条都可能缺失，服务端要保留来源和完整度。

启动监控在 API 35+ 可结合 `ApplicationStartInfo` 的系统时间戳；TTID、TTFD 和业务 ready 仍是不同指标。`Application.onCreate()` 到 `onWindowFocusChanged()` 不是所有窗口模式和启动路径都通用的冷启动定义。

## 本地队列与上报要接受进程随时消失

### 在正常运行时提前保存关键状态

Android 没有生产环境可依赖的进程死亡回调，`Application.onTerminate()` 也不会在普通设备进程退出时调用。关键状态应在正常业务边界写入小型 journal，例如：

- 当前 session 与进程启动标识；
- App 可见性、最近用户旅程类别和阶段；
- 最近一份内存、网络、帧或任务聚合；
- 已排队事件范围、丢弃计数和 schema 版本。

journal 要有长度前缀或校验，容忍尾部被截断。文件数量与总大小必须有上限。重要但不应进入系统备份的数据可放 `noBackupFilesDir`；可重新生成的大文件可放 `cacheDir`，并接受系统清理。

### 上传采用幂等协议

一个稳健的诊断上传流程是：

1. 本地记录生成不可重复的 event ID，并在提交前完成脱敏。
2. WorkManager 读取已封口批次，发送时带 event ID 与内容 hash。
3. 服务端按 ID 幂等接收，返回明确确认。
4. 客户端只在确认后删除本地批次。
5. 中断或重复执行时重发同一批次，不生成新的事件。

Crash handler 负责留下最小本地证据，不负责“立即上传”。profiling 文件通常更大、更敏感，应单独排队、限制并发和保留期；退出摘要不应因大文件上传失败而被阻塞。

## 隐私边界从采集前开始

### 普通 App 不能依赖系统日志与 dumpsys

从 Android 4.1 / API 16 起，只有特权系统 App 才能获得完整 `READ_LOGS` 能力。[Android 日志信息泄露指南](https://developer.android.com/privacy-and-security/risks/log-info-disclosure)明确指出普通第三方 App 不能读取其他进程的 logcat。`DUMP` 同样是系统级权限。这个边界并非 Android 15 才出现。

APM 应收集自己产生的结构化事件，多进程 App 通过自有 IPC 或文件协议汇总。`dumpsys meminfo`、`gfxinfo`、完整 bugreport 和跨进程 Perfetto 适合 adb、实验室、用户主动诊断或特权组件，不是普通生产 App 的后台采集入口。

### “性能数据”也可能成为用户数据

帧时间或 PSS 单独看是数值；与精确时间、页面类名、URL、账号、设备标识和长期 session 组合后，可以恢复用户行为与设备特征。heap dump、ANR trace、tombstone、system trace 和日志的敏感度更高，可能包含字符串、路径、请求信息、对象字段与代码结构。

数据模型应：

- 用受控的页面/场景枚举替代任意 Activity、Fragment 或 Compose route 文本；
- URL 只保留经过允许的模板或低基数分类，不保存 query、token 和用户输入；
- 使用随机、可重置且有保留期的安装或会话标识，不使用 IMEI、MAC、序列号或 Android ID 充当“匿名 ID”；
- 在写盘前删除不需要的字段，避免先采全量再在服务端过滤；
- 对大文件设置访问审批、静态与传输保护、审计和自动删除；
- 让用户删除账号或撤回授权时同步清理关联诊断数据。

Google Play 要求 App 的 Data safety 声明覆盖第三方 SDK 的收集与共享行为。SDK 还应读取宿主传入的 consent/opt-out 状态；若产品承诺退出后停止收集，就应停止采集和上传并清理队列，不能自行把 crash/ANR 解释为默认豁免。

## 监控自身也需要观测

降级系统至少上报这些低成本计数：

- `capture_attempted`、`capture_succeeded`、`capture_skipped`；
- skip reason：后台、预算不足、unsupported、rate limited、storage full、consent disabled；
- 本地队列字节、事件数、最老事件年龄和丢弃原因；
- WorkManager enqueue、start、stop reason、retry 与 server ack；
- profiling 注册、回调、error code、无文件和文件处理结果；
- 内存采集耗时、重复样本与采集期间分配；
- SDK 版本、规则版本、Android API、系统 build 与设备分组。

这些指标的分母必须是“具备采集资格的会话”，不能把未获得授权、系统不支持或从未执行到初始化的设备混入成功率。监控 SDK 自己发生错误时要降级并保留计数，不能阻塞业务线程或吞掉业务异常。

## Android 17 验收清单

- 平台锚点为 `android-17.0.0_r1`，cgroup/freezer 锚点为 `android17-6.18-2026-06_r6`。
- MemoryLimiter 只在部分 Android 17 设备实施，不按 RAM 或机型猜测固定限制。
- 退出归因同时检查 `REASON_OTHER` 与精确标记 `MemoryLimiter:AnonSwap`。
- `memory.high` 被解释为内核节流边界，终止决定归于 Android MemoryLimiter 流程。
- Android 14-17 不使用已停止通知的 running/complete trim 等级控制采样。
- cached/frozen 期间不假设定时器、GC、Binder 或采集线程继续运行。
- 不用进程 importance 冒充 freezer 已启用或已经冻结的证据。
- PSS、RSS、Java heap、native heap 与退出前样本分别建模并写明单位。
- `getProcessMemoryInfo()` 处理同 UID 限制、同步 Binder、限速和重复结果。
- FGS 只服务符合类型与用户预期的前台任务，不为 APM 冒用类型。
- WorkManager 用于可延期、幂等的持久上传，不作为性能采样时钟。
- ProfilingManager 按 API 35/36/37 能力分层，trigger 结果允许缺失和延迟。
- Java crash handler 调用默认 handler；native handler 只做 async-signal-safe 工作。
- 普通 App 不依赖其他进程 logcat、dumpsys 或跨进程 `/proc`。
- heap、trace、日志和行为上下文按高敏感度数据设置权限、保留和删除。
- consent/opt-out、Data safety 与第三方 SDK 行为保持一致。

在 Android 17 上，可靠监控依赖的是清晰的状态、公开 API、可丢失的数据协议和系统事后证据。允许样本缺失、记录缺失原因，并让业务在监控关闭时保持原有语义，比维持一个看似连续但无法解释的后台曲线更重要。

## 源码与官方文档

- [Android 17 App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [AOSP `MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [AOSP `CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [AOSP `Debug.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java)
- [AOSP `ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP `ProfilingManager.java`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [Cached apps freezer](https://source.android.com/docs/core/perf/cached-apps-freezer)
- [ComponentCallbacks2](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [ActivityManager](https://developer.android.com/reference/android/app/ActivityManager)
- [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [WorkManager expedited work](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work#expedited)
- [Google Play Data safety](https://support.google.com/googleplay/android-developer/answer/10787469)
