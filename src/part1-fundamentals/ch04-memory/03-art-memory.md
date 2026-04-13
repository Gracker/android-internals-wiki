---
title: "ART 虚拟机内存管理"
chapter: "4.3"
section: "4.3"
drafted_date: "2026-03-31"
drafted_by: "openclaw-task2"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 36)"
last_verified: "2026-03-31"
reviewed_date: "2026-04-14"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
last_verified_against: "AOSP android-15.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/art-management"
  - type: blog
    path: "ART虚拟机内存分配原理浅析 (微信技术文章)"
  - type: blog
    path: "ART虚拟机CMC GC算法核心实现介绍 (微信技术文章)"
  - type: blog
    path: "【Android ART】Heap的内存布局 (微信技术文章)"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles"
tags: ['art', 'gc', 'heap', 'tlab', 'aot', 'jit', 'cc-gc', 'cmc-gc', 'uffd', 'read-barrier', 'memory-allocation', 'generational-gc']
related_chapters: ["4.1", "4.2", "4.4", "4.6", "4.7", "4.8", "7.1", "7.7"]
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task6_result: needs-rework
task2b_state: pending
task9_result: needs-rework
---

# ART 虚拟机内存管理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ART 堆结构：Image Space、Zygote Space、Allocation Space、Large Object Space
- 🔹 GC 策略演进：CMS → CC (Concurrent Copying) GC
- 🔹 GC 对性能的影响：暂停时间（Pause Time）、吞吐量、Allocation Stall
- 🔹 对象分配路径：TLAB → Region → Full GC
- 🔹 ART Profile-Guided Compilation：Install-time、Runtime、Cloud Profile

### 扩展（可选深入）

- 🔸 JIT Compilation 的内存开销与 Code Cache 管理
- 🔸 Reference Processing（SoftRef、WeakRef、PhantomRef）与 GC 的交互
- 🔸 ART 在 Android 16 上的最新优化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 ART 的内存管理

我们在 Perfetto 中分析一个应用的卡顿问题时，经常会看到这样的现象：主线程突然被挂起几十毫秒，对应的时间片上标注着 `GC`。或者更隐蔽地，一个应用的帧率在持续滑动时逐渐下降，CPU 占用里 `HeapTaskDaemon` 线程的活跃时间越来越多。这些现象的背后，都是 ART 虚拟机的内存管理在工作。

理解 ART 的堆结构、GC 策略和对象分配机制，不是为了自己去实现垃圾回收器。我们的目标，是在拿到一份 Trace、看到 GC 暂停或 Allocation Stall 时，能快速判断这是正常波动，还是应用已经出现内存抖动，并知道该从哪里排查。读完这一节，我们应该能在 Perfetto 中识别 ART GC 的主要活动，理解它们对帧率和响应速度的影响，并掌握减少 GC 压力的基本方法。

[已验证: 官方文档, source.android.com/docs/core/perf/art-management]

## ART 堆结构：五个 Space 各司其职

ART 的 Heap 并不是一块单一的连续内存，而是由多个功能不同的 Space（空间）组合而成。每种 Space 有其特定的分配策略和 GC 行为，理解它们的分工是理解整个内存管理体系的基础。

[已验证: 官方文档, source.android.com/docs/core/perf/art-management]
[来源: Cubox/【Android ART】Heap的内存布局-2024-07-23.md]

### Image Space：系统启动时就位的基础设施

Image Space 是所有 Space 中最特殊的一块空间，它在应用进程启动之前就已经被填充好了。系统编译期间，构建工具会将启动类路径（bootclasspath）中的核心类预先实例化，并将完整的堆快照写入 `.art` 格式的镜像文件（如 `boot.art`）。Zygote 进程启动时，直接通过 `mmap` 将这些镜像文件映射到 Image Space 的地址空间。

这样做，是为了让每个 fork 出来的应用进程都能直接使用已经创建好的核心类对象，而不需要重新加载和初始化。在 Perfetto 中，这部分内存通常体现为进程启动阶段极快的类加载速度，因为这些对象并不需要重新加载，只是建立了映射关系。

