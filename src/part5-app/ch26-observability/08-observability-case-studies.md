---

title: "可观测性案例集"
chapter: "26.8"
section: "26.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
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

可观测性体系要在事故发生后给出可核对的时间线、影响范围和诊断证据。四个案例回答三个工程问题：团队从零建设 APM 时怎样确定采集边界，性能回归怎样进入 CI 和灰度门禁，线上疑难问题怎样关联指标、日志、Trace 与发布记录。架构分层和排障步骤见 26.1 和 26.5。

平台上界为 Android 17 / API 37，源码标签为 `android-17.0.0_r1`。涉及 `ApplicationExitInfo` 与 `ProfilingManager` 的结论按该标签和公开 API 复核。案例中的事件模型、服务端分析和 Runbook 属于应用基础设施设计，不依赖 Linux 内核专有实现，因此不附加 kernel tag。

## 从零搭建 APM 体系

APM 的第一版不必覆盖全部指标，但要让三类常见事故留下证据：Crash 与 ANR 能关联线程和业务场景，启动与卡顿能关联页面和版本，网络与 I/O 能关联请求阶段和设备环境。26.1 节已经说明 Metrics、Logs、Traces 的职责，本案例把它转换为分阶段交付路线。

### 阶段 0：统一事件模型与数据边界

APM 平台先收敛字段，再接入模块。每个事件至少带这组公共字段：

| 字段 | 用途 | 缺失后的排障代价 |
| --- | --- | --- |
| `event_id` | 服务端去重、重试幂等 | 重传后指标被放大 |
| `session_id` | 关联一次用户会话内的事件 | Crash、日志、网络样本无法按时间线对齐 |
| `trace_id` / `request_id` | 关联端到端请求 | 端侧错误和服务端日志无法匹配 |
| `scene_id` | 标识启动、支付、播放、下载、页面刷新等场景 | 只能看全局指标，看不到业务入口 |
| `build_id` / `config_version` | 关联构建产物、远程配置和实验 | 无法判断异常与哪次变更同时出现 |
| `device_model` / `android_version` / `abi` | 识别机型、系统和架构差异 | 设备或 ABI 问题会被混合分布隐藏 |
| `event_time` / `ingest_time` | 区分设备发生时间与服务端到达时间 | 延迟上报会被误判为刚发生的异常 |
| `sampling_unit` / `inclusion_probability` / `policy_version` | 说明按用户、会话还是事件采样，以及单条事件被采中的概率 | 无法正确加权，也分不清未发生与未采集 |
| `schema_version` | 固定字段与单位解释 | 历史数据可能被新计算逻辑错误解析 |

这些 ID 不应直接包含账号、手机号、URL query、文件名或其他个人数据。进入事件模型前要确定字段白名单、脱敏方式、访问控制、端侧与服务端保留时间、用户删除路径和大文件配额。Trace、heap dump、tombstone 与日志比聚合指标更敏感，应使用更小的采样范围和独立权限。

事件 schema 需要版本化。字段改名、单位变化、采样单元变化和枚举重定义都要生成新版本；服务端查询按 schema version 解码，避免把不同口径拼成同一条趋势。

### 阶段 1：接入高价值信号

第一批接入 Java Crash、Native crash、ANR、启动、关键页面慢帧、关键请求失败和采集 SDK 自监控。Crash 与 ANR 是低频高价值事件；启动、帧和网络属于高频事件，必须在事件级、会话级或用户级采样之间作出明确选择，不能因“价值高”而默认全量上报。

Crash/ANR 摘要可包含异常类型、主线程和故障线程堆栈、进程名、前后台状态、最近场景、受控操作记录、内存摘要、线程数、文件描述符数量与剩余空间。操作记录只保存允许的事件名和枚举参数，不能把输入文本、令牌或完整请求体写入诊断包。

Native signal handler 内只能使用异步信号安全操作，不适合执行分配、压缩、网络或复杂文件 I/O。若接入 Native crash SDK，需要验证它与 Android debuggerd/tombstone、其他 handler 和进程重启策略的兼容性，并在服务端保存 build ID 与符号文件版本。

Android 11 / API 30 起，可用 `ActivityManager.getHistoricalProcessExitReasons()` 读取近期进程退出记录。`ApplicationExitInfo.getTraceInputStream()` 同样从 API 30 提供，常见内容是 ANR trace；Android 12 / API 31 起，`REASON_CRASH_NATIVE` 还可返回 protobuf tombstone。该流可能为 `null`，ANR 恢复后又因其他原因退出时，先前 ANR trace 也可能附在后一次记录上。平台必须同时保存 actual reason 与 trace 类型，不能看到非空流就把事件改写为 ANR 或 Native crash。

