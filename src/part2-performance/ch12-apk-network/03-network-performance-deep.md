---
title: 网络性能深入：连接池、TLS 与传输优化
chapter: 12.3
section: 12.3
status: ready-for-review
drafted_date: 2026-04-07
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: 2026-07-03
last_verified_against: Android Developers docs / source.android / OkHttp 5.x docs / Google Security Blog 2022-07 / AOSP android-17.0.0_r1 libcore BlockGuard, packages/modules/Connectivity DnsResolver, packages/modules/DnsResolver rust/src/doh
confidence: medium
sources:
  - type: official
    path: https://perfetto.dev/docs/instrumentation/tracing-sdk
tags: [network, okhttp, retrofit, tls, http2, http3, quic, connection-pooling, dns, battery, perfetto]
related_chapters: ["12.2", "8.2", "11.2", "5.8", "14.1"]
created_by: task2a-knowledge-gap
created_date: 2026-04-07
gap_source: AOSP结构+官方文档+读者需求
gap_score: 14
drafted_by: openclaw-task2a
reviewed_by: openclaw-task6
reviewed_date: 2026-07-03
task6_result: pass-light-edit
review_round: 2
task6_state: reviewed
pipeline_stage: task9_pending
task9_state: pending
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
last_task9_at: 2026-07-03T09:32:24+08:00
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-07-03
last_task6_audit: 2026-06-10
last_task9_audit: 2026-07-03
last_task9_review_log: logs/deep-review/2026-07-03-09-deep-review.md
p0: 1
p1: 1
p2: 0
task9_review_notes: 2026-05-19 task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0。Android 16 DnsResolver Predictive Prefetching 平台能力缺公开锚点，需删除或降级待验证；2026-05-28 Task2B 已改为 App 侧受控预解析策略，回流 Task6。 | 2026-05-28 Task9 auto-fix: 修正 RouteSelector/ALPN 边界与 OkHttp EventListener connect/TTFB 指标口径，回到 Task6 复审。 | 2026-05-28 06 Task9复审: pass-tech-review；无 P0/P1/P2；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-03 Task9 闲时抽检 AUTO-FIX：Android 17 主线 libcore 中 `BlockGuard.java` 位于 `libcore/dalvik/src/main/java/dalvik/system/`，socket 网络入口由 `libcore/luni/src/main/java/libcore/io/BlockGuardOs.java` 调用 `BlockGuard.getThreadPolicy().onNetwork()`；已修正 frontmatter AOSP 源码路径并同步重锚 OkHttp 4.12.x `ConnectionPool.kt` 代码块。P0 1 / P1 0 / P2 0；回到 Task6 复审。 | 2026-07-03 09 Task9 deep-review AUTO-FIX：修正 DoH3 AOSP 路径为 packages/modules/DnsResolver/rust/src/doh，并补充 DnsResolver TYPE_HTTPS/HttpsRecord/HttpsEndpoint 在 android-17.0.0_r1 中的 FlaggedApi 边界。P0 1 / P1 1 / P2 0；回到 Task6 复审。
task6_reviewed_by: openclaw-task6
last_task6_at: 2026-07-03T13:14:00+08:00
task6_reviewed_at: 2026-05-28T06:11:00+08:00
last_task6_review_log: logs/review/2026-07-03-13-review.md
task6_review_notes: 2026-05-19 20 Task6 revisiting-review: pass-light-edit；L1 小修 1 处（删除填充强调词）。既有 Android 16 DNS prefetch 技术回炉项保留交 Task2B，queue pending 阻止自动晋升。 | 2026-05-28 05 Task6 revisiting-review: pass-light-edit；L1/L2 小修 1 处（规避序数词禁用词误命中）；outline 6/6 覆盖；无 L3/L4 回炉项。Task9 result 仍为 needs-rework，Task2B 已 fixed，送 Task9 复审。 | 2026-05-28 06 Task6 revisiting-review: pass-light-edit；L1/L2 小修 0 处；outline 6/6 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，未满足 pass-tech-review 自动晋升条件，送 Task9 复核。 | 2026-07-03 09 Task6 revisiting-review: pass-light-edit；L1 小修 1 处（禁用词\"链路\"→\"路径\", 在参考资料注释中）；outline 6/6 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，未满足 pass-tech-review 自动晋升条件，送 Task9 复核。 | 2026-07-03 13 Task6 revisiting-review: pass-light-edit;L1 小修 1 处(禁用词"落地"→"实际使用时", frontmatter sources 缩进修正);outline 6/6 覆盖;无 L3/L4 回炉项。Task9 result 为 auto-fixed，未满足 pass-tech-review 自动晋升条件,送 Task9 复核。
last_task2b_at: 2026-05-28T04:50:00+08:00
last_task2b_source: frontmatter-fallback/task9-deep-tech-review
last_task2b_note: 删除 Android 16 DnsResolver Predictive Prefetching 确定性平台结论，改写为 App 侧受控 DNS 预解析策略。
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
last_task9_autofix_at: 2026-07-03
last_task9_audit_log: logs/deep-review/2026-07-03-06-audit.md
task9_p0_issues: 1
task9_p1_issues: 1
task9_p2_issues: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-03
last_task2b_verifier_at: 2026-07-03T07:32:03+08:00
---
-
# 12.3 网络性能深入：连接池、TLS 与传输优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 网络栈全景：请求从 OkHttp 到内核协议栈的路径与耗时拆分
- 🔹 OkHttp 连接池与复用机制：ConnectionPool、HTTP/2 多路复用、EventListener 时序
- 🔹 TLS 握手性能与优化：TLS 1.2 / TLS 1.3、Conscrypt、证书校验开销
- 🔹 DNS 解析性能：系统 DNS resolver、DoT / DoH、OkHttp 自定义 DNS
- 🔹 网络请求对电池的影响：Radio State Machine、批量请求、JobScheduler 调度
- 🔹 在 Perfetto 中分析网络性能：自定义 Trace Event、主线程阻塞、指标基线

