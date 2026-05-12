# [研究] MotionEventPredictor 与低延迟图形渲染：Android 输入延迟优化的两条路径

- **来源**: developer.android.com (motion-prediction + low-latency-graphics)
- **作者/机构**: Google Android Team / Jetpack
- **日期**: 2026-04-05（graphics-core 1.0.4 最新版）
- **四维评分**: 相关性 5/5 · 技术深度 4/5 · 时效性 5/5 · 可验证性 5/5 · **总分 19/20**
- **映射章节**: 3.4 输入延迟与预测输入技术
- **映射锚点**: MotionEventPredictor API、前缓冲渲染、GLFrontBufferedRenderer、CanvasFrontBufferedRenderer、LowLatencyCanvasView、Kalman Filter 预测算法
- **摘要**: Android 提供两条互补路径降低输入到显示的延迟：MotionEventPredictor 通过 Kalman Filter 预测未来触控点降低感知延迟，低延迟图形库通过前缓冲渲染绕过多缓冲交换降低实际渲染延迟。两者组合可实现从触控到显示的最短路径。

### 关键发现

1. **MotionEventPredictor (androidx.input.motionprediction)**: 基于 Kalman Filter 算法预测未来 MotionEvent 对象（坐标/压力/时间戳）。record() 记录真实事件，predict() 返回预测事件。兼容 API 19+，新版本可利用系统级预测 API。核心价值：在真实触控数据到达前渲染预测点，使笔迹类应用体验接近纸笔。

2. **前缓冲渲染 (Front Buffer Rendering)**: 绕过传统三缓冲的 buffer swap 流程，直接写入显示正在使用的前缓冲区。适用于局部更新（如笔画绘制），不适合全屏重绘（会撕裂）。API 29+ 可用，ChromeOS Android 11+。

3. **Jetpack 三层 API 体系**:
   - GLFrontBufferedRenderer: OpenGL 前缓冲 + 多缓冲双模式
   - CanvasFrontBufferedRenderer: 硬件加速 Canvas 到 HardwareBuffer（回溯到 API 29）
   - LowLatencyCanvasView: 最简方案，内部管理 SurfaceView，与 View 层级同步
   - graphics-core 当前版本 1.0.4，graphics-shapes 1.1.0（2025.10 发布）

4. **组合优化**: MotionEventPredictor 解决感知延迟，前缓冲渲染解决实际渲染延迟。stylus 抬起后自动切回多缓冲模式持久化内容。这是 Google 推荐的触控/手写应用最佳实践。

### 可直接引用段落

> The MotionEventPredictor employs a mathematical prediction algorithm, specifically the Kalman Filter, to estimate where the user's input will go next. These predicted events are then provided to the renderer, allowing for immediate visual feedback.

> The "front buffer" is the memory directly used by the display for rendering. By writing directly to this buffer, the system bypasses the buffer-swapping process, resulting in faster rendering to the screen. This technique is most effective for small, localized updates, such as drawing a stylus stroke.

> The low-latency graphics library, available for Android 10 (API level 29) and higher, aims to reduce the processing time between stylus input and screen rendering. When a stylus is lifted, regular multi-buffered rendering can resume to persist the work.

### 与 queue.json 联动
- 优先级调整建议：建议将 §3.4 的 priority 从 80 提升到 90（Jetpack 官方库支撑，有完整 API 文档和实现代码）
- 素材路径建议：补充到 §3.4 的 material_paths
