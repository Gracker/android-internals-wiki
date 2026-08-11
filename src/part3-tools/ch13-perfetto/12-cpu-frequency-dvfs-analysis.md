---
title: "Perfetto CPU 频率与 DVFS 关联分析"
chapter: "13.12"
section: "13.12"
status: finalized
drafted_date: "2026-05-16"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
last_verified: "2026-08-07"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1 Perfetto sources; Android common kernel android17-6.18-2026-06_r6 CPUFreq/CPUIdle sources; arXiv 2507.02135v1 with explicit Android 13 Pixel/Tensor G2 boundary; 2026-08-07 rework cleared pending-verification/thin-source flags"
last_rework_at: "2026-08-07T21:35:15+08:00"
last_rework_run_id: "20260807-213515-rework-952e31cf"
last_rework_log: "logs/rework/2026-08-07-20260807-213515-rework-952e31cf-rework.md"
rework_result: "ready-for-review"
rework_notes: "2026-08-07 rework：复核 pending-verification-marker/thin-source-marking；补齐 frontmatter 精确源码锚点，正文增加证据边界说明，去除未使用的 DeepResearch material 路由；章节回流 ready-for-review 等待 Task6/Task9 复审。"
confidence: medium-high
tags: [perfetto, cpu-frequency, dvfs, power, scheduling]
related_chapters: ["5.2", "5.4", "11.1", "13.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/官方文档/AOSP 结构"
material_paths:
  - "Cubox/Perfetto查看CPU 频率部分指导-2026-05-03.md"
  - "论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md"
sources:
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/docs/data-sources/cpu-freq.md"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/common/cpu_freq_info.cc"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/frequency.sql"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/idle.sql"
  - type: source
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/tables/metadata_tables.py"
  - type: source
    path: "https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/pm/cpufreq.rst"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/pm/cpuidle.rst"
  - type: paper
    path: "https://arxiv.org/abs/2507.02135"
  - type: obsidian
    path: "Cubox/Perfetto查看CPU 频率部分指导-2026-05-03.md"
  - type: obsidian
    path: "论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md"
pipeline_stage: finalized
task6_state: reviewed
task6_result: rework-applied
reviewed_by: "hermes-aiw-review-finalize-apply"
reviewed_date: "2026-08-08"
last_task6_at: "2026-08-08T14:05:39+08:00"
last_review_finalize_at: "2026-08-08T14:05:39+08:00"
last_review_finalize_run_id: "20260808-140539-40d25f76"
last_task6_review_log: "logs/review/2026-05-28-04-review.md"
last_task6_audit: "2026-06-21"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-28 Task6：Task2B fixed-lite 后复审通过；L1/L2 小修 1 处，禁用词与高频词扫描无命中；outline 10/10 覆盖；无新增 L3/L4 回炉项。Task9 result 仍为 needs-rework，未自动晋升。"
task9_state: reviewed
task2b_state: "fixed"
task9_result: rework-applied
task2b_result: "fixed-lite"
last_task2b_lite_at: "2026-05-28"
task9_reviewed_by: "hermes-aiw-review-finalize-apply"
task9_reviewed_date: "2026-08-08"
last_task9_at: "2026-08-08T14:05:39+08:00"
task9_review_notes: "2026-05-28 Task9 04:30：pass-tech-review；无 P0/P1；queue 无 pending，Task6 已通过，自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-05-28-04-deep-review.md"
last_task9_audit: "2026-07-09"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-13
---

# 13.12 Perfetto CPU 频率与 DVFS 关联分析

平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`，内核锚点是 `android17-6.18-2026-06_r6`。Perfetto 的 CPU Frequency 轨道记录软件可见的频率状态，线程轨道记录调度状态。两者落在同一时间窗，才能回答“线程 Running 时，所在 CPU 报告了什么频率”。

证据边界是：频率轨并非硬件时钟探针。Android 17 内核在 cpufreq 普通切换完成后，把 `freqs->new` 写入 `cpu_frequency`；快速切换路径写入驱动返回的 `freq`。同一 policy 内的在线 CPU 会分别产生事件。`linux.sys_stats` 的轮询结果也只能代表 sysfs 暴露的值。仅凭这些数据，不能断言某段代码获得了对应数量的有效执行周期。

可复核来源分成三层：Android 17 tag 下的 Perfetto 采集、Trace Processor 表和 ProfilingManager 源码；`android17-6.18-2026-06_r6` 下的 CPUFreq、CPUIdle 与 schedutil 内核源码/文档；以及端侧 LLM DVFS 论文中限定在 Pixel 7 / Pixel 7 Pro、Android 13、Tensor G2 和特定推理栈内的实验结果。第三层只用于提供“协同 governor”的诊断视角，论文数字不能外推成 Android 17 或其他 SoC 的通用结论。

## 频率轨记录的是什么

CPUFreq 把调频路径分成 policy、governor 和 scaling driver：

- policy 表示一组共享硬件性能控制接口的 CPU，并维护允许的最小、最大频率与当前频率；
- governor 根据利用率、时序约束等信息提出目标频率；
- scaling driver 把目标提交给硬件，硬件仍可能受固件、温控或内部控制影响。

Android 17 的 `schedutil` 以利用率和容量计算候选频率，再交给 `cpufreq_driver_resolve_freq()` 选择驱动支持的频点。源码还保留 Android vendor hook，厂商可以改写映射结果。默认更新间隔来自 `cpufreq_policy_transition_delay_us(policy)`，不存在跨设备通用的固定调频周期。[Android 17 schedutil 源码](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)

频率证据可以按下面的强弱理解：

| 数据 | 能证明什么 | 不能单独证明什么 |
|---|---|---|
| `power/cpu_frequency` | cpufreq 路径报告了一次频率切换 | 硬件在整个区间都精确运行于该频率 |
| `linux.sys_stats` | 轮询时刻的 sysfs 频率值 | 两次轮询之间的瞬时切换 |
| `power/cpu_frequency_limits` | policy 的最小、最大频率约束发生更新 | 约束由 thermal、Power HAL 还是厂商逻辑触发 |
| `cpuinfo_cur_freq` / `cpuinfo_avg_freq` | 驱动具备相应反馈能力时，更接近硬件观测 | 所有设备都实现并允许读取 |
| PMU / AMU 与硬件功耗计 | 实际执行、周期或能耗的补充证据 | 单靠 Perfetto cpufreq 轨无法替代这些数据 |

Android 17 的 Perfetto 文档和 proto 注释把轮询路径描述为读取 `cpuinfo_cur_freq`，同一版本的 `CpuFreqInfo::ReadCpuCurrFreq()` 实现读取的是 `scaling_cur_freq`。内核文档指出，`scaling_cur_freq` 多数情况下表示 scaling driver 最近请求的 P-state，未必等于硬件瞬时频率。做版本锚定时应以该版本实现为准，并保留文档与实现的差异。[Android 17 Perfetto 采集实现](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/traced/probes/common/cpu_freq_info.cc) [Android 17 CPUFreq 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/pm/cpufreq.rst)

## 采集入口：事件、轮询和系统信息

下面的配置同时采集频率切换、频率限制、空闲状态、调度事件、轮询频率和可用频点。`500 ms` 来自 Android 17 Perfetto 官方示例，只用于补充初始频率和观察慢变化；它不适合还原单帧内的调频过程。

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_frequency_limits"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "sched/sched_wakeup_new"
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

`power/cpu_frequency` 提供切换时间点，`linux.sys_stats` 补充轮询快照，`linux.system_info` 在采集开始时读取可用频点。三条路径可能因驱动、内核配置、权限或 sysfs 导出差异而缺失，采集后应先检查数据完整性。[Android 17 Perfetto CPU frequency 文档](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/docs/data-sources/cpu-freq.md)

事件驱动路径只在频率发生变化时写记录。某个 CPU 在 trace 开头保持原频点，轨道左侧就会留白；这段空白不能解释为 CPU 停止运行。轮询能补快照，却会漏掉采样点之间的切换。面向启动和掉帧的分析要保留事件驱动采集。

`power/cpu_frequency_limits` 值得与频率事件一起抓。Android 17 内核在 policy 限制更新时记录 `min_freq`、`max_freq` 和 policy 的代表 CPU，它能区分“governor 没有请求更高频率”和“当前上限不允许再升频”这两类线索。限制来源仍需结合 thermal、Power HAL、节电模式和厂商代码确认。[Android 17 CPU frequency tracepoint](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/power.h) [Android 17 cpufreq core](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/cpufreq.c)

## Running、Runnable、idle 与频率

线程状态和频率轨回答不同问题：

| 观察组合 | 当前证据支持的判断 | 应补的证据 |
|---|---|---|
| Running 长，报告频率高 | 线程获得 CPU，执行时间较长 | 调用栈、函数采样、缓存与内存停顿、PMU |
| Running 长，报告频率低 | 低频、限频或低容量 CPU 值得检查 | policy limit、thermal、uclamp、CPU capacity、硬件频率反馈 |
| Runnable 长 | 线程可运行却在等待 CPU | 同 CPU 的运行者、优先级、调度类、CPU 压力 |
| Sleeping 长 | 线程主动等待 | 锁、条件变量、Binder、futex、定时器 |
| D 状态长 | 不可中断等待 | I/O、驱动、内核阻塞原因 |
| CPU idle，频率轨保留高值 | 频率值可能是进入 idle 前的残留 | `cpuidle`、唤醒源、设备功耗 |

Running 时间也不能直接换算成“CPU 算力已用满”。相同 wall time 下，指令级并行度、缓存未命中、内存带宽、分支预测、SMT/共享资源和迁核都会改变有效吞吐。频率分析适合定位相关性，根因判断还要依赖调用栈、硬件计数器和对照实验。

分析 App 卡顿时，可以沿着下面的顺序读取：

1. 在 UI 线程或 RenderThread 找到对应帧和慢 slice。
2. 统计 slice 内 Running、Runnable、Sleeping 与 D 状态。
3. 只对 Running 子区间关联 `ucpu`、逻辑 CPU、capacity、频率和 idle 状态。
4. 向前覆盖足够的负载建立阶段，观察唤醒、迁核、policy 限制与升频次序。观察窗应由 workload 周期决定，不套固定毫秒数。
5. 用调用栈、thermal、uclamp、Power HAL 或 PMU 证据验证假设。

Perfetto 的 `cpu_idle_counters` 已把原始值 `4294967295` 转成 `-1`，代表 CPU 回到 active；非负值越大通常表示更深的 idle state。具体 state 含义由 SoC 和 CPUIdle driver 定义，不能跨设备比较数字本身。

CPUIdle 的 target residency 是进入某个状态后至少停留多久才比浅层状态更节能，其中包含进入成本；exit latency 是从唤醒到开始执行第一条指令的最坏时间。短任务的首段延迟可能同时受 idle 退出与升频影响，需要观察任务唤醒前后的完整区间。[Android 17 CPUIdle 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/pm/cpuidle.rst)

## policy、cluster 与 CPU 标识

CPUFreq policy 是调频控制域，cluster 是处理器拓扑或容量分组。很多 Android SoC 的 policy 与 cluster 一一对应，所以多个 CPU 会同步变频；这是一种常见实现，不能当成定义。异构平台也可能让一个 cluster 出现多个 policy，或让多个逻辑 CPU 共享同一 policy。

本地设备上，`policy*/related_cpus` 和 `policy*/affected_cpus` 是判断共享控制接口的直接证据。下面的命令读取 policy 成员、频率限制、governor 和可用频点。

```bash
adb shell 'for p in /sys/devices/system/cpu/cpufreq/policy*; do
  echo "[$p]"
  for f in related_cpus affected_cpus scaling_min_freq scaling_max_freq \
           scaling_governor scaling_available_frequencies; do
    if [ -r "$p/$f" ]; then
      printf "%s: " "$f"
      cat "$p/$f"
    fi
  done
done'
```

输出中的 `related_cpus` 包含 policy 关联的在线和离线 CPU，`affected_cpus` 表示当前在线且受该 policy 影响的 CPU。部分厂商设备不会导出所有文件，缺字段时应记录设备边界，避免补写推测值。

Trace Processor 里有三种容易混淆的标识：

- `cpu` 是设备内的逻辑 CPU 编号；
- `ucpu` 是 Trace Processor 的可连接 CPU 标识，多机或虚拟化 trace 也能保持唯一；
- `cluster_id` 和 `capacity` 来自已采集的处理器信息，用于描述拓扑与相对容量。

只要查询涉及 `sched` 和 CPU counter 的时间交集，就应以 `ucpu` 分区。把 `sched.ucpu` 与 `cpu_counter_track.cpu` 直接比较，会混用两个标识域，在多机 trace 中尤其危险。

下面的查询读取 Android 17 `linux.system_info` 产生的可用频点，并与 CPU 拓扑关联。

```sql
SELECT
  c.cpu,
  c.cluster_id,
  c.capacity,
  cf.freq
FROM cpu_freq AS cf
JOIN cpu AS c ON cf.ucpu = c.ucpu
ORDER BY c.cpu, cf.freq;
```

Android 17 的公开表名是 `cpu_freq`，连接键是两侧的 `ucpu`。后续版 Trace Processor 曾调整相关公开表名；分析 Android 17 trace 时，应以配套 Trace Processor 的 schema 为准。频点集合、`cluster_id`、`capacity` 和同步变频可以互相校验，policy 成员仍以设备 sysfs 或内核源码为准。[Android 17 `cpu_freq` 表定义](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/tables/metadata_tables.py)

## 三类 workload 的判断方法

### 启动短突发

冷启动由类加载、资源解析、Binder 往返、View 构建、编译与首次绘制等阶段组成。关键线程在低频 Running，且频率在关键 slice 结束附近才抬升，可以提出“调频响应晚于该段工作”的假设。还要排除下面几种情况：

- 当前 CPU 属于低容量 policy，线程随后发生迁核；
- policy 的 `scaling_max_freq` 已被 thermal、节电模式或系统策略限制；
- `power/cpu_frequency` 表示请求值，硬件有效频率另有偏差；
- 代码受缓存或内存停顿限制，提高频率对 wall time 的收益有限；
- UI 线程 Running 之外仍有较长 Runnable、Binder 或 I/O 等待。

优化优先落在工作量本身：减少首帧前任务、合并可延后的工作、降低同步 I/O 与跨进程往返。系统侧调优再结合 PerformanceHint/ADPF、uclamp、Power HAL 和目标设备的能效曲线验证，不能从一条低频轨直接推出“锁最高频”。

### 连续渲染负载

滑动、动画和游戏帧循环具有重复节奏。分析时按帧切窗，并分别观察 UI 线程、RenderThread、GPU 提交线程与 SurfaceFlinger。频率升降若总是落后于负载相位，可能带来周期性 wall time 波动；线程迁往不同 capacity CPU、Runnable 排队或 GPU fence 等待也会产生相似画面。

频率高不保证帧能按期完成，频率低也不必然是异常。帧内工作量较少时，低频可能正是能效目标。判断依据应是相同设备、相同温度和相同 workload 下的帧时序与频率变化，并结合 2.x 渲染章节的应用、RenderThread、GPU、合成与显示链路。

### 后台批处理

压缩、数据库迁移、索引和日志整理通常对单帧时序不敏感。低频可能延长 active 时间，高频可能缩短完成时间并提高瞬时功耗。哪种方案能耗更低，取决于电压频率曲线、内存行为、policy 能效、idle state、唤醒次数和 thermal 状态。

频率轨不含电压，也不等价于整机功耗。后台任务的评估至少要同时比较完成时间、CPU active/idle 分布、唤醒次数、温度和硬件功耗数据。高频更快或低频更省电都只能作为待验证假设。

## 用 SQL 重建频率时间线

Android 17 把原始频率和 idle 事件建模为 `counter`，轨道属性放在 `cpu_counter_track`。下面的查询用于确认 trace 是否含有原始数据。

```sql
SELECT
  c.ts,
  t.name,
  t.cpu,
  c.value
FROM counter AS c
JOIN cpu_counter_track AS t ON t.id = c.track_id
WHERE t.name IN ('cpufreq', 'cpuidle')
ORDER BY c.ts, t.cpu
LIMIT 200;
```

`cpufreq` 的值单位是 kHz。`cpuidle` 原始值 `4294967295` 代表退出 idle。结果为空时要回查采集配置和设备支持情况；UI 没有显示轨道时也应执行该查询，因为 Android 17 文档记录过“缺少 idle 事件时 UI 不渲染频率轨，但 SQL 数据存在”的显示问题。

Perfetto 标准库已经把 counter 转成带 `dur` 的区间。下面的查询读取频率区间和规范化后的 idle 区间。

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;
INCLUDE PERFETTO MODULE linux.cpu.idle;

SELECT ts, dur, ucpu, cpu, freq
FROM cpu_frequency_counters
ORDER BY ts, cpu
LIMIT 100;

SELECT ts, dur, cpu, idle
FROM cpu_idle_counters
ORDER BY ts, cpu
LIMIT 100;
```

`cpu_frequency_counters` 同时提供 `ucpu` 与逻辑 `cpu`；`cpu_idle_counters.idle = -1` 表示 active。`dur = -1` 可能表示区间延续到 trace 末尾，做交集或聚合时要按查询目标处理开放区间。[Android 17 frequency 标准库](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/frequency.sql) [Android 17 idle 标准库](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/linux/cpu/idle.sql)

下面的模板用 `ucpu` 对调度区间与频率区间做 `SPAN_JOIN`。它是后续频率分布、迁核和帧窗口查询的公共准备步骤。

```sql
INCLUDE PERFETTO MODULE linux.cpu.frequency;

CREATE PERFETTO VIEW _running_spans AS
SELECT ts, dur, ucpu, cpu, utid
FROM sched
WHERE dur > 0;

CREATE PERFETTO VIEW _frequency_spans AS
SELECT ts, dur, ucpu, freq
FROM cpu_frequency_counters
WHERE dur > 0 AND freq IS NOT NULL;

CREATE VIRTUAL TABLE _running_with_frequency
USING SPAN_JOIN(
  _running_spans PARTITIONED ucpu,
  _frequency_spans PARTITIONED ucpu
);
```

结果中的每一行都是“某线程在某逻辑 CPU 上 Running，且该 CPU 处于某个已知频率区间”的时间交集。使用内连接会舍弃未知频率区间，汇总时应同时报告被覆盖的 Running 时间，防止把缺失数据当成零。

下面的查询以 `com.android.settings` 主线程为可执行示例，统计它在各频点上的 Running 时间。

```sql
WITH target_thread AS (
  SELECT t.utid
  FROM thread AS t
  JOIN process AS p ON t.upid = p.upid
  WHERE p.name = 'com.android.settings'
    AND t.tid = p.pid
),
running_freq AS (
  SELECT swf.dur, swf.freq
  FROM _running_with_frequency AS swf
  JOIN target_thread USING (utid)
  WHERE swf.dur > 0
)
SELECT
  freq,
  SUM(dur) / 1000000.0 AS running_ms,
  ROUND(100.0 * SUM(dur) / SUM(SUM(dur)) OVER (), 2) AS pct
FROM running_freq
GROUP BY freq
ORDER BY running_ms DESC;
```

把包名替换为目标进程名即可复用。`tid = pid` 用于定位 Linux 主线程，随后全程使用 `utid`，从而避开长 trace 中 tid 复用。这里的百分比是“已知频率覆盖范围内的 Running 时间占比”，不能解释为指令占比、周期占比或能耗占比。

下面的查询把 UI 线程 Running 区间裁到 `android_frames` 的帧窗口内，适合检查掉帧附近的频率分布。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  f.frame_id,
  swf.cpu,
  swf.freq,
  SUM(
    MIN(swf.ts + swf.dur, f.ts + f.dur) -
    MAX(swf.ts, f.ts)
  ) / 1000000.0 AS ui_running_ms
FROM android_frames AS f
JOIN _running_with_frequency AS swf
  ON swf.utid = f.ui_thread_utid
 AND swf.ts < f.ts + f.dur
 AND f.ts < swf.ts + swf.dur
WHERE f.process_name = 'com.android.settings'
GROUP BY f.frame_id, swf.cpu, swf.freq
ORDER BY f.frame_id, ui_running_ms DESC;
```

这个结果只覆盖 UI 线程。RenderThread 需要改用 `f.render_thread_utid` 单独查询；GPU、SurfaceFlinger 和显示侧仍要沿渲染链路核对。帧窗口内缺少频率行时，先计算该帧的 Running 时间与频率覆盖率，再讨论低频相关性。

线程迁核可以直接从公共结果里观察。下面的查询列出目标主线程连续 Running 区间之间的 CPU、cluster 与频率变化。

```sql
WITH target_thread AS (
  SELECT t.utid
  FROM thread AS t
  JOIN process AS p ON t.upid = p.upid
  WHERE p.name = 'com.android.settings'
    AND t.tid = p.pid
),
ordered AS (
  SELECT
    swf.ts,
    swf.dur,
    swf.cpu,
    c.cluster_id,
    c.capacity,
    swf.freq,
    LAG(swf.cpu) OVER (ORDER BY swf.ts) AS prev_cpu,
    LAG(c.cluster_id) OVER (ORDER BY swf.ts) AS prev_cluster_id
  FROM _running_with_frequency AS swf
  JOIN target_thread USING (utid)
  JOIN cpu AS c ON c.ucpu = swf.ucpu
)
SELECT *
FROM ordered
WHERE prev_cpu IS NOT NULL
  AND (cpu != prev_cpu OR cluster_id != prev_cluster_id)
ORDER BY ts;
```

该查询展示相邻的已知频率 Running 区间，不保证两行之间没有 Runnable、Sleeping 或未知频率空洞。迁核原因需要结合 `thread_state`、wakeup、uclamp、调度优先级和系统负载判断。

## 端侧 AI 推理中的 governor 协同

论文 *Dissecting the Impact of Mobile DVFS Governors on LLM Inference Performance and Energy Efficiency* 研究了 CPU、GPU 和内存调频各自决策时的能效错配。实验设备是 Pixel 7 与 Pixel 7 Pro，SoC 为 Tensor G2，系统为 Android 13；测试采用 llama.cpp、OpenCL/CLBlast、TinyLlama 1.1B、StableLM-Zephyr 3B 和 Llama-2 7B，并在 root、battery bypass、屏幕关闭和外部功耗采样条件下运行。

在这组实验边界内，独立 governor 相对同能耗的频率组合，部分 prefill/decode 延迟最多增加 40.4%。论文提出的 FUSE 在相同单 token 能耗下，平均降低 7.0%—16.9% 的 TTFT 和 25.4%—36.8% 的 TPOT。[论文页面](https://arxiv.org/abs/2507.02135)

这些数字不能外推到 Android 17、其他 SoC、NPU 后端或不同推理运行时。它们提供的是一种诊断视角：GPU 执行仍依赖 CPU 提交，KV cache 与权重访问受内存系统影响，单看 CPU 利用率可能低估整条推理流水线的时序需求。

端侧推理 trace 至少要把 CPU sched/cpufreq、GPU job 与频率、内存带宽或 DDR 频率、thermal、TTFT、TPOT 和单 token 能耗放在相同实验中。设备不暴露 GPU 或 DDR 数据时，结论应明确限定为 CPU 侧观察。

## 与 EAS、uclamp、thermal 交叉验证

CPU Frequency 是结果信号，解释其来源还要连接下面几组证据：

- **EAS 与 task placement**：确认线程所在 CPU 的 `capacity`、迁核方向和同核竞争，详见 5.2 节；
- **uclamp 与 PerformanceHint**：确认任务的利用率下限、上限及会话提示是否改变 schedutil 输入，详见 5.4 节；
- **CPUFreq policy**：对照 `scaling_min_freq`、`scaling_max_freq`、governor、`cpu_frequency_limits` 和可用频点；
- **thermal 与电源策略**：检查温度、冷却设备、节电模式、Power HAL 和 sustained workload，详见 11.1 节；
- **执行效率**：用 Simpleperf/Perf 采样、PMU、AMU 或厂商计数器排除缓存、内存和前端停顿。

Android 17 通用内核能说明 CPUFreq、schedutil、uclamp、EAS 与 CPUIdle 的框架。设备上的 energy model、频点表、thermal policy、Power HAL 和 vendor hook 可能来自厂商内核或闭源组件。没有目标设备的源码、sysfs 和 trace，结论只能停留在通用框架层。

## 线上与工具预设的采集边界

本地 `adb perfetto` 接受完整 TraceConfig，在设备允许的范围内可以显式启用分析所需的数据源。Android Studio Profiler 使用工具自己的采集配置，版本与入口不同会得到不同字段；分析前应检查 `cpu_counter_track` 和 trace metadata，不应按界面名称推断采集内容。

Android 17 的 `ProfilingManager` system trace 由平台 `Configs` 生成固定配置。该配置包含 compact sched、进程信息、应用 atrace 分类和 SurfaceFlinger FrameTimeline，未启用 `power/cpu_frequency`、`power/cpu_idle`、`linux.sys_stats` 或 `linux.system_info`。system trace 结果还会进入 redaction 流程，并受系统 rate limiter、参数范围和设备配置约束。它可以支持应用侧线上性能采样，却不能替代本地 CPU DVFS TraceConfig。[Android 17 Profiling 配置](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/Configs.java) [Android 17 ProfilingService](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/service/java/com/android/os/profiling/ProfilingService.java)

拿到线上 trace 后，先列出实际存在的数据源和轨道。缺少 idle、policy limit、GPU 或 thermal 时，报告应写成“已观测 CPU 频率与调度状态的相关性”，不能升级为整机能耗或 governor 根因。

## 误判清单

- **USB 改变 idle 条件**：Android 17 Perfetto 文档指出，许多 Android 设备接入 USB 时，USB driver stack 持有 wakelock，部分 idle state 不会出现。USB trace 的 idle 分布未必代表脱线使用。
- **轨道开头空白**：`power/cpu_frequency` 只记录切换，空白可能来自初始值缺失；用轮询补快照，并在 SQL 中报告覆盖率。
- **idle 区间的频率残留**：CPU clock-gated 后，轨道可能保留进入 idle 前的频率。频率值不能替代 idle state 或功耗数据。
- **请求频率等同硬件频率**：`cpu_frequency` 与 `scaling_cur_freq` 多数情况下更接近软件请求或驱动报告值；需要硬件反馈才能讨论有效频率。
- **高频等同高吞吐**：缓存未命中、内存带宽、分支和共享资源会让高频 Running 仍然很慢。
- **低频等同 governor 反应慢**：policy 上限、thermal、uclamp、节电模式、迁核和 vendor hook 都可能限制结果。
- **同步变频等同 cluster**：同步轨迹只能提示共享 policy；用 `cluster_id`、capacity、`related_cpus` 和源码确认拓扑。
- **频率等同功耗**：轨道没有电压、漏电、内存、GPU 和屏幕功耗。整机能耗需要硬件功耗计或可靠的设备级计量。
- **UI 没轨等同没数据**：Android 17 文档记录过 cpuidle 缺失导致 UI 不渲染 cpufreq 的问题，SQL 查询才是数据存在性的判据。
- **厂商策略可以互推**：高通、联发科、三星、Google Tensor 的 policy、Power HAL、thermal 与 GPU/内存调频实现不同，结论必须绑定设备、版本和 workload。

## 查询结果应怎样写进报告

一份可复核的 DVFS 结论至少包含：

1. 设备、构建版本、内核版本、Trace Processor 版本与采集配置；
2. workload、温度、充电/USB、屏幕、节电模式和重复次数；
3. 目标线程的 wall time、Running、Runnable、阻塞与频率覆盖率；
4. CPU 的逻辑编号、`ucpu`、capacity、cluster 与 cpufreq policy；
5. 频率切换、policy limit、idle、迁核和 thermal 的时间关系；
6. 代码或调用栈热点，以及必要的 PMU、AMU、GPU、内存与功耗证据；
7. 明确区分观测、推断和已验证根因。

“目标线程在已知频率覆盖的 Running 时间中，有多少比例落在某频点”是可复核观测。“governor 导致掉帧”属于因果结论，需要对照实验：固定 workload，控制温度与系统状态，改变一个调频相关变量，并确认帧时序随之稳定变化。这样写，频率轨才会从截图线索变成可验证的性能证据。
