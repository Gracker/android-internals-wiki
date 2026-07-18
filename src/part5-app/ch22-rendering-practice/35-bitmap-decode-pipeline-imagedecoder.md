---
title: "Bitmap 解码管线性能与 ImageDecoder 实战"
chapter: "22.35"
status: ready-for-review
drafted_date: "2026-07-18"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-18"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/ImageDecoder.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapFactory.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapRegionDecoder.java"
  - type: aosp
    path: "frameworks/base/core/jni/android/graphics/ImageDecoder.cpp"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/ImageDecoder"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/BitmapFactory.Options"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/BitmapRegionDecoder"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
tags: [bitmap, image-decoder, decode-pipeline, hardware-bitmap, image-format, mmap, inbitmap]
related_chapters: ["22.6", "22.17", "23.2", "7.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "章节深挖"
---

# 22.35 Bitmap 解码管线性能与 ImageDecoder 实战

<!-- outline-start -->
## 要点

### 🔹 ImageDecoder API 架构与 BitmapFactory 对比
### 🔹 硬件位图 (Hardware Bitmap) 解码路径与 GPU 上传
### 🔹 图片格式解码性能：PNG / WebP / HEIF / AVIF 对比
### 🔹 解码线程调度：专用线程 vs 线程池 vs 协程
### 🔹 内存映射解码与 mmap 在图片加载中的应用
### 🔹 inBitmap 复用对解码性能与内存的双重收益
### 🔹 Bitmap 内存模型：Android 17 下的 ashmem 与 dma_buf
### 🔹 解码性能指标采集：FrameMetrics + Perfetto 双轨方案

## 扩展

### 🔸 九宫格/瀑布流场景的解码调度策略
### 🔸 Glide / Coil / Picasso 解码管线对比
### 🔸 Android 17 ImageDecoder 新增 API 与行为变更

<!-- outline-end -->

本章聚焦解码管线本身——从压缩数据到像素 Buffer 的全过程。图片加载框架选型和缓存策略详见 22.6 节；Hardware Bitmap 进入 HWUI/RenderNode 的渲染流程详见 22.17 节；Bitmap 与 Native 内存统计治理详见 23.2 节。

[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]
[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]

## ImageDecoder API 架构与 BitmapFactory 对比

`BitmapFactory` 从 API 1 就存在，是 Android 最底层的图片解码入口。它的设计是同步、单次调用：传入文件路径或 byte 数组，拿到 `Bitmap`。缺点也由此而来——调用方在解码前无法基于图片 header 做决策，必须先用 `inJustDecodeBounds` 做一轮"试探解码"拿到宽高，再发起正式解码。两轮解码之间，调用方要自己管理状态。

`ImageDecoder` 从 API 28 (Android 9) 引入，设计目标是把"读 header → 做决策 → 解码"合并到一个异步回调中。核心入口是 `ImageDecoder.decodeBitmap(source, listener)`，在 `OnHeaderDecodedListener` 回调里，调用方拿到 `ImageDecoder` 对象和 `ImageInfo`（包含尺寸、 mimeType 等），可以一次性设置目标尺寸、采样率、allocator、色彩空间等参数，然后由系统完成解码。

[已验证: 官方文档, developer.android.com/reference/android/graphics/ImageDecoder]

两者的关键架构差异：

| 维度 | BitmapFactory | ImageDecoder |
| --- | --- | --- |
| Header 读取 | `inJustDecodeBounds = true` 两轮调用 | `OnHeaderDecodedListener` 单次回调 |
| 尺寸控制 | `inSampleSize`（仅 2 的幂次降采样） | `setTargetSize()` + `setSampleSize()`（任意整数） |
| Allocator | 无选择权 | `ALLOCATOR_DEFAULT` / `ALLOCATOR_SOFTWARE` |
| 部分解码 | 不支持 | `setCropRect()` 支持输出裁剪 |
| 动图 | 需手动分帧 | `decodeDrawable` 支持动画（GIF/WebP） |
| 错误处理 | 返回 null 或抛 OOM | `OnPartialImageListener` 允许接受部分解码结果 |
| 废弃状态 | API 11 起 `BitmapFactory` 未新增能力 | 持续接收新功能 |

工程上的迁移判断：

- **新代码优先 ImageDecoder**。API 28 以下的兼容可以 fallback 到 BitmapFactory，或依赖 Glide/Coil 等框架内部的版本适配。
- **存量 BitmapFactory 不必强行替换**。如果现有代码已稳定且用 `inSampleSize` + `inBitmap` 做了优化，替换的收益主要在代码简洁度，不在运行时性能。
- **图片库内部已做适配**。Glide 4.x 和 Coil 2.x 在 API 28+ 会优先走 ImageDecoder 路径。应用层直接调 API 的场景主要是自定义解码管线或特殊格式处理。

[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/ImageDecoder.java]
[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/BitmapFactory.java]

下面这段代码展示了 ImageDecoder 的基本用法，重点是 `OnHeaderDecodedListener` 内的尺寸决策：

```kotlin
@RequiresApi(Build.VERSION_CODES.P)
fun decodeImage(source: ImageDecoder.Source, reqWidth: Int, reqHeight: Int): Bitmap {
    return ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
        val srcW = info.size.width
        val srcH = info.size.height
        // 计算目标尺寸，保留宽高比
        val scale = minOf(
            reqWidth.toFloat() / srcW,
            reqHeight.toFloat() / srcH,
            1f
        )
        decoder.setTargetSize(
            (srcW * scale).toInt().coerceAtLeast(1),
            (srcH * scale).toInt().coerceAtLeast(1)
        )
        // 如果只用于屏幕绘制，使用默认 allocator（可能产生 Hardware Bitmap）
        // 需要像素读写时切换到 SOFTWARE
        // decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
    }
}
```

`ImageDecoder.Source` 可以从 ByteBuffer、File、ContentResolver、ByteArray 等创建。从文件创建时，系统内部会使用 `mmap` 读取数据，减少一次内存拷贝；从 ByteBuffer 创建时，数据需要在 JVM 堆或 Direct ByteBuffer 中。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/android/graphics/ImageDecoder.cpp]

