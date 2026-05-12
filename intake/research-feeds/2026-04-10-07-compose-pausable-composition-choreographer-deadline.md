## [研究] Compose Pausable Composition 内部实现与 Choreographer FrameData Deadline 协作机制
- **来源**: https://shreyaspatil.dev / https://composables.com / https://android-developers.googleblog.com
- **作者/机构**: Shreyas Patil / Composables / Google Android Team
- **日期**: 2025-12 ~ 2026-04
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**: 2.4 Choreographer 与渲染流水线
- **映射锚点**: Compose 对 Choreographer 的使用差异（行408-419）、PausableComposition 内部控制流、shouldPause 回调与 FrameData deadline 判定
- **摘要**: Jetpack Compose 1.7 引入 PausableComposition 作为内部性能优化机制，1.10（2025年12月稳定）将其设为默认行为。该机制通过 setPausableContent() → PausedComposition 对象 → resume() + shouldPause 回调 → apply() 的控制流，在 FrameData deadline 临近时暂停 Composition，避免帧超时导致的 jank。

### 关键发现

1. **PausableComposition 控制流**：`setPausableContent()` 不立即组合 UI，而是返回 `PausedComposition` 控制器对象。预取系统（如 LazyColumn）反复调用 `resume()` 执行分块的组合工作。每次 resume() 内部，Compose runtime 通过 `shouldPause` lambda 频繁检查帧截止时间。

2. **shouldPause 与 FrameData deadline 判定**：当 shouldPause 返回 true（即帧截止时间临近），Composition 暂停，主线程让出给当前帧的绘制任务。这不是协程的 CancellationException 机制，而是 Compose runtime 内部的专用中断点——基于 Composition tree 结构支持，在 Node 树的特定位置插入可暂停的 checkpoint。

3. **LazyList 预取集成**：PausableComposition 与 LazyColumn/LazyRow 的预取系统深度集成。在空闲时间增量组合即将滚动到可见区域的列表项，显著减少主线程的即时工作量。Compose 1.9 的 CacheWindow API 进一步利用了 pausable composition。

4. **apply() 提交机制**：当 resume() 返回 isComplete=true 时，调用 apply() 将所有计算出的 UI 变更提交到实际 UI 树。内部 applyChanges() 负责回放缓冲命令、分发生命周期回调（onRemembered）和运行排队的 SideEffect。未完成的 UI 树不会被渲染。

5. **与 1.7 之前行为的对比**：在 Compose 1.7 之前，Composition 必须在单个帧内完成，无法中断。复杂 UI（如长 LazyColumn）的组合时间可能超过 16.67ms 帧预算，直接导致 jank。PausableComposition 彻底改变了这一约束。

### 可直接引用段落

> PausableComposition enables the Compose runtime to perform "prep work" for UI elements asynchronously, often utilizing the idle time between frames. Instead of attempting to compose an entire complex UI element within a single 16.7-millisecond frame, PausableComposition allows the runtime to break down the composition into smaller, more manageable pieces and prepare this work before the UI is actively needed on screen.
>
> The "magic" of pausing lies within the shouldPause callback passed to the resume() function. The Compose runtime frequently invokes this lambda during composition. If shouldPause returns true—critically, when the frame deadline is approaching—the composition process halts, relinquishing the main thread to allow for more critical tasks, such as drawing the current frame.

> Jetpack Compose 1.10, which became stable in December 2025, marked a significant milestone by introducing pausable composition as a default behavior. Applications utilizing Compose 1.10 or newer automatically benefit from this performance enhancement without requiring any explicit code changes.

### 与 queue.json 联动
- 优先级调整建议：§2.4 Choreographer 的 deep tech review 问题"Compose pausable composition 暂停条件与实现原理"可由此素材直接回应，建议将 §2.4 优先级保持 85
- 素材路径建议：补充到 §2.4 的 material_paths
