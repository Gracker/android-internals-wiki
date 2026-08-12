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

启动完成后，用户仍会不断触发页面跳转、Tab 切换、点击和搜索。每个场景都要同时记录起点与终点；只测回调耗时，无法回答像素何时出现，也无法解释数据何时可用。

各场景采用下面的测量边界：

| 场景 | 起点 | 第一个终点 | 业务终点 |
| --- | --- | --- | --- |
| Activity / Fragment 跳转 | 触发导航的输入事件 | 目标页提交第一帧 | 目标内容可交互 |
| Tab 切换 | 点击 Tab 或滑动手势 | 新页稳定呈现 | 新页主要数据可用 |
| 普通点击 | 输入事件进入应用 | pressed、Ripple 或状态变化呈现 | 点击动作完成或进入可恢复状态 |
| 实时搜索 | 归一化后的查询发生变化 | Loading / 空态呈现 | 当前查询的结果呈现 |
| Deep Link / Widget | 外部宿主发起 Intent 或 PendingIntent | 目标页第一帧 | 链接内容可交互 |

起点也要写清楚。`ACTION_DOWN`、`ACTION_UP`、`onClick()` 和导航调用是不同时间点；搜索输入、debounce 到期和请求发出也属于不同阶段。Perfetto 适合关联 Input、主线程、Binder、FrameTimeline 与自定义 trace，Macrobenchmark 适合重复执行固定交互。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。输入驱动、调度、CPU frequency 和 I/O 的分析以内核 `android17-6.18-2026-06_r6` 为准。固定毫秒收益不能脱离设备、刷新率和业务入口使用。

## 页面跳转：Activity 与 Fragment 要分开看

### Android 17 的 Activity 跳转路径

同一应用内调用 `startActivity()` 仍会进入 `system_server`。Android 17 的主要路径可以压缩为：

1. `Activity.startActivityForResult()` 调用 `Instrumentation.execStartActivity()`。
2. 客户端通过 `IActivityTaskManager.startActivity()` 发起 Binder 请求。
3. ATMS / `ActivityStarter` 解析 Intent、权限、Task、launch mode 和窗口状态。
4. 目标进程不存在时，系统先请求 Zygote 创建并绑定进程。
5. 目标进程已存在时，系统通过 `ClientTransaction` 发送 `LaunchActivityItem`、`ResumeActivityItem` 等事务项。
6. 应用主线程创建 Activity，执行生命周期、构建窗口和 UI，并提交目标页首帧。

Android 9（API 28）引入 ClientTransaction 体系；Android 8.x 的旧路径使用 `scheduleLaunchActivity()`。这段历史能解释旧 trace 名称，Android 17 结论仍以 `android-17.0.0_r1` 为准。

“打开 Activity”至少有三种成本形态：

| 状态 | 可能出现的工作 |
| --- | --- |
| 目标 Activity 尚未创建，应用进程存活 | ATMS 调度、Activity 实例与窗口、生命周期、UI 和首帧 |
| 目标 Activity 已在 Task 中 | Task/launchMode 决策、`onNewIntent()` 或生命周期恢复、必要重绘 |
| 目标进程不存在 | 额外包含进程创建、`Application`、Provider 和首 Activity；接近冷启动 |

因此不能给 Binder、Activity 构造、inflate 或首帧分配通用时间。进程是否存活、目标页资源、转场、系统负载和编译状态都会改变结果。

### 从输入到目标帧拆开测

页面跳转慢可以落在五段不同的区间：

- 输入已经到应用，但主线程迟迟没有进入点击回调；
- 导航调用到 `system_server` 接收之间存在主线程或 Binder 等待；
- ATMS 解析、Task 操作或进程启动耗时；
- 目标 Activity / Fragment 的创建、数据读取与 UI 构建耗时；
- 目标内容已准备，但 measure、layout、draw、RenderThread 或合成错过帧截止时间。

下面的 AndroidX trace 只标记导航调用本身，便于在 Perfetto 中找到业务入口：

```kotlin
trace("Navigation.OpenDetail") {
    navController.navigate(
        DetailRoute(itemId = item.id)
    )
}
```

该 slice 在 `navigate()` 返回时结束，不代表目标页已经显示。验收时还要结合目标窗口的 FrameTimeline、目标页自定义阶段标记和内容就绪事件。trace 名称保持低基数，业务 ID 通过受控参数或单独事件记录。

