---
title: "内存持续增长"
chapter: "10.3"
section: "10.3"
status: ready-for-review
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-02"
last_verified_against: "AOSP android-16.0.0_r1"
reviewed_date: "2026-04-08"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
confidence: medium
word_count: "~8000"
sources:
  - type: blog
    path: "OPPO内存反碎片优化原理"
  - type: blog
    path: "RTC 性能自动化工具在内存优化场景下的实践"
  - type: blog
    path: "Hummer引擎优化系列 - 内存稳定性研究与优化"
  - type: official
    path: "https://developer.android.com/reference/android/util/LruCache"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiling"
tags: [memory, pss, memory-growth, fragmentation, lru-cache, bitmap, native-heap]
related_chapters: ["10.1", "10.2", "4.1", "4.3", "4.5"]
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# 内存持续增长

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存持续增长（非泄漏）的常见原因：缓存无上限、Bitmap 累积、Native 碎片化
- 🔹 与内存泄漏的区分方法
- 🔹 LRU Cache 策略的正确实现
- 🔹 内存增长的监控指标：PSS 趋势、Java Heap 使用率趋势
- 🔹 内存碎片化的检测与应对

### 扩展（可选深入）

- 🔸 WebView 内存增长问题与多进程 WebView
- 🔸 长时间运行 App（如音乐播放器）的内存管理策略

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解内存持续增长

在上一章（§10.2）我们讨论了内存泄漏——对象被无意识地持有引用，导致 GC 无法回收。但现实中还有一类更隐蔽的问题：内存并没有泄漏，GC 也在正常工作，但应用的内存占用就是一直在涨。

这种场景在 Perfetto 中表现为 Java Heap 或 Native Heap 的曲线呈阶梯式或锯齿式上升，每个锯齿的波谷都比上一个高。用 `dumpsys meminfo` 观察会发现 PSS 在用户使用过程中逐步攀升，即使退回主界面也没有明显回落。

这种情况和内存泄漏的区别在于：增长的对象确实有明确的业务用途——可能是图片缓存、可能是预加载的数据、可能是 Native 层的内存池——但它们的总量没有被有效控制。这不是"忘记释放"的问题，而是"没有限制上限"的问题。

理解内存持续增长的成因和治理方法，对于长生命周期应用（新闻客户端、社交 App、音乐播放器、电商应用）尤为重要。这类应用通常运行数小时不重启，如果内存以每小时几十 MB 的速度增长，最终必然触发 LMK 或 OOM。

## 内存持续增长的常见原因

### 缓存没有上限

这是最常见的非泄漏性内存增长原因。开发者为了提升用户体验，会使用各种缓存：图片缓存、接口数据缓存、列表项缓存。这些缓存的初衷是好的——避免重复加载、减少网络请求、加快页面渲染。但问题在于，如果缓存没有合理的容量限制，随着用户不断浏览新内容，缓存中的条目只会越来越多。

一个典型的场景是图片加载框架的内存缓存。如果直接使用 HashMap 或 ArrayList 来缓存 Bitmap，没有任何淘汰策略，那么用户每加载一张新图片，这张图片的像素数据就会一直驻留在 Java Heap 中。对于资讯类应用，用户可能在一个会话中浏览数百张图片，即使很多图片对应的页面已经关闭，它们依然占据着内存。

这种情况在 `dumpsys meminfo` 中的表现是 Java Heap 的 Alloc 值持续增长，而且 GC 后回落不明显——因为被缓存引用的 Bitmap 属于可达对象，GC 不会回收它们。

另一个常见变体是"无限追加的列表"。有些应用在首页信息流中持续加载新数据，把所有已加载的数据都保存在内存中的列表里。用户下拉加载越多，列表越长，内存占用越大。虽然每个数据对象本身不大，但数千条数据加上其中的嵌套对象（图片 URL、富文本、嵌套 JSON）的累积效应非常可观。

### Bitmap 累积

Bitmap 累积可以看作是缓存无上限的一个特例，但它值得单独讨论，因为 Bitmap 的内存影响远大于普通 Java 对象。