Image Space 中的对象永远不会被 GC 回收，也不会被移动，因此 ART 在标记阶段可以直接跳过 Image Space，减少工作量。

AOSP 源码路径：`art/runtime/gc/space/image_space.cc`
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/image_space.cc]

### Zygote Space：fork 之前的快照

当 Zygote 进程完成预加载、即将 fork 第一个子进程之前，它会将自己分配的对象整理一番：把在 Allocation Space 中分配的、仍然存活的对象拷贝到 Non-moving Space 的尾部，然后把这些对象和 Non-moving Space 中原有的对象合并，形成 Zygote Space。原来的 Allocation Space 被清空，留给 fork 出来的子进程使用。

Zygote Space 中的对象同样不会被 GC 移动和回收。这样做的好处有两层：第一，由于 Zygote Space 在所有应用进程间通过 Copy-on-Write 共享，不移动这些对象避免了 COW 页的额外拷贝；第二，GC 可以跳过对 Zygote Space 的扫描，减少标记阶段的耗时。

在 Perfetto 的内存统计中，一个应用进程的 Zygote Space 通常占几 MB 到十几 MB，这些内存是与其他进程共享的（直到被写入）。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap.cc InitializeZygoteSpace]

### Allocation Space：应用的主战场

Allocation Space（也叫 Main Space）是应用运行期间绝大多数对象分配的地方。它是 ART 堆中最大、最活跃的区域，也是 GC 主要的工作对象。

Allocation Space 的具体实现取决于当前使用的 GC 策略：

- 在 Android 8.0–14 中使用 CC（Concurrent Copying）GC 时，Allocation Space 的数据结构是 `RegionSpace`，堆被划分为 256KB 固定大小的 Region
- 在 Android 15+ 使用 CMC（Concurrent Mark-Compact）GC 时，Allocation Space 的数据结构切换为 `BumpPointerSpace`，结构更简单，更有利于全局压缩

这两种策略在后续的 GC 策略演进部分会详细展开。

Allocation Space 有一个重要的版本差异值得注意：在 Android 15 之前，ART 使用分代策略（Young/Old Generation），Allocation Space 包含了 Nursery（新生代）和 Tenured（老年代）。Android 15 的 CMC GC 改变了这一模型，但分代假说仍然在影响着 GC 的触发策略。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/region_space.cc]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/bump_pointer_space.cc]

### Large Object Space：大对象的特殊处理

如果一个对象同时满足两个条件，大小超过阈值（通常是 3 页，即 12KB），并且类型是基本类型数组或 `String`，ART 会把它分配到 Large Object Space，而不是 Allocation Space。原因也很直接，CC GC 需要移动对象，大对象来回拷贝的成本太高。独立放入 Large Object Space 后，GC 只需要标记和清除，不必移动这些对象。

Large Object Space 有两种实现：

- **FreeListSpace**（arm64 设备）：在初始化时 `mmap` 一块与堆上限（`HeapGrowthLimit`）大小一致的内存，通过空闲链表管理页的分配和回收。相同大小的页可以被复用
- **LargeObjectMapSpace**（非 arm64 设备）：每次分配时直接 `mmap` 一块新的匿名内存，释放时 `munmap`

在 Perfetto 中，如果大对象分配很频繁，通常说明应用在持续创建大量 `byte[]` 或大 `String`。这种情况常见于图片处理、网络数据解析等场景。Large Object Space 持续增长时，要进一步检查是否存在大对象泄漏。

AOSP 源码路径：`art/runtime/gc/space/large_object_space.cc`
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/large_object_space.cc]

### Non-moving Space：地址不可变的对象

Non-moving Space 用于存放那些"地址不能变"的对象——通常是 Java 层的对象地址被传递到了 Native 层使用，比如 `DirectByteBuffer`、早期的 `Bitmap`（在 `HardwareBuffer` 普及之前）。如果 GC 移动了这些对象，Native 层持有的指针就会失效。

Android 15 上，Non-moving Space 的数据结构仍然是 `DlMallocSpace`，使用 Doug Lea 的 `dlmalloc` 算法管理内存。这个分配器在 Dalvik 时代就已经存在，如今只负责 Non-moving Space 这个"安静的角落"。

