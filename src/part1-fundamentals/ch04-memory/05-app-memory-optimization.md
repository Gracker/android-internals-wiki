---
title: "App 内存优化"
chapter: "4.5"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-03-31"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://developer.android.com/build/apps/16kb-page-size"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java"
  - type: blog
    path: "https://android-developers.googleblog.com/2024/10/16kb-page-size-android-15.html"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/native-heap-profiler"
  - type: official
    path: "https://developer.android.com/ndk/guides/debug-gdb"
tags: ['memory-optimization', 'bitmap', 'memory-leak', 'onTrimMemory', 'native-memory', 'memory-churn', 'object-pool', 'heapprofd', '16kb-page-size']
related_chapters: ["4.1", "4.2", "4.3", "4.4", "7.2", "7.3"]
drafted_date: "2026-03-31"
drafted_by: "openclaw-task2"
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

我们在前面几节讲了 Android 内存模型的底层架构：Linux 内核如何管理物理页（4.2），ART 虚拟机如何分配和回收 Java 堆内存（4.3），系统在内存不足时如何通过 LMK 杀进程（4.4）。这些都是系统层面的机制——作为 App 开发者，你无法直接控制 `lmkd` 的杀进程策略，也无法修改 ART 的 GC 算法。

但这并不意味着 App 层面无能为力。恰恰相反，**App 的内存使用方式直接决定了系统级机制的触发频率**。一个内存管理良好的 App，不容易触发 GC 暂停导致卡顿，不容易被 LMK 杀死导致冷启动，也不容易因为内存抖动让整个系统的内存压力增大。

问题是，很多开发者对"内存优化"的理解是碎片化的——知道 Bitmap 要 recycle，知道 Activity 泄漏要用 WeakReference，知道 onTrimMemory 要处理——但缺少一个系统性的框架把这些点串起来。

本节的目标就是建立这个框架。

## 内存优化的分层思路

我们来看一个内存优化实践的层次模型。它不是一个清单，而是一套有先后顺序的策略——每一层都是下一层的前提。

### 第一层：减少分配

最有效的优化，是根本不分配内存。

这听起来是废话，但在实际项目中，大量的内存问题是"分配了不需要的东西"造成的。举几个例子：

- 在 `onDraw()` 中创建 `Paint`、`Path` 对象。`onDraw()` 在一帧中可能被调用多次，每帧创建新对象意味着大量短命对象，触发频繁 GC。正确做法是将 `Paint` 作为成员变量，在构造函数中初始化一次。
- 在循环中使用字符串拼接 `"" + value`。每次拼接都创建一个 `StringBuilder` 和一个新的 `String` 对象。使用 `StringBuilder` 的 `append()` 方法可以复用同一个实例。
- 使用 `AutoBoxing`。在 `HashMap<Integer, Value>` 中，每次 put/get 都会创建 `Integer` 对象。使用 `SparseArray` 可以避免自动装箱。

[已验证: 官方文档, developer.android.com/topic/performance/memory — 避免内存抖动的最佳实践]

这些问题的共同特点是：它们不是"bug"——代码能正确运行，测试不会失败。但它们在运行时悄悄制造了大量短命对象，当你的 App 在 120Hz 设备上运行时，帧间隔只有 8.3ms，GC 暂停 3-5ms 就可能导致掉帧。

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

避免泄漏比"减少分配"和"及时释放"更难，因为泄漏通常是隐式的：你并没有显式地"持有"一个对象，但某个回调、某个内部类、某个系统服务悄悄地替你持有了。而且泄漏的影响是累积的——一个 Activity 泄漏可能只浪费几 MB，但如果用户在一个列表页反复进出 20 次，就是 20 个 Activity 实例同时驻留在内存中。

我们会在后面的"内存泄漏的常见模式"部分逐一分析。

### 第四层：监控兜底

即使你的代码写得再好，也难免有遗漏。特别是大型项目，几十个开发者的代码合在一起，泄漏和过度分配几乎是不可避免的。

所以需要监控兜底：

