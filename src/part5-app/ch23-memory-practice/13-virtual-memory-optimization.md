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
    path: "[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些"黑科技"优化手段.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
tags: [virtual-memory, VSS, thread-stack, maps-analysis, oom-prevention, memory-optimization, webview-reservation]
related_chapters: ["20.5", "4.3", "4.4", "23.6", "23.3", "5.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-03"
gap_source: "Clippings结构参考/AOSP结构"
gap_score: 16
material_count: 4
---

# 23.13 应用虚拟内存优化实战

## 概述

虚拟内存（Virtual Memory）是 Android 应用稳定性的隐形天花板。虽然 64 位设备理论上拥有 256TB 的虚拟地址空间，几乎不会耗尽，但在 32 位进程（3GB user space）以及系统对单进程虚拟内存总量的隐性限制下，VSS（Virtual Set Size）不足仍然会导致 `mmap` 失败、线程创建失败、甚至 native OOM 崩溃。

本节聚焦应用层的虚拟内存优化实践，覆盖六个核心方向：VSS 构成分析、线程栈治理、多进程隔离、maps 文件解析、WebView 预留释放、ART GC 后台空间管理。这些手段在中大型应用（尤其 32 位包）中可直接降低 OOM 率。

> **与 Part 1 的关系**：Part 1 ch04 讲述了 ART 内存管理和 LMK 的底层机制（详见 4.3、4.4），本节关注的是「应用开发者能做什么」。

---

## 🔹 虚拟内存基础与 Android 应用 VSS 构成

### 32 位 vs 64 位进程的地址空间

| 架构 | 用户态虚拟地址空间 | 实际可用（含系统保留） | VSS 耗尽风险 |
|------|-------------------|----------------------|-------------|
| 32 位 ARM | 3GB（1GB 内核） | ~2.5GB | ⚠️ 高 |
| 64 位 ARM (AArch64) | 256TB | 实际受 per-process limit 限制（通常 128GB~256GB） | ✅ 极低 |

从 Android 14 开始，新设备必须使用 64 位 CPU，且新提交的应用必须提供 64 位包。但在 Android 17（API 37）的时间节点，大量存量 32 位包仍然活跃在旧设备上，虚拟内存优化对它们依然至关重要。

[适用版本: Android 10 (32 位包) - Android 17 (64 位包)]

### Android 应用 VSS 主要消耗者

通过 `/proc/self/maps` 分析一个典型中型 Android 应用，VSS 的主要消耗来源如下：

| 消耗来源 | 典型大小（64 位） | 典型大小（32 位） | 说明 |
|----------|------------------|------------------|------|
| ART MainSpace (RegionSpace) | 512MB | 512MB | 主 Java 堆，Zygote fork 时预分配 |
| ART LargeObjectSpace | 512MB | 512MB | 大对象分配区 |
| 线程栈（每线程 ~1MB） | N × 1MB | N × 1MB | 100 线程 ≈ 100MB |
| so 库映射（.text + .data + .bss） | 50~150MB | 30~80MB | 系统 so + 三方 so |
| WebView 预留 (libwebview reservation) | 1GB | 130MB | Zygote 预申请 |
| mmap 匿名映射 | 变化大 | 变化大 | Native 内存、JIT cache 等 |
| Dalvik 其他空间 (LinearAlloc, JIT 等) | 10~30MB | 5~15MB | ART 内部数据结构 |

在 32 位进程上，仅 MainSpace + LargeObjectSpace + WebView 预留就消耗 ~1.15GB，几乎占掉 3GB user space 的 38%。

### /proc/self/maps 结构与解析

`/proc/self/maps`（或 `/proc/{pid}/maps`）是 Linux 内核维护的进程虚拟内存映射表，每一行代表一段连续的虚拟地址区域：

```
address           perms offset  dev   inode    pathname
12c00000-32c00000 rw-p  00000000 00:00 0        [anon:dalvik-main space (region space)]
```

| 字段 | 含义 |
|------|------|
| address | 起始-结束虚拟地址（十六进制） |
| perms | r=读 w=写 x=执行 p=私有 s=共享 |
| offset | 文件映射偏移量 |
| dev | 设备号（major:minor） |
| inode | 文件 inode 号 |
| pathname | 映射来源（文件路径或 `[anon:...]` 标签） |

Android 系统通过 `android_os_Debug.cpp` 的 `load_maps()` 函数解析此文件并分类统计各类内存占用（详见 23.3 节对 Native 内存分析的讨论）。`load_maps()` 的核心逻辑是根据 pathname 前缀将每段映射分类到 `HEAP_DALVIK`、`HEAP_NATIVE`、`HEAP_SO`、`HEAP_STACK` 等类别。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/android_os_Debug.cpp]

