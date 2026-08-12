---
title: "Compose 首次组合开销与启动性能"
chapter: "21.13"
section: "21.13"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-27"
last_verified_against: "Compose BOM 2025.12.00, Kotlin 2.2, AOSP androidx-compose-release"
confidence: medium-high
tags: [compose, startup, first-composition, baseline-profile, cold-start]
related_chapters: ["21.3", "21.4", "22.3", "22.20", "22.26", "18.23"]
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
---

# Compose 首次组合开销与启动性能

Compose 首屏比传统 View 页面多一个 composition 阶段，但“用了 Compose 就固定多花几十毫秒”不是可复用的结论。View 页面也要负责 XML inflate、对象绑定、measure、layout 和 draw；Compose 则把 UI 描述执行、Slot Table 维护、节点创建，以及后续的 layout、draw 放进首帧路径。两者的成本结构不同，不能脱离设备、构建类型、编译状态和页面内容给出统一差值。

平台边界固定在 Android 17 / API 37 / `android-17.0.0_r1`。Compose 仍是随应用发布的 AndroidX 库，并没有并入 Android 17 framework。平台侧仍由 Activity 生命周期、`ViewRootImpl` traversal、HWUI 与 `RenderThread` 承接首帧；Compose 在应用进程内完成 composition，并通过一个 View host 接入这条渲染路径。

## 1. 从 `setContent` 到首帧：源码中的边界

### 1.1 Activity 安装的是 `ComposeView`

AndroidX 的 `ComponentActivity.setContent` 扩展先检查 `android.R.id.content` 的第一个子 View 是否已经是 `ComposeView`。没有可复用实例时，它会：

1. 创建 `ComposeView`；
2. 设置父 `CompositionContext` 和 content lambda；
3. 把 `LifecycleOwner`、`ViewModelStoreOwner`、`SavedStateRegistryOwner` 安装到 decor view；
4. 调用 Activity 的 `setContentView()`。

这里不应写成“Activity 直接插入 `AndroidComposeView`”。公开 host 是 `ComposeView`；内部 composition 创建时，`AbstractComposeView.setContent` 才会创建或复用 `AndroidComposeView`。后者继承 `ViewGroup`，是 Compose UI 节点与 Android View 渲染管线之间的 owner。

`ComposeView.setContent` 在 View 尚未 attach 时只保存 content，并把 `shouldCreateCompositionOnAttachedToWindow` 置为 `true`。初始 composition 在 attach 或显式调用 `createComposition()` 时创建，以先发生者为准。因此，`setContent {}` 不能简单标成“一次纯异步入队”，它会随 View attach、Lifecycle 状态和父 composition 的准备时机推进。

### 1.2 窗口级 `Recomposer` 受 Lifecycle 驱动

`AbstractComposeView` 会优先使用显式父 context、View 树中的 composition context 或缓存；都没有时，再通过 `windowRecomposer` 为窗口创建或取得 `Recomposer`。默认的窗口 factory 使用 UI 线程的 `AndroidUiDispatcher`，并从 View 树寻找 `LifecycleOwner`：

- Lifecycle 至少到 `STARTED` 时，frame clock 才持续提供可见帧；
- `ON_STOP` 会暂停 frame clock；
- `ON_DESTROY` 会取消对应 `Recomposer`；
- 找不到必需的 View tree owner 时，当前实现会抛出异常，而非安静等待一个不确定时长。

这也是 Fragment 中使用 `ComposeView` 时必须让 View 树 owner 与 composition disposal 策略匹配的原因。它关乎生命周期正确性，不应被描述成固定的若干毫秒成本。

### 1.3 初始 composition 做了哪些工作

composition 创建路径会启动全局 Snapshot 管理、建立 `Composition(UiApplier, parentContext)`，再把 Activity/窗口提供的 CompositionLocal 环境和业务 content 交给 runtime。进入业务根节点后，runtime 执行本次会进入的 composable group，记录 Slot Table，并把变化交给 `UiApplier` 创建或更新 Compose UI 节点。

需要把“会进入的内容”说清楚：

