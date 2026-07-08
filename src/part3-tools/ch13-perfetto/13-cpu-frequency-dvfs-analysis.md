---
title: "Perfetto CPU 频率与 DVFS 关联分析"
chapter: "13.13"
section: "13.13"
status: finalized
drafted_date: "2026-05-16"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
last_verified: "2026-05-16"
last_verified_against: "Perfetto cpu-freq docs + Linux cpufreq/cpuidle docs + arXiv 2507.02135v1"
confidence: medium
tags: [perfetto, cpu-frequency, dvfs, power, scheduling]
related_chapters: ["5.2", "5.4", "11.1", "13.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/官方文档/AOSP 结构"
material_paths:
  - "Cubox/Perfetto查看CPU 频率部分指导-2026-05-03.md"
  - "论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md"
  - "DeepResearch/2026-05-11-soc-platform-diff-dimensity-scheduling.md"
sources:
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-freq"
  - type: official
    path: "https://perfetto.dev/docs/analysis/trace-processor"
  - type: official
    path: "https://docs.kernel.org/admin-guide/pm/cpufreq.html"
  - type: official
    path: "https://docs.kernel.org/admin-guide/pm/cpuidle.html"
  - type: paper
    path: "https://arxiv.org/abs/2507.02135"
  - type: obsidian
    path: "Cubox/Perfetto查看CPU 频率部分指导-2026-05-03.md"
  - type: obsidian
    path: "论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task6_result: "pass-light-edit"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-28"
last_task6_at: "2026-05-28T04:13:00+08:00"
last_task6_review_log: "logs/review/2026-05-28-04-review.md"
last_task6_audit: "2026-06-21"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-28 Task6：Task2B fixed-lite 后复审通过；L1/L2 小修 1 处，禁用词与高频词扫描无命中；outline 10/10 覆盖；无新增 L3/L4 回炉项。Task9 result 仍为 needs-rework，未自动晋升。"
task9_state: reviewed
task2b_state: "fixed"
task9_result: pass-tech-review
task2b_result: "fixed-lite"
last_task2b_lite_at: "2026-05-28"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-28"
last_task9_at: "2026-05-28T04:30:00+08:00"
task9_review_notes: "2026-05-28 Task9 04:30：pass-tech-review；无 P0/P1；queue 无 pending，Task6 已通过，自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-05-28-04-deep-review.md"
last_task9_audit: "2026-07-09"
---

# 13.13 Perfetto CPU 频率与 DVFS 关联分析

<!-- outline-start -->
## 要点

### 🔹 采集入口：`power/cpu_frequency`、`power/cpu_idle` 与 `linux.sys_stats`
说明事件驱动与轮询两种 CPU 频率来源的差异，明确 `cpufreq_period_ms` 适合补齐 trace 开头缺少初始频率的问题。

### 🔹 CPU 频率、空闲状态与线程 Running 的关系
把 `sched`、`thread_state`、`cpufreq`、`cpuidle` 放到同一条判断路径里，避免把 Running 时间直接等同于高频运行时间。

### 🔹 大小核与 CPU cluster 的频率轨道识别
利用 `linux.system_info`、`cpu_freq` 表和可用频点识别 cluster，说明同一 cluster 内多个 CPU 同步变频的常见表现。

### 🔹 DVFS 调节滞后对启动、滑动与后台任务的影响
覆盖短突发任务、连续渲染负载、后台批处理三类场景，说明频率爬升、降频滞后和空闲状态恢复成本如何影响性能判断。

### 🔹 Perfetto SQL：从 counter 表重建频率时间线
给出 `counter` + `cpu_counter_track` 的查询方向，正文提供可直接复用的 SQL 模板和结果解释方式。

### 🔹 端侧 AI 推理中的 CPU/GPU governor 协同问题
基于移动端 LLM DVFS 论文素材，说明 CPU、GPU、内存 governor 分开调节时可能出现的能效错配，并标注设备与模型边界。

### 🔹 误判清单：USB、空闲态、缺失事件与厂商 governor
列出 trace 采集和解释时最容易出错的条件，包括 USB 保持唤醒、空闲态下频率值含义变弱、部分平台不暴露频率事件、厂商调度策略不可外推。

## 扩展

### 🔸 与 EAS / uclamp / thermal 的交叉验证
结合 5.2、5.4、11.1 节，补充 CPU capacity、任务迁移、降频与温控事件的组合判断。

### 🔸 线上采集能力边界
对比本地 Perfetto、Android Studio System Profiler、ProfilingManager 返回 trace 的字段可见性和隐私裁剪边界。

### 🔸 典型 SQL 模板集
可拆出 CPU 频率分布、Running 时间加权频率、cluster 迁移前后频率变化、渲染帧窗口内频率统计四类模板。

<!-- outline-end -->

Perfetto 里的 CPU Frequency 轨道回答的是“这个 CPU 当时被请求或报告到什么频率”，线程轨道回答的是“这个线程当时处于什么调度状态”。两条轨道要放在同一个时间窗里读：线程 Running 但频率低，才可能指向 DVFS 或温控；线程 Runnable 很长，问题更接近调度排队；CPU 已经 idle 时，频率值常常只剩上一段运行频率的残留语义。

这一节把 `sched`、`thread_state`、`cpufreq`、`cpuidle` 和 SQL 查询放在一条判断路径里，用来处理三类问题：启动短突发为什么没跑满频、滑动掉帧是不是频率没升起来、后台批处理为什么把功耗拖长。

## 采集入口：事件、轮询和系统信息

Perfetto 采集 CPU 频率有两条来源。`power/cpu_frequency` 走 ftrace 事件，只有内核 cpufreq scaling driver 改频时才记录一条事件；`linux.sys_stats` 走 sysfs 轮询，按 `cpufreq_period_ms` 周期读取 `/sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_cur_freq`。前者时间点准，后者适合补 trace 开头的初始频率缺口。

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-freq]

