---
status: ready-for-review
title: 内存相关的版本演进
chapter: '4.6'
section: '4.6'
reviewed_date: '2026-06-03'
reviewed_by: openclaw-task6
polish_count: 1
polish_date: '2026-04-07'
polish_by: task2b-polish
rework_date: '2026-04-02'
rework_by: openclaw-task2b
applicable_versions: Android 5.0 (API 21) - Android 16 (API 36)
last_verified: '2026-03-31'
last_verified_against: AOSP android-16.0.0_r1
confidence: medium
sources:
- type: official
  path: https://source.android.com/docs/core/perf/art-management
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://source.android.com/docs/security/test/memory-safety/arm-mte
- type: official
  path: https://developer.android.com/ndk/guides/arm-mte
- type: official
  path: https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: blog
  path: Cubox/Scudo内存分配器介绍-2022-01-14.md
- type: blog
  path: Cubox/【Android 15】内存分配器Scudo在这些年的优化-2024-06-14.md
- type: blog
  path: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md
- type: blog
  path: Cubox/四年之后，重新审视 MTE：从硬件架构到工程落地-2025-12-18.md
- type: research
  path: intake/research-feeds/2026-03-31-11-ch04-art-allocator-evolution.md
- type: research
  path: intake/research-feeds/2026-03-31-11-ch04-art-generational-gc.md
tags:
- memory-evolution
- art
- dalvik
- gc
- bitmap
- scudo
- mte
- large-heap
- memory-limit
- version-history
related_chapters:
- '4.1'
- '4.2'
- '4.3'
- '4.4'
- '4.5'
- '2.9'
drafted_date: '2026-03-31'
drafted_by: openclaw-subagent
review_count: 9
pipeline_stage: 'task9_pending'
task6_state: reviewed
task6_result: pass-light-edit
last_task6_at: '2026-06-03T13:05:00+08:00'
last_task6_review_log: logs/review/2026-06-03-13-review.md
task6_review_notes: '2026-06-03 Task6 13:05：pass-light-edit（状态修复+确认）。前次 12:15 review 已通过但 task6_state 未从 revisiting 更新为 reviewed。本轮确认无新增 L1/L2 问题，修复 frontmatter 状态。源码索引表 linker_phdr.cpp 版本标注不一致（代码注释 android-16.0.0_r1 vs 索引 android-mainline）已记入日志。task9_result 仍 needs-rework，不可自动晋升。'
task9_state: pending
task9_result: 'needs-rework'
last_task9_at: '2026-05-13T20:35:00+08:00'
task2b_state: 'fixed'
task2b_result: fixed-lite
last_task2b_at: '2026-05-13T19:33:05+08:00'
last_task2b_lite_at: '2026-06-03'
task9_reviewed_by: 'openclaw-task9'
task9_reviewed_date: '2026-05-13'
task9_review_notes: '2026-05-13 Task9 20:35：needs-rework。P0 0 / P1 1 / P2 0；CMC/Mark Compact 版本边界写成 Android 15 首次进入 AOSP，实际 android-14.0.0_r1 已有源码路径与 kCollectorTypeCMC/userfaultfd 探测。'
last_task9_review_log: 'logs/deep-review/2026-05-13-20-deep-review.md'
---



# 内存相关的版本演进

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 5.0 ART 替代 Dalvik，GC 效率大幅提升
- 🔹 Android 8.0 Bitmap 内存从 Java Heap 移至 Native Heap
- 🔹 Android 8.0 引入 Concurrent Copying GC；Android 10 完善分代 GC，Young GC 暂停降至 1-3ms
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

日常分析来自不同 Android 版本设备的 Trace 时，一个现象很容易误导判断：同样的内存分配模式，在 Android 8.0 的设备上 GC 暂停可能只有 2ms，但在 Android 6.0 的设备上却高达 30ms。同样是加载一张大图，在 Android 7.1 上 Java 堆直接 OOM，在 Android 8.0 上却可能不触发 Java 堆限制。

原因在于 Android 在每个大版本中都持续调整内存管理。有些改动是底层架构级的（比如 ART 替代 Dalvik），有些是分配策略级的（比如 Bitmap 像素数据搬家），有些是安全增强型的（比如 Scudo 和 MTE）。如果不了解这些变化的脉络，拿到一份旧设备的 Trace 时可能会做出错误的判断——把系统行为误认为是应用问题，或者反过来。

本节把这些散落在各版本中的内存相关变更串成一条清晰的演进线。读完之后，应能回答：给定一个 Android 版本和一种内存现象，这是该版本的正常行为还是异常？这个版本的内存子系统与更新版本相比有哪些关键差异？升级到新版本后，App 需要做哪些适配？

[已验证: 官方文档 source.android.com/docs/core/perf/art-management]

## Android 5.0：ART 替代 Dalvik，GC 效率大幅提升

Android 5.0 Lollipop 是 Android 内存管理的一次重要分水岭：ART（Android Runtime）正式替代了自 Android 诞生以来一直使用的 Dalvik 虚拟机。这个替换的影响范围超过"运行速度"，还改变了 Java 堆的分配策略和垃圾回收机制。

### Dalvik 的 GC 有多慢

Dalvik 虚拟机使用的是基于 `dlmalloc` 的标记-清除（Mark-Sweep）垃圾回收器。整个 GC 过程需要暂停所有应用线程（stop-the-world），在堆中扫描所有可达对象，然后清除不可达的。在早期 Android 设备（1GB 以下内存）上，一次 Full GC 可能暂停 50-100ms。以 60fps 的标准来看，一帧只有 16.6ms，一次 Full GC 就意味着丢掉 3-6 帧。用户感知到的就是"突然卡了一下"。

`dlmalloc` 作为通用内存分配器还有另一个严重问题：全局内存锁。所有线程共享一个锁来分配内存，在多线程场景下，锁争用导致分配延迟，这是早期 Android 应用在多核设备上性能提升不明显的底层原因之一。即使硬件从双核升级到四核、八核，`dlmalloc` 的全局锁仍然拖了后腿。

[已验证: 官方文档 source.android.com/docs/core/perf/art-management]

### ART 带来了什么

ART 的 GC 设计从一开始就瞄准了 Dalvik 的两个核心问题：暂停时间长和全局锁争用。

