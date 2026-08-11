---
title: "网络性能优化"
chapter: "12.1"
section: '12.1'
status: finalized
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
reviewed_date: "2026-05-28"
polish_count: 1
polish_date: '2026-04-10'
polish_by: task2b-polish
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: fixed
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-05-28"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-28T06:28:00+08:00"
pipeline_stage: ready-to-publish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-08-11'
last_verified_against: 'AOSP android-17.0.0_r1；Android 17 / API 37；OkHttp 5.3.0；Cronet Play services 18.0.1；HTTP/2、HTTP/3 与 QUIC RFC（2026-07）'
confidence: high
sources:
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/reading-network-state
- type: official
  path: https://developer.android.com/reference/android/net/ConnectivityManager
- type: official
  path: https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback
- type: official
  path: https://developer.android.com/reference/android/net/NetworkCapabilities
- type: official
  path: https://developer.android.com/develop/connectivity/cronet
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/start
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/CronetEngine.Builder
- type: official
  path: https://developer.android.com/reference/android/net/http/HttpEngine.Builder
- type: official
  path: https://developer.android.com/reference/androidx/tracing/Trace
- type: official
  path: https://developer.android.com/reference/android/telephony/SubscriptionInfo
- type: official
  path: https://developer.android.com/privacy-and-security/local-network-permission
- type: source
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/README.md
- type: source
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt
- type: source
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ConnectionPool.kt
- type: source
  path: https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt
- type: rfc
  path: https://www.rfc-editor.org/rfc/rfc9113
- type: rfc
  path: https://www.rfc-editor.org/rfc/rfc9114
- type: rfc
  path: https://www.rfc-editor.org/rfc/rfc9000
- type: rfc
  path: https://www.rfc-editor.org/rfc/rfc9001
- type: aosp
  path: packages/modules/Connectivity/framework/src/android/net/ConnectivityManager.java
- type: aosp
  path: packages/modules/Connectivity/framework/src/android/net/NetworkCapabilities.java
- type: aosp
  path: packages/modules/Connectivity/service/src/com/android/server/ConnectivityService.java
- type: aosp
  path: packages/modules/NetworkStack/src/com/android/server/connectivity/NetworkMonitor.java
- type: aosp
  path: frameworks/base/telephony/java/android/telephony/SubscriptionInfo.java
- type: aosp
  path: libcore/luni/src/main/java/libcore/io/BlockGuardOs.java
tags:
- network
- OkHttp
- HTTP/2
- HTTP/3
- QUIC
- weak-network
- performance
related_chapters:
- '12.2'
- '12.3'
- '1.62'
- '24.4'
- '24.5'
- '8.1'
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part2-performance/ch12-apk-network/03-network-performance-deep.md"
last_task9_audit: '2026-07-03'
last_task6_audit: "2026-06-22"
last_task2b_at: "2026-05-28T04:50:00+08:00"
last_task2b_source: "frontmatter-fallback/task9-deep-tech-review"
last_task2b_note: "修复 OkHttp EventListener 文档锚点、Cronet 0-RTT 配置边界、16KB Cronet 冷启动无来源百分比、NetworkCapabilities 带宽估算 Android 16/eBPF 口径。"
last_task6_at: "2026-05-28T06:11:00+08:00"
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-05-28T06:11:00+08:00"
last_task6_review_log: "logs/review/2026-05-28-06-review.md"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-28 05 Task6 revisiting-review: pass-light-edit；L1/L2 小修 1 处（补齐正文 H1 章节号）；outline 5/5 覆盖；无 L3/L4 回炉项。Task9 result 仍为 needs-rework，Task2B 已 fixed，送 Task9 复审。 | 2026-05-28 06 Task6 revisiting-review: pass-light-edit；L1/L2 小修 0 处；outline 5/5 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，未满足 pass-tech-review 自动晋升条件，送 Task9 复核。"
last_task9_autofix_at: "2026-05-28"
last_task9_review_log: "logs/deep-review/2026-05-28-06-deep-review.md"
p0: 0
p1: 0
p2: 0
task9_review_notes: "2026-05-28 Task9 auto-fix: 修正 OkHttp EventListener connect/TTFB 指标口径，并收窄 ADPF setPreferPowerEfficiency 调度语义，回到 Task6 复审。 | 2026-05-28 06 Task9复审: pass-tech-review；无 P0/P1/P2；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-06
---
# 12.1 网络性能优化