这段配置用于同时抓频率变更、空闲态变更、当前频率轮询和可用频点列表；如果后续要计算线程 Running/Runnable 占比，还要同时启用 sched 事件。

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup_new"
      ftrace_events: "sched/sched_waking"
    }
  }
}

data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      cpufreq_period_ms: 500
    }
  }
}

data_sources: {
  config {
    name: "linux.system_info"
  }
}
```

`power/cpu_frequency` 把每次频率变化写成 counter 事件；`power/cpu_idle` 给出 CPU 进入、退出 idle state 的时间点；`linux.system_info` 在 trace 开始时记录每个 CPU 支持的频率列表，后续可用 `cpu_freq` 表辅助识别大小核和 cluster。[来源: Cubox/Perfetto查看CPU 频率部分指导-2026-05-03.md]

采集配置有两个边界。

- 事件驱动会漏掉“开头已经在某个频率上”的状态。短 trace 里，如果某个 CPU 几秒内没有改频，左侧会出现空白；这不是 CPU 没频率，而是 trace 没拿到变更事件。
- sysfs 轮询有采样间隔。`cpufreq_period_ms: 500` 能补初始值，但不能精确描述 10 ms 级的瞬时升频和降频。分析启动和单帧掉帧时，事件驱动仍要保留。

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-freq]

## Running、频率和空闲态不能混读

线程处于 Running，只说明调度器把它放到了某个 CPU 上执行。它是否跑在高频、跑在大核、是否刚从深 idle state 恢复，要继续看 `cpufreq`、`cpuidle` 和 CPU 编号。

| 观察组合 | 更接近的判断 | 下一步 |
|---|---|---|
| Thread Running 长，CPU 频率高 | 代码执行成本高 | 看函数采样、atrace slice、simpleperf |
| Thread Running 长，CPU 频率低 | DVFS 未升频、被限频或跑在小核 | 看 `cpufreq`、thermal、uclamp、CPU 编号 |
| Thread Runnable 长，CPU 频率高 | CPU 忙但目标线程没拿到时间片 | 看同核上正在 Running 的线程和优先级 |
| Thread Sleeping / D 长，CPU 频率高 | 线程在等锁、Binder、I/O 或内核资源 | 回到阻塞原因和调用栈，不按 CPU 算力判断 |
| CPU idle 且频率轨保持某个值 | 频率值语义变弱 | 结合 `cpuidle`，不要把 idle 时的频率当运行频率 |

Perfetto 文档给了一个容易忽略的点：在很多 SoC 上，CPU idle 后会 clock-gated，频率轨显示的常常是进入 idle 前的上一段运行频率。也就是说，灰色 idle 区间上的高频不等于 CPU 还在高频耗电。功耗判断要结合 idle state 和整机功耗数据，详见 11.1 节。

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-freq]

对 App 卡顿来说，推荐按这个顺序读：

1. 在 UI 线程或 RenderThread 找到慢 slice，例如 `Choreographer#doFrame`、`DrawFrame`、`performTraversals`。
2. 看 slice 内线程状态占比。Running 占比高再看频率；Runnable 占比高先看调度排队；Sleeping / D 占比高转向等待来源。
3. 对 Running 子区间取 CPU 编号和频率。小核低频上的长 Running，与大核高频上的长 Running，不应归为同一类问题。
4. 把前后 50-200 ms 的 `cpuidle` 加进来。短突发任务常常受 idle 退出和升频滞后共同影响。