在分配器层面，ART 引入了 RosAlloc（Runs-of-Slots Allocator）替代 `dlmalloc`。RosAlloc 将内存组织为由相同大小 slot 组成的 run，这些 run 以 page 为单位聚集。不同线程可以在不同的 run 上并行分配，通过分片锁定（sharded locking）策略显著减少了全局锁争用。这个改进让多核设备能发挥并行优势。

在编译策略层面，ART 从 Dalvik 的纯 JIT（Just-In-Time）编译切换到 AOT（Ahead-Of-Time）编译，安装时就将 DEX 字节码编译为本地机器码。虽然 AOT 本身不直接改变 GC 行为，但它改变了对象分配的模式——编译后的代码执行路径更短，某些热点路径上的临时对象分配可以被优化掉，间接降低了 GC 压力。

在 GC 策略层面，ART 引入了 Concurrent Mark-Sweep（CMS）GC，将标记阶段的部分工作与应用线程并发执行。前台应用使用 CMS，后台应用使用更激进的压缩策略来节省内存。CMS 的引入让 GC 暂停时间从 Dalvik 时代的 50-100ms 降到了 10-20ms 的量级。

不过 CMS 仍然有一个关键缺陷：它是非移动式的（non-moving）。标记-清除不会整理内存碎片。长时间运行的应用，堆中的空闲空间可能很多但都是碎片化的，导致无法分配大对象而触发更频繁的 GC，形成恶性循环。Android 8.0 引入 Concurrent Copying GC 后，这个问题才有了系统级解决路径。

ART 内存管理的完整细节（堆结构、GC 策略、对象分配路径）详见 4.3 节「ART 虚拟机内存管理」。

AOSP 源码路径：
- ART CMS GC：`art/runtime/gc/collector/concurrent_mark_sweep.cc`
- RosAlloc：`art/runtime/gc/allocator/rosalloc.cc`

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/allocator/rosalloc.cc]

## Android 8.0：Bitmap 像素数据从 Java 堆迁移到 Native 堆

如果说 ART 替代 Dalvik 改变的是 GC 的"速度"，那么 Bitmap 像素数据的搬迁改变的就是 GC 的"工作范围"。这个变化看似只是一个存储位置的调整，但它深刻影响了 App 的内存统计方式和 OOM 的触发逻辑。

### 为什么 Bitmap 要搬家

在 Android 3.0 到 Android 7.1 的时代，Bitmap 的像素数据存储在 Java 堆中，用一个 `byte[]` 数组持有。一张 1080×1920 的 ARGB_8888 图片占 `1080 × 1920 × 4 ≈ 8MB` 的 Java 堆空间。一个信息流 App 的列表页同时缓存十几张图片，仅图片就占了上百 MB 的 Java 堆——而 Java 堆的上限通常只有 128-512MB。

这导致了一个常见的问题：App 的 Java 堆被 Bitmap 填满，抛出 `OutOfMemoryError`，但此时 Native 内存和系统整体内存明明还有大量空闲。Bitmap 占了 Java 堆的最大头，但像素数据本身不需要 Java GC 管理，主要等待 CPU/GPU 后续读取。把像素数据放在 Java 堆里，会让 GC 反复处理这些大块数据，既增加 GC 工作量，又挤占普通 Java 对象的空间。

[图：Bitmap 像素数据从 Java Heap 迁移到 Native Heap 的内存布局对比（Android 7.1 vs 8.0）]

从 Android 8.0 开始，Bitmap 的像素数据迁移到了 Native 堆。Java 层的 `Bitmap` 对象只保留一个指向 Native Bitmap 的 `long mNativePtr` 指针，不再持有 `byte[] mBuffer`。

[已验证: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md — 源码级分析 Android 7.1 vs 8.0 Bitmap.java 差异]

### 迁移带来的关键变化

**Java 堆的"天花板"变了。** 之前 Bitmap 像素数据计入 `dalvikHeapSize`，受 `Runtime.getRuntime().maxMemory()` 限制。迁移后，Bitmap 不再占用 Java 堆配额。同样大小的 Java 堆，可以容纳更多的 Java 对象（或者说，不容易因为 Bitmap 而触发 Java OOM）。

**内存统计口径变了。** 虽然 Bitmap 不在 Java 堆了，但它仍然占用进程的 PSS（Proportional Set Size）。通过 `dumpsys meminfo` 查看时，`Native Heap` 部分会增大。一个常见的错误是：开发者通过 `Runtime.getRuntime().freeMemory()` 判断内存是否紧张，但在 Android 8.0+ 上，这个方法只反映 Java 堆的情况，完全不包含 Bitmap 占用的 Native 内存。如果 App 有大量图片，可能 Java 堆看起来还很充裕，但进程整体内存已经接近系统限制。

**回收机制的变更。** Native 堆的 Bitmap 不再由 Java GC 直接回收。Android 8.0 引入了 `NativeAllocationRegistry` 机制：创建 Bitmap 时，将一个 Native 回收函数注册到 Java 层的 Cleaner（基于虚引用）。当 Java Bitmap 对象被 GC 回收时，Cleaner 触发 Native 回收函数，最终通过 `free()` 释放像素数据。这比 Android 7.0 之前使用的 Finalizer 机制更稳定、更可预测。

在 Android 8.0 之前，Bitmap 依赖 `BitmapFinalizer.finalize()` 来兜底回收 Native 侧的 SkBitmap 结构体（像素数据虽然在 Java 堆中，Native 侧仍有一个轻量级的 SkBitmap 对象需要清理）。但 Finalizer 的执行时机不可控——GC 不保证何时调用 `finalize()`，可能导致 Native 资源迟迟不释放。Android 8.0 引入 `NativeAllocationRegistry`，基于 `Cleaner`（虚引用）机制替代了 Finalizer：当 Java Bitmap 对象不可达时，`Cleaner` 会在下一次 GC 时触发 Native 回收函数，时序更可控、更可预测。

关于 Bitmap 优化的完整实践（inBitmap 复用、下采样、硬件 Bitmap 等），详见 4.5 节「App 内存优化」。

