---
title: "Native 内存管理与优化"
chapter: "23.3"
section: "23.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1；Perfetto heapprofd；Android NDK 内存调试、MTE、GWP-ASan、Scudo 与 16 KiB 官方文档"
last_review_finalize_at: "2026-08-15T07:14:34+08:00"
last_review_finalize_run_id: "20260815-071434-gracker-writing-review"
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/tests/debug/native-memory"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://developer.android.com/ndk/guides/memory-debug"
  - type: official
    path: "https://developer.android.com/ndk/guides/arm-mte"
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: official
    path: "https://developer.android.com/ndk/guides/gwp-asan"
  - type: aosp
    path: "https://android.googlesource.com/platform/bionic/+show/android-17.0.0_r1/libc/memory/malloc_debug/README.md"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Debug.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/androidprocheaps.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/procmeminfo.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/system/memory/libmemunreachable/+/refs/tags/android-17.0.0_r1/README.md"
  - type: official
    path: "https://source.android.com/docs/security/test/scudo"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: blog
    path: "Clippings/Android 性能优化 - Native 内存优化（上）：so 库申请的内存优化.md"
tags: [native-memory, malloc, asan, hwasan, so-memory]
related_chapters: ["23.2", "4.1", "4.2", "10.1", "14.5"]
pipeline_stage: finalized
last_draft_polish_at: "2026-08-15T07:14:34+08:00"
last_draft_polish_run_id: "20260815-071434-gracker-writing"
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
consolidated_from:
  - "src/part5-app/ch23-memory-practice/08-memory-case-studies.md"
  - "src/part5-app/ch23-memory-practice/11-scudo-native-heap-allocator.md"
---

# Native 内存管理与优化

> **版本基线**
>
> 平台源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点。涉及 `/proc`、VMA 与内核统计接口时，以 `android17-6.18-2026-06_r6` 为内核侧基线。旧版本只用于说明能力的引入时间，不作为当前实现依据。

## 原生内存为什么需要单独排查

Java 堆没有持续增长，不代表进程的内存占用稳定。使用 JNI、音视频 SDK、地图 SDK、游戏引擎、图片库或加密库的应用，原生堆（Native Heap）、匿名 `mmap`、共享库映射和图形缓冲都可能让 PSS 上升。后果可能是后台进程更早被系统回收、前台出现内存压力或原生崩溃。

应用侧要先确认增长属于哪一种系统统计，再按问题类型选择 heapprofd、`libmemunreachable`、`malloc_debug`、ASan、HWASan、GWP-ASan 或 MTE。容量问题与非法访问需要不同证据：前者关注分配栈和存活量，后者关注越界、释放后访问等错误现场。内存模型见 [4.1 Android 内存模型全景](../../part1-fundamentals/ch04-memory/01-memory-overview.md) 和 [4.2 Linux 内核内存管理](../../part1-fundamentals/ch04-memory/02-linux-memory.md)，工具使用见 [14.5 内存分析工具](../../part3-tools/ch14-other-tools/05-memory-tools.md)，应用进程统计见 [10.1 App 内存分析](../../part2-performance/ch10-memory-perf/01-app-memory-analysis.md)。

文中术语含义如下：

