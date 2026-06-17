---
title: "GenAI 应用集成性能边界：AICore 调度、Google Intelligence API 与资源竞争"
chapter: "5.20"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: ["GenAI", "AICore", "端侧AI", "性能优化", "NPU"]
related_chapters: ["5.11", "5.13", "5.14", "5.19", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/章节深挖"
---

# 5.20 GenAI 应用集成性能边界：AICore 调度、Google Intelligence API 与资源竞争

<!-- outline-start -->
## 要点

### 🔹 锚点 1
AICore 作为 Mainline 模块的独立进程模型，Google Intelligence API 的 Binder IPC 管线，GenAI 推理请求的进程间调度开销

### 🔹 锚点 2
同步推理调用阻塞主线程的风险，异步推理的回调延迟，推理任务与 UI 渲染的 CPU 时间片争抢

### 🔹 锚点 3
GenAI 模型的 RSS 占用，模型加载/卸载的内存抖动，与 App 自身堆内存的竞争边界

### 🔹 锚点 4
GenAI 推理触发的 ADPF thermal hint，推理任务的降级策略（模型切换/量化/延迟执行），thermal throttling 恢复后的性能重置

### 🔹 锚点 5
多个 App 同时请求 GenAI 推理时的系统调度策略，NPU/GPU 时间片分配，优先级队列与公平性

## 扩展

### 🔸 扩展点 1
不同模型大小（1B/3B/7B 参数）在主流 SoC 上的推理延迟与内存占用范围

### 🔸 扩展点 2
AICore 模块在不同 Android 版本的能力差异，Google Intelligence API 的 API level 映射

<!-- outline-end -->

> 本节内容待加工。