转场动画需要单独判断。动画持续期间可以并行创建页面；流畅的动画能覆盖部分准备时间，掉帧的动画会放大迟滞感。不要用动画时长代替页面准备耗时，也不要为了缩短一个数字直接删除必要的空间连续性。

### Android 17 的配置变更边界

Android 17 默认不再因以下变化重建 Activity：

- keyboard、keyboardHidden、navigation、touchscreen、colorMode；
- `uiMode` 只在进入或离开 `UI_MODE_TYPE_DESK` 时变化的情况。

运行中的 Activity 会收到 `onConfigurationChanged()`。若应用依赖销毁重建来重新读取资源，需要在 Manifest 的 `android:recreateOnConfigChanges` 中声明对应标志。`android-17.0.0_r1` 的 Manifest 属性说明还规定：同一标志若同时写进 `configChanges` 与 `recreateOnConfigChanges`，Activity 不会重建。

这项变化会减少某些显示器、输入设备和桌面模式切换中的状态丢失，也把资源刷新责任交给仍存活的 Activity。测试要覆盖主题、drawable、尺寸、导航状态和输入设备切换；只看生命周期次数会漏掉资源没有更新的问题。

### FragmentTransaction 是主线程异步队列

`FragmentTransaction.commit()` 会把事务安排到主线程执行，它不会在调用点同步完成。`setReorderingAllowed(true)` 允许 FragmentManager 合并同批事务中的中间状态，官方建议每个事务启用。`replace()` 的语义接近同一容器中的 remove 加 add；加入 back stack 后，旧 Fragment 的实例与 View 生命周期会按状态转换，返回时可能重新创建 View。

Fragment 切换的常见成本包括：

- 主线程等待执行 pending transaction；
- Fragment 实例与依赖创建；
- `onCreateView()` / ComposeView 首次组合；
- FragmentStateManager 状态推进；
- SpecialEffectsController 管理的动画或 transition；
- RecyclerView、图片和数据在同一帧集中更新；
- 返回栈恢复时重新创建 View。

AndroidX Fragment 没有承诺为每个生命周期或事务自动生成稳定的 Perfetto slice。业务应在导航入口、目标页 UI 构建和数据提交处插桩，再结合 `inflate`、RecyclerView、FrameTimeline 与线程状态。

`commitNow()` 会立即在当前主线程执行事务，且不能与 `addToBackStack()` 同用。它适合调用方必须马上读取事务结果的少数情况；用它追求“更快”会把创建、生命周期和布局工作同步塞进当前消息。FragmentManager 已保存状态后，普通 commit 还会抛出异常；`commitAllowingStateLoss()` 也不能作为性能手段。

### Fragment 页面怎样减少等待

- 使用接收 Fragment class 的事务 API，让 `FragmentFactory` 参与正常创建与状态恢复；
- 依赖注入放在 Factory 或 DI 容器，路由参数放在 arguments / Navigation route，构造过程不查磁盘和网络；
- 目标页尽快提交稳定骨架或缓存内容，把次要区域放到首帧后；
- View 销毁后取消与 `viewLifecycleOwner` 绑定的图片、列表和动画工作；
- `postponeEnterTransition()` 只等待 shared element 等转场必需内容，并同时设置 `postponeEnterTransition(timeout, unit)`；
- 成功、失败、取消和超时路径都要调用或触发 `startPostponedEnterTransition()`；
- 返回栈频繁重建 View 时，区分数据复用与 View 复用，不长期保留大 View 树来换速度。

Activity 与 Fragment 的选择由导航、模块边界、状态恢复和窗口需求决定。二者都在应用主线程创建 UI，Fragment 也可能因复杂布局和同步工作产生长帧。

## Tab 切换：ViewPager2 的保留范围与生命周期

### `offscreenPageLimit` 是内存与重建成本的交换

ViewPager2 基于内部 RecyclerView。默认值 `OFFSCREEN_PAGE_LIMIT_DEFAULT (-1)` 使用 RecyclerView 的缓存策略，不显式保留固定数量的邻页。显式值必须大于等于 1；传入 0 会抛出 `IllegalArgumentException`。

