---
title: "ANR 日志 CPU 数据系统化分析方法论"
chapter: "9.13"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [ANR, CPU, proc, iowait, load-average, thread-state, page-fault]
related_chapters: ["9.1", "9.3", "9.11", "26.25"]
sources:
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ProcessCpuTracker.java"
  - type: official
    path: "developer.android.com/topic/performance/anr"
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 45.md）"
---

# 9.13 ANR 日志 CPU 数据系统化分析方法论


## 分析目标与版本锚点

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，内核语义锚点为 `android17-6.18-2026-06_r6`。分析目标是回答三个可验证的问题：

1. 这段统计覆盖哪个采样区间？
2. 区间内有哪些资源压力和调度现象？
3. 哪条线程、Binder 或 I/O 证据能把现象连到 ANR 主线程？

CPU 摘要适合缩小调查范围。单凭百分比、load 或 fault 数量无法给出根因。

## CPU 摘要由谁生成，写到哪里

Android 17 的 ANR 主路径位于 `ProcessErrorStateRecord.appNotResponding()`。它记录 `anrTime`，采集 PSI，触发 Java/native 栈转储，再把 CPU 摘要写入 `ActivityManager` 主日志。`/data/anr/anr_*` 是另一份栈转储文件。后续的 DropBox、bugreport 或厂商采集系统可以把两类材料一起封装，但分析工具不应假设 CPU 摘要必定位于 ANR 栈文件内部。

这条路径可能输出两套采样结果：

| 结果 | 采样器 | 内容 | 时间特征 |
|---|---|---|---|
| 全局进程榜 | `AppProfiler.mProcessCpuTracker` | 最多 10 个活跃进程，不含逐线程明细 | 长期采样器；两次更新至少相隔 5 秒，区间可能覆盖 ANR 之前或跨过 ANR |
| 临时进程榜 | `new ProcessCpuTracker(true)` | 活跃进程及其活跃线程 | 为挑选额外栈目标执行 `init()`，休眠 200 ms 后 `update()`；静默后台 ANR 不执行这次排名采样 |

临时采样器先把当前 CPU 消耗较高的两个候选 Java 进程加入额外栈目标。栈转储结束后，系统打印这套采样器的 load 和进程/线程统计。注释写着“1/2 second”，Android 17 实现中的显式休眠值是 200 ms；设备调度和 `/proc` 遍历会让两个采样点的墙钟间隔略长。

`anrTime` 是 ANR 处理开始附近的 `uptimeMillis()`，临时采样通常发生在它之后。因此标题可能写成 `ms later`。若分析器只接受 `ms ago`，便会把合法的 Android 17 输出判成格式错误。

## 先校对采样窗口

`ProcessCpuTracker.printCurrentState(now)` 的标题包含单调时钟相对时间和墙钟时间。下面是符合其格式的示意文本：

```text
CPU usage from 612ms to 5812ms later (2026-07-30 10:00:00.120 to 2026-07-30 10:00:05.320):
  126% 24155/com.sample.app: 91% user + 35% kernel / faults: 5286 minor 3 major
    78% 24170/RenderThread: 52% user + 26% kernel
23% TOTAL: 9% user + 6% kernel + 7% iowait + 0.2% irq + 0.8% softirq
```

标题表示两个采样点相对传入 `now` 的位置。这里的区间在 `anrTime` 之后；它描述 ANR 处理阶段的活动，不能倒推超时窗口内一直存在相同负载。括号中的墙钟时间便于和 logcat 对齐，持续时间计算仍应使用单调时钟，避免自动校时或时区变化造成跳变。

分析每个 CPU 块时应记录：

- `sample_start`、`sample_end` 和 `duration`；
- 两端相对 `anrTime` 的方向；
- 采样器是长期榜还是临时榜；
- 进程是否在区间内新建或退出，行首会分别出现 `+` 或 `-`；
- CPU 统计和主线程栈是否来自相近时段。

采样区间与超时区间没有充分重叠时，报告只能说明“转储阶段仍观察到某现象”。这条时序限制应进入结论的置信度。

## 百分比的分母决定含义

### 进程与线程行

进程行的分子来自 `/proc/<pid>/stat` 的 `utime + stime` 增量，分母是该进程两个采样点之间的 `uptime`。线程行用 `/proc/<pid>/task/<tid>/stat` 做相同计算。

