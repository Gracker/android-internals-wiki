---
title: ApplicationStartInfo 与启动归因上报
chapter: '26.8'
section: '26.8'
status: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37)
last_verified: '2026-08-15'
last_source_verified_at: '2026-08-15'
last_verified_against: Current Android Developers ApplicationStartInfo and ActivityManager docs updated 2026-08-14, current app startup/Macrobenchmark/ProfilingTrigger docs, and AOSP android-17.0.0_r1 sources retrieved 2026-08-15
confidence: high
sources:
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationStartInfo
- type: official
  path: https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessStartReasons(int)
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture
- type: legacy-reference-preserved
  path: frameworks/base/core/java/android/app/ApplicationStartInfo.java
- type: legacy-reference-preserved
  path: frameworks/base/core/java/android/app/ActivityManager.java
- type: legacy-reference-preserved
  path: packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationStartInfo.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java
- type: official
  path: https://developer.android.com/topic/performance/vitals/launch-time
- type: official
  path: https://developer.android.com/reference/androidx/benchmark/macro/StartupMode
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics
tags:
- observability
- startup
- application-start-info
- profilingmanager
related_chapters:
- '8.2'
- '14.8'
- '26.6'
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: '2026-08-15T20:39:58+08:00'
last_draft_polish_run_id: 20260815-203958-gracker-writing-472
last_review_finalize_at: '2026-08-15T20:39:58+08:00'
last_review_finalize_run_id: 20260815-203958-gracker-writing-472
last_rework_at: '2026-08-15T20:39:58+08:00'
last_rework_run_id: 20260815-203958-gracker-writing-472
---

# ApplicationStartInfo 与启动归因上报

启动耗时要结合启动类型、启动原因和前一次进程状态解释。桌面图标触发的冷启动、最近任务恢复、广播拉起和低内存后的状态恢复，即使首帧耗时相同，优化方向也可能完全不同。

Android 15 / API 35 的 `ApplicationStartInfo` 给应用提供系统侧启动记录，包括进程身份、启动原因、冷/温/热类型、启动状态和单调时钟时间戳。冷启动从创建进程开始，温启动会复用部分已保存状态，热启动把仍在运行的应用带回前台。业务仍需记录首页何时可用、页面路由、异步数据完成和产品场景；Perfetto 与 `ProfilingManager` 继续解释线程、调度、输入输出（I/O）和 Binder 进程间通信等运行现场。

源码锚点采用 `android-17.0.0_r1` 的 `ApplicationStartInfo.java`、`ActivityManager.java` 和 `ProfilingTrigger.java`。

## ApplicationStartInfo 位于哪一层

一份可用的启动证据可分成三层：

| 层次 | 回答的问题 | 主要数据 |
|---|---|---|
| 系统启动记录 | 进程为何启动，处于哪种启动状态，系统记录到哪些阶段 | `ApplicationStartInfo` |
| 业务体验记录 | 用户从哪个入口进入，何时看到主内容并可交互 | route（页面路由）、scene（入口场景）、home ready（首页可用）、业务阶段 |
| 重型诊断附件 | 慢在主线程、I/O、锁、Binder、渲染还是类加载 | Perfetto system trace、stack sampling（定期抽取调用栈） |

`ApplicationStartInfo` 不能单独定位慢代码，也不能替代 TTID / TTFD 的平台指标。TTID（time to initial display）表示从系统收到启动 Intent 到首帧显示的时间；TTFD（time to full display）表示从同一起点到应用达到可用状态并调用 `reportFullyDrawn()` 的时间。`ApplicationStartInfo` 给每条启动样本增加系统归因，并为业务时间戳和诊断附件提供共同的进程、启动类型与时间基准。

## Android 15 的两种读取入口

### 历史记录

`ActivityManager#getHistoricalProcessStartReasons(maxNum)` 返回调用应用最近的启动记录，按时间从近到远排序。系统使用环形缓冲区保存记录：空间有限，新记录会逐步替换较早记录。`maxNum = 0` 表示不额外限制返回条数，但结果仍受系统缓冲区容量限制。

历史查询可能包含尚未完成的启动记录。startup state 表示系统收集这条记录的进度，start type 才表示冷、温或热启动。读取后先看 `getStartupState()`，再决定哪些字段可用：

