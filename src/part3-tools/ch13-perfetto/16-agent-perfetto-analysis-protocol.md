---
title: "Agent 辅助 Perfetto 分析协议"
chapter: "13.16"
section: "13.16"
status: ready-for-review
drafted_date: "2026-05-17"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-17"
last_verified_against: "android/skills profilers commit 4328beaf36f00265db107eb316f9add6b8764144; Perfetto Trace Processor docs; Perfetto SQL query/table docs; Android system tracing docs"
confidence: medium
tags: [perfetto, trace-analysis, agent-workflow, performance-tools]
related_chapters: ["13.2", "13.10", "13.15", "15.6", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "研究素材+官方仓库"
pipeline_stage: task9_pending
task2b_result: fixed-lite
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-28"
task6_result: pass-light-edit
last_task6_at: "2026-05-28T08:10:00+08:00"
task9_state: pending
task9_result: auto-fixed
task2b_state: fixed
last_task2b_lite_at: "2026-05-28"
last_task9_at: "2026-05-28T07:24:44+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-28"
sources:
  - type: official
    path: "https://github.com/android/skills/tree/main/profilers"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/quickstart/trace-analysis"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-深度调研.md"
  - type: material
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-研究材料/repo/skills/profilers/perfetto-sql/SKILL.md"
  - type: material
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-研究材料/repo/skills/profilers/perfetto-trace-analysis/SKILL.md"
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-05-28T08:10:00+08:00"
last_task6_review_log: "logs/review/2026-05-28-08-review.md"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-28 08 Task6 revisiting-review: pass-light-edit；L1/L2 小修 1 处，删除一处否定纠正式开场句；outline 8/8 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，送 Task9 复核。"
last_task9_review_log: "logs/deep-review/2026-05-28-07-deep-review.md"
updated_by: "openclaw-task9"
updated_date: "2026-05-28"
last_task9_autofix_at: "2026-05-28"
task9_review_notes: "2026-05-28 Task9 deep-review: auto-fixed。P0 1：修正 Perfetto SQL 守卫中不可 include 的 stdlib 模块名，回到 Task6 复审。"
p0: 1
p1: 0
p2: 0
---

# 13.16 Agent 辅助 Perfetto 分析协议

<!-- outline-start -->
## 要点

### 🔹 协议定位：从 Perfetto 教程到可复查的 Agent 调查流程
说明 `android/skills/profilers` 与普通 Perfetto 教程的区别，明确本节关注 trace 分析流程、证据约束和停止条件，而不是重复 UI 操作教程。

### 🔹 输入约束：trace 文件、问题类型、包名与版本信息
定义 Agent 分析前必须收集的最小输入，包括 trace 路径、Android 版本、设备/ROM、目标包名、复现场景、采集配置和期望回答的问题。

### 🔹 Scratchpad 证据链：只记录已验证事实
说明 scratchpad 的记录格式：时间窗、线程/进程、slice/counter、SQL、查询结果、排除项；强调假设与事实分离。

### 🔹 Perfetto SQL 生成守卫：schema、stdlib 与执行校验
覆盖 `trace_processor`、schema 检索、Perfetto stdlib 优先、`utid/upid`、`dur=-1`、`SPAN_JOIN`、`GLOB` 等查询稳定性规则。

### 🔹 六类调查域：CPU、Graphics、I/O、IPC、Memory、Power
把开放式 trace 分析拆成可执行的 domain hints，说明每类问题的起手查询、下一跳和常见误判。

### 🔹 Wall time 与 CPU time 分离
建立长耗时 slice 的基本判断流程：先查 `thread_state`，再区分 Running、Runnable、Sleeping、Uninterruptible Sleep，避免把等待时间误判为计算开销。

### 🔹 从局部异常到全局复核
说明找到疑似瓶颈后，仍要检查全局最长 slice、D-state、Binder、FrameTimeline 和关键 counter，避免第一个异常被误认为根因。

### 🔹 输出模板：证据表、阻塞方、边界与补采建议
定义最终报告结构：问题窗口、核心证据、根因链、排除项、可信度、补采字段、下一步优化动作。

## 扩展

### 🔸 Trace 采集规划器
按启动、滑动、ANR、I/O、内存、功耗、GPU 等问题类型生成 TraceConfig/atrace category 建议。

### 🔸 Android 版本与厂商轨道差异
整理 FrameTimeline、Binder、dmabuf、power rail、sched、MTK/vendor 轨道在不同 Android 版本和厂商 ROM 上的字段差异。

### 🔸 SQL 模板测试集
为常用 Perfetto SQL 建立 smoke test，降低字段漂移、stdlib 版本差异和空结果误判。

### 🔸 源码与 trace 关联
从 trace 中的 slice、Binder 方法、native 符号继续映射到 AOSP 或业务代码路径。

<!-- outline-end -->

Agent 辅助 Perfetto 分析要解决的问题是让一次 trace 调查能复查。人工看 Perfetto UI 很快，但结论常散在截图、口头判断和临时 SQL 里；换一台设备、换一个 trace、换一个人，很难复现同一条推理路径。本节把 `android/skills/profilers` 的思路改写成 AIW 的工作协议：输入要收齐，SQL 要查 schema，scratchpad 只写事实，报告要说明证据、边界和补采项。

13.2 节已经覆盖 Trace 抓取，13.10 节已经覆盖 Perfetto SQL 常用模板，13.15 节展示了 BufferQueue 阻塞案例。在这三节基础上，13.16 聚焦 Agent 调查流程：怎样提问、怎样取证、怎样避免早停。[来源: ../DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-深度调研.md]

## 协议定位：Perfetto 教程之外的调查规范

`android/skills/profilers` 目录包含两个能力包：`perfetto-sql` 与 `perfetto-trace-analysis`。前者把自然语言取数意图转换成可执行的 Perfetto SQL；后者面向开放式 trace 调查，要求 Agent 建立 scratchpad、读取 CPU / Graphics / I/O / IPC / Memory / Power 六类提示，并在结论前完成依赖追踪和全局复核。[已验证: android/skills profilers, commit 4328beaf36f00265db107eb316f9add6b8764144]

这套协议和普通 Perfetto 教程的差异在这里：教程关注概念、UI 操作和案例解释；协议关注 Agent 行为约束。一次合格的 Agent 调查至少要留下四类材料：输入条件、查询语句、查询结果、排除过的方向。没有这些材料，报告里的“主线程卡在 Binder”“GPU 阻塞”“I/O 竞争”都只是口头判断。

对 Android 性能优化来说，协议的价值集中在三类场景：疑难 trace 复盘、Benchmark 回归后的批量归因、线上问题证据包分析。明确的小问题仍然可以直接用 UI 或 13.10 节的 SQL 模板处理；开放式问题才需要完整协议，例如“这次启动为什么慢”“滑动为什么掉帧”“用户反馈点击后界面冻结”。

## 输入约束：分析前先把问题收窄

Agent 分析 trace 前必须拿到最小输入。输入越含糊，后面的查询越容易变成全量扫描；trace 越大，这种成本越高。

| 输入项 | 必填性 | 作用 | 缺失时的处理 |
|---|---:|---|---|
| trace 文件路径 | 必填 | `trace_processor` 查询对象 | 无法分析 |
| 问题类型 | 必填 | 选择启动、滑动、ANR、I/O、内存、功耗或 GPU 调查域 | 只能做快速巡检 |
| 目标包名 / 进程名 | 建议必填 | 限定 `process.upid` 与主线程 | 用 `android.startup.startups` 或进程列表查询候选 |
| Android 版本、设备、ROM | 必填 | 判断 FrameTimeline、Binder、dmabuf、power rail 等轨道可用性 | 报告降低可信度 |
| 复现场景与时间窗 | 建议必填 | 缩小 slice / counter 查询范围 | 先查全局最长 slice 和异常帧定位窗口 |
| 采集配置 | 建议必填 | 判断缺哪些 data source / atrace category | 把缺失字段写入补采建议 |
| 期望回答的问题 | 必填 | 决定报告输出是定位、归因还是优化建议 | 先改写成可验证问题 |

一个可分析的问题应该写成：“这份 trace 来自 Pixel 8 / Android 15，包名 `com.example.app`，复现冷启动首屏慢，采集包含 `sched`、`freq`、`am`、`wm`、`gfx`、`view`、`binder_driver`，希望确认慢在 App 主线程、系统服务、I/O 还是渲染提交。”这比“帮我看一下为什么慢”少很多歧义。

[自动发现] 输入约束还应该反向检查采集质量。缺少 `sched` 时无法分离 wall time 和 CPU time；缺少 FrameTimeline 时 jank 只能退回到 `Choreographer#doFrame`、RenderThread 和 SurfaceFlinger 轨道；缺少 Binder 事件或 flow 时，跨进程等待可能断在客户端。采集规划可回到 13.2 节，线上证据包可回到 26.5 节。[已验证: Perfetto Trace Processor docs, perfetto.dev/docs/analysis/trace-processor]

## Scratchpad 证据链：事实和假设分开

`perfetto-trace-analysis` 要求在 trace 同目录创建 scratchpad，文件名来自 trace 文件名加 `_analysis.md`。这个文件不能写“可能是”“看起来像”这类判断，只记录已经验证的事实：时间窗、线程、进程、slice、counter、SQL、结果、排除项。[已验证: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-研究材料/repo/skills/profilers/perfetto-trace-analysis/SKILL.md]

下面的模板用于约束 scratchpad 内容。排版只是附带要求，每条记录都要能回到一次查询或一次 UI 观察。

```markdown
# trace.perfetto-trace_analysis.md

## 输入
- trace: /path/to/trace.perfetto-trace
- package: com.example.app
- device: Pixel 8, Android 15
- question: 冷启动首屏慢，定位主耗时窗口和阻塞方

## 已验证事实
| 时间窗(ns) | 对象 | 证据 | 结果 | 来源 |
|---|---|---|---|---|
| 1200000000-2200000000 | main thread | SQL-01 thread_state overlap | Running 180ms, Runnable 420ms, Sleeping 390ms | trace_processor CSV |
| 1530000000-1620000000 | system_server binder thread | SQL-04 binder server slice | `PackageManager` 查询 86ms | trace_processor CSV |

## 排除项
- SQL-06: 目标窗口内未发现长 D-state，I/O 不是当前 trace 已证实的主因。
- SQL-07: FrameTimeline 中异常帧集中在启动窗口之后，不解释首屏慢。
```

这个模板把“事实”压成可审计单位。后续报告可以引用 `SQL-01`、`SQL-04`，但不能把未验证的推测写进 scratchpad。假设仍然可以存在，只能放在调查计划里；一旦查询证实或证伪，再写入 scratchpad。

## Perfetto SQL 生成守卫：先查 schema，再写查询

Perfetto SQL 的风险不在 SQL 语法本身，而在表、字段、模块和时间区间语义。`perfetto-sql` 对 Agent 的约束是：准备 `trace_processor`，检索标准库文档，确认表或视图的 schema，再写查询并执行校验。[已验证: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-研究材料/repo/skills/profilers/perfetto-sql/SKILL.md]

几条守卫规则应该固定下来：

| 规则 | 操作要求 | 防止的问题 |
|---|---|---|
| 固定入口 | 使用项目根目录的 `./trace_processor`，必要时下载官方 wrapper | 查询只停在生成文本，或工具路径不稳定 |
| schema 检索 | 用 Perfetto stdlib / SQL table 文档确认表名、列名、模块名 | 编造字段、混用旧版本字段 |
| stdlib 优先 | 优先查 `android.startup.startups`、`android.frames.timeline`、`android.frames.per_frame_metrics`、`sched.with_context`、`linux.cpu.utilization.process` 等具体模块；CPU 频率明细先用 prelude 的 `cpu_freq` 表或 CPU utilization 模块产出的聚合视图，`android.frames` 是 package 名，不是可直接 include 的模块名 | 手写复杂 join 时漏掉边界，或把原始表名误写成 stdlib 模块 |
| `utid/upid` | 线程和进程 join 使用 trace 内唯一 ID | `tid/pid` 复用导致错配 |
| `dur = -1` | 统计时用 `trace_end() - ts` 替代未闭合 duration | 总耗时和 overlap 计算错误 |
| overlap 过滤 | 时间窗查询使用区间相交条件 | 漏掉跨越窗口边界的长 slice |
| `GLOB` / `=` | 子串匹配用 `GLOB '*pattern*'`，精确匹配用 `=` | `LIKE` 下划线通配导致误匹配 |
| `SPAN_JOIN` | 输入表物化，按 CPU / 线程 / 进程分区 | 区间重叠时结果错误 |

这段 SQL 模板用于把目标进程主线程上的长 slice 与 `thread_state` 相交，回答“这段 wall time 里线程到底在运行还是等待”。执行前要把包名、slice 名和时间窗替换成当前 trace 的值。

```sql
WITH target_process AS (
  SELECT process.upid, process.pid, process.name
  FROM process
  WHERE process.name = 'com.example.app'
),
target_thread AS (
  SELECT thread.utid, thread.tid, COALESCE(thread.name, target_process.name) AS thread_name
  FROM thread
  JOIN target_process ON target_process.upid = thread.upid
  WHERE thread.tid = target_process.pid
),
target_slice AS (
  SELECT slice.id, slice.ts, IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) AS dur, slice.name
  FROM slice
  JOIN thread_track ON thread_track.id = slice.track_id
  JOIN target_thread ON target_thread.utid = thread_track.utid
  WHERE slice.name GLOB '*bindApplication*'
  ORDER BY dur DESC
  LIMIT 1
),
overlap_state AS (
  SELECT
    thread_state.state,
    MAX(thread_state.ts, target_slice.ts) AS overlap_ts,
    MIN(thread_state.ts + IIF(thread_state.dur = -1, trace_end() - thread_state.ts, thread_state.dur),
        target_slice.ts + target_slice.dur) - MAX(thread_state.ts, target_slice.ts) AS overlap_dur
  FROM thread_state
  JOIN target_thread ON target_thread.utid = thread_state.utid
  JOIN target_slice
  WHERE thread_state.ts < target_slice.ts + target_slice.dur
    AND target_slice.ts < thread_state.ts + IIF(thread_state.dur = -1, trace_end() - thread_state.ts, thread_state.dur)
)
SELECT
  CASE overlap_state.state
    WHEN 'R' THEN 'Runnable'
    WHEN 'R+' THEN 'Runnable'
    WHEN 'S' THEN 'Sleeping'
    WHEN 'D' THEN 'Uninterruptible Sleep'
    ELSE overlap_state.state
  END AS state_label,
  COUNT(*) AS segments,
  SUM(overlap_state.overlap_dur) / 1000000.0 AS dur_ms
FROM overlap_state
WHERE overlap_state.overlap_dur > 0
GROUP BY state_label
ORDER BY dur_ms DESC;
```

这条查询只回答状态分布，不直接给根因。Perfetto raw state 常见为 `Running`、`R/R+`、`S`、`D`，上面的 `state_label` 把它们映射成人类可读标签。`Running` 占比高，后续转向 CPU 采样、子 slice、频率和大核/小核分布；`Runnable` 占比高，转向调度竞争和同 CPU 其他线程；`Sleeping` 或 `Uninterruptible Sleep` 占比高，继续追 Binder、锁、I/O、futex 或内核等待。

## 六类调查域：把开放问题拆成可执行动作

`perfetto-trace-analysis` 把调查提示分成 CPU、Graphics、I/O、IPC、Memory、Power 六类。这里不把它们写成清单，而按“触发条件 → 起手证据 → 下一跳 → 误判边界”组织，便于 Agent 执行。[来源: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-研究材料/repo/skills/profilers/perfetto-trace-analysis/references/hints_*.md]

| 调查域 | 触发条件 | 起手证据 | 下一跳 | 常见误判 |
|---|---|---|---|---|
| CPU | 主线程或 RenderThread 长耗时，`Running` / `Runnable` 占比高 | `thread_state`、`sched`、CPU frequency、同 CPU 其他线程 | 查调度延迟、频率、IRQ、是否跑在慢核 | 把 `Runnable` 当成 App 正在计算 |
| Graphics | 掉帧、首帧慢、GPU 内存高、Surface 提交异常 | FrameTimeline、RenderThread slice、`gpu_mem_total`、graphics allocation | 对齐 App / SF frame token，查 `texture_upload`、`eglSwapBuffers`、BufferQueue | 只看 App 红帧，不查 SF 与 HWC |
| I/O | D-state、冷启动首轮慢、page fault 密集 | `thread_state.state = 'D'`、`blocked_function`、page fault、kworker | 查 dm-verity、page cache、block I/O、相关 kworker 唤醒 | 把 I/O 等待写成 CPU 耗时 |
| IPC | 客户端等待、Binder 调用密集、跨进程依赖明显 | Binder slice / table、flow、server process、server duration | 查服务端线程状态、慢方法、Binder storm | 停在“客户端等 Binder”，不追服务端 |
| Memory | LMK、swap 上升、kswapd 活跃、图形内存异常 | memory counters、LMK event、PSI、dmabuf / dma_heap | 查进程 RSS、swap、GPU buffer、bitmap、heap graph | 只看 Java heap，漏掉 native / graphics |
| Power | 屏灭耗电、无法 suspend、modem 或 BT rail 高 | power rails、suspend state、kernel wakelock、network packets | 查 wakelock 名称、UID 流量、Bluetooth / modem 事件 | 用平均功耗盖过短时间高能耗 |

这张表的用法是减少盲搜。Agent 不应该在每个问题上同时跑六类调查；应该从用户问题和已验证事实出发。比如启动慢先看启动窗口、主线程状态、I/O 和 Binder；滑动掉帧先看 FrameTimeline、UI / RenderThread、SurfaceFlinger 和 CPU；屏灭耗电先看 suspend、wakelock、power rail 和网络归因。

## Wall time 与 CPU time 必须分离

长 slice 的 `dur` 是 wall time，不等于 CPU time。一个 200ms 的 `bindApplication` slice 可能有 160ms 在 CPU 上运行，也可能 150ms 在等 Binder 或 I/O；优化方向完全不同。Agent 协议要求每个可疑长 slice 都查 `thread_state`，并按状态解释。[已验证: Perfetto Trace Processor docs, perfetto.dev/docs/analysis/trace-processor]

可操作的判断顺序如下：

1. 定位目标 slice 的 `ts`、`dur`、线程和进程。
2. 查同一时间窗内该线程的 `thread_state` overlap。
3. 将 `thread_state.state` 的 `R/R+`、`S`、`D` 映射为 Runnable、Sleeping、Uninterruptible Sleep，再计算各状态占比。
4. 按最大状态选择调查域：CPU、调度、Binder / 锁、I/O。
5. 找到阻塞方后，再回到全局视角确认没有更大的系统异常。

`Running` 表示线程正在 CPU 上执行，后续要看子 slice、CPU 频率、采样栈和是否跑在慢核；`Runnable` 表示线程醒着但没拿到 CPU，后续要看同 CPU 竞争、IRQ、RT 线程和 idle 情况；`Sleeping` 常对应等事件、锁、Binder 回复或 futex；`Uninterruptible Sleep` 常指向 I/O 或内核不可中断等待，需要结合 `blocked_function`、kworker 和 block 事件判断。

常见错误是把等待时间写成“函数慢”。函数名出现在 slice 上，只说明这段时间处于该函数范围内；线程状态决定这段时间有没有在 CPU 上做计算。报告里应写成“`bindApplication` wall time 200ms，其中 Running 40ms、Runnable 20ms、Sleeping 140ms，主要等待发生在 Binder 返回前”，不要只写“`bindApplication` 耗时 200ms”。

## 从局部异常到全局复核

找到一个异常后不能立即收工。复杂 trace 里可能同时存在 App 主线程等待、系统服务慢 Binder、SurfaceFlinger 合成异常和后台 I/O。第一个被发现的异常只说明“它存在”，不说明“它解释了用户问题”。

全局复核至少包括四步：

- **最长 slice 复核**：在目标时间窗内查全局最长 slice，确认是否有系统侧或其他进程的停顿超过当前候选瓶颈。
- **D-state 复核**：统计目标窗口内最长不可中断等待，判断 I/O 或内核等待是否被漏掉。
- **FrameTimeline / Binder 复核**：对 jank、启动、点击无响应类问题，分别确认异常帧和慢 Binder 是否与用户可感知窗口重合。
- **counter 复核**：查看 CPU frequency、memory、power rail、dmabuf 等关键 counter 是否在同一窗口发生突变。

这段查询用于复核目标窗口内的全局长 slice。它不负责归因，只负责提醒 Agent 是否漏掉更大的候选对象。

```sql
WITH window AS (
  SELECT 1200000000 AS start_ts, 2200000000 AS end_ts
)
SELECT
  process.name AS process_name,
  thread.name AS thread_name,
  slice.name AS slice_name,
  slice.ts,
  IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) / 1000000.0 AS dur_ms
FROM slice
JOIN thread_track ON thread_track.id = slice.track_id
JOIN thread ON thread.utid = thread_track.utid
LEFT JOIN process ON process.upid = thread.upid
JOIN window
WHERE slice.ts < window.end_ts
  AND window.start_ts < slice.ts + IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur)
ORDER BY dur_ms DESC
LIMIT 20;
```

如果这条查询返回的前几项都来自同一进程、同一问题窗口，原来的假设可信度会上升；如果出现 `system_server`、SurfaceFlinger、kworker 或其他 App 的更长停顿，报告必须解释它们为何相关或为何被排除。

## 输出模板：证据表、阻塞方、边界与补采建议

Agent 的最终报告不应该像 Perfetto UI 截图说明，而应该像一次工程调查记录。建议固定成八段：

| 段落 | 内容 | 要求 |
|---|---|---|
| 问题窗口 | trace 名称、设备、版本、包名、时间窗 | 给出 ns / ms 范围 |
| 结论 | 当前 trace 能支持的判断 | 不超过三条 |
| 证据表 | SQL 编号、对象、结果、解释 | 每条证据能回到 scratchpad |
| 阻塞方 | 如果存在等待，指出等待对象 | Binder / 锁 / I/O / 调度 / GPU |
| 排除项 | 已查但不解释本问题的方向 | 说明排除依据 |
| 可信度 | high / medium / low | 和 trace 采集字段绑定 |
| 补采建议 | 缺失 data source、category、采样栈或复现场景 | 可直接用于下一轮抓 trace |
| 优化动作 | App、Framework、系统、测试侧可执行动作 | 不写无法验证的结论 |

下面是一个压缩版报告骨架，可直接嵌入线上问题单或 Benchmark 回归记录。

```markdown
## Trace 调查报告

- trace: trace.perfetto-trace
- package: com.example.app
- window: 1200ms - 2200ms
- question: 冷启动首屏慢

### 结论
1. 主线程目标窗口 wall time 1000ms，其中 Sleeping 390ms、Runnable 420ms、Running 180ms。
2. 最大等待集中在 Binder 返回前，服务端 `system_server` 中 `PackageManager` 查询 slice 为 86ms。
3. 当前 trace 未采集调用栈，无法把服务端耗时继续归到具体 Java 方法。

### 证据
| 编号 | 证据 | 结果 |
|---|---|---|
| SQL-01 | 主线程 thread_state overlap | Running 180ms / Runnable 420ms / Sleeping 390ms |
| SQL-04 | Binder 服务端窗口 | `system_server` binder thread 86ms |
| SQL-06 | 全局 D-state 排行 | 目标窗口未见超过 20ms 的 D-state |

### 补采
- 增加 Binder 相关 data source / atrace category。
- 增加 Java / native 调用栈采样，采样窗口覆盖 1100ms - 2300ms。
```

这个模板刻意把“当前 trace 能证明什么”和“还需要补什么”分开。很多性能问题一次 trace 只能证明方向，不能证明最终代码位置；把边界写清楚，比给出一个看似完整但无法复查的根因更有价值。

## Trace 采集规划器

[自动发现] `android/skills/profilers` 偏分析阶段，缺少按问题生成采集配置的能力。AIW 版本应补一个轻量采集规划器：用户给问题类型，Agent 输出 `TraceConfig`、atrace category、buffer、时长和风险提示。13.2 节已经讲抓取方式，这里只定义问题到字段的映射。

| 问题类型 | 必要数据 | 建议补充 | 缺失风险 |
|---|---|---|---|
| 冷启动 / 热启动 | `sched`、`freq`、`am`、`wm`、`view`、Binder、App trace marker | 调用栈采样、I/O 事件 | 只能看到阶段耗时，难定位等待方 |
| 滑动 / 掉帧 | Android 12+ 优先 FrameTimeline；Android 10/11 回退到 `Choreographer#doFrame`、RenderThread、SurfaceFlinger、`gfx`、`view`、CPU frequency | GPU counter、BufferQueue / dmabuf | 难区分 UI、RT、GPU、SF |
| ANR / 点击无响应 | `sched`、Binder、input、锁等待、App marker | Java / native 栈、system_server 事件 | 等待方可能断在客户端 |
| I/O 卡顿 | `sched`、`sched_blocked_reason`、block I/O、page fault | kworker、dm-verity、文件名映射 | D-state 无法继续归因 |
| 内存 / OOM | memory counters、LMK、PSI、dmabuf / dma_heap | heapprofd、Java heap graph | 只能看到结果，看不到持有路径 |
| 功耗 | power rails、suspend、wakelock、network packets | Bluetooth / modem / thermal vendor 轨道 | 只能得到总量，难归到 UID 或模块 |

采集规划器的输出不应该替代人工判断。它的作用是减少“抓到 trace 才发现缺字段”的次数，并在报告里自动生成补采建议。

## Android 版本与厂商轨道差异

Perfetto SQL 模板不能假设所有 trace 都来自最新 Pixel。Android 10 到 Android 17 之间，FrameTimeline、Binder 抽象、dmabuf / ion、power rail、sched blocked reason、厂商 thermal / display 轨道的可见性都有差异。厂商 ROM 还可能把调度、功耗、显示事件放在 vendor 自定义 track 或 counter 里。

实际调查时建议把兼容性分成三层：

- **标准层**：Perfetto 基础表，如 `slice`、`sched`、`thread_state`、`counter`、`thread`、`process`。这层通常最稳，适合做兜底查询。
- **Android 标准库层**：如 `android.startup.startups`、`android.frames.timeline`、Binder、memory 相关模块。Android 12+ trace 才能稳定使用 FrameTimeline 口径；Android 10/11 需要回退到 UI/RenderThread/SF slice 和自定义 marker。
- **厂商扩展层**：如 MTK / vendor display、thermal、power、scheduler 轨道。只能按设备和 ROM 建词典，不能写成通用结论。

报告中的可信度要和这三层绑定。如果问题依赖 FrameTimeline，但 trace 来自字段不完整的旧版本或厂商裁剪 ROM，结论只能写 medium 或 low，并给出补采或手工 UI 对齐建议。

## SQL 模板测试集

Perfetto SQL 模板一旦进入团队工作流，就要像代码一样测试。字段变动、stdlib 模块变动、空结果、`dur = -1`、跨窗口 slice、`SPAN_JOIN` 分区错误，都会让 Agent 在下一次 trace 上生成错误结论。

一个可维护的测试集至少包含四类用例：

- **语法 smoke test**：每条模板能被 `trace_processor` 解析。
- **字段存在 test**：模板使用的表、视图、列能在当前 Perfetto 版本查到。
- **边界 test**：覆盖空结果、未闭合 slice、跨窗口 overlap、无 FrameTimeline 等情况。
- **语义 test**：用小 trace 或固定样例验证输出字段含义，例如状态占比之和是否等于目标窗口 overlap。

Perfetto 官方文档说明 Trace Processor 本身大量依赖 diff test：输入 trace、查询或 metric，输出和 golden 文件比较。[已验证: Perfetto Trace Processor docs, perfetto.dev/docs/analysis/trace-processor] AIW 的 SQL 模板不需要一开始就做到同样规模，但至少要把常用启动、帧、Binder、I/O、功耗模板纳入 smoke test。

## 源码与 trace 关联

Perfetto 能告诉我们“哪段时间发生了什么”，但优化动作通常要回到源码。Agent 报告定位到 slice、Binder 方法或 native 符号后，应继续建立到 AOSP 或业务代码的映射。

常见映射路径有四种：

- **slice 名称 → App trace marker**：回到业务代码里的 `Trace.beginSection()`，确认它包住的代码范围。
- **Binder 方法 → Framework 服务**：从服务名和方法名映射到 AOSP service，再结合服务端线程状态判断阻塞点。
- **native 符号 → AOSP / vendor 模块**：用符号名、进程名和调用栈定位 native 组件，必要时标注 vendor 不开源边界。
- **FrameTimeline / SurfaceFlinger → 图形栈章节**：队列、fence、BufferQueue、HWC 等机制回到 2.13、2.16、13.15，不在报告里重复写原理。

源码关联要克制。trace 证据能证明“这个窗口里哪个对象慢或在等谁”，源码只能解释“为什么可能走到这里”以及“哪里可能改”。没有调用栈、没有符号、没有业务 marker 时，不要把 trace 现象硬写成代码根因。

## 小结

Agent 辅助 Perfetto 分析的底线是可复查：输入清楚，scratchpad 只记事实，SQL 先查 schema，长 slice 必查线程状态，找到候选瓶颈后做全局复核，报告写清证据和边界。做到这些，Agent 才能从“帮忙看截图”变成可重复的 trace 调查工具。