一张 1080×1920 的 ARGB_8888 图片，解码后占用的内存是 1080 × 1920 × 4 = 约 7.9 MB。如果应用内同时持有 20 张这样的图片，仅图片像素数据就占了近 160 MB。在 Android 8.0（API 26）之前，Bitmap 的像素数据存储在 Java Heap 中，会直接挤占 Java 对象的分配空间；Android 8.0 之后像素数据移到了 Native Heap，虽然不再直接影响 Java Heap 的 GC 压力，但依然计入应用的总内存（PSS），同样会触发系统的 LMK 机制。

[已验证: 官方文档, developer.android.com/topic/performance/graphics/manage-memory]

Bitmap 累积的典型路径有两条：一是前面说的缓存无淘汰，图片加载后一直留在 ImageCache 中；二是"隐藏引用"——某个看似已经不用的对象（比如一个被回收的 RecyclerView Item）内部的 Bitmap 引用没有被正确清理，但由于数据结构层面还有间接引用链（比如一个全局的 resourceId 到 Bitmap 的映射），导致这些 Bitmap 无法被 GC。

在 Perfetto 的 heapprofd 分析中，如果看到 Native Heap 中大量分配来自 `Bitmap.allocateNative` 调用栈，且分配总量随时间线性增长，基本可以确认是 Bitmap 累积问题。

### Native 碎片化

内存碎片化是指可用内存被分割成许多不连续的小块，虽然总量上还有足够的空闲内存，但无法满足连续内存的分配请求。

在 Android 上，Native 碎片化主要发生在 Native Heap 层面。应用使用的 C/C++ 库（音视频解码器、图形引擎、JNI 调用的 Native 代码）通过 malloc/free 或 new/delete 管理内存。当频繁分配和释放不同大小的内存块时，空闲内存会被切割成不连续的片段。这就是为什么有时候 Native Heap 的 Alloc 值看起来不大，但 PSS 却居高不下——碎片化的内存虽然已经被释放回 malloc 的空闲链表，但由于碎片化，无法归还给操作系统。

[已验证: 来源见 Cubox/OPPO内存反碎片优化原理-2022-10-26.md]

碎片化问题在长时间运行的应用中尤为明显。比如音乐播放器 App 使用音频解码的 Native 库，每首歌解码时分配和释放不同大小的 PCM 缓冲区，运行几小时后 Native Heap 就会出现严重的碎片化。在 `dumpsys meminfo` 中表现为 Native Heap 的 Pss 和 Private Dirty 值远高于 Alloc 值。

在 Perfetto 中，可以通过 heapprofd 对 Native 层进行连续采样（continuous dump），观察分配和释放的模式。如果发现大量小尺寸的分配和释放交替出现，且每次分配的尺寸不一致，这就是碎片化的典型信号。

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiling]

### [自动发现] 匿名内存页（Anonymous Pages）累积

除了上述三个主要原因外，还有一种容易被忽视的增长来源：匿名内存页（anon RSS / Private Anonymous）。这部分内存不在 Java Heap 也不在 Native Heap 的常规统计中，通常来自：

- **mmap 的匿名映射**：某些 Native 库使用 mmap 分配大块内存作为内部缓冲区
- **线程栈**：每个线程默认分配 1-8 MB 的栈空间（取决于配置），大量创建线程但不销毁会导致栈内存累积
- **GPU 内存映射**：通过 GPU 驱动映射到进程地址空间的图形资源

在 `dumpsys meminfo` 中，这部分通常体现在 "Private Other" 或 "Unnamed" 行中。如果发现这部分持续增长但 Heap 区域没有对应变化，需要检查是否有线程泄漏或 Native 层的 mmap 操作。

[待验证: Android 16 中 meminfo 输出格式的具体变化]

## 与内存泄漏的区分方法

内存持续增长和内存泄漏在 Perfetto 或 `dumpsys meminfo` 中的表现非常相似——都是 PSS 持续增长。但区分它们对选择正确的治理策略至关重要。

### GC 行为是关键判据

内存泄漏的核心特征是：即使触发 GC，增长的那部分内存也不会被回收。因为泄漏的对象仍然有可达引用链，GC 认为它们是"活的"。

