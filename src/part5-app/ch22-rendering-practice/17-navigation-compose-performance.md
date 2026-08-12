---
title: "Navigation Compose 性能优化"
chapter: "22.17"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [Jetpack, Compose, 性能优化, 导航]
related_chapters: ["22.13", "22.15", "24.4"]
last_verified: "2026-08-01"
confidence: medium
sources:
- type: official
  path: developer.android.com/develop/ui/compose/navigation
- type: official
  path: developer.android.com/develop/ui/compose/libraries#hilt-navigation
- type: official
  path: developer.android.com/develop/ui/compose/performance
- type: official
  path: developer.android.com/jetpack/androidx/releases/navigation#2.9.8
- type: official
  path: developer.android.com/guide/navigation/design/type-safety
- type: official
  path: developer.android.com/guide/navigation/backstack/multi-back-stacks
- type: official
  path: developer.android.com/jetpack/androidx/releases/hilt#1.4.0
- type: official
  path: developer.android.com/develop/ui/compose/performance/stability/diagnose
- type: official
  path: developer.android.com/develop/ui/compose/tooling/tracing
- type: official
  path: developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics
- type: official
  path: developer.android.com/topic/performance/jankstats
- type: official
  path: perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: dl.google.com — androidx.navigation:navigation-compose:2.9.8 sources
- type: official
  path: dl.google.com — androidx.navigation:navigation-runtime:2.9.8 sources
- type: official
  path: dl.google.com — androidx.navigation:navigation-common:2.9.8 sources
- type: official
  path: dl.google.com — androidx.hilt:hilt-lifecycle-viewmodel-compose:1.4.0 sources
- type: aosp
  path: AOSP android-17.0.0_r1 — frameworks/base, frameworks/native
- type: kernel
  path: AOSP kernel android17-6.18-2026-06_r6 — kernel/sched
task6_state: needs-review
task9_state: reviewed
pipeline_stage: rework-verified
last_deep_review_at: "2026-07-25T12:27:08+08:00"
last_deep_review_run_id: "20260725-122708-deep-review-8250c5dd"
last_rework_at: "2026-08-01T21:35:02+08:00"
last_rework_run_id: "20260801-213502-rework-8250c5dd"
---

# Navigation Compose 性能优化

## 1. 版本基线与边界