一次接口调用的等待时间分散在客户端排队、域名解析、路由尝试、建连、加密握手、上传、边缘节点、服务端、响应传输、解析和界面更新中。“接口耗时 2 秒”只给出了结果，无法指出哪一段消耗了时间。

移动网络持续变化，客户端仍然可以控制请求时机、复用、总期限、缓存、重试和内容降级。优化工作的起点是统一计时口径，然后按协议、请求组织和网络状态选择策略。

基准版本为 Android 17 / API 37、AOSP `android-17.0.0_r1`、OkHttp 5.3.0 和 Play services Cronet 18.0.1。`netd` 与 DNS Resolver 的内部细节见 12.3，系统选网与 `NetworkAgent` 见 1.62。

## 应用网络栈和主线程边界

Android 应用常见的 HTTP 路径不能合写成一条调用栈：OkHttp 自己管理连接池，TCP 通常经 `java.net.Socket`，TLS 经平台 JSSE/Conscrypt；Cronet 使用 Chromium native 网络栈；API 34 起的 `HttpEngine` 使用设备提供的实现。HTTP/3/QUIC 状态机位于 Cronet/HttpEngine 的用户空间 provider，内核只看到 UDP/IP/socket，OkHttp 5.3.0 则没有稳定公开的 HTTP/3 配置入口。

主线程禁网也要区分“直接发起网络”与“等待后台网络”。Android 17 的 `Inet6AddressImpl` 在 DNS 缓存检查前调用 `BlockGuard.getThreadPolicy().onNetwork()`，`BlockGuardOs` 还覆盖 connect、阻塞 poll 与 recvmsg 等入口；JNI 直接 I/O 可能避开部分检测。`Future.get()`、`CountDownLatch.await()` 或 `runBlocking` 虽不会抛 `NetworkOnMainThreadException`，仍会让 UI 等待后台请求并造成卡顿或 ANR。

## 一次请求应当怎样计时

常规非双工请求可以按下面的顺序观察：

```text
enqueue / execute
  → Dispatcher 排队
  → 代理选择与 DNS
  → 路由尝试
  → TCP + TLS，或 QUIC + TLS
  → 请求头与请求体
  → 响应头
  → 响应体
  → 反序列化、业务处理与界面更新
```

缓存命中或连接复用会跳过若干阶段，重定向、认证、路由回退和重试又可能让某些阶段出现多次。双工请求还允许请求体与响应交错，因此监控系统要保存事件序列，不能假定每种事件只出现一次。

### 需要分开的指标

| 指标 | 建议边界 | 能回答的疑问 |
|---|---|---|
| Call 总耗时 | `callStart` 到 `callEnd` / `callFailed` | 用户发起的单次 `Call` 在网络库内停留多久 |
| Dispatcher 排队 | `dispatcherQueueStart` 到 `dispatcherQueueEnd` | 并发上限或线程资源是否造成客户端等待 |
| DNS | 每组 `dnsStart` 到 `dnsEnd` | 域名解析、缓存和重定向域名是否消耗时间 |
| TCP 建连 | `connectStart` 到 `secureConnectStart`，无 TLS 时到 `connectEnd` | Socket 建连和路由尝试是否缓慢 |
| TLS | `secureConnectStart` 到 `secureConnectEnd` | 加密握手与证书处理消耗多少时间 |
| 请求发送 | `requestHeadersStart` 到 `requestBodyEnd`，无请求体时到 `requestHeadersEnd` | 上传或请求体生产是否缓慢 |
| 响应头等待 | 请求发送结束到 `responseHeadersStart` | 网络往返、边缘节点和服务端共同造成的等待 |
| 响应体传输 | `responseBodyStart` 到 `responseBodyEnd` | 下载和应用读取速度是否偏低 |
| 内容可用时间 | 业务发起到数据可展示 | 网络、解析、数据库和 UI 的整体结果 |

OkHttp 5.3.0 的 `callStart` 在调用 `enqueue()` 或 `execute()` 后触发。若请求因 Dispatcher 或 HTTP/2 stream 资源不足而等待，`dispatcherQueueStart` / `dispatcherQueueEnd` 可以直接记录这段时间。相关约束写在 5.3.0 的 [`EventListener.kt`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt) 中。

### TTFB 不是服务端耗时

“首字节时间”在不同平台可能采用不同起点。客户端常见的两种口径是：

