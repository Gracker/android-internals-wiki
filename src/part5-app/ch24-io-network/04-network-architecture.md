---
title: "网络架构与连接管理"
chapter: "24.4"
section: "24.4"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [okhttp, connection-pool, httpdns, weak-network, dispatcher]
confidence: "medium"
sources:
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt
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
- type: official
  path: https://source.android.com/docs/core/ota/modular-system/dns-resolver
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/reading-network-state
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/uidt
- type: official
  path: https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt
- type: reference
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt
- type: reference
  path: https://www.rfc-editor.org/rfc/rfc9110.html
- type: reference
  path: https://www.rfc-editor.org/rfc/rfc6585.html
- type: aosp
  path: system/dns-resolver
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
related_chapters: ["24.5", "12.1", "12.2"]
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

## 为什么要了解网络架构与连接管理

一次请求显示为“慢”，内部可能经历 Dispatcher 排队、DNS 查询、多条地址竞速、TCP 建连、TLS 握手、服务端等待和响应体读取。只修改某个超时参数，无法判断时间花在哪个阶段，也容易把局部故障变成更长的等待。

应用架构需要处理四个问题：怎样复用连接，怎样选择解析策略，怎样隔离不同类型的流量，以及怎样在网络变化和请求失败时控制重试。一次调用的分段计时与协议细节见 [12.1 网络性能优化](../../part2-performance/ch12-apk-network/01-network-performance.md)，TLS 信任边界见 [12.2 网络安全与 TLS 性能](../../part2-performance/ch12-apk-network/02-network-security-tls-performance.md)。

平台结论以 Android 17 / API 37 / AOSP `android-17.0.0_r1` 为锚点，客户端结论以 OkHttp 5.3.0 为锚点。OkHttp 是独立发布的库；项目升级客户端版本后，还要复核默认参数和事件定义。

## 网络架构的四个控制面

应用网络层可以按四个控制面组织：

| 控制面 | 负责的问题 | 常见故障 | 主要观测点 |
| --- | --- | --- | --- |
| 连接 | TCP、TLS 和 HTTP 连接如何创建、复用与释放 | 频繁冷建连、响应体未关闭、HTTP/2 复用率低 | `connectStart`、`secureConnectStart`、`connectionAcquired`、协议 |
| 解析 | 主机名如何得到候选地址 | DNS 慢、地址族回退慢、缓存跨网络污染 | `dnsStart`、`dnsEnd`、候选地址数、目标 `Network` |
| 调度 | 哪些请求立即执行，哪些延迟、取消或批量执行 | 首屏流量被大文件占用、同步调用绕过并发限制 | 业务队列、Dispatcher 队列、取消率、后台约束 |
| 容错 | 失败是否重试，何时读取缓存或进入离线队列 | 重试风暴、重复写入、切网后持续使用旧地址 | 失败阶段、尝试次数、幂等键、缓存状态、网络变化序号 |

连接复用、解析、业务调度和失败恢复应保留各自的接口与指标。把这些策略全部写进一个拦截器，会混淆一次逻辑调用中的重定向、认证、传输恢复和业务重试，也不利于设置统一的调用截止时间。

## OkHttp 连接池与复用策略

### 共享客户端，不按请求创建

`OkHttpClient` 持有连接池、Dispatcher、DNS、TLS 配置和拦截器。OkHttp 官方建议在应用内共享客户端；每次请求创建客户端，会留下彼此隔离的连接池与线程资源。

下面的代码用于建立一个进程级共享客户端。示例没有覆盖 OkHttp 默认连接池、并发和超时参数，因为这些参数应由项目的链路数据和服务等级目标决定。

```kotlin
object NetworkClient {
    val shared: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .eventListenerFactory { NetworkEventListener() }
            .build()
    }
}
```

`lazy` 只负责避免重复构造；应用仍需保证使用同一个对象。需要调整某类请求时，优先从 `shared.newBuilder()` 派生。OkHttp 5.3.0 的 `newBuilder()` 会继承配置并共享连接池与线程资源；直接调用新的 `OkHttpClient.Builder()` 则会创建独立资源。

### 连接池不是总连接数上限

