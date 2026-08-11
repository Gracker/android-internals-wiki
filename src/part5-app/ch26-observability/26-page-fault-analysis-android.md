---
title: "Page Fault 类型分析与 Android 实践"
chapter: "26.26"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
drafted_date: "2026-07-16"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
tags: [page-fault, minor-fault, major-fault, mmap, memory, observability]
related_chapters: ["26.25", "4.01", "9.3"]
sources:
  - type: aosp
    path: "frameworks/base/core/jni/android_os_Debug.cpp"
  - type: official
    path: "developer.android.com/topic/performance/memory"
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "参考书驱动（Clippings/线上疑难问题 46.md）"
---

# 26.26 Page Fault 类型分析与 Android 实践

## 读数前先分清三类指标

Page Fault（缺页异常）是 CPU 在地址转换或权限检查时发现当前页表状态无法完成访问后，交给内核处理的同步异常。内核可能补齐映射并返回用户态，也可能把访问转成信号。排查时应区分下面三类指标：

| 指标或结果 | Android 17 / Linux 6.18 中的含义 | 常见原因 |
|---|---|---|
| Minor Fault | 内核成功完成 fault，且最终没有 `VM_FAULT_MAJOR`，处理过程也没有重试 | 匿名页按需分配、COW、页缓存已有数据但进程 PTE 尚未建立 |
| Major Fault | 内核成功完成 fault，最终返回 `VM_FAULT_MAJOR`，或处理过程发生过重试 | 文件页需要读入、交换页需要从 zRAM 或其 backing storage 取回 |
| 失败访问 | 内核不能为该访问建立合法映射，通常向线程发送 SIGSEGV 或 SIGBUS | 地址未映射、权限不符、文件映射越过 EOF、硬件内存错误 |

“Invalid Page Fault”适合描述失败结果，不是 `/proc/<pid>/stat` 中与 minor、major 并列的第三个计数器。这个区别会直接影响指标解读：`min_flt + maj_flt` 只覆盖成功完成的 fault，不能代替 native crash 统计。

另一个容易混淆的概念是 TLB miss。若 PTE 有效，只是地址转换不在 TLB 中，硬件执行 page-table walk 后即可继续访问；这种情况通常不会进入内核 Page Fault Handler。TLB refill 事件与 Page Fault 应分别分析。

## Android 17 arm64 的处理路径

平台源码锚点是 `android-17.0.0_r1`，内核锚点是 `android17-6.18-2026-06_r6`。arm64 的入口在 [`arch/arm64/mm/fault.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/mm/fault.c)，通用内存管理在 [`mm/memory.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/memory.c)。

下面的调用关系用于定位源码职责，不表示每次 fault 都会经过所有分支。

```text
do_mem_abort()
  └─ fault_info[] 按 ESR 分发
      ├─ do_translation_fault() ── 用户地址 ─┐
      └─ do_page_fault()                     │
                                             ▼
             校验访问类型、VMA 与权限
                       │
                       ▼
               handle_mm_fault()
                       │
                       ▼
              __handle_mm_fault()
                 ├─ do_anonymous_page()
                 ├─ do_wp_page()
                 ├─ do_fault()
                 └─ do_swap_page()
```

`do_page_fault()` 根据 ESR 判断读、写或执行访问，尝试用 per-VMA lock 查找 VMA，必要时退回 `mmap_lock` 路径。VMA 存在且权限匹配后，`handle_mm_fault()` 才进入匿名页、COW、文件页或 swap 等通用处理。失败结果回到 arm64 代码后，再按错误类型发送信号。

这里有三处计数时机需要单独记住：

