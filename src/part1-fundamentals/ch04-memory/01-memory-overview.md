---
title: Android 内存模型全景
chapter: '4.1'
section: '4.1'
status: ready-for-review
drafted_date: '2026-03-31'
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-06-12'
last_verified_against: "AOSP android-16.0.0_r1 / Android Developers bitmap memory & Android 17 app memory limits docs / Perfetto Java heap profiler & OOME docs / 16 KB page size docs / kernel zram docs"
reviewed_date: '2026-05-07'
reviewed_by: openclaw-task6
review_notes: 'task2b-polish: 已做首轮润色；2026-04-14 Task6：L1/L2 小修；2026-05-07 Task2B 验证：Stack
  物理占用已拆为虚拟栈保留+resident stack pages；ZRAM physical used 口径已修正为三指标分读（physical used/in
  swap/total swap）；2026-05-07 19:05 Task6 复审：L1/L2 轻量修复通过，交回 Task9；2026-05-07 20:08
  Task6 复审：L1/L2 小修 12 处，锚点覆盖完整，无新增回炉项，交回 Task9'
task6_result: pass-light-edit
confidence: medium
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
sources:
- type: official
  path: https://developer.android.com/topic/performance/memory-management
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://source.android.com/docs/core/perf/lmkd
- type: official
  path: https://source.android.com/docs/core/perf/cgroups
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ProcessList.java
- type: aosp
  path: frameworks/base/core/java/android/content/ComponentCallbacks2.java
- type: aosp
  path: system/core/libprocessgroup/profiles/task_profiles.json
- type: aosp
  path: system/memory/lmkd/lmkd.cpp
- type: official
  path: https://docs.kernel.org/admin-guide/blockdev/zram.html
- type: official
  path: https://perfetto.dev/docs/data-sources/java-heap-profiler
- type: official
  path: https://perfetto.dev/docs/case-studies/android-outofmemoryerror
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerShellCommand.java
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java
- type: aosp
  path: art/runtime/hprof/hprof.cc
- type: aosp
  path: external/perfetto/protos/perfetto/config/profiling/java_hprof_config.proto
- type: blog
  path: https://androidperformance.com/
- type: blog
  path: https://juejin.cn/post/7530909474103296039
tags:
- memory
- PSS
- RSS
- dumpsys
- meminfo
- procfs
- ZRAM
- cgroup
related_chapters:
- '4.2'
- '4.3'
- '4.4'
- '4.5'
- '10.1'
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-06-12'
last_task9_at: '2026-06-12T11:20:00+08:00'
last_task9_audit: '2026-06-12'
last_task9_autofix_at: '2026-06-12'
last_task9_review_log: 'logs/deep-review/2026-06-12-11-audit.md'
last_task6_audit: '2026-05-21'
task9_review_notes: '2026-05-07 20:24 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 1。遗留 `android.process_meminfo` 数据源口径错误，需统一改为 Perfetto `linux.process_stats` / `linux.sys_stats` / `android.java_hprof` 分层说明；补真实 dumpsys/Perfetto 样本。 | 2026-05-12 22:15 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；满足 task6_result=pass-light-edit 且 queue 无 pending，自动晋升 finalized / ready-to-publish。 | 2026-06-12 11:20 Task9 idle audit auto-fix: 修正 16 KB page 小对象表述、HPROF 小节 Perfetto Java heap dump 版本边界与旧的 traced Java heap dump 采集命令，改为 Android 11+ `android.java_hprof` / Android 14+ OOME trigger / `adb shell perfetto -c` 配置；回到 Task6 复审。'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-02
---


# Android 内存模型全景

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 内存模型全景：物理内存 → 内核管理 → 用户空间（Native + Java Heap + Graphics）
- 🔹 关键内存指标：VSS、RSS、PSS、USS 的定义与适用场景
- 🔹 进程内存组成：Java Heap、Native Heap、Code（.dex/.so）、Stack、Graphics（GPU/EGL）
- 🔹 procfs 接口：/proc/meminfo、/proc/<pid>/status、/proc/<pid>/smaps
- 🔹 dumpsys meminfo 的解读方法

### 扩展（可选深入）

- 🔸 cgroup v1/v2 对 Android 内存控制的作用
- 🔸 ZRAM / Swap 在 Android 上的使用与配置

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 内存模型

用 Perfetto 抓 Trace 时，可能注意过这样一个场景：一个列表滑得好好的，突然连续出现几帧耗时飙升，Trace 里对应的位置是几条长长的绿色 GC 条目。或者更隐蔽一些——App 没有明显的卡顿，但 `dumpsys meminfo` 显示 PSS 在几分钟内从 80MB 缓慢爬到了 200MB。

这些现象的背后，是 Android 内存系统在工作。理解内存模型，是为了在遇到内存相关的问题时，无论是 OOM 崩溃、GC 导致的卡顿，还是后台进程被杀，都知道从哪里入手排查。

这一节建立一张完整的内存全景图：从物理内存到内核管理，再到进程的各个内存区域，也把工具中的数字代表什么含义讲清。有了这张全景图，后面关于内存优化、GC 机制、LMK 等章节才有落脚点。

[已验证: 官方文档, developer.android.com/topic/performance/memory-management]

## 从物理内存到进程：Android 内存的整体架构

Android 的内存体系可以分成三层来看：物理内存、内核管理、用户空间。这三层彼此耦合。内核负责把物理内存分配给各个进程，进程之间的内存通过共享库和共享内存机制产生关联，Android 框架在内核之上又加了一层自己的管理策略。

### 物理内存：一切的基础

