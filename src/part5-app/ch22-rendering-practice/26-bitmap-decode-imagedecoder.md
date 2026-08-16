---
title: "Bitmap 解码、Hardware Bitmap 与 RenderNode"
chapter: "22.26"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1, Android API 37"
confidence: medium
consolidated_from:
  - "src/part2-performance/ch07-smoothness/10-image-bitmap-performance.md"
  - "src/part5-app/ch22-rendering-practice/17-hardware-bitmap-rendernode.md"
sources:
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/ImageDecoder.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapFactory.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Gainmap.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapRegionDecoder.java"
  - type: aosp
    path: "frameworks/base/libs/hwui/jni/ImageDecoder.cpp"
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
related_chapters: ["22.6", "23.2"]
---

# Bitmap 解码、Hardware Bitmap 与 RenderNode

> **源码锚点**
>
> - 平台：Android 17 / API 37 / `android-17.0.0_r1`
> - 内核：`android17-6.18-2026-06_r6`
> - Java API：`ImageDecoder.java`、`BitmapFactory.java`、`Bitmap.java`
> - Native 实现：`frameworks/base/libs/hwui/jni/ImageDecoder.cpp`、`BitmapFactory.cpp`
>
> 这里的“Android 17 行为”以这些源码为准。编解码器实现、图形内存分配和内存统计还会受 SoC（片上系统）、厂商图形缓冲分配器 `gralloc` 与驱动影响，因此设备实测仍是性能结论的一部分。

讨论范围是压缩图片数据如何变成可绘制像素，以及这些像素如何进入 Android 17 的 HWUI（Android 硬件加速 UI 渲染器）路径。图片请求、缓存与框架选型见 [22.6 图片加载](./06-image-loading.md)；本文同时覆盖 Hardware Bitmap 与 RenderNode 的绘制侧行为，Bitmap 内存治理见 [23.2 Bitmap 优化](../ch23-memory-practice/02-bitmap-optimization.md)。

## 1. 一次解码包含哪些工作

一次静态图片解码至少包含以下工作：

1. 从文件描述符、流、字节数组或 `ByteBuffer` 读取压缩数据；
2. 识别格式并解析头信息，得到原始尺寸、MIME 类型、动画与色彩空间信息；
3. 根据目标尺寸、采样、裁剪、色彩空间和内存策略确定输出规格；
4. 编解码器把压缩数据还原成可写像素；
5. 按需要执行缩放、裁剪、色彩转换、增益图提取或 `PostProcessor`；
6. 把结果放入普通原生堆（native heap）、共享内存或 Hardware Bitmap；
7. UI 使用结果时，HWUI 记录绘制命令，其渲染线程 RenderThread 再把图片作为采样资源提交给 GPU。

这几步不会因为调用了一个 Java 方法而变成同一类成本。文件读取受页缓存和存储影响，像素解码主要消耗 CPU 与内存带宽，Hardware Bitmap 的创建还包含图形缓冲分配和上传。诊断时要区分阶段，不能只记录 `decodeBitmap()` 的总耗时后直接归因于格式。

压缩文件大小也不能代表解码后内存。普通 `ARGB_8888` 图片的像素存储通常接近 `rowBytes × height`，其中 `rowBytes` 是一行像素实际占用的字节数。行对齐、色彩格式、增益图和中间缓冲会让实际分配不同于简单的 `width × height × 4`。

## 2. ImageDecoder 与 BitmapFactory 的边界

`BitmapFactory` 和 `ImageDecoder` 都是同步 API。它们适合在工作线程调用，但不会自行创建后台任务。

`ImageDecoder.decodeBitmap()` 与 `decodeDrawable()` 标注了 `@WorkerThread`。`OnHeaderDecodedListener` 是头信息回调，不是异步通知：它在调用解码方法的同一线程执行，并且发生在方法返回之前。调用方可以在已经读到头信息、尚未开始完整像素解码时配置本次请求。

| 维度 | `BitmapFactory` | `ImageDecoder` |
| --- | --- | --- |
| 初始版本 | API 1 | API 28 |
| 调用语义 | 同步 | 同步 |
| 头信息决策 | `inJustDecodeBounds` 后再次调用解码 | 同一次调用中的 `OnHeaderDecodedListener` |
| 缩小输出 | `inSampleSize`，原生解码器最终按 2 的幂处理；资源密度还可能追加缩放 | `setTargetSampleSize()` 或 `setTargetSize()` |
| 像素复用 | `Options.inBitmap` | 没有把现有 Bitmap 设为目标的公开 API |
| 存储选择 | `inPreferredConfig` 等选项 | DEFAULT、SOFTWARE、SHARED_MEMORY、HARDWARE 四种 allocator（分配器） |
| 静态输出 | `Bitmap` | `Bitmap`、`BitmapDrawable` 或 `NinePatchDrawable` |
| 动画输出 | 不负责通用动画 Drawable | `decodeDrawable()` 可返回 `AnimatedImageDrawable` |
| 损坏输入 | 返回 `null`、抛异常或给出部分结果，取决于入口与错误 | `OnPartialImageListener` 决定是否接受可用的部分结果 |

