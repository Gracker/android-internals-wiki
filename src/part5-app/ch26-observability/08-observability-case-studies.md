---

title: "可观测性案例集"
chapter: "26.8"
section: "26.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-15"
last_verified_against: "Android Developers docs / Android Vitals docs / Clippings structure references"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 0
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 3.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 13.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 35.md"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture"
  - type: official
    path: "https://developer.android.com/ndk/guides/debug"
tags: [case-study, observability, apm-setup, regression-guardrail]
related_chapters: ["26.1", "26.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_task2a_at: "2026-05-15T07:17:00+08:00"
task2a_result: drafted
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-08
last_task6_at: "2026-06-08T04:12:56+08:00"
last_task6_review_log: logs/review/2026-06-08-04-review.md
review_type: task6-writing-quality-review
task6_review_notes_r5: "2026-06-04 Task6 (round 5, revisiting): pass-light-edit. Fixed 7x 中英文空格 (Android XX(API) → Android XX (API)). L1 clean post-fix. No new L3/L4 issues. task9_result=needs-rework, routing to task9. | 2026-06-08 Task6 (revisiting→finalized): pass-light-edit. Task9 auto-fixed version boundary (Android 16+→16). L1/L2 clean. No B-class issues. Auto-promoted: task6=pass-light-edit, task9=auto-fixed, queue clear."
task6_review_notes_orig: "2026-05-15 Task6：pass-light-edit。修复结构性元叙述与 1 处否定-纠正句式；无新增 L3/L4 回炉问题，待 Task9 技术审查。"
task9_result: auto-fixed
last_task9_at: "2026-06-04T21:20:00+08:00"
last_task9_review_log: logs/deep-review/2026-06-04-21-deep-review.md
task9_review_notes: "2026-06-04 Task9 deep-review: auto-fixed. P1 版本边界：Runbook/诊断能力表中的 Android 16+ 改为 Android 16，避免越过 AIW Android 17/API 37 上限；P0 0 / P1 1 / P2 0。"
task2b_result: fixed-lite
last_task2b_lite_at: 2026-06-04
last_task9_autofix_at: 2026-06-04
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-10
---

# 可观测性案例集

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 从零搭建 APM 体系
- 🔹 性能回归检测实践
- 🔹 线上疑难问题排查案例

### 扩展（可选深入）

- 🔸 Runbook 模板：把监控、告警、证据包、处置动作写成可执行清单

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

可观测性体系的价值不是纸面架构，是事故来的时候能多快拿出证据。本节用可交付的路线回答三个工程问题：团队从零搭建 APM 要做对哪些事，性能回归怎样在 CI 和灰度两道门拦下来，线上疑难问题怎样把指标、日志、Trace 和发布记录拼成完整证据链。架构分层和排障方法论见 26.1 和 26.5。

## 从零搭建 APM 体系

APM 的第一版目标不该是“大而全”，而是让团队在三类事故里有证据：崩溃和 ANR 能定位线程与场景，启动和卡顿能定位页面与版本，网络和 I/O 能定位请求阶段与设备环境。26.1 节已经说明 Metrics / Logs / Traces 的分工，本案例把它压成可交付路线。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

### 第 0 周：统一事件模型

APM 平台先收敛字段，再接入模块。每个事件至少带这组公共字段：

| 字段 | 用途 | 缺失后的排障代价 |
| --- | --- | --- |
| `event_id` | 服务端去重、重试幂等 | 重传后指标被放大 |
| `session_id` | 串起一次用户会话 | Crash、日志、网络样本无法互相定位 |
| `trace_id` / `request_id` | 串起端到端请求 | 端侧错误和服务端日志无法匹配 |
| `scene_id` | 标识启动、支付、播放、下载、页面刷新等场景 | 只能看全局指标，看不到业务入口 |
| `build_version` / `config_version` | 关联发版、热修复、远程配置 | 无法判断是哪次变更引入问题 |
| `device_model` / `android_version` / `abi` | 识别机型、系统、架构差异 | 厂商或 ABI 问题会被全局均值淹没 |
| `sample_rate` / `sample_policy` | 还原采样后的比例 | 服务端无法区分“没发生”和“没采到” |

事件模型要比页面更早稳定。页面和看板可以晚一点做，字段一旦发到线上，后续改名、拆分、合并都会影响历史数据查询。

### 第 1 周：接入高价值低频事件

第一批事件只接低频、高价值、强行动性的信号：Java Crash、Native Crash、ANR、启动耗时、关键页面慢帧、网络请求错误、上报 SDK 自监控。它们有几个共同点：事件数量可控，事故优先级高，服务端能用它们触发告警。

Crash 和 ANR 的最小 envelope 包括异常类型、主线程堆栈、崩溃线程堆栈、进程名、前后台状态、最近场景、最近 20 条关键操作、内存摘要、线程数、fd 数、磁盘剩余空间。Native Crash 不要在 signal handler 里做复杂 I/O；更稳妥的方案是用成熟 crash handler 生成 minidump，再在下次启动补充业务上下文。Android 11 (API 30) 起可通过 `ActivityManager.getHistoricalProcessExitReasons()` 读取系统记录的退出原因（CRASH、ANR、LMK 等）。Android 12 (API 31) 起，native crash 对应的 `ApplicationExitInfo.getTraceInputStream()` 可返回 tombstone protobuf，作为 native crash 堆栈的补偿证据；API 30 虽然有 `ApplicationExitInfo`，但 `getTraceInputStream()` 对 `REASON_CRASH_NATIVE` 返回 null。启动、卡顿和网络事件只存阶段耗时，不存完整日志。启动事件拆成 process start、Application、首个 Activity、首帧、首页 ready、TTFD。卡顿事件记录页面、帧时间分位、主线程长任务、GC、Binder 等待摘要。网络事件记录 DNS、connect、TLS、TTFB、总耗时、HTTP 状态码、错误类型、网络类型和运营商维度。

### 第 2 周：让端侧上报不影响业务线程

上报组件经常败在采集和上报本身拖慢业务；网络不可用只是其中一类故障。可用的第一版需要满足四条约束：

- 采集入口只做对象构造和入队，主线程不写文件、不压缩、不发网络请求。
- 内存队列有上限，队列满时保留 Crash、ANR、启动和告警触发事件，丢弃普通性能样本，并把丢弃计数写入 SDK 自监控。
- 本地文件按优先级分片，Crash / ANR 摘要单独目录，Perfetto trace、HPROF、日志包这类大文件单独配额。
- 上传进程按优先级、网络类型、前后台状态和服务端限流组包，弱网下先传摘要，再传大文件。

这套设计和 19.27 节的 APM SDK 存储设计一致：端侧只负责可靠写入、有限缓存、批量发送；聚合、告警、索引、归因放到服务端。

### 第 3 周：建出第一张能处理事故的看板

APM 第一张看板不追求展示漂亮，字段要能支撑排障。

| 看板区域 | 必要能力 | 处理动作 |
| --- | --- | --- |
| 版本质量 | Crash 率、ANR 率、启动 P90/P95、慢会话比例、网络失败率 | 判定当前版本是否暂停灰度 |
| 机型分布 | 按设备、系统、ABI、渠道分组 | 判断是否是厂商、系统或架构问题 |
| 场景排行 | 启动、支付、播放、下载、首页刷新等场景 | 找到用户感知路径 |
| 样本列表 | 从聚合指标跳到单条事件、日志、Trace、发布记录 | 补齐证据包 |
| SDK 自监控 | 上报成功率、丢弃数、本地文件积压、配置版本 | 排除监控系统自身失真 |

Android Vitals 可作为外部基线。Play 质量页覆盖 user-perceived crash rate、user-perceived ANR rate、启动、慢渲染、耗电、LMK 等指标，并用最近 28 天数据评估应用质量。自建 APM 要补上内部维度：业务场景、灰度批次、配置版本、渠道、实验分组和用户日志。### 从零搭建的验收标准

第一版 APM 上线后，用三类演练验收：

1. 主动制造一次 non-fatal 和一次测试 Crash，确认端侧本地落盘、下次启动补传、服务端聚合、告警和样本回查都可用。
2. 在测试环境把启动链路注入一段 300 ms 的延迟，确认启动 P95、受影响场景、版本和设备维度能在看板上出现。
3. 让网络请求返回固定 5xx 或超时，确认端侧 requestId 能跳到服务端日志索引。

能通过这三类演练，APM 就具备处理日常事故的最低能力。后续再按事故频率依次补齐 ANR 专项、线上 Trace、功耗、I/O 和远程日志。

## 性能回归检测实践

性能回归要同时拦两条线：代码合入前的确定性退化，发布后的真实用户退化。CI 能控制环境，适合做基准测试；线上能覆盖机型、网络、数据量和厂商系统，适合发现长尾问题。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 32.md]