- 初始 composition 没有上一份相同 composition 的结果可复用，因此已经进入的 group 不能依靠上一轮参数跳过；
- 条件分支没有选中的内容不会执行；
- Lazy layout 尚未请求的 item 不会因为数据集合存在就全部执行；
- 已进入 group 中的 `remember { ... }` calculation 会执行一次；
- 一个 composable 可以不产生布局节点，也可以产生多个节点，函数调用数不等于 UI 节点数。

所以，首次成本不是 `N × M` 这样的层数公式。更有用的模型是：被进入的 composable 工作量、创建的 layout/modifier/semantics 节点、业务计算、子组合、文本与图片处理，再加上 apply、measure、layout、draw 的总和。

### 1.4 composition 完成后仍要经过 View traversal

初始结果应用到 UI 树后，`AndroidComposeView` 仍是 `ViewRootImpl` 管理的一棵 View 子树。Android 17 上的可见路径可以按边界理解为：

1. `AndroidComposeView.onMeasure()` 驱动 Compose 节点测量；
2. `onLayout()` 完成节点放置，并派发位置回调；
3. `dispatchDraw()`/内部 draw 路径记录绘制命令；
4. HWUI 与 `RenderThread` 处理 display list、GPU 工作和 buffer 提交；
5. SurfaceFlinger 合成后，像素才出现在屏幕上。

composition 只是首帧中的一段。若 Perfetto 显示 composition 很短，而主线程 I/O、文本测量、图片解码、View traversal 或 RenderThread 很长，继续删 composable 层级不会处理对应瓶颈。

## 2. 初始 composition 与重组不能混为一谈

重组优化关注“输入改变后，哪些 group 可以跳过”；初始 composition 关注“首屏第一次需要建立多少内容”。稳定类型、Strong Skipping、延后状态读取等能力主要减少后续重复工作，不能免除首屏需要进入的根内容。

`remember` 也只缓存当前 composition 后续可复用的结果。下面的写法可以避免每次重组都重新排序，但排序仍处于初始 composition 的关键路径。

```kotlin
@Composable
fun HomeScreen(items: List<Item>) {
    val sortedItems = remember(items) {
        items.sortedByDescending(Item::score)
    }

    HomeContent(sortedItems)
}
```

这段代码适合计算规模可控、结果只服务 UI 的场景。数据量大或排序涉及 I/O 时，应在 repository、use case 或 ViewModel 的数据准备阶段完成，并把准备好的 UI state 传入首屏。把代码从 Activity 移进 ViewModel 并不会自动延迟它；只要首屏同步创建 ViewModel 并等待结果，它仍属于 TTID 或 TTFD 路径。

`remember(LazyThreadSafetyMode.NONE)` 不是 Compose API。`remember` 的公开重载接收 calculation 和可选 keys，没有 `LazyThreadSafetyMode` 参数；该参数属于 Kotlin `lazy()`。它也不能用来关闭 Snapshot 状态跟踪。

## 3. 首屏开销应按来源拆分

| 成本来源 | 常见内容 | 判断证据 |
|---|---|---|
| AndroidX/应用类加载 | Compose runtime、UI、Material、导航及业务类首次加载 | Perfetto 的 class loading、ART 与主线程 slice |
| host 与 composition 建立 | `ComposeView`、`AndroidComposeView`、window recomposer、CompositionLocal 环境 | AndroidX coarse trace、方法 trace、调用栈 |
| 业务 composition | UI state 转换、集合处理、modifier 构建、首屏节点创建 | Composition Tracing、业务自定义 trace |
| layout | 约束传播、文本测量、Lazy 子组合、自定义 layout | `AndroidOwner:onMeasure`、`onLayout` 附近的调用 |
| draw/render | Canvas 记录、layer、图片上传、shader、RenderThread/GPU | `AndroidOwner:draw`、FrameTimeline、RenderThread、GPU 轨道 |
| 首屏外部依赖 | 数据库、磁盘、Binder、网络、字体与图片资源 | I/O、Binder、线程调度、业务 ready 状态 |

“Compose Runtime 有多少个类”“解释器比 AOT 慢几倍”都不能直接换算成本项目的首帧时间。R8 会改变类与方法布局，Baseline Profile 会改变编译状态，不同设备的存储、CPU、刷新率和热状态也不同。固定毫秒数只能作为某次实验的结果，必须连同设备型号、系统版本、APK、启动模式、编译模式和样本分布保存。

