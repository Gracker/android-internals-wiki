---

title: "OOM 治理"
chapter: "20.5"
section: "20.5"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-12"
last_verified_against: "AOSP android-17.0.0_r1: ART heap/thread/JNI/jdk_internal_misc_Unsafe, hwui Bitmap, libutils Looper, ComponentCallbacks2, AndroidRuntime heap properties, ActivityThread largeHeap handling"
confidence: medium
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap-inl.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/jdk_internal_misc_Unsafe.cc"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 初识内存：内存是什么？.md"
  - type: blog
    path: "Clippings/Android 应用稳定性剖析与优化 - 实现 FD 监控：文件描述符（FD）超限怎么办？.md"
tags: [oom, memory, thread-limit, fd-leak, virtual-memory]
related_chapters: ["20.1", "23.1", "23.3", "23.4", "23.6", "4.3", "4.4"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: fixed
---


# OOM 治理

`OutOfMemoryError` 只是 Android 进程资源失败的一种表现。Java heap 达到 ART growth limit、native-backed API 分配失败、线程创建失败，都可能投递 OOME；普通 `malloc()` / `mmap()` 失败也可能只返回错误，FD 耗尽通常表现为 `EMFILE` 或 abort，LMKD 结束进程时则没有 Java 异常。

治理工作的入口是保留原始错误、退出原因和进程资源快照，再按分配域选择证据。平台锚点是 Android 17 / API 37 / `android-17.0.0_r1`；涉及 Linux 资源限制的说明以 `android17-6.18-2026-06_r6` 为 kernel 锚点。

## OOM 的投递机制

同一个“内存不足”告警可能来自完全不同的系统层。先把事件放入正确类别：

| 事件 | 常见表现 | 主要证据 | 是否经过 Java `OutOfMemoryError` |
|---|---|---|---|
| ART Java heap 分配失败 | `Failed to allocate ... growth limit ...` | OOME 错误文本、Java 栈、heap dump、GC/heap 指标 | 是 |
| native-backed Java API 分配失败 | `native alloc`、Bitmap OOM、特定 JNI 错误 | Java 栈、native allocation 栈、PSS/RSS | 由 API 决定 |
| platform thread 创建失败 | `Could not allocate JNI Env` 或 `pthread_create (...) failed` | OOME 错误文本、线程数、线程栈、VmSize、进程限制 | ART 会投递 OOME |
| 普通 native 分配失败 | `malloc/calloc/mmap` 返回空指针或 `ENOMEM`，也可能被调用方转换为异常或 abort | native 栈、heapprofd、maps/smaps、errno | 不一定 |
| 低内存结束进程 | 进程被系统终止，重启后看到 `ApplicationExitInfo.REASON_LOW_MEMORY` | `ApplicationExitInfo`、LMKD/系统日志、内存压力 | 否 |
| FD 耗尽 | `EMFILE`、创建 socket/pipe/Looper 失败、FORTIFY abort | `/proc/self/fd`、rlimit、FD 创建与关闭记录 | 通常否 |
| 虚拟地址空间或 VMA 耗尽 | `mmap` 返回 `ENOMEM`，后续表现取决于调用方 | `/proc/self/maps`、VmSize、映射数、失败栈 | 不一定 |

这张表决定采集工具。Java heap dump 看不到所有 native 映射；heapprofd 也看不到 Java 对象引用；崩溃捕获 SDK 无法在 LMKD 终止进程后执行收尾代码。

### ART 如何投递 OOME

ART 的多条 native 失败路径会调用 `Thread::ThrowOutOfMemoryError()`。Android 17 的实现先尝试构造带错误文本的 `java.lang.OutOfMemoryError`；若构造 OOME 时再次发生 OOM，线程改用 Runtime 启动阶段准备的 OOME 对象。

下面是 `art/runtime/thread.cc` 的关键分支，省略了日志和无关代码。

```cpp
void Thread::ThrowOutOfMemoryError(const char* msg) {
  if (!tls32_.throwing_OutOfMemoryError) {
    tls32_.throwing_OutOfMemoryError = true;
    ThrowNewException("Ljava/lang/OutOfMemoryError;", msg);
    tls32_.throwing_OutOfMemoryError = false;
  } else {
    Dump(LOG_STREAM(WARNING));
    SetException(
        Runtime::Current()->GetPreAllocatedOutOfMemoryErrorWhenThrowingOOME());
  }
}
```

预分配对象保证异常状态可以被设置，却不保证完整错误文本和 Java 栈；递归分支还会主动 dump 当前线程帮助诊断。`Heap::ThrowOutOfMemoryError()` 另有 native stack overflow 分支，使用 `GetPreAllocatedOutOfMemoryErrorWhenHandlingStackOverflow()`。

OOME 成为 ART 的待处理异常后，控制流回到托管代码。没有被业务捕获时，它沿 `Thread.UncaughtExceptionHandler` 处理并结束对应进程。自定义处理器必须继续调用原处理器；API 37 的 `ProfilingTrigger.TRIGGER_TYPE_OOM` 也把这条调用路径作为自动生成 Java heap dump 的前提之一。

OOME 错误文本用于诊断，格式会随分配器和平台版本变化。监控平台可以提取 allocation size、growth limit 等已知字段做辅助分组，原始文本和栈必须保留，不能把正则结果当成长期接口。

## Java Heap OOM 分类与治理

Java heap OOM 要回答三个问题：请求多大、GC 后还活着多少对象、growth limit 之前还剩多少可用空间。只看“当前 free bytes”很容易误判。

### 从错误信息定位

典型 Android 17 heap OOME 可能包含以下信息：

```text
java.lang.OutOfMemoryError: Failed to allocate a 48 byte allocation with
3610680 free bytes and 3526KB until OOM, target footprint 536870912,
growth limit 536870912; giving up on allocation because <1% of heap free after GC.
```

字段应按 ART 语义解释：

- **allocation size**：本次请求大小。请求很小仍失败，通常说明堆已接近限制；一次超大请求则要检查输入尺寸和乘法溢出。
- **free bytes**：ART 统计的 heap 空闲总量。它大于请求值也不能单独证明分配可成功，目标 space 的连续块和最小剩余比例仍会参与判断。
- **until OOM**：`GetFreeMemoryUntilOOME()` 给出的剩余增长空间，受当前 footprint 和 growth limit 约束。
- **target footprint**：GC 用来调节 heap 增长的目标，不等同于硬上限。
- **growth limit**：应用 Java heap 的增长限制。设备通过 `dalvik.vm.heapgrowthlimit`、`dalvik.vm.heapsize` 等属性配置 Runtime；`android:largeHeap="true"` 会让 `ActivityThread` 调用 `VMRuntime.clearGrowthLimit()`，普通应用走 `clampGrowthLimit()`。
- **fragmentation 文本**：当空闲总量不小于请求且目标 allocator 支持碎片诊断时，`LogFragmentationAllocFailure()` 会报告最大连续块。Large Object Space 分支没有这段碎片详情。
- **`<1% of heap free after GC`**：分配后无法保留 ART 要求的最小空闲比例。它描述的是 heap 水位策略，不能仅凭这句话断定存在引用泄漏。

### ART 分配失败路径

`Heap::AllocateInternalWithGc()` 会尝试分配、执行适用的 GC，并在满足条件时重试。仍无法得到对象后才调用 `Heap::ThrowOutOfMemoryError()`。

下面的节选展示 Android 17 生成错误文本和选择碎片诊断的条件。

```cpp
void Heap::ThrowOutOfMemoryError(
    Thread* self,
    size_t byte_count,
    AllocatorType allocator_type) {
  size_t total_bytes_free = GetFreeMemory();
  oss << "Failed to allocate a " << byte_count
      << " byte allocation with " << total_bytes_free
      << " free bytes and " << PrettySize(GetFreeMemoryUntilOOME())
      << " until OOM, target footprint "
      << target_footprint_.load(std::memory_order_relaxed)
      << ", growth limit " << growth_limit_;

  if (total_bytes_free >= byte_count &&
      allocator_type != kAllocatorTypeLOS) {
    // 省略按 allocator_type 选择 AllocSpace 的代码。
    if (!space->LogFragmentationAllocFailure(oss, byte_count)) {
      oss << "; giving up on allocation because <"
          << kMinFreeHeapAfterGcForAlloc * 100
          << "% of heap free after GC.";
    }
  }
  self->ThrowOutOfMemoryError(oss.str().c_str());
}
```

这段代码说明两点：碎片诊断只在“空闲总量足够”且不是 LOS 时尝试；错误文本描述的是失败时状态，不能替代 heap dump 的引用关系。

### 四类 Java heap 问题

| 类型 | 证据特征 | 治理方向 |
|---|---|---|
| 引用泄漏 | 同一类对象和 GC Root 路径跨场景持续增长 | 修复生命周期、监听器、线程本地变量、静态集合或错误缓存所有权 |
| 设计性常驻过大 | 对象都有合法持有者，但稳定态存活集已接近预算 | 缩小模型、分页、按需加载、限制缓存和减少多份表示 |
| 分配抖动 | 存活集不高，短时间分配速率与 GC 频率很高 | 复用缓冲区、减少中间对象、流式解析、避免热路径装箱 |
| 单次大对象或尺寸错误 | OOME 栈集中在数组、Bitmap、解压或反序列化入口 | 校验输入上限、分块处理、目标尺寸解码、检查宽高与字节数乘法 |

heap dump 更适合在接近风险水位但进程仍健康时采集。发生 OOME 后再完整 dump 需要额外内存和 I/O，成功率低，还可能延长用户可见停顿。线上可用趋势采样找到水位上升场景，再在可控设备、灰度或实验室复现并抓取 HPROF。

`Runtime.totalMemory() - Runtime.freeMemory()` 表示当前已提交 heap 中尚未空闲的部分，不等于 GC 后存活集。判断泄漏要比较同一场景、同一 GC 状态下的对象数量和 retained size，不能用一次 Runtime 采样下结论。

### `largeHeap` 的边界

`largeHeap` 只改变应用可使用的 Java heap 上限，不会增加设备物理内存，也不会降低 native、图形缓冲、线程栈和其他进程的压力。更大的 heap 还会容纳更多存活对象，让系统更早承受内存竞争。

可以为少数确有大内存工作集的产品评估 `largeHeap`，前提是低内存设备、后台切换、进程重建和系统压力测试都有数据。泄漏、无界缓存和错误尺寸分配不能靠它处理。修改 ART 私有字段、反射调用隐藏接口或动态“扩堆”的做法依赖内部实现，也可能破坏 GC 假设，不应进入生产方案。

## Native 内存 OOM

native 分配没有统一的“native heap 上限”。`malloc()` 可能因地址空间、提交、allocator 元数据或系统策略失败；mmap、图形缓冲和线程栈又分别经过不同分配路径。进程也可能在分配函数返回失败前被 LMKD 结束。

### 哪些路径会转换为 OOME

Android 17 中有明确的转换点：

- `jdk_internal_misc_Unsafe.cc` 的 `Unsafe_allocateMemory()` 调用 `malloc()`；空指针时通过 `Thread::ThrowOutOfMemoryError("native alloc")` 投递 OOME。
- `libs/hwui/hwui/Bitmap.cpp` 的 `allocateHeapBitmap()` 使用 `calloc()` 分配普通 Bitmap 像素；返回空指针后，`libs/hwui/jni/Bitmap.cpp` 的 JNI 入口调用 `doThrowOOME()`。
- JNI 的某些 API 会在输入无法表示或分配失败时投递 OOME，例如超长 `NewStringUTF`。具体结果由 JNI 入口实现决定。
- 应用或第三方 native 库直接调用 `malloc/calloc/realloc/mmap` 时，失败结果属于调用方契约。忽略空指针可能转成 SIGSEGV，主动 `abort()` 会成为 SIGABRT，只有显式调用 JNI/ART 异常接口才会变成 Java OOME。

普通 Bitmap 自 Android 8.0 起由 native heap 持有像素；`Bitmap.Config.HARDWARE` 使用 GraphicBuffer / AHardwareBuffer。两者都能增加进程或系统内存压力，但采集方式和归属不同，Java heap dump 中的 Bitmap wrapper 大小不能代表全部像素或图形缓冲成本。

### 先区分虚拟地址、驻留页和比例分摊

| 指标 | 回答的问题 | 不能回答的问题 |
|---|---|---|
| VmSize / `/proc/self/maps` | 进程保留和映射了多少虚拟地址区间 | 这些页是否常驻、是否独占 |
| VmRSS / `smaps_rollup` RSS | 当前有多少页驻留内存 | 共享页应由哪个进程负责 |
| PSS | 共享页按映射进程数分摊后的进程成本 | 单个 native allocation 的调用栈 |
| `Debug.getNativeHeapAllocatedSize()` | bionic malloc 管理的已分配字节趋势 | mmap、线程栈、GraphicBuffer 等全部 native 成本 |
| heapprofd | 被采样的 malloc/free 调用栈、大小和存活情况 | 未经过受支持 allocator 的所有映射与图形内存 |

因此，“native heap 指标没涨”不能排除 mmap、线程栈或图形缓冲增长；“VmSize 很大”也不能直接认定物理内存泄漏。

### 诊断顺序

1. 用 `ApplicationExitInfo` 区分 OOME crash、native crash 和 `REASON_LOW_MEMORY`。先调用 `ActivityManager.isLowMemoryKillReportSupported()` 判断设备是否支持低内存退出归因；不支持时，缺少 `REASON_LOW_MEMORY` 不能排除系统内存压力。低内存终止进程没有可依赖的 uncaught 回调。
2. 对比同场景的 PSS/RSS、Java heap、native malloc、图形内存、线程和映射数，先确定增长域。
3. malloc 域使用 heapprofd 或 Android Studio native allocation profiler，保留分配与释放栈；接入条件受构建类型、`profileable` 配置、设备和系统策略影响。
4. mmap 域解析 `/proc/self/maps` / `smaps`，按文件路径、匿名映射名称和权限聚合。
5. 图形与媒体对象结合 Perfetto、`dumpsys meminfo`、dma-buf/GraphicBuffer 工具和对象生命周期检查。
6. 对 JNI 资源建立明确的所有权与释放协议：`close()`、RAII、引用计数和失败路径都要覆盖，不能只等待 Java GC 调用 `Cleaner`。

采样本身会增加内存与 CPU，线上应限制时长、采样率和目标进程。接近风险水位时优先保存轻量计数与场景，详细分析放到灰度或可复现设备。

## 线程数 OOM（pthread_create 失败）

已启动的传统 Java platform thread 需要 native thread、栈与 guard 区、ART `Thread`、JNI 环境和内核 task 资源。线程数增加会同时消耗虚拟地址空间、native 内存和调度能力；协程或任务数量不能直接换算为 OS 线程数。

### Android 17 的失败分支

`Thread::CreateNativeThread()` 先创建 ART `Thread` 和 `JNIEnvExt`，设置 pthread 栈大小，再调用 `pthread_create()`。下面是失败后错误文本的关键代码。

```cpp
std::string msg(
    child_jni_env_ext.get() == nullptr
        ? StringPrintf("Could not allocate JNI Env: %s",
                       error_msg.c_str())
        : StringPrintf("pthread_create (%s stack) failed: %s",
                       PrettySize(stack_size).c_str(),
                       strerror(pthread_create_result)));
soa.Self()->ThrowOutOfMemoryError(msg.c_str());
```

`Could not allocate JNI Env` 说明失败发生在 pthread 启动前；`pthread_create ... failed` 要继续看 strerror。Android 17 的 Bionic 在 stack/TLS 映射失败时返回 `EAGAIN`，kernel clone 也可能因 task 数、`RLIMIT_NPROC` 或资源不足返回错误。`android17-6.18-2026-06_r6/kernel/fork.c` 的 `copy_process()` 会在相关限制失败时返回 `-EAGAIN`，诊断时必须保留设备上的原始 errno 文本。

栈大小由 ART 的 `FixStackSize()` 和线程请求共同决定，不存在适用于所有设备与架构的“每线程固定 1 MB”。诊断应从 OOME 错误文本里的栈大小、`/proc/self/task` 数量和 maps 中的 stack/guard 映射出发。

### 线程治理与监控

- 对自有任务使用有界 executor、结构化协程和统一调度入口，记录池大小、active、queue depth、拒绝和取消。
- 审计 SDK、WebView、媒体、数据库和网络库的线程池。多个库各自“合理”的池相加后仍可能过量。
- `Dispatchers.IO` 适合阻塞 I/O，但它不是全应用线程总额控制器；多个 `limitedParallelism` 视图也需要产品级并发预算。
- 在线程创建点记录责任模块、名称和创建场景。优先使用自有 `ThreadFactory` / executor 观察，native hook 只用于受控诊断，需处理递归、性能和兼容性。
- 周期读取 `/proc/self/status` 的 `Threads`，并统计 `/proc/self/task`。两者是采样值，线程快速创建与退出时可能不同。
- 告警阈值来自设备和场景基线，例如稳定态分布、增长速度和剩余地址空间。固定 400 或 500 对不同进程没有通用意义。
- 高水位时不要立即调用 `Thread.getAllStackTraces()` 抓取所有栈；它会创建大量对象。平时保留线程名、责任模块和采样栈，高水位只补充有限线程证据。

线程数下降也要看任务是否仍能完成。把线程改成一个无界队列，可能把资源 OOM 改成排队延迟或 ANR。

## FD 泄漏导致的资源型崩溃

FD 是独立的内核资源。进程达到 `RLIMIT_NOFILE` 后，`open()`、`socket()`、`pipe()`、`eventfd()` 或 `epoll_create1()` 可能返回 `EMFILE`；系统级 file table 压力还可能表现为 `ENFILE`。`android17-6.18-2026-06_r6/fs/file.c` 的 FD 分配路径会按当前 files table 与 limit 返回 `-EMFILE`。

FD 耗尽通常不经过 ART OOME。仍应将内存、线程、FD 和地址空间放进同一套进程资源看板，同时保持事件类型分开。

### FORTIFY 与真实上限

下面的日志表示代码把过大的 fd 交给基于 `fd_set` 的 `select()` 接口：

```text
FORTIFY: FD_SET: file descriptor >= FD_SETSIZE
```

`FD_SETSIZE` 是 `select()` 数据结构的表示上限，和 `RLIMIT_NOFILE` 不是同一个值。只要进程拿到的 fd 编号超过 `FD_SETSIZE`，FORTIFY 就可能 abort；此时仍可能没有达到进程 fd limit。修复既要找 fd 增长源，也要检查库是否错误地用 `select()` 处理高编号 fd。

### 采集一份可解释的 FD 快照

一份有效快照至少包含：

- `getrlimit(RLIMIT_NOFILE)` 的软限制、硬限制和当前 FD 数。
- `/proc/self/fd/<n>` 的 readlink 结果，按 socket、pipe、anon_inode、文件、设备和未知类型归组。
- 持续增长类别的创建方、创建栈、创建时间和可用的业务 ID。
- close 结果、重复 close、dup 关系和对象生命周期。
- 快照时的线程数、网络连接、页面或任务场景。

遍历 `/proc/self/fd` 本身会短暂打开目录 FD，其他线程也可能同时 close/dup，因此结果是近似快照。readlink 失败要按竞态处理，不能把它记成泄漏。

常见泄漏点包括未关闭的 `ParcelFileDescriptor`、`Cursor`、`AssetFileDescriptor`、`InputStream`、socket、`Image`、`MediaExtractor` 和重复注册的 pipe/eventfd。Kotlin `use {}`、Java try-with-resources 和 C++ RAII 应覆盖成功、异常、取消与超时路径。

### 何时使用 native 插桩

只统计数量无法定位创建方时，可以在受控版本观察 `open/openat`、`socket/accept`、`pipe/pipe2`、`dup*`、`eventfd`、`epoll_create*` 与 `close`。实现要处理可变参数、符号别名、递归调用、采样和 fd 复用；漏掉 `dup` 或 `accept` 会让账目失真。

不要直接把全量调用栈和全局映射表放进每次 open/close。更稳妥的方式是先找增长类别，再对目标模块采样；fd 接近高水位时输出已有轻量记录，避免监控组件自己申请更多 FD 或大块内存。

## 虚拟内存空间耗尽（32 位进程）

32 位进程的地址空间窄，so、Java heap、native heap、线程栈和 mmap 更容易互相挤压。Android 17 主线设备与应用以 64 位为主要形态，但兼容 32 位 ABI 的设备仍可能运行 32 位进程；用 `Process.is64Bit()` 记录当前进程架构，不要只看设备 CPU。

“32 位用户空间固定为 3 GB、内核固定占 1 GB”不能作为跨设备结论。内核配置、架构、ASLR、保留区和进程映射共同决定可用范围，可分配的最大连续区间还会小于剩余总地址空间。

### 地址空间由哪些映射构成

| 区域 | 观察方式 | 边界 |
|---|---|---|
| ART heap spaces | maps/smaps 中的 dalvik/ART 匿名区 | Java heap footprint 与 growth limit 相关，但保留量和已提交量要区分 |
| native allocator arenas | libc malloc 匿名映射 | `Debug.getNativeHeapAllocatedSize()` 只覆盖 allocator 统计，不等于全部映射 |
| so、dex、oat、vdex | 带文件路径的映射 | 同一文件可有多个权限区段，共享页不能按 VmSize 当作独占物理成本 |
| 线程栈与 guard | stack/匿名映射、线程创建记录 | 大量线程会消耗地址区间，即使栈页尚未全部驻留 |
| Bitmap、媒体和共享内存 | 匿名、memfd、dma-buf 或设备映射 | 是否计入进程 RSS/PSS 取决于映射与统计方式 |
| 保留地址区间 | `PROT_NONE` 或 allocator/Runtime 保留区 | VmSize 会增长，但页可能尚未常驻 |

64 位进程也可能因无界映射、VMA 数量、异常地址保留或超大连续映射而收到 `ENOMEM`。`android17-6.18-2026-06_r6/mm/mmap.c` 的 `do_mmap()` 会在长度、地址或 `map_count` 超过系统约束等条件下返回 `-ENOMEM`；“64 位地址多”不能替代映射生命周期管理。

### 排查顺序

1. 保存进程位数、失败 errno、请求长度、调用栈和连续性要求。
2. 读取 `/proc/self/status` 的 VmSize/VmPeak 和 `/proc/self/maps` 区间数量，和同设备同场景健康样本比较。
3. 按映射名称、权限和责任模块聚合 maps/smaps，区分持续增长与单次巨型请求。
4. 同时检查线程、Java growth limit、native allocator、文件映射和图形/媒体资源，避免只盯一个总量。
5. 对 32 位进程检查最大空洞和碎片；总剩余地址空间足够，不代表存在满足本次请求的连续区间。
6. 对 64 位异常 VmSize 先识别 Runtime 保留区。较大的保留区可以是正常实现，证据要回到失败栈和映射增长。

`Debug.MemoryInfo.getTotalPrivateDirty()` 是物理脏页指标，不能判断虚拟地址空间是否接近限制。

### 治理方向

- 能迁移时提供完整 64 位 ABI，并验证指针变大带来的 native heap 增量和第三方 `.so` 兼容。
- 限制线程、映射和内存映射文件的数量与生命周期，及时 `munmap()` 或关闭资源所有者。
- 大对象采用分块、流式或尺寸上限，避免要求巨型连续区域。
- `mallopt(M_PURGE, 0)` 可清理 allocator 空闲物理页，不能自动释放所有保留地址区间，也不能修复映射泄漏。
- 拆进程会获得独立地址空间，却会复制 Runtime、so、线程和缓存，增加整机内存与 IPC 成本。只有隔离边界和测量数据同时成立时才采用。

## 扩展

### OOM 兜底与安全降级

OOME 发生后，当前线程连创建异常对象都可能失败。可靠方案把观测和降级放在资源接近预算时完成，uncaught 阶段只保留最小记录并沿默认处理路径结束进程。

### 在 OOM 前释放可重建资源

降级动作按风险排序：

1. 对图片、页面模型、预取、媒体缓冲和离线队列设置硬上限与逐出策略，不能等待系统回调才控制。
2. 当页面退出、UI 隐藏或任务取消时释放资源所有者；`close()` 和协程取消路径都要测试。
3. 内存水位持续上升时停止非必要预取、降低目标图片尺寸、缩小并发，并保留用户当前操作所需数据。
4. 后台阶段释放可快速重建的 UI 缓存，避免同步序列化或磁盘写入阻塞主线程。
5. 重任务支持检查点或幂等重试，让进程被系统结束后能够恢复，不依赖 OOM 处理器抢救。

API 34 及以上不再向应用发送旧的 `TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE` 和 `TRIM_MEMORY_COMPLETE`。面向 Android 17 的代码聚焦 `TRIM_MEMORY_UI_HIDDEN` 与 `TRIM_MEMORY_BACKGROUND`；需要兼容旧系统时，再为旧常量保留分支。

下面的示例让项目自定义缓存根据仍会送达的两个级别缩容；回调运行在主线程，`trimTo()` 只能释放引用和完成有界操作。

```kotlin
override fun onTrimMemory(level: Int) {
    when {
        level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND -> {
            memoryCaches.trimTo(CacheProfile.BACKGROUND)
        }
        level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN -> {
            memoryCaches.trimTo(CacheProfile.UI_HIDDEN)
        }
    }
}
```

释放引用后由 Runtime 决定 GC 时机，不要在生产路径主动调用 `System.gc()`。需要关闭文件或 native 资源时，关闭动作必须快速；耗时清理由后台任务处理，但不能继续持有本应释放的大对象。

### `UncaughtExceptionHandler` 与 API 37 OOM 触发器

全局 `UncaughtExceptionHandler` 不适合执行 `Debug.getMemoryInfo()`、heap dump、JSON 序列化或网络上报，这些动作会继续申请内存。若产品需要 OOM 标记，应预先准备固定大小记录和有界写入路径，失败时立即放弃。

自定义处理器必须保存安装前的处理器，并对所有 `Throwable` 调用它。API 37 的 `ProfilingTrigger.TRIGGER_TYPE_OOM` 可以在 OOM 时提供 Java heap dump；官方明确要求自定义处理器调用默认处理器。触发器仍受系统资源和速率限制，不能保证每次产生结果。

在可控的可选分配边界捕获 OOME，只适用于输入尺寸已知、没有共享状态写到一半、可以返回低分辨率或失败结果的操作。全局吞掉 OOME 后继续运行，进程可能仍处于高水位，其他线程也可能已失败。

`sigsetjmp` / `siglongjmp` 处理 SIGSEGV、SIGABRT 属于 native crash 隔离实验，不能处理 Java heap OOME，也不能修复 native allocator 失败。跳过栈展开会绕过锁、析构和 JNI 状态恢复，不应作为 OOM 降级方案。

### 大型 App 的内存预算管理

预算要同时覆盖 Java、native、graphics、线程、FD 和地址空间；只盯 Java `maxMemory()` 会漏掉大量进程成本。

### 预算维度与测量方式

| 维度 | 实验室/CI 证据 | 线上轻量指标 |
|---|---|---|
| Java live heap | HPROF、对象数、retained size、场景前后差值 | Runtime heap 水位、GC 次数/时间、风险事件 |
| native malloc | heapprofd、Android Studio native allocations | `getNativeHeapAllocatedSize()` 趋势 |
| 进程物理成本 | `dumpsys meminfo`、PSS/RSS、smaps_rollup | 低频 PSS/RSS 或平台允许的 MemoryInfo |
| graphics/media | Perfetto、dma-buf/GraphicBuffer 与媒体工具 | 自有缓冲区数量、尺寸、格式和生命周期 |
| 线程与调度 | `/proc/self/task`、线程栈、executor 指标 | 线程数、线程池 active/queue/reject |
| FD | rlimit、`/proc/self/fd` 分类、创建方 | FD 总数、主要类别和增长率 |
| 虚拟地址 | maps/smaps、映射数、最大空洞 | VmSize、映射数、进程位数 |

所有指标都要绑定场景和时间点。冷启动后固定等待 5 秒无法代表首页稳定态：网络、图片、延迟初始化和 GC 时机都可能不同。更可靠的采样点是“场景完成条件满足 + 短暂稳定窗口”，并记录测试数据、账户、网络、设备温度和进程冷热状态。

### 从产品预算到模块责任

预算制定可以按以下步骤执行：

1. 选择低内存、主流和高配置设备组，记录 `ActivityManager.getMemoryClass()`、`getLargeMemoryClass()`、`isLowRamDevice()` 与进程位数。
2. 为冷启动、首页稳定态、重页面峰值、后台驻留和多次往返分别建立基线，至少重复多轮并报告分布。
3. 把增量归到可行动的责任模块：缓存、图片、模型、线程池、native 句柄、图形缓冲或映射文件。无法可靠归因时保留“进程共享”项。
4. 模块预算同时规定稳定态、峰值、回落时间和失败策略。只有“不得超过 N MB”会鼓励把内存推迟到另一个阶段。
5. CI 比较同设备同数据的分布与基线，门槛结合测量噪声、置信区间和产品余量，不能固定使用“增加 5 MB 就阻断”。
6. 发布后按设备、系统、ABI、版本和场景观察 OOME 用户率、`REASON_LOW_MEMORY`、PSS 长尾、线程与 FD 水位。
7. 回归发生时同时检查分母和场景覆盖，避免测试样本减少后误判为优化。

模块预算之和不能直接等于进程预算：Runtime、共享库、allocator、系统组件和模块共享对象都需要单独余量。进程预算也不能挤到设备可承受上限，前后台切换、相机、WebView、媒体与系统更新都会改变整机竞争。

### 验证降级是否有效

每个降级动作都要验证三类结果：

- **资源结果**：目标指标是否下降，下降发生在多长时间内，是否只是从 Java 转移到 native 或磁盘。
- **功能结果**：当前操作是否有明确失败提示、低规格结果或可重试状态，进程重建后数据是否一致。
- **性能结果**：缓存缩小后是否引入启动、网络、解码、功耗或 ANR 回归。

OOM 治理达到可发布状态时，高水位事件有责任模块，系统终止与 OOME 分开统计，慢设备和 32 位兼容进程都有覆盖，任何 `UncaughtExceptionHandler` 都保留平台默认处理路径。

## 参考资料

- [Android Developers：Prioritizing memory efficiency for Android 17](https://developer.android.com/blog/posts/prioritizing-memory-efficiency-essential-steps-for-android-17)
- [Android Developers：ComponentCallbacks2](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Android Developers：ProfilingTrigger.TRIGGER_TYPE_OOM](https://developer.android.com/reference/android/os/ProfilingTrigger#TRIGGER_TYPE_OOM)
- [Android Developers：ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android Developers：ActivityManager](https://developer.android.com/reference/android/app/ActivityManager)
- [Android Developers：Record native allocations](https://developer.android.com/studio/profile/record-native-allocations)
- [AOSP Android 17：ART Heap](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP Android 17：ART Thread](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/thread.cc)
- [AOSP Android 17：Unsafe native allocation](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/native/jdk_internal_misc_Unsafe.cc)
- [AOSP Android 17：HWUI Bitmap allocation](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/hwui/Bitmap.cpp)
- [AOSP Android 17：Bitmap JNI](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/Bitmap.cpp)
- [AOSP Android 17：ActivityThread largeHeap handling](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP Android 17：Bionic pthread creation](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/pthread_create.cpp)
- [AOSP Android 17：Bionic malloc controls](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/include/malloc.h)
- [AOSP Kernel `android17-6.18-2026-06_r6`：FD allocation](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/file.c)
- [AOSP Kernel `android17-6.18-2026-06_r6`：Process/thread creation](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/fork.c)
- [AOSP Kernel `android17-6.18-2026-06_r6`：Memory mapping](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/mmap.c)