| startup state | 保证的内容 | 处理方式 |
|---|---|---|
| `STARTUP_STATE_STARTED` | `START_TIMESTAMP_LAUNCH` 和始终可用的身份/原因字段 | 可用于提前判断启动原因；不要强行读取启动类型 |
| `STARTUP_STATE_ERROR` | 不保证新增阶段时间戳 | 记录错误状态和已有字段，不计算完整启动耗时 |
| `STARTUP_STATE_FIRST_FRAME_DRAWN` | 额外保证 `APPLICATION_ONCREATE`、`BIND_APPLICATION`、`FIRST_FRAME` | 可以进入首帧分析；其他 timestamp 仍逐项判空 |

`getStartType()` 只在 `STARTUP_STATE_FIRST_FRAME_DRAWN` 时有保证。尚未完成的记录可能返回 `START_TYPE_UNSET`，也可能已经带有部分值；线上协议应使用 nullable 或 `unavailable`，不能把未设置值当成热启动。

### 首帧完成回调

`addApplicationStartInfoCompletionListener(executor, listener)` 在当前启动首帧绘制完成时通知应用。`Executor` 决定在哪个线程执行，listener 接收完成记录。回调不等待 `Activity.reportFullyDrawn()`；当前启动若已经完成，系统会立即把记录投递到指定 executor。每个 listener 最多调用一次，调用后自动移除；同一时刻已有 listener 时，新注册项会替换它。回调是异步的，注册和处理都应避免阻塞主线程。

需要 `START_TIMESTAMP_FULLY_DRAWN` 时，应在调用 `reportFullyDrawn()` 后重新查询记录，或重新注册 listener 取得已经完成的记录。首帧回调拿到的是当时的副本，稍后不会自行更新。

## 字段边界

### 身份和原因

| 字段 | 含义 | 注意事项 |
|---|---|---|
| `getPid()`、`getProcessName()` | 本次启动的进程身份 | PID 是进程编号，进程退出后会被复用，不能单独做主键 |
| `getPackageUid()`、`getRealUid()`、`getDefiningUid()` | 安装 UID、运行 UID 和外部服务定义 UID | UID 是系统用于身份与权限检查的编号；隔离进程、external service 场景下三者可能不同 |
| `getReason()` | 触发进程启动的细粒度原因 | API 35 起始终有值；不能代替组件分类 |
| `getIntent()` | 系统保留的启动 Intent | extras（Intent 携带的附加键值）已移除，返回值仍可能为空；不要上传完整 Intent |
| `getLaunchMode()` | 启动 Activity 的 launch mode（实例复用模式） | 非 Activity 启动不要过度解释 |
| `wasForceStopped()` | 是否为应用被 force-stop（强行停止）后的首次进程启动 | 可用于重新注册此前被清理的 alarm（定时任务）、job（调度任务）等 |

公开的 start reason 包括 alarm、backup、boot complete、broadcast、content provider、job、launcher、launcher recents、push、service、start activity 和 other。reason 描述启动诱因，同一个原因可能覆盖多种组件；组件类型要从 Android 16 新增的 `getStartComponent()` 读取。

Android 16 / API 36 增加 `getStartComponent()`，用于区分 Activity、Service、Broadcast、ContentProvider 和 Other。API 36 起应先按 start component 分流，再结合 reason 细分来源；Android 15 没有该字段，只能保留 reason，并接受较低的分类精度。external service 指应用绑定后以调用方身份运行、但代码由另一个包提供的外部服务，这类场景的 UID 字段尤其需要分别保存。

### 冷、温、热启动

`getStartType()` 的公开语义如下：

- `START_TYPE_COLD`：进程从头启动。
- `START_TYPE_WARM`：系统保留了最少的 `SavedInstanceState`（Activity 状态保存数据）。
- `START_TYPE_HOT`：已有应用状态被带回前台。
- `START_TYPE_UNSET`：启动类型尚未设置。

线上冷启动 SLA（服务等级目标）只纳入完成记录中的 `START_TYPE_COLD`。warm 和 hot 分桶统计，不与 cold 聚合。后台 Service、Broadcast、ContentProvider 等进程启动也不进入“首页冷启动”指标；它们属于后台拉起健康度或组件初始化成本。

用户入口还要结合 reason 和业务 route：

