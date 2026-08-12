---
title: "Jetpack Compose 内存分配与 GC 影响"
chapter: "23.8"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [compose, memory, gc, allocation, slottable, recomposition]
related_chapters: ["4.8", "7.7", "10.6", "22.3", "23.5"]
last_verified: "2026-06-19"
last_verified_against: "androidx-main (Compose 1.8.x) / AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: research
    path: "DeepResearch/2026-06-19-jetpack-compose-memory-churn-source-analysis.md"
  - type: official
    path: "https://developer.android.com/jetpack/compose/performance"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动？.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
consolidated_from:
  - "src/part5-app/ch23-memory-practice/12-compose-memory-allocation-gc.md"
---

# Jetpack Compose 内存分配与 GC 影响

## 范围与版本

讨论范围是 Android 上的 Compose Runtime、应用 Java Heap 与 ART GC。平台源码以 Android 17 / API 37 / `android-17.0.0_r1` 为准，内核基线为 `android17-6.18-2026-06_r6`。Compose 是独立发布的 Jetpack 库，这里使用 2026 年 7 月的稳定版 Compose Runtime 1.11.4，并把对应 AndroidX 提交 `854220f44ea8ea80fee824a6c5a045f39bede289` 作为源码锚点。

Compose 1.12.0-beta02 已发布，但仍是 beta。这里只在版本演进处说明其中与内存有关的修复，不用 beta 行为替代稳定版结论。

处理 Compose 内存问题时，先区分两种症状：

- 存活对象持续增加：常见于 Composition 没有按宿主生命周期释放、协程或监听器存活过久、状态所有者范围过大、View 与 Compose 互相持有。
- 短命对象分配速率过高：常见于组合阶段反复排序、映射、格式化，频繁重建输入对象，或在高频状态变化中执行不必要的组合。

重组表示 Compose 重新执行一部分 UI 描述。它不保证发生对象分配，也不保证创建新的 `RecomposeScopeImpl`。定位时要分别观察重组、allocation 和 GC，不能用其中一项替代另外两项。

## Compose Runtime 会长期持有什么

一份活跃 Composition 至少要保存组合结构、`remember` 的值、重组范围、状态观察关系和待应用的变更。Compose Runtime 1.11.4 的源码给出了几个重要边界。

### Slot storage 不是固定实现