AOSP 源码路径：
- Android 8.0 Bitmap 创建：`frameworks/base/graphics/java/android/graphics/Bitmap.java`
- NativeAllocationRegistry：`libcore/luni/src/main/java/libcore/util/NativeAllocationRegistry.java`
- Native Bitmap 分配：`frameworks/base/libs/hwui/hwui/Bitmap.cpp`（`allocateHeapBitmap` 使用 `calloc`）

[已验证: AOSP android-15.0.0_r1, frameworks/base/libs/hwui/hwui/Bitmap.cpp]
[已验证: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md]

### 回收兜底策略的版本对照

| Android 版本 | 像素数据存储位置 | 回收兜底策略 |
|---|---|---|
| 3.0–7.1 | Java 堆（byte[]） | Finalizer 机制（BitmapFinalizer） |
| 8.0+ | Native 堆（calloc） | 引用机制（NativeAllocationRegistry） |
| 8.0+ (Hardware Bitmap) | GPU 内存 | GraphicBuffer 引用计数 |


> [已确认: 经核对 AOSP Bitmap.java，Android 3.0–7.1 均使用 BitmapFinalizer（Finalizer 机制）兜底回收 Native 侧的 SkBitmap 结构体。NativeAllocationRegistry 从 Android 8.0（API 26）起引入，随 Bitmap 像素数据迁移至 Native 堆同步上线。]



[已验证: Cubox/不同版本上 Bitmap 内存分配与回收原理对比-2023-01-24.md — 表格总结]

## Android 8.0–14：GC 从 Concurrent Copying 演进到 Concurrent Mark-Compact

4.3 节已经详细解析 ART 的 CC GC 机制，这里聚焦"版本差异"——从 CMS 到 CC 的跨越，以及 Android 10 上的进一步优化。

### Android 8.0：CC GC 的核心改进

Android 8.0 Oreo 将 Concurrent Copying（CC）GC 设为默认策略。CC GC 的核心是用两个 Space 交替使用，GC 时将存活对象拷贝并紧凑排列，天然解决了碎片问题。

CC GC 引入了一个关键技术——Read Barrier（读屏障）。当 GC 正在移动一个对象时，如果应用线程试图读取该对象的引用，Read Barrier 会拦截这次读取，确保线程拿到的是移动后的正确地址。这让大部分 GC 工作可以与应用线程并发执行。

CC GC 在关键指标上的具体改善：

| 指标 | Android 7.0 (CMS) | Android 8.0 (CC) | 改善幅度 |
|---|---|---|---|
| 堆大小 | 基准 | 平均减少 32% | 不再需要预留碎片空间 |
| GC 暂停时间 | 基准 | 减少 85% | 大部分工作并发完成 |
| 对象分配速度 | 基准 | 快 70% | RegionTLAB 零同步分配 |

[图：GC 算法演进对比（CMS → CC → CMC 堆布局、暂停时间与分配策略变化示意）]

CC GC 还引入了 RegionTLAB（Thread Local Allocation Buffer）分配策略。每个应用线程从 `RegionSpace` 中获取专属的 TLAB，分配对象时只需移动一个 top 指针（bump pointer），无需任何同步操作。

[已验证: 官方文档 source.android.com/docs/core/perf/art-management — CC GC 性能数据]

### Android 10：分代 CC GC 的成熟

Android 10 在 CC GC 的基础上进一步完善了分代垃圾回收。ART 将 Allocation Space 划分为 Young Generation（新生代）和 Old Generation（老年代），新对象先进入 Young Generation。当 Young Generation 空间不足时，触发一次 Young GC（Partial GC），只扫描新生代对象，暂停时间通常只有 1-3ms。经历过多次 Young GC 仍然存活的对象被提升到 Old Generation。只有当 Old Generation 空间也不足时，才触发 Full GC。

分代策略大幅减少了 Full GC 的频率。在 120Hz 设备上，帧间隔只有 8.3ms，1-3ms 的 Young GC 暂停通常不会导致丢帧。即使偶尔发生，也只是丢一帧，用户几乎感知不到。但 Android 7.0 时代的 CMS GC 在同样的场景下，Full GC 可能暂停 10-50ms，在 120Hz 设备上意味着连续丢 6 帧以上。

在 Perfetto 中，可以通过 `art_gc` counter 观察这些变化。Android 10+ 的设备上，常见的是大量短暂、频率稳定的 Young GC 活动（每 2-5 秒一次），Full GC 非常罕见。如果在 Android 10+ 的设备上仍然看到频繁的 Full GC，基本可以判断应用存在内存问题（泄漏或过度分配）。

[已验证: AOSP android-15.0.0_r1, art/runtime/gc/collector/concurrent_copying.cc]
[来源: research-feed 2026-03-31-11-ch04-art-generational-gc.md]

### Android 14：UFFD 驱动的 Mark Compact 路径进入 AOSP

到了 Android 14，ART 源码里已经能看到基于 `userfaultfd` 的 Mark Compact / CMC 路径。这说明 AOSP 已具备 UFFD 驱动的 Mark Compact 实现路径，但不等于所有设备已经完全切换到这个 collector；讨论版本边界时，也要把 Android 16 QPR2+ 之后官方明确对外说明的 Generational CMC 分开。

这条路径把对象迁移和应用线程继续运行拆到页级别协调。GC 线程压缩对象时，如果应用线程访问到尚未整理完成的页，内核会把 fault 交给 ART 处理，ART 先整理目标页，再把控制权交还给应用线程。这里讨论的是 collector 实现变化，分代回收思路本身没有消失。

版本边界可以按下面三段记：
- **Android 8.0-13**：主线仍是 CC / generational CC
- **Android 14**：AOSP 已有 UFFD 驱动的 Mark Compact / CMC 路径
- **Android 16 QPR2+**：官方开始把 Generational CMC 作为对外能力明确说明

关于 CMC GC 的详细机制和 Perfetto 观察方法，详见 4.3 节「ART 虚拟机内存管理」。

AOSP 源码路径：
- CC GC：`art/runtime/gc/collector/concurrent_copying.cc`
- CMC GC：`art/runtime/gc/collector/mark_compact.cc`

