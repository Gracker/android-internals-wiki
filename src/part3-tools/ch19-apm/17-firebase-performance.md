---
title: "Firebase Performance"
deepseek_polish_state: done
last_deepseek_polish_at: '2026-05-25'
chapter: "19"
section: "19.17"
status: finalized
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-25"
last_verified_against: "Firebase Performance custom-code-traces / screen-traces / troubleshooting docs, Firebase Android SDK 20.1.0+ Fragment screen rendering boundary, external review 2026-04-25"
confidence: medium
tags: [apm]
related_chapters: ["19.0", "19.11"]
sources:
  - type: official
    path: "https://firebase.google.com/docs/perf-mon"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/get-started-android"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/troubleshooting"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/network-traces"
  - type: official
    path: "https://firebase.google.com/docs/perf-mon/screen-traces"
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: "reviewed"
task2b_state: fixed
task2b_result: fixed
task9_result: "pass-tech-review"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-08"
last_task9_at: "2026-05-08T02:30:38+08:00"
reviewed_by: openclaw-task9
reviewed_date: "2026-05-08"
last_task2b_at: "2026-05-07T23:47:13+08:00"
repaired_date: "2026-04-25"
repaired_by: openclaw-task2b
last_task6_at: "2026-05-08T02:09:46+08:00"
last_task6_audit: 2026-07-05
task6_review_notes: "2026-05-08 01:08 task6 revisiting-review: pass-light-edit。复核 Task2B 回炉修正后的写作层，修复 6 处 L1/L2 文风与可读性问题；保留 task9_result=pending 等待 Task9 复审。 | 2026-05-08 02:09 task6 revisiting-review: pass-light-edit。修复 YAML 引号、重复验证句和 8 处 L1/L2 表达问题；Task9 仍为 pending，未自动晋升。"
task9_review_notes: "2026-05-08 01:32 Task9 deep-review: needs-rework。P0 2 / P1 1 / P2 1。 | 2026-05-08 01:40 Task2B rework: P0 attribute key 32->40 + reserved prefix；P0 Cronet 改为 HttpMetric manual trace；P1 EventListener 删除无证据断言 | 2026-05-08 02 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_audit: "2026-06-20"
last_task9_audit_log: "logs/deep-review/2026-06-20-09-audit.md"
last_task9_audit_at: "2026-06-20T09:26:03+08:00"
last_task9_audit_result: "pass-audit-p2-only"
task9_audit_notes: "2026-06-20 Task9 idle audit: P0 0 / P1 0 / P2 3；Firebase _app_start 起点、main process only、screen rendering 60Hz 假设作为 P2 仅日志记录，正文未修改。"
---
# Firebase Performance

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 Firebase Performance 是托管型低接入成本方案，适合快速获得基础性能看板，但定制能力和数据控制有限。
- 🔹 [trace 模型] 展开自动 trace、自定义 trace、metric、attribute、screen rendering trace、network request trace 的数据关系。
- 🔹 [自动采集] 按启动、前后台、屏幕渲染、HTTP/S 请求列自动采集能力和需要官方文档核对的版本要求。
- 🔹 [自定义 trace] 给启动、首屏、登录、图片解码、数据库查询示例，说明 trace 名称、metric、attribute 的命名规则。
- 🔹 [网络聚合] 说明 URL pattern、域名、path 参数、状态码、payload size、失败原因如何影响聚合结果和隐私。
- 🔹 [JankStats 关系] 区分 Firebase 的屏幕渲染指标和 JankStats 的端侧帧数据；写清什么时候需要自采。
- 🔹 [采样与延迟] 说明数据采集、上传、控制台展示延迟、采样、阈值、版本维度对问题定位的影响。
- 🔹 [Google Play] 写与 Google Play Console / Android Vitals 的互补关系，避免重复解释同一类慢帧或 ANR 数据。
- 🔹 [接入成本] 覆盖 Gradle plugin、Google services、地区访问、账号权限、隐私政策、Release 开关。
- 🔹 [适用边界] 明确适合中小团队快速建看板，不适合深度私有化、复杂自定义诊断和完整原始样本回溯。

