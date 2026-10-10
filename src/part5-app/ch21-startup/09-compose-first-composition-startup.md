---
title: Compose 首次组合开销与启动性能
chapter: '21.9'
section: '21.9'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: Compose BOM 2026.08.00 (Compose 1.12.0), AOSP androidx-compose-release@963bf914
confidence: medium-high
tags:
- compose
- startup
- first-composition
- baseline-profile
- cold-start
related_chapters:
- '21.3'
- '21.4'
- '22.3'
- '22.4'
- '22.9'
- '13.8'
sources:
- type: androidx
  path: platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/AndroidComposeView.android.kt
- type: androidx
  path: platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Recomposer.kt
- type: official
  path: https://developer.android.com/topic/performance/baselineprofiles/overview
- type: clippings-structure
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: local
  path: src/part5-app/ch22-rendering-practice/03-compose-compiler-modifier-diagnostics.md
- type: local
  path: src/part5-app/ch21-startup/04-baseline-startup-cloud-profile.md
---

# Compose 首次组合开销与启动性能

Jetpack Compose 的首屏比传统 View 页面多一个阶段：组合（composition）。组合执行 `@Composable` UI 描述，并把结果记录成一份后续可以继续更新的结构。这个阶段值多少钱，我们先对比两边各做哪些事：View 页面要执行 XML inflate、对象绑定、测量、布局和绘制；Compose 要执行 UI 描述，维护 Slot Table，创建 UI 节点，再完成布局和绘制。Slot Table 是 runtime 维护的一张表，记录调用分组、参数和 `remember` 槽位。两种 UI 工具包的成本结构不同，差值要放在设备、构建类型、编译状态和页面内容的具体背景下才有意义。

> 源码基线：Android 17 / API 37 / AOSP `android-17.0.0_r1`。

Compose 仍是随应用发布的 AndroidX 库，没有并入 Android 17 framework。平台侧的首帧仍由 Activity 生命周期、`ViewRootImpl` 的 View 遍历、HWUI 与 `RenderThread` 承接；Compose 在应用进程内完成组合，再通过一个 View 宿主接入这条渲染路径。

## 1. 从 `setContent` 到首帧：源码中的边界

### 1.1 Activity 安装的是 `ComposeView`

我们从入口看起。AndroidX 的 `ComponentActivity.setContent` 扩展函数会先检查 `android.R.id.content` 的第一个子 View 是不是 `ComposeView`；没有可复用实例时，它会：

1. 创建 `ComposeView`；
2. 设置父 `CompositionContext` 与 content lambda：前者让子组合继承调度关系和环境值，后者声明 UI 的 `@Composable` 根函数；
3. 把提供生命周期、ViewModel 存储和状态恢复能力的 `LifecycleOwner`、`ViewModelStoreOwner`、`SavedStateRegistryOwner` 安装到 decor view，也就是窗口最外层的 View；
4. 调用 Activity 的 `setContentView()`。

“Activity 直接插入 `AndroidComposeView`”的说法与源码不符：公开宿主是 `ComposeView`；内部组合创建时，`AbstractComposeView` 才会创建或复用 `AndroidComposeView`，后者继承 `ViewGroup`，负责协调 Compose UI 节点与 Android View 的测量、布局、输入和绘制。

`attach` 表示 View 已接入窗口。`ComposeView.setContent` 在 View 尚未 attach 时只保存 content，并把 `shouldCreateCompositionOnAttachedToWindow` 置为 `true`；如果 View 已 attach，当前实现会立即调用 `createComposition()`。初始组合在 attach 或显式调用 `createComposition()` 时创建，以先发生者为准。所以 `setContent {}` 会随 View attach、Lifecycle 状态和父组合的准备时机推进，把它归类为“一次纯异步入队”并不可靠。

### 1.2 窗口级 `Recomposer` 受 Lifecycle 驱动

`Recomposer` 是 Compose runtime 的调度器：它接收状态失效通知，安排重组，并把变化应用到一个或多个 `Composition`。`AbstractComposeView` 会优先使用显式父 context、View 树中的 composition context 或缓存；都没有时，再通过 `windowRecomposer` 为窗口创建或取得 `Recomposer`。默认创建策略使用 UI 线程的 `AndroidUiDispatcher`，并从 View 树寻找 `LifecycleOwner`：

