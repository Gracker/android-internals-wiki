---
title: "内存抖动与频繁 GC"
chapter: "10.6"
section: "10.6"
status: "finalized"
polish_count: 1
polish_date: "2026-04-09"
polish_by: "task2b-polish"
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1（ART collector_type.h、runtime.cc、heap.cc、mark_compact.cc、region_space.cc；BinderInternal.java）/ Android Common Kernel android17-6.18-2026-06_r6（fs/userfaultfd.c、mm/mremap.c）/ Perfetto heapprofd 与 ART allocation profiling 文档 / Android Studio Java/Kotlin allocation recording / Compose Runtime 1.12.0-rc01 release notes / Compose strong skipping 与 performance best practices / Kotlin value class 文档"
verified_note: "Android 17/API 37 分代 CMC 基线已锚定 android-17.0.0_r1；2026-07-09 deep-tech-review 抽检确认 platform/art 与 frameworks/base 均已有 android-17.0.0_r1 tag，关键 CMC/GcWatcher 符号存在"
confidence: high
pipeline_stage: "ready-to-publish"
sources:
- type: material
  path: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md
- type: official
  path: developer.android.com/studio/profile/record-java-kotlin-allocations
- type: official
  path: developer.android.com/topic/performance/memory
- type: official
  path: perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: source.android.com/docs/core/runtime/gc-debug
- type: aosp
  path: android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector_type.h
- type: aosp
  path: android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/runtime.cc
- type: aosp
  path: android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc
- type: aosp
  path: android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc
- type: kernel
  path: android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/userfaultfd.c
- type: kernel
  path: android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/mremap.c
- type: official
  path: developer.android.com/jetpack/androidx/releases/compose-runtime
- type: official
  path: developer.android.com/develop/ui/compose/performance/stability/strongskipping
- type: official
  path: developer.android.com/develop/ui/compose/performance/bestpractices
- type: official
  path: developer.android.com/reference/kotlin/androidx/compose/runtime/MutableIntState
- type: reference
  path: kotlinlang.org/docs/inline-classes.html
tags: "[\"memory\", \"gc\", \"churn\", \"object-pool\", \"tlab\", \"autoboxing\", \"heapprofd\"]"
related_chapters: "[\"4.3\", \"7.1\", \"7.2\", \"10.1\", \"10.4\"]"
word_count: "~7500"
reviewed_date: "2026-07-10"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"  # 2026-07-10 revisiting review pass
task6_state: "reviewed"
task6_reviewed_date: "2026-07-10"
last_task6_at: "2026-07-10T01:09:00+08:00"
last_task6_audit: "2026-07-10"
last_task6_review_log: "logs/review/2026-07-10-01-review.md"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-07-10"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-10T12:30:03+08:00"
last_task9_audit: "2026-07-09"
task9_review_notes: "2026-07-10 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1；ART CMC/GcWatcher 与 heapprofd 主线复核通过；量化性能数据作为 P2 建议补一手 benchmark；queue 无 pending，自动晋升 finalized。"
task2b_state: "fixed"
task2b_result: "fixed"
task2b_rework_date: "2026-05-08"
task2b_fixed_at: "2026-05-08T04:51:42.168874+08:00"
last_task2b_at: "2026-07-09T22:52:12+08:00"
last_task2b_lite_at: 2026-06-22
review_notes: "2026-04-24 task6 re-review (revisiting): pass-light-edit. Task2b修复heapprofd命令和版本边界后内容无新L1/L2问题。GC版本拆分准确，代码示例规范，优化建议实用。Task9仍有needs-rework待重审。评分: 结构5/5·措辞4/5·一致性5/5·验证4/5·元数据5/5。 | 2026-05-08 Task6 05:05：revisiting→reviewed；修复 frontmatter/source YAML、无语言围栏和禁用/口语化表述，无新增 L3/L4 回炉项，待 Task9 复审。 | 2026-05-08 Task9 05:27：pass-tech-review。P0 0 / P1 0 / P2 3；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-09 23:25 Task2B Verifier：状态修正 status=finalized 与 pipeline_stage=task6_pending 矛盾；Task2B 已修复 (t2b_state=fixed) 但 status 阻止 Task6 拾取。status: finalized→ready-for-review，章节已正确回流 Task6。"
last_task9_review_log: "logs/deep-review/2026-07-10-12-deep-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-18
updated_by: "openclaw-task9"
updated_date: "2026-07-10"
last_task9_autofix_at: "2026-07-10"
finalized_date: "2026-07-10"
finalized_by: "openclaw-task9-auto-promote"
---

