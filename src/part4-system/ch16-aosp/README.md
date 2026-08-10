# 第 16 章：AOSP 性能优化

AOSP、system service、ROM 与平台侧优化可以直接改变系统路径和策略。

应用侧通常在既有接口与策略内降低成本，系统侧还需要评估设计约束、兼容性、整机收益和回归风险。

## 内容索引

- [16.1 Google 官方的性能优化思路](01-google-optimization.md)
- [16.2 各 Android 版本性能变更追踪](02-version-changes.md)
- [16.3 AOSP 源码编译与调试环境](03-aosp-build.md)
- [16.4 Android 17 + Kernel 6.18 系统级性能优化](04-android17-kernel618-performance.md)
- [16.5 Android 17（API 37）性能行为变更与适配](05-android17-api37-performance-changes.md)
- [16.6 Android 16 Cloud Profile 与 dexopt 安装优化](06-android16-cloud-profile-dexopt.md)
- [16.7 Android 系统启动耗时优化与 bootanalyze](07-system-boot-time-optimization.md)
- [16.8 AppFlow：GB 级应用冷启动内存联合调度](08-appflow-large-app-cold-launch-memory-scheduling.md)
- [16.9 Android 17 Secure Dex Metadata](09-android17-sdm-install-performance.md)
- [16.10 Android 17 平台 Rust 性能边界](10-rust-system-services-performance.md)
- [16.11 Android 17 ARM64 内核安全缓解机制性能开销](11-arm64-kernel-security-mitigation-performance.md)
- [16.12 AOHP：将 Android 改造为 Agent 原生 OS](12-agent-native-os.md)

## 阅读建议

- App 侧优化：按问题选读系统改动与版本边界条目。
- 系统、ROM 或平台方向：结合调度、渲染、内存和功耗章节交叉验证。
