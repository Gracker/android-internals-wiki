---
title: "Adaptive Refresh Rate 与动态帧率控制"
chapter: "2.18"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: ['ARR', 'refresh-rate', 'VSync', 'SurfaceFlinger', 'Android-16']
related_chapters: ['2.2', '2.3', '2.4', '2.6']
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "研究素材（19/20 高分研究 feed）+ 官方文档"
---

# 2.18 Adaptive Refresh Rate 与动态帧率控制

<!-- outline-start -->
## 要点

### 🔹 固定刷新率到可变刷新率的演进动机
为什么 60Hz/120Hz 二选一不够用了；LTPO 面板的硬件能力与软件适配之间的鸿沟
### 🔹 ARR 的架构设计
DisplayManager → SurfaceFlinger → Choreographer 的三方协调；Frame Rate Override 机制；app votable refresh rate
### 🔹 Android 16 ARR API 详解
WindowAttributes#preferredDisplayModeId、setFrameRate()、Choreographer.VsyncEventData 中 refreshRate 字段的含义与用法
### 🔹 SurfaceFlinger 的帧率决策策略
多 App 同时请求不同帧率时的仲裁逻辑；层优先级（Layer Priority）与帧率选择；VsyncModulator 对 offset 的动态调整
### 🔹 在 Perfetto 中分析 ARR 行为
VSYNC-app/VSYNC-sf 动态 offset 的 Track 表现；SurfaceFlinger 的 setDesiredDisplayModeSpecs 日志；帧间隔异常的 SQL 查询
### 🔹 ARR 对功耗的影响
高帧率场景的功耗代价；Seamless Refresh Rate Switching 的硬件与软件协同；何时降帧、何时维持的策略
### 🔹 常见问题与调试
帧率切换卡顿、App 请求帧率被忽略、LTPO 与非 LTPO 设备的行为差异

## 扩展

### 🔸 Game Mode API 与 ARR 的交互
GameManager 如何影响帧率决策；游戏场景的特殊处理
### 🔸 VR/AR 场景下的固定帧率需求
为什么 VR 需要固定高帧率，ARR 如何在这些场景下让步

<!-- outline-end -->

> 本节内容待加工。
