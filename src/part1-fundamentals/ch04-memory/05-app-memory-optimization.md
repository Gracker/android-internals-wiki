---


status: ready-for-review
title: App 内存优化
section: '4.5'
chapter: '4.5'
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-03-31'
last_verified_against: AOSP android-16.0.0_r1
confidence: medium
sources:
- type: official
  path: https://developer.android.com/topic/performance/memory
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://developer.android.com/build/apps/16kb-page-size
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityManager.java
- type: aosp
  path: frameworks/base/core/java/android/content/ComponentCallbacks2.java
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/Bitmap.java
- type: blog
  path: https://android-developers.googleblog.com/2024/10/16kb-page-size-android-15.html
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://developer.android.com/ndk/guides/debug-gdb
tags:
- memory-optimization
- bitmap
- memory-leak
- onTrimMemory
- native-memory
- memory-churn
- object-pool
- heapprofd
- 16kb-page-size
related_chapters:
- '4.1'
- '4.2'
- '4.3'
- '4.4'
- '7.2'
- '7.3'
drafted_date: '2026-03-31'
drafted_by: openclaw-task2
reviewed_date: 2026-06-04
reviewed_by: openclaw-task6
review_type: draft-review
review_round: 5
polish_count: 1
polish_date: '2026-04-08'
polish_by: task2b-polish
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
task2b_state: fixed
task2b_result: reworked
last_task2b_at: "2026-06-04T04:55:01"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-04"
last_task9_at: "2026-06-04T08:20:00+08:00"
task9_review_notes: "2026-06-04 Task9 deep review: auto-fixed。修正 onTrimMemory 在 Android 16 的 ApplicationThread→主线程分发链、Debug.getPss API level、heapprofd 开销边界和 System.gc 使用边界；已回到 Task6 复审。"
task6_result: pass-light-edit
last_task6_at: '2026-06-04T07:05:00+08:00'
last_task6_review_log: "logs/review/2026-05-22-08-review.md"
task6_review_notes: '2026-06-04 task6 revisiting-review: pass-light-edit。L1/L2 全部通过(禁用词0/AI套话0/高频词全0/元叙述0)。无B类大问题。task9 needs-rework + task2b 已 fixed,返回 task9 待复审。'
review_notes: 2026-05-12 Task6 16:15：L1/L2 小修 29 处（禁用词、第一人称导航、中英文间距、待验证标注）；L3 数据/Perfetto 证据缺口已写入 queue.json（priority 90）。
last_task9_review_log: "logs/deep-review/2026-06-04-08-deep-review.md"
last_task9_autofix_at: "2026-06-04"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-04
---


# App 内存优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存优化的分层思路：减少分配 → 及时释放 → 避免泄漏 → 监控兜底
- 🔹 Bitmap 内存优化：inBitmap 复用、采样率、硬件 Bitmap
- 🔹 内存泄漏的常见模式：Activity 引用泄漏、Handler 泄漏、单例持有 Context
- 🔹 Native 内存管控：JNI 层泄漏排查、malloc debug / ASan
- 🔹 onTrimMemory 与 ComponentCallbacks2 的正确响应策略

### 扩展（可选深入）

- 🔸 Glide/Fresco 等图片库的内存管理策略对比
- 🔸 Jetpack Compose 的内存特点与注意事项
- 🔸 大型 App 的内存预算（Memory Budget）管理实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要系统性地看待 App 内存优化

前面几节已经讲过 Android 内存模型的底层架构：Linux 内核如何管理物理页（4.2），ART 虚拟机如何分配和回收 Java 堆内存（4.3），系统在内存不足时如何通过 LMK 杀进程（4.4）。这些都是系统层面的机制——作为 App 开发者，无法直接控制 `lmkd` 的杀进程策略，也无法修改 ART 的 GC 算法。

但这并不意味着 App 层面无能为力。恰恰相反，**App 的内存使用方式直接决定了系统级机制的触发频率**。一个内存管理良好的 App，不容易触发 GC 暂停导致卡顿，不容易被 LMK 杀死导致冷启动，也不容易因为内存抖动让整个系统的内存压力增大。

很多开发者对"内存优化"的理解是碎片化的：知道 Bitmap 要 recycle，知道 Activity 泄漏要用 WeakReference，知道 onTrimMemory 要处理，但缺少一个框架把这些点串起来。

本节要做的就是建立这个框架。

## 内存优化的分层思路

内存优化实践可以拆成一个有严格先后顺序的层次模型，每一层都是下一层的前提。

### 第一层：减少分配

最有效的优化，是避免不必要的内存分配。

这个道理不复杂，但在实际项目中，大量内存问题恰恰来自"分配了不需要的东西"。几个典型例子：

- 在 `onDraw()` 中创建 `Paint`、`Path` 对象。`onDraw()` 在一帧中可能被调用多次，每帧创建新对象意味着大量短命对象，触发频繁 GC。正确做法是将 `Paint` 作为成员变量，在构造函数中初始化一次。
- 在循环中使用字符串拼接 `"" + value`。每次拼接都创建一个 `StringBuilder` 和一个新的 `String` 对象。使用 `StringBuilder` 的 `append()` 方法可以复用同一个实例。
- 使用 `AutoBoxing`。在 `HashMap<Integer, Value>` 中，每次 put/get 都会创建 `Integer` 对象。使用 `SparseArray` 可以避免自动装箱。

[已验证: 官方文档, developer.android.com/topic/performance/memory — 避免内存抖动的最佳实践]

这些问题的共同特点是：它们不是"bug"——代码能正确运行，测试不会失败。但它们在运行时悄悄制造了大量短命对象，当 App 在 120Hz 设备上运行时，帧间隔只有 8.3ms，GC 暂停 3-5ms 就可能导致掉帧。

### 第二层：及时释放

如果必须分配，那就确保用完之后尽快释放。

"及时释放"的核心不是手动调用 `System.gc()`（Android 明确不建议这样做），而是让对象的生命周期尽可能短，让 GC 能尽早回收。

最常见的反面模式是"对象的生命周期比它应该存在的长"。比如：

- 一个 `Handler` 持有了 `Activity` 的引用，`Activity` 销毁后 `Handler` 还在处理消息——这个 `Activity` 的所有 View 树、资源都无法被回收。
- 一个缓存 Map 没有大小限制，对象放进去就再也不会出来——随着时间推移，这个 Map 会越来越大。
- 在 `Fragment` 的 `onCreateView` 中注册了广播接收器，但没有在 `onDestroyView` 中反注册。

[已验证: 官方文档, developer.android.com/topic/performance/memory — 管理对象生命周期]

解决思路是让对象的引用链在合适的时机断开。后面讲内存泄漏时会展开具体模式。

### 第三层：避免泄漏

"泄漏"是指对象已经不再被使用，但 GC 无法回收它——因为还有一条从 GC Root 到这个对象的强引用链。

避免泄漏比"减少分配"和"及时释放"更难，因为泄漏通常是隐式的：开发者并没有显式地"持有"一个对象，但某个回调、某个内部类、某个系统服务隐式地持有了。而且泄漏的影响是累积的——一个 Activity 泄漏可能只浪费几 MB，但如果用户在一个列表页反复进出 20 次，就是 20 个 Activity 实例同时驻留在内存中。

后面的"内存泄漏的常见模式"部分会逐一分析这些模式。

### 第四层：监控兜底

