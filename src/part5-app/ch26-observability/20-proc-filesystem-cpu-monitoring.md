---
title: "ProcessCpuTracker 与 /proc 伪文件系统 CPU 数据采集"
chapter: "26.20"
section: "26.20"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ProcessCpuTracker.java"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/CpuTracker.java"
  - type: official
    path: "developer.android.com/reference/android/os/Debug.MemoryInfo"
  - type: blog
    path: "Clippings/线上疑难问题 45.md"
tags: [proc, ProcessCpuTracker, CPU, monitoring, observability, /proc/stat]
related_chapters: ["26.1", "26.3", "9.3"]
---

# 26.20 ProcessCpuTracker 与 /proc 伪文件系统 CPU 数据采集

## CPU 使用率的三种口径

Android 上的“CPU 使用率”至少有三种口径：

- 系统在采样窗口内有多少 CPU 容量处于忙碌状态；
- 某个进程在采样窗口内消耗了多少个“核等价”的 CPU 时间；
- 某个线程何时被调度、在哪个 CPU 上运行，以及等待运行队列多久。

这三类问题分别适合用 `/proc/stat`、进程 CPU 时间和调度事件回答。把它们混成一个百分比，常见后果是把单核占满误报成整机占满，或者把 load average 当作 CPU 利用率。

Android 17 还需要先处理权限边界：普通应用无法照搬 `system_server` 的 `ProcessCpuTracker` 方案。源码锚点采用 AOSP `android-17.0.0_r1` 和 Android Common Kernel `android17-6.18-2026-06_r6`，应用侧与平台侧的可采数据分别说明。

## procfs 是接口，不是磁盘快照

`procfs` 是内核提供的虚拟文件系统。读取 `/proc/stat`、`/proc/<pid>/stat` 等节点时，内核按节点实现生成文本；有些节点也允许写入，用来调整内核参数。

使用它时需要记住四个边界：

- 文件的 `st_size` 可能为零，也可能提供其他值，不能用“所有文件大小都为零”判断内容是否存在。
- 一次读取看到的是生成过程中的内核状态。多个文件之间没有事务，也不能认为整份采样天然原子。
- 进程可能在 `open()`、`read()` 之间退出，PID 还可能被复用。跨时刻跟踪进程时，应同时校验 `/proc/<pid>/stat` 的 `starttime`。
- 部分节点基于 `seq_file`，是否支持定位由节点实现决定；业务代码不应假设所有节点都不能 `lseek()`。

因此，可靠的采样器应给每次样本附加单调时钟时间戳，允许单个节点读取失败，并在计数回退、进程实例变化或字段不足时丢弃本轮差值。