- `callStart` 到 `responseHeadersStart`：包含排队、DNS、连接、握手、上传和等待响应，接近用户等待响应头的时间。
- 请求发送结束到 `responseHeadersStart`：排除了前置阶段，但仍包含网络往返、代理、CDN、服务端排队与处理。

因此，TTFB 高不能单独证明服务端慢。服务端 trace、`Server-Timing`、CDN cache 状态和客户端分段计时一起使用，才能缩小范围。对响应头和响应体之间的边界也要保持一致；OkHttp 的 `responseHeadersStart` 表示开始读取响应头，并不等同于业务已经拿到可展示数据。

### 传输速率的口径

传输速率适合大响应、上传和媒体流。计算时至少记录：

- 有效载荷字节数与计时边界；
- 内容编码，例如 gzip、Brotli；
- 是否命中 HTTP cache；
- 应用是否因消费响应过慢产生 backpressure；
- 协议、网络 transport、是否 metered、是否 roaming；
- 中断、续传和重试字节。

`NetworkCapabilities.getLinkDownstreamBandwidthKbps()` 返回系统估计的**第一跳 transport 带宽**，不能代替请求吞吐。Wi‑Fi、蜂窝、VPN 也不能直接映射成“快”“慢”。

## HTTP/1.1、HTTP/2 与 HTTP/3

| 能力 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| 传输 | TCP | TCP | QUIC over UDP |
| 加密 | 可选；Android 业务通常使用 TLS | HTTPS 场景使用 TLS | TLS 1.3 集成在 QUIC 握手中 |
| 同连接并发 | 常规实现中一条连接一次处理一个请求 | 多个 stream 复用一条连接 | 多个 QUIC stream 复用一条连接 |
| 头部压缩 | 无协议级动态压缩 | HPACK | QPACK |
| 丢包影响 | 该 TCP 连接等待缺失字节 | 同一 TCP 连接上的 stream 都受传输层顺序约束 | 丢失数据所属 stream 等待重传；共享拥塞控制仍会影响整条连接 |
| 网络迁移 | 通常重建连接 | 通常重建连接 | 协议具备 Connection ID 与路径验证能力，能否迁移取决于实现和服务端 |

HTTP/2 去掉了 HTTP/1.1 在应用层组织并发时对多连接的依赖，并通过 multiplexing 与 HPACK 降低重复开销。TCP 仍按字节序交付，一段数据丢失后，后续字节要等待重传。服务端的最大并发 stream、优先级实现和单连接拥塞也会影响结果。

HTTP/3 把 HTTP 映射到 QUIC stream。某个 stream 丢失的数据不会要求其他 stream 等待同一字节序列，但连接级拥塞窗口、设备 CPU、服务器调度和 UDP 路径仍是公共资源。“有丢包便一定更快”不成立。

### 0-RTT 的边界

QUIC 恢复连接时可能发送 TLS early data，从而减少一次往返。它需要已有会话状态、客户端允许、服务端接受并保留相应配置。服务端可以拒绝 early data，客户端随后按正常握手继续，因此 0-RTT 不能写进功能正确性的前提。

Early data 可能被重放，安全属性也弱于新握手后的 1-RTT 数据。业务只能发送能够容忍重放的操作。支付、发帖、创建订单等操作需要等待握手完成，或采用服务端幂等键、去重记录和明确的重放策略。HTTP 方法名只能作为线索，不能代替业务语义审计。

Cronet 的 `QuicOptions.Builder.enableTlsZeroRtt()` 控制 TLS 0-RTT；`addAllowedQuicHost()` 只配置 QUIC host allowlist。跨进程会话恢复还与磁盘 cache、provider 和服务端状态有关。

### 连接迁移也有条件

QUIC Connection ID 允许连接在 IP 或端口变化后通过新路径继续。Cronet 还提供 `ConnectionMigrationOptions`。迁移能否成功取决于 provider 配置、服务器支持、路径验证、NAT、VPN 和中间网络，切换 Wi‑Fi 与蜂窝时仍可能出现请求失败。业务层保留取消、重试和幂等处理，不能把迁移理解成无条件无感切换。

### Android 上怎样使用 HTTP/3

OkHttp 5.3.0 的稳定协议栈覆盖 HTTP/1.1 与 HTTP/2。需要 HTTP/3 时，可以评估 Cronet。当前 Android 官方接入使用下面的 Play services 依赖：

```kotlin
dependencies {
    implementation("com.google.android.gms:play-services-cronet:18.0.1")
}
```

