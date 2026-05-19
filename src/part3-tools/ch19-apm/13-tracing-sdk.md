---

title: androidx.tracing（Tracing SDK）
chapter: '19'
section: '19.13'
status: "ready-for-review"
drafted_date: '2026-04-24'
drafted_by: codex
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-04-24'
last_verified_against: Android tracing docs / AndroidX tracing reference / JankStats
  docs / Macrobenchmark docs / NDK tracing docs
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
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task9_state: "pending"
task2b_state: "fixed"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-18"
task6_result: "pass-light-edit"
task9_result: "needs-rework"
task9_reviewed_date: "2026-05-18"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-18T20:30:46+08:00"
task2b_result: "fixed"
last_task2b_at: "2026-05-19T15:20:11+08:00"
repaired_date: '2026-04-25'
repaired_by: openclaw-task2b
task9_review_notes: "2026-05-07 19:30 Task9 deep-review: needs-rework。P0 2 / P1 5 / P2 3。Top: 4.1 MemoryLimiter 误写为 PSS/exit reason；8.4 FragmentManager 自动 trace slice 未证实；19.13 协程 async trace 示例不可编译且异常路径不闭合。 | 2026-05-07 21:27 Task9 deep-review: needs-rework。P0 1 / P1 3 / P2 0。Top: API31+ tracing 内联/JNI 路径事实错误；协程修正示例仍可能跨挂起点或阻塞主线程；executor/mainHandler 示例异常路径仍可能遗留 async span。 | 2026-05-08 00:28 Task9 deep-review: needs-rework。P0 0 / P1 2 / P2 1。Top: AndroidX Tracing 版本表混淆平台 API 与 AndroidX compat，协程 async 示例仍有取消路径不闭合。 | 2026-05-15 Task9：needs-rework。P0 1 / P1 0 / P2 1；旧 async trace 两项已复核为 fixed，新增 Trace ThreadLocal 源码事实错误。 | 2026-05-18 Task9：needs-rework。P0 1 / P1 0 / P2 0；AndroidX Tracing compat 与版本表仍有源码错误（traceAsync 起始版本、pre-29 fallback、TraceEventCache）。 | 2026-05-18 Task9：needs-rework。P0 1 / P1 0 / P2 0；AndroidX Tracing API 18-28 compat 反射方法名仍写成不存在的 Trace.__setArg/__endTraceAsync，版本表对 tracing/tracing-ktx 归属和 lazy traceAsync 签名仍需回炉。"
task6_review_notes: "2026-04-29 task6 review: pass-light-edit。无P0/P1；L3需补充性能开销和版本兼容性细节，已写入Task 2B。 | 2026-05-01 task6 re-review (revisiting→reviewed): pass-light-edit. L1/L2 clean. Excellent code examples and practical tables. task9 needs-rework blocks auto-promotion. | 2026-05-07 19:05 task6 revisiting-review: pass-light-edit。L1/L2 轻量修复；技术正确性仍交由 Task9 复审。 | 2026-05-07 22:10 task6 revisiting-review: pass-light-edit。L1/L2 clean；已知技术风险继续交 Task9 复审，未自动晋升。 | 2026-05-15 task6 revisiting-review: pass-light-edit。L1/L2 clean；已知 async trace 技术项仍在 queue，等待 Task9/Task2B 复审，未自动晋升。 | 2026-05-18 12:26 Task6：revisiting 文稿复审；L1/L2 小修 1 处，承接 Task9 技术边界项 1 个，已在正文标注并并入 queue.json，等待 Task2B/Task9。 | 2026-05-18 20:16 Task6：revisiting 写作复审通过；L1/L2 小修 1 项（补全 frontmatter tags，覆盖 tracing / Perfetto / AndroidX 主题）；无新增回炉项，Task9 复审状态继续阻止自动晋升。"
last_task6_at: "2026-05-18T20:16:50+08:00"
last_task9_review_log: "logs/deep-review/2026-05-18-20-deep-review.md"
task6_reviewed_at: "2026-05-18T20:16:50+08:00"
task6_reviewed_by: "openclaw-task6"
last_task6_review_log: "logs/review/2026-05-18-20-review.md"
---
# androidx.tracing（Tracing SDK）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 androidx.tracing 用来给代码区间命名，让 Perfetto / systrace 中出现业务 slice。
- 🔹 [使用时机] 写清哪些阶段值得手动 trace：启动、首屏、列表 diff、图片解码、数据库查询、业务提交、跨线程任务。
- 🔹 [基本用法] 覆盖 Kotlin `trace {}`、Java begin/end、异常安全、嵌套 trace、主线程与后台线程。
- 🔹 [命名规范] 规定稳定名称、分层前缀、禁止动态 id / URL / 用户数据；给推荐和反例。
- 🔹 [同步 / 异步] 区分同步 slice、async trace、跨线程任务和协程任务；给一个 async 伪代码或真实示例。
- 🔹 [Native 标注] 说明 native 侧 ATrace / Perfetto 标注如何和 Java trace 一起阅读。
- 🔹 [工具关系] 区分 androidx.tracing、Perfetto SDK、btrace、Macrobenchmark trace section 的使用边界。
- 🔹 [线上关系] 说明 trace 名称如何和线上指标、JankStats context、APM custom trace 建立同名索引。
- 🔹 [阅读方式] 写清在 Perfetto UI 中如何找到 slice、看线程、看嵌套、看 gap 和 scheduler。
- 🔹 [常见错误] 覆盖名称过细、忘记 end、跨线程错配、热路径过度打标、把 trace 当统计系统。