内核接口与挂载选项可在 [`Documentation/filesystems/proc.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst) 中核对。

## Android 17 的访问边界

### 普通应用不能读取全局 CPU 节点

AOSP Android 17 的 `app_neverallows.te` 明确禁止所有普通应用域读取 `proc_stat` 和 `proc_loadavg`。这条规则覆盖不同 `targetSdk` 对应的 `untrusted_app_*` 域，因此不能用降低 `targetSdk` 恢复 `/proc/stat`。

同一份策略还保留了从 Android O 开始对这些拒绝日志的 `dontaudit` 处理。应用读取失败时，设备日志中未必出现醒目的 SELinux denial，不能据此判断节点可读。

Android 的 `/proc` 还使用 `hidepid=2` 隔离其他 UID 的进程目录；Android 17 的 first-stage init 以 `gid=AID_READPROC` 挂载该文件系统。普通应用可以依赖的是自身数据；其他 PID 是否可见不能作为 SDK 能力。Android 10 的公开隐私变更针对的是 `/proc/net`，而且影响设备上的所有应用，并不是 Android 10 才按 `targetSdk` 关闭整个 `/proc/<pid>`。

| 调用方 | Android 17 上适合依赖的数据 | 不应依赖的数据 |
|---|---|---|
| 普通应用或 APM SDK | `Process.getElapsedCpuTime()`、`/proc/self/stat`、自身可见的 `task` 节点 | `/proc/stat`、`/proc/loadavg`、全系统 PID 遍历 |
| 具有专用 SELinux 规则的平台服务 | 策略允许的全局节点与进程节点 | 仅凭“预装”或“平台签名”推定访问权 |
| `shell`、root、系统 tracing 服务 | Perfetto、受控的 procfs/ftrace/BPF 采集 | 把调试权限当作线上应用权限 |

厂商策略可以比 AOSP 更严格。采集器仍要把节点访问视为可失败能力，而不是用品牌或系统版本推断。

对应证据包括：

- [`app_neverallows.te` 的 procfs 禁止规则](https://android.googlesource.com/platform/system/sepolicy/+/refs/tags/android-17.0.0_r1/private/app_neverallows.te)
- [`untrusted_app_all.te` 的历史兼容说明](https://android.googlesource.com/platform/system/sepolicy/+/refs/tags/android-17.0.0_r1/private/untrusted_app_all.te)
- [`first_stage_init.cpp` 的 procfs 挂载参数](https://android.googlesource.com/platform/system/core/+/refs/tags/android-17.0.0_r1/init/first_stage_init.cpp)
- [Android 10 对 `/proc/net` 的公开说明](https://developer.android.com/about/versions/10/privacy/changes#restriction-access-proc-net)

## `/proc/stat`：全机 CPU 容量口径

平台进程读取 `/proc/stat` 时，首行汇总所有 possible CPU 的累计值，后续 `cpu0`、`cpu1` 等行列出当前在线 CPU 的独立累计值。下面只展示首行字段顺序，便于说明计算式：

```text
cpu  user nice system idle iowait irq softirq steal guest guest_nice
```

这些数值自启动以来累计，单位为 `USER_HZ`。不要把频率写死为 100；Android 17 的 `ProcessCpuTracker` 通过 `Os.sysconf(OsConstants._SC_CLK_TCK)` 获取换算系数。

各字段的含义如下：

| 字段 | 含义 |
|---|---|
| `user` | 普通优先级任务在用户态运行的时间 |
| `nice` | `nice > 0` 的低优先级任务在用户态运行的时间 |
| `system` | 任务在内核态运行的时间 |
| `idle` | CPU 空闲时间 |
| `iowait` | 内核归入等待 I/O 的空闲时间 |
| `irq` | 处理硬中断的时间 |
| `softirq` | 处理软中断的时间 |
| `steal` | 虚拟化环境中被宿主占用的时间 |
| `guest` | 运行普通优先级虚拟 CPU 的时间，已经计入 `user` |
| `guest_nice` | 运行低优先级虚拟 CPU 的时间，已经计入 `nice` |

`guest` 和 `guest_nice` 是细分项，不能再次加进总时间。Android 17 内核的 `account_guest_time()` 同时更新 `user`/`nice` 与对应的 guest 计数，这一包含关系可在 [`kernel/sched/cputime.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cputime.c) 中看到。

若产品要计算本机任务消耗的 CPU 时间，可以采用下列定义：

- `total = user + nice + system + idle + iowait + irq + softirq + steal`
- `localBusy = user + nice + system + irq + softirq`
- `localBusyPercent = ΔlocalBusy / Δtotal × 100%`

`steal` 表示虚拟机被宿主占用的时间，不是本机任务执行时间。如果指标要表达“对虚拟机不可用的 CPU 容量”，可以把 `steal` 加入分子，但应使用不同名称。`guest` 和 `guest_nice` 仍不能重复相加。

这里的 `cpu` 首行汇总多个 CPU。假设八个 CPU 在一个窗口内都保持在线，一个进程只占满其中一个 CPU，那么 `Δprocess / Δtotal` 接近整机容量的八分之一，而不是 100%。原先把该结果称为“单核百分比”，再除一次 CPU 数，会重复归一化。

还要注意：

- 内核文档明确指出 `iowait` 在多核和无时钟节拍场景下并不可靠，某些条件下甚至会回退。计数回退时应丢弃样本，不能用零替代负差值。
- CPU 热插拔会改变在线 CPU 集合。不要用固定核数补偿 `/proc/stat` 的聚合差值。
- CPU 时间没有表达核心微架构、频率和调度容量。同样的一毫秒在小核与大核上不代表相同工作量或能耗。

