---

title: androidx.tracing（Tracing SDK）
chapter: '19'
section: '19.10'
status: "finalized"
applicable_versions: Android 5 (API 21) - Android 17 (API 37); latest AndroidX Tracing 2.0 requires API 23
last_verified: '2026-08-14'
last_verified_against: AndroidX Tracing 2.0.0 stable and 1.3.0 compatibility artifacts + Tracing Perfetto 1.0.1 + Benchmark 1.4.1 stable / 1.5.0-rc01 + Android 17 Trace Java/JNI + NDK tracing docs
confidence: medium
tags:
- apm
- tracing
- perfetto
- androidx
- performance-tools
related_chapters:
- '19.0'
sources:
- type: official
  path: https://developer.android.com/topic/performance/tracing
- type: official
  path: https://developer.android.com/reference/androidx/tracing/package-summary
- type: official
  path: https://developer.android.com/topic/performance/jankstats
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview
- type: official
  path: https://developer.android.com/ndk/reference/group/tracing
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/tracing
- type: official
  path: https://dl.google.com/android/maven2/androidx/tracing/tracing/maven-metadata.xml
- type: official
  path: https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/2.0.0/tracing-android-2.0.0.aar
- type: official
  path: https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/2.0.0/tracing-android-2.0.0-sources.jar
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/benchmark
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
---
# androidx.tracing（Tracing SDK）

## 它给系统 trace 增加业务语义

系统 trace 是把系统执行活动按时间排列的记录。它能显示线程调度、Binder 进程间通信、I/O、渲染与锁等待，却无法自行判断某段应用代码正在解析首页数据，还是在提交支付结果。`androidx.tracing` 2.0.0 保留的经典 `Trace.*` / `trace {}` API 可以给这些代码区间加上稳定名称，使 Perfetto、Android Studio System Trace 和 Macrobenchmark 采集的 trace 出现应用自定义 slice。

这里要把三件事分开：

- **trace slice** 是有开始和结束的命名时间片，记录区间何时发生，以及它落在哪条 track（时间线轨道）上。
- **性能指标**负责统计分位数、失败率、慢帧率等聚合结果。
- **根因分析**需要把 slice 与线程状态、CPU 调度、Binder、I/O、帧时间线等证据放在一起读。

因此，经典 `androidx.tracing` 事件适合回答“慢发生在哪个业务阶段”，但不会上传数据，也不会自动解释慢因。slice 的持续时间是墙上时间（wall time），即现实中从开始到结束经过的时间；其中可以包含 CPU 执行、锁等待、I/O 等待和被调度器换出的时间，不能直接当作 CPU time（线程实际占用 CPU 的时间）。

### 核验基线

截至 2026-08-14，采用以下版本边界：

| 对象 | 核验锚点 | 已核实的边界 |
|---|---|---|
| Android 平台 | Android 17 / API 37 / `android-17.0.0_r1` | `android.os.Trace` 的同步 section、异步 section、counter 与 Java Native Interface（JNI）路径 |
| AndroidX 稳定线 | `androidx.tracing:tracing:2.0.0` | 发布于 2026-08-12；Android 变体最低 API 23；同时包含经典 API 与新的进程内 tracing API |
| AndroidX 兼容线 | `androidx.tracing:tracing:1.3.0` | 发布于 2025-04-23；Android 变体最低 API 21，供仍需覆盖 API 21-22 的应用使用 |
| Tracing Wire | `androidx.tracing:tracing-wire:2.0.0` | 给 2.0 进程内 API 提供 Perfetto 格式的 `TraceSink` 实现 |
| Tracing Perfetto | `androidx.tracing:tracing-perfetto:1.0.1` | 独立的 Perfetto SDK 接入组件，不等同于经典 `Trace.beginSection()`，也不等同于 `tracing-wire` |
| AndroidX Benchmark | 稳定版 `1.4.1`；预发布版 `1.5.0-rc01` | 1.5 预发布线可采集并合并目标包的进程内 trace |
| Kernel | `android17-6.18-2026-06_r6` | 仅在联读 CPU 调度、唤醒等 kernel（操作系统内核）事件时作为源码锚点 |