构造 `CronetEngine` 前要调用 `CronetProviderInstaller.installProvider(Context)`，并处理 Play services 缺失、需要更新或安装失败。官方 `cronet-fallback` 是能力较弱的 Java fallback，不能预设它与 native Cronet 具有相同的 HTTP/3、性能和连接迁移表现。

一个进程通常只创建一个 `CronetEngine`。多个 engine 不能并发使用同一个 storage directory。若应用打包 native Cronet provider，还要按 [25.30 Native SO 体积优化](../../part5-app/ch25-power-size/30-native-so-size-optimization.md) 验证 ABI、符号和 16KB page-size 兼容性；页大小变化对初始化耗时没有通用收益比例。

### 协议选择要看线上分组

HTTP/3 发布至少要按这些维度分组：

- 协商后的协议，而非客户端“已启用 QUIC”的配置值；
- 首次连接、会话恢复和已有连接复用；
- Wi‑Fi、蜂窝、VPN、漫游与 metered 状态；
- 地区、运营商、CDN POP 和服务端版本；
- P50、P95、P99 延迟，以及失败率、回退率和重试率；
- 请求大小、响应大小与电量成本。

服务器需要正确发布 HTTP/3 能力，CDN 和防火墙需要允许相应 UDP 路径。客户端还要保留 HTTP/2 回退。小流量灰度后若尾延迟或失败率变差，应按网络与地区定位，不能只看整体平均值。

## 请求组织：复用、并发、合并与预热

### 共享 OkHttpClient

OkHttp 官方建议复用一个 `OkHttpClient`。每个 client 都有连接池和线程资源；每次请求新建 client 会丢失复用机会，还会留下空闲资源。

下面的代码创建一个共享 client，并从它派生不同超时策略：

```kotlin
data class TimeoutPolicy(
    val callMs: Long,
    val connectMs: Long,
    val readMs: Long,
    val writeMs: Long,
)

val sharedClient = OkHttpClient()

fun clientFor(
    base: OkHttpClient,
    policy: TimeoutPolicy,
): OkHttpClient = base.newBuilder()
    .callTimeout(policy.callMs, TimeUnit.MILLISECONDS)
    .connectTimeout(policy.connectMs, TimeUnit.MILLISECONDS)
    .readTimeout(policy.readMs, TimeUnit.MILLISECONDS)
    .writeTimeout(policy.writeMs, TimeUnit.MILLISECONDS)
    .build()
```

`newBuilder()` 派生的 client 会共享连接池和线程资源。业务可按交互请求、上传、流式读取等类别配置策略。代理、信任管理器、证书固定、DNS 或协议要求相互冲突时，才需要认真评估独立 client。

OkHttp 5.3.0 默认最多保留 5 条**空闲**连接 5 分钟；这不是连接总数或域名数量上限。正在承载 HTTP/2 stream 的连接不属于空闲连接，并发仍受 Dispatcher、服务端 stream 配置、socket 与系统资源共同约束。调参前先统计新建连接率、空闲回收和服务端 keep-alive，不能只凭默认数字扩大池。

连接可否复用还受 scheme、port、代理、DNS、socket/TLS 配置、hostname verifier 和 certificate pinner 等完整 `Address` 约束。HTTP/2 跨主机 connection coalescing 还要求现有连接指向同一 IP/端口、证书覆盖新主机、使用兼容的主机名校验与 pin；应用不能假定两个域名一定共享连接。

OkHttp 5 默认启用 fast fallback，会并行尝试可用路由以降低 IPv6 / IPv4 连接等待。这会让一次 `Call` 出现多组 connect 事件，监控代码要按 attempt 保存。

### 并行和请求合并各有成本

聚合接口可以减少往返、重复 header 和客户端调度，也会扩大响应体、缓存失效范围和单次失败影响。HTTP/2 / HTTP/3 并行请求允许各数据块独立缓存、独立失败和按优先级展示。

选择时可以比较：

- 页面最早可展示时间与全部数据完成时间；
- 每个接口的缓存周期和权限边界；
- 部分失败是否允许展示；
- 聚合服务的超时与下游 fan-out；
- header、序列化和重复字段占比；
- 取消页面后还有多少无用请求继续执行。

同一页面每次打开都发出相同请求时，缓存或状态复用通常比单纯增加并发更有效。搜索联想、滚动图片和页面切换要及时取消过期请求，释放 Dispatcher、stream 和带宽资源。

### “预连接”是一笔真实请求成本

