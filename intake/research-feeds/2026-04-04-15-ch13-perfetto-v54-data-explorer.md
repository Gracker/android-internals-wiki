## [研究] Perfetto v54.0：Data Explorer 可视化查询 + 火焰图增强 + 7x JSON 解析提速
- **来源**：https://github.com/google/perfetto/releases/tag/v54.0 + https://perfetto.dev/docs/analysis/trace-protractor
- **作者/机构**：Google Perfetto Team
- **日期**：2026-02-27
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**：13.3 Perfetto View 解读 / 13.5 专题解读 / 14.1 Android Studio Profiler
- **映射锚点**：Perfetto UI 功能、SQL 分析、火焰图、Trace 抓取配置、数据源
- **摘要**：Perfetto v54.0（2026 年 2 月 27 日）发布重大更新：新增 Data Explorer 可视化查询构建器（免 SQL 拖拽分析）、Collapsed Stack 格式支持（Brendan Gregg 工具兼容）、7x JSON 解析提速、R8 反混淆 Retracing、内联函数火焰图区分、android.user_list / android.aflags 新数据源、加权 Jank 指标标准库等。

### 关键发现
1. **Data Explorer（可视化查询构建器）**：v54 新增核心功能——用户通过拖拽节点构建分析管线，无需编写 SQL 即可分析 Trace 数据。结果在交互式表格中实时显示。这对不熟悉 Perfetto SQL 的性能工程师大幅降低门槛
2. **Trace Processor 增强**：
   - 支持 Brendan Gregg 的 Collapsed Stack 格式（分号分隔栈帧+计数），可直接生成火焰图
   - 支持 Firefox Profiler 预处理 JSON 格式
   - JSON Trace 解析速度提升 7 倍，UI 和 trace processor 加载显著加速
   - R8 Retracing：反混淆时支持 R8 重追踪，Android 混淆堆栈可读性大幅提升
3. **火焰图（Flamegraph）增强**：
   - 可视化区分内联函数（inline functions），帮助识别编译器优化
   - TrackEvent Callstacks：开发者可在事件上附加调用栈，选中区域自动聚合为火焰图
   - 支持解析 perf script 输出和 simpleperf protobuf 格式 → 在 Perfetto UI 中可视化
   - macOS Instruments traces 的 CPU 栈采样也可可视化为火焰图
4. **Android 专项增强**：
   - 新增 `android.user_list` 数据源：列出 Android 多用户信息
   - 即将推出 `android.aflags` 数据源：捕获和可视化 Android aconfig flags
   - `android_anrs` 表新增 intent 和 component 详情字段
   - 标准库新增加权 Jank 指标（weighted jank metrics）
   - 录制页面新增预设配置（preset recording configs），一键配置常见 Android/Chrome 系统健康场景
5. **SDK / 基础设施**：
   - 新增 `NamedTrack`：可创建任意命名的 Track
   - TraceConfig 新增 `write_flush_mode` 枚举替代已弃用的 `no_flush_before_write_into_file`
   - 非Android平台的 tracing service 使用 lock-free task runner 降低锁竞争
   - `linux.ftrace` 编码优化减少 trace 体积，SharedMemoryArbiter 优化降低 CPU 使用

### 可直接引用段落
> Perfetto v54.0 introduces the Data Explorer, a new visual query builder that enables users to analyze trace data without writing SQL. It allows the construction of analysis pipelines by connecting nodes in a graph, with results displayed in real-time within an interactive table.

> The trace processor now supports the Collapsed Stack format (used by Brendan Gregg's FlameGraph tools) and Firefox Profiler's preprocessed JSON format. Parsing of JSON traces has improved by 7x, resulting in significantly faster loading in both the Perfetto UI and the trace processor.

> Flamegraphs are now capable of visually distinguishing inlined functions, which can help in identifying compiler optimizations. The trace processor can parse CPU sample data from perf script output and simpleperf's protobuf format, enabling their visualization as flamegraphs in the Perfetto UI.

### 与 queue.json 联动
- 优先级调整建议：§13.3 和 §13.5 已为 ready-for-review，建议在 review 时引用 v54 新特性补充 Data Explorer 和火焰图相关段落
- 素材路径建议：可补充到 §13.3 的 material_paths，为"Perfetto UI 新功能"和"SQL 分析替代方案"提供素材
- 建议 §14.1 review 时提及 R8 Retracing 对 Android Studio Profiler 的影响
