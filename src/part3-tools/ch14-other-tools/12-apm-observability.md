---
title: APM / 可观测性平台与 SDK 选型
chapter: '14.12'
section: '14.12'
status: finalized
drafted_date: '2026-04-21'
drafted_by: codex
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
last_verified: "2026-04-25"
last_verified_against: "Android Developers / AndroidX metrics docs / Firebase docs / GitHub upstream READMEs / external review 2026-04-25"
confidence: medium
sources:
- type: official
  path: https://developer.android.com/reference/androidx/metrics/performance/JankStats
- type: official
  path: https://developer.android.com/topic/performance/vitals
- type: official
  path: https://firebase.google.com/docs/perf-mon
- type: blog
  path: https://github.com/Tencent/matrix
- type: blog
  path: https://github.com/KwaiAppTeam/KOOM
- type: blog
  path: https://github.com/bytedance/btrace
- type: blog
  path: https://github.com/measure-sh/measure
- type: blog
  path: https://github.com/didi/DoKit
tags:
- apm
- observability
- monitoring
- matrix
- koom
- jankstats
- firebase
related_chapters:
- '14.5'
- '14.13'
- '15.3'
- '15.5'
- '15.9'
- '15.10'
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: '2026-04-25'
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-04-27"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-04-27T18:35:00+08:00"
task2b_state: fixed
repaired_date: '2026-04-22'
repaired_by: codex
task2b_result: fixed
last_task2b_at: "2026-04-25T16:44:10+08:00"
task9_review_notes: "2026-04-27 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0。"
last_task6_at: "2026-05-20T17:09:00+08:00"
last_task6_audit: "2026-05-20"
last_task6_audit_result: l1-light-edit
last_task6_audit_log: "logs/review/2026-05-20-17-audit.md"
---


# APM / 可观测性平台与 SDK 选型

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 先把“官方指标能力”“客户端 SDK”“后端 / 平台能力”分层
- 🔹 `androidx.metrics` / `JankStats` 解决的是帧级指标采集，不是完整 APM
- 🔹 `Matrix`、`KOOM`、`LeakCanary`、`btrace`、`DoKit` 的定位差异
- 🔹 `Firebase Performance`、`Measure` 这类平台型方案的价值和边界
- 🔹 选型先看目标：感知、定位、问题解决、成本、隐私

### 扩展（可选深入）

- 🔸 海外 SaaS APM 的客户端埋点与采样策略
- 🔸 自建平台时的埋点 schema 和 trace-id 设计
<!-- outline-end -->

## 为什么很多团队一开始就把选型做偏了

刚开始做线上性能治理时，最容易出现一种很自然的冲动：先去找“最强的那套方案”。于是大家开始比工具名、比功能表、比 README，问题逐渐变成“Matrix 和 Firebase 哪个更适合我们”“Measure 要不要一上来就接”“是不是再加一个 btrace 会更稳”。

这些问题看起来都很像选型问题，但它们的共同前提还没成立：团队到底想先解决哪一类问题？  
如果这个前提没说清楚，选型越认真，越容易把事情做偏。因为这些工具解决的并不是同一件事。

有些工具负责把线上问题先感知到，有些工具负责在异常发生时把现场保留下来，有些平台负责聚合、告警和回查，还有一些工具更偏开发阶段的调试现场。把它们都放进“性能库”这个大桶里看，结论往往只剩一个：信息很多，但判断不出来。

所以这一章要做的第一件事，是把能力重新放回它们原本的位置。

## 先把三层能力分开

如果把线上性能治理拆开看，至少有三层能力：

| 层次 | 解决的问题 | 代表能力 |
|---|---|---|
| **官方基线能力** | 系统已经愿意暴露哪些信号 | `JankStats`（AndroidX，低版本有回退）、`FrameMetrics`（API 24+）、`ApplicationExitInfo`（API 30+）、Android Vitals |
| **客户端增强层** | 应用自己还能补哪些上下文和现场 | `Matrix`、`KOOM`、`LeakCanary`、`btrace`、`DoKit` |
| **平台层** | 数据怎么聚合、回查、告警、进入治理 | Firebase Performance、Measure、自建平台 |

