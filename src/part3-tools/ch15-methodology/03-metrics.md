---
title: "性能指标体系"
chapter: "15.3"
status: finalized
drafted_date: "2026-04-04"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1；Android common kernel android17-6.18-2026-06_r6；Android Vitals / Macrobenchmark 1.4.1 文档"
confidence: high
sources:
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/base/core/java/android/view/FrameMetrics.java"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "system/memory/lmkd/lmkd.cpp"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl"
  - type: aosp
    tag: "android-17.0.0_r1"
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyConsumerResult.aidl"
  - type: kernel
    tag: "android17-6.18-2026-06_r6"
    path: "Documentation/accounting/psi.rst"
  - type: official
    path: "developer.android.com/topic/performance/vitals"
  - type: official
    path: "developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official
    path: "support.google.com/googleplay/android-developer/answer/9844486"
  - type: official
    path: "developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric"
  - type: official
    path: "developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "developer.android.com/topic/performance/memory"
  - type: official
    path: "perfetto.dev/docs/data-sources/battery-counters"
  - type: official
    path: "source.android.com/docs/core/power/power-stats-hal"
tags:
  - android
  - research
  - performance
  - metrics
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_reviewed_date: "2026-04-26"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-14T18:20:00+08:00"
last_task9_audit: "2026-06-26"
task2b_state: fixed
task2b_result: fixed
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-25"
last_task6_at: "2026-04-25T00:00:00+08:00"
task6_result: "pass-light-edit"
last_task6_audit: "2026-07-17T17:20:00+08:00"
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-04-25T08:51:01+08:00"
section: "15.3"
related_chapters:
  - "7.1"
  - "7.2"
  - "7.3"
  - "8.1"
  - "8.2"
  - "9.1"
  - "10.1"
  - "11.1"
  - "15.5"
  - "15.9"
review_round: 5
review_notes_5: "2026-04-25 task6 re-review (round 5): pass-light-edit. L1: 1 banned-word cleanup in 03-metrics; AI句式 3→1 in 03-metrics. 01-rendering-overview and 05-leakcanary clean. No B-class issues across all 3 chapters."
last_task9_audit_at: '2026-06-14T18:20:00+08:00'
last_task9_audit_log: 'logs/deep-review/2026-06-14-18-audit.md'
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-24"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-14
last_task9_autofix_at: '2026-06-14'
task9_review_notes: "2026-06-14 Task9 idle audit: auto-fixed FrameMetrics.DEADLINE duration-budget wording and Perfetto Power Rails / Energy Consumer unit semantics; no P0/P1 queue item."
last_task9_review_log: "logs/deep-review/2026-06-14-18-audit.md"
last_task2b_verifier_at: "2026-06-14T19:31:17"
task2b_verifier_result: "status-fix-ready-for-task6"
android17_review_notes: "2026-07-30：保留全部 task6/task9/OpenClaw 字段与 outline；平台锚点升级到 android-17.0.0_r1，PSI 锚点升级到 android17-6.18-2026-06_r6；重建流畅性、启动、稳定性、内存与功耗指标合同；修正 Play 当前阈值、TTID 起点、FrameMetrics/FrameTimingMetric、PSS/RSS、ApplicationExitInfo、Power Stats 单位与采样聚合边界；删除无来源阈值、固定采样率和虚构数据。"
---

# 性能指标体系

## 指标先写合同，再写数值

“启动耗时”“掉帧率”“OOM 率”都只是名字。团队要得到可比较的数据，还要定义事件、分母、统计窗口和排除条件。缺少这些信息，同名看板可能统计着不同对象。

每个长期指标至少包含以下字段：

