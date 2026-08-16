---
title: "非 Play 渠道性能监控与国内厂商 ROM 适配可观测性"
chapter: "26.24"
section: "26.24"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [non-play, domestic, ROM, observability, monitoring, OEM, channel]
related_chapters: ["1.27", "14.11", "25.14", "26.8", "26.15", "26.20"]
task6_state: deep-reviewed
task9_state: ready-for-audit
pipeline_stage: deep_review_passed
last_draft_polish_at: "2026-08-05T23:47:01+08:00"
last_draft_polish_run_id: "20260805-234701-draft-polish-010c5e00"
last_deep_review_at: "2026-08-06T08:36:03+08:00"
last_deep_review_run_id: "20260806-083603-deep-review-010c5e00"
last_verified: "2026-08-16"
last_source_verified_at: "2026-08-16"
last_verified_against: "AOSP android-17.0.0_r1; current Android API 37, Android Vitals, ProfilingManager, ProfilingTrigger, and JobScheduler docs retrieved 2026-08-16"
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
  - type: android-doc
    path: "https://developer.android.com/reference/android/content/pm/InstallSourceInfo"
  - type: android-doc
    path: "https://developer.android.com/reference/android/app/ActivityManager"
  - type: android-doc
    path: "https://developer.android.com/reference/android/app/usage/UsageStatsManager"
  - type: android-doc
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: android-doc
    path: "https://developer.android.com/reference/android/os/PerformanceHintManager"
  - type: android-doc
    path: "https://developer.android.com/reference/android/app/job/JobScheduler"
  - type: android-doc
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: android-doc
    path: "https://developer.android.com/topic/performance/tracing/profile-types-overview"
---

# 26.24 非 Play 渠道性能监控与国内厂商 ROM 适配可观测性

## 非 Play 分发的观测缺口

[Android Vitals](https://support.google.com/googleplay/android-developer/answer/9844486?hl=en) 的数据来自选择共享使用情况与诊断信息的部分用户和设备。官方说明明确排除未通过 Google Play 安装的应用版本，以及未通过认证的设备型号。

APK 是 Android 应用安装包。同一个 APK 即使同时发布到 Play 与其他市场，非 Play 安装产生的问题也不会自动进入同一份 Vitals 数据。

这里的 ROM 指设备厂商基于 Android 定制的系统构建，沿用的是行业叫法，与“只读存储器”的硬件含义不同。渠道指应用的分发来源或构建变体，例如 Google Play、厂商市场或企业分发；渠道字段适合分组，单独使用时不能证明性能原因。

国内 ROM 仍可能提供诊断能力，应用市场也可能有自己的质量报表，但二者的覆盖条件不能直接视为 Vitals 等价物。可靠做法是把平台公共 API、应用自身事件与服务端统计组成可审计的数据路径，再把厂商和渠道作为分析维度。

APM 是 Application Performance Monitoring 的缩写，指持续采集应用性能与稳定性信号的一类系统。厂商控制台、应用市场报表和第三方 APM 可以补充自建数据，应用侧记录仍是确认具体版本、场景和采集质量的基础。

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`。这里不维护一张“厂商行为排行榜”，也不把一次个案推广到整个品牌。ROM 会随机型、地区、版本、配置与用户设置变化，品牌名只能用于分组，不能单独证明原因。

## 端云数据路径

非 Play 场景仍应把指标、崩溃事件和 trace 分开处理。指标是可聚合的数值，崩溃事件描述一次离散故障，trace 则保存一段时间内的细粒度事件与时间戳。三者的体积、采样方式、隐私风险和服务端查询方式不同，塞进同一种日志容易造成容量与上传限额失控。

文本图中的 schema 是事件字段、类型和编码的版本化约定；有界队列则给本地数据设置容量与保存期限，避免离线期间无限增长。

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

“机会式”表示满足网络、电量和调度条件时才尝试上传，不承诺精确执行时刻。进程也可能在上传前结束，因此本地队列要限制容量与保存期限，写入要能抵抗进程中断；收到服务端确认后再删除对应批次。

服务端要区分“没有收到事件”和“指标值为零”。前者可能表示进程、调度、网络或队列出了问题；若把两种情况合并，后台限制较强的设备会从统计中消失。

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

wall clock 是可能被用户或网络校时调整的日历时间，便于服务端按日期对齐。elapsed realtime 是从设备启动起单调递增的时间，适合计算同一设备上的耗时；跨设备比较前仍要转换到共同时间基准。

进程 importance 是 `ActivityManager` 对进程当前重要程度的分类，例如是否承载前台界面或用户可感知工作。它会随组件生命周期变化，记录时应保留原始常量和 API 版本。

构建 ID 与证书、APK 摘要用于确认事件对应哪份产物。摘要是原数据经过散列函数得到的固定长度值，可用于一致性比较，但散列本身不会自动消除隐私风险。

fingerprint 是系统构建指纹，通常包含产品、版本和构建标识。高基数表示字段可能出现大量不同取值；原样 fingerprint 或仅做散列都可能形成很小的设备群组，服务端应归一化字段并设置最小样本门槛。

collector 是执行采集的客户端模块。记录它的版本、丢弃计数和队列年龄，才能区分业务指标变化与采集器自身回归。

ANR 是 Application Not Responding（应用无响应），表示主线程等关键响应路径在系统规定时间内没有完成。Native 崩溃指 C/C++ 等本地代码触发的进程故障。

[`PackageManager.getInstallSourceInfo()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/PackageManager.java) 从 API 30 开始提供安装来源信息。