## 硬件位图 (Hardware Bitmap) 解码路径与 GPU 上传

22.17 节从渲染侧解释了 Hardware Bitmap 如何省掉 RenderThread 的 texture upload。这一节从解码侧补充：Hardware Bitmap 是怎么产生的，以及解码管线的哪些选择会影响它。

Android 8.0 (API 26) 引入了 `Bitmap.Config.HARDWARE`。当解码器使用 `ALLOCATOR_DEFAULT`（ImageDecoder 的默认值）时，系统在支持设备上会尝试把解码结果直接放入 `AHardwareBuffer`，而不是普通 Native heap。这条路径产出的就是 Hardware Bitmap。

[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/Bitmap.java]

解码侧的关键约束：

1. **不可变**：Hardware Bitmap 是 immutable 的，不能用于需要 `eraseColor`、`setPixels` 或 `Canvas` 软件绘制的场景。
2. **不可 CPU 读写**：`getPixel()`、`copyPixelsToBuffer()` 等操作会抛 `IllegalStateException`。如果业务需要读取像素（如分享、截图、取色），必须确保解码时使用 `ALLOCATOR_SOFTWARE`。
3. **图片格式限制**：某些格式（如带 alpha 的 WebP 动画、部分 PNG 间色模式）可能不支持硬件解码路径，系统会静默 fallback 到软件解码。应用层不应假设 `ALLOCATOR_DEFAULT` 一定产出 Hardware Bitmap。
4. **设备依赖**：低 RAM 设备或特定 GPU 驱动可能禁用硬件位图。Glide 和 Coil 都提供了按设备禁用的配置项。

解码管线的工程决策：

- **只上屏的图**（信息流封面、头像、详情页静态图）→ `ALLOCATOR_DEFAULT`，让系统尝试 Hardware Bitmap。
- **需要后处理的图**（圆角 CPU 变换、滤镜、截图分享、Palette 取色）→ `ALLOCATOR_SOFTWARE`，确保拿到可读写的像素。
- **不确定时**→ 交给图片库处理。Glide 默认在 API 26+ 启用 Hardware Bitmap；Coil 同样默认启用。框架会根据 Transformation 配置自动决定。