- Lifecycle 至少到 `STARTED` 时，frame clock 才持续提供可见帧，它向动画和重组提供帧时间；
- `ON_STOP` 会暂停 frame clock；
- `ON_DESTROY` 会取消对应 `Recomposer`；
- 宿主从窗口 detach 时，窗口级 `Recomposer` 也会被取消；
- 找不到必需的 View tree owner 时，当前实现会抛出异常，不会安静等待一个不确定时长。

Fragment 中使用 `ComposeView` 时，我们要让 View 树 owner 与组合释放策略匹配。这属于生命周期正确性问题，用 owner 与策略是否匹配来衡量，而不是固定的毫秒数。

### 1.3 初始 composition 做了哪些工作

初始组合开始时，runtime 先启动全局 Snapshot 管理——Snapshot 负责协调状态读写与失效通知——随后建立 `Composition(UiApplier, parentContext)`，把 Activity/窗口提供的 `CompositionLocal` 环境值和业务 content 交给它。`CompositionLocal` 沿 UI 树隐式提供主题、密度等上下文；`UiApplier` 把组合产生的变化应用到 Compose UI 节点树。

进入业务根节点后，runtime 执行本轮会进入的 composable group。group 由 Compose 编译器在可组合调用周围建立，是可跟踪单元，其结构、参数和缓存槽位都记入 Slot Table。

哪些内容会进入本轮组合，先明确几条：

- 初始组合没有上一轮结果可复用，也就没有“靠上一轮参数跳过”这回事；
- 条件分支没有选中的内容不会执行；
- Lazy layout 按需组合可见项，尚未请求的 item 不会因为数据集合存在就全部执行；
- 已进入 group 中 `remember { ... }` 的 calculation，也就是花括号内的计算，会执行一次；
- 一个 composable 可以不产生布局节点，也可以产生多个节点，函数调用数与 UI 节点数没有换算关系。

所以首次成本更适合按几部分加总来估计，`N × M` 这样的层数公式套不上：被进入的 composable 工作量；创建的布局节点、modifier 节点和 semantics 节点；业务计算、子组合、文本与图片处理；以及应用变更、测量、布局和绘制。其中 modifier 节点承载布局、绘制或输入行为，semantics 节点保存无障碍和测试所需的语义信息。

### 1.4 composition 完成后仍要经过 View traversal

初始结果应用到 UI 树后，`AndroidComposeView` 仍是 `ViewRootImpl` 管理的一棵 View 子树，仍要走一轮 View traversal——`ViewRootImpl` 调度的测量、布局和绘制。我们顺着这棵子树看可见路径：

1. `AndroidComposeView.onMeasure()` 驱动 Compose 节点测量；
2. `onLayout()` 完成节点放置，并派发位置回调；
3. `dispatchDraw()`/内部 draw 路径记录绘制命令；
4. HWUI 与 `RenderThread` 处理 display list（已记录的绘制命令）、GPU 工作和图形 buffer 提交；
5. SurfaceFlinger 合成各窗口图层后，像素才出现在屏幕上。

组合只是首帧中的一段。若 Perfetto 系统 trace 显示组合很短，而主线程 I/O、文本测量、图片解码、View traversal 或 RenderThread 很长，我们该去处理对应的那一段；继续删 composable 层级帮不上忙。

## 2. 初始 composition 与重组不能混为一谈

初始组合和重组是两件事，优化手段也各有归属。重组（recomposition）是状态变化后重新执行受影响 UI 描述的过程：重组优化看“输入改变后，哪些 group 可以跳过”，初始组合看“首屏第一次要建立多少内容”。稳定类型、Strong Skipping、延后状态读取等能力主要减少后续重复工作；Strong Skipping 指参数和状态允许时跳过可跳过调用的编译器策略。首屏要进入的根内容，不在这些能力的节省范围内。

`remember` 只缓存当前组合后续可复用的结果。下面的写法可以避免每次重组都重新排序，但排序仍处于初始组合的首帧路径。

