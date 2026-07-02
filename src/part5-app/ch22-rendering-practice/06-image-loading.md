---
title: "图片加载与显示优化"
chapter: "22.6"
section: "22.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-02"
last_verified_against: "AOSP android-17.0.0_r1, Android Developers docs, Glide/Coil docs, Clippings 结构参考"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 资源文件的体积优化实战.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/Bitmap.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapFactory.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/BitmapRegionDecoder.java"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/ImageDecoder.java"
  - type: official
    path: "https://developer.android.com/topic/performance/graphics/manage-memory"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/reduce-image-sizes"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/BitmapFactory.Options"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/BitmapRegionDecoder"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/ImageDecoder"
  - type: library-doc
    path: "https://bumptech.github.io/glide/doc/caching.html"
  - type: library-doc
    path: "https://bumptech.github.io/glide/doc/resourcereuse.html"
  - type: library-doc
    path: "https://coil-kt.github.io/coil/"
  - type: library-doc
    path: "https://coil-kt.github.io/coil/image_loaders/"
tags: [image-loading, glide, coil, bitmap-decode, image-cache]
related_chapters: ["22.1", "23.2", "7.10"]
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task9_state: "reviewed"
task2b_state: "fixed"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-13"
task6_reviewed_date: "2026-05-13"
task6_result: pass-light-edit
last_task6_at: "2026-05-13T09:12:00+08:00"
last_task6_audit: "2026-06-09"
last_task6_review_log: "logs/review/2026-05-13-09-review.md"
task6_review_notes: "2026-05-13 Task6：L1/L2 轻修（术语、指标中文化、兜底表述）；四层质检通过，无新增回炉项，转入 Task9。"
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-05-19'
last_task9_at: "2026-07-02T15:26:14+08:00"
last_task9_audit: "2026-07-02"
last_task9_audit_log: "logs/deep-review/2026-07-02-15-audit.md"
last_task9_autofix_at: "2026-07-02"
last_task9_review_log: "logs/deep-review/2026-05-19-07-deep-review.md"
task9_review_notes: "2026-07-02 Task9 闲时抽检：复核 Android 17 源码路径与 BitmapRegionDecoder 格式版本差异；auto-fix Android 17 锚点和区域解码 AVIF 版本边界，回到 Task6 复审。"
task2b_result: "fixed"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-29
---

# 图片加载与显示优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Glide / Coil 图片加载框架性能对比
- 🔹 图片解码与缩放策略
- 🔹 大图加载与区域解码（BitmapRegionDecoder）
- 🔹 图片缓存策略（内存 / 磁盘 / 网络）

### 扩展（可选深入）

- 🔸 AVIF / WebP 格式选型与兼容性

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解图片加载与显示优化

图片优化要同时看三件事：解码成本、像素内存、展示时机。列表页滑动卡顿、详情页首屏慢、低端机 OOM，很多时候都不是网络慢，而是图片在错误尺寸、错误线程、错误缓存层里反复解码。

Part 5 的图片优化只讲应用侧动作。渲染管线和帧调度机制详见 22.1、7.10；Bitmap 与 Native 内存统计详见 23.2。本节把图片从 URL 或资源文件进入屏幕前的几道关口拆开：选框架、控解码、管大图、设缓存、定格式。

## Glide / Coil 图片加载框架性能对比

Glide 和 Coil 的差异不适合用单次基准测试排名。图片加载框架的性能取决于 UI 栈、请求生命周期、缓存命中率、解码尺寸和列表复用方式。工程选型时先看业务形态，再看 API 偏好。[已验证: Glide docs, bumptech.github.io/glide/][已验证: Coil docs, coil-kt.github.io]

| 维度 | Glide | Coil | 选型判断 |
| --- | --- | --- | --- |
| UI 栈 | View / RecyclerView 场景积累更久，`Glide.with(fragmentOrView)` 会绑定生命周期 | Kotlin-first，`AsyncImage` / `rememberAsyncImagePainter` 与 Compose 结合更自然 | 传统 View 列表优先 Glide；Compose 页面优先 Coil |
| 缓存模型 | 默认检查 active resources、memory cache、resource disk cache、data disk cache | 单个 `ImageLoader` 持有 memory cache、disk cache、网络客户端 | 团队要避免每个页面创建独立 loader，否则缓存会被拆散 |
| 复用能力 | `BitmapPool` 与资源引用计数做得细，适合高频列表滚动 | 依赖内存缓存、磁盘缓存、下采样和请求取消，配置面较薄 | 大量图片瀑布流更看重资源池和列表复用纪律 |
| 依赖与语言 | Java API 友好，迁移历史项目成本低 | Kotlin、Coroutines、Okio 依赖少，R8 友好 | Kotlin/Compose 新项目用 Coil 的认知成本低 |
| 风险点 | Target 复用、手动持有 Bitmap、Transformation 内 recycle 都可能破坏资源复用 | 多个 `ImageLoader`、Subcompose 过度使用、手写缓存重复 | 框架本身不是瓶颈，错误使用会制造额外解码和内存峰值 |