| 字段 | 需要写清楚的内容 |
|---|---|
| 用户场景 | 哪个 CUJ、页面或业务动作 |
| 起点/终点 | 由哪个事件或时间戳定义 |
| 观测单位 | frame、launch、operation、session、user-device-day 等 |
| 数值单位 | ns、ms、byte、uWs、次数或比例 |
| 分子/分母 | 哪些事件进入计算，哪些事件被排除 |
| 统计窗口 | 单次运行、小时、天、发布周期或 28 天 |
| 聚合方法 | count、sum、mean、P50/P90/P99、比例、直方图或 sketch |
| 维度 | App/Android 版本、设备、刷新率、场景、启动类型、网络等 |
| 采样方法 | 采样概率、稳定抽样键、丢弃规则和权重 |
| 数据源版本 | Android、SDK、Benchmark/Perfetto、schema 与采集配置 |
| 负责人 | 谁解释异常、谁维护埋点、谁批准口径变化 |

指标合同改变时，应新建 schema/version，避免把新旧口径拼进同一条趋势线。

## 指标的四种职责

| 类型 | 用途 | 示例 |
|---|---|---|
| 用户结果指标 | 描述用户是否顺利完成操作 | TTFD、click-to-display、播放首帧、搜索结果可见时间 |
| 健康指标 | 观察线上影响范围 | user-perceived ANR/crash、slow startup、excessive wake lock |
| 门禁指标 | 判断候选版本是否允许发布 | 固定 CUJ 的 Macrobenchmark 分布、内存峰值、功耗区间 |
| 诊断指标 | 解释为何回退 | thread state、frame overrun、Binder latency、RSS/heap、energy consumer |

同一数值可以出现在不同层，但合同通常不同。Play 的 bad-behavior threshold 是外部健康线；它不适合作为 App 团队唯一的发布目标。

## 流畅性指标

### FPS

FPS 表示单位时间内实际呈现或生成的帧数，定义时要注明是哪一层：

- App 生产帧；
- SurfaceFlinger 呈现帧；
- 游戏 session 的实际 frame rate；
- 采样窗口内的平均值。

高 FPS 不能说明每一帧都稳定。少量长帧会被较长窗口的平均 FPS 稀释；静止页面主动减少帧数也可能是正确的节能行为。FPS 适合描述持续动画或游戏吞吐，普通 UI 的回归更适合结合 frame deadline、jank 比例和场景状态。

### Android Vitals 的 slow/frozen rendering

当前 Android Vitals 对使用 View/Canvas UI Toolkit 的应用记录：

- slow frame：渲染时间位于 16 ms 到 700 ms；
- frozen frame：渲染时间超过 700 ms。

这是 Play 的固定报表口径。Vulkan、Unity、Unreal、OpenGL 等不使用该 UI Toolkit 的渲染内容，不能假定会出现在这组数据中。游戏应另看 slow sessions 等游戏指标。

16 ms 也不是所有设备的实时 deadline。90 Hz、120 Hz 与可变刷新率设备应使用 FrameTimeline 或 frame overrun 判断是否错过平台分配的窗口。

### FrameMetrics

`FrameMetrics` 从 API 24 提供窗口帧的阶段数据。Android 17 的 `FrameMetrics.java` 定义了 `TOTAL_DURATION`、`GPU_DURATION`、`DEADLINE` 与 `FRAME_TIMELINE_VSYNC_ID` 等指标；源码明确写出 `TOTAL_DURATION < DEADLINE` 表示 App 命中该帧的 intended deadline。

使用 `Window.OnFrameMetricsAvailableListener` 时要记录：

- `dropCountSinceLastInvocation`，否则回调拥塞会造成选择性丢帧；
- first draw 与普通交互帧的区分；
- 页面/CUJ 与刷新率；
- API level，因为部分字段在较新版本才存在；
- 指标对应哪个 Window；SurfaceView、独立渲染 surface 或游戏引擎的输出需另核对。

`TOTAL_DURATION - DEADLINE` 可以表达 deadline 余量，但只有在对应字段有效时才计算。缺失值不能当作 0。

### Macrobenchmark FrameTimingMetric

当前 `FrameTimingMetric` 输出的主要字段包括：