`ImageDecoder.setCrop()` 只是从已经解码、缩放后的结果中裁剪输出。官方文档明确说明它不替代 `BitmapRegionDecoder.decodeRegion()`。超大图只显示局部时，应先判断格式和区域解码能力，不能把 `setCrop()` 当作降低完整解码成本的保证。

### 2.1 正确使用 ImageDecoder

这段代码在调用方提供的后台调度器中解码一张只用于显示的静态图片，并在头信息回调中限制输出尺寸。

```kotlin
@RequiresApi(Build.VERSION_CODES.P)
suspend fun decodeForDisplay(
    resolver: ContentResolver,
    uri: Uri,
    targetWidth: Int,
    targetHeight: Int,
    decodeDispatcher: CoroutineDispatcher,
): Bitmap = withContext(decodeDispatcher) {
    require(targetWidth > 0 && targetHeight > 0)

    val source = ImageDecoder.createSource(resolver, uri)
    ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
        val sourceWidth = info.size.width
        val sourceHeight = info.size.height
        val scale = minOf(
            1f,
            targetWidth.toFloat() / sourceWidth,
            targetHeight.toFloat() / sourceHeight,
        )

        decoder.setTargetSize(
            (sourceWidth * scale).toInt().coerceAtLeast(1),
            (sourceHeight * scale).toInt().coerceAtLeast(1),
        )
        decoder.setAllocator(ImageDecoder.ALLOCATOR_DEFAULT)
    }
}
```

`withContext` 决定代码在哪个线程池执行，`ImageDecoder` 本身仍是同步调用。协程被取消时可以阻止排队任务开始或阻止结果交付，但已经进入原生编解码器的任务不一定会立即中断。列表快速滑动时，结果返回后还要核对请求身份。

若输出需要 `getPixel()`、`copyPixelsToBuffer()`、软件 `Canvas` 或后续原地修改，应显式选择 `ALLOCATOR_SOFTWARE`。如果只是在解码后画圆角，`ImageDecoder.setPostProcessor()` 可以先在内部软件像素上绘制，再生成不可变结果；它与“业务拿到结果后仍能修改像素”是两件事。

### 2.2 BitmapFactory 的两阶段尺寸决策

文件来源必须使用 `BitmapFactory` 时，第一次调用只读取边界，第二次才分配像素：

```kotlin
fun decodeSampledFile(
    path: String,
    requestedWidth: Int,
    requestedHeight: Int,
): Bitmap? {
    require(requestedWidth > 0 && requestedHeight > 0)

    val bounds = BitmapFactory.Options().apply {
        inJustDecodeBounds = true
    }
    BitmapFactory.decodeFile(path, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

    var sampleSize = 1
    while (
        bounds.outWidth / (sampleSize * 2) >= requestedWidth &&
        bounds.outHeight / (sampleSize * 2) >= requestedHeight
    ) {
        sampleSize *= 2
    }

    val decodeOptions = BitmapFactory.Options().apply {
        inSampleSize = sampleSize
        inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return BitmapFactory.decodeFile(path, decodeOptions)
}
```

这里的 `inSampleSize` 只做粗粒度降采样。若 View 需要精确尺寸，后续仍可能发生缩放。对资源解码还要考虑 `inDensity` 与 `inTargetDensity`，不能只按文件原始宽高推断最终 Bitmap 尺寸。

## 3. Source 与文件 I/O：文件来源不等于 mmap

Android 17 的 `ImageDecoder.Source` 只是数据来源描述，创建 Source 通常不会完成像素解码。读取发生在 `decodeBitmap()` 或 `decodeDrawable()` 中。

`android-17.0.0_r1` 的具体路径如下：

- `File` 来源创建 `FileInputStream`。文件描述符可用时进入原生层的 `nCreate`；
- 原生层代码复制文件描述符，调用 `fdopen()`，再构造 `SkFILEStream`；
- `content://` 来源先尝试 `AssetFileDescriptor`，无法取得时回退到 `InputStream`；
- Java `InputStream` 在原生层由输入流适配器包装，并增加满足编解码器探测需求的前置缓冲；
- `ByteBuffer` 与 `byte[]` 使用各自的流适配器。

`mmap` 是把文件区间映射到进程虚拟地址空间的内存映射机制。源码没有承诺文件 Source 必然使用 `mmap`。`SkFILEStream`、C 标准 I/O、内核页缓存和具体编解码器可以减少重复物理读取，但这不等于零拷贝。即使应用自己建立 `MappedByteBuffer`，编解码器仍要读取压缩数据并写入新的像素存储。

是否采用映射应由访问模式决定：

- 多次随机访问同一个本地大文件时，映射可能减少应用层缓冲区管理；
- 顺序读取一次的图片可能从普通文件流和页缓存获得相近效果；
- `content://` 的真实来源可能是本地文件、Binder 代理、云端文档或动态生成数据；
- 加密缓存、压缩容器和不能随机改变读取位置的流会改变 I/O 路径。