[已验证: AOSP android-14.0.0_r1, art/runtime/gc/collector/mark_compact.cc]
[已验证: AOSP android-14.0.0_r1, art/runtime/gc/heap.cc]
[来源: Cubox/ART虚拟机CMC GC算法核心实现介绍-2023-06-24.md]
[已验证: Android Developers Blog, Android 16 QPR2 is Released]

## Android 11+：Native malloc 切换到 Scudo 分配器

前面讲的 GC 和 Bitmap 变更主要影响的是 Java 层内存。而 Android 11 开始的 Scudo 分配器切换，影响的则是 Native 层（C/C++）的内存分配——所有通过 `malloc`/`free`、`new`/`delete` 分配的内存。

### 为什么替换 jemalloc

Android 11 之前，64 位设备的默认 Native 内存分配器是 jemalloc。jemalloc 在性能和碎片控制方面表现优秀，但它缺乏对内存安全问题的防御能力。在所有安全漏洞中，内存相关的漏洞（缓冲区溢出、use-after-free、double-free）占比超过一半。

Scudo 的全称是 Scudo Hardened Allocator，它的设计目标是在"性能"和"安全"之间取得平衡。它在保持合理性能的前提下，尽可能检测和阻止内存安全问题。

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

**减少页归还的频率和开销。** Scudo 释放内存后需要将空闲页归还给系统（通过 `madvise(MADV_DONTNEED)`），这个操作本身比较耗时。Google 发现对小内存的 Region（如 32B），即使 90% 的内存已释放，能整页归还的比例也很低。因此对 256B 以下的 Region 设定了更高的归还阈值，避免无意义的遍历和系统调用。同时增加了时间限制（一秒内只允许一次页归还）和增量限制（两次归还之间必须有足够的新释放量）。

**优化碎片管理。** Scudo 没有堆压缩能力，但它在分配时尽量让请求集中在同一个 Group（256KB）内，减少碎片化。Group 内部的分配仍然保持随机性以满足安全需求。

**Cache 分级设计。** 采用两级缓存：一级缓存是数组结构，每次存取操作数组末尾元素，局部性好、速度快；二级缓存是链表结构，批量补充一级缓存。这种分级让频繁的小内存分配几乎不需要锁操作。

AOSP 源码路径：
- Scudo 实现：`external/scudo/standalone/`（Android 集成版本）
- LLVM Scudo 上游：`compiler-rt/lib/scudo/standalone/`

[来源: Cubox/【Android 15】内存分配器Scudo在这些年的优化-2024-06-14.md]
[已验证: Cubox/Scudo内存分配器介绍-2022-01-14.md]

## 进程内存限制与 largeHeap 策略的版本演进

了解各个子系统（GC、Bitmap、Native allocator）的版本变化后，再看一个更宏观的维度：Android 在各版本中如何调整进程内存限制和 largeHeap 策略。这直接决定了 App 能用多少内存，以及超出限制后会发生什么。

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

Android 在 Manifest 中提供了 `android:largeHeap="true"` 选项，允许 App 请求更大的堆空间。这个设计的初衷是为少数需要大量内存的 App（如图片编辑器、地图应用）提供一个"逃生出口"。

largeHeap 有一个经常被误解的点：**它有成本**。更大的堆带来三个直接影响：

- **GC 暂停时间更长**。GC 需要扫描更多的对象，标记和回收的时间与堆大小正相关。一个 512MB 堆上的 Full GC 可能暂停 50ms 以上。
- **其他进程的可用内存减少**。Android 设备的物理内存是所有进程共享的。一个 App 占用过多的 Java 堆，会挤压其他进程的可用空间，触发更频繁的 lmkd 进程回收。
- **系统整体性能下降**。大量进程被杀后重新冷启动，用户感知到的就是"App 频繁重载"。

Google 在不同版本中对 largeHeap 的策略做了一些调整：

- **Android 5.0–7.0**：largeHeap 的上限主要由 OEM 在设备配置中决定，不同设备差异很大。
- **Android 8.0+**：Bitmap 像素数据迁移到 Native 堆后，Java 堆的内存压力大幅降低。很多之前依赖 largeHeap 的图片类 App，在 Android 8.0+ 上即使不开 largeHeap 也不会 OOM。这在客观上降低了 largeHeap 的"刚需"程度。
- **Android 10+**：系统更积极地限制后台进程的存活优先级。`ActivityManager.staticGetMemoryClass()` 和 `staticGetLargeMemoryClass()` 读取的是编译期设备配置（`SystemProperties`），运行时不区分前后台——Java 堆上限不会因为进程退到后台而被压缩。后台进程更容易被杀的原因是 `oom_adj` 升高后 lmkd 回收优先级上升，`largeHeap` 只扩大 Java heap 上限，不提高后台存活优先级。

[已验证: 官方文档 developer.android.com/topic/performance/memory — largeHeap 使用建议]

### 进程整体内存限制

除了 Java 堆限制外，Android 还对进程的整体内存使用有软性约束。系统通过 `lmkd`（Low Memory Killer Daemon）监控所有进程的内存使用，当系统内存紧张时按优先级杀进程。关于 lmkd 的详细机制，见 4.4 节「Low Memory Killer」。

Android 8.0 Bitmap 迁移到 Native 堆后，进程整体内存的构成发生了变化。之前 Bitmap 占 Java 堆，现在占 Native 堆。即使 Java 堆还有空闲，如果 Native 堆（包含 Bitmap 像素数据、JNI 分配、Scudo 管理的内存等）过大，进程仍然可能被 lmkd 选中杀掉。开发者在做内存优化时，需要同时关注 Java 堆和 Native 堆的使用情况。

### 如何查看设备的内存配置

这些命令分别对应系统属性和单进程内存快照。检查时先看 heap 配置，再看 `dumpsys meminfo` 中的 Java / Native / Graphics 分布。

```bash
# 查看堆大小配置
adb shell getprop dalvik.vm.heapstartsize
adb shell getprop dalvik.vm.heapgrowthlimit
adb shell getprop dalvik.vm.heapsize

# 查看进程的内存使用（包含 Java 堆和 Native 堆）
adb shell dumpsys meminfo <package_name>

# 查看进程的 Java 堆详情
adb shell dumpsys meminfo <package_name> --checkin
```

