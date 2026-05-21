---
title: "线上存储、I/O 与 SQLite 可观测性"
chapter: "26.16"
status: draft
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [observability, storage, io, sqlite, matrix]
related_chapters: ["24.1", "24.2", "24.12", "26.3", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "Clippings参考书/研究盲区/官方文档/AOSP结构"
---

# 26.16 线上存储、I/O 与 SQLite 可观测性

<!-- outline-start -->
## 要点

### 🔹 观测对象边界
区分文件 I/O、数据库操作、存储容量、文件损坏与资源泄漏，先确定每类问题应采集的事件、字段和触发条件。

### 🔹 I/O 采集路径选择
对比 Java Hook、Native Hook、插桩、Perfetto/ftrace 的覆盖范围、成本和线上可用边界。结构参考：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 14.md]

### 🔹 不良 I/O 规则模板
整理主线程 I/O、小 buffer 高频读写、重复读、文件句柄泄漏等规则，说明阈值如何按设备档位和业务场景调整。

### 🔹 SQLite 耗时、损坏与查询计划
覆盖 SQLite/Room 的慢查询、busy、损坏、索引缺失与 `EXPLAIN QUERY PLAN` 本地验证路径。结构参考：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 17.md]

### 🔹 存储容量与文件损坏指标
建立文件总量、文件数、目录树剪枝、CRC 校验、损坏率和远程清理策略的采集模板。结构参考：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 16.md]

### 🔹 上报、采样与隐私边界
说明路径脱敏、SQL 参数脱敏、采样率、批量上报、弱网缓存和用户隐私边界。

### 🔹 与现有章节的分工
定位为线上可观测性与诊断：文件 I/O 优化策略详见 24.1，SQLite/Room 性能优化详见 24.2，指标采集框架详见 26.3，线上排查流程详见 26.5。

## 扩展

### 🔸 Matrix I/O Canary 与 SQLiteLint
补充开源方案的接入边界、AGP 版本风险、Hook 覆盖范围和误报处理。

### 🔸 AndroidX SQLite/Room 新版本诊断能力
跟踪 AndroidX SQLite release notes 中 extended error codes、BundledSQLiteDriver 性能变更和 Room 诊断能力。

### 🔸 Perfetto 文件系统 trace 与线上指标对照
补充线下 Perfetto 证据如何映射到线上 I/O 事件字段。

<!-- outline-end -->

> 本节内容待加工。
