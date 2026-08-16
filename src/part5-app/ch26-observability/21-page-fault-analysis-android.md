---
title: "Page Fault 类型分析与 Android 实践"
chapter: "26.21"
section: "26.21"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_source_verified_at: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1; latest Android Common Kernel android17-6.18-2026-06_r39; current Android, Perfetto, and Linux kernel documentation retrieved 2026-08-15; the cited r6 fault.c, mm_types.h, and array.c files are byte-identical to r39, while mm_account_fault() is unchanged although mm/memory.c changed elsewhere"
confidence: high
tags: [page-fault, minor-fault, major-fault, mmap, memory, observability]
related_chapters: ["4.1", "4.2", "4.12", "4.15", "14.2", "20.3", "20.11", "23.3", "26.19", "26.20"]
sources:
  - type: legacy-reference-preserved
    path: "frameworks/base/core/jni/android_os_Debug.cpp"
  - type: legacy-reference-preserved
    path: "developer.android.com/topic/performance/memory"
  - type: legacy-reference-preserved
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/mm/fault.c"
  - type: legacy-reference-preserved
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/memory.c"
  - type: legacy-reference-preserved
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/mm_types.h"
  - type: legacy-reference-preserved
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table_generator.py"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/android_application_profiling.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/arch/arm64/mm/fault.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/mm/memory.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/include/linux/mm_types.h"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/array.c"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/filesystems/proc.rst"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/admin-guide/mm/userfaultfd.rst"
  - type: official
    path: "https://source.android.com/docs/core/perf/mmd"
  - type: official
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size"
  - type: official
    path: "https://source.android.com/docs/core/tests/debug/native-crash"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-scheduling"
---

# 26.21 Page Fault 类型分析与 Android 实践

## 先分清计数与失败结果

Page Fault（缺页异常）是 CPU 访问虚拟地址时，因页表缺项或权限不符而交给内核处理的同步异常。“同步”表示异常由当前指令直接触发；内核补齐映射或向线程发送信号之前，这条指令无法继续。信号是内核向线程或进程报告事件的机制。Page Fault Handler（缺页处理程序）泛指接收异常并尝试修复映射的内核代码。

Linux 的统计结果分为两类成功计数和一类失败结果：

| 指标或结果 | Android 17 / Linux 6.18 中的含义 | 常见原因 |
|---|---|---|
| Minor Fault | 内核成功完成 fault，最终未带 `VM_FAULT_MAJOR`，处理过程也未发生重试 | 匿名页按需分配、写时复制（COW）、页缓存已有数据但进程页表项（PTE）尚未建立 |
| Major Fault | 内核成功完成 fault，最终带 `VM_FAULT_MAJOR`，或处理过程发生过重试 | 文件页需要读入、交换页需要从 zRAM（内存压缩块设备）或后备存储取回 |
| 失败访问 | 内核不能为该访问建立合法映射，通常向线程发送 SIGSEGV 或 SIGBUS | 地址未映射、权限不符、文件映射越过 EOF、硬件内存错误 |

“Invalid Page Fault”可用于口头描述失败访问；`/proc/<pid>/stat` 并没有与 minor、major 并列的第三个同名计数器。`min_flt + maj_flt` 只覆盖成功完成的 fault，native crash 需要另行统计。

页表项（Page Table Entry，PTE）记录虚拟页到物理页的映射与访问权限。转译后备缓冲区（Translation Lookaside Buffer，TLB）是 CPU 保存近期地址转换结果的硬件高速缓冲。PTE 有效而转换结果未命中 TLB 时，硬件执行 `page-table walk`（逐级查页表）后即可继续；这类 TLB miss 通常不会进入内核的 Page Fault Handler，应与 Page Fault 分开分析。

## Android 17 arm64 的处理路径

本文保留 `android-17.0.0_r1` 平台源码和 `android17-6.18-2026-06_r6` 内核源码作为历史核验锚点。arm64 的入口在 [`arch/arm64/mm/fault.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/mm/fault.c)，通用内存管理在 [`mm/memory.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/memory.c)。

