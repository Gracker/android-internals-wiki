---

title: Linux 进程调度基础
chapter: '5.1'
section: '5.1'
status: "finalized"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
applicable_versions: Android 6.0 (API 23) - Android 17 (API 37, EEVDF 部分需 6.6+ 内核)
last_verified: '2026-06-11'
last_verified_against: Linux 6.6 sched-design-CFS + kernel/sched/fair.c/debug.c,
  bionic pthread.h android-16.0.0_r1, libprocessgroup task_profiles.json android-16.0.0_r1
confidence: high
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/31-android17-eevdf-scheduler.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.32-linux-610-bpf-dvfs-schedutil-loop.md"
  - "src/part1-fundamentals/ch05-cpu-power/5.34-android17-task-scheduler-optimization.md"
sources:
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-09-CPU.md
- type: blog
  path: Personal-Knowlodge/source/android-systrace-cpu-state-sleep.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_Android性能优化之绑定RenderThread到大核CPU.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-08_wechat_性能测试中的系统资源分析之_CPU.md
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
- type: official
  path: https://docs.kernel.org/scheduler/sched-design-CFS.html
- type: official
  path: https://docs.kernel.org/scheduler/sched-eevdf.html
- type: official
  path: https://man7.org/linux/man-pages/man7/sched.7.html
- type: official
  path: https://source.android.com/docs/core/perf/uclamp
tags:
- scheduler
- CFS
- vruntime
- nice
- sched_setaffinity
- cpuset
- Perfetto
related_chapters:
- '5.2'
- '5.3'
- '2.5'
- '7.3'
---

# 5.1 Linux 进程调度基础

> [!info] 源码锚点
> 正文按 Android 17 / API 37 / `android-17.0.0_r1` 与 kernel `android17-6.18-2026-06_r6` 复核。文中提到旧 CFS、SchedTune 或早期 Android 行为时，会明确标成历史背景，避免与当前实现混用。

## 调度决策链

Perfetto 的 CPU 轨道只展示了收尾步骤：某个线程在某个 CPU 上运行。要解释这一步，需要把调度决策拆成五个问题：

1. 线程是否已经被唤醒，处于 runnable 状态？
2. 它属于哪种调度策略，优先级和 nice 值是多少？
3. 在 fair 调度类中，它是否已经取得运行资格，virtual deadline 是否足够早？
4. affinity、cpuset 和 CPU online 状态允许它去哪些核心？
5. UClamp、CPU capacity、当前负载和能耗模型会让内核倾向于哪个核心、哪个频点？

这五层解决的问题不同。线程长期处于 Runnable，可能是同一 CPU 上有更高调度类的线程，也可能是 fair 竞争者很多；线程只在小核运行，也可能来自 cpuset 限制，而非 EEVDF 选人错误。分析时应从 Trace 证据逐层排除，避免看到一个长条就直接改 nice 或绑核。

线程从睡眠到获得 CPU 的简化路径如下：

```text
Sleeping / blocked
    │  sched_waking / sched_wakeup
    ▼
Runnable：已具备运行条件，在 runqueue 等待
    │  策略、资格、优先级、CPU 约束共同参与选择
    ▼
Running：出现在 sched_slice
    │
    ├─ 主动睡眠、等待锁或 I/O → S / D 等状态
    └─ 仍可运行但被切出         → R 或 R+
```

诊断时先确认线程是否具备运行条件，再检查调度资格和 CPU 约束，并评估是否需要调参。

## 从 CFS 公平性到 EEVDF

### vruntime 仍是公平记账的基础

CFS 从 Linux 2.6.23 开始使用虚拟运行时间描述任务消耗的 CPU 份额。对一个 fair 调度实体，可以用下面的关系理解 vruntime 增量：

```text
delta_vruntime ≈ delta_exec × NICE_0_LOAD / weight
```

`delta_exec` 是实际运行时间，`weight` 来自 nice 值。nice 越小，权重越大，相同实际运行时间产生的 vruntime 增量越少；长期竞争时，这类任务能获得更高的 CPU 份额。

