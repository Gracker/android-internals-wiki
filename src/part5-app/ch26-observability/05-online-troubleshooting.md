---
title: "线上问题排查方法论"
chapter: "26.5"
section: "26.5"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-15"
last_verified_against: "Android Developers / AOSP docs / Firebase docs / Play Console docs / Clippings structure references"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 0
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
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
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task6_review_notes: '2026-05-15 task6 review: pass-light-edit。L1/L2 小修 4 处（outline 扩展占位 1、措辞精修 3）；无新增 L3/L4 回炉项，等待 Task9 技术复审。'
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-05-15T03:11:00+08:00"
last_task6_review_log: logs/review/2026-05-15-03-review.md
last_task6_at: "2026-05-15T03:11:00+08:00"
reviewed_date: "2026-05-15"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-15"
last_task9_at: "2026-05-15T03:25:00+08:00"
last_task9_review_log: logs/deep-review/2026-05-15-03-deep-review.md
task2b_result: fixed
---

# 线上问题排查方法论

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 远程日志与动态日志级别
- 🔹 用户反馈与问题复现
- 🔹 线上 Trace 抓取与分析
- 🔹 灰度环境与问题隔离

### 扩展（可选深入）

- 🔸 证据包模板：把线上反馈、日志、Trace、变更和处置记录收束到同一张问题单

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解线上问题排查方法论

线上排障处理的是复现概率低、现场容易丢、影响面会变化的问题。排障效率取决于三件事：事发前有没有埋好证据，事发时能不能把证据按用户、版本、设备和时间聚到一起，事发后能不能把风险限制在小范围内。

26.1 节已经定义 Metrics、Logs、Traces 的分工，15.5 节已经覆盖线上性能监控，13.2 节已经说明 Perfetto 抓取方式。排障实战落在四个动作上：接到反馈后拿证据、复现问题、打开临时日志或诊断开关、用灰度环境缩小问题范围。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md]

## 远程日志与动态日志级别

远程日志的目标是在用户无须安装临时包的前提下，把一次会话的必要现场留下来。线上设备仍然是用户设备，不能按远程开发机处理。日志系统至少要回答四个问题：这是谁的设备、发生在哪个版本、当时走过哪些业务步骤、失败点附近有哪些系统状态。

[已验证: 官方文档, developer.android.com/privacy-and-security/risks/log-info-disclosure]
[已验证: AOSP 文档, source.android.com/docs/core/tests/debug/understanding-logging]

一套可用的远程日志方案通常分成四层：

- **本地写入层**：把日志先写到 App 私有目录，按时间、大小和会话切分文件，避免单个文件无限增长。多进程 App 要给每个进程独立文件或独立通道，合并动作放到后台上报进程处理。
- **采样与开关层**：默认只保留 INFO 以上的短期窗口；对目标用户、目标机型、目标版本临时打开 DEBUG 级别。系统文档里的 `log.tag.<TAG>` / `Log.isLoggable()` 适合本地和系统调试，线上 App 更常见的做法是用自有远程配置维护 tag 级别。
- **脱敏与合规层**：日志里不能写手机号、精确位置、完整 token、支付信息、联系人内容。确需关联用户时，只保留内部用户 ID、匿名设备 ID 或 hash 后的请求 ID，并在上报前做字段级清洗。
- **拉取与主动上报层**：用户反馈、Crash、ANR、严重业务失败可以触发主动上报；排障人员也可以对指定用户下发一次性拉取任务。拉取任务要带过期时间、文件大小上限和网络条件，避免把排障动作变成新的性能问题。

参考素材里的 Xlog、Logan、Holmes 分别代表三种思路：高性能本地日志、统一日志平台、动态补充执行路径。这里借鉴的是组织方式，不照搬实现。普通团队可以先做小版本：会话 ID、请求 ID、页面路径、关键业务状态、错误码、设备/系统/版本字段齐全，已经能解决大量偶发问题。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md]

动态日志级别要控制三类成本。CPU 成本来自字符串拼接、序列化和压缩；I/O 成本来自频繁写文件和落盘；流量成本来自批量上传。可执行的边界是：开关按 tag 生效，最多持续几个小时；DEBUG 日志只对少量用户生效；单次上报限定大小；敏感字段通过统一接口写入，业务代码不能绕过清洗层。

## 用户反馈与问题复现

用户反馈不能只收一句“打不开”。排障入口要把反馈转换成可检索的证据包，让后续查询能按同一组字段聚合。最小字段包括：用户 ID 或匿名 ID、App 版本、安装渠道、设备型号、Android 版本、发生时间、网络类型、页面或功能入口、用户操作步骤、错误提示截图、会话 ID、请求 ID。

