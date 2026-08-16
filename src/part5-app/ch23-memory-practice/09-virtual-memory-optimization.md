---
title: "应用虚拟内存优化实战"
chapter: "23.9"
section: "23.9"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1 / common kernel android17-6.18-2026-06_r6 / Android 17 mmd documentation"
last_review_finalize_at: "2026-08-15T08:53:05+08:00"
last_review_finalize_run_id: "20260815-085305-gracker-writing-review"
confidence: high
sources:
  - type: aosp
    path: "art/runtime/thread.cc @ android-17.0.0_r1 (FixStackSize, CreateNativeThread)"
  - type: aosp
    path: "art/runtime/native/java_lang_Thread.cc @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/webkit/WebViewLibraryLoader.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/native/webview/loader/loader.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/gc/heap.cc @ android-17.0.0_r1 (PerformHomogeneousSpaceCompact)"
  - type: aosp
    path: "frameworks/base/core/jni/android_os_Debug.cpp @ android-17.0.0_r1 (load_maps)"
  - type: official
    path: "https://source.android.com/docs/core/perf/mmd"
  - type: official
    path: "https://developer.android.com/guide/practices/page-sizes"
  - type: official
    path: "https://developer.android.com/training/articles/perf-jni"
  - type: aosp
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst"
  - type: aosp
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/mm/multigen_lru.rst"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]"
  - type: blog
    path: '[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些"黑科技"优化手段.md]'
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
tags: [virtual-memory, VSS, thread-stack, maps-analysis, oom-prevention, memory-optimization, webview-reservation]
related_chapters: ["20.5", "4.3", "4.4", "23.6", "23.3", "5.14"]
consolidated_from:
  - "src/part5-app/ch23-memory-practice/13-virtual-memory-optimization.md"
pipeline_stage: finalized
last_draft_polish_at: "2026-08-15T08:53:05+08:00"
last_draft_polish_run_id: "20260815-085305-gracker-writing"
---

# 应用虚拟内存优化实战