| 系统字段 | 建议指标分组 |
|---|---|
| component 为 Activity，reason 为 `LAUNCHER` 或 `LAUNCHER_RECENTS` | 用户显式启动；cold/warm/hot 分开 |
| component 为 Activity，reason 为 `START_ACTIVITY` | 外部跳转、通知或 deep link（深层链接）候选；由业务 entry scene 细分 |
| component 为 Service/Broadcast/ContentProvider | 后台或组件启动，不进入首页 SLA |
| reason 为 `PUSH` | 推送拉起与推送点击路径分开，依赖业务事件确认 |
| reason 为 `OTHER` | 保留原始字段，进入待分类样本 |

Android 15 缺少 start component 时，不要仅凭 reason 把样本永久定类。服务端可以标记 `component_source = unavailable`，并让业务入口补充候选分类。

## 时间戳协议

`getStartupTimestamps()` 返回非空的 `Map<Integer, Long>`。value 是纳秒单位的单调时钟时间戳；单调时钟只随设备运行向前递增，适合计算时长，不表示从 1970 年开始的 Unix epoch 日历时间。Map 对象非空，但各个 key 仍可能缺失。

系统公开的主要 key 包括：

| key | 事件 |
|---|---|
| `START_TIMESTAMP_LAUNCH` | 系统开始启动 |
| `START_TIMESTAMP_FORK` | 系统 fork（复制进程模板）创建应用进程 |
| `START_TIMESTAMP_BIND_APPLICATION` | 系统调用 `bindApplication`，把应用信息交给新进程 |
| `START_TIMESTAMP_APPLICATION_ONCREATE` | `Application.onCreate()` 调用 |
| `START_TIMESTAMP_FIRST_FRAME` | 首帧绘制 |
| `START_TIMESTAMP_FULLY_DRAWN` | 应用调用 `reportFullyDrawn()` |
| `START_TIMESTAMP_INITIAL_RENDERTHREAD_FRAME` | RenderThread（渲染线程）开始处理初始帧 |
| `START_TIMESTAMP_SURFACEFLINGER_COMPOSITION_COMPLETE` | SurfaceFlinger（系统合成服务）完成画面合成 |

可用性由启动状态、启动组件和系统采集情况共同决定。`FULLY_DRAWN` 只有应用调用 `reportFullyDrawn()` 后才可能出现。Android 官方文档还标明：Service 启动的 `START_TIMESTAMP_LAUNCH` 在 Android 16 及更早版本可能不正确。API 35 / 36 上不要用该值给 Service 启动设置耗时门禁；Android 17 再按修复后的平台语义处理。

当前 API reference 还展示了 API 10000 预览常量 `START_TIMESTAMP_SOURCE_EVENT`，用于记录触发 Activity 启动的源事件。它不属于稳定 API 37，本章的数据模型和门禁不使用该 key；待对应 SDK 正式发布后再单独验证时间基准和设备覆盖。

阶段耗时只在同一记录、两个 key 均存在时相减。例如：

- `FIRST_FRAME - LAUNCH` 可保存为系统首帧原始区间，前提是 Activity 启动且 launch 时间可信。
- `APPLICATION_ONCREATE - BIND_APPLICATION` 表示从 bindApplication 记录点到 `Application.onCreate()` 被调用的区间，其中还包含框架在两点之间执行的工作，不能当作 `Application.onCreate()` 自身耗时。
- `FULLY_DRAWN - LAUNCH` 只有 `reportFullyDrawn()` 的业务语义稳定时才可跨版本比较。

系统时间戳不应与 `System.currentTimeMillis()` 直接相减。若要给记录增加可读的 wall-clock（日历时钟）时间，应在采集瞬间同时保存日历时钟和单调时钟快照，再在同一 boot session（一次开机周期）内近似换算。设备重启或系统时间变化后，关联置信度需要降低。

### 把业务 ready 写入同一 Map

API 35 还提供 `ActivityManager#addStartInfoTimestamp(key, timestampNs)`。开发者 key 的保留范围是 `START_TIMESTAMP_RESERVED_RANGE_DEVELOPER_START` 到 `START_TIMESTAMP_RESERVED_RANGE_DEVELOPER`，即 21 到 30。重复使用同一个 key 会覆盖旧值；在 `reportFullyDrawn()` 之后添加的 timestamp 会被丢弃。

下面的代码演示两件事：安全读取未完成记录，以及在调用 `reportFullyDrawn()` 前写入一个由应用数据协议固定分配的首页 ready 时间戳。

