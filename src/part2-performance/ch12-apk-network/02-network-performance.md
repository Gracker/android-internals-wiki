---
title: "网络性能优化"
chapter: 12.2
section: '12.2'
status: ready-for-review
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
reviewed_date: "2026-04-29"
polish_count: 1
polish_date: '2026-04-10'
polish_by: task2b-polish
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: revisiting
task9_state: pending
task2b_state: fixed
task2b_result: fixed
task9_result: needs-rework
task9_reviewed_date: '2026-05-22'
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-22T18:30:26+08:00"
pipeline_stage: task6_pending
applicable_versions: Android 8 (API 26) - Android 16 (API 36)
last_verified: '2026-04-03'
last_verified_against: OkHttp 4.12.x / Android 16
confidence: medium
sources:
- type: official
  path: https://developer.android.com/reference/android/net/ConnectivityManager
- type: official
  path: https://square.github.io/okhttp/
- type: official
  path: https://developer.android.com/training/basics/network-ops
tags:
- network
- OkHttp
- HTTP/2
- HTTP/3
- QUIC
- weak-network
- performance
related_chapters:
- '12.1'
- '6.1'
- '8.1'
last_task9_audit: '2026-05-20'
last_task6_audit: '2026-05-22'
last_task2b_at: "2026-05-28T04:50:00+08:00"
last_task2b_source: "frontmatter-fallback/task9-deep-tech-review"
last_task2b_note: "修复 OkHttp EventListener 文档锚点、Cronet 0-RTT 配置边界、16KB Cronet 冷启动无来源百分比、NetworkCapabilities 带宽估算 Android 16/eBPF 口径。"
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

网络性能与本地性能有一个关键区别：**它不可控**。本地渲染管线的耗时主要由 App 自身代码决定，但网络请求的耗时取决于运营商、基站信号、DNS 服务器、CDN 节点、服务器负载等一系列不可控因素。正因如此，网络性能优化的核心思路不是"消除延迟"，而是**减少可控环节的延迟、增强对不可控因素的容错能力**。

面对一个"网络慢"的用户反馈，判断路径通常从请求全生命周期开始：先区分 DNS、连接、TTFB 和传输耗时，再看协议选择、请求组织、弱网容错和监控体系。这样才能快速判断问题落在 DNS、连接还是服务端处理，并确认代码层面还能优化哪些环节。

## 网络性能指标：一次请求的时间分解

一个 HTTP 请求从发起到收到完整响应，可以拆分为若干个阶段，每个阶段的耗时对应一个独立的性能指标。理解这些指标，是我们定位网络瓶颈的基础。

一次完整的 HTTP 请求时间线大致如下：

```text
DNS 查询 → TCP 连接 → TLS 握手 → 发送请求头 → 发送请求体 →
等待服务端处理 → 收到第一个响应字节 → 接收完整响应体
```

对应的关键指标有三个：

**DNS 解析时间（DNS Time）**：从发起域名解析到获得 IP 地址的耗时。在移动网络下，DNS 解析通常是第一个瓶颈。本地 DNS 缓存可以缓解，但首次请求或缓存过期后的 DNS 查询可能需要 20-200ms，在极端情况下（如运营商 DNS 不可用）甚至超过数秒。

**连接时间（Connect Time）**：从开始建立 TCP 连接到连接就绪的耗时。如果使用 HTTPS（现在几乎所有请求都是），这里还包含 TLS 握手的时间。连接时间通常在 50-200ms 之间，但如果服务器物理距离远或网络拥堵，可能翻倍。

**首字节时间（Time To First Byte, TTFB）**：从发送请求到收到服务端返回的第一个字节的时间。这个指标反映了服务端处理速度和网络往返延迟的综合影响。TTFB 是判断"问题在客户端还是服务端"的关键分水岭——如果 DNS 和连接都很快但 TTFB 高，问题几乎一定在服务端。

为什么这三个指标如此重要？因为它们各自对应不同的优化方向。DNS 慢 → 用 DNS 预解析或 HTTPDNS；连接慢 → 用连接复用或预连接；TTFB 慢 → 优化服务端或用 CDN。如果我们在做性能优化时不拆分指标，只是简单地看到"请求花了 2 秒"，就无从下手。

