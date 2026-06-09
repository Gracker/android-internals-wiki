---
status: "ready-for-review"
title: ART 虚拟机内存管理
chapter: '4.3'
section: '4.3'
drafted_date: '2026-03-31'
drafted_by: openclaw-task2
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-06-10'
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
last_verified_against: "AOSP android-14.0.0_r1 / android-15.0.0_r1 / android-16.0.0_r1 + Android Developers Blog (Android 16 QPR2); android-17.0.0_r1 tag unavailable on 2026-06-10"
confidence: medium
sources:
- type: official
  path: https://source.android.com/docs/core/runtime/gc-debug
- type: blog
  path: ART虚拟机内存分配原理浅析 (微信技术文章)
- type: blog
  path: ART虚拟机CMC GC算法核心实现介绍 (微信技术文章)
- type: blog
  path: 【Android ART】Heap的内存布局 (微信技术文章)
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: official
  path: https://android-developers.googleblog.com/2025/12/android-16-qpr2-is-released.html
tags:
- art
- gc
- heap
- tlab
- aot
- jit
- cc-gc
- cmc-gc
- uffd
- read-barrier
- memory-allocation
- generational-gc
related_chapters:
- '4.1'
- '4.2'
- '4.4'
- '4.6'
- '4.7'
- '4.8'
- '7.1'
- '7.7'
last_task2b_at: "2026-06-09T20:59:35+08:00"
reviewed_date: '2026-06-09'
reviewed_by: openclaw-task6
last_task6_at: '2026-06-09T23:13:33+08:00'
last_task6_audit: 2026-06-09
last_task6_review_log: logs/review/2026-06-09-23-review.md
task6_state: "revisiting"
task6_result: pass-light-edit
review_notes: '2026-06-09 23:00 Task6 revisiting 第三轮复审。L1 小修 4 处（3 处口水过渡词"更合适/更准确"，1 处附录格式）。无新增 L3/L4 回炉项。送 Task9 复审 auto-fixed 内容。 | 2026-06-09 21:09 Task6 revisiting 复审。L1/L2 小修 2 处。源码调研附录（AIW-源码调研-2026-06-09）未整合进正文为 L3 建议。送 Task9 复审。 | 2026-06-09 20:56 Task2B main 回炉。P0: 删除 05-28 Generational CMC 注入块(不存在 generational_collector.cc、gc_type.h 枚举名错误、未验证 Android 17 结论)。P1: 移除 "与 AIW §4.3现有描述的差异" 小节(指向已删块)。保留 06-09 一手验证块。 | 2026-04-30 task9 deep-review: needs-rework。P1 1 / P2 1。 | 2026-05-08 Task9 12:39：needs-rework。P1 2；DeliQueue/ConcurrentMessageQueue 版本与命名口径未证实，Perfetto ART GC track/SQL 口径与 ATrace 源码不匹配，已写入 queue。P2 既有 suggestions 保留，不重复新增。 | 2026-05-09 Task6 02:08：revisiting 写作复审；修复元叙述与 Perfetto GC counter 表述一致性 3 处，无新增 L3/L4 回炉项，转 Task9 复审。 | 2026-05-09 Task9 02:30：needs-rework。P1 1：DeliQueue / ConcurrentMessageQueue 命名与 ART ReferenceQueue 因果链仍未证实；保留既有 P2（LOS 实现选择、ART 8 性能数字、GC 阈值）不重复入队。 | 2026-05-12 Task6 16:15：L1/L2 小修 9 处；发现参考资料后追加调研材料未整合、实战案例不足等 L3/L4 问题，已写入 queue.json（priority 90）。'
task6_review_notes: "2026-06-09 23: Task6 revisiting 第三轮复审；L1 小修 4 处（口水过渡词 3 + 附录格式 1），无 L3/L4 回炉项，送 Task9 复审 auto-fixed 内容。 | 2026-06-09 21 Task6 revisiting 复审；Task2B 已删除 05-28 注入块，06-09 一手验证块保留。L1/L2 小修 2 处（"这样做，是为了让"重复起手式→直接陈述）。源码调研附录风格未整合为 L3 建议交 Task2B。送 Task9 技术复审。 | 2026-05-17 Task6 11: Task2B 回炉修复后复审；L1/L2 小修 5 处，未新增 L3/L4 回炉项，送 Task9 技术复审。" "2026-05-17 Task6 11: Task2B 回炉修复后复审；L1/L2 小修 5 处，未新增 L3/L4 回炉项，送 Task9 技术复审。"
task9_state: "reviewed"
task9_reviewed_date: '2026-06-10'
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-10T00:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-10-00-deep-review.md"
task2b_state: "fixed"
task2b_result: "fixed"
pipeline_stage: "task6_pending"
p0: 0
p1: 0
p2: 0
task9_review_notes: "2026-06-10 00:20 Task9 deep-review auto-fixed。P0: 修正 Zygote Space 源码锚点为 Heap::PreZygoteFork()，修正 LOS/main moving space 移动属性误写。P1: 收窄 Android17/Generational CMC 口径（android-17.0.0_r1 tag 仍为空），回 Task6 复审。 | 2026-06-09 22 Task9 deep-review auto-fixed。P0: 修正 06-09 源码调研块中 CMC kernel/userfaultfd 条件（Linux 5.13/MREMAP_DONTUNMAP + SIGBUS，minor-fault 非启用前提）；P1: 删除 Android17 候选结论口径；P2: 移除未 benchmark 的 CC/CMC 暂停时间表。回 Task6 复审。 | 2026-06-09 20 Task9 idle audit→Task2B 主修复已删除 05-28 注入块(虚假源码路径+未验证 Android 17 结论)。06-09 一手验证块保留。 | 2026-05-17 15 Task9 re-review: pass-tech-review。P0/P1 已清零；LOS FreeList/Map、CMC/BumpPointerSpace、Generational CMC 开关、JIT Code Cache 口径已对上 AOSP。GC baseline 数据 P2 既有 suggestions 保留。自动晋升 finalized。 | 2026-06-09 20 Task9 idle audit: needs-rework。P0 1：2026-05-28 Generational CMC 注入块存在 AOSP 源码路径/枚举错误；P1 1：Android 17/Generational CMC 版本边界证据不足，回 Task2B 清理或重写。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-27
last_task9_audit: 2026-06-09
task9_result: "auto-fixed"
last_task9_autofix_at: 2026-06-10
---

