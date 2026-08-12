---

title: ART 分代 GC、Region 碎片与暂停分析
chapter: '4.7'
section: '4.7'
status: ready-for-review
applicable_versions: Android 14 (API 34) - Android 17 (API 37)
last_verified: '2026-08-12'
last_verified_against: AOSP android-17.0.0_r1 ART runtime/gc source set (runtime.cc, heap.*, mark_compact.*, region_space.*, write_barrier-inl.h, card_table.h) + Android 17 release notes + ART GC debug/improvements docs + Perfetto android.garbage_collection/heap profiling docs + developer.android.com graphics memory docs; rework refresh for AIW-FRESH-704a10ad8e3f94fc
last_rework_at: '2026-08-12T13:43:41+08:00'
last_rework_run_id: '20260812-133503-rework-3aeaea29'
confidence: medium-high
sources:
- type: official
  path: https://developer.android.com/blog/posts/android-17-is-here
- type: official
  path: https://source.android.com/docs/core/runtime/gc-debug
- type: official
  path: https://source.android.com/docs/core/runtime/improvements
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/runtime.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.h
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.h
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap-inl.h
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/space/region_space.cc
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/write_barrier-inl.h
- type: aosp
  path: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/accounting/card_table.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
- type: official
  path: https://perfetto.dev/docs/reference/heap_profile-cli
- type: official
  path: https://perfetto.dev/docs/data-sources/java-heap-profiler
tags: 
- android
- memory
- research
- art
- gc
- perfetto
pipeline_stage: ready-for-review
task6_state: pending-review
task9_state: pending-review
task2b_state: "fixed"
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part1-fundamentals/ch04-memory/14-art-gc-region-fragmentation-compaction.md"
  - "src/part2-performance/ch10-memory-perf/10-art-gc-fragmentation-regions-optimization.md"
---
# 4.7 ART 分代 GC、Region 碎片与暂停分析

ART 源码以 Android 17 / API 37 的 `android-17.0.0_r1` 为准，内核能力以 `android17-6.18-2026-06_r6` 为准。§4.3 介绍 ART 堆、分配器与收集器的整体关系。

GC 与慢帧重叠，只能说明两件事同时发生。要判断 GC 是否参与造成慢帧，还要拆开暂停时间、GC 线程运行时间、GC 线程等待 CPU 的时间，以及主线程和 RenderThread 当时的调度情况。

## 1. GC 为什么会干扰一帧

应用线程分配对象，GC 负责找出不可达对象并回收空间。现代 ART 收集器把大量工作放在并发阶段，但部分阶段仍需暂停会读写 Java 堆的应用线程（mutator）。

一次 GC 可能从三个方向影响界面：

1. **暂停应用线程**：暂停若落在主线程的帧工作内，会直接占用这帧的时间。
2. **争用 CPU**：并发标记、扫描、压缩会运行 GC 线程。GC 线程处于 runnable 却迟迟得不到 CPU，也说明系统当时存在调度压力。
3. **拖慢分配路径**：堆空间紧张时，分配线程可能等待 GC 完成；这类 blocking GC 比后台并发回收更值得优先检查。

60 Hz 的名义帧间隔约为 16.67 ms，120 Hz 约为 8.33 ms。这个数字只是显示节奏，不能直接当作应用可独占的执行预算。输入、主线程、RenderThread、GPU、SurfaceFlinger 与调度延迟都会占用其中一部分。因而同样一次暂停，在设备负载、刷新率和它落入帧内的位置不同的情况下，结果也会不同。

官方 GC 调试文档给过一次 young concurrent copying 平均暂停 1.83 ms 的示例。它来自一份特定设备和进程的统计输出，只能帮助理解字段，不能当作 Android 设备的统一指标。应用应以自己的发布构建、目标设备和真实交互 trace 为准。

## 2. 从 CC 到 Android 17 的分代 CMC

### 2.1 分代解决什么问题

很多临时对象存活时间很短。若每次回收都扫描整个堆，长期存活对象会被反复处理。分代收集让常见回收优先处理较新的对象，并借助写屏障记录老对象中可能指向新对象的区域，从而减少单轮扫描范围。

这里不采用“90% 对象很快死亡”或“young 一定占堆的 10%～20%”一类固定数字。对象寿命分布、堆布局和收集边界都依赖工作负载与 ART 实现。判断收益时应看回收吞吐、回收量、GC CPU 时间和业务帧表现。