启动事件记录进程启动、`Application`、首个 `Activity`、首帧、业务 ready 与 TTFD 等阶段；卡顿事件记录页面、操作、帧分布、主线程长任务、GC 与 Binder 等待摘要；网络事件记录 DNS、connect、TLS、TTFB、总耗时、HTTP 状态和错误类别。日常事件保持轻量，只有命中预定义诊断条件时才申请 Trace 或上传更详细的受控日志。

### 阶段 2：让采集和上传不干扰业务线程

上报组件经常败在采集和上报本身拖慢业务；网络不可用只是其中一类故障。可用的第一版需要满足四条约束：

- 高频采集入口使用有界、低分配路径；主线程不做同步文件写入、压缩或网络请求。Crash 等极端路径另行设计最小可靠写入。
- 内存队列有上限，队列满时保留 Crash、ANR、启动和告警触发事件，丢弃普通性能样本，并把丢弃计数写入 SDK 自监控。
- 本地文件按优先级分片，Crash/ANR 摘要与普通批次分开管理；Perfetto trace、HPROF、tombstone 和日志包使用独立配额、加密与过期策略。
- 上传调度考虑优先级、网络约束、前后台状态和服务端退避。摘要与大文件分离后，即使大文件未上传，也能先知道事件存在。

队列溢出、写盘失败、解密失败、配额淘汰、上传响应、重试次数和服务器拒绝都要进入 SDK 自监控。否则“线上没有事件”可能只是采集链路自身故障。

### 阶段 3：建立能处理事故的看板

第一张看板要支持从聚合指标回到受控样本，并清楚显示口径：

| 看板区域 | 必要能力 | 处理动作 |
| --- | --- | --- |
| 版本质量 | Crash/ANR 用户率与事件率、启动分位值、慢会话比例、关键请求失败率 | 判定当前版本是否暂停灰度 |
| 机型分布 | 按设备、系统、ABI、渠道分组 | 判断是否是厂商、系统或架构问题 |
| 场景排行 | 启动、支付、播放、下载、首页刷新等场景 | 找到用户感知路径 |
| 样本列表 | 从指标进入已授权的事件、日志、Trace 与发布记录 | 补齐证据包 |
| 数据健康度 | 采样策略、生成/写盘/上传数量、丢弃数、延迟水位、schema/config 版本 | 判断当前窗口能否使用 |

Android vitals 可作为外部质量信号。Play 使用最近 28 天数据评估应用质量，并提供 user-perceived crash/ANR、启动、渲染、耗电和低内存等维度。自建 APM 可补充业务场景、灰度批次、配置版本、渠道与实验分组，但两边的用户范围、分母、时间窗口和延迟不同，不能直接合并成一个指标。

### 从零搭建的验收标准

第一版 APM 上线后，用三类演练验收：

1. 在专用测试包制造受控异常和测试 Crash，确认端侧写入、下次启动补传、符号化、聚合、告警和样本查询均可用。
2. 在测试环境给一个已标记的启动阶段注入已知延迟，确认阶段指标的变化与注入量相符，并能定位 build、场景和设备。
3. 让测试服务返回预设 HTTP 错误或超时，确认端侧 `request_id` 能关联服务端日志，且 URL、header 和错误正文经过脱敏。

验收还要包含失败演练：本地配额耗尽、离线重试、服务端限流、schema 不兼容、时钟偏差和删除请求。只有成功路径的演示不能证明采集链路在事故期间仍可用。

## 性能回归检测实践

性能回归要覆盖两条证据线：候选包的可重复退化，以及发布后的真实用户退化。CI 能控制设备、场景和编译状态，适合做基准测试；线上能覆盖机型、网络、数据量和 OEM 差异，适合发现分布尾部问题。两条线的样本来源不同，不能用线上 P95 与实验室的少量迭代直接比较。

### CI 门禁：用固定场景测稳定指标

CI 门禁只测少量稳定场景，目标是判断当前候选包相对固定基线是否退化。适合纳入门禁的场景包括冷启动、首页首屏、核心列表滚动、搜索结果、支付或播放入口、数据库迁移和图片密集页面。每个场景要固定测试数据、账号状态、设备、系统 build fingerprint、刷新率、编译模式和 Baseline Profile。

