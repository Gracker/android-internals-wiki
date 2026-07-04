---
title: "从采集到治理的反馈回路"
chapter: "15.9"
section: "15.9"
status: finalized
drafted_date: "2026-04-21"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) – Android 17 (API 37)"
last_verified: "2026-04-22"
last_verified_against: "AndroidX metrics-performance 1.0.0 Maven artifact (JankStats confirmed); AOSP android-17.0.0_r1 /base/core/java/android/app/ActivityManager.java (ApplicationExitInfo 相关方法, API 30+)"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
tags: [observability, apm, pipeline, governance, monitoring]
related_chapters: ["7.1", "8.1", "9.1", "14.12", "15.3", "15.5", "15.6", "15.10"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: 2026-07-04
reviewed_by: openclaw-task6
last_task6_at: 2026-07-04T13:09:00+08:00
task9_state: reviewed
repaired_date: "2026-04-22"
repaired_by: "codex"
task9_result: pass-tech-review
task9_reviewed_date: "2026-07-04"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-04T18:20:00+08:00"
last_task6_audit: "2026-07-04"
last_task6_audit_log: "logs/review/2026-07-03-07-audit.md"
last_task9_audit: "2026-07-04"
last_task9_idle_audit: "2026-07-04"
task2b_state: finalized
task2b_result: finalized
task2b_verifier_note: "2026-07-04T18:20:00+08:00 Auto-promoted to finalized: Task9 pass-tech-review (0 P0/P1), Task6 pass-light-edit, queue empty for this section"
last_task2b_rework_at: "2026-07-04T12:52:06+08:00"
last_task2b_rework_log: "Task2B 2026-07-04: 按 Task9 Deep Review 问题单修复 JankStats API 完整声明、异常→Backlog SLA 映射、版本声明一致性、多租户数据隔离、告警阈值参考。"
auto_promoted: true
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-24"
---
# 从采集到治理的反馈回路

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 线上性能治理不等于"把数据采回来"
- 🔹 治理回路至少包含:采集、采样、聚合、归因、告警、回查、修复、验收
- 🔹 指标、trace、会话上下文、版本/机型维度要能关联
- 🔹 没有接通处理回路的监控系统,最后会退化成日志堆积
- 🔹 把性能问题转成 backlog,并用回归验证确认结果,才进入治理

### 扩展(可选深入)

- 🔸 trace-id / session-id / page-id 的埋点设计
- 🔸 自建平台中的 schema 演进和存储成本控制
<!-- outline-end -->

## 为什么很多监控系统最后都没用起来

几乎每个做过线上性能治理的团队,都经历过一个类似阶段:平台建起来了,图表也出来了,版本发布后能看到一堆曲线,报警规则也配了几条。按理说,问题应该更容易被发现、更容易被修掉。可再过几个月回头看,常见结果却是另一种样子:

- 数据越来越多,但能走完整处理回路的问题很少。
- 图表越来越复杂,但一到具体 case,还是要靠人工拼现场。
- 报警越来越勤,但工程团队对它的信任越来越低。

原因不在"监控没做好",而在于很多系统只完成了前半段:**把数据采回来**。
难的部分在后半段:这些数据怎么被组织成一个可以流动、可以判断、可以进入修复、最后还能回到验证环节的过程。

本节聚焦的核心是：一条线上性能问题从被发现到被修掉，中间到底要经过哪些环节。

## 先把"监控"这件事拆开

如果把线上性能治理只理解成"采集指标",很快就会陷入一个误区:以为采得越多,系统越强。现实通常相反。
一条能工作的治理回路,至少要同时解决下面四个问题:

1. **感知**:系统有没有发现异常?
2. **定位**:系统有没有留下足够的上下文?
3. **流转**:问题有没有进入正确的人手里?
4. **验证**:修完之后,能不能确认它已经改善?

这四步里,只要断一环,平台就会开始失效。
只感知不定位,图表会越来越热闹;只定位不流转,工程团队还是得靠口头同步;只修复不验证,平台最后只会沦为"看过但没验证"的证据仓库。

## 一条完整治理回路,至少有八步

这八步描述的是大多数成熟团队在实际运转中形成的现实结构。

### 第一步:采集

先决定采什么,再决定接什么库。

常见的信号源包括:

- 帧级信号:`JankStats`（`androidx.metrics.performance.JankStats`，Maven 坐标 `androidx.metrics:metrics-performance:1.0.0`；核心 API 包括 `JankStats.createAndTrack(window, listener)` 注册帧回调、`OnFrameMetricsAvailableListener.onFrameMetricsAvailable(report)` 接收帧报告、`FrameData.getFrames()` 获取单帧时间戳。自 API 16 起提供基础帧耗时回调，API 31+ 内部分发至 `FrameMetrics.FRAME_TIMELINE_VSYNC_ID` 实现 VSync 对齐）、`FrameMetrics`
- 启动:TTID、TTFD、自定义首屏埋点
- 稳定性:`ApplicationExitInfo`（API 30+，Android 11 引入；API 26-29 需依赖 `ActivityManager.getRunningAppProcesses()` 或崩溃上报 SDK 获取进程退出信息；在 `android-17.0.0_r1` 中通过 `ActivityManager.java` 管理）
- 现场证据:`Matrix`、`btrace`、`Perfetto SDK`

采集这一层解决的是"有没有最基本的感知能力"。
没有这一步,后面所有治理都无从谈起。

> **API 版本说明**：上述采集通道的可用性随 Android 版本而异。
>
> | API 版本 | JankStats | FrameMetrics | 进程退出监控 |
> |----------|-----------|--------------|-------------|
> | API 26–29（Android 8–10） | ✅ 基础帧回调 | ✅ API 24 引入 | ⚠️ 需 `ActivityManager.getRunningAppProcesses()` / 崩溃 SDK / `StrictMode` |
> | API 30（Android 11） | ✅ | ✅ | ✅ `ApplicationExitInfo` 引入 |
> | API 31+（Android 12+） | ✅ 增强帧级 `DEADLINE` 跟踪和 `FRAME_TIMELINE_VSYNC_ID` VSync 事件标识 | ✅ 增强帧级 `DEADLINE` 跟踪和 `FRAME_TIMELINE_VSYNC_ID` VSync 事件标识 | ✅ |
> | API 37（Android 17） | ✅ 完整支持所有帧分析 API | ✅ 完整支持所有帧分析 API | ✅ `android-17.0.0_r1` `/base/core/java/android/app/ActivityManager.java` 基线验证通过 |
>
> 治理回路本身是版本无关的方法论框架，具体采集通道的可用性取决于目标 API 级别。API 26 以下的设备因市场占有率已极低，本节不再覆盖。

### 第二步:采样

采样决定的是"拿到多少数据"和"付出多大成本"。

线上最常见的三种策略是:

- **基线全量 + 异常补采**:基础指标全量,trace / hprof 这类重证据按异常触发
- **分群采样**:重点机型、重点渠道、灰度版本采得更密
- **会话级采样**:一旦命中采样,一个会话里的关键采集通道都保持一致,避免数据割裂

这一步最容易犯的错,是一开始就追求"大而全"。
线上体系需要把该采的采稳,同时避免让不该采的数据拖累系统。

### 第三步:聚合

单点事件的价值很有限。能支撑判断的,通常是分布和趋势。

所以聚合至少要能按这些维度切:

- 版本
- 机型 / SoC / GPU
- Android 版本
- 页面 / 场景
- 网络、前后台、多窗口等状态

没有这些维度,平台很快就会退化成一块大盘:全局均值看起来没什么问题,某几个重点机型却已经明显坏掉了。

### 第四步:归因

归因回答的是:问题更像落在哪条责任链上。

有用的归因,至少应该能把异常往下面这些方向里归:

- App MainThread
- RenderThread / GPU
- SurfaceFlinger / 显示管线
- Binder / 系统服务
- IO / 内存 / 调度 / thermal

如果平台只给出一句"某页面启动变慢了",对工程师帮助有限。
如果它能进一步说"首页骨架屏已经出现,但 TTFD 主要拉长在数据就绪之前",这条信息就开始变得可执行。

### 第五步:告警

告警要优先保证可行动性,而不是单纯追求速度。

所以比较稳的告警通常不会直接绑原始事件,而会绑业务可行动阈值,例如:

- 首页 P95 TTFD 连续 2 天上升（单日 ≥ 200ms 涨幅，样本量 ≥ 1000）
- 某机型 frozen frame rate 超阈值（P50 ≥ 2/min，连续 3 小时）
- 某版本 user-perceived ANR rate ≥ 0.5‰（样本量 ≥ 10000 启动）

如果平台把原始异常直接大量推给团队,结局通常只会是噪音堆积。

### 第六步:回查

回查能力决定了平台到底是"好看"还是"好用"。

工程师看到异常之后,至少要能回到:

- 会话时间线
- 页面 / 场景
- 版本 / 渠道 / 设备
- 相关 trace、堆栈、hprof、exit reason
- 最近的代码变更

很多系统到后面失效，问题通常在于异常被看到之后拿不到足够的现场。

### 第七步:修复

进入治理阶段后,问题不能再停留在"看板异常"这一级,需要变成工程语言。

至少要落成这样几类信息:

- 影响面
- 初步责任方向
- 复现条件
- 优先级
- 验收指标

没有这一步,平台和 backlog 之间就会一直断着。图表归图表,修复归修复,两边互相看得见,但互相接不上。

**从异常到 Backlog 的 SLA 映射**：

这一步的核心难点在于"什么样的异常该进 backlog、该给什么优先级"。常见的做法是建立两层 SLA：

- **业务 SLA**（用户可见）：首页 P95 TTFD ≥ 2.5s → 高危；冷启动 P90 ≥ 3s → 紧急；ANR 率 ≥ 0.5‰ → 紧急
- **技术 SLA**（系统内部）：frozen frame count 每分钟 ≥ 3 → 关注；主线程 blocked ≥ 16ms 连续 3 帧 → 中危；Binder 调用 P99 ≥ 50ms → 关注

映射关系不是 1:1。同一个"首页变慢"可能对应多种技术 SLA 触发，归因后的技术 SLA 命中情况才决定 backlog 的优先级：

| 异常现象 | 归因结果 | 技术 SLA 命中 | Backlog 优先级 |
|----------|---------|-------------|---------------|
| 首页 P95 TTFD 2.8s | 网络首包耗时上涨 | 首页 OkHttp P95 ≥ 800ms | P1（影响面大，方向明确） |
| 某机型 frozen frame 增多 | Shader 编译未命中缓存 | RenderThread ≥ 50ms 连续 5 帧 | P1（可复现，需要 GL 工程师） |
| ANR 率 0.3‰ | 单线程 Binder 阻塞 | Binder P99 ≥ 200ms | P2（低于阈值但趋势上升） |

规则的目的是让 backlog 里的每一条都带着"为什么现在修"和"修完怎么判断成功"的信息。

### 第八步:验收

这是最容易被忽略的一步。

很多团队会修问题,但修完以后没有再把结果拉回平台确认。于是系统最后只能说"这个问题当时看过",却说不清到底有没有改善。

比较完整的验收至少要看:

- 修复版本上线后指标是否回落
- 关键场景的 Macrobenchmark 是否恢复
- 线上 tail latency 是否改善
- 有没有引入新的回归

只看线下,不够;只看线上,也不够。两边都要回看。

## 一套治理回路需要哪些连接键

治理回路难，最常见的瓶颈是数据之间连不起来。

高频有用的键通常不多,但必须稳定:

- `session_id`
- `trace_id`
- `page_id` / `scene_id`
- `build / version / channel`
- `device fingerprint`

这些字段的价值取决于能否把不同层的数据 join 起来。
如果 trace 和指标、页面和版本、版本和报警之间连不上,平台功能再多也很难形成治理回路。

## 平台视角和工程视角,最容易断在这里

平台关心的是趋势和分布,工程师关心的是具体根因。
这两种视角天然不同,但又必须接上。

平台一侧常见的断点是:图表越来越多,趋势越来越漂亮,可工程师拿不到具体现场。
工程一侧常见的断点是:某次抓到了非常完整的 trace 和栈,但这些信息没有回流平台,后续版本再出类似问题时,还得从头再来。

成熟的系统要同时支持两种回路:

- 从群体趋势回到单次 case
- 从单次 case 回到群体趋势

只有这样,平台才会从展示层变成分析入口,工程分析也能从单次手工处理转成可复用经验。

### 多租户场景下的数据隔离

当平台需要服务多个业务线或外部合作方时，数据隔离是必须先解决的设计问题：

- **命名空间隔离**：每个租户的 `session_id` / `trace_id` 前缀加入租户标识，避免跨租户数据串扰。
- **存储层隔离**：按租户维度分表或分库；小规模团队可用租户 ID 过滤，大规模场景建议走独立实例。
- **访问控制**：基于租户 + 角色的权限模型——同一租户内的工程师可以查看自己团队的所有数据，跨租户查询需要显式授权。
- **成本核算**：按租户维度拆分量化的存储成本和采样配额，让各业务线对资源消耗有感知。

多租户不是锦上添花的功能。如果一个团队第一天就知道未来会有多条业务线接入，从第一版 schema 设计里就应该为 `tenant_id` 留出位置。

## 一个现实可执行的最小治理回路

团队初期不一定需要自建完整平台。更现实的做法,是先建立一个能稳定运转的最小版本:

1. 用 `JankStats`（API 16+）、启动埋点、`ApplicationExitInfo`（API 30+）建立基础指标；低于 API 30 的设备用崩溃上报 SDK 补充进程稳定性信号。
2. 对异常样本按低比例补采 trace 或会话时间线。
3. 用版本、机型、页面维度做最基本聚合。
4. 周期性把异常榜单送进 backlog。
5. 用 Macrobenchmark 和线上指标一起做修复验收。

这个最小治理回路的价值来自"责任清楚、能持续跑",不来自"功能很全"。
一条稳定运转的小回路,远比一次性搭一个看起来很大的平台更有价值。

## 本节在整本书里的位置

把本书主线往回连一下,

- `7/8/9` 负责解释用户到底在抱怨什么
- `15.3` 负责解释这些抱怨该落到哪些指标上
- `15.5` 负责解释怎样把这些指标从线上拿回来
- 本节负责解释,拿回来之后怎样不让问题在流程里丢掉
- `15.10` 继续往前一步,解释团队如何把这一整套机制长期跑起来

所以这一章更适合放在整条线上治理主线的中段,不能只当成平台建设附录。

## 结尾

线上性能治理最怕的场景:数据很多、问题也看到了,但最后没有流向修复和验证。
治理回路的价值,在于让一条线上异常最终变成一条能被处理、被验证、被复盘的工程任务。
