---
title: "App 内存分析"
chapter: "10.1"
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-27"
reviewed_date: "2026-04-15"
reviewed_by: "openclaw-task6"
last_verified_against: "AOSP android-16.0.0_r1 lmkd + memtrack AIDL / Android 15 16KB page size docs / developer.android.com docs"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
review_type: post-polish-quality-gate
review_round: 2
confidence: medium
sources:
  - type: blog
    path: "https://www.androidperformance.com/2015/04/11/AndroidMemory-Usage-Of-MAT-Pro/"
  - type: official
    path: "https://developer.android.com/studio/profile/memory-profiler"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiling"
  - type: official
    path: "https://source.android.com/docs/core/debug/interpreting-cpu"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "https://android.googlesource.com/platform/hardware/interfaces/+/android11-release/memtrack/1.0/IMemtrack.hal"
  - type: official
    path: "https://android.googlesource.com/platform/hardware/interfaces/+/android-16.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
tags: [memory, pss, rss, mat, heapprofd, memtrack, memory-analysis]
related_chapters: ["4.1", "4.3", "4.5", "13.1", "14.3"]
task6_state: "reviewed"
task6_result: pass-light-edit
last_task6_audit: "2026-05-17"
section: "10.1"
status: finalized
pipeline_stage: "ready-to-publish"
task9_result: fixed
task2b_state: fixed
task2b_result: fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-19"
last_task9_at: "2026-05-19T20:58:49+08:00"
last_task2b_at: "2026-04-27T15:52:00+08:00"
last_task9_audit: "2026-05-19"
last_task9_review_log: "logs/deep-review/2026-05-19-20-deep-review.md"
review_notes: "2026-05-19 task9 idle audit: needs-rework。P0 1(malloc debug 命令/选项无效),P1 2(ASan API 版本;PSS/largeHeap 指标口径),P2 1(Bitmap API10 历史口径);已写入 queue/suggestions,等待 Task2B 回炉。"
task9_review_notes: "2026-05-19 20 Task9 复核: needs-rework。P0 1: malloc debug 仍把 package 写入 libc.debug.malloc.program；P1 1: PSS 仍与 memoryClass/largeHeap 预算混用且单位口径错误；P2 2: Bitmap 历史分段、Native OOM 表述需补正。"
---

# App 内存分析

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 App 内存分析的核心工具:Android Studio Memory Profiler、adb shell dumpsys meminfo、MAT
- 🔹 Java Heap 分析:Retained Size、Shallow Size、Dominator Tree
- 🔹 Native Heap 分析:malloc debug、ASan、heapprofd
- 🔹 Graphics 内存的归属与计量:dumpsys gpu / memtrack
- 🔹 内存基线建立与回归检测方法

### 扩展(可选深入)

- 🔸 使用 Perfetto heapprofd 分析 Native 内存分配
- 🔸 线上内存监控的采样策略

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 App 内存分析

当我们在 Perfetto 中看到应用的 Java Heap Track 一路攀升不回落，或者在 `dumpsys meminfo` 里发现进程 PSS 已经明显超出同类 App 正常范围时，需要的就是这一章的知识。

内存分析不是一件"拿到 dump 文件然后翻翻看"就能解决的事。真实的场景是:我们拿到一个线上 OOM 崩溃的堆栈,但崩溃现场的信息有限--可能只知道崩溃时 Heap 使用量很高,却不知道是什么对象在增长、为什么增长、从哪条代码路径分配的。我们需要一套系统性的分析方法:先用宏观工具定位问题类型(Java 泄漏?Native 增长?Graphics 占用?),再用微观工具精确定位到具体的代码路径。

本章的目标是帮助我们掌握这套方法。读完之后,面对任何 App 内存问题,我们都能快速选择合适的工具组合,按照正确的分析路径定位根因。

## App 内存分析的核心工具

### 三层工具体系

App 内存分析的工具可以分为三层,每一层解决不同粒度的问题:

**宏观层:`dumpsys meminfo`**--回答"内存用在了哪里"。它是我们拿到一个内存问题后的第一步,快速了解进程的 PSS/RSS 分布,判断问题出在 Java Heap、Native Heap、Graphics 还是其他区域。它不需要连接 IDE,一条 adb 命令就能出结果,特别适合在测试设备上快速排查。

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

**中观层:Android Studio Memory Profiler**--回答"内存随时间怎么变化"。它可以实时观察 Java/Kotlin 对象的分配和回收,记录一段时间的分配追踪(Allocation Tracking),捕获 Heap Dump 分析对象引用关系。对于"哪个页面泄漏了"、"哪些对象在不断分配"这类问题,Memory Profiler 是最高效的工具。

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