Compose 1.11.4 同时包含 gap-buffer 与新的 link-buffer slot storage。`CompositionImpl.createSlotStorage()` 根据 `ComposeRuntimeFlags.isLinkBufferComposerEnabled` 选择实现，见稳定提交中的 [`Composition.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/Composition.kt)。

[`ComposeRuntimeFlags.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/ComposeRuntimeFlags.kt)显示，1.11.4 中 `isLinkBufferComposerEnabled` 默认仍为 `false`，新实现是实验选项。AndroidX 的 [Compose Runtime 1.11 发布说明](https://developer.android.com/jetpack/androidx/releases/compose-runtime)指出，新实现的目标是减少删除、移动和重排组合内容时的数组复制。

因此：

- 未启用实验标志的 1.11.4 应按 gap-buffer 分析；
- 开启标志的应用要按 link-buffer 分析；
- heap dump 中的内部类名和引用形态可能不同；
- 不应给所有 Compose 版本套用固定的 SlotTable 字节数或扩容次数。

Slot storage 持有 remembered values 和组合结构。Composition 被宿主继续引用时，里面的值也会继续存活。看到 SlotTable 或 LinkTable 出现在引用链中时，应沿 dominator 向上查找 Activity、Fragment view、`ComposeView`、Navigation destination、Recomposer 或长期协程，内部表结构通常只是持有路径中的一环。

### `RecomposeScopeImpl` 会复用

稳定版 [`RecomposeScopeImpl.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/RecomposeScopeImpl.kt)中，`trackedInstances` 与 `trackedDependencies` 初始为 `null`，读到状态或派生状态后才创建。`release()` 会清空 owner、追踪集合和重启 block。

重组时已有 scope 可以继续使用。代码中的 `updateScope()` 只替换重启 block，不能据此推导“每次重组创建一个 scope”。Lambda 是否产生新对象还受 Compose Compiler 生成代码与 Strong Skipping 影响。

[Strong Skipping 官方说明](https://developer.android.com/develop/ui/compose/performance/stability/strongskipping)记录了两条规则：

- Kotlin 2.0.20 起默认启用 Strong Skipping；
- restartable composable 即使带不稳定参数也可以被跳过，composable 内部的 Lambda 会自动 memoize。

不稳定参数使用引用相等比较，稳定参数使用对象相等比较。调用方每次构造新 `List`、新 UI model 或新 Lambda capture，仍可能让比较失败。优化对象应是输入身份与数据流，而不是统计源码里有多少个 Lambda 表达式。

### Snapshot record 在写入时演进

`MutableState` 与 `derivedStateOf` 都基于 Snapshot state record，但“切换一次 snapshot 就为所有 state 新建一条 record”并不成立。写入需要可写 record；读取会选择当前 snapshot 可见的 record。并发 snapshot、写入频率与 record 复用共同决定对象数量。

Compose Runtime 1.11.4 的 [`DerivedState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/DerivedState.kt)显示，`ResultRecord` 保存 dependencies、result 和用于有效性判断的 hash。结果与 mutation policy 判定等价时，实现可以更新当前 record 的依赖信息；结果变化时才申请可写 record。不能把每一帧或每次 snapshot apply 直接换算成一个 `ResultRecord`。

## 哪些分配值得优先处理

### 组合阶段的集合加工与格式化

Composable body 可能因状态变化多次执行。排序、`map`、字符串拼接、解析和对象适配如果直接放在 body 中，也会重复执行。下面的代码用于把排序结果缓存到 Composition，并给 Lazy list 提供稳定身份。

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

`remember` 在 key 的比较结果不变时返回已保存值；key 变化后重新计算。更重的数据加工可以移到 ViewModel 或数据层。`contacts` 若在原对象上原地修改，Compose 和 `remember` 都可能无法观察内容变化；推荐把 UI state 暴露为新的不可变列表实例，或使用能通知写入的 snapshot collection。每次重组创建 `contacts.toList()` 作为 key 会引入一份新列表，不能修正原地修改的数据模型。

### 原始类型 State

Compose Runtime 提供 `mutableIntStateOf`、`mutableLongStateOf`、`mutableFloatStateOf` 和 `mutableDoubleStateOf`。下面的代码用于让高频计数状态走原始类型接口。

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

稳定版 [`SnapshotIntState.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotIntState.kt)中的 `SnapshotMutableIntStateImpl` 用 `IntStateStateRecord` 保存 `Int`，`intValue` 直接读写原始类型。委托运算符也访问 `intValue`。这能避免通用 `MutableState<Int>` 路径的自动装箱，但收益仍要在 allocation recording 中验证；少量低频状态无需机械替换。

### Lambda 与 Modifier

Strong Skipping 会 memoize composable 内的 Lambda，但以下代码仍可能产生额外分配或失去跳过机会：

- 在调用 composable 前反复构造新的 UI model 或集合；
- 明确使用 `@DontMemoize`；
- 在非 composable 热路径中创建捕获 Lambda；
- 每次执行 body 都构造复杂 Modifier 链或中间集合；
- 参数对象的引用每次变化，使不稳定参数的 `===` 比较失败。

Compose Compiler 报告能说明函数是否 restartable、skippable，以及参数稳定性。它不能给出运行时对象分配数量。编译器报告与 allocation recording 应配合使用。

## `derivedStateOf` 与 `snapshotFlow`

### `derivedStateOf` 负责压缩 UI 失效

`derivedStateOf` 适合“输入变化很频繁，UI 只关心较少的结果变化”。滚动位置每次变化，按钮只关心是否已经离开列表顶部，就是典型场景。

下面的代码用于把高频滚动状态压成一个 Boolean，并把该对象保存在 Composition 中。

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

只要 `showButton` 的结果没有变化，读取它的 composable 不需要因每个滚动更新而重组。`derivedStateOf` 自己要维护依赖与缓存，因此普通字符串拼接、两个低频状态的简单组合、每次输入变化都会产生新输出的计算，通常直接计算更清楚。

Compose Runtime 1.12.0-beta01 的发布说明记录了一项潜在内存泄漏修复：未正确 remember 的 `derivedStateOf()` 在 forward writes 场景中可能被 Composition 保留到 dispose。稳定版 1.11.4 尚未包含这项 beta 修复。可执行的版本边界是：

- composable 内创建 `derivedStateOf` 时使用 `remember`；
- 不把 beta 修复描述成稳定版已有行为；
- 怀疑该问题时，在 heap dump 中检查 `DerivedSnapshotState` 到 Composition 的引用链，再决定升级验证；
- 不用 `remember(list, index)` 代替对 `SnapshotStateList` 元素的观察，因为列表身份不变时缓存可能返回旧数据。

### `snapshotFlow` 负责把 State 转成事件流

`snapshotFlow` 收集 block 读取的 snapshot state，相关 state apply 后重新运行 block，并按结果是否相等决定是否 emit。稳定版 [`SnapshotFlow.kt`](https://android.googlesource.com/platform/frameworks/support/+/854220f44ea8ea80fee824a6c5a045f39bede289/compose/runtime/runtime/src/commonMain/kotlin/androidx/compose/runtime/SnapshotFlow.kt)会注册 apply observer、维护订阅集合，并在 Flow 退出时取消订阅和 dispose 内部 manager。

下面的代码用于把列表位置变化交给分析事件；该任务会随 `LaunchedEffect` 离开 Composition 或 key 变化而取消。

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

把 `snapshotFlow` 放在 `LaunchedEffect` 中不会天然泄漏。风险来自外部作用域比 UI 所有者存活更久、effect key 选择错误、回调捕获 Activity/View，或重复启动未受管理的收集任务。heap dump 中只看到 Snapshot 类也不足以定案，要继续找协程 Job、Flow collector 和宿主生命周期。

## Lazy layout 的 key 到底解决什么

Lazy layout 默认按位置识别 item。数据重排后，同一个业务对象的位置变化，位置身份会让 remembered state 无法随业务对象移动。[Lazy list 官方文档](https://developer.android.com/develop/ui/compose/lists)建议提供稳定且唯一的 key，使 item state 在重排时跟随 item。

key 的主要价值包括：

- 数据插入、删除和排序后保持 item 身份；
- 减少无关 item 的重组；
- 让 `rememberSaveable` 状态在符合条件时恢复。

key 不能保证滚出屏幕的所有节点永久常驻，也不能单独消除 item 内部对象分配。用于 `rememberSaveable` 时，key 类型还要能由 `Bundle` 支持。业务稳定 ID 是优先选择；只有列表内容和顺序永远不变时，位置才可能满足身份语义。

## View 与 Compose 混合时的生命周期

### `ComposeView` 应跟随正确的 LifecycleOwner

每个 `ComposeView` 都有自己的 Composition 和宿主 View 引用。Fragment 的 View 销毁后，如果 Composition 仍由更长生命周期持有，remembered values、effects 和 UI tree 会继续存活。

下面的代码用于让 Fragment 中的 Composition 随 view lifecycle 销毁。

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

[Compose in Views 官方文档](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views)把 `DisposeOnViewTreeLifecycleDestroyed` 列为 Fragment View 的适用策略。普通 View 场景的默认策略是 `DisposeOnDetachedFromWindowOrReleasedFromPool`。选择策略时要按宿主类型判断，不要给所有 `ComposeView` 写同一个释放规则。

### `AndroidView.factory` 不需要额外 `remember`

`AndroidView` 的 `factory` 用于创建 View，`update` 在 View 创建后执行，也会在读取的 state 变化时再次执行。把 View 另存进 `remember` 可能制造第二个所有者，增加生命周期错误。

Lazy list 中需要复用 View 时，应使用带 `onReset` 的 overload。下面的代码用于在复用前清理上一条 item 的瞬时状态，并在不再复用时释放资源。

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

[Views in Compose 官方文档](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose)说明，`onReset` 必须非空才会启用 Lazy 容器中的 View 复用。`update` 应是幂等的；监听器若在每次 update 中注册，也要先替换或移除旧监听器。

混合页面的 heap dump 应同时检查 View tree 与 Composition。常见 dominator 包括 Fragment view binding、adapter、listener、`AndroidView` 内的 WebView/播放器/地图、Navigation back stack 和长生命周期 ViewModel。

## Android 17 中分配如何触发 ART GC

Compose Runtime 对象位于应用 Java Heap。Android 17 的 [`heap-inl.h`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap-inl.h)显示，Java 对象分配会更新已分配字节；并发 collector 下，`ShouldConcurrentGCForJava()` 根据当前配置检查分配阈值或 time-based GC 条件。需要 GC 时，分配路径在允许线程挂起后调用 `RequestConcurrentGCAndSaveObject()`。

[`heap.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/gc/heap.cc)中的 `ConcurrentGCTask` 由 task processor 调度。GC 名称包含“concurrent”不表示应用线程完全没有暂停；root 扫描、checkpoint、对象移动与系统调度仍可能影响帧。

Android 17 同时支持 generational CC 与 generational CMC。是否启用还要经过 collector、read barrier 或 userfaultfd 能力、`-Xgc` 选项、ART feature flag 和 DeviceConfig 属性判断。源码中的属性默认值不能替代设备实测。不要写成“所有 Android 17 应用都固定使用分代 CMC”。

Compose 分配与卡顿之间需要建立证据链：

1. Frame Timeline 出现 missed frame 或长帧；
2. Compose tracing 显示对应窗口执行了哪些 composable；
3. allocation recording 证明该窗口分配速率或特定类型增加；
4. ART GC slice、线程状态和暂停区间与长帧重叠；
5. 修正分配后，同一设备与场景的长帧和 GC 数据同步改善。

只有 GC 与帧出现在相近时间，尚不能证明 GC 是主因。重组中的业务计算、measure/layout、图片解码和主线程 I/O 都可能与 GC 同时发生。

## 诊断与回归流程

### 用 release 构建测性能

Debug 构建、Layout Inspector、method tracing 和 allocation recording 都会改变执行与分配行为。[Compose 稳定性诊断文档](https://developer.android.com/develop/ui/compose/performance/stability/diagnose)要求编译器报告使用 release build；页面性能回归也应使用 release-like、可 profile 的构建，并保持 R8、Baseline Profile 和依赖版本一致。

下面的 Gradle 配置用于输出 Compose Compiler 稳定性报告和模块指标。

```kotlin
composeCompiler {
    reportsDestination = layout.buildDirectory.dir("compose_compiler")
    metricsDestination = layout.buildDirectory.dir("compose_compiler")
}
```

报告中的 `restartable`、`skippable` 和参数稳定性用于筛选可疑 composable。它们不是优化目标清单：某个函数不可跳过但调用很少，可能没有用户可见成本；把不满足契约的类型强行标成 `@Stable` 会造成 UI 不更新。

### 四类工具回答四个问题

| 工具 | 回答的问题 | 使用限制 |
| --- | --- | --- |
| Compose Compiler reports | 编译器如何判断函数与参数 | 没有运行时次数和 allocation |
| Layout Inspector | 当前会话中哪些 composable 重组或被跳过 | 调试工具有观测成本 |
| Perfetto + Compose tracing | 重组、布局、绘制、线程与 GC 的时间关系 | 需要固定场景和 release-like 构建 |
| Allocation recording / heap dump | 哪些类型在分配、哪些对象被谁持有 | recording 成本高；heap dump 是单点状态 |

[Composition tracing 文档](https://developer.android.com/develop/ui/compose/tooling/tracing)说明，Macrobenchmark 可以产出带 Compose tracing 的系统 trace。滚动、页面切换和启动应写成可重复的 Macrobenchmark；Memory Profiler 用于专项归因，不作为唯一回归基线。

### 先判断 churn，再判断 leak

建议按以下顺序检查：

1. 用 `dumpsys meminfo` 和 Java Heap 曲线确认水位与增长形态；
2. 用 allocation recording 找高频类型与调用栈；
3. 用 heap dump 查看离开页面后仍存活对象的 dominator；
4. 用 Perfetto 对齐 Compose、frame 与 GC；
5. 修改一处后复跑相同操作，不同时改状态模型、列表与图片策略。

页面退出后仍存在一份 Composition 不一定异常，Navigation 可能保留 destination 状态。要结合 back stack、宿主 lifecycle 与产品预期判断。相同 destination 不断累积、旧 Fragment view 已销毁却仍支配 Composition，才有明确的泄漏方向。

## 版本边界

| 版本 | 相关变化 |
| --- | --- |
| Kotlin 2.0.20+ | Strong Skipping 默认启用；不稳定参数按引用相等判断，composable 内 Lambda 自动 memoize |
| Compose Runtime 1.11.4 | Jetpack 稳定锚点；link-buffer 实现存在但默认关闭 |
| Compose Runtime 1.12.0-beta01/02 | beta 发布说明记录 `derivedStateOf` forward writes 潜在保留问题修复；不能当作 1.11.4 已有修复 |
| Android 17 / API 37 | ART 源码锚点为 `android-17.0.0_r1`；GC collector 与 generational 模式仍受运行时和设备配置影响 |

Compose Multiplatform 在不同目标上使用不同运行时与内存管理器。这里的 GC、heap dump 和 Android View 互操作结论只适用于 Android；不能把 Desktop/JVM、iOS 或 Wasm 的对象大小与 GC 行为直接移植过来。

## 小结

Compose 内存治理要把“被长期持有”和“分配过快”分开。Slot storage、RecomposeScope 和 Snapshot record 是运行时结构，看到类名不等于发现泄漏。泄漏要沿 dominator 找宿主生命周期，churn 要用 allocation stack 证明。

对应用代码，优先处理组合阶段的重复计算、每次创建的新输入对象、错误的状态所有者、未管理的协程和 View 资源。`remember`、`derivedStateOf`、primitive State、Lazy key 与 Strong Skipping 各有明确语义，不能互相替代。ART GC 的触发与 collector 配置以 Android 17 源码和设备 trace 为准，不使用固定堆大小、每帧分配量或 GC 次数作通用结论。

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
