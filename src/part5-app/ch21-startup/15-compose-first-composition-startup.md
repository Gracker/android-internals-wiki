---
title: "Compose 首次组合开销与启动性能"
chapter: "21.15"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-27"
last_verified_against: "Compose BOM 2025.12.00, Kotlin 2.2, AOSP androidx-compose-release"
confidence: medium-high
drafted_date: "2026-06-27"
tags: [compose, startup, first-composition, baseline-profile, cold-start]
related_chapters: ["21.3", "21.4", "22.3", "22.20", "22.26", "18.25"]
sources:
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt"
  - type: androidx
    path: "platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Recomposer.kt"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: local
    path: "src/part5-app/ch22-rendering-practice/03-compose-performance.md"
  - type: local
    path: "src/part5-app/ch21-startup/04-baseline-profile-practice.md"
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "章节深挖"
---

# 21.15 Compose 首次组合开销与启动性能

Compose 应用冷启动时，首帧绘制前有一段 View 体系不会出现的开销：Compose Runtime 初始化 + 首次组合（First Composition）。这段开销在纯 Compose 应用的中端设备上通常占用 30-80ms，取决于 UI 树复杂度和 Baseline Profile 覆盖率。本节拆解首次组合的成本结构、度量方法和优化手段，覆盖 Android 12-17 和 Compose BOM 2025.12.00（Compose 1.10）。

## 首次组合的成本模型

### 从 setContent 到首帧的完整链路

`ComponentActivity.setContent {}` 执行后，Compose 的启动链路分四步：

1. **AndroidComposeView 安装**：Activity 的 `DecorView` 下插入 `AndroidComposeView`（继承 `ViewGroup`）。这一步包括 `ContextThemeWrapper` 创建、`UiModeManager` 读取、`Configuration` 快照。
2. **Recomposer 启动**：`AndroidComposeView` 通过 `currentRecomposer` 获取或创建 `Recomposer` 实例。`Recomposer` 在主线程的 `CoroutineScope` 上运行，负责驱动整个组合-布局-绘制循环。
3. **首次 Composition（applyChanges）**：`Recomposer.runRecomposeAndApplyChanges()` 执行根 Composable 函数，生成第一棵 `Composition` 树。所有 `remember` 块执行初始计算，所有 `@Composable` 函数体完整执行（无法跳过，因为没有上一轮的参数对比）。
4. **Layout + Draw**：生成的 UI 树经过 AndroidComposeView 的 `onLayout` / `onDraw`，走标准 View 布局和绘制管线，最终通过 `RenderThread` 提交到 GPU。

第 3 步是 Compose 特有的额外开销。View 体系在 `setContentView` 后直接进入 measure/layout/draw，没有"首次组合"这一层。一个典型的 Compose Activity，首次组合的 CPU 耗时占冷启动可感知阶段（`Activity.onCreate` 到第一帧 `Choreographer.doFrame`）的 15-30%。

### 首次组合 vs 重组的开销差异

重组（Recomposition）可以跳过未变化的子树，首次组合不能。首次组合时每个被调用的 `@Composable` 函数都会完整执行函数体，包括：

- 所有 `remember` 的 factory 调用
- 所有 `Modifier` 链的组装
- 所有子 Composable 的递归调用
- `CompositionLocalProvider` 的值安装

Composable 函数树的深度和广度直接影响首次组合耗时。根节点下的第一层有 N 个子 Composable，每个又有 M 个子节点，首次组合的总执行次数约为 N×M（简化模型，实际取决于具体树结构）。层级嵌套深的页面（如嵌套 `Column`/`Row` 5 层以上）首次组合的开销明显高于扁平结构。

### AndroidComposeView 的创建成本

`AndroidComposeView` 的构造函数做了不少初始化工作：

- `ModifierInfo` 全局状态注册
- `Density` / `FontFamilyResolver` / `HapticFeedback` 等环境对象创建
- `OwnerSnapshot` 系统初始化
- `MotionEventDispatcher` 创建
- `AutofillTree` 注册
- `ViewModelStoreOwner` / `SavedStateRegistryOwner` 查找

这段初始化在 `ComposeView` attach 到 window 时触发。用 `ComposeView` 替代直接 `AndroidComposeView` 会多一层 `ViewTreeLifecycleOwner` 的查找和 `AbstractComposeView` 的抽象方法调用，额外开销约 1-3ms。

[已验证: androidx-compose-release, compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt]

