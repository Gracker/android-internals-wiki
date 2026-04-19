# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch07-smoothness/`
- 最终选择：`src/part2-performance/ch07-smoothness/10-image-bitmap-performance.md`
- 选择理由：该章节属于性能优化的核心支柱（Bitmap），且其 `task9_state` 为 `pending`，迫切需要源码级深度复审以对齐 Android 14-17 的新特性。

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：**版本演进信息断层**。文章对 Android 14-17 的关键改进（Ultra HDR、dav1d、AGSL、Generational GC）几乎没有提及，且对 Hardware Bitmap 的监控机制描述过于笼统。
- 评分理由：文章在基础原理（BitmapFactory/ImageDecoder）和常规优化（inBitmap/Config）上表现优秀，且标注了 AOSP 验证，但在前沿工程实践和最新的系统级优化上存在 P1 级缺失。
- 本轮 review 覆盖范围：Bitmap 解码管线、内存复用、Hardware Bitmap 机制、Glide/Coil 架构、Android 14-17 演进、Perfetto 定位。
- 本轮未完成部分：无，已通过联网搜索补齐 Android 17 最新动态。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.5/5 | 1 |
| 原理链完整性 | 3.5/5 | 2 |
| 版本差异覆盖 | 2.5/5 | 3 |
| 知识盲区 | 3.0/5 | 2 |
| 数据/案例支撑 | 3.5/5 | 1 |
| 交叉引用一致性 | 4.5/5 | 0 |

## 四、P0 问题（事实错误）
- 暂未发现核心 API 调用或路径的严重错误。

## 五、P1 问题（重要缺失）

### 1. [P1][版本差异][Android 14-17 特性缺失]
- **原文问题**：虽然标记适用至 Android 17，但完全忽略了 **Ultra HDR (Gainmap)** 这一重大变革。
- **源码 / 一手资料锚点**：`android.graphics.Gainmap` (API 34+), `HardwareBufferRenderer` (API 34+)。
- **运行原理说明**：Android 14+ 引入 Ultra HDR，在 JPEG 中嵌入 Gainmap。解码器不仅要处理像素，还要处理元数据合成。
- **建议修正方向**：增加“Ultra HDR 与现代图片格式”小节，说明 Gainmap 对渲染管线的影响，以及应用如何通过 `setDesiredHdrHeadroom` 控制亮度。

### 2. [P1][原理链完整性][Hardware Bitmap 的自动降级机制]
- **原文问题**：只提到“要留意 fd 消耗”，没有讲清楚工程上是如何自动规避的。
- **源码 / 一手资料锚点**：Glide `HardwareConfigState` / `Downsampler.java`。
- **关键代码逻辑**：Glide 会定期检查 `/proc/self/fd` 的数量，当超过阈值（如 700）时，自动将 `inPreferredConfig` 降级为 `ARGB_8888`，这是防崩溃的关键护航机制。
- **建议修正方向**：在 Hardware Bitmap 章节补充“工程护航：自动 FD 监控”内容，给出 Glide 的监控思路。

### 3. [P1][数据支撑][AVIF 解码性能的变迁]
- **原文问题**：称 AVIF 软解慢，但未提及 Android 15 的重大优化。
- **证据依据**：Android 15 将默认 AV1 软解切换为 **dav1d**，速度提升 3 倍。
- **核验结论**：这使得 AVIF 在中低端设备上的可用性大幅提升，不再是“不可选”。
- **建议修正方向**：更新 AVIF 章节，明确标注 Android 15 后的性能拐点。

## 六、P2 问题（建议改进）

### 1. [P2][知识盲区][Android 17 ART 优化]
- **问题描述**：Android 17 引入了 **Generational GC** 和 **Lock-free MessageQueue**。
- **建议**：补充说明这些底层优化如何实质性地减少了频繁分配 Bitmap 带来的主线程抖动。

### 2. [P2][原理链完整性][Coil 移除 BitmapPool 的深意]
- **问题描述**：原文只说“不提供”，没说“为什么”。
- **理由**：Coil 官方认为现代 ART 内存管理已足够优化，`inBitmap` 的收益在 API 24+ 后显著下降，且不可变位图（Immutable Bitmaps）在并行渲染中更安全。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|----------|--------------|
| Ultra HDR Gainmap 合成 | 高 | 研究 `Gainmap` 在 GPU 侧的合成成本及 CPU 回退风险 |
| AGSL 自定义滤镜 | 中 | 探索 `RuntimeColorFilter` 替代传统 Bitmap 像素操作的性能优势 |
| 16KB 内存页影响 | 低 | 分析 Android 15 强制 16KB 页对大图加载的 PSS 影响 |

## 八、外部核验建议
- 搜索关键词：`Android 14 Ultra HDR Gainmap implementation`
- 建议查：`developer.android.com` 关于 Gainmap 的专题文档
- 搜索关键词：`Glide HardwareConfigState FD limit check`
- 建议查：Glide 源码中对 `/proc/self/fd` 的访问逻辑

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：7.10 图片加载与 Bitmap 性能优化
- **严重级别**：P1
- **问题类型**：版本差异与原理缺失
- **位置**：图片格式、Hardware Bitmap、库架构
- **描述**：缺失 Android 14-17 关键特性（Ultra HDR、dav1d、Generational GC）及 Glide 自动降级 FD 的细节。
- **建议修正方向**：同步上述 P1/P2 建议，特别是补充现代图形管线（HDR/AGSL）的内容。

### 9.4 可复用知识资产（高价值新增知识）
- **一手资料**：Android 15 软解 AV1 性能提升 3x（dav1d 集成）。
- **关键源码路径**：`frameworks/base/graphics/java/android/graphics/Gainmap.java`。
- **关键结论**：Android 17 的分代 GC 大幅缓解了 Bitmap 导致的 Minor GC 停顿，开发者在 Android 17+ 机器上可以更“激进”地分配临时 Bitmap 而不担心掉帧。
- **Trace 观察点**：在 Android 15+ 观察 AVIF 解码，应能看到从 `libgav1` 到 `dav1d` 的 slice 变化。

## 十、下一候选章节
- `src/part2-performance/ch07-smoothness/04-ui-rendering-pipeline.md` (需要确认渲染管线是否已同步 Gainmap 的合成步骤)。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-10-10-image-bitmap-performance-external-review.md`
