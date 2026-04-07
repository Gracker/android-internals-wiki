---
title: "多窗口与桌面模式渲染性能"
chapter: "2.20"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [multiwindow, desktop-mode, split-screen, freeform, foldable, surfaceflinger, rendering]
related_chapters: ["2.6", "2.9", "2.12", "7.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "AOSP结构+官方文档+读者需求"
gap_score: 16
---

# 2.20 多窗口与桌面模式渲染性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Android 多窗口模式演进
- 分屏模式 (Split-Screen)：Android 7.0 引入，两个 App 各占半屏
- 自由窗口模式 (Freeform)：Android 7.0 引入，Chrome OS 优先使用
- 画中画 (PiP)：Android 8.0 引入，视频/导航类 App 常用
- 桌面窗口模式 (Desktop Windowing)：Android 16 GA，外接显示器场景

### 🔹 锚点 2：多窗口下 SurfaceFlinger 的合成负载
- 多个可见 App → 多个独立 Layer → 合成复杂度增长
- HWC 叠加层数上限对性能的约束（通常 4-8 层）
- 超出 HWC 能力时回退到 GPU 合成的性能影响
- 在 Perfetto 中如何观察 SurfaceFlinger 合成耗时变化

### 🔹 锚点 3：折叠屏与多 Surface 渲染
- 折叠/展开时 Activity 重建 vs 配置变更
- 多 Surface 并存时的 BufferQueue 竞争
- 屏幕尺寸变化对 Choreographer 帧节奏的影响

### 🔹 锚点 4：桌面窗口模式的渲染架构变化
- 外接显示器场景下的 Surface 独立性
- 每个窗口独立的 VSync-app 与帧率控制
- 与 ARR (Adaptive Refresh Rate) 的交互

### 🔹 锚点 5：多窗口性能分析与优化
- Perfetto 中多窗口场景的 Track 解读
- 各窗口独立的 doFrame 时间线分析
- 常见性能问题：焦点窗口丢帧、后台窗口无谓渲染
- 优化策略：生命周期感知渲染、onStop 停止绘制

### 🔹 锚点 6：Android 16/17 大屏强制适配的渲染影响
- 600dp+ 设备 orientation 锁定失效
- recreateOnConfigChanges 减少不必要的 Activity 重建
- 对渲染管线的影响：减少 Surface 销毁/重建开销

## 扩展

### 🔸 扩展点 1：Chrome OS / Android 桌面环境渲染差异
{Chrome OS 上 Android App 的渲染管线差异}

### 🔸 扩展点 2：游戏在多窗口模式下的性能
{游戏类 App 在分屏/小窗模式下的帧率和功耗表现}

<!-- outline-end -->

> 本节内容待加工。
