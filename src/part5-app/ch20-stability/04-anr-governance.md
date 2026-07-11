---
title: "ANR 治理策略"
chapter: "20.4"
section: "20.4"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-11"
last_verified_against: "AOSP android-17.0.0_r1, kotlinx-coroutines 1.9.x, developer.android.com"
confidence: medium
drafted_date: "2026-05-11"
polish_count: 0
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastConstants.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ContentResolver.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/input/android/os/IInputConstants.aidl"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Service.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Binder.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/BroadcastReceiver.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderHelper.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/monitor.cc"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/workmanager"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md"
tags: [anr, main-thread, binder, lock-contention, watchdog, broadcast, contentprovider]
related_chapters: ["20.1", "9.1", "9.2", "9.3", "1.4", "1.5"]
pipeline_stage: ready-to-publish
task2b_result: fixed
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-07-12"
task6_result: pass-light-edit
last_task6_at: "2026-07-12T01:06:00+08:00"
last_task6_audit: "2026-07-12"
task6_reviewed_date: "2026-07-12"
task9_result: auto-fixed
task9_reviewed_date: "2026-06-02"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-11T20:30:00+08:00"
last_task6_review_log: "logs/review/2026-07-12-01-review.md"
task9_review_notes: "2026-07-11 Task9 idle audit auto-fix：按 android-17.0.0_r1 复核 ANR 阈值、Broadcast/Provider/FGS/Freezer/Binder 源码锚点；修正 ContentProvider timeout 常量、BroadcastReceiver 路径、CachedAppOptimizer freezer 锚点，并更新 AOSP sources 为 Android 17 固定链接。"
last_task9_review_log: "logs/deep-review/2026-07-11-20-audit.md"
task6_review_notes: "2026-05-23 Task6 08: revisiting 复审；清理 frontmatter 中的禁用词语境；Task9 ANR P0/P1 queue pending，未晋升。 2026-06-22 Task6 revisiting 复审：Task9 idle audit 补充 Android 14+ shortService FGS 计时器后回审；L1/L2 全部通过；applicable_versions 扩展至 Android 17 (API 37)；task9_result 确认 pass-tech-review；queue 无 pending，自动晋升 finalized。 2026-07-12 Task6 revisiting 复审：Task9 idle audit auto-fix（android-17 源码锚点修正）后回审；L1 修复 4 处（禁用词"链路"→"路径"、冗余副词"真的"、标点前空格、多余空行）；L2 全部通过；task9_result=auto-fixed 已接受；queue 无 pending，自动晋升 finalized。"
task2b_review_notes: "2026-06-02 Task2B fallback 修复 Task9 P0/P1：Dispatchers.IO 继承关系、FGS 晋升超时版本表、SIGQUIT 自进程权限边界；系统负载过滤降为标记/降权。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
last_task9_autofix_at: "2026-07-11"
last_task9_audit: "2026-07-11"
last_task9_audit_at: "2026-07-11T20:30:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-11-20-audit.md"
last_task9_audit_result: "auto-fixed"
last_task9_audit_notes: "idle audit auto-fix: corrected Android 17 source anchors, ContentProvider timeout constant, BroadcastReceiver path, and cached app freezer source path; returned to Task6 revisiting."
task2b_verifier_notes: "2026-07-11T23:25 Task2B Verifier: status finalized→ready-for-review (pipeline_stage=task6_pending, task6_state=revisiting but status=finalized blocked Task6 pickup). task9 auto-fix correctly set; chapter ready for Task6 revisiting re-review."
---

# ANR 治理策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）
- 🔹 ANR 触发场景与超时阈值
- 🔹 主线程瘦身策略与异步化
- 🔹 IPC（Binder）调用治理
- 🔹 锁竞争与死锁预防
- 🔹 ContentProvider / BroadcastReceiver 超时治理
- 🔹 ANR Watchdog 搭建
- 🔹 ANR 预警与主动发现
- 🔹 前后台 ANR 与系统负载过滤

### 导读
本节从系统超时窗口出发，沿主线程、Binder、锁、组件回调和应用侧 Watchdog 几条路径说明 ANR 治理动作。
<!-- outline-end -->

ANR 的分析和定位方法在 9.1-9.3 节已经讲过。这一节回答一个不同的问题：已知 ANR 的成因，怎么在工程里系统性地消除它。

ANR 治理的核心约束是：主线程必须在对应超时窗口内完成系统要求的响应。工程上可以从五个方向入手：主线程瘦身、IPC 调用治理、锁竞争治理、四大组件超时治理，以及应用侧 Watchdog 搭建。每个方向都需要明确治理手段和验证方法。

## ANR 触发场景与超时阈值

不同组件类型的 ANR 超时阈值不同，系统的检测机制也各不相同。治理 ANR 的第一步是区分自己面对的是哪种类型的 ANR：

