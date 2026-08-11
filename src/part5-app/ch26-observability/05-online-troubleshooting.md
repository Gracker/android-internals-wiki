---
title: "线上问题排查方法论"
chapter: "26.5"
section: "26.5"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37) (API 36 / 36.1)"
last_verified: "2026-08-06"
last_verified_against: "Android Developers / AOSP android-17.0.0_r1 docs / Firebase docs / Play Console docs / Clippings structure references; cross-checked with 26.10 versioned diagnostics"
confidence: medium-high
drafted_date: "2026-05-15"
polish_count: 1
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md"
  - type: official
    path: "https://developer.android.com/privacy-and-security/risks/log-info-disclosure"
  - type: official
    path: "https://source.android.com/docs/core/tests/debug/understanding-logging"
  - type: official
    path: "https://developer.android.com/studio/debug/bug-report"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/on-device"
  - type: official
    path: "https://developer.android.com/tools/perfetto"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://firebase.google.com/docs/crashlytics/android/customize-crash-reports"
  - type: official
    path: "https://firebase.google.com/docs/remote-config/rollouts/about"
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/6346149"
tags: [troubleshooting, remote-logging, user-feedback, online-trace]
related_chapters: ["26.1", "15.5", "13.2"]
pipeline_stage: "ready-for-review"
task6_state: "pending-review"
task9_state: "pending-review"
task6_review_notes: '2026-06-04 task6 re-review (round 2): pass-light-edit. L1/L2 clean. Fixed frontmatter formatting (leading blank lines). All 4 anchors + 1 extension covered. task9_result=auto-fixed. Score: structure 4/5, wording 4/5, consistency 4/5, verification 4/5, metadata 4/5.'
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-05-15T03:11:00+08:00"
last_task6_review_log: logs/review/2026-06-04-20-review.md
last_task6_at: "2026-06-04T20:15:00+08:00"
reviewed_date: "2026-08-05"
reviewed_by: hermes-aiw-review-finalize-apply
task6_result: pass-light-edit
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-04"
last_task9_at: "2026-06-04T09:20:00+08:00"
last_task9_review_log: logs/deep-review/2026-06-04-09-deep-review.md
task2b_result: fixed
last_task9_autofix_at: "2026-06-04"
task9_review_notes: "2026-06-04 Task9 auto-fix: clarified ProfilingTrigger API 36 vs version 36.1 boundary for APP_REQUEST_RUNNING_TRACE."
deepseek_cn_review_state: structure-reworked
last_deepseek_cn_review_at: 2026-06-12
task2b_state: fixed
last_task2b_verifier_at: "2026-06-14T11:25:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-06-14-11-task2b-verifier.md"
last_rework_at: "2026-08-06T09:37:37+08:00"
last_rework_run_id: "20260806-093722-rework-e80242a0"
last_rework_log: "logs/rework/2026-08-06-20260806-093722-rework-e80242a0-rework.md"
rework_result: "verification-marker-cleared"
rework_notes: "2026-08-06 rework: cleared stale verification quality flag by removing review-marker wording from the evidence-template guidance; returned chapter to ready-for-review so task6/task9 can re-check the bounded edit."
last_review_finalize_at: "2026-08-05T22:06:15+08:00"
last_review_finalize_run_id: "20260805-220526-b99bf55c"
review_finalize_notes: "2026-08-05 review-finalize: verified structure, Android 10-17/API 29-37 version boundaries, remote logging/privacy, bug report/Crashlytics, ProfilingManager/ProfilingTrigger, Play staged rollout, Remote Config rollout, Android vitals, and StatsD ordinary-app permission boundary; no Android 18/API 38+ claims found. Promoted to finalized."
---

# 26.5 线上问题排查方法论

## 线上问题排查流程

线上排障处理的是复现概率低、现场容易丢、影响面会变化的问题。排障效率取决于三件事：事发前有没有埋好证据，事发时能不能把证据按用户、版本、设备和时间聚到一起，事发后能不能把风险限制在小范围内。

26.1 节已经定义 Metrics、Logs、Traces 的分工，15.5 节已经覆盖线上性能监控，13.2 节已经说明 Perfetto 抓取方式。排障实战落在四个动作上：接到反馈后拿证据、复现问题、打开临时日志或诊断开关、用灰度环境缩小问题范围。

