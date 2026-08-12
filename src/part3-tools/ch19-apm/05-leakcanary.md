---
title: "LeakCanary"
chapter: "19"
section: "19.05"
status: finalized
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-08"
last_verified_against: "LeakCanary 2.14 fundamentals, changelog 2.6 ServiceWatcher, recipes, UI tests / leakcanary-android-instrumentation"
confidence: medium
tags: [apm, memory, leak-detection, debug-tools, shark]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://square.github.io/leakcanary/"
  - type: official
    path: "https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/"
  - type: official
    path: "https://square.github.io/leakcanary/changelog/"
  - type: official
    path: "https://square.github.io/leakcanary/recipes/"
  - type: official
    path: "https://square.github.io/leakcanary/ui-tests/"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
---

# LeakCanary

## 先确定工具定位和版本基线

LeakCanary 用于回答一个具体问题：某个 Java/Kotlin 对象的生命周期已经结束，为什么它仍能从 GC Root 经强引用到达？它会在开发或测试设备上观察对象、抓取 Java heap、用 Shark 计算引用路径，再把可疑引用缩小到便于回查代码的范围。

它不负责线上内存平台的全部职责。几类工具的分工如下：

| 工具 | 擅长回答的问题 | 不能单独证明什么 |
|---|---|---|
| LeakCanary | 已知生命周期对象为何没有回收；哪条强引用路径保留了它 | native 内存为何上涨、线上发生率、整机内存压力 |
| Android Studio Memory Profiler | 分配、heap dump、对象图和本地交互分析 | 线上分布和自动生命周期判定 |
| Perfetto | PSS/RSS、GC、调度、FrameTimeline、heap profiling 等时间线 | 某个 destroyed Fragment 被哪条 Java 引用长期保留 |
| KOOM / APM | 线上版本、机型、页面分布和受控样本 | 本地代码修改是否已经切断指定引用链 |

截至 2026-07-25，版本选择要分稳定线和预览线：

| 版本 | 发布状态 | 上游构建边界 | 使用建议 |
|---|---|---|---|
| `2.14` | 最新稳定版，tag commit `8d29638ccf25e15d84b0119b6617f0069bc0b2d8` | minSdk 14、compileSdk 34 | 作为常规 Debug / QA 接入基线 |
| `3.0-alpha-9` | 2026-06-25 发布的预览版，tag commit `bac94a74fa87ed807c31a42b4d495bbfdcede33a` | minSdk 26、compileSdk 35 | 只在隔离分支评估 heap growth 等新能力 |

Maven Central 把 `3.0-alpha-9` 标成 latest/release，只表示仓库元数据中的最新产物，并没有把 alpha 变成稳定版。2.14 也没有以 compileSdk 37 构建，所以下文会把“源码路径在 Android 17 仍存在”和“API 37 真机已经通过回归”分开表述。

稳定版最小接入只需要把完整能力放进 debug 变体：

```kotlin
dependencies {
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.14")
}
```

依赖通过 manifest 中的私有 `ContentProvider` 在主进程自动安装 watcher，不需要在 `Application` 中再调用初始化。2.14 另有基于 AndroidX Startup 的替代 artifact，不能把两条安装路径混写。若工程有 QA、internal 等自定义变体，应把依赖放到对应 configuration，避免依赖名称写着 debug、产物却被合进生产包。

## 从 watch 到 leak trace 的源码路径

“对象被保留”“触发 heap dump”“确认泄漏”是三个阶段，不能合成一句“5 秒后发现泄漏”。

