## [研究] 优先级反转与 Futex PI 在 Android 中的实践
- **来源**: https://source.android.com/docs/core/audio/latency/priority-inversion + https://lpc.events/ + https://androidperformance.com/
- **作者/机构**: AOSP / Linux Plumbers Conference / androidperformance.com
- **日期**: 2026-04-06
- **四维评分**: 相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**: 1.14 锁竞争与同步性能分析
- **映射锚点**: 优先级反转问题、PI Futex、锁优化策略、DeliQueue 无锁替代
- **摘要**: 优先级反转可导致最高 216ms 的帧 jank。Linux 提供 PI futex（FUTEX_LOCK_PI）实现优先级继承，但 Android Audio 子系统因开销和信任模型问题未采用，改用 try-lock + timeout / atomic / lock-free 替代方案。Android 17 DeliQueue 是近期最重要的锁优化案例：用 MPSC 无锁队列替代 MessageQueue 的 synchronized 锁。

### 关键发现
1. **优先级反转量化影响**：CPU 密集型工作负载中观测到高达 216ms 的帧 jank 由优先级反转导致。根因是低优先级线程持有锁，中间优先级线程抢占 CPU，高优先级线程（如 UI/RenderThread）无法获取锁。
2. **PI Futex 实践权衡**：Linux FUTEX_LOCK_PI 实现优先级继承协议，但 Android Audio 子系统文档明确指出不使用 PI futex，原因包括：(a) 系统调用开销影响实时性能；(b) 依赖客户端可信（恶意/bug 客户端可造成 DoS）；(c) audio callback 粒度极细（~2ms），PI 开销占比过高。
3. **替代策略与 DeliQueue**：AOSP 推荐的替代方案包括 try-lock with timeout（避免无限等待）、atomic 操作（CAS 替代锁）、lock-free 算法。Android 17 DeliQueue 是最典型案例：用 Multi-Producer Single-Consumer 无锁队列替代 MessageQueue 的 synchronized(this) 锁，减少 15% 主线程锁等待 + 4% 掉帧。

### 可直接引用段落
> Android 官方文档明确指出，Audio 子系统不使用 Linux PI futex（FUTEX_LOCK_PI）解决优先级反转，原因是系统调用开销和信任模型限制。替代方案包括 try-lock + timeout、atomic 操作和 lock-free 数据结构。Android 17 的 DeliQueue 是这一策略的最新实践：MPSC 无锁队列替代 synchronized MessageQueue，主线程锁等待减少 15%。

> 在 Perfetto 中识别优先级反转的模式：当 RenderThread（高优先级）的 thread_state track 显示 Runnable 但未 Running，同时同一 CPU 上有较低优先级线程在 Running，且 RenderThread 等待的锁被该低优先级线程持有时，即为典型的优先级反转场景。

### 与 queue.json 联动
- 优先级调整建议：§1.14 建议与 §1.13 (DeliQueue) 建立强交叉引用
- 素材路径建议：追加到 §1.14 的 material_paths