Android 17 对应实现位于 [`fs/proc/stat.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/stat.c)。该文件还输出：

- `ctxt`：全机累计上下文切换次数；
- `btime`：启动时间的 Unix 时间戳；
- `processes`：创建过的进程和线程数量；
- `procs_running`：正在运行或可运行的线程数量；
- `procs_blocked`：等待 I/O 的阻塞任务数量。

这些值适合补充描述系统压力，但不能替代调度 trace。

## 两种进程 CPU 百分比不要混用

`/proc/<pid>/stat` 的第 14、15 个字段分别是 `utime` 和 `stime`，两者相加得到进程累计 CPU 时间。对两次样本做差后，可以定义两种常见口径。

### 核等价利用率

`ΔprocessCpu / Δwall × 100%` 表示进程用了多少个核：

- 100% 表示窗口内约占用一个 CPU；
- 150% 表示平均约占用 1.5 个 CPU；
- 多线程进程可以超过 100%。

这是应用性能监控中更直观的口径。它不需要 `/proc/stat`，普通应用可以用公开 API [`Process.getElapsedCpuTime()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Process.java) 获取当前进程累计 CPU 毫秒数。

下面的 Kotlin 示例同时保留“设备唤醒期间”和“完整观察窗口”两个分母，避免睡眠时间是否计入指标变成隐含条件：

```kotlin
import android.os.Process
import android.os.SystemClock

data class CpuPoint(
    val processCpuMs: Long,
    val uptimeMs: Long,
    val realtimeMs: Long,
)

data class CpuUsage(
    val awakeCorePercent: Double,
    val windowCorePercent: Double,
)

class SelfCpuSampler {
    private var previous: CpuPoint? = null

    fun sample(): CpuUsage? {
        val current = CpuPoint(
            processCpuMs = Process.getElapsedCpuTime(),
            uptimeMs = SystemClock.uptimeMillis(),
            realtimeMs = SystemClock.elapsedRealtime(),
        )
        val old = previous
        previous = current
        if (old == null) return null

        val cpuDelta = current.processCpuMs - old.processCpuMs
        val uptimeDelta = current.uptimeMs - old.uptimeMs
        val realtimeDelta = current.realtimeMs - old.realtimeMs
        if (cpuDelta < 0 || uptimeDelta <= 0 || realtimeDelta <= 0) return null

        return CpuUsage(
            awakeCorePercent = cpuDelta * 100.0 / uptimeDelta,
            windowCorePercent = cpuDelta * 100.0 / realtimeDelta,
        )
    }
}
```

`uptimeMillis()` 在深度睡眠期间停止，适合描述设备醒着时的 CPU 密度；`elapsedRealtime()` 包含深度睡眠，适合描述完整观察窗口内的平均负担。这个示例只统计当前进程，不会自动合并应用的 `:remote` 等其他进程。

### 整机容量占比

`ΔprocessCpu / ΔallCpu × 100%` 表示进程占全机累计 CPU 容量的比例，通常位于 0% 到 100% 之间。它需要全局 CPU 计数，普通应用在 AOSP Android 17 上无法直接计算。

若产品为了跨设备比较而把核等价利用率除以 CPU 数量，必须把“CPU 数量”定义清楚：是物理核心、当前在线 CPU、进程 cpuset 允许的 CPU，还是按调度容量加权的 CPU。移动设备会热插拔，并且大小核性能不同，简单除以 `Runtime.availableProcessors()` 只能算近似值。

## `/proc/<pid>/stat` 的解析规则

CPU 采集常用字段如下，索引从 1 开始：

