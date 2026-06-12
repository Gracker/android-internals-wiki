---

title: 内存持续增长
chapter: '10.3'
section: '10.3'
status: finalized
drafted_date: '2026-04-02'
drafted_by: openclaw-task2a
applicable_versions: Android 8.0 (API 26) - Android 16 (API 36)
last_verified: '2026-04-02'
last_verified_against: AOSP android-16.0.0_r1
reviewed_date: "2026-05-27"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: '2026-04-08'
polish_by: task2b-polish
confidence: medium
word_count: ~8000
sources:
- type: blog
  path: OPPO内存反碎片优化原理
- type: blog
  path: RTC 性能自动化工具在内存优化场景下的实践
- type: blog
  path: Hummer引擎优化系列 - 内存稳定性研究与优化
- type: official
  path: https://developer.android.com/reference/android/util/LruCache
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiling
tags:
- memory
- pss
- memory-growth
- fragmentation
- lru-cache
- bitmap
- native-heap
related_chapters:
- '10.1'
- '10.2'
- '4.1'
- '4.3'
- '4.5'
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: "pass-light-edit"
task9_state: reviewed
task2b_result: "fixed-lite"
task2b_state: fixed
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-28"
last_task9_at: "2026-06-13T03:24:38+08:00"
last_task6_at: "2026-05-27T23:15:00+08:00"
last_task6_audit: '2026-06-08'
last_task6_audit_result: l1-clean
last_task9_audit: "2026-06-13"
last_task2b_lite_at: "2026-05-27"
last_task6_review_log: "logs/review/2026-05-27-23-review.md"
last_task9_autofix_at: "2026-06-13"
task6_review_notes: "2026-05-27 23:15 Task6：revisiting 写作复审通过；L1/L2 小修 3 项（删除正文编辑标记 2 处，压缩否定-纠正式句式 1 处）；无新增 L3/L4 回炉项。"
last_task9_review_log: "logs/deep-review/2026-06-13-03-audit.md"
task9_review_notes: "2026-06-13 03:20 Task9 闲时抽检：AUTO-FIX Bitmap 缓存像素数据 Java Heap/Native Heap 版本边界；回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
---

# 内存持续增长

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存持续增长（非泄漏）的常见原因：缓存无上限、Bitmap 累积、Native 碎片化
- 🔹 与内存泄漏的区分方法
- 🔹 LRU Cache 策略的正确实现
- 🔹 内存增长的监控指标：PSS / RSS 趋势、Java Heap 使用率趋势
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

上一章（§10.2）讨论的是内存泄漏——对象被无意识地持有引用，导致 GC 无法回收。但现实中还有一类更隐蔽的问题：内存并没有泄漏，GC 也在正常工作，应用的内存占用却一直在涨。

这种场景在 Perfetto 中表现为 Java Heap 或 Native Heap 的曲线呈阶梯式或锯齿式上升，每个锯齿的波谷都比上一个高。用 `dumpsys meminfo` 观察会发现 PSS 在用户使用过程中逐步攀升，即使退回主界面也没有明显回落。

这种情况和内存泄漏的区别在于：增长的对象有明确的业务用途——可能是图片缓存、可能是预加载的数据、可能是 Native 层的内存池——但它们的总量没有被有效控制。问题集中在容量上限缺失。

理解内存持续增长的成因和治理方法，对于长生命周期应用（新闻客户端、社交 App、音乐播放器、电商应用）尤为重要。这类应用通常运行数小时不重启，如果内存以每小时几十 MB 的速度增长，最终可能先撞到 Java Heap 上限、Native / 虚拟地址分配失败，或在系统内存压力下提高被 lmkd 回收的概率。

## 内存持续增长的常见原因

### 缓存没有上限

这是最常见的非泄漏性内存增长原因。开发者为了提升用户体验，会使用各种缓存：图片缓存、接口数据缓存、列表项缓存。这些缓存的初衷是好的——避免重复加载、减少网络请求、加快页面渲染。但问题在于，如果缓存没有合理的容量限制，随着用户不断浏览新内容，缓存中的条目只会越来越多。

