---
title: 移动网络架构、连接与容灾
chapter: '24.3'
section: '24.3'
status: finalized
pipeline_stage: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags:
- okhttp
- connection-pool
- httpdns
- weak-network
- dispatcher
- network
- cronet
- http3
- dns
- performance
confidence: high
sources:
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/main/CHANGELOG.md
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/data-transfer-options
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/DnsResolver.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/StrictMode.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework-t/src/android/net/TrafficStats.java
- type: official
  path: https://source.android.com/docs/core/ota/modular-system/dns-resolver
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/reading-network-state
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/uidt
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt
- type: reference
  path: https://www.rfc-editor.org/rfc/rfc9110.html
- type: reference
  path: https://www.rfc-editor.org/rfc/rfc6585.html
- type: reference
  path: https://www.rfc-editor.org/rfc/rfc7233.html
- type: aosp
  path: system/dns-resolver
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/network-access-optimization
- type: official
  path: https://developer.android.com/develop/connectivity/cronet
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/CronetEngine.Builder
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/NetworkQualityRttListener
- type: official
  path: https://developer.android.com/privacy-and-security/security-config
- type: official
  path: https://developer.android.com/privacy-and-security/security-ssl
- type: official
  path: https://developer.android.com/topic/performance/vitals/bg-network-usage
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/reference/android/net/http/HttpEngine
- type: official
  path: https://developer.android.com/reference/android/net/http/FinishedRequestTimings
- type: official
  path: https://developer.android.com/topic/performance/measuring-performance
- type: official
  path: https://developer.android.com/topic/performance/benchmarking/benchmarking-overview
- type: official
  path: https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt#L750-L766
- type: aosp
  path: /Users/gracker/Android/sources/android-35/android/net/DnsResolver.java
- type: aosp
  path: /Users/gracker/Android/sources/android-35/android/net/NetworkCapabilities.java
- type: aosp
  path: /Users/gracker/Android/sources/android-35/android/net/TrafficStats.java
- type: aosp
  path: /Users/gracker/Android/sources/android-30/com/android/server/ConnectivityService.java
- type: clipping-structure
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md
- type: clipping-structure
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md
last_verified: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1; Android Developers network state, background transfer, UIDT and long-running WorkManager docs; OkHttp 5.4.0 source and changelog; RFC 9110, RFC 6585 and RFC 7233
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
related_chapters:
- '24.4'
- '12.1'
- '24.7'
- '26.11'
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch24-io-network/08-io-network-case-studies.md
- src/part5-app/ch24-io-network/14-network-request-performance-playbook.md
- src/part5-app/ch24-io-network/04-network-architecture.md
- src/part5-app/ch24-io-network/13-network-performance-baseline.md
last_review_finalize_at: '2026-08-15T10:05:57+08:00'
last_review_finalize_run_id: 20260815-100557-gracker-writing-review
last_draft_polish_at: '2026-08-15T10:05:57+08:00'
last_draft_polish_run_id: 20260815-100557-gracker-writing
---

# 移动网络架构、连接与容灾

移动网络会在 Wi-Fi、蜂窝、VPN 和受限网络之间变化。应用先通过 ConnectivityManager 获得 Network 与能力，再把 DNS、连接池、重试和幂等策略绑定到正确网络生命周期。

## Network、能力变化与 Socket 绑定

### 一次网络请求为何会变慢

一次请求显示为“慢”，内部可能经历 Dispatcher（OkHttp 的异步调用调度器）排队、DNS 查询、多条地址竞速、TCP 建连、TLS 握手、服务端等待和响应体读取。只修改某个超时参数，既无法判断时间花在哪个阶段，也可能把局部故障变成更长的等待。

应用架构需要处理四个问题：怎样复用连接，怎样选择解析策略，怎样隔离不同类型的流量，以及怎样在网络变化和请求失败时控制重试。一次调用的分段计时与协议细节见 [12.1 Android 网络与 TLS 性能优化](../../part2-performance/ch12-apk-network/01-android-network-tls-performance.md)，TLS 信任边界见 [12.1 Android 网络与 TLS 性能优化](../../part2-performance/ch12-apk-network/01-android-network-tls-performance.md)。

平台结论以 Android 17 / API 37 / AOSP `android-17.0.0_r1` 为锚点，客户端结论以 2026 年 6 月 8 日发布的 OkHttp 5.4.0 为锚点。OkHttp 独立于 Android 发布；项目升级客户端版本后，还要复核默认参数、拦截器能力和事件定义。

### 把网络层拆成四类职责

这里把网络层拆成连接、解析、调度和容错四类职责。这样分工的目的，是让配置、故障和指标都有明确归属。

| 职责 | 负责的问题 | 常见故障 | 主要观测点 |
| --- | --- | --- | --- |
| 连接 | TCP、TLS 和 HTTP 连接如何创建、复用与释放 | 频繁冷建连、响应体未关闭、HTTP/2 复用率低 | `connectStart`、`secureConnectStart`、`connectionAcquired`、协议 |
| 解析 | 主机名如何得到候选地址 | DNS 慢、地址族回退慢、缓存跨网络污染 | `dnsStart`、`dnsEnd`、候选地址数、目标 `Network` |
| 调度 | 哪些请求立即执行，哪些延迟、取消或批量执行 | 首屏流量被大文件占用、同步调用绕过并发限制 | 业务队列、Dispatcher 队列、取消率、后台约束 |
| 容错 | 失败是否重试，何时读取缓存或进入离线队列 | 重试风暴、重复写入、切网后持续使用旧地址 | 失败阶段、尝试次数、幂等键、缓存状态、网络变化序号 |

连接复用、解析、业务调度和失败恢复应保留各自的接口与指标。把这些策略全部写进一个拦截器，会混淆一次逻辑调用中的重定向、认证、传输恢复和业务重试，也不利于设置统一的调用截止时间。OkHttp 5.4.0 允许拦截器为当前调用覆盖缓存、连接池、DNS、套接字工厂等客户端配置；这类覆盖应进入配置审计和诊断日志，不宜藏在通用拦截器中。

### OkHttp 连接池与复用策略

#### 共享客户端，不按请求创建

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

#### 连接池不是总连接数上限

OkHttp 5.4.0 默认连接池构造参数中的数量，表示最多保留多少条**空闲连接**，并不限制正在使用的连接总数，也不等于域名数量。HTTP/1.1 通常在连接空闲后复用；HTTP/2 可以在一条连接上并发传输多个逻辑流（stream，每个流承载一组双向请求与响应数据）。默认值属于库的调优选择，客户端升级后可能变化，不应复制为架构常量。