- `frameOverrunMs`：API 31+ 可用；正值表示错过 deadline，负值表示仍有余量；
- `frameDurationCpuMs`：UI Thread 与 RenderThread 生产该帧所用的 CPU 时间；
- `frameCount`：被统计的总帧数。

官方文档建议在可用时优先用 `frameOverrunMs` 检测回归，因为它更适合高刷和可变刷新率。`frameCount` 也要一起观察：移除大量无意义的轻量帧后，剩余帧的分位数可能变差，但总工作量和功耗已经改善。

### Frame Time 分位数与 jank rate

P50、P90、P99 描述分布中的不同位置。使用分位数前要保证样本来自同一合同：

- 同一 CUJ 与页面状态；
- 相同刷新率或按刷新率分桶；
- 相同 App/Android 版本和设备档位；
- 相同 first draw、动画、滚动或静止帧类型；
- 相同丢帧与采样规则。

“P99 高”说明尾部分布较长，不能单靠 P99 推出根因。高分位还需要足够样本；样本很少时，直接保留所有观测值更诚实。

jank rate 的分子必须定义。它可以是 `frameOverrunMs > 0` 的帧数、JankStats 启发式判定帧数、FrameTimeline 某组 jank type，或业务自定阈值。不同分子不能共用一个“卡顿率”名称。

## 响应速度指标

### TTID

TTID（Time to Initial Display）是从系统收到启动请求到 App 第一帧显示的时间。冷启动包含进程创建，温/热启动不一定创建进程，因此不能把 TTID 一律写成“进程创建到首帧”。

Android Framework 自动报告 TTID。Play 当前使用 TTID 判断 slow startup，并按启动类型区分：

| Play slow startup 口径（核对日期：2026-07-30） | TTID |
|---|---:|
| Cold | ≥ 5 s |
| Warm | ≥ 2 s |
| Hot | ≥ 1 s |

这些值用于解释 Play Console。项目内部预算应更严格，并绑定设备档位、构建、编译模式和分位数。

### TTFD

TTFD（Time to Full Display）覆盖 TTID 以及首帧后异步加载的主要内容，终点由 App 调用 `reportFullyDrawn()` 标记。若 App 不调用该 API，就没有可用的 TTFD。

标记位置应对应“主要内容完成且用户可交互”的业务状态。调用过早会把空壳页面记作完成；调用过晚会把非首屏工作混入启动。埋点评审应把 fully drawn 条件写进合同，并在 UI/导航改版后复核。

TTID 与 TTFD 要分开看。前者适合观察系统启动、Application/Activity 创建和首帧；后者能覆盖首屏数据、图片与业务准备。

### Click-to-Display

Click-to-display 是自定义端到端指标，必须明确两端：

- 起点可选 input reader、input dispatch、App 收到事件或业务点击回调；
- 终点可选 App 提交帧、SurfaceFlinger present 或外部光学传感器检测到屏幕变化。

软件 Trace 通常无法覆盖触控控制器之前和面板 scanout 之后的物理延迟。跨版本比较时，应固定起止层级；“点击回调到 App 提交帧”和“手指接触到屏幕发光”是两项不同指标。没有公开依据时，不为它写统一的 100 ms/200 ms 阈值。

## 稳定性指标

### Android Vitals 的分母

Play Console 的 ANR/crash rate 按 daily active users 归一化；同一用户在不同设备上的使用会贡献不同的 active user-device。次数、受影响用户比例和受影响 session 比例是三种不同分母。

截至 2026-07-30，Play 的 core-vital bad-behavior thresholds 为：

| 指标 | Overall | Per device model |
|---|---:|---:|
| User-perceived ANR rate | ≥ 0.47% | ≥ 8% |
| User-perceived crash rate | ≥ 1.09% | ≥ 8% |

Play 当前说明中，user-perceived ANR rate 只计入 `input dispatching timed out` 类别。项目仍应监控 Service、Broadcast、前台服务等其他 ANR，它们属于 overall ANR 或内部稳定性指标。

Play 通常使用最近 28 天评估 core vitals，数据来自选择共享诊断数据的部分设备，并排除未通过 Google Play 安装的版本及未认证设备。它不是全量用户数据。