Linux 6.18 的 `kernel/sched/fair.c` 仍通过 `update_curr()` 记账，并在 `calc_delta_fair()` 中按权重换算。变化集中在“下一次选谁”：早期 CFS 偏向 vruntime 最小的实体，当前 fair 调度路径使用 EEVDF 的 eligibility 和 virtual deadline。

### 旧 CFS 的“最左节点”只用于理解历史实现

旧 CFS 把 runnable entity 放入按 vruntime 排序的红黑树，缓存最左节点，从中选择欠 CPU 时间最多的实体。这个模型适合解释两件事：

- vruntime 为什么可以表达长期公平；
- nice 为什么影响 CPU 份额，而不会直接承诺某次唤醒的固定延迟。

在 kernel 6.18 中，继续把红黑树描述成“按 vruntime 排序并永远取最左节点”会得出错误结论。`__enqueue_entity()` 仍使用增广红黑树，但比较关系由 virtual deadline 决定；每个子树还维护 `min_vruntime`，供 `__pick_eevdf()` 快速跳过没有 eligible entity 的分支。

### EEVDF 的两个选择条件

EEVDF 是 Earliest Eligible Virtual Deadline First。Linux 从 6.6 开始迁移到该方案；在 kernel 6.18 中，`pick_eevdf()` 的选人条件可以压缩成两步：

1. **Eligible**：任务的 lag 大于等于 0，说明按公平份额计算，系统仍欠它 CPU 时间。
2. **Earliest virtual deadline**：只在 eligible entity 中选择 virtual deadline 最早者。

Linux 6.18 用加权平均虚拟时间与实体 vruntime 的差值表达 lag。理解方向即可：

```text
lag > 0：任务尚未获得应有份额，具备被补偿的理由
lag < 0：任务已经超出当前公平份额
```

virtual deadline 由本次请求的运行长度和权重共同决定。`update_deadline()` 的核心关系是：

```text
virtual_deadline = vruntime + weighted(slice)
```

默认请求长度来自 `sysctl_sched_base_slice`；若调用者通过 `sched_setattr()` 设置了 fair-class custom slice，Linux 6.18 的 `__setparam_fair()` 会把 `sched_runtime` 限制在 0.1 ms 到 100 ms。这个接口受内核版本、权限和调用方式约束，不能视作普通 Android App 的通用性能开关。

### base_slice 是请求粒度，不是性能承诺

在 `android17-6.18-2026-06_r6` 中，`normalized_sysctl_sched_base_slice` 的源码初值是 700,000 ns，也就是 0.70 ms。默认的 `SCHED_TUNABLESCALING_LOG` 会按在线 CPU 数量进行对数缩放，因此设备上的有效值不能只靠源码常量推断。

启用 `CONFIG_SCHED_DEBUG` 的内核可从下面的 debugfs 节点观察该值：

```shell
adb shell cat /sys/kernel/debug/sched/base_slice_ns
```

量产设备可能未挂载 debugfs，也可能禁止 shell 读取。节点不可见只说明观测条件不足，不能据此判断调度器没有使用 EEVDF。

### `sched_ext` 是可替换调度策略入口，不是 Android 17 的默认选人器

`android17-6.18-2026-06_r6` 已包含 `sched_ext` 与 BPF scheduler class。它允许具备系统权限的实现加载 BPF 调度策略，并可通过 `scx_bpf_cpuperf_set()` 向 CPU 性能控制传递目标。这个事实只证明内核具备接口，不能证明量产设备已经启用某个 BPF 调度器。

验证时至少同时检查内核配置、`/sys/kernel/sched_ext/state`（节点存在且可读时）、已加载 BPF program/link，以及 trace 中是否出现对应 `sched_ext` 事件。状态为 `disabled` 时，普通任务仍由本文描述的 fair/EEVDF 路径选择。即使 `sched_ext` 已启用，它也不直接写 CPUFreq driver；性能目标仍要经过 schedutil、policy、driver、固件与 thermal 上限，详见 5.4。