# 10.6 内存抖动与频繁 GC

内存抖动描述的是高频分配与回收，不等同于内存泄漏。泄漏对象长期可达，堆基线不断抬升；抖动对象通常很快失去引用，堆曲线反复上升和回落。两种现象也可能同时存在，例如一个页面既在每帧创建临时对象，又把少量对象留在错误的生命周期里。

一次 GC 事件也不能直接判定卡顿。诊断要证明三件事：目标场景的分配速率异常、GC 或分配等待与慢帧时间重叠、减少热点分配后同场景指标改善。

## 从分配到慢帧发生了什么

### 分配快，不代表分配免费

ART 为小对象提供线程本地分配快路径。Android 8 以来的 Concurrent Copying（CC）可使用 RegionTLAB；Android 17 的 Concurrent Mark-Compact（CMC）在启用 TLAB 时使用 TLAB allocator。线程在自己的缓冲区内推进指针时，不需要争用堆的全局锁。

对象仍有后续成本：

- TLAB 或 RegionTLAB 用尽后需要补充空间。
- 分配会增加标记、扫描和回收工作量。
- 活对象越多，收集器需要处理的引用越多。
- 大对象或突发分配更容易离开最轻的分配路径。
- 回收线程会消耗 CPU 和内存带宽，与 UI 线程、RenderThread 竞争。
- 可分配空间不足时，发起分配的线程可能等待 GC 完成。

120 Hz 屏幕的理论帧间隔约为 8.33 ms。GC 暂停、分配等待或 CPU 竞争只要与已经接近预算的帧重叠，就可能产生 missed frame。暂停时间没有跨设备通用常量，不能用“某类 GC 固定耗时几毫秒”代替 trace。

### Android 17 的 CMC 源码边界

Android 17 `collector_type.h` 将 `kCollectorTypeCMC` 定义为 **Concurrent mark-compact**。`heap.cc` 在 `gUseUserfaultfd` 为真时校验前台收集器为 CMC、后台收集器为 CMCBackground；启用 generational GC 时，还会创建 `YoungMarkCompact`。`runtime.cc` 对 generational GC 的选择同时检查 collector 能力、`-Xgc` 选项和 `ShouldUseGenerationalGC()`。

这几处源码说明 Android 17 具备 CMC 与 generational CMC 路径。源码中存在 `YoungMarkCompact`，不代表每台 Android 17 设备、每个进程都使用同一运行参数。OEM 配置、ART Mainline 模块和进程选项仍可能影响选择；取证时可从 ART 启动日志中的 collector 描述核对当前进程。

CMC 的 `mark_compact.cc` 检查 `UFFD_FEATURE_SIGBUS` 与 `MREMAP_DONTUNMAP`，并实现 `SigbusHandler()` 处理压缩期间的页面访问。kernel 侧对应实现锚定 `android17-6.18-2026-06_r6` 的 `fs/userfaultfd.c` 与 `mm/mremap.c`。该机制用于缩短并发压缩对 mutator 的阻塞范围，却没有消除 GC 工作量。应用持续制造短命对象时，年轻代回收、CPU 占用和 allocation stall 仍然需要测量。

## 识别抖动、泄漏与正常波动

| 现象 | 常见曲线 | 优先证据 | 主要处理方向 |
| --- | --- | --- | --- |
| 短命对象抖动 | 分配量快速增长，GC 后大幅回落 | allocation call stack、GC 时间、慢帧重叠 | 降低分配次数或单次大小 |
| 引用泄漏 | 多轮 GC 后存活基线持续抬升 | heap dump、Retained Size、GC Root | 修正引用所有权 |
| 缓存或对象池增长 | 上升后停在容量上限 | 容量、命中率、逐出记录 | 校准容量和失效策略 |
| 大对象突发 | 单次或少数分配拉高曲线 | 分配大小、调用栈、业务事件 | 复用 buffer、分块或移出关键路径 |
| 正常预热 | 启动阶段增长，随后稳定 | 类加载、资源初始化、后续稳态 | 通常不改，保留基线 |