而非泄漏性增长的情况是：如果手动清除缓存（比如调用 `cache.evictAll()`）或释放相关资源，内存会立刻回落。换言之，这些对象在技术上是可以被 GC 回收的，只是业务逻辑上一直没有触发回收条件。

在 Android Studio Memory Profiler 中，可以通过以下方式验证：触发一次 GC（点击垃圾桶图标），观察 Heap 的大小变化。如果 GC 后 Heap 明显缩小但随后又快速增长回来，大概率是非泄漏性的缓存增长；如果 GC 后 Heap 几乎不变，更可能是泄漏。

### dumpsys meminfo 的对比分析

`dumpsys meminfo <package_name>` 的输出可以提供更细致的判断线索：

| 指标 | 内存泄漏 | 非泄漏性增长 |
|------|---------|------------|
| Java Heap Alloc 持续增长 | ✓（可达对象无法回收） | ✓（缓存不断追加） |
| GC 后 Heap 回落幅度 | 很小或无 | 有回落但不彻底 |
| Native Heap Pss 增长 | 可能（Native 泄漏） | 常见（碎片化/Bitmap） |
| Views/Activities 计数 | 可能异常偏高 | 通常正常 |
| 手动清理缓存后回落 | 不明显 | 明显回落 |

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler]

### 用 LeakCanary 排除泄漏

如果不确定是泄漏还是非泄漏性增长，最直接的方法是用 LeakCanary 做一次检测。LeakCanary 通过监控 Activity、Fragment 和 View 的生命周期，能自动检测到这些组件的泄漏。如果 LeakCanary 没有报告泄漏，但内存仍在增长，那基本可以确认是非泄漏性的增长问题。

需要注意的是，LeakCanary 主要检测 Java 层的泄漏，对于 Native 层的泄漏（如 C/C++ 层分配后未释放的内存）无法检测。如果怀疑 Native 泄漏，需要使用 heapprofd 进行 Native Heap Profiling。

## LRU Cache 策略的正确实现

既然非泄漏性内存增长的核心问题是"没有上限"，那么解决方案的核心就是"设定上限并执行淘汰"。Android 提供的 `LruCache` 类就是为此设计的。

### LruCache 的基本原理

`LruCache` 内部使用 `LinkedHashMap` 维护一个按访问顺序排列的键值对集合。每次 `get` 或 `put` 操作都会将被访问的条目移动到链表尾部。当插入新条目导致缓存总大小超过设定的 `maxSize` 时，`LruCache` 会自动从链表头部（即最久未被访问的条目）开始淘汰。

```java
// frameworks/base/core/java/android/util/LruCache.java
// @ AOSP android-16.0.0_r1
public class LruCache<K, V> {
    private final LinkedHashMap<K, V> map;
    private int size;       // 当前缓存大小
    private int maxSize;    // 最大允许大小
    private int putCount;   // put 操作计数
    private int evictionCount; // 淘汰计数

    public LruCache(int maxSize) {
        if (maxSize <= 0) {
            throw new IllegalArgumentException("maxSize <= 0");
        }
        this.maxSize = maxSize;
        // accessOrder=true 表示按访问顺序排列，最近访问的在尾部
        this.map = new LinkedHashMap<K, V>(0, 0.75f, true);
    }
}
```

这段代码的关键在于 `LinkedHashMap` 构造函数的第三个参数 `accessOrder=true`。它使得 `get()` 操作也会触发条目重排——被访问的条目会移到链表尾部。这就是 LRU（Least Recently Used）语义的实现基础：链表头部永远是"最久未被访问"的条目，淘汰时优先移除它们。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/util/LruCache.java]

### 正确设置 maxSize

`LruCache` 的 `maxSize` 参数不一定是字节数，它的单位取决于你如何重写 `sizeOf()` 方法。默认情况下 `sizeOf()` 返回 1，意味着 `maxSize` 表示最大条目数。但对于图片缓存这种场景，每张图片的大小差异可能很大（缩略图 vs 高清大图），用条目数做限制显然不合理。