`ComponentActivity` 与 `AppCompatActivity` 也不适合套用固定差值。只需要 Activity 基础能力的纯 Compose 页面可以优先评估 `ComponentActivity`；依赖 AppCompat delegate、旧主题或兼容能力的页面保留 `AppCompatActivity`。迁移是否有收益，要比较相同 release APK 的 Macrobenchmark，不能拿基类名称代替证据。

## 4. Baseline Profile 与 Startup Profile 各优化什么

### 4.1 Compose 的库 Profile 不覆盖应用代码

Compose 作为库发布，库代码没有 platform boot image 的编译条件。Compose 库随发布物提供 Baseline Profile，应用消费 library profile 后，ART 可以提前编译 profile 覆盖的库路径。

这里有两个容易混淆的点：

- `androidx.compose:compose-bom` 只负责依赖版本对齐，不包含 Compose 实现代码，也不是 Baseline Profile 的承载 AAR；
- Compose 自带的规则只覆盖 Compose 库代码，不会自动覆盖应用自己的 composable、ViewModel、导航和数据准备路径。

应用仍应使用 `BaselineProfileRule` 采集 launcher、通知、deep link 等主要入口，并让测试走到首屏可交互状态。Profile 只改变代码编译状态，不会让数据库查询、网络等待或图片解码消失。

### 4.2 Startup Profile 是构建期 DEX 布局输入

Startup Profile 是启动相关规则的子集。R8 在构建期使用它调整 DEX 布局，尽量把启动路径放在更合适的位置，尤其是主 DEX。它不是 Android 15 才出现的运行时能力，也不是 ART 在安装阶段“优先编译一份较小 Profile”。

当前官方工具要求的核心边界是 AGP、Baseline Profile Gradle Plugin、Macrobenchmark 与 R8 配置；DEX layout optimization 自 AGP 8.3 起默认开启。library 可以贡献 Baseline Profile，但不能替应用贡献 Startup Profile，后者来自应用定义的启动测试。详细生成与产物校验见 [§21.4 Baseline Profile 与 Startup Profile 实战](./04-baseline-profile-practice.md)。

### 4.3 不要用类预加载代替 Profile

在 `Application.onCreate()` 中调用 `Class.forName()` 预加载 Compose 类，只是把类加载移动到更早的主线程路径，还可能扩大每次启动的必做集合。它既不能替代 AOT 编译，也不能保证 DEX 局部性。

更稳妥的做法是让 Baseline Profile 覆盖自然启动 CUJ，让 Startup Profile 反映相同入口，再从 release trace 中确认类加载、首次执行和 DEX 读取是否改善。不要编造“预热所有 Compose 类”的启动场景。

## 5. 缩减初始 composition 的有效手段

### 5.1 首帧只建立当前需要显示的内容

首屏根节点常见的无效工作包括：一次性创建未选中的 tab 内容、构建折叠区域、为暂不可见弹窗准备完整 UI、同步格式化大集合，以及在页面根部读取与首屏无关的状态。

可以把不可见且非必要的子树留在条件分支外，等业务状态或用户动作满足后再进入 composition。这里不能用空白壳层刻意压低 TTID：首帧应给出有意义的可见反馈，主要内容可用时再按业务定义上报 TTFD。

导航容器和页面预取的行为会随库版本及配置变化。不要自行用 Lifecycle observer 在后台创建第二套页面 composition；composition 与 UI owner、Snapshot、Lifecycle、资源和主线程调度有关。若某次导航确有可测的首次进入延迟，应使用对应组件公开的预取能力，或在数据层预取可复用数据。

### 5.2 把重计算移出 composable，但保留状态所有权

适合移出的工作包括：

- 大集合排序、分组、diff 和字符串拼装；
- JSON/数据库读取、磁盘探测与同步 Binder 调用；
- 与 UI 无关的正则、加密、图片解码和模型初始化；
- 每次进入根 composable 都重新创建的 formatter、parser 或配置对象。

`remember` 适合缓存 UI 局部对象，不能把阻塞工作变成安全的首帧工作。`rememberSaveable` 还涉及保存/恢复语义，也不应承载大对象或无法稳定序列化的业务模型。

