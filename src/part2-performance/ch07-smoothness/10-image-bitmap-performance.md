---
title: 图片加载与 Bitmap 性能优化
chapter: "7.10"
section: "7.10"
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
last_verified: 2026-08-02
last_verified_against: AOSP android-17.0.0_r1
reviewed_date: 2026-07-03
reviewed_by: openclaw-task6
task6_result: pass-light-edit
confidence: medium-high
sources:
- type: research
  path: intake/research-feeds/2026-03-31-19-ch04-app-bitmap-pool-optimization.md
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/BitmapFactory.java
  ref: android-17.0.0_r1
- type: aosp
  path: frameworks/base/libs/hwui/jni/BitmapFactory.cpp
  ref: android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/Bitmap.java
  ref: android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/ImageDecoder.java
  ref: android-17.0.0_r1
- type: aosp
  path: frameworks/base/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp
  ref: android-17.0.0_r1
- type: aosp
  path: frameworks/base/graphics/java/android/graphics/Gainmap.java
  ref: android-17.0.0_r1
- type: aosp
  path: frameworks/base/libs/hwui/RecordingCanvas.cpp
  ref: android-17.0.0_r1
- type: official-doc
  path: developer.android.com/topic/performance/graphics/manage-memory
- type: official-doc
  path: developer.android.com/topic/performance/graphics/load-bitmap
- type: official-doc
  path: developer.android.com/reference/android/graphics/ImageDecoder
- type: library-doc
  path: bumptech.github.io/glide/doc/hardwarebitmaps.html
- type: library-doc
  path: coil-kt.github.io/coil/api/coil-core/coil3.request/allow-hardware.html
pipeline_stage: rework-applied-awaiting-review
task6_state: rework-applied
task9_state: rework-applied
task2b_state: fixed
task2b_result: fixed
last_rework_date: 2026-05-06
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-07-03
task6_review_notes: '2026-04-30 task6 revisiting review (post-task2b fix): pass-light-edit。task2b已修正P0 inSampleSize源码锚点+P1 Gainmap内存模型+ImageDecoder内存峰值。L1/L2全通过，无B类大问题。task9需复审。 | 2026-05-05 task6 revisiting review 07:30: pass-light-edit。清理重复 frontmatter、未标语言代码块、高频填充词和第一人称；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。 | 2026-05-06 task6 revisiting review 08:15: pass-light-edit。清理编辑痕迹、虚假引导语和中英文格式；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。 | 2026-05-06 task6 revisiting review 09:07: pass-light-edit。移除未支撑的 upload/WebP/AVIF 量化口径，清理发布稿编辑痕迹和夸张标题；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。 | 2026-05-06 task6 revisiting review 10:10: pass-light-edit。清理 frontmatter 禁用词、口语化表达、绝对化措辞和结构性引导语；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。'
last_task9_at: 2026-07-03T12:32:56+08:00
last_task9_audit: 2026-07-03
last_task9_audit_log: logs/deep-review/2026-07-03-11-audit.md
task9_review_notes: '2026-05-06 08:30 task9 deep-review: needs-rework。P0 1：inBitmap 复用示例把返回对象语义写错；P1 1：AVIF/AV1 硬件能力边界过度外推；P2 2：Hardware Bitmap upload 与 WebP 压缩率缺少数据支撑。 | 2026-05-06 08:45 task2b rework(第三轮): P0 inBitmap像素转移语义修正；P1 AVIF硬件加速边界收窄 | 2026-05-06 09:20 task9 回归审计: needs-rework。P0 1 / P1 0 / P2 1；inBitmap 复用对象语义仍未解决。 | 2026-05-06 12:42 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；AVIF fallback 实现名与 Perfetto 调用栈采集条件写入 suggestions；无 active queue pending，自动晋升 finalized。 | 2026-07-03 12 Task9 deep-review: pass-tech-review。Task6 复审后复核 BitmapFactory.cpp、Bitmap.java、Choreographer.java、DrawFrameTask.cpp、RecordingCanvas.java、SkiaGpuPipeline.cpp 的 Android 17 锚点；P0 0 / P1 0 / P2 0；queue 中 WebView 时效性条目 section 误写为 7.10，已改为 7.11，自动晋升 finalized。'
last_task6_at: 2026-07-03T12:13:55+08:00
last_task6_audit: 2026-06-28
last_task6_review_log: logs/review/2026-05-06-10-review.md
task9_result: pass-tech-review
last_task9_autofix_at: 2026-07-03
auto_promoted: true
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-03
last_task9_review_log: logs/deep-review/2026-07-03-12-deep-review.md
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 0
p0: 0
p1: 0
p2: 0
last_rework_at: 2026-08-02T21:35:34+08:00
last_rework_run_id: 20260802-213534-rework-0bd5cec4
last_rework_by: hermes-aiw-polish-rework
last_rework_reason: 'Rework lane: 清除 outline 核验占位触发词；扩充 frontmatter sources 并补正文内联来源标记，解决核验占位与来源单薄的启发式标记'
rework_summary: '2026-08-02 rework：不改变 Android 17 技术结论；将 outline 中核验占位措辞改为“后续核验”，避免误判未收敛结论；sources 增补 Gainmap、RecordingCanvas、ImageDecoder API、Glide Hardware Bitmap、Coil allowHardware，并在正文关键结论补 5 处 [来源:] 标记。'
last_idle_audit_at: 2026-08-01T10:35:29+08:00
last_idle_audit_run_id: 20260801-103529-idle-audit-0bd5cec4
last_idle_audit_result: pass-no-change
---
# 7.10 图片加载与 Bitmap 性能优化

