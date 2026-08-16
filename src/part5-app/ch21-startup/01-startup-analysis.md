---
title: "启动完整路径分析（App 视角）"
chapter: "21.1"
section: "21.1"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "AOSP android-17.0.0_r1 / Android 17 (API 37); Android Developers launch-time and StartupTimingMetric docs; PerfettoSQL standard library checked 2026-08-14; no Android 18/API 38+ conclusions"
confidence: medium
sources:
- type: aosp
  path: frameworks/base/core/java/android/view/ViewRootImpl.java
- type: official
  path: https://developer.android.com/topic/performance/vitals/launch-time
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- type: official
  path: https://developer.android.com/topic/performance/appstartup/analysis-optimization
- type: official
  path: https://developer.android.com/reference/androidx/benchmark/macro/StartupTimingMetric
- type: official
  path: https://developer.android.com/reference/android/view/ViewTreeObserver
- type: official
  path: https://perfetto.dev/docs/data-sources/atrace
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
tags: [cold-start, warm-start, hot-start, ttid, ttfd, startup-trace, perfetto]
related_chapters: ["8.2", "8.3", "1.7", "1.11", "21.2"]
pipeline_stage: "finalized"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: fixed
---

# 启动完整路径分析（App 视角）

从应用进程一侧分析启动，需要确认系统什么时候把执行权交给应用、关键路径包含哪些阶段，以及 Trace（带时间轴的执行跟踪）中一段区间究竟代表什么。系统侧的进程创建、任务与窗口管理另见 8.2 节；初始化依赖治理、Baseline Profile 和首帧渲染分别在后续章节展开。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`。AndroidX 与 Perfetto 属于独立发布的工具链，相关内容会明确它们与平台版本的边界。

## 1. 冷、温、热描述的是启动前状态

[Android 应用启动文档](https://developer.android.com/topic/performance/vitals/launch-time)把启动分为 cold、warm、hot。三者概括的是启动前进程、Activity 和 UI 对象是否仍然存在；生命周期回调会随任务状态变化。

| 类型 | 启动前状态 | 应用侧通常需要完成的工作 |
| --- | --- | --- |
| 冷启动 | 目标应用进程不存在 | 创建进程和 Application，安装 Provider，创建 Activity，生成第一帧 |
| 温启动 | 复用了一部分状态，但 Activity 或进程中的部分对象需要重建 | 常见情况是进程仍在而 Activity 重建；恢复路径取决于任务和保存状态 |
| 热启动 | 进程与目标 Activity 仍在内存中 | 将已有 Activity 带回前台，处理生命周期与必要的重绘 |

同一个入口在不同时间可能落入不同类型。用户从桌面点击、通知跳转、深链、最近任务恢复，也可能命中不同 Activity 和任务栈。只看 `onCreate()` 是否调用，无法可靠判断平台记录的启动类型。

工程上要区分两件事：

- **实验分类**：Macrobenchmark 的 `StartupMode.COLD/WARM/HOT` 用固定前置条件构造可比较样本。
- **线上分类**：使用平台或 Play 的启动指标，并按入口、进程、版本和设备分组；Android 15+ 的 `ApplicationStartInfo` 可提供系统记录的启动类型，应用自有“进程首次启动”标记只能辅助解释。采集方法见[启动监控与度量](./08-startup-monitoring.md)。

不要用“温启动一定是冷启动的某个百分比”或“热启动一定小于一帧”作为基线。后台回收、配置变化、首屏数据、CPU 调频和页面重绘都会改变成本。

## 2. Android 17 冷启动的 App 侧路径

### 2.1 从启动请求到应用主线程

冷启动开始时，系统解析启动请求、准备任务与 starting window（应用首帧完成前由系统显示的启动窗口），并请求 Zygote fork 应用进程。Zygote 是预加载常用框架类的进程模板，fork 会从它派生新的 Linux 应用进程。这个阶段已经计入用户看到的启动等待，但应用自己的 `Application` 埋点还没有运行。

子进程进入 `ActivityThread.main()` 后，会准备主线程 Looper（按顺序取出并分发消息的事件循环）、创建 `ActivityThread`，再通过 Binder（Android 跨进程调用机制）向 system_server（承载主要系统服务的进程）登记。后续绑定信息和生命周期事务被送回应用主线程。对应用开发者而言，这段路径有两个含义：

1. `Application.attachBaseContext()` 不是整个冷启动的起点，早于它的系统与进程初始化同样消耗 TTID。
2. 只汇总应用内埋点会漏掉进程创建、调度等待、系统服务和跨进程通信时间。

### 2.2 `ContentProvider` 早于 `Application.onCreate()`

Android 17 的 [`ActivityThread.handleBindApplication()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)按以下关键顺序执行：

