---
tags:
  - android
  - power
  - research
---

## [研究] Android Dynamic Performance Framework (ADPF) 与游戏性能优化体系

- **来源**: https://developer.android.com/games/optimize/performance#adpf
- **作者/机构**: Google Android Team + MediaTek
- **日期**: 2026-02-26（文档最后更新）
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 8.9 Android 游戏性能与 Game Mode/State API
- **映射锚点**: ADPF Thermal API、Performance Hint Session、Game Mode Interventions、AGDK 工具链
- **摘要**: Android Dynamic Performance Framework (ADPF) 是 Google 为移动游戏提供的系统级性能优化框架，包含 Thermal API（热状态监控）、Performance Hint Session API（CPU 调度提示）、Game Mode API（性能/省电模式切换）和 Game State API（游戏状态通信）。2025-2026 年重点增强是与 MediaTek 的 MAGT 集成，提供更精细的热数据反馈。

### 关键发现

1. **ADPF Thermal API** 允许游戏实时监控设备热状态，主动调整图形负载（分辨率、阴影、粒子效果），在设备过热前降频，而非被动接受系统 thermal throttling。这种主动式热管理与传统的被动降频相比，能保持更稳定的帧率。

2. **Performance Hint Session API** 让游戏向系统报告目标帧时间和实际帧时间，系统据此优化 CPU 核心分配策略（如将关键线程调度到大核）。Android 15 新增 Power Efficiency Mode，允许线程在安全时优先功耗效率。

3. **MediaTek MAGT 集成**：Google 与 MediaTek 合作将 ADPF 与 MediaTek Adaptive Gaming Technology (MAGT) 对接，提供更丰富的热数据（芯片级温度而非系统级），实测数据显示帧率提升 57%、功耗降低。这是 OEM 级优化首次通过标准化 API 暴露给游戏开发者。

4. **Profile-Guided Optimization (PGO)** 已集成到 AGDE（Android Game Development Extension for Visual Studio），基于运行时数据优化代码路径，CPU 开销降低约 5%。AGDK v25.1.101（2025年9月）和 v26.1.102（2026年3月）持续更新。

5. **Game Mode Interventions**：OEM 可以对不再积极更新的游戏施加游戏专属优化（如通过调整 backbuffer 大小降低 GPU 负载、调整处理器使用稳定帧率），开发者可选择自行实现或退出。

### 可直接引用段落

> The Android Dynamic Performance Framework (ADPF) enables games to monitor device thermal state and dynamically adjust workloads before the device reaches thermal throttling. The Thermal API provides headroom percentage (0-100) indicating how close the device is to thermal limits, while the Performance Hint Session API allows games to communicate target and actual workload durations to the scheduler, enabling more effective CPU core assignment strategies. In Android 15, the Power Efficiency Mode lets threads prioritize power efficiency over raw performance when safe to do so.
>
> — Source: https://developer.android.com/games/optimize/performance

> Google 的研究表明，有效使用 ADPF 的游戏可以实现最高 57% 的帧率提升和显著的功耗降低。这与 MediaTek 的 MAGT (MediaTek Adaptive Gaming Technology) 集成后，游戏可以获得芯片级的热数据反馈，而非传统的系统级温度监控。
>
> — Source: https://developer.android.com/games/gamemode/gamemode-api (2026-02-26 更新)

### 与 queue.json 联动

- 优先级调整建议：8.9 的 priority 维持 80，但此素材为该章节提供了核心系统级 API 覆盖
- 素材路径建议：追加到 8.9 的 material_paths，可补充 ADPF Thermal + Hint Session 源码分析
- 交叉引用：与 2.17 Frame Pacing Library（Swappy 同属 AGDK）、5.11 NPU/GPU 加速（GPU 调度相关）、11.5 Wakelock（后台功耗管理）直接关联
