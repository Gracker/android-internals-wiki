---
title: "OOM 治理"
chapter: "20.5"
section: "20.5"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-12"
last_verified_against: "AOSP android-16.0.0_r1, art/runtime/gc/heap.cc"
confidence: medium
drafted_date: "2026-05-12"
polish_count: 0
sources:
  - type: aosp
    path: "art/runtime/gc/heap.cc"
  - type: aosp
    path: "art/runtime/thread.cc"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 初识内存：内存是什么？.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md"
tags: [oom, memory, thread-limit, fd-leak, virtual-memory]
related_chapters: ["20.1", "23.1", "23.4", "4.3", "4.4"]
review_count: 3
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
created_by: "task2a"
reviewed_date: "2026-06-01"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
last_task6_at: "2026-06-01T18:10:00+08:00"
last_task6_review_log: "logs/review/2026-06-01-18-review.md"
task6_review_notes: "2026-06-01 18 Task6 revisiting-review: pass-light-edit。删除虚拟内存治理重复 bullet，收敛口语化“这招”；L1/L2 通过，无新增回炉项，送 Task9 复核。"
task9_result: "pass-tech-review"
task2b_result: "fixed-lite"
last_task2b_at: '2026-05-13T19:33:05+08:00'
last_task2b_lite_at: "2026-06-01"
last_task9_at: "2026-06-01T18:21:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-01"
last_task9_review_log: "logs/deep-review/2026-06-01-18-deep-review.md"
task9_review_notes: "2026-06-01 Task9 18:21：pass-tech-review。复核 Task6 回流后的 OOM 治理；ART OOME 投递、Heap::ThrowOutOfMemoryError、JNI/native alloc、Bitmap native heap、pthread_create 与 heapprofd 边界经 AOSP android-16.0.0_r1 复核，无新增 P0/P1，自动晋升 finalized。"
last_task9_autofix_at: "2026-06-01"
last_task9_audit: "2026-06-21"
---

# OOM 治理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 OOM 的 ART 投递机制与预分配 OOM 对象兜底
- 🔹 Java Heap OOM 的错误字段、产生路径与治理方向
- 🔹 Native 内存 OOM、线程数 OOM、FD 泄漏 OOM 与虚拟内存耗尽的排查入口
- 🔹 OOM 兜底、安全降级与大型 App 内存预算管理

### OpenClaw 加工指引

> 锚点是最低覆盖要求，review 时需要确认每个锚点都有对应正文和验证标注。
<!-- outline-end -->

Android 应用遇到的 OutOfMemoryError 并不只有"堆内存不够"这一种。按照错误来源，可以分成两类：ART 虚拟机自身的堆限制（256 MB / 512 MB growth_limit），和 Linux 进程层面的虚拟内存、FD、线程数限制。两类 OOM 的约束来源不同，排查路径也不同——归类是治理的第一步。

本节从 OOM 的产生路径入手，逐类讲解 Java Heap OOM、Native 内存 OOM、线程数 OOM、FD 泄漏 OOM、虚拟内存空间耗尽的排查思路和治理策略。

## OOM 的投递机制

ART 里所有 OutOfMemoryError 最终都经过 `Thread::ThrowOutOfMemoryError`（`art/runtime/thread.cc`）。该函数在 Native 层设置 `tls32_.throwing_OutOfMemoryError` 标志，通过 `ThrowNewException` 构造 `Ljava/lang/OutOfMemoryError;` 对象。线程从 Native 返回 Java 层时检查 pending exception，触发 `UncaughtExceptionHandler`，应用崩溃。

关键细节：如果 OOM 发生在 OOM 构造过程中（递归场景），ART 会使用预分配的 `PreAllocatedOutOfMemoryErrorWhenThrowingOOME` 对象，避免在内存不足时再分配新对象。

[已验证: AOSP art/runtime/thread.cc, Thread::ThrowOutOfMemoryError]

## Java Heap OOM 分类与治理

堆内存 OOM 的排查，先看错误信息里的关键字段。

### 从错误信息定位

