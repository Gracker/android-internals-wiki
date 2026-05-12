---
tags:
  - android
  - ai
  - memory
  - research
  - github
---

## [研究] Coil 3 移除 Bitmap Pooling + Compose 集成性能优化
- **来源**：https://coil-kt.github.io/coil/changelog/ | https://github.com/coil-kt/coil
- **作者/机构**：Coil Team (Colin White)
- **日期**：2025-2026
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**：7.10 图片加载与 Bitmap 性能优化
- **映射锚点**：图片加载库对比、Bitmap 内存管理、Compose 图片性能
- **摘要**：Coil 3.x 做出了重大架构决策——完全移除 Bitmap Pooling。原因是 API 23+ 上 pooling 效果递减，且不可变 Bitmap 在新运行时上有性能优势。同时 Coil 3 的 Compose 集成声称运行时性能提升 25-40%，分配减少 35-48%。

### 关键发现
1. **Bitmap Pooling 移除**：Coil 3 完全移除了 LruBitmapPool。理由包括：(a) API 23+ 上 GC 对 Bitmap 回收已足够高效；(b) 不可变 Bitmap（immutable）在 ART 和 RenderThread 管线中有优化路径；(c) pooling 追踪开销超过了回收收益；(d) 移除后 API 更简洁，暴露 Drawable 的场景更多
2. **Compose Smart Integration**：AsyncImage/SubcomposeAsyncImage/rememberAsyncImagePainter 全部更新为 restartable + skippable，减少不必要的 recomposition；运行时性能提升 25-40%，内存分配减少 35-48%
3. **独立 Disk Cache**：Coil 3 实现了自己的磁盘缓存（不再依赖 OkHttp Cache），减少网络栈依赖和序列化开销

### 可直接引用段落
> Coil 3 removes bitmap pooling entirely. On modern Android versions (API 23+), the garbage collector is efficient enough at reclaiming bitmaps that the overhead of tracking and managing a bitmap pool outweighs the benefits. Additionally, removing pooling allows Coil to use immutable bitmaps, which have inherent performance advantages in the rendering pipeline.
> — Coil 3 Migration Guide

### 与 queue.json 联动
- 优先级调整建议：§7.10 的 priority 应保持 80 或提升到 85
- 素材路径建议：补充到 §7.10 material_paths
