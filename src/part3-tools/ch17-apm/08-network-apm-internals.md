---
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
chapter: '17.8'
confidence: high
last_verified: '2026-10-26'
last_source_verified_at: '2026-10-26T08:06:46.256273+08:00'
last_idle_audit_at: '2026-10-18'
last_verified_against: Published OkHttp 5.3.0, 5.4.0 and 5.5.1 JVM artifacts and source archives; EventListener, Exchange, BridgeInterceptor, CacheInterceptor, retry and fast-fallback implementation; Cronet API at fe8f6a81fa141754b36db3e0bf47540a67c4c428; AGP Instrumentation API and AOSP android-17.0.0_r1 anchors
verification_scope_note: 2026-10-26 全文和34张章节配图复核；固定5.3.0、5.4.0、5.5.1发布物在JVM验证缓存、压缩、预读和HTTP1临时响应；route、TLS、预算及异常路径为人工驱动回调。注册片段和ASM改写经JVM编译与执行；AGP DSL仅按官方API静态核对。未运行完整Android构建、真机、真实TLS、HTTP2或HTTP3、PLT Hook与特权BPF验收。
related_chapters:
- '17.0'
- '15.7'
- '17.1'
section: '17.8'
sources:
- type: reference
  path: https://square.github.io/okhttp/features/events/
- type: reference
  path: https://square.github.io/okhttp/features/interceptors/
- type: reference
  path: https://lysine.dev/okhttp/features/events/
- type: reference
  path: https://lysine.dev/okhttp/features/interceptors/
- type: reference
  path: https://github.com/lysine-dev/okhttp
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/CHANGELOG.md
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/CallServerInterceptor.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/CallServerInterceptor.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http1/Http1ExchangeCodec.kt
- type: official
  path: https://developer.android.com/reference/tools/gradle-api/8.6/com/android/build/api/instrumentation/AsmClassVisitorFactory
- type: official
  path: https://developer.android.com/build/releases/gradle-plugin-api-updates
- type: official
  path: https://developer.android.com/build/releases/gradle-plugin-roadmap
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/UrlRequest.Callback
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo.Metrics
tags:
- apm
- network
- okhttp
- asm
- cronet
title: 网络 APM 底层捕获原理
---

# 网络 APM 底层捕获原理

网络 APM（Application Performance Monitoring，应用性能监控）难在采样这一步。一条请求可能经过业务封装、HTTP 客户端、DNS（域名解析）、socket（网络通信端点）、TLS（传输加密协议）和内核网络栈；缓存命中、连接复用与明文 HTTP 会跳过其中部分阶段；WebView、Cronet（Chromium 提供的网络库） 或 C/C++ SDK 还会绕开应用熟悉的 Java 入口。监控图表上的一条“请求耗时”，要先把这一路上发生的事件正确配对，才有诊断价值。


> 源码基线：AOSP `android-17.0.0_r1`（Android 17 / API 37）；内核 `android17-6.18-2026-06_r6`。

OkHttp、Cronet 和 Android Gradle Plugin（AGP，Android 构建插件）独立发布，版本要用各自渠道核对，从 Android API 级别推不出来。截至 2026 年 10 月 26 日，OkHttp 当前仓库为 `lysine-dev/okhttp`，Maven Central 的最新稳定发布为 2026 年 10 月 22 日的 5.5.1。本文示例固定使用 5.3.0；本轮同时核对了 5.4.0 与 5.5.1 的发布源码及接口，三者保留本文使用的 `retryDecision`、`followUpDecision` 与响应事件签名。接口相同不保证全部内部行为相同，升级后仍要运行边界测试。

## 1. “无侵入”指业务入口免埋点

“无侵入”通常指业务开发者不必在每个接口旁手写计时代码。采集器仍会进入构建过程或请求执行路径，只是入口集中在客户端工厂、字节码插件或 Native（由 C/C++ 编译的本地代码） 代理里。我们先把各层的典型入口和它们各自答不了的问题列出来：

| 层级 | 典型入口 | 适合采集 | 无法独立回答的问题 |
| --- | --- | --- | --- |
| HTTP 语义层 | OkHttp `Interceptor`（拦截器）、Cronet callback（事件回调） | 路由、方法、状态码、缓存、业务 trace id（跨系统追踪同一次请求的标识） | DNS、建连和 TLS 的准确边界 |
| 客户端事件层 | OkHttp `EventListener`、Cronet metrics（测量结果） | DNS、route/connect、TLS、请求和响应事件 | 未经过该客户端的请求 |
| 构建期插桩层 | AGP Instrumentation API + ASM（修改 class 字节码的访问器库） | `HttpURLConnection` 调用点、封装在依赖中的 Java 请求入口 | Native 静态链接、自定义协议栈、反射或动态加载代码 |
| Native 动态链接层 | 库回调、PLT/GOT Hook（通过动态符号入口拦截函数调用） | libc（C 标准库实现）或动态 TLS 库的调用、返回值和 `errno`（系统调用错误码） | 静态链接、隐藏符号、直接系统调用、HTTP 业务语义 |
| 系统与内核层 | TrafficStats、系统 BPF（在内核中运行受限程序的机制）、受控测试工具 | UID（应用在 Linux 中的身份编号）/socket 流量、RTT（Round-Trip Time，网络往返时延）、重传和内核错误 | TLS 内的 URL、header（请求或响应元数据）和业务请求边界 |


这些层看到的对象并不重合：HTTP 请求、DNS 查询、建连尝试和 socket 之间，没有一一对应关系。一次调用可能复用现成连接，也可能解析一次域名后并行尝试多个地址；HTTP/2 和 HTTP/3 还允许不同请求通过各自的 stream（连接内的独立逻辑数据流） 共享连接，HTTP/3 用的 QUIC 则是基于 UDP、内置加密与多路复用的传输协议。

对应关系这么松，我们设计采集 schema（样本的字段结构） 时就要多留一层结构：只放一个 `attempt` 数组撑不住，重试和多路复用很快会让它失真；trace（跨服务串起同一次请求的调用轨迹） id 也要记清它对应 HTTP 的哪一层。

更稳妥的结构包含四条相互关联的记录：

- `call`：业务发起的一次客户端调用，是最外层生命周期。
- `dns_span`：一次域名解析区间，可出现零次或多次。
- `route_attempt`：对某个 IP、端口和 proxy（代理服务器） 的一次连接尝试。
- `exchange`：一轮开始写入 request 的 HTTP 交换尝试。`requestHeadersStart` 不保证数据已发上网络，写入或读取失败时也可能没有 response；重定向、鉴权挑战和部分故障恢复可产生新 exchange。


关联键要从同一客户端实例内的事件里取；按时间窗口猜，容易把并发请求配错。底层 socket 数据还原不出可靠的 HTTP/2 stream 或 QUIC stream 时，就只保留连接维度的关联，并把可信度写进样本。

## 2. OkHttp：事件时间线与请求语义分开采

OkHttp 主通道上，我们把 `EventListener`（按阶段通知网络事件的监听器） 和两类 `Interceptor` 组合起来用：

- `EventListener` 记录代理选择、DNS、连接、TLS、请求写入、响应读取、缓存与失败事件。
- 应用拦截器适合读取 request id（请求关联标识）、业务路由和最终响应语义；正常执行到拦截器链的 `Call` 会经过它，缓存命中也会经过它。需要 listener factory 读取的 id 必须在 `newCall()` 前写入原始请求。
- 网络拦截器按网络 exchange 执行，可看到发往网络的 request、连接和中间 response；纯缓存命中不会经过它。

Interceptor 一侧没有 `dnsStart`、`connectStart` 或 `secureConnectStart` 这类阶段事件；网络拦截器离传输层更近，看到的仍是一整段 exchange，拆不出 DNS、TCP 和 TLS。原始 request 用回调参数 `call` 的 `request()` 取；重定向或鉴权后发到网络上的 wire request，则要从 `requestHeadersEnd(call, request)` 取。

request id 的传递还要更早一步：我们在 `newCall()` 前把 `NetworkRequestId` 写入 `Request.tag()`，由 factory 从原始 `call.request()` 读取，应用拦截器读取同一 tag。id 本身不含用户信息或业务内容。在拦截器里临时创建的 tag，传不到已经创建好的 listener。

