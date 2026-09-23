---
title: Bitmap 与图片内存优化
chapter: '23.4'
section: '23.4'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: Android 17 / API 37 / AOSP android-17.0.0_r1；Android Bitmap、BitmapFactory.Options、Bitmap.Config 与 ImageDecoder 官方文档
last_review_finalize_at: '2026-08-15T07:00:43+08:00'
last_review_finalize_run_id: 20260815-070043-gracker-writing-review
confidence: high
sources:
- type: official
  path: https://developer.android.com/topic/performance/graphics/manage-memory
- type: official
  path: https://developer.android.com/topic/performance/graphics/load-bitmap
- type: official
  path: https://developer.android.com/reference/android/graphics/Bitmap
- type: official
  path: https://developer.android.com/reference/android/graphics/BitmapFactory.Options
- type: official
  path: https://developer.android.com/reference/android/graphics/Bitmap.Config
- type: official
  path: https://developer.android.com/reference/android/graphics/ImageDecoder
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BitmapFactory.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/BaseCanvas.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/ImageDecoder.java
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]'
- type: blog
  path: '[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]'
- type: clipping
  path: 货拉拉司机 Android 端内存治理实践（本地归档 Cubox）
tags:
- bitmap
- insamplesize
- native-memory
- inbitmap
- hardware-bitmap
related_chapters:
- '23.2'
- '22.9'
- '4.2'
pipeline_stage: finalized
last_draft_polish_at: '2026-08-15T07:00:43+08:00'
last_draft_polish_run_id: 20260815-070043-gracker-writing
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
consolidated_from:
- src/part5-app/ch23-memory-practice/08-memory-case-studies.md
---

# Bitmap 与图片内存优化

图片内存取决于解码尺寸、像素格式、存储位置、生命周期和缓存策略，文件体积不能直接代表运行时占用。优化顺序应从限制目标尺寸开始，再用大图监控、复用与 Hardware Bitmap 处理不同场景。

## 图片内存为什么容易超预算

Bitmap（位图）是 Android 中表示解码后像素及其描述信息的对象。图片内存问题通常由解码尺寸、缓存复用、页面生命周期和设备内存预算共同造成。一张 4000×3000 的 `ARGB_8888` 图片需要 48,000,000 字节，约 45.8 MiB（1 MiB 为 1,048,576 字节）；200×150 的目标 View 只有 30,000 个像素。若仍按原尺寸解码，分配的像素数是显示目标的 400 倍，随后交给 Canvas 缩小也无法省掉这次像素分配。Android 10 到 Android 17 的普通软件 Bitmap 会增加原生堆（Native Heap）占用，Hardware Bitmap 的像素则位于图形缓冲区。

应用侧要同时控制四件事：解码前按目标尺寸降采样；按像素所在的内存分区选择监控指标；在图片加载入口记录大图和生命周期线索；只在所有权清楚时复用像素存储。ART 堆与 GC 见 [4.2 ART Heap、GC 与后台维护调度](../../part1-fundamentals/ch04-memory/02-art-heap-gc-maintenance.md)，图片请求、缓存、解码与绘制见 [22.9 图片加载、Bitmap 解码与 RenderNode](../ch22-rendering-practice/09-image-bitmap-rendernode.md)，对象泄漏判断见 [23.2 内存泄漏检测与治理](02-memory-leak-governance.md)。

文中几组容易混淆的术语含义如下：

| 术语 | 本文含义 |
|---|---|
| software / Hardware Bitmap | software Bitmap 的像素可由 CPU 访问；Hardware Bitmap 的像素由图形缓冲持有，适合只交给硬件加速绘制的图片。 |
| Native Heap / 图形缓冲区 | Native Heap 是进程原生代码使用的堆；图形缓冲区由图形分配器和驱动管理，两者在内存工具中的统计口径不同。 |
| mutable / immutable | mutable 表示像素可修改，immutable 表示不可修改；`inBitmap` 只能使用 mutable Bitmap，`Config.HARDWARE` 始终 immutable。 |
| alpha / 广色域 / HDR | alpha 是透明度通道；广色域表示能表达更大的颜色范围；HDR 表示更大的亮度和颜色动态范围。 |
| `inBitmap` | `BitmapFactory.Options` 的复用选项，让一次解码尝试写入已有的可变像素存储。 |
| HPROF | Java 堆转储格式，用于查看 Bitmap 包装对象到 GC Root 的引用路径；Hardware Bitmap 的图形缓冲大小不能只靠 HPROF 判断。 |
| EXIF 方向 | 相机图片元数据中的旋转或镜像标记；像素宽高与最终显示方向可能因此不同。 |

