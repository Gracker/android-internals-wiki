---
title: ART GC 碎片化、Compaction 与性能诊断
chapter: 10.10
status: ready-for-review
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags: [Android, 内存性能, ART GC, 碎片化优化]
last_verified: "2026-08-09"
last_verified_against: "AOSP android-17.0.0_r1; Android 17 official release notes; Perfetto current memory profiling docs"
confidence: high
pipeline_stage: ready-for-review
task6_state: source-reworked
task9_state: ready-for-review
last_rework_at: "2026-08-09T02:51:39+08:00"
last_rework_run_id: "20260809-024950-rework-501b4554"
rework_notes: "Closed finding-64a9f0019062 by routing Android 17 ART GC Region/Compaction claims to AOSP android-17.0.0_r1 source anchors, official Android 17 GC notes, ART GC debug docs, and Perfetto memory profiling boundaries; chapter remains ready-for-review, not finalized."
last_deep_review_at: "2026-07-27T16:35:02+08:00"
last_deep_review_run_id: "20260727-163502-deep-review-501b4554"
sources:
  - type: aosp
    path: "art/runtime/gc/heap.cc"
  - type: aosp
    path: "art/runtime/gc/heap-inl.h"
  - type: aosp
    path: "art/runtime/runtime.cc"
  - type: aosp
    path: "art/runtime/gc/collector/garbage_collector.cc"
  - type: aosp
    path: "art/runtime/gc/collector/concurrent_copying.cc"
  - type: aosp
    path: "art/runtime/gc/collector/mark_compact.h"
  - type: aosp
    path: "art/runtime/gc/collector/mark_compact.cc"
  - type: aosp
    path: "art/runtime/gc/space/region_space.h"
  - type: aosp
    path: "art/runtime/gc/space/region_space.cc"
  - type: aosp
    path: "art/runtime/gc/space/bump_pointer_space.cc"
  - type: aosp
    path: "art/runtime/gc/space/large_object_space.h"
  - type: official
    path: "developer.android.com/blog/posts/android-17-is-here"
  - type: official
    path: "source.android.com/docs/core/runtime/gc-debug"
  - type: official
    path: "perfetto.dev/docs/getting-started/memory-profiling"
  - type: research
    path: "DeepResearch/2026-07-15-android17-art-markcompact-young-wrapper-source-verification.md"
---

# 10.10 ART GC 碎片化、Compaction 与性能诊断

“内存还有空闲，分配却变慢”“GC 频率突然升高”“进程 RSS 很大”经常被统称为内存碎片。这样的描述不足以支持优化决策。ART moving space、LargeObjectSpace、Native heap、虚拟地址空间和 Linux 物理页都有各自的碎片模型，处理手段也不同。

当前平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，讨论范围是 GC 碎片怎样转化为应用性能问题，以及如何用可复现证据定位。CC、CMC、RegionSpace 和 `UnevacFromSpace` 的完整源码结构见 [§4.7 ART 分代 GC、Region 碎片与暂停分析](../../part1-fundamentals/ch04-memory/07-art-generational-gc.md)；这里侧重端侧诊断和应用优化。

`RegionSpace`、`ShouldBeEvacuated()`、`YoungMarkCompact`、CMC pause、LOS 判定和 GC trace slice 的结论，以 `android-17.0.0_r1` ART 源码、Android 17 官方说明、ART GC debug 文档与 Perfetto memory profiling 文档为边界。没有实机 trace 或 benchmark 支撑的内容只用于说明排查流程，不作为量化收益或跨设备保证。

## 一、先确定“碎片”发生在哪一层

同一个进程里可能同时存在多种内存空间。某一层的 compaction 不会自动整理另一层。

| 现象或空间 | 资源管理者 | “碎片”的含义 | ART moving GC 能否处理 |
| --- | --- | --- | --- |
| CC moving space | ART `RegionSpace` | region 内死亡对象留下空洞，或 region 因搬迁收益低而保留 | CC 可搬迁适合的普通 region |
| CMC moving space | ART `BumpPointerSpace` | 存活对象之间存在可压缩空隙 | CMC 可压紧 moving space |
| LargeObjectSpace | ART LOS | 非移动空间中的空闲映射或空闲块不适合下一次大分配 | 不能由 CC/CMC 搬迁 |
| non-moving space | ART / RosAlloc | 空闲块尺寸和分布不能满足申请 | moving GC 不搬其中的对象 |
| Native heap | Scudo 或厂商 allocator | size class、span、arena、地址空间等维度的浪费 | 不能 |
| 文件映射与匿名映射 | Kernel VMA / 页表 | 地址区间、物理驻留与回收状态各不相同 | 不能 |
| Bitmap、DMA-BUF、GPU 资源 | Framework、驱动、GPU | buffer 生命周期、共享分摊或驱动私有分配 | 不能 |
| 物理页 | Linux buddy / compaction | 缺少满足某个 order 的连续物理页 | 由内核回收和页迁移处理 |

