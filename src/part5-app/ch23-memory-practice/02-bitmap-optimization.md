---
title: "Bitmap 与图片内存优化"
chapter: "23.2"
section: "23.2"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-06-30"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/load-bitmap"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/Bitmap"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/BitmapFactory.Options"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/Bitmap.Config"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapFactory.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BaseCanvas.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/ImageDecoder.java"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]"
  - type: clipping
    path: "货拉拉司机 Android 端内存治理实践（本地归档 Cubox）"
tags: [bitmap, insamplesize, native-memory, inbitmap, hardware-bitmap]
related_chapters: ["23.1", "22.6", "22.35", "4.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
consolidated_from:
  - "src/part5-app/ch23-memory-practice/08-memory-case-studies.md"
---

# Bitmap 与图片内存优化

## 为什么要了解 Bitmap 与图片内存优化

图片内存问题很少是单一原因。解码尺寸、缓存复用、页面生命周期、设备内存预算——这几个因素叠加才会把问题放大。举例：一张 4000×3000 的 `ARGB_8888` 图片需要 48,000,000 字节，约 45.8 MiB；200×150 的目标视图只有 30,000 个像素。若仍按原尺寸解码，分配的像素数是显示目标的 400 倍，随后交给 Canvas 缩小也无法省掉这次解码分配。Android 10 到 Android 17 的普通软件 Bitmap 会推高 Native Heap，硬件 Bitmap 则占用图形缓冲区。

这一节从四个应用侧入口来谈：解码前算清目标尺寸，用 `inSampleSize` 降低像素数；理解 Android 8.0 之后 Bitmap 像素内存进了 Native Heap，对监控口径的影响；在图片加载入口记录大图和泄漏线索；用 `inBitmap` 复用减少反复分配。ART 堆和 GC 的机制详见 4.3 节，图片加载和渲染侧问题详见 22.6 节，页面对象泄漏对 Bitmap 的放大效应详见 23.1 节。

## Bitmap 内存计算与 inSampleSize

Bitmap 的内存预算从三个量开始：宽、高、每像素字节数。常见配置里，`ARGB_8888` 每像素 4 字节，`RGB_565` 每像素 2 字节，`ALPHA_8` 每像素 1 字节，`RGBA_F16` 每像素 8 字节。工程估算可以先用下面的式子：

```text
bytes ≈ width × height × bytesPerPixel
```

这只是估算。Android `Bitmap.getByteCount()` 返回当前像素所需的最小字节数，`getAllocationByteCount()` 返回底层分配区大小；当 Bitmap 被 `inBitmap` 复用或 `reconfigure()` 调整后，后者可能大于前者。排查内存占用时优先记录 `allocationByteCount`，否则会低估复用池里的大块分配。

解码前先读尺寸，不直接创建像素内存。`BitmapFactory.Options.inJustDecodeBounds = true` 时，解码方法返回 `null`，但会填充 `outWidth`、`outHeight` 和 `outMimeType`。这一步适合放在所有本地文件、资源图、网络图落盘后的统一解码入口。

下面这段代码只做采样率计算。重点看两次 decode：第一次只取边界，第二次才分配像素内存。

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

`inSampleSize = 4` 表示宽高约降到原图的 1/4，像素数约降到 1/16。官方文档说明，非 2 的幂会向下取到最接近的 2 的幂；因此采样率计算不要把任意比例当作精确缩放。解码后的图片仍可能需要再按 View 尺寸缩放，但那是显示阶段的成本，不能替代解码阶段的像素数控制。

选择 `inPreferredConfig` 要按使用场景定。照片、透明图、需要高质量缩放的 UI 图默认用 `ARGB_8888`；没有 alpha、质量要求较低的列表缩略图可以评估 `RGB_565`，但要接受色彩精度下降和渐变色带风险；HDR 或广色域图片可能进入 `RGBA_F16`，内存预算要按 8 字节/像素计算。不要把 `RGB_565` 当成通用省内存开关。

## Android 8.0+ Bitmap Native 内存迁移

Bitmap 像素数据的存放位置经历过三次变化：Android 2.3.3 及更早版本放在 Native 内存；Android 3.0 到 7.1 随 Bitmap 对象放在 Dalvik Heap；Android 8.0 及以上重新进入 Native Heap。当前章节覆盖 Android 10 到 Android 17：普通软件 Bitmap 的像素分配按 Native Heap 排查，`Config.HARDWARE` 的像素分配则按图形缓冲区排查。

AOSP `Bitmap.java` 中，Java 对象保存 `mNativePtr`。Android 17 的 `registerNativeAllocation()` 使用两个 `NativeAllocationRegistry`：一个以 no-op 释放函数登记像素数据大小，用于把 Native 分配反馈给 ART；另一个通过 `sRegistry` 登记 native Bitmap 对象及其释放函数。`recycle()` 使用前者返回的 `mRecycler` 更新像素分配记账。这个设计带来两个工程结论：

- **Bitmap 对象仍受 Java 可达性影响**：Java 层对象被 Activity、Adapter、缓存或回调引用时，Native 像素内存也会被保留。Bitmap 泄漏的根不一定在 Native 层，常常是 Java 引用链没有断开。
- **Native Heap 变大不等于 JNI 泄漏**：Android 8.0 之后，图片加载增加会直接推高 Native Heap。用 `dumpsys meminfo` 或线上内存指标看到 Native Heap 上升时，先区分是 Bitmap 分配还是 JNI/so 库分配，不要直接归因到 JNI 泄漏。

`recycle()` 只能作为明确失效后的提前释放手段，不适合替代生命周期管理。官方文档对旧版本建议过引用计数式 `recycle()`，但也提醒：Bitmap 被回收后再绘制会触发 “Canvas: trying to use a recycled bitmap”。在 Android 10+ 项目里，更稳的策略是让图片请求跟随页面生命周期取消，让缓存有上限，让不可见页面及时释放强引用；只有超大图编辑、一次性解码、离屏处理这类边界清楚的场景，才考虑显式 `recycle()`。

## 图片内存监控与大图检测

图片监控不要等到 OOM 再看堆。统一图片入口应记录“原图尺寸、目标 View 尺寸、解码后尺寸、配置、分配字节数、页面名、调用栈摘要”。这组信息能直接回答两个问题：是否解码了远大于显示尺寸的图片；是否有页面在退出后仍保留大图。

大图阈值应按屏幕、业务类型、同时在内存中的图片数量和设备内存档位制定。全屏预览、图片编辑、头像和列表封面的合理预算不同；同一张图在单图详情页可以接受，进入多列列表后就可能让并发像素预算失控。维度比与分配字节数都应做成可配置策略，并通过目标设备上的峰值内存和滚动测试确定阈值。只用一个固定 MB 数字会漏掉低内存设备，也会误报正常的图片编辑场景。

下面这段代码展示统一解码后的记录点。它不替代图片库，只负责把高风险 Bitmap 暴露出来。

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

调用方需要按场景传入经过实测的字节预算和维度比，不能把示例函数变成全业务共用的固定阈值。这段记录还要和页面生命周期合起来看。页面退出后，如果同一 `scene` 的大图对象仍在 Hprof 中可达，按 23.1 节的引用链方法处理；如果对象已释放，但 Native Heap 峰值过高，重点查解码尺寸、缓存上限和并发解码数量。

线上采样要控制频率。建议只上报超过阈值的记录，保留图片来源的模板化标识，不上传真实 URL、文件名或用户图片内容。图片问题经常涉及用户隐私，监控只需要尺寸、配置、字节数和页面路径。

## 图片复用池与 inBitmap

`inBitmap` 解决的是反复分配和释放像素内存的成本。列表快速滑动、瀑布流、聊天图片流会持续创建相近尺寸的 Bitmap；如果每次都新分配，Native Heap 峰值和分配抖动都会变大。复用池把已淘汰但容量合适的 mutable Bitmap 留下来，下一次 decode 直接写入这块内存。

Android 4.4 之后，`BitmapFactory` 的复用条件放宽为：任意 mutable Bitmap 都可以用于解码其他 Bitmap，只要新 Bitmap 的 `byteCount` 小于或等于候选 Bitmap 的 `allocationByteCount`。AOSP `BitmapFactory.Options` 也明确写着，复用失败时 decode 会抛 `IllegalArgumentException`，调用方必须使用 decode 返回的 Bitmap，不能假定传入的 `inBitmap` 一定被使用。

下面这段代码展示复用池的最小安全形态。重点是三点：候选必须 mutable；按目标字节数筛选；复用失败后移除候选并重试一次普通 decode。

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

生产实现要比这段代码多两个约束。第一，复用池必须有总容量上限，否则它会从优化手段变成常驻大缓存。第二，候选选择不能只看字节数，还要结合宽高、色彩配置和业务场景；把一张超大横图分配复用于小图，虽然能 decode 成功，但会让 `allocationByteCount` 长期偏大。

`inBitmap` 不适合和 `Bitmap.Config.HARDWARE` 混用。AOSP `BitmapFactory.Options.validate()` 会拒绝硬件 Bitmap 作为 `inBitmap`，官方文档也说明硬件 Bitmap 总是 immutable。需要可变像素、二次绘制或复用池的图片，应走软件 Bitmap。

## Hardware Bitmap 的使用场景与限制

`Bitmap.Config.HARDWARE` 表示像素只存放在图形内存中；Java `Bitmap` 包装对象和 native 元数据仍然存在，因此“像素不在 Java/Native Heap”不等于这张图没有内存成本。`ImageDecoder` 的 AOSP 注释说明，默认创建的 Bitmap 是 immutable，并且通常采用 `Config.HARDWARE`。这里的“通常”不能省略：`ALLOCATOR_DEFAULT` 可能为小图选择软件分配，也会在 mutable、alpha mask 等条件与硬件分配不兼容时切换到软件。只展示、不修改、由硬件加速管线绘制的图片适合硬件 Bitmap，例如详情页大图、列表中不需要像素读取的封面图。

硬件 Bitmap 的限制集中在可变性和绘制路径：它不能作为 `inBitmap` 候选，也不能和 `inMutable = true` 同时要求。AOSP `BaseCanvas` 的标准软件绘制路径遇到 `Config.HARDWARE` 会抛出 `IllegalArgumentException("Software rendering doesn't support hardware bitmaps")`。因此下列场景应避免硬件 Bitmap：

- 需要 `Canvas` 软件绘制、截图合成、离屏处理或生成分享图。
- 需要读取或修改像素，例如滤镜、马赛克、取色、手写涂鸦。
- 需要进入 `inBitmap` 复用池。
- 目标 View 可能跑在软件渲染路径，或者业务里显式创建了软件 `Canvas`。

图片库的默认策略可以按用途拆开：展示型图片优先允许硬件 Bitmap，编辑型图片强制软件 Bitmap；列表页根据设备内存、圆角/变换需求和占位图策略决定。不要只按“硬件更省内存”或“软件更兼容”做全局开关，Bitmap 的使用方式才是判断依据。

## 案例：在第一次像素分配前限制尺寸

货拉拉公开复盘记录过一个图片发送峰值：发送前后 Native 内存突增，内存分类把增长指向大 Bitmap，代码检查发现旋转逻辑先完整解码原图，再做缩放与方向变换。最终结果即使很小，峰值阶段仍可能同时持有原图像素和变换后的中间结果。

这类问题的修改点应前移到第一次像素分配之前：先读取边界与 EXIF 方向，根据上传或展示目标计算采样尺寸，再解码、旋转或裁剪。验收至少覆盖处理前基线、解码峰值、变换峰值、上传结束和页面退出后的回落，并使用接近业务允许上限的图片尺寸与方向组合。只比较操作结束后的平均值，会漏掉真正触发 OOM 的瞬时峰值。

## 一套可执行的排查顺序

Bitmap 问题适合按“尺寸 → 生命周期 → 复用 → 配置”四步排查。这个顺序能避免一开始就陷入 Native Heap 或图片库内部实现。

1. **尺寸是否匹配显示目标**：检查原图尺寸、解码尺寸、目标 View 尺寸和 `allocationByteCount`。大图先用 `inJustDecodeBounds` + `inSampleSize` 降低像素数。
2. **生命周期是否按页面释放**：页面退出后查 Hprof，确认 Activity、Adapter、ImageView、图片请求和 Bitmap 是否仍被引用。引用链处理详见 23.1 节。
3. **复用池是否压住分配峰值**：列表和图片流场景观察 Bitmap 分配次数、复用命中率、池容量和淘汰策略。复用池命中低时，不要盲目扩大容量，先看尺寸分桶是否合理。
4. **配置是否符合使用方式**：展示图可评估硬件 Bitmap；需要像素处理、软件 Canvas 或复用池时使用软件 Bitmap；低质量缩略图再评估 `RGB_565`。

这四步走完，仍然解释不了 Native Heap 增长，再进入 23.3 节的 Native 内存排查路径，使用 malloc debug、heapprofd 或图片库内部统计继续归因。