设置为 `N` 后，当前页两侧 N 页会被创建并保留在 View 层级中；范围之外的页面从 View 层级移除，并按 adapter / RecyclerView 规则在需要时重建或复用。值增大可能减少往返滑动时的 inflate 与 layout，也会增加 View、图片、Compose composition 和订阅占用。

选择方法是对候选值做对照：

1. 用默认 `-1` 建立切换帧与内存基线；
2. 只测试业务有能力长期保留的较小值；
3. 覆盖快速往返、跨多页、旋转、后台恢复和低内存；
4. 同时看 FrameTimeline、创建次数、PSS、GC 和数据请求；
5. 根据页面复杂度与设备层级决定，不按 Tab 总数套用固定值。

ViewPager2 的公开 API 不允许替换内部 LayoutManager。优化入口集中在保留范围、页面构建成本、adapter 稳定 ID、数据预取和生命周期。

### FragmentStateAdapter 的可见生命周期

`FragmentStateAdapter` 使用 `setMaxLifecycle()` 约束页面：选中页达到 `RESUMED`，其他已添加页面通常停在 `STARTED`。旧 ViewPager 的 `setUserVisibleHint()` 已废弃，旧 adapter 的 `BEHAVIOR_RESUME_ONLY_CURRENT_FRAGMENT` 也不属于 ViewPager2 API。

数据加载可以分为两件事：

- View 在 `STARTED` 时收集并渲染可见或即将可见的数据；
- Fragment 进入 `RESUMED` 时触发幂等的 `ensureLoaded()`，只启动尚未完成的业务加载。

下面的示例把加载状态交给 ViewModel，并让 UI 收集随 View 生命周期停止：

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

`ensureLoaded()` 需要识别 Loading、Success、可重试 Error 和强制刷新，不能只靠 Fragment 成员布尔值。ViewModel 可跨同一 Fragment 的 View 重建保留状态；进程死亡后的恢复仍需 SavedState 或持久化数据源。

可见性与加载不要绑定到 `onViewCreated()`：邻页可能提前创建，从而把所有 Tab 请求同时挤进当前交互。也不要在每次 `onResume()` 无条件刷新，否则往返滑动会制造重复网络与列表更新。

### 邻页预取要有预算

`OnPageChangeCallback.onPageSelected()` 可以触发邻页数据预取，但 `onPageSelected()` 只提供选中位置，不自动表达用户下一步方向。预取策略要结合前一位置、页面顺序、网络类型、缓存新鲜度和用户是否停止滚动。

预取结果需要：

- 与页面 key、账号和筛选条件绑定；
- 有大小和 TTL 限制；
- 页面远离、查询变化或宿主销毁时可取消；
- 失败时不覆盖正常加载的错误处理；
- 避免和页面自己的首次请求重复；
- 在低内存或受限网络下可以关闭。

滑动动画期间优先保护主线程和 RenderThread。大量 JSON 解析、图片解码、DiffUtil 提交或 Compose 状态更新即使位于 worker，也可能在结果提交时挤入同一批帧。

### adapter 数据变化也会制造抖动

`FragmentStateAdapter` 默认 item ID 与 position 绑定。动态增删或重排页面时，应按文档实现稳定的 `getItemId()` 与 `containsItem()`，否则 Fragment 身份、状态恢复和创建次数可能与业务预期不同。更新后用 `notifyItem*` 或可靠的差分通知，不要每次刷新都重建整个 ViewPager2 adapter。

## 点击响应：反馈帧比 onClick 返回更接近用户感受

### Android 17 的输入与 View 路径

触摸事件从设备到目标 View 大致经过：

1. 内核 evdev 上报触摸数据；
2. InputReader 读取、归一化并生成 MotionEvent；
3. InputDispatcher 根据窗口、触摸焦点和策略选择目标；
4. InputChannel 把带序号的事件送到应用，应用处理后回传完成状态；
5. `ViewRootImpl.WindowInputEventReceiver` 把事件交给应用主线程输入阶段；
6. DecorView / ViewGroup 执行 `dispatchTouchEvent()`、拦截和命中测试；
7. 目标 View 维护 pressed、长按和手势状态；
8. 合法点击在 `ACTION_UP` 后通过 `performClick()` 调用 listener；
9. 下一次遍历、渲染与合成把反馈像素呈现到屏幕。

