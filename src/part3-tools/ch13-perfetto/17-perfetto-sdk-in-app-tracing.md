---
title: "Perfetto SDK 与应用内 Trace 数据源"
chapter: "13.17"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [perfetto, tracing-sdk, in-app-tracing, custom-data-source, observability]
related_chapters: ["13.2", "13.9", "19.13", "26.3", "26.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "素材驱动/官方文档"
gap_score: 16
material_count: 4
source_refs:
  - "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Cubox/性能工具-Perfetto(4)-通过SDK抓取信息-2026-05-02.md"
  - "https://perfetto.dev/docs/instrumentation/tracing-sdk"
  - "https://perfetto.dev/docs/getting-started/in-app-tracing"
  - "https://android.googlesource.com/platform/external/perfetto/+/refs/heads/main/docs/instrumentation/tracing-sdk.md"
---

# 13.17 Perfetto SDK 与应用内 Trace 数据源

<!-- outline-start -->
## 要点

### 🔹 Perfetto SDK 和 AndroidX Tracing 的边界
说明 `androidx.tracing` 只负责写入平台 trace section，Perfetto SDK 可以让应用成为 trace producer，并支持 in-process / system 两种后端。

### 🔹 in-process 后端的采集闭环
覆盖初始化、`TrackEvent::Register()`、`TraceConfig`、`TracingSession`、`TRACE_EVENT` / `TRACE_COUNTER`、写出 `.pftrace` 的最小闭环。

### 🔹 system 后端与系统 Perfetto service 协作
解释应用只作为 producer 时，外部 `perfetto` CLI 或系统服务控制开始、停止和读取，避免应用读取跨进程系统 trace 数据。

### 🔹 自定义 data source 的适用场景
说明何时需要自定义 protobuf 数据源，如何避免把它误用成业务日志系统，以及它和 track_event 的取舍。

### 🔹 启动早期 trace 与线上触发式采集
整理 startup trace、冷启动首屏、短窗口触发、异常前后环形缓冲等场景的配置思路。

### 🔹 构建、体积和版本兼容边界
覆盖 C / C++ SDK 集成、静态库体积、NDK ABI、Android 10+ system tracing 能力、低版本 fallback。

### 🔹 隐私和数据治理
说明 trace 参数、counter、category 名称不能携带用户隐私；系统模式下应用不能读取包含其他进程信息的 trace。

## 扩展

### 🔸 C SDK 与 C++ SDK 接入差异
对比单文件 SDK、CMake 接入、符号体积、API 表达能力和团队维护成本。

### 🔸 Perfetto SDK、ProfilingManager、APM custom trace 的组合方案
把开发期、测试期、线上触发式采集拆成三类决策表。

<!-- outline-end -->

> 本节内容待加工。
