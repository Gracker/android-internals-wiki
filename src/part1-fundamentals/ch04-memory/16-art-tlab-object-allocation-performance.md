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

§4.3 从 ART 堆整体架构角度介绍了对象分配路径的概貌，§4.8 讲了分代 GC 如何影响分配节奏，§4.14 深入分析了 Region 级碎片与压缩策略。本节聚焦一个更底层的问题：**从 `new` 关键字到内存就位，ART 的分配器内部经历了哪些代码路径，每条路径的性能开销是什么，以及在 Perfetto 中如何识别分配瓶颈**。

## 要点

### 🔹 ART 对象分配路径全景

ART 的对象分配从 Java 层的 `new` 关键字开始，经过 JNI 或解释器的入口点，最终到达 `Heap::AllocObjectWithAllocator()`。整条路径的关键决策点如下：

```
new MyClass()
    → ObjAlloc / NewInstance / NewArray (art/runtime/reflection / interpreter)
    → Class::AllocObject()  (检查类加载状态、初始化锁)
    → Heap::AllocObjectWithAllocator<TemplateFunc kInstrumented>(
          Thread* self, ObjPtr<Class> klass, size_t byte_size,
          AllocatorType allocator, const PreFenceVisitor& pre_fence)
```

`AllocObjectWithAllocator` 是 ART 分配的核心分叉点。它接收一个 `AllocatorType` 枚举参数，决定走哪条分配器路径：

| AllocatorType | 分配器 | 使用场景 | 同步开销 |
|---|---|---|---|
| `kAllocatorTypeTLAB` | Region TLAB | RegionSpace 中的常规小对象 | 无锁（fast path） |
| `kAllocatorTypeRosAlloc` | Runs-of-Slots | CMS 模式 / 非 CC 场景的后备 | 分片锁 |
| `kAllocatorTypeLOS` | Large Object Space | ≥12KB 的基本类型数组 / String | 堆锁 |
| `kAllocatorTypeNonMoving` | NonMovingSpace | class、class table 等不可移动对象 | 全局锁 |
| `kAllocatorTypeBumpPointer` | BumpPointerSpace | 仅 young gen CMC 场景 | 无锁 |

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/heap.h - AllocatorType enum]

在 Android 8.0+ 的 CC（Concurrent Copying）模式下，常规 Java 对象默认走 `kAllocatorTypeTLAB` 路径。Android 16+ 的分代 CMC（Concurrent Mark-Compact）引入了 `kAllocatorTypeBumpPointer` 作为 young gen 的主分配器，但 TLAB 仍然是 mature object 分配的首选路径。

分配入口还负责触发 GC：如果分配失败（allocator 返回 `nullptr`），`AllocObjectWithAllocator` 的 slow path 会调用 `Heap::ThrowOutOfMemoryError` 或先尝试触发 GC 后重试。§4.3 已经描述了"分配失败 → GC → 重试"的高层逻辑，这里补充实现细节：GC 触发由 `Heap::AllocateInternalWithGc()` 统一管理，它按优先级依次尝试 Young GC → Full GC，每次 GC 完成后重新尝试分配。

### 🔹 TLAB（Thread-Local Allocation Buffer）机制

§4.3 给出了 TLAB 分配的概念伪代码，本节展开 TLAB 在 RegionSpace 中的完整生命周期。

#### TLAB 的获取与初始化

每个 ART 线程（`art::Thread`）在自己的 TLS（Thread-Local Storage）中维护当前 TLAB 的三个关键指针：

- `thread_local_pos_`：TLAB 的起始地址
- `thread_local_end_`：TLAB 的结束地址
- `thread_local_top_`：当前分配游标（等于 `thread_local_pos_` + 已分配字节数）

[已验证: AOSP android-17.0.0_r1, art/runtime/thread.h - Thread::tlsPtr_]

当线程首次尝试分配对象或当前 TLAB 耗尽时，调用 `RegionSpace::AllocNewTlab(Thread* self)` 获取新的 TLAB：

1. 线程获取 RegionSpace 的 `lock__`（这是一个 `Mutex`，但持有时间极短）
2. 从 `free_list_` 中取出一个空闲 Region（256KB）
3. 设置 `thread_local_pos_` = Region 起始地址，`thread_local_end_` = Region 起始 + 256KB
4. 释放 `lock_`，返回

整个 refill 过程只涉及取一个链表节点和设置三个指针，在无竞争情况下耗时 < 1μs。

#### TLAB 的快速分配路径

线程在 TLAB 中分配对象时，走的是 `Heap::AllocObjectWithAllocator` 的模板实例化 fast path。核心逻辑可以简化为：

