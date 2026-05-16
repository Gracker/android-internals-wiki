---
title: "InputDispatcher 反压与无响应窗口降级"
chapter: "3.7"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [input, inputdispatcher, anr, latency, backpressure]
related_chapters: ["3.1", "3.2", "3.5", "9.2", "9.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "研究素材/源码结构"
---

# 3.7 InputDispatcher 反压与无响应窗口降级

<!-- outline-start -->
## 要点

### 🔹 输入通道的天然反压点
补齐 InputDispatcher 在输入管道拥塞时的 waitQueue 积压、WOULD_BLOCK、无响应连接隔离与跨应用切换降级策略。

### 🔹 waitQueue、inboundQueue 与 ANR 计时边界
补齐 InputDispatcher 在输入管道拥塞时的 waitQueue 积压、WOULD_BLOCK、无响应连接隔离与跨应用切换降级策略。

### 🔹 目标窗口无响应后的连接隔离
补齐 InputDispatcher 在输入管道拥塞时的 waitQueue 积压、WOULD_BLOCK、无响应连接隔离与跨应用切换降级策略。

### 🔹 跨应用切换时的队列裁剪策略
补齐 InputDispatcher 在输入管道拥塞时的 waitQueue 积压、WOULD_BLOCK、无响应连接隔离与跨应用切换降级策略。

### 🔹 Perfetto / dumpsys input 的观察入口
补齐 InputDispatcher 在输入管道拥塞时的 waitQueue 积压、WOULD_BLOCK、无响应连接隔离与跨应用切换降级策略。

### 🔹 与应用主线程卡顿、Binder 阻塞的归因边界
补齐 InputDispatcher 在输入管道拥塞时的 waitQueue 积压、WOULD_BLOCK、无响应连接隔离与跨应用切换降级策略。

## 扩展

### 🔸 游戏/高频触控场景下的反压放大
待结合素材验证后展开。

### 🔸 厂商输入调度策略与可验证边界
待结合素材验证后展开。

<!-- outline-end -->

> 本节内容待加工。
