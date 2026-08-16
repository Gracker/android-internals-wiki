---
title: "Jetpack Compose 内存分配与 GC 影响"
chapter: "23.8"
section: "23.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [compose, memory, gc, allocation, slottable, recomposition]
related_chapters: ["4.8", "7.7", "10.6", "22.3", "23.5"]
last_verified: "2026-08-15"
last_verified_against: "Compose Runtime 1.12.0 stable / AndroidX 963bf914f78b389bdddef0da7f36bee19d897274 / Kotlin 2.0.20+ Strong Skipping / AOSP android-17.0.0_r1 ART"
last_review_finalize_at: "2026-08-15T08:29:11+08:00"
last_review_finalize_run_id: "20260815-082911-gracker-writing-review"
confidence: high
sources:
  - type: research
    path: "DeepResearch/2026-06-19-jetpack-compose-memory-churn-source-analysis.md"
  - type: official
    path: "https://developer.android.com/jetpack/compose/performance"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/compose-runtime"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/bestpractices"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/stability/strongskipping"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/performance/stability/diagnose"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/lists"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/tooling/tracing"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动？.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
consolidated_from:
  - "src/part5-app/ch23-memory-practice/12-compose-memory-allocation-gc.md"
pipeline_stage: finalized
last_draft_polish_at: "2026-08-15T08:29:11+08:00"
last_draft_polish_run_id: "20260815-082911-gracker-writing"
---

# Jetpack Compose 内存分配与 GC 影响

## 范围与版本

讨论范围是 Android 上的 Compose Runtime、应用 Java Heap（ART 管理的 Java/Kotlin 对象堆）与 ART GC（垃圾回收）。平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核基线为 `android17-6.18-2026-06_r6`。Compose 是独立发布的 Jetpack 库；本文使用 2026 年 8 月 12 日发布的稳定版 Compose Runtime 1.12.0，并以 AndroidX 提交 `963bf914f78b389bdddef0da7f36bee19d897274` 为源码锚点。

Compose Runtime 1.13.0-alpha01 已发布，但仍是预览版。版本比较会标出预览变化，正文结论以 1.12.0 稳定版为准。

Composition 是一棵可组合界面在运行时的实例，保存界面结构、状态订阅和 `remember` 值；重组（recomposition）是状态变化后重新执行受影响的可组合函数。处理 Compose 内存问题时，先区分两种症状：

- 存活对象持续增加：常见于 Composition 没有按宿主生命周期释放、协程或监听器存活过久、状态所有者范围过大、View 与 Compose 互相持有。
- 短命对象分配速率过高：常见于组合阶段反复排序、映射、格式化，频繁重建输入对象，或在高频状态变化中执行不必要的组合。

allocation 表示创建对象并占用 Java Heap 空间，短命对象被频繁创建又回收时也称为分配抖动（allocation churn）。一次重组不一定创建新对象，也不一定创建新的 `RecomposeScopeImpl`。定位时要分别观察重组次数、对象分配和 GC；泄漏治理可参阅 [23.1 内存泄漏检测与治理](./01-memory-leak-governance.md)，分配抖动与 GC 可参阅 [23.5 内存抖动与 GC 治理](./05-memory-churn-gc.md)，生产环境指标可参阅 [23.7 内存监控与线上治理](./07-memory-monitoring.md)。

## Compose Runtime 会长期保存哪些数据

一份活跃 Composition 至少要保存组合结构、`remember` 的值、重组范围、状态观察关系和待应用的变更。理解这些内部结构的用途，才能区分正常持有、短期分配和生命周期泄漏。

### Slot storage 有两种实现

slot storage 是 Compose Runtime 保存组合层级、节点位置和 `remember` 值的内部存储。1.12.0 同时包含 gap-buffer（在连续数组中保留可移动空隙）与 LinkTable（用链接结构减少内容移动时的数组复制）两种实现。历史稳定提交中的 [`Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt) 和 [1.12.0 `Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt) 都显示，`CompositionImpl.createSlotStorage()` 根据 `ComposeRuntimeFlags.isLinkBufferComposerEnabled` 选择实现。

历史 [`ComposeRuntimeFlags.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt) 与 [1.12.0 `ComposeRuntimeFlags.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt) 都把该开关的默认值设为 `false`。AndroidX 的 [Compose Runtime 1.11 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-runtime)首次说明了 LinkTable 的目标；1.12.0 发布说明仍将它列为实验实现，并要求团队主动启用和验证。