```kotlin
data class StartEvidence(
    val pid: Int,
    val processName: String,
    val packageUid: Int,
    val realUid: Int,
    val reason: Int,
    val startupState: Int,
    val startType: Int?,
    val startComponent: Int?,
    val wasForceStopped: Boolean,
    val timestampsNs: Map<Int, Long>,
)

@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
fun readRecentStarts(
    context: Context,
    maxRecords: Int,
): List<StartEvidence> {
    require(maxRecords > 0)
    val activityManager = context.getSystemService(ActivityManager::class.java)

    return activityManager.getHistoricalProcessStartReasons(maxRecords).map { info ->
        val completed =
            info.startupState == ApplicationStartInfo.STARTUP_STATE_FIRST_FRAME_DRAWN

        StartEvidence(
            pid = info.pid,
            processName = info.processName,
            packageUid = info.packageUid,
            realUid = info.realUid,
            reason = info.reason,
            startupState = info.startupState,
            startType = info.startType.takeIf {
                completed && it != ApplicationStartInfo.START_TYPE_UNSET
            },
            startComponent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.BAKLAVA) {
                info.startComponent
            } else {
                null
            },
            wasForceStopped = info.wasForceStopped(),
            timestampsNs = info.startupTimestamps.toMap(),
        )
    }
}

@RequiresApi(Build.VERSION_CODES.VANILLA_ICE_CREAM)
fun markHomeReadyBeforeFullyDrawn(context: Context) {
    val activityManager = context.getSystemService(ActivityManager::class.java)
    activityManager.addStartInfoTimestamp(
        ApplicationStartInfo.START_TIMESTAMP_RESERVED_RANGE_DEVELOPER_START,
        SystemClock.elapsedRealtimeNanos(),
    )
}
```

`START_TIMESTAMP_RESERVED_RANGE_DEVELOPER_START` 在这个示例的数据协议中固定表示 `HOME_READY`。生产实现要维护 key 注册表，避免不同模块复用 21–30 的同一位置。写入后仍应重新读取完成记录；采集层不在字段缺失时补 0。

## 启动证据记录（envelope）

系统记录和业务体验记录可以放在同一个 envelope，也就是一条汇集启动证据的结构化记录，但每个字段都要标明来源。

| 字段组 | 建议字段 | 约束 |
|---|---|---|
| 记录身份 | `start_record_key`、pid、processName、packageUid、realUid | key 包含多字段，处理 PID 复用 |
| 系统归因 | `startup_state`、`start_type`、`start_reason`、`start_component`、`was_force_stopped` | 保留 API 可用版本和字段来源 |
| 系统时间 | `launch_ns`、`fork_ns`、`bind_application_ns`、`app_on_create_ns`、`first_frame_ns`、`fully_drawn_ns` | 缺失为 null；保留原始值 |
| 业务时间 | `home_ready_ns`、`first_interactive_ns`、`report_fully_drawn_policy` | 使用同一单调时钟；记录协议版本 |
| 业务入口 | `route_name`、`entry_scene`、`install_or_upgrade_state` | 使用有限枚举，避免上传原始 URI（统一资源标识符） |
| 口径调整 | `raw_duration_ms`、`adjusted_duration_ms`、`adjustment_reason` | raw 是系统原始时长，adjusted 是按产品协议调整后的时长；调整值不能覆盖原始值 |
| 诊断关联 | `session_id`、`trace_id`、`case_id`、`app_version`、`os_build`、`api_level` | 关联文件时保留 source |
| 策略信息 | `sample_policy_version`、`consent_state`、`upload_policy` | 支持审计和远程停用 |

广告、引导页或登录流程是否从产品体验指标中调整，应由版本化协议定义。研发回归始终保留原始时长，否则一次产品流程变化可能被误判为系统启动性能改善。

TTID 是系统从收到启动 Intent 到首次显示帧的指标；TTFD 从同一起点到应用报告 fully drawn。业务 `home_ready` 可以早于或晚于其他页面条件，但不能冒充 TTFD。应用应在主内容可见且可用后调用 `reportFullyDrawn()`，并让该语义跨版本稳定。

## Android 17 冷启动 trigger

trigger 是系统事件满足条件后启动或保存 profiling 结果的触发器。Android 17 / API 37 的 `TRIGGER_TYPE_COLD_START` 在系统判断 `ApplicationStartInfo#getStartType()` 为 `START_TYPE_COLD` 时尽早触发。系统为该 trigger 新启动 system trace 和 stack sampling profile，并持续到应用调用 `reportFullyDrawn()`；未调用时，公开 API 给出的默认停止时间为 5 秒。

