---
title: HTTPDNS 与 OkHttp Dns 的执行边界
chapter: '24.7'
section: '24.7'
status: finalized
pipeline_stage: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37) / OkHttp 4.x - 5.x
tags:
- network
- httpdns
- okhttp
- dns
- latency
confidence: high
sources:
- type: reference
  path: Clippings/Android 性能优化 - 缓存优化:冷热端分离+重排序,提升缓存命中率.md
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealRoutePlanner.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RouteSelector.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-dnsoverhttps/src/main/kotlin/okhttp3/dnsoverhttps/DnsOverHttps.kt
- type: aosp
  path: https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/net/InetAddress.java
- type: official
  path: https://source.android.com/docs/core/ota/modular-system/dns-resolver
- type: official
  path: https://developer.android.com/reference/android/net/LinkProperties
- type: official
  path: https://developer.android.com/reference/android/net/DnsResolver
- type: official
  path: https://developer.android.com/reference/android/net/Network
- type: official
  path: https://developer.android.com/reference/android/net/ConnectivityManager
- type: example
  path: https://api.example.com/`
- type: example
  path: https://203.0.113.10/`
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/InetAddressOrder.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/FastFallbackExchangeFinder.kt
- type: reference
  path: https://lysine.dev/okhttp/features/events/
- type: official
  path: https://developer.android.com/privacy-and-security/risks/bad-dns
- type: aosp
  path: system/dns-resolver
last_verified: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1 and Android API 37 DnsResolver, Network and LinkProperties docs current through 2026-08-15; OkHttp 5.4.0 source
related_chapters:
- '12.1'
- '12.2'
- '24.3'
- '24.4'
- '26.1'
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_review_finalize_at: '2026-08-15T11:23:47+08:00'
last_review_finalize_run_id: 20260815-112347-gracker-writing-review
last_draft_polish_at: '2026-08-15T11:23:47+08:00'
last_draft_polish_run_id: 20260815-112347-gracker-writing
---

# HTTPDNS 与 OkHttp Dns 的执行边界

本文所说的 HTTPDNS，是指应用通过 HTTP 或 HTTPS 解析服务取得“域名到 IP 地址”的结果。OkHttp 通过自定义 `Dns` 接入这组地址，解析服务请求本身仍是普通 HTTP/HTTPS 请求。

OkHttp 要在建立连接前把主机名转换成一组 `InetAddress`，也就是 Java 表示 IP 地址的对象。`Dns.lookup()` 返回之前，请求还没有开始 TCP 连接。如果在这个同步回调中再请求 HTTPDNS，业务请求必须先等待解析服务的网络请求，随后才能连接目标服务。

平台基准是 Android 17 / API 37 / `android-17.0.0_r1`，OkHttp 源码基准是 5.4.0 的 `parent-5.4.0` 标签。OkHttp 4.x 的旧实现使用 `StreamAllocation` 等类；5.x 应按 `RealRoutePlanner`、`RouteSelector` 和 `FastFallbackExchangeFinder` 分析路由规划、地址选择与并发连接，不能套用旧调用路径。

24.3 讨论网络架构，24.4 讨论 HTTP 与传输协议。理解 HTTPDNS 的执行边界，需要区分四件事：

- `Dns.lookup()` 何时执行，哪些请求不会执行它；
- HTTPDNS 查询、缓存和系统解析各自应处于哪条路径；
- 默认网络、指定 `Network`、VPN 与 Private DNS 怎样影响解析结果；
- 如何证明自定义解析改善了业务指标，同时没有削弱兼容性与安全性。

## `Dns.lookup()` 位于路由规划的同步路径

OkHttp 5.4.0 的 [`Dns`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt) 只有一个同步方法：

```kotlin
fun interface Dns {
    @Throws(UnknownHostException::class)
    fun lookup(hostname: String): List<InetAddress>
}
```

这段接口定义带来两个限制。调用方要等到整个地址列表返回后才能继续；同一个 `Dns` 实例可能被多个请求同时调用，因此缓存、重复刷新合并和失败记录都要支持并发访问。默认实现 `Dns.SYSTEM` 调用 `InetAddress.getAllByName(hostname)`。