1. 生命周期 watcher 在预期终点调用 `expectWeaklyReachable()`。`ObjectWatcher` 创建带唯一 key 的 `KeyedWeakReference`，并把它关联到 `ReferenceQueue`。这个弱引用不会让被观察对象继续存活。
2. 2.14 的默认 `retainedDelayMillis` 是 5 秒。延迟任务执行时，`ObjectWatcher` 先从 `ReferenceQueue` 移除已经变为 weakly reachable 的对象；仍在 map 中的对象被标记为 retained，并通知 LeakCanary。
3. retained 只表示“超过观察窗口仍可达”，还不是 heap 分析结论。`HeapDumpTrigger` 在后台线程检查 retained 数量，显式执行一次 `Runtime.gc()`、等待引用入队并运行 finalization，然后重新计数。
4. 应用可见时，默认要达到 5 个 retained object 才 dump；应用不可见后，会等待一个 `retainedDelayMillis`，随后 1 个 retained object 也足以触发。用户点通知还可以主动请求 dump。
5. dump 前会再检查开关、调试器状态、最近一次 dump 等条件。默认 `AndroidDebugHeapDumper` 调用公开的 `Debug.dumpHprofData()` 写出 `.hprof`。
6. Shark 在 heap 中找到带 key 的弱引用对象，计算从 GC Root 到目标对象的最佳强引用路径，运行 `ObjectInspector` 与 `ReferenceMatcher`，计算 retained size，并按 suspect reference 生成 signature、归并同源报告。

这段顺序有两个诊断含义：

- 页面退出 1 秒后对象还活着很常见，不能拿瞬时存活当泄漏。
- `retainedObjectCount > 0` 是候选信号。只有 dump 中仍存在目标对象并找到保留路径，才有可供修复的 leak trace。

阈值用于减少频繁冻结 UI，不是“少于 5 个就没有泄漏”。调试时把 App 切到后台，或在测试中调用官方 assertion，比为了快速出报告长期把前台阈值改成 1 更稳妥。

## 默认观察对象与依赖条件

2.14 的 `AppWatcher.appDefaultWatchers()` 安装四组 watcher：

| watcher | 观察终点 | 依赖和例外 |
|---|---|---|
| `ActivityWatcher` | `Activity.onDestroy()` 回调完成 | 使用 `Application.ActivityLifecycleCallbacks` |
| `FragmentAndViewModelWatcher` | Fragment `onDestroy()`、fragment view `onDestroyView()`、ViewModel `onCleared()` | AndroidX 路径只在相关类存在时安装；2.14 还兼容 support Fragment；framework Fragment 只覆盖 API 26+ |
| `RootViewWatcher` | root view 从 WindowManager 脱离 | Activity root 已由 ActivityWatcher 覆盖；PopupWindow root 不观察；Dialog root 默认不观察；Toast、Tooltip 和未知类型会观察 |
| `ServiceWatcher` | `Service.onDestroy()` 后 system server 收到 `serviceDoneExecuting()` | 依赖 framework 私有字段、消息号和 Binder 代理；反射失败会记录日志并放弃 Service 自动观察 |

“默认观察 View”不能简写成“所有 detached View 都会被扫一遍”。Fragment view 来自 Fragment 生命周期；root view 来自 Curtains 对 WindowManager root 的监听；普通子 View 没有统一生命周期，业务仍要在明确终点自行观察。

Service 也是高版本验证重点。2.14 的 `ServiceWatcher` 会反射 `ActivityThread.mH`、`mServices`、`Handler.mCallback` 和 `ActivityManager.IActivityManagerSingleton`，并识别 `STOP_SERVICE = 116`。Android 17 `android-17.0.0_r1` 中这些名字和停止流程仍存在，但它们都不是应用 SDK API。OEM 修改、hidden API 策略或后续平台改动都可能让 watcher 安装失败；测试包启动后要检查 Logcat 是否出现 `Could not watch destroyed services`，关键 Service 可在 `onDestroy()` 末尾再做业务侧观察。

## 自定义观察要放在明确的终点

播放器控制器、地图会话、Presenter、Dagger component 和业务 scope 都可能有自己的 `release()` / `close()`。观察调用要放在资源清理完成后，因为这时对象的所有者理应尽快放弃强引用。

下面的例子用 2.14 推荐的 `expectWeaklyReachable()`，避免继续使用已弃用的 `watch()`：