Macrobenchmark 适合处理这些任务。`StartupTimingMetric` 提供 `timeToInitialDisplayMs`，并在应用正确调用 `reportFullyDrawn()` 时提供 `timeToFullDisplayMs`；后者在 Android 10 / API 29 及更早版本可能不可用。官方输出以多次启动的 minimum、median 和 maximum 为主。少量迭代不足以稳定估计启动 P95/P99，不要从小样本强行生成尾部分位门禁。

`FrameTimingMetric` 输出帧分布的 P50/P90/P95/P99。`frameDurationCpuMs` 是 UI Thread 与 RenderThread 的 CPU 生产时间；`frameOverrunMs` 只在 Android 12 / API 31 及以上可用，正值表示错过 deadline。二者语义不同，不能共享阈值。线上慢帧指标还受刷新率、交互时段和 FrameTimeline 口径影响，应在各自系统内比较。

门禁结论可以分为三档：

- **阻断**：安全或稳定性预算被越过，或关键场景出现可重复且超过预设变化预算的退化。构建不能进入灰度。
- **人工复核**：效应方向不利，但不确定区间较宽，或测试环境出现温控、后台干扰等异常。复核单附上单次迭代 Trace 与变更列表。
- **灰度观察**：线下变化未达到阻断条件，但涉及高风险模块。发布单增加对应线上指标与停止条件。

基线至少区分固定 green release 与近期稳定趋势。固定基线用于发现累计漂移，近期趋势用于识别设备环境变化。基线升级必须留下原因和前后报告，不能因为当前构建失败就移动比较对象。

### 灰度门禁：按数据成熟度观察

灰度阶段要回答“真实用户有没有变差”。灰度数据的优势是覆盖真实设备、真实网络、真实数据量；缺点是用户样本可能有偏，指标会受地域、渠道、活跃度影响。灰度门禁要按同质分组比较，不要把全量均值当结论。

灰度观察表建议包含：

| 指标 | 观察维度 | 触发动作 |
| --- | --- | --- |
| user-perceived crash / ANR | 版本、设备、系统、渠道、前后台 | 暂停灰度，抽样 Crash/ANR 证据包 |
| 启动 TTID / TTFD P90/P95 | 启动类型、入口、设备档位、本地数据量 | 对目标分群启用受控启动诊断 |
| 慢会话比例 / frame overrun | 页面、设备、刷新率、实验组 | 获取目标页面的帧摘要或受控 Trace |
| 网络失败率 / TTFB | 域名、地区、运营商、网络类型 | 切备用域名或关闭实验配置 |
| 数据健康度 | 采样策略、上传成功率、积压、丢弃与延迟水位 | 将结果标为不可判定并暂停扩量 |

观察窗口不能直接复制固定分钟数。它要覆盖指标事件率、客户端更新和启动速度、上传延迟、服务端聚合水位及一个有代表性的业务周期。严重 Crash、ANR 或启动失败可以提前停止发布；普通性能变化需要报告样本量、设备构成和效应区间。

### 回归归因：把指标变化拉回证据

性能指标变差后，依次确定数据是否可用、影响范围、同时发生的变更、代表样本和可追加的 Trace，再决定处置。

以启动 P95 上升为例，先确认启动类型、入口和版本用户构成没有变化，再按设备、系统、渠道和本地数据量分组。资源受限设备与重度用户变差时，检查磁盘 I/O、数据库迁移、`SharedPreferences`、资源加载和类加载。多数设备同方向变化时，检查 `Application`、`ContentProvider`、初始化调度和远程配置。只有某个渠道变差时，核对渠道构建、加固、动态加载和资源变体。

以卡顿回归为例，慢会话比例上升后要定位页面和操作，再看主线程长任务、GC、锁等待、I/O、网络依赖和渲染阶段。单个采样堆栈只说明采样时刻，不能独立证明根因。证据包应对齐 CPU、线程状态、内存、I/O、网络和帧时间线。

### 性能回归的止损规则

门禁发现退化后，处置动作要提前写好：

1. 退化只在实验变体出现：停止实验或通过受支持的回退机制关闭变体，保存 assignment、激活与配置版本。Firebase A/B Testing 的变体权重在实验开始后不能修改，不能假定可以把原实验权重直接改成零。
2. 退化集中在设备或系统分群：若发布渠道不能按该分群暂停，就停止整个 staged rollout，并用远程配置对受影响分群关闭可选功能。
3. 退化覆盖大部分灰度用户：暂停发布，回退相关服务端配置，准备更高 `versionCode` 的修复包。
4. 退化来自监控 SDK：关闭新增采集与大文件诊断，保留经过容量验证的 Crash、ANR、退出与启动摘要。