因此：

- 未启用实验标志的 1.12.0 应按 gap-buffer 分析；
- 开启标志的应用要按 LinkTable 分析，并同时检查 R8（Android 代码压缩与优化工具）规则；
- heap dump（Java 堆转储）中的内部类名和引用形态可能不同；
- 不应给所有 Compose 版本套用固定的 SlotTable 字节数或扩容次数。

slot storage（槽位存储）持有 `remember` 值和组合结构。Composition 被宿主继续引用时，其中的值也会继续存活。heap dump 中的 dominator（支配对象，释放它才可能释放其支配的对象集合）用于寻找主要持有者。看到 SlotTable 或 LinkTable 出现在引用链中时，应继续检查 Activity、Fragment View、`ComposeView`、Navigation destination（导航目的地）、Recomposer（调度重组的运行时对象）或长期协程；内部表结构通常只是引用路径中的一环。

### `RecomposeScopeImpl` 会复用

`RecomposeScopeImpl` 表示可独立失效并重新执行的组合范围。历史稳定版 [`RecomposeScopeImpl.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt) 与 [1.12.0 源码](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt) 都让 `trackedInstances` 与 `trackedDependencies` 初始为 `null`，读取普通状态或派生状态后才按需创建。`release()` 会清空 `owner`、追踪集合和用于重启该范围的 `block`。

重组时可以继续使用已有的重组范围；`updateScope()` 只替换重启用的代码块。Lambda 是否产生新对象，还受 Compose Compiler 生成代码与 Strong Skipping（强跳过模式）影响。

[Strong Skipping 官方说明](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)记录了两条规则：

- Kotlin 2.0.20 起默认启用 Strong Skipping；
- restartable composable（可由运行时重新执行的可组合函数）即使带不稳定参数也可以被跳过；可组合函数内部的 Lambda 会自动缓存（memoize），也就是根据捕获对象缓存并复用。

不稳定参数使用引用相等比较，稳定参数使用对象相等比较。调用方每次构造新 `List`、新 UI 数据模型或捕获值不同的新 Lambda，仍可能让比较失败。优化时应检查输入对象是否稳定复用、状态是否在合适的所有者中更新，以及运行时是否出现高频分配；源码中的 Lambda 表达式数量不能直接代表运行时分配量。

### Snapshot 状态记录随写入演进

Snapshot 是 Compose 为状态读取和写入提供一致视图的机制；状态记录（`state record`）是同一状态对象在不同 Snapshot 中可见的数据版本。`MutableState` 与 `derivedStateOf` 都使用记录链。写入需要取得可写记录，读取会选择当前 Snapshot 可见的记录；切换 Snapshot 不会为所有状态统一新建记录。并发 Snapshot、写入频率与记录复用共同决定对象数量。

Compose Runtime 1.11.4 的 [`DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt) 与 [1.12.0 `DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt) 都显示，`ResultRecord` 保存依赖集合、计算结果和用于判断有效性的哈希值。mutation policy（变更策略）判定新旧结果等价时，实现会更新当前记录的依赖信息；结果变化时才申请可写记录。每一帧或每次 Snapshot 应用都不能直接换算成一个新 `ResultRecord`。

## 哪些分配值得优先处理

### 组合阶段的集合加工与格式化

composable body（可组合函数体）可能因状态变化多次执行。排序、`map`、字符串拼接、解析和对象适配如果直接放在函数体中，也会重复执行。这段代码把排序结果保存在 Composition 中，并给 Lazy list（按需组合可见列表项的容器）提供稳定身份。

```kotlin
@Composable
fun ContactList(
    contacts: List<Contact>,
    comparator: Comparator<Contact>,
    modifier: Modifier = Modifier,
) {
    val sortedContacts = remember(contacts, comparator) {
        contacts.sortedWith(comparator)
    }

    LazyColumn(modifier) {
        items(
            items = sortedContacts,
            key = { contact -> contact.id },
        ) { contact ->
            ContactRow(contact)
        }
    }
}
```

`remember` 在 key（决定缓存何时失效的输入）的比较结果不变时返回已保存值，key 变化后重新计算。计算量较大的数据加工可以移到 ViewModel 或数据层。`contacts` 若在原对象上修改内容，Compose 和 `remember` 都可能观察不到变化；可以把界面状态暴露为新的不可变列表实例，或使用 `SnapshotStateList` 这类能通知写入的状态集合。每次重组创建 `contacts.toList()` 作为 key 会额外分配一份列表，也不能修正原地修改的数据模型。

### 原始类型状态 API

Compose Runtime 提供 `mutableIntStateOf`、`mutableLongStateOf`、`mutableFloatStateOf` 和 `mutableDoubleStateOf`。这些接口直接保存整数、长整数、浮点数等原始类型，减少通用泛型状态可能产生的装箱对象。示例让高频计数状态使用原始类型接口。

```kotlin
@Composable
fun FrameCounter() {
    var frameCount by remember { mutableIntStateOf(0) }

    Text(
        text = frameCount.toString(),
        modifier = Modifier.clickable { frameCount++ },
    )
}
```

历史稳定版 [`SnapshotIntState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt) 与 [1.12.0 源码](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt) 中，`SnapshotMutableIntStateImpl` 都用 `IntStateStateRecord` 保存 `Int`，`intValue` 直接读写原始类型，委托运算符也访问 `intValue`。这条路径可以避免通用 `MutableState<Int>` 的自动装箱；收益仍要用 allocation recording（对象分配记录）验证，少量低频状态无需逐个替换。