手机上的 RAM 就是物理内存。一台 8GB 内存的设备，实际可用的并不是完整的 8GB——GPU 会占用一部分（通常几百 MB 到 1GB 不等），内核本身也要占用一些。剩下才是系统服务和各个 App 可以使用的部分。

需要留意的是，开启了 MTE（Memory Tagging Extension，ARMv8.5+）的设备会额外预留约 3% 的物理 RAM 用于存储内存标签，加上粒度开销，全系统 PSS 大约会上涨 5%。这是安全硬件的固定开销，在做内存基线对比时先把这部分扣除，避免误判为泄漏。

和桌面系统不同，Android 设备通常没有磁盘级别的 Swap 空间。它使用的是 ZRAM——在内存中划出一块区域做压缩交换。这样做的好处是避免了闪存的写入磨损和 IO 延迟，代价是消耗 CPU 来做压缩和解压。当内存紧张时，内核通过 `kswapd` 线程把不太活跃的内存页压缩到 ZRAM 中，腾出物理内存。

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd]

### 内核管理：分配、回收、保护

Linux 内核是内存管理的核心执行者。它通过页表把虚拟地址映射到物理地址，处理页面换入换出，管理共享内存，以及响应内存压力事件。

Android 在 Linux 内核的基础上做了几件特别的事情：

**进程优先级与内存回收绑定。** Framework 在 `ProcessList.java` 里维护 `adj` / procstate 这一组进程重要性分层，最终会映射到 `/proc/<pid>/oom_score_adj`。`lmkd` 处理内存回收时，先看系统是否进入压力区间，再结合 `oom_score_adj` 选择更容易被杀的进程。前台进程的 `oom_score_adj` 更低，缓存进程更高。这个机制会在 [4.4 Low Memory Killer](04-lmk.md) 中详细展开。

**App 侧 trim 回调和系统侧杀进程是两条路径。** `onTrimMemory()` 属于 `ComponentCallbacks2` 回调，由 framework 在合适的生命周期和内存压力点通知 `Application`、`Activity`、`Service` 等组件，让 App 主动释放缓存。`lmkd` 不会直接向 App 调 `onTrimMemory()`；当回收压力继续升高时，它会按 kill 策略直接结束目标进程。API 34 起，`TRIM_MEMORY_RUNNING_MODERATE`、`TRIM_MEMORY_RUNNING_LOW`、`TRIM_MEMORY_RUNNING_CRITICAL`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 这些等级已经不再投递给 App。

Android 17（API 37）引入了 app memory limits 硬限额机制。当应用的匿名交换页（AnonSwap）用量超过系统分配的配额时，进程会被终止。`ApplicationExitInfo.getReason()` 返回 `REASON_OTHER`，`getDescription()` 返回的字符串包含 `"MemoryLimiter:AnonSwap"`——不是独立的 `MemoryLimiter` reason code。开发者还可以通过 `ProfilingTrigger.TRIGGER_TYPE_ANOMALY` 在命中限额时触发 heap dump，用于事后分析。配额审计口径以 AOSP `ActivityManagerService` 和官方行为变更文档为准，PSS、RSS、AnonSwap 在 lmkd / kernel / framework 各层含义不同，不要混用。

**cgroup 约束。** Android 10 起把 cgroup 配置统一到 `cgroups.json` / `task_profiles.json` 这层抽象。memory controller 字段要按 v1 / v2 分开看：`MemLimit` 对应 v1 `memory.limit_in_bytes` 或 v2 `memory.max`；`MemSoftLimit` 对应 v1 `memory.soft_limit_in_bytes` 或 v2 `memory.low`。注意 `memory.pressure_level` 是 v1 接口，不能和 v2 的 `memory.max` / `memory.low` 混为一谈。

[已验证: source.android.com/docs/core/perf/lmkd；frameworks/base/services/core/java/com/android/server/am/ProcessList.java；frameworks/base/core/java/android/content/ComponentCallbacks2.java；system/core/libprocessgroup/profiles/task_profiles.json]

### 用户空间：进程看到的世界

每个 Android 进程通过虚拟内存看到的是自己的地址空间，它不能直接访问其他进程的内存（除非通过共享内存机制）。一个进程的内存空间大致包含以下区域：

[图：Android 进程内存布局示意图——从低地址到高地址依次为：代码段(.text)、数据段(.data/.bss)、Heap（Java Heap + Native Heap）、mmap 区域（.so/.dex/.apk 等映射）、Stack]

**代码段：** 包括 App 的 DEX 代码经过 AOT 编译后生成的 `.oat` 文件，以及系统框架的 `.vdex` 文件。这些代码通过 `mmap` 以只读方式映射到进程空间，多个进程可以共享同一份物理页面。

**Heap：** 这是内存分析中最常关注的区域，分为 Java Heap 和 Native Heap。Java Heap 由 ART 管理，存放所有 Java/Kotlin 对象；Native Heap 由 C/C++ 的 `malloc` 管理，存放 native 分配的内存。Bitmap 的像素数据从 Android 8.0 开始也存放在 Native Heap 中（之前版本存放在 Java Heap 的 "External" 区域）。

**mmap 映射：** `.so` 动态库、`.dex` 字节码、`.apk` 资源、字体文件等都通过 `mmap` 映射到进程空间。这些映射通常是私有的（进程修改时 COW），但未修改的部分可以在进程间共享。

**Stack：** 每个线程有自己的栈空间，默认大小通常是 1MB 左右（取决于 Android 版本和线程创建方式）。栈内存用于函数调用链和局部变量。

**Graphics：** GPU 相关的内存，包括 GL 纹理、EGL surface、图形缓冲区等。这部分内存在 `dumpsys meminfo` 中表现为 `Gfx dev`、`EGL mtrack`、`GL mtrack`。