| ANR 类型 | 超时阈值（AOSP 默认值） | 检测机制 | 典型成因 |
|----------|------------------------|---------|---------|
| Input dispatch | 5s（AOSP `DEFAULT_INPUT_DISPATCHING_TIMEOUT`，可通过 per-window/per-application timeout 调整） | InputDispatcher 检测触摸/按键事件在超时窗口内未送达 | 主线程阻塞导致 InputConsumer 无法处理事件 |
| BroadcastReceiver（前台） | 10s（Android 13 及以下）；10-20s（Android 14+，实际窗口取决于 `BroadcastConstants` 配置） | BroadcastQueue 检测 onReceive() 执行超时 | onReceive() 中执行同步 I/O 或 Binder 调用 |
| BroadcastReceiver（后台） | 60s（Android 13 及以下）；60-120s（Android 14+，实际窗口取决于 `BroadcastConstants` 配置） | 同上 | 后台广播处理链过长 |
| ContentProvider publish | 10s（AOSP `ContentResolver.CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`） | AMS 检测应用 publish provider 超时 | Application.onCreate() 或 ContentProvider.onCreate() 耗时 |
| Service（前台） | 20s（`ActivityManagerConstants.SERVICE_TIMEOUT`） | ActiveServices 检测 onCreate()/onStartCommand() 超时 | Service 生命周期回调中执行耗时操作 |
| Service（后台） | 200s（`ActivityManagerConstants.SERVICE_BACKGROUND_TIMEOUT`） | 同上 | 后台 Service 长时间运行 |
| FGS shortService（Android 14+） | 3min + 10s ANR 宽限（AOSP `mShortFgsTimeoutDuration` / `mShortFgsAnrExtraWaitDuration` 默认值） | ActiveServices 短 FGS 计时器触发 `SERVICE_SHORT_FGS_ANR_TIMEOUT_MSG` | `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE` 未及时 `stopSelf()` / `stopForeground()` |

上表中的超时值是 AOSP 默认值，厂商 ROM 可能调整（通常缩短）。在多数线上治理中，Input dispatch ANR 是优先排查对象，具体占比应以应用自己的 ANR 监控口径为准。

> 注意：上表超时值是 AOSP 默认值，厂商 ROM 可能调整（通常缩短）。Android 14+ 的广播超时由 `BroadcastConstants` 管理，窗口可拉长（CPU-starved、冷启动时间计入等场景），不宜写成固定值。有序广播的超时由 `BroadcastRecord.timeout` 控制，每个接收者独立计时。

## 主线程瘦身策略与异步化

主线程上任何超过超时阈值的同步操作都是 ANR 候选项。治理的第一步是识别哪些操作不应该出现在主线程上，再判断这些操作是否可以优化。

### 主线程耗时操作的分类

按治理难度从低到高排列：

| 类型 | 典型场景 | 治理难度 |
|------|----------|----------|
| 磁盘 I/O | SharedPreferences.apply() 在 onPause 被强制同步、日志写入、数据库查询 | 低 |
| 网络 I/O | 同步 HTTP 请求、DNS 解析阻塞 | 低（但在低版本或第三方 SDK 里仍然常见） |
| CPU 密集计算 | JSON 解析大对象、图片解码、正则匹配长文本 | 中 |
| Binder 同步调用 | 调用系统服务（PackageManager、ActivityManager）获取数据 | 中 |
| 锁等待 | 主线程持锁等后台线程、或其他线程持锁主线程需要 | 高 |

前两类治理手段明确：全部移到子线程。CPU 密集型和 Binder 调用需要按场景判断。锁等待涉及多线程协作，单独在后文展开。

### 异步化的执行模式

把操作移到子线程不只是 `new Thread().start()`。工程上有三种常用模式：

**1. Handler + ThreadExecutor 模式**

适用于需要回调主线程更新 UI 的场景。核心是保证"异步执行 → 主线程回调"这条路径上没有意外阻塞：

```java
// 异步执行
executorService.execute(() -> {
    byte[] data = loadFromDisk(filePath);  // I/O 操作放在子线程
    handler.post(() -> updateUI(data));     // 结果回主线程
});
```

关键约束：`handler.post()` 抛回主线程的 Runnable 也必须轻量。如果 `updateUI()` 里又做了布局计算或数据库操作，只是把阻塞从一个位置挪到了另一个位置。

**2. Kotlin 协程模式**

Kotlin 协程用 `Dispatchers.IO` 和 `Dispatchers.Default` 把操作从主线程调度出去，用 `withContext(Dispatchers.Main)` 回到主线程。和 Handler 模式本质相同，只是写法更简洁：

```kotlin
suspend fun loadData(): Data = withContext(Dispatchers.IO) {
    // I/O 操作自动在 IO 线程池执行
    val raw = file.readBytes()
    parseData(raw)
}
```

[已验证: 官方文档, developer.android.com/kotlin/coroutines]

协程治理 ANR 时需要注意一点：`Dispatchers.Main` 上的协程仍然跑在主线程。如果 `withContext(Dispatchers.Main)` 代码块里做了耗时操作，和直接在主线程做没有区别。协程只是让异步代码更容易写，不自动解决线程安全问题。

**3. WorkManager 后台任务模式**

不需要立即返回结果的任务（数据上报、缓存清理、日志轮转）用 WorkManager 处理。这类任务的特点是"迟早要做，但不影响当前用户体验"：

```kotlin
val uploadWork = OneTimeWorkRequestBuilder<UploadWorker>()
    .setConstraints(Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .build())
    .build()
WorkManager.getInstance(context).enqueue(uploadWork)
```

[已验证: AndroidX WorkManager 官方文档, developer.android.com/topic/libraries/architecture/workmanager]

### 主线程瘦身的安全清单

把同步操作改异步时，容易踩到以下坑：