这个分层看起来简单，但它恰好对应了团队最容易混淆的三个问题：

1. “系统已经给我的，够不够？”
2. “系统没给的，我还能不能自己补？”
3. “补回来之后，团队怎么把它用起来？”

只要这三层没有分清，讨论很快就会变成“接哪个库”，而不是“团队当前缺哪一层能力”。

## 第一层：官方基线能力，决定了你的最低起点

官方能力最适合拿来做基础盘。它们的优点很明显：系统支持、口径相对稳定、兼容性通常更好。缺点也一样直接：系统没暴露的东西，它们给不了。

### JankStats：先把帧级信号拿稳

`JankStats` 最适合解决的问题，不是“把所有流畅性问题都看透”，而是“先把最基础的线上帧级信号拿稳”。

它给出的信息并不复杂：

- 当前这帧花了多久
- 这帧是否被判为 jank
- 当时 UI 正在什么状态

`PerformanceMetricsState` 是 `JankStats` 区别于原始 `FrameMetrics` 的关键能力。它允许把页面名、列表滚动状态、业务场景等状态写入当前窗口的 metrics state，回调里的帧数据会带上这些状态。平台收到帧记录时，可以直接知道 jank 发生在首页首屏、列表 fling 还是某个弹窗过渡期。

这个能力非常适合当第一层信号源。对一个刚开始做线上流畅性监控的团队来说，能先知道“哪些页面、哪些交互、哪些版本的帧开始变差”，已经非常有价值。

但它也只做到这里。`JankStats` 不负责：

- trace 文件管理
- 会话回放
- 平台告警
- 治理流程走通

所以它更像基础设施，而不是完整答案。

### FrameMetrics：在高版本上把帧拆得更细

如果说 `JankStats` 解决的是“这一帧有没有问题”，那 `FrameMetrics` 更接近“问题更像发生在哪一段”。  
它在高版本设备上能补更细的帧阶段信息，所以更适合作为增强层，而不是唯一入口。

工程上更稳的理解不是“二选一”，而是：

- `JankStats` 负责统一信号源
- `FrameMetrics` 负责高版本细分耗时

这样既不丢覆盖面，也不会让体系一开始就变得过重。

### ApplicationExitInfo：先把稳定性事实说准

线上治理最怕误判。  
`ApplicationExitInfo` 的价值，不在信息量特别大，而在于它提供了一种更接近系统真相的出口：到底是 ANR、崩溃、后台被杀，还是其他退出原因。

没有这层能力，很多团队只能靠客户端自己的启发式判断去猜测“像不像 ANR”“是不是被系统回收了”。  
一旦口径建立在猜测上，后面的聚合和报警很容易一路变形。

它的版本边界要单独写清：`ApplicationExitInfo` 从 Android 11（API 30）开始可用，API 26-29 不能把它当作基础能力。低版本上的 ANR、crash、low-memory 归因仍要依赖 traces、崩溃回调、前后台状态、进程重启痕迹和服务端会话拼接。接入时也不要在冷启动主线程同步拉取大量历史记录，`ActivityManager.getHistoricalProcessExitReasons()` 经过 `system_server`，适合延后到首帧后或后台线程。

### Android Vitals：最粗，但也最不能忽视

Android Vitals 的问题大家都知道：粒度不够细，自定义空间有限，很多时候只能看到趋势，拿不到足够多的现场。

但它仍然是很多团队最早的性能入口。原因很简单：它来自真实分发面，而且几乎没有接入成本。  
对于刚开始搭体系的团队来说，完全不看 Vitals，等于把一块已经放在手边的基础看板直接丢掉。

## 第二层：客户端增强层，决定了你能不能把现场留下来

官方能力解决的是“系统已经愿意给你的信号”。客户端增强层解决的是另一件事：**当系统没直接给，或者你还需要更强现场时，应用自己能补到什么程度。**

### Matrix：把客户端常见监控问题先组织起来

Matrix 最值得写的一点，是它把客户端常见的监控问题组织成了一套框架。