### 扩展（可选深入）

- 🔸 增加一套 trace 命名表，覆盖启动、首页、详情页、支付、图片、数据库。
- 🔸 补一个协程 / executor 跨线程 trace 示例。
- 🔸 对 Android tracing docs、androidx.tracing reference 做版本核对。
- 🔸 增加与自定义 APM trace 的字段映射表。
- 🔸 补一个“trace 太多导致阅读困难”的反例和删减规则。

### 流水线加工要求

- 每个 trace 示例必须说明读者在 Perfetto 里应该看哪条线程和哪个 slice。
- 命名规范要能被团队直接采用，避免只写原则。
- 涉及异步区间时必须写开始、结束和 id 管理，不留伪概念。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## Tracing SDK 给代码区间命名

`androidx.tracing` 是 AndroidX 对平台 tracing API 的封装。它只做一件事：让应用在代码里标记某段工作，之后在 Perfetto 或 Systrace 里看到对应 slice。

它不采集性能指标，也不自动分析慢在哪里。它只负责把“这段时间应用在做什么”写进 trace。对性能分析来说，这个能力很有用，因为系统 trace 里最缺的往往是业务语义。

## 什么时候需要手动 trace

系统 trace 能看到线程运行、调度、Binder、I/O、渲染等事件，但它不知道业务代码在做“首页首屏数据解析”还是“支付按钮状态刷新”。这些语义只能由应用自己标注。

适合加 trace 的位置包括：

- 启动阶段的关键节点：`Application` 初始化、首屏数据、首帧前布局。
- 大列表刷新：diff、bind、图片解码、分页合并。
- 复杂交互：转场动画、手势处理、地图/视频/相机页面初始化。
- 同步等待点：缓存读取、数据库查询、跨进程调用包装。

不适合给每个小函数都加 trace。slice 太多会污染视图，也会增加运行时开销。

## 基本用法

Kotlin 扩展函数适合标记一个同步业务区间，重点是把区间名称写稳定。

```kotlin
import androidx.tracing.trace

fun renderHomeFeed(items: List<FeedItem>) {
    trace("HomeFeed#diffAndBind") {
        val diff = calculateDiff(items)
        adapter.submitList(diff)
    }
}
```

