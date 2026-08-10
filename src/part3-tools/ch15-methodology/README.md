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
- [15.8 Android 性能问题实证](08-empirical-performance-issues.md)
- [15.9 从采集到治理的反馈回路](09-observability-closed-loop.md)
- [15.10 性能治理工程化](10-performance-governance.md)
- [15.11 Google Android Bench：AI 编码能力评测方法论](15.11-google-android-bench-ai-coding-evaluation-methodology.md)
- [15.12 Android 性能优化研究方法论](15.12-android-performance-research-methodology.md)

## 阅读建议

- trace 结论不稳：优先阅读 `15.1`、`15.2`、`15.3`。
- 线上治理：连续阅读 `15.5`、`15.9`、`15.10`。
- 团队流程与研究方法：阅读 `15.10` 到 `15.12`。