`LaunchedEffect` 会在进入 composition 后启动协程，不等于“首帧后免费执行”。它的启动、主线程片段以及切换 dispatcher 前的代码仍可能与首帧竞争。首屏必需数据应有明确的 loading/ready 状态；非必需任务交给受生命周期管理的后台工作，并用 trace 验证调度位置。

### 5.3 正确选择 `Column` 与 Lazy layout

官方文档给出的边界很直白：固定且数量很少的内容可以使用 `Column`/`Row`；数量大或未知时，Lazy layout 避免一次组合并布局所有 item。不能据此承诺“100 项只组合 8 项”或“耗时降低 50%”，因为可见数量取决于 viewport、item 尺寸、content padding、预取与版本实现。

Lazy 首屏还要注意：

- item 在异步内容到达前不要是 0 像素，否则一次 measure 可能判断 viewport 能容纳大量 item，造成无效组合；
- 为可重排数据提供稳定 `key`；
- 异构列表提供合适的 `contentType`，帮助后续 composition reuse；
- 不要把大量元素塞进同一个 `item { ... }`，否则它们仍会作为一个单元一起组合和测量；
- 小型固定按钮组、标签组不应只为“懒加载”换成 `LazyRow`。

### 5.4 `SubcomposeLayout` 不是通用加速器

`SubcomposeLayout` 允许父布局拿到约束后，在 measure 期间选择并组合子内容。`LazyColumn`、`LazyRow` 和 `BoxWithConstraints` 属于官方文档列出的典型“子内容依赖父布局阶段”场景。

普通 `Box` 即使使用 `Modifier.align`，源码仍调用常规 `Layout` 和 `BoxMeasurePolicy`，并不因此变成 `SubcomposeLayout`。自定义页面也不应为了推迟工作就默认选择 subcomposition：它会把 composition 工作拆到 layout 阶段，Perfetto 中经常表现为两个相邻工作块，并可能增加当前帧总成本。只有子内容必须依赖测量约束或需要按 viewport 创建时才使用。

### 5.5 避免制造“首帧后立刻再来一帧”

下面这种模式会让首帧先用旧值绘制，再由 layout 回调写状态，触发下一帧 composition：

- `onSizeChanged()` / `onGloballyPositioned()` 得到尺寸；
- 把尺寸写进 `MutableState`；
- 在同一布局关系中把该状态读成 `padding`、`height` 或子节点位置。

若父子关系可以在同一次 measure 中求解，应使用现有布局组件或自定义 `Layout`。自适应页面也应从当前 constraints 或窗口尺寸类别派生结构，避免把一次布局结果绕回 composition。

## 6. Android 17 多窗口与多进程边界

Android 17 的自由窗口、分屏和旋转都可能改变窗口约束。约束变化后发生 remeasure，页面读取窗口类别时发生必要的 recomposition，这属于正确行为。不要在 `onCreate()` 里等待所谓“稳定的 `WindowMetrics`”再调用 `setContent`：可调整窗口没有永久稳定尺寸，这种等待还会推迟首帧。

启动测试至少覆盖一个常用全屏尺寸和一个可调整窗口尺寸。若窗口拖动期间重组过多，应检查状态读取范围、窗口类别离散化和布局到状态的反馈，不要冻结一次 `getCurrentWindowMetrics()` 结果。

每个 Android 进程有独立的 heap、ClassLoader 和 Compose runtime 状态。只有在某个进程创建 Compose UI host 时，它才会产生对应类加载与 composition 成本。通知、App Widget 的 `RemoteViews`，以及基于 Glance 生成 `RemoteViews` 的路径，不能按 Activity 中的 `AndroidComposeView` 首帧模型解释。多进程 Baseline Profile 是否覆盖入口，也应通过该进程的启动 trace 验证。

## 7. View/Compose 混合页面

混合页面会同时负责 View inflate/binding 和 Compose host 的初始 composition。每个独立 `ComposeView` 都有自己的 composition 生命周期，并在内部持有 Compose UI owner；首屏分散许多 `ComposeView` 可能放大 host、owner 查找和 composition 管理工作。

优化时可以评估把相邻 Compose 内容放进同一个 host，但要保留 Fragment/View 生命周期边界。`ViewCompositionStrategy` 的选择应先保证 composition 在正确时机释放。为了少一个 host 而让 composition 越过 Fragment view 生命周期，会把小幅性能猜测换成泄漏或状态错误。

