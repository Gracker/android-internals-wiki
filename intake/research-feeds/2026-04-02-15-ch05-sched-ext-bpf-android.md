# [研究] sched_ext: Linux 可扩展调度器类及其 Android 前景

- **来源**: https://lwn.net/Articles/995395/ · https://kernel.org/doc/html/latest/scheduler/sched-ext.html
- **作者/机构**: Linux Kernel Community（Meta/Google/Igalia 贡献）
- **日期**: 2024-11 (6.12 合并) · 持续更新至 2026
- **四维评分**: 相关性 4/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**: 5.1 Linux 进程调度基础 · 5.7 CPU 相关的版本演进
- **映射锚点**: EEVDF 前沿发展、调度器架构演进、sched_ext BPF 调度
- **摘要**: sched_ext 是 Linux 6.12 合并的可扩展调度器类，允许通过 BPF 程序实现自定义调度策略。它为 Android 平台提供了在不修改内核源码的情况下实验和部署专用调度器的可能性。Meta 的 Oculus 已在 Android 移植中实验 sched_ext。

### 关键发现
1. **架构定位**：sched_ext 在调度优先级栈中位于 SCHED_IDLE 和 SCHED_NORMAL 之间，可以管理 SCHED_NORMAL/BATCH/IDLE/EXT 任务
2. **BPF 集成**：调度决策由用户态编写的 BPF 程序完成，支持运行时动态加载和切换调度器，无需重启
3. **安全机制**：Bypass Mode —— 当检测到错误或任务停滞时，自动回退到简单 FIFO 调度器，确保系统不会挂死
4. **sched_deadline Server**：为防止 RT 任务饿死 sched_ext 任务，引入了 deadline server 机制，在系统启动时初始化
5. **Android 实验现状**：Meta/Oculus 正在 Android 移植版上实验 sched_ext；Google 计划将 ghOSt 调度框架迁移到 sched_ext
6. **6.13 增强**：增加了 LLC（末级缓存）和 NUMA 感知能力，修复了多路 Intel Xeon 服务器上的 live-lock 问题

### 可直接引用段落

> sched_ext (or SCX) is a scheduler class whose implementation can be dynamically loaded as a BPF program. It allows kernel scheduling behavior to be modified without rebooting the system, and enables rapid experimentation with new scheduling algorithms tailored to specific workloads.
>
> — kernel.org Documentation: scheduler/sched-ext

> The SCX_OPS_SWITCH_PARTIAL flag allows only tasks explicitly set to SCHED_EXT to be managed by the BPF scheduler, while all other tasks continue to use the default scheduler (EEVDF).
>
> — kernel.org Documentation: scheduler/sched-ext

### 与 queue.json 联动
- 映射建议：可补充到 5.1 的 material_paths（EEVDF 前沿发展锚点）和 5.7（版本演进）
- 无优先级调整建议
