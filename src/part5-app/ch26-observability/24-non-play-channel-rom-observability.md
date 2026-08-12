---
title: "非 Play 渠道性能监控与国内厂商 ROM 适配可观测性"
chapter: "26.24"
section: "26.24"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [non-play, domestic, ROM, observability, monitoring, OEM, channel]
related_chapters: ["25.25", "26.3", "26.15"]
task6_state: deep-reviewed
task9_state: ready-for-audit
pipeline_stage: deep_review_passed
last_draft_polish_at: "2026-08-05T23:47:01+08:00"
last_draft_polish_run_id: "20260805-234701-draft-polish-010c5e00"
last_deep_review_at: "2026-08-06T08:36:03+08:00"
last_deep_review_run_id: "20260806-083603-deep-review-010c5e00"
last_verified: "2026-08-06"
last_verified_against: "AOSP android-17.0.0_r1 public API sources; Android Developers API docs for ProfilingManager/ProfilingTrigger; Android Vitals data coverage documentation"
confidence: high
sources:
  - type: android-source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java"
  - type: android-source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java"
  - type: android-source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java"
  - type: android-source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/PackageManager.java"
  - type: android-source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java"
  - type: android-doc
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: android-doc
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: android-doc
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/querying-profiles"
  - type: android-doc
    path: "https://developer.android.com/about/versions/17/features"
  - type: android-doc
    path: "https://support.google.com/googleplay/android-developer/answer/9844486?hl=en"
---

# 26.24 非 Play 渠道性能监控与国内厂商 ROM 适配可观测性

## 非 Play 分发的观测缺口

[Android Vitals](https://support.google.com/googleplay/android-developer/answer/9844486?hl=en) 只统计符合其数据条件的 Google Play 安装。官方说明明确排除了未通过 Google Play 安装的应用版本，以及未通过认证的设备型号。一个 APK 即使同时发布到 Play 和其他市场，非 Play 安装产生的问题也不会自动进入同一份 Vitals 数据。

这不意味着国内 ROM 一定缺少诊断能力，也不意味着某个应用市场能够提供与 Vitals 等价的数据。可靠的做法是把平台公共 API、应用自身事件和服务端统计连成一条可审计的数据路径，再把厂商或渠道作为分析维度。厂商控制台、应用市场报表和第三方 APM 可以补充这条路径，但不能代替应用侧的事实记录。

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`。这里不维护一张“厂商行为排行榜”，也不把一次个案推广到整个品牌。ROM 会随机型、地区、版本、配置与用户设置变化，品牌名只能用于分组，不能单独证明原因。

## 端云数据路径

非 Play 场景仍应把指标、崩溃和 trace 分开处理。三类数据的体积、采样方式、隐私风险和服务端查询方式不同，把它们塞进同一种日志通常会导致限额失控。

下面的文本图用于说明各组件的职责。

```text
应用进程
├─ 指标采集：启动、帧、CPU、内存、任务执行、能力快照
├─ 稳定性采集：Java/Native 崩溃、ANR 线索、ApplicationExitInfo
├─ 诊断采集：命中策略后请求 profile 或保存应用内 trace
└─ 有界本地队列：版本化 schema、去重、限额、过期、用户同意状态
                         │
                         ▼
                  机会式批量上传
                         │
                         ▼
服务端入口 ──> 校验与限流 ──> 指标库 / 事件库 / trace 存储
                                  │
               构建与符号文件登记 ┤
                                  ▼
                    分群分析、告警、回归比较
```

“机会式”是这套设计的关键：后台任务没有精确执行时刻保证，进程也可能在上传前结束。本地队列需要有容量和保存期限，写入要能抵抗进程中断；上传成功后再删除对应批次。服务端则要把“没有收到”与“值为零”分开，否则后台限制较强的设备反而会从统计中消失。

每条事件至少需要以下几组字段：

| 字段组 | 建议内容 | 用途与边界 |
|---|---|---|
| 事件身份 | schema 版本、事件 ID、会话 ID、事件类型 | 会话 ID 不应包含账号或设备标识 |
| 时间 | wall clock、elapsed realtime、进程启动时刻 | wall clock 便于服务端对齐；单调时钟用于进程内耗时 |
| 应用构建 | versionCode、versionName、构建 ID、签名证书摘要、base/split 摘要 | 摘要用于确认是否为同一产物，不上传证书原文 |
| 分发 | 应用内声明的渠道、installing package、initiating package | 安装来源可能为空或发生变化，不能代替构建渠道 |
| 平台 | API、release、安全补丁、构建增量、fingerprint 的受控表示 | fingerprint 基数很高，应按隐私策略归一化或哈希 |
| 硬件群组 | manufacturer、model、device、ABI、page size、低内存设备标记 | 用于群组统计，不应拼成持久用户身份 |
| 运行状态 | 前后台、进程 importance、省电、热状态、刷新率、后台限制、standby bucket | 状态必须和被测事件尽量同时记录 |
| 采集质量 | collector 版本、采样原因、丢弃计数、队列年龄、上传重试状态 | 用于判断缺数和采集器自身回归 |

[`PackageManager.getInstallSourceInfo()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/PackageManager.java) 从 API 30 开始提供安装来源信息，但不同字段有权限与可见性条件，值也可能为空。应用应同时保留编译或分包阶段写入的明确渠道字段。二者不一致时记录差异，不要擅自选择一个作为“用户来自哪个市场”的答案。