进程 RSS 上升只说明驻留页增多。它既不能证明 ART heap 发生碎片，也不能区分 live object、allocator 保留页、共享映射和图形缓冲区。诊断起点应是内存归属，随后才选择 ART、Native、Graphics 或 Kernel 工具链。

## 二、Android 17 同时保留 CC 与 CMC

### 2.1 Android 8 以来的 CC 路线

Android 官方 GC 调试文档将 Android 8 起的默认 plan 说明为 Concurrent Copying（CC）。CC 使用 read barrier 协调并发对象复制，moving space 对应 `RegionSpace`，小对象常通过 RegionTLAB 进行 bump-pointer 分配。Android 10 起，CC 支持 young collection。

这段历史不能改写成“Android 8 已经采用 Android 17 的 UFFD CMC”。两者都会移动对象，却使用不同的空间、屏障和搬迁实现。

### 2.2 Android 17 的 Generational CMC

Android 17 的官方发布说明把 Generational CMC 列为运行时改进：更频繁地处理年轻代，减少扫描稳定长生命周期对象的次数。发布说明同时指出，这项 ART 改进可以通过 Google Play 系统更新覆盖部分 Android 12 及以上设备。测试时应记录 ART Mainline 模块和设备构建，不能只比较 `SDK_INT`。

`android-17.0.0_r1` 中的 CMC moving space 是 `BumpPointerSpace`。它通过 `userfaultfd`、SIGBUS 和页级状态完成并发压缩；代码仍然保留 `MarkingPause()` 与 `CompactionPause()`。因此，“CMC 全程零 STW”不符合源码。

### 2.3 `YoungMarkCompact` 只是分代入口

下面这段源码用于确认 `YoungMarkCompact` 与主收集器的关系：

```cpp
void YoungMarkCompact::RunPhases() {
  DCHECK(!main_collector_->young_gen_);
  main_collector_->young_gen_ = true;
  main_collector_->RunPhases();
  main_collector_->young_gen_ = false;
}
```

四行逻辑临时开启主 `MarkCompact` 的 young 模式，复用同一套标记和压缩数据结构，再恢复标志。它没有独立的 marking、compaction 或 barrier 算法。`Heap::CollectGarbageInternal()` 只在启用分代 GC 且请求 `kGcTypeSticky` 时选择这个包装器；其他 CMC 收集仍使用主 `MarkCompact`。

### 2.4 应用不能指定收集器或 region

公开 Android App API 没有以下能力：

- 给某个 Java/Kotlin 对象指定 young、mid 或 old；
- 设置 `RegionSpace` region 大小；
- 把业务对象固定到某个 region；
- 请求 ART 只压缩一个 region；
- 读取每个 region 的公开稳定统计；
- 用应用 API 在 CC 与 CMC 之间切换。

系统属性、ART flags 和内核能力会影响设备的收集器配置，这些是平台与设备实现边界。普通应用可以减少分配负担、修正对象生命周期并测量结果，不应依赖私有 GC 布局。

## 三、CC 的 RegionSpace 怎样留下或回收空洞

### 3.1 256 KiB region 是空间管理单位

Android 17 的 `RegionSpace::kRegionSize` 为 256 KiB。普通对象在 region 内顺序分配；超过一个 region 的 RegionSpace 分配可以占用 large head 和 large tail。这里的 large region 仍属于 RegionSpace，与独立的 `LargeObjectSpace` 不同。

一轮 CC 搬迁前，已分配的普通 region 可能变为：

- `FromSpace`：存活对象复制到新的 to-space，完成后整个旧 region 可复用；
- `UnevacFromSpace`：对象保留原地址，本轮不整体搬迁。

`UnevacFromSpace` 可以降低复制量和目标空间需求，但死亡对象留下的洞也会继续存在。这是一项复制成本与回收收益之间的选择。

### 3.2 75% 阈值有严格的前置条件