OkHttp 5.3.0 默认连接池构造参数中的数量，表示最多保留多少条**空闲连接**，并不限制正在使用的连接总数，也不等于域名数量。HTTP/1.1 通常在连接空闲后复用；HTTP/2 可以在一条连接上并发传输多个 stream。默认值属于库的调优选择，客户端升级后可能变化，不应复制为架构常量。

OkHttp 用 `Address` 和 `Route` 判断连接能否复用：

- `Address` 包含 scheme、主机、端口、DNS、代理、socket factory、TLS 配置、hostname verifier 和 certificate pinner 等静态配置。
- `Route` 还包含代理、候选 IP 与 socket 地址等本次连接选择。
- 跨主机的 HTTP/2 连接合并还要求直连 route、IP、证书覆盖、主机名校验、certificate pin 等条件同时满足。

两个域名解析到同一 IP，不代表它们一定共享 HTTP/2 连接。反过来，证书覆盖多个域名也不足以保证连接合并。具体判断可对照 OkHttp 5.3.0 的 [`RealConnection.isEligible()`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealConnection.kt)。

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

`use` 离开作用域时会关闭响应体。响应体未关闭会占用 socket 与 HTTP/2 stream，连接池即使配置正确也无法正常复用。流式下载不能先调用 `string()`，但仍要在消费结束、取消或异常时关闭响应体。

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

连接池命中时，DNS 与建连事件可能全部缺席。重定向、认证和 route 重试又可能让同一组事件出现多次。采集时要以一次逻辑 `Call` 为父级，再为每次 DNS、建连和交换分配事件序号；不能把第一组事件直接当作整次调用的唯一阶段。

## DNS 优化与 HTTPDNS

### 系统 DNS 仍是默认基线

OkHttp 5.3.0 的 `Dns.SYSTEM` 最终调用 `InetAddress.getAllByName()`。在 Android 17 上，这条路径进入按 Android `Network` 配置的系统解析链路，并受 VPN、Private DNS、每网络缓存和网络切换影响。DNS Resolver 自 Android 10 起由 `com.android.resolv` Mainline 模块提供，应用无需维护一份永久 IP 表来替代它。

`Dns.lookup()` 是同步接口，OkHttp 在选择 route 时调用它；实现类还必须支持并发调用。若 `lookup()` 内使用同一个业务客户端向 HTTPDNS 服务发请求，HTTPDNS 服务域名也可能再次进入该自定义 `Dns`，形成递归解析。若查询又依赖同一组受限执行资源，还可能出现线程相互等待。这里应检查解析路径是否依赖自身，不能归因为连接池没有空闲连接。

### HTTPDNS 先定义策略边界

HTTPDNS 可用于处理特定地区的解析污染、CDN 地址选择或解析时延，但接入前要写清楚以下规则：

- HTTPS URL 继续使用原主机名。自定义 `Dns` 只返回地址，SNI、hostname verification、certificate pin、Cookie 域规则仍按主机名执行。
- TTL 使用 HTTPDNS 响应或服务协议给出的有效期。不存在“统一取 TTL 的某个百分比”这一通用规则。
- 缓存键至少包含主机名与 Android `Network` 身份，默认网络变化后旧网络的结果不能直接继承。
- 缓存保留 IPv4、IPv6 和多个候选地址。OkHttp 5 的 Fast Fallback 默认开启，会对候选连接做竞速；只保留一个地址会丢失这项恢复能力。
- HTTPDNS 查询使用独立的引导解析策略，不能依赖正在实现的自定义解析器。
- 系统 DNS 回退是产品策略，不是无条件规则。严格隐私模式若承诺只使用指定解析服务，静默转向系统 DNS 会违反承诺；允许回退时也要记录原因。
- 自定义 HTTPDNS 会绕开系统解析器为 Private DNS、企业 VPN 和分流 DNS 提供的解析语义。应用仍可能通过 VPN 传输后续连接，但域名解析结果已不再由该系统策略决定。企业内网、专网和本地域名尤其需要实机验证。

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

