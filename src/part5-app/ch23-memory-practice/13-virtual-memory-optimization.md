---
title: "应用虚拟内存优化实战"
chapter: "23.13"
section: "23.13"
status: ready-for-review
drafted_date: "2026-07-03"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-03"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
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
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]"
  - type: blog
    path: '[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些"黑科技"优化手段.md]'
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
tags: [virtual-memory, VSS, thread-stack, maps-analysis, oom-prevention, memory-optimization, webview-reservation]
related_chapters: ["20.5", "4.3", "4.4", "23.6", "23.3", "5.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-03"
gap_source: "Clippings结构参考/AOSP结构"
gap_score: 16
material_count: 4
---

# 23.13 应用虚拟内存优化实战

虚拟内存问题经常和 Java heap OOM、native heap、线程上限混在一起。处理这类问题时，第一步是确认失败来自地址空间、物理内存、VMA 数量还是线程资源。只盯着一个很大的 VSS 数字，容易把正常的地址预留当成泄漏。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`；涉及内核 `/proc` 与 VMA 语义时，以 `android17-6.18-2026-06_r6` 为内核锚点。Android 10—16 的历史行为只用于解释存量设备，不高于 Android 17。

## 1. VSS 先看语义，再看数值

### 1.1 四个指标回答不同问题

| 指标 | 常见来源 | 回答的问题 | 不能单独证明什么 |
|---|---|---|---|
| VSS / `VmSize` | `/proc/<pid>/status` | 进程建立了多少虚拟地址映射 | 已消耗多少 RAM、是否正在泄漏 |
| RSS / `VmRSS` | `/proc/<pid>/status`、`smaps_rollup` | 当前驻留在 RAM 的页有多少 | 共享页应全部归属于该进程 |
| PSS | `dumpsys meminfo`、`smaps` | 按共享比例分摊后的物理内存 | 地址空间是否碎片化 |
| Private Dirty / Private Clean | `dumpsys meminfo`、`smaps` | 进程独占页的组成 | 单次快照中的增长原因 |

`PROT_NONE` reservation、文件映射和未触达的匿名页都会计入 VSS，其中一部分没有对应的物理页。64 位进程出现数 GB VSS 很常见；只有结合 ABI、地址空间空洞、线程数、VMA 数量和失败现场，VSS 才能成为诊断证据。

### 1.2 32 位与 64 位的风险差异

32 位进程的用户态地址空间小于 4 GiB，具体布局受内核、ABI、ASLR、链接器和厂商配置影响。不能把所有设备统一写成“3 GiB 用户态 + 1 GiB 内核态”。连续空洞不足时，即使剩余 VSS 看起来还有空间，大块 `mmap()` 仍可能返回 `ENOMEM`。

64 位进程的可用用户态地址范围由架构和内核配置决定。工程上无需把它固定成 128 GiB、256 GiB 或 256 TiB；应从目标设备的 maps 边界和内核配置取证。64 位地址耗尽很少见，VMA 数量、物理内存、commit charge、资源限制和错误的超大 reservation 仍可能让映射失败。

常见故障信号如下：

| 信号 | 优先检查 |
|---|---|
| `pthread_create (... stack) failed` | 线程数、每线程栈、native 内存、进程资源限制、VMA 数量 |
| `mmap failed: ENOMEM` | ABI、请求长度、最大连续空洞、VMA 数量、`RLIMIT_AS`、系统内存压力 |
| `std::bad_alloc` / native OOM | native allocator、RSS/PSS、碎片、申请尺寸；VSS 只作辅助 |
| Java `OutOfMemoryError` | ART heap 上限、对象保活与 GC；同时确认错误消息是否指向线程创建 |
| LMKD 杀进程 | PSS/RSS、进程状态和系统压力；VSS 不是 LMKD 的直接排序指标 |

### 1.3 `VmSwap` 不能当成另一份 VSS

内核 `proc.rst` 把 `VmSwap` 定义为匿名私有数据使用的 swap，shared memory 的 swap 不包含在内。页被换出后，原虚拟地址仍在 VMA 中，所以该页仍计入 `VmSize`；`VmSwap` 不是可以再加到 VSS 上的独立地址空间。

Android 17 引入的 `mmd` 体系由 `mmd_setup` 配置 ZRAM，再由 `mmd` 执行重压缩和可选的 writeback。应用从 `VmSwap` 只能看到按页核算的换出量，不能反推出 ZRAM 中的压缩后字节数，也不能判断页面此刻位于 ZRAM 还是后备存储。分析卡顿时，应把 `VmSwap` 增长与 major fault、PSI、`lmkd` 事件和业务时间线放在一起。

`android17-6.18-2026-06_r6` 还包含 Multi-Gen LRU。它按访问新旧程度参与页回收选择，但不会改变 VSS、RSS、PSS 的定义。应用侧应优化工作集和访问局部性，不应把内核回收策略当作某个 VMA 可被手动解除的依据。

## 2. 建立可复现的地址空间快照

### 2.1 设备侧基础采集

下面的脚本用于在同一时间点采集页大小、VSS、RSS、线程数和 maps。调用时显式传入包名与输出目录，避免把示例包名误用于现场：

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

`VmSize` 应与 maps 中各 VMA 长度之和接近，不是最低地址到最高地址的跨度；两段 VMA 之间的空洞不计入 `VmSize`。`Threads` 应与 `/proc/<pid>/task` 数量一致。脚本中的 `pidof -s` 只选择一个 PID，多进程应用需要对每个目标进程分别采集。`dumpsys meminfo` 补充 PSS、RSS 和 heap 分类。部分量产设备会限制 `showmap` 或 `smaps`，权限失败要记录为观测缺口。

采集点至少覆盖：

- 冷启动完成；
- 进入目标业务前；
- 业务稳定运行；
- 业务退出并等待缓存回收；
- 异常前后。

只有一张峰值快照时，无法区分一次性预留、可复用缓存和持续泄漏。

### 2.2 `/proc/<pid>/maps` 怎样读

下面这一行用于说明 maps 的字段布局：

```text
70000000-78000000 ---p 00000000 00:00 0  [anon:libwebview reservation]
```

地址范围给出 VMA 起止位置；`rwx` 是访问权限；第四个字符 `p` 或 `s` 表示 private 或 shared；后面是文件偏移、设备号、inode 与可选名称。`---p` 说明当前没有读写执行权限，仍不能据此认定该区域可由应用释放。

Android 17 的 [`android_os_Debug.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Debug.cpp) 通过 `meminfo` 解析器读取进程映射并按 heap 类型汇总。应用自建分类器不应假设标签在所有厂商版本上都完全一致。

