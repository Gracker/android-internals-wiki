---
title: ch10-memory-perf
chapter: '10'
status: deprecated
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1 / Android common kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: internal
    path: "src/part2-performance/ch10-memory-perf/10.01-android-memory-performance-optimization.md"
  - type: internal
    path: "src/part2-performance/ch10-memory-perf/README.md"
tags:
- performance
- memory
- perf
---

> ⚠️ **本页已废弃（deprecated 2026-07-04）**：文件路径仅用于兼容旧链接。第 10 章已经拆分为章节导航和 10.1～10.10 专题，本页不再维护重复正文。

# 第 10 章：内存性能

请从以下入口继续阅读：

- [第 10 章导航](README.md)：按现场现象选择专题；
- [10.01 Android 内存性能优化](10.01-android-memory-performance-optimization.md)：全章诊断框架；
- [10.1 App 内存分析](01-app-memory-analysis.md)：PSS、RSS、Java、Native、Graphics 与工具选择。

## 已撤销的旧稿结论

旧稿曾收录“Android 17 机器学习驱动的内存调度器”“启动时间降低 30%”“后台内存降低 25%”等摘要。`android-17.0.0_r1` 没有对应的 AOSP 组件、类名、调用链或可复现实验，这些内容已经删除，不能作为 Android 17 平台能力引用。

旧稿还把一篇 Linux 6.10 二手报道当作 Android 当前内核结论。第 10 章涉及内核行为时，统一以 `android17-6.18-2026-06_r6` 为锚点，并按 PSI、cgroup v2、reclaim、compaction 与 lmkd 的实际调用关系分别核对。

保留本页不会创建第二套技术叙述。后续修订只进入导航页或对应专题。