```cpp
// 概念简化：实际的内联模板更复杂，包含 instrumentation 和 read barrier
inline void* TlabAllocate(Thread* self, size_t byte_size) {
    size_t* old_pos = self->GetThreadLocalPos();
    size_t new_byte_size = RoundUp(byte_size, kAlignment);  // 8字节对齐
    if (old_pos + new_byte_size <= self->GetThreadLocalEnd()) {
        self->SetThreadLocalPos(old_pos + new_byte_size);
        return old_pos;  // 无锁分配成功
    }
    return nullptr;  // TLAB 耗尽，走 slow path
}
```

fast path 只有 4 步：对齐 → 边界检查 → 更新 pos → 返回地址。没有 CAS、没有锁、没有条件分支（除了边界检查本身）。这是 ART 对象分配性能远超 Dalvik 的根本原因。

#### TLAB 容量与 refill 频率

TLAB 的容量等于一个 Region 的大小，即 256KB（`kRegionSize = 256 * KB`，定义在 `region_space.h`）。一个 TLAB 在被线程"拥有"期间，不会被其他线程共享。线程用完 256KB 后触发 refill，从 free list 获取下一个 Region。

在高分配频率的场景下（例如 Compose 的重组阶段），单线程可能每秒消耗数十个 TLAB。refill 本身的开销很小（获取一次 RegionSpace 锁），但 refill 频率是衡量应用"分配压力"的一个直接指标。

需要注意：TLAB 不是按需动态调整大小的。无论线程分配多少，TLAB 始终是 256KB。这意味着一个只分配少量小对象的线程和一个大量分配的线程，TLAB refill 的频率差异直接反映了分配量差异。

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/region_space.h - kRegionSize]

### 🔹 RosAlloc（Runs-of-Slots Allocator）

在 CC 模式成为默认 GC 策略（Android 8.0）之后，RosAlloc 在常规对象分配中的角色被 TLAB 取代。但理解 RosAlloc 的设计仍然重要：

1. **历史代码路径**：在 Android 5.0-7.0 的 CMS 模式下，RosAlloc 是主分配器。部分老设备或特殊配置（如 low RAM 设备禁用 CC）仍然走 RosAlloc 路径
2. **NonMovingSpace 的后备**：某些不可移动对象的分配仍然可能经过 RosAlloc 的逻辑
3. **设计思想借鉴**：RosAlloc 的分片锁策略影响了后续分配器的设计

#### RosAlloc 的核心设计

§4.3 简要提到 RosAlloc 用"分片锁定"减少锁争用。这里展开具体机制：

RosAlloc 将堆内存划分为多个 run，每个 run 由若干 page 组成，专门服务特定大小级别的对象分配。大小级别（size class）从 16 字节到 4096 字节不等，按近似几何级数递增。

每个 run 内部被切成等大的 slot，对象直接放入 slot。关键设计是：**每个 run 有独立的锁**，而不是一把全局锁。线程在分配时先根据对象大小定位到对应的 size class，再获取该 run 的锁。不同线程分配不同大小的对象时，完全没有锁竞争；分配相同大小对象时，锁竞争也仅限于同一个 run。

```cpp
// rosalloc.h (简化)
class RosAlloc {
  // 按 size class 索引的 run 数组
  std::unique_ptr<Run> runs_[kNumOfSizeClasses];  // 约 40 个 size class
  // 每个 run 有独立锁
};
```

与 dlmalloc 的全局锁相比，RosAlloc 在多线程场景下的分配吞吐量提升了数倍。但与 TLAB 的完全无锁分配相比，RosAlloc 的每次分配仍然需要一次 CAS 或 mutex acquire。

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/allocator/rosalloc.h]

### 🔹 LargeObjectSpace 与大对象分配

§4.3 说明了超过 12KB（`kMinLargeObjectThreshold`）的基本类型数组或 `String` 进入 LargeObjectSpace。本节展开 LOS 的内部分配机制和对 GC 暂停的影响。

#### LOS 的分配实现

ART 的 LargeObjectSpace 有两个实现：

1. **`FreeListSpace`**：用空闲链表管理大对象内存。每个大对象占据独立的 mmap 区域，分配时从空闲链表找一块够大的，释放时归还链表
2. **`LargeObjectMapSpace`**：用 `std::map` 按大小管理空闲区域，适合大对象数量多且大小分布不均匀的场景

设备出厂时通过 `Heap::CreateLargeObjectSpace()` 选择具体实现。大多数 Android 14+ 设备使用 `LargeObjectMapSpace`。