平台能力上界为 Android 17 / API 37 / `android-17.0.0_r1`。远程日志、用户反馈与灰度控制属于应用架构；`ApplicationExitInfo`、`ProfilingManager` 和 StatsD 的版本与权限结论按 Android 17 复核。相关结论不依赖内核专有实现，因此不附加 Android 17 kernel tag。

一次线上事件可以按以下顺序推进：

1. 建立事件编号，记录用户可见现象、首次发生时间、影响版本和当前影响面。
2. 先做安全处置：暂停扩大灰度，必要时关闭可疑功能；保留已知证据，避免重启服务或清缓存后现场消失。
3. 建立按单调时间或可校准墙上时间排序的时间线，把客户端日志、服务端 traceId、Crash / ANR、配置变更和发布记录关联起来。
4. 明确证据缺口，再选择动态日志、端侧 profiling、用户协助 bug report 或测试环境复现。采集动作本身也要限时、限量并可撤销。
5. 修复或隔离后，用相同分桶和用户路径验证指标恢复；记录哪些证据支持结论，哪些只是相关性。

## 远程日志与动态日志级别

远程日志的目标是在用户无须安装临时包的前提下，把一次会话的必要现场留下来。线上设备仍然是用户设备，不能按远程开发机处理。日志系统至少要回答四个问题：这是谁的设备、发生在哪个版本、当时走过哪些业务步骤、失败点附近有哪些系统状态。

一套可用的远程日志方案通常分成四层：

- **本地写入层**：把应用自有日志写入 App 私有目录，按时间、字节和会话滚动，设置总容量与保留期限。多进程 App 可按进程分文件，上传前再按单调时间和进程名合并，避免多个进程竞争同一个文件。
- **采样与开关层**：发布版保留满足日常诊断所需的低成本事件；对目标用户、机型、版本或实验组临时增加字段与采样。`log.tag.<TAG>` / `Log.isLoggable()` 更适合 adb、系统组件和本地调试，普通线上 App 应使用自己的类型化配置，不能把远端字符串直接解释成系统属性或任意命令。
- **隐私与合规层**：密码、验证码、完整 token、支付凭据、输入文本和联系人内容不得进入日志。关联请求应使用服务端生成的随机 ID 或经过密钥保护的令牌化标识；简单 hash 仍可能被枚举，不等于匿名化。字段要在产生处分类，在写盘与上传两处校验，私有目录也不能成为采集敏感数据的理由。
- **拉取与主动上报层**：用户同意反馈、Crash、ANR 或严重业务失败可以触发受控上报。远程诊断任务必须使用有限动作集合，并携带目标范围、配置版本、过期时间、重放保护、总字节上限和网络条件；禁止下发 shell、任意反射调用或任意文件路径。

Xlog、Logan、Holmes 分别代表三种思路：高性能本地日志、统一日志平台、动态补充执行路径。普通团队可以先做小版本：会话 ID、请求 ID、页面路径、关键业务状态、错误码、设备/系统/版本字段齐全，已经能解决大量偶发问题。

动态日志级别要控制三类成本。CPU 成本来自字符串构造、序列化和压缩；I/O 成本来自频繁写文件与同步落盘；流量成本来自批量上传。开关应按 tag 或结构化事件类型生效，只覆盖明确分桶，并以服务端到期时间和客户端累计预算双重终止。每次下发、命中、续期和撤销都写审计记录；客户端无法验证签名、版本或有效期时，维持安全的默认级别。

## 用户反馈与问题复现

用户反馈不能只收一句“打不开”。排障入口要把反馈转换成可检索的证据包，让后续查询能按同一组字段聚合。最小字段包括：事件编号、经过授权的用户或会话标识、App 版本、安装渠道、设备型号、Android 版本、发生时间与时区、网络类型、页面或功能入口、操作步骤、错误提示，以及可用的请求 ID。截图和录屏要提醒用户检查通知、账号、聊天内容等屏幕隐私。