<!-- gracker-diagram: ch17-08-04-listeners-interceptors -->
![三种 OkHttp 采集入口的分工](../../assets/diagrams/ch17/ch17-08-04-listeners-interceptors.png)

图：应用语义、网络 exchange 与阶段回调由不同入口采集。 request id 在 newCall 前设置，factory 与拦截器才可读取同一 tag。

### 2.1 先读懂事件序列的四个例外

OkHttp 5.3.0 的 `EventListener` 源码把事件顺序写得很明确，我们先把四个例外记牢：

1. 连接复用时，代理选择、DNS 和 connect 事件可能全部缺席。
2. retry 与 follow-up（重定向、鉴权等后续请求）——前者是连接故障后的再次尝试，后者是重定向、鉴权等触发的后续请求——会重复产生事件序列。`requestFailed`、`responseFailed` 和 `connectFailed` 出现后，整个 `Call` 仍可能继续。
3. `Expect: 100-continue` 会先等服务端允许再发送 request body，因此 body 事件可能落在 response headers 事件之间；duplex body（请求和响应可同时传输的双工 body） 还允许两边交错传输。
4. `canceled` 可以与其他回调并发，甚至晚于 `callEnd`。5.3.0 的 fast fallback 已会错开并发执行 TCP 连接尝试；多个 route 的 connect 回调可能交错到达，先后顺序没有保证。当前实现选出成功的 TCP plan 后再进行 TLS，但公开 TLS 回调不携带地址，采集器别按数组末项补出确定的 route 归属。


还有一个容易遗漏的版本点：OkHttp 4.3 以前，`responseHeadersStart` 在“客户端准备读取 header”时就过早触发；4.3 起调整了触发位置。按本文使用的 5.3.0 与 5.4.0 实现，它在 `readResponseHeaders()` 返回后触发，HTTP/1.1 此时已读完一个 header block。这个回调给不出精确的首字节时间；遇到临时响应时，最终响应的起点单凭这一次回调定不下来。后文按这一触发位置计算观测值。`requestHeadersEnd(call, request)` 的签名从 OkHttp 3.9 就存在，但不同版本的响应回调语义要按各自源码核对。

<!-- gracker-diagram: ch17-08-06-headers-boundary -->
![响应回调在读取 Header block 之后](../../assets/diagrams/ch17/ch17-08-06-headers-boundary.png)

图：本文版本先完成一次 header block 读取，再触发 responseHeadersStart。 首次 block 可能是临时响应；这个回调给不出精确首字节时间。

### 2.2 一份不会覆盖 retry/follow-up 的核心实现

下面的 Kotlin 代码展示 per-call listener，也就是每个 `Call` 独占一个监听器实例。它在私有锁内维护有界状态并生成独立快照，分别保存连接、TLS、决策与缓存事件。为了让关注点留在事件配对上，`NetworkDimensions` 代表项目自己的脱敏字段转换器；`NetworkMetricSink.enqueue()` 只把快照放入内存队列，不在回调线程做序列化或 I/O。

