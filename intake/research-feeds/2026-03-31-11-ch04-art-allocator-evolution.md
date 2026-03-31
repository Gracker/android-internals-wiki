# [研究] ART 内存分配器演进：从 dlmalloc 到 RegionTLAB

- **来源**: https://source.android.com/docs/core/perf/art-management
- **作者/机构**: Google Android Team / AOSP
- **日期**: 2025-2026（持续更新）
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 4.3 ART 虚拟机内存管理
- **映射锚点**: 内存分配器架构、分配器演进、TLAB/Bump-Pointer 机制、内存碎片治理
- **摘要**: 系统梳理 ART 内存分配器从 Dalvik 时代的 dlmalloc 到 ART 的 RosAlloc，再到 Concurrent Copying GC 引入后的 RegionTLAB+Bump-Pointer 分配策略的完整演进路径。包含各代分配器的设计动机、性能瓶颈、以及 AOSP 源码路径。

### 关键发现

1. **dlmalloc 的局限**（Dalvik 时代）：全局内存锁导致多线程冲突；不支持堆压缩导致内存碎片和 OOM；"stop-the-world" GC 造成 UI jank
2. **RosAlloc 改进**（ART 初期）：用 Runs-of-Slots 替代 dlmalloc 的全局锁，引入分片锁定（sharded locking）和线程本地分配缓冲，显著降低多线程场景下的锁争用
3. **RegionTLAB + Bump-Pointer**（Android 8+ CC GC）：Concurrent Copying GC 将堆划分为 256KB 的 region，每个线程分配独立 TLAB，通过移动 top 指针完成分配（零同步开销），对象分配速度比 Android 7.0 快 70%
4. **AOSP 源码路径**：
   - Concurrent Copying 实现：`art/runtime/gc/collector/concurrent_copying.cc`
   - TLAB 相关：`ThreadFlipVisitor(ConcurrentCopying* concurrent_copying, bool use_tlab)`
   - RosAlloc 实现：`art/runtime/gc/allocator/rosalloc.cc`

### 可直接引用段落

> ART 的 Concurrent Copying GC（Android 8.0 Oreo 成为默认）将堆划分为固定大小的 region（例如 256KB bucket），每个应用线程通过 Thread Local Allocation Buffer（TLAB）获得独立的一块连续内存。分配对象时，线程只需移动（"bump"）一个 top 指针，无需任何同步操作。这使得对象分配比 Android 7.0 快约 70%，比 Dalvik 快约 18 倍。当 TLAB 耗尽时，线程向 GC 请求分配新的 TLAB，这个过程的开销远低于每次分配都加锁。

> RosAlloc（Runs-of-Slots Allocator）是 ART 替代 dlmalloc 的核心改进。它将内存组织为同一大小 slot 组成的 run，这些 run 以 page 为单位聚集。通过分片锁定策略，不同线程可以在不同的 run 上并行分配，显著减少了 dlmalloc 全局锁造成的争用。

### 与 queue.json 联动

- 优先级调整建议：4.3 的 priority 可从 55 提升到 65，因为 ART 内存管理是理解 Android 内存体系的关键桥梁
- 素材路径建议：可补充到 4.3 的 material_paths
