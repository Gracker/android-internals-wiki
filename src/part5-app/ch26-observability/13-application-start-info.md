---
title: "ApplicationStartInfo 与启动归因上报"
chapter: "26.13"
status: ready-for-review
drafted_date: "2026-05-18"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
last_verified: "2026-05-18"
last_verified_against: "AOSP main ApplicationStartInfo / ActivityManager, Android Developers ApplicationStartInfo / ProfilingTrigger docs, Clippings structure references"
confidence: medium
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationStartInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessStartReasons(int)"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationStartInfo.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java"
tags: [observability, startup, application-start-info, profilingmanager]
related_chapters: ["8.2", "8.10", "14.7", "26.9", "26.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "研究素材/官方文档/章节深挖/Clippings结构参考"
source_refs:
  - "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md]"
  - "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]"
  - "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]"
  - "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]"
  - "[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md]"
  - "intake/research-gaps.md#2026-05-17-26-12"
  - "developer.android.com/reference/android/app/ApplicationStartInfo"
  - "developer.android.com/about/versions/17/features"
pipeline_stage: "task2b_pending"
task2a_result: draft-ready-for-review
last_task2a_at: "2026-05-18T04:14:00+08:00"
---

# 26.13 ApplicationStartInfo 与启动归因上报

<!-- outline-start -->
## 要点

### 🔹 启动归因在可观测性链路中的位置
把 `ApplicationStartInfo` 放到启动性能、Crash/ANR 补偿和线上诊断证据包之间，明确它解决的是「这次进程为什么被拉起、属于哪类启动、各阶段时间戳如何落盘」。

### 🔹 Android 15 `ApplicationStartInfo` 的字段边界
梳理 `ActivityManager.getHistoricalProcessStartReasons()`、`getStartType()`、`getReason()`、`getStartupTimestamps()`、`START_TIMESTAMP_*` 的可用范围，并标注 API 35 起可用。

### 🔹 冷启动、温启动、热启动的线上分流口径
建立线上指标侧的启动类型分流规则：只把 `START_TYPE_COLD` 纳入冷启动 SLA，把温启动/热启动、后台拉起、广播拉起、Provider 拉起从冷启动指标中拆开。

### 🔹 启动时间戳与业务埋点的合并协议
定义 SDK envelope：系统时间戳、业务首屏时间、`reportFullyDrawn()`、页面 ready、广告/引导扣除、trace id 和版本字段，避免只依赖单一耗时指标。

### 🔹 Android 17 `ProfilingTrigger` 的冷启动触发关系
对齐 `TRIGGER_TYPE_COLD_START` 与 `ApplicationStartInfo.getStartType() == START_TYPE_COLD` 的前提，说明触发式 profiling 与常规启动上报的分工。

### 🔹 数据保留、采样率与隐私边界
覆盖历史记录条数、回调时机、采样率、端侧缓存、脱敏字段、用户同意和结果文件上传策略，避免启动诊断能力演变成无限制日志采集。

### 🔹 与 ApplicationExitInfo 的联合归因
把启动前一次退出原因和本次启动原因合并：崩溃循环、包更新后首启、组件状态变化、低内存杀进程后重启分别进入不同排障路径。

## 扩展

### 🔸 Android 15/16/17 版本能力表
补一张 API 35 `ApplicationStartInfo`、API 36 `ProfilingManager`、API 37 `ProfilingTrigger` 的能力边界表。

### 🔸 CI 与灰度监控接入
给出 Macrobenchmark、线上 P90/P99、trace 抽样和灰度回滚门禁之间的字段映射。

### 🔸 与 26.12 的拆分边界
26.12 继续讲版本化诊断能力总表；本节只写启动归因上报的 SDK 设计、字段协议和实战排障入口。

<!-- outline-end -->

本节只讨论启动归因上报。8.2 已经讲启动流程和 TTID / TTFD 定义，21.8 讲启动监控指标，26.12 讲版本化诊断入口总表；这里补齐 Android 15 之后应用能从系统拿到的启动原因、启动类型、阶段时间戳，以及这些字段怎样进入线上 SDK 协议。

参考资料里，启动监控部分把启动耗时拆成实验室监控、线上监控、启动类型、耗时扣除和线上堆栈采样；数据上报部分把采样、存储、上报、容灾和自监控放在同一套组件里。本节借鉴这个组织顺序，但字段和 API 以 Android 公开文档、AOSP 路径和现有章节为准，不复用参考书原文。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md][结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md][结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

## 启动归因补的是线上证据缺口

线上启动慢通常会混进几类样本：用户点击桌面图标的冷启动、最近任务回到前台、通知点击拉起、广播或 Job 触发的后台进程、覆盖安装后的首次启动、低内存杀进程后的恢复启动。只看业务埋点的 `launch_duration_ms`，这些样本会落在同一张图里，P90 / P99 会被后台拉起和特殊场景污染。

`ApplicationStartInfo` 提供的价值，是把系统已经知道的启动来源和启动阶段补进上报协议。它不能替代业务首屏埋点，也不能替代 Perfetto；它回答的是三个问题：进程为什么启动、属于冷 / 温 / 热哪一类、系统记录到哪些阶段时间戳。[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationStartInfo]

这层数据落库后，启动监控的第一步不再是算平均值，而是先分流：用户可感知冷启动进 SLA，后台组件拉起进健康度统计，温启动和热启动单独看活跃恢复，特殊来源进入排障队列。

## Android 15 的入口和字段边界

Android 15 / API 35 起，应用可以通过 `ActivityManager#getHistoricalProcessStartReasons(int maxNum)` 读取最近的 `ApplicationStartInfo` 记录。`maxNum = 0` 表示返回所有匹配记录；返回列表按从近到远排序；记录来自系统环形缓冲，只保证最近一批启动记录还在。[已验证: 官方文档, developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessStartReasons(int)]

同一类信息也可以通过 `ActivityManager#addApplicationStartInfoCompletionListener(Executor, Consumer<ApplicationStartInfo>)` 回调取得。这个回调的完成点是首帧绘制完成，不等待 `Activity.reportFullyDrawn()`；如果要读 `START_TIMESTAMP_FULLY_DRAWN`，需要在业务调用 `reportFullyDrawn()` 之后，再取一份新的 `ApplicationStartInfo` 记录。[已验证: 官方文档, ActivityManager.addApplicationStartInfoCompletionListener]

| 字段 | 适合落库的含义 | 使用边界 |
|---|---|---|
| `getStartType()` | 冷启动、温启动、热启动 | `START_TYPE_COLD` 表示进程从零创建；`START_TYPE_WARM` / `START_TYPE_HOT` 不进入冷启动 SLA |
| `getReason()` | 启动来源 | 包括 `START_REASON_LAUNCHER`、`START_REASON_ALARM`、`START_REASON_BROADCAST`、`START_REASON_CONTENT_PROVIDER`、`START_REASON_JOB`、`START_REASON_PUSH`、`START_REASON_SERVICE`、`START_REASON_START_ACTIVITY`、`START_REASON_OTHER` 等 |
| `getStartupState()` | 记录完成度 | `STARTUP_STATE_STARTED` 只保证启动已开始；`STARTUP_STATE_ERROR` 表示启动失败；`STARTUP_STATE_FIRST_FRAME_DRAWN` 才适合计算首帧相关耗时 |
| `getStartupTimestamps()` | 系统阶段时间戳 | 返回 `Map<Integer, Long>`，key 是 `START_TIMESTAMP_*` 常量，value 是 monotonic clock 时间戳；每个 key 都要判空 |
| `getStartComponent()` | 组件类别 | API 36 起补充 Activity / Service / Broadcast / ContentProvider / Other 这类粗分类 |
| `getIntent()` | 启动 Intent | 只建议端侧辅助判断，默认不上传完整 URI、extras 或 referrer |

AOSP `ApplicationStartInfo.java` 里，`START_TYPE_COLD = 1`、`START_TYPE_WARM = 2`、`START_TYPE_HOT = 3`；时间戳常量覆盖 `LAUNCH`、`FORK`、`BIND_APPLICATION`、`APPLICATION_ONCREATE`、`FIRST_FRAME`、`FULLY_DRAWN`、`SURFACEFLINGER_COMPOSITION_COMPLETE` 等阶段。[已验证: AOSP main, frameworks/base/core/java/android/app/ApplicationStartInfo.java]

`getStartupTimestamps()` 的返回值不是 `Bundle`。线上 SDK 读取时必须按 `Map<Integer, Long>` 处理，并把缺失 key 当作正常边界，而不是异常数据。

这段代码只演示安全读取方式。重点是判断 `startupState` 和 timestamp key，不直接 unbox。

```kotlin
@RequiresApi(35)
fun collectLatestStartInfo(context: Context): StartInfoSnapshot? {
    val am = context.getSystemService(ActivityManager::class.java)
    val latest = am.getHistoricalProcessStartReasons(1).firstOrNull() ?: return null
    val timestamps = latest.startupTimestamps

    fun ts(key: Int): Long? = timestamps[key]

    return StartInfoSnapshot(
        startType = latest.startType,
        reason = latest.reason,
        startupState = latest.startupState,
        launchNs = ts(ApplicationStartInfo.START_TIMESTAMP_LAUNCH),
        forkNs = ts(ApplicationStartInfo.START_TIMESTAMP_FORK),
        bindApplicationNs = ts(ApplicationStartInfo.START_TIMESTAMP_BIND_APPLICATION),
        applicationOnCreateNs = ts(ApplicationStartInfo.START_TIMESTAMP_APPLICATION_ONCREATE),
        firstFrameNs = ts(ApplicationStartInfo.START_TIMESTAMP_FIRST_FRAME),
        fullyDrawnNs = ts(ApplicationStartInfo.START_TIMESTAMP_FULLY_DRAWN),
        surfaceFlingerCompositionNs = ts(
            ApplicationStartInfo.START_TIMESTAMP_SURFACEFLINGER_COMPOSITION_COMPLETE,
        ),
    )
}
```

这段代码只把系统原始字段收集成快照。耗时计算放到后面的归一化层，避免采集层同时处理 API 兼容、缺失字段和指标口径判断。

## 冷启动指标先按系统启动类型分流

线上冷启动 SLA 只统计 `getStartType() == START_TYPE_COLD` 的样本。`START_TYPE_WARM` 和 `START_TYPE_HOT` 反映的是已有进程或保留状态的恢复路径，优化对象和用户体感都不同；混在冷启动里，会让回归判断失真。

启动来源还要再分一层：

- `START_REASON_LAUNCHER` / `START_REASON_LAUNCHER_RECENTS`：用户显式进入应用，适合作为用户可感知启动监控主样本。
- `START_REASON_START_ACTIVITY`：可能来自外部 App 跳转、通知点击或深链入口，要结合业务 route、referrer 和 Intent 类别归因。
- `START_REASON_BROADCAST` / `START_REASON_SERVICE` / `START_REASON_JOB` / `START_REASON_ALARM`：常见于后台任务或系统事件，不进入首页冷启动 SLA，但要进入后台拉起健康度统计。
- `START_REASON_PUSH`：单独看推送到达、点击、冷启动展示之间的漏斗，避免和普通桌面启动混算。
- `START_REASON_CONTENT_PROVIDER`：重点排查三方 SDK、初始化 Provider 和跨进程查询，详见 1.10。
- `START_REASON_OTHER`：保留原始系统字段和业务上下文，进入待分类样本池。

这套分流口径和参考书中的“冷启动、温启动、首次安装启动、覆盖安装启动分开统计”方向一致，但 Android 15 之后可以把其中一部分判断交给系统字段。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]