平台步骤以 `android-17.0.0_r1` 的 InputDispatcher、InputTransport、ViewRootImpl 与 View 为依据；驱动调度和 CPU 运行状态以内核 `android17-6.18-2026-06_r6` 为依据。每段时长取决于触控采样、队列、刷新率和系统负载，不使用固定区间。

`MotionEvent.getEventTime()` 与 `SystemClock.uptimeMillis()` 可用于应用内粗略比较事件时间和回调进入时间。面板呈现时间不能由 `Choreographer.postFrameCallback()` 直接代替；精确的 input-to-display 分析应使用 Perfetto 的 Input 关联、FrameTimeline 与显示轨迹。

### pressed 与 Ripple 也依赖主线程和帧

Android 17 的 `View.onTouchEvent()` 在普通可点击 View 收到 `ACTION_DOWN` 时设置 pressed 状态。View 位于可滚动容器时，Framework 会先进入 prepressed，并延迟一个 tap timeout，以免滚动手势误显示点击反馈。`ACTION_UP` 路径会 post `PerformClick`，给 pressed 状态一次先进入绘制的机会。

Ripple 是根据 drawable state 绘制的反馈。若主线程被长消息、同步 Binder、锁或停顿阻塞，pressed 状态即使已经写入，也可能错过下一帧。Ripple 无法独立绕过主线程和渲染管线。

一次点击可以有两个视觉终点：

- 输入确认：pressed、Ripple、选中态或按钮禁用已经呈现；
- 动作结果：导航页、保存成功、错误提示或可重试状态已经呈现。

页面应尽早表达“已接收”，长任务在受控作用域执行。回调中同步查库、`SharedPreferences.commit()`、文件 I/O、图片解码、等待锁或同步 Binder，都会推迟反馈帧。把函数标为 `suspend` 也不会自动换线程；应按数据源 API 的线程契约处理。

### 自定义 View 保留系统点击语义

自定义手势识别若直接调用业务函数，会绕过 OnClickListener、点击音效和无障碍 `ACTION_CLICK`。识别出合法单击后应调用 `performClick()`，并在覆盖 `performClick()` 时调用父实现。拖动、滑出边界、长按、多指、pressed 清理和 `ACTION_CANCEL` 需要由完整状态机或 `GestureDetector` 处理；只在 `ACTION_UP` 无条件调用业务函数会把滚动和取消也识别成点击。

能使用标准 Button、可点击 View 或 Compose clickable 时，保留组件自带的语义、触摸目标、键盘操作和无障碍支持。自定义 View 还要让触摸、键盘和无障碍动作进入同一条业务入口，避免三套状态各自演进。

### 重复点击要按业务状态处理

固定时间窗口会误伤快速合法操作，也无法阻止两个请求都已到达服务端。更可靠的方案包括：

- 提交期间把按钮状态切为 Loading，并决定是否允许取消；
- 给创建、支付等操作使用业务幂等键；
- 导航前检查当前 destination 与生命周期状态；
- 列表操作按 item ID 隔离，避免全页面禁用；
- 失败后恢复按钮并给出明确重试入口；
- 仍需时间门限时使用单调时钟 `SystemClock.elapsedRealtime()`，并覆盖键盘与无障碍点击。

## 实时搜索：把等待、执行和过期结果分开

### 搜索管线有四段延迟

一次“边输入边搜索”通常包含：

1. IME / TextField 把查询写入状态；
2. 归一化、debounce 和重复值过滤；
3. 本地索引、数据库或网络执行；
4. 结果 Diff、列表布局和结果帧呈现。

debounce 会主动增加等待，用来减少仍在变化的查询。它不能归入后端耗时，也不能被隐藏在一个“搜索总耗时”数字里。Loading 或清空旧结果的反馈可以在等待期间出现。

### Flow 管线要处理空查询与取消

下面的 ViewModel 管线让空查询立即清空结果，对非空查询使用可配置的 debounce，并让新查询停止收集旧查询：

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

`distinctUntilChanged()` 只去掉相邻的相同值。序列 `foo → bar → foo` 会再次搜索 foo，这通常符合用户重新选择查询的预期。若需要缓存，应在 repository 按规范化 query、账号、筛选和数据版本建立 key。

`flatMapLatest` 会取消旧 Flow 的收集。底层 Room、网络客户端或自定义数据源还要支持协作取消；服务器已经接收的请求可能继续执行。每个结果都应携带 query 或 generation，UI 只接受当前 generation，防止不可取消的旧回调覆盖新结果。