[已验证: Square OkHttp EventListener 官方文档 / Android ConnectivityManager 官方文档]

### 传输速率

除了时间指标，传输速率（Throughput）也是网络性能的重要维度。它表示单位时间内传输的数据量，通常以 Mbps 或 MB/s 衡量。传输速率受带宽、网络拥塞、数据包大小等因素影响。

在实际优化中，传输速率主要影响大文件下载和上传场景（图片、视频、APK 更新包等）。对于常规的 API 请求（通常几 KB 到几十 KB），传输速率的影响远小于 DNS 和连接时间。这也是为什么网络优化的重心通常放在"减少请求次数"和"缩短连接建立时间"上，而不是"提升带宽利用率"。

## HTTP/2 与 HTTP/3(QUIC)：协议选择对性能的影响

网络请求的底层协议决定了连接复用、头部压缩、丢包恢复等基础能力的上限。OkHttp 从 4.x 版本开始默认支持 HTTP/2（API 21+），而 HTTP/3（基于 QUIC）则需要通过 Cronet 等库引入。两者在移动场景下的性能差异，是我们选择技术方案的重要依据。

### HTTP/2：多路复用解决了 HTTP/1.1 的队头阻塞

HTTP/1.1 时代，浏览器通常会对同一域名的并发连接数做策略性限制，常见值是 6 左右。这个经验值来自浏览器实现，不是 HTTP/1.1 协议写死的上限。Android App 侧用 OkHttp 时，并发行为主要受 `Dispatcher`、`ConnectionPool` 和协议协商结果影响。以异步请求为例，OkHttp 默认用 `Dispatcher.maxRequestsPerHost()` 控制同一 host 的并发上限，默认值是 5；如果已经协商到 HTTP/2，同一连接上的多个 stream 又会改变排队方式。

HTTP/2 通过**多路复用**（Multiplexing）解决了这个问题。在 HTTP/2 下，一个 TCP 连接可以同时承载多个请求和响应，每个请求被分配一个独立的 Stream ID，数据被拆分为 Frame 在同一连接上交错传输。此外，HTTP/2 引入了 **HPACK 头部压缩**，减少了重复 Header 的传输开销。

在 Perfetto 中，如果 App 使用 HTTP/2，我们会看到 TCP 连接数量显著减少——多个请求共享同一个连接，而不是每个请求独占一个。这对移动网络特别有利，因为每次新建 TCP 连接都需要经历三次握手（加上 TLS 握手），在弱网环境下每次新建连接的 TLS 握手开销可能达到 100-200ms。

但 HTTP/2 并非完美。它解决了应用层的队头阻塞，却把问题推到了传输层——TCP 层仍然存在队头阻塞：如果一个 TCP 包丢失，该连接上所有 Stream 的数据传输都会被阻塞，直到丢包被重传。在高丢包率的移动网络下，这个问题尤为突出。

### HTTP/3(QUIC)：为移动网络设计的传输协议

HTTP/3 使用 QUIC 作为传输层协议，而 QUIC 基于 UDP 实现。这个架构变更带来了几个对移动网络场景尤为关键的改进：

**零/一次 RTT 连接建立**：QUIC 将传输层握手和 TLS 1.3 加密握手合并为一次交互。首次连接只需 1-RTT，后续连接可以利用保存的会话信息实现 0-RTT，即第一个包就可以携带请求数据。在移动网络下，一个 RTT 可能是 50-100ms，省掉一次往返意味着白屏时间直接减少 50-100ms。

> **⚠️ 0-RTT 安全边界**：0-RTT 数据不具备前向安全性（Forward Secrecy），且易受重放攻击（Replay Attack）（RFC 9001 §9.2）。业务层必须确保通过 0-RTT 发送的请求是幂等的（如 GET、PUT），或者携带服务端幂等键（Idempotency Key）来防止重复执行。对非幂等请求（POST、PATCH），应在 QUIC 配置中显式禁用 0-RTT，或在应用层降级到 1-RTT 发送。Cronet 的 `QuicOptions.Builder.addAllowedQuicHost()` 只负责 QUIC host allowlist；0-RTT 还要结合 `enableTlsZeroRtt(boolean)`、HTTP disk cache / session state 和服务端 replay 防护一起配置。

