---
title: "内存泄漏检测与治理"
chapter: "23.1"
status: finalized
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
tags: [memory-leak, performance, optimization, governance]
related_chapters: ["4.1 Android 内存模型全景", "10.1 App 内存分析"]
last_verified: "2026-08-09"
last_verified_against: "Android 17 / API 37 / AOSP android-17.0.0_r1; Android official docs; LeakCanary docs; KOOM repository; Perfetto heapprofd docs"
reviewed_date: "2026-08-09"
reviewed_by: hermes-aiw-review-finalize-apply
last_review_finalize_at: "2026-08-09T04:25:25+08:00"
last_review_finalize_run_id: "20260809-042525-7671f9ac"
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture
- type: official
  path: https://developer.android.com/reference/android/app/ApplicationExitInfo
- type: official
  path: https://developer.android.com/studio/profile/capture-heap-dump
- type: reference
  path: https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/
- type: reference
  path: https://github.com/KwaiAppTeam/KOOM
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
---

# 23.1 内存泄漏检测与治理

内存泄漏排查最容易出现两个误区：看到内存上涨就判断“泄漏”，看到 OOM 又只盯 Java 堆。Android 应用的内存同时包含 ART managed heap、native heap、线程栈、代码与文件映射、图形缓冲区等部分。某个对象仍可达，也不等于它一定违反业务生命周期。

平台基线为 Android 17 / API 37 / `android-17.0.0_r1`，内容围绕三个问题展开：

1. 怎样证明对象已经失去业务用途，却仍被强引用链保留？
2. 怎样区分 managed heap 泄漏、native 分配增长和正常缓存？
3. 怎样把本地复现、线上信号、采集产物与回归验证连成可执行流程？

Android 17 新增的 `ProfilingManager` OOM 与 anomaly trigger 会单独说明。`ApplicationExitInfo`、LeakCanary 和 KOOM 也会放回各自适用的边界，避免把退出记录、对象保留和泄漏结论混为一谈。

## 1. 先定义“泄漏”

### 1.1 GC 可达性只回答“能不能回收”

ART 从 GC Root 出发遍历引用图。只要对象仍能通过强引用路径到达，GC 就不能回收它。常见 Root 包括：

- 活跃线程的栈和 JNI local reference；
- Java 静态字段；
- JNI global reference；
- 运行时内部持有的对象。

泄漏判断还需要业务语义：

> 对象已经越过应有生命周期，却仍被一条不必要的强引用路径保留。

因此，“GC Root 到对象有路径”只是必要证据之一。单例、进程级缓存和当前显示的 Activity 都会有 Root 路径，它们可能仍在合法生命周期内。

### 1.2 retained object 只是嫌疑对象

页面收到 `onDestroy()`、Fragment view 收到 `onDestroyView()` 或 ViewModel 收到 `onCleared()` 后，工具可以延迟观察对应对象是否仍存在。对象在一次观察窗口后仍未回收，称为 retained object 更准确。

retained object 不一定已经构成泄漏：

- GC 可能尚未发生；
- 测试框架、调试器或系统组件可能暂时持有对象；
- 异步任务可能仍在合法完成阶段；
- OEM framework 可能存在已知库泄漏。

可靠结论需要把生命周期事件、引用路径、持有者语义和重复复现放在一起。

### 1.3 OOM 也不等于 Java 对象泄漏

应用层 OOM 没有跨设备固定的 256 MB 或 512 MB 阈值。managed heap 上限随设备配置和应用属性变化；native allocation、线程创建、地址空间、图形缓冲区和 mmap 也可能触发不同形式的内存失败。

排查 OOM 时至少区分下面几类现象：