多线程进程可在多个 CPU 上并行运行，所以进程占比超过 100% 合法。`126%` 表示区间内累计消耗约 1.26 个 CPU 核的执行时间，并不表示全机 CPU 超出上限。线程在任一时刻只能运行在一个 CPU 上，稳定存活线程的区间占比通常不高于 100%；极短区间、jiffy 取整以及新建/退出边界会引入误差。

进程的 `user` 与 `kernel` 都是执行时间：

- `user`：线程在用户态执行的时间；
- `kernel`：线程执行系统调用、缺页处理或其他内核路径的时间。

等待 mutex、Binder 回包或存储完成时，睡眠线程不累计执行时间。高 `kernel` 支持“内核路径消耗较多”，无法直接证明“锁等待较多”。定位锁或 Binder 依赖栈、调度状态和调用链。

### `TOTAL` 行

`TOTAL` 的分母是所有 CPU 的 `/proc/stat` 增量之和：

```text
user + system + iowait + irq + softirq + idle
```

这段表达式列出 Android 17 `ProcessCpuTracker` 纳入总量的字段。它把 `nice` 合并进 `user`，没有打印 `steal`。行首总百分比的分子排除 `idle`，却包含 `iowait`，所以它更接近“非 idle 记账占比”，不能当作纯执行利用率。

进程行与 `TOTAL` 行的分母不同。八核设备上，一个线程占满一核时，线程行约为 `100%`；若其余七核空闲，全机执行占比大约只有八分之一。不要用进程行与 `TOTAL` 行直接相减。

## `TOTAL` 各字段能说明什么

| 字段 | Android 17 统计口径 | 能支持的观察 | 不能单独证明的结论 |
|---|---|---|---|
| `user` | 所有 CPU 的 user + nice 增量 | 用户态执行占比较高 | ANR App 就是消耗者 |
| `kernel` | 所有 CPU 的 system 增量 | 系统调用、驱动、回收、调度等内核执行较多 | 锁等待或存储阻塞 |
| `iowait` | `/proc/stat` 的 iowait 增量 | 采样期间存在被记为 I/O 等待的 CPU 时间 | 某个 PID、某类设备或某次网络请求造成 ANR |
| `irq` | 硬中断时间增量 | 硬中断处理占比 | 中断源和受影响线程 |
| `softirq` | 软中断时间增量 | 网络、定时器等 softirq 工作可能活跃 | 网络就是 ANR 根因 |
| `idle` | idle 时间增量 | 全机仍有空闲 CPU 时间 | 目标线程能够及时获得合适 CPU |

Linux 内核文档明确提醒，`iowait` 很难精确解释：CPU 本身并不“等待任务”，等待 I/O 的任务睡眠后，CPU 可以运行别的任务；多核记账还可能让 iowait 计数出现反直觉变化。高 iowait 值适合作为存储、文件系统、swap 或设备路径的调查线索。网络 socket 阻塞一般表现为任务睡眠，不能由 iowait 数值直接确认。

固定使用 `iowait > 5%` 或 `idle < 20%` 会制造误判。5 秒窗口里的 4% iowait、200 ms 窗口里的 4% iowait 与主线程体验不同；系统总量也可能掩盖某个 CPU、cpuset 或热插拔集群上的排队。阈值应来自同机型、同场景、同窗口的基线，并和 PSI、线程调度片段一起使用。

## Load Average 不等于 CPU 利用率

`ProcessCpuTracker` 只读取 `/proc/loadavg` 的 1、5、15 分钟值，并原样输出：

```text
Load: 6.31 / 6.52 / 6.66
```

三个值是指数衰减平均，覆盖的历史远长于短时 ANR CPU 采样。Linux load 同时计入可运行任务和不可中断睡眠任务。一个长期处于 D 状态的任务能抬高 load，却几乎不消耗 CPU；一个短时占满大核的线程也可能没有立刻显著改变 1 分钟 load。

因此：

- 八核设备 `load=1` 不代表 12.5% CPU；
- `load / CPU 数` 不能还原利用率；
- `load > CPU 数` 不能自动判定 ANR 由 CPU 饱和造成；
- 异构 CPU、cpuset、线程亲和性、热限制和离线 CPU 会进一步削弱“按核数均分”的解释。

load 的用途是提示“较长时间内，可运行或不可中断任务数量是否偏多”。要确认 CPU 排队，应查看 Perfetto 的 Runnable 区间、`sched_wakeup` 到 `sched_switch` 延迟或 `/proc/<pid>/schedstat`；要确认资源阻塞，应结合 D 状态、PSI 与内核调用栈。