```kotlin
data class DnsSpan(
    val host: String,
    val startNs: Long,
    var endNs: Long? = null,
    var addressCount: Int? = null,
)

data class RouteAttempt(
    val address: String,
    val proxy: String,
    val connectStartNs: Long,
    var connectEndNs: Long? = null,
    var protocol: String? = null,
    var failure: String? = null,
    var failureNs: Long? = null,
)

data class HttpExchange(
    val index: Int,
    var requestHeadersStartNs: Long? = null,
    var requestHeadersEndNs: Long? = null,
    var requestBodyStartNs: Long? = null,
    var requestBodyEndNs: Long? = null,
    var responseHeadersStartNs: Long? = null,
    var responseHeadersEndNs: Long? = null,
    var responseBodyStartNs: Long? = null,
    var responseBodyEndNs: Long? = null,
    var requestBytes: Long? = null,
    var responseBodyBytesObserved: Long? = null,
    var route: String? = null,
    var statusCode: Int? = null,
    var protocol: String? = null,
    var requestIsDuplex: Boolean = false,
    var hasExpectContinue: Boolean = false,
    var requestFailure: String? = null,
    var responseFailure: String? = null,
)

data class TimedEvent(
    val kind: String,
    val timeNs: Long,
    val decision: Boolean? = null,
    val statusCode: Int? = null,
)

data class ConnectionEvent(
    val timeNs: Long,
    val address: String,
    val proxy: String,
    val protocol: String,
)

data class NetworkRequestId(val value: String)

data class CallMetric(
    val callId: String,
    val callStartNs: Long,
    val callEndNs: Long,
    val terminalFailure: String?,
    val cancelObservedBeforeTerminal: Boolean,
    val droppedEvents: Long,
    val unmatchedExchangeEvents: Long,
    val tlsEvents: List<TimedEvent>,
    val decisions: List<TimedEvent>,
    val cacheEvents: List<TimedEvent>,
    val connections: List<ConnectionEvent>,
    val dns: List<DnsSpan>,
    val routes: List<RouteAttempt>,
    val exchanges: List<HttpExchange>,
)

interface NetworkMetricSink {
    /** 只能把独立快照放入内存队列；入队后不得修改，序列化和 I/O 在后台完成。 */
    fun enqueue(metric: CallMetric)
}

interface NetworkDimensions {
    /** 返回值不得包含原始 query、动态 path 标识或未裁剪的网络地址。 */
    fun route(url: HttpUrl): String
    fun host(domainName: String): String
    fun address(address: InetSocketAddress): String
    fun proxy(proxy: Proxy): String
}

class NetworkMetricEventListenerFactory(
    private val sink: NetworkMetricSink,
    private val dimensions: NetworkDimensions,
    private val clock: () -> Long = System::nanoTime,
) : EventListener.Factory {
    override fun create(call: Call): EventListener =
        NetworkMetricEventListener(
            sink, dimensions, clock,
            call.request().tag(NetworkRequestId::class.java)?.value
                ?: UUID.randomUUID().toString(),
        )
}

private class NetworkMetricEventListener(
    private val sink: NetworkMetricSink,
    private val dimensions: NetworkDimensions,
    private val clock: () -> Long,
    private val callId: String,
) : EventListener() {
    private val lock = Any()
    private var callStartNs = 0L
    private var cancelObserved = false
    private var finished = false
    private var acceptedEvents = 0
    private var droppedEvents = 0L
    private var unmatchedExchangeEvents = 0L
    private val maxEvents = 512
    private val tlsEvents = mutableListOf<TimedEvent>()
    private val decisions = mutableListOf<TimedEvent>()
    private val cacheEvents = mutableListOf<TimedEvent>()
    private val connections = mutableListOf<ConnectionEvent>()
    // 原始配对键仅在当前 call 内短暂保存，不进入快照或日志。
    private val pendingDns = mutableListOf<Pair<String, DnsSpan>>()
    private val pendingRoutes = mutableListOf<PendingRoute>()
    private data class PendingRoute(
        val address: InetSocketAddress,
        val proxy: Proxy,
        val metric: RouteAttempt,
    )
    private val dns = mutableListOf<DnsSpan>()
    private val routes = mutableListOf<RouteAttempt>()
    private val exchanges = mutableListOf<HttpExchange>()

    private fun record(action: () -> Unit) {
        synchronized(lock) {
            if (finished) return
            if (acceptedEvents >= maxEvents) {
                droppedEvents++
                return // 不再写半条后续记录；保留截断标记。
            }
            acceptedEvents++
            action()
        }
    }

    private fun dimension(action: () -> String): String =
        try { action() } catch (_: Exception) { "unknown" }

    private fun currentExchange(): HttpExchange? =
        exchanges.lastOrNull().also {
            if (it == null) unmatchedExchangeEvents++
        }

    private fun takeRoute(address: InetSocketAddress, proxy: Proxy): RouteAttempt? {
        val i = pendingRoutes.indexOfLast { it.address == address && it.proxy == proxy }
        return if (i < 0) null else pendingRoutes.removeAt(i).metric
    }

    override fun callStart(call: Call) {
        record { callStartNs = clock() }
    }

    override fun dnsStart(call: Call, domainName: String) {
        val hostKey = dimension { dimensions.host(domainName) }
        record {
            val span = DnsSpan(hostKey, clock())
            dns += span
            pendingDns += domainName to span
        }
    }

    override fun dnsEnd(
        call: Call,
        domainName: String,
        inetAddressList: List<InetAddress>,
    ) {
        record {
            val i = pendingDns.indexOfLast { it.first == domainName }
            if (i >= 0) pendingDns.removeAt(i).second.apply {
                endNs = clock()
                addressCount = inetAddressList.size
            }
        }
    }

    override fun connectStart(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
    ) {
        val addressKey = dimension { dimensions.address(inetSocketAddress) }
        val proxyKey = dimension { dimensions.proxy(proxy) }
        record {
            val attempt = RouteAttempt(
                address = addressKey,
                proxy = proxyKey,
                connectStartNs = clock(),
            )
            routes += attempt
            pendingRoutes += PendingRoute(inetSocketAddress, proxy, attempt)
        }
    }

    override fun secureConnectStart(call: Call) {
        record { tlsEvents += TimedEvent("start", clock()) }
    }

    override fun secureConnectEnd(call: Call, handshake: Handshake?) {
        record { tlsEvents += TimedEvent("end", clock()) }
    }

    override fun connectEnd(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
        protocol: Protocol?,
    ) {
        record {
            takeRoute(inetSocketAddress, proxy)?.apply {
                connectEndNs = clock()
                this.protocol = protocol?.toString()
            }
        }
    }

    override fun connectFailed(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
        protocol: Protocol?,
        ioe: IOException,
    ) {
        record {
            takeRoute(inetSocketAddress, proxy)?.apply {
                failure = ioe.javaClass.name
                failureNs = clock()
            }
        }
    }

    override fun connectionAcquired(call: Call, connection: Connection) {
        val route = connection.route()
        val address = dimension { dimensions.address(route.socketAddress) }
        val proxy = dimension { dimensions.proxy(route.proxy) }
        record {
            connections += ConnectionEvent(clock(), address, proxy, connection.protocol().toString())
        }
        // 仅凭最近一次 connectEnd 不能证明实际取得了哪次新建连接。
    }

    override fun requestHeadersStart(call: Call) {
        record {
            // 每次 wire request 都新建 exchange。不能用 responseBodyEnd 判断上一轮，
            // 因为 requestFailed/responseFailed 后不一定出现 responseBodyEnd。
            exchanges += HttpExchange(
                index = exchanges.size,
                requestHeadersStartNs = clock(),
            )
        }
    }

    override fun requestHeadersEnd(call: Call, request: Request) {
        val route = dimension { dimensions.route(request.url) }
        val requestIsDuplex = request.body?.isDuplex() == true
        val hasExpectContinue =
            request.header("Expect").equals("100-continue", ignoreCase = true)
        record {
            currentExchange()?.apply {
                requestHeadersEndNs = clock()
                this.route = route
                this.requestIsDuplex = requestIsDuplex
                this.hasExpectContinue = hasExpectContinue
            }
        }
    }

    override fun requestBodyStart(call: Call) {
        record { currentExchange()?.requestBodyStartNs = clock() }
    }

    override fun requestBodyEnd(call: Call, byteCount: Long) {
        record {
            currentExchange()?.apply {
                requestBodyEndNs = clock()
                requestBytes = byteCount
            }
        }
    }

    override fun requestFailed(call: Call, ioe: IOException) {
        record {
            currentExchange()?.requestFailure = ioe.javaClass.name
        }
    }

    override fun responseHeadersStart(call: Call) {
        record {
            // 记录回调时刻；它可能对应临时响应，不能标作最终响应的首字节。
            currentExchange()?.responseHeadersStartNs = clock()
        }
    }

    override fun responseHeadersEnd(call: Call, response: Response) {
        record {
            currentExchange()?.apply {
                // OkHttp 5.3.0 / 5.4.0 已在内部跳过 100、102..199。
                responseHeadersEndNs = clock()
                statusCode = response.code
                protocol = response.protocol.toString()
            }
        }
    }

    override fun responseBodyStart(call: Call) {
        record { currentExchange()?.responseBodyStartNs = clock() }
    }

    override fun responseBodyEnd(call: Call, byteCount: Long) {
        record {
            currentExchange()?.apply {
                responseBodyEndNs = clock()
                responseBodyBytesObserved = byteCount
            }
        }
    }

    override fun responseFailed(call: Call, ioe: IOException) {
        record {
            currentExchange()?.responseFailure = ioe.javaClass.name
        }
    }

    // 决策不创建 exchange：建连前可重试，纯缓存也可收到 follow-up 决定。
    override fun retryDecision(call: Call, exception: IOException, retry: Boolean) {
        record { decisions += TimedEvent("retry", clock(), decision = retry) }
    }

    override fun followUpDecision(call: Call, networkResponse: Response, nextRequest: Request?) {
        record {
            decisions += TimedEvent("followUp", clock(), nextRequest != null, networkResponse.code)
        }
    }

    override fun cacheHit(call: Call, response: Response) {
        record { cacheEvents += TimedEvent("hit", clock(), statusCode = response.code) }
    }

    override fun cacheMiss(call: Call) {
        record { cacheEvents += TimedEvent("miss", clock()) }
    }

    override fun cacheConditionalHit(call: Call, cachedResponse: Response) {
        record { cacheEvents += TimedEvent("conditional", clock(), statusCode = cachedResponse.code) }
    }

    override fun satisfactionFailure(call: Call, response: Response) {
        record { cacheEvents += TimedEvent("unsatisfied", clock(), statusCode = response.code) }
    }

    override fun canceled(call: Call) {
        synchronized(lock) { cancelObserved = true }
    }

    override fun callEnd(call: Call) = finish(null)

    override fun callFailed(call: Call, ioe: IOException) =
        finish(ioe.javaClass.name)

    private fun finish(terminalFailure: String?) {
        val snapshot = synchronized(lock) {
            if (finished) return
            finished = true
            pendingDns.clear()
            pendingRoutes.clear()
            CallMetric(
                callId = callId,
                callStartNs = callStartNs,
                callEndNs = clock(),
                terminalFailure = terminalFailure,
                cancelObservedBeforeTerminal = cancelObserved,
                droppedEvents = droppedEvents,
                unmatchedExchangeEvents = unmatchedExchangeEvents,
                tlsEvents = tlsEvents.toList(),
                decisions = decisions.toList(),
                cacheEvents = cacheEvents.toList(),
                connections = connections.toList(),
                dns = dns.map(DnsSpan::copy),
                routes = routes.map(RouteAttempt::copy),
                exchanges = exchanges.map(HttpExchange::copy),
            )
        }
        try {
            sink.enqueue(snapshot)
        } catch (_: Exception) {
            // sink 的普通异常不能穿透到 OkHttp 回调。
        }
    }
}
```

这份实现只在 `requestHeadersStart` 新建 exchange；建连前的 retry 与纯缓存命中的 follow-up 决定单独存入 `decisions`，exchange 列表因此只含真实发生过的网络请求。DNS 和 route 使用当前 call 内的原始参数配对，脱敏值只作为展示维度；原始键不进入快照，并在终止时清除。TLS 回调独立保留，免得被附会到“最近一个 route”上；`connectionAcquired` 保存实际 connection 的 route 与 protocol。确需区分新建与复用时，再补充连接对象生命周期证据。

<!-- gracker-diagram: ch17-08-07-collector-state -->
![有界采集与终止快照](../../assets/diagrams/ch17/ch17-08-07-collector-state.png)

图：只有 wire headers start 创建 exchange，决策与缓存事件单独保存。 TLS 无地址参数，连接取得也不足以证明最近一次新建连接被采用。

状态修改使用 per-call 私有锁，锁内不做 I/O、不打日志、不调 sink。普通事件共用 512 次预算，耗尽后冻结这些字段、累加 `droppedEvents`，终止快照仍可生成；任何统计必须先检查截断标记。`cancelObservedBeforeTerminal` 只表示生成终止快照前观察到取消；晚到的取消不把成功改成失败。`copy()` / `toList()` 隔离 listener 状态，DTO 仍有可变字段，sink 必须遵守入队后不修改的约定。

<!-- gracker-diagram: ch17-08-09-budget-snapshot -->
![截断、取消与快照的生命周期](../../assets/diagrams/ch17/ch17-08-09-budget-snapshot.png)