### Lambda 与 Modifier

Strong Skipping 会缓存可组合函数内的 Lambda，但以下写法仍可能产生额外分配或失去跳过机会：

- 在调用可组合函数前反复构造新的界面模型或集合；
- 明确使用 `@DontMemoize`；
- 在非可组合函数的高频路径中创建捕获外部变量的 Lambda；
- 每次执行函数体都构造复杂 Modifier 链或中间集合；
- 参数对象的引用每次变化，使不稳定参数的 `===` 比较失败。

Compose Compiler 报告能说明函数能否重启、能否跳过，以及参数稳定性。它不提供运行时对象分配数量，需与 allocation recording 配合使用。

## `derivedStateOf` 与 `snapshotFlow`

### `derivedStateOf` 减少无效重组

`derivedStateOf` 适合输入频繁变化、界面只关心较少结果变化的场景。例如滚动位置不断变化，而按钮只关心列表是否已经离开顶部。

这段代码把高频滚动状态转换成一个 Boolean，并用 `remember` 把派生状态对象保存在 Composition 中。

```kotlin
@Composable
fun ScrollToTopButton(listState: LazyListState) {
    val showButton by remember(listState) {
        derivedStateOf {
            listState.firstVisibleItemIndex > 0
        }
    }

    AnimatedVisibility(visible = showButton) {
        Button(onClick = { /* launch scroll */ }) {
            Text("返回顶部")
        }
    }
}
```

只要 `showButton` 的结果没有变化，读取它的可组合函数就不需要因每次滚动更新而重组。`derivedStateOf` 自身要维护依赖和缓存；普通字符串拼接、两个低频状态的简单组合，以及每次输入变化都会产生新输出的计算，直接计算通常更清楚。

Compose Runtime 1.12.0 稳定版已经包含一项潜在内存泄漏修复：未正确 `remember` 的 `derivedStateOf()` 在 forward write（同一轮组合先读取依赖状态，随后又写入该状态）场景中，可能被 Composition 持有到该 Composition 销毁。该问题影响 1.11.4，修复最早记录于 1.12.0-beta01，随后进入 1.12.0 稳定版。处理边界如下：

- 在可组合函数内创建 `derivedStateOf` 时使用 `remember`；
- 使用 1.11.4 或更早版本并怀疑该问题时，在 heap dump 中检查 `DerivedSnapshotState` 到 Composition 的引用链，并用 1.12.0 复测；
- 升级到 1.12.0 后仍要使用 `remember`，避免每次重组创建新的派生状态对象；
- 不用 `remember(list, index)` 代替对 `SnapshotStateList` 元素的观察，因为列表身份不变时缓存可能返回旧数据。

### `snapshotFlow` 负责把 Snapshot 状态转成事件流