- arm64 在校验 VMA 之前调用 `perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, ...)`。Simpleperf 的 `page-faults` 因此更接近进入架构 fault 入口的次数，也会包含随后失败的访问。
- `handle_mm_fault()` 结束时调用 `mm_account_fault()`。`PGFAULT` VM 计数包含进入该函数后成功和失败的结果，但在 VMA 查找或权限检查阶段提前失败的访问不会到达这里。
- `mm_account_fault()` 遇到 `VM_FAULT_ERROR` 不更新 `current->min_flt`、`current->maj_flt` 以及对应 perf minor/major 事件。成功结果带 `VM_FAULT_MAJOR` 或发生过 retry 时记作 major，其余记作 minor。

因此，`page-faults` 不保证等于 `minor-faults + major-faults`。看到差值时，要考虑失败访问、采样边界和工具权限，不能直接归因于统计错误。

## Minor Fault：能在内存中完成的映射修复

Minor Fault 的共同特征是处理过程不需要为目标页执行存储读取。常见来源包括：

- **匿名页按需分配**：`mmap(MAP_ANONYMOUS)` 或堆扩展先建立 VMA，线程第一次触碰页面时再建立物理页和 PTE。读取可能映射共享零页，后续写入再分配私有页。
- **Copy-on-Write**：Zygote fork 出应用进程后，父子进程可共享只读页。任一进程写入共享页时，`do_wp_page()` 为写入方准备私有副本。
- **文件页已在 page cache 中**：目标文件数据已由本进程或其他进程读入内存，但当前进程还没有对应 PTE。内核可以从 page cache 建立映射，无需再次读取存储。

Minor 只说明“成功处理且未归为 major”，不等于“页原本已经映射”，也不等于“发生了一次内存分配”。一次 fault 可能涉及页表页分配、folio 处理、memcg 计费、反向映射和锁竞争，其耗时受内存压力、页大小、folio 大小与并发状态影响。没有跨设备适用的固定微秒阈值。

`malloc()` 是否转向 `mmap()` 由分配器实现、进程状态和版本共同决定。某个固定字节阈值不能用来解释 COW，也不应写进通用的 Page Fault 判断规则。

## Major Fault：处理过程需要读取或等待

Linux 6.18 在 [`include/linux/mm_types.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/mm_types.h) 中把 `VM_FAULT_MAJOR` 注释为 “Page read from storage”。`do_swap_page()` 在需要从 swap area 读取页面时设置该标志；文件映射的 fault handler 也会在需要页面读入时返回 major。

Android 上常见的来源有：

- 冷启动访问尚未进入 page cache 的 APK、DEX、OAT/VDEX、共享库或资源文件页面；
- 后台进程的匿名页被换出，进程恢复后从 zRAM 读取并解压；
- 设备启用 zRAM writeback 后，交换页已写入 backing storage，恢复访问需要从闪存取回；
- fault handler 等待页面 I/O 或发生 retry，最终按 major 计数。

Major Fault 表明这次映射修复涉及页面读入或等待，是调查 I/O 的有效线索，但不能单独证明存储已经成为用户可见瓶颈。一次 fault 可能触发 readahead，一次 I/O 也可能满足多个后续 fault；folio 大小、页缓存命中和 I/O 合并都会改变“fault 次数”与“读取字节数”的关系。设备的 UFS、调度器、文件系统和当前负载还会改变时延。

### Android 17 的 zRAM 与 MMD

zRAM 在 Linux 中注册为压缩 RAM-backed block device，可以作为 swap 设备使用。“Android 没有 swap，所以 swap-in 不会产生 major fault”和“zRAM 不是块设备”都不成立。

Android 17 引入的 [Memory Management Daemon（MMD）](https://source.android.com/docs/core/perf/mmd) 负责 zRAM 配置及维护，并支持 recompression、全局 writeback、按进程 writeback 与 prefetch。启用 writeback 后，冷页可以进入 `/data` 上的 backing storage。应用从冻结状态恢复时，系统还能按进程预取交换页，减少 backing storage 所致 major fault 对启动时延的影响。

这些能力和参数由设备配置决定。zRAM 大小、压缩算法、writeback 开关及 backing device 均不能用一个平台固定值代替，分析设备时应读取实际配置与内核统计。

## 失败访问与 native crash

arm64 找不到目标 VMA 时通常发送 `SIGSEGV`，`si_code` 为 `SEGV_MAPERR`；VMA 存在但访问权限不符时通常是 `SIGSEGV/SEGV_ACCERR`。文件映射越过可用文件内容等 `VM_FAULT_SIGBUS` 路径会得到 `SIGBUS/BUS_ADRERR`。硬件内存错误还可能产生 `BUS_MCEERR_*`，MTE tag check fault 则有对应的 SIGSEGV `si_code`。

几个工程细节值得留意：

- use-after-free 不保证立即 crash。被释放地址可能仍在 VMA 内，甚至已被分配器复用，此时访问在页表层面仍然合法。
- 栈向可增长区域扩展时，内核可能补充映射；超过 guard 或资源限制后才会转成失败。
- 只看 `signal 11` 不足以判断原因。tombstone 中的 signal、`si_code`、fault address、寄存器和映射表需要一起分析。

这类失败不应混入性能侧的 `min_flt`/`maj_flt` 趋势。它们属于 native 稳定性调查，相关方法见第 20 章。

## `/proc/<pid>/stat` 计数的精确语义

字段顺序由内核 [`fs/proc/array.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c) 输出。下面的布局用于检查解析器索引。