### Android 17 对 VSS 的影响

Android 17 在内存管理方面有几项与 VSS 相关的变化：

1. **16KB page size 对齐**：部分新设备采用 16KB 内存页（而非传统 4KB），maps 文件中映射地址按 16KB 对齐，单页粒度更大。这对 mmap 粒度有直接影响——小粒度内存申请仍可通过 sub-page 分配，但 VSS 统计上每个映射单元最小 16KB。

2. **Generational CC（分代并发拷贝 GC）**：ART 的 GC 策略进一步优化，RegionSpace 的后台压缩行为有调整，对「释放备用 Space」类优化方案的可行性有影响（后文详述）。

3. **64 位 only 设备成为主流**：新出厂设备几乎全部 64 位，32 位包的 VSS 瓶颈在新设备上不再是问题，但存量长尾设备仍需关注。

[待验证: Android 17 Generational CC 对 PerformHomogeneousSpaceCompact 的具体影响，需对照 android-17.0.0_r1 的 heap.cc 源码确认]

[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]

---

## 🔹 线程栈虚拟内存治理

### 线程创建与 FixStackSize

每个 Java 线程默认占用约 1MB 虚拟内存作为栈空间。这一行为的根源在 ART 源码中：

**调用链**：`Thread.start()` → `Thread.nativeCreate()` → `Thread::CreateNativeThread()` → `FixStackSize()` → `pthread_create()` → `clone()`

在 `art/runtime/thread.cc` 中，`FixStackSize` 的核心逻辑：

```cpp
static size_t FixStackSize(size_t stack_size) {
    if (stack_size == 0) {
        stack_size = Runtime::Current()->GetDefaultStackSize();
    }
    stack_size += 1 * MB;  // 默认在传入值基础上 +1MB
    // ... page alignment ...
    return stack_size;
}
```

当 `Thread` 构造函数将 `stackSize` 设为 0 时（默认行为），`FixStackSize` 会在其基础上增加 1MB。因此即使不在 Java 层显式设置 stackSize，每个线程依然占用 ~1MB 虚拟内存。

`pthread_create` 最终调用 Linux 内核的 `clone()` 系统调用，通过 `mmap` 分配指定大小的虚拟地址空间作为线程栈。在 `/proc/self/maps` 中表现为 `[anon:stack_and_tls:tid]` 条目。

[已验证: AOSP android-17.0.0_r1, art/runtime/thread.cc]

### 线程数与 VSS 的线性关系

| 线程数 | 栈空间 VSS（默认 1MB/线程） |
|--------|--------------------------|
| 50 | ~50MB |
| 100 | ~100MB |
| 200 | ~200MB |

在 32 位进程中，200 个线程的栈空间就消耗了 3GB user space 的 ~6.5%，这还不包括线程运行时分配的其他内存。

### 优化手段一：线程池化

**核心策略**：将应用中分散的 `new Thread()` 和 `newFixedThreadPool()` 统一收敛到公共线程池。

**线程池分类设计**：

