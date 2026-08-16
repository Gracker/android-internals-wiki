---
title: "Navigation Compose 2.x 性能优化"
chapter: "22.17"
status: finalized
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
tags: [Jetpack, Compose, 性能优化, 导航]
related_chapters: ["22.13", "22.15", "24.4"]
last_verified: "2026-08-15"
last_verified_against: "Navigation 2.9.8 / Navigation 3 1.1.6 / AndroidX Hilt 1.4.0 源码 JAR；Android 17 android-17.0.0_r1"
confidence: high
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
  path: developer.android.com/jetpack/androidx/releases/navigation3#1.1.6
- type: official
  path: developer.android.com/guide/navigation/navigation-3
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
  path: developer.android.com/reference/androidx/benchmark/macro/StartupMode
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
task6_state: reviewed
task9_state: reviewed
pipeline_stage: rework-verified
last_deep_review_at: "2026-07-25T12:27:08+08:00"
last_deep_review_run_id: "20260725-122708-deep-review-8250c5dd"
last_rework_at: "2026-08-01T21:35:02+08:00"
last_rework_run_id: "20260801-213502-rework-8250c5dd"
---

# Navigation Compose 2.x 性能优化

本文只分析 Navigation 2.x 的 Compose API，也就是由 `NavController`、`NavHost` 和 `NavBackStackEntry` 组成的导航方案。`NavBackStackEntry` 表示返回栈里的一次目的地实例，本文简称 entry；同一个目的地连续入栈，会产生多个 entry。Navigation 3 已有稳定版 1.1.6，它改由应用持有返回栈、`NavDisplay` 根据栈内容显示页面，两套库的状态与生命周期实现不同，本文结论不能直接套到 Navigation 3。[Navigation 3 发布说明](https://developer.android.com/jetpack/androidx/releases/navigation3#1.1.6)

导航性能不能只看 `navigate()` 的执行时间。目标页何时开始组合、转场期间保留几份内容、状态保存多久，以及哪一帧送到显示设备，都会影响用户感受到的速度。本文沿 Navigation 2.9.8 的返回栈、转场和状态恢复实现说明这些边界，并给出可复现的测量方法。

## 1. 版本基线与边界

本文的 Navigation 2.x 基线固定为 `androidx.navigation:navigation-compose:2.9.8`。截至 2026 年 8 月 15 日，它仍是 2.x 稳定版；该版本于 2026 年 4 月 22 日发布，并修复了 `NavHost` 在预测返回期间可能触发空指针异常的竞态。这里的“竞态”指多个异步状态变化的先后顺序不定，某种次序恰好触发错误。类型安全路由从 Navigation 2.8.0 起已经稳定，示例统一使用这套 API。[Navigation 2.9.8 发布说明](https://developer.android.com/jetpack/androidx/releases/navigation#2.9.8)

Navigation 2 已进入维护模式，仍会收到关键修复。新的纯 Compose 项目可以同时评估 Navigation 3；迁移会把 `NavController`/`NavHost` 换成应用持有的返回栈与 `NavDisplay`，不能只替换依赖版本。[Navigation 3 指南](https://developer.android.com/guide/navigation/navigation-3)

平台源码固定到 Android 17 / API 37 的 `android-17.0.0_r1`，内核源码固定到 `android17-6.18-2026-06_r6`。需要把三个版本域分开：

- Navigation Compose、Compose 运行时和 Compose 编译器随应用发布，Android 平台源码标签不能证明它们的行为。
- Android 17 提供系统输入、预测返回、负责调度帧回调的 `Choreographer`、HWUI、连接窗口缓冲区与 Surface 事务的 BLAST、系统合成器 `SurfaceFlinger`，以及硬件合成器（Hardware Composer，HWC）等宿主能力。
- 内核源码标签用于解释 CPU 调度和调频观测，不能用来解释 `NavController` 的返回栈规则。

Hilt 示例采用 AndroidX Hilt 1.4.0。从 Hilt 1.3.0 起，Compose 的 `hiltViewModel()` 已迁移到 `androidx.hilt:hilt-lifecycle-viewmodel-compose` 依赖和 `androidx.hilt.lifecycle.viewmodel.compose` 包；旧包中的同名函数已经弃用并指向新包。`hilt-lifecycle-viewmodel-compose:1.4.0` 使用 `compileSdk 37`，引用它的模块至少需要 AGP 9.2.0；Hilt 1.4.0 还要求 Kotlin Gradle Plugin（KGP）不低于 2.2.0。[Hilt 发布说明](https://developer.android.com/jetpack/androidx/releases/hilt#1.4.0)

源码只能说明生命周期、状态与渲染边界，无法给出固定的性能收益。耗时和内存差异都要在目标应用上做基准测试。

## 2. 一次导航跨过哪些阶段

`NavController.navigate()` 返回，只说明控制器已经处理这次导航请求。目标页面还要经历返回栈分发、组合（Composition）、布局（Layout）、绘制（Draw）、`RenderThread` 执行绘制命令、窗口图形缓冲区提交和显示合成，API 返回时间不能代表用户已经看到目标页。

以普通纯 Compose 页面为例，一次前进导航可以拆成下面几段：

1. 点击回调调用 `navigate()`，`NavController` 根据路由（route）、`NavOptions` 和当前导航图（graph）处理 `popUpTo`、状态恢复或新 entry。
2. `ComposeNavigator.pushWithTransition()` 把离开页和进入页加入正在转场的 entry 集合，进入页的生命周期上限暂时停在 `STARTED`。
3. `NavHost` 收集 `ComposeNavigator.backStack` 与 `NavController.visibleEntries`，用 `SeekableTransitionState` 和 `AnimatedContent` 驱动内容切换。
4. 进入页完成组合、测量、放置与绘制；离开页在转场结束前也可能保留组合并参与绘制。
5. `NavHost` 在动画稳定后调用 `onTransitionComplete()`，进入页才允许升到 `RESUMED`，已经弹出的离开页才允许进入 `DESTROYED`；未请求保存的 entry 随后可以清理 `ViewModelStore`。
6. 宿主窗口继续沿 `Choreographer → ViewRootImpl / Compose 宿主 → HWUI RenderThread → BLAST → SurfaceFlinger → HWC` 生成并合成画面。

`Surface` 是系统管理图形缓冲区队列和合成图层的对象，并不对应某个 Composable。普通 `NavHost` 不会为每个目的地建立独立 `Surface`：进入页和离开页的 Compose 内容写进同一个应用窗口缓冲区，`SurfaceFlinger` 通常只看到宿主窗口这一层。完整显示路径见 [18.23 Compose 渲染管线](../../part2-performance/ch18-rendering-pipelines/23-compose-rendering-pipeline.md)，动画阶段见 [22.15 Compose 动画性能](15-compose-animation-performance.md)。

这条链把问题分成四类：

| 现象 | 优先检查 | 证据 |
|---|---|---|
| 点击后很久才开始切换 | 点击回调、route 编码、主线程阻塞、返回栈操作 | 应用自定义跟踪区间（trace section）、主线程时间片（slice） |
| 转场期间掉帧 | 两页同时组合/布局/绘制、动画属性、GPU 成本 | Compose 组合跟踪、帧时间线（FrameTimeline）、GPU/RenderThread 区间 |
| 页面出现后仍不稳定 | 数据加载、图片解码、列表首次测量、重复执行的副作用 | 页面状态时间点、Compose 跟踪时间片、网络/数据库 trace |
| 返回或切换标签页（Tab）后内存上升 | 保存的返回栈、ViewModel 作用域、`rememberSaveable` 内容 | 堆内存快照、返回栈记录、状态恢复测试 |

先按现象选择证据，再判断时间消耗发生在控制器、页面工作还是显示阶段；只记录 `navigate()` 时长无法覆盖后三类问题。

## 3. 路由只承载定位信息

Navigation 官方建议只传递能定位数据的最小参数，再由目标页从数据源读取当前数据。大对象或 JSON 放进 route 会增加编码、字符串分配、参数解析与已保存状态的体积，还可能在进程重建后得到过期副本。[Navigation Compose 文档](https://developer.android.com/develop/ui/compose/navigation)

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

`ProfileRoute` 只携带不可变的 `userId`。注册端、调用端和读取端共享同一个 Kotlin 类型，可以避免手写路径（path）、查询参数（query）与字符串解析规则逐渐不一致。[类型安全路由文档](https://developer.android.com/guide/navigation/design/type-safety)

页面使用 ViewModel 时，可以直接从 `SavedStateHandle` 还原 route。下面的 ViewModel 在创建时读取 entry 参数，数据查询键也能随已保存参数恢复：

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

`SavedStateHandle.toRoute<T>()` 负责还原导航参数，Repository（仓库层，用于统一访问数据库、网络等数据源）仍是业务数据来源。`SavedStateHandle` 适合 id、筛选项、步骤号等轻量恢复字段；Bitmap、大列表、数据库实体和打开的文件句柄应留在缓存或数据层。

需要临时共享编辑草稿时，可选择父图 ViewModel。需要跨进程恢复时，应把必要字段写入 Room、DataStore 或其他持久化存储。route 只负责导航定位，不能替代业务存储。

## 4. 读取当前目的地时控制失效范围

Navigation Compose 2.9.8 的 `currentBackStackEntryAsState()` 实现只有一行：把 `currentBackStackEntryFlow` 通过 `collectAsState(null)` 转成 Compose `State`。当前 entry 或其参数变化时，读取这份 `State` 的重组作用域会被标记为需要重新检查。

“顶层读取一次”不会自动让整棵 UI 都执行昂贵重组。Compose 从 `State` 的读取位置安排重组，后续子节点还能依据参数稳定性被跳过。不过，把读取放在包含大量本地计算的宽作用域中，会让这段父级代码每次都重新执行。标题、底栏选中态和目标内容最好各自在最窄的使用位置读取或接收已经归一化的值。

`remember(currentRoute) { derivedStateOf { currentRoute.toTopLevelTab() } }` 不适合这里。`derivedStateOf` 只有在读取 Compose `State`，且派生结果比输入更少变化时，才可能减少读取方的无效执行。这里的代码块没有读取 Compose `State`，无法减少上游发值次数；route 到 Tab 的映射也很轻，直接计算即可。

底栏可以在自己的作用域收集当前 entry，再用目的地层级（destination hierarchy）判断嵌套图归属：

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

`hierarchy` 从当前目的地开始，逐级检查它所属的父导航图。详情页位于 `HomeGraph` 时，Home 仍保持选中；代码不依赖 route 字符串的内部编码。若底栏项很多，映射又包含较多分支或查询，可先测量，再把结果归一化成稳定枚举。

检查重组时要区分三种信号：

- `State` 发出新值（emission），只说明读取它的重组作用域会被标记为待检查。
- Composable 被调用，表示对应的可重新启动组（restart group，即编译器划出的独立重组单元）执行了。
- 子节点被跳过，表示 Compose 判断其输入未变，没有执行该节点的组合代码。

Layout Inspector 的重组/跳过计数和 Compose 编译器报告可以验证后两项。单看 `currentBackStackEntryFlow` 的发值次数无法估算帧成本。[Compose 稳定性诊断](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)

## 5. NavHost 转场期间有两份可见内容

Navigation Compose 2.9.8 的 `NavHost` 同时收集 `ComposeNavigator.backStack` 与 `NavController.visibleEntries`。`visibleEntries` 的公开契约按生命周期排序：

- 正在完成退出动画的 entry 可处于 `CREATED`，其中也可能包含已经从返回栈弹出的 entry。
- 正在进入或被浮动窗口部分覆盖的 entry 可处于 `STARTED`。
- 列表末尾是顶层 entry；只有进入动画完成后，它才可能到 `RESUMED`。

这些状态还是上限：宿主 Activity 或 Fragment 没到 `RESUMED` 时，任何 entry 都不能升到 `RESUMED`。

`AnimatedContent` 以 entry id 作为内容键（content key），用它区分转场前后的页面实例。前进、返回或 `launchSingleTop` 触发转场时，离开页与进入页会暂时共存；二者的布局、绘制、副作用与状态观察都值得检查。转场结束后，普通返回栈中被遮住的页面通常已经离开组合，但对应 entry、`ViewModelStore` 或已保存状态仍可能存活。组合、返回栈和 ViewModel 的寿命要分别判断。

优化转场时应按成本来源处理：

- 离开页无需继续更新的动画、传感器或高频 `Flow` 数据流，应以 `RESUMED` 为运行条件，或由业务显式暂停。转场期间离开页仍可能处于 `STARTED`，只按 `STARTED` 收集不会停下来。
- 进入页先绘制轻量骨架，图片解码、数据库查询和大列表数据通过异步状态到达。
- `enterTransition`、`exitTransition` 和 `sizeTransform` 会影响组合、布局或绘制，属性动画不能统一视为同一种成本。
- 两页同时存在时，模糊、阴影、大面积透明度、离屏图层和复杂绘制修饰符（draw modifier）可能同时增加 GPU 工作。

若页面嵌入 `SurfaceView`、`TextureView`、视频或 `WebView`，这些组件可能使用独立 `Surface` 或缓冲区路径，画面生成过程会出现分支。“同一个应用窗口缓冲区”只适用于普通 View/Compose/HWUI 主体。

## 6. 预测返回：手势进度直接控制转场

Android 14 到 Android 17 的系统返回手势由平台和 Activity 返回事件 API 提供进度。Navigation Compose 2.9.8 在 Android 端把 `androidx.activity.compose.PredictiveBackHandler` 接入 `NavHost`：

1. 手势开始时，当前 entry 与前一个 entry 被加入正在转场的集合。
2. 手势更新时，`SeekableTransitionState.seekTo(progress, previousEntry)` 驱动返回动画。
3. 手势完成时，当前 entry 被弹出。
4. 手势取消时，返回事件的 `Flow` 被取消；`NavHost` 退出预测返回模式，把当前动画进度（fraction）逐步降到 0，再复位到当前 entry。

这段过程会让前一页提前参与组合和绘制。前一页恢复时若同步重建列表、重新发起请求或恢复昂贵资源，拖动过程就可能出现慢帧。2.9.8 已修复一处预测返回竞态，但应用仍需在 Android 14、15、16、17 的真机上覆盖完成、取消、快速反向与连续返回。

平台手势输入、Activity 返回事件分发器（back dispatcher）、Navigation 动画和 HWUI 画面生成属于不同层。某一层出现修复，不能推导其余层没有问题。预测返回的专项分析见 [22.11 预测返回性能](11-predictive-back-performance.md)。

## 7. 多返回栈：恢复位置会延长状态寿命

底部栏或导航抽屉常希望每个顶层入口保留自己的子栈。Navigation 提供 `saveState` 与 `restoreState`：切走时保存被弹出目的地的返回栈状态，切回时按 route 恢复。`launchSingleTop` 只有两种情况能避免新增栈层级：普通目的地已经在栈顶，或目标导航图在当前栈中的子层级与预期层级完全一致。[多返回栈文档](https://developer.android.com/guide/navigation/backstack/multi-back-stacks)

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

`saveState = true` 会保存被弹出 entry 的参数与可保存状态，并保留恢复所需的映射；这些 entry 已创建的 `ViewModelStore` 也会继续占用内存，直到返回栈被恢复后再次正常弹出、通过 `clearBackStack()` 清除，或控制器销毁。页面组合不会因此一直留在内存，业务对象也不会自动持久化。进程被杀后，内存中的 ViewModel 不会恢复，只有能写入 `SavedState` 的数据可以随控制器状态重建。

多标签页（Tab）方案需要写清产品规则：

- 再次点当前 Tab，是停留在当前子页、回到该 Tab 根页，还是滚到列表顶部？
- 从 Tab A 的详情页切到 Tab B 后再回来，是恢复详情页，还是恢复 A 的起始页？
- 注销、账号切换或权限失效时，哪些已保存返回栈必须清除？
- 每个 Tab 的 ViewModel、`rememberSaveable` 和缓存可占多少内存？

`launchSingleTop` 不能替代点击防抖。目标不在栈顶时，连续事件仍可能新增 entry；命中 `launchSingleTop` 条件时，Navigation 也会用新参数重建相应的 entry 对象，因此页面仍可能更新。支付、提交、打开详情等事件应有业务级幂等控制，也就是同一请求重复到达时只允许生效一次；还可以在交互进行中暂时禁用入口。

## 8. ViewModel 作用域跟随 entry

`NavHost` 通过 `LocalOwnersProvider` 把当前 `NavBackStackEntry` 同时提供为三种状态所有者（owner）：`ViewModelStoreOwner` 决定 ViewModel 存在哪个 `ViewModelStore`，`LifecycleOwner` 提供生命周期，`SavedStateRegistryOwner` 管理可写入 `SavedState` 的字段。`SaveableStateHolder` 则按 entry 保存 `rememberSaveable` 状态。因此，无参 `hiltViewModel()` 默认取得当前目的地范围内的实例。

登录、下单或开户等多步骤流程适合用父导航图的 entry 共享 ViewModel。下面的写法把流程状态固定到 `CheckoutGraph`，并使用当前子 entry 作为 `remember` 的键：

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

`remember(childEntry)` 会在目的地 entry 被替换时，重新查询仍在返回栈内的父导航图。只用 `remember(navController)`，可能在换图、恢复或重新进入流程后继续持有旧的父 entry。`getBackStackEntry<T>()` 要求目标导航图仍在返回栈中，因此应在该图的子目的地内调用。

父导航图以 `saveState = false` 弹出且转场完成后，对应 `ViewModelStore` 才能清理。使用 `saveState = true` 保留流程栈会延长相关状态寿命。把流程 ViewModel 提升到 Activity 级会进一步延长寿命，适用于全局会话状态，不适合只服务一次流程的大对象。

## 9. Lazy 列表：分别检查滚动和点击

列表滚动阶段关注列表项的 key、`contentType`、参数稳定性、测量、预取与图片工作；导航点击阶段关注事件重复、route 构造和目标页首帧。把两类采样混在一起，很难判断耗时来自哪一段。

列表项只在点击发生时创建轻量 route：

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

稳定 key 用于保持业务对象身份，`contentType` 用于声明哪些列表项可以复用同类组合；二者都不负责阻止重复导航。若 `UserRow` 在滚动时频繁执行，检查列表实例、列表项参数、父级 `State` 读取，以及回调是否捕获了频繁变化的值。Lazy 布局细节见 [22.16 Compose Lazy 布局性能](16-compose-lazylist-performance.md)。

处理快速连点时，可在业务层只接受一次未完成操作，或在 UI 状态进入 `Navigating` 后暂时禁用按钮。基于 `currentDestination` 做简单判重只能覆盖一部分情况，因为返回栈分发、动画和业务事件可能处在不同时间点。

## 10. 深链：冷启动和页内导航要分开

深链可能同时包含 Activity 冷启动、Intent 分发、URI 匹配、认证、导航图构建、状态恢复、目标页查询和图片加载。只测 `navigate()` 时长会遗漏多数工作。

URI 到 route 的转换应保持纯粹和轻量：

- 校验 URI 的协议（scheme）、主机名（host）、路径（path）与允许的参数。
- 把外部字符串转换为应用内部的类型安全 route。
- 只保留资源 id、筛选项或模式。
- 把认证和数据访问交给独立状态机与 Repository。
- 失败路径返回明确的安全页面，避免在组合期间反复重定向。

冷启动深链与已运行应用内的深链要使用两套场景。前者用 `StartupTimingMetric` 观察 `timeToInitialDisplayMs`（TTID，从启动请求到目标页首帧）和 `timeToFullDisplayMs`（TTFD，从启动请求到完整内容就绪后的首帧）。Compose 页面应在内容就绪条件满足时使用 `ReportDrawnWhen` 或 `ReportDrawnAfter` 发出完整绘制（fully drawn）信号，不要直接调用 Activity 的 `reportFullyDrawn()`。后者用 `FrameTimingMetric` 覆盖导航和转场帧。[Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)

认证跳转还要检查循环：深链目标需要登录时，登录完成后只处理一次待导航 route；旋转、进程恢复或重复 Intent 不能多次压入同一目标。

## 11. 大屏、多窗格与可访问性

普通手机的 `NavHost` 通常只有一个顶层可交互目的地。Navigation 2.9 允许自定义 Navigator 让目的地实现 `SupportingPane`；这个标记表示当前目的地与前一个目的地并排显示，并共享生命周期，因此同屏窗格（pane）可以同时处于 `RESUMED`。`FloatingWindow` 表示覆盖在其他内容之上的浮动窗口目的地，被它覆盖但仍可见的页面通常保持 `STARTED`。所以，“永远只有一个 `RESUMED` entry”只适用于不含这些特殊目的地的普通栈。

大屏布局同时显示列表与详情时，需要检查：

- 两个窗格是否重复收集同一份高频 `Flow` 数据流。
- 窗口尺寸变化是否触发导航图重建或重复导航。
- 列表选择是否可以更新详情状态，避免每次选择都重建整套导航层。
- 折叠到单窗格后，返回路径和选中项能否一致恢复。
- 预测返回期间两个窗格的动画与焦点是否同步。

TalkBack、键盘和旋钮导航会增加焦点与语义状态恢复要求。减少无意义语义嵌套可以降低遍历成本，但不能删除控件角色、状态说明或可操作名称。状态恢复后应验证焦点落在当前可见目的地，避免焦点仍指向退出页。

## 12. 用数据定位导航慢帧

一套可复用的测量用例表应覆盖下面的场景：

页内导航不是启动测试。测量这类操作时，`startupMode` 应留空，并在 `setupBlock` 中把应用带到起点；`COLD` 只用于需要完整创建进程的冷启动。`WARM` 的定义是“进程已存在，但重新创建 Activity”，不能用它泛指应用已经运行。进程死亡恢复还要专门构造可恢复任务与已保存状态，不能只设置 `COLD`。[StartupMode API](https://developer.android.com/reference/androidx/benchmark/macro/StartupMode)

| 场景 | 准备状态 | 操作 | 主要指标 |
|---|---|---|---|
| 首页到详情 | 应用已运行 | 单次点击、等待转场稳定 | `FrameTimingMetric`、组合/布局/绘制 |
| 详情返回 | 应用已运行 | 返回完成与取消各一组 | `FrameTimingMetric`、预测返回进度、两页工作 |
| Tab 切换 | 应用已运行 | 首次进入、恢复旧栈、重复点当前 Tab | 帧时间、返回栈数量、内存 |
| 冷启动深链 | COLD | Intent 直达目标 | `StartupTimingMetric`、TTID、TTFD |
| 运行中深链 | 应用已运行 | 接收新 Intent | 路由解析、认证、帧时间 |
| 进程死亡恢复 | 专用恢复场景 | 重建任务并恢复状态 | 恢复正确性、TTFD、重复请求 |
| 大屏双窗格 | 应用已运行 | 选择、缩放窗口、返回 | 两个窗格的重组、生命周期、焦点 |

这张表先固定场景边界，再为每类问题选择指标；不同场景的 TTID、帧分布或内存值不能直接混成一个“导航耗时”。

工具各自回答不同问题：

- **Macrobenchmark `FrameTimingMetric`**：比较导航、返回和 Tab 切换期间的帧分布。使用经过发布优化且允许性能采集的 `release`/`profileable` 构建，并固定编译模式、设备状态、刷新率与测试数据。
- **Macrobenchmark `StartupTimingMetric`**：测冷启动深链的初显与完整绘制；它不适合替代运行中页面切换测量。
- **Perfetto FrameTimeline**：把应用窗口帧（App `SurfaceFrame`）与最终显示帧（`DisplayFrame`）按时间对应起来，识别错过截止时间、延迟呈现、GPU 合成或缓冲区堆积（buffer stuffing）。它描述宿主窗口帧，route 归属要靠应用事件补充。[FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)
- **组合跟踪（Composition tracing）**：查看目标页哪些 Composable 在转场窗口内执行，配合 `runtime-tracing` 与系统跟踪使用。[Compose tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- **Layout Inspector 与编译器报告**：检查重组/跳过次数和参数稳定性；Debug 构建的计数适合定位，不用于发布性能结论。
- **JankStats**：用 `PerformanceMetricsState` 给帧附加当前 route、交互类型和转场阶段，线上聚合慢帧时保留页面上下文。[JankStats 文档](https://developer.android.com/topic/performance/jankstats)
- **TestNavHostController**：验证 route、参数、`popUpTo` 和返回栈正确性；它不执行真实窗口出图，不能证明导航帧性能。

可以在跟踪数据中添加三个自定义事件：`NavRequest(route)` 表示请求发出，`DestinationChanged(route)` 表示控制器完成目的地分发，`ContentReady(route)` 表示页面得到可展示状态。这些名称是应用自行约定的标记，不是 Navigation 自动生成的事件；画面何时显示还要继续与 FrameTimeline 对应。三者能把控制器处理、页面数据与显示提交的时间分开。

## 13. Android 17 显示与内核源码入口

Navigation 请求最终仍要生成并显示一帧。Android 17 的普通 Compose 页面可以沿这些固定源码入口核查：

- [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java) 与 [`ViewRootImpl.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)：垂直同步（VSync）回调、一次视图树测量/布局/绘制调度（Traversal）和窗口绘制入口。
- [`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp) 与 [`CanvasContext.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/CanvasContext.cpp)：界面线程与 `RenderThread` 同步、绘制和图形缓冲区交换。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)、[SurfaceFlinger FrontEnd](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/FrontEnd/) 与 [`HWComposer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)：窗口缓冲区事务、快照与锁存、合成策略和最终呈现。

如果跟踪数据表明线程已处于可运行态却迟迟没获得 CPU，或出现频繁 CPU 迁移、频率响应过慢，再核对固定的内核源码标签：

- [`kernel/sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c) 与 [`kernel/cgroup/cpuset.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/cgroup/cpuset.c)：调度、`uclamp`（限制任务利用率估计的上下界）与 `cpuset`（限制任务可运行的 CPU 集合）。
- [`kernel/sched/cpufreq_schedutil.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)：调度器利用率进入 `schedutil` 调频策略的路径。

厂商电源 HAL（Vendor Power HAL）、温控策略、私有调频策略和设备刷新率规则不在 GKI（Generic Kernel Image，通用内核映像）文件里。AOSP/GKI 只能说明可观察机制，目标设备的跟踪数据才能说明某次导航为何迟到。

## 14. 检查清单

提交导航相关改动前，逐项核查：

- 依赖锁定到已记录的 Navigation、Compose、Kotlin 和 Hilt 版本。
- route 使用类型安全 API，只携带 id、枚举或轻量筛选条件。
- `currentBackStackEntryAsState()` 位于需要导航状态的窄作用域。
- route 到界面模型的轻量映射没有套用无效的 `derivedStateOf`。
- 顶层选中态按目的地层级判断，可覆盖嵌套详情页。
- 转场期间允许进入页和离开页共存，二者都没有在主线程同步执行耗时工作。
- 预测返回覆盖完成、取消、快速反向和连续返回。
- `launchSingleTop` 的使用范围明确，重复业务事件另有幂等保护。
- `saveState` / `restoreState` 的交互规则与内存代价经过测试。
- ViewModel 的状态所有者与当前目的地或父导航图一致，父 entry 查询随子 entry 更新。
- 冷启动深链和运行中深链分开测量。
- 普通 Compose、`SurfaceView`、`TextureView`、视频和 `WebView` 使用各自的画面生成模型。
- TestNavHostController 只负责正确性测试，性能结论来自真实窗口和真机。
- Macrobenchmark、Perfetto、组合跟踪与线上 route 标签可以按时间互相对应。

## 15. 固定来源

| 范围 | 来源 | 使用点 |
|---|---|---|
| Navigation 版本 | [Navigation 2.9.8 release notes](https://developer.android.com/jetpack/androidx/releases/navigation#2.9.8) | 稳定版本、预测返回竞态修复 |
| Navigation 3 边界 | [Navigation 3 1.1.6 release notes](https://developer.android.com/jetpack/androidx/releases/navigation3#1.1.6) | 当前稳定版本、与 Navigation 2 分界 |
| 类型安全 route | [Type safety in Kotlin DSL and Navigation Compose](https://developer.android.com/guide/navigation/design/type-safety) | `composable<T>()`、`toRoute<T>()`、`SavedStateHandle.toRoute<T>()` |
| 多返回栈 | [Support multiple back stacks](https://developer.android.com/guide/navigation/backstack/multi-back-stacks) | `saveState`、`restoreState`、`launchSingleTop` |
| Hilt Compose | [Hilt 1.4.0 release notes](https://developer.android.com/jetpack/androidx/releases/hilt#1.4.0)、[`hilt-lifecycle-viewmodel-compose:1.4.0` sources](https://dl.google.com/dl/android/maven2/androidx/hilt/hilt-lifecycle-viewmodel-compose/1.4.0/hilt-lifecycle-viewmodel-compose-1.4.0-sources.jar) | 新依赖、包名、ViewModel 状态所有者 |
| Navigation Compose 源码 | [`navigation-compose:2.9.8` sources](https://dl.google.com/dl/android/maven2/androidx/navigation/navigation-compose/2.9.8/navigation-compose-2.9.8-sources.jar) | `NavHost`、`currentBackStackEntryAsState()`、`LocalOwnersProvider` |
| Navigation 运行时源码 | [`navigation-runtime:2.9.8` sources](https://dl.google.com/dl/android/maven2/androidx/navigation/navigation-runtime/2.9.8/navigation-runtime-2.9.8-sources.jar) | `visibleEntries`、entry 生命周期、状态保存与恢复 |
| Navigation Common 源码 | [`navigation-common:2.9.8` sources](https://dl.google.com/dl/android/maven2/androidx/navigation/navigation-common/2.9.8/navigation-common-2.9.8-sources.jar) | `NavigatorState` 转场契约 |
| 帧测量 | [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)、[StartupMode API](https://developer.android.com/reference/androidx/benchmark/macro/StartupMode)、[Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline) | TTID/TTFD、完整绘制信号、启动条件、帧时间、显示截止时间 |
| Compose 诊断 | [Compose tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)、[Stability diagnosis](https://developer.android.com/develop/ui/compose/performance/stability/diagnose) | 组合跟踪时间片、重组与跳过 |

本文对 Navigation 2 行为的判断以 2.9.8 源码 JAR 为准；Android 17 与固定内核源码标签只用于说明宿主帧和调度边界。升级 Navigation 2 后，应重新核对 `NavHost`、entry 生命周期、状态恢复和预测返回实现；迁移到 Navigation 3 时，则要按 `NavDisplay` 和应用自有返回栈重新分析。
