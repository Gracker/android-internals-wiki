---
title: 图片加载与 Bitmap 性能优化
chapter: 7.10
section: 7.10
status: ready-for-review
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
tags: [bitmap, image-decode, hardware-bitmap, glide, coil, image-loading, memory, jank]
related_chapters: ["7.4", "7.5", "7.8", "4.5", "2.10", "14.1"]
created_by: task2a-knowledge-gap
created_date: 2026-04-07
gap_source: AOSP结构+官方文档+读者需求
gap_score: 17
drafted_date: 2026-04-07
drafted_by: openclaw-task2a
last_verified: 2026-07-03
last_verified_against: AOSP android-17.0.0_r1
reviewed_date: 2026-07-03
reviewed_by: openclaw-task6
task6_result: pass-light-edit
confidence: medium
sources: 
- type: research
path: intake/research-feeds/2026-03-31-19-ch04-app-bitmap-pool-optimization.md
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: fixed
task2b_result: fixed
last_rework_date: 2026-05-06
last_rework_by: openclaw-task2b
last_rework_reason: P95 Task9回炉(第四轮)：P0 inBitmap返回对象语义修正（reinitBitmap→return javaBitmap，返回值即inBitmap同一对象）
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-06
task6_review_notes: 2026-04-30 task6 revisiting review (post-task2b fix): pass-light-edit。task2b已修正P0 inSampleSize源码锚点+P1 Gainmap内存模型+ImageDecoder内存峰值。L1/L2全通过，无B类大问题。task9需复审。 | 2026-05-05 task6 revisiting review 07:30: pass-light-edit。清理重复 frontmatter、未标语言代码块、高频填充词和第一人称；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。 | 2026-05-06 task6 revisiting review 08:15: pass-light-edit。清理编辑痕迹、虚假引导语和中英文格式；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。 | 2026-05-06 task6 revisiting review 09:07: pass-light-edit。移除未支撑的 upload/WebP/AVIF 量化口径，清理发布稿编辑痕迹和夸张标题；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。 | 2026-05-06 task6 revisiting review 10:10: pass-light-edit。清理 frontmatter 禁用词、口语化表达、绝对化措辞和结构性引导语；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。
last_task9_at: 2026-05-06T12:42:00+08:00
last_task9_audit: 2026-07-03
last_task9_audit_log: logs/deep-review/2026-07-03-11-audit.md
task9_review_notes: 2026-05-06 08:30 task9 deep-review: needs-rework。P0 1：inBitmap 复用示例把返回对象语义写错；P1 1：AVIF/AV1 硬件能力边界过度外推；P2 2：Hardware Bitmap upload 与 WebP 压缩率缺少数据支撑。 | 2026-05-06 08:45 task2b rework(第三轮): P0 inBitmap像素转移语义修正；P1 AVIF硬件加速边界收窄 | 2026-05-06 09:20 task9 回归审计: needs-rework。P0 1 / P1 0 / P2 1；inBitmap 复用对象语义仍未解决。 | 2026-05-06 12:42 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；AVIF fallback 实现名与 Perfetto 调用栈采集条件写入 suggestions；无 active queue pending，自动晋升 finalized。
last_task6_at: 2026-07-03T12:13:55+08:00
last_task6_audit: 2026-06-28
last_task6_review_log: logs/review/2026-05-06-10-review.md
task9_result: auto-fixed
last_task9_autofix_at: 2026-07-03
auto_promoted: true
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-03
---
-
# 7.10 图片加载与 Bitmap 性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 BitmapFactory / ImageDecoder 的解码流程，以及 `inSampleSize`、`setTargetSize` 等关键参数
- 🔹 Bitmap 像素内存的版本差异，与 `Bitmap.Config.HARDWARE` 的适用边界
- 🔹 `inBitmap` 复用、BitmapPool，以及 Glide / Coil 的缓存与解码管线
- 🔹 JPEG、WebP、AVIF 等格式的解码成本，与大图 OOM 风险
- 🔹 在 Perfetto 中定位图片解码卡顿的方法与观察点
- 🔹 图片加载优化的可执行检查清单

### 扩展（可选深入）

- 🔸 Hardware Bitmap 的 fd 成本与低端设备限制
- 🔸 大型 App 的图片优化实践

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 量化数据、GPU 内存与解码器行为如果没有官方或实测证据，保留 `[待验证]`，不要写成确定结论。
<!-- outline-end -->

打开一份 Perfetto trace，发现主线程有一帧花了 200ms。展开调用栈，主要耗时来自 `BitmapFactory.decodeResource`——一张 4000×3000 的照片被原尺寸解码到内存，吃掉了 48MB，GC 被触发，界面就卡了。

图片解码是 Android 上资源开销很高的常规操作之一。一张手机拍的照片，磁盘上可能只有 5MB，但解码后在内存中占用的空间是 `宽 × 高 × 4` 字节（ARGB_8888 格式），很容易超过 20MB。列表滑动场景中，如果在主线程连续解码十几张这样的图，GC 频繁触发，就很容易掉帧。

本节说明图片加载和 Bitmap 管理的完整过程：从 BitmapFactory 的内部机制到 Hardware Bitmap 的 GPU 内存模型，从 Glide/Coil 的管线架构到如何在 Perfetto 中定位图片解码导致的卡顿。读完后，读者能独立分析图片相关的性能问题，并给出针对性的优化方案。

## BitmapFactory 与 ImageDecoder：解码的两代方案

### BitmapFactory 的解码流程

BitmapFactory 是 Android 最早的图片解码 API，提供了 `decodeResource`、`decodeFile`、`decodeStream`、`decodeByteArray` 四个入口。不管用哪个入口，内部的解码流程是一样的：