这里用 `elapsedRealtime()` 判断进程内有效期，避免用户修改墙上时钟后错误延长 TTL。若缓存需要跨重启持久化，还要同时保存可恢复的过期依据，并在重启后按协议重新校验。缓存写入端应解析数值 IP，不要在同步 `lookup()` 中用主机名解析 API 间接触发另一轮 DNS。

示例适用于明确允许系统 DNS 回退的策略。严格解析策略应把回退实现作为依赖传入，并让失败显式返回。若客户端绑定到指定 Android `Network`，回退解析也应使用该网络的 `getAllByName()`，并与对应的 socket 绑定策略保持一致。

HTTPDNS 查询失败、返回空地址、地址连接失败和 TLS 校验失败是不同事件。前两类属于解析服务与缓存策略，连接失败要保留到 route 维度，TLS 失败不能通过关闭 hostname verification 来“兼容”。

## Android 网络状态只能作为动态信号

Android 17 的 [`NetworkCapabilities`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) 对三个常用能力给出了明确边界：

- `NET_CAPABILITY_INTERNET` 表示网络被配置为访问一般互联网，不证明当前可达。
- `NET_CAPABILITY_VALIDATED` 表示系统最近一次验证一般互联网成功，不证明业务端点此刻可达。
- `NET_CAPABILITY_NOT_METERED` 表示网络不按流量计费。大传输应看该能力，而不是用 Wi-Fi 或蜂窝 transport 代替。

`VALIDATED` 适合提示离线状态、延迟非紧急公网同步和标记遥测数据，不适合作为每个 API 请求的前置条件。系统验证可能刚失效，业务端点仍可达；局域网、企业专网和 captive portal 也可能没有一般互联网验证。Android 17 的局域网访问约束见 [24.16 Android 17 流媒体与本地网络](16-android17-streaming-local-network.md)。

### 用回调维护有时序的状态

`getNetworkCapabilities()` 返回的是调用瞬间的快照，Android 17 源码注释说明它可能立即过时。生产代码应注册 `NetworkCallback`，并使用 `onCapabilitiesChanged()` 传入的对象。回调内再次同步查询 `getNetworkCapabilities()` 或 `getLinkProperties()` 会引入竞态。

下面的代码用于维护当前 UID 的默认网络信号。它在收到能力回调后才发布状态；Android 8.0 及以上，`onAvailable()` 后会按序收到 `onCapabilitiesChanged()`。

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

默认网络从 Wi-Fi 切到蜂窝时，新旧网络对象具有不同身份；物理接入点断开后重连，也可能得到新的 `Network`。HTTPDNS 缓存、按网络绑定的 socket 以及诊断记录都应保留这一身份，不能只保存“Wi-Fi/蜂窝”字符串。

## 网络请求优先级与调度

### Dispatcher 只管理异步调用的执行时机

OkHttp 5.3.0 的 `Dispatcher` 源码把自身定义为异步请求执行策略。`maxRequests` 和 `maxRequestsPerHost` 控制通过 `Call.enqueue()` 提交的调用：超过限额的调用留在内存队列，等待已有异步调用结束。通过 `Call.execute()` 发起的同步调用会被计入 `runningCalls()`，但不会经过这两个限额的晋升判断。

这一区别会影响架构选择：

- 不能用 Dispatcher 参数为任意线程上的同步 `execute()` 提供全局限流。
- Dispatcher 没有业务优先级。它不会理解首屏、预取、遥测和大文件之间的时效差异。
- `maxRequestsPerHost` 按 URL 主机名计数；多个主机可能指向同一 IP 或代理。WebSocket 也不计入该单主机限制。
- 限额调小只会阻止新的异步调用进入执行状态，已经运行的调用不会被中止。

业务调度应位于 OkHttp 之上：

| 层级 | 职责 | 示例 |
| --- | --- | --- |
| UI / ViewModel | 生命周期与用户意图 | 页面离开时取消；重复点击合并 |
| Repository | 数据来源与新鲜度 | 选择内存、磁盘、网络或离线队列 |
| 业务调度器 | 优先级、去重、配额与截止时间 | 首屏先于预取；遥测合批 |
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

