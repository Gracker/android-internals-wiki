---
title: 网络协议优化（HTTP/2、HTTP/3、gRPC）
chapter: 24.5
section: 24.5
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "AOSP android-17.0.0_r1 and Android common kernel android17-6.18-2026-06_r6; Android Developers HttpEngine, Cronet and API reference updated through 2026-08-03; OkHttp 5.4.0 source and changelog; IETF RFC 9000, 9001, 9113 and 9114; current gRPC guides"
confidence: high
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/HttpEngine.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/ConnectionMigrationOptions.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/UrlResponseInfo.java"
  - type: aosp-kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c"
  - type: official
    path: "https://developer.android.com/reference/android/net/http/HttpEngine.Builder"
  - type: official
    path: "https://developer.android.com/reference/android/net/http/ConnectionMigrationOptions"
  - type: official
    path: "https://developer.android.com/reference/android/net/http/UrlResponseInfo"
  - type: official
    path: "https://developer.android.com/reference/android/net/http/FinishedRequestTimings"
  - type: official
    path: "https://developer.android.com/reference/android/net/http/UrlRequest"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/integration"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/main/CHANGELOG.md"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt"
  - type: official
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.4.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt"
  - type: legacy-reference-preserved
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt"
  - type: legacy-reference-preserved
    path: "https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt"
  - type: standard
    path: "https://www.rfc-editor.org/rfc/rfc9113.html"
  - type: standard
    path: "https://www.rfc-editor.org/rfc/rfc9000.html"
  - type: standard
    path: "https://www.rfc-editor.org/rfc/rfc9001.html"
  - type: standard
    path: "https://www.rfc-editor.org/rfc/rfc9114.html"
  - type: official
    path: "https://grpc.io/docs/platforms/android/java/basics/"
  - type: official
    path: "https://grpc.io/docs/guides/deadlines/"
  - type: official
    path: "https://grpc.io/docs/guides/wait-for-ready/"
  - type: official
    path: "https://grpc.io/docs/guides/retry/"
  - type: official
    path: "https://grpc.io/docs/guides/flow-control/"
  - type: official
    path: "https://grpc.io/docs/guides/keepalive/"
  - type: official
    path: "https://grpc.io/docs/guides/performance/"
tags: [http2, http3, quic, grpc, protocol]
related_chapters: ["24.4", "12.1", "12.2"]
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_review_finalize_at: "2026-08-15T10:21:03+08:00"
last_review_finalize_run_id: "20260815-102103-gracker-writing-review"
last_draft_polish_at: "2026-08-15T10:21:03+08:00"
last_draft_polish_run_id: "20260815-102103-gracker-writing"
---

# 网络协议优化（HTTP/2、HTTP/3、gRPC）

## 协议名称不等于性能收益

协议名称不会直接转化为性能收益。HTTP/2、HTTP/3 和 gRPC 解决的问题不同：

- HTTP/2 用逻辑流（stream）复用和 HPACK 首部压缩，减少并发请求对连接数量与重复首部字节的需求。
- HTTP/3 在 QUIC 传输协议上提供 HTTP 语义。QUIC 的每条逻辑流独立排序，可避免 TCP 丢包让同一连接所有流一起等待的传输层队头阻塞，并支持连接迁移。
- gRPC 是远程过程调用（Remote Procedure Call，RPC）框架和接口契约；Android 常用实现仍通过 HTTP/2 传输，它不等于 HTTP/3。

平台锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，客户端与协议依据为 OkHttp 5.4.0、RFC 9113、RFC 9000、RFC 9001、RFC 9114 和当前 gRPC 官方文档。连接池、DNS、超时和重试边界见 [24.4 网络架构与连接管理](04-network-architecture.md)，分段性能与 TLS 见 [12.1 网络性能优化](../../part2-performance/ch12-apk-network/01-network-performance.md) 和 [12.2 网络安全与 TLS 性能](../../part2-performance/ch12-apk-network/02-network-security-tls-performance.md)。

