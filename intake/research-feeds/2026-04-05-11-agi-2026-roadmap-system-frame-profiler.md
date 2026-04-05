## [研究] AGI 2026 路线图：改进版 System Profiler + 高级 Frame Profiler Alpha + AVP 2025

- **来源**: https://developer.android.com/agi (AGI 官方文档 + Google I/O 2025/2026 session)
- **作者/机构**: Google / Android GPU Inspector 团队
- **日期**: 2025-2026 roadmap
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**: 14.8 GPU 图形调试与分析工具 / 2.10 GPU 渲染深入 / 13.3 Perfetto View 解读
- **映射锚点**: AGI 工具详解、Vulkan 帧分析、系统级 GPU tracing、render pass graph 分析、GFXReconstruct 工作流
- **摘要**: Google 发布 AGI（Android GPU Inspector）2025-2026 路线图：2026 年上半年推出改进版 System Profiler（更快、支持超大 trace、帧截图、side-by-side 对比、开源），2026 下半年推出基于 GFXReconstruct 的高级 Frame Profiler Alpha（frame looping、render pass graph、帧/RenderPass 计时与计数器、导出至 RenderDoc）。

### 关键发现
1. **改进版 System Profiler（2026 H1）**：速度和可靠性大幅提升，支持超大 trace 文件、帧截图功能、并排查看多个 trace 的能力。计划开源
2. **高级 Frame Profiler Alpha（2026 H2）**：基于 GFXReconstruct 构建，核心特性包括 frame looping（精确测量重复帧性能）、render pass graph（可视化 RenderPass 依赖关系，优化内存带宽）、帧和 RenderPass 级别的计时和硬件计数器、导出到 RenderDoc 进行深度检查
3. **AGI 对 GLES 应用的分析路径**：AGI 通过自定义 ANGLE build 将 GLES 命令翻译为 Vulkan 进行追踪和分析。这使 AGI 能同时支持原生 Vulkan 应用和 GLES 应用
4. **Vulkan Profiles (AVP 2025)**：AGI 团队参与定义了 Android Vulkan Profile 2025，包含额外内存特性、细粒度浮点控制、GPU query host reset、标准化像素格式，定义了活跃 Android 设备上的 Vulkan 能力基线

### 可直接引用段落
> An upgraded system profiler is set to launch soon, offering enhanced speed, reliability, and a smoother user experience. It will include features like frame screenshots, support for very large traces, and the ability to view traces side-by-side. This improved system profiler is slated to become open-source. An alpha version of an improved frame profiler is anticipated in H2 2026, based on GFXReconstruct and incorporating frame looping for more accurate measurements, render pass graph to optimize memory bandwidth, and frame/render pass timings and counters.

### 与 queue.json 联动
- 优先级调整建议：建议 §14.8 GPU 图形调试与分析工具素材充分度达标
- 素材路径建议：AGI 作为 §14.8 核心工具详解的素材，与 Sokatoa/RenderDoc/ARM Streamline 构成完整工具图谱
