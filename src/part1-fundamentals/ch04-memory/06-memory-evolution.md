---
title: "内存相关的版本演进"
chapter: "4.6"
status: ready-for-review
section: "4.6"
reviewed_date: "2026-04-03"
reviewed_by: "openclaw-task6"  # second review after rework
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
rework_date: "2026-04-02"
rework_by: "openclaw-task2b"
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-03-31"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/art-management"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://source.android.com/docs/security/test/memory-safety/arm-mte"
  - type: official
    path: "https://developer.android.com/ndk/guides/arm-mte"
  - type: blog
    path: "Cubox/Scudo内存分配器介绍-2022-01-14.md"
  - type: blog
    path: "Cubox/【Android 15】内存分配器Scudo在这些年的优化-2024-06-14.md"
  - type: blog
    path: "Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md"
  - type: blog
    path: "Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md"
  - type: research
    path: "intake/research-feeds/2026-03-31-11-ch04-art-allocator-evolution.md"
  - type: research
    path: "intake/research-feeds/2026-03-31-11-ch04-art-generational-gc.md"
tags: ['memory-evolution', 'art', 'dalvik', 'gc', 'bitmap', 'scudo', 'mte', 'large-heap', 'memory-limit', 'version-history']
related_chapters: ["4.1", "4.2", "4.3", "4.4", "4.5", "2.9"]
drafted_date: "2026-03-31"
drafted_by: "openclaw-subagent"
---

# 内存相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 5.0 ART 替代 Dalvik，GC 效率大幅提升
- 🔹 Android 8.0 Bitmap 内存从 Java Heap 移至 Native Heap
- 🔹 Android 10 GC 改为 Concurrent Copying，暂停时间降至亚毫秒
- 🔹 Android 11+ malloc 切换到 Scudo allocator
- 🔹 各版本对进程内存限制、大堆(largeHeap)策略的变化

### 扩展（可选深入）

- 🔸 MTE (Memory Tagging Extension) 在 Android 14+ 的推进
- 🔸 各版本 Graphics 内存的计量方式变化（如 GPU 内存归属）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解内存相关的版本演进

如果我们在日常工作中需要分析来自不同 Android 版本设备的 Trace，我们会发现一个让人困惑的现象：同样的内存分配模式，在 Android 8.0 的设备上 GC 暂停可能只有 2ms，但在 Android 6.0 的设备上却高达 30ms。同样是加载一张大图，在 Android 7.1 上 Java 堆直接爆了，在 Android 8.0 上却风平浪静。

这不是魔法，是 Android 在每个大版本中都对内存管理做了或多或少的改动。有些改动是底层架构级的（比如 ART 替代 Dalvik），有些是分配策略级的（比如 Bitmap 像素数据搬家），有些是安全增强型的（比如 Scudo 和 MTE）。如果你不了解这些变化的脉络，拿到一份旧设备的 Trace 时可能会做出错误的判断——把系统行为误认为是应用问题，或者反过来。

本节的目标是把这些散落在各版本中的内存相关变更串成一条清晰的演进线。读完之后，你应该能回答：给定一个 Android 版本和一种内存现象，这是该版本的正常行为还是异常？这个版本的内存子系统与更新版本相比有什么本质区别？以及，升级到新版本后，App 需要做哪些适配？

[已验证: 官方文档 source.android.com/docs/core/perf/art-management]

## Android 5.0：ART 替代 Dalvik，GC 效率大幅提升

Android 5.0 Lollipop 是 Android 内存管理史上最重大的一个版本分水岭——ART（Android Runtime）正式替代了自 Android 诞生以来一直使用的 Dalvik 虚拟机。这个替换影响的不仅仅是"运行速度"这么简单，它从根本上改变了 Java 堆的分配策略和垃圾回收机制。

### Dalvik 的 GC 有多慢

Dalvik 虚拟机使用的是基于 `dlmalloc` 的标记-清除（Mark-Sweep）垃圾回收器。整个 GC 过程需要暂停所有应用线程（stop-the-world），在堆中扫描所有可达对象，然后清除不可达的。在早期 Android 设备（1GB 以下内存）上，一次 Full GC 可能暂停 50-100ms。以 60fps 的标准来看，一帧只有 16.6ms，一次 Full GC 就意味着丢掉 3-6 帧。用户感知到的就是"突然卡了一下"。

`dlmalloc` 作为通用内存分配器还有另一个致命问题——全局内存锁。所有线程共享一个锁来分配内存，在多线程场景下，锁争用导致分配延迟，这是早期 Android 应用在多核设备上性能提升不明显的底层原因之一。即使硬件从双核升级到四核、八核，`dlmalloc` 的全局锁仍然拖了后腿。

[已验证: 官方文档 source.android.com/docs/core/perf/art-management]

### ART 带来了什么

ART 的 GC 设计从一开始就瞄准了 Dalvik 的两个核心痛点：暂停时间长和全局锁争用。

在分配器层面，ART 引入了 RosAlloc（Runs-of-Slots Allocator）替代 `dlmalloc`。RosAlloc 将内存组织为由相同大小 slot 组成的 run，这些 run 以 page 为单位聚集。不同线程可以在不同的 run 上并行分配，通过分片锁定（sharded locking）策略显著减少了全局锁争用。这个改进让多核设备终于能真正发挥并行优势。