# ART 虚拟机内存管理

## 为什么要了解 ART 的内存管理

在 Perfetto 中分析应用卡顿时，经常会看到这样的现象：主线程突然被挂起几十毫秒，时间片上标注着 `GC`；或者更隐蔽地，应用的帧率在滑动过程中逐渐下降，同时 `HeapTaskDaemon` 线程的 CPU 占用越来越多。这些表现背后，都是 ART 虚拟机的内存管理机制在工作。

如果不知道 ART 的堆结构、GC 策略和对象分配路径，面对这些问题就像在黑暗中摸索——你不知道 GC 为什么在这个时候暂停，不清楚对象分配为什么会阻塞，也无法判断当前的内存使用模式是否正常。

理解这些机制后，可以：
1. 在 Trace 中准确识别 ART GC 活动，区分正常的 Young GC 和有问题的 Full GC
2. 判断 Allocation Stall 的触发原因，而不是简单归结为"内存不足"
3. 在面对内存泄漏或抖动时，快速定位到具体的分配模式或 GC 策略问题

这节要解决的是更具体的 Trace 判断问题：看到 GC slice、Allocation Stall 或 `HeapTaskDaemon` 活跃时，能判断它们分别指向哪一类内存压力，而不是只会读 `dumpsys meminfo` 的汇总数字。

[已验证: 官方文档, https://source.android.com/docs/core/runtime/gc-debug]

## ART 堆结构：五类 Space 的分工

ART 的 Heap 由多个功能不同的 Space（空间）组合而成，单一连续内存这个模型不足以解释 ART 的分配策略和 GC 行为。理解这些 Space 的分工，是理解整个内存管理体系的基础。

[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]

### Image Space：系统启动时就位的基础对象

Image Space 是所有 Space 中最特殊的一块空间，它在应用进程启动之前就已经被填充好了。系统编译期间，构建工具会将启动类路径（bootclasspath）中的核心类预先实例化，并将完整的堆快照写入 `.art` 格式的镜像文件（如 `boot.art`）。Zygote 进程启动时，直接通过 `mmap` 将这些镜像文件映射到 Image Space 的地址空间。

每个 fork 出来的应用进程可以直接使用已经创建好的核心类对象，不需要重新加载和初始化。在 Perfetto 中，这部分内存通常体现为进程启动阶段极快的类加载速度，因为这些对象并不需要重新加载，只是建立了映射关系。

Image Space 中的对象永远不会被 GC 回收，也不会被移动，因此 ART 在标记阶段可以直接跳过 Image Space，减少工作量。

AOSP 源码路径：`art/runtime/gc/space/image_space.cc`
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/image_space.cc]

### Zygote Space：fork 之前的快照

当 Zygote 进程完成预加载、即将 fork 第一个子进程之前，它会将自己分配的对象整理一番：把在 Allocation Space 中分配的、仍然存活的对象拷贝到 Non-moving Space 的尾部，然后把这些对象和 Non-moving Space 中原有的对象合并，形成 Zygote Space。原来的 Allocation Space 被清空，留给 fork 出来的子进程使用。

Zygote Space 中的对象同样不会被 GC 移动和回收。这样做的好处有两层：第一，由于 Zygote Space 在所有应用进程间通过 Copy-on-Write 共享，不移动这些对象避免了 COW 页的额外拷贝；第二，GC 可以跳过对 Zygote Space 的扫描，减少标记阶段的耗时。

在 Perfetto 的内存统计中，一个应用进程的 Zygote Space 通常占几 MB 到十几 MB，这些内存是与其他进程共享的（直到被写入）。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap.cc Heap::PreZygoteFork()]

### Allocation Space：应用的主要分配区域

Allocation Space（也叫 Main Space）是应用运行期间绝大多数对象分配的地方。它是 ART 堆中最大、最活跃的区域，也是 GC 主要的工作对象。

Allocation Space 的具体实现取决于当前使用的 GC 策略：

- 在 Android 8.0–14 中使用 CC（Concurrent Copying）GC 时，Allocation Space 的数据结构是 `RegionSpace`，堆被划分为 256KB 固定大小的 Region
- 在 Android 15+ 的 CMC（Concurrent Mark-Compact）GC 路径上，Allocation Space 可以使用 `BumpPointerSpace`，结构更简单，更有利于全局压缩。但启用取决于 `gUseUserfaultfd`、内核 userfaultfd/MREMAP_DONTUNMAP 能力、系统属性和构建配置，不满足条件时仍走 CC/RegionSpace 路径

Android 15 针对 16KB 页环境改造了 `BumpPointerSpace` 的分配边界。旧版本中，分配边界硬编码为 4KB 对齐（`RoundUp(capacity, kPageSize)`）。从 `android-15.0.0_r1` 起，改为动态获取当前页大小（`RoundUp(capacity, gPageSize)`），全局变量 `gPageSize` 在 ART 初始化阶段由 `InitPageSize()` 设置，对应源码位于 `art/runtime/gc/space/bump_pointer_space.cc`。


Allocation Space 的实现和分代策略要按平台版本拆开看。Android 8.0-13 的主线是基于 `RegionSpace` 的 CC 路径，年轻对象优先在更小的工作集里回收。到了 Android 14，AOSP 平台源码已经出现 `kCollectorTypeCMC` 和 `mark_compact.cc`，说明 UFFD 驱动的 Mark Compact / CMC 路径已经进入主线实现；Android 15 继续补齐 `kCollectorTypeCMCBackground`、`BumpPointerSpace` 等配套结构。公开发布材料把 Generational CMC 明确讲清楚，则是 Android 16 QPR2 之后的事情。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/region_space.cc]
[已验证: AOSP android-14.0.0_r1, art/runtime/gc/collector_type.h]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/bump_pointer_space.cc]
[已验证: Android Developers Blog, Android 16 QPR2 is Released]