“锯齿形”只是线索。若每次 GC 后基线也在上升，需要同时排查存活对象；若分配很高但帧时间、CPU 和 GC 等待没有退化，优化优先级可以后移。

## 常见分配热点

### `onDraw()`、布局和动画回调

每帧回调会放大一次分配。`Paint`、`Path`、`Rect`、数组、Lambda 和临时集合都应通过 allocation profile 验证，不能只按代码外观猜测。

下面的示例用于说明如何把可复用的绘制状态移出 `onDraw()`。

```kotlin
class MeterView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {
    private val barPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.RED
    }
    private val barBounds = RectF()

    override fun onDraw(canvas: Canvas) {
        barBounds.set(0f, 0f, width.toFloat(), height.toFloat())
        canvas.drawRect(barBounds, barPaint)
    }
}
```

`Paint` 与 `RectF` 只在 View 创建时分配，帧回调只更新字段。若绘制状态会跨线程使用，复用对象还要满足线程所有权要求。

### 循环、列表绑定与流式转换

循环内部创建集合、正则、格式化器或中间 DTO，会按元素数放大。Kotlin collection pipeline 也可能创建中间集合；Sequence 能减少部分中间集合，但它有迭代器和间接调用成本，短小集合未必受益。

修复时先问三个问题：

- 中间结果是否必须保存？
- 容器能否移到循环外并通过 `clear()` 复用？
- 能否提供预估容量，减少数组扩容与复制？

复用容器前要确认调用不会把容器引用保存到异步任务或返回值中。误用同一实例会引入数据覆盖和并发错误。

### 字符串与日志

循环中的 `result += item` 会反复生成新的 String 内容。日志参数也会在调用前求值，日志方法内部再判断开关已经来不及避免参数构造。

下面的示例把多次不可变字符串拼接改成一次 builder 构造。

```kotlin
fun joinNames(items: List<String>): String = buildString {
    items.forEachIndexed { index, item ->
        if (index > 0) append(", ")
        append(item)
    }
}
```

返回 String 本身仍会分配；这段代码减少的是循环内重复复制。高频日志可在调用点检查日志级别，或使用接收 Lambda 的延迟日志 API，确保禁用日志时不构造文本。

### 装箱

泛型集合、可空原始类型和接口调用可能把 `Int`、`Long` 等值装箱。JVM 对部分数值有 wrapper cache，编译器也可能消除一些临时对象，因此“每次装箱必定分配”过于绝对。

在已确认的热点中可评估以下替代：

| 当前结构 | 候选结构 |
| --- | --- |
| `HashMap<Int, T>` | `SparseArray<T>` |
| `HashMap<Int, Int>` | `SparseIntArray` |
| `HashMap<Int, Long>` | `SparseLongArray` |
| `HashMap<Long, T>` | `LongSparseArray<T>` |
| `List<Int>` 的密集数值计算 | `IntArray` |

`SparseArray` 以排序后的原始类型 key 数组工作，能省去 key 装箱；它与哈希表的查找、插入特征不同。数据规模和更新模式必须通过 benchmark 决定，不能按“元素超过某个数量”设置统一切换点。

### 大型 buffer 与图像

相机、编解码、Bitmap 和序列化常产生大数组或 native buffer。此类问题的 Java 对象数可能不高，allocation bytes 却很大。优化方向包括固定数量的 buffer 轮转、按目标尺寸解码、分块处理和遵守库的 buffer pool 所有权。

Android 8.0（API 26）起 Bitmap 像素位于 native heap。图片库管理的 Bitmap 应归还给库自己的池；业务代码不要在未知调用方仍可能使用 Bitmap 时提前 `recycle()`。

## 用证据定位

### Android Studio：记录 Java/Kotlin 分配