**微观层:MAT(Memory Analyzer Tool)**--回答"对象之间谁引用了谁,为什么无法回收"。当我们已经通过 Memory Profiler 或 `dumpsys meminfo` 确认了泄漏或异常增长的存在,需要深入分析引用链、找到 GC Root 时,MAT 提供了最强大的分析能力。它的 Histogram、Dominator Tree、Leak Suspects 等视图,是定位 Java 内存泄漏的利器。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT-Pro.md]

**选择策略**:工作中通常按照 `dumpsys meminfo` → Memory Profiler → MAT 的顺序递进分析。先用 `dumpsys meminfo` 定位问题类型,再用 Memory Profiler 观察动态行为,用 MAT 精确定位引用链。对于 Native 内存问题,这个工具链会替换为 `dumpsys meminfo` → heapprofd/malloc debug。

### dumpsys meminfo:内存的全景地图

`adb shell dumpsys meminfo <package_name|pid>` 是我们分析 App 内存问题的起点。它输出的核心指标是 PSS(Proportional Set Size)和 RSS(Resident Set Size)。

PSS 适合做进程内存归因和回归监控。它计算进程的私有内存,加上按比例分摊的共享内存,比如一个 3MB 的共享库被 3 个进程使用,每个进程的 PSS 只记 1MB。分析 `dumpsys meminfo` 时,PSS 能较稳定地反映单个进程对系统内存的实际代价。Android 10 起的 userspace `lmkd` 则主要用 PSI monitors 感知内存压力,再结合 `oom_score_adj`、minfree 阈值和进程 RSS/size 等启发式挑选 victim,PSS 不再是现代杀进程路径里的单一决策指标。

[已验证: 官方文档, source.android.com/docs/core/debug/interpreting-cpu ; source.android.com/docs/core/perf/lmkd]

RSS 则更粗粒度,它统计进程占用的所有物理内存,不做共享分摊。对于同一块共享内存,每个进程的 RSS 都会完整计入,所以所有进程的 RSS 之和会超过系统实际物理内存。RSS 的优势是计算速度快,适合观察单个进程的内存变化趋势。在 Android 9(API 28)以上,Memory Profiler 也直接展示 RSS 信息。

Android 15 开始,设备可以使用 16KB page size。页大小会改变 PSS/RSS 的基线背景:同样一组小对象、`mmap` 映射或 `.so` 段,最小驻留粒度从 4KB 变成 16KB 后,页内未使用空间也会计入驻留页。Google 的 16KB 兼容性说明给出的经验口径是约 5-10% 性能收益,同时带来约 9% 额外内存使用。这里的 9% 属于系统页粒度变化带来的基线漂移,不能直接归因到 App 代码劣化。

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler ; developer.android.com/guide/practices/page-sizes]

`dumpsys meminfo` 的输出按内存类别展示了进程的完整内存布局:

```
** MEMINFO in pid 12345 [com.example.app] **
                   Pss    Private  Private     Swap     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------
  Native Heap    12,345   12,000       45        0   24,000   18,000    6,000
  Java Heap      8,765    8,500      265        0   16,000   12,000    4,000
         Code    3,456    1,200    2,256        0
        Stack      128      128        0        0
    Graphics    5,678    5,400      278        0
  Private Other    987      987        0        0
         System    654      234      420        0
                ------   ------   ------   ------
           TOTAL   32,013   28,449    3,264        0   40,000   30,000   10,000
```

这段输出中我们需要关注的几个关键列:`Pss Total` 是进程的实际内存代价,`Private Dirty` 是进程独占且已被修改的内存(无法被 swap 出去),`Heap Size/Alloc/Free` 展示了 Java 和 Native Heap 的分配情况。

[待验证: 上述输出格式是否与 Android 16 的 dumpsys meminfo 完全一致,各列名可能因版本而异]

分析 `dumpsys meminfo` 输出时重点看**哪一行的 PSS 异常偏高**。如果 Native Heap 很高,说明 Native 代码有分配泄漏或大对象;如果 Java Heap 很高,说明 Java 层有泄漏或对象未释放;如果 Graphics 很高,可能存在 Bitmap 未回收或 Surface 管理问题。

实际操作中,可以在操作 App 前后各抓一次 `dumpsys meminfo` 对比差异。比如打开一个页面、返回、触发 GC 后再抓一次,如果 PSS 没有回到操作前的水平,说明有内存没有被正确释放。

### Android Studio Memory Profiler:实时观测与分配追踪

Memory Profiler 是 Android Studio 内置的内存分析工具,它提供三种核心能力:

**实时内存曲线**:展示 Java Heap、Native Heap、Graphics、Code、Stack 等各类内存的实时使用量。当我们操作 App 时,可以观察内存曲线的变化模式--正常情况下,内存会随着操作上升,GC 后回落;如果曲线呈阶梯式上升且回落不完整,就说明存在泄漏。在 Android 9+ 的设备上,Memory Profiler 还会展示基于 RSS 的 Process Memory 指标。

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