[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

## 图片格式解码性能：PNG / WebP / HEIF / AVIF 对比

22.6 节从格式选型角度介绍了 AVIF/WebP 兼容性。这一节从解码管线角度补充各格式的解码成本差异。

解码成本不等同于文件大小。一张 AVIF 可能比同质量的 JPG 小 50%，但如果目标设备的 AVIF 解码器比 JPG 解码器慢 3 倍，首帧时间反而更差。解码成本取决于：

- **压缩复杂度**：PNG 使用 DEFLATE 无损压缩，解码需要 inflate + 颜色还原；JPEG 使用 DCT 有损压缩，需要 IDCT + 色彩空间转换；WebP 基于 VP8 帧内编码，解码步骤更多但优化更成熟；HEIF/AVIF 基于 H.265/AV1 帧内编码，解码器依赖硬件加速。
- **硬件解码支持**：部分 SoC 有专用 JPEG/H.264/H.265 硬件解码单元。软件解码 AVIF 在中低端设备上可能比 JPEG 慢 2-5 倍。
- **内存峰值**：渐进式 JPEG 和 WebP 可以流式解码；AVIF 的 AV1 解码器需要更大的中间缓冲区。

各格式在 Android 平台的支持版本：

| 格式 | 支持版本 (编码/解码) | ImageDecoder 支持 | BitmapRegionDecoder 支持 |
| --- | --- | --- | --- |
| JPEG | API 1+ | ✓ | ✓ |
| PNG | API 1+ | ✓ | ✓ |
| WebP (lossy) | API 14+ (解码) / API 18+ (编码) | ✓ | ✓ (API 14+) |
| WebP (lossless) | API 18+ | ✓ | ✓ |
| HEIF | API 28+ | ✓ | ✓ (API 28+) |
| AVIF | API 31+ (基础解码) | ✓ (API 31+) | ✓ (API 17+, 参见 22.6 节) |

[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/BitmapRegionDecoder.java — 格式列表由 native 层 SkBitmapRegionDecoder 决定]

实践建议：

- **线上测量同图多格式解码耗时**，不要只看文件大小。至少覆盖 P25/P50/P90 三档设备。
- **服务端按设备能力下发格式**。通过 Client Hints 或 URL 参数协商，低端机继续下发 WebP/JPG，高端机尝试 AVIF。
- **解码缓存**：同一张图的解码结果在内存缓存中是最终 Bitmap，格式不再影响后续缓存命中。格式选择影响的是首次解码耗时和下载字节数。
- **AVIF 在 Android 17 的区域解码**：`BitmapRegionDecoder` 在 Android 17 源码中明确列出 AVIF 支持。低版本需要 fallback 到 WebP/JPG。详见 22.6 节的格式选型分析。

[已验证: 官方文档, developer.android.com/reference/android/graphics/BitmapRegionDecoder]

## 解码线程调度：专用线程 vs 线程池 vs 协程

图片解码是 CPU 密集型操作，不能在主线程执行。但用什么样的后台线程模型，直接影响列表滑动的帧稳定性。

三种常见调度模型：

### 专用解码线程

```kotlin
private val decodeThread = HandlerThread("image-decode").apply { start() }
private val decodeHandler = Handler(decodeThread.looper)
```

优点：解码任务串行执行，不会争抢 CPU；线程优先级可独立设置。
缺点：并发度受限，多图同时请求时排队等待。

适合：详情页单图、头像加载等低并发场景。

### 线程池（Fixed / Cached）

```kotlin
private val decodePool = Executors.newFixedThreadPool(2) // 或按 CPU 核数
```

优点：多图并行解码，吞吐高。
缺点：线程数控制不当会抢占主线程 CPU 时间片，导致掉帧；Bitmap 分配抖动。

适合：九宫格、瀑布流等中等并发场景。线程数建议 `min(availableProcessors - 1, 4)`。

### 协程（Dispatchers.IO）

```kotlin
suspend fun decodeAsync(path: String): Bitmap = withContext(Dispatchers.IO) {
    BitmapFactory.decodeFile(path)
}
```

优点：生命周期跟随 CoroutineScope，取消语义清晰。
缺点：`Dispatchers.IO` 默认 64 线程上限（Android），大量图片解码任务可能与其他 IO 任务互相干扰；需要用 `limitedParallelism()` 限制并发。

适合：与业务逻辑紧耦合的单图解码（如 Compose `LaunchedEffect` 中触发）。

[自动发现] Android 13 (API 33) 起，`Dispatchers.IO` 可以通过 `limitedParallelism(n)` 创建子调度器。图片解码建议用 `Dispatchers.IO.limitedParallelism(2)` 隔离，避免与网络 IO 竞争线程。

[已验证: Kotlin Coroutines docs, limitedParallelism (since 1.6)]

Glide 内部使用固定大小的线程池（默认 4 线程，可通过 `GlideExecutor.newDiskCacheExecutor()` 定制）。Coil 依赖协程，解码在 `Dispatchers.IO` 上执行，默认不限制并发，但可以通过自定义 `ImageLoader` 的 coroutineContext 控制。

实践建议：

- **列表解码用框架内置调度**，不要在业务层另起线程池。框架的线程池和缓存、生命周期是配合设计的。
- **自定义解码管线的并发度**要按设备 CPU 核数分档。低端机（≤4 核）限制 1-2 并发；中高端机可以 3-4。
- **优先级**：使用 `Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND)` 或 `THREAD_PRIORITY_LESS_FAVORABLE`，让解码线程在主线程繁忙时让出 CPU。
- **取消机制**：列表快速滑动时，旧 item 的解码任务必须能取消。`BitmapFactory.decodeFile` 本身不可中断；ImageDecoder 也没有内置取消。框架通常通过竞争条件处理：解码完成后检查 target 是否仍然有效，无效则丢弃结果。

## 内存映射解码与 mmap 在图片加载中的应用

当图片数据来自文件时，传统的读取方式是 `open + read`，数据从内核空间拷贝到用户空间 buffer，再传给解码器。`mmap` 把文件映射到虚拟内存地址空间，解码器直接从映射区域读取数据，省掉一次内核→用户空间的数据拷贝。

Android 的 `BitmapFactory.decodeFile()` 内部走的是 `SKAutoMalloc` 分配，即把文件内容读入一块 malloc 的 buffer，再交给 Skia 解码器。`ImageDecoder.createFromSource()` 在 native 实现中，如果 Source 是文件路径，会使用 `SkData::MakeFromFileName()`，后者在 Android 平台上通过 `mmap` 实现。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/android/graphics/ImageDecoder.cpp — createFromSource 路径使用 SkData]