## 采集公共能力快照

下面的 Kotlin 示例用于在 Android 12 至 Android 17 上读取当前应用可见的公共信号。它不读取设备标识，也不调用隐藏 API。

```kotlin
import android.app.ActivityManager
import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.Build
import android.os.PowerManager
import android.system.Os
import android.system.OsConstants

data class RuntimeCapabilitySnapshot(
    val sdkInt: Int,
    val release: String,
    val securityPatch: String,
    val manufacturer: String,
    val model: String,
    val supportedAbis: List<String>,
    val pageSizeBytes: Long,
    val lowRamDevice: Boolean,
    val backgroundRestricted: Boolean,
    val standbyBucket: Int,
    val powerSaveMode: Boolean,
    val thermalStatus: Int,
    val ignoringBatteryOptimizations: Boolean,
    val installingPackage: String?,
    val initiatingPackage: String?
)

fun readRuntimeCapabilitySnapshot(context: Context): RuntimeCapabilitySnapshot {
    val activityManager =
        context.getSystemService(ActivityManager::class.java)
    val usageStatsManager =
        context.getSystemService(UsageStatsManager::class.java)
    val powerManager =
        context.getSystemService(PowerManager::class.java)
    val installSource =
        context.packageManager.getInstallSourceInfo(context.packageName)

    return RuntimeCapabilitySnapshot(
        sdkInt = Build.VERSION.SDK_INT,
        release = Build.VERSION.RELEASE,
        securityPatch = Build.VERSION.SECURITY_PATCH,
        manufacturer = Build.MANUFACTURER,
        model = Build.MODEL,
        supportedAbis = Build.SUPPORTED_ABIS.toList(),
        pageSizeBytes = Os.sysconf(OsConstants._SC_PAGESIZE),
        lowRamDevice = activityManager.isLowRamDevice,
        backgroundRestricted = activityManager.isBackgroundRestricted,
        standbyBucket = usageStatsManager.appStandbyBucket,
        powerSaveMode = powerManager.isPowerSaveMode,
        thermalStatus = powerManager.currentThermalStatus,
        ignoringBatteryOptimizations =
            powerManager.isIgnoringBatteryOptimizations(context.packageName),
        installingPackage = installSource.installingPackageName,
        initiatingPackage = installSource.initiatingPackageName
    )
}
```

返回值只是一张瞬时快照。省电、热状态、standby bucket 与后台限制都会变化，因此服务端不能拿首次启动时的值解释几天后的任务延迟。`Build.MANUFACTURER` 和 `Build.MODEL` 还需要服务端做别名归并，但原始值的保存期限和访问范围要受隐私策略约束。

Android 17 的 [`ActivityManager.isBackgroundRestricted()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java) 文档给出了明确语义：返回 `true` 时，系统会严格限制该应用的后台执行；至少包括作业与闹钟不能执行，以及应用不在前台时不能启动前台服务。它能证明系统报告了限制状态，不能单独说明是哪个设置页面、策略模块或厂商组件造成的。

[`UsageStatsManager.getAppStandbyBucket()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java) 查询本应用时不需要 `PACKAGE_USAGE_STATS`。bucket 越受限，后台运行机会通常越少，而且系统可以随时调整 bucket。记录 bucket 有助于解释任务等待时间，但不能把它当成稳定的用户属性。

`isIgnoringBatteryOptimizations()` 只说明应用当前是否在电池优化豁免名单中。普通应用不应为了改善统计完整度而诱导用户豁免，更不能把豁免视为后台常驻承诺。

## 进程退出：用 ApplicationExitInfo 记录事实