即使代码质量再高，也难免有遗漏。特别是大型项目，几十个开发者的代码合在一起，泄漏和过度分配几乎是不可避免的。

所以需要监控兜底。工程上通常分三个阶段布防：

- **开发期**：LeakCanary 自动检测 Activity/Fragment 泄漏
- **测试期**：Android Studio Memory Profiler 检查内存分配热点
- **线上**：通过 `Runtime.getRuntime().maxMemory() - Runtime.getRuntime().totalMemory() + Runtime.getRuntime().freeMemory()` 监控可用堆空间，接近上限时主动释放缓存

在工具层面，Perfetto 提供了几个直接面向内存的观察 Track：

- **Java Heap counter**：通过 `process_counter_track` 查看目标进程的 `java_heap` / `total_heap` / `native_heap`。正常状态下 Java Heap 呈锯齿形（分配→GC 回收→再分配），如果下限持续上移，是泄漏的信号
- **GC Event Track**：在 `HeapTaskDaemon` 线程上观察 GC slice（`ConcurrentCopying GC`、`MarkCompact GC`）。频繁的 Young GC（每秒多次）指向对象抖动，偶发的长时间 Full GC 指向老年代压力或泄漏
- **Native Heap（heapprofd）**：按调用栈聚合 Native 分配，找到哪些代码路径分配了最多内存。heapprofd 本身有性能开销，不建议在 Release 构建中长期开启
- **dmabuf / GPU memory Track**：在 `gfx` 相关 counter track 中观察 GPU 纹理和 GraphicBuffer 占用。`dmabuf` 持续增长但 Java Heap 稳定，通常是 Hardware Bitmap 或 Surface 相关资源未释放

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler — Memory Profiler 使用方法]

这四层不是孤立的，而是一个递进的防御体系：第一道防线是"减少分配"；剩余的分配要"及时释放"；没释放干净的风险要靠"避免泄漏"控制；监控负责兜底。

## 内存抖动：当"减少分配"失败时的连锁反应

在讲具体优化手段之前，需要先理解一个贯穿整个内存优化话题的核心概念——**内存抖动（Memory Churn）**，以及它如何与 4.3 节的 ART GC 产生连锁反应。

[已验证: 研究素材, research-feed 2026-03-31-19-ch04-app-memory-churn-gc-objectpool.md]

### 什么是内存抖动

内存抖动是指**短时间内大量临时对象的创建与销毁**。在 Android Studio 的 Memory Profiler 中看到一个上下剧烈波动的"锯齿图"——内存曲线快速上升又快速下降，反复循环——那就是内存抖动的典型表现。

锯齿的上升沿是对象分配，下降沿是 GC 回收。GC 触发的频率才是问题所在（回收本身是 GC 的本职工作）。

### 为什么内存抖动会导致卡顿

4.3 节讲过，ART 使用 Concurrent Copying Collector，虽然是并发的，但仍然有 Young Generation 暂停。当高频分配导致 GC 频繁触发时，会出现这样的时间线：

```
帧 N         | 帧 N+1       | 帧 N+2
UI Thread    | GC Pause!    | UI Thread
12ms         | ████ 8ms     | 4ms + GC 3ms
             ↑ 掉帧!          ↑ 卡顿!
```

帧 N+1 中，GC 暂停了 8ms，加上 UI 线程自身的工作时间，帧 N+1 的总耗时超过了 VSync 周期（120Hz 设备仅 8.3ms，60Hz 设备为 16.6ms），结果就是掉帧。

在高刷新率设备上，这个问题更加严峻。120Hz 设备的帧间隔只有 8.3ms，GC 暂停 5ms 会挤占 60% 的帧预算，几乎必然导致掉帧；而把 GC 暂停控制在 3ms 以内，则有较大概率"藏入"任务间隙，不触发掉帧。将 GC 暂停从 5ms 降到 3ms 后，应用掉帧率通常会有明显改善——具体改善幅度依赖设备、刷新率、负载和采样方法，无法给出通用倍数。实际收益应以同机 Trace 前后对比为准。

可以把"3ms 黄金停顿准则"作为 120Hz 设备上 GC 优化的量化目标——Young GC 单次暂停不应超过 3ms，否则就应该排查对象抖动源头。

这导致一个反直觉的现象：**App 在高刷设备上反而更容易暴露内存抖动问题**。60Hz 设备的 16.6ms 帧间隔给了 GC 更多"藏身"空间，5ms 的暂停可能不丢帧；同样的暂停在 120Hz 上就是掉帧。

### 对象池：对抗内存抖动的利器

理解了内存抖动的根因（高频分配 → GC 频繁 → 暂停导致掉帧），对抗策略就很自然了：**复用对象，避免重复分配**。

Android 系统自身就大量使用了对象池模式：

- **`Message.obtain()`**：系统自带的 Message 对象池，最大容量 50。`Handler.obtainMessage()` 和 `Handler.post()` 内部调用 `Message.obtain()` 从池中取对象复用。注意 `Handler.sendMessage()` 不会调用 `obtain()`——它直接使用调用方传入的 Message 对象，所以调用方需自行通过 `Message.obtain()` 获取。
- **`Parcel.obtain()` / `Parcel.recycle()`**：Binder IPC 的数据载体，通过对象池复用。
- **`MotionEvent.obtain()`**：触摸事件对象，从池中获取后必须调用 `recycle()` 归还。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Message.java — Message 池的链表实现]

如果代码中存在高频创建的自定义对象（比如游戏中的粒子、列表中的临时数据对象），可以考虑实现自己的对象池：

```kotlin
class ObjectPool<T>(
    private val factory: () -> T,
    private val maxSize: Int = 16
) {
    private val pool = ArrayDeque<T>(maxSize)

    fun acquire(): T = pool.removeFirstOrNull() ?: factory()

    fun release(obj: T) {
        if (pool.size < maxSize) {
            // 重置对象状态，避免脏数据
            pool.addLast(obj)
        }
    }
}
```

使用对象池时需要注意三个陷阱：

1. **线程安全**：如果多线程访问，需要加锁或使用 `ConcurrentLinkedDeque`
2. **状态重置**：对象从池中取出后，必须重置所有状态字段，否则会携带上一轮的脏数据
3. **池大小控制**：过大的池本身就是一种内存浪费——对象虽然不被使用了，但因为被池持有而无法回收

## Bitmap 内存优化

Bitmap 是 Android App 中最大的内存消费者之一。一张 1080×1920 的 ARGB_8888 图片，在内存中占用 `1080 × 1920 × 4 = 8,294,400 字节 ≈ 8MB`。一个信息流 App 的列表页同时缓存十几张图片，仅图片就占了上百 MB。

### Bitmap 在 Android 8.0 前后的存储变化

这是一个经常被忽略但影响深远的变更。

在 Android 8.0（API 26）之前，Bitmap 的像素数据存储在 **Java 堆**中，因此会直接计入 App 的 `dalvikHeapSize`，受 `Runtime.getRuntime().maxMemory()` 限制。当 Bitmap 过多导致 Java 堆超限时，就会抛出 `OutOfMemoryError`。

从 Android 8.0 开始，Bitmap 的像素数据移到了 **Native 堆**。这带来了几个变化：