Glide 文档明确列出多层缓存：active resources、memory cache、resource disk cache、data disk cache。Coil 文档建议全 App 共享一个 `ImageLoader`，因为每个 `ImageLoader` 都有自己的内存缓存、磁盘缓存和网络客户端。[已验证: Glide caching docs][已验证: Coil Image Loaders docs]

工程上可以按下面的规则做初始配置：

- View / RecyclerView：`Glide.with(view)` 或 `Glide.with(fragment)`，不要用 Application Context 代替页面生命周期；列表复用时在 `onViewRecycled()` 清理请求，避免旧请求回写到新 item。[已验证: Glide resource reuse docs]
- Compose：优先用 Coil 的 `AsyncImage`，固定 `model` 的 cache key，列表里减少 `SubcomposeAsyncImage` 的使用范围。Coil 文档说明 `SubcomposeAsyncImage` 依赖 subcomposition，适合需要状态 slot 的位置，不适合在大列表里无差别使用。[已验证: Coil Compose docs]
- 混合工程：框架允许并存，但同一页面不要混用两套图片加载器。否则内存缓存、磁盘缓存和网络连接池都会重复。

## 图片解码与缩放策略

图片解码的目标不是“把图片加载出来”，而是在显示前把像素数量压到接近目标 View 尺寸。一个 4000 × 3000 的 ARGB_8888 Bitmap 约占 45.8 MB；如果屏幕上只显示 1000 × 750，原图解码会浪费 15 倍以上的像素内存。