| 索引 | 字段 | 说明 |
|---:|---|---|
| 1 | `pid` | 进程或线程 ID |
| 2 | `comm` | 括号包围的任务名，可包含空格和右括号 |
| 3 | `state` | `R`、`S`、`D`、`Z`、`T` 等状态 |
| 14 | `utime` | 用户态累计 CPU 时间，单位为 `USER_HZ` |
| 15 | `stime` | 内核态累计 CPU 时间，单位为 `USER_HZ` |
| 16 | `cutime` | 已等待子进程累计的用户态 CPU 时间 |
| 17 | `cstime` | 已等待子进程累计的内核态 CPU 时间 |
| 20 | `num_threads` | 线程数量 |
| 22 | `starttime` | 任务从系统启动起算的创建时刻，单位为 clock tick |
| 23 | `vsize` | 虚拟地址空间大小，单位为字节 |
| 24 | `rss` | 驻留页数量，需要乘页大小得到字节 |
| 39 | `processor` | 任务上次运行所在的 CPU 编号 |

不能直接按空格切整行，因为 `comm` 可以包含空格和 `)`。分隔符是整行最右侧的 `)`；它后面的第一个 token 才是字段 3。下面的代码只解析 CPU 采集需要的稳定前缀，并保留 `starttime` 用于识别进程实例：

```kotlin
import android.system.Os
import android.system.OsConstants
import java.io.File

data class ProcCpuTicks(
    val cpuTicks: Long,
    val startTicks: Long,
)

private val whitespace = Regex("\\s+")

fun readSelfCpuTicks(): ProcCpuTicks? {
    return try {
        val line = File("/proc/self/stat").readText()
        val closingParen = line.lastIndexOf(')')
        require(closingParen > 0)

        // tail[0] 对应字段 3；utime、stime、starttime 分别对应 11、12、19。
        val tail = line.substring(closingParen + 1).trim().split(whitespace)
        require(tail.size > 19)
        ProcCpuTicks(
            cpuTicks = tail[11].toLong() + tail[12].toLong(),
            startTicks = tail[19].toLong(),
        )
    } catch (_: Exception) {
        null
    }
}

fun clockTicksPerSecond(): Long =
    Os.sysconf(OsConstants._SC_CLK_TCK)
```

解析失败返回 `null`，调用方应丢弃这一轮样本。不要返回 `-1` 后继续计算差值，否则一次权限拒绝或进程退出会产生很大的伪 CPU 峰值。跟踪任意 PID 时，还要在两次样本之间比较 `startTicks`；数值变化说明 PID 已对应另一个进程。

内核可能在末尾追加字段，因此不应断言 `/proc/<pid>/stat` 固定有 44 个字段。按需要解析稳定前缀，比校验总字段数更兼容。Android 17 生成这些字段的代码位于 [`fs/proc/array.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c)。

## 线程级采集

`/proc/<pid>/task/<tid>/stat` 与进程 stat 使用相同字段格式，但 `utime`、`stime` 对应单个线程。对普通应用而言，`/proc/self/task/` 可用于：

- 区分主线程与后台工作线程的 CPU 消耗；
- 查看 Binder 线程是否持续占用 CPU；
- 观察线程数量和线程 CPU 时间是否持续增长；
- 在卡顿前后保留轻量的线程 CPU 快照。

逐线程轮询的成本随线程数增长，并且目录枚举会遇到线程创建、退出的竞争。它适合短时诊断或低频摘要，不适合替代调度事件。主线程 CPU 较低也不代表主线程健康：锁等待、Binder 等待和 I/O 阻塞都可能让线程不消耗 CPU，却仍造成卡顿或 ANR。

## Android 17 `ProcessCpuTracker` 的准确模型

`ProcessCpuTracker` 位于 `com.android.internal.os`，是 Framework 内部类，不属于 SDK API。Android 17 源码中它直接声明为 `public class ProcessCpuTracker`，不存在同路径的 `CpuTracker` 基类。

它的主要入口与数据结构可以概括为：

```text
ProcessCpuTracker(boolean includeThreads)
  init(): void
  update(): void
  countStats(): int
  getStats(index): Stats
  countWorkingStats(): int
  getWorkingStats(index): Stats
  getCpuTimeForPid(pid): long
  getCpuDelayTimeForPid(pid): long

Stats
  pid, uid, name, baseName
  base_utime, base_stime, base_uptime
  rel_utime, rel_stime, rel_uptime
  rel_minfaults, rel_majfaults
  active, working, added, removed
```

这份摘要强调方法签名和字段名：`update()` 不返回布尔值，没有 `addCpuTime()`、`getProcessStats()` 或 `getIdleCpuTime()` 等接口。完整定义见 [`ProcessCpuTracker.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java)。