[已验证: 官方文档, developer.android.com/studio/debug/bug-report]
[已验证: 官方文档, firebase.google.com/docs/crashlytics/android/customize-crash-reports]

Android bug report 包含 `dumpsys`、`dumpstate` 和 `logcat` 数据，适合用户愿意配合、问题影响较大、系统状态可能参与的场景。Crashlytics 这类崩溃平台支持自定义 keys、日志和用户标识，适合把业务上下文贴到 Crash 或 non-fatal report 上。两类材料的分工不同：bug report 更偏系统现场，崩溃平台更偏 App 内上下文。

复现时先把问题分成四类：

- **强复现问题**：固定步骤能稳定触发。直接拉本地环境、打开 DEBUG 日志和 Perfetto，按 13.2 节流程抓取 Trace。
- **弱复现问题**：同一用户或同一机型偶尔触发。保留用户现场数据，按设备型号、系统版本、区域、网络、渠道分组，找重复出现的组合。
- **数据依赖问题**：只在某些账号、缓存、配置或服务端返回下触发。复现包要保存配置版本、接口返回摘要、数据库 schema 版本和迁移状态。
- **时序依赖问题**：只在启动、切后台、网络切换、进程恢复、灰度切换时触发。复现时要保留时间线，单条错误日志通常不够。

反馈处理的第一步是判断证据缺口：少用户身份就补用户标识，少时间线就补日志窗口，少系统状态就让用户导出 bug report，少业务状态就补 custom keys。证据补齐后再决定是否发临时日志、热修复或灰度包。

## 线上 Trace 抓取与分析

Trace 适合回答“时间花在哪里”和“线程为什么没跑”。线上排障里，Trace 不能替代日志；日志描述业务状态，Trace 描述线程、调度、锁、Binder、渲染和 I/O 时间。两者要用同一套会话 ID 和时间戳关联。

[已验证: 官方文档, developer.android.com/topic/performance/tracing/on-device]
[已验证: 官方文档, developer.android.com/tools/perfetto]
[详见 13.2 节]

发布版 App 不能假设自己可以在用户设备上随意抓系统级 Trace。Perfetto 是 Android 10 之后的系统追踪工具，官方文档推荐用 Perfetto viewer 分析慢启动、慢转场、UI jank 等性能问题；不同 Android 版本下获取完整系统 Trace 的手段不一样，需要按版本分层处理。

**Android 线上诊断能力按版本分层**：

| 能力 | Android 10-14 (API 29-34) | Android 15 (API 35) | Android 16+ (API 36) |
|------|---------------------------|---------------------|----------------------|
| 系统 Trace 获取 | 需 adb/用户协助/系统权限 | `ProfilingManager.requestProfiling()` App 程序化请求 | `ProfilingManager` + `ProfilingTrigger` 事件触发 |
| 退出原因查询 | `getHistoricalProcessExitReasons()` ✅ | ✅ | ✅ |
| ANR Trace | `getTraceInputStream()` ✅ | ✅ | ✅ |
| Native Tombstone | ✅ (API 31+) | ✅ | ✅ |
| 事件触发 Profiling | ❌ | ❌ | `ProfilingTrigger`（ANR/fully drawn/主动请求） |

**Android 10-14**：完整系统 Trace 依赖 adb、bugreport 或用户协助。只能在问题影响面大、复现路径清楚且用户或测试设备可配合时抓取。线上方案更多依赖 App 内埋点（`Trace.beginSection()`、自有耗时埋点）和服务端聚合。

**Android 15+**：`ProfilingManager.requestProfiling()` 可由 App 程序化请求 system trace、heap dump 或 stack profiling，结果写入 App 数据目录。有 rate limiter 保护（结果去重、频率控制），不影响用户数据。推荐在连续 profiling 场景提前开始、及时取消。详细 API 签名见 §26.2 附录 A.2。

**Android 16+**：`ProfilingTrigger` 可注册 ANR、`APP_FULLY_DRAWN`、App 主动请求等事件触发追踪，自动在事件发生时采集 system trace，配合 rate limiter 控制频次。详细触发类型和注册方法见 §26.2 附录 A.3。

线上方案仍然要把能力分成三个等级：

- **常驻轻量标记**：在启动、页面切换、列表刷新、图片加载、数据库迁移、网络请求等位置写入 `Trace.beginSection()` / `Trace.endSection()` 或自有耗时埋点。它不负责长时间保存系统 Trace，只负责让本地 Trace 和线上指标能对上阶段名。
- **触发式 App 内证据**：对少量目标用户打开函数耗时、主线程卡顿、请求耗时、I/O 摘要、锁等待摘要。只保留聚合结果和短窗口明细，避免把每次方法调用都上报。
- **人工协助系统 Trace**：当问题影响面大、复现路径清楚、用户或测试设备可配合时，再引导抓取 bug report 或 Perfetto Trace。文件要带采集时间、场景说明、App 版本和会话 ID。