```text
字段 10  minflt   当前任务或线程组的 minor fault
字段 11  cminflt  已回收子进程的 minor fault
字段 12  majflt   当前任务或线程组的 major fault
字段 13  cmajflt  已回收子进程的 major fault
字段 22  starttime  任务自系统启动后的创建时刻，单位为 clock tick
```

读取 `/proc/<pid>/stat` 时，`minflt` 和 `majflt` 是整个线程组的聚合值；读取 `/proc/<pid>/task/<tid>/stat` 时，得到指定线程的值。`cminflt`、`cmajflt` 统计已等待子进程的 fault，不是当前进程中其他线程的计数。

Android 17 的 [`ProcessCpuTracker`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java) 读取字段 10 和 12，保存 `base_minfaults`、`base_majfaults`，下一次采样计算 `rel_minfaults`、`rel_majfaults`。这也是系统 CPU dump 中 fault 增量的来源。

### 应用内安全解析自身计数

`comm` 字段被圆括号包围，进程名本身可以包含空格和右括号。直接按空格切整行会错位。下面的示例从末尾的 `)` 后解析字段，并用 `starttime` 防止 PID 复用或进程重启造成负增量。

```kotlin
import android.os.SystemClock
import java.io.File

data class FaultSnapshot(
    val startTimeTicks: Long,
    val minor: Long,
    val major: Long,
    val elapsedRealtimeNanos: Long,
)

data class FaultDelta(
    val minor: Long,
    val major: Long,
    val durationNanos: Long,
)

fun readSelfFaults(): FaultSnapshot {
    val line = File("/proc/self/stat").readText().trim()
    val commEnd = line.lastIndexOf(')')
    require(commEnd >= 0 && commEnd + 2 < line.length) {
        "Malformed /proc/self/stat"
    }

    // fields[0] 对应内核文档中的字段 3（state）。
    val fields = line
        .substring(commEnd + 2)
        .trim()
        .split(Regex("\\s+"))
    require(fields.size > 19) { "Incomplete /proc/self/stat" }

    return FaultSnapshot(
        startTimeTicks = fields[19].toLong(), // 字段 22
        minor = fields[7].toLong(),           // 字段 10
        major = fields[9].toLong(),           // 字段 12
        elapsedRealtimeNanos = SystemClock.elapsedRealtimeNanos(),
    )
}

fun delta(
    previous: FaultSnapshot,
    current: FaultSnapshot,
): FaultDelta? {
    if (current.startTimeTicks != previous.startTimeTicks) return null
    if (current.minor < previous.minor || current.major < previous.major) return null
    if (current.elapsedRealtimeNanos <= previous.elapsedRealtimeNanos) return null

    return FaultDelta(
        minor = current.minor - previous.minor,
        major = current.major - previous.major,
        durationNanos = current.elapsedRealtimeNanos - previous.elapsedRealtimeNanos,
    )
}
```

