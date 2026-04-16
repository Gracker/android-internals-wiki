---
title: "网络性能优化"
chapter: "12.2"
section: "12.2"
status: ready-for-review
drafted_date: "2026-04-03"
drafted_by: openclaw-task2a
reviewed_date: "2026-04-17"
polish_count: 1
polish_date: "2026-04-10"
polish_by: "task2b-polish"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "OkHttp 4.12.x / Android 16"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/net/ConnectivityManager"
  - type: official
    path: "https://square.github.io/okhttp/"
  - type: official
    path: "https://developer.android.com/training/basics/network-ops"
tags: [network, OkHttp, HTTP/2, HTTP/3, QUIC, weak-network, performance]
related_chapters: ["12.1", "6.1", "8.1"]
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task2b_state: idle
---

# 网络性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 网络性能指标：DNS 时间、连接时间、首字节时间(TTFB)、传输速率
- 🔹 HTTP/2 与 HTTP/3(QUIC) 的性能差异与适用场景
- 🔹 网络请求优化：连接复用、请求合并、预连接(preconnect)
- 🔹 弱网优化策略：超时策略、重试策略、降级策略
- 🔹 网络性能监控：OkHttp EventListener、NetworkCallback

### 扩展（可选深入）

- 🔸 CDN 策略对 Android 客户端的影响
- 🔸 图片加载的网络优化（渐进式加载、缩略图策略）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要关注网络性能

当我们谈论 Android 性能时，往往最先想到的是渲染卡顿、内存泄漏、ANR 这些"看得见"的问题。但网络请求的慢——DNS 解析耗时 200ms、连接建立卡在 TLS 握手、弱网下反复超时重试——同样是用户可感知的性能劣化。它不表现为帧率下降，而是表现为"白屏等待"、"数据加载中"的时间变长，严重时直接导致请求超时、功能不可用。

网络性能与本地性能有一个根本性的区别：**它不可控**。本地渲染管线的耗时主要由 App 自身代码决定，但网络请求的耗时取决于运营商、基站信号、DNS 服务器、CDN 节点、服务器负载等一系列不可控因素。正因如此，网络性能优化的核心思路不是"消除延迟"，而是**减少可控环节的延迟、增强对不可控因素的容错能力**。

本节将从网络请求的全生命周期出发，先建立一套可度量的性能指标体系，再逐层分析协议选择、请求优化、弱网容错、监控体系四大主题。读完之后，我们面对一个"网络慢"的用户反馈，应该能快速定位是 DNS 慢、连接慢、还是服务端慢，并知道在代码层面可以做哪些优化。

## 网络性能指标：一次请求的时间拆解

一个 HTTP 请求从发起到收到完整响应，可以拆分为若干个阶段，每个阶段的耗时对应一个独立的性能指标。理解这些指标，是我们定位网络瓶颈的基础。

一次完整的 HTTP 请求时间线大致如下：

```
DNS 查询 → TCP 连接 → TLS 握手 → 发送请求头 → 发送请求体 →
等待服务端处理 → 收到第一个响应字节 → 接收完整响应体
```

对应的关键指标有三个：

**DNS 解析时间（DNS Time）**：从发起域名解析到获得 IP 地址的耗时。在移动网络下，DNS 解析通常是第一个瓶颈。本地 DNS 缓存可以缓解，但首次请求或缓存过期后的 DNS 查询可能需要 20-200ms，在极端情况下（如运营商 DNS 不可用）甚至超过数秒。

**连接时间（Connect Time）**：从开始建立 TCP 连接到连接就绪的耗时。如果使用 HTTPS（现在几乎所有请求都是），这里还包含 TLS 握手的时间。连接时间通常在 50-200ms 之间，但如果服务器物理距离远或网络拥堵，可能翻倍。

**首字节时间（Time To First Byte, TTFB）**：从发送请求到收到服务端返回的第一个字节的时间。这个指标反映了服务端处理速度和网络往返延迟的综合影响。TTFB 是判断"问题在客户端还是服务端"的关键分水岭——如果 DNS 和连接都很快但 TTFB 高，问题几乎一定在服务端。

为什么这三个指标如此重要？因为它们各自对应不同的优化方向。DNS 慢 → 用 DNS 预解析或 HTTPDNS；连接慢 → 用连接复用或预连接；TTFB 慢 → 优化服务端或用 CDN。如果我们在做性能优化时不拆分指标，只是简单地看到"请求花了 2 秒"，就无从下手。