`Region::ShouldBeEvacuated()` 定义了 `kEvacuateLivePercentThreshold = 75`，它不适用于所有 region 和所有 GC：

1. live large region 不搬迁；
2. `kEvacModeForceAll` 搬迁所有非 large region；
3. newly allocated 的非 large region 直接搬迁；
4. 只有 `kEvacModeLivePercentNewlyAllocated`、旧普通 region 且 `live_bytes_` 有效时，才比较存活字节；
5. 条件使用严格小于号，恰好 75% 不搬迁；
6. 分母是向 256 KiB region 对齐后的已分配字节。

把它简化为“region 低于 75% 就压缩”会误判 sticky GC、force-all GC、large region 和 live-byte 未知的分支。

### 3.3 低搬迁收益也可能保留内部浪费

假设某个普通 region 有较高存活率，搬走大量对象只能回收少量空间。保留它通常会减少这轮 GC 的复制流量；后续 bump-pointer 分配却不能把其中零散空洞当成一个全新 region。工作负载如果长期保留一批旧对象，又不断制造短生命周期对象，可能同时出现：

- young GC 较频繁；
- full GC 间隔变化；
- 存活对象扫描或复制成本增大；
- heap footprint 增长；
- 某些 region 内的空洞继续保留。

这些现象需要 trace 和 allocation profile 共同证明。仅凭一次 `dumpsys meminfo` 无法推导 region 的搬迁决策。

### 3.4 Debug 构建可能放大差异

`region_space.h` 把循环选择 region 的 `kCyclicRegionAllocation` 绑定到 debug build。它会减少近期 region 的复用，以便更早暴露 GC 错误，也可能增加 region 级分散。

userdebug、eng 和量产 user build 的 GC 表现不能直接横比。做性能回归时应固定设备构建、ART 模块、应用版本和负载。

## 四、CMC 怎样压紧 moving space

### 4.1 CMC 使用 BumpPointerSpace

CMC 不沿用 CC 的 RegionSpace evacuation。`MarkCompact` 计算存活对象的压缩后地址，更新引用，并按页处理 moving space。典型流程包括：

1. `InitializePhase()` 准备本轮状态；
2. `MarkingPhase()` 执行主要标记工作；
3. `MarkingPause()` 处理暂停期工作；
4. `PrepareForCompaction()` 决定并准备压缩；
5. `CompactionPause()` 完成线程根翻转与页状态准备；
6. `CompactionPhase()` 处理页和对象；
7. `FinishPhase()` 更新边界和统计。

并发阶段会消耗 CPU、内存带宽和页表操作；暂停阶段会阻塞应用线程。分析卡顿时应同时查看 pause、GC 总时长、GC 线程调度和工作线程被抢占的情况。

### 4.2 UFFD 是运行时选择，不是 API 37 保证

默认配置路径要同时考虑：

- `-Xgc` 是否显式选择收集器；
- `ro.dalvik.vm.enable_uffd_gc`；
- `persist.device_config.runtime_native_boot.enable_uffd_gc_2`；
- `persist.device_config.runtime_native_boot.force_disable_uffd_gc`；
- 内核是否满足 ART 所需的 `userfaultfd` feature；
- 设备构建与 ART 模块配置。

分代 CMC 还会读取 `use_generational_cmc` flag，以及默认值为 `true` 的 `persist.device_config.runtime_native_boot.use_generational_gc`。默认值只代表源码的缺省选择，不能代替端侧确认。

下面的命令用于采集与 CMC、分代模式直接相关的属性：

```bash
adb shell getprop ro.dalvik.vm.enable_uffd_gc
adb shell getprop persist.device_config.runtime_native_boot.enable_uffd_gc_2
adb shell getprop persist.device_config.runtime_native_boot.force_disable_uffd_gc
adb shell getprop persist.device_config.runtime_native_boot.use_generational_gc
adb shell getprop ro.dalvik.vm.force_cmc_stw_compaction
```

属性结果还要与进程启动日志、实际 GC slice 和内核返回的 UFFD 能力对照。属性存在或默认开启，都不能单独证明目标进程运行在 Generational CMC。

### 4.3 young、mid、old 是逻辑边界

Android 17 的 `MarkCompact` 在分代模式下维护 young、mid、old 三段。young collection 会处理 young 和 mid；一轮结束后，原 mid 晋升 old，本轮存活的 young 变成下一轮 mid。对象连续存活两轮相关回收后才进入 old。