| 现象 | 优先证据 | 常见方向 |
| --- | --- | --- |
| Java/Kotlin 对象数量持续增长 | heap dump、retained size、GC Root 路径 | 生命周期引用、无界集合、缓存 |
| native heap 持续增长 | Perfetto heapprofd、native allocation stack | C/C++ 分配未释放、第三方库 |
| 线程数持续增长 | `/proc/<pid>/task`、线程 dump | Executor/Thread 未停止、线程泄漏 |
| Graphics 持续增长 | `dumpsys meminfo`、图形工具、业务资源计数 | Bitmap、Surface、Image、GPU buffer |
| RSS/PSS 上升但 Java heap 稳定 | `dumpsys meminfo`、maps/smaps、Perfetto | mmap、共享页、native/graphics |
| 分配速率过高但回落正常 | allocation recording、GC 事件 | 内存抖动，不一定是泄漏 |

`ActivityManager.getMemoryClass()` 可以读取当前设备给普通应用配置的 managed heap class，但它不是“安全缓存容量”，也不能解释 native 或图形内存。

## 2. Android 常见泄漏路径

### 2.1 长生命周期对象持有短生命周期 Context

进程级对象若只需要资源、文件或系统服务，通常保存 `applicationContext`。若功能必须依赖 Activity，例如弹出与页面绑定的窗口，就应让引用跟随页面生命周期释放。

下面的例子展示一个只需要进程级 Context 的仓库对象：

```kotlin
class ImageRepository(context: Context) {
    private val appContext = context.applicationContext

    fun cacheDir(): File = appContext.cacheDir
}
```

这里使用 `applicationContext` 是因为仓库与进程同寿命。不要把所有 Context 都改成 Application：主题、窗口、权限交互和 Activity Result 等能力仍可能要求 Activity Context。

### 2.2 监听器注册与注销不对称

常见引用链是 `process singleton -> listener collection -> Activity/Fragment/View`。注册位置和注销位置必须对应同一生命周期。

下面用 `DefaultLifecycleObserver` 把回调注册限定在可见生命周期内：

```kotlin
class SensorBinding(
    private val sensorManager: SensorManager,
    private val sensor: Sensor,
    private val listener: SensorEventListener,
) : DefaultLifecycleObserver {

    override fun onStart(owner: LifecycleOwner) {
        sensorManager.registerListener(
            listener,
            sensor,
            SensorManager.SENSOR_DELAY_NORMAL,
        )
    }

    override fun onStop(owner: LifecycleOwner) {
        sensorManager.unregisterListener(listener)
    }
}
```

这段代码的重点是所有权清楚：`LifecycleOwner` 进入 `STARTED` 时注册，离开时注销。若业务要求后台继续采集，就应把所有者提升到 Service 或进程组件，而不是省略注销。

### 2.3 延迟消息和异步任务越过页面生命周期

匿名 `Runnable`、回调 lambda 或协程都可能捕获 Fragment、View 或 Activity。问题不在“匿名类”这个语法形式，而在任务队列是否比被捕获对象活得更久。

下面的 Fragment 在 view 销毁时移除只服务于该 view 的延迟任务：

```kotlin
class ResultFragment : Fragment(R.layout.result) {
    private val mainHandler = Handler(Looper.getMainLooper())
    private val hideLoading = Runnable {
        view?.findViewById<View>(R.id.loading)?.isVisible = false
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val timeoutMs = resources
            .getInteger(R.integer.loading_timeout_ms)
            .toLong()
        mainHandler.postDelayed(hideLoading, timeoutMs)
    }

    override fun onDestroyView() {
        mainHandler.removeCallbacks(hideLoading)
        super.onDestroyView()
    }
}
```

移除回调同时避免任务操作已销毁的 view。协程场景优先选择 `viewLifecycleOwner.lifecycleScope`、`repeatOnLifecycle()` 或结构化并发，让取消关系由作用域表达。

### 2.4 Fragment view 与 Fragment 是两个生命周期

Fragment 可以留在 back stack 中，而它的 view 已被销毁。把 binding、Adapter callback、Animator 或 ComposeView 相关对象存为 Fragment 字段时，应在 `onDestroyView()` 释放 view 级引用。

不要用 `mFragmentManager == null`、`mCalled == true` 之类 framework 私有字段判断泄漏。这些字段不是应用契约，含义也不能代替 view lifecycle。