截至 2026-08-15，同系列最新标签是 `android17-6.18-2026-06_r39`。两版的 `fault.c` 字节一致；`mm/memory.c` 其他位置虽有改动，`mm_account_fault()` 的函数体保持一致。图中的 ESR（Exception Syndrome Register，异常综合寄存器）记录异常原因，VMA（Virtual Memory Area，虚拟内存区域）记录一段连续地址的权限和后备对象。调用关系只用于定位职责，每次 fault 会按原因选择其中一条分支。

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

`do_page_fault()` 根据 ESR 判断读、写或执行访问。内核先尝试用只保护目标 VMA 的 per-VMA lock 查找它，条件不满足时再使用覆盖整个地址空间的 `mmap_lock`。VMA 存在且权限匹配后，`handle_mm_fault()` 才进入匿名页、COW、文件页或 swap（交换页）等通用处理；错误结果返回 arm64 入口后，再转换成对应信号。

三处计数时机决定了各指标的边界：

- arm64 在校验 VMA 之前调用 `perf_sw_event(PERF_COUNT_SW_PAGE_FAULTS, ...)`。perf software event 是由内核代码递增、供性能工具读取的软件计数器；Simpleperf 的 `page-faults` 会包含这条主处理路径中后来失败的访问。
- `handle_mm_fault()` 返回前调用 `mm_account_fault()`。`PGFAULT` 是内核虚拟内存事件，系统级结果可在 `/proc/vmstat` 的 `pgfault` 字段看到。它计入已经到达 `handle_mm_fault()` 的成功与失败结果；`VM_FAULT_RETRY` 表示退出本轮处理并稍后重试，未完成的 retry 会先返回，待处理完成时再计数。VMA 查找或权限检查阶段提前失败的访问不会到达这里。
- `mm_account_fault()` 遇到 `VM_FAULT_ERROR` 时，不更新 `current->min_flt`、`current->maj_flt` 及对应的 perf minor/major 事件。成功结果最终带 `VM_FAULT_MAJOR`，或之前设置过 `FAULT_FLAG_TRIED`，都会记作 major；其余记作 minor。

所以，`page-faults` 与 `minor-faults + major-faults` 出现差值有源码依据。解释差值时需要同时检查失败访问、统计区间和工具权限。

## Minor Fault：能在内存中完成的映射修复

Minor Fault 的记账条件是成功完成、最终未带 `VM_FAULT_MAJOR`，并且处理过程没有 retry。它通常能用内存中已有的数据完成映射，常见来源包括：

- **匿名页按需分配**：`MAP_ANONYMOUS` 表示映射没有文件作为后备对象。`mmap(MAP_ANONYMOUS)` 或堆扩展先建立 VMA，线程首次访问时再建立物理页和 PTE；读取可能先映射共享零页，写入时再获得私有页。
- **写时复制（Copy-on-Write，COW）**：Zygote 是预加载框架代码并 `fork` 出应用进程的系统进程。父子进程先共享只读页，某一方写入时，`do_wp_page()` 才为它准备私有副本。
- **文件页已在页缓存中**：页缓存（`page cache`）保存内核近期读过的文件数据。数据已在内存而当前进程缺少对应 PTE 时，内核可以直接建立映射，无需再次读取存储。

Minor 只表示“成功处理且未归为 major”。它无法证明页面此前已经映射，也无法证明发生了一次对象分配。一次 fault 仍可能分配页表页、处理 folio、执行 memcg 计费、维护反向映射并等待锁；folio 是把一个或多个连续基础页作为整体管理的内核对象，memcg 是按控制组统计和限制内存的机制，反向映射则用于从物理页找到映射它的进程地址。耗时会随内存压力、页大小、folio 大小和并发状态变化，不存在跨设备通用的固定微秒阈值。

`malloc()` 何时改用 `mmap()` 由分配器实现、进程状态和版本共同决定。固定字节阈值既不能解释 COW，也不适合作为通用的 Page Fault 判断规则。

## Major Fault：处理过程需要读取或等待