mmap 解码的实际收益：

- **大图文件**：减少一次完整的文件读取。对于 5MB 以上的图片文件，mmap 可以让解码器按需读取页面，而不是一次性把整个文件载入内存。
- **内存峰值**：mmap 的页面按需载入（demand paging），不会在调用时立即占用全部文件大小的物理内存。
- **多图并发**：多个解码任务映射同一文件时，内核只维护一份 page cache。

注意事项：

- **网络图片不适用**：mmap 只能用于本地文件。网络图片下载到磁盘后，可以通过文件路径走 mmap 路径。Glide 的磁盘缓存解密后写入临时文件，再解码时可以受益。
- **ImageDecoder 必须从文件 Source 创建**才能走 mmap 路径。从 ByteBuffer 创建时，数据已在 JVM/Direct buffer 中，不会触发 mmap。
- **ContentResolver 来源**：ImageDecoder 可以从 `content://` URI 创建 Source。内部会先打开 InputStream，再决定是否拷贝到临时文件或直接流式读取。大图场景下，如果 ContentProvider 返回的 InputStream 支持 `seek`，系统可能选择 mmap 路径。

## inBitmap 复用对解码性能与内存的双重收益

`inBitmap` 是 `BitmapFactory.Options` 的一个字段，允许解码器把新图片的像素写入一块已有的 Bitmap 内存区域，而不是分配新的。`ImageDecoder` 通过 `decoder.setTargetBitmap(reusableBitmap)` 支持同样的复用。

[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/BitmapFactory.java]

复用的核心收益：

1. **减少内存分配**：避免每次解码都 calloc 一块新内存。高频列表滚动时，每秒可能产生几十次解码，每次分配几百 KB 到几 MB 的 Native 内存。
2. **减少 GC 压力**：Android 8.0 后 Bitmap 像素内存在 Native 侧，通过 `NativeAllocationRegistry` 管理。频繁分配/释放会触发 GC 和 Native 内存回收抖动。
3. **减少内存碎片**：长期运行的应用，反复分配和释放不同大小的 Bitmap 内存会导致 Native heap 碎片化。复用固定大小的 Bitmap 可以缓解碎片问题。

inBitmap 复用的约束（API 级差异）：