| 线程池类型 | 核心线程数 | 最大线程数 | 适用场景 |
|-----------|-----------|-----------|---------|
| CPU 线程池 | `Runtime.availableProcessors()` | 同核心线程数 | 计算、逻辑处理 |
| IO 线程池 | 0~3 | 64~128 | 网络请求、文件读写 |

CPU 线程池核心线程数设为 CPU 核数，理想状态下每核运行一个线程，减少调度损耗。IO 线程池核心线程数设为 0（或少量），因为 IO 任务不需要即时响应，常驻线程越少越好。

**野线程收敛**：

- **简单场景**：全局搜索 `new Thread()` 和 `Executors.newFixedThreadPool()`，手动替换为公共线程池调用。
- **复杂场景（三方库）**：使用字节码织入（如 Lancet）hook `Executors.newFixedThreadPool`，将返回值替换为公共线程池实例：

```java
@TargetClass("java.util.concurrent.Executors")
@Proxy(value = "newFixedThreadPool")
public static ExecutorService newFixedThreadPool(int nThreads) {
    return GlobalThreadPool.getInstance().getIOExecutor();
}
```

[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]

### 优化手段二：减小线程栈大小

**方案 A — Java 层修改 stackSize**：

`FixStackSize` 的逻辑为 `stack_size += 1 * MB`。如果传入 `-512KB`（即 `0xFFFFFFFFFFF80000` 作为 `size_t`），结果为 `1MB - 512KB = 512KB`。

在公共线程池的自定义 `ThreadFactory` 中设置：

```java
ThreadFactory customFactory = new ThreadFactory() {
    @Override
    public Thread newThread(Runnable r) {
        // stackSize = -512KB → FixStackSize 后实际栈大小为 512KB
        Thread t = new Thread(threadGroup, r, threadName, -512 * 1024L);
        t.setPriority(Thread.NORM_PRIORITY);
        return t;
    }
};
```

**方案 B — PLT Hook pthread_create**：

Hook `libc.so` 的 `pthread_create`，在回调中修改 `pthread_attr_t` 的 stack size：

```c
static int (*orig_pthread_create)(pthread_t*, const pthread_attr_t*,
                                   void*(*)(void*), void*);

static int hooked_pthread_create(pthread_t* thread, const pthread_attr_t* attr,
                                  void*(*start_routine)(void*), void* arg) {
    pthread_attr_t modified_attr;
    pthread_attr_init(&modified_attr);
    if (attr != nullptr) {
        pthread_attr_copy(&modified_attr, attr);  // Android 16+
    }
    pthread_attr_setstacksize(&modified_attr, 512 * 1024);  // 512KB
    int ret = orig_pthread_create(thread, &modified_attr, start_routine, arg);
    pthread_attr_destroy(&modified_attr);
    return ret;
}
```

**方案对比**：

| 方案 | 实现难度 | 覆盖范围 | 兼容性风险 |
|------|---------|---------|-----------|
| Java 层 stackSize | ⭐ 低 | 仅公共线程池创建的线程 | 低（需收集栈溢出 case） |
| PLT Hook pthread_create | ⭐⭐⭐ 高 | 所有线程（含三方库） | 中（需处理 attr 为 nullptr 的情况） |

**实践建议**：优先使用 Java 层方案，对公共线程池统一设置。个别栈深度大的线程（如递归调用链长的任务）不缩减栈，通过线上监控收集 StackOverflowError 后调整。

[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]

### 优化手段三：Android 17 Thread.Builder

Android 13（API 33）引入了 `Thread.ofPlatform()` 和 `Thread.ofVirtual()` Builder API。在 Android 17 上，这些 API 更成熟：

```java
Thread.Builder builder = Thread.ofPlatform()
    .name("worker-", 0)
    .daemon(true)
    .unstarted(runnable);

// 虚拟线程（协程）不占用固定 1MB 栈空间
Thread virtualThread = Thread.ofVirtual()
    .name("vt-", 0)
    .start(runnable);
```