OkHttp 没有承诺任意业务请求都能通过一个公开 `preconnect()` API 预建连接。发送 HEAD 或空 GET 进行 warmup 会产生 DNS、连接、TLS、服务器、流量和电量成本。后续请求还可能因网络切换、不同 authority、证书条件、连接空闲回收或服务端关闭而无法复用。

若冷启动指标证明预热有收益，可设置无副作用、低成本、允许失败的专用 endpoint，并满足这些条件：

- 与后续请求使用同一 authority 和网络栈；
- 不触发鉴权刷新、业务统计、昂贵后端或 WAF 规则；
- 只在很快会使用该域名时执行；
- 不阻塞首屏，也不把失败展示给用户；
- 记录复用命中率、额外字节和电量变化。

DNS 预解析只减少 resolver 阶段，无法完成 TCP、TLS 或 QUIC 握手。Cronet 的 QUIC hint 与会话元数据也属于提示和状态复用，不构成功能保证。

## CDN、DNS 与图片

### 客户端如何观察 CDN

CDN 会改变 DNS 答案、边缘距离、TLS 会话、协议协商、缓存命中和回源路径。客户端可在不泄露敏感信息的前提下记录：

- 业务域名的匿名分组；
- 协议与 IP family；
- CDN 提供的 POP / cache 状态响应头白名单；
- DNS、connect、TLS、响应头等待和传输耗时；
- 响应码、重试、回退和字节数。

客户端很难仅凭 TTFB 区分边缘排队、cache miss 与源站处理。CDN 日志和服务端 trace ID 应采用白名单传递，并避免把完整 URL、query、Cookie、Authorization 或用户标识写入 APM。

### 自定义 DNS 需要系统边界

OkHttp 的 `Dns` 接口允许自定义解析。HTTPDNS、DoH 或业务 DNS 服务需要处理 TTL、IPv6、多个地址、负缓存、取消、故障回退和缓存隔离。URL 仍应保留域名，让 Host、SNI 和证书校验使用域名；把 HTTPS URL 改成裸 IP 会破坏这些语义。

自定义解析还可能绕开 Android Private DNS、VPN、企业 split DNS、局域网域名和 captive portal 流程。采用前要确认安全与网络治理要求。系统 DNS 慢的证据应来自按网络分组的事件数据，不能把个别超时扩展成全量切换理由。

### 图片网络优化

图片请求的主要手段是减少无用字节和无用工作：

- 按显示尺寸、密度和裁剪方式请求合适分辨率；
- 列表优先缩略图，进入详情后再请求大图；
- 使用内存与磁盘 cache，服务端提供稳定 cache key、`ETag` 或合理的 `Cache-Control`；
- 页面离开后取消不再可见的请求；
- 根据请求观测和用户设置选择画质，避免用 Wi‑Fi / 蜂窝标签直接判定质量；
- 渐进式图片仅在编码格式、解码器和渲染组件均支持时采用。

缩略图和原图要使用可推导或可关联的 cache key，防止列表滚动时重复下载。渐进式传输如果需要多次解码，也会增加 CPU 和内存成本，必须同时测量首个可用画面与完整解码时间。

## 弱网策略：期限、重试、缓存与降级

### 超时是不同层级的期限

OkHttp 5.3.0 的默认 connect、read、write timeout 都是 10 秒，默认没有覆盖完整 `Call` 的总 timeout。它们的含义不同：

- `callTimeout` 覆盖整个调用，包括 DNS、建连、写入、服务端处理、读取、重定向和内部恢复。
- `connectTimeout` 约束新 TCP socket 的连接阶段，不约束 DNS 和完整调用。
- `readTimeout` 约束 socket 与单次读取操作，不等同于整个响应体期限。
- `writeTimeout` 约束写入操作，不等同于上传业务的完整截止时间。

超时值应来自接口 SLO、用户等待预算、请求体大小和可恢复方式。交互接口需要明确总期限；大文件上传更适合分片、进度与断点续传；长连接和流媒体要按心跳或 segment 设计；后台同步应使用 WorkManager 的网络约束与重试调度。

把弱网 timeout 一律调大，会延长用户等待并占用并发资源。把 timeout 一律调小，则会放大尾部网络上的失败与重试。每类请求都要记录超时发生在哪一段，再调整对应边界。

### 重试前先判断结果是否未知

请求失败可以分成几类：