该 trigger 使用 discard buffer（满后丢弃新事件的缓冲区），以保留启动早期内容。profiling 本身仍可能延迟开始，结果也受系统采样、设备状态和 rate limiter（频率限制器）影响，所以它不能替代每次启动的轻量证据记录。

| 数据 | 采集频率 | 主要用途 |
|---|---|---|
| `ApplicationStartInfo` 结构化字段 | 按线上轻量采样策略 | 分桶、趋势、版本回归 |
| 业务 ready 与 route | 按业务指标策略 | 用户体验和页面归因 |
| cold-start system trace + stack sampling | 低频、问题版本或指定 case（诊断案例） | 定位线程、I/O、Binder、调度与调用栈 |

系统触发结果只能通过 `ProfilingManager#registerForAllProfilingResults()` 的全局监听器接收。文件路径读取 `ProfilingResult#getResultFilePath()`；回调缺失或无文件属于预期降级路径。`TRIGGER_TYPE_APP_FULLY_DRAWN` 是 API 36 trigger，它在冷启动调用 `reportFullyDrawn()` 后保存正在运行的后台 system trace 快照，与 API 37 新启动采集的 cold-start trigger 语义不同。

## 与 ApplicationExitInfo 联合归因

`ApplicationExitInfo` 记录前一次进程退出，`ApplicationStartInfo` 记录本次进程启动。两者的时钟和进程身份不同：

- exit timestamp 是 Unix epoch 毫秒。
- start timestamp 是单调时钟纳秒。
- 前一次退出 PID 与本次启动 PID 通常不同，不能要求 PID 相等。
- 用户改时间、设备重启和包更新都会影响关联。

推荐保留两份原始记录，再生成带置信度的关联边；关联边表示“这次启动可能接在那次退出之后”，不会合并或覆盖原记录。候选匹配可以使用包 UID、processName、前后顺序、应用版本、boot session、采集时的 wall / monotonic 快照和业务 session。时间窗口由线上数据校准，不写成平台保证。

| 上次退出证据 | 本次启动证据 | 排障方向 |
|---|---|---|
| `REASON_CRASH` / `REASON_CRASH_NATIVE` | 短时间后 cold start | 崩溃后重启或崩溃循环；关联 Crash SDK 样本 |
| `REASON_ANR` | cold start 且回到相同 route | ANR 后用户重进；关联 ANR trace 和 profiling |
| `REASON_LOW_MEMORY` 或受支持设备上的 LMK（低内存终止）证据 | cold start，业务请求恢复状态 | 状态重建、缓存回填和恢复耗时 |
| `REASON_PACKAGE_UPDATED` | 新版本首次启动 | 升级首启分桶；旧进程和新进程版本不同 |
| 用户请求终止 | `wasForceStopped()` 或用户再次显式启动 | 不计为 crash 恢复；检查 alarm/job 是否需重新注册 |

`wasForceStopped()` 是本次启动记录上的直接信号，优先于从模糊 exit reason 推断。匹配失败时保留“无可确认前序退出”，不要把最近的一条退出记录强制关联给当前启动。

## 数据保留、采样和隐私

启动记录字段较轻，profiling 文件较重，两者要分配不同预算。

- 历史查询的 `maxNum` 由客户端策略配置，读取后用稳定 record key 去重。
- completion listener 在首帧阶段只做内存复制或轻量落盘，避免同步网络和重型序列化影响启动。
- 端侧队列设置容量、过期和失败退避；达到磁盘预算时优先删除过期诊断文件。
- 结构化字段和 profiling 文件使用不同的采样、上传条件、保留期限和访问权限。
- 记录采样策略版本、丢弃原因、上传状态和 `ProfilingResult` 错误码，便于判断“没有数据”的原因。

`getIntent()` 已移除 extras，但仍不应直接上传。Intent 的 action（动作）、data URI（目标数据）、component（目标组件）、flags（行为标志）或 referrer（来源页面）可能暴露业务路径与用户关联信息。服务端只接收经过白名单映射的 `entry_scene` 和 `route_name`；未知值归到 other，不发送原始字符串。

system trace 和 stack sampling 可能包含方法名、线程名、调度关系、路径和业务调用栈。上传需要适用的用户同意或合规依据、远程开关、传输与静态加密、最小权限、访问审计、保留期限和删除机制。

## CI 与灰度门禁