一次 `update()` 的流程是：

1. 用 `Process.readProcFile()` 读取 `/proc/stat` 的 `user` 到 `softirq` 七个字段，并按 `_SC_CLK_TCK` 换算为毫秒。
2. 用 `Process.getPids("/proc", ...)` 枚举进程，而不是只更新预先注册的 PID。
3. 对已有 PID 读取 `/proc/<pid>/stat`，计算 CPU 时间和缺页次数增量。
4. 新 PID 还会读取任务名与 `vsize`；退出的 PID 标记为 `removed` 后从活动列表移除。
5. `includeThreads` 为 `true` 时，在进程 CPU 发生变化后继续扫描其 `task` 目录。
6. 读取 `/proc/loadavg`，在数值变化时调用 `onLoadChanged()`。

`Stats.active` 表示本次 CPU 累计值发生变化；`Stats.working` 表示本轮需要进入工作集合，新发现的进程也可能被标为 working。退出项会短暂设置 `removed` 后从活动列表移除。三者不能互换。

### 同一个类中也存在不同百分比定义

Android 17 的 `getTotalCpuPercent()` 只用 `user + system + irq` 作为忙时间，并用 `user + system + irq + idle` 作分母；`iowait` 和 `softirq` 都未进入这个方法。另一方面，`printCurrentState()` 与 proto 输出计算总时间时包含 `iowait` 和 `softirq`。

这属于现有内部实现的语义差异，不应把 `getTotalCpuPercent()` 抄成通用 CPU 公式。使用内部数据时，应直接选取需要的增量字段并在指标协议中记录公式。

### Framework 为什么能用，应用为什么不能照搬

Android 17 的 `AppProfiler` 在 `system_server` 内持有一个 `ProcessCpuTracker`，源码注释明确说明它会遍历 `/proc`，并要求调用方避免在关键锁路径上持有其锁。采样结果用于 ANR 等诊断输出、进程 CPU 统计和 BatteryStats 归因，也用于 phantom process 的 CPU 状态更新。

