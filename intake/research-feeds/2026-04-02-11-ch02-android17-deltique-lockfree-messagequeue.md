## [研究] Android 17 DeliQueue：无锁 MessageQueue 对 Choreographer doFrame 性能的影响
- **来源**：https://android-developers.googleblog.com/ + https://cs.android.com/ (AOSP android-17-preview)
- **作者/机构**：Google Android Framework Team
- **日期**：2026-04-02
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 5/5 · 可验证性 5/5 · **总分 20/20**
- **映射章节**：2.4 Choreographer 与渲染流水线 / 1.5 线程模型
- **映射锚点**：doFrame 实现、版本演进、Perfetto Track 对照、线程模型
- **摘要**：Android 17（API 37）引入 DeliQueue——一个无锁 MessageQueue 实现，通过 Treiber Stack + Min-Heap 架构消除主线程锁竞争，实测减少 15% 主线程锁等待时间、4% 应用掉帧、7.7% SystemUI 掉帧、9.1% 冷启动首帧延迟（P95）。

### 关键发现
1. **DeliQueue 架构**：消息插入使用 Treiber Stack（无锁并发栈，基于原子 CAS 操作），消息处理使用 Min-Heap（Looper 线程独占）。两者完全分离，消除了插入和取出之间的锁竞争
2. **性能数据（Google 内部 Beta）**：
   - 多线程插入繁忙队列：最高 5000x 提速（对比旧 monitor lock 实现）
   - 主线程锁竞争时间：减少 15%
   - 应用掉帧率：减少 4%
   - SystemUI + Launcher 掉帧率：减少 7.7%
   - 冷启动到首帧绘制时间（P95）：改善 9.1%
3. **Choreographer doFrame 关联**：Choreographer 通过 `FrameHandler.handleMessage` 触发 `doFrame()`。旧架构中，后台线程持有 MessageQueue monitor lock 时会阻塞 UI 线程处理 doFrame 消息 → 导致掉帧。DeliQueue 消除了这一瓶颈
4. **Perfetto 中的观察**：在 Perfetto 中，旧架构可见 UI 线程频繁进入 `MONITOR_LOCK` 状态（对应 `MessageQueue.enqueueMessage` → `object.wait()`），DeliQueue 后这些 lock 等待 slice 将消失
5. **兼容性注意**：反射 MessageQueue 私有字段的应用可能崩溃。Espresso 需升级到 3.7.0+。可通过调试开关临时禁用 DeliQueue

### 可直接引用段落
> DeliQueue employs a lock-free data structure that uses atomic memory operations, effectively separating the insertion of messages (managed by a Treiber stack) from their processing (handled by a min-heap exclusively owned by the Looper thread). This design allows threads to operate without blocking each other.

> Internal beta testing revealed a 15% reduction in app main thread time spent in lock contention, a 4% decrease in missed frames within applications, a 7.7% reduction in missed frames during System UI and Launcher interactions, and a 9.1% improvement in the time from app startup to the first frame drawn at the 95th percentile.

### 与 queue.json 联动
- 优先级调整建议：建议将 §2.4 的 priority 维持 90（当前为 90，无需调整）
- 素材路径建议：可补充到 §2.4 的 material_paths，为"版本演进"节和"与其他机制的关系"节提供直接素材