[已验证: 官方文档, developer.android.com/topic/performance/memory-management]

## 关键内存指标：VSS、RSS、PSS、USS

当我们谈论"一个进程占了多少内存"时，答案取决于用哪个指标来衡量。Android/Linux 系统有四个核心内存指标，理解它们的区别是做内存分析的基本功。

### VSS（Virtual Set Size）——虚拟地址空间

VSS 是进程的整个虚拟地址空间大小，包括已经分配但尚未使用的部分、通过 `mmap` 映射但未实际访问的文件、以及各种预留区域。

**VSS 的值通常远大于进程实际使用的物理内存。** 一个典型 Android App 的 VSS 可能达到数 GB，但这不代表它已经用了那么多内存——虚拟地址只是"我可能要用这么多"，实际用了多少要看 RSS/PSS。

所以在实际的内存分析中，**VSS 几乎没有参考价值。** 它只是反映进程的地址空间有多大，不能用来判断内存压力。

### RSS（Resident Set Size）——常驻物理内存

RSS 是进程当前占用的物理内存总量，包括私有页面和共享页面。

RSS 比 VSS 有用得多，因为它反映的是"实实在在占用了多少物理内存"。但 RSS 有一个明显的问题：**共享内存被重复计算了。** 如果系统框架的代码被 50 个进程共享，RSS 会把这份数据在每个进程里都完整算一次，导致所有进程的 RSS 加起来远大于实际物理内存总量。

因此，RSS 适合观察**单个进程**的内存变化趋势，不适合评估**系统整体**的内存消耗。

### PSS（Proportional Set Size）——按比例分摊的物理内存

PSS 的计算方式和 RSS 不同：对于共享页面，PSS 会按共享进程数均摊。比如一个 4KB 的页面被 4 个进程共享，每个进程的 PSS 只增加 1KB。

PSS 是 `dumpsys meminfo`、`/proc/<pid>/smaps` 汇总和人工分析最常用的口径，因为共享页会按比例分摊。把所有进程的 PSS 加起来，可以比较接近系统实际占用的物理内存总量。

`lmkd` 的判断口径不是逐进程看 PSS 再排序。现代 userspace `lmkd` 先看 PSI、vmpressure、file cache、thrashing 等压力信号，再按 `oom_score_adj` 选择候选；如果启用了 `kill_heaviest_task`，它还会读取 `/proc/<pid>/statm` 的 RSS 来挑更重的进程。PSS 更适合人做分析，不是 `lmkd` 的主排序字段。

**在 Perfetto 中看内存趋势时，要先确认数据源。** Perfetto 的 `linux.process_stats` 数据源提供的是 RSS 级别的计数器（`mem.rss`、`mem.rss.anon`、`mem.rss.file`、`mem.swap`），不包含 PSS。如果需要 PSS 时间序列，要靠 `dumpsys meminfo` 定时快照。抓到的是 RSS 计数器时，按 RSS 口径解释，不能把曲线当成 PSS。

### USS（Unique Set Size）——进程独有的物理内存

USS 是完全属于该进程的私有内存，不包含任何共享页面。它等于 Private Dirty + Private Clean。

USS 的实用价值在于：**如果一个进程被杀掉，USS 就是被释放的内存量。** 所以评估"杀掉这个后台进程能腾出多少内存"时，看 USS 最准确。它也是排查内存泄漏时最直接的指标——USS 的持续增长意味着进程在不断地申请独占内存而不释放。

### 四者的关系

简单来说：**VSS ≥ RSS ≥ PSS ≥ USS。** 

| 场景 | 看哪个指标 | 原因 |
|------|-----------|------|
| 判断进程对系统内存的真实压力 | PSS | 消除了共享内存重复计算的问题 |
| 判断杀掉进程能释放多少内存 | USS | 只有私有内存才会被释放 |
| 单个进程内追踪内存分配趋势 | RSS | 变化更明显，计算开销更小 |
| 大致了解进程地址空间规模 | VSS | 仅作参考，实际用途有限 |

[已验证: developer.android.com/topic/performance/memory-management；system/memory/lmkd/lmkd.cpp]
[已验证: 官方文档, source.android.com/devices/tech/debug/mm]

## 进程内存组成详解

理解 PSS/RSS/USS 之后，可以从 `adb shell dumpsys meminfo <package>` 开始看这些数字背后的具体组成：

```text
** MEMINFO in pid 12345 [com.example.myapp] **
                   Pss     Private  Private  Swapped
                 Total    Dirty     Clean    Dirty    Heap     Heap     Heap
                                 ------   ------   ------   ------   Size    Alloc     Free
  Native Heap     8848     8844        0       0     32768    11234    21534
  Dalvik Heap     7832     7828        0       0     40960    15876    25084
  Dalvik Other    1523     1500        0       0
  Stack            96       96        0       0
  Ashmem            2        0        0       0
  Gfx dev        2492     2488        0       0
  Other dev        28       28        0       0
  .so mmap       4213        8     3324       0
  .apk mmap      1634        0     1234       0
  .ttf mmap        34        0       34       0
  .dex mmap      2090        0     2090       0
  Other mmap      228        0        4       0
  EGL mtrack     1020     1020        0       0
  GL mtrack      1832     1832        0       0
  Unknown        2202     2200        0       0
  TOTAL         43102    32844     6986       0     73728    27110    46618
```

[已验证: Cubox/Android ADB命令之内存统计与分析]

[待补充：dumpsys meminfo 真机截图]

输出字段很多，可以先按几个大类理解。

### Java Heap（Dalvik Heap）