排查时先确认像素位于哪类存储，再核对解码尺寸和对象生命周期；三个问题使用的证据不同。

## Bitmap 内存计算与 inSampleSize

Bitmap 的内存预算从三个量开始：宽、高、每像素字节数。常见配置里，`ARGB_8888` 每像素 4 字节，`RGB_565` 每像素 2 字节，`ALPHA_8` 每像素 1 字节；API 33 起提供的 `RGBA_1010102` 每像素 4 字节，`RGBA_F16` 每像素 8 字节。工程估算可以先用这个式子：

```text
bytes ≈ width × height × bytesPerPixel
```

这个式子没有体现每行像素的对齐填充，因此只适合预算估算。Android `Bitmap.getByteCount()` 返回当前像素所需的最小字节数，`getAllocationByteCount()` 返回底层分配区大小；当 Bitmap 被 `inBitmap` 复用或 `reconfigure()` 调整后，后者可能大于前者。排查内存占用时优先记录 `allocationByteCount`，否则会低估复用池里的大块分配。

解码前先读尺寸，不直接创建像素内存。`BitmapFactory.Options.inJustDecodeBounds = true` 时，解码方法返回 `null`，但会填充 `outWidth`、`outHeight` 和 `outMimeType`。这一步适合放在所有本地文件、资源图、网络图落盘后的统一解码入口。

这段代码只做采样率计算。两次 decode 中，第一次只取边界，第二次才分配像素内存。

```kotlin
fun decodeSampledBitmap(
    filePath: String,
    reqWidth: Int,
    reqHeight: Int
): Bitmap? {
    val bounds = BitmapFactory.Options().apply {
        inJustDecodeBounds = true
    }
    BitmapFactory.decodeFile(filePath, bounds)

    val decodeOptions = BitmapFactory.Options().apply {
        inSampleSize = calculateInSampleSize(bounds, reqWidth, reqHeight)
        inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return BitmapFactory.decodeFile(filePath, decodeOptions)
}

fun calculateInSampleSize(
    options: BitmapFactory.Options,
    reqWidth: Int,
    reqHeight: Int
): Int {
    require(reqWidth > 0 && reqHeight > 0) {
        "Requested dimensions must be positive"
    }
    val rawWidth = options.outWidth
    val rawHeight = options.outHeight
    var sample = 1

    if (rawHeight > reqHeight || rawWidth > reqWidth) {
        val halfHeight = rawHeight / 2
        val halfWidth = rawWidth / 2
        while (halfHeight / sample >= reqHeight && halfWidth / sample >= reqWidth) {
            sample *= 2
        }
    }
    return sample
}
```

`inSampleSize = 4` 表示宽高约降到原图的 1/4，像素数约降到 1/16。官方文档说明，非 2 的幂会向下取到最接近的 2 的幂；因此采样率计算不能当作任意比例的精确缩放。解码后的图片仍可能需要再按 View 尺寸缩放，但显示阶段的缩放不能替代解码阶段的像素数控制。

API 28 及以上使用 `ImageDecoder` 时，可在 `OnHeaderDecodedListener` 里调用 `setTargetSampleSize()` 或 `setTargetSize()`，在头信息回调中设定输出尺寸，避免默认按编码图的原始尺寸输出。它与 `BitmapFactory` 两阶段解码的差异见 22.9。

`inPreferredConfig` 是解码器尽量满足的请求，不保证结果一定采用指定配置；实际结果应读取 `bitmap.config` 和 `allocationByteCount`。

照片、透明图和需要高质量缩放的 UI 图通常优先使用 `ARGB_8888`。没有 alpha、质量要求较低的列表缩略图可以评估 `RGB_565`，但要接受色彩精度下降和渐变色带风险。广色域或 HDR 内容还可能使用 `RGBA_F16`，或在 API 33 及以上使用 `RGBA_1010102`；前者为 8 字节/像素，后者与 `ARGB_8888` 一样为 4 字节/像素。`RGB_565` 不能作为所有图片共用的省内存开关。

## Android 8.0+：Bitmap 像素内存位于原生堆