API 23+ 项目当前应使用稳定坐标 `androidx.tracing:tracing:2.0.0`。如果应用仍需运行在 API 21-22，可继续使用 1.3.0 兼容线；下面保留的是这种低版本依赖写法。

```kotlin
dependencies {
    implementation("androidx.tracing:tracing:1.3.0")
}
```

Gradle 会为 Android 目标选择对应版本的 `tracing-android` variant（针对 Android 的发布变体）。这里的 artifact 指 Maven 仓库中的发布组件。自 1.3.0 起，原 `tracing-ktx` 实现已并入主 artifact；使用 1.3.0 或 2.0.0 都不必再单独添加 `tracing-ktx`。

## 哪些位置值得手动标记

判断时应看“这个区间能否缩小性能问题的排查范围”，函数的重要程度并非主要依据。通常值得长期保留的点包括：

- 启动：配置读取、依赖初始化、首屏数据准备、首个可交互状态。
- 列表：diff（新旧列表的差量）计算、分页合并、批量 bind（把数据绑定到列表项）、预取和图片解码。
- 存储：关键数据库查询、事务提交、缓存反序列化。
- 交互：页面转场准备、支付提交、播放器 prepare、相机初始化。
- 跨线程任务：从业务请求开始，到后台工作完成或 UI 提交结束的逻辑跨度。
- Native 重任务：编解码、图像处理、渲染资源准备和大块数据转换。

下面这些位置通常不该逐次打点：

- `onDraw()`、像素循环、序列化字段循环等高频内层。
- 已被一个清晰父 slice 覆盖、且拆开后没有诊断价值的小函数。
- 只为临时观察而加入、问题结束后不再使用的细碎标记。
- 名称必须携带用户 ID、URL、搜索词或订单号才看得懂的事件。

一条长期 slice 应当对应一个稳定业务阶段。需要知道循环处理了多少项时，用 counter 或离线统计；不要为每一项创建不同名称的 slice。

## 三种事件：同步 slice、异步 slice、counter

### 同步 slice：同一线程上的嵌套区间

同步 section 遵循线程内栈语义：`beginSection()` 与 `endSection()` 必须在同一线程配对，嵌套顺序必须后进先出。Kotlin 优先使用 `trace {}`，它用 `finally` 关闭区间。

下面的例子用于区分主线程上的列表提交和其中的 diff 计算。

```kotlin
import androidx.tracing.trace

fun submitFeed(items: List<FeedItem>) {
    trace("Home#submitFeed") {
        val result = trace("Home#calculateDiff") {
            calculateDiff(items)
        }
        adapter.dispatchUpdates(result)
    }
}
```

在 Perfetto 中，应当到调用 `submitFeed()` 的线程轨道查找 `Home#submitFeed`；`Home#calculateDiff` 会成为它的子 slice。父 slice 很长而子 slice 很短时，耗时还在 diff 之外，不能把父区间全归因于 diff。

Java 代码可以直接调用 `Trace.beginSection()` / `endSection()`，但必须用 `try-finally` 保证异常路径也闭合。

```java
import androidx.tracing.Trace;

void decodeThumbnail(byte[] encoded) {
    Trace.beginSection("Image#decodeThumbnail");
    try {
        decoder.decode(encoded);
    } finally {
        Trace.endSection();
    }
}
```

如果这段方法在解码线程执行，slice 就出现在该解码线程，而不会自动出现在主线程。漏掉 `finally` 会破坏当前线程后续 section 的嵌套关系。

### 异步 slice：跨线程、跨挂起点的逻辑跨度

异步 section 由“名称 + `Int` cookie”配对。cookie 是区分同名并发任务的整数标识；开始和结束可以位于不同线程，也不要求按栈嵌套，同名且时间重叠的任务必须使用不同 cookie。它适合表示一次跨线程加载、一次远端请求或一段会挂起的协程任务。