处置后继续观察同一口径的指标与有效暴露漏斗。指标随动作恢复说明处置与症状相关，根因仍需代码、Trace、复现或对照证据确认。证据包和变更记录进入问题单，并把遗漏场景加入下一次门禁。

## 线上疑难问题排查案例

线上疑难问题常见的困难是现场保存时间短、复现概率低、跨端依赖多。26.5 节已经给出通用步骤，下面四个案例说明证据怎样按共同时间轴组织。案例只给候选分支；具体事故必须依据采集结果排除，不能把“常见原因”写成根因。

### 案例一：文件下载卡在 99%

用户反馈“文件下载到 99% 后无法继续”。99% 可能表示末段正文未收到，也可能表示字节已收齐但正在 flush、校验、解压、rename 或更新数据库；还可能只是 UI 的取整和状态机错误。排查时要先定义进度值的分子、分母和状态，再让证据覆盖网络、服务端、磁盘、断点续传、校验和 UI 分支。

证据包字段：

| 证据 | 要采集的字段 | 用来排除什么 |
| --- | --- | --- |
| 请求阶段 | DNS、connect、TLS、TTFB、正文读取、重试与取消时间 | 网络连接和服务端响应问题 |
| HTTP 信息 | 脱敏 URL 模板、`Range`、状态码、`Content-Range`、`Content-Length`、`ETag` | 断点续传和响应一致性问题 |
| 本地文件 | 期望/已接收/已写入字节、文件系统错误、剩余空间、flush/close/rename 结果 | 磁盘不足、写入失败或收尾阶段卡住 |
| 校验阶段 | 算法版本、校验耗时、期望摘要、实际摘要、解压状态 | 完整性或归档处理失败 |
| UI 状态 | progress 的计算来源、下载状态、最近一次状态转换、观察者生命周期 | 后台已完成但 UI 未更新 |
| 关联 ID | `request_id`、`download_id`、`session_id`、服务端日志索引 | 关联端侧、存储与服务端证据 |

同一地区或运营商集中时，把网络和 CDN 作为优先候选；同一文件集中时，核对服务端 Range、ETag 与长度语义；低存储设备集中时，检查临时文件写入和原子替换是否位于同一文件系统；只有某版本出现时，回查下载组件、持久化 schema 和 UI 状态机变更。分群只用于排序候选，不能单独证明原因。

临时处置也要匹配证据：服务端或 CDN 异常时使用经过演练的备用路径；磁盘不足时停止继续写入，给出可操作提示并按安全策略保留或删除临时文件；UI 状态错误时以持久化下载状态与校验结果恢复界面；校验失败时隔离损坏文件，并依据重试预算决定是否重新下载。每个动作都记录配置版本和生效时间。

### 案例二：低端机启动 P95 上升

灰度后发现资源受限设备的冷启动 P95 上升，而高性能设备变化不明显。该分布提示 CPU、I/O、内存压力或本地数据量值得优先检查，但也可能来自版本用户构成、刷新率、启动入口或上报缺失。排查前先验证分桶和数据健康度。

证据包字段：

- 启动阶段：进程创建、Application、ContentProvider、首页 Activity、首帧、首页数据 ready、TTFD。
- 本地数据：数据库大小、SharedPreferences 条目数、缓存目录大小、首屏资源文件读取摘要。
- 线程与调度：主线程长任务、后台初始化任务数量、线程池排队、Binder 调用耗时。
- I/O：主线程读写次数、长 I/O 区间、文件类型、读写量和缓存策略。
- 用户分桶：低内存设备、低存储空间、重度用户、首次安装、覆盖安装、升级后首次启动。

只有重度用户变差时，优先检查数据库迁移、缓存扫描、`SharedPreferences` 解析和首页数据预加载。只有覆盖安装后的首次启动变差时，核对应用迁移、资源准备、运行时编译状态和版本兼容逻辑。多数资源受限设备同时变差时，检查 `Application` 同步初始化、线程池竞争、主线程 I/O 和启动阶段 Binder 等待。

短期可以用远程配置关闭可选初始化、延后不影响首帧的预加载或减少非关键首屏工作。数据库 schema 和数据一致性要求的迁移不能跳过；若要移出首帧路径，必须先设计兼容读写与失败恢复。长期措施包括划分启动任务优先级、在固定资源受限设备上运行 Macrobenchmark，并在线上保留本地数据量分群。