### 2.2 版本边界

ART 的演进可按下面三步理解：

- **Android 8.0**：Concurrent Copying（CC）成为默认收集器。它使用读屏障和 RegionTLAB，主要工作可并发执行。
- **Android 10 及以后**：CC 支持分代模式，young collection 可以延后成本更高的 full-heap collection。
- **Android 17**：Concurrent Mark-Compact（CMC）增加分代 GC，频繁执行成本较低的 young collection。Android 17 官方发布说明提到，它降低了 GC 对应用线程的干扰和最大 RSS。

ART 属于可通过 Google Play 系统更新下发的 Mainline 模块。系统版本相同的两台设备，ART 模块版本、厂商配置和内核能力仍可能不同。因此，“运行 Android 17”不能单独证明某个进程正在使用分代 CMC；应结合设备构建和运行时观测判断。

## 3. Android 17 如何选出收集器

`Heap` 初始化时会按运行时配置创建可用收集器。Android 17 源码中有两条分代路径：

- 使用 CC 且启用分代时，同时创建 full CC 与 young CC。
- 使用 CMC 且启用分代时，同时创建 `MarkCompact` 与 `YoungMarkCompact`。

是否走 CMC 与 userfaultfd（UFFD）能力有关。`mark_compact.cc` 中的 `ShouldUseUserfaultfd()` 会综合命令行选项、系统属性、内核 API 和所需 UFFD feature。`runtime.cc` 对分代 GC 还有一层组合条件：

```cpp
use_generational_gc =
    (kUseBakerReadBarrier || gUseUserfaultfd) &&
    xgc_option.generational_gc &&
    ShouldUseGenerationalGC();
```

这段代码的用途是展示分代开关并非单一布尔量。读屏障或 UFFD 路径、`-Xgc` 配置和运行时开关都要满足相应条件。

在 Android 17 的 `ShouldUseGenerationalGC()` 中，UFFD 路径还会检查 `use_generational_cmc` flag；随后读取 `persist.device_config.runtime_native_boot.use_generational_gc`，默认值为 true。默认值不等于每台设备都会启用，前置条件和产品配置仍需成立。

`android17-6.18-2026-06_r6` 的 arm64 GKI defconfig 含 `CONFIG_USERFAULTFD=y`。这只说明通用内核具备编译期支持。ART 启动时仍会探测 `userfaultfd`、`UFFD_FEATURE_SIGBUS`、`MREMAP_DONTUNMAP` 等能力，并接受产品属性和运行时 flag 的约束。

进程在 post-fork 初始化后会记录类似 `Using generational <collector> GC.` 的日志。它适合在可调试环境中确认选择结果；量产设备是否输出、日志级别和读取权限由构建配置决定。

## 4. 分代 CMC 的 young、mid、old

### 4.1 三代模型

Android 17 的 `mark_compact.h` 明确描述了三代：

```cpp
// In generational-mode, we maintain 3 generations: young, mid, and old.
// Mid generation is collected during young collections. This means objects
// need to survive two GCs before they get promoted to old-gen.
```

这段注释给出两条信息：

- young collection 会同时处理 young 和 mid。
- 新对象需要连续存活两轮 GC，才会晋升到 old。

边界由 `mid_gen_end_` 和 `old_gen_end_` 等状态维护。一轮 young collection 结束后，原 mid 中存活的对象进入 old，原 young 中存活的对象成为下一轮的 mid。多一层 mid 可以减少短期对象过早进入 old 后带来的后续扫描成本。

可以把连续两轮回收理解为：

```text
分配后：        old | mid | young
第 1 轮存活：   old | 原 young 的存活对象 | 新分配对象
第 2 轮存活：   old + 原 mid 的存活对象 | 原 young 的存活对象 | 新分配对象
```

这里的 young、mid、old 是 CMC 的代际边界。它们与卡表（Card Table）中的 dirty、aged、aged2 状态不是同一组概念。

### 4.2 YoungMarkCompact 复用主收集器

`YoungMarkCompact` 没有复制一整套标记压缩实现。它是 `MarkCompact` 的包装器：

```cpp
void YoungMarkCompact::RunPhases() {
  DCHECK(!main_collector_->young_gen_);
  main_collector_->young_gen_ = true;
  main_collector_->RunPhases();
  main_collector_->young_gen_ = false;
}
```