测量文件 I/O 时，应区分冷缓存与热缓存，并把网络下载、解密、磁盘读取和像素解码分别计时。固定文件大小阈值无法跨设备判断内存映射是否更优。

## 4. Hardware Bitmap：图形存储不等于硬件编解码

`Bitmap.Config.HARDWARE` 表示结果的像素由图形缓冲持有，且应用不能通过普通 CPU 像素 API 读写。它没有承诺 JPEG、PNG、WebP、HEIF 或 AVIF 一定由专用硬件编解码器处理。

Android 17 的 `ImageDecoder_nDecodeBitmap()` 展示了静态图的关键顺序：

1. 根据目标尺寸、色彩空间和内存策略建立一个可写 `SkBitmap`，它是 Skia 内部的像素容器；
2. SOFTWARE、DEFAULT 与 HARDWARE 静态图路径先通过 `Bitmap::allocateHeapBitmap()` 分配普通像素；SHARED_MEMORY 使用 `allocateAshmemBitmap()`；
3. `decoder->decode()` 把像素写入这块 CPU 可写存储；
4. `PostProcessor` 如存在，会在该 Bitmap 的 `Canvas` 上执行；
5. 若最终结果应为 Hardware Bitmap，`Bitmap::allocateHardwareBitmap(bm)` 再创建图形缓冲并上传；
6. DEFAULT 的硬件分配失败时可以返回软件 Bitmap，HARDWARE 被显式要求时则报告失败。

因此 Hardware Bitmap 没有消除 CPU 解码和像素传输。它把图形缓冲准备放在解码结果构建阶段，避免普通软件 Bitmap 在首次绘制时再由 HWUI 建立纹理副本。成本发生时间和后续存储形态改变了，不能写成“图片由 GPU 直接解码”。

### 4.1 四种 allocator（分配器）的含义

| allocator（分配器） | Android 17 公开语义 | 适合场景 | 主要约束 |
| --- | --- | --- | --- |
| `ALLOCATOR_DEFAULT` | 通常尝试 Hardware Bitmap，不兼容或分配失败时可回退软件结果 | 静态、只上屏图片 | 不能假设结果一定是 HARDWARE |
| `ALLOCATOR_SOFTWARE` | 普通软件像素存储 | CPU 读写、软件 Canvas、业务后处理 | 绘制时可能需要建立或更新 GPU 采样资源 |
| `ALLOCATOR_SHARED_MEMORY` | 共享内存像素 | 跨进程传递且确有共享需求 | 仍需计算像素内存与 IPC 生命周期 |
| `ALLOCATOR_HARDWARE` | 必须返回 `Config.HARDWARE` | 调用方能满足全部硬件限制的静态图 | 与可变输出、透明度蒙版（alpha mask）等选项冲突时抛异常 |

官方 API 文档说 DEFAULT “通常”产生 Hardware Bitmap，也保留小图走软件或不兼容时回退的权利。业务判断必须查看返回值的 `config`，不能把默认策略当作固定兼容性契约。

### 4.2 可变性、后处理和动画

`setMutableRequired(true)` 只适用于 `decodeBitmap()`，并与 `ALLOCATOR_HARDWARE` 冲突。`decodeDrawable()` 请求可变结果会抛出 `IllegalStateException`。

`setPostProcessor()` 在解码和缩放后获得一个 `Canvas`，适合一次性绘制遮罩、圆角或颜色效果。Android 17 原生实现先完成这一步，再尝试生成 Hardware Bitmap；使用 PostProcessor 不会把最终结果限制为软件 Bitmap。如果业务要在返回后继续修改，仍需可变的软件结果。

当输入是动画且调用 `decodeDrawable()` 时，Android 17 返回 `AnimatedImageDrawable`。allocator 对动画 Drawable 会被忽略，数据源还可能在返回后继续被动画对象读取。由 `byte[]` 或 `ByteBuffer` 创建动画 Source 时，不得在动画仍使用数据时修改底层内容。

### 4.3 Hardware Bitmap 在显示管线中的位置

Hardware Bitmap 是应用绘制命令使用的资源，不会因为自身存在就成为 SurfaceFlinger 图层（layer）。标准窗口仍按这条路径显示：

`UI Thread 记录 DisplayList` → `RenderThread/HWUI` → `Skia GPU` → `App Window buffer` → `BLAST` → `SurfaceFlinger` → `HWC`

其中 `DisplayList` 是录制后的绘制命令列表，BLAST 负责衔接应用窗口缓冲队列与 SurfaceFlinger。普通软件 Bitmap 可能在 RenderThread 侧产生上传；Hardware Bitmap 已具备 GPU 可采样的图形存储。二者最终都由宿主窗口提交，除非应用另行把 `HardwareBuffer` 交给独立 `SurfaceControl`。

## 5. PNG、JPEG、WebP、HEIF 与 AVIF：格式没有固定性能排名

文件更小只代表下载、磁盘和缓存成本可能下降，不代表像素解码更快。格式复杂度、图片内容、位深、透明通道、动画、增益图、目标尺寸、编解码器实现和 SoC 都会改变结果。