### Large Object Space：大对象的特殊处理

如果一个对象同时满足两个条件，大小达到大对象阈值，并且类型是基本类型数组或 `String`，ART 会把它分配到 Large Object Space，而不是 Allocation Space。以 `android-15.0.0_r1` 为例，`Heap::kMinLargeObjectThreshold`（定义在 `art/runtime/gc/heap.h`）的默认值是 `12 * KB`。大对象判断入口在 `Heap::ShouldAllocLargeObject(ObjPtr<mirror::Class>, size_t)`（定义在 `art/runtime/gc/heap-inl.h`），它会检查对象类型是否为 primitive array 或 `String`。旧资料常把这个阈值写成 `3 * kPageSize`，但在 Android 15 的平台源码里它已经固定成 12KB。结合 16KB page size 的适配背景，AOSP 把 LOS 入口从页大小解耦，避免不同页大小设备出现不同的大对象分配边界。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap.h]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap-inl.h]

Large Object Space 有两种实现：

- **FreeListSpace**：在初始化时 `mmap` 一块与堆上限（`HeapGrowthLimit`）大小一致的内存，通过空闲链表管理页的分配和回收。相同大小的页可以被复用
- **LargeObjectMapSpace**：每次分配时直接 `mmap` 一块新的匿名内存，释放时 `munmap`

两者的选择不是按 arm64 / 非 arm64 划分，而是由 `USE_ART_LOW_4G_ALLOCATOR` 构建宏决定：启用时使用 `FreeListSpace`，不启用时使用 `LargeObjectMapSpace`。这个宏与设备的堆地址空间布局相关（4GB 压缩引用窗口），不是简单的架构区分。`Heap::kDefaultLargeObjectSpaceType` 定义在 `art/runtime/gc/heap.h` 中，最终值取决于这个宏。

[已验证: AOSP android-16.0.0_r1, art/runtime/gc/heap.h, art/runtime/gc/space/large_object_space.cc]

在 Perfetto 中，如果大对象分配很频繁，通常说明应用在持续创建大量 `byte[]` 或大 `String`。这种情况常见于图片处理、网络数据解析等场景。Large Object Space 持续增长时，要进一步检查是否存在大对象泄漏。

AOSP 源码路径：`art/runtime/gc/space/large_object_space.cc`
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/large_object_space.cc]

### Non-moving Space：地址不可变的对象

Non-moving Space 用于存放那些"地址不能变"的对象——通常是 Java 层的对象地址被传递到了 Native 层使用，比如 `DirectByteBuffer`、早期的 `Bitmap`（在 `HardwareBuffer` 普及之前）。如果 GC 移动了这些对象，Native 层持有的指针就会失效。

Android 15 上，Non-moving Space 的数据结构仍然是 `DlMallocSpace`，使用 Doug Lea 的 `dlmalloc` 算法管理内存。这个分配器在 Dalvik 时代就已经存在，如今只负责 Non-moving Space 这个"安静的角落"。

有一个容易踩到的坑：Non-moving Space 和 Zygote Space 共享 64MB 的地址空间。如果应用大量使用 `DirectByteBuffer`，即使总体堆内存还有空闲，也可能因为 Non-moving Space 耗尽而抛出 `OutOfMemoryError`。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/space/dlmalloc_space.cc]

[图：ART Heap 的五个 Space 在虚拟地址空间中的布局示意]

### 堆地址空间的 4GB 限制


一个容易忽略的细节是，ART 的主要托管堆和相关 card table 布局会尽量放在 low 4GB 区间。`heap.cc` 里能直接看到 `/* low_4gb= */ true` 的映射请求，以及“card table 覆盖 whole low_4gb”的注释。这样 `CompressedReference` / `HeapReference` 就能继续用 32 位压缩引用表示 Java 对象引用，在 64 位进程里减少引用字段的内存开销，并减轻缓存压力。

这里说的“4GB 限制”指的是 ART 为托管堆保留的低地址窗口，而不是 64 位进程只能使用 4GB 虚拟地址空间。Native heap、Code Cache 和其他映射并不受这条约束。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap.cc]
[已验证: AOSP android-15.0.0_r1, art/runtime/mirror/object_reference.h]

## GC 策略演进：从 CMS 到 CC 再到 CMC

ART 的垃圾回收策略经历了几次版本切换，每一次切换都会改变 GC 对应用性能的影响方式。了解这个演进脉络，能帮助读者在不同 Android 版本的设备上做出准确的性能判断。

### Dalvik 时代：stop-the-world 的代价

Dalvik 虚拟机使用的是基于 `dlmalloc` 的标记-清除（Mark-Sweep）GC。整个 GC 过程需要暂停所有应用线程（stop-the-world），在堆中扫描所有可达对象，然后清除不可达的。在早期 Android 设备（1GB 以下内存）上，一次 Full GC 可能暂停 50-100ms——这在 60fps 的标准下意味着丢掉 3-6 帧。

Dalvik 时代分配器 `dlmalloc` 的另一层限制，是全局内存锁。所有线程共享同一把锁来分配内存。在多线程场景下，锁争用会拉长分配延迟，这也是早期 Android 应用在多核设备上性能提升不明显的底层原因之一。

[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]

### ART 初期（Android 5.0–7.0）：CMS 与 RosAlloc

ART 引入了 Concurrent Mark-Sweep（CMS）GC，将标记阶段的部分工作与应用线程并发执行，大幅减少了 stop-the-world 的暂停时间。前台应用使用 CMS，后台应用使用更激进的压缩策略来节省内存。

在分配器层面，ART 用 RosAlloc（Runs-of-Slots Allocator）替代了 `dlmalloc`。RosAlloc 将内存组织为由相同大小 slot 组成的 run，这些 run 以 page 为单位聚集。不同线程可以在不同的 run 上并行分配，通过分片锁定（sharded locking）策略减少了全局锁争用。