这些边界位于 `BumpPointerSpace` 中，不能称为应用可配置的“young region”“old region”。把 CMC 的三代边界与 CC 的 256 KiB region 混在一起，会导出错误的对象布局和调优建议。

### 4.4 dense 前缀也会跳过低收益搬迁

Full CMC 可以把 moving space 的一段高密度前缀保留在原位，只处理后面的可压缩部分。Generational CMC 对 old 区也有相应的 dense 处理。

这个决策与 CC 的 `UnevacFromSpace` 都会减少低收益搬迁，但判断单位、空间实现和引用更新机制不同。诊断文案不应把两者统一称为 “Region selective compaction”。

### 4.5 16 KiB 页改变页处理粒度

Android 17 的 RegionSpace 仍以 256 KiB 为 region 大小：

- 4 KiB 页设备每个 region 对应 64 页；
- 16 KiB 页设备每个 region 对应 16 页。

CMC 广泛使用运行时 `gPageSize` 处理页状态、压缩缓冲和 UFFD 范围。页大小变化会改变处理粒度和页表行为，却不能独立推出 GC 更快、碎片更少或 RSS 必然降低。比较实验要固定 ABI、构建、对象分布和业务输入。

## 五、LargeObjectSpace 是另一条诊断路径

### 5.1 达到 12 KiB 不代表一定进入 LOS

Android 17 的默认和最小 large-object threshold 都是 12 KiB。`Heap::ShouldAllocLargeObject()` 还要求对象属于 primitive array 或 `String`。普通对象即使超过阈值，也不能只按大小断言它进入 LOS。

LOS 的 `CanMoveObjects()` 固定返回 `false`。CC 和 CMC 都不会搬迁其中的对象。大量不同尺寸的 `byte[]`、`char[]`、其他 primitive array 或大字符串，可能把性能问题带到 non-moving 的 LOS，而 moving-space compaction 无法消除这部分碎片。

### 5.2 LOS 初次失败可能回退普通 allocator

`heap-inl.h` 的大对象分配路径允许在 LOS 初次失败后清除本次异常，并用普通 allocator 重试。源码注释把严重虚拟地址空间碎片列为 LOS 先失败的一种可能原因。

这个回退会让“对象大小”和“最终所在空间”的关系更加复杂。分析应以端侧空间统计、heap dump 和源码条件为准，避免仅根据对象类型猜测。

### 5.3 OOM 日志也有空间边界

`RegionSpace` 和 `BumpPointerSpace` 可以在特定分配失败路径中报告最大连续可分配范围。LOS 的 `LogFragmentationAllocFailure()` 没有提供同等语义，`Heap::ThrowOutOfMemoryError()` 对 LOS 也跳过这类输出。

因此，某次 OOM 日志没有“largest possible contiguous allocation”不代表没有碎片；看到这条信息时，也要确认失败的 allocator 类型。

## 六、怎样采集可解释的 GC 证据

### 6.1 一次快照回答不了时间问题

GC 性能问题至少包含三条时间序列：

- 对象分配速率和峰值；
- GC 的类型、频率、暂停与总耗时；
- 帧、启动、输入或业务任务的延迟。

Heap dump 适合回答“哪些对象仍然可达、由谁持有”。ART allocation profile 适合回答“哪些调用栈持续创建对象”。Perfetto system trace 适合回答“GC 何时运行、应用线程何时被暂停或抢占”。三个问题不能互相替代。

### 6.2 用 SIGQUIT 查看累计 GC timing

调试环境中可以向目标进程发送 SIGQUIT，让 ART 把累计 GC timing 连同线程信息写入 ANR trace：

```bash
pid=$(adb shell pidof com.example.app)
adb shell kill -s QUIT "$pid"
adb shell ls -lt /data/anr | head
```

输出中搜索 `Dumping cumulative Gc timings`。各 collector 的 phase histogram、pause histogram、累计时间和回收量适合判断长期趋势；SIGQUIT 本身会产生诊断扰动，也不能提供帧级因果关系。

不要把这条命令放进线上应用流程。它面向开发和系统诊断环境，文件读取权限也会受设备构建与权限限制。

### 6.3 用 Perfetto 对齐 GC 与卡顿

采集包含应用调度、frame timeline、ART 和内存相关数据的 trace 后，可以先用下面的查询列出线程轨道上的 GC 候选 slice：