反方向的 `AndroidView`/`AndroidViewBinding` 也会把 View 创建和测量带入 Compose 页面。归因时应在 trace 中拆开 XML inflate、View 构造、composition、layout 和 draw，不能把整个混合页耗时都记到 Compose。

## 8. 用 TTID、TTFD 和 Perfetto 测量

### 8.1 TTID 与 TTFD 回答不同问题

`StartupTimingMetric.timeToInitialDisplayMs` 从系统收到启动 intent 到目标 Activity 第一帧显示。`timeToFullDisplayMs` 到应用报告 fully drawn，并以包含或紧随该报告的首帧为结束边界。

Compose 首屏可以用 `ReportDrawnWhen` 把“主要内容可交互”定义成可审查条件。下面示例用于等待状态加载完成；合法空态也必须能够进入 `Ready`。

```kotlin
@Composable
fun HomeRoute(state: HomeUiState) {
    ReportDrawnWhen {
        state is HomeUiState.Ready
    }

    HomeScreen(state)
}
```

这段条件描述业务 ready，而不是“列表必须非空”。若应用把错误页或离线页也定义为可交互完成态，应让这些状态同样释放 fully drawn reporter，避免 TTFD 样本永久缺失。

### 8.2 Macrobenchmark 固定实验条件

下面的基准骨架用于测量带 Baseline Profile 的冷启动；目标 variant 应接近 production、`profileable`、non-debuggable，并开启 R8。

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

`CompilationMode.Partial(Require)` 会要求 APK 内存在可安装的 Baseline Profile 和 ProfileInstaller，适合验证交付链。另建 `CompilationMode.None()` 场景可以观察无预编译的下界，但它代表偏差的最差条件，不能当成用户默认安装状态。比较前要固定设备、系统、APK、启动入口、数据集、网络替身和温控条件，并看多轮分布。

### 8.3 Perfetto 负责归因

Macrobenchmark 会产出 system trace。初始分析可按这条顺序进行：

1. 在 Android App Startups/TTID 区间确认主线程何时进入 Activity、`setContent` 和首次 traversal；
2. 对齐 `Choreographer#doFrame`、FrameTimeline、主线程、RenderThread、Binder、I/O 与 GC；
3. 查看 Compose coarse slice，再判断长段位于 composition、measure/layout 还是 draw；
4. 开启 Composition Tracing 后，把长段定位到具体 composable；
5. 给业务数据准备、图片请求和路由解析增加低基数自定义 trace，和 Compose slice 对齐。

当前 AndroidX 源码能看到 `Compose:initializeView`、`Recomposer:recompose`、`AndroidOwner:onMeasure`、`AndroidOwner:onLayout`、`AndroidOwner:draw` 等内部 slice。名称会随 AndroidX 版本变化，不是公开 API，也不能假定每条 trace 都完整出现。分析脚本若依赖名称，必须与被测 Compose 版本一起维护。

细粒度 composable 名称需要 `androidx.compose.runtime:runtime-tracing`。使用 Compose BOM 时依赖无需单列版本。Android Studio 可以自动完成常规 system trace 配置；手动 terminal 采集还需要 `tracing-perfetto`、仅测试构建使用的 `tracing-perfetto-binary`、`track_event` data source 和 `ENABLE_TRACING` 广播。Macrobenchmark 的完整 composition tracing 还要按官方文档配置 `androidx.benchmark.fullTracing.enable=true`。

不要在 `Application.onCreate()` 中调用一个笼统的 `Trace.enable()`，也不要假定 Android 15 到 Android 17 会自动打开细粒度 Compose tracing。采集方式取决于 Android Studio、Macrobenchmark 或手动 Perfetto 路径，详见 [§22.22 Compose Runtime Tracing](../ch22-rendering-practice/22-compose-compiler-recomposition-diagnostics.md)。

`FrameMetrics` 和 `FrameTimingMetric` 适合回答帧是否超时，不能单独说明慢在 composition。反过来，某个 composable slice 较长也不等于用户已经看到卡顿；还要与同一帧 deadline、主线程和 RenderThread 工作对齐。

## 9. 常见症状与下一步证据