这套顺序能避免一个常见误判：只看到绿色 Running 长，就断定“CPU 被打满”。Running 是调度状态，不是频率状态，也不是能耗状态。

## 识别大小核和 cluster

Linux CPUFreq 用 policy 表示一组共享 P-state 控制接口的 CPU。多个 CPU 如果指向同一个 policy，写一次硬件接口会同时影响这组 CPU。Android 大小核设备上，这组 CPU 通常对应一个 cluster，所以 Perfetto 里经常能看到 CPU 0-3 同步变频、CPU 4-6 同步变频、CPU 7 单独变频。

[已验证: 官方文档, docs.kernel.org/admin-guide/pm/cpufreq.html]

Perfetto 的 `linux.system_info` 会记录每个 CPU 的 `scaling_available_frequencies`，Trace Processor 解析后可通过 `cpu_freq` 表读取。当前 Trace Processor 的 `cpu` 表在有数据时还会暴露 `cluster_id` 与 `capacity`，识别顺序应先看 `cpu.cluster_id` / `capacity`，再用频点集合和同步变频交叉验证；缺字段时退回 sysfs `policy*/affected_cpus`。

这段 SQL 用于查看 trace 中记录到的可用频点，帮助识别 cluster。

```sql
SELECT c.cpu, c.cluster_id, c.capacity, cf.freq
FROM cpu_freq AS cf
JOIN cpu AS c ON cf.ucpu = c.id
ORDER BY c.cpu, cf.freq;
```

结果先按 `cluster_id` / `capacity` 分组；字段缺失或全为默认值时，再横向对比每个 `cpu` 的频点集合。集合完全相同且频率变化同步的一组 CPU，可作为同一 cluster 处理；只有最高频率高低差异时，再结合设备 SoC 拓扑确认小核、大核和超大核的编号。

如果 trace 里没有 `cpu_freq` 表数据，可以退回设备 sysfs：

```bash
adb shell 'for p in /sys/devices/system/cpu/cpufreq/policy*; do echo $p; cat $p/affected_cpus; cat $p/scaling_available_frequencies; done'
```

这条命令在设备端读取 policy、影响的 CPU 和可用频点。它适合本地复现实验，不适合直接写成所有线上设备都能读取的能力，因为权限、SELinux、厂商内核导出项都会影响结果。

## DVFS 滞后怎样影响三类场景

DVFS 的目标是在性能和功耗之间选频率。Linux 文档把这件事拆成 CPUFreq core、scaling governor 和 scaling driver 三层：governor 估计需要的 CPU capacity，driver 写平台硬件接口，policy 表示一组共享调频接口的 CPU。

[已验证: 官方文档, docs.kernel.org/admin-guide/pm/cpufreq.html]

### 启动短突发

冷启动早期有大量 1-10 ms 的短任务：类加载、资源解析、Binder 往返、View inflate、首次 draw。若 governor 还没把目标 cluster 拉到合适频率，UI 线程会在低频 Running 上消耗更长 wall time。trace 表现是：关键 slice 几乎都在 Running，但 `cpufreq` 在 slice 中段或结束后才抬升。