1. **读取数据源**：从文件、资源、流或字节数组中获取原始图片数据。
2. **解析头部**：读取图片的格式信息（JPEG/PNG/WebP 等）、宽高、色彩空间，不分配像素内存。
3. **分配内存**：根据目标配置（Bitmap.Config）和缩放参数，在 Native 堆（Android 8.0+）或 Java 堆（8.0 之前）分配像素数据所需的连续内存。
4. **解码像素**：将压缩的图片数据解码为原始像素点阵。

这个过程有几个关键的参数，都在 `BitmapFactory.Options` 中：

**inJustDecodeBounds**——设为 `true` 时，只执行第 2 步（解析头部），不分配内存也不解码像素。这是预加载的标准操作：先用它拿到原始宽高，计算采样率，再正式解码。

**inSampleSize**——采样率。设为 2 时，解码结果的宽高各缩小一半，像素数变为原来的 1/4，内存占用也降为 1/4。

官方 API 文档仍建议将 `inSampleSize` 设为 2 的幂（1、2、4、8...），这是跨格式、跨设备的兼容安全口径。但现代 AOSP 的 native 解码路径已经不再强制这一约束：`libs/hwui/jni/BitmapFactory.cpp` 的 `doDecode()` 将 `inSampleSize` 传给 `SkAndroidCodec::getSampledDimensions(sampleSize)`，由 SkCodec 按具体格式能力决定采样方案，必要时做 fine scale。也就是说，传 3 在多数设备上能得到约 1/3 尺寸的结果，但行为因格式和 codec 实现而异，生产代码仍推荐 2 幂。

如果需要非 2 幂的精确降采样（比如原图 4000×3000 只需要 1200×900），`ImageDecoder.setTargetSize()` 是更合适的 API——它直接指定目标尺寸，解码器内部完成缩放，不受 2 幂限制。[已验证：AOSP `libs/hwui/jni/BitmapFactory.cpp` doDecode() + `SkAndroidCodec::getSampledDimensions()` + Android API 文档 `BitmapFactory.Options.inSampleSize`]

**inPreferredConfig**——目标色彩格式。默认 `ARGB_8888`（每像素 4 字节）。如果图片不需要透明通道，用 `RGB_565`（每像素 2 字节）可以节省一半内存。

**inBitmap**——Android 4.4（API 19）之后的核心优化参数。传入一个已有的 Bitmap，解码时复用它的像素内存，不再分配新的。这个机制是 Glide 等图片库减少 GC 压力的基石，后文展开。

**inDensity / inTargetDensity**——从资源文件（`decodeResource`）加载图片时，这两个参数决定了缩放比例。`inDensity` 是资源所在目录的 dpi（如 `drawable-xxhdpi` 对应 480），`inTargetDensity` 是设备的屏幕 dpi。解码后的实际尺寸 = 原始尺寸 × `inTargetDensity / inDensity`。这就是为什么同一张图放在不同 drawable 目录下，加载后的内存占用可能差好几倍。

```java
// 示意代码：BitmapFactory Options 中采样与 density 缩放的逻辑（伪代码，非 AOSP 源码原文）
// 实际实现见 libs/hwui/jni/BitmapFactory.cpp doDecode()
if (options.inSampleSize != 1) {
    width = width / options.inSampleSize;
    height = height / options.inSampleSize;
}
// 从资源加载时的额外缩放
if (options.inTargetDensity != 0 && options.inDensity != 0) {
    width = (width * options.inTargetDensity + options.inDensity / 2) 
            / options.inDensity;
    height = (height * options.inTargetDensity + options.inDensity / 2) 
             / options.inDensity;
}
```

这段代码说明两件事：`inSampleSize` 的缩放是整数除法，不是浮点缩放；资源文件的 dpi 匹配直接影响内存占用——把一张 1080p 的图放在 `drawable-mdpi` 目录，在 xxhdpi 设备上加载后实际像素是 3240×5760，内存从 8MB 暴涨到 72MB。[已验证：来源见 万字长文 Android Bitmap 相关的一切 中关于 density 缩放的计算说明]

### ImageDecoder：API 28+ 的现代替代

Android 9（API 28）引入了 `ImageDecoder`，官方推荐在新项目优先使用。相比 BitmapFactory，它有几个实质性改进：

**自动处理 EXIF 旋转**。用 BitmapFactory 加载一张手机拍的 JPEG，如果照片有旋转标记（Exif ORIENTATION_ROTATE_90），通常要手动读取 EXIF 信息并做旋转变换。ImageDecoder 在解码时自动处理了这件事。

**统一的数据源 API**。不再需要区分 `decodeResource`、`decodeFile`、`decodeStream`——`ImageDecoder.decodeDrawable` / `decodeBitmap` 接受 `Source` 对象，通过 `ImageDecoder.createSource` 从任意来源创建。

**原生支持动画**。解码 GIF 或 WebP 动图时，返回 `AnimatedImageDrawable`，自带播放控制。用 BitmapFactory 完全做不到这一点。

**setTargetSize 替代 inSampleSize**。不需要手动计算 2 的幂采样率，直接设定期望尺寸，解码器内部处理缩放。`ImageDecoder` 在单次解码流水线中完成采样和缩放，避免 `BitmapFactory` 常见的「先按 2 幂采样再二次缩放」路径中产生的大图缓冲区峰值。对大图场景（如 4000×3000 原图解码到 1080p），这个差异能降低解码过程中的内存峰值（Memory Spike），减少 OOM 风险。

这两个边界要分清：`setTargetSize` 必须在 `OnHeaderDecodedListener` 回调内设置；最终走 sample 还是 scale 由 codec 能力决定，不能无条件写成所有格式都避免大缓冲。`setTargetSampleSize()` 可以让解码器按可高效执行的方向取整。

```java
// ImageDecoder 的典型用法
ImageDecoder.Source source = ImageDecoder.createSource(getResources(), R.drawable.photo);
Drawable drawable = ImageDecoder.decodeDrawable(source, (decoder, info, s) -> {
    // 设置目标尺寸（替代 inSampleSize）
    decoder.setTargetSize(1080, 1920);
    // 如果需要，可以选择硬件位图配置
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        decoder.setAllocator(ImageDecoder.ALLOCATOR_HARDWARE);
    }
});
```

