---
title: "Android 17 内核 EEVDF 调度器：从 CFS 到 Earliest Eligible Virtual Deadline First"
chapter: "5.31"
status: ready-for-review
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [EEVDF, CFS, Linux内核, CPU调度, sched, kernel6.18, 虚拟截止时间, vlag, sched_ext]
related_chapters: ["5.1", "5.2", "5.4", "5.9", "5.28", "17.21"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-15"
gap_source: "AOSP结构"
drafted_date: "2026-07-15"
last_verified: "2026-07-15"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18; Linux 6.6/6.12/6.18 kernel/sched/fair.c"
confidence: high
sources:
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-eevdf.html"
  - type: official
    path: "https://docs.kernel.org/scheduler/sched-design-CFS.html"
  - type: official
    path: "https://source.android.com/docs/core/perf/uclamp"
  - type: aosp
    path: "android-17.0.0_r1 kernel/sched/fair.c"
  - type: aosp
    path: "android-17.0.0_r1 kernel/sched/cpufreq_schedutil.c"
  - type: aosp
    path: "android-17.0.0_r1 system/libprocessgroup/task_profiles.json"
---

# 5.31 Android 17 内核 EEVDF 调度器：从 CFS 到 Earliest Eligible Virtual Deadline First

> **一句话总结**：以 Android 17 / API 37 / `android-17.0.0_r1` 和 Android Common Kernel `android17-6.18-2026-06_r6` 为基准，普通公平调度任务由 EEVDF 在“有资格的实体”中选择虚拟截止时间最早者；EAS、PELT、uclamp 与 schedutil 分别负责或参与选核、负载跟踪和调频，不能把这些机制混成同一次调度决策。

---

## 先划清版本与职责边界

Android 平台版本和 Linux 内核版本是两个锚点。本文讨论的 framework 行为以 `android-17.0.0_r1` 为准，调度器实现以 `android17-6.18-2026-06_r6` 为准。量产设备还会叠加 SoC 厂商配置、vendor hook 和设备内核补丁，因此分析具体设备时仍要核对 `uname -r`、内核配置与调度器运行状态。

| 问题 | Android 17 / 6.18 中的主要机制 |
|---|---|
| 唤醒任务应放在哪个 CPU | `select_task_rq_fair()`，满足条件时进入 EAS 的 `find_energy_efficient_cpu()` |
| 当前 CPU 下一次运行哪个公平调度实体 | EEVDF 的 `pick_eevdf()` |
| 任务近期占用了多少算力 | PELT 的 `util_avg`、`load_avg` 等信号 |
| CPU 应请求多少性能 | schedutil 结合有效利用率、uclamp 和架构信号计算 |
| 实时任务能否抢占普通任务 | 由调度类优先级处理，不归 EEVDF 决定 |

Linux 文档把 6.6 描述为“开始从早期 CFS 选择方式迁移到 EEVDF”。在 6.18 源码中，`fair_sched_class` 仍然存在，`SCHED_NORMAL`、`SCHED_BATCH` 和 `SCHED_IDLE` 也仍由公平调度代码管理。更准确的说法是：**公平调度类保留了 CFS 的大量基础设施，选人算法已经采用 EEVDF**。它不会取代 `SCHED_FIFO`、`SCHED_RR`、`SCHED_DEADLINE` 等更高调度类。

## EEVDF 如何判断“轮到谁”

### 1. Lag 表示服务欠账

内核注释给出的关系是：

$$
lag_i = S - s_i = w_i(V-v_i)
$$

- $S$ / $s_i$ 分别表示理想服务量和实体已经获得的服务量。
- $w_i$ 是由 nice 等因素形成的调度权重。
- $V$ 是运行队列的虚拟时间，$v_i$ 是实体的 `vruntime`。
- `lag >= 0` 表示实体尚未拿足公平份额，具备 eligibility；`lag < 0` 表示它已经多拿了服务。

这里有一个容易误读的实现细节：运行队列中的实体并不依赖持续写回的 `se->vlag` 来判断资格。`entity_eligible()` 调用 `vruntime_eligible()`，直接用 `cfs_rq->sum_w_vruntime`、`sum_weight`、当前实体和待判断实体的 `vruntime` 完成等价比较，还特意避开了先做除法带来的精度损失。

`se->vlag` 主要负责离队与重新入队之间的 lag 保存：

1. `update_curr()` 用 `rq_clock_task()` 计算已经运行的 `delta_exec`，再通过 `calc_delta_fair()` 推进 `curr->vruntime`。
2. 实体离开运行队列时，`dequeue_entity()` 调用 `update_entity_lag()`，把当前虚拟 lag 保存到 `se->vlag`。
3. 实体重新入队时，`place_entity()` 以运行队列平均虚拟时间为基准，补偿加入实体对加权平均值的扰动，并恢复应保留的 lag。

所以，“`update_curr()` 每个 tick 直接更新 vlag”这个说法不符合 6.18 实现。它更新执行时间和 `vruntime`；eligibility 随运行队列的虚拟时间关系变化，离队前才把 lag 快照保存到字段中。

### 2. Deadline 表示当前服务请求的虚拟期限

每个公平调度实体拥有请求长度 `slice`。6.18 的 `update_deadline()` 在一个请求耗尽后按下式生成新期限：

$$
deadline_i = vruntime_i + \operatorname{calc\_delta\_fair}(slice_i, entity_i)
$$

同一权重下，较短的请求会得到较近的虚拟 deadline。权重也会参与 `calc_delta_fair()`，因此 nice 值仍会改变虚拟时间推进速度和 deadline 距离。

普通实体默认使用 `sysctl_sched_base_slice`。这个内核锚点的未缩放基值是 700,000 ns，默认采用对数缩放，CPU 数量最多按 8 个计算：

$$
base\_slice = 0.7ms \times (1+\log_2(\min(nr\_online\_cpus, 8)))
$$

8 核及以上设备的源码默认值由此得到 2.8 ms。它是默认请求长度，不能理解为“任务一旦运行便有 2.8 ms 绝对不可抢占”：高调度类仍可抢占公平任务，EEVDF 自身还有 eligibility、deadline、slice protection 和唤醒抢占判断，vendor hook 也可能改变决定。

6.18 还允许公平调度任务通过 `sched_setattr()` 的 `sched_runtime` 请求自定义 slice。`__setparam_fair()` 会把非零值限制在 0.1 ms 到 100 ms；传 0 则恢复默认 `base_slice`。这项内核能力不能推导出 Android UI 线程已经使用它，判断某个线程是否设置了 custom slice 应查看设备运行状态或对应调用方。

### 3. 红黑树按 deadline 排序，用 min_vruntime 剪枝

`cfs_rq->tasks_timeline` 是增强红黑树：

- `entity_before()` 比较 `se->deadline`，因此树的排序键是虚拟 deadline。
- 每棵子树记录最小 `vruntime`，同时维护最小和最大 slice。
- `__pick_eevdf()` 先用子树的 `min_vruntime` 判断其中是否可能存在 eligible 实体；不能满足资格的子树可以跳过。
- 在 eligible 候选中，调度器选择 deadline 最早的实体，并把仍在运行的当前实体一并比较。

这使选人保持在 $O(\log n)$ 量级，同时满足两道条件：先有资格，再比较期限。只看红黑树最左节点、只看最小 `vruntime` 或只看最早 deadline，都会漏掉一部分算法。

### 4. Slice protection 控制过度抢占

6.18 默认启用 `RUN_TO_PARITY`。当前实体在到达 0-lag 点或耗尽受保护的请求前，`pick_eevdf()` 可以继续返回它，避免每次唤醒都引发切换。`PREEMPT_SHORT` 也默认启用：新唤醒实体具有更短 slice 且 eligible 时，可以缩短当前实体的保护区间。

因此，EEVDF 的唤醒抢占需要同时看当前实体的保护状态、唤醒实体的资格、slice 与 deadline。用“deadline 更早便立即抢占”概括 6.18 行为会过于简单。

### 5. 睡眠任务不会靠短暂阻塞清空负 lag

`DELAY_DEQUEUE` 和 `DELAY_ZERO` 在本内核锚点中默认开启。一个准备睡眠且尚不 eligible 的实体会先标记为 `sched_delayed`，暂留在竞争集合中，让它的负 lag 随虚拟时间变化逐步衰减。它被选中准备完成延迟出队，或在此期间重新唤醒时，再进入相应路径；完成延迟出队时，正 lag 还会被裁到 0。

这个设计抑制了“运行超额后短睡一下，醒来便重置欠账”的利用方式。长睡眠任务也不会因为理想执行时间持续无界累积而自动得到巨大正 lag；lag 的保存、边界限制和延迟出队共同约束了唤醒位置。

## 从旧 CFS 选人方式迁移时，哪些认识要更新

| 观察点 | 早期 CFS 常见描述 | 6.18 EEVDF 实现 |
|---|---|---|
| 公平依据 | 选择最小 `vruntime` | `vruntime` 仍是服务记账基础，先以 lag 判断资格 |
| 候选排序 | 时间线按 `vruntime` 排序 | 时间线按 deadline 排序，子树增强信息用于 eligibility 剪枝 |
| 请求长度 | 调度周期和最小粒度共同影响 | 默认请求由 `base_slice_ns` 给出，也支持 custom slice |
| 唤醒抢占 | 依赖 vruntime 差值及 wakeup granularity | 结合 EEVDF 选人结果、slice protection 与短 slice 规则 |
| 睡眠补偿 | 调整新入队实体的 `vruntime` | 保存 lag，并对负 lag 睡眠实体使用延迟出队 |

不要把 Linux 6.6 到 6.18 之间每个小版本的变化编成一张“版本功能表”。官方 EEVDF 文档只确认 Linux 从 6.6 开始迁移，并描述 6.18 所采用的 lag、deadline、延迟出队和自定义 slice 等方向；具体补丁应按 commit 或目标标签验证。本文只对 `android17-6.18-2026-06_r6` 的最终代码作结论。

旧版调优经验也应重新核查。这个标签的公平选人直接使用 `base_slice_ns`，但源码中仍可能保留供其他调度功能使用或导出的历史变量。看到变量名仍在源码里，不等于它仍以旧 CFS 语义控制 EEVDF。可靠做法是从读写点追到 `update_deadline()`、`place_entity()`、`check_preempt_wakeup_fair()` 和 `pick_eevdf()`。

## EEVDF、EAS、PELT、uclamp 和 schedutil 的关系

任务从唤醒到运行，大致经过下面几个阶段：

1. `select_task_rq_fair()` 先处理 CPU 亲和性、唤醒关系和 vendor hook。
2. EAS 可用且 root domain 未进入 overutilized 状态时，`find_energy_efficient_cpu()` 评估性能域候选、剩余容量和 Energy Model。
3. 任务进入目标 CPU 的 `cfs_rq`，EEVDF 决定该队列下一次运行的公平实体。
4. PELT 持续维护利用率与负载信号。
5. schedutil 的 `sugov_get_util()` 取得有效 CPU 利用率，并结合性能上下限形成频率请求。

overutilized 后，唤醒选核不会进入 EAS 的能耗比较，会继续走亲和性和调度域负载均衡路径。目标 CPU 内的公平选人仍由 EEVDF 完成，把这种回退称作“退回旧 CFS 选人算法”并不准确。

### PELT 仍然重要，但不直接充当 EEVDF 的候选键

`util_avg` 会参与 EAS 容量判断、能耗估计、负载均衡与 schedutil 调频。EEVDF 的 `entity_eligible()` 和 `entity_before()` 不读取 `util_avg`，它们使用运行队列虚拟时间、实体 `vruntime`、权重、slice 和 deadline。

`vruntime` 也不是 PELT 的延伸。两者都是公平调度代码维护的状态，但时间尺度和用途不同：

- `vruntime` 按执行时间和权重推进，用于公平服务与 EEVDF 期限。
- PELT 对 runnable/running 信号做时间衰减，估计近期负载与利用率。

### uclamp 限制的是利用率信号，不是 MHz

`uclamp.min` 和 `uclamp.max` 的数值处在容量归一化尺度上，通常是 0 到 1024。它们会影响：

- EAS 判断任务是否适合某个容量等级的 CPU；
- 运行队列的有效利用率上下界；
- schedutil 根据利用率请求性能时使用的边界。

uclamp 值不是直接的最低或最高 CPU 频率。最终频点还取决于 CPU 容量、DVFS 映射、策略域、thermal 限制和驱动。

更重要的是，CPU 高频不会让同一段墙上执行时间记成更小的 `delta_exec`。`update_se()` 计算的是 `rq_clock_task()` 的时间差，`update_curr()` 再据此推进 `vruntime`。频率提高后，线程可能更早完成一批指令并主动阻塞，从而缩短本次 runnable 区间；只要它持续占用 CPU，相同的运行时长会得到相同量级的调度时间记账。由此不能推出“高 uclamp.min 让 vlag 下降更慢”或“低 uclamp.max 让任务更快失去资格”。

Android 17 的 `system/core/libprocessgroup/profiles/task_profiles.json` 基线定义了 `UClampMin`、`UClampMax` 和 `UClampLatencySensitive` 对应的 cgroup 属性，也定义了 foreground、top-app、background 等调度组。基线文件没有原文所写的 `SetClamps` / `BoostPct` / `ClampPct` 动作。具体 clamp 数值来自 cgroup 配置与设备覆盖，分析时应读取设备上的有效值。

### ADPF 没有通用的“帧 deadline → EEVDF deadline”映射

ADPF Hint Session 描述目标工作时长和每轮实际工作时长，后端可以据此调整性能资源。厂商实现可能借助 uclamp、调频或其他内核接口，但 `PerformanceHintManager` 的 deadline 也不会自动写入 `sched_entity.deadline`。

EEVDF 的 deadline 是公平调度器内部的**虚拟服务期限**；ADPF 的 target duration 是应用工作周期的**墙上时间目标**。两者名称相近，单位和决策语义不同。Android 17 framework 是否为某类线程设置 custom slice，必须用调用点或运行时 `sched_debug` 信息验证，不能从 ADPF API 的存在推断。

## UI 线程会自动获得更早 deadline 吗

EEVDF 不识别 `main`、`RenderThread`、Vsync 或应用包名。UI 线程的响应优势可能来自：

- 线程睡眠等待事件后唤醒时的 lag 状态；
- nice 权重、调度策略或 custom slice；
- foreground/top-app 调度组、cpuset、CPU affinity 和 uclamp；
- EAS 选核结果；
- Android vendor hook 与设备调度补丁；
- 更高调度类的优先级。

只要两个 `SCHED_NORMAL` 线程具有相同权重、相同 slice 和相近 lag，EEVDF 没有理由因为其中一个名为 `RenderThread` 就给它更早 deadline。系统策略若只提高 uclamp，主要改变选核与性能请求，也不会直接改写 EEVDF deadline。

对后台任务也要区分两层限制。JobScheduler 决定工作何时具备运行条件，调度组、cpuset、CPU weight 和 quota 决定它能在哪些 CPU 上竞争以及能拿多少组级份额；EEVDF 只处理已经进入公平运行队列的调度实体。启用 `CONFIG_FAIR_GROUP_SCHED` 时，任务组本身也是分层调度实体，单个线程的资格不能越过 cgroup 配额或层级权重。

## `sched_ext`：GKI 已编译，运行时是否启用另算

`android17-6.18-2026-06_r6` 的 arm64 GKI defconfig 明确设置：

- `CONFIG_SCHED_CLASS_EXT=y`
- `CONFIG_BPF_SYSCALL=y`
- `CONFIG_BPF_JIT=y`
- `CONFIG_BPF_JIT_ALWAYS_ON=y`

正确配置符号是 `CONFIG_SCHED_CLASS_EXT`。这证明 GKI 编译了 sched_ext 调度类；在没有加载 BPF 调度器时，sched_ext 仍处于 disabled 状态，普通公平任务继续由 EEVDF 处理。

sched_ext 的覆盖范围由 BPF 调度器的 `ops->flags` 决定：

- 默认可以接管 `SCHED_NORMAL`、`SCHED_BATCH`、`SCHED_IDLE` 和 `SCHED_EXT` 任务；
- 设置 `SCX_OPS_SWITCH_PARTIAL` 时，只接管显式使用 `SCHED_EXT` 策略的任务；
- BPF 调度器退出或发生错误时，内核停止该 sched_ext 实例，并把任务交回内核调度器。

下面的命令用于区分“编译进内核”和“已经加载调度器”；它们通常需要 root，节点是否可读还受设备构建类型和 SELinux 约束。

```bash
zcat /proc/config.gz | grep CONFIG_SCHED_CLASS_EXT
cat /sys/kernel/sched_ext/state
cat /sys/kernel/sched_ext/root/ops
cat /sys/kernel/sched_ext/enable_seq
```

第一行检查构建配置；`state` 显示 sched_ext 当前状态，`root/ops` 显示已注册调度器名称，`enable_seq` 可辅助判断是否曾启用。只看到配置为 `y`，不能证明量产设备正在用 BPF 调度器。

sched_ext 提供完整的调度接口，BPF 策略需要自行处理选 CPU、排队和时间片等问题。它不会自动继承 Android EAS 策略的所有行为。任何游戏、AI 或省电收益都要靠具体 BPF 实现、设备拓扑与实验数据证明，不能由框架存在直接推出。

## 如何在设备上验证 EEVDF

### 1. 查看 slice、eligibility 和 deadline

下面的命令用于检查当前构建是否开放调度调试信息。`/proc/sched_debug` 依赖相应内核配置，user 构建可能不可用。

```bash
adb shell su 0 cat /sys/kernel/debug/sched/base_slice_ns
adb shell su 0 cat /proc/sched_debug
```

在这个 6.18 源码中，`sched_debug` 的 runnable task 表包含 `vruntime`、`eligible`、`deadline`、是否为 custom slice、`slice`、累计执行时间和优先级。它没有直接打印每个在队实体的原始 `vlag`，但已经能验证“是否 eligible”“deadline 谁更早”“slice 是否自定义”三个关键问题。

### 2. 用 Perfetto 测量 Runnable 等待

采集包含 `sched_switch`、`sched_waking` / `sched_wakeup` 的 Perfetto trace 后，可用下面的 SQL 比较目标线程从 Runnable 到 Running 的等待时长。先用准确进程或线程名缩小范围，避免把系统中同名线程混在一起。

```sql
SELECT
  t.name AS thread_name,
  COUNT(*) AS runnable_slices,
  ROUND(AVG(ts.dur) / 1e6, 3) AS avg_runnable_ms,
  ROUND(MAX(ts.dur) / 1e6, 3) AS max_runnable_ms
FROM thread_state AS ts
JOIN thread AS t USING (utid)
WHERE ts.state IN ('R', 'R+')
  AND ts.dur > 0
  AND t.name IN ('main', 'RenderThread')
GROUP BY t.name
ORDER BY avg_runnable_ms DESC;
```

结果反映端到端 runnable 等待，其中同时包含 EEVDF 选人、CPU 亲和性、选核、迁移、cgroup 竞争、更高调度类占用和 CPU 过载等影响。它可以确认“线程在等 CPU”，单凭这张表还不能把原因归到 vlag 或 deadline。

### 3. 沿源码调用点定位

| 要验证的行为 | `android17-6.18-2026-06_r6` 入口 |
|---|---|
| 增加执行时间与 `vruntime` | `update_se()`、`update_curr()` |
| 计算运行队列虚拟时间 | `avg_vruntime()` |
| 判断 eligibility | `vruntime_eligible()`、`entity_eligible()` |
| 选择下一实体 | `__pick_eevdf()`、`pick_eevdf()` |
| 生成新 deadline | `update_deadline()` |
| 保存 lag | `update_entity_lag()`、`dequeue_entity()` |
| 恢复 lag 与放置实体 | `place_entity()` |
| 处理睡眠负 lag | `DELAY_DEQUEUE`、`finish_delayed_dequeue_entity()` |
| 唤醒抢占 | `check_preempt_wakeup_fair()` |
| EAS 选核 | `select_task_rq_fair()`、`find_energy_efficient_cpu()` |
| schedutil 取有效利用率 | `sugov_get_util()`、`effective_cpu_util()` |

## 排查卡顿时的判断顺序

看到 UI 线程 Runnable 时间偏长，可以按下面的顺序缩小范围：

1. 确认目标线程、进程和卡顿区间，避免只看全程平均值。
2. 检查线程的调度策略、nice、CPU affinity、cpuset 和 cgroup。
3. 看它被放到哪个 CPU，该 CPU 是否被实时任务、IRQ 或大量公平任务占用。
4. 在可调试内核上读取 `eligible`、`deadline` 和 `slice`，确认是否存在资格等待或 custom slice。
5. 对照 CPU frequency、idle 和 thermal 轨道。频率不足会延长完成工作所需的墙上时间，但不能据此断言 EEVDF 记账错误。
6. 检查 vendor hook、设备调度补丁和 sched_ext 状态。GKI 源码结论不能覆盖设备私有改动。

最终记住五条边界：

- EEVDF 是公平调度类中的选人算法，CFS 基础设施和层级公平机制仍在。
- eligibility 来自运行队列虚拟时间关系，`se->vlag` 主要保存离队状态。
- 较短 slice 才会直接形成较近 deadline，线程名称和 ADPF target duration 不会自动做到这一点。
- uclamp 影响容量匹配与性能请求，不会改变同一段 CPU 执行时间的记账速率。
- `CONFIG_SCHED_CLASS_EXT=y` 只表示支持 sched_ext；是否正在运行要读取 `/sys/kernel/sched_ext/`。

## 参考与验证锚点

- Linux 官方文档：`Documentation/scheduler/sched-eevdf.rst`
- Linux 官方文档：`Documentation/scheduler/sched-design-CFS.rst`
- Android Common Kernel：`android17-6.18-2026-06_r6`
  - `kernel/sched/fair.c`
  - `kernel/sched/features.h`
  - `kernel/sched/debug.c`
  - `kernel/sched/cpufreq_schedutil.c`
  - `kernel/sched/ext.c`
  - `arch/arm64/configs/gki_defconfig`
- Android 平台：`android-17.0.0_r1`
  - `system/core/libprocessgroup/profiles/task_profiles.json`

相关基础知识见 §5.1「Linux 进程调度基础」、§5.2「EAS 能量感知调度」、§5.9「ADPF 自适应性能提示」、§5.28「PELT Boost 回退与 AMU/PMU 微架构感知调频」以及 §17.21「SoC 厂商 Power HAL 与 schedutil」。