- **SharedPreferences 的 commit() → apply() 陷阱**：`apply()` 是异步写磁盘没错，但在 `onPause()` / `onStop()` / `Activity.onSaveInstanceState()` 等生命周期回调里，系统会等待所有 `apply()` 完成后才继续。如果 `apply()` 积压了大量未完成的写操作，这些回调里主线程仍然会被阻塞。解决方案：高频写入场景用内存缓存 + 批量异步落盘，不要每改一个值就 `apply()` 一次。
- **StrictMode 的价值**：在开发阶段启用 `StrictMode`，它能在主线程 I/O 和网络操作发生时直接抛异常，比线上 ANR 发现成本低两个数量级。
- **第三方 SDK 的主线程调用**：很多第三方 SDK（广告、推送、统计）在初始化或回调里做磁盘 I/O 或网络请求，而调用时机往往是 `Application.onCreate()` 或 `Activity.onCreate()`——这两个都在主线程。治理手段：SDK 初始化移到子线程（如果 SDK 支持），或者用 `ContentProvider` 的延迟初始化机制（详见后文）。

### Kotlin 协程内部调度与 ANR 关系

协程让异步代码更易写，但它不自动消除 ANR 风险。理解 Dispatchers 的线程池和调度行为，才能判断协程在什么场景下会间接导致主线程阻塞。本节基于 kotlinx-coroutines 1.9.x 源码说明关键点。

#### Dispatchers.IO 与 Default 共享线程池

Dispatchers.Default 的内部实现是 `DefaultScheduler`（继承 `SchedulerCoroutineDispatcher`）。Dispatchers.IO 的内部实现是 `DefaultIoScheduler`（实现 `ExecutorCoroutineDispatcher` / `Executor`），它通过 `UnlimitedIoScheduler.limitedParallelism()` 把 blocking 任务委托给 `DefaultScheduler.dispatchWithContext(..., BlockingContext, ...)`。两者共享底层 worker 资源，但继承关系和调度语义不同。

```kotlin
// kotlinx-coroutines-core/jvm/src/scheduling/Dispatcher.kt
internal object DefaultScheduler : SchedulerCoroutineDispatcher(
    CORE_POOL_SIZE, MAX_POOL_SIZE, ...
)

private object UnlimitedIoScheduler : CoroutineDispatcher() {
    // 内部调用 DefaultScheduler.dispatchWithContext(block, BlockingContext, ...)
}

internal object DefaultIoScheduler : ExecutorCoroutineDispatcher(), Executor {
    private val default = UnlimitedIoScheduler.limitedParallelism(
        systemProp(IO_PARALLELISM_PROPERTY_NAME, 64.coerceAtLeast(AVAILABLE_PROCESSORS))
    )
    override fun dispatch(context: CoroutineContext, block: Runnable) {
        default.dispatch(context, block)  // 路由到 DefaultScheduler
    }
}
```

关键注释（Dispatcher.kt 官方文档）：

> "This dispatcher and its views share threads with the Default dispatcher, so using `withContext(Dispatchers.IO) { ... }` when already running on the Default dispatcher typically does not lead to an actual switching to another thread."

**ANR 治理启示**：在 Default 线程上用 `withContext(Dispatchers.IO)` 不会发生线程切换，只是改变了 TaskContext（从 NonBlockingContext 变为 BlockingContext）。可观察的线程切换开销来自 blocking 任务释放 CPU 令牌后调度器唤醒/创建新 worker 的开销。

#### CoroutineScheduler 的 CPU 令牌机制

CoroutineScheduler 用"CPU 令牌"机制隔离 CPU 密集型和 blocking 任务：

```kotlin
// kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt
enum class WorkerState {
    CPU_ACQUIRED,   // 持有 CPU 令牌，只执行 CPU 任务或 steal CPU 任务
    BLOCKING,       // 执行 blocking 任务，释放 CPU 令牌
    PARKING,        // 空闲停车
    DORMANT,        // 不再需要的 worker
    TERMINATED
}

// Worker 寻找任务时的调度决策（行 200-230）：
while (true) {
    if (tryAcquireCpuPermit()) return findAnyTask(mayHaveLocalTasks)
    // 无法获取 CPU 令牌 → 只能执行 blocking 任务
    return findBlockingTask()
}
```

**ANR 治理启示**：如果一个 worker 在执行 blocking 任务（TaskContext = BlockingContext）时阻塞（例如无限期等待 I/O），它不会影响持有 CPU 令牌的 worker 处理 CPU 任务。但一旦 blocking 任务占满所有 worker，主线程上的 withContext(Dispatchers.IO) 任务就必须排队等待。

#### Dispatchers.Main 的 Handler 降级逻辑

Android 上的 Dispatchers.Main 基于 Handler。**关键风险**：Handler 关闭时，任务会被重新路由到 Dispatchers.IO：

```kotlin
// ui/kotlinx-coroutines-android/src/HandlerDispatcher.kt
override fun dispatch(context: CoroutineContext, block: Runnable) {
    if (!handler.post(block)) {
        cancelOnRejection(context, block)  // Handler 关闭时触发
    }
}

private fun cancelOnRejection(context: CoroutineContext, block: Runnable) {
    context.cancel(CancellationException("..."))
    Dispatchers.IO.dispatch(context, block)  // 降级到 IO
}
```

**降级触发条件**：`handler.post()` 返回 false 的唯一原因是底层 Looper 正在退出（`Looper.quit()` 已调用）。`Dispatchers.Main` 包装的是主线程 Looper，它在正常应用生命周期内不会退出，所以这条降级路径对主线程 ANR 分析来说基本不可达。Handler 降级更多出现在自定义 Handler 关联的子线程 Looper 被 quit() 的场景。