### 扩展（可选深入）

- 🔸 增加一份 Firebase custom trace Kotlin 示例，包含 metric 和 attribute。
- 🔸 补一张 Firebase、JankStats、FrameMetrics、Google Play Vitals 的指标分工表。
- 🔸 对 Firebase Performance official docs、Android SDK 版本要求和自动 trace 列表做 L1 核对。
- 🔸 补一个 URL pattern 设计案例，说明如何避免把用户 id、订单 id 写进 trace 名。
- 🔸 增加从 Firebase 迁移到自建 APM 或商业 APM 时需要保留的字段清单。

### 流水线加工要求

- 每个 Firebase 能力都要写清“自动采集还是自定义采集”。
- 所有控制台数据解释必须包含展示延迟和采样限制。
- 示例字段不能包含真实用户标识、完整 URL 或业务敏感值。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## Firebase Performance 的定位

Firebase Performance Monitoring 是托管型性能看板。它的长处是接入快、自动采集覆盖面广、控制台不需要自建；短板是原始样本控制弱、字段契约弱、私有化能力弱，控制台还有处理延迟。

它适合中小团队先把启动、渲染、网络和少量业务 trace 建起来，再用 JankStats、Perfetto 或自建 APM 补深度诊断。把它当成秒级事故面板会踩空。

## 数据模型：trace、metric、attribute

Firebase 的基本单位是 trace。自动 trace 和 custom trace 都会挂 metric 与 attribute。网络 request trace 还会附带 URL pattern、status code、payload size 这一类字段，用来做版本、设备和接口维度的聚合。

| 对象 | 含义 | 例子 | 使用建议 |
| --- | --- | --- | --- |
| trace | 一段时间窗口 | `app_start`、`home_first_feed` | 名称稳定，不拼动态值 |
| metric | 这个窗口里的数值 | duration、`item_count`、`payload_kb` | 只放数值计量，不拼动态维度 |
| attribute | 过滤维度 | `entry=cold_start`、`result=success` | 只放低基数枚举上下文，不放 user id |

metric 用来做累加、平均或分布统计；attribute 用来过滤和分组。把用户 id、订单号、完整搜索词这类高基数字段塞进 attribute，会让控制台聚合变散。

这个模型擅长回答“哪个版本慢了”“哪类设备慢了”“哪条业务路径慢了”，不擅长还原某一次事故的完整调用路径。

## 构建链和采集开关

Firebase Performance 不是只加一个 SDK 依赖就结束。官方 get-started 文档要求把 `com.google.gms.google-services` 和 `com.google.firebase.firebase-perf` 两个 Gradle plugin 都接进构建链，并提供 `google-services.json`。

```kotlin
plugins {
    id("com.android.application")
    id("com.google.gms.google-services")
    id("com.google.firebase.firebase-perf")
}
```

Manifest 开关要单独写清楚：

- `firebase_performance_collection_enabled=false`：默认关闭采集，后面还可以按灰度策略再打开
- `firebase_performance_collection_deactivated=true`：完全停用；它会覆盖前一个开关，想恢复只能改 Manifest 重新发版

```xml
<application>
    <meta-data
        android:name="firebase_performance_collection_enabled"
        android:value="false" />
</application>
```

Release 策略也要固定下来：debug 包默认关闭，内部测试包只开小流量，正式版按地区和渠道放量。这样可以避免开发期噪声把线上盘面污染掉。

接入前还要把地区可用性、Firebase project 权限、Google Analytics 权限、隐私政策和数据保留口径写进发布清单。产品不面向 Google 服务可用地区时，控制台可用性要先验证。

## 自动采集能力与版本边界

Firebase 的自动采集很多，但边界也很明确：

