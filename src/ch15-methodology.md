---
title: Android 性能优化研究方法论
chapter: "15"
status: ready-for-review
applicable_versions: Android 8-17 (API 26-37)
last_verified_against: AOSP android-17.0.0_r1, Android Developers 文档, Perfetto 官方文档, 官方性能博客
tags: [performance, methodology, perfetto, profiling, optimization, android]
task9_result: needs-rework
task6_result: pass-light-edit
task6_state: reviewed
task9_state: pending
task2b_state: fixed
pipeline_stage: task9_pending
last_task6_at: "2026-07-04T06:10:00+08:00"
last_task6_review_log: "logs/review/2026-07-04-06-review.md"
last_task9_at: "2026-07-04T02:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-07-04-02-deep-review.md"
task6_review_notes_final: "2026-07-02 Task6 revisiting-review round3 (post-Task2B-structural): pass-light-edit. L1 fix×3 (关键是→要, 链路→链, 舒服→自我安慰). L2 pass. No B-class issues. Auto-promoted: task9=pass, queue=completed."
task6_review_notes_round4: "2026-07-03 Task6 revisiting-review round4 (post-Task2B-content-rework + Task9-autofix): pass-light-edit. L1 clean (banned-word scan: 0 real hits, 3 false positives). L2 pass (opening direct, structure clear, breathing points adequate). L3/L4: no B-class writing issues. FrameRateOverrides section (4.4) well-written, SQL examples properly formatted. DeviceConfig section (3.2) clean. Auto-promotion blocked: task9_result=auto-fixed (not pass-tech-review). Sent to Task9 for final tech confirmation."
task6_review_notes_round5: "2026-07-04 Task6 revisiting-review round5 (post-Task2B-lite-fix source path prefix): pass-light-edit. L1 clean (banned-word scan: 0 real hits; 矩阵=priority matrix false positive, 上分=substring of 线上分布 false positive). High-freq words all within limits. Restricted patterns: 2 (at limit). Structural meta-narrative: 0. Code blocks: all properly tagged (bash/sql). L2 pass (opening direct, rhythm good, structure clear, reader takeaways solid). L3 pass (evidence-backed, actionable SQL/bash examples, original frameworks). L4 pass (natural Chinese, peer-to-peer tone, no translation feel). No L1/L2 fixes needed this round. Auto-promotion blocked: task9_result=needs-rework (not pass-tech-review). Sent to Task9 for final tech confirmation."
task6_review_notes_round6: "2026-07-04 Task6 revisiting-review round6 (post-Task2B-lite source-path-prefix fix): pass-light-edit. L1 clean (banned-word scan: 0 real hits; 上分=substring of 线上分布 false positive; 问题是=part of 5W2H framework description false positive). High-freq words all within limits (其实×1, 彻底×1). Restricted patterns: 2 (not...而是 at limit). Structural meta-narrative: 0. Adjective+colon: 0. Code blocks: all properly tagged (bash/sql). L2 pass (opening direct, rhythm good, structure clear, breathing points adequate). L3 pass (evidence-backed with SQL/bash examples, source code anchored to android-17.0.0_r1, original frameworks like 3-tier baseline and 5-Whys walkthrough). L4 pass (natural Chinese, peer-to-peer tone, no translation feel, no AI-pattern sentences). L1 fix: tags field filled [performance, methodology, perfetto, profiling, optimization, android]. No B-class writing issues. Auto-promotion blocked: task9_result=needs-rework (not pass-tech-review). Pipeline sent to Task9 for final tech confirmation."
task2b_result: fixed-lite
last_task2b_lite_at: 2026-07-04
task9_task6_review_notes: | 2026-07-02 Task6 re-review (revisiting): needs-rework。L1 修复 4 处（禁用词+空壳章节）。B 类问题：章节整体为百科词条式罗列、案例数据疑似编造、Section 12 内容空泛、缺少 Perfetto 实战维度。已写入 queue priority:90。 | 2026-07-03 17:27 Task9 复核：16:32 入队的 2 条 P85（FrameRateOverrides + persist.traced.enable fallback）仍然成立，本节继续走 Task 2B。不在本轮新增 P0/P1。
review_notes: "2026-06-27 Task2B Lite: 曾修复 Perfetto 版本描述与 ADB 命令版本限定；2026-06-27 Task9 Deep Tech Review: 通过，无 P0/P1 问题，总体评分 3.5/5。 | 2026-07-02 Task9 闲时抽检 AUTO-FIX: 修正 Perfetto/traced 命令入口、服务启用边界与 Android 17 CLI 选项；回 Task6 复审。 | 2026-07-02 Task2B 主修复：结构性回炉——去百科化、移除编造案例数据、删除泛化云原生/5G/边缘计算内容、补充 Perfetto SQL 实战示例。 | 2026-07-02 Task9 Deep Review AUTO-FIX: 修正 Perfetto CLI detached/background 语义与 trace_processor SQL join/schema 示例；回 Task6 复审。 | 2026-07-03 17:27 Task9 复核：2 项 P1 仍成立（FrameRateOverrides、persist.traced.enable fallback），已在 queue.json 中持有 P85 entry 2 条，本轮未新增，继续走 Task 2B 闭环。"
last_task9_audit: "2026-07-03"
last_task9_autofix_at: "2026-07-02"
task2b_fixed_at: "2026-07-02T20:56:40+08:00"
last_idle_audit_at: "2026-07-02T17:27:39+08:00"
last_task6_audit: "2026-07-04"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-03
task2b_lite_notes: "2026-07-04 Task2B Lite: 修正 Perfetto 源码路径前缀缺失（src/perfetto_cmd/perfetto_cmd.cc → external/perfetto/src/perfetto_cmd/perfetto_cmd.cc; src/traced/service/service.cc → external/perfetto/src/traced/service/service.cc）。P1 from deep-review 2026-07-04-00."
---