图片性能问题很少只由“解码慢”解释。一次图片请求至少包含数据获取、格式解析、像素解码、尺寸变换、缓存交接、纹理准备和窗口绘制。任一阶段都可能消耗 CPU、内存带宽、native/graphics 内存或文件描述符；多个请求并发时，还会与主线程和 RenderThread 争用资源。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，对应 `BitmapFactory.java`、`ImageDecoder.java` 与 `Bitmap.java`。涉及旧版本的段落只用于说明像素内存位置、`inBitmap` 约束等兼容差异。图片库的默认策略不属于系统契约：Glide、Coil 的行为必须结合项目所用版本、请求参数和目标设备验证。

## 1. 先把请求拆成七段

排查图片卡顿前，先按下面的阶段记录时间和内存：

| 阶段 | 典型工作 | 常见资源压力 | 优先证据 |
|---|---|---|---|
| Fetch | 网络、磁盘、ContentProvider 读取编码数据 | I/O、网络、线程等待 | 请求监听器、网络事件、文件 I/O slice |
| Header | 识别格式、尺寸、色彩空间、动画信息 | 少量 CPU 与 I/O | `outWidth/outHeight`、`ImageInfo` |
| Decode | 压缩数据展开为像素 | CPU、native 内存、内存带宽 | 自定义 trace、CPU sample、分配曲线 |
| Resize | codec 采样或解码后的缩放 | CPU、临时像素缓冲 | 目标尺寸、采样尺寸、native 调用栈 |
| Transform | 裁剪、圆角、模糊、调色 | CPU 或 GPU、额外 Bitmap | 图片库事件、变换前后尺寸 |
| Texture preparation | software bitmap 变成 GPU 可采样资源 | RenderThread、GPU、内存带宽 | `Bitmap#prepareToDraw`、RenderThread slice |
| Window rendering | 图片绘入应用窗口 buffer，交给 SurfaceFlinger | GPU、BufferQueue、合成 | FrameTimeline、RenderThread、SurfaceFlinger |

这张表能避免两类误判：网络等待被算成解码耗时，或 software bitmap 的首绘纹理准备被算成 SurfaceFlinger 合成耗时。帧级分析方法可配合[卡顿分析方法论](./03-jank-methodology.md)，列表生命周期可配合[RecyclerView 性能章节](./08-recyclerview-performance.md)。

## 2. BitmapFactory：理解公共契约，再读实现

`BitmapFactory` 提供资源、文件、流和字节数组等入口。各入口会构造数据源并进入 native 解码路径，但资源 density、流是否可回退读取、NinePatch 和异常处理仍有差别，所以“所有入口完全相同”并不严谨。

### 2.1 `inJustDecodeBounds` 解决什么问题

`inJustDecodeBounds = true` 会让解码 API 返回 `null`，同时填写 `outWidth`、`outHeight`、`outMimeType`、`outConfig` 和 `outColorSpace` 等可用信息。它适合在正式分配输出像素前确定尺寸和配置。

把它称为“只读文件头”容易产生误解。不同容器和 codec 为得到边界信息所需读取的数据量不同；应用能够依赖的是“没有输出 Bitmap 像素分配”，不能依赖固定读取字节数。

### 2.2 `inSampleSize` 仍按 2 的幂理解

Android 17 的 `BitmapFactory.Options` 文档仍规定：大于 1 的值请求子采样，非 2 的幂会向下取到最接近的 2 的幂。`BitmapFactory.cpp` 会把 sample size 交给 `SkAndroidCodec`，但 native 实现细节没有扩大 Java API 的保证范围。