- **不再直接受 Java 堆限制**：Bitmap 占用不再计入 `dalvikHeapSize`，通过 `Runtime.getRuntime().freeMemory()` 观察到的可用空间不再包含 Bitmap 占用
- **仍然计入进程的 PSS**：虽然不在 Java 堆，但通过 `dumpsys meminfo` 看到的 `Native Heap` 会增加
- **释放路径变更**：Native 堆的 Bitmap 像素数据通过 `NativeAllocationRegistry` 注册到 ART 的 `Cleaner` 机制。当 Java 层的 Bitmap 对象变为不可达时，`Cleaner` 触发 Native 释放回调（而非旧版的 `finalize()`）。`Bitmap.recycle()` 仍可主动立即释放像素内存，不需要等 Cleaner 队列处理

[已验证: 官方文档, developer.android.com/topic/performance/graphics/manage-memory — Bitmap 内存管理]

所以在 Android 8.0+ 上，不能仅凭 Java 堆的使用量来判断 App 的真实内存占用。一个 App 可能 Java 堆只用了一半，但 Native 堆被大量 Bitmap 填满了。

### inBitmap：复用 Bitmap 的内存

[已验证: 官方文档, developer.android.com/reference/android/graphics/BitmapFactory.Options.html#inBitmap]

`inBitmap` 是 BitmapFactory 提供的一种复用机制：解码新图片时，不分配新的内存块，而是复用已有 Bitmap 的像素数组。

```kotlin
val options = BitmapFactory.Options().apply {
    inBitmap = reusableBitmap  // 复用已有 Bitmap 的内存
    inSampleSize = 2
}
val bitmap = BitmapFactory.decodeResource(res, resId, options)
```

`inBitmap` 的规则在不同 API 级别有差异：

- **API 11-18**：复用 Bitmap 的大小必须与解码后的 Bitmap **精确匹配**（限制极大，几乎不可用）
- **API 19+**：复用 Bitmap 的大小只需要 **≥** 解码后的 Bitmap（实用性强得多）

直接好处是它完全跳过了内存分配和释放，减少了 malloc/free 调用，也降低了 GC 压力。在列表滑动场景中，图片不断进出屏幕，`inBitmap` 可以显著减少 Bitmap 相关的内存分配——具体减少比例取决于图片尺寸、列表复用策略和采样方法，应以同机 Memory Profiler 对比为准。

### 下采样（inSampleSize）

如果只需在 UI 上显示一张 200×200 的缩略图，但原图是 4000×3000 的高分辨率照片，直接加载会浪费大量内存。

`inSampleSize` 用于在解码时缩小图片：

```kotlin
fun calculateInSampleSize(options: BitmapFactory.Options, reqWidth: Int, reqHeight: Int): Int {
    val (height, width) = options.outHeight to options.outWidth
    var inSampleSize = 1
    if (height > reqHeight || width > reqWidth) {
        val halfHeight = height / 2
        val halfWidth = width / 2
        while ((halfHeight / inSampleSize) >= reqHeight &&
               (halfWidth / inSampleSize) >= reqWidth) {
            inSampleSize *= 2
        }
    }
    return inSampleSize
}
```

注意 `inSampleSize` 的值必须是 2 的幂（2, 4, 8, ...）。如果不是 2 的幂，系统会向下取最近的 2 的幂。`inSampleSize = 2` 意味着宽高各缩小一半，像素数减少为原来的 1/4，内存也减少为 1/4。

### 硬件 Bitmap（Hardware Bitmap）

[已验证: 官方文档, developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE]

Android 8.0（API 26）引入了一种特殊的 Bitmap 配置：`Bitmap.Config.HARDWARE`。

硬件 Bitmap 的像素数据存储在 **GPU 内存**中，而不是系统 RAM 中。直接结果是：

- **不计入 Java Heap**：从 dumpsys meminfo 角度看，像素常见于 Graphics/GL/memtrack/Other dev 等口径，是否归入单进程 PSS 取决于 OEM/memtrack 实现，设备差异大。不能写成"不占内存"——它仍然形成系统内存压力
- **渲染更快**：GPU 直接使用自己的显存绘制，不需要从系统 RAM 拷贝到 GPU
- **不能修改**：不能对硬件 Bitmap 使用 Canvas 绘制或 `setPixel()`——它是只读的
- **不能跨进程**：硬件 Bitmap 不能通过 Binder 传递（比如不能直接传给 Remote Views）

硬件 Bitmap 最适合的场景是"只显示一次的图片"——比如信息流中的图片、广告图、聊天中的表情。Glide 和 Coil 默认在 API 26+ 上使用硬件 Bitmap。

### Bitmap 格式选择

另一个容易被忽略的优化点是 Bitmap 的颜色格式：

| 格式 | 每像素字节数 | 说明 |
|------|-------------|------|
| ARGB_8888 | 4 | 默认格式，支持透明度，质量最高 |
| RGB_565 | 2 | 无透明度，内存减半，适合照片类 |
| ALPHA_8 | 1 | 只有透明度通道，适合遮罩 |
| HARDWARE | GPU 管理 | 最优内存，但不支持修改 |

如果图片不需要透明度（比如照片、缩略图），使用 `RGB_565` 可以省掉 50% 的内存。代价是色彩精度降低（16 位色 vs 32 位色），但在小尺寸图片上几乎看不出差异。

### 图片加载库的内存管理

[已验证: Glide 官方文档, bumptech.github.io/glide/doc/bitmap-pool.html]

现代 Android 开发中，很少有人手动管理 Bitmap。常见做法是使用 Glide、Coil 或 Fresco 这类图片加载库，它们都内建了完善的 Bitmap 内存管理。

**Glide** 使用 `LruBitmapPool` 管理 Bitmap 复用池。池的默认大小是 `maxMemory / 8`。当 Bitmap 不再使用时，Glide 不调用 `recycle()`，而是将 Bitmap 放入池中等待复用。下次解码新图片时，优先从池中取一个大小匹配的 Bitmap，通过 `inBitmap` 复用它的内存。

**Coil** 是 Kotlin-first 的图片加载库。Coil 1.x 曾有 BitmapPool，但 Coil 2.x/3.x 已移除了 BitmapPool 与 PoolableViewTarget，改为依赖 memory cache、hardware/immutable bitmap 和 Android 平台内置的 ImageDecoder 来管理 Bitmap 生命周期。

**Fresco** 采用了完全不同的方案——它使用 Native 层的 `CloseableReference` 和三层缓存（Bitmap 缓存 + 内存缓存 + 磁盘缓存）管理图片。Fresco 在 Android 5.0 之前就已经将 Bitmap 放在 Native 堆上了（Ashmem 区），比 Android 8.0 的官方迁移更早。

| 特性 | Glide | Coil | Fresco |
|------|-------|------|--------|
| Bitmap Pool | ✅ LruBitmapPool | ❌（Coil 2.x+ 已移除） | ✅ CloseableReference |
| 内存缓存 | LRU + WeakRef | LRU | 三层缓存 |
| 硬件 Bitmap | API 26+ 默认 | API 26+ 默认 | 可配置 |
| Kotlin 支持 | Java 优先 | Kotlin-first | Java 优先 |

[待验证: Glide BitmapPool 默认大小 = maxMemory/8 的说法来自官方文档]

## 内存泄漏的常见模式

内存泄漏是 App 内存优化中最棘手的问题——它不像崩溃那样立刻暴露，而是像温水煮青蛙一样慢慢消耗可用内存，直到 App 被系统杀死或者开始严重卡顿。

三种最常见的泄漏模式分别如下。

### 模式一：Activity 引用泄漏

这是 Android 开发中最经典的泄漏模式。触发条件是：一个长生命周期的对象持有了一个已经应该被销毁的 `Activity` 的引用。

最常见的触发场景是**非静态内部类**。在 Java 中，非静态内部类（包括匿名内部类）隐式持有外部类的引用。如果这个内部类的实例比外部 `Activity` 活得更长，`Activity` 就泄漏了。

```java
// 泄漏代码
public class MyActivity extends Activity {
    private void startAsyncWork() {
        new Thread() {
            @Override
            public void run() {
                // 这个匿名 Thread 隐式持有 MyActivity 的引用
                // 如果 Activity 销毁时 Thread 还在运行，Activity 就泄漏了
                doSomethingSlow();
            }
        }.start();
    }
}
```

修复方法是使用**静态内部类 + WeakReference**：

```java
// 修复后
public class MyActivity extends Activity {
    private static class MyWorker extends Thread {
        private final WeakReference<MyActivity> activityRef;

        MyWorker(MyActivity activity) {
            activityRef = new WeakReference<>(activity);
        }

        @Override
        public void run() {
            // 耗时逻辑在 run() 中执行，不依赖 Activity 实例
            doSlowBackgroundWork();

            // 需要更新 UI 时，通过 WeakReference 判空后再回调 Activity
            MyActivity activity = activityRef.get();
            if (activity != null && !activity.isFinishing()) {
                activity.onWorkCompleted();
            }
        }
    }
}
```

修复的关键点在于：`static` 修饰的内部类不再隐式持有外部类引用，代码通过 `WeakReference` 显式地、可空地获取 Activity。当 Activity 被销毁后，`activityRef.get()` 返回 `null`，worker 线程就知道应该停止工作。

[已验证: 官方文档, developer.android.com/reference/java/lang/ref/WeakReference]

### 模式二：Handler 泄漏

Handler 泄漏是 Activity 泄漏的一个特例，但因为太常见，值得单独讲。

```java
// 泄漏代码
public class MyActivity extends Activity {
    private final Handler mHandler = new Handler() {
        @Override
        public void handleMessage(Message msg) {
            // 匿名 Handler 子类隐式持有 Activity 引用
            updateUI();
        }
    };

    private void postDelayedWork() {
        mHandler.postDelayed(() -> {
            // Lambda/Runnable 也隐式持有 Activity
            updateUI();
        }, 5000);  // 5 秒后执行
    }
}
```

问题出在 `postDelayed`：如果用户在 5 秒内退出了 Activity，`Handler` 的消息队列中还有一个待处理的 `Message`，这个 `Message` 持有 `Runnable`，`Runnable` 持有 `Activity` 引用——整个 Activity 无法被回收，直到 5 秒后消息被处理。

修复方案有两个层面：

**方案一：在 `onDestroy` 中清理消息队列**

```java
@Override
protected void onDestroy() {
    mHandler.removeCallbacksAndMessages(null);  // null 表示移除所有消息
    super.onDestroy();
}
```

**方案二：使用静态 Handler + WeakReference**

```java
private static class SafeHandler extends Handler {
    private final WeakReference<MyActivity> ref;

    SafeHandler(MyActivity activity) {
        ref = new WeakReference<>(activity);
    }

    @Override
    public void handleMessage(Message msg) {
        MyActivity activity = ref.get();
        if (activity == null || activity.isFinishing()) return;
        activity.updateUI();
    }
}
```

### 模式三：单例持有 Context

单例（Singleton）的生命周期等于进程的生命周期——它永远不会被 GC 回收。如果单例持有了一个 `Activity` 或 `View` 的 `Context`，那这个 Activity 就永远无法被回收。

```java
// 泄漏代码
public class ImageLoader {
    private static ImageLoader instance;
    private Context context;  // 如果传入的是 Activity Context，就泄漏了

    public static ImageLoader getInstance(Context context) {
        if (instance == null) {
            instance = new ImageLoader(context);
        }
        return instance;
    }
}
```

如果调用 `ImageLoader.getInstance(activity)`，单例就持有了 Activity 的引用，直到进程结束。

修复非常简单：使用 `Application Context`。

```java
// 修复后
public static ImageLoader getInstance(Context context) {
    if (instance == null) {
        instance = new ImageLoader(context.getApplicationContext());
    }
    return instance;
}
```

`Application Context` 的生命周期与进程相同，和单例的生命周期一致，不存在泄漏问题。

**判断规则**：如果一个对象的生命周期可能比 Activity 长（单例、静态变量、Application 级 Service、长生命周期线程），它持有的 Context 必须是 `Application Context`，不能是 `Activity Context`。

### 如何检测内存泄漏

**LeakCanary** 是 Android 内存泄漏检测的事实标准。它通过以下方式工作：

1. 监听 `Activity` 和 `Fragment` 的生命周期
2. 当 `Activity.onDestroy()` 被调用后，创建一个 `WeakReference` 指向该 Activity
3. 触发 GC 后检查 `WeakReference` 是否被清除
4. 如果没有被清除，说明 Activity 泄漏了，dump heap 分析引用链

```gradle
dependencies {
    debugImplementation 'com.squareup.leakcanary:leakcanary-android:2.14'
}
```

只需要添加依赖，不需要写任何代码。LeakCanary 在 debug 构建中自动工作，不影响 release 构建。

[已验证: LeakCanary 官方文档, square.github.io/leakcanary/]

**Android Studio Memory Profiler** 是另一个重要工具。它可以：

- 实时查看内存分配曲线（发现内存抖动）
- 抓取 Heap Dump（分析内存泄漏）
- 按 class 排序查看实例数量（发现异常的对象数量增长）

在 Memory Profiler 中抓取 Heap Dump 后，按 "Retained Size"（该对象通过引用链持有的总内存大小）排序，可以快速定位"哪些对象占用了最多的内存且无法被回收"。

[图：Memory Profiler 中的 Heap Dump 分析界面，标注 Retained Size 排序、泄漏 Activity 的引用链展开]

## Native 内存管控

Java 层的内存泄漏可以通过 GC 和工具比较容易地发现，但 Native 内存（C/C++ 通过 `malloc`/`new` 分配的内存）完全没有 GC 的帮助——分配了多少就占多少，直到手动 `free`/`delete` 或者进程被杀。

### JNI 层的常见泄漏模式

JNI 层的内存泄漏比 Java 层更隐蔽，因为 Native 代码没有 GC 机制。Code Review 中反复出现的模式有三种：

- **`NewGlobalRef` 不 `DeleteGlobalRef`**：JNI 中的全局引用会阻止 GC 回收被引用的 Java 对象。每次 `NewGlobalRef` 都必须有对应的 `DeleteGlobalRef`。
- **`malloc` 不 `free`**：最基础的 C 层泄漏，但当代码路径复杂（提前 return、异常分支）时很容易遗漏。
- **文件描述符不关闭**：`open()` 后不 `close()`。虽然不占堆内存，但 FD 耗尽可能导致系统无法打开新文件（`Too many open files`）。

### malloc debug

Android 提供了 `malloc debug` 工具来追踪 Native 内存分配：

```bash
# 方式一：通过 adb shell 设置进程 wrap 属性（需 force-stop 后重启进程）
adb shell am force-stop com.example.app
adb shell setprop wrap.com.example.app '"LIBC_DEBUG_MALLOC_OPTIONS=backtrace"'

# 方式二：通过 app_process 设置（适用于 debuggable 应用）
adb shell am force-stop com.example.app
adb shell setprop wrap.com.example.app '"LIBC_DEBUG_MALLOC_OPTIONS=backtrace_enable_on_signal"'
adb shell am start -n com.example.app/.MainActivity
```

`backtrace` 选项记录每次 native 分配的调用栈，`backtrace_enable_on_signal` 在收到 `SIGUSR1` 后才开始记录，减少运行时开销。启用后通过 `dumpsys mallocinfo <pid>` 查看分配统计，或结合 `heapprofd`（见下节）做更详细的性能分析。

> [已验证: 官方文档, source.android.com/docs/core/debug/native-crash — malloc debug 选项列表]

### ASan（AddressSanitizer）

ASan 是 LLVM/Clang 提供的内存错误检测工具，可以检测：

- 堆缓冲区溢出（heap-buffer-overflow）
- 栈缓冲区溢出（stack-buffer-overflow）
- 使用已释放的内存（use-after-free）
- 双重释放（double-free）

在 Android 上启用 ASan 需要通过 NDK/Clang 编译参数，而非 Gradle DSL。正确路径如下：

```gradle
// build.gradle — 仅影响符号保留，不启用 ASan 插桩
android {
    buildTypes {
        debug {
            packagingOptions {
                doNotStrip "**/*.so" // 仅保留符号表，方便 crash 定位
            }
        }
    }
}
```

`doNotStrip` 只保留 .so 符号表，**不会启用 ASan**。启用 ASan 的正确方式是通过 NDK 编译参数：

1. 在 `CMakeLists.txt` 或 `Android.mk` 中为目标库添加编译/链接参数：

```cmake
# CMakeLists.txt
target_compile_options(my-native-lib PRIVATE -fsanitize=address -fno-omit-frame-pointer)
target_link_options(my-native-lib PRIVATE -fsanitize=address)
```

2. 准备 `wrap.sh` 包装脚本（Android API 27+ / O_MR1，debug 构建专用）：

```bash
#!/system/bin/sh
# app/src/main/resources/lib/arm64-v8a/wrap.sh
# ASan 运行时库路径取决于 NDK 版本，以下为典型路径
ASAN_LIB=$(dirname $0)/libclang_rt.asan-aarch64-android.so
export LD_PRELOAD=$ASAN_LIB
ASAN_OPTIONS=alloc_dealloc_mismatch=0:detect_stack_use_after_return=1
export ASAN_OPTIONS
exec "$@"
```

关键运行条件：
- `wrap.sh` 仅在 `android:debuggable=true`（或通过 `android.testOnly`）的进程中生效
- `LD_PRELOAD` 加载的 ASan runtime `.so` 需要正确打包到 APK 的 `lib/<abi>/` 下
- 在 `build.gradle` 中确保 `debug` 构建类型的 `jniDebuggable true` 和正确的 NDK sanitizer 配置

ASan 会使 App 性能下降 2-5 倍，所以只在 debug 构建中使用。但它能捕获到 malloc debug 无法发现的越界访问和 use-after-free 问题。

[已验证: 官方文档, developer.android.com/ndk/guides/asan]

### heapprofd：Native 内存性能分析

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiler]