# Android 性能优化研究方法论

Android 性能优化的工作质量，取决于前面有没有把问题定义清楚、工具选对、数据采到位、根因追到底。没有这一层，后面的优化方案再漂亮也容易跑偏。

本章把性能优化的完整流程拆成几个阶段——从问题分类、工具选择、数据采集与分析，到根因定位、方案设计与效果验证。每个阶段有对应的决策框架和常见陷阱。

## 1. 性能问题分类与优先级管理

### 1.1 问题面前的第一件事：定优先级

一个 App 同时面对的卡顿类问题可能有几十个——某机型下的滑动掉帧、特定页面的初始化慢、低端机 OOM。全部修不现实，但也不能靠直觉拍脑门。

用三个维度做量化排序：影响范围（受影响的用户百分比）、严重程度（问题的可感知程度，比如从 60fps 掉到 30fps 还是 40fps）、解决成本（需要的研发人天和测试资源）。三角代入后得到一个优先级矩阵：

- P0：高影响范围 + 高严重程度。启动慢、首页卡顿这类，立即投入。
- P1：影响范围小但严重程度高。特定机型的 ANR，尽快安排。
- P2：影响范围和严重程度都低。若干机型上偶发的微卡，排期解决。

排完之后，除非有新数据刷新，否则不要在修到一半时因为"这个看着也挺重要"临时换 target——P0 还没修完就去修 P1，等于两个都没修透。

### 1.2 分类框架：让问题先归档再动手

性能问题的分类框架是把排查路径标准化。拿到一个 issue 报告时，先归到这六类里：

- 启动性能：冷启动、温启动、热启动各自的时间组成
- 流畅度：帧率抖动、掉帧、UI 响应延迟
- 内存：峰值占用、泄漏、碎片、GC 频率
- 网络：总耗时 vs 分段耗时、超时模式、重试行为
- 电量：待机消耗、前台耗电模型、后台网络唤醒
- 热稳定性：温控降频后的性能衰减曲线

归完之后不要急着看代码。先确认同类问题在当前线上的分布——同一个卡顿 issue，是 80% 的用户都在某个 Activity 遇到，还是千分之一的低端机才有。这个数据决定后面投入的力度。

## 2. 优化方法体系：问题到验证的完整循环

### 2.1 PDCA 的实际用法

PDCA（Plan-Do-Check-Act）在性能优化里对应具体的动作。

- Plan：定义问题的量化指标（比如"冷启动从点击到首帧 < 1.5s"），选好对比基线（优化前同一机型同一版本的数据），确定采集工具。
- Do：实施改动。每次只改一个变量——同时改启动框架 + 布局 + 网络策略，最后看数据变好了也不知道是哪个生效的。
- Check：对比优化前后的相同指标。不能只看一次——至少跑三天，覆盖不同时段、网络、电量状态。单次 2s 降到 1.5s 不代表上线后一直是这样。
- Act：效果达标就固化方案、更新基线；效果不达标就回退、分析为什么没生效，进入下一轮。

这个循环能转起来的前提是"做的改动有数据反馈"。如果采集不到变更前后的数据差异，"优化"之后说"感觉快了"只是在自我安慰。

### 2.2 三类研究方法，各有各的着力点

性能优化要解决的问题性质不同，用的方法也不同。

定性分析对应"问题是什么"。5W2H 是简单好用的起点：What（什么指标异常）、Where（哪个页面/线程/机型）、When（版本发布时间点、是否有规律性）、Who（哪类用户）、Why（追因）、How（多严重）、How much（资源与时间成本）。很多排查跑偏是因为连 What 都没定清楚就开始翻代码。

定量分析对应"问题有多大"。Perfetto 导出的 trace 里有精确到微秒的 slice 数据，trace_processor 跑 SQL 能把"某段线程阻塞了多少次、每次阻塞了多久"变成一张表。统计方法派上用场是在数据已经结构化之后——先有 clean 的 trace 数据或线上指标，再谈 3σ 异常检测或趋势分析。

实验验证对应"这个解法是否改善了目标指标"。A/B 测试或灰度是最后的闸口，做完优化后象征性地对一下数字还不够。验证要回答三个问题：目标指标有改善（比如 frame deadline miss 减少）、副作用在可接受范围（比如电量没有明显上涨）、不同机型表现一致（不是高端机变快、低端机更慢）。

## 3. 性能分析工具与选择策略