一个典型的 Java Heap OOM 错误信息如下：

```text
java.lang.OutOfMemoryError: Failed to allocate a 48 byte allocation with 3610680 free bytes
and 3526KB until OOM, target footprint 536870912, growth limit 536870912;
giving up on allocation because <1% of heap free after GC.
```

需要关注的字段：

- **growth limit**：虚拟机为应用设置的堆上限（`Runtime.getRuntime().maxMemory()`），通常 256 MB 或 512 MB，由 `ActivityManager` 在进程启动时通过 `processinfo` 配置。
- **target footprint**：当前堆的目标大小，ART 的 GC 会尽量把堆控制在这个值附近。当 target footprint 等于 growth limit 且空闲内存不够分配时，OOM 产生。
- **free bytes / until OOM**：当前空闲内存和距 OOM 的余量。单独看 free bytes 大于请求大小不能直接断定碎片化——需要结合下文的 `LogFragmentationAllocFailure` 输出判断。
- **<1% of heap free after GC**：说明 GC 后堆空闲比例极低，属于整体堆占用饱和，不是碎片化问题。
- **largest contiguous chunk < N** 或 fragmentation alloc failure 信息：这才是堆碎片化的明确信号——空闲字节数足够但连续空间不够。

### 产生路径

Java 层的 `new` 操作符进入 ART 后走到 `Heap::AllocObjectWithAllocator`（`art/runtime/gc/heap.cc`）。分配失败时，ART 发起一次强力 GC（`AllocateInternalWithGc`），如果 GC 后仍然分配不了，进入 `Heap::ThrowOutOfMemoryError`：

```cpp
// art/runtime/gc/heap.cc 简化逻辑
void Heap::ThrowOutOfMemoryError(Thread* self, size_t byte_count,
                                  AllocatorType allocator_type) {
  std::ostringstream oss;
  oss << "Failed to allocate a " << byte_count << " byte allocation with "
      << GetFreeMemory() << " free bytes and "
      << PrettySize(GetFreeMemoryUntilOOME()) << " until OOM,"
      << " target footprint " << target_footprint_.load(std::memory_order_relaxed)
      << ", growth limit " << growth_limit_;
  // 根据分配类型定位到具体 space
  if (allocator_type == kAllocatorTypeLOS) { /* LargeObjectSpace */ }
  else {
    space::AllocSpace* space = /* 根据 allocator_type 选对应 space */;
    space->LogFragmentationAllocFailure(oss, byte_count);
  }
  self->ThrowOutOfMemoryError(oss.str().c_str());
}
```

`Heap::ThrowOutOfMemoryError` 是堆 OOM 的唯一出口。它根据分配类型（ROS_ALLOC、DL_MALLOC、BUMP_POINTER、REGION_TLAB、LOS 等）定位到具体的 Space，输出碎片化信息。

### 诊断分类

`Heap::ThrowOutOfMemoryError` 的内部逻辑把 OOM 分成两类，排查时先区分：

| 诊断信号 | 含义 | 排查方向 |
|----------|------|----------|
| `largest contiguous chunk < N` / `LogFragmentationAllocFailure` | 空闲总字节数够，但连续空间不足 | 减少大对象分配频率、对象池化、避免频繁分配/释放不同大小对象 |
| `<1% of heap free after GC` | GC 后整体堆空闲比例极低 | 排查内存泄漏、降低常驻内存、评估是否需要 growth limit 扩展 |

内存泄漏的具体检测手段（Shark 解析 hprof、GC Root 引用链追踪）详见 23.1 节。Java 堆优化策略（减少对象分配、对象池、缓存策略）详见 23.4 节。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]

## Native 内存 OOM

Native 层的 OOM 发生在 `malloc`、`mmap` 等 Linux 内存分配 API 返回失败时，和 Java 堆是独立的两个限制维度。

### 常见触发路径

**JNI 分配**

`NewStringUTF` 在构造字符串时，如果长度超过 `INT_MAX`，即使内存空间充足也会抛出 OOM：