在编译策略层面，ART 从 Dalvik 的纯 JIT（Just-In-Time）编译切换到 AOT（Ahead-Of-Time）编译，安装时就将 DEX 字节码编译为本地机器码。虽然 AOT 本身不直接改变 GC 行为，但它改变了对象分配的模式——编译后的代码执行路径更短，某些热点路径上的临时对象分配可以被优化掉，间接降低了 GC 压力。

在 GC 策略层面，ART 引入了 Concurrent Mark-Sweep（CMS）GC，将标记阶段的部分工作与应用线程并发执行。前台应用使用 CMS，后台应用使用更激进的压缩策略来节省内存。CMS 的引入让 GC 暂停时间从 Dalvik 时代的 50-100ms 降到了 10-20ms 的量级。

不过 CMS 仍然有一个根本性的缺陷：它是非移动式的（non-moving）。标记-清除不会整理内存碎片。长时间运行的应用，堆中的空闲空间可能很多但都是碎片化的，导致无法分配大对象而触发更频繁的 GC，形成恶性循环。这个问题直到 Android 8.0 引入 Concurrent Copying GC 才彻底解决。

关于 ART 内存管理的完整细节（堆结构、GC 策略、对象分配路径），我们在 4.3 节「ART 虚拟机内存管理」中已经深入展开，这里不再重复。本节重点关注的是"版本之间的变化"本身。

AOSP 源码路径：
- ART CMS GC：`art/runtime/gc/collector/concurrent_mark_sweep.cc`
- RosAlloc：`art/runtime/gc/allocator/rosalloc.cc`

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/allocator/rosalloc.cc]

## Android 8.0：Bitmap 像素数据从 Java Heap 迁移到 Native Heap

如果说 ART 替代 Dalvik 改变的是 GC 的"速度"，那么 Bitmap 像素数据的搬迁改变的就是 GC 的"工作范围"。这个变化看似只是一个存储位置的调整，但它深刻影响了 App 的内存统计方式和 OOM 的触发逻辑。

### 为什么 Bitmap 要搬家

在 Android 3.0 到 Android 7.1 的时代，Bitmap 的像素数据存储在 Java 堆中，用一个 `byte[]` 数组持有。这意味着什么？一张 1080×1920 的 ARGB_8888 图片占 `1080 × 1920 × 4 ≈ 8MB` 的 Java 堆空间。一个信息流 App 的列表页同时缓存十几张图片，仅图片就占了上百 MB 的 Java 堆——而 Java 堆的上限通常只有 128-512MB。

这导致了一个非常常见的问题：App 的 Java 堆被 Bitmap 填满，抛出 `OutOfMemoryError`，但此时 Native 内存和系统整体内存明明还有大量空闲。Bitmap 占了 Java 堆的最大头，但它只是一个"数据搬运工"——像素数据本身不需要 GC 管理，它们只是放在那里等待 GPU 读取。把像素数据放在 Java 堆里，让 GC 每次都要扫描这些不需要 GC 管理的大块数据，既浪费了 GC 的时间，又挤占了真正需要 GC 管理的 Java 对象的空间。

[图：Bitmap 像素数据从 Java Heap 迁移到 Native Heap 的内存布局对比（Android 7.1 vs 8.0）]

从 Android 8.0 开始，Bitmap 的像素数据迁移到了 Native 堆。Java 层的 `Bitmap` 对象只保留一个指向 Native Bitmap 的 `long mNativePtr` 指针，不再持有 `byte[] mBuffer`。

[已验证: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md — 源码级分析 Android 7.1 vs 8.0 Bitmap.java 差异]

### 迁移带来的关键变化

**Java 堆的"天花板"变了。** 之前 Bitmap 像素数据计入 `dalvikHeapSize`，受 `Runtime.getRuntime().maxMemory()` 限制。迁移后，Bitmap 不再占用 Java 堆配额。这意味着同样大小的 Java 堆，可以容纳更多的 Java 对象（或者说，不容易因为 Bitmap 而触发 Java OOM）。

**内存统计的"作弊"问题。** 虽然 Bitmap 不在 Java 堆了，但它仍然占用进程的 PSS（Proportional Set Size）。通过 `dumpsys meminfo` 查看，你会发现 `Native Heap` 部分增大了。一个常见的错误是：开发者通过 `Runtime.getRuntime().freeMemory()` 判断内存是否紧张，但在 Android 8.0+ 上，这个方法只反映 Java 堆的情况，完全不包含 Bitmap 占用的 Native 内存。如果App 有大量图片，可能 Java 堆看起来还很充裕，但进程整体内存已经接近系统限制。

**回收机制的变更。** Native 堆的 Bitmap 不再由 Java GC 直接回收。Android 8.0 引入了 `NativeAllocationRegistry` 机制：创建 Bitmap 时，将一个 Native 回收函数注册到 Java 层的 Cleaner（基于虚引用）。当 Java Bitmap 对象被 GC 回收时，Cleaner 触发 Native 回收函数，最终通过 `free()` 释放像素数据。这比 Android 7.0 之前使用的 Finalizer 机制更稳定、更可预测。

在 Android 7.0 上，Bitmap 依赖 `BitmapFinalizer.finalize()` 来兜底回收 Native 内存，但 Finalizer 的执行时机不可控，可能导致 Native 内存迟迟不释放。Android 7.0 开始引入引用机制，到 Android 8.0 正式采用 `NativeAllocationRegistry`，这个问题得到了根本性的解决。