| API 版本 | 约束 |
| --- | --- |
| API 11-18 | 仅支持相同尺寸的 Bitmap 复用 |
| API 19+ | 支持复用更大的 Bitmap（被解码图 ≤ 已有 Bitmap 的 `allocationByteCount`） |
| API 26+ | Hardware Bitmap 不支持 inBitmap（不可变） |

实践建议：

- **交给框架管理**：Glide 的 `BitmapPool` 和 Coil 的 `MemoryCache` 都内置了 Bitmap 复用逻辑。应用层手动管理复用池容易出错（特别是复用仍在展示的 Bitmap 会导致花屏）。
- **ImageDecoder 的复用**：`setTargetBitmap()` 要求目标 Bitmap 是 mutable 的，且 `allocationByteCount` ≥ 解码目标大小。解码器不会自动缩放源图来匹配目标 Bitmap 尺寸。
- **监控指标**：如果自行管理复用池，监控池命中率（reuse count / decode count）。命中率低于 30% 说明池大小或 Bitmap 规格配置不当。

[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md — NativeAllocationRegistry 原理]

## Bitmap 内存模型：Android 17 下的 ashmem 与 dma_buf

Android 各版本中 Bitmap 像素内存的存放位置经历了多次变更：

| 版本 | 存放位置 | 说明 |
| --- | --- | --- |
| API 1-2 | Java heap (byte[]) | GC 管理但占用 Java 堆 |
| API 3-7 | Native heap (malloc/calloc) | 不受 GC 直接管理，需要手动 recycle |
| API 8-10 | Native heap + NativeAllocationRegistry | Java 对象回收时自动释放 Native 内存 |
| API 11-25 | Native heap (SkMallocPixelRef) | NativeAllocationRegistry 逐步完善 |
| API 26+ | Native heap 或 AHardwareBuffer | `HARDWARE` config 的像素在 graphics memory |

Android 17 (API 37) 中，普通 Bitmap（`ARGB_8888` / `RGB_565` / `ALPHA_8` / `RGBA_F16`）的像素仍存储在 Native heap，通过 `NativeAllocationRegistry` 与 Java `Bitmap` 对象关联。Hardware Bitmap 的像素存储在 `AHardwareBuffer` 管理的 graphics memory 中。

[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/Bitmap.java — 构造函数中 NativeAllocationRegistry 注册]

关于 ashmem 和 dma_buf：

- **ashmem**（Anonymous Shared Memory）：Android 早期的匿名共享内存机制。在 Android 10 之前的 Bitmap 内存模型中，部分场景使用 ashmem 区域存放像素数据（特别是跨进程传递的 Bitmap）。Android 10+ 逐步用 `memfd` 替代 ashmem。
- **dma_buf**：Linux 内核的 DMA 缓冲共享框架。Hardware Bitmap 的 `AHardwareBuffer` 底层依赖 `dma_buf` 实现跨进程、跨硬件模块（GPU、display controller、camera）的缓冲共享。
- **Android 17 的变化**：ashmem 在应用层 Bitmap 中的使用已非常少见。普通 Bitmap 主要走 SkMallocPixelRef → Native malloc 路径。`AHardwareBuffer` 在 API 26+ 成为 Hardware Bitmap 的标准后端。

从内存统计角度：

- 普通 Bitmap 的像素计入 `HEAP_NATIVE` 或 `HEAP_OTHER`（取决于 `Debug.getMemoryInfo` 的分类）。
- Hardware Bitmap 的像素计入 `HEAP_GRAPHICS`（通过 `libmemtrack` 查询）。
- `Debug.MemoryInfo` 中的 `graphics` 和 `gl` 字段分别反映 graphics memory 和 GL memory 的使用量。

[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md — graphic 内存数据来源]

Bitmap 内存治理的具体方法详见 23.2 节。

## 解码性能指标采集：FrameMetrics + Perfetto 双轨方案

解码性能的线上/线下观测需要两套互补的指标体系。

### 线上：FrameMetrics

`Window.OnFrameMetricsAvailableListener` 从 API 24+ 提供每帧的详细耗时数据。与解码相关的字段：

- `FrameMetrics.LAYOUT_DRAW_TIME`：包含 measure + layout + draw 的总时间。解码如果阻塞主线程（例如错误地在主线程解码），会反映在这里。
- `FrameMetrics.DRAW_TIME`：仅绘制阶段耗时。Hardware Bitmap 减少的 texture upload 时间主要体现在这里。
- `FrameMetrics.SWAP_BUFFERS_TIME`：交换缓冲区耗时。GPU 资源过多时可能变长。

