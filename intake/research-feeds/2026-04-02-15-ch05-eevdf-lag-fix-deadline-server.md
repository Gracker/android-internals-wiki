# [研究] EEVDF lag 计算修复与 sched_deadline Server 防饥饿机制

- **来源**: https://lwn.net/Articles/1004261/ · https://kernel.org/doc/html/latest/scheduler/sched-design-EEVDF.html
- **作者/机构**: Peter Zijlstra（Linux Kernel 核心调度器维护者）
- **日期**: 2025-01 (6.13 稳定版发布时修复)
- **四维评分**: 相关性 4/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**: 5.1 Linux 进程调度基础 · 5.7 CPU 相关的版本演进
- **映射锚点**: EEVDF 虚拟截止时间机制、lag 计算与公平性保证
- **摘要**: Linux 6.13 在发布前最后一刻修复了 EEVDF 调度器中的 lag 计算和 entity placement 问题。这个修复直接影响任务调度的公平性——之前错误的 lag 计算可能导致某些任务获得过多或过少的 CPU 时间。同时，sched_deadline server 基础设施为 sched_ext 任务提供了防饥饿保护。

### 关键发现
1. **Lag 计算修复**：EEVDF 中的 entity placement bug 导致 lag 值计算不正确，使得某些任务的虚拟截止时间偏离预期。修复后 lag 计算更准确，但开发者承认"尚不完美"
2. **Lag 语义**：正 lag 表示任务"被欠"CPU 时间（应优先调度），负 lag 表示任务"多占"CPU 时间。只有 lag≥0 的任务才是"eligible"可运行的
3. **睡眠任务的 lag 处理**：EEVDF 引入"deferred dequeue"机制——睡眠任务保留当前 lag 值并在虚拟运行时间上衰减，防止任务通过短暂睡眠来"重置"负 lag 值
4. **sched_setattr() 新接口**：应用可以通过 sched_setattr() 系统调用请求特定时间片长度（time slice），这对延迟敏感型 Android 应用（如音频/游戏）有重要意义
5. **sched_deadline Server**：为 sched_ext 引入的 deadline server 在 boot 时初始化，当第一个 sched_ext 任务入队时自动启动，确保即使在 RT 任务霸占 CPU 时，sched_ext 任务也能获得 CPU 时间
6. **向后移植**：lag 修复预期将被回移到旧版稳定内核

### 可直接引用段落

> A significant fix for an EEVDF scheduling lag, caused by an entity placement bug, was introduced just before the Linux 6.13 stable kernel release. This fix aimed to compute lag properly and address issues discovered by Peter Zijlstra. The fix is expected to be backported to older stable kernels.
>
> — LWN.net, Linux 6.13 Release Coverage

> Only tasks with a lag value >= 0 are considered "eligible" to run. Among eligible tasks, a virtual deadline is computed, and the task with the earliest virtual deadline is chosen. This mechanism helps prioritize latency-sensitive tasks with shorter time slices.
>
> — kernel.org Documentation: scheduler/sched-design-EEVDF

### 与 queue.json 联动
- 映射建议：可补充到 5.1 的 material_paths（EEVDF 虚拟截止时间锚点的更新素材）
- 映射建议：可补充到 5.7 的 material_paths（6.12/6.13 调度器变更）
- 无优先级调整建议