一个典型的场景是图片加载框架的内存缓存。如果直接使用 HashMap 或 ArrayList 来缓存 Bitmap，没有任何淘汰策略，那么用户每加载一张新图片，Bitmap 对象及缓存索引会留在 Java Heap 中；对本章覆盖的 API 26+，像素数据主要留在 Native Heap、RSS 和 PSS 中。对于资讯类应用，用户可能在一个会话中浏览数百张图片，即使很多图片对应的页面已经关闭，它们依然占据着内存。

这种情况在 `dumpsys meminfo` 中的表现是 Java Heap 的 Alloc、Native Heap、RSS 或 PSS 随缓存规模增长，而且 GC 后回落不明显——因为被缓存引用的 Bitmap 属于可达对象，GC 不会回收它们。

另一个常见变体是"无限追加的列表"。有些应用在首页信息流中持续加载新数据，把所有已加载的数据都保存在内存中的列表里。用户下拉加载越多，列表越长，内存占用越大。虽然每个数据对象本身不大，但数千条数据加上其中的嵌套对象（图片 URL、富文本、嵌套 JSON）会逐步抬高 Java Heap 和 PSS。

### Bitmap 累积

Bitmap 累积可以看作是缓存无上限的一个特例，但它值得单独讨论，因为 Bitmap 的内存影响远大于普通 Java 对象。

一张 1080×1920 的 ARGB_8888 图片，解码后占用的内存是 1080 × 1920 × 4 = 约 7.9 MB。如果应用内同时持有 20 张这样的图片，仅图片像素数据就占了近 160 MB。Bitmap 像素数据的存放位置有明确版本边界：Android 2.3.3（API 10）及以下在 Native 内存，Android 3.0 到 7.1（API 11-25）在 Dalvik Heap，Android 8.0（API 26）及以上在 Native Heap。对本章覆盖的 API 26+，Bitmap 累积主要抬高 Native Heap、RSS 和 PSS；它不会直接吃掉 Java Heap 上限，但会增加 Native 分配失败风险，并在系统内存压力下提高被 lmkd 选择的概率。

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

### 匿名内存页（Anonymous Pages）累积

除了上述三个主要原因外，还有一种容易被忽视的增长来源：匿名内存页（anon RSS / Private Anonymous）。这部分内存不在 Java Heap 也不在 Native Heap 的常规统计中，通常来自：

- **mmap 的匿名映射**：某些 Native 库使用 mmap 分配大块内存作为内部缓冲区
- **线程栈**：每个线程会保留一段栈虚拟地址空间，实际 RSS / PSS 取决于被触碰的栈页；大量线程或深调用栈会抬高匿名页占用
- **GPU 内存映射**：通过 GPU 驱动映射到进程地址空间的图形资源

在 `dumpsys meminfo` 中，这部分通常体现在 "Private Other" 或 "Unnamed" 行中。如果发现这部分持续增长但 Heap 区域没有对应变化，需要检查是否有线程泄漏或 Native 层的 mmap 操作。

16KB 页面设备上的 `meminfo` 粒度更粗，匿名映射尾页的浪费也更容易抬高 `Private Other` 一类条目。跨设备比对这类指标前，先确认页大小。

增长源确认后，下一步要定位具体来源。排查 Unnamed / Private Other 增长时，`dmabuf_dump -b` 可以先覆盖 DMA-BUF 这一类来源。它能按 buffer 尺寸和进程归属列出当前系统中所有 DMA-BUF 的物理占用，帮助确认匿名页增长是否来自图形 buffer。操作步骤：

1. `adb shell dmabuf_dump -b` 获取全系统 DMA-BUF 快照
2. 按进程名过滤目标 App，看其名下的 buffer 尺寸分布
3. 如果发现大量 GPU 纹理 buffer（通常来自 `gralloc` 分配），结合 GPU 内存分析定位具体的纹理泄漏来源
4. 如果发现大量 ion/cma buffer，检查是否有 Native 库的 mmap 未释放

## 与内存泄漏的区分方法

内存持续增长和内存泄漏在 Perfetto 或 `dumpsys meminfo` 中的表现非常相似——都是 PSS 持续增长。但区分它们是选择正确治理策略的前提。

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

