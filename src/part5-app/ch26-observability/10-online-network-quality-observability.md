---
title: 线上网络质量监控与接入层对账
chapter: '26.10'
section: '26.10'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-10-04'
last_source_verified_at: '2026-10-04'
last_verified_against: Android network-state guide updated 2026-10-01; Android 17 android-17.0.0_r1 Connectivity sources; TrafficStats and NetworkCapabilities API references; OkHttp 5.5.0 Maven metadata and EventListener source; Cronet references updated 2026-07-31, API 143.7445.0, and 500.1.0 artifact migration POMs, retrieved 2026-10-04
confidence: high
sources:
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md
- type: official
  path: https://developer.android.com/reference/android/net/TrafficStats
- type: official
  path: https://developer.android.com/reference/android/net/NetworkCapabilities
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/reading-network-state
- type: legacy-reference-preserved
  path: https://square.github.io/okhttp/5.x/okhttp/okhttp3/-event-listener/
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework-t/src/android/net/TrafficStats.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo.Metrics
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/UrlResponseInfo
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/start
- type: library-api
  path: https://dl.google.com/dl/android/maven2/org/chromium/net/cronet-api/143.7445.0/cronet-api-143.7445.0.aar
- type: library-api
  path: https://repo1.maven.org/maven2/com/squareup/okhttp3/okhttp/maven-metadata.xml
- type: library-api
  path: https://github.com/square/okhttp/blob/parent-5.5.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt
- type: library-api
  path: https://github.com/square/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt
- type: library-api
  path: https://github.com/square/okhttp/blob/parent-5.5.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/FastFallbackExchangeFinder.kt
- type: library-api
  path: https://dl.google.com/dl/android/maven2/org/chromium/net/cronet-api/maven-metadata.xml
- type: library-api
  path: https://dl.google.com/dl/android/maven2/org/chromium/net/cronet-api/500.1.0/cronet-api-500.1.0.pom
- type: library-api
  path: https://dl.google.com/dl/android/maven2/org/chromium/net/cronet/500.1.0/cronet-500.1.0.pom
tags:
- observability
- network
- trafficstats
- apm
- alerting
related_chapters:
- '17.7'
- '24.5'
- '24.7'
- '26.1'
- '26.3'
last_draft_polish_at: '2026-08-15T21:22:20+08:00'
last_review_finalize_at: '2026-08-15T21:22:20+08:00'
last_rework_at: '2026-08-15T21:22:20+08:00'
---

# 线上网络质量监控与接入层对账

网络质量监控要回答三个问题：时间花在哪个阶段，哪些用户受到影响，客户端和接入层记录的是否为同一次请求。这里的接入层，指面向公网接收请求的 CDN、边缘节点或 API 网关。如果只存一个接口总耗时，队列、DNS 解析、路由尝试、TLS 握手、请求发送、首个响应头、响应体读取、重定向与重试就全部混在一个数值里，出了问题我们无从下手。

> 源码基线：AOSP `android-17.0.0_r1`（API 37）。OkHttp 与 Cronet 是独立发布的网络库，不受平台版本约束，事件里要记录网络库、库版本和协议。连接管理见 24.5，HTTPDNS 见 24.7，底层网络 APM（application performance monitoring，应用性能监控）见 17.8，通用采样与上报见 26.1。

## 网络监控的分层目标

排查一次网络故障时，我们手上至少有三套观察口径：客户端样本、接入层日志、系统网络状态。三套口径回答的问题不同，各自都留着盲区，所以要看全得把它们对起来。

| 观察层 | 能回答的问题 | 常见盲区 | 适合的动作 |
| --- | --- | --- | --- |
| 客户端样本 | 用户当时的网络能力、阶段耗时、失败异常、路由尝试、页面场景 | 上报通道也可能受故障影响；采样和延迟上传会改变可见分布 | 判断用户体验，识别受影响版本、设备、粗粒度地域或网络分组 |
| 接入层日志 | 请求是否到达入口、入口流量是否下跌、服务端处理耗时、状态码分布 | 客户端 DNS 失败、建连失败、被代理/VPN 拦截的请求可能看不到 | 秒级告警、定位入口集群/CDN/域名异常 |
| 系统网络状态 | 默认网络、传输类型、VPN、计费网络、互联网验证、受限网络 | App 拿不到无线驱动、基站、运营商内部路由的完整状态 | 解释网络切换、Captive Portal（需要网页认证的受限网络）、代理/VPN 干扰 |