| 术语 | 本文含义 |
|---|---|
| JNI / `.so` / ELF | JNI 是 Java/Kotlin 与 C/C++ 代码之间的调用接口；ELF 是 Android 原生二进制文件采用的格式，`.so` 是其中的共享库文件。 |
| RSS / PSS / Private Dirty | RSS 是驻留物理页总量；PSS 按共享者数量分摊共享页；Private Dirty 是当前进程独占且已写入的页面。`Shared Clean` 是未被写脏的共享页，`Private Clean` 是未被写脏的私有页。 |
| VMA / `mmap` | VMA（虚拟内存区域）描述一段连续地址范围及其权限和来源；`mmap` 用于建立匿名或文件映射。 |
| allocator / arena / chunk / quarantine | allocator（内存分配器）管理申请与释放；arena 是其成组管理的内存区域；chunk 是单个分配块；quarantine（隔离区）会延迟复用已释放块。 |
| memtrack / `dma-buf` | memtrack 是 Android 汇总图形等设备内存的接口；`dma-buf` 是内核中供设备和进程共享缓冲区的机制。 |
| Graphics / GL / Code / Unknown | 这些是 `dumpsys meminfo` 的分类标签：Graphics 和 GL 通常覆盖图形缓冲与 OpenGL 驱动分配，Code 统计映射的程序及安装包文件，Unknown 收纳未归入其他分类的页面；具体边界受平台和驱动实现影响。 |
| UID / SELinux / root | UID 是 Linux 用来区分进程身份的用户编号；SELinux 是 Android 的强制访问控制机制；root 表示系统管理员权限。 |
| user / userdebug / eng | user 是量产构建；userdebug 和 eng 提供更多调试权限。`debuggable`、`profileable` 是应用清单或构建配置声明的可调试、可分析属性。 |
| Bionic / Scudo / jemalloc | Bionic 是 Android 的 C 标准库；Scudo 和 jemalloc 是系统可采用的原生内存分配器。 |
| sanitizer / instrumentation | sanitizer 是检测内存错误的运行时；instrumentation（插桩）是在构建时加入检测代码。 |
| tombstone / fault address | tombstone 是 Android 原生崩溃转储；fault address 是触发异常访问的地址。Build ID 用于匹配二进制和符号，ABI 表示应用二进制接口。 |
| HPROF | Java 堆快照的数据格式和分析路径，用于查看 Java 对象，不等同于 heapprofd 记录的原生堆分配。 |
| producer / client | 在 heapprofd 中，producer 是写入 Perfetto 数据的组件，client 是目标进程内接收配置并记录分配的组件。 |

原生内存先按系统统计分区，再选择对应工具；分配调用栈、虚拟内存页和图形缓冲不能用同一份数据互相替代。

## 原生内存包含哪些部分

应用侧讨论原生内存时，容易把所有非 Java 堆的增长都归到 `malloc`。排查时至少区分四类：

- **原生堆**：C/C++ 代码通过 `malloc`、`calloc`、`realloc`、`new` 申请的堆内存，常见来源是 JNI 层业务代码、第三方 `.so`、音视频编解码、图片库和加密库。
- **匿名 `mmap` 区域**：代码直接用 `mmap` 申请的私有匿名映射，或者分配器向内核申请的大块 arena。`/proc/<pid>/smaps` 中可能显示为 `[anon:libc_malloc]`、`[anon:scudo:*]` 或业务自定义名称。
- **`.so` / ELF 映射**：`.so` 文件被动态链接器映射到进程地址空间后，会产生代码段、只读数据、可写数据和重定位相关页面。共享只读页面通常按 PSS 分摊，可写脏页计入当前进程。
- **图形与硬件缓冲**：Bitmap 像素、OpenGL/Vulkan 纹理、Surface buffer（界面缓冲）、`dma-buf` 等资源可能出现在原生堆、Graphics、GL 或 memtrack 统计中。统计位置受分配方式、驱动和厂商实现影响，不能只根据一个 VMA 名称判断资源类型。图片内存见 [23.2 Bitmap 与图片内存优化](./02-bitmap-optimization.md)。

Android 17 中，`android_os_Debug.cpp` 的 `android_os_Debug_getDirtyPagesPid()` 调用 libmeminfo 的 `ExtractAndroidHeapStats()` 取得按 VMA 分类的统计，再把 memtrack 返回的图形数据计入相应字段。VMA 分类规则位于 `androidprocheaps.cpp`：`[heap]`、`[anon:libc_malloc]`、`[anon:scudo:]` 和 `[anon:GWP-ASan]` 等名称归入原生堆，`.so` 归入共享库，`.jar`、`.apk` 等归入对应的代码分类。Graphics 数值还可能来自 memtrack，不能推断所有 `dma-buf` 都由 `androidprocheaps.cpp` 按名称归类。