`snapshotFlow` 记录 `block` 中读取的 Snapshot 状态；相关状态的写入被应用后，它会重新执行 `block`，只有新结果与旧结果不相等时才向 Flow 发送。历史稳定版 [`SnapshotFlow.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt) 与 [1.12.0 源码](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt) 都会注册 Snapshot apply observer（状态应用观察者）、维护订阅集合，并在 Flow 结束收集时取消本次订阅。

1.12.0 默认重载会创建内部 `SnapshotFlowManager`，并在 Flow 结束时释放；实验性重载允许同一线程上的多个 `snapshotFlow` 共用管理器，此时由调用方在不再使用时调用 `dispose()`，且不能让同一个管理器被不同线程并行收集。这段代码使用默认重载，把列表位置变化交给分析回调上报；任务会在 `LaunchedEffect` 离开 Composition 或 key 变化时取消。

```kotlin
@Composable
fun TrackListPosition(
    listState: LazyListState,
    reportIndex: (Int) -> Unit,
) {
    LaunchedEffect(listState) {
        snapshotFlow { listState.firstVisibleItemIndex }
            .collect { index -> reportIndex(index) }
    }
}
```

把 `snapshotFlow` 放在 `LaunchedEffect` 中不会自动造成泄漏。风险来自外部协程作用域比界面所有者存活更久、`LaunchedEffect` 的 key 选择错误、回调捕获 Activity/View，或重复启动未受管理的收集任务。heap dump 中只看到 Snapshot 类不足以确认泄漏，还要继续检查协程 Job（可取消任务）、Flow collector（Flow 收集者）和宿主生命周期。

## Lazy layout 的 key 维护列表项身份

Lazy layout（按需组合可见内容的布局）默认按位置识别 item（列表项）。数据重排后，同一个业务对象的位置会变化，按位置保存的 `remember` 状态就无法跟随业务对象移动。[Lazy list 官方文档](https://developer.android.com/develop/ui/compose/lists)建议为每项提供稳定且唯一的 key，使状态在插入、删除和重排时仍与同一个业务对象关联。

key 的主要价值包括：

- 数据插入、删除和排序后保持列表项身份；
- 减少无关列表项的重组；
- 让 `rememberSaveable` 状态在符合条件时恢复。

key 不能让滚出屏幕的所有节点永久保留，也不能消除列表项内部的对象分配。用于 `rememberSaveable` 时，key 类型还要能由 `Bundle` 保存，例如原始类型、枚举或 `Parcelable`。业务稳定 ID 通常适合作为 key；位置只适用于内容和顺序都固定的列表。

## View 与 Compose 混合时的生命周期

### `ComposeView` 应跟随正确的 LifecycleOwner

每个 `ComposeView` 都有自己的 Composition，并引用宿主 View。Fragment 的 View 销毁后，如果 Composition 仍由更长生命周期的对象持有，`remember` 值、副作用任务和界面树也会继续存活。

这段代码让 Fragment 中的 Composition 随 View lifecycle（从 `onCreateView()` 到 `onDestroyView()` 的界面生命周期）销毁。

```kotlin
override fun onCreateView(
    inflater: LayoutInflater,
    container: ViewGroup?,
    savedInstanceState: Bundle?,
): View {
    return ComposeView(requireContext()).apply {
        setViewCompositionStrategy(
            ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed
        )
        setContent {
            AppTheme {
                ScreenContent()
            }
        }
    }
}
```

[Compose in Views 官方文档](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)把 `DisposeOnViewTreeLifecycleDestroyed` 列为 Fragment View 的适用策略。普通 View 场景默认使用 `DisposeOnDetachedFromWindowOrReleasedFromPool`：View 脱离窗口时释放；若位于 `RecyclerView` 等复用容器中，则在容器脱离或该项被移出对象池时释放。释放策略要按宿主类型选择。

### `AndroidView.factory` 不需要额外 `remember`

`AndroidView` 的 `factory` 用于创建 View；`update` 在创建后执行，并在其中读取的 Snapshot 状态变化时再次执行。把 View 另存进 `remember` 会让 Composition 与 `AndroidView` 同时保存它的引用，增加生命周期不一致的风险。

Lazy list 中需要复用 View 时，应使用带 `onReset` 的重载 API。示例在复用前清理上一条列表项留下的临时状态，并在该 View 不再复用时释放资源。

```kotlin
AndroidView(
    factory = { context -> PreviewView(context) },
    update = { view ->
        view.bind(model)
    },
    onReset = { view ->
        view.clearTransientState()
    },
    onRelease = { view ->
        view.release()
    },
)
```

[Views in Compose 官方文档](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)说明，`onReset` 必须非空才会启用 Lazy 容器中的 View 复用；`onRelease` 在 View 离开 Composition 且不再复用时调用。`update` 应具备幂等性，也就是用相同输入重复执行不会累积副作用；监听器若在每次 `update` 中注册，要先替换或移除旧监听器。

混合页面的 heap dump 应同时检查 View tree（传统 View 层级）与 Composition。常见 dominator 包括 Fragment view binding（生成的视图绑定对象）、adapter（列表适配器）、listener（监听器）、`AndroidView` 内的 WebView/播放器/地图、Navigation back stack（导航返回栈）和长生命周期 ViewModel。

## Android 17 中分配如何触发 ART GC

Compose Runtime 对象位于应用 Java Heap。Android 17 的 [`heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)显示，Java 对象分配会更新已分配字节数；使用并发垃圾回收器时，`ShouldConcurrentGCForJava()` 根据当前配置检查字节阈值，以及启用后的 time-based GC（同时考虑分配量和距上次 GC 时间的触发方式）。需要 GC 时，分配路径会在允许线程挂起后调用 `RequestConcurrentGCAndSaveObject()` 请求并发回收。

