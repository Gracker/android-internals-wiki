---
title: "网络架构与连接管理"
chapter: "24.4"
section: "24.4"
status: finalized
pipeline_stage: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [okhttp, connection-pool, httpdns, weak-network, dispatcher]
confidence: high
sources:
- type: legacy-reference-preserved
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/main/CHANGELOG.md"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt"
- type: official
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt"
- type: aosp
  path: "https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java"
- type: official
  path: "https://developer.android.com/develop/background-work/background-tasks/data-transfer-options"
- type: aosp
  path: "https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java"
- type: aosp
  path: "https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/DnsResolver.java"
- type: aosp
  path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/StrictMode.java"
- type: aosp
  path: "https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework-t/src/android/net/TrafficStats.java"
- type: official
  path: "https://source.android.com/docs/core/ota/modular-system/dns-resolver"
- type: official
  path: "https://developer.android.com/develop/connectivity/network-ops/reading-network-state"
- type: official
  path: "https://developer.android.com/develop/background-work/background-tasks/uidt"
- type: official
  path: "https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running"
- type: legacy-reference-preserved
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt"
- type: legacy-reference-preserved
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt"
- type: legacy-reference-preserved
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt"
- type: legacy-reference-preserved
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt"
- type: legacy-reference-preserved
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt"
- type: legacy-reference-preserved
  path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt"
- type: reference
  path: "https://www.rfc-editor.org/rfc/rfc9110.html"
- type: reference
  path: "https://www.rfc-editor.org/rfc/rfc6585.html"
- type: reference
  path: "https://www.rfc-editor.org/rfc/rfc7233.html"
- type: aosp
  path: "system/dns-resolver"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1; Android Developers network state, background transfer, UIDT and long-running WorkManager docs; OkHttp 5.4.0 source and changelog; RFC 9110, RFC 6585 and RFC 7233"
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
related_chapters: ["24.5", "12.1", "12.2"]
last_consolidated_at: "2026-08-11"
consolidated_from:
- "src/part5-app/ch24-io-network/08-io-network-case-studies.md"
- "src/part5-app/ch24-io-network/14-network-request-performance-playbook.md"
last_review_finalize_at: "2026-08-15T10:05:57+08:00"
last_review_finalize_run_id: "20260815-100557-gracker-writing-review"
last_draft_polish_at: "2026-08-15T10:05:57+08:00"
last_draft_polish_run_id: "20260815-100557-gracker-writing"
---

# 网络架构与连接管理

## 一次网络请求为何会变慢

一次请求显示为“慢”，内部可能经历 Dispatcher（OkHttp 的异步调用调度器）排队、DNS 查询、多条地址竞速、TCP 建连、TLS 握手、服务端等待和响应体读取。只修改某个超时参数，既无法判断时间花在哪个阶段，也可能把局部故障变成更长的等待。

应用架构需要处理四个问题：怎样复用连接，怎样选择解析策略，怎样隔离不同类型的流量，以及怎样在网络变化和请求失败时控制重试。一次调用的分段计时与协议细节见 [12.1 网络性能优化](../../part2-performance/ch12-apk-network/01-network-performance.md)，TLS 信任边界见 [12.2 网络安全与 TLS 性能](../../part2-performance/ch12-apk-network/02-network-security-tls-performance.md)。

平台结论以 Android 17 / API 37 / AOSP `android-17.0.0_r1` 为锚点，客户端结论以 2026 年 6 月 8 日发布的 OkHttp 5.4.0 为锚点。OkHttp 独立于 Android 发布；项目升级客户端版本后，还要复核默认参数、拦截器能力和事件定义。

## 把网络层拆成四类职责

这里把网络层拆成连接、解析、调度和容错四类职责。这样分工的目的，是让配置、故障和指标都有明确归属。

| 职责 | 负责的问题 | 常见故障 | 主要观测点 |
| --- | --- | --- | --- |
| 连接 | TCP、TLS 和 HTTP 连接如何创建、复用与释放 | 频繁冷建连、响应体未关闭、HTTP/2 复用率低 | `connectStart`、`secureConnectStart`、`connectionAcquired`、协议 |
| 解析 | 主机名如何得到候选地址 | DNS 慢、地址族回退慢、缓存跨网络污染 | `dnsStart`、`dnsEnd`、候选地址数、目标 `Network` |
| 调度 | 哪些请求立即执行，哪些延迟、取消或批量执行 | 首屏流量被大文件占用、同步调用绕过并发限制 | 业务队列、Dispatcher 队列、取消率、后台约束 |
| 容错 | 失败是否重试，何时读取缓存或进入离线队列 | 重试风暴、重复写入、切网后持续使用旧地址 | 失败阶段、尝试次数、幂等键、缓存状态、网络变化序号 |

