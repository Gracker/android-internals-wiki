---
{
  "title": "androidx.tracing（Tracing SDK）",
  "chapter": "19",
  "section": "19.13",
  "status": "ready-for-review",
  "drafted_date": "2026-04-24",
  "drafted_by": "codex",
  "applicable_versions": "Android 8 (API 26) - Android 17 (API 37)",
  "last_verified": "2026-04-24",
  "last_verified_against": "Android tracing docs / androidx.tracing Trace reference / custom events docs",
  "confidence": "medium",
  "tags": [
    "apm"
  ],
  "related_chapters": [
    "19.0"
  ],
  "sources": [
    {
      "type": "official",
      "path": "https://developer.android.com/topic/performance/tracing"
    },
    {
      "type": "official",
      "path": "https://developer.android.com/reference/androidx/tracing/package-summary"
    }
  ],
  "pipeline_stage": "task6_pending",
  "task6_state": "revisiting",
  "task9_state": "pending",
  "task2b_state": "fixed",
  "reviewed_by": "openclaw-task6",
  "reviewed_date": "2026-04-24",
  "task6_result": "pass-light-edit",
  "task9_result": "needs-rework",
  "task9_reviewed_date": "2026-04-24",
  "task9_reviewed_by": "openclaw-task9",
  "last_task9_at": "2026-04-24T19:59:52+08:00",
  "task2b_result": "fixed",
  "last_task2b_at": "2026-04-24T21:14:45+08:00",
  "repaired_date": "2026-04-24",
  "repaired_by": "openclaw-task2b"
}
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

`androidx.tracing` 是 AndroidX 对平台 tracing API 的封装。它的作用很简单：让应用在代码里标记某段工作，之后在 Perfetto 或 Systrace 里看到对应 slice。

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

下面这段代码展示 Kotlin 扩展函数的写法，重点是把业务区间命名清楚。

```kotlin
import androidx.tracing.trace

fun renderHomeFeed(items: List<FeedItem>) {
    trace("HomeFeed#diffAndBind") {
        val diff = calculateDiff(items)
        adapter.submitList(diff)
    }
}
```

抓 Perfetto 时，`HomeFeed#diffAndBind` 会显示在对应线程轨道上。这样分析慢帧或启动慢时，可以把系统调度和业务阶段放在一起看。

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
- btrace：专项诊断时补方法级现场。
- Perfetto SDK：需要更复杂自定义数据源时使用。

大多数 App 先用 `androidx.tracing` 就够。把启动、首屏、列表、图片、数据库和关键交互标好，Perfetto 可读性会提升很多。

## 线上和线下的边界

trace 标注代码可以留在 Release 包里，但能不能在 Perfetto 里看到自定义 slice，要按平台版本判断。

| 平台 | 默认可见性 | 额外处理 |
|---|---|---|
| API 24-28 | 只有 debuggable 进程默认能记录 app trace | 非 debuggable 进程要在启动早期调用 `Trace.forceEnableAppTracing()` |
| API 29-30 | debuggable 和 profileable 进程默认可见 | 非 debuggable 且未声明 `profileable` 的进程，仍要调用 `Trace.forceEnableAppTracing()` |
| API 31+ | app tracing 在所有应用里默认开启 | `Trace.forceEnableAppTracing()` 在这一段没有实际效果 |

AndroidX `Trace.forceEnableAppTracing()` 的文档说明了两点：它用于在 non-debuggable process 中启用 app tracing；从 Android 12 开始，应用代码写入的 custom trace 在所有应用里都默认开启。用正式包抓性能数据时，优先使用 profileable 或接近发布态的构建，避免把 debuggable 包的调试开销带进结论。

还有两条约束：

- 热路径上不要创建复杂字符串作为 trace 名称。
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

这段 trace 只记录异步任务提交耗时，不记录网络、解析、数据库和 UI 更新。跨线程任务要分两层标注：

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
    ioExecutor.execute {
        trace("Home#requestFirstFeed") {
            val response = api.loadFirstFeed()
            val items = parser.parse(response)
            mainHandler.post {
                trace("Home#renderFirstFeed") {
                    adapter.submitList(items)
                }
                Trace.endAsyncSection("Home#loadFirstFeed", cookie)
            }
        }
    }
}
```

在 Perfetto 里，`beginAsyncSection()` 和 `endAsyncSection()` 会按同名加同 cookie 配对。多个异步任务并发时，cookie 必须唯一；如果名称相同而 cookie 复用，几个任务会被合并成一条错误的 span。

只想看线程内耗时分布时，分线程同步 slice 就够了。需要读一个完整的跨线程逻辑链时，再补 async trace。

## trace 与线上指标关联

`androidx.tracing` 本身不上传数据，但 trace 名称应该和线上 APM 的事件名保持一致。比如线上启动事件叫 `startup.first_draw`，Perfetto slice 可以叫 `Startup#firstDraw`。这样线上指标、日志和线下 trace 能互相对应。

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

Java 层只看到一次 JNI 调用，Perfetto 里如果没有 native slice，读者不知道 native 内部时间花在哪里。

## 常见错误

| 错误 | 后果 | 修正 |
|---|---|---|
| trace 包太大 | Perfetto 视图里 slice 跨太多逻辑，无法定位 | 拆成几个稳定阶段 |
| trace 包太小 | 视图噪声过多，抓 trace 成本上升 | 只标性能敏感路径 |
| 名称带动态数据 | 无法聚合，可能泄露隐私 | 用固定枚举和稳定名称 |
| 只标异步提交 | 看不到实际工作耗时 | 在实际执行线程标记 |
| Debug 才有 trace | Release 问题无法复现 | 低成本稳定 trace 留在正式代码 |

Tracing SDK 的价值来自一致性。少量稳定、长期存在的 trace，比临时到处加标记更有用。