Android Studio 的 “Track Memory Consumption (Java/Kotlin Allocations)” 可以显示分配类型、大小、线程、调用栈和释放时间。完整记录本身会减慢高分配应用；官方工具提供 sampled 模式降低影响。

一次有效的录制应满足：

1. 在可重复的用户动作前开始录制。
2. 只保留足以覆盖该动作的时间窗。
3. 分别按 Allocations、Allocation Size 与 Total Count 排序。
4. 回到调用栈，确认对象来自业务路径还是 profiler、框架预热。
5. 修复后在同设备、同构建类型、同数据集下复测。

分析 churn 时关注时间窗内累计分配次数与字节数；分析泄漏时关注结束时仍存活的数量、大小和引用关系。两个问题不应使用同一排序口径。

### Perfetto heapprofd：调用栈采样

heapprofd 从 Android 10 起支持 native malloc/free 分配分析。Android 12 起可把 heap 指定为 `com.android.art`，记录 Java allocation call stack。ART allocation profile 只记录对象创建位置，不提供对象删除时间或完整引用图；heap dump 才用于存活对象的引用关系。

下面两条命令展示当前 Perfetto 脚本的 native 与 ART 入口。

```bash
# Native malloc/free allocation profile
tools/heap_profile android -n com.example.app

# Java allocation profile（Android 12+）
tools/heap_profile android -n com.example.app --heaps com.android.art
```

user build 只允许分析 manifest 标记为 `debuggable` 或 `profileable` 的 App。Java profile 里的 `Total allocation size` 和 `Total allocation count` 包含采样期间的累计分配，即使对象稍后已经回收；不能把它们当作当前存活堆大小。分配突发还可能让共享缓冲区溢出，Perfetto 会提前结束 profile，此时需要提高 sampling interval 或按官方建议调整缓冲区。

### Perfetto：把分配、GC 和帧放进同一窗口

系统 trace 至少应包含调度、频率、Frame Timeline 与 ART/应用 trace。分析顺序如下：

1. 从 missed frame 或业务事件确定时间窗。
2. 检查 UI 线程是否暂停、Runnable 但未获调度，或等待分配。
3. 对齐 GC slice、`HeapTaskDaemon` 活动和 CPU 频率。
4. 用 allocation profile 找到同一场景的高频调用栈。
5. 排除锁竞争、I/O、Binder、thermal throttling 等并发原因。

`HeapTaskDaemon` 活跃且附近出现慢帧，只能说明时间相关。线程状态、GC slice 和修复前后对照共同成立，因果判断才可靠。

### 不要在 App 中复制 `GcWatcher`

Android 17 的 `BinderInternal.GcWatcher` 仍通过 `WeakReference` 与 `finalize()` 感知 GC，并向 framework 内部 watcher 分发回调。`BinderInternal` 属于隐藏 API，finalization 的执行时间也没有确定性。应用不应复制这种模式做线上 GC 计数，更不应把 watcher 的 `finalize()` 当作每次 GC 的精确通知。

开发期使用 Android Studio、Perfetto 和 ART 日志；线上只保留经过开销评估的场景指标。Android 17 的 `ProfilingManager` 可提供受系统控制的 profile artifact，但同样不构成实时 GC 回调 API。

## 优化策略

### 优先删除分配

收益最高且风险较低的改动通常是：

- 把逐帧创建的绘制对象变为 View 或 renderer 的成员。
- 移除不必要的中间集合和 DTO。
- 给已知规模的数组、集合、builder 设置合理初始容量。
- 让相机、音视频与网络 buffer 按清晰所有权复用。
- 关闭的日志在调用点跳过字符串与参数构造。
- 密集数值路径使用原始类型数组，减少泛型装箱。

预分配会把成本移到更早的时间，并增加对象存活期。启动路径已经紧张或对象很少使用时，预分配可能让结果变差；应在目标场景基准中评估。

### 对象池是受约束的优化

Android framework 的 `Message.obtain()`、`MotionEvent.obtain()` 等 API 使用池化，因为对象创建频繁、状态可重置且所有权协议明确。业务对象只有满足相似条件时才适合入池：