**独立的 Stream 丢包恢复**：QUIC 在自己的传输层实现了多路复用，每个 Stream 的丢包重传互不影响。一个 Stream 丢包不会阻塞其他 Stream 的数据传输——这正是 HTTP/2 over TCP 最大的薄弱环节。

**连接迁移**：QUIC 使用 Connection ID 而不是四元组（源 IP、源端口、目标 IP、目标端口）来标识连接。当用户的网络从 Wi-Fi 切换到 4G/5G 时（IP 地址改变），QUIC 连接可以无缝迁移，不需要重新建立连接。在 HTTP/2 下，这种网络切换会导致所有正在进行的请求失败并需要重试。

实际性能数据也印证了 HTTP/3 在移动场景下的优势。Google 报告 YouTube 在移动设备上缓冲时间减少了 15%；Uber 在 Android/iOS 上采用 QUIC 后尾部延迟降低了 10-30%；Meta 在 Instagram 上观察到请求错误率降低 6%、尾部延迟降低 20%。 [已验证: 来源见 Uber Engineering Blog (eng.uber.com), Google Chromium Blog]

### 在 Android 上的选择

在 Android 开发中，接入 HTTP/3 前要先选 Cronet 的 provider 形态。对有 GMS 的设备，`Cronet by Play Services` 是默认优先项，App 侧引入的是一层很薄的 Java 依赖，APK 增量通常是几十 KB，Cronet 内核跟随 Google Play services 更新。对无 GMS 设备，或者业务要求固定 Cronet 版本、离线也必须可用的产品，常见做法是打包 standalone 或 bundled provider，这时成本会变成数 MB 级的 native 库体积，以及随 APK 一起发布和回滚的运维成本。

因此，“引入 Cronet 会让 APK 增加 1-2MB”不是通用结论。体积、更新路径和可用性要分开看。GMS 设备更看重 provider 是否已经安装、版本是否满足要求；非 GMS 设备更看重包体积、ABI 覆盖和发布节奏。生产实践里通常会先探测 Play Services provider，可用时优先走 Cronet；探测失败时回退到 bundled Cronet 或 OkHttp/HTTP/2。这样才能把性能收益、包体积和设备覆盖率放在同一个决策框架里。

16KB 分页对 Cronet 冷启动的影响要按 provider 与设备实测。`libcronet.so` 是大型 native 库，4KB 分页下页表条目更多，page fault 与重定位成本更容易出现在冷启动路径；16KB page size 可能降低页表项数量和部分 fault 成本，但不能直接推出固定百分比收益。若要把 Cronet 初始化放进启动阶段的预连接策略，建议用同一设备、同一 ABI、同一 Cronet provider 版本，对比 4KB / 16KB 环境下 `dlopen`、provider install、首次请求发出三个时间点。

[已验证: Android Developers Cronet 文档 / Google Play services CronetProviderInstaller]

## 网络请求优化：连接复用、请求合并与预连接

协议层能力决定连接层上限，应用层能直接控制的是三类优化：连接复用、请求合并、预连接。它们共同减少网络请求的"固定开销"——即与数据传输量无关，只要发起请求就必然产生的那部分延迟。

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

OkHttp 默认的 ConnectionPool 配置是：最多 5 个空闲连接，每个连接保持存活 5 分钟。在 5 分钟内有新请求到同一地址，可以直接复用连接——在移动端频繁切换页面的场景下，这个时间窗口足够覆盖大部分复用机会。

[已验证: OkHttp 官方文档, square.github.io/okhttp/connections/]

### 请求合并：把多次往返变成一次

请求合并（Request Batching）的思路是：如果能一次请求拿到所有数据，就不要分成多次请求。这在 API 设计层面就需要考虑。

典型场景是一个页面需要多个接口的数据。如果串行请求三个接口，总耗时 = 请求1 + 请求2 + 请求3。但如果后端提供一个聚合接口，一次请求返回所有数据，总耗时 ≈ 单次请求耗时（数据量略大但传输时间远小于减少的往返次数）。