调用时先进入 young 模式，再执行主收集器的阶段，结束后恢复标记。因此，young 和 full CMC 共用主要数据结构与阶段实现，`young_gen_` 决定扫描和标记时采用哪组范围与分支。

### 4.3 Write Barrier 标记的是持有者

老对象可能在 young collection 前写入一个指向新对象的字段。若回收器只从 young 区域内部找引用，就可能漏掉这个仍可达的新对象。ART 在引用写入时执行 Write Barrier：

```cpp
template <WriteBarrier::NullCheck kNullCheck>
inline void WriteBarrier::ForFieldWrite(
    ObjPtr<mirror::Object> dst,
    MemberOffset offset,
    ObjPtr<mirror::Object> new_value) {
  if (kNullCheck == kWithNullCheck && new_value == nullptr) {
    return;
  }
  DCHECK(new_value != nullptr);
  GetCardTable()->MarkCard(dst.Ptr());
}
```

`MarkCard()` 接收的是 `dst`，也就是持有字段的对象。它标记持有者所在的卡表项（card），而非 `new_value` 指向的对象。数组写入和批量字段写入也有对应屏障。

### 4.4 Card Table 缩小老年代扫描范围

Android 17 的 `CardTable` 以 `kCardShift = 10` 划分堆，因此一个 card 覆盖 1024 字节地址范围。卡表的每个字节对应一个卡表项，可取 clean、dirty、aged、aged2 等值。

dirty card 只表示这段堆地址最近发生过引用写入，是一个保守候选。它不能说明其中必然有 old-to-young 引用。GC 仍需扫描 card 覆盖的对象并检查字段。

young CMC 的 `ScanOldGenObjects()` 会扫描 moving old 区域和 non-moving space 中达到指定 card age 的区域。这样可以找到老对象指向年轻对象的引用，同时避免每轮都遍历完整 old generation。

## 5. Young 之后何时执行 Full

ART 不按固定次数轮换 young 与 full。`heap.cc` 在一次非 sticky 回收后把下一次设为 sticky；完成 sticky 回收后，则比较本次 sticky 回收吞吐和历史非 sticky 回收的平均吞吐，并结合目标阈值决定下一次继续 sticky，还是改用非 sticky 回收。

在这里：

- sticky 对分代收集器对应 young collection；
- non-sticky 对应覆盖更大范围的 collection；
- 回收吞吐关注单位时间释放的字节等运行数据。

若 young collection 仍能快速释放足够空间，继续 young 往往更划算。随着新生代存活率上升或可回收量下降，full collection 可能获得更好的回收效率。这个决策会随堆状态变化，所以“每 N 次 young 执行一次 full”以及固定 GC 周期都不适合作为诊断依据。

应用启动阶段还有特殊处理。post-fork 后 ART 会先采用 full collection，并在启动期临时调整堆阈值，避免把稳态策略机械套到冷启动过程。

## 6. 暂停时间、总时长和调度时间

分析一轮 GC 时，至少分开看四类时间：

| 指标 | 回答的问题 |
| --- | --- |
| mutator pause | 应用线程被暂停了多久 |
| GC wall duration | 从 GC 开始到结束经过了多久 |
| GC running duration | GC 线程得到 CPU 并执行了多久 |
| GC runnable duration | GC 线程可运行但在等待 CPU 多久 |

wall duration 很长，不一定代表应用线程全程暂停。running 高说明 GC 消耗了较多 CPU；runnable 高说明 GC 线程本身也受调度竞争影响。若同一时段主线程或 RenderThread 也频繁 runnable，应进一步看 CPU 核、优先级、频率和其他进程负载。

暂停也不能只看平均值。少量长尾、time to suspend GC，常常比稳定的小暂停更容易伤害交互。对滚动、动画和输入响应，应同时看 P95/P99 或最大值，并回到发生长尾的 trace 片段。

## 7. Large Object Space 的精确边界

Android 17 的默认 large-object threshold 是 12 KiB，但它不适用于所有 Java 对象。`Heap::ShouldAllocLargeObject()` 的核心条件是：

```cpp
byte_count >= large_object_threshold_ &&
    (c->IsPrimitiveArray() || c->IsStringClass())
```

达到阈值的 primitive array 或 `String` 会先尝试 Large Object Space（LOS）分配；若 LOS 分配失败，分配器仍可回退到普通 space。普通业务对象即使整体很大，也不能仅凭“超过 12 KiB”断言它进入 LOS。

