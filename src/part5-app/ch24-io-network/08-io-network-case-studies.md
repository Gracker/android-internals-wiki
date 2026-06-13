---
title: "I/O 与网络优化案例集"
chapter: "24.8"
section: "24.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-14"
last_verified_against: "AOSP android-35 SDK sources + Android Developers docs + OkHttp 5.x docs + Clippings 结构参考"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 1
sources:
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/app/SharedPreferencesImpl.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/app/QueuedWork.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/os/StrictMode.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/app/DownloadManager.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/NetworkCapabilities.java"
  - type: official
    path: "https://developer.android.com/reference/android/content/SharedPreferences.Editor"
  - type: official
    path: "https://developer.android.com/topic/libraries/architecture/datastore"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work"
  - type: official
    path: "https://square.github.io/okhttp/features/calls/"
  - type: official
    path: "https://square.github.io/okhttp/features/events/"
  - type: official
    path: "https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dispatcher/"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
tags: [case-study, io, network, optimization, sharedpreferences, upload-download]
related_chapters: ["24.1", "24.4", "24.6", "24.7", "25.4"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
last_task6_at: "2026-06-04T06:08:46+08:00"
task6_review_notes: "2026-06-03 Task6：revisiting 复审通过；L1/L2 扫描无新增正文问题；无新增 L3/L4 回炉项，转入 Task9 pending。"
task9_state: reviewed
task2b_state: fixed
last_task2a_at: "2026-05-14T13:14:00+08:00"
task9_result: auto-fixed
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-03"
last_task9_at: "2026-06-03T14:26:33+08:00"
last_task9_review_log: "logs/deep-review/2026-06-03-14-deep-review.md"
task2b_result: fixed
last_task2b_at: "2026-06-03T04:50:00+08:00"
last_task2b_notes: "frontmatter fallback：修复 PreferenceWriteBuffer flush 后无条件清空 pending 导致并发新增写入丢失的问题。"
task6_reviewed_date: "2026-06-03"
last_task6_review_log: "logs/review/2026-06-03-07-review.md"
last_task9_autofix_at: "2026-06-03"
task9_review_notes: "2026-06-03 Task9 14:20 auto-fixed：修正 OkHttp Dispatcher 排队时间观测口径，使用 OkHttp 5.x dispatcherQueueStart/dispatcherQueueEnd；旧版 OkHttp 需自定义队列埋点，不能用 callStart 代表出队。P0 0 / P1 0 / AUTO-FIX 1；回到 Task6 复审。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-13
---

# I/O 与网络优化案例集

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SharedPreferences ANR 治理实战
- 🔹 网络请求性能优化案例
- 🔹 大文件上传下载优化

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 I/O 与网络优化案例集

I/O 与网络优化最怕只改一个点。SP 写入从调用点看很快，生命周期收尾时可能卡在 `QueuedWork.waitToFinish()`；接口耗时看起来是服务端慢，细拆后可能是 DNS、建连、Dispatcher 排队或缓存命中率低；大文件上传下载看起来只是“放后台”，上线后却占满 API 并发、耗电、失败重传、进度丢失。

24.1 到 24.7 已经分别讲过文件 I/O、数据库、序列化、网络架构、协议、缓存和离线优先。落到项目里，问题通常会混在一起：SP ANR、页面网络慢、大文件传输。三个案例都沿着“现象 → 观测 → 根因 → 改法 → 验收”展开，方便在项目里复用排查路径。

速度问题先拆 CPU 等待、I/O 等待和缓存命中，再回到线程池与任务调度。

## SharedPreferences ANR 治理实战

### 现象

一个常见现场是页面退出、切后台或服务停止时出现 ANR，主线程堆栈停在 `QueuedWork.waitToFinish()`，后台线程堆栈能看到 `SharedPreferencesImpl.writeToFile()`、`FileUtils.sync()` 或 XML 写入。业务侧通常会说“这里只是 `apply()`，不是 `commit()`”，但 ANR 发生点已经离调用点很远。

SP 的风险在两个阶段。读取阶段，首次访问可能等待 XML 加载；写入阶段，`apply()` 更新内存并排队写磁盘，生命周期收尾时可能等待队列清空。从 AOSP `SharedPreferencesImpl` 和 `QueuedWork` 源码可以看到这条路径：`apply()` 创建写入任务，`QueuedWork` 保存 pending work，框架在部分组件收尾路径调用 `waitToFinish()`。[已验证: AOSP android-35 SDK sources, android/app/SharedPreferencesImpl.java, android/app/QueuedWork.java]

### 观测路径

排查不要只查 ANR 日志。要同时抓三类证据：

| 证据 | 观测方式 | 判断点 |
| --- | --- | --- |
| 主线程堆栈 | ANR traces、Crash 平台、Bugreport | 是否停在 `QueuedWork.waitToFinish()`、`Object.wait()`、`CountDownLatch.await()` |
| 调用来源 | SP 写入封装埋点、线程名、key 维度统计 | 哪些 key 写入频率高、单次 value 多大、是否在页面生命周期内连写 |
| I/O 等待 | Perfetto 线程状态、StrictMode、磁盘事件 | 主线程是否等待后台 I/O，后台写入是否发生在切后台窗口 |

StrictMode 可以在 Debug 包暴露主线程读写风险。它不能直接判断“这次 `apply()` 会不会在稍后引发 ANR”，但能把启动和点击路径上的同步 I/O 先清出来。StrictMode、SP、DataStore 和 MMKV 的完整边界见 24.1；这个案例关注启动和点击路径上的同步 I/O 清理。[已验证: AOSP android-35 SDK sources, android/os/StrictMode.java；详见 24.1 节]

### 根因

SP ANR 往往是三类模式叠加：

- 大文件：多个业务把配置塞进同一个 XML，首次加载和写回都变慢。
- 高频写：埋点开关、弹窗状态、草稿、实验参数在短时间内多次 `apply()`，写入队列积压。
- 错误时机：`onPause()`、`onStop()`、广播回调、服务停止前写 SP，正好撞上框架等待 pending work 的窗口。

`apply()` 适合低频小配置，不适合当成无成本异步落盘接口。官方 `SharedPreferences.Editor` 文档区分了 `apply()` 的异步持久化和 `commit()` 的同步结果返回；DataStore 文档则把协程、Flow 和事务化更新作为 SP 替代方案。[已验证: 官方文档, developer.android.com/reference/android/content/SharedPreferences.Editor][已验证: 官方文档, developer.android.com/topic/libraries/architecture/datastore]

### 改法

治理时按访问路径分层处理：

| 数据类型 | 原问题 | 改法 |
| --- | --- | --- |
| 启动强依赖配置 | 首次读取卡启动 | 拆成小文件，进程启动前段预热；非首屏 key 延后读取 |
| 高频运行态标记 | 多次 `apply()` 造成 pending work 积压 | 合并写入，内存态先更新，定时或生命周期外统一刷盘 |
| 结构化对象 | JSON 字符串塞进 XML，文件膨胀 | 迁移到 Proto DataStore、Room 或专用文件 |
| 交易类状态 | 异步写入失败不可感知 | 使用可确认的持久化方案，写入结果进入业务状态机 |

这段代码展示轻量合并写入器的形态：把多次小写合并成一次后台刷盘，并把调用点从页面生命周期里移出去。类名和调度方式可以按项目替换，写入合并和生命周期外刷盘这两个边界要保留。

```kotlin
class PreferenceWriteBuffer(
    private val prefs: SharedPreferences,
    private val scope: CoroutineScope,
) {
    private val pending = MutableStateFlow<Map<String, Any>>(emptyMap())

    fun putBoolean(key: String, value: Boolean) {
        pending.update { it + (key to value) }
    }

    fun start() {
        scope.launch(Dispatchers.IO) {
            pending
                .debounce(1_000)
                .filter { it.isNotEmpty() }
                .collect { snapshot ->
                    prefs.edit().apply {
                        snapshot.forEach { (key, value) ->
                            if (value is Boolean) putBoolean(key, value)
                        }
                    }.apply()
                    pending.update { current ->
                        current.filterNot { (key, value) ->
                            snapshot[key] == value
                        }
                    }
                }
        }
    }
}
```

刷盘后不能无条件把 `pending` 清空。`flush` 期间可能又有新的 `putBoolean()` 写入，清空会直接丢掉这些更新；上面的写法只移除本轮 snapshot 已经落盘且当前值没有变化的 key，新写入或值已变化的 key 会留到下一轮刷盘。这段代码仍然使用 SP，只适合低风险开关类数据。高频结构化数据要迁到 DataStore 或 Room；跨进程共享、小型热数据可以评估 MMKV，边界见 24.1 节。

### 验收

上线前至少确认四个指标：单个 SP 文件大小、每分钟写入次数、`apply()` 到写盘完成的 P95、ANR 堆栈中 `QueuedWork.waitToFinish()` 占比。治理后如果只看 ANR 总量，可能会被版本流量、设备分布和后台限制掩盖。更可靠的验收是用同一批页面路径复测：启动、切后台、频繁进入退出页面、低端机存储压力场景都要覆盖。

## 网络请求性能优化案例

SP ANR 的根因在 I/O 路径上；另一种常见的性能退化则来自网络路径——请求本身不慢，但端到端耗时被 DNS、建连和调度排队吃掉了一大块。

### 现象

页面接口 P95 从 800 ms 涨到 2 s，服务端日志只显示处理耗时 200 ms。客户端抓包和 OkHttp EventListener 拆分后，慢在三个位置：DNS 偶发 300 ms 以上，部分请求没有复用连接，首屏接口被图片预取和日志上报挤在 Dispatcher 队列后面。

OkHttp 文档把一次 Call 拆成请求、重定向、重试和响应过程；异步请求由 Dispatcher 控制总并发和单 host 并发。EventListener 可以记录 `dispatcherQueueStart/dispatcherQueueEnd`、`dnsStart/dnsEnd`、`connectStart`、`secureConnectStart`、`connectionAcquired`、`responseHeadersStart` 等事件，用来区分 Dispatcher 排队、解析、建连、TLS、连接复用和服务端等待。[已验证: OkHttp Calls docs, square.github.io/okhttp/features/calls/][已验证: OkHttp Events docs, square.github.io/okhttp/features/events/][已验证: OkHttp Dispatcher docs, square.github.io/okhttp/5.x/okhttp/okhttp3/-dispatcher/]

### 观测路径

客户端网络慢要先拆时间段。只记录总耗时会把 DNS、建连、排队、服务端、下载、解析混在一起。

| 时间段 | OkHttp 事件或业务埋点 | 常见根因 |
| --- | --- | --- |
| 排队 | OkHttp 5.x 的 `dispatcherQueueStart` → `dispatcherQueueEnd`；旧版 OkHttp 需要自定义 Dispatcher 队列埋点 | 并发上限过低，图片、下载、API 共用队列 |
| DNS | `dnsStart` → `dnsEnd` | 本地 DNS 慢，HTTPDNS 缓存失效，网络切换 |
| 建连/TLS | `connectStart` → `secureConnectEnd` | 连接池被切碎，短连接过多，证书链或代理慢 |
| TTFB | request body 结束 → `responseHeadersStart` | 服务端处理慢，网关排队，弱网重传 |
| body 下载 | `responseBodyStart` → `responseBodyEnd` | 响应体过大，未压缩，大 JSON |
| 解析落库 | body 结束后业务耗时 | JSON 解析、数据库事务、主线程回调 |

这张表对应 24.4 的连接、解析、调度、容错四个控制面。协议层细节见 24.5，压缩和缓存见 24.6。

### 根因

这个案例的问题在于网络层没有隔离请求等级。API、图片预取、日志上报、大文件都共用一个 `OkHttpClient` 和 Dispatcher；业务方为了“多发一点”调大总并发，反而让同 host 并发和移动网络带宽竞争变得不可控。把速度问题拆成 CPU、缓存和任务调度；放到网络层，对应的治理动作是限制低优先级请求，不让它抢占首屏等待窗口。

HTTPDNS 接入也有一个边界：自定义 `Dns.lookup()` 同步参与 OkHttp 路由规划，不能在 `lookup()` 里实时发一次依赖同一 client 的 HTTPDNS 请求。更稳的方式是异步预取、内存/磁盘缓存读取、TTL 刷新、失败 IP 隔离，并保留系统 DNS 兜底。HTTPDNS 的完整设计边界见 24.4；这个案例只取异步预取、缓存读取和兜底这三个处置动作。

### 改法

网络治理按三步改：

1. API、图片、大文件、日志分 Dispatcher；API 请求保留稳定并发窗口，大文件和预取限制并发。
2. 给所有请求接 EventListener，产出阶段耗时和连接复用指标；慢请求必须能定位到 DNS、建连、服务端、下载或业务解析。
3. HTTPDNS 只走缓存读取，缓存失效时后台刷新；返回 IP 要有 TTL、失败隔离和系统 DNS 兜底。

这段配置展示分 Dispatcher 的边界。数字只是示例，生产值要用线上阶段耗时和服务端限流能力校准。

```kotlin
object HttpClients {
    private val apiDispatcher = Dispatcher().apply {
        maxRequests = 64
        maxRequestsPerHost = 8
    }

    private val bulkDispatcher = Dispatcher().apply {
        maxRequests = 6
        maxRequestsPerHost = 2
    }

    val apiClient: OkHttpClient = OkHttpClient.Builder()
        .dispatcher(apiDispatcher)
        .eventListenerFactory { MetricsEventListener() }
        .build()

    val bulkClient: OkHttpClient = apiClient.newBuilder()
        .dispatcher(bulkDispatcher)
        .build()
}
```

`newBuilder()` 会复用原 client 的一部分配置，但新 Dispatcher 会形成独立排队策略。API 与大文件是否共享连接池，要结合域名、证书、Cookie、鉴权和流量隔离一起评估；不能为了复用连接把所有请求重新塞回同一个队列。

### 验收

网络优化验收看分位数和结构占比：DNS P95、建连/TLS P95、连接复用率、Dispatcher 排队 P95、首屏关键 API P95、响应体字节数、缓存命中率。Android 官方网络优化文档建议减少不必要传输、合并和延后网络访问、按网络与充电状态安排大任务；这些动作必须反映到指标上。[已验证: 官方文档, developer.android.com/develop/connectivity/network-ops/network-access-optimization]

如果优化后总耗时下降，但失败率、重试次数或耗电上升，这个方案不能算通过。弱网下的重试尤其要限制次数和退避窗口，避免接口慢变成重试风暴。

## 大文件上传下载优化

网络请求优化解决的是"多而碎"的请求被排队和建连拖慢的问题；大文件是"少而大"——单次传输拉长、占用连接更久、失败恢复成本更高。

### 现象

大文件问题通常有两类：下载任务跑在普通 API client 上，导致接口排队；上传任务一次性把文件读进内存，低端机出现 OOM 或长时间 GC。断点续传、网络切换、后台限制、进度恢复没有设计时，用户看到的是进度卡住、重新上传、耗电明显增加。

大文件不是普通请求的放大版。它占用更久的连接、更大的带宽窗口、更长的持久化状态和更复杂的失败恢复。24.6 处理缓存与压缩，24.7 处理离线队列，25.4 处理 WorkManager；上传下载方案要把这些能力组合起来。

### 下载治理

下载任务按“用户立即需要”和“后台可延后”拆开：

| 下载类型 | 执行方式 | 约束 |
| --- | --- | --- |
| 用户点击后立即打开 | 前台任务或可取消请求 | 展示进度，支持取消，失败保留恢复入口 |
| 离线包、地图包、模型包 | WorkManager / DownloadManager | Wi-Fi 或非计费网络、充电、电量不低、存储空间检查 |
| 图片和短视频缓存 | 图片库 / 媒体缓存层 | 限制并发，按页面生命周期取消 |

Android 官方网络优化文档给出的典型方向是把完整下载安排到 Wi-Fi，必要时还要求设备充电；WorkManager 文档支持 `NetworkType.UNMETERED`、充电等约束。AOSP `DownloadManager` 也提供系统级下载入口，适合交给系统通知、网络和重试策略管理的公开下载任务。[已验证: 官方文档, developer.android.com/develop/connectivity/network-ops/network-access-optimization][已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work][已验证: AOSP android-35 SDK sources, android/app/DownloadManager.java]

这段 WorkManager 配置表达后台大文件下载的约束边界：非计费网络、充电和唯一任务名共同避免同一资源被重复下载。

```kotlin
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .setRequiresCharging(true)
    .build()

val request = OneTimeWorkRequestBuilder<LargeFileDownloadWorker>()
    .setConstraints(constraints)
    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
    .build()

WorkManager.getInstance(context).enqueueUniqueWork(
    "download-model-v3",
    ExistingWorkPolicy.KEEP,
    request,
)
```

如果用户明确点击“立即下载”，约束可以降级为 `CONNECTED`，但 UI 要提示流量和电量成本。后台预取不要偷偷抢占用户当前页面的 API 并发。

### 上传治理

上传比下载更容易出错，因为文件读取、压缩、分片、重试和服务端幂等都在客户端路径里。治理时按四个边界设计：

- 流式读取：不要把完整文件读进内存；用 `RequestBody` 从文件流分段写入 sink。
- 分片与断点：大文件拆成 chunk，每个 chunk 有编号、校验值和服务端确认状态。
- 幂等：上传会被重试，服务端要用 uploadId、chunk index、checksum 去重。
- 取消与恢复：用户取消、网络切换、进程重启后，客户端能从本地状态表恢复。

这段代码只保留流式 `RequestBody` 的写入路径。生产环境还要补 MIME、进度回调、取消检查、错误映射和分片状态。

```kotlin
class FileStreamingBody(
    private val file: File,
    private val mediaType: MediaType,
) : RequestBody() {
    override fun contentType(): MediaType = mediaType
    override fun contentLength(): Long = file.length()

    override fun writeTo(sink: BufferedSink) {
        file.source().use { source ->
            sink.writeAll(source)
        }
    }
}
```

这类实现避免一次性读完整文件，但不等于上传就安全。移动网络下可能在任意 chunk 失败；服务端如果没有幂等，客户端重试会制造重复文件或重复资源记录。

### 验收

大文件优化要用场景表验收：

| 场景 | 验收点 |
| --- | --- |
| Wi-Fi 正常网络 | 下载/上传 P50、P95、吞吐、CPU、内存峰值 |
| 蜂窝网络 | 是否尊重用户设置和网络计费状态 |
| 网络切换 | 断点是否恢复，失败是否可重试 |
| 进程被杀 | 本地状态能否恢复，临时文件是否清理 |
| 存储不足 | 是否提前检查空间，失败提示是否可操作 |
| 多任务并发 | 普通 API 是否被大文件请求挤占 |

Android `NetworkCapabilities` 提供 `NET_CAPABILITY_NOT_METERED` 等网络能力标记，可用于判断当前网络是否非计费；WorkManager 约束则负责把后台任务交给系统调度。两者都不能替代产品层确认：用户点击“立即上传”的路径，和后台预取大资源的路径，应该有不同策略。[已验证: AOSP android-35 SDK sources, android/net/NetworkCapabilities.java][已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work]

## 案例复盘清单

三个案例有同一条排查线：先把等待段拆出来，再把等待段归到 I/O、网络、调度或缓存命中率。SP ANR 看 `QueuedWork` 和文件大小；网络慢看 EventListener 阶段耗时和 Dispatcher 排队；大文件看队列隔离、断点状态和系统约束。

可复用的上线门槛如下：

- SP：单文件大小、写入频率、pending work 等待、`QueuedWork.waitToFinish()` ANR 占比都有监控。
- 网络：关键 API 有阶段耗时，DNS、建连、TLS、排队、TTFB、body、解析分开记录。
- 大文件：独立并发策略、支持取消/恢复、尊重网络约束，不抢占首屏 API 请求。
- 缓存：记录命中率和过期原因；命中率低时先改访问模式和淘汰策略，再加容量。
- 灰度：每个优化都有回滚开关，按设备档位、网络类型和版本分组看 P95/P99。

[已验证: AOSP android-35 SDK sources, SharedPreferencesImpl / QueuedWork / DownloadManager / NetworkCapabilities]
[已验证: 官方文档, Android Developers network access optimization / WorkManager define work / SharedPreferences.Editor / DataStore]
[已验证: OkHttp docs, Calls / Events / Dispatcher]