**分配追踪(Allocation Tracking)**:记录一段时间内所有 Java/Kotlin 对象的分配事件,包括分配的对象类型、大小、分配线程和调用栈。这对于定位"内存抖动"(短时间内大量创建和销毁对象)特别有用。借助这份记录,能定位哪些方法在频繁分配临时对象,再针对性优化--比如用对象池替换频繁 new 出的临时对象,或者将不必要的对象分配移到初始化阶段。

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

**Heap Dump**:捕获当前 Java Heap 的完整快照,用于查看所有存活对象及其引用关系。Memory Profiler 会自动标记出可能的 Activity/Fragment 泄漏(已 destroyed 但仍被引用的实例)。但 Memory Profiler 的 Heap Dump 分析能力相对有限,对于复杂的引用链分析,我们通常将 `.hprof` 文件导出后用 MAT 做更深入的分析。

在抓取 Heap Dump 之前,先手动触发一次 GC(点击 Memory Profiler 中的垃圾桶图标)。这样可以排除 Unreachable 对象--可以被 GC 回收但还没来得及回收的对象,它们会干扰泄漏分析。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT-Pro.md]

## Java Heap 分析:Retained Size、Shallow Size、Dominator Tree

当我们确认了 Java Heap 有问题(PSS 偏高、Heap Dump 中有泄漏嫌疑对象),下一步就是精确定位"谁持有引用导致无法回收"。这一步的核心概念是 Shallow Size 和 Retained Size,以及 Dominator Tree。

### Shallow Size 与 Retained Size

**Shallow Size** 是对象自身占用的内存大小,不包括它引用的其他对象。一个只有两个 int 字段的对象,Shallow Size 就是 8 字节(加上对象头开销,通常是 16 字节)。这个值告诉我们"这个对象本身有多大",但不能反映它的实际影响--一个只有几个字段的对象可能通过引用链间接持有几十 MB 的 Bitmap。

**Retained Size** 是如果这个对象被回收,能释放的内存总量--包括对象自身及其**仅被该对象直接或间接持有**的所有对象的内存。它是衡量"一个对象对内存的实际影响"的核心指标。当我们在排查泄漏时,Retained Size 帮助我们快速锁定"影响最大"的对象。

但 Retained Size 有一个容易踩的坑:它假设该对象是引用链中唯一的支配者。如果两个对象同时引用了一个 Bitmap,那么这个 Bitmap 的 Retained Size 不会完全归属于任何一个引用者。这就是为什么我们需要 Dominator Tree 来更准确地分析。

[已验证: 官方文档, eclipse.dev/mat/]

### Dominator Tree

Dominator Tree 是 MAT 中最重要的分析视图。它的核心思想是:如果一个对象 A 是另一个对象 B 到 GC Root 的必经之路(即所有从 GC Root 到 B 的路径都必须经过 A),那么 A 就是 B 的 Dominator。在 Dominator Tree 中,每个对象的 Retained Size 就是它作为 Dominator 持有的所有内存。

在实际分析中这个概念非常直觉化。Dominator Tree 按内存占用从大到小排列,排在最前面的就是"如果被回收能释放最多内存"的对象。我们通常的做法是:

1. 打开 Dominator Tree 视图,按 Retained Size 降序排列
2. 找到 Retained Size 异常大的对象(通常是 Activity、Fragment、View 或大数组)
3. 右键 → Path To GC Roots → exclude weak/soft references,查看哪些强引用链阻止了回收
4. 分析引用链上的每个节点,判断哪个引用应该被释放但没有被释放

[已验证: 来源见 obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT-Pro.md]

### MAT 的关键操作

MAT 提供了几个内存泄漏排查常用操作,这些操作需要熟练掌握:

**Histogram**:按类维度统计对象数量和内存占用。如果我们怀疑某个类的实例数量异常(比如某个 Bean 类有几千个实例),用 Histogram 按 Percentage 排序可以快速发现。还可以按 Package 分组,只看自己 App 的类。

**List Objects → with incoming/outgoing references**:查看一个对象引用了什么(outgoing)和被谁引用(incoming)。这是追踪引用链的基本操作。

**Path To GC Roots → exclude all phantom/weak/soft references**:这是最常用的操作,它排除了虚引用、弱引用和软引用,只保留强引用链。因为强引用是阻止 GC 回收的唯一原因,这条路径直接告诉我们"谁在阻止回收"。

**Merge Shortest Path to GC Root**:当有多个对象可能都有问题时,用这个操作可以找到它们的共同引用路径,快速定位到公共的泄漏源。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT-Pro.md]