图：普通事件共享有限预算，耗尽后冻结字段，终止仍生成一次快照。 丢弃计数影响统计可信度；已入队 DTO 按约定不再修改。

`NetworkDimensions` 的方法必须有明确时间上限、无 I/O 与外部副作用；示例把普通异常转为 `unknown`，只挡住了异常返回，耗时预算仍要单独设定。host 采用允许清单，address/proxy 输出合规前缀或有密钥的摘要；这些可能碰撞的维度只作展示，原始配对仍要用回调参数。`NetworkMetricSink.enqueue()` 必须使用有界、非阻塞队列，满时丢弃并计数；示例接口本身不实现队列。


注册必须使用 `eventListenerFactory(...)`：

```kotlin
val client = OkHttpClient.Builder()
    .eventListenerFactory(
        NetworkMetricEventListenerFactory(
            sink = metricSink,
            dimensions = networkDimensions,
        )
    )
    .build()

// 在 newCall 前创建 tag，factory 与应用拦截器才能读取同一标识。
val request = Request.Builder()
    .url("https://example.com/status")
    .tag(NetworkRequestId::class.java, NetworkRequestId(UUID.randomUUID().toString()))
    .build()
val call = client.newCall(request)
```

这样每个 `Call` 都有独立状态；`eventListener(listener)` 会在多个并发调用间复用同一个实例，只适合没有 per-call 可变字段的监听器。

<!-- gracker-diagram: ch17-08-10-request-id-order -->
![Factory 读取 Request tag 的时机](../../assets/diagrams/ch17/ch17-08-10-request-id-order.png)

图：先设置 tag，再 newCall 创建 listener，执行时拦截器读取同一标识。 拦截器临时生成的 tag，到不了已创建的 factory 状态。

### 2.3 Interceptor 只做它能证明的事

应用拦截器适合建立 request sample 外壳：

- 从业务路由注册表取得 low-cardinality route name，也就是取值数量有限、不会把每个动态 URL 都变成新维度的路由名。
- 读取在 `newCall()` 前设置的 request id；只有服务端需要时才放入 header。若由应用拦截器生成新的子请求标识，应另存其来源，并注明 factory 读不到它。
- 记录最终响应码、`priorResponse` 链、缓存语义和业务错误码。
- 记录已知的 request/response content length；未知长度保留 `null`。

网络拦截器适合观察每个 wire exchange，拿它读 body 来“顺便采样”则行不通：one-shot（只能发送一次）、duplex 和流式 body 可能没法原样重放，提前 `string()` 或复制整个 buffer 还会改变内存、时序和 backpressure（下游读取速度反过来限制上游发送的机制）。

我们确需统计字节时，用 forwarding sink/source（转发数据的同时计数的包装器） 在转发途中计数；内容采集仍按第 7 节的允许清单执行。`responseBodyEnd(byteCount)` 在本文版本的 `Exchange.ResponseBodySource` 计数，位于 `BridgeInterceptor` 的透明 gzip 解压之前，也受缓冲预读影响；这个数对不上精确的业务已消费字节数，也对不上 IP/TLS 链路总字节数。提前 close 时读到的可能是部分，也可能是全部，样本里照实记录。示例将它命名为 `responseBodyBytesObserved`；业务解压后消费量需要在对应上层另外计数。

<!-- gracker-diagram: ch17-08-11-body-byte-boundary -->
![Gzip、缓冲与应用消费的计数边界](../../assets/diagrams/ch17/ch17-08-11-body-byte-boundary.png)

图：内部 body source 计数在透明 gzip 解压之前，缓冲预读又早于业务逐字节消费。 回调字节对不上 IP/TLS 总字节，也对不上业务已消费量；不要提前读取 body 采样。

## 3. 指标模型：先定义计时边界，再计算差值

事件采上来之后，还要变成能比较的指标。这一节我们先把每条记录的字段与计时位置定义清楚，再计算差值——计时位置定错，差值就会跟着错。

### 3.1 call、DNS、route 与 exchange 字段

| 记录 | 关键字段 | 说明 |
| --- | --- | --- |
| `call` | `call_id`、route、method、start/end、terminal error、cache events | 生命周期受 body 读取或关闭影响；不是业务处理完成标记 |
| `dns_span` | host pattern、start/end、address count | 自定义 DNS、缓存或重定向可能产生不同序列 |
| `route_attempt` | 脱敏地址、proxy、connect 时间与 failure | 原始键短暂配对；TLS 单列，禁止根据数组末项归属 |
| `exchange` | wire route、request/response 时间、status、protocol、failure、follow-up | 重定向和鉴权 response 也要保留 |

`attempt_count` 这个名字过于含糊，我们把它拆成 `route_attempt_count`、`exchange_count`、`retry_decision_count` 和 `follow_up_count`。连接复用的请求可以有 exchange，却没有 route attempt；一次 DNS 结果也可能对应多个地址尝试。

`network_type` 同样要按会变化的量来存。蜂窝与 Wi‑Fi 切换、VPN 或 QUIC connection migration（地址或网络改变后继续沿用连接）都可能发生在一次请求期间。至少记录 call 开始和结束时的 network handle/type（Android 网络对象标识与网络类型）；能监听默认网络变化时，再追加 transition（切换事件） 事件。VPN 下看不到底层网络，就写 `unknown`，别靠猜。


### 3.2 OkHttp 阶段差值

TTFB（Time to First Byte）要的是“首字节到达”这个时刻，而 `EventListener` 的响应回调给的是另一个时刻：在 OkHttp 5.3.0 与 5.4.0 的 `CallServerInterceptor` 中，`responseHeadersStart` 在一次 `readResponseHeaders()` 返回后触发，此时 HTTP/1.1 已读完状态行和一个 header block。这次回调对应的可能是 `100 Continue`、`103 Early Hints` 或最终响应，字段命名要体现这一点，直接叫“最终响应 TTFB（Time to First Byte，首字节时间）”会出错。

下表保留回调能证明的区间。`responseHeadersStart` 与 `responseHeadersEnd` 均指采集器收到回调的时刻：

| 指标 | 算法 | 正确解释 |
| --- | --- | --- |
| DNS | `dnsEnd - dnsStart` | 客户端 DNS 实现的阻塞区间；可能来自缓存或自定义 DNS |
| Transport connect | `connectEnd - connectStart` | Socket 建立到协议可用的总区间；HTTPS 下包含 TLS |
| Pre-TLS transport | `secureConnectStart - connectStart` | 直连时接近 TCP connect；有 HTTP proxy 时还可能包含隧道协商 |
| TLS | `secureConnectEnd - secureConnectStart` | TLS 握手区间 |
| Request headers | `requestHeadersEnd - requestHeadersStart` | 客户端写 request header 的区间；数据仍可能在缓冲区中 |
| Request body | `requestBodyEnd - requestBodyStart` | 客户端写 body 的区间；没有 body 时为空 |
| Exchange response-header wait | `responseHeadersStart - requestHeadersStart` | 从开始写 request 到首次 header block 可用回调；包含发送、等待与该 block 的读取处理 |
| Post-write response wait estimate | `responseHeadersStart - sendEnd` | 请求写入结束回调到首次 header block 可用回调；不保证请求已经发上网络 |
| Header callback interval | `responseHeadersEnd - responseHeadersStart` | 从首次 header block 可用到最终响应 header 回调；可能包含等待后续响应的时间 |
| Body callback interval | `responseBodyEnd - responseBodyStart` | 内部 source 的回调窗口；正常读取时 start 在首个 read 返回后触发，零长度或未读关闭也可补发 start；缓冲与读取间隔会影响它 |

只有 TLS 事件可唯一配对且能证明属于同一 route 时，才计算或组合相关差值；本文采集器保留原始 TLS 事件，不自动完成这种归属。失败或歧义区间保持 `null` 与原因。

HTTPS 下 `connectEnd` 发生在 `secureConnectEnd` 之后，`connectStart → connectEnd` 已经含了 TLS，再当 TCP 握手用、再与 TLS 相加都会算错。直连 HTTPS 时，我们可把 `connectStart → secureConnectStart` 当作 TCP 近似；经过 HTTP proxy 时，这段还混着 CONNECT 隧道协商——代理先为客户端和 HTTPS 目标建立字节通道——所以只能叫 pre-TLS transport。

