---
status: ready-for-review
title: 系统内存压力与 lmkd
section: 4.4
chapter: 4.4
drafted_date: 2026-03-31
reviewed_date: 2026-05-10
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: "pending-verification"
_audit: 2026-05-21
last_task6_audit_log: logs/review/2026-05-21-21-audit.md
last_task6_audit: 2026-06-14
last_task6_at: "2026-05-21T21:06:00+08:00"
task9_state: "reviewed"
polish_count: 1
polish_date: 2026-04-05
polish_by: task2b-polish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: 2026-05-09
last_verified_against: "AOSP android-4.0.1_r1 init.rc/ProcessList.java, android-8.1"
confidence: medium-high
sources:
- type: aosp
  path: AOSP ProcessList.java, lmkd.cpp, reaper.cpp, OomAdjuster.java, CachedAppOptimizer.java; source.android.com/docs/core/perf/lmkd; developer.android.com/about/versions/17/behavior-changes-all
tags: "LMK, lmkd, OOM, oom_score_adj, PSI, memory-pressure, process-priority, CachedAppOptimizer, Android-17"
related_chapters: "4.1, 4.3, 1.3, 10.4"
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
task9_reviewed_date: 2026-06-08
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-08T22:20:00+08:00"
review_notes: "2026-04-27 task2b: 修复 Task9 P0/P1 与 external P1；校正旧 LMK 初始化、userspace"
last_task9_autofix_at: 2026-06-08
last_task2b_at: "2026-06-08T21:06:43+08:00"
task2b_fixed_by: openclaw-task2b
repaired_date: 2026-04-27
repaired_by: openclaw-task2b
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
pipeline_stage: ready-for-review
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch04-memory/15-psi-lowmemdetector-lmkd-architecture.md"
  - "src/part1-fundamentals/ch04-memory/4.36-android17-lmkd-procs-prio-batch.md"
  - "src/part1-fundamentals/ch04-memory/4.50-lmkd-v2-psi-tiered-pressure-governance.md"
---

# 4.4 系统内存压力与 lmkd

## 先把 LMK 放回 Android 内存体系

Android 会尽量保留离开前台的应用进程。用户再次打开应用时，系统可以复用进程、Java 堆、已加载的类和部分页面缓存，省去一次从 Zygote fork 开始的进程启动。代价是物理内存、压缩交换空间和文件页缓存会逐渐承压。

Linux 内核自带 OOM Killer，但它通常在分配已经难以继续时介入。Android 还需要一层更早、也更了解应用重要性的策略：系统根据 Activity、Service、ContentProvider、绑定关系以及近期交互计算进程优先级；`lmkd` 结合这个优先级和内核压力数据，先处理对用户影响较小的进程。

Android 17 的 LMK 主路径包含三类输入、两段决策和一条回收链，各模块职责如下：

```mermaid
flowchart LR
    lifecycle["Activity、Service、Provider 与绑定关系"] --> adjuster["OomAdjuster / Process State Controller"]
    adjuster --> processlist["ProcessList"]
    processlist -->|"控制 socket：PID、UID、adj"| lmkd["lmkd"]
    lmkd -->|"写入"| procfs["/proc/PID/oom_score_adj"]

    psi["PSI：some / full stall"] --> lmkd
    memory["meminfo、vmstat、zoneinfo、swap、refault"] --> lmkd
    memevents["BPF memevents：direct reclaim、kswapd"] --> lmkd

    lmkd --> candidate["按 adj 与内存占用选择一个候选"]
    candidate --> reaper["Reaper"]
    reaper --> terminate["cgroup kill 接口或 pidfd SIGKILL"]
    terminate --> release["process_mrelease 加速回收"]
```

图中有两个容易混淆的边界：

- `OomAdjuster` 负责回答“这个进程对用户有多重要”，`lmkd` 负责回答“当前压力是否需要杀进程，以及在什么优先级范围内选谁”。
- `lmkd` 会写 `/proc/<pid>/oom_score_adj`，同时在自己的进程表中登记候选。AMS 与 `lmkd` 之间存在专用控制 socket，不能把这条通信简化成“双方只通过 `/proc` 共享信息”。

平台源码以 `android-17.0.0_r1` 为锚点，内核语义以 `android17-6.18-2026-06_r6` 为锚点。

## 从内核 LMK 到 userspace lmkd

### 早期方案：in-kernel LowMemoryKiller

早期 Android 使用 `drivers/staging/android/lowmemorykiller.c`。Framework 计算若干组 `minfree` 与 `adj`，再写入内核模块参数。内核回收路径发现可用页和文件缓存低于某一档阈值后，遍历进程并选择优先级较低的目标。

这套方案的局限来自它所在的位置：