因此，业务代码应使用 1、2、4、8 等值，并根据返回的 `Bitmap.width`、`height` 复核结果。若目标尺寸要求更精确，可让图片库做 downsample，或在 API 28 及以上使用 `ImageDecoder.setTargetSize()`。不要根据某个 codec 在某台设备上接受 3，就把 3 当成跨格式约定。

下面这段代码展示“先读边界，再按 2 的幂计算采样”的最小做法：

```java
private static int powerOfTwoSample(
        int sourceWidth,
        int sourceHeight,
        int targetWidth,
        int targetHeight
) {
    int sample = 1;
    while (sourceWidth / (sample * 2) >= targetWidth
            && sourceHeight / (sample * 2) >= targetHeight) {
        sample *= 2;
    }
    return sample;
}

BitmapFactory.Options bounds = new BitmapFactory.Options();
bounds.inJustDecodeBounds = true;
BitmapFactory.decodeFile(fileName, bounds);

if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
    throw new IllegalArgumentException("Unsupported or damaged image");
}

BitmapFactory.Options decode = new BitmapFactory.Options();
decode.inSampleSize = powerOfTwoSample(
        bounds.outWidth,
        bounds.outHeight,
        targetWidth,
        targetHeight
);
Bitmap bitmap = BitmapFactory.decodeFile(fileName, decode);
```

返回尺寸可能仍大于控件尺寸，也可能受 EXIF、density 或 codec 取整影响。生产代码还要处理空返回、超大尺寸、取消请求、并发上限和方向信息；图片库通常已经覆盖其中大部分边界。

### 2.3 `inPreferredConfig` 是偏好值

`inPreferredConfig` 请求目标配置，decoder 可以因源格式或能力限制忽略它。`ARGB_8888` 适合常规 UI 和照片；`RGB_565` 只保存 16 位颜色，没有 alpha，渐变和暗部容易出现色带。它只能在内容不透明、画质验收通过且内存收益明确时启用。

用“照片没有透明通道，所以统一改成 RGB_565”会把色彩损失带进所有设备。更稳妥的决策顺序是：控制尺寸与并发，确认缓存持有量，测量峰值，再评估是否接受降色深。

### 2.4 resource density 会改变输出像素

`decodeResource()` 会根据资源 density 与目标 density 做缩放。`drawable-nodpi` 不参与 density 缩放；`drawable-mdpi`、`drawable-xxhdpi` 等目录带有密度语义。输出像素由源尺寸、采样结果和 density 缩放共同决定，内存评估应读取解码后的宽高、`rowBytes` 与 `allocationByteCount`。

Android 17 的 `BitmapFactory.cpp` 在 density scale 不为 1 时会先解码采样尺寸，再分配目标 Bitmap 做缩放。输出 Bitmap 之外还可能存在临时软件缓冲。只用“目标宽 × 目标高 × 4”评估解码峰值会低估风险。

## 3. ImageDecoder：API 28 以上的尺寸与分配控制

`ImageDecoder` 将 Source、header callback、尺寸、裁剪、色彩空间、allocator 和动画解码放进一套 API。`decodeBitmap` 返回静态 Bitmap，`decodeDrawable` 可返回 `AnimatedImageDrawable`。EXIF 方向也由解码流程处理。

### 3.1 `setTargetSize` 与 `setTargetSampleSize`

两者都必须在 `OnHeaderDecodedListener` 中设置，且二者只有末次调用生效：

- `setTargetSize(width, height)` 请求任意输出尺寸，可放大或缩小。codec 可以采样，也可以增加内部缩放步骤。
- `setTargetSampleSize(sampleSize)` 按采样率计算目标尺寸，并允许 decoder 向更高效的方向取整。
- 任一方法都不能保证“完全没有中间缓冲”。格式、裁剪、色彩转换、allocator 和 codec 能力都会影响峰值。

下面的例子按容器上限等比缩小，并让默认 allocator 自行选择兼容的 backing：

```java
Bitmap bitmap = ImageDecoder.decodeBitmap(source, (decoder, info, ignored) -> {
    Size sourceSize = info.getSize();
    float scale = Math.min(
            (float) maxWidth / sourceSize.getWidth(),
            (float) maxHeight / sourceSize.getHeight()
    );
    scale = Math.min(scale, 1.0f);

    int width = Math.max(1, Math.round(sourceSize.getWidth() * scale));
    int height = Math.max(1, Math.round(sourceSize.getHeight() * scale));
    decoder.setTargetSize(width, height);
    decoder.setAllocator(ImageDecoder.ALLOCATOR_DEFAULT);
});
```