逐字段语义见 [`InstallSourceInfo`](https://developer.android.com/reference/android/content/pm/InstallSourceInfo)。

`installingPackageName` 是当前登记的安装器名称，可以被更改；`initiatingPackageName` 指请求安装或更新的包，来源不可用或该包已经卸载时可能为空。`originatingPackageName` 由发起安装的一方提供且未经框架验证，调用方缺少 `INSTALL_PACKAGES` 权限时无法取得。

应用还应保留编译或分包阶段写入的明确渠道字段。平台字段与自有渠道不一致时记录差异，并把结果标为待解释，避免擅自选一个字段回答“用户来自哪个市场”。

## 采集公共能力快照

Kotlin 示例用于在 Android 12 至 Android 17 上读取当前应用可见的公共信号。它不读取设备标识，也不调用隐藏 API。

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

能力快照是带采集时间的观测记录，它不代表设备具备一组永远不变的能力。省电模式、热状态、standby bucket 与后台限制都可能变化；首次启动时的值无法解释几天后的任务延迟。

standby bucket（应用待机分组）是系统根据近期使用情况给应用划分的活跃程度类别，并据此调整后台资源。热状态是 `PowerManager` 报告的设备热压力等级。存储这些整数值时还要记录 API 与采集器版本，服务端按对应版本的常量解释；读取失败或值不可用时写“未知”，不要用零代替。

示例只查询当前包，因此 `getAppStandbyBucket()` 不需要 `PACKAGE_USAGE_STATS`。服务端还需归并 `Build.MANUFACTURER` 与 `Build.MODEL` 的别名，并按隐私策略限制原始值的保存期限和访问范围。

Android 17 的 [`ActivityManager.isBackgroundRestricted()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java) 文档给出了明确语义。

返回 `true` 时，系统至少会阻止作业和闹钟执行，并在应用不处于前台时阻止其启动前台服务；这项用户施加的限制在充电时仍然有效。该值只能证明系统报告了限制状态，无法指出具体设置页面、策略模块或厂商组件。

[`UsageStatsManager.getAppStandbyBucket()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/usage/UsageStatsManager.java) 查询的是调用应用当前所在的待机分组。

系统可随时调整分组，越受限的分组通常获得越少后台运行机会。它适合解释采集时刻附近的任务等待，不能作为稳定的用户属性。

`isIgnoringBatteryOptimizations()` 只说明应用当前是否在电池优化豁免名单中。普通应用不应为了改善统计完整度而诱导用户豁免，更不能把豁免视为后台常驻承诺。

## 进程退出：用 ApplicationExitInfo 记录事实

Android 11 / API 30 引入 `ApplicationExitInfo`。

Android 17 的 [`ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java) 定义了退出原因、状态码、进程重要性、时间戳、PSS、RSS、描述和可选 trace 流。

`getHistoricalProcessExitReasons()` 返回系统仍保留的近期记录，而非一份永久、完整的退出账本。应用应在下次获得运行机会时尽早读取、限量写入本地队列并上传；记录可能被更近的退出覆盖，可选 trace 也可能为空。

代码示例按调用方给定的批量上限读取历史记录，并以复合键去重。

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

示例没有读取 trace 内容，因为 trace 的体积、I/O、脱敏和保存策略应由独立采样流程控制。ANR 进程若恢复后因其他原因退出，记录里仍可能带有较早的 ANR trace。

从 API 31 开始，Native 崩溃还可能提供 protobuf 格式的 tombstone。tombstone 是系统保存的 Native 崩溃诊断记录，protobuf 是 Protocol Buffers 的二进制编码格式。消费方必须同时检查退出原因和 trace 类型，不能把“存在 trace”直接解释为本次退出由 ANR 引起。

示例中的复合键只用于演示本地去重，也不构成设备身份。生产实现应给字段元组加版本并采用无歧义编码，例如长度前缀或规范化序列化后取摘要，避免进程名中的分隔符造成碰撞。收到上报确认后再持久化已处理标记；只保存“最大时间戳”会漏掉同一毫秒内的其他记录。

PSS 是 proportional set size（比例集大小），会把共享内存页按共享进程数折算后计入；RSS 是 resident set size（常驻集大小），统计当前驻留在物理内存中的页面，共享页会在每个进程的 RSS 中出现。`pss` 与 `rss` 的单位均为 kB，字段保存的是系统最近一次采样值，可能早于退出时刻；系统没有样本时还会返回零。两者适合辅助分组，单独一项无法证明退出由内存引起。

解释退出原因时要留意几个边界：

- `REASON_CRASH`、`REASON_CRASH_NATIVE`、`REASON_ANR`、`REASON_USER_REQUESTED`、`REASON_PACKAGE_UPDATED` 等是平台给出的分类，可作为直接信号；
- `REASON_USER_REQUESTED` 覆盖多种用户发起的停止动作，原因码本身无法区分“设置中的强行停止”和“从最近任务移除”等具体入口；
- 部分设备不支持可靠报告 `REASON_LOW_MEMORY`。先查 `ActivityManager.isLowMemoryKillReportSupported()`；不支持时，低内存终止可能只表现为 `REASON_SIGNALED` 与 `SIGKILL`；
- `REASON_FREEZER` 表示系统 freezer 相关退出。freezer 是让目标进程暂停执行的一种系统机制，该原因码不能用于命名某个厂商的后台管理功能；
- `REASON_UNKNOWN` 或一般的 `REASON_SIGNALED` 信息不足，不能自动标记为“被安全中心杀死”；
- subreason 是比公开 reason 更细的原因码，在平台源码中属于隐藏信息，普通应用不应通过反射建立依赖。

可以用 `ActivityManager.setProcessStateSummary()` 写入少量、无敏感信息的当前业务阶段，帮助下一次启动解释退出发生前的应用状态。参数最多 128 字节；系统可能限制调用频率，调用过多还可能抛出 `RuntimeException`。这份数据适合版本化的稳定枚举，不适合 UI 恢复，也不能包含 URL、搜索词、账号或自由文本。

## 缺失数据也要有语义

APM 事件中断只说明服务端没有继续收到数据。以下情况都可能产生相似表象：

- 进程正常或异常退出；
- 作业尚未获得运行机会，或者约束未满足；
- 网络不可用、服务器拒绝请求或本地队列已满；
- 用户关闭后台运行、撤回采集同意或清除应用数据；
- 用户对应用执行强行停止；在用户再次显式启动前，作业和闹钟不会恢复正常触发；
- 应用被卸载，此后不会再有“下次启动”上传退出记录。

因此，服务端应把会话结束、最近一次成功上传时刻、队列年龄和下一次启动时的退出补记放在一起看。若一直没有下次启动，系统没有提供一个让应用进程自行说明原因的机会。周期性心跳也不能改变这一点，因为它同样受进程、调度和网络条件约束。

以下 A—D 分级是本文采用的工程约定，Android API 没有定义这套等级。时间相关或群组相关只表示两个现象一起变化；要说明因果关系，还需要控制其他条件、重复实验，并找到符合 API 契约的作用机制。

| 等级 | 含义 | 可写出的结论 |
|---|---|---|
| A：平台直接信号 | 公共 API、系统回调、退出记录或明确异常 | “系统报告后台受限”“退出原因为 ANR” |
| B：时间相关 | 状态变化与问题在同一时间窗出现 | “问题与进入省电状态同时出现” |
| C：群组相关 | 某机型、版本或渠道的比率显著不同 | “该群组异常率较高，待对照实验” |
| D：用户描述 | 截图、客服反馈或复现叙述 | “用户报告开启某设置后恢复” |

A 级证据可以按字段原义陈述平台报告的事实，仍不能扩写公共 API 未提供的细节。B、C、D 级证据用于提出和筛选假设，不能改写成“该厂商会执行某策略”。

## 后台任务与前台服务怎么记录

`JobScheduler` 是 Android 平台的作业调度服务，WorkManager 是 Jetpack 提供的可延后后台工作调度库。enqueue（入队）指把任务及其约束交给调度器等待执行；worker 是 WorkManager 中实际运行任务逻辑的组件。两套接口都不承诺精确启动时刻。观察一项后台任务时，至少记录：

- enqueue、计划条件和唯一工作名称；
- 系统契约允许的最早运行条件，不写自行计算的“应当启动”时刻；
- worker 实际开始、结束、重试次数和输出状态；
- 当时的网络、充电、存储、standby bucket、后台限制与省电状态；
- WorkManager 或 JobScheduler 暴露的停止原因；
- 前台服务启动请求、异常类型、`onStartCommand()` 和 `onDestroy()` 时刻。

一个任务晚于业务期望启动，可能仍符合 API 契约。只有在同一应用构建、相同约束和受控设备设置下做对照实验，才能判断某个系统版本是否引入了额外差异。不要把固定延迟值写成某个 ROM 的默认规则。

Android 14 / API 34 起，[`JobScheduler`](https://developer.android.com/reference/android/app/job/JobScheduler) 可以返回任务仍在等待的原因。Android 17 / API 37 的 `getPendingJobReasonStats(jobId)` 进一步按原因汇总等待时长。

多个约束可能同时成立，因此各项时长相加可以超过总等待时间。这些统计不会跨设备重启保存，任务成功完成或取消时会被清空。查询不对应待执行任务的 ID 会抛出 `IllegalArgumentException`。

FGS 是 foreground service（前台服务）的常用缩写，指执行用户可感知工作并按平台规则关联通知的服务。应用要按 Android 版本处理服务类型、启动窗口和权限。记录 `ForegroundServiceStartNotAllowedException` 等公共异常，适合发布版本的线上统计；厂商日志仅作为实验室取证，不能成为应用依赖的稳定协议。

## ADPF：先协商能力，再看效果

ADPF 是 Android Dynamic Performance Framework，中文可理解为 Android 动态性能框架。它允许应用描述工作负载和性能目标，由系统结合热状态、功耗与硬件能力做调度决策。

[`PerformanceHintManager`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java) 是 ADPF 的公共入口。

hint session（性能提示会话）把一组应用线程、目标工作时长和后续实际工作时长关联起来。SoC 是 system-on-chip（片上系统），即集成 CPU、GPU 等部件的主芯片。

Android 17 源码中，`createHintSession()` 在设备不支持 hint session 或线程不属于调用应用等情况下可以返回 `null`；空线程列表、非正目标时长等错误参数会抛出 `IllegalArgumentException`。应用应按服务和 session 的实际结果协商能力，不能维护“某品牌或某 SoC 必然支持”的静态表。

一次可分析的 hint session 应记录：

- manager 是否可取得、session 是否创建成功和失败类型；
- 目标工作时长及每次上报的实际工作时长；前者表示应用希望在多久内完成，后者表示一次工作已经花费多久；
- 参与线程集合变更；
- session 对应的渲染或计算阶段；
- 同场景下的帧、CPU time、热状态、功耗代理指标和质量级别。

ADPF 是向系统表达负载意图的控制接口，API 返回值只说明能力与请求结果。体验是否改善仍要通过帧耗时、任务时长、热状态和功耗代理指标验证。若该能力不可用，应用应回到自身已有的质量分级、工作量控制和线程模型，继续记录结果；不要私自写 CPU 频率，也不要把提升线程优先级当成通用替代方案。

## ProfilingManager：请求可能不执行

[`ProfilingManager`](https://developer.android.com/reference/android/os/ProfilingManager) 从 Android 15 / API 35 开始提供面向应用的性能采样请求。profile 在这里指一份用于定位性能问题的采样产物，四种类型各自回答不同问题：

- system trace 记录进程、线程、调度、CPU 运行和系统或应用事件的时间关系，适合分析延迟与卡顿；
- Java heap dump 保存某一时刻 Java 堆中的对象及引用关系，适合查找重复对象和内存泄漏；
- heap profile 在发生内存分配时抽样并关联调用位置，适合观察分配热点和内存抖动；
- stack sampling 按固定频率抽取正在 CPU 上运行的调用栈，适合定位 CPU 热点和代码执行路径。

系统 trace、heap profile 与 stack sampling 是持续一段时间的采集，开始请求和实际开始采集之间可能有延迟；Java heap dump 更接近时点快照。请求会受频率限制，也不保证执行。调用 `requestProfiling()` 时必须成对提供 executor 与 listener，或者事先注册成对的全局 executor 与 listener；两处都没有有效组合时，请求会被丢弃且没有回调。

executor 决定在哪个执行环境处理回调，listener 接收 `ProfilingResult`。结果写入请求应用的数据目录，经过脱敏，只包含请求进程的特定信息，不能借此读取其他进程的任意内容。

Android 16 / API 36 增加 `ProfilingTrigger`。Android 17 / API 37 又增加异常行为、应用兼容问题、冷启动、因 CPU 使用过多而终止及 OOM 等触发类型。OOM 是 Out of Memory，指内存不足异常。

具体常量按 [`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger) 和 [Android 17 功能说明](https://developer.android.com/about/versions/17/features) 适配，不能从主线源码预览推定发布版本行为。

系统触发的结果只投递给 `registerForAllProfilingResults()` 注册的全局 listener。它按 UID 生效；UID 是系统为应用分配的 Linux 用户标识。系统触发同样可能受限而没有产物，进程在采集期间被杀后，系统也可能在应用重新注册全局 listener 时尝试再次投递。

“请求没有结果”应保留为未知状态。可能原因包括版本不支持、参数错误、缺少有效回调组合、频率限制、系统资源状态、进程生命周期或实现问题。应用需要记录请求类型、请求时刻、回调结果和超时状态，再在目标设备上复现。

API 35 以下没有 ProfilingManager，可使用适合该版本的公共指标、Android Studio、Perfetto 或 Simpleperf 完成实验室诊断。Perfetto 用于记录和查询系统 trace，Simpleperf 用于采样 CPU 性能数据。

读取受保护的 ftrace 内核跟踪节点或通过 hook 拦截平台私有实现，不能包装成线上降级方案。hook 在这里指替换或截获函数调用的非公开做法。Android 17 上 profile 的查询与脱敏边界可参考官方的 [ProfilingManager profile 查询说明](https://developer.android.com/topic/performance/tracing/profiling-manager/querying-profiles)。

## 帧、CPU 与系统状态

`FrameMetrics` 提供窗口帧各阶段的耗时字段，AndroidX JankStats 在兼容不同 Android 版本的同时标记卡顿帧，`Choreographer` 则按显示垂直同步节奏安排应用回调。三者和应用内 trace 都只能观察各自覆盖的事件，不会自动给出厂商策略的原因。

进入省电、热限制或刷新率切换后，帧节奏和预算可能变化，所以事件旁边要记录显示模式、刷新率、热状态和省电状态。没有公开证据表明某品牌会系统性修改 `FrameMetrics` 的“精度”，采样差异不能直接写成厂商结论。

CPU time 表示进程或线程实际占用处理器运行的累计时间。`ProcessCpuTracker` 属于 framework 内部实现，第三方应用没有受支持的公共 API 契约。线上应用可使用：

- `Process.getElapsedCpuTime()` 观察本进程累计 CPU time；
- `/proc/self/stat` 或 `/proc/self/task/<tid>/stat` 读取当前进程可见计数，并按内核时钟频率换算；`/proc` 是内核暴露运行状态的伪文件系统，内容由内核动态生成，磁盘不会持久保存；
- ProfilingManager、Perfetto 或 Simpleperf 在各自允许的环境中做采样分析。

`/proc` 可见性、字段解析和采样开销应按 [26.20](20-proc-filesystem-cpu-monitoring.md) 的边界处理。某个节点不可读时记录能力缺失，不要通过扩大权限或扫描其他进程规避。

## 渠道性能比较如何避免误判

渠道通常和厂商、型号、地区、系统版本、应用产物、ABI、签名、安装时间及用户群一起变化。与渠道同时变化、又会影响性能结果的因素称为混杂因素。直接比较“渠道 A 平均启动时长”和“渠道 B 平均启动时长”，很容易把设备结构差异误写成安装市场影响。

实验室比较应满足这些条件：

- 使用同一源码和等价构建参数，记录 base APK、split APK、签名与 Native 库摘要；split APK 是按 ABI、语言或功能等条件拆出的安装分包；
- 明确安装方式、首次安装或覆盖安装、应用数据状态和编译状态；
- 在相同设备与系统镜像上交叉安装，重复冷启动和热启动；
- 记录 ABI、page size、存储余量、温度、充电状态和网络条件；ABI 是应用二进制与处理器约定的接口，page size 是系统管理虚拟内存的基本页大小；
- 把安装完成到首次启动的系统日志作为辅助证据。

线上分析则按应用版本、产物摘要、API、厂商、型号、系统构建、ABI、page size、地区、安装来源和明确渠道分层，并报告样本量、分位数和置信区间。置信区间给出统计估计在既定假设下的不确定范围，不能消除样本偏差。

跨群组比较时，可用匹配让两组样本在已知特征上更接近，或用回归模型估计并控制这些特征的影响。没有记录或无法建模的差异属于未观测混杂，结论中要明确保留这一限制。

dexopt 是 Android 对 dex 字节码进行校验、优化或编译的一组处理。启动变慢不能直接推出“应用商店没有执行 dexopt”，启动变快也不能证明市场执行了预优化。验证编译因素时，要在受控设备上检查 package 编译状态、安装会话和用于编译决策的运行时 profile，并保持 APK 与数据状态一致。

## 厂商安全中心与用户引导

不要把“加入白名单”设计成所有用户第一次启动时的必做步骤。更合适的触发条件是：

1. 公共 API 已显示后台受限，或多次任务记录显示约束满足后仍未运行；
2. 该功能依赖及时后台执行，延迟会给用户带来可解释的影响；
3. 当前机型和系统版本的页面路径经过验证；
4. UI 说明用户将改变什么设置、可能增加什么耗电，以及如何恢复。

Intent 是 Android 用于描述要执行的操作及目标数据的消息对象。设置页面和厂商说明会变化，应用应使用当前官方文档和受支持的 Intent；打开失败时停留在系统通用设置，不要扫描已安装包寻找安全中心，也不要为监控申请与功能无关的广泛权限。

“白名单”是用户和厂商文档中常见的统称，各设备上的实际开关可能分别控制电池优化、后台启动或任务清理，没有统一公共 API 语义。

所谓“厂商行为库”应保存证据，传闻不进入结论。每条记录至少包含机型、系统构建、应用构建、复现步骤、观察信号、对照组、证据等级和失效日期。系统升级后重新验证，不能沿用旧 ROM 结论。

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

符号化是把混淆后的类名或机器地址还原为可定位的源码位置。R8 mapping 用于还原 Java/Kotlin 混淆名称，Native symbol 用于解析 Native 地址，build ID 则把崩溃事件与生成该二进制的符号文件对应起来；三者都必须和具体构建严格配对。动态特性指按需交付的 dynamic feature 模块，也需要登记所属分包与构建标识。

Tinker 是热修复框架，职责是下发代码补丁，与持续采集和分析性能信号的 APM 范围不同。厂商控制台或应用市场若提供性能报告，也要确认它覆盖哪些安装、设备和采样人群，再决定它能否补充自建数据。

## 排障顺序

遇到“某渠道、某 ROM 数据少或性能差”时，可以按以下顺序推进：

1. 核对事件 schema、采样、限流、队列和服务端接收，排除采集器回归。
2. 核对应用构建、签名、split、ABI、安装来源和明确渠道，确认比较对象。
3. 查看后台限制、standby bucket、省电、热状态、网络与任务生命周期。
4. 在下次启动补记 `ApplicationExitInfo`，区分已知退出与未知中断。
5. 按机型、系统构建和应用版本分群，检查样本量与置信区间。
6. 用同一设备、同一产物和受控状态复现，并保存系统 trace 或 profiler 证据。
7. 只有在直接证据支持时，才形成厂商或系统版本级结论，并设置复验日期。

这套顺序要求每个判断都能回到记录、API 契约或可重复实验。非 Play 可观测性的难点在于明确数据覆盖范围，以及每个归因所依据的证据等级。