- shrinker 回调不适合承载遍历进程、评估目标和杀进程这类重操作；
- 固定的空闲页阈值很难识别 page cache thrashing，也容易把正常文件缓存当成紧迫内存；
- 策略位于内核，设备调校和版本更新成本较高；
- Android 进程语义先被压缩成一个数字，内核侧缺少更多决策信号。

上游 Linux 从 4.12 移除了该驱动。Android 随后把监控和选择逻辑迁到用户空间。

### 现代方案：userspace lmkd

Android 8.1 的源码已经包含 userspace `lmkd` 及 AMS 控制协议。Android 9 起，在未检测到内核 LMK 驱动时启用 userspace 路径；Android 10 引入 PSI 监控模式；Android 11 的新策略进一步把 zone watermark、swap 和 workingset refault thrashing 纳入判断。Android 17 延续这条架构。

迁到用户空间以后，`lmkd` 可以：

- 读取 `/proc/meminfo`、`/proc/vmstat`、`/proc/zoneinfo` 和 PSI；
- 接收 AMS 计算出的最新 `oom_score_adj`；
- 根据 swap、文件页反复换入和回收状态过滤压力信号；
- 通过属性、资源覆盖和 vendor hook 做设备级调校；
- 输出 logcat、statsd、控制 socket 事件和 Perfetto 事件。

“用户空间”不表示它脱离内核。PSI、pidfd、cgroup、`process_mrelease()` 以及内存统计仍由内核提供；策略代码位于 `lmkd`。

## `oom_score_adj`：候选优先级，不是生命周期枚举

### 取值方向

Linux 的 `oom_score_adj` 范围是 `-1000` 到 `1000`：

- 数值越大，进程越容易成为回收候选；
- 数值越小，保护程度越高；
- `-1000` 对 Linux OOM 选择有特殊保护含义；
- Android Framework 的 `UNKNOWN_ADJ=1001` 是内部未决值，超出可写入内核的范围，不会作为有效 adj 发送。

Android 17 把核心常量集中在 `services/core/java/com/android/server/am/psc/Constants.java`。下表列出源码中的主要边界。

| 常量或区间 | Android 17 数值 | 常见语义 |
|---|---:|---|
| `NATIVE_ADJ` | -1000 | AMS 未管理、未由 AMS 分配 adj 的 native 进程所用的特殊分类 |
| `SYSTEM_ADJ` | -900 | `system_server` |
| `PERSISTENT_PROC_ADJ` | -800 | persistent 系统进程 |
| `PERSISTENT_SERVICE_ADJ` | -700 | 被 system 或 persistent 进程以重要方式绑定的服务 |
| `FOREGROUND_APP_ADJ` | 0 | top/前台关键进程 |
| `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ` | 50 | 近期从 TOP 转到 FGS 的宽限层 |
| `VISIBLE_APP_ADJ` | 100 | 可见进程；特性开关启用时可分层到 199 |
| `PERCEPTIBLE_APP_ADJ` | 200 | 用户可感知组件，例如符合条件的音频播放 |
| `PERCEPTIBLE_MEDIUM_APP_ADJ` | 225 | system 绑定且要求较高保护的服务 |
| `PERCEPTIBLE_LOW_APP_ADJ` | 250 | 低一级的可感知绑定 |
| `BACKUP_APP_ADJ` | 300 | 正在备份 |
| `HEAVY_WEIGHT_APP_ADJ` | 400 | heavy-weight 应用 |
| `SERVICE_ADJ` | 500 | 一般 service 进程 |
| `HOME_APP_ADJ` | 600 | Launcher/Home |
| `PREVIOUS_APP_ADJ` | 700 | 前一个应用；特性开关启用时可分层到 799 |
| `SERVICE_B_ADJ` | 800 | B-list service |
| `CACHED_APP_MIN_ADJ`～`CACHED_APP_MAX_ADJ` | 900～999 | cached 进程 |
| `CACHED_APP_LMK_FIRST_ADJ` | 950 | LMK minfree 档优先允许处理的 cached 边界 |

这张表不能直接当作“每种组件永远对应一个固定值”。`OomAdjuster` 或 Modern Oom Adjuster 会按整个依赖图计算 adj：

- 前台客户端绑定后台服务时，服务端可以得到更高保护；
- 前台进程正在使用某个 ContentProvider 时，Provider 所在进程也可能被抬高；
- 前台服务的类型、近期 TOP 宽限、可见 Activity 层次和系统绑定都会影响结果；
- cached 和 previous 在特性开关启用后可使用更细的阶梯值。

因此，排查时要读取目标时刻的 adj，不能只凭“它有一个 Service”推断。

`NATIVE_ADJ` 也不代表所有 native daemon 都天然不会被杀。该常量在 Framework 中描述 AMS 未管理的 native 进程；某个 daemon 的实际保护还取决于 init service 配置、它的 `/proc/<pid>/oom_score_adj` 以及它是否登记到 `lmkd`。

## AMS 如何把优先级交给 lmkd