```text
创建并 attach Application
        ↓
installContentProviders(app, data.providers)
        ↓
Instrumentation.onCreate(...)
        ↓
Instrumentation.callApplicationOnCreate(app)
```

这段顺序说明，自动初始化 Provider 的 `onCreate()` 位于应用 `Application.onCreate()` 之前。`Instrumentation` 是框架用来创建和驱动应用组件的入口。仅给 `Application.onCreate()` 计时会漏掉 App Startup、第三方 SDK 或业务 Provider 的成本。

`Application.attachBaseContext()` 到 `Application.onCreate()` 之间可能包含：

- Provider 类加载、静态初始化与 `onCreate()`；
- 配置和资源初始化；
- instrumentation 初始化；
- 主线程上的 Binder、文件、数据库和锁等待。

Provider 治理见 [ContentProvider 启动优化](./03-contentprovider-optimization.md)。多进程应用还要核对每个 Provider 的 `android:process`：默认进程的 Provider 不会自动在每个子进程各运行一次，声明到某个进程的组件只随对应进程安装。

### 2.3 Application 阶段

`Application.onCreate()` 在主线程同步执行。适合保留在这里的工作应同时满足：

- 当前进程需要；
- 当前入口需要；
- 在 Activity 或首帧之前必须完成；
- 能在给定主线程预算内结束；
- 不依赖不受控的网络或长时间锁等待。

常见长任务包括 SDK 初始化、同步数据库打开、反序列化大配置、原生库加载和批量对象构造。把它们全部提交到后台线程也可能延迟启动：主线程若随后等待结果，关键路径没有缩短；如果不等待，后台 CPU、I/O 和类加载仍会与首帧争用资源。

对于 `minSdkVersion >= 21` 的应用，平台原生支持从多个 DEX 加载类，不需要在 `Application` 中调用旧版 `MultiDex.install()`。只有仍支持 API 20 及以下的应用才需要单独审视这条兼容路径。

### 2.4 Activity 创建与 UI 构建

应用收到启动 Activity 的 lifecycle transaction（系统发给应用主线程的一组生命周期操作）后，框架创建 Activity，并根据目标状态执行 `onCreate()`、`onStart()`、`onResume()` 等回调。不要把这串回调当作所有启动的恒定路径；已有 Activity 回前台、配置变化和任务恢复会走不同组合。

View UI 的 `setContentView()` 会触发布局 XML 解析、View 创建和属性解析。Compose UI 则在 `setContent` 后经历初始 composition（执行 Composable 并建立 UI 结构）、layout 和 draw。两种 UI 技术都要关注：

- 是否在主线程读取磁盘或等待 Binder；
- 图片解码、字体和资源是否进入首帧关键路径；
- 首屏不可见区域是否提前创建；
- 自定义 View 构造、`onMeasure()`、`onLayout()`、`onDraw()` 是否执行重活；
- Compose 的首轮 composition 是否创建过多对象或读取未准备好的状态。

View 数量、布局深度或 Composable 数量都没有通用的危险阈值。Trace 中的耗时和调用路径才是优化依据。`ViewStub`（需要时才展开布局的占位 View）、条件 composition、懒加载或异步 inflate（在允许范围内把 View 创建移出主线程）也各有语义限制，采用前要验证线程安全、状态恢复和首屏交互。

### 2.5 第一帧从 traversal 到系统确认绘制

主线程在 VSync（显示刷新节奏信号）驱动下进入 `Choreographer#doFrame`，执行 traversal，也就是对 View 树完成 measure、layout 和 draw。硬件加速路径中，UI 线程记录绘制命令，RenderThread 与 GPU 继续处理渲染，图形 buffer 再交给系统合成路径。

Android 17 的 [`ViewRootImpl`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)在首次绘制请求完成后走 `reportDrawFinished(...)` 路径，窗口系统据此结束对应的启动绘制等待。需要区分几个相邻观测点：

