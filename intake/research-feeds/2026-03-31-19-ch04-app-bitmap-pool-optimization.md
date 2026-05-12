# Bitmap 内存优化：inBitmap、Bitmap Pool 与图片加载库策略

> 研究素材 · 2026-03-31 19:00 · task5-research-discovery · 目标章节: 4.5 App 内存优化

## 来源

- Android Developers: Managing Bitmap Memory (developer.android.com)
- Glide / Coil 官方文档
- Android 16KB page size 与 Bitmap 的影响分析

## 核心发现

### 1. Bitmap 是 App 内存的最大消费者

- 一张 1080×1920 ARGB_8888 图片 ≈ 8MB 内存
- 列表滑动时频繁加载/释放 Bitmap 是内存抖动的主要来源之一
- Bitmap 在 Android 8.0 (API 26) 后移至 Native 堆，但仍计入 PSS

### 2. inBitmap 复用机制

```kotlin
// API 19+ : inBitmap 只需新 Bitmap ≤ 复用 Bitmap 大小
val options = BitmapFactory.Options().apply {
    inBitmap = reusableBitmap  // 复用已有 Bitmap 的内存
    inSampleSize = 2
}
val bitmap = BitmapFactory.decodeResource(res, resId, options)
```

- **API 11-18**：inBitmap 大小必须精确匹配（限制很大）
- **API 19+**：复用 Bitmap 必须 ≥ 新 Bitmap（更实用）
- 效果：减少 malloc/free 调用，降低 GC 压力

### 3. 图片加载库的内存管理

| 库 | Bitmap Pool | 特点 |
|-----|-----------|------|
| Glide | ✅ 内建 BitmapPool | LRU 策略，自动回收 |
| Coil | ✅ 基于 Coroutine | 轻量，Kotlin-first |
| Fresco | ✅ Native Memory 管理 | CloseableReference，三层缓存 |

- Glide 4.x 默认使用 `LruBitmapPool`，大小 = `maxMemory / 8`
- 自定义 Bitmap Pool：`GlideBuilder.setBitmapPool(new LruBitmapPool(size))`

### 4. 16KB Page Size 对 Bitmap 的影响

- Bitmap 像素数据存储在 Native 堆
- 16KB page size 情况下，每个 Bitmap 的内存页浪费可能增加
- Google 建议：使用标准图片加载库（已适配），避免手动 Native Bitmap 管理

### 5. 其他 Bitmap 优化策略

- **下采样 (inSampleSize)**：加载前先缩小，避免加载原始尺寸
- **格式选择**：ARGB_8888(4B/px) vs RGB_565(2B/px)，后者省 50% 内存但无透明度
- **WebP/AVIF**：文件更小，解码后内存相同，但传输+存储节省
- **硬件 Bitmap (Hardware Bitmap)**：API 26+ 可用，像素存 GPU 内存，不计入 App PSS
  - `Bitmap.Config.HARDWARE`
  - 适合只显示一次的图片
  - 不能修改（Canvas 操作受限）

## 与 4.5 章节的关联

- Bitmap 是 App 内存优化的核心战场之一
- 与 "内存抖动" 主题互补：图片加载是最常见的抖动来源
- 与 4.3 (ART 内存管理) 中 Native 堆部分形成呼应
- 建议在 4.5 中设独立小节 "图片内存优化"

## 可验证性

- [已验证] inBitmap API 变更来自 Android 官方文档
- [已验证] Hardware Bitmap 限制来自 developer.android.com
- [待验证] Glide BitmapPool 默认大小 = maxMemory/8 的说法

## 原始链接

- https://developer.android.com/topic/performance/graphics/manage-memory
- https://developer.android.com/reference/android/graphics/Bitmap.Config#HARDWARE
- https://bumptech.github.io/glide/doc/bitmap-pool.html
