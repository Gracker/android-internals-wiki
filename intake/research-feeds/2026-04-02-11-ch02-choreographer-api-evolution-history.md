## [研究] Choreographer API 演进史：从 Project Butter 到 Android 17
- **来源**：developer.android.com (official docs) + cs.android.com (AOSP source) + android-developers.googleblog.com
- **作者/机构**：Google Android Team
- **日期**：2026-04-02
- **四维评分**：相关性 4/5 · 技术深度 4/5 · 时效性 4/5 · 可验证性 5/5 · **总分 17/20**
- **映射章节**：2.4 Choreographer 与渲染流水线
- **映射锚点**：版本演进、API 变更、常见问题与误区
- **摘要**：梳理 Choreographer 从 Android 4.1 引入到 Android 17 的完整 API 演进：FrameCallback（API 16）→ NDK Choreographer（API 24）→ 刷新率回调（API 30）→ VsyncCallback + FrameTimeline 多时间线选择（API 33）→ ARR 自适应刷新率（Android 16）→ DeliQueue 无锁队列（Android 17）。

### 关键发现
1. **API 16（Android 4.1, Project Butter）**：引入 `Choreographer.FrameCallback`，提供帧开始渲染时间。doFrame 按顺序执行 CALLBACK_INPUT → CALLBACK_ANIMATION → CALLBACK_INSETS_ANIMATION → CALLBACK_TRAVERSAL → CALLBACK_COMMIT
2. **API 24（Android 7.0, NDK）**：C++ 版 Choreographer 可用，Native 代码可直接接收 VSync 回调
3. **API 30（Android 11）**：引入刷新率回调注册/注销 API。注意 `Display.getRefreshRate()` 可能在回调后短时间内返回旧值，推荐用 `DisplayListener.onDisplayChanged` 获取准确刷新率
4. **API 33（Android 13, 关键里程碑）**：
   - 引入 `Choreographer.VsyncCallback` 和 `AChoreographer_postVsyncCallback`
   - `AChoreographerFrameCallbackData` 负载提供多个可能的帧时间线（frame timelines），允许应用根据渲染截止时间和期望呈现时间选择时间线
   - 应用可以在渲染截止时间过近时动态简化渲染
   - 旧设备可 fallback 到 `AChoreographer_postFrameCallback64` 或 `AChoreographer_postFrameCallback`
5. **Android 16（API 36）**：引入 `Display.hasArrSupport()` 和 `Display.getSuggestedFrameRate()` 支持自适应刷新率（ARR）。`RecyclerView 1.4` 内置 ARR 支持，快速滚动时临时提升刷新率
6. **Android 17（API 37）**：DeliQueue 无锁 MessageQueue（详见 Feed 1），间接提升 Choreographer doFrame 效率

### 可直接引用段落
> API Level 33 brought a significant update with Choreographer.VsyncCallback and AChoreographer_postVsyncCallback. This empowered apps to follow proper frame pacing more precisely and even choose a future frame to render. The AChoreographerFrameCallbackData payload provides information about multiple possible frame timelines, allowing apps to select a timeline based on their rendering deadline and desired presentation time.

> Android 16 introduced new APIs like Display.hasArrSupport() and Display.getSuggestedFrameRate() to enable applications to actively participate in adaptive refresh rate optimization. This allows the system to intelligently switch the display's refresh rate to match content, saving battery and providing smoother experiences during animations or scrolling.

### 与 queue.json 联动
- 优先级调整建议：建议维持 §2.4 priority 90
- 素材路径建议：直接补充到 §2.4 material_paths，为"版本演进"节和"常见问题与误区"节提供素材
- 可为 doFrame 伪代码修正提供 API 33+ FrameData/FrameTimeline 的正确用法参考