Java Heap 存放 Java/Kotlin 对象。写 `val list = mutableListOf<String>()` 时，这个 list 对象和它里面的元素就分配在 Java Heap 上。ART 虚拟机通过垃圾回收（GC）来管理这片区域——不再被引用的对象会被自动回收。

Java Heap 有一个硬性上限，这个上限因设备的总内存大小和 Android 版本而异。通过 `ActivityManager.getMemoryClass()` 可以查到常规上限（通常 128-256MB），通过 `getLargeMemoryClass()` 查到 `largeHeap` 模式下的上限。如果 App 的 Java Heap 分配量超过上限，就会抛出 `OutOfMemoryError`。

`dumpsys meminfo` 输出中，**Dalvik Heap** 那一行的 Heap Size / Heap Alloc / Heap Free 三个值分别代表：Java Heap 的总容量、已分配量、剩余空间。注意 Heap Size 并不等于 PSS——Heap Size 是虚拟机维护的堆大小，而 PSS 是实际占用的物理内存（可能因为页面共享或未实际提交而小于 Heap Size）。

### Native Heap

Native Heap 是 C/C++ 代码通过 `malloc`/`free`（或 `new`/`delete`）管理的内存。即使 App 完全用 Java/Kotlin 编写，Native Heap 也不会是 0，Android 框架和图形栈里仍有大量 native 分配。

Bitmap 像素内存的版本线要分三段看：Android 2.3.3（API 10）及更早版本放在 native memory，Android 3.0-7.1（API 11-25）放在 Dalvik / Java Heap，Android 8.0（API 26）及更高版本又回到 native heap。排查 Bitmap 相关 OOM 时，要先看设备版本，再判断压力落在 Java Heap 还是 Native Heap。

在 API 26+ 设备上，Java 层 `Bitmap` 对象释放后，对应的 native allocation 会随对象生命周期回收。它不再计入 Java Heap 上限，但仍会体现在进程的 Native Heap、RSS 和 PSS 里。

[已验证: Android Developers Managing Bitmap Memory]

Native Heap 的内存泄漏比 Java Heap 更难排查，因为没有自动的 GC 机制。常用的排查工具包括 Perfetto 的 native heap profile、`heapprofd`、以及 Android Studio 的 Native Memory Profiler。

### Code（.dex / .so / .apk）

代码段是 App 的可执行代码和资源通过 `mmap` 映射到内存的区域：

- **`.dex mmap`**：DEX 字节码文件。这是 Java/Kotlin 代码编译后的产物。这部分大多是 Private Clean 的——意味着它可以从原始的 APK 文件中重新加载，内存紧张时内核可以轻松回收这些页面。
- **`.so mmap`**：Native 共享库。包括系统的 `libc.so`、`libandroid_runtime.so` 以及 App 自带的 `.so` 文件。多个进程可以共同映射同一批 `.so` 只读代码页，每个进程的 PSS 只分摊其中一部分。
- **`.apk mmap`**：APK 文件中的资源（布局、图片、字符串等）通过 mmap 映射。和 `.dex` 类似，未修改的部分是 Clean 的。
- **`.ttf mmap`**：字体文件映射。

Code 部分的内存通常不构成优化重点（除非 App 有大量未压缩的 `.so` 文件），但理解它们的共享特性有助于准确解读 PSS 数字。

### Stack

每个线程有自己的栈空间，用于函数调用链、局部变量、返回地址等。在 Android 上，主线程和通过 `Thread` 创建的线程通常有约 1MB 的栈空间（`pthread` 默认值，不同版本可能略有差异）。

Stack 的 PSS 通常很小（几十到几百 KB），因为 `pthread` 的 1MB 默认栈只是虚拟地址空间保留——只有实际触碰的栈页（函数调用链实际到达的深度）才会进入 RSS/PSS。线程越多，VSS 越大，但物理占用取决于实际栈深度，不能把 1MB × 线程数当作稳定的 PSS 结论。不过线程数量仍然会增加内存压力：每个线程至少有一组 guard page 和已用栈页，加上页表开销，在线程数上百时会对内存造成可感知的负担。无节制的线程创建既是 CPU 调度的负担，也是内存的负担。

### Graphics（Gfx dev / EGL mtrack / GL mtrack）

Graphics 内存是显示相关的一块重要区域，包含以下几类：

- **Gfx dev**：图形设备相关的内存分配。
- **EGL mtrack**：EGL surface 相关的 GPU 内存追踪。每个 Window 的 Surface 都会占用这部分内存。
- **GL mtrack**：OpenGL/Vulkan 纹理和缓冲区的 GPU 内存追踪。

对于 UI 密集型的 App（图片浏览器、地图、视频播放器等），Graphics 内存可能占整个 PSS 的 30% 以上。在低端设备上，Graphics 内存过大会直接导致进程被 `lmkd` 杀掉。

[待补充：Perfetto 中 Graphics 内存的 Track 截图描述]

### 其他区域

除了上面几个主要区域，进程内存中还有一些不太显眼但值得了解的部分：

- **Ashmem**：Android Shared Memory，一种进程间共享内存的机制。在现代 Android 上逐渐被 `dmabuf` 替代，但在老版本和某些场景中仍在使用。
- **Unknown**：无法归类的内存映射。通常数量不大，但如果 Unknown 持续增长，可能需要通过 `/proc/<pid>/smaps` 进一步排查。
- **Dalvik Other**：ART 虚拟机内部结构占用的内存（非对象本身），包括 JIT 编译缓存、类加载器数据等。

## procfs 接口：内核暴露的内存数据