连接复用、解析、业务调度和失败恢复应保留各自的接口与指标。把这些策略全部写进一个拦截器，会混淆一次逻辑调用中的重定向、认证、传输恢复和业务重试，也不利于设置统一的调用截止时间。OkHttp 5.4.0 允许拦截器为当前调用覆盖缓存、连接池、DNS、套接字工厂等客户端配置；这类覆盖应进入配置审计和诊断日志，不宜藏在通用拦截器中。

## OkHttp 连接池与复用策略

### 共享客户端，不按请求创建

`OkHttpClient` 持有连接池、Dispatcher、DNS、TLS 配置和拦截器。OkHttp 官方建议在应用内共享客户端；每次请求创建客户端，会留下彼此隔离的连接池与线程资源。

下面的代码用于建立一个进程级共享客户端。示例没有覆盖 OkHttp 默认连接池、并发和超时参数，因为这些参数应由项目的链路数据和服务等级目标（可接受的耗时、成功率等边界）决定。

```kotlin
object NetworkClient {
    val shared: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .eventListenerFactory { NetworkEventListener() }
            .build()
    }
}
```

`lazy` 只负责避免重复构造；应用仍需保证使用同一个对象。需要调整某类请求时，优先从 `shared.newBuilder()` 派生。OkHttp 5.4.0 的 `newBuilder()` 会继承配置，并共享连接池、调度器所用线程池等资源；直接调用新的 `OkHttpClient.Builder()` 则会创建独立资源。

### 连接池不是总连接数上限

OkHttp 5.4.0 默认连接池构造参数中的数量，表示最多保留多少条**空闲连接**，并不限制正在使用的连接总数，也不等于域名数量。HTTP/1.1 通常在连接空闲后复用；HTTP/2 可以在一条连接上并发传输多个逻辑流（stream，每个流承载一组双向请求与响应数据）。默认值属于库的调优选择，客户端升级后可能变化，不应复制为架构常量。

OkHttp 用 `Address` 和 `Route` 判断连接能否复用：

- `Address`（连接地址配置）包含 URL 协议方案（scheme，例如 HTTP 或 HTTPS）、主机、端口、DNS、代理、套接字创建器（socket factory）、TLS 配置、主机名校验器（hostname verifier）和证书或公钥固定器（certificate pinner）等静态配置。
- `Route`（具体连接路径）还包含代理、候选 IP 与套接字地址等本次连接选择。
- 跨主机的 HTTP/2 连接合并还要求直连路径、IP、证书覆盖、主机名校验、证书固定规则等条件同时满足。

两个域名解析到同一 IP，不代表它们一定共享 HTTP/2 连接。反过来，证书覆盖多个域名也不足以保证连接合并。当前判断以 OkHttp 5.4.0 的 [`RealConnection.isEligible()`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt) 为准；为便于追溯，原有 5.3.0 源码锚点 [`RealConnection.isEligible()`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt) 仍予保留。

### 关闭响应体才能稳定复用连接

同步调用必须关闭 `Response` 或 `ResponseBody`。下面的代码用于读取一个短文本响应，并确保成功、异常和提前返回时都执行关闭。

```kotlin
fun executeText(client: OkHttpClient, request: Request): String {
    return client.newCall(request).execute().use { response ->
        check(response.isSuccessful) {
            "HTTP ${response.code}"
        }
        response.body.string()
    }
}
```

`use` 离开作用域时会关闭响应体。响应体未关闭会占用套接字与 HTTP/2 逻辑流，连接池即使配置正确也无法正常复用。流式下载不能先调用 `string()`，但仍要在消费结束、取消或异常时关闭响应体。

### 用事件区分排队、解析、建连与服务端等待

下面的监听器只展示阶段边界。生产采集器应使用单调时钟保存时间戳，并把数据写入低开销的内存队列；回调中不执行文件 I/O、网络 I/O，也不重新调用同一个客户端。

```kotlin
class NetworkEventListener : EventListener() {
    override fun dnsStart(call: Call, domainName: String) = Unit

    override fun dnsEnd(
        call: Call,
        domainName: String,
        inetAddressList: List<InetAddress>,
    ) = Unit

    override fun connectStart(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
    ) = Unit

    override fun secureConnectStart(call: Call) = Unit

    override fun connectionAcquired(
        call: Call,
        connection: Connection,
    ) = Unit

    override fun responseHeadersStart(call: Call) = Unit

    override fun callFailed(call: Call, ioe: IOException) = Unit
}
```

连接池命中时，DNS 与建连事件可能全部缺席。重定向、认证和连接路径重试又可能让同一组事件出现多次。采集时要以一次逻辑 `Call` 为父级，再为每次 DNS、建连和交换分配事件序号；不能把第一组事件直接当作整次调用的唯一阶段。

一次请求进入 DNS 前，还可能停留在业务队列、OkHttp Dispatcher 或缓存判定。端到端时间线应覆盖业务入队、异步排队、直接或条件缓存命中、DNS、每次连接与 TLS 尝试、请求写入、TTFB（Time to First Byte，从请求发出到收到响应首部的等待）、响应体消费以及解码入库。TTFB 不等于“解析响应头所花的时间”；流式上传、双工请求和长连接还要单独定义边界。