<!-- gracker-diagram: ch17-08-13-connect-tls-overlap -->
![Transport connect 已包含 TLS](../../assets/diagrams/ch17/ch17-08-13-connect-tls-overlap.png)

图：同一条 HTTPS route 的 transport 总区间包含 TLS，代理隧道还会影响 pre-TLS。 仅在事件可唯一配对且确属同一路由时计算；connect 与 TLS 别重复相加。

`sendEnd` 有 body 时取 `requestBodyEnd`，无 body 时取 `requestHeadersEnd`。post-write response wait estimate 要满足三个条件：

- 已核对依赖版本的回调实现；本文的计时位置对应 5.3.0 与 5.4.0，4.3 以前的过早触发行为要另行核对。
- `sendEnd` 存在，且 `responseHeadersStart >= sendEnd`。
- request 不是 duplex，也没有 `Expect: 100-continue` 导致的事件交错。

条件不满足时，`post_write_response_wait_ms` 记 `null` 并写明缺失或交错原因；把负数取绝对值或强行归零，都会掩盖协议行为。条件满足时，我们拿到的也只是上述回调差值，把它当精确的“发完请求到响应首字节”还缺依据。


同一 exchange 可能先收到 `100 Continue` 或 `103 Early Hints`。这两个版本在内部跳过 `100` 和 `102..199` 后，才用最终响应调用一次 `responseHeadersEnd`；`101 Switching Protocols` 则保留为协议升级响应。所以示例里 `responseHeadersEnd` 只计数最终响应，`responseHeadersStart` 也不重标为最终响应起点。仅靠这些公开回调，临时响应数量与最终响应首字节时间都应留空；需要逐个 header block 时，要增加能观察该阶段的客户端探针并验证其版本行为。


“Server Wait”这个名称也罩不住这些端侧差值：写入、缓冲、网络 RTT（往返时延）、服务端排队与执行和 header 处理都可能包含其中。要拆出后端耗时，就要借助服务端自报的 `Server-Timing`（服务端通过响应 header 报告的耗时）、记录跨服务调用轨迹的分布式 trace，或服务端日志，并校验时钟与 request id。

排查回调触发位置时，可以用受控 HTTP/1.1 服务先发状态行和部分 header，暂不发结束空行；再测试完整 `103` 后延迟最终 `200`。前者能检查 `responseHeadersStart` 是否等待完整 header block，后者能检查 start 与 end 是否对应不同的响应。不要用只有单个 `200`、一次性写完 header 的样例验证 TTFB 语义。

body 回调还要单独按内部 source 解释：正常读取时，首个 `read()` 返回后才触发 start；零长度或未读即关闭也可能补发 start。内部预读完成可以早于上层缓冲消费与业务处理结束。第 2.3 节所述 gzip 解压前计数、这里的回调时间窗与业务处理终点，需要分别命名，一个“下载完成”字段盖不住三者。

<!-- gracker-diagram: ch17-08-16-body-window -->
![Body 完成与业务处理完成是两个边界](../../assets/diagrams/ch17/ch17-08-16-body-window.png)

图：内部回调、上层消费与业务处理有不同完成边界。 正常读取时 start 在首个阻塞 read 返回后触发；零长度或未读关闭也可补发 start，回调差值算不上完整下载时间。

### 3.3 空字段也是结论

| 现象 | 常见解释 | 存储方式 |
| --- | --- | --- |
| 没有 DNS/connect/TLS | 连接池复用、缓存命中，或请求尚未走到该阶段 | `null`，另存 reuse/cache 状态 |
| 一个连接服务多个 call | HTTP/2 或 HTTP/3 多路复用 | socket 指标保留连接维度，禁止复制到每个请求后求和 |
| body 回调区间很长 | 读取间隔、网络等待、流式处理或 backpressure | 保留内部回调窗口和对应计数字节，不能直接命名下载时间 |
| `callEnd` 很晚或早于业务处理结束 | 内部 body 完成或关闭影响调用结束；缓冲可先读完数据 | 与 headers、业务消费完成和处理完成分别记录 |
| DNS 为 0 ms | 客户端或系统缓存快速返回 | 保留 0；不要改为空 |


持续流、WebSocket upgrade（把 HTTP 连接升级为 WebSocket） 和 duplex RPC（请求与响应可同时传输的远程调用）是另一类：一次性 HTTP 下载模型套不上它们，应改用 stream 生命周期、首消息、消息间隔、backpressure 和关闭原因这类字段。

## 4. 弱网、重试与 follow-up 的识别

弱网分析的要领是保留失败路径，并把重复事件区分开来，别都叫重试：

- 多次 `connectStart` 表示多个 route attempt，可能来自地址回退，也可能来自 fast fallback（类似 Happy Eyeballs，错开启动且可能重叠的连接竞速）。
- `connectFailed` 只说明该 route 失败；只要还有 route，整个 `Call` 可以继续。
- `retryDecision(retry = true)` 是 OkHttp 5.3 及 5.4 连接故障恢复决定的直接依据。
- `followUpDecision(nextRequest != null)` 表示即将处理重定向、401/407 鉴权、408 或 503 等 follow-up。
- 多次 `requestHeadersStart` 表示多个 wire exchange，原因还要结合 retry/follow-up 决定和中间状态码。
- `requestFailed` 与 `responseFailed` 都可能被恢复，见到它们时先别把 call 标成失败。

同一域名的 IPv6 与 IPv4 地址可能被依次尝试，fast fallback（错开启动多条候选连接的竞速策略） 还可能让连接尝试重叠。route 配对要用 address、port、proxy 和事件参数去对，靠数组末项猜会配错；已有 API 定不下唯一配对时，上传原始顺序、`pairing_confidence = low（配对可信度低）` 和有限字段即可。


看板至少分开展示：

- `call_total_ms`：用户看到的整次调用生命周期。
- `route_failure_overhead_ms`：失败 route 覆盖的时间并集。并发 attempt 的时间有重叠，直接相加会重复计时。
- 每个 exchange 的 response-header wait 与 post-write response wait estimate。
- `final_exchange_header_wait_ms`：最终应用响应对应的 exchange 的 header 回调等待值；仍不表示该响应的精确首字节时间。
- `redirect_or_auth_overhead_ms`：follow-up 前的中间 exchange 时间。

“只取最终 attempt 的 server wait”会丢掉连接复用、重定向和请求写入后重试等情况。最终 response 属于 exchange；route attempt 可能早已结束，当前 call 也可能没有发生建连。定位原因时，要用同一层级的事件。


排查时我们按下面的顺序找线索：

- DNS span 超时或失败，且后续 route 未开始：先看解析器、DoH（DNS over HTTPS，通过 HTTPS 发送 DNS 查询）/系统 DNS 和网络切换。
- route attempt 失败、IP 或 proxy 切换：看地址可达性、TCP/代理/TLS 错误。
- post-write response wait estimate 高：先核对 header block 与缓冲语义，再结合 RTT 与服务端 trace 判断等待来自哪里。
- body 回调区间长：结合具体计数层、吞吐、上层读取间隔和下行丢包判断；需要完整下载区间时另取明确边界。


## 5. `HttpURLConnection` 与三方 SDK：在调用点插桩

`java.net.URL` 与 `HttpURLConnection` 的 API 定义在 libcore（Android 的 Java 核心库实现）里，又在 boot classpath（系统启动时加载的核心 class 路径） 上，应用改不动它。我们让构建插件改写应用或依赖的 class 字节码，把这些 API 的调用导向采集桥接层。

AGP 8.0 已移除旧 Transform API。本轮核对的 AGP 官方 API 与迁移路线仍通过 `androidComponents` 下的 Instrumentation API 与 `AsmClassVisitorFactory` 修改或检查字节码。下面的代码按每个 build variant（构建变体，例如 debug 或 release） 注册 ASM visitor：

```kotlin
androidComponents {
    onVariants(selector().all()) { variant ->
        variant.instrumentation.transformClassesWith(
            UrlConnectionVisitorFactory::class.java,
            InstrumentationScope.PROJECT,
        ) { params ->
            params.includePrefixes.set(listOf("com.example."))
        }
        variant.instrumentation.setAsmFramesComputationMode(
            FramesComputationMode.COMPUTE_FRAMES_FOR_INSTRUMENTED_METHODS,
        )
    }
}
```