### 控制协议

Android 17 的命令号在 Framework `ProcessList.java` 与 `system/memory/lmkd/include/lmkd.h` 中保持一致：

| 命令 | 值 | 作用 |
|---|---:|---|
| `LMK_TARGET` | 0 | 下发最多 6 组 `minfree/oom_adj` |
| `LMK_PROCPRIO` | 1 | 登记一个进程并设置 adj |
| `LMK_PROCREMOVE` | 2 | 移除一个进程记录 |
| `LMK_PROCPURGE` | 3 | 清理该客户端登记的进程 |
| `LMK_GETKILLCNT` | 4 | 查询 kill 次数 |
| `LMK_SUBSCRIBE` | 5 | 订阅异步 kill 或 stats 事件 |
| `LMK_PROCKILL` | 6 | `lmkd` 发给订阅者的 kill 通知 |
| `LMK_UPDATE_PROPS` | 7 | 重新读取属性并重建监控 |
| `LMK_KILL_OCCURRED` | 8 | Framework 中的 stats 事件名；native 头文件名为 `LMK_STAT_KILL_OCCURRED` |
| `LMK_START_MONITORING` | 9 | 启动延迟初始化的 PSI 监控 |
| `LMK_BOOT_COMPLETED` | 10 | 通知 `lmkd` 完成启动后初始化 |
| `LMK_PROCS_PRIO` | 11 | 批量登记 adj |

单进程 `LMK_PROCPRIO` 包含 6 个 32 位整数：命令、PID、UID、adj、process type、`for_lmkd_only`。默认 process type 是 `PROC_TYPE_APP`。当 `for_lmkd_only=false` 时，`lmkd::apply_proc_prio()` 先把 adj 写到 `/proc/<pid>/oom_score_adj`，再把进程放进对应 adj 链表。

批量命令每个包最多放 3 个进程，每个记录有 PID、UID、adj、process type 和 `for_lmkd_only` 五个字段。Android 17 的 `ProcessList.batchSetOomAdj()` 固定把末尾一个字段写成 0，因此批量路径不支持只更新 `lmkd` 内部值。

每包三条来自控制包最多 16 个 `int`：一个命令字加三组、每组五个字段。批量路径减少 socket write 和 daemon 收包次数，但它不是一次原子事务。`lmkd` 会逐条校验 PID、UID、adj 和字段范围；某条记录失败不代表其他记录自动回滚。`for_lmkd_only` 只决定是否同时写 `/proc/<pid>/oom_score_adj`，不是“只在压力时生效”的延迟更新开关。

连接建立后，`ProcessList.onLmkdConnect()` 会：

1. 发送 `LMK_PROCPURGE`，清掉旧连接留下的登记；
2. 在 OOM 档位已计算时重发 `LMK_TARGET`；
3. 订阅 kill 与 stats 两类异步事件。

这条控制链也解释了一个常见误判：手工写 `/proc/<pid>/oom_score_adj` 只改变内核值，未必同步 `lmkd` 自己的候选链表；AMS 下一轮调整还可能覆盖手工值。

### Android 17 的 6 档 `LMK_TARGET`

`ProcessList` 仍保留 6 档 minfree。Android 17 的 adj 数组是：

| 档位 | adj | 低端基线（KB） | 高端基线（KB） |
|---|---:|---:|---:|
| Foreground | 0 | 12,288 | 73,728 |
| Visible | 100 | 18,432 | 92,160 |
| Perceptible | 200 | 24,576 | 110,592 |
| Perceptible-low | 250 | 36,864 | 129,024 |
| Cached-min | 900 | 43,008 | 147,456 |
| Cached-first | 950 | 49,152 | 184,320 |

最终值还会受 RAM、显示面积、64 位 cached 档乘数以及资源覆盖项影响。Framework 把 KB 转成页数再发送，所以不能在 16KB page 设备上把一页默认写死成 4KB。

这些数组在 Android 17 仍有两类用途：

- `ro.lmk.use_minfree_levels=true` 时，`lmkd` 使用传统的空闲页和文件缓存阈值；
- Framework 的 `getMemLevel()` 等逻辑仍会读取计算后的内存档位。

看到 `LMK_TARGET` 仍在源码中，不能据此判断默认 PSI 新策略也只看固定 minfree。

## Android 17 的 PSI 新策略

### `some` 与 `full` 的精确定义

内核通过 `/proc/pressure/memory` 导出 PSI：

- `some` 表示至少有一部分任务因该资源而停顿；
- `full` 表示所有非 idle 任务同时停顿，此时 CPU 无法继续做有效工作。

这里的对象是调度中的 task。把 `full` 解释为“设备上的所有进程都阻塞”过于宽泛，也忽略了 idle task。

PSI trigger 使用“某个窗口内累计 stall 多久”的形式。例如 `some 70000 1000000` 表示 1 秒窗口内累计出现 70 ms partial stall 时唤醒监听者。trigger 是唤醒信号，本身不等于一次 kill。