LOS 对排查的意义主要在于识别大块 `byte[]`、`char[]`、`int[]`、解码缓冲区和大字符串。频繁创建这些对象会增加大对象分配、扫描和回收成本。是否产生 blocking GC 取决于当时的堆空间与分配结果，不能把每次 LOS 分配都描述为同步 GC。

Android 8.0 起，`Bitmap` 像素数据放在 native heap。Android 14～17 中，大图带来的内存压力仍很重要，但像素内存不能按 Java LOS 对象计算。应结合 Java wrapper、native allocation、图形缓冲和 GPU 资源分别观察。

## 8. Region 碎片与 compaction 的准确边界

ART heap 的碎片、native allocator 碎片与 Linux 物理页碎片属于不同地址层级。ART compaction 移动 managed object，目标是整理对象空间；Linux `mm/compaction.c` 迁移物理页，目标是形成连续 buddy 空闲块。两者都可能出现在同一时间窗，但不能共享一套“碎片率”。

### CC 的三种 evacuation 结果

Concurrent Copying 以 RegionSpace 为主要 moving space。Android 17 会结合 collection 范围、region 年龄、分配状态和存活率，为 region 选择不同结果：

- `ForceEvac`：本轮必须搬迁；
- `LivePercentNewlyAllocated`：新分配或低存活 region 可按存活比例决定搬迁；
- `UnevacFromSpace`：高存活 region 暂时保留，避免为了少量空洞复制大量对象。

`RegionSpace::ShouldBeEvacuated()` 的条件还需要逐项读：large live region 不搬迁；force-all 模式直接搬迁；新分配 region 会被搬迁；其他普通 region 只有在按对齐后已分配字节计算的存活率严格低于 75% 时才搬迁。75% 因而只是这条实现路径的局部选择阈值，不是整个 Java heap 的碎片告警线。RegionSpace 中跨多个 region 的 large region 也不等于 Large Object Space；前者仍属于 moving-space 布局，后者是独立非移动大对象空间。

### CMC 与 UFFD 处理页级搬迁

CMC 会先标记存活对象、计算压紧后的目标地址并修正引用，再用 userfaultfd/SIGBUS 相关能力协调应用重新访问尚未处理页面时的填充。其运行条件还受 `MREMAP_DONTUNMAP`、UFFD feature、系统属性和 ART flag 约束；条件不满足时可能选择 CC 或 STW fallback。

Generational CMC 的 `YoungMarkCompact` 复用主 `MarkCompact`，用 young/mid/old 边界缩小常见回收范围。young collection 不等于只看新区域：old-to-young 引用仍需要 card/remembered information，存活对象要经过 young、mid 两轮才晋升 old。

### 诊断时先确认 collector

同样的“GC 后 RSS 没下降”可能来自存活集过大、Unevac region、LOS、allocator 保留页面，或 Java heap 之外的 native/graphics 增长。诊断顺序应是：确认 collector 与 generational 状态，区分 young/full 和 cause，再对齐暂停、对象存活、region/LOS 与 RSS/PSS。不要仅凭一次 full GC 或单个 heap utilization 数字声明“碎片严重”。

## 9. 用 Perfetto 判断 GC 是否参与慢帧

### 9.1 先保证 trace 包含所需数据

抓取交互 trace 时，至少需要应用调度、ART/GC 事件和 Frame Timeline。不同 Android 构建与 trace 配置能看到的轨道不同。若 SQL 表为空，应先检查 data source 和目标进程是否被采集，再判断应用没有 GC。

推荐按这个顺序阅读：

1. 找到 `actual_frame_timeline_slice` 中的 jank 帧。
2. 查看主线程和 RenderThread 在这一帧内处于 Running、Runnable、Sleeping 还是被阻塞。
3. 查看同进程 GC event 是否与帧重叠，以及 GC 是短而密还是单次长尾。
4. 对重叠事件比较 wall、running、runnable 和 interruptible/uninterruptible 时间。
5. 再决定是否抓分配 profile 或 heap dump。

### 9.2 汇总 GC 类型与时长

下面的查询适合回答“哪类 GC 多、总共回收了多少、wall time 多少”：