```kotlin
@Composable
fun HomeScreen(items: List<Item>) {
    val sortedItems = remember(items) {
        items.sortedByDescending(Item::score)
    }

    HomeContent(sortedItems)
}
```

这段代码适合计算规模可控、结果只服务 UI 的场景。数据量大或排序涉及 I/O 时，我们把排序挪到数据准备阶段完成——repository 封装数据来源，use case 封装一项业务操作，ViewModel 也可以承担——再把准备好的 UI state，也就是可直接用于渲染的页面状态，传入首屏。把代码从 Activity 移进 ViewModel 并不会自动延迟它：只要首屏同步创建 ViewModel 并等待结果，这段工作仍属于首帧显示时间 TTID 或完整显示时间 TTFD 的统计路径。

`remember(LazyThreadSafetyMode.NONE)` 并不存在于 Compose API：`remember` 的公开重载接收 calculation 和可选 keys，`LazyThreadSafetyMode` 参数属于 Kotlin `lazy()`。它也关不掉 Snapshot 对状态读取和失效通知的跟踪。

## 3. 首屏开销应按来源拆分

拿到一份首屏 trace，我们先把开销按来源归类：

| 成本来源 | 常见内容 | 判断证据 |
|---|---|---|
| AndroidX/应用类加载 | Compose runtime、UI、Material、导航及业务类首次加载 | Perfetto 的 class loading、ART（Android Runtime）与主线程 slice（带起止时间的 trace 片段） |
| 宿主与组合建立 | `ComposeView`、`AndroidComposeView`、window recomposer、CompositionLocal 环境 | AndroidX 粗粒度 trace、方法 trace、调用栈 |
| 业务组合 | UI state 转换、集合处理、modifier 构建、首屏节点创建 | Composition Tracing、业务自定义 trace |
| 布局 | 约束传播、文本测量、Lazy 子组合、自定义布局 | `AndroidOwner:onMeasure`、`onLayout` 附近的调用 |
| 绘制与渲染 | Canvas 命令记录、图层、图片上传、shader（GPU 着色程序）、RenderThread/GPU | `AndroidOwner:draw`、FrameTimeline（系统记录的帧生命周期）、RenderThread、GPU 轨道 |
| 首屏外部依赖 | 数据库、磁盘、Binder 跨进程调用、网络、字体与图片资源 | I/O、Binder、线程调度、业务 ready 状态 |

“Compose Runtime 有多少个类”“解释器比 AOT 慢几倍”这类数字，落到本项目首帧时间上还隔着好几层：AOT 是安装期或安装后的提前编译；R8 是 release 构建使用的代码压缩与优化工具，会改变类和方法布局；Baseline Profile 是一组随应用交付的热点类与方法规则，会改变安装后的编译状态；设备的存储、CPU、刷新率和热状态也各不相同。所以固定毫秒数只能作为某次实验的结果，引用时要连同设备型号、系统版本、APK、启动模式、编译模式和样本分布一起保存。

`ComponentActivity` 与 `AppCompatActivity` 之间的差值同样要实测。只需要 Activity 基础能力的纯 Compose 页面可以优先评估 `ComponentActivity`；依赖 AppCompat delegate、旧主题或兼容能力的页面保留 `AppCompatActivity`。迁移是否有收益，要比较同一 release APK 的 Macrobenchmark 结果；Macrobenchmark 从应用进程外测量完整用户流程，基类名称代替不了证据。

## 4. Baseline Profile 与 Startup Profile 各优化什么

### 4.1 库 Profile 与应用代码的覆盖范围

Compose 以应用依赖的库发布，代码不在 platform boot image 中——boot image 是系统预先编译、应用间共享的一组核心 framework 类。Compose 的发布物会附带 Baseline Profile；应用合并这些 library profile 后，ART 可以提前编译规则覆盖的库代码路径。

两个容易混淆的点：