## 协议能力来自不同组件

Android 项目常见的协议能力来自不同组件：

| 组件 | Android 17 下的协议能力 | 版本边界 |
| --- | --- | --- |
| OkHttp 5.4.0 | HTTP/1.1、HTTP/2 | 没有稳定的公开 HTTP/3 配置入口 |
| `android.net.http.HttpEngine` | 由设备提供的 HTTP 引擎处理 HTTP/1.1、HTTP/2、HTTP/3 | API 34 起可用，也可由 S Extensions 7（系统组件扩展版本 7）提供；实际能力受设备实现影响 |
| Cronet 库 | Chromium 网络栈，支持 HTTP/1.1、HTTP/2 和基于 QUIC 的 HTTP/3 | 能力取决于项目采用的 Cronet 实现与版本 |
| gRPC Java / Kotlin | RPC 语义、生成的客户端代理（stub）、流式调用、调用截止时间（deadline）与状态码 | Android 常用传输基于 HTTP/2，也可评估 Cronet 传输实现 |

配置允许 HTTP/3，只表示客户端可以选择它。服务端能力、Alt-Svc（服务器声明同一资源可由另一地址或协议提供的响应首部）、代理、UDP 可达性、证书和客户端状态都会影响本次请求的最终协议。线上数据必须记录实际协商结果，不能用客户端库名称代替。

## HTTP/2 多路复用与服务端推送

### 多路复用减少连接，不消除排队

HTTP/2 保留 HTTP 方法、状态码和首部语义，将消息编码为二进制帧（frame），再把帧归入不同逻辑流。多个流可以在同一连接上交错传输，HPACK 则用动态表等机制压缩重复首部。Android 上的 HTTPS 请求通常通过 ALPN（Application-Layer Protocol Negotiation，TLS 握手中的应用层协议协商）选择 `h2`。

| 维度 | HTTP/1.1 | HTTP/2 |
| --- | --- | --- |
| 并发请求 | 通常需要多条连接 | 一条连接可以承载多个逻辑流 |
| 首部编码 | 每次发送文本首部 | HPACK 可复用首部表并压缩 |
| 应用层队头等待 | 一条连接同一时刻通常处理一次请求—响应交换 | 不同逻辑流可并发推进 |
| 传输层队头等待 | TCP 丢包阻塞连接后续字节 | 仍运行在 TCP 上，因此影响同一连接的所有逻辑流 |
| 流量控制 | 主要依靠 TCP 与应用读取 | 同时存在连接级和逻辑流级 HTTP/2 流量控制 |

HTTP/2 的并发数还受服务端 `SETTINGS_MAX_CONCURRENT_STREAMS`（一条连接允许同时活跃的逻辑流上限）、客户端 `Dispatcher`、连接与逻辑流的流量窗口、服务端容量和设备资源限制。它不会保证所有请求都共用一条连接，也不会为业务请求提供优先级承诺。OkHttp 5.4.0 还把单个 HTTP/2 响应的首部总量限制为 256 KiB（262,144 字节）；超大首部不能依赖客户端无限接收。

大响应体会争用同一连接的带宽和拥塞窗口。消费方长时间不读取响应体，还会产生逻辑流级背压，也就是接收方处理不及时后逐步限制发送方，并可能影响连接级流量窗口。大文件与短 API 是否使用同一客户端或 `Dispatcher`，应根据排队以及 P95、P99 等尾部耗时决定；P95、P99 分别表示 95%、99% 的样本不超过的耗时。不能只凭“HTTP/2 支持多路复用”得出结论。

连接复用仍取决于 OkHttp 的 `Address`（连接地址配置）、`Route`（具体连接路径）、证书和连接健康状态。把资源分散到多个域名的“域名分片”可能增加 DNS、TCP 与 TLS 成本，也可能阻止符合条件的 HTTP/2 连接合并。资格检查见 [24.4 网络架构与连接管理](04-network-architecture.md)。