`ALLOCATOR_DEFAULT` 通常倾向 Hardware Bitmap，小图或不兼容选项可得到 software bitmap。调用方若必须读写像素，应明确选择 `ALLOCATOR_SOFTWARE`。

### 3.2 Hardware allocator 的异常边界

`ALLOCATOR_HARDWARE` 表示强制 Hardware Bitmap。它与 `setMutableRequired(true)` 或 `setDecodeAsAlphaMaskEnabled(true)` 组合时，Android 17 会在解码前抛出 `IllegalStateException`。这与 `ALLOCATOR_DEFAULT` 的兼容性回退语义不同。

动画 drawable 会忽略 allocator。后处理、未预乘 alpha、裁剪和色彩空间还会改变解码路径；调用方不应只凭 allocator 常量推算内存或时延。

## 4. Bitmap 像素内存的版本变化

Bitmap 的 Java 对象一直由 managed heap 持有，像素 backing 的位置经历过三段变化：

| 版本 | 像素数据位置 | 工程含义 |
|---|---|---|
| Android 2.3.3 / API 10 及以下 | native memory | 像素释放曾需更谨慎地配合 `recycle()` |
| Android 3.0–7.1 / API 11–25 | managed heap | 像素直接增加 Java 堆占用 |
| Android 8.0–17 / API 26–37 | native memory | Java 堆下降不代表进程图片内存下降 |

Android 17 的 `Bitmap.java` 使用两个 `NativeAllocationRegistry` 登记 native 对象和像素大小：一个注册释放函数，另一个用 no-op free function 更新像素分配的内存压力。ART 不会扫描 native 像素内容；Java Bitmap 的可达性、registry 登记和 native 引用共同决定生命周期。

观察内存时至少区分 Java Heap、Native Heap、Graphics、共享页和进程 PSS。`Runtime.maxMemory()` 不能描述 HardwareBuffer 或 graphics 驱动侧占用，`dumpsys meminfo <package>`、Perfetto memory counters、heapprofd 与 GPU 厂商节点各自只覆盖一部分。

### 4.1 软件配置的估算与实测

| Config | 名义字节/像素 | alpha | 使用边界 |
|---|---:|---|---|
| `ALPHA_8` | 1 | 只保存 alpha | mask |
| `RGB_565` | 2 | 无 | 可接受色带的完全不透明内容 |
| `ARGB_8888` | 4 | 有 | 常规 UI 与照片 |
| `RGBA_F16` | 8 | 有 | 宽色域或高精度处理 |
| `HARDWARE` | 不用固定 B/px 推算 | 取决于内部格式 | GPU 可采样、不可变的展示资源 |

软件 Bitmap 的 `rowBytes × height` 比 `width × height × 名义 B/px` 更接近像素存储量；`getAllocationByteCount()` 反映底层分配容量，复用后可能大于当前内容的 `getByteCount()`。对 Hardware Bitmap，内部像素格式、stride、压缩和驱动分配方式都可能变化，应用层的 `Config.HARDWARE` 无法给出统一字节数。

## 5. Ultra HDR 与 Gainmap

Android 14 起的 Ultra HDR 图片可以在 SDR base image 之外携带 gainmap。Android 17 的 `BitmapFactory.cpp` 会通过 codec 取得 gainmap，解码成独立 Bitmap 并附到 base Bitmap；Hardware Bitmap 路径还会为 gainmap 创建对应的 hardware backing。`Gainmap.java` 保存 gainmap contents Bitmap 与显示参数。

因此，Ultra HDR 的持有成本至少要考虑：

- base Bitmap 的分辨率、配置和 stride；
- gainmap Bitmap 的分辨率、配置和 stride；
- 解码与缩放期间的临时缓冲；
- software 或 hardware backing；
- 图片库、Drawable 与 UI 对两层对象的引用时间。

不存在可靠的固定 1.25 倍或 2 倍公式。`Bitmap.getAllocationByteCount()` 只描述当前 Bitmap 的 backing，不能自动代表附着 gainmap 及所有 graphics 分配。应在目标设备上同时记录 base/gainmap 属性与进程 Graphics、Native Heap、PSS 的变化。

`bitmap.setGainmap(null)` 会把 gainmap 从 base Bitmap 上移除。只有其他 Java/native 引用也结束后，对应资源才具备释放条件。是否移除还涉及 HDR 产品效果、显示能力和色彩一致性，不能作为低端机的无条件开关。

## 6. Hardware Bitmap 的收益与边界

`Bitmap.Config.HARDWARE` 在 API 26 引入。它以 HardwareBuffer/GraphicBuffer 一类 GPU 可访问 backing 保存像素，Bitmap 保持不可变。把它说成“像素只在独立显存里”不适用于统一内存架构，也会漏掉句柄、页表、导入对象和驱动记账。