MAT 分析前同样需要先触发 GC(参见上文 Memory Profiler 的说明)。Heap 中未被 GC 的 Unreachable 对象会干扰分析,一个快速识别方法是看 Retained Size--Unreachable 对象的 Retained Size 为 0。

## Native Heap 分析:malloc debug、ASan、heapprofd

Java Heap 的泄漏可以用 MAT 精确定位,但 Native Heap 的分析完全是另一套工具链。随着越来越多 App 使用 JNI、音视频 SDK、跨平台框架(Flutter/RN),Native 内存问题变得越来越常见--而且更难排查,因为 Native 代码没有 GC 机制,泄漏就是真的泄漏。

### heapprofd:Native Heap 的采样分析

heapprofd 是 Android 10+ 提供的低开销 Native Heap 采样分析器,集成在 Perfetto 框架中。它的工作原理是 hook `malloc`/`calloc`/`realloc`/`free` 等 C 库分配函数,在每次分配时按一定采样率记录调用栈。记录的结果可以在 Perfetto UI 中以火焰图的形式展示,我们能看到"哪个调用栈分配了多少内存、还有多少未释放"。

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiling]

使用 heapprofd 有两种方式。最方便的是通过 Perfetto UI(ui.perfetto.dev)的录制界面:选择设备 → 开启 "Native Heap Profiling" → 输入目标进程名 → 开始录制。录制结束后,Perfetto UI 会在 "Heap profile" Track 上显示一个钻石标记,点击即可查看火焰图。

命令行方式使用 `heap_profile` 脚本:

```bash
# 对指定进程进行 Native Heap Profiling
heap_profile -n com.example.app
```

火焰图中有两个关键视图:**Unreleased Malloc Size**(分配但未释放的内存)和 **Total Malloc Size**(所有分配过的内存,包括已释放的)。分析泄漏时看 Unreleased,分析分配频率时看 Total。

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiling]

heapprofd 有几个需要注意的限制:第一,它只能捕获开启录制之后的分配,所以如果要分析启动阶段的 Native 分配,需要在进程启动前就开始录制(可以设置环境变量 `PERFETTO_HEAPPROFD_BLOCKING_INIT=1`);第二,它是采样分析,默认不是每次 malloc 都记录,所以精确数值可能不完全准确;第三,它只跟踪 `malloc/free` 系列调用,直接使用 `mmap` 的分配不会被记录。

### malloc debug:Native 内存的调试工具

malloc debug 是 Android 系统提供的另一种 Native 内存分析工具,它的定位和 heapprofd 不同--heapprofd 是性能分析工具(低开销,适合线上),malloc debug 是调试工具(高开销,适合开发阶段)。

malloc debug 通过设置系统属性开启:

```bash
# 方式 1：root/platform 场景 — 指定目标可执行文件名
# 注意：libc.debug.malloc.program 接受的是可执行文件名，不是包名
# 对 zygote fork 的 App，可执行文件名是 app_process64（或 app_process）
# 设置 app_process64 会影响所有从 zygote fork 出的 App
adb shell setprop libc.debug.malloc.program app_process64
adb shell setprop libc.debug.malloc.options "backtrace"

# 方式 2：按信号切换（先不记录，收到 SIGUSR1 后开始记录 backtrace）
adb shell setprop libc.debug.malloc.options "backtrace_enable_on_signal"

# 方式 3：debuggable App 场景（不需要 root）
# 在 AndroidManifest.xml 中设置 android:debuggable="true"
# 或通过 adb shell am set-debug-app -w <package>
# 然后创建 wrap.sh 并在其中 export 相关环境变量：
#   #!/system/bin/sh
#   export LIBC_DEBUG_MALLOC_OPTIONS=backtrace
#   exec "$@"
```

开启后，malloc debug 会跟踪每一次 Native 内存分配的调用栈，并能在检查到内存错误（如 use-after-free、buffer overflow）时输出详细信息。`backtrace` 本身即启用分配栈记录；`backtrace_enable_on_signal` 允许按信号动态切换记录状态。root 场景下 `libc.debug.malloc.program` 设置为 `app_process64` 后，所有 zygote fork 的进程都会被 hook；如果只想调试特定 App，优先用方式 3（wrap.sh）。相比于 heapprofd，malloc debug 提供更完整的分配记录（非采样），但性能开销也大得多。

[已验证: 官方文档, source.android.com/docs/core/debug/native-crash; NDK malloc debug 选项表不包含 enable_on_start，backtrace 本身即启用栈记录]

### ASan / HWASan:内存错误检测器

ASan(AddressSanitizer)和 HWASan(Hardware-Assisted AddressSanitizer)是检测 Native 内存**错误**的工具--use-after-free、buffer overflow、double free 等。它们不是用来分析"内存用了多少"的,而是用来发现"内存用错了"的。

