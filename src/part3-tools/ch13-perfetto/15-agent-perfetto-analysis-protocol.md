---
title: "Agent 辅助 Perfetto 分析协议"
chapter: "13.15"
section: "13.15"
status: ready-for-review
drafted_date: "2026-05-17"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-08"
last_verified_against: "android/skills profilers commit 4328beaf36f00265db107eb316f9add6b8764144; Perfetto official AI skill docs/release notes v57.1-v57.2; Android 17 Perfetto stdlib docs/source (android.frames.*, android.startup.startups, android.binder, slices.with_context, slices.time_in_state, slices.cpu_time, sched.with_context, linux.cpu.frequency, linux.cpu.utilization.process); Perfetto SQL table docs (slice, thread_state, sched, cpu_freq); Android system tracing docs | 2026-08-08 rework: closed pending-verification marker by pinning critical stdlib/source anchors and retaining Android 17 / android-17.0.0_r1 boundary"
last_rework_at: "2026-08-08T09:36:00+08:00"
last_rework_run_id: "20260808-093600-rework-39378b94"
last_rework_log: "logs/rework/2026-08-08-20260808-093600-rework-39378b94-rework.md"
rework_result: "ready-for-review"
rework_notes: "2026-08-08 rework：处理待验证标记；将 linux.cpu.utilization 通配口径收窄为已核验的 linux.cpu.utilization.process，并在正文官方资料区补充 Android 17 固定标签下的关键 stdlib/source 路径锚点；未越过 Android 17 / android-17.0.0_r1 基线，章节回流 ready-for-review 等待 Task6/Task9 复审。"
confidence: medium-high
tags: [perfetto, trace-analysis, agent-workflow, performance-tools]
related_chapters: ["13.2", "13.9", "13.14", "15.6", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "研究素材+官方仓库"
pipeline_stage: ready-for-review
task2b_result: fixed-lite
task6_state: pending-review
reviewed_by: hermes-aiw-review-finalize-apply
reviewed_date: "2026-08-04"
task6_result: "rework-applied"
last_task6_at: "2026-06-19T04:25:46+08:00"
task9_state: pending-review
task9_result: rework-applied
task2b_state: fixed
last_task2b_lite_at: "2026-05-28"
last_task9_at: "2026-07-10T01:28:21+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-10"
sources:
  - type: official
    path: "https://github.com/android/skills/tree/4328beaf36f00265db107eb316f9add6b8764144/profilers"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://perfetto.dev/docs/quickstart/trace-analysis"
  - type: official
    path: "https://perfetto.dev/docs/analysis/sql-tables"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/time_in_state.sql"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/cpu_time.sql"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/utilization/process.sql"
  - type: official
    path: "https://perfetto.dev/docs/getting-started/using-ai"
  - type: official
    path: "https://github.com/google/perfetto/releases/tag/v57.1"
  - type: official
    path: "https://github.com/google/perfetto/releases/tag/v57.2"
  - type: official
    path: "https://perfetto.dev/docs/contributing/testing"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-深度调研.md"
  - type: material
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Skill/android-skills/profilers/perfetto-sql/SKILL.md"
  - type: material
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Skill/android-skills/profilers/perfetto-trace-analysis/SKILL.md"
task6_reviewed_by: "openclaw-task6"
task6_reviewed_at: "2026-05-28T08:10:00+08:00"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
last_task9_review_log: "logs/deep-review/2026-07-10-01-audit.md"
updated_by: openclaw-task9
updated_date: "2026-07-10"
last_task9_autofix_at: "2026-07-10"
task9_review_notes: "2026-05-28 Task9 deep-review: auto-fixed。P0 1：修正 Perfetto SQL 守卫中不可 include 的 stdlib 模块名，回到 Task6 复审。 2026-05-28 08 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0。满足 task6_result=pass-light-edit、queue 无 pending、本轮无 P0/P1，自动晋升 finalized。 2026-06-18 Task9 idle-audit: auto-fixed。P0 1：修正 Perfetto CPU 频率时间区间入口，`cpu_freq` 仅为 CPU/freq 维度表，频率区间应使用 `linux.cpu.frequency` / `cpu_frequency_counters`。 2026-06-19 08 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0。复核源码/官方文档锚点、版本边界、Perfetto stdlib/API 口径，无新增技术问题；满足 task6_result=pass-light-edit 且 queue 无 pending，自动晋升 finalized。 2026-07-10 Task9 idle-audit: auto-fixed。P0 1：修正 android/skills profilers 失效本地素材路径，并将 GitHub main 源码锚点固定到 commit 4328beaf36f00265db107eb316f9add6b8764144。"
p0: 0
p1: 0
p2: 0
finalized_by: "hermes-aiw-review-finalize-apply"
finalized_date: "2026-08-04"
last_review_finalize_at: "2026-08-04T14:07:05+08:00"
last_review_finalize_run_id: "20260804-140516-9d7a366c"
last_task9_audit: "2026-07-10"
task6_reviewed_date: "2026-06-19"
task6_review_notes: "2026-06-19 Task6 revisiting-review: pass-light-edit。Task9 idle-audit auto-fix（cpu_freq linux.cpu.frequency cpu_frequency_counters 修正）已确认干净。L1 禁用词/高频词/翻译腔/元叙述 0 命中。L2 可读性通过（两处模板引导语属于代码块用途句，不算元叙述）。outline 8/8 覆盖。L1-L2 小修 0 处，无 B 类问题。task9_result=auto-fixed，待 Task9 最终确认。"
last_task6_review_log: "logs/review/2026-06-19-04-review.md"
last_task6_audit: "2026-07-07"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-11
---

# 13.15 Agent 辅助 Perfetto 分析协议

Agent 辅助 Perfetto 分析的目标是让 trace 调查可复查。人工查看 Perfetto UI 很快，但结论容易散落在截图、口头判断和临时 SQL 里；换一份 trace 或换一名分析者后，很难重放同一条推理路径。分析协议吸收了 `android/skills/profilers` 固定提交中的约束和 Perfetto 官方 Agent Skill 的主机侧工具边界：输入完整、SQL 经执行验证、证据与假设分开、报告注明版本和采集缺口。

在 13.2 节 Trace 抓取、13.9 节 Perfetto SQL 常用模板、13.14 节 BufferQueue 阻塞案例的基础上，这里聚焦 Agent 调查流程：怎样提问、怎样取证、怎样避免过早下结论。

平台源码锚点是 Android 17 / API 37、`android-17.0.0_r1`；该标签在 `platform/external/perfetto` 对应提交 `ece66975738007dd0978b911d8a2077e49b8f31e`。涉及调度和内核等待时，内核锚点是 `android17-6.18-2026-06_r6`。主机侧 SQL 在 Perfetto v57.2、提交 `da1d152cff27890903d158fe96751de3aab883cc` 的 Trace Processor 上验证，并覆盖 Android 17 标签中的标准库。Perfetto v57.1 引入官方 Agent Skill，v57.2 修复 Trace Processor 解析带内嵌 proto descriptor 的部分 trace 时出现的兼容问题。

Android 17 标签是 2026 年 4 月的固定源码快照，包含 Perfetto v54.0 之后的提交，不能写成“Android 17 等于 Perfetto v54”。主机上的新 Trace Processor 读取旧设备 trace 时，只能解析 trace 已经采到的数据；它可以改变表结构、标准库和分析能力，不能补出设备当时未记录的 FrameTimeline、ftrace、调用栈或厂商事件。

每次调查要分别记录这些版本：

| 层次 | 必须记录的内容 | 影响 |
|---|---|---|
| 设备平台 | 构建指纹、Android/API、ROM、内核版本 | 决定 trace 生产者实现与可用数据源 |
| 采集 | TraceConfig、atrace category、缓冲区、触发方式、截断情况 | 决定原始证据是否存在 |
| Trace Processor | `--version` 输出、二进制或包装脚本来源、校验值 | 决定 SQL 表结构、标准库和解析行为 |
| Perfetto UI | UI 版本或固定链接环境 | 决定界面插件和交互，不应改变保存 SQL 的字段语义 |
| Agent skill | 仓库、提交或发布版本、安装方式 | 决定 Agent 的调查步骤，不能替代 Trace Processor 版本 |
| SQL 包 | 标准库来源、额外 SQL 包、覆盖路径 | 决定模块实现，必须与查询结果一起保存 |

## 协议定位：Perfetto 教程之外的调查规范

`android/skills/profilers` 在 commit `4328beaf36f00265db107eb316f9add6b8764144` 下包含两个能力包：`perfetto-sql` 把取数意图转换成可执行的 PerfettoSQL；`perfetto-trace-analysis` 面向开放式 trace 调查，要求 Agent 建立 scratchpad、读取 CPU / Graphics / I/O / IPC / Memory / Power 六类提示，并在结论前完成依赖追踪和全局复核。

Perfetto v57.1 发布了符合 Agent Skills 规范的官方 skill。它教 Agent 调用 `trace_processor`、编写 PerfettoSQL、录制 Android trace，并提供 Android 内存与 GPU 调查流程；安装包内含可工作的 Trace Processor 包装脚本。两套 skill 的目录结构和指令不同，这里只提炼可复查原则，不把某个 skill 的内部文件名当成长期 API。

这套协议和普通 Perfetto 教程的差异在这里：教程关注概念、UI 操作和案例解释；协议关注 Agent 行为约束。一次合格的 Agent 调查至少要留下四类材料：输入条件、查询语句、查询结果、排除过的方向。没有这些材料，报告里的“主线程卡在 Binder”“GPU 阻塞”“I/O 竞争”都只是口头判断。

对 Android 性能优化来说，协议的价值集中在三类场景：疑难 trace 复盘、Benchmark 回归后的批量归因、线上问题证据包分析。明确的小问题仍然可以直接用 UI 或 13.9 节的 SQL 模板处理；开放式问题才需要完整协议，例如“这次启动为什么慢”“滑动为什么掉帧”“用户反馈点击后界面冻结”。

## 输入约束：分析前先把问题收窄

Agent 开始分析 trace 之前要收齐最低限度的输入。输入越含糊，后续查询越容易变成全量扫描；trace 越大，成本越高。

| 输入项 | 必填性 | 作用 | 缺失时的处理 |
|---|---:|---|---|
| trace 文件路径或受控句柄 | 必填 | `trace_processor` 查询对象 | 无法分析 |
| 问题类型 | 必填 | 选择启动、滑动、ANR、I/O、内存、功耗或 GPU 调查域 | 只能做快速概览 |
| 目标包名 / 进程名 | 建议必填 | 限定 `process.upid` 与主线程 | 用 `android.startup.startups` 或进程列表查询候选 |
| Android 版本、设备、ROM | 必填 | 判断 FrameTimeline、Binder、dmabuf、电源轨等轨道可用性 | 报告降低可信度 |
| 复现场景与时间窗 | 建议必填 | 缩小 slice / counter 查询范围 | 先查全局最长 slice 和异常帧定位窗口 |
| 采集配置 | 建议必填 | 判断缺哪些数据源 / atrace 类别 | 把缺失字段写入补采建议 |
| trace 散列值 | 必填 | 确认多人分析的是同一份输入 | 报告无法可靠复现 |
| skill / Trace Processor 版本 | 必填 | 固定表结构、标准库和工具行为 | SQL 结果只能按未知工具版本解释 |
| 期望回答的问题 | 必填 | 决定报告输出是定位、归因还是优化建议 | 先改写成可验证问题 |

可验证的问题要同时写明设备构建、目标包、复现场景、时间窗、已启用数据源和判断目标。例如，冷启动调查应明确要区分 App 主线程、系统服务、I/O 与渲染提交，而不能只写“为什么慢”。

输入约束还应该反向检查采集质量。缺少 `sched` 时无法分离经过时间和 CPU 运行时间；缺少 FrameTimeline 时，异常帧分析只能退回到 `Choreographer#doFrame`、RenderThread 和 SurfaceFlinger 轨道；缺少 Binder 事件或 flow 关系时，跨进程等待可能断在客户端。采集规划可回到 13.2 节，线上证据包可回到 26.5 节。

trace 可能包含进程名、线程名、URL、日志、文件路径和业务标记。共享报告时保存散列值和受控存储标识即可，不要把本机绝对路径、原始日志或未脱敏 SQL 结果复制到公开问题单。

## Scratchpad 证据链：事实和假设分开

固定提交中的 `perfetto-trace-analysis` 要求在 trace 同目录创建 scratchpad，文件名由 trace 文件名追加 `_analysis.md` 得到。团队协议还要服从权限和数据处理规则：trace 目录只读或由外部系统管理时，把 scratchpad 放入获准的工作目录，并记录 trace 散列值与受控存储标识。scratchpad 不写“可能是”“看起来像”这类判断，只记录已经验证的事实。

scratchpad 分成三张表：

| 表 | 必须记录的字段 | 约束 |
|---|---|---|
| 输入 | trace 散列值、平台构建、目标包、问题、复现条件、采集配置、Trace Processor、skill 与 SQL 包版本 | 任何字段未知都要显式写“未提供”，不能自行补全 |
| 已验证事实 | 证据编号、时间窗、`upid/utid`、slice/计数器/帧 token、完整 SQL、结果文件或结果摘要 | 每条记录都能由保存的命令重新执行 |
| 排除项 | 假设、执行过的查询、结果、排除范围 | 空结果只能排除“当前 trace 当前表结构下可见的证据”，不能写成机制绝对不存在 |

假设放在调查计划，不放在事实表。查询证实后转成已验证事实，证伪后转成排除项；证据不足时保留为待验证项，并注明缺少的数据源。

## Perfetto SQL 生成守卫：先查表结构，再写查询

Perfetto SQL 即使语法正确，也可能因为表、字段、模块版本或时间区间口径错误而给出误导性结果。`perfetto-sql` 对 Agent 的约束是：固定 Trace Processor 和 SQL 包，检查当前表结构，再编写查询并对真实输出做语义校验。

Android 17 的固定源码快照提供三类入口。`slice`、`thread_state`、`thread`、`process` 等基础表由 Trace Processor 预置；`android.startup.startups`、`slices.time_in_state` 等标准库模块要通过 `INCLUDE PERFETTO MODULE` 加载；旧版基于 trace 的 metric 由 metric 运行入口生成，不能因为加载同名标准库模块就假定 metric 表已经存在。

| 规则 | 操作要求 | 防止的问题 |
|---|---|---|
| 固定执行环境 | 保存 Trace Processor `--version` 输出、二进制散列值、标准库提交和完整命令；使用官方 skill 时也要记录其包装脚本与下载到的二进制 | 包装脚本或自动下载结果变化后无法重放 |
| 表结构检索 | 对实际二进制检查表和列，并对固定源码中的模块文件复核公开对象 | 根据记忆编造字段，或混用不同版本的表结构 |
| 标准库优先 | Android 17 可用 `android.startup.startups`、`android.frames.timeline`、`android.frames.per_frame_metrics`、`android.binder`、`slices.with_context`、`slices.time_in_state`、`slices.cpu_time`、`sched.with_context`、`linux.cpu.frequency`、`linux.cpu.utilization.process`；其中 `sched.with_context` 公开的是 `sched_with_thread_process` 这类调度 slice 上下文视图，不等同于 `thread_state` 的等待状态分布 | 手写复杂关联时漏掉上下文或边界 |
| CPU 频率口径 | `linux.cpu.frequency` 生成 `cpu_frequency_counters` 时间区间，`freq` 单位为 kHz；`cpu_freq` 是 CPU 与支持频点的维度表 | 把频点维度当成随时间变化的计数器，或把记录的 cpufreq 状态当成硬件瞬时有效频率 |
| `utid/upid` | 线程和进程 join 使用 trace 内唯一 ID | `tid/pid` 复用导致错配 |
| `dur = -1` | 统计时用 `trace_end() - ts` 替代未闭合 duration | 总耗时和 overlap 计算错误 |
| overlap 过滤 | 时间窗查询使用区间相交条件 | 漏掉跨越窗口边界的长 slice |
| 名称匹配 | 已知全名用 `=`；需要通配时明确使用 `GLOB` 的 `*`、`?` 语义并检查转义 | 把 `LIKE` 中的 `_` 当成普通字符，或让宽泛模式混入同名事件 |
| 区间关联 | 优先使用 `slices.time_in_state` 等公开模块；直接使用 `SPAN_JOIN` 时，输入区间在每个分区内不能互相重叠，并且分区键要匹配 CPU、线程或进程语义 | 区间重复计算或跨对象错配 |
| 私有对象 | 不在项目模板里直接调用以下划线开头的表、视图或宏，例如标准库内部的 `_interval_intersect!` | 上游内部实现变化后模板失效 |
| 未闭合区间 | Android 17 的 `thread_slice_time_in_state` 只纳入 `dur > 0` 的 slice 和线程状态；需要分析 `dur = -1` 时，使用显式边界查询并标注采集结束边界 | 标准库静默排除未闭合记录后，仍把结果当成完整分布 |

下面的查询不依赖示例包名或虚构时间窗。它从 trace 中选择有效经过时间最长的线程 slice，再与同一 `utid` 的 `thread_state` 相交，因此可以直接作为空 trace 语法测试，也可以在一份真实 trace 上演示状态口径。

```sql
WITH candidate_slice AS (
  SELECT
    slice.id,
    slice.ts,
    IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) AS dur,
    slice.name AS slice_name,
    thread_track.utid,
    thread.tid,
    thread.name AS thread_name,
    process.upid,
    process.pid,
    process.name AS process_name
  FROM slice
  JOIN thread_track
    ON thread_track.id = slice.track_id
  JOIN thread
    ON thread.utid = thread_track.utid
  LEFT JOIN process
    ON process.upid = thread.upid
  WHERE IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) > 0
),
target_slice AS (
  SELECT *
  FROM candidate_slice
  ORDER BY dur DESC, id
  LIMIT 1
),
overlap_state AS (
  SELECT
    target_slice.id AS slice_id,
    target_slice.slice_name,
    target_slice.ts AS slice_ts,
    target_slice.dur AS slice_dur,
    target_slice.utid,
    target_slice.tid,
    target_slice.thread_name,
    target_slice.upid,
    target_slice.pid,
    target_slice.process_name,
    thread_state.state,
    MIN(
      thread_state.ts
        + IIF(thread_state.dur = -1, trace_end() - thread_state.ts, thread_state.dur),
      target_slice.ts + target_slice.dur
    ) - MAX(thread_state.ts, target_slice.ts) AS overlap_dur
  FROM target_slice
  JOIN thread_state
    ON thread_state.utid = target_slice.utid
  WHERE thread_state.ts < target_slice.ts + target_slice.dur
    AND target_slice.ts
      < thread_state.ts
        + IIF(thread_state.dur = -1, trace_end() - thread_state.ts, thread_state.dur)
),
normalized AS (
  SELECT
    *,
    CASE state
      WHEN 'R' THEN 'Runnable'
      WHEN 'R+' THEN 'Runnable (Preempted)'
      WHEN 'S' THEN 'Sleeping'
      WHEN 'D' THEN 'Uninterruptible Sleep'
      ELSE state
    END AS state_label
  FROM overlap_state
  WHERE overlap_dur > 0
)
SELECT
  slice_id,
  slice_name,
  slice_ts,
  slice_dur / 1e6 AS slice_dur_ms,
  utid,
  tid,
  thread_name,
  upid,
  pid,
  process_name,
  state_label,
  COUNT(*) AS segments,
  SUM(overlap_dur) / 1e6 AS state_dur_ms
FROM normalized
GROUP BY
  slice_id,
  slice_name,
  slice_ts,
  slice_dur,
  utid,
  tid,
  thread_name,
  upid,
  pid,
  process_name,
  state_label
ORDER BY state_dur_ms DESC;
```

这里选择“最长线程 slice”只为给模板一个可执行目标，正式调查必须把 `target_slice` 换成 scratchpad 已确认的 slice ID 或问题窗口，不能把全局最长项自动当作用户问题的根因。状态时长之和还要与目标 slice 的有效经过时间核对；缺少 `sched` 数据时，两者不会闭合，报告应记录证据缺口。

## 六类调查域：把开放问题拆成可执行动作

`perfetto-trace-analysis` 把调查提示分成 CPU、Graphics、I/O、IPC、Memory、Power 六类。这里不把它们写成清单，而按“触发条件 → 起手证据 → 下一跳 → 误判边界”组织，便于 Agent 执行。

| 调查域 | 触发条件 | 起手证据 | 下一跳 | 常见误判 |
|---|---|---|---|---|
| CPU | 主线程或 RenderThread 长耗时，`Running` / `Runnable` 占比高 | `thread_state`、`sched`、`slices.cpu_time`、`linux.cpu.frequency` | 查调度延迟、同 CPU 竞争、IRQ、cpufreq 状态、CPU 拓扑和采样栈 | 把 `Runnable` 当成 App 正在计算，或根据 cpufreq 状态推断瞬时硬件有效频率 |
| Graphics | 掉帧、首帧慢、GPU 内存高、Surface 提交异常 | `android.frames.timeline`、`android.frames.per_frame_metrics`、RenderThread、可用的 GPU/图形内存轨道 | 匹配 App 与 SurfaceFlinger frame token，再查 BufferQueue、fence、HWC 或 RenderEngine | 只看 App 帧，不查 SurfaceFlinger 与显示提交 |
| I/O | D-state、冷启动首轮慢、缺页事件密集 | `thread_state` 的 `D` 状态、可用的 `io_wait` / `blocked_function`、缺页与块设备事件 | 查页缓存、dm-verity、块设备请求和相关内核线程 | 仅凭 D-state 就断定是存储设备慢 |
| IPC | 客户端等待、Binder 调用密集、跨进程依赖明显 | `android.binder`、Binder slice、flow、服务端进程与耗时 | 查服务端线程状态、慢方法和 Binder 请求洪峰 | 停在“客户端等 Binder”，不追服务端 |
| Memory | LMK、swap 上升、kswapd 活跃、图形内存异常 | 已采集的内存计数器、LMK、PSI、dmabuf / dma_heap、堆图 | 查进程 RSS、swap、GPU buffer、Bitmap 与持有路径 | 只看 Java heap，漏掉 native 或图形内存 |
| Power | 屏灭耗电、无法 suspend、modem 或蓝牙电源轨高 | 可用的电源轨、suspend、唤醒源、网络与厂商功耗轨道 | 查唤醒源、UID 流量、蓝牙 / modem / thermal 事件 | 把缺失电源轨或归因字段解释成零功耗 |

这张表用于减少盲搜。Agent 应从用户问题和已验证事实选择调查域：启动慢通常从启动窗口、主线程状态、I/O 与 Binder 开始；滑动掉帧从 FrameTimeline、UI / RenderThread、SurfaceFlinger 与 CPU 开始；屏灭耗电从 suspend、唤醒源、电源轨与网络归因开始。某个轨道未被采集时，结论应降级为“该证据不可见”，不能写成“该异常不存在”。

## Wall time 与 CPU time 必须分离

长 slice 的 `dur` 是 wall time（经过时间），不等于 CPU time（CPU 运行时间）。它可能覆盖 CPU 执行，也可能覆盖调度等待、Binder、锁、futex 或 I/O 等待。Agent 协议要求每个可疑长 slice 都查 `thread_state`，再按状态选择下一条证据链。

判断顺序分五步：

1. 定位目标 slice 的 `ts`、`dur`、线程和进程。
2. 查同一时间窗内该线程与 `thread_state` 的区间相交。
3. 用 Trace Processor 的调度状态语义解释 `Running`、`R/R+`、`S`、`D` 等值，再计算各状态占比。
4. 按最大状态选择调查域：CPU、调度、Binder / 锁、I/O。
5. 找到阻塞方后，回到全局视角检查同一用户可感知窗口中的竞争事件。

`Running` 表示线程正在 CPU 上执行，后续要看子 slice、采样栈、cpufreq 状态和 CPU 拓扑；`Runnable` 表示线程可运行但尚未被调度，后续要看同 CPU 竞争、IRQ、实时线程和 idle 情况；`Sleeping` 可能对应等事件、锁、Binder 回复或 futex；`Uninterruptible Sleep` 需要结合 `io_wait`、`blocked_function`、内核线程与 block 事件判断。Android 17 的 `slices.time_in_state` 会输出 `io_wait` 和 `blocked_function`，但后两项依赖 `sched/sched_blocked_reason`；`blocked_function` 还受 userdebug 构建与符号可用性限制。

函数名出现在 slice 上，只说明线程处于该标记范围；它不能单独证明 CPU 正在执行该函数。报告要分别给出经过时间、CPU 运行时间或调度状态分布，再用 Binder flow、锁事件、调用栈或内核证据定位等待方。

## 从局部异常到全局复核

复杂 trace 里可能同时存在 App 主线程等待、系统服务慢 Binder、SurfaceFlinger 合成异常和后台 I/O。发现一个异常只证明它存在；归因还需要证明它与用户可感知窗口重合，并能沿依赖关系解释关键路径。

全局复核至少包括四步：

- **长 slice 复核**：在目标时间窗内排序线程 slice，同时保留 `depth` 与 `parent_id`，避免把父子 slice 当成互相独立的耗时。
- **D-state 复核**：统计目标窗口内最长不可中断等待，判断 I/O 或内核等待是否被漏掉。
- **FrameTimeline / Binder 复核**：对 jank、启动、点击无响应类问题，分别确认异常帧和慢 Binder 是否与用户可感知窗口重合。
- **计数器复核**：查看可用的 cpufreq、内存、电源轨、dmabuf 等计数器是否在同一窗口发生变化，并核对单位与采样间隔。

下面的可执行查询仍以 trace 中最长线程 slice 作为演示窗口，并列出与该窗口相交的全部线程 slice。正式调查要用 scratchpad 中已经确认的问题窗口替换 `target_window`；保留完整 slice 时长、相交时长、层级和父节点，才能识别跨边界 slice 与父子重复。

```sql
WITH effective_slice AS (
  SELECT
    slice.id,
    slice.parent_id,
    slice.depth,
    process.name AS process_name,
    thread.name AS thread_name,
    slice.name AS slice_name,
    slice.ts,
    IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) AS dur
  FROM slice
  JOIN thread_track
    ON thread_track.id = slice.track_id
  JOIN thread
    ON thread.utid = thread_track.utid
  LEFT JOIN process
    ON process.upid = thread.upid
  WHERE IIF(slice.dur = -1, trace_end() - slice.ts, slice.dur) > 0
),
target_window AS (
  SELECT ts AS start_ts, ts + dur AS end_ts
  FROM effective_slice
  ORDER BY dur DESC, id
  LIMIT 1
),
candidate AS (
  SELECT
    effective_slice.*,
    target_window.start_ts,
    target_window.end_ts,
    MIN(effective_slice.ts + effective_slice.dur, target_window.end_ts)
      - MAX(effective_slice.ts, target_window.start_ts) AS overlap_dur
  FROM effective_slice
  CROSS JOIN target_window
  WHERE effective_slice.ts < target_window.end_ts
    AND target_window.start_ts < effective_slice.ts + effective_slice.dur
)
SELECT
  id,
  parent_id,
  depth,
  process_name,
  thread_name,
  slice_name,
  ts,
  dur / 1e6 AS slice_dur_ms,
  overlap_dur / 1e6 AS overlap_ms
FROM candidate
ORDER BY overlap_dur DESC, depth, id;
```

`slice_dur_ms` 是完整时长，`overlap_ms` 是 slice 落入窗口的部分。排行按相交时长进行；同一线程上嵌套的父子项仍可能覆盖同一段时间，不能把它们相加成总耗时。结果中出现 `system_server`、SurfaceFlinger 或其他进程的长 slice 时，还要用 flow、调度或帧 token 证明关联，进程名本身不是依赖证据。内核线程不一定拥有 `thread_track` slice，D-state 与调度复核还需要独立查询 `thread_state`、`sched` 和 ftrace 事件。

调查可以在下列条件全部满足后停止：

- 用户提出的问题已经被改写为可验证命题，并由一条带时间关系的证据链回答。
- 候选阻塞关系已经追到服务端、锁持有者、I/O、调度、GPU / 显示提交，或明确记录 trace 在哪一跳缺少数据。
- 与问题相关的竞争假设已经执行查询；无法验证的假设留在待验证项，不写进结论。
- 全局复核没有发现更能解释同一用户可感知窗口的可见证据。这个判断只约束当前 trace 和当前表结构。
- 每条结论都能回到保存的 SQL、结果和版本信息；查询为空时，报告说明空结果能排除的范围。

缺少关键数据源、trace 被截断、时钟域无法对齐或服务端依赖断链时，应停止归因并输出补采方案。继续生成看似完整的根因会越过证据边界。

## 输出模板：证据表、阻塞方、边界与补采建议

Agent 的最终报告是一份可重放的工程调查记录。结构可以固定，条目数量由证据决定：

| 段落 | 内容 | 要求 |
|---|---|---|
| 输入与版本 | trace 受控标识与散列值、设备构建、内核、采集配置、Trace Processor、skill、SQL 包 | 不复制未经脱敏的本机路径或业务数据 |
| 问题窗口 | 场景、目标进程、起止时间、窗口来源 | 时间戳保留 trace 原始单位，并可附换算值 |
| 结论 | 当前 trace 能支持的判断 | 每条都引用证据编号，不规定人为条数 |
| 证据表 | SQL 编号、对象、查询文件、结果、解释 | 每条证据能在 scratchpad 中找到对应记录 |
| 依赖链 | 主体、等待状态、下一跳、服务端或持有者 | 用 flow、token、状态重叠或调用栈连接各跳 |
| 排除项 | 已查但不解释本问题的方向 | 说明排除依据 |
| 可信度 | 证据支持程度与缺失字段 | 不用单一等级掩盖各结论差异 |
| 补采建议 | 缺失数据源、atrace 类别、采样栈、缓冲区或复现场景 | 给出缺失证据与配置字段的对应关系 |
| 优化与验证 | 可修改位置、预期改变的 trace 证据、回归方法 | 机制解释、改动建议和已验证效果分开写 |

报告中的结论应使用“观测 → 依赖 → 归因边界”结构。例如，先记录目标 slice 与状态分布，再写等待关系如何连接到服务端，随后说明调用栈或符号是否足以定位代码。这样不会用一张 UI 截图替代查询，也不会把补采计划写成已经证实的根因。

## Trace 采集规划器

采集规划是协议的前置步骤。用户给出问题类型与复现条件后，Agent 要输出可审阅的 `TraceConfig`、atrace 类别、触发方式、缓冲区规划、采集窗口、预计开销和敏感数据风险。缓冲区大小与采集时长不能写成所有设备通用的常量；它们要根据问题持续时间、事件速率、可接受开销和是否允许触发采集决定，并在预采样后检查丢包、缓冲区覆盖与 trace 截断。

| 问题类型 | 必要数据 | 建议补充 | 缺失风险 |
|---|---|---|---|
| 冷启动 / 热启动 | `sched`、cpufreq、`am`、`wm`、`view`、Binder、App trace marker | 调用栈采样、缺页与块设备事件 | 只能看到阶段耗时，难定位计算或等待方 |
| 滑动 / 掉帧 | Android 12 及以上优先 FrameTimeline；旧版本回退到 `Choreographer#doFrame`、RenderThread、SurfaceFlinger、`gfx`、`view` | GPU 计数器、BufferQueue、fence、dmabuf | 难区分 UI、RenderThread、GPU、SurfaceFlinger 与 HWC |
| ANR / 点击无响应 | `sched`、Binder、input、锁等待、App marker | Java / native 栈、system_server 与目标服务事件 | 依赖链可能断在客户端 |
| I/O 卡顿 | `sched`、`sched_blocked_reason`、块设备与缺页事件 | 内核线程、dm-verity、文件映射 | D-state 无法继续归因，`blocked_function` 可能为空 |
| 内存 / OOM | 内存计数器、LMK、PSI、dmabuf / dma_heap | heapprofd、Java 堆图 | 只能看到结果，看不到分配与持有路径 |
| 功耗 | 电源轨、suspend、唤醒源、网络包 | 蓝牙 / modem / thermal 厂商轨道 | 只能得到设备总量，难归到 UID 或模块 |

采集配置还要经过权限与隐私复核。调用栈、日志、App marker、网络信息和文件名可能带出业务数据；线上采集要按最小数据原则选择生产者、采样频率与保留范围。规划器减少的是缺字段返工，不能绕过设备限制、用户授权或性能开销评估。

## Android 版本与厂商轨道差异

Perfetto SQL 模板不能假设所有 trace 都来自 Pixel 或完整的 userdebug 构建。Android 10 到 Android 17 之间，FrameTimeline、内存分配器轨道、电源轨、`sched_blocked_reason` 和厂商 thermal / display 数据的可见性不同。厂商 ROM 还可能关闭生产者、改用自定义轨道，或因权限与构建类型省略符号。

实际调查时建议把兼容性分成三层：

- **基础表结构层**：`slice`、`sched`、`thread_state`、`counter`、`thread`、`process` 等表由 Trace Processor 暴露，但表存在不代表 trace 中有对应数据。
- **Android 标准库层**：`android.startup.startups`、`android.frames.timeline`、`slices.time_in_state` 等模块还受采集字段限制。FrameTimeline 从 Android 12 开始可用；Android 10/11 需要回退到 UI、RenderThread、SurfaceFlinger slice 和业务 marker。
- **厂商扩展层**：显示、thermal、功耗、调度器等自定义轨道要按设备、ROM、构建和采集配置建立词典，不能直接写成平台通用机制。

涉及调度和内核等待时，Android 17 kernel common 锚点是 `android17-6.18-2026-06_r6`。设备仍可能使用厂商分支与不同配置，报告要同时记录运行设备的内核版本。`io_wait` 需要采到 `sched/sched_blocked_reason`，`blocked_function` 还依赖 userdebug 与符号；电源轨、GPU 计数器和厂商显示轨道也都属于可选证据。可信度应按结论逐项绑定这些条件。

## SQL 模板测试集

Perfetto SQL 模板进入团队工作流后要像代码一样测试。字段变化、标准库模块变化、空结果、`dur = -1`、跨窗口 slice、区间分区错误，都会让 Agent 生成错误结论。

一个可维护的测试集至少包含四类用例：

- **语法冒烟测试**：每条模板在固定 Trace Processor 与 Android 17 标准库组合下可以解析和执行。
- **表结构测试**：模板使用的表、视图、列与公开模块能在固定版本查到。
- **边界测试**：覆盖空结果、未闭合 slice、跨窗口相交、缺少 `sched`、缺少 FrameTimeline 等情况。
- **语义测试**：使用可审计的合成 trace 或固定 golden trace 验证输出，例如状态区间不能越过目标窗口，父子 slice 不能被误加为独立耗时。

空 trace 只能证明 SQL 在零行输入下可解析，不能证明关联、单位和归因正确。Perfetto 的差分测试会把输入 trace、查询或 metric 的输出与固定预期结果比较；项目模板至少要为启动、帧、Binder、I/O 与功耗查询保留代表性 trace、预期输出、Trace Processor 版本和标准库提交。

## 源码与 trace 关联

Perfetto 提供事件、状态和时间关系，优化动作通常还要回到源码。Agent 报告定位到 slice、Binder 方法或 native 符号后，应继续建立到 AOSP 或业务代码的映射。

常见映射路径有四种：

- **slice 名称 → App trace marker**：回到产生 marker 的业务代码，确认标记范围；Java 可从 `Trace.beginSection()` 等调用点查起，native marker 则查对应 ATrace API。
- **Binder 方法 → Framework 服务**：从接口描述符、transaction、服务名与服务端进程映射到固定标签的 AOSP 实现，再结合服务端线程状态判断阻塞点。
- **native 符号 → AOSP / vendor 模块**：用符号、构建 ID、进程与调用栈定位同一次构建的二进制；缺少匹配符号时标注 vendor 闭源边界。
- **FrameTimeline / SurfaceFlinger → 图形栈章节**：队列、fence、BufferQueue、HWC 等机制回到 2.13、2.16、13.14，不在报告里重复写原理。

源码关联要固定版本边界。平台代码使用 `android-17.0.0_r1`，内核使用 `android17-6.18-2026-06_r6`，业务与厂商代码记录仓库提交和构建 ID。trace 证据可以证明某个窗口里的对象、状态和依赖，源码用于解释这条构建路径怎样产生对应事件。缺少调用栈、符号、transaction 对应关系或业务 marker 时，不能把 trace 现象直接写成具体代码根因。

## 官方资料与固定版本

- [`android/skills` Perfetto profilers，commit 4328beaf](https://github.com/android/skills/tree/4328beaf36f00265db107eb316f9add6b8764144/profilers)
- [Perfetto v57.1 release notes](https://github.com/google/perfetto/releases/tag/v57.1)
- [Perfetto v57.2 release notes](https://github.com/google/perfetto/releases/tag/v57.2)
- [Using AI with Perfetto](https://perfetto.dev/docs/getting-started/using-ai)
- [Android 17 固定标签的 Perfetto SQL 标准库](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/)
- [android.startup.startups](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/startup/startups.sql)、[android.frames.timeline](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/timeline.sql)、[android.frames.per_frame_metrics](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/frames/per_frame_metrics.sql)
- [android.binder](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/android/binder.sql)、[slices.with_context](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/with_context.sql)、[slices.time_in_state](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/time_in_state.sql)、[slices.cpu_time](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/slices/cpu_time.sql)
- [sched.with_context](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/sched/with_context.sql)、[linux.cpu.frequency](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/frequency.sql)、[linux.cpu.utilization.process](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/utilization/process.sql)
- [Android 17 kernel common 固定标签](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
- [Trace Processor](https://perfetto.dev/docs/analysis/trace-processor)
- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)
- [SQL tables](https://perfetto.dev/docs/analysis/sql-tables)
- [Trace Processor diff tests](https://perfetto.dev/docs/contributing/testing)

## 小结

Agent 辅助 Perfetto 分析的底线是可复查：输入完整，scratchpad 区分事实与假设，SQL 固定执行环境并检查表结构，长 slice 分离经过时间与 CPU 运行时间，候选瓶颈经过依赖追踪和全局复核。报告还要写清采集缺口、版本边界与停止条件，才能让另一名工程师在同一份 trace 上重放结论。
