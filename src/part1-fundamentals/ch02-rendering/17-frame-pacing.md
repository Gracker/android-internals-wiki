---
title: "Frame Pacing Library 与帧节奏控制"
chapter: "2.17"
status: draft
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
tags: [Frame Pacing, Swappy, AGDK, 游戏性能, Adaptive Refresh Rate, 帧节奏]
related_chapters: ["2.2", "2.3", "2.9", "2.14", "7.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档 + 研究素材"
---

# 2.17 Frame Pacing Library 与帧节奏控制

<!-- outline-start -->
## 要点

### 🔹 锚点 1：帧节奏问题是什么
- 游戏渲染循环 vs 显示硬件刷新率的失配
- 短帧（渲染快于刷新率）导致帧重复显示 → stuttering
- 长帧（渲染慢于刷新率）导致掉帧 → jank
- 帧节奏不均匀的用户感知：卡顿、抖动、不流畅

### 🔹 锚点 2：Swappy 的核心设计思想
- 利用 Choreographer 同步渲染循环与 VSync
- Sync Fence 管理长帧，避免 buffer stuffing
- Presentation Time 精确控制帧提交时间
- 自动检测设备刷新率并匹配最优帧率
- 自适应刷新率支持：60Hz/90Hz 设备上 30FPS 游戏可平滑降到 45FPS

### 🔹 锚点 3：Swappy 的 API 与集成方式
- AGDK (Android Game Development Kit) 中的 Swappy 库
- OpenGL 和 Vulkan 双后端支持
- Unity 优化帧节奏设置（Project Settings checkbox）
- Unreal Engine 5.2+ 默认启用
- Android Frame Pacing Library ( androidx.graphics:graphics-core )

### 🔹 锚点 4：Swappy 与 Android 渲染管线的协作
- Swappy 在 Choreographer 回调中调度帧提交
- 与 SurfaceFlinger 的 BufferQueue 交互
- 与 Sync Fence 框架的协作
- 与 Adaptive Refresh Rate (Android 16+) 的协同

### 🔹 锚点 5：帧节奏在 Perfetto 中的分析
- FrameTimeline track 中的帧提交与呈现时间
- 如何识别帧节奏不均匀的 trace 特征
- 对比启用/禁用 Swappy 的 trace 差异

### 🔹 锚点 6：游戏引擎之外的帧节奏优化
- 非 game 场景的帧率控制需求（动画、视频、AR/VR）
- 自定义渲染循环如何正确使用 Choreographer + presentation time
- 与 Jetpack Compose 动画帧调度的对比

## 扩展

### 🔸 扩展点 1：LTPO 显示面板与帧节奏的交互
- LTPO 可变刷新率对帧节奏的影响
- Android 16 ARR API 与 Swappy 的配合

### 🔸 扩展点 2：VR/AR 场景的帧节奏要求
- VR 的 72/90/120Hz 严格帧率要求
- VR 模式下的帧提交与预测渲染

<!-- outline-end -->

> 本节内容待加工。