### 3.1 先看工具能回答什么问题，再看它叫什么名字

工具表如果只列工具名和一句话描述，等于什么都没给。下面这张表把每个工具的观测能力对应到 Android 性能问题的实测对象上。

| 工具 | 观测能力 | 什么场景用它 | 典型输出 |
|---|---|---|---|
| Perfetto | 系统级 tracer：ftrace 事件、atrace 标签、heapprofd、java_hprof 等 30+ 数据源 | 渲染管线、Binder 调度、IO 路径、内存分配 | trace.perfetto-trace + SQL 查询结果 |
| Android Studio Profiler | IDE 内置的 CPU/内存/网络实时采样 | 本地调试、快速复现问题时的第一站 | 方法火焰图、内存分配时间线 |
| Battery Historian | 解析 bugreport 中的电量事件与唤醒锁 | 待机耗电、后台网络、WakeLock 持有 | 电量消耗时间线、UID 级别统计 |
| LeakCanary | 检测 Activity/Fragment 引用泄漏 | 开发阶段的内存泄漏自动告警 | 泄漏链 + heap dump |
| Network Profiler | HTTP/HTTPS 请求的时间线、状态码、字节数 | 单接口排查、请求瀑布流 | 请求甘特图 + 响应头/体 |

工具选对的标准：拿这个工具采集到的数据，能不能直接回答"性能异常到底发生在哪个阶段"。

### 3.2 版本兼容性：不是"能不能跑"，而是"能采到什么级别"

Android 各版本的 tracing 能力不一样。下面按版本交代清楚每个阶段采得到什么、采不到什么。

**Android 8 (API 26)**：核心 tracing 工具是 Systrace。AOSP 此版本不含 Perfetto，必须用 Systrace 的 atrace 标签体系（`sched`、`gfx`、`view`、`wm`、`am`），搭配 Android Studio Profiler 的 CPU/内存采样。采集粒度到函数级（Traceview），但做不到 Perfetto 那种跨进程 timeline 和 SQL 查询。

```bash
# Android 8 标准 trace 采集
python systrace.py -t 10 -o trace.html gfx view wm am sched
```

**Android 9 (API 28)**：AOSP `external/perfetto/perfetto.rc` 已包含 `traced` / `traced_probes` service，默认 `disabled`。能否启用取决于设备厂商是否把 `persist.traced.enable` 设为 1。启用了就可以用 `perfetto` CLI 采集，不启用就退回到 Systrace。

```bash
# 确认 Perfetto service 状态
adb shell getprop persist.traced.enable
# 如返回空或 0，尝试手动触发（需 root 或 debug build）
adb shell setprop persist.traced.enable 1
```

**Android 10-13 (API 29-33)**：Perfetto 成为系统 tracing 主入口，Systrace 逐步废弃。标准 AOSP 通过 `persist.traced.enable=1` 启动后台 service。`perfetto` CLI 支持 `-t`、`-b`、`-o` 以及 `sched/sched_switch` 等数据源名称。

```bash
# 10 秒 trace，32MB buffer
adb shell perfetto -t 10s -b 32mb -o /data/misc/perfetto-traces/trace.pftrace sched/sched_switch gfx
```

**Android 14-17 (API 34-37)**：Perfetto CLI + traced service 的组合完全替代 Systrace。长时采集可用 `perfetto -d` 让命令进入后台；detached session 是另一套模式，用 `--detach=<key>` 创建、`--attach=<key> --stop` 回收，不能和 `-d` 混用。`traced` 自身只接受服务端选项（`--background`、`--version`、`--set-socket-permissions`），不要给它传 `-b` 或 `--async`。

```bash
# 长时后台采集
adb shell perfetto -d -t 30s -b 64mb -o /data/misc/perfetto-traces/long_trace.pftrace sched gfx view wm

# detached session 回收时必须带 key
adb shell perfetto --attach=my_trace --stop
```

**源码验证（基于 AOSP android-17.0.0_r1）**：

`external/perfetto/perfetto.rc` 中 `traced`、`traced_relay`、`traced_probes` 三个 service 均为 `disabled`。标准 AOSP 通过 `persist.traced.enable=1` 的 init action 启动 `traced` / `traced_probes`，同时创建 `/data/misc/perfetto-traces` 和 `/data/misc/perfetto-configs` 目录。Pixel 或厂商镜像可通过 vendor init、DeviceConfig 或属性默认值覆盖启用边界。

`external/perfetto/src/perfetto_cmd/perfetto_cmd.cc` 中 `perfetto` CLI 接受的参数：`-c/--config`、`-o/--out`、`-t/--time`、`-b/--buffer`、`-d/--background`、`-D/--background-wait`、`--detach/--attach`。`external/perfetto/src/traced/service/service.cc` 中 `traced` 只处理 `--background`、`--version`、`--set-socket-permissions`、`--enable-relay-endpoint`，不接受 `-b` 或 `--async`。

**Android 17（API 37）Perfetto 启用方式的变化**：Android 17 在 `persist.traced.enable` 基础上引入了 `debug.perfetto.enabled` 系统属性，作为更细粒度的启用控制。同时 DeviceConfig 机制使 Perfetto 的生产者数据源可以在无需 root 的条件下动态开启或关闭。