## `ProcessCpuTracker` 不打印 R、S、D

Android 17 的 `PROCESS_STAT_*_FORMAT` 跳过 `/proc/<pid>/stat` 第三个字段。`printProcessCPU()` 的标准格式是 `pid/name:`，不会生成 `pid/name(R):`。日志若带括号状态字符，它来自厂商扩展、其他采集器或二次解析结果，不能套用 AOSP `ProcessCpuTracker` 的字段位置。

线程分析还要区分两种状态体系：

| 层级 | 常见展示 | 含义 |
|---|---|---|
| ART 线程状态 | `Runnable`、`Waiting`、`TimedWaiting`、`Blocked`、`Native` | Java/ART 视角，用于解释 monitor、Object.wait、native 调用等 |
| Linux 调度状态 | `R`、`S`、`D` 等 | 内核在某个采样时刻看到的运行/睡眠状态 |

Linux 中：

- `R` 覆盖正在 CPU 上执行和位于 run queue 的任务。单点 `R` 无法区分两者；
- `S` 是可中断睡眠，可对应 futex、Binder、epoll、timer、socket 或许多驱动等待；
- `D` 是不可中断睡眠，常见于存储、文件系统、内存回收、swap 或驱动路径，也存在其他内核等待原因。

一份静态栈无法告诉你状态持续了多久。`/proc/<pid>/wchan` 只给当前睡眠点，还受权限、内核符号和采样竞争影响。Perfetto 的 `thread_state` 能把 Running、Runnable、Sleeping、Uninterruptible Sleep 放进时间轴，适合回答“主线程在超时窗口内卡了多久”。

## Page fault 是事件计数，不是分配字节数

`ProcessCpuTracker` 读取 `/proc/<pid>/stat` 的 `minflt` 和 `majflt`，打印两个采样点之间的增量：

- `minor`：缺页处理不需要从后备存储读取页面。匿名页首次触达、写时复制、已在 page cache 中的文件页映射等都可能增加计数；
- `major`：缺页处理需要从后备存储取回页面。文件映射、swap-in 等路径都可能出现；在 Android 上，swap 后备可能是 zram，不能一律称为物理磁盘读取。

这两个计数没有地址、文件、延迟和字节数。`minor faults × 4 KB` 不能当作内存分配量，原因包括：

- Android 设备可能使用 4 KB、16 KB 等页大小；
- fault 表示页表或页面可用性事件，不等同于 allocator 请求；
- 一个映射的访问、写时复制和重新 fault 都可能改变计数；
- 大页、预读和 page cache 让 fault 次数与实际 I/O 字节数失去一一对应关系。

major fault 在短窗口内集中出现时，应检查主线程是否同时处于 D 状态，以及文件系统、swap、memory reclaim 和 block I/O 事件是否时间重合。minor fault 很多时，可调查初始化触页、mmap、COW、GC 后工作集重建或大量新匿名页，但结论仍需调用栈和内存轨迹支持。

## PSI 给出更直接的资源压力背景

Android 17 在 ANR 报告中调用 `ResourcePressureUtil.currentPsiState()`，依次读取：

```text
/proc/pressure/memory
/proc/pressure/cpu
/proc/pressure/io
```

每个文件通常包含 `some` 和 `full`，以及 `avg10`、`avg60`、`avg300` 和累计 `total`。这些字段描述任务因 CPU、内存或 I/O 资源不足而停顿的时间比例：

- `some`：至少有部分任务因该资源停顿；
- `full`：所有非 idle 任务同时因该资源停顿；系统级 `cpu full` 按内核接口定义为 0；
- `avg10/60/300`：最近 10、60、300 秒的衰减平均；
- `total`：自启动以来的累计停顿微秒数，只有做差后才对应自定义窗口。

单次 `total` 绝对值没有事件强度含义。`avg10` 也可能把 ANR 前后的压力混在一起。分析时可把 PSI 当成资源背景，再用 Perfetto 或连续两次 PSI 快照确定时间归属。

## 一条可审计的诊断流程

### 第一步：确认材料来自哪个时段

从 ANR Reason、`anrTime` 附近的 logcat、CPU 标题和栈文件头提取时间。把长期榜与临时榜分开，标记每个采样区间和超时区间的重叠关系。没有时间重叠时，下调因果置信度。

### 第二步：判断全机是否存在资源竞争