实际项目中，BitmapFactory 和 ImageDecoder 的选择往往被图片加载库封装了。以 Glide 4.x 为例，Bitmap 请求默认仍走 `Downsampler` / `BitmapFactory`。只有应用显式调用 `GlideBuilder.setImageDecoderEnabledForBitmaps(true)`，并且设备是 Android 10（API 29）及以上时，Glide 才会把 Bitmap 解码切到 `ImageDecoder`。排查同一张图在不同设备上的解码差异时，先确认库版本和这个开关。[已验证：Glide `GlideBuilder#setImageDecoderEnabledForBitmaps`]

### Bitmap 像素内存分配的版本差异

Bitmap 的 Java 对象一直在 Java 堆里，但像素数据放在哪里，Android 历史演进分成三段：

**Android 2.3.3（API 10）及以下**：像素数据在 Native memory，Java 堆里只有 Bitmap 壳对象。旧版本里像素内存释放和 Dalvik GC 不完全同步，所以经常要配合 `recycle()` 尽快回收。[已验证：官方文档 `Managing Bitmap Memory`]

**Android 3.0（API 11）到 Android 7.1（API 25）**：像素数据改放到 Dalvik / ART managed heap，Bitmap 对象和像素一起受 GC 管理。`inBitmap` 这类复用策略在这个阶段也更容易观察和调试。[已验证：官方文档 `Managing Bitmap Memory`]

**Android 8.0（API 26）及之后**：像素数据再次回到 Native heap。Java 堆压力会下降，但这些像素页仍然计入进程 PSS，所以图片解码过多，进程一样会因为总体内存压力被 `lmkd` 回收。[已验证：官方文档 `Managing Bitmap Memory` + AOSP `frameworks/base/libs/hwui/jni/Bitmap.cpp`]

这套模型能成立，靠的不是“GC 直接扫描 Native heap”，而是 `Bitmap.java` 通过 `NativeAllocationRegistry` 把底层像素内存登记给 ART。Bitmap 的 Java 壳对象仍留在 Java 堆；当这个 Java 对象不可达时，registry 会调用注册好的 native free 函数释放底层像素内存。同时，ART 会把这部分 registered native size 纳入内存压力判断，所以大批量图片解码仍然可能把并发 GC 提前拉起来。也正因为这层绑定，绝大多数常规场景不需要手动调用 `recycle()`。

### 各 Bitmap.Config 的内存开销对比

| Config | 每像素字节 | 透明通道 | 色彩质量 | 适用场景 |
|--------|-----------|---------|---------|---------|
| ARGB_8888 | 4 | ✅ | 1677 万色 + 256 级透明 | 默认选择，照片、UI 元素 |
| RGB_565 | 2 | ❌ | 65536 色 | 不需要透明的大图、缩略图 |
| HARDWARE | 4（GPU 侧） | ✅ | 等同 ARGB_8888 | 只显示不修改的图片（详见下节） |
| ALPHA_8 | 1 | ✅（仅透明度） | 无 | 遮罩、透明度模板 |
| RGBA_F16 | 8 | ✅ | 广色域（HDR） | HDR 照片编辑、Wide Color Gamut |

一张 1080×1920 的图片在不同配置下的内存占用：ARGB_8888 = 7.9MB，RGB_565 = 3.9MB，HARDWARE ≈ 0MB（Java 堆侧）。从数字上就能看出来——列表场景如果把透明度不重要的图切成 RGB_565，内存立刻省一半。

### Ultra HDR / Gainmap 内存模型

Android 14+ 默认支持 Ultra HDR（Gainmap）。解码含 Gainmap 的 JPEG 时，GPU 需要同时维护基础层（base bitmap）和 Gainmap 掩码层（gainmap bitmap + metadata）。AOSP `Bitmap.java` 提供了 `hasGainmap()` / `getGainmap()` / `setGainmap(null)` API；`BitmapFactory.cpp` 通过 `getGainmapAndroidCodec()` / `decodeGainmap()` 完成解码。

内存估算不能只用 `宽 × 高 × 4`（ARGB_8888）。含 Gainmap 的 JPEG 在 GPU 显存中的真实开销高于 SDR 计算值，因为 base bitmap 和 gainmap bitmap 各占一份像素空间，加上 metadata。具体倍率取决于 gainmap 的分辨率和格式配置，不能按固定系数估算。在长列表场景中，这份额外开销会让显存水位（VRAM Usage）更早触顶。[待验证：1.25x 倍率缺乏一手实测支撑，实际倍率需按设备 GPU 和 gainmap 参数实测确认]

观测上，PSS / NativeAllocationRegistry 只登记 base bitmap 的 native 大小；Gainmap 部分的 GPU 显存通常不出现在 Java 堆统计里，需要结合 `dumpsys meminfo` 的 Graphics 类别和 `procfs` GPU memory 节点一起看。

工程建议：如果业务不需要 HDR 显示，可以在低端设备上解码后调用 `bitmap.setGainmap(null)` 移除 Gainmap 层，去掉这部分额外开销。[已验证：AOSP `Bitmap.java` hasGainmap()/getGainmap()/setGainmap() + `BitmapFactory.cpp` decodeGainmap()]

## Hardware Bitmap：像素存在 GPU 里

Android 8.0（API 26）引入了 `Bitmap.Config.HARDWARE`，它的像素数据不存储在 CPU 侧的 Native 堆，而是直接存在 GPU 内存（通过 `AHardwareBuffer` / `GraphicBuffer`）。

### 为什么能省内存

一张普通 Bitmap 的渲染路径是：CPU 侧 Native 堆存像素 → 上传到 GPU 纹理 → GPU 渲染。上传这一步需要把像素数据从 CPU 内存拷贝到 GPU 内存，既占带宽又占时间。列表快速滑动时，如果每帧都有新图片需要上传纹理，这个拷贝就会成为瓶颈。