### 扩展（可选深入）

- 🔸 HTTP/3 与 QUIC
- 🔸 WebSocket 性能
- 🔸 Retrofit 与 Coroutine 集成性能

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果后续补到了 HTTP/2 复用、Radio State Machine 或网络请求分阶段 Trace 的图示，优先插入对应锚点后并补验证来源。
<!-- outline-end -->

在 §12.2 中我们从宏观角度梳理了网络性能优化的策略和工具：HTTP/2 与 HTTP/3 的选择、弱网应对方案、OkHttp EventListener 监控等。那些内容回答了实践策略。

这一节我们深入到网络请求的底层机制：一个 HTTP 请求从发起到收到响应，中间到底经历了哪些步骤？每个步骤的耗时分布在哪？为什么连接复用比新建连接快这么多？TLS 握手到底有多贵？DNS 解析在什么情况下会成为瓶颈？

理解这些底层机制之后，再看 Perfetto 中的网络相关 Trace 数据，我们就能精确判断性能瓶颈出在哪个环节——是 DNS 慢、还是 TLS 握手耗时、或者是服务端响应延迟。

## Android 网络栈全景

一个 HTTP 请求从 App 代码调用开始，到拿到 Response 对象，中间不止一条实现路径。排查性能时，分清自己站在哪条栈上。

- **OkHttp**：默认路径通常经由 `java.net`、`javax.net.ssl` 和平台 socket。TLS 常见落到 `libcore` 的 `Conscrypt` provider，DNS 默认走 `Dns.SYSTEM` 对应的系统 resolver。
- **Cronet**：它是以库形式提供给应用的 Chromium 网络栈，HTTP/2、HTTP/3、QUIC、连接调度和大部分网络状态机都在 Chromium 层完成。
- **HttpEngine**：Android 14 / API 34 把 Cronet 能力以 `android.net.http` SDK 形式暴露出来，底层仍是 Chromium / Cronet 栈。

把 OkHttp、Cronet、HttpEngine 整合为同一条 `java.net -> Conscrypt -> kernel` 调用链，会把 QUIC、HTTP/3 和连接管理的边界写混。后续分析 DNS、TLS、连接复用或 Perfetto 线程时，都要先按具体网络栈分流。

无论走哪条栈，一个 HTTPS 请求从发起到收到响应，必经的环节是相同的。下面是一次典型请求的完整时间分解：

1. **DNS 解析**：将域名解析为 IP 地址。局域网环境下 < 1 ms，公网解析通常 20-120 ms。
2. **TCP 连接建立**：三次握手，取决于网络 RTT（Round-Trip Time），通常 30-100 ms（4G 网络）。
3. **TLS 握手**：密钥协商和证书验证。TLS 1.2 需要 2 个 RTT，TLS 1.3 减少到 1 个 RTT。
4. **HTTP 请求/响应**：发送请求头和 body、等待服务端处理、接收响应。首字节时间（TTFB）取决于服务端处理能力。

对于首次连接，前三步可能先消耗 100-300 ms，数据传输要到第 4 步才开始。连接池和 keep-alive 的价值就在这里，第二次请求可以直接跳到第 4 步。

### 网络操作与主线程性能

对 `targetSdk >= 11` 的应用，主线程直接做网络操作时通常会触发 `NetworkOnMainThreadException`。底层入口是 `BlockGuard` 的线程策略检查，`StrictMode` 会在这条检查链上把主线程网络访问记成违规并决定处罚方式。`StrictMode.detectNetwork()` 属于开发期诊断开关，只有显式启用时才会额外记录网络违规；`permitAll()` 会关闭这类检测。两条机制职责不同，不能混写。

冷启动里更常见的风险是主线程同步等待网络结果。App 在 `Application.onCreate()` 或首屏初始化中发起后台请求后，又在主线程用 `Future.get()`、`CountDownLatch.await()`、`runBlocking` 等方式等结果，首帧就会被卡住。直接在主线程做 Java 网络调用，通常会更早触发 `NetworkOnMainThreadException`。