Java 侧没有 `trace {}` 的语法保护，`beginSection()` / `endSection()` 要用 `try-finally` 配对。示例里要重点检查 `finally`：无论 diff 计算是否抛异常，当前线程上的 trace 栈都会被关闭。

```java
import androidx.tracing.Trace;

void renderHomeFeed(List<FeedItem> items) {
    Trace.beginSection("HomeFeed#diffAndBind");
    try {
        List<FeedItem> diff = calculateDiff(items);
        adapter.submitList(diff);
    } finally {
        Trace.endSection();
    }
}
```

`beginSection()` 和 `endSection()` 必须在同一线程配对。漏掉 `finally` 后，异常路径会把后续 slice 嵌进错误的父区间，Perfetto 里的线程时间线会失真。

抓 Perfetto 时，`HomeFeed#diffAndBind` 会显示在对应线程轨道上。这样分析慢帧或启动慢时，可以把系统调度和业务阶段放在一起读。

## 性能开销与适用边界

`Trace.beginSection()` / `Trace.endSection()` 的单次调用开销取决于平台和字符串长度，大致范围如下：

| 操作 | 量级（trace 已启用） | 说明 |
|---|---|---|
| `beginSection`（短名称） | 亚微秒级 | 含 `@FastNative` JNI 调用 + atrace tag 检查 + ftrace write；具体耗时因 SoC、ftrace buffer 状态、字符串长度而异 |
| `beginSection`（长名称） | 微秒级上下 | 字符串拷贝与 ftrace write 随名称长度线性增长 |
| `endSection` | 百纳秒级 | 无字符串参数，仅 tag 检查 + ftrace write |
| `beginAsyncSection` / `endAsyncSection` | 亚微秒级 | 含 int cookie 写入，与 beginSection 处于同一量级 |
| trace disabled fast path | 纳秒级 | 平台层 `isTagEnabled()` 布尔短路即返回，生产环境无 trace 时几乎零开销 |

> 量级来自公开文档与平台源码行为分析。具体数值因设备、Android 版本、ftrace buffer 状态而异；读者可用 `androidx.benchmark:benchmark-micro-junit4` 在目标设备上复测。

开销来自两部分：

1. **字符串分配**：每次 `beginSection` 都会在 native 层做一次 `write(fd, ...)` 系统调用，把 `B|<pid>|<name>` 写入 `trace_marker`。字符串越长，系统调用耗时越高。
2. **ftrace ring buffer 写入**：写入 per-CPU ring buffer 本身很快（约 100ns），但在高并发场景下 buffer 溢出会触发额外的锁竞争。
3. **AndroidX 包装层与平台路径**：`androidx.tracing` 1.3.0 的 `Trace.beginSection(label)` 最终调用 `android.os.Trace.beginSection(label.truncatedTraceSectionLabel())`，平台层再经 `isTagEnabled(TRACE_TAG_APP)` 检查和 `nativeTraceBegin()`（标注 `@FastNative`）写入 atrace。无论 API 级别如何，调用链都经过 JNI；AndroidX 1.2 的变化是 lazy string/cookie 的 `trace()` / `traceAsync()` 扩展函数以及 begin 失败时自动跳过 end，不是"API 31+ 跳过 JNI"。在热路径高频打标场景下，单次完整 `beginSection` 调用（含字符串处理、tag 检查、JNI transition、ftrace write）约几百纳秒到一微秒，`onBindViewHolder` 里每帧 20 次 trace 调用约 6-14μs，占 120Hz 帧预算（8.33ms）的 0.07-0.17%。

基于这些数据，几个实用边界：