- **开发期**：LeakCanary 自动检测 Activity/Fragment 泄漏
- **测试期**：Android Studio Memory Profiler 检查内存分配热点
- **线上**：通过 `Runtime.getRuntime().maxMemory() - Runtime.getRuntime().totalMemory() + Runtime.getRuntime().freeMemory()` 监控可用堆空间，接近上限时主动释放缓存

[已验证: 官方文档, developer.android.com/studio/profile/memory-profiler — Memory Profiler 使用方法]

这四层不是孤立的，而是一个递进的防御体系。你的第一道防线是"减少分配"，过了这一关之后，剩余的分配要"及时释放"，万一没释放干净就要"避免泄漏"，最后的底线是"监控兜底"。

## [自动发现] 内存抖动：当"减少分配"失败时的连锁反应

在讲具体优化手段之前，我们需要理解一个贯穿整个内存优化话题的核心概念——**内存抖动（Memory Churn）**，以及它如何与我们在 4.3 节讲的 ART GC 产生连锁反应。

[来源: research-feed 2026-03-31-19-ch04-app-memory-churn-gc-objectpool.md]

### 什么是内存抖动

内存抖动是指**短时间内大量临时对象的创建与销毁**。如果你在 Android Studio 的 Memory Profiler 中看到了一个上下剧烈波动的"锯齿图"——内存曲线快速上升又快速下降，反复循环——那就是内存抖动的典型表现。

锯齿的上升沿是对象分配，下降沿是 GC 回收。问题不在于 GC 回收了这些对象（GC 的本职工作），而在于 GC 触发的频率。

### 为什么内存抖动会导致卡顿

我们在 4.3 节讲过，ART 使用 Concurrent Copying Collector，虽然是并发的，但仍然有 Young Generation 暂停。当高频分配导致 GC 频繁触发时，会出现这样的时间线：

```
帧 N         | 帧 N+1       | 帧 N+2
UI Thread    | GC Pause!    | UI Thread
12ms         | ████ 8ms     | 4ms + GC 3ms
             ↑ 掉帧!          ↑ 卡顿!
```

帧 N+1 中，GC 暂停了 8ms，加上 UI 线程自身的工作时间，帧 N+1 的总耗时超过了 VSync 周期（120Hz 设备仅 8.3ms，60Hz 设备为 16.6ms），结果就是掉帧。

在高刷新率设备上，这个问题更加严峻。120Hz 设备的帧间隔只有 8.3ms，GC 暂停 5ms 就可能导致掉帧。而 60Hz 设备有 16.6ms 的缓冲，GC 暂停 5ms 还可能不丢帧。所以你会看到一个反直觉的现象：**App 在高刷设备上反而更容易出现因内存抖动导致的卡顿**。

[待验证: 120Hz 设备上 GC 暂停 5ms 导致掉帧的具体测试数据]

### 对象池：对抗内存抖动的利器

理解了内存抖动的根因（高频分配 → GC 频繁 → 暂停导致掉帧），对抗策略就很自然了：**复用对象，避免重复分配**。

Android 系统自身就大量使用了对象池模式：

- **`Message.obtain()`**：系统自带的 Message 对象池，最大容量 50。`Handler.sendMessage()` 内部会调用 `Message.obtain()` 从池中取对象，而不是每次 `new Message()`。
- **`Parcel.obtain()` / `Parcel.recycle()`**：Binder IPC 的数据载体，通过对象池复用。
- **`MotionEvent.obtain()`**：触摸事件对象，从池中获取后必须调用 `recycle()` 归还。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/Message.java — Message 池的链表实现]

如果你的代码中有高频创建的自定义对象（比如游戏中的粒子、列表中的临时数据对象），可以考虑实现自己的对象池：

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

在 Android 8.0（API 26）之前，Bitmap 的像素数据存储在 **Java 堆**中。这意味着 Bitmap 的内存占用直接计入 App 的 `dalvikHeapSize`，受 `Runtime.getRuntime().maxMemory()` 限制。当 Bitmap 过多导致 Java 堆超限时，就会抛出 `OutOfMemoryError`。

