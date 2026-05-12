## [研究] Vulkan 成为 Android 官方图形 API：ANGLE 过渡对渲染管线的影响
- **来源**：https://android-developers.googleblog.com/2025/03/the-road-to-vulkan-on-android.html + https://www.khronos.org/vulkan/
- **作者/机构**：Google Android 团队 + Khronos Group
- **日期**：2025-03
- **四维评分**：相关性 4/5 · 技术深度 3/5 · 时效性 5/5 · 可验证性 4/5 · **总分 16/20**
- **映射章节**：2.1 Android 渲染架构全景 / 2.7 RenderThread 与 Skia 渲染 / 9.1 GPU 与图形 API
- **映射锚点**：Vulkan 替代 OpenGL ES、ANGLE 兼容层、RenderEngine SKIA_GL_THREADED、Swappy Frame Pacing

### 摘要
2025 年 3 月，Google 正式宣布 Vulkan 成为 Android 官方图形 API。85% 的活跃 Android 设备已支持 Vulkan，Unity 新游戏 45%+ 的会话使用 Vulkan 渲染。OpenGL ES 应用通过 ANGLE（Almost Native Graphics Layer Engine）翻译为 Vulkan 调用运行。Android UI 渲染框架也在兼容设备上使用 Vulkan。Vulkan Profile 2025 已发布。

### 关键发现
1. **RenderEngine 演进**：AOSP 中 RenderEngine 有四种类型——THREADED、SKIA_GL、SKIA_GL_THREADED、GLES；Android 13+ 默认使用 SKIA_GL_THREADED，可通过 debug.renderengine.backend 覆盖
2. **ANGLE 兼容性**：ANGLE 作为 OpenGL ES 的系统驱动，将 GL 调用翻译为 Vulkan；2026 年前将成为默认方案，最终成为 OpenGL ES 的唯一可用路径
3. **Vulkan Pre-rotation**：应用需显式处理 surface rotation（pre-rotation），否则 SurfaceFlinger 会导致帧时间增加和 GPU 抢占
4. **Android 15 YV12 问题**：SurfaceFlinger 的 Skia/Ganesh 渲染引擎在 ANGLE/Vulkan 后端上导入 YV12 格式帧（来自视频解码器）时会崩溃——因为 ANGLE/Vulkan 可能无法导入某些平面 YV12 buffer

### 可直接引用段落
> Vulkan is already supported by 85% of active Android devices, and major game engines like Unity and Unreal are increasingly choosing Vulkan as their default renderer. Over 45% of sessions from new games on Unity already utilize Vulkan, with rapid growth anticipated. The Android UI rendering framework also uses Vulkan on compatible devices.
> — Android Developers Blog, 2025-03

### 与 queue.json 联动
- 素材路径建议：可补充到 2.1 Android 渲染架构全景 和 2.7 RenderThread 节