`heapprofd` 是 Perfetto 提供的 Native 堆分析工具，可以精确追踪每一次 Native 内存分配的调用栈：

```bash
# 追踪特定进程的 Native 堆分配（主机侧 Perfetto 脚本）
tools/heap_profile -p <PID>

# 追踪特定包名的 Native 堆分配
tools/heap_profile -n <package_name>

# Java 堆分配采样：通过 --heaps 指定 ART heap
tools/heap_profile -n <package_name> --heaps com.android.art
```

或在 Perfetto TraceConfig 中配置：

```protobuf
data_sources {
    config {
        name: "linux.heapprofd"
        heapprofd_config {
            sampling_interval_bytes: 4096
            heaps: "com.android.art"  # Java 堆分配采样
            pid: <PID>
        }
    }
}
```

[图：Perfetto UI 中 heapprofd 的 Heap Profiles 面板，标注按分配大小排序的调用栈火焰图]

在 Perfetto UI 中，`heapprofd` 的数据出现在 "Heap Profiles" 面板中。按分配大小排序可以找到分配最多的调用栈——这就是内存热点。

`heapprofd` 的开销取决于采样间隔、分配频率和设备负载，可以在内测、灰度或高价值样本中按需采样。Perfetto 的配置中可以设置采样间隔，比如每 4096 字节采样一次，用更低的采样密度换取更低的运行时扰动。