| 能力 | 采集方式 | 稳妥边界 | 局限 |
| --- | --- | --- | --- |
| App start / foreground / background | 自动 | 跟随当前 Android SDK 接入；API 24+ 可用系统进程启动时间作为冷启动起点 | 适合看版本趋势，不等于完整首屏 |
| Screen rendering | 自动 | Activity 自动 screen trace；Firebase Performance Android SDK 20.1.0+ 支持 Fragment screen rendering trace | 能看 Activity / Fragment 聚合，不能替代 JankStats 的逐帧界面状态 |
| HTTP/S request | 自动 + 手工补点 | 官方只承诺“多数 network requests” | 不同网络库覆盖不一样，未完成请求可能漏掉 |
| Custom trace | 手工 | 跟随 SDK 接入 | 适合登录、图片解码、数据库查询这类业务路径 |

启动 trace 的起点要按版本看。API 24+ 设备可以用 `Process.getStartUptimeMillis()` 拿到进程启动时间；低版本或特殊启动路径仍会受 SDK 初始化时机影响。控制台里的 `_app_start` 还会做后台启动过滤，避免非用户触发的进程唤醒污染冷启动样本。

Screen rendering 也要区分粒度。SDK 20.1.0+ 已经能自动记录 Fragment 级 screen rendering trace，这对单 Activity / Navigation 架构有用；它仍然是控制台聚合指标，缺少 JankStats 那种逐帧界面状态和业务动作上下文。

到 Android 17，官方 get-started 和 troubleshooting 文档没有列出单独的 API 37 变更。以下内容基于最新 Firebase Android BoM，能力边界沿当前文档执行，不额外编造 Android 17 专属行为。

## 自定义 trace 的命名规则

自定义 trace 要解决两个问题：名字能长期复用，字段不会把聚合盘打散。官方限制要分对象看：trace 名和 metric 名最多 100 个字符，不能有前后空格，也不能以下划线开头；attribute key 最多 40 个字符、value 最多 100 个字符，每个 custom trace 最多 5 个 attribute。key 不能使用 `firebase_`、`google_`、`ga_` 前缀，且必须以字母开头。attribute value 也按枚举写，避免高基数字段。

| 场景 | trace 名 | metric 名 | attribute | 不要写 |
| --- | --- | --- | --- | --- |
| 首屏首批内容 | `home_first_feed` | `item_count`、`payload_kb` | `entry=cold_start` | 完整接口 URL、user id |
| 登录流程 | `login_request` | `retry_count` | `result=success|fail` | 手机号、邮箱 |
| 图片解码 | `image_decode_list` | `image_count`、`decode_ms` | `source=disk|network` | 图片 hash、CDN 签名 |
| 数据库查询 | `db_query_user` | `row_count`、`query_ms` | `source=room` | SQL 原文、主键 id |

这类写法不合适：把订单号、实验桶 id、SQL 文本、完整搜索词写进 attribute，或者把 trace 名拼成 `login_user_12345`。这会同时破坏聚合效果和隐私边界。

## 网络请求聚合和 URL pattern

Firebase 自动网络 trace 更像聚合盘，不是抓包器。它擅长回答“哪个接口在某个版本变慢了”，不擅长拆 DNS、TCP、TLS、服务端队列和弱网重试这些阶段。

URL pattern 必须做归一化。像 `/api/item/10001/detail`、`/api/item/10002/detail` 这一类路径，在盘面上应该收敛成 `/api/item/{id}/detail`。query 参数里的 token、签名、搜索词、实验参数也不要直接进聚合维度。

状态码、payload size 和 Content-Type 只能解释一部分失败。DNS、TLS、timeout、服务端 5xx 这类原因要靠客户端错误码或服务端 trace 补齐，避免多个失败阶段都混在同一个 URL pattern 里。

官方文档给了几条实操边界：

