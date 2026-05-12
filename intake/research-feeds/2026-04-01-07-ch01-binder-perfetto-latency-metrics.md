## [研究] Perfetto Binder 事务延迟分析：client_dur / server_dur / dispatch_dur 三维指标
- **来源**: https://perfetto.dev/docs (Binder transaction analysis) | https://android.com (Perfetto docs) | https://perfetto.dev/docs/analysis/sql-tables (binder_transaction)
- **作者/机构**: Google Perfetto Team / Android Performance 团队
- **日期**: 2025 (最新 Perfetto 模块更新)
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**: 1.4 Binder IPC 机制与性能影响 · 9.1 ANR 设计思想 · 13.5 Perfetto 专题解读
- **映射锚点**: Binder 事务在 Perfetto 中的表现、Binder 线程池饱和分析、ANR 中的 Binder 因素
- **摘要**: Perfetto 提供了 Binder 事务的完整追踪能力，通过 linux.ftrace 的 binder_transaction / binder_transaction_received / binder_reply 三个 tracepoint，以及 PerfettoSQL 的 binder_transaction 表，可以精确量化三个关键延迟维度：client_dur（客户端总耗时）、server_dur（服务端处理耗时）、dispatch_dur（排队等待耗时）。当 dispatch_dur 持续大于 server_dur 时，通常意味着服务端 Binder 线程池饱和（默认上限 16 线程）。

### 关键发现
1. **三维延迟指标体系**：client_dur = dispatch_dur + server_dur + 网络开销。其中 dispatch_dur 是服务端排队等待时间，直接反映线程池压力
2. **线程池饱和检测**：在 Perfetto UI 中添加 "Android Binder / Transactions" track，配合 thread_state track 检查 Binder 线程状态。如果大部分 Binder 线程持续处于 Running/D/S 状态，说明线程池已饱和
3. **客户端阻塞特征**：客户端线程卡在 `ioctl(BINDER_WRITE_READ)` 或 `epoll_wait` 的 S (Sleeping) 状态，是 Binder 线程池压力的强信号
4. **PerfettoSQL 查询**：可使用标准 SQL 查询 binder_transaction 表，按 process/时间范围过滤，计算平均 dispatch_dur 和 server_dur
5. **Android 2025 增强**：Perfetto 标准库新增 Binder transaction 模块，将底层 trace 概念转化为开发者友好的高级概念，支持 SQL 查询

### 可直接引用段落
> "In Perfetto's Binder transaction analysis, three key metrics are available: client_dur (the total time the client waits), server_dur (the time the server actually spends processing), and dispatch_dur (the queueing delay between the client sending and the server receiving the transaction). A consistently large dispatch_dur compared to server_dur often points to queuing issues at the server due to thread pool saturation." — Perfetto Documentation

> "Binder thread pool exhaustion occurs when all Binder worker threads within a process are busy, leaving no idle threads for new transactions. This can cause client threads to become blocked, often appearing as an uninterruptible sleep state at ioctl(BINDER_WRITE_READ), resulting in significantly large dispatch_dur values." — Android Performance Analysis Guide

### 与 queue.json 联动
- 优先级调整建议：建议将 9.1 ANR 设计思想的 priority 从 50 提升到 60，因为 Binder-ANR 关联分析工具已成熟
- 素材路径建议：可补充到 1.4（Binder 性能分析在 Perfetto 中的表现）和 9.1（ANR 中 Binder 因素的分析方法）