在不修改后端 API 的情况下，OkHttp 的 HTTP/2 多路复用可以自动并行发送多个请求到同一服务器，省去串行等待。但注意：减少请求次数的效果通常大于并行化——并行化只减少了等待时间，而合并请求直接减少了 RTT 数量。

### 预连接：在需要之前就准备好

预连接（Preconnect）的目标可以分成三层。第一层是 DNS 预解析，只把域名解析成 IP，减少后续请求的 lookup 开销。第二层是预热 TCP + TLS，让真实请求直接复用已经握手完成的连接。第三层是预热 HTTP/2 或 HTTP/3 会话，让首个业务请求尽量避开 stream 建立、控制帧交换或 QUIC 会话恢复的冷启动成本。三层目标对应的收益和约束不同，设计时要分开看。

工程上常见的做法是用 HEAD 或 no-op GET 主动触发连接建立，但它只是 warmup 手段，不是语义保证。HEAD 仍可能命中业务逻辑、鉴权流程、缓存统计或 WAF。后续请求能否复用这条连接，还取决于是否命中同一个 authority（scheme + host + port）、证书与 SNI 是否匹配、ALPN 是否协商到同一协议，以及 HTTP/2 connection coalescing 或 HTTP/3 session reuse 条件是否成立。

更稳妥的做法是为预热准备一个 no-op endpoint，例如 `/generate_204`、`/healthz` 或专门的 warmup path，并把失败视为可静默回退的优化，不要把它做成功能前提。

```java
public final class PreconnectManager {
    private final OkHttpClient client;

    public PreconnectManager(OkHttpClient client) {
        this.client = client;
    }

    public void warmUp(String url) {
        Request request = new Request.Builder()
            .url(url) // 建议指向 no-op endpoint，且与真实请求同 authority
            .head()
            .build();

        client.newCall(request).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {
                // 预热失败时静默回退，真实请求仍按正常路径发起
            }

            @Override public void onResponse(Call call, Response response) {
                response.close();
            }
        });
    }
}
```

如果业务要覆盖 HTTP/3，还要额外验证 QUIC provider 是否可用、会话恢复是否命中，以及网络切换后连接迁移是否稳定。App 启动阶段不要为了“预连接”再额外制造一条关键路径，弱网下 warmup 本身也可能拖慢首屏。

[已验证: OkHttp 连接复用文档 / Cronet 官方说明]


### 网络线程的能效分档

Android 15 在 ADPF（Adaptive Performance Framework）的 `PerformanceHintManager.Session` 中新增了 `setPreferPowerEfficiency(boolean)` 方法，用于向系统声明线程组的能效偏好。声明了 `true` 的 session，调度器在满足目标帧时间的前提下会优先选择能效更高的调度策略（如分配到低功耗核心、降低频率目标）。不声明时，ADPF 默认按性能优先处理。

两类网络线程应该分开配置：

- **交互式网络线程**：用户正在等待结果（列表加载、搜索请求）。这类线程需要低延迟，不应声明能效偏好，保持默认的响应优先级调度。
- **能效式网络线程**：用户不感知的后台任务（日志上报、数据同步、预加载）。这类线程声明能效偏好后，系统可以在节能模式下执行，避免一个 200ms 的 TCP 超时把大核唤醒并拉高频率。

2026 年的网络层设计，应把"显式声明能效偏好"作为后台网络任务的准入指标。不声明的代价是后台日志上报把大核唤醒、CPU 频率拉高，电池消耗在等一个本可以用 LITTLE 核处理完的请求上。

## 弱网优化策略：超时、重试与降级

移动网络的不确定性远高于固定网络——电梯里信号突然消失、高铁上频繁切换基站、地下室完全无信号。弱网优化的目标是**让 App 在网络很差时依然可用或至少优雅降级**。

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