Android bug report 包含系统服务诊断输出、`dumpstate` 产物和 `logcat` 等数据。普通用户需要启用开发者选项并主动生成、分享，它不是 App 可以静默读取的线上接口。文件可能包含设备与其他应用信息，接收方应提示风险、取得同意、限制访问并按事件保留期删除。Crashlytics 一类平台的 custom keys 与自定义日志适合附加 App 内上下文，但仍受字段数量、大小和隐私规则约束。两类材料的分工不同：bug report 偏系统现场，崩溃平台偏应用上下文。

复现时先把问题分成四类：

- **强复现问题**：固定步骤能稳定触发。直接拉本地环境、打开 DEBUG 日志和 Perfetto，按 13.2 节流程抓取 Trace。
- **弱复现问题**：同一用户或同一机型偶尔触发。保留用户现场数据，按设备型号、系统版本、区域、网络、渠道分组，找重复出现的组合。
- **数据依赖问题**：只在某些账号、缓存、配置或服务端返回下触发。复现包要保存配置版本、接口返回摘要、数据库 schema 版本和迁移状态。
- **时序依赖问题**：只在启动、切后台、网络切换、进程恢复、灰度切换时触发。复现时要保留时间线，单条错误日志通常不够。

反馈处理从判断证据缺口开始：缺少关联键就补会话或请求标识，缺少时间线就补有界日志窗口，怀疑系统状态且用户愿意配合时再请求 bug report，缺少业务状态就补经过审核的 custom keys。bug report 应是高成本的后备手段，不能成为每次反馈的默认要求。证据补齐后再决定是否启用临时诊断、下发运行期开关或发布修复版本。

## 线上 Trace 抓取与分析

Trace 适合回答“时间花在哪里”和“线程为什么没跑”。线上排障里，Trace 不能替代日志；日志描述业务状态，Trace 描述线程、调度、锁、Binder、渲染和 I/O 时间。两者要用同一套会话 ID 和时间戳关联。

发布版 App 不能假设自己可以在用户设备上随意抓取完整系统 Trace。Android 9 起设备提供 System Tracing 应用，Android 10 起保存 Perfetto 格式；这条路径需要用户或测试人员操作。Android 15 新增的 `ProfilingManager` 才给普通 App 提供受系统约束的程序化 profiling，它返回经过裁剪或脱敏、与请求进程相关的数据，不等同于 adb 条件下的全设备 Trace。

**Android 线上诊断能力按版本分层**：

| 平台版本 | 普通 App 可用能力 | 需要记住的边界 |
|---|---|---|
| Android 10 / API 29 | System Tracing、bug report、App 内 trace section | 系统 Trace 依赖用户或 adb；尚无 `ApplicationExitInfo` |
| Android 11 / API 30 | `getHistoricalProcessExitReasons()`、`getTraceInputStream()` | 查询退出历史；trace 可能为空或被系统环形缓冲区覆盖 |
| Android 12-14 / API 31-34 | 延续退出历史；API 31 起 Native crash 可返回 protobuf tombstone | 按 reason 区分 ANR trace 与 Native tombstone |
| Android 15 / API 35 | `ProfilingManager.requestProfiling()` | 请求可能延迟、失败或被限流；连续类型应提前开始并用 `CancellationSignal` 停止 |
| Android 16 / API 36 | `ProfilingTrigger`、`addProfilingTriggers()` | 系统触发结果只投递给全局 listener，不保证每次触发都有文件 |
| Android 16 36.1 与 Android 17 / API 37 | `requestRunningSystemTrace()` 与扩展触发类型 | 仅在后台 trace 正在运行且 App 已注册对应 trigger 时才可能得到快照 |

Android 15 的 `requestProfiling()` 支持 system trace、Java heap dump、heap profile 和 stack sampling。请求必须配好 listener 与 executor；系统会同时按应用和全局预算限流，回调中的 `ProfilingResult` 才能说明成功、失败或限流原因。结果文件交付到应用数据目录后，应用仍要执行容量、保留期和上传策略。

Android 16 的 `ProfilingTrigger` 支持注册 ANR、`APP_FULLY_DRAWN` 等事件。version 36.1 增加 `requestRunningSystemTrace()` 和 `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE`；这个 API 请求的是系统后台 trace 的快照，不会为调用方临时启动一条不受约束的全局 Trace。Android 17 / API 37 又增加 OOM、冷启动、异常行为、兼容性问题和过量 CPU 被终止等触发类型，不同类型返回 system trace、stack sample、heap dump 或与异常类型对应的产物。客户端应通过运行时版本检查选择能力，不能只看 `targetSdk`。详细 API 用法见 26.2 节。