```kotlin
class PlayerController {
    private var released = false

    fun release() {
        if (released) return
        released = true

        stopPlayback()
        unregisterCallbacks()
        AppWatcher.objectWatcher.expectWeaklyReachable(
            watchedObject = this,
            description = "PlayerController.release() completed"
        )
    }
}
```

这段代码观察的是 `PlayerController` 本身。若页面或播放器管理器在 `release()` 后仍保存 controller，5 秒后它会成为 retained 候选；若调用方按约定清掉引用，弱引用会进入 `ReferenceQueue`，观察记录自行移除。

ObjectWatcher 2.14 没有为每次观察返回“取消句柄”。不要用全局 `clearWatchedObjects()` 掩盖业务生命周期变化；对象可能复用、进入池或重新被 owner 接管时，应等到不可逆的终点再观察。测试框架为了隔离用例可以清理旧记录，业务代码不应借此消除报告。

降低噪声还要遵守三条规则：

- 不观察 Application、全局 cache、进程级 repository 等设计上常驻的对象。
- description 写“哪个生命周期终点已经发生”，不要只写类名。
- teardown 本身有异步完成条件时，在完成回调后观察；不要用随意增加 sleep 的方式掩盖 ownership 不清。

## leak trace 要逐行读

Leak trace 是 GC Root 到 retained object 的强引用路径，不是线程调用栈。文本报告中：

- `GC Root` 说明遍历起点，常见类型有 thread local、Java thread、system class 和 native reference。
- `├─` / `╰→` 是路径上的对象；`↓` 是指向下一对象的字段、数组元素或 Java local。
- `Leaking: NO / YES / UNKNOWN` 来自 Shark 的对象状态推断。
- `~~~` 标出尚未被排除的 suspect reference。它表示“应继续查的引用”，不等于工具已经定位到一行错误代码。
- `retainedHeapByteSize` 估算移除该泄漏后可回收的字节数，还可计入部分与 Java 对象关联的 native 大小，例如 Android Bitmap。它不能覆盖通用 native heap；共享对象图和运行时状态也会限制数值的解释范围。
- signature 由 suspect reference 组合计算，用来把同一原因的多个实例归为一组。

下面是一条经过压缩、但保留 LeakCanary 文本结构的 Fragment view 泄漏：

```text
┬───
│ GC Root: System class
│
├─ com.example.AnalyticsDispatcher class
│    Leaking: NO (a class is never leaking)
│    ↓ static AnalyticsDispatcher.callbacks
│                                 ~~~~~~~~~
├─ java.util.ArrayList instance
│    ↓ ArrayList.elementData
│                ~~~~~~~~~~~
├─ java.lang.Object[] array
│    ↓ Object[].[2]
│               ~~~
├─ com.example.HomeFragment$callback instance
│    ↓ HomeFragment$callback.this$0
│                            ~~~~~~
├─ com.example.HomeFragment instance
│    ↓ HomeFragment.binding
│                   ~~~~~~~
├─ com.example.HomeFragmentBinding instance
│    ↓ HomeFragmentBinding.rootView
│                         ~~~~~~~~
╰→ androidx.constraintlayout.widget.ConstraintLayout instance
     Leaking: YES (ObjectWatcher was watching this because
     HomeFragment received Fragment#onDestroyView() callback)
```

逐行阅读时按下面的顺序收敛：

1. 末尾的 root view 已经过了 `onDestroyView()`，因此“应该回收”的前提成立。
2. `HomeFragment.binding` 说明 Fragment 在 view 销毁后仍持有 binding；Fragment 留在 back stack 时，这条引用会拖住整棵 view tree。
3. `callback.this$0` 是匿名内部类对 Fragment 的隐式引用。
4. 静态 `AnalyticsDispatcher.callbacks` 是长生命周期 owner，集合元素没有注销，使 callback、Fragment 和 binding 连续可达。
5. 修复不能停在“把某个引用改成 WeakReference”。应在 `onDestroyView()` 解除 dispatcher 注册并清空 binding，使 owner 与生命周期对齐。