- `androidx.compose:compose-bom` 是 BOM（Bill of Materials，依赖版本清单），只负责让一组 Compose 依赖选用兼容版本。它本身不含 Compose 实现代码；承载 Baseline Profile 的 AAR（Android 库归档）另有其物；
- Compose 自带的规则只覆盖 Compose 库代码，不会自动覆盖应用自己的 composable、ViewModel、导航和数据准备路径。

应用仍应使用 `BaselineProfileRule` 采集桌面启动入口、通知入口、deep link（由 URI 直接打开应用内页面）等主要路径，并让测试走到首屏可交互状态。Profile 只改变代码编译状态，不会让数据库查询、网络等待或图片解码消失。

### 4.2 Startup Profile 是构建期 DEX 布局输入

Startup Profile 是 Baseline Profile 中专门标记启动路径的规则子集。DEX 是 APK 内承载 Android 字节码的文件；R8 在构建期依据 Startup Profile 调整 DEX 中的类和方法布局，让启动代码尽量聚集在读取成本较低的位置，尤其是最先加载的主 DEX。它在 Android 15 之前就已存在，而且是一项构建期输入；ART 在安装阶段“优先编译一份较小 Profile”的说法，与它无关。

当前官方文档建议使用 Macrobenchmark 1.2.0+、AGP（Android Gradle Plugin）8.2+ 和 Android Studio Iguana+，并在 release 构建中开启 R8。DEX layout optimization 从 AGP 8.1 开始可用，AGP 8.3 起默认开启；使用 AGP 8.1～8.2 时还要在 `baselineProfile {}` 中显式设置 `dexLayoutOptimization = true`。依赖库可以贡献 Baseline Profile；Startup Profile 只能来自应用自己定义的启动测试。详细生成与产物校验见 [21.4 Baseline、Startup 与 Cloud Profile 编译优化](04-baseline-startup-cloud-profile.md)。

### 4.3 类预加载与 Profile 的分工

在 `Application.onCreate()` 中调用 `Class.forName()` 预加载 Compose 类，效果只是把类加载挪到更早的主线程路径，还可能扩大每次启动的必做集合；它替代不了 AOT 编译，也保证不了启动代码在 DEX 中相邻存放。

更稳妥的做法是让 Baseline Profile 覆盖自然启动 CUJ（Critical User Journey，一条需要重点保障的用户流程），让 Startup Profile 反映相同入口，再从 release trace 中确认类加载、首次执行和 DEX 读取是否改善。不要编造“预热所有 Compose 类”的启动场景。

## 5. 缩减初始 composition 的有效手段

### 5.1 首帧只建立当前需要显示的内容

进入具体手段前，我们先看首屏根节点常见的无效工作：一次性创建未选中的标签页内容、构建折叠区域、为暂不可见弹窗准备完整 UI、同步格式化大集合，以及在页面根部读取与首屏无关的状态。

可以把不可见且非必要的子树留在条件分支外，等业务状态或用户动作满足后再进入 composition。拿空白壳层刻意压低 TTID 并不可取——首帧应给出有意义的可见反馈，主要内容可用时再按业务定义上报 TTFD。

导航容器和页面预取的行为会随库版本及配置变化，不要自行用 Lifecycle observer 创建第二套页面组合；组合与 UI owner、Snapshot、Lifecycle、资源和主线程调度有关。若某次导航确有可测的首次进入延迟，应使用对应组件公开的预取能力，或在数据层预取可复用数据。

Compose UI 1.11 起提供 `ComposeViewContext`，可让尚未 attach 的 `ComposeView` 提前创建组合，官方示例场景是 RecyclerView item 预取。这个 API 允许“未挂到 View 树时组合”，但依旧依赖一个已 attach View 提供的上下文与 owner，对 UI 代码运行线程的限制也依旧。若预取的 `ComposeView` 最终没有 attach，必须调用 `disposeComposition()` 释放资源。整页启动是否值得这样预取，应由 trace 和端到端基准决定。

### 5.2 把重计算移出 composable，但保留状态所有权

适合移出的工作包括：

- 大集合排序、分组、diff（计算新旧集合变化）和字符串拼装；
- JSON/数据库读取、磁盘探测与同步 Binder 调用；
- 与 UI 无关的正则、加密、图片解码和模型初始化；
- 每次进入根 composable 都重新创建的格式化器、解析器或配置对象。