Linux 6.18 在 [`include/linux/mm_types.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/mm_types.h) 中把 `VM_FAULT_MAJOR` 注释为 “Page read from storage”。`do_swap_page()` 需要从交换区读页时会设置该标志，文件映射的 fault handler 需要读页时也会返回 major。

记账规则还把发生过 retry 的成功 fault 归入 major。retry 表示本轮无法立即完成，处理程序需要释放条件、等待或重新进入；它可能与 I/O 有关，也可能由其他等待触发。因此，major 只能作为“需要读页或重试”的调查线索，单凭该计数无法证明闪存 I/O 已经发生。

Android 上常见的来源有：

- 冷启动访问尚未进入页缓存的 APK、DEX、OAT/VDEX、共享库或资源文件页面；
- 后台进程的匿名页进入交换区，进程恢复后从 zRAM 读取并解压；
- 设备启用 zRAM writeback 后，交换页已写入后备存储，恢复访问需要从闪存取回；
- fault handler 等待页面 I/O 或发生 retry，最终按 major 计数。

一次 fault 可能触发 readahead（内核预读后续文件页），一次 I/O 也可能满足多个后续 fault。folio 大小、页缓存命中和 I/O 合并都会改变“fault 次数”与“读取字节数”的关系。UFS（Universal Flash Storage，移动设备常用闪存接口）、I/O 调度器、文件系统和当前负载还会影响时延。只有 major 增长与关键线程等待存储在同一时间段出现，才能支持“存储影响用户体验”的判断。

### Android 17 的 zRAM 与 MMD

swap（交换）是把匿名页内容写入交换设备、释放原物理页，并在再次访问时读回的机制。zRAM 是位于内存中的压缩块设备，Android 通常把它用作交换设备；从 zRAM 读回并解压页面仍会走 swap-in 路径并记作 major。

Android 17 起，[Memory Management Daemon（MMD）](https://source.android.com/docs/core/perf/mmd) 统一管理 zRAM 配置和维护任务。recompression 会用压缩率更高的算法重新压缩冷页；writeback 会把符合条件的 zRAM 页移到 `/data` 上的后备存储；prefetch 则在应用按需访问前先把指定进程的交换页取回。应用从缓存冻结状态恢复时，`system_server` 可以请求 MMD 异步执行按进程预取，以减少主界面初始化期间等待后备存储的概率。

MMD 由系统策略调用，普通应用没有可移植的直接控制接口。zRAM 大小、压缩算法、writeback 开关、后备设备和预取策略都由产品配置决定；设备分析应读取实际配置和内核统计。

## 失败访问与 native crash

`si_code` 记录信号的具体原因。arm64 找不到目标 VMA 时通常发送 `SIGSEGV`，并把 `si_code` 设为 `SEGV_MAPERR`；VMA 存在但访问权限不符时通常得到 `SIGSEGV/SEGV_ACCERR`。文件映射越过有效文件内容等 `VM_FAULT_SIGBUS` 路径会产生 `SIGBUS/BUS_ADRERR`，硬件内存错误还可能产生 `BUS_MCEERR_*`。

MTE（Memory Tagging Extension，内存标签扩展）会比较指针标签与内存标签，标签检查失败时也可能发送带专用 `si_code` 的 `SIGSEGV`。因此，同为 signal 11，根因仍可能不同。

排查失败访问时还要考虑三个边界：

- use-after-free（释放后使用）未必立即 crash。被释放地址可能仍在 VMA 内，甚至已被分配器复用，此时页表层面仍允许访问。
- 栈访问落入允许增长的区域时，内核可能扩展映射；越过 guard 区或资源限制后才会失败。guard 区是留在栈边界附近、用于捕获越界访问的保护区域。
- tombstone 是 Android native crash 的诊断文件。判断根因时应一起读取 signal、`si_code`、fault address、寄存器和内存映射表，单看 `signal 11` 信息不足。

这类失败属于 native 稳定性调查，不应混入性能侧的 `min_flt`/`maj_flt` 趋势。完整方法见 [20.3 Native Crash 治理](../ch20-stability/03-native-crash-governance.md)。

## `/proc/<pid>/stat` 计数的精确语义

字段顺序由内核 [`fs/proc/array.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/proc/array.c) 输出。Linux 源码中的 task 是可被调度的执行单元，在这个接口里可对应单个线程，也可按线程组汇总。字段布局如下，可直接用于检查解析器索引。