### 案例三：用户投诉支付页卡 3 秒

卡顿投诉不能只看一条主线程堆栈。用户感知的三秒可能来自主线程长任务，也可能是锁等待、Binder 等待、GC、I/O、同步等待网络结果、渲染阶段过载或系统负载。

证据包字段：

| 方向 | 关键证据 | 处理提示 |
| --- | --- | --- |
| 主线程长任务 | Looper 消息耗时、方法耗时、当前页面、操作路径 | 先看业务代码、序列化、图片解码、布局测量 |
| 锁等待 | 主线程状态、持锁线程堆栈、等待对象摘要 | 区分 Java 锁、native mutex、数据库锁 |
| I/O | 脱敏后的文件类别、读写量、线程和时间区间 | 主线程 I/O 优先移出交互路径；后台 I/O 还要检查锁和资源竞争 |
| GC / 内存 | GC 次数、pause、分配热点、内存水位 | 结合 23.x 章节定位对象 churn 或图片内存 |
| 渲染 | FrameTimeline、UI thread、RenderThread、SurfaceFlinger | 详见 22.x 和 13.2 节 |
| 系统负载 | CPU 调度、线程 runnable 区间、块 I/O、频率和温控状态 | 区分 App 工作与设备环境 |

如果只保留卡顿时的一次堆栈采样，容易把采样点误当成根因。需要对齐卡顿前后的用户点击、网络请求、数据库访问、主线程消息、GC、I/O 与帧时间线。可用 Perfetto 时优先分析调度、Binder、FrameTimeline 和自定义 Trace；无法取得系统 Trace 时，端侧至少保存同一单调时钟上的轻量事件，并标明观测缺口。

Android 15 / API 35 起，`ProfilingManager.requestProfiling()` 可以申请 system trace、Java heap dump、heap profile 和 stack sampling。请求受系统 rate limiter 管理，不保证执行；结果经过裁剪，只包含与请求进程相关的信息。应用进程在回调前死亡时，系统会在应用下次启动并注册通用 listener 后尝试重新交付结果。

Android 16 / API 36 增加 `addProfilingTriggers()`，首批公开触发器包括 `TRIGGER_TYPE_APP_FULLY_DRAWN` 与 `TRIGGER_TYPE_ANR`。ANR trigger 表示系统已识别 ANR、尚未尝试终止应用，并不表示进程最终因 ANR 被杀。触发式采集依赖系统恰好在运行后台 Trace、系统与应用限流均允许，因此注册成功也不能保证收到产物。

Android 17 / API 37 继续增加 `TRIGGER_TYPE_COLD_START`、`TRIGGER_TYPE_OOM`、`TRIGGER_TYPE_ANOMALY`、`TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE` 和 `TRIGGER_TYPE_APP_COMPAT`。其中 cold start 会生成新启动的 system trace 与 stack sampling，持续到 `reportFullyDrawn()`，未报告时使用系统默认停止时间；OOM trigger 返回 Java heap dump，并要求自定义 `UncaughtExceptionHandler` 继续调用默认 handler。不同 trigger 的产物类型和失败条件不同，APM 要保存 trigger type、`ProfilingResult` error code、tag、请求/触发时间和产物路径，不能把“已注册”记为“已采到”。

这些能力适合为低频目标事件补充系统证据，不能替代日常轻量指标。大文件上传前要检查用户授权、网络与电量约束、端侧配额、保留期限和服务端访问控制。

### 案例四：后台耗电投诉无法复现

耗电问题的难点是用户现场常常只剩一张系统耗电截图。没有调用栈、没有时间线、没有后台任务记录，团队只能猜。排查要把后台行为拆成系统关心的资源：WakeLock、Alarm、后台网络、定位、传感器、Wi-Fi 扫描、JobScheduler / WorkManager。

证据包字段：

- WakeLock：名称、持有时长、调用栈摘要、前后台状态、充电状态。
- Alarm：类型、触发次数、间隔、是否唤醒设备、业务来源。
- 后台网络：请求域名、字节数、失败重试、网络类型、触发任务。
- 定位 / 传感器：采样频率、前后台状态、业务场景、关闭原因。
- 任务调度：WorkManager / JobScheduler 任务名、约束条件、执行窗口、失败重试。
- 用户环境：电量、充电状态、系统省电模式、App standby bucket、设备温度。

