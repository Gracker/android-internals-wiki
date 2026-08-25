---
title: 第三方 SDK 性能影响评估与治理实战
chapter: '20.14'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags:
- SDK治理
- 第三方库
- 性能评估
- 启动阻塞
- 稳定性
related_chapters:
- '21.3'
- '20.1'
- '23.2'
- '24.5'
last_verified: '2026-08-14'
last_verified_against: android-17.0.0_r1 / Android 17 (API 37); android17-6.18-2026-06_r6; Android Developers, Google Play, and Privacy Sandbox phaseout/API deprecation docs checked 2026-08-14; no Android 18/API 38+ conclusions
last_draft_polish_at: '2026-08-08T11:35:18+08:00'
last_draft_polish_run_id: 20260808-113518-draft-polish-76608468
confidence: medium-high
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: '2026-08-08T12:06:09+08:00'
last_review_finalize_run_id: 20260808-120545-a55fec3c
sources:
- type: aosp
  path: AOSP Android 17 ActivityThread (android-17.0.0_r1)
- type: aosp
  path: AOSP Android 17 SdkSandboxManagerService deprecation boundary (android-17.0.0_r1)
- type: kernel
  path: Android Common Kernel proc 文档 (android17-6.18-2026-06_r6)
- type: reference
  path: 'Android Developers: App Startup, Macrobenchmark, Baseline Profiles, Android 17 behavior changes'
- type: reference
  path: Privacy Sandbox phaseout status plus historical SDK Runtime architecture and backward compatibility
---

# 第三方 SDK 性能影响评估与治理实战

第三方 SDK 治理需要一套可重复的证据链：发布包中究竟包含什么、代码在何时执行、消耗了哪些资源、异常由谁触发，以及出问题后能否快速停止调用或回退版本。一张“可接入/不可接入”的静态名单回答不了这些问题。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。涉及内核内存接口时，以 `android17-6.18-2026-06_r6` 为源码锚点。历史版本用于解释兼容路径，不把预览版或更高版本行为提前套用到 Android 17。

## 1. 先定义“SDK”，再讨论数量

SDK 并不只是一份 AAR。一次商业能力接入可能同时带来：

- 多个 Maven artifact（以 groupId、artifactId 和版本区分的独立发布单元），以及这些单元继续引入的传递依赖；
- Java/Kotlin 字节码、资源、Manifest 合并项，以及按 ABI（应用二进制接口，如 `arm64-v8a`）区分的 `.so`；
- `ContentProvider`、`Service`、`Receiver`、`Activity`、独立进程和自定义权限；
- 初始化代码、线程池、定时任务、网络协议、数据库与本地缓存；
- consumer ProGuard/R8 规则（库随 AAR 交付、构建时并入应用的压缩与混淆规则）、基线配置文件和注解处理器；
- 服务端开关、控制台配置、数据处理关系与供应商运维能力。

因此，“一个应用平均有 20～40 个 SDK”“SDK 代码占 30%～60%”不能当作项目结论。这类数字高度依赖统计口径：是按供应商、业务能力、Maven 发布单元、DEX 包名前缀，还是按最终安装字节计数？同一家供应商可能拆成十几个发布单元，一个基础库也可能被多个 SDK 复用。

更可靠的做法是同时维护两种视图：

1. **能力/供应商视图**：回答谁提供了什么能力、由谁负责、能否替换。
2. **发布制品视图**：回答本次 release 中多了哪些代码、资源、组件、权限和原生库。

不要用依赖声明数量推断最终体积，也不要用包名前缀直接推断运行时责任。治理对象应当是“某个能力在某个版本发布制品中的完整执行路径”。

## 2. 建立可核对的 SDK 台账

### 2.1 从 release 产物反推事实

调试变体和发布变体的混淆、资源压缩、动态特性交付与依赖选择可能不同。评估必须以准备发布的构建变体（variant）为准。

下面的命令用于检查 release 运行时依赖图，并解释某个模块为什么被选中：

```bash
./gradlew :app:dependencies \
  --configuration releaseRuntimeClasspath

./gradlew :app:dependencyInsight \
  --configuration releaseRuntimeClasspath \
  --dependency <artifact-name>
```