关于 Bitmap 优化的完整实践（inBitmap 复用、下采样、硬件 Bitmap 等），详见 4.5 节「App 内存优化」。

AOSP 源码路径：
- Android 8.0 Bitmap 创建：`frameworks/base/graphics/java/android/graphics/Bitmap.java`
- NativeAllocationRegistry：`libcore/ojluni/src/main/java/libcore/util/NativeAllocationRegistry.java`
- Native Bitmap 分配：`frameworks/base/libs/hwui/Bitmap.cpp`（`allocateHeapBitmap` 使用 `calloc`）

[已验证: AOSP android-15.0.0_r1, frameworks/base/libs/hwui/Bitmap.cpp]
[已验证: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md]

### 回收兜底策略的版本对照

| Android 版本 | 像素数据存储位置 | 回收兜底策略 |
|---|---|---|
| 7.0 以前 | Java 堆（byte[]） | Finalizer 机制 |
| 7.0 / 7.1 | Java 堆（byte[]） | 引用机制（NativeAllocationRegistry） |
| 8.0 以后 | Native 堆（calloc） | 引用机制（NativeAllocationRegistry） |
| 8.0+ (Hardware Bitmap) | GPU 内存 | GraphicBuffer 引用计数 |

[已验证: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md — 表格总结]

## Android 8.0–10：GC 演进为 Concurrent Copying，暂停时间降至毫秒级

我们在 4.3 节中详细解析了 ART 的 CC GC 机制，这里聚焦于"版本差异"这个维度——从 CMS 到 CC 的跨越，以及在 Android 10 上的进一步优化。

### Android 8.0：CC GC 的革命性突破

Android 8.0 Oreo 将 Concurrent Copying（CC）GC 设为默认策略。CC GC 的核心是用两个 Space 交替使用，GC 时将存活对象拷贝并紧凑排列，天然解决了碎片问题。

CC GC 引入了一个关键技术——Read Barrier（读屏障）。当 GC 正在移动一个对象时，如果应用线程试图读取该对象的引用，Read Barrier 会拦截这次读取，确保线程拿到的是移动后的正确地址。这让大部分 GC 工作可以真正与应用线程并发执行。

CC GC 带来的性能数据非常亮眼：

| 指标 | Android 7.0 (CMS) | Android 8.0 (CC) | 改善幅度 |
|---|---|---|---|
| 堆大小 | 基准 | 平均减少 32% | 不再需要预留碎片空间 |
| GC 暂停时间 | 基准 | 减少 85% | 大部分工作并发完成 |
| 对象分配速度 | 基准 | 快 70% | RegionTLAB 零同步分配 |

[图：GC 算法演进对比（CMS → CC → CMC 堆布局、暂停时间与分配策略变化示意）]

CC GC 还引入了 RegionTLAB（Thread Local Allocation Buffer）分配策略。每个应用线程从 `RegionSpace` 中获取专属的 TLAB，分配对象时只需移动一个 top 指针（bump pointer），无需任何同步操作。

[已验证: 官方文档 source.android.com/docs/core/perf/art-management — CC GC 性能数据]

### Android 10：分代 CC GC 的成熟

Android 10 在 CC GC 的基础上进一步完善了分代垃圾回收。ART 将 Allocation Space 划分为 Young Generation（新生代）和 Old Generation（老年代），新对象首先进入 Young Generation。当 Young Generation 空间不足时，触发一次 Young GC（Partial GC），只扫描新生代对象，暂停时间通常只有 1-3ms。经历过多次 Young GC 仍然存活的对象被提升到 Old Generation。只有当 Old Generation 空间也不足时，才触发 Full GC。

分代策略大幅减少了 Full GC 的频率。在 120Hz 设备上，帧间隔只有 8.3ms，1-3ms 的 Young GC 暂停通常不会导致丢帧。即使偶尔发生，也只是丢一帧，用户几乎感知不到。但 Android 7.0 时代的 CMS GC 在同样的场景下，Full GC 可能暂停 10-50ms，在 120Hz 设备上意味着连续丢 6 帧以上。

在 Perfetto 中，我们可以通过 `art_gc` counter 观察这些变化。Android 10+ 的设备上，你会看到大量短暂的、频率稳定的 Young GC 活动（每 2-5 秒一次），而 Full GC 非常罕见。如果我们在 Android 10+ 的设备上仍然看到频繁的 Full GC，那几乎可以确定是应用存在内存问题（泄漏或过度分配）。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/collector/concurrent_copying.cc]
[来源: research-feed 2026-03-31-11-ch04-art-generational-gc.md]

### Android 15：CMC GC 与 UFFD 的巧妙结合

Android 15 引入了 Concurrent Mark-Compact（CMC）GC，解决了 CC GC 的两个遗留问题：Read Barrier 的持续性能开销（即使 GC 不运行，每次引用读取也有 1-3% 的额外开销），以及 FromSpace/ToSpace 同时存在时的物理内存短暂翻倍。

CMC 的核心创新是利用 Linux 的 UFFD（User Fault FD）特性。GC 线程从后向前逐页压缩对象，如果应用线程访问到一个尚未被压缩的页面，UFFD 触发异常，VM 优先压缩这个页面然后返回。这样就不需要 Read Barrier 了——GC 不运行时，没有任何额外开销。