Bitmap 像素数据的存放位置经历过三次变化：Android 2.3.3 及更早版本位于原生内存；Android 3.0 到 7.1 随 Bitmap 对象位于 Dalvik 堆；Android 8.0 及以上又回到原生堆。本文覆盖 Android 10 到 Android 17：普通软件 Bitmap 的像素分配按原生堆排查，`Config.HARDWARE` 的像素分配按图形缓冲区排查。

AOSP `Bitmap.java` 中，Bitmap 的 Java 对象通过 `mNativePtr` 指向原生 Bitmap。`NativeAllocationRegistry` 用来把 Java 对象关联的原生分配量和释放函数登记给 ART。Android 17 的 `registerNativeAllocation()` 使用两个登记器：一个以空操作释放函数记录像素数据大小，只负责分配记账；另一个通过 `sRegistry` 登记原生 Bitmap 对象和对应的释放函数。`mRecycler` 是前一个登记器返回的清理任务，`recycle()` 释放像素后运行它，更新 ART 记录的原生分配量。这个设计带来两个工程结论：

- **Bitmap 对象仍受 Java 可达性影响**：Java 层对象被 Activity、Adapter、缓存或回调引用时，原生像素内存也会被保留。Bitmap 泄漏的根不一定在原生层，常常是 Java 引用链没有断开。
- **原生堆变大不等于 JNI 泄漏**：Android 8.0 之后，图片加载增加会直接推高原生堆。用 `dumpsys meminfo` 或线上内存指标看到原生堆上升时，先区分 Bitmap 分配与 JNI（Java 和原生代码之间的调用接口）或 `.so` 原生库分配，不能直接归因于 JNI 泄漏。

`recycle()` 只能作为明确失效后的提前释放手段，不适合替代生命周期管理。官方文档对旧版本建议过引用计数式 `recycle()`，但也提醒：Bitmap 被回收后再绘制会触发 “Canvas: trying to use a recycled bitmap”。在 Android 10+ 项目里，更稳的策略是让图片请求跟随页面生命周期取消，让缓存有上限，让不可见页面及时释放强引用；只有超大图编辑、一次性解码、离屏处理这类边界清楚的场景，才考虑显式 `recycle()`。

## 图片内存监控与大图检测

图片监控不能等到 OOM（内存耗尽）后才看堆。统一图片入口应记录“原图尺寸、目标 View 尺寸、解码后尺寸、配置、分配字节数、页面名、调用栈摘要”。这组信息能直接回答两个问题：是否解码了远大于显示尺寸的图片；是否有页面在退出后仍保留大图。

大图阈值应按屏幕、业务类型、同时在内存中的图片数量和设备可用内存分组制定。全屏预览、图片编辑、头像和列表封面的合理预算不同；同一张图在单图详情页可以接受，进入多列列表后就可能让并发像素预算失控。维度比与分配字节数都应做成可配置策略，并通过目标设备上的峰值内存和滚动测试确定阈值。只用一个固定 MB 数字会漏掉低内存设备，也会误报正常的图片编辑场景。

这段代码展示统一解码后的记录点。它不替代图片库，只负责识别并记录高风险 Bitmap。

```kotlin
data class BitmapDecodeRecord(
    val scene: String,
    val sourceWidth: Int,
    val sourceHeight: Int,
    val targetWidth: Int,
    val targetHeight: Int,
    val bitmapWidth: Int,
    val bitmapHeight: Int,
    val config: Bitmap.Config?,
    val allocationBytes: Int
)

fun Bitmap.toDecodeRecord(
    scene: String,
    sourceWidth: Int,
    sourceHeight: Int,
    targetWidth: Int,
    targetHeight: Int
): BitmapDecodeRecord {
    return BitmapDecodeRecord(
        scene = scene,
        sourceWidth = sourceWidth,
        sourceHeight = sourceHeight,
        targetWidth = targetWidth,
        targetHeight = targetHeight,
        bitmapWidth = width,
        bitmapHeight = height,
        config = config,
        allocationBytes = allocationByteCount
    )
}

fun BitmapDecodeRecord.isSuspiciousLargeBitmap(
    maxAllocationBytes: Int,
    maxDimensionRatio: Float
): Boolean {
    require(maxAllocationBytes > 0 && maxDimensionRatio >= 1f)
    if (targetWidth <= 0 || targetHeight <= 0) {
        return allocationBytes >= maxAllocationBytes
    }
    val widthRatio = bitmapWidth.toFloat() / targetWidth
    val heightRatio = bitmapHeight.toFloat() / targetHeight
    return allocationBytes >= maxAllocationBytes &&
        (widthRatio >= maxDimensionRatio || heightRatio >= maxDimensionRatio)
}
```