**主线程 ANR 的协程侧成因**：Handler 队列积压。主线程被一个长操作阻塞时，后续通过 `withContext(Dispatchers.Main)` 投递的恢复协程全部排在 Handler 队列后面。这些等待恢复的协程如果持有其他线程需要的资源（锁、信号量、Channel），就会形成跨线程的级联阻塞。阻塞解除后，积压的消息仍需逐个执行，新投递的 Runnable 排在队尾，响应延迟被放大。

#### Dispatchers.IO 的 unlimited 线程特性

Dispatchers.IO.limitedParallelism() 的视图**不共享 parallelism 限制**：

> "Despite not abiding by Dispatchers.IO's parallelism restrictions, its views share threads and resources with it."

```kotlin
// Dispatchers.kt 文档注释
// 100 threads for MySQL connection
val myMysqlDbDispatcher = Dispatchers.IO.limitedParallelism(100)
// 60 threads for MongoDB connection
val myMongoDbDispatcher = Dispatchers.IO.limitedParallelism(60)
// Peak: 64 + 100 + 60 threads possible
```

**ANR 治理启示**：`limitedParallelism(n)` 通过 worker 计数器严格限制该视图同时向底层调度器投递的任务数，`n` 表示强制并发上限。但线程数仍可能超过 `n`，原因在底层调度器：当视图内的任务在 worker 上执行并进入 BLOCKING 状态，CoroutineScheduler 会释放该 worker 的 CPU 令牌并创建新 worker 服务其他任务。多个视图同时存在阻塞任务时，底层线程数上限是 `MAX_POOL_SIZE`（默认 256），线程调度开销和上下文切换成本会显著上升。

#### 协程 ANR 的本质

协程不自动防 ANR。`withContext(Dispatchers.Main)` 的代码仍然在主线程执行：

```kotlin
// 错误用法：
suspend fun doHeavyWork() {
    withContext(Dispatchers.Main) {
        database.query()  // 仍然阻塞主线程！
    }
}

// 正确用法：
suspend fun doHeavyWork() = withContext(Dispatchers.IO) {
    database.query()  // 在 IO 线程执行
}
// UI 更新时才回主线程：
suspend fun updateUI() = withContext(Dispatchers.Main) {
    textView.text = data  // 仅必要的 UI 操作
}
```

## IPC（Binder）调用治理

Binder 是 Android 进程间通信的基础设施。应用通过 Binder 和系统服务（AMS、PMS、WMS）交互，也通过 Binder 和其他应用交互。Binder 调用的特殊性在于：即使调用方在子线程，如果对方进程没有响应，调用方的线程也会被阻塞。而当这个调用发生在主线程时，就有 ANR 风险。

### Binder 调用导致 ANR 的典型路径

1. **主线程直接调用系统服务**：`PackageManager.getPackageInfo()`、`ActivityManager.getRunningAppProcesses()` 等。这些调用在正常情况下耗时极短（< 1ms），但在系统负载高时可能飙到数百毫秒。
2. **主线程等待子线程的 Binder 调用结果**：主线程通过 `Future.get()` 或 `CountDownLatch.await()` 等待一个包含 Binder 调用的异步任务，如果 Binder 调用阻塞，主线程也会被间接阻塞。
3. **Binder 调用触发对方的 ANR**：应用作为 Service 提供方时，如果 `onBind()` / `onTransact()` 处理慢，调用方会触发 ANR。

### Binder 调用的治理策略

**避免在主线程调用系统服务获取数据。** 这是最直接的治理手段。在工程实践中，以下场景需要特别注意：

- **PackageManager 查询**：在低端设备上 `getInstalledPackages()` 可能需要 50-200ms。做法是在应用启动时一次性查询并缓存结果，后续直接读缓存。
- **ActivityManager 进程查询**：`getRunningAppProcesses()` 在 Android 10+ 已经不返回其他应用的信息，不要依赖它做业务判断。
- **WindowManager 的同步事务**：`WindowManager.addView()` / `updateViewLayout()` 内部走 Binder 调用到 WindowManagerService。如果 WMS 处理队列繁忙，调用可能阻塞。

**设置 Binder 调用超时。** Android 平台的同步 Binder 调用本身没有通用的调用超时 API。`Binder.setCallingWorkSourceUid(int)` 只做调用方 UID 归因，不提供超时控制；`Binder.allowBlocking(IBinder)` 只关闭 blocking warning 日志，也不提供超时控制。应用层能做的是在异步调用外部 Service 时，用带超时的 `Future.get(timeout)` 或协程 `withTimeout` 降级，而不是无限等待：

```java
Future<String> result = executor.submit(() -> remoteService.getData());
try {
    String data = result.get(2, TimeUnit.SECONDS);  // 最多等 2 秒
} catch (TimeoutException e) {
    // 超时降级处理
}
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/Binder.java]

**监控 Binder 调用耗时。** 在线上环境中，通过 `BinderProxy.transact()` 的 Hook 或者 AOP 方式记录每次 Binder 调用的耗时。微信团队的实践是：在 `BinderProxy.transactNative()` 的入口和出口插桩，统计调用次数和耗时分布，发现异常 Binder 调用后推动对应模块治理。

## 锁竞争与死锁预防

锁竞争导致的 ANR 有一个特征：在 traces.txt 里，主线程的堆栈显示为 `BLOCKED` 状态，等待某个 `monitor`。这类 ANR 的治理难点不在于定位（traces.txt 通常指向明确的锁对象），而在于修复——改锁的粒度和策略往往牵动多线程架构。

### 锁竞争的常见模式

**模式一：主线程等后台线程释放锁**

```text
"main" prio=5 tid=1 BLOCKED
  | waiting to lock <0x0f3a4b5c> (a java.lang.Object) held by tid=15
  at com.example.DataManager.getData(DataManager.java:87)