### Crash/ANR 内部指标

内部看板应同时保留：

- 受影响 user-device-day 比例；
- 受影响 session 比例；
- 事件次数与重复事件用户；
- error/ANR cluster；
- App/Android 版本、设备型号、进程与前后台状态；
- 采样率和缺失率。

Crash 与 ANR 的分母必须分别记录。一次 session 发生多次同类错误时，事件率会上升，受影响 session 率只记一次；两者回答的问题不同。

### ApplicationExitInfo

API 30+ 的 `ActivityManager.getHistoricalProcessExitReasons()` 可以读取系统保留的历史退出记录。`ApplicationExitInfo` 能提供 reason、timestamp、status、importance、PSS/RSS 采样以及可选 trace：

- `REASON_LOW_MEMORY` 的支持度要用 `ActivityManager.isLowMemoryKillReportSupported()` 检查；
- `getPss()` / `getRss()` 是系统最近记录的值，不保证等于死亡瞬间峰值；
- `getTraceInputStream()` 只在系统保存了对应 trace/tombstone 时可用；
- 历史记录有数量和保留范围，不应当作无损事件日志。

内部可把 exit reason 率分为 ANR、Java/native crash、low memory、excessive resource、user requested 等类别。LMK、OOM 和 crash 不能合并成一个“内存崩溃率”。

## 内存指标

### PSS 与 RSS

| 指标 | 含义 | 适合用途 | 限制 |
|---|---|---|---|
| PSS | 私有驻留页 + 按共享者比例分摊的共享驻留页 | 进程占用归因、场景前后快照 | 采集有成本；受共享页和采样时点影响 |
| RSS | 进程全部 resident 页，共享页按完整大小计入 | 时间趋势、reclaim/LMK 前后对照 | 跨进程相加会重复计算共享页 |
| Java heap | ART 管理的对象堆 | 分配速率、GC、存活对象与 heap 趋势 | 不包含完整 native、graphics、mmap 与共享内存 |
| Native heap | native allocator 管理的分配 | JNI/C++ 分配与泄漏诊断 | 不等同于进程所有 native/mmap/GPU 内存 |

PSS/RSS 是占用指标，不是 lmkd 的唯一杀进程排序规则。Android 17 `lmkd.cpp` 会结合 PSI、内存状态、`oom_score_adj` 与设备策略选择候选进程。

### PSI 与系统压力

Android common kernel `android17-6.18-2026-06_r6` 的 PSI 文档定义了 CPU、memory、I/O 的 `some`/`full` stall：

- `some` 表示至少部分任务因该资源停顿；
- `full` 表示所有非 idle 任务同时停顿；system-level CPU 不定义 `full`。

PSI 描述资源争用造成的 stall，不描述单个 App 的 PSS。内存看板可以把 App 占用、系统 PSI、reclaim 和 lmkd 事件放在同一时间轴，但不能用一个指标替代另一个。

### Java heap 与 GC

`Runtime.totalMemory() - Runtime.freeMemory()` 只能估算当前 Java heap 内已使用空间，不代表进程总内存。heap 上限还受设备、ART、`getMemoryClass()`、largeHeap 与运行状态影响；固定写成某个 MB 范围会误导跨设备门禁。

GC 次数本身也不是性能缺陷。需要结合暂停时间、分配速率、帧/响应窗口和存活对象。大量并发 GC 可能对主线程影响很小，短时间 stop-the-world 暂停也可能恰好跨过 frame deadline。

### OOM、native allocation failure 与 LMK

建议拆为三类：

| 类别 | 典型证据 | 推荐分母 |
|---|---|---|
| Java OOM | `OutOfMemoryError` crash cluster | session 或 user-device-day |
| Native allocation failure | tombstone、abort message、allocator/driver 日志 | session 或进程启动 |
| LMK/low-memory exit | `ApplicationExitInfo`、lmkd 事件 | session、进程启动或返回前台次数 |

