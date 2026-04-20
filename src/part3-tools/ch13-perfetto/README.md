---
title: "第 13 章：Perfetto"
chapter: "13.0"
section: "13.0"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-21"
last_verified_against: "ch13 README + 13.1-13.10 目录 + DeepResearch/Perfetto 2026 与 AndroidX Tracing 2.0"
confidence: medium
sources:
  - type: official
    path: "https://perfetto.dev/docs/"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Perfetto 2026 架构级深度技术分析  .md"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/AndroidX Tracing 2.0 架构级深度技术分析 .md"
pipeline_stage: task6_pending
task2b_result: fixed
task2b_state: fixed
task6_state: revisiting
task9_state: pending
---

# 第 13 章：Perfetto

Perfetto 已经不只是“抓一份 Trace 再手动看图”的工具。本章覆盖的是 Android 10 到 Android 17 这条主线里，Perfetto 在采集、可视化、SQL 分析和平台接入上的完整工作流。

到 2026 年，这套体系有两条很明显的扩展方向。系统侧，`traced` / `traced_probes`、Mainline APEX 和标准 SQL 模块把采集、存储、分析拆成了可独立演进的层；像 Android 16 的 UprobeStats 这类 eBPF 动态埋点工具，也开始把“不改应用代码、直接看用户态函数耗时”带进 Android 追踪体系。应用侧，AndroidX Tracing 2.0 把进程内 TracePacket 发射、协程上下文传播和 host JVM trace 带进同一套 Perfetto 数据模型，适合做协程归因和非生产环境验证。

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

## 阅读顺序建议

- 第一次接触 Perfetto，按 13.1 → 13.3 → 13.5 读，先建立 UI 和专题分析的基本视角。
- 需要稳定抓 Trace 或处理大文件，接着看 13.2、13.4、13.7。
- 需要把问题量化到 SQL，重点看 13.8、13.10。
- 需要理解采集路径和扩展 tracing 能力，重点看 13.9，再回看 13.7 里的高级用法。

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