- Gradle plugin 通过字节码插桩拦截 OkHttp，但覆盖范围有限：自研网络库、Cronet、native 网络栈或非常规封装可能漏掉。Cronet、native 网络栈、自研网络库需要用 `HttpMetric` 手工 network trace：通过 `FirebasePerformance.getInstance().newHttpMetric(url, method)` 创建 metric，手动调用 `start()` / `stop()`，并设置 `setHttpResponseCode()`、`setRequestPayloadSize()` / `setResponsePayloadSize()`、`setContentType()`。不支持的协议会静默缺失
- 如果项目中使用了复杂 AOP 框架（自定义 Transformer 顺序不当），Firebase 的字节码插桩可能失败。排查路径：在 `build.log` 中搜索 `firebase-perf` 插件输出确认插桩生效；在 Logcat 中开启 `firebase_performance_logcat_enabled`，确认 `FirebasePerformance` 日志里出现 completed request 和正确的 Content-Type
- 只完成了一半、长时间不结束的连接，控制台不一定会形成稳定样本；`Content-Type` 非法的请求也可能不展示

线上要拆阶段时，还是要回到应用日志、服务端 trace 和 Perfetto。

## 采样、时效和排查边界

Firebase Performance 的控制台时效会直接影响排查方式。官方 troubleshooting 文档明确给了版本边界：Android SDK `v19.0.10+`，或 Firebase Android BoM `v26.1.0+`，才进入 near real-time 路径；旧 SDK 的控制台展示通常会落后大约 36 小时。

| SDK 情况 | 控制台时效 | 适合做什么 |
| --- | --- | --- |
| Android SDK `v19.0.10+` 或 BoM `v26.1.0+` | `SDK detected` 通常 10 分钟内可见，初始处理数据一般几分钟到 30 分钟 | 灰度观察、当日回归、版本趋势 |
| 旧 SDK | 大约 36 小时延迟 | 次日复盘、长期趋势 |

采样也不是无限上报。官方文档写明：设备侧对 code trace 和 network trace 有 10 分钟 300 事件的限流，还会做按项目动态采样。结果就是：控制台上的数据是“采样后的聚合盘”，不是每一条请求、每一帧卡顿都原样保留。

采样和时效决定了排查边界：Firebase 适合发布回归、版本比较、趋势监控，不适合秒级 incident 排查。

近实时 SDK 的几分钟延迟叠加采样过滤，可能导致事故发生时控制台仍然显示正常。不要把 Firebase Performance 作为唯一的故障发现工具——线上告警体系必须有独立的实时业务错误码监控、自建 APM 或日志告警作为主要告警路径，Firebase 只做补充验证和趋势观察。

## 和 JankStats、FrameMetrics、Android Vitals 的分工

这几套工具都会给出“卡顿”相关指标，但口径不一样：

| 工具 | 主要样本 | 长处 | 不足 |
| --- | --- | --- | --- |
| Firebase Performance | Activity / Fragment screen 聚合、network 聚合、自定义 trace | 接入快，控制台能直接看版本和设备分布 | 逐帧上下文弱，延迟高，原始样本少 |
| JankStats | 端侧逐帧数据 + 界面状态 | 能把卡顿和页面状态、实验桶、业务动作关联起来 | 需要自己存储和上报 |
| FrameMetrics | 端侧阶段耗时 | 适合做渲染阶段拆分和本地诊断 | 平台 API，字段更底层 |
| Android Vitals | Play 分发真实用户质量数据 | 适合看发布质量门槛、慢帧和 ANR 风险 | 只覆盖 Play 分发用户，业务上下文少 |

Firebase 和 Android Vitals 也不要混成一套口径。两边都可能出现“slow frames”“frozen frames”这类指标，但样本面、聚合窗口和覆盖用户群都不同，不能把百分比直接拿来比较。Google Play Console 更适合看发布质量门槛，Firebase Performance 更适合看接入 SDK 后的版本和设备分布。

## 使用建议

Firebase Performance 适合下面这类团队：

- 先把启动、渲染、网络盘面搭起来，再决定哪些流程要补自定义 trace
- 产品主要面向 Google 生态可用地区
- 团队缺少平台建设时间，也能接受聚合盘的延迟和采样限制

这些场景不能只靠 Firebase：

- 需要秒级事故排查和实时告警
- 需要自托管、私有化或更严格的数据所有权控制
- 需要还原原始 network stage、逐帧上下文、ANR 线程或 native 现场

它适合作为“第一层聚合盘”。深度诊断还是要靠 JankStats、Perfetto、服务端 trace 和更细的内部字段契约。