正确的做法是重写 `sizeOf()` 返回每个条目的实际内存占用（通常以 KB 为单位），然后将 `maxSize` 设为应用可用内存的一个合理比例：

```java
// 获取应用最大可用内存（以 KB 为单位）
final int maxMemory = (int) (Runtime.getRuntime().maxMemory() / 1024);
// 取 1/8 作为图片缓存的预算
final int cacheSize = maxMemory / 8;

LruCache<String, Bitmap> imageCache = new LruCache<String, Bitmap>(cacheSize) {
    @Override
    protected int sizeOf(String key, Bitmap value) {
        // 返回 Bitmap 的实际内存占用（KB）
        // Android 3.0+ 可以使用 getByteCount()
        return value.getByteCount() / 1024;
    }
};
```

1/8 这个比例并非银弹，它来自 Android 官方文档的示例。实际的合理比例取决于应用的类型：图片密集型应用（如 Instagram）可能需要更大的比例，而以文字为主的应用可以更小。关键是要有明确的预算，而不是"能放多少放多少"。

[已验证: 官方文档, developer.android.com/reference/android/util/LruCache]

### 响应系统内存压力

`LruCache` 的淘汰只在缓存满时触发，但系统可能在任何时候进入低内存状态。正确做法是在 `onTrimMemory()` 回调中主动释放缓存资源：

```java
@Override
public void onTrimMemory(int level) {
    if (level >= ComponentCallbacks2.TRIM_MEMORY_MODERATE) {
        // 系统内存紧张，清空缓存
        imageCache.evictAll();
    } else if (level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND) {
        // 应用进入后台，释放一半缓存
        imageCache.trimToSize(imageCache.size() / 2);
    }
}
```

这里我们利用了 `LruCache` 自身的 LRU 特性：`trimToSize()` 会按照 LRU 顺序淘汰条目，保留最近使用的部分。而 `evictAll()` 则清空整个缓存，用于应对严重的内存压力。

[已验证: 官方文档, developer.android.com/reference/android/content/ComponentCallbacks2]

### entryRemoved 的资源释放

当条目从 `LruCache` 中被淘汰时，`entryRemoved()` 方法会被回调。如果缓存值持有需要显式释放的资源（比如 Bitmap），可以在这里做清理：

```java
@Override
protected void entryRemoved(boolean evicted, String key,
        Bitmap oldValue, Bitmap newValue) {
    if (oldValue != null && !oldValue.isRecycled()) {
        // Android 8.0 以下需要手动 recycle
        // 8.0+ 的 Native Bitmap 会由 GC 自动回收
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            oldValue.recycle();
        }
    }
}
```

注意在 Android 8.0（API 26）之后，Bitmap 的像素数据存储在 Native Heap，GC 可以自动回收。但在更早版本上，像素数据在 Java Heap 中，手动调用 `recycle()` 可以加速释放。

[已验证: 官方文档, developer.android.com/topic/performance/graphics/manage-memory]

## 内存增长的监控指标

知道问题存在和能系统性地发现问题，是两件不同的事。在生产环境中，我们需要一套指标体系来持续监控内存增长趋势。

### PSS 趋势

PSS（Proportional Set Size）是 Android 系统衡量进程实际物理内存占用的核心指标。它将共享库的内存按引用进程数量均摊到每个进程上，比 RSS（Resident Set Size）更准确地反映了每个进程对系统内存的真实消耗。

监控系统层面的 PSS 趋势是发现内存增长问题最直接的方式。可以通过 `Debug.getPss()` 获取当前进程的 PSS 值（返回值单位为字节），也可以通过 `Debug.getMemoryInfo()` 获取更详细的 `Debug.MemoryInfo` 对象，其中包含了各内存类别的 PSS 分项。