CMC 的分配器也从 `RegionSpace` 切换为 `BumpPointerSpace`，结构更简单：分配时只需移动一个 top 指针。

关于 CMC GC 的详细机制和 Perfetto 观察方法，详见 4.3 节「ART 虚拟机内存管理」。

AOSP 源码路径：
- CC GC：`art/runtime/gc/collector/concurrent_copying.cc`
- CMC GC：`art/runtime/gc/collector/concurrent_mark_compact.cc`

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/collector/concurrent_mark_compact.cc]
[来源: Cubox/ART虚拟机CMC GC算法核心实现介绍-2023-06-24.md]

## Android 11+：Native malloc 切换到 Scudo 分配器

前面讲的 GC 和 Bitmap 变更主要影响的是 Java 层内存。而 Android 11 开始的 Scudo 分配器切换，影响的则是 Native 层（C/C++）的内存分配——所有通过 `malloc`/`free`、`new`/`delete` 分配的内存。

### 为什么替换 jemalloc

Android 11 之前，64 位设备的默认 Native 内存分配器是 jemalloc。jemalloc 在性能和碎片控制方面表现优秀，但它缺乏对内存安全问题的防御能力。在所有安全漏洞中，内存相关的漏洞（缓冲区溢出、use-after-free、double-free）占比超过一半。

Scudo 的全称是 Scudo Hardened Allocator，它的设计目标是在"性能"和"安全"之间取得平衡。它不是追求极致性能的分配器，而是一个"戴着镣铐跳舞"的分配器——在保持合理性能的前提下，尽可能检测和阻止内存安全问题。

从 Android 11 开始，Scudo 替代 jemalloc 成为 non-svelte 配置模式下（即大内存设备）的默认分配器。svelte 模式（小内存设备）仍然使用 jemalloc。随着 64 位和大 RAM 设备的普及，Scudo 的覆盖范围不断扩大。

[已验证: Cubox/Scudo内存分配器介绍-2022-01-14.md — Android R 开始 Scudo 替代 jemalloc]

### Scudo 的核心架构

[图：Scudo 分配器四大组件架构（Primary Allocator / Secondary Allocator / TSD 线程缓存 / Quarantine 隔离区）]

Scudo 由四个核心组件构成：

**Primary Allocator** 负责分配较小的内存块。它在初始化时 mmap 出 256M×33 大小的空间，分为 33 个 region，每个 region 管理特定大小的内存块（如 32B、48B、...、64KB）。分配时根据请求大小选择对应的 region，从线程本地缓存中取空闲块。

**Secondary Allocator** 用于分配大于 64KB 的内存。它直接通过 mmap 分配新的虚拟内存，并在内存块两端设置保护页（Guard Page），防止越界访问。

**TSD（Thread Specific Data）** 让不同线程使用不同的缓存，避免锁竞争。64 位 Android 使用共享模型，TSD 池中只有 2 个 TSD 对象，通过轮转分配给线程使用。每个 TSD 包含一个 SizeClassAllocatorLocalCache（一级缓存）和一个 QuarantineCache。

**Quarantine（隔离区）** 延迟释放内存，防止内存块被立即再分配。这对于检测 use-after-free 非常有效——释放后的内存被暂时隔离在 Quarantine 中，如果有代码试图访问这块已释放的内存，会触发检测。不过 Quarantine 对性能和内存占用有一定影响，默认情况下是禁用的。

[已验证: Cubox/Scudo内存分配器介绍-2022-01-14.md — Scudo 四大组件详解]

### 安全检测能力

Scudo 在每次内存释放时进行多重检查：

1. **对齐检测**：释放的地址必须 16 字节对齐。如果传入了一个非对齐的值，报 `misaligned pointer` 错误。
2. **Checksum 检测**：Chunk Header 中保存了校验和，释放时重新计算并比较。如果不一致，报 `corrupted chunk header`——说明 header 被覆盖或传入的不是有效指针。
3. **状态检测**：如果 Chunk 的状态不是 "Allocated"，说明这是一个 double-free 或非法释放，报 `invalid chunk state`。
4. **类型检测**：如果分配用 `malloc` 但释放用 `delete`（或反过来），报 `allocation type mismatch`。
5. **大小检测**：如果释放时传入的大小与分配时不一致，报 `invalid sized delete`。

这些检查的开销很小（主要是几次条件判断），但能捕获大量 Native 内存错误。在实际开发中，如果 Native 代码出现 crash 并且 tombstone 中出现 Scudo 相关的错误信息，通常意味着存在内存安全问题。

[已验证: 官方文档 source.android.com/docs/security/test/memory-safety/arm-mte — Scudo 错误信息分析]

### Scudo 的持续优化

Scudo 引入后，部分系统厂商（特别是国内的手机厂商）对它有顾虑：安全特性带来的性能和内存开销，是否会影响用户体验？

Google 在后续版本中对 Scudo 做了大量优化，主要集中在三个方面：