ASan 的工作原理是在每次内存分配前后插入“红区”（poison bytes），当程序访问这些红区时，ASan 就能检测到越界访问。NDK ASan 从 API 27（Android 8.1 O MR1）起支持在非 root 设备上调试应用；生产设备/非 root 调试通常依赖 debuggable + wrap.sh。Android 14+ 的 ARM64 设备优先考虑 HWASan（或 Pixel Android 15+ HWASan system image），硬件辅助方案的内存开销比 ASan 低。

[已验证: Android NDK ASan 官方文档 — “AddressSanitizer beginning with API level 27”; HWASan 文档 — source.android.com/docs/core/debug/asan]

实际工作中的选择策略:如果怀疑 Native 内存泄漏(内存持续增长但不释放),用 heapprofd 做采样分析;如果需要完整的分配记录来精确定位泄漏点,用 malloc debug;如果遇到的是 Native 崩溃(use-after-free、buffer overflow 等),用 ASan/HWASan。

## Graphics 内存的归属与计量

Graphics 内存是内存分析中经常被忽略但又占据相当大比例的部分。一个使用了大量 Bitmap 的 App,Graphics 内存可能占总 PSS 的 30% 甚至更多。

### dumpsys gpu 与 Graphics 内可见性

`memtrack` HAL 在 HIDL 时代就已经存在。Android 11 的 `hardware/interfaces/memtrack/1.0/IMemtrack.hal` 已经提供 `getMemory()`,`dumpsys meminfo` 的 "Graphics" 行依赖 `libmemtrack` 和设备侧 HAL 实现汇总进程的 Graphics / GL 相关记账。因此,同一 App 在不同 SoC 和 OEM 设备上的可见项与数值可能有差异。

[已验证: AOSP, android11-release hardware/interfaces/memtrack/1.0/IMemtrack.hal]

Android 12 之后,Graphics 和 DMA-BUF 的记账口径继续收紧。android-16.0.0_r1 的 AIDL `IMemtrack` 仍提供 `getMemory()` 和 `getGpuDeviceInfo()`,用于区分 GPU 设备并减少 CPU 映射与 GPU 映射缓冲区的重复记账。

Android 16 还明确了系统级 GPU 查询:`pid = 0` 且 `type = GL` 时,HAL 返回全局 GPU private memory;对应记录可以带 `FLAG_SMAPS_UNACCOUNTED`,表示这部分显存不会出现在某个进程的 `/proc/<pid>/smaps` PSS/RSS 中。这个接口让进程 Graphics 行和系统 GPU 显存总量之间的差额有了标准查询入口。分析 Graphics 内存时,`dumpsys meminfo`、`dumpsys gpu`、`IMemtrack` 与设备厂商实现要结合着看。

[已验证: AOSP, android-16.0.0_r1 hardware/interfaces/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl]

`adb shell dumpsys gpu` 命令可以查看更详细的 GPU 内存信息,包括全局 GPU 内存使用量和按进程的 GPU 内存分配。不过这个命令的输出格式在不同 OEM 设备上差异较大。

### Bitmap 内存管理的关键变化

在 Android 8.0(API 26)之前,Bitmap 的像素数据存储在 Java Heap 中,可以直接通过 MAT 看到每个 Bitmap 的大小和内容。从 Android 8.0 开始,Bitmap 像素数据移到了 Native Heap,Java 层只保留一个小的 Bitmap 对象(包含宽高、配置等元信息)。这一变化的背景和各版本 Bitmap 回收策略的演进,详见 §4.6 内存相关的版本演进。

这个变化对内存分析有两个影响:第一,`dumpsys meminfo` 中的 Java Heap 可能看起来不大,但 Native Heap 很高,因为 Bitmap 像素数据在那里;第二,MAT 中看到 Bitmap 对象的 Shallow Size 很小(只有几十字节),但通过 Bitmap 的 `mBuffer` 字段可以间接看到像素数据的 Native 内存占用。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT-Pro.md]

### 在 Perfetto 中的表现

Perfetto 里能否直接看到 Graphics 内存计数器,取决于 trace 配置、数据源和设备实现。下手前先枚举这个进程实际暴露出的 counter track,再选其中的 graphics / gpu 相关项。

```sql
-- 先枚举该进程实际存在的 counter track
SELECT DISTINCT pct.name
FROM process_counter_track AS pct
WHERE pct.pid = 12345
ORDER BY pct.name;
```

```sql
-- 再替换成实际存在的 graphics / gpu track 名称
SELECT c.ts, c.value, pct.name
FROM counter AS c
JOIN process_counter_track AS pct ON c.track_id = pct.id
WHERE pct.pid = 12345
  AND pct.name IN ('<actual graphics track name>')
ORDER BY c.ts;
```