如果不确定是泄漏还是非泄漏性增长，可以先用 LeakCanary 排除 Activity、Fragment、Fragment View、ViewModel 这类生命周期对象的泄漏。没有报告只能说明这些自动监控对象没有明显 retained path，不能排除普通 Java 对象、单例缓存、线程、JNI 全局引用或 Native 层泄漏。若 PSS 仍在增长，需要继续看 Heap Dump 的 dominant retainers、对象数量趋势和 heapprofd。

## LRU Cache 策略的正确实现

非泄漏性内存增长通常源于缓存没有上限，治理时要给缓存设定预算并执行淘汰。Android 提供的 `LruCache` 类就是为此设计的。

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

`LruCache` 的 `maxSize` 参数不一定是字节数，它的单位取决于你如何重写 `sizeOf()` 方法。默认情况下 `sizeOf()` 返回 1，意味着 `maxSize` 表示最大条目数。但对于图片缓存这种场景，每张图片的大小差异可能很大（缩略图 vs 高清大图），用条目数做限制会失真。

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

1/8 这个比例并非银弹，它来自 Android 官方文档的示例。实际的合理比例取决于应用的类型：图片密集型应用（如 Instagram）可能需要更大的比例，而以文字为主的应用可以更小。要先给缓存设定明确预算，不能"能放多少放多少"。

[已验证: 官方文档, developer.android.com/reference/android/util/LruCache]

### 响应系统内存压力

`LruCache` 的淘汰只在缓存满时触发，但系统压力往往更早出现。缓存收缩策略要按版本段理解：