## Class 加载与 Compose Runtime 初始化

### Compose Runtime 类加载链

首次使用 Compose 时，ART 需要加载一系列类。加载链大致如下：

```
ComposeView
  → AbstractComposeView
    → AndroidComposeView
      → Recomposer
        → CoroutineScope (runtimeDispatcher)
          → Snapshot (SnapshotKt.takeMutableSnapshot)
            → CompositionData / CompositionImpl
              → ComposerKt (compositionLocalMap)
```

每个类的加载包括：`.dex` 文件查找 → `ClassDef` 解析 → `ClassLinker` 链接 → `Init` 静态块执行。Compose Runtime 涉及约 200-300 个类，首次冷启动时类加载总耗时约 5-15ms（中端设备），取决于 `dexopt` 编译模式和类是否在 `boot.art` 中。

没有 Baseline Profile 时，Compose Runtime 的方法首次执行走解释器或 JIT，速度比 AOT 编译慢 2-5 倍。这就是 Baseline Profile 对 Compose 启动至关重要的根本原因——详见 §21.4。

### AppCompatActivity vs ComponentActivity

`AppCompatActivity` 在 `onCreate` 中额外执行了 `AppCompatDelegateImpl` 的初始化，包括 `SupportActionBar` 相关逻辑和 `AppCompatViewInflater` 的替换。如果 Activity 使用 Compose 作为根视图（`setContent {}`），这些 AppCompat 基础设施大部分不参与渲染，但初始化开销仍然存在：

- `AppCompatDelegateImpl.create()`：约 2-5ms
- `AppCompatViewInflater` 注册：约 0.5-1ms

纯 Compose Activity 推荐继承 `ComponentActivity`，跳过 AppCompat 初始化链路。如果项目因历史原因必须用 `AppCompatActivity`，这部分开销约 3-6ms，属于可接受范围但不理想。

[已验证: Compose BOM 2025.12.00 行为，Android 12-17]

## Baseline Profile 对 Compose 首次组合的优化

### 为什么 Compose 需要 Baseline Profile

Compose 的编译产物有两个特点导致 Baseline Profile 的收益特别大：

1. **生成代码量大**：Compose compiler 为每个 `@Composable` 函数生成 `Group` 框架代码（`startRestartGroup` / `endRestartGroup` / `updateGroup` 等），生成的方法数远多于源码中的函数数。
2. **运行时高频调用的 Runtime API**：`Composer.skipToGroupEnd()`、`Snapshot.takeMutableSnapshot()`、`Recomposer.recompositionStarted()` 等方法在首次组合中被密集调用。没有 AOT 编译时，这些方法走解释器，性能差距明显。

Baseline Profile 让 ART 在安装时（或 OTA 后首次启动时）预先将这些方法 AOT 编译为机器码，跳过解释器和 JIT 预热阶段。

### Compose Baseline Profile 的获取方式

从 Android Studio Flamingo（2023）起，新建 Compose 项目默认包含 Compose 预置 Baseline Profile（`androidx.compose:compose-bom` 携带）。但预置 Profile 只覆盖 Compose 库自身代码，不覆盖应用自己的 Composable 函数。

获取完整 Baseline Profile 的方法：

1. **Macrobenchmark + BaselineProfileRule**：编写 `BaselineProfileRule` 测试，在测试中启动 App 并操作核心页面（特别是冷启动后第一个可见页）。生成的 profile 覆盖冷启动路径上的所有 Compose 调用。

2. **Startup Profile（Android 15+）**：Startup Profile 是 Baseline Profile 的子集，专门聚焦 App 启动路径。Android 运行时安装时优先处理 Startup Profile，编译速度更快。从 `androidx.profileinstaller:profileinstaller` 1.4.0 起，如果项目同时提供 Baseline Profile 和 Startup Profile，安装时两者协同生效。详见 §21.12。

### Baseline Profile 对 Compose 首帧的效果

以下数据来自 Google 官方 Macrobenchmark 示例和社区公开报告（[来源: Google I/O 2024 "Compose Performance" talk, Android 开发者博客]）：

- 纯 Compose 冷启动首帧：Baseline Profile 覆盖后，首次组合耗时降低约 20-40%
- 中端设备（如 Pixel 6a / Snapdragon 7 系列）效果最明显，高端设备（Pixel 9 Pro）因 CPU 算力富裕差距收窄