有一个容易踩到的坑：Non-moving Space 和 Zygote Space 共享 64MB 的地址空间。如果应用大量使用 `DirectByteBuffer`，即使总体堆内存还有空闲，也可能因为 Non-moving Space 耗尽而抛出 `OutOfMemoryError`。

[来源: Cubox/【Android ART】Heap的内存布局-2024-07-23.md]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/dlmalloc_space.cc]

[图：ART Heap 的五个 Space 在虚拟地址空间中的布局示意]

### [自动发现: 堆地址空间的 4GB 限制] 

来源: Cubox/【Android ART】Heap的内存布局-2024-07-23.md

一个容易忽略的细节是，ART 的所有 Space 都位于 0–4GB 的虚拟地址空间范围内，即使是在 64 位进程中也是如此。这样做的目的是让所有 Java 对象的引用（reference）都可以用 32 位（4 字节）表示，而不是 64 位的指针，每个对象引用节省一半的内存。对于一个有大量对象引用的应用来说，这个优化可以节省可观的堆空间。

这个设计在 Android 15 上仍然沿用。

[待验证: 4GB 限制是否在 Android 16/17 中有所变化]

## GC 策略演进：从 CMS 到 CC 再到 CMC

ART 的垃圾回收策略经历了几次重大演进，每一次演进都显著改变了 GC 对应用性能的影响方式。了解这个演进脉络，能帮助我们在不同 Android 版本的设备上做出准确的性能判断。

### Dalvik 时代：stop-the-world 的代价

Dalvik 虚拟机使用的是基于 `dlmalloc` 的标记-清除（Mark-Sweep）GC。整个 GC 过程需要暂停所有应用线程（stop-the-world），在堆中扫描所有可达对象，然后清除不可达的。在早期 Android 设备（1GB 以下内存）上，一次 Full GC 可能暂停 50-100ms——这在 60fps 的标准下意味着丢掉 3-6 帧。

Dalvik 时代分配器 `dlmalloc` 的另一层限制，是全局内存锁。所有线程共享同一把锁来分配内存。在多线程场景下，锁争用会拉长分配延迟，这也是早期 Android 应用在多核设备上性能提升不明显的底层原因之一。

[已验证: 官方文档, source.android.com/docs/core/perf/art-management]

### ART 初期（Android 5.0–7.0）：CMS 与 RosAlloc

ART 引入了 Concurrent Mark-Sweep（CMS）GC，将标记阶段的部分工作与应用线程并发执行，大幅减少了 stop-the-world 的暂停时间。前台应用使用 CMS，后台应用使用更激进的压缩策略来节省内存。

在分配器层面，ART 用 RosAlloc（Runs-of-Slots Allocator）替代了 `dlmalloc`。RosAlloc 将内存组织为由相同大小 slot 组成的 run，这些 run 以 page 为单位聚集。不同线程可以在不同的 run 上并行分配，通过分片锁定（sharded locking）策略减少了全局锁争用。

但 CMS 仍然有一个根本性的缺陷：它是非移动式的（non-moving）。标记-清除不会整理内存碎片。长时间运行的应用，堆中的空闲空间可能很多但都是碎片化的，导致无法分配大对象而触发更频繁的 GC，形成恶性循环。

AOSP 源码路径：`art/runtime/gc/collector/concurrent_mark_sweep.cc`
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/allocator/rosalloc.cc]

### Android 8.0：CC GC 的革命性突破

Android 8.0 Oreo 将 Concurrent Copying（CC）GC 设为默认策略，这是 ART 内存管理的一次根本性变革。

CC GC 的核心思想是：用两个 Space（FromSpace 和 ToSpace）交替使用，GC 时将存活对象从 FromSpace 拷贝到 ToSpace，拷贝完成后两个 Space 角色互换。这种拷贝式 GC 天然解决了碎片问题——每次 GC 后存活对象都被紧凑排列。

