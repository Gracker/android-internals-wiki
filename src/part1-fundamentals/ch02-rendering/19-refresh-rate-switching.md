---
title: "刷新率切换与帧率适配性能"
chapter: "2.19"
status: draft
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [refresh-rate, frame-rate, SurfaceFlinger, VSync, setFrameRate, jank, rendering]
related_chapters: ["2.2", "2.3", "2.6", "2.18", "7.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "高爷专家洞察+研究素材+ARR研究"
---

# 2.19 刷新率切换与帧率适配性能

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么帧率切换会卡顿
- 帧率切换卡顿的典型场景：相机界面多任务返回桌面动画（60Hz → 120Hz）
- 不同 Surface/Window 可以有不同的 preferred refresh rate（setFrameRate() API）
- 切换过程中 Display HAL 需要重新配置显示参数（PLL 时钟、时序参数）
- 过渡期产生若干帧延迟，导致用户可感知卡顿
- 这类卡顿瓶颈在 SurfaceFlinger / Display HAL 层面，App 侧 Trace 看起来完全正常

### 🔹 锚点 2：SurfaceFlinger 的刷新率选择策略
- SurfaceFlinger 如何处理多刷新率 Surface 的合成
- refresh rate selection 箖略：多个 Layer 不同帧率时的决策逻辑
- setFrameRate() API 的工作原理与优先级
- WindowManager.setDisplayRefreshRateOverride() 的作用

### 🔹 锚点 3：Display HAL 帧率切换的硬件过渡
- Display HAL 切换刷新率时的硬件过渡时间
- PLL 时钟重配置的延迟
- 不同 SoC 平台（高通/联发科/三星）的过渡时间差异

### 🔹 锚点 4：在 Perfetto 中识别帧率切换卡顿
- Expected Timeline 出现 VSync 周期跳变的特征
- Actual Timeline 与 Expected Timeline 不对齐
- FrameTimeline 中的特征模式
- 如何区分帧率切换卡顿和其他类型的卡顿

### 🔹 锚点 5：Adaptive Refresh Rate 与帧率切换的关系
- ARR（2.18 节）与帧率切换卡顿的联系
- Android 15/16/17 中 ARR 对帧率切换的优化
- MRR (Minimum Refresh Rate) 和 preferred refresh rate 的交互

### 🔹 锚点 6：优化策略与最佳实践
- App 开发者如何避免不必要的帧率切换
- setFrameRate() 的正确使用方式
- 系统侧优化（SurfaceFlinger 的帧率切换缓冲策略）

## 扩展

### 🔸 扩展点 1：Camera App 的帧率管理最佳实践
- Camera 预览帧率与系统动画帧率的冲突处理

### 🔸 扩展点 2：游戏引擎的帧率适配策略
- 游戏场景中 setFrameRate() 的使用建议
- 游戏从 60fps 切换到 120fps 的过渡处理

### 🔸 扩展点 3：OEM 厂商对帧率切换的定制优化
- 不同厂商的 Display HAL 实现差异
- 帧率切换时的帧缓冲策略

<!-- outline-end -->

> 本节内容待加工。