线上方案仍然要把能力分成三个等级：

- **常驻轻量标记**：在启动、页面切换、列表刷新、图片加载、数据库迁移和网络请求等位置写入 `Trace.beginSection()` / `Trace.endSection()` 或 AndroidX Tracing section，并用独立指标记录耗时。section 只有在 Trace 被采集时才会出现，不能代替常驻指标。
- **触发式 App 内证据**：对少量目标用户打开函数耗时、主线程卡顿、请求耗时、I/O 摘要、锁等待摘要。只保留聚合结果和短窗口明细，避免把每次方法调用都上报。
- **人工协助系统 Trace**：当问题影响面大、复现路径清楚、用户或测试设备可配合时，再引导抓取 bug report 或 Perfetto Trace。文件要带采集时间、场景说明、App 版本和会话 ID。

线上 Trace 分析建议按同一张表归档：

| 场景 | 触发条件 | 必带轨道或字段 | 关联章节 |
|------|----------|----------------|----------|
| 慢启动 | 冷启动 P90/P99 突然上升 | 进程启动时间、主线程、RenderThread、Binder、磁盘 I/O、首屏业务阶段名 | 21.x、13.2 |
| 页面卡顿 | jank rate 或慢帧上升 | Choreographer、RenderThread、SurfaceFlinger、主线程长任务、GC | 22.x、13.2 |
| 网络疑难 | 请求超时或 5xx 集中出现 | traceId、DNS、connect、TLS、TTFB、服务端日志索引 | 24.x、26.1 |
| ANR / 卡死 | 前台 ANR 或长时间无响应 | 主线程堆栈、Binder 等待、锁等待、CPU 调度、输入事件时间线 | 20.3、13.2 |

如果团队已经有 traceId 或 requestId，Trace section 名称不要写高基数值。section 只写稳定阶段名，高基数字段放日志或事件属性里，否则 Perfetto 视图和聚合统计会被大量唯一名称污染。

## 灰度环境与问题隔离

灰度环境用于限制风险范围，并让诊断配置与功能开关能够撤销。它同时服务发版和线上排障：给小范围用户增加日志、下发诊断配置、关闭可疑功能或恢复旧配置，都应经过同一套授权、发布、监控和审计规则。

隔离策略按影响面从小到大排列：

- **单用户隔离**：经用户同意后，对反馈会话开启受控日志、诊断动作或备用配置。适合弱复现问题。
- **同类设备隔离**：按设备型号、系统版本、ABI、渠道、地区、网络类型圈定。适合厂商 ROM、SoC、网络环境相关问题。
- **版本隔离**：按 App 版本、配置版本、资源版本、热修复版本切分。适合发版后指标异常或配置下发事故。
- **功能隔离**：用远程配置关闭可疑功能、切回旧实现、降采样、降低图片质量、停用高风险实验。适合无法立刻发版但可以止损的场景。

Google Play staged rollout 可以停止继续分发，但已经收到该版本的用户仍停留在该版本；修复通常需要发布更高 versionCode 的新版本，不能把“halt”理解为远程降级已安装 APK。Firebase Remote Config rollout 可以把同一 rollout 的比例降到 0，使客户端在后续 fetch 与 activate 后回到模板值。两条路径的生效时延不同，事故预案要分别准备“停止新增曝光”“运行期关闭功能”和“发布修复版本”。

远程开关也有失败模式。旧客户端可能不认识新字段，设备可能离线，配置缓存可能尚未刷新，服务端也可能误下发。关键功能应给出向后兼容默认值、配置 schema 版本和本地有效期；关闭功能的开关要经过演练，不能在事故发生后才验证客户端是否会执行。

灰度期间只看崩溃率不够。Android vitals 会评估 user-perceived crash rate、user-perceived ANR rate、启动、慢渲染、耗电、LMK 等质量指标；业务侧还要看登录、支付、播放、下载等路径指标。排障期间的判断要同时满足两条线：技术指标没有继续恶化，用户路径指标没有出现新异常。

## 扩展：证据包模板

每个线上疑难问题可以按同一份模板建单，避免排障过程散在聊天记录里：

