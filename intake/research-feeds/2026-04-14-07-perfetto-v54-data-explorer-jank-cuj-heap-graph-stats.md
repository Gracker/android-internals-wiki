# [研究] Perfetto v54.0 — Data Explorer、Jank CUJ 模块与 SQL 标准库重大更新
- **来源**：https://github.com/google/perfetto/releases/tag/v54.0
- **作者/机构**：Google Perfetto Team
- **日期**：2026-02-27
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**：13 Profiling 工具（v54 新特性）、7 流畅性（Jank CUJ 模块）、10 内存性能（heap_graph_stats + dmabuf）
- **映射锚点**：Perfetto Data Explorer、Jank CUJ SQL 模块、counter-based weighted jank metrics、heap_graph_stats（含 dmabuf）、android_anrs 增强、Collapsed Stack 格式、R8 retracing、snap-to-boundaries UI

## 摘要
Perfetto v54.0 是 2026 年初最重要的性能分析工具更新。核心新增包括 Data Explorer（无代码可视化分析）、Jank CUJ SQL 标准库模块、counter-based weighted jank 指标、heap_graph_stats 模块（含 dmabuf 支持）、Collapsed Stack 格式（兼容 Brendan Gregg FlameGraph）、Firefox Profiler 格式支持、R8 retracing 去混淆增强，以及多项 UI 交互优化（snap-to-boundaries、pivot table、glob filter）。

### 关键发现
1. **Data Explorer**：全新的无代码可视化分析界面，通过连接节点构建分析管线，支持选择数据源、添加变换、实时查看交互式表格结果。降低了 Perfetto SQL 的使用门槛。
2. **Jank CUJ 模块 + counter-based weighted jank metrics**：SQL 标准库新增 relevant threads jank CUJ 模块和基于 counter 的加权 jank 指标。这为 13.8（Perfetto 输入延迟 SQL 深度分析）提供了新的标准库支撑，可直接用于 CUJ 级别的 jank 量化分析。
3. **heap_graph_stats 模块 + dmabuf 支持**：新增 heap_graph_stats SQL 模块，支持 DMA-BUF 图形内存分析。与 ch10 内存性能和 ch2 渲染架构中的 DMA-BUF/Gralloc 内容直接关联。
4. **android_anrs 表增强**：新增 intent 和 component 列，ANR 分析时可直接关联到具体的 Intent 和组件名称。
5. **Breaking changes**：slice 表移除 stack_id 和 parent_stack_id 列（迁移到 slices.stack stdlib module）；machine_id 改为 non-nullable；metadata 表重构支持 multi-trace/multi-machine。

### 可直接引用段落
> **SQL Standard library:**
> * Added `heap_graph_stats` module and added dmabuf support.
> * Added `intent` and `component` columns to `android_anrs` table.
> * Added relevant threads jank CUJ module and counter-based weighted jank metrics.
> — Perfetto v54.0 Release Notes, github.com/google/perfetto

> **UI:**
> * Added present configs to the recording page to allow easy configuration of traces for common system health problems on Android and Chrome.
> * Added snap-to-boundaries feature for precise time selection. When dragging selection handles or creating area selections, the cursor automatically snaps to nearby slice boundaries to enable exact measurement of slice durations. Hold Alt to temporarily disable snapping.
> — Perfetto v54.0 Release Notes

> **Trace Processor:**
> * Added support for Collapsed Stack format (from Brendan Gregg's FlameGraph tools). This format uses semicolon-separated stack frames with a count, e.g., "main;foo;bar 100".
> * Added support for Firefox Profiler's preprocessed JSON format.
> — Perfetto v54.0 Release Notes

### 与 queue.json 联动
- **13.8 Perfetto 输入延迟 SQL 深度分析**（priority: 90, pending）：v54 新增的 Jank CUJ 模块和 weighted jank metrics 为该章节提供了新的 SQL 标准库工具，建议在重写时纳入这些新模块。
- **14.9 Android Camera 性能**（priority: 80）：heap_graph_stats 的 dmabuf 支持可直接用于 Camera 图形内存分析。
- 素材路径建议：`intake/research-feeds/2026-04-14-07-perfetto-v54-data-explorer-jank-cuj-heap-graph-stats.md`