这条新连接调用路径标出了同步等待发生的位置：

```text
RealCall
  → RealRoutePlanner.plan()
    → RealRoutePlanner.planConnect()
      → RouteSelector.next()
        → resetNextInetSocketAddress(proxy)
          → address.dns.lookup(socketHost)
          → 生成一组 Route
  → ExchangeFinder 选择或连接 Route
```

[`RealRoutePlanner.planConnect()`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealRoutePlanner.kt) 在列举地址的位置注明 `Dns.lookup()` 可能阻塞。[`RouteSelector`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RouteSelector.kt) 先触发 `dnsStart`，同步调用 `lookup()`，确认结果非空，再触发 `dnsEnd` 并生成 `InetSocketAddress`。空列表会被转换成 `UnknownHostException`，表示没有可供连接的地址。

这条路径还包含几个分支：

- 连接池已有合格连接时，请求直接复用连接，不执行 DNS 查询。
- URL 主机本身是 IP 字面量，即直接写出的 IPv4 或 IPv6 地址时，`RouteSelector` 直接构造地址，不调用 `Dns`。
- SOCKS 是一种由代理服务器代为建立连接的协议。使用 SOCKS 代理时，OkHttp 保留未解析的 `InetSocketAddress`，把目标主机名交给代理解析。
- 使用 HTTP 代理时，OkHttp 在这条路径中解析代理服务器的主机名；目标站点通常由代理解析。
- HTTP/2 连接合并允许证书和路由条件相容的不同主机复用同一条连接，因此也可能没有新的 DNS 查询。

生产日志中没有 `dnsStart`，不能据此断定解析模块没有生效。连接复用、IP 字面量和代理模式都可能让该事件不出现。

## 在同步回调中请求 HTTPDNS 的故障形态

这段代码展示一种应当避免的结构：

```kotlin
class BlockingHttpDns(
    private val client: OkHttpClient,
    private val endpoint: HttpUrl,
) : Dns {
    override fun lookup(hostname: String): List<InetAddress> {
        val request = Request.Builder()
            .url(
                endpoint.newBuilder()
                    .addQueryParameter("host", hostname)
                    .build(),
            )
            .build()

        return client.newCall(request).execute().use { response ->
            parseAddresses(response)
        }
    }
}
```

业务请求必须等待内层 HTTPDNS 请求完成。若 `client` 也安装了这个 `Dns`，解析 HTTPDNS 服务域名时会再次进入 `lookup()`，形成递归调用。即使通过固定地址避开递归，共用 `Dispatcher`、连接池和请求并发配额仍会让解析流量与业务流量相互影响。`Dispatcher` 是 OkHttp 管理异步请求并发和排队的调度器。HTTPDNS 服务变慢、TLS 握手失败或响应解析异常，都会延长外层业务请求在建连前的等待。

`connectTimeout` 只约束套接字连接，不是 DNS 超时。OkHttp 的 `callTimeout` 把 DNS 计入整次调用期限，但取消一个 `Call` 无法保证任意自定义阻塞代码立即返回。自定义 `lookup()` 应只执行耗时可控的本地操作，不能依赖外层超时终止网络查询。

OkHttp 自带的 [`DnsOverHttps`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-dnsoverhttps/src/main/kotlin/okhttp3/dnsoverhttps/DnsOverHttps.kt) 也受同步接口约束。DoH（DNS over HTTPS）把 DNS 查询放入 HTTPS 请求。5.4.0 源码会异步提交 A 记录和 AAAA 记录查询，再用 `CountDownLatch.await()` 等待全部请求结束；A 记录返回 IPv4 地址，AAAA 记录返回 IPv6 地址。`CountDownLatch` 是让当前线程等待一组任务完成的同步工具，所以 `enqueue()` 没有把 `lookup()` 变成异步方法。DoH 仍需独立的引导解析来找到解析服务本身，并使用配置受控的专用客户端；它的网络等待仍发生在 OkHttp 路由规划期间。