这类问题不能只靠“提前拉满频”解决。高频时间过长会增加热量，后续可能更早触发 thermal 限频。实战里更稳的动作是减少启动短任务数量，合并 I/O，避免在首帧前制造碎片化 CPU burst；需要系统侧配合时，再看 ADPF / PerformanceHint、uclamp、Power HAL 策略。DVFS 机制详见 5.4 节。

### 连续渲染负载

滑动、动画和游戏帧循环有稳定节奏。理想情况是 CPU cluster 在前几帧内升到能覆盖帧预算的频率，随后保持在相对稳定的频点。如果 trace 中每隔几帧出现一次低频 Running 长块，再伴随 Runnable 抖动，说明 governor 在负载谷底降得太快，下一帧来时又要重新升频。

判断时要把帧窗口切开：UI 线程、RenderThread、GPU 提交线程不一定在同一个 CPU 上。某一帧掉了，可能是 UI 线程低频，也可能是 RenderThread 被迁到小核，或 GPU/显示侧等待。CPU 频率只解释 CPU 侧执行速度，不能替代渲染管线分析，相关渲染机制详见 Part 1 的 2.x 章节。

### 后台批处理

后台压缩、数据库迁移、日志整理这类任务对单帧时序不敏感，但会拉长 CPU active 时间。频率过低时，单次任务耗时拉长，CPU 更晚回到 idle；频率过高时，任务结束更快，但瞬时功耗和热量上升。哪种更省电，取决于任务类型、cluster 能效曲线和 idle state 恢复成本。

CPUIdle 文档列出两个和性能判断直接相关的参数：target residency 表示进入该状态至少要停留多久才划算，exit latency 表示从该状态恢复执行的最坏时间。后台任务如果频繁把 CPU 从深 idle 拉醒，问题常常不在单次 CPU 频率，而在唤醒频率和任务批量化策略。

[已验证: 官方文档, docs.kernel.org/admin-guide/pm/cpuidle.html]

## 用 SQL 重建频率时间线

Perfetto 把 CPU 频率和 idle state 都建模为 counter。`counter` 存时间戳和值，`cpu_counter_track` 存 track 名称和 CPU 编号。`cpuidle` 值里的 `0xffffffff`（4294967295）表示回到非 idle 状态。

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-freq]

这段 SQL 用于快速检查 trace 是否抓到了频率和 idle 数据。

```sql
SELECT
  c.ts,
  t.name,
  t.cpu,
  c.value
FROM counter AS c
JOIN cpu_counter_track AS t ON c.track_id = t.id
WHERE t.name IN ('cpufreq', 'cpuidle')
ORDER BY c.ts
LIMIT 200;
```

如果这里没有 `cpufreq` 行，要回到采集配置检查 `power/cpu_frequency` 和 `linux.sys_stats`；如果没有 `cpuidle` 行，Perfetto UI 可能不会显示组合轨，SQL 里也无法判断 idle 区间。

要把“线程在哪个频率上运行”算出来，需要把调度切片和频率区间做时间交集。Perfetto 文档提供的 `SPAN_JOIN` 正适合这个场景。

```sql
CREATE VIEW sp_sched AS
SELECT s.ts, s.dur, s.ucpu AS cpu_id, c.cpu, s.utid
FROM sched AS s
JOIN cpu AS c ON s.ucpu = c.id
WHERE dur > 0;

CREATE VIEW sp_frequency AS
SELECT
  c.ts,
  LEAD(c.ts) OVER (PARTITION BY c.track_id ORDER BY c.ts) - c.ts AS dur,
  t.cpu AS cpu_id,
  c.value AS freq
FROM counter AS c
JOIN cpu_counter_track AS t ON c.track_id = t.id
WHERE t.name = 'cpufreq';

CREATE VIRTUAL TABLE sched_with_frequency
USING SPAN_JOIN(sp_sched PARTITIONED cpu_id, sp_frequency PARTITIONED cpu_id);

SELECT ts, dur, cpu, utid, freq
FROM sched_with_frequency
WHERE dur > 0;
```