```kotlin
window.addOnFrameMetricsAvailableListener(
    this,
    { _, frameMetrics, _ ->
        val drawTime = frameMetrics.getMetric(FrameMetrics.DRAW_TIME)
        val totalDraw = frameMetrics.getMetric(FrameMetrics.LAYOUT_DRAW_TIME)
        // 上报到 APM 平台，按页面/场景分桶统计
    },
    Handler(HandlerThread("metrics").looper)
)
```

注意 FrameMetrics 反映的是主线程和 RenderThread 的帧时间，不直接包含后台解码线程的耗时。解码线程的耗时要通过自定义 trace 或采样单独采集。

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

### 线下：Perfetto

Perfetto 是解码性能分析的精确工具。关键 trace 类别：

- **`android.graphics.Bitmap` track**：AOSP 在 Android 12+ 加入了 Bitmap 分配的 trace point（`Bitmap#allocateColorBuffer WxH`），可以观察每次 Bitmap 分配的尺寸和时机。
- **`android.graphics.ImageDecoder` track**：ImageDecoder 解码阶段的 trace（`ImageDecoder#decode`），包含格式识别、header 读取、像素解码的总耗时。
- **RenderThread track**：`DrawFrame`、`syncFrameState`、`Upload` slice 可观察 texture upload 成本。22.17 节有详细说明。
- **CPU track + sched**：配合 ` sched/cpu` track，可以确认解码线程的 CPU 占用是否影响了主线程调度。

Perfetto 查询示例——统计一次 trace 中所有 Bitmap 分配的像素总量：

```sql
SELECT
    SUM(EXTRACT_ARG(slice.arg_set_id, 'width') *
        EXTRACT_ARG(slice.arg_set_id, 'height') * 4) AS total_pixels_bytes,
    COUNT(*) AS alloc_count
FROM slice
WHERE name GLOB 'Bitmap#allocate*'
```

Perfetto 解码分析的实战步骤：

1. 录制包含 `android.graphics` + `gpu` + `sched` + `binder` 类别的 trace。
2. 在 UI 中定位到出现卡顿的帧（`FrameTimeline` track 标红）。
3. 检查该帧前后的 `ImageDecoder#decode` slice 耗时。
4. 检查 RenderThread 的 `Upload` slice 是否出现在该帧。
5. 检查 CPU track 中解码线程的优先级和调度情况。

Perfetto 的 SQL 查询手册与实战查询库详见 13.22 节。

[已验证: AOSP android-17.0.0_r1 — Bitmap/ImageDecoder trace point 在 frameworks/base/graphics 目录源码中]

## 九宫格/瀑布流场景的解码调度策略

[扩展]

九宫格和瀑布流是图片解码压力最大的场景。同屏可能同时有 6-12 张图片需要解码，加上预取策略可能达到 20+ 张待解码任务。

核心矛盾：解码并发度 vs 帧稳定性。并发度越高，单位时间吞吐越大，但 CPU 时间片竞争越激烈，主线程绘制帧可能因此掉帧。

推荐的调度策略：

1. **优先级队列**：视口内的图片优先级最高，视口边缘 ±1 屏的预取次之，更远的预取最低。滑动方向上的预取优先级应高于反方向。
2. **动态并发度**：根据 `Choreographer` 的帧间隔动态调整。帧间隔稳定（≤16ms）时提高并发度；帧间隔抖动时降低并发度或暂停预取。
3. **按尺寸分桶**：缩略图（≤200dp）用小并发线程池（2-3 线程），中图（200-500dp）用 1-2 线程，大图（>500dp）串行解码。避免多个大图同时解码导致内存峰值。
4. **内存预算**：设定解码 Bitmap 的总内存预算（如 PSS 的 10-15%），超过预算时拒绝新解码请求，只走缓存。

Glide 的 `RecyclerViewPreloader` 和 Coil 的 `AsyncImage` 都支持部分策略，但动态并发度和内存预算需要应用层配合。

## Glide / Coil / Picasso 解码管线对比

[扩展]