派生客户端使用新的 Dispatcher，但沿用基准客户端的连接池。限额应来自本项目的数据，同时观察 Dispatcher 排队、服务端并发能力、HTTP/2 stream、文件吞吐和交互请求尾延迟。

请求取消应由持有 `Call` 的业务作用域执行 `Call.cancel()`，或由支持取消传播的协程适配器完成。扫描 `dispatcher.queuedCalls()` 和 `runningCalls()` 再按 tag 取消只能得到一个会变化的快照，也容易误取消其他页面复用的请求。共享请求需要引用计数或订阅者模型：一个订阅者退出时，不应中止其他订阅者仍在等待的调用。

### 后台传输要按用户意图选择 API

Android 官方的[后台数据传输选择指南](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)区分了可延迟同步和用户发起的长传输：

| 场景 | 推荐机制 | 边界 |
| --- | --- | --- |
| 非用户发起、可延迟的同步或上传 | WorkManager | 工作必须可停止、可重试；约束满足不保证精确开始时间 |
| 用户发起并需要持续展示进度的长上传或下载 | Android 14 / API 34 起使用 User-Initiated Data Transfer Job | 调度时机、通知与约束需符合 UIDT 要求；旧系统准备兼容方案 |
| 平台已有专用传输 API 的场景 | 专用 API | 优先使用平台已提供的生命周期与系统集成 |
| WorkManager 和专用 API 均不适合的短时关键工作 | 符合类型要求的前台服务 | 受后台启动、时长和前台服务类型限制 |

WorkManager 的长运行 Worker 由前台服务与 JobScheduler 协作执行。Android 16 起，这类工作可能耗尽应用的 job 配额；Android 17 同样保留该边界。用户点击后启动的长文件传输，不应继续以“WorkManager 一定能无限运行”为前提。

可延迟流量应合并传输，并用 `UNMETERED`、充电和电量等约束表达成本偏好。无线电尾部耗电随设备、制式、信号和运营商配置变化，不能把某个固定秒数写进通用调度算法。

## 弱网优化从失败阶段开始

延长全部超时并增加重试次数，会让失败请求占用更多连接、线程、电量和用户等待时间。处理弱网前，应先确认失败发生在哪个阶段。

| 阶段 | 可观测信号 | 处理方向 |
| --- | --- | --- |
| Dispatcher 排队 | `dispatcherQueueStart` 到 `dispatcherQueueEnd` | 调整业务优先级、合并请求、隔离大传输 |
| DNS | `dnsStart` 到 `dnsEnd`、`UnknownHostException` | 检查目标网络、Private DNS、自定义解析和候选地址 |
| TCP | `connectStart` 到成功或 `connectFailed` | 保留多地址与 Fast Fallback，按地址族和 route 分析 |
| TLS | `secureConnectStart` 后成功或连接失败 | 检查证书链、主机名、pin、TLS 协商与连接复用 |
| 请求写入 | request body 事件、已发送字节 | 检查上传体积、写超时、取消与请求体是否可重放 |
| 响应首部 | request 完成到 `responseHeadersStart` | 检查服务端排队、CDN、上行完成时间 |
| 响应体 | response body 事件、读取字节 | 分页、压缩、断点续传、消费方读取速度 |

### 超时是分阶段预算

OkHttp 的 `connectTimeout` 约束 socket 建连阶段，`readTimeout` 和 `writeTimeout` 约束对应 I/O 操作，`callTimeout` 覆盖整次逻辑调用，包括 DNS、连接、写入、服务端处理和读取。将读超时增大，无法修复 DNS 或 Dispatcher 排队；只设置阶段超时，也无法限制重定向与重试累积后的总等待。

参数应由同一接口在不同网络类别下的分位数、用户交互截止时间和服务端服务等级目标得出。流式下载与短 API 的读取模型不同，不应共享一组机械常数。

### 区分传输恢复与业务重试

OkHttp 5.3.0 的 `retryOnConnectionFailure` 默认开启。它用于从部分连接故障中恢复，例如失效的池连接或可替代 route；这不等于应用可以再次提交任意业务操作。一次 `Call` 内部发生传输恢复后，应用层拦截器若再执行重试，实际尝试次数可能高于业务代码表面上的计数。

