# 第 18 章：渲染链路全景

这一章的存在，是因为“渲染系统”这四个字在真实工程里其实包含了很多完全不同的路径。

同样是把内容画到屏幕上，普通 View、SurfaceView、TextureView、Flutter、WebView、OpenGL ES、Vulkan、Camera、视频叠加，背后的生产者、消费者、同步方式和瓶颈都不一样。  
如果把这些场景全都压成一条统一的“渲染管线”，分析时就会非常容易看错责任链。

所以这一章更像是一张“路径地图”。它想做的，不是把所有图形 API 都讲成百科，而是让读者先知道：**这次问题到底走的是哪条出图路径。**

## 阅读前的底层索引

- **BufferQueue、BLASTBufferQueue 与 Vsync**：后续 SurfaceView、TextureView、Flutter、WebView、Camera 等渲染路径都绕不开这套生产者、消费者和事务同步模型。
- **Frame Timeline 与 JankTracker**：Android 12+ 分析 jank 时，Expected Timeline / Actual Timeline 已经是主要观察入口，不能只盯旧式 Vsync slice。
- **RenderEffect、AGSL、可更新 GPU 驱动、Game Mode API**：这些能力决定现代 UI 特效、驱动更新和游戏渲染调优该从哪里入手。

这三组索引并不是附带知识点，而是这一章反复会回来的地基。  
如果读者后面在某条具体路径里迷路，通常回到这三组索引，重新把生产者、同步点和观测入口对齐，问题就会清楚很多。

## 本章内容

- `18.1` 渲染路径分类与选型对照
- `18.2` Android View 标准路径（BLAST 深入）
- `18.3` Android View 软件渲染路径
- `18.4` Android View 混合渲染路径
- `18.5` Android View 多窗口路径
- `18.6` SurfaceView 直出路径
- `18.7` TextureView 合成路径
- `18.8` OpenGL ES 渲染路径
- `18.9` Vulkan 原生渲染路径
- `18.10` SurfaceControl API 深入
- `18.11` ANGLE（GLES-over-Vulkan 翻译层）
- `18.12` Flutter 渲染路径
- `18.13` WebView 渲染路径（四种模式）
- `18.14` Camera 渲染管线
- `18.15` 视频叠加与 HWC
- `18.16` 游戏引擎渲染路径
- `18.17` Hardware Buffer Renderer
- `18.18` PIP 与自由窗口渲染
- `18.19` 可变刷新率渲染管线
- `18.20` 渲染分析方法（含 Frame Timeline / JankTracker 观察）
- `18.21` EyeDropper API 与跨设备协作性能
- `18.22` Android XR 空间 UI 与环境资产渲染性能
- `18.23` 多媒体播放管线：Codec2、Tunneled Playback 与 Media3 ABR

## 参考资料

### Flutter Impeller 着色器编译管线与运行期 PSO 缓存机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-04-flutter-impeller-shader-compilation-pipeline.md
- 类型：DeepResearch 调研结果
- 摘要：Impeller 全 AOT 离线编译策略（GLSL→SPIRV→后端 Shader→FlatBuffers ShaderArchive→C 数组静态链接），运行期零反射加载，Vulkan vk::PipelineCache 落盘 vs GLES 内存表不落盘，消除运行时 shader 编译抖动的架构设计。
- 注入时间：2026-07-05
- 价值：补强 ch18 渲染管线中 Flutter Impeller 着色器编译机制的深度技术分析

---

## 阅读建议

- **新手入门**：先看上面的底层索引，再读 `18.1` 了解全貌，然后进入 `18.2` 到 `18.7`
- **性能分析实战**：先读 `18.20`，遇到具体问题时再回到对应章节，并把 BufferQueue / Vsync 放回同一条时序线
- **深度理解**：按 `18.2` → `18.7` → `18.10` → `18.20` 的顺序，把 BLAST、SurfaceControl 和 Frame Timeline 串到一起看

如果你现在已经带着一个具体问题来读，例如“视频层偶发不稳”“Flutter 页面卡顿”“TextureView 感觉比 SurfaceView 更吃力”，最好的方式通常不是顺序读完整章，而是：

1. 先确定问题属于哪条路径。
2. 再回到对应章节。
3. 最后把 `18.20` 的分析方法拿出来复核。