用 `TOTAL` 描述执行、iowait 与 idle 的分布，用 PSI 区分 CPU、memory、io 压力。不要在这一步指定根因进程。

| 组合观察 | 调查方向 | 还需要的证据 |
|---|---|---|
| idle 低、`user + kernel` 高、CPU PSI `some` 高 | CPU 排队或抢占 | 主线程 Runnable 延迟、占 CPU 的线程及调用栈 |
| iowait 上升、I/O PSI 上升 | 存储、文件系统、swap 或设备路径 | D 状态区间、`blocked_function`、f2fs/block/reclaim 事件 |
| kernel 高、softirq 高 | 网络、驱动、回收或高频系统调用 | softirq 类型、内核调用栈、目标线程时序 |
| 全机 idle 充足，目标线程长时间 Runnable | cpuset、亲和性、优先级、单核热点或调度反转 | 目标 CPU run queue、调度优先级、频率与热限制 |
| 全机压力低，主线程 Sleeping/Blocked | Binder、monitor、条件变量或消息依赖 | 栈、Binder flow、锁持有者和唤醒关系 |

### 第三步：把消耗者和受害者分开

ANR 进程 CPU 高，说明它在区间内执行较多；主线程仍可能在等待工作线程。ANR 进程 CPU 低，也可能因为主线程被锁、Binder 或 I/O 挂起。应分别标注：

- 消耗 CPU 的进程/线程；
- 触发超时的主线程；
- 主线程等待的服务端、锁持有者或工作线程。

三者是同一线程时，CPU 热点更接近根因。三者分离时，需要沿依赖关系继续调查。

### 第四步：用线程时间轴验证候选解释

推荐查看 [9.8 ANR 与内核 Trace 联合诊断](08-anr-kernel-trace-joint-diagnosis.md) 中的 Perfetto 采集项，并把以下事件对齐：

- `sched_wakeup`、`sched_switch` 和 `thread_state`；
- Binder transaction 与 reply；
- 主线程消息、monitor contention 或应用 trace section；
- `blocked_function`、文件系统、reclaim、swap 与 block I/O；
- CPU frequency、idle 和 thermal/cpuset 信息。

`ProcessCpuTracker` 告诉你区间内累计了多少执行时间；调度时间轴告诉你这些时间发生在何处，以及主线程其余时间在等待什么。

### 第五步：回到源码或业务入口

确认具体调用点后，再判断修复层级：

- 主线程 CPU 热点：拆分计算、降低复杂度、预计算或移出关键响应路径；
- 同步 I/O：移动到受控后台执行，处理结果回传和取消；
- Binder 依赖：缩短服务端临界路径，避免调用锁内外部服务，补充异步协议或超时降级；
- 锁竞争：缩短锁范围，移除锁内 I/O/Binder，核对持有者调度优先级；
- 系统压力：减少并发和后台工作，结合设备策略、内存回收与热限制评估。

修复验收应复现相同入口并比较主线程关键路径时长、Runnable 延迟、PSI 增量和用户可见超时结果，不能只比较某一行 CPU 百分比。

## 四种常见证据组合

### 主线程计算热点

典型材料是 ANR 进程 user 时间高、主线程在超时窗口内长时间 Running、采样调用栈集中到同一段计算代码。全机仍可能有大量 idle，因为一个线程只能占用一个 CPU。此时 load 和 iowait 没有决定作用。

### CPU 争用造成受害者排队

目标进程 CPU 可能不高，主线程却反复处于 Runnable。若同一 cpuset 内已有高优先级或大量线程占用 CPU，并伴随 CPU PSI `some` 增长，调度等待就是强候选。还要排除频率过低、热限制、线程优先级和 affinity。

### I/O、swap 或 reclaim 停顿

主线程或其依赖线程出现持续 D 状态，I/O 或 memory PSI 同期增长，调用栈落在文件系统、swap 或 reclaim 路径时，证据才形成相互支持。单独出现 iowait、major fault 或 D 状态只能提供调查方向。

### Binder 或锁依赖

主线程处于 ART `Blocked`、`Waiting` 或 native wait，Binder flow 指向慢服务端，或 monitor 栈能找到持有者。此类 ANR 常伴随较低的目标进程 CPU。系统 kernel 百分比高低都不能替代依赖链证据。

## 工具边界与正确用法

### `dumpsys cpuinfo`

下面的命令适合取得当前 `AppProfiler` 采样器输出：

```bash
adb shell dumpsys cpuinfo
```