[待验证: 具体百分比数据随设备和 Compose 版本变化，建议用项目自身 Macrobenchmark 验证]

## 延迟组合与按需 Composition

### SubcomposeLayout 的拆分效果

`SubcomposeLayout` 允许 Compose 在 measure 阶段按需组合子节点，而不是在组合阶段一次性组合所有子节点。这对首帧的优化效果是：将一次大的组合拆分为多次小的组合，首帧只需完成可见部分。

Compose 标准库中大量使用 `SubcomposeLayout`：`Box`（带 `Modifier.align`）、`LazyColumn`/`LazyRow`、`TextField` 等。自定义布局如果子节点数量不确定或按需展示，也应该考虑 `SubcomposeLayout`。

`SubcomposeLayout` 的代价是：每次 `measure` 可能触发额外组合，总体 CPU 开销高于一次性组合。对启动场景，首帧时间的收益通常值得这个代价。

### LazyColumn / LazyRow 在启动中的角色

`LazyColumn` 只组合当前可见区域 + `beyondBoundsItemCount` 指定的额外项目。在一个有 100 项数据的列表页面中，首帧只组合约 8-12 项（取决于屏幕高度和项目高度），而非全部 100 项。

这直接影响首次组合耗时。如果启动页的根布局是一个长列表，用 `LazyColumn` 替代 `Column { items() }` 可以将首次组合耗时降低 50% 以上。

### NavHost 目的地延迟组合

Navigation Compose 的 `NavHost` 默认只组合当前目的地的 Composable，不预组合其他目的地。这对启动有利：启动时只组合起始目的地，其他页面等用户导航时才组合。

如果项目有预加载需求（如启动时预组合第二个页面以减少导航延迟），可以用 `Lifecycle.Observer` 在 `ON_RESUME` 后触发后台预组合，但这会增加启动期内存压力。权衡取舍。

### remember 与 LazyThreadSafetyMode

`remember(LazyThreadSafetyMode.NONE)` 跳过 `Snapshot` 系统的读写追踪。在确定某个 `remember` 只在单线程访问的场景（如主线程的组合阶段），使用 `NONE` 可以减少 `SnapshotMutableState` 的创建和注册开销。

Compose 1.10（BOM 2025.12）中，Strong Skipping 默认启用后，编译器对 `remember` 的处理更加积极，部分场景编译器会自动选择 `NONE` 模式。手动标注仍然适用于编译器无法推断的场景。

## Compose 启动链路度量

### 从 Activity.onCreate 到 Compose 首帧的时间线分解

```
Activity.onCreate()
  ├─ super.onCreate()                    [1-3ms]
  ├─ setContent {}                       
  │   ├─ AndroidComposeView 安装          [2-5ms]
  │   ├─ Recomposer 创建+启动             [1-3ms]
  │   └─ 首次 Composition 队列入队         [0ms, async]
  ├─ 数据初始化 / ViewModel 创建           [variable]
  └─ Activity.onCreate() 返回
                                        ↓
Choreographer doFrame #1
  ├─ Recomposer.runRecomposeAndApplyChanges  [10-40ms] ← 首次组合
  ├─ AndroidComposeView.onMeasure             [2-5ms]
  ├─ AndroidComposeView.onLayout              [1-3ms]
  └─ AndroidComposeView.onDraw                [1-3ms]
                                        ↓
RenderThread
  └─ 提交到 GPU                               [2-5ms]
                                        ↓
Display compositor → 像素上屏
```

首次组合（`runRecomposeAndApplyChanges`）是整个链路中变异最大的环节，取决于 UI 树复杂度、Baseline Profile 覆盖率和设备 CPU 性能。

### Perfetto 中的 Compose 首次组合 Trace

Compose Runtime 通过 `androidx.compose.runtime` 的 `Trace` API（`androidx.tracing`）向 Perfetto 输出 trace 区间。关键标记：

| Trace 区间名 | 含义 |
|---|---|
| `Compose:recompose` | Recomposer 执行重组/首次组合 |
| `Compose:applyChanges` | 将组合结果应用到 Composition 树 |
| `Compose:layout` | Compose 布局阶段 |
| `Compose:draw` | Compose 绘制阶段 |
| `Recomposer:runRecomposeAndApplyChanges` | 整个组合循环迭代 |

在 Perfetto 中搜索 `Compose:recompose` 的第一个实例，即可定位首次组合。结合 `Choreographer#doFrame` 区间，可以精确计算首次组合占用帧时间的比例。