虚拟线程（Virtual Thread / Project Loom）在 ART 上的实现方式与传统平台线程不同，不通过 `pthread_create` 创建，而是由 ART 运行时调度在少量载体线程（carrier thread）上运行，栈空间按需分配/释放，不预分配 1MB。

[适用版本: Android 13 (API 33) - Android 17 (API 37)]
[待验证: Android 17 ART 虚拟线程的 VSS 实际占用测量数据]

---

## 🔹 多进程架构的虚拟内存优化

### 原理

将大内存模块隔离到独立进程中，子进程拥有独立的虚拟地址空间。主进程的 VSS 因此显著降低，同时大内存模块的崩溃也不会波及主进程。

### 适合放入子进程的业务

| 业务类型 | VSS 消耗特征 | 子进程收益 |
|----------|-------------|-----------|
| WebView / H5 容器 | 1GB 预留 + 渲染内存 | 主进程释放 1GB 预留 |
| 地图 SDK（高德/百度） | 100~300MB | 主进程 VSS 降低 100MB+ |
| 视频编解码 / 直播 SDK | 50~200MB | 减少编解码缓冲 VSS |
| 音频处理 / 语音 SDK | 50~100MB | 隔离音频缓冲 |
| SDK 初始化密集型 | 各 SDK 各自 50~100MB | 减少初始化堆积 |

### 实施方式

**AndroidManifest 配置**：

```xml
<activity
    android:name=".WebViewActivity"
    android:process=":webview" />

<service
    android:name=".MapService"
    android:process=":map" />
```

冒号前缀（`:webview`）表示私有进程，其他应用无法访问。

**多进程通信**：子进程与主进程通过 Binder/AIDL 通信。需注意：

- 序列化开销：大数据传递考虑 SharedMemory 或 MemoryFile
- 启动延迟：子进程首次创建需 ~200~500ms，可通过预启动（提前触发空 Activity）优化

### 与 LMKD 的协作

详见 4.4 节对 Low Memory Killer 的分析。多进程架构下，LMKD 根据 oom_adj 分数决定杀进程顺序：

- 主进程（前台）oom_adj 低，优先级高
- 子进程（后台 WebView 进程）oom_adj 高，优先被杀

这意味着在内存紧张时，系统会自动回收子进程释放物理内存，但虚拟内存层面的进程地址空间也会随之释放。

> **交叉引用**：多进程策略的整体设计与 `largeHeap`、内存预算管理详见 23.6 节。

[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]

---

## 🔹 /proc/self/maps 分析方法论

### maps 文件格式详解

每行格式如下：

```
722d0a6000-722d0b7000 rw-p 00000000 00:00 0    [anon:libwebview reservation]
```

解析规则：
- 地址范围由空格分隔为起始和结束（十六进制）
- perms 四字符：`r/w/x/-` + `p/s`（私有/共享）
- pathname 为 `[anon:...]` 表示匿名映射的命名标签，通过 `prctl(PR_SET_VMA, PR_SET_VMA_ANON_NAME, ...)` 设置

### 按类型分类统计 VSS

编写解析脚本，将每行按 pathname 分类，累加 `end - start` 得到各类型 VSS：

```python
import re
from collections import defaultdict

def analyze_maps(maps_path="/proc/self/maps"):
    categories = defaultdict(int)
    with open(maps_path) as f:
        for line in f:
            parts = line.split(None, 5)
            if len(parts) < 5:
                continue
            addr_range = parts[0]
            start, end = [int(x, 16) for x in addr_range.split("-")]
            size_mb = (end - start) / (1024 * 1024)
            pathname = parts[5].strip() if len(parts) > 5 else "[anonymous]"

            if "[anon:dalvik-main space" in pathname:
                categories["ART MainSpace"] += size_mb
            elif "[anon:dalvik-large object space" in pathname:
                categories["ART LargeObjectSpace"] += size_mb
            elif "[anon:stack_and_tls" in pathname:
                categories["Thread Stack"] += size_mb
            elif "[anon:libwebview reservation" in pathname:
                categories["WebView Reservation"] += size_mb
            elif pathname.endswith(".so"):
                categories["SO Library"] += size_mb
            elif pathname == "[heap]" or "[anon:libc_malloc" in pathname:
                categories["Native Heap"] += size_mb
            elif not pathname or pathname == "[anonymous]":
                categories["Anonymous mmap"] += size_mb
            else:
                categories["Other"] += size_mb

    for cat, size in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"{cat:30s} {size:10.1f} MB")
```