```

后台线程（tid=15）持锁做耗时操作，主线程需要同一把锁来读取数据。修复方向：

- 缩小锁的粒度：把 `synchronized(dataManager)` 改为只锁住实际需要保护的数据结构。
- 读写分离：读操作用 `ReadWriteLock` 的读锁，写操作用写锁，读操作之间不互斥。
- Copy-on-Write：写操作先复制一份，改完再原子替换引用，读操作完全无锁。

**模式二：死锁——两个线程互相等待**

```text
"main" prio=5 tid=1 BLOCKED
  | waiting to lock <0x0a1b2c3d> held by tid=8
"Worker-1" prio=5 tid=8 BLOCKED
  | waiting to lock <0x0f3a4b5c> held by tid=1
```

主线程持有锁 A，等锁 B；后台线程持有锁 B，等锁 A。这是经典的死锁。修复手段：

- **锁排序**：所有需要同时持有多把锁的代码，按固定顺序获取锁（比如先 A 后 B），打破循环等待条件。
- **tryLock 带超时**：用 `ReentrantLock.tryLock(timeout)` 替代 `synchronized`，超时返回 false 后走降级逻辑，避免无限等待。
- **锁消除**：检查被保护的资源是否需要锁。很多场景下用 `ConcurrentHashMap`、`AtomicReference` 或 `volatile` 就够了，不需要显式加锁。

**模式三：synchronized 方法中的 I/O 操作**

锁的持有时间取决于锁内代码的执行时间。如果 `synchronized` 方法里包含磁盘 I/O 或网络请求，锁的持有时间会被 I/O 延迟放大。在高负载设备上，一个 `synchronized` 块里的 10ms 文件读取可能变成 500ms，直接导致等待这把锁的主线程 ANR。

[已验证: AOSP android-17.0.0_r1, art/runtime/monitor.cc — ART 的 monitor 实现中，synchronized 块的 entry/exit 通过 monitor enter/exit 指令实现，持有期间其他线程进入 BLOCKED 状态]

### 锁治理的工程规范

1. **主线程不持锁**。如果主线程需要访问共享数据，用无锁方案（Copy-on-Write、Atomic 类）或者把数据准备逻辑完全放在后台线程。
2. **锁内不做 I/O**。任何可能阻塞的操作（磁盘、网络、Binder 调用）都不应该在 `synchronized` 块内。
3. **避免嵌套锁**。需要同时操作多个共享资源时，用一把粗粒度锁保护所有资源，而不是嵌套多把细粒度锁。
4. **线上监控**：定期 dump 主线程堆栈（通过 `Thread.getStackTrace()` 或 SIGQUIT 信号），统计主线程处于 `BLOCKED` 状态的频率。如果发现某把锁频繁出现在主线程的等待堆栈中，标记为高优先级治理对象。

## ContentProvider / BroadcastReceiver 超时治理

ContentProvider 的 ANR 超时阈值是 10 秒（publish provider）。BroadcastReceiver 的基础超时在 Android 13 及以下是前台 10 秒 / 后台 60 秒；Android 14+ 会在 `BroadcastConstants` 基础值上按 CPU-starved 等场景拉长到前台 10-20 秒、后台 60-120 秒。有序广播按每个接收者独立计时。完整的阈值表见 9.2 节。

这两种 ANR 的治理思路和主线程 ANR 不同：治理重点从单个操作耗时，转向减少系统回调里的工作量。

### ContentProvider 超时治理

ContentProvider 的超时发生在 `ActivityManagerService` 等待应用 publish provider 时。触发场景：

1. **应用启动时 ContentProvider 初始化过重**。在 `Application.onCreate()` 执行前，系统要求应用 publish 所有在 manifest 中声明的 ContentProvider。如果某个 ContentProvider 的 `onCreate()` 里做了大量初始化（SDK 初始化、数据库创建、文件读取），publish 就会被延迟。系统等待 10 秒后触发 ANR。
2. **多个 ContentProvider 串行初始化**。Android 按 manifest 中的声明顺序逐个调用 ContentProvider 的 `onCreate()`。如果应用声明了多个 ContentProvider（很多第三方 SDK 通过 ContentProvider 做自动初始化），初始化时间会累加。

治理手段：

- **延迟初始化**：`AppComponentFactory.instantiateProvider()` 只提供实例化 hook，返回的 Provider 对象尚无 Context，不能用于控制初始化时机。实际可用的做法是在 ContentProvider 的 `onCreate()` 里只做极轻量的注册操作，实质的初始化工作放到首次调用 `query()` / `insert()` 时再触发（lazy init）。
- **App Startup 统一管理**：用 AndroidX App Startup 的 `Initializer` 替代各 SDK 自注册 ContentProvider，在 manifest 中只保留一个 `InitializationProvider`，按依赖顺序统一调度初始化。
- **精简 ContentProvider 数量**：检查 manifest 中声明的 ContentProvider，移除不必要的。很多第三方 SDK 提供了关闭自动初始化的开关（`enable = false`），改用手动初始化。
- **启动时序优化**：把 ContentProvider 初始化纳入启动框架统一调度（详见 21.2 节），控制并发数和依赖关系。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java]

### BroadcastReceiver 超时治理

BroadcastReceiver 的 ANR 发生在 `onReceive()` 执行超过阈值时。关键约束：`onReceive()` 在主线程执行。`goAsync()` 允许在 `onReceive()` 中调用 `PendingResult` 把工作移到其他线程，但广播执行超时仍覆盖到 `PendingResult.finish()` 为止——超时窗口不会因为 `goAsync()` 而消失。

治理手段：

- **onReceive() 只做转发**：收到广播后，把实际处理逻辑交给 `JobScheduler` / `WorkManager` / `Coroutine` 在后台执行。`onReceive()` 本身只做参数解析和任务调度。
- **用 goAsync() 延长处理窗口**：`BroadcastReceiver.goAsync()` 不新增超时预算，只是延续同一个广播超时窗口——从 `onReceive()` 开始到 `PendingResult.finish()` 返回，仍然受原广播超时约束。正确用法是在 `goAsync()` 的窗口内启动异步任务，然后在任务完成后调用 `PendingResult.finish()`。
- **静态广播 → 动态广播**：如果不需要在应用未运行时接收广播，把静态注册的 `BroadcastReceiver` 改为动态注册。动态注册可以减少应用未运行时被唤醒的广播面，但 `onReceive()` / `goAsync()` 仍受广播执行时间限制——系统不因注册方式不同而豁免超时。

```kotlin
// goAsync 的正确用法
override fun onReceive(context: Context, intent: Intent) {
    val pendingResult = goAsync()
    CoroutineScope(Dispatchers.IO).launch {
        try {
            processData(intent)  // 在 IO 线程处理
        } finally {
            pendingResult.finish()  // 必须调用，否则 ANR 仍会发生
        }
    }
}
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/content/BroadcastReceiver.java]