```bash
# Android 17 新增：通过 DeviceConfig 动态管理 Perfetto 生产者
adb shell device_config put persist.debug.perfetto enable_producer 1
adb shell device_config get persist.debug.perfetto enable_producer

# 查询当前 Perfetto 启用状态（兼容多版本）
adb shell getprop persist.traced.enable
adb shell getprop debug.perfetto.enabled
```

DeviceConfig 的优势是按生产者粒度控制——例如只在启用 heapprofd 时才打开对应的 `android.heapprofd` 生产者，避免全局开启的持续性能开销。`persist.traced.enable=1` 在 Android 17 中仍然有效且是 AOSP 默认推荐方式，`debug.perfetto.enabled` 和 DeviceConfig 提供了更细粒度的运行时控制能力，尤其适合在非 root 的 user build 设备上按需开关数据源。

## 4. 数据采集与分析：从 raw data 到 actionable 结论

### 4.1 采样策略：不同问题用不同采法

采样不是采得越多越好——采样策略取决于问题类型的自然发生频率和单个样本的价值。

- 启动性能：冷启动 100% 采样。冷启动次数天然少（用户一天也就几次），少一个样本就可能漏掉关键退化。每个冷启动都采集 trace、记录所有阶段耗时。
- 流畅度：按设备档位分层采样。高端/中端/低端分开统计，framedrop 的触发模式在这三档差别很大——混在一起看平均值会掩盖低端机的真实体验。
- 内存：按生命周期节点采样。启动完成、进入关键页面、退出后台、OOM 前的快照比连续采样更有意义。要把峰值前后的对象分配轨迹抓下来，而不是只看时刻点的 PSS。
- 网络：按网络类型分层。WiFi、4G、5G 的 RTT 和吞吐量差了一个数量级，混在一起得到的"平均网络耗时"没有任何优化指导意义。
- 电量：按电池状态和系统状态采集。电量 80% 以上 vs 20% 以下，充电中 vs 未充电，前台 vs 后台——同一个网络请求的功耗成本完全不同。

### 4.2 基准线的三条腿

性能优化从有基线开始。三类基准不是取一个就行，是互相校准。

绝对基准：应用自身的当前性能值。比如"冷启动 P50 1.8s，P99 4.2s"。没有这个，优化完只能说"好像快了点"。

相对基准：同一个指标在上一版本的值。冷启动 P50 从 1.8s 变成 2.1s——这个变化比绝对值更能说明问题。相对基准的坑在于"上一版本"的采集条件必须和当前版本一致（同机型、同网络、同系统版本），否则对比没有意义。

行业基准：同类应用在同一个性能维度上的表现。Google Play Android Vitals 给出的 ANR 率、启动时间、帧率阈值可以作为参考锚点。行业基准当红绿灯用——知道自己相对于基准是高还是低——不要精确对标，因为用户群、机型分布和对方大概率不一样。

### 4.3 Perfetto trace_processor 实战：用 SQL 把 trace 变成结论

Perfetto 的 trace 文件要用 `trace_processor` 解析才有诊断价值。下面给几个实战 SQL，覆盖最常见的"帧为什么掉"和"线程在等谁"两类场景。

**查询卡顿帧的渲染流水线**

```sql
-- 找出耗时超过 16ms 的帧，按耗时降序排列
SELECT
  id AS frame_id,
  ts,
  ts + dur AS ts_end,
  dur / 1000000 AS dur_ms,
  name
FROM slice
WHERE name GLOB '*Choreographer#doFrame*'
  AND dur > 16000000
ORDER BY dur DESC
LIMIT 20;
```

这个查询告诉"哪些帧慢了"，但不告诉"为什么慢"——Choreographer 的 doFrame 只是帧的入口计时器，慢的原因可能在它内部的任何一个子阶段。

**展开帧内各阶段耗时**

```sql
-- 展开一帧内部的各阶段：input、animation、traversal、draw
WITH target_frame AS (
  SELECT id
  FROM slice
  WHERE id = <frame_id>
)
SELECT
  child.name,
  child.dur / 1000000 AS dur_ms
FROM slice AS child
JOIN target_frame AS frame ON child.parent_id = frame.id
ORDER BY child.ts;
```

把 `<frame_id>` 换成上面第一句查出来的 `frame_id`，就能看到帧内 input 处理、animation、measure/layout、draw 各花了多少时间。如果绝大多数时间都耗在 draw 里，接下来就去查 RenderThread 的 GPU 提交。

**主线程被 Binder 调用阻塞**

```sql
-- 找主线程中对 Binder 的阻塞等待
SELECT
  s.name AS blocked_call,
  s.dur / 1000000 AS blocked_ms,
  s.ts
FROM slice s
JOIN thread_track t ON s.track_id = t.id
JOIN thread ON t.utid = thread.utid
LEFT JOIN process ON thread.upid = process.upid
WHERE (thread.is_main_thread = 1 OR thread.tid = process.pid)
  AND s.name GLOB '*binder*'
  AND s.dur > 5000000
ORDER BY s.dur DESC;
```

