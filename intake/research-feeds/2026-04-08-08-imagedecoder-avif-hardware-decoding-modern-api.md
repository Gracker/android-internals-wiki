---
tags:
  - android
  - performance
  - rendering
  - research
---

## [研究] ImageDecoder vs BitmapFactory + AVIF/HEIF 硬件解码现代管线
- **来源**：https://developer.android.com/reference/android/graphics/ImageDecoder | AOSP frameworks/base/core/jni/android/graphics/ImageDecoder.cpp
- **作者/机构**：Android Developers / AOSP
- **日期**：2024-2026
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**：7.10 图片加载与 Bitmap 性能优化
- **映射锚点**：ImageDecoder API、BitmapFactory 对比、AVIF/HEIF 硬件解码、图片解码管线
- **摘要**：Android 9（API 28）引入 ImageDecoder 取代 BitmapFactory 的部分场景。ImageDecoder 提供了更精确的缩放（setTargetSize vs inSampleSize 的 2 的幂次限制）、更好的裁剪控制、以及对 AnimatedImageDrawable 的原生支持。Android 14+ 扩展了对 AVIF 格式的硬件解码支持。

### 关键发现
1. **ImageDecoder vs BitmapFactory 关键差异**：
   - `setTargetSize(w, h)` 可以精确缩放到任意尺寸（BitmapFactory 的 `inSampleSize` 只支持 2 的幂次，导致可能加载比需要大 4 倍的图片）
   - `setCrop` 在解码时就裁剪，不需要先解码再 Bitmap.createBitmap 裁剪（节省一次内存分配）
   - `OnHeaderDecodedListener` 在读取文件头后就回调，此时可以基于实际尺寸做决策
   - 对 AnimatedImageDrawable（GIF/WebP 动画）的原生支持
2. **NDK ImageDecoder（API 30+）**：原生代码可以直接通过 AImageDecoder API 解码图片，避免 JNI 开销。适用于游戏引擎、相机管线等 native 密集场景
3. **AVIF 硬件解码**：Android 14（API 34）开始对 AVIF 格式提供系统级支持。部分 SoC（如 Snapdragon 8 Gen 3、Dimensity 9300）提供 AVIF 硬件解码器，解码速度比软解快 3-5x。Android 16/17 进一步扩展了 HEIF/AVIF 的编解码器兼容性要求
4. **BitmapFactory 仍然需要**：对于需要逐行解码、progressive JPEG、或者需要 `inPurgeable`（已废弃）等特殊场景，BitmapFactory 仍然是唯一选择。Glide 内部仍然大量使用 BitmapFactory

### 可直接引用段落
> ImageDecoder is the recommended API for decoding images on Android API 28+. Unlike BitmapFactory's inSampleSize which only supports powers of 2 (1, 2, 4, 8...), ImageDecoder's setTargetSize() allows precise downscaling to any target dimension. This means loading a 4000x3000 image into a 500x375 ImageView can be done in a single decode step at exactly the target size, rather than decoding at inSampleSize=8 (500x375) which happens to work, but inSampleSize=4 (1000x750) would waste 4x memory.

### 与 queue.json 联动
- 优先级调整建议：§7.10 priority 保持 80
- 素材路径建议：补充到 §7.10 material_paths
- 交叉引用：与 §4.3 ART 内存管理（Bitmap 像素数据堆外分配）、§2.9 渲染版本演进（Hardware Bitmap API 26+）