OkHttp 用 `Address` 和 `Route` 判断连接能否复用：

- `Address`（连接地址配置）包含 URL 协议方案（scheme，例如 HTTP 或 HTTPS）、主机、端口、DNS、代理、套接字创建器（socket factory）、TLS 配置、主机名校验器（hostname verifier）和证书或公钥固定器（certificate pinner）等静态配置。
- `Route`（具体连接路径）还包含代理、候选 IP 与套接字地址等本次连接选择。
- 跨主机的 HTTP/2 连接合并还要求直连路径、IP、证书覆盖、主机名校验、证书固定规则等条件同时满足。

两个域名解析到同一 IP，不代表它们一定共享 HTTP/2 连接。反过来，证书覆盖多个域名也不足以保证连接合并。当前判断以 OkHttp 5.4.0 的 [`RealConnection.isEligible()`](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt) 为准；为便于追溯，原有 5.3.0 源码锚点 [`RealConnection.isEligible()`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt) 仍予保留。

#### 关闭响应体才能稳定复用连接

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

#### 用事件区分排队、解析、建连与服务端等待

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

### DNS 优化与 HTTPDNS

#### 系统 DNS 仍是默认基线

OkHttp 5.4.0 的 `Dns.SYSTEM` 最终调用 `InetAddress.getAllByName()`。在 Android 17 上，这条路径进入当前 Android `Network`（系统分配给一条具体网络的句柄）对应的系统解析链路，并受 VPN、Private DNS（Android 的加密 DNS 设置）、每网络缓存和网络切换影响。DNS Resolver 自 Android 10 起由可独立更新的 `com.android.resolv` Mainline 模块提供，应用无需维护一份永久 IP 表来替代它。

`Dns.lookup()` 是同步接口，OkHttp 在选择连接路径时调用它；实现类还必须支持并发调用。HTTPDNS 指应用通过 HTTP 或 HTTPS 接口获取域名地址的自定义解析方案，它不一定采用标准化的 DNS over HTTPS（DoH）协议。若 `lookup()` 内使用同一个业务客户端向 HTTPDNS 服务发请求，该服务的域名也可能重新进入自定义 `Dns`，形成递归解析。若查询又依赖同一组受限执行资源，还可能出现线程相互等待。这里应检查解析路径是否依赖自身，不能归因为连接池没有空闲连接。

#### HTTPDNS 先定义策略边界

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

### Android 网络状态只能作为动态信号

Android 17 的 [`NetworkCapabilities`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) 对三个常用能力给出了明确边界：

- `NET_CAPABILITY_INTERNET` 表示网络被配置为访问一般互联网，不证明当前可达。
- `NET_CAPABILITY_VALIDATED` 表示系统最近一次验证一般互联网成功，不证明业务端点此刻可达。
- `NET_CAPABILITY_NOT_METERED` 表示网络不按流量计费。大传输应看该能力，而不是用 Wi-Fi 或蜂窝等传输类型代替计费判断。

`VALIDATED` 适合提示离线状态、延迟非紧急公网同步和标记监控数据，不适合作为每个 API 请求的前置条件。系统验证可能刚失效，业务端点仍可达；局域网、企业专网和登录门户（captive portal，需要网页登录或同意条款的受限网络）也可能没有一般互联网验证。Android 17 的局域网访问约束见 [24.8 低带宽、流媒体与本地网络适配](08-low-bandwidth-streaming-local-network.md)。

#### 用回调维护有时序的状态

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

### 网络请求优先级与调度

#### Dispatcher 只管理异步调用的执行时机

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

#### 后台传输要按用户意图选择 API

Android 官方的[后台数据传输选择指南](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)区分了可延迟同步和用户发起的长传输：

| 场景 | 推荐机制 | 边界 |
| --- | --- | --- |
| 非用户发起、可延迟的同步或上传 | WorkManager | 普通工作通常应能在约 10 分钟内完成，并且可停止、可重试；约束满足不保证精确开始时间 |
| 用户发起并需要持续展示进度的长上传或下载 | Android 14 / API 34 起使用 User-Initiated Data Transfer Job（UIDT，用户发起的数据传输任务） | 调度时机、通知与约束需符合 UIDT 要求；旧系统准备兼容方案 |
| 平台已有专用传输 API 的场景 | 专用 API | 优先使用平台已提供的生命周期与系统集成 |
| WorkManager 和专用 API 均不适合的短时关键工作 | 符合类型要求的前台服务 | 受后台启动、时长和前台服务类型限制 |

WorkManager 的长运行 Worker（工作单元）由前台服务与 JobScheduler（系统后台任务调度器）协作执行。Android 16 起，这类工作会消耗应用的任务运行配额，也就是系统允许应用占用后台执行资源的额度；Android 17 同样保留该边界。UIDT 不消耗普通任务配额，但仍受系统健康约束。截至本次核验，Jetpack 没有 UIDT 的兼容抽象，因此 Android 14 以下还要准备 WorkManager 长运行 Worker 等回退路径。用户点击后启动的长文件传输，不能以“WorkManager 一定能无限运行”为前提。

可延迟流量应合并传输，并用 `UNMETERED`、充电和电量等约束表达成本偏好。无线电尾部耗电随设备、制式、信号和运营商配置变化，不能把某个固定秒数写进通用调度算法。

#### 大文件传输必须围绕可恢复状态设计

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

### 弱网优化从失败阶段开始

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

#### 超时是分阶段预算

OkHttp 的 `connectTimeout` 约束套接字建连阶段，`readTimeout` 和 `writeTimeout` 约束对应的读写操作，`callTimeout` 覆盖整次逻辑调用，包括 DNS、连接、写入、服务端处理和读取。将读超时增大，无法修复 DNS 或 Dispatcher 排队；只设置阶段超时，也无法限制重定向与重试累积后的总等待。

参数应由同一接口在不同网络类别下的耗时分位数、用户交互截止时间和服务端服务等级目标得出。分位数描述一组请求中有多少比例不超过该耗时，例如 P95 是 95% 的样本不超过的值。流式下载与短 API 的读取模型不同，不应共享一组机械常数。

#### 区分传输恢复与业务重试

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

#### 网络状态不能代替端点结果

默认网络为空时，应用可以直接进入离线界面，但切网回调与请求执行仍存在时序差。网络带 `VALIDATED`，业务域名也可能故障；没有 `VALIDATED`，局域网端点仍可能可达。请求结果、端点健康和 `NetworkCapabilities` 应分别记录。