虚拟内存问题经常与 Java heap OOM（ART 托管对象堆耗尽）、native heap（C/C++ 分配使用的堆）和线程资源耗尽混在一起。VMA（virtual memory area，虚拟内存区域）是内核记录的一段连续地址范围；同一 VMA 具有一致的权限和映射来源。排查时要先确认失败来自地址空间、物理内存、VMA 数量还是线程资源。只看一个很大的 VSS 数字，容易把正常的地址空间预留误判成泄漏。对象和 native 内存的持有关系可分别参阅 [23.1 内存泄漏检测与治理](./01-memory-leak-governance.md) 与 [23.3 Native 内存管理与优化](./03-native-memory-management.md)。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`；涉及内核 `/proc` 与 VMA 语义时，以 `android17-6.18-2026-06_r6` 为内核锚点。Android 10—16 的历史行为只用于解释存量设备，实际诊断仍以目标设备为准。

## 1. VSS 先看语义，再看数值

### 1.1 四个指标回答不同问题

| 指标 | 常见来源 | 回答的问题 | 不能单独证明什么 |
|---|---|---|---|
| VSS（Virtual Set Size）/ `VmSize` | `/proc/<pid>/status` | 所有 VMA 长度之和，也就是进程映射了多少虚拟地址 | 已消耗多少 RAM、是否正在泄漏 |
| RSS（Resident Set Size）/ `VmRSS` | `/proc/<pid>/status`、`smaps_rollup` | 当前驻留在 RAM 的页有多少 | 共享页应全部归属于该进程 |
| PSS（Proportional Set Size） | `dumpsys meminfo`、`smaps` | 共享页按使用进程数分摊后的物理内存 | 地址空间是否碎片化 |
| Private Dirty / Private Clean | `dumpsys meminfo`、`smaps` | 进程独占且已修改或仍可从文件恢复的页 | 单次快照中的增长原因 |

地址空间预留（reservation）会先占用一段虚拟地址，常用 `PROT_NONE` 禁止访问，等后续加载或提交时再改变映射。它与文件映射、尚未访问的匿名页都会计入 VSS，其中一部分还没有对应的物理页。64 位进程出现数 GiB VSS 很常见；结合 ABI、地址空间空洞、线程数、VMA 数量和失败现场后，VSS 才能参与判断。

### 1.2 32 位与 64 位的风险差异

32 位进程的用户态地址空间小于 4 GiB，具体布局受内核、ABI（应用二进制接口，决定指令集和数据布局）、ASLR（地址空间布局随机化）、链接器和厂商配置影响。不能把所有设备统一写成“3 GiB 用户态 + 1 GiB 内核态”。连续空洞不足时，即使未映射地址的总量看起来还够，大块 `mmap()`（建立内存映射的系统调用）仍可能返回 `ENOMEM`（无法满足内存或地址空间请求）。

64 位进程的可用用户态地址范围由架构和内核配置决定，无需固定写成 128 GiB、256 GiB 或 256 TiB；可从目标设备的 `maps` 边界和内核配置确认。64 位地址耗尽很少见，但 VMA 数量、物理内存、commit charge（内核对匿名内存可兑现容量的提交记账）、资源限制和错误的超大地址空间预留仍可能让映射失败。

常见故障信号如下：

| 信号 | 优先检查 |
|---|---|
| `pthread_create (... stack) failed` | 线程数、每线程栈、native 内存、进程资源限制、VMA 数量 |
| `mmap failed: ENOMEM` | ABI、请求长度、最大连续空洞、VMA 数量、`RLIMIT_AS`（进程虚拟地址空间资源上限）、系统内存压力 |
| `std::bad_alloc` / native OOM | native allocator（C/C++ 内存分配器）、RSS/PSS、碎片、申请尺寸；VSS 只作辅助 |
| Java `OutOfMemoryError` | ART 托管堆上限、对象存活关系与 GC；同时确认错误消息是否指向线程创建 |
| LMKD 杀进程 | PSS/RSS、进程状态和系统压力；VSS 不是 LMKD（low memory killer daemon，低内存终止守护进程）的直接排序指标 |

错误类型决定排查入口：线程创建失败先看线程和栈，映射失败先看连续地址与资源限制，进程被终止则先看物理内存压力。VSS 不能替代这些现场信号。

### 1.3 `VmSwap` 不能当成另一份 VSS

内核 `proc.rst` 把 `VmSwap` 定义为匿名私有数据使用的 swap（换出空间），shared memory（共享内存）的换出量不包含在内。页被换出后，原虚拟地址仍在 VMA 中，所以该页仍计入 `VmSize`；`VmSwap` 不是可以再加到 VSS 上的独立地址空间。

Android 17 及以上支持内存管理守护进程 `mmd`：`mmd_setup` 负责配置 ZRAM（在 RAM 中保存压缩换出页的块设备），`mmd` 再执行重压缩和可选的 writeback（把冷页写到后备存储）。应用从 `VmSwap` 只能看到按页核算的换出量，不能反推出 ZRAM 中压缩后的字节数，也不能判断页面此刻位于 ZRAM 还是后备存储。分析卡顿时，应同时查看 `VmSwap` 增长、major fault（需要存储 I/O 才能完成的主缺页）、PSI（Pressure Stall Information，资源压力导致的任务停顿统计）、`lmkd` 事件和业务时间线。

`android17-6.18-2026-06_r6` 还包含 Multi-Gen LRU（按访问时间把可回收页划分为多代的 LRU 实现）。它按访问新旧程度参与页回收选择，但不会改变 VSS、RSS、PSS 的定义；目标设备是否启用仍取决于内核与产品配置。应用侧应减少实际工作集并改善访问局部性，不能据此认定某个 VMA 可以由应用手动解除。

## 2. 建立可复现的地址空间快照

### 2.1 设备侧基础采集

这段脚本在同一轮中依次采集页大小、VSS、RSS、线程数和 `maps`。调用时显式传入包名与输出目录，避免把示例包名误用于现场：

```bash
#!/usr/bin/env bash
set -euo pipefail