```sql
INCLUDE PERFETTO MODULE android.garbage_collection;

SELECT
  process_name,
  gc_type,
  COUNT(*) AS gc_count,
  ROUND(AVG(gc_dur) / 1e6, 2) AS avg_gc_ms,
  ROUND(MAX(gc_dur) / 1e6, 2) AS max_gc_ms,
  ROUND(SUM(reclaimed_mb), 2) AS reclaimed_mb
FROM android_garbage_collection_events
WHERE process_name = 'com.example.app'
GROUP BY process_name, gc_type
ORDER BY gc_count DESC;
```

`gc_dur` 是事件 wall duration。`reclaimed_mb` 由 Perfetto 的 heap counter 区间变化推导，适合在同一 trace 中比较趋势，不应当作所有堆空间释放量的精确账本。

### 9.3 查 GC 与 jank 帧的时间交集

下面的查询按进程和时间区间找交集：

```sql
INCLUDE PERFETTO MODULE android.garbage_collection;

SELECT
  gc.process_name,
  gc.gc_type,
  gc.gc_ts,
  ROUND(gc.gc_dur / 1e6, 2) AS gc_ms,
  ft.ts AS frame_ts,
  ROUND(ft.dur / 1e6, 2) AS frame_ms,
  ft.jank_type
FROM android_garbage_collection_events gc
JOIN actual_frame_timeline_slice ft
  ON gc.upid = ft.upid
 AND gc.gc_ts < ft.ts + ft.dur
 AND gc.gc_ts + gc.gc_dur > ft.ts
WHERE gc.process_name = 'com.example.app'
  AND COALESCE(LOWER(ft.jank_type), 'none') != 'none'
ORDER BY gc.gc_ts;
```

查询结果证明两者重叠，不证明因果。还需检查应用线程暂停、GC 线程调度以及同一帧中的其他阻塞。

### 9.4 区分 GC 执行和等待 CPU

下面的查询把 running 与 runnable 分开：

```sql
INCLUDE PERFETTO MODULE android.garbage_collection;

SELECT
  thread_name,
  gc_type,
  COUNT(*) AS gc_count,
  ROUND(AVG(gc_running_dur) / 1e6, 2) AS avg_running_ms,
  ROUND(AVG(gc_runnable_dur) / 1e6, 2) AS avg_runnable_ms,
  ROUND(MAX(gc_runnable_dur) / 1e6, 2) AS max_runnable_ms
FROM android_garbage_collection_events
WHERE process_name = 'com.example.app'
GROUP BY thread_name, gc_type
ORDER BY avg_running_ms DESC;
```

running 高时，继续查分配速率、存活对象和 full collection；runnable 高时，同时查系统负载和 CPU 调度。二者也可能一起升高。

### 9.5 CMC fault counter 只覆盖 GC 线程

Android 17 的 `MarkCompact::TraceFaults()` 记录 `Majflt-GC` 与 `Minflt-GC` 两个 atrace counter。前者表示 GC 线程的 major fault，可能涉及文件回读或 ZRAM 解压；后者表示 GC 线程的 minor fault，例如 COW 或匿名页分配。源码明确说明这两个 counter 不覆盖 userfault，因此它们只能证明 GC 线程自身发生了 fault。若 `Majflt-GC` 上升，还要对齐 swap、ZRAM、文件回读和系统内存压力，不能直接归因为某个 CMC 目标页。

## 10. 用 GC timing、分配 profile 和 heap dump 补证据

### 10.1 SIGQUIT 的累计 GC 统计

在允许调试的设备上，可以向目标进程发送 `SIGQUIT`：

```bash
adb shell kill -s QUIT <PID>
```

ART 会把线程栈、锁和累计 GC timing 写入 ANR trace，搜索 `Dumping cumulative Gc timings` 可找到各收集器阶段、暂停直方图、time to suspend、吞吐和 blocking GC 统计。量产设备对 `/data/anr` 的读取常有限制，可通过可调试构建或 bugreport 获取允许访问的记录。

发送 `SIGQUIT` 会触发一次诊断转储。压测脚本应控制次数，并避免在用户生产会话中随意执行。

### 10.2 ART allocation profiling 看谁在分配

Perfetto 的 `heap_profile` 工具在 Android 12 及以后可选择已注册的 heap。当前命令行示例使用的 ART heap 名称为 `com.android.art`：

```bash
tools/heap_profile -p <PID> --heaps com.android.art
```

它以采样方式记录 ART 分配及调用栈，适合定位滚动、解析或动画期间的分配热点。采样间隔会影响精度与开销，profile 也会扰动被测进程，因此要使用相同场景做前后对照。