```sql
SELECT
  s.ts,
  s.dur,
  s.name,
  t.name AS thread_name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t USING (utid)
WHERE lower(s.name) GLOB '*gc*'
   OR lower(s.name) GLOB '*concurrent*copy*'
   OR lower(s.name) GLOB '*mark*compact*'
ORDER BY s.dur DESC;
```

查询只做候选筛选。Slice 名称属于实现和构建细节，不是稳定 API；应回到时间轴核对 track、线程、嵌套 phase 和目标应用，再解释结果。

`GarbageCollector::Run()` 创建的总 slice 名称由 GC cause、collector name 和 `GC` 组成。不同设备可能出现 young、full、Concurrent Copying 或 Mark Compact 等名称。不要把旧教程中的一个固定字符串写成跨版本 SQL 契约。

### 6.4 `Majflt-GC` 与 `Minflt-GC` 的边界

Android 17 的 `MarkCompact::TraceFaults()` 记录两个 atrace counter：

- `Majflt-GC`：GC 线程的 major fault，可包含文件读取或 ZRAM 解压；
- `Minflt-GC`：GC 线程的 minor fault，例如 COW 和匿名页分配。

源码明确说明，这两个 counter 只统计 GC 线程资源使用，不覆盖 userfault。看到 `Majflt-GC` 增长，应继续检查 swap、ZRAM、文件回读与系统内存压力，不能据此锁定某个 CMC 目标页。

### 6.5 先分离 ART、Native 与 Graphics

建议至少同时保存以下证据：

| 证据 | 主要回答的问题 |
| --- | --- |
| `dumpsys meminfo <package>` | Java、Native、Graphics、Code、Stack 等大类怎样变化 |
| `/proc/<pid>/smaps_rollup` | 进程 RSS、PSS、匿名页、文件页和 swap 汇总 |
| ART heap dump | 当前可达对象、retained size 和引用链 |
| ART allocation profile | Java/Kotlin 分配热点与分配速率 |
| Native heap profile | `malloc`/`free` 调用栈及存量变化 |
| Perfetto system trace | GC、调度、frame、fault 与业务区间的时间关系 |
| DMA-BUF / GPU 统计 | 图形和共享 buffer 是否增长 |

如果 Java heap 稳定而 Graphics 或 DMA-BUF 增长，应转到 [§10.8 GPU / 图形内存统计与实战监控](08-gpu-memory-tracking.md)。如果 Native heap 增长，应使用 Native allocation profile；调用 `System.gc()` 不会释放 native 泄漏。

## 七、一套可复现的排查流程

### 7.1 固定实验条件

每轮比较都记录：

- 设备型号、内存容量和页大小；
- Android build fingerprint、API level 与 ART Mainline 模块版本；
- user、userdebug 或 eng 构建；
- 应用版本、ABI、是否可调试或 profileable；
- 冷启动、热启动、账号和数据集状态；
- 操作脚本、循环次数与采样窗口；
- 屏幕刷新率、温度和供电状态。

Generational CMC 可通过 ART 模块更新覆盖旧平台。缺少模块版本时，“Android 16 对 Android 17”的对比可能混入不同 runtime 实现。

### 7.2 建立稳定负载

对内存增长或 GC 抖动，使用可重复的业务循环，例如：

1. 打开同一列表；
2. 加载固定数量与尺寸的图片；
3. 进入详情并返回；
4. 清理业务缓存或等待同样的空闲时长；
5. 重复若干轮。

采样窗口应覆盖预热、稳态和压力上升阶段。只截取一次高点，无法区分首次缓存、持续泄漏和周期性 GC。

### 7.3 先判断对象是否仍然存活

若 heap dump 显示同一批业务对象在每轮操作后继续被 GC root 引用，优先处理生命周期或缓存上限。Compaction 只会移动存活对象，不会让仍可达对象消失。

若 live set 稳定而 allocation profile 显示高分配速率，重点检查 churn：短命对象虽能回收，仍会增加 young GC、扫描、复制和调度成本。

若 Java live set 与分配速率都稳定，再检查 Native、Graphics、映射、swap 和系统内存压力。

### 7.4 区分 pause、总 GC 工作和 mutator 干扰

建议分别统计：

- 每类 GC 次数；
- pause 的分布和最大值；
- GC wall time 与 GC thread CPU time；
- 每轮 freed bytes、scanned bytes 和吞吐；
- 业务窗口的分配字节与对象数；
- 主线程 runnable 延迟和 frame deadline miss；
- Java heap、进程 RSS、PSS 与 swap 的趋势。

