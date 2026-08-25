# 第 15 章：方法论

一次性能调查要能复查、复现和交接，至少要说清四件事：现象怎样定义，现有证据能证明什么，App、系统和测试环境分别影响哪一段，以及修复后怎样验证。

前面的章节解释系统机制和工具用法。本章把问题定义、责任归因、指标、实验、线上监控、源码阅读和团队协作放进同一套判断流程。

## 内容索引

- [15.1 Android 性能优化原则、实证与治理](01-performance-principles-evidence-governance.md)
- [15.2 如何区分系统问题和 App 问题](02-system-vs-app.md)
- [15.3 性能指标体系与线上监控](03-performance-metrics-online-monitoring.md)
- [15.4 竞品分析方法](04-competitive-analysis.md)
- [15.5 性能测试最佳实践](05-testing-best-practices.md)
- [15.6 AOSP 代码阅读](06-aosp-reading.md)
- [15.7 Google Android Bench：AI 编码能力评测方法论](07-google-android-bench-ai-coding-evaluation-methodology.md)
- [15.8 设备分级性能策略实战](08-device-tier-performance-strategy.md)

## 阅读建议

- 第一次建立性能分析流程：按 `15.1` → `15.2` → `15.3` 阅读，先统一结论、归因和指标口径。
- 设计可比较的实验：阅读 `15.4` 和 `15.5`；前者偏竞品对照，后者偏回归测试。
- 处理线上问题并推动修复：先用 `15.3` 定义监控信号和指标，再用 `15.1` 的治理方法跟到发布验收。
- 从证据继续追源码或研究数据：阅读 `15.6` 和 `15.1`。评估 AI 修改 Android 代码的能力时，再阅读 `15.7`。
- 制定跨启动、渲染、内存和媒体的设备差异化策略：阅读 `15.8`，并回到对应机制章验证每项预算。

第二轮审阅把本章从 10 篇收敛为 7 篇：性能原则、实证方法和治理闭环统一到 15.1，指标体系与线上监控统一到 15.3；竞品、测试、源码阅读和 AI 编码评测继续独立承载。结构复审又把原 21.11 的跨场景设备分级策略移入方法论，形成 15.8。详细映射见 [`metadata/content-consolidation-audit.md`](../../../metadata/content-consolidation-audit.md)。
