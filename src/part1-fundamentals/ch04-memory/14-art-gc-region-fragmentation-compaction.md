---
title: "ART GC Region 碎片化与 Compaction 策略"
chapter: "4.14"
status: finalized
task2b_result: fixed-lite
task2b_state: fixed
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: auto-fixed
pipeline_stage: ready-to-publish
reviewed_by: openclaw-task6
reviewed_date: "2026-06-29"
last_task6_at: "2026-06-29T23:10:00+08:00"
last_task9_at: "2026-06-29T22:20:00+08:00"
last_task9_autofix_at: "2026-06-29"
drafted_date: "2026-06-11"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-29"
last_verified_against: "AOSP android-17.0.0_r1 (主线) / android-16.0.0_r1 (版本演进对比)"
confidence: medium
sources:
  - type: aosp
    path: "platform/art/+/android-17.0.0_r1/runtime/gc/space/region_space.h"
  - type: aosp
    path: "platform/art/+/android-17.0.0_r1/runtime/gc/space/region_space.cc"
  - type: aosp
    path: "platform/art/+/android-17.0.0_r1/runtime/gc/collector/mark_compact.h"
  - type: aosp
    path: "platform/art/+/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc"
  - type: aosp
    path: "platform/art/+/android-17.0.0_r1/runtime/gc/collector/concurrent_copying.cc"
  - type: aosp
    path: "platform/art/+/android-17.0.0_r1/runtime/gc/space/large_object_space.h"
  - type: aosp
    path: "platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc"
tags: ['ART', 'GC', 'RegionSpace', 'MarkCompact', '碎片化', '内存管理', 'UnevacFromSpace', 'userfaultfd']
related_chapters: ['4.3', '4.8', '4.10']
created_by: "task2a-knowledge-gap"
created_date: "2026-06-11"
gap_source: "DeepResearch 调研结果（score 19）+ AOSP 源码结构"
last_task2b_lite_at: "2026-06-29"
---

# 4.14 ART GC Region 碎片化与 Compaction 策略

§4.3 讲过 ART 堆的整体结构和 GC 策略演进，§4.8 讲过分代垃圾回收如何减少 GC 暂停。这一节聚焦一个更窄但实战影响很大的问题：**ART 怎么控制 Region 级内存碎片，以及两条碎片压缩路径（CC 的 UnevacFromSpace 和 CMC 的 userfaultfd 压缩）各自怎么工作**。

读完这一节，应该能回答三个问题：为什么 Region 反复搬迁会造成 RSS 持续增长；UnevacFromSpace 和 CMC 分别在什么条件下生效；以及在做端侧大模型推理这类长生命周期对象密集的场景时，GC 碎片控制方案有什么影响。

## RegionSpace 的区域分配模型

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/region_space.h]

ART 的 ConcurrentCopying（CC）收集器使用 RegionSpace 作为主分配空间。RegionSpace 把堆内存切成等大的 region（默认 256KB），每个 region 有独立的状态和类型标记：

```cpp
// region_space.h
enum RegionType : uint8_t {
  kRegionTypeAll,           // All types
  kRegionTypeFromSpace,     // From-space, to be evacuated
  kRegionTypeUnevacFromSpace, // Unevacuated from-space, NOT to be evacuated
  kRegionTypeToSpace,       // To-space
  kRegionTypeNone,          // None
};
```

每次 CC GC 运行时，RegionSpace 的 region 会在 from-space 和 to-space 之间切换。存活对象从 from-region 搬迁到 to-region，已清空的 from-region 回收。这个模型的问题在于：如果一个 region 的存活率一直很高，每次 GC 都要复制大部分有效对象，但回收收益很小，白白消耗拷贝带宽，还会导致 from-space 和 to-space 在回收窗口里同时占用内存，RSS 居高不下。

Android 内部 bug b/33795328 记录的就是这个问题：region 级的循环分配碎片。