```text
字段 10  minflt   当前任务或线程组的 minor fault
字段 11  cminflt  已回收子进程的 minor fault
字段 12  majflt   当前任务或线程组的 major fault
字段 13  cmajflt  已回收子进程的 major fault
字段 22  starttime  任务自系统启动后的创建时刻，单位为 clock tick
```

clock tick 是内核用于表示时间的离散单位，频率由系统的 `CLK_TCK` 决定，与 CPU 时钟周期含义不同。`starttime` 可用于判断两次读取是否仍属于同一个进程实例。

读取 `/proc/<pid>/stat` 时，`minflt` 和 `majflt` 是整个线程组的聚合值；读取 `/proc/<pid>/task/<tid>/stat` 时，得到指定线程的值。`cminflt`、`cmajflt` 累计已经由父进程等待回收的子进程 fault，不包含当前进程的其他线程。

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

`comm` 是 stat 中用圆括号包住的任务名，内容可以含空格和右括号；找到最末尾的 `)` 后再解析，才能保持后续字段位置稳定。示例只读取当前应用自己的 proc 节点，并用 `starttime` 识别 PID 复用或进程重启。采样应放在低频诊断窗口，避免文件读取干扰短场景；进程或线程退出、读取失败及计数回退都按无效样本处理。

### 为什么不能用 fault 数估算分配字节

`Δfaults × 4 KB` 无法表示这段时间的内存分配量，原因包括：

- Android 15 及更高版本支持 16 KB page-size 设备；Android 17 设备可能使用 4 KB 或 16 KB 页，页大小要在运行时查询；
- minor fault 还包含 COW 和文件页缓存映射，同一虚拟区域在回收后也可能再次 fault；
- 分配器可以复用已经驻留的堆页，发生分配却没有新增 fault；
- readahead 和大 folio 会让一次 major fault 与一个基础页的 I/O 失去一一对应关系。

Java/Kotlin 可按 [AOSP 页大小指南](https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size) 调用 `Os.sysconf(OsConstants._SC_PAGE_SIZE)`，原生代码使用 `getpagesize()`。页大小只适合换算明确以 page 为单位的内核字段；对象或原生分配应使用 Heap Profile、heapprofd，或通过 JVMTI（Java Virtual Machine Tool Interface）对分配事件采样。

## 从计数建立因果证据

Page Fault 调查要回答三个问题：计数在哪个阶段增长、增长的是 minor 还是 major、当时访问的是文件映射还是匿名映射。计数只能提示现象，时间线和映射对象才能把现象与用户可感知时延联系起来。

### 用 Simpleperf 区分事件

Android 17 Simpleperf 的生成器在 [`event_table_generator.py`](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table_generator.py) 中注册 `page-faults`、`minor-faults` 和 `major-faults` 三个软件事件。命令应先列出目标设备可用事件，再对指定应用计数。

```shell
adb shell simpleperf list
adb shell simpleperf stat \
  --app com.example.app \
  -e page-faults,minor-faults,major-faults \
  --duration 10
```

`simpleperf list` 的实际输出就是本机能力边界。应用还要满足 [Android application profiling](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/android_application_profiling.md) 的权限条件：面向发布的 release 包通常需要 `profileableFromShell`，调试用 debug 包可依赖 `debuggable`，root 设备另有更宽权限。user build 是面向量产设备的系统构建，预装工具版本和厂商策略仍可能缩小其可用范围。统计结果中 `page-faults` 与 minor、major 之和的差值，应按三类事件各自的计数时机解释。

### 用 Perfetto 定位等待发生在哪一段