但"拷贝时应用还在跑"是个难题。ART 的解决方案是 **Read Barrier（读屏障）**：当 GC 正在移动一个对象时，如果应用线程试图读取该对象的引用，Read Barrier 会拦截这次读取，确保线程拿到的是移动后的正确地址。这个过程对应用代码完全透明。

```java
// Read Barrier 的概念示意（非实际代码）
Object readReference(Object holder, Field field) {
    Object ref = holder.field;           // 读取引用
    if (ref != null && gc.isMoving(ref)) {
        ref = gc.getForwardingAddress(ref); // 如果对象正在被移动，获取新地址
    }
    return ref;
}
```

上面的伪代码只是概念示意。Read Barrier 由编译器在每次对象引用读取时自动插入，开发者通常无感知。代价是每次引用读取都会多一次条件判断，大约带来 1-3% 的性能开销。

CC GC 引入后的关键性能提升：
- **堆大小**：比 Android 7.0 平均减少 32%（不再需要预留碎片空间）
- **GC 暂停时间**：减少 85%（大部分工作并发完成）
- **对象分配速度**：比 Android 7.0 快 70%

AOSP 源码路径：`art/runtime/gc/collector/concurrent_copying.cc`
[已验证: 官方文档, source.android.com/docs/core/perf/art-management]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/collector/concurrent_copying.cc]

### Android 15：CMC GC 与 UFFD 的巧妙结合

CC GC 虽然解决了碎片问题，但引入了两个新问题：第一，GC 过程中 FromSpace 和 ToSpace 同时存在，物理内存需求会短暂翻倍；第二，Read Barrier 对所有引用读取都有额外开销，即使没有 GC 在运行。

Android 15 引入的 Concurrent Mark-Compact（CMC）GC 解决了这两个问题。CMC 的核心创新是利用 Linux 的 **UFFD（User Fault FD）** 特性：

UFFD 允许用户空间程序注册一段虚拟内存范围的访问监控。当这段内存出现缺页异常（如 SIGBUS）时，内核不会直接处理，而是将异常交给用户空间程序处理。CMC GC 利用这个机制实现了"按需压缩"：GC 线程从后向前逐页压缩对象，如果应用线程访问到了一个尚未被压缩的页面，UFFD 会触发异常，VM 优先压缩这个页面然后返回给应用线程。

这样就不需要 Read Barrier 了——应用线程要么访问到已经压缩好的页面（直接可用），要么触发 UFFD 异常（等待当前页压缩完成）。GC 不运行时，没有任何额外开销。

CMC 的分配器也从 `RegionSpace` 切换为 `BumpPointerSpace`，结构更简单：分配时只需移动一个 top 指针（bump pointer），不需要维护 Region 的管理结构。

[来源: Cubox/ART虚拟机CMC GC算法核心实现介绍-2023-06-24.md]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/collector/concurrent_mark_compact.cc]

### 分代 GC：Young Generation 的快速回收

[已验证: 官方文档, source.android.com/docs/core/perf/art-management]

无论底层是 CC 还是 CMC，ART 都采用了分代垃圾回收策略。分代假说（Generational Hypothesis）告诉我们：绝大多数对象都是短命的——在一个典型的应用中，超过 90% 的对象在创建后很快就会变成垃圾。

ART 将 Allocation Space 划分为 Young Generation（新生代/Nursery）和 Old Generation（老年代/Tenured）。新对象首先进入 Young Generation。当 Young Generation 空间不足时，触发一次 Young GC（也叫 Partial GC）：

- Young GC 只扫描 Young Generation 中的对象，不扫描整个堆
- 暂停时间通常只有 1-3ms
- 仍然存活的对象被提升（promote）到 Old Generation

只有当 Old Generation 空间也不足时，才触发 Full GC（也叫 Full-Heap GC），扫描整个堆。Full GC 的代价比 Young GC 大得多，但在分代策略下，Full GC 的频率被大大降低。

在 Perfetto 中，我们可以通过以下方式观察分代 GC 的行为：
- **Young GC**：在 GC 线程上表现为短暂的、频繁的活动（通常每秒 1-2 次或更少）
- **Full GC**：表现为较长的、低频的 GC 活动，通常与堆增长或内存压力相关
- **如果一个应用的 Young GC 每秒超过 2-3 次**，通常意味着存在严重的对象抖动（object churn）

