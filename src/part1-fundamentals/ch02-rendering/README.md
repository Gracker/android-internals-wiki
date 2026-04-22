# 第 2 章：渲染系统

如果说 Android 性能问题里哪条链路最容易被频繁遇到，那大概率就是渲染链路。

列表滑动卡顿、页面切换不顺、动画发飘、首帧出来太慢，最后几乎都会回到同一组角色：VSync、Choreographer、主线程、RenderThread、SurfaceFlinger、BufferQueue。  
这也是为什么很多“看上去像业务问题”的现象，最后往往要回到图形系统里找答案。

这一章的目标，不是只把渲染流程背下来，而是让读者脑子里真正有一条“从 `invalidate()` 到屏幕像素”的路线图。后面不管看 Perfetto、做 jank 分析，还是判断问题更像 App 侧还是系统侧，都要反复回到这里。

## 本章内容

- Android 渲染架构全景
- 帧率与刷新率
- VSync 机制
- Choreographer 与渲染流水线
- MainThread 与 RenderThread 协作
- SurfaceFlinger 与合成
- Hardware Layer
- 过度绘制
- 渲染机制的版本演进

## 阅读建议

- 如果你想先建立整体图景，推荐按 `2.1 → 2.3 → 2.4 → 2.5 → 2.6` 的顺序读。
- 如果你当前最关心的是卡顿分析，`2.4`、`2.5`、`2.6` 和第 7 章配合起来读最有用。
- 如果你后面准备进入更复杂的渲染路径（如 SurfaceView、TextureView、Flutter、WebView），这一章是 `18` 章的前置基础。