弱网体验还需要数据策略配合：列表可展示有新鲜度标记的缓存，图片可按资源版本选择较小变体，上传可持久化进度并支持断点，非必要模块可以延迟请求。缓存控制和离线写入分别见 [24.5 数据缓存与离线优先架构](05-data-cache-offline-first.md) 与 [24.5 数据缓存与离线优先架构](05-data-cache-offline-first.md)。

Android 网络调用不能进入主线程。AOSP `android-17.0.0_r1` 的 `StrictMode` 在启用网络检测和对应终止策略时，由 `onNetwork()` 抛出 `NetworkOnMainThreadException`。UI 线程等待后台 `Future`、锁或 `runBlocking` 不一定触发同一异常，却仍会卡住输入与绘制，排查时要同时检查线程等待关系。

#### 流量归因只能回答其公开口径

`TrafficStats.getUidRxBytes()` 与 `getUidTxBytes()` 返回当前 UID 自开机以来、跨所有网络接口累计的网络层字节，适合做进程内前后差值与粗粒度异常发现。在 Android 7.0（API 24）及以上，应用只能查询调用方自身 UID 的这两个计数。它们不提供单请求、单域名或后台移动网络字节；设备重启后归零，不支持时返回 `UNSUPPORTED`。VPN 转发和 CLAT（把应用的 IPv4 流量转换到仅 IPv6 网络的兼容机制）等路径也可能改变归因口径，不能据此做结算或安全审计。历史用量要使用 `NetworkStatsManager` 并遵守权限与用户授权，`setThreadStatsTag()` 只添加归因标签，不会替应用限流、取消或执行后台约束。

网络方案上线时至少比较逻辑操作的 P50、P95、P99 和超时率：它们分别表示 50%、95%、99% 样本不超过的耗时。还要比较每个操作产生的调用数、连接尝试数与总字节，缓存直接或条件命中率，切网或页面退出后的遗留请求，以及后台移动流量和任务完成时效。平均耗时下降而 P99、重试次数或后台字节上升，不能判定优化有效。

### 账号、安全与资源隔离

Cookie、认证头和业务拦截器属于请求策略，连接池本身不会保存某次请求的这些 HTTP 头。登录态和匿名态可以通过不同的派生客户端或请求构造器表达，不必仅因为账号不同就创建全新的连接池。

TLS、代理与套接字配置会参与连接资格判断。使用不同的证书信任管理器（trust manager）、主机名校验器（hostname verifier）、证书或公钥固定器（certificate pinner）、客户端证书、代理或 DNS 时，应让配置差异在各自客户端中清楚可见，并验证 OkHttp 不会复用不兼容的连接。不能为提高复用率而关闭证书校验或放宽主机名验证。

是否使用独立连接池，可按以下条件判断：

- 是否需要独立释放资源或独立进程生命周期。
- 大传输是否经过实测持续影响交互请求，且只隔离 Dispatcher 仍不足。
- 代理、套接字创建器（socket factory）或连接安全策略是否存在不可共享的要求。
- 独立连接池带来的额外建连、TLS 和内存成本是否可接受。

按业务团队各建一个客户端通常没有网络语义，也会让拦截器、认证、缓存和指标配置产生多份版本。应按传输与安全策略管理客户端，而不是按模块目录管理。

### Wi-Fi 选网只保留应用观测边界

默认网络由 Android 连接服务按请求能力、网络评分、用户选择、验证状态和设备配置决定，应用不能用一个 RSSI（Received Signal Strength Indicator，接收信号强度，通常以 dBm 表示）阈值复现系统结果。相关源码链路见 [24.6 Wi-Fi 评分、网络选择与连接切换性能](06-wifi-connectivity-selection.md)。

应用侧应记录：

- 默认 `Network` 身份与变化序号。
- 传输类型、`VALIDATED`、`NOT_METERED`、VPN 和登录门户等取值种类有限的信号；限制取值种类可以控制指标维度数量，避免监控系统负担失控。
- Dispatcher 排队、DNS、每次连接尝试、TLS、请求写入、TTFB 和响应体读取。
- 使用的协议、连接是否复用、缓存命中与失败阶段。

系统侧再结合 `bugreport`（Android 诊断信息包）、`dumpsys connectivity` 与 `dumpsys wifi`（分别导出连接服务和 Wi-Fi 服务状态的命令）、Perfetto 系统追踪和 `logcat` 系统日志还原选网过程。应用指标里的“Wi-Fi”只说明传输类型，不能直接推断计费、互联网可达性或信号质量。

### 工程检查清单

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

### 继续阅读

- [24.4 HTTP/2、HTTP/3、gRPC 与 ECH](04-http2-http3-grpc-ech.md)：HTTP/2、HTTP/3、gRPC 与协议协商。
- [24.5 数据缓存与离线优先架构](05-data-cache-offline-first.md)：HTTP 缓存、多级缓存与新鲜度。
- [24.5 数据缓存与离线优先架构](05-data-cache-offline-first.md)：离线队列、同步和冲突处理。
- [24.6 Wi-Fi 评分、网络选择与连接切换性能](06-wifi-connectivity-selection.md)：系统评分、默认网络与切换。
- [24.8 低带宽、流媒体与本地网络适配](08-low-bandwidth-streaming-local-network.md)：局域网能力与 Android 17 访问边界。

### 源码与规范依据

#### 当前平台与客户端依据

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

#### 保留的旧版本源码锚点

