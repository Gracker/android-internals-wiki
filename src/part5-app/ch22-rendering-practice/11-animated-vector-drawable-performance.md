---
title: "AnimatedVectorDrawable 线程退化与动画卡顿"
chapter: "22.11"
status: draft
applicable_versions: "Android 7.1 (API 25) - Android 16 (API 36)"
tags: ["animated-vector-drawable", "renderthread", "animation", "jank", "ui-thread"]
related_chapters: ["2.5", "7.5", "18.2", "22.5", "22.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构"
sources:
  - type: aosp
    path: "cs.android.com frameworks/base/graphics/java/android/graphics/drawable/AnimatedVectorDrawable.java"
  - type: material
    path: "DeepResearch/2026-05-08-animatedvectordrawable-thread-degradation.md"
  - type: structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md"
---

# 22.11 AnimatedVectorDrawable 线程退化与动画卡顿

<!-- outline-start -->
## 要点

### 🔹 AnimatedVectorDrawable 的 RenderThread 与 UI 线程双路径
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 fallbackOntoUI 的触发条件
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 软件 Canvas、硬件加速与动画状态迁移
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 Perfetto 中识别动画退化的观察点
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 资源写法与运行时场景的优化策略
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

### 🔹 线上帧率监控如何标记 AVD 退化样本
{待加工：围绕该锚点补充事实、验证路径与实战判断。}

## 扩展

### 🔸 VectorDrawable 路径复杂度与 GPU 负载关系
{待补充：素材充分时展开。}

### 🔸 Lottie、属性动画与 AVD 的选型边界
{待补充：素材充分时展开。}

<!-- outline-end -->

> 本节内容待加工。