VMA 分类和总量统计使用不同读取路径。`androidprocheaps.cpp` 必须扫描详细的 `/proc/<pid>/smaps`，因为分类依赖每个 VMA 的名字。`ProcMemInfo::SmapsOrRollup()` 服务于 PSS、RSS 等聚合值；内核提供 `smaps_rollup` 时读取汇总文件，否则改读 `smaps`。`smaps_rollup` 没有逐 VMA 名称，不能替代分类路径。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/jni/android_os_Debug.cpp`, `system/memory/libmeminfo/androidprocheaps.cpp`, `system/memory/libmeminfo/procmeminfo.cpp`]

四类内存对应不同的诊断动作：原生堆看分配栈；`.so` 映射看装载范围、重定位和脏页；图形缓冲看图像、渲染资源与 memtrack；匿名 `mmap` 需要追踪调用方或业务设置的 VMA 名称。把它们合成一个“原生内存”数字，会丢失定位所需的信息。

## 排查入口：先看趋势，再记录调用栈

原生内存问题常见两种曲线：一次性峰值过高，或者存活内存随操作次数持续增长。前者多见于大图、模型、音视频缓冲和一次性解压；后者需要继续检查泄漏、缓存失控或对象池未回收。

这三组命令用于建立第一次快照。`dumpsys meminfo` 适合先看系统分类；读取 `smaps` 适合检查 VMA，但在量产设备上可能受到 UID、SELinux 和 `/proc` 访问限制，需要 root、userdebug 或目标进程具备相应调试条件。

```bash
# 1. 看系统口径的进程内存分类
adb shell dumpsys meminfo <package_or_pid>

# 2. 在权限允许时保存 VMA 级明细
adb shell cat /proc/<pid>/smaps > smaps.txt

# 3. 从系统分类中单独观察 Native Heap
adb shell dumpsys meminfo <pid> | grep -A 20 "Native Heap"
```

这些快照只能说明“哪一类发生变化”，不能直接证明泄漏。应在相同设备、相同构建和相同操作序列下，对比进入场景前、场景稳定后、退出并等待回收后的数据。如果原生堆持续增长，再采 heapprofd；如果 Graphics、GL 或 memtrack 相关值增长，转到图片和渲染资源路径；如果 `.so` 的私有脏页异常，再检查动态库装载、初始化写入和重定位。

## heapprofd：原生堆分配的首选分析入口

heapprofd 适合回答两个问题：哪条调用栈的累计分配量高，哪条调用栈在快照时仍有较多存活分配。它是 Perfetto 的原生堆采样分析器，从 Android 10 开始可用。user 构建只能分析满足系统权限规则的 debuggable 或 profileable 应用；系统进程和更深的诊断通常需要 userdebug 或 eng 环境。

### 中央服务默认禁用，由采集请求按需启动

Android 17 的 `heapprofd.rc` 把 `heapprofd` 服务声明为 `disabled`。`persist.heapprofd.enable=1` 或 `traced.lazy.heapprofd=1` 时，init（Android 启动后负责管理系统服务的进程）才启动服务；两个属性都清空后停止。因此，heapprofd 不是从开机起持续运行的常驻采集器。

服务启动后，`heapprofd.cc::StartCentralHeapprofd()` 从 init 进程传入的 socket（本地通信端点）取得监听端，建立 `HeapprofdProducer`，接收目标进程中分析 client 的连接。应用进程使用 `malloc_interceptor_bionic_hooks.cc` 中的 Bionic `MallocDispatch` 拦截 `malloc`、`free`、`calloc`、`realloc` 等入口，并通过 `AHeapProfile_registerHeap` 注册要分析的堆；这条路径不依赖 `LD_PRELOAD`。

这套接口属于 heapprofd 与系统分配器的内部协作面，不能作为应用 SDK 的公共 malloc 拦截 API。Android 17 源码里的 `heapprofd_get_malloc_leak_info` 和 `heapprofd_write_malloc_leak_info` 是显式的空实现，不能把它们解释为 LeakCanary 或其他原生泄漏 SDK 的基础接口。

[源码锚点: Perfetto `android-17.0.0_r1`, `heapprofd.rc`, `src/profiling/memory/heapprofd.cc`, `src/profiling/memory/malloc_interceptor_bionic_hooks.cc`]

### 采集配置与采样语义

这段配置演示如何采集一个指定进程。`size_kb` 和 `dump_interval_ms` 是诊断示例值，需要根据复现时长和设备负载调整；`sampling_interval_bytes` 决定采样密度。

```protobuf
buffers: {
  size_kb: 65536
}
data_sources: {
  config {
    name: "android.heapprofd"
    heapprofd_config {
      process_cmdline: "com.example.app"
      sampling_interval_bytes: 4096
      continuous_dump_config {
        dump_interval_ms: 10000
      }
    }
  }
}
```

Perfetto 官方文档把 `4096` 字节作为默认采样间隔。`Sampler::SampleSize()` 对小于间隔的分配使用按字节推进的概率采样，含义是长期期望每 N 字节产生一个样本；单次分配大于或等于间隔时绕过该概率路径，记录这次分配的原始大小。因而，不能用“采样覆盖率”直接换算某个对象被记录的固定次数，也不能脱离设备、调用栈展开成本和负载给出固定 CPU 百分比。

采集后在 Perfetto UI 的 Heap Profile（堆分配视图）中查看结果；其中的火焰图按调用栈层级汇总分配。分析泄漏时，比较多个时间点仍然存活的分配及其调用栈；分析频繁申请和释放造成的分配抖动时，观察累计分配量与分配频率。间隔越小，小分配的细节越多，事件量与运行开销也越高。应先在目标设备上测量开销，再决定复现窗口和采样间隔。

[源码锚点: Perfetto `android-17.0.0_r1`, `src/profiling/memory/sampler.h`, `src/profiling/memory/sampler.cc`]

### 原生堆与 Java HPROF 是两条独立路径

Android 17 的 Perfetto 源码为原生 heapprofd 使用 `__SIGRTMIN + 4`，为 Java HPROF 使用 `__SIGRTMIN + 6`。Java HPROF producer 在发送信号前还会通过 `CanProfile()` 检查目标进程是否允许分析。两者使用不同的数据源、信号与权限路径；某一种转储命令能运行，不能推出另一种 Perfetto 数据源也一定可用。

[源码锚点: Perfetto `android-17.0.0_r1`, `src/profiling/memory/heapprofd_producer.cc`, `src/profiling/memory/java_hprof_producer.cc`]

## libmemunreachable 与 malloc_debug：本地复现时补充泄漏证据

`libmemunreachable` 在请求发生时扫描原生分配器中无法从可达根访问的分配块。默认模式不会为每次分配记录回溯，因此运行期开销低，但报告只能提供地址、大小上界和部分内容。启用 `malloc_debug` backtrace（分配回溯栈）后，报告可以附带分配栈，代价是明显的运行时开销。

Android 17 固定标签下，面向应用的流程位于独立仓库 `platform/system/memory/libmemunreachable`；`malloc_debug` 实现则从旧目录 `libc/malloc_debug` 移到了 Bionic 的 `libc/memory/malloc_debug`。这组命令用于 userdebug 设备上的单个应用；`<process>` 要替换为进程名，设置属性后必须终止并重新启动进程。

```bash
adb root
adb shell setprop libc.debug.malloc.program app_process
adb shell setprop wrap.<process> "\$\@"
adb shell setprop libc.debug.malloc.options backtrace=4