| 格式 | 稳定特征 | 评测时容易遗漏的变量 |
| --- | --- | --- |
| JPEG | 常用于有损照片，无 alpha | 渐进式编码（progressive）、色度采样、EXIF 方向元数据、目标色彩空间 |
| PNG | 无损，支持 alpha | 滤波类型、位深、透明通道、图片内容可压缩性 |
| WebP | 支持有损、无损、alpha 与动画 | 静态和动画路径不同，编码参数差异很大 |
| HEIF | 容器可承载 HEVC 图像及附加信息 | 设备编解码器、位深、增益图、厂商实现 |
| AVIF | 基于 AV1 图像编码，支持较丰富的色彩能力 | 编码配置、位深、设备实现、目标尺寸 |

Android 17 的 `BitmapRegionDecoder.java` 明确列出 JPEG、PNG、WebP、HEIF 和 AVIF。这个列表表示当前平台区域解码器接受这些格式，不表示旧 API 版本都具备相同能力，也不表示所有输入特性都能等价处理。版本兼容必须在应用最低 API 和目标设备上验证。

### 5.1 Ultra HDR 与 Gainmap

Android 14 起，Ultra HDR 图片可以在 SDR 基础图之外携带增益图（gainmap）。增益图记录从 SDR 基础图恢复 HDR 亮度所需的增益信息。Android 17 的 `BitmapFactory.cpp` 会从编解码器取得增益图，解码为独立 Bitmap 并附着到基础 Bitmap；Hardware Bitmap 路径还会为增益图创建对应的硬件像素存储。`Gainmap.java` 保存增益图内容 Bitmap 与显示参数。

Android 17 的 `ImageDecoder.cpp` 在设置 `PostProcessor` 时跳过自动增益图提取，因为平台无法推断任意 Canvas 处理应怎样等价作用于增益图。Ultra HDR 输入若还要做解码期后处理，应同时验证 `hasGainmap()` 和显示效果，不能只检查最终 Bitmap 是否为 `Config.HARDWARE`。

计算这类图片的驻留内存与解码峰值时，要纳入基础 Bitmap、增益图 Bitmap 和解码、缩放期间的临时缓冲；生成硬件结果时，软件像素与硬件像素存储还可能短暂共存。`Bitmap.getAllocationByteCount()` 只描述当前 Bitmap 的底层像素存储，不能代表附着的增益图和全部图形分配，因此不存在可跨设备套用的固定倍数。实测时应同时记录两层 Bitmap 的尺寸、配置、行跨度（stride），以及进程 Graphics、Native Heap 和比例分摊内存（PSS）的变化。

`bitmap.setGainmap(null)` 只解除基础 Bitmap 对增益图的关联；其他 Java 或原生层引用结束后，对应资源才具备释放条件。移除增益图还会改变 HDR 效果、显示能力适配和色彩一致性，不应作为低端机的无条件节省内存开关。

选择线上格式时，应对同一视觉内容记录：

- 编码字节数与下载时间；
- 头信息解析和完整解码耗时；
- 输出 `width`、`height`、`config`、色彩空间与 `allocationByteCount`；
- 解码期间的 CPU 时间、峰值内存和能耗；
- 首次绘制是否出现软件 Bitmap 上传；
- 失败率，以及服务端回退格式是否生效。

一台旗舰设备的单次结果不足以推导全量策略。设备分组应来自实际 SoC、系统版本、内存等级和业务样本，格式性能则由各组实测给出。

## 6. 解码线程调度：限制并发的依据是 CPU 与内存

专用线程、线程池和协程解决的是任务组织问题，不能改变编解码器的计算量。

| 模型 | 特点 | 适用条件 |
| --- | --- | --- |
| 单个专用线程 | 顺序明确，内存峰值容易控制 | 请求稀疏，或单次解码占用较大 |
| 有界线程池 | 可以提高吞吐，也会增加 CPU 竞争和同时存活的中间像素 | 列表、多路图片请求，且已通过设备实测确定并发上限 |
| 协程 + 有界调度器（dispatcher） | 生命周期与请求取消更易表达 | Kotlin 项目；底层仍需要受控的执行器或并行度 |

`Dispatchers.IO` 的名字不表示任务是轻量 I/O。图片解码在读完数据后会长时间占用 CPU，和数据库、网络或文件任务共用一个宽线程池时可能互相影响。自定义图片管线应给解码建立可观测的有界执行资源，并根据以下信号调节：

- 主线程与 RenderThread 已可运行但仍在等待 CPU 的调度延迟；
- 单次解码 CPU 时间和墙钟时间；
- 同时解码时的原生堆、共享内存或图形内存峰值；
- 视口请求命中率与被取消任务比例；
- 不同设备组的吞吐和卡顿变化。

并发数不应仅按 CPU 核数计算。两张大尺寸、广色域图片可能先受内存带宽和分配峰值限制；多张小缩略图则可能受调度与请求管理成本限制。

### 6.1 取消的真实边界

图片请求至少有三种取消时机：

