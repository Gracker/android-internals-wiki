## [研究] Android 17 DeliQueue：无锁 MessageQueue 重构及其对渲染管线的影响
- **来源**：https://android-developers.googleblog.com/2026/03/android-17-lock-free-messagequeue.html
- **作者/机构**：Google Android 团队
- **日期**：2026-03
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**：2.5 Choreographer 与渲染流水线 / 5.1 滑动卡顿分析
- **映射锚点**：Choreographer doFrame 调度、主线程 MessageQueue 锁竞争、掉帧分析

### 摘要
Android 17 引入 DeliQueue，用无锁数据结构替代传统 MessageQueue 的 monitor lock 实现。核心设计是 Treiber 栈（无锁并发插入）+ 单线程最小堆（消息处理），分离了生产者和消费者路径。实测数据：主线程锁竞争时间减少 15%，App 掉帧减少 4%，SystemUI/Launcher 掉帧减少 7.7%-9.1%，App 启动到首帧绘制 P95 改善 9.1%。

### 关键发现
1. **根因定位**：旧 MessageQueue 使用单一 monitor lock 管理主线程任务队列，后台线程 post 消息时会阻塞高优先级 UI 线程，产生优先级反转和掉帧
2. **架构设计**：DeliQueue 采用混合结构——无锁 Treiber 栈处理多线程并发插入（合成基准测试中比旧实现快 5000 倍），Looper 线程独占的最小堆处理消息消费
3. **性能数据**：Perfetto trace 显示主线程锁竞争时间减少 15%；App 掉帧减少 4%；SystemUI/Launcher 掉帧减少 7.7%-9.1%
4. **兼容性注意**：使用反射访问 MessageQueue 私有字段（如 mMessages）的代码会失效——mMessages 在新实现中始终为 null
5. **Perfetto 影响**：可直接在 trace 中观察到锁竞争减少，对分析主线程 jank 有直接影响

### 可直接引用段落
> DeliQueue is a hybrid data structure combining a lock-free Treiber stack for concurrent message insertion and a single-threaded min-heap for message processing. This separation allows multiple threads to push new messages without contention, while the Looper thread exclusively processes messages from the min-heap without needing additional synchronization. Perfetto traces have shown a 15% reduction in app main thread time spent in lock contention, translating to a 4% reduction in missed frames in apps and a 7.7% to 9.1% reduction in missed frames in the System UI and Launcher.
> — Android Developers Blog, 2026-03

### 与 queue.json 联动
- 优先级调整建议：建议将 2.5 Choreographer 与渲染流水线的 priority 提升到 85（此素材提供了 Android 17 重大变更的关键数据）
- 素材路径建议：可补充到 2.5 节的 material_paths
