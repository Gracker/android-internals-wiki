---
tags:
  - android
  - startup
  - research
---

## [研究] Android 16 云端编译：Baseline Profiles + Startup Profiles 的编译优化全链路

- **来源**：https://developer.android.com/topic/performance/baselineprofiles + Android Developers Blog (Android 16 Cloud Compilation)
- **作者/机构**：Google Android Team
- **日期**：2025-2026
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**：8.7 Baseline Profiles 与编译优化实践
- **映射锚点**：Baseline Profiles 机制、Startup Profiles 与 DEX Layout、dex2oat 编译流程、云端编译（Android 16 新特性）、AutoFDO 联动
- **摘要**：Android 16 引入云端编译（Cloud Compilation），将 dex2oat 从设备端迁移至 Google Play 云端，通过 Secure Dex Metadata (SDM) 文件下发预编译产物。Baseline Profiles 和 Startup Profiles 共同指导 AOT 编译，后者专注启动路径的 DEX 布局优化，可将启动速度额外提升 15-30%。

### 关键发现

1. **Baseline Profiles 量化数据**：首次启动代码执行速度提升约 30%。Meta 报告各项关键指标提升达 40%。Vodafone 测试冷启动时间降低超 20%（从 2.42s 到 1.98s），特定页面 jank 帧减少 38.7%。
2. **Startup Profiles 的 DEX Layout 优化**：AGP 8.1 引入、8.3 默认启用。Startup Profiles 将启动关键代码集中在主 classes.dex 中，减少页面换入和 I/O 开销，在 Baseline Profiles 基础上额外提升 30% 启动性能。
3. **Android 16 云端编译**：dex2oat 在 Google Play 服务端执行，编译产物以 SDM 文件形式下发到设备。低端设备受益最大——安装时间大幅缩短，安装后无需等待设备端编译。
4. **AGP 8.2+ R8 重写增强**：R8 对 Baseline Profile 规则的重写可将覆盖率提升约 30%，整体性能额外提升 15%。

### 可直接引用段落

> Baseline Profiles inform the Android Runtime (ART) which code needs to be AOT compiled, bypassing slower Just-In-Time (JIT) compilation during initial app launches. This significantly speeds up execution.
>
> Startup Profiles specifically optimize the DEX layout at compile time. The build system utilizes Startup Profiles to reorder DEX bytecode, arranging startup-critical code sequentially in the primary .dex file. This prevents loading multiple DEX files during startup, reducing page faults. Startup Profiles can lead to a 15% to 30% faster app startup compared to using Baseline Profiles alone.
>
> Android 16 introduces cloud compilation: pre-compiled application artifacts are downloaded from Google Play as Secure Dex Metadata (SDM) files, bypassing the need for on-device dex2oat execution during installation.

### 与 queue.json 联动
- 优先级调整建议：建议将 8.7 的 priority 从 80 提升到 90，因为 Android 16 云端编译是编译优化链的核心新特性
- 素材路径建议：可补充到 8.7 的 material_paths，同时关联 1.7 ART 编译、1.12 AutoFDO