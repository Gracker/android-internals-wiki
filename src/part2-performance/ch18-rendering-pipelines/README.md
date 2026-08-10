# 第 18 章：渲染链路全景

Android 渲染系统包含多条出图路径。

普通 View、SurfaceView、TextureView、Flutter、WebView、OpenGL ES、Vulkan、Camera 和视频叠加的 Producer、Consumer、同步方式与瓶颈不同。套用一条统一路径会混淆责任边界。

分析前要先确认当前问题经过哪条出图路径，再选择对应的时间点和工具。

## 基础索引

- **BufferQueue、BLASTBufferQueue 与 Vsync**：后续 SurfaceView、TextureView、Flutter、WebView、Camera 等渲染路径都绕不开这套生产者、消费者和事务同步模型。
- **FrameTimeline 与 JankTracker**：Android 12+ 分析 jank 时，Expected Timeline / Actual Timeline 是主要观察入口，不能只看旧式 VSync slice。
- **RenderEffect、AGSL、可更新 GPU 驱动、Game Mode API**：这些能力决定现代 UI 特效、驱动更新和游戏渲染调优该从哪里入手。

三组索引用于确认 Producer、Consumer、同步点和观测入口。具体路径不明确时，应先回到这些对象重新对齐证据。

## 内容索引

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
- `18.24` Advanced Professional Video 与专业视频编解码管线
- `18.25` Jetpack Compose 渲染管线架构
- `18.26` HWUI Vulkan 多队列并行渲染与帧边界管理
- `18.27` Jetpack WebGPU 渲染与计算管线

---

## 阅读建议

- **基础路径**：先看基础索引，再读 `18.1`，然后进入 `18.2` 到 `18.7`。
- **性能分析**：从 `18.20` 开始，遇到具体问题时再回到对应路径，并把 BufferQueue / VSync 放回同一条时间线。
- **组件路径**：按 `18.2 → 18.7 → 18.10 → 18.20` 阅读，连接 BLAST、SurfaceControl 和 FrameTimeline。

针对视频层、Flutter 或 TextureView 等具体问题，可按以下顺序阅读：

1. 确定问题所属的出图路径。
2. 阅读对应组件章节。
3. 使用 `18.20` 的分析方法复核。