| 观测点 | 可以说明什么 | 不能说明什么 |
| --- | --- | --- |
| `performTraversals` 结束 | 本轮主线程 traversal 返回 | GPU、buffer 提交和系统确认均已结束 |
| RenderThread `DrawFrame` | 渲染线程处理这一帧 | 像素已经被面板扫描显示 |
| frame commit callback | 硬件渲染内容已提交到 swap chain（等待显示的图形缓冲队列） | 用户已经看到该帧；该回调只适用于硬件渲染 |
| TTID | 系统记录的首帧启动指标 | 页面主要内容已经可用 |

帧预算取决于刷新率、FrameTimeline deadline（这一帧应完成的时间点）和渲染流水线阶段，不能一律写成 16 ms。120 Hz 显示器的节奏与 60 Hz 不同，一次 traversal 跨过某个 VSync 也要结合目标时间线和实际时间线判断是否错过 deadline。

## 3. TTID 与 TTFD 回答不同问题

### 3.1 TTID：首个 UI 帧

TTID（Time To Initial Display）从系统收到启动请求开始，直到目标 Activity 的第一帧被记录为已显示。它包含冷启动时的进程创建，也包含冷/温启动时的 Activity 创建和首帧工作。

TTID 很短只能说明用户很快看到一个应用帧。该帧可能仍是骨架、空列表或占位内容。系统 SplashScreen 的持续时间、应用第一帧和主要内容可用时间也不能混为一个数字。

Logcat 中的 `Displayed ... +...`、`adb shell am start -W` 和 Perfetto 都能帮助本地诊断。命令行结果会受到任务栈、是否 force-stop、编译状态和设备状态影响，不应把一次 `am start -W` 当成发布门禁。

Android vitals（Google Play 汇总的真实设备质量指标）当前把冷启动 5 秒、温启动 2 秒、热启动 1.5 秒及以上列为 excessive。它们是 Play 的告警边界，不是优秀体验的目标值。应用自己的预算应按入口、设备档位和产品体验设得更严格。

### 3.2 TTFD：由应用声明“主要内容可用”

TTFD（Time To Fully Drawn）从同一启动请求开始，到应用调用 `reportFullyDrawn()`，并完成包含该报告的帧。`StartupTimingMetric` 的 `timeToFullDisplayMs` 在 API 29 以前可能不可用；API 29 是该指标的适用起点。

平台不知道每个产品何时“可用”，因此团队必须先定义完成条件。例如：

- 首页主列表已经展示本地缓存或网络数据；
- 关键按钮可点击，必要依赖已经准备好；
- 错误态或离线态也已形成可操作界面；
- 不影响首要任务的推荐、广告或二级卡片不进入条件。

下面的示例把“关键数据就绪”和“主内容完成布局”作为报告条件：

```kotlin
class MainActivity : ComponentActivity() {
    private var criticalDataReady = false
    private var mainContentLaidOut = false
    private var fullyDrawnReported = false

    private fun maybeReportFullyDrawn() {
        if (criticalDataReady &&
            mainContentLaidOut &&
            !fullyDrawnReported
        ) {
            fullyDrawnReported = true
            reportFullyDrawn()
        }
    }
}
```

`criticalDataReady` 和 `mainContentLaidOut` 应由对应状态与布局回调更新，每次更新后调用 `maybeReportFullyDrawn()`。报告只发送一次；完成条件应覆盖成功、离线和可恢复错误，避免网络失败后永远没有 TTFD。若调用发生在首帧之前，平台会以系统检测到的首帧时间为下限，因此提前调用不会生成比 TTID 更早的有效 TTFD。

AndroidX `ComponentActivity` 的 Fully Drawn 支持可协调多个组件或异步条件。无论使用平台方法还是 AndroidX 封装，团队都要把“fully drawn”定义写进测试，避免不同页面各自解释。

### 3.3 自定义里程碑：解释 TTID/TTFD 内部时间

TTID 和 TTFD 是端到端指标，无法直接说明慢在哪里。应用可补充少量稳定里程碑：

- Application attach；
- 每个必要初始化器的开始和结束；
- Activity 创建、UI 状态提交；
- 关键数据可用；
- 主要内容完成布局；
- `reportFullyDrawn()` 请求。

区间计时优先使用单调时钟，也就是只向前推进、不受用户改时或网络校时影响的时钟。`SystemClock.uptimeNanos()` 不计深度休眠，适合进程内 CPU/主线程工作区间；`elapsedRealtimeNanos()` 计入深度休眠，并在同一设备上提供自开机以来的时间基准。`System.nanoTime()` 只保证用于计算同一运行环境中的时间差，不应依赖它的绝对起点。