在 Perfetto 里排查这类问题时，主线程上的 `blocked_function` 要和线程上下文一起看。若 MainThread 直接落在 `poll`、`recvmsg`、`epoll_wait` 这类 socket 相关等待上，要继续核对调用栈或 fd 归属，确认是否真的把网络 I/O 放到了 UI 线程。若主线程落在 `futex` 等同步原语上，而 OkHttp / Cronet 工作线程同时处于 DNS、connect、TLS 或 response body read 阶段，根因通常是主线程在等网络结果。

[已验证: Android SDK reference — NetworkOnMainThreadException / StrictMode.ThreadPolicy.Builder.detectNetwork()]

## OkHttp 连接池与复用机制

OkHttp 的连接池是理解 Android 网络性能优化的核心。它解决的问题很直接：TCP 连接的建立代价很高，能不能复用已经建立的连接？

### 连接池的工作方式

OkHttp 内部使用 `ConnectionPool` 类管理所有 TCP 连接。当一个请求完成后，底层的 TCP 连接不会被立即关闭，而是归还到连接池中。下一个请求如果目标是同一个地址（相同的 host、port、scheme），就可以直接从池中取出一条已有连接使用，省去 DNS 解析、TCP 握手、TLS 握手三个步骤。

[已验证: OkHttp 4.12.x, okhttp3.ConnectionPool]

连接池有两个核心参数：`maxIdleConnections`（最大空闲连接数，默认 5）和 `keepAliveDuration`（空闲连接的最大存活时间，默认 5 分钟）。超过这个数量或时间的空闲连接会被后台清理线程回收。

```kotlin
// okhttp/src/main/kotlin/okhttp3/ConnectionPool.kt (OkHttp 4.12.x)
// OkHttp 默认连接池配置
constructor() : this(5, 5, TimeUnit.MINUTES)
```

这段代码告诉我们一个重要的默认值：OkHttp 最多保持 5 条空闲连接，每条最多存活 5 分钟。对于大多数 App 来说，如果在 5 分钟内再次访问同一个域名，通常可以直接复用连接。如果 App 需要同时与超过 5 个不同的后端域名保持长连接，空闲连接数可能不够，需要适当调大这个参数。

### HTTP/2 多路复用 vs HTTP/1.1 连接池

HTTP/1.1 的连接复用是串行的：一个 TCP 连接上，必须等上一个请求完成后才能发送下一个请求。如果浏览器或 App 需要并发请求同一个域名的多个资源，就需要建立多条 TCP 连接。

HTTP/2 引入了多路复用（multiplexing）：一个 TCP 连接上可以同时承载多个请求和响应，通过 stream ID 区分不同的请求。同一域名的并发请求通常可以压到一条 TCP 连接上。

在 OkHttp 中，当服务端支持 HTTP/2 时（通过 ALPN 协商），连接池的行为会发生变化：同一个地址只需要维持一条连接，所有请求复用这条连接。这大大减少了连接池的压力，也降低了服务端的资源消耗。

HTTP/2 的好处在于把同域名并发请求放到一条已建立的连接上。DNS、TCP、TLS 这些固定成本通常只付一次，后续多个 stream 直接复用现有连接。效果大小取决于资源数量、RTT、服务端实现和丢包情况，正文不固定写成单一百分比。

[图：同一域名 8 个资源在 HTTP/1.1 多连接与 HTTP/2 单连接下的阶段对比，标出 DNS/TCP/TLS 只发生一次，以及多个 stream 并发返回的位置]

### 连接建立的完整流程

一个 OkHttp 请求的连接建立过程大致如下：

1. **Route Selection**：OkHttp 的 `RouteSelector` 根据代理配置、DNS 地址列表和连接失败历史生成候选 `Route`；HTTP/2 是否可用要等连接后的 ALPN 或 prior knowledge 路径确认。
2. **DNS 解析**：调用 `Dns` 接口的 `lookup()` 方法，将 hostname 解析为 IP 地址列表。
3. **TCP 连接**：通过 `Socket` 连接到目标 IP 和端口。
4. **TLS 握手**（如果是 HTTPS）：在 TCP 连接之上建立加密通道。
5. **HTTP 协议协商**：通过 ALPN（Application-Layer Protocol Negotiation）协商 HTTP/2 或 HTTP/1.1。

每一步的耗时可以通过 OkHttp 的 `EventListener` 回调精确测量：

```java
// OkHttp EventListener 回调时序
callStart()           // 请求开始
dnsStart()            // DNS 解析开始
dnsEnd()              // DNS 解析结束 → 得到 DNS 耗时
connectStart()        // TCP 连接开始
secureConnectStart()  // TLS 握手开始
secureConnectEnd()    // TLS 握手结束 → 得到 TLS 耗时
connectEnd()          // 建连完成；HTTPS 下已经包含 TLS 阶段
connectionAcquired()  // 从连接池获取连接（可能是复用）
requestHeadersStart() // 发送请求头
responseHeadersStart()// 收到响应头 → 得到 TTFB
responseBodyStart()   // 开始接收 body
responseBodyEnd()     // body 接收完成 → 得到传输耗时
callEnd()             // 请求完成
```