Hardware Bitmap 跳过的是“software bitmap 首次绘制前的 GPU 纹理上传”。普通 software bitmap 解码完成后，像素还在 CPU 可访问内存里，第一次参与绘制时，RenderThread 仍要把它上传到 GPU。`Bitmap.prepareToDraw()` 的作用，就是尽量把这次上传提前到正常 draw path 之外。AOSP 注释写明，从 Android 7.0 起，这个调用会在 RenderThread 上异步触发 upload。如果图片已经是 `Bitmap.Config.HARDWARE`，渲染阶段就不再走这一步。[已验证：AOSP `Bitmap.prepareToDraw()` 注释]

### 文件描述符的隐性成本

每个 Hardware Bitmap 底层对应一个 `AHardwareBuffer`，而这个 buffer 会消耗文件描述符。进程 fd 上限由内核和设备配置决定，图片多的长列表、瀑布流和图库场景要特别留意这项开销。

在实际项目中，如果一个 `RecyclerView` 同屏保留大量 Hardware Bitmap，fd 数量会跟着增长。再叠加网络连接、数据库、日志文件等其他 fd 消耗者，进程就可能逼近上限。Glide 的 `HardwareConfigState` 之所以定期检查 `/proc/self/fd`，就是为了避免 hardware bitmap 把 fd 用光。[已验证：Glide `HardwareConfigState`]

### 限制

Hardware Bitmap 的限制，不是“系统会自动降级成普通 Bitmap”，而是很多 CPU 侧操作不可用，或者代价很高：

- `getPixel()`、`getPixels()`、`copyPixelsToBuffer()` 这类直接读像素的 API，会抛 `IllegalStateException`，因为 `Config.HARDWARE` 不支持 CPU 读写像素。[已验证：AOSP `Bitmap.java`]
- `sameAs()`、`copy(Config, ...)` 这类需要比较或复制整张图的路径，会触发 `StrictMode.noteSlowCall()`，因为框架可能要把 GPU 侧像素拉回 CPU 再处理。[已验证：AOSP `Bitmap.java`]

对图片库来说，要确认的是请求有没有软件 Canvas、像素读取、Palette、共享元素过渡或复杂 Transformation。遇到这些场景，就应该显式回退到 software bitmap。Glide 4.x 用 `disallowHardwareConfig()`，Coil 用 `allowHardware(false)`。如果请求只是把图直接画到屏幕上，才适合保留 `Bitmap.Config.HARDWARE`。

### 使用建议

- 纯展示、无像素访问：可以保留 Hardware Bitmap
- 需要圆角、模糊、Palette、共享元素或软件 Canvas：直接用 `ARGB_8888`
- 图片很多的 feed：同时观察 `/proc/self/fd` 或图片库的 hardware bitmap 限额



## Hardware Bitmap 与 RenderThread/SurfaceFlinger 合成管线

Hardware Bitmap 仍要经过 RenderThread 和 GPU 合成管线，不会直接作为独立图层交给 SurfaceFlinger。它省掉的是 software bitmap 首次绘制前的同步 upload 成本，不是整条渲染管线。

### 源码级证据

`SkiaGpuPipeline::prepareToDraw()`（`frameworks/base/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp:137-151`）中：

```cpp
void SkiaGpuPipeline::prepareToDraw(const RenderThread& thread, Bitmap* bitmap) {
    GrDirectContext* context = thread.getGrContext();
    if (context && !bitmap->isHardware()) {
        // 仅对 NON-hardware Bitmap 执行 upload
        ATRACE_FORMAT("Bitmap#prepareToDraw %dx%d", ...);
        auto image = bitmap->makeImage();
        skgpu::ganesh::PinAsTexture(context, image.get());
        skgpu::ganesh::UnpinTexture(context, image.get());
        context->flushAndSubmit();
    }
    // Hardware Bitmap 此处为空操作
}
```

`!bitmap->isHardware()` 分支明确表明 Hardware Bitmap 跳过 prepareToDraw 阶段的 upload 逻辑。但 RenderThread 本身依然参与（执行 draw 命令、GPU 渲染、Buffer 提交）。

### 完整的渲染管线

```text
App 主线程                      RenderThread                  SurfaceFlinger
   |                                  |                              |
View.onDraw(RecordingCanvas)         |                              |
       |                              |                              |
RenderNode.record()                   |                              |
       |                              |                              |
DisplayList 记录 drawBitmap 命令       |                              |
       |                              |                              |
                         syncFrameState()                              |
                                    |                                 |
                         DrawFrameTask.run()                          |
                                    |                                 |
                         SkiaCanvas::drawBitmap()                     |
                                    |                                 |
                         SkCanvas->drawImage(image from AHB)          |
                                    |                                 |
                         GPU 渲染命令执行 + context->flushAndSubmit()  |
                                             BufferQueue/dequeueBuffer
                                                                    |
                                                                    HWC composition
```

Hardware Bitmap 的优化点：**省去 software bitmap 首次绘制前的同步 upload 成本**，但无法绕过渲染管线直接交给 SurfaceFlinger。

## inBitmap 复用机制与 BitmapPool

### 为什么需要复用

Bitmap 的创建和销毁是内存抖动的主要来源之一。一次 `BitmapFactory.decodeResource` 会分配几十 KB 到几十 MB 不等的 Native 内存。当这个 Bitmap 不再使用被 GC 回收时，Native 内存释放。如果在列表滑动中反复执行这个过程——分配 → 使用 → 回收 → 分配 → 使用 → 回收——内存分配曲线会呈锯齿状，GC 被频繁触发。

单次 GC 不一定很长，但 GC 期间会暂停所有线程（在 ART 的部分 GC 模式下）。如果 GC 频率达到每秒几十次，累积的暂停时间就足以导致掉帧。