处置路径按后台工作的用户价值与平台约束判断。没有明确用户价值的轮询、重复唤醒、无限重试和缺少约束的任务应停用或改为系统调度；导航、通话、播放、下载等用户可感知任务要满足对应的前台服务类型、权限和通知要求。修复后同时观察 Android vitals、后台任务次数、唤醒时长、业务成功率和数据健康度，避免以功能失败换取较低耗电。

## Android 版本化诊断能力表

| Android 版本 | 可用能力 | 适用案例 | 边界 |
| --- | --- | --- | --- |
| Android 10 / API 29+ | Perfetto 与 on-device tracing 工具链 | 实验室复现、测试设备、用户明确协助的诊断 | 普通发布版应用不能任意取得完整系统 Trace |
| Android 11 / API 30+ | `ApplicationExitInfo` 与 ANR `getTraceInputStream()` | 查询近期退出原因，补充 ANR trace | 历史与 trace 分别受环形缓冲区影响；流可能为 `null` |
| Android 12 / API 31+ | Native crash tombstone protobuf | 为 `REASON_CRASH_NATIVE` 补充 Native tombstone | 与 ANR trace 格式不同，读取后必须按 reason/type 解析 |
| Android 15 / API 35+ | `ProfilingManager.requestProfiling()` | 目标场景的 system trace、heap dump/profile、stack sampling | 请求受限流且不保证执行，结果经过裁剪 |
| Android 16 / API 36 | `ProfilingTrigger`：fully drawn、ANR | 采集事件前的后台 Trace 快照 | 只有后台 Trace 正在运行且限流允许时才可能产生结果 |
| SDK extension 36.1 | 请求当前后台 Trace；force-stop、Recents、Task Manager 等 trigger | 用户终止与主动请求的诊断 | 使用 `SdkExtensions` 检查扩展版本，不能只判断 `SDK_INT` |
| Android 17 / API 37 | cold start、OOM、anomaly、excessive CPU kill、app compat triggers；`ApplicationExitInfo.getAnrInfo()` | 启动、OOM、兼容性与结构化 ANR 分类 | 每种 trigger 的产物与条件不同；`AnrInfo` 只在 reason 为 ANR 时可能存在 |

能力选择要按运行时检测。高版本设备优先使用公开系统能力，低版本设备使用 App 内轻量事件、受控日志、人工 bug report 和实验室复现。系统 API 返回 `null`、限流或没有命中后台 Trace 都是正常结果，Runbook 必须写明替代证据，不能把“没有系统产物”等同“问题没有发生”。

## 扩展：Runbook 模板

每个高频事故类型都要有一份 Runbook。模板如下：

| 模块 | 内容 |
| --- | --- |
| 触发条件 | 指标阈值、告警窗口、分组口径、是否需要人工确认 |
| 影响面判断 | 版本、机型、系统、渠道、地区、网络、实验组 |
| 必带证据 | Metrics、日志、Trace、Crash / ANR report、服务端日志、发布记录 |
| 版本能力 | Android 10-14、15、16/extension 36.1、17 分别能采哪些证据 |
| 处置动作 | 暂停灰度、关闭配置、降级功能、切备用域名、发修复包 |
| 验证方式 | 指标定义、数据成熟条件、效应区间、是否需要对照组 |
| 防复发 | CI 门禁、静态检查、APM 字段补充、告警规则调整 |

Runbook 要与告警规则使用同一个版本号。告警说明系统观察到了什么，Runbook 说明值班工程师后续需取得哪些证据、谁有权执行外部动作、怎样确认处置结果。涉及远程日志、heap dump、Trace 或用户数据时，还要列出权限、脱敏、保留和删除要求。

## 小结

APM、性能回归和线上排障共享同一套事件身份、时间语义、采样说明与发布记录。CI 识别可重复退化，灰度监控覆盖真实分布，Runbook 把告警映射为证据与处置动作。Android 17 增加了 cold start、OOM、兼容性等 profiling triggers，也为 ANR 提供结构化 `AnrInfo`；这些接口都受可用性、限流和隐私边界约束，不能替代持续的轻量采集。

## 参考资料

- [AOSP Android 17：`ApplicationExitInfo`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP Android 17：`ProfilingManager`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [AOSP Android 17：`ProfilingTrigger`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [AOSP Android 17：`ProfilingService`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java)
- [Android vitals](https://developer.android.com/topic/performance/vitals)
- [Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [App-driven profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/how-to-capture)
- [Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [`ProfilingManager` API](https://developer.android.com/reference/android/os/ProfilingManager)
- [`ProfilingTrigger` API](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [`ApplicationExitInfo` API](https://developer.android.com/reference/android/app/ApplicationExitInfo)