1. 尚在队列中：直接移除，不进入编解码器；
2. 正在读取自定义数据源：关闭来源或让读取逻辑响应取消；
3. 已进入 `BitmapFactory` 或 `ImageDecoder` 原生层解码：公开 API 没有可靠的逐请求强制中断协议。

所以列表复用时必须在完成回调处比较请求键、条目标识或代次编号（generation）。旧任务返回的 Bitmap 可以进入合适的缓存，但不能覆盖已绑定新数据的 View 或 Compose 状态。

## 7. inBitmap：BitmapFactory 能复用，ImageDecoder 不能

`BitmapFactory.Options.inBitmap` 允许符合条件的解码复用一块可变 Bitmap 存储。Android 17 原生实现会检查现有 `allocationByteCount`，并在有密度缩放或其他中间步骤时选择不同分配器。

约束应按公开 API 理解：

- Android 4.4 / API 19 起，候选 Bitmap 必须可变，且新结果的字节数不大于候选的 `allocationByteCount`；
- API 19 以前还有额外限制：输入需为 JPEG 或 PNG、尺寸相同、`inSampleSize == 1`；
- `Config.HARDWARE` 始终不可作为 `inBitmap`；
- 候选不能已回收；
- 解码方法可能因为候选不兼容而抛 `IllegalArgumentException`；
- 无论是否期待复用，都必须使用解码方法的返回值，不能直接假设返回的就是候选对象。

`ImageDecoder` 没有 `setTargetBitmap()`，也没有等价的公开复用入口。它可以选择目标尺寸和分配器，但不能把应用提供的 Bitmap 当成静态图解码目标。图片库若在某条路径切换到 ImageDecoder，也要重新评估原有 Bitmap 复用池在“解码目标复用”上的收益。

手工维护池还要证明对象已经不再显示、不会被另一个请求并发使用，并处理色彩格式与容量匹配。大多数应用应优先使用成熟图片库的缓存和复用策略；自定义池应记录命中、拒绝、错误与峰值内存，无需追求一个通用命中率阈值。

## 8. Android 17 的 Bitmap 内存模型

官方 Bitmap 内存文档给出的版本历史是：

| 平台区间 | 像素数据位置 |
| --- | --- |
| Android 2.3.3 / API 10 及以下 | 原生内存，与 Dalvik 堆中的 Bitmap 对象分离 |
| Android 3.0 / API 11 至 Android 7.1 / API 25 | 与 Bitmap 对象一起计入 Dalvik/ART 托管堆 |
| Android 8.0 / API 26 及以上 | 原生堆 |

Android 17 的普通 Bitmap Java 对象通过 `NativeAllocationRegistry` 关联原生分配。这个注册机制帮助运行时感知原生内存压力和释放动作，不表示像素转回 Java 托管堆，也不保证原生分配会在 Java 引用失效的瞬间释放。

### 8.1 ashmem 与共享像素

`ashmem` 是 Android 的匿名共享内存机制。Android 17 的 ImageDecoder 在 `ALLOCATOR_SHARED_MEMORY` 路径调用 `Bitmap::allocateAshmemBitmap()`；`Bitmap.java` 还保留 `createAshmemBitmap()`、ashmem 检查和用于跨进程序列化的 Parcel 处理。

ashmem 在 Android 17 中仍有明确的共享像素用途。普通软件 Bitmap 默认使用原生堆；跨进程共享、Parcel 或指定共享内存分配器等场景才需要分析 ashmem。

共享内存不会降低解码后的像素总量。它改变了后端存储和跨进程共享方式，还会引入文件描述符、映射和对象生命周期问题。

### 8.2 HardwareBuffer、dma-buf 与厂商实现

Hardware Bitmap 可以通过 `Bitmap.getHardwareBuffer()` 取得 `HardwareBuffer`。应用层拿到的是标准化的 AHardwareBuffer/HardwareBuffer 图形缓冲句柄；实际 `gralloc` 分配堆、压缩布局、IOMMU（I/O 内存管理单元）映射与统计归类由设备实现决定。

在 `android17-6.18-2026-06_r6` 内核基线下，图形缓冲跨设备或跨进程共享通常会使用 Linux 的共享缓冲机制 dma-buf，生产者和消费者同步会关联 dma-fence。这个机制不能反向证明“每个 Hardware Bitmap 都来自相同分配堆、采用相同物理布局”，也不能只凭一个文件描述符（FD）推断 GPU 已完成写入。

### 8.3 怎样看内存统计

这组命令同时观察进程级 PSS 分类和图形缓冲信息，避免只凭某一个字段定性。

```bash
adb shell dumpsys meminfo your.package.name
adb shell dumpsys gfxinfo your.package.name
adb shell dumpsys SurfaceFlinger
```

`dumpsys meminfo` 中 Native Heap、Graphics、GL 和 Other 的归类依赖 Android 版本、图形内存统计接口 memtrack HAL 与厂商实现。PSS 表示按共享关系折算后的物理内存贡献，与某个 Java 对象的独占字节数含义不同。应用内的 `allocationByteCount`、进程 PSS、原生堆分析器 heapprofd 和图形缓冲统计应互相校验。