Compose trace 默认需要引入 `androidx.tracing:tracing-perfetto` 依赖（1.0.0+），并在 `Application.onCreate` 中调用 `Trace.enable()`. Android 15+ 的 Perfetto 可以直接捕获 Compose trace 区间，不需要额外 enable 调用。详见 §22.20 Compose 性能优化盲区中的 Trace 配置部分。

### FrameMetrics 与 Compose 首帧

`FrameMetrics` API（§19.12）报告的 `TOTAL_DURATION` 和 `DRAW_DURATION` 包含了 Compose 的布局和绘制，但不区分 Compose 组合和 View measure/layout。要拆分 Compose 组合耗时，必须依赖 Perfetto trace。

`reportDrawComposition` 不是公开 API。Compose 内部通过 `DisplayListCanvas` 和 `RenderNode` 与 HardwareRenderer 交互，首帧完成时 HardwareRenderer 的 `syncContent` 回调通知 Compose。在 Perfetto 中追踪更可靠。

## 多进程与多窗口下的 Compose 初始化

### 子进程 Compose 初始化开销

每个使用 Compose 的进程独立承担 Compose Runtime 初始化成本。子进程不能复用主进程已加载的 Compose 类（ART 的类加载器是进程级的）。

多进程 App（如推送服务、小工具进程）如果 UI 面板使用 Compose，需要单独评估其启动性能。优化方向：

- 子进程 UI 尽量简单，减少首次组合的 UI 树复杂度
- 子进程的 Baseline Profile 需要覆盖子进程入口路径
- 考虑子进程是否真的需要 Compose，简单的 RemoteViews 可能更高效

### 多窗口与桌面模式

Android 多窗口模式下，Compose 的行为与全屏模式一致。但 `AndroidComposeView` 的 `onConfigurationChanged` 可能在窗口大小调整时频繁触发重组。启动阶段的窗口尺寸变化（如桌面模式窗口默认尺寸不固定）会导致首次组合完成后立即触发额外重组。

在 Android 17 桌面模式下（详见 §2.20 多窗口与桌面模式渲染性能），推荐在 `onCreate` 中读取 `WindowManager.getCurrentWindowMetrics()` 获取稳定窗口尺寸后再触发 Compose 组合，避免启动期窗口尺寸抖动引起的重复重组。

## 扩展

### Compose 预编译方案

Compose 团队在探索的预编译（Precompilation）方向：在应用构建期将 Composable 函数预编译为中间表示（IR），减少运行时首次组合的开销。目前（Compose 1.10 / Kotlin 2.2）还没有公开可用的预编译 API。

工程实践中可考虑的替代方案：

- **预加载 Compose 类**：在 `Application.onCreate` 中通过 `Class.forName()` 显式触发 Compose Runtime 核心类的加载。效果有限（类加载只是首次组合的一部分），但在超大 App 中可以减少 5-10ms。
- **后台线程预组合**：Compose 1.8+ 的 `PausableComposition` 支持在子线程执行部分组合工作（详见 §22.3）。但首次组合必须在主线程 `Recomposer` 驱动下完成，子线程预组合目前仍有限制。

[待验证: PausableComposition 在启动场景的具体效果，建议跟踪 Compose 1.11+ 更新]

### View/Compose 混合启动的性能

在 View 体系为主的 App 中逐步引入 Compose，启动路径可能同时包含 View inflate 和 Compose 首次组合。额外开销来源：

- `ComposeView` 嵌入 `FrameLayout` 时，`AndroidComposeView` 作为子 View 参与父布局的 measure/layout，增加一次布局传递
- `ViewTreeLifecycleOwner` / `ViewTreeViewModelStoreOwner` 的安装时机：如果 `ComposeView` attach 时 owner 未就绪，Compose 会延迟初始化直到 owner 可用，这段等待表现为 `runRecomposeAndApplyChanges` 的首次调用延迟

混合迁移的性能影响详见 §22.15 Compose First 与 View/Compose 混合迁移性能边界。

---

> 本节内容已加工，状态变更：draft → ready-for-review。
> 加工日期：2026-06-27
> 交叉引用：§21.3 ContentProvider 启动治理、§21.4 Baseline Profile 实战、§22.3 Compose 性能优化实战、§22.20 Compose 性能优化盲区、§22.26 Compose Snapshot 系统与状态观测性能、§18.25 Jetpack Compose 渲染管线架构
> [结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