指标应分成四层，避免重试把一次用户动作统计成多次失败：

| 层级 | 示例 | 应记录的标识与预算 |
| --- | --- | --- |
| 逻辑操作 | 刷新首页、提交订单、上传草稿 | `operation_id`、总截止时间、允许的总字节、最终结果 |
| 网络调用 | 一次 OkHttp `Call` 或 Cronet `UrlRequest` | `call_id`、调用序号、缓存路径、取消原因 |
| 连接尝试 | IPv6、IPv4、代理或替代地址 | `attempt_id`、地址族、匿名化 `Network`、失败分类 |
| HTTP 交换 | 重定向、401 跟进、业务层重试 | `exchange_id`、响应码、发送/接收字节 |

逻辑操作成功率、网络调用成功率、连接尝试成功率和缓存可用率必须使用各自分母。若把 Fast Fallback（并行尝试多个候选地址、优先采用先成功连接的机制）的每个地址尝试都当成请求，会虚增失败率；若只保留获胜连接，又看不到某个地址族持续故障。线上监控只使用路由模板、错误分类与匿名化网络标识，不能记录完整 URL、查询参数、Cookie、Authorization、原始 IP、证书正文或未经清洗的异常消息。

## DNS 优化与 HTTPDNS

### 系统 DNS 仍是默认基线

OkHttp 5.4.0 的 `Dns.SYSTEM` 最终调用 `InetAddress.getAllByName()`。在 Android 17 上，这条路径进入当前 Android `Network`（系统分配给一条具体网络的句柄）对应的系统解析链路，并受 VPN、Private DNS（Android 的加密 DNS 设置）、每网络缓存和网络切换影响。DNS Resolver 自 Android 10 起由可独立更新的 `com.android.resolv` Mainline 模块提供，应用无需维护一份永久 IP 表来替代它。

`Dns.lookup()` 是同步接口，OkHttp 在选择连接路径时调用它；实现类还必须支持并发调用。HTTPDNS 指应用通过 HTTP 或 HTTPS 接口获取域名地址的自定义解析方案，它不一定采用标准化的 DNS over HTTPS（DoH）协议。若 `lookup()` 内使用同一个业务客户端向 HTTPDNS 服务发请求，该服务的域名也可能重新进入自定义 `Dns`，形成递归解析。若查询又依赖同一组受限执行资源，还可能出现线程相互等待。这里应检查解析路径是否依赖自身，不能归因为连接池没有空闲连接。

### HTTPDNS 先定义策略边界

HTTPDNS 可用于处理特定地区的解析污染、CDN 地址选择或解析时延，但接入前要写清楚以下规则：

- HTTPS URL 继续使用原主机名。自定义 `Dns` 只返回地址；SNI（TLS 握手携带的目标主机名提示）、主机名校验（hostname verification）、证书或公钥固定（certificate pin）和 Cookie 域规则仍按主机名执行。
- TTL（Time to Live，解析结果的缓存有效期）使用 HTTPDNS 响应或服务协议给出的值。不存在“统一取 TTL 的某个百分比”这一通用规则。
- 缓存键至少包含主机名与 Android `Network` 身份，默认网络变化后旧网络的结果不能直接继承。
- 缓存保留 IPv4、IPv6 和多个候选地址。OkHttp 5.4.0 默认开启 Fast Fallback，会并行错峰尝试候选连接；只保留一个地址会丢失这项恢复能力。这类策略也常称为 Happy Eyeballs。
- HTTPDNS 查询使用独立的引导解析策略，不能依赖正在实现的自定义解析器。
- 系统 DNS 回退是产品策略，不是无条件规则。严格隐私模式若承诺只使用指定解析服务，静默转向系统 DNS 会违反承诺；允许回退时也要记录原因。
- 自定义 HTTPDNS 会绕开系统解析器为 Private DNS、企业 VPN 和分流 DNS（不同域名交给不同解析器）提供的解析语义。应用仍可能通过 VPN 传输后续连接，但域名解析结果已不再由该系统策略决定。企业内网、专网和本地域名尤其需要实机验证。

下面的工程骨架只在同步路径读取缓存。`HttpDnsCache` 是应用接口，异步刷新、持久化和服务鉴权应在它的实现外完成。

```kotlin
interface HttpDnsCache {
    fun lookup(
        network: Network?,
        hostname: String,
        nowElapsedRealtimeMs: Long,
    ): List<InetAddress>
}

class CachedHttpDns(
    private val currentNetwork: () -> Network?,
    private val cache: HttpDnsCache,
    private val systemDns: Dns = Dns.SYSTEM,
) : Dns {
    override fun lookup(hostname: String): List<InetAddress> {
        val cached = cache.lookup(
            network = currentNetwork(),
            hostname = hostname,
            nowElapsedRealtimeMs = SystemClock.elapsedRealtime(),
        )
        return cached.ifEmpty {
            systemDns.lookup(hostname)
        }
    }
}
```