## 系统时间戳要和业务首屏协议合并

`ApplicationStartInfo` 的时间戳适合描述系统启动阶段，业务首屏埋点适合描述用户看到的页面状态。两者不能互相替代。

建议 SDK 上报一份启动 envelope，把系统字段、业务字段和扣除规则放在同一条记录里：

| 字段组 | 字段 | 说明 |
|---|---|---|
| 系统归因 | `api_level`、`start_type`、`start_reason`、`start_component`、`startup_state` | Android 15+ 填系统值；低版本填 `unavailable` |
| 系统时间戳 | `launch_ns`、`fork_ns`、`bind_application_ns`、`app_on_create_ns`、`first_frame_ns`、`fully_drawn_ns`、`sf_composition_ns` | 统一用 monotonic clock；缺失字段不补 0 |
| 业务首屏 | `home_ready_elapsed_ms`、`first_interactive_elapsed_ms`、`route_name`、`entry_scene` | 由业务 SDK 打点，和系统时间戳分列保存 |
| 口径扣除 | `splash_deduct_ms`、`ad_deduct_ms`、`guide_deduct_ms`、`deduct_reason` | 只在明确产品口径要求时使用，原始耗时仍保留 |
| 诊断关联 | `session_id`、`trace_id`、`case_id`、`app_version`、`build_fingerprint_hash` | 用于关联 Crash / ANR / trace / 服务端日志 |
| 隐私控制 | `sample_policy_version`、`consent_state`、`upload_policy` | 记录采样和授权状态，便于审计 |