这个解析器只读取当前应用自己的 proc 节点。把采样放到低频诊断窗口，避免文件读取反过来干扰短场景；进程或线程退出、读取失败以及计数回退都应作为样本失效处理。

### 为什么不能用 fault 数估算分配字节

`Δfaults × 4 KB` 不能表示这段时间的内存分配量，原因包括：

- Android 15 及更高版本支持 16 KB page-size 设备；Android 17 设备可能使用 4 KB 或 16 KB 页，页大小要在运行时查询；
- minor fault 还包含 COW 和文件 page-cache 映射，同一虚拟区域在回收后也可能再次 fault；
- 分配器可以复用已经驻留的堆页，发生分配却没有新增 fault；
- readahead 和大 folio 使一次 major fault 与一个基础页的 I/O 不再一一对应。

Java/Kotlin 可按 [AOSP 页大小指南](https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size) 调用 `Os.sysconf(OsConstants._SC_PAGE_SIZE)`，native 代码使用 `getpagesize()`。页大小只适合换算明确以 page 为单位的内核字段；对象或 native allocation 应使用 Heap Profile、heapprofd、JVMTI allocation sampling 或相应分配器工具。

## 诊断流程：计数、时间线、映射对象

Page Fault 调查需要回答三个问题：哪个阶段增长、增长的是 minor 还是 major、当时访问了什么映射对象。

### 用 Simpleperf 区分事件

Android 17 Simpleperf 的生成器在 [`event_table_generator.py`](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table_generator.py) 中注册 `page-faults`、`minor-faults` 和 `major-faults` 三个软件事件。下面的命令先确认目标设备支持事件，再对指定应用采样。

```shell
adb shell simpleperf list
adb shell simpleperf stat \
  --app com.example.app \
  -e page-faults,minor-faults,major-faults \
  --duration 10
```

`simpleperf list` 的结果应作为能力判断。应用必须满足设备上 simpleperf 的 profiling 权限要求；user build、debuggable/profileable 状态和厂商策略都会影响可用范围。采样报告中 `page-faults` 与 minor、major 之和的差值也应按前文计数时机解释。

### 用 Perfetto 解释卡在哪里

Perfetto 适合把 fault 增长与启动阶段、调度、文件 I/O、内存回收和 block I/O 放在同一时间线上。arm64 设备不保证提供 `exceptions/page_fault_user`；把该 tracepoint 固定写进配置会在部分设备上静默丢失数据。

系统侧调试时，可先查询 tracefs，再从目标设备已经暴露的 sched、vmscan、filemap、kmem 和 block 事件中选择配置。

```shell
adb shell su 0 sh -c \
  "grep -E 'page_fault|vmscan|filemap|kmem|block' \
  /sys/kernel/tracing/available_events"
```

这条命令需要 root 或等价系统调试权限。结果为空时应回到 Simpleperf 计数和常规 Perfetto 调度/I/O 数据，不要假设 tracepoint 名称跨内核版本稳定。eBPF 同样只能挂载设备中存在且策略允许的 tracepoint；kprobe 方案还与内核版本、BTF 和函数 ABI 绑定，不适合作为普通应用的通用监控接口。

### 建立因果证据

建议按以下顺序收集证据：

1. 给冷启动、页面切换、滚动或后台恢复打清晰的时间标记，按阶段计算 fault 增量和持续时间。
2. 用 `/proc/<pid>/maps`、Perfetto 文件系统事件或采样调用栈确认相关映射是 DEX/OAT、共享库、资源、匿名堆还是 swap。
3. 同时观察调度等待、内存回收和 block I/O。major 增长且关键线程等待存储，才构成 I/O 影响关键路径的证据。
4. 在同一设备、同一安装状态和可比内存压力下做基线对照。冷 page cache 与热 page cache 应分组记录。

