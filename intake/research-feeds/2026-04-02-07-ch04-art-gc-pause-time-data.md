## [研究] ART GC 暂停时间精确数据与分代收集器演进

- **来源**：https://source.android.com/docs/art (ART GC overview) + AOSP art/runtime/gc/collector/concurrent_copying.cc
- **作者/机构**：Google ART Team / AOSP
- **日期**：2024-2026（持续演进）
- **四维评分**：相关性 5/5 · 技术深度 5/5 · 时效性 4/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：4.6 内存相关的版本演进 / 4.3 ART 虚拟机内存管理
- **映射锚点**：GC 暂停时间演进 / 分代 GC / ConcurrentCopying
- **摘要**：ART CC（Concurrent Copying）收集器从 Android 8.0 引入，暂停时间比 Android 7.0 降低 85%。Android 10+ 分代 GC 年轻代暂停 1-3ms（平均 1.83ms）。Android 17 进一步集成分代 GC 到 CC 收集器，减少 CPU 开销。章节标题"亚毫秒"应修正为"暂停时间大幅降低"或补充 Android 17 的目标数据。

### 关键发现
1. **Android 8.0 CC 收集器**：引入并发复制收集器，暂停仅处理线程 root，暂停时间不再随堆大小线性增长。相比 Android 7.0，H2 benchmark 暂停时间减少 85%
2. **Android 10+ 分代 CC**：年轻代收集暂停 1-3ms（实测平均 1.83ms），足够避免大多数应用掉帧（16.67ms@60fps）。>90% 对象在年轻代即被回收
3. **Android 17 分代 GC 增强**：将分代收集正式集成到 CC 收集器中，优先执行低成本的年轻代收集，减少全堆 GC 频率
4. **标题准确性**：当前 4.6 章节标题称"亚毫秒"，但实际数据为 1-3ms——应修正为"暂停时间大幅降低"或补充未来目标

### 可直接引用段落
> ART introduced a concurrent compacting garbage collector in Android 8.0 (Oreo), significantly reducing pause times by compacting the heap while the app is running. This collector involves only one short pause for processing thread roots, and its pause times no longer scale with heap size. For the H2 benchmark, it offered 85% smaller pause times compared to Android 7.0's GC.
> — source.android.com/docs/art

> Modern ART, from Android 10 onwards, utilizes a generational, mostly concurrent garbage collector. Young generation collections typically result in pauses of 1-3 milliseconds. An average pause time of 1.83 milliseconds has been observed, which is considered low enough to prevent missed frames in most applications.
> — android.com performance documentation

> Android 17 integrates generational garbage collection into ART's Concurrent Mark-Compact collector. This optimization prioritizes frequent, low-cost young generation collections, efficiently sweeping up short-lived objects and reducing overall processing power needed for GC.
> — Android 17 Developer Preview documentation

### AOSP 源码路径
- art/runtime/gc/collector/concurrent_copying.h — CC 收集器头文件
- art/runtime/gc/collector/concurrent_copying.cc — CC 收集器实现
- art/runtime/gc/heap.cc — 分代堆管理

### 与 queue.json 联动
- 优先级调整建议：4.6 review issue "标题称降至亚毫秒但正文数据为 1-3ms" 可用本素材精确数据支撑标题修正
- 素材路径建议：追加到 4.6 的 material_paths
