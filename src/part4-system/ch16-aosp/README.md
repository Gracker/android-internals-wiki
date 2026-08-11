# 第 16 章：AOSP 性能优化

AOSP、system service、ROM 与平台侧优化可以直接改变系统路径和策略。

应用侧通常在既有接口与策略内降低成本，系统侧还需要评估设计约束、兼容性、整机收益和回归风险。

## 内容索引

- [16.1 AOSP 性能优化的分层方法](01-google-optimization.md)
- [16.2 各 Android 版本性能变更追踪](02-version-changes.md)
- [16.3 AOSP 源码编译与调试环境](03-aosp-build.md)
- [16.4 Android 17 Kernel 6.18 性能机制与验证](04-android17-kernel618-performance.md)
- [16.5 Android 17（API 37）性能行为变更与适配方法](05-android17-api37-performance-changes.md)
- [16.6 Profile、DM 与 Secure Dex Metadata 安装编译](06-profile-dm-sdm-install-compilation.md)
- [16.7 Android 系统启动耗时优化与 bootanalyze](07-system-boot-time-optimization.md)
- [16.8 AppFlow：GB 级应用冷启动内存联合调度](08-appflow-large-app-cold-launch-memory-scheduling.md)
- [16.9 Android 17 平台 Rust 性能边界：Binder、CXX 与 Soong](09-rust-system-services-performance.md)
- [16.10 Android 17 ARM64 内核安全缓解机制性能开销与调优](10-arm64-kernel-security-mitigation-performance.md)
- [16.11 AOHP：将 Android 改造为 Agent 原生 OS](11-agent-native-os.md)

## 阅读建议

- App 侧优化：按问题选读系统改动与版本边界条目。
- 系统、ROM 或平台方向：结合调度、渲染、内存和功耗章节交叉验证。

## 源码与引用口径

- 平台结论优先固定到 `android-17.0.0_r1`；内核结论固定到 `android17-6.18-2026-06_r6`。main 分支和其他 GKI 分支只用于说明演进。
- release notes、behavior changes 与 SDK 文档用于确定公开合同；固定 tag 源码用于核对实现；设备上的 build、flag、模块和 trace 用于证明实际启用状态。
- 社区文章和研究论文可以提供问题线索或原型数据，不能替代平台源码、官方文档和目标设备实验。
- 每篇正文保留与主题直接相关的来源。原独立“参考资料”页只有通用入口，已并入本页，不再占用正文目录项。
