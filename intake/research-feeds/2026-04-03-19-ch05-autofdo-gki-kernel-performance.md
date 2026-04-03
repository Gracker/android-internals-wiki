## [研究] AutoFDO GKI 内核级性能优化：Pixel 量化数据与 Android 16 部署
- **来源**：https://android-developers.googleblog.com/ (Google Blog); https://source.android.com/docs/core/architecture/kernel/gki
- **作者/机构**：Google Android Kernel Team
- **日期**：2025-06 ~ 2026-03
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**：§5.1 Linux 进程调度基础 / §5.7 CPU 相关的版本演进 / §1.6 Android 版本演进中的架构变化
- **映射锚点**：内核调度性能优化、PGO/AutoFDO 技术、Android 16 GKI 内核、版本演进量化数据
- **摘要**：Google 在 android16-6.12 和 android15-6.6 GKI 内核分支全面部署 AutoFDO（Automatic Feedback-Directed Optimization）。通过采集 Pixel 设备上 Top 100 应用的真实负载 profile，对占 CPU 时间约 40% 的内核热路径进行 PGO 编译优化，在 Pixel 设备上取得冷启动 4%、开机时间 2%、Binder-rpc 21.7%、binder-addints 37.7%、HwBinder 20% 的性能提升。

### 关键发现
1. **量化性能数据（Pixel 8, 6.6.123 kernel profile）**：冷启动 3.0%~4.3%、开机时间 2%、Binder-rpc 19.5%~21.7%、binder-addints 12.3%~37.7%、HwBinder 11.7%~20%。微基准测试约 10% 提升，真实负载约 5%。
2. **Profile 采集机制**：Google 在 Pixel 设备上运行 Top 100 热门应用采集真实硬件采样数据（基于硬件 performance counter），然后反馈到 LLVM Clang 编译管线进行 AutoFDO + Propeller 优化。内核占 Android 设备 CPU 时间约 40%，是 PGO 的最大收益目标。
3. **部署范围与路线图**：当前已覆盖 android16-6.12 和 android15-6.6 两个 GKI 分支（AArch64 架构），计划扩展到更新的 GKI 版本和更多构建目标。CachyOS 发行版已在 Linux 6.12 LTS 默认启用 AutoFDO。

### 可直接引用段落
> Google is implementing AutoFDO across the android16-6.12 and android15-6.6 branches of the Android Linux kernel. Benchmarks on Pixel devices demonstrated "significant performance wins for users," including over 4% faster cold app launch times, a 2% reduction in boot times, and up to 21% faster Binder tests. AutoFDO works by utilizing real-world usage patterns, collected from representative workloads like running the top 100 most popular apps on Pixel devices, to guide the compiler in making more intelligent optimization decisions. The kernel accounts for approximately 40% of CPU time on Android devices.
>
> — 来源：Google Android Developers Blog, 2025

### 与 queue.json 联动
- 优先级调整建议：freshness-005 (ch05-cpu-power/01-linux-scheduling.md) 可标记为已研究并补充素材
- 素材路径建议：可补充到 §5.1 的 material_paths 和 §5.7 版本演进章节