`searchDebounceMs` 没有跨应用通用值。内存索引可能不需要 debounce，远程补全会结合打字节奏、请求成本和服务端限流选择。应通过输入到反馈、请求数、取消率、结果呈现分布和用户完成率调参。

### 本地索引与缓存不能挤进按键帧

- Room / SQLite 查询使用索引并限制返回列与首批数量；
- 拼音、首字母或全文索引在数据变化时增量更新，不在每次按键时全量转换；
- 大列表 Diff 在 worker 计算，提交阶段仍要观察主线程和布局；
- 内存缓存设置容量，持久缓存设置数据版本与过期规则；
- 热门查询预取受网络、账号、隐私和存储预算约束；
- 页面退出或查询变化时取消预取和图片工作；
- 错误、离线与空结果属于不同 UI 状态，避免旧列表假装属于新查询。

搜索结果呈现后的键盘、焦点和无障碍播报也会影响响应。大量结果一次性触发布局与 accessibility event，可能让网络很快而界面仍迟钝。

## Deep Link：路由正确性属于响应时间

Android 使用 Intent filter 路由 Deep Link。Android 12（API 31）起，普通 HTTP(S) 链接若没有通过域名验证，通常交给默认浏览器；自有域名应使用 verified App Links，避免 chooser 或浏览器往返。

Deep Link 入口可能命中存活进程，也可能触发完整冷启动。优化时要覆盖：

- URI 解析和安全校验只做内存内、有限长度的工作；
- 直接创建能展示目标内容的宿主，减少只负责转发的 Activity；
- 认证缺失时保存规范化 route，在登录后恢复，不重复解析不可信 URI；
- 目标内容未到时先展示合法占位、缓存或错误状态；
- Intent 通过 `onCreate()` 与 `onNewIntent()` 进入时采用同一条幂等路由；
- App Link 验证失败、无网络、非法参数和不存在内容都有稳定退路；
- Back / Up 栈符合外部进入时的导航预期。

下面的命令分别用于观察 Intent 解析结果与执行一次带等待的 Deep Link 启动：

```bash
adb shell am start \
  -W \
  -a android.intent.action.VIEW \
  -d 'https://www.example.com/items/42' \
  com.example.app
```

`-W` 输出适合快速回归，但不能拆分路由、页面创建和结果渲染。正式实验应为同一 URI 分别测冷、温状态，并用 Macrobenchmark / Perfetto 关联目标页 TTID、TTFD 和 FrameTimeline。

## Widget 点击：从宿主进程进入应用

App Widget 的 View 位于 Launcher 等宿主进程，布局由 RemoteViews 描述。点击通常触发应用提供的 PendingIntent，因此会经过宿主、系统和目标组件；应用进程不存在时还会包含冷启动。

打开页面的 Widget 点击应尽量使用指向目标 Activity 的 `PendingIntent.getActivity()`。Android 12 起，Launcher 可以为这种直接启动提供更顺滑的转场；从 BroadcastReceiver 或 Service 再跳 Activity 的 trampoline 不会使用这套新动画。

下面的代码给不同 Widget 实例创建可区分、不可变的页面 PendingIntent：

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

`requestCode` 与 Intent data 参与 PendingIntent 身份，能避免多个 Widget 复用旧路由。只在系统或宿主必须填充 Intent 的 API 上使用 mutable；简单的直达 Activity 点击保持 immutable。Widget 顶层背景使用 `@android:id/background`，可让 Android 12+ Launcher 识别转场背景。

切换开关或执行轻量命令时可以把 PendingIntent 指向 Receiver。`onReceive()` 保持短小，先更新可见状态，再把可延迟工作交给受约束的后台机制；长网络请求不能占住 Receiver。要同时测试应用进程存活、进程不存在、设备锁定、Widget 多实例和目标页面已在 Task 中的情况。

## 用 Perfetto 和基准把场景关联起来

### Trace 中关注四条证据

1. **Input**：事件何时进入系统、何时送到应用、应用何时完成处理。
2. **Main thread / Binder**：回调前排队、同步调用、锁、I/O、类加载和生命周期。
3. **FrameTimeline**：哪个 intended frame 承载反馈，是否迟交、由 App 还是 SurfaceFlinger 造成。
4. **Business state**：页面、Tab、点击动作或搜索结果何时达到定义的可用状态。