### 识别可释放的虚拟内存区域

判定标准：
1. **大小 > 10MB**：小区域不值得释放风险
2. **perms 包含 `-p`（私有且无权限）**：说明是预留但未使用的保留区
3. **可识别来源且确认不需要**：如 `libwebview reservation`（应用不使用系统 WebView）

### 16KB page size 对 maps 的影响

在 Android 17 的 16KB page 设备上，maps 中的地址对齐从 4KB（`0x1000`）变为 16KB（`0x4000`）。解析脚本中的地址计算不受影响（都是十六进制减法），但每个映射的最小粒度从 4KB 变为 16KB。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/android_os_Debug.cpp (load_maps 分类逻辑)]

---

## 🔹 WebView 预留虚拟内存释放

### WebView 预留机制

Zygote 进程在启动时加载 `libwebviewchromium_loader.so`，通过 `DoReserveAddressSpace()` 函数调用 `mmap` 预留一块虚拟内存：

| 架构 | 预留大小 | 来源 |
|------|---------|------|
| 64 位 ARM | ~1GB | `WebViewLibraryLoader.java` |
| 32 位 ARM | ~130MB | 同上 |
| 其他（x86 等） | ~190MB | 同上 |

所有应用进程由 Zygote fork 而来，继承这块预留区域。预留地址和大小存储在 `loader.cpp` 的全局变量 `gReservedAddress` 和 `gReservedSize` 中。

从 Android 10 开始，系统通过 `prctl(PR_SET_VMA, PR_SET_VMA_ANON_NAME, ...)` 将此区域命名为 `[anon:libwebview reservation]`，在 maps 文件中可见。Android 9 及以下该区域为匿名，无法通过名称定位。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebViewLibraryLoader.java + frameworks/base/native/webview/loader/loader.cpp]

### 释放方案

#### 方案一：解析 maps（Android 10+）

适用于 maps 中能看到 `[anon:libwebview reservation]` 标签的系统版本：

```c
// 1. 扫描 /proc/self/maps 找到 libwebview reservation 区域
void* reserved_start = nullptr;
size_t reserved_size = 0;

FILE* fp = fopen("/proc/self/maps", "r");
char line[512];
while (fgets(line, sizeof(line), fp)) {
    uintptr_t start, end;
    char perms[5];
    char pathname[256];
    if (sscanf(line, "%lx-%lx %4s %*x %*x:%*x %*d %255[^\n]",
               &start, &end, perms, pathname) == 4) {
        if (strcmp(pathname, "[anon:libwebview reservation]") == 0) {
            reserved_start = (void*)start;
            reserved_size = end - start;
            break;
        }
    }
}
fclose(fp);

// 2. 释放
if (reserved_start && reserved_size > 0) {
    munmap(reserved_start, reserved_size);
}
```

#### 方案二：PLT Hook android_dlopen_ext（全版本兼容）

对于 Android 9 及以下无法通过 maps 名称定位的设备，通过 PLT Hook 拦截 `libwebviewchromium_loader.so` 对 `android_dlopen_ext` 的调用，从 `android_dlextinfo` 结构体中提取 `reserved_addr` 和 `reserved_size`：

