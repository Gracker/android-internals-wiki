---
title: HTTP/2、HTTP/3、gRPC 与 ECH
chapter: '24.6'
section: '24.6'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-08-15'
last_verified_against: AOSP android-17.0.0_r1 and Android common kernel android17-6.18-2026-06_r6; Android Developers HttpEngine, Cronet and API reference updated through 2026-08-03; OkHttp 5.4.0 source and changelog; IETF RFC 9000, 9001, 9113 and 9114; current gRPC guides
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/HttpEngine.java
- type: aosp
  path: https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/ConnectionMigrationOptions.java
- type: aosp
  path: https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/UrlResponseInfo.java
- type: aosp-kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c
- type: official
  path: https://developer.android.com/reference/android/net/http/HttpEngine.Builder
- type: official
  path: https://developer.android.com/reference/android/net/http/ConnectionMigrationOptions
- type: official
  path: https://developer.android.com/reference/android/net/http/UrlResponseInfo
- type: official
  path: https://developer.android.com/reference/android/net/http/FinishedRequestTimings
- type: official
  path: https://developer.android.com/reference/android/net/http/UrlRequest
- type: official
  path: https://developer.android.com/develop/connectivity/cronet
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/integration
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/main/CHANGELOG.md
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt
- type: official
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt
- type: legacy-reference-preserved
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt
- type: standard
  path: https://www.rfc-editor.org/rfc/rfc9113.html
- type: standard
  path: https://www.rfc-editor.org/rfc/rfc9000.html
- type: standard
  path: https://www.rfc-editor.org/rfc/rfc9001.html
- type: standard
  path: https://www.rfc-editor.org/rfc/rfc9114.html
- type: official
  path: https://grpc.io/docs/platforms/android/java/basics/
- type: official
  path: https://grpc.io/docs/guides/deadlines/
- type: official
  path: https://grpc.io/docs/guides/wait-for-ready/
- type: official
  path: https://grpc.io/docs/guides/retry/
- type: official
  path: https://grpc.io/docs/guides/flow-control/
- type: official
  path: https://grpc.io/docs/guides/keepalive/
- type: official
  path: https://grpc.io/docs/guides/performance/
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/privacy-and-security/security-config
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/reference/android/net/DnsResolver
- type: official
  path: https://developer.android.com/reference/android/net/dns/HttpsRecord
- type: official
  path: https://developer.android.com/reference/android/net/ssl/SSLSockets
- type: official
  path: https://developer.android.com/reference/android/net/ssl/SSLEngines
- type: official
  path: https://developer.android.com/reference/android/net/ssl/EchConfigMismatchException
- type: official
  path: https://developer.android.com/reference/android/security/NetworkSecurityPolicy
- type: rfc
  path: https://www.rfc-editor.org/rfc/rfc9849
- type: rfc
  path: https://www.rfc-editor.org/rfc/rfc9460
- type: upstream
  path: https://github.com/lysine-dev/okhttp/pull/9573
- type: upstream
  path: https://github.com/lysine-dev/okhttp/pull/9596
- type: upstream
  path: https://github.com/lysine-dev/okhttp/tree/parent-5.4.0
- type: upstream
  path: https://chromium.googlesource.com/chromium/src/net/+/40d5138e2f148890a937d6653284074cd3c3676d
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]'
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]'
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]'
tags:
- http2
- http3
- quic
- grpc
- protocol
- network
- tls
- ech
- android17
- network-security-config
related_chapters:
- '24.5'
- '12.1'
- '24.9'
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_review_finalize_at: '2026-08-15T10:21:03+08:00'
last_review_finalize_run_id: 20260815-102103-gracker-writing-review
last_draft_polish_at: '2026-08-15T10:21:03+08:00'
last_draft_polish_run_id: 20260815-102103-gracker-writing
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch24-io-network/05-protocol-optimization.md
- src/part5-app/ch24-io-network/15-android17-ech-domain-encryption.md
---

# HTTP/2、HTTP/3、gRPC 与 ECH

HTTP/2 在 TCP 上复用流，HTTP/3 在 QUIC 上处理传输和拥塞，gRPC 在 HTTP/2 或 HTTP/3 上定义 RPC 语义。ECH 保护 ClientHello 中的目标信息，但依赖 DNS HTTPS 记录和服务端部署。

## 多路复用、QUIC 与 RPC 流控制

### 协议名称不等于性能收益

HTTP/2、HTTP/3 和 gRPC 解决的问题不同：

- HTTP/2 用逻辑流（stream）复用和 HPACK 首部压缩，减少并发请求对连接数量与重复首部字节的需求。
- HTTP/3 在 QUIC 传输协议上提供 HTTP 语义。QUIC 的每条逻辑流独立排序，可避免 TCP 丢包让同一连接所有流一起等待的传输层队头阻塞，并支持连接迁移。
- gRPC 是远程过程调用（Remote Procedure Call，RPC）框架和接口契约；Android 常用实现仍通过 HTTP/2 传输，它不等于 HTTP/3。

平台锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，客户端与协议依据为 OkHttp 5.4.0、RFC 9113、RFC 9000、RFC 9001、RFC 9114 和当前 gRPC 官方文档。连接池、DNS、超时和重试边界见 [24.5 移动网络架构、连接与容灾](05-mobile-network-connection-resilience.md)，分段性能与 TLS 见 [12.1 Android 网络与 TLS 性能优化](../../part2-performance/ch12-apk-network/01-android-network-tls-performance.md)。

### 协议能力来自不同组件

Android 项目常见的协议能力来自不同组件：

| 组件 | Android 17 下的协议能力 | 版本边界 |
| --- | --- | --- |
| OkHttp 5.4.0 | HTTP/1.1、HTTP/2 | 没有稳定的公开 HTTP/3 配置入口 |
| `android.net.http.HttpEngine` | 由设备提供的 HTTP 引擎处理 HTTP/1.1、HTTP/2、HTTP/3 | API 34 起可用，也可由 S Extensions 7（系统组件扩展版本 7）提供；实际能力受设备实现影响 |
| Cronet 库 | Chromium 网络栈，支持 HTTP/1.1、HTTP/2 和基于 QUIC 的 HTTP/3 | 能力取决于项目采用的 Cronet 实现与版本 |
| gRPC Java / Kotlin | RPC 语义、生成的客户端代理（stub）、流式调用、调用截止时间（deadline）与状态码 | Android 常用传输基于 HTTP/2，也可评估 Cronet 传输实现 |

配置允许 HTTP/3，只表示客户端可以选择它。服务端能力、Alt-Svc（服务器声明同一资源可由另一地址或协议提供的响应首部）、代理、UDP 可达性、证书和客户端状态都会影响本次请求的最终协议。线上数据必须记录实际协商结果，不能用客户端库名称代替。

### HTTP/2 多路复用与服务端推送

#### 多路复用减少连接，不消除排队

