## [2026-05-31] 18.13 WebView 渲染管线 — 知识盲区

### 盲区描述
Android 12+ 中 WebView SurfaceControl 的具体性能对比数据缺失，无法量化独立子 Surface vs Functor 路径的性能差异

### 重要程度
高

### 建议研究方向
- 在不同设备上测试 WebView SurfaceControl 路径的内存占用、帧率稳定性、GPU 负载对比
- 收集 Functor 路径在重负载页面下对主窗口渲染的影响数据
- 分析 SurfaceControl 在低内存设备上的 fallback 机制

### 关联章节
18.13 WebView 渲染管线
18.10 SurfaceControl API 深入
7.11 WebView 渲染性能与优化

## [2026-05-31] 18.15 视频叠加与 HWC — 知识盲区

### 盲区描述
缺少厂商特定 HWC 实现差异及其对视频合成决策影响的系统性研究

### 重要程度
高

### 建议研究方向
- 收集主流厂商（Qualcomm、MediaTek、Samsung）HWC 实现的差异
- 分析不同厂商在 YUV/RGBA 视频层处理、HDR 支持等方面的能力差异
- 研究厂商特定 bug 和优化建议

### 关联章节
18.15 视频叠加与 HWC
2.6 SurfaceFlinger 与合成
18.6 SurfaceView

## [2026-05-31] 18.15 视频叠加与 HWC — 知识盲区

### 盲区描述
HDR 视频在 HWC 合成中的特殊处理机制和限制条件研究不足

### 重要程度
中

### 建议研究方向
- 分析 HDR 视频层在 HWC 中的特殊处理流程
- 研究 HDR 色域转换对性能的影响
- 收集不同平台 HDR 视频回退到 GPU 的典型案例

### 关联章节
18.15 视频叠加与 HWC
2.10 GPU 渲染深入
18.6 SurfaceView