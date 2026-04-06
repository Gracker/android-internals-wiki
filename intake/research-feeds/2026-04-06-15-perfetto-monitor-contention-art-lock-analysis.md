## [研究] Perfetto Monitor Contention SQL 分析与 ART 锁机制全景
- **来源**: https://perfetto.dev/docs/analysis/sql-tables (android.monitor_contention) + https://cs.android.com/android/platform/superproject/+/main:art/runtime/monitor.cc
- **作者/机构**: Google Perfetto Team / AOSP ART Team
- **日期**: 2026-04-06
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 1.14 锁竞争与同步性能分析
- **映射锚点**: Java Monitor 竞争分析、Native 锁分析、Perfetto SQL 查询、ART Monitor 实现
- **摘要**: Perfetto 提供 android.monitor_contention SQL 标准库模块，可直接查询 Java Monitor 竞争事件的 Owner/Waiter 线程对、锁对象类名、等待时长。ART runtime/monitor.cc 实现了 thin lock → fat lock 膨胀机制，monitor_contenders_ 条件变量管理等待队列，kLongWaitMs=100ms 触发长等待日志。

### 关键发现
1. **Perfetto android.monitor_contention 模块**：标准 SQL 库提供结构化查询，包含 owner_tid、waiter_tid、lock_class、blocked_reason 字段，可通过 JOIN thread / process 获取完整调用栈。Thread / Lock contention track 可视化 Owner→Waiter 连线。
2. **ART Monitor 膨胀机制**：每个 Java 对象关联一个 monitor，初始为 thin lock（轻量级 CAS），竞争发生时膨胀为 fat monitor（调用 futex 内核等待）。art/runtime/monitor.cc 中 monitor_contenders_.Wait(self) 是等待队列入口，kLongWaitMs=100ms 触发 logcat W 级别长等待告警。
3. **Native 锁分析路径**：sched_switch（线程被调度出去）+ sched_waking（线程被唤醒）事件提供精确的 futex 等待/唤醒调用栈。blocked_function 包含 futex_wait 表示等待 Java 锁或 native mutex。

### 可直接引用段落
> Perfetto 的 Thread / Lock contention track 显式标记 "Owner"（持有锁的线程）和 "Waiter"（等待锁的线程）及其连线关系，并标注被竞争锁对象的类名。PerfettoSQL 标准库 android.monitor_contention 模块提供结构化查询接口，支持按进程、线程、锁类名过滤。

> 在 ART runtime/monitor.cc 中，当线程进入 synchronized 块发现 monitor 已被占用，线程状态切换为 kBlocked，先释放 mutator lock，然后调用 monitor_contenders_.Wait(self) 进入条件变量等待队列。等待超过 kLongWaitMs（100ms）后，ART 输出长等待日志，包含 owner 线程信息和等待线程数。

### 与 queue.json 联动
- 优先级调整建议：§1.14 当前 priority 85，建议维持（核心基础分析维度，DeliQueue 仅覆盖 MQ 特例）
- 素材路径建议：追加到 §1.14 的 material_paths