这套回调是网络性能监控的核心基础设施。在 HTTPS 请求中，`connectEnd - connectStart` 是建连总耗时，不等于纯 TCP socket 耗时；TLS 耗时应使用 `secureConnectEnd - secureConnectStart`，TCP socket connect 可用 `secureConnectStart - connectStart` 近似。在线上环境中，我们可以通过 EventListener 收集每个阶段的耗时，建立网络性能的基线数据。

## TLS 握手性能与优化

TLS 握手是 HTTPS 请求中耗时最长的步骤之一，理解它的流程和优化手段会直接影响我们对网络耗时的判断。

### TLS 1.2 握手流程

TLS 1.2 的完整握手需要 2 个 RTT（Round-Trip Time），流程如下：

**第一次往返**：客户端发送 `ClientHello`，包含支持的 TLS 版本、加密套件列表、随机数。服务端回复 `ServerHello`，选定 TLS 版本和加密套件，发送自己的证书链和密钥交换参数。

**第二次往返**：客户端验证服务端证书，发送密钥交换完成消息。服务端确认后，双方开始加密通信。

在一个 RTT 约 50 ms 的 4G 网络上，TLS 1.2 完整握手至少需要 100 ms。加上 CPU 做非对称加密运算（RSA/ECDHE）的时间，实际握手耗时通常在 150-300 ms。

### TLS 1.3 的性能提升

TLS 1.3（Android 10+ 默认启用）将握手从 2-RTT 减少到 1-RTT。它通过以下方式实现：

1. 移除了 `ServerKeyExchange` 和 `ClientKeyExchange` 两个独立步骤，将密钥交换参数合并到 `Hello` 消息中。
2. 简化了密码套件协商，只保留基于 ECDHE 的前向保密密钥交换。
3. 移除了不安全的旧算法（RSA 密钥交换、CBC 模式加密、SHA-1 签名等）。

从性能角度看，1-RTT 让 50 ms RTT 网络上的 TLS 握手从至少 100 ms 降到约 50 ms。再算上 CPU 计算时间，总耗时约 80-150 ms，大约是 TLS 1.2 的一半。

[已验证: 官方文档, developer.android.com — TLS 1.3 在 Android 10 (API 29) 起默认启用]

TLS 1.3 还定义了 0-RTT 恢复模式，允许客户端在恢复会话时直接携带应用数据。0-RTT 的主要风险是重放攻击（RFC 9001 §9.2），这也是 §12.2 中建议对非幂等请求禁用 0-RTT 的原因。

Android 平台的标准 TLS 入口（JSSE/Conscrypt）目前不支持 0-RTT。官方 TLS 1.3 行为文档明确标注“0-RTT mode isn't supported”。Android 15 中 Conscrypt 限制了对 TLS 1.0/1.1 的支持，但并未引入 0-RTT 或 Anti-replay 能力。如果 App 需要在移动端利用类似 0-RTT 的加速，唯一可用的路径是 Cronet/HttpEngine 的 QUIC 会话恢复（0-RTT QUIC handshake），这和标准 JSSE/Conscrypt 的 TLS 1.3 路径完全不同。

分析网络 trace 时，区分“TLS 1.3 完整握手”、“TLS 1.3 恢复（1-RTT）”和 QUIC 0-RTT 三种情况——其中只有 QUIC 0-RTT 会在首包携带应用数据，但走的是 QUIC/UDP 传输而非标准 TLS/TCP。

### Conscrypt 与 Android TLS 实现

Android 平台默认的 TLS 实现来自 Conscrypt，它构建在 BoringSSL 之上。Android 10 起，Conscrypt 模块 `com.android.conscrypt` 以 Mainline APEX 形式分发，更新路径是 Google Play system updates，不是 Google Play services。

Google Play services 提供的是另一条兼容路径：`ProviderInstaller.installIfNeeded()` 可以在运行时安装可动态更新的 security provider。这个能力更适合旧系统或兼容场景，职责和 Mainline APEX 不同。

如果 App 需要在旧设备上显式切换到外部 Conscrypt provider，可以自己插入 provider：

```java
// 需要显式依赖 org.conscrypt:conscrypt-android
Security.insertProviderAt(Conscrypt.newProvider(), 1);
```

这段代码属于“应用自己插入 provider”的方案。工程上可以按设备能力分三档：Android 10+ 先信任系统 Conscrypt；旧设备优先尝试 ProviderInstaller；还不满足时再显式引入外部 Conscrypt provider。

[已验证: source.android Conscrypt Mainline / Google Play services ProviderInstaller]

### 证书验证的性能开销