HTTP 语义提供起点，但服务端契约仍需确认：

- RFC 9110 把 GET、HEAD 等安全方法，以及 PUT、DELETE，定义为幂等方法。幂等描述重复相同请求的预期服务端效果，不保证响应相同，也不能修复违反规范的服务端实现。
- 非幂等方法不能仅凭“尚未收到响应”就推断服务端没有执行。支付、下单、发消息等 POST 请求需要服务端幂等键、状态查询或事务协议。
- 一次性请求体无法可靠重放。自定义流式 `RequestBody` 若只能写一次，应实现 `isOneShot()`，让客户端避免不安全的重传。
- `Retry-After` 可表达服务端期望的等待时间。503 的语义见 RFC 9110，429 的使用见 RFC 6585；客户端还要服从用户取消与整次调用截止时间。

一个可审计的重试策略至少包含以下字段：

| 字段 | 要回答的问题 |
| --- | --- |
| 失败阶段 | DNS、连接、TLS、写入、响应首部还是响应体失败 |
| 已发送状态 | 请求头或请求体是否可能已到达服务端 |
| 操作语义 | 方法是否幂等，服务端是否支持幂等键 |
| 请求体能力 | 能否重新生成，是否为 one-shot 或 duplex |
| 服务端提示 | 是否有合法的 `Retry-After` |
| 总预算 | 已尝试多少次，还剩多少调用时间 |
| 网络变化 | 默认网络是否已变化，旧 route 是否仍适用 |
| 取消状态 | 页面、任务或用户是否已取消 |

退避可以采用带随机抖动的指数策略，但基数、上限和次数必须来自业务恢复目标、服务端容量与整次截止时间。不存在对所有接口都安全的一组毫秒值。

### 网络状态不能代替端点结果

默认网络为空时，应用可以直接进入离线界面，但切网回调与请求执行仍存在时序差。网络带 `VALIDATED`，业务域名也可能故障；没有 `VALIDATED`，局域网端点仍可能可达。请求结果、端点健康和 `NetworkCapabilities` 应分别记录。

弱网体验还需要数据策略配合：列表可展示有新鲜度标记的缓存，图片可按资源版本选择较小变体，上传可持久化进度并支持断点，非必要模块可以延迟请求。缓存控制和离线写入分别见 [24.6 数据缓存](06-data-caching.md) 与 [24.7 离线优先](07-offline-first.md)。

Android 网络调用不能进入主线程。AOSP `android-17.0.0_r1` 的 `StrictMode` 在启用网络检测和对应终止策略时，由 `onNetwork()` 抛出 `NetworkOnMainThreadException`。UI 线程等待后台 `Future`、锁或 `runBlocking` 不一定触发同一异常，却仍会卡住输入与绘制，排查时要同时检查线程等待关系。

## 账号、安全与资源隔离

Cookie、认证头和业务拦截器属于请求策略，连接池本身不会保存某次请求的这些 HTTP 头。登录态和匿名态可以通过不同的派生客户端或请求构造器表达，不必仅因为账号不同就创建全新的连接池。

TLS、代理与 socket 配置会参与连接资格判断。使用不同 trust manager、hostname verifier、certificate pinner、客户端证书、代理或 DNS 时，应让配置差异在各自客户端中清楚可见，并验证 OkHttp 不会复用不兼容的连接。不要为提高复用率而关闭证书校验或放宽主机名验证。

是否使用独立连接池，可按以下条件判断：

- 是否需要独立释放资源或独立进程生命周期。
- 大传输是否经过实测持续影响交互请求，且只隔离 Dispatcher 仍不足。
- 代理、socket factory 或连接安全策略是否存在不可共享的要求。
- 独立连接池带来的额外建连、TLS 和内存成本是否可接受。

按业务团队各建一个客户端通常没有网络语义，也会让拦截器、认证、缓存和指标配置产生多份版本。应按传输与安全策略管理客户端，而不是按模块目录管理。

## Wi-Fi 选网只保留应用观测边界