### Android 17 最终注册的阈值

`lmkd.cpp` 静态初始化的三档表是 `some 70 ms / some 100 ms / full 70 ms`。默认新策略启动时会覆盖它：

- LOW 档设为 0，不注册；
- MEDIUM 使用 `ro.lmk.psi_partial_stall_ms`，高性能设备默认 70 ms，low-RAM 设备默认 200 ms；
- CRITICAL 使用 `ro.lmk.psi_complete_stall_ms`，默认 700 ms；
- 默认窗口是 1000 ms。

所以，阅读源码时要追到 `init_psi_monitors()`。只摘录静态数组会得到错误的运行时阈值。

`use_new_strategy` 的默认值是：

```text
low_ram_device || !use_minfree_levels
```

上面的表达式用来说明默认选择条件：low-RAM 设备或未启用 minfree legacy 模式时采用新策略。若强制使用旧策略，Android 17 还要求 memcg v1；`mp_event_common()` 已标记 `[[deprecated("memcg v1 is not supported after Dec. 2026")]]`。这条注解是源码中的支持期限提示，不宜扩写成某个 Android 产品版本的兼容承诺。

`LowMemDetector` 和 “LMKD v2” 都不是 `android-17.0.0_r1` 中的正式类名或版本对象。前者最多表示低内存检测这一概念，后者常用于旧资料中区分 userspace lmkd 与早期内核模块。当前源码应按 `use_new_strategy`、PSI trigger、memevents 和具体函数解释。

Android 17 的 `libpsi` 为 lmkd 打开全局 `/proc/pressure/memory`，并没有遍历每个 App 的 `memory.pressure`。`ro.config.per_app_memcg`、Reaper 使用 `cgroup.kill`、cgroup v2 支持局部 PSI，是三个不同事实；它们不能推出 lmkd 会按“哪个 App cgroup 的 PSI 最高”选择 victim。

### PSI 唤醒之后还要检查什么

新策略收到 PSI 或轮询事件后，会继续读取并比较：

- `/proc/vmstat` 中的 workingset refault、direct reclaim 和 kswapd 统计；
- `/proc/meminfo` 中的空闲页、文件页、swap、匿名页等数据；
- `/proc/zoneinfo` 计算出的 zone watermark；
- free swap 与 swap utilization；
- 文件页 refault 相对 page cache 大小得到的 thrashing 比例；
- 上一次 kill 是否完成，以及 kill 后水位是否恢复。

Android 17 还在 boot completed 之后尝试注册 BPF memevents：

- direct reclaim begin/end；
- kswapd wake/sleep；
- 可选的 vendor LMK kill；
- 可选的 zoneinfo update。

若 memevent listener 不可用，`lmkd` 回退到 vmstat 差分来识别 direct reclaim 和 kswapd。BPF 事件改善了状态判断，它们也不自动触发一次 kill。

### 决策原因与候选门槛

Android 17 新策略的主要 kill reason 包括：

- critical PSI 下设备长时间无响应；
- low swap 与 page-cache thrashing 同时出现；
- 内存水位和 free swap 同时偏低；
- 内存水位偏低且 swap utilization 过高；
- 低水位伴随 thrashing；
- direct reclaim 期间 thrashing，或 direct reclaim 持续过久；
- thrashing 之后 file cache 仍低；
- kill 后仍跌破 min watermark；
- 普通低水位；
- vendor memevent 提供的原因。

普通低水位分支使用 `ro.lmk.lowmem_min_oom_score`。Android 17 默认是 `PREVIOUS_APP_ADJ + 1`，即 701，并且源码把它限制为不低于 `PERCEPTIBLE_APP_ADJ + 1`，即 201。

“701 等于从 cached 开始杀”并不严谨。启用 previous ladder 时，701～799 可能包含 previous 进程；800 是 service B；900 以上才是 cached。关闭该阶梯时，701～799 可能没有对应进程，但门槛仍是 701。严重 stall 下门槛可以降到 0，使前台层也进入候选范围。

`__mp_event_psi()` 按固定顺序评估 vendor 事件、kill 后仍低水位、critical PSI、low swap、thrashing、direct reclaim 与普通低水位。前面的分支命中后会确定本轮 reason，后面的条件不会覆盖它。诊断日志中的 reason 因而不仅说明“哪些条件为真”，也反映了源码判断顺序。

thrashing 来自 `workingset_refault_file` 相对窗口起点 active/inactive file pages 的增长率，描述文件页工作集反复丢失；它不是匿名页换入率、ZRAM 压缩率或 PSI `full`。成功 kill 后，部分 reason 会按 `thrashing_limit_decay` 降低下一轮动态阈值；没有合适 victim 时，历史 refault 可经过衰减保留到下一窗口。