Binder 调用耗时超过 5ms 就会直接吃掉帧预算。这个查询把"哪些 Binder 调用拖慢了主线程"直接列出来。结合调用名就能判断是系统服务（SurfaceFlinger、AMS）慢了还是 App 自己的 Service 慢了。

**内存分配热点（需在 Perfetto config 中开启 heapprofd）**

```sql
-- 按函数统计分配次数和大小
SELECT
  f.name AS function_name,
  SUM(a.count) AS alloc_count,
  SUM(a.size) AS total_bytes
FROM heap_profile_allocation a
JOIN stack_profile_callsite c ON a.callsite_id = c.id
JOIN stack_profile_frame f ON c.frame_id = f.id
WHERE a.size > 0
GROUP BY f.name
ORDER BY total_bytes DESC
LIMIT 20;
```

heapprofd 需要在 Perfetto config 中显式开启。开启后 trace 里会包含每个 malloc/free 的调用栈，上面这条 SQL 直接给出 Top 20 内存分配函数。结合分配次数和总字节数，能找到"频繁小分配"和"偶尔大分配"两类不同的内存问题模式。

### 4.4 数据分析的三个实用原则

先看分布，再看平均值。平均值掩盖离散度。启动 P50 1.5s 看起来不错，但如果 P99 是 8s，说明有长尾用户在糟糕的体验里——长尾通常是机型、网络或内存状态导致的。修长尾和修中位数是两套策略。

切分维度后再看趋势。按机型、系统版本、网络类型、时段分开后看指标变化。如果总体启动变快了但不分维度——可能是某款新机型占比提升拉低了 P50，而老机型的体验其实在退化。

异常值不要自动丢弃。P99.9 的极端值往往是某个机型组合触发了一个边界条件——不是随机的网络中断。单次 OOM 的 trace 比一百次正常的 trace 更有诊断价值。

#### 自适应刷新率场景的帧数据分析

Android 17 引入的 FrameRateOverrides API 允许应用或 WindowManager 为特定窗口指定目标帧率（例如游戏窗口 120Hz、视频窗口 60Hz、静态内容降到 30Hz）。在支持多档刷新率的设备上，同一个应用的不同窗口可能以不同的帧预算运行——「帧超时」的定义不再固定为 16.6ms。

这一变化对数据分析的三个关键影响：

**帧预算的动态性**：在自适应刷新率场景下，Perfetto trace 中每个 Choreographer doFrame 的超时阈值取决于该帧所在窗口的当前目标帧率。60Hz 对应的帧预算是 16.6ms，90Hz 是 11.1ms，120Hz 是 8.3ms。分析时必须先确认当前窗口的目标帧率，否则会把正常帧误判为卡顿。

**FrameTimeline Expected Timeline 的校准作用**：FrameTimeline 记录了每帧的 Expected Presentation Time 和 Actual Presentation Time。Expected Timeline 已经反映了 FrameRateOverrides 的干预结果——它将目标帧率换算为预期的 VSync 序列。分析时优先看 Expected 和 Actual 之间的差值（即帧的 deadline miss），而不是直接用 16ms 做阈值。

**VSync 偏移动态调整**：在 Android 17 中，SurfaceFlinger 会根据当前帧率动态调整 VSync offset——帧率越低，offset 越大，给 App 的主线程留更多渲染时间。帧率切换点附近的帧容易出现 deadline miss，因为 offset 调整有延迟，新帧率的 offset 在上一帧的渲染周期已确定。

Perfetto trace 中的可观测字段：

```sql
-- 在 Perfetto trace 中查询帧率变化事件（需 trace 中包含 SurfaceFlinger 数据源）
SELECT
  ts,
  name,
  int_value AS target_fps
FROM slice
JOIN metadata ON slice.name = 'frame_rate_override'
WHERE int_value > 0
ORDER BY ts;
```

```sql
-- 查询 FrameTimeline Expected vs Actual 差异，按帧做 jank 判定
SELECT
  frame_id,
  expected_presentation_timestamp_ns,
  actual_presentation_timestamp_ns,
  (actual_presentation_timestamp_ns - expected_presentation_timestamp_ns) / 1000000.0 AS miss_ms
FROM expected_frame_timeline_slice
JOIN actual_frame_timeline_slice USING (frame_id)
WHERE actual_presentation_timestamp_ns > expected_presentation_timestamp_ns
ORDER BY miss_ms DESC
LIMIT 20;
```

实战建议：做帧率分析时，第一步确认 trace 期间窗口的目标帧率是否发生过变化（查 `SurfaceFlinger` 的 `display_connected_fps` counter 或 `vsync_source` 的 `rate` 字段）。如果目标帧率在变化，不要用固定的 16.6ms 当作合格线——改用 FrameTimeline 的 deadline miss 字段，或者按帧率分段统计。


## 5. 性能问题根因分析

### 5.1 从现象到原因，中间缺的是可验证的步骤

根因分析最常犯的错误：看到一个可疑的调用或者一个耗时的函数，就直接定性为"原因"。衡量标准——这个判断能不改代码就验证吗？

5 Whys 的实际用法，用卡顿排查演示：