[图：Perfetto 中 Young GC vs Full GC 的典型表现对比]

## GC 对性能的影响：暂停、吞吐与 Stall

理解了 GC 策略的演进后，我们需要关注一个更实际的问题：GC 具体在哪些方面影响应用性能？

### Pause Time（暂停时间）

即使是并发 GC，也仍然有短暂的 stop-the-world 阶段——主要用于处理线程根集（thread roots）和完成最终的标记整理。在 CC/CMC GC 下，这个暂停通常只有 1-5ms，大部分情况下不会导致丢帧。

但以下情况会导致暂停时间异常增长：
- **堆过大**：堆越大，需要处理的对象越多
- **引用关系复杂**：大量 `SoftReference`/`WeakReference`/`PhantomReference` 需要特殊处理
- **Native 内存关联**：通过 JNI 持有 Java 对象引用的 Native 代码增加了根集的扫描范围

### Allocation Stall（分配阻塞）

当应用线程需要分配对象但堆中没有足够的空闲空间时，它必须等待 GC 完成回收。这种情况叫 Allocation Stall。在 Perfetto 中，它表现为应用线程在 `AllocObject` 或类似函数上被阻塞。

Allocation Stall 在以下场景中容易发生：
- 短时间内大量创建对象（如解析大型 JSON、加载大图）
- 堆接近上限，GC 刚刚完成但回收的空间不够
- 后台进程被 lmkd 杀掉导致内存压力增大

### GC 吞吐量

GC 吞吐量指的是应用运行时间占总时间的比例。如果 GC 吞吐量是 99%，意味着 1% 的时间花在了 GC 上。在正常应用中，这个值应该在 98% 以上。如果降到 95% 以下，用户很可能感知到卡顿。

在 Perfetto 中可以通过 `art_gc_*` 相关的 counter track 来监控 GC 的吞吐量和频率。

[已验证: 官方文档, source.android.com/docs/core/perf/art-management]

## 对象分配路径：从 TLAB 到 Full GC

了解对象在 ART 中是如何分配的，有助于我们理解为什么某些代码模式会导致性能问题。

### TLAB 分配：最快路径

Android 8.0+ 的 CC GC 引入了 RegionTLAB（Thread Local Allocation Buffer）分配策略。每个应用线程从 `RegionSpace` 中获取自己专属的 TLAB——一块连续的内存缓冲区。线程在自己的 TLAB 中分配对象时，只需要移动一个 top 指针（bump pointer），无需任何同步操作：

```
// 概念伪代码：TLAB 分配
Object allocate(size_t size) {
    if (tlab_top + size <= tlab_end) {
        void* addr = tlab_top;
        tlab_top += size;      // 只需移动 top 指针
        return new(addr) Object();  // 零同步开销
    }
    return allocateSlowPath(size);  // TLAB 耗尽，走慢路径
}
```

TLAB 分配的速度比 Android 7.0 快 70%，比 Dalvik 时代快约 18 倍。这是 ART 内存分配的"快车道"——只要 TLAB 有空间，对象分配几乎是免费的。

AOSP 源码路径：`art/runtime/gc/space/region_space.cc (AllocNewTLAB)`
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/region_space.cc]

### Region 分配：TLAB 耗尽后

当线程的 TLAB 空间用完时，它需要向 `RegionSpace` 请求分配一个新的 TLAB。这个过程需要获取堆锁（heap lock），但只需要很短的时间——从空闲 Region 列表中取出一个 Region（256KB），划分给该线程作为新的 TLAB。

如果空闲 Region 列表为空，就需要从操作系统的虚拟地址空间中 `mmap` 新的内存页来创建新的 Region。

### 分配失败与 GC 触发

当堆的使用量接近上限（由 `HeapGrowthLimit` 或 `HeapMaxLimit` 控制）时，新的分配请求会触发 GC。触发路径如下：