### CI 门禁：用固定场景测稳定指标

CI 门禁只测少量固定场景，目标是判断“这次改动是否让基线变差”。适合纳入门禁的场景：冷启动、首页首屏、核心列表滚动、搜索结果页、支付或播放入口、数据库迁移、图片密集页面。

Macrobenchmark 适合承担这类任务。官方 `StartupTimingMetric` 会采集启动时间，包括 time to initial display；`FrameTimingMetric` 会输出帧耗时分位，Android 12 (API 31)+ 还会提供 frame overrun，正数表示超过帧期限的时间。门禁不要只看一次运行结果。建议每个场景至少保留最近 N 次绿色构建的基线，比较当前构建和基线分布。启动类指标看 P50/P90/P95，渲染类指标看 frameDuration / frameOverrun 的 P90/P95/P99 和慢帧比例，I/O 类指标看主线程 I/O 次数、总时长和最大单次时长。

门禁结论分三档：

- **阻断**：关键路径 P95 明显超过基线，或 frame overrun、启动失败、ANR、Crash 出现硬性退化。构建不能进入灰度。
- **人工确认**：指标有轻微退化，但样本量小或波动较大。需要对比 trace 和变更列表。
- **记录观察**：指标变化低于阈值，但属于敏感模块。灰度期间加一个观察项。