## UnevacFromSpace：区域级碎片控制

### 75% 存活率阈值

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/region_space.cc]

CC 收集器在每次 GC 的 marking 阶段结束后，逐 region 统计存活对象占 region 总大小的比例。核心判断逻辑在 `Region::ShouldBeEvacuated()`：

```cpp
// region_space.cc
static constexpr uint kEvacuateLivePercentThreshold = 75U;
```

- 存活率 < 75% → 设为 from-space，本轮搬迁
- 存活率 ≥ 75% → 设为 **UnevacFromSpace**，不搬迁，原地保留

这个 75% 阈值在 Android 8.0 的 CC 路径中已经存在，Android 10-17 仍保留这一判断口径。

### 原地保留如何消除循环碎片

降级为 UnevacFromSpace 的 region 在本轮 GC 中不会被清空，也不会被 to-space 替代。下一轮 GC 再次按 75% 阈值重新评估。长期高占用的 region 自然稳定下来——它们不会在 from/to 之间反复搬迁。

从实际效果看：

| 场景 | region 存活率 | GC 行为 | 对 RSS 的影响 |
|------|-------------|---------|-------------|
| 新分配、短生命周期对象多 | < 75% | 搬迁到 to-region，原 region 回收 | 正常回收 |
| 常驻对象、缓存、大模型权重引用 | ≥ 75% | UnevacFromSpace，不搬迁 | 避免 from/to 双份占用 |
| 混合 region（部分常驻 + 部分临时） | ≈ 75% | 按阈值边界波动 | 稳定后固定为 unevac |

### CC GC 单轮调用链

1. `ConcurrentCopying::RunPhases()` 判断当前是否走 generational CC 路径
2. `CreateInterRegionRefBitmaps()` 创建 region 间引用位图（仅 generational CC）
3. 逐 region 调用 `ShouldBeEvacuated(evac_mode)` 做搬迁决策
4. 满足阈值 → `SetAsFromSpace()`；否则 → `SetAsUnevacFromSpace(clear_live_bytes)`
5. 仅 from-space 的 region 参与对象搬迁；UnevacFromSpace 的对象保持不动

## 并发 MarkCompact（CMC）与 userfaultfd 压缩

CC 系列通过 UnevacFromSpace 在 region 级做碎片控制，但整个方案不涉及全堆压缩。ART 的另一条路径——**Concurrent MarkCompact（CMC）**——直接在堆级别做并发压缩，依赖 Linux 内核的 `userfaultfd` 机制。

### CMC 与 CC 的分工

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/collector/mark_compact.cc]

这两条路径在代码层是互斥的：

| 条件 | GC 路径 |
|------|--------|
| `gUseReadBarrier == true` | CC（读屏障形态取决于构建配置，可能是 Baker 或 table-lookup） |
| `gUseReadBarrier == false && gUseUserfaultfd == true` | CMC（依赖 UFFD；还要满足 collector 选项 / 系统属性、`MREMAP_DONTUNMAP`、UFFD SIGBUS 等门控） |

CC 的读屏障成本不能写成固定纳秒值：Baker read barrier 和 table-lookup read barrier 的实现路径不同，实际开销还取决于编译配置与负载。CMC 关闭 read barrier，但 `gUseUserfaultfd` 不是单纯的 Linux 版本判断；`KernelSupportsUffd()` 在 Android 17 中会检查 `MREMAP_DONTUNMAP`（Linux 5.13 或 GKI backport）和 UFFD SIGBUS 能力。Linux 5.7 的 fault-retry 只影响并发压缩终止逻辑，不是 CMC 启用门槛。

### userfaultfd 页级压缩模型

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/collector/mark_compact.cc]

CMC 把堆压缩改造为页级 fault-retry 模型：

1. 标记阶段并发标记所有存活对象
2. 计算压缩后的目标布局
3. 按页迁移对象，利用 UFFD/SIGBUS fault 路径处理 mutator 线程对该页的并发访问
4. 内核 ≥ 5.7 支持 fault-retry 特性时，同一页可以重复 fault，并发压缩终止逻辑会更高效

