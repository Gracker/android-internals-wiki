# [研究] Perfetto v53.0 — Rust SDK、pprof/Simpleperf 可视化与 Overview 页重设计
- **来源**：https://github.com/google/perfetto/releases/tag/v53.0
- **作者/机构**：Google Perfetto Team
- **日期**：2025-11-13
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：13 Profiling 工具（pprof/Simpleperf 可视化）、14 其他工具（Rust SDK）
- **映射锚点**：pprof 原生可视化、Simpleperf protobuf 导入、TrackEvent callstack + flamegraph、custom sorting（process_sort_index/thread_sort_index）、Rust SDK、Overview 页重设计、inline functions in flamegraphs

## 摘要
Perfetto v53.0 引入了多项重量级功能：原生 pprof 可视化（无需转换即可直接在 UI 中分析 pprof 数据）、Simpleperf protobuf 格式导入支持、TrackEvent callstack 与 flamegraph 聚合、inline functions 在 flamegraph 中的可视化区分、custom sorting（process_sort_index 和 thread_sort_index 字段控制 track 排列顺序）、初始 Rust SDK（contrib/ 目录）、以及全新的 Overview 页面设计。

### 关键发现
1. **pprof + Simpleperf 原生可视化**：Perfetto UI 现在可直接导入和可视化 pprof profile 和 Simpleperf 的 protobuf 格式，无需第三方工具转换。这意味着开发者可以在同一个 Trace 中同时分析 system trace 和 CPU profiling 数据。
2. **TrackEvent callstack + flamegraph**：转换 trace 时可以为事件附加 callstack，选择区域后自动聚合为 flamegraph。配合 inline functions 可视化区分，可以识别编译器优化对性能的影响。
3. **Custom sorting**：通过 `process_sort_index` 和 `thread_sort_index` 字段控制 track 排列顺序，这是社区长期请求的功能（issues #378, #555, #764），对大型 trace 的可读性有显著提升。
4. **Rust SDK**：初始版本发布在 crates.io（perfetto-sdk），是 contrib/ 目录下第一个社区维护项目，由 Rivos 工程师贡献。
5. **Lock-free task runner**：在非 Android 平台启用了无锁任务运行器，减少锁竞争开销，对高吞吐量数据源有性能提升。

### 可直接引用段落
> **pprof & Simpleperf Support:**
> Perfetto now supports importing and visualizing pprof profiles directly in the UI. This includes a dedicated page for analyzing pprof data. We've also added support for ingesting simpleperf's protobuf format.
> — Perfetto v53.0 Release Notes, github.com/google/perfetto

> **Custom Sorting for JSON:**
> You can now control the layout of your JSON traces with standard process_sort_index and thread_sort_index fields! This lets you explicitly control the order of tracks in the UI. This was a long requested feature (#378, #555, #764).
> — Perfetto v53.0 Release Notes

> **Flamegraph & Callstack Improvements:**
> - TrackEvent Callstacks: You can now attach callstacks to events when converting traces to Perfetto! Selecting an area will aggregate these callstacks into a flamegraph.
> - Inline Functions: Flamegraphs are now capable of visually distinguishing inlined functions, making it easier to identify compiler optimizations.
> — Perfetto v53.0 Release Notes

### 与 queue.json 联动
- **13.x Profiling 工具章节**：pprof 和 Simpleperf 原生可视化是 ch13 的核心新内容，建议新增专门小节介绍这两种格式在 Perfetto UI 中的使用方法。
- 素材路径建议：`intake/research-feeds/2026-04-14-07-perfetto-v53-rust-sdk-pprof-simpleperf-custom-sorting.md`