# 重启目标进程并复现问题后执行
adb shell dumpsys -t 600 meminfo --unreachable <process>
```

`--unreachable` 报告的是扫描时无法到达的分配块，不等于语言层意义上的确定泄漏。保守扫描可能把某些整数误认成指针，第三方分配器或自管理内存也可能不在它的观察范围内。应结合可重复的增长趋势、分配栈和资源生命周期判断。

Bionic README 还记录了 Android 12 起的一个 `wrap.<APP>` 问题。属性未生效时，可在受控测试设备上按 README 设置 `dalvik.vm.force-java-zygote-fork-loop=true`，再重启 Zygote（应用进程的模板进程）；这会影响设备进程启动方式，不应在量产设备上尝试。

完成诊断后要清除三个属性并重启进程，避免后续测试继续承受 backtrace 开销：

```bash
adb shell setprop libc.debug.malloc.options "''"
adb shell setprop libc.debug.malloc.program "''"
adb shell setprop wrap.<process> "''"
```

这些清理命令只撤销本次 malloc_debug 配置，不会修改应用数据。量产 user 设备通常不具备执行该流程所需的 root、属性和 SELinux 权限，因此它应位于可控环境的复现阶段。

## 怎样选择 ASan、HWASan、GWP-ASan 与 MTE

原生内存问题不只有泄漏。越界写、use-after-free（释放后使用）和 double free（重复释放）可能先表现为偶发崩溃、数据损坏或 UI 异常，再在内存统计里留下噪声。检测工具按使用场景选择：

| 工具 | 适合场景 | 代价与边界 |
| --- | --- | --- |
| ASan | HWASan 无法使用时，调试旧设备上的越界访问和 use-after-free | 已弃用且不再积极维护；需要重新编译插桩，内存和运行时开销高 |
| HWASan | 测试阶段检测 64 位 Arm 设备上的内存错误 | 当前 NDK 文档推荐的测试期首选；需要支持的系统镜像和编译配置 |
| GWP-ASan | 在较低开销下抽样捕获原生堆 use-after-free（释放后使用）和 heap-buffer-overflow（堆缓冲区越界） | 抽样检测，不保证每次问题都命中 |
| MTE | Arm Memory Tagging Extension（内存标记扩展），用硬件标签检测越界和释放后访问 | 依赖硬件、系统版本、应用清单与系统配置；模式不同会影响性能与报错时机 |

HWASan 适合测试构建，ASan 只在 HWASan 不可用时作为兼容方案。GWP-ASan 和 MTE 可在较低开销下扩大检测样本。它们定位内存安全错误，不替代 heapprofd 的容量分析；heapprofd 能说明哪些调用栈分配得多，sanitizer 能说明哪次访问越界或访问了已释放内存。

应用清单可请求的启用模式是 `sync` 和 `async`；`asymm` 不是 `android:memtagMode` 的取值。ASYMM 是 Arm v8.7-A 提供的平台模式：读取按同步方式检查，写入按异步方式检查。设备可以通过每个 CPU 的 `mte_tcf_preferred`，把应用请求的 ASYNC 静默升级为 ASYMM 或 SYNC。因此，应用记录的是请求模式，设备的有效模式还取决于平台配置。

## `.so` 库内存优化从三个维度入手

`.so` 库相关内存要拆成装载成本、运行时分配和可写脏页。三者对应不同动作。

### 装载成本：少装、晚装、按需装

一个 `.so` 被加载后，代码段、只读数据、重定位表和符号相关页面会进入进程地址空间。只看 APK 体积无法判断运行时内存，排查时要看进程 `maps` / `smaps` 中对应 `.so` 的 RSS、PSS 和 Private Dirty。

可执行动作：

- 只在测量表明 `dlopen` 数量或重复元数据造成显著成本时，评估合并小型原生模块；合并后若低频代码被一并加载，也可能增加常驻映射；
- 把低频功能的 `.so` 延后到功能入口加载；
- 清理未使用 ABI、未使用架构和重复打包的 `.so`，这主要减少安装包与安装占用；只有相关文件原本会被映射时，才会影响运行时 RSS/PSS；
- 把发布构建的符号文件作为独立产物保存，供 tombstone、Perfetto 和地址回溯使用；从 App 内移除调试段主要减少文件体积，不能直接视为等量的运行时内存收益。

### 运行时分配：把大块分配变成可解释事件

第三方 `.so` 分配异常时，单靠 `dumpsys meminfo` 只能看到原生堆变大。heapprofd 或 malloc 拦截能把分配归到调用栈；如果符号文件保留完整，还能还原到函数名和源码行。

工程上可以为可控的原生大对象建立统一分配入口，例如模型缓冲、音视频帧缓冲、解码输出池和压缩临时缓冲。封装层记录大小、用途、生命周期与调用位置，生产环境只上报有界的聚合数据；本地再使用 heapprofd 或 `malloc_debug` 取得完整分配栈。对于不可改动的第三方库，以分析工具的证据为准，避免仅凭库名归因。

### 可写脏页：少改共享映射，少做启动期全量初始化

`.so` 的只读页面可以在多个进程间共享；页面一旦被当前进程写脏，就会变成私有成本。常见来源包括全局可变数据、启动期大表初始化、懒加载缓存写入和重定位后的可写段。

排查时对比同一 `.so` 的 `Shared Clean`、`Private Dirty`、`Private Clean`。如果某个库的 `Private Dirty` 远高于同类模块，要检查它是否在启动期写入大块全局状态，或者把可延迟的数据提前初始化了。

## 原生内存监控方案

生产监控不应照搬本地分析工具。用户设备上的目标是发现趋势、定位版本和场景，不能长期记录完整调用栈。

一套可控方案可以分三层：

- **基础指标层**：定时采集 PSS、RSS、Native Heap Alloc（原生堆已分配量）、Graphics、GL、线程数、文件描述符（FD）数量，并带上页面、业务场景、前后台状态和设备可用内存分组。采集频率按场景设定，避免常驻高频轮询。
- **异常判定层**：在同一会话内观察增长斜率，例如进入页面前后、按确定脚本重复操作后、播放或上传结束后。单点阈值容易把合理的高占用当成异常。
- **诊断触发层**：命中抽样诊断规则后，对少量 debuggable 或 profileable 包触发 heapprofd、系统 meminfo 快照或业务侧原生分配摘要。普通发布包只上报聚合指标和场景标签。

指标上报要区分“占用高”和“泄漏”。缓存命中带来的短时原生堆增长不一定是问题；退出场景、收到 `onTrimMemory()` 或完成任务后仍不回落，只能构成进一步分析的信号，还需要分配栈与对象生命周期证明原因。分配器可能保留空闲页，PSS 没有立刻下降也不能单独证明对象仍然存活。

## Scudo 与原生堆的统计边界

Android 应用通常不直接选择系统分配器，但分配器会影响碎片、页归还、错误检测和 `smaps` 命名。Android 11 起常规设备使用 Scudo，低内存设备仍可能使用 jemalloc；最终实现应根据设备构建、VMA 名称和 tombstone 确认。

### 四种数值不要互相替代

| 口径 | 数据来源 | 适合回答的问题 | 覆盖不到的部分 |
| --- | --- | --- | --- |
| `Debug.getNativeHeapAllocatedSize()` | `mallinfo().uordblks` | 分配器当前记为已分配的字节 | 任意 `mmap()`、线程栈、共享库、Graphics |
| `dumpsys meminfo` 的 Native Heap | 原生堆 VMA 的 PSS/RSS 分类 | 原生堆对物理内存的贡献 | 具体分配调用栈 |
| `/proc/$pid/smaps` / `showmap` | 内核 VMA 与页统计 | 匿名映射、文件映射、栈和 `.so` 分别占多少 | 每次 `malloc()` 的调用者 |
| heapprofd / `Native Allocations` | 录制窗口内的分配、释放与栈 | 哪些路径分配、哪些样本仍存活 | 录制前分配和绕过分配器的映射 |

Android 17 的 `android_os_Debug.cpp` 直接把 `mallinfo().uordblks` 返回为 `getNativeHeapAllocatedSize()`。`libmeminfo` 则把 `[heap]`、`[anon:libc_malloc]`、`[anon:scudo:*]` 和 `[anon:GWP-ASan*]` 等 VMA 归到 Native Heap，并按页面计算 PSS/RSS。两条统计路径不同，所以分配器记录的已分配量下降后，原生堆 PSS 不要求同步下降。

### `free()` 后 RSS 没回落不等于泄漏

业务调用 `free()` 后，chunk 已不能再访问，但分配器可以把它放进 quarantine、线程缓存或空闲结构，等待复用或批量归还操作系统。Scudo 的 quarantine 会延迟复用已释放块，release interval 是批量向系统归还页面的间隔；两者会影响安全检查、锁竞争、复用速度与 RSS 回落。普通应用不应通过 `SCUDO_OPTIONS` 或 `__scudo_default_options` 把这类系统配置当作常规省内存开关。

泄漏判断仍需同时满足可重复增长和对象归因：固定场景中已分配量持续上升，heapprofd 的未释放样本集中在稳定调用栈，业务缓存过期后仍不回落，并且 Graphics、线程栈、文件映射等其他分区不能解释增量。

### Scudo ERROR：发现错误的位置不等于破坏内存的位置

Scudo 会在发现 `corrupted chunk header`、`invalid chunk state`、`misaligned pointer`、`allocation type mismatch` 或 `invalid sized delete` 等异常时终止进程。这些是日志中的原始错误标签，其中 chunk header 是分配器保存大小、状态等信息的元数据。若线程 B 在 `free()` 时发现 header 已损坏，越界写可能早已发生在线程 A。排查必须保留完整 tombstone、错误文本、fault address、Build ID、ABI、相关线程和匹配的未剥离符号，再用 GWP-ASan、MTE 或 HWASan 补充分配、释放与访问位置的证据。

GWP-ASan 是抽样检测，Recoverable（可恢复上报）模式写出 tombstone 后继续运行也不代表进程已经恢复正确状态。MTE 的 SYNC、ASYNC 和平台 ASYMM 模式在定位精度与成本上不同，应用清单请求还受设备硬件和系统配置约束。这些工具定位内存安全错误，不能替代 heapprofd 的容量归因。

### 16 KiB 页与三方 so

16 KiB 页会改变 ELF 加载段对齐、APK 中未压缩 `.so` 的 ZIP 起始位置对齐、`mmap()` 参数约束以及分配器管理区域的页面粒度。它不会让每个小对象都占用独立 16 KiB，也不能从 PSS 增量直接反推出 `malloc()` 对象数。含原生代码的应用应检查所有 ABI，运行时通过 `getconf PAGE_SIZE` 获取实际页大小，清理动态链接器和第三方库中写死的 4096 字节假设。

Android 15 起支持 16 KiB 页面设备。按 2026-08-15 的 Google Play 规则，面向 Android 15（API 35）及以上的应用更新需要在 64 位设备上支持 16 KiB 页面；从 2027-02-01 起，不兼容的更新将无法发布。构建兼容性仍需同时检查 ELF 加载段和 APK 内未压缩 `.so` 的 ZIP 对齐，不能只在 4 KiB 设备上运行一次就判定通过。

第三方 `.so` 的报告至少保存 SDK 版本、`.so` Build ID、ABI、输入与并发、设备页大小、heapprofd 样本和相同场景的 `meminfo`。缺少 Build ID 时，同名 `.so` 可能来自不同二进制，聚合后的调用栈没有可比性。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/jni/android_os_Debug.cpp`, `system/memory/libmeminfo/androidprocheaps.cpp`, `platform/bionic/libc/bionic/malloc_common.cpp`, `platform/external/scudo`]

