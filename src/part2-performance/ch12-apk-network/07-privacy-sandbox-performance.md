---
title: "Privacy Sandbox API 性能影响：Topics、Protected Audiences 与 Attribution Reporting"
chapter: "12.7"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: ["PrivacySandbox", "Topics", "ProtectedAudiences", "网络性能", "广告"]
related_chapters: ["12.2", "12.4", "21.10", "25.10"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/AOSP结构"
---

# 12.7 Privacy Sandbox API 性能影响：Topics、Protected Audiences 与 Attribution Reporting

<!-- outline-start -->
## 要点

### 🔹 锚点 1
Privacy Sandbox 运行时架构，API 调用链路与进程模型，与标准网络请求的性能差异

### 🔹 锚点 2
Topics 分类推断的计算开销，本地 taxonomy 查询性能，缓存策略与冷启动延迟

### 🔹 锚点 3
Custom Audience 模型存储与检索，on-device auction 执行的 CPU/内存开销，竞价超时与降级策略

### 🔹 锚点 4
事件级报告与汇总报告的注册开销，source/trigger 匹配性能，延迟报告对网络调度的聚集效应

### 🔹 锚点 5
Privacy Sandbox SDK 在独立 SandboxedProcess 中运行的 IPC 开销，跨进程数据传输性能边界

## 扩展

### 🔸 扩展点 1
WebView 中 Privacy Sandbox API 的执行路径差异与渲染性能影响

### 🔸 扩展点 2
不支持 Privacy Sandbox 的设备上的回退性能，兼容模式的开销

<!-- outline-end -->

> 本节内容待加工。