不要让门禁覆盖所有页面。覆盖面过大后，测试时间变长，波动也会变大，团队会绕过它。门禁只守核心路径，其他路径靠线上指标和专项回归补齐。

### 灰度门禁：发布后按小时观察

灰度阶段要回答“真实用户有没有变差”。灰度数据的优势是覆盖真实设备、真实网络、真实数据量；缺点是用户样本可能有偏，指标会受地域、渠道、活跃度影响。灰度门禁要按同质分组比较，不要把全量均值当结论。

灰度观察表建议包含：

| 指标 | 观察维度 | 触发动作 |
| --- | --- | --- |
| user-perceived crash / ANR | 版本、机型、系统、渠道、前后台 | 暂停灰度，抽样 Crash / ANR 证据包 |
| 启动 TTID / TTFD P90/P95 | 冷启动、热启动、低端机、重度用户 | 降采样日志改为补采启动阶段 trace |
| 慢会话比例 / frame overrun | 页面、机型、刷新率、实验组 | 打开目标页面帧耗时明细 |
| 网络失败率 / TTFB | 域名、地区、运营商、网络类型 | 切备用域名或关闭实验配置 |
| SDK 自监控 | 上报成功率、积压文件、丢弃数 | 暂停新增采集项，保留 Crash / ANR 摘要 |

Android Vitals 的 28 天口径适合看发布后的外部质量变化；灰度门禁要更快，通常按 15 分钟、1 小时、4 小时几个窗口观察。短窗口只用于发现明显事故，是否扩大灰度仍要结合样本量、设备分布和业务指标。

### 回归归因：把指标变化拉回证据

