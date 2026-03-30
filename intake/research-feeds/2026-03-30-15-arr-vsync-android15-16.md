## [研究] Android 15/16 自适应刷新率 (ARR) 与 VSync 演进

- **来源**: https://developer.android.com/about/versions/16/features + https://developer.android.com/about/versions/15/features
- **作者/机构**: Google Android Developers
- **日期**: 2025-2026
- **四维评分**: 相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**: 2.3 VSync 机制 / 2.9 渲染机制的版本演进
- **映射锚点**: ARR, 自适应刷新率, VSync 离散步进, frame rate API, HWC HAL v3, RecyclerView 1.4
- **摘要**: Android 15 引入、Android 16 显著增强的自适应刷新率 (ARR) 将显示 VSync 率与刷新率解耦，使用离散 VSync 步进动态匹配内容帧率，减少功耗和卡顿。

### 关键发现

1. **ARR 核心机制**：自适应刷新率允许兼容硬件上的显示刷新率通过离散 VSync 步进 (discrete VSync steps) 动态调整到内容帧率。目标：降低功耗（低帧率时降刷新率）和消除卡顿（无需显示模式切换）。

2. **Android 16 新 API**：`hasArrSupport()` 和 `getSuggestedFrameRate(int)` 帮助 App 集成 ARR。RecyclerView 1.4 内置支持 ARR（fling 和 smooth scroll 操作时自动切换帧率）。

3. **实现要求**：需要 HWC HAL v3 (`android.hardware.graphics.composer3`) + 内核/系统层变更。设备端需要支持离散 VSync 步进的显示硬件。

4. **对 VSync 管线的影响**：ARR 意味着 VSync 周期不再固定（如 60Hz 的 16.66ms），而是在运行时动态变化。DispSync 模型需要适应变化的周期，这对帧节奏库 (Frame Pacing Library) 和 Choreographer 的调度逻辑有直接影响。

### 可直接引用段落

> Android 16 significantly improves Adaptive Refresh Rate support. ARR enables the display refresh rate on compatible hardware to dynamically adjust to the content's frame rate using discrete VSync steps. This optimization aims to reduce power consumption and minimize "jank" (inconsistent frame delivery). Android 16 provides new APIs, such as hasArrSupport() and getSuggestedFrameRate(int), to facilitate app integration with ARR.
>
> — Android 16 Developer Features Documentation

> Implementing ARR requires new Hardware Composer (HWC) HAL APIs (version 3 of android.hardware.graphics.composer3) and kernel/system changes on devices running Android 15 and later.
>
> — Android Platform Developer Guide

### 与 queue.json 联动
- 优先级调整建议：建议将 2.9 渲染机制的版本演进 priority 从 70 提升到 75
- 素材路径建议：可同时补充到 2.3 和 2.9