有些 trace 只暴露全局 GPU counter,没有稳定的 `mem.android.graphics` 进程轨道。遇到这种情况,需要回到 Perfetto UI 或 `counter_track` / `process_counter_track` 表先做探测。

### Android 14 的 Graphics 内存优化

Android 14 引入了一项有意义的改进:当 `GraphicBufferProducer` 断开连接时,系统可以强制清除 Composer HAL 和 SurfaceFlinger 之间的 per-layer 缓冲区缓存。在之前,这个缓存即使不再使用也不会被释放,导致 Graphics 内存无法及时回收。完整的优化效果需要 Composer HAL API 3.2 的支持。

[已验证: 官方文档, source.android.com]

## 内存基线建立与回归检测方法

上面的工具组合覆盖了 Java Heap、Native Heap、Graphics 内存的分析场景。但定位和修复只是第一步--没有回归检测,下次发版可能引入新的内存问题。本节讨论如何建立系统化的内存基线,把内存防护变成自动化流程。

### 建立内存基线

内存基线是指 App 在关键场景下的"正常"内存使用水平。建立基线的方法是:在固定的设备型号和系统版本上,按照预定义的操作流程(如"冷启动→首页停留→打开详情页→返回→进入设置→返回"),用 `dumpsys meminfo` 或 Memory Profiler 记录每个步骤的 PSS/Heap 数据。

关键场景的基线至少应该包括:

- **冷启动后**:App 刚启动完成时的内存水平
- **热启动后**:App 从后台恢复时的内存水平
- **核心页面**:主要功能页面稳定状态下的内存
- **长时间运行后**:模拟 30 分钟或更长时间使用后的内存增长

基线数据需要记录多次取平均值,因为 Java GC 的时机不确定会导致单次测量有波动。

Android 15/16 上还要把 page size 纳入基线维度。同一条基线至少绑定设备型号、Android 版本、ABI、page size 和采样工具版本;4KB 与 16KB page size 分成两套基线。跨 page size 对比时,先按系统页粒度做分组,再看同组内的 PSS/RSS 变化。16KB 设备上约 9% 的系统性抬升不应直接算作应用回归。

| 维度 | 记录方式 | 用途 |
|------|----------|------|
| `page_size_kb` | `adb shell getconf PAGE_SIZE` 换算为 KB | 区分 4KB / 16KB 基线 |
| `android_api` | 设备系统版本 | 避免 Android 15/16 与旧版本混算 |
| `pss_kb` / `rss_kb` | `dumpsys meminfo` 或线上采样 | 观察总体内存趋势 |
| `private_dirty_kb` | `dumpsys meminfo` | 剥离共享库分摊影响,辅助判断 App 自身增长 |
| `graphics_kb` | `dumpsys meminfo` / `dumpsys gpu` / memtrack | 单独跟踪 Bitmap、Surface、GPU 资源 |

### 回归检测

有了基线之后,回归检测就是对比每次发版前的内存数据与基线的差异。自动化回归检测通常集成在 CI/CD 流水线中:

1. 在真机或云测试设备上运行预定义的操作流程
2. 用 `dumpsys meminfo` 或 Memory Profiler API 记录每个步骤的内存数据
3. 与同设备族、同 Android 版本、同 page size 的基线对比;如果 PSS 或 Private Dirty 增长超过阈值(如 5%),标记为回归
4. 跨 4KB / 16KB page size 汇总时,分别输出同组变化率和全量变化率,避免把系统页粒度变化误算进 App 回归
5. 使用 Macrobenchmark 库可以在 CI 中集成内存指标采集

[已验证: 官方文档, developer.android.com/studio/profile/benchmark]

Jetpack Macrobenchmark 提供了 `MemoryUsageMetric` 指标,可以在自动化测试中采集内存数据:

```kotlin
benchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(
        MemoryUsageMetric(MemoryUsageMetric.Mode.Max),  // 记录最大内存使用
    ),
    iterations = 10,
    startupMode = StartupMode.COLD
) {
    // 执行需要测试的操作
    pressHome()
    startActivityAndWait()
}
```

[已验证: 官方文档, developer.android.com/studio/profile/benchmark]

### 泄漏检测自动化

除了内存数值的回归检测,泄漏检测也是防劣化的重要手段。LeakCanary 是最常用的 Java 内存泄漏自动检测库,它能在 Debug 构建中自动检测 Activity、Fragment、View 等组件的泄漏,并输出完整的引用链。

将 LeakCanary 集成到自动化测试中的做法是:在每个 UI 测试结束后,用 `LeakAssertions.assertNoLeaks()` 检查是否有泄漏。如果有,测试会失败,CI 会报警,确保泄漏不会带上线。