### Service 超时补充

Service 的前台生命周期超时是 `SERVICE_TIMEOUT` 默认 20 秒，后台 `SERVICE_BACKGROUND_TIMEOUT` 默认 200 秒。FGS 晋升超时是独立的计时器（见下方）。治理要点：

- `onCreate()` 和 `onStartCommand()` 都在主线程执行。如果 `onStartCommand()` 需要做耗时操作，启动一个后台线程来处理，然后立即返回 `START_STICKY` 或 `START_NOT_STICKY`。
- FGS 晋升超时（`startForegroundService()` → `startForeground()`）：Android 8 引入此约束，排查时按目标系统源码中的配置确认，不要统一写 5s。Android 10-12 的核心窗口来自 `ActiveServices.SERVICE_START_FOREGROUND_TIMEOUT`，默认 10s；Android 13+ 改为 `ActivityManagerConstants.mServiceStartForegroundTimeoutMs` 默认 30s，超时后再等待 `mServiceStartForegroundAnrDelayMs` 默认 10s 触发 ANR。此外 Android 12+ 还有 FGS 启动限制（`ForegroundServiceStartNotAllowedException`），需要满足豁免条件才能从后台启动前台 Service。
- Android 14+ 的 `FOREGROUND_SERVICE_TYPE_SHORT_SERVICE` 还有类型级计时器：AOSP 默认 3 分钟，超时后调用 `Service.onTimeout()`；如果再过 `short_fgs_anr_extra_wait_duration` 默认 10 秒仍未停止，`ActiveServices.onShortFgsAnrTimeout()` 触发 ANR。这个计时器与普通 Service 生命周期超时、FGS 晋升超时相互独立。
- 普通前台 Service 生命周期执行超时（`onCreate()`/`onStartCommand()`）：`ActivityManagerConstants.SERVICE_TIMEOUT` 默认 20s（前台），`SERVICE_BACKGROUND_TIMEOUT` 默认 200s（后台）。两者与 FGS 晋升超时是独立的计时器。

[已验证: AOSP android-14.0.0_r1 - android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java；AOSP android-16.0.0_r1 / android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActiveServices.java]

## ANR Watchdog 搭建

ANR Watchdog 是应用侧的 ANR 检测机制，用于在系统弹出 ANR 对话框之前就发现主线程阻塞。

这里需要区分两层检测。第一层是系统的 ANR 检测——上表所列的 ANR 类型各有独立的超时阈值和检测逻辑。第二层是应用侧的 Watchdog，它是一套独立的监测线程，不依赖系统信号，通过主动探测主线程的响应性来判断。Watchdog 的检测间隔和阈值由应用自己设定，通常比系统阈值低，目的是在系统判定 ANR 之前发出预警。

### 工作原理

Watchdog 的核心是一个定期向主线程投递 `Runnable` 的监测线程：

1. 监测线程每 N 毫秒向主线程的 `Handler` 投递一个 `Runnable`，同时记录投递时间戳。
2. 下一个周期，监测线程检查上一个 `Runnable` 是否已被主线程执行。
3. 如果未被执行且超过阈值，判定主线程阻塞。