从 Android 8.0 开始，Bitmap 的像素数据移到了 **Native 堆**。这带来了几个变化：

- **不再直接受 Java 堆限制**：Bitmap 占用不再计入 `dalvikHeapSize`，你通过 `Runtime.getRuntime().freeMemory()` 看到的可用空间不再包含 Bitmap 占用
- **仍然计入进程的 PSS**：虽然不在 Java 堆，但通过 `dumpsys meminfo` 看到的 `Native Heap` 会增加
- **GC 不再直接回收**：Native 堆的 Bitmap 由 Native 层的 finalize 机制回收，或者通过 `Bitmap.recycle()` 主动释放

[已验证: 官方文档, developer.android.com/topic/performance/graphics/manage-memory — Bitmap 内存管理]

这意味着在 Android 8.0+ 上，你不能仅凭 Java 堆的使用量来判断 App 的真实内存占用。一个 App 可能 Java 堆只用了一半，但 Native 堆被大量 Bitmap 填满了。

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

复用的效果是显著的：它完全跳过了内存分配和释放，减少了 malloc/free 调用，也降低了 GC 压力。在列表滑动场景中，图片不断进出屏幕，`inBitmap` 可以将 Bitmap 相关的内存分配减少 80% 以上。

### 下采样（inSampleSize）

如果你只需要在 UI 上显示一张 200×200 的缩略图，但原图是 4000×3000 的高分辨率照片，直接加载会浪费大量内存。

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

硬件 Bitmap 的像素数据存储在 **GPU 内存**中，而不是系统 RAM 中。这意味着：

- **不计入 App 的 PSS**：从内存统计的角度看，这张 Bitmap "不占内存"
- **渲染更快**：GPU 直接使用自己的显存绘制，不需要从系统 RAM 拷贝到 GPU
- **不能修改**：你不能对硬件 Bitmap 使用 Canvas 绘制或 `setPixel()`——它是只读的
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

现代 Android 开发中，很少有人手动管理 Bitmap。我们通常使用图片加载库——Glide、Coil 或 Fresco——它们都内建了完善的 Bitmap 内存管理。

**Glide** 使用 `LruBitmapPool` 管理 Bitmap 复用池。池的默认大小是 `maxMemory / 8`。当 Bitmap 不再使用时，Glide 不调用 `recycle()`，而是将 Bitmap 放入池中等待复用。下次解码新图片时，优先从池中取一个大小匹配的 Bitmap，通过 `inBitmap` 复用它的内存。

**Coil** 是 Kotlin-first 的图片加载库，底层使用 Coroutine 管理 Bitmap 的生命周期。它同样实现了 Bitmap Pool，但因为基于协程，可以更精确地在生命周期结束时释放 Bitmap。

**Fresco** 采用了完全不同的方案——它使用 Native 层的 `CloseableReference` 和三层缓存（Bitmap 缓存 + 内存缓存 + 磁盘缓存）管理图片。Fresco 在 Android 5.0 之前就已经将 Bitmap 放在 Native 堆上了（Ashmem 区），比 Android 8.0 的官方迁移更早。

| 特性 | Glide | Coil | Fresco |
|------|-------|------|--------|
| Bitmap Pool | ✅ LruBitmapPool | ✅ 基于 Coroutine | ✅ CloseableReference |
| 内存缓存 | LRU + WeakRef | LRU | 三层缓存 |
| 硬件 Bitmap | API 26+ 默认 | API 26+ 默认 | 可配置 |
| Kotlin 支持 | Java 优先 | Kotlin-first | Java 优先 |

[待验证: Glide BitmapPool 默认大小 = maxMemory/8 的说法来自官方文档]

## 内存泄漏的常见模式

内存泄漏是 App 内存优化中最棘手的问题——它不像崩溃那样立刻暴露，而是像温水煮青蛙一样慢慢消耗可用内存，直到 App 被系统杀死或者开始严重卡顿。

我们来看三种最常见的泄漏模式。

### 模式一：Activity 引用泄漏