## onTrimMemory 与 ComponentCallbacks2

前面讲的优化都是"主动优化"——写代码时就注意到了内存问题。但还有一种"被动优化"场景：**系统通知内存紧张，需要配合释放一些资源**。这就是 `onTrimMemory` 的作用。

### onTrimMemory 的回调级别

[已验证: 官方文档, developer.android.com/reference/android/content/ComponentCallbacks2]

`ComponentCallbacks2.onTrimMemory(int level)` 的回调级别在 API 33 及以下和 API 34+ 存在显著差异：

**API 33 及以下——全部回调可用：**

前台回调：

| 级别 | 值 | 含义 | 建议操作 |
|------|---|------|----------|
| `TRIM_MEMORY_RUNNING_LOW` | 10 | 系统内存开始紧张 | 释放非关键缓存 |
| `TRIM_MEMORY_RUNNING_MODERATE` | 5 | 内存进一步紧张 | 释放更多缓存 |
| `TRIM_MEMORY_RUNNING_CRITICAL` | 15 | 内存严重紧张，后台进程可能被杀 | 释放所有可释放的缓存 |

注意：这些回调在进程**仍然在前台运行**时就会触发。及时响应可以降低系统进入更严重内存压力状态的概率。

后台回调：

| 级别 | 值 | 含义 | 建议操作 |
|------|---|------|----------|
| `TRIM_MEMORY_UI_HIDDEN` | 20 | UI 不可见了 | 释放 UI 相关资源（Bitmap 缓存等） |
| `TRIM_MEMORY_BACKGROUND` | 40 | 进程进入 LRU 列表 | 释放所有可以重新创建的资源 |
| `TRIM_MEMORY_MODERATE` | 60 | 进程在 LRU 列表中部 | 释放更多缓存 |
| `TRIM_MEMORY_COMPLETE` | 80 | 进程即将被杀 | 释放一切，保存关键数据 |

**API 34+——回调范围收窄：**

从 API 34 起，以下回调级别不再投递给 App（AOSP `ComponentCallbacks2.java` 中带 `@Deprecated` 且明确标注"Apps are not notified of this level since API level 34"）：

| 废弃级别 | 值 | 说明 |
|----------|---|------|
| `TRIM_MEMORY_RUNNING_MODERATE` | 5 | 前台回调，已停止投递 |
| `TRIM_MEMORY_RUNNING_LOW` | 10 | 前台回调，已停止投递 |
| `TRIM_MEMORY_RUNNING_CRITICAL` | 15 | 前台回调，已停止投递 |
| `TRIM_MEMORY_MODERATE` | 60 | 后台 LRU 回调，已停止投递 |
| `TRIM_MEMORY_COMPLETE` | 80 | 后台"即将被杀"回调，已停止投递 |

API 34+ 仍会实际投递的回调为：