- **热路径谨慎打标**：如果某段代码在一帧内被调用超过 1000 次（如 `onDraw` 内的循环），不要在里面放 `beginSection`。把 trace 提到循环外面，标注整体耗时即可。
- **避免动态字符串拼接**：`"item_" + id` 这种写法会多一次 `StringBuilder` 分配 + `toString()` + JNI 层 `GetStringUTFChars()` 转换 + native 字符串拷贝。高频调用时字符串分配带来的 GC 压力和 JNI 转换开销可能超过 trace 本身耗时。改用静态常量可以完全消除这笔开销：

```kotlin
companion object {
    private const val TAG_BIND = "Feed#bindItem"
}
// 使用时直接引用 TAG_BIND，零分配
```
- **Release 包保留必要的 trace**：少量稳定的 trace slice（每帧 < 20 个）在 120Hz 下只占帧预算的小比例，对用户无感知。

不适合加 trace 的场景：

- `onMeasure` / `onLayout` 内部的高频循环体。
- JNI native 方法边界（native 侧已有 `ATrace_*` 可用）。
- 任何频率超过 10kHz 的代码路径。

## 命名要稳定

trace 名称不要带高基数字段，比如用户 id、完整 URL、搜索词、订单号。原因很直接：名称会进入 trace 文件，可能触发隐私问题，也会让分析视图变得不可聚合。

更适合的命名方式是：

- `Startup#loadConfig`
- `Home#firstFeedRequest`
- `Feed#diff`
- `Image#decodeThumbnail`
- `Checkout#submit`

如果需要区分页面或业务类型，可以使用少量固定枚举，不要把动态内容写进 trace 名称。

## 和 btrace、Perfetto SDK 的区别

`androidx.tracing` 是手动标注。btrace / RheaTrace 可以采到更多方法级调用信息。Perfetto SDK 则适合写入更结构化或跨平台的自定义 trace 数据源。

三者的关系可以这样理解：

- `androidx.tracing`：轻量、稳定、适合长期保留的业务 slice。
- Macrobenchmark：测试侧抓 trace；App 侧的 `androidx.tracing` slice 会成为 `TraceSectionMetric` 或 Perfetto 人工分析里的业务阶段锚点。
- btrace：专项诊断时补方法级现场。
- Perfetto SDK：需要更复杂自定义数据源时使用。

大多数 App 先用 `androidx.tracing` 就够。把启动、首屏、列表、图片、数据库和关键交互标好，Macrobenchmark 报告和 Perfetto trace 才能指向同一组业务阶段。

## 线上和线下的边界

trace 标注代码可以留在 Release 包里，但能不能在 Perfetto 里看到自定义 slice，要按平台版本判断。

### 平台公开 API 边界

| API 版本 | 自定义 slice 可见性 | 异步 trace (`beginAsyncSection`) | 其他关键变化 |
|---|---|---|---|
| API 18-28 | 仅 debuggable 进程默认可见 | 不可用 | 非 debuggable 进程需在启动早期调用 `Trace.forceEnableAppTracing()`，效果依赖 ROM 对 `trace_marker` fd 的 SELinux 策略 |
| API 29-30 | debuggable + profileable 进程默认可见 | API 29 引入 `beginAsyncSection()` / `endAsyncSection()` | 非 debuggable 且未声明 `profileable` 的进程仍需 `forceEnableAppTracing()` |
| API 31+ | 所有应用默认开启 | 可用 | `androidx.tracing` 直接调用平台 API；`<profileable enabled=false/>` 可能仍有限制 |
| API 33+ | 同上 | 可用 | Perfetto 默认启用 `android.os.Trace` 数据源 |
| API 35+ | 同上 | 可用 | ProfilingManager 可在 App 不主动 trace 时自动抓取 |

### AndroidX Tracing compat 行为

AndroidX `Trace.forceEnableAppTracing()` 在 API 18-30 上为 non-debuggable 进程尝试打开 app tracing 通道。从 API 31 起，平台默认开启 app tracing，该调用不再有实际效果。

