# 第 7 章：流畅性

> 本章节正在建设中。

## 本章内容

- 卡顿的定义与分类
- 卡顿原因体系
- 卡顿分析方法论
- 典型场景分析
- 优化策略
- 案例集
- 场景化性能作战手册

## 延伸阅读

### Android 12+ FrameTimeline 架构与 Jank 责任归因矩阵深度报告
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android 12+ FrameTimeline 架构与 Jank 责任归因矩阵深度报告  .md
- 类型：DeepResearch 调研结果
- 摘要：从 TokenManager、DisplayFrame/SurfaceFrame、present fence 到 Perfetto 表结构系统梳理 Android 12+ FrameTimeline，给出 jank 位掩码归因、默认阈值和数据流全景，是做卡顿责任定位、版本边界判断与 SQL 分析的高密度参考。
- 注入时间：2026-04-20
- 价值：兼顾源码结构和可观测性，适合作为 Jank 归因与 FrameTimeline 读图的统一入口。