**本地缓存**：OkHttp 默认遵守 HTTP 缓存语义。服务端返回了合适的 `Cache-Control`、`Expires`、`ETag` 等头部后，客户端才会自动复用缓存；缓存过期后，默认行为是重新验证或回源，不会因为当前离线就无条件返回 stale response。离线读缓存通常有三种做法：请求侧显式使用 `CacheControl.FORCE_CACHE`，或 `onlyIfCached()` 配合 `maxStale()` 接受一定范围内的过期数据，或在离线拦截器里主动放宽缓存策略。如果本地没有可用缓存，`FORCE_CACHE` 和 `onlyIfCached()` 会直接返回 504 `Unsatisfiable Request`，不会自动联网。

**功能降级**：对非核心功能，在网络差时主动降级。例如：图片加载从原图降级为缩略图甚至占位符；信息流从图文模式降级为纯文字；视频从高清降级为标清或仅显示封面。

实现降级的前提是 App 能感知当前网络状况，这就是 NetworkCallback 的用武之地。

## 网络性能监控：OkHttp EventListener 与 NetworkCallback

"无法度量就无法优化。"要系统化地改善网络性能，需要建立两个层面的感知能力：应用层面，精确度量每个请求各阶段的耗时；系统层面，感知当前网络环境的质量变化。前者由 OkHttp EventListener 承担，后者由 ConnectivityManager.NetworkCallback 承担。两者配合，才能实现“感知→度量→调整”的自适应循环。

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

[已验证: Square OkHttp EventListener 官方文档]

### ConnectivityManager.NetworkCallback：感知网络环境变化

EventListener 解决的是单次请求的拆账问题，NetworkCallback 解决的是当前网络环境发生了什么。但这里至少有四层语义要拆开：有没有网络、有没有经过系统验证的公网访问、系统给出的网络能力估计值、请求实际跑出来的吞吐与时延。把这四层压成一个 `isConnected` 布尔值，后续的重试、降级和预加载策略很容易跑偏。

NetworkCallback 提供的几个回调里，语义最容易混淆的是 `onAvailable()` 和 `onCapabilitiesChanged()`：

- `onAvailable(Network)`：系统拿到了一条可用网络。它说明 transport 已经可用，不说明这条网络一定能访问公网。
- `onCapabilitiesChanged(Network, NetworkCapabilities)`：网络能力发生变化。在线判定、是否 metered、系统估计的上下行带宽，都应该在这里读取。
- `onLost(Network)`：当前网络失效，可以触发离线模式或暂停非关键请求。
- `onLinkPropertiesChanged(Network, LinkProperties)`：DNS、MTU、路由等网络属性变化。

在 Application 层维护全局网络状态时，`onAvailable()` 适合记录“有网络对象出现了”，“在线”判定要放到 `onCapabilitiesChanged()`，同时检查 `NET_CAPABILITY_INTERNET` 和 `NET_CAPABILITY_VALIDATED`。`getLinkDownstreamBandwidthKbps()` 也只能当系统估计值，用来做粗粒度分档，不能把它当成真实吞吐。

```java
public final class NetworkMonitor {
    private final ConnectivityManager cm;
    private volatile boolean hasValidatedInternet = false;
    private volatile int estimatedDownstreamKbps = 0;

    public NetworkMonitor(Context context) {
        cm = context.getSystemService(ConnectivityManager.class);
    }

    private final ConnectivityManager.NetworkCallback callback =
            new ConnectivityManager.NetworkCallback() {
        @Override
        public void onAvailable(Network network) {
            // 这里只表示网络可用，先不要宣布“已经联网”
        }

        @Override
        public void onCapabilitiesChanged(
                Network network, NetworkCapabilities caps) {
            boolean internet = caps.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_INTERNET);
            boolean validated = caps.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_VALIDATED);
            hasValidatedInternet = internet && validated;
            estimatedDownstreamKbps =
                    caps.getLinkDownstreamBandwidthKbps();
        }

        @Override
        public void onLost(Network network) {
            hasValidatedInternet = false;
            estimatedDownstreamKbps = 0;
        }
    };

    public void start() {
        cm.registerDefaultNetworkCallback(callback);
    }
}
```