但 CMS 仍然有一个主要缺陷：它是非移动式的（non-moving）。标记-清除不会整理内存碎片。长时间运行的应用，堆中的空闲空间可能很多但都是碎片化的，导致无法分配大对象而触发更频繁的 GC，形成恶性循环。

ART 的 CMS 实现分布在多个文件中。核心标记-清除逻辑在 `art/runtime/gc/collector/mark_sweep.cc`（`MarkSweep` / `PartialMarkSweep` / `StickyMarkSweep`），而非 `concurrent_mark_sweep.cc`。`art/runtime/gc/collector/` 目录下没有名为 `concurrent_mark_sweep.cc` 的文件。
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/allocator/rosalloc.cc]

### Android 8.0：CC GC 成为默认策略

Android 8.0 Oreo 将 Concurrent Copying（CC）GC 设为默认策略，这是 ART 内存管理的一次重要切换。

CC GC 的做法是：用两个 Space（FromSpace 和 ToSpace）交替使用，GC 时将存活对象从 FromSpace 拷贝到 ToSpace，拷贝完成后两个 Space 角色互换。这种拷贝式 GC 可以整理碎片——每次 GC 后存活对象都被紧凑排列。

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

CC GC 带来的性能变化主要落在三处：
- **堆大小**：比 Android 7.0 平均减少 32%（不再需要预留碎片空间）
- **GC 暂停时间**：减少 85%（大部分工作并发完成）
- **对象分配速度**：比 Android 7.0 快 70%

AOSP 源码路径：`art/runtime/gc/collector/concurrent_copying.cc`
[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/collector/concurrent_copying.cc]

### Android 14 / 15：UFFD 驱动的 Mark Compact / CMC 路径

CC GC 解决了碎片问题，但代价也很具体。拷贝式回收需要同时保留 from-space 和 to-space，回收窗口里的物理内存压力更高。Read Barrier 还会插入到对象引用读取路径上，GC 不运行时这层开销也在。

从 `android-14.0.0_r1` 开始，ART 平台源码已经有 `kCollectorTypeCMC` 和 `art/runtime/gc/collector/mark_compact.cc`。到 `android-15.0.0_r1`，`kCollectorTypeCMCBackground`、`BumpPointerSpace` 和 `MarkCompact::GetUffdAndMinorFault()` 这类配套实现更完整。Android 14 / 15 已进入 UFFD 驱动的 Mark Compact / CMC 路径，但不要把这条路线直接写成 Generational CMC。

UFFD 允许用户空间监听一段虚拟内存的缺页事件。GC 压缩对象时，如果应用线程访问到尚未整理完成的页，内核会把 fault 交给 ART 处理，ART 先把这一页整理到位，再把控制权交还给应用线程。这样做的目的，是把对象迁移和应用继续运行拆到页级别协调，而不是在每次引用读取时都依赖 Read Barrier。

CMC 的另一处变化，是主分配路径可以配合 `BumpPointerSpace` 这类更简单的线性分配结构。对性能分析来说，重点是把 Android 8.0-13 的 CC、Android 14 / 15 的 CMC 路径、Android 16 QPR2 之后的 Generational CMC 分开看。

[已验证: AOSP android-14.0.0_r1, art/runtime/gc/collector_type.h]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/collector/mark_compact.cc]
[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap.cc]

### Android 16 QPR2：官方对外明确 Generational CMC

Android 16 QPR2 的官方发布说明直接写到：ART now includes a Generational Concurrent Mark-Compact (CMC) Garbage Collector。这个版本分界会直接影响 GC 路线的写法。写 Android 16 QPR2 时，可以把 Generational CMC 当成正式能力来讨论；截至 2026-06-10，AOSP platform/art 仍没有 android-17.0.0_r1 tag，本节不把 Android 17 单独作为源码结论。写 Android 14 / 15 时，表述应收在 Mark Compact / CMC 路径本身。

这条时间线更适合记成：Android 8.0-13 主要看 CC，Android 14 / 15 看 UFFD 驱动的 CMC 路径，Android 16 QPR2 之后再谈 Generational CMC。也不要把 Android 8.0-14 的 generational CC 经验，原样套到 Android 16 QPR2 之后的 Generational CMC 上。两者都体现了优先回收年轻对象，但底层 collector 已经不是同一套实现。

Generational CMC 的分代策略配合 CMC 的压缩能力，在高刷新率环境和高计算负载场景下有潜力释放可观的 CPU 吞吐量。官方博客确认了 ART includes Generational CMC and reduces CPU/battery 的定性描述，但博客原文未给出量化 benchmark 数字。如需引用具体性能数据（如 PCMark 跑分、Young GC 延迟、能效百分比），必须补充可公开访问的一手测试报告（含设备型号、系统版本、负载场景和采样条件）。

[已验证: Android Developers Blog, Android 16 QPR2 is Released]


### Generational CMC 与传统 CC 的实现差异

Generational CMC 不只是把 CMC 加上了分代策略——它在几个关键实现点上与传统 CC（Concurrent Copying）有本质区别。

**读屏障的处理方式不同**。CC GC 使用 Baker read barrier（`kUseBakerReadBarrier`），在每次对象引用读取路径上插入屏障检查，无论 GC 是否在运行，这层开销始终存在。Generational CMC 利用 userfaultfd（UFFD）把对象迁移的同步问题从"每条引用读取"降到了"页级别"——只有当应用线程访问到正在迁移的页时才会触发 page fault，由 ART 处理完后恢复执行。两者都需要并发标记阶段的屏障配合，但 CMC 的 UFFD 页级屏障触发频率远低于 CC 的逐引用 Baker read barrier。

**内存开销不同**。CC GC 需要 from-space 和 to-space 两个空间交替使用，物理内存峰值接近堆大小的两倍。CMC 的压缩是在原地（in-place）通过 UFFD 协调完成的，不需要预留一整块拷贝目标空间。这对内存紧张的设备（如低 RAM 机型）更友好。