这张临时表会把每段调度运行时间切成更小的片段，每个片段带上当时 CPU 的频率。后续可以按线程、进程、帧窗口继续聚合。`SPAN_JOIN` 要求同一 partition 内输入 span 不重叠；对 `sched` 和按 track 重建的 `cpufreq` 区间来说，这个条件通常成立。

这个模板计算某个线程在 Running 时间上的频率分布。`target_tid` 换成线程的 Linux tid，结果能回答“它主要跑在哪些频点上”。

```sql
WITH target_thread AS (
  SELECT utid
  FROM thread
  WHERE tid = $target_tid
), running_freq AS (
  SELECT swf.dur, swf.freq
  FROM sched_with_frequency AS swf
  JOIN target_thread USING (utid)
  WHERE swf.dur > 0 AND swf.freq IS NOT NULL
)
SELECT
  freq,
  SUM(dur) / 1000000.0 AS running_ms,
  ROUND(100.0 * SUM(dur) / SUM(SUM(dur)) OVER (), 2) AS pct
FROM running_freq
GROUP BY freq
ORDER BY running_ms DESC;
```

这个结果只统计 Running 时间，不包含 Runnable 排队和 Sleeping 等待。若一个慢 slice 的 wall time 很长，但这里的 Running 时间很短，CPU 频率不是主因，应回到线程状态占比。

## 端侧 AI 推理里的 governor 错配

移动端 LLM 推理把 DVFS 问题放大了。arXiv 2507.02135 的实验在 Pixel 7 / Pixel 7 Pro 上测试 llama.cpp 等移动端 LLM 推理框架，发现即使模型以 GPU 计算为主，CPU 仍要参与 OpenCL command queue 管理，内存频率也影响 KV cache 访问。CPU、GPU、内存 governor 各自按本组件利用率调频时，可能把同一个推理任务拆成互相不知情的三个局部决策。

[已验证: arXiv 2507.02135v1]

论文中的一个现象很适合放进 Perfetto 分析口径：decode 阶段 GPU 利用率不一定持续打满，GPU governor 可能降频；CPU 侧看到自己的利用率也不高，EAS / CPU governor 继续降频；但 GPU 仍依赖 CPU 及时喂下一批 kernel，两个组件同时降频会拉长 token 输出时间。论文实验条件是 Android 13、root/open 设备、battery bypass、屏幕关闭、Monsoon 0.2 ms 功耗采样、ShareGPT 数据集和固定频率搜索口径；在这个前提下，Pixel 7 / 7 Pro 上部分 prefill / decode 延迟有 40.4% 的优化空间，FUSE 方案让 TTFT 降低 7.0%-16.9%，TPOT 降低 25.4%-36.8%。

[来源: 论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md]

这组结论不能外推成“LLM 推理都要锁高频”。它的设备边界是 Pixel 7 / Pixel 7 Pro，SoC 是 Google Tensor G2，模型和框架以论文实验为准。放到 Android 性能分析里，更稳的用法是把它当成一个提醒：端侧 AI 推理要同时看 CPU 频率、GPU 频率、内存带宽、温控和每 token 延迟；只看 CPU Frequency 轨，会漏掉多组件 governor 之间的错配。

分析端侧 AI 推理 trace 时，建议额外记录 GPU counter、thermal 事件、CPU sched、`cpufreq`、内存带宽或厂商可用的 DDR 频率数据。若设备不暴露 GPU/DDR 频率，CPU 侧结论只能标成局部证据。

## 误判清单