```c
typedef struct {
    uint64_t flags;
    void* reserved_addr;    // 即 gReservedAddress
    size_t reserved_size;   // 即 gReservedSize
    int relro_fd;
    int library_fd;
    off64_t library_fd_offset;
    struct android_namespace_t* library_namespace;
} android_dlextinfo;

static void* (*orig_dlopen_ext)(const char*, int, const void*);

static void* hooked_dlopen_ext(const char* filename, int flags,
                                const void* extinfo) {
    if (extinfo) {
        auto info = (const android_dlextinfo*)extinfo;
        if (info->reserved_addr && info->reserved_size > 0) {
            sReservedAddr = info->reserved_addr;
            sReservedSize = info->reserved_size;
        }
    }
    return orig_dlopen_ext(filename, flags, extinfo);
}

// 通过 bytehook / bhook 注册
bytehook_hook_single(
    nullptr,
    "libwebviewchromium_loader.so",
    "android_dlopen_ext",
    (void*)hooked_dlopen_ext,
    nullptr, nullptr);
```

**触发 android_dlopen_ext 调用**：`gReservedAddress` 仅在 `DoCreateRelroFile()` 或 `DoLoadWithRelroFile()` 执行时被使用。应用如果未启动 WebView，这两个函数不会被自动调用。需要在 Native 层主动触发 `WebViewLibraryLoader.nativeLoadWithRelroFile()` 来促使框架调用 `android_dlopen_ext`：

```c
// JNI 层主动调用 WebViewLibraryLoader 的 native 方法
JNIEnv* env = ...
jclass clazz = env->FindClass("android/webkit/WebViewLibraryLoader");
// 不同 Android 版本参数签名不同，需遍历尝试
jmethodID method = env->GetStaticMethodID(clazz,
    "nativeLoadWithRelroFile",
    "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/ClassLoader;)I");
```

> **注意**：系统会自动为 native 方法添加包名前缀，直接反射调用可能失败。需要通过 Native 层的 JNI 接口绕过此限制。

### 适用场景与风险评估

| 场景 | 是否建议释放 | 风险 |
|------|------------|------|
| 应用不使用任何 WebView | ✅ 强烈建议 | 极低 |
| WebView 已隔离到子进程 | ✅ 主进程释放 | 低 |
| 应用主进程直接使用 WebView | ❌ 不建议 | 高（WebView 崩溃） |

[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些"黑科技"优化手段.md]

---

## 🔹 ART GC 后台空间释放

### 背景：拷贝回收与备用 Space

在 Android 5~7 的 ART 运行时中，Java 堆使用两块 MainSpace（main space + main space 1），每块 512MB，共 1GB 虚拟内存。这是为 **Homogeneous Space Compact（同构空间压缩）** GC 算法预留的备用空间。

当应用进入后台或 Java 堆内存不足时，ART 执行拷贝回收：将存活对象从当前 Space 复制到另一块干净的 Space，然后释放原 Space。这需要两块等大的 Space 交替使用。

### 禁用拷贝回收的方案

通过 `GetPrimitiveArrayCritical()` / `GetStringCritical()` 可以将 ART 内部的 `disable_moving_gc_count_` 计数器加 1，阻止拷贝回收执行：

```c
// 在 JNI 层执行，禁用 moving GC
jbyteArray arr = env->NewByteArray(1);
void* ptr = env->GetPrimitiveArrayCritical(arr, nullptr);
// 不调用 ReleasePrimitiveArrayCritical → disable_moving_gc_count_ 保持为 1
// 拷贝回收被永久禁用
```

在 `heap.cc` 的 `PerformHomogeneousSpaceCompact()` 中：

```cpp
if (disable_moving_gc_count_ != 0 || IsMovingGc(collector_type_) ||
    !main_space_->CanMoveObjects()) {
    return kErrorReject;  // ← 中断拷贝回收
}
```

禁用后，可以安全释放备用 MainSpace 的虚拟内存。

### 释放备用 Space

```c
// 通过 GetPrimitiveArrayCritical 返回的指针判断当前使用哪块 Space
uintptr_t arrAddr = (uintptr_t)ptr;
if (arrAddr >= space1Start && arrAddr < space1End) {
    // 当前使用 Space1，释放 Space2
    munmap((void*)space2Start, space2Size);
} else {
    // 当前使用 Space2，释放 Space1
    munmap((void*)space1Start, space1Size);
}
```