在 Perfetto 中，可以通过 `Process Memory` track 查看进程的 RSS（Resident Set Size）变化，通过 `Java Heap` 相关 counter 查看 Java 堆的使用情况。

[已验证: 官方文档 developer.android.com/topic/performance/memory]

## 扩展：MTE 在 Android 13+ 的平台边界

MTE（Memory Tagging Extension）是 ARM 提供的硬件级内存安全能力，用来检测 Native 代码中的越界访问和 use-after-free。审查 MTE 时，要把 ARM ISA 的能力演进和 Android 平台向 App 暴露的能力边界分开看。

### MTE 的工作原理

[图：MTE Tag 比对机制示意（指针顶部 4-bit Tag 与内存 Tag Storage 中的 Tag 比对流程）]

MTE 会给指针和内存块都附上一段 4-bit Tag。CPU 访问内存时，硬件自动比较两边的 Tag。匹配就继续执行，不匹配就触发异常。对 Native 越界访问和 use-after-free，这是一层直接落在硬件上的检查。

Tag Storage 独立于普通数据存储。每 16 字节内存对应 4 bit Tag，额外占用约 1/32 的物理内存。这个比例解释了为什么 MTE 会有成本，但成本主要来自标签维护和检查路径，不是 Java 层对象模型的变化。

### ARM ISA 时间线

| 时间节点 | 事件 |
|---|---|
| 2018 | ARMv8.5 引入 FEAT_MTE / FEAT_MTE2 |
| 2020 | ARMv8.7 增补 FEAT_MTE3 |
| 2022 | ARMv8.9 增补 FEAT_MTE4 |

ISA 时间线说明的是硬件能力在扩展，不等于同一时间 Android 平台已经把这些能力完整暴露给 App。

### Android 平台时间线

| 时间节点 | 面向 Android 的可见边界 |
|---|---|
| Android 13 | 部分设备开始支持 MTE；App 可通过 `android:memtagMode` 使用 `sync` 或 `async` |
| Android 14 QPR3 | 官方 NDK 指南开始给出 MTE Stack Tagging 的平台边界与构建方式 |
| 后续版本 | 支持设备继续增加，是否默认开启取决于设备配置 |

`adb shell grep mte /proc/cpuinfo` 可以先确认设备是否具备 MTE 支持。公开设备里，Pixel 8 系列是较早可直接验证的一组机型。

### App 侧只看 sync / async

对 App 开发者来说，Manifest 里稳定暴露的模式是 `sync` 和 `async`：

**Synchronous（同步模式）**：tag 不匹配时立即以 `SIGSEGV`（`SEGV_MTESERR`）终止，定位最精确，适合开发和测试阶段排查问题。

**Asynchronous（异步模式）**：tag 不匹配后会在下一次内核入口结算，报 `SIGSEGV`（`SEGV_MTEAERR`）。诊断信息更粗，但运行开销更低，更接近发布阶段的使用方式。

Manifest 中启用异步模式时，只需要在 `application` 上声明 `memtagMode`：

```xml
<!-- 在 Manifest 中启用 MTE 异步模式 -->
<application android:memtagMode="async" ... />
```

Stack Tagging 属于另一条能力线。它要求 JNI / NDK 代码重新用 MTE instrumentation 构建，公开文档给出的平台边界是 Android 14 QPR3 起可用。

<!-- AIW-源码调研-2026-04-26: MTE ASYMM 深度补充 -->
### [自动发现] Asymmetric（ASYMM）模式：生产环境推荐方案

在「App 侧只看 sync / async」的框架下，文档只暴露了 sync 和 async 两个模式。但从 Arm v8.7-A 开始，硬件层面存在第三个模式——**Asymmetric（ASYMM）**，它对读取执行同步检查，对写入执行异步检查。具体表现为：

- **读取越界（如 use-after-free read）**：立即触发 `SEGV_MTESERR`，提供精确错误位置
- **写入越界**：延迟到下次内核入口触发 `SEGV_MTEAERR`，开销与 async 相当

**性能表现**：Arm 官方估算 ASYMM 性能接近 ASYNC（1-2% 开销），远低于 SYNC 的理论开销。在 SPEC INT 2006 实测中，SYNC 在性能核上最高可达 6.64x 减速，而 ASYNC 通常在 1.82x 以内（Pixel 8/9 实测数据，来源：arxiv:2405.02735）。

**关键限制**：ASYMM 需要 `mte3` 特性，即 `/proc/cpuinfo` 中显示 `mte mte3`（而非仅有 `mte`）。当前仅部分 Arm v8.7-A+ 设备支持，主流手机 SoC 中 Pixel 8/9 是较早公开验证的机型。

**Android 系统行为**：Android 不向 App 暴露 ASYMM 模式——App 侧只能请求 `sync` 或 `async`。App 通过 `android:memtagMode="async"` 请求 MTE 时，Zygote 将其映射到 `MEMORY_TAG_LEVEL_ASYNC`，进程以 ASYNC 模式运行。ASYMM 不是 App 请求 `async` 后必然获得的行为，而是取决于硬件能力（`mte3`）和 vendor policy。vendor 可通过 `/sys/devices/system/cpu/cpu<N>/mte_tcf_preferred` 配置 per-CPU preferred 模式（`async` / `sync` / `asymm`），在支持 ASYMM 的硬件上透明升级，但这是平台实现细节，App 无法控制也无需感知。

**sysfs 底层控制**：`/sys/devices/system/cpu/cpu<N>/mte_tcf_preferred` 控制 per-CPU 的 preferred MTE 模式（`async` / `sync` / `asymm`）。写入 `asymm` 可强制启用 ASYMM，但需要 root 权限。

**Scudo + MTE 协作**：Android 默认堆分配器 Scudo（Android 11+）通过 `IRG`（生成随机 tag）和 `STG`（存储 tag 到内存 granule）指令与 MTE 协作。仅 Primary 分配（< 0x10000 字节）支持 MTE tag，Secondary 大块分配通过 mmap 不使用 MTE tag。

**源码锚点**：`frameworks/base/core/java/com/android/internal/os/Zygote.java` 中 `memtagModeToZygoteMemtagLevel()` 将 App 请求映射到内部 `MEMORY_TAG_LEVEL_ASYNC`（Zygote 本身始终 ASYNC）。Scudo 分配器的 MTE tag 逻辑在 LLVM 上游 `compiler-rt/lib/scudo/`（Scudo Primary 分配路径），bionic linker 侧的 MTE 初始化走 `bionic/linker/linker_mte.cpp`。