**减少页归还的频率和开销。** Scudo 释放内存后需要将空闲页归还给系统（通过 `madvise(MADV_DONTNEED)`），这个操作本身比较耗时。Google 发现对小内存的 Region（如 32B），即使 90% 的内存已释放，真正能整页归还的比例也很低。因此对 256B 以下的 Region 设定了更高的归还阈值，避免无意义的遍历和系统调用。同时增加了时间限制（一秒内只允许一次页归还）和增量限制（两次归还之间必须有足够的新释放量）。

**优化碎片管理。** Scudo 没有堆压缩能力，但它在分配时尽量让请求集中在同一个 Group（256KB）内，减少碎片化。Group 内部的分配仍然保持随机性以满足安全需求。

**Cache 分级设计。** 采用两级缓存：一级缓存是数组结构，每次存取操作数组末尾元素，局部性好、速度快；二级缓存是链表结构，批量补充一级缓存。这种分级让频繁的小内存分配几乎不需要锁操作。

AOSP 源码路径：
- Scudo 实现：`system/memory/libmemunreachable/scudo/`（Android 集成版本）
- LLVM Scudo：`compiler-rt/lib/scudo/`

[来源: Cubox/【Android 15】内存分配器Scudo在这些年的优化-2024-06-14.md]
[已验证: Cubox/Scudo内存分配器介绍-2022-01-14.md]

## 进程内存限制与 largeHeap 策略的版本演进

了解了各个子系统（GC、Bitmap、Native allocator）的版本变化后，我们来看一个更宏观的维度：Android 在各版本中是如何调整进程内存限制和 largeHeap 策略的。这直接决定了你的 App 能用多少内存，以及超出限制后会发生什么。

### 常规堆限制（normal heap）

Android 系统为每个进程设定了 Java 堆的大小上限。这个上限不是固定的，而是由设备配置决定的。系统属性 `dalvik.vm.heapsize`（32 位进程）和 `dalvik.vm.heapsize` + `dalvik.vm.heapgrowthlimit` 共同控制。

典型的堆大小配置随设备内存容量变化：

| 设备 RAM | 正常堆限制 | largeHeap 限制 |
|---|---|---|
| 2GB 以下 | 128–192 MB | 256–384 MB |
| 2–4 GB | 192–256 MB | 384–512 MB |
| 4–8 GB | 256–384 MB | 512–768 MB |
| 8 GB+ | 384–512 MB | 768 MB–1 GB |

开发者可以通过 `ActivityManager.getMemoryClass()` 获取正常堆限制（返回值单位为 MB），通过 `ActivityManager.getLargeMemoryClass()` 获取 largeHeap 限制。

[已验证: 官方文档 developer.android.com/topic/performance/memory — getMemoryClass 说明]
[待验证: 上述具体数值来自多个设备的经验值，不同 OEM 可能有不同配置]

### largeHeap 的设计意图与滥用风险

Android 在 Manifest 中提供了 `android:largeHeap="true"` 选项，允许 App 请求更大的堆空间。这个设计的初衷是为少数确实需要大量内存的 App（如图片编辑器、地图应用）提供一个"逃生出口"。

但 largeHeap 有一个经常被误解的点：**它不是免费的**。更大的堆意味着：

- **GC 暂停时间更长**。GC 需要扫描更多的对象，标记和回收的时间与堆大小正相关。一个 512MB 堆上的 Full GC 可能暂停 50ms 以上。
- **其他进程的可用内存减少**。Android 设备的物理内存是所有进程共享的。一个 App 占用过多的 Java 堆，会挤压其他进程的可用空间，触发更频繁的 lmkd 进程回收。
- **系统整体性能下降**。大量进程被杀后重新冷启动，用户感知到的就是"App 频繁重载"。

Google 在不同版本中对 largeHeap 的策略做了一些调整：

- **Android 5.0–7.0**：largeHeap 的上限主要由 OEM 在设备配置中决定，不同设备差异很大。
- **Android 8.0+**：Bitmap 像素数据迁移到 Native 堆后，Java 堆的内存压力大幅降低。很多之前依赖 largeHeap 的图片类 App，在 Android 8.0+ 上即使不开 largeHeap 也不会 OOM。这在客观上降低了 largeHeap 的"刚需"程度。
- **Android 10+**：系统更积极地限制后台进程的内存使用。后台进程的堆增长被更严格地控制，即使声明了 largeHeap，退到后台后可用的堆空间也会被压缩。

[已验证: 官方文档 developer.android.com/topic/performance/memory — largeHeap 使用建议]

### 进程整体内存限制

除了 Java 堆限制外，Android 还对进程的整体内存使用有软性约束。系统通过 `lmkd`（Low Memory Killer Daemon）监控所有进程的内存使用，当系统内存紧张时按优先级杀进程。关于 lmkd 的详细机制，见 4.4 节「Low Memory Killer」。

值得注意的是，Android 8.0 Bitmap 迁移到 Native 堆后，进程整体内存的构成发生了变化。之前 Bitmap 占 Java 堆，现在占 Native 堆。这意味着即使 Java 堆还有空闲，如果 Native 堆（包含 Bitmap 像素数据、JNI 分配、Scudo 管理的内存等）过大，进程仍然可能被 lmkd 选中杀掉。开发者在做内存优化时，需要同时关注 Java 堆和 Native 堆的使用情况。

### 如何查看设备的内存配置