if (( $# != 2 )); then
  echo "usage: $0 <package-name> <output-directory>" >&2
  exit 2
fi

package_name="$1"
output_directory="$2"
pid="$(adb shell pidof -s "$package_name" | tr -d '\r')"

if [[ -z "$pid" ]]; then
  echo "process not found: $package_name" >&2
  exit 1
fi

mkdir -p "$output_directory"
adb shell getconf PAGE_SIZE | tr -d '\r' > "$output_directory/page-size.txt"
adb shell cat "/proc/$pid/status" > "$output_directory/status.txt"
adb shell "ls /proc/$pid/task | wc -l" > "$output_directory/task-count.txt"
adb shell "wc -l /proc/$pid/maps" > "$output_directory/vma-count.txt"
adb shell cat "/proc/$pid/maps" > "$output_directory/maps.txt"
adb shell dumpsys meminfo "$package_name" > "$output_directory/meminfo.txt"

grep -E '^(Name|VmPeak|VmSize|VmRSS|RssAnon|RssFile|VmSwap|Threads):' \
  "$output_directory/status.txt"
```

`VmSize` 应与 `maps` 中各 VMA 长度之和接近，它不是最低地址到最高地址的跨度；两段 VMA 之间的空洞不计入 `VmSize`。`Threads` 应与 `/proc/<pid>/task` 数量一致。脚本中的命令顺序执行，并非原子快照；进程变化较快时要缩短采集间隔或连续采两轮验证。`pidof -s` 只选择一个 PID，多进程应用需要对每个目标进程分别采集。`dumpsys meminfo` 补充 PSS、RSS 和堆分类。部分量产设备会限制 `showmap` 或 `smaps`，权限失败要记录为观测缺口。

采集点至少覆盖：

- 冷启动完成；
- 进入目标业务前；
- 业务稳定运行；
- 业务退出并等待缓存回收；
- 异常前后。

只有一张峰值快照时，无法区分一次性预留、可复用缓存和持续泄漏。

### 2.2 `/proc/<pid>/maps` 怎样读

这一行展示 `maps` 的字段布局：

```text
70000000-78000000 ---p 00000000 00:00 0  [anon:libwebview reservation]
```

地址范围给出 VMA 起止位置；`rwx` 是读、写、执行权限；第四个字符 `p` 或 `s` 表示 private（私有映射）或 shared（共享映射）；其后依次是文件偏移、设备号、inode（文件系统中的对象编号）与可选名称。`---p` 说明当前没有读、写、执行权限，仍不能据此认定该区域可由应用释放。

Android 17 的 [`android_os_Debug.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Debug.cpp) 通过 `meminfo` 解析器读取进程映射并按堆类型汇总。应用自建分类器不能假设标签在所有厂商版本上都完全一致。

这段离线脚本按 pathname（`maps` 末列的映射名称或文件路径）汇总 VSS，并统计没有 pathname 的匿名 VMA。参数是设备侧脚本生成的 `maps.txt`：

```python
from collections import defaultdict
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(f"usage: {sys.argv[0]} <maps-file>")

groups = defaultdict(lambda: {"bytes": 0, "vmas": 0})
maps_path = Path(sys.argv[1])

for line in maps_path.read_text(encoding="utf-8").splitlines():
    fields = line.split(maxsplit=5)
    if len(fields) < 5:
        continue
    start, end = (int(value, 16) for value in fields[0].split("-", 1))
    name = fields[5] if len(fields) == 6 else "[anonymous]"
    key = name if name.startswith("[") else Path(name).name
    groups[key]["bytes"] += end - start
    groups[key]["vmas"] += 1

for name, stat in sorted(
        groups.items(), key=lambda item: item[1]["bytes"], reverse=True):
    mib = stat["bytes"] / 1024 / 1024
    print(f"{mib:10.1f} MiB  {stat['vmas']:6d} VMAs  {name}")
```

汇总结果适合查找大块地址空间预留、线程栈、重复 `.so` 库和 VMA 数量异常。脚本按文件名而非完整路径聚合，同名但不同路径的库会被合并；同一路径的多个 segment（映射分段）也可能分别承载代码、只读数据和可写数据。汇总值表示虚拟地址长度，不能直接当成私有物理内存。

### 2.3 16 KiB 页设备

`getconf PAGE_SIZE` 返回 `16384` 时，VMA 边界、guard page（用于捕获越界访问的不可访问保护页）和 ART 对齐都以 16 KiB 页大小计算。小对象仍可由分配器在页内切分；`maps` 只展示页级映射。

自研 native 组件需要遵守运行时页大小，[Android 的 16 KiB 页适配指南](https://developer.android.com/guide/practices/page-sizes) 要求清理写死的 `4096`、`0x1000` 或 4 KiB 对齐。解析 `start/end` 的十六进制差值不受页大小影响；调用 `mmap()`、`mprotect()`、`munmap()` 时，则要分别遵守接口对地址、offset（偏移量）和 length（长度）的约束。

每个系统调用的对齐要求不同：文件映射的 `mmap()` offset 必须按页对齐，内核会把实际映射范围向上取整到包含 length 的完整页；`MAP_FIXED` 地址、`mprotect()` 起始地址和 `munmap()` 起始地址也有页对齐要求。“所有参数都必须页对齐”并不是统一规则，具体要看调用使用的 flags（控制映射行为的标志）和接口文档。

## 3. 线程栈：先控制线程数量

### 3.1 Android 17 的 Java 线程栈计算

[`Thread::FixStackSize()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 按以下顺序计算栈预留大小：

1. 传入 `0` 时改用 ART 的默认栈大小；
2. 增加 1 MiB，以兼容依赖 Dalvik 较大 native stack 的应用；
3. 启用内存检测工具的构建保证至少 2 MiB；
4. 保证不小于 `PTHREAD_STACK_MIN`；
5. 根据隐式栈溢出检查配置，增加不可访问保护区和运行时保留区，或只增加保留区；
6. 向运行时页大小取整；
7. 把结果交给 `pthread_attr_setstacksize()` 和 `pthread_create()`。

“每个 Java 线程固定占 1 MiB”并不准确。最终地址空间预留还受 ART 默认值、保护区、保留区、页对齐和构建配置影响。`maps` 中的 `[anon:stack_and_tls:<tid>]` 是 Bionic（Android 的 C 标准库与系统基础库）为线程栈与 TLS 合并映射使用的标签；线程 dump（线程转储）可以把线程名与 TID（线程 ID）对应起来，映射大小仍应从 `maps` 读取。

线程栈通常按需分配物理页，因此 VSS 增长会早于 RSS 增长。32 位进程中，大量线程还会增加 VMA 数量、调度开销、TLS（thread-local storage，线程局部存储）和运行时线程元数据。

### 3.2 有界线程池

这个 Java 工厂方法展示有界队列、固定工作线程数和线程命名。调用方必须传入经过压测的工作线程数与队列容量，示例不内置设备无关的固定阈值：

```java
static ThreadPoolExecutor newBoundedExecutor(
        String threadNamePrefix,
        int workerCount,
        int queueCapacity,
        RejectedExecutionHandler rejectedExecutionHandler) {
    if (workerCount <= 0 || queueCapacity <= 0) {
        throw new IllegalArgumentException("workerCount and queueCapacity must be positive");
    }
    Objects.requireNonNull(threadNamePrefix);
    Objects.requireNonNull(rejectedExecutionHandler);

    AtomicInteger sequence = new AtomicInteger();
    ThreadFactory factory = runnable -> {
        Thread thread = new Thread(runnable);
        thread.setName(threadNamePrefix + "-" + sequence.incrementAndGet());
        return thread;
    };

    return new ThreadPoolExecutor(
            workerCount,
            workerCount,
            0L,
            TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(queueCapacity),
            factory,
            rejectedExecutionHandler);
}
```

固定上限可以阻止突发任务无限扩张线程。`workerCount` 要结合 CPU/I/O 比例和任务驻留内存确定，`queueCapacity` 要结合可接受的排队时延确定。拒绝策略也由调用方显式选择：`CallerRunsPolicy` 会让提交线程执行任务；提交方可能是主线程时，应改用合并、拒绝或异步重试等符合业务语义的处理。

线程数量常从这些位置失控：

- `Executors.newCachedThreadPool()` 的无限最大线程数；
- 每个 SDK 各建一套线程池；
- 定时任务每次创建新线程；
- 协程调度器或 RxJava Scheduler 配置不当；
- native SDK 内部的 `pthread_create()`；
- 线程退出后仍被 ThreadLocal、HandlerThread 或线程池引用。

CPU 密集任务的并发度可从 CPU 核数起步，I/O 任务没有通用的“64—128 线程”答案。应根据服务端并发限制、文件描述符、尾延迟和内存预算决定。

### 3.3 栈大小与函数拦截的边界

`Thread(ThreadGroup, Runnable, String, long)` 把 stack size（期望栈大小）定义为平台相关的建议值。Android 17 的 [`Thread.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java) 会原样保存该构造器传入的负数，JNI 桥接再把 `jlong` 交给接收 `size_t` 的 `Thread::CreateNativeThread()`。因此，特定负数可能在无符号转换和增加 1 MiB 时回绕成较小值；例如 `-512 KiB` 会在增加 1 MiB 后得到 512 KiB，再叠加 ART 保留区并按页取整。`Thread.Builder.OfPlatform.stackSize()` 则明确拒绝负数。这条回绕路径属于实现细节，构建变化后可能得到超大栈、`pthread_attr_setstacksize()` 失败或进程异常，不能进入生产方案。

对 `pthread_create()` 做 PLT hook（通过 Procedure Linkage Table 拦截动态库函数调用）也不能覆盖所有线程来源，并会改变系统库与三方库的栈假设。诊断时可以在可调试构建中记录调用栈和 `pthread_attr_t` 属性；修改栈大小则必须按 ABI、4/16 KiB 页、递归深度、JNI 栈帧大小和极端调用链做压力测试。生产环境仍应优先减少线程数量。

### 3.4 Android 17 的虚拟线程

`android-17.0.0_r1` 的 libcore 已包含 `Thread.ofVirtual()`、`startVirtualThread()` 和 `VirtualThread` 实现，但 [`api/current.txt`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/api/current.txt) 给创建入口标记了 `com.android.libcore.virtual_thread_api_v1` `FlaggedApi`，表示公开可用性受功能标志控制。[`ThreadBuilders.newVirtualThread()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/ThreadBuilders.java) 会检查 `ContinuationSupport.isSupported()`：支持时创建由 continuation（可暂停并恢复执行状态的运行时机制）驱动的 `VirtualThread`；不支持且调用方没有指定自定义 scheduler（任务调度器）时，创建一对一绑定平台线程的 `BoundVirtualThread`。

因此不能把“Android 17 虚拟线程一定不创建 pthread、每个任务都省下 1 MiB”当成通用结论。产品采用前需要确认目标镜像是否开放该 API、运行时是否支持 continuation，以及 pinning（虚拟线程因特定阻塞或同步操作而无法暂时脱离承载线程）的行为、调试工具和关键库兼容性。面向 Android 10—17 的通用实现仍应以协程、有界线程池和结构化取消为主。

更完整的线程泄漏边界参阅 [20.19 线程泄漏与匿名线程监控](../ch20-stability/19-thread-leak-anonymous-thread-monitoring.md)。

## 4. WebView 地址空间预留：可观测，不手动解除

### 4.1 固定标签中的预留

Android 17 的 [`WebViewLibraryLoader.reserveAddressSpaceInZygote()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebViewLibraryLoader.java) 选择以下地址空间大小：

| 进程 ABI | 地址空间预留 |
|---|---:|
| 64 位 | 1 GiB |
| 32 位 ARM | 130 MiB |
| 其他 32 位 ABI | 190 MiB |

[`loader.cpp::DoReserveAddressSpace()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/native/webview/loader/loader.cpp) 使用 `mmap(PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS)` 创建地址空间预留，并让全局变量 `gReservedAddress`、`gReservedSize` 记录其地址和大小。`maps` 中的名称是 `[anon:libwebview reservation]`。

这块预留会增加 VSS，但未访问的 `PROT_NONE` 地址不会按预留大小消耗 RSS。64 位进程看到 1 GiB VSS 增量时，不能写成“WebView 已消耗 1 GiB RAM”。表中的常量解释的是 Android 17 固定标签源码，其他系统版本仍应按对应标签核对。

### 4.2 为什么不能 `munmap`

WebView 加载器随后把 `gReservedAddress` 和 `gReservedSize` 交给 `android_dlopen_ext()`，在这段固定预留中加载 provider（提供 WebView 实现的系统组件）原生库和共享 RELRO（重定位完成后设为只读、可供进程共享的数据）。应用私自调用 `munmap()` 后，加载器的全局状态没有同步清零，该地址还可能被其他映射占用。稍后任何 WebView 初始化都可能加载失败或破坏进程地址空间。

通过函数拦截取得 `android_dlopen_ext()` 的地址、反射隐藏的 `nativeLoadWithRelroFile()`，或按 `maps` 标签解除映射，都依赖隐藏实现。即使当前进程暂时不用 WebView，广告、登录、支付、帮助页、SDK 和系统组件也可能在后续触发 provider。

安全策略只有两类：

- 业务不需要 WebView 时，避免初始化 provider 和相关 SDK，接受从 Zygote（用于孵化应用进程的模板进程）继承的预留仍计入 VSS；
- 需要隔离 WebView 时，按产品架构放入受控进程，管理该进程生命周期，并测量总 PSS、启动时延和 Binder（Android 进程间通信机制）代价。

把 WebView Activity 放到子进程不会自动移除主进程继承的预留；它的收益主要来自已提交页、WebView 对象与故障边界的隔离。

## 5. ART 托管堆：应用不能释放运行时内存区域

### 5.1 Homogeneous Space Compact 的适用条件

HSC（Homogeneous Space Compact，同构空间压缩）把主分配空间中的存活对象复制到备用空间，以整理碎片。Android 17 的 [`Heap::SupportHomogeneousSpaceCompactAndCollectorTransitions()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc) 要求同时存在 `main_space_backup_`、`main_space_`，且前台垃圾回收器为 CMS（Concurrent Mark Sweep，并发标记清扫）。`PerformHomogeneousSpaceCompact()` 还会在 moving GC（会移动存活对象的垃圾回收）已被禁用、当前回收器本身会移动对象，或主空间不允许移动对象时拒绝执行。

同一文件的 Heap 构造路径会对 CC（Concurrent Copying，并发复制）和 CMC（Concurrent Mark Compact，并发标记压缩）关闭 `use_homogeneous_space_compaction_for_oom_`。HSC 是受回收器与 Space（ART 管理的一类内存区域）布局约束的兼容路径，并非 Android 17 应用普遍执行的内存整理流程。它也不能推出“每个 Android 17 应用都有两块固定 512 MiB MainSpace”。ART 会按回收器、heap growth limit（托管堆允许增长到的上限）、设备配置和进程类型建立不同 Space。RegionSpace 用分区支持移动回收，zygote space 保存进程孵化前已有的对象，large object space 管理大对象，image space 映射启动镜像；JIT 代码映射则保存即时编译生成的机器码，各自的用途和生命周期不同。

### 5.2 JNI 临界区必须成对释放

[Android JNI tips](https://developer.android.com/training/articles/perf-jni) 对 `GetPrimitiveArrayCritical()` 的约束是：ART 可以返回指向数组的直接指针，也可以返回副本。取得指针到执行 `ReleasePrimitiveArrayCritical()` 之间称为 JNI 临界区；期间 native 代码不能长时间阻塞，也不能任意调用 JNI。完成访问后必须成对释放。

长期保留临界区指针可能延迟或限制 GC，具体影响取决于 ART 返回直接指针还是副本，以及当前垃圾回收器的实现。两种路径都要求临界区尽快结束，否则可能增加分配等待和线程停顿。对任一 `dalvik-*` 区域调用 `munmap()` 还会破坏 ART 的分配器、card table（记录哪些堆区域可能包含跨区引用的表）、对象位图和引用关系。“禁用 moving GC 后释放备用 Space”不是安全的应用方案。

应用侧能控制的是对象生命周期和分配形态：

- 取消不再需要的任务与回调；
- 对缓存设置容量和生命周期；
- 释放 Bitmap、媒体缓冲区、DirectByteBuffer 与 native peer（Java 对象对应的原生侧实例）；
- 用 heap dump（堆转储）、Perfetto、heapprofd（Android 原生堆采样器）和对象分配记录找到长期持有者；
- 避免在内存压力回调中同步制造大量临时对象。

## 6. 多进程：改变故障边界，也增加固定成本

每个 Android 进程都有独立的虚拟地址空间、ART 运行时、Binder 状态和原生内存分配器。把模块移入子进程会降低主进程中的已提交页与对象数量，但整个应用的总 PSS 可能上升。进程隔离的完整取舍可参阅 [23.6 大内存与多进程策略](./06-large-heap-multiprocess.md)。

这段 `AndroidManifest.xml` 配置展示私有进程声明：

```xml
<activity
    android:name=".WebContainerActivity"
    android:process=":web" />

<service
    android:name=".CodecService"
    android:process=":codec"
    android:exported="false" />
```

冒号前缀创建应用私有进程。是否值得拆分，要同时测主进程 PSS、子进程 PSS、启动时延、Binder 流量、冷启动次数和低内存下的恢复体验。

适合评估隔离的模块通常具备这些特征：

- 生命周期清晰，结束后允许整个进程退出；
- 原生代码崩溃风险较高，需要限制影响范围；
- 已提交内存大，主进程长期不需要保留；
- IPC（inter-process communication，进程间通信）接口较少，避免高频传输大对象；
- 被 LMKD 回收后可以恢复。

较大的数据载荷（payload）可考虑通过 `SharedMemory`、文件描述符或流式接口传输；仍要定义所有权、校验长度并及时关闭 FD（file descriptor，文件描述符）。多进程不能用来规避应用整体内存预算。

## 7. 建立面向原因的监控

### 7.1 采样字段

一条可解释的虚拟内存快照至少包含：

- 时间、业务场景、进程名、PID、ABI 和页大小；
- `VmSize`、`VmPeak`、`VmRSS`、`RssAnon`、`RssFile`、`VmSwap`；
- 线程数、VMA 数量和 FD 数量；
- `Java Heap`、`Native Heap`、`Graphics`、`Code` 与 `Stack` 等 `dumpsys meminfo` 分类的 PSS；
- 占用较大的 VSS 分类及其 VMA 数量，按报告容量保留排名靠前的若干类别；
- 最近一次 `mmap`、`pthread_create` 或内存分配器失败信息。

采样频率按风险控制。`/proc/self/status` 成本较低，可在场景边界采样；读取并解析 `maps`、记录每个 VMA 物理页明细的 `smaps`，或抓取堆转储，应由异常触发，避免高频磁盘读取和主线程阻塞。

### 7.2 阈值按设备分组

“五分钟增长 100 MiB”或“接近 2 GiB 就报警”缺少 ABI、业务和基线条件。阈值应按以下维度分别统计分位数：

- 32/64 位 ABI；
- Android 版本与页大小；
- 设备内存档位；
- 进程角色；
- 冷启动、稳定态、退出后；
- 线程数与 VMA 数量。

告警应组合 `VmSize` 增量、RSS/PSS 增量、线程/VMA 增量和错误信号。VSS 上升后 RSS 不变、业务退出后保持稳定，通常来自地址空间预留或可复用映射；VSS、RSS、线程数一起持续上升时，调查优先级更高。

## 8. 常见现场如何定位

### 8.1 `pthread_create` 失败

1. 保存 ART 错误中的 `requested stack size`（请求的栈大小）和 `errno`（native 调用返回的错误号）；
2. 记录 `/proc/<pid>/status` 的 `Threads`、`VmSize` 和 `VmRSS`；
3. 按线程名、创建调用栈和持有者聚合；
4. 检查缓存线程池、HandlerThread、SDK 与 native 线程；
5. 先减少线程，再评估受控线程的栈大小。

### 8.2 32 位进程 `mmap` 失败

1. 记录申请长度、`flags`（映射标志）、`errno` 和调用栈；
2. 保存完整 maps；
3. 计算最大连续空洞，不能只用地址总范围减 VSS；
4. 检查大块地址空间预留、重复库、线程栈和 VMA 数量；
5. 优先提供 64 位 ABI，并减少不必要映射的创建来源。

### 8.3 VSS 很大但设备没有内存压力

检查大区域是否为 `PROT_NONE`、文件映射、ART 预留或 WebView 地址空间预留，再看 RSS/PSS 与 page fault（访问尚未驻留页面时产生的缺页事件）。没有失败信号时，不为缩小面板数字去解除系统映射。

### 8.4 多进程后主进程变小、整机更卡

把所有进程的 PSS 相加，并检查进程反复冷启动、Binder 数据载荷、共享页分摊和 LMKD 回收。主进程单项下降无法证明方案节省了整机内存。

## 9. 优化顺序

表中的 P0、P1、P2 表示实施优先级：P0 是先完成的基础治理，P1 需要按设备或架构验证，P2 只用于受控诊断；“禁止”项会破坏运行时所有权。

| 顺序 | 动作 | 风险 |
|---|---|---|
| P0 | 记录 ABI、页大小、VSS/RSS/PSS、线程和 VMA 的同轮快照 | 低 |
| P0 | 明确线程持有者，使用有界线程池，清理失控的 HandlerThread/SDK 线程 | 低 |
| P0 | 修复对象、原生缓冲区、Bitmap、DirectByteBuffer 和映射生命周期 | 低 |
| P1 | 评估 64 位 ABI 覆盖，针对 32 位碎片做专项测试 | 中 |
| P1 | 按总 PSS 和生命周期评估进程隔离 | 中 |
| P2 | 在可调试构建中拦截 `mmap`/`pthread_create` 做取证 | 中 |
| 禁止 | 对 WebView 地址空间预留或 ART 托管堆 Space 调用 `munmap` | 高 |
| 禁止 | 永久持有 JNI 临界区指针来阻止 moving GC | 高 |
| 禁止 | 用负数栈大小依赖无符号回绕 | 高 |

虚拟内存优化要让每段地址空间都能对应到创建来源和生命周期。32 位进程优先检查连续空洞、线程栈和 VMA 数量；64 位进程优先区分地址空间预留与物理页，并把 PSS/RSS、线程和失败信号放在同一份报告中。如果只有主进程 VSS 下降，而总 PSS 和故障数据没有改善，就不能把改动记为有效优化。

## 参考源码与内核文档

- [`art/runtime/thread.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc)
- [`art/runtime/native/java_lang_Thread.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/java_lang_Thread.cc)
- [`libcore Thread.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/Thread.java)
- [`libcore ThreadBuilders.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/ThreadBuilders.java)
- [`libcore VirtualThread.java`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/VirtualThread.java)
- [`WebViewLibraryLoader.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebViewLibraryLoader.java)
- [`WebView loader.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/native/webview/loader/loader.cpp)
- [`art/runtime/gc/heap.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- [`android_os_Debug.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Debug.cpp)
- [Android JNI tips](https://developer.android.com/training/articles/perf-jni)
- [Android 17 Memory management daemon](https://source.android.com/docs/core/perf/mmd)
- [Linux 6.18 `/proc` 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)
- [Linux 6.18 Multi-Gen LRU](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/mm/multigen_lru.rst)
- [Android 17 common kernel tag `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