**分代策略的配置**。Generational CMC 的分代策略有几个关键参数：

- **`gUseUserfaultfd`**：由 `mark_compact.cc` 中 `ShouldUseUserfaultfd()` 静态初始化的全局常量（不是 `runtime.cc` 的局部开关），在 ART 启动时根据内核是否支持 `userfaultfd` 系统调用和 `MREMAP_DONTUNMAP` 来设置。如果内核不支持，CMC 路径不会被启用
- **`use_generational_gc`**：`Runtime::Init()` 中使用的变量名（不是 `use_generational_cmc`），由 `mark_compact.cc::ShouldUseGenerationalGC()` 判断是否启用分代策略。判断条件包括 `kUseBakerReadBarrier || gUseUserfaultfd` 以及命令行 GC 类型选项
- **硬件能力检查**：`ShouldUseUserfaultfd()` 在 `mark_compact.cc` 中检测 `userfaultfd` 系统调用和 `KernelSupportsUffd()`，`ShouldUseGenerationalGC()` 检查分代条件
- **年轻代大小**：由 `Heap` 内部的分代参数控制。[待验证：年轻代占堆比例的具体数值需补 AOSP commit/tag 锚点] 新分配的对象优先进入年轻代，Young GC 只扫描这部分空间

**分代策略与 Perfetto 观察的对应关系**。在 Generational CMC 下，Perfetto 中仍然可以区分 Young GC 和 Full GC，但 slice 名称可能与 CC 路径不同。CC 路径下 Young GC 的 slice 通常标记为 `ConcurrentCopying`（partial / sticky），CMC 路径下则标记为 `MarkCompact` 相关名称。分析时需要先确认设备使用的 collector 类型，再对应 slice 名称。

### 分代 GC：Young Generation 的快速回收

[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]

分代回收这件事，本身比底层 collector 更稳定。它依赖的判断很朴素：新分配对象大多活不久，先把回收工作集中在年轻对象上，通常能用更短的暂停时间拿到更高的回收收益。

在 Android 8.0-9 的 CC 路径里，分代回收还处于早期阶段；Android 10-14 的 CC 路径有了更成熟的 generational CC 实现，新对象先进入年轻工作集，Young GC 主要扫描这部分对象，暂停时间通常只有 1-3ms；只有年轻对象晋升、老年代压力上来，才会触发更重的 full-heap 回收。到了 Android 16 QPR2 之后，Generational CMC 取代了 generational CC 的角色——同样优先回收年轻对象，但底层 collector 从 CC 的 Baker read barrier + from/to-space 双缓冲换成了 UFFD + 原地压缩（见上方对比）。观察口径不变：Young GC 负责快速回收短命对象，Full GC 负责全局压缩。

在 Perfetto 中，仍然可以用相同的观察方式区分这两类活动：
- **Young / minor collection**：持续时间短、频率更高，通常出现在对象快速创建和销毁的场景
- **Full-heap collection / full GC**：持续时间更长，常和堆增长、老年代压力或内存泄漏一起出现
- **如果一个应用的 minor collection 已经频繁到每秒多次**，通常说明对象抖动已经开始影响前台体验

[图：Perfetto 中 Young GC vs Full GC 的典型表现对比]

## GC 对性能的影响：暂停、吞吐与 Stall

理解 GC 策略的演进后，还需要回答一个更实际的问题：GC 具体在哪些方面影响应用性能？

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

在 Perfetto 中要结合 GC slice、`HeapTaskDaemon` 活动和实际 trace 中可见的 GC counter 来估算 GC 的频率与耗时。

[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]

### ART FinalizerDaemon 与 ReferenceQueue 的锁边界

ART 的 FinalizerDaemon 线程负责处理对象的 `finalize()` 方法。GC 完成标记后，通过 `ReferenceQueue` 将待 finalize 对象传递给 FinalizerDaemon。这条路径依赖 `synchronized(lock)` 同步——`ReferenceQueue.enqueue()` 的入口和 `enqueuePending()` 的批处理循环（`MAX_ITERS=100`）都在同一个 object monitor 内执行。当 GC 频率高、FinalizerDaemon 处理压力大时，锁竞争会导致 `TimeoutException`，极端情况下引发 ANR。

Android 16 引入了 `ConcurrentMessageQueue`（无锁 Treiber 栈 + VarHandle 原子操作），但这条优化路径属于 `android.os` 层的 Handler/Looper 路径，与 ART 内部的 `ReferenceQueue` 是两条独立的调用链。源码级验证结论：

- ✅ `libcore ReferenceQueue.java` 仍使用 `private final Object lock`，所有核心方法（`enqueue`/`poll`/`remove`）都在 `synchronized(lock)` 内
- ✅ `ConcurrentMessageQueue` 的无锁 Treiber 架构仅用于 UI 消息分发，未接入 `ReferenceQueue`
- ✅ `reference_processor.cc` 的 `kAsyncReferenceQueueAdd = false` 未变

`ReferenceQueue` 是否会在后续 Android 版本中移除同步锁，需要等正式 tag 或 release note 确认。

在 Perfetto 中，如果看到 `FinalizerDaemon` 线程出现长时间的 `Object.wait()` 或 `ReferenceQueue` 相关的阻塞 slice，通常是锁竞争路径的表征。定位步骤：

1. 在 `HeapTaskDaemon` track 上确认 GC 频率和耗时
2. 在 `FinalizerDaemon` track 上查找 `Object.wait()` slice，观察等待时长
3. 对比 GC 完成时间与 `FinalizerDaemon` 处理时间——如果 GC 频繁但 FinalizerDaemon 处理跟不上，锁竞争就是瓶颈
4. 检查应用是否大量使用 `finalize()`（已废弃但仍存在于部分库），如果是，优先迁移到 `Cleaner` API

## 对象分配路径：从 TLAB 到 Full GC

了解对象在 ART 中的分配路径，有助于解释某些代码模式为什么会导致性能问题。

