## [研究] ART Thin/Fat Lock 膨胀与长等待竞争日志
- **来源**: https://cs.android.com/android/platform/superproject/+/main:art/runtime/monitor.cc + https://cs.android.com/android/platform/superproject/+/main:art/runtime/lock_word.h
- **作者/机构**: AOSP ART Team
- **日期**: 2026-04-06
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 3/5 · 可验证性 5/5 · **总分 18/20**
- **映射章节**: 1.14 锁竞争与同步性能分析
- **映射锚点**: ART 锁实现原理、锁膨胀机制、Monitor::MonitorEnter/MonitorExit
- **摘要**: ART 中每个 Java 对象的 lock word 实现了三级锁状态：Unlocked → Thin Locked (CAS bias/递归计数) → Fat Monitor (futex 等待队列)。竞争触发 thin→fat 膨胀后不可逆，wait() 调用同样触发膨胀。monitor_lock_.Lock(self) 保护 monitor 内部状态，monitor_contenders_ 条件变量管理等待线程队列。

### 关键发现
1. **Lock Word 三级状态**：art/runtime/lock_word.h 定义了 kStateUnlocked(0) / kStateThinLocked(1) / kStateFatLocked(2)。Thin lock 使用对象头 mark word 的高位存储 owner thread id + 递归计数，首次竞争失败时通过 DeflateMonitor/InflateMonitor 转为 fat monitor。
2. **Fat Monitor 内部结构**：monitor.cc 中 fat monitor 包含 monitor_lock_（自旋锁保护内部状态）、monitor_contenders_（条件变量）、owner_（持有线程指针）、lock_count_（递归计数）。Wait(self) 调用时线程先释放 mutator lock（STW 安全），然后等待 monitor_contenders_ 信号。
3. **长等待日志机制**：kLongWaitMs=100ms 阈值，超过后 ART 输出 "Long monitor contention on XXX" 日志到 logcat，包含 owner 线程名、等待时长、当前等待线程数。这是 Perfetto atrace dalvik 类别捕获 monitor contention slice 的数据源头。

### 可直接引用段落
> ART 的锁实现分为 thin lock 和 fat monitor 两级。Thin lock 利用对象 mark word 中的高位字段存储 owner thread id 和递归计数，通过 CAS 原子操作实现无竞争时的快速获取。当 CAS 失败（即发生竞争）或调用 Object.wait() 时，锁膨胀为 fat monitor：创建独立的 Monitor 对象，内部使用 futex 系统调用管理等待队列。膨胀后不可逆转回 thin lock。

> monitor.cc 中 kLongWaitMs 定义为 100ms。当线程等待 monitor 超过此阈值，ART 在 logcat 输出 W 级别日志："Long monitor contention on [class_name] owner=[thread_name] ([wait_ms]ms)"。Perfetto 的 atrace dalvik 类别捕获这些事件，生成 Thread / Lock contention track 中的可视化 slice。

### 与 queue.json 联动
- 素材路径建议：追加到 §1.14 的 material_paths