性能指标变差后，处理顺序是：锁定范围、找变更、取样本、补 Trace、决定处置。

以启动 P95 上升为例，排查不要从“谁改了启动代码”开始，而是先按版本、机型、系统、渠道、用户数据量分组。低端机和重度用户变差，优先看磁盘 I/O、数据库迁移、SharedPreferences、资源加载和类加载。所有机型同幅度变差，优先看 Application、ContentProvider、初始化任务编排和远程配置。只有某个渠道变差，优先看加固、渠道包、动态加载和资源变体。

以卡顿回归为例，慢会话比例上升后要先定位页面和操作，再看主线程长任务、GC、锁等待、I/O、网络等待和渲染阶段。卡顿监控只给堆栈还不够，最好同时带 CPU、线程状态、内存、I/O 和网络摘要。参考素材里的卡顿现场分析思路可以借鉴为证据清单，但正文实现要以团队已有 APM 和 Perfetto 能力为准。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md][结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md]

### 性能回归的止损规则

门禁发现退化后，处置动作要提前写好：

1. 退化只在实验组出现：把实验比例降到 0，保留样本和配置版本。
2. 退化只在某个机型或系统出现：停止对该分组放量，开启目标日志和诊断指令。
3. 退化覆盖大部分灰度用户：暂停灰度，回滚远程配置，必要时发修复包。
4. 退化来自监控 SDK 本身：立即关闭新增采集项，保留 Crash / ANR / 启动摘要。

回滚后要继续观察同一批指标。指标恢复只能说明处置有效，不等于根因已经找到。证据包和变更记录要进入问题单，避免下一次改动重新触发。

## 线上疑难问题排查案例

线上疑难问题的共同特点是现场短、复现弱、责任边界不清。排查时不要按模块争论，先把证据补齐。26.5 节已经给出通用方法，本节用三个案例说明证据如何组织。

### 案例一：文件下载卡在 99%

用户反馈“文件下载到 99% 后无法继续”。这个现象可能来自网络、服务端、磁盘、断点续传协议、校验逻辑或 UI 状态。排查入口不要直接改下载逻辑，先让证据覆盖每个分支。

证据包字段：

| 证据 | 要采集的字段 | 用来排除什么 |
| --- | --- | --- |
| 请求阶段 | DNS、connect、TLS、TTFB、body 下载耗时、重试次数 | 网络连接和服务端响应问题 |
| HTTP 信息 | URL 模板、range header、status code、content-length、etag、错误码 | 断点续传协议问题 |
| 本地文件 | 已写入字节数、临时文件路径 hash、剩余空间、rename 结果 | 磁盘不足、权限、文件落盘失败 |
| 校验阶段 | hash 类型、校验耗时、期望 hash、实际 hash 摘要 | 完整性校验失败 |
| UI 状态 | progress 来源、最近一次进度事件、按钮状态 | 下载完成但 UI 未更新 |
| 关联 ID | `request_id`、`download_id`、`session_id`、服务端日志索引 | 端到端串起证据 |

如果同一地区、同一运营商集中发生，先看网络和 CDN；如果同一文件集中发生，先看服务端 range / etag / content-length；如果低存储空间设备集中发生，先看临时文件写入和 rename；如果只有某版本发生，回查下载组件和 UI 状态机变更。

止损动作也要按证据分支设置。服务端异常时切备用 CDN；磁盘不足时提示清理并保留断点；UI 状态错误时让下载完成事件以本地文件校验结果为准；校验失败时删除临时文件并重新拉取。每个动作都要带上配置版本，便于观察是否生效。

### 案例二：低端机启动 P95 上升

灰度后发现低端机冷启动 P95 上升，但高端机变化不明显。这个分布通常说明问题和 CPU、I/O、内存或用户本地数据量相关。排查重点应落到启动阶段划分和重度用户分桶。

证据包字段：