## 9. FrameMetrics 与 Perfetto：一个看帧，一个看解码

### 9.1 FrameMetrics 不能直接测后台解码

Android 17 的 `FrameMetrics` 公开指标包括：

- `LAYOUT_MEASURE_DURATION`
- `DRAW_DURATION`
- `SYNC_DURATION`
- `COMMAND_ISSUE_DURATION`
- `SWAP_BUFFERS_DURATION`
- `TOTAL_DURATION`
- `GPU_DURATION`
- `DEADLINE`

这些指标描述窗口帧的 UI/HWUI/GPU 阶段。后台图片解码不计入这些时长字段，只会通过三种间接方式影响帧：

- 错误地在主线程解码，增加垂直同步信号（VSync）的响应延迟或某个 UI 阶段；
- 后台解码占用 CPU、内存带宽或触发内存回收，使 UI/RenderThread 调度变差；
- 软件 Bitmap 首次绘制需要准备 GPU 采样资源，影响 RenderThread 或 GPU。

所以 FrameMetrics 适合回答“用户看到的窗口帧是否受影响”，无法给出某一次后台图片解码的耗时。旧文案中的 `LAYOUT_DRAW_TIME`、`DRAW_TIME`、`SWAP_BUFFERS_TIME` 也不是 Android 17 的公开常量名。

### 9.2 Perfetto 中的 Android 17 源码切片

`trace` 是系统跟踪中的带时间区间事件，Perfetto 会把这类区间显示为切片。`ImageDecoder.java` 在 Android 17 记录这些资源 trace：

- `ImageDecoder#decodeBitmap`
- `ImageDecoder#decodeDrawable`
- 内层描述 `ID#w=<sourceWidth>;h=<sourceHeight>;dw=<targetWidth>;dh=<targetHeight>;src=<source>`

原生层的 `ImageDecoder_nDecodeBitmap()` 还记录 `Decoding <width>x<height> bitmap`。这些切片可以确认一次调用的总区间、目标尺寸和原生像素解码区间，但没有自动把格式探测、文件读取、颜色转换、上传全部分成独立公开阶段。

这段代码给业务自己的获取、解码和交付阶段增加同一个请求标识，便于与系统切片对齐。

```kotlin
inline fun <T> tracedImageStage(
    requestId: String,
    stage: String,
    block: () -> T,
): T {
    Trace.beginSection("Image:$stage:$requestId")
    return try {
        block()
    } finally {
        Trace.endSection()
    }
}
```

`beginSection()` 与 `endSection()` 必须在同一线程成对执行，切片名称还应控制长度并避免写入用户隐私。使用这层标记后，可以在 Perfetto 中把应用排队、系统解码和结果绑定关联到同一个请求。

一次可靠的线下分析应同时检查：

1. 应用自定义请求、获取、解码和交付切片；
2. `ImageDecoder#decodeBitmap` 或 `BitmapFactory` 调用所在的线程；
3. `sched` 调度事件中 UI Thread、RenderThread 与解码线程已可运行但仍在等待 CPU 的时长；
4. FrameTimeline 帧时间线中受影响的窗口帧；
5. RenderThread/GPU 是否在软件 Bitmap 首次出现时增加资源准备成本；
6. heapprofd、Java 托管堆与 `dumpsys meminfo` 中的分配峰值；
7. 冷缓存和热缓存是否混在同一组数据里。

不要编写依赖并不存在的 `Bitmap#allocate` 切片参数的 SQL。若平台源码没有记录所需字段，应由应用 trace counter（轨迹计数器）、请求日志或内存采样补齐。

## 10. 九宫格和瀑布流的调度策略

列表图片管线的目标，是让当前视口在内存可控的前提下及时得到正确尺寸的结果。

设计时依次确定：

1. **请求身份**：URL、目标尺寸、变换、色彩策略和业务版本共同决定缓存键（key）；
2. **目标尺寸**：布局尺寸确定后再请求，避免按原图解码后立即缩小；
3. **任务去重**：相同缓存键的并发请求共享获取和解码工作；
4. **优先级**：视口内高于预取，滚动方向上的近邻高于远端；
5. **取消与交付校验**：离开视口时取消排队任务，完成后核对条目身份；
6. **有界并发**：同时执行数由设备测量和图片尺寸决定；
7. **内存预算**：同时存活的解码中间结果、内存缓存和待上传 Bitmap 都要计入；
8. **预取验证**：记录预取命中和浪费，不能只看缓存命中率。

按 dp（密度无关像素）把图片固定分为“小、中、大”不能准确估计内存。解码目标最终是像素尺寸，还会受屏幕密度、输出配置、广色域和增益图影响。预算至少应使用预计 `rowBytes × height`，解码完成后再用实际 `allocationByteCount` 校准。

动态并发也不应只由上一帧是否超过某个毫秒值控制。刷新率、FrameTimeline 记录的帧截止时间（deadline）、CPU 压力和图片内存峰值需要共同判断；频繁改变并发本身还会造成队列抖动。可按设备组离线确定安全区间，线上只做缓慢、可回退的调整。

