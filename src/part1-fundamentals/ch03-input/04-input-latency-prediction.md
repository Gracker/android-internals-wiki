---
title: "输入延迟与预测输入技术"
chapter: "3.4"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [input, latency, touch, prediction, input-delay]
related_chapters: ["3.1", "3.2", "2.3", "8.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "章节深挖+读者需求"
---

# 3.4 输入延迟与预测输入技术

<!-- outline-start -->
## 要点

### 🔹 锚点 1：输入延迟的端到端模型
- 从触控 IC 发出中断到像素点亮的完整链路
- 输入延迟的四个阶段：硬件采样 → 内核处理 → 系统分发 → 渲染显示
- 各阶段的典型耗时（120Hz 屏幕为例）
- 与 VSync 对齐带来的额外延迟分析

### 🔹 锚点 2：触控事件在内核层的处理
- 触控 IC → I2C/SPI 中断 → IRQ handler → input subsystem
- evdev 事件从 /dev/input/eventX 到 InputDispatcher 的路径
- 触控固件（firmware）对延迟的影响
- 如何在 Perfetto 中追踪 kernel 到 userspace 的输入延迟

### 🔹 锚点 3：InputDispatcher 的延迟优化
- InputDispatcher 的分发策略与窗口焦点管理
- 输入事件过滤（InputFilter）和拦截（Policy）的开销
- 输入事件的 ANR 超时机制（5 秒）与延迟监控
- Android 16/17 InputDispatcher 的改进

### 🔹 锚点 4：预测输入与触控预测（Touch Prediction）
- Google 的触控预测 ML 模型原理
- MotionEvent.getHistorical 系列方法的使用
- 预测补偿对滑动流畅性的改善
- 预测输入的局限性：错误预测导致画面抖动

### 🔹 锚点 5：输入延迟在 Perfetto 中的分析方法
- 输入事件的 Track 识别（InputLatency track）
- 从 input_event 到 doFrame 的时间差计算
- 输入延迟与帧延迟的关联分析
- 实战案例：识别输入延迟的瓶颈阶段

### 🔹 锚点 6：降低输入延迟的优化策略
- 游戏模式（Game Mode）对输入优先级的提升
- InputTransport 的异步模式 vs 同步模式
- Choreographer 与输入事件的调度优化
- OEM 层面的触控延迟优化（采样率、报点率）

## 扩展

### 🔸 扩展点 1：手写笔（Stylus）的延迟特性
- Stylus 输入的特殊处理路径
- Samsung S Pen / Google Pixel Pen 的延迟差异
- 低延迟渲染模式（Front Buffer Rendering）

### 🔸 扩展点 2：Android 17 Predictive Back 的输入关联
- Predictive Back 手势的输入延迟特性
- 返回手势动画的帧同步机制

<!-- outline-end -->

> 本节内容待加工。