1. 为什么页面卡？→ 主线程 doFrame 超过 16ms
2. 为什么 doFrame 超时？→ measure/layout 花了 11ms（正常情况下 3ms）
3. 为什么 measure 突然变慢？→ 某个 View 的 onMeasure 被重复调用了 4 次
4. 为什么重复调用？→ RecyclerView item 的动画触发了 parent 重新 measure，而 parent 的布局依赖链没有 cut
5. 为什么动画会触发 parent 布局？→ item 动画改了 View 的 margin，margin 影响 parent 的测量尺寸

到第五层才定位到 root cause——不是"measure 太慢"，而是一个动画改了不该改的属性，导致布局依赖链被重新触发。每一层"为什么"都对应一个可以独立验证的检查点——查 trace、看调用栈、改代码做对照——而不是在脑子里推导。

Fishbone（鱼骨图）的用法是从大类到具体线索的穷举框架。排查时按这几个分支列 checklist：人员（改动者、review 流程）、流程（CI 性能回归检查是否跑了、基线是否更新）、代码（最近提交的 diff、重构影响的模块边界）、环境（设备档位、系统版本、网络条件）。每一条线索要么验证通过、要么排除，不能靠感觉选。

### 5.2 两个高频排查手段

Call Stack / Flame Graph 分析：火焰图看宽度——宽的地方就是热点。Perfetto trace 导出到 Flame Graph 工具后，先看占比最高的 3-5 个调用链，再逐个做"这条路是否合理"的判断。不需要修每一个 hotspot——只处理那些调用次数多、单次耗时也高的。

内存分析：heap dump 看两个指标——retained size（这个对象及其引用子树占了多少内存）和 alloc count（这个类型的对象被分配了多少次）。retained size 大 + alloc count 高 = 内存泄漏或缓存设计不当。单独 retained size 大但 alloc count 低，通常是某次大对象分配后没释放，这时候看 GC root path。

## 6. 优化方案设计

### 6.1 20/80 法则在性能优化里的具体含义

代码 profiling 出来的热点图中，常常是 20% 的函数占了 80% 的执行时间。这不等于"找到热点就改热点"——还要问两个问题：这个热点能不能从路径上去掉（而不仅仅是优化它），以及优化这个热点会不会把瓶颈转移到另一个地方。

如果一个函数在主线程上耗时 12ms，直接把它拆到后台线程——这是去掉了路径上的热点。如果在原地用更快的算法把 12ms 优化成 6ms——瓶颈还在，只是变轻了。前者是结构性优化，后者是增量优化。优先前者。

### 6.2 渐进式实施：三档分类法

三层不能只用工作量划分，要按风险和对局部体验的改善程度分：

| 层级 | 典型内容 | 风险 | 验证周期 |
|---|---|---|---|
| 快速修复 | 单函数算法优化、不合理的同步锁去掉、冗余 measure 剪枝 | 低 | 一天内跑完灰度 |
| 中期优化 | 线程模型调整、启动框架重构、缓存策略重设计 | 中 | 至少一周，覆盖周末流量波动 |
| 长期优化 | 架构级改动（模块化拆分、渲染管线重构） | 高 | 按版本迭代，每步有回退方案 |

快速修复不能攒一堆一起上线——看似"改很小"的三个改动放到同一次灰度里，出了问题无法定位是哪个。每次只推一个快速修复，验证通过再推下一个。中期和长期优化按版本节奏走，不用追求一次新版把所有优化都带上。

### 6.3 常见优化手段的适用边界

启动优化：布局层级裁剪（减少 `ViewGroup` 嵌套）、延迟初始化（非首屏模块的 `ContentProvider` 改为懒加载）、闪屏策略（避免空白窗口）。关键不是在 `Application.onCreate` 里多线程——多线程初始化如果依赖关系没理清，结果是把单线程的 1.5s 变成了多线程的 1.5s（总耗时没变，只是分散了）。

流畅度优化：减少过度绘制（开发者选项打开 GPU 过度绘制检测，确认红色区域）、硬件加速与软件绘制的边界处理（某些自定义 View 的 `onDraw` 在硬件加速关闭时走到不同路径）、RenderThread 的帧提交时机（VSync offset 配置不当会导致帧延迟一整拍）。

内存优化：引用释放——匿名内部类持有外部 Activity 引用是最常见的泄漏源。数据结构选型——`HashMap` vs `SparseArray` 对 int key 场景的内存差异显著。缓存策略——LRU 的容量不是拍脑袋定，是按"应用在前台期间可能访问到的最大缓存集"反推出来的。

网络优化：减少请求次数（聚合接口、GraphQL）、协议升级（HTTP/2 多路复用替代 HTTP/1.1 的六连接限制）、头部压缩（HPACK/QPACK）。但协议升级有迁移成本——换 HTTP/2 之前先确认接入层是否支持、客户端的证书链是否兼容。

## 7. 效果验证

### 7.1 验证的铁三角

量化验证、对照验证、回归验证，三者缺一条都不是完整的验证。