对应调用链可在 [`AppProfiler.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppProfiler.java) 中核对。

普通应用同时受两层约束：

- 类本身是隐藏 API，反射调用没有兼容性保证；
- 即使设法调用成功，SELinux 与 procfs 挂载权限也不会随反射绕过。

所以第三方 APM 应使用公开 API 采集自身进程 CPU，并把系统级诊断交给 Perfetto、bugreport 或受控的平台服务。

## `/proc/loadavg` 回答的不是 CPU 利用率

Android 17 内核将 load average 定义为 `nr_running + nr_uninterruptible` 的指数衰减平均值，三个窗口通常称为 1、5、15 分钟负载。它同时包含可运行任务和不可中断睡眠任务，因此高负载既可能来自 CPU 竞争，也可能来自 D 状态任务。

下面的示例只用于说明文件布局：

```text
1.23 1.45 1.67 3/1024 12345
```

前三个值是三个时间尺度的负载平均值；`3/1024` 是读取时刻的 runnable 线程数与系统线程总数；末尾值来自当前 PID 命名空间最近分配位置。第四列不是“运行进程数/总进程数”，也不应假定只统计进程主线程。

不要为所有设备设定固定的 load average 告警线。Android 设备存在 CPU 热插拔、大小核、cpuset 和功耗策略，同一个数值在不同设备和温控状态下含义不同。更稳妥的做法是：

- 与同机型、同场景的历史基线比较；
- 同时查看系统 CPU busy、`procs_running`、`procs_blocked` 与 PSI；
- 用调度 trace 区分运行队列等待、锁等待和不可中断 I/O；
- 把温控、频率和在线 CPU 集合作为解释上下文。

生成第四列的代码位于 [`fs/proc/loadavg.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/loadavg.c)，负载平均算法位于 [`kernel/sched/loadavg.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/loadavg.c)。普通应用在 AOSP Android 17 上不能读取该节点。

## 采样器的工程约束

采样间隔没有脱离产品场景的固定答案。短间隔能看见更短的尖峰，也会增加唤醒、文件解析、线程枚举和上报成本。设计时应明确：

- 常态只采当前进程的累计 CPU 时间，异常窗口再临时增加线程维度；
- 不在主线程读取 procfs，避免磁盘读取策略告警和业务抖动；
- 使用单调时钟，不用 `currentTimeMillis()` 计算采样间隔；
- 记录原始累计值、差值、时间分母和指标口径，服务端不要凭字段名猜公式；
- 对读取失败、差值为负、时间不前进、`starttime` 变化分别计数；
- 通过设备实验测量采集线程 CPU、唤醒次数、分配量与包体影响，再决定频率；
- 后台和温控状态下允许降频或停止，异常触发的高频模式应有持续时间限制。

`ProcessCpuTracker` 自身也说明了全 PID 扫描属于长操作。它缓存已有 `Stats` 和进程名，按 PID 合并新增、存续、退出记录，但并没有消除每轮 `/proc` 枚举。

## Perfetto 与 eBPF：何时换成事件数据

### CPU 调度分析用 `linux.ftrace`

Perfetto 的 `linux.process_stats` 主要提供进程/线程身份关系和按周期采集的内存、`oom_score_adj` 等数据，不是进程 CPU 时间采样器。线程何时运行、运行多久、为何被换下 CPU，应由 `linux.ftrace` 的 `sched_switch` 提供；`sched_waking` 可补充唤醒与调度延迟。

下面的配置展示两类数据源如何配合，目的是让调度事件具有完整的进程和线程名称：

```textproto
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}
```

`linux.ftrace` 给出 CPU 时间轴，`linux.process_stats` 补充名称和线程归属。若要周期采集进程内存，再显式配置 `proc_stats_poll_ms`；它不应被描述成 CPU 采样频率。可继续阅读 Perfetto 的 [CPU Scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling) 与 [Memory counters and events](https://perfetto.dev/docs/data-sources/memory-counters)。

### eBPF 不是普通应用的直接替代

平台团队可以在 `sched_switch` 等事件上运行 BPF 程序，把时间归因到 UID、PID 或 TID，并通过 map 输出聚合结果。但这条路线有三个前提：

- Android 需要由受信任的 loader、固定对象和 SELinux 规则管理 BPF 能力，普通应用不能只靠声明权限获得访问；
- BPF 程序在每次调度切换时执行，事件驱动不等于开销必然低于周期采样；
- 读取并清空同一张 map 会与内核侧更新竞争，需要按 CPU 聚合、双缓冲或带世代的协议，不能把一次 `BPF_MAP_LOOKUP_AND_DELETE_ELEM` 调用当成无损快照。

`BPF_MAP_LOOKUP_AND_DELETE_ELEM` 是 `bpf()` 系统调用的操作命令，不是 map 类型。Android 的 loader、对象编译与固定规则可参考 AOSP 的 [Extend the kernel with eBPF](https://source.android.com/docs/core/architecture/kernel/bpf)。对于普通应用性能诊断，Perfetto 已经提供受平台管理的调度数据通路；只有设备厂商或系统组件需要长期、定制化聚合时，才有理由维护专用 BPF 方案。

## 排查顺序

遇到 CPU 告警时，可以按问题粒度选择数据：

1. 用 `Process.getElapsedCpuTime()` 判断当前进程是否持续消耗核等价 CPU。
2. 对短时异常读取自身线程 stat，确认 CPU 时间集中在哪些线程。
3. 若线程 CPU 不高但用户仍感到卡顿，转向 Perfetto 检查 runnable 等待、锁、Binder、I/O 与调度抢占。
4. 只有具备平台权限并且问题涉及全机竞争时，才读取 `/proc/stat`、load average 或使用 `ProcessCpuTracker`。
5. 需要长期系统级归因时，再评估平台服务或 BPF 聚合，并单独验证开销与权限模型。

这套顺序让每种数据回答它擅长的问题，也避免普通应用依赖 Android 17 已经关闭的全局 procfs 接口。
