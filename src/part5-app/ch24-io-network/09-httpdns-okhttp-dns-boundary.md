---
title: "HTTPDNS 与 OkHttp Dns 执行边界"
chapter: "24.9"
section: "24.9"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37) / OkHttp 4.x - 5.x"
tags: [network, httpdns, okhttp, dns, latency]
confidence: "medium"
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
- type: reference
  path: https://api.example.com/`
- type: reference
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
last_verified: "2026-06-09"
last_verified_against: "OkHttp 5.x docs + OkHttp source 728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab + DeepResearch 2026-05-14 + Clippings 结构参考"
drafted_date: "2026-05-16"
reviewed_date: "2026-05-16"
reviewed_by: "openclaw-task6"
related_chapters: ["12.1", "12.3", "24.4", "24.5", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "章节深挖/研究素材"
last_task2a_at: "2026-05-16T16:04:00+08:00"
task6_state: "reviewed"
task6_result: "pass-light-edit"
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task2b_result: "fixed"
last_task6_at: "2026-06-25T21:17:30+08:00"
last_task6_audit: "2026-06-25"
task6_l1_l2_fixes: "18"
task6_l3_l4_issues: "0"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-16"
last_task9_at: "2026-05-16T16:30:00+08:00"
last_task9_audit: "2026-06-09"
last_task9_autofix_at: "2026-06-09"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-11
verifier_promoted: "2026-06-25T19:28 Task2B Verifier: both Task6(pass-light-edit) + Task9(auto-fixed) complete, queue clear, promoted to finalized"
---

# HTTPDNS 与 OkHttp Dns 执行边界

HTTPDNS 的风险集中在调用位置。OkHttp 要在建连前把主机名转换成一组
`InetAddress`，`Dns.lookup()` 返回之前，请求还没有进入 TCP 连接阶段。如果在这个
同步回调中再发起 HTTP 请求，一次普通业务请求便多了一段不可忽略的网络等待。

平台基准是 Android 17 / API 37 / `android-17.0.0_r1`，OkHttp 源码基准是
5.4.0 的 `parent-5.4.0` 标签。版本演进部分会提到 OkHttp 4.x，但分析当前实现时
使用 `RealRoutePlanner`、`RouteSelector` 和 `FastFallbackExchangeFinder`，不再用
旧版 `StreamAllocation` 调用链解释 5.x。

24.4 讨论网络架构，24.5 讨论 HTTP 与传输协议。这里聚焦四个问题：

- `Dns.lookup()` 何时执行，哪些请求不会执行它；
- HTTPDNS 查询、缓存和系统解析各自应处于哪条路径；
- 默认网络、指定 `Network`、VPN 与 Private DNS 怎样影响解析结果；
- 如何证明自定义解析改善了业务指标，同时没有削弱兼容性与安全性。

## `Dns.lookup()` 位于路由规划的同步路径

OkHttp 5.4.0 的 [`Dns`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
只有一个同步方法：

```kotlin
fun interface Dns {
    @Throws(UnknownHostException::class)
    fun lookup(hostname: String): List<InetAddress>
}
```

这段接口定义说明了两个限制。调用方要等到整个地址列表返回后才能继续；同一个
`Dns` 实例可能被不同请求并发调用，因此实现中的缓存、刷新去重和失败记录都要满足
并发访问要求。默认的 `Dns.SYSTEM` 调用 `InetAddress.getAllByName(hostname)`。

新连接的主要调用路径如下，用途是定位同步等待发生的位置：

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

[`RealRoutePlanner.planConnect()`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealRoutePlanner.kt)
在列举地址的位置明确注明 `Dns.lookup()` 可能阻塞。
[`RouteSelector`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RouteSelector.kt)
先触发 `dnsStart`，同步调用 `lookup()`，检查结果非空，再触发 `dnsEnd` 并生成
`InetSocketAddress`。空列表会被转换成 `UnknownHostException`。

这条路径还有几个容易遗漏的分支：

- 连接池已有合格连接时，请求可以直接复用连接，不发生 DNS 查询。
- URL 主机本身是 IP 字面量时，`RouteSelector` 直接构造地址，不调用 `Dns`。
- SOCKS 代理使用未解析的 `InetSocketAddress`，主机名交给 SOCKS 代理解析。
- 使用 HTTP 代理时，OkHttp 在这里解析代理主机；目标站点的解析通常由代理完成。
- HTTP/2 连接合并可能复用另一个主机已有的连接，前提仍受证书与路由检查约束。

因此，线上没有 `dnsStart` 不等于解析模块没有生效。连接复用、IP 字面量和代理模式
都可能使该事件缺席。

## 在同步回调中请求 HTTPDNS 的故障形态

下面的代码用于展示应当避免的结构：

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

业务请求必须等待内层 HTTPDNS 请求完成。若 `client` 也安装了这个 `Dns`，解析
HTTPDNS 服务域名时还会再次进入 `lookup()`；即使通过固定地址避开递归，共用
`Dispatcher`、连接池和请求并发配额仍会让解析流量与业务流量相互影响。HTTPDNS
服务变慢、TLS 握手失败或响应解析异常，也会直接延长外层请求的建连前等待。

`connectTimeout` 只约束套接字连接，不是 DNS 超时。OkHttp 的 `callTimeout` 文档把
DNS 计入整次调用期限，但取消一个 call 无法保证任意自定义阻塞代码立即返回。
自定义 `lookup()` 保持本地、短小且可预测，比依赖外层超时更可靠。

OkHttp 自带的
[`DnsOverHttps`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-dnsoverhttps/src/main/kotlin/okhttp3/dnsoverhttps/DnsOverHttps.kt)
也受同步接口约束。5.4.0 源码会异步提交 A、AAAA 请求，再用 `CountDownLatch.await()`
等待这些请求结束。这里的 `enqueue()` 没有使 `lookup()` 变成异步方法。使用 DoH
仍需给解析服务准备独立的引导解析和受控的网络客户端，并接受其网络等待处于路由
规划阶段这一事实。

## Android 17 系统解析器提供了哪些语义

在 `android-17.0.0_r1` 中，
[`InetAddress.getAllByName()`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/net/InetAddress.java)
把默认网络标识交给 Android 的底层解析实现。Android 的
[`com.android.resolv`](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
模块负责 DNS 查询和缓存，并为 `InetAddress.getAllByName()`、
`Network.getAllByName()` 等接口提供系统解析能力。

使用 `Dns.SYSTEM` 可以自然继承这些平台语义：

- 查询跟随系统选出的默认网络；
- 解析器使用当前网络提供的 DNS 配置和系统缓存；
- Android 9 及以上的 Private DNS 配置由系统正确处理；
- VPN、企业网络的分域解析和本地网络名称仍有机会按系统策略工作；
- 网络变化时，平台解析器能按相应网络配置查询。

自定义 HTTPDNS 返回 IP 后，OkHttp 不再通过系统解析器查询该主机。这样会绕过当前
网络的部分 DNS 策略。Android 的
[`LinkProperties`](https://developer.android.com/reference/android/net/LinkProperties)
文档要求应用在 Private DNS 生效时不要发送未加密查询；严格模式还要求查询指定的
Private DNS 主机。面向 Android 9 及以上版本的应用，不应静默用明文自定义 DNS
替代用户或设备管理员设置的加密解析。

兼容性问题不只来自加密方式。企业 VPN 可能通过分域 DNS 返回内网地址，校园网和
酒店网络可能需要先完成门户认证，`.local` 名称可能由系统 mDNS 处理。公共
HTTPDNS 服务通常不掌握这些信息。域名不在经过验证的 HTTPDNS 允许列表内，或当前
网络处于 VPN、门户认证等不适合自定义解析的状态时，应直接使用系统解析。

## Android 17 的 `DnsResolver` 仍不能改变 OkHttp 接口

`DnsResolver` 从 API 29 起提供异步查询。Android 17 / API 37 新增
`DnsResolver(Context, Looper)`，并弃用无上下文的 `getInstance()`；API 37 还增加了
A、AAAA 与 HTTPS 记录的并发查询接口。平台会通过调用者指定的 `Executor` 返回
结果，并支持 `CancellationSignal`。详见
[`DnsResolver` API](https://developer.android.com/reference/android/net/DnsResolver)。

这些能力适合后台预取，也适合需要明确指定 `Network` 的系统 DNS 查询，却不能直接
作为 OkHttp 的异步解析扩展。把回调结果用 `CountDownLatch` 或 `Future.get()` 等待，
只是再次把异步 API 同步化。若应用使用 `DnsResolver` 预热系统或自建缓存，回调应在
后台完成；`Dns.lookup()` 仍只读取已经发布的结果。

`DnsResolver.query()` 返回的 `List<InetAddress>` 不包含可供应用缓存的 TTL。需要
掌握原始 DNS TTL 时，应使用能返回 TTL 的服务契约或解析原始响应，并负责协议解析、
安全校验和版本兼容责任。

## 查询与读取分离

移动端 HTTPDNS 更适合采用两条相互独立的执行路径：

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

这段流程的重点是发布关系。刷新线程完成全部校验后一次性替换不可变快照，
`lookup()` 不遍历正在修改的集合，也不等待磁盘或网络任务。

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

`networkHandle` 区分实际出站网络；没有显式绑定网络时，也应记录刷新开始时的默认网络
标识。内存中的刷新与过期判断使用单调时钟，避免用户修改系统时间造成记录突然失效或
长期不过期。磁盘记录无法跨重启保存 `elapsedRealtime` 的含义，加载时要根据服务端
TTL、接收时的墙上时钟和合理性检查重新计算，不能直接复用旧的单调时钟值。

下面的实现骨架用于说明 `lookup()` 的职责边界，省略了具体存储和地址排序策略：

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

当前请求只会读内存、检查时间和筛选地址。`scheduleRefresh()` 必须立即返回，并按
`CacheKey` 合并并发刷新。缓存没有命中、已经到达强制过期时间或所有地址都不可用时，
代码调用系统解析；它不会把空列表交给 OkHttp。

磁盘快照不宜在每次 `lookup()` 中同步读取。应用可以在进程初始化阶段异步装载并原子
发布；装载完成前使用 `Dns.SYSTEM`。这样能避免慢存储、文件损坏和解密操作进入每个
新连接的路由规划。

## TTL 是有效期，不是刷新建议

HTTPDNS 服务返回的 TTL 决定地址还能被信任多久。工程实现通常需要两个时间点：

- `refreshAtElapsedMs` 到达后启动后台刷新，旧记录在 TTL 内仍可使用；
- `expiresAtElapsedMs` 到达后停止把旧记录作为 HTTPDNS 结果返回。

刷新时间可以带随机抖动，避免大量客户端在同一秒请求解析服务；具体比例应来自服务
契约和线上测量，不宜写成通用常量。超出 TTL 后继续使用旧 IP 属于额外的陈旧数据
策略，必须由域名所有者确认。没有这项约定时，回退系统解析比擅自延长 TTL 更安全。

负结果也不能无限缓存。NXDOMAIN、空响应、服务端错误、响应签名失败和本地解析异常
代表不同原因。只有服务契约明确给出负缓存语义时才缓存对应结果；其余情况记录失败并
使用系统解析。

## HTTPDNS 刷新客户端必须独立

刷新客户端至少应与业务客户端隔离以下配置：

- 不安装业务 `CachedHttpDns`，避免解析服务域名再次进入同一套逻辑；
- 使用独立 `Dispatcher` 和连接池，使解析服务拥塞不会占用业务请求配额；
- 设置与解析服务相符的调用、连接和读取期限；
- 仅访问固定的 HTTPS 解析端点，并执行正常的证书与主机名校验；
- 限制刷新域名集合、并发数和重试次数。

若 HTTPDNS 端点仍通过系统 DNS 引导，刷新客户端可以保留 `Dns.SYSTEM`。若服务方
提供固定引导地址，自定义 `Dns` 只能对端点主机返回这些地址，其他主机仍交给系统
解析。固定地址也要有更新、双栈和撤销方案，不能作为永远有效的常量。

刷新成功后要验证响应属于请求的 hostname，地址列表非空，TTL 可解析，地址族和
地址范围符合该域名的策略。解析响应中的文本 IP 时应直接构造 `InetAddress`，不要
为了把字符串转换为地址再次触发名称查询。

## 指定 `Network` 时要同时约束解析和套接字

默认网络客户端可以使用 `Dns.SYSTEM` 回退。显式绑定 Wi-Fi、蜂窝或其他
`Network` 的客户端则需要更严格的配对：解析要发生在同一个 `Network`，套接字也要
从这个 `Network` 的 `SocketFactory` 创建。

下面的工厂用于表达这种配对关系：

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

`Network.getAllByName()` 在指定网络上解析，
[`Network.getSocketFactory()`](https://developer.android.com/reference/android/net/Network)
创建发往同一网络的套接字。只绑定套接字却使用默认网络 DNS，或在指定网络解析后让
套接字走另一条网络，都会产生分域 DNS、NAT64、VPN 和 CDN 调度不一致的问题。
`Network` 失效后，它的 `SocketFactory` 和既有套接字都不再可用；绑定客户端应随
网络生命周期释放。

HTTPDNS 刷新同样要记录实际出站网络。一个可行做法是为刷新任务创建绑定到目标
`Network` 的独立客户端，并在写缓存前确认该网络仍有效。若刷新过程使用默认网络，
默认网络已经改变的响应不应写入新网络对应的缓存项。

## 网络切换时按网络隔离，不清空全部记录

使用 `registerDefaultNetworkCallback()` 可以接收默认网络变化。`onAvailable()` 之后
平台会继续报告该网络的能力和链路属性；不要在 `onAvailable()` 中同步调用
`getNetworkCapabilities()` 猜测后续状态。等
`onCapabilitiesChanged()` 报告 `NET_CAPABILITY_VALIDATED` 后，再刷新需要联网的
核心域名。

网络切换时推荐执行这些动作：

- 原子更新当前默认网络标识和网络代次；
- 新查找只读取新网络键下的记录；
- 合并同一主机、同一网络上的刷新任务；
- 保留其他网络的缓存项供该网络再次出现时校验，但不跨网络直接复用；
- `onLost()` 只让对应网络的绑定客户端和任务失效，不删除无关网络记录；
- VPN 开启或关闭后重新判断该域名是否仍允许走 HTTPDNS。

这样做不需要在切网瞬间同步清空磁盘，也不会把 Wi-Fi 上得到的 CDN 地址直接当成
蜂窝网络结果。新网络的 HTTPDNS 结果尚未准备好时，当前请求使用该网络的系统解析。

## 失败地址隔离要使用可归因的证据

隔离键采用 `hostname + IP + network`，但不是每种失败都能归因到某个 IP。

适合短时间降低某个地址优先级的证据包括：

- 直连该地址时发生连接超时、拒绝连接或无路由；
- 同一网络下的多次独立连接都在该地址失败，而其他地址成功；
- 服务端控制面明确撤下该地址。

下列信号不应直接判定 IP 不可用：

- TLS 证书或主机名校验失败，原因可能是配置、安全拦截或证书发布问题；
- HTTP 5xx，响应可能来自共享集群，连接本身已经成功；
- 请求超时，耗时可能发生在上传、服务端处理或响应读取阶段；
- 使用 HTTP 代理时的 `connectFailed`，其中的套接字地址属于代理，不是目标站点；
- Fast Fallback 中被取消的竞速连接，它没有产生可归因的连接失败。

OkHttp 本身会记录失败路由并尝试其他候选，自定义隔离层不应设置过长期限，也不应因
一个地址失败而删除整个主机记录。成功连接可以提前清除对应地址的临时降级。所有期限
和触发次数应由故障演练与线上数据确定。

## 不要把 HTTPS URL 改写为 IP

HTTPDNS 只应替换 `Dns` 返回的连接地址，原始 URL 仍保留域名。这样 OkHttp 才能用
原始主机名生成 HTTP `Host`、TLS SNI、证书主机名校验、Cookie 作用域和证书锁定
检查。

把 `https://api.example.com/` 改成 `https://203.0.113.10/`，再手工补一个 `Host`
请求头，会改变 TLS 主机名、连接合并、重定向和 Cookie 语义。关闭
`HostnameVerifier`、信任所有证书或放宽 Network Security Config 来适配这种改写，
会把解析优化变成传输安全漏洞。

HTTPDNS 响应也应视为网络输入。应用至少要校验 HTTPS 端点、响应主机、地址格式和
允许的地址范围。公网业务域名若意外返回回环、链路本地、组播或未指定地址，应拒绝
该结果。企业内网域名可能合法返回私有地址，这类例外需要按域名配置，不能用一条全局
规则覆盖。

## 多地址与 OkHttp 5 Fast Fallback

HTTPDNS 返回单一“最优 IP”会移除连接层的备用路线。只要服务契约允许，结果应保留
经过验证的多个候选和可用的 IPv6、IPv4 地址。候选顺序表达服务端偏好，但 OkHttp 5
启用 Fast Fallback 后不会严格串行等待每个地址超时。

OkHttp 5.4.0 默认启用 `fastFallback`。
[`RouteSelector`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/InetAddressOrder.kt)
在双栈结果中交替排列 IPv6 与 IPv4，并保持每个地址族内部的相对顺序。
[`FastFallbackExchangeFinder`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/FastFallbackExchangeFinder.kt)
每隔 250 ms 启动一个新的 TCP 尝试，某个 TCP 连接成功后取消其他竞速连接，再由胜出
路线完成代理隧道、TLS 等后续步骤。若 TLS 阶段失败，路由规划仍可继续尝试后续方案。

Fast Fallback 缩短坏地址带来的连接等待，却无法缩短 `Dns.lookup()` 本身。地址列表
要在竞速开始前完整返回。HTTPDNS 若只返回 IPv4，也会让 OkHttp 失去双栈选择空间。

## TTL 到期不会驱逐已复用连接

DNS 参与新路线生成，不管理已经进入连接池的连接。一个 HTTP/2 连接可以在 DNS TTL
到期后继续服务请求，只要 OkHttp 判断连接健康且仍符合主机与证书规则。新的 DNS
结果不会自动关闭它。

这通常是期望行为：DNS TTL 约束名称解析记录，不是现有 TCP/TLS 会话的存活时间。
若服务端需要紧急撤下节点，应配合负载均衡、连接排空、服务端关闭连接和客户端版本
策略。频繁执行 `connectionPool.evictAll()` 会损失连接复用，并可能影响共享同一
客户端的无关域名。必须隔离处置时，应让特殊业务使用独立客户端和连接池。

## 系统 DNS、DoH 与 HTTPDNS 的选择

| 方案 | 保留的平台语义 | 主要代价 | 适合的用途 |
| --- | --- | --- | --- |
| `Dns.SYSTEM` | 默认网络、Private DNS、VPN、分域解析和系统缓存 | 调度能力受当前网络 DNS 限制 | 默认方案、兼容方案、长尾域名 |
| DoH | 取决于 DoH 客户端配置，查询传输可加密 | 引导解析、同步等待、企业网络兼容和服务可用性 | 有明确隐私策略并能控制解析服务的场景 |
| HTTPDNS | 由业务服务控制 TTL、候选地址和调度 | 自建缓存、网络隔离、安全、合规与容灾责任 | 少量经过评估的核心公网域名 |

系统 DNS 应是起点，也是自定义解析失败时的兼容路径。HTTPDNS 和 DoH 都不适合未经
评估地覆盖所有域名。应用还要考虑域名是否属于用户数据、解析请求会发送到哪个地区、
服务方保留哪些日志，以及隐私政策是否已经披露。

## 观测不能只依赖 `dnsStart` 与 `dnsEnd`

OkHttp
[`EventListener`](https://lysine.dev/okhttp/features/events/)
提供 DNS、TCP、TLS、请求和响应阶段事件。连接复用时 DNS 与连接事件可能都不存在；
自定义 `lookup()` 抛出异常时，`RouteSelector` 也不会执行正常的 `dnsEnd`。因此，
HTTPDNS 实现还要记录自己的查询结果，不能只用两个事件相减。

建议按 call 关联以下信息：

| 维度 | 建议字段 | 解释 |
| --- | --- | --- |
| 解析决策 | 来源、缓存年龄、网络代次、地址数量、回退原因 | 解释这次返回了哪组地址 |
| 网络阶段 | DNS、TCP、TLS、TTFB、整次调用耗时 | 区分解析与后续等待 |
| 路线结果 | 目标地址族、连接成功或失败、是否复用连接 | 判断地址质量和连接池影响 |
| 网络环境 | 传输类型、是否 validated、是否 VPN、切网代次 | 避免把不同网络混在一起 |
| 安全与合规 | 只记录归一化错误和域名分组 | 不在日志中泄露完整查询与用户信息 |

地址、域名和网络信息可能具有隐私属性。线上日志应采样、脱敏并设置保留期限，不能把
完整 URL、DNS 响应和用户标识一起上报。

## 验证方案从故障分支开始

单元测试可以用假 `Dns`、假时钟和 MockWebServer 验证确定性逻辑：

- TTL 内命中、刷新时间到达、强制过期三种状态；
- 同一个缓存键的并发刷新只发出一项任务；
- 空响应、格式错误、服务端错误都回退系统解析；
- 单地址隔离不会删除同一主机的其他候选；
- 网络代次变化后不读取上一网络的 HTTPDNS 记录；
- 磁盘快照损坏、过期或来自上次启动时不会进入同步路径。

设备与网络实验应覆盖：

- Wi-Fi、蜂窝、双栈、IPv4-only 和 NAT64 网络；
- VPN 开关、Private DNS 严格模式、企业分域 DNS；
- 门户认证前后以及网络从未验证到已验证；
- HTTPDNS 端点超时、证书失败、空响应和错误 TTL；
- 多地址中首个地址不可达，以及 Fast Fallback 开启和关闭；
- 连接池命中与新建连接，确认两者的事件差异。

上线判断使用应用既有的成功率和分位耗时目标，分别比较缓存命中、系统回退、网络类型
和地址族。固定写一个通用 P90/P99 数值或“切网后若干秒”的门槛没有依据；阈值应来自
上线前基线、用户体验目标和故障预算。HTTPDNS 服务完全不可用时，系统解析路径仍应
保持可用，这项故障演练比平均 DNS 耗时下降更有说服力。

## 工程检查清单

- `Dns.lookup()` 是否只执行并发安全的内存读取和筛选；
- 刷新任务是否立即返回，并按主机和网络合并重复请求；
- HTTPDNS 是否使用独立客户端、调度器、连接池和引导解析；
- 缓存键是否包含实际出站网络，网络变化后是否避免跨网络复用；
- TTL 到期后是否停止返回旧记录，陈旧结果策略是否得到服务方确认；
- 缓存为空、过期、全被隔离时是否调用合适网络上的系统解析；
- VPN、Private DNS、内网域名和门户认证是否有明确的禁用或回退策略；
- 是否保留多个有效候选，让 OkHttp 5 的 Fast Fallback 有选择空间；
- 是否只依据可归因的连接失败隔离地址，并忽略竞速取消与 HTTP 5xx；
- HTTPS URL 是否始终保留原主机名，证书与主机名校验是否保持开启；
- 指定 `Network` 时，DNS 与 `SocketFactory` 是否绑定同一个网络；
- 指标是否区分连接复用、解析来源、网络代次和地址族；
- 故障演练是否证明 HTTPDNS 失效时业务仍能回退到系统解析。

## 源码与文档索引

- [Android 17 `InetAddress`](https://android.googlesource.com/platform/libcore/+/refs/tags/android-17.0.0_r1/ojluni/src/main/java/java/net/InetAddress.java)
- [Android DNS Resolver 模块](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
- [Android `DnsResolver` API](https://developer.android.com/reference/android/net/DnsResolver)
- [Android `Network` API](https://developer.android.com/reference/android/net/Network)
- [Android 不安全 DNS 配置风险](https://developer.android.com/privacy-and-security/risks/bad-dns)
- [OkHttp 5.4.0 `Dns`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
- [OkHttp 5.4.0 `RouteSelector`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RouteSelector.kt)
- [OkHttp 5.4.0 `RealRoutePlanner`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealRoutePlanner.kt)
- [OkHttp 5.4.0 Fast Fallback](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/FastFallbackExchangeFinder.kt)
- [OkHttp 5.4.0 `DnsOverHttps`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp-dnsoverhttps/src/main/kotlin/okhttp3/dnsoverhttps/DnsOverHttps.kt)