这里用 `elapsedRealtime()` 判断进程内有效期，避免用户修改设备日期或时间后错误延长 TTL。若缓存需要跨重启持久化，还要同时保存可恢复的过期依据，并在重启后按协议重新校验。缓存写入端应直接解析数值 IP，不要在同步 `lookup()` 中用主机名解析 API 间接触发另一轮 DNS。

示例适用于明确允许系统 DNS 回退的策略。严格解析策略应把回退实现作为依赖传入，并让失败显式返回。若客户端绑定到指定 Android `Network`，回退解析也应使用该网络的 `getAllByName()`，并与对应的套接字绑定策略保持一致。

HTTPDNS 查询失败、返回空地址、地址连接失败和 TLS 校验失败是不同事件。前两类属于解析服务与缓存策略，连接失败要保留到具体连接路径，TLS 失败不能通过关闭主机名校验来“兼容”。

## Android 网络状态只能作为动态信号

Android 17 的 [`NetworkCapabilities`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) 对三个常用能力给出了明确边界：

- `NET_CAPABILITY_INTERNET` 表示网络被配置为访问一般互联网，不证明当前可达。
- `NET_CAPABILITY_VALIDATED` 表示系统最近一次验证一般互联网成功，不证明业务端点此刻可达。
- `NET_CAPABILITY_NOT_METERED` 表示网络不按流量计费。大传输应看该能力，而不是用 Wi-Fi 或蜂窝等传输类型代替计费判断。

`VALIDATED` 适合提示离线状态、延迟非紧急公网同步和标记监控数据，不适合作为每个 API 请求的前置条件。系统验证可能刚失效，业务端点仍可达；局域网、企业专网和登录门户（captive portal，需要网页登录或同意条款的受限网络）也可能没有一般互联网验证。Android 17 的局域网访问约束见 [24.14 Android 17 流媒体与本地网络](14-android17-streaming-local-network.md)。

### 用回调维护有时序的状态

`getNetworkCapabilities()` 返回的是调用瞬间的快照，Android 17 源码注释说明它可能立即过时。应用应注册 `NetworkCallback`，并使用 `onCapabilitiesChanged()` 传入的对象。若在回调内重新同步查询 `getNetworkCapabilities()` 或 `getLinkProperties()`，查询结果可能属于更新后的状态，与当前回调不再对应；这就是这里的竞态。

下面的代码用于维护当前 UID（Android 为应用分配的 Linux 用户标识）的默认网络信号。它在收到能力回调后才发布状态；Android 8.0（API 26）及以上，`onAvailable()` 后会按序收到 `onCapabilitiesChanged()`。

```kotlin
data class DefaultNetworkState(
    val network: Network? = null,
    val hasInternetCapability: Boolean = false,
    val validated: Boolean = false,
    val notMetered: Boolean = false,
)

class DefaultNetworkMonitor(
    private val publish: (DefaultNetworkState) -> Unit,
) : ConnectivityManager.NetworkCallback() {
    private var currentNetwork: Network? = null

    override fun onAvailable(network: Network) {
        currentNetwork = network
    }

    override fun onCapabilitiesChanged(
        network: Network,
        capabilities: NetworkCapabilities,
    ) {
        if (network != currentNetwork) return

        publish(
            DefaultNetworkState(
                network = network,
                hasInternetCapability = capabilities.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_INTERNET,
                ),
                validated = capabilities.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_VALIDATED,
                ),
                notMetered = capabilities.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_NOT_METERED,
                ),
            ),
        )
    }

    override fun onLost(network: Network) {
        if (network == currentNetwork) {
            currentNetwork = null
            publish(DefaultNetworkState())
        }
    }
}
```

注册方需要声明 `ACCESS_NETWORK_STATE`，并在不再观察时调用 `unregisterNetworkCallback()`。如果把回调投递到可并发执行的自定义执行器，`currentNetwork` 和发布器还要增加同步保护。

默认网络从 Wi-Fi 切到蜂窝时，新旧网络对象具有不同身份；接入点断开后重连，也可能得到新的 `Network`。HTTPDNS 缓存、按网络绑定的套接字以及诊断记录都应保留这一身份，不能只保存“Wi-Fi/蜂窝”字符串。

## 网络请求优先级与调度

### Dispatcher 只管理异步调用的执行时机

OkHttp 5.4.0 的 `Dispatcher` 是异步调用调度器。`maxRequests` 和 `maxRequestsPerHost` 控制通过 `Call.enqueue()` 提交的调用：超过并发上限的调用留在内存队列，等待已有异步调用结束。通过 `Call.execute()` 发起的同步调用会被计入 `runningCalls()`，但不会经过这两个上限的排队与放行判断。

这一区别会影响架构选择：

