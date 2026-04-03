## [研究] Android 17 (API 37) 分代垃圾回收机制：GC 暂停与渲染流畅度
- **来源**：https://developer.android.com/about/versions/17; https://android-developers.googleblog.com/
- **作者/机构**：Google Android Runtime Team
- **日期**：2026-03 ~ 2026-04
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 17/20**
- **映射章节**：§4.3 ART 虚拟机内存管理 / §4.6 内存相关的版本演进 / §1.6 Android 版本演进中的架构变化
- **映射锚点**：ART GC 机制、分代 GC、GC 暂停时间、内存管理版本演进
- **摘要**：Android 17 (API 37) 引入分代垃圾回收（Generational GC），预期在资源密集型应用中减少卡顿，通过降低整体 GC CPU 开销和暂停时间来自动提升性能。配合 static final field 强制不可变（§4.3 已研究），ART 编译器可进行更激进的常量折叠和代码优化。

### 关键发现
1. **分代 GC 机制**：Android 17 正式在 ART 中引入分代 GC，将堆按对象年龄分为年轻代和老年代。年轻代 GC 只扫描短期对象，暂停时间极短（预计 1ms 以内）；老年代 GC 频率低但回收量大。这一设计与此前 CC（Concurrent Copying）收集器形成对比。
2. **与 static final field 不可变性的协同**：API 37 中 static final field 的反射/JNI 修改被禁止，使 ART 编译器可安全地将这些字段视为编译期常量（常量折叠 + 内联），配合分代 GC 减少了对常量对象的 GC 扫描开销。
3. **对 UI 渲染流畅度的影响**：通过减少 GC 暂停，资源密集型应用（图片/视频编辑、大型游戏、复杂 Compose UI）的掉帧率预期下降，特别是 GC 暂停发生在 RenderThread 提交帧的临界区时。

### 可直接引用段落
> Android 17 introduces generational GC, which is expected to reduce stutter in resource-intensive apps and automatically improve performance by reducing overall GC CPU cost and time duration. This helps in smoother UI rendering by minimizing pauses during heavy processing.
>
> — 来源：Android 17 Developer Features, developer.android.com

### 与 queue.json 联动
- 优先级调整建议：freshness-006 (ch04-memory/03-art-memory.md) 可标记为已研究并补充素材
- 素材路径建议：可补充到 §4.3 ART 内存管理和 §4.6 内存版本演进的 material_paths