### 2.5 Compose 的 effect 没有释放外部订阅

`DisposableEffect` 适合管理必须显式注册和注销的非 Compose 资源。

下面的 composable 会在 key 变化或离开 composition 时移除监听器：

```kotlin
@Composable
fun NetworkState(source: NetworkStateSource) {
    var connected by remember { mutableStateOf(source.isConnected()) }

    DisposableEffect(source) {
        val listener = NetworkStateListener { connected = it }
        source.addListener(listener)
        onDispose { source.removeListener(listener) }
    }

    Text(if (connected) "Connected" else "Disconnected")
}
```

`remember` 只让对象跟随当前 composition 保存，并不会自动注销外部系统中的 listener。`DisposableEffect` 的 `onDispose` 才定义了释放点。

### 2.6 `observeForever()`、静态集合与无界缓存

`observeForever()` 的 observer 不受 Lifecycle 自动管理，调用方必须保存同一个 observer 并执行 `removeObserver()`。RxJava subscription、Flow 转换后的自建 scope、广播接收器和 SDK callback 也遵循同样原则。

静态集合和缓存还要回答：

- key 是否会无限增长？
- value 是否间接持有页面对象？
- 淘汰策略依据数量、字节数还是业务代次？
- 账号切换、退出登录和低内存事件是否会清理？

弱引用不能代替缓存策略。`SoftReference` 也不适合作为可预测缓存；回收时机由运行时决定，命中率和容量都不可控。

### 2.7 Kotlin Coroutine 与 Flow 的生命周期边界

协程泄漏的根源仍是生命周期长短不匹配。页面任务不应放进 `GlobalScope` 或其他进程级 scope；Fragment View 相关的收集任务应绑定 `viewLifecycleOwner`，回调式 API 转为 `callbackFlow` 时则要在 `awaitClose` 中移除 listener。

```kotlin
class FeedFragment : Fragment(R.layout.feed) {
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.items.collect { items ->
                    render(items)
                }
            }
        }
    }
}
```

这段写法让收集任务随 View 生命周期停止和重启。Fragment 本体仍在 back stack、但 View 已销毁时，不会继续把旧 View 树留在收集回调里。Compose 场景对应使用 `LaunchedEffect`、`DisposableEffect`、`collectAsStateWithLifecycle` 等与组合生命周期绑定的入口。

## 3. 证据链：从“内存上涨”到引用路径

### 3.1 固定复现场景

一次首页启动和连续执行二十轮页面进出不可直接比较。先固定：

- 相同设备、build、ABI 与应用版本；
- 相同账号和数据规模；
- 相同操作序列与等待点；
- 相同前后台状态；
- 采集前是否执行 GC、是否连接调试器。

轮次不要写成通用门槛。应根据页面应有对象数、噪声和问题增长速度确定，并在修复前后使用同一协议。

### 3.2 先看分区，再决定工具

`dumpsys meminfo <package>` 适合做低成本分区观察。分析时应比较 Java Heap、Native Heap、Graphics、Code、Stack 等分区在相同操作序列下的变化，单次总 PSS 只能作为一个采样点。

下面的命令用于记录进程内存概况和线程数量：

```bash
adb shell dumpsys meminfo com.example.app
adb shell pidof com.example.app
adb shell ls /proc/<pid>/task | wc -l
```

把 `<pid>` 替换为 `pidof` 返回值。`dumpsys meminfo` 是采样视图；PSS 会受共享页和系统环境影响，线程数也需要与业务并发阶段一起解释。

### 3.3 heap dump 看的是某一时刻的对象图

Android Studio Heap Dump 可显示 class instance、shallow size、retained size、dominator 和引用关系。分析顺序建议为：

1. 找到按业务应已销毁的对象实例；
2. 查看它的 shortest path to GC Root；
3. 在路径上找到第一个不应继续持有的引用；
4. 判断这条引用属于应用代码、第三方库还是 framework；
5. 修改所有权或注销时机后重复同一场景。

