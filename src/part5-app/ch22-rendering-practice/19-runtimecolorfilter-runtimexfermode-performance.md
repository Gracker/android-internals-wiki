---
title: "RuntimeColorFilter 与 RuntimeXfermode 性能实践"
chapter: "22.19"
status: draft
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [agsl, runtimecolorfilter, runtimexfermode, gpu, android16]
related_chapters: ["2.10", "18.2", "22.5", "22.10", "22.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-26"
gap_source: "官方文档/AOSP结构/章节深挖"
gap_score: "16/20"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
  - type: official
    path: "https://developer.android.com/develop/ui/views/graphics/agsl/using-agsl"
---

# 22.19 RuntimeColorFilter 与 RuntimeXfermode 性能实践

<!-- outline-start -->
## 要点

### 🔹 Android 16 AGSL 绘制 API 的新增边界
区分 RuntimeShader、RuntimeColorFilter、RuntimeXfermode 三类能力，说明 ColorFilter 与 Xfermode 各自进入绘制管线的位置。

### 🔹 适合实时处理的效果类型
覆盖 threshold、sepia、hue saturation、局部蒙版和自定义混合，区分简单颜色处理与复杂采样效果。

### 🔹 Shader 编译、uniform 更新与缓存
设计 shader 对象复用、参数更新频率、线程归属和动画帧内开销的检查清单。

### 🔹 与 RenderEffect / Hardware Bitmap 的选型关系
说明何时直接挂到 draw call，何时使用 RenderEffect，何时预生成 Bitmap 或 RenderNode 缓存。

### 🔹 GPU、内存带宽与离屏渲染风险
围绕作用区域、过度绘制、纹理读写和低端 GPU 差异建立验证方法。

### 🔹 兼容性与降级路径
处理 API 36 以下设备、厂商 GPU 差异、效果关闭和远程配置策略。

## 扩展

### 🔸 AGSL 单元测试与截图回归
[待补充]

### 🔸 RuntimeXfermode 与传统 PorterDuff 语义对照
[待补充]

### 🔸 Compose graphicsLayer / drawWithCache 接入方式
[待补充]

<!-- outline-end -->

> 本节内容待加工。