GC Root 只告诉你为何整条链始终可达，不一定是业务修复点。上例若盯着 system class 或 ClassLoader 处理，就会绕开未注销 callback 这个责任边界。

## 三个能从代码走到 trace 的案例

### Fragment：binding 活得比 view 久

Fragment 可以留在 back stack，而它的 view 已在 `onDestroyView()` 销毁。下面的 teardown 同时断开 RecyclerView 与 adapter、Fragment 与 binding：

```kotlin
class FeedFragment : Fragment(R.layout.feed) {
    private var _binding: FeedBinding? = null
    private val binding: FeedBinding get() = requireNotNull(_binding)
    private val feedAdapter = FeedAdapter()

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        _binding = FeedBinding.bind(view)
        binding.list.adapter = feedAdapter
    }

    override fun onDestroyView() {
        binding.list.adapter = null
        _binding = null
        super.onDestroyView()
    }
}
```

典型 trace 会经过 `FragmentManager` 或 Fragment store 到仍存活的 Fragment，再从 `_binding` 到 root view。`_binding = null` 切断主要引用；`list.adapter = null` 还会解除 RecyclerView 注册在 adapter 上的 observer，避免 adapter 从另一侧保留旧 RecyclerView。

### RecyclerView：全局 listener 经 adapter 拖住页面

Adapter 常被当作“纯数据对象”，但 `AdapterDataObservable`、回调 lambda 和业务 listener 都可能形成反向引用。下面的 adapter 明确暴露 teardown，并由 view owner 调用：

```kotlin
class FeedAdapter(
    private val dispatcher: PlaybackDispatcher
) : RecyclerView.Adapter<FeedViewHolder>() {

    private val playbackListener = PlaybackListener { itemId ->
        notifyItemChanged(findPosition(itemId))
    }

    init {
        dispatcher.addListener(playbackListener)
    }

    fun dispose() {
        dispatcher.removeListener(playbackListener)
    }
}

override fun onDestroyView() {
    binding.list.adapter = null
    feedAdapter.dispose()
    _binding = null
    super.onDestroyView()
}
```

泄漏路径通常是 `PlaybackDispatcher` → listener → adapter → `AdapterDataObservable` → RecyclerView observer → RecyclerView → Activity。只清空 Fragment binding 仍可能留下 dispatcher 这一侧的强引用，所以 listener 的注册和注销必须成对。

`onDetachedFromRecyclerView()` 不一定等同于 adapter 的永久销毁：同一个 adapter 可能被临时拆下再挂回。是否在该回调释放，要由组件的复用约定决定；页面级 adapter 用显式 `dispose()` 更容易审计。

### Coroutine / Flow：collector 绑定错生命周期

Fragment 的 `lifecycleScope` 跟 Fragment 实例一起存活，可能跨过 `onDestroyView()`。collector 若捕获 binding，就会在 view 已销毁后继续保留旧视图。下面把收集任务绑定到 `viewLifecycleOwner`：

```kotlin
viewLifecycleOwner.lifecycleScope.launch {
    viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
        viewModel.uiState.collectLatest { state ->
            render(binding, state)
        }
    }
}
```

进入 STOPPED 时，`repeatOnLifecycle` 取消内部 collection；view lifecycle 到 DESTROYED 时，外层 scope 也会取消。对应泄漏 trace 若出现 `JobSupport`、continuation、collector lambda、Fragment 和 binding，应先检查启动 scope 与 owner，再检查 Flow 上游是否把回调或 collector 另存到全局对象。

取消 coroutine 只能终止遵守取消协议的挂起工作。阻塞 I/O、第三方 callback、`GlobalScope` 和自行保存的 listener 仍要单独 teardown；不能看到 `lifecycleScope` 就判定引用一定安全。

## 常见模式要从“谁持有谁”分析

