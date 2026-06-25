---
title: "Compose 首次组合开销与启动性能"
chapter: "21.15"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [compose, startup, first-composition, baseline-profile, cold-start]
related_chapters: ["21.3", "21.4", "22.3", "22.20", "22.26"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "章节深挖"
---

# 21.15 Compose 首次组合开销与启动性能

<!-- outline-start -->
## 要点

### 🔹 首次组合的成本模型
- ComposeView/AbstractComposeView 初始化时 `setContent {}` 触发的首次 Composition 流程
- 从 `Composition` 创建 → `Recomposer` 注册 → 首帧 `applyChanges` 的端到端开销
- 首次组合与后续重组（Recomposition）的开销差异：为什么首次最贵
- Composable 函数树的深度与广度对首次组合耗时的线性/指数影响

### 🔹 Class 加载与 Compose Runtime 初始化
- `ComposeRuntime` 类加载链：`androidx.compose.runtime.*` → `SnapshotKt` → `Recomposer` 的加载顺序
- 首次使用 Compose 时的 `AndroidComposeView` 安装成本
- `ComposeView` inflate 与传统 `ViewBinding` inflate 的耗时对比

### 🔹 Baseline Profile 对 Compose 首次组合的优化
- Compose Runtime 函数在 AOT 编译中的覆盖问题
- 为什么 `remember`/`CompositionLocal`/`currentRecomposer` 调用需要 Baseline Profile
- Macrobenchmark 中 Compose 首帧场景的 Profile 收集策略
- Startup Profile vs Baseline Profile：哪个对 Compose 启动更有效

### 🔹 延迟组合与按需 Composition
- `SubcomposeLayout` 对首次组合的拆分效果
- `LazyColumn`/`LazyRow` 的按需组合对冷启动的影响
- 导航图（NavHost）中的目的地延迟组合策略
- `remember` vs `remember(LazyThreadSafetyMode.NONE)` 在启动场景的取舍

### 🔹 Compose 启动链路度量
- `reportDrawComposition` 与 `FrameMetrics` 的关系
- Perfetto 中 Compose 首次组合的 Trace 标记位置
- 从 `Activity.onCreate` 到 Compose 首帧绘制的完整时间线分解
- Compose 首帧 vs View 体系首帧的度量差异

### 🔹 多进程/多窗口下的 Compose 初始化
- 子进程使用 Compose 的重复初始化开销
- `AppCompatActivity` vs `ComponentActivity` 对 Compose 初始化路径的影响

## 扩展

### 🔸 Compose 预编译（Precompilation）方案探索
- `prepareCompose` 等实验性 API 的可行性
- 在后台线程预组合 UI 的策略与限制

### 🔸 Jetpack Compose 与 View 体系混合启动的性能
- `ComposeView` 嵌入 `FrameLayout` 的额外开销
- `ViewTreeLifecycleOwner`/`ViewTreeViewModelStoreOwner` 安装时机的影响

<!-- outline-end -->

> 本节内容待加工。