### inBitmap 的工作原理

`inBitmap` 的核心思想是：不释放旧 Bitmap 的内存，而是把这块内存拿去解码新图片。

```java
BitmapFactory.Options options = new BitmapFactory.Options();
options.inBitmap = reusableBitmap;  // 复用这个 Bitmap 的像素内存
options.inSampleSize = 2;
Bitmap resultBitmap = BitmapFactory.decodeResource(res, resId, options);
// decodeResource 返回值通常与 options.inBitmap 指向同一个 Bitmap 对象，
// 底层像素缓冲被重新配置并复用；调用方应使用返回值作为后续引用，
// 不要继续按旧尺寸/旧内容使用 reusableBitmap。
// [已验证：AOSP android-17.0.0_r1 BitmapFactory.cpp doDecode() —
//  javaBitmap != null 时执行 bitmap::reinitBitmap() 后 return javaBitmap]
```

关键细节：`decodeResource` 返回的 Bitmap 通常就是 `options.inBitmap` 传入的那个 Java 对象（不是新建对象）。底层像素缓冲被重新配置以容纳新解码的图片数据。调用方必须使用返回值作为后续引用——`reusableBitmap` 变量在解码后仍指向同一个对象，但其尺寸和内容已经改变，不应再按旧参数使用。[已验证：AOSP `BitmapFactory.cpp` `doDecode()` 中 `javaBitmap != nullptr` 分支执行 `bitmap::reinitBitmap()` 后 `return javaBitmap`]

### Glide 的 BitmapPool 实现

Glide 4.x 使用 `LruBitmapPool` 管理 Bitmap 复用池。当 Bitmap 不再使用时，不调用 `recycle()`，而是放回 BitmapPool。下次解码新图片时，Glide 从池中找一个大小足够的 Bitmap，通过 `inBitmap` 复用它的内存。

BitmapPool 的大小由 `MemorySizeCalculator` 根据设备配置自动计算（通常与内存缓存共享同一个内存预算）。当池满时，用 LRU 策略淘汰最早放入的 Bitmap。

Glide 的内存缓存体系分成三层：

1. **Active Resources**：正在被使用的图片，用弱引用持有。ImageView 还在显示这张图时，它会留在这里。
2. **LruResourceCache**：LRU 内存缓存。图片不再被 Active 持有时进入这里。
3. **LruBitmapPool**：Bitmap 复用池。解码新图片时优先从这里取可复用的 Bitmap。

这三层协同工作：当系统内存紧张时，Glide 收到 `ComponentCallbacks2.onTrimMemory` 回调，会按源码顺序清理：先通知所有 `RequestManager`（`level >= TRIM_MEMORY_MODERATE` 时暂停并移除未完成请求，更低 level 不做处理），再清理 `MemoryCache`（即 `LruResourceCache`），然后清理 `BitmapPool`，再清理 `ArrayPool`。`ActiveResources` 不是 `onTrimMemory` 的主动清理目标——它用弱引用持有正在使用的资源，引用计数归零时自然移入 `LruResourceCache`。[已验证：Glide 4.16.0 `Glide.trimMemory()` + `RequestManager.onTrimMemory()` 源码调用链]

## 图片格式解码性能

不同图片格式的解码速度差异很大，理解这些差异有助于在业务中选择合适的格式。

### 各格式解码成本对比

这组比较只讨论“同一设备、同一分辨率、使用系统默认解码器”时的常见趋势，不是 benchmark 结果。做格式选型，还是要在目标机型上实测。

| 格式 | 文件体积趋势 | 解码成本 | 适合场景 | 备注 |
|------|-------------|---------|---------|------|
| JPEG | 小 | 低 | 照片、封面 | 通用性最好 |
| PNG | 大 | 高 | 图标、透明 UI 资源 | 无损，照片类内容不划算 |
| WebP（有损） | 更小 | 低到中 | 照片、信息流图片 | 常见做法是用它替代 JPEG |
| WebP（无损） | 中到大 | 中到高 | 需要无损压缩的 UI 资源 | 解码通常比有损 WebP 更重 |
| AVIF | 很小 | 差异很大 | 带宽敏感的图片 | 软件解码偏慢，硬件能力要按设备确认 |
| GIF（单帧） | 中 | 中 | 兼容旧动画资源 | 色彩位数有限 |

[待验证：如果要给出具体毫秒数，需要固定设备、分辨率、图片样本、解码器实现，再用 Macrobenchmark 或自建基准实测]

### AVIF：更高压缩率与解码代价

Android 12（API 31）引入了对 AVIF 的基础支持。Android 14 对部分新设备要求支持 AV1 硬件解码，但 AVIF 的硬件加速取决于 SoC 的 AV1 解码器是否支持 still image 子集（SUBPEL 精度和 single tile 限制）；不满足条件的设备退回软件解码（libdav1d）。

AVIF 基于 AV1 视频编码的帧内压缩，相比 JPEG 在同等画质下通常能用更小文件换取相近画质；具体比例取决于图片内容、编码参数和解码器。对于带宽敏感的场景（图片 CDN、社交信息流），它能减少网络流量和 CDN 成本。抖音的技术团队通过将 JPEG 转为 HEIC（类似思路的格式），带宽成本降低超过 80%。

但 AVIF 的软件解码比较慢，在低端设备上可能成为瓶颈。如果应用的 minSdk 低于 31，还需要考虑软件解码兜底。常见工程做法是把 `libavif` 一类 JNI 解码库随 App 打包，在 Android 12 以下走软件解码，再按系统版本和 ABI 做能力分流。代价是包体、CPU 开销和 Native 维护成本都会上升。

### 大图解码的 OOM 风险

一张 4000×3000 的照片用 ARGB_8888 解码，内存占用 = 4000 × 3000 × 4 = 48MB。如果在列表中同时持有多个这样的 Bitmap，很快就会触发 OOM 或导致系统杀进程。