| 级别 | 值 | 含义 | 建议操作 |
|------|---|------|----------|
| `TRIM_MEMORY_UI_HIDDEN` | 20 | UI 不可见 | 释放 UI 相关资源（Bitmap 缓存等） |
| `TRIM_MEMORY_BACKGROUND` | 40 | 进程进入 LRU 列表 | 释放所有可以重新创建的资源 |

说明：`TRIM_MEMORY_BACKGROUND`（40）和 `TRIM_MEMORY_UI_HIDDEN`（20）在 AOSP `ComponentCallbacks2.java` 中**没有** `@Deprecated` 标注，不应写成"已废弃/不投递"。在 API 34+ 设备上，内存压力判断应回到 PSI（`/proc/pressure/memory`）、`lmkd` 指标、`dumpsys meminfo` 等系统级信号，不要只依赖 `onTrimMemory` 作为全部内存压力来源。

在 API 34+ 设备上，系统内存压力判断应回到 PSI（`/proc/pressure/memory`）、`mm_vmscan` tracepoint、`lmkd` 指标等系统级信号，不要依赖不再投递的 `TRIM_MEMORY_COMPLETE` 作为"即将被杀"的信号。

[已验证: AOSP ComponentCallbacks2.java — RUNNING_MODERATE=5, RUNNING_LOW=10, RUNNING_CRITICAL=15, UI_HIDDEN=20, BACKGROUND=40, MODERATE=60, COMPLETE=80]

### onTrimMemory 的分发路径

了解回调级别之后，还要看 `onTrimMemory` 是怎么从系统到达 App 的。沿着 AOSP 源码追踪，完整分发链路可以拆成三步。

1. **System Server**：`ActivityManagerService` 检测到内存压力变化后，通过 Binder 向目标进程发送 `scheduleTrimMemory(level)`。
2. **App 侧 ApplicationThread**：Binder 入口是 `ApplicationThread.scheduleTrimMemory(level)`，它不会直接在 Binder 线程执行 `handleTrimMemory()`；Android 16 源码会把 `handleTrimMemory()` 投递到主线程的 `Choreographer.CALLBACK_COMMIT`，没有 Choreographer 时才退回 `mH.post(r)`。
3. **主线程分发**：`handleTrimMemory(int level)` 调用 `collectComponentCallbacks(true)` 收集 `Application`、未结束的 `Activity`、`Service` 和本地 `ContentProvider`，再逐个调用 `onTrimMemory(level)`。通过 `Application.registerComponentCallbacks()` 注册的回调会在 `Application.onTrimMemory()` 内部分发。

```java
// frameworks/base/core/java/android/app/ActivityThread.java
// handleTrimMemory 的核心分发（简化）
public final void handleTrimMemory(int level) {
    final ArrayList<ComponentCallbacks2> callbacks =
            collectComponentCallbacks(true /* includeUiContexts */);
    for (int i = 0; i < callbacks.size(); i++) {
        callbacks.get(i).onTrimMemory(level);
    }
}
```

> [已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java — handleTrimMemory]

两个排查边界：

- **回调顺序不应假设**：`handleTrimMemory` 会按 `collectComponentCallbacks(true)` 收集到的组件列表分发；通过 `Application.registerComponentCallbacks()` 注册的回调再由 `Application.onTrimMemory()` 分发。业务代码不要假设某个回调一定在另一个之前执行。
- **API 34+ 收窄发生在 System Server 侧**：前文提到的 `RUNNING_*`、`MODERATE`(60)、`COMPLETE`(80) 等旧 level 在 API 34+ 不再投递——`ActivityManagerService` 直接跳过这些 level，App 侧的 `handleTrimMemory` 不会收到。

### 正确的响应策略

很多开发者对 `onTrimMemory` 的处理过于粗糙——要么不处理，要么一收到回调就清空所有缓存。更好的做法是根据级别做差异化的释放：

```kotlin
override fun onTrimMemory(level: Int) {
    when (level) {
        TRIM_MEMORY_RUNNING_LOW,
        TRIM_MEMORY_RUNNING_MODERATE -> {
            // 释放非关键缓存，比如预加载的数据
            releaseNonCriticalCaches()
        }
        TRIM_MEMORY_RUNNING_CRITICAL -> {
            // 释放更多缓存，但保留核心数据
            releaseNonCriticalCaches()
            releaseImageCache(size = imageCache.size / 2)
        }
        TRIM_MEMORY_UI_HIDDEN -> {
            // UI 不可见了，释放 UI 相关资源
            releaseUIResources()
        }
        TRIM_MEMORY_BACKGROUND,
        TRIM_MEMORY_MODERATE -> {
            // 后台状态，释放大部分缓存
            releaseImageCache(size = imageCache.size / 3)
            releaseSecondaryCaches()
        }
        TRIM_MEMORY_COMPLETE -> {
            // 即将被杀，释放一切
            releaseAllCaches()
            saveCriticalState()
        }
    }
}
```

处理原则：**`onTrimMemory` 的回调不应该导致用户可感知的体验下降**。当进程在前台时收到 `TRIM_MEMORY_RUNNING_LOW`，应释放的是预加载缓存、二级缓存这类"有更好、没有也不影响核心功能"的资源。不要在前台状态下清空图片缓存——用户正在看的列表会突然变成白屏。

### 注册方式

`onTrimMemory` 不只是 `Activity` 的回调。任何组件都可以通过 `ComponentCallbacks2` 接收：

```kotlin
// 在 Application 或任何组件中注册
override fun onCreate() {
    super.onCreate()
    registerComponentCallbacks(object : ComponentCallbacks2 {
        override fun onTrimMemory(level: Int) {
            // 处理内存压力回调
        }
        override fun onConfigurationChanged(newConfig: Configuration) {}
        override fun onLowMemory() {
            // 兼容旧 API 的回调，优先使用 onTrimMemory
        }
    })
}
```

`registerComponentCallbacks` 注册的回调会在进程的所有生命周期中生效，而不仅限于某个 Activity 的生命周期。

## 16KB Page Size 迁移对 App 内存的影响

[已验证: 研究素材, research-feed 2026-03-31-19-ch04-app-memory-16kb-migration.md]

2025-2026 年 Android 平台最大的平台级内存变更是 **16KB Page Size 的强制迁移**。Google Play 要求：自 2025-11-01 起，提交到 Google Play、面向 Android 15/API 35+ 设备的新应用和更新必须支持 16KB page size。此要求不作用于所有已发布应用的存量版本，也不作用于仅面向 Android 14 及以下设备的提交。

### 为什么 16KB Page Size 能提升性能

传统 Android 使用 4KB 内存页。16KB 页的优势在于：

- **TLB 压力降低**：更大的页意味着更少的 TLB entry，减少了 Page Table Walk 的开销
- **冷启动加速**：Google 官方数据，冷启动时间平均提升 3.16%，最佳案例提升 30%
- **启动功耗降低**：启动期间功耗降低 4.56%

[已验证: Google 官方博客, android-developers.googleblog.com/2024/10/16kb-page-size-android-15.html]

### 对 App 的影响

**Java/Kotlin 纯应用**：几乎不需要改动。ART 自动处理内存分配的对齐问题。

**NDK/C++ 应用**：需要重新编译。关键改动：

```gradle
// AGP 8.5.1+ 自动处理 16KB 对齐
android {
    // NDK r28+ 默认 16KB ELF alignment
    // 旧版 NDK 需手动添加链接器标志：
    // -Wl,-z,max-page-size=16384
}
```

最需要注意的代码模式是**硬编码页大小**：