TLS 握手中的证书验证涉及证书链的签名校验，在性能敏感场景下值得关注。Certificate Pinning（证书固定）是一种安全策略，它要求服务端证书必须匹配预设的公钥哈希。OkHttp 提供了 `CertificatePinner` 来实现这一点。

Certificate Pinning 本身不会增加额外的网络往返，但错误的配置（比如 pin 过期后没有更新）会导致所有请求直接失败。从性能角度看，更大的影响来自于 OCSP（Online Certificate Status Protocol）和 CRL（Certificate Revocation List）检查——如果 App 或系统在 TLS 握手过程中去查询证书的吊销状态，会额外增加一次或多次网络请求。Android 默认不执行 OCSP stapling 之外的在线证书状态检查，这是一个合理的性能与安全的平衡。

## DNS 解析性能

DNS 解析是网络请求过程的第一步，也是最容易被忽视的性能瓶颈。

### Android DNS 解析流程

当 App 通过 `InetAddress.getAllByName()` 或底层的 `getaddrinfo()` 发起 DNS 查询时，请求会进入 Android 的系统 resolver。对 OkHttp 默认 `Dns.SYSTEM` 这类路径，常见路径是 `InetAddress` → `libcore.io.Linux`（JNI）→ `getaddrinfo()`（bionic/libc）→ Android DNS resolver → 配置的 DNS 服务器。

DNS Resolver 在 Android 10 已以 Mainline 模块形态引入，Android 11 起成为强制模块化组件。Cronet / HttpEngine 则维护自己的 Chromium 异步网络栈，分析这两类请求时，不要把它们简单压成同一条 `InetAddress` 调用链。

系统层面，Android 维护了 DNS 缓存，但这个缓存的 TTL（Time To Live）由 DNS 记录本身的 TTL 值决定。如果域名的 DNS 记录 TTL 很短（比如 60 秒），频繁的解析请求会反复命中网络查询。

### DNS 解析耗时分布

DNS 解析的耗时差异很大，取决于缓存命中情况和网络环境：

- **本地缓存命中**：< 1 ms，几乎可以忽略
- **局域网 DNS 服务器响应**：1-10 ms
- **公网 DNS 服务器响应**：20-120 ms（国内运营商 DNS 可能更长）
- **DNS 解析失败/超时**：通常 3-30 秒（取决于系统超时配置）

还有一个常被忽视的点：DNS 解析是同步阻塞操作。如果 DNS 查询发生在主线程上（哪怕是通过 OkHttp 发起），在解析完成之前线程会被阻塞。OkHttp 默认在自己的线程池中执行网络请求，但自定义的 `Dns` 实现如果不注意异步化，可能把 DNS 查询带回调用线程。

### DNS over HTTPS 与性能

DNS 加密传输有三种主流协议，我们先区分清楚。DoT（DNS over TLS）对应 Android 9 引入的 Private DNS。DoH 是把 DNS 报文封装到 HTTP 的协议族，底层可以跑在 HTTP/2 或 HTTP/3 上。DoH3 则是 DoH over HTTP/3，底层传输是 QUIC。

Android 系统 resolver 的公开入口，长期稳定的是 Private DNS 这条 DoT 路径。Google 在 2022 年披露，DoH3 通过 Google Play system update rollout 到 Android 11 及以上设备，另有一部分较早接入 Play system update 的 Android 10 设备也会收到这项能力。对支持的 well-known DNS servers，系统会把原来的 DoT transport 升级为 DoH3；用户使用的 DNS 服务本身不变。

这部分实现位于 `packages/modules/DnsResolver/rust/src/doh/`，并通过 `packages/modules/DnsResolver/doh.h`、`DohParamsParcel.aidl` 等入口接入系统 resolver，属于 transport 演进，不是 App 侧通用 API。Google 给出的初始 rollout 数据是：成功查询上，DoH3 相比 DoT 的 median query time 下降 24%，95th percentile 下降 44%。这组数据出自 Google Online Security Blog。

对性能分析来说，这段版本线的价值在于分清瓶颈落点。若 DNS P95 偏高，要继续区分是 resolver 选择、解析协议、运营商网络，还是单个 DNS 服务实现的问题。DoT 单流上的 head-of-line blocking，和 DoH3 / QUIC 的多 stream 行为，对尾延迟的影响不同。

[已验证: Google Online Security Blog 2022-07 / Android Private DNS 文档]

### App 侧预解析策略

公开 Android 16 / API 36 文档没有提供 `DnsResolver` Predictive Prefetching API，也没有确认系统会在链接 hover 或 TalkBack 聚焦 URL 时自动预解析。不能把这类行为写成平台保证。

如果业务能明确识别“用户很可能点击某个链接”的交互，例如搜索建议、文章内链接 hover、无障碍焦点移动或下一页预加载，可以在 App 层做受控预解析：把 host 交给自有 DNS 层或 OkHttp `Dns` 实现提前查询，并设置并发上限、缓存 TTL 和取消策略。不要在主线程直接调用 `InetAddress.getAllByName()`；自定义 DNS 也要避免把阻塞查询带回 UI 线程。