Perfetto 可以把 fault 增长与启动阶段、线程调度、文件 I/O、内存回收和块设备 I/O 放在同一时间线上。tracepoint 是内核预先定义并命名的静态事件点；tracefs 是列出、启用和读取这类事件的内核虚拟文件系统。arm64 设备不保证暴露 `exceptions/page_fault_user`，把它固定写进配置可能得到没有该事件的数据。

系统侧调试应先查询 tracefs，再从目标设备已经暴露的 `sched`、`vmscan`、`filemap`、`kmem` 和 `block` 事件中选择配置。

```shell
adb shell su 0 sh -c \
  "grep -E 'page_fault|vmscan|filemap|kmem|block' \
  /sys/kernel/tracing/available_events"
```

这条命令需要 root 或等价系统调试权限。结果为空时，应改用 Simpleperf 计数和常规 Perfetto 调度/I/O 数据，不要假定 tracepoint 名称跨内核版本稳定。

eBPF 是经过内核校验、可在事件点执行的小程序，也只能挂到设备已有且安全策略允许的位置。`kprobe` 会在内核函数或指令位置安装动态探针，BTF 描述内核类型信息，ABI 规定函数调用约定；内核升级可能改变三者依赖的符号、类型或参数布局。这些方案适合受控的系统调试环境，不适合作为普通应用的通用监控接口。

### 把计数对齐到关键路径

建议按以下顺序收集证据：

1. 给冷启动、页面切换、滚动或后台恢复添加时间标记，按阶段计算 fault 增量和持续时间。
2. 读取 `/proc/<pid>/maps`，或使用 Perfetto 文件系统事件、采样调用栈，确认相关 VMA 对应 DEX/OAT、共享库、资源、匿名堆还是 swap。
3. 同时观察线程状态、内存回收和块设备 I/O。major 增长并且关键线程同期等待存储，才构成 I/O 影响关键路径的证据。
4. 在同一设备、同一安装状态和相近内存压力下做基线对照，分别记录冷页缓存与热页缓存场景。

`/proc/stat` 中的 `iowait` 表示 CPU 被记为空闲且系统有待完成 I/O 的时间，它无法把等待归因到具体进程，内核文档也提醒该值很难精确计算。较高的 kernel CPU 表示 CPU 正在执行内核代码，也不表示 CPU 正在等待 I/O。两项数据都需要进程级时间线补充。

## 按原因选择改进手段

### 冷启动文件页

先确认 major fault 出现在启动关键路径，并定位到 DEX/OAT、原生库或资源。DEX 保存应用字节码，OAT/VDEX 是 ART 编译或校验这些字节码时生成和使用的产物。Baseline Profile 记录常用代码，帮助 ART 提前编译；Startup Profile 描述启动期间常用类和方法，还可参与 DEX 布局优化。检查两类 profile 是否覆盖实际启动调用，再比较编译产物与布局变化。

原生库、资源和 APK 条目的压缩、对齐会影响能否直接 `mmap` 及读取范围，需要结合构建产物和安装形态验证。文件体积变小与 fault 等待缩短没有必然关系。

### 匿名页与 COW

minor fault 集中在首次访问大块匿名内存时，应检查分配时机、初始化范围和执行线程。Zygote 继承页的大量写入还会增加 COW。PSS（Proportional Set Size，按共享比例分摊后的驻留内存）、堆剖析和调用栈可以帮助定位写入来源。

评价改动时同时比较关键路径时延、总内存和后台压力。单独降低 fault 数不能证明优化有效。

### swap-in 与后台恢复

后台恢复出现 major fault 时，要同时查看内存压力、进程冻结、zRAM、writeback 和 LMKD 事件。LMKD（Low Memory Killer Daemon，低内存终止守护进程）会在内存压力下选择进程终止，它的事件可帮助区分“从交换区恢复”和“进程已被杀后重启”。

Android 17 的 MMD prefetch 属于系统策略能力，普通应用不应复制其内核机制。系统开发者调整策略时，要同时比较恢复时延、后台 I/O、内存占用和闪存写入量。

### 谨慎使用预取建议

