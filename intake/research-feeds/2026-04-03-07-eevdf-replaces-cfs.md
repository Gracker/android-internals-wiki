## [研究] EEVDF 取代 CFS 成为 Linux 默认调度器（6.6→6.12 全面转正）
- **来源**：https://lwn.net/Articles/925371/ (LWN), https://kernelnewbies.org/Linux_6.12 (KernelNewbies), https://source.android.com/docs/core/architecture/kernel (AOSP)
- **作者/机构**：Peter Zijlstra (Linux kernel maintainer), AOSP
- **日期**：2024-11-17 (Linux 6.12 release), 2025-06-10 (Android 16 stable with 6.12 kernel)
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**：§5.1 Linux 进程调度基础 · §5.7 CPU 相关的版本演进
- **映射锚点**：CFS→EEVDF 演进、调度器核心算法、fair scheduling class、Android 16 内核升级
- **摘要**：Linux 6.6 引入 EEVDF 作为可选项，6.12 完成默认切换。Android 16 基于 6.12 内核，成为首个默认使用 EEVDF 的 Android 版本。EEVDF 通过 lag 追踪和虚拟截止时间实现更公平的 CPU 分配，对延迟敏感任务有显著改善。

### 关键发现
1. **Lag 追踪机制**：EEVDF 为每个任务计算 lag（预期 CPU 时间 - 实际 CPU 时间），lag > 0 的任务被标记为 eligible 优先调度，lag < 0 的任务暂时不参与调度，直到 lag 恢复。这消除了 CFS 依赖的"脆弱启发式"来平衡交互式与批处理任务的问题。
2. **sched_setattr() 时间片请求**：EEVDF 允许任务通过 sched_setattr() 请求特定时间片长度。延迟敏感任务可请求更短时间片，获得更早的虚拟截止时间，从而更频繁被调度——但不消耗更多 CPU 总量。这对 Android UI 线程、音频线程等场景直接有益。
3. **Android 16 时间线**：Android 16 稳定版（2025-06-10）使用 android16-6.12 内核分支，该内核中 EEVDF 已是默认调度器。AOSP 文档明确指出 EEVDF "better balance CPU access between short and long-running tasks"。
4. **ChromeOS 调优经验**：ChromeOS 的 EEVDF 集成测试发现，默认参数在某些 Web 应用场景性能低于 CFS，需要将基础时间片长度翻 4 倍才能达到性能对等。移除 eligibility 机制在某些指标上带来 30% 提升——这暗示 Android 厂商可能需要针对移动场景做参数调优。

### 可直接引用段落
> EEVDF replaces CFS to "better balance CPU access between short and long-running tasks." Unlike CFS, which relied on fragile heuristics to distinguish interactive and batch workloads, EEVDF integrates responsiveness directly into the core scheduling algorithm through virtual deadlines and lag-based eligibility.
> — AOSP documentation, source.android.com

> The EEVDF scheduler was initially merged as an option in Linux 6.6 and its transition was completed with Linux 6.12 (released November 17, 2024). Linux kernel 6.13 subsequently included a fix to address an EEVDF scheduling lag issue, computing lag properly and preventing entity placement bugs.
> — LWN.net, kernel documentation

### 与 queue.json 联动
- 优先级调整建议：建议将 §5.7 (CPU 相关的版本演进) 的 priority 提升，EEVDF 取代 CFS 是调度器领域 10 年来最大的架构变化
- 素材路径建议：可补充到 §5.1 的版本演进小节和 §5.7 的 CFS→EEVDF 演进部分
