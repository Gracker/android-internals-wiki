---
title: "ART TLAB 与对象分配性能"
chapter: "4.16"
status: ready-for-review
drafted_date: "2026-06-27"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-27"
last_verified_against: "AOSP android-17.0.0_r1 (art/runtime/gc)"
confidence: medium
sources:
  - type: aosp
    path: "art/runtime/gc/heap-inl.h (AllocObjectWithAllocator)"
  - type: aosp
    path: "art/runtime/gc/space/region_space.h / region_space.cc"
  - type: aosp
    path: "art/runtime/gc/allocator/rosalloc.h / rosalloc.cc"
  - type: aosp
    path: "art/runtime/gc/space/large_object_space.h / large_object_space.cc"
  - type: official
    path: "developer.android.com/topic/performance/memory-overview"
  - type: aosp
    path: "art/runtime/thread.h (Thread::tlsPtr_.thread_local_pos)"
tags: [art, tlab, allocation, rosalloc, gc, memory, region-space]
related_chapters: ["4.3", "4.8", "4.14", "10.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构"
---

# 4.16 ART TLAB 与对象分配性能

`new` 看起来只创建了一个对象，ART 却要同时满足几项约束：选择与当前垃圾收集器匹配的空间、维护对象对齐和堆统计、发布已经初始化好的对象，并在空间不足时协调 GC。源码以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点，普通 Java 对象会从分配入口进入 TLAB、RosAlloc 或 Large Object Space（LOS）。

两条边界如下：

1. TLAB 的快，来自线程在自己持有的地址区间内移动游标；获取或扩展 TLAB 仍可能加锁。
2. “分配很快”不代表“可以忽略分配量”。对象存活时间、refill 频率、GC 回收效率和主线程等待时间共同决定用户能否感知到卡顿。

## 1. 从 `new` 到当前分配器

编译代码可通过 ART quick allocation entrypoint 分配对象；解释执行、反射和数组创建也有各自入口。完成类状态、对象大小等必要检查后，这些入口会进入 `Class::AllocObject()` 和 `Heap::AllocObjectWithAllocator()` 一带。普通对象最终使用哪种分配器，由当前 collector、是否启用 TLAB、对象类型和对象大小共同决定。

### 1.1 Android 17 的 collector 与默认分配器

`Heap::ChangeCollector()` 在切换 collector 时重建 `gc_plan_`，并选择默认分配器：

| Collector | 启用 TLAB | 未启用 TLAB | `gc_plan_` |
|---|---|---|---|
| Concurrent Copying（CC） | `kAllocatorTypeRegionTLAB` | `kAllocatorTypeRegion` | 分代配置先放入 Sticky，最终放入 Full |
| Concurrent Mark-Compact（CMC） | `kAllocatorTypeTLAB` | `kAllocatorTypeBumpPointer` | 分代配置先放入 Sticky，最终放入 Full |
| Semi-Space（SS） | `kAllocatorTypeTLAB` | `kAllocatorTypeBumpPointer` | Full |
| Mark-Sweep / Concurrent Mark-Sweep | `kAllocatorTypeRosAlloc` | 编译时关闭 RosAlloc 才选 dlmalloc | Sticky、Partial、Full |

这里有两个容易混淆的名字：

- `kAllocatorTypeTLAB` 表示 **BumpPointerSpace 内的 TLAB**，CMC 和 SS 可选用它。
- `kAllocatorTypeRegionTLAB` 表示 **RegionSpace 的一段内存作为 TLAB**，CC 可选用它，也是枚举注释所说的多数小对象默认分配器。

`kAllocatorTypeBumpPointer` 与 `kAllocatorTypeRegion` 则是相应空间里的全局 CAS bump-pointer 分配。CMC 的移动空间是 `BumpPointerSpace`，不能把它描述成“从 RegionSpace 取得 young region”。

这张表描述源码提供的选择规则，不保证所有设备都采用同一 collector。运行时参数、产品配置和构建选项仍会影响结果。

### 1.2 大对象会提前分流

在常规分配器尝试分配前，`Heap::ShouldAllocLargeObject()` 检查：

```cpp
byte_count >= large_object_threshold_ &&
    (klass->IsPrimitiveArray() || klass->IsStringClass())
```

Android 17 的默认和最小 `large_object_threshold_` 都是 12KB。达到阈值仍不够，类还必须是基本类型数组或 `String`；一个很大的普通对象不会仅凭大小自动进入 LOS。

LOS 分配失败后，`AllocObjectWithAllocator()` 会清除这次失败留下的异常，再关闭大对象检查，尝试当前普通空间。这项回退是为了应对 LOS 虚拟地址碎片等情况，不能据一次 LOS 失败直接判断进程已经没有可用堆空间。

## 2. TLAB 的线程本地状态

Android 17 在 `Thread::tlsPtr_` 中保存 TLAB 状态。理解下面四个指针就能读懂快慢路径：

| 字段 | 含义 |
|---|---|
| `thread_local_start` | 当前 TLAB 的起点，用于统计已经使用的范围 |
| `thread_local_pos` | 下一次分配的位置 |
| `thread_local_end` | 当前已经开放给线程的末端 |
| `thread_local_limit` | 该 TLAB 最多可扩展到的位置，满足 `limit >= end` |

另有 `thread_local_objects` 记录该 TLAB 已分配的对象数。源码中的两个容量函数含义不同：

- `TlabSize()` 返回 `end - pos`，也就是当前可直接使用的字节数。
- `TlabRemainingCapacity()` 返回 `limit - pos`，还包括尚未开放、但可以扩展进来的容量。

因此，“当前 TLAB 用完”不等于“它所属的内存范围完全用完”。如果 `pos` 到 `limit` 仍有空间，ART 可以先扩展 `end`，再完成分配。

## 3. TLAB fast path 做了什么

`Heap::AllocObjectWithAllocator()` 对两种 TLAB 分配器采用相同的基本过程：

1. 按 `BumpPointerSpace::kAlignment` 对齐对象大小；Android 对象对齐为 8 字节。
2. 如果对齐后的大小不超过 `TlabSize()`，调用 `Thread::AllocTlab()`。
3. `AllocTlab()` 增加本地对象计数，返回旧 `pos`，再把 `pos` 向前移动。
4. 写入对象的 class，执行读屏障状态断言（启用 Baker read barrier 时）、`pre_fence_visitor` 和构造发布 fence。

第 3 步只写当前线程的 TLS，不需要共享分配器锁，也不需要对全局游标做 CAS。这是 TLAB 在高频小对象分配中成本较低的核心原因。

### 3.1 quick entrypoint 还有一条更窄的直接路径

Android 17 的 `quick_alloc_entrypoints.cc` 只在以下条件同时满足时，直接在 quick entrypoint 中操作 TLAB：

- entrypoint 未被 instrumentation；
- 当前 allocator 是 `kAllocatorTypeTLAB`，也就是 BumpPointerSpace TLAB；
- 类已经“可见地初始化”，对象大小固定，且对象不可 finalizable；
- 对象大小严格小于 `TlabSize()`。

`kAllocatorTypeRegionTLAB` 没有使用这段特定的 quick 代码，但进入共享的 `AllocObjectWithAllocator()` 后，仍可在自己的 TLAB 中完成无共享锁分配。两者不能只看“TLAB”这个名字就合并成同一条入口路径。

### 3.2 instrumentation 会改变观察对象

启用分配监听或 profiler 后，ART 可能发送 pre-allocation 事件。监听器甚至可以调整待分配大小；entrypoint 的 instrumentation 状态在挂起点发生变化时，分配还要重新开始。Java heap sampler 也会通过 `NextTlabSize()` 影响 refill 或扩展尺寸，并在需要时调用 `ReportTlabAllocation()`。

所以，profiler 记录的是受观测条件影响的运行。它适合找热点、比较数量级和调用栈，不适合把一次采样结果解释为无观测时每次分配的固定耗时。

## 4. partial TLAB：16KB、32KB 与 256KB 各指什么

Android 17 的三个常量经常被误读：

| 常量 | 数值 | 用途 |
|---|---:|---|
| `Heap::kPartialTlabSize` | 16KB | partial TLAB 的默认扩展或申请参考值 |
| `Heap::kDefaultTLABSize` | 32KB | BumpPointerSpace 新 TLAB 的额外容量参考值 |
| `RegionSpace::kRegionSize` | 256KB | 一个 Region 的大小，也是单个 RegionTLAB 可归属的上限范围 |

TLAB 的当前开放区间并不固定为 256KB。`Heap::kUsePartialTlabs` 在该版本为 `true`，refill 前还会先尝试扩展已有 TLAB。

### 4.1 先扩展当前 TLAB

当对象大于当前 `TlabSize()`，但不大于 `TlabRemainingCapacity()` 时，`AllocWithNewTLAB()` 不必换 TLAB。它计算至少能容纳对象的扩展量，并以 `kPartialTlabSize` 为参考向 heap sampler 请求下一段大小，再增加 `thread_local_end`。

这一步说明 `end` 与 `limit` 必须分开理解：`end` 控制当前可直接分配的范围，`limit` 保留以后扩展的余量。

### 4.2 BumpPointerSpace TLAB refill

对 `kAllocatorTypeTLAB`，新 TLAB 大致以“本次对象大小 + 32KB 参考余量”为基础，并考虑运行时页大小和 heap sampler 的调整。`BumpPointerSpace::AllocNewTlab()` 获取空间自己的锁，撤销旧 TLAB，分配新块，然后把 `start`、`end`、`limit` 设为新块的边界。

32KB 是 sizing 的默认输入，不是每次 refill 的固定返回值。

### 4.3 RegionSpace TLAB refill

对 `kAllocatorTypeRegionTLAB`：

- 对象不超过 256KB 时，ART 以 16KB 为默认参考计算本次要开放的 partial TLAB 大小。
- `RegionSpace::AllocNewTlab()` 可以复用 `partial_tlabs_` 中容量合适的剩余段，也可以分配新 Region。
- 设置线程状态时，`end` 是本次开放位置，`limit` 可以指向 Region 末端。后续分配可继续扩展 `end`。
- 撤销 TLAB 时，如果 `pos` 到 Region 末端至少还剩 16KB，RegionSpace 会把这段余量放回 `partial_tlabs_` 供后续复用。
- TLAB refill 失败时，ART 会尝试 Region 的非 TLAB 分配；对象大于 256KB 时也直接走 Region 的大块分配。

这些操作受 `region_lock_` 保护。只有已经取得 TLAB 后的游标分配不需要这把共享锁。

## 5. RosAlloc：线程本地 run 与按 size bracket 加锁

Mark-Sweep 系列 collector 在 Android 17 源码中仍选择 RosAlloc。它把小对象放入按大小划分的 run，再把 run 切成等大的 slot。

RosAlloc 一共有 42 个 size bracket：

- 前 16 个是线程本地 bracket，覆盖 8～128 字节，步长 8 字节；
- 之后的常规 bracket 覆盖 144～512 字节，步长 16 字节；
- 最终还有 1KB 和 2KB 两档；
- 大于 2KB 的 RosAlloc 请求按页粒度处理。

不超过 128 字节时，线程可先从自己的 thread-local run 取空闲 slot；当前 run 无法满足请求时，再进入补充 run 的代码。共享 run、`current_runs_` 与 `non_full_runs_` 由 **每个 size bracket 一把** `size_bracket_locks_[i]` 保护。页映射、空闲页集合和 footprint 等状态另有全局 `lock_`，批量释放还有 `bulk_free_lock_`。

因此，下面两种说法都不准确：

- “RosAlloc 每次小对象分配都获取全局锁”忽略了 thread-local run。
- “每个 run 都有独立锁”把锁的归属层级写错了；源码按 size bracket 配锁。

## 6. Large Object Space 的两种实现

Android 17 保留两种 LOS：

| 实现 | 地址空间组织 | 分配与释放特点 |
|---|---|---|
| `LargeObjectMapSpace` | 每个对象拥有一份匿名 `MemMap`，map 记录所有存活对象 | 分配先 `MemMap::MapAnonymous()`，再持有 LOS 锁登记；从 map 删除对象时，其 `MemMap` 随之释放 |
| `FreeListSpace` | 一块预留的连续 `MemMap`，旁边有 `AllocationInfo` 元数据 | `free_blocks_` 按 best-fit 查找，释放时可 `madvise`，并与相邻空闲块合并 |

两种实现的元数据操作都受 LOS 的 `lock_` 保护。默认类型取决于编译条件：

```cpp
USE_ART_LOW_4G_ALLOCATOR
    ? LargeObjectSpaceType::kFreeList
    : LargeObjectSpaceType::kMap
```

不能只依据 Android 版本断言某个设备一定采用 Map 或 FreeList。

LOS 中的死亡对象由 GC 标记、清理，但两个实现的地址空间行为不同：Map 版本释放独立映射，FreeList 版本在预留区间内回收并合并块。排查大数组或大字符串问题时，应先确认进程使用的实现、对象大小分布和分配调用栈，再讨论碎片或系统调用成本。

## 7. 分配失败后的 GC slow path

`AllocateInternalWithGc()` 不是固定执行“Young GC → Full GC”。Android 17 的处理顺序更细：

1. 如果已有 GC 正在运行，等待它结束并重试分配。
2. 进程关停阶段若 GC 已禁用，尝试 NonMoving allocator。
3. 若 `next_gc_type_` 尚未尝试，按 `GrowForUtilization()` 选出的类型执行一次 GC；只有回收结果达到源码设定的有效阈值时才重试。
4. 仍失败时，使用 `gc_plan_.back()` 执行最完整的全堆收集，并清除 SoftReference。若回收足够但内存被其他线程抢先使用，源码允许有限条件下继续尝试。
5. 无法满足请求后抛出 `OutOfMemoryError`。

RosAlloc 或 dlmalloc 还可能在 OOM 前尝试 homogeneous space compaction，是否启用取决于相应配置。分配失败可能来自堆已满、碎片、请求过大或线程间竞争，不能只用“GC 没有及时执行”解释。

### 7.1 堆阈值要结合运行时配置

Android 17 `Heap` 类给出的默认值包括：

- `kDefaultMinFree = 8MB`
- `kDefaultMaxFree = 32MB`
- `kDefaultTargetUtilization = 0.6`
- `kDefaultInitialSize = 2MB`
- `kDefaultMaximumSize = 256MB`

这些是源码默认值，设备资源、runtime 参数和产品配置可以覆盖它们。并发 GC 的默认起点也不是简单的固定利用率：`SetDefaultConcurrentStartBytesLocked()` 以当前 `target_footprint` 的四分之一作为 reserve，将剩余部分作为 `concurrent_start_bytes_`。

阅读现场数据时，应记录设备、构建、collector、堆上限和进程状态。把 `min_free`、`max_free` 写成固定百分比，或者假设所有应用都使用 256MB 上限，都会误导结论。

## 8. 怎样观察分配压力

### 8.1 系统 trace 能可靠看到什么

Android 17 源码中可确认的信号包括：

- 分配线程等待 GC 时的 `GC: Wait For Completion <cause>` slice；
- `GarbageCollector::Run()` 建立的 `<cause> <collector name> GC` slice；
- `Heap size (KB)` counter；
- GC 结束时的 `freed_normal_object_bytes`、`freed_large_object_bytes` 和 `freed_bytes` 指标；
- 线程在等待 GC 时的调度状态和被阻塞时长。

常规 TLAB 每对象分配和 `RegionSpace::AllocNewTlab()` 并没有稳定的 `AllocObject`、`AllocNewTlab` atrace slice。不要编写依赖这些假设名称的 SQL，也不要把“trace 中没有分配 slice”理解为没有对象分配。

系统 trace 适合回答以下问题：

- 主线程是否因 GC 等待而错过帧期限；
- GC 发生的时间、类型和回收量；
- GC 前后的堆规模；
- 等待期间 CPU 是否忙于 GC，还是线程被其他资源拖住。

### 8.2 Android Studio allocation recording

Android Studio Memory Profiler 可对 debuggable 应用记录 Java/Kotlin 分配，查看对象类型、分配字节数、线程、时间和调用栈。Full 模式记录更完整，Sampled 模式开销较低。使用它时先框定一次可复现操作，再比较热点调用栈，避免长时间无边界录制。

它回答的是“谁在分配、分配了多少”，而系统 trace 更适合回答“这段分配是否引发 GC 等待并影响帧”。两类证据配合使用，比从单一曲线猜测 TLAB refill 更可靠。

### 8.3 Perfetto ART Allocation Profiling

Android 12 及以上可用 Perfetto 的 ART Allocation Profiling。命令行抓取可按官方文档把 heap 指定为 `com.android.art`：

```text
tools/heap_profile -n <process_name> --heaps com.android.art
```

这类 profile 给出采样到的分配调用栈和分配量，适合观察 churn。它不跟踪每个对象的删除时刻，也不能替代保留关系分析。若要查看谁仍然引用某对象，应使用 Android 11 及以上支持的 ART heap dump；heap dump 展示 retention graph，不提供原始分配调用栈。

profileable/debuggable 限制、采样间隔和目标进程权限会影响能否采集。采样还会改变 TLAB sizing，跨组比较时要保持配置一致。

## 9. 面向应用代码的优化顺序

### 9.1 先用调用栈确认热分配点

建议按以下顺序排查：

1. 固定场景、设备、构建类型和录制时长。
2. 用 allocation recording 或 ART allocation profile 找到分配字节数、对象数和调用栈都靠前的位置。
3. 在 system trace 中检查同一时段是否有 GC、`GC: Wait For Completion` 和帧超时。
4. 区分高频小对象、大数组/字符串、意外存活和跨线程突发分配。
5. 改动后重复同样操作，比较对象数、字节数、GC 等待和帧表现。

仅凭一次 GC 或一次 TLAB refill 无法证明代码存在问题。持续高分配率与可见等待、帧超时或内存增长同时出现时，优化才有清晰目标。

### 9.2 谨慎使用对象池

有界对象池可以减少昂贵且高频对象的重复创建，但也会延长对象存活时间，增加重置状态、线程安全和容量管理的复杂度。适合池化的对象通常同时满足：

- 创建或初始化成本已经由 profile 证明较高；
- 使用频率高，生命周期短，峰值并发量可估算；
- 对象状态能够完整清理；
- 池容量有明确上限。

普通小对象的 TLAB 分配已经很便宜。为了避开一次游标更新而维护复杂池，可能把短命对象变成长期保留对象。`Message.obtain()` 这类平台实践有明确使用模式，不能据此推导“所有临时对象都应该池化”。

### 9.3 Compose 也应以测量结果为准

重组期间可能出现状态记录、集合或 lambda 等分配，但具体热点取决于代码和 Compose 版本。用 allocation recording 覆盖一次明确的重组场景，先找到调用栈；`remember` 应按组合语义保存需要跨重组保留的值，不能只为减少分配而随意延长对象生命周期。

平台 ART 的 TLAB 机制也不能证明某个 Compose API 在 Android 17 自动“平滑分配”。UI 框架调度与 ART 分配属于不同层次，需要分别查对应版本源码和性能数据。

## 10. 版本阅读原则

行为结论锚定 `android-17.0.0_r1`。阅读旧版本资料时，至少重新确认：

- collector 与 allocator 的对应关系；
- `use_tlab_`、分代 GC 和构建选项；
- partial TLAB 常量与 Region 大小；
- LOS threshold 和默认 LOS 类型；
- profiler 是否会改变入口或采样策略。

可以保留 collector 和 allocator 的历史演进，但不要把旧版本的默认配置套到 Android 17，也不要从 Android 17 的实现反推所有旧设备。

## 小结

- Android 17 区分 BumpPointerSpace 的 `kAllocatorTypeTLAB` 与 RegionSpace 的 `kAllocatorTypeRegionTLAB`。
- TLAB fast path 依靠线程本地 `pos` 游标；refill、扩展和撤销仍会进入空间级同步。
- partial TLAB 默认参考 16KB，BumpPointer TLAB 参考 32KB，Region 大小为 256KB；三者含义不同。
- RosAlloc 对小对象提供 thread-local run，共享状态按 size bracket 加锁。
- LOS 只接收达到阈值的基本类型数组或 `String`，Map 与 FreeList 两种实现的地址空间行为不同。
- 分配 slow path 会等待已有 GC、执行 `next_gc_type_`，必要时再全堆收集并清除 SoftReference。
- 分配热点用 allocation profile 查调用栈，GC 等待和帧影响用 system trace 判断。

## 源码与工具索引

- [AllocatorType：两种 TLAB 与 Region 分配器](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/allocator_type.h)
- [Heap::AllocObjectWithAllocator 与 ShouldAllocLargeObject](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [Heap：collector 选择、GC slow path 与 TLAB refill](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [Thread：TLAB 指针与容量语义](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/thread.h)
- [RegionSpace：partial TLAB 复用与撤销](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/space/region_space.cc)
- [RosAlloc：size bracket、run 与锁](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/allocator/rosalloc.h)
- [LargeObjectSpace：Map 与 FreeList 实现](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/space/large_object_space.cc)
- [Android Studio：记录 Java/Kotlin 分配](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [Perfetto：ART allocation profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [Perfetto：ART heap dump](https://perfetto.dev/docs/data-sources/java-heap-profiler)