### 10.3 Java heap dump 看谁在保留

Perfetto ART heap dump 需要 Android 11 及以后。它记录完整的 Java 对象引用图和保留关系，不记录分配调用栈，也不包含普通 HPROF 中的对象内容。

Android 13 及以后，某些通过 `NativeAllocationRegistry` 关联的 native size 会以额外节点显示。这个数字只覆盖被注册并能关联的 native 分配，不能代表进程全部 native heap。

选择工具时可用一个简单问题区分：

- “谁在高频创建对象？”——抓 ART allocation profile。
- “谁把这批对象一直留着？”——抓 Java heap dump。

## 11. 应用侧如何降低 GC 干扰

### 11.1 从已证实的热点开始

先录制可重复场景，确认分配调用栈、GC 类型和慢帧关系，再改代码。只看到 heap 曲线呈锯齿状还不够，因为正常运行的 managed heap 本来就会分配和回收。

优先级通常是：

1. 每帧、每次列表绑定、每个音视频数据包等高频路径。
2. 大块 primitive array、字符串与序列化缓冲。
3. 造成 full 或 blocking GC 的存活对象和短时峰值。
4. 普通低频业务对象。

### 11.2 移出每帧分配

自定义绘制中，确定可安全复用的绘图对象可以放到字段中：

```kotlin
class MeterView(context: Context) : View(context) {
    private val barPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val barBounds = RectF()

    override fun onDraw(canvas: Canvas) {
        barBounds.set(0f, 0f, width * progress, height.toFloat())
        canvas.drawRect(barBounds, barPaint)
    }
}
```

这段代码复用 `Paint` 和 `RectF`，但复用对象仍需遵守线程与重入边界。若对象会跨线程使用，或一次调用尚未结束就可能再次进入，共享可变实例会带来数据竞争。

循环中的字符串拼接、装箱、临时集合也值得检查。优化目标是减少 profile 中已经出现的热点，不需要把所有小对象都改成手写缓存。

### 11.3 谨慎使用对象池

Android 系统中的 `Message`、`MotionEvent` 等类型有明确的高频使用模式和生命周期约束。普通应用对象未必适合照搬对象池。

对象池会延长对象存活时间，增加状态清理、容量管理和线程安全成本，还可能让更多对象进入 old。只有在 profile 证明创建成本或分配量显著，并且对象可完整重置、生命周期清楚时，才值得引入有上限的池。

对短小的 managed 对象，ART 的 TLAB 分配通常很快。先消除无意义的分配或调整算法，往往比维护通用对象池更可靠。

### 11.4 复用大缓冲区要限制生命周期

网络、图片、音视频和序列化代码常反复创建大 `byte[]`。可以按业务并发上限复用缓冲区，或分批处理数据，避免短时间堆积多个峰值。

缓存过大会抬高常驻内存，并可能触发 Android 17 的应用内存限制或系统回收。缓冲池应有容量上限，页面离开或任务结束后释放长期引用；低内存回调可作为收缩信号，不能代替容量设计。

### 11.5 Compose 以重组证据为准

Compose 重组不等于每次都会创建 lambda 或状态对象。编译器可以记忆部分值，稳定性推断、参数变化和 API 使用方式也会影响重组范围。

排查 Compose 场景时，先用系统 trace、Compose tooling 或基准测试确认哪些 composable 频繁重组，再处理：

- 把状态读取推迟到更接近使用位置，缩小受影响范围。
- 让输入类型满足可验证的稳定性约束。
- 对昂贵且可安全复用的计算使用 `remember`，并确保 key 能表达失效条件。
- 绘制阶段仅复用 profile 证明频繁分配的对象。

`remember` 会延长对象生命周期。将大型集合或上下文相关对象无条件记忆，可能以更高保留量换取更少分配，需要同时看 allocation profile 和 heap dump。

### 11.6 显式资源关闭与 GC 分工

文件、游标、压缩器、图像解码器和 native handle 应通过 `close()`、`use {}` 或明确的生命周期释放。GC 负责 managed object 的可达性，不能提供及时释放外部资源的时限保证。

避免依赖 finalization。带 finalizer 的对象需要额外处理，回收会延后。`Cleaner` 可以作为无法显式关闭时的安全网，但不应替代 `AutoCloseable` 和结构化资源管理。