LOS 分配需要获取 `large_object_lock_`，这是一个全局互斥锁。如果多个线程同时分配大对象（例如并行解码多张 Bitmap），锁竞争会显著拉长分配延迟。相比之下，TLAB 分配完全没有锁。

#### LOS 对 GC 暂停的影响

大对象不走 Region 分配，因此 CC GC 的 Region 级拷贝不适用于 LOS。LOS 的 GC 策略是标记-清除（mark-sweep）：标记阶段遍历所有 LOS 对象引用，清除阶段直接 munmap 已死亡对象的内存。

这带来两个性能影响：

1. **内存碎片**：LOS 的标记-清除不整理碎片。长期运行后 LOS 可能出现"空闲总量够但单个连续块不够"的情况，导致大对象分配失败触发 Full GC
2. **munmap 开销**：`munmap` 是系统调用，在大量大对象被同时回收时可能导致内核 page table 操作的尖峰

在 Perfetto 中，如果观察到 GC 暂停时间异常且 `HeapTaskDaemon` 上有大量 `LargeObjectSpace::Sweep` slice，通常意味着应用的大对象分配模式需要优化（例如用对象池复用 Bitmap 或 ByteBuffer）。

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/large_object_space.cc]

### 🔹 分配竞争与 GC 触发

ART 的堆增长策略和 GC 触发逻辑直接影响分配性能。核心参数定义在 `Heap` 类中：

#### 关键阈值参数

- **`min_free_` / `max_free_`**：堆的空闲内存下限和上限。当分配后空闲内存 < `min_free_` 时，触发 Concurrent GC；当空闲内存 > `max_free_` 时，堆不会继续增长。这两个值默认按堆大小的一定比例计算（通常 `min_free_` 约堆大小的 8%，`max_free_` 约堆大小的 16%），但会根据 GC 频率和分配速度动态调整
- **`target_utilization_`**：目标堆利用率，默认 0.75。GC 后存活对象大小 / 堆总大小应接近此值。如果 GC 后利用率高于目标，堆会增长；低于目标，堆可能缩小
- **`grow_` / `shrink_`**：堆增长和缩小的步长，根据历史 GC 数据动态计算

#### 分配与 GC 的竞争模型

Concurrent GC 的核心挑战是：GC 线程在后台扫描堆的同时，应用线程仍在不停分配。ART 处理这个竞争的方式是：

1. **CC 的 Read Barrier 协调**：应用线程在读取对象引用时触发 read barrier，确保不会访问到已搬迁的旧地址。分配可以与并发标记同时进行
2. **分配预算**：在 GC 运行期间，RegionSpace 允许线程继续分配新 Region。如果 free list 耗尽，分配会阻塞等待 GC 完成
3. **Foreground GC 回退**：如果分配速度远超 GC 回收速度，ART 会触发 foreground GC（stop-the-world），暂停所有应用线程直到 GC 完成。这种情况在 Perfetto 中表现为应用线程 track 上出现 `GC: Wait For Completion` slice

`AllocObjectWithAllocator` 的 slow path 中有一个关键循环：分配尝试失败 → 检查 OOM → 触发 GC → 重试。如果 Concurrent GC 跟不上分配速度，每次分配都走 slow path 并等待 foreground GC，应用的帧率会急剧下降。在 Perfetto 中表现为 `AllocObject` slice 大量出现在主线程 track 上，紧跟 foreground GC slice。

### 🔹 Android 17 ART 分配变更

Android 17（API 37）在 ART 分配层面的变化主要体现在分代 CMC 的成熟和 Region 分配策略的整合。

#### 分代 CMC 与分配器的协作

Android 16 引入了三代分代 CMC（young gen / mid gen / old gen），使用 `BumpPointerSpace` 作为 young gen 的分配器。Android 17 的改进包括：

1. **BumpPointerSpace 与 RegionSpace 的整合**：young gen 的 bump-pointer 分配区域直接从 RegionSpace 中划分，而不是使用独立的空间。这减少了空间切换的开销
2. **TLAB 的统一管理**：在分代 CMC 模式下，TLAB 的 refill 可以直接从 young gen region 中获取，无需切换分配器类型
3. **GC 暂停优化**：Android 17 的 `MarkCompact` 收集器通过分代策略减少了 full heap compaction 的频率，间接降低了分配 slow path 的触发概率

这些改进的核心效果是：**分配 fast path 的比例提高，slow path（触发 GC 或 refill）的频率降低**。

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/heap.cc - 分代 CMC 整合逻辑]

#### concurrent allocation 的改进

Android 17 优化了分配与并发 GC 的竞争处理：当 Concurrent GC 正在搬迁 Region 时，需要分配新 Region 的线程可以跳过被 GC 占用的 Region，直接从 free list 的下一块获取。这减少了分配线程等待 GC 搬迁完成的时间。