### TLAB 分配：最快路径

Android 8.0+ 的 CC GC 引入了 RegionTLAB（Thread Local Allocation Buffer）分配策略。每个应用线程从 `RegionSpace` 中获取自己专属的 TLAB——一块连续的内存缓冲区。线程在自己的 TLAB 中分配对象时，只需要移动一个 top 指针（bump pointer），无需任何同步操作：

```cpp
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

TLAB 分配的速度比 Android 7.0 快 70%，比 Dalvik 时代快约 18 倍。只要 TLAB 有空间，这就是 ART 对象分配的最快路径。

AOSP 源码路径：`art/runtime/gc/space/region_space.cc (AllocNewTlab)`、`kRegionSize = 256 * KB` 定义在 `region_space.h`
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

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/heap.cc TryToAllocate]

## ART Profile-Guided Compilation：让代码越跑越快

ART 的内存管理不仅仅涉及堆和 GC，还包括编译策略对内存的影响。ART 采用混合编译模式：解释执行、JIT（Just-In-Time）编译和 AOT（Ahead-Of-Time）编译三者结合。这个策略直接影响了应用的内存占用和运行时性能。

### 三种编译模式的协作

ART 的编译策略可以简化为以下流程：

1. **首次运行**：方法先被解释执行（最慢，但无需编译时间和空间）
2. **JIT 编译**：频繁执行的方法被 JIT 编译为机器码，存入 Code Cache（在内存中）
3. **Profile 收集**：ART 在运行过程中记录哪些方法被频繁执行，生成 Profile 文件
4. **AOT 编译**：设备空闲且充电时，编译守护进程（`dex2oat`）根据 Profile 对热点代码进行 AOT 编译，结果持久化到磁盘

这种混合策略的取舍是：把内存和编译时间优先花在高频代码路径上。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]

### Baseline Profiles：安装期优化要按版本拆开看

Baseline Profiles 的时间线要拆成两段，不能收在 Android 13 一个节点里。

对 Android 7-8.1（API 24-27），如果应用集成了 `androidx.profileinstaller`，Baseline Profile 会在首次启动时安装到设备上，ART 后续再结合空闲期编译继续优化。

对 Android 9（API 28）及以上，Google Play 在安装阶段就会使用 Baseline Profiles 优化 APK；如果后续还有 Cloud Profiles，可继续把真实用户的热点路径分发给后续安装者。版本线拆开看：Android 7-8.1 有 ProfileInstaller 驱动的 Baseline Profile，Android 9+ 进入 Baseline + Cloud Profile 的安装期 AOT 路径。不应该把整件事压到 Android 13 才出现。

官方文档给出的直接表述是，Baseline Profiles 可以让包含的代码路径从第一次启动开始提速约 30%。这类收益描述适合放在安装期和启动过程里理解，和 §8.7 的编译优化实践要保持同一口径。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]

### Cloud Profiles：聚合真实用户数据

Cloud Profiles 是 Google Play 在后台聚合的数据：当一批用户安装并使用了新版本应用后，Play 会收集他们的运行时 Profile，聚合后分发给后续安装同一版本的用户。

Cloud Profiles 解决了 Baseline Profiles 无法覆盖的问题：开发者可能不知道所有热点代码路径，但真实用户的使用数据可以揭示开发者未曾关注的性能瓶颈。

### 编译策略对内存的影响

AOT 编译后的机器码存储在 `.oat` 和 `.vdex` 文件中，运行时通过 `mmap` 映射到进程地址空间。这些文件的大小直接影响了应用的内存占用：

- **过度 AOT 编译**：如果 Profile 包含了太多方法，`.oat` 文件会很大，mmap 后占用大量虚拟地址空间
- **JIT Code Cache**：运行时 JIT 编译的代码存在内存中的 Code Cache 里，初始容量很小（`JitCodeCache::GetInitialCapacity()` 在 release 构建中约 64KB），运行中按需增长，上限默认 64MB（可由 `-Xjitcodecachesize` 或 runtime option 调整，定义在 `art/runtime/jit/jit_code_cache.h` 的 `kMaxCapacity`）。如果 Code Cache 满了，旧的编译结果会被淘汰，对应的方法回退到解释执行

在 Perfetto 中可以通过 `art_jit_*` 相关的事件来观察 JIT 编译活动。

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles]

### Android 15/16 的 16KB Page Size 对 ART 的影响


16KB page size 是 Android 15 开始支持的系统能力。在 ART 内存管理语境里，需要把 ART 直接受到的影响和系统级收益拆开。

对 ART 来说，页大小变化会影响 `mmap` 粒度、堆页管理和 native 库兼容性边界。它当然会反映到运行时内存行为，但官方页面公开的数字是整机测试结果，不是 ART 内部某个分配器的单独 benchmark。

官方文档当前给出的平均结果是：内存压力下的应用启动时间降低 3.16%，启动期功耗降低 4.56%，相机热启动快 4.48%，相机冷启动快 6.60%，开机时间改善 8%。这些数据更适合放在 §4.7《16KB Page Size 与 Android 性能》里展开。在 ART 内存管理语境里，如果讨论 16KB page 对 TLAB、Region 或 TLB miss 的具体影响，必须给出设备、版本和实验条件，不能把它直接写成 ART 的默认事实。

[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

## 在 Perfetto 中观察 ART GC

理解 GC 路径后，Perfetto 中的实际观察入口主要有三类。

### 关键 Track 和事件

在 Perfetto 的 UI 中，ART GC 的活动分布在几个关键位置：

- **GC 事件 slice**：ART 的 `GarbageCollector::Run()` 通过 `ScopedTrace` 产出 GC slice，名称如 `ConcurrentCopying GC`、`MarkCompact GC` 等。slice 所在 track 取决于执行线程——后台并发 GC 由 `HeapTaskDaemon` 线程执行，Foreground GC 则出现在触发 GC 的应用线程 track 上
- **GC 活动 counter**：Perfetto 中存在反映 GC 频率和吞吐量的 counter track，具体 track name 因 Android 版本和 GC 实现而异，需对照实际 trace 确认
- **`HeapTaskDaemon` 线程**：ART 的后台 GC 线程，Concurrent GC 的主要执行者。这个线程的活跃区间对应并发标记和拷贝/压缩的时间
- **`AllocObject` trace point**：当应用线程在分配对象时被阻塞（Allocation Stall），对应线程的 track 上会出现这个 slice

对于需要量化分析的场景，可以使用 Perfetto 的 SQL 视图。以下查询统计一段时间内各类型 GC 的次数和平均耗时：

```sql
-- 统计 GC 事件类型、次数和平均耗时（按线程名和 slice 名匹配）
SELECT slice.name AS gc_type, COUNT(*) AS count, ROUND(AVG(dur / 1e6), 2) AS avg_duration_ms
FROM slice
JOIN track ON slice.track_id = track.id
JOIN thread_track ON thread_track.id = track.id
JOIN thread ON thread_track.utid = thread.utid
WHERE (thread.name = 'HeapTaskDaemon' OR slice.name LIKE '%GC%')
  AND slice.name LIKE '%GC%'
  AND slice.dur > 0