不要把 `System.gc()` 当作常规优化。若显式 GC 未被运行时禁止，`Heap::CollectGarbage()` 会以 explicit cause 请求 `gc_plan_.back()` 对应的回收计划，通常涉及较大范围；调用也可能被配置忽略。业务代码无法借它稳定控制暂停时机。

## 12. 一次 GC 卡顿排查示例

假设列表快速滚动时出现间歇性慢帧，可以按以下顺序缩小范围：

1. 用 Macrobenchmark 或固定手势重复滚动，保留发布构建、设备温度和刷新率。
2. 录制包含 Frame Timeline、sched 和 ART/GC 的 Perfetto trace。
3. 用时间交集查询找出 GC 与 jank frame 重叠的样本。
4. 对样本查看主线程 pause、GC running/runnable，以及是否有 blocking GC。
5. 若 GC 短而密，抓 ART allocation profile，定位每次绑定或绘制中的分配栈。
6. 若 full GC 后仍释放很少，或堆持续增长，抓 heap dump 查保留关系。
7. 只修改已定位的热点，再用相同脚本复测 GC 次数、CPU 时间、长尾帧和 RSS。

若修改后分配量下降，而长尾帧没有改善，说明原来的 GC 重叠可能只是伴随现象。此时应回到 Binder、锁、I/O、CPU 调度或 GPU 等方向继续查。

## 13. 常见问题

### Young GC 没有扫描整个 old，如何保证不漏对象？

引用写入会通过 Write Barrier 标记持有者所在 card。young collection 扫描 young/mid，并检查 old 与 non-moving space 中符合条件的 card，从中找到指向年轻对象的引用。

### dirty card 是否等于存在跨代引用？

不等于。dirty 表示对应地址范围发生过非空引用写入。它是保守候选，GC 还要扫描对象字段确认引用。

### 一次 GC 与 jank frame 重叠，能否直接判定 GC 导致掉帧？

不能。还要看 mutator pause、GC running/runnable、主线程状态和同一帧的其他阻塞。时间重叠是后续调查入口。

### Android 17 应用需要主动开启分代 CMC 吗？

普通应用没有稳定的公开 API 去选择 ART 收集器。选择结果由 ART、设备配置和内核能力决定。应用能做的是控制自身分配与保留行为，并用 trace 验证目标设备。

### 为什么优化后 GC 次数可能增加？

分代策略可以用更多次、成本较低的 young collection 替代 full collection。次数单独增加不代表退化，应同时比较总 GC CPU、暂停长尾、blocking GC、回收吞吐、RSS 和用户场景耗时。

## 14. 版本结论

| 版本 | 分代 GC 变化 |
| --- | --- |
| Android 8.0 | CC 成为默认收集器，提供并发压缩和 RegionTLAB |
| Android 10 | CC 默认支持分代模式，以 young collection 延后 full-heap collection |
| Android 12+ | ART Mainline 更新可把部分运行时改进下发到旧系统设备 |
| Android 17 / API 37 | CMC 支持分代 GC；AOSP tag 中可见 young/mid/old、`YoungMarkCompact` 与相关运行时条件 |

Android 17 的分代 CMC 降低了处理短命对象的平均成本，但它不会消除高分配、过度保留、CPU 争抢或显式资源管理问题；这些问题仍需用目标设备上的 trace 和 heap 数据逐项确认。

## 参考资料

- [Android 17 is Here：Generational garbage collection](https://developer.android.com/blog/posts/android-17-is-here)
- [AOSP：Debug ART garbage collection](https://source.android.com/docs/core/runtime/gc-debug)
- [AOSP：Android 8.0 ART improvements](https://source.android.com/docs/core/runtime/improvements)
- [AOSP android-17.0.0_r1：mark_compact.h](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.h)
- [AOSP android-17.0.0_r1：mark_compact.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
- [AOSP android-17.0.0_r1：heap.cc](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP android-17.0.0_r1：write_barrier-inl.h](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/write_barrier-inl.h)
- [AOSP android-17.0.0_r1：card_table.h](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/accounting/card_table.h)
- [Android 17 GKI 6.18：arm64 gki_defconfig](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/arch/arm64/configs/gki_defconfig)
- [Perfetto stdlib：android.garbage_collection](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Perfetto heap_profile 命令行](https://perfetto.dev/docs/reference/heap_profile-cli)
- [Perfetto ART Heap Dumps](https://perfetto.dev/docs/data-sources/java-heap-profiler)
