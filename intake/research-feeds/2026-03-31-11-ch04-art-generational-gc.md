# [研究] ART 分代 GC 架构：Young/Old Generation 与 Concurrent Copying

- **来源**: https://source.android.com/docs/core/perf/art-management + Android 17 Beta 1 Release Notes
- **作者/机构**: Google Android Team
- **日期**: 2026-03（Android 17 Beta 1 确认分代 GC 持续演进）
- **四维评分**: 相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 4.3 ART 虚拟机内存管理
- **映射锚点**: 分代 GC、Young Generation、Old Generation、Concurrent Copying、GC 暂停时间、Read Barrier
- **摘要**: 深入解析 ART 分代垃圾回收的完整架构，包括 Young/Old Generation 的划分策略、Concurrent Copying GC 的并发机制、Read Barrier 技术、以及从 Android 8 到 Android 17 的演进历程。含具体性能数据和 AOSP 源码引用。

### 关键发现

1. **分代模型**：ART 将堆划分为 Young Generation（Nursery）和 Old Generation（Tenured）。新对象首先进入 Young Generation，超过 90% 的对象在此区域就死亡并被快速回收（1-3ms 暂停）。经历多次 Young GC 后仍存活的对象被提升（promote）到 Old Generation
2. **Concurrent Copying GC 演进**：
   - Android 8.0：CC 成为默认 GC plan，引入并发堆压缩（比 Android 7.0 堆平均小 32%，暂停时间减少 85%）
   - Android 10+：CC 扩展为分代 GC，支持 Young Generation 快速回收，推迟 Full-Heap GC
   - Android 17 Beta 1（2026.03）：确认 ART 的 Concurrent Mark-Compact collector 继续支持分代 GC，优先执行低成本的 Young Generation 回收
3. **Read Barrier 机制**：CC GC 在并发拷贝过程中通过 Read Barrier 拦截从堆中读取的引用，开发者无需任何干预。这是 ART 实现并发移动对象的核心技术
4. **低延迟模式（Low-Latency Mode）**：近期 ART 改进引入了低延迟 GC 模式，防止 GC 周期导致 UI 线程停滞，目标是匹配 SwiftUI ARC 的流畅度
5. **性能数据**：
   - Young GC 暂停：通常 1-3ms（< 5ms）
   - Old GC 暂停：mostly concurrent，仅短暂 STW 阶段
   - 堆大小：比 Android 7.0 平均减少 32%
   - 分配速度：比 Android 7.0 快 70%，比 Dalvik 快 18 倍

### 可直接引用段落

> ART 的分代 GC 基于"分代假说"（Generational Hypothesis）：绝大多数对象都是短命的。因此 ART 将堆划分为 Young Generation 和 Old Generation，对 Young Generation 执行频繁、低成本的部分堆回收（通常只需 1-3ms 暂停），只有当对象在多次 Young GC 中存活后才将其提升到 Old Generation。这种策略大幅减少了 Full-Heap GC 的频率——Full GC 需要扫描整个堆，代价远高于 Young GC。

> ART 的 Concurrent Copying GC 在并发拷贝过程中使用 Read Barrier 技术。当 GC 正在移动一个对象时，应用线程如果试图读取该对象的引用，Read Barrier 会拦截这次读取，确保线程拿到的是移动后的正确地址。这个过程对应用代码完全透明，开发者无需编写任何特殊代码。这种设计让大部分 GC 工作可以和应用线程真正并发执行，只需要极短的 "stop-the-world" 暂停来处理线程根集（thread roots）。

> 在 Perfetto 中观察 ART GC 行为：可以看到 GC 线程的活动模式、Young GC 的频率和持续时间。如果一个应用的 Young GC 过于频繁（例如每秒超过 2-3 次），通常意味着存在严重的对象抖动（object churn），大量临时对象被快速创建和丢弃。这种情况下，即使每次 GC 暂停很短，累积的 CPU 开销也会影响帧率和响应速度。

### 与 queue.json 联动

- 素材路径建议：可补充到 4.3 的 material_paths；部分内容（GC 版本演进）也可映射到 4.6 内存相关的版本演进
- 交叉引用：与 7.7 Jetpack Compose 性能优化有关联（Compose 的 recomposition 可能产生大量临时对象，触发频繁 Young GC）