### 服务器推送（Server Push）是协议能力，不是 OkHttp 应用能力

RFC 9113 定义了 `PUSH_PROMISE`（服务器在客户端请求前声明将主动发送某项资源的帧），但客户端可以限制或拒绝推送。OkHttp 5.4.0 的 `Http2Connection.Builder` 仍默认使用内部 `PushObserver.CANCEL`；该观察器收到推送事件后请求取消，`OkHttpClient.Builder` 也没有面向应用开放的 `PushObserver` 配置。

因此，使用 OkHttp 的 Android 应用不应把 HTTP/2 服务器推送写进可执行的性能方案。更容易观测和控制的替代方式包括：

- 首屏聚合接口，减少明确存在的依赖链。
- 客户端在用户意图足够明确时发起可取消的预取。
- 使用标准 HTTP 缓存，让重复资源按新鲜度复用。
- 服务端返回资源清单，由客户端按当前界面、网络费用和本地缓存决定是否获取。

即使换用支持推送的客户端，也要测量推送资源被使用、已缓存、重复传输和取消的比例。协议存在该能力，不代表它对移动 API 有净收益。

## HTTP/3 与 QUIC 的收益边界

### 传输层发生了什么变化

HTTP/3 把 HTTP 消息映射到 QUIC 逻辑流，并用 QPACK 压缩首部。QUIC 在 UDP 之上实现可靠传输、拥塞控制、TLS 1.3、逻辑流复用和连接 ID（不依赖 IP 地址与端口的连接标识）。它主要改变以下行为：

- 一条逻辑流丢失的数据需要重传时，其他不依赖该数据的流可以继续交付。HTTP/2 运行在单个 TCP 有序字节流上，丢失字节会阻塞后续字节。
- TLS 与 QUIC 握手集成，已建立状态满足条件时可使用恢复；0-RTT 仍是可选能力。
- 连接用连接 ID 标识，IP 地址或端口变化后可以验证新路径是否可用，再迁移连接。

这些机制仍有共享资源。QUIC 的拥塞控制通常作用于连接路径；丢包使拥塞窗口缩小时，多条逻辑流的吞吐都会受到影响。HTTP/3 也不会缩短 DNS、服务端处理或应用读取时间。