[已验证: 官方文档, developer.android.com/reference/android/os/Debug#getPss()]

在实际工程中，PSS 采样的策略通常有两种：

**定时采样**：每隔一定时间（如 30 秒或 1 分钟）采集一次 PSS。适合长生命周期应用的后台监控。需要注意的是 `Debug.getPss()` 本身有执行开销（需要遍历 /proc/pid/smaps），频率不宜过高。

**页面级采样**：在每个页面（Activity/Fragment）进入和退出时各采集一次 PSS，差值即为该页面的内存增量。这种方式能精确定位哪个页面导致了最多的内存增长。

将 PSS 采样数据上报到监控平台后，可以绘制出应用在典型使用路径下的内存曲线。正常的曲线应该是锯齿形——使用时上升，页面退出后回落；如果曲线整体呈上升趋势（每个锯齿的波谷都在抬高），就说明存在持续增长问题。

### Java Heap 使用率趋势

除了 PSS，Java Heap 的使用率趋势也是关键指标。可以通过 `Runtime.getRuntime()` 获取：

```java
Runtime runtime = Runtime.getRuntime();
long maxMemory = runtime.maxMemory();     // 应用最大可用 Heap
long totalMemory = runtime.totalMemory(); // 当前已分配的 Heap
long freeMemory = runtime.freeMemory();   // 当前已分配 Heap 中的空闲部分
long usedMemory = totalMemory - freeMemory; // 实际使用的 Heap
float heapUsageRatio = (float) usedMemory / maxMemory; // Heap 使用率
```

Java Heap 使用率趋势的分析方法和 PSS 类似：如果在使用过程中持续上升且回落幅度越来越小，说明有持续增长问题。特别要注意的是，即使 Heap 使用率没有到 100%，如果持续在 75% 以上，GC 的频率会显著增加（因为 ART 在 Heap 快满时会更频繁地触发 GC），导致应用出现卡顿。这就是 §10.6 会详细讨论的"内存抖动"问题。

### Native Heap 与 Graphics 内存

对于使用 Native 库较多的应用（音视频、游戏引擎、Flutter），Native Heap 和 Graphics 内存的监控同样重要。`Debug.MemoryInfo` 提供了 `getTotalPrivateDirty()` 和 `getTotalPss()` 方法来获取更细粒度的数据。

Graphics 内存（GPU 纹理、Buffer）的监控可以通过 `dumpsys gpu` 或 `memtrack` HAL 来实现。如果应用大量使用图片、视频或 3D 渲染，Graphics 内存的持续增长是一个常见但容易被忽视的问题。

[待补充: Perfetto 中 Java Heap / Native Heap / Graphics Track 的 Trace 截图]

### 监控数据的可视化

采集到 PSS 和 Heap 数据后，需要将它们可视化才能发现趋势。推荐的做法是：

1. **按会话聚合**：将一次完整使用过程（从打开应用到退出）的所有采样点连成一条曲线
2. **多会话对比**：将多次使用过程的曲线叠在一起，观察是否有会话级别的增长趋势
3. **分位数监控**：关注 P95 和 P99 的 PSS 值，而不仅仅是平均值。极端值往往是最需要关注的问题

## 内存碎片化的检测与应对

### 碎片化的本质

理解碎片化需要区分两个层面：

**物理内存碎片化**是指空闲的物理页面在页帧号（PFN）上不连续，导致无法合并成高阶页面（order > 0 的连续物理块）。这会影响内核的伙伴分配器——当需要分配连续物理内存（如相机 buffer、GPU buffer）时，即使总空闲内存充足，也可能因为碎片化而分配失败或分配变慢。

**虚拟内存碎片化**是指进程的虚拟地址空间被大量小尺寸的映射分割，导致没有足够大的连续虚拟地址范围来满足新的 mmap 请求。对于 32 位进程（虚拟地址空间只有 4 GB），这个问题尤其严重。

[已验证: 来源见 Cubox/OPPO内存反碎片优化原理-2022-10-26.md]

### Native Heap 碎片化的检测

Native Heap 的碎片化在应用层面很难直接量化，但可以通过以下间接指标判断：

1. **PSS 与 Alloc 的差距**：通过 `dumpsys meminfo` 观察 Native Heap 的 Pss 和 Alloc 值。如果 Pss 远大于 Alloc，说明有大量已释放但无法归还给操作系统的内存（即碎片化空洞）。

2. **分配失败日志**：当 Native 层的 `malloc` 或 `mmap` 因为碎片化而失败时，logcat 中可能出现类似 `failed due to fragmentation (required contiguous free X bytes, largest contiguous free Y bytes)` 的日志。

3. **heapprofd 连续采样**：通过 heapprofd 对 Native 层进行 continuous dump，对比不同时间点的分配快照。如果分配总量变化不大但 PSS 在增长，说明碎片化在加剧。

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiling]