Android 的内存分析工具（`dumpsys meminfo`、Perfetto、Android Studio Profiler）底层都依赖 Linux 内核的 procfs 接口。理解这些接口有助于更深入地排查问题，尤其是在工具不直接提供所需信息时。

### /proc/meminfo：系统全局内存状态

`adb shell cat /proc/meminfo` 输出的关键字段：

```text
MemTotal:        5789412 kB    // 物理内存总量
MemFree:          123456 kB    // 完全空闲的内存（通常很少）
MemAvailable:    1234567 kB    // 可用内存（包含可回收的缓存）
Buffers:          234567 kB    // 块设备缓冲区
Cached:           890123 kB    // 页面缓存（文件映射等）
SwapTotal:        500000 kB    // ZRAM 总大小
SwapFree:         456789 kB    // ZRAM 剩余
Active:          2345678 kB    // 最近使用的内存（不太容易被回收）
Inactive:        1234567 kB    // 较久未使用的内存（更容易被回收）
```

[已验证: Cubox/Android ADB命令之内存统计与分析]

[已验证: Linux kernel documentation, kernel.org/doc/Documentation/filesystems/proc.txt]

有几个常见误区会影响判断：

**MemFree 很小不代表内存紧张。** Linux 会尽量把空闲内存用作文件缓存（Cached），因为缓存可以加速文件访问，且在需要时可以立即回收。所以看 `MemAvailable`（它包含了可回收的缓存）比看 `MemFree` 更有意义。

**Active vs Inactive** 是理解内存回收行为的关键。Inactive 列表中的页面更可能在内存压力下被回收——如果 Inactive 的比例很低，说明系统已经处于内存紧张状态。

### /proc/<pid>/status：进程级别内存摘要

`adb shell cat /proc/<pid>/status` 中与内存相关的关键字段：

```text
VmSize:    4823456 kB    // 虚拟地址空间大小（≈ VSS）
VmRSS:      123456 kB    // 常驻物理内存（≈ RSS）
VmData:      56789 kB    // 私有数据段
VmStk:         136 kB    // 主线程栈大小
VmExe:          24 kB    // 代码段
VmLib:       45678 kB    // 共享库映射
```

这个接口比 `smaps` 轻量，适合快速查看一个进程的内存概况。其中 `VmRSS` 就是前文提到的 RSS。

### /proc/<pid>/smaps：最详尽的内存映射

`/proc/<pid>/smaps` 是 Android 内存分析中最细的进程映射视图。它列出了进程中每一个内存映射区域的详细信息，包括地址范围、权限、PSS/RSS/USS 等分项数据。

```text
7a3b400000-7a3b800000 rw-p 00000000 00:00 0       [anon:dalvik-LinearAlloc]
Size:           4096 kB         // 映射的虚拟大小
KernelPageSize:     4 kB
MMUPageSize:        4 kB
Rss:             512 kB         // 该区域的 RSS
Pss:             512 kB         // 该区域的 PSS
Pss_Anon:        500 kB
Pss_File:         12 kB
Pss_Shmem:         0 kB
Shared_Clean:      0 kB
Shared_Dirty:      0 kB
Private_Clean:     0 kB
Private_Dirty:   512 kB         // 该区域的 Private Dirty
Referenced:       512 kB
Anonymous:        500 kB
LazyFree:           0 kB
AnonHugePages:      0 kB
ShmemPmdMapped:     0 kB
Shared_Hugetlb:     0 kB
Private_Hugetlb:    0 kB
Swap:               0 kB
SwapPss:            0 kB
Locked:             0 kB
```

上面这个片段按 4 KB page 设备展示。Android 15 开始，AOSP 支持 16 KB page size 设备。到这类设备上，`KernelPageSize`、`MMUPageSize` 以及很多 `Rss` / `Pss` 增量都会按 16 KB 粒度出现，`mmap` offset 粒度和 native 库页面边界要求也会变化。

smaps 的实际使用场景通常是：**当发现进程的 PSS 异常高，但 `dumpsys meminfo` 的分类无法定位具体原因时，逐项查看 smaps 来找到那个异常大的映射区域。**跨设备比对 `smaps`、Perfetto 内存曲线或 native 崩溃现场时，用 `adb shell getconf PAGE_SIZE` 或 `smaps` 里的页大小字段确认当前页大小，再解释页粒度带来的页内碎片、页表开销和 PSS / RSS 跳变。

16 KB 页环境下页内碎片会增加：被触碰并提交的匿名页、`mmap` 页面和 allocator span 会按 16 KB 粒度进入 RSS/PSS；多个小对象仍可能共享同一页，不能把“1 KB 对象”理解成必然独占 16 KB。全系统总 PSS 通常上涨 5% 到 10%。这是架构层面的正常开销，不代表应用存在泄漏。跨版本或跨设备对比 PSS 基线时，需要先确认页大小，再判断增量是否在合理范围内。

读取 `/proc/<pid>/smaps` 需要足够的权限（通常是 root，或者目标 App 是 debuggable 的），且读取操作本身有性能开销（内核需要遍历所有页表），不建议在高频循环中调用。

[已验证: Linux kernel documentation, kernel.org/doc/Documentation/filesystems/proc.txt / Android Developers 16 KB page size]

## dumpsys meminfo：日常内存分析的主力工具

<!-- AIW-源码调研-2026-06-06 -->

### HPROF 堆转储分析

Android 的堆转储要分两条路径看：`am dumpheap` 通过 ActivityManager 转发到目标进程；Perfetto 的 ART heap dump 数据源从 Android 11 起提供引用图采集，Android 14 起可以配合 OOM trigger 等待 `OutOfMemoryError`。Android 17 的 app memory limits 命中后，开发者侧更适合用 `ProfilingTrigger.TRIGGER_TYPE_ANOMALY` 或事后 `ApplicationExitInfo` 判断触发原因。

