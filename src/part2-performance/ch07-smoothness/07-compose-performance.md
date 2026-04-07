---
title: "Jetpack Compose 性能优化"
chapter: "7.7"
status: ready-to-publish
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-01"
last_verified_against: "Android 16 Developer Preview"
confidence: medium
reviewed_date: "2026-04-07"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-04"
polish_by: "task2b-polish"
review_type: post-polish-quality-gate
review_round: 2
sources:
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_沉思录_如何优化_Compose_的性能_通过_底层原理_寻找答案.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_提升Jetpack_Compose_性能.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_Compose_渲染性能到底怎么样.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_原创_写给初学者的Jetpack_Compose教程_用derivedStateOf提升性能.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-08_wechat_Compose_与原生启动性能对比.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_掌握_Android_Compose_从基础到性能优化全面指南.md"
  - type: official
    path: "developer.android.com/develop/ui/compose/performance"
tags: [compose, jank, recomposition, stability, lazy-column, layout-inspector, compose-compiler, animation, compose-interop]
related_chapters: ["7.1", "7.2", "7.3", "2.4", "2.5", "2.11"]
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2a"
section: "7.7"
---

# Jetpack Compose 性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Compose 渲染模型：Composition → Layout → Drawing 三阶段与传统 View 体系的对比
- 🔹 Recomposition 的触发条件与最小化策略：stable 标记、remember、derivedStateOf
- 🔹 Compose 中的性能陷阱：不稳定参数导致的过度重组、LazyColumn 的 key 策略
- 🔹 Compose 性能检测：Layout Inspector Recomposition 计数、Compose Compiler Metrics
- 🔹 Compose 与 View 混合布局的性能考量（ComposeView / AndroidView 开销）

### 扩展（可选深入）

- 🔸 Compose Multiplatform 的性能差异
- 🔸 Compose 动画性能：animate*AsState vs Animatable vs transition

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要关注 Compose 的性能

如果我们在 Perfetto 中看到一个 Compose 应用的主线程出现了异常的长帧——比如一帧花了 30ms 而预期的 16.6ms——我们打开那一帧的 slice，看到的不是传统 View 体系里熟悉的 measure/layout/draw，而是一堆以 "CM"（Compose Manager）开头的标记。这意味着什么？这一帧的开销来自 Compose 的重组（Recomposition），而不是传统的布局计算。

这就是我们需要理解 Compose 性能模型的原因。Compose 不是"换了种写 UI 的语法"那么简单，它的渲染管线、状态管理、重组机制都和传统 View 体系有着根本性的差异。如果我们用分析传统 View 那套思路来分析 Compose，很容易走偏——比如看到掉帧就怀疑是布局层级太深，但实际原因可能是某个参数不稳定导致整个页面被无意义地重组了一遍。

了解 Compose 的性能模型之后，我们能做之前做不到的事：在 Perfetto 中准确识别 Compose 相关的性能瓶颈，通过 Layout Inspector 定位过度重组的组件，利用 Compose Compiler Metrics 在编译阶段就发现潜在的性能问题。

## Compose 的渲染模型：Composition → Layout → Drawing

[已验证: 官方文档, developer.android.com/develop/ui/compose/mental-model]

传统 View 体系的渲染过程，我们在前面章节已经讲过了：measure → layout → draw，由 Choreographer 驱动，每个 VSync 周期最多执行一轮。Compose 的渲染过程本质上也是这三个阶段，但在前面多了一个"Composition"阶段。

**Composition（组合）** 是 Compose 独有的阶段，也是它和传统 View 体系最大的区别。在这个阶段，Compose 运行时会执行所有的 @Composable 函数，生成一棵"虚拟的"UI 树——注意，这棵树不是 View 对象的树，而是一个描述 UI 结构的数据结构（SlotTable）。每个 @Composable 函数的执行，相当于在这棵树上挂一个节点。

Composition 之后就是 **Layout** 阶段。这个阶段和传统 View 体系的 layout 非常类似：Compose 会遍历 UI 树，测量每个节点的尺寸，确定它们在屏幕上的位置。具体来说，Compose 的 Layout 阶段会调用每个节点的 measure 方法，完成尺寸协商。