三套口径各管一段：客户端样本解释用户侧经历，接入层日志显示已到达入口的请求，系统状态说明 App 当时可见的默认网络。我们把它们关联起来靠的是 `trace_id`、`request_id` 和 `attempt_id`（四层请求 ID 的定义见下文「客户端阶段耗时采集」）。其中有一类记录要特别留意：DNS、connect 或 TLS 阶段失败的 attempt 根本到不了服务器，服务端自然没有同名 ID。对账时这类只在客户端出现的记录必须保留，丢了它们，入口前失败就成了盲区。

## 客户端阶段耗时采集

排查网络慢或失败时，我们要把耗时按请求生命周期拆开记录，只存一个 `duration_ms` 是回答不了“慢在哪一段”的。动手前先区分四个对象：

- `trace_id` 对应一次用户操作或完整业务请求路径；
- `request_id` 对应网络库的一次逻辑调用；
- `attempt_id` 对应一次路由或连接尝试；
- `exchange_id` 对应一次请求与响应交换；重定向、认证质询等自动后续请求（follow-up）会产生新的 exchange。

这四层 ID 规定了怎么把多个事件归到同一次用户操作。同一个 `request_id` 里可能发生多次 DNS、connect 或 `connectionAcquired`，也可能因为复用已有连接，完全没有 DNS、connect 和 TLS 事件。这就带来一个问题：如果采集器只为每个阶段保留一个开始时间，后一次路由尝试就会覆盖前一次失败，算出来的分段之和也可能和调用总耗时对不上。

