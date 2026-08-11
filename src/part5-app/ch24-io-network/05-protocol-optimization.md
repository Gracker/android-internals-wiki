---
title: 网络协议优化（HTTP/2、HTTP/3、gRPC）
chapter: 24.5
section: 24.5
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: 2026-07-01
last_verified_against: AOSP android-17.0.0_r1 external/cronet HttpEngine.java / ConnectionMigrationOptions.java + Android Developers docs 2026-07-01 + OkHttp 5.x docs + IETF RFC 9000/9114 + gRPC docs
confidence: medium
drafted_date: 2026-05-14
reviewed_by: openclaw-task6
reviewed_date: 2026-05-14
task6_result: pass-light-edit
polish_count: 1
sources:
  - type: aosp
    path: "https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/HttpEngine.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/ConnectionMigrationOptions.java"
tags: [http2, http3, quic, grpc, protocol]
related_chapters: ["24.4", "12.1", "12.2"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_task2a_at: 2026-05-14T10:04:00+08:00
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-07-01
last_task9_at: "2026-07-01T03:30:55+08:00"
last_task9_autofix_at: "2026-07-01"
last_task9_review_log: logs/deep-review/2026-07-01-03-audit.md
task9_review_notes: 2026-07-01 Task9 闲时抽检 auto-fix：将 HttpEngine / ConnectionMigrationOptions 源码锚点从旧本地 SDK source 重锚到 AOSP android-17.0.0_r1 external/cronet；P0 0 / P1 0 / P2 1（已修）；回到 Task6 复审。
last_task6_audit: 2026-07-03
last_task9_audit: 2026-07-01
last_task9_audit_log: logs/deep-review/2026-07-01-03-audit.md
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-06
---
# 网络协议优化（HTTP/2、HTTP/3、gRPC）

## 为什么要了解网络协议优化（HTTP/2、HTTP/3、gRPC）

协议名称不会直接转化为性能收益。HTTP/2、HTTP/3 和 gRPC 解决的问题不同：

- HTTP/2 用 stream 复用和 HPACK 减少并发请求对连接数量与重复首部的需求。
- HTTP/3 在 QUIC 上提供 HTTP 语义，避免 TCP 字节流导致的跨 stream 传输层队头阻塞，并支持连接迁移机制。
- gRPC 是 RPC 框架和调用契约，Android 上的常用传输仍是 HTTP/2；它不等于 HTTP/3。

平台锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，客户端与协议依据为 OkHttp 5.3.0、RFC 9113、RFC 9000、RFC 9114 和当前 gRPC 官方文档。连接池、DNS、超时和重试边界见 [24.4 网络架构与连接管理](04-network-architecture.md)，分段性能与 TLS 见 [12.1 网络性能优化](../../part2-performance/ch12-apk-network/01-network-performance.md) 和 [12.2 网络安全与 TLS 性能](../../part2-performance/ch12-apk-network/02-network-security-tls-performance.md)。

## 先区分协议、客户端和传输实现

Android 项目常见的协议能力来自不同组件：

| 组件 | Android 17 下的协议能力 | 版本边界 |
| --- | --- | --- |
| OkHttp 5.3.0 | HTTP/1.1、HTTP/2 | 没有稳定的公开 HTTP/3 配置入口 |
| `android.net.http.HttpEngine` | 由设备提供的 HTTP 引擎处理 HTTP/1.1、HTTP/2、HTTP/3 | API 34 起可用，也标注为 S Extensions 7；实际能力受设备实现影响 |
| Cronet 库 | Chromium 网络栈，支持 HTTP/1.1、HTTP/2、HTTP/3 over QUIC | 随应用或 Google Play services 提供，能力取决于所选实现提供方与版本 |
| gRPC Java / Kotlin | RPC 语义、生成 stub、streaming、deadline 与状态码 | 常用 Android transport 基于 HTTP/2；也可评估 Cronet transport |

“启用 HTTP/3”和“这次请求使用 HTTP/3”也是两件事。服务端能力、Alt-Svc 或其他发现机制、代理、UDP 可达性、证书、客户端状态都会影响最终协商。线上数据必须记录请求实际使用的协议，不能用客户端库名称代替。

## HTTP/2 多路复用与服务端推送

### 多路复用减少连接，不消除排队

HTTP/2 保留 HTTP 方法、状态码和首部语义，将消息编码为二进制 frame，并把 frame 归属到不同 stream。多个 stream 可以在同一连接上交错传输，HPACK 则压缩重复首部。Android 上的 HTTPS 请求通常通过 ALPN 协商 `h2`。

| 维度 | HTTP/1.1 | HTTP/2 |
| --- | --- | --- |
| 并发请求 | 通常需要多条连接 | 一条连接可以承载多个 stream |
| 首部编码 | 每次发送文本首部 | HPACK 可复用首部表并压缩 |
| 应用层队头等待 | 一条连接同一时刻通常处理一个 exchange | stream 可并发推进 |
| 传输层队头等待 | TCP 丢包阻塞连接后续字节 | 仍运行在 TCP 上，因此影响同一连接的 stream |
| 流量控制 | 主要依靠 TCP 与应用读取 | 同时存在连接级和 stream 级 HTTP/2 流量控制 |

HTTP/2 的并发数还受服务端 `SETTINGS_MAX_CONCURRENT_STREAMS`、客户端 Dispatcher、连接和 stream 流量窗口、服务端容量与设备资源限制。它不会保证所有请求都共用一条连接，也不会为业务请求提供优先级承诺。

大响应体会争用同一连接的带宽和拥塞窗口。消费方长时间不读取响应体，还会产生 stream 级背压，并可能影响连接级流量窗口。大文件与短 API 是否使用同一客户端或 Dispatcher，应根据排队和尾延迟数据决定，不能只凭“HTTP/2 支持多路复用”得出结论。

连接复用仍取决于 OkHttp 的 `Address`、route、证书和连接健康状态。域名分片可能增加 DNS、TCP 与 TLS 成本，也可能阻止符合条件的 HTTP/2 连接合并。相关资格检查见 24.4。

### Server Push 是协议能力，不是 OkHttp 应用能力

RFC 9113 定义了 `PUSH_PROMISE`，但客户端可以限制或拒绝推送。OkHttp 5.3.0 的 `Http2Connection.Builder` 默认使用内部 `PushObserver.CANCEL`；该观察器收到推送事件后请求取消，`OkHttpClient.Builder` 也没有面向应用开放的 PushObserver 配置。

因此，使用 OkHttp 的 Android 应用不应把 HTTP/2 Server Push 写进可执行的性能方案。更容易观测和控制的替代方式包括：

- 首屏聚合接口，减少明确存在的依赖链。
- 客户端在用户意图足够明确时发起可取消的预取。
- 使用标准 HTTP 缓存，让重复资源按新鲜度复用。
- 服务端返回资源清单，由客户端按当前界面、网络费用和本地缓存决定是否获取。

即使换用支持推送的客户端，也要测量推送资源被使用、已缓存、重复传输和取消的比例。协议存在该能力，不代表它对移动 API 有净收益。

## HTTP/3 与 QUIC 的收益边界

### 传输层发生了什么变化

HTTP/3 把 HTTP 消息映射到 QUIC stream。QUIC 在 UDP 之上实现可靠传输、拥塞控制、TLS 1.3、stream 复用和连接 ID。它主要改变以下行为：

- 一个 stream 丢失的数据需要重传时，其他不依赖该数据的 stream 可以继续交付。HTTP/2 运行在单个 TCP 有序字节流上，丢失字节会阻塞后续字节。
- TLS 与 QUIC 握手集成，已建立状态满足条件时可使用恢复；0-RTT 仍是可选能力。
- 连接用 connection ID 标识，IP 地址或端口变化后可以执行路径验证和迁移。

这些机制仍有共享资源。QUIC 的拥塞控制通常作用于连接路径，丢包导致拥塞窗口变化时，多个 stream 的吞吐都会受到影响。HTTP/3 也不会缩短 DNS、服务端处理或应用读取时间。

QUIC 位于 Cronet/Chromium 用户空间。Android common kernel 负责 UDP socket、IP、路由、队列和设备驱动，不实现 HTTP/3 状态机。内核锚点为 `android17-6.18-2026-06_r6`；可从该标签的 [`net/ipv4/udp.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c) 继续追踪 UDP 收发。

### 连接迁移不是切网成功保证

RFC 9000 定义了连接迁移和路径验证机制。Android 17 的 `ConnectionMigrationOptions` 源码也写明两项前提：连接必须是 QUIC，服务端必须支持迁移。客户端还要面对以下约束：

- 新网络需要可达同一服务端，并通过路径验证。
- NAT、企业代理、VPN、防火墙和服务端负载均衡配置可能阻止迁移。
- 迁移期间的请求可能超时或被取消，业务仍要有恢复策略。
- 允许使用非默认网络可能产生流量费用；`setAllowNonDefaultNetworkUsage()` 在 AOSP `android-17.0.0_r1` 中标注为实验 API。

`HttpEngine.Builder.setConnectionMigrationOptions()` 在同一源码锚点中也带有 `ConnectionMigrationOptions.Experimental` 注解。项目可以在受控实验中启用默认网络迁移，生产使用前要验证设备实现、服务端、代理、计费网络和关闭开关。

### 0-RTT 只用于可重放操作

QUIC 的 0-RTT 允许恢复连接在握手完成前发送 early data，但这类数据缺少连接间防重放保证。登录、支付、下单和产生一次性副作用的写请求不能仅凭“使用 HTTPS”就进入 0-RTT。

HttpEngine 的 `addQuicHint()` 文档还说明，跨引擎会话利用 0-RTT 需要启用磁盘缓存。即使配置满足，服务端也可以拒绝 early data，客户端必须允许按正常握手继续。指标应区分最终协议和业务总耗时，不应把“启用 QUIC”直接记成“命中 0-RTT”。

### UDP、代理和发现机制决定可用性

HTTP/3 依赖 UDP。部分企业网络、代理、VPN 或热点会阻断或限制 QUIC，客户端需要保留基于 TCP 的 HTTP/2 或 HTTP/1.1。RFC 9114 明确允许在 QUIC 连接问题发生时尝试 TCP-based HTTP。

服务端还要通过客户端支持的方式声明 HTTP/3 能力，例如 Alt-Svc，或者由应用提供可信的 QUIC hint。打开 `setEnableQuic(true)` 只允许引擎使用 QUIC，不会让缺少服务端配置的域名自动变成 HTTP/3。

Android 17 / API 37 为 `HttpEngine.Builder` 增加 `setProxyOptions()`。应用代理配置会覆盖系统代理配置；若企业环境依赖系统代理，错误的应用代理或缺少最终的 `null` 回退可能导致完全不可达。协议灰度必须包含企业代理和 VPN 场景。

## Android 17 上选择 OkHttp、HttpEngine 或 Cronet

### OkHttp 5.3.0

OkHttp 适合已有 Retrofit、拦截器、Cookie、缓存和 EventListener 体系的 HTTP/1.1、HTTP/2 API。它能通过 `Response.protocol` 报告最终协议，也能用 EventListener 记录 DNS、连接、TLS 和交换阶段。OkHttp 5.3.0 没有稳定的公开 HTTP/3 配置入口。

若项目希望保留 OkHttp API 并使用 Cronet transport，Android 官方集成文档列出了 Cronet Transport for OkHttp。接入时仍要核对该 transport 的版本、支持的 OkHttp API、拦截器语义、缓存、证书、代理和事件指标；它不是替换依赖后即可无差异工作的开关。

### HttpEngine

`HttpEngine` 从 API 34 起提供，也标注为 S Extensions 7。AOSP `android-17.0.0_r1` 的 `HttpEngine.Builder` 直接使用 `NativeCronetEngineBuilderImpl`。默认配置：

- 启用 HTTP/2。
- 启用 QUIC。
- 关闭 HTTP 缓存。

默认启用表示协议可被选择，最终请求仍可能使用 HTTP/1.1 或 HTTP/2。若需要 HTTP 缓存，必须显式配置缓存模式与容量；磁盘缓存还要配置独占的存储目录。同一目录不能同时被多个 HttpEngine 使用。

HttpEngine 应作为长生命周期对象复用，并在不再使用时调用 `shutdown()`。按请求创建引擎会失去连接、QUIC 状态、线程和缓存复用，也可能违反存储目录的单实例约束。

### Cronet 库

Cronet 是随应用或实现提供方交付的 Chromium 网络栈。Android 官方指南当前列出 Google Play services 提供方，并为无法加载它的情况提供 Java 回退实现。回退实现的性能和协议能力不能按 native Cronet 推断。

项目需要记录实际实现提供方、版本与最终协议。Android 10—13 若要使用 HTTP/3，通常需要外部 Cronet；Android 14 及以上可评估平台 HttpEngine。选择哪条路径还取决于包体积、设备覆盖、更新渠道、现有网络层适配和可观测性。

### 基础 API 37 能观测什么

`UrlResponseInfo` 在基础 API 37 提供最终协商协议、缓存使用情况和接收字节下界。下面的代码用于在请求的终止回调中生成一条结果记录。

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

应在终止回调中读取最终字节数；`onFailed()` 和 `onCanceled()` 还要先确认 `UrlResponseInfo` 非空。`wasCached()` 返回 `true` 时也可能包含经过网络重新验证的响应，不能把它一律解释成零网络流量。`getReceivedByteCount()` 是处理请求所需网络字节的最小计数，包含重定向且位于解压前，但可以忽略 IP、TCP/UDP、TLS 和代理开销。空协议字符串表示未协商、未知或普通 HTTP/HTTPS，不能自行改写成 HTTP/1.1。

`FinishedRequestTimings` 和 `UrlRequest.getFinishedRequestTimings()` 是 37.1 / S Extensions 23 新增能力，不属于 API 37 / `android-17.0.0_r1` 锚点。基础 API 37 不能据此声称可直接获得 DNS、连接和 TLS/QUIC 的完整公开时序。

## gRPC 在移动端的实践

### gRPC 是调用契约，不是通用 HTTP 替代品

gRPC 用 `.proto` 描述服务与消息，Android 通常使用 protobuf lite 生成客户端类型。它提供四种方法形态：

| 方法形态 | 请求与响应 | 适合的业务 |
| --- | --- | --- |
| 一元调用 | 单请求、单响应 | 有明确边界的查询与写入 |
| 服务端流 | 单请求、响应流 | 服务端持续发送一组结果或更新 |
| 客户端流 | 请求流、单响应 | 分段上传或批量聚合 |
| 双向流 | 双向流 | 双方独立持续发送消息的会话 |

生成代码能提供字段类型与方法签名，但协议演进仍要遵守 Protobuf 兼容规则。字段号不能复用，删除字段应保留编号，客户端与服务端要支持新旧版本交错发布。序列化边界见 [24.3 序列化与反序列化](03-serialization-performance.md)。

标准 gRPC 在 HTTP/2 上承载 metadata、长度前缀消息和 trailers。HTTP 状态码不足以表示 RPC 结果；监控必须记录 gRPC status、服务名、方法名、deadline、取消、消息字节和 attempt，而不是只记录 HTTP 200。

### Channel 是虚拟连接

gRPC `Channel` 表示到一个逻辑目标的通信通道，可以在内部持有零条、一条或多条实际连接，并参与名称解析与客户端负载均衡。它不能简单等同于一条 socket。

官方性能建议要求尽量复用 channel 和 stub。复用边界应按 target、TLS、代理、名称解析和服务配置决定。用户 token 更适合通过每次调用的 credentials 或 metadata 提供；仅因账号切换就重建 channel，会丢失可安全共享的传输资源。认证实现必须避免把旧 token 固化在长生命周期拦截器中。

### Deadline、取消和 Wait-for-Ready

gRPC 默认不设置 deadline，客户端可能一直等待。每个方法需要根据用户交互期限、网络分布和服务端处理预算设置 deadline。上游取消、页面销毁和后台任务停止也应传播到 RPC。

`wait-for-ready` 允许调用在 channel 暂时不可用时等待恢复，但 deadline 仍然生效。它适合允许短暂等待连接恢复的调用，不适合绕过用户取消或无限延长启动等待。

流式 RPC 还要定义断线恢复语义。连接中断时，未完成 stream 会失败；重新建流不能自动恢复业务位置。消息序号、游标、确认、去重和补发属于应用协议。

流式 RPC 还受 gRPC 与 HTTP/2 流量控制约束。一次写入只表示消息交给 gRPC，不代表字节已经发到网络；发送方速度长期高于接收方时，框架会等待或缓存。应用队列必须有界，手动流量控制还要保证两端持续读取，避免双方都等待写入空间。

### Retry 由 Service Config 和业务语义共同决定

gRPC 支持透明重试，即使没有显式 retry policy，也可能对确定未进入服务端应用逻辑的低层竞态执行有限恢复。更广泛的重试通过 Service Config 按方法配置 attempt 上限、退避、可重试状态码和节流。

状态码 `UNAVAILABLE` 并不自动表示业务操作可重复。客户端与服务端仍要确认方法语义：

- 查询或幂等操作可以在总 deadline 内进行受控重试。
- 写操作需要幂等键、版本条件或查询确认，不能只按 gRPC status 重发。
- 一旦收到响应首部，gRPC retry 机制会把 RPC 视为已提交，不再按同一策略重试。
- 应同时记录逻辑 RPC 与每次 attempt，避免把内部重试时间全部归为一次服务端延迟。

### Keepalive 和长流会消耗移动网络资源

gRPC keepalive 使用 HTTP/2 PING 检查空闲连接。客户端需要与服务端约定频率和是否允许无活动 RPC 时发送；服务端可用 `GOAWAY` 和 `too_many_pings` 拒绝过密 ping。

移动端还要考虑蜂窝无线电唤醒、Doze、应用进程回收和后台执行限制。低频通知通常更适合系统共享推送通道。长流适用于前台持续交互或业务确有连续传输需求的场景，并应具备取消、恢复与断点状态。

长生命周期 stream 启动后通常不能重新参与客户端负载均衡。服务端滚动发布、连接年龄和节点故障都会中断它，因此“保持一个永久 stream”不是高可用设计。

## 协议选型与兼容策略

### 从请求形态与系统约束选择

| 请求形态 | 候选方案 | 需要验证的边界 |
| --- | --- | --- |
| 常规 REST / JSON，同一 authority 下短请求较多 | OkHttp + HTTP/2 | 网关与 CDN 的 ALPN、连接复用、服务端 stream 上限 |
| 媒体、长下载、切网与丢包敏感流量 | HttpEngine / Cronet，评估 HTTP/3 | UDP、代理、VPN、服务端 QUIC、迁移和缓存 |
| 自有客户端与服务端之间的强类型 RPC | gRPC over HTTP/2 | protobuf 演进、网关、status/trailers、deadline、重试 |
| 长生命周期双向消息 | gRPC bidi stream 或已有消息协议 | 后台限制、流量控制、断线恢复、负载均衡 |
| 浏览器和第三方共同使用的公开接口 | REST / JSON，必要时另建 gRPC-Web 网关 | 调试、兼容、缓存和跨语言契约 |
| 可延迟后台上报 | 批量 REST 或批量 RPC | WorkManager 约束、幂等、与交互流量隔离 |

协议选择还要计算包体积、适配成本、发布渠道和排障工具。一个小型低频接口即使能使用 gRPC 或 HTTP/3，也可能无法抵消新增依赖与运维成本。

### 回退要分协议与业务两层

HTTP/3 到 HTTP/2、HTTP/2 到 HTTP/1.1 属于同一 HTTP 语义下的传输协商。成熟客户端可以根据服务端和网络条件完成。应用仍要记录最终协议和错误，但不必为每次 QUIC 失败手写另一遍请求。

gRPC 到 REST 属于两套接口契约，不是协议自动回退。只有业务明确维护双路径时才可使用，而且两条路径必须共享：

- 权限与鉴权规则。
- 幂等键、版本条件和重复提交处理。
- 字段含义、默认值和错误映射。
- 灰度、审计与数据一致性规则。

双路径会增加测试与服务端维护成本。多数业务更适合在当前 RPC 上恢复或显示错误，而不是看到任意 gRPC 失败就改发 REST。

### 更换传输实现时保持业务契约不变

从 OkHttp 迁移到 HttpEngine/Cronet，或为 OkHttp 接入 Cronet transport 时，应逐项核对：

- Authorization、Cookie、trace ID、实验首部和 User-Agent。
- Network Security Config、证书 pin、用户 CA、系统代理、应用代理和 VPN。
- HTTP 缓存、业务缓存、Cookie 存储和磁盘目录。
- 重定向、上传重放、取消、超时和后台生命周期。
- 压缩、字节统计、错误分类和敏感字段脱敏。

协议实验期间保持接口语义、服务端业务逻辑和缓存策略稳定。多项改动同时发布会破坏归因。

## 协议灰度与可观测性

### 各客户端公开指标不同

| 客户端 | 基础可观测信息 | 限制 |
| --- | --- | --- |
| OkHttp 5.3.0 | `Response.protocol`、EventListener 阶段、连接事件 | HTTP/2 stream 并发与底层 TCP 指标不是完整公开 API |
| 基础 API 37 HttpEngine | `getNegotiatedProtocol()`、`wasCached()`、接收字节下界、回调时刻与异常 | 没有 37.1 的 `FinishedRequestTimings` |
| Cronet 库 | 实现提供方给出的请求完成信息、NetLog 与回调 | 能力随 Cronet 版本和集成方式变化 |
| gRPC | method、status、deadline、metadata、逻辑调用和 attempt 指标 | 还需与所用 transport 的连接指标关联 |

最终协商为 HTTP/2 不能证明客户端先尝试过 HTTP/3。只有底层日志或可靠的 attempt 指标能区分“未发现 HTTP/3”“UDP 不通”“QUIC 握手失败”和“策略未启用”。缺少证据时，应把数据标记为最终协议，不能命名为 HTTP/3 回退。

### 实验单位与分层

协议实验应稳定地按用户或设备分组，并限制到明确的 host 与接口。分析时至少按以下维度分层：

- 最终协议、客户端实现与实现提供方版本。
- 默认网络变化序号、transport、计费属性、VPN 和代理。
- 请求与响应大小、缓存状态、冷连接或复用连接。
- DNS、连接、握手、TTFB、响应体与逻辑调用总时长；只使用当前客户端实际公开的阶段。
- HTTP 或 gRPC 错误、取消、重试 attempt 与最终成功率。
- 前台交互、后台任务、媒体传输和切网场景。

比较中位数和高分位延迟，同时观察错误率、取消率、字节量与电量。连接状态、CDN 节点、服务端版本和缓存命中未分层时，平均值变化无法归因到协议。

灰度开关应支持按 host、接口、网络类型、客户端版本和应用版本关闭。回滚只改变传输选择，不能丢失正在执行写操作的幂等状态。

## 工程检查清单

- 是否记录请求最终协商的协议，而不是只记录客户端库名称。
- HTTP/2 连接复用是否被无意义的多客户端或域名分片削弱。
- 是否把服务端 stream 上限、流量控制和 TCP 队头等待纳入分析。
- OkHttp 方案是否已移除不可用的 HTTP/2 Server Push 假设。
- HTTP/3 是否保留基于 TCP 的协议协商路径。
- QUIC 迁移是否覆盖 Wi-Fi/蜂窝切换、VPN、代理、计费网络和服务端不支持场景。
- 0-RTT 是否只允许可重放操作，指标是否避免把 QUIC 等同于 0-RTT。
- HttpEngine 是否复用，缓存与磁盘目录是否显式配置。
- Android 17 应用代理是否验证系统代理覆盖与最终回退。
- 基础 API 37 指标是否避免引用 37.1 才提供的详细时序。
- gRPC channel 与 stub 是否复用，token 是否按调用安全更新。
- 每个 gRPC 方法是否有合理 deadline，取消是否传播。
- gRPC retry 是否由 Service Config 与业务幂等语义共同限制。
- 流式 RPC 是否具备流量控制、断线恢复、前后台和电量策略。
- 灰度是否保持服务端业务、缓存和接口语义稳定。

## 源码与规范依据

- [AOSP `android-17.0.0_r1` HttpEngine](https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/HttpEngine.java)
- [AOSP `android-17.0.0_r1` ConnectionMigrationOptions](https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/ConnectionMigrationOptions.java)
- [AOSP `android-17.0.0_r1` UrlResponseInfo](https://android.googlesource.com/platform/external/cronet/+/android-17.0.0_r1/android/java/src/android/net/http/UrlResponseInfo.java)
- [Android HttpEngine.Builder API](https://developer.android.com/reference/android/net/http/HttpEngine.Builder)
- [Android Cronet 功能](https://developer.android.com/develop/connectivity/cronet)
- [Android Cronet 与其他库集成](https://developer.android.com/develop/connectivity/cronet/integration)
- [OkHttp 5.3.0 Http2Connection](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/Http2Connection.kt)
- [OkHttp 5.3.0 PushObserver](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/http2/PushObserver.kt)
- [RFC 9113：HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html)
- [RFC 9000：QUIC](https://www.rfc-editor.org/rfc/rfc9000.html)
- [RFC 9001：Using TLS to Secure QUIC](https://www.rfc-editor.org/rfc/rfc9001.html)
- [RFC 9114：HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html)
- [gRPC Android Java 指南](https://grpc.io/docs/platforms/android/java/basics/)
- [gRPC Deadline](https://grpc.io/docs/guides/deadlines/)
- [gRPC Retry](https://grpc.io/docs/guides/retry/)
- [gRPC Flow Control](https://grpc.io/docs/guides/flow-control/)
- [gRPC Keepalive](https://grpc.io/docs/guides/keepalive/)
- [gRPC 性能建议](https://grpc.io/docs/guides/performance/)
