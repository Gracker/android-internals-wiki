---
title: "Android 17 Excessive CPU Kill 与后台任务功耗治理"
chapter: "25.12"
section: "25.12"
status: ready-for-review
drafted_date: "2026-05-20"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
last_verified: "2026-05-20"
last_verified_against: "Android Developers ProfilingManager / ProfilingTrigger docs, AOSP packages/modules/Profiling, DeepResearch 2026-05-19/2026-05-20, Clippings structure references"
confidence: medium
tags: [android-17, profiling-trigger, jobscheduler, workmanager, power, background-task]
related_chapters: ["5.10", "25.2", "25.4", "26.12", "11.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "研究素材/官方文档/章节深挖"
gap_score: 18
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-19-android-jobscheduler-profilingtrigger-version-boundary.md"
  - type: research
    path: "/Users/gracker/.openclaw/workspace/AutoResearchClaw/state/researched-gaps.json"
  - type: internal
    path: "src/part5-app/ch26-observability/12-versioned-diagnostics.md"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
---

# 25.12 Android 17 Excessive CPU Kill 与后台任务功耗治理

<!-- outline-start -->
## 要点

### 🔹 Android 17 excessive CPU trigger 的能力边界
说明 `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 解决的问题、返回物形态、与 `ProfilingManager` / `ProfilingTrigger` 的关系，并明确它不能替代 App 自己的后台任务治理。

### 🔹 与 JobScheduler quota 的关系
区分 JobScheduler / WorkManager 的配额、约束和调度延迟，与系统对异常 CPU 占用的终止与采样机制。重点说明两者可能观察同一类后台任务，但控制路径不同。

### 🔹 App 侧高 CPU 后台任务的常见成因
覆盖周期任务过密、链式 Work 堆积、重试风暴、日志压缩上传、数据库 vacuum / migration、图片转码、加密压缩、热循环轮询等场景。

### 🔹 线上证据采集与归因字段
设计后台任务 CPU 异常的证据包字段：work id、job id、uid、processName、threadName、triggerType、trace file、start reason、exit reason、battery state、network state、standby bucket。

### 🔹 治理策略：约束、合并、退避和熔断
按任务可延后程度设置约束，给出唯一任务、指数退避、失败隔离、分片执行、前台可见任务切换、远程开关和采样上限的实战策略。

### 🔹 Android 15-17 的版本化降级路径
Android 15 以前主要依赖 App 自建监控和 `ApplicationExitInfo`；Android 15+ 可结合 `ProfilingManager` 主动采集；Android 17 使用 trigger 结果做事后归因。需要列出低版本 fallback。

## 扩展

### 🔸 与 26.12 线上诊断能力的关系
26.12 负责讲版本化诊断 API；本节只讲后台任务功耗治理场景，避免重复解释 `ProfilingManager` 基础 API。

### 🔸 与 5.10 系统调度机制的关系
5.10 讲 JobScheduler / WorkManager 调度机制；本节讲 App 因后台 CPU 异常被系统采样或终止时如何定位和治理。

### 🔸 待验证阈值与厂商差异
记录 excessive CPU 触发阈值、kill signal、厂商自定义策略、实机触发条件等需要补充 trace 或源码证据的边界。

<!-- outline-end -->

## 本节处理的问题

Android 17 的 `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 给后台 CPU 异常多了一个系统侧证据入口。它适合回答“进程被系统处置前后有没有 profiling 结果”，不适合替 App 判断“哪个后台任务该不该跑”。

后台任务功耗治理仍要回到业务任务本身：任务是否由用户刚刚触发，是否能延后，是否能合并，失败后是否会重试到失控。§5.10 讲 JobScheduler / WorkManager 的调度机制，§25.2 讲后台功耗治理框架，§25.4 讲 WorkManager 实战；本节只处理一种更窄的场景：后台任务已经跑起来，并且 CPU 占用高到触发系统采样或终止。

[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]
[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]
[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]

## Android 17 excessive CPU trigger 的能力边界

`ProfilingManager` 从 Android 15 开始提供应用驱动的 profiling 采集，Android 16 起扩展出系统事件触发采集。以 §26.12 已复核的版本口径，Android 17 / API 37 新增的 trigger 包含 `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`，用于系统因过量 CPU 使用处置进程后的取证。应用注册 trigger 后，结果通过 `registerForAllProfilingResults()` 的全局 listener 接收，归档层读取 `ProfilingResult#getTriggerType()`、`getTag()`、`getResultFilePath()`、`getErrorCode()` 和 `getErrorMessage()`。详见 26.12 节。 [已验证: src/part5-app/ch26-observability/12-versioned-diagnostics.md; developer.android.com/reference/android/os/ProfilingTrigger]

这个 trigger 的产物应按“事后证据”处理。公开资料能支撑的是 trigger 类型、结果回调和 profiling 文件归档方式；触发阈值、持续时间、kill signal、厂商是否调整策略，目前仍缺少稳定公开口径。正文不能写成固定的 “5 分钟检查一次”“CPU 超过某个百分比必杀” 这类规则。 [待验证: excessive CPU 触发阈值、kill signal、厂商配置]

App 侧接入时，最小处理流程是三步：注册 trigger，监听 profiling 结果，把结果文件和后台任务证据绑定到同一个 case。注册动作本身不会降低 CPU，也不会阻止系统终止进程；它只让 App 在事后多拿到一份系统保存的现场材料。 [已验证: Android Developers ProfilingManager / ProfilingTrigger docs]

## 与 JobScheduler quota 的关系

JobScheduler quota 回答“这个 UID 现在还能不能继续运行后台 job”。它看的是 bucket、约束、执行历史、系统状态和 quota 预算。excessive CPU trigger 回答“系统已经观察到过量 CPU 使用，并为这次事件保存了 profiling 结果”。两者会落在同一个后台任务上，但控制路径不同。

| 维度 | JobScheduler / WorkManager quota | `KILL_EXCESSIVE_CPU_USAGE` trigger |
|------|----------------------------------|------------------------------------|
| 处理阶段 | 任务启动前和运行中调度 | 系统观察到异常 CPU 使用并处置前后 |
| 决策对象 | job / work 是否有执行资格 | 进程 / UID 的 CPU 异常事件 |
| App 可控项 | 约束、unique work、退避、任务粒度、是否 expedited | trigger 注册、结果 listener、证据归档和限流 |
| 典型证据 | `dumpsys jobscheduler`、pending reason、WorkInfo stop reason | `ProfilingResult`、trace file、`ApplicationExitInfo` |
| 常见误判 | 把 quota 耗尽当成 Worker 代码 bug | 把系统取证当成调度策略本身 |

一个后台日志上传 Worker 如果因为 network constraint 长期 pending，这是 quota / 约束问题；如果它在可运行窗口内做全量压缩、加密和上传，CPU 长时间跑满后被系统处置，这才进入 excessive CPU trigger 的排查范围。§5.10 负责解释 quota 和 pending reason，本节只在任务已经消耗 CPU 后接手。 [已验证: src/part1-fundamentals/ch05-cpu-power/10-jobscheduler-workmanager-performance.md]

## App 侧高 CPU 后台任务的常见成因

Clippings 的 CPU 优化章节把问题拆成线程池、CPU 闲时利用、等待锁 / IO 和线程优先级。迁移到后台任务场景，问题通常不在某个 API 名字，而在任务模型失控。

- 周期任务过密：多个 15 分钟 periodic work 同时存在，每个业务各跑一套同步，设备刚满足约束就集中执行。
- 链式 Work 堆积：压缩、加密、上传、清理被拆成很多节点，前置失败后后续节点反复重入，WorkManager 数据库和调度队列一起膨胀。
- 重试风暴：网络失败、服务端 5xx、鉴权失败都按同一种 retry 处理，短窗口内不断重新执行 CPU 和网络准备工作。
- 日志压缩上传：后台一次性扫描全量日志、压缩、计算摘要、加密，再上传。单次任务看似合理，CPU 时间窗口过长。
- 数据库维护：migration、vacuum、索引重建、离线数据重算被放进后台任务，用户离开后继续运行。
- 图片 / 视频转码：用户退出页面后仍保留批量转码队列，没有按前台可见度降级或暂停。
- 热循环轮询：为了等某个远端状态或本地文件出现，用短 sleep + 轮询维持线程运行。
- 线程池配置错误：CPU 型任务进了无限 IO 线程池，或者 IO 型任务堵在 CPU 线程池，造成调度开销、锁等待和上下文切换一起上升。

这些成因有一个共同特征：系统只能看到 CPU 被消耗，无法知道这次消耗有没有业务价值。App 必须在任务平台里保存任务类型、触发来源、用户可见度、重试次数和 owner，否则 trace 里只会留下线程名和调用栈，值班同学仍要猜业务来源。

## 线上证据采集与归因字段

excessive CPU 事件的证据包要把三类材料放在一起：系统退出记录、profiling 结果、App 任务上下文。只保留 trace 文件不够；没有 work id、job id、业务 owner 和重试次数，trace 很难回到具体任务配置。

| 字段 | 来源 | 用途 |
|------|------|------|
| `caseId` / `sessionId` | App 归档层 | 合并日志、trace、退出记录和用户反馈 |
| `uid` / `pid` / `processName` | App + `ApplicationExitInfo` | 区分主进程、worker 进程和 SDK 进程 |
| `workId` / `workName` / `tags` | WorkManager | 定位具体 Worker 和业务 owner |
| `jobId` | JobScheduler / WorkManager 映射 | 回查 `dumpsys jobscheduler` 与 pending reason |
| `triggerType` / `profilingType` / `tag` | `ProfilingResult` | 确认是否来自 `KILL_EXCESSIVE_CPU_USAGE` |
| `resultFilePath` / `fileSha256` / `fileSize` | `ProfilingResult` + 归档层 | 上传去重和完整性校验 |
| `exitReason` / `status` / `timestamp` | `ApplicationExitInfo` | 判断是否是系统资源处置、ANR、低内存或用户关闭 |
| `startReason` / `foregroundState` | App 自建埋点 | 区分用户触发、定时触发、进程启动恢复 |
| `standbyBucket` | `UsageStatsManager` | 解释 quota 变化和后台执行资格 |
| `batteryState` / `charging` / `thermalStatus` | App + 系统接口 | 解释高 CPU 是否伴随低电量、充电、热限频 |
| `networkState` / `metered` | App + Connectivity | 判断上传、重试和弱网是否相关 |
| `retryCount` / `backoffMs` / `chainDepth` | 任务平台 | 识别重试风暴和链式堆积 |
| `cpuTimeMs` / `threadSamples` | 自建采样 + profiling trace | 与 trace 中的热点线程互相校验 |

`ApplicationExitInfo` 从 Android 11 起可用，适合在下次启动补退出原因；`ProfilingManager` / `ProfilingTrigger` 适合补系统采样文件。两者要按时间戳和 pid 做近邻合并，不要只按进程名合并，同名进程在短时间内可能多次重启。 [已验证: src/part5-app/ch26-observability/12-versioned-diagnostics.md]

## 治理策略：约束、合并、退避和熔断

后台 CPU 治理的目标不是把所有任务都延后，而是把任务放到合适的用户可见度和资源预算里。用户刚点击的上传可以争取 expedited / UIDT / 前台服务；周期同步、日志清理、缓存预热要接受系统选择窗口；纯保活和短轮询应删除。

- 约束：日志压缩、缓存清理、数据库维护优先加 `requiresCharging`、`requiresBatteryNotLow`、`requiresDeviceIdle` 或网络约束，避免在低电量和弱网下消耗 CPU。
- 合并：同类后台任务使用 `enqueueUniqueWork()` / `enqueueUniquePeriodicWork()`，用业务 key 去重，避免每次启动重复入队。
- 退避：网络失败、服务端错误和本地资源不足要分开处理；服务端 5xx 走指数退避，鉴权失败直接停止并等待新 token。
- 熔断：同一 tag 在短窗口内连续失败或 CPU 时间超过预算时暂停该类任务，远程开关降采样或停用。
- 分片：大文件压缩、数据库迁移和图片转码拆成可中断小片，每片结束检查约束、取消信号和剩余预算。
- 前台切换：用户正在等待结果的任务转为用户可见路径，给通知、取消入口和超时；用户离开后降级为普通后台任务。
- 采样上限：profiling 和自建 CPU 采样都要按用户、case、版本和设备限流，避免问题越多采集越重。

下面的 WorkManager 片段展示一个可延后日志上传任务。读者重点看三处：唯一任务、约束、指数退避。

```kotlin
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .setRequiresBatteryNotLow(true)
    .build()

val request = OneTimeWorkRequestBuilder<LogUploadWorker>()
    .setConstraints(constraints)
    .setBackoffCriteria(
        BackoffPolicy.EXPONENTIAL,
        30,
        TimeUnit.SECONDS,
    )
    .addTag("log_upload")
    .build()

WorkManager.getInstance(context).enqueueUniqueWork(
    "log_upload_${accountId}",
    ExistingWorkPolicy.KEEP,
    request,
)
```

`KEEP` 会保留已经排队或运行中的同名任务，适合避免重复上传；如果业务要求新日志覆盖旧任务，可以改成 `REPLACE`，但要同步记录被替换任务的取消原因。约束和退避不负责“保证立刻上传”，它们负责把上传放到更低成本的窗口，并在失败时压住重试频率。 [已验证: Android Developers WorkManager docs; src/part5-app/ch25-power-size/04-workmanager-practice.md]

## Android 11-17 的版本化降级路径

| 系统版本 | 可用能力 | 后台 CPU 异常处理方式 |
|----------|----------|----------------------|
| Android 10 及更早 | 自建日志、bug report、线下 Perfetto | 只能靠 App 任务平台记录 work / job / 线程 / CPU 采样；线上系统证据弱 |
| Android 11-14 | `ApplicationExitInfo` | 下次启动补退出 reason、timestamp、PSS / RSS；CPU 细节仍靠自建采样和线下 trace |
| Android 15 | `ProfilingManager#requestProfiling()` | 灰度或用户授权场景主动采集 system trace / stack sampling，适合少量设备定向排查 |
| Android 16 | `ProfilingTrigger` 事件触发能力扩展 | 可注册系统事件触发采集；结果经全局 listener 归档，版本和 Extension 要单独记录 |
| Android 17 | `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` | 系统因过量 CPU 使用处置进程后，结合 trigger 结果、退出记录和任务上下文归因 |

低版本 fallback 不应伪装成同等能力。Android 11-14 能拿到退出记录，但拿不到 Android 17 的 excessive CPU trigger 结果；Android 15 能主动请求 profiling，但不能等价替代系统事件触发。归档表里要保留 `apiLevel`、`extensionVersion` 和 `diagnosticCapability`，否则同一类 case 在不同设备上会被误读成“有的设备没问题”。

## 与 26.12 线上诊断能力的关系

26.12 讲 API 边界和证据归档，本节只讲后台任务 CPU 异常。这里不重复 `ProfilingManager` 的请求类型、结果回调和 rate limiter 细节，只引用它作为证据入口。

工程实现上，26.12 的证据表可以增加一个 `backgroundTask` 子对象：`workId`、`jobId`、`workName`、`tags`、`retryCount`、`chainDepth`、`owner`、`cpuBudgetMs`、`stopReason`。这样同一个 profiling result 既能进入线上诊断系统，也能回到后台任务平台做治理。

## 与 5.10 系统调度机制的关系

5.10 解释 JobScheduler / WorkManager 的系统调度：约束、bucket、quota、pending reason、Expedited Job 和 WorkManager 调度器选择。本节不再展开这些机制，只补一条实战边界：quota 不等于 CPU 异常。

排查时按这个顺序看更稳：任务没跑，查 5.10 的 pending reason 和 quota；任务跑了但被停止，查 WorkInfo / JobParameters stop reason；进程被系统处置或有 profiling 结果，再进入本节的 excessive CPU 证据包。这样可以避免把“调度延迟”“任务超时”“CPU 异常 kill”混成同一种问题。

## 待验证阈值与厂商差异

当前公开资料还不足以写死 Android 17 excessive CPU 的阈值和处置路径。需要保留以下验证项：

- 触发阈值：CPU 百分比、持续时间、是否区分 cached / background / foreground service 状态。 [待验证]
- 处置信号：进程收到 SIGKILL、SIGTERM，还是经 ActivityManager 的应用进程清理路径。 [待验证]
- 产物形态：trace 文件名、profiling type、buffer 时长、是否所有设备都返回 `resultFilePath`。 [待验证]
- 厂商策略：不同 SoC、温控策略、系统电量模式下是否调整阈值。 [待验证]
- WorkManager 映射：系统处置时，WorkManager 是否能稳定记录 stop reason，是否需要下次启动补偿。 [待验证]

验证实验可以从一个 cached 进程 CPU hog 开始：注册 trigger，启动带唯一 tag 的后台 Worker，让 Worker 在可控时间窗口内执行 CPU 密集循环，同时记录 `/proc/<pid>/task/*/stat`、logcat、`dumpsys jobscheduler`、`ApplicationExitInfo` 和 profiling result。实验结果要按设备、系统版本、API level、Extension 版本和电量模式分组，不能把单台设备结果写成通用规则。

## 小结

`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 的价值在取证，不在治理。后台 CPU 异常的治理仍由 App 完成：任务分层、唯一任务、合理约束、指数退避、分片执行、远程熔断和证据归档。系统 trigger 能补一份现场，但只有把它和 work id、job id、重试次数、bucket、退出 reason 绑定起来，才能从“知道进程被处置”走到“知道该改哪个后台任务”。

## 延伸阅读


### ProfilingManager Excessive CPU Trigger 版本边界验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-03-android17-profilingmanager-excessive-cpu-version-boundary.md
- 类型：DeepResearch 调研结果
- 摘要：TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE 在 AOSP android-17.0.0_r1 中无公开稳定锚点，应降级为待验证。SUBREASON_EXCESSIVE_CPU=7 从 API 30 已存在。JobScheduler quota 与 AMS excessive CPU kill 属不同路径，可同时作用。版本边界清晰区分了已验证和未验证项。
- 注入时间：2026-06-04
- 价值：关键的版本边界验证，将缺乏一手源码支撑的结论降级为待验证，防止章节写入未确认信息
### ProfilingManager 企业环境隐私合规策略
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-04-profilingmanager-enterprise-privacy.md
- 类型：DeepResearch 调研结果
- 摘要：ProfilingManager API 35+ 的 rate limiter 机制和企业 MDM 合规分析。需 MANAGE_PROFILING（signature|privileged）权限，采集数据仅含 CPU 时间片和堆栈采样，不含内存内容。企业场景下存在并发数限制、时长限制和数据导出控制，与 Android Vitals 通过 statsd 集成。
- 注入时间：2026-06-04
- 价值：补充了 ProfilingManager 企业环境 rate limiter、权限门控和 Vitals 集成路径，对理解 excessive CPU kill 的 profiling 数据流有直接帮助
### Android 17 TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE 机制边界验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-24-android17-trIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE-mechanism.md
- 类型：DeepResearch 调研结果
- 摘要：确认 Android 17 引入 TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE（API 37，targetSdk>=37），但 excessive CPU 检测服务、阈值、kill 路径等关键细节仍缺 AOSP 源码闭环。targetSdk gating 条件已修正（非 API 36）。与 JobScheduler quota 的关联尚无直接证据。
- 注入时间：2026-05-25
- 价值：补充 targetSdk gating 条件修正和官方文档层面的确认，标注待验证源码路径



<!-- AIW-源码调研-2026-05-26 -->
## 源码调研补充（2026-05-26）

**来源**：DeepResearch/2026-05-26-android17-excessive-cpu-kill-mechanism-boundary.md

**核心验证结论**：

1. **TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE 确认存在于 API 37（Android 17），触发前提包含 targetSdk >= 37**。该 trigger 非预防机制，是系统处置进程后的事后取证入口。

2. **ProfilingResult 产物**：triggerType、tag、resultFilePath、errorCode、errorMessage。应用通过 `registerForAllProfilingResults()` 全局 listener 接收。

3. **关键源码位置**：Perfetto trigger.proto（`external/perfetto/protos/perfetto/trace/trigger.proto`）、ProfilingTrigger.java、ProfilingManager.java。

4. **与 JobScheduler quota 关系**：两者控制路径独立——quota 管"能跑多久"，trigger 管"被处置时的现场"。AOSP 源码未发现直接关联路径。

5. **标注待验证**：触发阈值、kill signal、检测服务（PowerManagerService/ProcessList）、trace buffer 时长、厂商差异——均缺 AOSP 源码闭环，建议保持"待验证"标注。

### Android 17 Excessive CPU Kill 机制边界验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-26-android17-excessive-cpu-kill-mechanism-boundary.md
- 类型：DeepResearch 调研结果
- 摘要：TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE 是事后取证机制非预防性治理。确认存在于 API 37 非 36；targetSdk>=37 触发前提；JobScheduler quota 与 trigger 无直接源码关联。含 Perfetto trigger.proto、ProfilingTrigger.java 源码位置。
- 注入时间：2026-05-27
- 价值：明确 Android 17 Excessive CPU Kill 为取证机制而非预防机制，纠正章节可能存在的误解

<!-- AIW-源码调研-2026-06-04 -->
## 源码调研补充（2026-06-04）

**来源**：DeepResearch/2026-06-04-profilingmanager-enterprise-privacy.md

**核心验证结论**：

1. **ProfilingManager 公共 API 自 Android 15 / API 35 开始提供**，需 `android.permission.MANAGE_PROFILING` 权限（signature|privileged 级别，普通 App 无法获取）

2. **Rate limiter 机制属厂商私有实现**。AOSP 层面仅通过 `ProcessRecord.profilingInfo` 锁控制单个进程同一时间只允许一个 profiling 会话。频率上限（如每小时最多 N 次）、具体阈值属于厂商差异化配置，非 AOSP 公共接口。

3. **ProfilingManager 采集数据符合隐私最小化原则**：仅含采样指标（CPU 时间片、堆栈采样、Binder 调用统计），**不含**进程内存内容、文件内容、网络 payload。这为企业隐私合规（GDRP 等）提供基础。

4. **Android 17 TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE（API 37）新增**。但 android-17.0.0_r1 源码仍无法访问（404），结论基于合理推断，应保持"待验证"标注。

5. **与 Android Vitals 集成路径**：`ProfilingManager` → `/data/misc/profiles/` → `statsd`（定期扫描）→ `ProfileStore` → Play Console Android Vitals。

6. **企业场景特殊约束**：在 device owner / profile owner 场景下，profiling 数据保留期、数据导出能力受 MDM 策略控制，`ProfileData#isExportable()` 出厂默认 false。

**关键源码**：
- `android-16.0.0_r3:frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`（profileControl 锁机制，一手验证）
- Android Developers: ProfilingManager reference（公共 API 验证，一手）

**待验证**：android-17.0.07 ProfilingManager.java 精确源码、Rate limiter 具体阈值（厂商私有）、ProfilingTrigger callback 线程模型