还要区分三个相近开关：`thrashing_limit_critical` 可取消额外的 perceptible 保护；`stall_limit_critical` 比较 memory `full avg10`；`direct_reclaim_threshold_ms` 只在 memevents 能提供 direct-reclaim 起止时判断卡死。它们不是一个“critical thrashing”条件。

### 候选选择

`find_and_kill_process()` 从 `oom_score_adj=1000` 向门槛递减：

1. 先看数值更大的 adj 档；
2. 默认从该档链表尾部取候选；
3. `ro.lmk.kill_heaviest_task=true` 时，在该 adj 档选择内存最大的目标；
4. 当门槛已经下探到 `PERCEPTIBLE_APP_ADJ` 或更低时，源码会强制选择该档最重的进程，希望减少高价值 victim 的数量；
5. 一次函数调用成功处理一个目标后返回。

“一次调用只选一个”不等于一次压力周期只杀一个。PSI 事件后，`lmkd` 会进入 10 ms 或 100 ms 轮询；等待目标死亡时暂停轮询，收到 pidfd 死亡通知或超时后恢复。水位仍未恢复时，下一轮可以继续选择目标。

## 终止进程后：Reaper 怎样让内存尽快可用

`kill_one_process()` 在发出 kill 前会做几项防护和记账：

- 再读 `/proc/<pid>/status`，检查进程是否仍存在；
- 校验 TGID，降低 PID 复用导致误杀的风险；
- 读取 RSS、anonymous RSS、swap；
- 读取可用的 DMA-BUF PSS/RSS；
- 调用 vendor free-memory hook，若别处已经释放足够内存则跳过 kill；
- 建立 pidfd 或 PID 死亡等待。

随后，`reaper.kill(..., false)` 尝试把任务交给异步 Reaper：

1. 优先写 cgroup 的 kill 接口；较旧兼容路径会遍历 `cgroup.procs`；
2. 无合适 cgroup 时回退到 `pidfd_send_signal(SIGKILL)`；
3. Reaper 线程调用 `process_mrelease(pidfd, 0)`，促使内核提前回收已退出进程的匿名页和页表。

Reaper 线程会进入前台 `cpuset` 并提高自身优先级；它还会为目标进程组设置专门的 reap task profile。这个行为来自 AOSP `reaper.cpp`，无需借助某个 SoC 厂商的私有补丁来解释。

kill 信号发出和内存回到可用池之间可能有时间差。目标包含大量匿名页、swap 或 DMA-BUF 时，这段差距尤其值得观察。

### Android 17 的可观测输出

当前 `lmkd.cpp` 每次成功提交 kill 都执行：

```cpp
ATRACE_INSTANT_FOR_TRACK(LOG_TAG, desc);
```

这行代码用于说明事件类型。`LOG_TAG` 是 `lowmemorykiller`，`desc` 依次编码 PID、kill reason、目标 adj、最低候选 adj 和最大 thrashing。它是 instant event，并非带开始和结束时间的 duration slice；源码中也没有旧文章常提到的 `LMKD_TRACE_KILLS` 编译开关。

同一条路径还会：

- 写 logcat，包含进程名、PID、UID、adj、RSS、anon RSS、swap、DMA-BUF 与原因；
- 写 statsd 的 LMK kill atom；
- 向订阅的 Framework 客户端发送 kill 和 stats 消息。

`ProcessList` 收到 `LMK_PROCKILL` 后，把记录交给 `AppExitInfoTracker`，应用退出历史会标记为 `ApplicationExitInfo.REASON_LOW_MEMORY`。

### 主事件处理超时的 watchdog

lmkd 为事件 handler 启动 2 秒 watchdog。超时后，独立线程从 `oom_score_adj=1000` 向 0 搜索有效候选，通过 Reaper 同步 kill 一个进程并记录 `killinfo`。这条紧急路径不会重新执行完整的 PSI、水位和 reason 决策；日志中的 `lmkd watchdog timed out!` 应与普通压力 kill 分开统计。

## LMK、Linux OOM、进程内 OOM 与 MemoryLimiter

这四类故障都可能表现为“进程消失”或“内存不足”，证据来源不同：

| 机制 | 触发范围 | Android 17 的主要证据 |
|---|---|---|
| userspace `lmkd` | 系统整体压力，按 adj 选 victim | `lowmemorykiller` 日志、Perfetto `mem.lmk`、`REASON_LOW_MEMORY` |
| Linux OOM Killer | 内核分配无法满足，内核选 victim | kernel log；Framework `OomConnection` 记录 `REASON_LOW_MEMORY` + `SUBREASON_OOM_KILL` |
| Java/native 进程内 OOM | 单进程堆或地址空间分配失败 | `OutOfMemoryError`、abort/tombstone、crash exit reason |
| Android 17 MemoryLimiter | 单应用进程超过设备配置的配额 | `REASON_OTHER`，description 含 `MemoryLimiter:AnonSwap` |