```java
public class ANRWatchdog {
    private static final long CHECK_INTERVAL_MS = 5000;  // 5 秒检测一次
    private volatile long mainThreadTick = 0;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private final Runnable ticker = () -> mainThreadTick = SystemClock.uptimeMillis();

    public void start() {
        Thread watchdogThread = new Thread(() -> {
            while (true) {
                mainThreadTick = 0;
                mainHandler.post(ticker);
                try {
                    Thread.sleep(CHECK_INTERVAL_MS);
                } catch (InterruptedException e) {
                    return;
                }
                if (mainThreadTick == 0) {
                    // 主线程在 CHECK_INTERVAL_MS 内没有执行 ticker
                    // 可能阻塞了，触发上报
                    onANRSuspected();
                }
            }
        }, "ANR-Watchdog");
        watchdogThread.start();
    }
}
```

监测线程与主线程的交互时序如下：

1. 监测线程将 `mainThreadTick` 置 0（`volatile` 写，对所有线程立即可见）
2. 监测线程通过 `mainHandler.post(ticker)` 将 ticker 投递到主线程的 Handler 队列
3. 监测线程 `Thread.sleep(CHECK_INTERVAL_MS)` 进入等待
4. 主线程 Looper 取出 ticker 并执行，将 `mainThreadTick` 设为当前时间（`volatile` 写）
5. 监测线程唤醒，检查 `mainThreadTick` 是否仍为 0
6. `mainThreadTick == 0` → 主线程在整个检测周期内没有执行 ticker → 判定阻塞

`volatile` 保证步骤 1 和 4 的写入对所有线程可见，不需要额外同步。检测存在一个盲区：ticker 可能在监测线程检查之后、`onANRSuspected()` 执行之前被主线程处理。这会导致偶发误报，通过"连续 2-3 次检测确认"来消除（见参数调优小节）。

这段代码是简化版本，生产环境的 Watchdog 需要处理更多细节：误报过滤、多次确认、主线程堆栈 dump、上报策略等。

### Watchdog 的参数调优

- **检测间隔**：通常设为 2-5 秒。间隔太短会频繁误报（主线程可能在正常处理一帧），间隔太长会漏报。
- **确认次数**：连续 2-3 次检测主线程未响应才判定为 ANR 嫌疑。单次检测可能只是主线程在处理一个稍长的 Message。
- **阈值 vs 系统阈值的关系**：Watchdog 的阈值通常设为 3 秒（比系统的 5 秒 Input ANR 阈值低），这样能在系统判定 ANR 之前就发出告警。

### 主线程堆栈 Dump

当 Watchdog 检测到主线程阻塞时，需要 dump 主线程的调用栈来做分析。方法有两种：

1. **Thread.getStackTrace()**：从监测线程调用 `mainThread.getStackTrace()`。这是最简单的方式，但有一个限制——如果主线程正处于 `BLOCKED` 状态（等锁），`getStackTrace()` 可能拿不到有意义的堆栈。
2. **SIGQUIT 信号**：向自进程发送 `SIGQUIT` 信号可以触发 ART 虚拟机 dump 本进程线程堆栈，这个动作本身不需要 root 或 `android.permission.DUMP`。受权限限制的是读取系统写入的 `/data/anr` 产物，或对其他进程抓完整 dump；普通应用在线上环境通常拿不到这些文件。

生产环境通常用方法一，因为它不依赖系统 traces 文件。如果主线程堆栈信息不够丰富，可以同时采样其他关键线程（如 Binder 线程、RenderThread）的堆栈作为补充；SIGQUIT 路径更适合内部调试包或具备日志回收能力的灰度环境。

### 上报与告警

Watchdog 检测到主线程阻塞后，上报的数据应该包含：

- 主线程堆栈（最关键）
- 阻塞时长估算（检测间隔 × 确认次数）
- 当时进程的 CPU 使用率（通过 `/proc/self/stat` 读取）
- 内存状态（`Debug.getMemoryInfo()`）
- 是否有正在进行的 Binder 调用（通过线程栈采样中 `BinderProxy.transactNative` / `Binder.execTransact` 帧的出现频率间接判断，或在具备权限时用 SIGQUIT / debuggerd 获取完整线程状态）

这些数据聚合后，按堆栈签名聚类，就能看到哪些代码路径是高频的 ANR 嫌疑点。

## ANR 预警与主动发现

线上 ANR 治理除了修复已知 ANR，还要发现尚未被系统判定的主线程阻塞趋势。以下是几种预警手段：

### 主线程 Looper 监控

在主线程 Looper 的每个 Message 分发前后插桩，记录单个 Message 的处理耗时。超过阈值（如 500ms）但未触发系统 ANR 的消息就是"准 ANR"——它在当前设备上没超时，但在更慢的设备或更高负载下可能触发。

```java
// 基于 Looper.getMainLooper().setMessageLogging() 的监控
public class LooperMonitor implements Printer {
    private long startTime = 0;

    @Override
    public void println(String x) {
        if (x.startsWith(">>>>> Dispatching to Handler")) {
            startTime = SystemClock.uptimeMillis();
        } else if (x.startsWith("<<<<< Finished to Handler")) {
            long duration = SystemClock.uptimeMillis() - startTime;
            if (duration > 500) {  // 500ms 预警阈值
                // 记录主线程堆栈和耗时，用于聚类分析
                onMainThreadStall(duration);
            }
        }
    }
}

// 注册
Looper.getMainLooper().setMessageLogging(new LooperMonitor());
```

### Binder 调用耗时监控

Binder 调用在主线程上的阻塞时间直接影响 ANR 风险。通过 `BinderProxy.transactNative()` 的 AOP 插桩，记录每次调用的对端进程、接口描述符和耗时。超过 50ms 的 Binder 调用需要重点关注。