## 11. Glide、Coil 与 Picasso：先确认依赖版本的真实路径

图片库的默认解码器、Hardware Bitmap 条件、线程配置和缓存策略会随版本改变。不能用“Glide 永远走 ImageDecoder”“Coil 固定使用某个协程调度器”或“Picasso 已停止维护”这类未经当前版本源码确认的结论选型。

| 框架 | 官方资料可确认的能力 | 主要核查点 |
| --- | --- | --- |
| Glide 4 | 请求生命周期、内存/磁盘缓存、`BitmapPool`、可配置 Hardware Bitmap | 当前版本是否启用 ImageDecoder；该路径不能使用 `inBitmap` 作为解码目标 |
| Coil 3 | Interceptor、Mapper、Keyer、Fetcher、Decoder 组件链，内存/磁盘缓存 | 注册了哪个 Decoder、`allowHardware` 与变换是否要求软件像素 |
| Picasso | ImageView 复用处理、请求取消、变换与缓存 | 当前依赖版本和源码中采用的解码器、网络缓存实际由谁提供 |

选择时应优先检查项目已经使用的 UI 技术、现有缓存命中、定制格式、生命周期接入和可观测性。成熟框架能处理大量边界，但不能替应用决定服务端格式、设备分组和业务内存预算。

若性能问题只发生在少数请求，先从框架的请求监听器、事件监听或自定义解码器取得分阶段数据。直接绕开框架自建下载、缓存、解码和取消系统，往往会增加重复请求与生命周期错误。

## 12. Android 17 的 ImageDecoder 新增项

Android 17 / API 37 的公开 API 差异为 `ImageDecoder` 增加了四个默认头信息监听方法：

- `setDefaultThreadListener()` / `getDefaultThreadListener()`
- `setDefaultProcessListener()` / `getDefaultProcessListener()`

Android 17 源码中的调用顺序是：

1. 当前线程设置了线程级监听器时，先调用它，并跳过进程级监听器；
2. 当前线程没有线程级监听器时，调用进程级监听器；
3. 本次 `decodeBitmap()` 或 `decodeDrawable()` 显式传入的监听器始终随后执行。

线程级监听器存在 `ThreadLocal` 中，每个线程各自保存一份值；进程级监听器则由进程内所有线程共享。它们适合由基础设施统一附加保守默认值或观测逻辑，但有两个工程风险：

- 进程级设置会影响同进程内的图片库和其他模块；
- 显式监听器后执行，可以覆盖默认监听器设置的参数。

业务请求若只需要配置自己的尺寸、分配器或颜色空间，继续使用每次调用的显式监听器更清楚。使用默认监听器时，还要明确安装、覆盖和清理时机，避免测试或线程池复用带来隐藏状态。

`setTargetColorSpace()`、`setOnPartialImageListener()` 和四种分配器都早于 API 37，不能列为 Android 17 新增能力。Android 17 的公开变化应以 API 差异中的这四个监听方法为准。

## 13. RenderNode 与首次纹理准备

`RenderNode` 是 HWUI 中可跨帧复用的绘制节点，`DisplayList` 是它录制的绘制命令列表。Hardware Bitmap 进入 View 或 Compose 后，仍是宿主 RenderNode 的 DisplayList 所引用的图片资源。RenderNode 保存命令和属性，不等于缓存整块栅格结果；`translation`、`scale`、`alpha` 等属性可在内容不变时复用已录制命令，图片对象或绘制内容变化仍要重录。`RecordingCanvas` 会保留所画 Bitmap 的引用，因此业务缓存移除对象，不代表仍存活的 View 或 RenderNode 已立即释放它；自建 RenderNode 结束生命周期时可调用 `discardDisplayList()`，框架 View 的内部节点交给框架管理。

Android 17 的 HWUI 对非 Hardware Bitmap 可进入 `prepareToDraw()` / `PinAsTexture()` 的显式纹理准备分支；Hardware Bitmap 已在创建阶段完成主要图形缓冲上传，所以跳过这段路径。收益是移动工作发生的时间和存储形态，不是让上传消失：格式转换、AHardwareBuffer 分配、GL/Vulkan 提交和驱动延迟仍可能落在解码完成前或首次使用时。

对照实验应固定同一图片字节、目标尺寸、色彩空间、缓存冷热和页面，分别采集软件 Bitmap 直接显示、软件 Bitmap 提前 `prepareToDraw()`、Hardware Bitmap 显示，以及三组内存缓存命中。比较从请求开始到目标帧呈现（present）的总等待，并记录解码、上传或准备切片、`DrawFrame`、GPU 完成时刻和 Graphics、dma-buf、PSS。若 Hardware 组首绘更稳定但解码完成更晚，只能说明成本前移；端到端是否改善仍要看总等待。

Hardware Bitmap 不会变成 SurfaceFlinger 独立图层，`computeApproximateMemoryUsage()` 也不包含子 RenderNode 和 Bitmap。页面退出后的评审要同时检查图片库仍在使用的资源（active resource）、View、Drawable 和 DisplayList 引用、Graphics/GL/PSS、dma-buf、GPU 内存与 FD 趋势；不能按“每张图固定一个 FD”或 `width × height × 4` 估算完整代价。

