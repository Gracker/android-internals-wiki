---
title: "Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数"
chapter: "13.11"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["perfetto", "sql", "span-join", "trace-processor"]
related_chapters: ["13.10", "13.6", "14.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/研究素材"
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-13-perfetto-span-join-window-function.md"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
  - type: official
    path: "https://perfetto.dev/docs/analysis/perfetto-sql-getting-started"
---

# 13.11 Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数

<!-- outline-start -->
## 要点

### 🔹 SPAN_JOIN 解决的时间重叠问题
- slice、counter、sched 三类数据的时间语义
- 为什么普通 JOIN 容易写错或放大结果
- 适合用 SPAN_JOIN 的诊断场景

### 🔹 从 counter 构造 span 视图
- 用 LEAD() 生成 dur 的基本模式
- track_id / cpu / utid 分区方式
- 最后一条 counter 的边界处理

### 🔹 PARTITIONED 约束与错误结果
- 整数分区列要求
- 同一分区内 span 不能重叠
- 重叠数据的预处理办法

### 🔹 帧 × CPU 频率关联案例
- FrameTimeline 或 UI slice 作为左表
- cpufreq counter 转 span
- 输出每帧运行期间的频率分布

### 🔹 帧 × Binder / 锁 / GC 交叉分析
- Binder transaction 与帧重叠
- 锁竞争 slice 与线程运行段重叠
- GC pause 与用户感知 jank 的关联

### 🔹 Trace Processor 标准库配合方式
- thread_slice / process_slice 视图
- sched_with_thread_process 的使用边界
- 把临时 SQL 固化成可复用 macro

## 扩展

### 🔸 SPAN_LEFT_JOIN 与 SPAN_OUTER_JOIN 的差异
[待补充]

### 🔸 SPAN_JOIN 性能成本与索引策略
[待补充]

### 🔸 在 CI 中复用复杂 Perfetto SQL
[待补充]

<!-- outline-end -->

> 本节内容待加工。
