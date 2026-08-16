# 第 16 章：AOSP 性能优化

AOSP（Android Open Source Project）是 Android 开源平台源码。system service 指运行在系统进程、向 App 或其他系统组件提供能力的服务；本章所说的 ROM，指设备厂商基于 AOSP 构建并发布的系统软件。做这类平台侧优化时，可以直接修改系统代码、配置和调度策略。

App 侧优化通常只能在现有接口和系统策略内降低自身成本。系统侧改动会影响多个 App 或整台设备，因此还要评估设计约束、兼容性、整机收益，以及改动让原有功能或性能退步的回归风险。

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

- 如果负责 App 侧优化，可按当前问题选读系统改动与版本边界条目，先确认应用能够控制的范围。
- 如果负责系统、ROM 或平台开发，应结合调度、渲染、内存和功耗章节交叉验证，避免只改善单项指标却增加其他系统成本。

## 源码与引用口径

- 平台结论优先固定到 `android-17.0.0_r1`；内核结论固定到 `android17-6.18-2026-06_r6`。固定 tag 表示可复查的源码版本。main 是持续变化的开发分支；其他 GKI（Generic Kernel Image，通用内核镜像）分支只用于说明机制如何演进。
- release notes（版本说明）、behavior changes（行为变更文档）与 SDK 文档用于确定对开发者公开承诺的接口和行为边界；固定 tag 源码用于核对该版本的实现。设备上的 build（具体系统构建）、flag（功能开关）、模块版本和 trace（运行轨迹）用于证明目标设备实际启用了什么。
- 社区文章和研究论文可以提供问题线索或原型数据，不能替代平台源码、官方文档和目标设备实验。
- 每篇正文保留与主题直接相关的来源。原独立“参考资料”页只有通用入口，其引用原则已并入本页，不再占用正文目录项。