默认网络由 Connectivity 系统按请求能力、网络评分、用户选择、验证状态和设备配置决定，应用不能用一个 RSSI 阈值复现系统结果。相关源码链路见 [24.9 Wi-Fi 评分、网络选择与连接切换性能](09-wifi-connectivity-selection.md)。

应用侧应记录：

- 默认 `Network` 身份与变化序号。
- transport、`VALIDATED`、`NOT_METERED`、VPN 和 captive portal 等低基数信号。
- Dispatcher 排队、DNS、每次 connect attempt、TLS、请求写入、TTFB 和响应体读取。
- 使用的协议、连接是否复用、缓存命中与失败阶段。

系统侧再结合 bugreport、`dumpsys connectivity`、`dumpsys wifi`、Perfetto 和 logcat 还原选网过程。应用指标里的“Wi-Fi”只说明传输类型，不能直接推断计费、互联网可达性或信号质量。

## 工程检查清单

- 是否共享基准 `OkHttpClient`，并明确哪些派生客户端共享连接池。
- 同步 `execute()` 是否由调用方限流，是否错误地把 Dispatcher 参数当成同步限额。
- 是否关闭每个响应体，并测试取消、异常和提前返回路径。
- EventListener 是否允许事件缺席、重复和交错，回调中是否避免阻塞工作。
- HTTPDNS 是否保留原主机名、TTL、多地址、网络身份和引导解析策略。
- HTTPDNS 对 Private DNS、VPN、企业分流和隐私承诺的影响是否经过评审。
- 网络状态是否来自回调参数，是否避免把 `VALIDATED` 当作业务端点前置条件。
- 页面取消是否直接作用于所持有的 `Call`，共享请求是否保护其他订阅者。
- 可延迟工作、用户发起的长传输和前台服务是否按 Android 17 规则选择。
- 重试是否同时检查失败阶段、幂等语义、请求体能力、服务端提示和总截止时间。
- 大传输是否根据 `NOT_METERED` 与用户意图决策，而不是只看 Wi-Fi transport。
- 是否用 MockWebServer 等测试工具覆盖断连、慢响应体、TLS 失败、重定向和重试，并在设备上覆盖 VPN、Private DNS、IPv6、切网与 captive portal。

## 继续阅读

- [24.5 协议优化](05-protocol-optimization.md)：HTTP/2、HTTP/3、gRPC 与协议协商。
- [24.6 数据缓存](06-data-caching.md)：HTTP 缓存、多级缓存与新鲜度。
- [24.7 离线优先](07-offline-first.md)：离线队列、同步和冲突处理。
- [24.9 Wi-Fi 连接与选择](09-wifi-connectivity-selection.md)：系统评分、默认网络与切换。
- [24.16 Android 17 流媒体与本地网络](16-android17-streaming-local-network.md)：局域网能力与 Android 17 访问边界。

## 源码与规范依据

- [AOSP `android-17.0.0_r1` NetworkCapabilities](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)
- [AOSP `android-17.0.0_r1` ConnectivityManager 与 NetworkCallback](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java)
- [AOSP `android-17.0.0_r1` DnsResolver](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/DnsResolver.java)
- [AOSP `android-17.0.0_r1` StrictMode](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/StrictMode.java)
- [Android DNS Resolver Mainline 模块](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
- [Android 读取网络状态指南](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Android 后台数据传输选择指南](https://developer.android.com/develop/background-work/background-tasks/data-transfer-options)
- [Android User-Initiated Data Transfer Job](https://developer.android.com/develop/background-work/background-tasks/uidt)
- [Android WorkManager 长运行 Worker](https://developer.android.com/develop/background-work/background-tasks/persistent/how-to/long-running)
- [OkHttp 5.3.0 OkHttpClient](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt)
- [OkHttp 5.3.0 Dispatcher](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dispatcher.kt)
- [OkHttp 5.3.0 Dns](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
- [OkHttp 5.3.0 EventListener](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
- [OkHttp 5.3.0 ResponseBody](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ResponseBody.kt)
- [OkHttp 5.3.0 RequestBody](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/RequestBody.kt)
- [RFC 9110：HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
- [RFC 6585：Additional HTTP Status Codes](https://www.rfc-editor.org/rfc/rfc6585.html)