GROUP BY gc_type
ORDER BY avg_duration_ms DESC;
```

> **注意**：GC slice 所在的 track name 就是线程名，因 Android 版本和 GC 实现而异。读者需打开自己的 trace，在线程列表中确认 `HeapTaskDaemon` 或目标应用线程的实际名称，再据此调整 SQL 中的 `thread.name` 过滤条件。

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

SQL 结果可以直接转成排查动作：Young GC 平均耗时超过 5ms 时，先排查对象抖动；Allocation Stall 频繁出现时，先看堆上限、峰值分配和大对象路径。

### 正常 vs 异常的 GC 模式

中等复杂度应用的常见基线可以这样看：
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

不应该这样做。`System.gc()` 会强制触发一次 Full GC，暂停时间比正常的 Young GC 长得多。ART 的 GC 是自适应的，会根据堆压力和分配情况决定回收时机。如果发现需要手动触发 GC 来"解决问题"，通常说明存在内存泄漏或对象抖动，应该从源头修复。

### 误区二：对象池总是能减少 GC 压力

对象池只在特定场景（如游戏中的子弹对象、消息队列的 Message）下有效。不加区分地使用对象池反而会增加 Old Generation 中的常驻对象，导致 Full GC 时需要扫描更多的存活对象。正确做法是先用 Trace 分析确认 GC 压力来源，再针对性地优化。

### 误区三：Android 的 GC 已经足够快了，不需要关注

虽然 ART 的 GC 比 Dalvik 时代快了很多，但在 120Hz 设备上，一帧只有 8.33ms。即使一次 GC 暂停只有 3ms，如果恰好发生在帧的关键路径上，也可能导致掉帧。特别是在 Compose 应用中，recomposition 可能产生大量临时对象——如果不注意优化，GC 仍然是卡顿的重要来源。

### 误区四：堆越大越好

ART 的堆大小受到系统限制（由 `ActivityManager.getMemoryClass()` 返回，通常 128-512MB）。更大的堆意味着 GC 需要扫描更多的对象，暂停时间会相应增长。此外，一个应用占用过多堆空间，会导致其他应用的可用内存减少，触发更频繁的 lmkd 进程回收。合理的内存使用比申请更大的堆更有价值。

[已验证: 官方文档, source.android.com/docs/core/runtime/gc-debug]

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
- Concurrent Mark-Compact / Mark Compact：`art/runtime/gc/collector/mark_compact.cc`
- RegionSpace（CC GC 的分配器）：`art/runtime/gc/space/region_space.cc`
- BumpPointerSpace（CMC GC 的分配器）：`art/runtime/gc/space/bump_pointer_space.cc`
- RosAlloc：`art/runtime/gc/allocator/rosalloc.cc`
- Image Space：`art/runtime/gc/space/image_space.cc`
- Large Object Space：`art/runtime/gc/space/large_object_space.cc`
- TLAB 分配：`art/runtime/gc/space/region_space.cc (AllocNewTlab)`
- Profile 管理：`art/runtime/jit/profile_saver.cc`

### 官方文档
- [Manage device memory | source.android.com](https://source.android.com/docs/core/runtime/gc-debug)
- [Baseline Profiles | developer.android.com](https://developer.android.com/topic/performance/baselineprofiles)
- [16KB Page Size | developer.android.com](https://developer.android.com/guide/practices/page-sizes)
- [Android 16 QPR2 is Released | Android Developers Blog](https://android-developers.googleblog.com/2025/12/android-16-qpr2-is-released.html)

### 素材来源
- [ART虚拟机内存分配原理浅析](https://cubox.pro/web/card/7169016886301033688)
- [ART虚拟机CMC GC算法核心实现介绍](https://cubox.pro/web/card/7072254330031571026)
- [【Android ART】Heap的内存布局](https://cubox.pro/web/card/7215366783438422022)
- [研究] ART 内存分配器演进（dlmalloc → RosAlloc → RegionTLAB）
- [研究] ART 分代 GC 架构（Young/Old Generation + Concurrent Copying）
- [研究] Android 15/16 的 16KB Page Size 对 ART 内存的影响


<!-- AIW-源码调研-2026-06-09 ·topic=ART GC碎片控制+并发压缩 -->

> ⚠️ 版本边界：android-17.0.0_r1 在 2026-06-10 **未发布**（AOSP tag 查询为空）。以下内容只基于 android-16.0.0_r1（API 36）一手源码；main 分支仅作目录对照，不作为 Android 17/API 37 正文结论，**不涉及 Android 18/API 38+**。

### 4.3.x Android 16 ART 碎片控制与并发压缩（一手源码补遗）

#### (a) RegionSpace区域级 UnevacFromSpace机制

`art/runtime/gc/space/region_space.h`枚举：

```cpp
enum RegionType : uint8_t {
 kRegionTypeAll, // All types.
 kRegionTypeFromSpace, // From-space. To be evacuated.
 kRegionTypeUnevacFromSpace, // Unevacuated from-space. Not to be evacuated.
 kRegionTypeToSpace, // To-space.
 kRegionTypeNone, // None.
};
```

`art/runtime/gc/space/region_space.cc`关键常量与决策函数：

```cpp
// If a region has live objects whose size is less than this percent
// value of the region size, evacuate the region.
static constexpr uint kEvacuateLivePercentThreshold =75U;