[来源: arxiv:2405.02735 - ARM MTE Performance in Practice (Extended Version)]
[来源: developer.android.com - Memory Tagging Extension]
[来源: AOSP frameworks/base/core/java/com/android/internal/os/Zygote.java]
[来源: AOSP compiler-rt/lib/scudo/ + bionic/linker/linker_mte.cpp]


[已验证: 官方文档 developer.android.com/ndk/guides/arm-mte]
[已验证: 官方文档 source.android.com/docs/security/test/memory-safety/arm-mte]

## 扩展：Graphics 内存的计量方式变化

Android 在不同版本中对 Graphics 内存的计量和归属做了几次调整，这会影响 `dumpsys meminfo` 里的 `Graphics`、`GL` 和厂商 memtrack 统计。

### Hardware Bitmap 与 Graphics 计量

Android 8.0 引入了 `Bitmap.Config.HARDWARE`。官方定义是：bitmap 像素只存放在 graphic memory 中，bitmap 对象本身始终不可变。它解决的是 Java Heap 不再持有像素副本，不等于这部分内存对进程“完全不可见”。

[已验证: 官方 API 参考 developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE]

排查时按下面的口径理解：
- **不在 Java Heap**：MAT 或 Java Heap 指标看不到像素主体
- **通常体现在 Graphics / GL / memtrack / 驱动相关统计中**：不同 SoC 和 OEM 的可见性不完全一致
- **仍然属于进程的整体内存压力**：图片很多时，PSS、RSS 或 Graphics 统计仍然会上升
- **位图不可变**：`Bitmap.Config.HARDWARE` 只适合解码后直接上屏的场景

如果一台设备上 `dumpsys meminfo` 的 `Graphics` 行不明显，不代表 Hardware Bitmap 没有占内存，往往只是记账口径落在了更底层的 memtrack 或驱动统计上。§10.1 对 Graphics / memtrack 的说明可以直接拿来交叉核对。

### EGL/GL 内存的跟踪

`dumpsys meminfo` 中的 `GL` 和 `Graphics` 行追踪的是 GPU 相关的内存分配。不同版本和不同厂商的跟踪粒度并不完全一致：

- **Android 12+**：系统通过 `memtrack` HAL 提供更精确的 GPU 内存计量，`Graphics` 行通常来自 `libmemtrack` API
- **不同 SoC / OEM**：实现差异仍然存在，同一 App 在不同设备上的 Graphics 数值不能机械横比

### 对性能分析的影响

在 Perfetto 中分析内存问题时，不要只盯 Java Heap。大量 Hardware Bitmap、Surface 或视频缓冲区更常落在 Graphics / GL / memtrack 一侧。实践里通常要把 `dumpsys meminfo`、`dumpsys gpu` 和 Perfetto 的进程内存轨道一起看。

关于 Hardware Bitmap 的使用建议，详见 4.5 节「App 内存优化」。

## Android 15+：16KB Page Size 支持

传统 Android 设备长期以 4KB 页面大小为主。Android 15 开始，AOSP 支持配置为 16KB page size 的设备。Google Play 也规定，自 2025 年 11 月 1 日起，面向 Android 15+ 的新应用和现有应用更新，在 64 位设备上都必须支持 16KB page size。至于某一代机型是否默认采用 16KB，要以具体设备配置和厂商发布信息为准，不能直接写成统一的 Android 16 规则。

这个变化的核心动机是 TLB（Translation Lookaside Buffer）效率。TLB 是 CPU 内部缓存页表映射的高速缓存，容量有限。在 12-16GB 内存的高端设备上，4KB 页面意味着需要管理数百万个页表条目，TLB 的命中率会显著下降。切换到 16KB 页面后，页表条目数量减少为原来的四分之一，TLB 命中率大幅提升——这是所有后续性能改善的底层机制。

Google 官方测试给出的量化结果包括：

- **App 冷启动**平均快 3.16%，在内存压力下最高可达 30%
- **启动功耗**降低约 4.56%
- **相机冷启动**快 6.6%，热启动快 4.48%
- **系统启动**快约 8%（约节省 950ms）

截至 2026 年，16KB page size 仍处于开发者引领阶段。以 Pixel 10（Tensor G5）为例，虽然硬件已针对 16KB 做了优化，但出厂默认仍以 4KB 模式运行，主要原因是大量旧版 NDK 应用在 16KB 环境下会出现兼容性问题。Google Play 要求 2025 年 11 月起上架应用必须 16KB 兼容，但设备侧的全面切换仍需要更长的过渡期。开发者应确保 NDK 代码兼容 16KB，但不必期待短期内所有旗舰机都默认启用。

这些性能提升的代价是**内部碎片**：原本只需要 4KB 的小内存分配（如 `mmap` 映射），现在实际占用 16KB。对于内存分配密集的应用，实际内存占用会更高。不过在 8GB+ 的大内存设备上，这个代价相对 TLB 收益来说是可以接受的。

对于开发者的适配要求：纯 Java/Kotlin 应用自动兼容，无需修改；但使用 NDK/C++ 的应用需要用 NDK r28+ 重新编译，确保 ELF 段对齐到 16KB。硬编码 `PAGE_SIZE = 4096` 的代码必须改为 `sysconf(_SC_PAGESIZE)` 动态获取。可以通过 `adb shell getconf PAGE_SIZE` 检查设备当前的页面大小。

[已验证: 官方文档 source.android.com/docs/architecture/16kb-page-size]
[来源: intake/research-feeds/2026-04-02-07-ch04-16kb-page-size-impact.md]




<!-- AIW-源码调研-2026-04-23: 16KB Page Size PSS 与内存碎片深度补充 -->

### [自动发现] 16KB Page Size 下的 PSS 计算与内部碎片量化

16KB Page Size 对 PSS 的影响需要分成计算口径和最小分配粒度两层看。

#### PSS 计算机制：数据源头 `/proc/<pid>/smaps`

