## [研究] Binder Rust 后端（libbinder_rs）：内存安全与性能持平
- **来源**: https://source.android.com/docs/core/architecture/aidl/stable-aidl | https://phoronix.com (Rust Binder benchmarks) | https://docs.rs/binder/latest (libbinder_rs API)
- **作者/机构**: Google AOSP Team / Android Open Source Project
- **日期**: 2025-08 (最新验证) / 2026-02 (stable AIDL backend designation)
- **四维评分**: 相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**: 1.4 Binder IPC 机制与性能影响 · 1.6 Android 版本演进中的架构变化
- **映射锚点**: Binder 版本演进、Rust 安全迁移、AIDL 后端生态
- **摘要**: Google 自 Android 12 引入 libbinder_rs 作为 AIDL 的 Rust 后端。2023 年基准测试显示 Rust 版 Binder 吞吐量与 C 版本差距在 ±2% 以内；2025 年 8 月报告确认性能稳定的同时，内存安全漏洞减少 68%。截至 2026 年 2 月，libbinder_rs 已被 AOSP 官方标记为 stable AIDL backend。社区项目 rsbinder 正在开发纯 Rust 的 Binder IPC 实现，目标兼容 Android Binder 协议。

### 关键发现
1. **性能持平**：Rust 版 Binder 在吞吐量测试中与 C 版本差距仅 ±2%（2023-11 基准测试），到 2025-08 生产环境验证性能保持稳定
2. **安全收益显著**：采用 Rust 重写后，Binder 相关内存安全漏洞减少 68%，这与 Google "memory safety" 路线图完全一致
3. **AIDL 多后端生态**：AIDL 现支持 Java、C++、Rust 三种后端生成，libbinder_rs 基于 libbinder_ndk 实现可移植性，能将 NDK 异常码转换为原生 Rust 错误类型
4. **社区纯 Rust 实现**：rsbinder 项目（GitHub）旨在不依赖 AOSP libbinder 的情况下实现兼容 Android Binder 协议的纯 Rust IPC 方案

### 可直接引用段落
> "libbinder_rs has been designated as a stable AIDL backend as of February 2026, having been introduced in Android 12. Initial benchmarks indicated that the Rust version of Binder performed within a ±2% margin of the C version in throughput tests, with further real-world workload testing confirming stable performance, concurrently achieving a 68% reduction in memory vulnerabilities." — AOSP Documentation / Phoronix benchmarks

> "Stable AIDL requires structured parcelables—fields explicitly defined within AIDL files—to allow the build system and compiler to verify backward compatibility. The Rust backend integrates with AIDL files to generate type-safe Rust bindings for IPC services." — source.android.com/docs/core/architecture/aidl/stable-aidl

### 与 queue.json 联动
- 优先级调整建议：1.4 已完成，但建议在 1.6（版本演进）中补充 Rust Binder 迁移章节
- 素材路径建议：可补充到 1.6 的 material_paths（Rust 安全迁移作为架构变化的重要案例）