#### Shell 命令层 (`am dumpheap`)

基础命令用于触发堆转储：
```bash
# Java 堆 dump（包含 GC 数据）
adb shell am dumpheap -g <pid> /data/local/tmp/heap.hprof

# Native 堆 dump
adb shell am dumpheap -n <pid> /data/local/tmp/native-heap.hprof

# Malloc 信息 dump
adb shell am dumpheap -m <pid> /data/local/tmp/malloc-info.txt
```

#### 三层调用架构

1. **Shell 命令** → ActivityManagerService.dumpHeap()
   - 需要高危权限 `SET_ACTIVITY_WATCHER`
   - 调用 `enableFreezer(false)` 避免干扰

2. **AMS 层** → ActivityThread.dumpHeap()
   - 异步执行，避免阻塞主线程
   - 支持完成回调通知机制

3. **ART 层** → Hprof::Dump()
   - 双重保护机制：
     ```cpp
     gc::ScopedGCCriticalSection gcs(self, gc::kGcCauseHprof, gc::kCollectorTypeHprof);
     ScopedSuspendAll ssa(__FUNCTION__, true /* long suspend */);
     ```
   - 输出标准 JAVA PROFILE 1.0.3 格式

#### Perfetto ART heap dump（Android 11+；OOM trigger Android 14+）

Perfetto 的 `android.java_hprof` 数据源从 Android 11 起可用。它采集 ART 堆引用图，不等同于 `am dumpheap` 导出的标准 HPROF 对象数据：

**配置数据源**：
```proto
message JavaHprofConfig {
    message ContinuousDumpConfig {
        optional uint32 dump_interval_ms = 2;   // 连续导出间隔
        optional bool scan_pids_only_on_start = 3;  // 进程扫描策略
    }
    repeated string process_cmdline = 1;  // 目标进程
    optional ContinuousDumpConfig continuous_dump_config = 3;
    optional uint32 min_anonymous_memory_kb = 4;  // 内存下限过滤
}
```

**解析流程**：
1. ART heap dump 数据源把 Java 对象引用图写入 Perfetto trace。
2. Trace Processor 导入 heap graph 数据。
3. SQL 层通过 `heap_graph_class`、`heap_graph_object`、`heap_graph_reference` 查询。
4. Perfetto UI 在 Heap Profile track / Heap Dump Explorer 中展示这些对象关系。

#### 内存分析实践

**配置连续监控**：
```bash
# 采集 ART heap dump 引用图，输出为 Perfetto trace
cat <<'EOF' | adb shell perfetto -c - --txt -o /data/misc/perfetto-traces/java-heap.pftrace
buffers: { size_kb: 65536 fill_policy: DISCARD }
duration_ms: 30000
data_source_stop_timeout_ms: 100000
data_sources: {
  config {
    name: "android.java_hprof"
    java_hprof_config {
      process_cmdline: "com.example.app"
      continuous_dump_config { dump_interval_ms: 5000 }
    }
  }
}
EOF
adb pull /data/misc/perfetto-traces/java-heap.pftrace .
```

**数据解读**：
- **托管堆 dump**: 包含对象引用关系，用于内存泄漏分析
- **Native 堆 dump**: 重点关注内存碎片和大块分配
- **Malloc 信息**: 系统层内存分配模式分析

#### 性能影响

堆转储会对应用性能产生以下影响，具体数值取决于堆大小、对象数量、设备 I/O 和是否触发 GC：
- **线程暂停**：`am dumpheap` 的 Java HPROF 路径会进入 GC critical section 并执行 `ScopedSuspendAll`，停顿随堆规模变化。
- **内存 / CPU 开销**：Perfetto ART heap dump 和 native heap profiling 都会消耗额外 buffer 与解析资源，连续采集要控制间隔和目标进程。
- **I/O 压力**：`am dumpheap` 直接写文件描述符；Perfetto 写 `.pftrace` 到 `/data/misc/perfetto-traces/` 后再 pull。

**优化建议**：
- 在非关键时间点进行 dump
- 避免在性能敏感期连续多次调用
- 使用过滤条件减少导出数据量

[已验证: AOSP android-16.0.0_r1 ActivityManagerShellCommand / ActivityManagerService / ActivityThread / art/runtime/hprof/hprof.cc；Perfetto ART heap dump 与 OOME docs]

前面已经多次用到 `dumpsys meminfo` 的输出，这里把它的用法系统地过一遍。

### 全局模式：查看系统内存概况

```bash
adb shell dumpsys meminfo
```

全局模式输出几个关键信息：

1. **系统级内存统计**：Total RAM、Free RAM、Used RAM、Lost RAM、ZRAM 使用情况。这可以快速判断当前设备的内存压力等级。
2. **按 OOM 优先级分类的 PSS 汇总**：Native、System、Persistent、Visible、Perceptible、Cached 等各类别的总 PSS。
3. **按内存类型分类的 PSS 汇总**：Native Heap、Dalvik、`.art mmap`、`.oat mmap`、Gfx dev 等。

如果 "Used RAM" 占比很高、Free RAM 很低、ZRAM 使用率很高，说明设备已经处于内存压力之下，后台 App 很容易被 `lmkd` 杀掉。

[已验证: Cubox/Android ADB命令之内存统计与分析]

### 单进程模式：深入分析某个 App

```bash
adb shell dumpsys meminfo com.example.app
```

单进程模式是日常排查里最常用的形式。输出的关键区域：

**App Summary 段**——这是最快能看懂的部分：

