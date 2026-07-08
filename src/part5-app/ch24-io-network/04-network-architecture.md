---
title: "网络架构与连接管理"
chapter: "24.4"
section: "24.4"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [okhttp, connection-pool, httpdns, weak-network, dispatcher]
confidence: "medium"
last_verified: "2026-06-03"
last_verified_against: "Android Developers docs 2026-05-14 + OkHttp 5.x docs + AOSP android-17.0.0_r1 SDK sources"
drafted_date: "2026-05-14"
reviewed_date: "2026-06-03"
reviewed_by: "openclaw-task6"
polish_count: "2"
task6_result: "pass-light-edit"
task6_state: "reviewed"
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_result: "fixed-lite"
task2b_state: "fixed"
path: ""
related_chapters: ["24.5", "12.2", "12.3"]
last_task6_at: "2026-07-08T08:10:41+08:00"
last_task6_audit: "2026-07-08"
last_task2b_lite_at: "2026-07-08"
last_task2a_at: "2026-05-14T09:21:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-03"
last_task9_at: "2026-06-03T09:20:00+08:00"
last_task9_autofix_at: "\"2026-06-03\""
task2b_verified_at: "2026-06-26T07:27:19+08:00"
task2b_verify_result: "stale-state-fixed: task6_state revisiting→reviewed (already finalized)"
task6_review_notes_round2: "2026-07-08 Task6 revisiting-review round2: pass-light-edit (3 L1 fixes: frontmatter引号清理, Android 35→android-17.0.0_r1, path字段修正)"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-08
---

# 网络架构与连接管理

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 OkHttp 连接池与复用策略
- 🔹 DNS 优化与 HTTPDNS
- 🔹 网络请求优先级与调度
- 🔹 弱网优化策略

### 扩展(可选深入)

- 🔸 (待扩展)

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解网络架构与连接管理

网络性能问题很少只由一个接口慢导致。DNS 抖动、连接复用失效、并发请求挤占、弱网重试放大流量——随便哪个都能把一次页面加载拖成多段等待。第 12 章已经拆解过网络耗时和 TLS 传输细节。落到 App 架构侧，有四个工程问题必须回答：连接怎么复用、DNS/HTTPDNS 怎么接入、请求怎么排队、弱网下怎么收敛失败。

本节判断基于 OkHttp 5.x 文档、Android Connectivity / NetworkCapabilities / WorkManager 官方文档，以及 android-17.0.0_r1 SDK sources 中 `ConnectivityManager`、`NetworkCapabilities`、`StrictMode` 和 `DnsResolver` 的源码。

## 网络架构的四个控制面

App 网络层至少要分成四个控制面:连接、解析、调度、容错。

| 控制面 | 负责的问题 | 常见故障 | 主要观测点 |
|---|---|---|---|
| 连接 | TCP/TLS/HTTP 连接怎样创建和复用 | 每次请求重新建连、TLS 握手占比高、HTTP/2 复用失败 | `connectStart`、`secureConnectStart`、`connectionAcquired` |
| 解析 | 域名怎样变成可连接 IP | DNS 慢、单 IP 故障、IPv6/IPv4 回退慢、HTTPDNS 与 TLS 校验冲突 | `dnsStart`、`dnsEnd`、返回 IP 列表、失败 IP |
| 调度 | 哪些请求先发、哪些请求排队或取消 | 首页被低优先级请求挤占、同域名并发过高、后台同步耗电 | Dispatcher 队列、业务优先级、生命周期取消 |
| 容错 | 网络差时怎样重试、降级、缓存 | 重试风暴、接口雪崩、弱网白屏、离线不可用 | 超时类型、重试次数、缓存命中、NetworkCapabilities |

这四个面要分开设计。连接复用解决的是建连成本;DNS 解决的是可达性和首段延迟;调度解决的是资源竞争;弱网策略解决的是失败后的用户体验。把所有逻辑塞进一个 `Interceptor`,后续很难判断一条请求到底慢在哪一段。