这件事的重要性在于：很多团队接监控时，卡住的地方通常是缺少统一入口。流畅性一套、IO 一套、内存一套、battery 一套，结果谁都接了一点，谁也接不完整。Matrix 提供的恰好是一种更容易收敛的接入方式。

它更适合的团队通常有两个特征：

- 已经有自己的上报通道
- 需要更强的客户端现场

它不适合被想象成“接了以后平台就有了”。  
很多团队用 Matrix 的难点，往往不在 SDK 接入，而在 schema、采样、回查和治理流程。

### KOOM：内存问题成为主矛盾时，它的价值更明显

`KOOM` 的优势很集中：Java Heap、Native Heap、线程泄漏、OOM 治理。  
所以它更像一把专项刀，而不是总平台入口。

如果团队当前最痛的是：

- 低内存设备回前台慢
- Native 泄漏难定位
- OOM 突增

那 KOOM 的优先级会非常高。  
但如果团队当前主要卡在首页慢、列表卡、响应延迟，它通常不应该作为第一站。

### LeakCanary：本地排泄漏，仍然非常强

`LeakCanary` 的位置很清楚：它更偏开发和测试阶段的本地排查工具。  
它最擅长的是把“谁没有被回收、为什么还活着”讲清楚。

所以更稳的理解是：

- `LeakCanary` 用来本地查泄漏
- `KOOM` 用来线上治理内存问题

把这两者混成“选一个就行”，读者后面很容易在使用场景上犯错。

### btrace / RheaTrace：当普通指标不够时，用它把现场保下来

`btrace` 这类工具的价值，不在于平时全量开着，而在于**问题已经被发现，但现场还不够**的时候。

比如一个版本的冷启动 P95 开始抬升，JankStats 也能看出首页某段交互开始变差，但为什么变差仍然说不清。这种时候，如果能按异常样本补一段方法级 trace，再叠上 Perfetto 体系里的系统事件，很多原本模糊的问题会迅速清楚。

所以 `btrace` 的位置是客户端增强层里的现场补强工具，不适合作为常驻 tracing 库。

Matrix Trace Canary 和 btrace 都能补方法级现场，但路线不同。Matrix 依赖编译期 ASM 插桩，覆盖面广，包体积和运行时事件量也更高；btrace 3.0 更偏同步采样，默认开销低，代价是采样命中率和还原精度需要按场景评估。线上选型时要把这类差异写进采样率、灰度和开关策略。

### DoKit：更像开发和测试现场的工具箱

DoKit 覆盖的能力很杂，实用点也不少：FPS、启动耗时、网络、页面检查、调试辅助、沙盒浏览。
它解决的是开发和测试现场怎样更快看到问题。

所以它更接近研发工具箱，而不是线上治理平台。  
这也是为什么它和 Firebase、Measure 看起来都“能看性能”，但并不在同一条线上。

## 第三层：平台层，决定治理能不能持续运转

客户端能力再强，没有平台，很多时候也只能停留在“拿到了一些点状证据”。  
平台层补上的，是这些能力：

- 版本对比
- 机型聚合
- 页面榜单
- 会话回查
- 告警分级
- 进入 backlog 的流转能力

### Firebase Performance：最容易进入团队视野的平台型能力

Firebase Performance 最大的优点，是上手快。  
对一个刚开始做线上性能治理的团队来说，它很适合解决“先把基础盘立起来”这个问题。

但这类平台也有很清楚的边界：越往深走，越会碰到定制能力、私有化、trace 流程控制这些限制。  
它适合做第一层平台，不一定适合承载整个治理体系。

### Measure：更接近完整治理平台

`Measure` 是开源移动可观测性平台，适合想替代 Firebase 但又希望自托管、数据留存可控、会话时间线可回查的团队。它把崩溃、ANR、trace、日志放在同一个视角里组织，适合已有 owner 维护平台和数据 schema 的团队。

对已经跨过“只想先看到几个指标”的团队来说，这类平台更贴近治理，不能只按展示看板来评估。

## 做选型时，先问四个问题

### 1. 团队当前最缺的是感知，还是归因？