ASM visitor 会逐条访问 class 中的方法指令；AGP 随后为受影响方法重算 stack map frame（JVM 验证字节码时使用的栈与局部变量类型信息）。默认用 `PROJECT`，只处理当前项目的 class。官方 API 限定库模块只能插桩本地项目类；应用与测试模块才可选择 `ALL`，把依赖类纳入范围。启用 `ALL` 时，通过 `isInstrumentable()` 的精确包名前缀排除 APM runtime（采集器运行时代码）、生成代码和不兼容依赖。


下面的 visitor 把实例调用替换成静态桥接调用。`URL` receiver（实例方法的接收对象） 原本在 operand stack（执行字节码时暂存操作数的栈） 上，替换后成为静态方法的第一个参数，因此无需额外插入 `DUP` 或局部变量。

```kotlin
private val replacements = mapOf(
    "openConnection()Ljava/net/URLConnection;" to
        Hook("openConnection", "(Ljava/net/URL;)Ljava/net/URLConnection;"),
    "openConnection(Ljava/net/Proxy;)Ljava/net/URLConnection;" to
        Hook(
            "openConnection",
            "(Ljava/net/URL;Ljava/net/Proxy;)Ljava/net/URLConnection;",
        ),
    "openStream()Ljava/io/InputStream;" to
        Hook("openStream", "(Ljava/net/URL;)Ljava/io/InputStream;"),
)

override fun visitMethodInsn(
    opcode: Int,
    owner: String,
    name: String,
    descriptor: String,
    isInterface: Boolean,
) {
    val hook = if (opcode == Opcodes.INVOKEVIRTUAL && owner == "java/net/URL") {
        replacements[name + descriptor]
    } else {
        null
    }

    if (hook != null) {
        super.visitMethodInsn(
            Opcodes.INVOKESTATIC,
            "com/example/apm/ApmUrlHook",
            hook.name,
            hook.descriptor,
            false,
        )
    } else {
        super.visitMethodInsn(opcode, owner, name, descriptor, isInterface)
    }
}
```

三个 method descriptor（编码参数与返回类型的方法签名） 必须分别匹配；只 Hook（拦截并转到自定义实现） 无参 `openConnection()` 会漏掉代理重载和 `openStream()`。`ApmUrlHook` 所在包必须从插桩范围排除，否则桥接方法再次调用 `URL.openConnection()` 会递归。

<!-- gracker-diagram: ch17-08-22-receiver-stack -->
![实例 Receiver 变成静态首参数](../../assets/diagrams/ch17/ch17-08-22-receiver-stack.png)

图：把 URL 实例调用重写为带 URL 首参数的静态桥接调用，保持栈中参数顺序。 无参、Proxy 重载和 openStream 分别匹配；桥接包必须排除以防递归。

桥接层可包装 `URLConnection`、input stream 与 output stream，记录公开 API 能证明的时刻和字节数。`connect()` 返回并不等价于“纯 TCP 完成”，`getInputStream()` 又可能同时触发建连、写请求和读 response header。`HttpURLConnection` 没有 OkHttp 那样的 DNS/TLS 回调，几个 Java 方法的时间点拼不出完整的协议阶段；需要 DNS、TLS 或重试细节时，只能结合实现可用的回调、受控 Native 观测或服务端 trace。


依赖 class 能否被 `InstrumentationScope.ALL` 处理，还受打包形式、动态加载、混淆和插件版本影响。构建时要输出“扫描 class 数、命中调用点数、排除原因”，再用 fixture（固定输入的测试样例）覆盖 AAR/JAR（Android/Java 依赖包格式）、Proxy 重载、异常和 R8（Android 代码压缩与优化工具） 构建。

## 6. Cronet、PLT Hook 与 eBPF 的能力边界

OkHttp 和 `HttpURLConnection` 之外，请求还可能走 Cronet、Native 库或系统层。这三类入口的取数手段各不相同：官方 metrics、PLT/GOT Hook 与 eBPF 各覆盖一段，能力范围也各有前提。

### 6.1 Cronet 优先使用官方 metrics

Cronet 支持 HTTP/1.1、HTTP/2 和 HTTP/3 over QUIC。请求完成后，`RequestFinishedInfo.Metrics` 可提供 DNS、connect、SSL、sending、response start、request end、socket reuse、transport 字节数，以及直接计算的 TTFB 与总耗时，我们优先从这里取数。通过 `UrlRequest.Builder.addRequestAnnotation()` 放入不含敏感信息的 request id，再从 `getAnnotations()` 取回，可以避免按 URL 和时间窗口猜测关联关系。

Cronet 的字段也要按文档解释：

- `connectEnd` 位于 TCP 与 SSL 完成之后；QUIC 0-RTT 下，它甚至可能晚于 `sendingStart`。
- QUIC 的 `sslStart/sslEnd` 与 `connectStart/connectEnd` 指同一段时间，分别记录即可，相加会重复计时。
- socket reuse 为 true 时，DNS、connect 与 SSL 时间为空。
- metrics 不可用或请求未走到该阶段时，时间为 `null`。
- `getTtfbMs()` 表示从请求发起到响应 header 首字节的毫秒数；`getTotalTimeMs()` 包括成功、失败或取消前的完整请求时间。Cronet provider（实际提供实现的组件） 没有采集时，两者都可能为 `null`。
- `getResponseStart()` 是最终 response headers 收完的时刻，应与 Cronet 自己的 `getTtfbMs()` 区分。OkHttp 的 header 回调又受第 3.2 节所述触发位置的限制，名称相近的字段要先核对采样点再对齐；直接 TTFB 字段为空时，用 header 收完时间算出的值要另起字段名。
- `getMetrics()` 的总说明称时间和字节覆盖全部 redirect，但 `getReceivedByteCount()` 的字段说明又明确排除先前 redirect，源码也保留了返回完整 metrics 链的 TODO。redirect 字节数是否累计，以实际 Cronet provider/version 的 contract test（用固定输入验证字段行为的契约测试） 结果为准，先测再定。
- 单个 `Metrics` 精确还原不了每一跳；每个 redirect 要结合 `onRedirectReceived()` 另存语义事件。

Cronet 的 Google Play services 实现、作为后备的 fallback 与独立发布的 Chromium artifact（发布的依赖包） 之间可能存在 API 或实现差异。统一 schema（结构化数据的字段结构） 要保留 `metric_source = okhttp | cronet`、provider/version 与 `timestamp_semantics`（时间戳代表的事件边界）。上线前用编译依赖对应的 API 和真机契约测试核对空字段、redirect 与字节计算规则；字段名相同，采样点未必相同，跨客户端汇总前先统一定义。

<!-- gracker-diagram: ch17-08-24-cronet-metrics -->
![Cronet 首字节字段与 Header 完成](../../assets/diagrams/ch17/ch17-08-24-cronet-metrics.png)

图：Cronet 保留自身 provider、版本与时间语义，再映射到共有字段。 TTFB 与 responseStart 边界不同，redirect 字节契约需在实际 provider 上验证。

### 6.2 PLT/GOT Hook 的覆盖范围

PLT（Procedure Linkage Table）和 GOT（Global Offset Table）是 ELF（Android Native 二进制格式） 动态链接过程中定位外部函数的表。我们修改这些入口，把部分函数调用转交给采集代码；它只对确实经过动态符号入口的调用生效。

Native 兜底常见目标包括：

- `getaddrinfo`：观察 libc 中的域名解析调用区间、返回码和结果数量。
- `connect`：观察目标地址、耗时、返回值与 `errno`（线程局部保存的系统调用错误码）。
- `send` / `recv`：观察 socket 调用的字节数和错误；HTTPS 下通常是 TLS record 或其他密文。
- `SSL_write` / `SSL_read`：动态 TLS 库导出且经 PLT/GOT 调用时，可观察输入或输出的明文字节数与 TLS 错误。

设计时要把三条限制写清楚：

