## [研究] Android 16 Adaptive Refresh Rate 与 SurfaceFlinger/Choreographer 帧调度协同
- **来源**：https://developer.android.com/reference/android/view/Choreographer + https://android-developers.googleblog.com/2025/adaptive-refresh-rate.html
- **作者/机构**：Google Android 团队
- **日期**：2025-2026
- **四维评分**：相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**：2.3 VSync 机制 / 2.5 Choreographer 与渲染流水线 / 6.2 Doze 与省电模式
- **映射锚点**：VSync 周期动态调整、Choreographer 回调管理、SurfaceFlinger 刷新率选择、Frame Pacing Library (Swappy)

### 摘要
Android 16 完善了 Adaptive Refresh Rate (ARR)，使屏幕刷新率能根据内容动态调整。SurfaceFlinger 在 DisplayManager 策略指导下，基于活跃 layer 的平均 FPS 启发式决定刷新率。新增 API 包括 hasArrSupport()、getSuggestedFrameRate(int)、getSupportedRefreshRates()。RecyclerView 1.4 内置 ARR 支持，在 fling/scroll 时动态提升刷新率。

### 关键发现
1. **ARR 刷新率选择机制**：SurfaceFlinger 在 DisplayManager 高层策略指导下，基于活跃 layer 及其平均 FPS 使用启发式算法选择实际刷新率——即使 App 没有显式请求
2. **新增 API**：hasArrSupport() 检测设备支持、getSuggestedFrameRate(int) 查询最优帧率、getSupportedRefreshRates() 列出可用刷新率
3. **RecyclerView 1.4 集成**：在 fling/smooth scroll 操作中自动提升刷新率，实现无 jank 滚动体验
4. **VSync 离散步进**：ARR 使用离散 VSync 步进匹配内容帧率，避免了频繁模式切换导致的 jank
5. **Swappy 帧 pacing 库**：OpenGL/Vulkan 游戏通过 Android Frame Pacing Library 实现正确的帧节奏——利用 Choreographer 同步 + presentation time + sync fence 防止 buffer stuffing

### 可直接引用段落
> SurfaceFlinger, guided by the DisplayManager's high-level policy, determines the actual display refresh rate. It can use heuristics based on active layers and their average FPS to decide the refresh rate, even without explicit requests from applications. ARR enables the display to dynamically adjust its refresh rate to match the frame rate of the content being displayed, utilizing discrete VSync steps.
> — Android Developer Documentation, 2025-2026

### 与 queue.json 联动
- 素材路径建议：可补充到 2.3 VSync 机制 和 2.5 Choreographer 节