自定义 slice 应使用稳定名称，例如 `Navigation.Detail`、`Tab.Select`、`Search.Query`。用 `androidx.tracing.trace` 或 try/finally 保证异常时结束 section。不要把 URI、query、用户 ID 或 item ID 直接拼进 slice 名，避免高基数和敏感信息进入 trace。

Macrobenchmark 可以通过 UIAutomator 重复点击、滑动和输入，配合 `FrameTimingMetric`、自定义 trace 与目标状态等待。每个用例固定入口、数据、动画、编译状态和设备；点击后只 `waitForIdle()` 可能过早或过晚，应等待明确的页面节点或业务完成标记。

### 响应回归看分布与失败

页面切换和搜索都可能因缓存命中形成双峰分布。报告至少按冷/温数据、入口、设备、Android 版本和网络条件拆分，并同时记录：

- 输入到首个反馈帧；
- 输入到业务内容；
- 慢帧与冻结帧比例；
- 请求数、取消率、缓存命中率；
- 超时、空态、错误和降级比例；
- 样本量及 P50、P90/P95。

平均值无法描述少量长尾。阈值应来自产品场景和设备基线，RAIL 可以作为 Web 交互启发，不能当成 Android 全设备硬门槛。

## Android 17 与内核边界

Android 17 对 targetSdk 37 及以上应用启用 lock-free `MessageQueue`。它可能降低生产者与 Looper 的锁竞争，也会让反射 `mMessages` 或私有方法的旧监控失效。页面切换和点击监控应使用公开 trace、FrameTimeline 与测试 API；队列实现变化不能替代应用侧对照测量。

Android 17 还引入 generational Concurrent Mark-Compact GC，并可通过 ART Mainline 覆盖部分较早系统。它可能改变停顿与 CPU 分布；看到点击或切换附近的 GC slice 时，要检查分配速率、堆状态和 collector 事件，不用平台版本推断固定收益。

出现长时间 runnable、频繁抢占、CPU frequency 不足、input driver 延迟或 I/O wait 时，再进入 `android17-6.18-2026-06_r6` 分析调度和驱动。Activity、View、InputDispatcher、MessageQueue 与配置变更仍属于 `android-17.0.0_r1` 平台证据。

## 场景审计清单

### 页面与 Tab

- 记录输入、导航调用、目标首帧和内容可用四个时间点。
- 区分目标进程、Activity 和 Fragment 是否已经存在。
- 检查目标 UI 创建、同步数据、转场和结果提交。
- Fragment 事务启用 reordering，并避免为速度使用 `commitNow()`。
- 对 ViewPager2 默认缓存与候选 offscreen limit 做帧和内存对照。
- 数据加载幂等、可取消，并与 View 生命周期分离。
- 覆盖返回栈、配置变化、进程重建与动态 Tab。

### 点击与搜索

- 检查事件到 callback 的主线程排队。
- 确认 pressed / Ripple 或业务状态能在短回调后绘制。
- 自定义 View 通过 `performClick()` 保留无障碍语义。
- 用业务状态和幂等保护重复提交。
- 搜索把 debounce、执行、结果渲染分别计时。
- 空查询立即清理，旧查询可取消或带 generation 防覆盖。
- 索引、Diff、图片与 accessibility 更新都纳入结果帧分析。

### 外部入口

- Deep Link 同时测试冷、温、`onNewIntent()` 与非法参数。
- 自有域名检查 App Link 验证和 Android 12+ 路由。
- Widget 直达 Activity，避免 Broadcast / Service trampoline。
- PendingIntent 身份、mutability、多实例和返回栈都有测试。
- 外部入口同样定义 TTID 与内容可用终点。

## 小结

响应速度需要沿着输入、调度、业务执行和反馈帧分段。Activity、Fragment、ViewPager2、点击、搜索、Deep Link 与 Widget 的入口不同，共同约束是主线程不能被无界工作占用，后台任务也要控制 CPU、I/O、取消和结果提交。

Android 17 的平台源码锚点是 `android-17.0.0_r1`；输入驱动与调度分析使用 `android17-6.18-2026-06_r6`。固定毫秒经验、单一回调耗时和“加一个异步”都不足以证明优化，证据应来自同口径基准、Perfetto 关键路径和线上分布。

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