埋点名称要稳定，可能出现的名称数量也要受控；监控系统把这种取值数量称为基数。不要把用户 ID、URL 或动态参数写入 Trace 名称。线上事件还需采样，并记录启动入口、应用版本、设备档位、编译状态和进程名。

## 4. 用 Macrobenchmark 建立启动基线

[Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)从目标应用进程外驱动启动，并为每轮采集 Perfetto Trace。它比在 `Application` 内自行计时更适合端到端回归。目标应用需要可 profile，即通过 `android:profileable` 允许性能工具读取接近发布配置的跟踪数据。

下面的基准用于测量带有 Baseline Profile 的冷启动：

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {
    @get:Rule
    val rule = MacrobenchmarkRule()

    @Test
    fun coldStart() = rule.measureRepeated(
        packageName = TARGET_PACKAGE,
        metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.Partial(
            baselineProfileMode = BaselineProfileMode.Require,
        ),
        startupMode = StartupMode.COLD,
        iterations = 10,
        setupBlock = {
            pressHome()
        },
    ) {
        startActivityAndWait()
    }
}
```

`StartupTimingMetric`输出 `timeToInitialDisplayMs`；应用正确报告 fully drawn 时，还会输出 `timeToFullDisplayMs`。十次迭代只是一组起始配置，应根据噪声、设备数量和需要检测的回归幅度调整。

每次对比必须固定：

- 同一 release 配置和构建工具链；
- 相同 `CompilationMode` 与 Baseline Profile 条件；
- 相同入口 Intent、账号、数据和网络桩（测试中返回固定结果的网络替身）；
- 相同设备型号、系统版本、电量与温度范围；
- 相同冷/温/热模式。

Debug 包、模拟器、低电量或温度降频样本不适合建立发布阈值。遇到 profileable、Baseline Profile 或编译模式配置错误时，应让测试失败并修正配置，不能忽略错误后继续使用结果。

冷、温、热三组结果要分别保存。页面结构或首屏数据变化时，还要同时检查 TTFD 和帧指标，防止用更早展示空壳换取较短 TTID。

## 5. 自定义 Trace 应围绕业务边界

应用控制的初始化入口可以用 `androidx.tracing` 补充切片。下面的示例用于区分配置解析与崩溃监控初始化：

```kotlin
fun initializeRequiredComponents() {
    trace("startup/config") {
        configStore.loadLocalSnapshot()
    }
    trace("startup/crash-reporter") {
        crashReporter.start()
    }
}
```

Perfetto 中会显示两个命名切片；切片是时间轴上带开始、结束和名称的一段区间。它要包住同步工作本身；如果代码只提交异步任务，切片结束仅代表“已提交”，不能代表初始化完成。等待异步结果时，应在生产者和消费者两端记录可关联的 async trace，或用 flow（连接两个切片的因果箭头）标出任务从提交到执行的关系，并控制关联 ID 的数量。

Trace 本身有开销。不要为每个小方法加切片，也不要只凭一个总切片判定责任。较好的层级是：

1. 启动端到端指标；
2. Application、Provider、Activity、首帧等阶段；
3. 少量可行动的业务或 SDK 边界；
4. 出现回归后再采集方法栈、Binder 或 I/O 细节。

## 6. Perfetto 启动分析实战

### 6.1 获取一条可复现的 Trace

推荐路径是运行 Macrobenchmark，并打开某次迭代生成的 `.perfetto-trace`。这样启动模式、编译模式和操作脚本与指标结果属于同一个样本。

需要手工捕获时，可以在 Perfetto UI 或设备“系统跟踪”中启用 `sched`、`freq`、`am`、`wm`、`gfx`、`view`、`binder_driver`、`dalvik` 等设备支持的类别，并指定目标应用。这些类别分别提供调度、CPU 频率、Activity/Window、图形、View、Binder 和 ART 等事件；应用自定义 `Trace` 切片还要通过 `atrace_apps` 指定允许采集的包名。

下面的 pbtxt（Protocol Buffer 文本配置）是一份诊断起点，目标包名应替换为被测应用：

```textproto
duration_ms: 15000
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "binder/binder_transaction"
      ftrace_events: "binder/binder_transaction_received"
      atrace_categories: "am"
      atrace_categories: "wm"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "dalvik"
      atrace_apps: "com.example.app"
    }
  }
}
```

把配置通过 `adb shell perfetto --txt -c - -o /data/misc/perfetto-traces/startup.perfetto-trace` 传入后，在另一终端按明确前置条件启动应用，再 pull Trace。pbtxt 文本模式适合诊断；Perfetto 文档提示它不是面向生产的稳定接口，自动化基准优先使用 Macrobenchmark。

类别和 tracepoint（内核或系统组件预先定义的跟踪事件）受设备内核及版本影响。采集前用 Perfetto UI 或设备支持列表确认，缺少某个事件时不要把它解释为对应工作没有发生。

### 6.2 先选中 Android App Startups

打开 Trace 后，先找到 **Android App Startups** 派生轨道。派生轨道是 Trace Processor 根据原始事件计算出的分析结果；选中目标包的启动 slice，再固定该时间窗口。它给出的启动边界比手工搜索第一个 `performTraversals` 更可靠。

随后按这条顺序阅读：

1. **system_server**：启动请求、进程创建、任务和窗口事件。
2. **应用主线程**：`bindApplication`、Provider/Application、自定义切片、Activity lifecycle。
3. **线程状态**：Running、Runnable、Sleeping、Blocked 以及对应唤醒者。
4. **RenderThread 与 FrameTimeline**：首帧的 CPU/GPU 工作和 deadline。
5. **相关线程/进程**：Binder 对端、I/O、编译、GC 或 SDK 工作线程。

平台 slice 名称是诊断实现，不是公开 API。名字在不同 Android/Perfetto 版本间可能变化，自动化查询应优先使用 Trace Processor 标准库和自有稳定切片。

### 6.3 分解主线程的“运行”和“等待”

看到一段长主线程 slice 后，先展开 thread state：

- **Running**：线程正在 CPU 上运行，继续查看调用栈、类加载或计算。
- **Runnable**：线程可运行但未获 CPU，检查 CPU 竞争、优先级、频率与其他活跃线程。
- **Sleeping**：可能在等待 Binder、futex（内核提供的用户态同步等待机制）、I/O 或条件变量，要沿唤醒关系找生产者。
- **Uninterruptible Sleep**：常与内核 I/O 等待有关，需要结合块设备和文件事件。

不存在“Runnable 低于 70% 就是异常”这类通用判据。主线程同步等待 5 ms 可能卡住关键路径，后台线程消耗大量 CPU 也可能让主线程长时间处于 Runnable。判断依据是关键路径上的墙钟时间，也就是现实经过时间，以及任务之间的依赖关系。

### 6.4 阅读 bind、Activity 和首帧

`bindApplication` 较长时，依次检查：

- Provider 自动初始化；
- Application attach/onCreate 自定义切片；
- 类加载、验证、静态初始化；
- GC、锁等待和 Binder；
- 主线程文件 I/O；
- 同期后台线程的 CPU/I/O 竞争。

Activity 阶段较长时，检查 View inflate 或 Compose 初始 composition、图片/字体、同步状态恢复和首屏数据绑定。单看 `Activity.onCreate()` 总时间不够，应该把可修改的业务边界标出来。

首帧阶段同时观察主线程 `Choreographer#doFrame`/traversal、RenderThread 和 FrameTimeline。`performTraversals` 结束只能当作主线程 traversal 的边界，不能作为 TTID 终点；也不能默认第一次同名 slice 就属于目标窗口。