全局 `iowait` 上升只能说明采样 CPU 存在 I/O 等待，无法指出具体进程；较高的 kernel CPU 则表示 CPU 正在执行内核代码，不表示 CPU 在等待 I/O。两项数据都需要时间线和进程级证据补充。

## 按原因选择改进手段

### 冷启动文件页

先确认 major fault 落在启动关键路径，并定位到 DEX/OAT、native library 或资源。Java/Kotlin 代码可优先检查 Baseline Profile 与 Startup Profile 是否覆盖启动路径，让 ART 编译和 DEX 布局更贴近启动调用集合。native library、资源和 APK 条目的压缩及对齐需要结合构建产物、安装形态和 mmap 条件验证，不能把“压缩更小”直接等同于 fault 更快。

### 匿名页与 COW

minor fault 集中在首次触碰大块匿名内存时，应检查分配时机、初始化范围和是否位于 UI 关键线程。Zygote 继承页的大量写入还会增加 COW，可结合 PSS 分类、heap profile 和调用栈找出写热点。降低 fault 数不是独立目标；把初始化移出关键路径且不增加总内存和后台压力，才有优化价值。

### swap-in 与后台恢复

后台恢复出现 major fault 时，要同时查看内存压力、进程冻结、zRAM、writeback 和 LMKD 相关事件。Android 17 的 MMD prefetch 是系统策略能力，普通应用不应自行复制其机制。系统开发者调整策略时，要比较恢复时延、后台 I/O、内存占用和闪存写入。

### 谨慎使用预取建议

`madvise(MADV_WILLNEED)`、readahead 或主动触碰页面可能把等待移到更早的时间，也可能造成无效 I/O、挤占 page cache 和增加内存压力。只有在访问集合稳定、收益经过冷态实验验证、且预取不与前台关键任务竞争时才值得采用。

## `userfaultfd`：ART 的生产用例与应用边界

`userfaultfd` 从 Linux 4.3 开始提供用户态 fault 处理能力。Android 17 并非“缺少实际案例”：ART 的 Concurrent Mark-Compact GC 在 [`mark_compact.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc) 中调用 `userfaultfd(..., UFFD_USER_MODE_ONLY)`，注册 moving space，在并发压缩期间处理受管区域的缺页。

ART 会检查内核特性与所需 UFFD feature。创建失败或条件不满足时，代码把 `uffd_` 设为 fallback mode，转入 stop-the-world compaction。这个实现说明了两个边界：

- `userfaultfd` 的可用性由内核能力、Android 安全限制和系统配置共同决定；
- 接管 fault 会改变线程阻塞和内存访问行为，它适合受控的运行时或系统组件，不是零干扰的应用性能计数器。

普通应用只需要 Page Fault 指标时，应使用 `/proc/self/stat` 或受支持的 perf 工具。系统组件确需 `userfaultfd` 时，应像 ART 一样做 feature negotiation、失败降级和版本级验证。

## 小结

Page Fault 计数描述的是地址映射修复过程，不能直接换算分配字节，也不能只凭 major 增长断定存储瓶颈。Android 17 上的可靠做法是：

1. 用 `min_flt`、`maj_flt` 或 Simpleperf 区分成功完成的 minor 与 major。
2. 把失败访问交给 tombstone、signal 和 `si_code` 分析，不把它当作第三个 proc fault 计数。
3. 结合场景时间线、映射对象、调度、回收和 I/O 证据定位原因。
4. 在运行时读取 4 KB 或 16 KB page size，但不再用页数推算对象分配量。
5. 针对文件冷页、匿名页/COW、swap-in 分别验证改动，避免用统一的预取或 mmap 建议代替测量。

以上结论已对照 AOSP `android-17.0.0_r1`、Android common kernel `android17-6.18-2026-06_r6`、Android 17 MMD 文档及 16 KB page-size 文档。
