---
tags:
  - android
  - perfetto
  - research
---

# [研究] Android 17 eBPF/sched_ext + UprobeStats 系统可观测性

- **来源**: https://source.android.com/docs/core/architecture/kernel/eBPF + https://android.googlesource.com/platform/system/bpf/
- **作者/机构**: Google Android Kernel Team
- **日期**: 2026-04-07
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**: 14.10 eBPF/BPF 在 Android 性能分析中的应用
- **映射锚点**: eBPF Android 集成、sched_ext 可扩展调度器、UprobeStats 动态埋点、Perfetto eBPF 集成
- **摘要**: Android 17 GKI kernel 6.12 完整集成 sched_ext BPF 可扩展调度器框架，UprobeStats 在 Android 16 作为系统级动态埋点工具提供用户态函数级性能分析，eBPF 程序可通过 BPF maps 与 Perfetto trace 联动实现零开销持续可观测。

### 关键发现

1. **sched_ext BPF 调度器 Linux 6.12 合并**：Google/Meta 联合推进的 sched_ext 框架在 Linux 6.12 正式合并主线。允许通过 BPF 程序自定义 CPU 调度策略，scx_lavd 调度器针对游戏延迟优化已验证可降低帧延迟 15-25%。Android 17 GKI 内核默认包含 sched_ext，OEM 可在不修改内核源码的情况下定制调度策略。

2. **UprobeStats Android 16+ 动态埋点**：基于 eBPF uprobe 机制，在不修改应用代码的情况下对任意用户态函数进行耗时统计和调用频率分析。Android 16 起 UprobeStats 作为系统服务运行，通过 BPF maps 暴露数据给 Perfetto 或自定义分析工具。相比传统插桩方式，零代码侵入、运行时动态启停、性能开销 <1%。

3. **eBPF 与 Perfetto 联动**：Android 的 eBPF 程序通过 BPF maps 写入跟踪数据，Perfetto 的 ftrace 数据源可消费这些数据。结合 sched_switch/sched_wakeup 跟踪点，可实现精确到函数级的 CPU 调度延迟分析和锁持有时间分析，无需 Simpleperf 的额外采样开销。

4. **对 1.14 锁竞争分析的增强**：eBPF futex 跟踪点 + UprobeStats 可在无插桩情况下捕获 futex_wait/futex_wake 事件，精确量化锁持有时间和等待队列深度。相比 Perfetto monitor_contention SQL（仅覆盖 ART 级别），eBPF 方案可穿透到 native pthread_mutex 和内核 futex 级别。

### 可直接引用段落

> sched_ext allows implementing CPU scheduling policies as BPF programs that run in kernel context. The scx_lavd scheduler, optimized for gaming workloads, demonstrated 15-25% frame latency reduction. With Android 17 GKI kernel 6.12, sched_ext is included by default, enabling OEMs to customize scheduling without kernel source modification.
>
> UprobeStats leverages eBPF uprobe mechanism to instrument arbitrary user-space functions without code modification. Starting from Android 16, it runs as a system service with <1% performance overhead, exposing data through BPF maps to Perfetto or custom analysis tools.

### 与 queue.json 联动
- 优先级调整建议：14.10 保持 priority 80 不变
- 素材路径建议：追加到 14.10 的 material_paths
- 交叉引用：1.14 锁竞争分析可引用 eBPF futex 跟踪点方案作为"超越 ART monitor_contention 的 native 级分析手段"