最后是 **Drawing** 阶段。Compose 的 UI 元素最终会通过 Android 的 Canvas 进行绘制。这意味着虽然 Jetpack Compose 是全新的 UI 框架，但它的底层并没有脱离 Android 的范畴——最终还是要把像素画到 Canvas 上。

关键的区别在于：传统 View 体系只在 UI 结构发生变化时才重新创建 View 对象（比如 addView/removeView），而 **Compose 的 Composition 阶段在每次状态变化时都可能重新执行**。这就是所谓的"Recomposition"（重组）。

[图：Compose 渲染管线三阶段示意——Composition 生成 SlotTable → Layout 测量定位 → Drawing 绘制到 Canvas，与传统 View 体系 measure → layout → draw 对比]

### 重组到底是什么

[已验证: 官方文档, developer.android.com/develop/ui/compose/mental-model#recomposition]
[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_沉思录_如何优化_Compose_的性能_通过_底层原理_寻找答案.md]

"重组"这个词听起来像是一个复杂的机制，但它的本质非常简单：**重新调用一次 @Composable 函数**。

Compose 编译器插件在编译时会改造每个 @Composable 函数。以一个简单的 Greeting 组件为例：

```kotlin
@Composable
fun Greeting(msg: String) {
    Text(text = "Hello $msg!")
}
```

编译后，这个函数的签名会多出 `Composer` 和 `$changed` 两个参数，函数体里会被插入 `startRestartGroup` 和 `endRestartGroup` 调用。`endRestartGroup` 会返回一个 `ScopeUpdateScope` 对象，开发者可以往上面注册一个回调——当状态变化导致这个函数需要重组时，Compose 运行时就通过这个回调递归调用函数自身。

整个机制基于 Compose 的**状态快照系统（Snapshot）**。当我们通过 `mutableStateOf` 创建一个 State 变量时，它的 getter 和 setter 实际上是自定义的：setter 会通知快照系统"这个值变了"，快照系统再找到订阅了这个值的 ScopeUpdateScope，触发重组。

所以当我们说"某个 Composable 发生了重组"，准确的意思是：Compose 运行时重新调用了一次这个 @Composable 函数。重组的范围取决于状态读取发生在哪个 Scope——**状态读取发生在哪个 Scope，状态更新时哪个 Scope 就发生重组**。

这个原则非常重要，因为它是所有 Compose 性能优化策略的理论基础。后面我们讲到的 derivedStateOf、延迟读取、Lambda 包装等优化手段，本质上都是通过改变状态读取的 Scope 来缩小重组范围。

### 与传统 View 体系的性能对比

[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_Compose_渲染性能到底怎么样.md]

社区中有开发者做过直接对比：同一个列表页面，分别用 LazyColumn 和 RecyclerView 实现，然后在不同 Android 版本的设备上测量快速滑动时的 FPS。

结果是这样的：在高端设备（Android 11+）上，两者都能稳定跑满 60fps。但在中低端设备上差距明显——Android 7.1 设备上 LazyColumn 只有约 43fps，而 RecyclerView 仍然能稳定在 60fps。不过有意思的是，同样的测试者在粒子动画场景中对比了 Compose 和 View 的 Canvas 绘制性能，两者几乎完全一致。

这说明什么？**Compose 本身的渲染性能（Layout + Drawing）已经和传统 View 持平，差距主要在 Composition 阶段——也就是重组的开销**。如果我们的 Compose 页面掉帧，大概率不是"Compose 画得慢"，而是"Compose 重组了不该重组的东西"。

这也解释了为什么 Compose 性能优化的核心策略就是：**减少不必要的重组、缩小重组的范围**。

[待补充：Compose 和 View 在 Perfetto 中的帧耗时对比截图]

## Recomposition 的触发条件与最小化策略

理解了重组的本质之后，我们来看具体的触发条件和优化策略。这部分是 Compose 性能优化的核心。

### stable 标记：让 Compose 知道"参数没变"

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance#stability]

Compose 编译器在编译时会推断每个类型的"稳定性"（Stability）。一个类型如果满足以下条件，就被认为是"稳定"的：

- 所有公共属性在创建后不会变化（immutable），或者变化时会通知 Compose
- 所有公共属性的类型本身也是稳定的

稳定的类型包括：基本类型（Int、String、Boolean）、标记了 @Stable 或 @Immutable 的类、所有属性都是 val 且类型稳定的 data class。

不稳定的类型最常见的是：`List<T>`（Kotlin 的 List 是接口，编译器无法保证实现类是否可变）、包含 var 属性的类、接口类型。

为什么稳定性很重要？因为 Compose 的跳过机制依赖它：**只有当一个 Composable 的所有参数都是稳定类型时，Compose 才能在参数没有实际变化时跳过这个 Composable 的重组**。如果参数类型不稳定，Compose 只能保守地假设"可能变了"，每次父组件重组时都跟着重组。

有两种方式可以声明稳定性：

**@Immutable**：标记完全不可变的类。一旦创建，内部任何内容都不会改变。这是最严格的承诺：

```kotlin
@Immutable
data class ProductListState(
    val products: List<Product>,
    val isLoading: Boolean
)
```

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_提升Jetpack_Compose_性能.md]

