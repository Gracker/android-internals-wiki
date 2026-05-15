---
title: "Perfetto Profile 导入与 Flamegraph 分析"
chapter: "13.12"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: ["perfetto", "simpleperf", "pprof", "flamegraph", "profiling", "trace"]
related_chapters: ["13.2", "13.3", "13.10", "14.2", "14.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "研究素材/官方发布说明"
sources:
  - type: official
    path: "https://github.com/google/perfetto/releases/tag/v53.0"
  - type: official
    path: "https://github.com/google/perfetto/releases/tag/v54.0"
  - type: blog
    path: "intake/research-feeds/2026-04-14-07-perfetto-v53-rust-sdk-pprof-simpleperf-custom-sorting.md"
  - type: blog
    path: "intake/research-feeds/2026-04-14-07-perfetto-v54-data-explorer-jank-cuj-heap-graph-stats.md"
---

# 13.12 Perfetto Profile 导入与 Flamegraph 分析

<!-- outline-start -->
## 要点

### 🔹 profile 与 system trace 的数据边界
说明 pprof、simpleperf protobuf、Perfetto trace 三类输入各自回答的问题，以及时间轴能否互相对齐。

### 🔹 pprof / Simpleperf 导入流程
整理 Perfetto v53 起支持的导入入口、格式限制、符号文件准备和常见失败原因。

### 🔹 TrackEvent callstack 与区域聚合
说明转换 trace 时附加 callstack 后，选区如何聚合成 flamegraph，以及它和 CPU sample profile 的差异。

### 🔹 Flamegraph、inline function 与 R8 retracing
整理内联函数显示、混淆还原、Java/Kotlin/native 混合栈在 Perfetto UI 中的阅读顺序。

### 🔹 Data Explorer 与 SQL 标准库补充
把 v54 Data Explorer、Collapsed Stack、Jank CUJ、heap_graph_stats 和现有 SQL 工作流的关系放到同一张表。

### 🔹 大 Trace 分析工作流
给出从抓取、裁剪、导入 profile、定位热点线程到写出结论的步骤，避免只看火焰图最高帧。

## 扩展

### 🔸 Firefox Profiler / Collapsed Stack 互通
补跨工具转换场景和信息丢失点。

### 🔸 Profile 与 FrameTimeline / Binder / GC 交叉分析
给出 SQL join 与 UI 选区结合的案例模板。

<!-- outline-end -->

> 本节内容待加工。