```text
                   Pss(KB)
  Java Heap:      15234
  Native Heap:     8488
  Code:            8352
  Stack:             96
  Graphics:        4002
  Private Other:   1120
  System:          6789
```

[已验证: Cubox/Android ADB命令之内存统计与分析]

这些分类是对详细输出区域的聚合。排查问题时重点关注：

- **Java Heap 突然增长**：可能有 Java 层的内存泄漏。进一步用 Android Studio 的 Heap Dump 分析。
- **Native Heap 持续增长**：可能有 native 层的内存泄漏。用 `heapprofd` 或 Perfetto 的 Native Heap Profile 追踪。
- **Graphics 占用异常高**：可能有大量 Bitmap 未释放、GL 纹理泄漏。检查图片加载库的缓存配置。

**Objects 段**——展示 App 中各种对象的数量：

```text
Objects
         View:        256        Activity:          4
      AppContext:         12       ContextImpl:         12
       AssetManager:         12    RuntimeAsset:         12
        AssetManager:          0        Bitmap:        128
```

这一段对排查 View 泄漏和 Activity 泄漏特别有用。如果退出 Activity 后 View 数量没有减少，那就是泄漏了。

### 实用技巧

**1. 对比前后两次快照**

```bash
# 操作前
adb shell dumpsys meminfo com.example.app > before.txt
# 执行一系列操作（如打开/关闭某个页面 10 次）
# 操作后
adb shell dumpsys meminfo com.example.app > after.txt
# 对比
diff before.txt after.txt
```

重点关注 PSS Total、Java Heap、Native Heap 的变化。如果反复操作后数字只增不减，就是泄漏。

**2. 触发 GC 后再采集**

Java Heap 的增长有时只是还没来得及 GC。可以先触发内存回收再采集：

```bash
adb shell am send-trim-memory com.example.app TRIM_MEMORY_COMPLETE
# 等待几秒
adb shell dumpsys meminfo com.example.app
```

[已验证: Cubox/Android ADB命令之内存统计与分析]

**3. 在 Perfetto 中看内存**

Perfetto 的 `linux.process_stats` 数据源会周期性采集进程的 RSS、swap 等数据（计数器包括 `mem.rss`、`mem.rss.anon`、`mem.rss.file`、`mem.swap`），可以在时间轴上直观地看到内存变化趋势。这比 `dumpsys meminfo` 的瞬时快照更适合分析"内存增长发生在什么时候"。如果需要 PSS 维度的趋势数据，要单独采集 `dumpsys meminfo` 快照序列，`linux.process_stats` 不提供 PSS。

[待补充：Perfetto 内存面板截图]

[已验证: 官方文档, developer.android.com/studio/profile/investigate-ram]
[已验证: Perfetto 官方文档, perfetto.dev/docs/data-sources（linux.process_stats / linux.sys_stats 计数器定义）]

## cgroup 对 Android 内存控制的作用

cgroup（Control Group）是 Linux 内核提供的资源隔离机制。Android 从早期版本就开始使用 cgroup v1 来管理进程组，Android 10 引入了 cgroup 抽象层，支持 v1/v2 双栈。

在内存管理方面，cgroup 的核心作用是：

**按进程组施加内存约束。** Android 10 之后，framework 通过 `cgroups.json` / `task_profiles.json` 给进程或线程套 profile。内存字段要分 controller 版本看：v1 的硬限制是 `memory.limit_in_bytes`，v2 对应 `memory.max`；v1 的软限制是 `memory.soft_limit_in_bytes`，v2 对应 `memory.low`。`memory.high` 是 cgroup v2 的回收节流阈值，但不是 Android 10+ 所有设备都统一使用的字段。

**配合 lmkd 观察压力。** `lmkd` 的压力输入来自 PSI 或 vmpressure。`memory.pressure_level` 是 cgroup v1 memory controller 的接口，通常和 `cgroup.event_control` 配合使用；在 v2 场景，更常见的是 `memory.events` 一类统计接口和 PSI 监控。`lmkd` 拿到压力信号后，再结合 `oom_score_adj` 和 heaviest-task 策略决定回收对象。

**ActivityManager 与 cgroup 的协作。** App 前后台切换时，framework 会通过 libprocessgroup / task profile 调整进程所属 cgroup、CPU/内存属性和 `oom_score_adj`。这里改变的是系统回收优先级与资源保护程度，不是给某个 App 单独发一个“更容易换出到 ZRAM”的开关。

[已验证: source.android.com/docs/core/perf/cgroups；system/core/libprocessgroup/profiles/task_profiles.json]

## ZRAM：在内存中做 Swap

Android 不使用传统磁盘 Swap，主要原因是闪存写入寿命有限，且 IO 延迟高。ZRAM 的思路是在内存中创建一个压缩块设备——把不活跃的内存页压缩存储，腾出更多可用空间。

### ZRAM 的工作方式

当系统内存紧张时，后台回收路径会把匿名页面换出到 swap 设备；如果设备启用了 ZRAM，这些页会先被压缩后写进 ZRAM。`kswapd` 负责后台回收和换出，但页被再次访问时，解压和换入发生在 page fault 触发的 swapin 路径，不是 `kswapd` 主动把页搬回内存。

ZRAM 的大小、压缩算法和 swappiness 都是 OEM 按机型配置的，没有通用的统一比例。常见算法是 `lz4` 或 `lz4hc`，实际压缩率取决于页面可压缩性、前后台负载和匿名页类型。读 `dumpsys meminfo` 或 `/sys/block/zram0/` 时，以当前设备的 `physical used`、原始换出量和压缩占用为准，不要拿一台机器的经验当成通用公式。