AndroidX Tracing 2.0.0 保留了 suspend `traceAsync()`；suspend 表示这个 Kotlin 函数可以挂起后再恢复。下面的例子让一个异步 span（跨线程表达同一逻辑工作的区间）覆盖完整加载过程，同时保留 I/O 线程和主线程各自的同步 slice。

```kotlin
import androidx.tracing.trace
import androidx.tracing.traceAsync
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private val nextTraceCookie = AtomicInteger(1)

suspend fun loadFirstFeed(): List<FeedItem> {
    val cookie = nextTraceCookie.getAndIncrement()
    return traceAsync("Home#loadFirstFeed", cookie) {
        val items = withContext(Dispatchers.IO) {
            trace("Home#requestFirstFeed") {
                repository.loadFirstFeedBlocking()
            }
        }

        withContext(Dispatchers.Main.immediate) {
            trace("Home#submitFirstFeed") {
                adapter.submitList(items)
            }
        }
        items
    }
}
```

`traceAsync()` 的 2.0.0 源码仍在 `try-finally` 中结束异步 section，所以正常返回、异常和协程取消都会走关闭路径。Perfetto 中，`Home#loadFirstFeed` 表示墙上时间跨度；`Home#requestFirstFeed` 要到 I/O 线程查看，`Home#submitFirstFeed` 要到主线程查看。前者不能代替后两条线程内证据。

不要用同步 `trace {}` 包住包含 `delay()`、`withContext()` 或其他挂起点的代码。协程恢复后可能换线程，而同步 section 要求 begin/end 位于同一线程；即使某次测试恰好恢复到原线程，也不能把这种调度结果当作 API 保证。

对于线程池（executor）、回调或消息队列，规则相同：

1. 提交任务前生成 cookie 并开始异步 section。
2. 在任务的唯一终态关闭同名、同 cookie 的 section。
3. 提交被拒绝、任务取消、回调不再投递时也要关闭。
4. 每条实际执行线程再用同步 section 标记 CPU 工作。

如果现有抽象无法保证“每个 begin 恰好对应一次 end”，先修正任务生命周期，再加 async trace。用多个 `catch` 和回调分别关闭，很容易形成漏关或重复关闭。

### Counter：观察随时间变化的值

counter 表示某个时刻的数值，不表示一段耗时。它适合队列深度、缓存条目数、在途请求数等低频状态。

下面的例子在解码队列变化时写入固定名称的 counter。

```kotlin
import androidx.tracing.Trace

fun onDecodeQueueChanged(pendingCount: Int) {
    Trace.setCounter("Image#decodeQueueDepth", pendingCount)
}
```

在 Perfetto 中搜索 `Image#decodeQueueDepth`，应当看到一条随时间变化的 counter 轨道。AndroidX 1.3.0 只有 `Int` 参数；2.0.0 保留这个重载，并增加 API 29+ 可用的 `Long` 重载。Android 17 平台 `android.os.Trace.setCounter()` 接受 `long`。写公共库时要注明所依赖的 AndroidX 版本和最低 API，不能把三者混写成同一签名。

## 命名是一份可维护的诊断协议

建议统一使用 `Module#Action`，必要时再加一个固定层级，如 `Module#Stage.Step`。名称描述业务阶段，不绑定类名、方法名或当前架构。

| 场景 | 推荐名称 | 不推荐 | 原因 |
|---|---|---|---|
| 应用启动 | `Startup#loadConfig` | `ConfigRepositoryImpl.loadV3` | 实现重构后仍可比较 |
| 首页首屏 | `Home#loadFirstFeed` | `feed_4938102` | 避免高基数，即避免名称数量随请求或内容数量增长 |
| 详情页 | `Detail#renderContent` | `Detail#render/sku-123` | 不写业务 ID |
| 支付提交 | `Checkout#submit` | `pay/alice@example.com` | 不写用户数据 |
| 图片解码 | `Image#decodeThumbnail` | 完整图片 URL | 避免隐私与超长名称 |
| 数据库查询 | `Database#loadTimeline` | 完整 SQL | 防止敏感参数进入 trace |

团队可以按下面四条规则评审名称：