[已验证: 官方文档, https://square.github.io/okhttp/features/connections/] [已验证: 官方文档, https://developer.android.com/develop/connectivity/network-ops/connecting]

## OkHttp 连接池与复用策略

OkHttp 判断连接复用时先看 `Address`,但不能把它理解成唯一边界。官方文档把请求拆成 URL、Address、Route 三层:URL 描述资源;Address 描述 scheme、host、port、TLS、代理、协议等静态连接配置;Route 描述 DNS 返回的具体 IP、代理和 TLS 版本等动态选择。相同 Address 更容易复用底层连接;HTTP/2 场景下,OkHttp 还可能在证书、HostnameVerifier、CertificatePinner、Route IP 等条件满足时做 connection coalescing,让不同 hostname 共享同一条连接。HTTP/1.x 复用空闲连接,HTTP/2 在同一连接上做多路复用。 [已验证: 官方文档, https://square.github.io/okhttp/features/connections/]

工程上最稳的做法是按网络策略复用 `OkHttpClient`,而不是每个业务模块都 new 一个 client。`OkHttpClient` 持有自己的 `ConnectionPool`、`Dispatcher`、DNS、TLS 配置和拦截器。随手创建 client 会带来三个问题:连接池被切碎、Dispatcher 并发不可控、Cookie/Auth/证书策略容易分叉。

一个可维护的组织方式:

```kotlin
object NetworkClients {
    private val apiDispatcher = Dispatcher().apply {
        maxRequests = 64
        maxRequestsPerHost = 8
    }

    val api: OkHttpClient = OkHttpClient.Builder()
        .dispatcher(apiDispatcher)
        .connectionPool(ConnectionPool(10, 5, TimeUnit.MINUTES))
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .fastFallback(true)
        .eventListenerFactory { NetworkEventListener() }
        .build()
}
```

这段配置只表达方向,不代表所有 App 都该使用相同数字。`maxRequests` 控制总并发,`maxRequestsPerHost` 控制单 host 并发;超出限制的异步请求会在 Dispatcher 内存队列等待。OkHttp 文档也提醒,单 host 限制按 URL host 计算,共享同一 IP 或代理时仍可能在网络侧汇聚。 [已验证: 官方文档, https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dispatcher/] [已验证: 官方文档, https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dispatcher/max-requests.html] [已验证: 官方文档, https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dispatcher/max-requests-per-host.html]

连接池参数要跟业务形态匹配:

| App 形态 | 建议方向 | 判断依据 |
|---|---|---|
| 首页短请求多、域名集中 | 共享 client,保留适量空闲连接 | 降低重复 TCP/TLS 建连成本 |
| 图片/视频与 API 域名分离 | API、图片、下载可分 client 或至少分 Dispatcher | 避免大文件请求占满 API 并发 |
| 登录态和匿名态共存 | 同一 host 下谨慎分 client,Cookie/Auth 策略要明确 | 防止连接池、CookieJar、Authenticator 行为不一致 |
| 大文件上传下载 | 独立 Dispatcher,限制并发,支持取消和断点 | 避免长连接占住普通 API 请求槽 |

预连接要克制。对首屏必用域名,可以通过轻量请求或业务启动阶段的真实请求建立连接;对低概率页面提前建连,可能只是在消耗电量和服务器连接数。预连接收益要用 EventListener 统计:如果 `connect + secureConnect` 占比低,继续预连接不会改善主要瓶颈。

```kotlin
class NetworkEventListener : EventListener() {
    override fun dnsStart(call: Call, domainName: String) {}
    override fun dnsEnd(call: Call, domainName: String, inetAddressList: List<InetAddress>) {}
    override fun connectStart(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy) {}
    override fun secureConnectStart(call: Call) {}
    override fun connectionAcquired(call: Call, connection: Connection) {}
    override fun responseHeadersStart(call: Call) {}
    override fun callFailed(call: Call, ioe: IOException) {}
}
```

`connectionAcquired` 前后的时间能区分"复用了已有连接"还是"重新建连"。这比只看接口总耗时更有用;总耗时慢可能是服务端慢,也可能是 DNS、建连、TLS 或排队慢。详见 12.3 节。 [已验证: 官方文档, https://square.github.io/okhttp/features/connections/]

## DNS 优化与 HTTPDNS

OkHttp 默认使用系统 DNS。`Dns` 接口允许业务提供自定义实现:返回某个 hostname 对应的 `InetAddress` 列表,OkHttp 会按返回顺序尝试连接;某个地址失败时,会继续尝试后续地址,直到连接成功或候选地址耗尽。 [已验证: 官方文档, https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dns/]

HTTPDNS 的价值在于绕开本地 DNS 污染、缩短解析耗时、按运营商或区域选择更合适的 IP。但接入 HTTPDNS 时要保留三条边界:

1. **不要把 HTTPS URL 改成 IP URL。** OkHttp 的自定义 `Dns` 应该返回 IP,URL 仍然保留原始 hostname。这样 SNI、证书校验、HostnameVerifier、Cookie 域名规则仍按域名工作。
2. **保留系统 DNS 兜底。** HTTPDNS 服务不可用、返回空列表、返回不可达 IP 时,必须回退到 `Dns.SYSTEM` 或平台解析结果。
3. **遵守 TTL 与失败隔离。** DNS 缓存不是越久越好。移动网络切换、CDN 调度、灰度发布都会改变最优 IP;单个 IP 连接失败后要短时间隔离,不能在每次请求里反复尝试同一个坏地址。

`Dns.lookup()` 位于 OkHttp 的同步建连路径,不能在这里实时发 HTTPDNS 网络请求。更稳的模型是后台异步预取、按 TTL 写入本地缓存,`lookup()` 只读取已缓存且未隔离的结果;缓存缺失或不可用时回退系统 DNS,HTTPDNS 服务自身也要使用独立 bootstrap client,避免递归依赖同一个业务 client。

一个安全的自定义 DNS 骨架如下:

```kotlin
class HttpDns(
    private val httpDns: HttpDnsService,
    private val fallback: Dns = Dns.SYSTEM,
) : Dns {
    override fun lookup(hostname: String): List<InetAddress> {
        val records = httpDns.cachedRecords(hostname)
            .filter { it.isNotExpired && !it.isQuarantined }
            .mapNotNull { it.toInetAddressOrNull() }

        return records.ifEmpty { fallback.lookup(hostname) }
    }
}
```

DNS 结果还要跟 Android 网络状态结合。`NetworkCapabilities` 文档写明,`NET_CAPABILITY_INTERNET` 只表示网络配置上可访问互联网;`NET_CAPABILITY_VALIDATED` 表示系统最近一次确认过实际互联网可达;`NET_CAPABILITY_NOT_METERED` 表示网络不按字节计费,适合推迟大下载到该能力出现时再执行。 [已验证: 官方文档, https://developer.android.com/reference/android/net/NetworkCapabilities] [已验证: AOSP android-17.0.0_r1, /Users/gracker/Android/sources/android-17.0.0_r1/android/net/NetworkCapabilities.java]

```kotlin
fun NetworkCapabilities.isUsableForApi(): Boolean {
    return hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
        hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
}

fun NetworkCapabilities.isGoodForBulkDownload(): Boolean {
    return isUsableForApi() &&
        hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
}
```

不要用 "Wi-Fi 就一定适合大下载、蜂窝网络就一定不适合" 这种判断。AOSP 注释也提示,是否计费应看 `NET_CAPABILITY_NOT_METERED`,不要直接看 transport;可能存在计费 Wi-Fi,也可能存在不计费蜂窝连接。 [已验证: AOSP android-17.0.0_r1, /Users/gracker/Android/sources/android-17.0.0_r1/android/net/NetworkCapabilities.java]

OkHttp 5 的 `fastFallback(true)` 默认开启,它会并发尝试多个 TCP 连接并保留最先成功的连接,用来平衡 IPv6/IPv4 或多 IP 场景下的连接延迟和资源浪费。HTTPDNS 返回多 IP 时,不要只返回一个"看起来最优"的地址;保留候选列表,才能让连接层有回退空间。 [已验证: 官方文档, https://square.github.io/okhttp/5.x/okhttp/okhttp3/-ok-http-client/-builder/fast-fallback.html]

## 网络请求优先级与调度

OkHttp Dispatcher 控制的是并发执行,不提供业务优先级队列。首页接口、图片预加载、埋点、日志上报、文件上传如果直接丢进同一个 client,Dispatcher 只能按进入队列的顺序和 host 限制执行。业务优先级要放在 OkHttp 之上。

一套可执行的分层如下:

| 层级 | 负责内容 | 示例 |
|---|---|---|
| UI / ViewModel | 生命周期、取消、去重 | 页面销毁取消请求;同一个 pull-to-refresh 合并 |
| Repository | 数据来源选择 | 先读缓存,再决定是否请求网络 |
| RequestScheduler | 业务优先级、限流、降级 | 首屏接口高优先级;埋点延迟批量发 |
| OkHttp Dispatcher | 总并发和单 host 并发 | `maxRequests`、`maxRequestsPerHost` |
| WorkManager / JobScheduler | 后台任务约束 | 仅在不计费网络、低电量保护外执行同步 |

前台请求的原则是"少排队、可取消、可去重"。页面进入时只发首屏必要请求;同一资源正在请求时复用结果;页面退出后取消 tag 绑定的 call。OkHttp 支持给 Request 设置 tag,调度层可以按页面、业务或请求类型统一取消。

```kotlin
val request = Request.Builder()
    .url(url)
    .tag(PageScope::class.java, pageScope)
    .build()

fun cancelPageCalls(client: OkHttpClient, pageScope: PageScope) {
    (client.dispatcher.queuedCalls() + client.dispatcher.runningCalls())
        .filter { it.request().tag(PageScope::class.java) == pageScope }
        .forEach { it.cancel() }
}
```

后台请求的原则是"可延迟、可批量、可约束"。Android 官方文档把网络请求视为耗电影响较大的行为,因为无线电从低功耗状态切到活跃状态有启动延迟和 tail time。把多次零散请求合并成一次批量请求,通常比每隔十几秒唤醒一次网络更省电。 [已验证: 官方文档, https://developer.android.com/develop/connectivity/network-ops/network-access-optimization] [已验证: 官方文档, https://developer.android.com/develop/connectivity/minimize-effect-regular-updates]

非用户触发的同步、日志、配置拉取,应优先交给 WorkManager 这类受系统约束管理的调度工具,设置网络类型、低电量保护和退避重试。用户正在等待结果的请求才走前台 Dispatcher。后台请求一旦跟前台请求共用并发槽,用户会感知到"页面慢",但根因在调度策略。

[已验证: 官方文档, https://developer.android.com/develop/connectivity/minimize-effect-regular-updates]

## 弱网优化策略

弱网策略不能只写成"加大超时时间 + 多重试"。超时越长,用户等待越久;重试越多,网络越差时越容易放大排队和电量消耗。弱网要按失败类型处理。

| 失败类型 | 典型信号 | 处理方式 |
|---|---|---|
| 无可用网络 | `getActiveNetwork() == null` 或 NetworkCallback `onLost` | 直接返回离线态,等待网络恢复后再刷新 |
| 未验证互联网可达 | 缺少 `NET_CAPABILITY_VALIDATED` | 提示网络不可用,保留本地缓存,不做密集重试 |
| DNS 慢或失败 | `dnsStart` 到 `dnsEnd` 长、UnknownHostException | HTTPDNS / 系统 DNS 互为兜底,失败 IP 短时隔离 |
| 连接慢 | `connectStart` 后长时间无响应 | 缩短 connectTimeout,启用 fast fallback,保留多 IP 候选 |
| TLS 慢 | `secureConnectStart` 后长时间无响应 | 检查 TLS 版本、证书链、连接复用率;详见 12.4 节 |
| 服务端慢 | 已连上但 TTFB 高 | 服务端容量、CDN、缓存、接口拆分,不在客户端盲目重试 |
| 大响应慢 | headers 已到,body 下载慢 | 分页、压缩、断点续传、图片降级;详见 24.6 节 |

Android 要求网络操作离开主线程。官方文档说明,在主线程执行网络操作会抛出 `NetworkOnMainThreadException`;AOSP `StrictMode` 中 `detectNetwork()` 对应 `BlockGuard.Policy.onNetwork()`,在启用网络检测并设置 death penalty 时会抛出同一异常。弱网下更要避免任何同步网络调用进入主线程,否则一次 DNS 或连接超时就可能拖住 UI。 [已验证: 官方文档, https://developer.android.com/develop/connectivity/network-ops/connecting] [已验证: AOSP android-17.0.0_r1, /Users/gracker/Android/sources/android-17.0.0_r1/android/os/StrictMode.java]

重试只适合幂等请求,且必须有上限和退避。GET、HEAD、部分可安全重试的查询接口可以做指数退避加随机抖动;POST/支付/下单/写操作必须依赖服务端幂等键,客户端不能因为超时就无条件重发。

```kotlin
fun nextDelayMs(attempt: Int): Long {
    val base = 300L * (1 shl attempt.coerceAtMost(5))
    val jitter = Random.nextLong(0, 250)
    return (base + jitter).coerceAtMost(10_000L)
}
```

弱网体验还要有产品侧降级:列表页优先展示缓存和骨架屏;图片加载从低清到高清;非必要模块延迟加载;上传任务进入后台队列;需要用户确认的操作给出明确状态。技术层能收敛失败,不能把所有网络问题都变成"转圈等待"。

## 连接池边界也决定账号和安全边界

连接池复用看起来是性能问题,但它也影响账号、证书和代理策略。不同业务如果使用不同证书固定策略、不同代理、不同 Authenticator、不同 CookieJar,就不应该强行合并到一个 client;相同 host、相同安全策略、相同登录态的 API 请求才适合共享连接池。

建议把 client 拆分标准写进网络层设计文档:

- `apiClient`:普通业务 API,共享 Cookie/Auth、统一 EventListener。
- `imageClient`:图片请求,独立 Dispatcher,可配更大的读超时和缓存策略。
- `downloadClient`:大文件下载,独立并发限制,支持断点和后台约束。
- `uploadClient`:上传请求,独立写超时、重试和幂等策略。
- `noAuthClient`:登录前或公开资源,避免污染登录态 Cookie。

拆分不是越多越好。每多一个 client,就多一份连接池、Dispatcher 和配置维护成本。以"安全策略是否不同、请求时延模型是否不同、是否会互相挤占"为拆分条件,比按业务团队拆分更稳定。

[已验证: 官方文档, https://square.github.io/okhttp/features/connections/]



## Wi-Fi 评分与系统选网只保留观测边界

Wi-Fi 评分和默认网络选择属于系统侧策略，展开见 24.9。本节只保留 App 网络架构需要关注的边界：Android 12 及以上 Connectivity 侧使用 `NetworkScore` flags 和 `NetworkRanker` 选择网络；Wi-Fi 侧候选评分会受 RSSI、吞吐估计、用户近期选择、metered / validated 状态和 OEM overlay 影响。旧资料里的"0-20/40/60 固定阈值"和特定 scorer 权重不能当作通用结论。

App 侧要记录 default network、transport、`NET_CAPABILITY_VALIDATED`、`NET_CAPABILITY_NOT_METERED`、DNS / TCP / TLS / TTFB 分段耗时和切网事件序号。系统侧排查再通过 bugreport、`dumpsys wifi`、`dumpsys connectivity` 与 Perfetto / logcat 还原决策过程。

[已验证: 官方文档, https://source.android.com/docs/core/connect/network-selection]
[已验证: 官方文档, https://source.android.com/docs/core/connect/wifi-network-selection]
[交叉引用: 24.9 Wi-Fi 评分、网络选择与连接切换性能]



## OkHttp Dns.lookup() 同步阻塞边界与死锁风险

OkHttp `Dns` 接口的 `lookup(hostname)` 方法是**同步阻塞调用**，发生在建连线程中。如果在 `lookup()` 内发起 HTTPDNS HTTP 请求,且该请求使用同一个 `OkHttpClient`,可能引发死锁:DNS 请求需要从连接池获取 HTTP session,但连接池为空且等待 DNS 结果释放。

### 源码锚点

**Dns 接口定义**:`okhttp/okhttp/src/main/kotlin/okhttp3/Dns.kt` (square/okhttp master)

```kotlin
fun interface Dns {
  @Throws(UnknownHostException::class)
  fun lookup(hostname: String): List<InetAddress>
}
```

官方文档明确要求:"Implementations of this interface **must be safe for concurrent use**."

**RouteSelector 调用路径**:`okhttp/okhttp/src/main/java/okhttp3/internal/http/RouteSelector.java` L124-L146

```java
// Try each address for best behavior in mixed IPv4/IPv6 environments.
List<InetAddress> addresses = address.dns().lookup(socketHost);
for (int i = 0, size = addresses.size(); i < size; i++) {
  InetAddress inetAddress = addresses.get(i);
  inetSocketAddresses.add(new InetSocketAddress(inetAddress, socketPort));
}
```

调用链:
1. `RouteSelector.next()` → `resetNextProxy()` → `resetNextInetSocketAddress()`
2. `address.dns().lookup(socketHost)` 在当前建连线程同步执行
3. 如果 `lookup()` 内部发起网络请求,该线程被阻塞

### 正确工程模式：异步预取 + 两级缓存

```
[App Startup / Background Thread]
    → WorkManager / Coroutine Dispatchers.IO
        → HTTPDNS SDK.query(domain)
            → HTTP GET to HTTPDNS Service
            → Parse { ips: ["1.2.3.4", ...], ttl: 600 }
            → Write to Memory Cache (LruCache)
            → Write to Disk Cache (SharedPreferences / SQLite)

[OkHttp Dns.lookup() call]
    → Check Memory Cache (L1)
        → HIT: return immediately
        → MISS: check Disk Cache (L2)
            → HIT: return + async refresh
            → MISS: fallback to Dns.SYSTEM.lookup()
```

关键设计点:
- **同步路径只读缓存**:绝对不能在 `lookup()` 内发起网络请求
- **HTTPDNS 服务使用独立 OkHttpClient**:与业务请求隔离,避免死锁
- **TTL 管理**:缓存 TTL 建议设为 HTTPDNS 服务 TTL 的 80%
- **失败隔离**:HTTPDNS 不可达时自动 fallback 到 `Dns.SYSTEM`

**验证依据**：OkHttp `Dns.kt` 接口定义、`RouteSelector.java`（L124-L146）调用路径、[OkHttp 官方 Dns 文档](https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dns/index.html)。


## 工程检查清单

加工网络架构时,可以按下面的清单做一次自检:

- App 内是否存在多个无理由创建的 `OkHttpClient`?
- `maxRequests`、`maxRequestsPerHost` 是否按业务场景设置,而不是沿用默认值?
- 首页 API、图片、埋点、下载是否共用同一组并发槽?
- DNS 是否保留系统兜底、TTL、失败隔离、多 IP 回退?
- HTTPS 是否仍使用原始 hostname,避免 IP URL 破坏 SNI 和证书校验?
- 是否通过 EventListener 采集 DNS、连接、TLS、TTFB、失败类型?
- 页面销毁、刷新去重、重复点击是否会取消或复用请求?
- 后台同步是否使用 WorkManager / JobScheduler 约束网络和电量?
- 弱网重试是否限制幂等性、次数、退避和随机抖动?
- 大下载是否推迟到不计费网络或用户明确触发?

## 扩展

### CDN、HTTP/2、HTTP/3 与 gRPC 的协议选型

HTTP/2 多路复用、HTTP/3/QUIC、gRPC 与协议兼容策略详见 24.5。这里保留和连接/调度相关的接口边界:网络层要把协议、连接复用、fallback 结果暴露给上层和 APM,避免协议细节在 24.4、24.5 两处重复。

### 网络缓存与离线优先

24.6、24.7 负责展开缓存策略、HTTP 缓存头、多级缓存、离线队列与冲突解决。这里保留架构接口:请求层要暴露缓存命中、网络失败、可重试状态,给上层决定展示缓存还是进入离线队列。
