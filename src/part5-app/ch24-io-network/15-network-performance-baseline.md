---
title: "移动网络性能优化实战：DNS、连接、传输与容灾"
chapter: "24.15"
status: ready-for-review
drafted_date: "2026-05-22"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-22"
last_verified_against: "AOSP local sources android-35; Android Developers connectivity/Cronet docs 2026-02/03"
confidence: medium
tags: [network, cronet, http3, dns, weak-network, performance]
related_chapters: ["12.2", "12.3", "12.4", "24.4", "24.5", "24.10", "24.14", "26.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "参考书素材/官方文档/AOSP结构"
material_sources:
  - "intake/research-gaps.md#2026-05-22-网络性能优化"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
  - "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - "https://developer.android.com/develop/connectivity/cronet"
sources:
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/CronetEngine.Builder"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/NetworkQualityRttListener"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/reading-network-state"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system/dns-resolver"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/DnsResolver.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/NetworkCapabilities.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/TrafficStats.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-30/com/android/server/ConnectivityService.java"
  - type: clipping-structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
  - type: clipping-structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
---

# 24.15 移动网络性能优化实战：DNS、连接、传输与容灾

<!-- outline-start -->
## 要点

### 🔹 请求阶段拆分
按 DNS、地址选择、TCP/QUIC 建连、TLS 握手、请求发送、首包返回、响应体下载拆分耗时，并给每个阶段绑定可观测字段。

### 🔹 DNS 与地址选择
覆盖系统 DNS、HTTPDNS、DoH/DoT、IPv4/IPv6 选择、TTL、缓存刷新和失败兜底，说明哪些问题应放在 24.10 继续展开。

### 🔹 连接复用与队头阻塞
整理 HTTP/1.1 keep-alive、HTTP/2 多路复用、连接池、域名合并和单连接限速场景，区分复用收益与 TCP 队头阻塞代价。

### 🔹 Cronet、OkHttp 与 Mars 选型
比较三类网络栈的协议支持、弱网能力、长连接支持、平台依赖、接入成本和监控字段，避免把某个库写成通用答案。

### 🔹 HTTP/3、QUIC 与网络切换
说明 HTTP/3/QUIC 在建连、迁移、队头阻塞上的优势，以及 UDP 可达率、回退策略、服务端支持和灰度条件。

### 🔹 弱网容灾策略
覆盖超时、重试、熔断、备用域名、备用 IP、请求分级、幂等保护和流量降级，回连 24.14 的请求分段优化。

### 🔹 数据体积与传输成本
对比 JSON、Protocol Buffers、gzip、Brotli、Zstandard 和业务字典，说明 CPU、流量、服务端成本之间的取舍。

### 🔹 验证与回归防护
给出客户端阶段耗时、接入层日志、Android Vitals、Cronet metrics、Perfetto/network trace 的联合验证方法。

## 扩展

### 🔸 移动网络标准演进
补充 Wi-Fi、蜂窝网络、5G、IPv6、网络切换对 App 请求体验的影响，避免停留在 2019 年网络环境。

### 🔸 安全与性能的取舍
整理 TLS 1.3、0-RTT、证书锁定、代理环境、证书轮换和重放风险的边界。

### 🔸 系统侧网络模块
从 ConnectivityService、DnsResolver、netd 角度补 AOSP 验证锚点，用于区分 App 网络库问题和系统网络问题。

<!-- outline-end -->

## 本节边界

本节把移动端一次网络请求拆成可测、可调、可回滚的阶段。协议机制见 12.2、12.3、12.4 和 24.5；HTTPDNS 的 OkHttp 接入边界见 24.10；请求分段优化的通用手册见 24.14；线上指标与接入层对账见 26.17。

Part 5 的价值在执行面：怎样给每段耗时命名，怎样决定该换 DNS、换协议、调重试还是降级业务。参考书提供了「请求过程 → 网络库 → 接入层 → QUIC/IPv6」的组织顺序，正文只采用结构和知识点清单，不搬运原文段落。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md][结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md]

## 请求阶段拆分