- **稳定**：相同阶段跨版本保留同名，指标才能纵向比较。
- **有界**：动态变化只能来自少量固定枚举，如 `thumbnail`、`preview`、`full`。
- **可定位**：名称能指向业务阶段，但无需暴露类和方法实现。
- **无敏感数据**：trace 文件可能被分享、上传或附在缺陷单中。

Android 17 的平台 `Trace.beginSection()` 限制名称最多 127 个 Unicode code unit。这里的 code unit 是 Java `String.length` 使用的 UTF-16 计数单位，一个可见字符不一定只占一个单位。采集已启用时，直接向平台 API 传入超长名称会抛 `IllegalArgumentException`；AndroidX 1.3.0 与 2.0.0 都会先截断到 127。截断仍可能让不同名称变得相同，所以设计时就应保持短且稳定。`|`、换行和空字符属于底层保留字符，也不应放入名称。

## Android 17 的调用链：不要固定套用旧版 `trace_marker` 叙述

以 `android-17.0.0_r1` 为准，AndroidX 2.0.0 经典 `trace {}` API 的同步调用链可以概括为：

```text
androidx.tracing.trace("Home#submitFeed")
  -> androidx.tracing.Trace.beginSection()
  -> android.os.Trace.beginSection()
  -> nativeTraceBegin(TRACE_TAG_APP, name)
  -> tracing_perfetto::traceBegin(tag, name)
```

这条链说明两个边界：

- AndroidX 负责兼容封装、异常安全辅助和名称截断，平台仍会检查 `TRACE_TAG_APP` 是否启用。
- Android 17 的 `android_os_Trace.cpp` 已把 JNI 调用交给 `tracing_perfetto`，不能再把所有版本概括成“每次直接向 `trace_marker` 执行一次 `write()`”。

因此，也不能从旧版实现推导 Android 17 的固定纳秒开销、锁竞争方式或系统调用次数。若要判断打点是否影响热路径（高频或对延迟敏感的执行路径），应当在目标构建、目标设备和实际采集配置上运行 Microbenchmark（针对一小段代码的重复性能测试），并同时比较 trace 开启与关闭两种状态。

## 版本与可见性：允许写入不等于正在采集

`Trace.isEnabled()` 为 `true` 需要同时满足两件事：当前存在能接收应用事件的 trace 会话，并且该进程被允许写 app trace。Android 12 以后“默认允许应用 tracing”不表示系统一直在后台记录。

下表中的 non-debuggable 表示应用关闭调试能力，profileable 表示应用允许 shell 等受控工具进行性能采集。

| 平台范围 | 非 debuggable 进程的允许条件 | AndroidX 经典 async/counter 路径 |
|---|---|---|
| API 21-22 | 只能使用 1.3.0；应用启动早期调用 `Trace.forceEnableAppTracing()` | 反射平台隐藏的 `asyncTraceBegin`、`asyncTraceEnd`、`traceCounter` |
| API 23-28 | 1.3.0 或 2.0.0；应用启动早期调用 `Trace.forceEnableAppTracing()` | 反射同一组平台隐藏方法 |
| API 29-30 | manifest 设置 `<profileable android:shell="true"/>`，或调用 `forceEnableAppTracing()` | 调用 API 29 新增的公开平台方法 |
| API 31-37 | 默认允许；显式设置 `<profileable android:enabled="false"/>` 或 `android:shell="false"` 会限制该能力 | 调用公开平台方法；`forceEnableAppTracing()` 在这一范围无操作 |

当前稳定版 `tracing-android:2.0.0` 的 `minSdkVersion` 是 23；兼容线 1.3.0 的下限是 21。两版源码都保留了更低平台的兼容分支说明，但发布物 manifest 会先限制依赖范围，不能据此宣称 artifact 支持 API 18。

采集侧也要包含目标应用：

- Macrobenchmark 会自动采集目标应用的自定义 trace point。
- 旧 systrace 命令需要用 `-a <package>` 指定应用。
- 自定义 Perfetto 配置要把目标包加入相应的 atrace app 配置；atrace 是 Perfetto 用来接收 Android 系统与应用 trace point 的数据源之一。

