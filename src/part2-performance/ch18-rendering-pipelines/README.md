# 第 18 章：渲染链路全景

> 本章系统梳理 Android 系统中的主流出图路径，从 Android View 标准路径一路走到游戏引擎、Flutter、WebView、Camera 等复杂场景。

## 阅读前的底层索引

- **BufferQueue、BLASTBufferQueue 与 Vsync**：后续 SurfaceView、TextureView、Flutter、WebView、Camera 等渲染路径都绕不开这套生产者、消费者和事务同步模型。
- **Frame Timeline 与 JankTracker**：Android 12+ 分析 jank 时，Expected Timeline / Actual Timeline 已经是主要观察入口，不能只盯旧式 Vsync slice。
- **RenderEffect、AGSL、可更新 GPU 驱动、Game Mode API**：这些能力决定现代 UI 特效、驱动更新和游戏渲染调优该从哪里入手。

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

## 阅读建议

- **新手入门**：先看上面的底层索引，再读 `18.1` 了解全貌，然后进入 `18.2` 到 `18.7`
- **性能分析实战**：先读 `18.20`，遇到具体问题时再回到对应章节，并把 BufferQueue / Vsync 放回同一条时序线
- **深度理解**：按 `18.2` → `18.7` → `18.10` → `18.20` 的顺序，把 BLAST、SurfaceControl 和 Frame Timeline 串到一起看