1. `SSL_write` 的输入长度对应不上链路发送字节：TLS record 分帧、缓冲和重试都会改变数量；`SSL_read` 的输出也可能混着 HTTP/2 frame（协议帧） 等数据，未必就是业务 body。
2. `send/recv` 看不到 TCP 重传：重传发生在内核 TCP 栈，用户态 QUIC 的重传又属于协议库。socket 调用失败和“发生重传”是两回事。
3. Cronet 常把 BoringSSL（Chromium 使用的 TLS 实现）与网络栈静态链接，Mars 或自研库也可能隐藏符号、内联调用或直接执行 syscall（系统调用）。这时 PLT Hook 对 `SSL_*` 或 libc wrapper（封装函数） 的覆盖率可能很低。


Bionic（Android 的 C 标准库）的 `socket()` 仍通过 `NetdClientDispatch` 分派，dynamic linker（动态链接器） 负责 ELF 装载与符号解析。这个源码事实只说明存在潜在调用路径，离“所有网络请求都能 Hook 到”还差得远。Hook 实现还要处理线程局部的递归调用保护、原始函数解析、`errno` 保存恢复、fork（从当前进程创建子进程） 与动态加载、ABI（Application Binary Interface，应用二进制接口） 和 16 KiB page size（内存页大小） 兼容，并在故障时自动关闭采集。

<!-- gracker-diagram: ch17-08-26-hook-guard -->
![Native 代理的故障隔离](../../assets/diagrams/ch17/ch17-08-26-hook-guard.png)

图：Native 代理需要递归保护、原函数调用与错误状态保护，并在异常时关闭采集。 源码里存在分派路径，还证明不了全覆盖；ABI 与16KiB页兼容需在目标产物和设备验证。

只要网络库提供稳定回调，就优先接回调；PLT Hook 更适合当作覆盖范围已验证、先向少量设备开放并随时可撤回的后备观测，补回调盖不到的部分。

### 6.3 eBPF 适用于系统或受控设备

eBPF（extended Berkeley Packet Filter）允许受验证的小程序在内核事件上运行。`platform/system/bpf` 仍由系统 loader（加载器） 管理 BPF 程序，量产三方应用通常拿不到加载、pin（在 BPF 文件系统中保留对象引用） 并 attach（绑定到事件） BPF 程序所需的 Linux capability（细分的特权权限）、SELinux（Android 强制访问控制机制） 安全域与文件访问权限。我们能用的场景主要是：

- ROM（设备系统镜像） 或系统组件。
- 具有所需系统特权的企业专管设备或设备代理；设备管理权限或用户授权本身不授予 BPF 加载权限。
- root（取得系统最高权限）/工程机上的诊断工具。
- CI（持续集成） 实验室或线下复现环境。


在这些环境中，先按实际设备的内核、配置和可用探针核对支持范围：本文以 `android17-6.18-2026-06_r6` 为源码锚点，它只代表这一条内核线，设备实际运行的内核未必是 6.18。可借 BPF、tracepoint（内核跟踪点）或 socket 统计观察 UID 流量、TCP RTT、重传和连接错误。但它看到的仍是密文与字节数：URL、header、HTTP/2 stream 或 QUIC stream 都恢复不出来，UID 字节数也没法直接摊到单个业务请求上。

内核 TCP 重传指标盖不住用户态 QUIC 的协议重传。分析 HTTP/3 时，优先用 Cronet/QUIC 栈暴露的 NetLog（Chromium 网络事件日志）或 metrics，再拿内核 UDP/socket 事件补连接级的线索。

<!-- gracker-diagram: ch17-08-28-tcp-quic-boundary -->
![内核 TCP 与用户态 QUIC 的边界](../../assets/diagrams/ch17/ch17-08-28-tcp-quic-boundary.png)

图：TCP 重传来自内核 TCP 栈，QUIC 协议重传要由用户态协议库提供。 加密和多路复用下，UID/socket 字节没法直接恢复或均摊单个 HTTP 请求。

## 7. 隐私与安全：原始数据不要进入样本

网络采集会碰到账号、token（登录或访问凭证）、设备标识、位置、订单与业务内容。我们要在生成内存样本之前就完成安全控制；服务端脱敏兜底的，已经是端侧泄露之后的数据。

### 7.1 URL 与 route

- 先用业务路由注册表匹配，再写入样本；禁止先保存 raw URL 后异步清洗。
- `/user/12345/order/888` 可归一为 `/user/:userId/order/:orderId`。
- 未命中的 path 只上报允许的 host 与 path 段数等有限信息；已有受控模板才可记录模板 hash，不对未知原始 path 直接做摘要后上报。
- Query（URL 中 `?` 后的参数），value 默认全部丢弃；key 也可能带业务含义，只保留允许清单中的名称。
- Fragment（URL 中 `#` 后的片段） 本就不发给 HTTP 服务端，APM 也不采集。


### 7.2 Header

- 默认允许清单可包含 `content-type`、受控的 `content-length` 与专用 trace id。
- `authorization`、`proxy-authorization`、`cookie`、`set-cookie`、设备 id、用户 id 和位置字段直接丢弃。
- trace id 也能跨事件关联用户，应设置用途、保留期和访问权限。
- 不通过中间人证书或绕过 certificate pinning（证书锁定）来获取内容；APM 要维持原有的传输安全。

### 7.3 Body 与文件

任意文本 body 的“前 N 字节”并不安全，token 和手机号常出现在开头。默认策略是不采内容，只记录经过校验的长度、MIME（内容类型标识） 和编码。业务确有诊断需求时，走下面的流程：

1. endpoint 与 schema 同时命中允许清单。
2. 在结构化对象阶段按字段名删除或替换敏感值。
3. 对脱敏结果设置很小的字节上限。
4. 经过采样、用户授权、保留期和访问审计后再上报。

满足这些条件后才可以截取 body。对未知文本、二进制、multipart（一个 body 中容纳多个部分的格式） 和文件上传，只记录类型、长度区间和成功/失败；文件名与本地路径留在样本之外。


### 7.4 标识符与删除

普通 hash 只是可关联的假名：手机号或邮箱的可能取值有限，攻击者仍可枚举原文并比对结果。优先不采用户标识；确需关联时，改用服务端管理、定期轮换的 HMAC key（计算带密钥摘要所用的密钥），并把用途限制在约定窗口内。request sample 与身份映射放进相互隔离的存储系统，支持按用户删除、到期清理、按法规要求限定数据存储地区和权限审计。


## 8. 开销控制与自监控

EventListener 回调在请求的关键路径上，我们要给采集器定性能预算——每次回调允许占用的时间、内存和流量上限——超出时能自动减量或关闭：

- 回调只读取时间、枚举和计数，写入固定大小结构或有界 ring buffer（写满后按既定策略处理的环形缓冲区）。
- `System.nanoTime()` 只在同一进程内算时长，持久化后拿去和 wall clock（表示日期时间的系统时钟） 比较会出错。
- URL 归一化要避免正则表达式出现灾难性回溯，也要避免复制大字符串；规则在后台预编译。
- 不在回调中序列化 JSON、写文件、查数据库、打印日志或发请求。
- body 内容默认关闭；字节计数用 forwarding source/sink，不复制整包。
- 采样按 route 和 request id 做确定性决策，使同一标识总是得到相同的采样结果，避免同一问题的前后事件随机断裂。
- 大量故障同时出现时，要设置每分钟上限、按 route 或错误类型分组的 reservoir sampling（蓄水池采样）和丢弃计数，防止错误期进一步推高 CPU、磁盘和上报流量。
- 采集队列满时丢弃 APM 样本，不阻塞业务请求；上报端排除自己的网络请求，避免递归采集。

对象池不一定比小型 DTO（Data Transfer Object，只承载字段的数据对象） 更省：池本身会带来锁、生命周期和残留数据风险，先用基准测试证明对象分配真是瓶颈再上池。采集器至少自报 callback p50/p95/p99（第 50、95、99 百分位回调耗时），以及分配量、队列深度、丢弃率和上报字节。超出预算时依次停 body 采集、降成功样本率、再降失败样本率，让诊断价值更高的失败样本留得更久。


## 9. HTTP/3 / QUIC 的字段要显式区分

QUIC 基于 UDP，传输握手与 TLS 1.3 紧密结合，支持连接复用、0-RTT 和连接迁移——0-RTT 指恢复既有连接时不等完整往返就先发送早期数据。把 TCP 字段原样搬过来填 0，等于把“不适用”伪装成“瞬间完成”。

