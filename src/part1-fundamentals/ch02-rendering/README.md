---
title: "渲染系统总纲"
chapter: "2.0"
section: "2.0"
status: ready-for-review
drafted_date: "2026-04-23"
drafted_by: "openclaw-task2b"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-23"
last_verified_against: "ch02-rendering 目录结构、AOSP android-16.0.0_r1 渲染流程说明、external review 资产"
confidence: medium
tags: [rendering, SurfaceFlinger, BufferQueue, BLAST, sync-fence, FrameTimeline, ARR]
pipeline_stage: task6_pending
last_task2b_at: "2026-05-09T22:40:00+08:00"
task6_state: revisiting
reviewed_date: "2026-04-23"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task9_state: pending
task2b_state: fixed
task2b_result: fixed
task9_result: needs-rework
last_task9_at: "2026-04-28T14:33:59+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-04-28"
---

# 第 2 章：渲染系统

Android 里最常见的性能体感问题，很多都要回到渲染流程。列表掉帧、过渡动画发飘、首帧晚、SurfaceView 黑边、高刷切换不稳，排查时都会碰到同一组节点：`Choreographer`、`RenderThread`、`SurfaceFlinger`、`BufferQueue / BLAST`、`Sync Fence`、`Display HAL`。

这一章把“App 产出一帧”到“面板显示这一帧”之间的路径拆开。读完整章，应该能回答三件事：问题落在 App、系统合成还是显示流程；Perfetto 里该先看哪条轨道；Android 12 到 17 之间哪些渲染变化改变了分析方法。

## 本章内容

### 基础主流程：从 UI 线程到 SurfaceFlinger
- `2.1` Android 渲染架构全景：先把 App、RenderThread、SurfaceFlinger、HWC 放到同一张图里
- `2.2` 帧率与刷新率：区分内容产出速度和屏幕刷新节奏
- `2.3` VSync 机制：理解 `VSYNC-app`、`VSYNC-sf` 和 phase offset
- `2.4` Choreographer 与渲染流水线：把 `doFrame`、FrameTimeline 和 deadline 放到同一套时间线上
- `2.5` MainThread 与 RenderThread 协作：看 UI 线程和渲染线程怎样分工
- `2.6` SurfaceFlinger 与合成：看 layer 收集、合成决策和提交路径

### 经典瓶颈与版本演进
- `2.7` Hardware Layer：适用场景、缓存收益和副作用
- `2.8` 过度绘制：定位 GPU 填充浪费和无效像素工作
- `2.9` 渲染机制的版本演进：梳理 Android 早期 View 渲染到 FrameTimeline / 高刷时代的变化

### GPU、缓冲区与同步基础设施
- `2.10` GPU 渲染深入：Skia Graphite 后端、GPU 提交流程、带宽瓶颈与标准化利用率轨道
- `2.11` Flutter 渲染管线与性能：Impeller 渲染后端、16KB 合规适配与原生管线性能分析方法
- `2.12` Window Manager Service 与窗口管理：理解窗口层级、动画和可见性变化
- `2.13` 图形缓冲区管理（BufferQueue）：看 producer/consumer、槽位和背压
- `2.14` 图形 API 演进与选择策略：Vulkan 1.4 必选扩展、ANGLE 强制化与 WebGPU 前景
- `2.15` DMA-BUF、Gralloc 与跨进程图形内存共享：看 GraphicBuffer 在进程间如何流转
- `2.16` Sync Fence 框架与帧同步机制：定位 GPU 等待、buffer release 和合成阻塞

### 帧节奏、高刷与刷新率仲裁
- `2.17` Frame Pacing Library 与帧节奏控制：看游戏和高帧率内容如何稳住 cadence
- `2.18` Adaptive Refresh Rate：理解 Android 15/16 之后的 ARR 能力与 App 接口
- `2.19` 刷新率切换与帧率适配性能：定位 60Hz / 120Hz 切换、Display policy 和 SurfaceFlinger 仲裁

### 特殊形态与现代渲染主题
- `2.20` 多窗口与桌面模式渲染性能：看多层合成、大屏和桌面形态的额外成本
- `2.21` 文字渲染性能：补齐文本布局、字形缓存、PrecomputedText 和 GPU 文本路径

`2.13`、`2.16`、`2.18`、`2.19` 是 Android 12-16 渲染分析里最容易反复回查的四节。BLAST、FrameTimeline、高刷仲裁和 ARR 都落在这组章节里。

## 阅读建议

- 想先拿到完整主流程：`2.1 → 2.3 → 2.4 → 2.5 → 2.6`
- 想排查 BufferQueue、release 卡住、合成迟到：`2.1 → 2.13 → 2.16 → 2.6`
- 想分析高刷、帧率抖动和切换卡顿：`2.2 → 2.17 → 2.18 → 2.19`
- 想进入 Flutter / SurfaceView / WebView / Camera 这类特殊渲染路径，第 18 章之前最好先补 `2.6`、`2.13`、`2.16`、`2.18`
- 想先看版本演进，再回头补源码细节：`2.9 → 2.13 → 2.16 → 2.19 → 2.21`