PSS 的计算与页大小无关，它的本质是"按共享进程数分摊"：

```text
PSS = Private_Clean + Private_Dirty
    + (Shared_Clean / N_sharers)
    + (Shared_Dirty / N_sharers)
```

其中 `N_sharers` 是该页被多少个进程共享。这个数据由 Linux kernel 写入 `/proc/<pid>/smaps`。

**关键源码路径**：
- Java 层入口：`frameworks/base/core/java/android/os/Debug.java` — `getMemoryInfo()` / `getPss()`
- JNI 实现：`frameworks/base/core/jni/android_os_Debug.cpp` — `android_os_Debug_getPssPid()` / `read_mapinfo()` 解析 smaps
- 底层数据源：kernel 写入 `/proc/<pid>/smaps`（不可伪造，是进程内存的真实镜像）

PSS 公式本身不因页大小改变——**16KB 页不改变 PSS 的分摊逻辑**。但因为最小分配粒度从 4KB 跳到 16KB，所有小于 16KB 的 private 映射都会多浪费内存，这部分浪费会计入 `Private_Dirty`，直接增加进程的 PSS 计数。

#### 内部碎片量化

| 分配大小 | 4KB 系统使用量 | 4KB 碎片浪费 | 16KB 系统使用量 | 16KB 碎片浪费 | 增量 |
|---------|-------------|------------|-------------|------------|------|
| 5KB | 8KB (2 页) | 3KB | 16KB (1 页) | 11KB | **+8KB (+267%)** |
| 17KB | 20KB (5 页) | 3KB | 32KB (2 页) | 15KB | **+12KB (+60%)** |
| 65KB | 68KB (17 页) | 3KB | 80KB (5 页) | 15KB | **+12KB (+18%)** |

**公式**：`碎片开销增量 = ceil(size / 16KB) × 16KB − ceil(size / 4KB) × 4KB`

其中碎片本身分别为 `ceil(size / page) × page − size`。

以 5KB 为例：`ceil(5/16) × 16 − ceil(5/4) × 4 = 16 − 8 = +8KB`，与表格一致。

**结论**：小分配为主的 native workload（如 JNI 频繁分配小 buffer）在 16KB 系统下内存浪费显著增加。

#### Bionic Linker 16KB Compat Mode

`bionic/linker/linker_phdr.cpp` 中 `ElfReader::LoadSegments()` 调用 `IsEligibleFor16KiBAppCompat()` 判断 ELF 是否需要 compat 处理——满足条件后通过 `Setup16KiBAppCompat()` 配置兼容加载参数（如放宽 RELRO 权限、改用 RW 初始映射）。具体 compat 逻辑封装在 `bionic/linker/linker_phdr_16kib_compat.cpp` 中。当 `kPageSize == 16384` 且 ELF 段 `min_palign == 4096` 时，linker 在 `ReadProgramHeaders` 阶段读取 `min_palign` 和系统属性 `bionic.linker.16kb.app_compat.enabled`，设置 `should_use_16kib_app_compat_` 标志；随后 `Load()` 调用 `Setup16KiBAppCompat()`，其中 `IsEligibleFor16KiBAppCompat()` 校验 RELRO/RW 边界条件；`LoadSegments()` 使用 compat 参数执行实际映射。

```cpp
// bionic/linker/linker_phdr.cpp (android-16.0.0_r1)
// ElfReader::LoadSegments() 内部判断：
if (kPageSize == 16*1024 && min_palign == 4096) {
  // IsEligibleFor16KiBAppCompat() → Setup16KiBAppCompat()
  // 实际 compat 逻辑在 linker_phdr_16kib_compat.cpp
  should_use_16kib_app_compat_ =
    GetBoolProperty("bionic.linker.16kb.app_compat.enabled", false);
}
// Compat 模式代价：
//   1. 初始映射使用 RW（而非标准 RO），需额外 kPageSize 预留空间
//   2. RELRO 使用 PROT_READ | PROT_EXEC（比标准 PROT_READ 的保护更弱）
//   3. 4KB ELF 的共享页变为进程独占（PSS 上升）
```

#### 页表内存节省

| 映射大小 | 4KB 页表内存 | 16KB 页表内存 | 节省 |
|---------|------------|------------|------|
| 1GB | ~2MB | ~0.5MB | **75%** |
| 8GB | ~16MB | ~4MB | **75%** |

在高 RAM 设备上，页表节省可以完全抵消内部碎片开销，整体呈现内存"下降"而非"上升"。

#### 源码文件索引（补充）

| 文件路径 | 关键内容 | 版本 |
|---------|---------|------|
| `frameworks/base/core/jni/android_os_Debug.cpp` | PSS JNI 读取，read_mapinfo() 解析 smaps | android-14+ |
| `bionic/linker/linker_phdr.cpp` | 16KB Compat Mode，`ElfReader::LoadSegments()` 入口 | android-mainline |
| `bionic/linker/linker_phdr_16kib_compat.cpp` | `Setup16KiBAppCompat()` / `IsEligibleFor16KiBAppCompat()` | android-mainline |
| `android.googlesource.com commit fc89c8ae1dfc` | 16KB 错误消息改进 | 2024-08-05 |
| `kernel/common/arch/arm64/Kconfig` | CONFIG_ARM64_16K_PAGES=y | ACK 6.6+ |




### [自动发现] MGLRU 在 GKI 6.12 中基线化

MGLRU（Multi-Gen LRU）在 GKI 6.1（Android 14）和 GKI 6.6（Android 15）的 `defconfig` 中已可核验到 `CONFIG_LRU_GEN=y` 默认启用，不是 Android 16 才首次出现的配置变化。GKI 6.12（Android 16）延续了这一默认配置。如果某台设备的 GKI 分支对应 `android16-6.12`，它沿用的是 6.1/6.6 已建立的 MGLRU 基线，不能写成"Android 16 首次强制开启"。厂商覆盖默认参数的可能性仍然存在，但那是具体设备的行为，不是版本分界。

MGLRU 的核心改进是把页回收决策从被动扫描变为按代分级。内核按访问时间将页分到不同 generation，回收时优先淘汰最老一代中的页。与传统 LRU 的线性链表扫描相比，MGLRU 的多代结构让回收精度更高，误杀活跃页的概率更低。