| 模式 | 常见强引用路径 | 修复责任 |
|---|---|---|
| static / singleton | class → static field / collection → Activity、View、callback | 长生命周期 owner 不保存页面对象；只在语义允许时改存 `applicationContext` |
| Handler / Runnable | thread → MessageQueue → Message.callback → Runnable → 页面 | owner 保存自己的 Runnable，并在生命周期终点 `removeCallbacks(runnable)`；不要清掉共享 Handler 的全部消息 |
| Listener / callback | manager / SDK → listener list → lambda / anonymous class → 页面 | 注册方或 owner 成对注销，异常与提前返回路径也要覆盖 |
| Coroutine / Flow / Rx | scope / Job / subscriber → continuation / collector → View | 使用与目标资源一致的 scope；取消 subscription，并终止外部 callback |
| Adapter | dispatcher → adapter，或 adapter observable → RecyclerView | 拆 adapter、注销 observer/listener、清理缓存的 ViewHolder |
| anonymous class / lambda | callback → `this$0` / captured variable → Activity 或 Fragment | 缩小捕获对象，或在 owner 结束时解除 callback |
| Context | singleton → Activity Context → Window / View tree | 只有不需要主题、Window、页面语义时才使用 Application Context |
| Dialog / PopupWindow | manager / listener → Dialog → Window → decor view → Activity | dismiss 后解除 listener 与 owner 引用；优先让 DialogFragment 管理配置变化 |
| WebView | 页面 / JS bridge / callback → WebView，或 WebView 内部对象 → Activity | 从父容器移除，停止加载，解除 JS interface/回调，按组件约定调用 `destroy()` 并清掉 owner 引用 |

Handler 的修复最好针对本 owner 的 Runnable：

```kotlin
private val refreshRunnable = Runnable { refreshUi() }

override fun onDestroy() {
    mainHandler.removeCallbacks(refreshRunnable)
    super.onDestroy()
}
```

`removeCallbacksAndMessages(null)` 会删除同一 Handler 上其他 owner 的任务，可能把泄漏问题换成功能错误。若 Runnable 必须跨页面执行，就不要捕获 Activity、Fragment 或 View；把结果交给生命周期感知的状态 owner。

WebView 还可能持有 native 资源，LeakCanary 只能分析 Java heap 中通往 WebView 或 Activity 的引用。`WebView.destroy()` 不是所有页面都能机械套用的补丁：先停止业务回调和 JS bridge，再从 parent 移除并按产品的复用策略销毁；共享 WebView 池则需要独立的 owner 和明确的回收协议。

## Application Leak 与 Library Leak 的处置

LeakCanary 使用 `ReferenceMatcher` 识别已知第三方或 Android Framework 引用模式：

- **Application Leak**：没有命中已知库问题，LeakCanary 按应用泄漏报告；多数 suspect reference 可由应用控制，也可能是尚未收录的系统或依赖问题。默认 CI assertion 会为这类泄漏失败。
- **Library Leak**：命中已知模式，表示应用按正常 API 使用时仍受到系统或依赖 bug 影响。它仍在占内存，只是修复权可能不在应用侧。

处理 Application Leak 时，要找到引用的 owner、注册点、预期解绑时刻和遗漏分支，随后补测试。不要通过给字段加 `ReferenceMatcher` 把自家问题改名为 Library Leak。

Library Leak 按影响处理：

- 记录 signature、系统版本、厂商、依赖版本、发生场景和 retained size。
- 查上游 issue 与修复版本，做升级、降级或最小规避的 A/B 验证。
- 高流量页面或大 retained size 即使来自系统，也要评估生命周期顺序、功能降级或隔离进程。
- 低占比且无法规避的问题可以暂缓，但 matcher 要有 issue、owner、适用版本和删除条件。

`referenceMatchers` 会改变分类和路径搜索，不等同于“不 dump”。默认 instrumentation reporter 只对 Application Leak 抛错，因此错误的 matcher 会让 CI 绿灯；这也是白名单必须评审和定期过期的原因。

## Android 17 / API 37 验证边界

Android 17 `android-17.0.0_r1` 的 `android.os.Debug.dumpHprofData(String)` 仍是公开方法，内部继续调用 `VMDebug.dumpHprofData()`。LeakCanary 2.14 与 3.0-alpha-9 的默认 `AndroidDebugHeapDumper` 都直接使用这条 API，因此基础 Java heap dump 路径没有依赖 ART 私有 C++ 符号。