`getLinkDownstreamBandwidthKbps()` 返回的是系统估算值，公开文档只承诺它表示 first-hop transport 的估计下行带宽。它适合做粗粒度分档，例如是否预加载大图、是否进入低码率模式；不适合当成真实吞吐或 RTT 判断。Android 16 公开文档没有说明该 API 已改由 eBPF 实测统计提供，也没有给出可依赖的精度变化。

这段代码给的是策略输入，不是最终网络质量结论。网络是否真的“快”，还要结合 EventListener 里的 DNS、connect、TTFB 和响应体传输时间一起看。`NET_CAPABILITY_VALIDATED` 为 true 只能说明系统探测到这条网络能访问公网；`getLinkDownstreamBandwidthKbps()` 很高，也不代表当前请求就一定能跑到这个速率。

[已验证: Android ConnectivityManager / NetworkCapabilities 官方文档]

## 与其他机制的关系

网络性能不是孤立的。它与本书其他章节的内容有交叉：

- **§12.1 APK 体积优化**：APK 体积影响的是安装和更新时的下载耗时。两者的共同思路是"减少传输数据量"——APK 体积优化通过压缩和裁剪减少静态数据，网络优化通过缓存和增量更新减少动态数据。
- **§6.1 存储架构**：网络请求的缓存依赖于本地存储。OkHttp 的 HTTP 缓存需要配置 Cache 目录，Room 或 SQLite 可以作为更灵活的离线数据层。
- **§8.1 响应速度**：App 启动时的网络请求（如拉取配置、预加载首页数据）直接影响启动后的内容可用时间。预连接和请求合并在这里尤其重要。

## 常见问题与误区

**"网络慢就是服务端的问题"**——这是最常见的误区。DNS 慢、连接建立慢、客户端重试逻辑不当，都可能导致请求耗时长。区分责任方要看 TTFB：如果 TTFB 正常但总耗时高，问题在数据传输或客户端处理；如果 TTFB 本身就高，问题在服务端或网络路径。

**"HTTP/2 就够了，不需要 HTTP/3"**——在稳定的 Wi-Fi 环境下通常成立。但在移动网络（尤其是弱网、高丢包、频繁切换基站）下，HTTP/3 的 QUIC 协议在高丢包和频繁网络切换场景下优势明显。如果 App 的用户主要在移动网络下使用，值得评估 HTTP/3。

**"OkHttp 默认配置就够了"**——默认配置适合开发阶段，但生产环境需要根据业务特点调整超时时间、连接池大小、缓存策略。尤其是 connectTimeout 和 readTimeout，默认的 10 秒在弱网下可能太短（导致频繁超时），在好网络下可能太长（让用户白等）。

**"网络优化就是优化请求速度"**——优化请求速度只是其中一面。另一面是减少请求的必要性：本地缓存减少重复请求、数据预加载减少用户等待时间、批量接口减少请求次数。最好的网络请求是不需要发出的请求。

**"DNS 解析很快，不需要优化"**——在桌面网络下 DNS 通常几乎无感，但移动端的 DNS 解析面临两个特殊问题：运营商 DNS 服务器可能响应慢甚至返回劫持结果（指向广告页）；DNS 查询使用 UDP 协议，在弱网下丢包率较高导致超时重试。这就是 HTTPDNS 在国内大量使用的原因——绕过运营商 DNS，直接向可信的 DNS 服务（如阿里 DNS、腾讯 DNS）查询，同时还能返回离用户最近的 CDN 节点 IP。OkHttp 本身不内置 HTTPDNS，但可以通过 `Dns` 接口接入自定义解析逻辑。

## 参考资料

- OkHttp 官方文档: <https://square.github.io/okhttp/>
- OkHttp EventListener API: <https://square.github.io/okhttp/events/>
- Android ConnectivityManager: <https://developer.android.com/reference/android/net/ConnectivityManager>
- Android NetworkCallback: <https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback>
- HTTP/3 (QUIC) 规范: <https://www.rfc-editor.org/rfc/rfc9114>
- Uber Engineering — 迁移到 QUIC: <https://eng.uber.com/en/better-http-3/>
- Google Chromium Blog — HTTP/3 性能数据（通用参考）: <https://blog.chromium.org/>