源码注释明确标注了内核依赖：

```cpp
// mark_compact.cc
// Concurrent compaction termination logic is different (and slightly more
// efficient) if the kernel has the fault-retry feature (allowing repeated
// faults on the same page), which was introduced in 5.7
```

### YoungMarkCompact 委托模式

CMC 的 young 收集器 `YoungMarkCompact` 是 `MarkCompact` 的薄包装，共享同一个状态机：

```cpp
// mark_compact.cc
void YoungMarkCompact::RunPhases() {
  DCHECK(!main_collector_->young_gen_);
  main_collector_->young_gen_ = true;
  main_collector_->RunPhases();
  main_collector_->young_gen_ = false;
}
```

设计意图在 `mark_compact.h` 的注释中写得很清楚：使用委托模式避免为 young 和 full 收集器各创建一套数据结构。

`MarkCompact` 构造函数中的 `young_gen_` 布尔字段控制当前走 young 还是 full 路径。两套逻辑共享 heap bitmap、info-map 和压缩状态机。

## Generational CMC 的三代模型

### 三代分区：young / mid / old

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/collector/mark_compact.cc]

Android 16 引入的三代 CMC 通过 `mid_gen_end_` 字段把连续的 bump-pointer space 切成两段：

```
[moving_space_begin_  ...  mid_gen_end_  ...  moving_space_end_]
 |<-------- old + mid -------->|<----------- young ---------->|
```

- young 区在两次 GC 后晋升到 mid
- mid 区再晋升到 old
- `MarkCompact` 构造函数中 `mid_gen_end_` 初始值设为 `moving_space_begin_`（即初始时 young 区覆盖整个空间）

### 门控开关

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/collector/mark_compact.cc]

三代 CMC 的启用受两层开关控制：

```cpp
// mark_compact.cc
#ifdef ART_TARGET_ANDROID
bool ShouldUseGenerationalGC() {
  if (gUseUserfaultfd && !com::android::art::flags::use_generational_cmc()) {
    return false;
  }
  return GetBoolProperty(
    "persist.device_config.runtime_native_boot.use_generational_gc", true);
}
#endif
```

- `use_generational_cmc` flag：编译期 flag，控制是否允许三代 CMC
- `persist.device_config.runtime_native_boot.use_generational_gc`：运行时持久化属性，默认 `true`
- 两个条件必须同时满足才启用三代模型
- 非 Android 目标（如 dex2oat 宿主编译）不受此限制

`Heap` 构造函数中根据 `ShouldUseGenerationalGC()` 的返回值决定是否创建 `YoungMarkCompact` 实例：

```cpp
// heap.cc
if (ShouldUseGenerationalGC()) {
  young_mark_compact_ = new collector::YoungMarkCompact(this, mark_compact_);
  garbage_collectors_.push_back(young_mark_compact_);
}
```

### 降级策略

当设备不支持 `gUseUserfaultfd` 时，`ShouldUseGenerationalGC()` 在非 Android 目标上返回 `true`，但 Heap 构造函数中 foreground collector type 不是 `kCollectorTypeCMC` 时不会创建 MarkCompact 实例。不支持 UFFD 的设备上，系统自动回退到 CC 路径，不会走 CMC。

[待验证: `gUseUserfaultfd` 的设备级默认值由厂商在 `BoardConfig.mk` 或 `parsed_options.cc` 中配置，各厂商的分布情况未在源码中直接体现]

## LargeObjectSpace：不参与压缩的大对象

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/large_object_space.h]

LargeObjectSpace（LOS）的 `CanMoveObjects()` 硬编码返回 `false`：

```cpp
// large_object_space.h
bool CanMoveObjects() const override {
  return false;
}
```