- [OkHttp 5.3.0 OkHttpClient](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt)
- [OkHttp 5.3.0 Dispatcher](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt)
- [OkHttp 5.3.0 Dns](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
- [OkHttp 5.3.0 EventListener](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
- [OkHttp 5.3.0 ResponseBody](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt)
- [OkHttp 5.3.0 RequestBody](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt)

#### HTTP 规范

- [RFC 9110：HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 6585：Additional HTTP Status Codes](https://www.rfc-editor.org/rfc/rfc6585.html)
- [RFC 7233：Range Requests（旧版范围请求规范锚点）](https://www.rfc-editor.org/rfc/rfc7233.html)


## DNS、连接复用、重试与容灾

系统网络状态确定后，应用传输层还要处理域名解析、连接建立、协议回退和网络切换。重试必须受幂等性和总 deadline 约束。

### 范围

性能基线是一组可重复测量、可与后续版本比较的数据分布。记录中要写清用户路径、应用与系统版本、网络状态、缓存与连接方式，以及成功和失败的计数规则。缺少这些条件的“平均耗时”无法判断新版本是否退化。

本文以 Android 17 / API 37 / `android-17.0.0_r1` 为主要平台，同时标出 37.1 新增的 `HttpEngine` 计时能力。本文前文已给出请求事件与重试上限，24.4 解释 HTTP/2、HTTP/3 和 QUIC，24.7 解释 HTTPDNS 接入；这里讨论样本设计、对照实验和发布阻断规则。发布阻断规则是持续集成或发布系统中的自动判断：指标越过约定阈值时停止合入或发布。

### 三类基线各自回答一个问题

工程中至少保留三类基线。它们的环境和用途不同，不能把数据合并后计算一个分位值。

| 基线 | 环境 | 回答的问题 | 适合自动阻断的指标 |
| --- | --- | --- | --- |
| 确定性基线 | 本地测试服务、固定响应、受控故障代理 | 客户端排队、读写、解码、取消和重试语义是否退化 | 操作耗时、调用数、尝试数、字节数、功能不变量 |
| 设备实验室基线 | 固定真机、系统版本、接入点、服务端，并人为控制带宽、延迟和丢包 | DNS、建连、协议、切网与功耗改动是否符合预期 | 分阶段分布、成功率、协议使用率、恢复时间、能耗 |
| 线上基线 | 真实地区、运营商、设备与服务端版本 | 改动对用户路径和慢请求有什么影响 | 页面完成、请求成功、P50/P95/P99、后台流量、业务正确性与资源上限 |

P50、P95、P99 分别表示 50%、95%、99% 的样本不超过该值；P95/P99 描述分布尾部的慢请求，常称“尾延迟”。确定性基线可以进入 CI（Continuous Integration，持续集成）并随每次提交执行。公共互联网和生产 CDN（Content Delivery Network，内容分发网络）会受调度、拥塞、证书、服务端发布与时间段影响，适合定时实验和分阶段发布验证，不适合作为每次提交的单一阻断条件。分阶段发布是先让少量用户使用候选版本，观察指标后再逐步扩大范围，也常称“灰度发布”。

基线对象也应从用户路径开始。例如“首页可交互”可能包含配置、列表、图片和本地解码，单个 API 变快不保证页面变快。每条关键路径都要定义：

- 开始事件与完成事件。
- 必须成功的请求、允许使用旧缓存的请求和可延后请求。
- 用户等待截止时间与取消条件。
- 允许的网络调用数、连接尝试数和总字节。
- 服务端写操作的幂等与结果查询方式。幂等表示同一操作重复执行不会产生额外副作用，例如重复请求不会创建两笔订单。

### 请求阶段拆分使用同一份指标字典

基线字段沿用本节前文的请求时间线。“逻辑操作”是用户或业务发起的一次目标，例如刷新首页；它可能触发多次网络库调用。一次网络库调用又可能因多地址连接、重试或重定向产生多次连接尝试和 HTTP 交换。报告至少保留这四个层级，避免把内部恢复误算成多个用户请求。

| 阶段 | 起止边界 | 缺失时如何解释 | 不能混入的时间 |
| --- | --- | --- | --- |
| 业务队列 | 用户动作到调用网络层 | 无队列也要记录零或明确缺失原因 | OkHttp `Dispatcher` 等待 |
| 调度队列 | 网络库接收调用到开始执行 | 同步调用或未排队时可能没有独立事件 | DNS、代理选择、缓存查找 |
| 缓存路径 | 缓存判定到命中，或转入网络 | 未配置缓存与缓存未命中要分开 | 响应解码与业务缓存 |
| DNS | 解析开始到结果或错误 | 复用连接时通常没有 DNS | 地址建连和 Fast Fallback 等待 |
| 建连（connect） | 每次地址尝试开始到成功或失败 | 复用连接时没有新建连 | TLS 与后续交换 |
| TLS | 握手开始到验证结束 | 明文、复用连接或库未暴露时为空 | 服务端应用处理 |
| 上传 | 请求头发送开始到请求体完成 | 无请求体时以请求头发送完成为界 | 排队和响应等待 |
| TTFB | 请求发送完成到最终响应的首字节开始 | TTFB 是 Time to First Byte；缓存命中与双工流要使用单独定义 | 响应体下载 |
| 下载 | 响应体开始到读取或关闭 | 提前关闭要记录取消或截断 | 解压、反序列化与界面提交 |
| 本地消费 | 字节可用到业务消费完成 | 后台预取可能没有界面事件 | 网络等待 |

阶段值允许为空。连接复用时把 DNS、connect、TLS 填成零，会把“没有发生”误写成“瞬间完成”；失败发生在 DNS 时，后续阶段同样应为空。聚合前应按缓存路径、连接复用、协议、成功/失败和取消分别统计。

#### 用结构化键阻止不兼容样本混算

下面的 Kotlin 数据结构给实验记录建立最小约束。它不负责发请求，只规定哪些环境字段必须随样本保存。

```kotlin
enum class RequestPathState {
    NETWORK_NEW_CONNECTION,
    NETWORK_REUSED_CONNECTION,
    CACHE_HIT,
    CACHE_REVALIDATED,
}

enum class OperationOutcome {
    SUCCEEDED,
    FAILED,
    CANCELED,
    DEADLINE_EXCEEDED,
}

data class NetworkBaselineKey(
    val platformApi: Int,
    val platformBuildId: String,
    val appVersionCode: Long,
    val networkStackName: String,
    val networkStackVersion: String,
    val networkStackConfigId: String,
    val scenarioId: String,
    val requestPathState: RequestPathState,
    val networkSessionId: Long,
    val transports: Set<Int>,
    val validated: Boolean,
    val metered: Boolean,
)

data class NetworkBaselineSample(
    val key: NetworkBaselineKey,
    val operationElapsedNanos: Long,
    val outcome: OperationOutcome,
    val negotiatedProtocol: String?,
    val sentBytes: Long?,
    val receivedBytes: Long?,
    val networkCallCount: Int,
    val connectionAttemptCount: Int,
)
```

`networkSessionId` 是进程内为每个新观察到的 `Network` 分配的临时编号，不上传系统网络句柄。实验室可保存完整系统构建号；线上数据应按预先定义的版本或设备类别分组，不上传过细的属性组合，以免形成可识别单台设备的指纹。这种把连续或高种类数据归入有限类别的做法常称“分桶”。`scenarioId`、网络栈配置编号和传输集合必须来自白名单，也不能包含账号、URL、IP 或文档名。

分位值只在 `NetworkBaselineKey` 相同或分析者明确选择的维度内计算。系统版本、网络栈提供程序、缓存路径或计费状态不同的样本直接混合，会把环境构成变化误判成代码回归。

### DNS 与地址选择的基线怎么建

Android 10 / API 29 起公开的 `DnsResolver` 支持异步查询，并可传入代表某条系统网络的 `Network`。`android-17.0.0_r1` 的 [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) 仍按目标网络的 `netId` 发起解析；`netId` 是系统内部标识该网络的编号。它属于系统解析入口，不等同于应用自行请求指定服务的 HTTPDNS。

每种解析方案单独建组：

| 解析路径 | 固定条件 | 必须记录 | 不能由结果推断 |
| --- | --- | --- | --- |
| 系统 DNS | Android `Network`、Private DNS 状态、网络会话 | 是否执行查询、耗时、结果数量、错误类别 | 具体递归解析器的完整内部耗时 |
| HTTPDNS | 服务版本、缓存版本、系统 DNS 回退策略 | 本地命中、过期、请求结果、回退原因 | 返回地址一定可连接或证书一定匹配 |
| 应用内 DoH | DoH 提供方、引导地址、连接复用状态 | 引导方式、查询耗时、HTTP 状态、回退 | Android 系统 DNS 的行为 |
| 平台 Private DNS | 系统设置与 `LinkProperties` 快照 | 是否启用、是否验证、默认网络会话 | 应用请求一定使用某个特定服务器 |

DoH（DNS over HTTPS）把 DNS 查询装入 HTTPS 请求；Android 的 Private DNS 则是用户或管理员配置的平台级加密 DNS。`LinkProperties` 提供某条网络的链路属性快照，包括 DNS 服务器等配置。“冷 DNS”通常指没有可用解析缓存的首次查询，但应用可以清理自己的 HTTPDNS 缓存，却通常不能在普通测试进程里独占或可靠清理系统解析缓存。若无法控制系统缓存，报告应写“新应用客户端、无应用缓存”，不要写成“系统冷解析”。

地址选择要保留候选数量、地址族、每次尝试的顺序、是否并行、失败类型和获胜尝试。OkHttp 5.3.0 默认启用 Fast Fallback：客户端按短间隔并发尝试多个候选地址，任一连接成功后采用该连接；这类算法也称 Happy Eyeballs，用延迟少量额外连接来降低单一地址族不可达造成的等待。只记录最终 IPv4 或 IPv6 会隐藏另一组地址持续失败的问题。线上遥测不保存原始 IP，可使用地址族、匿名化边缘节点编号和服务端返回的区域标记。

TTL（Time to Live，生存时间）规定 DNS 记录可以缓存多久。TTL 到期只影响后续解析；已经复用的连接不会随之自动失效，基线也不能用清空连接池来模拟普通 TTL 刷新。HTTPDNS 与 OkHttp 的同步边界继续见 24.7。

### 连接复用与队头阻塞要分路径测试

队头阻塞指排在前面的数据丢失或处理变慢时，后续数据也被迫等待。连接复用实验至少建立四种请求路径：

| 路径 | 实验准备 | 验证目标 |
| --- | --- | --- |
| 新连接 | 无可复用连接，明确 DNS 缓存条件 | 解析、地址选择、connect、TLS 和首个交换 |
| 复用空闲连接 | 同一网络、代理、地址与安全配置，前一请求已完成 | 连接池命中与省去握手后的收益 |
| 多路复用并发 | 同一 HTTP/2 或 HTTP/3 连接发出多请求 | 流数量、优先级、丢包时的尾延迟与大响应干扰 |
| HTTP 缓存 | 分别制造直接命中、条件请求和未命中 | 缓存语义、线上字节与本地读取成本 |

新建一个客户端不代表所有网络状态都已清空：系统 DNS、TLS 会话状态、Cronet 磁盘数据、服务器 QUIC 信息和 CDN 边缘状态都可能保留。报告要列出清理了哪些状态、保留了哪些状态。

连接池保存可再次使用的连接，省去后续请求的建连和握手成本。HTTP/1.1 的并发通常依赖多条连接；HTTP/2 可在一条 TCP 连接上多路复用多个流，即让多个请求交错传输。TCP 丢包会影响该连接的发送进度；HTTP/3 在 QUIC 中为流提供独立的有序交付，单个流的数据丢失不会按 HTTP/2 的 TCP 字节序阻塞其他流。QUIC 仍共享连接级拥塞控制和路径容量，因此某个流占用大量带宽仍可能影响其他流。

连接合并指多个主机在证书、DNS、代理、地址和网络库规则都允许时，共用同一条 HTTP/2 连接。实验要单独标记这一情况。主机数不能代替连接数，连接复用率也不能单独证明页面更快。

### Cronet、OkHttp、HttpEngine 与 Mars 的可比性

选型实验应记录实际实现，不使用“Cronet 组”“OkHttp 组”这种过宽标签。`CronetProvider` 决定 Cronet 引擎由哪个实现提供；同一个 API 可能落到原生引擎或功能较少的 Java 回退实现。Mars 是微信开源的长连接网络组件，消息确认与重连模型不同于一次 HTTP 请求，也要单独定义指标。

| 网络栈 | 基线必须固定 | 可用观测 | 主要边界 |
| --- | --- | --- | --- |
| OkHttp 5.3.0 | 精确版本、拦截器顺序、`Dispatcher`、连接池、DNS、协议列表 | `EventListener`、`Response.protocol`、应用事件 | 标准公开配置没有 HTTP/3；事件可因复用、重试和重定向而缺失或重复 |
| Cronet 库 | Maven 版本、实际 `CronetProvider`、引擎版本、缓存目录和配置 | `RequestFinishedInfo.Metrics`、`UrlResponseInfo`、网络质量估计、NetLog | Java 回退实现与原生实现不等价；NetLog 只用于受控诊断 |
| 平台 `HttpEngine` | API/SDK 扩展版本、模块版本、缓存与 QUIC/Brotli 配置 | `UrlResponseInfo` 与公开回调 | 基础 API 属于 API 34 / S Extension 7；详细计时 `FinishedRequestTimings` 到 37.1 / S Extension 23 才加入，`android-17.0.0_r1` 没有该接口 |
| Mars 或自有长连接 | 仓库提交、协议版本、心跳、连接复用、加密与重连策略 | 团队定义的消息确认、积压、重连和字节指标 | 指标需和 HTTP 请求分开，不能用库名称代替具体实现 |

Cronet 的 `RequestFinishedInfo.Metrics` 能提供请求、DNS、连接、TLS、发送、响应开始和结束等时间。复用套接字时 DNS、连接和 TLS 时间为空；重定向相关计时与字节按该 API 的定义累计，分析前要阅读所用 Cronet 版本的接口说明。NetLog 是 Chromium 网络栈的详细事件日志，可能包含敏感网络信息，只用于受控诊断。`UrlRequest.Builder.addRequestAnnotation()` 可关联请求类型，但注解值应来自数量有限的固定集合；这就是“低基数”，可防止指标维度因 URL、用户 ID 等不断增加，也不能放入个人信息。

Cronet 网络质量估计器的 RTT（Round-Trip Time，往返时延）样本可能来自 TCP、QUIC 或 URL 请求层，吞吐样本来自网络栈观察。吞吐表示单位时间内成功传输的数据量。两类数值都是网络状态信号，不能代替某条请求的 DNS、TTFB 或下载耗时。未启用估计器或没有足够观察时，API 会返回未知值，不能填入默认网速。

跨网络栈比较时，业务拦截器、缓存、压缩、Cookie、代理、证书验证、线程执行器和响应读取方式必须一致。若同时从 OkHttp 切到 Cronet 并启用 HTTP/3，结果同时包含实现变化与协议变化，无法判断差异来自哪一个变量；统计实验把这种情况称为“混杂”。

### HTTP/3、QUIC 与网络切换的实验设计

QUIC 是主要运行在用户空间、以 UDP 为承载的传输协议，HTTP/3 构建在 QUIC 之上。要单独观察协议影响，优先在同一个 Cronet 或 `HttpEngine` 实现中只改变 QUIC 开关，其余配置保持一致。实验组还要按以下状态分开：

- 首次连接、已有 QUIC 服务器信息、具备可用会话状态。
- HTTP/3 成功、主动禁用、UDP 不可达后回到 HTTP/2 或 HTTP/1.1。
- 直接响应、重定向、HTTP 缓存命中和条件请求。
- 请求前切网、上传期间切网、等待响应时切网、下载期间切网。

每次切网实验记录旧、新 `Network` 的临时编号和能力快照、切换发生时的请求阶段、已发送与已接收字节、最终协议、是否重新建连、业务层是否重复提交。QUIC 的连接迁移允许连接在 IP 地址或网络变化后继续使用，但不保证每个提供程序、服务端和路径都会迁移成功；代理、VPN、NAT（Network Address Translation，网络地址转换）、服务器配置和连接迁移选项都会改变结果。

UDP 阻断测试必须保留从首次 QUIC 尝试到 HTTP 回退完成的总耗时。只比较成功的 HTTP/3 与成功的 HTTP/2，会漏掉协议探测失败造成的慢请求。服务端同时记录 ALPN（Application-Layer Protocol Negotiation，TLS 握手中的应用协议协商）、QUIC 版本、连接 ID 迁移、重试令牌和错误分类，客户端不要从端口或 URL 推断协议。

0-RTT 是在恢复已有 TLS/QUIC 会话时、握手完成前发送应用数据的能力，可以省去一个往返等待。它单独建组，并只用于即使被攻击者重放也不会产生额外副作用的操作。客户端与服务端要共同验证重复到达时的语义，状态变更请求不能只因耗时更短便直接放入早期数据。

QUIC 状态机位于用户空间网络栈，也就是普通进程可实现的协议层；Android common kernel（Android 通用内核）负责 UDP 套接字、IP、路由、队列和驱动。内核证据以 `android17-6.18-2026-06_r6` 为准，UDP 发送路径可从 [`net/ipv4/udp.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c) 继续检查。应用层不能把内核 UDP 统计直接当作 HTTP/3 请求结果。

### 弱网故障测试检查不变量

故障注入是测试环境主动制造 DNS 超时、断网、截断响应等异常。它用于验证“不重复提交、按时取消、资源能关闭”等在故障下仍必须成立的条件，这些条件称为不变量。每种故障都要写出客户端允许做什么、禁止做什么。

| 故障 | 要验证的行为 | 主要风险 |
| --- | --- | --- |
| DNS 超时、无答案、NXDOMAIN | 错误分类、系统 DNS 或缓存回退、总截止时间 | 多层解析同时重试 |
| 单个地址超时或拒绝连接 | Fast Fallback、失败隔离、尝试上限 | 并行连接过多 |
| 证书链或主机名错误 | 立即失败并保留安全错误 | 被错误归类为可重试弱网 |
| 上传后连接断开 | 结果未知、幂等查询或恢复 | 重复下单、支付或发消息 |
| 429、503 与 `Retry-After` | 尊重服务端等待要求和逻辑操作截止时间 | 客户端请求风暴 |
| 响应头慢、响应体截断 | TTFB 与下载阶段分离、关闭资源 | 只记录响应码为成功 |
| 网络切换、VPN 变化 | 取消或恢复符合幂等规则 | 全量清池与集中重建 |
| 页面退出与任务取消 | 网络调用停止、回调不再更新界面 | 遗留下载和无效解码 |

NXDOMAIN 表示 DNS 明确回答“该域名不存在”，与查询超时或返回空记录不是同一种失败。超时参数来自用户路径截止时间和各阶段历史分布，不能复制一组全局数字。网络库内部恢复、业务重试、图片库重试和 WorkManager 退避都要计入同一个逻辑操作；退避指连续失败后逐步延长下一次尝试前的等待。有关实现顺序与幂等边界见 24.3。

熔断器在某类请求连续失败达到阈值后暂时拒绝新请求，等待后再用少量探测判断服务是否恢复。熔断范围通常限定到具体服务、路由或接入点，并限制探测并发；对全站使用一个状态，可能让局部故障扩大成整站不可用。备用域名和 IP 还必须通过证书、SNI、Host、Cookie、鉴权和服务端反滥用规则校验。SNI（Server Name Indication，服务器名称指示）是 TLS 握手中用于表明目标主机名的扩展，不能随意换成备用 IP 后省略。

### 数据体积与传输成本分两个轴比较

序列化格式决定业务数据怎样表示，内容编码决定表示结果怎样压缩。这是两个可以独立改变的变量：先比较 JSON、Protocol Buffers 等表示在相同字段集合下的大小和解析成本，再比较 gzip、Brotli、Zstandard 等内容编码在相同输入上的网络传输字节与 CPU 成本。

| 变量 | 需要固定 | 需要测量 | 兼容边界 |
| --- | --- | --- | --- |
| JSON 字段集合 | 业务语义、空值与默认值策略 | 未压缩字节、解析 CPU、对象分配 | 服务端与旧客户端字段兼容 |
| Protocol Buffers | 消息结构（schema）、未知字段、默认值与版本 | 编码字节、序列化/反序列化 CPU | 结构演进和调试工具 |
| gzip | 压缩级别、服务端实现、响应类型 | 线上字节、压缩与解压 CPU | 客户端透明解压后的字段口径 |
| Brotli | 质量等级、静态或动态响应、网络栈开关 | 线上字节、首包与 CPU | HttpEngine 默认关闭 Brotli，实际配置要入样本 |
| Zstandard | 客户端/服务端支持、内容协商、可选字典版本 | 线上字节、CPU、内存和失败回退 | 不能假定所有 Android 网络栈自动支持 |
| 压缩字典 | 字典 ID、版本、分阶段发布与回滚 | 命中率、字节、解码失败 | 客户端与服务端必须同时拥有兼容字典 |

这里的 schema 是消息字段、类型和编号的结构定义，决定 Protocol Buffers 如何编码与兼容演进。压缩字典则保存一组常见字节序列，编码端和解码端必须使用兼容版本。请求字段裁剪、分页和差量更新通常能先减少无用数据，再考虑是否更换压缩算法。基线因此要同时记录业务实际使用的字节和网络传输字节，防止“压缩率提高”掩盖响应仍包含大量首屏不用的字段。

字节指标必须写清统计范围和定义。Cronet `UrlResponseInfo.getReceivedByteCount()` 返回处理该请求所需的最小网络接收字节，发生在解压前，包含重定向的头部与数据，但不保证包含 IP、TCP/UDP、TLS 和代理等全部开销。OkHttp 事件字节、响应体长度、`TrafficStats` UID 差值也各有定义；UID 是 Android 分配给应用身份的整数编号，`TrafficStats` 的 UID 数据覆盖该应用的累计流量，不能与单请求字节放进同一列直接比较。

序列化和解压 CPU 可用 Microbenchmark 在固定输入上重复测量单段代码；端到端页面可用 Macrobenchmark 启动应用并测量完整用户流程。两者都应配合本地固定响应。远程网络波动会混入 CPU 微基准，不应把真实互联网请求放入循环测试。

### 验证与回归测试

#### 固定环境，再做 A/B

A/B 对照实验把样本分为基线组 A 与候选组 B，并尽量只改变待验证的一个变量。同一轮实验至少固定：

- 物理设备、Android 版本、系统构建和相关 Mainline 模块状态。Mainline 是可通过 Google Play 系统更新独立于整机 OTA 升级的系统模块机制。
- 发布型 APK、编译状态、代码压缩配置和应用数据准备方式。
- 网络接入点、代理/整形配置、计费与验证能力、VPN 和 Private DNS 状态。
- 网络栈版本、提供程序、缓存目录、协议开关和连接预热方式。
- 服务端版本、响应内容、缓存指令、边缘节点与证书配置。
- 实验顺序、并发背景任务、充电与温度条件。

Android 官方性能指南要求使用接近发布版本的构建，并在同一设备与系统版本上做 A/B。Debug 构建、调试器、持续抓包和详细 NetLog 都会增加开销，只用于定位，不进入正式基线。

为降低时间漂移，可以在同一设备上交错运行基线组与候选组，并随机化用例顺序。网络切换、DNS 缓存、CDN 状态等跨用例状态仍需显式重置或记录；“重新启动应用”不是完整清理方案。

#### 统计时先看总样本构成

报告顺序建议固定为：

1. 样本数、成功、失败、取消和截止时间超限。
2. 每个逻辑操作的网络调用数、连接尝试数和总字节。
3. 成功样本的 P50、P95、P99 与置信区间。置信区间表示根据当前样本推断总体指标时的不确定范围。
4. 按缓存路径、协议、网络能力、地区、运营商、设备和版本分组。
5. 页面完成、业务正确性、后台流量和功耗限制。

只对成功样本计算延迟会产生幸存者偏差：失败样本被排除后，留下的成功请求不能代表全部请求；候选方案若更早失败，成功请求反而可能看起来更快。成功率和延迟必须并列展示，失败请求也要保留失败阶段与已消耗时间。

回归阈值来自用户体验目标、历史波动、样本量和实验成本。固定的通用毫秒阈值无法覆盖首页 API、媒体、长连接和后台同步。自动阻断配置应保存基线版本、适用场景、统计窗口和阈值来源，基线也不能永远指向“上一轮结果”，否则连续小幅退化会逐次被接受。

#### 工具各看一层

| 工具 | 适合观察 | 不适合回答 |
| --- | --- | --- |
| OkHttp `EventListener` | 调度、DNS、连接、TLS、交换、缓存和重试决策 | Cronet、WebView 或自有套接字流量 |
| Cronet 完成信息与网络质量估计 | Cronet 请求时间、字节、协议与网络状态样本 | 平台外部网络栈或业务页面完成 |
| `NetworkCapabilities` / `LinkProperties` | 网络会话、能力、传输集合、路由与 DNS 配置 | 端到端实测速率；带宽字段只估算设备到接入网络这一段 |
| `TrafficStats` | 当前 UID 跨接口的粗粒度累计字节 | 单请求、单域名、后台移动流量或协议开销 |
| Perfetto 与应用 Trace | 线程调度、CPU、Binder、GC 和本地处理时间关系 | 完整 DNS、TLS、HTTP/3 语义 |
| 服务端追踪记录 | 接入层排队、上游耗时、响应字节与限流 | 客户端队列、无线网络和本地解码 |
| Macrobenchmark | 带固定数据源的用户路径完成与系统 Trace | 把不受控公共互联网结果用作稳定的协议阻断条件 |

Trace 是带时间戳的执行事件记录；Binder 是 Android 的跨进程调用机制；GC（Garbage Collection）是运行时回收不再使用对象的过程。Android vitals 是 Play Console 汇总的应用质量指标，其中的后台移动网络数据可作为发布保护指标。实验室确认协议收益后，仍要分阶段发布，并为失败率、P99、重试数、后台字节、服务端 CPU 和业务成功率分别设置停止条件。

### 扩展：Android 10 到 Android 17 的网络基线变化

Android 版本和可独立更新的 Mainline 模块都会改变实验环境，因此同一应用版本也可能出现不同结果。

| 平台节点 | 与基线相关的变化 | 记录要求 |
| --- | --- | --- |
| Android 10 / API 29 | `DnsResolver` 成为公开异步 API；DNS Resolver 以 `com.android.resolv` APEX 交付 | 系统构建、解析路径、Private DNS 和模块状态 |
| Android 14 / API 34 | 平台加入 `HttpEngine`，也标注为 Android S 扩展 7 | API/扩展版本、HttpEngine 配置与实现版本 |
| Android 17 / API 37 | 面向 API 37 的应用默认启用 CT；平台为 TLS 连接提供 ECH 配置 | `targetSdk`、安全配置、网络库 ECH 支持和系统构建 |

APEX 是 Android 用于封装和独立更新底层系统组件的文件格式；实验要记录模块版本，不能只记录整机版本。`NetworkCapabilities.getLinkDownstreamBandwidthKbps()` 与上行对应接口只表示系统估计的首跳传输带宽，也就是设备到接入网络这一段，不是服务器到应用的端到端吞吐。Wi-Fi、蜂窝、VPN 和卫星等传输类型也不能直接代表计费、延迟或可用带宽。Android 17 源码定义可在 [`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) 中核对。

IPv6 也不单独判定快慢。IPv6-only 表示接入网络只提供 IPv6；NAT64 会把 IPv6 客户端流量转换到 IPv4 服务端。它们与双栈地址顺序、代理、运营商、边缘节点和服务端路由共同决定请求结果。基线用连接尝试与端到端结果回答问题，不用地址族预先判断快慢。

### 扩展：安全策略也是基线条件

Android 17 / API 37 的网络安全配置需要进入 TLS 基线。`targetSdk` 是应用声明并据此启用新平台行为的目标 API 版本。面向 API 37 的应用默认启用 CT（Certificate Transparency，证书透明度），系统会要求证书出现在可验证的公开日志中。ECH（Encrypted Client Hello）用于加密 TLS ClientHello 中的 SNI；只有网络库和服务端都支持时才会协商成功。协商失败时客户端还可能发送带随机内容的 ECH GREASE 扩展，以免网络设备把 ECH 扩展误判为异常；GREASE 本身不表示 SNI 已加密。网络安全配置写成 `enabled` 也不能证明某条请求已经协商 ECH，只有网络栈公开结果或受控服务端记录能提供证据。详细机制见 24.4。

性能实验不得安装“信任所有证书”的 `TrustManager`、宽松主机名验证或明文回退。`TrustManager` 负责验证服务端证书是否来自受信任的 CA（Certificate Authority，证书颁发机构）。若测试代理需要解密 HTTPS，应使用只存在于测试构建的调试 CA，并把“经过代理”和“直接连接”分成两组。

Android 官方文档不建议普通应用进行证书固定。证书固定是客户端只接受预先记录的公钥或证书；它会把服务端证书轮换与客户端版本覆盖绑定在一起。若风险评估后仍采用，基线必须包含备用公钥、过期策略、旧版本客户端和轮换演练。客户端无法连到服务端时，远程配置也未必能送达。

TLS 会话恢复与 0-RTT 不能合并成“复用握手”一个字段。0-RTT 有重放风险，只允许经过服务端确认的可重放操作；测试还要验证早期数据被拒绝后的重发语义。

### 扩展：系统源码查询入口

应用观察到 DNS 慢、切网或连接失败时，按职责查源码：

| 层级 | Android 17 源码位置 | 能回答的问题 |
| --- | --- | --- |
| 应用 DNS API | [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) | 查询如何绑定 `Network`、取消和回调 |
| 网络能力模型 | [`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) | 验证、计费、受限、传输与设备到接入网络的带宽字段语义 |
| 系统网络选择 | [`ConnectivityService.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/ConnectivityService.java) | 默认网络匹配、能力变化与回调分发 |
| DNS Resolver 模块 | [`packages/modules/DnsResolver`](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/) | 系统存根解析器（stub resolver）、缓存和解析实现 |
| Linux UDP | [`udp.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c) | QUIC 所依赖的 UDP 发送、套接字与错误路径 |

存根解析器接收应用的域名查询，再把请求交给递归 DNS 服务并缓存结果。DNS Resolver 从 Android 10 起以 `com.android.resolv` APEX 交付。官方模块说明指出，它由 Android 网络守护进程 `netd` 动态链接，同时直接服务本地 Unix socket `/dev/socket/dnsproxyd`；解析器配置的 Binder 跨进程入口也已移到该模块。Android 17 上不应继续用 Android 9 以前“所有解析都由 netd 内部实现”的结构解释问题。

这些源码用于确认平台职责和公开语义。普通应用仍应通过 SDK、网络库和服务端观测定位，不绕过平台路由、权限、证书验证或后台限制。

### 上线前检查清单

- 每条基线都带场景、版本、网络栈配置、网络会话、缓存路径和结果状态。
- 持续集成、设备实验室和线上基线没有混算。
- 无应用 DNS 缓存、无可复用连接、复用连接与缓存命中的准备条件写清楚。
- 失败、取消和截止时间超限进入分母，不只统计成功请求。
- DNS、建连、TLS 缺失表示阶段未发生或不可观测，不填零。
- 协议来自网络栈公开结果，HTTP/3 失败后的回退时间计入逻辑操作。
- A/B 只改变计划验证的变量；网络栈与协议同时变化时，报告明确写出两个变量都变了，不能归因给其中一个。
- 弱网用例检查幂等、取消、资源关闭和尝试上限。
- 压缩比较区分 JSON/Protocol Buffers 等数据表示、网络内容编码、解压后字节和 UID 总流量。
- Android 17 的 CT、ECH、网络能力和 Mainline 模块状态进入实验记录。
- 发布阻断规则说明阈值来源，并同时检查成功率、P95/P99、字节、功耗与业务正确性。


## 参考资料

- [Android 17 / API 37 公开 API 签名](https://android.googlesource.com/platform/prebuilts/sdk/+/refs/tags/android-17.0.0_r1/37.0/public/api/android.txt)
- [读取 Android 网络状态](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Cronet 功能与接入](https://developer.android.com/develop/connectivity/cronet)
- [Cronet RequestFinishedInfo 源码](https://chromium.googlesource.com/chromium/src/+/lkgr/components/cronet/android/api/src/org/chromium/net/RequestFinishedInfo.java)
- [Cronet 网络质量 RTT](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/NetworkQualityRttListener)
- [Android 网络安全配置](https://developer.android.com/privacy-and-security/security-config)
- [Android 网络协议安全与证书固定建议](https://developer.android.com/privacy-and-security/security-ssl)
- [Android vitals：后台移动网络使用过多](https://developer.android.com/topic/performance/vitals/bg-network-usage)
- [Android 17 行为变化](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android API：`HttpEngine`](https://developer.android.com/reference/android/net/http/HttpEngine)
- [Android API：`FinishedRequestTimings`](https://developer.android.com/reference/android/net/http/FinishedRequestTimings)
- [OkHttp 5.3.0 源码：Fast Fallback](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt#L750-L766)
- [Android DNS Resolver 模块](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
- [Android 应用性能测量](https://developer.android.com/topic/performance/measuring-performance)
- [Android Benchmark 概览](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [TrafficStats API](https://developer.android.com/reference/android/net/TrafficStats)
- [Zstandard Content-Encoding：RFC 9659](https://www.rfc-editor.org/rfc/rfc9659.html)