| 失败位置 | 风险 | 处理方向 |
|---|---|---|
| DNS 或尚未发送请求的连接失败 | 服务端大多尚未收到业务请求 | 允许网络库尝试其他地址或路由，并受总期限限制 |
| TLS 证书、主机名或协议校验失败 | 安全配置或中间网络异常 | 停止盲目重试，保留错误分类 |
| 请求体发送后连接中断 | 服务端可能已经执行 | 查询业务状态，或依赖幂等键去重 |
| HTTP 408、429、503 | 服务端可能允许稍后尝试 | 按接口契约和 `Retry-After` 决定 |
| 其他 4xx | 请求、权限或业务状态通常需要修改 | 按响应语义处理 |
| 响应体中途失败 | 已接收部分数据 | 支持 Range / ETag 的下载可续传，其他请求按业务语义恢复 |

指数退避要加入随机抖动，并受尝试次数、总期限、前后台状态和用户取消约束。服务端给出 `Retry-After` 时优先遵守。恢复网络时不要让所有挂起请求同步重发。

OkHttp 的 `retryOnConnectionFailure` 默认开启，用于处理部分路由和连接层恢复；重定向、认证与某些响应也会在一个 `Call` 内产生 follow-up。应用层重试叠加在其上时，要记录网络库 attempt 与业务 attempt，避免数量相乘。Interceptor 内阻塞等待退避会占用执行资源，重试调度更适合放在请求编排层或 WorkManager。

HTTP 方法的规范语义也不足以保证业务安全。一个声明为 PUT 或 DELETE 的接口仍可能包含审计、通知或外部系统副作用。支付、订单和发帖等写操作应由服务端提供幂等键和可查询结果。

### HTTP cache 与业务离线数据

OkHttp cache 遵守 HTTP 缓存语义。下面的函数为共享 client 配置磁盘 cache，容量由产品策略传入：

```kotlin
fun withHttpCache(
    base: OkHttpClient,
    directory: File,
    budgetBytes: Long,
): OkHttpClient = base.newBuilder()
    .cache(Cache(directory, budgetBytes))
    .build()
```

服务端应正确返回 `Cache-Control`、`ETag`、`Last-Modified` 和 `Vary`。客户端 cache 只保存符合规则的 HTTP 响应，不能替代 Room、SQLite 或文件层的业务离线数据。

离线时若产品允许使用一段时间内的 stale 响应，可以显式构造只读 cache 请求：

```kotlin
fun offlineRequest(
    url: HttpUrl,
    maxStaleSeconds: Int,
): Request {
    val policy = CacheControl.Builder()
        .onlyIfCached()
        .maxStale(maxStaleSeconds, TimeUnit.SECONDS)
        .build()

    return Request.Builder()
        .url(url)
        .cacheControl(policy)
        .build()
}
```

cache miss 时，`onlyIfCached()` 会得到 504 `Unsatisfiable Request`，不会自动访问网络。UI 要区分“没有缓存”“缓存过旧”“请求失败”和“已展示旧数据并刷新中”。

### 降级要基于内容能力

弱网降级可以选择已有缓存、较低分辨率、较小分页、暂停自动播放或延后非交互同步。网络 transport 只是提示；同一 Wi‑Fi 可能经过拥塞链路，蜂窝也可能有良好吞吐。策略输入应结合用户设置、metered、roaming、系统估计和近期请求观测，并设置滞回，避免频繁切换画质。

## 长连接、解析与后台流量

WebSocket 适合高频双向消息，但长连接不会自动省电。固定 ping/pong、代理或 NAT 空闲超时、网络切换后的重复重连都可能让蜂窝 radio 频繁保持活跃；低频通知优先复用 FCM 等系统通道，高频业务则要共同定义心跳、退避、会话恢复和消息去重。

Retrofit 的 suspend adapter 也不会让协议本身更快。EventListener 已显示网络完成、业务仍迟迟拿不到数据时，应继续拆分 Converter/JSON 解析、数据库和 UI 映射；协程取消还要确认会传到 `Call.cancel()`。网络、CPU 解析和界面提交分别 trace，避免把网络完成后的 CPU 时间计入 TTFB。

日志、遥测和可延迟同步应在应用内合批，并交给 WorkManager/JobScheduler 表达网络、电量和充电约束。蜂窝 tail time 会受设备、RAT、信号和运营商配置影响，不能引用固定时长；是否节能要比较唤醒次数、radio 活跃窗口、字节量和任务完成率。

## 监控：EventListener 与 NetworkCallback

### OkHttp EventListener