retained size 很大不代表当前节点就是缺陷位置。它表示该对象支配的对象集合大小；修复点往往位于引用路径更靠近 Root 的字段或容器。

heap dump 会暂停或扰动被测进程，也会暂时增加内存占用。性能结果不能用 dump 期间的数据代替正常运行数据。

### 3.4 native 增长用 allocation stack

Java heap 稳定而 Native Heap 上升时，继续抓 Java hprof 往往不会得到答案。Perfetto `heapprofd` 能记录 native allocation/free 与调用栈；ART allocation profiling 则面向 Java/Kotlin 分配。

采样频率、目标进程、持续时间和符号化条件会影响开销与可读性。线上启用前应在目标机型做开销验证，并保留 build ID、native symbols 和混淆映射。

## 4. LeakCanary：开发期 retained-object 检测

LeakCanary 的主路径可以概括为：

1. `ObjectWatcher` 用弱引用观察已越过生命周期的对象；
2. 对象在等待和 GC 后仍存在时，标记为 retained；
3. retained object 达到当前配置条件后生成 hprof；
4. Shark 分析对象图并计算 leak trace；
5. 相同可疑引用路径按 signature 归组。

Activity、Fragment、Fragment view 和 ViewModel 等常见类型可以自动观察。业务自定义对象也可以在确认其生命周期结束后交给 `AppWatcher.objectWatcher.watch()`。

依赖通常只加入 debug variant，避免把本地分析 UI 和自动 heap dump 带进生产包：

```kotlin
dependencies {
    debugImplementation(libs.leakcanary.android)
}
```

这里用 version catalog 隐去具体版本，项目应锁定经过验证的依赖版本。LeakCanary 默认策略会随版本变化，阈值和延迟应查当前依赖的配置与文档。

LeakCanary 给出的 leak trace 是定位入口。修复前仍要确认：

- 被标记对象在业务上是否已经无用；
- 可疑引用是否由测试环境或调试器引入；
- library leak 是否有可升级版本或可行规避；
- 同一 signature 是否能稳定复现。

## 5. KOOM 与自建线上方案

KOOM 官方仓库提供 Java Heap、Native Heap 和 Thread 三类监控模块。Java leak 模块包含基于 fork/COW 的 heap dump 方案，native 模块和 thread 模块有各自的 hook 与分析路径。

它不应被简化成“计数器推断泄漏”，也不能用固定的“精度高低”表格和 LeakCanary 互相排名。是否接入取决于：

- 目标 Android 版本、ABI 与 OEM 兼容性；
- native hook、fork/dump 策略对稳定性和时延的影响；
- 产物体积、上传成本与隐私要求；
- 符号、混淆映射和服务端分析能力；
- 项目维护状态以及本地验证结果。

自建方案也不要通过周期性 `System.gc()` 加弱引用来宣布泄漏。更稳妥的做法是把低成本趋势信号用于筛选样本，再用系统或工具产生的 heap/native profile 取证。

## 6. Android 17：用 `ProfilingManager` 捕获线上证据

### 6.1 API 边界

`ProfilingManager` 在 API 35 加入平台，可请求 system trace、Java heap dump、heap profile 和 stack sampling。系统 trigger 能力从后续版本继续扩展。

Android 17 / API 37 新增了与内存诊断直接相关的 trigger：

- `ProfilingTrigger.TRIGGER_TYPE_OOM`：应用抛出 `OutOfMemoryError` 时采集 Java heap dump；
- `ProfilingTrigger.TRIGGER_TYPE_ANOMALY`：系统检测到过量内存使用等异常时，可在系统采取处置前提供相应 profile。

请求受系统 rate limiter、设备状态和采集条件约束，不保证每次事件都有结果。OOM 发生时原进程通常无法继续可靠工作，结果需要在后续进程启动并注册 listener 后接收。

### 6.2 注册 trigger 和结果监听

下面的 Kotlin 示例只在 API 37 及以上注册 OOM 与 anomaly trigger，并在采集成功时把系统生成的文件路径交给应用自己的上传调度器：