`madvise(MADV_WILLNEED)` 是向内核提示“近期可能访问这段映射”，不保证立即读入，也不保证保留页面。它、readahead 或主动访问页面都可能把等待移到更早时刻，也可能产生无效 I/O、挤占页缓存并增加内存压力。采用前要在冷态场景验证访问集合和收益，并确认预取不与前台关键任务竞争。

## `userfaultfd`：ART 的生产用例与应用边界

`userfaultfd` 允许进程注册一段虚拟地址，并通过文件描述符接收该区域的 fault 通知，再用 `UFFDIO_*` ioctl 完成映射。文件描述符是进程引用内核对象的整数句柄，ioctl 是向该对象发送控制命令的系统调用。`userfaultfd` 把部分缺页处理交给用户态线程，适合需要自行控制页面到达时机的内存管理器。

Android 17 已有生产用例。ART 的 Concurrent Mark-Compact GC 在 [`mark_compact.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc) 中调用 `userfaultfd(..., UFFD_USER_MODE_ONLY)`。Concurrent Mark-Compact 会标记存活对象并移动它们以压缩堆；moving space 是这次移动涉及的 ART 堆区域。

ART 先通过 `UFFDIO_API` 查询可用 feature，这一步称为 feature negotiation（能力协商）。它还检查所需内核能力和 `UFFD_FEATURE_SIGBUS`。创建失败或条件不满足时，`uffd_` 进入 fallback mode，改用 stop-the-world compaction；后者会暂停应用线程再完成压缩。

这个实现给出两条使用边界：

- `userfaultfd` 的可用性由内核能力、Android 安全限制和系统配置共同决定；
- 接管 fault 会改变线程阻塞与内存访问行为，适合受控的运行时或系统组件，无法充当低干扰的应用性能计数器。

普通应用只需 Page Fault 指标时，应读取 `/proc/self/stat` 或使用设备支持的 perf 工具。系统组件确需 `userfaultfd` 时，应像 ART 一样完成能力协商、失败降级和逐版本验证。

## 判读清单

1. `min_flt`、`maj_flt` 与 Simpleperf minor/major 只统计成功完成的 fault；`page-faults` 的计数边界更靠近架构入口。
2. SIGSEGV、SIGBUS 等失败访问交给 tombstone、signal 和 `si_code` 分析，不把它们虚构成第三个 proc fault 计数。
3. major 是页面读入或 retry 的线索。只有它与关键线程存储等待同时出现，才支持 I/O 影响关键路径的判断。
4. 设备页大小在运行时可能是 4 KB 或 16 KB；fault 数仍不能换算对象分配字节。
5. 文件冷页、匿名页/COW 与 swap-in 需要分别验证，预取、布局或初始化改动都要用同场景对照评估。

## 参考材料

- [Android Common Kernel r39：arm64 fault 入口](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/arch/arm64/mm/fault.c)
- [Android Common Kernel r39：通用 fault 处理与计数](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/mm/memory.c)
- [Android Common Kernel r39：`VM_FAULT_*` 定义](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/include/linux/mm_types.h)
- [Android Common Kernel r39：进程 stat 输出](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/fs/proc/array.c)
- [Android Common Kernel r39：procfs 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/filesystems/proc.rst)
- [Android Common Kernel r39：`userfaultfd` 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r39/Documentation/admin-guide/mm/userfaultfd.rst)
- [AOSP：Android 17 Simpleperf 软件事件表](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/event_table_generator.py)
- [AOSP：Android 应用 Simpleperf 权限与用法](https://android.googlesource.com/platform/system/extras/+/refs/tags/android-17.0.0_r1/simpleperf/doc/android_application_profiling.md)
- [Android 官方文档：Memory Management Daemon](https://source.android.com/docs/core/perf/mmd)
- [Android 官方文档：运行时获取页大小](https://source.android.com/docs/core/architecture/16kb-page-size/getting-page-size)
- [Android 官方文档：native crash 与 tombstone](https://source.android.com/docs/core/tests/debug/native-crash)
- [Perfetto：CPU scheduling events](https://perfetto.dev/docs/data-sources/cpu-scheduling)