移动端网络优化从阶段耗时开始。只看 `total_time_ms` 会把 DNS 抖动、TCP 失败、TLS 证书校验、服务端排队、响应体过大混在一起，后续动作很容易偏。

| 阶段 | 客户端字段 | 服务端/接入层字段 | 失败含义 | 下一步动作 |
|------|------------|-------------------|----------|------------|
| DNS | `dns_start_ms`、`dns_end_ms`、`dns_provider`、`dns_cache_hit` | 解析来源、调度 IP、TTL | 解析慢、劫持、跨运营商调度 | 看 24.10 的 HTTPDNS 缓存和兜底模型 |
| 地址选择 | `ip_family`、`candidate_ip_count`、`selected_ip`、`fallback_index` | VIP/边缘节点、区域、运营商 | IPv6 不通、单 IP 故障、调度不准 | 多 IP fast fallback，失败 IP 隔离 |
| 建连 | `connect_start_ms`、`connect_end_ms`、`protocol`、`socket_reused` | 接入层连接队列、端口、四元组 | TCP/QUIC 可达率低、端口被限 | 预连接、复用、HTTP/3 灰度回退 |
| TLS | `tls_start_ms`、`tls_end_ms`、`tls_version`、`session_reused` | 证书、SNI、ALPN、握手错误码 | 证书链慢、会话复用失效、代理干预 | TLS 1.3、会话复用、证书配置审计 |
| 请求发送 | `request_bytes`、`upload_ms`、`content_encoding` | 入站字节、限流、鉴权结果 | 体积过大、上行带宽低、请求被拦 | 压缩、字段裁剪、请求分级 |
| 首包 | `ttfb_ms`、`http_status`、`retry_count` | upstream 耗时、业务处理耗时、缓存命中 | 服务端慢、接入层排队、重试放大 | 接入层对账，避免客户端盲目重试 |
| 下载 | `response_bytes`、`download_ms`、`throughput_kbps` | 出站字节、CDN 命中、分片耗时 | 响应大、单连接限速、弱网丢包 | 分页、差量、CDN、协议切换 |

Cronet 公开 API 能提供请求结束指标、网络质量估计、HTTP RTT 和吞吐量估计；Android Developers 文档也确认 Cronet 支持 HTTP、HTTP/2 和 HTTP/3 over QUIC。[已验证: 官方文档, developer.android.com/develop/connectivity/cronet][已验证: 官方文档, developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/NetworkQualityRttListener]

OkHttp 项目通常通过 `EventListener` 补齐 DNS、connect、secureConnect、requestHeaders、responseHeaders 等阶段。自研网络栈也要提供等价字段，否则只能用外层耗时猜测瓶颈。

## DNS 与地址选择

Android 10 以后，App 可使用 `DnsResolver` 进行异步 DNS 查询，并可传入 `Network` 约束解析走哪张网络。AOSP android-35 的 `android.net.DnsResolver` 仍保留 `query(Network, String, ...)` 系列入口，这说明系统 DNS 能按网络对象参与解析，但它不等于业务层 HTTPDNS。[已验证: AOSP android-35, android/net/DnsResolver.java]

DNS 优化要拆成四个问题：

- 解析入口：系统 DNS 适合默认路径，HTTPDNS 适合调度、容灾和运营商 LocalDNS 异常治理；DoH/DoT 适合隐私和抗篡改诉求，是否接入取决于服务器、合规和失败兜底能力。
- 缓存策略：TTL 要来自权威配置或 HTTPDNS 返回，客户端本地缓存不能无限延长；网络切换、失败 IP、证书错误都应触发刷新或隔离。
- 地址排序：IPv4/IPv6、多个 VIP、多个端口不要只按列表顺序尝试；失败历史、网络类型、运营商、区域和握手耗时都应进入排序。
- 兜底路径：HTTPDNS 服务不可达时要回到系统 DNS；HTTPDNS 返回空列表、单 IP 超时、多 IP 部分失败都应有独立错误码。

24.10 已经展开 OkHttp `Dns.lookup()` 的同步执行边界。本节只保留判断口径：`lookup()` 里发实时 HTTPDNS 请求会阻塞 route planning，还可能递归依赖同一个网络栈；更稳的模型是异步预取 + 内存缓存读取 + 磁盘缓存兜底 + 系统 DNS 回退。