kernel 6.18 还包含 slice protection、`RUN_TO_PARITY`、`PREEMPT_SHORT` 和 deferred dequeue 等细节。它们会影响一次请求何时允许被抢占、短请求怎样参与竞争以及睡眠任务的 lag 怎样衰减。面向 Trace 分析时，记住下面三点更有用：

- EEVDF 仍以公平份额为目标，没有取消 nice 权重；
- eligible 解决“当前是否欠它 CPU”，deadline 解决“欠 CPU 的任务里先选谁”；
- 单个 Running 切片的长度不等于 `base_slice`，唤醒、阻塞、抢占、层级调度与 tick 都可能让切片提前结束或继续运行。

## 调度策略、调度类与优先级

### 用户可见策略的顺序

忽略内核内部的 stop class，以及配置相关的 sched_ext 后，常见用户态策略可以按优先关系理解为：

```text
SCHED_DEADLINE
    > SCHED_FIFO / SCHED_RR
    > SCHED_OTHER / SCHED_BATCH / SCHED_IDLE
```

这里有一个重要修正：用户态 `SCHED_IDLE` 由 `kernel/sched/fair.c` 实现，仍属于 fair 调度模块；它不能与每个 CPU 的 idle task 所属 `idle_sched_class` 混为一谈。`SCHED_IDLE` 比 nice 19 更弱，但线程仍是普通可运行任务。

各策略的参数含义如下：

| 策略 | 用户态参数 | 关键语义 |
| --- | --- | --- |
| `SCHED_DEADLINE` | `sched_runtime`、`sched_deadline`、`sched_period` | 采用 deadline class，受准入控制 |
| `SCHED_FIFO` | `sched_priority` 1..99 | 同优先级任务不会因 RR quantum 自动轮转 |
| `SCHED_RR` | `sched_priority` 1..99 | 同优先级任务按 RR quantum 轮转 |
| `SCHED_OTHER` | `sched_priority = 0`，使用 nice | Android 普通线程的主要策略 |
| `SCHED_BATCH` | `sched_priority = 0`，使用 nice | 偏向吞吐，交互性较弱 |
| `SCHED_IDLE` | `sched_priority = 0` | fair 模块中的极低权重策略 |

RT 线程先比较 `sched_priority`，数值越大，用户态实时优先级越高。两个 RT 线程只有在优先级相同时，FIFO 与 RR 的队列语义才决定轮转方式。

对 fair 线程，内核静态优先级通常可按 `120 + nice` 理解：nice -20 对应 100，nice 0 对应 120，nice 19 对应 139。Perfetto `sched_slice.priority` 中看到 fair 线程的这些数字时，数值越小表示权重越高。不要把这套内核编号方向与 RT 的用户态 `sched_priority` 方向混在一起。

### nice 调整的是份额，不是执行速度

Linux 的 nice 范围是 -20 到 19。权重表近似按每一级 1.25 倍变化，几个常用点如下：

| nice | weight |
| ---: | ---: |
| -20 | 88761 |
| -10 | 9548 |
| 0 | 1024 |
| 10 | 110 |
| 19 | 15 |

两个一直 runnable、处在同一 fair 层级并竞争同一 CPU 的线程，CPU 份额大致与权重成比例。实际设备还会受到 cgroup 层级、负载均衡、CPU capacity、UClamp、热限制和睡眠/唤醒模式影响。

nice 也不会让一段代码“每条指令执行得更快”。它改变的是 CPU 竞争结果。提高 nice 数值会降低权重；降低 nice 数值会提高权重，通常需要相应权限。若线程大部分时间在等待 Binder、锁、I/O 或 GPU，改 nice 很可能没有收益。

Android framework 的 `android.os.Process` 在 Android 17 中仍定义了一组常用线程优先级，例如：