异步 trace 配对（`beginAsyncSection` / `endAsyncSection`）在 API 29+ 走平台原生实现；API 18-28 由 `androidx.tracing:tracing` 通过反射调用 `android.os.Trace.asyncTraceBegin(long, String, int)` / `asyncTraceEnd(long, String, int)` 实现 compat，API < 18 时降级为空操作。`trace {}` Kotlin 扩展函数从 `tracing-ktx` 1.0.0 起可用；1.2.0 新增了 lazy string/cookie 的 `trace(name) { }` / `traceAsync(name, cookie) { }` 重载，以及 `beginSection` 失败时自动跳过 `endSection` 的异常安全修正。

AndroidX `Trace.forceEnableAppTracing()` 的文档说明了两点：它用于在 non-debuggable process 中启用 app tracing；从 Android 12 开始，应用代码写入的 custom trace 在所有应用里都默认开启。用正式包抓性能数据时，优先使用 profileable 或接近发布态的构建，避免把 debuggable 包的调试开销带进结论。

`androidx.tracing:tracing` 库的版本差异：

| 版本 | 关键能力 |
|---|---|
| 1.0-1.1 | `tracing` 主库提供 `beginAsyncSection` / `endAsyncSection` 的反射 compat（API 18-28）；`tracing-ktx` 1.0.0 提供 `trace {}` / `traceAsync {}` Kotlin 扩展 |
| 1.2.0 | 新增 lazy string/cookie 的 `trace(name) { }` / `traceAsync(name, cookie) { }` Kotlin 扩展重载；`beginSection` 失败时自动跳过 `endSection`，防止异常路径下 trace 栈失配 |
| 1.3.0 | Trace API 转 Kotlin；`tracing-ktx` 合并入主 artifact；当前最新 stable（2025-04 发布） |
| 2.0.0-alpha | 新增 `traceCoroutine` API，支持协程上下文传播；引入可插拔 backend 接口（仍为 alpha） |

生产包推荐使用 1.3.0 stable。1.2.0 是最小安全版本（含 lazy string 和异常安全），1.3.0 在此基础上完成 Kotlin 迁移和 artifact 合并。2.0.0-alpha 的 coroutine tracing 需要单独验证 trace 体积和兼容性，不建议未经评估直接上线。

还有两条约束：

- 热路径上不要创建复杂字符串作为 trace 名称。`"Item_" + position` 这种写法在每帧调用 N 次的 `onBindViewHolder` 里，每次都分配一个临时 `StringBuilder`、触发 `toString()`、再经 JNI `GetStringUTFChars()` 转为 C 字符串写入 `trace_marker`——分配 + GC + JNI 开销可能超过 trace 本身耗时。改用静态常量或预拼接字符串。
- 不要在 trace 名称里写用户数据、业务密钥或完整请求信息。

Tracing SDK 的收益来自长期积累。每个性能敏感模块保留少量稳定 slice，后面抓到 Perfetto 时，系统事件和业务阶段才容易对应。

## trace 名称就是书里的索引

业务 trace 名称要让读 trace 的人一眼知道阶段。建议采用 `Module#Action` 或 `Feature.Step` 形式：

| 好的名称 | 含义 |
|---|---|
| `Startup#initImageLoader` | 启动阶段初始化图片库 |
| `Home#loadFirstFeed` | 首页首屏 feed 加载 |
| `Feed#diffAndBind` | 列表 diff 和提交 |
| `Search#renderResult` | 搜索结果渲染 |
| `Player#prepare` | 播放器 prepare 阶段 |

命名不宜过细。`HomeRepository$getFeedFromCache` 这种函数式名称会让 trace 过度贴近代码实现，重构后就失效。书稿级工程里，trace 名称应该描述业务阶段，不描述当前实现。

## 同步和异步区间要分开

`trace {}` 只能覆盖当前线程上的同步区间。主线程发起请求、I/O 线程执行、主线程提交 UI 时，单个同步 slice 只会覆盖发起动作。

错误示例：

