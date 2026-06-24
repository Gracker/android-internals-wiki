
## [Task2A Gap Mining] 2026-06-25 06:04 已检查方向（无合格缺口）
- **AVF / pVM**: 偏安全隔离，性能素材不足 (9/20)
- **Wear OS 性能优化**: 受众窄，Wear OS 6 基于 Android 15 (11/20)
- **Rust in System Services**: 已有 3.8/1.25 覆盖，独立章节素材不足 (11/20)
- **Gradle / AGP 构建性能**: 偏离 App 运行时性能主线 (10/20)
- **Compose Multiplatform / KMP**: 与 Compose Android 性能高度重叠 (10/20)
- **NFC / Host Card Emulation**: 极低性能影响，素材稀缺 (7/20)
- **TelephonyManager / Radio**: 偏 telephony 层，app 开发者关注度低 (12/20)
- **Android Backup/Restore**: 非性能关键路径 (5/20)
- **Dynamic Feature Modules**: 大型 app 才用，性能素材不足 (8/20)
- **Work Profile / Enterprise**: 企业场景 niche (7/20)
- **Android Emulator Performance**: 开发工具性能，非 app 运行时 (8/20)
- **Compose Snapshot System**: 高级内部实现，独立章节分数边界 (12/20)
- **备注**: 本日第 4 轮挖掘。全书 471 小节 / 327 finalized (69.4%)。0 空 draft。31 个 draft 全部有实质内容。管线堵点在 Task6/Task9 复审（64 ready-for-review 待审核）。ch27 Performance Engineering 6 个 draft（37-58 行）内容完整度已达标但尚未进入审核管线。
## [Task9 Deep Review] 26.12 Android 版本化线上诊断能力 — 2026-06-25

- **类型**：版本差异
- **位置**：MemoryLimiter 部分
- **问题**：只提到 targetSdk ≥ 36 的应用在高 RAM 设备上受限制，但缺少具体的限制阈值计算公式和示例
- **建议**：补充具体的内存限制计算逻辑，如基于设备总 RAM 的比例公式和示例代码

- **类型**：版本差异
- **位置**：Extension 36.1 trigger 部分
- **问题**：没有明确说明如何在运行时检测 Extension 版本的具体方法
- **建议**：补充 Extension 版本检测的代码示例，如使用 PackageManager API 或 Build.SUPPORTED_ABIS 检测

- **类型**：权限边界
- **位置**：隐私、限流与采集成本部分
- **问题**：没有详细说明不同 API level 的权限要求
- **建议**：补充权限版本矩阵，说明 READ_RESTRICTED_STATS、REGISTER_STATS_PULL_ATOM 等权限在不同版本的可用性

- **类型**：数据支撑
- **位置**：排障决策表部分
- **问题**：决策表缺少不同设备在不同 Android 版本下的实际表现数据
- **建议**：补充 2-3 个典型设备（如 Pixel 6、Pixel 7、Samsung Galaxy S23）在不同 Android 版本下的实际测试结果

- **类型**：限流配置
- **位置**：ProfilingManager 限流部分
- **问题**：提到有 rate limiter，但没有具体数值
- **建议**：补充典型设备的限流阈值范围和配置方法