- API 33 及以下，`onTrimMemory()` 还会投递 `TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 这类更细的等级。
- API 34 起，这些等级不再投递给 App；API 35 又把相关常量标成 deprecated。现代版本里，App 侧最稳定的信号主要是 `TRIM_MEMORY_UI_HIDDEN` 和 `TRIM_MEMORY_BACKGROUND`，更细的系统压力判断要回到 RSS、PSS、Perfetto、logcat 和冷启动证据。

```java
@Override
public void onTrimMemory(int level) {
    if (level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND) {
        // 进程进入 LRU 区域，尽快收缩后台缓存
        imageCache.evictAll();
        return;
    }
    if (level == ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN) {
        // UI 不可见，先释放 UI 相关缓存
        imageCache.trimToSize(imageCache.size() / 2);
    }
}
```

`trimToSize()` 仍然按 LRU 顺序淘汰条目，适合做温和收缩；`evictAll()` 适合在进程退到后台队列后直接清空可再生缓存。如果项目还需要连续的系统余量信号，应该接 RSS 趋势、Perfetto 或系统 health / headroom 能力，不要继续把缓存策略绑定在已经不再投递的 trim 常量上。

[已验证: 官方文档, developer.android.com/reference/android/content/ComponentCallbacks2]

### entryRemoved 的资源释放

当条目从 `LruCache` 中被淘汰时，`entryRemoved()` 方法会被回调。它适合释放缓存条目持有的明确资源，但普通 Bitmap 缓存不要默认在这里调用 `recycle()`：

```java
@Override
protected void entryRemoved(boolean evicted, String key,
        Bitmap oldValue, Bitmap newValue) {
    // LruCache 淘汰只移除缓存这一条强引用。
    // 如果 value 持有 Closeable / 硬件句柄，在这里 release / close；
    // 普通 Bitmap 让最后一个强引用消失后交给 GC 回收。
}
```

对本章覆盖的 Android 8.0（API 26）及以上，Bitmap 像素数据在 Native Heap 中，Bitmap 对象不可达后由 GC 触发释放。`recycle()` 不是缓存淘汰的通用动作；只有确定没有任何显示引用或缓存引用时才可以主动调用，且官方推荐主要针对 Android 2.3.3（API 10）及以下的历史内存管理方式。

[已验证: 官方文档, developer.android.com/topic/performance/graphics/manage-memory]

## 内存增长的监控指标

知道问题存在和能系统性地发现问题，是两件不同的事。生产环境需要一套指标体系来持续监控内存增长趋势。

### PSS 趋势

PSS（Proportional Set Size）仍然是理解进程真实物理内存占用的重要口径，但更适合做低频校准，不适合做秒级时序指标。

一方面，PSS 查询本身成本高。Android 16 的 `Debug.getPss()` 路径会通过 `ProcMemInfo.SmapsOrRollup()` 聚合 `smaps_rollup` / `smaps`，并叠加 memtrack 与 swapPss；它适合低频校准，不适合高频轮询。Android 14+ 系统侧更快的 PSS 采集路径可能被节流，App 内同进程 `Debug.getPss()` 不应被写成通用秒级指标。把 PSS 放在 30 秒、1 分钟或页面切换点上做校准更稳妥，连续趋势更适合交给 RSS、Java Heap 和 Native Heap 指标。

Android 15 的 16KB Page Size 还会改变这组指标的解释方式。页变大以后，TLB miss 和页表开销会下降，但小块分配的内部碎片会变多。同样一段业务路径，在 16KB 设备上看到的 RSS / PSS 往往会比 4KB 设备更高。跨设备比对内存曲线前，先用 `adb shell getconf PAGE_SIZE` 确认页大小，再判断增长是不是异常。

在实际工程里，更稳妥的组合是三层指标一起看：

- **RSS**：Android 15/16 在编译 SDK 与 flagged API 可用时可用 `Debug.getRss()`；Android 8-14 用 `/proc/self/status` 的 `VmRSS`、`/proc/self/statm` 或低频 `dumpsys meminfo` 看驻留页变化
- **Java Heap**：用 `Runtime.getRuntime()` 看托管堆预算和回落幅度
- **Native Heap**：用 `Debug.getNativeHeapAllocatedSize()` 看 Native 分配是否持续抬高

PSS 保留给低频校准和回归比对。如果线上需要在异常发生时补抓现场，Android 15+ 的 `ProfilingManager` 更适合触发 system trace / heap profile，而不是靠高频轮询 PSS。

[已验证: 官方文档, developer.android.com/reference/android/os/Debug#getPss()；另见 src/part3-tools/ch14-other-tools/07-profiling-manager.md（ProfilingManager）]

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

采集到 PSS 和 Heap 数据后，需要将它们可视化才能发现趋势。可以按三个层次观察：

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

一些厂商会在内核里做反碎片处理，例如按页迁移类型整理空闲页、把小块虚拟映射整理到更集中的地址范围，目标都是减少高阶页分配失败和大块虚拟地址被零散映射打碎。

这些优化属于 OEM / 系统层面的工作，公开资料里的命名并不完全统一。对 App 开发者来说，更有用的结论是：相同总内存下，分配形态越稳定、对象生命周期越集中，系统越容易把空闲页合并回来，连续物理页和连续虚拟地址也越容易保住。

[已验证: 来源见 Cubox/OPPO内存反碎片优化原理-2022-10-26.md]

## WebView 内存增长问题与多进程 WebView

前面讨论的增长类型主要发生在应用自身的代码中。但有一类组件，它带来的内存增长往往超出开发者的预期——WebView。Chromium 渲染引擎本身的内存开销很高。在多进程 WebView 中，WebView 会关联到 renderer 进程，但多个 WebView 可能共享同一个 renderer；一个 renderer 的终止也可能影响多个 WebView。V8 JavaScript 引擎的堆、Blink 渲染引擎的 DOM 树、GPU 纹理缓存等进程级开销都要纳入预算。

在一个典型的混合应用中（原生 + WebView），如果用户在 WebView 中连续浏览多个页面，WebView 内部的缓存（HTTP 缓存、图片缓存、JS Heap）会持续增长。还要看 WebView 进程级数据结构（如 Visited Links 表、Service Worker 缓存）的生命周期：它们与 WebView 进程绑定，即使销毁 WebView 实例也可能无法完全释放。

[来源: Cubox/WebView 经历的各种干货方案分享-2024-11-28.md]

针对 WebView 的内存增长，有几种有效的策略：

**及时销毁 WebView 实例**：在 Activity/Fragment 销毁时，必须显式调用 `webView.destroy()`，否则 WebView 关联的 Native 资源无法释放。

**使用多进程 WebView**：对于 WebView 使用量大的应用（如小程序框架），可以将 WebView 运行在独立的进程中。当 WebView 进程的内存增长到一定程度时，直接杀掉整个进程重建，释放 WebView 进程持有的内存。微信的小程序框架就是这么做的——每个小程序运行在独立的 WebView 进程中，进程退出后相关内存被回收。

**限制 WebView 缓存**：通过 `WebSettings` 控制 WebView 的缓存行为，比如禁用 DOM Storage、限制数据库大小等。

## 长时间运行 App 的内存管理策略

前面讨论的治理手段适用于大多数应用的日常使用场景。但某些类型的应用天然需要长时间运行：音乐播放器、导航应用、运动追踪器、IM 应用。这类应用的内存管理需要一套不同于普通应用的策略。

**设定全局内存预算**：根据目标设备的典型内存配置，为应用设定一个总的内存预算（比如 200 MB），然后将预算分配到各个模块：图片缓存 50 MB、音视频缓冲区 40 MB、数据缓存 30 MB、其他 80 MB。每个模块需要在预算内自行管理分配和释放。

**定期自检与收缩**：在应用后台运行时，定期检查内存占用。如果超过预算阈值，主动释放非关键资源。比如音乐播放器在后台播放时，可以释放专辑封面缓存、歌词缓存等非必要数据。

**按版本处理 trim 回调**：API 33 及以下还能根据 `TRIM_MEMORY_RUNNING_*` 等级细分策略；API 34+ 只能把 `TRIM_MEMORY_UI_HIDDEN` 和 `TRIM_MEMORY_BACKGROUND` 当作粗粒度信号。长生命周期应用的缓存治理要建立在预算、自检和后台收缩上，不能继续依赖已经不再投递的 trim 常量。

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

这类问题要拆成三条路径看：

- **Java Heap OOM**：应用达到设备给当前进程的托管堆上限后继续分配 Java / Kotlin 对象，ART 抛出 `OutOfMemoryError`。
- **Native / 虚拟地址分配失败**：Native Heap、`mmap`、线程栈、图形映射等持续增长，可能导致 `malloc` / `mmap` 失败；32 位进程还要看连续虚拟地址空间。
- **LMK / lmkd 回收**：系统出现内存压力时，`lmkd` 结合 PSI / vmpressure、`oom_adj_score`、进程重要性和内存收益选择目标进程。PSS / RSS 是风险指标，不是“PSS 到某个进程上限就触发 OOM”的单一条件。

### "`LruCache` 用上就能控制内存"

`LruCache` 只解决了"有限容量"的问题，但如果 `maxSize` 设置不合理（比如设得太大），缓存依然会占用过多内存。另外，`LruCache` 只管理 `put` 和 `get` 操作涉及的条目，如果你的代码在 `LruCache` 之外还持有对这些条目的引用（比如在某个全局列表中同时缓存了 Bitmap 引用），那么 `LruCache` 淘汰这些条目后，它们不会被 GC 回收，等于缓存限制失效了。

### "Native 碎片化只能靠系统解决"

虽然物理内存碎片化属于系统层面的问题，但 App 开发者可以通过优化自身的内存分配模式来减轻碎片化。使用内存池、避免频繁的小尺寸分配和释放、合理管理 Native 对象的生命周期，都能显著降低碎片化的程度。

### "把所有东西都放到 LRU Cache 里就好"

`LruCache` 适合管理可以被重新加载或计算的数据。对于那些重新获取成本很高或无法重新获取的数据（比如实时传感器数据、唯一的状态快照），不应该用 `LruCache` 管理，而应该有专门的持久化和加载策略。

## 参考资料

- AOSP 源码路径：`frameworks/base/core/java/android/util/LruCache.java`
- Android 官方文档：[Manage your app's memory](https://developer.android.com/topic/performance/memory)
- Android 官方文档：[LruCache Reference](https://developer.android.com/reference/android/util/LruCache)
- Android 官方文档：[Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
- Android 官方文档：[ProfilingManager Reference](https://developer.android.com/reference/android/os/ProfilingManager)
- Perfetto heapprofd：[Native Heap Profiling](https://perfetto.dev/docs/data-sources/native-heap-profiling)
- OPPO 内存反碎片优化（素材来源：Cubox/OPPO内存反碎片优化原理-2022-10-26.md）
- Hummer 引擎内存稳定性研究（素材来源：Personal-Knowlodge/source/2026-03-08）
