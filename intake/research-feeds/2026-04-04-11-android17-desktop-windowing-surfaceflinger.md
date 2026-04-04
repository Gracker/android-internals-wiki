## [研究] Android 16/17 Desktop Windowing 与 SurfaceFlinger 渲染管线影响
- **来源**：https://android-developers.googleblog.com/2025/05/android-16-beta.html + https://android-developers.googleblog.com/2026/02/android-17-beta.html
- **作者/机构**：Google Android Team
- **日期**：2025-05~2026-03
- **四维评分**：相关性 4/5 · 技术深度 3/5 · 时效性 5/5 · 可验证性 4/5 · **总分 16/20**
- **映射章节**：§2.6 SurfaceFlinger 与合成 / §2.9 渲染机制的版本演进 / §16 窗口与显示
- **映射锚点**：SurfaceFlinger 合成流程、多窗口渲染、版本演进时间线
- **摘要**：Android 16 引入原生桌面窗口化支持，Android 17 Beta 2 新增"Bubbles"浮动窗口模式。这些多窗口形态要求 SurfaceFlinger 管理更复杂的场景图（更多独立可调整 Surface），对外接显示器的跨分辨率/跨刷新率合成提出了新的性能要求。

### 关键发现
1. **Android 16 QPR3（2026-03）外接显示器支持 GA**：从 QPR1 Beta 2 开发者预览到正式可用，Android 手机连接外接显示器后可进入完整桌面窗口环境，SurfaceFlinger 需处理独立的桌面会话。
2. **Android 17 Beta 2 "Bubbles"窗口模式**：不同于消息气泡，这是任意 App 都可以浮动窗口打开的新模式。大屏设备还有"bubble bar"用于管理浮动窗口。SurfaceFlinger 需高效管理更多独立可调整 Surface 的合成。
3. **Desktop Windowing 最小化按钮**：Android 16 Beta 3 为桌面窗口化的 App 标题栏添加了最小化按钮，SurfaceFlinger 需处理 Surface 的可见性生命周期管理。
4. **对 Perfetto 分析的影响**：多窗口场景下，SurfaceFlinger Track 中的合成就绪时间可能增加，Layer 数量动态变化，需要在 Trace 分析时考虑窗口形态的影响。

### 可直接引用段落
> Android 16 introduces native desktop windowing support, enabling users to run multiple applications simultaneously in resizable windows on compatible phones, tablets, and foldables. Connected display support moved from developer preview in Android 16 QPR1 Beta 2 to general availability with Android 16 QPR3. (source: Google Blog)

> Android 17 Beta 2 introduces "Bubbles" as a new windowing mode, allowing users to open virtually any app in a floating window. On larger screens, a "bubble bar" within the taskbar assists in organizing and managing these floating app windows. (source: Google Blog)

### 与 queue.json 联动
- 优先级调整建议：建议关注 freshness-003（§2.6 SurfaceFlinger）中 Desktop Windowing 对 SurfaceFlinger 性能的具体影响
- 素材路径建议：可补充到 §2.6 和 §2.9 的 material_paths