## Android 17 系统解析器提供了哪些语义

在 `android-17.0.0_r1` 中，[`InetAddress.getAllByName()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/net/InetAddress.java) 把默认网络标识交给 Android 的系统解析实现。[`com.android.resolv`](https://source.android.com/docs/core/ota/modular-system/dns-resolver) 是可独立更新的 DNS Resolver 模块，负责 DNS 查询和缓存，并为 `InetAddress.getAllByName()`、`Network.getAllByName()` 等接口提供系统解析能力。

使用 `Dns.SYSTEM` 可以保留这些平台语义：

- 查询跟随系统选出的默认网络；
- 解析器使用当前网络提供的 DNS 配置和系统缓存；
- Android 9 及以上的 Private DNS 配置由系统处理；Private DNS 是 Android 对 DNS-over-TLS 加密解析的系统设置；
- VPN、企业网络的分域解析和本地网络名称仍能按系统策略工作；分域解析会按域名后缀选择不同的 DNS 服务器；
- 网络变化时，平台解析器能按相应网络配置查询。

自定义 HTTPDNS 返回 IP 后，OkHttp 不再通过系统解析器查询该主机，因此会绕过当前网络的部分 DNS 策略。Android 的 [`LinkProperties`](https://developer.android.com/reference/android/net/LinkProperties) 文档要求应用在 Private DNS 生效时不要发送未加密查询；严格模式还要求把查询发给指定的 Private DNS 主机，并验证其证书。面向 Android 9 及以上版本的应用，不应静默用明文自定义 DNS 替代用户或设备管理员设置的加密解析。

企业 VPN 可能通过分域 DNS 返回内网地址，校园网和酒店网络可能要求先完成登录门户认证，`.local` 名称还可能由 mDNS（multicast DNS，在本地网络内通过组播解析名称）处理。公共 HTTPDNS 服务通常没有这些网络内部信息。域名不在经过验证的 HTTPDNS 允许列表内，或当前网络处于 VPN、门户认证等不适合自定义解析的状态时，应直接使用系统解析。

## Android 17 的 `DnsResolver` 仍不能改变 OkHttp 接口

`DnsResolver` 从 API 29 起提供异步查询。Android 17 / API 37 新增 `DnsResolver(Context, Looper)`，并弃用无上下文的 `getInstance()`；API 37 还增加了同时查询 A、AAAA 与 HTTPS DNS 记录的接口。这里的 HTTPS 记录是 DNS 记录类型，用来携带服务端点与连接参数，不是一次 HTTPS 请求。平台通过调用者指定的 `Executor` 调度回调线程，并用 `CancellationSignal` 接收取消信号。详见 [`DnsResolver` API](https://developer.android.com/reference/android/net/DnsResolver)。

这些能力适合后台预取，也适合明确指定 `Network` 的系统 DNS 查询，却不能把 OkHttp 的同步 `Dns` 接口改成异步接口。用 `CountDownLatch` 或 `Future.get()` 等待回调结果，只是让异步 API 再次阻塞当前线程。若应用使用 `DnsResolver` 预取地址或填充自建缓存，查询与回调都应在后台完成；`Dns.lookup()` 仍只读取已经发布的结果。

`DnsResolver.query()` 返回的 `List<InetAddress>` 不含可供应用缓存的 TTL。TTL（time to live）是 DNS 记录允许缓存的有效期。需要读取原始 TTL 时，应使用能返回 TTL 的服务契约或解析原始 DNS 响应，并承担协议解析、安全校验和版本兼容责任。

## 查询与读取分离

移动端 HTTPDNS 适合采用两条相互独立的执行路径：后台任务负责网络查询与校验，`Dns.lookup()` 只读内存中的已完成结果。

```text
后台刷新
  触发条件
    → 对 hostname + network 做并发去重
    → 独立客户端请求 HTTPDNS
    → 校验主机名、地址、TTL 与响应来源
    → 原子发布不可变快照

OkHttp 路由规划
  Dns.lookup(hostname)
    → 读取当前 network 对应的内存快照
    → 去掉已过期或暂时不可用的地址
    → 异步请求刷新
    → 没有可用地址时调用系统解析
```

刷新线程完成全部校验后，一次性替换不可变快照。这里的“快照”是一份发布后不再修改的地址记录集合；“原子发布”保证读取方只能看到完整的旧集合或新集合，不会读到写了一半的状态。`lookup()` 不遍历正在修改的集合，也不等待磁盘或网络任务。流程图中的 `network` 指产生这份结果时使用的 Android `Network`。

缓存记录至少需要下列信息：

```kotlin
data class CacheKey(
    val hostname: String,
    val networkHandle: Long?,
)

data class HttpDnsRecord(
    val addresses: List<InetAddress>,
    val receivedAtEpochMs: Long,
    val ttlMillis: Long,
    val refreshAtElapsedMs: Long,
    val expiresAtElapsedMs: Long,
    val source: Source,
)
```

`networkHandle` 区分实际出站网络；没有显式绑定网络时，也应记录刷新开始时的默认网络标识。网络句柄只适合关联该网络对象的存活期，不能当作跨设备重启的永久标识。内存中的刷新与过期判断使用单调时钟，它只随设备运行时间前进，不受用户改时间或系统校时影响。磁盘记录无法跨重启保留 `elapsedRealtime` 的时间基准，加载时要根据服务端 TTL、接收时的墙上时钟和合理性检查重新计算，不能直接复用旧的单调时钟值。墙上时钟是日历时间，可能被用户或系统调整。

这段实现骨架说明 `lookup()` 的职责边界，省略具体存储和地址排序策略：

```kotlin
class CachedHttpDns(
    private val records: AtomicReference<Map<CacheKey, HttpDnsRecord>>,
    private val networkKey: () -> Long?,
    private val quarantine: IpQuarantine,
    private val scheduleRefresh: (CacheKey) -> Unit,
    private val fallback: Dns = Dns.SYSTEM,
    private val elapsedRealtimeMs: () -> Long = SystemClock::elapsedRealtime,
) : Dns {
    override fun lookup(hostname: String): List<InetAddress> {
        if (hostname.isBlank()) {
            throw UnknownHostException("hostname is empty")
        }

        val now = elapsedRealtimeMs()
        val key = CacheKey(hostname.lowercase(Locale.US), networkKey())
        val record = records.get()[key]

        if (record == null || now >= record.refreshAtElapsedMs) {
            scheduleRefresh(key) // 只投递任务，并按 key 合并重复刷新。
        }

        val cached = record
            ?.takeIf { now < it.expiresAtElapsedMs }
            ?.addresses
            .orEmpty()
            .filterNot { quarantine.isBlocked(key, it, now) }

        return cached.ifEmpty { fallback.lookup(hostname) }
    }
}
```

当前请求只读内存、检查时间并筛选地址。`scheduleRefresh()` 必须立即返回，并按 `CacheKey` 合并同时到来的刷新。缓存未命中、已到达强制过期时间或所有地址都不可用时，代码调用系统解析；它不会把空列表交给 OkHttp。

磁盘快照不应在每次 `lookup()` 中同步读取。应用可在进程初始化阶段异步装载并原子发布；装载完成前使用 `Dns.SYSTEM`。这样能避免慢存储、文件损坏和解密操作进入每个新连接的路由规划。

## TTL 约束记录的最长有效期

HTTPDNS 服务返回的 TTL 决定地址还能被信任多久。工程实现通常需要两个时间点：

- `refreshAtElapsedMs` 到达后启动后台刷新，旧记录在 TTL 内仍可使用；
- `expiresAtElapsedMs` 到达后停止把旧记录作为 HTTPDNS 结果返回。

刷新时间可以加入随机偏移，让大量客户端不要在同一秒请求解析服务；偏移范围应来自服务约定和生产环境测量，不能写成适用于所有域名的常量。超出 TTL 后继续使用旧 IP 属于额外的陈旧数据策略，必须由域名所有者确认。没有这项约定时，应停止返回旧 HTTPDNS 结果并使用系统解析。

失败结果也不能无限缓存。NXDOMAIN 表示负责该域名最终记录的权威 DNS 服务器回答“该域名不存在”，它与空响应、服务端错误、响应签名失败和本地解析异常不是同一种结果。只有服务约定明确给出负缓存规则时，才缓存对应失败结果；其余情况记录失败并使用系统解析。

## HTTPDNS 刷新客户端必须独立

刷新客户端至少应在这些方面与业务客户端分开：

- 不安装业务 `CachedHttpDns`，避免解析服务域名再次进入同一套逻辑；
- 使用独立 `Dispatcher` 和连接池，使解析服务拥塞不会占用业务请求配额；
- 设置与解析服务相符的调用、连接和读取期限；
- 仅访问固定的 HTTPS 解析端点，并执行正常的证书与主机名校验；
- 限制刷新域名集合、并发数和重试次数。

若 HTTPDNS 端点仍通过系统 DNS 完成首次解析，刷新客户端可以保留 `Dns.SYSTEM`。若服务方提供固定的引导地址，自定义 `Dns` 只能对解析端点主机返回这些地址，其他主机仍交给系统解析。固定地址也要支持更新、IPv4/IPv6 双栈和撤销，不能作为永久有效的常量。

刷新成功后要验证响应属于请求的 `hostname`，地址列表非空，TTL 可解析，地址族（IPv4 或 IPv6）和地址范围符合该域名的策略。解析响应中的文本 IP 时应直接构造 `InetAddress`，不要为了把字符串转换为地址再次触发名称查询。

## 指定 `Network` 时要同时约束解析和套接字

默认网络客户端可以使用 `Dns.SYSTEM`。显式绑定 Wi-Fi、蜂窝或其他 `Network` 的客户端需要严格配对：解析要发生在同一个 `Network`，套接字也要从这个 `Network` 的 `SocketFactory` 创建。

这个工厂把解析与套接字绑定到同一个网络：

```kotlin
fun OkHttpClient.onNetwork(network: Network): OkHttpClient {
    val networkDns = Dns { hostname ->
        network.getAllByName(hostname).toList()
    }

    return newBuilder()
        .dns(networkDns)
        .socketFactory(network.socketFactory)
        .build()
}
```

`Network.getAllByName()` 在指定网络上解析，[`Network.getSocketFactory()`](https://developer.android.com/reference/android/net/Network) 创建发往同一网络的套接字。只绑定套接字却使用默认网络 DNS，或在指定网络解析后让套接字经过另一条网络，都会引发分域 DNS、NAT64、VPN 和 CDN 选择不一致。NAT64 让仅有 IPv6 的网络访问 IPv4 服务，所需的合成地址与当前网络有关；CDN（content delivery network，内容分发网络）也可能按查询来源返回不同节点。`Network` 断开后，它的 `SocketFactory` 以及过去或将来创建的套接字都会失效；绑定客户端应随该网络释放。

HTTPDNS 刷新同样要记录实际出站网络。可为刷新任务创建绑定到目标 `Network` 的独立客户端，并在写缓存前确认该网络仍有效。若刷新过程使用默认网络，默认网络已经改变的响应不应写入新网络对应的缓存项。

## 网络切换后只使用对应网络的记录

`registerDefaultNetworkCallback()` 可以接收默认网络变化，调用它需要 `ACCESS_NETWORK_STATE` 权限。`onAvailable()` 之后，平台会继续通过回调报告该网络的能力和链路属性；不要在 `onAvailable()` 中同步调用 `getNetworkCapabilities()`，因为网络状态可能在回调与查询之间变化。等 `onCapabilitiesChanged()` 报告 `NET_CAPABILITY_VALIDATED`，也就是系统探测确认公网可达后，再刷新需要联网的核心域名。

网络代次是应用为每次默认网络变化分配的递增序号。网络切换时执行这些动作：

- 原子更新当前默认网络标识和网络代次；
- 新查找只读取新网络键下的记录；
- 合并同一主机、同一网络上的刷新任务；
- 保留其他网络的缓存项供该网络再次出现时校验，但不跨网络直接复用；
- `onLost()` 只让对应网络的绑定客户端和任务失效，不删除无关网络记录；
- VPN 开启或关闭后重新判断该域名是否仍允许走 HTTPDNS。

这些动作不需要在切网瞬间同步清空磁盘，也不会把 Wi-Fi 上得到的 CDN 地址直接当成蜂窝网络结果。新网络的 HTTPDNS 结果尚未准备好时，当前请求使用该网络的系统解析。

## 失败地址隔离要使用可归因的证据

这里的“地址隔离”是暂时降低某个地址的优先级或停止选择它。隔离键采用 `hostname + IP + network`，因为同一地址可能只在特定主机或网络上失败；并非每种失败都能归因到某个 IP。

适合短时间降低某个地址优先级的证据包括：

- 直连该地址时发生连接超时、拒绝连接或无路由；
- 同一网络下的多次独立连接都在该地址失败，而其他地址成功；
- 服务端管理系统明确标记该地址已经下线。

下列信号不应直接判定 IP 不可用：

- TLS 证书或主机名校验失败，原因可能是配置、安全拦截或证书发布问题；
- HTTP 5xx，响应可能来自共享集群，连接本身已经成功；
- 请求超时，耗时可能发生在上传、服务端处理或响应读取阶段；
- 使用 HTTP 代理时的 `connectFailed`，其中的套接字地址属于代理，不是目标站点；
- Fast Fallback（错开启动多个候选地址的连接尝试）中被取消的竞速连接，它没有产生可归因的连接失败。

OkHttp 本身会记录失败路由并尝试其他候选，自定义隔离层不应设置过长期限，也不应因一个地址失败而删除整个主机记录。成功连接可以提前恢复对应地址的优先级。隔离期限和触发次数应由故障演练与生产数据确定。

## 不要把 HTTPS URL 改写为 IP

HTTPDNS 只应替换 `Dns` 返回的连接地址，原始 URL 仍保留域名。OkHttp 会用原始主机名生成 HTTP `Host` 请求头；TLS 的 SNI（Server Name Indication）也会在握手中携带目标主机名。证书主机名校验、Cookie 适用域和证书锁定同样依赖这个名称。证书锁定要求服务端证书或公钥匹配应用预置值，用来限制可被接受的证书范围。

把 `https://api.example.com/` 改成 `https://203.0.113.10/`，再手工补一个 `Host` 请求头，会改变 TLS 主机名、连接合并、重定向和 Cookie 规则。`example.com` 与 `203.0.113.0/24` 都是文档示例保留值，不是可访问的业务端点。关闭 `HostnameVerifier`、信任所有证书，或放宽 Network Security Config 来适配 URL 改写，都会削弱 HTTPS 校验。Network Security Config 是 Android 用 XML 配置受信任 CA 或证书、明文流量和证书锁定等网络安全规则的机制。

HTTPDNS 响应也属于不可信网络输入。应用至少要校验 HTTPS 端点、响应主机、地址格式和允许的地址范围。公网业务域名若返回回环地址（只指向本机）、链路本地地址（只在当前二层网络有效）、组播地址或未指定地址，应拒绝该结果。企业内网域名可能合法返回私有地址，这类例外需要按域名配置，不能用一条全局规则覆盖。

## 多地址与 OkHttp 5 Fast Fallback

HTTPDNS 只返回一个“最优 IP”会移除连接层的备用路线。只要服务约定允许，结果应保留经过验证的多个候选，以及可用的 IPv6、IPv4 地址。候选顺序表达服务端偏好，但 OkHttp 5 启用 Fast Fallback 后不会严格串行等待每个地址超时。

OkHttp 5.4.0 默认启用 `fastFallback`。[`RouteSelector`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/InetAddressOrder.kt) 所用的地址排序逻辑位于链接目标 `InetAddressOrder.kt`，它在双栈结果中交替排列 IPv6 与 IPv4，并保持每个地址族内部的相对顺序。[`FastFallbackExchangeFinder`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/FastFallbackExchangeFinder.kt) 每隔 250 ms 启动一个新的 TCP 尝试。某个 TCP 连接成功后，它会取消其他竞速连接，再由胜出路线完成代理隧道、TLS 等步骤；若 TLS 阶段失败，路由规划仍可尝试后续方案。

Fast Fallback 能缩短坏地址带来的连接等待，却无法缩短 `Dns.lookup()` 本身。地址列表要在竞速开始前完整返回。HTTPDNS 若只返回 IPv4，也会让 OkHttp 失去双栈选择空间。

## TTL 到期不会驱逐已复用连接

DNS 参与新路线生成，不管理已经进入连接池的连接。一个 HTTP/2 连接可以在 DNS TTL 到期后继续服务请求，只要 OkHttp 判断连接健康且仍符合主机与证书规则。新的 DNS 结果不会自动关闭它。

DNS TTL 约束名称解析记录，不约束现有 TCP/TLS 会话的存活时间。若服务端需要紧急撤下节点，应配合负载均衡、连接排空、服务端关闭连接和客户端版本策略。连接排空是停止把新请求分配给待下线节点，同时等待已有请求结束。频繁执行 `connectionPool.evictAll()` 会损失连接复用，并影响共享同一客户端的无关域名。需要单独处置时，应让特殊业务使用独立客户端和连接池。

## 系统 DNS、DoH 与 HTTPDNS 的选择

| 方案 | 保留的平台语义 | 主要代价 | 适合的用途 |
| --- | --- | --- | --- |
| `Dns.SYSTEM` | 默认网络、Private DNS、VPN、分域解析和系统缓存 | 地址调度受当前网络 DNS 限制 | 默认方案、兼容方案、非核心域名 |
| DoH | 取决于 DoH 客户端配置，查询传输可加密 | 引导解析、同步等待、企业网络兼容和服务可用性 | 有明确隐私策略并能控制解析服务的场景 |
| HTTPDNS | 由业务服务控制 TTL、候选地址和调度 | 自建缓存、网络隔离、安全、合规，以及解析服务故障时仍保持可用的责任 | 少量经过评估的核心公网域名 |

系统 DNS 应作为默认选择，也是自定义解析失败时的兼容路径。HTTPDNS 和 DoH 都不适合未经评估地覆盖所有域名。应用还要确认域名是否属于用户数据、解析请求会发送到哪个地区、服务方保留哪些日志，以及隐私政策是否已经披露这些处理方式。

## 观测不能只依赖 `dnsStart` 与 `dnsEnd`

OkHttp [`EventListener`](https://lysine.dev/okhttp/features/events/) 提供 DNS、TCP、TLS、请求和响应阶段事件。连接复用时，DNS 与连接事件可能都不存在；自定义 `lookup()` 抛出异常时，`RouteSelector` 也不会执行正常的 `dnsEnd`。HTTPDNS 实现还要记录自己的查询结果，不能只用两个事件相减。

一次 OkHttp `Call` 表示一项逻辑请求，内部可能包含重试、重定向或认证产生的多次网络交换。应按 `Call` 关联以下信息：

| 观察对象 | 建议字段 | 解释 |
| --- | --- | --- |
| 解析决策 | 来源、缓存年龄、网络代次、地址数量、改用系统解析的原因 | 解释这次返回了哪组地址 |
| 网络阶段 | DNS、TCP、TLS、TTFB、整次调用耗时 | TTFB（time to first byte）是发出请求后等到首个响应字节的时间，用它区分解析与后续等待 |
| 路线结果 | 目标地址族、连接成功或失败、是否复用连接 | 判断地址质量和连接池影响 |
| 网络环境 | 传输类型、是否有 `NET_CAPABILITY_VALIDATED`、是否 VPN、网络代次 | 避免把不同网络混在一起 |
| 安全与合规 | 只记录归类后的错误码和域名分组 | 不在日志中泄露完整查询与用户信息 |

地址、域名和网络信息可能具有隐私属性。生产日志应采样、脱敏并设置保留期限，不能把完整 URL、DNS 响应和用户标识一起上传。

## 验证方案从故障分支开始

单元测试可以用测试专用的 `Dns`、可控时钟和 MockWebServer 验证确定性逻辑。MockWebServer 是 OkHttp 提供的本地测试服务器，可按脚本返回响应并记录请求：

- TTL 内命中、刷新时间到达、强制过期三种状态；
- 同一个缓存键的并发刷新只发出一项任务；
- 空响应、格式错误、服务端错误都改用系统解析；
- 单地址隔离不会删除同一主机的其他候选；
- 网络代次变化后不读取上一网络的 HTTPDNS 记录；
- 磁盘快照损坏、过期或来自上次启动时不会进入同步路径。

设备与网络实验应覆盖：

- Wi-Fi、蜂窝、双栈、仅 IPv4 和 NAT64 网络；
- VPN 开关、Private DNS 严格模式、企业分域 DNS；
- 门户认证前后以及网络从未验证到已验证；
- HTTPDNS 端点超时、证书失败、空响应和错误 TTL；
- 多地址中首个地址不可达，以及 Fast Fallback 开启和关闭；
- 连接池命中与新建连接，确认两者的事件差异。

发布判断应使用应用既有的成功率和分位耗时目标，分别比较缓存命中、系统解析、网络类型和地址族。P90 与 P99 分别表示 90% 和 99% 的样本不超过该耗时。不能预设一组通用 P90/P99 数值或“切网后若干秒”的门槛；阈值应来自改造前实测值、用户体验目标和允许的失败额度。还要通过故障演练确认：HTTPDNS 服务完全不可用时，系统解析路径仍保持可用。这个结果比只看到平均 DNS 耗时下降更能说明方案可发布。

## 工程检查清单

- `Dns.lookup()` 是否只执行并发安全的内存读取和筛选；
- 刷新任务是否立即返回，并按主机和网络合并重复请求；
- HTTPDNS 是否使用独立客户端、调度器、连接池和引导解析；
- 缓存键是否包含实际出站网络，网络变化后是否避免跨网络复用；
- TTL 到期后是否停止返回旧记录，陈旧结果策略是否得到服务方确认；
- 缓存为空、过期、全被隔离时是否调用合适网络上的系统解析；
- VPN、Private DNS、内网域名和门户认证是否有明确的禁用条件或系统解析策略；
- 是否保留多个有效候选，让 OkHttp 5 的 Fast Fallback 有选择空间；
- 是否只依据可归因的连接失败隔离地址，并忽略竞速取消与 HTTP 5xx；
- HTTPS URL 是否始终保留原主机名，证书与主机名校验是否保持开启；
- 指定 `Network` 时，DNS 与 `SocketFactory` 是否绑定同一个网络；
- 指标是否区分连接复用、解析来源、网络代次和地址族；
- 故障演练是否证明 HTTPDNS 失效时业务仍能改用系统解析。

## 参考与验证

- [Android 17 `InetAddress`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/net/InetAddress.java)
- [Android DNS Resolver 模块](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
- [Android `DnsResolver` API](https://developer.android.com/reference/android/net/DnsResolver)
- [Android `Network` API](https://developer.android.com/reference/android/net/Network)
- [Android `LinkProperties` API](https://developer.android.com/reference/android/net/LinkProperties)
- [Android `ConnectivityManager` API](https://developer.android.com/reference/android/net/ConnectivityManager)
- [Android 不安全 DNS 配置风险](https://developer.android.com/privacy-and-security/risks/bad-dns)
- [OkHttp 5.4.0 `Dns`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
- [OkHttp 5.4.0 `RouteSelector`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RouteSelector.kt)
- [OkHttp 5.4.0 `RealRoutePlanner`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealRoutePlanner.kt)
- [OkHttp 5.4.0 Fast Fallback](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/FastFallbackExchangeFinder.kt)
- [OkHttp 5.4.0 `DnsOverHttps`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-dnsoverhttps/src/main/kotlin/okhttp3/dnsoverhttps/DnsOverHttps.kt)
