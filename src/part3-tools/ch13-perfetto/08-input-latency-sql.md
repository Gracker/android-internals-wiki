---
title: "Perfetto 输入延迟 SQL 深度分析"
chapter: "13.8"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ['Perfetto', 'SQL', 'input-latency', 'android.input', 'trace-analysis']
related_chapters: ['3.1', '3.4', '13.3', '13.5']
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "研究素材（Perfetto android.input SQL 模块研究 feed）"
---

# 13.8 Perfetto 输入延迟 SQL 深度分析

<!-- outline-start -->
## 要点

### 🔹 android.input 模块的 SQL 表结构
input_events、input_connections 等核心表的 schema；字段含义与版本差异
### 🔹 端到端输入延迟的量化查询
从 kernel touch event → InputDispatcher → App doFrame 的全链路时间计算 SQL
### 🔹 InputDispatcher 延迟分解
dispatching_latency、wait_connection_response 等指标的 SQL 提取；ANR 前的输入队列堆积分析
### 🔹 Choreographer 与 Input 的时序关联
将 input_event 时间戳与 doFrame callback 对齐；input → vsync → render 的流水线延迟 SQL
### 🔹 常用 SQL 模板集
按场景分类的即用型 SQL 查询（滑动卡顿输入分析、ANR 输入超时分析、冷启动输入响应分析）
### 🔹 与 13.5 专题解读的衔接
本节 SQL 方法如何补充 13.5 的可视化分析方法；何时用 SQL、何时用 UI

## 扩展

### 🔸 自定义 input trace config
如何配置 Perfetto TraceConfig 以捕获完整的输入链路数据；debug-level tracing 的开销
### 🔸 批量 Trace 的输入延迟对比
跨版本、跨设备的输入延迟 SQL 对比分析方法

<!-- outline-end -->

> 本节内容待加工。