`remember` 适合缓存 UI 局部对象；阻塞工作放进 `remember`，安全性问题依然存在。`rememberSaveable` 会把值接入实例状态保存与恢复，适合承载小而能稳定序列化的值；大对象或无法稳定序列化的业务模型应放在别处。

`LaunchedEffect` 会在进入组合后启动协程，“首帧后免费执行”的印象要打折扣：它的启动、主线程片段以及切换 dispatcher 前的代码，仍可能与首帧竞争；dispatcher 决定协程在哪类线程执行。首屏必需数据应有明确的 loading/ready 状态，也就是区分“仍在准备”和“已经可显示”；非必需任务交给受生命周期管理的后台工作，并用 trace 验证调度位置。

### 5.3 正确选择 `Column` 与 Lazy layout

官方文档给出的划分很直白：固定且数量很少的内容可以使用 `Column`/`Row`；数量大或未知时交给 Lazy layout，避免一次组合并布局所有 item。要给出“100 项只组合 8 项”“耗时降低 50%”这类承诺，得先弄清可见数量从哪来：它取决于 viewport、item 尺寸、content padding、预取与版本实现。

Lazy 首屏还要注意：

- item 在异步内容到达前不要是 0 像素，否则一次 measure 可能判断 viewport 能容纳大量 item，造成无效组合；
- 为可重排数据提供稳定 `key`；
- 异构列表提供合适的 `contentType`，让 Lazy 容器知道哪些 item 结构兼容，帮助后续复用组合结果；
- 不要把大量元素塞进同一个 `item { ... }`，否则它们仍会作为一个单元一起组合和测量；
- 小型固定按钮组、标签组没有理由只为“懒加载”换成 `LazyRow`。

### 5.4 `SubcomposeLayout` 的适用场景

`SubcomposeLayout` 允许父布局拿到 constraints 后，在 measure 期间选择并组合子内容，这个过程称为 subcomposition（子组合）。`LazyColumn`、`LazyRow` 和 `BoxWithConstraints` 属于官方文档列出的典型“子内容依赖父布局阶段”场景。

普通 `Box` 即使使用 `Modifier.align`，源码仍调用常规 `Layout` 和 `BoxMeasurePolicy`，并不会因此变成 `SubcomposeLayout`。自定义页面若只为推迟工作就默认选择子组合，代价是把一部分组合工作移到布局阶段，Perfetto 中经常表现为两个相邻工作块，还可能抬高当前帧总成本；它的适用条件是子内容必须依赖测量约束，或需要按可见区域创建。

### 5.5 阶段反馈与首帧后的第二帧

如果首帧先用旧值绘制，布局回调再写状态、触发下一帧组合，就形成了“后一个阶段把结果写回前一个阶段”的循环，常被称为 phase feedback（阶段反馈）：

- `onSizeChanged()` / `onGloballyPositioned()` 得到尺寸；
- 把尺寸写进 `MutableState`——这类可变状态会触发 Compose 失效通知；
- 在同一布局关系中把该状态读成 `padding`、`height` 或子节点位置。

若父子关系可以在同一次测量中求解，应使用现有布局组件或自定义 `Layout`。自适应页面也应从当前 constraints 或窗口尺寸类别派生结构，避免把一次布局结果绕回组合。

## 6. Android 17 多窗口与多进程边界

自由窗口、分屏和旋转都可能改变窗口约束。约束变化后会重新测量，页面读取窗口类别时会发生必要的重组，这属于正确行为。在 `onCreate()` 里等一个所谓“稳定的 `WindowMetrics`”再调 `setContent`，只会推迟首帧：`WindowMetrics` 记录的是某一时刻的窗口范围和系统区域信息，可调整窗口没有永久稳定尺寸。

启动测试至少覆盖一个常用全屏尺寸和一个可调整窗口尺寸。若窗口拖动期间重组过多，应检查状态读取范围、窗口类别离散化和布局到状态的反馈，不要冻结一次 `getCurrentWindowMetrics()` 结果。