| 常量 | nice 值 |
| --- | ---: |
| `THREAD_PRIORITY_DEFAULT` | 0 |
| `THREAD_PRIORITY_BACKGROUND` | 10 |
| `THREAD_PRIORITY_FOREGROUND` | -2 |
| `THREAD_PRIORITY_DISPLAY` | -4 |
| `THREAD_PRIORITY_URGENT_DISPLAY` | -8 |
| `THREAD_PRIORITY_AUDIO` | -16 |
| `THREAD_PRIORITY_URGENT_AUDIO` | -19 |

这些常量描述请求值，不代表任意 App 都能把线程设置到所有负 nice 值。内核权限、Android 服务端检查和 SELinux 策略仍会限制调用。

进程进入后台时，系统可能同时改变 cpuset、CPU cgroup、UClamp、timer slack、I/O priority 和 `oom_score_adj`。不能把这些变化概括成“系统一定把进程 nice 调高”，也不要把 CPU 调度优先级与低内存回收优先级视为同一套状态。

## Android 17 的 CPU 约束与 task profile

### affinity、cpuset 与 online CPU 共同决定可运行范围

一个线程能够运行的 CPU 范围，可以用下面的交集来理解：

```text
effective CPUs
  = online CPUs
  ∩ sched affinity mask
  ∩ cpuset / cgroup 允许范围
```

`sched_setaffinity()` 为线程设置 affinity mask。在 Linux 接口中传入 tid 即可控制单个线程。Android bionic 也提供 `sched_setaffinity()` / `sched_getaffinity()`；`pthread_setaffinity_np()` / `pthread_getaffinity_np()` 从 API 36 起公开。

affinity 只能进一步缩小允许范围，无法绕过 cpuset。随后若系统改变 cpuset、CPU 下线或热管理策略缩小范围，线程还可能被迁移。直接把 RenderThread 固定在某个“大核编号”会失去调度器的迁移空间，并可能造成排队、温升或能耗回归，应把它当作受控实验，而非默认优化。

CPU 编号也不能用“`cpu >= 4` 就是大核”判断。SoC 的簇布局各不相同，分析时应结合 Trace 中的 CPU frequency/capacity 信息，或读取设备的 sysfs 拓扑与最大频率。

### task profile 是 Android userspace 的命名控制层

Android 17 的 libprocessgroup 用 task profile 把 userspace 名称映射到 cgroup 与属性动作。`system/core/libprocessgroup/profiles/task_profiles.json` 中定义了：

- `HighEnergySaving` 加入 CPU `background` cgroup；
- `HighPerformance` 加入 CPU `foreground` cgroup；
- `HighPerformanceWI` 加入 `foreground_window`；
- `MaxPerformance` 加入 `top-app`；
- `ProcessCapacityLow`、`ProcessCapacityHigh`、`ProcessCapacityMax` 分别加入相应 cpuset；
- `UClampMin`、`UClampMax` 和 `UClampLatencySensitive` 映射到 CPU 控制器属性。

聚合 profile 会组合多个动作。例如 Android 17 源码中的 `CPUSET_SP_BACKGROUND` 同时引用 `HighEnergySaving`、`ProcessCapacityLow`、低 I/O 优先级和较高 timer slack；`CPUSET_SP_TOP_APP` 则组合 `MaxPerformance`、`ProcessCapacityMax`、最高 I/O 优先级和普通 timer slack。

因此，“前台/后台调度组”包含多种资源策略，不能只靠一个目录名推断全部效果。设备还可能提供 system_ext 或 vendor profile 覆盖。诊断具体设备时，应从运行时配置和进程成员关系反查，避免硬编码某个 `/dev/cpuset` 或 `/dev/cgroot` 路径。

下面这组只读命令用于确认某个线程的有效 CPU 范围和 cgroup 成员关系：

```shell
adb shell 'cat /proc/<pid>/task/<tid>/status | grep Cpus_allowed_list'
adb shell 'cat /proc/<pid>/task/<tid>/cgroup'
adb shell 'cat /proc/mounts | grep cgroup'
```