落到具体采集器，先看 OkHttp。截至 2026 年 10 月 4 日，`com.squareup.okhttp3:okhttp` 的 Maven metadata 标记 release 为 5.5.0；其 [`EventListener` 5.5.0 源码](https://github.com/square/okhttp/blob/parent-5.5.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt) 与 [`EventListener` 5.4.0 源码](https://github.com/square/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt) 一致。

从 dispatcher（请求调度器）排队，到 DNS、建连、安全连接、连接获取、请求发送和响应读取，这些事件都属于同一个 `Call`。要注意的是事件序列并非固定：connect 系列事件可能因候选路由与 Fast Fallback 重复出现——Fast Fallback 会交错尝试多个地址，缩短单一路径迟迟无法建连造成的等待；`connectionAcquired` 也可能在一个 `Call` 中出现多次；反过来，连接复用时 DNS、connect 和 TLS 事件又可能缺席。所以采集器要保存有序事件和对应的 attempt/exchange，事件序列长什么样，就按什么样子记。

Cronet 这边，公开采集入口是 `org.chromium.net.RequestFinishedInfo.Listener`。本文逐方法核验的 API 版本为 `143.7445.0`；[`RequestFinishedInfo.Metrics`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo.Metrics) 提供请求开始、DNS、建连、SSL、发送、响应开始和请求结束时间戳，以及套接字复用、TTFB（time to first byte，收到首个响应字节前的时间）、总耗时和可空的传输字节数。没有发生或无法取得的阶段返回 `null`；复用连接时 DNS、connect 和 SSL 均为空。还有一个容易误读的点：DNS 命中本地缓存但没有复用 socket 时，Cronet 仍可给出 DNS 时间戳，所以“存在 DNS 事件”离“访问了远端 DNS”还差一步，要区分开。

还有一个版本陷阱：Google Maven 目前把 `cronet-api:500.1.0` 标为 release，但其 [`POM`](https://dl.google.com/dl/android/maven2/org/chromium/net/cronet-api/500.1.0/cronet-api-500.1.0.pom)（Maven 依赖描述文件）明确说明这是已废弃的过渡空工件，只负责引入 `org.chromium.net:cronet:500.1.0`；新项目应直接依赖 `cronet`。所以 `cronet-api` 元数据里的最新版本号，离实际引擎版本还差一层，也谈不上据此假定 143.7445.0 的方法语义原样延续。事件里应同时记录依赖坐标、API 版本、`provider`（实现提供方）和引擎版本，升级后重新核对可空字段与字节口径。

字节字段也要注明来源：`Metrics#getReceivedByteCount()` 是当前请求的传输层接收字节，不包含之前的重定向；`UrlResponseInfo#getReceivedByteCount()` 是从请求开始累计到当前响应的最小接收字节估计，包含重定向但不覆盖所有协议开销。这两个口径不同的字段，我们要分开记，别混进同一指标序列。

平台这边没有现成入口：AOSP `android-17.0.0_r1` 没有向 App 提供 `android.net.http.RequestFinishedInfo` 这一公共 API，Cronet 独立于平台版本发布，App 应使用 `org.chromium.net` 公共 API，并在事件中记录 Cronet 版本。另外别忘了覆盖面：Cronet 看不到绕过它的 OkHttp、`HttpURLConnection` 或 Native 自研协议。

自研网络库应把阶段事件纳入接口设计。下表用 `observed` 表示采集器看到了该阶段，`not_observed` 表示该阶段未发生或未被回调覆盖，`unsupported` 表示当前库不提供该字段。

| 字段组 | 示例字段 | 说明 |
| --- | --- | --- |
| 请求身份 | `trace_id`、`request_id`、`attempt_id`、`exchange_id`、`scene_id`、`endpoint_id` | `endpoint_id` 来自受控的主机名与路径模板，不上传完整 URL 与查询参数 |
| 实现信息 | `engine`、`engine_version`、`negotiated_protocol`、`collector_version` | 区分平台、网络库和采集器升级引起的口径变化 |
| 阶段时间 | `queue_ms`、`dns_ms`、`connect_ms`、`secure_handshake_ms`、`ttfb_ms`、`body_ms`、`total_ms` | 每个阶段同时记录 `observed`、`not_observed` 或 `unsupported`；连接复用时阶段未发生，不能记成 0 ms |
| 网络现场 | `network_snapshot_id`、`transports`、`validated`、`metered`、`vpn`、`proxy_present` | `network_snapshot_id` 是端侧短期关联键，不上传原始 `Network` 标识 |
| 失败与重试 | `error_domain`、`error_code`、`http_code`、`route_index`、`retry_reason`、`peer_group_id` | Java 异常未必暴露稳定 errno（操作系统错误号）；错误类和库内枚举优先于解析异常文案 |
| 上报状态 | `sample_rate`、`upload_channel`、`upload_delay_ms`、`dropped_reason` | 网络故障时，上报失败本身也是证据 |

这张表和 26.1 的性能指标模型保持一致：事件回调只记录轻量时间戳、枚举和引用，序列化、压缩、写入本地文件与上传交给后台任务。我们尤其要守住一条底线：主线程、OkHttp callback（回调函数）或 Cronet listener（监听器）里做磁盘 I/O，会直接干扰被测请求。

## QUIC / HTTP/3 指标口径

协议一变，阶段字段的含义就要重新对。QUIC 是在 UDP 之上集成加密与多路复用的传输协议，HTTP/3 以它为基础。落到指标上，`connect_ms` 的含义随协议变化：遇到 QUIC，它就不再是固定的 TCP 三次握手；`secure_handshake_ms` 同理，不再是固定的 TCP 上的 TLS。所以公共指标用协议中性的字段名，并记录 `negotiated_protocol`。Cronet 的 [`UrlResponseInfo#getNegotiatedProtocol()`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/UrlResponseInfo) 返回协商协议，也可能为空。

在 Cronet `143.7445.0` 中，QUIC 的 SSL 开始/结束分别等于 connect 开始/结束；使用 0-RTT（在握手确认前发送早期数据）时，connect end 表示握手确认，可能晚于 sending start。HTTP/2 与 QUIC 会在一条连接上承载多个 stream（独立请求流），首个 stream 之后的 `getSocketReused()` 返回 `true`，DNS、connect 和 SSL 时间随之为空。看到同一请求中 `sendingStart < connectEnd`，我们只能按 Cronet 文档解释时间顺序；要得到准确的 `zero_rtt_used=true`，还要靠别的证据。

该版本公开的 `RequestFinishedInfo.Metrics` 没有稳定字段暴露 0-RTT 是否使用、连接迁移次数、路径验证耗时或丢包率。只有选定引擎通过公开且有版本说明的 API 提供这些数据时，才能把它们放入扩展字段，并同时记录 `engine`、`engine_version`、`metric_source` 和字段可用性。协议内部状态，我们只从公开 API 拿，套接字重用、阶段先后顺序或异常文本都推算不出它。

## 流量与网络状态维度

流量层面我们用 `TrafficStats` 观察趋势，但要清楚它提供的是累计计数器，口径以 `android-17.0.0_r1` 的 [`TrafficStats.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework-t/src/android/net/TrafficStats.java) 为准：

- 计数覆盖自开机以来、所有网络接口上的网络层流量，包含 TCP 和 UDP，设备重启后归零；
- `getUidRxBytes()` 和 `getUidTxBytes()` 聚合同一 UID（Android 为应用分配的用户标识）下的所有进程；Android 7.0 起，普通 App 查询其他 UID 会得到 `UNSUPPORTED`；
- 设备不支持某项统计时也会返回 `UNSUPPORTED`，`-1` 别当有效字节数；
- `getTotalRxBytes()` 和 `getTotalTxBytes()` 是整台设备口径，看 App 自己的流量时要换回 UID 口径。

看板应保存 `boot_id`（设备本次开机的标识）或等价标记、采集时间和前后差值，一旦发现计数变小、启动标记变化或任一端为 `UNSUPPORTED`，就舍弃该区间差值。另外 `TrafficStats.tagSocket()` 可以给 socket 计账加标签，但它只是计数器，给不出 DNS、握手和首包时间，逐请求事件还是要靠网络库。

流量指标常用于三类分析：

- **版本回归**：新版本在同等访问量（PV）下 UID 发送字节数上升，可能是重试次数、图片规格、日志上报或轮询策略变化。
- **故障旁证**：某个运营商请求失败率升高，同时发送字节数上升、接收字节数下降，常见原因是连接建立后响应读不到，或客户端在短时间内大量重试。
- **上报通道健康度**：业务请求失败率升高时，监控上报自身的发送/接收量和延迟要单独看，避免把“没有上报”误读成“没有故障”。

网络状态这边，`NetworkCapabilities` 描述系统当前知道的网络属性，读它时心里要有数：`NET_CAPABILITY_INTERNET` 表示网络被配置为可访问互联网，离“已经连通”还差一次实际访问；`NET_CAPABILITY_VALIDATED` 表示系统探测到公共互联网，要证明某个业务域名可达，还得看那次请求本身。Captive Portal 探测期间通常有 `INTERNET` 和 `CAPTIVE_PORTAL`，没有 `VALIDATED`。Wi-Fi、蜂窝和 VPN 都是 transport（网络承载类型）；一张网络可以同时具有多个 transport，例如 VPN 运行在 Wi-Fi 与蜂窝之上。

网络状态要按样本发生的时刻记录。使用 `registerDefaultNetworkCallback()` 时，Android 8.0 及以上会在 `onAvailable()` 后立即给出 `onCapabilitiesChanged()` 和 `onLinkPropertiesChanged()`，所以在 `onAvailable()` 里同步查询新网络属性会撞上时序竞争（竞态），等后两个回调到了再读。默认网络回调的 `onLost()` 同样要读准：它只说明这张网络不再是 App 的默认网络，它未必已经断开。

默认网络回调运行在 App 的 `ConnectivityManager` 专用线程，所以回调里只更新创建后不再修改的内存快照，耗时计算与上传放到工作线程，并在不再使用时注销该回调。`Network` 对象也一样有生命周期：它仅在该次连接存续期内有效，同一接入点重连后也会得到新对象，端侧短期关联够用，跨会话的设备或网络标识要另想办法。

## Native Hook 与统一网络库的边界

网络监控入口有四类：编译期插桩（构建时在字节码中加入观测代码）、库层回调、Native Hook（运行时拦截本地函数调用）、统一网络库。

| 方案 | 覆盖面 | 优点 | 风险 |
| --- | --- | --- | --- |
| 编译期插桩 | App 代码和可插桩的第三方软件开发工具包（SDK）中的 `HttpURLConnection` / OkHttp 创建点 | 接入成本低，能补业务 `trace_id` | 反射、动态加载、Native 请求、已混淆封装可能漏采 |
| OkHttp / Cronet 官方指标 | 使用对应网络库的请求 | 阶段口径清楚，版本兼容性由库维护 | 覆盖不到绕开统一库的 SDK；事件语义要按连接复用和重试建模 |
| Native / PLT Hook | 动态链接且符号可见的 `connect`、`send`、`recv`、`SSL_read`、`SSL_write` 等调用 | 能发现部分绕过 Java 网络层的调用和总流量 | Android 版本、ABI（应用二进制接口）、符号、加固和静态链接都会影响覆盖率；发布前必须先向少量用户启用 |
| 统一网络库 | App 自有业务请求 | 适合统一策略、观测事件、`trace_id`、HTTPDNS、重试和容灾 | 迁移成本高；三方 SDK 和 WebView 仍需单独监控 |

PLT（Procedure Linkage Table，过程链接表）保存动态函数的跳转入口，PLT Hook 只能拦截经过目标表项的调用。这条路有绕不过的死角：静态链接的 BoringSSL、隐藏符号、直接系统调用以及 Cronet 的 QUIC/UDP 协议状态都可能绕开这些入口；就算捕获到 `send`/`recv`，要可靠恢复 HTTP/2 stream、QUIC stream 或一次逻辑请求的边界也做不到。所以 Hook 适合补充覆盖，可解释的阶段指标还是交给统一网络库和官方事件接口。（详见 17.8 节）

每条 Hook 样本还应记录采集器版本、ABI、命中入口与已知覆盖范围。工程上还有两条护栏：ASM 字节码插桩要配合构建期允许名单和回滚开关；Native Hook 需要按 ABI 小范围启用、监控崩溃率、支持远程关闭和端上自检。采集一旦失败就 fail-open，也就是停用采集并让业务请求继续执行。

## 客户端与接入层对账

进入对账前先摆正预期：客户端与接入层采用不同的采集范围，两边数字本来就可能不同；真出现差异时，差异本身就是故障信号。

| 差异类型 | 客户端看到 | 接入层看到 | 排查方向 |
| --- | --- | --- | --- |
| 请求未到达入口 | DNS 失败、connect timeout、TLS failure、代理/VPN 失败 | 没有对应 `request_id`；入口 PV 可能下跌 | DNS、运营商、CDN、证书、网络切换、HTTPDNS 缓存 |
| 入口秒级异常 | 客户端样本延迟到达或上报失败 | 入口流量、错误率、处理耗时秒级变化 | 服务端发布、入口集群、CDN、机房、限流策略 |
| 客户端维度更丰富 | 某机型/系统/版本/网络类型集中异常 | 入口只看到域名、状态码、地域或 IP 段 | App 版本、设备兼容、网络库升级、代理/VPN、运营商 |

对账 ID 必须在客户端发起请求前生成：`trace_id` 描述完整业务请求路径，`request_id` 描述网络库调用，`attempt_id` 描述客户端路由或重试。两边各记各的账：只有请求头成功发到入口时，服务端才可能读到这些 ID，DNS、connect、TLS 阶段失败的 attempt 只存在于客户端；接入层记录收到的 ID、入口节点、协商协议、状态码、服务端处理耗时和响应字节数，客户端记录相同 ID 对应的阶段与 attempt 结局。

对账的第一步，是把两边记录按 `request_id + attempt_id` 对起来，区分出三种集合：两侧都有记录、只有客户端记录、只有接入层记录。第一类可比较端到端耗时与服务端耗时；第二类用于分析入口前失败；第三类提示客户端采样、ID 注入或上报丢失。重定向和重试还要按 `exchange_id` 或接入层生成的 span（分布式追踪中的单段操作）区分，避免把多次响应的字节数、状态码和耗时相加后误认为一次请求。

未到达入口的样本同样有价值，仍应保存受控证据，例如候选地址数量、脱敏后的 peer（对端节点）分组、库级错误枚举、TLS 错误类别、代理/VPN 标记和网络快照。哪些字段留在端侧、哪些能进通用遥测，边界要划清：原始 DNS 列表、完整 IP、完整 URL、查询参数、代理地址与系统 `Network` 标识不应作为通用遥测字段。

## 实时告警与离线分析

监控建起来之后怎么用？我们把网络质量监控分为实时发现、交互式分析和离线复盘三层。时间窗口由业务流量与响应目标决定，表中只划分职责，不给所有应用套一组固定时长。

| 层次 | 指标 | 维度控制 | 输出 |
| --- | --- | --- | --- |
| 实时发现 | 入口请求量、错误率、超时率、5xx、关键接口延迟、客户端上报延迟与预计到达量 | 只保留 endpoint（受控接口标识）、版本、粗粒度地域、网络分组等取值种类较少的字段 | 告警、影响面初判、是否回滚或调整入口流量去向 |
| 交互式分析 | 阶段耗时分位值、错误类别、路由尝试、重试、样本覆盖率、上报丢失率 | 按需要展开设备、系统、App 版本、CDN、peer 分组、协议和场景 | 确定故障范围和触发条件 |
| 离线复盘 | 长尾分布、失败样本聚类、版本对比、地域或网络分组趋势 | 受权限控制的明细与聚合数据，过滤低样本噪声 | 修复验证、容量规划、规则调整 |

实时告警不展开取值种类很多的高基数字段。每个分位值与错误率都要同时展示样本数、采样率、覆盖率和数据新鲜度——低样本量下 P90/P99（90/99 分位值）的波动，离“用户体验突变”还隔着一个样本量的问题。还有一类系统性盲区要单独盯：客户端网络故障还会阻断遥测上传，“已收到的失败率”因此存在幸存者偏差，无法上报的失败用户没有进入统计。所以接入层请求量下降、客户端待上传队列增长、上传延迟升高和预计样本缺口应一起报警。

尾延迟是少量最慢请求形成的分布尾部，需要结合阶段分布分析：DNS 长尾指向解析、调度和网络切换；connect 长尾指向候选路由、可达性、CDN 和防火墙；TTFB 同时包含客户端到入口的传输、入口排队与服务端处理，要归因到服务端还得带上另外两段一起看；响应体读取阶段（body）长尾还会受响应大小、网络路径吞吐和应用读取速度影响。指标帮我们缩小检索范围，结论仍需客户端事件、接入层日志和服务端 span 相互验证。

## 规则与时间序列报警边界

报警引擎怎么选？网络报警适合组合规则与时间序列模型：规则处理入口请求量突变、5xx 偏离基线、某 endpoint DNS 失败率异常等明确现象；时间序列模型处理流量周期、地域时区、节假日和运营活动带来的自然波动。

但算法弥补不了指标缺失：输入里没有阶段耗时、协议、样本覆盖率和上报健康度，模型就只能发现某个总耗时发生了变化，找不到阶段。落到配置上，主入口可采用少量可解释规则，高流量 endpoint 和关键场景再使用按星期、时段和发布状态分组的历史基线。低流量接口独立做 P99 异常检测样本不够，可换用错误样本聚类、相邻 endpoint 联动和人工复核。

误报和漏报本身也要计量：每条规则记录触发、确认故障、误报原因、漏报补录和处置动作；模型版本、训练区间、特征可用性与阈值配置需要可追溯。规则变更先影子运行，也就是只计算结果而不通知值班，再根据历史回放和线上反馈决定是否正式告警。

## 网络故障证据包

真到复盘一次线上网络故障时，证据包要能回答三件事：影响范围多大、怎么模拟触发条件、修复有没有生效。字段按采样策略与数据分级收集，严重故障也不能绕过隐私、权限和保留期限约束。

| 字段组 | 必要字段 | 用途 |
| --- | --- | --- |
| 用户与版本 | 轮换或用 HMAC（带密钥的消息认证码）处理的关联 ID、App 版本、渠道、设备类别、Android 版本、粗粒度地区 | 判断是否集中在版本、设备类别、地区或分批发布人群 |
| 网络环境 | `network_snapshot_id`、transport 集合、`VALIDATED`、`CAPTIVE_PORTAL`、VPN、是否存在代理、计费与漫游状态、网络分组 | 解释网络切换和受限网络；MCC/MNC（移动国家码/移动网络码）在双卡或 VPN 场景不等同于请求实际使用的网络路径 |
| 请求身份 | `trace_id`、`request_id`、`attempt_id`、`exchange_id`、`endpoint_id`、协商协议、CDN/接入点、`peer_group_id`（对端节点分组） | 与接入层日志对账；不记录完整 URL、查询参数和原始 IP |
| 阶段耗时 | `queue_ms`、`dns_ms`、`connect_ms`、`secure_handshake_ms`、发送、TTFB、`body_ms`、`total_ms`、复用状态与阶段可用性 | 判断可观测时间花在哪一段 |
| 失败信息 | 网络库、异常类、稳定错误枚举、HTTP 状态码、业务错误码、超时类别、路由与重试结局 | Java 层没有稳定 errno 时保留 `unknown`，不解析本地化异常消息 |
| 上报健康度 | 样本采样率、写入本地成功、上传时间、上传网络、丢弃原因、压缩后大小 | 判断监控数据是否受同一故障影响 |

还有一条红线：运营商、MCC/MNC、城市、IP、DNS 服务器、代理、SSID（Wi-Fi 网络名）和 BSSID（接入点标识）都可能构成敏感或可识别信息。地域、网络分组和 peer 分组能由接入层生成的优先在服务端生成；端侧只收集诊断所需的最小范围，并保留“未知”，不要拿设备 SIM 信息强行推断请求路径归属。

26.3 给出了通用线上问题证据包模板，网络场景再补充请求尝试、阶段可用性、接入层日志索引和遥测上传状态。这样排障人员就能回答：哪个 endpoint 与协议受影响、客户端在哪个阶段结束、请求是否到达入口、服务端记录如何、样本缺口有多大。

## Wi-Fi 稳定性与系统网络验证

Wi-Fi 排障时先认清能力边界：应用侧无法从普通公开 API 获得 Wi-Fi 射频、AP（无线接入点）拥塞和运营商内部路由的完整事实，但可以使用系统能力缩小检索范围。`NET_CAPABILITY_VALIDATED` 只说明系统探针在最近一次判断中访问了公共互联网，App 的业务域名、证书链、代理路径或当前时刻是否可用，还要靠那次请求自己验证；`CAPTIVE_PORTAL=true` 且 `VALIDATED=false` 是门户登录的重要旁证，但业务错误还可能有其他原因。

Wi-Fi 也不能默认标记为“不计费”或“比蜂窝快”，应分别读取 `NOT_METERED` 和系统给出的带宽估计，估计值当作提示而非实测吞吐。VPN 网络还可能同时带有 VPN、Wi-Fi 和蜂窝承载类型，数据模型应保存集合，不要用单值枚举覆盖信息。

系统和厂商的网络选择策略会在会话内切换默认网络，所以网络快照应绑定到 `request_id`/`attempt_id`。一个典型场景：请求 A 在旧默认网络失败，请求 B 切换后成功，这两条样本来自不同的网络，聚合成同一网络的自动恢复就错了。默认网络回调的 `onLost()` 只代表网络失去默认地位；若业务显式绑定了其他 `Network`，就必须使用该请求选中的网络快照，全局默认快照用不上。

Android 官方的 [Read network state](https://developer.android.com/develop/connectivity/network-ops/reading-network-state) 说明了 `Network` 生命周期、多种承载类型、`VALIDATED`、回调顺序和 `onLost()` 边界；平台实现可对照 `android-17.0.0_r1` 的 [`ConnectivityManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java) 与 [`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)。

## 全文小结

回到开头的三个问题。一套可用的网络质量系统，手里要有三份记录：客户端保存逻辑调用、attempt、exchange、阶段可用性和请求所用网络的快照；接入层保存已经到达入口的事实；遥测通道报告自身的延迟与缺口。三侧记录用 `trace_id`/`request_id`/`attempt_id` 对账，再结合协议、网络分组和库版本解释差异。这样得到的结论既能指出时间花在哪一段，也会明确哪些阶段没有观测到、哪些请求从未到达服务器。