`inSampleSize` 是应对大图的标准手段。计算方法：

```java
public static int calculateInSampleSize(BitmapFactory.Options options, 
                                         int reqWidth, int reqHeight) {
    final int height = options.outHeight;
    final int width = options.outWidth;
    int inSampleSize = 1;
    if (height > reqHeight || width > reqWidth) {
        final int halfHeight = height / 2;
        final int halfWidth = width / 2;
        while ((halfHeight / inSampleSize) >= reqHeight
                && (halfWidth / inSampleSize) >= reqWidth) {
            inSampleSize *= 2;
        }
    }
    return inSampleSize;
}
```

关键原则：解码尺寸应该尽量匹配显示尺寸。如果 ImageView 只有 360×640 像素，解码一张 4000×3000 的原图就是浪费。设置 `inSampleSize = 4` 后解码为 1000×750（4.7MB），再由 GPU 缩放到 360×270 显示，内存省了 90%。

## Glide 管线架构与性能调优

Glide 是目前 Android 生态中使用最广泛的图片加载库。理解它的内部架构，才能在遇到性能问题时知道从哪里下手。

### 请求生命周期

一次完整的 Glide 加载请求经过以下阶段：

```text
Glide.with(context)
  .load(url)
  .into(imageView)

→ RequestBuilder 构建 Request
→ Engine 检查缓存
  → Active Resources（弱引用）→ 命中？返回
  → LruResourceCache（内存缓存）→ 命中？返回
  → DiskLruCacheWrapper（磁盘缓存）→ 命中？DecodeJob 解码 → 返回
  → 原始数据源（网络/文件）→ DataFetcher 获取 → DecodeJob 解码 → 返回
```

`Engine` 是整个管线的调度中心。它为每个请求创建一个 `EngineJob`（管理线程和回调），一个 `DecodeJob`（负责实际解码）。`DecodeJob` 从数据源获取原始数据后，用 `ResourceDecoder` 解码为 Bitmap，中间可以插入 `Transformation`（圆角、裁剪等），最终通过 `ResourceTranscoder` 转换为目标类型。

### 内存缓存策略

Glide 的内存缓存分为两层：

**Active Resources（活跃资源）**：用弱引用 `ResourceWeakReference` 持有当前正在使用的图片。当一个 `Resource` 的引用计数归零时，它从 Active Resources 移到 LruResourceCache。

**LruResourceCache**：LRU 策略的内存缓存。大小由 `MemorySizeCalculator` 自动计算，计算逻辑以屏幕像素数为基础：`memoryCacheScreens` 默认 2 屏 ARGB_8888 像素，`bitmapPoolScreens` 在 Android 8.0 以下为 4、8.0+ 为 1、低内存 8.0+ 可降至 0；二者总和受 `maxSizeMultiplier=0.4`（低内存时 `lowMemoryMaxSizeMultiplier=0.33`）的 `maxMemory` 百分比上限约束。生产设备上的实际值通常在 maxMemory 的 1/8 到 1/3 之间，取决于屏幕分辨率和内存等级。开发者可以在 `AppGlideModule` 中通过 `MemorySizeCalculator.Builder` 自定义这些参数。[已验证：Glide 4.16.0 `MemorySizeCalculator` 源码]

### Glide 的自动降采样

Glide 在解码时会自动根据 `ImageView` 的尺寸计算采样率。流程是：

1. 读取图片的原始尺寸（`inJustDecodeBounds = true`）
2. 获取 `ImageView` 的实际尺寸（`getWidth()` / `getHeight()`）
3. 计算 `inSampleSize`，使解码后的尺寸 ≥ `ImageView` 尺寸且最接近

这个自动降采样是 Glide 的核心价值之一——开发者不需要手动计算采样率，Glide 保证解码后的图片刚好够用，不浪费内存。

### 常见配置误区

**误区 1：禁用缓存**。`DiskCacheStrategy.NONE` 看似减少磁盘占用，但每次加载都需要重新从网络或磁盘读取原始数据并解码。对于频繁显示的图片（列表中的头像、封面），这会增加 CPU 负担和耗电。

**误区 2：错误的线程池大小**。Glide 默认的 `ExecutorService` 大小根据 CPU 核心数自动计算。手动设置过大的线程池会导致过多的并发解码，争抢 CPU 和内存带宽，反而降低帧率。

**误区 3：在 RecyclerView 中不做生命周期管理**。`Glide.with(itemView)` 会自动绑定包含该 View 的 Fragment/Activity 的生命周期，在 `onStop` 时暂停请求、`onDestroy` 时清理资源。但 RecyclerView item 回收不是 Activity/Fragment 的生命周期事件——item 出屏回收入池时，Glide 不会自动取消对应请求。正确的做法是在 `onViewRecycled(holder)` 中调用 `Glide.with(itemView).clear(imageView)` 显式释放，或者在 `onBindViewHolder` 中对同一个 `ImageView` 重新调用 `into()` 时，Glide 会替换旧请求。如果传了 `ApplicationContext`，宿主生命周期绑定也会失效，请求只能等自然完成或手动取消。[已验证：Glide `RequestManagerRetriever.get(View)` 查找宿主 Fragment/Activity；RecyclerView 回收不触发宿主生命周期回调]

## Coil 管线架构

Coil 的 API 设计以 Kotlin Coroutine 为中心，和 Compose 的结合也更自然。请求取消、超时和生命周期联动都更直接，但底层获取和解码仍然落在 Dispatcher 对应的工作线程上，不是“完全没有线程”。

### 基于 Coroutine 的请求模型

```kotlin
// Coil 的典型用法
imageView.load("https://example.com/photo.jpg") {
    crossfade(true)
    transformations(CircleCropTransformation())
    size(1080, 1920)  // 目标尺寸
}
```

一次 Coil 请求大致会经历：请求构建 → Memory Cache 查找 → Disk Cache / Fetcher 读取数据 → Decoder 解码 → Transformation（如有）→ Target 显示。