量化验证：优化前后的指标在相同条件下的数据差异。不是看一次对比，是至少 3 天的数据窗口期——覆盖工作日/周末、白天/深夜的流量模式差异。只看发布后 2 小时的指标看不出真实的改善幅度。

对照验证：灰度发布时实验组和对照组的性能差异。对照的前提是分组随机（不能把新用户都放实验组、老用户都放对照组）且样本量够——P99 的差异需要比 P50 更大的样本量才有统计意义。

回归验证：优化目标以外的指标有没有变差。启动快了但首页帧率掉了 5%，这个优化不合格。回归检查要自动化——每次性能改动后自动跑一遍所有性能用例，不是靠人工回忆"上次好像看过那个指标"。

### 7.2 指标选择：不只看平均，要分场景看分布

- 启动时间：P50 和 P99 一起看。P50 决定多数用户的体验，P99 暴露长尾问题。
- 帧率：不只看平均帧率——60fps 下如果每 60 帧掉 1 帧，平均还是 59fps，但用户看到的就是一秒一卡。用 frame deadline miss rate 或 Janky frame count 替代平均帧率。
- 内存：峰值 PSS 和 GC 暂停次数。GC 导致的 stop-the-world 暂停如果超过 10ms，UI 线程就会被明显感知到。
- 网络：分段耗时（DNS、connect、TLS、TTFB、body read）的 P50/P90/P99，而不是只看总耗时。

## 8. 性能优化知识管理

### 8.1 问题库的价值：下次不用从零排查

性能问题库的标准是：每次修完后把排查路径、证据链、根因和修复方式记录下来，而不是随手记一笔症状。一个条目至少包含：

- 症状描述：用户/监控看到什么现象
- 复现条件：机型/系统版本/网络/操作步骤
- 排查路径：从哪个工具开始、看了什么数据、按什么顺序排除
- 根因：最终定位到的代码层面原因
- 修复方式：改了什么、为什么这样改
- 验证结果：修完后指标的变化

有这份记录，团队里其他人遇到相似症状时不需要从头排查。问题库按性能类型归档（启动/流畅度/内存/网络/电量/温控），每种类型再按根因分类（框架使用问题/业务逻辑问题/系统行为）。

### 8.2 文档与分享：知识资产化

技术文档和操作文档分开。技术文档回答"为什么这样设计"，操作文档回答"怎么用这个工具/跑这个 case"。两者混在一起会让排查流程的读者找不到入口——他需要的是"这条命令怎么跑"，中间夹了半页设计理由，读完就忘了命令。

团队分享的节奏比形式重要。一个双周 20 分钟的案例复盘，比季度的 2 小时正式汇报更能积累实战经验。案例复盘的三要素：问题原貌、排查过程（保留走弯路的步骤，删掉就等于删了最有价值的部分）、最终结论和 check 清单。

## 9. 最佳实践：在开发流程中嵌入性能意识

### 9.1 开发阶段：不在收尾时才看性能

性能问题改得越晚越贵。开发阶段的三个嵌入点：

需求评审：把性能需求写成可验证的指标。"搜索结果页首屏渲染 < 500ms（P50），< 1.2s（P99）"——不是泛泛地说"页面要快"。指标精确到这个程度，研发和 QA 才能共同验证。

技术方案评审：新增模块的性能评估——引入的新线程数、内存峰值预估、网络请求的频次和时机。如果评估结果是"不确定"，就要求先做一次 prototype profiling 再进入正式开发。

CI 性能回归：每次 MR 自动跑性能基准测试。启动耗时、核心页面帧率、内存峰值——这三个指标的回归检查是 CI 流水线的必过门禁。门禁的阈值不能设得太松（等于没门禁），也不能设得太紧（变成无意义的红灯）。

### 9.2 发布阶段：灰度是验证，不是仪式

灰度发布的目的是验证真实用户在真实环境里的体验——不是在办公室 Wi-Fi 下的开发者设备上。灰度要回答：实验组的主要性能指标是否优于对照组、是否有新增的 ANR/Crash、长尾用户（低端机、弱网、低电量）的体验是否有退化。

灰度数据的回溯周期至少 48 小时。发版后 2 小时的指标波动大部分是下载和安装行为导致的，不是实际的用户使用数据。

### 9.3 运维阶段：监控比优化更需要维护

线上性能监控的维护成本容易被低估。三个容易出问题的地方：

阈值更新：App 版本迭代后，很多操作的耗时基准变了——上一个版本的"正常耗时"可能是这一版的"偏慢"。按版本更新性能基线，否则报警要么不响，要么天天响。

埋点稳定性：关键性能埋点的采样率不能悄悄掉下去。线上监控面板上"P99 耗时为 0"不是好消息——多半是埋点数据丢了。

应急机制：性能严重退化时，除了报警之外要有回滚路径。对比度发布和 A/B 实验系统，保证问题版本可以在 30 分钟内切回对照组流量。

## 10. 案例复盘：三个典型场景的排查思路

以下案例不标注具体数值——同一类问题的表现数字在不同 App、不同机型上差异很大。重点在呈现排查路径的走法，不是比较绝对值。

### 10.1 启动慢：排查从哪个阶段切入