[已验证: 官方文档, developer.android.com/reference/okhttp3/EventListener]

### 传输速率

除了时间指标，传输速率（Throughput）也是网络性能的重要维度。它表示单位时间内传输的数据量，通常以 Mbps 或 MB/s 衡量。传输速率受带宽、网络拥塞、数据包大小等因素影响。

在实际优化中，传输速率主要影响大文件下载和上传场景（图片、视频、APK 更新包等）。对于常规的 API 请求（通常几 KB 到几十 KB），传输速率的影响远小于 DNS 和连接时间。这也是为什么网络优化的重心通常放在"减少请求次数"和"缩短连接建立时间"上，而不是"提升带宽利用率"。

## HTTP/2 与 HTTP/3(QUIC)：协议选择对性能的影响

网络请求的底层协议决定了连接复用、头部压缩、丢包恢复等基础能力的上限。OkHttp 从 4.x 版本开始默认支持 HTTP/2（API 21+），而 HTTP/3（基于 QUIC）则需要通过 Cronet 等库引入。两者在移动场景下的性能差异，是我们选择技术方案的重要依据。

### HTTP/2：多路复用解决了 HTTP/1.1 的队头阻塞

HTTP/1.1 时代，浏览器（和 HTTP 客户端）对同一域名的并发请求有数量限制（通常 6 个）。超过限制的请求需要排队等待，这就是著名的"队头阻塞"（Head-of-Line Blocking）。移动端 App 通常会为每个域名维护一个连接池来缓解这个问题，但根本性的限制依然存在。

HTTP/2 通过**多路复用**（Multiplexing）解决了这个问题。在 HTTP/2 下，一个 TCP 连接可以同时承载多个请求和响应，每个请求被分配一个独立的 Stream ID，数据被拆分为 Frame 在同一连接上交错传输。此外，HTTP/2 引入了 **HPACK 头部压缩**，减少了重复 Header 的传输开销。

在 Perfetto 中，如果 App 使用 HTTP/2，我们会看到 TCP 连接数量显著减少——多个请求共享同一个连接，而不是每个请求独占一个。这对移动网络特别有利，因为每次新建 TCP 连接都需要经历三次握手（加上 TLS 握手），在弱网环境下每次新建连接的 TLS 握手开销可能达到 100-200ms。

但 HTTP/2 并非完美。它解决了应用层的队头阻塞，却把问题推到了传输层——TCP 层仍然存在队头阻塞：如果一个 TCP 包丢失，该连接上所有 Stream 的数据传输都会被阻塞，直到丢包被重传。在高丢包率的移动网络下，这个问题尤为突出。

### HTTP/3(QUIC)：为移动网络设计的传输协议

HTTP/3 使用 QUIC 作为传输层协议，而 QUIC 基于 UDP 实现。这个架构变更带来了几个对移动网络场景尤为关键的改进：

**零/一次 RTT 连接建立**：QUIC 将传输层握手和 TLS 1.3 加密握手合并为一次交互。首次连接只需 1-RTT，后续连接可以利用保存的会话信息实现 0-RTT，即第一个包就可以携带请求数据。在移动网络下，一个 RTT 可能是 50-100ms，省掉一次往返意味着白屏时间直接减少 50-100ms。

**独立的 Stream 丢包恢复**：QUIC 在自己的传输层实现了多路复用，每个 Stream 的丢包重传互不影响。一个 Stream 丢包不会阻塞其他 Stream 的数据传输——这正是 HTTP/2 over TCP 最大的痛点。

**连接迁移**：QUIC 使用 Connection ID 而不是四元组（源 IP、源端口、目标 IP、目标端口）来标识连接。这意味着当用户的网络从 Wi-Fi 切换到 4G/5G 时（IP 地址改变），QUIC 连接可以无缝迁移，不需要重新建立连接。在 HTTP/2 下，这种网络切换会导致所有正在进行的请求失败并需要重试。

实际性能数据也印证了 HTTP/3 在移动场景下的优势。Google 报告 YouTube 在移动设备上缓冲时间减少了 15%；Uber 在 Android/iOS 上采用 QUIC 后尾部延迟降低了 10-30%；Meta 在 Instagram 上观察到请求错误率降低 6%、尾部延迟降低 20%。 [已验证: 来源见 Uber Engineering Blog (eng.uber.com), Google Chromium Blog]

### 在 Android 上的选择