- profiler 已确认分配点占据显著成本；
- 对象构造或 backing storage 昂贵；
- 同时在用的实例数有稳定上限；
- `acquire/release` 所有权能被审查；
- 每个字段都能可靠重置；
- 池命中率、容量与内存占用可观测。

池会延长对象存活期，也可能增加同步、清理和泄漏风险。小型不可变对象或构造很便宜的对象通常交给 ART 更合适。池大小不能照搬 16、32 等经验数字，应由并发峰值和命中率决定。

### 不调用 `System.gc()` 治理抖动

`System.gc()` 只是向虚拟机提出 GC 请求，既不保证立即执行，也不消除分配源。主动请求可能把回收安排到用户操作期间。测试工具可在明确目的下触发 GC；产品代码应修正分配速率、生命周期和容量。

## Kotlin value class 的边界

`@JvmInline value class` 在 JVM 上可用底层值表示，适合给原始类型增加类型安全，同时避免部分 wrapper。下面的类型在直接参数和局部变量路径上通常可用 `long` 表示。

```kotlin
@JvmInline
value class UserId(val raw: Long)
```

Kotlin 官方文档明确列出需要装箱的场景：作为泛型类型、接口类型或 nullable value class 使用。`List<UserId>`、`Comparable<UserId>` 参数和 `UserId?` 都可能产生 wrapper。value class 是减少特定路径装箱的工具，不会自动让泛型集合变成原始类型存储；高频数值处理仍可评估 `LongArray`。

## Jetpack Compose 中的分配

Compose Runtime 通过 SlotTable/LinkTable、RecomposeScope 和 snapshot state 保存组合结构。结构本身会占用内存；业务更常见的 churn 来自重组时重复执行的构造代码、不断变化的参数身份和不必要的状态派生。

### `remember` 解决的是重组期重建

在 composable 中直接创建集合、格式化器或状态对象，会在该代码重新执行时创建新实例。需要跨重组保存的对象可用 `remember(keys)` 缓存，并让 key 精确描述对象何时失效。

下面的示例让 formatter 只在 locale 改变时重建。

```kotlin
@Composable
fun PriceText(
    price: BigDecimal,
    locale: Locale,
) {
    val formatter = remember(locale) {
        NumberFormat.getCurrencyInstance(locale)
    }
    Text(formatter.format(price))
}
```

`remember` 会延长对象在 composition 中的存活时间，不适合缓存无限增长的数据。key 过于频繁变化时，缓存会反复失效；key 缺失时，又可能读到与新输入不匹配的旧对象。

### strong skipping 减少无效重组

Kotlin 2.0.20 起默认启用 Compose strong skipping。启用后，restartable composable 可被标记为 skippable，具有 unstable capture 的 Lambda 也会被编译器记忆。参数比较规则仍有差异：unstable 参数使用实例相等，stable 参数使用对象相等。

不要为了跳过重组随意添加 `@Stable`。它是一份行为契约：公开属性变化必须能被 Compose 感知，`equals()` 也要满足约定。错误标注可能让 UI 漏掉更新。可通过 Compose compiler reports 检查稳定性推断，再优化频繁重组的节点。

### `derivedStateOf` 有适用条件

`derivedStateOf` 适合输入变化频率高、输出变化频率低的场景，例如滚动位置持续变化，而按钮只关心“是否离开列表顶部”。它本身有维护依赖和计算状态的成本；两个输入每次变化都要求更新拼接结果时，直接计算通常更简单。

Compose 官方示例把 `derivedStateOf` 放在 `remember` 中。Compose Runtime 1.12.0-beta01 修复了一个潜在保留问题：未正确 remember 的 derived state 在 forward write 路径上可能被 composition 持有到销毁。该修复已包含在 2026-07-29 发布的 1.12.0-rc01；生产升级仍要遵循团队对 RC/稳定版的依赖政策。

### 原始类型 state

计数器等状态可使用 `mutableIntStateOf()`、`mutableLongStateOf()` 等原始类型 state API，并通过 `intValue`、`longValue` 访问，减少 `MutableState<Int>` 在 JVM 路径上的装箱机会。仍需用 allocation profile 验证热点；UI 状态读写频率和重组范围通常比单个 wrapper 更值得先看。