- 还不知道问题在哪：优先建立信号层
- 已经能看到异常，但说不清原因：优先补客户端增强层

### 2. 团队当前最痛的是哪类问题？

- 卡顿 / 启动：先看 `JankStats`、Matrix Trace Canary、`btrace`
- OOM / 泄漏：先看 `KOOM`、`LeakCanary`
- 研发联调效率：先看 `DoKit`

### 3. 团队有没有平台承接能力？

没有平台承接时，客户端采再多，也很容易堆成日志。  
有平台能力时，才值得把 trace-id、场景上下文、会话时间线这些字段认真组织起来。

### 4. 团队能承受多少运行时开销和维护成本？

没有任何线上 APM 是“零成本”的。成熟的方案，一定要同时看：

- 默认开销
- 采样策略
- 开关粒度
- 数据边界
- 平台运维成本
- 版本兼容维护成本

如果团队没有明确 owner 去维护这件事，方案越重，后面越容易烂尾。

## 一张更实用的评估表

做选择时，可以用下面五个维度来问问题：

| 维度 | 要问的问题 |
|---|---|
| 感知能力 | 能不能及时发现卡顿、启动、ANR、OOM？ |
| 归因深度 | 只能看到指标，还是能看到 trace、调用链和会话上下文？ |
| 平台能力 | 有没有版本、机型、页面、地域等聚合视图？ |
| 工程成本 | 接入复杂度、运行时开销、运维成本如何？ |
| 数据边界 | 隐私、留存、自托管、上传策略是否可控？ |

没有哪套方案会在所有维度都最优。  
选型要做的，是把“换来了什么”以及“付出了什么”同时看清楚。

## 按团队成熟度选，而不是按流行度选

### 阶段 1：先把基础信号立住

如果团队现在还没有稳定线上信号，那最合理的顺序通常是：

- `JankStats`
- 启动埋点
- `ApplicationExitInfo`（API 30+；低版本仍要保留传统 crash / ANR 归因）
- Android Vitals / Firebase 这类基础平台能力

这个阶段最忌讳一上来接过重方案。因为团队还没确认哪些指标最有用，过度建设只会放大噪音。

### 阶段 2：问题能看到，但现场不够

这时应该补客户端证据层：

- `Matrix`
- `btrace`
- `KOOM`

目标从“有没有问题”变成“问题发生时能不能更快落到责任环节”。

### 阶段 3：证据不少，但治理效率低

这时应该投的是平台和流程：

- 会话时间线
- 版本 / 机型聚合
- 告警分级
- 问题榜单
- 回查能力

也就是 `15.9` 和 `15.10` 里展开的那部分。

## 什么时候反而不该继续扩 APM 体系

下面几种情况，往往不适合继续堆能力：

- 指标已经不少，但 backlog 没有人消费
- trace 和 hprof 已经能拿到，但平台回查很弱
- 团队没有明确 owner 维护版本兼容和采样策略

这时候继续加能力，通常只会增加复杂度，而不会增加治理效果。

## 给初学者的一个稳妥起点

如果读者刚开始搭团队的线上性能体系，一个比较稳的起点是：

1. 先用官方基线能力把启动、帧级信号、ANR / exit 看起来
2. 再选一两个最贴近团队当前问题的客户端增强工具
3. 再考虑平台整合和治理流程

这个顺序不够激进，但更容易推行。



<!-- AIW-源码调研-2026-05-03 -->
## 源码调研补充：AppExitInfoTracker 系统实现与 KOOM fork dump 机制

> 本节补充内容基于 AOSP 源码（AppExitInfoTracker.java）和 KOOM GitHub 仓库源码研究。

### AppExitInfoTracker 系统实现（源码级）

`AppExitInfoTracker` 是 `ActivityManagerService` 内部的进程退出信息追踪组件，位于 `frameworks/base/services/core/java/com/android/server/am/AppExitInfoTracker.java`。

**核心职责**：记录所有进程退出事件（含 Zygote 子进程 fork/exit、LMKD low-memory kill、ANR 等），持久化到 Proto 文件，支持 `ActivityManager.getHistoricalProcessExitReasons()` 查询。