**@Stable**：标记"可变但会通知"的类。它承诺：当属性值变化时，Compose 运行时一定会收到通知。适用于 State holder 类：

```kotlin
@Stable
class ProductListState(
    val products: List<Product>,
    val isLoading: Boolean
)
```

需要特别注意的是：`@Immutable` 和 `@Stable` 是**契约**，不是提示。如果我们标记了 @Immutable 但类实际上有可变状态，Compose 可能会跳过必要的重组，导致 UI 不更新。这是一种更难发现的 bug。

### remember：跨重组保持数据

[已验证: 官方文档, developer.android.com/develop/ui/compose/composition#remember]

`remember` 的作用是在 Composable 函数的多次重组中保持数据。每次重组时，普通变量会被重新初始化，而 `remember` 包裹的值会保留上一次的结果。

最常见的用法是配合 `mutableStateOf` 创建响应式状态：

```kotlin
var clickCount by remember { mutableStateOf(0) }
```

但 `remember` 也可以用来缓存计算结果，避免在每次重组时重复计算：

```kotlin
val sortedItems = remember(items) { items.sortedBy { it.priority } }
```

注意这里的 `items` 是 `remember` 的 key——只有当 items 变化时才会重新排序。如果不指定 key，排序结果会在整个 Composable 的生命周期内被缓存，即使 items 已经变了也不会更新。

### derivedStateOf：只在结果真正变化时才触发重组

[已验证: 官方文档, developer.android.com/develop/ui/compose/side-effects#derivedstateof]
[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_原创_写给初学者的Jetpack_Compose教程_用derivedStateOf提升性能.md]

`derivedStateOf` 是减少不必要重组的利器。它创建一个"派生状态"——只有当派生表达式的**结果**发生变化时，才会通知 Compose 触发重组。

一个经典的场景是：根据列表滚动位置控制 FAB 按钮的显隐。

```kotlin
// 问题代码：每次 firstVisibleItemIndex 变化（每滑过一个 item）都触发重组
val shouldShowButton = state.firstVisibleItemIndex == 0

// 优化代码：只在 shouldShowButton 的值切换（true↔false）时才触发重组
val shouldShowButton by remember {
    derivedStateOf { state.firstVisibleItemIndex == 0 }
}
```

前者的状态读取发生在 MainLayout 的 Scope 中，所以每滑过一个 item，整个 MainLayout 都会重组。后者把读取包装在 `derivedStateOf` 里，只有当 `firstVisibleItemIndex == 0` 的布尔结果发生变化时才会通知——也就是从 0 变成 1 和从 1 变成 0 的那两次。其余的滑动完全不会触发重组。

### 延迟状态读取：缩小重组范围

[来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_沉思录_如何优化_Compose_的性能_通过_底层原理_寻找答案.md]

这是 Android 官方推荐的另一项关键优化。核心思想是：**尽可能把状态的读取推迟到使用它的地方**，利用 Kotlin Lambda 的惰性求值（Laziness）来避免在 Composition 阶段产生不必要的订阅关系。

考虑一个滚动偏移影响标题位置的场景：

```kotlin
// 问题代码：在 Composition 阶段就读取了 scroll.value
@Composable
private fun Title(snack: Snack, scroll: Int) {
    val offset = with(LocalDensity.current) { scroll.toDp() }
    Column(modifier = Modifier.offset(y = offset)) {
        // ...
    }
}
```

当 scroll 值在每次滑动事件中变化时，Title 和它的父级 SnackDetail 都会重组——因为状态读取发生在它们的 Scope 里。

优化方式是把参数改为 Lambda：

```kotlin
// 优化代码：用 Lambda 延迟读取
@Composable
private fun Title(snack: Snack, scrollProvider: () -> Int) {
    val offset = with(LocalDensity.current) { scrollProvider().toDp() }
    Column(modifier = Modifier.offset(y = offset)) {
        // ...
    }
}

// 调用方：
Title(snack) { scroll.value }  // scroll.value 被包装在 Lambda 中
```

这样一来，`scroll.value` 的读取不在 Composition 阶段发生，而是延迟到了 Layout 或 Draw 阶段。当 scroll 变化时，Compose 可以跳过重组，直接进入 Layout + Draw。这在频繁变化的场景（如滑动偏移、动画进度）中性能提升非常显著。

## Compose 中的性能陷阱

了解优化策略之后，我们来看实际项目中最容易踩的坑。

### 陷阱一：不稳定参数导致整个页面被拖着重组

这是 Compose 性能问题中最常见的一类。当我们把一个包含 var 属性的类，或者一个 `List<T>` 传给 Composable 时，编译器无法确定这个参数是否稳定，只好在每次父组件重组时都重新执行这个 Composable。

一个典型的案例：我们的 ViewModel 暴露了一个 `StateFlow<List<Item>>`，在 Compose 中通过 `collectAsState()` 收集。问题在于 `List<Item>` 是不稳定的——即使列表内容完全没变，Compose 也无法确定这一点，每次都会重组所有消费这个列表的 Composable。

解决方案：

1. 用 `kotlinx.collections.immutable` 的不可变集合替代普通 List，让编译器能推断稳定性
2. 用 `@Immutable` 注解标记我们的数据类（前提是我们真的保证它不可变）
3. 在 Compose Compiler 1.5.5+ 中，可以通过 Stability Configuration File 声明外部类的稳定性

[自动发现: Kotlin 2.0.20 引入的 Strong Skipping 模式可以在一定程度上缓解这个问题——即使参数类型不稳定，只要对象实例相同（引用相等），也可以跳过重组。来源: Android Developers Blog]

### 陷阱二：LazyColumn 缺少 key 导致整列表重组

[来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_提升Jetpack_Compose_性能.md]

LazyColumn 默认用 item 在列表中的位置（index）作为标识。这意味着如果我们在列表头部插入一个新 item，Compose 会认为所有 item 都变了（因为它们的 index 都变了），导致整列表重组。

解决方案是给每个 item 提供一个稳定的 key：

```kotlin
LazyColumn {
    items(
        items = products,
        key = { it.id }  // 用稳定的业务 ID 而非位置
    ) { product ->
        ProductCard(product)
    }
}
```

有了 key 之后，Compose 就能识别出哪些 item 是新增的、哪些是移动的、哪些没变，只重组真正变化的 item。

### 陷阱三：在 Composable 函数中做计算

如果一个 Composable 函数里有排序、过滤等计算操作，而且这些操作的结果在多次重组间不会变化（或只在特定参数变化时才需要重新计算），那就应该用 `remember` 包裹：

```kotlin
// 错误：每次重组都排序
@Composable
fun ProductList(products: List<Product>) {
    val sorted = products.sortedBy { it.priority }  // 每次重组都执行！
    LazyColumn {
        items(sorted) { ... }
    }
}

// 正确：只在 products 变化时排序
@Composable
fun ProductList(products: List<Product>) {
    val sorted = remember(products) { products.sortedBy { it.priority } }
    LazyColumn {
        items(sorted) { ... }
    }
}
```

## Compose 性能检测工具

优化之前，先要能发现问题。Compose 提供了几个层次的检测工具。

### Layout Inspector：实时查看重组次数

[已验证: 官方文档, developer.android.com/studio/debug/layout-inspector/compose]

Android Studio 的 Layout Inspector 可以实时显示每个 Composable 的重组次数。使用方式：

1. 在 Android Studio 中打开 Layout Inspector（View → Tool Windows → Layout Inspector）
2. 连接正在运行的 debug 应用（需要 API 29+，Compose 1.2.0+）
3. 在 Component Tree 中找到"Show Recomposition Counts"选项并启用

启用后，每个 Composable 旁边会显示两个数字：**recomposition count**（实际重组的次数）和 **skip count**（被跳过的次数）。如果某个 Composable 的重组次数异常高——比如我们在滑动列表时，一个不相关的头部组件被重组了几十次——那就是需要优化的信号。

Layout Inspector 还会用颜色渐变来可视化重组热度：颜色越深表示重组越频繁。双击一个 Composable 可以直接跳转到源码。

### Compose Compiler Metrics：在编译阶段发现不稳定类型

[已验证: 官方文档, developer.android.com/develop/ui/compose/performance#compose-compiler-metrics]

这是一个编译时工具，不需要运行应用就能分析 Compose 的稳定性。配置方式：

```gradle
// build.gradle (module level)
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

构建后会在 `build/compose_compiler/` 目录下生成几个关键文件：

- **module.json**：模块级汇总，包括 skippable Composable 占比、restartable Composable 占比等。如果 skippable 比例很低，说明很多 Composable 因为参数不稳定无法被跳过。
- **composables.txt**：每个 Composable 的详细信息——是否 restartable、是否 skippable、每个参数的稳定性。这个文件是定位问题的主力。
- **classes.txt**：每个类的稳定性推断结果。我们可以看到哪些类被判定为不稳定，以及原因。

社区工具 `compose-report-to-html` 可以把这些文本报告转换成更直观的 HTML 页面，方便团队分享。

建议在 CI 流水线中集成 Compiler Metrics 检查，设置 skippable 比例的阈值（比如低于 80% 就告警），在代码合并前就拦截潜在的性能问题。

## Compose 与 View 混合布局的性能考量

[已验证: 官方文档, developer.android.com/develop/ui/compose/migrate/interoperability-apis]

很少有项目能一次性把所有页面都迁移到 Compose。更常见的情况是项目中同时存在传统 View 和 Compose，通过互操作 API 桥接。但"桥"本身是有开销的。

### ComposeView：在传统布局中嵌入 Compose

`ComposeView` 是一个传统 View，我们可以在 XML 或代码中创建它，然后通过 `setContent` 设置 Compose 内容：

```xml
<androidx.compose.ui.platform.ComposeView
    android:id="@+id/compose_view"
    android:layout_width="match_parent"
    android:layout_height="wrap_content" />
```

它的性能开销主要在首次创建时——需要初始化 Compose 运行时。之后的重组开销和普通 Compose 页面没有区别。但需要注意在 RecyclerView 中使用 `ComposeView` 的情况：每个 item 都会创建一个独立的 Compose 容器，如果 item 复杂或列表快速滑动，可能导致帧延迟。在这种情况下可以考虑对 ComposeView 进行回收复用。

[待验证: Compose 1.10 中 ReuseComposeView API 的稳定性]

### AndroidView：在 Compose 中嵌入传统 View

`AndroidView` 是反向的桥接——在 Compose 布局中嵌入一个传统 View。最常见的场景是使用 WebView、MapView 等没有 Compose 替代品的组件：

```kotlin
@Composable
fun WebViewScreen(url: String) {
    AndroidView(
        factory = { context -> WebView(context).apply { settings.javaScriptEnabled = true } },
        update = { webView -> webView.loadUrl(url) }
    )
}
```

[来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_Jetpack_Compose_与_WebView.md]

性能注意事项：`factory` 只在首次创建 View 时调用，`update` 在每次重组时都会调用。如果把初始化逻辑错误地放在了 `update` 里，就会导致每次重组都重新执行——比如每次都重新创建 WebViewClient，这是完全没有必要的开销。

### 混合布局的通用建议

- **减少边界跨越**：每次从 Compose 切换到 View 或者反过来，都有上下文切换的开销。尽量把 UI 元素集中在同一种体系中，而不是大量穿插使用。
- **注意 View 的生命周期**：传统 View 有自己的生命周期（attach/detach），而 Compose 组件的生命周期由 Compose 管理。在混合布局中，要确保两者的生命周期同步——比如在 Compose 的 `DisposableEffect` 中清理 View 的监听器。
- **性能测试要覆盖混合场景**：纯 Compose 页面和纯 View 页面的性能我们可能都测过了，但混合页面的性能往往是意想不到的瓶颈。在 Perfetto 中，混合布局的帧延迟通常表现为 RenderThread 和主线程之间的额外同步等待。特别是在低端设备上，Compose 和 View 之间的交互可能引入额外的帧延迟。

## Compose 动画性能

[来源: obsidian/Personal-Knowlodge/source/2026-03-05_wechat_Android_鸿蒙_AI_技术刊_第14期_Compose动画深度解析_KMP多端实践落地_Android_16适配指.md]

前几节讨论了 Compose 的重组机制和常见的性能陷阱，这些优化手段已经能覆盖大部分场景。但还有一个特殊的性能敏感区域：动画。动画的特点是状态变化极为频繁（每秒 60 甚至 120 次），如果每一帧都走完整的 Composition → Layout → Draw 流程，开销会迅速累积。Compose 提供了三种层次的动画 API，性能特征各不相同：

**`animate*AsState`**（如 `animateColorAsState`、`animateDpAsState`）：最简单的声明式动画 API。它内部通过 State 变化驱动重组，意味着每一帧动画都会触发重组。对于简单的属性变化（颜色、透明度），这个开销通常可以接受；但如果动画作用在复杂的 Composable 上，重组开销可能就不划算了。

**`Animatable`**：更底层的 API，可以在 Coroutine 中手动驱动动画。它的优势在于可以在不触发重组的情况下直接修改绘制属性——比如通过 `Modifier.drawBehind` 在 Draw 阶段直接读取 `Animatable` 的当前值，从而完全跳过 Composition 和 Layout 阶段。**这是 Android 官方推荐的高性能动画方式。**

**`updateTransition`**：用于管理多个属性的联动动画。和 `animate*AsState` 一样，它也通过 State 变化驱动重组，但可以把多个动画的状态集中管理，避免创建多个独立的 State。

从性能角度，我们推荐的策略是：

**优先使用 Draw 阶段动画。** 如果动画只影响绘制属性（颜色、透明度、位移），用 `Animatable` + `Modifier.graphicsLayer{}` 或 `drawBehind`，跳过 Composition 和 Layout。这种方式的开销最小，因为完全不涉及重组。

**布局动画注意缩小重组范围。** 如果动画涉及布局变化（尺寸、位置），只能用 `animate*AsState` 或 `updateTransition`，此时要确保重组范围尽可能小——把动画状态的作用域限制在最小的 Composable 内。

**避免大范围动画重组。** 不要在动画的每一帧都触发整个页面的重组，这在 Perfetto 中表现为连续的长帧，帧耗时随动画进行不收敛。

[待补充：Compose 动画在 Perfetto 中的帧耗时对比——重组驱动动画 vs Draw 阶段动画的实际帧时间差异]

## 与其他章节的关系

我们在本章讨论的 Compose 性能问题，与本书其他章节有密切的关联。

从卡顿的定义来看（7.1），Compose 的卡顿在本质上仍然是"某帧耗时超限"，只是卡顿的来源从传统的 measure/layout/draw 变成了 Composition/Recomposition。从分析方法论来看（7.3），通用的分析框架同样适用——先定位到掉帧的时间段，再分析是什么导致了长帧，只是在 Compose 场景下需要额外检查重组次数。

在底层渲染链路上，Compose 的渲染同样由 Choreographer 驱动（2.4），VSync → doFrame → Composition/Layout/Draw 的链路和传统 View 一致。Composition 和 Layout 阶段在主线程执行，Draw 阶段可能涉及 RenderThread（2.5）。值得一提的是，Jetpack Compose 与 Flutter（2.11）的渲染模型有相似的思路——都采用了组合式的 UI 树和差异化的更新策略，但两者的运行时实现完全不同。

## 常见问题与误区

**误区一："Compose 比 View 慢，所以不应该用 Compose"**

实际情况更微妙。Compose 的 Canvas 绘制性能与传统 View 几乎一致，差距主要在 LazyColumn 的快速滑动场景。对于大多数应用，这个差距在实际使用中并不显著。而且随着 Compose 版本迭代（特别是 1.5+ 的 Strong Skipping 和 1.9/1.10 的 API 优化），性能在持续改善。

**误区二："给所有类加 @Stable 就能解决性能问题"**

`@Stable` 是一个契约，不是魔法。如果我们的类实际上不满足稳定性的要求（比如内部有不受 State 管理的可变状态），加注解不仅不能提升性能，还会导致 UI 不更新的 bug。正确做法是先用 Compiler Metrics 找到真正不稳定的类，然后根据实际情况选择修复方式。

**误区三："Compose 的 remember 就是缓存，什么都能往里塞"**

`remember` 确实有缓存的效果，但它的语义是"跨重组保持状态"，不是通用缓存。`remember` 不关心内存压力，不会被自动回收。如果我们用它缓存大量数据，可能导致内存问题。对于需要响应配置变更的场景，应该考虑 `rememberSaveable`。

**误区四："Compose 就不需要关心过度绘制了"**

过度绘制（Overdraw）的检测方式在 Compose 中完全适用。虽然 Compose 在理论上可以更精确地控制重绘区域，但如果我们在 Compose 中堆叠了多层半透明组件，过度绘制的问题和传统 View 一样存在。可以用"Show GPU Overdraw"来检测。

## 参考资料

- [Jetpack Compose Performance | Android Developers](https://developer.android.com/develop/ui/compose/performance) [已验证: 官方文档]
- [Compose Mental Model | Android Developers](https://developer.android.com/develop/ui/compose/mental-model) [已验证: 官方文档]
- [Compose Compiler Metrics | Android Developers](https://developer.android.com/develop/ui/compose/performance#compose-compiler-metrics) [已验证: 官方文档]
- [Layout Inspector for Compose | Android Developers](https://developer.android.com/studio/debug/layout-inspector/compose) [已验证: 官方文档]
- [Compose and View Interoperability | Android Developers](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis) [已验证: 官方文档]
- [朱涛·沉思录：如何优化 Compose 的性能](https://mp.weixin.qq.com/s?__biz=Mzg5MDY5ODk2MQ==&mid=2247485054) [来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_沉思录_如何优化_Compose_的性能_通过_底层原理_寻找答案.md]
- [提升 Jetpack Compose 性能 | Kotlin 社区](https://mp.weixin.qq.com/s?__biz=MzIyMzg2MzQxNg==&mid=2247486800) [来源: obsidian/Personal-Knowlodge/source/2026-03-07_wechat_提升Jetpack_Compose_性能.md]
- [Compose 渲染性能到底怎么样 | 程序员江同学](https://mp.weixin.qq.com/s?__biz=MzkzNjMxNzY5NQ==&mid=2247484027) [来源: obsidian/Personal-Knowlodge/source/2026-03-08_wechat_Compose_渲染性能到底怎么样.md]
- [用 derivedStateOf 提升性能 | 郭霖](https://mp.weixin.qq.com/s?__biz=MzA5MzI3NjE2MA==&mid=2650284101) [来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_原创_写给初学者的Jetpack_Compose教程_用derivedStateOf提升性能.md]
- [掌握 Android Compose：从基础到性能优化全面指南](https://mp.weixin.qq.com/s?__biz=MzkyNTUyNDA5Nw==&mid=2247485870) [来源: obsidian/Personal-Knowlodge/source/2026-03-06_wechat_掌握_Android_Compose_从基础到性能优化全面指南.md]
