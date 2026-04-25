# 第 7 章：流畅性

这一章是整本书里最容易被反复翻回来的部分。

因为用户最常抱怨的，就是“卡”。  
而这个“卡”背后，既可能是典型的掉帧，也可能是输入延迟、渲染链路卡住、系统负载高，甚至是一些已经接近 ANR 的问题。要把这些情况分清，不能只靠“看起来像卡”，而要建立一套更稳的判断路径。

这一章的任务，就是先把流畅性问题本身讲透：什么叫 jank，常见根因有哪些，分析时应该先看哪里，优化时该从哪些方向落手。

## 本章内容

- [7.1 卡顿的定义与分类](01-jank-definition.md)
- [7.2 卡顿原因体系](02-jank-causes.md)
- [7.3 卡顿分析方法论](03-jank-methodology.md)
- [7.4 典型场景分析](04-typical-scenarios.md)
- [7.5 优化策略](05-optimization.md)
- [7.6 案例集](06-case-studies.md)
- [7.7 Jetpack Compose 性能优化](07-compose-performance.md)
- [7.8 RecyclerView 列表滑动性能深度优化](08-recyclerview-performance.md)
- [7.9 感知流畅性：步幅波动与无掉帧卡顿](09-perceived-smoothness.md)
- [7.10 图片加载与 Bitmap 性能优化](10-image-bitmap-performance.md)
- [7.11 WebView 渲染性能与优化](11-webview-performance.md)
- [7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销](12-view-layout-performance.md)
- [7.13 SystemUI 性能分析](13-systemui-performance.md)
- [7.14 GAPS：Android 动态分析目标可达性路径重建](14-gaps-dynamic-analysis.md)
- [7.15 场景化性能作战手册](15-scenario-playbooks.md)

## 阅读建议

- 第一次系统学流畅性，按 `7.1 → 7.2 → 7.3` 顺着读，先建立问题框架。
- 正在排查线上卡顿，优先看 `7.3`、`7.4`、`7.6`、`7.15`。
- 关注具体 UI 组件，按技术栈进入 `7.7` 到 `7.13`：Compose、RecyclerView、图片、WebView、View 布局和 SystemUI 分开查。
- 需要把动态分析和性能 trace 接起来，再看 `7.14`，然后回到第 13 章的 Perfetto 工具链。