```c
// 错误：硬编码 4KB
#define PAGE_SIZE 4096

// 正确：运行时获取
long page_size = sysconf(_SC_PAGESIZE);
```

[已验证: 官方文档, developer.android.com/build/apps/16kb-page-size — 迁移指南]

**第三方 SDK**：React Native、Flutter 等框架已提供兼容版本。如果 App 依赖了包含 Native 代码的第三方 SDK，需要确认其是否已适配 16KB 页。

### 测试方法

- **Pixel 8/9**：开发者选项中启用 "Boot with 16KB page size"
- **Android Studio AVD**：使用 API 35 的 "16KB" 镜像
- **APK Analyzer（Android Studio Panda+）**：APK Analyzer 新增了 16KB 对齐状态列，开发者可以直接审计 APK 中所有 `.so` 文件的页对齐合规性。打开 APK Analyzer 后，在 `lib/` 目录下查看 Native 库列表，"16KB Aligned"列会标注每个 `.so` 是否满足 16KB 对齐要求。第三方 SDK 的 `.so` 文件如果没有对齐，会在这一列直接暴露

### 对 Bitmap 的影响

Bitmap 像素数据存储在 Native 堆。在 16KB 页模式下，每个 Bitmap 的内存页浪费可能增加（如果一个 Bitmap 的像素数据不是 16KB 的整数倍，最后一页会有更多浪费）。Bitmap 像素数据存储在 Native 堆。在 16KB 页模式下，分配对齐从 4KB 提升到 16KB，可能影响 native allocation、GraphicBuffer/allocator 分配路径。具体影响需用 heapprofd、dumpsys meminfo 和特定图像库版本实测确认。Glide/Coil 等图片加载库在构造 Bitmap 时依赖平台 API，其对齐行为由平台 allocator 和 GraphicBuffer 决定，未必在库层面做了显式 16KB 对齐优化。

## 扩展：大型 App 的内存预算管理

对于大型 App（DAU 百万级以上），单纯靠"哪里泄漏修哪里"是不够的。需要有系统性的内存预算管理。

### 确定内存预算

一个 App 的内存预算取决于两个因素：

1. **设备可用内存**：通过 `ActivityManager.getMemoryClass()` 获取设备给单个 App 的堆大小限制（通常是 128MB-512MB）
2. **App 自身的内存分配模式**：不同的业务场景有不同的内存热点

### 内存分区策略

大型 App 的典型做法是将可用内存划分为几个"区域"：

- **核心区（约 30%）**：Framework、基础库、长生命周期对象。这部分内存相对稳定，不容易波动。
- **业务区（约 40%）**：当前页面的 View 树、数据模型、业务逻辑。随页面切换波动。
- **缓存区（约 20%）**：图片缓存、网络缓存、预加载缓存。最容易被释放。
- **预留区（约 10%）**：为突发场景（如大图编辑、视频处理）预留的缓冲空间。

当 `onTrimMemory` 回调触发时，按照"缓存区 → 预留区 → 业务区的非核心部分"的顺序释放。

[已验证: 公开技术分享, 货拉拉 Android 端内存治理实践等]

### 线上监控

线上内存监控的关键指标：

- **Java 堆使用率**：`Runtime.getRuntime().totalMemory() / Runtime.getRuntime().maxMemory()`
- **PSS 总量**：通过 `Debug.getPss()` 获取（API 14+ 可用）
- **FD 数量**：通过 `/proc/self/fd` 的文件数量
- **Bitmap 数量**：通过 `Debug.getMemoryInfo()` 中的 `nativePss` 间接推算

当这些指标接近阈值时，触发降级策略（释放缓存、降低图片质量、关闭预加载）。

### 线上诊断路径

当前已公开的诊断路径：

- **`ApplicationExitInfo`（Android 11 / API 30+）**：通过 `getHistoricalProcessExitReasons()` 获取进程终止原因、状态、PSS/RSS 快照。`getPss()` / `getRss()` 也是 API 30 口径；Android 10 / API 29 设备无法按此路径回查低内存退出原因。如果 `reason == REASON_LOW_MEMORY`，说明进程被系统因内存压力终止
- **`ProfilingManager`（Android 15/API 35+）**：可在内存水位达到阈值时触发系统级 Trace 采集，提供零侵入的内存异常捕获

[待验证] Android 17 是否在 `ApplicationStartInfo` 中新增了上次运行周期的峰值内存回查方法。确认前可先用 `ApplicationExitInfo.getPss()` 和 `getRss()` 作为替代诊断数据源。

## 常见问题与误区

内存优化是 Android 开发中最容易产生误解的领域之一。一部分原因是 Android 的内存管理机制在不同版本之间发生了显著变化，一些曾经正确的做法在新版本上不再适用，而一些从未正确过的做法却因为"看起来有效"而被广泛传播。这里梳理几个在实际开发和技术面试中反复出现的典型误区。

### 误区一："调用 System.gc() 能解决内存问题"

这个想法的出发点可以理解——内存不够了，那就主动告诉系统"来回收一下吧"。但 Android 明确不建议手动触发 GC，原因有两层。

第一层原因是 **GC 本身有开销**。ART 的 Concurrent Copying Collector 虽然大部分工作是并发的，但仍然需要短暂的"暂停"阶段（Young Generation 暂停）来拷贝存活对象。调用 `System.gc()` 时，就是在主动制造一次 GC 周期，这会让正在运行的线程暂停——如果这个调用发生在主线程的渲染路径中，就是一次额外的掉帧风险。

第二层原因是 **它掩盖了问题本身**。内存紧张通常意味着存在泄漏或过度分配。调用 `System.gc()` 可能在短时间内"解决"内存不足的症状（GC 可能回收一些刚变为不可达的对象（比如清空缓存后，原先被缓存强引用持有的对象断开了引用链）），但它不会修复泄漏——泄漏的对象仍然有从 GC Root 到达的强引用链，GC 无法回收它们。正确的做法是用 Memory Profiler 或 LeakCanary 找到泄漏源头，而不是用 `System.gc()` 掩盖症状。

极少数受控压测场景下，刚执行完一次大批量内存释放操作（比如清空大型缓存 Map）后，可以用 `System.gc()` 辅助观察“引用是否已经断开”。这不应进入用户路径，也不应作为 `onTrimMemory` 响应策略；线上治理仍应依赖减少分配、断开引用、释放缓存和观察内存水位。

[已验证: 官方文档, developer.android.com/topic/performance/memory — 避免手动触发 GC]

### 误区二："Android 8.0+ 不需要 recycle Bitmap"

前文讲过，Android 8.0（API 26）将 Bitmap 的像素数据从 Java 堆移到了 Native 堆。Bitmap 因此不再直接占用 Java 堆配额，也不再直接导致 `OutOfMemoryError`。但"不需要 recycle"这个结论过于简化了。

实际情况是：Bitmap 的 Java 对象仍然在 Java 堆中（它是一个普通 Java 对象，包含宽高、配置等元数据），而像素数据在 Native 堆。当 Java 层的 Bitmap 对象变得不可达时，GC 回收 Java 对象后，`NativeAllocationRegistry` 注册的 `Cleaner` 回调触发 Native 像素释放。这个过程是**异步的、延迟的**——GC 不保证立即回收，Cleaner 队列的处理也可能滞后。

在以下场景中，显式调用 `Bitmap.recycle()` 仍然有意义：