参考书强调线上启动耗时要处理结束点、广告 / 引导扣除和启动类型。这里建议保留“原始耗时”和“业务扣除后耗时”两列：原始列用于研发回归，扣除列用于产品体验报表。只保留扣除后数字，会让版本之间的技术变化难以复盘。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]

系统时间戳计算阶段耗时时，使用相邻 timestamp 的差值，不跨口径硬算。例如 `APPLICATION_ONCREATE - BIND_APPLICATION` 可以近似看应用 `onCreate()` 入口前后；`FIRST_FRAME - LAUNCH` 可以作为系统首帧链路观察值；`FULLY_DRAWN` 只有业务主动调用 `reportFullyDrawn()` 后才有意义。TTID / TTFD 的定义和平台统计口径详见 8.2。

## Android 17 冷启动 trigger 负责采样现场

Android 17 / API 37 新增 `ProfilingTrigger.TRIGGER_TYPE_COLD_START`。官方说明里，这个 trigger 在应用冷启动时尽早触发，响应结果包含 system trace 和 stack sampling profile；触发前提等价于 `ApplicationStartInfo.START_TYPE_COLD`。[已验证: 官方文档, developer.android.com/reference/android/os/ProfilingTrigger][已验证: 官方文档, developer.android.com/about/versions/17/features]