看到 `REASON_LOW_MEMORY` 后，还要结合 subreason、`lmkd` 日志和 trace 区分系统 LMK 与 kernel OOM。Java `OutOfMemoryError` 也不能直接归因于 `lmkd`。

## LMK 如何变成用户可感知卡顿

LMK 自身的目标是缩短内存压力持续时间。体验问题通常出现在 kill 之后：

1. 系统持续处于低水位或 thrashing；
2. `lmkd` 反复处理 cached、service B 或 previous 进程；
3. 用户返回已被杀的应用；
4. 系统重新 fork 进程、绑定 Application、创建组件并恢复界面状态；
5. 新进程重新加载代码、资源、数据库页和网络数据，又推高内存与 IO 压力。

第 3 步没有发生时，kill 不会自动产生一次冷启动。只有用户或系统再次需要该进程，才会付出重建成本。界面状态可恢复也不代表进程仍是原进程。

排查时建议同时看四组指标：

- 单位时间 LMK 次数及 victim 的 adj 分布；
- victim 的 RSS、anon RSS、swap 和 DMA-BUF；
- kill 前的 PSI、watermark、swap 与 refault；
- 目标进程再次启动后的启动耗时、主线程、缺页和 I/O。

如果大量 victim 都在 900～999，系统大体还在牺牲缓存命中率换取可用内存；若频繁下探到 800、700 甚至 200 以下，后台工作、最近任务和用户可感知组件已经受到影响。

## 用 Perfetto、logcat 与退出历史定位

### Perfetto

以下配置同时采集 userspace LMK、adj 变化和系统内存计数。旧内核 LMK 事件只在分析历史设备时添加。

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      atrace_apps: "lmkd"
      ftrace_events: "oom/oom_score_adj_update"
      # 历史 in-kernel LMK 设备再启用：
      # ftrace_events: "lowmemorykiller/lowmemory_kill"
    }
  }
}

data_sources {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      meminfo_period_ms: 100
      vmstat_period_ms: 100
    }
  }
}

duration_ms: 30000
```

`atrace_apps: "lmkd"` 让 userspace LMK 事件进入 trace，`oom_score_adj_update` 用来还原 victim 当时的保护级别，`linux.sys_stats` 用来对齐水位和回收变化。量产设备允许的 ftrace 事件与采样频率可能受构建配置限制。

Android 17 对应的 Perfetto SQL 标准库会解析当前的 instant、旧 slice 和更早的 counter 三种 LMK 记录。下面的 SQL 使用统一后的 `android_lmk_events` 表列出 victim：

```sql
INCLUDE PERFETTO MODULE android.memory.lmk;

SELECT
  ts,
  process_name,
  pid,
  oom_score_adj,
  kill_reason