## 14. 错误恢复与安全边界

`OnPartialImageListener` 在编解码器报告输入不完整或数据错误后收到 `DecodeException`。返回接受只表示调用方愿意使用当前可得到的结果，不表示平台提供渐进式网络图片流，也不表示损坏内容已经安全。

对不可信图片来源，应同时限制：

- 压缩数据来源、协议和下载字节数；
- 头信息中声明的尺寸、帧数和色彩信息；
- 目标解码尺寸与同时解码数量；
- 超时、取消和失败回退；
- 原生编解码器安全更新对应的系统版本。

Android 17 源码中存在受特性开关（feature flag）保护的解码分配限制实现，但它不属于 API 37 已确认的稳定公开契约。应用不能把尚未公开的接口当作生产保护，应在请求层做尺寸预检和内存预算。

## 15. 评审清单

遇到图片解码或首次绘制问题时，依次核查：

- 解码是否在工作线程，头信息监听器是否被误解成异步；
- 输出像素尺寸是否接近实际显示尺寸；
- 采样 API 是否写成 `setTargetSampleSize()`；`ImageDecoder` 没有 `setSampleSize()`；
- 业务是否写了不存在的 `ImageDecoder.setTargetBitmap()`；
- CPU 读写需求是否与分配器匹配；
- Hardware Bitmap 是否被误写成专用硬件编解码器；
- 文件 Source 是否被无证据地描述成固定内存映射；
- `setCrop()` 是否被误当成区域解码；
- `inBitmap` 候选是否可变、容量足够且不再显示；
- 动画 Drawable 是否仍依赖原始字节数组、`ByteBuffer` 或流；
- FrameMetrics 是否只用于帧影响，解码耗时是否另有 trace 记录；
- 格式性能是否来自同尺寸、同设备、冷热缓存分开的测量；
- 原生堆、共享内存和图形内存是否用多种观测互相校验。

## 16. 结论

Bitmap 解码优化需要控制输出像素、明确存储需求，并把 I/O、编解码器、分配、上传和绘制分别测量。

`ImageDecoder` 提供同一次同步调用中的头信息配置、四种分配器、静态与动画 Drawable 支持；它不提供现有 Bitmap 复用，也不会自动把工作移到后台。`BitmapFactory` 仍是有效且持续维护的 API，尤其适合需要 `inBitmap` 的成熟管线。

Hardware Bitmap 解决的是最终图形存储与绘制准备问题，不等同于硬件解码。Android 17 的静态图源码显示，CPU 可写像素解码完成后才分配 Hardware Bitmap。这一顺序可以解释“解码变慢但首绘更稳定”或“软件 Bitmap 解码快但首次显示多一次资源准备”等现象。

## 参考资料

- [`ImageDecoder.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/ImageDecoder.java)：同步调用、默认监听器、动画、trace 与参数校验。
- [`ImageDecoder.cpp`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/ImageDecoder.cpp)：Source 适配、像素解码、ashmem、PostProcessor 与 Hardware Bitmap 创建。
- [`BitmapFactory.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BitmapFactory.java) 与 [`BitmapFactory.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/jni/BitmapFactory.cpp)：采样、复用、缩放和硬件上传。
- [`Bitmap.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java)：NativeAllocationRegistry、ashmem、HardwareBuffer 与 CPU 访问限制。
- [`Gainmap.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Gainmap.java)：增益图内容 Bitmap、显示参数与引用关系。
- [`BitmapRegionDecoder.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BitmapRegionDecoder.java)：Android 17 区域解码支持格式。
- [`RenderNode.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/RenderNode.java)：DisplayList 生命周期与近似内存统计口径。
- [`FrameMetrics.java`（`android-17.0.0_r1`）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)：窗口帧公开时长字段。
- [ImageDecoder API](https://developer.android.com/reference/android/graphics/ImageDecoder) 与 [API 36 → 37 diff](https://developer.android.com/sdk/api_diff/37/changes/android.graphics.ImageDecoder)：公开契约和 Android 17 新增监听器。
- [BitmapFactory.Options API](https://developer.android.com/reference/android/graphics/BitmapFactory.Options)：`inBitmap` 与 `inSampleSize` 约束。
- [Managing Bitmap Memory](https://developer.android.com/topic/performance/graphics/manage-memory)：像素存储位置的版本历史。
- [BitmapRegionDecoder API](https://developer.android.com/reference/android/graphics/BitmapRegionDecoder)：当前区域解码格式与入口。
- [Glide BitmapPool 配置](https://bumptech.github.io/glide/doc/configuration.html)、[Coil image pipeline](https://coil-kt.github.io/coil/image_pipeline/)、[Picasso 官方站点](https://square.github.io/picasso/)：图片库能力边界。
- [Android common kernel（`android17-6.18-2026-06_r6`）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)：内核基线及 dma-buf/dma-fence 语义来源。
