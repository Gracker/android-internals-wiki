---
title: "Startup Insights API 与启动性能可观测性"
chapter: "21.17"
section: "21.17"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-07-06"
last_verified_against: "AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ApplicationStartInfo.java"
confidence: medium
drafted_date: "2026-07-06"
tags: [startup, insights, observability, api, metrics, performance-monitoring]
related_chapters: ["21.1", "21.2", "21.8", "8.1", "26.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-05"
gap_source: "研究素材/知识盲区"
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationStartInfo.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java (android-17.0.0_r1)"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationStartInfo"
  - type: official
    path: "https://developer.android.com/about/versions/15/features"
---

# 21.17 Startup Insights API 与启动性能可观测性

本节把 `ApplicationStartInfo`、`ActivityManager` 的配套接口以及围绕它们建立的采集方案统称为 Startup Insights。Android Framework 中没有名为 `StartupInsights` 的公开类，接入代码仍以这两个公开 API 为准。

应用可以在 `ContentProvider` 中记录早于 `Application.onCreate()` 的节点，也可以在 `Instrumentation`、Activity 生命周期和首帧回调中继续打点。然而，应用自己的代码无法准确还原 AMS 何时收到启动请求、Zygote 何时 fork、系统怎样判定 cold/warm/hot。Android 15（API 35）加入的 `ApplicationStartInfo` 补充了这部分系统视角。

它返回一份阶段记录，不是一条完整 trace：记录中可能缺少 `FORK`、RenderThread、SurfaceFlinger 或 `FULLY_DRAWN` 时间戳，也没有方法调用、线程调度、Binder 和 I/O 明细。线上采集用它识别启动类型并寻找变慢区间；需要解释区间内部发生了什么时，再用应用事件和 Perfetto。

完整的指标、cohort 和告警设计见[启动监控与度量](./08-startup-monitoring.md)，启动归因上报协议见[ApplicationStartInfo 与启动归因上报](../ch26-observability/13-application-start-info.md)。本节集中处理 API 行为、源码边界和接入时容易出错的细节。

## 1. Android 15、16、17 的能力边界

这一组 API 的主要能力在 Android 15 已经提供。Android 17 是本章的源码校验锚点，不应把已有接口误写成 Android 17 新增。

| 能力 | Android 15 / API 35 | Android 16 / API 36 | Android 17 / API 37 |
| --- | --- | --- | --- |
| `ApplicationStartInfo` | 加入 | 保留 | 保留 |
| 历史记录查询与首帧完成监听 | 加入 | 保留 | 保留 |
| 8 个系统时间戳常量 | 加入 | 保留 | 保留 |
| 21–30 自定义时间戳区间 | 加入 | 保留 | 保留 |
| `getLaunchMode()`、`wasForceStopped()` | 加入 | 保留 | 保留 |
| 去除 extras 的启动 `Intent` | 加入 | 保留 | 保留 |
| `getStartComponent()` 与组件常量 | 无 | 加入 | 保留 |

API 36 diff 明确列出了 `getStartComponent()` 和五个 `START_COMPONENT_*` 常量。API 37 的 `android.app` diff 没有列出 `ApplicationStartInfo` 变更。Android 17 的价值在于提供一条经过 `android-17.0.0_r1` 重新核对的稳定边界。

分析 Android 15–16 存量样本时还要保留一项版本限制：官方文档说明，Service 触发启动的 `START_TIMESTAMP_LAUNCH` 在 Baklava（Android 16）及以下可能不准确。Android 17 不再落在该限制范围内。

## 2. 一份启动记录怎样形成

Android 17 中，`AppStartInfoTracker` 在 system_server 内维护近期记录。不同系统路径陆续写入启动原因、进程身份、fork、bind、首帧和画面呈现等信息，应用侧通过 `ActivityManager` 读取副本。

这段关系可以简化为：

```text
启动请求
  -> AppStartInfoTracker 建立 STARTED 记录
  -> ProcessList / AMS 添加 fork、bindApplication 等节点
  -> 应用进程执行 Provider、Application、Activity 启动路径
  -> 系统记录 first frame，并把状态改为 FIRST_FRAME_DRAWN
  -> 应用可在稍后调用 reportFullyDrawn()

读取入口
  -> ActivityManager.getHistoricalProcessStartReasons()
  -> ActivityManager.addApplicationStartInfoCompletionListener()
```

这张简图用于说明记录的生产者和读取入口。箭头表示数据逐步补入同一记录，不代表每个节点都一定存在，也不能据此推导线程或调用栈。

### 2.1 三种状态决定字段可用性

| `getStartupState()` | 含义 | 平台保证的时间戳 |
| --- | --- | --- |
| `STARTUP_STATE_STARTED` | 启动仍在进行 | `LAUNCH` |
| `STARTUP_STATE_ERROR` | 启动失败，记录不会继续完整化 | 除已有节点外，不再保证新增节点 |
| `STARTUP_STATE_FIRST_FRAME_DRAWN` | Activity 启动已走到首帧 | 在 `LAUNCH` 之外，保证 `BIND_APPLICATION`、`APPLICATION_ONCREATE`、`FIRST_FRAME` |

`ApplicationStartInfo` 没有 `FULLY_DRAWN` 状态。`FULLY_DRAWN` 只是一个可选时间戳，依赖应用调用 `Activity.reportFullyDrawn()`。

Android 17 的 `AppStartInfoTracker.checkCompletenessAndCallback()` 只在状态为 `STARTUP_STATE_FIRST_FRAME_DRAWN` 时触发完成监听。Activity 启动失败时，tracker 把记录设为 `ERROR` 并移出进行中队列，却不会走该完成回调。只由 Service、Broadcast 或 Provider 拉起且没有 Activity 首帧的进程，也可能一直等不到这次监听。

因此，完成监听适合拿 Activity 首帧记录，历史查询负责补充进行中、失败和非 Activity 启动。监控 SDK 不能用“监听一直没回调”直接判定启动失败。

## 3. 八个时间戳怎样解释

`getStartupTimestamps()` 返回 `Map<Int, Long>`，值是单调时钟纳秒。常量编号用于查 Map，不表示发生顺序；例如 `APPLICATION_ONCREATE` 的 key 是 2，`BIND_APPLICATION` 的 key 是 3，但运行顺序是 bind 在前、`Application.onCreate()` 在后。

| 常量 | Android 17 源码语义 | 可用性与解读限制 |
| --- | --- | --- |
| `START_TIMESTAMP_LAUNCH` | launch started | 每种状态都保证；不等同于 Launcher 点击，只是本次组件启动的系统起点 |
| `START_TIMESTAMP_FORK` | process fork | 可选；表示 fork 节点，不要改写成“进程初始化完成” |
| `START_TIMESTAMP_BIND_APPLICATION` | `bindApplication` called | 首帧状态保证；是系统发起应用绑定的节点，不是绑定工作完成 |
| `START_TIMESTAMP_APPLICATION_ONCREATE` | `Application.onCreate()` called | 首帧状态保证；Android 17 的 `ActivityThread` 在调用 `Application.onCreate()` 前取 `SystemClock.uptimeNanos()` |
| `START_TIMESTAMP_FIRST_FRAME` | first frame drawn | 首帧状态保证；不能单独证明 SurfaceFlinger 已呈现，也不能证明页面可交互 |
| `START_TIMESTAMP_FULLY_DRAWN` | application called `reportFullyDrawn()` | 始终可缺失；语义由应用的 fully-drawn 条件决定 |
| `START_TIMESTAMP_INITIAL_RENDERTHREAD_FRAME` | initial RenderThread frame | 可选；适合与首帧和渲染 trace 对齐 |
| `START_TIMESTAMP_SURFACEFLINGER_COMPOSITION_COMPLETE` | SurfaceFlinger composition complete | 可选；比 `FIRST_FRAME` 更靠近呈现端，仍不代表业务内容可用 |

几个常用区间可以这样命名：

- `LAUNCH → FIRST_FRAME`：系统记录的启动起点到首帧；
- `FORK → BIND_APPLICATION`：进程 fork 到 AMS 发起应用绑定，前提是两个节点都存在；
- `BIND_APPLICATION → APPLICATION_ONCREATE`：应用绑定消息到 `Application.onCreate()` 调用前，可能包含应用进程准备、类加载和 Provider 安装；
- `APPLICATION_ONCREATE → FIRST_FRAME`：从 `Application.onCreate()` 入口到首帧，覆盖 Application、Activity、布局或 Compose 首次组合以及帧调度；
- `LAUNCH → FULLY_DRAWN`：只有应用定义并上报 fully-drawn 条件时才成立。

长区间只能指出排查范围。比如 `APPLICATION_ONCREATE → FIRST_FRAME` 变长，原因可能是主线程计算、同步 I/O、Binder、锁等待、GC、布局、资源加载或调度延迟。没有 trace 和应用阶段事件时，不能把它直接归因给 `Application.onCreate()`。

## 4. 启动类型、原因与组件要分开

三个字段回答不同问题：

| 字段 | 回答的问题 | 使用规则 |
| --- | --- | --- |
| `getStartType()` | 本次属于 cold、warm 还是 hot | 只在 `FIRST_FRAME_DRAWN` 状态保证可用 |
| `getReason()` | 系统为什么启动应用 | 每种状态都可用，原因比组件类别更细 |
| `getStartComponent()` | 哪类组件触发启动 | API 36+；Activity、Service、Broadcast、ContentProvider、Other |

`getReason()` 可能返回 launcher、launcher recents、start activity、push、alarm、job、service、broadcast、content provider、boot complete、backup 或 other。reason 与 component 存在交叠，组件分组应读取 `getStartComponent()`，不要从 reason 猜测。

线上用户可感知启动通常以 Activity 组件为主。Service、Broadcast、Provider 和 Job 拉起的进程应单独统计，避免改变首页 cold-start 的样本构成。对于 deep link、通知点击和桌面入口，还要结合应用自己的 route 枚举；系统 reason 无法代替业务入口。

`getIntent()` 返回的是为历史记录处理过的 `Intent`，不包含 extras。即便如此，action、data URI、component 或 referrer 仍可能带有业务信息。默认上报枚举化入口，原始 `Intent` 只留在端侧诊断。

## 5. 读取当前进程的正确记录

`getHistoricalProcessStartReasons(maxNum)` 读取系统环形缓冲，按新到旧排序；`maxNum = 0` 表示返回所有尚在缓冲中的匹配记录。列表可能含未完成记录，也可能覆盖同一 UID 下的多个进程或相邻启动。无条件取 `first()` 会在多进程和重叠启动场景中拿错样本。

下面的代码演示两个安全入口：首帧监听直接消费系统传回的记录；历史查询按 PID、进程名和 launch 时间选择当前进程最新记录。

```kotlin
import android.app.ActivityManager
import android.app.Application
import android.app.ApplicationStartInfo
import android.content.Context
import android.os.Process
import androidx.annotation.RequiresApi
import java.util.concurrent.Executor

@RequiresApi(35)
class PlatformStartInfoReader(context: Context) {
    private val activityManager =
        context.getSystemService(ActivityManager::class.java)

    fun observeFirstFrame(
        callbackExecutor: Executor,
        consume: (ApplicationStartInfo) -> Unit,
    ) {
        activityManager.addApplicationStartInfoCompletionListener(
            callbackExecutor,
        ) { info ->
            consume(info)
        }
    }

    fun latestForCurrentProcess(
        maxRecords: Int = 8,
    ): ApplicationStartInfo? {
        val currentPid = Process.myPid()
        val currentProcessName = Application.getProcessName()

        return activityManager
            .getHistoricalProcessStartReasons(maxRecords)
            .asSequence()
            .filter { info ->
                info.pid == currentPid &&
                    info.processName == currentProcessName
            }
            .maxByOrNull { info ->
                info.startupTimestamps[
                    ApplicationStartInfo.START_TIMESTAMP_LAUNCH
                ] ?: Long.MIN_VALUE
            }
    }
}
```

监听最多回调一次，启动已到首帧时注册则可能立即在指定 executor 上返回已有记录。注册动作本身应放在后台线程，回调只复制需要的字段并投递给已有采集队列，不要在首帧附近做序列化、磁盘扫描或网络请求。

需要 `FULLY_DRAWN` 时，应在业务完成条件满足后调用 `reportFullyDrawn()`，再通过历史接口取一份新副本。首帧监听不等待该调用，它传回的快照经常没有 `START_TIMESTAMP_FULLY_DRAWN`。

## 6. 自定义时间戳的 Android 17 源码约束

API 35 起，应用可以调用 `ActivityManager.addStartInfoTimestamp(key, timestampNs)`，把 key 21–30 的开发者节点写入调用方最新的启动记录。`ApplicationStartInfo` 本身没有公开的 `addStartupTimestamp()` 方法；该名字只出现在 framework 内部，应用代码不能调用。

自定义节点要使用与平台节点一致的单调时钟。下面的代码把路由决策完成记录为一个首帧前节点。

```kotlin
import android.app.ActivityManager
import android.app.ApplicationStartInfo
import android.os.SystemClock
import androidx.annotation.RequiresApi

private const val TIMESTAMP_ROUTE_RESOLVED =
    ApplicationStartInfo.START_TIMESTAMP_RESERVED_RANGE_DEVELOPER_START

@RequiresApi(35)
fun markRouteResolved(activityManager: ActivityManager) {
    activityManager.addStartInfoTimestamp(
        TIMESTAMP_ROUTE_RESOLVED,
        SystemClock.uptimeNanos(),
    )
}
```

`SystemClock.uptimeNanos()` 与 Android 17 启动记录的 app-side 取时方式一致。这个函数每次启动只应执行一次，并在首帧前执行；key 与业务含义要纳入稳定 schema，发布后不能复用同一个 key 表示另一个事件。

这里存在一处必须按源码处理的文档差异：

- Android 17 `ActivityManager` 注释称，相同 key 会覆盖旧值，并称 `reportFullyDrawn()` 后的自定义节点会被丢弃；
- `android-17.0.0_r1` 的 `AppStartInfoTracker.isAddTimestampAllowed()` 会拒绝重复 key；
- 记录进入 `FIRST_FRAME_DRAWN` 后，tracker 只接受 `FULLY_DRAWN`、`INITIAL_RENDERTHREAD_FRAME` 和 `SURFACEFLINGER_COMPOSITION_COMPLETE` 三个系统 key，开发者 key 会被拒绝。

基于 Android 17 源码锚点，生产代码应把开发者 key 当成“首帧前、仅写一次”的节点。首页数据 ready、延迟图片完成等常在首帧后发生，不适合依赖这一接口；这些节点继续写入应用遥测，并用 `reportFullyDrawn()` 表达约定的首屏完成边界。

另一个边界来自记录选择：tracker 把开发者时间戳写入调用方最新记录，API 没有参数让应用指定启动 ID。存在多个相邻启动记录时，自定义节点可能无法表达应用期望的那一次 Activity 启动。服务端应保留平台 launch 时间、PID、进程名和应用会话 ID，以便发现无法可靠配对的样本。

## 7. 计算阶段耗时时要防守缺失和乱序

不要把缺失 key 补成 0，也不要按 key 数字排序。只有起止节点都存在、结束时间不早于开始时间时，区间才有效。

下面的辅助函数只负责安全相减，指标含义由调用方选择的两个 key 决定。

```kotlin
import android.app.ApplicationStartInfo

fun startupDurationMs(
    info: ApplicationStartInfo,
    fromKey: Int,
    toKey: Int,
): Double? {
    val timestamps = info.startupTimestamps
    val startNs = timestamps[fromKey] ?: return null
    val endNs = timestamps[toKey] ?: return null
    if (endNs < startNs) return null
    return (endNs - startNs) / 1_000_000.0
}
```

返回 `null` 表示该区间无法从这份记录计算。采集端应保留 `startupState`、原始时间戳和字段存在位，派生耗时可以在服务端重算；这样能在 schema 调整或发现平台差异后重新分析历史数据。

## 8. 线上监控怎样使用这些字段

一条可维护的启动记录至少包含以下几组信息：

| 字段组 | 建议字段 | 用途 |
| --- | --- | --- |
| 记录身份 | app version、API level、PID、进程名、采集 schema | 去重并区分多进程 |
| 系统分类 | state、type、reason、component、launch mode、force-stopped | 构造可比较的启动样本 |
| 原始节点 | 8 个系统 key、已定义的开发者 key、字段存在位 | 重算阶段耗时并分析缺失 |
| 业务节点 | route、content ready、interactive ready、fully-drawn 条件版本 | 解释用户任务何时可用 |
| 环境分组 | 设备性能档、ABI、安装或升级状态、实验配置 | 控制样本构成变化 |
| 数据质量 | 采样策略、TTID/TTFD 完成率、上传状态 | 识别幸存者偏差和采集回归 |

启动类型、入口、设备档位、App 版本和安装状态要先分组，再计算 P50、P90 或 P99。不同 cohort 混在一起时，分位数变化可能来自样本比例变化，未必来自代码退化。

告警阈值也不应从示例毫秒数直接复制。项目需要在固定 cohort 上同时评估：

- 绝对耗时是否超过产品预算；
- 相对基线的变化是否超过历史噪声；
- 样本量和置信区间是否足以支持判断；
- TTID、TTFD 和上传完成率是否同步变化；
- 回归是否连续出现于多个统计窗口。

`STARTUP_STATE_ERROR` 的占比不能直接解释为“系统问题率”。它描述平台启动记录的错误状态，原因可能涉及启动取消、组件或进程路径，也可能受采集覆盖影响。把它与首帧前 Crash、ANR、进程死亡和用户退出一起分析，才有排障意义。

## 9. 与其他工具的分工

| 工具 | 回答的问题 | 适合场景 |
| --- | --- | --- |
| `ApplicationStartInfo` | 为什么启动、属于哪类启动、系统记录了哪些阶段节点 | Android 15+ 线上轻量采集 |
| 应用事件与 `reportFullyDrawn()` | 哪个业务阶段完成、首屏何时达到约定可用状态 | 全版本业务监控 |
| Macrobenchmark | 同一设备和编译条件下，版本间 TTID/TTFD 是否回归 | CI 与实验室复测 |
| Perfetto | 长区间内线程在执行、阻塞、I/O、Binder、GC 还是等待调度 | 单次或抽样诊断 |
| `ProfilingManager` | 应用请求受系统约束的 trace、stack sample 等 profiling | Android 15+ 定向线上诊断 |
| Android Vitals | 发布用户中的平台启动质量分布 | Play 渠道的群体趋势 |

Perfetto 不限于手工离线抓取。Android 15 起，应用可以通过 `ProfilingManager` 请求受系统管理的 profiling；采集仍需考虑系统限额、用户设备成本、隐私和上传策略。`ApplicationStartInfo` 字段小、适合较高覆盖率，trace 和 stack sample 较重，只针对问题版本或受控样本启用。

Perfetto 标准库已经提供 Android startup 模块。下面的查询列出 trace 中识别出的应用启动，不依赖猜测 slice 名称。

```sql
INCLUDE PERFETTO MODULE android.startup.startups;

SELECT
  startup_id,
  package,
  startup_type,
  dur / 1e6 AS duration_ms
FROM android_startups
ORDER BY ts;
```

查询结果给出 Perfetto 在当前 trace 中识别的启动区间。确定目标 `startup_id` 后，再关联进程、线程状态、Binder、I/O、GC 和 FrameTimeline；平台启动记录与 trace 使用各自的记录 ID，跨数据源关联要借助包名、进程、单调时间范围和应用会话信息。

`androidx.metrics:metrics-performance` 也不能当作 Library 启动耗时 API。该 artifact 的主要公开能力是 JankStats 和 `PerformanceMetricsState`，用于逐帧卡顿状态关联。SDK 初始化耗时仍需 SDK 与宿主约定事件协议，或使用 trace section 和宿主采集器。

## 10. 常见误用

- 把 `START_TIMESTAMP_LAUNCH` 解释成桌面图标点击，导致 Service、Provider 和 Broadcast 样本含义错误。
- 认为八个系统 key 每次都齐全，遇到缺失值就补 0。
- 按 key 编号推断时间顺序，把 `APPLICATION_ONCREATE` 排在 `BIND_APPLICATION` 前。
- 把 `FORK` 写成 fork 完成后的进程就绪点。
- 把首帧完成监听当成 `reportFullyDrawn()` 回调。
- 期待错误启动或纯后台组件启动一定触发首帧完成监听。
- 调用不存在的公开方法 `ApplicationStartInfo.addStartupTimestamp()`。
- 在首帧后写开发者 key，忽略 Android 17 tracker 会拒绝该节点。
- 用历史列表第 0 项代表当前进程，忽略多进程和相邻启动。
- 从一个阶段区间直接判断函数级原因，没有应用事件或 trace 证据。
- 把 JankStats 当作 SDK 初始化计时工具。
- 只统计成功到达 TTFD 的会话，使启动中退出或崩溃的慢样本从分母消失。

## 11. 接入检查表

- [ ] API 35 以下有应用自建事件和 fully-drawn 兼容路径。
- [ ] API 36 以下不读取 `getStartComponent()`。
- [ ] 读取每个 timestamp 前都检查 key，计算前检查单调顺序。
- [ ] completion listener 只解释为 Activity 首帧完成。
- [ ] `reportFullyDrawn()` 后重新查询历史记录，再读取 `FULLY_DRAWN`。
- [ ] 自定义 key 固定为 21–30 内的稳定 schema，Android 17 上只在首帧前写一次。
- [ ] 历史记录按 PID、进程名和 launch 时间匹配，没有无条件取第一项。
- [ ] reason、component、route 分列保存，不互相推断。
- [ ] 原始 `Intent`、URI 和 referrer 默认不上报。
- [ ] 服务端保存原始节点、字段存在位、状态和采样策略。
- [ ] 阈值来自同 cohort 的项目基线，同时检查绝对差、相对差、样本量和完成率。
- [ ] 归因结论同时有平台阶段、应用事件或 Perfetto 证据。

## 小结

`ApplicationStartInfo` 给 Android 15+ 启动监控增加了系统侧记录：启动原因、启动类型、触发组件以及若干单调时间戳。它适合在线上筛选样本、标出变慢区间，却不提供完整调用链，也不保证八个节点全部存在。

Android 17 / API 37 下，接入时应牢记三个边界：`getStartComponent()` 从 API 36 才可用；首帧完成监听不等待 `reportFullyDrawn()`；开发者时间戳虽然从 API 35 已公开，`android-17.0.0_r1` tracker 只接受首帧前的一次写入。把这些边界写进采集 schema，再用 Macrobenchmark、应用阶段事件和 Perfetto 补充实验与诊断证据，启动数据才能用于可靠的版本比较。

## 参考资料

- [Android 17 `ApplicationStartInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationStartInfo.java)：状态、原因、类型、组件和时间戳的公开语义。
- [Android 17 `ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)：历史查询、首帧完成监听和 `addStartInfoTimestamp()`。
- [Android 17 `AppStartInfoTracker.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppStartInfoTracker.java)：记录队列、完成回调与时间戳接收规则。
- [Android 17 `ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)：Provider 安装和 `Application.onCreate()` 时间点。
- [`ApplicationStartInfo` API reference](https://developer.android.com/reference/android/app/ApplicationStartInfo)：字段可用性和跨版本说明。
- [`ActivityManager` API reference](https://developer.android.com/reference/android/app/ActivityManager)：查询、监听和开发者时间戳入口。
- [API 36 `ApplicationStartInfo` diff](https://developer.android.com/sdk/api_diff/36/changes/android.app.ApplicationStartInfo)：启动组件分类的新增边界。
- [API 37 `android.app` diff](https://developer.android.com/sdk/api_diff/37/changes/pkg_android.app)：Android 17 的公开 API 变更范围。
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time)：TTID、TTFD 和 `reportFullyDrawn()`。
- [App-driven profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture)：Android 15+ 应用请求 profiling 的方式。
- [PerfettoSQL syntax](https://perfetto.dev/docs/analysis/perfetto-sql-syntax)：`android.startup.startups` 标准库模块及查询语法。
- [JankStats](https://developer.android.com/topic/performance/jankstats)：`androidx.metrics:metrics-performance` 的逐帧卡顿用途。