- **内存密集型操作**（如图片编辑 App 同时操作多张大图），需要尽快释放 Native 内存，而不是等待 finalize 队列慢慢处理
- **低内存设备**上，Native 内存的压力同样会触发系统的 OOM Killer，不 recycle 意味着大量 Bitmap 像素数据占着 Native 堆
- **需要确认 Bitmap 已被释放**：`recycle()` 会将 Bitmap 标记为"dead"，后续任何使用都会抛异常——这比让一个"僵尸 Bitmap"悄悄占用内存要好

不过，如果使用 Glide、Coil 这样的图片加载库，通常不需要手动 recycle。这些库通过 Bitmap Pool 管理 Bitmap 的生命周期，会自动决定何时复用、何时释放。手动 recycle 一个由 Glide 管理的 Bitmap，反而会破坏它的复用池。

[已验证: 官方文档, developer.android.com/topic/performance/graphics/manage-memory — Bitmap 管理最佳实践]

### 误区三："onTrimMemory 触发 = App 即将被杀"

这个误解导致了很多 App 在收到 `onTrimMemory` 回调时反应过度——清空所有缓存、停止所有后台任务、甚至弹窗提示用户"内存不足"。

`onTrimMemory` 有多个级别，大部分是**预警**而非"死刑通知"。前面已经列出每个级别的含义，这里用一个简化的判断框架来帮助理解：

- **前台回调**（`TRIM_MEMORY_RUNNING_LOW/MODERATE/CRITICAL`）：App 仍在前台运行，系统只是说"整个设备的内存有点紧了"。这时候应释放非关键缓存（比如预加载的数据），但不要影响用户正在使用的核心功能——不要清空当前列表的图片缓存，不要停止正在播放的视频。
- **`TRIM_MEMORY_UI_HIDDEN`**：App 的 UI 不可见（比如用户按了 Home 键）。这是最常见的前后台切换回调，和"即将被杀"没有关系。只需释放 UI 相关的资源（比如大的 View 缓存）。
- **后台回调**（`TRIM_MEMORY_BACKGROUND/MODERATE`）：App 在后台 LRU 列表中，系统在考虑是否回收进程。应释放大部分可重建的缓存，但还没到最高压力级别。
- **`TRIM_MEMORY_COMPLETE`**：这是唯一一个可以理解为"系统正在认真考虑终止进程"的级别。到了这个级别，应释放一切可释放的资源，并保存关键状态数据，以备下次冷启动时恢复。

**不要把 `onTrimMemory` 当成 `onDestroy`**。它是一个梯度式的预警系统，不是一次性开关。正确的做法是根据级别做差异化的响应，而不是一收到回调就清空一切。

### 误区四："申请 largeHeap 是解决内存不足的好办法"

`android:largeHeap="true"` 看起来是一个简单的解决方案——在 Manifest 里加一行配置，Java 堆的大小限制就提高了。但它有几个不容易被注意到的代价。

**GC 开销增大**。ART 的 GC 时间与堆的大小正相关——堆越大，GC 需要扫描的对象越多，单次 GC 的耗时越长。在 120Hz 设备上，帧间隔只有 8.3ms，GC 暂停多出 2-3ms 就可能导致掉帧。一个普通堆大小 256MB 的 App 和一个 largeHeap 512MB 的 App，在相同分配模式下，后者的 GC 暂停时间可能是前者的 1.5-2 倍。

**设备碎片化问题**。"large heap"的具体大小由设备厂商决定，不同设备差异很大。在高内存设备上可能是 512MB，在低内存设备上可能只有 384MB——看似申请了"很大"的堆，实际可能只多了一点点。

**largeHeap 不解决内存泄漏**。如果 App 存在 Activity 泄漏，申请更大的堆只是让泄漏的"容量"变大了——从"泄漏 20 个 Activity 后 OOM" 变成了"泄漏 40 个 Activity 后 OOM"。泄漏仍然存在。

Google 的官方建议是：`largeHeap` 仅适用于需要大内存的特定场景（图片/视频编辑、大型游戏、地图渲染），而不应该作为解决 OOM 的常规手段。在申请 largeHeap 之前，先用 Memory Profiler 分析 App 的内存分配模式，确认是需要更多内存，还是只需要修复泄漏和优化分配。

[已验证: 官方文档, developer.android.com/guide/topics/manifest/application-element — largeHeap 属性说明]

### 误区五："内存抖动只发生在低端设备上"

直觉上容易这样判断：低端设备内存小、CPU 慢，所以更容易出现内存抖动导致的卡顿；高端设备内存大、CPU 快，应该不会有这个问题。

但实际情况是反过来的：**120Hz 高刷新率设备比 60Hz 设备更容易暴露内存抖动问题**。

前面的"内存抖动"小节已经分析过原因：卡顿是否发生，取决于 GC 暂停时间是否超过帧间隔。60Hz 设备的帧间隔是 16.6ms，GC 暂停 5ms 还有 11.6ms 的余量。但 120Hz 设备的帧间隔只有 8.3ms，同样的 5ms GC 暂停就只剩 3.3ms——如果这一帧的 UI 工作本身需要 5ms，总共就是 10ms，超过了 8.3ms 的帧间隔，掉帧就发生了。

结果是：在 60Hz 设备上测试可能毫无卡顿，到了 120Hz 设备上就可能暴露。这也是为什么内存优化不应该只在低端设备上做——高刷设备同样需要减少不必要的对象分配，特别是 `onDraw()`、`onBindViewHolder()` 这类高频回调路径中的分配。

[待验证: 120Hz vs 60Hz 设备上 GC 暂停导致掉帧的实际测试数据对比]

---

## 参考资料

### AOSP 源码
- `frameworks/base/core/java/android/graphics/BitmapFactory.java` — inBitmap 实现
- `frameworks/base/core/java/android/graphics/Bitmap.java` — Bitmap 配置和回收
- `frameworks/base/core/java/android/app/ActivityManager.java` — getMemoryClass() / onTrimMemory
- `frameworks/base/core/java/android/content/ComponentCallbacks2.java` — TRIM_MEMORY 常量
- `frameworks/base/core/java/android/os/Message.java` — Message 对象池实现

### 官方文档
- [Managing Bitmap Memory](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Investigate RAM Usage](https://developer.android.com/topic/performance/memory)
- [16KB Page Size](https://developer.android.com/build/apps/16kb-page-size)
- [Bitmap.Config.HARDWARE](https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE)
- [heapprofd (Perfetto)](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AddressSanitizer (NDK)](https://developer.android.com/ndk/guides/asan)
- [malloc debug](https://developer.android.com/ndk/guides/debug-gdb)

### 技术博客与参考
- [16KB Page Size — Android Developers Blog](https://android-developers.googleblog.com/2024/10/16kb-page-size-android-15.html)
- [Glide Bitmap Pool](https://bumptech.github.io/glide/doc/bitmap-pool.html)
- [LeakCanary](https://square.github.io/leakcanary/)

### 交叉引用
- 本章 4.1 节「Android 内存模型全景」— 系统内存组成和度量方法
- 本章 4.3 节「ART 虚拟机内存管理」— Java 堆 GC 机制
- 本章 4.4 节「Low Memory Killer」— 系统杀进程策略
- 第 7 章第 2 节「卡顿原因体系」— 内存抖动作为卡顿根因之一
- 第 7 章第 3 节「卡顿分析方法论」— heapprofd 在卡顿分析中的使用