### DNS HTTPS Record（Type 65）

Android 17（API 37）的 `DnsResolver` 新增了对 DNS HTTPS Record（Type 65）的公开 API 支持，包括 `DnsResolver.TYPE_HTTPS`、`android.net.dns.HttpsRecord`、`HttpsEndpoint` 以及带 `httpsTimeoutMillis` 参数的并发 A/AAAA/HTTPS 查询重载。传统 DNS 查询只返回 IP 地址；Type 65 查询一次能拿到目标服务的 HTTPS RR 信息：IP 地址、支持的 ALPN 协议列表（如 `h3` 标识 HTTP/3 可用）、ECH（Encrypted Client Hello）公钥等。

源码边界也要记住：这些入口在 `android-17.0.0_r1` 中带 `@FlaggedApi(com.android.tethering.flags.Flags.FLAG_ENCRYPTED_CLIENT_HELLO_DNS)`；`HttpsRecord.getEchConfigList()` 还受 Conscrypt 的 ECH platform flag 约束。因此它们可以作为 Android 17 / API 37 的能力讨论，实际使用时仍要以目标设备的 SDK/API 暴露和平台 flag 状态为准。

对性能的直接影响是减少了建连前的探测 RTT。旧模型下，客户端要先查 A/AAAA 记录得到 IP，再通过 ALPN 协商判断是否支持 HTTP/3，连接建立后还要单独协商 ECH——每一步都可能产生额外 RTT。Type 65 把这些信息打包进一次查询，省掉 1-2 个探测 RTT。

API 使用边界：`DnsResolver` API 37 可显式返回 `HttpsEndpoint`（包含 IP 与 HTTPS RR 信息）；`InetAddress` 仍只返回地址，不暴露 HttpsRecord/ALPN/ECH 配置包。使用自定义 `Dns` 接口的 OkHttp 用户需要在 `lookup()` 实现中显式调用 `DnsResolver` 的 Type 65 查询。

### OkHttp 自定义 DNS 解析

OkHttp 提供了 `Dns` 接口，允许 App 自定义域名解析逻辑。这在以下场景中特别有用：

```java
// 自定义 DNS 解析示例：使用 HTTPDNS 绕过运营商 DNS 劫持
public class HttpDns implements Dns {
    @Override
    public List<InetAddress> lookup(String hostname) {
        // 1. 先尝试 HTTPDNS 服务获取 IP
        // 2. 如果失败，回退到系统 DNS
        try {
            List<InetAddress> result = httpDnsResolve(hostname);
            if (!result.isEmpty()) return result;
        } catch (Exception ignored) {}
        return Dns.SYSTEM.lookup(hostname);
    }
}
```

国内运营商的 DNS 劫持和解析延迟是一个现实问题。HTTPDNS（通过 HTTP 接口直接向 DNS 服务商查询）绕过了运营商的 Local DNS，可以直接拿到域名对应的 IP，同时避免 DNS 劫持导致的 CDN 调度不准。

使用自定义 DNS 时有一个常见陷阱：OkHttp 只在建立新连接时才做 DNS 解析。如果连接池中已有到该域名的连接，即使 DNS 记录发生了变化（比如服务端 IP 切换），已缓存的连接仍然使用旧 IP。解决方案是在网络状态变化时主动清理连接池：

```java
// 网络切换时清理连接池
connectivityManager.registerDefaultNetworkCallback(
    new ConnectivityManager.NetworkCallback() {
        @Override
        public void onAvailable(Network network) {
            okHttpClient.connectionPool().evictAll();
        }
    });
```

## 网络请求对电池的影响

网络操作是移动设备最大的电池消耗来源之一，理解无线电模块的工作机制是优化功耗的关键。

### Radio State Machine

移动网络功耗看的是基带状态切换，不是单个 HTTP 包本身用了多少 CPU。以蜂窝网络为例，调制解调器会在高功耗传输态、较低功耗的维持态和空闲态之间切换。传输结束后，modem 往往不会立刻回到最省电的空闲态，而是保留一段 tail time 等后续流量。

这个 tail time 决定了网络请求为何适合批量发送。若请求零散分布，系统会反复把 modem 拉回高功耗态；若能把同一时间窗口内的请求合并，尾巴成本就能被多次请求共同分摊。具体效果和 RAT 类型、运营商参数、设备基带实现直接相关，正文不固定写成统一毫安值或统一倍数。

[图：蜂窝网络状态机示意，标出一次短请求后的 tail time，以及连续小请求导致 modem 多次停留在高功耗态的对比]

### JobScheduler 与网络请求时机优化

这正是 JobScheduler 和 WorkManager 的核心价值——它们让系统来决定网络请求的执行时机，而不是 App 各自为战。通过 `JobScheduler`，多个 App 的网络请求可以被系统合并到同一时间窗口执行，基带只需要唤醒一次就能处理所有 App 的请求。