AOSP `Bitmap.java` 暴露 `getAllocationByteCount()`，`BitmapFactory.Options` 暴露 `inSampleSize`、`inBitmap`、`inDensity`、`inTargetDensity` 等控制点。Android 8.0 之后 Bitmap 像素内存主要计入 Native 侧，Java 对象被回收后，`NativeAllocationRegistry` 负责配合释放 Native 分配。[已验证: AOSP android-17.0.0_r1, frameworks/base/graphics/java/android/graphics/Bitmap.java][结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

这段代码只演示解码前的尺寸决策，重点看 `inJustDecodeBounds` 和 `inSampleSize` 的配合：

```kotlin
fun decodeScaled(path: String, reqWidth: Int, reqHeight: Int): Bitmap {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(path, bounds)

    val sample = calculateInSampleSize(bounds.outWidth, bounds.outHeight, reqWidth, reqHeight)
    val opts = BitmapFactory.Options().apply {
        inSampleSize = sample
        inPreferredConfig = Bitmap.Config.ARGB_8888
    }
    return requireNotNull(BitmapFactory.decodeFile(path, opts))
}

fun calculateInSampleSize(srcWidth: Int, srcHeight: Int, reqWidth: Int, reqHeight: Int): Int {
    var sample = 1
    var halfWidth = srcWidth / 2
    var halfHeight = srcHeight / 2
    while (halfWidth / sample >= reqWidth && halfHeight / sample >= reqHeight) {
        sample *= 2
    }
    return sample.coerceAtLeast(1)
}
```

`inSampleSize > 1` 会请求解码器对原图做子采样，返回更小的 Bitmap。Android 官方文档给出的语义是节省内存；AOSP `BitmapFactory.java` 里也把 `inSampleSize` 与复用 Bitmap 的约束写在同一组选项里。[已验证: 官方文档, BitmapFactory.Options][已验证: AOSP android-17.0.0_r1, BitmapFactory.java]

API 28 之后的新代码可优先使用 `ImageDecoder`。它支持在 `OnHeaderDecodedListener` 里设置目标尺寸、采样尺寸、目标色彩空间和部分图片回调，适合把“读 header → 决定目标尺寸 → 解码”放在一个闭合流程里。[已验证: 官方文档, ImageDecoder]

这段代码只展示 `ImageDecoder` 的目标尺寸控制，网络、缓存和异常处理交给图片加载框架：

```kotlin
@RequiresApi(Build.VERSION_CODES.P)
fun decodeWithImageDecoder(source: ImageDecoder.Source, reqWidth: Int, reqHeight: Int): Bitmap {
    return ImageDecoder.decodeBitmap(source) { decoder, info, _ ->
        val srcWidth = info.size.width
        val srcHeight = info.size.height
        val scale = minOf(reqWidth.toFloat() / srcWidth, reqHeight.toFloat() / srcHeight, 1f)
        decoder.setTargetSize((srcWidth * scale).toInt(), (srcHeight * scale).toInt())
        decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
    }
}
```

`ALLOCATOR_SOFTWARE` 会让结果以普通 Bitmap 形式返回，便于后续处理；如果只做展示，交给 Glide / Coil 处理硬件位图会更稳，页面不要在拿到结果后继续手动修改 Bitmap。

解码策略落到业务里，可以按四条检查：

- 列表缩略图只解到 item 尺寸，详情页再请求更高规格图，不让缩略图承载详情图质量。
- 图片服务端返回宽高和格式，客户端在发请求前就能决定 `override()` / `size()`，不要等下载完成后再裁。
- `RGB_565` 只适合无透明度、无高质量渐变要求的场景；头像、插画、暗色渐变图降低位深后容易出现色带（banding）。
- `inBitmap` 复用要交给框架或统一池管理。Android 官方文档说明 API 19 前复用限制更严，现代业务仍要防止把仍在展示的 Bitmap 放回复用池。[已验证: 官方文档, Managing Bitmap Memory]

## 大图加载与区域解码（BitmapRegionDecoder）

长图、地图、超高分辨率海报不能一次解成完整 Bitmap。大图方案应按 tile 组织：视口移动到哪里，就解码哪一块；离开视口的 tile 释放或降级到缓存。`BitmapRegionDecoder.decodeRegion(rect, options)` 就是平台提供的区域解码入口。[已验证: 官方文档, BitmapRegionDecoder]

区域解码的工作流如下：

1. 读取图片 header，拿到原始宽高。
2. 按屏幕缩放级别和 tile size 计算当前可见区域。
3. 用 `decodeRegion()` 只解码可见矩形。
4. 滑动或缩放时取消过期 tile 请求，保留邻近区域做预取。
5. 内存紧张时优先释放离视口最远的 tile。

这段代码只说明 tile 解码的边界，生产代码还要加请求取消、线程调度和 tile 缓存：

```kotlin
fun decodeTile(
    decoder: BitmapRegionDecoder,
    visibleRect: Rect,
    sampleSize: Int,
    reusable: Bitmap? = null,
): Bitmap {
    val options = BitmapFactory.Options().apply {
        inSampleSize = sampleSize.coerceAtLeast(1)
        inPreferredConfig = Bitmap.Config.ARGB_8888
        inBitmap = reusable
    }
    return decoder.decodeRegion(visibleRect, options)
}
```

官方文档说明 `BitmapRegionDecoder` 适合“原图很大但只需要其中一部分”的场景。Android 17 源码中 `BitmapRegionDecoder` 列出的格式为 JPEG、PNG、WebP、HEIF 和 AVIF；Android 10 / 11 只列 JPEG、PNG，Android 12 到 16 列 JPEG、PNG、WebP、HEIF，因此区域解码 AVIF 需要按 Android 17 能力处理，低版本准备 WebP / JPG fallback。带 `isShareable` 的 `newInstance()` 重载在 Android 17 源码中仍标记 deprecated；`ImageDecoder.setCrop()` 只做输出裁剪，不是 `decodeRegion()` 的替代品。[已验证: AOSP android-17.0.0_r1, BitmapRegionDecoder.java][已验证: 官方文档, ImageDecoder]

因此，大图展示不要只写成“用 ImageDecoder 裁一下”。如果业务需要平移缩放长图，仍要按 tile 设计数据结构；如果目标只是在解码时裁掉边缘区域，`ImageDecoder.setCrop()` 才合适。

## 图片缓存策略（内存 / 磁盘 / 网络）

缓存不是越多越好。图片缓存有三个目标：减少重复网络请求、减少重复解码、控制峰值内存。三个目标对应不同层级，混在一个 LruCache 里会让问题变得难排查。

| 缓存层 | 缓存对象 | 命中收益 | 主要风险 | 建议 |
| --- | --- | --- | --- | --- |
| 内存缓存 | 已解码 Bitmap / Drawable | 省掉磁盘读和解码 | 占用 PSS / Native heap，触发 OOM | 用框架默认内存缓存，按 `onTrimMemory()` 收缩 |
| 复用池 | 可复用 Bitmap / byte array | 减少分配和 GC / Native 分配抖动 | 复用仍在展示的资源会花屏或崩溃 | 交给 Glide / Coil，少写手动池 |
| 磁盘缓存 | 原始数据或变换后资源 | 省网络，部分场景省解码 | 占用存储，缓存 key 失效难追 | key 包含 URL、尺寸、变换、格式版本 |
| 网络缓存 | CDN / HTTP cache | 降低下载耗时和流量 | Header 配错导致旧图不更新 | 服务端维护 `ETag`、`Cache-Control`、版本化 URL |

Glide 的磁盘缓存区分 resource 和 data，能缓存变换后结果，也能缓存原始数据。Coil 的 `ImageLoader` 同时管理内存缓存、磁盘缓存和网络客户端。业务层再套一层 URL → Bitmap 缓存，通常只会增加双份内存和错误失效概率。[已验证: Glide caching docs][已验证: Coil Image Loaders docs]

内存缓存大小应跟设备等级和页面形态绑定：

- 首页信息流：缓存命中影响滑动稳定性，内存缓存可以略大，但要在 `TRIM_MEMORY_UI_HIDDEN` 后释放页面级引用。
- 聊天 / 相册：同屏图片多，缓存 key 必须带尺寸；原图、缩略图、圆角图不能共用一个 key。
- 低端机：优先降请求尺寸和预取数量，再调小缓存。只调缓存大小不能解决解码峰值。
- 多进程：每个进程都有独立缓存。图片展示放在主进程时，后台进程不要初始化完整图片加载栈。

线上指标不要只记录“加载成功率”。图片加载至少要采集解码耗时、内存缓存命中、磁盘缓存命中、下载字节数、Bitmap 分配字节数、OOM 前最近 N 次图片请求。这样才能区分网络慢、解码慢、缓存失效和图片尺寸异常。[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]

## AVIF / WebP 格式选型与兼容性

Android 官方图片压缩文档把 AVIF、PNG、JPG、WebP 放在常见格式范围内，并说明 Android 12（API 31）及以上支持 AVIF。AVIF 在同等文件大小下通常能提供更好的静态图质量，但低版本平台、服务端转码链路、图片库解码器都要验证。[已验证: 官方文档, Reduce image sizes]

格式选择可以按下面的边界处理：

- JPG：照片类内容仍然稳，缺点是透明度不支持，反复压缩会损伤细节。
- PNG：透明 UI 资源和小图标安全，但照片类图片体积偏大。
- WebP：适合替代一部分 JPG / PNG，兼容性风险低于 AVIF，透明图也可覆盖不少 PNG 场景。
- AVIF：优先用于 Android 12+ 的静态大图和服务端可协商下发的场景；Android 10/11 准备 WebP 或 JPG fallback。

格式优化不要脱离解码成本。体积更小不一定等于首屏更快：如果某格式在目标设备上解码更慢，首帧仍可能变差。上线前至少对低端机做同图对比：下载字节数、解码耗时、峰值内存、首帧时间、视觉质量。

## 实战检查清单

图片问题排查可以从这张清单开始：

- 目标尺寸：请求尺寸是否接近 View 尺寸，列表缩略图是否错误请求原图。
- 解码线程：解码是否在后台线程，主线程是否只接收已完成结果。
- 取消机制：列表快速滑动后，旧请求是否能取消，旧结果是否会回写到复用 item。
- 缓存 key：URL、尺寸、圆角、变换、格式版本是否进入 key。
- 内存峰值：同一屏最多会同时存在多少张 Bitmap，ARGB_8888 下峰值是多少 MB。
- 生命周期：页面退出、Fragment `onDestroyView()`、Compose item 离屏后请求是否释放。
- 低内存回调：`ComponentCallbacks2.onTrimMemory()` 是否能触发缓存收缩。
- 格式兼容：AVIF / WebP 是否按系统版本和服务端能力下发兜底格式。

到这里，图片优化的主线就清楚了：先把图片解到正确尺寸，再让框架管理生命周期和缓存，超大图按区域解码，格式选择服从兼容性和真实耗时。工程里最常见的收益，来自“少解码”和“少重复解码”。