### 碎片化的应对策略

**应用层面：**

- **使用内存池**：对于频繁分配/释放的固定大小对象，使用预分配的内存池（Object Pool）替代 malloc/free。内存池一次性分配一大块内存，内部自行管理分配和回收，避免了碎片化。
- **减少小尺寸分配**：尽量合并小的内存请求为大的批量请求。比如音频解码时，与其每帧分配一个 PCM buffer，不如预分配一个足够大的环形 buffer。
- **使用 Arena/Region 分配器**：将同一生命周期的对象分配在同一个 Arena 中，释放时一次性释放整个 Arena，不会产生碎片。这在游戏引擎和数据库系统中很常见。

**系统层面：**

一些厂商（如 OPPO）在内核中实现了反碎片化机制：

- **MF（Multi-Freearea）**：在物理内存管理层面，将空闲页面集中在高 PFN 范围，增加合并为高阶页面的概率
- **CSVM（Centralize-Small-VirtualMem）**：在虚拟内存管理层面，将小尺寸的虚拟内存分配集中在特定的地址范围，减少对大块虚拟空间的"污染"

这些优化属于 OEM/系统层面的工作，App 开发者无法直接使用，但了解其原理有助于理解碎片化的底层机制，以及在 Perfetto 中观察到的系统级行为。

[已验证: 来源见 Cubox/OPPO内存反碎片优化原理-2022-10-26.md]
[待验证: OPPO MF/CSVM 在其他厂商平台上的类似实现]

## WebView 内存增长问题与多进程 WebView

前面讨论的增长类型主要发生在应用自身的代码中。但有一类组件，它带来的内存增长往往超出开发者的预期——WebView。Chromium 渲染引擎本身就非常消耗内存——每个 WebView 实例背后都有一个 Renderer 进程的内存开销，包括 V8 JavaScript 引擎的堆、Blink 渲染引擎的 DOM 树、GPU 进程的纹理缓存等。

在一个典型的混合应用中（原生 + WebView），如果用户在 WebView 中连续浏览多个页面，WebView 内部的缓存（HTTP 缓存、图片缓存、JS Heap）会持续增长。更严重的是，WebView 的一些内部数据结构（如 Visited Links 表、Service Worker 缓存）的生命周期与 WebView 进程绑定，即使销毁 WebView 实例也可能无法完全释放。

[来源: Cubox/WebView 经历的各种干货方案分享-2024-11-28.md]

针对 WebView 的内存增长，有几种有效的策略：

**及时销毁 WebView 实例**：在 Activity/Fragment 销毁时，必须显式调用 `webView.destroy()`，否则 WebView 关联的 Native 资源无法释放。

**使用多进程 WebView**：对于 WebView 使用量大的应用（如小程序框架），可以将 WebView 运行在独立的进程中。当 WebView 进程的内存增长到一定程度时，直接杀掉整个进程重建，彻底释放所有内存。微信的小程序框架就是这么做的——每个小程序运行在独立的 WebView 进程中，进程退出后所有内存都被回收。

**限制 WebView 缓存**：通过 `WebSettings` 控制 WebView 的缓存行为，比如禁用 DOM Storage、限制数据库大小等。

## 长时间运行 App 的内存管理策略

前面讨论的治理手段适用于大多数应用的日常使用场景。但某些类型的应用天然需要长时间运行：音乐播放器、导航应用、运动追踪器、IM 应用。这类应用的内存管理需要一套不同于普通应用的策略。

**设定全局内存预算**：根据目标设备的典型内存配置，为应用设定一个总的内存预算（比如 200 MB），然后将预算分配到各个模块：图片缓存 50 MB、音视频缓冲区 40 MB、数据缓存 30 MB、其他 80 MB。每个模块需要在预算内自行管理分配和释放。