它和常规启动上报的分工很清楚：

| 能力 | 作用 | 适合频率 | 结果 |
|---|---|---:|---|
| `ApplicationStartInfo` | 每次启动的原因、类型和阶段时间戳 | 可按较高比例上报轻量字段 | 结构化字段 |
| 业务启动 envelope | 首页 ready、交互可用、扣除规则、业务入口 | 可按产品线策略上报 | 结构化字段 |
| `TRIGGER_TYPE_COLD_START` | 冷启动慢样本的系统 trace 和调用栈 | 低比例、强限流、灰度或问题版本开启 | trace / stack sample 文件 |
| `TRIGGER_TYPE_APP_FULLY_DRAWN` | `reportFullyDrawn()` 后触发的 profiling | 低比例、用于校验 TTFD 附近现场 | profiling 结果文件 |

`ProfilingTrigger.Builder#setRateLimitingPeriodHours()` 可以给单个 trigger 设置限流周期。线上接入时，冷启动 trigger 不应默认全量开启；更稳的做法是用远程配置对版本、渠道、设备档位和采样用户分层，只在 P90 / P99 异常或灰度版本放量时打开。[已验证: 官方文档, developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture]

ProfilingManager 的 builder、结果回调、文件目录和错误码详见 14.7；各 trigger 的产物类型和版本边界详见 8.10。本节只把冷启动 trigger 放进启动归因协议，不重复展开工具机制。