LOS 不参与任何形式的压缩。这是 ART 对「大对象压缩成本不划算」的工程取舍——单个 MB 级对象的拷贝开销远高于保留它所在的内存页。

### 碎片诊断接口

当 LOS 分配失败时，`LogFragmentationAllocFailure()` 打印当前最大连续可分配块长度。`Heap::ThrowOOME` 在分配失败路径调用此接口输出 LOS 占用和碎片情况，用于判断 OOM 是否由大对象碎片化导致。

```cpp
// large_object_space.h
bool LogFragmentationAllocFailure(std::ostream& os, size_t failed_alloc_bytes)
    override REQUIRES_SHARED(Locks::mutator_lock_);
```

LOS 通过 `LargeObjectSpaceType` 枚举支持 `kMap` 和 `kFreeList` 两种实现。`kMap` 按对象 `mmap` / `munmap`，`kFreeList` 预留一段连续空间并用空闲链表复用洞；不能把两种实现都概括成 `dlmalloc`。`kFreeList` 的收益主要是减少频繁大对象分配时的映射管理开销，与 APK 体积没有直接关系。

## kCyclicRegionAllocation：Debug 模式的碎片放大器

[已验证: AOSP android-17.0.0_r1, art/runtime/gc/space/region_space.h]

```cpp
// region_space.h
// strategy reduces region reuse and should help catch some GC bugs
// earlier. However, cyclic region allocation can also create memory
// fragmentation at the region level (see b/33795328); therefore, we
// only enable it in debug mode.
static constexpr bool kCyclicRegionAllocation = kIsDebugBuild;
```

`kCyclicRegionAllocation` 在 debug 构建中启用，循环分配 region 而不是线性分配。这样做的好处是能更早暴露 GC bug（region 不被复用时错误更容易被发现），但代价是加剧 region 级碎片。

生产环境使用线性分配，不受此影响。debug 构建中观察到的 region 碎片化程度会比生产环境更严重，做 GC 分析时需要注意区分。

## CC 与 CMC 的路径选择矩阵

把前面的条件汇总，得到不同设备能力下的 GC 策略选择：

| 设备条件 | GC 路径 | 碎片控制手段 | 暂停特性 |
|---------|--------|------------|---------|
| `gUseReadBarrier == true` | CC | RegionSpace + UnevacFromSpace 75% 阈值 | 暂停时间需看实际 Perfetto GC slice |
| `gUseReadBarrier == false && gUseUserfaultfd == true` | CMC | BumpPointerSpace + UFFD 并发压缩 | 关闭逐引用 read barrier，收益需同设备实测 |
| CMC + generational 开关开启 | 三代 CMC | young/mid/old 分代 + 压缩 | young / full 路径按 collector slice 区分 |

注意：CMC 依赖 UFFD 能力和 ART 运行时门控，不能只用 kernel 版本判断。CC 路径的读屏障形态也要按构建配置区分，不能把所有设备写成 read barrier table 查询。

### 版本演进路径

| 版本 | 默认 GC | 三代模型 | Region 碎片机制 | 关键 flag |
|------|---------|---------|---------------|----------|
| Android 8（API 26） | CC + PartialMarkSweep | 无 | 75% UnevacFromSpace 已存在 | — |
| Android 10（API 29） | CC | 无 | 75% UnevacFromSpace 保留 | — |
| Android 11（API 30） | CC + Generational CC | young + old 两代 | 75% 阈值 | — |
| Android 14-15（API 34-35） | CC 为主，CMC 源码路径进入主线 | young + old / CMC 非三代路径 | 同上 | UFFD / CMC 相关门控 |
| Android 16（API 36） | CC / CMC 二选一 | **young + mid + old 三代**（CMC 路径） | UnevacFromSpace + 75% 阈值 | `use_generational_gc` 默认 true |
| Android 17（API 37） | Android 17 源码已验证 CC / CMC 二选一 | 三代 CMC 源码已验证 | 同上 | `use_generational_cmc` flag |