### 6.1 它省掉哪段工作

software bitmap 解码后保留 CPU 可访问像素。HWUI 首次把它当作纹理使用时，需要创建或更新 GPU 资源。Android 17 的 `SkiaGpuPipeline::prepareToDraw()` 只对 `!bitmap->isHardware()` 调用 `PinAsTexture`、`UnpinTexture` 和 `flushAndSubmit`；Hardware Bitmap 跳过这条 software texture preparation 路径。

这项收益不等于“图片绕过 RenderThread”。应用仍在 DisplayList 中记录 drawBitmap，RenderThread 仍把图片采样并绘入应用窗口 buffer，随后通过 BufferQueue 交给 SurfaceFlinger。普通 ImageView 中的一张 Bitmap 通常不会成为独立 SurfaceFlinger layer。

Hardware Bitmap 参与绘制时仍有 HardwareBuffer 导入、同步、GPU 采样和窗口提交成本。收益大小要看图片是否重复显示、software 纹理是否已缓存、上传时机、GPU 驱动和内存带宽。

### 6.2 CPU 访问与可变性

Hardware Bitmap 不支持 `getPixel()`、`getPixels()`、`copyPixelsToBuffer()` 等直接像素访问，也不能作为可变 Bitmap 使用。复制、序列化或某些比较路径可能触发 GPU readback，`Bitmap.java` 会对部分操作调用 `StrictMode.noteSlowCall()`。

以下需求应选择 software bitmap：

- 软件 Canvas 需要把它作为绘制目标；
- Palette、像素采样、JNI 像素处理或自定义滤镜需要 CPU 访问；
- 变换实现要求可变输出；
- 目标 View 或渲染路径未启用硬件加速；
- 测试发现设备/驱动的 HardwareBuffer 成本更高。

圆角、裁剪和共享元素过渡本身不足以判定配置。图片库可能用 GPU、生成新的 software bitmap，或因请求条件禁用 Hardware Bitmap；要检查所用 transformation 与 target 的实现。

### 6.3 fd 成本要按设备测量

HardwareBuffer 及其跨进程/驱动句柄可能占用文件描述符。Glide 会检查进程 fd 数量并在接近内部阈值时停止使用 Hardware Bitmap，但阈值与策略属于库实现，不属于 Android API 契约。

图库、瀑布流或大缓存场景可采集 `/proc/self/fd` 数量、`RLIMIT_NOFILE`、图片缓存条目数和 Hardware Bitmap 数量。fd 上升若与图片释放不同步，再检查 Drawable、Target、缓存和转场是否延长了资源生命周期。

### 6.4 `prepareToDraw()` 的准确含义

`Bitmap.prepareToDraw()` 会把 software bitmap 的更新/上传工作移到常规 draw path 之外。Android 17 的 Ganesh 路径在 RenderThread 取得图像、pin 为纹理并 `flushAndSubmit()`；对 Hardware Bitmap 是空操作。

它能提前提交纹理准备，但不承诺调用返回时 GPU 已完成全部工作，也不保证首帧没有同步等待。若图片库已负责预绘制，业务层重复调用可能没有收益。应以 RenderThread trace 和首帧时延验证。

## 7. `inBitmap` 与 BitmapPool

### 7.1 Android 17 的复用条件与对象语义

API 19 及以上，`BitmapFactory` 可以尝试复用一个可变 Bitmap，只要新解码结果所需字节数不超过旧 Bitmap 的 `getAllocationByteCount()`。Hardware Bitmap 始终不可变，不能作为 `inBitmap`。API 19 之前还要求 JPEG/PNG、相同尺寸且 `inSampleSize = 1`。

Android 17 native 流程在复用成功时调用 `bitmap::reinitBitmap()` 更新同一个 Java Bitmap 的宽高和配置，然后返回传入的 `javaBitmap`。调用方仍应只使用 decode 返回值，因为公共文档要求不能假设每次都复用成功；无效复用可能以 `IllegalArgumentException` 结束。

下面的代码展示了复用时必须遵守的引用规则：

```java
BitmapFactory.Options options = new BitmapFactory.Options();
options.inMutable = true;
options.inBitmap = candidate;

Bitmap decoded;
try {
    decoded = BitmapFactory.decodeStream(input, null, options);
} catch (IllegalArgumentException reuseFailed) {
    options.inBitmap = null;
    decoded = BitmapFactory.decodeStream(reopenedInput, null, options);
}

if (decoded == null) {
    throw new IOException("Image decode failed");
}
candidate = decoded;
```