### Compose 与 Android 17 的版本关系

Compose 通过 AndroidX 发布，不跟 platform API 一一绑定。Compose Runtime 1.12.0-alpha01 把库的 compileSdk 更新到 API 37，并要求至少 AGP 9.2.0；这属于构建依赖边界，不能据此推断 Android 17 设备拥有专属的 SlotTable、LinkTable 或 Lazy list GC 行为。

## 验证优化

优化前后使用同一套脚本和数据：

| 维度 | 建议指标 |
| --- | --- |
| 分配 | 每次业务操作的 allocation count、allocation bytes、热点调用栈占比 |
| GC | 事件次数、暂停区间、blocking GC/allocation wait、GC 线程 CPU |
| 帧 | Frame Timeline 的 missed frame、帧时长分位数 |
| 资源 | Java heap、native heap、graphics、RSS/PSS 与 CPU 频率 |
| 正确性 | 对象池状态、并发、画面、数据一致性和生命周期 |

只比较峰值 heap 容易漏掉“总分配量下降但存活集上升”。只比较 GC 次数也会受 heap 上限、收集器和设备配置影响。目标场景的分配、GC、帧时间与正确性同时验收，结论才可复用。

## 排查清单

- 高分配发生在启动、滚动、动画、相机、编解码还是后台任务？
- 对象是短命、长期存活，还是被缓存/池持有？
- 排序依据是 allocation count、bytes 还是 live objects？
- 慢帧时间窗内是否存在 GC pause、allocation wait 或 GC CPU 竞争？
- profiler 自身是否改变了应用速度或内存分类？
- `onDraw()`、循环和日志是否仍有可移出的对象构造？
- 装箱是否经过 allocation call stack 证实？
- 对象池是否有容量、重置、所有权和并发规则？
- Compose 的 `remember` key、参数身份和重组范围是否符合预期？
- 修复后是否在相同构建、设备、数据和操作脚本下复测？

## 与其他章节的关系

- **4.3 ART 虚拟机内存管理**：CC、CMC、TLAB、RegionTLAB 与 GC 日志。
- **7.1/7.2 卡顿分析**：Frame Timeline、线程状态与 CPU 竞争。
- **10.1 App 内存分析**：Java、native、graphics 与 mmap 的分类工具。
- **10.2 内存泄漏**：存活对象、GC Root 与引用所有权。
- **10.3 内存持续增长**：缓存、pool、碎片和虚拟地址空间。
- **10.4 低内存影响**：进程内 GC 与整机回收压力的区别。
- **10.5 案例集**：MemoryThrashing 的平台边界与差分采样。

## 参考资料

- [Android Studio：Record Java/Kotlin allocations](https://developer.android.com/studio/profile/record-java-kotlin-allocations)
- [Android Developers：Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [AOSP：Debug ART garbage collection](https://source.android.com/docs/core/runtime/gc-debug)
- [Perfetto：Callstack-based allocation profiling](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP `collector_type.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector_type.h)
- [AOSP `runtime.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/runtime.cc)
- [AOSP `heap.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/heap.cc)
- [AOSP `mark_compact.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/collector/mark_compact.cc)
- [AOSP `region_space.cc`（android-17.0.0_r1）](https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1/runtime/gc/space/region_space.cc)
- [AOSP `BinderInternal.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/BinderInternal.java)
- [Android Common Kernel `fs/userfaultfd.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/fs/userfaultfd.c)
- [Android Common Kernel `mm/mremap.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/mremap.c)
- [Android Developers：SparseArray](https://developer.android.com/reference/android/util/SparseArray)
- [Kotlin：Inline value classes](https://kotlinlang.org/docs/inline-classes.html)
- [Compose：Strong skipping mode](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)
- [Compose：Performance best practices](https://developer.android.com/develop/ui/compose/performance/bestpractices)
- [Compose Runtime：MutableIntState](https://developer.android.com/reference/kotlin/androidx/compose/runtime/MutableIntState)
- [Compose Runtime release notes](https://developer.android.com/jetpack/androidx/releases/compose-runtime)