### 预警数据的聚合与分析

预警数据的价值在于趋势发现，而不是单次告警。将"准 ANR"事件按主线程堆栈签名聚类，就能看到哪些代码路径在逼近 ANR 阈值，在它们触发系统 ANR 之前进行治理。

## 后台 ANR 与前台 ANR 的差异化治理

ANR 的严重程度取决于触发时应用的状态。前台 ANR 用户可以直接感知（弹出对话框），治理优先级最高。后台 ANR 用户看不到对话框（系统静默处理），但在 Android 10+，后台 ANR 同样会被 Google Play Console 统计并影响应用评分。

### 前台 ANR

前台 ANR 的治理方向是"消除"。用户看到了无响应对话框，体验已经受损，所以每次前台 ANR 都需要定位并修复。

治理重点：
- Input ANR（触摸/按键无响应 5 秒）：占前台 ANR 的大多数。通常由主线程直接阻塞导致，通过 Watchdog 和 traces.txt 定位。
- 生命周期 ANR（Service/Broadcast/Provider 超时）：由系统回调中的耗时操作导致。治理手段在前文已展开。

### 后台 ANR

后台 ANR 的治理方向是"控制"而非"消除"。后台 ANR 的成因更复杂：

- 系统在低内存条件下杀后台进程时，进程可能在执行清理逻辑，来不及响应系统回调。
- 后台 Service 的 200 秒超时虽然很长，但如果进程被系统冻结（Android 11+ 的 CachedAppFreezer），解冻后可能来不及在超时窗口内完成工作。
- JobScheduler 和 WorkManager 的超时行为在不同厂商 ROM 上不一致。

治理策略：
- **减少后台 Service 的使用**：用 `JobScheduler` / `WorkManager` 替代长时间运行的后台 Service。
- **处理系统冻结/解冻**：在 `onStartCommand()` 中检查进程是否刚从冻结状态恢复（通过时间差判断），如果是，跳过非必要操作直接返回。
- **过滤上报噪声**：后台 ANR 中有大量"系统杀进程导致的假 ANR"——进程已经被杀，但 ANR 日志已经被记录。在 Watchdog 上报时检查 `ActivityManager.getRunningAppProcesses()` 中本进程的状态，过滤掉这类噪声。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java — cached app freezer 实现]

## 系统负载导致的 ANR 识别与过滤

ANR 不一定都是应用代码的问题。低端设备、内存紧张、系统服务繁忙时，应用的正常操作也可能被系统拖慢到触发 ANR。这类 ANR 如果当成应用 bug 治理，投入产出比极低。

### 系统负载 ANR 的特征

在 traces.txt 和 event log 中，如果看到以下特征，系统负载很可能是主因：

- **主线程堆栈显示 `nativePollOnce`**：主线程在 Looper 中等待下一个 Message，没有在执行应用回调。它只能说明应用主线程当时处于空闲等待状态，还要结合 system_server、Binder 线程和 input dispatch 相关堆栈确认是否为系统侧阻塞。
- **event log 中 `am_anr` 前后有大量 `am_proc_died` / `am_kill`**：系统在密集杀进程，内存压力极大。
- **CPU iowait 异常升高**：设备存储 I/O 瓶颈严重，多个进程都在等磁盘。具体阈值要来自同设备、同版本、同采样窗口的线上基线，不能把固定百分比当成通用判据。
- **ANR 发生在设备启动后的短时间内**：系统启动阶段各服务初始化集中，响应速度普遍偏慢。时间窗口要按设备和 ROM 基线确认，不能单靠“启动后 N 分钟”直接过滤。

### 过滤策略

在线上监控中，对疑似系统负载导致的 ANR 做以下处理：

1. **标记并降权**：在 ANR 上报中增加 `likely_system_caused` 标记，和代码问题导致的 ANR 分开统计。单个信号只能用于降权或分桶；只有多项系统负载信号同时出现，并且主线程堆栈没有应用耗时回调时，才考虑从代码问题看板中剔除。
2. **按设备分桶**：统计 ANR 率时，排除低端设备（RAM < 2GB 或 Android 10 以下）的数据，或者单独建桶。不同设备的 ANR 基线差异很大，混在一起会掩盖真实的代码问题。
3. **关注趋势而非绝对值**：系统负载 ANR 的波动和系统版本更新、厂商 ROM 调优相关。单次突增不需要立即响应，但如果某个版本后持续上升，说明需要跟进。

## 总结

ANR 治理的五条核心策略：

1. **主线程瘦身**：所有 I/O、网络、Binder 调用尽量移到子线程。用 `StrictMode` 在开发期捕获遗漏。
2. **Binder 调用治理**：缓存系统服务查询结果，异步调用外部 Service，监控 Binder 调用耗时。
3. **锁竞争治理**：主线程不持锁，锁内不做 I/O，避免嵌套锁。用 Copy-on-Write / Atomic 类替代显式锁。
4. **组件超时治理**：ContentProvider 和 BroadcastReceiver 的回调只做最轻量的转发，实际工作交给后台线程。
5. **Watchdog 兜底**：在系统判定 ANR 之前主动检测主线程阻塞，dump 堆栈并上报。

ANR 的机制和类型在 9.1-9.3 节已详述；本节聚焦的是工程实践层面的治理手段。遇到线上 ANR 时，先按 9.3 节的方法定位类型，再按本节对应的方向执行修复。