分母要与产品问题对应。若关注“切回 App 后被重启”，返回前台次数可能比总 session 更有解释力。

## 功耗指标

### Battery drain rate

电量百分比每小时适合长时场景的粗粒度观察，但电池曲线受充放电状态、温度、电池健康度和系统平滑算法影响。短时实验应优先使用可用的 energy counter、Power Rails/ODPM、Energy Consumer 或外部功耗仪。

若能读取累计能量，平均功率可由同一 counter 的窗口差分计算：

> average power = Δenergy / Δtime

Android 17 Power Stats AIDL 中，`EnergyMeasurement.energyUWs` 与 `EnergyConsumerResult.energyUWs` 都以 microwatt-seconds（uWs）表示；timestamp/duration 使用毫秒。累计 counter 要先做差分，再按时间换算功率。counter reset、wrap、缺失与设备不支持都要显式处理。

### Active/Idle power

Active 与 Idle 需要由项目定义场景。前台静止、后台同步、息屏待机、音频播放和导航不能共用一个 idle 基线。实验至少固定：

- 屏幕亮度、刷新率和显示内容；
- 网络类型与信号；
- 充电状态、电池温度和 thermal；
- 设备/App 版本与后台进程；
- 场景时长、预热和统计窗口。

Power Rails 与 Energy Consumer 的可用项、命名和精度取决于设备硬件与 HAL 实现。CPU frequency 只能提供活动背景，不能换算出 App 精确功耗。

### Excessive partial wake locks

Android Vitals 当前把后台或前台服务期间的非豁免 partial wake lock 累计时长纳入统计：

- 24 小时内合计达到 2 小时或更多，session 被标记为 excessive；
- 最近 28 天内超过 5% 的 App sessions 命中时，可能影响 Play 可见度；
- audio、location、JobScheduler user-initiated 等场景有官方豁免。

这是一项 Play 健康指标。内部功耗目标还应记录 wake lock 名称、持有区间、调用方和是否存在更合适的调度 API。

## 线上与线下怎样配合

| 维度 | 线下实验 | 线上监控 |
|---|---|---|
| 目标 | 复现、归因、验证改动 | 发现趋势、影响范围和设备长尾 |
| 条件 | 可控制设备、构建、thermal、网络 | 环境复杂，存在采样与选择偏差 |
| 数据 | Trace、调用栈、逐次观测 | 聚合分布、cluster、少量上下文 |
| 优势 | 因果验证能力强 | 覆盖版本与设备群 |
| 限制 | 样本小，代表性有限 | 难以直接给出代码根因 |

线上异常应生成可复现的分群：版本、设备、Android、场景、网络和状态。线下按该分群搭建实验；修复后用相同实验与线上分群共同验证。

## 聚合规则

### 不要平均分位数

机型 A 的 P90 与机型 B 的 P90 不能通过普通平均得到总体 P90；每日 P99 的平均值也不是周期 P99。跨分片聚合应合并原始直方图、t-digest/DDSketch 等可合并摘要，或重新计算原始样本。

看板应标明分位数基于 frame、launch、session 还是 user 聚合。高频用户产生更多事件时，event-level P99 会偏向高频用户；user-level 指标应先在用户内聚合，再在用户间聚合。

### 均值仍有用途

均值适合可加总的成本指标，例如 CPU time、energy、bytes 和基础设施成本。对长尾敏感的交互延迟，应同时提供分位数、超阈值比例和样本量。不要把“永远不用均值”写成规则。

### 采样率由误差预算决定

固定建议“高频事件采 1%—10%，启动 100%”缺少业务、样本量和隐私背景。采样设计应记录：

- 稳定抽样键，避免一次 session 内忽采忽不采；
- 每条数据的采样概率或权重；
- 分层抽样策略，保护低端机、低版本和小流量场景；
- 客户端丢弃、限流和上传失败；
- 指标要求的最小样本与误差范围。

异常触发采样会改变分布。若慢事件更容易被上传，必须在合同中注明，不能与均匀采样数据直接合并。