- **现象**：用户看到的结果、错误文案、截图或录屏。
- **范围**：影响用户数、版本、设备、系统、渠道、地区、网络。
- **时间线**：首报时间、指标开始异常时间、最近一次发版或配置变更时间。
- **证据**：日志文件、Crash / ANR report、bug report、Trace、服务端日志索引、用户反馈单。Android 11+ 补充 `ApplicationExitInfo` 退出记录，包括进程名、reason、status、时间戳、importance，以及可用时的 trace；PSS/RSS 是系统最近一次采样值，可能为 0，也不是死亡瞬间的精确快照。与 SDK 事件可按进程名、时间窗、reason、session_id 和 trace 摘要做概率关联，关联结果要保留置信标记。
- **变更**：App 发版、热修复、远程配置、服务端发布、运营活动、第三方 SDK 版本。
- **处置**：已打开的日志开关、灰度策略、回滚动作、下一次观察窗口。
- **结论**：定位到的模块、修复方式、验证方式、后续防复发项。

这个模板用于减少遗漏。排障人员拿到单子后，可以直接判断缺哪类证据。结论栏要区分“已由复现实验或代码路径证明”“由时间与分桶相关性支持”“证据仍不充分”，避免把同时发生的变更直接写成根因。

## 从症状到证据的案例索引

常见事故不需要各自维护一篇独立案例文档。把症状拆成阶段，再按同一份证据包推进，既能复用排障流程，也能避免“常见原因”被写成既定根因。

| 用户症状 | 首先拆分的阶段 | 必须关联的证据 | 典型止损动作 |
| --- | --- | --- | --- |
| 下载卡在 99% | 正文接收、flush、校验、解压、rename、数据库更新、UI 状态 | DNS/connect/TLS/TTFB、`Range`/`Content-Range`、期望与已写字节、剩余空间、校验结果、状态转换、request ID | 暂停有问题的断点续传或收尾路径，保留失败批次 |
| 低端机启动 P95 上升 | 进程创建、`Application`、Provider、首帧、业务 ready | 启动类型、设备档位、本地数据量、编译状态、磁盘 I/O、类加载、初始化 Trace、构建与配置版本 | 缩小灰度，对受影响设备关闭可选初始化 |
| 支付页卡约 3 秒 | UI 主线程、Binder、网络、锁、服务端等待、超时重试 | 页面阶段名、线程状态、请求 ID、DNS/TLS/TTFB、服务端日志、配置版本、代表性 Trace | 关闭可疑实验或重试策略，切换受支持的备用链路 |
| 后台耗电无法复现 | 任务调度、wakelock、网络批次、前台服务、进程状态 | 任务 enqueue/start/stop、约束、省电与热状态、wakelock、网络、Battery Historian/Perfetto 时间线 | 停止高频任务或诊断采集，收紧后台策略 |

这些案例共用一个闭环：先确认指标和状态定义，再检查采集链路是否完整；按版本、设备、渠道和场景圈定影响面；找同一时间窗内的发布、配置和服务端变更；抽取代表样本补日志或 Trace；执行可撤销的止损；最后用原口径验证恢复。若只有时间相关性，结论保持为候选，直到代码路径、对照实验、回滚或可重复 Trace 提供更强证据。

Runbook 至少要固定负责人、告警入口、证据查询、权限申请、止损开关、升级路径、恢复判定和复盘动作。每次演练还应覆盖队列满、上传失败、schema 不兼容、时钟偏差和诊断开关无法下发，避免只验证事故链路的成功分支。


### 平台与 OEM 补充：StatsD 的权限边界

StatsD 可以给 Android 平台、OEM 和具备相应权限的系统组件提供长期聚合数据，但它不是普通第三方 App 的通用线上查询接口。Android 17 的 `StatsManagerService` 通过 Binder 与 Native `statsd` daemon 通信，`StatsCompanionService` 负责部分系统协作；这条链路不是 JNI 三层模型。

权限决定了适用对象：

| 操作 | Android 17 平台权限 | 对普通第三方 App 的含义 |
|---|---|---|
| 注册 pull atom callback | `REGISTER_STATS_PULL_ATOM`，`signature|privileged` | 不能通过运行时申请获得 |
| 读取受限指标 | `READ_RESTRICTED_STATS`，`internal|privileged` | 不属于公开应用能力 |
| 配置或读取 statsd 数据 | 服务端检查 `DUMP`、`PACKAGE_USAGE_STATS` 与 usage-stats AppOp | `DUMP` 明确不供第三方应用使用 |