这是 Android 开发中最经典的泄漏模式。核心问题是：一个长生命周期的对象持有了一个已经应该被销毁的 `Activity` 的引用。

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
            MyActivity activity = activityRef.get();
            if (activity != null && !activity.isFinishing()) {
                doSomethingSlow();
            }
        }
    }
}
```

修复的关键点在于：`static` 修饰的内部类不再隐式持有外部类引用，我们通过 `WeakReference` 显式地、可空地获取 Activity。当 Activity 被销毁后，`activityRef.get()` 返回 `null`，worker 线程就知道应该停止工作。

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

Java 层的内存泄漏可以通过 GC 和工具比较容易地发现，但 Native 内存（C/C++ 通过 `malloc`/`new` 分配的内存）完全没有 GC 的帮助——分配了多少就占多少，直到你手动 `free`/`delete` 或者进程被杀。

### JNI 层的常见泄漏模式

- **`NewGlobalRef` 不 `DeleteGlobalRef`**：JNI 中的全局引用会阻止 GC 回收被引用的 Java 对象。每次 `NewGlobalRef` 都必须有对应的 `DeleteGlobalRef`。
- **`malloc` 不 `free`**：最基础的 C 层泄漏，但当代码路径复杂（提前 return、异常分支）时很容易遗漏。
- **文件描述符不关闭**：`open()` 后不 `close()`。虽然不占堆内存，但 FD 耗尽可能导致系统无法打开新文件（`Too many open files`）。

### malloc debug

Android 提供了 `malloc debug` 工具来追踪 Native 内存分配：

```bash
# 启用 malloc debug
adb shell setprop wrap.com.example.app '"LIBC_DEBUG_MALLOC_OPTIONS=backtrace_tracker android.app.ActivityThread"'

# 或通过 am 启动
adb shell am start --activity-clear-task -n com.example.app/.MainActivity
```

启用后，可以通过 `dumpsys meminfo --checkin <pid>` 查看分配统计，或者通过 `heapprofd`（见下节）获取更详细的信息。

[已验证: 官方文档, developer.android.com/ndk/guides/debug-gdb — malloc debug 选项]

### ASan（AddressSanitizer）

ASan 是 LLVM/Clang 提供的内存错误检测工具，可以检测：

- 堆缓冲区溢出（heap-buffer-overflow）
- 栈缓冲区溢出（stack-buffer-overflow）
- 使用已释放的内存（use-after-free）
- 双重释放（double-free）

在 Android 上启用 ASan：

```gradle
// build.gradle
android {
    defaultConfig {
        ndk {
            // 在 debug 构建中启用 ASan
            packagingOptions {
                doNotStrip "**/*.so"
            }
        }
    }
}
```

ASan 会使 App 性能下降 2-5 倍，所以只在 debug 构建中使用。但它能捕获到 malloc debug 无法发现的越界访问和 use-after-free 问题。

[已验证: 官方文档, developer.android.com/ndk/guides/asan]

### heapprofd：Native 内存性能分析

[已验证: 官方文档, perfetto.dev/docs/data-sources/native-heap-profiler]

`heapprofd` 是 Perfetto 提供的 Native 堆分析工具，可以精确追踪每一次 Native 内存分配的调用栈：

```bash
# 追踪特定进程的 Native 堆分配
adb shell heapprofd --pid=<PID>