## 连接复用与队头阻塞

建连成本由 TCP/QUIC 握手、TLS 握手、代理环境、证书链、网络切换共同决定。复用连接能少走这些阶段，但复用不是越高越好。

| 场景 | 收益 | 风险 | 处理方式 |
|------|------|------|----------|
| HTTP/1.1 keep-alive | 避免重复 TCP/TLS 建连 | 并发请求受连接数限制 | 按 host 建连接池，控制空闲连接数量 |
| HTTP/2 多路复用 | 多个请求共享同一 TCP 连接 | TCP 层丢包会影响同连接上的多个 stream | 大文件、视频、第三方下载可单独隔离 |
| 域名合并 | 多业务复用同一接入层连接 | 证书 SAN、SNI、Cookie、鉴权边界容易混 | 只在统一接入层和安全边界明确时启用 |
| 预连接 | 用户动作前完成建连 | 浪费电量、流量和服务端连接资源 | 只给高置信路径设置短窗口预连接 |
| 单连接限速绕过 | 避免下载被服务端限速 | 破坏 HTTP/2 复用收益 | 仅对下载类请求独立策略，不影响 API 请求 |

HTTP/2 解决的是 HTTP/1.1 应用层请求排队，底层仍跑在一条 TCP 连接上。弱网丢包时，同连接上的多个 stream 都会受 TCP 重传影响。HTTP/3/QUIC 把多个 stream 放到 UDP 之上的 QUIC 层，单个 stream 的丢包不会按 TCP 连接粒度拖住其他 stream；代价是 UDP 可达率和服务端改造要通过灰度验证。

## Cronet、OkHttp 与 Mars 选型

网络库选型要围绕业务形态，不要把某个库写成统一答案。

| 维度 | OkHttp | Cronet | Mars / 自研长连接 |
|------|--------|--------|-------------------|
| 协议 | HTTP/1.1、HTTP/2，HTTP/3 取决于外部接入方案 | 官方文档明确支持 HTTP、HTTP/2、HTTP/3 over QUIC | 常见定位是 Socket/长连接层，HTTP 能力取决于封装 |
| Android 接入 | 生态成熟，拦截器和 Retrofit 集成成本低 | 需要引入 Cronet 依赖或 Play services 方案 | 接入、灰度、监控、服务端配套成本高 |
| 弱网能力 | 依赖连接池、超时、重试和业务策略 | 有网络质量估计、QUIC、连接迁移等 Chromium 能力 | 可按业务协议做心跳、重连、包大小和容灾策略 |
| 跨端一致性 | Android 侧强，iOS 需另配 | Chromium 栈更利于多端统一 | 可按公司协议统一，但维护成本高 |
| 可观测性 | EventListener、拦截器、应用埋点 | RequestFinishedInfo、全局 metrics、网络质量估计 | 指标完全由团队设计，灵活但要防口径漂移 |
| 适合场景 | 常规 API、图片、下载、快速交付 | 大流量、协议演进、HTTP/3 灰度、跨端网络栈 | IM、直播、游戏、强弱网容灾、长连接业务 |

Cronet 官方文档写明它是 Chromium 网络栈的 Android 库，目标是降低延迟、提高吞吐，并支持 HTTP/3 over QUIC。[已验证: 官方文档, developer.android.com/develop/connectivity/cronet] 但 Cronet 不会替业务处理幂等、降级、接入层路由和服务端排队问题。OkHttp 也不是弱网治理的反面；它的优势在接入成本、生态和可控性。

## HTTP/3、QUIC 与网络切换

HTTP/3/QUIC 在移动端有三类直接收益：握手更短、stream 级别队头阻塞更少、网络切换时连接迁移空间更大。Cronet 的 `CronetEngine.Builder` 文档还提到 QUIC hint、HTTP cache 对跨会话 0-RTT 的作用，以及 network quality estimator 的 RTT/吞吐估计能力。[已验证: 官方文档, developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/CronetEngine.Builder]

生产接入不能只看实验室耗时。灰度方案至少要记录这些字段：