### 缓存与 Bitmap 管理要按版本看

Coil 2.x 开始移除了 `BitmapPool` 和相关 API，不再走“把旧 Bitmap 放回池里，再用 `inBitmap` 复用”的路线。主要原因有两个：一是支持 Immutable Bitmap——`inBitmap` 复用会修改 Bitmap 的内部状态，Coil 3.x 的跨平台架构（Kotlin Multiplatform）要求 Bitmap 在解码后保持不可变；二是简化内存模型，把优化重心放在尺寸控制和缓存命中上，而非运行时 Bitmap 池管理。Coil 3.x 延续了这个策略，没有把 BitmapPool 加回来。[已验证：Coil `upgrading_to_coil2.md`]

除了 BitmapPool，Coil 的磁盘缓存策略在不同版本间也有变化：

1. **Coil 1.x**：主要依赖 OkHttp `Cache`
2. **Coil 2.x**：切到自带 `DiskCache`，官方明确不建议再把 OkHttp `Cache` 当成图片磁盘缓存
3. **Coil 3.x**：继续使用自带 `DiskCache`，但缓存格式和 2.x 不兼容；升级时通常要准备清缓存。同时，3.x 把网络加载拆成独立模块，只有引入 `coil-network-okhttp` 等网络 artifact，才具备网络图片加载能力。[已验证：Coil `upgrading_to_coil2.md` / `upgrading_to_coil3.md`]

Hardware Bitmap 也不能只写成“默认开启”。Coil Android 侧的 `allowHardware` 默认值是 `true`，但如果目标 View 不是硬件加速，或者请求配置与硬件位图不兼容，Coil 会把 `Bitmap.Config.HARDWARE` 回退成 `ARGB_8888`。[已验证：Coil `imageRequests.android.kt` / `RequestService.android.kt`]

### Coil vs Glide 的选择

| 维度 | Glide 4.x | Coil 2.x / 3.x |
|------|-----------|----------------|
| 语言与 API 风格 | Java + Kotlin，历史兼容性好 | Kotlin-first，Coroutine / Compose 友好 |
| Compose 支持 | 需要额外库 | `AsyncImage` 等 API 更直接 |
| Bitmap 复用 | `LruBitmapPool` + `inBitmap` | 不提供 BitmapPool |
| 磁盘缓存 | `DiskLruCacheWrapper` | 自带 `DiskCache`，3.x 网络模块单独引入 |
| Hardware Bitmap | 按请求条件决定，必要时 `disallowHardwareConfig()` | `allowHardware(true)` 默认允许，不兼容请求会回退 |
| 适合场景 | 历史 Java 项目、定制化 `ModelLoader`、成熟插件生态 | 纯 Kotlin / Compose 项目，希望 API 更轻 |

如果项目是纯 Kotlin、使用 Compose，Coil 的接入成本更低。如果项目历史较长、有大量 Java 代码，或者已经深度依赖 Glide 的扩展点，继续用 Glide 更稳妥。

抖音的 BDFresco 框架在 Fresco 基础上做了多层优化，包括动静图缓存拆分、HEIF 软解码、按需缩放等。抖音的实验数据表明：动静图缓存拆分后，OOM 数量下降，大盘帧率上升；将不携带透明通道的图片从 ARGB_8888 降级为 RGB_565，内存占用减少近一半。这些是大型 App 在图片优化上的工程实践，思路值得借鉴。

## 在 Perfetto 中定位图片解码卡顿

### 两类耗时要分开看

图片相关 jank 常见有两段：

1. **解码阶段**：`BitmapFactory` / `ImageDecoder` 把压缩数据展开成像素
2. **首帧上传阶段**：software bitmap 第一次参与绘制时，RenderThread 把像素上传成 GPU 纹理

如果只盯主线程，容易漏掉第二段；如果只盯 RenderThread，又会把“上传慢”误判成“解码慢”。

### 主线程解码怎么找

图片解码不会自动出现在 Perfetto 里，除非 App 或图片库自己打了 trace。定位方法通常有两种：

**方法 1：自定义 Trace。** 在业务的解码包装层加 `Trace.beginSection("Bitmap.decode")` / `Trace.endSection()`，这样 `slice` 表里就会有可查询的名字。

```java
Trace.beginSection("Bitmap.decode");
Bitmap bitmap = BitmapFactory.decodeResource(res, resId, options);
Trace.endSection();
```

**方法 2：看调用栈。** 如果某一帧的主线程 CPU slice 很长，展开调用栈后看到 `BitmapFactory.nativeDecodeAsset`、`BitmapFactory.nativeDecodeStream` 或 `ImageDecoder` 相关栈帧，通常就是解码跑上主线程了。

[图：Perfetto 主线程片段。FrameTimeline 中某一帧超过预算；同一时间 MainThread 上出现 `Bitmap.decode` slice，持续 20ms 以上。标出该帧开始时间、slice 持续时间、对应的 `Choreographer#doFrame` 区间。]

### software bitmap 首帧为什么会卡

software bitmap 解码完成后，像素还在 CPU 可访问内存里。第一次绘制到屏幕时，RenderThread 还要把它上传成 GPU 纹理。AOSP 对 `Bitmap.prepareToDraw()` 的注释写得很明确，从 Android 7.0 起，这个调用会在 RenderThread 上异步触发 upload，尽量把成本挪到正常 draw path 之外。[已验证：AOSP `Bitmap.java`]

对应到分析过程，可以按这个顺序看：

`decode 完成` → `Bitmap.prepareToDraw()` 预上传，或者首帧 draw 时同步上传 → RenderThread 出现 upload / draw 开销 → FrameTimeline 出现 jank frame

Hardware Bitmap 的价值就在这里。像素本来就在 GPU 可访问内存中，渲染阶段不用再做 software bitmap 的首帧上传。

