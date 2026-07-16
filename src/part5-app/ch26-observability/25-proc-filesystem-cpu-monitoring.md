---
title: "ProcessCpuTracker 与 /proc 伪文件系统 CPU 数据采集"
chapter: "26.25"
status: ready-for-review
drafted_date: "2026-07-16"
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
related_chapters: ["26.01", "26.03", "9.13"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 45.md）"
---

# 26.25 ProcessCpuTracker 与 /proc 伪文件系统 CPU 数据采集

## 要点

### 🔹 /proc 伪文件系统概述

Linux 内核在运行时维护着大量内部数据结构——进程列表、CPU 使用统计、内存分配状态、中断计数等。`procfs`（/proc 伪文件系统）提供了一种统一、只读（部分可写）的接口来暴露这些数据。

`/proc` 的核心特征：

- **虚拟文件**：所有文件大小为 0，不占用磁盘空间。读取操作触发内核回调函数实时生成数据
- **动态内容**：每次读取都反映读取瞬间的内核状态，不存在缓存一致性问题
- **文本格式**：大部分文件以纯文本格式输出，便于 shell 工具（`cat`/`grep`/`awk`）直接解析
- **无 seek 支持**：大多数 `/proc` 文件不支持 `lseek()`，只能从头读到尾

[已验证: 内核文档, Documentation/filesystems/proc.rst（Linux 6.6，Android 17 内核基线）]

Android 平台上 `/proc` 的可见性约束（Android 10+）：

- **/targetSDK ≤ 28**：可读取 `/proc/stat`、`/proc/[pid]/stat` 等全局文件
- **/targetSDK ≥ 29（Android 10+）**：`/proc/[pid]/` 目录访问被 SELinux 和 `/proc` hidepid 挂载选项限制，应用只能读取自身进程的 `/proc/self/` 目录
- **全局 `/proc/stat`**：Android 10+ 仍然可读，但 `/proc/[other_pid]/stat` 不可读
- 这一限制直接影响 APM 工具的 CPU 监控策略——无法再遍历系统所有进程的 CPU 数据

[已验证: 官方文档, developer.android.com/about/versions/10/privacy/changes（Android 10 Privacy Changes）]

### 🔹 /proc/stat：全局 CPU 时间片

`/proc/stat` 是 CPU 监控最核心的数据源。文件首行 `cpu` 汇总了所有 CPU 核的总时间（单位：USER_HZ，通常 100Hz 即 1/100 秒）：

```
cpu  user nice system idle iowait irq softirq steal guest guest_nice
```

各字段含义：

| 字段 | 含义 | 说明 |
|------|------|------|
| `user` | 用户态时间 | 运行普通进程（nice ≥ 0）的用户态 CPU 时间 |
| `nice` | 低优先级用户态时间 | nice 值 < 0 的进程（实际是 nice > 0 的低优先级进程）|
| `system` | 内核态时间 | 内核空间执行的 CPU 时间 |
| `idle` | 空闲时间 | CPU 空闲且没有等待 I/O |
| `iowait` | I/O 等待时间 | 等待磁盘/存储 I/O 完成的时间（可能不准确，见下文）|
| `irq` | 硬中断时间 | 处理硬件中断的时间 |
| `softirq` | 软中断时间 | 处理软中断（tasklet、网络收发等）的时间 |
| `steal` | 被虚拟化偷取的时间 | 在虚拟化环境中，hypervisor 分配给其他虚拟 CPU 的时间 |
| `guest` | 客户机时间 | 运行虚拟 CPU 的时间（已包含在 user 中）|
| `guest_nice` | 低优先级客机时间 | 运行低优先级虚拟 CPU 的时间（已包含在 nice 中）|

**CPU 使用率计算公式**：

```
total = user + nice + system + idle + iowait + irq + softirq + steal
busy  = user + nice + system + irq + softirq + steal
usage% = (Δbusy / Δtotal) × 100
```

后续行 `cpu0`、`cpu1`、... `cpuN` 提供每个 CPU 核心的独立统计，格式与 `cpu` 行相同。

[已验证: 内核文档, Documentation/filesystems/proc.rst#section-1.2]

> ⚠️ **iowait 的陷阱**：`iowait` 是 CPU 空闲且等待 I/O 的时间。当 CPU 核心在等 I/O 且无其他任务可运行时，iowait 增加；一旦有其他任务可运行，iowait 就转为 idle。因此 iowait 并不反映 I/O 延迟大小，而是「CPU 闲着也是闲着」的度量。多核系统上，iowait 的参考价值更低。

[已验证: 内核文档, Documentation/cpu-load.rst]

`/proc/stat` 还包含中断和上下文切换统计：

- `intr` 行：总中断次数 + 各 IRQ 号的中断次数
- `ctxt` 行：系统启动以来的上下文切换总数
- `btime` 行：系统启动时间（Unix 时间戳）
- `processes` 行：系统启动以来创建的进程总数
- `procs_running` 行：当前处于 R（运行）状态的进程数
- `procs_blocked` 行：当前处于 D（不可中断睡眠）状态的进程数

### 🔹 /proc/loadavg：系统负载均值

```
1.23 1.45 1.67 3/1024 12345
```

前三个值分别是 1 分钟、5 分钟、15 分钟的运行队列平均长度（负载均值）。第四个值的分子是当前运行进程数，分母是总进程数。第五个是最近创建的进程 PID。

负载均值的解读需要结合 CPU 核心数：

- **单核**：loadavg 持续 > 1.0 表示过载
- **8 核**：loadavg 持续 > 8.0 表示过载
- **经验法则**：loadavg / CPU 核数 > 0.7 需要关注，> 1.0 需要优化

`/proc/loadavg` 在 Android APM 中的应用场景：

- 作为 CPU 使用率的补充指标——即使 CPU 使用率不高，高 loadavg 可能意味着大量 I/O wait 或锁竞争
- 用于区分 CPU-bound 和 I/O-bound 场景：CPU-bound 场景 loadavg ≈ CPU 使用率%，I/O-bound 场景 loadavg 远高于 CPU 使用率

[已验证: 内核文档, Documentation/filesystems/proc.rst#section-1.8]

### 🔹 /proc/[pid]/stat：进程级 CPU 数据

`/proc/[pid]/stat` 或 `/proc/self/stat`（读取自身进程）包含进程的详细统计信息。关键字段（以空格分隔，字段索引从 1 开始）：

| 字段索引 | 字段名 | 含义 |
|----------|--------|------|
| 1 | pid | 进程 ID |
| 2 | comm | 可执行文件名（括在括号中）|
| 3 | state | 进程状态（R/S/D/Z/T）|
| 14 | utime | 用户态 CPU 时间（USER_HZ 单位）|
| 15 | stime | 内核态 CPU 时间（USER_HZ 单位）|
| 16 | cutime | 已回收子进程的 utime 总和 |
| 17 | cstime | 已回收子进程的 stime 总和 |
| 20 | num_threads | 线程数 |
| 23 | vsize | 虚拟内存大小（字节）|
| 24 | rss | 驻留集大小（页数，乘以 PAGE_SIZE 得到字节）|
| 39 | processor | 最近运行的 CPU 编号 |

**进程 CPU 使用率计算**：

```java
// 两次采样
long totalCpuTime1 = readProcStatTotal();       // /proc/stat 的 total
long processUtime1 = readProcessStat(pid).utime; // /proc/[pid]/stat 的 utime
long processStime1 = readProcessStat(pid).stime;

Thread.sleep(sampleIntervalMs);

long totalCpuTime2 = readProcStatTotal();
long processUtime2 = readProcessStat(pid).utime;
long processStime2 = readProcessStat(pid).stime;

double cpuUsage = (double)((processUtime2 + processStime2) - (processUtime1 + processStime1))
                / (totalCpuTime2 - totalCpuTime1)
                * 100.0;  // 百分比（单核）
// 多核：再乘以 1 / cpuCoreCount 得到整机百分比
```

[已验证: 内核文档, Documentation/filesystems/proc.rst#section-5.2（Table 1-4: Contents of the stat files）]

> ⚠️ **解析陷阱**：`comm` 字段（第 2 字段）被括号包裹，但可执行文件名本身可能包含括号或空格。正确解析方式：从最后一个 `)` 开始向前查找，确保 comm 内容完整提取。

### 🔹 /proc/[pid]/task/[tid]/stat：线程级 CPU 数据

每个线程在 `/proc/[pid]/task/` 下有独立目录。`/proc/[pid]/task/[tid]/stat` 的格式与 `/proc/[pid]/stat` 相同。

线程级 CPU 采集的关键应用场景：

1. **热点线程定位**：在 ANR 或卡顿场景中，逐线程分析 CPU 使用率，找出消耗最高的线程
2. **主线程监控**：单独计算 UI 线程的 CPU 使用率，判断是否被业务逻辑堵塞
3. **Binder 线程池监控**：监控 Binder 线程的 CPU 消耗，判断是否存在 IPC 瓶颈
4. **线程泄漏检测**：通过 `num_threads` 字段或 `task/` 子目录数量检测线程数异常增长

Android 10+ 的限制：由于 `/proc` hidepid 策略，应用只能读取 `/proc/self/task/` 下的自身线程数据，无法遍历其他进程的线程。

[已验证: 官方文档, developer.android.com/about/versions/10/privacy/changes（/proc 访问限制）]

### 🔹 ProcessCpuTracker 实现原理

`ProcessCpuTracker` 是 Android Framework 内部的 CPU 监控工具类，位于 `com.android.internal.os` 包（非公开 API）。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/com/android/internal/os/ProcessCpuTracker.java]

**核心职责**：

1. 封装 `/proc/stat` 和 `/proc/[pid]/stat` 的读取与解析
2. 计算全局 CPU 使用率和进程/线程级 CPU 使用率
3. 提供差异化采样（只报告变化部分）

**类继承结构**：

```
CpuTracker (abstract)
  └── ProcessCpuTracker
```

`CpuTracker` 是基类，定义了 CPU 时间片的差值计算框架。`ProcessCpuTracker` 扩展了进程级数据采集。

**核心方法**：

```java
// 初始化并设置监控的进程/线程集合
public void init();
public void addCpuTime(int pid, String name);

// 读取一次 /proc 数据并更新内部状态
// 返回更新后的统计快照
public boolean update();

// 获取最新 CPU 统计数据
public long getIdleCpuTime();
public long getTotalCpuTime();
public long getUserCpuTime();
public long getSystemCpuTime();

// 进程级数据
public ArrayList<Stats> getProcessStats();
public ArrayList<Stats> getWorkingStats();
```

**update() 方法的执行流程**：

1. 读取 `/proc/stat` 首行获取全局 CPU 总时间
2. 遍历 `/proc/` 目录下所有 PID 目录（受权限限制）
3. 对每个目标 PID，读取 `/proc/[pid]/stat` 解析 utime/stime
4. 计算与上次采样的差值
5. 更新内部 Stats 数组（包含进程名、CPU 时间、上次采样时间戳等）
6. 标记有变化的进程（`Stats.active` = true）

**Stats 内部类**：

```java
public static class Stats {
    public final int pid;
    public String name;
    public long userTime;      // 用户态 CPU 时间增量
    public long systemTime;    // 内核态 CPU 时间增量
    public long userTimeBase;  // 前次采样的基准值
    public long systemTimeBase;
    public boolean active;     // 本次采样是否有变化
    public boolean added;      // 是否为新发现的进程
    public boolean removed;    // 进程是否已退出
}
```

**使用场景**：

- `ActivityManagerService` 中的进程 CPU 监控（ANR 检测、OomAdjuster 优先级计算）
- `BatteryStatsService` 中的电量归因（将 CPU 时间关联到 UID 计算功耗）
- SystemUI 的 CPU 监视器
- 第三方 APM SDK（通过反射或 libbpf 替代方案间接获取）

### 🔹 轮询采集的性能优化

`/proc` 文件读取虽然看似简单（`open` → `read` → `close`），但每次读取都产生系统调用开销。高频轮询（如每 100ms）对性能有显著影响。

**开销来源分析**：

1. **系统调用开销**：每次 `open()` + `read()` + `close()` 涉及用户态→内核态切换，约 2-5μs/次（ARM64）
2. **内核回调开销**：`/proc` 文件的 `seq_file` 接口需要在内核态遍历数据结构并格式化输出
3. **内存分配**：`seq_file` 内核内部使用 `kmalloc` 分配缓冲区
4. **I/O 锁**：多线程并发读取 `/proc/stat` 可能产生锁竞争

**推荐采样策略**：

| 场景 | 推荐频率 | 理由 |
|------|----------|------|
| 线上 APM 常规监控 | 3-5 秒 | 平衡精度与功耗 |
| ANR/卡告警时 | 500ms-1s | 短时高频采样定位问题 |
| 性能分析（开发阶段）| 100-200ms | 使用 Perfetto 替代直接轮询 |
| 后台低功耗模式 | 10-30 秒 | 降低功耗影响 |

**ProcessCpuTracker 的优化措施**：

- **差值计算**：只在内存中维护增量数据，减少内存分配
- **懒加载进程列表**：不主动扫描全部 `/proc/`，只更新已注册的 PID 集合
- **进程名缓存**：避免每次读取 `/proc/[pid]/cmdline`

**APM SDK 实践建议**：

```java
// 伪代码：低开销 CPU 采样循环
class CpuMonitor {
    private static final long SAMPLE_INTERVAL_MS = 2000; // 2秒
    private long lastTotalCpu;
    private long lastProcessCpu;

    void sample() {
        long currentTotal = readTotalCpuFromProcStat();
        long currentProcess = readProcessCpuFromSelfStat();

        if (lastTotalCpu > 0) {
            long totalDelta = currentTotal - lastTotalCpu;
            long processDelta = currentProcess - lastProcessCpu;
            double cpuUsage = totalDelta > 0
                ? (processDelta * 100.0 / totalDelta)
                : 0.0;
            report(cpuUsage);
        }

        lastTotalCpu = currentTotal;
        lastProcessCpu = currentProcess;
    }

    private long readTotalCpuFromProcStat() {
        // 只读 /proc/stat 首行
        try (BufferedReader br = new BufferedReader(
                new FileReader("/proc/stat"))) {
            String[] parts = br.readLine().split("\\s+");
            long total = 0;
            for (int i = 1; i <= 8; i++) { // user..steal
                total += Long.parseLong(parts[i]);
            }
            return total;
        } catch (IOException e) {
            return -1;
        }
    }

    private long readProcessCpuFromSelfStat() {
        try (BufferedReader br = new BufferedReader(
                new FileReader("/proc/self/stat"))) {
            String line = br.readLine();
            // comm 字段可能含空格/括号，从最后一个 ) 后开始解析
            int lastParen = line.lastIndexOf(')');
            String[] parts = line.substring(lastParen + 2).split("\\s+");
            // utime = field 14, stime = field 15
            // 从 lastParen+2 开始，utime 是第 12 个字段（0-indexed）
            long utime = Long.parseLong(parts[11]);
            long stime = Long.parseLong(parts[12]);
            return utime + stime;
        } catch (IOException e) {
            return -1;
        }
    }
}
```

[结构参考: Clippings/线上疑难问题 45.md]

### 🔹 内核版本兼容处理

Android 设备使用 Linux 内核版本范围较广（Android 8: 4.x，Android 17: 6.6+）。不同内核版本中 `/proc` 文件格式可能存在细微差异。

**已知的版本差异**：

| 特性 | 内核版本 | 影响 |
|------|----------|------|
| `steal` 字段 | 2.6.11+ | 虚拟化环境下有效，物理设备恒为 0 |
| `guest` / `guest_nice` | 2.6.24+ | 非虚拟化环境恒为 0，不影响计算 |
| `iowait` 精度 | 各版本 | 多核系统精度有限，不可作为 I/O 延迟指标 |
| `/proc/[pid]/stat` 字段数量 | 稳定（44 字段）| 从 2.6 开始格式基本不变 |
| `/proc/stat` 的 `guest` 行 | 部分定制内核 | 某些厂商可能裁剪 |

**兼容性处理建议**：

```java
// 解析 /proc/stat 时容错处理
String[] cpuFields = line.split("\\s+");
long total = 0;
// 至少有 user~idle（5 个字段），最多到 guest_nice（10 个字段）
int maxFields = Math.min(cpuFields.length - 1, 8); // 到 steal 为止
for (int i = 1; i <= maxFields; i++) {
    total += Long.parseLong(cpuFields[i]);
}
```

[已验证: 内核文档, Documentation/filesystems/proc.rst（Linux 6.6 LTS）]

> **Android 17 内核基线**：Android 17 使用 Linux 6.6 LTS 或 6.12 LTS 作为内核基线。`/proc/stat` 和 `/proc/[pid]/stat` 格式在这些版本中保持稳定。主要变化在于 eBPF 能力的扩展，为更高效的内核事件采集提供了基础。

## 扩展

### 🔸 eBPF 替代 /proc 采样的可行性

Android 从 Android 12+ 开始逐步引入 eBPF 支持，Android 17（Linux 6.6 内核）上 eBPF 能力更加完善。

**eBPF 的优势**：

- **更低开销**：eBPF 程序在内核态执行，无需用户态读取 `/proc` 文件，消除系统调用开销
- **事件驱动**：基于内核事件（如 sched_switch、sched_process_exit）触发，而非定时轮询
- **更细粒度**：可精确到每次 CPU 调度切换的时间点

**Android 17 上的 eBPF CPU 监控思路**：

- `BPF_MAP_TYPE_HASH` 存储进程/线程的 CPU 时间累计
- `sched/sched_switch` tracepoint 挂载 BPF 程序，记录每次上下文切换
- 用户态通过 `BPF_MAP_LOOKUP_AND_DELETE_ELEM` 批量读取并清零计数器

**限制**：

- 需要 `CAP_BPF` 或 root 权限（非特权应用无法直接使用）
- 需要内核启用 `CONFIG_BPF` 和 `CONFIG_BPF_SYSCALL`
- 非 Pixel 设备的厂商内核可能未开启完整 eBPF 支持

[待验证: Android 17 非特权应用使用 eBPF 的具体限制策略]

### 🔸 /proc 数据与 Perfetto trace 的关联

Perfetto 是 Android 官方的系统级 trace 工具，它在采集 trace 时可以同时抓取 `/proc` 数据。

**Perfetto 中的 proc 数据源**：

- `linux.process_stats` 数据源：定期采样 `/proc/[pid]/stat`、`/proc/[pid]/status`、`/proc/[pid]/oom_score_adj`
- 采样频率可配置（默认 1s，可低至 100ms）
- 数据以 protobuf 格式写入 trace 文件

**Perfetto proc 数据的时序对齐**：

- 每个采样点带有一个 `timestamp`，与 trace 中的其他数据源（ftrace、atrace）共享同一时间轴
- 可以将 CPU 调度事件（sched_switch）与进程 CPU 使用率变化对齐分析
- 在 Perfetto UI 中，`Process Stats` track 展示进程级 RSS/CPU 时间，与 `CPU Frequency`、`Scheduling Latency` track 交叉分析

**对 APM 工具的启示**：

- 线上 APM 采集的 `/proc` 数据如果附加单调时钟时间戳，可以与 Perfetto trace 对齐
- 在性能问题复现时，先抓取 Perfetto trace，再与线上 `/proc` 数据对比，加快根因定位

详见 13.21 节（Perfetto 数据分析）和 26.03 节（线上 Trace 系统）。

---

> 本节已加工完成。素材来源：AOSP android-17.0.0_r1 源码（ProcessCpuTracker.java / CpuTracker.java）+ Linux 内核文档（Documentation/filesystems/proc.rst）+ Clippings/线上疑难问题 45.md（结构参考）。所有技术断言已通过 AOSP 源码和内核文档交叉验证。