HTTP/2 保留 HTTP 方法、状态码和首部语义，将消息编码为二进制帧（frame），再把帧归入不同逻辑流。多个流可以在同一连接上交错传输，HPACK 则用动态表等机制压缩重复首部。Android 上的 HTTPS 请求通常通过 ALPN（Application-Layer Protocol Negotiation，TLS 握手中的应用层协议协商）选择 `h2`。

| 维度 | HTTP/1.1 | HTTP/2 |
| --- | --- | --- |
| 并发请求 | 通常需要多条连接 | 一条连接可以承载多个逻辑流 |
| 首部编码 | 每次发送文本首部 | HPACK 可复用首部表并压缩 |
| 应用层队头等待 | 一条连接同一时刻通常处理一次请求—响应交换 | 不同逻辑流可并发推进 |
| 传输层队头等待 | TCP 丢包阻塞连接后续字节 | 仍运行在 TCP 上，因此影响同一连接的所有逻辑流 |
| 流量控制 | 主要依靠 TCP 与应用读取 | 同时存在连接级和逻辑流级 HTTP/2 流量控制 |

HTTP/2 的并发数还受服务端 `SETTINGS_MAX_CONCURRENT_STREAMS`（一条连接允许同时活跃的逻辑流上限）、客户端 `Dispatcher`、连接与逻辑流的流量窗口、服务端容量和设备资源限制。它不会保证所有请求都共用一条连接，也不对业务请求承诺优先级。

OkHttp 5.4.0 还把单个 HTTP/2 响应的首部总量限制为 256 KiB（262,144 字节）；超大首部不能依赖客户端无限接收。

大响应体会争用同一连接的带宽和拥塞窗口。消费方长时间不读取响应体，还会产生逻辑流级背压，也就是接收方处理不及时后逐步限制发送方，并可能影响连接级流量窗口。大文件与短 API 是否使用同一客户端或 `Dispatcher`，应根据排队以及 P95、P99 等尾部耗时决定；P95、P99 分别表示 95%、99% 的样本不超过该耗时。不能只凭“HTTP/2 支持多路复用”得出结论。

连接复用仍取决于 OkHttp 的 `Address`（连接地址配置）、`Route`（具体连接路径）、证书和连接健康状态。把资源分散到多个域名的“域名分片”可能增加 DNS、TCP 与 TLS 成本，也可能阻止符合条件的 HTTP/2 连接合并。资格检查见 [24.5 移动网络架构、连接与容灾](05-mobile-network-connection-resilience.md)。

#### 服务器推送（Server Push）是协议能力，不是 OkHttp 应用能力

RFC 9113 定义了 `PUSH_PROMISE`（服务器在客户端请求前声明将主动发送某项资源的帧），但客户端可以限制或拒绝推送。OkHttp 5.4.0 的 `Http2Connection.Builder` 仍默认使用内部 `PushObserver.CANCEL`；该观察器收到推送事件后请求取消，`OkHttpClient.Builder` 也没有面向应用开放的 `PushObserver` 配置。

因此，使用 OkHttp 的 Android 应用不应把 HTTP/2 服务器推送写进可执行的性能方案。更容易观测和控制的替代方式包括：

- 首屏聚合接口，减少明确存在的依赖链。
- 客户端在用户意图足够明确时发起可取消的预取。
- 使用标准 HTTP 缓存，让重复资源按新鲜度复用。
- 服务端返回资源清单，由客户端按当前界面、网络费用和本地缓存决定是否获取。

即使换用支持推送的客户端，也要测量推送资源被使用、已缓存、重复传输和取消的比例。协议存在该能力，不代表它对移动 API 有净收益。

### HTTP/3 与 QUIC 的收益边界

#### 传输层发生了什么变化

HTTP/3 把 HTTP 消息映射到 QUIC 逻辑流，并用 QPACK 压缩首部。QUIC 在 UDP 之上实现可靠传输、拥塞控制、TLS 1.3、逻辑流复用和连接 ID（不依赖 IP 地址与端口的连接标识）。它主要改变以下行为：

- 一条逻辑流丢失的数据需要重传时，其他不依赖该数据的流可以继续交付。HTTP/2 运行在单个 TCP 有序字节流上，丢失字节会阻塞后续字节。
- TLS 与 QUIC 握手集成，已建立状态满足条件时可使用恢复；0-RTT 仍是可选能力。
- 连接用连接 ID 标识，IP 地址或端口变化后可以验证新路径是否可用，再迁移连接。

这些机制仍有共享资源。QUIC 的拥塞控制通常作用于连接路径；丢包使拥塞窗口缩小时，多条逻辑流的吞吐都会受到影响。HTTP/3 也不会缩短 DNS、服务端处理或应用读取时间。