```bash
# 查看堆大小配置
adb shell getprop dalvik.vm.heapsize
adb shell getprop dalvik.vm.heapgrowthlimit
adb shell getprop dalvik.vm.heapsize

# 查看进程的内存使用（包含 Java 堆和 Native 堆）
adb shell dumpsys meminfo <package_name>

# 查看进程的 Java 堆详情
adb shell dumpsys meminfo <package_name> --checkin
```

在 Perfetto 中，可以通过 `Process Memory` track 查看进程的 RSS（Resident Set Size）变化，通过 `Java Heap` 相关 counter 查看 Java 堆的使用情况。

[已验证: 官方文档 developer.android.com/topic/performance/memory]

## 扩展：MTE 在 Android 14+ 的推进

MTE（Memory Tagging Extension）是 ARMv8.5 引入的硬件级内存安全特性，也是 Android 近年在内存安全方面最重要的平台级投入。它的目标是让 Native 内存的越界访问和 use-after-free 等错误在发生时就能被硬件检测到，而不是等到安全漏洞被利用才后知后觉。

### MTE 的工作原理

[图：MTE Tag 比对机制示意（指针顶部 4-bit Tag 与内存 Tag Storage 中的 Tag 比对流程）]

MTE 的核心思想是给每块内存和一个指针都打上一个 4-bit 的 Tag（标签，取值 0-15）。当 CPU 访问内存时，硬件自动比较指针的 Tag 和内存的 Tag：如果匹配，正常执行；如果不匹配，触发异常。由于 Tag 只有 4 bit（16 个值），随机 Tag 的碰撞概率是 1/16，这意味着大约 93.75% 的错误访问会被检测到。

内存的 Tag 存储在独立的物理空间中（Tag Storage），对软件透明。每 16 字节的内存对应 4 bit 的 Tag，所以 Tag Storage 占总物理内存的 1/32（约 3%）。对于一台 8GB 内存的设备，约 256MB 的物理空间被预留给 Tag Storage。

[已验证: Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md — MTE 架构和性能分析]

### Android 中的 MTE 演进时间线

| 时间节点 | 事件 |
|---|---|
| 2018 | ARMv8.5 发布，定义 FEAT_MTE/FEAT_MTE2 |
| 2019 | Google 宣布在 Android 中采用 MTE；ARM 发布 MTE 白皮书 |
| 2020 | ARMv8.7 发布 FEAT_MTE3（引入 Asymmetric 模式） |
| 2022 | ARMv8.9 发布 FEAT_MTE4（Enhanced MTE） |
| 2023 末 | Google Pixel 8 成为第一台支持 MTE 的手机 |
| Android 14 QPR3 | 开始支持 MTE Stack Tagging（实验性） |
| Android 15+ | Scudo 分配器与 MTE 深度集成 |
| Android 16 | Stack MTE 和 Global MTE 支持趋于完整 |

[来源: Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md]

### MTE 的三种检测模式

MTE 提供三种检测模式，在安全性和性能之间提供不同的权衡：

**Synchronous（同步模式）**：每次内存访问都立即检测 Tag，如果不匹配立即触发 SIGSEGV(MTESERR) 信号，精确报告出错指令的位置。安全性最高，但性能开销也最大（3%-30%，取决于工作负载），主要用于调试阶段。

**Asynchronous（异步模式）**：Tag 检测与正常执行并行，不阻断流水线。错误被记录但不立即报告，等到下一次进入内核（如系统调用）时才结算。性能开销只有 1-2%，适合生产环境使用。代价是报错不精确——你只知道"某个时间段内发生了错误"，但不知道是哪条指令。

**Asymmetric（非对称模式）**（FEAT_MTE3 引入）：读操作使用同步检测（开销几乎为零），写操作使用异步检测。这是一种"性价比"最高的模式，在性能接近异步模式的前提下，对读操作的越界检测更加精确。

[已验证: Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md — 三种模式的 CPU 流水线分析]

### Scudo 与 MTE 的配合

Scudo 作为 Android 的默认 Native 内存分配器，是 MTE 在堆上检测的核心载体。当 MTE 启用时，Scudo 会在每次 `malloc` 时生成随机 Tag 并写入内存，在 `free` 时擦除 Tag。这样任何对已释放内存的访问（use-after-free）都会因为 Tag 不匹配而被检测到。

一个巧妙的设计细节：Android 配置 GCR_EL1 寄存器排除 Tag 0，只允许生成 Tag 1-15。而 Scudo 的 Chunk Header 使用 Tag 0。这意味着任何溢出踩踏到 Chunk Header 的行为都会因为 Tag 不匹配被当场捕获。

### 对 App 开发者的影响

如果 App 包含 Native 代码（JNI 库、C/C++ SDK），MTE 的启用意味着之前"碰巧没出问题"的内存错误可能在新设备上被检测到并导致 crash。这是好事——它帮你提前发现了安全漏洞。但需要确保：

1. **使用最新 NDK 编译**（r25+），确保生成的代码与 MTE 兼容。
2. **避免硬编码页大小**（`#define PAGE_SIZE 4096`），改为 `sysconf(_SC_PAGESIZE)`。
3. **在 debug 构建中启用同步模式**，尽早发现内存问题。
4. **通过 `android:memtagMode`** 在 Manifest 中声明 App 的 MTE 策略。

```xml
<!-- 在 Manifest 中启用 MTE 异步模式（推荐） -->
<application android:memtagMode="async" ... />
```