### 6.5 用标准库批量列出启动

当前 Trace Processor 标准库提供 `android.startup.startups` 模块。标准库是随 `trace_processor` 版本发布的一组 PerfettoSQL 表、视图和函数。下面的查询用于列出目标包在一条 Trace 中的启动类型和持续时间：

```sql
INCLUDE PERFETTO MODULE android.startup.startups;

SELECT
  startup_id,
  package,
  startup_type,
  dur / 1e6 AS duration_ms
FROM android_startups
WHERE package = 'com.example.app'
ORDER BY ts;
```

这个查询使用派生启动表，不依赖 `bindApplication` 等裸 slice 是否存在。结果是 Trace Processor 对启动窗口的解析，仍应与 Macrobenchmark 报告和界面中的目标启动核对。

下面的查询用于查看目标启动窗口内耗时较长的主线程 slice：

```sql
INCLUDE PERFETTO MODULE android.startup.startups;

SELECT
  s.startup_id,
  s.slice_name,
  s.slice_dur / 1e6 AS duration_ms
FROM android_thread_slices_for_all_startups AS s
JOIN android_startups AS a USING (startup_id)
WHERE a.package = 'com.example.app'
  AND s.is_main_thread
  AND s.slice_dur >= 5e6
ORDER BY s.startup_id, s.slice_dur DESC;
```