## 数据上报要按高可用组件设计

启动归因字段很轻，但冷启动 trace、stack sample、用户日志都可能很重。上报组件至少要处理采样、端侧缓存、上传、容灾和自监控五类问题。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

- 采样策略：轻量结构化字段可以按 UV 采样或问题版本提高比例；profiling 文件必须低比例，并受远程开关、系统限流和本地磁盘预算共同约束。
- 端侧缓存：启动 envelope 先写本地小文件或 mmap 队列，避免首启阶段同步网络请求；上传失败后按过期时间和磁盘上限清理。
- 上传策略：普通字段走批量上报；trace / stack sample 先写诊断索引，再按 Wi-Fi、电量、授权和 case 优先级上传文件。
- 自监控：记录采样命中率、落盘失败率、上传到达率、文件超限清理次数、ProfilingResult 错误码分布。
- 容灾处理：如果本地文件堆积、加密失败、压缩失败或服务端拒收，SDK 要自动降级为只上传轻量字段。

采样配置需要有版本号。客户端每次上报携带本地策略版本，服务端发现版本落后时在回包里返回新策略。这样不依赖推送，也能让采样和开关随正常上报逐步生效。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]

## 隐私边界要写进协议

`ApplicationStartInfo` 可能包含 `Intent`，profiling 结果可能包含线程名、方法名、类名、对象类型、文件路径和业务栈信息。启动诊断协议默认只上传枚举、耗时、hash 后设备指纹和业务场景名，不上传完整 Intent URI、extras、referrer、用户输入内容或原始日志片段。

诊断文件上传需要单独策略：

- 只在用户协议、隐私政策和远程配置允许时上传。
- 文件在端侧加密，传输走 HTTPS，服务端按 case 设置访问权限。
- 保留期限独立于普通埋点，过期后自动删除。
- trace / heap / stack sample 文件进入脱敏和访问审计，不和普通 BI 数据混库。
- 对未登录用户使用端侧随机 ID 或安装 ID 时，记录生成方式、重置条件和跨 App 边界。

用户日志章节里提到全量日志、主动上报和按用户拉取能提升疑难问题排查效率；放到启动归因场景，原则是“先轻量字段定位，再按授权和采样拿重文件”。不要把冷启动诊断能力扩成长期、无限制的行为采集。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md]

## 和 ApplicationExitInfo 合并做启动后验

启动慢有时不是启动阶段本身造成的，而是上一次退出状态改变了本次启动路径。Android 11+ 的 `ApplicationExitInfo` 负责回答“上次为什么退出”，Android 15+ 的 `ApplicationStartInfo` 负责回答“本次为什么启动”。两条记录合并后，排障入口会更准。

| 上次退出 | 本次启动 | 排障方向 |
|---|---|---|
| Java / native crash | 短时间内 `START_TYPE_COLD` + `START_REASON_LAUNCHER` | 崩溃循环或 SafeMode，详见 20.7、26.2 |
| ANR | 再次冷启动并进入同一业务 route | ANR 后用户重进，关联 26.9 的 trace / reason 和本节启动 envelope |
| low memory / cached kill | `START_TYPE_COLD` 但业务认为是恢复场景 | 恢复路径和状态重建耗时，避免算成普通桌面冷启动 |
| package updated / package state changed | 安装或升级后首启 | 单独进入升级首启指标，不和普通冷启动混算 |
| user requested / force stop | 用户主动结束后启动 | 不按崩溃恢复处理，但可以观察重启后的首屏路径 |