每个 `Call` 都要由 `EventListener.Factory` 创建独立 listener。回调必须快速返回，不能执行磁盘或网络 I/O，也不能重新进入同一个 client。事件先写入无阻塞队列，再由后台消费者批量处理。

下面的示例记录总耗时与 Dispatcher 排队时间，不采集 URL 或 header：

```kotlin
data class CallMetric(
    val totalMs: Long,
    val queueMs: Long?,
    val failed: Boolean,
)

class CallTimingListener(
    private val emit: (CallMetric) -> Unit,
) : EventListener() {
    private var callStartNs = 0L
    private var queueStartNs = 0L
    private var queueTotalNs = 0L

    override fun callStart(call: Call) {
        callStartNs = System.nanoTime()
    }

    override fun dispatcherQueueStart(call: Call, dispatcher: Dispatcher) {
        queueStartNs = System.nanoTime()
    }

    override fun dispatcherQueueEnd(call: Call, dispatcher: Dispatcher) {
        if (queueStartNs != 0L) {
            queueTotalNs += System.nanoTime() - queueStartNs
            queueStartNs = 0L
        }
    }

    override fun callEnd(call: Call) {
        finish(failed = false)
    }

    override fun callFailed(call: Call, ioe: IOException) {
        finish(failed = true)
    }

    private fun finish(failed: Boolean) {
        val endNs = System.nanoTime()
        val totalNs = endNs - callStartNs
        val activeQueueNs = if (queueStartNs != 0L) {
            endNs - queueStartNs
        } else {
            0L
        }
        val allQueueNs = queueTotalNs + activeQueueNs
        emit(
            CallMetric(
                totalMs = TimeUnit.NANOSECONDS.toMillis(totalNs),
                queueMs = allQueueNs.takeIf { it > 0L }?.let {
                    TimeUnit.NANOSECONDS.toMillis(it)
                },
                failed = failed,
            )
        )
    }
}

val metricQueue = ConcurrentLinkedQueue<CallMetric>()
val monitoredClient = OkHttpClient.Builder()
    .eventListenerFactory {
        CallTimingListener { metric -> metricQueue.add(metric) }
    }
    .build()
```

生产监控可用同一方式增加 DNS、connect、secure connect、request、response 和 `connectionAcquired` span。DNS、connect、请求与响应事件可能因重定向和恢复重复出现，应追加到 attempt 列表。连接复用时 DNS 和 connect 事件会缺席，这属于正常结果。

指标上传要限制基数并保护隐私。建议记录经过白名单映射的接口模板、协议、状态码、错误类别和时间分段；完整 URL、query、header、请求体、响应体、Cookie 与 token 不应进入网络性能日志。

### 用 Perfetto 对齐网络与线程

Perfetto 不会自动把 OkHttp `Call` 展成 DNS、TLS 和 TTFB。可以用 AndroidX Tracing 的异步 slice 标记整个逻辑调用，用唯一 cookie 区分同名并发请求；阶段事件仍由 EventListener 记录单调时钟，再按 Call、route 和 attempt 关联。trace 名称只使用低基数常量，不写完整 URL、用户 ID、token 或查询参数。

主线程出现 `nativePollOnce` 通常只是 Looper 空闲。只有调用栈、线程状态和时间重叠共同指向 `Future.get()`、锁、socket 或协程桥接点时，才能判断 UI 在等待网络。网络 slice 与主线程慢区间重叠只能建立相关性，业务 request ID 和同步对象栈才能补足因果证据。

### NetworkCallback 只描述平台网络状态

`NetworkCallback` 不能测量业务 host 的 DNS、TLS 或响应延迟。`INTERNET` 是网络能力声明，`VALIDATED` 是系统公网探测结果，业务请求成功仍取决于目标域名、路由、证书、CDN 和服务端。应用只需把 capability、metered、blocked、VPN 与网络切换作为请求策略输入；回调顺序、每 UID 100 个共享 request/callback 配额、注册生命周期、FullScore 选择和 linger 统一见 [1.62 Android 17 ConnectivityManager：架构、网络选择与性能](../../part1-fundamentals/ch01-architecture/1.62-android17-connectivitymanager-architecture-performance.md)。

后台任务若只关心“有网”或“非计费网络”，优先使用 WorkManager/JobScheduler constraint。网络切换后也不要统一清空连接池或立即重放全部失败请求，应让网络库先处理连接状态，再由业务幂等和退避策略决定恢复。

## Android 17 的平台策略输入