QUIC 的协议状态机位于 Cronet/Chromium 进程代码中。Android 通用内核（common kernel）负责 UDP 套接字、IP、路由、队列和设备驱动，不实现 HTTP/3 状态机。内核锚点为 `android17-6.18-2026-06_r6`；可从该标签的 [`net/ipv4/udp.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c) 继续追踪 UDP 收发。

#### 连接迁移不是切网成功保证

RFC 9000 定义了连接迁移和路径验证机制。Android 17 的 `ConnectionMigrationOptions` 源码也写明两项前提：连接必须是 QUIC，服务端必须支持迁移。客户端还要面对以下约束：

- 新网络需要可达同一服务端，并通过路径验证。
- NAT（网络地址转换）、企业代理、VPN、防火墙和服务端负载均衡配置可能阻止迁移。
- 迁移期间的请求可能超时或被取消，业务仍要有恢复策略。
- 允许使用非默认网络可能产生流量费用；`setAllowNonDefaultNetworkUsage()` 在 AOSP `android-17.0.0_r1` 中标注为实验 API。

`HttpEngine.Builder.setConnectionMigrationOptions()` 在同一源码锚点中也带有 `ConnectionMigrationOptions.Experimental` 注解。项目可以在受控实验中启用默认网络迁移；上线前要验证设备实现、服务端、代理、计费网络和远程关闭开关。

#### 0-RTT 只用于可重放操作

QUIC 的 0-RTT（零往返恢复）允许恢复的连接在握手完成前发送早期数据（early data），但这类数据缺少跨连接的防重放保证。攻击者可能重新发送捕获的数据，因此登录、支付、下单和产生一次性副作用的写请求不能仅凭“使用 HTTPS”就进入 0-RTT。

`HttpEngine.Builder.addQuicHint()` 用主机与备用端口提示服务器支持 QUIC。官方文档还说明，跨引擎会话利用 0-RTT 需要启用磁盘缓存。即使配置满足，服务端也可以拒绝早期数据，客户端必须允许按正常握手继续。指标应区分最终协议和业务总耗时，不应把“启用 QUIC”直接记成“命中 0-RTT”。

#### UDP、代理和发现机制决定可用性

HTTP/3 依赖 UDP。部分企业网络、代理、VPN 或热点会阻断或限制 QUIC，客户端需要保留基于 TCP 的 HTTP/2 或 HTTP/1.1。RFC 9114 允许在 QUIC 连接出现问题时改用基于 TCP 的 HTTP。

服务端还要通过客户端支持的方式声明 HTTP/3 能力，例如发送 Alt-Svc，或者由应用提供可信的 QUIC 能力提示（hint）。调用 `setEnableQuic(true)` 只允许引擎选择 QUIC，不会让缺少服务端配置的域名自动使用 HTTP/3。

Android 17 / API 37（同时属于 S Extensions 22）为 `HttpEngine.Builder` 增加 `setProxyOptions()`。应用代理配置会覆盖系统代理配置；若企业环境依赖系统代理，错误的应用代理或代理列表缺少末尾的 `null` 回退，可能导致网络完全不可达。分批启用协议的实验还必须包含企业代理和 VPN 场景。

### Android 17 上选择 OkHttp、HttpEngine 或 Cronet

#### OkHttp 5.4.0

OkHttp 适合已有 Retrofit、拦截器、Cookie、缓存和 `EventListener` 体系的 HTTP/1.1、HTTP/2 API。它能通过 `Response.protocol` 报告最终协议，也能用 `EventListener` 记录 DNS、连接、TLS 和交换阶段。OkHttp 5.4.0 没有稳定的公开 HTTP/3 配置入口。

若项目希望保留 OkHttp API 并使用 Cronet 传输实现，Android 官方集成文档列出了 `Cronet Transport for OkHttp`。接入时仍要核对该传输库的版本、支持的 OkHttp API、拦截器语义、缓存、证书、代理和事件指标；更换依赖不会自动保留全部行为。

#### HttpEngine

`HttpEngine` 从 API 34 起提供，也标注为 S Extensions 7。AOSP `android-17.0.0_r1` 的 `HttpEngine.Builder` 直接使用 `NativeCronetEngineBuilderImpl`。默认配置如下：

- 启用 HTTP/2。
- 启用 QUIC。
- 关闭 HTTP 缓存。

默认启用表示引擎可以选择相应协议，最终请求仍可能使用 HTTP/1.1 或 HTTP/2。若需要 HTTP 缓存，必须显式配置缓存模式与容量；磁盘缓存还要配置独占的存储目录。同一目录不能同时被多个 `HttpEngine` 使用。

`HttpEngine` 应作为长生命周期对象复用，并在不再使用时调用 `shutdown()`。按请求创建引擎会失去连接、QUIC 状态、线程和缓存复用，也可能违反存储目录的单实例约束。

#### Cronet 库

Cronet 是供 Android 应用使用的 Chromium 网络栈。当前 Android 官方概览确认其原生支持 HTTP/1.1、HTTP/2 与基于 QUIC 的 HTTP/3，但没有承诺每种集成方式都提供相同能力。项目必须从实际依赖与运行时实现确认提供方、版本、原生库加载结果和协议支持。

Android 10—13 若要使用 HTTP/3，通常需要外部 Cronet；Android 14 及以上可评估平台 `HttpEngine`。选择哪条路径还取决于安装包体积、设备覆盖、更新渠道、现有网络层适配，以及诊断与指标能力。

#### 基础 API 37 能观测什么

`UrlResponseInfo` 在基础 API 37 提供最终协商协议、缓存使用情况和接收字节下界。字节下界表示至少接收了这么多网络字节，但统计可以忽略部分协议开销。下面的代码用于在请求的终止回调中生成一条结果记录。

```kotlin
data class HttpEngineResult(
    val negotiatedProtocol: String?,
    val cacheUsed: Boolean,
    val receivedByteCountLowerBound: Long,
)

fun UrlResponseInfo.toTerminalResult(): HttpEngineResult {
    return HttpEngineResult(
        negotiatedProtocol = negotiatedProtocol.ifEmpty { null },
        cacheUsed = wasCached(),
        receivedByteCountLowerBound = receivedByteCount,
    )
}
```

应在终止回调中读取最终字节数；`onFailed()` 和 `onCanceled()` 还要先确认 `UrlResponseInfo` 非空。`wasCached()` 返回 `true` 时也可能包含经过网络重新验证的响应，不能把它一律解释成零网络流量。

`getReceivedByteCount()` 是处理请求所需网络字节的最小计数，包含所有重定向的首部与数据，并在解压前统计；它可以忽略 IP、TCP/UDP、TLS 和代理开销。空协议字符串表示未协商、未知或普通 HTTP/HTTPS，不能自行改写成 HTTP/1.1。

`FinishedRequestTimings` 和 `UrlRequest.getFinishedRequestTimings()` 是 37.1 / S Extensions 23 新增能力，只能在成功、失败或取消的终止回调到达后读取，不属于 API 37 / `android-17.0.0_r1` 锚点。由此不能认为基础 API 37 可以直接获得 DNS、连接和 TLS/QUIC 的完整公开时序。

### gRPC 在移动端的实践

#### gRPC 是调用契约，不是通用 HTTP 替代品

gRPC 用 `.proto` 接口定义文件描述服务与消息，Android 通常使用 protobuf lite（精简版 Protocol Buffers 运行库）生成客户端类型。它提供四种方法形态：

| 方法形态 | 请求与响应 | 适合的业务 |
| --- | --- | --- |
| 一元调用 | 单请求、单响应 | 有明确边界的查询与写入 |
| 服务端流 | 单请求、响应流 | 服务端持续发送一组结果或更新 |
| 客户端流 | 请求流、单响应 | 分段上传或批量聚合 |
| 双向流 | 双向流 | 双方独立持续发送消息的会话 |

这四种形态的差别在于哪一侧可以持续发送消息；采用流式调用后，还要另行设计流量控制和断线恢复。生成代码能提供字段类型与方法签名，但协议演进仍要遵守 Protocol Buffers 兼容规则。字段号不能复用，删除字段应保留编号，客户端与服务端要支持新旧版本交错发布。序列化边界见 [24.2 数据库与序列化性能](02-database-serialization-performance.md)。

标准 gRPC 在 HTTP/2 上承载键值元数据（metadata）、带长度前缀的消息和响应体结束后发送的尾部字段（trailers）。HTTP 状态码不足以表示 RPC 结果；监控必须记录 gRPC 状态码、服务名、方法名、调用截止时间、取消、消息字节和每次尝试，不能只记录 HTTP 200。

#### `Channel` 是逻辑通信通道

gRPC `Channel` 表示到一个逻辑目标的通信通道，可以在内部持有零条、一条或多条实际连接，并参与名称解析与客户端负载均衡。它不等同于一条套接字连接。

官方性能建议要求尽量复用 `Channel` 和生成的客户端代理（stub）。复用边界应按逻辑目标（target）、TLS、代理、名称解析和服务配置决定。用户令牌更适合通过每次调用的调用凭据（credentials）或元数据提供；仅因账号切换就重建 `Channel`，会丢失可安全共享的传输资源。认证实现必须避免把旧令牌固化在长生命周期拦截器中。

#### 调用截止时间、取消和 Wait-for-Ready

gRPC 默认不设置调用截止时间（deadline），客户端因此可能一直等待。每个方法需要根据用户交互期限、网络耗时分布和服务端处理预算显式设置截止时间。上游取消、页面销毁和后台任务停止也应传播到 RPC。

`wait-for-ready`（等待通道就绪）会在 `Channel` 暂时不可用时把调用留在队列中，待连接恢复后再发送；默认模式会更早返回失败。调用截止时间仍然生效，因此它只适合允许短暂等待连接恢复的调用，不能绕过用户取消或无限延长启动等待。

流式 RPC 还要定义断线恢复语义。连接中断时，未完成的逻辑流会失败；重新建流不能自动恢复业务位置。消息序号、游标、确认、去重和补发属于应用协议。

流式 RPC 还受 gRPC 与 HTTP/2 流量控制约束。一次写入只表示消息交给 gRPC，不代表字节已经发到网络；发送方速度长期高于接收方时，框架会等待或缓存。应用队列必须有界，手动流量控制还要保证两端持续读取，避免双方都等待写入空间。

#### 重试由服务配置（Service Config）和业务语义共同决定

gRPC 支持透明重试：即使没有显式重试策略，也可能恢复少量底层故障，前提是确认调用没有进入服务端应用逻辑。这类故障来自并发事件先后顺序不确定。更广泛的重试通过 Service Config（服务配置）按方法设置尝试次数上限、逐次延长的等待间隔、可重试状态码和重试总量限制。

状态码 `UNAVAILABLE` 并不自动表示业务操作可重复。客户端与服务端仍要确认方法语义：

- 查询或幂等操作可以在总截止时间内受控重试。
- 写操作需要幂等键、版本条件或查询确认，不能只按 gRPC 状态码重发。
- 一旦收到响应首部，gRPC 重试机制会把 RPC 视为已提交，不再按同一策略重试。
- 应同时记录逻辑 RPC 与每次尝试，避免把内部重试时间全部归为一次服务端延迟。

#### 保活探测（Keepalive）和长流会消耗移动网络资源

gRPC 保活探测使用 HTTP/2 `PING` 检查空闲连接。客户端需要与服务端约定频率，以及没有活动 RPC 时是否允许发送；当前官方指南建议客户端不要把间隔设得远低于一分钟，也建议避免在没有调用时启用保活。服务端可发送 `GOAWAY`（通知客户端停止在该连接上创建新流）和 `too_many_pings` 调试信息，拒绝过密探测。

移动端还要考虑蜂窝无线电唤醒、Doze（Android 设备空闲省电模式）、应用进程回收和后台执行限制。低频通知通常更适合系统共享推送通道。长流适用于前台持续交互或业务确有连续传输需求的场景，并应具备取消、恢复与断点状态。

长生命周期逻辑流启动后通常不能重新参与客户端负载均衡。服务端滚动发布、连接年龄和节点故障都会中断它，因此固定保持一条永久逻辑流不能保证高可用。

### 协议选型与兼容策略

#### 从请求形态与系统约束选择

| 请求形态 | 候选方案 | 需要验证的边界 |
| --- | --- | --- |
| 常规 REST / JSON，同一主机与端口组合（authority）下短请求较多 | OkHttp + HTTP/2 | 网关与 CDN 的 ALPN、连接复用、服务端逻辑流上限 |
| 媒体、长下载、切网与丢包敏感流量 | HttpEngine / Cronet，评估 HTTP/3 | UDP、代理、VPN、服务端 QUIC、迁移和缓存 |
| 自有客户端与服务端之间的强类型 RPC | 基于 HTTP/2 的 gRPC | Protocol Buffers 演进、网关、状态码与尾部字段、截止时间、重试 |
| 长生命周期双向消息 | gRPC 双向流或已有消息协议 | 后台限制、流量控制、断线恢复、负载均衡 |
| 浏览器和第三方共同使用的公开接口 | REST / JSON，必要时另建 gRPC-Web 网关 | 调试、兼容、缓存和跨语言契约 |
| 可延迟后台上报 | 批量 REST 或批量 RPC | WorkManager 约束、幂等、与交互流量隔离 |

这张表只给出候选方向，不能代替设备与服务端实验。协议选择还要计算安装包体积、适配成本、发布渠道和排障工具。一个小型低频接口即使能使用 gRPC 或 HTTP/3，也可能无法抵消新增依赖与运维成本。

#### 回退要分协议与业务两层

HTTP/3 到 HTTP/2、HTTP/2 到 HTTP/1.1 属于同一 HTTP 语义下的传输协商。成熟客户端可以根据服务端和网络条件完成。应用仍要记录最终协议和错误，但不必为每次 QUIC 失败手写另一遍请求。

gRPC 到 REST 属于两套接口契约，不是协议自动回退。只有业务明确维护双路径时才可使用，而且两条路径必须共享：

- 权限与鉴权规则。
- 幂等键、版本条件和重复提交处理。
- 字段含义、默认值和错误映射。
- 分批发布、审计与数据一致性规则。

双路径会增加测试与服务端维护成本。多数业务更适合在当前 RPC 上恢复或显示错误，而不是看到任意 gRPC 失败就改发 REST。

#### 更换传输实现时保持业务契约不变

从 OkHttp 迁移到 HttpEngine/Cronet，或为 OkHttp 接入 Cronet 传输实现时，应逐项核对：

- `Authorization`、Cookie、跨服务关联一次调用的追踪标识（trace ID）、实验首部和 `User-Agent`。
- Network Security Config（Android 网络安全配置）、证书或公钥固定、用户安装的 CA（证书颁发机构）证书、系统代理、应用代理和 VPN。
- HTTP 缓存、业务缓存、Cookie 存储和磁盘目录。
- 重定向、上传重放、取消、超时和后台生命周期。
- 压缩、字节统计、错误分类和敏感字段脱敏。

协议实验期间保持接口语义、服务端业务逻辑和缓存策略稳定。多项改动同时发布会破坏归因。

### 协议实验与观测

#### 各客户端公开指标不同

| 客户端 | 基础可观测信息 | 限制 |
| --- | --- | --- |
| OkHttp 5.4.0 | `Response.protocol`、`EventListener` 阶段、连接事件 | HTTP/2 逻辑流并发与底层 TCP 指标不是完整公开 API |
| 基础 API 37 HttpEngine | `getNegotiatedProtocol()`、`wasCached()`、接收字节下界、回调时刻与异常 | 没有 37.1 的 `FinishedRequestTimings` |
| Cronet 库 | 实现提供方给出的请求完成信息、NetLog（Chromium 网络诊断日志）与回调 | 能力随 Cronet 版本和集成方式变化 |
| gRPC | 方法、状态码、截止时间、元数据、逻辑调用和每次尝试 | 还需与所用传输实现的连接指标关联 |

最终协商为 HTTP/2，不能证明客户端尝试过 HTTP/3。只有底层日志或可靠的连接尝试指标能区分“未发现 HTTP/3”“UDP 不通”“QUIC 握手失败”和“策略未启用”。缺少证据时，应把数据标记为最终协议，不能命名为 HTTP/3 回退。

#### 实验单位与分层

协议实验应稳定地按用户或设备分组，并限制到明确的主机与接口。分析时至少按以下维度分层：

- 最终协议、客户端实现与实现提供方版本。
- 默认网络变化序号、传输类型、计费属性、VPN 和代理。
- 请求与响应大小、缓存状态、冷连接或复用连接。
- DNS、连接、握手、TTFB（Time to First Byte，从请求发出到收到响应首部的等待）、响应体与逻辑调用总时长；只使用当前客户端实际公开的阶段。
- HTTP 或 gRPC 错误、取消、重试尝试与最终成功率。
- 前台交互、后台任务、媒体传输和切网场景。

比较中位数和高分位延迟，同时观察错误率、取消率、字节量与电量。连接状态、CDN 节点、服务端版本和缓存命中未分层时，平均值变化无法归因到协议。

分批实验开关应支持按主机、接口、网络类型、客户端版本和应用版本关闭。关闭实验并恢复原传输实现时，只改变传输选择，不能丢失正在执行写操作的幂等状态。

### 工程检查清单

- 是否记录请求最终协商的协议，而不是只记录客户端库名称。
- HTTP/2 连接复用是否被无意义的多客户端或域名分片削弱。
- 是否把服务端逻辑流上限、流量控制和 TCP 队头等待纳入分析。
- OkHttp 方案是否已移除不可用的 HTTP/2 服务器推送假设。
- HTTP/3 是否保留基于 TCP 的协议协商路径。
- QUIC 迁移是否覆盖 Wi-Fi/蜂窝切换、VPN、代理、计费网络和服务端不支持场景。
- 0-RTT 是否只允许可重放操作，指标是否避免把 QUIC 等同于 0-RTT。
- HttpEngine 是否复用，缓存与磁盘目录是否显式配置。
- Android 17 应用代理是否验证系统代理覆盖与最终回退。
- 基础 API 37 指标是否避免引用 37.1 才提供的详细时序。
- gRPC `Channel` 与客户端代理（stub）是否复用，用户令牌是否按调用安全更新。
- 每个 gRPC 方法是否有合理的调用截止时间，取消是否传播。
- gRPC 重试是否由 Service Config 与业务幂等语义共同限制。
- 流式 RPC 是否具备流量控制、断线恢复、前后台和电量策略。
- 分批协议实验是否保持服务端业务、缓存和接口语义稳定。

### 协议与 RPC 小结

HTTP/2、HTTP/3 和 gRPC 分别改变连接复用、传输恢复和调用契约，不能只凭协议名称判断收益。选型要固定客户端实现、最终协商协议、缓存与连接状态，并同时验证流量控制、截止时间、幂等重试、切网和后台生命周期。

### 源码与规范依据

#### 当前平台与客户端依据

- [AOSP `android-17.0.0_r1` HttpEngine](https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/HttpEngine.java)
- [AOSP `android-17.0.0_r1` ConnectionMigrationOptions](https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/ConnectionMigrationOptions.java)
- [AOSP `android-17.0.0_r1` UrlResponseInfo](https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/UrlResponseInfo.java)
- [Android common kernel `android17-6.18-2026-06_r6` UDP](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c)
- [Android HttpEngine.Builder API](https://developer.android.com/reference/android/net/http/HttpEngine.Builder)
- [Android ConnectionMigrationOptions API](https://developer.android.com/reference/android/net/http/ConnectionMigrationOptions)
- [Android UrlResponseInfo API](https://developer.android.com/reference/android/net/http/UrlResponseInfo)
- [Android FinishedRequestTimings API](https://developer.android.com/reference/android/net/http/FinishedRequestTimings)
- [Android UrlRequest API](https://developer.android.com/reference/android/net/http/UrlRequest)
- [Android Cronet 功能](https://developer.android.com/develop/connectivity/cronet)
- [Android Cronet 与其他库集成](https://developer.android.com/develop/connectivity/cronet/integration)
- [OkHttp 变更记录](https://github.com/lysine-dev/okhttp/blob/main/CHANGELOG.md)
- [OkHttp 5.4.0 Http2Connection](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt)
- [OkHttp 5.4.0 PushObserver](https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt)

#### 保留的旧版本源码锚点

- [OkHttp 5.3.0 Http2Connection](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt)
- [OkHttp 5.3.0 PushObserver](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt)

#### 协议与 gRPC 依据

- [RFC 9113：HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html)
- [RFC 9000：QUIC](https://www.rfc-editor.org/rfc/rfc9000.html)
- [RFC 9001：Using TLS to Secure QUIC](https://www.rfc-editor.org/rfc/rfc9001.html)
- [RFC 9114：HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html)
- [gRPC Android Java 指南](https://grpc.io/docs/platforms/android/java/basics/)
- [gRPC Deadline](https://grpc.io/docs/guides/deadlines/)
- [gRPC Wait-for-Ready](https://grpc.io/docs/guides/wait-for-ready/)
- [gRPC Retry](https://grpc.io/docs/guides/retry/)
- [gRPC Flow Control](https://grpc.io/docs/guides/flow-control/)
- [gRPC Keepalive](https://grpc.io/docs/guides/keepalive/)
- [gRPC 性能建议](https://grpc.io/docs/guides/performance/)

## ECH、DNS HTTPS 记录与回退

传输协议确定后，ECH 作用于 TLS ClientHello 隐私。客户端支持、DNS 结果和服务端配置必须同时满足，失败路径要保留可控回退。

### 适配范围

Android 17 / API 37 为网络库提供了加密客户端问候（Encrypted Client Hello，ECH）所需的域名解析（DNS）、传输层安全协议（TLS）和按域名策略接口。ECH 会加密 TLS 初始握手中的敏感字段，主要是服务器名称指示（Server Name Indication，SNI）。

`domainEncryption` 是 Android 网络安全配置中的 XML 元素。应用把目标系统版本 `targetSdkVersion` 设为 37 时，它的默认模式从 `disabled` 变为 `enabled`。这个默认值只表达应用策略。网络库仍须读取策略、从 DNS 的 HTTPS 资源记录取得 ECH 配置，并在 TLS 握手中应用；使用平台 TLS 提供方（provider，Java 安全框架中的 TLS 实现组件）的网络库可以调用 Android 17 新增接口，自带 TLS 实现的网络库则要完成等价处理。服务端也要支持互联网标准 RFC 9849。

DNS 的 HTTPS 资源记录描述服务连接参数，与以 `https://` 开头的网页地址无关。HTTPS 最终能连通只说明连接路径可用；验收还要确认：

- 当前网络库版本是否已经接入 Android 17 ECH API。
- 设备使用的解析路径能否取得 HTTPS 资源记录中的 `ech` 参数。
- 服务端 ECH 配置、用于外层握手路由的公开名称、证书与轮换流程是否一致。
- 没有 ECH 配置、配置失配、代理拦截和证书透明度（CT）失败时分别发生什么。
- 连接复用、DNS 等待和协议切换是否改变业务耗时。

平台源码以 Android 开源项目（AOSP）的 `android-17.0.0_r1` 标签为基准。ECH 的 Android 实现位于用户空间的 DNS 与 TLS 组件，没有供应用调用的内核接口。TLS 1.3、证书链、连接池和 HTTP/2、HTTP/3 原理见 12.1、24.5 与 24.6。

### ECH 的 Android 17 适配边界

ClientHello 是客户端发出的第一条 TLS 握手消息，其中包含支持的算法和 SNI 等信息。ECH 把它拆成外层 `ClientHelloOuter` 和加密的 `ClientHelloInner`：真实 SNI 等敏感扩展位于内层，外层保留供服务端路由的公开名称。RFC 9849 还定义了配置失配后的重试信息和 ECH GREASE。GREASE 是内容随机的兼容性测试扩展，用来检查网络中间设备能否容忍 ECH 格式；它本身不会加密真实 SNI。

ECH 保护范围有限：

- 目标 IP 地址仍对网络路径可见。
- 公开名称仍会出现在外层 ClientHello。
- 使用明文 DNS 时，查询名称仍可能泄露；ECH 不替代加密 DNS。
- 流量大小、时序与连接目的地仍可用于流量分析。
- 客户端、服务端、代理与业务日志仍能看到各自处理的数据。

ECH 不会让域名对所有观察者不可见。网络库和服务端完成协商后，它只加密 ClientHello 内的真实 SNI 等字段，降低网络中间设备直接读取这些字段的能力。[RFC 9849](https://www.rfc-editor.org/rfc/rfc9849) 给出 ECH 协议细节，[RFC 9460](https://www.rfc-editor.org/rfc/rfc9460) 定义 HTTPS 与服务绑定（SVCB）资源记录。

采用 Android 17 平台 API 接入 ECH 的网络库，可按以下顺序处理：

1. 网络库通过 `NetworkSecurityPolicy.getDomainEncryptionMode(hostname)` 读取应用对目标域名的策略。
2. 网络库通过 `DnsResolver` 并发查询 IPv4 地址记录（A）、IPv6 地址记录（AAAA）和 HTTPS 记录，得到描述候选连接端点的 `HttpsEndpoint`。
3. `HttpsRecord.getEchConfigList()` 从服务模式（ServiceMode）的 HTTPS 记录中解析可选的 ECH 配置列表 `EchConfigList`。
4. 网络库在握手开始前调用 `SSLSockets.setEchConfigList()` 或 `SSLEngines.setEchConfigList()`。
5. 平台 TLS 实现发送 ECH ClientHello；服务端接受配置，或返回配置失配及可选的重试配置。

`domainEncryption` 只提供按域名策略，不会自动改造网络库。网络库还要完成 DNS 查询、握手配置和失配处理，Android 官方文档也把网络库已接入 ECH 列为生效前提。

### 在网络安全配置中声明 `domainEncryption`

网络安全配置（Network Security Configuration）是应用资源中的 XML 文件。`domainEncryption` 可放在 `base-config` 或 `domain-config` 下：`base-config` 是未被域名规则覆盖时使用的默认配置，`domain-config` 只匹配指定域名。多个规则同时匹配时，平台使用域名最长、范围最具体的一条；`includeSubdomains="true"` 会让规则覆盖该域名及各级子域。

这份 XML 明确声明全局启用，并为一个已知不兼容的网关域名禁用 ECH：

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config>
        <domainEncryption mode="enabled" />
    </base-config>

    <domain-config>
        <domain includeSubdomains="true">legacy-gateway.example.com</domain>
        <domainEncryption mode="disabled" />
    </domain-config>
</network-security-config>
```

这段配置要求支持该策略的网络库对普通域名使用 `enabled`；访问 `legacy-gateway.example.com` 及其子域时，不发送 ECH，也不发送 ECH GREASE。对 `targetSdkVersion 37` 的应用，平台默认已经是 `enabled`，显式写入 `base-config` 可以记录应用策略。

Android 17 正式版的 XML 语法只接受两个值：

| XML 模式 | 语义 |
| --- | --- |
| `enabled` | 握手获得 ECH 配置时使用 ECH；没有配置时启用 ECH GREASE |
| `disabled` | 不使用 ECH，也不使用 ECH GREASE |

`NetworkSecurityPolicy` 的公开常量还包含 `DOMAIN_ENCRYPTION_MODE_OPPORTUNISTIC` 与 `DOMAIN_ENCRYPTION_MODE_UNKNOWN`。`OPPORTUNISTIC` 表示有服务端配置时尝试 ECH、没有配置时不发送 GREASE；`UNKNOWN` 要求网络库退回普通 TLS。它们是网络库读取策略时可能遇到的 API 值，不是当前 XML 语法允许填写的字符串。网络安全配置中不能写 `mode="opportunistic"`。

这段诊断函数用于确认某个主机名经过 Network Security Configuration 匹配后得到的策略值：

```kotlin
@RequiresApi(37)
fun domainEncryptionMode(hostname: String): String {
    val mode = NetworkSecurityPolicy.getInstance()
        .getDomainEncryptionMode(hostname)

    return when (mode) {
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_DISABLED -> "disabled"
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_OPPORTUNISTIC -> "opportunistic"
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_ENABLED -> "enabled"
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_UNKNOWN -> "unknown"
        else -> "unrecognized:$mode"
    }
}
```

返回值只能证明平台解析出的策略，不能证明 DNS 返回了 ECH 配置，也不能证明某次 TLS 握手使用了 ECH。诊断日志不应记录完整 URL、查询参数或用户标识。

模式与默认值以 [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config#domain-encryption) 为准，API 常量见 [`NetworkSecurityPolicy`](https://developer.android.com/reference/android/security/NetworkSecurityPolicy)。

### Android 17 API 与源码边界

`DnsResolver` 在 API 37 增加了返回 `HttpsEndpoint` 的查询重载。它会并发发出 A、AAAA 和 HTTPS 查询，并允许调用方通过 `httpsTimeoutMillis` 指定地址记录完成后还要等待 HTTPS 记录多久。`DnsResolver.getInstance()` 在 API 37 已废弃，新代码应使用接收 `Context` 与 `Looper` 的构造函数。

`HttpsRecord` 表示 RFC 9460 的 HTTPS 记录。`priority == 0` 表示别名模式（AliasMode），只把查询指向另一个名称，不携带 IP 提示、端口、ALPN 或 ECH 配置。其他优先级表示服务模式（ServiceMode），可携带连接参数；ALPN 是应用层协议协商，用于声明 HTTP/1.1、HTTP/2 等可选上层协议。`getEchConfigList()` 可能返回 `null`，ECH 配置二进制格式无效时会抛出 `InvalidEchDataException`。

`SSLSocket` 封装基于套接字（socket）的 TLS 连接，`SSLEngine` 则提供不直接绑定套接字的 TLS 状态机。`SSLSockets.setEchConfigList()` 和 `SSLEngines.setEchConfigList()` 必须在握手开始前调用，而且只接受平台 TLS 实现创建的对应对象。自带 BoringSSL、OpenSSL 等 TLS 库，或自带 QUIC 实现的 SDK，不会因为应用增加了 XML 就自动执行这些 API；QUIC 是 HTTP/3 使用的基于 UDP 的传输协议。

在 `android-17.0.0_r1` 中可以直接核对这些实现：

- [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) 发起 A、AAAA 与 HTTPS 查询，并构建 `HttpsEndpoint`。
- [`HttpsRecord.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/dns/HttpsRecord.java) 解析 `EchConfigList`。
- [`DomainEncryptionMode.java`](https://android.googlesource.com/platform/external/conscrypt/+/refs/tags/android-17.0.0_r1/common/src/main/java/org/conscrypt/DomainEncryptionMode.java) 给出平台 TLS 实现 Conscrypt 内部使用的模式枚举。
- [`Platform.java`](https://android.googlesource.com/platform/external/conscrypt/+/refs/tags/android-17.0.0_r1/platform/src/main/java/org/conscrypt/Platform.java) 把 ECH 配置失配转换为 Android 公共异常。

应用通常不应重写这套解析与重试逻辑。自定义网络库如果必须接入，应完整处理 `HttpsEndpoint` 选择、平台 TLS 对象检查、握手前配置、取消、超时和配置失配。只把一段 ECH 字节交给套接字，不足以完成安全的协商与重试。

### 网络库支持状态要按版本核对

Android 17 [行为变更页面](https://developer.android.com/about/versions/17/behavior-changes-17#ech) 把 HttpEngine、WebView 与 OkHttp 列为网络库示例，同时明确规定 ECH 只在网络库已经集成支持时生效。文档出现库名称，不能证明应用当前安装或依赖的版本已经支持 ECH。

截至 2026-08-15，可验证的上游状态如下：

| 路径 | 可验证事实 | 适配判断 |
| --- | --- | --- |
| Android 平台 API | DNS、策略、TLS 与失配异常 API 已进入 API 37 | 提供接入能力，不替网络库完成接入 |
| OkHttp | `square/okhttp` 现重定向到上游仓库 `lysine-dev/okhttp`。主分支于 2026-07-24 合并初始 Android API 37 ECH 支持的 [PR #9573](https://github.com/square/okhttp/pull/9573)，并于 2026-07-26 合并按 `NetworkSecurityPolicy` 选择模式的 [PR #9596](https://github.com/square/okhttp/pull/9596)；最新 [`parent-5.4.0`](https://github.com/square/okhttp/tree/parent-5.4.0) 标签创建于 2026-06-08，早于两次合并 | 主分支已经有接入代码，`parent-5.4.0` 尚未包含；核对依赖版本或提交号 |
| Chromium / WebView / Cronet | 2026-06-22 的 [Chromium 提交](https://chromium.googlesource.com/chromium/src/net/+/b91f5ad12e2adc0166183b0172cd4cbc0a04a934) 加入按主机读取平台模式；2026-07-11 的 [后续提交](https://chromium.googlesource.com/chromium/src/net/+/40d5138e2f148890a937d6653284074cd3c3676d) 已在 TLS 与 QUIC 路径执行 ECH 模式 | 主分支已具备读取和执行逻辑；设备上的 WebView 或 Cronet 仍要确认其版本包含这两次提交 |
| 自定义 `SSLSocket` / `SSLEngine` | 公共 API 已可用 | 应由网络库维护完整 DNS、策略与重试流程 |
| 自带原生 TLS 的 SDK | 是否读取 Android XML 取决于 SDK | 要求供应方给出版本、源码或测试证据 |

主分支状态不能直接代表已发布制品或设备组件。上线记录应包含 Maven 依赖坐标与版本、WebView 实现版本、Android 构建号、TLS 实现、是否使用自定义 DNS，以及服务端 ECH 发布状态。Maven 坐标用于唯一标识依赖库，WebView 实现是设备上可独立更新的系统网页组件。仅记录库名无法还原实际能力。

HTTPDNS 是应用通过 HTTP 请求调用第三方 DNS 服务、不使用系统解析器的方案。它和只返回 IP 地址的自定义 `Dns` 接口都需要单独审查。ECH 配置位于 HTTPS 资源记录中；解析实现若只交付 A、AAAA 结果，网络库可能拿不到 `EchConfigList`。HTTPDNS 的适配边界见 24.7。

### 失败与回退判定

ECH 失败应按发生阶段分类。表中的缓存生存时间（time to live，TTL）表示 DNS 记录可以缓存多久。

| 现象 | 可能原因 | 核对动作 |
| --- | --- | --- |
| 连接成功，没有 ECH 配置 | HTTPS 记录缺失、AliasMode、记录没有 `ech` 参数、自定义 DNS 丢失记录 | 对比权威 DNS、设备解析结果和网络库日志 |
| 发送 GREASE 后连接成功 | `enabled` 下没有可用 ECH 配置 | 记为 GREASE，不能记为 ECH 成功 |
| `InvalidEchDataException` | HTTPS 记录里的 ECH 数据为空、长度错误或格式无效 | 修复 DNS 发布内容，检查缓存与 TTL |
| `EchConfigMismatchException` | 客户端缓存的配置与服务端当前配置不一致 | 验证公开名称与证书，再使用服务端给出的重试配置 |
| 普通 TLS 证书失败 | 证书链、主机名、证书透明度或代理证书问题 | 单独核对证书错误，禁用 ECH 不会修复证书 |
| HTTP/3 失败而 HTTP/2 成功 | UDP、QUIC、地址或协议协商问题 | 按本节前文的协议路径分析 |
| 私网地址、`.local` 或设备发现失败 | `ACCESS_LOCAL_NETWORK` 未获授权 | 按 24.9 的本地网络权限路径分析 |

ECH GREASE 用随机内容模拟 ECH 扩展，帮助发现会阻断未知扩展的网络中间设备。它没有可用的服务端 ECH 配置，不能加密真实 SNI。诊断事件至少要区分 ECH 被接受、GREASE、策略禁用、没有配置、配置失配与其他 TLS 错误。

配置失配后不能跳过校验直接重试。`EchConfigMismatchException` 要求客户端先取得 `getPublicHostname()`，用主机名验证器确认证书对该公开名称有效；公开名称为 `null` 时必须忽略重试配置。验证成功且 `getRetryConfigList()` 非空后，网络库才可以新建连接重试。公共 API 的约束见 [`EchConfigMismatchException`](https://developer.android.com/reference/android/net/ssl/EchConfigMismatchException)。

Android 17 对 `targetSdkVersion 37` 及以上的应用默认启用证书透明度（Certificate Transparency，CT）。证书颁发机构（CA）签发证书后，签名证书时间戳（SCT）可证明该证书已提交到 CT 日志。CT 与 ECH 都可能表现为 TLS 失败，但校验阶段不同。使用系统 CA 时应核对 SCT 与 CT 策略；使用用户 CA 或应用内嵌 CA 时，网络安全配置可能因信任锚不是系统 CA 而关闭 CT，除非域名规则显式启用。禁用 ECH 不会改变证书链或 CT 结果。

`domainEncryption` 位于 Android 安装包（APK）的资源 XML 中，普通远程配置不能修改它。把某个域名改成 `disabled` 通常需要发布新版本；网络库自带的策略开关属于另一套配置，必须确认它与平台策略的优先级。XML 域名覆盖规则不能充当远程即时修复开关。

### 性能观测方法

ECH 对耗时的影响可能来自 HTTPS DNS 查询等待、配置失配后的新连接、TLS 计算和连接复用变化。不同设备与网络的结果会变，不能用一个固定毫秒数概括。

| 阶段 | 建议记录 | 解释限制 |
| --- | --- | --- |
| DNS | A、AAAA、HTTPS 各阶段耗时；HTTPS 记录与 ECH 配置是否存在 | 权威 DNS 有记录不代表设备解析路径取得了记录 |
| TLS | 新连接握手耗时、ECH 接受、GREASE、失配、证书错误 | 通用 HTTP 事件监听器未必暴露 ECH 状态，需要网络库或服务端证据 |
| 重试 | 配置失配次数、是否收到重试配置、新连接次数 | 重试会增加高分位慢样本，不能只看首次握手的平均值 |
| 连接池 | 新建连接率、复用率、HTTP/2 流与 HTTP/3 会话 | 已复用连接不会重新执行完整握手 |
| 业务 | 首包、关键接口分位数、页面首屏、媒体首缓冲 | 同时记录网络类型、代理、VPN、地域与运营商 |

`DnsResolver` 的 `HTTPS_QUERY_WAIT_NONE` 会在地址查询完成后立即回调，即使 HTTPS 查询尚未返回；官方不建议把它用于安全或延迟敏感场景。`HTTPS_QUERY_WAIT_UNTIL_TIMEOUT` 会等待 HTTPS 查询完成或超时，在丢弃 HTTPS 查询的网络中可能增加延迟。网络库通常应从 `HTTPS_QUERY_WAIT_AUTO` 开始，并按实测调整，应用不应随意覆盖内部选择。

`dig` 是查询 DNS 记录的命令行工具。这条命令使用当前电脑配置的解析器，检查域名是否发布 HTTPS 记录：

```bash
dig HTTPS api.example.com +short
```

命令结果可以验证发布格式，却不能代表 Android 设备在蜂窝网络、专用 DNS、VPN 或 HTTPDNS 下获得同一答案。专用 DNS 是 Android 提供的系统级加密 DNS 设置，VPN 则可能接管解析路径。客户端解析日志、服务端 DNS 日志与 TLS 服务端的 ECH 接受状态需要一起核对。

抓包可以观察是否出现形似 ECH 的扩展、连接重试和协议选择，但无法仅凭扩展存在区分有效 ECH 与 GREASE，也不应尝试从 ECH 中恢复内层 SNI。业务性能数据仍要来自网络库事件、应用性能追踪数据（trace）与服务端日志。

### 分阶段发布策略

分阶段发布前先核对这些条件，XML 已配置只是其中一项：

- 固定网络库、WebView 实现、TLS 实现和 Android 17 构建版本。
- 确认库版本包含策略读取、HTTPS DNS 查询、握手配置与失配重试。
- 为候选域名发布 HTTPS 记录，记录 TTL、内容分发网络（CDN）节点、公开名称和证书覆盖。
- 让服务端提供 ECH 接受、拒绝与配置轮换日志。
- 选择低风险域名测试，再处理登录、支付、消息与配置获取等关键接口。
- 分开观察普通网络、企业代理、VPN、校园网、蜂窝网络和不同地域。

`targetSdkVersion 36` 与 37 的对照会同时包含 CT 等其他行为变化，不能把差异单独归因到 ECH。实验室可在相同网络库和代码下构建两份网络安全配置：一份保持 `enabled`，另一份对候选域名设为 `disabled`。这样只改变 ECH 策略，便于归因；生产发布还要考虑应用版本更新需要的时间。

回退手段有三类：

- 服务端修正或轮换 ECH 配置，并在失配响应中提供有效重试配置。
- DNS 撤下或修正 `ech` 参数；客户端缓存会按 TTL 延迟生效。
- 发布应用更新，将确认不兼容的域名设为 `disabled`。

降低 `targetSdkVersion` 会同时改变其他 Android 17 安全行为，也可能不符合应用商店要求，不应作为 ECH 的常规回退方案。远程开关只有在网络库明确支持，并定义了它与平台策略的优先级时才能使用。

隐私日志保留域名分类、错误类型、网络库版本、粗粒度网络环境和协议即可。不要记录完整 URL、令牌、用户输入、证书私钥材料或 ECH 配置原始字节。

### 与 12.1 TLS 性能章节的边界

12.1 解释 TLS 1.3、证书、CT、SNI、混合公钥加密（HPKE）、会话恢复和安全连接成本。ECH 使用 HPKE 加密 ClientHello 内层。本节的范围是 Android 17 的按域名策略、配置获取和接入验证。握手耗时、证书链和 0-RTT 等问题仍按 12.1 的方法分析；0-RTT 指恢复会话时在完整握手结束前发送早期数据。

### 与 24.9 本地网络权限适配的关系

24.9 处理 Android 17 `ACCESS_LOCAL_NETWORK`、局域网设备发现、Google Cast 投屏、物联网（IoT）设备与本地 HTTP 服务。ECH 与网络安全配置适用于公网 HTTPS 连接，两类问题的失败阶段不同。

公网域名的 TLS 握手失败应检查 DNS HTTPS 记录、ECH、CT、证书与协议回退。RFC 1918 私有 IPv4 地址、仅在当前网段有效的地址、`.local`、组播 DNS（mDNS）、简单服务发现协议（SSDP）和本地 HTTP 服务失败时，应先检查本地网络权限。工单中记录目标地址类别和失败阶段，可以避免把权限拒绝误报为 TLS 问题。

### ECH 小结

Android 17 提供了 ECH 所需的平台接口，并为 `targetSdkVersion 37` 的应用把 `domainEncryption` 默认设为 `enabled`。生效仍取决于网络库接入和服务端支持。正式 XML 只接受 `enabled` 与 `disabled`；公开 API 中的 `opportunistic` 常量不能直接写入 XML。

验收时要沿着策略、HTTPS DNS、TLS 配置、服务端协商和重试逐段取证。没有 ECH 配置时发送的是 GREASE，不能计为 ECH 成功；配置失配时必须验证公开名称后再使用重试配置。CT、HTTP/3 和本地网络权限各有独立触发条件，不能因它们都表现为连接失败就归入 ECH。

## 全文小结

协议优化先决定请求与流的语义，再选择能够稳定提供相应能力的客户端、服务端和网络路径。HTTP/2 多路复用、HTTP/3/QUIC、gRPC 流与 ECH 都需要以实际协商、错误阶段和业务完成结果验收，配置存在不等于能力生效。

ECH 位于 DNS HTTPS 记录、网络安全策略和 TLS 握手的交界处，不能替代加密 DNS、证书验证或业务容灾。协议升级与 ECH 发布都应按主机和场景分批，保留 TCP/普通 TLS 的安全回退，并避免把多项网络栈变化放进同一次实验。