正式性能结论宜来自 non-debuggable、profileable 且接近发布配置的构建。debuggable 包的调试设施、编译选项和运行时行为可能改变时间分布。

## 开销控制：少而稳定，动态内容延迟计算

Tracing 没有一个适用于所有设备的固定开销数字。成本会随是否采集、平台实现、事件类型、名称处理、缓冲区压力和调用频率变化。工程上应采用以下约束：

- 把 section 提到循环外，观察一次批处理，不给每个元素打点。
- 优先使用静态名称；只有诊断需要且取值空间很小时才构造动态名称。
- 用 `Trace.isEnabled()` 避免只为 trace 做昂贵计算。
- 用同一套 Macrobenchmark 或 Microbenchmark 对比打点前后，关注 p50/p95 与 trace 丢失情况；p95 表示 95% 的观测值不超过该数值。
- 父 slice 已足够定位时，删除重复的子 slice。

AndroidX 2.0.0 保留 lazy label（延迟计算名称）重载。下面的例子只在 tracing 启用时构造带固定枚举的名称。

```kotlin
import androidx.tracing.trace

fun bindCard(card: Card, viewType: CardViewType) {
    trace(lazyLabel = { "Feed#bind/${viewType.traceName}" }) {
        renderer.bind(card)
    }
}
```

`traceName` 应是受控枚举，如 `text`、`image`、`video`，不能返回 item ID。该 slice 位于执行 `bindCard()` 的线程；如果它每帧出现很多次，应改为在批量 bind 外只保留一个父 section。

## Native 标注：与 Java 使用同一套名称

Android Native Development Kit（NDK）的 `<android/trace.h>` 从 API 23 提供同步 section，API 29 增加异步 section 与 counter。Native 同步 section 也要求在同一线程正确嵌套。

下面的 RAII（Resource Acquisition Is Initialization，以对象生命周期管理资源）封装用于保证 early return（函数提前返回）或 C++ 异常不会漏掉 `ATrace_endSection()`。

```cpp
#include <android/trace.h>

class ScopedTrace final {
public:
    explicit ScopedTrace(const char* name) {
        ATrace_beginSection(name);
    }

    ~ScopedTrace() {
        ATrace_endSection();
    }

    ScopedTrace(const ScopedTrace&) = delete;
    ScopedTrace& operator=(const ScopedTrace&) = delete;
};

void DecodeFrame(const EncodedFrame& frame) {
    ScopedTrace trace("Video#decodeFrame");
    DecodeOneFrame(frame);
}
```

Perfetto 会把 `Video#decodeFrame` 放在执行 `DecodeFrame()` 的 native 线程轨道上。Java 外层若有 `Video#processFrame`，两者只有在同一线程同步调用时才形成自然嵌套；JNI 前后换了线程时，要用 async span 或 Perfetto flow（连接两个 slice 的箭头）表达逻辑联系。

`ATrace_isEnabled()` 可用于跳过只服务于 tracing 的昂贵名称计算。不要为了调用它而包住正常业务逻辑，业务逻辑无论 tracing 状态如何都必须执行。

## 与 Perfetto SDK、btrace、Macrobenchmark 的分工

这些工具都能产出或消费 trace 信息，但抽象层级不同。

| 工具 | 适合的任务 | 关键边界 |
|---|---|---|
| 经典 `Trace.*` / `trace {}`（2.0.0；API 21-22 用 1.3.0） | 长期保留少量业务 section、async span、counter | 写入系统 trace；不上传、不聚合；官方仍推荐用于低频事件 |
| `Tracer` + `tracing-wire:2.0.0` | 进程内 Perfetto 格式 trace、分类、metadata（键值附注）、flow 与协程上下文传播 | 最低 API 23；要设计 `TraceDriver`、`TraceSink`、文件和丢事件生命周期 |
| `tracing-perfetto:1.0.1` | 通过独立 Perfetto SDK 组件记录应用事件 | 有自己的 native binary 与启用握手（handshake），与经典 API、`tracing-wire` 都是不同接入路径 |
| btrace / RheaTrace | 专项抓取方法级调用现场，即记录大量方法进入和退出 | 数据量和侵入面更大，适合定向诊断 |
| Macrobenchmark 1.4.1 / 1.5.0-rc01 | 在测试侧启动、交互并采集 trace；1.5 预发布线可合并进程内 trace | `TraceSectionMetric` 是实验 API；默认只看目标包；1.5.0-rc01 尚未成为稳定版 |
| Perfetto UI / Trace Processor | 人工或 SQL 联读系统与应用证据 | 工具负责展示和查询，不替应用补业务语义 |