```cpp
// art/runtime/jni/jni_internal.cc 简化
if (utf16_length > std::numeric_limits<int32_t>::max()) {
  soa.Self()->ThrowOutOfMemoryError(
      StringPrintf("NewStringUTF input has 2^31 or more characters: %zu", utf16_length).c_str());
  return nullptr;
}
```

**Unsafe.allocateMemory**

`sun.misc.Unsafe` 的 `allocateMemory` 底层调用 `malloc`。`malloc` 返回 `nullptr` 时，ART 抛出 `"native alloc"` OOM：

```cpp
// art/runtime/native/sun_misc_Unsafe.cc 简化
// 函数名: Unsafe_allocateMemory()
void* mem = malloc(malloc_bytes);
if (mem == nullptr) {
  soa.Self()->ThrowOutOfMemoryError("native alloc");
  return 0;
}
```

> **边界说明**：Gson 等反序列化框架使用 `Unsafe.allocateInstance(Class)` 绕过构造函数——这条路径分配的是 Java 对象，走 Java 堆，不应归入 Native 内存 OOM。`allocateInstance` 增加的是 Java 堆压力（对象数），`allocateMemory` 增加的是 Native 堆压力（字节数），两者的 OOM 触发机制完全不同。

**Bitmap 像素存储（Android 8.0+）**

Android 8.0 起，普通 Bitmap 的像素数据通过 `calloc` 分配在 Native 堆（`frameworks/base/libs/hwui/hwui/Bitmap.cpp` 的 `allocateHeapBitmap`），不再占用 Java 堆。Hardware Bitmap（`Bitmap.Config.HARDWARE`）走 GraphicBuffer / AHardwareBuffer 路径。大量 Bitmap 创建不会触发 Java Heap OOM，但会耗尽 Native 堆或虚拟内存。Native 堆 OOM 的错误信息取决于分配路径：`calloc` 失败时返回 `nullptr`，最终触发 ART 的 `ThrowOutOfMemoryError`；极少数超大块连续内存分配由 allocator 内部走 `mmap`，失败时报告 `Failed anonymous mmap`——但不要把所有 Bitmap OOM 都归结为 `Failed anonymous mmap`。

### 排查手段

1. **`/proc/pid/status` 查看 VmSize / VmRSS**：VmSize 持续增长说明存在 Native 内存泄漏。
2. **`/proc/pid/smaps` 按内存类型统计**：关注 `[anon:dalvik-...]`、`[anon:libc_malloc]` 段的增长趋势。
3. **Perfetto Native Heap Profile**（Android 10+）：`heapprofd` 可以抓取 Native 分配调用栈，定位泄漏点；user build 上通常要求应用设置 `debuggable` 或 `profileable`。
4. **`android.os.Debug.getNativeHeapAllocatedSize()`**：在代码中周期性采样，绘制趋势图。

Native 内存管理的详细优化策略详见 23.3 节。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]

## 线程数 OOM（pthread_create 失败）

每个 Java 线程在底层对应一个 `pthread`，需要分配栈空间（默认约 1 MB）和 JNI 环境结构体。`Thread::CreateNativeThread`（`art/runtime/thread.cc`）调用 `pthread_create` 时，如果虚拟内存不够分配线程栈，或内核资源不足（`EAGAIN`），创建失败，抛出 OOM。线程数 OOM 的根因是虚拟地址空间耗尽或内核线程配额——与 FD 泄漏是两个独立的治理路径。

### 错误信息区分

`CreateNativeThread` 的错误处理区分两种失败原因：

```cpp
// art/runtime/thread.cc 简化
std::string msg(child_jni_env_ext.get() == nullptr ?
    StringPrintf("Could not allocate JNI Env: %s", error_msg.c_str()) :
    StringPrintf("pthread_create (%s stack) failed: %s",
                 PrettySize(stack_size).c_str(), strerror(pthread_create_result)));
soa.Self()->ThrowOutOfMemoryError(msg.c_str());
```

