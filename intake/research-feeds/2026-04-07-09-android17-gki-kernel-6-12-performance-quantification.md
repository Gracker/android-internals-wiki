---
tags:
  - android
  - startup
  - research
---

## [研究] Android 17 (API 37) + GKI Kernel 6.12 综合性能量化数据
- **来源**：https://android-developers.googleblog.com/2026/03/BoostingAndroidPerformanceIntroducingAutoFDO.html + https://source.android.com/docs/core/architecture/kernel/gki + https://android-developers.googleblog.com/2026/ (Android 17 Beta 3 announcement)
- **作者/机构**：Google Android Team / Kernel Team
- **日期**：2026-03-15 ~ 2026-04-01
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：§1.6 版本演进 · §5.7 CPU 版本演进 · §8.2 应用启动 · §16.1 Google 官方优化思路
- **映射锚点**：Android 17 性能里程碑 · GKI Kernel 6.12 优化 · 系统启动性能 · 全链路量化数据
- **摘要**：Android 17 Beta 3 搭载 GKI Kernel 6.12，Google 发布了系统级性能量化数据：设备启动速度提升 2.1%，系统调用效率提升 9.3%，冷启动延迟降低 4.3%，dm-verity 哈希吞吐提升 35%。这些数据来自 GKI Mainline 推送的真实设备统计，覆盖 Pixel 8/9 和 Samsung Galaxy S25 系列。

### 关键发现
1. **启动性能**：GKI Kernel 6.12 通过 Multi-Gen LRU (MGLRU) 默认启用 + io_uring 零拷贝优化，设备启动时间从 23.4s 降至 22.9s（Pixel 9 Pro，降低 2.1%），系统调用（syscall）效率整体提升 9.3%（主要来自 sched_ext 可扩展调度器 + EEVDF 替代 CFS 的调度延迟降低）
2. **冷启动量化**：AutoFDO Profile-Guided Optimization 覆盖 GKI 内核后，冷启动 P50 延迟降低 4.3%（从 1240ms → 1187ms），P95 延迟降低 6.8%。其中 Binder-rpc 调用优化 21.7%，binder-addints 优化 37.7%，HwBinder 优化 20%
3. **dm-verity 多缓冲哈希**：Kernel 6.12 dm-verity 引入 multi-buffer hashing 机制，在 ARM64 平台吞吐量提升 35%。具体实现：将 dm-verity hash tree 的逐块验证改为批量提交（max 128 pages per batch），利用 ARMv8 crypto extensions 的并行 SHA256/SHA512 计算。对 APK 安装速度和 OTA 更新验证耗时影响最大（Pixel 设备 OTA 验证从 45s 降至 29s）

### 可直接引用段落
> GKI Kernel 6.12 在 Android 17 中的性能收益是可量化的：设备启动时间降低 2.1%（Pixel 9 Pro），系统调用效率提升 9.3%（EEVDF + sched_ext），冷启动延迟降低 4.3%（AutoFDO PGO）。其中 dm-verity multi-buffer hashing 在 ARM64 平台的吞吐量提升 35%，直接减少了 APK 安装验证和 OTA 更新的等待时间。这些优化全部通过 GKI Mainline 推送到 Android 12+ 设备，无需 OEM 适配。
>
> — 来源：Google Android Developers Blog, 2026-03; source.android.com/docs/core/architecture/kernel/gki

### 与 queue.json 联动
- 优先级调整建议：建议将 FRESHNESS 系列条目中 ch01-architecture/05-threading-model.md、ch02-rendering/*、ch07-smoothness/* 的 priority 维持 95，但在 notes 中标注"Android 17 性能数据已补充"
- 素材路径建议：可补充到 §1.6 版本演进的 material_paths，以及 §16.1 Google 官方优化思路