- UDP 可达率：按国家、运营商、网络类型、系统版本统计 QUIC 建连成功率。
- 回退路径：QUIC 失败后回到 HTTP/2 或 HTTP/1.1 的耗时、错误码和重试次数。
- 迁移效果：Wi-Fi ↔ 蜂窝切换时，请求是否重建、是否丢首包、是否触发业务超时。
- 服务端能力：接入层是否支持 QUIC、证书和 ALPN 是否齐全、负载均衡是否保留连接状态。
- 灰度开关：按域名、接口、业务等级和地区控制，不把登录、支付、下单等高风险请求放在第一批。

HTTP/3 接入后，P50 变快不代表风险降低。要同时看 P95/P99、失败率、回退率、服务端 CPU、UDP 被阻断比例和耗电表现。网络协议切换影响请求、接入层、证书、CDN 与监控口径，回滚开关必须比灰度开关更早上线。

## 弱网容灾策略

弱网治理的目标不是让每个请求都成功，而是让重要请求有预算、可恢复、可解释。24.14 已经给出一次请求的七段拆解，本节补执行清单。

| 策略 | 适合对象 | 关键边界 | 观测字段 |
|------|----------|----------|----------|
| 分阶段超时 | 登录、首页、支付、图片、下载 | DNS、connect、read、write 不共用一个总超时 | `timeout_stage`、`elapsed_ms` |
| 重试预算 | GET、幂等 POST、资源拉取 | 非幂等请求必须有业务幂等键；网络层不替业务兜底 | `retry_count`、`retry_reason`、`idempotency_key` |
| 熔断 | 某域名、某接口、某接入点连续失败 | 熔断粒度不能大到影响全站；恢复要小流量探测 | `circuit_state`、`probe_result` |
| 备用域名/IP | DNS 污染、VIP 故障、区域接入层异常 | 备用 IP 要过证书、SNI、Host、风控校验 | `fallback_host`、`fallback_ip` |
| 请求分级 | 首屏、交易、后台同步、日志上报 | 低优先级请求在弱网下降级或延后 | `request_class`、`degrade_reason` |
| 流量降级 | 图片、视频、列表、推荐流 | 降级要保护用户体验，不把空白页当成功 | `payload_level`、`bytes_saved` |

重试要防止「失败 → 重试 → 队列变长 → 更多超时」的放大效应。客户端、接入层和业务服务要共享错误分类：DNS 失败、TCP 连接失败、TLS 失败、HTTP 5xx、业务错误、客户端取消不能混成一个 `network_error`。

## 数据体积与传输成本

减少字节数通常能改善弱网体验，但压缩和序列化会消耗 CPU、电量和服务端资源。移动端要按数据形态选方案。

| 方案 | 收益 | 成本 | 适合场景 |
|------|------|------|----------|
| JSON 字段裁剪 | 接入快，兼容好 | 仍有字段名和文本冗余 | API 响应、灰度字段治理 |
| Protocol Buffers | 体积和解析速度较好 | schema 管理、调试和兼容成本更高 | 高频接口、跨端协议、长连接消息 |
| gzip | 通用支持好 | 压缩率和速度不是最优 | 文本响应、旧服务端 |
| Brotli | 文本压缩率好 | 编码 CPU 成本更高 | 静态资源、可缓存文本 |
| Zstandard | 压缩率和速度平衡好，可配字典 | 客户端库、字典分发、服务端训练成本 | 高频业务数据、接入层统一压缩 |
| 业务字典 | 对固定字段和枚举收益大 | 字典版本、回滚和兼容复杂 | 大规模统一接入层、有样本训练能力的团队 |

压缩策略要和缓存、分页、差量更新一起评估。把一个 3 MB 响应 gzip 成 1 MB 只能降低传输时间；如果首屏只用 50 KB，分页和字段裁剪比压缩更有效。

## 验证与回归防护

网络优化的回归测试要覆盖客户端、系统、接入层和用户体验四个面。