输入流通常不能直接重放，复用失败后的重试需要重新打开数据源。成功后 `candidate` 的旧尺寸和旧内容都已失效，持有旧语义的其他引用会产生数据错误。

### 7.2 BitmapPool 是复用池，不是内容缓存

BitmapPool 保存可供下一次解码或变换覆盖的空闲像素 backing；内存缓存保存仍能按 key 返回给 UI 的图片资源。二者目的和生命周期不同：

- 内容缓存命中可以省掉 fetch、decode 和 transformation；
- BitmapPool 命中主要减少新像素分配和碎片；
- 池过大会挤压内容缓存与业务内存；
- 资源仍在显示或被引用时，不能放回池中覆盖。

Glide 4 使用 `LruBitmapPool` 配合 `inBitmap`。使用 Glide 管理的 Bitmap 时，应用不能手动 `recycle()`，也不能在请求 clear 或资源释放后继续持有底层 Bitmap。否则池可能把同一 backing 分配给另一请求。

Coil 从 2.x 移除了 BitmapPool，Coil 3 延续该设计。使用 Coil 时应把精力放在目标尺寸、请求去重、内存/磁盘缓存和并发量，避免照搬 Glide 的池参数。

## 8. Glide 与 Coil：先确认请求生命周期

### 8.1 Glide 的缓存查找顺序

Glide 官方文档把一次请求的查找路径描述为：

1. Active Resources；
2. Memory Cache；
3. Resource Disk Cache；
4. Data Disk Cache；
5. 原始数据源。

Resource Disk Cache 保存已解码、变换后的资源，Data Disk Cache 保存原始或转换后的编码数据。BitmapPool 不在这条内容缓存链中。排查“为什么又解码”时，要同时记录 model、signature、尺寸、transformation、options、resource class 和缓存策略；任一 key 维度变化都可能导致未命中。

`into(imageView)` 会替换该 target 上旧的 Glide 请求。View 明确结束使用时可调用 `clear()`；在 RecyclerView 中，重新 bind 同一 ImageView 通常会替换旧请求，复杂 target 或预加载仍要按生命周期清理。资源交还 Glide 后不得继续保留或手工 recycle。

Glide 根据 Target 尺寸参与 downsample，但不能承诺输出“刚好等于控件像素”。ScaleType、override、transformation、codec 采样和磁盘缓存资源都会影响结果。定位内存异常时应记录请求尺寸与最终 Bitmap 尺寸。

### 8.2 Coil 3 的共享 ImageLoader

Coil 3 的 `ImageLoader` 持有内存缓存、磁盘缓存、网络客户端和组件注册表。应用通常应共享一个配置好的实例；每个页面创建 ImageLoader 会复制缓存和连接资源。

Coil 3 的网络功能位于独立 artifact，例如 `coil-network-okhttp`。`allowHardware(false)` 用于请求 CPU 可访问的 Bitmap；在 Android 上，HARDWARE 请求被禁用或不兼容时会选择 software 配置。Coil 2/3 没有 BitmapPool，看到“池命中率”指标时应先确认它来自业务层还是其他组件。

Glide 与 Coil 的选择不应只看 API 风格。已有缓存 key 体系、自定义 fetcher/decoder、Compose 集成、动画格式、监控接口、包体和升级成本都要纳入评估。性能结论应来自相同图片集、相同尺寸和相同缓存冷热状态的对照测试。

## 9. 格式选择：编码体积与解码成本分开测

编码文件大小无法推导 Bitmap 分配。4000×3000 的 JPEG、WebP 或 AVIF 即使文件体积差很多，解码到相同尺寸和软件配置后，输出像素量仍接近；差异主要出现在下载、解析、codec CPU、临时缓冲、色彩转换和动画帧管理。

| 格式 | 主要特性 | 评估重点 |
|---|---|---|
| JPEG | 照片常用、有损、无 alpha | 质量、体积、EXIF、渐进式支持 |
| PNG | 无损、支持 alpha | 内容类型、体积、解码 CPU；UI 图与照片分开测 |
| WebP | 有损/无损/alpha/动画 | 系统版本、编码参数、画质与解码时延 |
| AVIF | 高压缩潜力、HDR/alpha 能力 | 设备覆盖、codec 路径、CPU、功耗、兼容回退 |
| HEIF/HEIC | 高压缩潜力、容器能力 | 平台支持、专利/服务端链路、解码路径 |
| GIF | 兼容广、颜色和压缩受限 | 帧数、帧尺寸、disposal、动画内存 |