它和 ANR 报告使用同一类长期 `ProcessCpuTracker`，但执行时刻不同。若命令在 ANR 结束数秒后运行，其结果只能描述新的区间，适合观察持续性问题，不应覆盖 ANR 原始采样。

### simpleperf

对可复现的 native 或混合 CPU 热点，可在目标进程存活时录制 10 秒调用链：

```bash
adb shell simpleperf record -p <pid> --duration 10 -g \
  -o /data/local/tmp/anr.data
adb pull /data/local/tmp/anr.data
simpleperf report -i anr.data
```

`--duration 10` 才是录制时长；`-t` 表示线程 ID。`-p`、`-t` 和调用链采样受 build type、SELinux、perf_event 权限以及 App 的 debuggable/profileable 属性限制。采样到 `openat` 或 `pread64` 只证明该函数进入过 CPU 样本，阻塞时线程不运行，不能凭函数名计算 I/O 等待时长。I/O 时序仍应由 Perfetto 或内核事件确认。

### Perfetto

Perfetto trace 不会因为系统生成了 ANR 栈文件就自动出现在 `/data/anr`。Android 17 的 ANR 路径会发出 Perfetto instant，并写一个用于触发 Perfetto 的 stats atom；是否有对应 trace 取决于设备配置、触发器和权限。实验环境应预先配置持续或触发式 trace，线上环境则确认厂商是否收集。

线程状态分析可参考 [13.6 Perfetto 线程 CPU 状态](../../part3-tools/ch13-perfetto/06-thread-cpu-states.md)，native CPU 采样可参考 [14.2 Simpleperf](../../part3-tools/ch14-other-tools/02-simpleperf.md)。

## 自动解析器应输出证据，不要输出伪确定性

建议把解析结果分为“事实字段、派生观察、候选解释”三层：

```text
事实字段
  ├─ 采样器类型、区间、相对 ANR 时刻
  ├─ process/thread user、kernel、fault delta
  ├─ TOTAL 各记账项
  └─ load 与 PSI 原始字段

派生观察
  ├─ 单进程跨核执行
  ├─ 全机执行繁忙或仍有 idle
  ├─ CPU / memory / I/O pressure
  └─ 采样与超时窗口是否重叠

候选解释
  └─ 必须列出支持证据、反证和缺失材料
```

这个分层让报告保留原始计数，也让工程师知道哪句话来自公式，哪句话仍待 Trace 或栈验证。解析器不应内置“iowait 5% 即 I/O 瓶颈”“major fault 100 次即磁盘问题”之类的跨设备常量。

更稳妥的规则是：

- 阈值按设备、build、场景和采样窗口建立基线；
- 对每条推断要求至少两类独立材料；
- 时间不重叠、字段缺失或 OEM 格式未知时降低置信度；
- 保留原始文本，解析失败时不丢弃整段报告；
- 把厂商扩展字段标成带命名空间的可选字段，不预设品牌固定格式。

## 结论

Android 17 的 ANR CPU 数据回答的是“两个采样点之间，谁执行了多少、全机如何记账”。它不记录完整调度历史，也不携带锁、Binder、文件或 fault 地址。可靠分析要按以下次序收敛：

1. 校对采样窗口和 ANR 超时窗口；
2. 区分长期进程榜与约 200 ms 的临时进程/线程榜；
3. 按各自分母解释进程行与 `TOTAL`；
4. 用 PSI 判断资源压力背景；
5. 用栈、Binder flow、Perfetto 调度和 I/O 事件验证依赖链；
6. 在同场景复现中检验修复效果。

这套流程允许 CPU 摘要快速排除错误方向，同时避免把相关性写成因果。

## 参考资料

- [AOSP `ProcessCpuTracker.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java)
- [AOSP `ProcessErrorStateRecord.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessErrorStateRecord.java)
- [AOSP `AppProfiler.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppProfiler.java)
- [AOSP `StackTracesDumpHelper.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/StackTracesDumpHelper.java)
- [AOSP `ResourcePressureUtil.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/ResourcePressureUtil.java)
- [Linux proc 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)
- [Linux PSI 文档（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/accounting/psi.rst)
- [Android Developers：ANR 诊断](https://developer.android.com/topic/performance/vitals/anr)
- [26.25 ProcessCpuTracker 与 `/proc` CPU 数据采集](../../part5-app/ch26-observability/25-proc-filesystem-cpu-monitoring.md)