- 不能用 Dispatcher 参数为任意线程上的同步 `execute()` 提供全局限流。
- Dispatcher 没有业务优先级。它不会理解首屏、预取、监控上报和大文件之间的时效差异。
- `maxRequestsPerHost` 按 URL 主机名计数；多个主机可能指向同一 IP 或代理。WebSocket 也不计入该单主机限制。
- 限额调小只会阻止新的异步调用进入执行状态，已经运行的调用不会被中止。

业务调度应位于 OkHttp 之上：

| 层级 | 职责 | 示例 |
| --- | --- | --- |
| UI / ViewModel | 生命周期与用户意图 | 页面离开时取消；重复点击合并 |
| 数据访问层（Repository） | 数据来源与新鲜度 | 选择内存、磁盘、网络或离线队列 |
| 业务调度器 | 优先级、去重、配额与截止时间 | 首屏先于预取；监控数据合批 |
| OkHttp Dispatcher | 异步总并发与单主机并发 | 执行 `enqueue()` 调用 |
| WorkManager / JobScheduler | 持久后台工作的系统约束 | 网络、电量、充电和存储条件 |

若大文件流量经过 `enqueue()`，并且确认它会影响交互请求，可以为它配置独立 Dispatcher，同时从共享客户端派生，以继续复用兼容的连接。下面的函数展示资源关系，限额由调用方传入项目配置。

```kotlin
fun OkHttpClient.withDispatcherLimits(
    maxRequests: Int,
    maxRequestsPerHost: Int,
): OkHttpClient {
    require(maxRequests > 0)
    require(maxRequestsPerHost in 1..maxRequests)

    val dispatcher = Dispatcher().apply {
        this.maxRequests = maxRequests
        this.maxRequestsPerHost = maxRequestsPerHost
    }
    return newBuilder()
        .dispatcher(dispatcher)
        .build()
}
```

派生客户端使用新的 Dispatcher，但沿用基准客户端的连接池。并发上限应来自本项目的数据，同时观察 Dispatcher 排队、服务端并发能力、HTTP/2 逻辑流、文件吞吐和交互请求的尾延迟；尾延迟指 P95、P99 等较慢分位的耗时，而非平均值。

请求取消应由持有 `Call` 的业务作用域执行 `Call.cancel()`，或由支持取消传播的协程适配器完成。扫描 `dispatcher.queuedCalls()` 和 `runningCalls()` 后按请求标签（tag）取消，只能得到一个会变化的快照，也容易误取消其他页面复用的请求。共享请求需要引用计数或订阅者模型：一个订阅者退出时，不应中止其他订阅者仍在等待的调用。

### 后台传输要按用户意图选择 API

Android 官方的[后台数据传输选择指南](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)区分了可延迟同步和用户发起的长传输：

| 场景 | 推荐机制 | 边界 |
| --- | --- | --- |
| 非用户发起、可延迟的同步或上传 | WorkManager | 普通工作通常应能在约 10 分钟内完成，并且可停止、可重试；约束满足不保证精确开始时间 |
| 用户发起并需要持续展示进度的长上传或下载 | Android 14 / API 34 起使用 User-Initiated Data Transfer Job（UIDT，用户发起的数据传输任务） | 调度时机、通知与约束需符合 UIDT 要求；旧系统准备兼容方案 |
| 平台已有专用传输 API 的场景 | 专用 API | 优先使用平台已提供的生命周期与系统集成 |
| WorkManager 和专用 API 均不适合的短时关键工作 | 符合类型要求的前台服务 | 受后台启动、时长和前台服务类型限制 |

WorkManager 的长运行 Worker（工作单元）由前台服务与 JobScheduler（系统后台任务调度器）协作执行。Android 16 起，这类工作会消耗应用的任务运行配额，也就是系统允许应用占用后台执行资源的额度；Android 17 同样保留该边界。UIDT 不消耗普通任务配额，但仍受系统健康约束。截至本次核验，Jetpack 没有 UIDT 的兼容抽象，因此 Android 14 以下还要准备 WorkManager 长运行 Worker 等回退路径。用户点击后启动的长文件传输，不能以“WorkManager 一定能无限运行”为前提。

可延迟流量应合并传输，并用 `UNMETERED`、充电和电量等约束表达成本偏好。无线电尾部耗电随设备、制式、信号和运营商配置变化，不能把某个固定秒数写进通用调度算法。

### 大文件传输必须围绕可恢复状态设计

大文件失败后的成本远高于普通 API。下载任务至少持久化资源标识、临时文件、已验证字节数、总长度、强 ETag（服务器为特定字节表示生成且不带弱校验前缀 `W/` 的版本标识）、内容摘要与任务状态；上传任务则要区分“客户端已发送”和“服务端已确认”。进度只放在内存中，无法承受切网、进程终止或系统停止任务。

恢复 HTTP 下载时应遵守以下协议：