**定期自检与收缩**：在应用后台运行时，定期检查内存占用。如果超过预算阈值，主动释放非关键资源。比如音乐播放器在后台播放时，可以释放专辑封面缓存、歌词缓存等非必要数据。

**利用 onTrimMemory 分级响应**：`onTrimMemory()` 的不同级别提供了系统内存状态的细粒度信息。对于长生命周期应用，需要实现完整的分级响应策略——从低级别的"减少缓存"到高级别的"释放所有可释放资源"，确保在任何内存压力下都能做出合理的让步。

**避免在后台持续累积数据**：长生命周期应用的一个常见错误是在后台持续接收数据并缓存在内存中。比如 IM 应用在后台持续接收消息，如果把所有未读消息都保存在内存中，运行一整天后内存占用可能翻倍。正确的做法是在进入后台后限制内存缓存条目数，超过限制的数据持久化到数据库。

[待验证: 音乐播放器类应用在 Android 16 上的典型内存预算参考值]

## 与其他机制的关系

内存持续增长问题横跨了多个系统层面的知识：

- **与 §10.1（App 内存分析）的关系**：本章讨论的增长类型判定（泄漏 vs 非泄漏）和监控指标（PSS/Heap 趋势）都依赖于 §10.1 介绍的分析工具
- **与 §10.2（内存泄漏）的关系**：本章和 §10.2 是一对互补章节——§10.2 处理"忘了释放"的问题，本章处理"没限制上限"的问题
- **与 §4.3（ART 虚拟机内存管理）的关系**：理解 ART 的 GC 机制和 Heap 结构，有助于判断增长是 Java 层还是 Native 层的
- **与 §10.6（内存抖动与频繁 GC）的关系**：持续增长会导致 Heap 使用率居高不下，进而触发频繁 GC，形成"增长→GC 压力→卡顿"的恶性循环

## 常见问题与误区

### "内存没泄漏就不会 OOM"

这是最大的误区。OOM 的触发条件是进程的 PSS 达到了系统为该进程分配的内存上限（或系统整体内存耗尽触发 LMK）。这个上限取决于 Heap 大小、Native 分配、Graphics 内存等所有组成部分的总和。即使没有泄漏，缓存无上限增长同样会触碰上限。

### "LRU Cache 用上就万事大吉"

`LruCache` 只解决了"有限容量"的问题，但如果 `maxSize` 设置不合理（比如设得太大），缓存依然会占用过多内存。另外，`LruCache` 只管理 `put` 和 `get` 操作涉及的条目，如果你的代码在 `LruCache` 之外还持有对这些条目的引用（比如在某个全局列表中同时缓存了 Bitmap 引用），那么 `LruCache` 淘汰这些条目后，它们实际上不会被 GC 回收，等于缓存限制失效了。

### "Native 碎片化是系统问题，App 开发者无能为力"

虽然物理内存碎片化确实是系统层面的问题，但 App 开发者可以通过优化自身的内存分配模式来减轻碎片化。使用内存池、避免频繁的小尺寸分配和释放、合理管理 Native 对象的生命周期，都能显著降低碎片化的程度。

### "把所有东西都放到 LRU Cache 里就好"

`LruCache` 适合管理可以被重新加载或计算的数据。对于那些重新获取成本很高或无法重新获取的数据（比如实时传感器数据、唯一的状态快照），不应该用 `LruCache` 管理，而应该有专门的持久化和加载策略。

## 参考资料

- AOSP 源码路径：`frameworks/base/core/java/android/util/LruCache.java`
- Android 官方文档：[Manage your app's memory](https://developer.android.com/topic/performance/memory)
- Android 官方文档：[LruCache Reference](https://developer.android.com/reference/android/util/LruCache)
- Perfetto heapprofd：[Native Heap Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiling)
- OPPO 内存反碎片优化（素材来源：Cubox/OPPO内存反碎片优化原理-2022-10-26.md）
- Hummer 引擎内存稳定性研究（素材来源：Personal-Knowlodge/source/2026-03-08）