Android 11 / API 30 引入 `ApplicationExitInfo`。Android 17 的 [`ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java) 定义了退出原因、状态码、进程重要性、时间戳、PSS、RSS、描述和可选 trace 流。应用在下次有机会运行时，可以通过 `getHistoricalProcessExitReasons()` 补记上次未上传的退出。

下面的代码用于按调用方给定的批量上限读取历史记录，并以复合键去重。

```kotlin
import android.app.ActivityManager
import android.app.ApplicationExitInfo
import android.content.Context

data class ExitRecord(
    val key: String,
    val timestampMillis: Long,
    val pid: Int,
    val processName: String?,
    val reason: Int,
    val status: Int,
    val importance: Int,
    val pssKilobytes: Long,
    val rssKilobytes: Long,
    val description: String?
)

fun readUnseenExitRecords(
    context: Context,
    batchLimit: Int,
    wasUploaded: (String) -> Boolean
): List<ExitRecord> {
    require(batchLimit > 0)
    val activityManager =
        context.getSystemService(ActivityManager::class.java)

    return activityManager.getHistoricalProcessExitReasons(
        context.packageName,
        0,
        batchLimit
    ).map { info ->
        val key = listOf(
            info.timestamp,
            info.pid,
            info.reason,
            info.status,
            info.processName
        ).joinToString(":")

        ExitRecord(
            key = key,
            timestampMillis = info.timestamp,
            pid = info.pid,
            processName = info.processName,
            reason = info.reason,
            status = info.status,
            importance = info.importance,
            pssKilobytes = info.pss,
            rssKilobytes = info.rss,
            description = info.description
        )
    }.filterNot { wasUploaded(it.key) }
}
```

示例没有读取 trace 内容，因为 trace 的体积、I/O、脱敏和保存策略应由独立采样流程控制。复合键也只是本地去重键，不应被当成设备身份。上报确认后再持久化已处理标记；只保存“最大时间戳”可能漏掉同一时间戳下的多条记录。

`pss` 与 `rss` 的单位是 kB，而且是系统最近一次采样值，不是进程退出瞬间的精确内存占用；系统来不及采样时还可能返回零。它们适合辅助分组，不能单独证明内存是退出原因。

解释退出原因时要留意几个边界：

- `REASON_CRASH`、`REASON_CRASH_NATIVE`、`REASON_ANR`、`REASON_USER_REQUESTED`、`REASON_PACKAGE_UPDATED` 等是平台给出的分类，可作为直接信号；
- `REASON_LOW_MEMORY` 并非所有设备都支持。先查 `ActivityManager.isLowMemoryKillReportSupported()`；不支持时，低内存终止可能只表现为 `REASON_SIGNALED` 与 `SIGKILL`；
- `REASON_FREEZER` 表示系统 freezer 相关退出，但不能据此命名某个厂商的后台管理功能；
- `REASON_UNKNOWN` 或一般的 `REASON_SIGNALED` 信息不足，不能自动标记为“被安全中心杀死”；
- subreason 在平台源码中属于隐藏信息，普通应用不应通过反射建立依赖。

可以用 `ActivityManager.setProcessStateSummary()` 写入少量、无敏感信息的当前业务阶段，帮助下一次启动解释退出发生前的应用状态。该摘要受平台长度限制，并可能随退出记录一起参与诊断，因此只适合稳定枚举，不适合 URL、搜索词、账号或自由文本。

## 缺失数据也要有语义

APM 事件中断只说明服务端没有继续收到数据。以下情况都可能产生相似表象：

- 进程正常或异常退出；
- 作业尚未获得运行机会，或者约束未满足；
- 网络不可用、服务器拒绝请求或本地队列已满；
- 用户关闭后台运行、撤回采集同意或清除应用数据；
- 用户对应用执行强行停止；在用户再次显式启动前，作业和闹钟不会恢复正常触发；
- 应用被卸载，此后不会再有“下次启动”上传退出记录。

因此，服务端应把会话结束、最近一次成功上传时刻、队列年龄和下一次启动时的退出补记放在一起看。若一直没有下次启动，系统没有提供一个让应用进程自行说明原因的机会。周期性心跳也不能改变这一点，因为它同样受进程、调度和网络条件约束。

建议给诊断结论标注证据等级：

| 等级 | 含义 | 可写出的结论 |
|---|---|---|
| A：平台直接信号 | 公共 API、系统回调、退出记录或明确异常 | “系统报告后台受限”“退出原因为 ANR” |
| B：时间相关 | 状态变化与问题在同一时间窗出现 | “问题与进入省电状态同时出现” |
| C：群组相关 | 某机型、版本或渠道的比率显著不同 | “该群组异常率较高，待对照实验” |
| D：用户描述 | 截图、客服反馈或复现叙述 | “用户报告开启某设置后恢复” |

只有 A 级证据适合直接写平台事实。B、C、D 级证据用于提出和筛选假设，不能改写成“该厂商会执行某策略”。

## 后台任务与前台服务怎么记录

`JobScheduler` 与 WorkManager 都不承诺精确启动时刻。观察一项后台任务时，至少记录：

- enqueue、计划条件和唯一工作名称；
- 系统允许的最早运行语义，而不是自行计算的“应当启动”时刻；
- worker 实际开始、结束、重试次数和输出状态；
- 当时的网络、充电、存储、standby bucket、后台限制与省电状态；
- WorkManager 或 JobScheduler 暴露的停止原因；
- 前台服务启动请求、异常类型、`onStartCommand()` 和 `onDestroy()` 时刻。

一个任务晚于业务期望启动，可能仍符合 API 契约。只有在同一应用构建、相同约束和受控设备设置下做对照实验，才能判断某个系统版本是否引入了额外差异。不要把固定延迟值写成某个 ROM 的默认规则。

对前台服务也要按 Android 版本规则处理服务类型、启动窗口和权限。捕获 `ForegroundServiceStartNotAllowedException` 等公共异常，比解析厂商日志关键字更适合线上统计；厂商日志可作为实验室取证，不能成为 release 应用的稳定协议。

## ADPF：先协商能力，再看效果

[`PerformanceHintManager`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java) 是 ADPF 的公共入口。Android 17 源码中，`createHintSession()` 在设备不支持 hint session 或线程不属于调用应用等情况下可以返回 `null`，错误参数也可能抛出异常。应用应按服务和 session 的实际结果协商能力，不能维护“某品牌或某 SoC 必然支持”的静态表。

一次可分析的 hint session 应记录：

- manager 是否可取得、session 是否创建成功和失败类型；
- 目标工作时长及每次上报的实际工作时长；
- 参与线程集合变更；
- session 对应的渲染或计算阶段；
- 同场景下的帧、CPU time、热状态、功耗代理指标和质量级别。

ADPF 是向系统表达负载意图的控制接口，不是性能指标。session 创建成功也不能证明体验改善。若不可用，应用应回到自身已有的质量分级、工作量控制和线程模型，继续记录结果；不要私自写 CPU 频率，也不要把提升线程优先级当成通用替代方案。

## ProfilingManager：请求可能不执行

[`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager) 从 Android 15 / API 35 开始提供公共 profiling 请求，可请求 system trace、Java heap dump、heap profile 与 stack sampling。官方契约强调请求受频率限制，并不保证每次都执行。结果写入应用数据目录并通过 listener 通知；系统会按应用边界处理数据，普通应用不能借此读取其他进程的任意内容。