## 排查清单

- `dumpsys meminfo` 中增长的是 Native Heap、Graphics/GL、Code，还是 Unknown？
- 使用确定的操作脚本重复场景后，内存曲线是趋于稳定、随次数增长，还是只出现一次峰值？
- heapprofd 的存活分配火焰图中，最大路径是否来自业务 JNI、第三方 SDK、图片库或音视频库？
- 原生崩溃是否带有 ASan、HWASan、GWP-ASan、MTE 相关标记？
- 相关 `.so` 是否有符号文件可用于地址还原？
- `smaps` 里同一 `.so` 的 `Private Dirty` 是否异常偏高？
- 生产环境是否只采集聚合指标，避免在用户设备上长期开启高开销调试能力？

## 参考资料

- [Debug native memory use](https://source.android.com/docs/core/tests/debug/native-memory)
- [Perfetto Native Heap Profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Memory error debugging and mitigation](https://developer.android.com/ndk/guides/memory-debug)
- [GWP-ASan](https://developer.android.com/ndk/guides/gwp-asan)
- [Arm MTE](https://developer.android.com/ndk/guides/arm-mte)
- [AOSP Arm MTE 与 ASYMM 模式](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [Scudo](https://source.android.com/docs/security/test/scudo)
- [Android 16 KiB 页面兼容要求](https://developer.android.com/guide/practices/page-sizes)
- [AOSP `android-17.0.0_r1`, malloc_debug README](https://android.googlesource.com/platform/bionic/+show/android-17.0.0_r1/libc/memory/malloc_debug/README.md)
- [AOSP `android-17.0.0_r1`, libmemunreachable README](https://android.googlesource.com/platform/system/memory/libmemunreachable/+/refs/tags/android-17.0.0_r1/README.md)
- [AOSP `android-17.0.0_r1`, android_os_Debug.cpp](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/jni/android_os_Debug.cpp)
- [AOSP `android-17.0.0_r1`, androidprocheaps.cpp](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/androidprocheaps.cpp)
- [AOSP `android-17.0.0_r1`, procmeminfo.cpp](https://android.googlesource.com/platform/system/memory/libmeminfo/+/android-17.0.0_r1/procmeminfo.cpp)
- [AOSP `android-17.0.0_r1`, Bionic README](https://android.googlesource.com/platform/bionic/+/android-17.0.0_r1/README.md)
- [Perfetto `android-17.0.0_r1`, heapprofd.rc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/heapprofd.rc)
- [Perfetto `android-17.0.0_r1`, heapprofd.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/heapprofd.cc)
- [Perfetto `android-17.0.0_r1`, malloc_interceptor_bionic_hooks.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/malloc_interceptor_bionic_hooks.cc)
- [Perfetto `android-17.0.0_r1`, heapprofd_producer.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/heapprofd_producer.cc)
- [Perfetto `android-17.0.0_r1`, java_hprof_producer.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/java_hprof_producer.cc)
- [Perfetto `android-17.0.0_r1`, sampler.h](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/sampler.h)
- [Perfetto `android-17.0.0_r1`, sampler.cc](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/profiling/memory/sampler.cc)