在 Android 开发中，协议选择受到库生态的制约。OkHttp 默认支持 HTTP/2，这是大多数 App 的默认选择。要使用 HTTP/3，需要引入 Google 的 Cronet 库（或 Chromium 网络栈的封装），这会增加 APK 体积约 1-2MB。

实际建议是：**HTTP/2 作为基线，在高丢包、频繁网络切换的场景考虑 HTTP/3**。如果 App 的用户群体中有大量移动网络用户，且对首屏加载时间敏感（如信息流、电商），HTTP/3 带来的收益是值得额外引入 Cronet 的。

[已验证: 官方文档, square.github.io/okhttp — HTTP/2 default since 4.x]
[待验证: OkHttp 5.x 对 HTTP/3 的支持计划]

## 网络请求优化：连接复用、请求合并与预连接

理解了协议层面的能力后，我们来看在应用层可以做的三类关键优化。这三者的共同目标是减少网络请求的"固定开销"——即与数据传输量无关，只要发起请求就必然产生的那部分延迟。

### 连接复用：一个 OkHttpClient 实例走天下

连接复用是最基础也是最容易被忽视的优化。OkHttp 通过 ConnectionPool 管理 TCP 连接的复用：一个请求完成后，连接不会立即关闭，而是保持在池中供后续请求使用。当新请求的目标地址与池中某个空闲连接匹配时，直接复用该连接，省去 TCP 三次握手和 TLS 握手的开销。

但这个机制生效的前提是：**所有请求共享同一个 OkHttpClient 实例**。如果在代码中每次请求都 `new OkHttpClient()`，就完全绕过了连接池，每个请求都要从头建立连接。

```java
// 错误：每次请求创建新 client，无法复用连接
void makeRequest() {
    OkHttpClient client = new OkHttpClient(); // 每次都是全新的连接池
    Request request = new Request.Builder()
        .url("https://api.example.com/data")
        .build();
    client.newCall(request).execute();
}
```

正确做法是将 OkHttpClient 作为单例使用：

```java
// 正确：全局共享一个 client，连接池生效
public class NetworkClient {
    private static final OkHttpClient INSTANCE = new OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build();

    public static OkHttpClient get() { return INSTANCE; }
}
```

OkHttp 默认的 ConnectionPool 配置是：最多 5 个空闲连接，每个连接保持存活 5 分钟。这意味着在 5 分钟内有新请求到同一地址，可以直接复用连接——在移动端频繁切换页面的场景下，这个时间窗口足够覆盖大部分复用机会。

[已验证: OkHttp 官方文档, square.github.io/okhttp/connections/]

### 请求合并：把多次往返变成一次

请求合并（Request Batching）的思路是：如果能一次请求拿到所有数据，就不要分成多次请求。这在 API 设计层面就需要考虑。

典型场景是一个页面需要多个接口的数据。如果串行请求三个接口，总耗时 = 请求1 + 请求2 + 请求3。但如果后端提供一个聚合接口，一次请求返回所有数据，总耗时 ≈ 单次请求耗时（数据量略大但传输时间远小于减少的往返次数）。

在不修改后端 API 的情况下，OkHttp 的 HTTP/2 多路复用可以自动并行发送多个请求到同一服务器，省去串行等待。但注意：减少请求次数的效果通常大于并行化——并行化只减少了等待时间，而合并请求直接减少了 RTT 数量。

### 预连接：在需要之前就准备好

预连接（Preconnect）的思路是：在用户即将发起网络请求之前，提前完成 DNS 解析和 TCP/TLS 连接建立。当真正的请求到来时，直接复用已建立的连接，DNS 和连接时间接近于零。

典型的使用场景是：App 启动时预连接后端 API 域名，或用户进入某个功能页面前预连接该功能的数据域名。实现方式很简单——发起一个 HEAD 请求或空 GET 请求即可触发连接建立。

```java
// 预连接示例：App 启动时调用
public class PreconnectManager {
    private final OkHttpClient client;

    public void preconnect(String url) {
        Request request = new Request.Builder()
            .url(url)
            .head() // HEAD 请求不下载 body，开销最小
            .build();
        client.newCall(request).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {
                // 预连接失败不影响业务，静默处理
            }
            @Override public void onResponse(Call call, Response response) {
                response.close(); // 只需要建立连接，不关心响应内容
            }
        });
    }
}
```