`ApplicationExitInfo` 的 reason 版本差异详见 26.9 和 26.12。这里的落库关键，是把 `previous_exit_key` 和 `current_start_key` 关联起来：`processName`、`pid`、`timestamp`、`appVersion`、`sessionId`、`bootCount`、`elapsedRealtime` 都可以参与去重。不要只用 wall clock 时间戳，用户改系统时间会让关联结果不稳定。

## Android 15/16/17 能力表

| 版本 | 启动归因能力 | profiling 能力 | 本节建议 |
|---|---|---|---|
| Android 15 / API 35 | `ApplicationStartInfo`、`getHistoricalProcessStartReasons()`、completion listener、启动类型 / 原因 / 时间戳 | `ProfilingManager` 应用驱动采集 | 结构化启动 envelope 可以上线，trace 仍以主动采集为主 |
| Android 16 / API 36 | `ApplicationStartInfo` 继续可用，`getStartComponent()` 这类组件分类补齐 | `ProfilingTrigger` 覆盖 `APP_FULLY_DRAWN`、`ANR` 等事件 | TTFD 校验和 ANR 现场采样可进入灰度策略 |
| Android 17 / API 37 | `ApplicationStartInfo.START_TYPE_COLD` 可作为冷启动 trigger 前提 | `TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 等新增 | 冷启动慢样本可按低比例采 trace / stack sample |

低于 Android 15 的设备仍然需要自建启动埋点：Application / Activity 生命周期、首帧回调、`reportFullyDrawn()`、业务首页 ready、启动来源 route。为了报表连续性，SDK 的字段名保持一致，系统不可用字段填 `unavailable`，不要用业务推断值伪装成系统字段。

## CI 与灰度门禁的字段映射

实验室、CI 和线上灰度各自回答的问题不同，字段也不要混在一起。

| 场景 | 工具 / 数据 | 建议字段 | 门禁判断 |
|---|---|---|---|
| CI | Macrobenchmark `StartupTimingMetric`、Baseline Profile 检查 | `startup_mode`、TTID、TTFD、trace 文件、baseline profile 状态 | 相同设备、相同 build type 下对比阈值 |
| 实验室复现 | Perfetto、Logcat displayed、`reportFullyDrawn()` | `case_id`、trace id、系统阶段耗时、业务首屏耗时 | 定位阶段瓶颈，不直接代表线上 P90 |
| 灰度 | 启动 envelope、`ApplicationStartInfo`、采样 trace | `start_type`、`start_reason`、`route_name`、P50 / P90 / P99、异常版本号 | 普通冷启动、升级首启、后台拉起分桶判断 |
| 线上问题 | `ApplicationExitInfo` + `ApplicationStartInfo` + profiling 文件 | previous exit、current start、trace / stack sample 索引 | 判断是否进入 Crash / ANR / 启动性能排障队列 |

灰度回滚不要只看平均值。启动耗时通常长尾明显，P90 / P99、超阈值比例、低端机分桶、升级首启分桶更能反映用户体感。参考书对“90% 用户启动时间”和启动类型分流的建议，在 Android 15+ 可以落到 `start_type`、`start_reason` 和业务 route 三个维度上。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]

## 与 26.12 的拆分边界

26.12 负责回答“不同 Android 版本有什么线上诊断入口”。本节负责回答“启动这类问题怎样上报和归因”。

因此，版本能力表只保留启动相关字段；ProfilingManager 的通用采集方式不在这里重写；ApplicationExitInfo 也只作为前一次退出证据参与联合归因。读者要接工具，去 14.7；要看 trigger 细节，去 8.10；要看退出原因，去 26.9；要看完整版本化排障总表，去 26.12。