[适用版本: Android 8（API 26）已有 UnevacFromSpace 75% 阈值；本节主线范围从 Android 10（API 29）开始，Android 11（API 30）引入 Generational CC，Android 16（API 36）引入三代 CMC]

> Android 17 行为已通过 `refs/tags/android-17.0.0_r1` 源码验证。`art/runtime/gc/collector/` 目录结构在 android-15 / android-16 / android-17 之间保持一致。

## GC 暂停预算与端侧 AI 场景

整套碎片控制方案的设计目标，是减少 region 反复搬迁造成的 RSS 增长，并尽量缩短前台可见暂停。具体暂停预算不能从源码常量直接推出，必须结合设备、系统版本和 Perfetto GC slice 实测。

### 对端侧大模型推理的影响

端侧大模型推理通常在 native 侧维持较大的连续权重缓冲，Java 侧只保留句柄、buffer 包装对象或调度对象。不能从 native 权重大小直接推断 Java 对象所在 region 一定超过 75% 存活率；只有当长生命周期 Java 对象在 region 中占比足够高时，CC 才会把这些 region 归入 UnevacFromSpace。

需要注意的点：

- Java 侧应避免在主线程持续分配不进入 LOS 的中等大小对象；超过 LOS 阈值的 primitive array / `String` 会走 LargeObjectSpace，其他对象仍可能进入 moving space
- 对 `byte[]`、大 `String` 这类 LOS 对象，优先预分配并复用 buffer，让它们保持在 non-moving 的 LOS 路径
- ART metrics 和 Perfetto slice 名称会随版本、构建和数据源配置变化；分析时先在实际 trace 中确认 `ConcurrentCopying`、`MarkCompact`、`HeapTaskDaemon` 等可见事件

### 对长生命周期对象密集应用的影响

相册、长会话直播等应用常驻大量 Bitmap 和 VideoDecoder buffer 对应的 Java 引用对象。这些对象所在的 region 自然晋升到 mid/old 后，UnevacFromSpace 的评估开销会随 region 稳定而降低。对象池复用可以让对应 region 更快稳定。

[自动发现] Perfetto 中观察 CC/CMC 行为的方式：先搜索 ART GC、`ConcurrentCopying`、`MarkCompact`、`HeapTaskDaemon` 等 slice，再对比 young GC 和 full GC 的频率与耗时。如果 young GC 频率异常高，需要结合对象分配速率、young space 大小和应用负载一起判断。

## 扩展

### 🔸 CMC 与 ZRAM 压缩的交互

压缩内存页对 UFFD minor-fault 路径的影响。当 ZRAM 压缩了一个正在被 CMC 压缩引用的内存页时，fault 处理路径会多一步解压，可能增加单次 GC 的延迟。具体的量化数据需要在真实设备上测量。

[待补充]

### 🔸 16KB Page Size 对 Region 大小选择与碎片化率的影响

RegionSpace 的 region 大小（默认 256KB）是基于 4KB page size 设计的。16KB page size 下，每个 region 包含的页数从 64 降到 16，分配粒度变粗。对碎片化率的量化影响需要基于设备内核配置验证。

[待补充]

### 🔸 端侧 LLM 推理场景下 GC 暂停对推理延迟的实际影响案例

端侧 LLM 推理通常以 token 为单位，每个 token 的推理延迟在 10-50ms 量级。如果 GC 暂停恰好发生在推理关键路径上，单次 2-3ms 的暂停对整体延迟的影响约 5-15%。但在 batch 推理或多模型并行场景下，GC 暂停的叠加效应需要实测。

[待补充]

---

> 本节内容基于 AOSP android-17.0.0_r1 一手源码验证，详见 DeepResearch/2026-06-09-android17-art-gc-fragmentation-region-mc.md。
> Android 17 相关源码锚点已按 `refs/tags/android-17.0.0_r1` 二次核对。