AndroidX 2.0.0 的新 `Tracer` API 与经典 `Trace.beginSection()` 是两条用途不同的接口面。经典 API 仍写系统 trace，也没有被弃用。新路径由 `TraceDriver` 持有 `Tracer` 并管理一次 tracing 生命周期，`TraceSink` 决定事件如何序列化和输出；`tracing-wire` 提供 Perfetto 格式实现。category 用于按类别筛选事件，metadata 给事件附加键值信息，instant event 表示没有持续时间的瞬时点。新 API 还支持 counter、Perfetto flow 和 `traceCoroutine()`。Android Studio System Trace 目前不会直接采集这条进程内路径，Benchmark 1.5.0-rc01 的 `PerfettoCapture` / `PerfettoTraceRule` 可以采集并在事后合并目标包的进程内 trace。即使 2.0.0 已稳定，接入新路径时仍要设计采集启动方式、文件生命周期、丢事件策略、体积与工具兼容性。

Benchmark 稳定版 1.4.1 的 `TraceSectionMetric(sectionName)` 仍是实验 API，默认使用 `Mode.Sum`，输出全部匹配 section 的总时长与次数；只有显式选择 `Mode.First` 才取第一条。这里的 mode 是把多条同名 section 汇成指标的方式。它默认只读取目标包。用于基准指标的 section 要把生命周期和 mode 写清楚，并用生成的 trace 复核所选区间。

## 与线上指标建立同名索引

经典 `androidx.tracing` 不会把事件送到线上；2.0 进程内 API 也只负责本地记录，上传仍需应用自行设计。可以用一张受版本控制的阶段表，让 Perfetto slice、JankStats context 和 APM（Application Performance Monitoring，应用性能监控）span 指向同一个业务语义；span 是 APM 中表示一次操作区间的记录。

| 业务阶段 | Perfetto slice | JankStats state | APM 事件 |
|---|---|---|---|
| 应用初始化 | `Startup#appOnCreate` | `phase=startup_init` | `startup.app_on_create` |
| 首屏数据 | `Home#loadFirstFeed` | `phase=first_feed_load` | `home.first_feed_load` |
| 首页提交 | `Home#submitFirstFeed` | `phase=first_feed_submit` | `home.first_feed_submit` |
| 详情内容可见 | `Detail#renderContent` | `phase=content_render` | `detail.content_render` |
| 支付提交 | `Checkout#submit` | `phase=checkout_submit` | `checkout.submit` |

映射表只保存稳定阶段。请求 ID、trace ID 等关联字段可进入受控的日志或 APM 字段，不应拼进 Perfetto slice 名称。

JankStats 的 `PerformanceMetricsState` 是状态，不是瞬时事件。进入阶段时写入，离开阶段时移除或替换；若忘记清理，后续帧会继续携带过期上下文。线上看到 `phase=first_feed_submit` 的慢帧后，可以在线下复现并搜索 `Home#submitFirstFeed`，再用主线程与帧时间线确认慢因。

## 在 Perfetto 里按证据顺序阅读

拿到 trace 后，建议按固定顺序分析：