症状：某版本发布后，用户反馈"打开 App 变慢了"。线上指标显示冷启动 P50 增加了约四成。

排查路径：

1. 看线上分布——所有机型都变慢还是只有特定机型？如果是特定机型，先缩小到 SoC/系统版本/内存配置三个维度。
2. 取受影响机型的 Perfetto trace，对照上一版本同机型的 trace，在 Choreographer 的 doFrame 之前找差距——差距在 `Application.onCreate`、`Activity.onCreate`、还是首帧绘制。
3. 如果在 `Application.onCreate`，逐个看 `ContentProvider` 的初始化耗时——`ContentProvider.onCreate()` 在 `Application.onCreate()` 之前执行。新增的 SDK、新增的 `ContentProvider` 经常是启动变慢的来源。
4. 定位到具体初始化项后，判断是否可以延迟——非首屏模块的初始化移到第一次使用时，或放到 IdleHandler 里。

常见陷阱：多线程初始化如果没理清依赖关系，启动时间不变但分散到了多个线程——冷启动统计到的"完成"时间没变，但用户看到首帧的时间可能反而变晚了，因为多个线程同时争 CPU。

### 10.2 卡顿：用 Perfetto 定位帧瓶颈

症状：滑动列表时，每隔几秒出现一次明显的停顿感。

排查路径：

1. 用 Perfetto 采集包含 `gfx`、`view`、`wm`、`sched` 数据源的 trace。
2. 在 `trace_processor` 中查 Choreographer doFrame 耗时超过 16ms 的帧（见 4.3 节 SQL）。
3. 对超时帧展开内部阶段：input → animation → traversal → draw。多数卡顿卡在 draw 阶段。
4. 进入 draw 阶段后，看 RenderThread 的 GPU 提交时间线和主线程的 Canvas 绘制调用——RenderThread 在等 GPU fence 时主线程如果同时在准备下一帧的绘制数据，就会出现排队等待。
5. 如果每次卡顿的触发点都是 RecyclerView 滑动到某个特定 item 时，重点查那个 item 的布局复杂度（嵌套层级、`onBindViewHolder` 的耗时、decode bitmap 的位置）。

常见陷阱：把"平均帧率正常"等同于"没有卡顿"。平均帧率不反映单帧抖动——每秒 60 帧里如果有 10 帧超过 16ms，剩下的 50 帧把平均拉上来了，但用户体验是每 100ms 一次微卡。

### 10.3 OOM：从分配轨迹反推泄漏源头

症状：低端机用户频繁遇到 OOM 崩溃，崩溃前 PSS 持续上涨。

排查路径：

1. 开启 heapprofd 采集目标机型在典型使用路径下的内存分配 trace（见 4.3 节 SQL）。
2. 按 retained size 排序，确认哪类对象占用最多。
3. 对 retained size 最高的对象类型，看 GC root path——哪条引用链让它无法被回收。
4. 常见场景：`Activity` 被 `Handler`（匿名内部类）持有、单例持有 `Context` 的引用传入后未清理、`Bitmap` 在 `ImageView` 不可见后未 `recycle`、`WebView` 的资源释放不彻底。
5. 用 LeakCanary 做开发阶段的自动检测，CI 中集成 LeakCanary 的 leak 检测，阻止新的泄漏引入。

常见陷阱：PSS 高不等于泄漏。先区分"峰值正常但未及时释放"（说明某个生命周期的 onDestroy 后还有引用）和"持续上涨不回落"（经典泄漏模式），两类问题的定位路径不同。

## 11. 参考资料

### 官方文档
- [Android Performance Vitals](https://developer.android.com/topic/performance/vitals) — Google 官方性能指标定义与最佳实践
- [Android Profiler](https://developer.android.com/studio/profile/android-profiler) — Android Studio 内置性能分析工具
- [Perfetto 文档](https://perfetto.dev/) — 系统级 tracing 工具完整文档，含 trace_processor SQL 参考
- [Perfetto SQL 参考](https://perfetto.dev/docs/analysis/sql-tables) — trace_processor 所有 SQL 表结构和查询示例
- [Battery Historian](https://developer.android.com/topic/performance/battery-historian) — 电池使用分析工具文档

### 开源工具
- [LeakCanary](https://square.github.io/leakcanary/) — Square 开源的内存泄漏检测库
- [Systrace](https://source.android.com/devices/tech/perf/systrace) — Android 8-9 的 tracing 工具
- [Android GPU Inspector](https://developer.android.com/studio/profile/android-gpu-inspector) — GPU 性能分析工具

### 书籍
- [《高性能 Android 应用开发》](https://book.douban.com/subject/27027548/)
- [《Android 性能优化实战》](https://book.douban.com/subject/26740779/)
- [《深入理解 Android 性能优化》](https://book.douban.com/subject/30264920/)

### 延伸阅读
- [Android Performance Patterns (YouTube)](https://www.youtube.com/playlist?list=PLWz5rJ2EKKc8j2Bd8Bd9-2O9V1zr-hBFY) — Google 官方性能模式视频系列
- [Android Vitals](https://developer.android.com/topic/performance/vitals) — Google Play 的 ANR/启动/帧率评分体系
