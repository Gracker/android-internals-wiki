## [研究] Samsung Sokatoa：开源多帧 GPU Profiler（2026.03）

- **来源**: https://developer.samsung.com/galaxy-gamedev/sokatoa.html
- **作者/机构**: Samsung（与 Google、LunarG 合作开发）
- **日期**: 2026-03
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**: 14.8 GPU 图形调试与分析工具 / 2.10 GPU 渲染深入
- **映射锚点**: GPU profiling 工具选型、Vulkan 分析工具、多帧分析方法论、跨 GPU 厂商工具
- **摘要**: Samsung 于 2026 年 3 月发布 Sokatoa，一款面向 Android 的开源 GPU 性能分析器。核心创新是多帧分析能力，可跨帧识别渲染模式和间歇性卡顿。基于 LunarG 的 GFXReconstruct 捕获/回放引擎构建，原生支持 Vulkan，兼容 Samsung Xclipse、Qualcomm Adreno、ARM Mali。

### 关键发现
1. **多帧 GPU profiling**：区别于 AGI/RenderDoc 的单帧分析范式，Sokatoa 可同时分析多个连续帧的 GPU 行为，定位单帧工具难以发现的间歇性渲染异常（如偶发卡顿、shader 编译尖刺）
2. **硬件无关架构**：基于 GFXReconstruct 的 API 调用捕获/回放机制，支持 Exynos/Qualcomm/ARM 多种 GPU，实现跨平台确定性分析
3. **开源计划**：Samsung 已宣布 2026 年内开源 Sokatoa，这将使其成为继 RenderDoc 之后第二个主流开源移动 GPU profiler

### 可直接引用段落
> Sokatoa supports multi-frame GPU profiling, which allows developers to analyze rendering behavior across multiple frames simultaneously. This helps in identifying and resolving complex graphics performance issues that are often challenging to detect with traditional single-frame tools. The profiler is built on LunarG's GFXReconstruct capture and replay engine and supports Vulkan-based applications. While optimized for Samsung's Xclipse and Exynos GPUs, Sokatoa is also compatible with other major Android GPUs from manufacturers like Qualcomm and ARM.

### 与 queue.json 联动
- 优先级调整建议：建议 §14.8 GPU 图形调试与分析工具的 priority 保持 80 不变，但素材充分度已达标
- 素材路径建议：可补充到 §14.8 的 material_paths，作为核心工具之一（与 AGI、RenderDoc、ARM Streamline 并列）
