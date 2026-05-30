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