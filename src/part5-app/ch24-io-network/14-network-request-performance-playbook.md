---
title: "网络请求分段优化与弱网治理"
chapter: "24.14"
section: "24.14"
status: finalized
drafted_date: "2026-05-22"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-03"
task9_reviewed_date: "2026-07-03"
task9_reviewed_by: "openclaw-task9"
pipeline_stage: ready-to-publish
last_verified_against: "Android Developers Cronet / network access optimization docs 2026-05-22 + android-17.0.0_r1 (verified via git ls-remote; APIs cross-checked against android-17.0.0_r1 tag on googlesource) + OkHttp 5.x docs"
confidence: medium
tags: [network, latency, weak-network, cronet, okhttp, power]
related_chapters: ["24.4", "24.5", "24.10", "24.11", "26.17", "12.1", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "Clippings参考书/官方文档/章节深挖"
gap_score: 18
last_task2a_at: "2026-05-22T16:18:00+08:00"
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-22"
task6_result: pass-light-edit
task9_state: reviewed
last_task6_at: "2026-05-22T17:08:00+08:00"
last_task6_review_log: "logs/review/2026-05-22-17-review.md"
task6_l1_l2_fixes: 5
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-22 Task6：首次写作质检通过；补齐 outline，清理结构性元叙述、编辑标记和填充副词 5 处；无 L3/L4 回炉项，送 Task9 技术复核。"
task9_result: pass-tech-review
last_task9_at: "2026-07-03T19:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-07-02-20-audit.md"
last_task9_audit: "2026-07-02"
last_task6_audit: "2026-06-17"
task9_review_notes: "2026-07-02 Task9 闲时抽检：发现 P1 版本基准问题；章节适用范围到 Android 17/API 37，但源码证据仍锚定 Android 35 SDK。已写入 queue priority:85，回 Task2B 重锚 android-17.0.0_r1。2026-07-02 Task2B：所有源码引用已重锚 android-17.0.0_r1，tag 经 git ls-remote 验证存在；API 行为经跨版本确认一致。"
task2b_state: fixed
last_idle_audit_at: "2026-07-02T20:34:05+08:00"
task2b_result: fixed
task2b_fixed_at: "2026-07-02T21:08:00+08:00"
task2b_fix_summary: "Re-anchored all source references from Android 35 SDK to android-17.0.0_r1; verified tags exist on googlesource (platform/frameworks/base + NetworkStack); confirmed API consistency across versions"
sources:
  - type: clippings
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
  - type: clippings
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
  - type: clippings
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/integration"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/topic/performance/power/network/index.html"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/bg-network-usage"
  - type: official
    path: "https://square.github.io/okhttp/features/events/"
  - type: aosp
    path: "https://android.googlesource.com/platform/packages/modules/NetworkStack/+/refs/tags/android-17.0.0_r1/framework/src/android/net/http/HttpEngine.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/packages/modules/NetworkStack/+/refs/tags/android-17.0.0_r1/framework/src/android/net/http/QuicOptions.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/net/ConnectivityManager.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/net/TrafficStats.java"
  - type: local
    path: "src/part5-app/ch24-io-network/04-network-architecture.md"
  - type: local
    path: "src/part5-app/ch24-io-network/05-protocol-optimization.md"
  - type: local
    path: "src/part5-app/ch24-io-network/10-httpdns-okhttp-dns-boundary.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-07
---

# 24.14 网络请求分段优化与弱网治理

页面等待的是一次业务操作完成，网络库记录的却可能是若干次连接尝试、重定向和重试。只看请求总耗时，无法判断时间消耗在客户端排队、域名解析、服务端处理，还是响应解码。有效的治理方式是先建立分段时间线，再给每个场景分配总预算、重试预算和流量预算。

平台基准为 Android 17 / API 37 / `android-17.0.0_r1`，重点是普通 HTTP 请求的工程做法。连接池与超时见 24.4，协议与 QUIC 见 24.5，HTTPDNS 边界见 24.10，跨端线上观测见 26.17。

## 七段之前，还有排队和缓存判定

对普通、非双工的 HTTP 请求，可以把网络与内容处理拆成七段。请求进入这七段前，还可能停留在业务队列、OkHttp `Dispatcher` 或缓存判定中。首屏偶发慢而 DNS、连接、TLS 全部正常时，这两段很容易被漏掉。

| 位置 | 时间边界 | 常见原因 | 可执行动作 |
| --- | --- | --- | --- |
| 业务与调度队列 | 业务提交时间到网络执行开始 | 同一主机并发占满、低优先级请求挤占、线程执行器拥塞 | 区分前台与后台调度，记录队列长度和等待时间 |
| 缓存判定 | 执行开始到缓存命中，或进入网络阶段 | 缓存键错误、响应指令禁止缓存、条件请求 | 记录命中、条件命中和未命中，不把命中请求算作“零毫秒网络” |
| DNS | `dnsStart` 到 `dnsEnd` | 解析器慢、无可用地址、地址顺序不合适 | 后台刷新、系统 DNS 回退、按 `Network` 隔离结果 |
| connect | 每次 `connectStart` 到对应的成功或失败事件 | SYN 重传、某个地址不可达、代理连接慢 | 连接复用、OkHttp Fast Fallback、限制预连接 |
| TLS | `secureConnectStart` 到 `secureConnectEnd` | 证书验证失败、完整握手、服务端配置异常 | 修复证书链、减少无价值跨域、观察会话恢复 |
| request write | 请求头开始到请求体写完 | 上传体积大、发送窗口受限、写超时 | 分片、可恢复上传、限制后台大请求 |
| TTFB | 请求发送完成到响应头开始到达 | 上行传输、接入层排队、服务端处理、下行首字节传输 | 关联服务端追踪记录，分离网关与业务耗时 |
| response read | 响应体开始到读取结束 | 带宽不足、大响应、服务端发送慢 | 分页、断点续传、媒体自适应码率 |
| decode/render | 完整数据可用到界面完成消费 | JSON/Proto 或图片解码、主线程工作、布局绘制 | 后台解码、裁剪字段、按需渲染 |

TTFB 不是“读取响应头用了多久”。它覆盖请求发完以后，到客户端收到响应首部的等待。服务端指标正常而客户端 TTFB 偏高，仍可能是上行末尾、无线接入网、代理、下行首包或连接迁移造成的。流式上传、双工请求和长连接没有同一套时间边界，应单独定义事件。

### 用 OkHttp 事件记录事实，不急着在回调里算结论

下面的代码按 OkHttp 5.4.0 公开接口记录单调时钟上的事件点，作用是保留一次 `Call` 的原始顺序。阶段配对和聚合放到采集线程之外完成。

```kotlin
data class NetworkStageEvent(
    val callSequence: Long,
    val name: String,
    val elapsedNanos: Long,
    val byteCount: Long? = null,
)

class TimelineEventListener(
    private val callSequence: Long,
    private val emit: (NetworkStageEvent) -> Unit,
) : EventListener() {
    private val originNanos = SystemClock.elapsedRealtimeNanos()

    private fun mark(name: String, byteCount: Long? = null) {
        emit(
            NetworkStageEvent(
                callSequence = callSequence,
                name = name,
                elapsedNanos = SystemClock.elapsedRealtimeNanos() - originNanos,
                byteCount = byteCount,
            ),
        )
    }

    override fun callStart(call: Call) = mark("call_start")

    override fun dispatcherQueueStart(call: Call, dispatcher: Dispatcher) =
        mark("dispatcher_queue_start")

    override fun dispatcherQueueEnd(call: Call, dispatcher: Dispatcher) =
        mark("dispatcher_queue_end")

    override fun cacheHit(call: Call, response: Response) = mark("cache_hit")
    override fun cacheMiss(call: Call) = mark("cache_miss")

    override fun cacheConditionalHit(call: Call, cachedResponse: Response) =
        mark("cache_conditional_hit")

    override fun dnsStart(call: Call, domainName: String) = mark("dns_start")

    override fun dnsEnd(
        call: Call,
        domainName: String,
        inetAddressList: List<InetAddress>,
    ) = mark("dns_end")

    override fun connectStart(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
    ) = mark("connect_start")

    override fun secureConnectStart(call: Call) = mark("tls_start")

    override fun secureConnectEnd(call: Call, handshake: Handshake?) =
        mark("tls_end")

    override fun connectEnd(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
        protocol: Protocol?,
    ) = mark("connect_end")

    override fun connectFailed(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
        protocol: Protocol?,
        ioe: IOException,
    ) = mark("connect_failed")

    override fun connectionAcquired(call: Call, connection: Connection) =
        mark("connection_acquired")

    override fun connectionReleased(call: Call, connection: Connection) =
        mark("connection_released")

    override fun requestHeadersStart(call: Call) = mark("request_headers_start")

    override fun requestHeadersEnd(call: Call, request: Request) =
        mark("request_headers_end")

    override fun requestBodyStart(call: Call) = mark("request_body_start")

    override fun requestBodyEnd(call: Call, byteCount: Long) =
        mark("request_body_end", byteCount)

    override fun responseHeadersStart(call: Call) = mark("response_headers_start")
    override fun responseBodyStart(call: Call) = mark("response_body_start")

    override fun responseBodyEnd(call: Call, byteCount: Long) =
        mark("response_body_end", byteCount)

    override fun retryDecision(
        call: Call,
        exception: IOException,
        retry: Boolean,
    ) = mark(if (retry) "retry_accepted" else "retry_rejected")

    override fun canceled(call: Call) = mark("canceled")
    override fun callEnd(call: Call) = mark("call_end")
    override fun callFailed(call: Call, ioe: IOException) = mark("call_failed")
}

fun buildNetworkClient(
    eventSink: (NetworkStageEvent) -> Unit,
): OkHttpClient {
    val callSequence = AtomicLong()
    return OkHttpClient.Builder()
        .eventListenerFactory {
            TimelineEventListener(
                callSequence = callSequence.incrementAndGet(),
                emit = eventSink,
            )
        }
        .build()
}
```

`callSequence` 只用于关联同一进程内的事件，跨端追踪仍要使用受控的追踪标识。代码刻意没有记录域名、IP、完整 URL 和异常消息；生产采集应使用路由模板、错误分类和匿名化网络标识，避免把令牌、查询参数或用户地址写入日志。`eventSink` 还要支持并发写入，因为并行建连和取消可能从不同线程回调。事件方法必须快速返回，文件和网络 I/O 放到异步消费端，也不能从回调重新调用同一个客户端。

同一 `Call` 内的事件不保证各出现一次：

- 连接池复用时不会出现 DNS、connect 和 TLS 事件。
- 缓存直接命中时不会进入网络读写。
- 重定向、身份验证跟进和连接恢复可能形成多个请求/响应交换。
- OkHttp 5 默认启用 `fastFallback`，多个地址可能并行建连，因此 `connectStart`、`connectFailed` 和 `connectEnd` 会重复或交错。
- 响应体只有被读取或关闭后，生命周期数据才完整。只拿到 `Response` 就结束计时，会漏掉下载耗时。

业务队列仍需在业务提交与 `Call.enqueue()` 两处打点。OkHttp 5.4.0 的 `dispatcherQueueStart/End` 则直接标记网络库因线程或流数量限制产生的等待；未排队的调用不会收到这对事件。`callStart` 到首个缓存、代理或连接事件之间不能统一命名为 DNS 耗时。

## 速度、弱网、安全和功耗是四组约束

这四项目标的策略会相互影响。预连接可能降低下一次请求延迟，也可能无故唤醒无线电；并行建连能缩短坏地址带来的等待，也会增加连接尝试；频繁重试提高某些请求的成功率，同时会放大流量和服务端压力。

| 目标 | 常用手段 | 必须同时观察 |
| --- | --- | --- |
| 交互速度 | 连接复用、缓存、请求合并、减少首屏字段、合适的 HTTP/2 或 HTTP/3 | P50/P95/P99、队列等待、缓存路径、首屏完成时间 |
| 弱网可用性 | 多地址建连、总截止时间、幂等重试、缓存数据、降级界面 | 物理尝试数、尾延迟、重复写入、取消是否生效 |
| 传输安全 | HTTPS、平台证书验证、Network Security Configuration、证书透明度 | 握手失败分类、证书轮换、调试信任配置是否进入发布包 |
| 功耗与流量 | 批量同步、计费网络约束、压缩、受控预取 | 后台移动流量、无线电唤醒、废弃预取字节、任务新鲜度 |

安全策略不能用跳过证书校验换成功率。自定义“信任所有证书”的 `TrustManager`、宽松 `HostnameVerifier` 和明文回退都应从发布构建中移除。对于以 Android 17 / API 37 为目标版本的应用，证书透明度默认启用；只有确有私有证书体系等兼容需求时才评估按域配置。

Android 官方安全文档不建议普通应用使用证书固定。服务端更换证书或 CA 后，旧版本客户端可能全部断网。如果业务风险评估后仍决定固定公钥，必须准备备用公钥、短有效期、服务端轮换演练和应用版本覆盖方案。证书固定不能代替标准证书链与主机名验证。

前台交互和后台同步还应拥有不同的并发配额。共享一个 `OkHttpClient` 有利于复用连接和线程资源，但业务调度层可以为后台任务设置独立队列或并发闸门，防止批量上传占满用户可见请求的执行机会。

## OkHttp、Cronet、HttpEngine 与长连接怎么选

网络栈的协议列表只说明能力，无法直接证明业务收益。选型时同时检查兼容范围、可观测性、现有拦截器语义、缓存目录和服务端配置。

| 方案 | 合适的请求 | 主要能力 | 引入时要验证 |
| --- | --- | --- | --- |
| OkHttp 5 | 常规 REST、GraphQL、文件上传下载 | 成熟的拦截器、HTTP/1.1 与 HTTP/2、连接池、`EventListener` | 调度等待、连接复用、业务拦截器顺序；它本身不提供 HTTP/3 |
| Cronet 库 | 需要 Chromium 网络栈、HTTP/3 over QUIC、Brotli 或 Cronet 生态集成的路径 | 异步请求、HTTP/1.1、HTTP/2、HTTP/3、缓存、`RequestFinishedInfo` | 提供程序、QUIC 成功率、TCP 回退尾延迟、回调线程、缓存目录 |
| 平台 `HttpEngine` | 系统版本和扩展版本满足条件，并希望使用平台 HTTP 引擎的应用 | Cronet 风格 API，HTTP/2 与 QUIC 默认开启，可选 Brotli 与 HTTP 缓存 | API/扩展版本、公开指标边界、厂商模块更新、存储目录 |
| 自有长连接 | IM、实时协作、推送补充通道等有持续会话语义的业务 | 自定义心跳、消息确认、重连和流控 | NAT 超时、前后台限制、鉴权续期、服务端容量；不用于替代全部 HTTP API |

Cronet 可以通过应用库或 Google Play 服务提供程序加载。工程上应检查最终选中的 `CronetProvider`；Java 回退实现的性能和协议能力不能当作原生 Cronet 等价物。应用通常复用一个 `CronetEngine`，同一个磁盘存储目录也不能被多个引擎同时占用。请求完成数据由 `RequestFinishedInfo.Listener` 采集，调试环境还可按需生成 NetLog，但 NetLog 可能包含敏感网络信息，不应默认上传。

Cronet 的 `UrlRequest.Callback.onResponseStarted()` 收到的是重定向后的最终响应头。HTTP 4xx/5xx 仍是成功完成传输的 HTTP 响应，业务必须读取或取消响应体；它们不会自动进入 `onFailed()`。`NetworkException.immediatelyRetryable()` 只是网络库给出的一个信号，业务仍要检查幂等性、总截止时间和尝试次数。

### `android-17.0.0_r1` 的 HttpEngine 边界

Android 17 公开 SDK 中，`HttpEngine` 从 API 34 / Android S 扩展 7 起可用。`HttpEngine.Builder` 的默认值是：

- HTTP/2：开启。
- QUIC：开启。
- HTTP 缓存：关闭。
- Brotli：关闭。

`setEnableHttpCache()` 的磁盘模式除 HTTP 响应外，还可保存 QUIC 服务器信息；`HTTP_CACHE_DISK_NO_HTTP` 只持久化这类非 HTTP 数据。开启磁盘模式前必须设置独占的存储目录。`setEnableBrotli(true)` 会让引擎在 `Accept-Encoding` 中声明 Brotli，不能因为类存在就假定已经开启。

`android-17.0.0_r1` 的公开 API 没有完整的逐请求 DNS、connect、TLS 分段结果。后续模块版本增加的 `FinishedRequestTimings` 不属于这个源码锚点，基于 `r1` 构建的观测代码不能依赖它。`UrlResponseInfo` 可提供协商协议、缓存标记和字节等公开结果，完整分段应在所选网络库公开能力范围内设计，不能调用隐藏类补齐。

这些结论可在 [`android-17.0.0_r1` 的 API 37 公开签名](https://android.googlesource.com/platform/prebuilts/sdk/+/refs/tags/android-17.0.0_r1/37.0/public/api/android.txt) 中核对。24.5 继续说明 QUIC、0-RTT 和模块版本边界。

## DNS、建连和网络切换按 Network 隔离

DNS 决定候选地址，连接池减少重复握手，Fast Fallback 控制多个候选地址的尝试节奏。三部分相互影响，但生命周期不同。

HTTPDNS 的同步边界见 24.10。OkHttp `Dns.lookup()` 位于路由生成前，请求必须等它返回。把一次实时 HTTPDNS 请求放进 `lookup()` 会让原请求依赖另一条网络请求，还可能递归进入同一个网络栈。生产实现通常由后台任务刷新结果，`lookup()` 只读本地快照；无结果、过期或失败时回到系统 DNS。

OkHttp 5 的 `fastFallback` 默认开启，通过并行尝试多个地址减少单个坏地址造成的等待。它会消耗额外套接字和握手资源，因此要记录每个连接尝试的地址族、开始顺序、失败分类和获胜协议。日志中的地址应匿名化，故障隔离至少包含主机、地址、Android `Network`、失败类型和有效期。

不要因 DNS TTL 到期就清空连接池。已经建立的连接有自己的可用性与安全校验，TTL 管理的是后续解析结果。HTTP/2 连接合并还可能让多个主机共用一条连接，是否可复用要同时满足证书、地址、代理和网络库规则，不能用“每个域名一条连接”推算。

### 网络回调只使用随回调送达的数据

Android 8.0 起，默认网络回调中的 `onAvailable(network)` 后会依次送达 `onCapabilitiesChanged()`、`onLinkPropertiesChanged()` 和 `onBlockedStatusChanged()`。不要在这些回调里同步调用 `getNetworkCapabilities()` 或 `getLinkProperties()`；返回对象可能已经过期，也可能为空。Android 17 对应实现可在 [`ConnectivityManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java) 中核对。

判断网络时使用能力，少用传输类型猜测：

- `NET_CAPABILITY_INTERNET` 表示网络配置为可访问互联网，不代表已经通过系统验证。
- `NET_CAPABILITY_VALIDATED` 是系统确认公共互联网可达的信号。
- `NET_CAPABILITY_CAPTIVE_PORTAL` 表示可能需要门户登录。
- `NET_CAPABILITY_NOT_METERED` 表示系统认为该网络不计费。
- Wi-Fi 可能计费、拥塞或无互联网；蜂窝网络也可能吞吐更高。一个网络还可能同时具有多个传输类型，VPN 会进一步改变观察结果。

默认网络切换后，新建套接字会使用新的默认网络；已有连接可能短时间继续工作，随后失效。不要在每次 `onAvailable()` 或能力变化时直接调用 `connectionPool.evictAll()`：这会终止可复用连接，并让所有请求同时重建。更稳妥的处理是让网络库识别连接失效，对失败的幂等请求在预算内恢复。显式使用 `Network.bindSocket()` 的业务应按 `Network` 管理客户端和连接池，并在对应网络失效后关闭该组资源。

## 弱网治理从一次逻辑操作开始计数

“请求重试了几次”常有歧义。一次页面加载可能触发一个逻辑操作，逻辑操作包含多个网络库 `Call`；每个 `Call` 又可能包含多个路由尝试和 HTTP 交换。

| 层级 | 示例 | 应记录的标识与预算 |
| --- | --- | --- |
| 逻辑操作 | 刷新首页、提交订单、上传草稿 | `operation_id`、用户等待截止时间、允许的总字节 |
| 网络库调用 | 一次 OkHttp `Call` 或 Cronet `UrlRequest` | `call_id`、调用序号、取消原因 |
| 连接尝试 | IPv6、IPv4、代理或替代地址建连 | `attempt_id`、地址族、`Network`、错误分类 |
| HTTP 交换 | 重定向、401 认证跟进、业务层重试 | `exchange_id`、响应码、发送与接收字节 |

所有内部恢复都消耗逻辑操作的总预算。网络库连接恢复一次、业务层再重试两次，不能在报表里写成“只重试两次”。

### 重试前回答五个问题

1. 失败发生在哪一段？DNS、connect、TLS、写入、读取、HTTP 状态码和业务错误不能放在一个“网络失败”桶里。
2. 服务端是否可能已经执行？请求体写出后连接断开，客户端不知道服务端是否收到了并提交事务。
3. 操作是否幂等？GET、HEAD 通常可重试；支付、下单、发消息等写操作需要服务端支持稳定的幂等键和结果查询。
4. 剩余截止时间是否足够？新尝试要包含排队、解析、建连、TLS 和读取时间，不能只比较单次读超时。
5. 服务端是否要求等待？遇到 429 或 503 时解析 `Retry-After`，并与客户端总截止时间共同决定是否再试。

OkHttp 的 `retryOnConnectionFailure` 处理部分可恢复连接故障，不会替业务处理 HTTP 429、5xx 或业务错误码。业务重试器要放在它的外层统一计数，采用有上限的指数退避与随机抖动，并响应页面销毁、协程取消和进程后台化。多个请求同时失败时，还要限制恢复并发，避免网络恢复瞬间发出一批重复请求。

状态变更接口即使带了幂等键，也要由服务端定义键的作用域、保留时长、参数冲突行为和结果查询方式。客户端生成一个随机键但服务端不存储，不能提供幂等保证。

降级同样属于预算决策。缓存数据要标注新鲜度，界面要区分“旧数据可用”和“操作提交失败”；读请求可以显示旧数据，写请求不能用本地成功状态掩盖服务端结果未知。

## 压缩、缓存和预取要分别核算

这三类策略节省的资源不同：

- 压缩减少线上传输字节，同时增加压缩、解压和缓存变体成本。
- HTTP 缓存避免或缩短网络访问，正确性由 `Cache-Control`、`ETag`、`Vary` 等响应语义决定。
- 预取把一次可能发生的请求提前执行，命中时减少等待，未使用时会浪费流量、电量和缓存空间。

| 请求形态 | 优先检查 | 常见误判 |
| --- | --- | --- |
| 小型 JSON 配置 | `ETag`、字段裁剪、合并往返 | Brotli 节省的字节可能抵不过额外处理和首包开销 |
| 首屏列表 | 分页、响应字段、图片尺寸、下一页概率 | 拉取更多数据不等于首屏更快 |
| 大文件 | Range、实体校验、临时文件、原子完成 | 仅支持 Range 不代表资源变更后还能安全续传 |
| 图片与视频 | CDN、尺寸协商、格式、播放器自适应码率 | 普通 API 的超时和并发参数不适用于媒体 |
| 日志与遥测 | 批量、压缩、去重、后台约束 | 每条日志独立重试会增加无线电唤醒 |

记录字节数时必须写明语义：线上压缩字节、解压后的响应体字节、业务对象大小不能混为一个字段。各网络库公开指标包含的头部、协议开销和解压阶段也可能不同，跨网络栈对比前要统一口径。

缓存命中率也要分路径：直接命中、条件请求返回 304、网络取回新实体、请求不可缓存。带鉴权信息的响应是否允许共享或本地保存，由服务端缓存指令和产品安全要求共同决定，客户端不能为了命中率强制缓存。

预取应由下一步使用概率、对象体积和资源状态共同控制。出现计费网络、Data Saver、低电量、后台受限或业务方向改变时，及时取消尚未开始的任务；已经执行的请求仍要纳入废弃字节统计。Android 官方网络功耗文档中的无线电状态数字来自特定制式和设备，只适合作为机制示例，不能直接当作 LTE、5G 和所有运营商的固定参数。

## 后台请求由 WorkManager 和系统约束调度

后台同步的目标是按期完成并控制资源，而不是争抢最低延迟。可延迟的持久任务使用 WorkManager 表达网络、电量、充电、空闲和存储约束；用户主动发起、需要进度与取消控制的大传输，应评估 `DownloadManager` 或系统的用户发起数据传输任务。

下面的示例为可延迟同步创建唯一任务，避免同一业务范围反复入队。`NetworkType.UNMETERED` 表示系统判定为不计费，不等同于指定 Wi-Fi。

```kotlin
fun enqueueDeferredSync(
    context: Context,
    uniqueName: String,
    requireCharging: Boolean,
) {
    val constraints = Constraints.Builder()
        .setRequiredNetworkType(NetworkType.UNMETERED)
        .setRequiresBatteryNotLow(true)
        .setRequiresCharging(requireCharging)
        .build()

    val request = OneTimeWorkRequestBuilder<DeferredSyncWorker>()
        .setConstraints(constraints)
        .setBackoffCriteria(
            BackoffPolicy.EXPONENTIAL,
            WorkRequest.MIN_BACKOFF_MILLIS,
            TimeUnit.MILLISECONDS,
        )
        .build()

    WorkManager.getInstance(context).enqueueUniqueWork(
        uniqueName,
        ExistingWorkPolicy.KEEP,
        request,
    )
}
```

`uniqueName` 应表示稳定的任务范围，并避免包含账号、文档名等个人信息。`KEEP` 适合“已有同范围任务就不重复加入”的语义；如果新任务必须取代旧输入，需明确选择 `REPLACE` 带来的取消行为，或重新设计可合并的输入队列。

约束在 Worker 运行期间变为不满足时，WorkManager 会停止工作，条件恢复后再安排。Worker 因此必须支持协作式取消：关闭响应体、取消进行中的 HTTP 调用、保留可验证的续传位置，并让服务端写操作具备幂等性。退避时间是调度下限，不是精确执行时刻。

Android vitals 把应用处于 `PROCESS_STATE_BACKGROUND` 或 `PROCESS_STATE_CACHED` 时，每天移动网络接收与发送合计 50 MB 视为过度后台移动网络使用。这个值是 Play Console 的告警定义，不是业务可以放心用满的配额。定位功耗时优先使用系统追踪、Macrobenchmark 功耗指标或 Power Profiler；Battery Historian 已不再积极维护。

Data Saver 开启且当前网络计费时，系统可能限制后台数据，前台应用也应减少非必要传输。任务是否执行应结合系统限制、用户设置和产品时效要求，不能只判断 Wi-Fi 或蜂窝图标。

### TrafficStats 能回答什么

`TrafficStats.getUidRxBytes()` 与 `getUidTxBytes()` 可以观察当前 UID 自开机以来、跨所有网络接口累计的网络层字节。它适合做进程内前后差值和粗粒度异常发现，但有以下边界：

- 设备重启后归零，设备不支持时返回 `UNSUPPORTED`。
- Android 7.0 起只能查询调用方 UID，查询其他 UID 返回 `UNSUPPORTED`。
- UID 数值包含该 UID 的全部接口和 TCP/UDP 流量，无法直接得到单请求、单域名或后台移动网络字节。
- 接口级统计对 VPN、CLAT 等调整并不完整，不能用作结算或安全审计。
- 历史用量查询应使用 `NetworkStatsManager`，还要遵守权限和用户授权要求。

Android 17 的这些约束可在 [`TrafficStats.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework-t/src/android/net/TrafficStats.java) 中核对。`TrafficStats.setThreadStatsTag()` 只提供流量归因标签，不会替应用执行限流、取消或后台约束。

## 指标按逻辑操作、尝试和交换建模

客户端只能观察本地队列、网络库事件和解码；接入层知道路由、限流与上游耗时；业务服务知道事务和依赖。三方使用同一个追踪标识，才能判断 TTFB 增长来自无线网络、网关排队还是服务端。

推荐的字段按职责分组：

| 层级 | 字段 | 说明 |
| --- | --- | --- |
| 逻辑操作 | 路由模板、操作类型、前后台、总截止时间、最终结果 | 统计一次用户动作，不被内部重试放大 |
| 网络调用 | 网络栈、缓存路径、协商协议、响应码、发送/接收字节 | 协议从公开协商结果读取，不按 URL 或端口猜测 |
| 连接尝试 | DNS、connect、TLS 事件，地址族，代理类型，匿名化 `Network` | 允许缺失和重复，保留并行尝试关系 |
| Android 网络 | `VALIDATED`、`NOT_METERED`、`CAPTIVE_PORTAL`、传输集合、Data Saver | 使用回调提供的能力快照 |
| 服务端 | 区域、接入节点、排队、上游耗时、限流、重试 | 与客户端 TTFB 和响应码关联 |
| 页面消费 | 解码、数据合并、首屏提交、降级类型、缓存年龄 | 判断网络变快是否转化为用户可见收益 |

追踪标识可通过标准追踪头或业务头传递，但服务端要限制长度、字符集和信任边界，不能把客户端提供的任意值直接写入高基数字段。完整 URL、查询参数、Cookie、Authorization、原始 IP、证书内容和异常正文不进入常规遥测。路由用 `/items/{id}` 这类模板表示。

统计时至少分开以下分母：

- 逻辑操作成功率：用户动作是否在截止时间内得到可用结果。
- 网络调用成功率：每个 `Call` 或 `UrlRequest` 的结果。
- 连接尝试成功率：每个地址与协议尝试的结果。
- 缓存可用率：直接命中、条件命中和旧数据降级。

如果把所有连接尝试都当请求，Fast Fallback 会抬高“失败率”；如果只保留获胜连接，又看不到 IPv6、代理或某组地址持续失败。原始事件与面向业务的聚合指标应同时保留定义。

Native socket Hook 可以覆盖未接入统一网络库的流量，但它会引入 ABI、兼容性、稳定性和隐私风险。普通应用应先把 OkHttp `EventListener`、Cronet 完成信息、平台公开回调和业务追踪记录准确；Hook 更适合受控诊断或专门的 APM 组件。

## 不同请求场景分别验收

Cronet 可以接入 Media3/ExoPlayer、gRPC、OkHttp 传输适配器和图片库，但“用了 Cronet”不代表这些组件自动共用同一个引擎、连接池、缓存目录或指标。必须检查应用创建和注入的实例。

| 场景 | 主要指标 | 不能直接套用的结论 |
| --- | --- | --- |
| 普通 API | 队列、缓存、DNS、connect、TLS、TTFB、解码 | 单接口平均值不能代表页面完成时间 |
| WebView | WebView/Chromium 版本、导航与资源时序、Service Worker | App 的 OkHttp 拦截器通常覆盖不到 WebView |
| 媒体播放 | 启播、卡顿、缓冲余量、码率切换、CDN、Range | 普通 JSON 的超时与并发配置不适用于媒体段 |
| 大文件传输 | 断点位置、实体校验、磁盘空间、用户取消、完整性 | 多连接下载不保证更快，也可能触发服务端限制 |
| IM 与长连接 | 握手、鉴权、心跳、确认、积压、重连退避 | HTTP 请求成功率不能描述会话可用性 |

弱网实验也要覆盖业务会遇到的网络状态：高 RTT、限带宽、丢包、IPv6-only/NAT64、门户网络、VPN、Data Saver、前后台切换和 Wi-Fi/蜂窝切换。测试代理可以制造延迟、断流和状态码，MockWebServer 可以验证重定向、重试、半包与响应体关闭；真机测试负责验证 Android 网络回调、无线电和系统后台限制。

每次改动至少比较：

- 逻辑操作的 P50、P95、P99 与超时率。
- 每个操作产生的网络调用数、连接尝试数和总字节。
- 缓存直接命中、条件命中与旧数据降级比例。
- 切网、取消和页面退出后的遗留请求数。
- 后台移动网络字节、任务完成时效与功耗变化。

平均耗时下降但 P99、重试次数或后台字节上升，不能直接判定优化有效。

## 上线检查清单

- 业务入队、网络执行、缓存路径和七段时间线都有明确边界。
- `EventListener` 允许事件缺失、重复和并行，不用单一 `connectStart` 覆盖后续尝试。
- TTFB 从请求发送结束算到响应开始，并能与接入层和服务端追踪记录关联。
- HTTPDNS 没有在 `Dns.lookup()` 内执行同步网络请求，结果按 Android `Network` 隔离。
- 网络切换不会无条件清空全局连接池，也不会在回调内同步查询网络属性。
- 重试从逻辑操作统一计数，并同时受幂等性、总截止时间、总字节和并发限制。
- 429/503 处理 `Retry-After`；写入后断线被视为结果未知，不直接重复提交。
- Android 17 保留平台证书验证与默认 CT，不含信任所有证书或宽松主机名验证。
- Cronet、HttpEngine 和 OkHttp 的协议、缓存、压缩与指标能力按实际配置记录。
- WorkManager 唯一任务、约束、停止和退避行为与业务语义一致。
- `TrafficStats` 只用于其支持的 UID 粗粒度统计，不冒充单请求或后台移动流量。
- WebView、媒体、大文件和长连接使用各自的指标与测试场景。

## 参考资料

- [Android 17 / API 37 公开 API 签名](https://android.googlesource.com/platform/prebuilts/sdk/+/refs/tags/android-17.0.0_r1/37.0/public/api/android.txt)
- [HttpEngine.Builder API](https://developer.android.com/reference/android/net/http/HttpEngine.Builder)
- [Cronet 概览](https://developer.android.com/develop/connectivity/cronet)
- [Cronet 集成](https://developer.android.com/develop/connectivity/cronet/integration)
- [Cronet RequestFinishedInfo](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo)
- [OkHttp 5.4.0 EventListener 源码](https://github.com/square/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
- [OkHttp 5.4.0 OkHttpClient 源码](https://github.com/square/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt)
- [读取 Android 网络状态](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config)
- [Android 网络协议安全](https://developer.android.com/privacy-and-security/security-ssl)
- [定义 WorkManager 任务](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [用户发起数据传输](https://developer.android.com/develop/background-work/background-tasks/uidt)
- [优化网络访问以降低功耗](https://developer.android.com/topic/performance/power/network/index.html)
- [后台移动网络用量 Android vitals](https://developer.android.com/topic/performance/vitals/bg-network-usage)
- [TrafficStats API](https://developer.android.com/reference/android/net/TrafficStats)