[已验证: 官方文档 developer.android.com/ndk/guides/arm-mte — MTE 适配指南]

## 扩展：Graphics 内存的计量方式变化

Android 在不同版本中对 Graphics 内存的计量和归属做了几次调整，这会影响你在 `dumpsys meminfo` 中看到的 `Graphics` 和 `GL` 行的数值。

### Hardware Bitmap 与 GPU 内存

Android 8.0 引入了 `Bitmap.Config.HARDWARE`。硬件 Bitmap 的像素数据存储在 GPU 内存中，而不是系统 RAM 中。这意味着：

- **不计入 App 的 PSS**：从 `dumpsys meminfo` 的角度看，这张 Bitmap "不占内存"。
- **渲染更快**：GPU 直接使用自己的显存绘制，不需要从系统 RAM 拷贝到 GPU。
- **不能修改**：硬件 Bitmap 是只读的，不能用 Canvas 绘制。
- **不能跨进程**：不能通过 Binder 传递给 Remote Views。

Glide 和 Coil 等图片加载库默认在 API 26+ 上使用硬件 Bitmap。这解释了一个常见困惑：为什么 App 在 Android 8.0+ 上看起来"内存占用更少"——不是真的少了，是一部分内存转移到了 GPU 侧。

### EGL/GL 内存的跟踪

`dumpsys meminfo` 中的 `GL` 和 `Graphics` 行追踪的是 GPU 相关的内存分配。不同版本的跟踪粒度有所差异：

- **Android 7.0 以前**：GPU 内存跟踪不够精确，`Graphics` 行的数值可能低估了实际 GPU 内存使用。
- **Android 7.0-8.0**：改进了 GPU 内存的统计方式，`Graphics` 行更准确。
- **Android 9.0+**：引入了更细粒度的 GPU 内存跟踪，可以区分不同类型的 GPU 内存分配。
- **Android 10+**：`GpuStats` 服务开始收集 GPU 内存使用数据，可以通过 `dumpsys gpu` 查看。

[待验证: 各版本 GPU 内存统计的具体差异，需要参考更多官方文档]

### 对性能分析的影响

在 Perfetto 中分析内存问题时，需要注意 GPU 内存的"隐藏"占用。如果你的 App 大量使用 Hardware Bitmap 或 Surface（如视频播放、相机预览），GPU 内存可能是内存大户，但在常规的 `dumpsys meminfo` 中可能不够显眼。建议结合 `dumpsys gpu` 和 Perfetto 的 GPU track 一起分析。

关于 Hardware Bitmap 的使用建议，详见 4.5 节「App 内存优化」。

## Android 15+：16KB Page Size 的全面启用

传统 Android 设备使用 4KB 的内存页面大小，这是 Linux 内核在大多数架构上的默认值。Android 15 引入了 16KB 页面大小的支持，Android 16 开始在高端设备（8GB+ RAM）上默认启用。Google Play 自 2025 年 11 月起强制要求所有新 App 和更新支持 16KB 页面对齐。

这个变化的核心动机是 TLB（Translation Lookaside Buffer）效率。TLB 是 CPU 内部缓存页表映射的高速缓存，容量有限。在 12-16GB 内存的高端设备上，4KB 页面意味着需要管理数百万个页表条目，TLB 的命中率会显著下降。切换到 16KB 页面后，页表条目数量减少为原来的四分之一，TLB 命中率大幅提升——这是所有后续性能改善的底层机制。

Google 官方测试的量化数据相当可观：

- **App 冷启动**平均快 3.16%，在内存压力下最高可达 30%
- **启动功耗**降低约 4.56%
- **相机冷启动**快 6.6%，热启动快 4.48%
- **系统启动**快约 8%（约节省 950ms）

这些性能提升的代价是**内部碎片**：原本只需要 4KB 的小内存分配（如 `mmap` 映射），现在实际占用 16KB。对于内存分配密集的应用，这意味着更高的内存占用。不过在 8GB+ 的大内存设备上，这个代价相对 TLB 收益来说是可以接受的。

对于开发者的适配要求：纯 Java/Kotlin 应用自动兼容，无需修改；但使用 NDK/C++ 的应用需要用 NDK r28+ 重新编译，确保 ELF 段对齐到 16KB。硬编码 `PAGE_SIZE = 4096` 的代码必须改为 `sysconf(_SC_PAGESIZE)` 动态获取。可以通过 `adb shell getconf PAGE_SIZE` 检查设备当前的页面大小。

[已验证: 官方文档 source.android.com/docs/architecture/16kb-page-size]
[来源: intake/research-feeds/2026-04-02-07-ch04-16kb-page-size-impact.md]


## 版本演进速查表

为了方便日常查阅，我们把本节覆盖的所有内存相关版本变化汇总成一张表：

