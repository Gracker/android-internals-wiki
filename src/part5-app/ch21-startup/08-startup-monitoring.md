---
title: "启动监控与度量"
chapter: "21.8"
section: "21.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-13"
last_verified_against: "Android Developers docs, Google Play Android Vitals, Clippings structure refs"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/performance/appstartup/analysis-optimization"
  - type: official
    path: "https://developer.android.com/reference/android/app/Activity#reportFullyDrawn()"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationStartInfo.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java (android-17.0.0_r1)"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [startup-monitoring, metrics, p50, p90, regression, android-vitals]
related_chapters: ["21.1", "26.3", "15.3", "15.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-03"
last_task9_at: "2026-06-03T05:27:37+08:00"
last_task9_audit: "2026-07-02"
last_task9_review_log: "logs/deep-review/2026-06-03-05-deep-review.md"
task2b_result: fixed-lite
task2b_state: fixed
last_task2b_lite_at: "2026-06-02"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
task6_reviewed_date: "2026-06-03"
task6_result: pass-light-edit
last_task6_at: "2026-06-03T03:06:00+08:00"
last_task6_audit: "2026-07-14T23:06:00+08:00"
last_task6_review_log: "logs/review/2026-06-03-03-review.md"
task6_review_notes: "2026-06-03 Task6 复审：pass-light-edit。L1/L2 复审通过；禁用词扫描仅有 `线上分位值` 假阳性；锚点覆盖完整。Task9 仍 pending/needs-rework，未自动晋升。"
task9_review_notes: "2026-06-03 Task9 深度复审：pass-tech-review。P0 0 / P1 0 / P2 0；ApplicationStartInfo、reportFullyDrawn 与 Android Vitals 启动阈值口径复核通过，自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-17
consolidated_from:
  - "src/part5-app/ch21-startup/17-startup-insights-api-observability.md"
  - "src/part5-app/ch21-startup/09-startup-case-studies.md#一份可直接使用的复盘模板"
---

# 启动监控与度量

## 为什么启动监控需要独立设计

启动监控要回答两个问题：改动发布后，用户启动体验是否退化；一旦退化，怎样定位到版本、入口、设备和初始化任务。

只在 `Application.onCreate()` 入口与出口打点不够。这个区间看不到启动请求、进程创建、`bindApplication`、Provider 安装和首帧，也无法表达首屏核心内容何时可用。完整方案需要三类数据互相校准：

| 数据 | 回答的问题 | 典型来源 |
| --- | --- | --- |
| 平台启动记录 | 系统何时收到启动、进程属于 cold/warm/hot、由什么原因与组件触发 | Android 15+ `ApplicationStartInfo`、Logcat、Perfetto |
| 应用阶段事件 | 哪个 Provider、初始化任务、页面或数据依赖消耗时间 | 单调时钟埋点、自定义 trace |
| 用户体验指标 | 第一帧何时显示，核心内容何时可交互 | TTID、`reportFullyDrawn()` 对应的 TTFD、业务 ready |

监控负责发现分布变化，Macrobenchmark 负责可重复对比，Perfetto 负责解释一次启动中的线程、Binder、I/O 和调度证据。三者用途不同，不能用一条线上 P90 曲线代替 trace，也不能用一次 trace 代替线上分布。

## 1. 先固定测量契约

启动指标必须写清起点、终点、适用启动类型和失败样本。名称相同但边界不同的数据不能放进同一条曲线。

### 1.1 TTID、TTFD 与业务 ready

| 指标 | 起点 | 终点 | 平台语义 | 使用方式 |
| --- | --- | --- | --- | --- |
| TTID | 系统收到启动请求 | Activity 窗口第一帧绘制并显示 | Framework 自动测量 | 判断用户何时看到应用 UI |
| TTFD | 系统收到启动请求 | 应用调用 `reportFullyDrawn()`，且不早于 TTID | 由应用声明“核心 UI 已完整绘制并可用” | 判断首屏何时达到约定的可用状态 |
| `content_ready` | 与 TTID/TTFD 相同的启动记录，或明确的应用起点 | 首屏关键数据和交互状态满足产品约定 | 应用自定义 | 解释 TTFD，支持无法直接读取系统 TTFD 的版本 |
| `app_on_create_cost` | `Application.onCreate()` 方法入口 | 方法返回前 | 应用局部阶段 | 只解释 App 初始化，不能称为总启动耗时 |

TTID 只说明第一帧出现。骨架屏、空列表或不可点击的占位页也可能已有 TTID。TTFD 需要团队给每个首屏入口定义“可用”：例如首页主导航可操作且首批必要数据已展示，支付页已完成本地安全状态检查，拍摄页预览已可用。广告、推荐流后续分页和不影响首个操作的后台刷新通常不应延长 TTFD。

`Activity.reportFullyDrawn()` 是一次性启动信号。Android 17 的 `Activity` 实现由 `mDoReportFullyDrawn` 控制，第一次有效调用会经 `ActivityClient` 报给系统，后续调用被忽略。若调用发生在系统确认第一帧之前，平台会把 TTFD 时间推到 TTID，因此过早上报会让两个值相同，失去“内容完成”的区分能力。

### 1.2 使用同一种时钟

耗时计算使用单调时钟。Android 17 的 `ApplicationStartInfo.getStartupTimestamps()` 返回 monotonic nanoseconds；应用自定义点应使用 `SystemClock.elapsedRealtimeNanos()`，或在只需进程内相对耗时时使用同样单调的 `System.nanoTime()`。

`System.currentTimeMillis()` 会受到用户改时、网络校时和时区变化影响，适合记录事件发生的墙钟时间，不适合相减得到启动耗时。一个事件可以同时保存：

- `event_wall_ms`：用于版本发布、灰度和配置变更对齐；
- `event_elapsed_ns`：用于同一台设备本次启动内的阶段耗时；
- `duration_ms`：端侧完成边界检查后生成，服务端不跨设备相减单调时钟。

### 1.3 启动样本的身份

同一设备可能由桌面图标、deep link、通知、Widget、Service、Broadcast 或 Provider 拉起；多进程应用还会产生多个进程启动记录。每条样本至少携带：

| 维度 | 建议字段 |
| --- | --- |
| 构建 | versionName、versionCode、渠道、构建 ID、监控 schema 版本 |
| 启动 | cold/warm/hot、入口枚举、首屏路由、是否新任务 |
| 进程 | processName、pid、主/远程进程角色 |
| 安装状态 | 首次安装后启动、升级后启动、普通启动、数据库迁移版本 |
| 设备 | Android 版本、ABI、RAM 档位、SoC/机型分桶、低电量与热状态 |
| 编译与配置 | Baseline Profile 状态、实验组、远程配置版本 |
| 结果 | TTID、TTFD、content ready、超时、退出或上报缺失 |

入口 URL、Intent extras、用户 ID 和页面原始参数不应上传。路由、设备和任务名应转换成受控枚举或稳定哈希，并遵守数据最小化要求。更完整的采集规则见[性能指标采集与上报](../ch26-observability/03-performance-collection.md)。

## 2. 端侧埋点怎样放

### 2.1 不为“更早”新增 Provider

Provider 在 `Application.onCreate()` 之前安装。为启动监控新增自动初始化 Provider，会把监控 SDK 的类加载和初始化加到每次冷启动里。已有 Provider 若负责监控入口，也只能记录一个时间戳和必要身份，序列化、压缩、网络发送与设备信息扩展应延后。

推荐点位如下：

| 点位 | 位置 | 能说明什么 | 不能说明什么 |
| --- | --- | --- | --- |
| `process_observed` | 已有的最早轻量入口或 `Application.attachBaseContext()` | App 代码能看到进程的时间 | 系统启动请求与 fork 的精确时间 |
| `application_on_create_enter/exit` | `Application.onCreate()` | Application 阶段代码耗时 | Provider 和系统进程创建耗时 |
| `activity_create/start/resume` | 入口 Activity 生命周期 | 页面创建路径和生命周期等待 | 第一帧已显示 |
| 初始化 task 事件 | 启动任务执行器 | 任务墙钟耗时、线程和依赖 | CPU 消耗或锁归因，除非再配 trace |
| `content_ready` | 首屏状态机 | 核心数据和交互就绪 | SurfaceFlinger 已完成显示 |
| `fully_drawn_reported` | `reportFullyDrawn()` 调用处 | 应用声明的 TTFD 边界 | 每次页面恢复的完成时间 |

`onResume()` 不等于首帧。`ViewTreeObserver.OnPreDrawListener` 发生在即将绘制之前，`Choreographer.FrameCallback` 表示帧回调时机，两者也都不等于 SurfaceFlinger 已经把像素显示到屏幕。应用可以把它们用作自定义近似点，但事件名必须写成 `pre_draw` 或 `frame_callback`，不能冒充平台 TTID。

### 2.2 准确上报 fully drawn

直接散落多处 `reportFullyDrawn()` 容易提前上报。`ComponentActivity` 的 `FullyDrawnReporter` 可以等待多个内容条件，并在所有 reporter 释放后的下一帧调用平台 API。

下面的 ViewModel 状态示例用于等待首屏核心数据完成，再由 `FullyDrawnReporter` 安排上报：

```kotlin
class HomeActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        lifecycleScope.launch {
            fullyDrawnReporter.reportWhenComplete {
                viewModel.uiState
                    .filterIsInstance<HomeUiState.Ready>()
                    .first()
            }
        }
    }
}
```

`reportWhenComplete` 会为这段挂起工作持有 reporter，等待 `Ready` 后释放；全部 reporter 都释放后，`FullyDrawnReporter` 在下一动画帧调用 `reportFullyDrawn()`。异常与永久 loading 必须有业务降级或超时，否则 TTFD 会长期缺失。缺失样本要单独统计，不能从分母中安静删除。

Compose 首屏可以把同一条 ready 规则放进 `ReportDrawnWhen`：

```kotlin
@Composable
fun HomeRoute(state: HomeUiState) {
    ReportDrawnWhen {
        state is HomeUiState.Ready &&
            state.primaryItems.isNotEmpty()
    }

    HomeScreen(state)
}
```

这个条件应表示用户已能完成首个核心操作。若空列表是合法结果，判断条件要表达“数据请求已完成”，不能用 `isNotEmpty()` 让合法空态永远不报告。

### 2.3 慢任务需要时间线，不只需要总耗时

启动任务应记录 task 名、调度线程、依赖、开始/结束、结果和是否位于首帧前。对高频短任务，埋点本身可能比任务还贵，可以只保留聚合计数或在慢启动诊断采样中打开细节。

自定义 trace 与统计事件分工如下：

- 统计事件保留每次启动的稳定字段与耗时，用于计算分布；
- `Trace.beginSection()` / `Trace.endSection()` 或 AndroidX Tracing 标记阶段，用于 Perfetto 对齐主线程、Binder、I/O 和调度；
- 不上传任意类名、SQL、URL 或用户内容作为 trace 名；
- section 必须严格配对，名称集合要有上限，避免动态字符串造成维度爆炸。

采集器不能在首帧前创建大线程池、扫描完整设备信息或同步写日志文件。启动事件先写入内存队列或受控的小型本地记录，首帧后批量编码；网络发送由既有后台上报机制处理。

## 3. Android 17 的 `ApplicationStartInfo`

Android 15（API 35）加入 `ApplicationStartInfo` 和 `ActivityManager` 查询接口。Android 17 / API 37 上，它可以给出应用自己难以准确获得的系统侧信息：

- `getProcessName()`、PID 与 UID；
- `getReason()`：launcher、Service、Provider、Broadcast、Job、Push 等更细的启动原因；
- `getStartType()`：cold、warm、hot；
- `getStartupState()`：记录仍在启动、发生错误或已经画出首帧；
- `getStartupTimestamps()`：launch、fork、bindApplication、Application.onCreate、first frame、fully drawn 等单调时间戳；
- `getStartComponent()`：Android 16（API 36）加入，用于区分 Activity、Service、Broadcast 和 Provider。
- `getLaunchMode()`、`wasForceStopped()` 与去除 extras 的启动 Intent：用于补充任务和进程状态；原始 Intent、URI 与 referrer 默认不进入遥测。

`reason` 与 `start component` 不应混用。原因表示为什么启动，组件表示哪类组件触发进程创建。同一个原因可能覆盖多种组件，Android 17 源码也明确要求用 `getStartComponent()` 判断四大组件类型。

### 3.1 Android 15、16、17 的能力边界

这组 API 的主体在 Android 15 已经提供，Android 17 是本文的源码校验锚点，不应把既有能力误写成新功能。

| 能力 | API 35 / Android 15 | API 36 / Android 16 | API 37 / Android 17 |
| --- | --- | --- | --- |
| `ApplicationStartInfo`、历史查询、首帧完成监听 | 加入 | 保留 | 保留 |
| 8 个系统时间戳、21–30 开发者时间戳 | 加入 | 保留 | 保留 |
| `getLaunchMode()`、`wasForceStopped()`、去除 extras 的启动 Intent | 加入 | 保留 | 保留 |
| `getStartComponent()` 与组件常量 | 无 | 加入 | 保留 |

API 36 以下不能读取 `getStartComponent()`。Service 启动的 `LAUNCH` 时间戳在 Android 15–16 还存在官方精度限制；Android 17 已越过该边界。

### 3.2 记录形成与状态

system_server 的 `AppStartInfoTracker` 先建立启动记录，随后由进程创建、应用绑定、首帧和 fully drawn 等路径逐步补入字段。应用通过 `ActivityManager` 读取的是记录副本，不是一条包含线程调度、Binder 和 I/O 的完整 trace。

| `getStartupState()` | 含义 | 可依赖的节点 |
| --- | --- | --- |
| `STARTUP_STATE_STARTED` | 启动仍在进行 | `LAUNCH` |
| `STARTUP_STATE_ERROR` | 启动失败，记录不会继续完整化 | 只使用已经存在的节点 |
| `STARTUP_STATE_FIRST_FRAME_DRAWN` | Activity 已走到首帧 | `LAUNCH`、`BIND_APPLICATION`、`APPLICATION_ONCREATE`、`FIRST_FRAME` |

平台没有 `FULLY_DRAWN` 状态；它只是依赖应用调用 `reportFullyDrawn()` 的可选时间戳。首帧完成监听只在记录进入 `FIRST_FRAME_DRAWN` 时触发：失败启动、纯 Service/Broadcast/Provider 拉起可能没有回调，不能把“监听未回调”直接判成启动失败。

八个系统时间戳的常量编号也不代表发生顺序：

| 时间戳 | 语义与限制 |
| --- | --- |
| `LAUNCH` | 系统组件启动起点，不一定是桌面图标点击 |
| `FORK` | 可选的进程 fork 节点，不表示进程初始化完成 |
| `BIND_APPLICATION` | 系统调用应用绑定的节点 |
| `APPLICATION_ONCREATE` | 调用 `Application.onCreate()` 前的节点 |
| `FIRST_FRAME` | 首帧绘制，不单独证明 SurfaceFlinger 已呈现或页面可交互 |
| `FULLY_DRAWN` | 应用定义并上报的完成边界，始终可能缺失 |
| `INITIAL_RENDERTHREAD_FRAME` | 可选的初始 RenderThread 帧 |
| `SURFACEFLINGER_COMPOSITION_COMPLETE` | 可选的合成完成节点，仍不等于业务 ready |

### 3.3 时间戳不是每项都保证存在

`getHistoricalProcessStartReasons(maxNum)` 返回最近到最旧的环形缓冲记录，也可能包含尚未完成的启动。读取前要检查 `getStartupState()`，读取 Map 时要检查 key 是否存在。

首帧完成状态通常可获得 `LAUNCH`、`BIND_APPLICATION`、`APPLICATION_ONCREATE` 和 `FIRST_FRAME`；`FULLY_DRAWN` 依赖应用调用 `reportFullyDrawn()`，任何版本都不能假设它一定存在。`addApplicationStartInfoCompletionListener()` 在首帧完成时回调，不等待 fully drawn，因此回调里的那份快照经常没有 `FULLY_DRAWN`。需要 TTFD 时，应在上报后再次调用历史查询并取得新的副本。

跨版本还要保留一个限制：官方 API 文档说明，Service 触发的 `START_TIMESTAMP_LAUNCH` 在 Android 16（Baklava / API 36）及以下可能不准确。Android 17 锚点已越过这个限制；分析 Android 15–16 存量设备时仍需标记该样本，不能用这项时间戳做精确 Service 启动回归。

### 3.4 读取当前进程的正确记录

历史列表还会混入同一应用近期的其他进程或相邻启动。选择当前记录时至少按 PID、进程名过滤，再按 `LAUNCH` 取最新项；不能无条件取列表第 0 项。

```kotlin
@RequiresApi(35)
fun latestCurrentProcessStart(
    activityManager: ActivityManager,
    maxRecords: Int = 16,
): ApplicationStartInfo? = activityManager
    .getHistoricalProcessStartReasons(maxRecords)
    .asSequence()
    .filter { info ->
        info.pid == Process.myPid() &&
            info.processName == Application.getProcessName()
    }
    .maxByOrNull { info ->
        info.startupTimestamps[
            ApplicationStartInfo.START_TIMESTAMP_LAUNCH
        ] ?: Long.MIN_VALUE
    }
```

生产采集还应核对 launch 时间与当前应用会话。需要 `FULLY_DRAWN` 时，在业务条件满足并调用 `reportFullyDrawn()` 后重新查询；首帧回调中的旧副本通常没有这个节点。

### 3.5 把业务点写进平台启动记录

API 35 起，`ActivityManager.addStartInfoTimestamp()` 允许应用使用 21–30 的保留 key 添加自定义单调时间戳。它能把 `route_resolved` 这类首帧前业务点与系统的 launch、fork、bind 和 first frame 放在同一份记录中。公开注释称相同 key 会覆盖旧值，并称 `reportFullyDrawn()` 之后添加的点会被丢弃；但 `android-17.0.0_r1` 的 tracker 实现会拒绝重复 key，而且记录进入首帧完成状态后不再接受开发者 key。按当前源码，生产代码应把开发者 key 当作“首帧前、每次启动只写一次”的节点。通常发生在首帧后的 `content_ready` 继续使用应用遥测，并由 `reportFullyDrawn()` 表达约定的完成边界。

下面的代码注册首帧完成监听，并用保留区第一个 key 写入首帧前的路由决策完成点：

```kotlin
@RequiresApi(35)
class PlatformStartInfoCollector(
    private val activityManager: ActivityManager,
    private val callbackExecutor: Executor,
) {
    companion object {
        const val TIMESTAMP_ROUTE_RESOLVED =
            ApplicationStartInfo
                .START_TIMESTAMP_RESERVED_RANGE_DEVELOPER_START
    }

    fun register(
        onFirstFrameRecord: (ApplicationStartInfo) -> Unit,
    ) {
        activityManager.addApplicationStartInfoCompletionListener(
            callbackExecutor,
        ) { info ->
            onFirstFrameRecord(info)
        }
    }

    fun markRouteResolved() {
        activityManager.addStartInfoTimestamp(
            TIMESTAMP_ROUTE_RESOLVED,
            SystemClock.elapsedRealtimeNanos(),
        )
    }

    fun latestCurrentProcessRecord(): ApplicationStartInfo? {
        return activityManager
            .getHistoricalProcessStartReasons(8)
            .asSequence()
            .filter { info ->
                info.pid == Process.myPid() &&
                    info.processName == Application.getProcessName()
            }
            .maxByOrNull { info ->
                info.startupTimestamps[
                    ApplicationStartInfo.START_TIMESTAMP_LAUNCH
                ] ?: Long.MIN_VALUE
            }
    }
}
```

监听回调由指定 Executor 执行，里面只应复制必要字段并交给采集队列。历史列表覆盖应用近期多个进程启动，不能无条件取第 0 项；示例按当前 PID 和进程名过滤，生产代码还应核对最新 launch 时间与当前启动代次。业务 key 的编号和含义要随监控 schema 固定，避免不同版本把同一个 key 解释成不同事件。

`ApplicationStartInfo` 适合校准系统起点和启动分类，Android 10–14 仍需兼容自建埋点。完整 API 设计见[ApplicationStartInfo](../ch26-observability/11-application-start-info.md)。

### 3.6 阶段耗时必须防守缺失与乱序

不要把缺失 key 补成 0，也不要按常量编号排序。只有起止节点都存在且终点不早于起点时，区间才有效：

```kotlin
fun startupDurationMs(
    info: ApplicationStartInfo,
    fromKey: Int,
    toKey: Int,
): Double? {
    val startNs = info.startupTimestamps[fromKey] ?: return null
    val endNs = info.startupTimestamps[toKey] ?: return null
    if (endNs < startNs) return null
    return (endNs - startNs) / 1_000_000.0
}
```

采集端应保留原始节点、字段存在位和 `startupState`，让服务端能在 schema 调整或发现平台差异后重新派生区间。

## 4. 线上聚合不能只画平均值

启动耗时通常是右偏长尾分布：低端设备、升级迁移、磁盘繁忙、配置冷读取和编译状态都会产生慢样本。均值容易被少数极慢值拉动，也可能被大量热启动样本稀释。

常用分位数回答不同问题：

| 分位数 | 解释 | 使用提醒 |
| --- | --- | --- |
| P50 | 一半样本不超过该耗时 | 观察主路径和整体平移 |
| P75 | 较慢但仍常见的样本 | 观察普通长尾是否扩大 |
| P90/P95 | 慢启动群体 | 适合作为版本门禁候选指标 |
| P99 | 极端尾部 | 需要较大样本量，易受异常设备与数据质量影响 |

分位数必须在服务端从同一 cohort 的原始样本或可合并分布结构计算。不能让每台设备先算 P90，再把各设备 P90 求平均；也不能把每日 P90 平均成周 P90。使用直方图、t-digest、KLL 等结构时，要固定 bucket 或算法版本，并保留计数、最小值、最大值和缺失率。

### 4.1 先分 cohort，再看分位数

最低限度需要按以下维度拆分：

- cold、warm、hot；
- 首屏路由与入口来源；
- 普通启动、首次安装启动、升级后启动；
- App 版本、实验组与远程配置版本；
- Android 版本、ABI、设备性能档位；
- 主进程与远程进程；
- Profile 安装/编译状态能够可靠获得时，单独分组。

切分过细会让样本稀疏。看板应支持从“版本 × 启动类型”逐层钻到页面和设备，告警层只选择流量足够且责任边界稳定的 cohort。

### 4.2 把缺失和退出当成结果

TTFD 上报容易出现幸存者偏差：完成启动的会话有数值，启动期间退出、崩溃、ANR、进程被杀或长期 loading 的会话没有数值。如果只统计成功上报样本，严重退化反而可能让 TTFD 曲线变好。

每个窗口应同时展示：

- 启动请求或可观测会话数；
- TTID 有效样本数；
- TTFD 有效样本数与完成率；
- fully drawn 超时数；
- 首屏前崩溃、ANR、主动退出和进程死亡；
- 采样率、上传成功率、去重率与 schema 版本。

采样策略也要进入分母。普通样本可以做稳定随机采样，慢样本与失败样本可以提高诊断采样率，但两类数据不能不加权地混算总体分位数。用于告警的指标流和用于定位的诊断流应分开保存。

## 5. 回归检测与归因

固定写死“P90 上升 15% 就拦截”会在低基线、小流量或季节波动中制造噪声。门禁应同时考虑绝对变化、相对变化、样本量和不确定性。

一条可执行的规则可以写成：

```text
同 cohort、同统计窗口：
  样本量达到该指标的最低要求
  AND P90 绝对增量超过产品预算
  AND P90 相对增量超过历史噪声带
  AND 差异的置信区间不跨过“无影响”边界
  AND 连续两个窗口成立
=> 暂停灰度并进入归因
```

这段规则中的预算和噪声带要由产品历史数据确定。高流量版本可以使用 bootstrap 置信区间；低流量灰度可先看中位数、MAD、样本明细和线下 benchmark，避免把不稳定的 P99 当成发布结论。实验统计细节见[性能实验统计](../ch26-observability/06-ab-testing-regression.md)。

### 5.1 归因顺序

发现回归后，按以下顺序缩小范围：

1. 核对 schema、采样率、TTFD 完成率与启动类型占比，排除测量变化。
2. 对齐灰度开始、构建发布时间、远程配置、服务端接口和实验开关。
3. 按入口、页面、设备档位、Android 版本、ABI、安装状态分组。
4. 比较初始化 task 出现率和耗时，检查是否新增 Provider、SDK 或主线程 I/O。
5. 在可复现设备上运行同编译模式的 Macrobenchmark，并打开 Perfetto。
6. 把长耗时区间映射到具体提交和模块所有者，修复后按同一 cohort 回看。

常见信号可以这样解释：

| 现象 | 优先检查 |
| --- | --- |
| `LAUNCH -> FORK` 变长 | 系统负载、进程创建竞争、设备或 ROM 集中性 |
| `BIND_APPLICATION -> APPLICATION_ONCREATE` 变长 | Provider、类加载、Instrumentation 与应用绑定阶段 |
| Application 阶段变长 | 新 SDK、同步 I/O、锁、线程池和任务依赖 |
| TTID 变长但 Application 稳定 | Activity 创建、布局/Compose 首次组合、资源加载与首帧调度 |
| TTID 稳定但 TTFD 变长 | 首屏数据、数据库、网络、缓存和 ready 条件 |
| TTFD 数值变好但完成率下降 | 超时、退出、崩溃或上报丢失造成幸存者偏差 |
| 只在升级后启动变慢 | 数据库迁移、缓存重建、Profile/编译状态和版本迁移任务 |

`ApplicationStartInfo` 的系统节点用来确定区间，应用 task 事件说明责任模块，Perfetto 用来确认线程当时在运行、睡眠、I/O 还是锁等待。缺少后两层证据时，不应仅凭一个长区间判断根因。

## 6. Android Vitals 怎样对标

Google Play Android Vitals 使用 TTID 判断 excessive startup。当前官方公开阈值为：

| 启动类型 | excessive 阈值 |
| --- | --- |
| cold | 5 秒及以上 |
| warm | 2 秒及以上 |
| hot | 1.5 秒及以上 |

这些数值是 Play 的风险阈值，不是优秀体验目标。团队内部预算通常要更严格，并按核心入口、设备档位和用户任务设置。Google 的性能测量总览还给出更激进的目标参考，但项目不能脱离页面复杂度、设备和编译条件直接承诺统一毫秒数。

Vitals 与自建监控应同时保留：

| 维度 | Android Vitals | 自建监控 |
| --- | --- | --- |
| 分发覆盖 | 满足 Play 采集条件的发布用户 | 可覆盖灰度、内测和非 Play 渠道 |
| 核心口径 | 平台 TTID 与 excessive 比例 | TTID 近似/平台校准、TTFD、业务 ready、任务阶段 |
| 维度 | Play 提供的版本与设备等维度 | 页面、入口、实验、任务和业务状态 |
| 时效 | 适合版本趋势与外部质量观察 | 可按团队管线提供更快告警 |
| 主要用途 | 外部质量基线 | 发布门禁与内部归因 |

两边数据不一致时，检查版本覆盖、启动类型、统计窗口、渠道、设备分布、采样条件和 TTFD 完成率。不要通过乘一个固定系数把自建 TTID“换算”为 Vitals。

Android Vitals 的专项边界和 Play Console 使用方式见[Android Vitals 与 Play Console](../ch26-observability/12-android-vitals-play-console-quality.md)。

## 7. 线下与线上怎样互证

一条启动问题从发现到验收，建议保留四层证据：

| 层级 | 工具 | 产物 |
| --- | --- | --- |
| 发布前回归 | Macrobenchmark `StartupTimingMetric` | 固定设备、启动模式、编译模式和迭代次数下的 TTID/TTFD 分布 |
| 单次诊断 | Perfetto / Android Studio Profiler | Android App Startups、主线程、RenderThread、Binder、I/O 与调度时间线 |
| 平台校准 | `ApplicationStartInfo` | 系统起点、启动类型、原因、组件与阶段时间戳 |
| 线上验证 | 自建监控 + Android Vitals | 版本 cohort、分位数、完成率、失败率和长期趋势 |

Macrobenchmark 必须记录 `StartupMode`、`CompilationMode`、设备、温度、电量和迭代数。`StartupMode.COLD` 代表进程冷启动，不代表设备 page cache 也被清空。Baseline Profile 实验还要区分 Profile 是否安装，避免把编译差异归给业务代码。

Perfetto 中先找 Android App Startups 派生轨道，再与应用自定义 trace 对齐。一个 task 在墙钟上持续 80 ms，不代表它消耗了 80 ms CPU；线程可能在等待 Binder、锁、I/O 或调度。优化结论要由对应轨道证明。标准库查询可以先稳定列出 trace 中识别出的启动，再围绕目标 `startup_id` 展开线程、Binder、I/O、GC 和帧证据：

```sql
INCLUDE PERFETTO MODULE android.startup.startups;

SELECT startup_id, package, startup_type, dur / 1e6 AS duration_ms
FROM android_startups
ORDER BY ts;
```

Android 15+ 还可用 `ProfilingManager` 请求受系统约束的 trace 或 stack sample。它比 `ApplicationStartInfo` 重得多，只适合问题版本或受控样本，并要遵守系统限额、设备成本、隐私与上传策略。

## 8. 用同一份模板沉淀复盘

复盘要把现象、证据、假设、改动和结果分开，避免把一次相关性写成根因。下面的最小模板可直接用于 PR 或性能专项：

```markdown
# <入口 / 问题> 启动优化复盘

## 1. 范围
- App commit / versionCode、release variant、R8、编译模式：
- 设备 / Android / RAM / ABI / 温度与电量：
- 入口 / 账号 / 数据 / 网络、cold / warm / hot 定义：
- 统计窗口、样本量、采样率：

## 2. 用户症状
- TTID / TTFD 的 P50、P90 与完成率：
- 首屏前 ANR / Crash / 退出、受影响 cohort：

## 3. 证据
- ApplicationStartInfo 区间、Macrobenchmark、Perfetto：
- task / Provider / manifest、首次出现的版本或配置：

## 4. 根因假设
- 假设、支持证据、反证、仍未知：

## 5. 单变量改动
- 改动、目标区间、风险、灰度与回滚开关：

## 6. 验证
- 线下 before / after 分布：
- 线上同 cohort 的 TTID / TTFD / frame / ANR / Crash / 业务护栏：
- 结果是否超过历史噪声与产品预算：

## 7. 后续
- 门禁、owner、截止时间、回滚条件：
```

若无法写出“哪条证据会推翻当前假设”，通常说明结论还停留在猜测。每次只改变一个可解释变量；当代码、Profile、服务端配置和样本结构同时改变时，结果只能说明整个版本组合发生变化。

## 检查清单

- [ ] TTID、TTFD、content ready 和 Application 局部耗时各有独立名称与边界。
- [ ] 耗时使用单调时钟，墙钟只用于事件对齐。
- [ ] 没有为监控新增自动初始化 Provider 或首帧前重型 SDK。
- [ ] `onResume`、pre-draw 与 frame callback 没有被命名成平台 TTID。
- [ ] 每个首屏入口都定义了可测试的 fully drawn 条件和超时/降级。
- [ ] TTFD 缺失、启动中退出、崩溃与 ANR 进入分母和数据质量看板。
- [ ] cold/warm/hot、安装状态、入口和设备 cohort 分开统计。
- [ ] 分位数从可合并分布计算，没有平均客户端或每日分位数。
- [ ] 告警同时检查绝对差、相对差、样本量、不确定性和连续窗口。
- [ ] Android 15–16 Service 启动的 `LAUNCH` 时间戳限制已标记。
- [ ] `ApplicationStartInfo` completion callback 没有被当成 fully drawn callback。
- [ ] Vitals 阈值只作外部风险线，内部预算由产品基线确定。
- [ ] Macrobenchmark、Perfetto、平台时间戳和线上样本可以按同一启动入口互相对齐。

## 小结

启动监控的核心是一份稳定的测量契约。平台 TTID 告诉我们第一帧何时显示，`reportFullyDrawn()` 给出约定的首屏可用边界，`ApplicationStartInfo` 补齐 Android 15+ 的系统起点、启动分类和触发原因，应用事件负责解释任务与业务状态。服务端再按同一 cohort 计算分位数、完成率和失败率，用绝对预算与统计不确定性共同判断回归。

当一条告警能够回答“哪个版本、哪种启动、哪个入口、哪类设备、哪个阶段开始变慢”，启动监控才具备工程价值。

## 参考资料

- [Android 17 `ApplicationStartInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationStartInfo.java)：启动原因、类型、组件、状态和系统/开发者时间戳。
- [Android 17 `ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)：历史启动记录、首帧完成监听与 `addStartInfoTimestamp()`。
- [Android 17 `Activity.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Activity.java)：`reportFullyDrawn()` 的一次性上报与首帧边界。
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time)：TTID、TTFD、fully drawn 与 Android Vitals 阈值。
- [App startup analysis and optimization](https://developer.android.com/topic/performance/appstartup/analysis-optimization)：Macrobenchmark、Perfetto 与启动区间分析。
- [`ApplicationStartInfo` API reference](https://developer.android.com/reference/android/app/ApplicationStartInfo)：字段可用性、时间戳和跨版本限制。
- [`ActivityManager` API reference](https://developer.android.com/reference/android/app/ActivityManager)：启动记录查询、completion listener 与自定义时间戳。
- [`Activity.reportFullyDrawn()` API reference](https://developer.android.com/reference/android/app/Activity#reportFullyDrawn())：调用语义及过早、过晚上报的影响。
- [`FullyDrawnReporter` API reference](https://developer.android.com/reference/androidx/activity/FullyDrawnReporter)：多条件 fully drawn 协调。
- [Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)：启动基准测试和 `StartupTimingMetric`。