每个 Android 进程有独立的 heap、ClassLoader 和 Compose runtime 状态；只有创建了 Compose UI 宿主的进程，才会产生对应的类加载与组合成本。通知和 App Widget 常使用 `RemoteViews`，把受限 View 描述交给系统或其他进程显示；Glance 最终生成的也是 `RemoteViews`，这条路径套用 Activity 里的 `AndroidComposeView` 首帧模型并不合适。多进程 Baseline Profile 是否覆盖入口，要用该进程自己的启动 trace 验证。

## 7. View/Compose 混合页面

混合页面会同时执行 View 的 inflate/binding 和 Compose 宿主的初始组合。每个独立 `ComposeView` 都有自己的组合生命周期，内部持有 Compose UI owner；首屏分散许多 `ComposeView`，也可能推高宿主创建、owner 查找和组合管理的成本。

优化时可以评估把相邻 Compose 内容放进同一个宿主，但要保留 Fragment/View 各自的生命周期。`ViewCompositionStrategy` 决定 View 宿主中的组合何时释放，先保证它与实际生命周期匹配。为了少一个宿主而让组合越过 Fragment view 生命周期，等于拿未经证实的小幅性能收益去换泄漏或状态错误。

反方向的 `AndroidView`/`AndroidViewBinding` 是在 Compose 中承载传统 View 的互操作 API，也会把 View 创建和测量带入 Compose 页面。归因时我们在 trace 中分别查看 XML inflate、View 构造、组合、布局和绘制；整个混合页的耗时要按这些段拆开看，而不是全部记到 Compose。

## 8. 用 TTID、TTFD 和 Perfetto 测量

### 8.1 TTID 与 TTFD 回答不同问题

TTID 对应 `StartupTimingMetric.timeToInitialDisplayMs`：从系统收到启动 intent 到目标 Activity 第一帧显示。TTFD 对应 `timeToFullDisplayMs`：从同一起点到应用报告 fully drawn，以包含或紧随该信号的首帧作为终点。fully drawn 表示应用定义的主要内容已经可用，不要求所有后台任务结束。

Compose 首屏可以用 `ReportDrawnWhen` 把“主要内容可交互”写成可审查的布尔条件。它把条件注册到 Activity 的 `FullyDrawnReporter`，并观察条件读取的 Snapshot state；条件变为 `true` 后，Activity 才能完成 fully drawn 上报。下面示例用于等待状态加载完成，合法空态也必须能够进入 `Ready`。

```kotlin
@Composable
fun HomeRoute(state: HomeUiState) {
    ReportDrawnWhen {
        state is HomeUiState.Ready
    }

    HomeScreen(state)
}
```

这里的 ready 是业务完成条件，不要求列表非空。若错误页或离线页也属于可交互完成态，应让这些状态同样释放 fully drawn reporter，避免 TTFD 样本永久缺失。

### 8.2 Macrobenchmark 固定实验条件

下面的基准骨架用于测量带 Baseline Profile 的冷启动。目标 variant（参与测试的构建变体）应接近生产包，开启 R8，并设置为 `profileable`、non-debuggable：前者允许性能工具采集有限的生产级诊断数据，后者避免调试构建的额外开销。

```kotlin
@RunWith(AndroidJUnit4::class)
class HomeStartupBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun coldStartupWithProfile() {
        benchmarkRule.measureRepeated(
            packageName = TARGET_PACKAGE,
            metrics = listOf(StartupTimingMetric()),
            compilationMode = CompilationMode.Partial(
                baselineProfileMode = BaselineProfileMode.Require
            ),
            startupMode = StartupMode.COLD,
            iterations = 10,
            setupBlock = { pressHome() }
        ) {
            startActivityAndWait()
        }
    }
}
```

`CompilationMode.Partial(Require)` 会要求目标 APK 同时包含可安装的 Baseline Profile 与 ProfileInstaller，缺少任意一项都会在编译准备阶段报错。它会按 profile 做部分 AOT 编译，适合验证应用的 profile 交付是否完整。另建 `CompilationMode.None()` 场景会清除编译 profile，不做预编译，并允许代码在运行中 JIT；它用于观察通常偏慢的最差条件，性能下界和用户默认安装状态都不是它的定位。比较前要固定设备、系统、APK、启动入口、数据集、网络替身和温控条件，并查看多轮的中位数与分布。