Android 17 的 platform 源码也保留了 2.14 `ServiceWatcher` 所依赖的字段和停止消息流程：

- `ActivityThread.mH`、`mServices` 和 `H.STOP_SERVICE = 116`
- `ActivityThread.handleStopService()` 在 `Service.onDestroy()` 后调用 `IActivityManager.serviceDoneExecuting()`
- `ActivityManager.IActivityManagerSingleton`
- `Handler.mCallback`

这只验证 AOSP tag 的结构，没有给反射调用提供兼容承诺。API 37 验收至少覆盖 Activity、AndroidX Fragment view、ViewModel、root view、Service、前后台阈值、通知权限、heap dump、Shark 分析和结果页；Service 要单列 watcher 安装日志。

官方仓库和发布 AAR 没有 `.so`，LeakCanary 自身没有 16 KB ELF 对齐问题，也不依赖 `android17-6.18-2026-06_r6` 内核锚点。这个结论不能外推到被测 App：App 自带的 native 库仍要独立检查 16 KB；malloc、GPU、驱动或 native cache 上涨也不会因为 Java Hprof 可分析而自动出现完整根因。

2.14 用 compileSdk 34 构建，3.0-alpha-9 用 compileSdk 35 构建。它们可以被 API 37 App 依赖，不表示上游已经覆盖 targetSdk 37、OEM ROM 和 API 37 全套回归。团队应在自己的 compileSdk/targetSdk 37 internal 变体上保留上述测试集。

## Release 边界：计数、分析和上传是三件事

生产包的选择不能只看 artifact 名称：

| 依赖 / 能力 | 行为 | 风险边界 |
|---|---|---|
| `leakcanary-android:2.14` | 自动观察、dump、Shark 分析、通知和结果 UI | 官方要求用于 debuggable 构建；非 debuggable 初始化默认会崩溃，防止误带 |
| `leakcanary-object-watcher-android:2.14` | 自动安装 watcher，可读取 `retainedObjectCount` | 只有候选计数，没有引用链；5 秒窗口和生命周期噪声不能当线上泄漏率 |
| `leakcanary-android-release:2.14` | 提供生产环境 heap analysis API | 官方标为 experimental，需要自行设计触发、取消、脱敏、存储和上报 |

完整 heap dump 会暂停被测进程，并把当时 Java heap 写入文件。文件可能包含字符串、URL、token、页面内容、业务 ID、集合元素和类结构；体积也可能达到数十或数百 MB。Shark 分析还会占用 CPU、内存、I/O 和电量。`stripHeapDump` 把 primitive array 内容归零，能降低字符串等数据暴露，但不应被视为已经通过匿名化审查。

线上专项分析至少要具备：

- 服务端开关、低比例采样、设备/版本限制、冷却时间和单设备上限。
- 只在后台、熄屏或用户明确同意的诊断流程触发，并允许取消。
- 使用 app 私有且不备份的临时目录；分析结束或失败后删除 Hprof。
- 上传分析结果优先于上传原始 Hprof；字段做 allowlist，传输与存储有加密、权限和保留期限。
- 记录 dump/analysis 时长、失败率、文件大小、OOM/ANR 和电量影响，达到熔断条件立即停用。

大多数团队更适合让 KOOM、自研 APM 或 Android Vitals 提供线上入口，再回到可控的 Debug / QA 包用 LeakCanary 找引用链。生产 heap analysis 是专项能力，不应因官方存在 release artifact 就默认常开。

## 从线上信号回到本地验证

线上 OOM 或 PSS 上涨可能来自泄漏、缓存、图片、WebView、native allocator、GPU 或进程工作集变化。联动过程应保留证据分层：