下面的离线脚本用于按 pathname 汇总 VSS，并统计无 pathname 的匿名 VMA。参数是上一节生成的 `maps.txt`：

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

汇总结果适合找大 reservation、线程栈、重复 so 和 VMA 数量异常。路径相同的多个 segment 可能分别承载代码、只读数据和可写数据，不能把汇总值直接当成私有物理内存。

### 2.3 16 KiB 页设备

`getconf PAGE_SIZE` 返回 `16384` 时，VMA 边界、guard page 和 ART 对齐都以 16 KiB 页大小计算。小对象仍可由 allocator 在页内切分；maps 只展示页级映射。

自研 native 组件需要遵守运行时页大小，[Android 的 16 KiB 页适配指南](https://developer.android.com/guide/practices/page-sizes) 要求清理写死的 `4096`、`0x1000` 或 4 KiB 对齐。解析 `start/end` 的十六进制差值不受页大小影响；调用 `mmap()`、`mprotect()`、`munmap()` 时，则要分别遵守接口对地址、offset 和 length 的约束。

这里需要区分每个系统调用的契约：文件映射的 `mmap()` offset 必须按页对齐，内核会把 length 向上覆盖到完整页；`MAP_FIXED` 地址、`mprotect()` 起始地址和 `munmap()` 起始地址有页对齐要求。不能把“所有参数都必须页对齐”当成统一规则，具体以调用的 flags 和接口文档为准。

## 3. 线程栈：先治理线程数量

### 3.1 Android 17 的 Java 线程栈计算

[`Thread::FixStackSize()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc) 的顺序很明确：

1. 传入 `0` 时改用 ART default stack size；
2. 增加 1 MiB，以兼容依赖 Dalvik 较大 native stack 的应用；
3. sanitizer 构建保证至少 2 MiB；
4. 保证不小于 `PTHREAD_STACK_MIN`；
5. 增加 stack overflow protected/reserved 区；
6. 向运行时页大小取整；
7. 把结果交给 `pthread_attr_setstacksize()` 和 `pthread_create()`。

所以“每个 Java 线程固定占 1 MiB”只是粗略说法。最终 reservation 还包含 ART default、guard/reserved 区、页对齐和构建配置。应从 maps 中的 `[anon:stack_and_tls:<tid>]` 或线程 dump 读取目标设备结果。

线程栈通常按需触页，VSS 增长会早于 RSS 增长。32 位进程中，大量线程会同时增加地址空间占用、VMA 数量、调度开销、TLS 和 native bookkeeping。

### 3.2 有界线程池

下面的 Java 工厂方法用于展示有界队列、有界线程数和命名。调用方必须传入经过压测的 worker 数与队列容量，示例不内置设备无关的固定阈值：

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

固定上限可以阻止突发任务无限扩张线程。`workerCount` 要结合 CPU/IO 比例和任务驻留内存确定，`queueCapacity` 要结合可接受排队时延确定。拒绝策略也由调用方显式选择：`CallerRunsPolicy` 会让提交线程执行任务，提交方可能是主线程时，应改用合并、拒绝或异步重试等符合业务语义的处理。

重点检查这些来源：

- `Executors.newCachedThreadPool()` 的无限最大线程数；
- 每个 SDK 各建一套线程池；
- 定时任务每次创建新线程；
- coroutine/RxJava dispatcher 误配；
- native SDK 内部的 `pthread_create()`；
- 线程退出后仍被 ThreadLocal、HandlerThread 或 executor 保活。

CPU 密集任务的并发度可从 CPU 核数起步，IO 任务没有通用的“64—128 线程”答案。应根据服务端并发限制、文件描述符、尾延迟和内存预算决定。

### 3.3 栈大小与 hook 的边界

`Thread(ThreadGroup, Runnable, String, long)` 把 stack size 定义为平台相关的建议值。Android 17 ART 还会在正数建议值上增加 1 MiB 和保护区。“传负数让无符号加法回绕成 512 KiB”依赖 Java/JNI/C++ 转换细节，属于未公开契约，构建变化后可能得到超大栈、`pthread_attr_setstacksize()` 失败或进程异常，不进入生产方案。

对 `pthread_create()` 做 PLT hook 也不能覆盖所有线程来源，并会改变系统库与三方库的栈假设。若只为诊断，可在可调试构建中记录调用栈和 attr；若要修改 stack size，必须按 ABI、4/16 KiB 页、递归深度、JNI 框架大小和极端调用链做压力测试。默认生产策略仍是减少线程数量。

### 3.4 Android 17 的虚拟线程

`android-17.0.0_r1` 的 libcore 已包含 `Thread.ofVirtual()`、`startVirtualThread()` 和 `VirtualThread` 实现，但 [`api/current.txt`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/api/current.txt) 给创建入口标记了 `com.android.libcore.virtual_thread_api_v1` `FlaggedApi`。[`ThreadBuilders.newVirtualThread()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/lang/ThreadBuilders.java) 会检查 `ContinuationSupport.isSupported()`：支持时创建 continuation 驱动的 `VirtualThread`，不支持且调用方未指定自定义 scheduler 时创建 `BoundVirtualThread`，后者由平台线程承载。

因此不能把“Android 17 虚拟线程一定不创建 pthread、每个任务都省下 1 MiB”当成通用结论。产品采用前需要确认目标镜像是否开放该 API、运行时是否支持 continuation、pinning 行为、调试工具和关键库兼容性。面向 Android 10—17 的通用实现仍应以协程、有界 executor 和结构化取消为主。

更完整的线程泄漏边界参阅 [20.19 线程泄漏与匿名线程监控](../ch20-stability/19-thread-leak-anonymous-thread-monitoring.md)。

## 4. WebView reservation：可观测，不手动解除

### 4.1 固定标签中的预留

Android 17 的 [`WebViewLibraryLoader.reserveAddressSpaceInZygote()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/webkit/WebViewLibraryLoader.java) 选择以下地址空间大小：

| 进程 ABI | reservation |
|---|---:|
| 64 位 | 1 GiB |
| 32 位 ARM | 130 MiB |
| 其他 32 位 ABI | 190 MiB |

[`loader.cpp::DoReserveAddressSpace()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/native/webview/loader/loader.cpp) 使用 `mmap(PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS)` 创建 reservation，并把全局 `gReservedAddress`、`gReservedSize` 指向该区域。maps 中的名称是 `[anon:libwebview reservation]`。

这块 reservation 会增加 VSS，未触页的 `PROT_NONE` 地址不会按 reservation 大小消耗 RSS。64 位进程看到 1 GiB VSS 增量时，不能写成“WebView 已消耗 1 GiB RAM”。

### 4.2 为什么不能 `munmap`

WebView loader 后续把 `gReservedAddress` 和 `gReservedSize` 交给 `android_dlopen_ext()`，以固定 reservation 加载 provider native library 和共享 RELRO。应用私自 `munmap()` 后，loader 的全局状态没有同步清零；地址也可能被其他映射占用。稍后任何 WebView 初始化都可能加载失败或破坏进程地址空间。

通过 hook `android_dlopen_ext()` 窃取地址、反射隐藏 `nativeLoadWithRelroFile()` 或按 maps 标签解除映射，都依赖隐藏实现。即使当前进程暂时不用 WebView，广告、登录、支付、帮助页、SDK 和系统组件也可能在后续触发 provider。

安全策略只有两类：

- 业务不需要 WebView 时，避免初始化 provider 和相关 SDK，接受 Zygote reservation 仍计入 VSS；
- 需要隔离 WebView 时，按产品架构放入受控进程，管理该进程生命周期，并测量总 PSS、启动时延和 Binder 代价。

把 WebView Activity 放到子进程不会自动移除主进程继承的 reservation；它的收益主要来自已提交页、WebView 对象与故障边界的隔离。

## 5. ART heap：应用不能释放运行时拥有的 Space

### 5.1 Homogeneous Space Compact 的适用条件

Android 17 的 [`Heap::SupportHomogeneousSpaceCompactAndCollectorTransitions()`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc) 要求同时存在 `main_space_backup_`、`main_space_`，且前台 collector 为 CMS。`PerformHomogeneousSpaceCompact()` 还会在 moving GC 已禁用、collector 已是 moving collector 或 main space 不能移动对象时拒绝执行。

同一文件的 Heap 构造路径会对 CC 和 CMC 关闭 `use_homogeneous_space_compaction_for_oom_`。这说明 HSC 是受 collector 与 space 布局约束的兼容路径，不是 Android 17 应用普遍执行的内存整理流程。它也不能推出“每个 Android 17 应用都有两块固定 512 MiB MainSpace”。ART 会按 collector、heap growth limit、设备配置和进程类型建立不同 space；RegionSpace、zygote space、large object space、image space 和 JIT 也各有生命周期。

### 5.2 JNI critical section 必须成对释放

[Android JNI tips](https://developer.android.com/training/articles/perf-jni) 对 `GetPrimitiveArrayCritical()` 的约束是：VM 可以返回直接指针或副本。调用期间，native 代码不能长时间阻塞，也不能任意调用 JNI；完成访问后必须执行 `ReleasePrimitiveArrayCritical()`。

长期保留 critical pointer 可能延迟或限制 GC，具体影响取决于 VM 返回直接指针还是副本以及当前 collector 的实现；无论哪条路径，都违反了短临界区的使用前提，并可能放大分配与线程停顿。随后 `munmap()` 任一 `dalvik-*` 区域会破坏 ART 的 allocator、card table、bitmap 与对象引用。初稿中的“禁用 moving GC 后释放备用 Space”从工程建议中删除。

应用侧能控制的是对象生命周期和分配形态：

- 取消不再需要的任务与回调；
- 对缓存设置容量和生命周期；
- 释放 Bitmap、媒体 buffer、DirectByteBuffer 与 native peer；
- 用 heap dump、Perfetto、heapprofd 和 allocation profile 找到 owner；
- 避免在内存压力回调中同步制造大量临时对象。

## 6. 多进程：改变故障边界，也增加固定成本

每个 Android 进程都有独立的虚拟地址空间、ART runtime、Binder 状态和 native allocator。把模块移入子进程会降低主进程中的已提交页与对象数量，但整个应用的总 PSS 可能上升。

下面的 manifest 片段用于说明私有进程声明：

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
- native 崩溃风险较高，需要限制影响范围；
- 已提交内存大，主进程长期不需要保留；
- IPC 接口小，避免高频传大对象；
- 被 LMKD 回收后可以恢复。

大 payload 可考虑 `SharedMemory`、文件描述符或流式传输；仍要定义所有权、校验长度并及时关闭 FD。多进程不能用来规避应用整体内存预算。

## 7. 建立面向原因的监控

### 7.1 采样字段

一条可解释的虚拟内存快照至少包含：

- 时间、业务场景、进程名、PID、ABI 和页大小；
- `VmSize`、`VmPeak`、`VmRSS`、`RssAnon`、`RssFile`、`VmSwap`；
- 线程数、VMA 数量和 FD 数量；
- Java heap、native heap、graphics、code 与 stack 的 PSS；
- 占用较大的 VSS 分类及其 VMA 数量，保留多少类由报告容量决定；
- 最近一次 `mmap`、`pthread_create` 或 allocator 失败信息。

采样频率按风险控制。`/proc/self/status` 成本较低，可在场景边界采样；读取并解析 `maps`、`smaps` 或抓 heap dump 应由异常触发，避免高频磁盘读取和主线程阻塞。

### 7.2 阈值按设备分组

“五分钟增长 100 MiB”或“接近 2 GiB 就报警”缺少 ABI、业务和基线条件。更稳妥的方式是按以下维度建立分位数：

- 32/64 位 ABI；
- Android 版本与页大小；
- 设备内存档位；
- 进程角色；
- 冷启动、稳定态、退出后；
- 线程数与 VMA 数量。

告警应组合 `VmSize` 增量、RSS/PSS 增量、线程/VMA 增量和错误信号。VSS 上升后 RSS 不变、业务退出后保持稳定，通常只是 reservation 或可复用映射；VSS、RSS、线程数一起持续上升时，调查优先级更高。

## 8. 常见现场怎样收敛

### 8.1 `pthread_create` 失败

1. 保存 ART 错误中的 requested stack size 和 errno；
2. 记录 `/proc/<pid>/status` 的 `Threads`、`VmSize` 和 `VmRSS`；
3. 按 thread name、创建栈和 owner 聚合；
4. 检查 cached pool、HandlerThread、SDK 与 native 线程；
5. 先减少线程，再评估受控线程的 stack size。

### 8.2 32 位进程 `mmap` 失败

1. 记录申请长度、flags、errno 和调用栈；
2. 保存完整 maps；
3. 计算最大连续空洞，不能只用地址总范围减 VSS；
4. 检查大 reservation、重复库、线程栈和 VMA 数量；
5. 优先提供 64 位 ABI 并减少映射 owner。

### 8.3 VSS 很大但设备没有内存压力

检查大区域是否为 `PROT_NONE`、文件映射、ART reserve 或 WebView reservation，再看 RSS/PSS 与 page fault。没有失败信号时，不为缩小面板数字去解除系统映射。

### 8.4 多进程后主进程变小、整机更卡

把所有进程的 PSS 相加，并检查进程反复冷启、Binder payload、共享页分摊和 LMKD 回收。主进程单项下降无法证明方案节省了整机内存。

## 9. 优化顺序

| 顺序 | 动作 | 风险 |
|---|---|---|
| P0 | 记录 ABI、页大小、VSS/RSS/PSS、线程和 VMA 的同点快照 | 低 |
| P0 | 收敛线程 owner，使用有界 executor，清理失控的 HandlerThread/SDK 线程 | 低 |
| P0 | 修复对象、native buffer、Bitmap、DirectByteBuffer 和映射生命周期 | 低 |
| P1 | 评估 64 位 ABI 覆盖，针对 32 位碎片做专项测试 | 中 |
| P1 | 按总 PSS 和生命周期评估进程隔离 | 中 |
| P2 | 在可调试构建中 hook `mmap`/`pthread_create` 做取证 | 中 |
| 禁止 | `munmap` WebView reservation 或 ART heap space | 高 |
| 禁止 | 永久持有 JNI critical pointer 来阻止 moving GC | 高 |
| 禁止 | 用负数 stack size 依赖无符号回绕 | 高 |

虚拟内存优化的目标是让地址空间与资源生命周期可解释。32 位进程重点看连续空洞、线程栈和 VMA；64 位进程重点区分 reservation 与物理页，并把 PSS/RSS、线程和失败信号放在同一份报告中。

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