- **USB 采集会影响 idle state**：Perfetto 文档提到，多数 Android 设备插着 USB 时不会进入某些 idle state，因为 USB driver stack 持有 wakelock。用 USB 抓功耗 trace 时，idle 分布可能比真实使用场景浅。
- **频率事件缺失不等于 CPU 没跑**：`power/cpu_frequency` 只在变频时出事件。trace 开头空白通常要靠 `linux.sys_stats` 补初始频率。
- **idle 区间上的频率不能当运行频率**：CPU clock-gated 后，频率值可能只是进入 idle 前的上一段运行值。看功耗时要结合 `cpuidle` 和 11.1 节的功耗模型。
- **UI 不显示不等于 SQL 没数据**：Perfetto 文档提到，某些情况下 UI 不渲染 cpufreq track，但数据仍可通过 Trace Processor 查询。遇到 UI 空白要先跑 SQL。
- **Intel 与 ARM 暴露能力不同**：Perfetto 文档说明，现代 Intel CPU 的内部 DVFS 可能不向内核暴露频率变更事件；Android ARM SoC 上通常更可靠，但也受厂商内核影响。
- **厂商 governor 不可外推**：联发科、高通、三星、Google Tensor 的 EAS 参数、Power HAL、thermal 策略和 GPU governor 都可能不同。没有实机 trace 和源码证据时，只能写设备级结论。
- **thermal 和 uclamp 会改变解释**：同一段低频 Running，可能来自 governor 未升频，也可能来自 thermal 限频、`uclamp_max`、省电模式或厂商策略。要与 5.2、5.4、11.1 节交叉验证。

## 与 EAS、uclamp、thermal 的交叉验证

Perfetto CPU Frequency 分析只覆盖“观察到的频率结果”。要解释结果来源，还要把三层信号接上：

- **EAS / task placement**：看线程是否被放到合适 cluster，详见 5.2 节。若 UI 线程持续在小核低频 Running，先确认是否有迁移、优先级、uclamp 或 top-app 状态问题。
- **schedutil / DVFS**：看频率是否跟随 utilization 变化，详见 5.4 节。短 burst 结束后才升频，属于典型调频滞后观察点。
- **thermal / power model**：看是否有温控限频、功耗归属异常或 sustained workload，详见 11.1 节和热管理相关章节。

联发科调度源码调研也提示了一个边界：AOSP / Linux 主线能解释通用 cpufreq、schedutil、uclamp、EAS 框架；vendor-specific energy model、freq table、Power HAL 策略常在厂商内核或闭源组件里。正文里不应把开源框架行为写成所有设备的最终调度策略。[来源: DeepResearch/2026-05-11-soc-platform-diff-dimensity-scheduling.md]

## 线上采集能力边界

本地 Perfetto 能通过完整 TraceConfig 记录 `linux.ftrace`、`linux.sys_stats` 和 `linux.system_info`。线上能力要分两类看：

- **应用主动请求的 system trace**：Android 15 起 `ProfilingManager` / AndroidX Profiling 可让应用请求 system trace、heap dump、heap profile、stack sampling。返回文件仍受平台限流、隐私裁剪和设备策略影响，不能假设和本地 `adb perfetto` 完全一致。详见 14.7 节。
- **Android Studio / System Profiler**：适合本地复现和交互式查看，但采集 preset 可能不包含所有 ftrace event。遇到频率轨缺失，回到 TraceConfig 或 SQL 检查。

线上 trace 里如果缺少 `power/cpu_idle`、GPU counter 或 thermal 信息，结论要收窄到“CPU 频率观察”。不要把它扩成整机能耗判断。

## SQL 模板集

这组模板可作为独立查询片段维护。

| 模板 | 回答的问题 | 依赖表 |
|---|---|---|
| CPU 频率分布 | 某个 CPU / cluster 在哪些频点停留更久 | `counter`, `cpu_counter_track` |
| Running 时间加权频率 | 某个线程 Running 时主要处于哪些频点 | `sched`, `thread`, `counter`, `cpu_counter_track`, `SPAN_JOIN` |
| cluster 迁移前后频率变化 | 线程从小核迁到大核前后频率是否同步变化 | `sched`, `thread`, `cpu_freq`, `counter` |
| 帧窗口内频率统计 | 掉帧窗口是否伴随低频或升频滞后 | `slice`, `sched`, `counter`, `SPAN_JOIN` |

使用这些模板时要保留两个字段：`cpu` 和 `utid`。前者防止把不同 cluster 的频率混在一起，后者防止 Linux tid 复用带来的误匹配。Trace Processor 文档推荐用 `utid` / `upid` 做线程和进程的唯一标识，这一点在长 trace 中尤其要保留。

[已验证: 官方文档, perfetto.dev/docs/analysis/trace-processor]