实际落地时应通过解析 `/proc/self/maps` 获取 `dalvik-main space` 和 `dalvik-main space 1` 的确切地址，不硬编码。

### Android 8+ 的变化

从 Android 8 开始，ART 默认使用 RegionSpace 替代传统的双 MainSpace 设计。RegionSpace 将堆划分为多个 Region，GC 时在 Region 级别进行压缩，不再需要整块备用 Space。

因此在 Android 8+ 设备上，此优化方案的适用性降低。**该方案主要针对 Android 5~7 的存量设备**，这些设备在 2026 年的时间节点占比已很低。

[待验证: Android 17 Generational CC 下，RegionSpace 的后台压缩是否仍有可释放的预留区域，需对照 android-17.0.0_r1 的 art/runtime/gc/heap.cc 和 space_region.cc 确认]

### 风险评估

禁用拷贝回收会增加内存碎片（无法通过拷贝整理碎片），可能导致可用堆内存减少。但实际线上验证（字节跳动抖音团队大规模 A/B 测试）表明：

- Java 堆 OOM 率未显著提升
- 虚拟内存不足导致的 native OOM 率有明显下降
- 原因：应用进程不是常驻的，用一段时间后会被系统或用户杀死，碎片累积有限

> **交叉引用**：OOM 的完整治理策略（FD 泄漏、线程数超限、native OOM 等）详见 20.5 节。

[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些"黑科技"优化手段.md]

---

## 🔸 虚拟内存监控与告警体系

### VSS 定期采样方案

在应用运行期间，定期读取 `/proc/self/maps` 或使用 `Debug.getMemoryInfo()` 采集 VSS 数据。但 `load_maps` 解析开销较大，Android 10+ 对此加了 5 分钟频控。

**轻量级替代方案**：

```java
// 通过 ActivityManager 获取总 PSS（不含 VSS 明细，但开销小）
ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
ActivityManager am = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
am.getMemoryInfo(mi);
// mi.totalMem - 可用内存，但不直接反映进程 VSS

// 更精确：读取 /proc/self/status 中的 VmSize（单文件读取，开销极小）
// VmSize 即进程总虚拟内存大小
```

```c
// Native 层读取 VmSize
long get_vss_kb() {
    FILE* fp = fopen("/proc/self/status", "r");
    char line[256];
    long vss = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (sscanf(line, "VmSize: %ld kB", &vss) == 1) {
            break;
        }
    }
    fclose(fp);
    return vss;
}
```

### VSS 增长趋势分析与异常检测

- **基线建立**：在冷启动后 30s、60s、120s 分别采样 VSS，建立各时间点的基线范围
- **异常检测规则**：
  - VSS 在 5 分钟内增长 > 100MB → 疑似内存泄漏
  - VSS 持续接近 2GB（32 位进程）→ 预警
  - 线程数突增 → 可能导致 VSS 线性增长

### 与 MemoryAdvice API 的集成