- **"Could not allocate JNI Env"**：`JNIEnvExt::Create` 阶段失败，通常是 `mmap` 分配 JNI 环境所需的内存页失败。说明进程虚拟内存已耗尽。
- **"pthread_create (XXX stack) failed"**：`pthread_create` 返回非零错误码，常见 `EAGAIN`（资源不足）。需要看 `strerror` 的具体内容。

### 治理策略

**线程治理**（预防）

1. 全局线程池统一管理异步任务，禁止直接 `new Thread`。使用 `Executors.newFixedThreadPool` 或 Kotlin 协程的 `Dispatchers.Default` / `Dispatchers.IO`。
2. 三方库的线程创建需要监控。通过统一 `ThreadFactory` 或协程 dispatcher 封装记录创建堆栈；必要时 hook `Thread.start()`、`pthread_create()` 或三方库线程工厂，在阈值触发时同时上报当前线程堆栈与创建堆栈。
3. 设定进程线程数上限阈值（线上通常设 400-500），超过阈值触发告警。

**线程监控**（发现）

定期读取 `/proc/pid/status` 的 Threads 字段：

```text
Threads:	387
```

或者遍历 `/proc/pid/task/` 目录统计线程数。线上监控中，当线程数超过基线 50% 时记录当前所有线程的堆栈（`Thread.getAllStackTraces()`），上报分析。

**线程回溯兜底**（防护）

针对子线程的 Native Crash，`sigsetjmp` / `siglongjmp` 只能作为强约束下的线程级隔离实验：信号处理函数只能执行 async-signal-safe 的最小跳转逻辑，跳回后也不能假定锁、堆、JNI 和业务状态仍然一致。具体实现通过 PLT Hook 拦截 `pthread_create`，替换执行函数实现；命中后应记录最小状态并尽快结束进程，详见扩展小节"OOM 兜底与安全降级"。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - pthread_create 回溯：原来 Native 也有 try catch！.md]
[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]

## FD 泄漏导致的资源型崩溃

Linux 进程的 FD（文件描述符）是有限资源。单个进程的 FD 上限由 `ulimit -n` 决定，Android 上通常为 1024 或更高（取决于厂商配置）。FD 耗尽后，无法打开新文件、创建新 socket，也让后续需要 epoll、pipe 或 socket 的初始化步骤失败——每个 Looper 线程初始化时都会创建 epoll FD 和 eventfd（`system/core/libutils/Looper.cpp`）。这类问题通常表现为 FD 创建失败、Looper/InputChannel 初始化失败或 FORTIFY abort，不等价于 ART 投递的 `OutOfMemoryError`；放在 OOM 治理章，是因为线上内存告警常把 FD、线程、虚拟地址空间一起作为进程资源水位管理。

### 典型崩溃堆栈

```text
signal:6 (SIGABRT), code:-6 (SI_TKILL)
FORTIFY: FD_SET: file descriptor >= FD_SETSIZE
```

这个崩溃不是"FD 超限"的直接原因，而是 FD 编号超过 `FD_SETSIZE`（通常 1024）后，`FD_SET` 宏触发的 fortify 检查。出现这个崩溃时，FD 泄漏已经持续了很长时间——崩溃点只是资源耗尽后暴露出来的表层位置。

### 常见 FD 消耗者

| 类型 | 示例 | 说明 |
|------|------|------|
| 文件 | `open()` / `FileInputStream` | 日志库 mmap、数据库 WAL 文件 |
| Socket | 网络请求、网络长连接 | HTTP、WebSocket 长连接 |
| Pipe | `pipe()` / `eventfd` | Looper 的 `mWakeEventFd`、线程间通信 |
| epoll | `epoll_create()` | 每个 Looper 线程创建一个 epoll 实例 |
| anon_inode | `memfd_create()` | 共享内存、Ashmem |

### 排查与监控

**第一步：读取 `/proc/pid/fd` 目录**

```kotlin
val fdFile = File("/proc/${Process.myPid()}/fd/")
val files = fdFile.listFiles()
// files.size 即为当前 FD 总数
```

对每个 FD 调用 `Os.readlink()` 获取指向路径：