`Bitmap.prepareToDraw()` 从 Android 7.0 起就在 RenderThread 上异步触发纹理上传，公开 API 行为在 Android 17 / API 37 基准下仍成立。工程实践上，在解码完成后的工作线程或图片即将显示前调用 `prepareToDraw()` 即可预上传；不需要额外配合 `Choreographer` 的 `CALLBACK_COMMIT` 阶段——`Choreographer.postFrameCallback()` 投递的是 `CALLBACK_ANIMATION` 类型，不等于 `CALLBACK_COMMIT`。[已验证：AOSP android-17.0.0_r1 `Bitmap.java` prepareToDraw() 注释与 `Choreographer.java` 回调类型]

源码路径上，Hardware Bitmap 不能绕过 RenderNode 直接提交给 SurfaceFlinger。Hardware Bitmap 仍需经过 Display List 录制 → `syncFrameState` 同步 → `DrawFrame` 执行的完整 RenderNode 流程。优化点在于 **upload 时机的转移**：普通 Bitmap 在首帧 `syncFrameState` 期间同步 upload 纹理，而 Hardware Bitmap 在创建时已完成 GPU 内存分配，首帧无需 upload。`Bitmap.prepareToDraw()` 对 `Config.HARDWARE` 是 no-op（因为 upload 已完成）。SurfaceFlinger 的 HWC 合成决策（DEVICE Overlay vs CLIENT Composition）不受 Hardware Bitmap 影响，仍按标准 BufferQueue → validate → compose 流程执行。[已验证：AOSP android-17.0.0_r1 `Bitmap.java`、`DrawFrameTask.cpp`、`RecordingCanvas.cpp`、`SkiaGpuPipeline.cpp`]

[图：Perfetto RenderThread 片段。`Bitmap.prepareToDraw` 或首帧 `DrawFrame` 前后出现长 slice，并且能看到同一帧的 jank frame。旁边补一张使用 Hardware Bitmap 的正常帧，说明少掉了首帧 texture upload。]

### 用 Perfetto SQL 查自定义解码 slice

如果代码里已经打了 `Bitmap.decode` 这类自定义 trace，可以直接查 `slice` 表：

```sql
SELECT
  name,
  track_id,
  dur / 1000000.0 AS dur_ms,
  ts
FROM slice
WHERE name LIKE 'Bitmap.decode%'
ORDER BY dur DESC
LIMIT 50;
```

这个查询只覆盖手工标过的 slice，它不会自动识别所有 `BitmapFactory.decode*` 调用。

### StrictMode 能做什么

`StrictMode` 只能观测显式标记的慢调用。调试构建里，如果线程策略开启 `detectCustomSlowCalls()`，业务代码又在解码包装层调用了 `StrictMode.noteSlowCall("Bitmap decode on main thread")`，日志里就会出现对应告警。[已验证：AOSP `StrictMode.java`] 它不会自动把所有 `BitmapFactory.decode*` 抓出来，所以排查主线程解码，还是要靠自定义 Trace、调用栈或 benchmark。

## 优化实践总结

把这一节的内容整合成一份可执行的检查清单：

### 解码阶段

1. **匹配 ImageView 尺寸**：解码前计算 `inSampleSize`，不加载比显示尺寸大的图。Glide/Coil 自动做了这件事。
2. **选择合适的 Bitmap.Config**：不需要透明通道的图片用 `RGB_565`，省一半内存。
3. **优先用 ImageDecoder**（API 28+）：系统 API 会自动处理 EXIF 旋转。若使用 Glide 4.x 加载 Bitmap，还要先确认有没有显式打开 `setImageDecoderEnabledForBitmaps(true)`。
4. **使用 Hardware Bitmap**：只展示不修改的图片用 `Bitmap.Config.HARDWARE`，Java 堆几乎零占用。

### 内存管理

5. **利用内存复用**：减少内存分配/释放频率，降低 GC 压力。Glide 4.x 已封装 `BitmapPool` / `inBitmap`；Coil 2.x / 3.x 不再提供 BitmapPool，优化重心应放在尺寸控制、缓存命中和请求配置上。
6. **监控 fd 数量**：Hardware Bitmap 消耗 fd，大量图片场景需要关注 `/proc/<pid>/fd` 的数量。
7. **响应 onTrimMemory**：在系统内存紧张时释放图片缓存。Glide 自动做了。

### 格式选择

8. **WebP 有损替代 JPEG**：同等画质下通常能减小文件体积，但要用业务图片集确认画质、体积和解码成本。
9. **AVIF 前瞻**：带宽收益要和解码成本一起评估，硬件能力要按设备确认；minSdk 31 以下要准备软件解码兜底。
10. **避免 PNG 大图**：PNG 无损压缩，文件大、解码慢。照片类内容通常不要用 PNG。

### 工具链

11. **用 StrictMode 标记自定义慢调用**：开启 `detectCustomSlowCalls()`，并在自有解码包装层手动调用 `noteSlowCall()`；它不会自动捕获 `BitmapFactory.decode*`。
12. **自定义 Trace 标记解码**：在 `BitmapFactory.decode*` 调用前后加 `Trace.beginSection / endSection`，Perfetto 中直接可见。

---

> 验证级别：L2（基于多个独立来源交叉验证，AOSP 源码路径已标注）
>
> 主要素材来源：
> - 万字长文 Android Bitmap 相关的一切（鸿洋/杨充，2023-04-10）
> - 深入探索 Android Bitmap：从原理到实战（顾林海，2025-04-20）
> - 抖音 Android 端图片优化实践（字节跳动技术团队，2024-06-11）
> - 抖音 Android 端图片优化最佳实践（AndroidPub，2024-12-19）
> - Bitmap 内存优化：inBitmap、Bitmap Pool 与图片加载库策略（研究素材，2026-03-31）
> - Android Developers: Managing Bitmap Memory
> - Android Developers: Bitmap.Config.HARDWARE
> - Glide 官方文档
