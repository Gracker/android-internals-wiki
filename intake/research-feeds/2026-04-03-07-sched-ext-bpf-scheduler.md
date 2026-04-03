## [研究] sched_ext BPF 可扩展调度器（Linux 6.12 合入，Android 实验性移植中）
- **来源**：https://lwn.net/Articles/922013/ (LWN sched_ext merge), https://github.com/sched-ext/scx (GitHub), https://android.googlesource.com/platform/system/experimental/sched_ext/ (AOSP)
- **作者/机构**：Tejun Heo (Meta/kernel), David Vernet (Meta), Google Android kernel team
- **日期**：2024-11-17 (Linux 6.12 merge), 2025 ongoing (Android port experiments)
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**：§5.1 Linux 进程调度基础 · §5.7 CPU 相关的版本演进
- **映射锚点**：调度器架构演进、BPF 与内核交互、sched_ext 框架、Android 调度器定制化路径
- **摘要**：sched_ext 在 Linux 6.12 合入主线，允许通过 BPF 程序动态加载自定义调度策略。Meta 和 Google 均已投入。Android 的实验性移植正在进行，Oculus 已在 Android 上实验 sched_ext，但大规模生产部署需更新平台内核。

### 关键发现
1. **BPF 安全保障**：sched_ext 利用 BPF 的静态分析在加载时验证调度器程序，确保自定义调度器不会破坏或崩溃系统。这使得在不修改内核源码、不重编译内核的情况下快速迭代调度策略成为可能。
2. **游戏/延迟敏感场景**：scx_lavd 调度器专为游戏工作负载设计，关注交互性和帧率稳定性。scx_rustland 在游戏中（如 Terraria）展示了即使有其他重负载（如内核编译）运行也能保持 FPS 提升。
3. **Android 移植状态**：AOSP 提供了 sched_ext 示例调度器和 BPF 编译工具链。Meta 和 Google "fully committed" to sched_ext。Oculus 在 Android 上实验性使用。但大规模 Android 生产部署 "would take quite a while" 且需要更新的平台内核。
4. **对 Android 性能分析的潜在影响**：如果 sched_ext 在 Android 上可用，性能工程师可以编写针对特定场景（如 UI 流畅性、后台任务管控、游戏帧率优化）的定制调度器，并通过 Perfetto 观察调度行为变化。

### 可直接引用段落
> sched_ext is a flexible and safe Linux kernel feature that enables developers to implement and dynamically load custom kernel thread schedulers as BPF programs. This approach allows rapid development and testing of new scheduling policies without requiring kernel modifications or recompilation.
> — sched-ext.com documentation

> Meta and Google are "fully committed" to sched_ext. An Android port is being developed and experimented with. However, widespread deployment on Android would "take quite a while" and would necessitate the rollout of a newer platform kernel.
> — LPC 2024 sched_ext talk, multiple kernel mailing list discussions

### 与 queue.json 联动
- 优先级调整建议：§5.7 应增加 sched_ext 作为 Android 未来调度器架构的重要内容
- 素材路径建议：§5.1 增加 sched_ext 架构图位置，§5.7 增加时间线（2024 合入 → 2025 实验 → 未来 Android 部署）