- 发送 `Range: bytes=<offset>-` 请求从指定字节偏移继续下载，并用 `If-Range` 携带强 ETag 等版本验证器；
- 只有收到 `206 Partial Content`（部分内容），且 `Content-Range` 给出的起点、终点和总长度都与记录一致时才追加；
- 收到 `200 OK` 说明服务端发送完整表示，应丢弃或重建旧临时文件，不能直接追加；
- 收到 `416 Range Not Satisfiable`（请求范围不可满足）时重新核对 `Content-Range` 与本地长度，不能直接宣告完成；
- 透明内容编码会改变字节偏移，断点协议要固定编码表示，必要时使用 `Accept-Encoding: identity`，要求服务器不要对响应内容再做压缩转换；
- 完成后校验长度、摘要或签名，再用一次不可分割的替换发布正式文件，避免其他读取方看到半成品。

上传前不要把整份文件读入字节数组。用户选择的 `content://` 内容地址应复制到应用拥有的不可变暂存文件，或通过 `ACTION_OPEN_DOCUMENT`（系统文档选择器动作）获取持久 URI（资源标识符）权限；即便已持久授权，原文档被移动或删除后仍要进入可恢复错误。OkHttp 的文件请求体可流式发送，但暂存文件在重试完成前必须保持路径、长度和内容不变。

断点上传还需要服务端协议共同保证：创建稳定的 `uploadId`（一次上传会话的唯一标识）；每个分片携带范围、长度与校验值；服务端以不可分割的操作确认分片，并让重复提交同一分片得到相同结果；客户端只持久化已确认范围；完成操作使用幂等语义，并由服务端验证完整长度与摘要。幂等表示同一操作重复执行不会重复产生业务效果。分片并发与大小应依据网络、服务端限制和设备读写实测，进度回调按时间或变化幅度限制频率。

验收先验证恢复正确性，再比较吞吐：覆盖 `206`/`200`/`416`、远端表示变化、网络切换、进程终止、任务停止、存储不足、URI 失效、多任务争用和计费网络策略。完整传输的本地长度/摘要、正式文件发布状态与服务端完成状态必须一致。

## 弱网优化从失败阶段开始

延长全部超时并增加重试次数，会让失败请求占用更多连接、线程、电量和用户等待时间。处理弱网前，应先确认失败发生在哪个阶段。

| 阶段 | 可观测信号 | 处理方向 |
| --- | --- | --- |
| Dispatcher 排队 | `dispatcherQueueStart` 到 `dispatcherQueueEnd` | 调整业务优先级、合并请求、隔离大传输 |
| DNS | `dnsStart` 到 `dnsEnd`、`UnknownHostException` | 检查目标网络、Private DNS、自定义解析和候选地址 |
| TCP | `connectStart` 到成功或 `connectFailed` | 保留多地址与 Fast Fallback，按地址族和具体连接路径分析 |
| TLS | `secureConnectStart` 后成功或连接失败 | 检查证书链、主机名、证书固定规则、TLS 协商与连接复用 |
| 请求写入 | 请求体事件、已发送字节 | 检查上传体积、写超时、取消与请求体是否可重新发送 |
| 响应首部 | 请求发送完成到 `responseHeadersStart` | 检查服务端排队、CDN、上行完成时间 |
| 响应体 | 响应体事件、读取字节 | 分页、压缩、断点续传、消费方读取速度 |

这张表用于先定位失败阶段，再选择相应措施。若阶段尚未确定，统一延长超时或统一增加重试只会掩盖原始问题。

### 超时是分阶段预算

OkHttp 的 `connectTimeout` 约束套接字建连阶段，`readTimeout` 和 `writeTimeout` 约束对应的读写操作，`callTimeout` 覆盖整次逻辑调用，包括 DNS、连接、写入、服务端处理和读取。将读超时增大，无法修复 DNS 或 Dispatcher 排队；只设置阶段超时，也无法限制重定向与重试累积后的总等待。

参数应由同一接口在不同网络类别下的耗时分位数、用户交互截止时间和服务端服务等级目标得出。分位数描述一组请求中有多少比例不超过该耗时，例如 P95 是 95% 的样本不超过的值。流式下载与短 API 的读取模型不同，不应共享一组机械常数。

### 区分传输恢复与业务重试

OkHttp 5.4.0 的 `retryOnConnectionFailure` 默认开启。它用于从部分连接故障中恢复，例如失效的池连接或可替代连接路径；这不等于应用可以重新提交任意业务操作。一次 `Call` 内部发生传输恢复后，应用层拦截器若又执行重试，实际尝试次数可能高于业务代码表面上的计数。

HTTP 语义提供起点，但服务端契约仍需确认：

- RFC 9110 把 GET、HEAD 等安全方法，以及 PUT、DELETE，定义为幂等方法。幂等描述重复相同请求的预期服务端效果，不保证响应相同，也不能修复违反规范的服务端实现。
- 非幂等方法不能仅凭“尚未收到响应”就推断服务端没有执行。支付、下单、发消息等 POST 请求需要服务端幂等键、状态查询或事务协议。
- 一次性请求体无法可靠重放。自定义流式 `RequestBody` 若只能写一次，应实现 `isOneShot()`，明确告诉客户端该内容不能重新生成，从而避免不安全的重传。
- `Retry-After` 可表达服务端期望的等待时间。503 的语义见 RFC 9110，429 的使用见 RFC 6585；客户端还要服从用户取消与整次调用截止时间。