1. **分配失败** → 检查是否可以增长堆 → 如果可以，增长后重试
2. **无法增长** → 触发 Concurrent GC（后台执行）→ 等待 GC 完成后重试
3. **GC 后仍然不够** → 触发 Full GC（stop-the-world）→ 重试
4. **Full GC 后还不够** → 抛出 `OutOfMemoryError`

这就是为什么在 Perfetto 中经常看到 GC 活动紧跟在大量对象分配之后——是分配失败触发了 GC，而不是反过来。

### 大对象分配的独立路径

前面提到，超过 12KB 的基本类型数组或 `String` 会进入 Large Object Space。大对象的分配路径与小对象完全独立，走的是 `FreeListSpace` 或 `LargeObjectMapSpace` 的分配逻辑。由于大对象不会被移动，GC 对它们的处理也更简单——只需要标记存活和清除死亡，不需要拷贝或压缩。

[来源: Cubox/ART虚拟机内存分配原理浅析-2024-03-17.md]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap.cc TryToAllocate]

## ART Profile-Guided Compilation：让代码越跑越快

ART 的内存管理不仅仅涉及堆和 GC，还包括编译策略对内存的影响。ART 采用混合编译模式：解释执行、JIT（Just-In-Time）编译和 AOT（Ahead-Of-Time）编译三者结合。这个策略直接影响了应用的内存占用和运行时性能。

### 三种编译模式的协作

ART 的编译策略可以简化为以下流程：

1. **首次运行**：方法首先被解释执行（最慢，但无需编译时间和空间）
2. **JIT 编译**：频繁执行的方法被 JIT 编译为机器码，存入 Code Cache（在内存中）
3. **Profile 收集**：ART 在运行过程中记录哪些方法被频繁执行，生成 Profile 文件
4. **AOT 编译**：设备空闲且充电时，编译守护进程（`dex2oat`）根据 Profile 对热点代码进行 AOT 编译，结果持久化到磁盘

这种混合策略的核心思想是：用最少的内存和时间，让最重要的代码运行得最快。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]

### Baseline Profiles：安装时就优化

Baseline Profiles 是 Google 在 Android 13（正式推广）引入的机制，允许开发者在 APK/AAB 中预置一份"热点方法清单"。当用户从 Google Play 安装应用时，ART 会在安装阶段就对这些方法进行 AOT 编译。

对于一个全新安装的应用，即使没有 Cloud Profile 数据，也没有历史运行记录，用户第一次启动时仍然可以拿到接近 AOT 编译的性能。Google 的数据显示，使用 Baseline Profiles 可以将冷启动速度提升 20-30%。

对于开发者来说，Baseline Profiles 的使用方式很简单：通过 `BaselineProfileRule` 在自动化测试中生成 Profile 文件，然后打包到 APK 中。

### Cloud Profiles：聚合真实用户数据

Cloud Profiles 是 Google Play 在后台聚合的数据：当一批用户安装并使用了新版本应用后，Play 会收集他们的运行时 Profile，聚合后分发给后续安装同一版本的用户。

Cloud Profiles 解决了 Baseline Profiles 无法覆盖的问题：开发者可能不知道所有热点代码路径，但真实用户的使用数据可以揭示开发者未曾关注的性能瓶颈。

### 编译策略对内存的影响

AOT 编译后的机器码存储在 `.oat` 和 `.vdex` 文件中，运行时通过 `mmap` 映射到进程地址空间。这些文件的大小直接影响了应用的内存占用：

- **过度 AOT 编译**：如果 Profile 包含了太多方法，`.oat` 文件会很大，mmap 后占用大量虚拟地址空间
- **JIT Code Cache**：运行时 JIT 编译的代码存在内存中的 Code Cache 里，默认大小约 4-16MB（取决于设备配置）。如果 Code Cache 满了，旧的编译结果会被淘汰，对应的方法回退到解释执行

在 Perfetto 中可以通过 `art_jit_*` 相关的事件来观察 JIT 编译活动。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]

### Android 15/16 的 16KB Page Size 对 ART 的影响

[来源: intake/research-feeds/2026-03-31-11-ch04-art-16kb-page-memory.md]