```kotlin
trace("Home#loadFirstFeed") {
    repository.loadFirstFeedAsync()
}
```

这段 trace 只记录异步任务提交耗时，不记录网络、解析、数据库和 UI 更新。

协程里也有同样边界，且更容易写错。不要把包含 `delay()`、`withContext()` 或其他挂起点的 `suspend` 块直接包进同步 `trace {}`。同步 slice 是线程轨道内的嵌套事件，`beginSection()` / `endSection()` 必须在同一线程配对。挂起时协程让出线程，但 `endSection()` 还没被调用；线程转去执行其他协程或系统任务时，后续所有 `beginSection()` 调用都会被压入这条未关闭的 slice 下面——Perfetto 里不仅出现跨线程的错误长区间，后续 trace 事件也全部变成这条 slice 的子节点，导致整个 trace 视图被污染。未引入 AndroidX Tracing 2.0.0 alpha 的 coroutine tracing API 前，包含挂起点的业务跨度用 async trace 显式配对；线程内真实工作仍用同步 slice。

这类写法会在 Perfetto 里产生"视图污染"，可以改成按线程和异步跨度分层标记：

**❌ 错误：同步 `trace {}` 包裹含挂起点的协程块**

```kotlin
// 错误：trace 区间跨越了挂起点
trace("Home#loadData") {
    val data = repository.fetchData()   // 内部 withContext(Dispatchers.IO)
    adapter.submitList(data)
}
```

Perfetto 中这条 slice 会从调用开始一直延伸到协程恢复后执行完毕。挂起期间主线程去跑了其他任务（measure、draw、input handling），但这些工作全部被包在 `Home#loadData` 这条 slice 内。读 trace 的人会误以为"加载耗时 200ms"，网络请求只占 50ms，剩下的 150ms 是主线程在挂起期间执行的无关工作。

**✅ 修正：同步 slice 只包住线程内阻塞工作，跨线程逻辑用 async trace 配对**

```kotlin
val cookie = nextCookie.getAndIncrement()
val spanClosed = java.util.concurrent.atomic.AtomicBoolean(false)
// 先注册 beginAsyncSection，再启动协程：避免 Main.immediate dispatcher
// 同步执行协程体并在 finally 中 endAsyncSection 时出现 end-before-begin
Trace.beginAsyncSection("Home#loadData", cookie)
val job = viewModelScope.launch {
    try {
        // 切到 I/O 线程，同步 slice 只包住该线程内的阻塞工作
        val data = withContext(Dispatchers.IO) {
            trace("Home#fetchData") {
                repository.fetchDataBlocking()  // 阻塞式网络/解析调用
            }
        }
        // 回到主线程，同步 slice 只包住渲染
        trace("Home#renderData") {
            adapter.submitList(data)
        }
    } finally {
        if (spanClosed.compareAndSet(false, true)) {
            Trace.endAsyncSection("Home#loadData", cookie)
        }
    }
}
// scope 已取消或 launch 后 block 未实际执行时，finally 不会运行
// invokeOnCompletion 在 job 终止时触发，覆盖取消/取消前/失败/完成所有状态
job.invokeOnCompletion {
    if (spanClosed.compareAndSet(false, true)) {
        Trace.endAsyncSection("Home#loadData", cookie)
    }
}
```

修正后，`withContext(Dispatchers.IO)` 保证 `trace("Home#fetchData")` 在 I/O 线程内部执行，不跨挂起点；主线程的 `trace("Home#renderData")` 只覆盖 `submitList` 的同步部分。async trace 把两端串成同一个业务 span，不会出现同步 slice 跨挂起点导致的视图污染。

`invokeOnCompletion` + `AtomicBoolean` 保证 async span 只关闭一次，覆盖三条路径：
- 协程正常完成或异常：`finally` 块关闭 span。
- 协程 body 因 scope 取消而未执行：`invokeOnCompletion` 关闭 span。
- 协程 body 已启动后被 `withContext` 内取消：`finally` 块关闭 span。