线上 Trace 分析建议按同一张表归档：

| 场景 | 触发条件 | 必带轨道或字段 | 关联章节 |
|------|----------|----------------|----------|
| 慢启动 | 冷启动 P90/P99 突然上升 | 进程启动时间、主线程、RenderThread、Binder、磁盘 I/O、首屏业务阶段名 | 21.x、13.2 |
| 页面卡顿 | jank rate 或慢帧上升 | Choreographer、RenderThread、SurfaceFlinger、主线程长任务、GC | 22.x、13.2 |
| 网络疑难 | 请求超时或 5xx 集中出现 | traceId、DNS、connect、TLS、TTFB、服务端日志索引 | 24.x、26.1 |
| ANR / 卡死 | 前台 ANR 或长时间无响应 | 主线程堆栈、Binder 等待、锁等待、CPU 调度、输入事件时间线 | 20.3、13.2 |

[自动发现] 如果团队已经有 traceId 或 requestId，Trace section 名称不要写高基数值。section 只写稳定阶段名，高基数字段放日志或事件属性里，否则 Perfetto 视图和聚合统计会被大量唯一名称污染。

## 灰度环境与问题隔离

灰度环境的任务是把风险拆小，并让排障动作可回退。它同时服务发版和线上排障：给少量用户打开日志、下发诊断配置、切换接口域名、关闭可疑功能、回滚有问题的远程配置，都应该走同一套发布和监控规则。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]
[已验证: 官方文档, support.google.com/googleplay/android-developer/answer/6346149]
[已验证: 官方文档, firebase.google.com/docs/remote-config/rollouts/about]
[已验证: 官方文档, developer.android.com/topic/performance/vitals]

隔离策略按影响面从小到大排列：

- **单用户隔离**：对反馈用户开启日志、诊断指令或备用配置。适合弱复现问题和 VIP 用户问题。
- **同类设备隔离**：按设备型号、系统版本、ABI、渠道、地区、网络类型圈定。适合厂商 ROM、SoC、网络环境相关问题。
- **版本隔离**：按 App 版本、配置版本、资源版本、热修复版本切分。适合发版后指标异常或配置下发事故。
- **功能隔离**：用远程配置关闭可疑功能、切回旧实现、降采样、降低图片质量、停用高风险实验。适合无法立刻发版但可以止损的场景。

Google Play 的 staged rollout 支持暂停发布；Firebase Remote Config rollout 支持按比例下发并在同一 rollout 内把比例降到 0，让用户回到模板默认值。这类能力说明灰度既要能逐步放量，也要能快速停止。自建发布平台也要有同样的按钮：暂停、回滚、扩大、只读审计、事故备注。

灰度期间只看崩溃率不够。Android vitals 会评估 user-perceived crash rate、user-perceived ANR rate、启动、慢渲染、耗电、LMK 等质量指标；业务侧还要看登录、支付、播放、下载等路径指标。排障期间的判断要同时满足两条线：技术指标没有继续恶化，用户路径指标没有出现新异常。

## 扩展：证据包模板

[自动发现]

每个线上疑难问题可以按同一份模板建单，避免排障过程散在聊天记录里：

- **现象**：用户看到的结果、错误文案、截图或录屏。
- **范围**：影响用户数、版本、设备、系统、渠道、地区、网络。
- **时间线**：首报时间、指标开始异常时间、最近一次发版或配置变更时间。
- **证据**：日志文件、Crash / ANR report、bug report、Trace、服务端日志索引、用户反馈单。Android 11+ 补充 `ApplicationExitInfo` 快照（`getHistoricalProcessExitReasons()` 返回的退出原因、时间戳、importance 和 PSS/RSS）。与 SDK 上报的 event/sessionId 按 pid + 时间戳窗口去重，避免同一崩溃重复计数。
- **变更**：App 发版、热修复、远程配置、服务端发布、运营活动、第三方 SDK 版本。
- **处置**：已打开的日志开关、灰度策略、回滚动作、下一次观察窗口。
- **结论**：定位到的模块、修复方式、验证方式、后续防复发项。

这个模板的作用是减少遗漏。排障人员拿到单子后，能直接判断缺哪类证据，少一些“还有没有日志”的反复追问。

## 小结

线上排障要把“猜问题”改成“补证据”。远程日志提供业务现场，用户反馈提供复现入口，Trace 提供时间线，灰度环境提供风险隔离。四件事连在一起，才能把偶发问题从一次投诉变成可验证、可回滚、可复盘的工程事件。