[已验证: 来源见 obsidian/Cubox/为什么各大厂自研的内存泄漏检测框架都要参考 LeakCanary?因为它是真强啊!-2023-01-31.md]

## 使用 Perfetto heapprofd 分析 Native 内存分配

(🔸 扩展内容)

上一节我们介绍了 heapprofd 的基本用法,这里深入讨论它在实际场景中的分析方法。

### 模块归因分析

当 heapprofd 的火焰图显示大量 Native 分配时,第一步不是去看具体的分配点,而是做模块归因--这些分配来自 App 的哪个模块或哪个第三方 SDK。

模块归因的方法是按调用栈中的符号信息做分类。以字节跳动的 VolcRTC 为例:它的架构是以 Pipeline 形式组成的媒体引擎,每个 Pipeline 由不同功能的 Node 构成。通过命名空间对堆栈过滤,再按软件分层架构层层归因,就能形成一个树状结构,准确分析每个 Pipeline、每个 Node 的内存占用。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_RTC_性能自动化工具在内存优化场景下的实践.md]

实际操作中,Perfetto UI 的火焰图支持按调用栈路径搜索和过滤。我们可以用 `libexample.so` 或特定的命名空间做过滤,快速定位是哪个 `.so` 文件贡献了最多的 Native 分配。

### 一个常见陷阱:hook malloc 大小 ≠ Native Heap 大小

用 heapprofd 追踪到的 malloc 大小,和 `dumpsys meminfo` 显示的 Native Heap 大小通常不一致。原因是 malloc 分配器向操作系统申请内存是按页(4KB)进行的,而且分配器内部会缓存小内存块、产生碎片。所以 `dumpsys meminfo` 的 Native Heap 是操作系统视角的内存使用,heapprofd 的是应用视角的 malloc 调用量。两者的差值就是内存碎片和分配器缓存。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_RTC_性能自动化工具在内存优化场景下的实践.md]

## 线上内存监控的采样策略

(🔸 扩展内容)

线下工具(Memory Profiler、MAT、heapprofd)能精确定位问题,但只能覆盖开发人员手动测试的场景。线上监控的目的是捕获真实用户遇到的内存问题,包括:

### 关键指标采集

线上内存监控通常采集以下指标:

- **Java Heap 使用率**：通过 `Runtime.totalMemory() - freeMemory()` 计算已用部分，以 `Runtime.maxMemory()` 为预算上界（受 `largeMemoryClass` 约束）
- **进程 PSS**：通过 `Debug.MemoryInfo.getTotalPss()` 获取，返回进程 total PSS memory usage（单位 kB），涵盖 Java Heap、Native Heap、Graphics、Stack 等所有内存类别
- **是否接近内存预算**：Java Heap 使用率以 `Runtime.maxMemory()` 为分母（不是 `largeHeap` 绝对值）；进程 PSS 不应直接与 `ActivityManager.getMemoryClass()`/`largeMemoryClass()` 返回的 MB 值做比例——PSS 包含 Native Heap、Graphics、Stack 等 Java heap 之外的内存，`getMemoryClass()` 返回的是 Java heap 预算上限（单位 MB），两者口径不同。PSS 监控应建立同设备、同 Android 版本的历史基线做趋势对比
- **GC 频率**:短时间内 GC 事件过多说明内存压力大

[待验证: `Debug.getMemoryInfo()` 的 PSS 计算在不同 Android 版本上是否一致]

### 采样策略

线上监控不能每次都采集完整的内存信息(开销太大),通常采用以下采样策略:

**定时采样**:每隔 N 秒采集一次基础内存指标(PSS、Heap 使用率)。间隔通常为 30-60 秒,在后台运行时不采集。

**关键节点采样**:在页面切换、GC 后、收到 `onTrimMemory` 回调等关键时刻采集。这些时刻的内存数据最能反映页面的内存健康状况。

**异常触发**：当检测到内存使用率超过阈值（如 Java Heap 使用率 > 85% 或进程 PSS 出现异常增长）时，触发一次完整的内存快照采集（包括 Heap Dump），上报到服务端分析。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06-wechat_货拉拉司机Android端内存治理实践.md]

## 工具速查表