调用方需要按场景传入经过实测的字节预算和维度比，不能把示例函数变成全业务共用的固定阈值。这段记录还要和页面生命周期合起来看。页面退出后，如果同一 `scene` 的大图对象仍在 HPROF 中可达，按 23.2 的引用链方法处理；如果对象已释放，但原生堆峰值过高，重点查解码尺寸、缓存上限和并发解码数量。

生产采样要控制频率。建议只上报超过阈值的记录，用不含用户数据的类别标识记录图片来源，不上传真实 URL、文件名或用户图片内容。图片问题经常涉及用户隐私，监控只需要尺寸、配置、字节数和页面路径。

## 图片复用池与 inBitmap

`inBitmap` 用于减少反复分配和释放像素内存的成本。列表快速滑动、瀑布流和聊天图片流会持续创建相近尺寸的 Bitmap；如果每次都新分配，原生堆峰值和分配抖动都会增大。这里的分配抖动是指短时间内反复申请、释放大量像素存储。复用池保留已淘汰、容量合适且不再显示的 mutable Bitmap，下一次解码尝试写入这块内存。

Android 4.4 之后，`BitmapFactory` 的复用条件放宽为：任意 mutable Bitmap 都可以作为候选，只要预计输出所需的字节数小于或等于候选 Bitmap 的 `allocationByteCount`。AOSP `BitmapFactory.Options` 也明确写着，复用失败时解码方法会抛出 `IllegalArgumentException`；调用方必须使用方法返回的 Bitmap，不能假定传入的 `inBitmap` 一定被使用。

这段代码展示复用池的最小安全形态。候选必须 mutable；按目标字节数筛选；复用失败后移除候选并重试一次普通解码。

```kotlin
class BitmapReusePool {
    private val pool = LinkedHashSet<Bitmap>()

    @Synchronized
    fun put(bitmap: Bitmap) {
        if (!bitmap.isRecycled && bitmap.isMutable && bitmap.config != Bitmap.Config.HARDWARE) {
            pool += bitmap
        }
    }

    @Synchronized
    fun take(requiredBytes: Int): Bitmap? {
        val iterator = pool.iterator()
        while (iterator.hasNext()) {
            val candidate = iterator.next()
            if (candidate.isRecycled) {
                iterator.remove()
                continue
            }
            if (candidate.allocationByteCount >= requiredBytes) {
                iterator.remove()
                return candidate
            }
        }
        return null
    }

    @Synchronized
    fun discard(bitmap: Bitmap) {
        pool.remove(bitmap)
    }
}

fun decodeWithReuse(
    path: String,
    requiredBytes: Int,
    pool: BitmapReusePool
): Bitmap? {
    val candidate = pool.take(requiredBytes)
    val options = BitmapFactory.Options().apply {
        inMutable = true
        inBitmap = candidate
    }

    return try {
        BitmapFactory.decodeFile(path, options)
    } catch (error: IllegalArgumentException) {
        candidate?.let(pool::discard)
        BitmapFactory.decodeFile(path, BitmapFactory.Options().apply { inMutable = true })
    }
}
```

生产实现还要补齐三类约束：复用池必须有总容量上限，避免变成常驻大缓存；候选进入池前必须确认不再显示或被其他解码任务使用；候选选择除字节数外还要考虑宽高、色彩配置和业务场景。把一张超大横图的分配区复用于小图，虽然可能解码成功，却会让 `allocationByteCount` 长期偏大。如果所用图片库已经管理缓存或像素复用，应由图片库统一管理所有权，避免再叠加一套互不知情的自建池。

`inBitmap` 不适合和 `Bitmap.Config.HARDWARE` 混用。AOSP `BitmapFactory.Options.validate()` 会拒绝硬件 Bitmap 作为 `inBitmap`，官方文档也说明硬件 Bitmap 总是 immutable。需要可变像素、二次绘制或复用池的图片，应走软件 Bitmap。

## Hardware Bitmap 的使用场景与限制