1. **搜索精确名称**：确认目标 slice 是否出现，以及出现了几次。
2. **确认轨道**：同步 slice 看所在的 thread track（每条线程的时间线轨道）；异步 span 看它连接的逻辑轨道和两端事件。
3. **展开嵌套**：父 slice 的墙上时间只能说明范围，子 slice 才能继续分段归因。
4. **对齐帧或启动窗口**：慢帧要对齐 FrameTimeline（记录每帧生命周期的系统时间线），启动要对齐进程创建、activity launch 和首帧。
5. **查看线程状态**：Running 表示正在占用 CPU，Runnable 表示可运行但未获 CPU，Sleeping 常见于等待；还要继续结合锁、Binder、I/O 和 wakeup（线程被唤醒）事件。
6. **检查 gap**：gap 是两个业务 slice 之间的空白，可能来自等待或没有标记的代码，不能只凭空白下结论。

需要批量核对同名 slice 时，可以在 Perfetto Trace Processor（Perfetto 的 SQL 查询引擎）中执行下面的查询。

```sql
SELECT
  s.ts / 1e6 AS start_ms,
  s.dur / 1e6 AS duration_ms,
  t.name AS thread_name
FROM slice AS s
JOIN thread_track AS tt ON s.track_id = tt.id
JOIN thread AS t ON tt.utid = t.utid
WHERE s.name = 'Home#submitFirstFeed'
ORDER BY s.ts;
```

这条查询只列出 thread track 上的同步 slice。`ts` 和 `dur` 的原始单位是纳秒，除以 `1e6` 后得到毫秒；`utid` 是 Trace Processor 内部的线程关联键，不等同于 Linux `tid`。异步 slice 可能位于其他 track，不能因查询无结果就断言事件没有采到。`dur = -1` 通常意味着区间未闭合或采集结束时仍在进行，需要回查 begin/end 生命周期。

CPU 调度与唤醒证据来自系统和 kernel trace 数据源。涉及这类实现时，以 `android17-6.18-2026-06_r6` 为 kernel 侧锚点；应用自定义 slice 的 Android 17 Java/JNI 行为则以 `android-17.0.0_r1` 为准，两类源码边界不要混用。

## 常见错误与修正

| 错误 | trace 中的表现 | 修正 |
|---|---|---|
| 名称带 ID、URL、SQL 或用户数据 | 名称爆炸，无法聚合，并有泄露风险 | 固定名称；动态字段进入受控日志或 APM |
| Java begin/end 没放进 `try-finally` | 后续 slice 嵌套到错误父区间，或出现未闭合区间 | Kotlin 用 `trace {}`；Java 强制 `try-finally` |
| 同步 section 跨协程挂起点 | begin/end 可能跨线程，线程栈语义失效 | 用 suspend `traceAsync()` 表示逻辑跨度，线程内工作另加同步 slice |
| async span 复用并发 cookie | 同名任务互相错配 | cookie 在同名重叠任务间保持唯一 |
| 只标任务提交 | 只看到 `execute()`、`post()` 的提交耗时 | 在执行线程标记工作，并用 async span 串起生命周期 |
| 每个循环元素都打点 | 视图充满碎片，缓冲区压力上升 | 把 section 移到循环外；数量用 counter |
| 把 slice 时长当 CPU time | 把等待和调度延迟误算为执行耗时 | 联读 thread state、sched（调度事件）、Binder、I/O |
| 认为 API 31+ 一直在采集 | 没抓 trace 时仍构造昂贵名称 | 用 lazy label 或 `Trace.isEnabled()` |
| 把 2.0 `Tracer` 当成经典 `Trace.*` 的直接替换 | 采集和文件生命周期设计缺失 | 将进程内 tracing 作为独立路径评估；低频系统事件可继续用经典 API |
| 把 trace 当线上统计系统 | 没有分位数、采样和上传策略 | 指标交给 JankStats/APM/Benchmark，trace 用于解释现场 |

## 源码核验记录

相关结论来自官方文档、Android 17 源码和已发布 artifact 的交叉核对：