确认设备是否运行 MGLRU 的可靠方式：检查 `/sys/kernel/mm/lru_gen/enabled`（存在且值为非零表示 MGLRU 已启用），或确认内核配置 `CONFIG_LRU_GEN=y`。Perfetto 中 `mm_vmscan_lru_shrink_inactive` tracepoint 可以观察页回收活动，但该 tracepoint 在传统 LRU 路径中也存在，不能单独作为 MGLRU 的判断依据。如果需要区分 MGLRU 和传统 LRU 的回收行为，应结合上述 sysfs/config 检查结果一起判断。Android 16 设备上，如果发现回收仍然过于激进，需要检查厂商是否覆盖了 MGLRU 的默认参数。

[来源: GKI 6.12 kernel config, CONFIG_LRU_GEN_ENABLED=y by default]

## 版本演进速查表

下表汇总本节覆盖的所有内存相关版本变化：

| 版本 | 变更 | 影响 |
|---|---|---|
| Android 5.0 | ART 替代 Dalvik，CMS GC + RosAlloc | GC 暂停从 50-100ms 降到 10-20ms；多线程分配性能提升 |
| Android 8.0 | CC GC 成为默认；Read Barrier | GC 暂停减少 85%，堆大小减少 32%，分配速度提升 70% |
| Android 8.0 | Bitmap 像素数据迁移到 Native 堆 | Java 堆 OOM 大幅减少；回收机制改为 NativeAllocationRegistry |
| Android 8.0 | 引入 Hardware Bitmap | 像素常驻 graphic memory；计量通常落在 Graphics / GL / memtrack |
| Android 10 | 分代 CC GC 成熟 | Young GC 暂停 1-3ms，Full GC 频率大幅降低 |
| Android 11 | Scudo 替代 jemalloc（64 位大内存设备） | Native 内存安全检测增强，double-free/UAF 可检测 |
| Android 13 | 部分设备开始支持 MTE；App 可配置 `memtagMode=sync/async` | Native 内存错误可借助硬件检测 |
| Android 14 | UFFD 驱动的 Mark Compact / CMC 路径进入 AOSP | GC 路线开始从 CC 扩展到 Mark Compact |
| Android 15 | 16KB Page Size 支持 | 64 位 App 需确认 NDK / 预编译 so 的页大小兼容 |
| Android 16 QPR2+ | 官方对外明确 Generational CMC | 版本讨论时要与 Android 14 的 Mark Compact 路径分开写 |

[来源: 综合本节各锚点的验证结果汇总]

## 常见问题与误区

### 误区一：Android 8.0 后 Bitmap 不用管了

Android 8.0 之后，普通 Bitmap 像素数据更多落在 Native Heap，`Bitmap.Config.HARDWARE` 这类位图则把像素放到 graphic memory。两者都不再占用 Java Heap 配额，但都会形成进程整体内存压力。如果 App 有大量图片（如信息流、图片浏览器），进程照样可能因为总内存过高被 lmkd 选中。

### 误区二：largeHeap 能解决所有内存问题

largeHeap 只是提高了 Java 堆的上限，它不能增加 Native 堆或进程整体内存的配额。如果瓶颈来自 Bitmap 过多（Android 8.0+ 更常体现在 Native Heap 或 Graphics）或 Native 内存泄漏，largeHeap 完全帮不上忙。更糟糕的是，更大的 Java 堆意味着 GC 需要扫描更多对象，可能导致更长的暂停时间。

### 误区三：Scudo 让 Native 内存更安全了，不用再关心内存问题

Scudo 能检测很多内存安全错误，但它是"检测"而不是"预防"。它能在错误发生后报告（crash），但不能阻止错误的发生。而且 Quarantine 默认是禁用的，所以 use-after-free 在生产环境中可能仍然检测不到。Scudo 是一道防线，但不是万能药。

### 误区四：MTE 开销太大，应该关闭

对 App 来说，稳定暴露的 MTE 模式是 `sync` 和 `async`。测试阶段更适合用 `sync` 抓精确出错点，发布阶段是否启用 `async` 要看设备覆盖和 Native 代码稳定性。把 MTE 一律关掉，只会让已经存在的内存破坏继续潜伏。

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
- ART CMC GC：`art/runtime/gc/collector/mark_compact.cc`
- RosAlloc：`art/runtime/gc/allocator/rosalloc.cc`
- RegionSpace：`art/runtime/gc/space/region_space.cc`
- Bitmap 分配（Android 8.0+）：`frameworks/base/libs/hwui/hwui/Bitmap.cpp`
- NativeAllocationRegistry：`libcore/luni/src/main/java/libcore/util/NativeAllocationRegistry.java`
- Scudo：`compiler-rt/lib/scudo/`（LLVM 上游）
- ActivityManager（getMemoryClass）：`frameworks/base/core/java/android/app/ActivityManager.java`

### 官方文档
- [Manage device memory | source.android.com](https://source.android.com/docs/core/perf/art-management)
- [Managing Bitmap Memory | developer.android.com](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Bitmap.Config.HARDWARE | developer.android.com](https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE)
- [Arm MTE on Android | source.android.com](https://source.android.com/docs/security/test/memory-safety/arm-mte)
- [MTE Guide for NDK | developer.android.com](https://developer.android.com/ndk/guides/arm-mte)
- [Investigate RAM Usage | developer.android.com](https://developer.android.com/topic/performance/memory)
- [Support 16 KB page sizes | developer.android.com](https://developer.android.com/guide/practices/page-sizes)

### 素材来源
- [Scudo内存分配器介绍](https://cubox.pro/web/card/6881531810761673398)（内核工匠，2022）
- [【Android 15】内存分配器Scudo在这些年的优化](https://cubox.pro/web/card/7201166401090880497)（2024）
- [不同版本上 Bitmap 内存分配与回收原理对比](https://cubox.pro/web/card/7017381197579814489)（JsonChao，2023）
- [四年之后，重新审视 MTE](https://cubox.pro/web/card/7401290052359161649)（2025）
- [研究] ART 内存分配器演进（dlmalloc → RosAlloc → RegionTLAB）
- [研究] ART 分代 GC 架构（Young/Old Generation + Concurrent Copying）