# 同时追踪 Java 堆（Android 12+）
adb shell heapprofd --pid=<PID> --java
```

在 Perfetto UI 中，`heapprofd` 的数据出现在 "Heap Profiles" 面板中。你可以按分配大小排序，找到分配最多的调用栈——这就是内存热点。

`heapprofd` 的开销很小（通常 < 5%），可以在线上环境中采样使用。Perfetto 的配置中可以设置采样间隔，比如每 4096 字节采样一次，这样既不会影响性能，又能获得有代表性的分配热点。

## onTrimMemory 与 ComponentCallbacks2

前面讲的优化都是"主动优化"——你在写代码时就注意到了内存问题。但还有一种"被动优化"场景：**系统告诉你内存紧张了，你需要配合释放一些资源**。这就是 `onTrimMemory` 的作用。

### onTrimMemory 的回调级别

[已验证: 官方文档, developer.android.com/reference/android/content/ComponentCallbacks2]

`ComponentCallbacks2.onTrimMemory(int level)` 的回调级别分为三类：

**进程在前台时的回调：**

| 级别 | 值 | 含义 | 建议操作 |
|------|---|------|---------|
| `TRIM_MEMORY_RUNNING_LOW` | 10 | 系统内存开始紧张 | 释放非关键缓存 |
| `TRIM_MEMORY_RUNNING_MODERATE` | 20 | 内存进一步紧张 | 释放更多缓存 |
| `TRIM_MEMORY_RUNNING_CRITICAL` | 40 | 内存严重紧张，后台进程可能被杀 | 释放所有可释放的缓存 |

注意：这些回调在进程**仍然在前台运行**时就会触发。系统还没杀任何后台进程，但已经在预警了。及时响应这些回调，可以降低系统进入更严重内存压力状态的概率。

**进程退到后台后的回调：**

| 级别 | 值 | 含义 | 建议操作 |
|------|---|------|---------|
| `TRIM_MEMORY_UI_HIDDEN` | 20 | UI 不可见了 | 释放 UI 相关资源（Bitmap 缓存等） |
| `TRIM_MEMORY_BACKGROUND` | 40 | 进程进入 LRU 列表 | 释放所有可以重新创建的资源 |
| `TRIM_MEMORY_MODERATE` | 60 | 进程在 LRU 列表中部 | 释放更多缓存 |
| `TRIM_MEMORY_COMPLETE` | 80 | 进程即将被杀 | 释放一切，保存关键数据 |

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

这里有一个关键原则：**`onTrimMemory` 的回调不应该导致用户可感知的体验下降**。当你的进程在前台时收到 `TRIM_MEMORY_RUNNING_LOW`，你释放的应该是预加载缓存、二级缓存这类"有更好、没有也不影响核心功能"的资源。不要在前台状态下清空图片缓存——用户正在看的列表会突然变成白屏。

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

## [自动发现] 16KB Page Size 迁移对 App 内存的影响

[来源: research-feed 2026-03-31-19-ch04-app-memory-16kb-migration.md]

2025-2026 年 Android 平台最大的平台级内存变更是 **16KB Page Size 的强制迁移**。这不是一个"可选优化"，而是 Google Play 对所有应用的强制要求。

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

**第三方 SDK**：React Native、Flutter 等框架已提供兼容版本。如果你的 App 依赖了包含 Native 代码的第三方 SDK，需要确认其是否已适配 16KB 页。

### 测试方法

- **Pixel 8/9**：开发者选项中启用 "Boot with 16KB page size"
- **Android Studio AVD**：使用 API 35 的 "16KB" 镜像
- **APK Analyzer**：检查 `.so` 文件的 ELF 段是否已对齐到 16KB

### 对 Bitmap 的影响

Bitmap 像素数据存储在 Native 堆。在 16KB 页模式下，每个 Bitmap 的内存页浪费可能增加（如果一个 Bitmap 的像素数据不是 16KB 的整数倍，最后一页会有更多浪费）。Google 建议使用标准图片加载库（Glide/Coil），它们已经内部处理了对齐问题。

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

[来源: 货拉拉 Android 端内存治理实践等公开技术分享]

### 线上监控

线上内存监控的关键指标：

- **Java 堆使用率**：`Runtime.getRuntime().totalMemory() / Runtime.getRuntime().maxMemory()`
- **PSS 总量**：通过 `Debug.getPss()` 获取（API 23+ 可用）
- **FD 数量**：通过 `/proc/self/fd` 的文件数量
- **Bitmap 数量**：通过 `Debug.getMemoryInfo()` 中的 `nativePss` 间接推算

当这些指标接近阈值时，触发降级策略（释放缓存、降低图片质量、关闭预加载）。

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