`beginAsyncSection` 放在 `viewModelScope.launch` 之前调用。原因：`viewModelScope` 默认使用 `Main.immediate` dispatcher，`launch` 创建的协程可能在 `launch` 调用返回前同步执行协程体；如果先 `launch` 再 `beginAsyncSection`，协程的 `finally` 可能在 `begin` 之前运行，产生 end-before-begin 的 trace 错误。

跨线程任务要分两层标注：

- 每个线程保留自己的同步 slice，用来读本线程的真实耗时。
- 同一个业务 span 再补一组 async trace，用来串起跨线程阶段。

```kotlin
import androidx.tracing.Trace
import androidx.tracing.trace
import java.util.concurrent.atomic.AtomicInteger

private val nextCookie = AtomicInteger(1)

fun loadFirstFeed() {
    val cookie = nextCookie.getAndIncrement()
    Trace.beginAsyncSection("Home#loadFirstFeed", cookie)
    try {
        ioExecutor.execute {
            try {
                val items = trace("Home#requestFirstFeed") {
                    val response = api.loadFirstFeed()
                    parser.parse(response)
                }
                val posted = mainHandler.post {
                    try {
                        trace("Home#renderFirstFeed") {
                            adapter.submitList(items)
                        }
                    } finally {
                        // posted runnable 内无论成功/异常都关闭 async span
                        Trace.endAsyncSection("Home#loadFirstFeed", cookie)
                    }
                }
                if (!posted) {
                    // Handler 已退出（如 Activity 销毁），立即关闭 span
                    Trace.endAsyncSection("Home#loadFirstFeed", cookie)
                }
            } catch (e: Exception) {
                // 网络/解析/executor 失败时关闭 async span
                Trace.endAsyncSection("Home#loadFirstFeed", cookie)
            }
        }
    } catch (e: Exception) {
        // executor.execute() 本身可能抛 RejectedExecutionException
        Trace.endAsyncSection("Home#loadFirstFeed", cookie)
    }
}
```

在 Perfetto 里，`beginAsyncSection()` 和 `endAsyncSection()` 会按同名加同 cookie 配对。多个异步任务并发时，cookie 必须唯一；如果名称相同而 cookie 复用，几个任务会被合并成一条错误的 span。

只想看线程内耗时分布时，分线程同步 slice 就够了。需要读一个完整的跨线程逻辑路径时，再补 async trace。

如果团队已经评估 AndroidX Tracing 2.0.0 alpha 系列，可以单独验证 `traceCoroutine` 在挂起和恢复时的 Perfetto 表现。它仍是 alpha API，发布包接入前要验证生成的 trace 体积、线程切换呈现方式和工具兼容性。

## trace 与线上指标关联

`androidx.tracing` 本身不上传数据，但 trace 名称应该和线上 APM 的事件名保持一致。比如线上启动事件叫 `startup.first_draw`，Perfetto slice 可以叫 `Startup#firstDraw`。这样线上指标、日志和线下 trace 能互相对应。

JankStats 的 `PerformanceMetricsState` 也要使用同一套阶段命名。这段代码把线上 jank 状态和线下 trace slice 放进同一张阶段表：线上样本看 `screen=Home` 与 `phase=feed_render`，Perfetto 里读 `Home#feedRender`。

```kotlin
val holder = PerformanceMetricsState.getHolderForHierarchy(rootView)
holder.state?.putState("screen", "Home")
holder.state?.putState("phase", "feed_render")

trace("Home#feedRender") {
    adapter.submitList(items)
}
```

阶段结束后要移除对应 state，避免后续帧继续带着过期上下文。trace 名称、JankStats state、APM 事件名都用固定枚举，不写动态 id、URL 或用户数据。

推荐建立一张性能阶段表：