### 在 dumpsys meminfo 中看 ZRAM

全局 `dumpsys meminfo` 的输出中有 ZRAM 相关行：

```text
ZRAM:  123,456K physical used for 456,789K in swap (500,000K total swap)
```

这行数据包含三个指标，含义不同：`123MB physical used` 是压缩后实际占用的 RAM；`456MB in swap` 是未压缩的换出量（`SwapUsed`）；`500MB total swap` 是 ZRAM 设备可容纳的未压缩 swap 容量。压缩效率看前两者的比值（456/123 ≈ 3.7x）；RAM 开销看 `physical used`；容量压力看 `in swap` 是否接近 `total swap`——当换出量接近总容量时，ZRAM 无法接纳更多页面，系统会更积极地杀后台进程。不要把 `physical used` 与 `total swap` 对比来判断容量压力，两者口径不同。

### ZRAM 的性能代价

压缩和解压需要 CPU 周期。在低端设备上，频繁的 ZRAM 换入换出可能导致 UI 卡顿——因为前台进程在访问被压缩的页面时需要等待解压完成。这在 Perfetto 中表现为意外的 CPU 占用和短暂的非预期延迟。

[已验证: source.android.com/docs/core/perf/lmkd]
[已验证: docs.kernel.org/admin-guide/blockdev/zram.html]

## 在 Perfetto 中的表现

把前面的内存概念放到 Perfetto Trace 里，主要看下面几类数据。

### 内存相关的 Track

- **`linux.process_stats`**：按进程周期性采集 `mem.rss`、`mem.swap` 等 per-process 计数器，是看内存增长趋势的主要数据源。Perfetto UI 中表现为进程级别的内存轨道，SQL 层通过 `counter` + `process_counter_track` 表查询。
- **`linux.sys_stats`**：采集 `/proc/meminfo` 中的系统级内存指标（`MemAvailable`、`SwapUsed`、`Cached` 等），用于观察系统整体内存压力。
- **`android.java_hprof` / `android.java_hprof.oom`**：Java Heap Dump 数据源，需要在 TraceConfig 中显式启用，触发后生成 heap dump 用于离线分析。

注意区分数据源名称与 UI 轨道名称：上面列出的是 TraceConfig `data_sources` 配置项，Perfetto UI 中的轨道名称和 SQL 表名不一定与数据源同名。

### 常见模式识别

**正常 App：** PSS 在启动后达到一个稳定值，操作时小幅波动，返回后回落。

**内存泄漏 App：** PSS 随操作次数单调递增，每次打开同一个页面都会叠加一层内存，永不回落。

**内存压力下的系统：** `MemAvailable` 持续下降，ZRAM 使用率上升，后台进程被杀事件（`lmkd` kill events）频繁出现。在 Perfetto 中可以在 `Event` track 上看到 `am_proc_died` 事件。

[待补充：Perfetto 中内存泄漏和内存压力的 Trace 截图]

## 常见问题与误区

### 误区一："PSS 就是 App 占用的全部内存"

PSS 接近"App 对系统的内存压力"这个口径，但它包含了按比例分摊的共享库内存。如果要评估"杀掉这个进程能释放多少内存"，应该看 USS（Private Dirty + Private Clean），而不是 PSS。

### 误区二："Java Heap 超过限制就 OOM"

这句话只能覆盖一部分版本。Android 2.3.3 及更早版本，Bitmap 像素在 native memory；Android 3.0-7.1，像素回到 Dalvik / Java Heap，Bitmap 更容易直接推高 Java Heap；Android 8.0 及更高版本，像素又回到 native heap。

判断 OOM 时，要一起看 Java Heap、Native Heap 和图形缓冲区，而不是只盯 `getMemoryClass()`。API 26+ 之后，Native Heap 的内存增长也不受 `getMemoryClass()` 直接约束，它更受系统整体内存和 `lmkd` 行为影响。

### 误区三："MemFree 很低就是内存不够"

Linux 会积极使用空闲内存做文件缓存。`MemFree` 低不代表内存紧张，应该看 `MemAvailable`——它包含了可以立即回收的缓存内存。

### 误区四："VSS 很大说明内存泄漏"

VSS 是虚拟地址空间，不是物理内存使用量。一个刚启动的 App 的 VSS 就可能有好几 GB。VSS 大是正常的，不看 VSS。

### 误区五："后台进程不占内存所以不需要优化"

后台进程的 USS 可能不多（因为大部分页面是共享的），但它的 PSS 仍然计入系统总内存。当系统内存紧张时，大量后台进程累积的 PSS 会加速 `lmkd` 杀进程的速度，影响前台 App 的稳定性。

## 参考资料

- [Investigate your app's RAM usage](https://developer.android.com/studio/profile/investigate-ram) — Android 官方文档
- [Managing Your App's Memory](https://developer.android.com/topic/performance/memory) — Android 官方文档
- [Low Memory Killer Daemon](https://source.android.com/docs/core/perf/lmkd) — AOSP 文档
- [Cgroups in Android](https://source.android.com/docs/core/perf/cgroups) — AOSP 文档
- [procfs documentation](https://kernel.org/doc/Documentation/filesystems/proc.txt) — Linux 内核文档
- [ZRAM documentation](https://kernel.org/doc/Documentation/blockdev/zram) — Linux 内核文档
- [Perfetto Process Memory Data Source](https://perfetto.dev/docs/data-sources) — Perfetto 官方文档
- `frameworks/base/core/java/android/app/ActivityManager.java` — AOSP 源码
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java` — lmkd 相关源码

[适用版本: Android 8 (API 26) - Android 17 (API 37)]