短 pause 不保证业务没有受影响。并发 GC 仍会竞争 CPU、缓存和内存带宽；系统压力高时，GC 线程和应用线程还可能遭遇调度延迟或换页。

### 7.5 一次只验证一个假设

可执行的实验形式包括：

- 把某个解析阶段的临时数组合并或分批，观察分配速率与 young GC 是否同步下降；
- 给业务缓存设置明确容量，观察 live set、RSS 和命中率；
- 把大 buffer 的尺寸分布改为少量规格，观察 LOS 或 Native allocator 行为；
- 延后非必要预加载，观察启动窗口的分配峰值与 frame timeline；
- 在相同 ART 配置上比较优化前后，避免把设备 GC 差异当成代码收益。

结论应同时包含收益和代价。缓存缩小可能增加 I/O 或解码；对象复用可能增加常驻内存和状态错误；批处理可能降低分配频率，却抬高单次峰值。

## 八、应用侧优化原则

### 8.1 减少高频短命分配

适合优先检查的模式包括：

- 热循环中的临时集合、迭代器、装箱和字符串拼接；
- JSON、protobuf 或数据库读取中的中间 `byte[]`；
- 图片变换链上的重复像素 buffer；
- 每帧创建的绘制参数、路径、`Matrix` 或事件对象；
- Compose 或 View 列表中因状态不稳定产生的重复对象；
- JNI 边界上的重复数组复制和 wrapper。

优化目标是降低业务关键窗口的分配量和峰值，不是追求“零对象”。现代 ART 的小对象分配很快；为了减少几个对象引入共享可变状态、复杂池化或锁竞争，可能得不偿失。

### 8.2 管好长生命周期对象

旧对象会增加 full collection 的扫描范围，也可能通过引用链保留大量短命对象。应重点检查：

- 无上限内存缓存；
- 静态集合持有 Activity、View 或大对象图；
- 长生命周期 coroutine、listener、callback 和 observer；
- 任务队列中排队过久的闭包与参数；
- 页面退出后仍保留的适配器、图片请求或渲染对象；
- 失败重试队列没有淘汰策略。

修复引用生命周期通常比讨论 region 阈值更有效。对象仍可达时，任何 moving collector 都必须保留它。

### 8.3 大数组和字符串要看尺寸分布

大 primitive array 与大 `String` 可能进入 LOS。比起只统计总字节，更有用的数据包括：

- 分配调用栈；
- 尺寸直方图；
- 同一时间的并发存量；
- 生命周期与复用间隔；
- 失败后是否触发普通 allocator 回退；
- Java 与 Native 是否各保存一份副本。

固定少量 buffer 规格有时能改善复用，但过大的共享 buffer 会抬高常驻内存。复用策略要用实际峰值、并发数和延迟验证。

### 8.4 谨慎使用对象池

对象池适合创建成本高、状态可可靠重置、并发模型清晰且收益已测量的对象。对普通小对象，池化可能带来：

- 对象存活时间变长；
- old generation 扩大；
- 清理遗漏和脏状态；
- 锁或原子操作开销；
- 缓存容量失控。

先用 allocation profile 确认热点，再设计有硬上限的池，并比较 GC、RSS 和业务延迟三项结果。

### 8.5 不用 `System.gc()` 充当通用修复

显式 GC 只是请求运行时执行回收。它不能释放仍可达对象、Native 泄漏、DMA-BUF 或 GPU 私有资源，也不能保证目标设备采用某种 compaction。

在交互路径频繁调用还可能增加暂停和 CPU 消耗。若某个离线阶段需要显式回收，应以目标设备实验说明触发时机、延迟代价和收益，不要把它写成通用最佳实践。

## 九、常见场景怎样归因

### 9.1 图片列表越滑越卡

建议按以下顺序检查：

1. heap dump 中 Bitmap wrapper、Drawable、View 和请求对象是否仍被持有；
2. allocation profile 中解码、变换和列表绑定是否产生大量临时数组；
3. `dumpsys meminfo` 的 Java、Native、Graphics 怎样变化；
4. Perfetto 中 GC 是否与 frame deadline miss 重叠；
5. 图片库缓存上限、预取距离和目标尺寸是否符合页面需求。

硬件 Bitmap 的像素资源不应只按 Java heap 判断。若 Graphics 或 DMA-BUF 上升，继续检查图形内存链路。