Android 15 引入了 16KB 内存页大小的支持（替代传统的 4KB 页），这对 ART 有以下影响：

ART 的 RegionSpace 默认使用 256KB 的 Region，恰好是 16KB 的整数倍（256 / 16 = 16），所以 Region 级别的布局几乎不受影响。但 TLAB 的最小分配单位从 4KB 变为 16KB，如果应用创建了大量线程但每个线程分配量很小，会有更多的内存被 TLAB 预占但未使用。

Google 报告在部分工作负载上，16KB 页通过减少 TLB miss 带来了约 5-10% 的性能提升。Android 16 为未适配 16KB 页的应用提供了兼容模式。

[待验证: 16KB Page Size 在不同 SoC 平台上的实际性能差异]

## 在 Perfetto 中观察 ART GC

了解原理后，接下来转到 Perfetto 中的实际观察路径。

### 关键 Track 和事件

在 Perfetto 的 UI 中，ART GC 的活动分布在几个关键位置：

- **`art_gc` counter track**：显示 GC 的整体活动。Young GC 在这个 track 上表现为短促的脉冲，Full GC 则是持续更长的波峰
- **`HeapTaskDaemon` 线程**：ART 的后台 GC 线程，Concurrent GC 的主要执行者。这个线程的活跃区间对应并发标记和拷贝/压缩的时间
- **`AllocObject` trace point**：当应用线程在分配对象时被阻塞（Allocation Stall），对应线程的 track 上会出现这个 slice

对于需要量化分析的场景，可以使用 Perfetto 的 SQL 视图。以下查询统计一段时间内各类型 GC 的次数和平均耗时：

```sql
-- 统计 GC 事件类型、次数和平均耗时
SELECT
  slice.name AS gc_type,
  COUNT(*) AS count,
  ROUND(AVG(dur / 1e6), 2) AS avg_duration_ms
FROM slice
JOIN track ON slice.track_id = track.id
WHERE track.name LIKE '%art_gc%'
  AND slice.name LIKE '%GC%'
GROUP BY gc_type
ORDER BY avg_duration_ms DESC;
```

另一个实用的查询是检查 Allocation Stall——找出哪些线程在对象分配上等待了多久：

```sql
-- 查找 Allocation Stall 事件
SELECT
  process.name AS process_name,
  thread.name AS thread_name,
  slice.name,
  ROUND(slice.dur / 1e6, 2) AS stall_duration_ms
FROM slice
JOIN track ON slice.track_id = track.id
JOIN thread_track ON thread_track.id = track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE slice.name LIKE '%AllocObject%'
  AND slice.dur > 1e6  -- 只看超过 1ms 的 stall
ORDER BY slice.dur DESC
LIMIT 20;
```

这些 SQL 查询的结果可以直接指导优化方向：如果 Young GC 平均耗时超过 5ms，需要排查对象抖动；如果 Allocation Stall 频繁出现，说明堆空间需要优化或增大。

### 正常 vs 异常的 GC 模式

正常情况下，一个中等复杂度的应用：
- Young GC 频率：每 2-5 秒一次，每次 1-3ms
- Full GC 频率：每几分钟一次（甚至更少）
- GC 吞吐量：> 98%
- Allocation Stall：几乎不可见

需要警惕的异常信号主要有四类。

如果 Young GC 频繁到每秒多次，通常是对象抖动，大量临时对象被快速创建又快速丢弃，需要检查循环内的对象分配。

如果 Full GC 每十几秒就触发一次，说明堆压力持续偏高，可能存在内存泄漏，或者数据结构选择不当（比如用 `ArrayList` 存储海量数据，而不是按需分页）。

如果 Allocation Stall 已经明显出现在 Trace 中，说明堆接近上限，需要减少峰值内存使用。

如果 GC 线程的 CPU 占用持续较高，说明整体 GC 压力偏大，应该从源头减少对象分配，而不是指望 GC 策略兜底。

[待补充：Trace 截图展示正常和异常 GC 模式的对比]

## 常见问题与误区

### 误区一：GC 导致了卡顿，应该手动调用 System.gc()