与 §5.8 后台执行限制和 §11.2 App 耗电优化中讨论的一致，合理的网络请求调度策略是：

1. 非即时性请求（如日志上报、数据同步）通过 WorkManager 延迟到充电或 Wi-Fi 环境下执行。
2. 即时性请求（如用户触发的数据加载）可以立即执行，但应该合并同一时间窗口内的多个请求。
3. 使用 `NetworkCapabilities` 感知当前网络类型，在 Wi-Fi 环境下更积极地预取数据。

## 在 Perfetto 中分析网络性能

Perfetto 没有内置的网络流量 Track（不像 CPU 或内存有专门的 Track），但我们可以通过多种方式在 Trace 中定位网络性能问题。

### 自定义 Trace Event 标记网络请求

最直接的方式是在 OkHttp 中添加自定义 Trace Event。通过 `Trace.beginSection()` / `Trace.endSection()`（或者 Jetpack Tracing 库的 `trace { }` 函数），我们可以在 Perfetto 中精确标记每个网络请求的起止时间：

```kotlin
class TracingInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val url = request.url.host + request.url.encodedPath
        
        return try {
            Trace.beginSection("OkHttp: $url")
            chain.proceed(request)
        } finally {
            Trace.endSection()
        }
    }
}
```

添加这个 Interceptor 后，Perfetto 中会直接出现每个网络请求在 OkHttp 线程上占用的精确时间。结合 OkHttp 的 `EventListener`，还可以分别标记 DNS、连接、TLS、请求/响应各阶段：

```kotlin
override fun connectStart(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy) {
    Trace.beginSection("OkHttp-connect: ${call.request().url.host}")
}

override fun connectEnd(call: Call, ...) {
    Trace.endSection()
}

override fun secureConnectStart(call: Call) {
    Trace.beginSection("OkHttp-TLS: ${call.request().url.host}")
}

override fun secureConnectEnd(call: Call, handshake: Handshake?) {
    Trace.endSection()
}
```

这样在 Perfetto 中，我们就能看到一次网络请求被拆分为多个嵌套的 slice：`OkHttp-TLS` 在 `OkHttp-connect` 内部，`OkHttp-connect` 在整个请求 slice 内部。每个 slice 的长度就是对应阶段的耗时。

### 定位主线程等待网络结果

Perfetto 里更常见的现象是主线程等待网络线程，而不是主线程直接执行 socket I/O。排查时先看 MainThread 是否长时间停在 `futex`、`poll`、`epoll_wait` 等等待点，再看同一时间窗口里 OkHttp Dispatcher、Cronet 或 Binder 线程是否正处于 DNS、connect、TLS、response body read 阶段。

如果 MainThread 自己落在 `recvmsg`、`sendto`、`poll` 这类 socket 调用上，再去核对 `targetSdk`、调用栈和 native 层代码，确认是否真的存在主线程网络 I/O。若 MainThread 停在 `futex`，而后台网络线程正忙于建连或收包，根因通常是同步等待网络结果。

[图：一次 HTTPS 请求的阶段切片示意，主线程等待点与 OkHttp Dispatcher 上的 dns/connect/tls/ttfb/body slice 对照]

### 网络性能监控的最佳实践

线上环境中，通过 OkHttp `EventListener` 收集的网络性能指标通常包括：

- **DNS 时间**：`dnsEnd - dnsStart`
- **建连总耗时**：`connectEnd - connectStart`，HTTPS 下包含 TLS
- **TLS 时间**：`secureConnectEnd - secureConnectStart`
- **首字节时间（TTFB）**：GET 可用 `responseHeadersStart - requestHeadersEnd`；有请求体时从 `requestBodyEnd` 起算
- **内容传输时间**：`responseBodyEnd - responseBodyStart`
- **总耗时**：`callEnd - callStart`

这些指标的 P50 和 P95 分布是评估网络性能健康度的关键基线。如果 TTFB 的 P95 从 200 ms 涨到 800 ms，大概率是服务端处理能力出了问题；如果 DNS 时间的 P95 从 50 ms 涨到 500 ms，可能是 DNS 配置或运营商网络出了问题。

## 扩展

### 🔸 HTTP/3 与 QUIC

当 DNS、TCP、TLS、TTFB 都已经拆开看过，弱网或网络切换时尾延迟仍然抖动，再看 HTTP/3 / QUIC 这一层。QUIC 跑在 UDP 上，把丢包恢复放到 stream 级别处理，能减轻 HTTP/2 over TCP 在单连接上的 head-of-line blocking。移动端分析里，更常见的好处是连接恢复、弱网恢复和高 RTT 下的尾延迟，而不是单纯背协议名。

