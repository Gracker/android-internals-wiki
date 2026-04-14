---
title: "Android 网络安全与 TLS 性能优化"
chapter: "12.4"
section: "12.4"
status: ready-for-review
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/reference/android/net/ssl/HPKE"
  - type: official
    path: "https://developer.android.com/training/articles/security-gms-provider"
tags: [network-security, tls, ech, hpke, certificate-transparency, cleartext, performance]
related_chapters: ["12.2", "12.3", "1.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "官方文档+AOSP结构"
gap_score: 14
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: "needs-rework"
task2b_state: pending
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-14"
task6_result: "needs-rework"
---

# 12.4 Android 网络安全与 TLS 性能优化

一次 API 请求只有几 KB，首包却要多等上百毫秒，瓶颈往往不在业务代码，而在连接建立阶段的 TLS 握手。Android 近几代把 TLS 1.3、Certificate Transparency、Encrypted Client Hello、HPKE 这些安全机制逐步推到默认路径里，网络延迟和安全策略也越来越耦合。

这一节关注两个问题：Android 平台上的安全机制会怎样影响网络性能，我们又该怎样在安全和连接成本之间做判断。

<!-- outline-start -->
## 本节导读
- 🔹 TLS 握手与连接延迟：梳理 TLS 1.2、TLS 1.3、0-RTT 与 Session Resumption 对连接时延的影响。
- 🔹 ECH、CT 与 Cleartext 迁移：说明 Android 17 相关安全默认值带来的延迟、兼容性与迁移成本。
- 🔹 HPKE SPI：交代 Android 17 引入的 HPKE 能力、适用场景与性能边界。
- 🔹 优化实践：从连接池、DNS、证书链和重定向配置出发，整理可执行的优化动作。
- 🔹 版本演进与交叉引用：把网络安全策略放回 Android 版本演进和相关章节的上下文里。
<!-- outline-end -->

## TLS 握手与连接延迟

TLS 握手是网络请求延迟中最容易被忽视的一环。对于一个小数据量的 API 请求，TLS 握手耗时可能占到整个请求延迟的 30%-50%，尤其是在移动网络环境下。

### TLS 1.2 vs TLS 1.3：握手次数的质变

TLS 1.2 的完整握手需要 2 个 RTT（Round-Trip Time）。客户端先发 ClientHello，服务器回 ServerHello + Certificate + ServerHelloDone，客户端再发 ClientKeyExchange + ChangeCipherSpec + Finished，服务器最后回 ChangeCipherSpec + Finished。在移动网络下，一个 RTT 通常在 50-200ms（4G 网络），完整的 TLS 1.2 握手会额外增加 100-400ms 延迟。

TLS 1.3 把这个流程压缩到了 1-RTT。核心变化在于密钥交换机制：客户端在第一次握手时就带上 KeyShare，服务器可以在第一次回复时就推导出会话密钥并发送加密数据。相比 TLS 1.2，连接建立时间减少约 50%。

Google 在 Android 10（API 29）上默认启用 TLS 1.3 后报告，相比 TLS 1.2 有最高 40% 的速度提升。[已验证: 官方文档, developer.android.com/about/versions/10/security]

TLS 1.3 还引入了 0-RTT（Zero Round-Trip Time）恢复模式。当客户端之前连接过某个服务器并获得了 session ticket 后，下次连接时可以直接在 ClientHello 中携带加密的 "early data"，实现零延迟恢复。对于频繁请求同一 API 的场景，TLS 开销可以降到接近零。

0-RTT 有一个安全代价：early data 不具备前向安全性（forward secrecy），而且可以被重放。因此只适用于幂等请求（如 GET），不能用于有副作用的操作（如 POST /transfer）。OkHttp 从 4.x 版本开始支持 TLS 1.3，但默认不启用 0-RTT，需要开发者手动配置。

### Session Resumption：被低估的优化手段

Session Resumption 分两种机制：Session ID 和 Session Ticket。

Session ID 方式下，服务器在握手时分配一个 session ID，客户端下次连接时携带这个 ID，服务器从缓存中找到之前的会话状态，跳过完整的密钥协商过程。TLS 1.2 的 session resumption 需要 1-RTT，TLS 1.3 的 PSK（Pre-Shared Key）恢复也是 1-RTT，但 TLS 1.3 的 0-RTT 可以做到 0-RTT。

在实际应用中，session resumption 是降低 TLS 开销最有效的手段之一。一个良好的实践是确保连接池（ConnectionPool）的 keep-alive 时间足够长（OkHttp 默认 5 分钟），这样 TCP 连接保持期间内复用连接完全不需要 TLS 握手。只有连接断开后重新建立时，session resumption 才发挥作用。

[图：Perfetto 中 TLS 握手耗时的观测示意，标出 DNS、TCP connect、TLS 握手与首包返回的时间段]

### Android 各版本的 TLS 默认行为

Android 平台的 TLS 行为随着版本演进持续收紧：

| 版本 | TLS 默认行为 |
|------|------------|
| Android 7.0 (API 24) | TLS 1.1/1.2 默认启用，但部分设备不支持 |
| Android 8.1 (API 27) | TLS 1.2 连接验证更严格 |
| Android 10 (API 29) | TLS 1.3 默认启用，通过 Conscrypt provider |
| Android 11 (API 30) | TLS 1.3 完善支持 |
| Android 17 (API 37) | ECH 平台级支持、CT 默认启用、cleartext 阻断 |

[已验证: 官方文档, developer.android.com/training/articles/security-gms-provider]

Android 的 TLS 实现由 Conscrypt 安全提供者（基于 BoringSSL）负责。这个提供者可以通过 Google Play Services 更新，即使设备没有升级系统版本，也可能获得 TLS 安全补丁。

## Encrypted Client Hello (ECH) 的性能影响

TLS 握手的一个长期隐私问题是：ClientHello 中的 SNI（Server Name Indication）字段是明文传输的。即使 TLS 加密了后续所有通信，网络中间人（ISP、企业网关）仍然可以知道你在访问哪个域名。

Encrypted Client Hello（ECH，RFC 9180 相关扩展）的目的是加密整个 ClientHello，包括 SNI。

### Android 17 的 ECH 支持

Android 17（API 37）在平台级别引入了 ECH 支持，默认以 "opportunistic" 模式启用。当 DNS 查询返回 ECH 配置（HTTPS/SVCB 记录类型）时，平台会自动尝试使用 ECH。如果服务器不支持 ECH，连接会降级到普通 TLS，不会导致连接失败。

ECH 的工作流程依赖 DNS-over-HTTPS（DoH）或 DNS-over-TLS（DoT）：客户端先通过加密 DNS 查询获取目标域名的 ECH 公钥配置，然后用这个公钥加密 ClientHello 中的 SNI 和其他敏感信息。

### 性能开销

ECH 的额外开销来自两部分：

1. **DNS 查询增加**：客户端需要先获取 ECH 配置。如果使用 DoH，这是一次额外的 HTTPS 请求。不过这个查询通常会被 DNS 缓存命中，实际只在首次连接时有额外延迟。

2. **ClientHello 加密**：ECH 使用 HPKE（Hybrid Public Key Encryption）对 ClientHello 进行加密，加密操作本身的计算开销很小。Chrome 的 ECH 试用数据显示对通用指标的影响"可以忽略"。

在现代 Android 设备上，加密操作通常由硬件加速器（ARM CE 指令集）处理，TLS 相关的 CPU 开销在整体请求延迟中占比很小。真正影响延迟的始终是 RTT，而不是计算。

[已验证: 官方文档, developer.android.com/about/versions/17/behavior-changes-17]
[待验证: ECH 对 OkHttp / Cronet 的透明性，预计 Android 17 平台级实现对上层 HTTP 客户端透明]

## Certificate Transparency 的开销

Certificate Transparency（CT，RFC 6962）是一个证书审计机制，要求证书颁发机构（CA）将所有签发的证书提交到公开的 CT 日志中。客户端在 TLS 握手时验证服务器证书中是否包含 CT 日志的签名时间戳（SCT，Signed Certificate Timestamp），以此确保证书没有被秘密签发。

### Android 17 默认启用

在 Android 16 及之前，CT 默认不启用，需要 App 通过 Network Security Configuration 显式 opt-in。Android 17 将 CT 默认启用，targetSdkVersion >= 37 的 App 的所有 TLS 连接都会自动验证 SCT。

SCT 可以通过三种方式交付：

1. **嵌入证书**：作为 X.509v3 扩展直接嵌入证书中（最常见）
2. **OCSP Stapling**：服务器在 TLS 握手时附带 OCSP 响应，其中包含 SCT
3. **TLS 扩展**：作为 `signed_certificate_timestamp` TLS 扩展发送

### 性能影响

CT 验证的核心开销是对 SCT 的签名验证。每个 SCT 需要一次签名验证操作，一张证书通常包含 2-3 个 SCT。在现代 ARM 处理器上，一次 ECDSA 签名验证耗时在微秒级别，远低于一个网络 RTT。所以 CT 验证本身对 TLS 握手延迟的影响几乎可以忽略。

CT 实际可能带来影响的场景是：服务器配置不当，没有提供足够的 SCT（Android 要求至少 2 个有效的 SCT），导致连接失败。这不是性能问题，而是兼容性问题。

[已验证: 官方文档, developer.android.com/about/versions/17/behavior-changes-17]
[待验证: Android 17 CT 验证的具体 SCT 数量要求]

## Cleartext Traffic 弃用的迁移与性能

### 弃用时间线

Android 对明文流量（HTTP）的限制是一个渐进过程：

- **Android 6.0 (API 23)**：引入 `usesCleartextTraffic` 标志和 `StrictMode` 检测
- **Android 7.0 (API 24)**：引入 Network Security Configuration，提供更细粒度的控制
- **Android 9 (API 28)**：targetSdkVersion >= 28 的 App 默认禁止明文流量
- **Android 17 (API 37)**：正式弃用 `usesCleartextTraffic` 属性，即使设为 `true` 也不再生效

[已验证: 官方文档, developer.android.com/training/articles/security-config]

### 迁移中的延迟变化

从 HTTP 迁移到 HTTPS 的主要延迟影响来自 TLS 握手。但这个影响是一次性的，连接建立完成后，TLS 对数据传输的吞吐量影响很小。Google 的研究表明，当数据量超过 500KB 时，TLS 的能量开销相比传输 I/O 开销可以忽略。

迁移中真正需要关注的是：

1. **混合内容（Mixed Content）**：如果 App 的部分请求走 HTTPS，部分走 HTTP，浏览器/WebView 会阻塞或警告混合内容。这不会增加延迟，但会导致请求失败，用户感知为"加载变慢"。

2. **HTTP→HTTPS 重定向**：如果服务端只是做了 301/302 重定向，客户端先发 HTTP 请求再被重定向到 HTTPS，等于额外增加了 1-2 个 RTT 的延迟。正确的做法是在客户端直接使用 HTTPS URL。

3. **证书链过长**：如果服务器配置了过长的证书链（超过 4-5 层），TLS 握手时传输的证书数据量增加，在高延迟网络下会显著影响握手时间。最佳实践是服务器只发送必要的中间证书。

### Network Security Configuration 的性能配置

Network Security Configuration 是 Android 推荐的网络安全管理方式（取代 `usesCleartextTraffic`）。从性能角度，有几个和性能直接相关的配置：

```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
    <!-- 全局禁止明文 -->
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
    
    <!-- 调试模式允许 localhost 明文（仅 debuggable=true 时生效） -->
    <debug-overrides>
        <trust-anchors>
            <certificates src="user" />
        </trust-anchors>
    </debug-overrides>
</network-security-config>
```

`debug-overrides` 只在 App 处于 debuggable 模式时生效，不会影响生产环境的性能和安全。

[已验证: 官方文档, developer.android.com/training/articles/security-config]

## HPKE 混合加密 SPI

Android 17 引入了 Hybrid Public Key Encryption（HPKE，RFC 9180）的公开 Service Provider Interface（SPI）。HPKE 是一种标准的混合加密方案，结合了公钥加密和对称加密（AEAD），为端到端加密通信提供了一套标准化的 API。

### 为什么要关注

在 HPKE 之前，如果开发者需要实现端到端加密，通常要自己组合密钥交换（ECDH）和对称加密（AES-GCM）方案。不同的实现方式安全性和性能差异很大。HPKE 通过标准化这个流程，让开发者不需要自己设计加密方案，同时保证了性能和安全性。

### 适用场景

HPKE 适合以下需要公钥加密的场景：

- **端到端加密消息**：使用接收者的公钥加密消息内容
- **安全配置分发**：设备注册时加密敏感配置数据
- **跨进程安全通信**：App 内部不同组件间的加密数据传递

Android 17 的 HPKE 实现目前只支持 base mode（最基本的加密解密模式），不支持 PSK 或 auth mode。`HpkeSpi` 作为 JCA（Java Cryptography Architecture）的一部分，允许第三方安全提供者提供自己的 HPKE 实现。

[已验证: 官方文档, developer.android.com/reference/android/net/ssl/HPKE]
[待验证: Android 17 HPKE 的具体性能基准数据，目前 Beta 阶段尚无公开 benchmark]

## 网络安全性能优化最佳实践

把上面各个安全机制的性能影响汇总后，我们得出以下实践建议。这些不是理论推导，而是基于 Android 平台 TLS 实现的实际行为得出的。

### 连接池与 TLS 连接复用

这是降低 TLS 开销最直接有效的手段。OkHttp 的 `ConnectionPool` 默认保持 5 个空闲连接 5 分钟。在此期间，TCP + TLS 连接完全复用，没有任何握手开销。

需要关注的配置：

```java
// OkHttp ConnectionPool 配置
ConnectionPool pool = new ConnectionPool(
    5,      // maxIdleConnections: 空闲连接上限
    5,      // keepAliveDuration: 保持时间（分钟）
    TimeUnit.MINUTES
);
OkHttpClient client = new OkHttpClient.Builder()
    .connectionPool(pool)
    .build();
```

调整 `maxIdleConnections` 时需要注意：过多的空闲连接会占用服务器资源（每个连接对应服务器端的一个 socket + 线程），对于高并发 App（如即时通讯），适当增大到 10-15 可以减少 TLS 重握手频率。

### DNS-over-HTTPS / DNS-over-TLS 的权衡

Android 9（API 28）引入了 Private DNS（DoT）设置，Android 11 扩展支持了 DoH。加密 DNS 查询增加了 DNS 解析延迟（首次），但可以防止 DNS 劫持和 SNI 泄露。

从性能角度：

- **首次查询**：DoH 增加约 1 个 RTT 的延迟（建立 TLS 连接 + HTTPS 请求）
- **后续查询**：DoH 连接复用后，延迟接近传统 DNS
- **缓存**：Android 的 DNS 缓存（`InetAddress` 级别）会缓存解析结果，有效 TTL 内不会重新查询

如果 App 大量请求使用不同域名（如 CDN 分发、多服务 API），DNS 查询频率较高，可以考虑在 App 层面做 DNS 预解析（`Dns` 接口自定义实现），在后台线程提前解析可能用到的域名。

### 安全配置的性能影响总结

| 机制 | 性能影响 | 缓解手段 |
|------|---------|---------|
| TLS 1.3 完整握手 | 1-RTT | 连接池复用 |
| TLS 1.3 0-RTT | 0-RTT（恢复连接） | 仅用于幂等请求 |
| ECH | 额外 DNS 查询（首次） | DNS 缓存 |
| Certificate Transparency | SCT 签名验证（微秒级） | 无需特别处理 |
| Cleartext→HTTPS | 初始 TLS 握手开销 | 避免 HTTP→HTTPS 重定向 |
| HPKE | 视具体场景，一般微秒级 | 适用端到端加密 |

## 与其他章节的关联

- **§12.2 网络性能优化**：本章的安全机制是网络请求延迟的一部分，与连接池、缓存等优化手段配合使用
- **§12.3 网络性能深入**：连接池、TLS、DNS 是网络请求的底层基础设施，理解这些有助于分析整体网络性能
- **§1.6 版本演进**：TLS 和网络安全策略的版本演进是 Android 安全生态演进的重要组成部分

## 参考资料

- [Android 17 Behavior Changes](https://developer.android.com/about/versions/17/behavior-changes-17)，官方行为变更文档
- [Network Security Configuration](https://developer.android.com/training/articles/security-config)，网络安全配置指南
- [HPKE RFC 9180](https://www.rfc-editor.org/rfc/rfc9180)，HPKE 标准规范
- [TLS 1.3 RFC 8446](https://www.rfc-editor.org/rfc/rfc8446)，TLS 1.3 标准规范
- [Certificate Transparency RFC 6962](https://www.rfc-editor.org/rfc/rfc6962)，CT 标准规范
- [Conscrypt Security Provider](https://developer.android.com/training/articles/security-gms-provider)，Android TLS 实现说明