Google 提供的 [Memory Advice API](https://developer.android.com/games/sdk/memory-advice)（最初为游戏设计，但通用可用）可以在内存压力时回调通知：

```java
MemoryAdvice.registerWatcher(new MemoryAdvice.MemoryWatcher() {
    @Override
    public void onWarning(int warningState) {
        if ((warningState & MemoryAdvice.RED) != 0) {
            // 红色警告：内存极度紧张，立即释放资源
            releaseCaches();
            notifyBackground();
        } else if ((warningState & MemoryAdvice.YELLOW) != 0) {
            // 黄色警告：内存压力上升
            reduceCacheSize();
        }
    }
});
```

[适用版本: Android 10 (API 29) - Android 17 (API 37)]

---

## 🔸 Native Hook 在虚拟内存优化中的应用

### PLT Hook 拦截 mmap/munmap

通过 PLT Hook（如 bytehook / bhook）拦截 so 库的外部函数调用，可以监控和管理虚拟内存分配：

```c
// Hook mmap 监控所有 mmap 调用
static void* (*orig_mmap)(void*, size_t, int, int, int, off_t);

static void* hooked_mmap(void* addr, size_t length, int prot, int flags,
                          int fd, off_t offset) {
    void* result = orig_mmap(addr, length, prot, flags, fd, offset);
    if (length > 1024 * 1024) {  // 仅记录 > 1MB 的映射
        log_mmap_allocation(result, length, prot, flags);
    }
    return result;
}
```

### 线程创建监控

Hook `pthread_create` 可以同时实现线程创建监控和栈大小定制：

```c
static int hooked_pthread_create(pthread_t* thread, const pthread_attr_t* attr,
                                  void*(*start)(void*), void* arg) {
    size_t stack_size = 0;
    if (attr) {
        pthread_attr_getstacksize(attr, &stack_size);
    }
    // 记录线程创建堆栈
    log_thread_creation(stack_size);
    // 可选：调整栈大小
    return orig_pthread_create(thread, attr, start, arg);
}
```

### Android 17 PLT Hook 兼容性

在 Android 17 上，PLT Hook 面临以下兼容性考量：

1. **16KB page size**：ELF 加载对齐变化，但不影响 PLT/GOT 表结构
2. ** stricter namespace**：Android 11+ 的 `android_namespace_t` 限制了 so 库加载范围，但 PLT Hook 在进程内操作，不受 namespace 限制
3. **RLIMIT_AS**：部分 OEM 设备通过 `setrlimit(RLIMIT_AS, ...)` 限制进程虚拟内存上限，hook 此调用可以观测但不应绕过

[适用版本: PLT Hook 技术从 Android 7.0 起广泛使用，至 Android 17 兼容性良好]
[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上/下）.md]

---

## 实践总结

### 优化优先级排序

| 优先级 | 优化手段 | VSS 收益 | 实现难度 | 风险 |
|--------|---------|---------|---------|------|
| P0 | 线程池化 + 栈大小减半 | 50~150MB | ⭐ | 低 |
| P0 | 多进程隔离大内存模块 | 100MB~1GB | ⭐⭐ | 低 |
| P1 | WebView 预留释放（不用 WebView 时） | 130MB~1GB | ⭐⭐⭐ | 中 |
| P2 | maps 分析 + 专项释放 | 视情况 | ⭐⭐ | 中 |
| P3 | 禁用拷贝回收 + 释放备用 Space | ~512MB | ⭐⭐⭐ | 中（仅 Android 5~7） |

### 32 位 vs 64 位策略差异

**32 位进程**（存量旧设备）：
- 全部优化手段都需要认真实施
- VSS 是实际崩溃风险因素
- 建议推动用户升级到 64 位包

**64 位进程**（Android 14+ 新设备主流）：
- 线程池化和多进程架构仍有价值（减少物理内存，提升性能）
- WebView 预留释放必要性降低（1GB 对 256TB 微不足道）
- 重点关注物理内存（PSS/RSS/USS）而非虚拟内存

### 与其他章节的关系

| 主题 | 机制原理 | 实战策略 |
|------|---------|---------|
| ART 内存管理 | → 4.3 | 本节（23.13） |
| LMK 与进程优先级 | → 4.4 | 本节多进程部分 |
| OOM 治理全景 | → 20.5 | 本节 VSS 专项 |
| 多进程架构设计 | → 23.6 | 本节 VSS 视角 |
| Native 内存优化 | → 23.3 | 本节虚拟内存视角 |
| 内存分析工具 | → 14.3 | 本节 maps 分析 |

---

> 📝 本节内容基于 Clippings 参考书的结构参考和知识点索引，结合 AOSP android-17.0.0_r1 源码验证撰写。所有源码引用已标注 `[已验证]`，未能独立验证的部分标注 `[待验证]`。
