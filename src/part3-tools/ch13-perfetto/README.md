---
title: "第 13 章：Perfetto"
chapter: "13.0"
section: "13.0"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-21"
last_verified_against: "ch13 README + 13.1-13.16 目录 + DeepResearch/Perfetto 2026 与 AndroidX Tracing 2.0"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Perfetto 2026 架构级深度技术分析  .md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/AndroidX Tracing 2.0 架构级深度技术分析 .md"
tags: ['perfetto', 'tracing', 'overview', 'chapter-intro']
related_chapters: ["13.1", "13.2", "13.3", "13.4", "13.5", "13.6", "13.7", "13.8", "13.9", "13.10", "13.11", "13.12", "13.13", "13.14", "13.15", "13.16", "13.17"]
pipeline_stage: ready-to-publish
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
reviewed_date: "2026-04-23"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task9_result: pass-tech-review
last_task9_at: "2026-04-28T14:33:59+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-04-28"
---

# 第 13 章：Perfetto

Perfetto 是 Android 性能分析的统一时间轴。渲染、输入、启动、ANR、调度、锁、Binder、I/O、内存和功耗来自不同 data source，Trace Processor 把它们转换成可关联的表，Perfetto UI 再呈现时间关系。学习目标包括采到能回答问题的数据、读懂不同 track 的语义，以及把观察写成可复核的 SQL 与源码结论。

## 版本口径

| 层级 | 采用的版本 | 使用边界 |
|---|---|---|
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | 平台源码、数据源注册、权限和系统事件语义 |
| Android 内核 | `android17-6.18-2026-06_r6` | `sched`、perf event、ftrace、DMA-BUF 等内核行为 |
| 平台内 Perfetto | v54 时代快照，加 Android 固定 tag 中的后续改动 | 不能简写成纯 v54.0，也不能写成 Android 17 内置 v57 |
| 宿主机分析器 | Perfetto v57.2 | 用于复核当前 UI、Trace Processor 和标准库；版本应和分析结果一起保存 |
| AndroidX Tracing | 稳定版 1.3.0；2.0.0-beta01（2026-07-15） | 2.0 beta 的 `Tracer`、driver/sink、协程传播和 host JVM trace 属于应用依赖，不是平台 API 37 的组成部分 |

设备采集端与宿主机分析端可以独立升级。新 UI 通常能读取旧 trace，却不能让旧设备凭空提供新的 data source。看到空表时，应检查采集配置、设备权限、trace data loss 和分析器 schema，不能只升级浏览器页面。

## 章节目录

### 入门与采集

- [13.1 Perfetto 简介与演进](01-perfetto-intro.md)
- [13.2 Trace 抓取](02-trace-capture.md)
- [13.3 Perfetto View 解读](03-perfetto-view.md)
- [13.4 命令行打开超大 Trace](04-large-traces.md)
- [13.5 专题解读](05-topic-analysis.md)
- [13.6 线程 CPU 状态分析](06-thread-cpu-states.md)
- [13.7 Perfetto 的高级用法](07-advanced-usage.md)

### SQL 与跨层分析

- [13.8 Perfetto 输入延迟 SQL 深度分析](08-input-latency-sql.md)
- [13.9 atrace、ftrace 与 Perfetto 数据采集原理](09-tracing-infrastructure.md)
- [13.10 Perfetto SQL 性能分析实战手册](10-perfetto-sql-cookbook.md)
- [13.11 SPAN_JOIN 与窗口函数](11-perfetto-span-join-window-functions.md)
- [13.12 Profile 导入与 Flamegraph 分析](12-perfetto-profiles-flamegraph.md)
- [13.13 CPU 频率与 DVFS 关联分析](13-cpu-frequency-dvfs-analysis.md)
- [13.14 DataGrid、Data Explorer 与 Jank CUJ 标准库](14-perfetto-data-explorer-jank-cuj.md)
- [13.15 BufferQueue 阻塞的 Perfetto 识别](15-bufferqueue-blocking-perfetto.md)
- [13.16 Agent 辅助 Perfetto 分析协议](16-agent-perfetto-analysis-protocol.md)

### 数据源、SDK 与分析平台