恰恰相反。`System.gc()` 会强制触发一次 Full GC，暂停时间比正常的 Young GC 长得多。ART 的 GC 是自适应的，它知道什么时候该回收。如果发现需要手动触发 GC 来"解决问题"，通常说明存在内存泄漏或对象抖动，应该从源头修复。

### 误区二：对象池总是能减少 GC 压力

对象池在特定场景（如游戏中的子弹对象、消息队列的 Message）下确实有效。但不加区分地使用对象池反而会增加 Old Generation 中的常驻对象，导致 Full GC 时需要扫描更多的存活对象。正确做法是先用 Trace 分析确认 GC 压力来源，再针对性地优化。

### 误区三：Android 的 GC 已经足够快了，不需要关注

虽然 ART 的 GC 确实比 Dalvik 时代快了很多，但在 120Hz 设备上，一帧只有 8.33ms。即使一次 GC 暂停只有 3ms，如果恰好发生在帧的关键路径上，也可能导致掉帧。特别是在 Compose 应用中，recomposition 可能产生大量临时对象——如果不注意优化，GC 仍然是卡顿的重要来源。

### 误区四：堆越大越好

ART 的堆大小受到系统限制（由 `ActivityManager.getMemoryClass()` 返回，通常 128-512MB）。更大的堆意味着 GC 需要扫描更多的对象，暂停时间会相应增长。此外，一个应用占用过多堆空间，会导致其他应用的可用内存减少，触发更频繁的 lmkd 进程回收。合理的内存使用比申请更大的堆更有价值。

[已验证: 官方文档, source.android.com/docs/core/perf/art-management]

## 与其他章节的关联

- **4.1 Android 内存模型全景**：ART 堆是 Android 内存体系中的"Java 层内存"部分
- **4.2 Linux 内核内存管理**：ART 的 `mmap` 分配最终由内核管理，OOM Killer 由 lmkd 实现
- **4.4 Low Memory Killer**：当应用 GC 后仍然占用过多内存，lmkd 可能会介入回收
- **7.1 卡顿的定义与分类**：GC 暂停和 Allocation Stall 是卡顿的重要来源之一
- **7.7 Jetpack Compose 性能优化**：Compose 的 recomposition 可能产生大量临时对象，触发频繁 Young GC

## 参考资料

### AOSP 源码路径
- ART Heap 管理：`art/runtime/gc/heap.cc`
- Concurrent Copying GC：`art/runtime/gc/collector/concurrent_copying.cc`
- Concurrent Mark-Compact GC：`art/runtime/gc/collector/concurrent_mark_compact.cc`
- RegionSpace（CC GC 的分配器）：`art/runtime/gc/space/region_space.cc`
- BumpPointerSpace（CMC GC 的分配器）：`art/runtime/gc/space/bump_pointer_space.cc`
- RosAlloc：`art/runtime/gc/allocator/rosalloc.cc`
- Image Space：`art/runtime/gc/space/image_space.cc`
- Large Object Space：`art/runtime/gc/space/large_object_space.cc`
- TLAB 分配：`art/runtime/gc/space/region_space.cc (AllocNewTLAB)`
- Profile 管理：`art/runtime/jit/profile_saver.cc`

### 官方文档
- [Manage device memory | source.android.com](https://source.android.com/docs/core/perf/art-management)
- [Baseline Profiles | developer.android.com](https://developer.android.com/topic/performance/baselineprofiles)
- [16KB Page Size | developer.android.com](https://developer.android.com/guide/practices/page-sizes)

### 素材来源
- [ART虚拟机内存分配原理浅析](https://cubox.pro/web/card/7169016886301033688)
- [ART虚拟机CMC GC算法核心实现介绍](https://cubox.pro/web/card/7072254330031571026)
- [【Android ART】Heap的内存布局](https://cubox.pro/web/card/7215366783438422022)
- [研究] ART 内存分配器演进（dlmalloc → RosAlloc → RegionTLAB）
- [研究] ART 分代 GC 架构（Young/Old Generation + Concurrent Copying）
- [研究] Android 15/16 的 16KB Page Size 对 ART 内存的影响