`SubscriptionInfo.getStreamingAppMaxDownlinkKbps()` / `getStreamingAppMaxUplinkKbps()` 表示运营商为流媒体应用分配的速率上限，未知时返回 `BITRATE_UNKNOWN`；它不是链路测速。targetSdk 37 的局域网功能还需适配 `ACCESS_LOCAL_NETWORK` 或系统 picker，权限拒绝不能归类成普通弱网。完整的权限、NetworkCallback、FullScore、网络切换和系统源码边界见 [1.62 Android 17 ConnectivityManager](../../part1-fundamentals/ch01-architecture/1.62-android17-connectivitymanager-architecture-performance.md)。

## 版本边界

| 版本 | 相关变化 |
|---|---|
| Android 8 / API 26 | 范围下界；`onAvailable()` 后的 capabilities 与 link properties callback 顺序得到公开保证 |
| Android 11 / API 30 | 平台改进 5G 场景的带宽估计；返回值仍是第一跳估计 |
| Android 17 / API 37 | `SubscriptionInfo` 增加流媒体分配速率；target 37 的局域网访问受 `ACCESS_LOCAL_NETWORK` 约束 |
| OkHttp 5.3.0 | 客户端锚点；共享 client、fast fallback、EventListener 排队事件与默认 timeout 口径以此版本为准 |
| Cronet 18.0.1 | Play services Cronet 接入锚点；provider 可用性和协议协商需要运行时观测 |

## 排查清单

### 指标

- [ ] 总耗时、排队、DNS、connect、TLS、响应头等待和响应体传输已分开
- [ ] 计时使用单调时钟
- [ ] 重定向、路由回退和重试按 attempt 保存
- [ ] 协议、cache、network、metered 与失败类别进入低基数分组
- [ ] APM 没有记录完整 URL、query、凭证或正文

### 协议与请求组织

- [ ] OkHttpClient 或 CronetEngine 在进程内复用
- [ ] HTTP/3 指标按协商协议统计，并保留 HTTP/2 回退
- [ ] 0-RTT 只用于可容忍重放的业务
- [ ] 聚合接口与并行请求比较了缓存、部分失败和最早展示时间
- [ ] warmup 有专用 endpoint、命中率和额外流量数据
- [ ] 页面离开后会取消失效请求

### 弱网

- [ ] 每类接口有总期限和阶段 timeout
- [ ] 重试受幂等、结果未知、`Retry-After`、尝试次数和总期限约束
- [ ] 网络恢复采用抖动，避免请求同步重发
- [ ] HTTP cache 与业务离线数据职责清楚
- [ ] 降级策略结合近期请求观测，带有滞回

### Android 平台

- [ ] default network callback 在不再使用时注销
- [ ] `INTERNET`、`VALIDATED`、metered、transport 与请求结果没有混用
- [ ] 第一跳带宽估计没有写成实时吞吐
- [ ] Android 17 流媒体 carrier cap 正确处理 `BITRATE_UNKNOWN`
- [ ] target 37 的局域网功能已适配权限或系统 picker

## 参考资料

- [Read network state](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [`ConnectivityManager`](https://developer.android.com/reference/android/net/ConnectivityManager)
- [`ConnectivityManager.NetworkCallback`](https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback)
- [`NetworkCapabilities`](https://developer.android.com/reference/android/net/NetworkCapabilities)
- [OkHttp 5.3.0 README](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/README.md)
- [OkHttp 5.3.0 `OkHttpClient.kt`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt)
- [OkHttp 5.3.0 `EventListener.kt`](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
- [Perform network operations using Cronet](https://developer.android.com/develop/connectivity/cronet)
- [Send a simple Cronet request](https://developer.android.com/develop/connectivity/cronet/start)
- [`CronetEngine.Builder`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/CronetEngine.Builder)
- [`QuicOptions.Builder`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/QuicOptions.Builder)
- [RFC 9113: HTTP/2](https://www.rfc-editor.org/rfc/rfc9113)
- [RFC 9114: HTTP/3](https://www.rfc-editor.org/rfc/rfc9114)
- [RFC 9000: QUIC](https://www.rfc-editor.org/rfc/rfc9000)
- [RFC 9001: Using TLS to Secure QUIC](https://www.rfc-editor.org/rfc/rfc9001)
- [`SubscriptionInfo`](https://developer.android.com/reference/android/telephony/SubscriptionInfo)
- [Android 17 local network permission](https://developer.android.com/privacy-and-security/local-network-permission)