### 8.3 Perfetto 负责归因

Macrobenchmark 会产出 system trace，也就是把系统与应用多个线程的带时间事件放在同一条时间轴上。初始分析可按这条顺序进行：

1. 在 Android App Startups/TTID 区间确认主线程何时进入 Activity、`setContent` 和首次 View traversal；
2. 对齐 `Choreographer#doFrame`、FrameTimeline、主线程、RenderThread、Binder、I/O 与 GC；
3. 查看 Compose 粗粒度 slice，再判断长段位于组合、测量/布局还是绘制；
4. 开启 Composition Tracing 后，把长段定位到具体 composable；
5. 给业务数据准备、图片请求和路由解析增加低基数自定义 trace，也就是只使用少量、名称固定的事件标签，再与 Compose slice 对齐。

本轮核对的 AndroidX 提交中存在 `Compose:initializeView`、`Recomposer:recompose`、`AndroidOwner:onMeasure`、`AndroidOwner:onLayout`、`AndroidOwner:draw` 等内部 slice。这些名称随 AndroidX 版本变化，属于实现细节而非公开 API，每条 trace 里也未必齐全；分析脚本若依赖这些名称，必须与被测 Compose 版本一起维护。

细粒度 composable 名称需要 `androidx.compose.runtime:runtime-tracing`。使用 Compose BOM 时，这项依赖无需单列版本。Android Studio 可以自动完成常规 system trace 配置；从终端手动采集还需要 `tracing-perfetto`、只用于测试构建的 `tracing-perfetto-binary`、名为 `track_event` 的 Perfetto 数据源和 `ENABLE_TRACING` 广播。Macrobenchmark 的完整 Composition Tracing 还要在测试模块加入 tracing 依赖，并传入 instrumentation 参数 `androidx.benchmark.fullTracing.enable=true`。`tracing-perfetto-binary` 会明显增大包体，发布生产包时应把它留在测试构建里。

在 `Application.onCreate()` 里调一个笼统的 `Trace.enable()`，或者假定 Android 15 到 Android 17 会自动打开细粒度 Compose tracing，都靠不住；采集方式取决于 Android Studio、Macrobenchmark 或手动 Perfetto 路径，详见 [§22.3 Compose Runtime Tracing](../ch22-rendering-practice/03-compose-compiler-modifier-diagnostics.md)。

`FrameMetrics` 和 `FrameTimingMetric` 适合回答帧是否超时；耗时是否来自组合，它们单独回答不了。反过来，某个 composable slice 较长，用户也未必已经看到卡顿，下结论前还要与同一帧的 deadline（完成时限）、主线程和 RenderThread 工作对齐。

## 9. 常见症状与下一步证据

| 症状 | 先看什么 | 常见处理方向 |
|---|---|---|
| TTID 高，初始组合明显长 | 进入的首屏子树、业务计算、Profile 覆盖 | 推迟不可见内容、移出重计算、补应用 Profile |
| TTID 高，Compose slice 很短 | ContentProvider、DI（依赖注入）、I/O、类加载、启动画面、View traversal | 回到完整启动流程，不改 UI 结构猜测 |
| 组合正常，测量/布局长 | 文本、Lazy item、子组合、自定义布局 | 减少重复测量，检查约束与 0 尺寸 item |
| TTID 正常，TTFD 长 | 数据 ready、图片、错误/空态、上报条件 | 优化异步依赖并修正 fully drawn 定义 |
| 首帧后立即出现同结构重组 | 布局回写状态、effect 更新、窗口类别抖动 | 消除阶段反馈，缩小状态读取范围 |
| `Partial` 明显优于 `None`，发布包却无收益 | Profile 打包、安装和编译状态 | 检查 APK/AAB（应用商店分发包）中的 profile 产物与安装渠道 |
| View/Compose 混合页首帧变慢 | XML inflate、多个宿主、`AndroidView` 创建 | 分段 trace 后按最大成本处理 |