```text
socket:[12345]    → 网络连接
pipe:[789]        → 管道
anon_inode:[...]  → Looper / InputChannel
/data/app/...     → 打开的文件
```

统计各类型 FD 的数量，找到增长最快的类别。

**第二步：Native Hook 监控 FD 创建**

当 FD 数量监控无法定位到具体泄漏点时，通过 PLT Hook 拦截 `open`、`socket`、`pipe`、`dup`、`epoll_create` 等 FD 创建函数：

```cpp
// 使用 bhook 拦截 open 函数
typedef int(*open_type)(char*, int, int);
int proxy_open(char* path, int flags, int mode) {
  int fd = BYTEHOOK_CALL_PREV(proxy_open, open_type, path, flags, mode);
  // 记录 fd → backtrace 到 FD_MAP
  BYTEHOOK_POP_STACK();
  return fd;
}
```

在 `close` 时从 `FD_MAP` 中移除对应记录。定期检查 `FD_MAP` 中存活时间过长的 FD，取其创建堆栈上报。

`FD_MAP` 的实现采用分桶锁（类似 `ConcurrentHashMap`），避免多线程环境下锁竞争影响业务性能。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md]

## 虚拟内存空间耗尽（32 位进程）

32 位进程的用户空间虚拟地址上限约 3 GB（`0x00000000` - `0xBFFFFFFF`，内核占用高 1 GB）。虽然 64 位设备已普及，但部分应用（含 32 位 so 库）或特定场景下仍以 32 位模式运行。

### 虚拟内存的主要消费者

一个 Android 进程的虚拟内存布局（可通过 `/proc/pid/maps` 查看）：

| 区域 | 典型大小 | 说明 |
|------|----------|------|
| Java 堆 | 256-512 MB | ART 的 Region Space / Bump Pointer Space |
| Native 堆 | 几十到数百 MB | `malloc` 分配，受 `mallopt` 参数影响 |
| mmap 区域 | 数十到数百 MB | so 库映射、Bitmap 像素、日志 mmap |
| 线程栈 | N × ~1 MB | 每个线程约 1 MB 栈空间 |
| GPU / Gralloc | 几十 MB | Surface / BufferQueue 的图形缓冲区 |

3 GB 的空间里，Java 堆占用一半以上后，留给线程栈、Native 分配、mmap 映射的空间就很紧张。

### 排查方法

1. **`/proc/pid/maps` 全量分析**：关注 `[anon]` 段的数量和大小，统计各 so 库的映射大小。
2. **`/proc/pid/status` 的 VmSize / VmPeak**：观察虚拟内存总量是否接近 3 GB。
3. **`Debug.getMemoryInfo()` 的 `getTotalPrivateDirty()`**：作为内存趋势的辅助指标。

### 治理方向

- 迁移到 64 位：从地址空间上解决 32 位进程的虚拟地址上限。
- 减少线程数：线程栈是虚拟内存的大头消费者。合并线程池、使用协程替代线程。
- 减少 so 库数量：每个 so 的代码段 + 数据段都要占用虚拟地址空间。动态合并或按需加载。
- 拆分进程：将功能模块拆到独立进程，分摊虚拟地址空间压力。
- `mallopt(M_PURGE, 0)` 归还空闲 arena 的物理页：它降低的是 Native RSS / 物理内存压力，不能释放已保留的虚拟地址区间，对 32 位虚拟地址空间耗尽的直接帮助有限。放在 §23.3 Native 内存优化中一起看更合适。

虚拟内存优化详见 23.6 节（大型 App 的多进程内存策略）。

## 扩展

### OOM 兜底与安全降级

线上环境无法完全避免 OOM，但可以做两层兜底。

**Java 层：`UncaughtExceptionHandler` 捕获 OOM**

OOM 是 `Error` 不是 `Exception`，默认的 `UncaughtExceptionHandler` 会终止进程。注册自定义 Handler 后，可以拦截 OOM 并做降级处理：