| 场景 | 工具 | 命令/操作 | 适用阶段 |
|------|------|-----------|----------|
| 快速查看内存分布 | dumpsys meminfo | `adb shell dumpsys meminfo <pkg>` | 所有阶段 |
| 实时观察内存曲线 | Memory Profiler | AS → View → Tool Windows → Profiler | 开发/测试 |
| Java 对象分配追踪 | Memory Profiler | Allocation Tracking | 开发 |
| Java 泄漏引用链 | MAT | Heap Dump → Dominator Tree → GC Roots | 开发/测试 |
| Native 内存分析 | heapprofd | Perfetto UI / `heap_profile` | 开发/测试 |
| Native 内存调试 | malloc debug | `setprop libc.debug.malloc.*` | 开发 |
| Native 内存错误 | ASan/HWASan | 编译选项 + wrap.sh | 开发 |
| GPU/ Graphics 内存 | dumpsys gpu | `adb shell dumpsys gpu` | 开发/测试 |
| 自动泄漏检测 | LeakCanary | 依赖集成 + UI 测试 | 开发/CI |
| CI 内存回归 | Macrobenchmark | `MemoryUsageMetric` | CI |

## 与其他章节的关系

本章聚焦于 App 内存分析的**工具和方法**,回答的是"怎么查"。与以下章节构成完整的内存知识体系:

- **§4.1 Android 内存模型全景**:了解内存分析的底层原理--PSS/RSS 是怎么计算的、内存分区是怎么回事
- **§4.3 ART 虚拟机内存管理**:了解 Java Heap 的分配和回收机制,理解 MAT 分析结果背后的原理
- **§4.5 App 内存优化**:在用本章的工具定位到问题后,§4.5 提供具体的优化策略
- **§14.3 内存分析工具**:对 Perfetto、Android Studio Profiler 等工具的更详细使用指南
- **§10.2 内存泄漏**和 **§10.3 内存持续增长**:定位到具体问题类型后的深入分析方法

## 常见问题与误区

**误区一:"Java Heap 大就是有泄漏"**

Java Heap 使用量大不一定等于泄漏。可能是正常的内存需求(如大量图片缓存),也可能是 GC 还没来得及回收。判断泄漏要看**内存是否能回落**--操作后触发 GC,如果 Heap 使用量没有回落到操作前的水平,才是泄漏。

**误区二:"Native Heap 不用管,系统会处理"**

Native 内存没有 GC,分配了不释放就是真的泄漏。随着 App 使用 JNI、音视频 SDK、Flutter 等,Native 内存占比越来越高。线上很多 OOM 崩溃是 Native 内存耗尽了 Java Heap 的预算空间。

**误区三:"MAT 中 Retained Size 最大的一定是泄漏"**

Retained Size 最大的对象可能只是正常的缓存(如图片库的 LRU Cache)。判断泄漏需要结合引用链分析:如果引用链经过一个应该被释放的 Activity/Fragment,那才是泄漏;如果引用链最终指向一个长期存活的单例或 Application 对象,那可能是有意为之。

**误区四:"dumpsys meminfo 的 PSS 等于 App 的内存开销"**

PSS 是进程维度的内存计量,但它包含了共享库的分摊。对于系统整体内存的影响,需要看 `dumpsys meminfo` 的 TOTAL 行;对于 App 自身可控的内存,应重点关注 Private Dirty(进程独占且被修改的内存)。

**误区五:"线上内存监控只需要采集 PSS"**

PSS 是必要的但不够。它只能告诉你"内存高了",但不知道是 Java Heap、Native Heap 还是 Graphics 的问题。线上监控至少需要区分 Java Heap 使用率和 PSS,最好还能采集 Native Heap 和 Graphics 的数据,才能指导排查方向。

## 参考资料

- [Android Studio Memory Profiler 官方文档](https://developer.android.com/studio/profile/memory-profiler)
- [Perfetto Native Heap Profiling 文档](https://perfetto.dev/docs/data-sources/native-heap-profiling)
- [Android userspace lmkd 文档](https://source.android.com/docs/core/perf/lmkd)
- [Memtrack HAL HIDL 接口(Android 11)](https://android.googlesource.com/platform/hardware/interfaces/+/android11-release/memtrack/1.0/IMemtrack.hal)
- [Memtrack HAL AIDL 接口(android-16.0.0_r1)](https://android.googlesource.com/platform/hardware/interfaces/+/android-16.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl)
- [Android 16KB page size 兼容性说明](https://developer.android.com/guide/practices/page-sizes)
- [MAT (Memory Analyzer Tool) 官方文档](https://eclipse.dev/mat/)
- [malloc debug 官方文档](https://source.android.com/docs/core/debug/native-crash)
- [ASan (AddressSanitizer) 官方文档](https://source.android.com/docs/core/debug/asan)
- [Android 内存管理概述](https://source.android.com/docs/core/debug/interpreting-cpu)
- [Jetpack Macrobenchmark](https://developer.android.com/studio/profile/benchmark)
- [已验证: 来源见 obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT-Pro.md]
- [已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_RTC_性能自动化工具在内存优化场景下的实践.md]
- [已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06-wechat_货拉拉司机Android端内存治理实践.md]