我们的做法是保留协议无关的上层字段，同时补充传输语义：

| 字段 | TCP + TLS | QUIC |
| --- | --- | --- |
| `transport` | `tcp` | `quic` |
| `transport_connect_ms` | TCP、代理和 TLS 到协议可用的总区间 | QUIC 库定义的 handshake/confirmation（握手与确认）区间 |
| `tcp_connect_estimate_ms` | 有条件计算 | `null` / not applicable |
| `tls_ms` | 独立 TLS 区间 | 与 QUIC connect 重叠，禁止重复相加 |
| `connection_reused` | 连接池复用 | QUIC connection/stream 复用 |
| `migration_count` | 通常为 0 | 由 QUIC 栈提供；没有证据时为空 |
| `retransmission_source` | 内核 TCP | QUIC 库；内核 UDP 无法给出同等语义 |

0-RTT 下请求发送可能早于握手确认，各阶段也就不再严格按“前一个结束、下一个才开始”的顺序发生。`connectEnd - connectStart` 仍可作为库定义的 transport 区间，只是别强行把它放到 sending 之前。跨 HTTP/2 与 HTTP/3 比较时，优先看定义一致的请求耗时、成功率和吞吐，再按 transport 分组看连接指标。TTFB 只在有首字节观测依据时比较，OkHttp 的 header 回调差值单列。


## 10. 一套可维护的接入顺序

工程接入上，我们按覆盖率与风险逐步推进：

1. 在统一 OkHttp client 上接应用拦截器、网络拦截器和 per-call `EventListener.Factory`。
2. 建立 call、DNS、route、exchange 四条时间线，先在线下验证缓存、连接复用、重定向、401、失败恢复、`Expect: 100-continue` 和 duplex。
3. 对仍在使用 `HttpURLConnection` 的自有代码启用 `InstrumentationScope.PROJECT`，用构建报告确认调用点覆盖。
4. 只对明确列出的少量三方 Java SDK 做 `ALL` 范围实验；Native SDK 优先接官方 callback。
5. Cronet 用 annotation（创建请求时附加、完成后原样取回的对象）关联 `RequestFinishedInfo`并保留其字段语义与 redirect 累计规则。
6. PLT Hook 与 eBPF 只在权限、覆盖率和回滚条件明确的环境启用；回滚指关闭采集并恢复到上一套已验证配置。
7. 端侧在样本生成前执行 route、header、body 和标识符规则，后台只接收已裁剪结构。
8. 用可控 DNS 延迟、代理故障、TLS 失败、限速/丢包和 HTTP/3 测试服务校验每个字段；事件证明不了的字段保留为空。

扩展到 WebView、gRPC（基于 RPC 与 HTTP/2 等协议的调用框架） 或自研 RPC 时，不必把它们伪装成 OkHttp：各客户端先保留原生事件，再映射到共有的 call、route 和 exchange 概念；对不齐的阶段用 `metric_source` 和 `timestamp_semantics` 明示差异。


## 11. 源码锚点与参考资料

### Android 17 / API 37

- [Android 17 `java.net.URL`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/net/URL.java)：核对 `openConnection()`、代理重载与 `openStream()` 的平台 API。
- [Android 17 `HttpURLConnection`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/net/HttpURLConnection.java)：核对公开生命周期与能力范围。
- [Android 17 Bionic `NetdClientDispatch.cpp`](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/libc/bionic/NetdClientDispatch.cpp)：核对 libc `socket/connect/send*` 到 `NetdClientDispatch` 的入口。
- [Android 17 Bionic linker](https://android.googlesource.com/platform/bionic/+/refs/tags/android-17.0.0_r1/linker/linker.cpp)：核对 Android 动态链接与符号解析实现。
- [Android 17 system BPF](https://android.googlesource.com/platform/system/bpf/+/refs/tags/android-17.0.0_r1/)：核对系统 BPF loader 与目录结构。
- [Android 17 Connectivity BPF](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/bpf/)：核对网络 BPF loader、netd 集成、program 与 syscall wrapper。

### Android 17 common kernel

- [`android17-6.18-2026-06_r6` BPF core](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/bpf/)：BPF syscall、map、program 与 verifier 的内核实现。
- [`android17-6.18-2026-06_r6` network BPF](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/bpf/)：网络 BPF 相关实现。
- [`android17-6.18-2026-06_r6` socket filter](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/core/filter.c)：socket filter 与 BPF helper 的关键实现。

### 客户端与构建工具

- [OkHttp 当前仓库](https://github.com/lysine-dev/okhttp)：核对当前维护位置；稳定发布再由 changelog 与 Maven Central 发布元数据交叉确认。
- [OkHttp 当前 Events 文档](https://lysine.dev/okhttp/features/events/)：核对事件模型与监听器使用方式；元数据中的 `square.github.io` 同名 URL 是迁移前旧址，现已返回 404，仅为保留历史来源。
- [OkHttp 当前 Interceptors 文档](https://lysine.dev/okhttp/features/interceptors/)：核对应用拦截器与网络拦截器的职责划分。
- [OkHttp 5.4.0 changelog](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/CHANGELOG.md)：核对 2026-06-08 版本及变更范围。
- [OkHttp 5.4.0 `EventListener` 源码](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)：核对当前回调签名与并发说明。
- [OkHttp 5.3.0 `CallServerInterceptor`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/CallServerInterceptor.kt) 与 [5.4.0 对应实现](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/CallServerInterceptor.kt)：核对 header 读取后触发 start、跳过临时响应后触发 end 的顺序。
- [OkHttp 5.3.0 `Http1ExchangeCodec`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http1/Http1ExchangeCodec.kt)：核对 `readResponseHeaders()` 读取完整状态行与 header block 的行为。
- [OkHttp 5.3.0 `EventListener` 源码](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)：本文示例使用的事件顺序、恢复与并发说明。
- [OkHttp 5.3.0 Interceptors](https://github.com/square/okhttp/blob/parent-5.3.0/docs/features/interceptors.md)：应用拦截器与网络拦截器的差异。
- [AGP Instrumentation API 迁移说明](https://developer.android.com/build/releases/gradle-plugin-api-updates)：核对 Transform 移除与 Instrumentation API 注册方式。
- [AGP 9.x/10.0 API 迁移路线](https://developer.android.com/build/releases/gradle-plugin-roadmap)：核对当前 Variant 与 Instrumentation API 方向。
- [AGP `InstrumentationScope`](https://developer.android.com/reference/tools/gradle-api/current/com/android/build/api/instrumentation/InstrumentationScope)：核对 `PROJECT` 与 `ALL` 的处理范围。
- [Cronet `RequestFinishedInfo.Metrics`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo.Metrics)：核对直接 TTFB、总耗时、阶段时间与字节字段。
- [Cronet `RequestFinishedInfo` 源码](https://chromium.googlesource.com/chromium/src/+/fe8f6a81fa141754b36db3e0bf47540a67c4c428/components/cronet/android/api/src/org/chromium/net/RequestFinishedInfo.java)：核对 metrics、redirect 累计、annotation 与空字段语义。
- [Cronet request lifecycle](https://developer.android.com/develop/connectivity/cronet/lifecycle)：核对 callback 状态转换与终止条件。

- [OkHttp 5.5.1 changelog](https://github.com/lysine-dev/okhttp/blob/parent-5.5.1/CHANGELOG.md) 与 [Maven Central 发布元数据](https://repo.maven.apache.org/maven2/com/squareup/okhttp3/okhttp-jvm/maven-metadata.xml)：核对本轮最新稳定发布与日期。
- [OkHttp 5.3.0 `Exchange`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/Exchange.kt) 与 [`BridgeInterceptor`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/BridgeInterceptor.kt)：核对 body 计数、预读、完成与透明 gzip 层次。
- [OkHttp 5.3.0 `RetryAndFollowUpInterceptor`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http/RetryAndFollowUpInterceptor.kt)、[`CacheInterceptor`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/cache/CacheInterceptor.kt) 与 [`FastFallbackExchangeFinder`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/FastFallbackExchangeFinder.kt)：核对决策不等于网络 exchange、条件缓存序列与并发 TCP 竞速。
