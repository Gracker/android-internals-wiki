---
title: "RenderEffect 与 RuntimeShader 性能实践"
chapter: "22.10"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: ["rendereffect", "runtimeshader", "agsl", "hwui", "gpu"]
related_chapters: ["2.7", "2.10", "18.2", "22.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "素材驱动/AOSP结构"
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-rendereffect-gpu-rendering-pipeline-analysis.md"
  - type: clippings
    path: "[结构参考: Clippings/Android 性能优化 - Android 性能优化总结.md]"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RenderEffect"
  - type: official
    path: "https://developer.android.com/reference/android/graphics/RuntimeShader"
---

# 22.10 RenderEffect 与 RuntimeShader 性能实践

<!-- outline-start -->
## 要点

### 🔹 RenderEffect 的适用场景
- 模糊、颜色滤镜、AGSL 自定义像素处理
- 与传统 Bitmap 预处理的成本差异
- 适合动态效果还是静态素材预生成

### 🔹 HWUI 管线中的成本来源
- RenderNode 绑定效果后的重绘行为
- offscreen buffer 分配与额外纹理读写
- Blur 半径、区域大小和链式效果的成本

### 🔹 RuntimeShader / AGSL 的实践边界
- API 33+ 的能力范围
- uniform 更新频率与每帧成本
- Shader 编译、缓存和降级策略

### 🔹 常见 UI 效果的选型
- 毛玻璃背景
- 列表项阴影和蒙版
- 转场动画中的效果叠加

### 🔹 Perfetto 与 GPU 工具观测
- FrameTimeline 中的渲染耗时变化
- RenderThread / GPU completion 的观察点
- 配合 AGI / GPU Inspector 查纹理和 draw call

### 🔹 优化清单
- 控制效果区域
- 避免大半径实时模糊
- 把静态效果预渲染或缓存

## 扩展

### 🔸 RenderEffect 与 Hardware Layer 的交互
[待补充]

### 🔸 Compose graphicsLayer / RenderEffect 对应关系
[待补充]

### 🔸 厂商 GPU 对模糊效果的差异
[待补充]

<!-- outline-end -->

> 本节内容待加工。
