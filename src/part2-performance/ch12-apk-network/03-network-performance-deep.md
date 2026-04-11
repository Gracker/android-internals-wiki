---
title: "网络性能深入：连接池、TLS 与传输优化"
chapter: "12.3"
section: "12.3"
status: ready-for-review
drafted_date: "2026-04-07"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-07"
last_verified_against: "OkHttp 4.12.x / AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/training/basics/network-ops/managing"
  - type: official
    path: "https://square.github.io/okhttp/"
  - type: official
    path: "https://developer.android.com/reference/android/net/TrafficStats"
  - type: official
    path: "https://developer.android.com/reference/android/net/ConnectivityManager"
tags: [network, okhttp, retrofit, tls, http2, connection-pooling, dns, battery]
related_chapters: ["12.2", "8.2", "11.2", "5.8", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-07"
gap_source: "AOSP结构+官方文档+读者需求"
gap_score: 14
drafted_by: "openclaw-task2a"
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# 12.3 网络性能深入：连接池、TLS 与传输优化

在 §12.2 中我们从宏观角度梳理了网络性能优化的策略和工具：HTTP/2 与 HTTP/3 的选择、弱网应对方案、OkHttp EventListener 监控等。那些内容回答了"应该做什么"。

这一节我们深入到网络请求的底层机制：一个 HTTP 请求从发起到收到响应，中间到底经历了哪些步骤？每个步骤的耗时分布在哪？为什么连接复用比新建连接快这么多？TLS 握手到底有多贵？DNS 解析在什么情况下会成为瓶颈？

理解这些底层机制之后，再看 Perfetto 中的网络相关 Trace 数据，我们就能精确判断性能瓶颈出在哪个环节——是 DNS 慢、还是 TLS 握手耗时、或者是服务端响应延迟。

## Android 网络栈全景

一个 HTTP 请求从 App 代码调用 `OkHttpClient.newCall().execute()` 开始，到拿到 Response 对象，中间经历了一条完整的调用链。我们逐层拆解。

应用层是 OkHttp（或者 Cronet、HttpEngine 等网络库），负责 HTTP 协议的处理——构建请求、解析响应、管理连接池。往下是 Java 层的 `java.net` 和 `javax.net.ssl`，提供 Socket 和 TLS 抽象。再往下进入系统层，Android 的 DNS resolver 模块负责域名解析，`libcore` 中的 `Conscrypt` 安全提供者处理 TLS 加解密。最终通过内核的 TCP/IP 协议栈、网卡驱动，经由无线电模块发送出去。

这条链路上的每个环节都有可能成为性能瓶颈。一个典型 HTTPS 请求的完整时间分解如下：

1. **DNS 解析**：将域名解析为 IP 地址。局域网环境下 <1ms，公网解析通常 20-120ms。
2. **TCP 连接建立**：三次握手，取决于网络 RTT（Round-Trip Time），通常 30-100ms（4G网络）。
3. **TLS 握手**：密钥协商和证书验证。TLS 1.2 需要 2 个 RTT，TLS 1.3 减少到 1 个 RTT。
4. **HTTP 请求/响应**：发送请求头和 body、等待服务端处理、接收响应。首字节时间（TTFB）取决于服务端处理能力。

可以看到，对于首次连接，前三步可能消耗 100-300ms 才开始真正传输数据。连接池和 keep-alive 的价值就在于：第二次请求可以跳过前三步，直接进入第 4 步。

### 网络操作与主线程性能

在 Perfetto 中，如果看到主线程上有长时间的网络相关等待（比如 `Socket` read/write 的 I/O 阻塞），这通常意味着网络操作被错误地放在了主线程。Android 的 `StrictMode` 默认会检测主线程上的网络 I/O 操作（`penaltyDeath` 或 `penaltyLog`），但很多 App 在 Release 版本中关闭了 StrictMode，导致这类问题在测试阶段被忽略。

从启动速度的角度看，冷启动过程中的同步网络请求是常见的"首帧延迟"原因。App 在 `Application.onCreate()` 或首个 Activity 的 `onCreate()` 中发起同步网络请求，整个启动流程被阻塞在等待网络响应上。在 Perfetto 中，这类问题表现为 MainThread 上一个长时间处于 `Sleeping` 或 `I/O wait` 状态的 segment，对应的 `blocked_function` 通常是 `pread64` 或 `poll`。

## OkHttp 连接池与复用机制

OkHttp 的连接池是理解 Android 网络性能优化的核心。它解决的问题很直接：TCP 连接的建立代价很高，能不能复用已经建立的连接？

### 连接池的工作方式

OkHttp 内部使用 `ConnectionPool` 类管理所有 TCP 连接。当一个请求完成后，底层的 TCP 连接不会被立即关闭，而是归还到连接池中。下一个请求如果目标是同一个地址（相同的 host、port、scheme），就可以直接从池中取出一条已有连接使用，省去 DNS 解析、TCP 握手、TLS 握手三个步骤。

[已验证: OkHttp 4.12.x, okhttp3.ConnectionPool]

连接池有两个核心参数：`maxIdleConnections`（最大空闲连接数，默认 5）和 `keepAliveDuration`（空闲连接的最大存活时间，默认 5 分钟）。超过这个数量或时间的空闲连接会被后台清理线程回收。

```java
// okhttp3/ConnectionPool.java
// OkHttp 默认连接池配置
public ConnectionPool() {
    this(5, 5, TimeUnit.MINUTES);
}
```

这段代码告诉我们一个重要的默认值：OkHttp 最多保持 5 条空闲连接，每条最多存活 5 分钟。对于大多数 App 来说，这意味着如果在 5 分钟内再次访问同一个域名，可以直接复用连接。如果 App 需要同时与超过 5 个不同的后端域名保持长连接，空闲连接数可能不够，需要适当调大这个参数。

### HTTP/2 多路复用 vs HTTP/1.1 连接池

HTTP/1.1 的连接复用是串行的：一个 TCP 连接上，必须等上一个请求完成后才能发送下一个请求。如果浏览器或 App 需要并发请求同一个域名的多个资源，就需要建立多条 TCP 连接。

HTTP/2 引入了多路复用（multiplexing）：一个 TCP 连接上可以同时承载多个请求和响应，通过 stream ID 区分不同的请求。这意味着只需要一条 TCP 连接就能满足所有并发需求。

在 OkHttp 中，当服务端支持 HTTP/2 时（通过 ALPN 协商），连接池的行为会发生变化：同一个地址只需要维持一条连接，所有请求复用这条连接。这大大减少了连接池的压力，也降低了服务端的资源消耗。

从性能数据上看，HTTP/2 多路复用在并发请求场景下优势明显。一个典型的 Web 页面可能需要加载 30-50 个资源，HTTP/1.1 下浏览器需要 6-8 条 TCP 连接并发请求（浏览器对同一域名的并发连接数有限制），而 HTTP/2 只需要 1 条。减少了 TCP 连接数意味着减少了 DNS 解析次数、TCP 握手次数、TLS 握手次数，整体页面加载时间可以缩短 20-40%。

[待补充：HTTP/2 多路复用在 Perfetto 中的具体 Trace 表现截图]

### 连接建立的完整流程

一个 OkHttp 请求的连接建立过程大致如下：

1. **Route Selection**：OkHttp 的 `RouteSelector` 根据 DNS 解析结果、代理配置、HTTP/2 支持情况选择一条最优路由。
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
connectEnd()          // 连接建立完成 → 得到 TCP 连接耗时
connectionAcquired()  // 从连接池获取连接（可能是复用）
requestHeadersStart() // 发送请求头
responseHeadersStart()// 收到响应头 → 得到 TTFB
responseBodyStart()   // 开始接收 body
responseBodyEnd()     // body 接收完成 → 得到传输耗时
callEnd()             // 请求完成
```

这套回调机制是网络性能监控的基础。在线上环境中，我们可以通过 EventListener 收集每个阶段的耗时，建立网络性能的基线数据。

## TLS 握手性能与优化

TLS 握手是 HTTPS 请求中耗时最长的步骤之一，理解它的流程和优化手段对分析网络性能至关重要。

### TLS 1.2 握手流程

TLS 1.2 的完整握手需要 2 个 RTT（Round-Trip Time），流程如下：

**第一次往返**：客户端发送 `ClientHello`，包含支持的 TLS 版本、加密套件列表、随机数。服务端回复 `ServerHello`，选定 TLS 版本和加密套件，发送自己的证书链和密钥交换参数。

**第二次往返**：客户端验证服务端证书，发送密钥交换完成消息。服务端确认后，双方开始加密通信。

在一个 RTT 约 50ms 的 4G 网络上，TLS 1.2 完整握手至少需要 100ms。加上 CPU 做非对称加密运算（RSA/ECDHE）的时间，实际握手耗时通常在 150-300ms。

### TLS 1.3 的性能提升

TLS 1.3（Android 10+ 默认启用）将握手从 2-RTT 减少到 1-RTT。它通过以下方式实现：

1. 移除了 `ServerKeyExchange` 和 `ClientKeyExchange` 两个独立步骤，将密钥交换参数合并到 `Hello` 消息中。
2. 简化了密码套件协商，只保留基于 ECDHE 的前向保密密钥交换。
3. 移除了不安全的旧算法（RSA 密钥交换、CBC 模式加密、SHA-1 签名等）。

从性能角度看，1-RTT 意味着在 50ms RTT 的网络上，TLS 握手从至少 100ms 降到约 50ms，加上 CPU 计算时间，总耗时约 80-150ms——大约是 TLS 1.2 的一半。

[已验证: 官方文档, developer.android.com — TLS 1.3 在 Android 10 (API 29) 起默认启用]

TLS 1.3 还定义了 0-RTT 恢复模式，允许客户端在恢复会话时直接携带加密数据发送，跳过握手过程。但需要注意：Android 原生的 TLS 1.3 实现目前不支持 0-RTT，这是出于安全考虑——0-RTT 数据存在重放攻击的风险。

### Conscrypt 与 Android TLS 实现

Android 的 TLS 实现在底层使用的是 Google 的 Conscrypt 库，它构建在 BoringSSL（Google 维护的 OpenSSL 分支）之上。从 Android 10 开始，Conscrypt 通过 Project Mainline 以 APEX 模块的形式更新，Google 可以通过 Google Play Services 推送 TLS 相关的安全补丁，不再依赖 OEM 的系统更新。

对于需要支持 Android 10 以下设备的 App，可以通过 Jetpack 方式引入 Conscrypt：

```java
// 在 Application.onCreate() 中插入 Conscrypt 作为安全提供者
Security.insertProviderAt(Conscrypt.newProvider(), 1);
```

插入后，OkHttp 等网络库会自动使用 Conscrypt 的 TLS 实现，从而在旧设备上也获得 TLS 1.3 的性能提升。

[已验证: 官方文档, android.com — Conscrypt 自 API 16 起集成，Android 10+ 通过 Mainline 更新]

### 证书验证的性能开销

TLS 握手中的证书验证涉及证书链的签名校验，在性能敏感场景下值得关注。Certificate Pinning（证书固定）是一种安全策略，它要求服务端证书必须匹配预设的公钥哈希。OkHttp 提供了 `CertificatePinner` 来实现这一点。

需要注意的是，Certificate Pinning 本身不会增加额外的网络往返，但错误的配置（比如 pin 过期后没有更新）会导致所有请求直接失败。从性能角度看，更大的影响来自于 OCSP（Online Certificate Status Protocol）和 CRL（Certificate Revocation List）检查——如果 App 或系统在 TLS 握手过程中去查询证书的吊销状态，会额外增加一次或多次网络请求。Android 默认不执行 OCSP stapling 之外的在线证书状态检查，这是一个合理的性能与安全的平衡。

## DNS 解析性能

DNS 解析是网络请求链路的第一步，也是最容易被忽视的性能瓶颈。

### Android DNS 解析流程

当 App 通过 `InetAddress.getAllByName()` 或底层的 `getaddrinfo()` 系统调用发起 DNS 查询时，请求会进入 Android 的 DNS resolver 模块。这个模块是 Android 网络栈的一部分，从 Android 11 开始作为独立模块（DNS Resolver module）通过 Mainline 更新。

解析流程是：Java 层的 `InetAddress` → `libcore.io.Linux`（JNI）→ `getaddrinfo()`（libc）→ Android DNS resolver → 发送 DNS 查询到配置的 DNS 服务器。

系统层面，Android 维护了 DNS 缓存，但这个缓存的 TTL（Time To Live）由 DNS 记录本身的 TTL 值决定。如果域名的 DNS 记录 TTL 很短（比如 60 秒），频繁的解析请求会反复命中网络查询。

### DNS 解析耗时分布

DNS 解析的耗时差异很大，取决于缓存命中情况和网络环境：

- **本地缓存命中**：<1ms，几乎可以忽略
- **局域网 DNS 服务器响应**：1-10ms
- **公网 DNS 服务器响应**：20-120ms（国内运营商 DNS 可能更长）
- **DNS 解析失败/超时**：通常 3-30 秒（取决于系统超时配置）

一个容易被忽视的问题是：DNS 解析是同步阻塞操作。如果 DNS 查询发生在主线程上（哪怕是通过 OkHttp 发起），在解析完成之前线程会被阻塞。OkHttp 默认在自己的线程池中执行网络请求，但自定义的 `Dns` 实现如果不注意异步化，可能把 DNS 查询带回调用线程。

### DNS over HTTPS 与性能

Android 9 引入了 DNS-over-TLS (DoT) 的"私有 DNS"设置，Android 13 新增了 DNS-over-HTTPS (DoH) 的原生支持。从 Android 11 开始，Android 还支持 DNS-over-HTTP/3 (DoH3)，Google 的测试数据显示：相比 DoT，DoH3 的中位查询时间缩短 24%，P95 分位缩短 47%。

DoH3 之所以更快，是因为它将每个 DNS 查询放在独立的 QUIC stream 中，避免了 DoT 在单一 stream 上的队头阻塞。

[已验证: 官方文档, android.com — DoT 从 Android 9 支持，DoH3 从 Android 11 支持]

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

使用自定义 DNS 有一个需要注意的陷阱：OkHttp 只在建立新连接时才做 DNS 解析。如果连接池中已有到该域名的连接，即使 DNS 记录发生了变化（比如服务端 IP 切换），已缓存的连接仍然使用旧 IP。解决方案是在网络状态变化时主动清理连接池：

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

移动设备的无线电模块（基带芯片 + 射频前端）遵循一个状态机模型运行。以 4G LTE 为例，它有三个主要状态：

**全功率状态（RRC_CONNECTED）**：数据传输中，基带芯片全速运行，功耗最高。一个典型的 4G 基带在全功率状态下可能消耗 500-1000mA 电流。

**低功率状态（DRX/IDLE）**：数据传输完成后的过渡状态，基带降低时钟频率和射频功率，功耗约为全功率状态的 50%。

**待机状态**：基带进入深度休眠，仅监听寻呼消息，功耗极低（约 10-20mA）。

关键在于状态转换的延迟（tail time）。基带不会在数据传输完成后立刻进入待机状态——它会在低功率状态停留一段时间（4G 网络通常 10-20 秒），以防还有后续数据需要传输。这意味着即使一个网络请求只用了 100ms，基带可能会在全功率和低功率状态维持额外 10-20 秒。

### 批量请求 vs 分散请求

理解了 Radio State Machine 的行为，我们就能理解为什么"批量请求"比"分散请求"省电。

假设 App 需要在 1 分钟内发送 6 次网络请求：

- **分散请求**（每 10 秒 1 次）：每次请求都会唤醒基带到全功率状态，基带在 1 分钟内几乎无法进入待机。总功耗约为基带全功率持续 60 秒。
- **批量请求**（1 次发送 6 个请求）：基带只唤醒一次，传输完成后 10-20 秒回到待机。总功耗约为基带全功率持续 15-20 秒。

两者功耗差异可能达到 3-4 倍。

[待补充：Radio State Machine 状态转换时序图]

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

添加这个 Interceptor 后，在 Perfetto 中可以看到每个网络请求在 OkHttp 线程上占用的精确时间。结合 OkHttp 的 `EventListener`，还可以分别标记 DNS、连接、TLS、请求/响应各阶段：

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

### 定位主线程网络阻塞

在 Perfetto 中识别主线程上的网络阻塞，最直接的信号是：

1. 主线程出现长时间 `Sleeping` 或 `I/O wait` 的 segment。
2. 对应的 `blocked_function` 是 `poll`、`pread64` 或 `recvmsg`。
3. 在该 segment 期间，如果系统有 `binder_driver` 活动，可能是 `ConnectivityManager` 或 `TrafficStats` 等系统服务的调用。

严格来说，OkHttp 默认不会在主线程执行网络操作（除非调用 `execute()` 而非 `enqueue()`）。但在某些场景下——比如启动时同步等待关键配置数据——App 会故意在主线程做同步网络请求。这种情况下，Perfetto 中看到的表现就是 MainThread 上一个长达数百毫秒到数秒的阻塞 segment。

### 网络性能监控的最佳实践

线上环境中，通过 OkHttp `EventListener` 收集的网络性能指标通常包括：

- **DNS 时间**：`dnsEnd - dnsStart`
- **连接时间**：`connectEnd - connectStart`
- **TLS 时间**：`secureConnectEnd - secureConnectStart`
- **首字节时间（TTFB）**：`responseHeadersStart - requestHeadersStart`
- **内容传输时间**：`responseBodyEnd - responseBodyStart`
- **总耗时**：`callEnd - callStart`

这些指标的 P50 和 P95 分布是评估网络性能健康度的关键基线。如果 TTFB 的 P95 从 200ms 涨到 800ms，大概率是服务端处理能力出了问题；如果 DNS 时间的 P95 从 50ms 涨到 500ms，可能是 DNS 配置或运营商网络出了问题。

## 扩展

### 🔸 HTTP/3 与 QUIC

HTTP/3 基于 Google 设计的 QUIC 协议，运行在 UDP 之上。它解决的核心问题是 TCP 的队头阻塞（Head-of-Line Blocking）：在 HTTP/2 over TCP 中，一个 TCP 包的丢失会阻塞该连接上所有 stream 的数据传输；而 QUIC 中每个 stream 独立处理丢包恢复，一个 stream 的丢包不会影响其他 stream。

从连接建立性能看，QUIC 支持真正的 0-RTT 连接恢复：如果客户端之前连接过该服务端，可以在第一个包中就携带加密数据，完全跳过握手过程。这比 TLS 1.3 的 1-RTT 更快。

Android 对 QUIC 的支持主要通过 Cronet（Chromium 网络栈的 Android 封装）。从 Android 11 开始，系统默认的 `HttpEngine`（API 34+ 推荐）也支持 QUIC。OkHttp 目前不原生支持 QUIC，但可以通过 `crazy_things_` 等实验性扩展来桥接 Cronet。

[待验证：OkHttp 对 QUIC 的官方支持计划]

### 🔸 WebSocket 性能

WebSocket 提供了全双工的持久连接，适合实时通信场景（聊天、推送、行情数据）。与 HTTP long-polling 相比，WebSocket 在建立连接后只需要 2-14 字节的帧头开销，而 long-polling 每次请求都有完整的 HTTP 头部开销（通常数百字节）。

从功耗角度看，WebSocket 的长连接会持续占用基带资源——只要连接活跃，基带就无法进入待机状态。对于频繁的小消息推送，WebSocket 的功耗效率好于 long-polling（减少了重复的连接建立开销）；但对于低频推送（比如每分钟一条），用 Firebase Cloud Messaging（FCM）等系统级推送通道更省电，因为 FCM 复用了系统与 Google 服务器的已有连接。

### 🔸 Retrofit 与 Coroutine 集成性能

Retrofit 是 Android 上最常用的 HTTP 客户端封装，它将 OkHttp 的 Call 对象映射为 Kotlin suspend 函数。从性能角度看，Retrofit 的适配层开销很小——它本质上是在 OkHttp Call 之上加了一层接口代理和类型转换。

使用 `suspend` 函数后，网络请求的线程模型变得更清晰：请求在 OkHttp 的内部线程池中执行，结果通过 Kotlin 协程的 Continuation 机制回调到调用方的调度器（通常是 `Dispatchers.Main`）。对比 RxJava 的 Observable 链式调用，协程版本减少了一层 Observable 包装和调度器切换的开销，但这部分开销在整体网络请求耗时中占比很小（通常 <1ms），不是性能优化的重点。

真正需要注意的性能问题是大批量并发请求的线程模型。OkHttp 默认的 Dispatcher 配置是最大 64 个并发请求、每个域名最多 5 个并发请求。如果 App 需要大量并发请求（比如图片列表预加载），需要根据实际情况调整 Dispatcher 的配置，否则请求会排队等待，表现为 TTFB 虚高。

## 参考资料

- [OkHttp 官方文档](https://square.github.io/okhttp/)
- [Android Network Operations](https://developer.android.com/training/basics/network-ops)
- [Android TrafficStats](https://developer.android.com/reference/android/net/TrafficStats)
- [Android ConnectivityManager](https://developer.android.com/reference/android/net/ConnectivityManager)
- [Android Optimizing Battery Life](https://developer.android.com/training/monitoring-device-state)
- [OkHttp EventListener API](https://square.github.io/okhttp/4.x/okhttp/okhttp3/-event-listener/)
- [Conscrypt 安全提供者](https://github.com/google/conscrypt)
- [Perfetto 自定义 Trace Event](https://perfetto.dev/docs/instrumentation/tracing-sdk)
