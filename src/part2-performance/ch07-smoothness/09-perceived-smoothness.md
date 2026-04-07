---
title: "感知流畅性：步幅波动与无掉帧卡顿"
chapter: "7.9"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [smoothness, step-jitter, perceived-performance, no-jank-stutter, animation, OverScroller]
related_chapters: ["7.1", "7.2", "2.4", "3.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "高爷专家洞察+研究素材"
---

# 7.9 感知流畅性：步幅波动与无掉帧卡顿

<!-- outline-start -->
## 要点

### 🔹 锚点 1：无掉帧卡顿的定义与现象
- "无掉帧卡顿"——FrameTimeline 不标红，所有帧都在预算时间内完成，但用户仍然感觉"卡卡的"
- 问题的本质不是帧率，而是「每帧位移量（step size）」的不均匀
- 用户在连续动画中建立的是对运动轨迹的预期，而不是对帧间隔的预期
- 相邻帧之间的位移差异过大时，视觉系统感知到「不连贯」——即使帧率稳定在 120fps
- 典型场景：多任务上划回桌面，窗口动画前期变化速度过快，前后帧画面大小出现明显变化

### 🔹 锚点 2：步幅波动的技术成因
- 动画插值算法（interpolator）对步幅均匀性的影响
- OverScroller / SpringAnimation 等动画引擎的位移计算原理
- 手势速度到动画速度的映射函数的突变点
- 物理模拟的时间步长不稳定

### 🔹 锚点 3：VSync 时间精度与位移计算
- Android 列表滑动中，计算帧距离使用 VSync 时间的 ms（取整后的毫秒值）而非纳秒原始值
- 时间精度损失链路：Choreographer.getFrameTimeNanos() → 动画引擎 → OverScroller
- 在 120Hz 下（VSync 周期 8.33ms），±1ms 的波动意味着约 12% 的帧间时间差异
- 这种微小的波动传递到位移计算后，导致列表每帧滚动像素数不均匀
- AOSP 中 OverScroller / Scroller 的时间精度处理源码分析

### 🔹 锚点 4：帧率稳定性 ≠ 步幅均匀性
- 帧率稳定的 120fps 并不保证流畅体验
- 帧率稳定性与步幅均匀性是两个独立维度
- 「视觉惯性与帧率稳定性」概念辨析

### 🔹 锚点 5：在 Perfetto 中量化步幅波动
- 非标准指标，需要自定义分析
- 如何从 FrameTimeline 数据推导每帧位移量
- 自定义 SQL 查询示例
- 识别 step-size jitter 的 Trace 特征

### 🔹 锚点 6：优化策略
- 动画插值器的选择对步幅均匀性的影响
- 使用纳秒级时间戳计算的可行性
- 厂商优化案例（如直接使用纳秒时间戳计算）
- 与视觉惯性模型结合的优化方向

## 扩展

### 🔸 扩展点 1：OverScroller 源码级时间精度分析
- AOSP OverScroller 的 computeScrollOffset() 实现细节
- 是否有厂商对此做过深度优化

### 🔸 扩展点 2：视觉感知模型与流畅性评估
- 人类视觉系统对运动不均匀性的感知阈值
- 学术研究中关于 perceived smoothness 的量化方法

### 🔸 扩展点 3：Compose 动画中的步幅控制
- Jetpack Compose 动画框架对步幅均匀性的处理
- Compose 与 View 系统在动画精度上的差异

<!-- outline-end -->

> 本节内容待加工。