把 `<pid>` 和 `<tid>` 替换成目标值。第一条给出当前 affinity/cpuset 约束后的允许列表，第二、三条帮助定位设备的实际 controller 与挂载路径。

### UClamp 影响利用率提示，不直接改 fair 排名

UClamp 为任务或 cgroup 提供 utilization 的上下界：

- `uclamp.min` 给调度器一个最低利用率提示，可能影响 CPU 选核和调频；
- `uclamp.max` 限制可采用的最高利用率，有助于约束性能与功耗；
- Android 配置中的 `cpu.uclamp.latency_sensitive` 还依赖设备内核对该属性的支持。

UClamp 与 EEVDF 处理的层面不同。EEVDF 在 fair runqueue 中处理资格和 virtual deadline；UClamp 参与容量适配、能耗感知选核和频率决策。提高 `uclamp.min` 不保证线程立刻得到 CPU，也不会越过 RT 或 deadline 线程。

SchedTune 的 `schedtune.boost` 常见于旧 Android/vendor 内核。阅读历史 Trace 或旧设备配置时仍可能遇到它；对 Android 17 / kernel 6.18 锚点，应先检查 cgroup v2 与 `cpu.uclamp.*`，再根据设备源码判断是否保留了厂商扩展。

## 在 Perfetto 中读调度延迟

### 区分 Running、Runnable 与被抢占

Perfetto 的 `sched_slice` 每一行描述某个线程在某个 CPU 上的一段 Running 时间。`end_state` 表示该切片结束后线程进入的状态：

- `R`：切出后仍然 Runnable；
- `R+`：`Runnable (Preempted)`，Perfetto 明确标记为被抢占；
- `S`：可中断睡眠；
- `D`：不可中断睡眠；
- `I`：idle kernel thread 状态；
- `NULL` 且 `dur = -1`：Trace 结束时切片尚未闭合等未完成情况。

`thread_state` 把 Running、Runnable 和睡眠状态放在同一张时间表中。统计 runqueue wait 时应同时纳入 `R` 与 `R+`；只查询 `R` 会漏掉被抢占后继续等待的区间。

下面的查询用于找出目标进程中 Runnable 等待最多的线程：

```sql
SELECT
  t.name AS thread_name,
  ts.state,
  COUNT(*) AS wait_count,
  ROUND(SUM(ts.dur) / 1e6, 3) AS total_wait_ms,
  ROUND(MAX(ts.dur) / 1e6, 3) AS max_wait_ms
FROM thread_state AS ts
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE p.name = 'your.package.name'
  AND ts.state IN ('R', 'R+')
  AND ts.dur > 0
GROUP BY t.utid, t.name, ts.state
ORDER BY total_wait_ms DESC;
```

这里的 `dur` 是每段状态的持续时间，单位为纳秒。先看最大值判断是否存在少数尖峰，再看总量判断是否持续竞争；不要只用平均值掩盖长尾。

若要直接观察哪些 Running 切片以抢占结束，可以使用下面的查询：

```sql
SELECT
  s.ts,
  ROUND(s.dur / 1e6, 3) AS running_ms,
  s.cpu,
  t.name AS thread_name,
  s.priority
FROM sched_slice AS s
JOIN thread AS t USING (utid)
JOIN process AS p USING (upid)
WHERE p.name = 'your.package.name'
  AND s.end_state = 'R+'
  AND s.dur > 0
ORDER BY s.dur DESC
LIMIT 100;
```

`R+` 能证明这次切出被 Perfetto 编码为 preempted，却不能单独说明抢占者是谁。还要查看同一 CPU 上紧接着开始的 `sched_slice`、其调度类/priority，以及唤醒事件。

### CPU runtime 不等于 CPU utilization

下面的查询只统计各 CPU 在 Trace 中记录到的 Running 时长，适合快速看工作分布：

```sql
SELECT
  cpu,
  ROUND(SUM(dur) / 1e6, 3) AS running_ms
FROM sched_slice
WHERE dur > 0
GROUP BY cpu
ORDER BY cpu;
```