Android 12 / API 31 加入 AVIF 支持。Android 17 的 `ImageDecoder.isMimeTypeSupported("image/avif")` 会检查平台能力，但 AV1 视频硬件能力不能直接证明静态 AVIF 的某次解码走硬件。应用若关心硬件或软件路径，需要在目标 SoC、系统镜像和输入样本上采集 codec、CPU 与功耗证据。

格式对照测试至少固定以下变量：源图片集、输出像素尺寸、色彩空间、质量目标、冷/热缓存、线程数、设备温度和系统版本。记录编码体积、P50/P95 解码时间、峰值 PSS/native/graphics、能耗以及视觉质量。不要用单张图给所有资源定格式规则。

## 10. 大图与 OOM：看峰值和并发

`width × height × 4` 只适合估算紧凑 `ARGB_8888` 输出。更完整的预算包含：

`峰值 ≈ 输出 backing + codec 临时缓冲 + resize/transform 输出 + gainmap + 同时在途请求 + 缓存新增量`

一张 4000×3000 的紧凑 ARGB_8888 输出约 48,000,000 字节，约 45.8 MiB；row stride、色彩配置和附加层还会改变数值。若列表同时解码四张，风险来自并发峰值，单张图成功不能证明方案安全。

工程控制项包括：

- 在拿到目标 View/Compose constraints 后再确定请求尺寸；
- 对预取与解码设置并发上限，低内存设备单独测量；
- 变换链尽量复用输出，避免连续保留多个全尺寸中间 Bitmap；
- 超大图缩放查看时使用区域解码或分块方案；
- 页面退出、target 替换与请求取消要结束 fetch/decode 和引用；
- 缓存预算与页面业务对象共享同一进程内存，而非独立额度；
- 用 `onTrimMemory` 调整缓存，但不要依赖它挽救已经过高的瞬时分配。

OOM 排查要保留输入尺寸、目标尺寸、配置、并发数、缓存状态、gainmap、有无 transformation 和失败前内存快照。只记录“加载某 URL 时 OOM”不足以复现。

## 11. 用 Perfetto 区分 decode、upload 与 present

### 11.1 建立可关联的业务 slice

框架不会为每个图片库请求自动生成可读的 URL/业务名 slice。可在自有解码边界或图片库 listener 中加入短、稳定且不含隐私的 trace 名称。

下面的包装保证异常时也会闭合 trace：

```java
Trace.beginSection("ImageDecode:feed_thumbnail");
try {
    return BitmapFactory.decodeStream(input, null, options);
} finally {
    Trace.endSection();
}
```

这段 slice 只覆盖被包装的同步调用。网络、排队、异步回调、图片库内部变换和纹理准备应分别标记，避免用一个长 slice 混合多类等待。

### 11.2 一帧一帧对齐证据

定位某个 jank frame 时，按时间轴检查：

1. FrameTimeline 中 app frame 的 deadline、present type 与 jank tag；
2. 主线程是否在 decode、资源读取、Bitmap 变换或回调中消耗 CPU；
3. 图片库 worker 是否出现长 decode，同时与主线程争用大核或内存带宽；
4. RenderThread 是否在图片首次绘制附近出现 `Bitmap#prepareToDraw`、纹理创建、upload 或长 `DrawFrame`；
5. 应用 buffer 是否按时 queue，SurfaceFlinger/HWC 是否另有合成延迟；
6. 同一时段是否有 GC、native 内存增长、页错误或 thermal/cpufreq 变化。

CPU sampling 或 heapprofd 需要在 trace 配置中显式启用。普通 system trace slice 不能自动提供完整 native 调用栈。采样率也会影响短解码函数是否被捕获。

### 11.3 查询自定义 slice

下面的 SQL 用于列出业务已经打标的图片阶段，并按耗时排序：

```sql
SELECT
  s.name,
  s.ts,
  s.dur / 1e6 AS dur_ms,
  t.name AS thread_name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
WHERE s.name GLOB 'ImageDecode:*'
ORDER BY s.dur DESC
LIMIT 50;
```

查询结果只能证明对应 slice 的墙钟持续时间。若要区分 CPU 运行、锁等待和 I/O，需要继续关联 thread state、sched 与采样调用栈。

### 11.4 StrictMode 的作用有限

`detectCustomSlowCalls()` 只会报告应用主动调用 `StrictMode.noteSlowCall()` 的位置。它不会自动拦截全部 `BitmapFactory.decode*`。它适合在 debug 构建中防止自有同步解码回到主线程，不能替代 Perfetto、benchmark 或图片库监控。

## 12. 可执行检查清单

### 尺寸与解码

