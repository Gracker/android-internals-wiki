## [研究] Android 17 ANGLE 强制 + Vulkan 1.4 + OpenGL ES 淘汰路线（2025-2026）

- **来源**: https://android-developers.googleblog.com/ (Vulkan as official Android graphics API) + https://source.android.com/docs/core/graphics/angle
- **作者/机构**: Google / Android 开发者团队
- **日期**: 2025-03 ~ 2026-Q2
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**: 2.14 图形 API 演进与选择策略 / 2.9 渲染机制的版本演进 / 14.8 GPU 图形调试与分析工具
- **映射锚点**: OpenGL ES → Vulkan 迁移策略、ANGLE 兼容层机制、Vulkan Profiles (AVP 2025)、渲染 API 选型决策树
- **摘要**: Google 于 2025 年 3 月宣布 Vulkan 为 Android 官方图形 API。Android 16 新设备强制 Vulkan 1.4，ANGLE 从 allowlist 转向 denylist（Android 17 全面 denylist）。OpenGL ES 进入维护模式，通过 ANGLE→Vulkan 翻译层运行。Android Vulkan Profile 2025 定义设备能力基线。WebGPU Jetpack 库于 2025 年底发布。

### 关键发现
1. **ANGLE 策略演进时间线**：Android 16（2025.06）新设备 ANGLE allowlist → Android 17（2026.06）新设备 ANGLE denylist（默认全部通过 ANGLE，仅排除名单中的应用使用原生 GLES 驱动）。注意：旧设备升级到 Android 17 不受 denylist 强制约束
2. **Vulkan 1.4 强制要求**：Android 17（API 37）新设备 SoC 必须支持 Vulkan 1.4，Vulkan 成为 GPU HAL 层的基础
3. **AVP 2025 (Android Vulkan Profile 2025)**：定义了活跃 Android 设备上的 Vulkan 扩展/特性/格式/限制集合，包含额外内存特性、细粒度浮点控制、GPU query 重置、标准化像素格式
4. **WebGPU Jetpack 库**：2025 年底以 Jetpack 库形式发布，底层走 Vulkan；后续将直接集成到 Android 系统中，简化 GPU 访问
5. **开发者迁移策略**：Vulkan 通过 NDK 开发；RenderScript → Vulkan Compute Shader 迁移；开发者需自行处理 pipeline 复用、内存类型选择、descriptor set 分组、pre-rotation 等优化（不做优化可能比 GLES 更慢）

### 可直接引用段落
> With the release of Android 17 (API level 37), new devices will be required to support Vulkan 1.4. Furthermore, Android 17 will mandate ANGLE for most applications on new devices. This transition means moving from an allowlist, where only specific applications utilized ANGLE, to a denylist, where all applications will use ANGLE unless explicitly excluded. ANGLE serves as a compatibility layer, translating OpenGL ES calls to Vulkan, thus providing a more consistent graphics experience across diverse hardware. While OpenGL ES will continue to be supported, it will primarily function through ANGLE and is no longer undergoing active feature development.

### 与 queue.json 联动
- 优先级调整建议：建议 §2.14 图形 API 演进与选择策略保持 priority 80，本素材覆盖了该章节核心内容
- 素材路径建议：作为 §2.14 的核心素材，§2.9 版本演进章节的 ANGLE/Vulkan 部分也可引用