AndroidX 基线固定为 `androidx.navigation:navigation-compose:2.9.8`。该版本于 2026 年 4 月发布，并修复了 `NavHost` 在预测返回期间可能触发空指针异常的竞态。类型安全路由从 Navigation 2.8.0 起已经稳定，示例统一使用这套 API。[Navigation 2.9.8 发布说明](https://developer.android.com/jetpack/androidx/releases/navigation#2.9.8)

平台源码固定到 Android 17 / API 37 的 `android-17.0.0_r1`，内核源码固定到 `android17-6.18-2026-06_r6`。需要把三个版本域分开：

- Navigation Compose、Compose Runtime 和 Compose Compiler 随应用发布，Android platform tag 不能证明它们的行为。
- Android 17 提供输入、预测返回、`Choreographer`、HWUI、BLAST、SurfaceFlinger 与 HWC 等宿主能力。
- kernel tag 用于解释线程调度、uclamp、cpuset 和 cpufreq 观测，不能用来解释 `NavController` 返回栈规则。

Hilt 示例采用 AndroidX Hilt 1.4.0。从 Hilt 1.3.0 起，Compose 的 `hiltViewModel()` 已迁移到 `androidx.hilt:hilt-lifecycle-viewmodel-compose` 和 `androidx.hilt.lifecycle.viewmodel.compose` 包；旧包中的同名函数已经弃用并指向新包。1.4.0 的 Compose artifact 按 API 37 编译，构建项目需要 AGP 9.2.0 或更高版本。[Hilt 发布说明](https://developer.android.com/jetpack/androidx/releases/hilt#1.4.0)

所有固定收益数字都需要目标应用的基准测试。这里只说明源码可核对的生命周期、状态与渲染边界。

## 2. 一次导航跨过哪些阶段

`NavController.navigate()` 返回，只说明这次导航请求已经在控制器内处理。目标页面还要经历返回栈分发、Composition、Layout、Drawing、RenderThread 绘制、窗口 buffer 提交和显示合成，API 返回时间不能代表用户已经看到目标页。

以普通纯 Compose 页面为例，一次前进导航可以拆成下面几段：

1. 点击回调调用 `navigate()`，`NavController` 根据 route、`NavOptions` 和当前 graph 处理 `popUpTo`、状态恢复或新 entry。
2. `ComposeNavigator.pushWithTransition()` 把离开页和进入页加入 transition 集合，进入页的生命周期上限暂时停在 `STARTED`。
3. `NavHost` 收集 navigator back stack 与 `NavController.visibleEntries`，用 `SeekableTransitionState` 和 `AnimatedContent` 驱动内容切换。
4. 进入页完成 Composition、measure、placement 与 draw；离开页在转场结束前也可能保留组合并参与绘制。
5. `NavHost` 在动画稳定后调用 `onTransitionComplete()`，进入页才允许升到 `RESUMED`，已经弹出的离开页才允许进入 `DESTROYED`；未请求保存的 entry 随后可以清理 ViewModelStore。
6. 宿主窗口继续沿 `Choreographer → ViewRootImpl / Compose host → HWUI RenderThread → BLAST → SurfaceFlinger → HWC` 出图。

普通 `NavHost` 没有为每个 destination 建立独立 Surface。进入页和离开页的 Compose 内容写进同一个 App Window buffer；SurfaceFlinger 通常只看到宿主窗口 layer。完整显示路径见 [18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)，动画阶段见 [22.15 Compose 动画性能](15-compose-animation-performance.md)。

这条链把问题分成四类：

| 现象 | 优先检查 | 证据 |
|---|---|---|
| 点击后很久才开始切换 | 点击回调、route 编码、主线程阻塞、返回栈操作 | 业务 trace section、主线程 slice |
| 转场期间掉帧 | 两页同时组合/布局/绘制、动画属性、GPU 成本 | Compose tracing、FrameTimeline、GPU/RenderThread |
| 页面出现后仍不稳定 | 数据加载、图片解码、列表首次 measure、重复 effect | 页面状态时间点、Compose slice、网络/数据库 trace |
| 返回或切 Tab 后内存上升 | 保存的 back stack、ViewModel 作用域、`rememberSaveable` 内容 | heap、back stack dump、状态恢复测试 |

## 3. 路由只承载定位信息

Navigation 官方建议传递能定位数据的最小参数，再由目标页从数据源读取当前数据。大对象或 JSON 放进 route 会增加编码、字符串分配、参数解析与 saved state 压力，还可能在进程重建后得到过期副本。[Navigation Compose 文档](https://developer.android.com/develop/ui/compose/navigation)

Navigation 2.9.8 的类型安全 route 可以这样注册和读取：

```kotlin
@Serializable
data object HomeRoute

@Serializable
data class ProfileRoute(val userId: String)

NavHost(
    navController = navController,
    startDestination = HomeRoute
) {
    composable<HomeRoute> {
        HomeScreen(
            onOpenProfile = { userId ->
                navController.navigate(ProfileRoute(userId))
            }
        )
    }

    composable<ProfileRoute> { entry ->
        val route = entry.toRoute<ProfileRoute>()
        ProfileRouteContent(userId = route.userId)
    }
}
```

`ProfileRoute` 只携带不可变的 `userId`。注册端、调用端和读取端共享同一个 Kotlin 类型，能避开手写 path、query 参数和字符串解析之间的漂移。[类型安全路由文档](https://developer.android.com/guide/navigation/design/type-safety)

页面使用 ViewModel 时，可以直接从 `SavedStateHandle` 还原 route。这个构造函数让加载键跟随 entry 的已保存参数：

```kotlin
@HiltViewModel
class ProfileViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    repository: ProfileRepository
) : ViewModel() {
    private val route = savedStateHandle.toRoute<ProfileRoute>()

    val uiState: StateFlow<ProfileUiState> =
        repository.observeProfile(route.userId)
            .map { profile -> ProfileUiState.Content(profile) }
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5_000),
                initialValue = ProfileUiState.Loading
            )
}
```

`SavedStateHandle.toRoute<T>()` 负责还原导航参数，Repository 仍是业务数据来源。`SavedStateHandle` 适合 id、筛选项、步骤号等轻量恢复字段；Bitmap、大列表、数据库实体和开放文件句柄应留在缓存或数据层。

需要临时共享编辑草稿时，可选择父图 ViewModel。需要跨进程恢复时，应把必要字段写入 Room、DataStore 或其他持久化存储。route 不能替代业务存储。

## 4. 读取当前目的地时控制失效范围

Navigation Compose 2.9.8 的 `currentBackStackEntryAsState()` 实现只有一行：把 `currentBackStackEntryFlow` 通过 `collectAsState(null)` 转成 Compose `State`。每次 current entry 或其参数变化，读取这份 State 的重组作用域会失效。

“顶层读取一次”不会自动让整棵 UI 都执行昂贵重组。Compose 从 State 的读取位置安排重组，后续子节点还能依据参数稳定性被跳过。不过，把读取放在包含大量本地计算的宽作用域中，会让这段父级代码每次都重新执行。标题、底栏选中态和目标内容最好各自在最窄的使用位置读取或接收已经归一化的值。

`remember(currentRoute) { derivedStateOf { currentRoute.toTopLevelTab() } }` 不适合这里。`derivedStateOf` 的代码块没有读取任何 Compose State，无法减少上游 emission；route 到 tab 的映射又很便宜，直接计算即可。

底栏可以在自己的作用域收集当前 entry，再用 destination hierarchy 判断嵌套图归属：

```kotlin
private enum class TopLevelTab {
    HOME,
    SEARCH,
    ACCOUNT
}

private fun NavDestination?.belongsTo(tab: TopLevelTab): Boolean =
    this?.hierarchy?.any { destination ->
        when (tab) {
            TopLevelTab.HOME -> destination.hasRoute<HomeGraph>()
            TopLevelTab.SEARCH -> destination.hasRoute<SearchGraph>()
            TopLevelTab.ACCOUNT -> destination.hasRoute<AccountGraph>()
        }
    } == true

@Composable
private fun AppBottomBar(
    navController: NavHostController,
    onSelect: (TopLevelTab) -> Unit
) {
    val entry by navController.currentBackStackEntryAsState()
    val destination = entry?.destination

    NavigationBar {
        TopLevelTab.entries.forEach { tab ->
            NavigationBarItem(
                selected = destination.belongsTo(tab),
                onClick = { onSelect(tab) },
                icon = { TopLevelIcon(tab) },
                label = { Text(tab.name) }
            )
        }
    }
}
```

`hierarchy` 会沿当前 destination 向父 graph 遍历。详情页位于 `HomeGraph` 时，Home 仍保持选中；代码不依赖 route 字符串的内部编码。若底栏项很多且映射变重，可先测量，再把结果归一化成稳定枚举。

审计重组时要区分三种信号：

- State emission 表示读取方具备失效条件。
- Composable 被调用表示该 restart group 执行了。
- 子节点被跳过表示它没有负责对应的组合工作。

Layout Inspector 的 recomposition/skip 计数和 Compose compiler report 可以验证后两项。单看 `currentBackStackEntryFlow` 的 emission 次数无法估算帧成本。[Compose 稳定性诊断](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)

## 5. NavHost 转场期间有两份可见内容

Navigation Compose 2.9.8 的 `NavHost` 同时收集 `ComposeNavigator.backStack` 与 `NavController.visibleEntries`。`visibleEntries` 的公开契约按生命周期排序：

- 正在完成退出动画的 entry 可处于 `CREATED`，其中也可能包含已经从返回栈弹出的 entry。
- 正在进入或被浮动窗口部分覆盖的 entry 可处于 `STARTED`。
- 列表末尾是顶层 entry；只有进入动画完成后，它才可能到 `RESUMED`。

`AnimatedContent` 以 entry id 作为 content key。前进、返回或 `launchSingleTop` 触发转场时，离开页与进入页会暂时共存；二者的布局、绘制、effect 与状态观察都值得检查。转场结束后，普通栈下方页面通常已经离开组合，但对应 entry、ViewModelStore 或保存状态仍可能存活。组合存活、返回栈存活、ViewModel 存活是三个独立问题。

优化转场时应按成本来源处理：

- 离开页无需继续更新的动画、传感器或高频 Flow，应在生命周期降到 `STARTED` 后停止，或由业务显式暂停。
- 进入页先绘制轻量骨架，图片解码、数据库查询和大列表数据通过异步状态到达。
- `enterTransition`、`exitTransition` 和 `sizeTransform` 会影响 Composition、Layout 或 Drawing，属性动画不能统一视为同一种成本。
- 两页同时存在时，模糊、阴影、大面积 alpha、离屏图层和复杂 draw modifier 可能同时叠加 GPU 工作。

若页面嵌入 `SurfaceView`、`TextureView`、视频或 WebView，出图拓扑会发生分叉。“同一个 App Window buffer”只适用于普通 View/Compose/HWUI 主体。

## 6. 预测返回：手势进度会驱动可寻址转场

Android 14 到 Android 17 的系统返回手势由平台和 Activity back API 提供进度事件。Navigation Compose 2.9.8 在 Android 端把 `androidx.activity.compose.PredictiveBackHandler` 接入 `NavHost`：

1. 手势开始时，当前 entry 与前一个 entry 被标为 transition 中。
2. 手势更新时，`SeekableTransitionState.seekTo(progress, previousEntry)` 驱动返回动画。
3. 手势完成时，当前 entry 被弹出。
4. 手势取消时，转场从当前 fraction 动画回起点，再复位到当前 entry。

这段过程会让前一页提前参与组合和绘制。前一页恢复时若同步重建列表、重新发起请求或恢复昂贵资源，拖动过程就可能出现慢帧。2.9.8 已修复一处预测返回竞态，但应用仍需在 Android 14、15、16、17 的真机上覆盖完成、取消、快速反向与连续返回。

平台手势输入、Activity back dispatcher、Navigation 动画和 HWUI 出图属于不同层。某一层出现修复，不能推导其余层没有问题。预测返回的专项分析见 [22.11 预测返回性能](11-predictive-back-performance.md)。

## 7. 多返回栈：状态恢复会交换时间与内存

底部栏或导航抽屉常希望每个顶层入口保留自己的子栈。Navigation 提供 `saveState` 与 `restoreState` 支持：切走时保存被弹出目的地的 back stack state，切回时按 route 恢复；`launchSingleTop` 只在目标已经位于栈顶，或目标 graph 与预期 child hierarchy 精确匹配时避免增加同类栈顶副本。[多返回栈文档](https://developer.android.com/guide/navigation/backstack/multi-back-stacks)

官方文档中的顶层导航选项可以封装成这个扩展函数：

```kotlin
fun <T : Any> NavHostController.navigateTopLevel(route: T) {
    navigate(route) {
        popUpTo(graph.findStartDestination().id) {
            saveState = true
        }
        launchSingleTop = true
        restoreState = true
    }
}
```

`saveState = true` 会保存被弹出 entry 的参数与状态，并保留恢复所需的映射；相应 ViewModelStore 也可能继续占用内存，直到这份 back stack 被恢复、清除或控制器销毁。它不会保证页面 composition 一直留在内存，也不会自动替所有业务对象做持久化。

Tab 方案需要写清产品规则：

- 再次点当前 Tab，是停留在当前子页、回到该 Tab 根页，还是滚到列表顶部？
- 从 Tab A 的详情页切到 Tab B 后再回来，是恢复详情页，还是恢复 A 的起始页？
- 注销、账号切换或权限失效时，哪些已保存 back stack 必须清除？
- 每个 Tab 的 ViewModel、`rememberSaveable` 和缓存可占多少内存？

`launchSingleTop` 也不是通用点击防抖。目标不在栈顶时，连续事件仍可能新增 entry；参数变化还可能替换栈顶 entry。支付、提交、打开详情等事件应有业务级幂等控制或交互状态保护。

## 8. ViewModel 作用域跟随 entry

`NavHost` 通过 `LocalOwnersProvider` 把当前 `NavBackStackEntry` 同时提供为 `ViewModelStoreOwner`、`LifecycleOwner` 与 `SavedStateRegistryOwner`，再用 `SaveableStateHolder` 保存该 entry 的 Compose 可保存状态。因此，无参 `hiltViewModel()` 默认取得当前 destination 范围内的实例。

登录、下单或开户等多步骤流程适合用父 graph entry 共享 ViewModel。父 graph 共享写法把流程状态固定到 `CheckoutGraph`，并使用当前 child entry 作为 `remember` key：

```kotlin
@Serializable
data object CheckoutGraph

@Serializable
data object AddressRoute

navigation<CheckoutGraph>(
    startDestination = AddressRoute
) {
    composable<AddressRoute> { childEntry ->
        val parentEntry = remember(childEntry) {
            navController.getBackStackEntry<CheckoutGraph>()
        }
        val viewModel: CheckoutViewModel =
            hiltViewModel(viewModelStoreOwner = parentEntry)

        AddressScreen(viewModel)
    }
}
```

`remember(childEntry)` 会在 destination entry 被替换时重新查询仍在栈内的父 graph。只用 `remember(navController)` 可能在换图、恢复或重新进入流程后继续持有旧 parent entry。`getBackStackEntry<T>()` 要求目标 graph 当前仍在 back stack；应在该 graph 的 child destination 内调用。

父 graph 被无保存地弹出且转场完成后，对应 ViewModelStore 才能清理。使用 `saveState = true` 保留流程栈会延长相关状态寿命。把流程 ViewModel 提升到 Activity 级会进一步延长寿命，适用于全局会话状态，不适合只服务一次流程的大对象。

## 9. Lazy 列表：滚动和点击分开审计

列表滚动阶段关注 item key、`contentType`、参数稳定性、measure/prefetch 与图片工作；导航点击阶段关注事件重复、route 构造和目标页首帧。把两类采样混在一起，很难判断优化发生在哪一段。

列表 item 只在点击发生时创建轻量 route：

```kotlin
LazyColumn {
    items(
        items = users,
        key = { user -> user.id },
        contentType = { "user" }
    ) { user ->
        UserRow(
            user = user,
            onClick = {
                navController.navigate(ProfileRoute(user.id))
            }
        )
    }
}
```

稳定 key 用于保持业务对象身份，`contentType` 用于声明可复用兼容性；二者都不负责阻止重复导航。若 `UserRow` 在滚动时频繁执行，检查列表实例、item 参数、父级 State 读取与 callback 捕获。Lazy 布局细节见 [22.16 Compose Lazy 布局性能](16-compose-lazylist-performance.md)。

处理快速连点时，可在用例层只接受一次未完成操作，或在 UI 状态进入 `Navigating` 后暂时禁用按钮。基于 `currentDestination` 做简单判重只能覆盖一部分情况，因为返回栈分发、动画和业务事件可能处在不同时间点。

## 10. 深链：冷启动和页内导航要分开

深链可能同时包含 Activity 冷启动、Intent 分发、URI 匹配、认证、graph 构建、状态恢复、目标页查询和图片加载。只测 `navigate()` duration 会遗漏多数工作。

URI 到 route 的转换应保持纯粹和轻量：

- 校验 scheme、host、path 与允许的参数。
- 把外部字符串转换为应用内部的类型安全 route。
- 只保留资源 id、筛选项或 mode。
- 把认证和数据访问交给独立状态机与 Repository。
- 失败路径返回明确的安全页面，避免在组合期间反复重定向。

冷启动深链与已运行应用内的深链要使用两套场景。前者用 `StartupTimingMetric` 观察 `timeToInitialDisplayMs`，并在数据就绪后调用 `reportFullyDrawn()` 观察 `timeToFullDisplayMs`；后者用 `FrameTimingMetric` 覆盖导航和转场帧。[Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)

认证跳转还要检查循环：深链目标需要登录，登录完成后只消费一次 pending route；旋转、进程恢复或重复 Intent 不能多次压入同一目标。

## 11. 大屏、多 Pane 与可访问性

普通手机 `NavHost` 通常只有一个顶层可交互 destination。Navigation 2.9 允许自定义 Navigator 让 destination 实现 `SupportingPane`：同屏 pane 可以与相邻 destination 共享 `RESUMED` 状态；`FloatingWindow` 下方的可见页面通常保持 `STARTED`。因此，不能把“永远只有一个 RESUMED entry”写成通用规则。

大屏布局同时显示列表与详情时，需要检查：

- 两个 pane 是否重复收集同一份高频 Flow。
- 窗口尺寸变化是否触发 graph 重建或重复导航。
- 列表选择是否可以更新详情状态，避免每次选择都重建整套导航层。
- 折叠到单 pane 后，返回路径和选中项能否一致恢复。
- 预测返回期间两 pane 的动画与焦点是否同步。

TalkBack、键盘和旋钮导航会增加焦点与语义状态恢复要求。减少无意义语义嵌套可以降低遍历成本，但不能删除控件角色、状态说明或可操作名称。状态恢复后应验证焦点落在当前可见 destination，避免焦点仍指向退出页。

## 12. 用数据定位导航慢帧

一套可复用的测量用例表应覆盖下面的场景：

| 场景 | 启动模式 | 操作 | 主要指标 |
|---|---|---|---|
| 首页到详情 | WARM | 单次点击、等待转场稳定 | `FrameTimingMetric`、Composition/Layout/Draw |
| 详情返回 | WARM | 返回完成与取消各一组 | `FrameTimingMetric`、预测返回 progress、两页工作 |
| Tab 切换 | WARM | 首次进入、恢复旧栈、重复点当前 Tab | 帧时间、back stack 数量、内存 |
| 冷启动深链 | COLD | Intent 直达目标 | `StartupTimingMetric`、TTID、TTFD |
| 运行中深链 | WARM | 接收新 Intent | 路由解析、认证、帧时间 |
| 进程重建 | COLD | 恢复保存状态 | 恢复正确性、TTFD、重复请求 |
| 大屏双 Pane | WARM | 选择、缩放窗口、返回 | 两 pane 重组、生命周期、焦点 |

工具各自回答不同问题：

- **Macrobenchmark `FrameTimingMetric`**：比较导航、返回和 Tab 切换期间的帧分布。使用 release/profileable 构建，并固定编译模式、设备状态、刷新率与测试数据。
- **Macrobenchmark `StartupTimingMetric`**：测冷启动深链的初显与 fully drawn；它不适合替代运行中页面切换测量。
- **Perfetto FrameTimeline**：对齐 App SurfaceFrame 和 DisplayFrame，识别 missed deadline、late present、GPU composition 或 buffer stuffing。它描述宿主窗口帧，route 归属要靠应用事件补充。[FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)
- **Composition tracing**：查看目标页哪些 Composable 在转场窗口内执行，配合 `runtime-tracing` 与 system trace 使用。[Compose tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- **Layout Inspector 与 compiler report**：检查重组/跳过次数和参数稳定性；Debug 计数适合定位，不用于发布性能结论。
- **JankStats**：用 `PerformanceMetricsState` 给帧附加当前 route、交互类型和转场阶段，线上聚合慢帧时保留页面上下文。[JankStats 文档](https://developer.android.com/topic/performance/jankstats)
- **TestNavHostController**：验证 route、参数、`popUpTo` 和返回栈正确性；它不执行真实窗口出图，不能证明导航帧性能。

建议在 trace 中记录 `NavRequest(route)`、`DestinationChanged(route)`、`ContentReady(route)` 三个业务时间点。它们分别表示请求发出、控制器完成目的地分发、页面得到可展示状态；帧完成还要继续对齐 FrameTimeline。这样可以分辨控制器处理、页面数据和显示提交各自占用的时间。

## 13. Android 17 显示与内核锚点

Navigation 请求最终仍要落到一帧。Android 17 的普通 Compose 页面沿下面的固定源码入口核查：

- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java) 与 [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：VSync callback、Traversal 和窗口绘制入口。
- [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp) 与 [`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：UI 到 RenderThread 同步、draw 与 buffer swap。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)、[SurfaceFlinger FrontEnd](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/) 与 [`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)：窗口 buffer transaction、snapshot/latch、composition strategy 与 present。

如果慢帧证据落在 runnable delay、CPU 迁移或频率响应，再核对固定 kernel tag：

- [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c) 与 [`kernel/cgroup/cpuset.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/cgroup/cpuset.c)：调度、uclamp 与 cpuset 约束。
- [`kernel/sched/cpufreq_schedutil.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)：调度利用率进入 schedutil 的路径。

Vendor Power HAL、thermal policy、私有 governor 和设备刷新率策略不在 GKI 文件里。AOSP/GKI 说明可观察机制，目标设备 trace 才能说明某次导航为何迟到。

## 14. 检查清单

提交导航相关改动前，逐项核查：

- 依赖锁定到已记录的 Navigation、Compose、Kotlin 和 Hilt 版本。
- route 使用类型安全 API，只携带 id、枚举或轻量筛选条件。
- `currentBackStackEntryAsState()` 位于需要导航状态的窄作用域。
- route 到 UI model 的便宜映射没有套用无效的 `derivedStateOf`。
- 顶层选中态按 destination hierarchy 判断，可覆盖嵌套详情页。
- 转场期间允许进入页和离开页共存，二者都没有同步重工作。
- 预测返回覆盖完成、取消、快速反向和连续返回。
- `launchSingleTop` 的使用范围明确，重复业务事件另有幂等保护。
- `saveState` / `restoreState` 的交互规则与内存代价经过测试。
- ViewModel owner 与 destination 或父 graph 一致，父 entry 查询随 child entry 更新。
- 冷启动深链和运行中深链分开测量。
- 普通 Compose、SurfaceView、TextureView、视频和 WebView 使用各自的出图模型。
- TestNavHostController 只负责正确性测试，性能结论来自真实窗口和真机。
- Macrobenchmark、Perfetto、Composition tracing 与线上 route 标签可以互相对齐。

## 15. 固定来源

| 范围 | 来源 | 使用点 |
|---|---|---|
| Navigation 版本 | [Navigation 2.9.8 release notes](https://developer.android.com/jetpack/androidx/releases/navigation#2.9.8) | 稳定版本、预测返回竞态修复 |
| 类型安全 route | [Type safety in Kotlin DSL and Navigation Compose](https://developer.android.com/guide/navigation/design/type-safety) | `composable<T>()`、`toRoute<T>()`、`SavedStateHandle.toRoute<T>()` |
| 多返回栈 | [Support multiple back stacks](https://developer.android.com/guide/navigation/backstack/multi-back-stacks) | `saveState`、`restoreState`、`launchSingleTop` |
| Hilt Compose | [Hilt 1.4.0 release notes](https://developer.android.com/jetpack/androidx/releases/hilt#1.4.0)、[`hilt-lifecycle-viewmodel-compose:1.4.0` sources](https://dl.google.com/dl/android/maven2/androidx/hilt/hilt-lifecycle-viewmodel-compose/1.4.0/hilt-lifecycle-viewmodel-compose-1.4.0-sources.jar) | 新 artifact、包名、ViewModel owner |
| Navigation Compose 源码 | [`navigation-compose:2.9.8` sources](https://dl.google.com/dl/android/maven2/androidx/navigation/navigation-compose/2.9.8/navigation-compose-2.9.8-sources.jar) | `NavHost`、`currentBackStackEntryAsState()`、`LocalOwnersProvider` |
| Navigation Runtime 源码 | [`navigation-runtime:2.9.8` sources](https://dl.google.com/dl/android/maven2/androidx/navigation/navigation-runtime/2.9.8/navigation-runtime-2.9.8-sources.jar) | `visibleEntries`、entry lifecycle、状态保存与恢复 |
| Navigation Common 源码 | [`navigation-common:2.9.8` sources](https://dl.google.com/dl/android/maven2/androidx/navigation/navigation-common/2.9.8/navigation-common-2.9.8-sources.jar) | `NavigatorState` transition 契约 |
| 帧测量 | [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)、[Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline) | TTID/TTFD、帧时间、显示截止时间 |
| Compose 诊断 | [Compose tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)、[Stability diagnosis](https://developer.android.com/develop/ui/compose/performance/stability/diagnose) | Composition slice、重组与跳过 |

Navigation 2.9.8 的 exact source JAR 是 AndroidX 行为的主要依据；Android 17 与 kernel 固定 tag 只负责宿主帧和调度边界。升级任一版本后，应重新核对 `NavHost`、entry lifecycle、状态恢复和预测返回实现。