它没有直接给出利用率百分比。若要算利用率，需要先确定分析窗口，并把跨窗口的 slice 裁剪到窗口边界，再用“该 CPU 的非 idle Running 时长 / 窗口长度”计算。多个 CPU 的时长也不能先求和后除以单个窗口，否则结果会超过 100%。

### 唤醒到运行要结合 wakeup 事件

Runnable 延迟可以粗略写成：

```text
scheduling latency = first_running_ts - runnable_ts
```

但 `runnable_ts` 的来源需要区分：

- 从睡眠被唤醒：关注 `sched_waking` / `sched_wakeup`；
- Running 后被抢占：前一个 `sched_slice.end_state = 'R+'`；
- 主动 yield、迁移或其他调度路径：需要结合相邻状态和内核事件判断。

采集 CPU 调度延迟时，Perfetto 官方文档建议关注 `sched_switch`、`sched_waking`，必要时再加入 `sched_wakeup`。`sched_waking` 由发起唤醒的一侧记录，通常足以还原唤醒关系；若要继续分析 wakeup path 或跨 CPU IPI 延迟，再核对 `sched_wakeup`。

没有跨设备通用的“Runnable 超过帧周期 10% 就算异常”阈值。阈值应来自业务 deadline、线程角色和设备分布。例如主线程在一次 8.33 ms 帧预算内等待 2 ms 可能很关键，后台编译线程等待同样时长通常无须处理。

## Android 中的实时线程

Audio、显示合成、相机等系统路径可能使用 RT 策略降低调度抖动，但是否启用、使用哪个优先级以及由谁授权，取决于 AOSP 服务、设备配置和厂商实现。不能仅凭线程名断言它是 `SCHED_FIFO`。

普通 App 直接设置 RT 策略通常会受到 `CAP_SYS_NICE`、rlimit、服务端授权与 SELinux 的限制。Android 音频路径存在由系统服务协调优先级的机制；这也不等同于任意应用线程可以自由选择 RT priority。

RT 调度的风险来自无界运行：高优先级 FIFO 线程若长时间不阻塞，会压制较低 RT 与全部 fair 线程。审查 RT 问题时至少确认：

- 线程的 policy 和 priority；
- 每次连续 Running 的最长时间；
- 是否存在稳定的阻塞点；
- 是否造成关键 fair 线程长时间 Runnable；
- 设备是否配置 RT bandwidth 或厂商保护机制。

SurfaceFlinger、AudioFlinger 或 HAL 线程的策略应从目标设备 Trace 与源码确认。把某款设备上的 RT 配置写成 Android 平台固定行为，会让结论失去版本和设备边界。

## 一套可复现的诊断顺序

### 1. 先确认关键区间和 deadline

从输入、动画、Binder 请求或业务 slice 找到问题窗口，写清楚线程必须在什么时间前完成。没有 deadline，Runnable 时长只是一项观测值。

### 2. 分解线程时间

把目标线程的区间拆成 Running、`R/R+`、`S`、`D` 和 Binder/锁等待：

- Running 很长：优先检查代码量、热点与 CPU frequency；
- `R/R+` 很长：继续检查 CPU 竞争、policy、priority 与 CPU 约束；
- `S` 很长：找唤醒者、锁、futex、Binder 或定时器；
- `D` 很长：检查 blocked function 与 I/O/内核路径。

“墙上时间接近 CPU 时间”只能作为 CPU-bound 的初筛。多线程并行、抢占、迁核和采样误差都会破坏这个近似。

### 3. 解释竞争者

在长 Runnable 区间内查看同一 CPU 正在运行的线程：

- 若是 deadline/RT 线程，先检查其运行是否有界；
- 若是更高权重 fair 线程，核对 nice、cgroup 层级和业务必要性；
- 若 CPU 处于 idle，检查目标线程是否受 affinity/cpuset 限制，或 Trace 是否缺事件；
- 若目标线程频繁跨核，结合 cache miss、频率与迁移事件评估影响，不要只数迁移次数。

