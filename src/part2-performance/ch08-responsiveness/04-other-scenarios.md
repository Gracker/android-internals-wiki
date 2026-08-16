---
title: "其他响应速度场景"
chapter: "8.4"
section: "8.4"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-06"
last_verified_against: "AOSP android-16.0.0_r1 Activity/InputDispatcher/View/ViewRootImpl + AndroidX ViewPager2 1.1.0 / Fragment 1.8.9 sources + Android 17 Beta config-change docs"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/app/Activity.java"
  - type: aosp
    path: "androidx/fragment/fragment/src/main/java/androidx/fragment/app/FragmentTransaction.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: blog
    path: "https://developer.android.com/guide/fragments"
  - type: blog
    path: "https://developer.android.com/reference/androidx/viewpager2/widget/ViewPager2"
  - type: official
    path: "https://developer.android.com/blog/posts/the-first-beta-of-android-17"
tags: ['responsiveness', 'page-switch', 'click-response', 'search', 'viewpager2', 'fragment', 'debounce']
related_chapters: ["8.1", "8.2", "8.3", "3.1", "3.2", "7.4"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: fixed
---
# 8.4 其他响应速度场景

## 把“响应快”定义成可测量的终点

应用完成启动后，用户仍会不断触发页面跳转、Tab 切换、点击和搜索。每个场景都要同时记录起点和终点；只测量回调执行时间，无法说明反馈画面何时出现，也无法说明业务数据何时可用。

各场景采用下面的测量边界：

| 场景 | 起点 | 第一个终点 | 业务终点 |
| --- | --- | --- | --- |
| Activity / Fragment 跳转 | 触发导航的输入事件 | 目标页提交第一帧 | 目标内容可交互 |
| Tab 切换 | 点击 Tab 或滑动手势 | 新页稳定呈现 | 新页主要数据可用 |
| 普通点击 | 输入事件进入应用 | pressed、Ripple 或状态变化呈现 | 点击动作完成或进入可恢复状态 |
| 实时搜索 | 归一化后的查询发生变化 | Loading / 空结果状态呈现 | 当前查询的结果呈现 |
| Deep Link / Widget | 外部宿主发起 Intent 或 PendingIntent | 目标页第一帧 | 链接内容可交互 |

起点同样需要明确。`ACTION_DOWN`、`ACTION_UP`、`onClick()` 和导航调用分别发生在不同时间点；搜索文字变化、debounce 等待结束和请求发出也属于不同阶段。Perfetto 适合关联 Input、主线程、Binder、FrameTimeline 和自定义 trace，Macrobenchmark 适合重复执行固定交互。

本文以 Android 17 / API 37 的 `android-17.0.0_r1` 为平台源码基线。输入驱动、线程调度、CPU frequency 和 I/O 分析以内核 `android17-6.18-2026-06_r6` 为准。任何固定毫秒数的收益都必须附带设备、刷新率和业务入口条件。

## 页面跳转：Activity 与 Fragment 要分开看

### Android 17 的 Activity 跳转路径

即使在同一个应用内调用 `startActivity()`，请求仍会经过 `system_server`。Android 17 的主要步骤如下：

1. `Activity.startActivityForResult()` 调用 `Instrumentation.execStartActivity()`。
2. 客户端通过 `IActivityTaskManager.startActivity()` 发起 Binder 请求。
3. ATMS / `ActivityStarter` 解析 Intent、权限、Task、launch mode（启动模式）和窗口状态。
4. 目标进程不存在时，系统先请求 Zygote 创建并绑定进程。
5. 目标进程已经存在时，系统通过 `ClientTransaction` 发送 `LaunchActivityItem`、`ResumeActivityItem` 等生命周期事务项。
6. 应用主线程创建 Activity，执行生命周期、构建窗口和 UI，并提交目标页首帧。

Android 9（API 28）引入了 `ClientTransaction` 体系；Android 8.x 的旧路径使用 `scheduleLaunchActivity()`。这项版本差异可以解释旧 trace 中的方法名，Android 17 的结论仍以 `android-17.0.0_r1` 为准。

“打开 Activity”至少有三种成本形态：

| 状态 | 可能出现的工作 |
| --- | --- |
| 目标 Activity 尚未创建，应用进程存活 | ATMS 调度、Activity 实例与窗口、生命周期、UI 和首帧 |
| 目标 Activity 已在 Task 中 | Task / launchMode 决策、`onNewIntent()` 或生命周期恢复、必要重绘 |
| 目标进程不存在 | 额外包含进程创建、`Application`、Provider 和首 Activity；接近冷启动 |

因此，无法给 Binder、Activity 构造、inflate 或首帧分配一套通用时间。进程是否存活、目标页资源、转场、系统负载和编译状态都会改变结果。

### 从输入到目标帧拆开测

页面跳转延迟可能发生在以下五个区间：

- 输入已经到应用，但主线程迟迟没有进入点击回调；
- 导航调用到 `system_server` 接收之间存在主线程或 Binder 等待；
- ATMS 解析、Task 操作或进程启动耗时；
- 目标 Activity / Fragment 的创建、数据读取和 UI 构建耗时；
- 目标内容已准备，但 measure、layout、draw、RenderThread 或合成错过帧截止时间。

下面的 AndroidX trace 只标记 `navigate()` 调用本身，便于在 Perfetto 中定位业务发起导航的时间：

```kotlin
trace("Navigation.OpenDetail") {
    navController.navigate(
        DetailRoute(itemId = item.id)
    )
}
```

这个 slice 会在 `navigate()` 返回时结束，并不表示目标页已经显示。验收时还要结合目标窗口的 FrameTimeline、目标页的阶段标记和内容就绪事件。trace 名称应保持低基数，也就是只使用少量稳定名称；业务 ID 应通过受控参数或单独事件记录。

转场动画需要单独测量。动画播放期间可以同时创建页面；流畅动画能遮住部分准备时间，掉帧动画则会让延迟感更明显。不能用动画时长代替页面准备耗时，也不应为了缩短一个数字而删除有助于理解页面空间关系的过渡。

### Android 17 的配置变更边界

Android 17 默认不再因以下变化重建 Activity：

- keyboard、keyboardHidden、navigation、touchscreen、colorMode；
- `uiMode` 只在进入或离开 `UI_MODE_TYPE_DESK` 时变化的情况。

运行中的 Activity 会收到 `onConfigurationChanged()`。如果应用依赖销毁重建来重新读取资源，需要在 Manifest 的 `android:recreateOnConfigChanges` 中声明对应标志。`android-17.0.0_r1` 的 Manifest 属性说明还规定：同一个标志同时写入 `configChanges` 和 `recreateOnConfigChanges` 时，Activity 不会重建。

这项变化可以减少某些显示器、输入设备和桌面模式切换时的状态丢失，但资源刷新也因此由仍然存活的 Activity 负责。测试应覆盖主题、drawable、尺寸、导航状态和输入设备切换；只统计生命周期调用次数，会漏掉资源没有更新的问题。

### FragmentTransaction 是主线程异步队列

`FragmentTransaction.commit()` 会把事务加入主线程队列，不会在调用点同步完成。`setReorderingAllowed(true)` 允许 FragmentManager 合并同一批事务中的中间状态，官方建议每个事务都启用。`replace()` 的效果接近在同一容器中先 remove 再 add；事务加入 back stack（返回栈）后，旧 Fragment 实例和它的 View 生命周期会分别转换状态，返回时可能重新创建 View。

Fragment 切换的常见成本包括：

- pending transaction（待处理事务）在主线程队列中等待执行；
- Fragment 实例与依赖创建；
- `onCreateView()` / ComposeView 首次组合；
- FragmentStateManager 状态推进；
- `SpecialEffectsController` 管理的动画或 transition（转场）；
- RecyclerView、图片和数据在同一帧集中更新；
- 返回栈恢复时重新创建 View。

AndroidX Fragment 没有保证为每个生命周期或事务自动生成稳定的 Perfetto slice。应用应在导航入口、目标页 UI 构建和数据提交处加入 trace 标记，再结合 `inflate`、RecyclerView、FrameTimeline 和线程状态分析。

`commitNow()` 会立即在当前主线程执行事务，而且不能与 `addToBackStack()` 同用。它只适合调用方必须立刻读取事务结果的少数情况；为追求“更快”而使用它，会把创建、生命周期和布局工作同步放进当前消息。FragmentManager 已保存状态后，普通 commit 还会抛出异常；`commitAllowingStateLoss()` 也不能用作性能优化手段。

### Fragment 页面怎样减少等待

- 使用接收 Fragment class 的事务 API，让 `FragmentFactory` 参与正常创建和状态恢复；
- 将依赖注入放在 Factory 或 DI 容器中，把路由参数放在 arguments / Navigation route 中，构造过程不访问磁盘和网络；
- 目标页尽快提交稳定骨架或缓存内容，把次要区域放到首帧后；
- View 销毁后取消与 `viewLifecycleOwner` 绑定的图片、列表和动画工作；
- `postponeEnterTransition()` 只等待 shared element（共享元素）等转场必需内容，并同时设置 `postponeEnterTransition(timeout, unit)`；
- 成功、失败、取消和超时路径都要调用或触发 `startPostponedEnterTransition()`；
- 返回栈频繁重建 View 时，应区分数据复用和 View 复用，不能通过长期保留大型 View 树来换取速度。

Activity 和 Fragment 的选择应由导航、模块边界、状态恢复和窗口需求决定。二者都会在应用主线程创建 UI，Fragment 也可能因为复杂布局和同步工作产生长帧。

## Tab 切换：ViewPager2 的保留范围与生命周期

### `offscreenPageLimit` 是内存与重建成本的交换

ViewPager2 内部使用 RecyclerView。默认值 `OFFSCREEN_PAGE_LIMIT_DEFAULT (-1)` 沿用 RecyclerView 的缓存策略，不保证固定保留多少个相邻页面。手动设置时，值必须大于等于 1；传入 0 会抛出 `IllegalArgumentException`。

设置为 `N` 后，当前页两侧各 N 页会被创建并保留在 View 层级中；范围外的页面会从 View 层级移除，再按照 adapter / RecyclerView 规则在需要时重建或复用。增大这个值可能减少往返滑动时的 inflate 和 layout，也会增加 View、图片、Compose composition 和数据订阅所占用的内存与资源。

可以按照以下方式对候选值进行对照测试：

1. 用默认 `-1` 建立切换帧与内存基线；
2. 只测试业务能够长期承担内存开销的较小值；
3. 覆盖快速往返、跨多页、旋转、后台恢复和低内存；
4. 同时看 FrameTimeline、创建次数、PSS、GC 和数据请求；
5. 根据页面复杂度与设备层级决定，不按 Tab 总数套用固定值。

ViewPager2 的公开 API 不允许替换内部 `LayoutManager`。可调整的范围主要包括页面保留数量、页面构建开销、adapter 稳定 ID、数据预取和生命周期管理。

### FragmentStateAdapter 的可见生命周期

`FragmentStateAdapter` 通过 `setMaxLifecycle()` 限制各页面的最高生命周期状态：选中页达到 `RESUMED`，其他已添加页面通常停在 `STARTED`。旧 ViewPager 的 `setUserVisibleHint()` 已废弃，旧 adapter 的 `BEHAVIOR_RESUME_ONLY_CURRENT_FRAGMENT` 也不属于 ViewPager2 API。

数据加载可以分为两件事：

- View 在 `STARTED` 时收集并渲染可见或即将可见的数据；
- Fragment 进入 `RESUMED` 时触发幂等的 `ensureLoaded()`，只启动尚未完成的业务加载。

下面的示例把加载状态交给 ViewModel，并让 UI 状态收集在 View 离开 `STARTED` 后自动停止：

```kotlin
override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
    viewLifecycleOwner.lifecycleScope.launch {
        viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
            viewModel.uiState.collectLatest(::render)
        }
    }
}

override fun onResume() {
    super.onResume()
    viewModel.ensureLoaded()
}
```

`ensureLoaded()` 需要区分 Loading、Success、可重试 Error 和强制刷新，不能只依赖 Fragment 中的一个布尔成员。ViewModel 可以在同一 Fragment 重建 View 时保留状态；进程死亡后的恢复仍需要 SavedState 或持久化数据源。

不要把页面可见性与数据加载直接绑定到 `onViewCreated()`：相邻页面可能提前创建，从而让所有 Tab 的请求同时发生在当前交互期间。也不要在每次 `onResume()` 时无条件刷新，否则往返滑动会触发重复网络请求和列表更新。

### 邻页预取要有预算

`OnPageChangeCallback.onPageSelected()` 可以作为邻页数据预取的触发点，但它只提供当前选中位置，并不能直接说明用户下一步会滑向哪一页。预取策略需要结合前一个位置、页面顺序、网络类型、缓存新鲜度，以及用户是否已经停止滚动。

预取结果需要：

- 与页面 key、账号和筛选条件绑定；
- 有容量和 TTL（存活时间）限制；
- 页面远离、查询变化或宿主销毁时可取消；
- 失败时不覆盖正常加载的错误处理；
- 避免和页面自己的首次请求重复；
- 在低内存或受限网络下可以关闭。

滑动动画期间应优先保证主线程和 RenderThread 获得资源。大量 JSON 解析、图片解码、DiffUtil 提交或 Compose 状态更新即使发生在 worker 中，也可能在提交结果时集中进入同一批帧。

### adapter 数据变化也会制造抖动

`FragmentStateAdapter` 默认将 item ID 与 position 绑定。动态增删或重排页面时，应按照文档实现稳定的 `getItemId()` 和 `containsItem()`，让同一业务页面在位置变化后仍保持身份；否则 Fragment 状态恢复和创建次数可能偏离业务预期。更新时应使用 `notifyItem*` 或可靠的差分通知，不要每次刷新都重建整个 ViewPager2 adapter。

## 点击响应：反馈帧比 onClick 返回更接近用户感受

### Android 17 的输入与 View 路径

触摸事件从设备到目标 View，大致经过以下步骤：

1. 内核 evdev（Linux 输入事件接口）上报触摸数据；
2. InputReader 读取数据、统一坐标和状态，并生成 `MotionEvent`；
3. InputDispatcher 根据窗口、触摸焦点和策略选择目标；
4. InputChannel 将带序号的事件送到应用，应用处理后回传完成状态；
5. `ViewRootImpl.WindowInputEventReceiver` 把事件交给应用主线程输入阶段；
6. DecorView / ViewGroup 执行 `dispatchTouchEvent()`、拦截和命中测试；
7. 目标 View 维护 pressed、长按和手势状态；
8. 合法点击在 `ACTION_UP` 后通过 `performClick()` 调用 listener（监听器）；
9. 下一次遍历、渲染与合成把反馈像素呈现到屏幕。

平台步骤以 `android-17.0.0_r1` 中的 InputDispatcher、InputTransport、ViewRootImpl 和 View 为依据；驱动调度和 CPU 运行状态以内核 `android17-6.18-2026-06_r6` 为依据。每个阶段的时长都会受到触控采样、队列、刷新率和系统负载影响，不能套用固定区间。

`MotionEvent.getEventTime()` 和 `SystemClock.uptimeMillis()` 可以在应用内粗略比较事件采样时间和回调开始时间。`Choreographer.postFrameCallback()` 只表示帧回调发生，不能直接代表面板呈现时间；精确分析 input-to-display（输入到显示）延迟时，应使用 Perfetto 的 Input 关联、FrameTimeline 和显示轨迹。

### pressed 与 Ripple 也依赖主线程和帧

Android 17 的 `View.onTouchEvent()` 会在普通可点击 View 收到 `ACTION_DOWN` 时设置 pressed 状态。View 位于可滚动容器中时，Framework 会先进入 prepressed（预按下）状态，并等待一个 tap timeout（点击判定时限），避免用户其实想滚动时过早显示点击反馈。`ACTION_UP` 路径会 post `PerformClick`，让 pressed 状态有机会先进入一帧绘制。

Ripple 根据 drawable state 绘制点击波纹。如果主线程被长消息、同步 Binder、锁或停顿阻塞，即使 pressed 状态已经写入，也可能错过下一帧。Ripple 同样要经过主线程和渲染路径，无法独立显示。

一次点击可以有两个视觉终点：

- 输入确认：pressed、Ripple、选中态或按钮禁用已经呈现；
- 动作结果：导航页、保存成功、错误提示或可重试状态已经呈现。

页面应尽早显示操作已被接收，再让长任务在受控作用域中执行。在回调中同步查询数据库、调用 `SharedPreferences.commit()`、执行文件 I/O 或图片解码、等待锁或同步 Binder，都会推迟反馈帧。把函数标为 `suspend` 不会自动切换线程，仍应遵守数据源 API 的线程约定。

### 自定义 View 保留系统点击语义

自定义手势识别如果直接调用业务函数，会绕过 `OnClickListener`、点击音效和无障碍 `ACTION_CLICK`。识别出合法单击后应调用 `performClick()`，覆盖 `performClick()` 时也要调用父实现。拖动、滑出边界、长按、多指、pressed 清理和 `ACTION_CANCEL` 都需要由完整状态机或 `GestureDetector` 处理；若在每次 `ACTION_UP` 时都无条件调用业务函数，滚动和已取消的手势也可能被识别成点击。

能够使用标准 `Button`、可点击 View 或 Compose `clickable` 时，应保留组件自带的语义、触摸目标、键盘操作和无障碍支持。自定义 View 还要让触摸、键盘和无障碍动作进入同一个业务入口，避免三种输入方式维护各自不同的状态。

### 重复点击要按业务状态处理

只设置固定点击间隔，可能会拦截快速但合法的操作，也无法阻止已经发往服务端的两个请求。更可靠的方案包括：

- 提交期间把按钮状态切为 Loading，并决定是否允许取消；
- 为创建、支付等操作使用业务幂等键，让服务端识别并拒绝同一次操作的重复提交；
- 导航前检查当前 destination 与生命周期状态；
- 列表操作按 item ID 隔离，避免全页面禁用；
- 失败后恢复按钮并给出明确重试入口；
- 仍需时间门限时使用单调时钟 `SystemClock.elapsedRealtime()`，并覆盖键盘与无障碍点击。

## 实时搜索：把等待、执行和过期结果分开

### 搜索管线有四段延迟

一次“边输入边搜索”通常包含四个阶段：

1. IME / TextField 把查询写入状态；
2. 归一化、debounce（等待输入短暂停顿）和重复值过滤；
3. 本地索引、数据库或网络执行；
4. 结果 Diff、列表布局和结果帧呈现。

debounce 会主动增加一段等待，用来减少用户仍在输入时发出的查询。它不属于后端执行耗时，也不应隐藏在一个不分阶段的“搜索总耗时”数字中。等待期间可以显示 Loading，或先清空已经过期的旧结果。

### Flow 管线要处理空查询与取消

下面的 ViewModel 管线会让空查询立即清空结果，为非空查询使用可配置的 debounce，并在新查询到来时停止收集旧查询：

```kotlin
@OptIn(FlowPreview::class, ExperimentalCoroutinesApi::class)
val searchState: StateFlow<SearchUiState> = query
    .map { it.trim() }
    .debounce { value ->
        if (value.isEmpty()) 0L else searchDebounceMs
    }
    .distinctUntilChanged()
    .flatMapLatest { value ->
        if (value.isEmpty()) {
            flowOf(SearchUiState.Empty)
        } else {
            repository.observeSearch(value)
        }
    }
    .stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(),
        initialValue = SearchUiState.Empty
    )
```

`distinctUntilChanged()` 只去掉相邻的相同值。序列 `foo → bar → foo` 仍会再次搜索 foo，这通常符合用户重新选择查询的预期。如果需要缓存，应在 repository 中按照规范化 query、账号、筛选条件和数据版本建立 key。

`flatMapLatest` 会取消旧 Flow 的收集，但底层 Room、网络客户端或自定义数据源还需要支持协作式取消；服务器已经收到的请求仍可能继续执行。每个结果都应携带 query 或 generation（查询代次编号），UI 只接受当前 generation，避免无法取消的旧回调覆盖新结果。

`searchDebounceMs` 没有适用于所有应用的固定值。内存索引可能完全不需要 debounce，远程补全则要结合打字节奏、请求成本和服务端限流选择。应根据输入到反馈的延迟、请求数、取消率、结果呈现分布和用户完成率调整参数。

### 本地索引与缓存不能挤进按键帧

- Room / SQLite 查询应使用索引，并限制返回列和首批结果数量；
- 拼音、首字母或全文索引在数据变化时增量更新，不在每次按键时全量转换；
- 大列表 Diff 可以在 worker 中计算，但提交阶段仍要观察主线程和布局开销；
- 内存缓存设置容量，持久缓存设置数据版本与过期规则；
- 热门查询预取受网络、账号、隐私和存储预算约束；
- 页面退出或查询变化时取消预取和图片工作；
- 错误、离线和空结果属于不同 UI 状态，不能让旧列表继续显示成新查询的结果。

搜索结果呈现时，键盘、焦点和无障碍播报也会影响响应。大量结果一次性触发布局和 accessibility event，可能出现网络请求很快、界面更新却仍然迟缓的情况。

## Deep Link：路由正确性属于响应时间

Android 使用 Intent filter 路由 Deep Link（外部链接进入应用的路径）。从 Android 12（API 31）开始，普通 HTTP(S) 链接如果没有通过域名验证，通常会交给默认浏览器；自有域名应使用 verified App Links（已验证应用链接），避免出现 chooser（应用选择器）或先进入浏览器再返回应用。

Deep Link 入口可能命中存活进程，也可能触发完整冷启动。优化时要覆盖：

- URI 解析和安全校验应限制输入长度，并且只执行内存中的快速操作；
- 直接创建能展示目标内容的宿主，减少只负责转发的 Activity；
- 缺少登录认证时保存规范化后的 route，在登录后恢复，不要重复解析不可信 URI；
- 目标内容未到时先展示合法占位、缓存或错误状态；
- Intent 通过 `onCreate()` 与 `onNewIntent()` 进入时采用同一条幂等路由；
- App Link 验证失败、无网络、非法参数和不存在内容都有稳定退路；
- Back / Up 栈符合外部进入时的导航预期。

下面的命令发起一次 Deep Link 启动，并通过 `-W` 等待 Activity 启动结果：

```bash
adb shell am start \
  -W \
  -a android.intent.action.VIEW \
  -d 'https://www.example.com/items/42' \
  com.example.app
```

`-W` 输出适合快速回归，但无法分别统计路由、页面创建和结果渲染耗时。正式实验应对同一个 URI 分别测量冷、温状态，并用 Macrobenchmark / Perfetto 关联目标页 TTID、TTFD 和 FrameTimeline。

## Widget 点击：从宿主进程进入应用

App Widget 的 View 实际显示在 Launcher 等宿主进程中，界面由应用提供的 `RemoteViews` 跨进程描述。点击通常触发应用预先创建的 `PendingIntent`，因此会经过宿主、系统和目标组件；应用进程不存在时还会包含一次冷启动。

用于打开页面的 Widget 点击，应尽量使用直接指向目标 Activity 的 `PendingIntent.getActivity()`。从 Android 12 开始，Launcher 可以为这种直接启动提供专用转场；如果先进入 `BroadcastReceiver` 或 Service，再通过 trampoline 跳转到 Activity，就无法使用这套动画。

下面的代码为每个 Widget 实例创建身份不同且不可变的页面 `PendingIntent`：

```kotlin
val intent = Intent(context, DetailActivity::class.java)
    .setData("example://widget/$widgetId".toUri())
    .putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId)

val pendingIntent = PendingIntent.getActivity(
    context,
    widgetId,
    intent,
    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
)

remoteViews.setOnClickPendingIntent(R.id.widget_root, pendingIntent)
```

`requestCode` 和 Intent data 都参与 `PendingIntent` 身份判断，因而可以避免多个 Widget 实例错误复用旧路由。只有系统或宿主必须补充 Intent 内容的 API 才使用 mutable（可变）模式；直接打开 Activity 的简单点击应保持 immutable（不可变）。Widget 顶层背景使用 `@android:id/background`，可以让 Android 12 及以上版本的 Launcher 识别转场背景。

切换开关或执行轻量命令时，可以把 `PendingIntent` 指向 Receiver。`onReceive()` 应尽快返回：先更新可见状态，再把可延迟工作交给受约束的后台机制，不能让长时间网络请求一直占用 Receiver。还要分别测试应用进程存活、进程不存在、设备锁定、Widget 多实例，以及目标页面已经位于 Task 中的情况。

## 用 Perfetto 和基准把场景关联起来

### Trace 中关注四条证据

1. **Input**：事件何时进入系统、何时送到应用，以及应用何时完成处理。
2. **Main thread / Binder**：回调前排队、同步调用、锁、I/O、类加载和生命周期。
3. **FrameTimeline**：哪个 intended frame（原计划承载反馈的帧）包含这次更新，是否迟交，以及延迟来自 App 还是 SurfaceFlinger。
4. **Business state**：页面、Tab、点击动作或搜索结果何时达到定义的可用状态。

自定义 slice 应使用稳定名称，例如 `Navigation.Detail`、`Tab.Select`、`Search.Query`。使用 `androidx.tracing.trace` 或 try / finally，确保发生异常时也能结束 section。不要把 URI、query、用户 ID 或 item ID 直接拼进 slice 名，以免大量不同取值形成高基数数据，并把敏感信息写入 trace。

Macrobenchmark 可以通过 UIAutomator 重复执行点击、滑动和输入，并配合 `FrameTimingMetric`、自定义 trace 和目标状态等待。每个用例都要固定入口、数据、动画、编译状态和设备。点击后只调用 `waitForIdle()` 可能过早或过晚，应等待明确的页面节点或业务完成标记。

### 响应回归看分布与失败

页面切换和搜索都可能因为缓存是否命中而形成双峰分布，也就是快速和慢速样本各聚成一组。报告至少应按冷 / 温数据、入口、设备、Android 版本和网络条件分组，并同时记录：

- 输入到首个反馈帧；
- 输入到业务内容；
- 慢帧与冻结帧比例；
- 请求数、取消率、缓存命中率；
- 超时、空态、错误和降级比例；
- 样本量以及 P50、P90 / P95。

平均值无法描述少量但很慢的长尾样本。阈值应来自产品场景和设备基线；RAIL 可以作为 Web 交互的参考，不能当成所有 Android 设备的硬门槛。

## Android 17 与内核边界

Android 17 会为 targetSdk 37 及以上的应用启用 lock-free（无锁）`MessageQueue`。它可能减少消息生产者和 Looper 之间的锁竞争，也会让通过反射读取 `mMessages` 或调用私有方法的旧监控失效。页面切换和点击监控应使用公开 trace、FrameTimeline 和测试 API；队列实现发生变化后，仍需进行应用侧对照测量。

Android 17 还引入了 generational Concurrent Mark-Compact GC，也就是按对象代际管理、并以并发标记和压缩方式回收内存的 GC；它还可能通过 ART Mainline 更新覆盖部分较早系统。这会改变停顿和 CPU 时间分布。看到点击或切换附近出现 GC slice 时，应检查对象分配速率、堆状态和 collector 事件，不能仅根据平台版本推断固定收益。

只有在出现线程长时间处于 runnable（可运行但未获得 CPU）、频繁被抢占、CPU frequency 不足、input driver 延迟或 I/O wait 时，才需要进入 `android17-6.18-2026-06_r6` 分析调度和驱动。Activity、View、InputDispatcher、MessageQueue 和配置变更仍应依据 `android-17.0.0_r1` 的平台源码。

## 场景审计清单

### 页面与 Tab

- 记录输入、导航调用、目标首帧和内容可用四个时间点。
- 区分目标进程、Activity 和 Fragment 是否已经存在。
- 检查目标 UI 创建、同步数据、转场和结果提交。
- Fragment 事务启用 reordering，并避免只为追求速度而使用 `commitNow()`。
- 对 ViewPager2 默认缓存和候选 offscreen limit 进行帧与内存对照。
- 数据加载幂等、可取消，并与 View 生命周期分离。
- 覆盖返回栈、配置变化、进程重建和动态 Tab。

### 点击与搜索

- 检查事件到 callback 的主线程排队。
- 确认 pressed / Ripple 或业务状态能在回调快速返回后完成绘制。
- 自定义 View 通过 `performClick()` 保留无障碍语义。
- 用业务状态和幂等保护重复提交。
- 搜索把 debounce、执行、结果渲染分别计时。
- 空查询立即清理，旧查询可取消或带 generation 防覆盖。
- 索引、Diff、图片和 accessibility 更新都纳入结果帧分析。

### 外部入口

- Deep Link 同时测试冷启动、温启动、`onNewIntent()` 和非法参数。
- 自有域名检查 App Link 验证和 Android 12+ 路由。
- Widget 直达 Activity，避免 Broadcast / Service trampoline。
- 测试 PendingIntent 身份、mutability（可变性）、多实例和返回栈。
- 外部入口同样定义 TTID 与内容可用终点。

## 小结

分析响应速度时，需要把输入、线程调度、业务执行和反馈帧分别计时。Activity、Fragment、ViewPager2、点击、搜索、Deep Link 和 Widget 的入口各不相同，但都不能让主线程执行没有时长边界的工作；后台任务也要限制 CPU、I/O，并正确处理取消和结果提交。

Android 17 的平台源码基线是 `android-17.0.0_r1`，输入驱动和调度分析使用 `android17-6.18-2026-06_r6`。固定毫秒经验、单一回调耗时，以及简单地“加一个异步”，都不足以证明性能已经改善。证据应来自口径一致的基准测试、Perfetto 关键路径和线上分布。

## 参考资料

- [AOSP Android 17：Activity.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Activity.java)
- [AOSP Android 17：Instrumentation.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/Instrumentation.java)
- [AOSP Android 17：ActivityThread.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP Android 17：ActivityStarter.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityStarter.java)
- [AOSP Android 17：ActivityInfo.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/pm/ActivityInfo.java)
- [AOSP Android 17：Manifest attributes](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml)
- [AOSP Android 17：View.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/View.java)
- [AOSP Android 17：ViewRootImpl.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [AOSP Android 17：InputDispatcher.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)
- [AOSP Android 17：InputTransport.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/input/InputTransport.cpp)
- [Android Developers：Fragment transactions](https://developer.android.com/guide/fragments/transactions)
- [Android Developers：Fragment animations and postponed transitions](https://developer.android.com/guide/fragments/animate)
- [Android Developers：ViewPager2 API](https://developer.android.com/reference/androidx/viewpager2/widget/ViewPager2)
- [Android Developers：Swipe views with ViewPager2](https://developer.android.com/develop/ui/views/animations/screen-slide-2)
- [Android Developers：Lifecycle-aware coroutine collection](https://developer.android.com/topic/libraries/architecture/coroutines)
- [Kotlin Coroutines API：debounce](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/debounce.html)
- [Kotlin Coroutines API：distinctUntilChanged](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/distinct-until-changed.html)
- [Kotlin Coroutines API：flatMapLatest](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/flat-map-latest.html)
- [Android Developers：Create Deep Links](https://developer.android.com/training/app-links/create-deeplinks)
- [Android Developers：Create an App Widget](https://developer.android.com/develop/ui/views/appwidgets)
- [Android Developers：Enhance App Widget transitions](https://developer.android.com/develop/ui/views/appwidgets/enhance)
- [Android Developers：Handle configuration changes](https://developer.android.com/guide/topics/resources/runtime-changes)
- [Android Developers：Android 17 MessageQueue behavior](https://developer.android.com/about/versions/17/changes/messagequeue)
- [Perfetto：FrameTimeline data source](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android Developers：Macrobenchmark overview](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