### 维度要控制基数

常用维度包括 App/Android 版本、设备型号、SoC、内存档位、刷新率、页面、CUJ、启动类型和网络。用户 ID、完整 URL、自由文本和堆栈不适合作为时序标签，可进入受控日志或 cluster 系统。

## Android Vitals 的位置

Android Vitals 无需 App 集成自有 SDK，但数据来自选择共享 usage/diagnostics 的部分认证设备，并要求相关 App 版本通过 Google Play 安装。它提供：

- core vitals 与 bad-behavior thresholds；
- 版本、Android、设备、形态和地区等分群；
- slow startup、rendering、battery、crash/ANR 等数据；
- Play Developer Reporting API。

团队还需要自建业务 CUJ、非 Play 渠道、特定设备实验和详细上下文。两套数据应通过版本与场景关联，避免把分母不同的比例放进同一图表。

## 自定义业务指标

定义“信息流刷新完成”“视频首帧”“搜索结果可见”等指标时，逐项回答：

1. 用户动作从哪个事件开始？
2. 终点是数据返回、UI 提交、屏幕 present，还是可交互？
3. 取消、失败、缓存命中、后台恢复怎样计入？
4. 超时样本是否保留？若只记录成功，会产生幸存者偏差。
5. 跨进程/跨设备时钟怎样对齐？
6. 一个 session 多次操作如何聚合？
7. 采样和隐私规则是什么？
8. 指标变化后由谁启动 Trace、日志或回滚流程？

自定义指标应尽量落到用户可见终点，同时保留网络、解析、业务、UI、present 等诊断阶段。用户结果与内部阶段分开命名。

## 常见误区

### FPS 高就代表流畅

平均 FPS 会隐藏长帧；静止页面低 FPS 也可能符合设计。结合 deadline、jank 比例、分位数和 CUJ。

### TTID 快就代表启动完成

TTID 只到首帧。主要内容和交互准备要由 TTFD 或业务指标覆盖。

### Play 阈值可以直接当门禁

Play 阈值用于平台健康评估，且可能更新。内部预算需要绑定用户旅程、设备、构建和统计分布。

### PSS、RSS、Java heap 可以互换

三者的页分摊、覆盖范围和采集时点不同。趋势图和预算必须标明具体指标。

### P99 可以跨天求平均

分位数不能普通平均。保留可合并分布摘要与样本量。

### 只记录成功操作

失败和超时被排除后，延迟看板会虚假改善。成功率与延迟应成对观察。

## 参考资料

- [Android Developers：Android vitals](https://developer.android.com/topic/performance/vitals)
- [Play Console Help：Monitor your app's technical quality](https://support.google.com/googleplay/android-developer/answer/9844486)
- [Android Developers：Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Android Developers：App startup time](https://developer.android.com/topic/performance/vitals/launch-time)
- [Android Developers：Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [AndroidX Benchmark：FrameTimingMetric](https://developer.android.com/reference/androidx/benchmark/macro/FrameTimingMetric)
- [Android API：ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [AOSP android-17.0.0_r1：FrameMetrics.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)
- [AOSP android-17.0.0_r1：ApplicationExitInfo.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP android-17.0.0_r1：lmkd.cpp](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [AOSP android-17.0.0_r1：EnergyMeasurement.aidl](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyMeasurement.aidl)
- [AOSP android-17.0.0_r1：EnergyConsumerResult.aidl](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/EnergyConsumerResult.aidl)
- [Android common kernel android17-6.18-2026-06_r6：PSI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/accounting/psi.rst)
- [AOSP：Low memory killer daemon](https://source.android.com/docs/core/perf/lmkd)
- [Perfetto：Battery counters and power rails](https://perfetto.dev/docs/data-sources/battery-counters)
- [AOSP：Power Stats HAL](https://source.android.com/docs/core/power/power-stats-hal)
- [Android Developers：Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Android Developers：Battery Historian](https://developer.android.com/topic/performance/power/battery-historian)