[`heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)中的 `ConcurrentGCTask` 由 task processor（ART 的后台任务调度器）调度。GC 名称中的 concurrent 表示部分工作可与应用线程并行执行；root 扫描（检查线程栈和全局引用等根对象）、checkpoint（让线程在安全位置配合运行时操作）、对象移动与系统调度仍可能让应用线程等待并影响帧时间。

Android 17 的 ART 源码支持 generational CC（分代并发复制）与 generational CMC（分代并发标记压缩）。分代表示优先回收新生代对象，并按条件执行完整回收。设备选择哪种模式，还取决于垃圾回收器、read barrier（读取引用时执行的屏障逻辑）或 `userfaultfd` 内核能力、`-Xgc` 选项、ART 功能标志和 DeviceConfig 属性。源码支持某种模式，不代表所有 Android 17 设备都默认启用；应以目标设备日志和 Perfetto 跟踪结果为准。

Compose 分配与卡顿之间需要建立证据链：

1. Frame Timeline（帧时间线）出现 missed frame（未按时完成的帧）或长帧；
2. Compose tracing 显示对应时间段执行了哪些可组合函数；
3. allocation recording 证明该时间段的分配速率或特定类型增加；
4. ART GC slice（跟踪中的一段 GC 事件）、线程状态和暂停区间与长帧重叠；
5. 修正分配后，同一设备与场景的长帧和 GC 数据同步改善。

GC 与长帧出现在相近时间只能说明相关性。重组中的业务计算、measure/layout（测量与布局）、图片解码和主线程 I/O 都可能同时发生；需要用分配证据和修改后的对照数据确认 GC 是否为主要原因。

## 诊断与回归流程

### 用发布版配置测量性能

Debug（调试）构建、Layout Inspector、method tracing（方法调用跟踪）和 allocation recording 都会改变执行与分配行为。[Compose 稳定性诊断文档](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)要求编译器报告使用发布版构建。页面性能回归也应使用接近发布配置的可分析构建：编译优化、R8、Baseline Profile（预编译常用代码路径的配置）和依赖版本都要与发布版一致，同时通过 `profileable` 等方式允许工具采集。

这段 Gradle 配置用于输出 Compose Compiler 稳定性报告和模块指标。

```kotlin
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

报告中的 `restartable`、`skippable` 和参数稳定性用于筛选可疑的可组合函数。某个函数不可跳过但调用很少，可能没有用户可见成本；把不满足稳定性约定的类型强行标成 `@Stable`，可能让 Compose 跳过本应执行的更新。

### 四类工具回答四个问题

| 工具 | 回答的问题 | 使用限制 |
| --- | --- | --- |
| Compose Compiler reports | 编译器如何判断函数与参数 | 没有运行时次数和对象分配数据 |
| Layout Inspector | 当前会话中哪些 composable 重组或被跳过 | 调试工具有观测成本 |
| Perfetto + Compose tracing | 重组、布局、绘制、线程与 GC 的时间关系 | 需要固定场景和接近发布配置的构建 |
| Allocation recording / heap dump | 哪些类型在分配、哪些对象被谁持有 | 分配记录成本高；heap dump 只反映采集时刻 |

[Composition tracing 文档](https://developer.android.com/develop/ui/compose/tooling/tracing)说明，Macrobenchmark（在应用外驱动完整场景的基准测试）可以产出带 Compose tracing 的系统跟踪。滚动、页面切换和启动应写成可重复的 Macrobenchmark；Memory Profiler 用于定位具体分配或持有关系，不能单独作为回归判断依据。四类工具提供的是不同证据，需要按同一时间段、设备和操作进行关联。

### 先判断分配抖动，再判断泄漏

建议按以下顺序检查：

1. 用 `dumpsys meminfo` 和 Java Heap 曲线确认占用水平与增长形态；
2. 用 allocation recording 找出高频分配类型与调用栈；
3. 用 heap dump 查看离开页面后仍存活对象的 dominator；
4. 用 Perfetto 按时间对齐 Compose、帧与 GC 事件；
5. 修改一处后复跑相同操作，不同时改状态模型、列表与图片策略。

页面退出后仍存在一份 Composition 不一定异常，Navigation 可能按设计保留导航目的地状态。判断时要结合返回栈、宿主生命周期与产品预期。相同导航目的地的实例数量随进入次数持续增加，或旧 Fragment View 已销毁却仍支配 Composition，才指向生命周期泄漏。

## 版本边界

| 版本 | 相关变化 |
| --- | --- |
| Kotlin 2.0.20+ | Strong Skipping 默认启用；不稳定参数按引用相等判断，可组合函数内的 Lambda 自动缓存 |
| Compose Runtime 1.11.4 及更早版本 | LinkTable 实现存在但默认关闭；尚未包含 `derivedStateOf` forward-write 保留问题修复 |
| Compose Runtime 1.12.0 | 当前稳定锚点；包含上述 `derivedStateOf` 修复；LinkTable 仍为实验实现且默认关闭 |
| Compose Runtime 1.13.0-alpha01 | 当前预览版；不作为本文稳定行为依据 |
| Android 17 / API 37 | ART 源码锚点为 `android-17.0.0_r1`；垃圾回收器与分代模式仍受运行时和设备配置影响 |

Compose Multiplatform 在不同目标上使用不同运行时与内存管理器。这里的 GC、heap dump 和 Android View 互操作结论只适用于 Android；Desktop/JVM、iOS 或 Wasm 的对象大小与 GC 行为需要按各自平台验证。

## 小结

Compose 内存问题要把“对象被长期持有”和“短命对象分配过快”分开。slot storage（槽位存储）、RecomposeScope 和 Snapshot 状态记录是正常运行时结构，类名本身不能证明泄漏。泄漏要沿 dominator 查找生命周期更长的持有者，分配抖动要用 allocation stack（对象分配调用栈）确认创建位置。

应用代码应优先处理组合阶段的重复计算、每次创建的新输入对象、生命周期过长的状态所有者、未管理的协程和 View 资源。`remember`、`derivedStateOf`、原始类型状态 API、Lazy 列表 key 与 Strong Skipping 各自解决不同问题。ART GC 的触发与垃圾回收器配置以 Android 17 源码和设备跟踪结果为准；固定堆大小、每帧分配量或 GC 次数不能作为跨设备的通用阈值。

## 参考资料

- [Compose Runtime release notes](https://developer.android.com/jetpack/androidx/releases/compose-runtime)
- [Compose performance best practices](https://developer.android.com/develop/ui/compose/performance/bestpractices)
- [Compose phases and performance](https://developer.android.com/develop/ui/compose/performance/phases)
- [Strong Skipping](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)
- [Diagnose Compose stability](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)
- [State and Jetpack Compose](https://developer.android.com/develop/ui/compose/state)
- [Lazy lists and grids](https://developer.android.com/develop/ui/compose/lists)
- [Composition tracing](https://developer.android.com/develop/ui/compose/tooling/tracing)
- [Using Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)
- [Using Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)
- [Compose Runtime 1.11.4：`Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt)
- [Compose Runtime 1.11.4：`RecomposeScopeImpl.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt)
- [Compose Runtime 1.11.4：`DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt)
- [Compose Runtime 1.11.4：`SnapshotFlow.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt)
- [AOSP Android 17：ART `heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)
- [AOSP Android 17：ART `heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)
- [Android 17 Kernel：`android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/)
- [Compose Runtime 1.12.0：`Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt)
- [Compose Runtime 1.12.0：`ComposeRuntimeFlags.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt)
- [Compose Runtime 1.12.0：`RecomposeScopeImpl.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt)
- [Compose Runtime 1.12.0：`DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt)
- [Compose Runtime 1.12.0：`SnapshotIntState.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt)
- [Compose Runtime 1.12.0：`SnapshotFlow.kt`](https://android.googlesource.com/platform/frameworks/support/+/963bf914f78b389bdddef0da7f36bee19d897274/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt)