### 🔹 实战：观察分配性能

#### Perfetto 中的分配相关 Track

在 Perfetto trace 中，ART 对象分配的活动可以通过以下方式观察：

1. **`AllocObject` / `AllocObjectWithAllocator` slice**：当线程在分配对象时，Perfetto 会捕获 ART 的 atrace 标记。如果分配走 slow path（TLAB refill 或 GC 触发），slice 的持续时间会显著拉长。正常的 TLAB fast path 分配在 trace 中几乎看不到（< 1μs）
2. **`RegionSpace::AllocNewTlab` slice**：TLAB refill 事件。出现频率直接反映分配压力
3. **`HeapTaskDaemon` track 上的 GC slice**：`ConcurrentCopying` / `MarkCompact` / `HCollector` 等 slice。GC 频率与分配速率强相关
4. **`art::gc::*` counter tracks**：部分 Android 版本提供堆大小、空闲内存、GC 计数的 counter track

#### 判断分配瓶颈的方法

| 观察到的模式 | 诊断 | 优化方向 |
|---|---|---|
| `AllocObject` slice 频繁出现在主线程，每次 < 5μs | 正常分配，非瓶颈 | 无需优化 |
| `AllocNewTlab` 每帧出现多次 | TLAB refill 频率过高，分配压力大 | 减少热路径的对象分配 |
| `AllocObject` 持续 > 100μs，紧跟 GC slice | 分配触发 GC，slow path 阻塞 | 降低分配速率或增大堆 |
| 主线程出现 `Wait For Completion` + GC slice | foreground GC 回退，严重性能问题 | 检查是否有大对象分配或内存泄漏 |

#### Allocation Tracker / Profiler

Android Studio 的 Memory Profiler 提供了 Allocation Tracking 功能，可以按线程/类记录分配事件。Perfetto 在 Android 12+ 也可以通过 `traced_perf` 抓取 ART 的 allocation sample（需要 `art.heap_alloc_monitor` 配置）。

在 Perfetto SQL 中，可以用以下查询找到分配压力最大的线程：

```sql
-- 查找 TLAB refill 最频繁的线程
SELECT t.name AS thread, COUNT(*) AS refill_count
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
WHERE s.name LIKE '%AllocNewTlab%'
GROUP BY t.name
ORDER BY refill_count DESC
LIMIT 10;
```

[引用: perfetto.dev/docs/analysis/common-queries]

## 扩展

### 🔸 对象池与 TLAB 的协作

Android 的 `Message` 类使用了对象池（`Message.obtain()` / `recycle()`），其设计初衷是减少 `Message` 对象的分配和 GC 压力。在 TLAB 语境下，对象池的效果需要分两面看：

**正面**：对象池减少了新对象的分配次数。每次 `obtain()` 是从链表头部取一个已有对象，不触发 TLAB 分配。对于高频使用的对象（如 `Message`，每帧可能创建多个），对象池能有效降低 TLAB refill 频率。

**反面**：对象池持有的对象不会被 GC 回收，它们作为"存活对象"出现在 GC 的 marking 阶段。如果对象池容量过大（例如缓存了数千个对象），会增加 GC 的标记成本。此外，对象池中的对象分散在堆的不同 Region，可能增加 cache miss。

对于自定义对象池，TLAB 友好的模式是：池容量保持合理（与实际并发使用量匹配），避免无限制增长。TLAB 敌对的模式是：在紧密循环中创建临时对象列表然后整体丢弃——这会产生大量短生命周期对象，触发频繁 TLAB refill 和 young GC。

### 🔸 Compose 的分配模式与 TLAB

Jetpack Compose 的组合（composition）过程会产生大量临时对象：`Snapshot` 对象、状态读取记录、lambda 实例等。在 §18.25（Jetpack Compose 渲染管线架构）中有更详细的讨论。从 TLAB 性能角度：

1. **`remember` 的缓存效果**：`remember` 把计算结果缓存在 Composition 中，避免重组时重复分配。这直接减少了 TLAB 的分配压力
2. **Snapshot 对象的生命周期**：Compose 的 Snapshot 在每次组合或状态修改时创建。如果重组频率很高（例如动画期间），Snapshot 对象的分配会显著增加 TLAB refill 频率
3. **Pausable Composition（Android 17+）**：Android 17 引入的 pausable composition 允许在帧时间不足时暂停组合，下一帧继续。这平滑了分配压力，避免了某一帧内 TLAB 被快速耗尽后触发 GC

详见 §18.25 关于 Compose 渲染管线的深入分析。