**关键设计**：
- 持久化路径：`/data/system/proc_exit_store/proc_exit_info`（Proto 格式）
- 持久化周期：30 分钟（`APP_EXIT_INFO_PERSIST_INTERVAL`）
- 支持最多 8 条历史记录 per（package, UID）组合
- Zygote 和 LMKD 作为两个独立外部来源，标记 `REASON_LOW_MEMORY` / `REASON_SIGNALED` 等

**关键字段**（`ApplicationExitInfo`）：
| 方法 | 含义 |
|------|------|
| `getReason()` | 退出原因：REASON_OTHER / REASON_LOW_MEMORY / REASON_SIGNALED / REASON_VETOED / ... |
| `getStatus()` | 依赖 reason 的扩展状态码（如 `REASON_EXCESSIVE_RESOURCE_USAGE` 时含 WIFEXITED 等） |
| `getImportance()` | 退出时进程优先级 |
| `getPss() / getRss()` | 内存占用（KB） |
| `getTraceFile()` | 关联的 ANR trace 文件路径（.gz 压缩） |
| `getTimestamp()` | 退出时间戳 |

**触发链**：
```
AMS.killProcess() / Zygote SIGCHLD
  → scheduleNoteProcessDied()
  → MSG_PROC_DIED (KillHandler)
    → handleNoteProcessDiedLocked()
      → AppExitInfoTracker.handleNoteProcessDiedLocked()
        → 合并 Zygote/LMKD 来源的额外信息
        → addExitInfoLocked() / updateExistingExitInfoRecordLocked()
        → scheduleLogToStatsd()
```

### KOOM fork 子进程 dump Hprof 机制（源码级）

KOOM（快手）解决传统 hprof dump 阻塞主进程 20 秒的核心思路：

**传统方案问题**：`Debug.dumpHprofData()` 在主进程执行，整个 App 卡死约 20 秒。

**KOOM 解决方案**：
```
主进程 Suspend ART VM → fork() → 主进程 Resume ART VM → 子进程独立 dump
```

**主进程实际阻塞：< 20ms**。子进程在后台完成 dump + strip + 分析。

**关键 API 链**（`koom-java-leak` 模块）：
```kotlin
OOMMonitor.startLoop(loopInterval)
  → dumpAndAnalysis()
    → ForkStripHeapDumper.getInstance().dump(path)
      // JNI 层：
      // 1. art::Dbg::SuspendVM()
      // 2. fork() 创建子进程
      // 3. art::Dbg::ResumeVM()
      // 4. 子进程：hprof 写入 → strip 裁剪 → 上报
```

**文件裁剪与补全**：KOOM 在子进程中对 hprof 进行裁剪以减小体积（约 50-70% 减小），使用 `koom-fill-crop.jar` 在 PC 端补全被裁剪的 STRING/CLASS/PROXY DUMP 段，使文件可被 AS Profiler / MAT 解析。

**泄漏判定规则**：
- Activity：`mFinished || mDestroyed == true` 且存在到 GC Root 的引用链
- Fragment：`mFragmentManager == null && mCalled == true`（生命周期回调已完成）

**版本支持**：minSdk 21，armeabi-v7a / arm64-v8a / x86 / x86-64，支持 `c++_shared` 或 `c++_static` 两种链接模式。

**数据来源**：
- `AppExitInfoTracker` 源码：AOSP `frameworks/base/services/core/java/com/android/server/am/AppExitInfoTracker.java`（约 2100 行）
- KOOM 源码：`github.com/KwaiAppTeam/KOOM`（Apache 2.0）
<!-- AIW-源码调研-2026-05-03 -->

## 这一章在全书里的位置

这一章把工具能力放回治理体系里看：

- `7/8/9` 解释了体验问题的分类和诊断入口
- `15.3` 解释了该看哪些指标
- `15.5` 解释了线上怎么感知
- `15.9` 解释了感知之后怎么把治理走通
- `15.10` 解释了团队怎么长期把这件事做对

读者如果读完后，能先分层、再看目标、再按团队能力做组合，而不是直接抄一份工具清单，这一章就算达到目的了。