| 症状 | 先看什么 | 常见处理方向 |
|---|---|---|
| TTID 高，initial composition 明显长 | 进入的首屏子树、业务计算、Profile 覆盖 | 推迟不可见内容、移出重计算、补应用 Profile |
| TTID 高，Compose slice 很短 | Provider、DI、I/O、类加载、Splash、View traversal | 回到完整启动链，不改 UI 结构猜测 |
| composition 正常，measure/layout 长 | 文本、Lazy item、subcomposition、自定义 layout | 减少重复测量，检查约束与 0 尺寸 item |
| TTID 正常，TTFD 长 | 数据 ready、图片、错误/空态、report 条件 | 优化异步依赖并修正 fully drawn 定义 |
| 首帧后立即出现同结构重组 | layout 回写状态、effect 更新、窗口类别抖动 | 消除 phase feedback，缩小状态读取范围 |
| `Partial` 明显优于 `None`，发布包却无收益 | Profile 打包、安装和编译状态 | 检查 APK/AAB profile 产物与安装渠道 |
| View/Compose 混合页首帧变慢 | XML inflate、多个 host、`AndroidView` 创建 | 分段 trace 后按最大成本处理 |

## 10. 检查清单

- 是否把平台锚点限制在 Android 17 / API 37，并把 Compose 视为 AndroidX 库？
- 是否准确区分 `ComposeView`、内部 `AndroidComposeView`、`Composition` 与 `Recomposer`？
- 是否删除没有设备、构建、编译模式和样本分布的固定毫秒数或百分比？
- 是否明确初始 composition 只执行进入的分支与被请求的 Lazy 内容？
- 是否理解 `remember` 的 calculation 在初始 composition 仍要执行？
- 是否把 Baseline Profile 的 AOT 编译和 Startup Profile 的构建期 DEX 布局分开？
- 是否避免 `Class.forName()` 预热、后台自行驱动 composition 和无效的 `remember(LazyThreadSafetyMode.NONE)`？
- 是否按内容规模选择 `Column`/`Row` 或 Lazy layout，并避免 0 像素 item？
- 是否只在子内容依赖 constraints 时使用 subcomposition，并确认普通 `Box` 不属于这一路径？
- 是否用 release-like Macrobenchmark 同时记录 TTID/TTFD，并以 Perfetto 做阶段归因？
- 是否把内部 trace slice 名称视作版本相关实现细节？
- 是否在多窗口和混合页面中优先保证生命周期、状态与布局正确，再比较性能？

## 参考资料

- [AndroidX `ComponentActivity.setContent` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/activity/activity-compose/src/main/java/androidx/activity/compose/ComponentActivity.kt)
- [AndroidX `ComposeView` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/ComposeView.android.kt)
- [AndroidX `WindowRecomposer` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/WindowRecomposer.android.kt)
- [AndroidX `Recomposer` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Recomposer.kt)
- [AndroidX `remember` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composables.kt)
- [AndroidX `Box` 源码](https://android.googlesource.com/platform/frameworks/support/+/androidx-compose-release/compose/foundation/foundation-layout/src/commonMain/kotlin/androidx/compose/foundation/layout/Box.kt)
- [Compose phases](https://developer.android.com/develop/ui/compose/phases)
- [Compose performance](https://developer.android.com/develop/ui/compose/performance)
- [Compose Baseline Profile](https://developer.android.com/develop/ui/compose/performance/baseline-profiles)
- [Baseline Profiles overview](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Create Startup Profiles](https://developer.android.com/topic/performance/startupprofiles/dex-layout-optimizations)
- [Lazy lists and grids](https://developer.android.com/develop/ui/compose/lists)
- [Jetpack Glance](https://developer.android.com/develop/ui/compose/glance)
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [App startup time: TTID and TTFD](https://developer.android.com/topic/performance/vitals/launch-time)
- [§21.4 Baseline Profile 实战](./04-baseline-profile-practice.md)
- [§21.8 启动性能监控](./08-startup-monitoring.md)
- [§22.3 Compose 性能优化](../ch22-rendering-practice/03-compose-performance.md)
- [§22.13 View/Compose 混合迁移](../ch22-rendering-practice/13-compose-view-interop.md)
- [§22.16 Compose LazyList 性能](../ch22-rendering-practice/16-compose-lazylist-performance.md)
- [§18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)
