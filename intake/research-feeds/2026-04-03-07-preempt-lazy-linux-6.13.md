## [研究] PREEMPT_LAZY 懒抢占模式（Linux 6.13，对 Android 调度行为的影响）
- **来源**：https://kernelnewbies.org/Linux_6.13 (KernelNewbies), https://lwn.net/Articles/994282/ (LWN), https://source.android.com/docs/core/architecture/kernel (AOSP kernel versions)
- **作者/机构**：Thomas Gleixner (Linux kernel), Linus Torvalds, AOSP kernel team
- **日期**：2025-01-19 (Linux 6.13 release)
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**：§5.1 Linux 进程调度基础 · §5.7 CPU 相关的版本演进
- **映射锚点**：抢占模型、PREEMPT_NONE/VOLUNTARY/FULL/LAZY、调度器配置选项、Android 内核抢占策略
- **摘要**：Linux 6.13 引入 PREEMPT_LAZY 新抢占模式，在实时任务（RR/FIFO/DEADLINE）上表现为完全抢占，在普通任务（SCHED_NORMAL）上延迟到下一个定时器 tick 才抢占。目标是减少 lock holder preemption、提升吞吐量、在响应性和吞吐量之间取得更好的平衡。

### 关键发现
1. **双模式抢占策略**：PREEMPT_LAZY 对实时任务（SCHED_RR/SCHED_FIFO/SCHED_DEADLINE）立即抢占，确保实时性。对普通任务（SCHED_NORMAL，即 Android 上大多数 App 线程），延迟抢占到下一个调度 tick。这减少了内核锁持有者被抢占导致的锁竞争和缓存失效。
2. **ARM 架构支持**：Linux 6.13 对 ARM 架构有重要更新，包括 Arm CCA（Confidential Compute Architecture）受保护虚拟机支持。PREEMPT_LAZY 已在 x86、RISC-V、LoongArch 启用，ARM 支持预期在后续版本跟进。
3. **Android 内核时间线**：Android 16 使用 android16-6.12 内核（不含 PREEMPT_LAZY）。但 android-mainline 持续跟踪上游内核，后续 ACK 分支可能合入 6.13+ 的 PREEMPT_LAZY。这对 Android 17/18 的调度行为有潜在影响。
4. **Perfetto 中的可观察性**：如果 Android 内核启用 PREEMPT_LAZY，在 Perfetto 中观察到的调度延迟模式会变化——普通任务的抢占延迟会更规律（tick 对齐），而实时任务的响应保持即时。性能分析师需要了解这一变化以正确解读 Trace 数据。

### 可直接引用段落
> PREEMPT_LAZY is a new preemption model introduced in Linux 6.13. For real-time tasks (RR/FIFO/DEADLINE), PREEMPT_LAZY behaves like full preemption, ensuring immediate responses. However, for normal tasks (SCHED_NORMAL), it delays preemption until the next timer tick. The goal is to reduce "lock holder preemption" and improve throughput.
> — kernelnewbies.org Linux 6.13 changelog

> The lazy preemption model simplifies the configuration options and bridges the performance gap with voluntary preemption, increasing performance for general workloads while maintaining low-latency response for critical tasks.
> — LWN.net, kernel documentation

### 与 queue.json 联动
- 优先级调整建议：§5.7 版本演进中应补充 PREEMPT_LAZY 作为 Linux 6.13 的重要调度器变更
- 素材路径建议：§5.1 抢占模型章节可增加 PREEMPT_LAZY 作为第四种抢占模式的介绍