- AndroidX Tracing 发布说明与 Google Maven metadata：2.0.0 stable、1.3.0 兼容线与 Tracing Perfetto 1.0.1 的版本边界。
- `android-17.0.0_r1` 的 `android.os.Trace`：127 code unit 限制、同步同线程约束、异步 name/cookie 配对和公开 API。
- `android-17.0.0_r1` 的 `android_os_Trace.cpp`：JNI 进入 `tracing_perfetto::traceBegin()`、`traceEnd()`、`traceAsyncBegin()` 等实现。
- `tracing-android:2.0.0` sources：AndroidX 名称截断、API 29 前反射兼容路径、`forceEnableAppTracing()`、`Long` counter 重载与 suspend `traceAsync()` 的 `finally` 配对。
- AndroidX Tracing 2.0 发布说明与 `tracing-wire` POM：进程内 `Tracer`、Perfetto 格式 `TraceSink`、Studio System Trace 的采集边界，以及 Benchmark 1.5 的事后合并能力。
- AndroidX Benchmark 发布说明与 `TraceSectionMetric` API：1.4.1 stable、1.5.0-rc01、实验 API 标记和 mode 语义。
- Android NDK tracing reference：同步 API 从 23 可用，异步与 counter 从 29 可用。

为便于复核，下载件的 SHA-256 如下：

| 文件 | SHA-256 |
|---|---|
| `tracing-android-2.0.0.aar` | `b21800b83ed0e3e214742c8a94edee90130e0a9970c85e59161d161546f5fe9a` |
| `tracing-android-2.0.0-sources.jar` | `3e8834bc1448680390709e1379de6fcae6170920ebc9b8a569d00c5e735df51d` |
| `tracing-android-1.3.0.aar` | `f59782bbe3470a6b0c531cef262dd1fc9d9a0233490bb5e6d553e1fe6a1816b2` |
| `tracing-android-1.3.0-sources.jar` | `a3a9c1b46707208a024ab3939fc93dd56978f5c0e5928ec808e21df9e139cc5d` |
| `tracing-android-2.0.0-beta01.aar` | `a5596bdc3870afcede0c8a4b99685eea692bfed9b583679b3a07e9598750feb8` |
| `tracing-android-2.0.0-beta01-sources.jar` | `3e8834bc1448680390709e1379de6fcae6170920ebc9b8a569d00c5e735df51d` |

2.0.0 与 beta01 的 sources JAR 内容哈希相同，已发布 AAR 的哈希不同；表中同时保留两组值，避免复核历史文章时把两个产物混为一谈。

## 参考资料

- [AndroidX Tracing release notes](https://developer.android.com/jetpack/androidx/releases/tracing)
- [Google Maven：AndroidX Tracing metadata](https://dl.google.com/android/maven2/androidx/tracing/tracing/maven-metadata.xml)
- [Android custom trace events](https://developer.android.com/topic/performance/tracing/custom-events)
- [AndroidX Tracing API reference](https://developer.android.com/reference/androidx/tracing/package-summary)
- [Android 17 `android.os.Trace`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Trace.java)
- [Android 17 `android_os_Trace.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/android_os_Trace.cpp)
- [`tracing-android:2.0.0` AAR](https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/2.0.0/tracing-android-2.0.0.aar)
- [`tracing-android:2.0.0` sources](https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/2.0.0/tracing-android-2.0.0-sources.jar)
- [`tracing-android:1.3.0` AAR](https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/1.3.0/tracing-android-1.3.0.aar)
- [`tracing-android:1.3.0` sources](https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/1.3.0/tracing-android-1.3.0-sources.jar)
- [`tracing-android:2.0.0-beta01` AAR](https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/2.0.0-beta01/tracing-android-2.0.0-beta01.aar)
- [`tracing-android:2.0.0-beta01` sources](https://dl.google.com/dl/android/maven2/androidx/tracing/tracing-android/2.0.0-beta01/tracing-android-2.0.0-beta01-sources.jar)
- [AndroidX Benchmark release notes](https://developer.android.com/jetpack/androidx/releases/benchmark)
- [`TraceSectionMetric` API reference](https://developer.android.com/reference/androidx/benchmark/macro/TraceSectionMetric)
- [NDK tracing API](https://developer.android.com/ndk/reference/group/tracing)
- [Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)
- [JankStats](https://developer.android.com/topic/performance/jankstats)
- [`android17-6.18-2026-06_r6` kernel source](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