1. 用 APM、Vitals 或 KOOM 确认问题版本、系统版本、机型、页面、操作序列和内存类型。
2. 在相同版本与接近的 API / OEM 环境构造可重复场景，循环进入、操作、退出页面。
3. LeakCanary 只负责 Java/Kotlin 生命周期对象：记录 signature、完整 trace、retained size 和观察 description。
4. 修复 suspect reference 后，用同一脚本重复多轮；确认旧 signature 不再出现，也没有新 signature。
5. 用 Profiler、Perfetto 或 heap diff 检查对象数与内存曲线，避免“引用链断了，但缓存或 native 内存仍上涨”。
6. 灰度上线后回看原版本维度的 OOM、PSS/RSS 和页面指标。线上指标没有改善时，重新检查问题分类，不把 LeakCanary 无报告当作所有内存问题已解决。

这种联动让线上数据回答“影响多大、在哪里发生”，让 LeakCanary 回答“哪条 Java 强引用需要修改”。

## Instrumentation 测试和 CI 门禁

UI 测试环境中，LeakCanary 检测到 JUnit 在 classpath 会关闭日常自动 dump。官方 `leakcanary-android-instrumentation` 会在 assertion 时等待主线程空闲、触发 GC、等待 retained delay，再在有 retained object 时 dump 和分析。它比手写 `sleep(6000) + retainedObjectCount == 0` 少一层时序猜测。

2.14 的测试依赖必须与 App 侧调试依赖同时存在：

```kotlin
dependencies {
    debugImplementation(
        "com.squareup.leakcanary:leakcanary-android:2.14"
    )
    androidTestImplementation(
        "com.squareup.leakcanary:leakcanary-android-instrumentation:2.14"
    )
}
```

`androidTestImplementation` 提供 assertion 和 rule，`debugImplementation` 把 watcher 与 heap 分析实现放进被测 APK。只加测试依赖并不能代替 App 侧依赖。

单个关键场景可以在页面退出后显式断言：

```kotlin
@RunWith(AndroidJUnit4::class)
class CheckoutLeakTest {

    @Test
    fun checkoutPage_doesNotLeakAfterFinish() {
        ActivityScenario.launch(CheckoutActivity::class.java).use { scenario ->
            performCheckout()
            scenario.moveToState(Lifecycle.State.DESTROYED)
        }

        LeakAssertions.assertNoLeaks()
    }
}
```

`assertNoLeaks()` 发现 retained object 后才 dump；默认 reporter 在分析得到 Application Leak 时抛出 `NoLeakAssertionFailedError`。页面必须在 assertion 前到达销毁终点，否则测试只是证明“仍在使用的页面还活着”。

要在每个成功用例末尾检查，可以使用 rule：

```kotlin
@get:Rule
val detectLeaks = DetectLeaksAfterTestSuccess(tag = "AfterTest")
```

Rule 只在测试主体成功时执行。它和 `ActivityScenarioRule` 的内外顺序会改变 assertion 发生在 Activity 销毁前还是销毁后；官方提供 `detectLeaksAfterTestSuccessWrapping()`，可在 Activity rule 两侧各检查一次，分别覆盖 Fragment/view teardown 和 Activity teardown。

CI 设计建议分三层：

- PR 门禁只跑高流量页面、复杂容器和历史高风险路径，减少设备时间与偶发异步噪声。
- nightly 扩展页面集合和循环次数，并保存完整 heap analysis 文本。
- 3.0 alpha 的 repeating heap growth 能发现“没有明确 lifecycle watch 点、但场景反复执行后对象持续增长”的问题；它仍是预览 API，不应直接替换稳定门禁。

每条失败至少保存 App commit、依赖锁文件、设备、API、ABI、场景 tag、leak signature、完整 trace、retained size 和测试次数。只有 `retainedObjectCount` 没有路径，无法用于可靠去重和归因。

### 白名单和误报维护

白名单只能覆盖有证据的系统或第三方已知问题：