- [13.17 Android 17 Perfetto 数据源边界与验证](17-android17-data-sources.md)
- [13.17 Perfetto SDK 与应用内 Trace 数据源](17-perfetto-sdk-in-app-tracing.md)
- [13.18 SmartPerfetto 与可复用 Trace 分析平台](18-smartperfetto-trace-analysis-platform.md)
- [13.19 FrameTracer 与 Graphics Frame Event 数据通路](19-frametracer-graphics-frame-event.md)
- [13.20 Frame Timeline：Expected 与 Actual Timeline](20-frame-timeline-api33-perfetto-analysis.md)
- [13.21 pprof 与 Simpleperf 原生可视化](21-perfetto-pprof-simpleperf-native-visualization.md)
- [13.22 Perfetto SQL 查询库与 CI](22-perfetto-sql-cookbook-performance-analysis.md)

### 补充专题

- [Perfetto 版本演进与 Android 9—17 特性验证](13.21-perfetto-version-evolution.md)
- [13.25 PerfDog 的 Android GPU/性能数据源](13.25-perfdog-android-platform-gpu-performance-data-sources.md)
- [13.26 android.os.Trace API 与应用级自定义追踪](13.26-android-trace-api-custom-tracing.md)
- [13.27 Android 17 trace、Perfetto v57 AI skill 与状态轨道](13.27-android17-perfetto-v57-ai-skill-state-tracks.md)

目录中有两篇文章共用 `13.17`，版本演进专题与 pprof 专题共用 `13.21`；阅读时应按标题和路径区分。heapprofd 生产部署以 [§26.24 heapprofd 生产级部署与权限模型](../../part5-app/ch26-observability/24-heapprofd-production-deployment-permissions.md) 为准。

## 按任务选择阅读路径

### 第一次使用 Perfetto

按 13.1 → 13.2 → 13.3 → 13.5 阅读。13.2 负责采集，13.3 解释轨道与选择区，13.5 把常见现象连接到后续专题。

### 帧卡顿与渲染

按 13.20 → 13.19 → 13.14 → 13.15 阅读。FrameTimeline 定位异常帧，FrameTracer 补 buffer 阶段，CUJ 标记场景，BufferQueue 说明 producer/consumer 阻塞。RenderThread、GPU 或 SurfaceFlinger 归因还要回到对应渲染章节。

### CPU、调度与频率

按 13.6 → 13.13 → 13.11 → 13.22 阅读。Running、Runnable 和 Sleeping 要分开统计；频率、调度区间和业务 slice 的关联使用区间连接，批量回归使用固定查询库。

### 输入、Binder 与跨进程等待

按 13.8 → 13.9 → 13.10 → 13.22 阅读。输入流水线负责确定事件身份与时间窗，Binder 标准库区分客户端等待和服务端处理，`thread_state` 补充调度与阻塞证据。

### CPU profile 与内存

按 13.12 → 13.21 → 13.22 阅读。pprof 是聚合 profile，Simpleperf protobuf 保存样本时间戳，Perfetto `linux.perf` 可以和 system trace 同轴采集。内存分析要区分 heap profile、heap graph、process counter 与 DMA-BUF。

### 应用埋点与工具集成

按应用内 SDK 专题 → 13.26 → 13.9 阅读。`android.os.Trace`、AndroidX Tracing 和 Perfetto SDK 的写入路径、文件格式与采集 session 依赖不同，选型前应确认目标是系统时间轴、独立进程内 trace 还是自定义 data source。

### 自动化与代理分析

按 13.16 → 13.22 → 13.18 → 13.27 阅读。自动分析必须保留 trace hash、分析器版本、执行 SQL、单位、结果行数和数据缺口。代理可以加快 schema 探索与查询迭代，结论仍需 trace 行、标准库语义和源码共同支持。

## 一次可复核的分析流程

1. 写出假设和所需数据源，再生成采集配置；
2. 记录设备 build fingerprint、平台 tag、内核、采集端与分析端版本；
3. 检查 `stats`、trace 时长、表是否存在及行数；
4. 用 FrameTimeline、启动 marker、输入事件或业务 slice 固定时间窗；
5. 分别检查 CPU 执行、Runnable 排队、睡眠、Binder、锁、I/O、GPU 和内存；
6. 用 SQL 保留筛选条件、身份键、单位和样本数；
7. 回到 Android 17 固定源码或对应上游 tag 验证字段与调用路径；
8. 保存原始 trace、配置、SQL、工具 hash 和结论边界。

UI 截图适合说明位置，不足以支撑可重复回归。SQL 聚合适合量化，也不能代替单帧、单事务或单调用栈的时序证据。

## 官方入口

- [Perfetto 文档](https://perfetto.dev/docs/)
- [PerfettoSQL 标准库](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Android 17 Perfetto changelog](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/CHANGELOG)
- [AndroidX Tracing 发布说明](https://developer.android.com/jetpack/androidx/releases/tracing)
