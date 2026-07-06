## [Task9 Deep Review] 1.5 线程模型 — 2026-07-07
- **类型**：版本差异
- **位置**：源码版本锚点声明
- **问题**：章节声明适用 Android 5.0 - Android 17，但主要源码引用基于 android-16.0.0_r1，与 Android 17 (android-17.0.0_r1) 存在版本差异。源码版本锚点与覆盖范围不匹配。
- **建议**：明确区分 android-16.0.0_r1 与 Android 17 的版本边界，在源码引用处标注具体版本，并补充说明 Android 17 中 MessageQueue 默认启用边界（USE_NEW_MESSAGEQUEUE）和 RenderThread 调度策略的重要变化。

## [Task2B Verifier] §18.18 PIP 与自由窗口渲染 — 2026-07-07
- **类型**：blocked-need-rework-evidence
- **位置**：src/part2-performance/ch18-rendering-pipelines/18-pip-freeform.md
- **问题**：task9_result=needs-rework，但 queue.json 无 pending 条目。Task2B Lite 已修复（TaskOrganizer 版本标注），Task6 已复审通过。needs-rework 可能来自 verifier 重复键解析（pass-tech-review → needs-rework），需 Task9 明确复审
- **建议**：Task9 下一轮应复审 §18.18，出具 pass-tech-review 或写入新 queue 条目

## [Task2B Verifier] §14.11 Battery Historian — 2026-07-07
- **类型**：blocked-need-rework-evidence
- **位置**：src/part3-tools/ch14-other-tools/11-battery-historian.md
- **问题**：task9_result=needs-rework，queue.json 中 14.11 全部 completed。Task2B 已修复全部 P0/P1，Task6 多轮复审通过。needs-rework 可能是 frontmatter 重建后的残留状态
- **建议**：Task9 下一轮应复审 §14.11，出具 pass-tech-review 或写入新 queue 条目