### 9.2 JSON 或 protobuf 解析出现周期性停顿

常见证据是解析窗口内分配大量字符串、集合节点和临时 `byte[]`，随后出现 young GC。可以尝试流式解析、减少中间模型、避免重复编码转换、复用有明确上限的读取 buffer。

仍需检查 live set。若解析结果被历史页面或缓存长期保留，降低临时分配只能缓解 churn，不能解决堆持续增长。

### 9.3 相机或媒体会话切换后内存不降

相机会同时涉及 Java wrapper、Native codec、GraphicBuffer、DMA-BUF 和驱动资源。ART heap dump 只能覆盖其中一部分。应把 `ImageReader`、`Image.close()`、Surface 生命周期、codec release、GPU/DMA-BUF 统计和 native profile 放在同一时间线上。

单独触发 GC 后 Java heap 下降，不能证明整条媒体资源链已经释放。

### 9.4 端侧推理时 GC 和 RSS 同时升高

模型权重常位于文件映射或 Native buffer；Java/Kotlin 层还会创建张量 wrapper、形状数组、字符串和调度对象。应分别衡量：

- 模型映射和 Native buffer；
- 输入输出 primitive array；
- wrapper 与任务对象的分配速率；
- young/full GC 的暂停和 CPU；
- swap、major fault 与推理尾延迟。

把模型总大小直接换算成 RegionSpace 存活率没有依据。先确认每类内存的 owner 和生命周期。

## 十、版本边界

| 版本范围 | 阅读重点 |
| --- | --- |
| Android 8～9 | 官方默认 CC；不要套用 Android 17 的 CMC 分代实现 |
| Android 10～16 | CC 已有分代能力；具体 collector、属性和 ART Mainline 更新需按设备确认 |
| Android 17 / API 37 | AOSP 包含 Generational CMC、`YoungMarkCompact`、young/mid/old 边界和 UFFD CMC 路径 |

Android 17 官方说明还指出，Generational CMC 改进可通过 ART Mainline 更新到部分 Android 12 及以上设备。版本演进文章可以保留旧版本事实，但当前结论的最高平台锚点应为 `android-17.0.0_r1`。厂商分支和后续 Mainline 模块必须单独记录版本。

这些结论不依赖 Android 18/API 38+ 行为。涉及 Linux 物理页碎片、direct reclaim 或内核 compaction 时，应切换到 `android17-6.18-2026-06_r6` 的内核证据，参见 [§4.10 内存规整与 Direct Reclaim](../../part1-fundamentals/ch04-memory/10-memory-compaction-direct-reclaim.md)。

## 十一、复核清单

遇到“GC 碎片化”结论时，逐项确认：

- [ ] 已区分 ART moving space、LOS、Native、Graphics、映射和物理页；
- [ ] 已确认目标进程运行的 collector 与 GC 类型；
- [ ] 没有把 CC RegionSpace 与 CMC BumpPointerSpace 混写；
- [ ] 没有把 75% 当成所有 region 的通用压缩阈值；
- [ ] 没有把 `YoungMarkCompact` 描述成独立 GC 算法；
- [ ] 已分别衡量 pause、GC 总工作和业务延迟；
- [ ] 已用 heap dump 判断 live set，用 allocation profile 判断 churn；
- [ ] 已记录 build fingerprint、ART 模块、页大小和构建类型；
- [ ] 性能收益来自同设备、同负载的可复现实验；
- [ ] 优化没有用 `System.gc()`、无上限对象池或私有属性掩盖问题。

## 参考资料

- [AOSP `heap.cc`：collector 创建、选择与累计 GC timing](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP `heap-inl.h`：LOS 判定与分配路径](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP `garbage_collector.cc`：GC slice、pause 和统计](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/garbage_collector.cc)
- [AOSP `region_space.cc`：75% 条件与 evacuation 决策](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/space/region_space.cc)
- [AOSP `mark_compact.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.h)
- [AOSP `mark_compact.cc`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
- [AOSP `large_object_space.h`](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/space/large_object_space.h)
- [Android 17 is Here：Generational garbage collection](https://developer.android.com/blog/posts/android-17-is-here)
- [AOSP：Debug ART garbage collection](https://source.android.com/docs/core/runtime/gc-debug)
- [Perfetto：Profiling memory usage and allocations](https://perfetto.dev/docs/getting-started/memory-profiling)
