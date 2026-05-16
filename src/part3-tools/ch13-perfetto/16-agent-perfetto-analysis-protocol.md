---
title: "Agent 辅助 Perfetto 分析协议"
chapter: "13.16"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [perfetto, trace-analysis, agent-workflow, performance-tools]
related_chapters: ["13.2", "13.10", "13.15", "15.6", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "研究素材+官方仓库"
sources:
  - type: official
    path: "https://github.com/android/skills/tree/main/profilers"
  - type: research
    path: "DeepResearch/android-skills-profilers/2026-05-16-android-skills-profilers-深度调研.md"
---

# 13.16 Agent 辅助 Perfetto 分析协议

<!-- outline-start -->
## 要点

### 🔹 协议定位：从 Perfetto 教程到可复查的 Agent 调查流程
说明 `android/skills/profilers` 与普通 Perfetto 教程的区别，明确本节关注 trace 分析流程、证据约束和停止条件，而不是重复 UI 操作教程。

### 🔹 输入约束：trace 文件、问题类型、包名与版本信息
定义 Agent 分析前必须收集的最小输入，包括 trace 路径、Android 版本、设备/ROM、目标包名、复现场景、采集配置和期望回答的问题。

### 🔹 Scratchpad 证据链：只记录已验证事实
拆解 scratchpad 的记录格式：时间窗、线程/进程、slice/counter、SQL、查询结果、排除项；强调假设与事实分离。

### 🔹 Perfetto SQL 生成守卫：schema、stdlib 与执行校验
覆盖 `trace_processor`、schema 检索、Perfetto stdlib 优先、`utid/upid`、`dur=-1`、`SPAN_JOIN`、`GLOB` 等查询稳定性规则。

### 🔹 六类调查域：CPU、Graphics、I/O、IPC、Memory、Power
把开放式 trace 分析拆成可执行的 domain hints，说明每类问题的起手查询、下一跳和常见误判。

### 🔹 Wall time 与 CPU time 分离
建立长耗时 slice 的基本判断流程：先查 `thread_state`，再区分 Running、Runnable、Sleeping、UninterruptibleSleep，避免把等待时间误判为计算开销。

### 🔹 从局部异常到全局复核
说明找到疑似瓶颈后，仍要检查全局 longest slice、D-state、Binder、FrameTimeline 和关键 counter，避免第一个异常被误认为根因。

### 🔹 输出模板：证据表、阻塞方、边界与补采建议
定义最终报告结构：问题窗口、核心证据、根因链、排除项、可信度、补采字段、下一步优化动作。

## 扩展

### 🔸 Trace 采集规划器
按启动、滑动、ANR、I/O、内存、功耗、GPU 等问题类型生成 TraceConfig/atrace category 建议。

### 🔸 Android 版本与厂商轨道差异
整理 FrameTimeline、Binder、dmabuf、power rail、sched、MTK/vendor 轨道在不同 Android 版本和厂商 ROM 上的字段差异。

### 🔸 SQL 模板测试集
为常用 Perfetto SQL 建立 smoke test，降低字段漂移、stdlib 版本差异和空结果误判。

### 🔸 源码与 trace 关联
从 trace 中的 slice、Binder 方法、native 符号继续映射到 AOSP 或业务代码路径。

<!-- outline-end -->

> 本节内容待加工。