### 4. 检查 Android 控制面

读取目标 tid 的 `Cpus_allowed_list`、cgroup 成员关系、policy/nice，并对照运行时 task profile。还要区分 app 自己的设置、framework 生命周期调整和 vendor 配置。

### 5. 每次只验证一个改动

可选措施包括减少关键路径工作、拆分后台任务、修正错误优先级、调整 profile、修正过窄 cpuset，或在有平台权限的系统组件中修改 UClamp/RT 参数。affinity 只在证据表明迁移或选核造成问题时实验。

验证至少覆盖：

- 目标延迟的 P50/P90/P99；
- Runnable 长尾；
- CPU frequency、温度与功耗；
- 相邻关键线程是否退化；
- 冷机、热稳态和持续负载。

调度优化常把延迟从一个线程转移到另一个线程。只看目标线程变快，还不足以证明系统收益。

## 常见误判

### “优先级高，代码会执行得更快”

优先级改变竞争顺序或 CPU 份额。代码在相同核心、相同频率下的指令执行成本不会因此下降。

### “绑到大核一定更快”

过窄的 affinity 会减少可选 CPU，让线程在繁忙核心上排队，也会限制 EAS 根据温度与负载迁移。先用 Trace 证明选核或迁移是瓶颈，再做 A/B 对照。

### “大量 Runnable 说明调度器有 bug”

Runnable 只说明线程想运行但尚未运行。CPU 过载、RT 干扰、错误线程优先级、cpuset 限制和应用自身制造的并发都可能产生相同现象。

### “UClamp、nice、cpuset 可以互相替代”

三者分别约束利用率提示、公平权重和可用 CPU 集合。它们会相互影响，但修改对象和副作用不同。

### “oom_score_adj 低，线程就会先获得 CPU”

`oom_score_adj` 服务于低内存回收选择；CPU 调度由 policy、priority、nice、cgroup、cpuset、UClamp 等机制决定。两者可能由同一生命周期事件一起更新，含义仍然独立。

## 版本边界与源码索引

| 主题 | 当前锚点 | 历史内容的用途 |
| --- | --- | --- |
| Android 平台 | `android-17.0.0_r1` / API 37 | 说明 API 引入与旧设备差异 |
| Linux 内核 | `android17-6.18-2026-06_r6` | 旧 CFS 用于解释 vruntime 与演进 |
| fair 选人 | EEVDF：eligible + earliest virtual deadline | “最小 vruntime 最左节点”仅作旧 CFS 模型 |
| Android CPU 控制 | libprocessgroup task profiles、cpuset、cgroup v2 UClamp | SchedTune 用于识别旧/vendor 内核 |
| Perfetto | Android 17 对应源码与 CPU scheduling 文档 | 旧 Systrace 术语只作兼容阅读 |

相关结论可从以下源码入口复核：

- kernel `Documentation/scheduler/sched-design-CFS.rst`、`Documentation/scheduler/sched-eevdf.rst`；
- kernel `kernel/sched/fair.c`：`update_curr()`、`entity_eligible()`、`__pick_eevdf()`、`update_deadline()`、`__setparam_fair()`；
- Android `system/core/libprocessgroup/profiles/task_profiles.json`；
- Android bionic `libc/include/sched.h` 与 `libc/include/pthread.h`；
- Perfetto `docs/data-sources/cpu-scheduling.md`、`thread_state` 与 `sched_slice` 表定义。

## 参考资料

- [Linux CFS Scheduler 文档](https://docs.kernel.org/scheduler/sched-design-CFS.html)
- [Linux EEVDF Scheduler 文档](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [kernel 6.18 fair.c（Android 17 kernel tag）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [Android 17 task_profiles.json](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/libprocessgroup/profiles/task_profiles.json)
- [Android 17 bionic pthread.h](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/pthread.h)
- [Perfetto CPU Scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [Android UClamp](https://source.android.com/docs/core/perf/uclamp)