5 ms 只是缩小诊断结果的查询过滤器，不是性能合格线。当前标准库文档已把 `android_thread_slices_for_all_startups` 标为通常不应直接使用的底层视图；上面的查询适合固定 `trace_processor_shell` 版本后的临时排查。长期 CI 应优先采用 `android_slices_for_startup_and_slice_name(...)`、`android_startup_opinionated_breakdown` 等公开函数或表，并为查询 schema（列名与类型约定）编写测试。

## 7. ClassLoader、编译状态与 DEX 布局

### 7.1 类首次使用仍可能进入启动关键路径

应用类通常由 ClassLoader（按名称查找并装入类定义的加载器）按需加载。首次主动使用一个类时，运行时可能需要查找定义、加载、验证、解析，并在需要时执行 `<clinit>`（类的静态初始化方法）。其中一部分工作可由安装期 AOT（提前编译）、运行时缓存或已有编译产物减少，但静态初始化中的应用代码仍会执行。

启动阶段要关注：

- 反射或 ServiceLoader 扫描大量类；
- 一个入口触发长依赖链的类初始化；
- `<clinit>` 读取文件、创建线程或加载 native library；
- 多个 SDK 同时加载重复的框架与序列化类型；
- 编译条件不同导致解释执行、JIT（运行时即时编译）或 AOT 路径不同。

`ApplicationLoaders` 的缓存属于进程内状态。冷启动意味着旧应用进程不存在，不能依靠它让下一次冷启动“直接命中”。多次冷启动越来越快，可能来自 Linux page cache（内核保留的文件页缓存）、ART 编译产物、应用磁盘缓存、设备频率或数据状态变化，因此基准必须控制编译与缓存条件。

### 7.2 Baseline Profile 与 Startup Profile 分工

两类 profile 解决的问题不同：

- **Baseline Profile**向 ART 提供关键类和方法，帮助安装/后台优化时进行 AOT 编译，减少关键路径上的解释与 JIT。
- **Startup Profile**面向 DEX 布局，把启动所需代码组织到主 DEX 的相邻区域；读取相邻数据所需的文件页更集中，这就是这里的读取局部性。

Baseline Profile 不会跳过业务初始化，也不会消除磁盘、Binder、锁或网络等待；Startup Profile 也不等于“把类放到文件前面就会进入 CPU cache”。它影响的是 DEX 文件组织和读取局部性，收益要用固定编译模式的启动基准验证。

两者的实践统一见 [Baseline Profile 与 Startup Profile 实战](./04-baseline-profile-practice.md)。启动期 ART/GC 行为见 [ART 启动期 GC 调节](./11-art-gc-suppression-startup-performance.md)。

## 8. 从 Trace 到修复的判断顺序

面对一条慢启动样本，可以按以下顺序推进：

1. 确认启动类型、入口、编译模式、设备状态和 TTID/TTFD。
2. 选中 Android App Startups 时间窗，判断延迟位于系统、bind、Activity 还是首帧。
3. 查看主线程是 Running、Runnable 还是等待，并追到依赖线程或 Binder 对端。
4. 用自定义切片、调用栈、I/O 或 GC 数据缩小到可修改代码。
5. 判断工作是否属于首屏必要条件；能移除就移除，能按需就按需，必须保留才考虑并发和局部优化。
6. 运行同配置 A/B Macrobenchmark，并检查 TTID、TTFD、帧和功能正确性。
7. 在小流量发布的线上数据中，按入口、设备、版本和启动类型确认回归消失。

启动优化不能只追求更早撤掉 SplashScreen。用户需要的是更快看到可理解、可操作且状态正确的内容；TTID、TTFD 和关键页面帧必须一起看。

## 参考资料

- [Android 应用启动时间](https://developer.android.com/topic/performance/vitals/launch-time)
- [启动分析与优化](https://developer.android.com/topic/performance/appstartup/analysis-optimization)
- [Macrobenchmark 概览](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [`StartupTimingMetric` API](https://developer.android.com/reference/androidx/benchmark/macro/StartupTimingMetric)
- [`ViewTreeObserver.registerFrameCommitCallback`](https://developer.android.com/reference/android/view/ViewTreeObserver)
- [Perfetto ATrace 数据源](https://perfetto.dev/docs/data-sources/atrace)
- [PerfettoSQL 标准库](https://perfetto.dev/docs/analysis/stdlib-docs)
- [AOSP Android 17 `ActivityThread`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP Android 17 `ViewRootImpl`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