`Bitmap.Config.HARDWARE` 表示像素只存放在图形内存中；Java `Bitmap` 包装对象和原生元数据仍然存在，因此“像素不在 Java 或原生堆”不等于这张图没有内存成本。`ImageDecoder` 的 AOSP 注释说明，默认创建的 Bitmap 不可修改，并且通常采用 `Config.HARDWARE`。这个“通常”有具体边界：`ALLOCATOR_DEFAULT`（默认像素分配策略）可能为小图选择软件分配，也会在 mutable、alpha mask（透明度蒙版）等条件与硬件分配不兼容时切换到软件。只展示、不修改、由硬件加速管线绘制的图片适合 Hardware Bitmap，例如详情页大图、列表中不需要像素读取的封面图。

硬件 Bitmap 的限制集中在可变性和绘制路径：它不能作为 `inBitmap` 候选，也不能和 `inMutable = true` 同时要求。AOSP `BaseCanvas` 的标准软件绘制路径遇到 `Config.HARDWARE` 会抛出 `IllegalArgumentException("Software rendering doesn't support hardware bitmaps")`。因此下列场景应避免硬件 Bitmap：

- 需要 `Canvas` 软件绘制、截图合成、离屏处理或生成分享图。
- 需要读取或修改像素，例如滤镜、马赛克、取色、手写涂鸦。
- 需要进入 `inBitmap` 复用池。
- 目标 View 可能跑在软件渲染路径，或者业务里显式创建了软件 `Canvas`。

图片库的默认策略可以按用途区分：展示型图片优先允许 Hardware Bitmap，编辑型图片强制使用软件 Bitmap；列表页根据设备内存、圆角或变换需求和占位图策略决定。全局开关不能只依据“硬件更省内存”或“软件更兼容”，还要看 Bitmap 的实际使用方式。

## 案例：在第一次像素分配前限制尺寸

货拉拉公开复盘记录过一个图片发送峰值：发送前后原生内存突增，内存分类显示这部分增长来自大 Bitmap，代码检查发现旋转逻辑先完整解码原图，再做缩放与方向变换。输出图片即使很小，峰值阶段仍可能同时持有原图像素和变换后的中间结果。

这类问题要在第一次像素分配之前限制尺寸：先读取边界与 EXIF 方向，根据上传或展示目标计算采样尺寸，再解码、旋转或裁剪。验收至少覆盖处理前基线、解码峰值、变换峰值、上传结束和页面退出后的回落，并使用接近业务允许上限的图片尺寸与方向组合。只比较操作结束后的平均值，会漏掉触发 OOM 的瞬时峰值。

## 排查顺序

Bitmap 问题适合按“尺寸 → 生命周期 → 复用 → 配置”四步排查。这个顺序先区分应用侧问题，再决定是否继续检查原生堆或图片库实现。

1. **尺寸是否匹配显示目标**：检查原图尺寸、解码尺寸、目标 View 尺寸和 `allocationByteCount`。大图先用 `inJustDecodeBounds` + `inSampleSize` 降低像素数。
2. **生命周期是否按页面释放**：页面退出后查 HPROF，确认 Activity、Adapter、ImageView、图片请求和 Bitmap 是否仍被引用。引用链处理见 23.2。
3. **复用池是否降低分配峰值**：列表和图片流场景观察 Bitmap 分配次数、复用命中率、池容量和淘汰策略。复用池命中低时，先检查尺寸分组是否合理，不能直接扩大容量。
4. **配置是否符合使用方式**：展示图可评估硬件 Bitmap；需要像素处理、软件 Canvas 或复用池时使用软件 Bitmap；低质量缩略图再评估 `RGB_565`。

这四步仍无法解释原生堆增长时，再进入 [23.3 Native 与虚拟内存管理优化](03-native-virtual-memory-optimization.md)，使用 `malloc_debug`（原生分配调试工具）、heapprofd（Perfetto 原生堆分析器）或图片库内部统计继续归因。

## 全文小结

Bitmap 内存优化首先控制第一次像素分配：依据目标尺寸和方向读取边界、降采样，再选择与显示或编辑需求匹配的像素格式。文件体积、Java 包装对象大小和最终 View 尺寸都不能代替 `allocationByteCount` 与实际存储分区。

随后才处理生命周期、缓存和复用。软件 Bitmap、Hardware Bitmap 与 `inBitmap` 有不同的所有权和绘制约束；统一入口应记录尺寸、配置、分配量和场景，并用页面退出后的引用链与原生/图形内存回落共同验收。