第一条命令给出直接依赖和传递依赖，第二条命令显示版本选择与依赖路径。它们仍然只是构建输入；还要检查最终合并 Manifest、APK/AAB 和动态交付模块。APK 是可直接安装的应用包，AAB（Android App Bundle）则由应用商店按设备配置生成安装包。Android Studio 的 [APK Analyzer](https://developer.android.com/studio/debug/apk-analyzer) 可以比较两个 APK/AAB 的下载大小、文件组成、DEX 内容和最终 Manifest。

每个 SDK 至少记录这些字段：

| 维度 | 必须记录的事实 |
| --- | --- |
| 身份 | 能力、供应商、Maven 坐标、精确版本、制品校验值 |
| 代码 | DEX 包、原生库、ABI、Build ID（把原生二进制与符号文件一一对应的标识）、consumer R8 规则 |
| 入口 | Provider、Application、App Startup、显式 API、其他组件 |
| 权限 | 声明权限、运行时权限、特殊访问、组件导出状态 |
| 执行 | 进程、线程/执行器、Job/Alarm/Work、回调与监听器 |
| 数据 | 采集字段、存储位置、网络端点、保留周期、用户同意条件 |
| 可观测性 | Trace（带时间轴的执行跟踪）能力、日志、指标、R8 mapping（反混淆映射文件）、原生符号 |
| 运维 | 负责人、供应商响应时限、禁用开关、回退版本、移除成本 |

Google Play 的[第三方 SDK 使用责任说明](https://support.google.com/googleplay/android-developer/answer/10358880?hl=zh-Hans)与[Google Play SDK Index](https://support.google.com/googleplay/android-developer/answer/13326895?hl=zh-Hans)都强调：即使问题来自第三方代码，应用开发者仍对发布的应用负责。[Google Play SDK Index](https://developer.android.com/distribute/sdk-index)提供版本采用率、权限、可靠性和供应商消息等风险信号，但覆盖范围有限，也不能代替本应用的实测与代码审查。

### 2.2 版本升级也按新依赖准入

“已经接入”不等于后续版本自动可信。SDK 升级可能改变：

- 自动初始化入口和初始化顺序；
- 新增权限、导出组件或独立进程；
- 传递依赖版本以及 R8 keep 范围；
- 原生库、ABI 和符号化方式；
- 线程、网络、缓存与后台调度策略；
- 数据采集字段和用户同意时机。

每次升级都应保存依赖图、Manifest、APK/AAB 组成和基准结果的差异。若供应商无法说明变更，应提高小流量发布的准入门槛，不能靠版本号猜测风险。

## 3. 测量先于归因

### 3.1 四条基本规则

SDK 评估容易出现“工具显示了数字，于是数字属于 SDK”的误判。测量前先固定四条规则：

1. **同场景比较**：启动模式、账号状态、网络、数据集、设备温度与电量状态一致。
2. **单变量比较**：A/B release 产物只改变一个 SDK、一个版本或一个初始化策略。
3. **重复采样**：保留分布、P50/P95 和异常样本，不用单次结果下结论。P50 是中位数；P95 表示 95% 的样本不超过该值，可用来观察偏慢的一段样本。
4. **保留证据**：产物、版本、编译模式、Trace、符号、mapping 与实验脚本一并归档。

单 SDK 实验用于判断边际成本，也就是有无该 SDK 或版本变更时的场景差值；全部 SDK 的集成实验用于识别竞争和叠加效应。两种实验不能互相替代。

### 3.2 证据强度

| 结论 | 弱证据 | 较强证据 |
| --- | --- | --- |
| 启动变慢来自 SDK | 主线程栈出现 SDK 类 | A/B 产物回归 + Trace 时间片 + 可复现调用路径 |
| 内存增加来自 SDK | heap dump 中有 SDK 包名 | 同场景 A/B + retained path（从 GC Root 到对象的强引用链）/分配栈 + 原生 Build ID |
| 网络由 SDK 发起 | 某域名看起来像供应商 | 请求 ID/调用栈/供应商诊断回调 + 端点和配置核对 |
| Crash 属于 SDK 缺陷 | 顶部帧位于 SDK | SDK 开关或版本对照复现 + 供应商确认/修复 |
| 后台耗电来自 SDK | 看到一个 SDK 线程 | 调度来源、唤醒、CPU 栈、网络与场景差值一致 |

工具回答的是“观察到什么”，归因还需要对照实验与调用关系。尤其在同一进程内，线程、堆、网络连接和系统回调经常由宿主与 SDK 共同参与。

## 4. 启动：先找自动入口

### 4.1 Provider 早于 `Application.onCreate`

在 Android 17 的 [`ActivityThread`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java) 启动路径中，系统先调用 `installContentProviders(...)`，随后通过 `Instrumentation.callApplicationOnCreate(...)` 调用 `Application.onCreate()`；`Instrumentation` 是 Android 用来创建和驱动应用组件的框架入口。因此，SDK 的自动 `ContentProvider` 初始化发生在应用自己的 `Application.onCreate()` 之前。

常见主线程成本包括：

- Provider 构造、类加载与静态初始化；
- SharedPreferences、文件、数据库或 PackageManager 查询；
- Binder（Android 跨进程调用机制）调用、锁等待和同步网络探测；
- 初始化时注册监听器、创建线程池或加载原生库；
- 多个 SDK 争用主线程、磁盘和类加载锁。

这也解释了为什么只给 `Application.onCreate()` 打点会漏掉早期成本。Provider 优化的完整路径见 [ContentProvider 启动优化](../ch21-startup/03-contentprovider-multiprocess-startup.md)。

### 4.2 App Startup 能解决什么

[Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup) 将多个自动初始化 Provider 合并到一个 `InitializationProvider`，并通过 `Initializer.dependencies()` 显式声明依赖顺序。它适合统一入口和减少 Provider 数量，但不会自动把初始化移出主线程：由 Manifest 声明的 `Initializer.create()` 仍在 Provider 启动阶段执行。

如果某个初始化器与首屏无关，可从 Manifest 中移除对应声明：

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge">
    <meta-data
        android:name="com.example.analytics.AnalyticsInitializer"
        tools:node="remove" />
</provider>
```

删除这条元数据后，应用可在用户同意或功能首用时调用 `AppInitializer.initializeComponent(...)`。App Startup 的公开契约还规定：关闭某个组件（component）的自动初始化，也会关闭其 `dependencies()` 返回组件的自动初始化；随后手动初始化该组件时，这些依赖会按图一并初始化。若某个依赖同时被其他 Manifest 声明的 `Initializer` 引用，它仍可能从另一条路径启动，因此必须检查完整依赖图。

### 4.3 按需、延迟与异步不是同义词

- **按需初始化**：功能第一次需要时才启动，通常最节省未使用能力的成本。
- **延迟初始化**：在首帧后某个时点启动，成本仍会发生，并可能撞上首屏交互。
- **异步初始化**：把允许并发的工作移出主线程，但没有改变后台执行限制、生命周期和依赖时序。

选择策略时先拆分 SDK 工作：

| 工作 | 建议 |
| --- | --- |
| 首次 API 调用前必须完成的轻量状态 | 保持同步，但设定很小的主线程预算 |
| 用户同意前不得运行的数据能力 | 同意后显式初始化 |
| 只在特定页面使用的能力 | 页面或功能首用时初始化 |
| 可预取且可取消的资源 | 首帧后按场景调度，限制并发和截止时间 |
| 需要持久保证的后台任务 | 按任务契约选择系统调度 API，不靠常驻线程 |

把同步调用包进协程不代表它就安全。如果代码仍在 Main dispatcher 运行，主线程成本没有变化；即使换到后台线程，也可能带来 CPU、I/O 竞争或生命周期泄漏。

### 4.4 用 Macrobenchmark 建立可比较基线

[Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) 能在应用进程外重复驱动冷、温、热启动，并保存 Perfetto Trace。冷启动从无进程状态开始，温启动保留进程但重新启动 Activity，热启动则把仍在内存中的 Activity 带回前台。目标应用需要可 profile，即发布构建通过 `android:profileable` 允许性能工具读取跟踪数据。比较 SDK 版本时，release 配置、设备、启动模式和编译模式都要相同。

下面的测试用于测量带有 Baseline Profile 的冷启动；`BaselineProfileMode.Require` 会在配置不满足时让测试失败，避免悄悄换成另一种编译条件：

```kotlin
@LargeTest
@RunWith(AndroidJUnit4::class)
class SdkStartupBenchmark {
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

测试应对 A/B 产物分别运行，并查看 [`timeToInitialDisplayMs` 与 `timeToFullDisplayMs`](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)及对应 Trace。迭代十次只是示例，不是统计学保证；应按设备噪声和回归幅度决定样本量。

[Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/overview)可以预编译关键代码路径，SDK 也能随库交付 profile rules。它们不能消除同步磁盘、网络、锁等待，也不会改变静态初始化语义。评估 profile 收益时，仍要固定 [`CompilationMode.Partial`](https://developer.android.com/reference/kotlin/androidx/benchmark/macro/CompilationMode.Partial) 配置。

对于可控的集成代码，可用 `androidx.tracing` 给初始化入口增加命名切片；切片是 Trace 时间轴上带开始、结束与名称的一段区间。不透明的 Provider 只能依赖系统切片、调用栈或供应商提供的 Trace。切片应覆盖等待时间和结果，不能只包住一次异步任务提交。

## 5. 内存：同进程没有可靠的“每 SDK PSS”

### 5.1 先辨认工具边界

`dumpsys meminfo`、`procrank` 和 `/proc/<pid>/smaps` 都以进程或虚拟内存区域为观察对象：

- PSS（Proportional Set Size，比例集大小）把共享物理页按映射进程数分摊，适合进程级比较；
- RSS（Resident Set Size，驻留集大小）统计当前驻留在物理内存中的页，读取成本较低，但共享页会在多个进程重复出现；
- `smaps` 描述每个 VMA（Virtual Memory Area，虚拟内存区域）的地址、权限、对应文件与页统计；
- Java heap dump 是 Java/Kotlin 托管堆在某一时刻的对象与引用快照；
- heapprofd 是 Perfetto 的原生堆采样器，可按分配调用栈归集 native 分配。

Android 17 的内核接口定义可核对 [`Documentation/filesystems/proc.rst`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)。这些工具不会凭空生成 SDK 所有权：

- 同一进程的 Java heap 与 native 内存分配器被宿主和各 SDK 共用；
- 类的包名不等于对象的保留责任，宿主可能把对象长期放进缓存；
- `.so` 文件映射的 RSS 包含代码页与共享干净页，不等于该 SDK 的活跃 native heap；
- native 分配可能经过宿主封装、JNI 回调或公共库，必须看符号化调用栈。

因此，“按包名汇总 heap dump”“把 `.so` RSS 当作 SDK 内存”“从 smaps 精确拆分 SDK PSS”都只能作为线索，不能写成精确归因。

### 5.2 推荐的 A/B 内存实验

一次可审计的内存评估应包含：

1. 生成只相差一个 SDK 或一个版本的两个 release 产物。
2. 在相同设备档位、冷进程、账号数据和固定脚本下运行相同场景。
3. 在稳定点与峰值点重复采集 RSS/PSS、Java heap、native heap 和映射。
4. Java 堆查看 dominator（支配对象：它不可达时，其下游对象也会变为不可达）与 retained path，不只按类名计数。
5. native 堆用带 Build ID 的符号解析 heapprofd 分配栈。
6. 把加载映射、活跃分配、线程栈和图形缓冲分开解释。
7. 保存每轮原始数据与分布，报告差值、取值范围和离散程度；只有明确统计模型时才报告置信区间。

若 SDK 自带有语义的缓存/队列计数器，也应纳入同一时间线。供应商指标可以帮助解释，但不能代替系统级内存差值。

SDK 使用独立进程时，可以分别观测宿主和子进程，却仍要报告两者的合计用户成本。关于 Java 泄漏的 retained path 分析见 [内存泄漏治理](../ch23-memory-practice/02-memory-leak-governance.md)，native 分配归因见 [Native 内存泄漏的线上分层监控](06-native-memory-leak-online-monitoring.md)。

### 5.3 Android 17 内存上限

Android 17 的 [所有应用行为变更](https://developer.android.com/about/versions/17/behavior-changes-all) 引入 App Memory Limits，但只在部分设备启用，限制值由设备配置决定，不存在一个适用于全部 Android 17 设备的固定阈值。

嵌入宿主进程的 SDK 内存会计入宿主进程。若命中限制，历史退出信息在 Android 17 上可能以 `REASON_OTHER` 出现，并在描述中包含 `MemoryLimiter:AnonSwap`；不要把更高版本新增的退出 reason 常量提前写进 Android 17 代码。准入实验至少覆盖一个可能启用该机制的低内存设备档位，并验证应用的降级和状态恢复。

## 6. 后台、CPU、网络与功耗

### 6.1 后台线程不等于后台执行资格

嵌入式 SDK 与宿主共享 UID（Linux 用户标识，也是 Android 权限与部分资源统计的边界）、进程状态、权限和后台限制。将任务提交到线程池、协程或 native 线程（通常由 `pthread` 创建），不会取得新的后台执行豁免。

治理时应清点：

- 常驻线程、线程池大小、线程优先级和空闲回收；
- WorkManager、JobScheduler、AlarmManager 与前台服务；
- `BroadcastReceiver`、`ContentObserver`、生命周期回调和系统监听器；
- 长连接、心跳、重试队列、DNS 与 TLS 会话；
- 定位、传感器、音频、蓝牙等受限资源。

需要持久保证的工作应按 [持久后台任务指南](https://developer.android.com/develop/background-work/background-tasks/persistent)选择系统 API。供应商不能仅以“内部线程实现”为由绕开应用对调度条件、重试上限与用户可见性的控制。

### 6.2 CPU 归因需要调用栈

`top` 可以发现进程或线程在某个采样窗口内占用 CPU，却不能说明谁安排了工作。simpleperf（Android NDK 提供的 CPU 采样与性能计数器工具）与 Perfetto 的调用栈更接近归因证据，但仍受这些条件影响：

- 应用是否可 profile，以及 Java/native 符号是否齐全；
- 异步提交后，执行线程可能只有公共执行器名称；
- 宿主回调 SDK、SDK 回调宿主时，顶部帧不代表工作发起者；
- 混淆、内联和 stripped native library（已剥除调试符号的原生库）会降低栈的可读性。

应用自有适配层应给关键任务增加稳定的 Trace 名称、请求 ID 和来源标签；线程与协程泄漏治理见 [20.8 线程与协程泄漏治理](08-thread-coroutine-leak-governance.md)。

### 6.3 网络字节不能只看 UID

`TrafficStats` 的 UID 统计适合观察应用总体网络量，但同 UID 内无法区分宿主和多个 SDK。应用 HTTP interceptor（HTTP 客户端的请求拦截器）只能覆盖经过该客户端的请求；SDK 的自建客户端、Cronet（Chromium 网络库）、WebView 或 native socket 可能绕开它。

较可靠的组合是：

- 实验环境抓包或受控代理，核对域名、协议、字节量和重试；
- 供应商提供请求标签、诊断回调或网络代理注入点；
- 在适配层传播请求 ID，把业务动作与后台流量对齐；
- 对照关闭 SDK、关闭某功能或更换版本后的场景差值；
- 将上传负载、协议开销、失败重试和长连接心跳分开统计。

网络请求的端到端分层方法见 [网络架构与连接管理](../ch24-io-network/05-mobile-network-connection-resilience.md)。

### 6.4 功耗看场景，不看请求次数

请求次数少不代表耗电低。频繁唤醒、差网络下重传、无线电尾部能耗、过密 Alarm、持续定位和音频资源都可能放大成本。应在固定场景中比较 CPU 时间、唤醒、调度、网络字节与电量指标。Macrobenchmark [`PowerMetric`](https://developer.android.com/reference/kotlin/androidx/benchmark/macro/PowerMetric) 仍带 `ExperimentalMetricApi` 标记；高精度 power/energy 数据依赖设备支持，而且结果反映测量窗口内的系统总消耗，并非某个应用或 SDK 的独占消耗。Perfetto power rails（设备暴露的硬件供电轨功耗计数器）也有相同的设备与归因边界；缺失数据不能按零消耗处理。

### 6.5 Android 17 的相关兼容点

除 App Memory Limits 外，Android 17 还需关注：

- target API 37 后，[`MessageQueue` 使用无锁实现](https://developer.android.com/about/versions/17/changes/messagequeue)；依赖反射访问其私有字段的 SDK 可能失效。公共 `Handler`/`Looper` 契约没有因此改变。
- Android 17 对所有应用施加了更严格的[后台音频交互限制](https://developer.android.com/about/versions/17/changes/bg-audio)：后台播放、音频焦点和音量操作需要可见 Activity，或一个类型不为 `SHORT_SERVICE` 的前台服务。target API 37 后，后台应用还需让该前台服务具备 while-in-use（由可见界面或用户操作授予的“使用期间”）能力；精确闹钟权限配合 `USAGE_ALARM` 音频流是例外。不满足条件时，播放和音量操作会静默失败，音频焦点请求返回 `AUDIOFOCUS_REQUEST_FAILED`。
- 后台调度、前台服务和权限仍由宿主应用共同负责合规与稳定性责任。

评估报告要写明 SDK 行为依赖的是公开 API 还是私有实现。Android 17 的目标 SDK 变更可从 [target 37 行为变更](https://developer.android.com/about/versions/17/behavior-changes-17)逐项核对。

## 7. Crash、ANR 与进程退出归因

### 7.1 栈顶是候选，不是判决

Java 异常栈顶出现 SDK 类，可能是 SDK 缺陷，也可能是宿主传入非法参数、调用顺序错误、线程模型不符或回调状态被破坏。建议把归因分为三档：

1. **候选相关**：堆栈或线程状态涉及 SDK。
2. **实验相关**：关闭 SDK、改变版本或改变调用路径后可稳定复现/消失。
3. **供应商确认**：供应商确认根因，并提供可验证修复或规避方案。

ANR（Application Not Responding，应用无响应）同样不能只看是否出现 SDK 帧。要找到主线程正在等待什么、锁或 Binder 的另一端是谁、后台线程是否持有资源，以及等待是否由宿主调用时机触发。

### 7.2 符号与版本是上线条件

每个 release 必须保存与产物一一对应的：

- R8 mapping 和 retrace 工具版本；mapping 记录混淆前后的名称对应关系，retrace 用它还原 Java/Kotlin 堆栈；
- 未剥离 native library 或可用符号文件；
- ABI、Build ID、SDK 精确版本和制品校验值；
- 上传到监控平台的符号处理结果。

[ndk-stack](https://developer.android.com/ndk/guides/ndk-stack)需要与崩溃二进制匹配的符号。若闭源 SDK 只提供 stripped `.so` 且供应商无法按 Build ID 符号化，团队就无法可靠定位 native crash；这项缺口应直接记入准入风险，并在发布前备齐材料。

聚类键是把疑似同一根因的事件归为一组的字段组合，建议包含异常类型或 signal（如 native crash 的 `SIGSEGV`）、归一化栈、SDK 版本、ABI、Android 版本、设备、进程和功能路径。归一化栈会去掉地址偏移等易变信息，保留稳定的调用结构。[Android vitals](https://support.google.com/googleplay/android-developer/answer/9859174?hl=zh-Hans)可能标记“可能与 SDK 有关”的问题，这仍是线索；SDK 供应商可通过 [Google Play SDK Console](https://support.google.com/googleplay/android-developer/answer/12246095?hl=zh-Hans)接收聚合信息并上传反混淆文件。

对于没有 Java/Native 崩溃栈的异常退出，应结合 `ApplicationExitInfo`（系统保存的历史进程退出原因）、系统日志、内存样本和前台状态分析。不要把低内存杀进程、用户停止、系统更新与 SDK crash 混成同一指标。

## 8. 包体积、R8 与供应链

### 8.1 体积看最终交付字节

供应商宣称的 AAR 大小不能代表用户下载或安装增量。资源压缩、代码复用、ABI 拆分、语言/密度拆分和动态交付都会改变结果。应比较同配置 A/B App Bundle，并分别报告：

- 压缩下载增量；
- 安装后 DEX、资源和 native library 增量；
- 各 ABI/密度/语言组合的影响；
- 动态特性是否只在需要时交付。

DEX 方法数可帮助发现代码量变化，但不能替代字节、启动类加载和运行时成本。

### 8.2 审查 consumer R8 规则

SDK 携带的宽泛 `-keep` 规则可能保留无关代码、阻止优化或放大反射面。审查时应：

- 查看合并后的 R8 配置；
- 用 `-whyareyoukeeping` 解释关键类为什么保留；
- 核对反射、JNI、序列化所需范围；
- 比较规则收窄前后的构建与回归测试；
- 每个 release 单独保存 mapping，禁止跨版本混用。

不能为了缩小体积盲删供应商规则。收窄规则必须有功能测试和反混淆验证，必要时由供应商给出可维护的最小规则。

### 8.3 传递依赖冲突

Gradle 的版本调解可能让一个 SDK 运行在它没有验证过的依赖版本上。编译通过也不说明运行路径兼容。对于关键公共库，应通过 `dependencyInsight` 找出选择原因，固定可验证版本，并覆盖涉及二进制兼容、资源、序列化与网络协议的集成测试。

供应链记录还应包含来源仓库、制品校验、许可证、SBOM（Software Bill of Materials，软件物料清单）、漏洞响应与下架策略。远程下发未知代码或通用动态修补不是稳妥的 SDK 修复方案；通常应依次考虑关闭能力、回退已验证版本和发布修复包。

## 9. 准入：阈值来自应用预算

不存在适用于所有应用的“启动不得增加 X ms、内存不得增加 Y MB”。社交应用、车机、低内存设备与支付确认页的预算不同。阈值应从应用 SLO（Service Level Objective，服务级目标）、重点场景、设备档位和当前余量推导，并为多个 SDK 的合计成本留出预算。

一份可执行的评分表应覆盖：

| 领域 | 评估项 |
| --- | --- |
| 价值 | 用户能力、业务收益、替代方案、功能负责人 |
| 启动 | 冷/温/热启动 P50/P95、主线程同步时间、Provider 入口 |
| 内存 | 稳态/峰值 RSS/PSS、Java 保留对象与保留大小、native 分配、低内存恢复 |
| 流畅度 | 关键页面帧时间、主线程任务、Binder 与远端渲染 |
| 后台 | CPU、线程、唤醒、调度、网络字节、重试 |
| 稳定性 | Crash、ANR、异常退出、符号与供应商响应 |
| 包体积 | 下载/安装增量、DEX、资源、各 ABI `.so` |
| 安全隐私 | 权限、组件、端点、数据字段、同意与删除路径 |
| 运维 | 指标、日志、开关、回退、移除时间、事故联系人 |

建议按五个阶段检查：

1. **静态检查**：依赖、Manifest、权限、组件、R8、native 库和数据清单。
2. **隔离 A/B**：只改变一个 SDK，测量标准场景的边际成本。
3. **集成压力**：在全部 SDK 同时工作时检查锁、线程、内存和网络竞争。
4. **内测与小流量发布**：观察分设备档位、版本、ABI 和进程的回归。
5. **持续监控**：每次 SDK 或构建工具升级重放基准与差异检查。

“每个 SDK 单独达标”仍可能让总预算超标。准入记录必须同时显示该 SDK 的边际成本和应用剩余预算。

## 10. 退出能力要在接入时设计

### 10.1 用应用自己的接口隔离供应商

业务代码若到处暴露供应商类型，替换和禁用都会变成大规模改造。应用应定义自己的领域接口，也就是由应用控制、只表达业务能力的抽象；供应商 API 留在适配层，由适配层处理同意、初始化、状态和异常。

下面的简化示例展示一个可禁用的统计接口：

```kotlin
interface Analytics {
    fun record(event: AnalyticsEvent)
}

class GovernedAnalytics(
    private val provider: AnalyticsProvider,
) : Analytics {
    private val enabled = AtomicBoolean(false)

    fun enableAfterConsent() {
        if (enabled.compareAndSet(false, true)) {
            provider.start()
        }
    }

    override fun record(event: AnalyticsEvent) {
        if (enabled.get()) {
            provider.record(event)
        }
    }

    fun disable() {
        enabled.set(false)
        provider.stopIfSupported()
    }
}
```

这里的开关阻止后续调用，并只在供应商支持时执行停止操作。它不能从进程中卸载已经加载的 DEX/`.so`，也不能自动撤销静态初始化、未知监听器或已经排队的任务；SDK 必须提供成对的注册/反注册和可重复调用的停止契约。

### 10.2 远程开关的边界

远程配置适合阻止后续初始化、停止新请求或隐藏依赖 SDK 的功能，但要满足：

- 读取开关不依赖待禁用 SDK；
- 冷启动早期即可得到安全默认值；
- 禁用路径不触发无限重试或 crash loop（应用启动后反复崩溃、再次拉起的循环）；
- 本地保留上次可信状态并设过期策略；
- 隐私同意撤回能停止采集并处理待上传数据；
- 服务端、客户端和供应商控制台状态可核对。

若 SDK 在进程创建时由 Provider 自动运行，远程开关读取往往已经太晚。高风险 SDK 应改为显式初始化，或至少让 Provider 只做轻量登记，不执行耗时的网络或磁盘操作。

## 11. 常见 SDK 类型的治理重点

这些类别用于说明检查方式，不代表对某个供应商实现的评价。具体结论仍以精确版本、配置和发布产物为准。

### 11.1 多通道推送

华为、小米、OPPO、vivo、FCM 等通道通常按设备能力、地区和业务策略选择。治理目标不是让全部通道在每个进程中同时启动：

- 由应用层选择当前有效通道，避免无关通道执行重初始化；
- 统一推送 token 的状态流转，明确生成、更新、失效、账号切换和注销时各自执行什么操作；
- 服务端做消息 ID 去重，客户端记录通道与送达路径；
- 为切换、失败回退和供应商服务不可用设定边界；
- 分通道观测初始化、线程、网络、送达率与耗电。

推送到达率不能只靠增加心跳或并行初始化来换取；任何后台策略都要符合平台限制和用户设置。

### 11.2 统计、Crash 与错误监控

友盟、Bugly、Sentry 等产品覆盖的能力并不完全相同。常见控制点包括：

- 在用户同意和数据配置满足条件后初始化；
- 统一事件 schema（字段、类型、命名和版本约定）、采样、批量大小、上传条件和重试；
- 限制 breadcrumb（崩溃前的操作与状态记录）、附件、线程栈与本地队列上限；
- 保留与业务版本匹配的 mapping 和 native symbols；
- 让核心错误观测不依赖可能引发故障的同一执行链。

降低事件采样率只能减少一部分上传与服务端负载，不一定降低初始化、常驻线程或基础缓存成本，仍需分别测量。

### 11.3 广告与远端内容

穿山甲、优量汇等广告 SDK 的版本与配置变化频繁，不能用供应商名称代替评估。建议：

- 只在广告场景临近使用时初始化或预热；
- 预取必须有数量、超时、内存和取消上限；
- 分开测量 SDK 初始化、请求、素材下载、WebView、视频解码，以及把 View 挂入窗口的成本；
- 检查远端进程、Binder、Surface 和宿主页面的帧时间；
- 广告不可用时让页面能快速降级，避免阻塞主流程；
- 将点击、展示和收入校验与性能诊断 ID 对齐，但避免记录敏感内容。

WebView 或视频卡顿不一定由 SDK 主线程代码直接引起；需结合渲染、Binder、网络与媒体缓冲时间线定位。

## 12. SDK Runtime：只按遗留路径评估

### 12.1 Android 17 已停止支持新接入

Google 在 2025 年 10 月 17 日宣布[退役 SDK Runtime 等 Privacy Sandbox 技术](https://privacysandbox.google.com/blog/update-on-plans-for-privacy-sandbox-technologies)，官方[功能状态页](https://privacysandbox.google.com/overview/status)也把 Android SDK Runtime 标为计划逐步退出。Android 17 / API 37 的 [`SdkSandboxManager`](https://developer.android.com/reference/android/app/sdksandbox/SdkSandboxManager) 已废弃，API 文档明确说明 SDK sandbox 不再受支持；AndroidX `privacysandbox-sdkruntime` 的 [`1.0.0-alpha19`](https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime) 同样已废弃且不会继续更新。

API 符号、旧设计页或系统服务类仍然存在，不能据此判断能力可用于新项目。Android 17 AOSP 仍保留 [`SdkSandboxManagerService`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/service/java/com/android/server/sdksandbox/SdkSandboxManagerService.java) 等兼容代码，但面向 API 37 的接入决策应服从公开 API 的废弃契约。新项目不应再围绕 runtime-enabled SDK bundle、`SdkSandboxManager.loadSdk()` 或旧 sandbox 生命周期设计广告架构。

现有产品需要按 Android 版本和 SDK 精确版本记录运行路径：Android 14–16 上只维护已经发布的遗留能力，并做可用性探测和失败降级；Android 17 上关闭 sandbox 路径，转回受支持的普通嵌入式 SDK 或供应商明确支持的其他进程模型。

### 12.2 遗留隔离路径仍要计算合计成本

[SDK Runtime 架构说明](https://privacysandbox.google.com/private-advertising/sdk-runtime/architecture)与[兼容模式](https://privacysandbox.google.com/private-advertising/sdk-runtime/backward-compatibility)仍可用于理解 Android 14–16 的历史行为。旧 Runtime 路径把 SDK 放进每个应用对应的独立进程，宿主通过 Binder 与它通信，两端没有共享 Java/native heap；兼容路径则把 DEX 载入宿主进程，只用独立 classloader 隔开类名空间。

对仍在维护的遗留版本，独立进程改善了地址空间隔离，也让宿主与 Runtime 进程的内存更容易分别观察；代价包括：

- Runtime 和 SDK 的冷启动；
- 独立进程的固定内存；
- Binder 参数序列化、跨进程往返与回调调度；
- 远端 UI 的 Surface 与帧同步；
- 进程死亡后的状态恢复和重新加载。

当旧 Runtime 路径仍在运行时，评估应报告宿主与 Runtime 进程的合计 PSS/RSS，并同时测量加载延迟、Binder 回调、远端 UI 帧时间、进程死亡率与恢复成功率。两端没有共享堆；应用商店曾提出的可信分发可能影响下载或磁盘存储，不能据此推断运行时 RAM 会下降。

历史兼容方案由 Android Gradle Plugin（AGP）和 Bundletool 构建包含 SDK 的应用变体，再由 SDK Runtime client library 从应用 assets 提取 DEX，并通过独立 classloader（类加载器）载入宿主进程。类加载器能降低类名冲突，却不提供进程隔离。AndroidX 兼容库已经停止更新，所以它只能解释现有发布包的行为，不能充当 Android 17 的替代方案或新接入路径。

迁移时应验证禁用开关、Manifest 与构建依赖清理、普通 SDK 回退、进程死亡和数据合规路径。每个发布版本都要记录实际运行路径，避免把 Android 14–16 的遗留行为推到 Android 17。

## 13. 一份可复用的检查清单

### 接入前

- [ ] 明确用户价值、能力负责人、供应商联系人和替代方案。
- [ ] 固定坐标、版本、来源、校验值、许可证和数据处理关系。
- [ ] 检查 release 依赖图、Manifest、权限、组件、进程、R8 与 `.so`。
- [ ] 要求 Java mapping、native symbols、Build ID 方案和响应时限。
- [ ] 设计应用自有接口、同意门、显式初始化、禁用与回退路径。
- [ ] 在目标设备档位完成隔离 A/B 与全部 SDK 集成实验。

### 发布前

- [ ] 对比 AAB/APK 的下载、安装、DEX、资源与 ABI 增量。
- [ ] 固定编译模式测冷/温/热启动，并保存 Trace。
- [ ] 测稳态/峰值内存、CPU、线程、网络、功耗和关键页面帧时间。
- [ ] 完成 Crash/ANR/退出符号化与故障注入，即主动制造断网、超时、进程死亡等受控故障。
- [ ] 验证远程禁用、供应商不可用、无网、进程死亡和低内存恢复。
- [ ] 按版本、设备档位、ABI、进程和功能配置设置小流量观测。

### 运行中

- [ ] SDK 升级触发完整依赖差异和性能回归。
- [ ] 对新增权限、组件、端点、线程和调度做自动检查。
- [ ] 定期演练禁用、回退、符号化和供应商响应。
- [ ] 结合业务价值复查闲置 SDK，移除没有清晰负责人的能力。
- [ ] 同时跟踪单 SDK 边际成本和应用总体预算。

## 小结

SDK 治理的输出不该是一份静态名单，而应是一组能被重复执行的实验、制品差异和运行时证据。当团队能回答“哪段代码在什么条件下运行、成本如何复现、出错后如何停止”时，SDK 才处于可控状态。

## 参考资料

- [AOSP Android 17 `ActivityThread`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP Android 17 `SdkSandboxManagerService`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/service/java/com/android/server/sdksandbox/SdkSandboxManagerService.java)
- [Android Common Kernel `android17-6.18-2026-06_r6` proc 文档](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/filesystems/proc.rst)
- [Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup)
- [Macrobenchmark 概览](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Macrobenchmark 指标](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [Android 内存管理概览](https://developer.android.com/topic/performance/memory-management)
- [Android 17 所有应用行为变更](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android 17 target 37 行为变更](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Privacy Sandbox 技术退役公告](https://privacysandbox.google.com/blog/update-on-plans-for-privacy-sandbox-technologies)
- [Privacy Sandbox 功能状态](https://privacysandbox.google.com/overview/status)
- [Android 17 `SdkSandboxManager` API](https://developer.android.com/reference/android/app/sdksandbox/SdkSandboxManager)
- [AndroidX `privacysandbox-sdkruntime` release notes](https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime)
- [SDK Runtime 架构](https://privacysandbox.google.com/private-advertising/sdk-runtime/architecture)
- [SDK Runtime 兼容模式](https://privacysandbox.google.com/private-advertising/sdk-runtime/backward-compatibility)
- [Google Play SDK Index](https://developer.android.com/distribute/sdk-index)
- [Google Play SDK Index](https://support.google.com/googleplay/android-developer/answer/13326895?hl=zh-Hans)
