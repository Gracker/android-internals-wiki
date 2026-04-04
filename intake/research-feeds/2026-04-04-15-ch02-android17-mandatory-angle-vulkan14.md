## [研究] Android 17 强制 ANGLE + Vulkan 1.4：OpenGL ES 路径的根本性转变
- **来源**：https://developer.android.com/about/versions/17 + https://android-developers.googleblog.com/ + https://vulkan.org/
- **作者/机构**：Google Android Graphics Team / Khronos Group
- **日期**：2026-02-14（Android 17 Beta 1）~ 2026-03（Beta 3 Platform Stability）
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 4/5 · **总分 18/20**
- **映射章节**：2.10 GPU 渲染深入 / 2.9 渲染机制的版本演进
- **映射锚点**：ANGLE 架构、Vulkan 支持、GPU HAL 演进、版本演进表格
- **摘要**：Android 17（API 37）实现两个重大图形栈转变：(1) 新设备强制使用 ANGLE 作为 OpenGL ES 实现层（从 allowlist 转为 denylist 模型，所有 App 默认通过 ANGLE→Vulkan 路径，仅排除列表中的 App 例外）；(2) 支持 Vulkan 1.4。OpenGL ES 不再有活跃特性开发，转为维护模式。

### 关键发现
1. **ANGLE 强制化策略演进**：
   - Android 15：ANGLE 作为可选层，仅特定 App 使用
   - Android 16：新设备要求特定 App 使用 ANGLE（allowlist 模式）
   - **Android 17：新设备要求大部分 App 使用 ANGLE（denylist 模式）**——所有 App 默认通过 ANGLE→Vulkan，仅 denylist 中的 App 例外
   - 本质：ANGLE 成为系统 GL 驱动，原生 OpenGL ES 驱动逐步退出新设备
2. **Vulkan 1.4 支持**：Android 17 支持 Vulkan 1.4 规范。自 Android 16 起 Vulkan 已成为 Android 官方图形 API（Android 10 起新 64 位设备必须支持 Vulkan）。目前 85%+ 活跃设备支持 Vulkan
3. **OpenGL ES 维护模式**：
   - Google 明确声明 OpenGL ES 不再有活跃特性开发
   - 旧版 OpenGL ES 1.0/1.1 已弃用
   - 对新项目强烈推荐直接使用 Vulkan（更低 CPU 开销、光线追踪、bindless API 等高级特性）
4. **性能影响**：
   - ANGLE 作为兼容层引入翻译开销，部分场景可能降低帧率
   - 但测试显示许多游戏通过 ANGLE 性能与原生驱动持平甚至更好
   - 图形密集型应用建议直接使用 Vulkan
   - Pipeline 创建延迟和启动开销需要预热 Pipeline Cache 缓解
5. **驱动质量提升**：强制 ANGLE 意味着所有 GPU 厂商的 Vulkan 驱动将面对更广泛的内容测试 + Android 17 新增认证测试 → 驱动质量整体提升

### 可直接引用段落
> For Android 17, newer devices will implement OpenGL ES capabilities primarily through ANGLE translating to Vulkan, rather than through a direct, native OpenGL ES driver. This represents a shift from an allowlist approach to a denylist model, where all applications use ANGLE unless explicitly excluded.

> OpenGL ES is no longer under active feature development, as Google is transitioning to a modern, unified rendering stack centered on Vulkan. For new development projects, using Vulkan directly is strongly recommended for optimal performance.

> Testing indicates that for many games, the performance impact of ANGLE is minimal, with some even showing improved performance compared to native drivers. Pipeline creation delays and startup costs can occur when using ANGLE and Vulkan layers, necessitating warmed-up pipeline caches for optimal performance.

### 与 queue.json 联动
- 优先级调整建议：§2.10 已 finalized，建议在后续 polish 时补充 Android 17 ANGLE 强制化内容到"版本演进"段落
- 素材路径建议：可补充到 §2.9 渲染机制的版本演进（Android 17 行）和 §2.10 的 ANGLE 章节
- 新增建议：建议 §2.9 版本演进表格增加 Android 17 行，标注"ANGLE denylist 强制 + Vulkan 1.4"