| 版本 | 变更 | 影响 |
|---|---|---|
| Android 5.0 | ART 替代 Dalvik，CMS GC + RosAlloc | GC 暂停从 50-100ms 降到 10-20ms；多线程分配性能提升 |
| Android 8.0 | CC GC 成为默认；Read Barrier | GC 暂停减少 85%，堆大小减少 32%，分配速度提升 70% |
| Android 8.0 | Bitmap 像素数据迁移到 Native 堆 | Java 堆 OOM 大幅减少；回收机制改为 NativeAllocationRegistry |
| Android 8.0 | 引入 Hardware Bitmap | GPU 侧存储，不计入 PSS |
| Android 10 | 分代 CC GC 成熟 | Young GC 暂停 1-3ms，Full GC 频率大幅降低 |
| Android 11 | Scudo 替代 jemalloc（64 位大内存设备） | Native 内存安全检测增强，double-free/UAF 可检测 |
| Android 14+ | MTE 支持开始落地（Pixel 8 首发硬件） | 硬件级内存安全检测，Async 模式开销 1-2% |
| Android 15 | CMC GC（基于 UFFD）替代 CC GC | 去掉 Read Barrier，GC 不运行时零额外开销 |
| Android 15 | 16KB Page Size 支持 | TLB 命中率提升；冷启动快 3-16%；App 需适配 NDK r28+ |

[来源: 综合本节各锚点的验证结果汇总]

## 常见问题与误区

### 误区一：Android 8.0 后 Bitmap 不用管了

Bitmap 像素数据迁移到 Native 堆后，确实不占用 Java 堆配额了。但它仍然占用进程的 Native 堆和 PSS。如果 App 有大量图片（如信息流、图片浏览器），Native 内存同样可能被撑爆。系统通过 lmkd 杀进程时看的是 PSS 总量，不会区分 Java 还是 Native。

### 误区二：largeHeap 能解决所有内存问题

largeHeap 只是提高了 Java 堆的上限，它不能增加 Native 堆或进程整体内存的配额。如果问题是 Bitmap 过多（Android 8.0+ 占的是 Native 堆）或 Native 内存泄漏，largeHeap 完全帮不上忙。更糟糕的是，更大的 Java 堆意味着 GC 需要扫描更多对象，可能导致更长的暂停时间。

### 误区三：Scudo 让 Native 内存更安全了，不用再关心内存问题

Scudo 能检测很多内存安全错误，但它是"检测"而不是"预防"。它能在错误发生后报告（crash），但不能阻止错误的发生。而且 Quarantine 默认是禁用的，这意味着 use-after-free 在生产环境中可能仍然检测不到。Scudo 是一道防线，但不是万能药。

### 误区四：MTE 开销太大，应该关闭

MTE 的 Async 模式开销只有 1-2%，这在绝大多数场景下可以忽略。Asymm 模式（如果硬件支持）的性能开销与 Async 相当，但对读操作的检测更精确。对于包含 Native 代码的 App，建议至少启用 Async 模式。

## 与其他章节的关联

- **4.1 Android 内存模型全景**：本节的版本演进是 4.1 中各类内存组成在不同版本中的具体变化
- **4.2 Linux 内核内存管理**：Scudo 的 mmap/madvise 最终由内核管理；MTE 的 Tag Storage 与物理内存布局相关
- **4.3 ART 虚拟机内存管理**：GC 策略从 CMS 到 CC 到 CMC 的演进细节
- **4.4 Low Memory Killer**：进程内存限制的变化直接影响 lmkd 的杀进程策略
- **4.5 App 内存优化**：Bitmap 优化、内存泄漏检测等实践在不同版本上的差异
- **2.9 渲染机制的版本演进**：Hardware Bitmap 和 GPU 内存的版本变化与渲染架构的演进相关

## 参考资料

### AOSP 源码路径
- ART CMS GC：`art/runtime/gc/collector/concurrent_mark_sweep.cc`
- ART CC GC：`art/runtime/gc/collector/concurrent_copying.cc`
- ART CMC GC：`art/runtime/gc/collector/concurrent_mark_compact.cc`
- RosAlloc：`art/runtime/gc/allocator/rosalloc.cc`
- RegionSpace：`art/runtime/gc/space/region_space.cc`
- Bitmap 分配（Android 8.0+）：`frameworks/base/libs/hwui/Bitmap.cpp`
- NativeAllocationRegistry：`libcore/ojluni/src/main/java/libcore/util/NativeAllocationRegistry.java`
- Scudo：`compiler-rt/lib/scudo/`（LLVM 上游）
- ActivityManager（getMemoryClass）：`frameworks/base/core/java/android/app/ActivityManager.java`

### 官方文档
- [Manage device memory | source.android.com](https://source.android.com/docs/core/perf/art-management)
- [Managing Bitmap Memory | developer.android.com](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Arm MTE on Android | source.android.com](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [MTE Guide for NDK | developer.android.com](https://developer.android.com/ndk/guides/arm-mte)
- [Investigate RAM Usage | developer.android.com](https://developer.android.com/topic/performance/memory)

### 素材来源
- [Scudo内存分配器介绍](https://cubox.pro/web/card/6881531810761673398)（内核工匠，2022）
- [【Android 15】内存分配器Scudo在这些年的优化](https://cubox.pro/web/card/7201166401090880497)（2024）
- [不同版本上 Bitmap 内存分配与回收原理对比](https://cubox.pro/web/card/7017381197579814489)（JsonChao，2023）
- [四年之后，重新审视 MTE：从硬件架构到工程落地](https://cubox.pro/web/card/7401290052359161649)（2025）
- [研究] ART 内存分配器演进（dlmalloc → RosAlloc → RegionTLAB）
- [研究] ART 分代 GC 架构（Young/Old Generation + Concurrent Copying）