- 启动阶段：进程创建、Application、ContentProvider、首页 Activity、首帧、首页数据 ready、TTFD。
- 本地数据：数据库大小、SharedPreferences 条目数、缓存目录大小、首屏资源文件读取摘要。
- 线程与调度：主线程长任务、后台初始化任务数量、线程池排队、Binder 调用耗时。
- I/O：主线程读写次数、最大连续读写时长、文件类型、buffer 大小。
- 用户分桶：低内存设备、低存储空间、重度用户、首次安装、覆盖安装、升级后首次启动。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 13.md]

排查路径建议从分桶开始。只有重度用户变差，优先看数据库迁移、缓存扫描、SharedPreferences 全量解析和首页数据预加载。只有覆盖安装后首次启动变差，优先看 dexopt、资源解压、配置迁移和兼容逻辑。所有低端机变差，优先看 Application 同步初始化、线程池竞争、主线程 I/O 和启动阶段 Binder 等待。

处置动作可以分成短期和长期。短期用远程配置关闭非必要初始化、延后低价值预加载、降低首屏资源质量或跳过非关键迁移；长期把启动任务分级，给 CI 增加低端机 Macrobenchmark，给线上 APM 增加重度用户分桶。

### 案例三：用户投诉支付页卡 3 秒

卡顿投诉不能只看一条主线程堆栈。用户感知的 3 秒可能是主线程运行长任务，也可能是锁等待、Binder 等待、GC、I/O 抖动、网络等待、渲染阶段过载或系统负载过高。

证据包字段：

| 方向 | 关键证据 | 处理提示 |
| --- | --- | --- |
| 主线程长任务 | Looper 消息耗时、方法耗时、当前页面、操作路径 | 先看业务代码、序列化、图片解码、布局测量 |
| 锁等待 | 主线程状态、持锁线程堆栈、等待对象摘要 | 区分 Java 锁、native mutex、数据库锁 |
| I/O | 文件路径类型、读写大小、buffer、线程、连续耗时 | 主线程 I/O 直接进入整改；后台 I/O 看锁和资源竞争 |
| GC / 内存 | GC 次数、pause、分配热点、内存水位 | 结合 23.x 章节定位对象 churn 或图片内存 |
| 渲染 | FrameTimeline、UI thread、RenderThread、SurfaceFlinger | 详见 22.x 和 13.2 节 |
| 系统负载 | CPU busy、线程 runnable、iowait、温控状态 | 区分 App 自身耗时和设备环境 |

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md]

这个案例重点是“补现场”。如果只保留发生卡顿时的一个堆栈，容易把采样点当根因。更稳的做法是保留卡顿窗口前后的时间线：用户点击、网络请求、数据库访问、主线程消息、GC、I/O 和帧信息。能抓 Perfetto 就用 Perfetto；不能抓系统 Trace 时，端侧至少保留同一时间窗的轻量事件。

Android 15 (API 35)+ 的 `ProfilingManager.requestProfiling()` 支持 App 触发 profiling session，官方文档列出 system trace、Java heap dump、heap profile、stack sampling 等类型；采集可能受 rate limiter 限制。Android 16 引入 system-triggered profiling，应用可注册 cold start fully drawn、ANR 等触发器，由系统管理采集并把结果交给 App。这些新能力适合补齐“线上 Trace 难采”的缺口，但不能替代日常轻量埋点。APM 要先用 Metrics 发现受影响分组，再对目标用户或目标触发器采集 profile，避免把系统级采集当全量监控。

### 案例四：后台耗电投诉无法复现

耗电问题的难点是用户现场常常只剩一张系统耗电截图。没有调用栈、没有时间线、没有后台任务记录，团队只能猜。排查要把后台行为拆成系统关心的资源：WakeLock、Alarm、后台网络、定位、传感器、Wi-Fi 扫描、JobScheduler / WorkManager。

证据包字段：