- [ ] 记录编码尺寸、EXIF 方向、目标像素尺寸与最终 Bitmap 尺寸。
- [ ] `BitmapFactory` 的 `inSampleSize` 使用 2 的幂，并检查返回尺寸。
- [ ] `ImageDecoder` 的 target 设置在 header callback 内；区分 DEFAULT 与强制 HARDWARE。
- [ ] resource 图片确认 density 目录，避免意外放大。
- [ ] 统计 decode、resize、transform 各自耗时和临时内存。
- [ ] 对异常尺寸、损坏文件、取消请求和复用失败有明确处理。

### 内存与生命周期

- [ ] 使用 `rowBytes`、`allocationByteCount` 和最终配置核算 software bitmap。
- [ ] Ultra HDR 同时核算 base、gainmap 和解码临时缓冲。
- [ ] 记录在途请求数、缓存新增量和页面退出后的资源下降。
- [ ] Glide 资源交还后不再持有，不手动 recycle。
- [ ] Coil 共享 ImageLoader，确认 memory/disk cache 配置。
- [ ] 低内存回调与缓存缩减策略经过设备测试。

### Hardware Bitmap

- [ ] 只有 CPU 像素访问、软件 Canvas 或可变输出需求明确时才禁用。
- [ ] 观察 graphics/native/PSS 与 fd，避免只看 Java Heap。
- [ ] 验证首绘 RenderThread 成本，确认 Hardware Bitmap 或 `prepareToDraw()` 有可测收益。
- [ ] 检查目标 View 硬件加速、transformation 和图片库版本的兼容行为。
- [ ] Hardware Bitmap 不被描述为独立 SurfaceFlinger layer 或固定 4 B/px。

### 格式与基准

- [ ] JPEG、PNG、WebP、AVIF 使用同一业务图片集对照。
- [ ] 固定输出尺寸、画质目标、缓存状态、线程数和温度。
- [ ] 同时记录体积、P50/P95 decode、峰值内存、功耗和视觉质量。
- [ ] AVIF 硬件路径按设备与输入验证，不从 AV1 视频能力推断。
- [ ] 动图记录帧数、帧尺寸、缓存帧策略与页面可见性。

### Perfetto

- [ ] fetch、decode、transform、texture preparation 使用不同 trace 名称。
- [ ] FrameTimeline 与 Main、worker、RenderThread、SurfaceFlinger 同时对齐。
- [ ] 需要调用栈时启用 CPU sampling；需要 native 分配时配置 heapprofd。
- [ ] 用 thread state 区分运行、I/O、锁等待和调度延迟。
- [ ] 结论附带 trace 时间段、设备、构建、输入和请求配置。

## 13. Android 17 源码锚点

以下路径均以 `android-17.0.0_r1` 为准：

- [`BitmapFactory.Options` 公共契约与 `inBitmap` 约束](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/BitmapFactory.java)
- [`BitmapFactory.cpp` 解码、density scale、复用、Hardware Bitmap 与 gainmap](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/jni/BitmapFactory.cpp)
- [`Bitmap.java` native allocation、像素访问、Gainmap 与 `prepareToDraw`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/Bitmap.java)
- [`ImageDecoder.java` target size、allocator 与兼容性检查](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/ImageDecoder.java)
- [`Gainmap.java` contents Bitmap 与参数对象](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/graphics/java/android/graphics/Gainmap.java)
- [`SkiaGpuPipeline.cpp` 的 software texture preparation](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/pipeline/skia/SkiaGpuPipeline.cpp)
- [`RecordingCanvas.cpp` 的 Bitmap/Gainmap 绘制入口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/libs/hwui/RecordingCanvas.cpp)

配套官方资料：

- [Android Developers：Managing bitmap memory](https://developer.android.com/topic/performance/graphics/manage-memory)
- [Android Developers：Loading large bitmaps efficiently](https://developer.android.com/topic/performance/graphics/load-bitmap)
- [Android Developers：ImageDecoder API](https://developer.android.com/reference/android/graphics/ImageDecoder)
- [Glide：Caching](https://bumptech.github.io/glide/doc/caching.html)
- [Glide：Resource reuse](https://bumptech.github.io/glide/doc/resourcereuse.html)
- [Glide：Hardware Bitmaps](https://bumptech.github.io/glide/doc/hardwarebitmaps.html)
- [Glide：Targets](https://bumptech.github.io/glide/doc/targets.html)
- [Coil：ImageLoaders](https://coil-kt.github.io/coil/image_loaders/)
- [Coil：Network images](https://coil-kt.github.io/coil/network/)
- [Coil：Upgrading to Coil 2](https://coil-kt.github.io/coil/upgrading_to_coil2/)
- [Coil：`allowHardware`](https://coil-kt.github.io/coil/api/coil-core/coil3.request/allow-hardware.html)