一个可审计的重试策略至少包含以下字段：

| 字段 | 要回答的问题 |
| --- | --- |
| 失败阶段 | DNS、连接、TLS、写入、响应首部还是响应体失败 |
| 已发送状态 | 请求头或请求体是否可能已到达服务端 |
| 操作语义 | 方法是否幂等，服务端是否支持幂等键 |
| 请求体能力 | 能否重新生成；是否为 `one-shot`（只能写一次）或 `duplex`（请求与响应可同时流动的双工传输） |
| 服务端提示 | 是否有合法的 `Retry-After` |
| 总预算 | 已尝试多少次，还剩多少调用时间 |
| 网络变化 | 默认网络是否已变化，旧连接路径是否仍适用 |
| 取消状态 | 页面、任务或用户是否已取消 |

重试间隔可以按指数逐次增大，并在每次间隔中加入随机偏移，避免大量客户端同时重试。起始间隔、上限和次数必须来自业务恢复目标、服务端容量与整次截止时间，不存在对所有接口都安全的一组毫秒值。

### 网络状态不能代替端点结果

默认网络为空时，应用可以直接进入离线界面，但切网回调与请求执行仍存在时序差。网络带 `VALIDATED`，业务域名也可能故障；没有 `VALIDATED`，局域网端点仍可能可达。请求结果、端点健康和 `NetworkCapabilities` 应分别记录。

弱网体验还需要数据策略配合：列表可展示有新鲜度标记的缓存，图片可按资源版本选择较小变体，上传可持久化进度并支持断点，非必要模块可以延迟请求。缓存控制和离线写入分别见 [24.6 数据缓存](06-data-caching.md) 与 [24.7 离线优先](07-offline-first.md)。

Android 网络调用不能进入主线程。AOSP `android-17.0.0_r1` 的 `StrictMode` 在启用网络检测和对应终止策略时，由 `onNetwork()` 抛出 `NetworkOnMainThreadException`。UI 线程等待后台 `Future`、锁或 `runBlocking` 不一定触发同一异常，却仍会卡住输入与绘制，排查时要同时检查线程等待关系。

### 流量归因只能回答其公开口径

`TrafficStats.getUidRxBytes()` 与 `getUidTxBytes()` 返回当前 UID 自开机以来、跨所有网络接口累计的网络层字节，适合做进程内前后差值与粗粒度异常发现。在 Android 7.0（API 24）及以上，应用只能查询调用方自身 UID 的这两个计数。它们不提供单请求、单域名或后台移动网络字节；设备重启后归零，不支持时返回 `UNSUPPORTED`。VPN 转发和 CLAT（把应用的 IPv4 流量转换到仅 IPv6 网络的兼容机制）等路径也可能改变归因口径，不能据此做结算或安全审计。历史用量要使用 `NetworkStatsManager` 并遵守权限与用户授权，`setThreadStatsTag()` 只添加归因标签，不会替应用限流、取消或执行后台约束。

网络方案上线时至少比较逻辑操作的 P50、P95、P99 和超时率：它们分别表示 50%、95%、99% 样本不超过的耗时。还要比较每个操作产生的调用数、连接尝试数与总字节，缓存直接或条件命中率，切网或页面退出后的遗留请求，以及后台移动流量和任务完成时效。平均耗时下降而 P99、重试次数或后台字节上升，不能判定优化有效。

## 账号、安全与资源隔离

Cookie、认证头和业务拦截器属于请求策略，连接池本身不会保存某次请求的这些 HTTP 头。登录态和匿名态可以通过不同的派生客户端或请求构造器表达，不必仅因为账号不同就创建全新的连接池。

TLS、代理与套接字配置会参与连接资格判断。使用不同的证书信任管理器（trust manager）、主机名校验器（hostname verifier）、证书或公钥固定器（certificate pinner）、客户端证书、代理或 DNS 时，应让配置差异在各自客户端中清楚可见，并验证 OkHttp 不会复用不兼容的连接。不能为提高复用率而关闭证书校验或放宽主机名验证。

是否使用独立连接池，可按以下条件判断：

- 是否需要独立释放资源或独立进程生命周期。
- 大传输是否经过实测持续影响交互请求，且只隔离 Dispatcher 仍不足。
- 代理、套接字创建器（socket factory）或连接安全策略是否存在不可共享的要求。
- 独立连接池带来的额外建连、TLS 和内存成本是否可接受。

按业务团队各建一个客户端通常没有网络语义，也会让拦截器、认证、缓存和指标配置产生多份版本。应按传输与安全策略管理客户端，而不是按模块目录管理。

## Wi-Fi 选网只保留应用观测边界

