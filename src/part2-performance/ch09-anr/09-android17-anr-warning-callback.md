---
title: "Android 17 ANR 预警回调与类型枚举"
chapter: "9.9"
section: "9.9"
status: ready-for-review
applicable_versions: "Android 17 (API 37)"
tags: [ANR, warning, callback, AnrTypes, observability, IAnrWarningCallback]
related_chapters: ["9.1", "9.2", "9.3", "9.7", "26.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-02"
drafted_date: "2026-07-02"
drafted_by: "openclaw-task2a"
gap_source: "每日技术文章 intake"
last_verified: "2026-07-02"
last_verified_against: "AOSP android-17.0.0_r1（源文件路径级验证有限，部分标注待验证）"
confidence: medium
sources:
  - type: blog
    path: "技术文章/Android/Android-17系统层面新特性/39-ANR-类型和预警回调.md"
  - type: aosp
    path: "frameworks/base/core/java/android/anr/AnrTypes.java"
  - type: aosp
    path: "frameworks/base/core/java/android/anr/AnrWarningResult.java"
  - type: aosp
    path: "frameworks/base/core/java/android/anr/IAnrWarningCallback.aidl"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/AnrHelper.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/utils/AnrTimer.java"
  - type: research
    path: "DeepResearch/2026-06-15-anr-detection-inputdispatcher-ams-anrhelper-source.md"
---

# 9.9 Android 17 ANR 预警回调与类型枚举

Android 17 / API 37 增加了公开的 ANR warning API。应用可以向 `ActivityManager` 注册 listener，在部分 ANR 计时器接近 deadline 时收到 `AnrWarningResult`。

这个信号有三个边界：

- warning 表示“某个计时条件已进入预警点”，系统尚未宣告 ANR；
- 阻塞条件可能在 deadline 前恢复，因此 warning 后未必有 ANR；
- 回调按 best-effort 投递，系统可能来不及调用，也可能在 executor 排队期间到达 deadline。

warning 不会暂停或延长原计时器。它适合记录轻量状态、串起 warning 与事后退出记录，不适合在回调里临时执行全线程 dump、同步落盘或网络上传。

平台锚点为 `android-17.0.0_r1`。ANR 的 timeout 与报告管线见 [§9.1 ANR 设计思想](01-anr-design.md)，线程转储和 Perfetto 联合分析见 [§9.3](03-anr-analysis.md) 与 [§9.7](07-anr-kernel-trace-joint-diagnosis.md)。

## 1. 公开 API 在 `android.app`

Android 17 的相关类型位于 `android.app`：

| API | 作用 |
|---|---|
| `AnrTypes` | 结构化 ANR 类型常量 |
| `AnrWarningResult` | warning 的 Parcelable 载荷 |
| `ActivityManager.registerAnrWarningListener()` | 注册 executor 与 listener |
| `ActivityManager.unregisterAnrWarningListener()` | 用同一个 listener 对象注销 |

`IAnrWarningCallback.aidl` 是 ActivityManager 与 AMS 之间的 hidden Binder 接口，应用不需要直接实现它。`ActivityManager` 会在当前进程注册第一个 listener 时创建一个 Binder stub；同一进程后续 listener 复用这条系统回调。

这些 API 都在 API 37 加入。公开文档没有要求 `targetSdkVersion >= 37`；应用需要用 API 37 SDK 编译，并在运行时检查设备版本。

## 2. `AnrTypes` 的完整枚举

`AnrTypes` 使用 `@IntDef`，不是 Java/Kotlin `enum`。Android 17 定义了 11 个常量：

| 值 | 常量 | 含义 |
|---:|---|---|
| 0 | `ANR_TYPE_OTHER` | 无法归入其他类型 |
| 1 | `ANR_TYPE_INPUT_DISPATCH_NO_FOCUSED_WINDOW` | 输入派发期间没有 focused window |
| 2 | `ANR_TYPE_INPUT_DISPATCH` | 输入事件响应超时 |
| 3 | `ANR_TYPE_BROADCAST_OF_INTENT` | BroadcastReceiver 处理超时 |
| 4 | `ANR_TYPE_START_FOREGROUND_SERVICE` | 前台服务没有按期进入 foreground |
| 5 | `ANR_TYPE_EXECUTE_SERVICE` | Service `onCreate`、`onStartCommand` 或 `onBind` 执行超时 |
| 6 | `ANR_TYPE_CONTENT_PROVIDER_NOT_RESPONDING` | 已连接 ContentProvider 的受监控调用超时 |
| 7 | `ANR_TYPE_APP_TRIGGERED` | 应用主动请求触发 ANR |
| 8 | `ANR_TYPE_FOREGROUND_SHORT_SERVICE_TIMEOUT` | short service 没有按期响应 `onTimeout()` |
| 9 | `ANR_TYPE_JOB_SERVICE_START` | JobService 启动响应超时 |
| 10 | `ANR_TYPE_APPLICATION_START` | 应用启动超时 |

这些常量还用于 Android 17 的 `ApplicationExitInfo.AnrInfo`。类型集合覆盖 ANR 分类，不表示每一种类型都已经拥有 warning producer。

### 2.1 枚举覆盖与预警覆盖要分开

在已核对的 `android-17.0.0_r1` 实现中，明确发出 warning 的路径有：

| warning producer | `AnrTypes` | 预警点 |
|---|---|---|
| InputDispatcher 等待 focused window | `INPUT_DISPATCH_NO_FOCUSED_WINDOW` | 剩余窗口为 timeout 的一半，或平台默认 pre-ANR window，取较长者 |
| Service execution timer | `EXECUTE_SERVICE` | `AnrTimer` 运行到 50% split point |
| short FGS timer | `FOREGROUND_SHORT_SERVICE_TIMEOUT` | `AnrTimer` 运行到 50% split point |
| start-foreground timer | `START_FOREGROUND_SERVICE` | `AnrTimer` 运行到 50% split point |

InputDispatcher 的 `processPreAnrsLocked()` 在该 tag 中只调用 `processNoFocusedWindowPreAnrLocked()`。普通 input connection timeout 没有沿这段代码发送 warning。BroadcastQueue、ContentProvider call detector、JobService 和 app-triggered ANR 也不能因为存在对应常量就推断已经投递 warning。

warning 覆盖还受 feature flag 与计时器实现影响。生产统计应同时保留“最终 ANR 无 warning”和“warning 后恢复”两类记录，不能把 listener 收到的数量当作全量 ANR 分母。

## 3. `AnrWarningResult` 只有五项数据

Android 17 的载荷字段已经在源码和公开 API 中确定：

| getter | 语义 |
|---|---|
| `getAnrId()` | 该类型下的 ANR event id |
| `getAnrType()` | `AnrTypes` 中的类型值 |
| `getConsumedMillis()` | warning 生成时已经消耗的时长，时钟为 `SystemClock.uptimeMillis()` |
| `getTimeoutMillis()` | 系统为该次计时使用的总 deadline |
| `getDescription()` | 短诊断描述，格式不稳定 |

载荷没有 PID、UID、包名、进程名、组件对象、线程栈、锁状态或 Binder 队列深度。`description` 可能包含 Service component 等提示，但 API 明确声明格式可变；可用于人工分析或辅助聚类，不应解析成稳定协议。

`anrId` 只保证“在每个 `anrType` 内唯一”。持久化 key 应至少使用 `(anrType, anrId)`，还应带上用户、应用版本、设备 boot/session 和本地进程名，避免跨重启或多进程数据混在一起。

## 4. 注册与注销

下面的 Kotlin 示例使用专用单线程 executor，把 warning 复制成小型内存记录。示例避免在回调里遍历全部线程或访问网络：

```kotlin
class AnrWarningRecorder(
    private val context: Context
) : Closeable {
    private val executor =
        Executors.newSingleThreadExecutor { task ->
            Thread(task, "anr-warning-recorder")
        }

    private val lastWarning =
        AtomicReference<WarningSnapshot?>()

    private val listener =
        Consumer<AnrWarningResult> { result ->
            lastWarning.set(
                WarningSnapshot(
                    type = result.anrType,
                    id = result.anrId,
                    consumedMs = result.consumedMillis,
                    timeoutMs = result.timeoutMillis,
                    description = result.description,
                    callbackUptimeMs = SystemClock.uptimeMillis(),
                    receiverProcess = Application.getProcessName()
                )
            )
        }

    fun start() {
        if (Build.VERSION.SDK_INT >= 37) {
            context.getSystemService(ActivityManager::class.java)
                .registerAnrWarningListener(executor, listener)
        }
    }

    override fun close() {
        if (Build.VERSION.SDK_INT >= 37) {
            context.getSystemService(ActivityManager::class.java)
                .unregisterAnrWarningListener(listener)
        }
        executor.shutdown()
    }
}
```

`WarningSnapshot` 是应用自定义的不可变数据类。若 recorder 与进程同寿命，可以在 `Application` 初始化时注册并长期保留；若它属于短生命周期组件，必须用原 listener 实例注销，随后关闭 executor。

官方文档要求 executor 不要使用应用主线程。原因很直接：主线程可能就是等待目标，把回调再次排到主线程会失去预警机会。executor 也不应与容易饱和的业务线程池共用。

## 5. 系统如何投递

### 5.1 应用进程内

`ActivityManager` 在进程内维护 `Consumer<AnrWarningResult> → Executor` 映射：

1. 第一个 listener 注册时，向 AMS 注册一个 `IAnrWarningCallback`；
2. AMS 调用 hidden AIDL 方法 `onAnrImminent(result)`；
3. `ActivityManager` 遍历本进程 listener，把任务提交给各自 executor；
4. 多个 listener 的通知顺序没有保证；
5. 本进程移除全部 listener 后，系统 Binder callback 也会注销。

重复注册同一个 listener 对象不会增加第二条记录。注销一个从未注册的 listener 会直接返回。

### 5.2 system_server 内

`AnrWarningController` 按 calling UID 保存 callback 列表，并为每个 Binder callback 注册 death recipient。producer 调用 `ActivityManagerService.notifyAnrWarning()` 后，controller：

1. 为 `anrId` 取得 error id；
2. 若该 UID 有 callback，发出 `debug.anr` category 的 `AnrWarningDetected` Perfetto instant；
3. 构造 `AnrWarningResult`；
4. 通过 oneway AIDL 通知该 UID 下的每个已注册进程；
5. 记录 ANR warning API stats。

注册范围由 calling UID 决定。应用不能监听其他 UID 的 warning。

### 5.3 多进程应用会收到重复通知

AMS 的 callback 表按 UID 分组。一个包的主进程和 `:remote` 进程都注册 listener 后，同一 UID 的 warning 会投递到两个进程；载荷又没有目标 PID。

多进程应用应：

- 在记录中加入 `Application.getProcessName()`；
- 以 `(type, id, boot/session)` 去重上传；
- 预先决定由哪个进程持久化；
- 不从“收到回调的进程”推断“发生阻塞的进程”。

同 UID 多包场景也要按 UID 语义处理。warning API 没有提供 package selector。

## 6. warning 发生在 deadline 前

旧式 ANR 线程转储在 deadline 到期后才开始，容易遇到取样变旧。Android 17 warning 的时序更早：

```text
计时器开始
    │
    ├── warning split point
    │      └── AMS → onAnrImminent() → app executor
    │
    ├── 阻塞解除：timer cancel，本次不产生 ANR
    │
    └── deadline 到期：进入对应 timeout/ANR 处理
```

图中的 app executor 任务可能晚于 Binder 回调执行。`getConsumedMillis()` 表示系统生成 warning 时的计时进度，`callbackUptimeMs` 才是应用代码开始处理的本地时间；二者不应混写。

### 6.1 Service timer

`AnrTimer.Args.anrWarning(true)` 向 native timer 加入 50% split point。到点后，`AnrTimer` 把 `timerId`、关联对象和 elapsed time送回相应 Handler，再由 `ActiveServices` 生成 type、timeout 和 description。

这一过程发生在 timer expiry 之前。系统负载、Handler 延迟和 executor 排队会缩短应用可用的剩余时间。

### 6.2 No-focused-window input

InputDispatcher 为 no-focused-window 状态维护独立 pre-ANR 标记。pre-ANR window 取“总 timeout 的一半”与平台默认预警窗口中的较大值，再从 deadline 反推 warning 时刻。状态恢复、focused application 改变或已有 focused window 时，最终 ANR可以取消。

该实现路径使用 `ANR_TYPE_INPUT_DISPATCH_NO_FOCUSED_WINDOW`。不能把它扩展解释为全部输入派发超时已有预警。

## 7. warning 与最终 ANR 如何关联

Android 17 为 `ApplicationExitInfo` 增加了 `getAnrInfo()`。当退出原因为 `REASON_ANR` 且系统保留结构化信息时，`ApplicationExitInfo.AnrInfo` 提供：

- `getAnrId()`；
- `getAnrType()`；
- `getTimeoutMillis()`；
- `isUserPerceptible()`。

warning 的 `anrId` 会关联到最终 `ApplicationExitInfo.AnrInfo` 中的 id。下面的 Kotlin 代码用于在下次启动后匹配已保存的 warning key：

```kotlin
if (Build.VERSION.SDK_INT >= 37) {
    val activityManager =
        context.getSystemService(ActivityManager::class.java)

    val anrExits =
        activityManager.getHistoricalProcessExitReasons(
            context.packageName,
            0,
            32
        ).filter { it.reason == ApplicationExitInfo.REASON_ANR }

    anrExits.forEach { exit ->
        val info = exit.anrInfo ?: return@forEach
        val key = "${info.anrType}:${info.anrId}"
        Log.i(
            "AnrCorrelation",
            "key=$key timeout=${info.timeoutMillis} " +
                "userPerceptible=${info.isUserPerceptible}"
        )
    }
}
```

若 warning 后条件恢复，不会出现匹配的 ANR exit。若有 ANR exit 却没有 warning，可能是该类型未接入 producer、feature 关闭、回调投递失败、executor 未运行或应用当时没有注册。

`isUserPerceptible()` 表示系统记录的用户可感知性，不等同于“进程一定展示了某种固定样式的对话框”。后台 silent ANR 与设备 UI 策略仍由最终 ANR 管线决定。

## 8. 回调里适合记录什么

高价值且成本可控的数据包括：

- `(anrType, anrId)`、consumed/timeout；
- callback 的 uptime 与 wall clock；
- 当前 receiver process；
- 当前 Activity、业务阶段、最近一次输入或生命周期事件；
- 已经维护在内存中的主线程消息、Binder 调用和锁等待 breadcrumbs；
- 内存压力、thermal 等已有快照的索引。

下面这些动作风险较高：

- `Thread.getAllStackTraces()` 对全部线程做临时转储；
- 同步写大文件、压缩或数据库 transaction；
- 直接发网络请求；
- 主线程 `runOnUiThread()` 并等待结果；
- 临时启动完整 heap dump、长 CPU profile 或高频 trace。

应用无法通过公开 API在回调中读取 Binder 驱动队列深度或枚举 JVM 中的全部锁持有关系。需要这些信息时，应在平时维护低成本 breadcrumbs，或依赖系统 Perfetto snapshot 与 ANR trace。

## 9. 与 ProfilingManager 的关系

Android 16（API 36）的 `ProfilingTrigger.TRIGGER_TYPE_ANR` 在系统识别 ANR 时，请求一份正在运行的 system trace 快照。Android 17 的 `ProfilingManager` 在应用同时具备：

- 通过 `registerForAllProfilingResults()` 提供的 executor；
- 已注册 `TRIGGER_TYPE_ANR` 或 all triggers；

会在内部调用 `ActivityManager.registerAnrWarningListener()`。它的 listener 写入一个短 trace section：

```text
ANR Warning ANR-Id: <id> consumedMs=<value> timeoutMs=<value>
```

这段标记提供 warning 时间戳与 ANR id，并帮助 trace redactor 保留相关 slice。应用使用 `ProfilingManager` 的 ANR trigger 时，不需要为了这条内部标记再注册第二个 warning listener。

warning listener 本身不会启动系统 trace，也不会补回注册前的历史。`TRIGGER_TYPE_ANR` 是否返回产物仍受后台 trace、buffer、系统限流和设备配置影响。

在 warning 回调里临时调用 `requestProfiling()` 也不能保证赶在 deadline 前产出结果。需要 prehistory 的诊断应依靠系统环形 trace、平时 breadcrumbs 或预先开启且经过开销验证的采集。

## 10. 与 Perfetto 对齐

Android 17 的 `AnrWarningController` 在存在目标 UID callback 时发出：

- category：`debug.anr`；
- instant name：`AnrWarningDetected`；
- args：`anrId`、`errorId`、`anrTimeoutMs`、`consumedTimeMs`。

最终 ANR 处理中，`ProcessErrorStateRecord` 还可发出 `ANR Detected` instant。抓取配置需要启用 `debug.anr` Track Event category，详细配置见 [§9.7](07-anr-kernel-trace-joint-diagnosis.md#3-android-17-中可用的数据源)。

分析时可按下面的时间关系核对：

1. `AnrWarningDetected`；
2. 应用自定义 warning breadcrumb；
3. `ANR Detected`；
4. early dump 与完整 ANR trace；
5. final exit 或恢复事件。

若只有 warning instant，没有最终 ANR instant，应检查条件是否恢复。若 app breadcrumb 缺失而 system instant 存在，应检查 Binder 投递、process callback、executor 和进程存活状态。

## 11. `description` 与类型的使用方式

`anrType` 适合做稳定分组，`description` 适合保留原文供人工查看。一个可靠的存储模型可以包含：

| 字段 | 用途 |
|---|---|
| `warning_key` | type + id + boot/session |
| `type` | 稳定分类 |
| `description_raw` | 原始提示，不作为协议解析 |
| `consumed_ms` / `timeout_ms` | 计时进度 |
| `system_warning_uptime_estimate` | 由 callback uptime 与投递延迟估算时需标明误差 |
| `receiver_process` | 说明哪个进程接收 |
| `matched_exit` | 是否匹配最终 `ApplicationExitInfo.AnrInfo` |
| `evidence_refs` | trace、breadcrumb、日志文件索引 |

warning 对恢复样本也有价值。大量 warning 在同一业务阶段恢复，说明该阶段接近 deadline，适合在产生用户可感知 ANR 前做性能治理。

## 12. 常见误解

### 收到 warning 就一定会 ANR

计时对象可以在 deadline 前完成，producer 会取消 timer。warning 应标记为 potential event。

### 所有 `AnrTypes` 都会触发 listener

类型集合比 Android 17 当前 producer 覆盖广。统计平台要按实际收到的 type 记录覆盖率。

### listener 收到 warning 的进程就是目标进程

AMS 按 UID 分发。同 UID 的多个已注册进程都可能收到同一 warning。

### warning 载荷带线程栈和组件

载荷只有 id、type、consumed、timeout 和 description。组件可能出现在不稳定的 description 中。

### 回调能给 ANR deadline 续时

原计时器继续运行。回调耗时不会改变 timeout。

### `targetSdkVersion` 决定能否注册

公开 API 的版本门槛是运行平台 API 37；官方签名没有 target SDK 条件。feature flag 和设备实现仍可能影响 warning producer。

## 13. 接入检查表

- 用 API 37 SDK 编译，并用 `SDK_INT >= 37` 保护调用；
- executor 与主线程、业务拥塞线程池隔离；
- 保存同一个 listener 实例用于注销；
- 记录 `(type, id)`，加入 boot/session 和 receiver process；
- 回调只复制轻量内存状态；
- 多进程按 UID 投递语义去重；
- warning 与 `ApplicationExitInfo.AnrInfo` 双向匹配；
- 单独统计 recovered warning、matched ANR 和 ANR-without-warning；
- 对 description 只做原文保留或容错聚类；
- 在目标 build 上验证 feature flag、覆盖类型和剩余窗口。

## 版本结论

Android 17 / API 37 把 ANR 类型、预警载荷和 listener 注册做成公开 API。它提供 deadline 前的 best-effort 信号，也让 warning id 能与事后的 `ApplicationExitInfo.AnrInfo` 对齐。

这项能力适合补充已有监控：平时维护轻量 breadcrumbs，warning 时冻结一个小快照，ANR 后再与 system trace 和退出记录合并。它没有取代系统 ANR trace，也没有覆盖 Android 17 中的每一种 ANR 类型。

## 参考资料

- [Android Developers：ActivityManager.registerAnrWarningListener](https://developer.android.com/reference/android/app/ActivityManager#registerAnrWarningListener(java.util.concurrent.Executor,%20java.util.function.Consumer))
- [Android Developers：AnrWarningResult](https://developer.android.com/reference/android/app/AnrWarningResult)
- [Android Developers：AnrTypes](https://developer.android.com/reference/android/app/AnrTypes)
- [Android Developers：ApplicationExitInfo.getAnrInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo#getAnrInfo())
- [AOSP android-17.0.0_r1：ActivityManager warning API](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [AOSP android-17.0.0_r1：AnrTypes](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/AnrTypes.java)
- [AOSP android-17.0.0_r1：AnrWarningResult](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/AnrWarningResult.java)
- [AOSP android-17.0.0_r1：IAnrWarningCallback](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/IAnrWarningCallback.aidl)
- [AOSP android-17.0.0_r1：AnrWarningController](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AnrWarningController.java)
- [AOSP android-17.0.0_r1：AnrTimer](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/utils/AnrTimer.java)
- [AOSP android-17.0.0_r1：ActiveServices warning producers](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java)
- [AOSP android-17.0.0_r1：InputDispatcher pre-ANR](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)
- [AOSP android-17.0.0_r1：WindowManager AnrController](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/AnrController.java)
- [AOSP android-17.0.0_r1：ProfilingManager](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [§9.1 ANR 设计思想](01-anr-design.md)
- [§9.3 ANR 分析方法](03-anr-analysis.md)
- [§9.7 ANR 与 Kernel Trace 联合诊断](07-anr-kernel-trace-joint-diagnosis.md)