CI（持续集成）中的 Macrobenchmark、灰度发布和线上全量监控可以使用同一套指标名称，但数值分布不能混用。Macrobenchmark 是 AndroidX 在设备上重复执行完整应用场景的基准测试工具。

| 环境 | 数据 | 比较方式 |
|---|---|---|
| CI / 实验室 | `StartupTimingMetric` 的 TTID / TTFD、Macrobenchmark trace、固定 `StartupMode` 和 compilation mode | compilation mode 表示预编译条件；只在设备类别、系统版本、构建类型和编译条件相同时比较 |
| 灰度 | cold Activity 启动的 P50 / P90 / P99、超限比例、入口和设备分桶 | P50 / P90 / P99 表示有 50% / 90% / 99% 样本不超过该值；与稳定版本使用相同分桶，达到配置门槛后阻止放量或回滚 |
| 线上诊断 | `ApplicationStartInfo`、业务 envelope、抽样 profiling 文件 | 用结构化异常定位候选样本，再分析原始附件 |

Macrobenchmark 的 `StartupMode.COLD/WARM/HOT` 控制测试前置状态；`ApplicationStartInfo.START_TYPE_*` 是系统对一次线上启动的记录。两组枚举不要按整数值关联，也不要假定所有语义细节完全相同。CI 负责可重复回归，线上分位数负责用户分布，trace 负责解释异常样本。

门禁配置应带样本量条件、统计窗口、设备和入口分桶、基线版本及回滚规则。平均值容易隐藏长尾，启动评审至少同时观察中位数、尾部分位和异常占比；具体阈值由产品目标、设备实验和稳定版本分布确定。

## Android 15 / 16 / 17 能力表

| 版本 | 启动记录 | profiling | 接入重点 |
|---|---|---|---|
| Android 15 / API 35 | `ApplicationStartInfo`、历史查询、首帧 completion listener、developer timestamps、`wasForceStopped()` | App-driven `ProfilingManager` | 处理未完成记录；reason 与业务入口联合分桶 |
| Android 16 / API 36 | 增加 `getStartComponent()` | 增加 `APP_FULLY_DRAWN`、`ANR` trigger | 组件分类改用 start component；Service launch timestamp 避免用于门禁 |
| Android 17 / API 37 | 延续并修正版本边界 | 增加 `COLD_START` 等 trigger | cold-start trace 与 stack sampling 只做抽样诊断 |

Android 15 以下继续使用 Application/Activity 生命周期、首帧、`reportFullyDrawn()` 和业务 ready 埋点。系统字段不可用时填 `unavailable`，不能用业务推断值伪装成 `ApplicationStartInfo`。

## 与 26.6 的边界

26.6 解释 Android 10–17 的退出追溯、App-driven profiling 和系统 trigger 总体能力。启动记录侧主要讨论 SDK 协议、分桶、时间戳、前后进程关联和监控接入。

ProfilingManager 的四类主动采集、结果字段、限流和 trigger 全表放在 26.6；启动流程与 TTID/TTFD 机制放在 8.2；退出原因细节也放在 26.6。这里引用这些能力，只为说明一次启动样本如何进入线上证据体系。

## 全文小结

`ApplicationStartInfo` 的价值是为启动样本补上系统归因，而不是代替业务 ready、TTID/TTFD 或 trace。接入时要先检查启动记录是否完成，再按 component、reason 与 cold/warm/hot 分桶；时间戳只在同一条记录、字段都存在且时钟口径一致时相减。

线上应长期保存轻量的启动 envelope，把 Android 17 cold-start profiling 作为低频附件，并用带置信度的关联边连接前一次 `ApplicationExitInfo`。CI、灰度和线上可以共享指标名称，但要各自保留实验条件、分布与原始证据，避免把系统字段缺失或产品流程变化误判为性能改善。

## 源码与官方文档锚点

- [ApplicationStartInfo.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationStartInfo.java)
- [ActivityManager.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [ProfilingTrigger.java（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [ApplicationStartInfo API reference](https://developer.android.com/reference/android/app/ApplicationStartInfo)
- [ActivityManager API reference](https://developer.android.com/reference/android/app/ActivityManager)
- [App startup time：TTID 与 TTFD](https://developer.android.com/topic/performance/vitals/launch-time)
- [ProfilingTrigger API reference](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [Macrobenchmark StartupMode](https://developer.android.com/reference/androidx/benchmark/macro/StartupMode)
- [Macrobenchmark startup metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