```kotlin
@RequiresApi(37)
class MemoryProfileRegistrar(
    context: Context,
    private val executor: Executor,
    private val onProfileReady: (File) -> Unit,
) {
    private val manager =
        context.getSystemService(ProfilingManager::class.java)

    private val callback = Consumer<ProfilingResult> { result ->
        if (result.errorCode == ProfilingResult.ERROR_NONE) {
            result.resultFilePath?.let { onProfileReady(File(it)) }
        } else {
            Log.w(TAG, "Profiling failed: ${result.errorCode}")
        }
    }

    fun register() {
        manager.registerForAllProfilingResults(executor, callback)
        manager.addProfilingTriggers(
            listOf(
                ProfilingTrigger.Builder(
                    ProfilingTrigger.TRIGGER_TYPE_OOM,
                ).build(),
                ProfilingTrigger.Builder(
                    ProfilingTrigger.TRIGGER_TYPE_ANOMALY,
                ).build(),
            ),
        )
    }

    fun unregister() {
        manager.unregisterForAllProfilingResults(callback)
    }

    private companion object {
        const val TAG = "MemoryProfiling"
    }
}
```

应用应在稳定的进程入口尽早注册全局 listener，否则可能错过先前事件的结果交付。上传任务还要检查文件存在性、网络与电量条件、用户同意和服务端去重。不要在回调线程同步上传大型产物。

同一种 trigger 只能保留一个注册项；重复添加会覆盖先前配置。业务若设置 `setRateLimitingPeriodHours()`，该限制会叠加在系统 rate limiter 之上，数值应由样本预算和事件频率确定。

## 7. `ApplicationExitInfo` 能证明什么

`ApplicationExitInfo` 从 API 30 起记录历史进程退出信息。它适合回答“进程为何退出、退出前系统最近采样到多少 PSS/RSS”，不能直接回答“哪条引用造成泄漏”。

下面的代码读取最近退出记录，并提取内存诊断需要的基础字段：

```kotlin
data class ExitSnapshot(
    val reason: Int,
    val timestampMs: Long,
    val pssKb: Long,
    val rssKb: Long,
    val processName: String,
    val description: String?,
)

fun readRecentExits(context: Context): List<ExitSnapshot> {
    val activityManager =
        context.getSystemService(ActivityManager::class.java)

    return activityManager
        .getHistoricalProcessExitReasons(context.packageName, 0, 0)
        .map { info ->
            ExitSnapshot(
                reason = info.reason,
                timestampMs = info.timestamp,
                pssKb = info.pss,
                rssKb = info.rss,
                processName = info.processName,
                description = info.description,
            )
        }
}
```

`getPss()` 和 `getRss()` 是系统退出前最近一次采样值，可能为零，也不保证等于死亡瞬间。`REASON_LOW_MEMORY` 说明系统在低内存情境下终止进程，仍需结合设备压力、进程重要性和内存分区判断；部分设备不支持该原因码，可用 `ActivityManager.isLowMemoryKillReportSupported()` 查询。`getTraceInputStream()` 主要用于 ANR trace，以及 API 31 起的 native tombstone；不要假设每条低内存记录都附带 heap dump。

## 8. 生产治理：信号、采集与验证分层

### 8.1 低成本信号

生产环境可以长期保留：

- Java/native/graphics 等分区的轻量采样；
- 进程 RSS/PSS 与线程数；
- OOM、LMK、native allocation failure 和历史退出原因；
- 当前页面或关键用户流程、设备档位、系统版本、应用 build；
- 采集器自身耗时、内存和失败率。

单个绝对阈值很难覆盖所有设备。阈值应来自设备分层基线、业务场景和历史分布，并与持续增长、退出原因或异常率组合判断。

### 8.2 高成本证据按需触发

heap dump、native allocation profile 和长时间 trace 都会带来资源开销及敏感数据风险。采集策略应限制：