默认网络由 Android 连接服务按请求能力、网络评分、用户选择、验证状态和设备配置决定，应用不能用一个 RSSI（Received Signal Strength Indicator，接收信号强度，通常以 dBm 表示）阈值复现系统结果。相关源码链路见 [24.8 Wi-Fi 评分、网络选择与连接切换性能](08-wifi-connectivity-selection.md)。

应用侧应记录：

- 默认 `Network` 身份与变化序号。
- 传输类型、`VALIDATED`、`NOT_METERED`、VPN 和登录门户等取值种类有限的信号；限制取值种类可以控制指标维度数量，避免监控系统负担失控。
- Dispatcher 排队、DNS、每次连接尝试、TLS、请求写入、TTFB 和响应体读取。
- 使用的协议、连接是否复用、缓存命中与失败阶段。

系统侧再结合 `bugreport`（Android 诊断信息包）、`dumpsys connectivity` 与 `dumpsys wifi`（分别导出连接服务和 Wi-Fi 服务状态的命令）、Perfetto 系统追踪和 `logcat` 系统日志还原选网过程。应用指标里的“Wi-Fi”只说明传输类型，不能直接推断计费、互联网可达性或信号质量。

## 工程检查清单

- 是否共享基准 `OkHttpClient`，并明确哪些派生客户端共享连接池。
- 同步 `execute()` 是否由调用方限流，是否错误地把 Dispatcher 参数当成同步限额。
- 是否关闭每个响应体，并测试取消、异常和提前返回路径。
- `EventListener` 是否允许事件缺席、重复和交错，回调中是否避免阻塞工作。
- HTTPDNS 是否保留原主机名、TTL、多地址、网络身份和引导解析策略。
- HTTPDNS 对 Private DNS、VPN、企业分流和隐私承诺的影响是否经过评审。
- 网络状态是否来自回调参数，是否避免把 `VALIDATED` 当作业务端点前置条件。
- 页面取消是否直接作用于所持有的 `Call`，共享请求是否保护其他订阅者。
- 可延迟工作、用户发起的长传输和前台服务是否按 Android 17 规则选择。
- 重试是否同时检查失败阶段、幂等语义、请求体能力、服务端提示和总截止时间。
- 大传输是否根据 `NOT_METERED` 与用户意图决策，而不是只看 Wi-Fi 传输类型。
- 是否用 `MockWebServer` 等测试工具覆盖断连、慢响应体、TLS 失败、重定向和重试，并在设备上覆盖 VPN、Private DNS、IPv6、切网与登录门户。

## 继续阅读

- [24.5 协议优化](05-protocol-optimization.md)：HTTP/2、HTTP/3、gRPC 与协议协商。
- [24.6 数据缓存](06-data-caching.md)：HTTP 缓存、多级缓存与新鲜度。
- [24.7 离线优先](07-offline-first.md)：离线队列、同步和冲突处理。
- [24.8 Wi-Fi 连接与选择](08-wifi-connectivity-selection.md)：系统评分、默认网络与切换。
- [24.14 Android 17 流媒体与本地网络](14-android17-streaming-local-network.md)：局域网能力与 Android 17 访问边界。

## 源码与规范依据

### 当前平台与客户端依据

- [AOSP `android-17.0.0_r1` NetworkCapabilities](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)
- [AOSP `android-17.0.0_r1` ConnectivityManager 与 NetworkCallback](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java)
- [AOSP `android-17.0.0_r1` DnsResolver](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/DnsResolver.java)
- [AOSP `android-17.0.0_r1` StrictMode](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/StrictMode.java)
- [Android DNS Resolver Mainline 模块](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
- [Android 读取网络状态指南](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Android 后台数据传输选择指南](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)
- [Android User-Initiated Data Transfer Job](https://developer.android.com/develop/background-work/background-tasks/uidt)
- [Android WorkManager 长运行 Worker](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running)
- [OkHttp 变更记录](https://github.com/lysine-dev/okhttp/blob/main/CHANGELOG.md)
- [OkHttp 5.4.0 OkHttpClient](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt)
- [OkHttp 5.4.0 Dispatcher](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt)
- [OkHttp 5.4.0 Dns](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
- [OkHttp 5.4.0 EventListener](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
- [OkHttp 5.4.0 ResponseBody](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt)
- [OkHttp 5.4.0 RequestBody](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt)
- [OkHttp 5.4.0 RealConnection](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt)

### 保留的旧版本源码锚点

- [OkHttp 5.3.0 OkHttpClient](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt)
- [OkHttp 5.3.0 Dispatcher](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt)
- [OkHttp 5.3.0 Dns](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
- [OkHttp 5.3.0 EventListener](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
- [OkHttp 5.3.0 ResponseBody](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt)
- [OkHttp 5.3.0 RequestBody](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt)

### HTTP 规范

- [RFC 9110：HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 6585：Additional HTTP Status Codes](https://www.rfc-editor.org/rfc/rfc6585.html)
- [RFC 7233：Range Requests（旧版范围请求规范锚点）](https://www.rfc-editor.org/rfc/rfc7233.html)