- WakeLock：名称、持有时长、调用栈摘要、前后台状态、充电状态。
- Alarm：类型、触发次数、间隔、是否唤醒设备、业务来源。
- 后台网络：请求域名、字节数、失败重试、网络类型、触发任务。
- 定位 / 传感器：采样频率、前后台状态、业务场景、关闭原因。
- 任务调度：WorkManager / JobScheduler 任务名、约束条件、执行窗口、失败重试。
- 用户环境：电量、充电状态、系统省电模式、App standby bucket、设备温度。

处置路径按“后台是否必要”判断。用户无感知的后台轮询、重复唤醒、失败重试和无约束任务优先关闭；用户可感知的导航、通话、播放、下载要保留前台服务通知和明确场景标记。修复后同时看 Android Vitals、电量投诉、后台任务次数和业务成功率，避免只压低耗电却损伤功能。

## Android 版本化诊断能力表

26.5 的 research-gaps 已记录：线上 Trace 与证据包模板需要按 Android 版本拆分官方诊断入口。本节把它放进案例集，作为后续排障 Runbook 的版本表。

| Android 版本 | 可用能力 | 适用案例 | 边界 |
| --- | --- | --- | --- |
| Android 10 (API 29)+ | Perfetto / on-device tracing 工具链 | 本地复现、测试设备、人工协助 trace | 发布版用户设备上通常不能随意抓完整系统 Trace |
| Android 11 (API 30)+ | `ApplicationExitInfo` 历史退出原因 | Crash、ANR、LMK 退出原因分类 | 历史记录可能被循环缓冲区覆盖 |
| Android 12 (API 31)+ | `ApplicationExitInfo.getTraceInputStream()` | Native crash tombstone protobuf 补偿证据 | 仅 `REASON_CRASH_NATIVE` 可用；tombstone 可能因全局 circular buffer 覆盖返回 null |
| Android 15 (API 35)+ | `ProfilingManager.requestProfiling()` | 目标用户或目标场景的系统 trace / heap / stack 采集 | 有 rate limiter，不适合全量常驻采集 |
| Android 16 (API 36) | system-triggered profiling / `ProfilingTrigger` | cold start fully drawn、ANR 等系统触发采集 | 触发类型和支持范围按平台版本变化，接入前要做能力检测 |

[来源: intake/research-gaps.md]

这个表的用法是降级：高版本设备走系统能力，低版本设备走 App 内日志、轻量 trace、用户反馈和人工 bug report。Runbook 里要把“采不到系统 Trace 时的替代证据”写清楚，否则排障会卡在权限和版本上。

## 扩展：Runbook 模板

每个高频事故类型都要有一份 Runbook。模板如下：

| 模块 | 内容 |
| --- | --- |
| 触发条件 | 指标阈值、告警窗口、分组口径、是否需要人工确认 |
| 影响面判断 | 版本、机型、系统、渠道、地区、网络、实验组 |
| 必带证据 | Metrics、日志、Trace、Crash / ANR report、服务端日志、发布记录 |
| 版本能力 | Android 10-14、15、16 分别能采哪些证据 |
| 处置动作 | 暂停灰度、关闭配置、降级功能、切备用域名、发修复包 |
| 验证方式 | 哪些指标恢复、观察多长时间、是否需要对照组 |
| 防复发 | CI 门禁、静态检查、APM 字段补充、告警规则调整 |

Runbook 要放在告警旁边。告警只告诉团队发生了什么，Runbook 告诉值班同学下一步怎么拿证据和止损。

## 小结

APM、性能回归和线上排障不是三套孤立系统。APM 提供统一事件模型和证据存储，回归门禁把质量问题挡在发布路径上，疑难问题 Runbook 把事故处理变成固定动作。体系越早把字段、采样、证据包和处置动作写清楚，事故发生时越少靠临场猜测。

## 参考资料

- Android Vitals: https://developer.android.com/topic/performance/vitals
- Macrobenchmark metrics: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics
- App-driven profiling: https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture
- Trigger-based profiling: https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture
- Android NDK debug / ApplicationExitInfo native crash tombstone: https://developer.android.com/ndk/guides/debug