QUIC 的协议状态机位于 Cronet/Chromium 进程代码中。Android 通用内核（common kernel）负责 UDP 套接字、IP、路由、队列和设备驱动，不实现 HTTP/3 状态机。内核锚点为 `android17-6.18-2026-06_r6`；可从该标签的 [`net/ipv4/udp.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c) 继续追踪 UDP 收发。

### 连接迁移不是切网成功保证

RFC 9000 定义了连接迁移和路径验证机制。Android 17 的 `ConnectionMigrationOptions` 源码也写明两项前提：连接必须是 QUIC，服务端必须支持迁移。客户端还要面对以下约束：

- 新网络需要可达同一服务端，并通过路径验证。
- NAT（网络地址转换）、企业代理、VPN、防火墙和服务端负载均衡配置可能阻止迁移。
- 迁移期间的请求可能超时或被取消，业务仍要有恢复策略。
- 允许使用非默认网络可能产生流量费用；`setAllowNonDefaultNetworkUsage()` 在 AOSP `android-17.0.0_r1` 中标注为实验 API。

`HttpEngine.Builder.setConnectionMigrationOptions()` 在同一源码锚点中也带有 `ConnectionMigrationOptions.Experimental` 注解。项目可以在受控实验中启用默认网络迁移；上线前要验证设备实现、服务端、代理、计费网络和远程关闭开关。

### 0-RTT 只用于可重放操作

QUIC 的 0-RTT（零往返恢复）允许恢复连接在握手完成前发送早期数据（early data），但这类数据缺少跨连接的防重放保证。攻击者可能重新发送捕获的数据，因此登录、支付、下单和产生一次性副作用的写请求不能仅凭“使用 HTTPS”就进入 0-RTT。

`HttpEngine.Builder.addQuicHint()` 用主机与备用端口提示服务器支持 QUIC。官方文档还说明，跨引擎会话利用 0-RTT 需要启用磁盘缓存。即使配置满足，服务端也可以拒绝早期数据，客户端必须允许按正常握手继续。指标应区分最终协议和业务总耗时，不应把“启用 QUIC”直接记成“命中 0-RTT”。

### UDP、代理和发现机制决定可用性

HTTP/3 依赖 UDP。部分企业网络、代理、VPN 或热点会阻断或限制 QUIC，客户端需要保留基于 TCP 的 HTTP/2 或 HTTP/1.1。RFC 9114 允许在 QUIC 连接出现问题时改用基于 TCP 的 HTTP。

服务端还要通过客户端支持的方式声明 HTTP/3 能力，例如发送 Alt-Svc，或者由应用提供可信的 QUIC 能力提示（hint）。调用 `setEnableQuic(true)` 只允许引擎选择 QUIC，不会让缺少服务端配置的域名自动使用 HTTP/3。

Android 17 / API 37（同时属于 S Extensions 22）为 `HttpEngine.Builder` 增加 `setProxyOptions()`。应用代理配置会覆盖系统代理配置；若企业环境依赖系统代理，错误的应用代理或代理列表缺少末尾的 `null` 回退，可能导致网络完全不可达。分批启用协议的实验还必须包含企业代理和 VPN 场景。

## Android 17 上选择 OkHttp、HttpEngine 或 Cronet

### OkHttp 5.4.0

OkHttp 适合已有 Retrofit、拦截器、Cookie、缓存和 `EventListener` 体系的 HTTP/1.1、HTTP/2 API。它能通过 `Response.protocol` 报告最终协议，也能用 `EventListener` 记录 DNS、连接、TLS 和交换阶段。OkHttp 5.4.0 没有稳定的公开 HTTP/3 配置入口。

若项目希望保留 OkHttp API 并使用 Cronet 传输实现，Android 官方集成文档列出了 `Cronet Transport for OkHttp`。接入时仍要核对该传输库的版本、支持的 OkHttp API、拦截器语义、缓存、证书、代理和事件指标；更换依赖不会自动保留全部行为。

### HttpEngine

`HttpEngine` 从 API 34 起提供，也标注为 S Extensions 7。AOSP `android-17.0.0_r1` 的 `HttpEngine.Builder` 直接使用 `NativeCronetEngineBuilderImpl`。默认配置如下：

- 启用 HTTP/2。
- 启用 QUIC。
- 关闭 HTTP 缓存。

默认启用表示引擎可以选择相应协议，最终请求仍可能使用 HTTP/1.1 或 HTTP/2。若需要 HTTP 缓存，必须显式配置缓存模式与容量；磁盘缓存还要配置独占的存储目录。同一目录不能同时被多个 `HttpEngine` 使用。

`HttpEngine` 应作为长生命周期对象复用，并在不再使用时调用 `shutdown()`。按请求创建引擎会失去连接、QUIC 状态、线程和缓存复用，也可能违反存储目录的单实例约束。

### Cronet 库

Cronet 是供 Android 应用使用的 Chromium 网络栈。当前 Android 官方概览确认其原生支持 HTTP/1.1、HTTP/2 与基于 QUIC 的 HTTP/3，但没有承诺每种集成方式都提供相同能力。项目必须从实际依赖与运行时实现确认提供方、版本、原生库加载结果和协议支持。

Android 10—13 若要使用 HTTP/3，通常需要外部 Cronet；Android 14 及以上可评估平台 `HttpEngine`。选择哪条路径还取决于安装包体积、设备覆盖、更新渠道、现有网络层适配，以及诊断与指标能力。

### 基础 API 37 能观测什么

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

应在终止回调中读取最终字节数；`onFailed()` 和 `onCanceled()` 还要先确认 `UrlResponseInfo` 非空。`wasCached()` 返回 `true` 时也可能包含经过网络重新验证的响应，不能把它一律解释成零网络流量。`getReceivedByteCount()` 是处理请求所需网络字节的最小计数，包含所有重定向的首部与数据，并在解压前统计；它可以忽略 IP、TCP/UDP、TLS 和代理开销。空协议字符串表示未协商、未知或普通 HTTP/HTTPS，不能自行改写成 HTTP/1.1。

`FinishedRequestTimings` 和 `UrlRequest.getFinishedRequestTimings()` 是 37.1 / S Extensions 23 新增能力，只能在成功、失败或取消的终止回调到达后读取，不属于 API 37 / `android-17.0.0_r1` 锚点。基础 API 37 不能据此声称可直接获得 DNS、连接和 TLS/QUIC 的完整公开时序。

## gRPC 在移动端的实践

### gRPC 是调用契约，不是通用 HTTP 替代品

gRPC 用 `.proto` 接口定义文件描述服务与消息，Android 通常使用 protobuf lite（精简版 Protocol Buffers 运行库）生成客户端类型。它提供四种方法形态：

| 方法形态 | 请求与响应 | 适合的业务 |
| --- | --- | --- |
| 一元调用 | 单请求、单响应 | 有明确边界的查询与写入 |
| 服务端流 | 单请求、响应流 | 服务端持续发送一组结果或更新 |
| 客户端流 | 请求流、单响应 | 分段上传或批量聚合 |
| 双向流 | 双向流 | 双方独立持续发送消息的会话 |

这四种形态的差别在于哪一侧可以持续发送消息；采用流式调用后，还要另行设计流量控制和断线恢复。生成代码能提供字段类型与方法签名，但协议演进仍要遵守 Protocol Buffers 兼容规则。字段号不能复用，删除字段应保留编号，客户端与服务端要支持新旧版本交错发布。序列化边界见 [24.3 序列化与反序列化](03-serialization-performance.md)。

标准 gRPC 在 HTTP/2 上承载键值元数据（metadata）、带长度前缀的消息和响应体结束后发送的尾部字段（trailers）。HTTP 状态码不足以表示 RPC 结果；监控必须记录 gRPC 状态码、服务名、方法名、调用截止时间、取消、消息字节和每次尝试，不能只记录 HTTP 200。

### `Channel` 是逻辑通信通道

gRPC `Channel` 表示到一个逻辑目标的通信通道，可以在内部持有零条、一条或多条实际连接，并参与名称解析与客户端负载均衡。它不等同于一条套接字连接。

官方性能建议要求尽量复用 `Channel` 和生成的客户端代理（stub）。复用边界应按逻辑目标（target）、TLS、代理、名称解析和服务配置决定。用户令牌更适合通过每次调用的调用凭据（credentials）或元数据提供；仅因账号切换就重建 `Channel`，会丢失可安全共享的传输资源。认证实现必须避免把旧令牌固化在长生命周期拦截器中。

### 调用截止时间、取消和 Wait-for-Ready

gRPC 默认不设置调用截止时间（deadline），客户端因此可能一直等待。每个方法需要根据用户交互期限、网络耗时分布和服务端处理预算显式设置截止时间。上游取消、页面销毁和后台任务停止也应传播到 RPC。

`wait-for-ready`（等待通道就绪）会在 `Channel` 暂时不可用时把调用留在队列中，待连接恢复后再发送；默认模式会更早返回失败。调用截止时间仍然生效，因此它只适合允许短暂等待连接恢复的调用，不能绕过用户取消或无限延长启动等待。

流式 RPC 还要定义断线恢复语义。连接中断时，未完成的逻辑流会失败；重新建流不能自动恢复业务位置。消息序号、游标、确认、去重和补发属于应用协议。

流式 RPC 还受 gRPC 与 HTTP/2 流量控制约束。一次写入只表示消息交给 gRPC，不代表字节已经发到网络；发送方速度长期高于接收方时，框架会等待或缓存。应用队列必须有界，手动流量控制还要保证两端持续读取，避免双方都等待写入空间。

### 重试由服务配置（Service Config）和业务语义共同决定

gRPC 支持透明重试：即使没有显式重试策略，也可能在确认调用没有进入服务端应用逻辑时，恢复少量因并发事件先后顺序不确定而产生的底层故障。更广泛的重试通过 Service Config（服务配置）按方法设置尝试次数上限、逐次延长的等待间隔、可重试状态码和重试总量限制。

状态码 `UNAVAILABLE` 并不自动表示业务操作可重复。客户端与服务端仍要确认方法语义：

- 查询或幂等操作可以在总截止时间内进行受控重试。
- 写操作需要幂等键、版本条件或查询确认，不能只按 gRPC 状态码重发。
- 一旦收到响应首部，gRPC 重试机制会把 RPC 视为已提交，不再按同一策略重试。
- 应同时记录逻辑 RPC 与每次尝试，避免把内部重试时间全部归为一次服务端延迟。

### 保活探测（Keepalive）和长流会消耗移动网络资源

gRPC 保活探测使用 HTTP/2 `PING` 检查空闲连接。客户端需要与服务端约定频率，以及没有活动 RPC 时是否允许发送；当前官方指南建议客户端不要把间隔设得远低于一分钟，也建议避免在没有调用时启用保活。服务端可发送 `GOAWAY`（通知客户端停止在该连接上创建新流）和 `too_many_pings` 调试信息，拒绝过密探测。

移动端还要考虑蜂窝无线电唤醒、Doze（Android 设备空闲省电模式）、应用进程回收和后台执行限制。低频通知通常更适合系统共享推送通道。长流适用于前台持续交互或业务确有连续传输需求的场景，并应具备取消、恢复与断点状态。

长生命周期逻辑流启动后通常不能重新参与客户端负载均衡。服务端滚动发布、连接年龄和节点故障都会中断它，因此固定保持一条永久逻辑流不能保证高可用。

## 协议选型与兼容策略

### 从请求形态与系统约束选择

| 请求形态 | 候选方案 | 需要验证的边界 |
| --- | --- | --- |
| 常规 REST / JSON，同一主机与端口组合（authority）下短请求较多 | OkHttp + HTTP/2 | 网关与 CDN 的 ALPN、连接复用、服务端逻辑流上限 |
| 媒体、长下载、切网与丢包敏感流量 | HttpEngine / Cronet，评估 HTTP/3 | UDP、代理、VPN、服务端 QUIC、迁移和缓存 |
| 自有客户端与服务端之间的强类型 RPC | 基于 HTTP/2 的 gRPC | Protocol Buffers 演进、网关、状态码与尾部字段、截止时间、重试 |
| 长生命周期双向消息 | gRPC 双向流或已有消息协议 | 后台限制、流量控制、断线恢复、负载均衡 |
| 浏览器和第三方共同使用的公开接口 | REST / JSON，必要时另建 gRPC-Web 网关 | 调试、兼容、缓存和跨语言契约 |
| 可延迟后台上报 | 批量 REST 或批量 RPC | WorkManager 约束、幂等、与交互流量隔离 |

这张表只给出候选方向，不能代替设备与服务端实验。协议选择还要计算安装包体积、适配成本、发布渠道和排障工具。一个小型低频接口即使能使用 gRPC 或 HTTP/3，也可能无法抵消新增依赖与运维成本。

### 回退要分协议与业务两层

HTTP/3 到 HTTP/2、HTTP/2 到 HTTP/1.1 属于同一 HTTP 语义下的传输协商。成熟客户端可以根据服务端和网络条件完成。应用仍要记录最终协议和错误，但不必为每次 QUIC 失败手写另一遍请求。

gRPC 到 REST 属于两套接口契约，不是协议自动回退。只有业务明确维护双路径时才可使用，而且两条路径必须共享：

- 权限与鉴权规则。
- 幂等键、版本条件和重复提交处理。
- 字段含义、默认值和错误映射。
- 分批发布、审计与数据一致性规则。

双路径会增加测试与服务端维护成本。多数业务更适合在当前 RPC 上恢复或显示错误，而不是看到任意 gRPC 失败就改发 REST。

### 更换传输实现时保持业务契约不变

从 OkHttp 迁移到 HttpEngine/Cronet，或为 OkHttp 接入 Cronet 传输实现时，应逐项核对：

- `Authorization`、Cookie、跨服务关联一次调用的追踪标识（trace ID）、实验首部和 `User-Agent`。
- Network Security Config（Android 网络安全配置）、证书或公钥固定、用户安装的 CA（证书颁发机构）证书、系统代理、应用代理和 VPN。
- HTTP 缓存、业务缓存、Cookie 存储和磁盘目录。
- 重定向、上传重放、取消、超时和后台生命周期。
- 压缩、字节统计、错误分类和敏感字段脱敏。

协议实验期间保持接口语义、服务端业务逻辑和缓存策略稳定。多项改动同时发布会破坏归因。

## 协议实验与观测

### 各客户端公开指标不同

| 客户端 | 基础可观测信息 | 限制 |
| --- | --- | --- |
| OkHttp 5.4.0 | `Response.protocol`、`EventListener` 阶段、连接事件 | HTTP/2 逻辑流并发与底层 TCP 指标不是完整公开 API |
| 基础 API 37 HttpEngine | `getNegotiatedProtocol()`、`wasCached()`、接收字节下界、回调时刻与异常 | 没有 37.1 的 `FinishedRequestTimings` |
| Cronet 库 | 实现提供方给出的请求完成信息、NetLog（Chromium 网络诊断日志）与回调 | 能力随 Cronet 版本和集成方式变化 |
| gRPC | 方法、状态码、截止时间、元数据、逻辑调用和每次尝试 | 还需与所用传输实现的连接指标关联 |

最终协商为 HTTP/2，不能证明客户端尝试过 HTTP/3。只有底层日志或可靠的连接尝试指标能区分“未发现 HTTP/3”“UDP 不通”“QUIC 握手失败”和“策略未启用”。缺少证据时，应把数据标记为最终协议，不能命名为 HTTP/3 回退。

### 实验单位与分层

协议实验应稳定地按用户或设备分组，并限制到明确的主机与接口。分析时至少按以下维度分层：

- 最终协议、客户端实现与实现提供方版本。
- 默认网络变化序号、传输类型、计费属性、VPN 和代理。
- 请求与响应大小、缓存状态、冷连接或复用连接。
- DNS、连接、握手、TTFB（Time to First Byte，从请求发出到收到响应首部的等待）、响应体与逻辑调用总时长；只使用当前客户端实际公开的阶段。
- HTTP 或 gRPC 错误、取消、重试尝试与最终成功率。
- 前台交互、后台任务、媒体传输和切网场景。

比较中位数和高分位延迟，同时观察错误率、取消率、字节量与电量。连接状态、CDN 节点、服务端版本和缓存命中未分层时，平均值变化无法归因到协议。

分批实验开关应支持按主机、接口、网络类型、客户端版本和应用版本关闭。关闭实验并恢复原传输实现时，只改变传输选择，不能丢失正在执行写操作的幂等状态。

## 工程检查清单

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

## 源码与规范依据

### 当前平台与客户端依据

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

### 保留的旧版本源码锚点

- [OkHttp 5.3.0 Http2Connection](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt)
- [OkHttp 5.3.0 PushObserver](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt)

### 协议与 gRPC 依据

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