| 线上事件 | Trace slice | 说明 |
|---|---|---|
| `startup.app_on_create` | `Startup#appOnCreate` | `Application.onCreate()` 内关键初始化 |
| `startup.first_screen_data` | `Startup#firstScreenData` | 首屏数据准备 |
| `home.feed_render` | `Home#feedRender` | 首页列表渲染 |
| `detail.content_ready` | `Detail#contentReady` | 详情页内容可见 |

没有这张表，每个开发者会按自己的习惯命名，trace 读起来像一堆临时标签。

## Native trace 标注

如果性能敏感代码在 native 层，也要用 native trace 标注。Android 支持 native 代码写自定义 trace event，适合音视频、图像处理、渲染、压缩、加密等场景。

典型使用点：

- 图像解码和缩放。
- OpenGL / Vulkan 资源创建。
- 音视频解复用、解码、渲染。
- native 数据库或文件处理。
- JNI 边界上的大数组复制。

Native 侧最小写法如下，重点是引入 NDK tracing 头文件，并让 begin/end 在同一线程配对。

```cpp
#include <android/trace.h>

void DecodeFrame() {
    ATrace_beginSection("Video#decodeFrame");
    DecodeOneFrame();
    ATrace_endSection();
}
```

Java 层只看到一次 JNI 调用，Perfetto 里如果没有 native slice，读者不知道 native 内部时间花在哪里。native slice 会出现在执行它的线程轨道上，名称规则应和 Java 层保持一致。存在 early return 或异常边界时，用局部 guard 封装 `ATrace_endSection()`，不要让区间失配。

## 在 Perfetto 里怎么读

抓到 trace 后，用固定 slice 名称定位业务阶段，再把它和线程状态放在同一个时间窗里读。

- slice 轨道：搜索 `Home#feedRender` 这类固定名称，确认它落在哪条线程上。主线程 slice 用来判断 UI 阶段，I/O 线程 slice 用来判断后台工作。
- 嵌套关系：父 slice 太长时，继续看子 slice 是否已经拆到可行动的阶段；没有子 slice 时，回到代码补更细的稳定标记。
- Gap：两个业务 slice 中间的空白不等于业务没做事，可能是 I/O 等待、锁等待、Binder 等待或 CPU 调度延迟。
- Thread State / Scheduler：Gap 或长 slice 旁边要一起读 Thread State。线程处于 Running 但耗时长，优先查 CPU 占用；处于 Runnable，优先查调度竞争；处于 Sleeping / Uninterruptible Sleep，优先查锁、I/O 或 Binder 等待。

这样读 trace 时，业务 slice 负责标出“阶段”，Thread State 负责解释“为什么这段时间没有继续跑”。

## 常见错误

| 错误 | 后果 | 修正 |
|---|---|---|
| trace 包太大 | Perfetto 视图里 slice 跨太多逻辑，无法定位 | 拆成几个稳定阶段 |
| trace 包太小 | 视图噪声过多，抓 trace 成本上升 | 只标性能敏感路径 |
| 名称带动态数据 | 无法聚合，可能泄露隐私 | 用固定枚举和稳定名称 |
| 只标异步提交 | 看不到实际工作耗时 | 在实际执行线程标记 |
| Java begin/end 没有 `finally` | 异常路径会破坏后续 slice 嵌套 | 用 `try-finally` 固定关闭区间 |
| 同步 `trace {}` 包含协程挂起点 | Perfetto 出现跨线程的错误长 slice，挂起期间线程的其他工作全被包进同一条 slice，读 trace 的人误判耗时 | 挂起跨度用 async trace 或评估 `traceCoroutine`；上方的"视图污染"示例展示了错误写法和修正方案 |
| Debug 才有 trace | Release 问题无法复现 | 低成本稳定 trace 留在正式代码 |

Tracing SDK 的价值来自一致性。少量稳定、长期存在的 trace，比临时到处加标记更有用。
