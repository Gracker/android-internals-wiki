## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-06-10
- **类型**：知识表述更新
- **位置**：章节中关于 preloaded classes 数量的历史对比表述
- **问题**：文中提到"老文章常把 preloaded classes 写成'3000-4000 个常用类'"，虽然正文已正确说明当前版本为18431，但这种过时参考的对比表述可能让读者困惑当前实际值
- **建议**：直接删除"3000-4000"这个过时数字的对比，或改为更明确的版本标注，如"Android 8/9时代的3000-4000个类已扩展到当前版本的18431个"

## [Task6 Review] 14.2 Simpleperf — 2026-06-10

### B1 需重写 — 全文叙述风格
- **类型**：需重写
- **位置**：全文（14.2.1-14.2.6）
- **问题**：命令速查表风格，缺乏连贯叙述和因果关系。违反 writing-guide.md "叙述为主，列表为辅"铁律。读者读完知道有哪些命令但不知道怎么用它们解决实际问题。整篇可被 simpleperf --help 替代。
- **建议**：以完整性能分析案例为主线贯穿全文：发现问题→选择工具→配置采集→解读report→定位热点→优化→验证。命令和参数在流程中自然引出。

### B2 需重写 — 开头
- **类型**：需重写
- **位置**：14.2.1 第一段
- **问题**：百科词条式定义（"Simpleperf是Android系统自带的高性能分析工具，专为开发者设计"），违反 writing-guide Type C 工具使用篇模板。
- **建议**：从"没有 simpleperf 时 native 性能分析只有 top/strace、看不到函数级热点、无法关联调用栈"的痛点切入。

### B3 需补充内容 — 性能优化实践
- **类型**：需补充内容
- **位置**：14.2.7
- **问题**：仍为 Task2B 回炉占位符，无实质内容。上次 review 已指出旧版为通用 Java 优化模式且 API 版本矛盾。
- **建议**：按回炉方向重写：simpleperf report 发现热点→调用栈解读→定位优化方向→优化后再用 simpleperf 验证。

### B4 需补充内容 — 性能案例分析
- **类型**：需补充内容
- **位置**：14.2.9
- **问题**：仍为 Task2B 回炉占位符，缺少 simpleperf 特有信息。
- **建议**：完整案例：record → report 原始输出 → 调用栈图 → 热点函数定位 → 优化 → 验证全流程。

### B5 需补充内容 — 性能基准测试
- **类型**：需补充内容
- **位置**：14.2.11
- **问题**：仍为 Task2B 回炉占位符。
- **建议**：基于 simpleperf stat 实测重写，展示如何建立性能基线。

### B6 需补充内容 — 总结与最佳实践
- **类型**：需补充内容
- **位置**：14.2.12
- **问题**：仍为 Task2B 回炉占位符。
- **建议**：以"如何用 Simpleperf 建立日常性能监控节奏"为主线，落实到 record→report→定位热点→验证的具体步骤。

### B7 需确认 — Perfetto 相关参数真实性（交 Task 9）
- **类型**：需确认
- **位置**：14.2.5 Perfetto 数据收集
- **问题**：使用 --perfetto、--config perfetto_config.xml、--out perfetto.traces 等参数，需 Task 9 对照 NDK simpleperf 文档验证这些是否为真实支持的参数名。
- **建议**：Task 9 源码验证后给出正确参数名。

### B8 需确认 — 内存分析事件名和 report 参数真实性（交 Task 9）
- **类型**：需确认
- **位置**：14.2.6 数据分析与解读
- **问题**：alloc_count/alloc_size/malloc_count/malloc_size 事件名及 --show-alloc-stats/--show-branch-miss/--show-cache-miss/--show-timeline/--top 10 等 report 参数，需 Task 9 验证是否存在。
- **建议**：Task 9 对照 simpleperf 官方文档验证。

### B9 结构性 — 内部章节编号冲突
- **类型**：需确认
- **位置**：全文标题
- **问题**：章节为 14.2 Simpleperf，但内部标题使用 14.1-14.13（与 14.2 章节号冲突）。
- **建议**：修正为 14.2.1-14.2.13，并检查 SUMMARY.md 交叉引用一致性。

### B10 版本边界 — DeepResearch main 分支引用
- **类型**：需确认
- **位置**：参考资料/DeepResearch引用
- **问题**：引用的 DeepResearch 标注为"main分支快照"，包含可能未进入 Android 17 的内容。按 AIW 版本边界规则需标注"未进入 Android 17"。
- **建议**：审查材料中哪些断言已进入 Android 17 正式分支，确定是否需要更新 applicable_versions。

## [Task9 Deep Review] 14.2 Simpleperf — 2026-06-10
- **类型**：源码准确性/数据缺失/交叉引用
- **位置**：多个维度的问题
- **问题**：1) 缺少AOSP源码具体路径和验证的代码片段 2) 没有实际simpleperf输出示例和解读 3) 缺少与Android安全模型的集成说明 4) 没有ARM/x86架构特有行为说明 5) 缺少与其他Android profiling工具的比较
- **建议**：1) 补充具体AOSP源码路径和关键类/方法名 2) 提供真实report输出示例并逐行解读 3) 增加安全权限和隐私保护机制章节 4) 添加架构特有行为说明和限制 5) 补充与Systrace/Traceview等工具的对比表格

- **review 日志**：logs/review/2026-06-10-07-review.md


## [Task6 Review] 14.2 Simpleperf — 2026-06-10 (第三轮)

### N1 需确认 — 事实矛盾（交 Task 9）
- **类型**：需确认
- **位置**：14.2.1 vs 14.2.2
- **问题**：14.2.1 称"Android 系统自带"+"零依赖：无需额外安装"，14.2.2 却写"Simpleperf 通过 NDK 分发，不在系统镜像中预装"。两处描述互相矛盾
- **建议**：由 Task 9 查源确认 simpleperf 在各 Android 版本的分发方式，统一描述
- **review 日志**：logs/review/2026-06-10-08-review.md

### N2 需确认 — 命令参数准确性（交 Task 9）
- **类型**：需确认
- **位置**：14.2.5（Perfetto 数据收集）、14.2.6（数据分析）
- **问题**：以下命令参数可能不存在于 simpleperf：
  - `--perfetto` 标志
  - `--config perfetto_config.xml`
  - `--out perfetto.traces`
  - `alloc_count`/`alloc_size`/`malloc_count`/`malloc_size` 事件名
  - `--show-alloc-stats`/`--show-timeline`/`--top` 报告标志
- **建议**：Task 9 对照 NDK simpleperf 文档逐一验证
- **review 日志**：logs/review/2026-06-10-08-review.md

### N3 需补充 — 验证标注
- **类型**：需补充
- **位置**：全文
- **问题**：所有技术断言（命令参数、事件名、标志含义）无 [已验证]/[待验证] 标注
- **建议**：Task 2B 在重写时补充验证标注
- **review 日志**：logs/review/2026-06-10-08-review.md