FROM android_lmk_events
ORDER BY ts;
```

查询结果给出事件时刻、被杀进程、adj 和 kill reason。Trace Processor 内部也会生成兼容旧查询的 `mem.lmk` instant；新分析脚本优先使用标准库表，可以直接取得 Android 17 instant 中携带的原因和 adj。下一步应回到同一时间窗口，检查内存计数、reclaim，以及稍后是否出现该包的新进程。

### 设备侧命令

下面的命令用于快速交叉验证，不依赖单一日志来源：

```bash
adb shell cat /proc/<pid>/oom_score_adj
adb shell dumpsys meminfo
adb shell dumpsys activity exit-info <package-name>
adb shell getprop | grep -E 'ro\\.lmk|sys\\.lmk'
adb logcat -b all -s lowmemorykiller ActivityManager MemoryLimiter
```

`/proc/<pid>/oom_score_adj` 只能观察存活进程的当前值；退出历史和 logcat 用于查找已死亡 victim；Perfetto 用于建立时序。三者时间要对齐。

### 判断因果的四步

1. 先确认进程退出时间与退出类型；
2. 再看 kill 前是否存在 PSI、低水位、低 swap 或 thrashing；
3. 核对 victim 当时的 adj 和内存构成；
4. 最终确认用户返回后是否产生新进程与启动代价。

仅看到 `lmkd` 在 trace 中运行，无法证明它导致卡顿。一次 `dumpsys meminfo` 快照也无法解释数十秒前的 kill。

## `onTrimMemory()` 与 cached app freezer 的边界

### App 仍应处理的两档回调

从 API 34 起，App 不再收到 `TRIM_MEMORY_RUNNING_MODERATE(5)`、`RUNNING_LOW(10)`、`RUNNING_CRITICAL(15)`、`MODERATE(60)` 和 `COMPLETE(80)`。这些常量随后被标记 deprecated。现代应用应集中处理：

- `TRIM_MEMORY_UI_HIDDEN(20)`：UI 离开可见区域，适合释放只服务于可见界面的资源；
- `TRIM_MEMORY_BACKGROUND(40)`：进程进入可终止的后台范围，适合释放可快速重建的缓存。

下面的例子展示按区间处理两档回调。清理函数应快速、幂等，避免在主线程执行大规模磁盘写入。

```kotlin
class App : Application() {
    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)

        when {
            level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> {
                imageCache.trimToBackground()
                decodedAssetCache.clearRebuildableEntries()
            }
            level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> {
                uiOnlyCache.clear()
            }
        }
    }
}
```

使用 `>=` 可以兼容未来插入的中间值。具体缓存库还要遵循线程约束；回调中释放仍在绘制或播放的对象可能引入崩溃和抖动。

Android 17 的 `ActivityThread.scheduleTrimMemory()` 把回调投递到主线程 `Choreographer.CALLBACK_COMMIT`，注释写明目的是在一帧绘制后执行，以降低 jank 风险；拿不到 Choreographer 时回退到主线程 Handler。特性开关 `skipBgMemTrimOnFgApp` 启用后，重要前台进程会跳过 background 或更高等级的 trim。

### Freezer 与 lmkd 是两条独立路径

cached app freezer 由 OomAdjuster/CachedAppOptimizer 根据 cached 状态安排。`CachedAppOptimizer.freezeAppAsyncInternalLSP()` 在目标 adj 至少为 900 时，先通过 Binder 请求 `TRIM_MEMORY_BACKGROUND`，再向 freeze handler 投递冻结消息。

Binder 请求先发出不等于 App 已经完成清理。回调在 App 主线程异步执行，冻结也由另一条 Handler 路径安排，因此应用不能把这次通知当作有完成保证的“截止期限”。

冻结后的进程仍存在，也没有释放全部进程内存。回到前台时是进程 thaw，常见代价是页重新变热、缓存重建和待处理任务恢复；这与 LMK 后从 Zygote 创建新进程的冷启动不同。Freezer 本身也不会产生 `ApplicationExitInfo` 的进程退出记录。

`lmkd` 不会通过 AMS 发出“请冻结这个 victim”的命令。把路径画成 `lmkd → CachedAppOptimizer → freeze` 会混淆两个子系统。

## Android 17 MemoryLimiter：单进程配额

Android 17 增加 MemoryLimiter，用于限制异常的单应用进程内存占用。它与 `lmkd` 的系统压力策略并行，只在一部分设备上启用。

### 启用与配置

默认实例同时满足以下条件才启用：

- Framework 特性开关 `memoryLimiterEnable()` 打开；
- 运行在 system UID；
- `/vendor/etc/memory-limiter-config.xml` 存在；
- XML 中有一组 `minimumRequiredMemTotal` 不高于当前 `/proc/meminfo` 的 `MemTotal`。

这些条件决定是否创建 enabled controller。native 层是否主动监控由 `memoryLimiterTrigger()` 控制，是否配置 swap 上限由 `memoryLimiterSwap()` 控制；`memory_limiter_disable_limits` 和 `memory_limiter_disable_kill` 还可以在运行时分别停用限制与 kill。

源码会选择符合设备总 RAM 的配置中 `minimumRequiredMemTotal` 最大的一组。可见与不可见进程的内存、swap 数值来自 vendor XML。`4 GB / 2 GB` 等 `sDefaultConfig` 只供测试，注释明确要求生产使用前另行评估，不能当作 Android 17 通用默认值。

### proc state 映射

MemoryLimiter 按 `ActivityManager` proc state 应用配置：

- persistent 与 persistent UI：取消限制；
- top、bound-top、important-foreground、top-sleeping：使用 visible 配置；
- FGS、bound FGS、important-background、transient-background、backup、service、receiver、home、last-activity、heavy-weight：使用 not-visible 配置；
- cached：`memory.high` 使用“忽略本次配置”，swap limit 设为 disabled；
- unknown 与 nonexistent：忽略。

因此，前台服务仍属于 not-visible 配额组。把 MemoryLimiter 概括成“只限制普通后台 Service”会漏掉 FGS、Receiver、Backup 和 Home 等状态。

### cgroup 文件与超限处理

native 实现使用进程 cgroup v2 文件：

- `memory.high`；
- `memory.swap.max`；
- `memory.events`；
- `memory.stat` 与 `memory.swap.current`。

Java 层部分注释和展示字符串仍写作 `memory.swap.high`，但 Android 17 native 源码的 `CgroupFile::kSwapMax` 明确解析到 `memory.swap.max`。描述运行行为时应以写入路径为准。

native 层写入 `memory.high` 和 swap 上限，并监听 `memory.events` 的 `high` 计数。`memory.high` 触发后，监控线程进入轮询区，比较 `anon + shmem + swap` 与两项配置之和。组合指标超过配置后，Java 回调会先取消该进程限制；若相关 profiling 特性开启且能解析包名，则发送 `TRIGGER_TYPE_ANOMALY`；随后延迟 30 秒请求 AMS 以 `"MemoryLimiter:AnonSwap"` 为原因杀进程。

这 30 秒用于给已配置的 profiling 留时间，不保证每次都能生成 heap dump。Android 17 官方文档给出的应用侧识别方式是：

- `ApplicationExitInfo.getReason()` 为 `REASON_OTHER`；
- `getDescription()` 包含 `"MemoryLimiter:AnonSwap"`。

设备支持时，可用以下命令检查和测试配额：

```bash
adb shell am memory-limiter status
adb shell am memory-limiter ignore <uid>
adb shell am memory-limiter ignore none
adb shell am memory-limiter manual <pid> 30
adb shell am memory-limiter manual <pid> none
```

这些命令在未启用 MemoryLimiter 的设备上没有效果。`manual` 的数字单位是 MB；`max` 移除限制，`none` 恢复系统默认配置。

## OEM 调校应怎样表述

AOSP 公开了多种设备调校入口，例如：

- `ro.config.low_ram`；
- `ro.lmk.psi_partial_stall_ms` 与 `ro.lmk.psi_complete_stall_ms`；
- `ro.lmk.thrashing_limit`、decay、swap 和 file-cache 参数；
- `ro.lmk.lowmem_min_oom_score` 与 `ro.lmk.kill_heaviest_task`；
- legacy `ro.lmk.use_minfree_levels`；
- vendor free-memory hook 与 vendor LMK memevent；
- Framework resource overlay 和 MemoryLimiter vendor XML。

具体厂商可以加入白名单、场景化水位或私有 kill reason。没有对应 ROM、版本和源码/trace 证据时，不应写成“某品牌总会把相机启动预留为固定容量”或“固定杀到 adj 200”。这些数字会随 RAM 档位、相机管线和产品配置变化。

## Android 15～17 的版本边界

### Android 15：16KB page size

16 KB page size 会改变页表、内部碎片和进程内存构成，也会改变 KB 与 page count 的换算。它不直接改写 `lmkd` 的优先级原则。`ProcessList` 发送 `LMK_TARGET` 时按运行时 `PAGE_SIZE` 把 KB 换算成页，分析脚本也应读取设备页大小。

### Android 16：userspace lmkd 与 Reaper

Android 16 已经具备 PSI/thrashing 决策、pidfd、Reaper 与 `process_mrelease()` 主链。`sys.lmk.minfree_levels`、`sys.lmk.reportkills` 等属性更早就存在，不适合作为 Android 16 独有特性。

### Android 17 源码边界

Android 17 源码中值得单独记住的边界包括：

- OOM adj 常量集中到 Process State Controller 的 `psc/Constants.java`；
- `ProcessList` 的 6 档目标使用 0、100、200、250、900、950；
- `LMK_PROCS_PRIO` 支持每包最多 3 个进程的批量 adj 更新；
- 默认 PSI 新策略覆盖静态三档阈值，LOW 监控关闭；
- boot completed 后尝试接入 BPF memevents；
- Reaper 输出无 `LMKD_TRACE_KILLS` 条件的 ATrace instant；
- MemoryLimiter 作为部分设备启用的单进程配额机制加入 Framework。

## 小结

理解 Android 17 LMK，可以抓住四条线：

1. AMS/Process State Controller 把组件状态和依赖关系计算成动态 `oom_score_adj`；
2. `ProcessList` 经控制 socket 把进程信息交给 `lmkd`，`lmkd` 更新 `/proc` 并维护候选表；
3. PSI 负责唤醒，watermark、swap、thrashing 和 reclaim 状态共同决定是否杀、门槛降到哪里；
4. Reaper 负责终止目标并加速页回收，Framework、statsd、logcat 与 Perfetto 记录结果。

性能分析也应沿这四条线取证。只看空闲内存、只看 victim 的生命周期标签，或把 freezer、MemoryLimiter 和 `lmkd` 混为一个机制，都会得到不完整的结论。

## 源码与官方资料

### Android 17 / API 37

- [`ProcessList.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [`psc/Constants.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/psc/Constants.java)
- [`MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [`com_android_server_am_MemoryLimiter.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)
- [`CachedAppOptimizer.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/CachedAppOptimizer.java)
- [`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [`lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/lmkd.cpp)
- [`include/lmkd.h`](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/include/lmkd.h)
- [`reaper.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/android-17.0.0_r1/reaper.cpp)

### Kernel `android17-6.18-2026-06_r6`

- [PSI documentation](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/accounting/psi.rst)
- [cgroup v2 memory controller](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)

### 官方说明与工具

- [AOSP Low memory killer daemon](https://source.android.com/docs/core/perf/lmkd)
- [Android 17 behavior changes: App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [Perfetto memory counters and LMK events](https://perfetto.dev/docs/data-sources/memory-counters)