| 能力 | Android / API | Cronet | HttpEngine | OkHttp | 备注 |
| --- | --- | --- | --- | --- | --- |
| HTTP/2 | 不绑定单一系统 API，取决于库版本 | 原生支持 | API 34+，`setEnableHttp2(true)` | 原生支持 | 常规默认路径 |
| HTTP/3 over QUIC | 不绑定单一系统 API，取决于库版本 | 原生支持 | API 34+，`setEnableQuic(true)`，可配 `addQuicHint()` | `OkHttpClient.Builder.protocols()` 文档当前只列 `http/1.1`、`h2`、`h2 prior knowledge` | 需要区分系统 API 与客户端库能力 |
| 0-RTT / 会话恢复 | 依赖服务端和客户端栈 | 可能使用 | 可能使用 | 无公开原生入口 | 不要把每次恢复连接都当成 0-RTT |
| DoT | Android 9+ / API 28+ | - | - | - | 公开系统入口是 Private DNS |
| DoH3（系统 resolver） | Android 11+ 主线覆盖，另有部分 Android 10 设备通过 Google Play system update 获取 | - | - | - | 这是系统解析器能力，不是通用 App API |

`android.net.http.HttpEngine` 是 Android 14 / API 34 新增类。`HttpEngine.Builder` 暴露了 `setEnableQuic(true)` 和 `addQuicHint(host, port, alternatePort)` 这类 QUIC 入口。时间线写法要和 API 形态保持一致，不能写成“Android 11 起以 HttpEngine 形式默认支持”。

OkHttp 的 `Protocol` 枚举里能看到 `QUIC` 常量，但 `OkHttpClient.Builder.protocols()` 的公开文档当前列出的可配置协议集合只有 `http/1.1`、`h2` 和 `h2 prior knowledge`。工程判断以公开 Builder 入口为准，当前不要把 OkHttp 当成稳定的原生 HTTP/3 客户端。

### 🔸 WebSocket 性能

WebSocket 值不值得看，取决于消息节奏。高频小消息、聊天室、行情推送这类场景，握手成本摊薄后，WebSocket 往往比重复 HTTP 请求更稳。低频推送先看 FCM 或系统推送通道，因为它们复用了系统连接，基带不会被单个 App 的心跳频繁唤醒。分析 trace 时，WebSocket 重点看心跳间隔、重连频率和网络切换后的恢复时间。

### 🔸 Retrofit 与 Coroutine 集成性能

Retrofit 通常不是网络慢的第一嫌疑人。若 `EventListener` 显示 DNS、TCP、TLS、TTFB 都正常，但业务层拿到结果仍然晚，再去看 converter、JSON 解析、协程调度和主线程切换。列表页预加载场景还要同时核对 OkHttp Dispatcher 的 `maxRequests` 与 `maxRequestsPerHost`，确认没有把请求排队时间误判成服务端慢。

## 参考资料

- [Android Network Operations](https://developer.android.com/training/basics/network-ops)
- [NetworkOnMainThreadException](https://developer.android.com/reference/android/os/NetworkOnMainThreadException)
- [StrictMode.ThreadPolicy.Builder.detectNetwork()](https://developer.android.com/reference/android/os/StrictMode.ThreadPolicy.Builder#detectNetwork())
- [HttpEngine](https://developer.android.com/reference/android/net/http/HttpEngine)
- [HttpEngine.Builder](https://developer.android.com/reference/android/net/http/HttpEngine.Builder)
- [Cronet 文档](https://developer.android.com/develop/connectivity/cronet)
- [ProviderInstaller](https://developers.google.com/android/reference/com/google/android/gms/security/ProviderInstaller)
- [Conscrypt Mainline 模块](https://source.android.com/docs/core/ota/modular-system/conscrypt)
- [DNS-over-HTTP/3 in Android](https://security.googleblog.com/2022/07/dns-over-http3-in-android.html)
- [OkHttp Builder protocols](https://square.github.io/okhttp/5.x/okhttp/okhttp3/-ok-http-client/-builder/protocols.html)
- [Android TrafficStats](https://developer.android.com/reference/android/net/TrafficStats)
- [Android ConnectivityManager](https://developer.android.com/reference/android/net/ConnectivityManager)
- [Android Optimizing Battery Life](https://developer.android.com/training/monitoring-device-state)
- [OkHttp EventListener API](https://square.github.io/okhttp/4.x/okhttp/okhttp3/-event-listener/)
- [Perfetto 自定义 Trace Event](https://perfetto.dev/docs/instrumentation/tracing-sdk)
- [Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径](DeepResearch/2026-06-17-android17-network-quota-limit-enforcement.md) — 源码级分析双服务架构（采集+策略执行）：BPF/eBPF FastDataInput 模式 4 个 BpfMap 绕过 procfs 零拷贝读取、quota 超限触发路径（内核 BPF map → netd.bandwidthSetGlobalAlert → AlertObserver.onQuotaLimitReached → performPollLocked 持久化 → firewall chain 隔离）、15K 采样率与 2MB 持久化阈值、BlockedReasons/AllowedReasons UID 级状态机