inline bool RegionSpace::Region::ShouldBeEvacuated(EvacMode evac_mode) {
 // The region should be evacuated if:
 // - the evacuation is forced (!large && `evac_mode == kEvacModeForceAll`); or
 // - the region was allocated after the start of the previous GC (newly allocated region); or
 // - !large and the live ratio is below threshold (`kEvacuateLivePercentThreshold`).
 ...
}
```

- 高占用（≥75%存活）region 在并发复制 GC周期被降级为 UnevacFromSpace，**避免反复搬迁**。
- `kCyclicRegionAllocation` 仅 debug模式开启，release模式关闭——Android内部 b/33795328（region级循环分配碎片）已通过 UnevacFromSpace + 单调区域分配策略抑制（`region_space.h`注释明确点名）。

#### (b) MarkCompact 三代模型 + userfaultfd

`art/runtime/gc/collector/mark_compact.cc`门控与状态字段：

```cpp
#ifdef ART_TARGET_ANDROID
bool ShouldUseGenerationalGC() {
 if (gUseUserfaultfd && !com::android::art::flags::use_generational_cmc()) {
 return false;
 }
 return GetBoolProperty(
 "persist.device_config.runtime_native_boot.use_generational_gc", true);
}
#else
bool ShouldUseGenerationalGC() { return true; }
#endif

MarkCompact::MarkCompact(Heap* heap)
 : ...
 young_gen_(false),
 use_generational_(heap->GetUseGenerational()),
 compacting_(false),
 ...
 black_dense_end_(moving_space_begin_),
 mid_gen_end_(moving_space_begin_), // young / mid / old 三代切分锚点
```

- 三代模型：bump-pointer space 被 `mid_gen_end_`切分为 `[begin_, mid_gen_end_)`（old/mid）与 `[mid_gen_end_, end_)`（young）。young 经过两次 GC晋升到 mid，mid 再晋升到 old。
- `YoungMarkCompact` 是 `MarkCompact` 的「薄包装」，通过翻转 `young_gen_`标志委托到父类 `RunPhases()`：

```cpp
void YoungMarkCompact::RunPhases() {
 DCHECK(!main_collector_->young_gen_);
 main_collector_->young_gen_ = true;
 main_collector_->RunPhases();
 main_collector_->young_gen_ = false;
}
```

- CMC 启用条件不能简化成 Linux ≥5.7 或 minor-fault。`android-16.0.0_r1` 的 `KernelSupportsUffd()` 先检查 `MREMAP_DONTUNMAP`（源码注释写明该能力在 Linux 5.13 引入并可 backport 到 GKI）和 userfaultfd SIGBUS；minor-fault 特性只用于 minor-fault mode。未满足条件时会回退到非 UFFD 路径，不能直接写成“低于 5.7 走传统 STW 压缩”。

#### (c) LargeObjectSpace不可移动 +碎片诊断

`art/runtime/gc/space/large_object_space.h`：

```cpp
bool CanMoveObjects() const override { return false; }
// LargeObjectSpaces don't have thread local state.
size_t RevokeThreadLocalBuffers(art::Thread*) override { return 0U; }
size_t RevokeAllThreadLocalBuffers() override { return 0U; }

bool LogFragmentationAllocFailure(std::ostream& os, size_t failed_alloc_bytes) override
 REQUIRES_SHARED(Locks::mutator_lock_);
```

- LOS 是 discontinuous + non-moving space，和 main moving space（`RegionSpace` / `BumpPointerSpace`）分离，不参与 CC/CMC 的移动压缩。
- `LogFragmentationAllocFailure` 在分配失败路径输出「最大连续可分配块」长度——APM工具可借此判断 OOM 是否由碎片化引起。
- LOS 不参与移动压缩；`kFreeList` 路径复用 `dlmalloc_space` 相关实现，`kMap` 路径则按对象 `mmap` / `munmap`，不能把两种实现都概括成“底层使用 dlmalloc”。

#### (d) CC vs CMC 取舍

`art/runtime/gc/heap.cc`：

```cpp
if (gUseReadBarrier) {
 CHECK_EQ(foreground_collector_type_, kCollectorTypeCC);
 CHECK_EQ(background_collector_type_, kCollectorTypeCCBackground);
} else if (background_collector_type_ != gc::kCollectorTypeHomogeneousSpaceCompact) {
 CHECK_EQ(IsMovingGc(foreground_collector_type_), IsMovingGc(background_collector_type_))
 << "Changing from " << foreground_collector_type_ << " to "
 << background_collector_type_ << " (or visa versa) is not supported.";
}
```

- `gUseReadBarrier == true` →走 CC。具体读屏障形态按 ART 构建配置区分 Baker read barrier / table-lookup read barrier，不能把所有设备写成“查 RB table”，也不能在缺少 benchmark 时给出纳秒级固定开销。
- `gUseReadBarrier == false && gUseUserfaultfd == true` →可走 CMC；实际还要满足 `ShouldUseUserfaultfd()` / `KernelSupportsUffd()`、`use_generational_cmc()` 与 device_config 等条件。
- CC 与 CMC 是互斥两条路径，不存在运行时热切换。

#### (e) 性能特征边界

本补遗不保留 Young GC / Full GC 暂停时间的固定数值。`mark_compact.cc` 中的常量只能说明实现阈值，不能推出跨设备的暂停耗时。若要比较 CC 与 CMC 的 pause / CPU / battery，应使用同一设备、同一系统版本、同一负载下的 Perfetto GC slice、ART GC histogram 或公开 benchmark。