- 客户端阶段耗时：统一采集 DNS、connect、TLS、TTFB、download、bytes、protocol、socket reuse、retry 等字段，OkHttp 用 EventListener，Cronet 用公开 Cronet API 和网络质量估计能力。[已验证: 官方文档, developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/NetworkQualityRttListener]
- 系统网络状态：用 `ConnectivityManager` 和 `NetworkCapabilities` 区分 Wi-Fi、蜂窝、以太网、卫星等 transport；AOSP android-35 的 `NetworkCapabilities` 保留 `TRANSPORT_CELLULAR`、`TRANSPORT_WIFI` 等常量。[已验证: AOSP android-35, android/net/NetworkCapabilities.java]
- 流量统计：`TrafficStats.getUidRxBytes()` 等接口能按 UID 读取收发字节，适合做粗粒度流量回归；精细阶段仍要靠网络库埋点。[已验证: AOSP android-35, android/net/TrafficStats.java]
- 接入层对账：客户端 `trace_id` 要贯穿 DNS 选择、接入层、upstream 服务和 CDN 日志，避免客户端把服务端排队误判成弱网。
- 功耗约束：Android Developers 的网络访问优化文档强调无线电状态机和批量网络请求对电量的影响；后台请求、预连接和重试都要看电量指标。[已验证: 官方文档, developer.android.com/develop/connectivity/network-ops/network-access-optimization]
- 回归用例集：Wi-Fi、蜂窝、弱网、网络切换、代理、证书替换、IPv6-only、UDP 阻断、服务端 5xx、DNS 空响应都要有固定用例。

Perfetto 更适合观察线程调度、CPU、binder、socket 相关系统调用与应用阶段埋点的时间关系；它不能替代网络库里的协议阶段字段。线上网络质量监控的告警、证据包和接入层协同见 26.17。

## 扩展：移动网络标准演进

Wi-Fi、蜂窝网络、5G、IPv6 对 App 请求的影响不只体现在带宽。App 更常遇到的是网络切换、NAT、运营商策略、UDP 可达率、代理环境和局部拥塞。`ConnectivityService` 负责向应用侧分发网络能力变化，AOSP android-30 代码中能看到 `notifyNetworkCallbacks()`、Wi-Fi/蜂窝 transport 判断和网络回调分发路径。[已验证: AOSP android-30, com/android/server/ConnectivityService.java]

IPv6 的收益不能简单写成「一定更快」。它减少 NAT 层级，对 P2P、QUIC 和地址资源有帮助，但具体请求耗时取决于运营商、地区、接入层和应用地址选择策略。IPv6-only、NAT64、464XLAT、双栈选择都要进入回归用例。

## 扩展：安全与性能的取舍

TLS 1.3、会话复用、0-RTT 和证书链优化能减少握手成本，但安全策略会改变性能边界。0-RTT 有重放风险，只适合幂等请求；证书锁定能降低被代理或中间人篡改的风险，但证书轮换失败会造成大面积不可用。

Android Network Security Config 官方文档说明，证书 pinning 可设置过期时间，避免长期未更新 App 在证书轮换后完全断网。[已验证: 官方文档, developer.android.com/privacy-and-security/security-config] 高风险业务可以锁定公钥或根证书，但必须保留备用 pin、过期时间、灰度验证和远程熔断方案。

## 扩展：系统侧网络模块

App 网络库问题和系统网络问题要分开判断。DNS 解析可看 `DnsResolver`、DNS Resolver APEX 与 netd；网络能力和切换可看 `ConnectivityService`、`NetworkCapabilities`、`ConnectivityManager.NetworkCallback`；流量粗统计可看 `TrafficStats`。Source Android 文档说明 DNS Resolver 模块以 APEX 形式交付，并由 netd 动态链接，同时本模块可直接服务 `/dev/socket/dnsproxyd`。[已验证: 官方文档, source.android.com/docs/core/ota/modular-system/dns-resolver]

系统侧验证只用于定位边界，不建议 App 绕过平台网络策略。应用侧能稳定控制的是网络库选型、阶段埋点、缓存、重试、降级和接入层协同。

## 小结

移动网络优化要从阶段字段开始，按 DNS、地址选择、建连、TLS、发送、首包、下载逐段验证。DNS 和协议切换能改善一部分请求，弱网容灾、请求分级、接入层对账和回滚开关决定线上能否长期稳定。