- 设备与用户抽样；
- 单设备和单版本配额；
- 电量、温度、磁盘和网络条件；
- 文件生命周期与加密；
- 符号化、反混淆和访问权限；
- 失败重试和重复事件合并。

系统允许采集不代表产品可以无条件上传。上线前还需满足隐私声明、用户选择和所在地区的数据要求。

### 8.3 用回归实验确认修复

引用路径修正后，重复原场景并验证：

1. 目标对象数量回到预期；
2. 同一 leak signature 不再出现；
3. 相同轮次下 retained size 或分区增长斜率下降；
4. 页面行为、异步任务和缓存命中没有被错误破坏；
5. OOM/LMK 等线上指标按版本和设备分层改善。

一次 heap dump 不再显示对象，只能证明该次快照没有捕获它。稳定复现协议和版本对照才能降低偶然 GC、采样时机与数据规模带来的误判。

## 9. 容易制造新问题的“修复”

- **把所有引用换成 WeakReference**：弱引用会让对象在仍被业务需要时消失，也掩盖所有权设计问题。
- **用 SoftReference 做核心缓存**：回收时机不可预测，不能保证容量、命中或业务可用性。
- **频繁调用 `System.gc()`**：GC 请求不构成释放保证，还可能增加暂停和 CPU 开销。
- **只清空页面字段，不注销外部 listener**：外部 owner 仍可通过 listener 捕获页面。
- **把 `observeForever()` 当 lifecycle observer**：它必须显式 `removeObserver()`。
- **盲目使用对象池**：对象池会延长对象寿命、引入同步和重置成本；只应在基准证明确有收益时使用。
- **只上传 OOM stack trace**：内存耗尽后异常可能出现在任意后续分配点，stack trace 常常不是增长源。

## 10. 排查清单

### 现象确认

- 内存增长位于 Java、native、graphics、线程还是 mmap？
- 增长是持续保留，还是高分配率后能够回落？
- 只发生在特定设备、ABI、系统版本或业务数据规模吗？

### 对象证据

- 对象的业务生命周期结束事件是什么？
- heap dump 中是否存在稳定的 GC Root 路径？
- 路径上第一个不合理 owner 或容器是谁？
- 问题来自应用、SDK、OEM framework 还是测试环境？

### 修复验证

- 注销、取消和字段清理是否位于正确生命周期？
- 是否误伤合法后台任务、缓存或配置变更恢复？
- 修复前后是否使用同一复现协议？
- 线上指标是否按版本、设备和场景分层验证？

## 11. 结论

内存泄漏治理的核心证据是“已结束的业务生命周期 + 不必要的强引用路径 + 可重复的保留现象”。OOM、PSS 上涨、retained object 和 `REASON_LOW_MEMORY` 都是线索，单独使用都不足以给出引用泄漏结论。

本地开发优先用 LeakCanary 与 Android Studio heap dump 找对象路径；native 增长用 heapprofd 等 allocation profile；生产环境用低成本趋势筛选样本，再通过 Android 17 `ProfilingManager` OOM/anomaly trigger 或经过验证的线上工具采集产物。修复点应回到所有权和生命周期，而不是依赖 GC、弱引用或固定阈值。

## 参考资料

- [AOSP `android-17.0.0_r1` manifest tag](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/)
- [AOSP `ProfilingManager.java` at `android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [AOSP `ProfilingTrigger.java` at `android-17.0.0_r1`](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [Android 17 features and APIs: new ProfilingManager triggers](https://developer.android.com/about/versions/17/features)
- [ProfilingManager API reference](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingTrigger API reference](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Trigger-based profiling](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [ApplicationExitInfo API reference](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Capture a heap dump with Android Studio](https://developer.android.com/studio/profile/capture-heap-dump)
- [LeakCanary: How LeakCanary works](https://square.github.io/leakcanary/fundamentals-how-leakcanary-works/)
- [KOOM official repository](https://github.com/KwaiAppTeam/KOOM)
- [Perfetto heapprofd documentation](https://perfetto.dev/docs/data-sources/native-heap-profiler)
