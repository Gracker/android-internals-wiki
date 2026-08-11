# 第 15 章：方法论

性能分析需要一套跨模块的判断框架。

工具和零散知识只能回答局部问题，还需要明确异常分类、系统与 App 责任边界、指标选择、线上反馈和团队协作方式。

前面的章节解释系统机制，这里集中说明怎样组织证据并形成可重复的分析流程。

## 内容索引

- [15.1 性能优化的术、道、器](01-philosophy.md)
- [15.2 如何区分系统问题和 App 问题](02-system-vs-app.md)
- [15.3 性能指标体系](03-metrics.md)
- [15.4 竞品分析方法](04-competitive-analysis.md)
- [15.5 线上性能监控](05-online-monitoring.md)
- [15.6 性能测试最佳实践](06-testing-best-practices.md)
- [15.7 AOSP 代码阅读](07-aosp-reading.md)
- [15.8 Android 性能问题实证：真实世界的分类与代码模式](08-empirical-performance-issues.md)
- [15.9 性能反馈回路与治理工程化](09-performance-governance.md)
- [15.10 Google Android Bench：AI 编码能力评测方法论](10-google-android-bench-ai-coding-evaluation-methodology.md)

## 阅读建议

- trace 结论不稳：优先阅读 `15.1`、`15.2`、`15.3`。
- 线上监控与团队治理：连续阅读 `15.5`、`15.6`、`15.9`。
- 研究、源码阅读与 AI 编码评测：阅读 `15.7`、`15.8`、`15.10`。

本章由 12 篇正文收敛为 10 篇。原 15.9 的数据生命周期、工单状态机和验收流程并入 15.9 治理主文；原 15.12 与总方法论、测试和 Perfetto 专章重复，独有的证据等级、替代假设和知识交付规范并入 15.1。详细映射见 [`metadata/content-consolidation-audit.md`](../../../metadata/content-consolidation-audit.md)。
