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

如果整本书里只能挑一个最应该反复回来的工具章节，那大概率就是这一章。

原因很简单：Perfetto 不是一个“看图工具”，而是一整套观察 Android 运行时的方式。  
渲染、输入、启动、ANR、调度、锁竞争、Binder、I/O，只要问题开始跨线程、跨进程、跨系统层级，最后几乎都会回到同一根时间线上来。

这一章的目标是带着读者建立三层能力：

- 先知道 Perfetto 到底是什么
- 再知道怎样把 trace 抓对
- 最后知道怎样从图、从 SQL、从专题分析里拿到真正能落手的判断

到 2026 年，这套体系还有两个明显扩展方向。系统侧，`traced` / `traced_probes`、Mainline APEX 和标准 SQL 模块让采集、存储、分析拆成了可以独立演进的层；应用侧，AndroidX Tracing 2.0 又把进程内 TracePacket、协程上下文传播和 host JVM trace 拉进了同一个 Perfetto 数据模型。  
但对大多数读者来说，第一步仍然是先学会把一份 trace 看明白。

## 本章内容

- 13.1 Perfetto 简介与演进
- 13.2 Trace 抓取
- 13.3 Perfetto View 解读
- 13.4 命令行打开超大 Trace
- 13.5 专题解读
- 13.6 线程 CPU 状态分析
- 13.7 Perfetto 的高级用法
- 13.8 Perfetto 输入延迟 SQL 深度分析
- 13.9 Android Tracing 基础设施：atrace、ftrace 与 Perfetto 数据采集原理
- 13.10 Perfetto SQL 性能分析实战手册
- 13.11 Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数
- 13.12 Perfetto Profile 导入与 Flamegraph 分析
- 13.13 Perfetto CPU 频率与 DVFS 关联分析
- 13.14 Perfetto DataGrid 与 Jank CUJ 标准库
- 13.15 BufferQueue 阻塞的 Perfetto 识别
- 13.16 Agent 辅助 Perfetto 分析协议
- 13.17 Android 17 Perfetto 数据源边界与验证

## 阅读顺序建议

- 第一次接触 Perfetto，按 13.1 → 13.3 → 13.5 读，先建立 UI 和专题分析的基本视角。
- 需要稳定抓 Trace 或处理大文件，接着看 13.2、13.4、13.7。
- 需要把问题量化到 SQL，重点看 13.8、13.10、13.11、13.13。
- 需要理解采集路径和扩展 tracing 能力，重点看 13.9、13.12、13.16，再回看 13.7 里的高级用法。
- 需要分析 FrameTimeline、Jank CUJ 或 BufferQueue 阻塞，重点看 13.14、13.15。

如果你是在真实排障中第一次翻到这一章，最实用的方式通常是：

1. 先看 `13.3`，知道界面里到底在看什么。
2. 再看 `13.2`，把 trace 抓对。
3. 然后根据具体问题，回到 `13.5`、`13.6`、`13.8` 或 `13.10`。

这样读，效率通常比一上来先看架构史要高。

## 延伸阅读

### Perfetto 2026 架构级深度技术分析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Perfetto 2026 架构级深度技术分析  .md
- 类型：DeepResearch 调研结果
- 摘要：覆盖 Perfetto v51-v54 与 Android 13-16 的架构演进，串起 traced、traced_probes、Mainline APEX、Trace Summary v2、FrameTimeline/CUJ/monitor contention 标准库以及主要 data source，是 2026 版 Android trace 体系总览与检索入口。
- 注入时间：2026-04-20
- 价值：信息面最全，适合作为 Perfetto 章节的年度更新型参考资料。

### AndroidX Tracing 2.0 架构级深度技术分析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/AndroidX Tracing 2.0 架构级深度技术分析 .md
- 类型：DeepResearch 调研结果
- 摘要：围绕 AndroidX Tracing 2.0 alpha05，拆解 Tracer、TraceDriver、TraceSink 新对象模型、协程上下文传播、纯 Kotlin Perfetto TracePacket 发射路径，以及与 1.x、Benchmark、Studio Profiler 的边界。
- 注入时间：2026-04-21
- 价值：适合和 13.7、13.9 一起看，判断应用侧 tracing 新能力当前能做什么、还不能做什么。