因此，面向 Play 发布的普通 App 应使用自有 Metrics、Android vitals、`ApplicationExitInfo` 和 `ProfilingManager`。平台或 OEM 项目如果已经通过合规审查导出 StatsD 聚合结果，可以把 atom ID、config key/version、elapsed timestamp、聚合窗口和缺失状态放入证据包，再与 Perfetto 时间线对照。没有权限时，应明确记录“不可用”，不能建议用户授予所谓“特殊权限”，也不能把虚构的业务字段称为系统 atom。

### Android 17：StatsD 重启后的注册恢复

这一段只适用于平台、OEM 或具备权限的系统组件。`android-17.0.0_r1` 已公开，StatsD 模块位于 `platform/packages/modules/StatsD/`，不再需要用 Android 16 源码推测 Android 17 行为。

`StatsManagerService.registerPullAtomCallback()` 会先把 `PullerKey` 与回调参数写入 `mPullers`，再通过 `getStatsdNonblocking()` 尝试通知 Native daemon。statsd 暂时不可用时，服务保留 Java 侧注册；后续 `statsdReady()` 更新 `mStatsd`、唤醒等待者，并由 `sayHiToStatsd()` 重放 puller 与 PendingIntent 订阅。各 `registerAll*()` 方法在锁内复制容器，释放锁后再执行 Binder IPC，避免持有 `mLock` 跨进程调用。

数据读取路径使用 `waitForStatsd()`，Android 17 的 `STATSD_TIMEOUT_MILLIS` 为 5000。这个常量是单次等待 daemon 连接的上限，不能解释为“最多只丢五秒数据”；daemon 停机期间是否缺数据，还取决于事件入口、队列、配置恢复时点和数据源本身。

排查平台侧 StatsD 时，可以据此区分三类状态：

- 注册调用已返回、daemon 当时不可用：检查 `statsdReady()` 之后是否完成重放，而非要求调用方无限重复注册。
- 读取或配置调用失败：记录具体 API、config key、调用 UID、权限/AppOp 结果和连接超时，重试必须使用稳定 key 与有界退避。
- 指标时间线有空洞：同时核对 statsd 生命周期、配置生效时间和 atom 生产端；仅凭 Java 缓存仍存在，不能证明停机期间的 atom 已保存。

Native `statsd` 在 Android 17 的 `main.cpp` 中仍创建上限 50000 条、未预分配的 `LogEventQueue`，随后启动 socket listener、注册 Binder 服务并与 companion 建立联系。这个上限不能直接换算成固定 RSS，也不能单独用于判断 OOM 根因。

## 小结

线上排障的核心是用最小必要采集得到可验证证据。远程日志保存业务状态，用户反馈给出复现入口，Trace 解释线程与调度时间线，灰度和运行期开关限制新增影响。Android 17 提供了更丰富的 profiling trigger，但系统限流、权限、隐私和结果缺失仍是设计输入；事件结论必须标明证据强度，并用相同指标验证修复效果。

## 参考资料

- [Android 日志信息泄露风险](https://developer.android.com/privacy-and-security/risks/log-info-disclosure)
- [抓取和阅读 bug report](https://developer.android.com/studio/debug/bug-report)
- [设备端系统 Trace](https://developer.android.com/topic/performance/tracing/on-device)
- [`ApplicationExitInfo` API](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ProfilingManager` API](https://developer.android.com/reference/android/os/ProfilingManager)
- [`ProfilingTrigger` API](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [基于触发器采集 profiling 数据](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [Google Play staged rollout](https://support.google.com/googleplay/android-developer/answer/6346149)
- [Firebase Remote Config rollout](https://firebase.google.com/docs/remote-config/rollouts/about)
- [AOSP Android 17：平台权限声明](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/AndroidManifest.xml)
- [AOSP Android 17：`StatsManagerService`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/service/java/com/android/server/stats/StatsManagerService.java)
- [AOSP Android 17：`statsd` 启动入口](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/statsd/src/main.cpp)