## 10. 检查清单

- 是否把平台基线限制在 Android 17 / API 37，并把 Compose 视为 AndroidX 库？
- 是否准确区分 `ComposeView`、内部 `AndroidComposeView`、`Composition` 与 `Recomposer`？
- 是否删除没有设备、构建、编译模式和样本分布的固定毫秒数或百分比？
- 是否明确初始组合只执行进入的分支与被请求的 Lazy 内容？
- 是否理解 `remember` 的 calculation 在初始组合中仍要执行？
- 是否把 Baseline Profile 的 AOT 编译和 Startup Profile 的构建期 DEX 布局分开？
- 是否避免 `Class.forName()` 预热、后台自行驱动 composition 和无效的 `remember(LazyThreadSafetyMode.NONE)`？
- 是否按内容规模选择 `Column`/`Row` 或 Lazy layout，并避免 0 像素 item？
- 是否只在子内容依赖 constraints 时使用子组合，并确认普通 `Box` 不属于这一路径？
- 是否用 release-like Macrobenchmark 同时记录 TTID/TTFD，并以 Perfetto 做阶段归因？
- 是否把内部 trace slice 名称视作版本相关实现细节？
- 是否在多窗口和混合页面中优先保证生命周期、状态与布局正确，再比较性能？

## 小结

Compose 首次组合只是启动首帧中的一个阶段：业务 composable 建立节点后，仍要经过 View 测量、布局、绘制、RenderThread 和系统合成。优化先缩小首帧实际进入的 UI 与业务计算，再用 Baseline/Startup Profile 改善代码执行和 DEX 布局，并以 TTID/TTFD、FrameTimeline 与 Composition Tracing 区分组合、布局、绘制和外部依赖。重组优化是后续工作，代替不了首次组合治理。

## 参考资料

- [AndroidX `ComponentActivity.setContent` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/activity/activity-compose/src/main/java/androidx/activity/compose/ComponentActivity.kt)
- [AndroidX `ComposeView` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/ComposeView.android.kt)
- [AndroidX `WindowRecomposer` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/WindowRecomposer.android.kt)
- [AndroidX `Recomposer` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Recomposer.kt)
- [AndroidX `remember` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composables.kt)
- [AndroidX `Box` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/foundation/foundation-layout/src/commonMain/kotlin/androidx/compose/foundation/layout/Box.kt)
- [本轮 AndroidX 源码提交 `963bf914`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274)
- [Compose BOM 与库版本映射](https://developer.android.com/develop/ui/compose/bom/bom-mapping)
- [`ComposeViewContext` API](https://developer.android.com/reference/kotlin/androidx/compose/ui/platform/ComposeViewContext)
- [Compose phases](https://developer.android.com/develop/ui/compose/phases)
- [Compose performance](https://developer.android.com/develop/ui/compose/performance)
- [Compose Baseline Profile](https://developer.android.com/develop/ui/compose/performance/baseline-profiles)
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Create Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [Lazy lists and grids](https://developer.android.com/develop/ui/compose/lists)
- [Jetpack Glance](https://developer.android.com/develop/ui/compose/glance)
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Macrobenchmark `CompilationMode`](https://developer.android.com/reference/androidx/benchmark/macro/CompilationMode)
- [App startup time: TTID and TTFD](https://developer.android.com/topic/performance/vitals/launch-time)
- [21.4 Baseline、Startup 与 Cloud Profile 编译优化](04-baseline-startup-cloud-profile.md)
- [§21.1 启动性能监控](01-app-startup-path-monitoring.md)
- [22.3 Compose 性能、Compiler 与 Modifier.Node 诊断](../ch22-rendering-practice/03-compose-compiler-modifier-diagnostics.md)
- [§22.6 View/Compose 混合迁移](../ch22-rendering-practice/06-compose-view-interop.md)
- [§22.2 Compose LazyList 性能](../ch22-rendering-practice/02-recyclerview-compose-lazylist.md)
- [§13.8 Compose 渲染管线](../../part2-performance/ch13-rendering-pipelines/08-compose-rendering-pipeline.md)
