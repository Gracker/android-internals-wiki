---
tags:
  - android
  - memory
  - research
---

## [研究] Android 17 ART 分代垃圾回收：Concurrent Mark-Compact + Generational GC

- **来源**：cs.android.com (art/runtime/gc/) + Android Developers Blog
- **作者/机构**：Google Android Team
- **日期**：2025-2026（Android 17 "Cinnamon Bun"）
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**：4.8 ART 分代垃圾回收与 GC 暂停优化
- **映射锚点**：分代 GC 机制、Concurrent Copying Collector、GC 暂停优化、young/old generation 分离、对 RecyclerView 滑动的影响
- **摘要**：Android 17 引入 Concurrent Mark-Compact collector Enhanced with Generational GC，通过更频繁的低开销 young generation 回收减少 full-heap GC 频率。目标：自动分离"年轻"和"年老"对象，显著缩小导致 RecyclerView 停止滚动的 GC 暂停。

### 关键发现

1. **Android 17 新特性**：Concurrent Mark-Compact + Generational GC。更频繁的 young generation 回收，延迟 full-heap GC 触发，降低整体 GC CPU 开销和持续时间。
2. **分代策略**：新对象放入 young generation，高频低开销回收。存活多次的对象晋升到 old generation，低频回收。
3. **历史演进**：Android 8.0 引入 Concurrent Copying GC，暂停时间缩小 85%，不再随堆大小线性增长。Android 10+ CC GC 扩展为分代模式。Android 17 进一步增强。
4. **对开发者的影响**：GC 暂停是 RecyclerView 滚动卡顿的常见根因。分代 GC 自动处理，但理解机制有助于在 Perfetto 中识别 GC 相关 jank。

### 可直接引用段落

> Android 17 ships with a "Concurrent Mark-Compact collector Enhanced with Generational gc." This aims to reduce the overall GC CPU cost and time duration through more frequent, low-overhead young-generation collections alongside full-heap collections.
>
> The goal is to significantly shrink "annoying GC pauses that would cause a RecyclerView to stop scrolling" by automatically separating "young" and "old" objects.
>
> Android 8.0's concurrent compacting GC resulted in 85% smaller pause times compared to Android 7.0, and crucially, pause times no longer scaled with heap size.

### 与 queue.json 联动
- 优先级调整建议：维持 4.8 优先级 80，标记为 Android 17 核心新特性
- 素材路径建议：补充到 4.8 material_paths，与 7.8 RecyclerView 性能交叉引用