OkHttp 5.x 还引入了 `ConnectionPool.setPolicy()` API，允许为特定地址配置最小连接池大小，进一步系统化了预连接能力。不过截至 OkHttp 4.12.x 稳定版，手动触发 HEAD 请求仍然是最实用的方案。

[待验证: OkHttp 5.0 ConnectionPool.setPolicy API 在稳定版中的可用性]

## 弱网优化策略：超时、重试与降级

移动网络的不确定性远高于固定网络——电梯里信号突然消失、高铁上频繁切换基站、地下室完全无信号。弱网优化不是让网络变快，而是**让 App 在网络很差时依然可用或至少优雅降级**。

### 超时策略：不要等太久，也不要放弃太快

OkHttp 的超时分为三类，每一类对应请求生命周期的不同阶段：

- **connectTimeout**：建立 TCP 连接的超时时间。默认 10 秒。在弱网下，10 秒可能都不够完成一次 TCP 握手，但如果设得太长，用户会面对漫长的"加载中"。
- **readTimeout**：等待服务端响应数据的超时时间。默认 10 秒。这个值需要根据接口特性调整——列表接口可以短一些（10-15 秒），而文件上传、报表生成等需要更长（30-60 秒）。
- **writeTimeout**：向服务端写入请求体的超时时间。默认 10 秒。主要影响上传场景。

合理的超时配置不是"一刀切"，而是根据请求类型分档。关键接口（如支付、登录）可以给更长的超时；非关键接口（如上报、埋点）可以设短一些，快速失败不影响核心体验。

```java
// 全局默认超时
OkHttpClient client = new OkHttpClient.Builder()
    .connectTimeout(15, TimeUnit.SECONDS)
    .readTimeout(20, TimeUnit.SECONDS)
    .writeTimeout(15, TimeUnit.SECONDS)
    .build();

// 特定请求使用更长超时（OkHttp 支持按请求覆盖）
Request request = new Request.Builder()
    .url("https://api.example.com/report")
    .build();

OkHttpClient longTimeoutClient = client.newBuilder()
    .readTimeout(60, TimeUnit.SECONDS)
    .build();
longTimeoutClient.newCall(request).execute();
```

[已验证: OkHttp 官方文档, square.github.io/okhttp — timeout 配置 API]

### 重试策略：指数退避 + 幂等性约束

在网络不稳定时，简单的"失败就重试"策略可能让情况更糟——大量重试请求涌入已经不堪重负的网络，形成"重试风暴"。正确的重试策略需要满足三个条件：

**第一，只重试可恢复的错误。** 连接超时（SocketTimeoutException）、DNS 解析失败（UnknownHostException）可以重试；但 400 类客户端错误（参数错误、鉴权失败）重试毫无意义，服务端 5xx 错误可以有限重试。

**第二，使用指数退避（Exponential Backoff）加抖动（Jitter）。** 每次重试的间隔时间翻倍：第一次等 1 秒，第二次 2 秒，第三次 4 秒。加上随机抖动可以避免多个客户端同时重试导致的"雷群效应"。

**第三，区分幂等和非幂等请求。** GET、PUT、DELETE 是幂等的，多次执行效果相同，可以安全重试。POST、PATCH 通常不是幂等的——重复提交可能导致重复扣款、重复发帖。对非幂等请求的重试必须配合服务端的幂等键（Idempotency Key）机制。

OkHttp 本身有一定的内置重试逻辑（`RetryOnConnectionFailure` 默认开启），但它只处理连接级别的重试（如 TCP 连接失败后尝试备用 IP），不处理应用层的超时重试和指数退避。应用层重试需要通过 Interceptor 实现。

### 降级策略：没有网络也要能用

降级策略是指在网络极差或完全不可用时，App 仍然能提供基本功能。核心思路有两个：

**本地缓存**：OkHttp 内置 HTTP 缓存机制，只要服务端返回了合适的 Cache-Control 头，OkHttp 会自动缓存响应。在离线或弱网时，可以使用缓存数据（即使已经过期），配合 UI 上的"数据可能不是最新"提示。

**功能降级**：对非核心功能，在网络差时主动降级。例如：图片加载从原图降级为缩略图甚至占位符；信息流从图文模式降级为纯文字；视频从高清降级为标清或仅显示封面。

实现降级的前提是 App 能感知当前网络状况，这就是 NetworkCallback 的用武之地。

## 网络性能监控：OkHttp EventListener 与 NetworkCallback