```kotlin
Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
  if (throwable is OutOfMemoryError) {
    // 预分配 MemoryInfo，避免 OOM 路径再分配
    val memInfo = Debug.MemoryInfo()
    Debug.getMemoryInfo(memInfo)
    val runtime = Runtime.getRuntime()
    logOOMState(runtime.totalMemory(), runtime.freeMemory(),
                runtime.maxMemory(), memInfo.totalPrivateDirty)
    safeExit()
  } else {
    defaultHandler.uncaughtException(thread, throwable)
  }
}
```

注意：OOM 场景下创建新对象可能再次触发 OOM。降级逻辑中避免分配大对象，使用预分配的字符串和日志缓冲区。

**Native 层：`sigsetjmp` / `siglongjmp` 线程级隔离**

对子线程的 Native Crash（包括 SIGSEGV、SIGABRT），可以通过 PLT Hook 拦截 `pthread_create`，在执行函数入口调用 `sigsetjmp` 设置安全点。信号处理函数收到 crash 信号时，只能执行 async-signal-safe 的最小逻辑并调用 `siglongjmp` 跳回安全点：

```cpp
static void* pthread_wrapper(void* arg) {
  ThreadArgs* args = (ThreadArgs*)arg;
  if (sigsetjmp(args->env, 1)) {
    // 从 crash 中恢复：通知上层线程异常退出
    notifyThreadCrash(args->thread_id);
    return nullptr;
  }
  // 执行原始线程函数
  args->original_func(args->original_arg);
  return nullptr;
}
```

适用场景只限后台线程的非关键 crash（如日志写入、数据上报）。跳回后进程可能已经持有不一致的锁、堆或 JNI 状态，只能做最小上报和安全退出；主线程 crash 不建议拦截，用户可见操作中断后继续运行，状态难以保证一致性。

### 大型 App 的内存预算管理

模块化程度高的大型 App，各业务线独立开发，容易各自膨胀内存。内存预算管理是约束手段。

**建立内存基线**

在不同设备档次（低/中/高端）上测量冷启动后 5 秒的 Java 堆、Native 堆、线程数、FD 数，建立各模块的内存消耗基线。测量工具推荐：

- Java 堆：`Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()`
- Native 堆：`Debug.getNativeHeapAllocatedSize()`
- 线程数：`/proc/pid/status` 的 `Threads` 行
- FD 数：`/proc/pid/fd` 目录 size

**设定模块级预算**

根据基线数据，为各业务模块设定内存预算（如启动阶段 ≤ 80 MB，首页稳定态 ≤ 150 MB）。CI 流水线中集成内存检测：模块合入前对比基线，增量超过阈值（如 +5 MB）则阻断合入。

**`onTrimMemory` 分级响应**

`ComponentCallbacks2.onTrimMemory(level)` 是系统通知应用释放内存的回调，不同 level 对应不同的释放策略：

| Level | 含义 | 建议动作 |
|-------|------|----------|
| `TRIM_MEMORY_UI_HIDDEN` | UI 不可见 | 释放 UI 相关缓存（图片、布局缓存） |
| `TRIM_MEMORY_RUNNING_LOW` | 内存开始紧张 | 释放非关键缓存 |
| `TRIM_MEMORY_MODERATE` | 后台应用，内存中等压力 | 释放可重建的数据 |
| `TRIM_MEMORY_COMPLETE` | 后台应用，内存极度紧张 | 释放所有可释放的资源 |

关键点：`onTrimMemory` 在主线程回调，释放操作必须快速。耗时操作（如写磁盘、序列化）放到子线程异步执行。

## 参考资料

### OOM 治理 — ART 堆内存分区与黑科技扩量
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-15-oom-art-heap-analysis.md
- 类型：DeepResearch 调研结果
- 摘要：ART 多层堆架构（Linear Alloc / Zygote / Active 堆分区）的内存管理机制。黑科技扩量在 OOM 风险时动态扩展堆内存，延长应用存活 2-3 秒为后台任务和内存清理提供缓冲，涉及 GC、内存监控和动态扩展三个模块。
- 注入时间：2026-05-17
- 价值：补充 ART 堆分区与 OOM 区域映射关系，以及 OOM 时堆增量技术的实现机制