Android 16 / API 36 增加 `ProfilingTrigger`；Android 17 / API 37 继续扩展 profiling 的系统触发场景。具体 API 变化应按 [`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger) 和 [Android 17 功能说明](https://developer.android.com/about/versions/17/features) 适配，而不是按主线源码预览外推。使用系统触发时要注册全局结果 listener，因为结果不一定来自当前一次显式请求。

这里不把“请求没有结果”直接归因于厂商裁剪。可能原因包括不支持的版本、参数错误、频率限制、系统资源状态、进程生命周期或实现问题。应用需要记录请求类型、请求时刻、回调结果和超时后的未知状态，再在目标设备上复现。

API 35 以下没有 ProfilingManager，应使用适合该版本的公共指标、Android Studio、Perfetto 或 Simpleperf 完成实验室诊断。不能把读取受保护 ftrace 节点或 hook 平台私有实现包装成它的线上降级方案。Android 17 上 profile 的查询与脱敏边界可参考官方的 [ProfilingManager profile 查询说明](https://developer.android.com/topic/performance/tracing/profiling-manager/querying-profiles)。

## 帧、CPU 与系统状态

应用可以使用 `FrameMetrics`、AndroidX JankStats、`Choreographer` 和应用内 trace 观察自己的帧。进入省电、热限制或刷新率切换后，帧节奏和预算可能变化，所以事件旁边要记录显示模式、刷新率、热状态和省电状态。没有公开证据表明某品牌会系统性修改 `FrameMetrics` 的“精度”，不要把采样差异写成厂商结论。

CPU 监控也要保持应用边界。`ProcessCpuTracker` 是 framework 内部实现，不是第三方应用公共 API。线上应用可使用：

- `Process.getElapsedCpuTime()` 观察本进程累计 CPU time；
- `/proc/self/stat` 或 `/proc/self/task/<tid>/stat` 读取当前进程可见计数，并按内核时钟频率换算；
- ProfilingManager、Perfetto 或 Simpleperf 在各自允许的环境中做采样分析。

`/proc` 可见性、字段解析和采样开销应按 [26.20] 的边界处理。某个节点不可读时记录能力缺失，不要通过扩大权限或扫描其他进程规避。

## 渠道性能比较如何避免误判

渠道不是独立变量。它常与厂商、型号、地区、系统版本、应用产物、ABI、签名、安装时间和用户群同时变化。直接比较“渠道 A 平均启动时长”和“渠道 B 平均启动时长”，很容易把设备结构差异写成安装市场影响。

实验室比较应满足这些条件：

- 使用同一源码和等价构建参数，记录 base APK、split APK、签名与 native 库摘要；
- 明确安装方式、首次安装或覆盖安装、应用数据状态和编译状态；
- 在相同设备与系统镜像上交叉安装，重复冷启动和热启动；
- 记录 ABI、page size、存储余量、温度、充电状态和网络条件；
- 把安装完成到首次启动的系统日志作为辅助证据。

线上分析则按应用版本、产物摘要、API、厂商、型号、系统构建、ABI、page size、地区、安装来源和明确渠道分层，并报告样本量、分位数和置信区间。需要跨群组比较时，使用匹配或回归控制已知差异，同时保留未观测混杂的说明。

启动变慢不能直接推出“应用商店没有做 dexopt”，启动变快也不能证明市场执行了预优化。要验证编译因素，需要在受控设备上检查 package 编译状态、安装会话和运行时 profile 条件，并保持 APK 与数据状态一致。

## 厂商安全中心与用户引导

不要把“加入白名单”设计成所有用户第一次启动时的必做步骤。更合适的触发条件是：

1. 公共 API 已显示后台受限，或多次任务记录显示约束满足后仍未运行；
2. 该功能依赖及时后台执行，延迟会给用户带来可解释的影响；
3. 当前机型和系统版本的页面路径经过验证；
4. UI 说明用户将改变什么设置、可能增加什么耗电，以及如何恢复。

设置页面和厂商说明会变化，应用应使用当前官方文档和受支持的 Intent；打开失败时停留在系统通用设置，不要扫描已安装包寻找安全中心，也不要为监控申请与功能无关的广泛权限。

所谓“厂商行为库”也应保存证据，不是保存传闻。每条记录至少包含机型、系统构建、应用构建、复现步骤、观察信号、对照组、证据等级和失效日期。系统升级后重新验证，不能沿用旧 ROM 结论。

## 自建与第三方 APM 的选型

产品名单、套餐和厂商支持会变化，不适合维护静态营销对照表。选型时用同一组样例事件和目标设备验证以下项目：

| 维度 | 需要验证的问题 |
|---|---|
| 信号覆盖 | Java/Native 崩溃、ANR、ApplicationExitInfo、启动、帧、网络、trace 分别如何采集 |
| 符号化 | R8 mapping、native symbol、build ID、split 和动态特性如何对应 |
| 离线能力 | 队列容量、过期、断点续传、进程中断后的写入一致性 |
| 采集开销 | 不同事件密度下的 CPU、内存、I/O、包体和网络变化 |
| 数据质量 | 采样率、丢弃计数、重复事件、时钟和 schema 升级是否可见 |
| 隐私与安全 | 同意、字段脱敏、传输与存储加密、数据驻留、删除和访问审计 |
| 数据控制 | 原始数据能否导出、保存周期、查询接口、SDK 与后端是否可替换 |
| 运维 | 限流、告警、符号上传、版本回滚和 SDK 自身故障如何处理 |

Tinker 是热修复框架，不应因为与某些稳定性产品一起出现就把它当成 APM。厂商控制台或应用市场若提供性能报告，也要确认它覆盖的是哪些安装、哪些设备、何种采样人群，再决定它能否补充自建数据。

## 排障顺序

遇到“某渠道、某 ROM 数据少或性能差”时，可以按下面顺序推进：

1. 核对事件 schema、采样、限流、队列和服务端接收，排除采集器回归。
2. 核对应用构建、签名、split、ABI、安装来源和明确渠道，确认比较对象。
3. 查看后台限制、standby bucket、省电、热状态、网络与任务生命周期。
4. 在下次启动补记 `ApplicationExitInfo`，区分已知退出与未知中断。
5. 按机型、系统构建和应用版本分群，检查样本量与置信区间。
6. 用同一设备、同一产物和受控状态复现，并保存系统 trace 或 profiler 证据。
7. 只有在直接证据支持时，才形成厂商或系统版本级结论，并设置复验日期。

这套顺序要求每个判断都能回到记录、API 契约或可重复实验。非 Play 可观测性的难点在于明确数据覆盖范围，以及每个归因所依据的证据等级。