1. matcher 精确到 class、field、厂商、API 和依赖版本，不用宽泛包名前缀。
2. description 关联上游 issue、内部 owner、加入日期、影响和删除条件。
3. Application 自己的 singleton、listener、adapter 泄漏不进入 matcher。
4. 临时跳过测试使用 `@SkipLeakDetection` 时写 issue 原因，并设到期检查；不要在 suite 级关闭。
5. 升级 SDK 或 Android 版本后重跑不带自定义 matcher 的基线，删除不再命中的规则。

一个 Library Leak 不会因为 CI 不失败就停止占用内存。门禁策略可以暂缓修复权不在团队手里的问题，但报告和趋势仍要保留。

## 修复后的验收清单

- 原始步骤能稳定触发旧 signature，而不是只出现一次 retained 通知。
- 修改点切断了 trace 中的 owner → target 强引用，生命周期责任可以从代码审查中说明。
- 相同设备、数据和操作循环下，旧 signature 不再出现。
- Fragment view、Activity、Service、Dialog、WebView 等各自到达预期终点后再 assertion。
- 没有用 WeakReference、扩大延时、提高阈值、清空全局 watcher 或 matcher 重分类来隐藏应用泄漏。
- retained size、对象数和 Java heap 曲线回落；涉及 native / GPU 时另有对应工具证据。
- instrumentation 用例在 API 37 设备通过，Service watcher 安装和 heap dump / Shark 分析均有日志。
- 灰度后原问题维度的线上指标改善；无改善时回到内存类型和复现假设重新判断。

## 参考源码与文档

- [LeakCanary 2.14 源码锚点](https://github.com/square/leakcanary/tree/8d29638ccf25e15d84b0119b6617f0069bc0b2d8)
- [LeakCanary 3.0-alpha-9 源码锚点](https://github.com/square/leakcanary/tree/bac94a74fa87ed807c31a42b4d495bbfdcede33a)
- [Maven Central `leakcanary-android` 版本元数据](https://repo.maven.apache.org/maven2/com/squareup/leakcanary/leakcanary-android/maven-metadata.xml)
- [LeakCanary 工作流程](https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/)
- [Leak trace 阅读与修复](https://square.github.io/leakcanary/fundamentals-fixing-a-memory-leak/)
- [LeakCanary 2.14 配置与 release retained count](https://square.github.io/leakcanary/recipes/)
- [Instrumentation 泄漏检测](https://square.github.io/leakcanary/ui-tests/)
- [实验性的 release heap analysis](https://square.github.io/leakcanary/leakcanary-for-releases/)
- [2.14 `ObjectWatcher.kt`](https://github.com/square/leakcanary/blob/8d29638ccf25e15d84b0119b6617f0069bc0b2d8/leakcanary-object-watcher/src/main/java/leakcanary/ObjectWatcher.kt)
- [2.14 `AppWatcher.kt`](https://github.com/square/leakcanary/blob/8d29638ccf25e15d84b0119b6617f0069bc0b2d8/leakcanary-object-watcher-android-core/src/main/java/leakcanary/AppWatcher.kt)
- [2.14 `MainProcessAppWatcherInstaller.kt`](https://github.com/square/leakcanary/blob/8d29638ccf25e15d84b0119b6617f0069bc0b2d8/leakcanary-object-watcher-android/src/main/java/leakcanary/internal/MainProcessAppWatcherInstaller.kt)
- [2.14 `HeapDumpTrigger.kt`](https://github.com/square/leakcanary/blob/8d29638ccf25e15d84b0119b6617f0069bc0b2d8/leakcanary-android-core/src/main/java/leakcanary/internal/HeapDumpTrigger.kt)
- [2.14 `ServiceWatcher.kt`](https://github.com/square/leakcanary/blob/8d29638ccf25e15d84b0119b6617f0069bc0b2d8/leakcanary-object-watcher-android-core/src/main/java/leakcanary/ServiceWatcher.kt)
- [Android 17 `Debug.dumpHprofData()`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Debug.java)
- [Android 17 `ActivityThread` Service 停止流程](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [Android 17 `ActivityManager.IActivityManagerSingleton`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [Android 17 `Handler.mCallback`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Handler.java)