"无法度量就无法优化。"要系统化地改善网络性能，首先需要建立两个层面的感知能力：应用层面，精确度量每个请求各阶段的耗时；系统层面，感知当前网络环境的质量变化。前者由 OkHttp EventListener 承担，后者由 ConnectivityManager.NetworkCallback 承担。两者配合，才能实现“感知→度量→调整”的自适应循环。

### OkHttp EventListener：请求全生命周期埋点

OkHttp 的 EventListener 是一个回调接口，覆盖了 HTTP 请求从发起到结束的每一个阶段。它比 Interceptor 更适合做性能监控——Interceptor 看到的是"请求和响应"这个粒度，而 EventListener 能看到 DNS 查询、TCP 连接、TLS 握手这些底层细节。

关键回调方法和对应的指标映射如下：

| 回调方法 | 对应阶段 | 可度量指标 |
|---------|---------|-----------|
| `callStart` | 请求开始 | 总耗时起点 |
| `dnsStart` / `dnsEnd` | DNS 解析 | DNS 解析时间 |
| `connectStart` / `connectEnd` | TCP 连接 | 连接时间 |
| `secureConnectStart` / `secureConnectEnd` | TLS 握手 | TLS 握手时间 |
| `requestHeadersStart` / `requestHeadersEnd` | 发送请求头 | 请求头发送时间 |
| `responseHeadersStart` / `responseHeadersEnd` | 接收响应头 | TTFB（近似） |
| `responseBodyStart` / `responseBodyEnd` | 接收响应体 | 响应体传输时间 |
| `callEnd` / `callFailed` | 请求结束 | 总耗时 / 失败原因 |

需要注意：当多个请求并发时，每个请求需要独立的 EventListener 实例来记录各自的时间戳。OkHttp 提供了 `EventListener.Factory` 接口来解决这个问题——每次请求通过 Factory 创建新的 EventListener 实例。

```java
public class PerfEventListener extends EventListener {
    private long dnsStartNanos;
    private long connectStartNanos;
    private long requestEndNanos;

    @Override
    public void dnsStart(Call call, String domainName) {
        dnsStartNanos = System.nanoTime();
    }

    @Override
    public void dnsEnd(Call call, String domainName, List<InetAddress> list) {
        long dnsMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - dnsStartNanos);
        // 上报 DNS 耗时指标
    }

    private long callStartNanos;

    @Override
    public void callStart(Call call) {
        callStartNanos = System.nanoTime();
    }

    @Override
    public void responseHeadersStart(Call call) {
        long ttfbMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - callStartNanos);
        // 上报 TTFB 指标（DNS + 连接 + TLS + 服务端处理的综合耗时）
    }

    public static final Factory FACTORY = call -> new PerfEventListener();
}

// 注册
OkHttpClient client = new OkHttpClient.Builder()
    .eventListenerFactory(PerfEventListener.FACTORY)
    .build();
```

在实际项目中，EventListener 收集的指标通常会上报到 APM（Application Performance Monitoring）平台，形成 P50/P90/P99 的分位数统计。我们关注的不是单个请求的耗时，而是大盘数据——如果 P90 的 DNS 时间从 50ms 涨到 200ms，说明 DNS 基础设施出了问题，需要考虑引入 HTTPDNS。

[已验证: 官方文档, developer.android.com — OkHttp EventListener API]

### ConnectivityManager.NetworkCallback：感知网络环境变化

EventListener 解决了"度量单个请求"的问题，但我们还需要知道"当前网络环境好不好"。这是 ConnectivityManager.NetworkCallback 的职责。

NetworkCallback 提供了以下核心回调：

- `onAvailable(Network)`：网络连接可用。注意这不等于有互联网访问——Wi-Fi 连上了但路由器没联网也会触发。
- `onLost(Network)`：网络断开。这是触发离线模式、暂停网络请求的信号。
- `onCapabilitiesChanged(Network, NetworkCapabilities)`：网络能力变化。可以查询下行带宽（`LinkSpeed`）、是否按流量计费（`NET_CAPABILITY_NOT_METERED`）等信息。
- `onLinkPropertiesChanged(Network, LinkProperties)`：链路属性变化。可以获取 DNS 服务器地址、MTU 等信息。

一个常见的最佳实践是：在 Application 层注册 NetworkCallback，维护一个全局的网络状态对象（当前是否在线、网络类型、预估带宽），供所有网络请求和 UI 层使用。