| 维度 | Glide 4.x | Coil 2.x/3.x | Picasso 2.x |
| --- | --- | --- | --- |
| 解码入口 | API 28+ 使用 ImageDecoder，低版本 BitmapFactory | API 28+ 使用 ImageDecoder | 仅 BitmapFactory |
| Hardware Bitmap | 默认启用（API 26+），可按 Request 关闭 | 默认启用 | 不支持 |
| Bitmap 复用 | `BitmapPool` + `inBitmap`，池策略可定制 | 依赖 `MemoryCache` 的 eviction 策略 | 无内置复用 |
| 线程调度 | 固定线程池（默认 4 线程），优先级可配置 | 协程 `Dispatchers.IO` | `Dispatcher` 线程池（默认 3 线程） |
| 缓存层级 | Active + Memory + Disk (resource/data) | Memory + Disk | Memory + Disk |
| 格式支持 | 依赖系统解码器，可注册自定义 `ResourceDecoder` | 依赖系统解码器 | 依赖系统解码器 |
| 维护状态 | 活跃 | 活跃 | 停更（2.8 为最后版本） |

选型建议：

- **新项目**：Coil（Compose-first，协程友好）或 Glide（成熟稳定，View/RecyclerView 场景积累深）。
- **已有 Picasso 的项目**：如果解码性能不是瓶颈，不必迁移。Picasso 的架构简洁，维护成本低。需要 Hardware Bitmap 或更精细的 Bitmap 复用时再考虑迁移。
- **自定义解码管线**：如果业务需要特殊格式（如医疗影像、RAW 图片），评估直接使用 ImageDecoder + 自建缓存和调度。

解码管线内部细节（框架通用模式）：

1. 从缓存/网络/磁盘获取原始数据（byte stream / ByteBuffer / File）
2. 根据设备和 API 版本选择解码器（ImageDecoder vs BitmapFactory）
3. 计算目标尺寸和采样率（从 Target/View 尺寸推导）
4. 检查 BitmapPool 中是否有可复用的 Bitmap
5. 执行解码
6. 应用 Transformation（圆角、裁剪、滤镜等，可能降级为软件 Bitmap）
7. 将结果存入 active resources / memory cache
8. 回调到主线程更新 UI

[已验证: Glide docs, bumptech.github.io/glide]
[已验证: Coil docs, coil-kt.github.io]

## Android 17 ImageDecoder 新增 API 与行为变更

[扩展]

Android 17 (API 37) 对 ImageDecoder 的主要变化：

1. **AVIF 区域解码**：`BitmapRegionDecoder` 在 Android 17 源码中正式列出 AVIF 格式支持。之前版本需要通过 `isSupported(ImageDecoder.Source)` 或 try-catch 判断。
2. **Allocator 行为一致性**：`ALLOCATOR_DEFAULT` 在更多设备上优先尝试 Hardware Bitmap 路径。但系统保留 fallback 权利，应用不应假设一定产出 Hardware Bitmap。
3. **`setTargetColorSpace()`**：Android 17 中 ImageDecoder 对广色域（Wide Gamut）图片的色彩空间处理更完善。如果应用窗口配置为 `colorMode = COLOR_MODE_WIDE_COLOR_GAMUT`，解码时设置 `setTargetColorSpace(ColorSpace.get(ColorSpace.Named.DISPLAY_P3))` 可以减少绘制时的色彩空间转换成本。
4. **错误恢复**：`OnPartialImageListener` 在遇到损坏文件的容错性提升。对于渐进式 JPEG，可能在部分数据可用时就产出较低质量的 Bitmap。

[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/ImageDecoder.java]

## 小结

Bitmap 解码管线的性能优化可以归纳为三条主线：

- **解对尺寸**：在解码前通过 ImageDecoder 的 `OnHeaderDecodedListener` 或 BitmapFactory 的 `inJustDecodeBounds` 决定目标尺寸，避免解码后立即缩放。
- **选对路径**：只上屏的图走 `ALLOCATOR_DEFAULT`（可能产出 Hardware Bitmap），需要后处理的图走 `ALLOCATOR_SOFTWARE`。格式选择不只看文件大小，还要看目标设备的解码耗时。
- **管好线程和内存**：解码线程并发度按设备分档，列表场景用优先级队列 + 动态并发度。Bitmap 复用交给框架，线上用 FrameMetrics、线下用 Perfetto 双轨监控。

图片加载框架选型和缓存策略详见 22.6 节；Hardware Bitmap 进入 HWUI 的渲染流程详见 22.17 节；Bitmap 内存统计与治理详见 23.2 节。
