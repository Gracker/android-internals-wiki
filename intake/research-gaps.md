## [2026-07-03] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 知识盲区

### 盲区描述
Android 13+ 新增的 `android.aflags` 和 `android.game_intervention_list` 场景感知数据源在当前章节中未深入分析。根据源码调研，这两个数据源是 Android 13+ 后新增的特殊数据源，分别抓取 features.xml 开关状态和 Game Mode 干预策略，属于 Peretto 与 Android 系统深度集成的重要特性。

### 重要程度
高

### 建议研究方向
- 深入分析 `android.aflags` 数据源的内部实现机制，研究其与 Android Runtime 的交互方式
- 调研 `android.game_intervention_list` 数据源的性能影响和实际应用场景
- 分析这两个场景感知数据源在 Android 17 中的具体实现和配置方式
- 研究这些数据源与其他数据源之间的依赖关系和协同工作机制

### 关联章节
- 13.1 Perfetto 基础架构
- 13.20 Android Runtime 集成机制
- 13.22 游戏性能分析专题

---

## [2026-07-03] 13.21 Perfetto 版本演进与 Android 9-17 新特性验证 — 知识盲区

### 盲区描述
heapprofd 使用 __SIGRTMIN+4 和 __SIGRTMIN+6 信号进行线程间通信的机制在当前章节中未详细说明。这两个信号分别用于 Native 调用栈采样和 Java HPROF 周期 dump 的线程间同步，是 heapprofd 双 producer 模型的重要组成部分。

### 重要程度
中

### 建议研究方向
- 分析 heapprofd 信号机制的具体实现细节和线程同步策略
- 研究信号传递与共享内存的协同工作机制
- 调研信号处理中的错误处理和边界情况
- 分析多 session 环境下的信号冲突解决方案

### 关联章节
- 13.19 内存分析工具演进
- 13.23 Android 性能调优实战