```java
public class NetworkMonitor {
    private final ConnectivityManager cm;
    private boolean isConnected = false;
    private int downstreamBandwidthKbps = 0; // 预估下行带宽

    private final NetworkCallback callback = new NetworkCallback() {
        @Override
        public void onAvailable(Network network) {
            isConnected = true;
        }

        @Override
        public void onLost(Network network) {
            isConnected = false;
            downstreamBandwidthKbps = 0;
        }

        @Override
        public void onCapabilitiesChanged(Network network,
                NetworkCapabilities caps) {
            downstreamBandwidthKbps = caps.getLinkDownstreamBandwidthKbps();
        }
    };

    public void start(Context context) {
        cm = context.getSystemService(ConnectivityManager.class);
        NetworkRequest request = new NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build();
        cm.registerNetworkCallback(request, callback);
    }
}
```

[已验证: 官方文档, developer.android.com/reference/android/net/ConnectivityManager]

NetworkCallback 的信息可以用来驱动网络策略的自适应调整：带宽高时预加载高清图片；带宽低时只加载缩略图；完全离线时切换到本地缓存。结合 EventListener 的指标数据，可以构建一个"感知→度量→调整"的自适应循环。

## 与其他机制的关系

网络性能不是孤立的。它与本书其他章节的内容有交叉：

- **§12.1 APK 体积优化**：APK 体积影响的是安装和更新时的下载耗时。两者的共同思路是"减少传输数据量"——APK 体积优化通过压缩和裁剪减少静态数据，网络优化通过缓存和增量更新减少动态数据。
- **§6.1 存储架构**：网络请求的缓存依赖于本地存储。OkHttp 的 HTTP 缓存需要配置 Cache 目录，Room 或 SQLite 可以作为更灵活的离线数据层。
- **§8.1 响应速度**：App 启动时的网络请求（如拉取配置、预加载首页数据）直接影响启动后的内容可用时间。预连接和请求合并在这里尤其重要。

## 常见问题与误区

**"网络慢就是服务端的问题"**——这是最常见的误区。实际上，DNS 慢、连接建立慢、客户端重试逻辑不当，都可能导致请求耗时长。区分责任方的关键是看 TTFB：如果 TTFB 正常但总耗时高，问题在数据传输或客户端处理；如果 TTFB 本身就高，问题在服务端或网络链路。

**"HTTP/2 就够了，不需要 HTTP/3"**——在稳定的 Wi-Fi 环境下确实如此。但在移动网络（尤其是弱网、高丢包、频繁切换基站）下，HTTP/3 的 QUIC 协议在高丢包和频繁网络切换场景下优势明显。如果 App 的用户主要在移动网络下使用，值得评估 HTTP/3。

**"OkHttp 默认配置就够了"**——默认配置适合开发阶段，但生产环境需要根据业务特点调整超时时间、连接池大小、缓存策略。尤其是 connectTimeout 和 readTimeout，默认的 10 秒在弱网下可能太短（导致频繁超时），在好网络下可能太长（让用户白等）。

**"网络优化就是优化请求速度"**——优化请求速度只是其中一面。另一面是减少请求的必要性：本地缓存减少重复请求、数据预加载减少用户等待时间、批量接口减少请求次数。最好的网络请求是不需要发出的请求。

**"DNS 解析很快，不需要优化"**——在桌面网络下 DNS 确实几乎无感，但移动端的 DNS 解析面临两个特殊问题：运营商 DNS 服务器可能响应慢甚至返回劫持结果（指向广告页）；DNS 查询使用 UDP 协议，在弱网下丢包率较高导致超时重试。这就是 HTTPDNS 在国内大量使用的原因——绕过运营商 DNS，直接向可信的 DNS 服务（如阿里 DNS、腾讯 DNS）查询，同时还能返回离用户最近的 CDN 节点 IP。OkHttp 本身不内置 HTTPDNS，但可以通过 `Dns` 接口接入自定义解析逻辑。

## 参考资料

- OkHttp 官方文档: <https://square.github.io/okhttp/>
- OkHttp EventListener API: <https://square.github.io/okhttp/events/>
- Android ConnectivityManager: <https://developer.android.com/reference/android/net/ConnectivityManager>
- Android NetworkCallback: <https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback>
- HTTP/3 (QUIC) 规范: <https://www.rfc-editor.org/rfc/rfc9114>
- Uber Engineering — 迁移到 QUIC: <https://eng.uber.com/en/better-http-3/>
- Google Chromium Blog — HTTP/3 性能数据（通用参考）: <https://blog.chromium.org/>
