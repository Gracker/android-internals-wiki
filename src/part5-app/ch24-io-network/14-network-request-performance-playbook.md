---
title: "网络请求分段优化与弱网治理"
chapter: "24.14"
section: "24.14"
status: ready-for-review
drafted_date: "2026-05-22"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-02"
last_verified_against: "Android Developers Cronet / network access optimization docs 2026-05-22 + android-17.0.0_r1 (verified via git ls-remote; APIs cross-checked against android-17.0.0_r1 tag on googlesource) + OkHttp 5.x docs"
confidence: medium
tags: [network, latency, weak-network, cronet, okhttp, power]
related_chapters: ["24.4", "24.5", "24.10", "24.11", "26.17", "12.3", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "Clippings参考书/官方文档/章节深挖"
gap_score: 18
last_task2a_at: "2026-05-22T16:18:00+08:00"
pipeline_stage: task6_pending
task6_state: revisiting
reviewed_by: openclaw-task6
reviewed_date: "2026-05-22"
task6_result: pass-light-edit
task9_state: pending
last_task6_at: "2026-05-22T17:08:00+08:00"
last_task6_review_log: "logs/review/2026-05-22-17-review.md"
task6_l1_l2_fixes: 5
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-22 Task6：首次写作质检通过；补齐 outline，清理结构性元叙述、编辑标记和填充副词 5 处；无 L3/L4 回炉项，送 Task9 技术复核。"
task9_result: fixed
last_task9_at: "2026-07-02T20:34:05+08:00"
last_task9_review_log: "logs/deep-review/2026-07-02-20-audit.md"
last_task9_audit: "2026-07-02"
last_task6_audit: "2026-06-17"
task9_review_notes: "2026-07-02 Task9 闲时抽检：发现 P1 版本基准问题；章节适用范围到 Android 17/API 37，但源码证据仍锚定 Android 35 SDK。已写入 queue priority:85，回 Task2B 重锚 android-17.0.0_r1。2026-07-02 Task2B：所有源码引用已重锚 android-17.0.0_r1，tag 经 git ls-remote 验证存在；API 行为经跨版本确认一致。"
task2b_state: fixed
last_idle_audit_at: "2026-07-02T20:34:05+08:00"
task2b_result: fixed
task2b_fixed_at: "2026-07-02T21:08:00+08:00"
task2b_fix_summary: "Re-anchored all source references from Android 35 SDK to android-17.0.0_r1; verified tags exist on googlesource (platform/frameworks/base + NetworkStack); confirmed API consistency across versions"
sources:
  - type: clippings
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
  - type: clippings
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
  - type: clippings
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/integration"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/topic/performance/power/network/index.html"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/bg-network-usage"
  - type: official
    path: "https://square.github.io/okhttp/features/events/"
  - type: aosp
    path: "https://android.googlesource.com/platform/packages/modules/NetworkStack/+/refs/tags/android-17.0.0_r1/framework/src/android/net/http/HttpEngine.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/packages/modules/NetworkStack/+/refs/tags/android-17.0.0_r1/framework/src/android/net/http/QuicOptions.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/net/ConnectivityManager.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/net/TrafficStats.java"
  - type: local
    path: "src/part5-app/ch24-io-network/04-network-architecture.md"
  - type: local
    path: "src/part5-app/ch24-io-network/05-protocol-optimization.md"
  - type: local
    path: "src/part5-app/ch24-io-network/10-httpdns-okhttp-dns-boundary.md"
---

# 24.14 网络请求分段优化与弱网治理

<!-- outline-start -->
## 要点

### 🔹 一次请求的七段拆解
说明 DNS、connect、TLS、request write、TTFB、response read 和 decode/render 的观测入口，避免只看总耗时。

### 🔹 速度、弱网、安全和功耗的取舍
把低延迟、弱网可用性、安全和省电拆开设计，说明前台请求与后台同步不能共用同一套策略。

### 🔹 OkHttp、Cronet 与自研长连接选型
明确不同网络栈适合的业务路径、迁移成本和验证指标，避免把协议能力等同于实际收益。

### 🔹 DNS、建连和连接复用组合
把 HTTPDNS、连接池、fast fallback、IPv6/IPv4 fallback 和网络切换放在同一套风险模型中检查。

### 🔹 弱网治理与重试预算
按失败类型、幂等性、页面预算和请求体积设计弱网策略，重点控制请求风暴。

### 🔹 压缩、缓存和预取验证
按请求形态评估 Brotli、HTTP cache、预取和断点续传的收益，避免用单一结论覆盖所有接口。

### 🔹 后台网络与 Vitals 约束
结合电量、移动网络、WorkManager 约束和 TrafficStats，把后台同步从前台低延迟路径中拆出来。

### 🔹 指标采集与场景拆分
用 trace id 关联客户端、接入层和业务服务日志，并区分 API、WebView、媒体、下载和长连接场景。

## 扩展

### 🔸 与 26.17 线上网络质量监控的关系
App 侧策略入口聚焦本地拆段、降级和指标埋点；线上接入层观测和跨层监控在 26.17 展开。

### 🔸 与 24.4 / 24.5 / 24.10 的关系
24.4 / 24.5 / 24.10 分别承接连接池、协议优化和 HTTPDNS 执行边界，当前章节引用这些结论，不重复展开底层机制。

<!-- outline-end -->

移动端网络优化不能只盯一个慢接口。一次请求从域名解析到响应解析，中间会经过 DNS、建连、TLS、写请求、首字节、读响应、业务解码；任何一段抖动，页面都会变慢。App 侧要做的是把这些等待段拆清楚，再按场景选择网络栈、缓存、降级和监控策略。

App 侧可执行的策略主要落在请求分段、网络栈选型、弱网治理、后台约束和指标采集。DNS 与连接池细节见 24.4、24.10，HTTP/2、HTTP/3、QUIC 与 gRPC 见 24.5，线上网络质量观测见 26.17。参考书用于组织写作顺序：网络基础、弱网特征、网络库选型、监控与流量指标；正文不使用参考书原文和代码。 [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md] [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md] [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md]

## 先把一次请求拆成七段

网络请求总耗时没有诊断价值。要定位慢在哪里，日志至少拆成七段。

| 阶段 | 典型等待 | App 侧观测入口 | 常见处理 |
|---|---|---|---|
| DNS | 域名解析慢、返回坏 IP、IPv6/IPv4 回退慢 | OkHttp `dnsStart/dnsEnd`、HTTPDNS 缓存命中率 | 异步预取、短 TTL、失败 IP 隔离 |
| TCP connect | 建连慢、SYN 重传、单 IP 不通 | `connectStart/connectEnd/connectFailed` | 多 IP fast fallback、连接池复用、预连接 |
| TLS | 握手慢、证书校验失败、会话恢复未命中 | `secureConnectStart/End` | 会话复用、证书链治理、减少跨域名散点 |
| request write | 上传体大、写 socket 阻塞 | request body bytes、write timeout | 分片上传、压缩、限速、后台任务约束 |
| TTFB | 服务端排队、接入层路由慢 | response headers 到达时间、服务端 trace id | 接入层日志关联、超时分层、灰度摘流 |
| response read | 带宽低、大响应体、单连接限速 | body bytes、read timeout、吞吐估算 | 分页、断点续传、媒体自适应码率 |
| decode/render | JSON/Proto 解码、图片解码、主线程阻塞 | 业务耗时、CPU trace、主线程任务 | 后台解码、缓存、减少首屏字段 |

OkHttp 的 `EventListener` 文档提供了 DNS、connect、secureConnect、request/response header/body 等事件，可用于把请求耗时拆到具体阶段。 [已验证: 官方文档, https://square.github.io/okhttp/features/events/] 如果使用 Cronet，优先使用 public Cronet API 的完成回调和指标能力；不要依赖 Android framework 里未公开或版本漂移的 `android.net.http` 内部指标类。

## 速度、弱网、安全和功耗分开设计

参考书把网络优化拆成速度、弱网、安全三个目标；Android 官方电量文档还要加上功耗。四个目标会互相牵制。

| 目标 | 主要手段 | 代价 | 适用场景 |
|---|---|---|---|
| 速度 | HTTP/2 复用、HTTP/3/QUIC、预连接、缓存 | 连接和缓存状态更复杂 | 首屏、多小请求、API 域名集中 |
| 弱网可用性 | 多 IP、重试、缓存降级、请求裁剪 | 流量放大、服务端幂等要求更高 | 地铁、电梯、蜂窝切 Wi-Fi、海外链路 |
| 安全 | HTTPS、证书校验、证书透明度、敏感接口 pinning | 握手成本、证书轮换成本 | 登录、支付、账号与隐私数据 |
| 功耗/流量 | 批量同步、预取、后台约束、压缩 | 实时性下降、缓存一致性复杂 | feed、离线包、日志上报、后台同步 |

同一个 App 通常要有两套路由：用户可见路径偏向低延迟，后台同步偏向批量和省电。把后台任务和首屏请求放在同一个 Dispatcher 或同一组连接策略里，低优先级请求会挤占用户可见路径。

## 网络栈选型：OkHttp、Cronet、自研长连接

24.4 已经覆盖 OkHttp 的连接池、Dispatcher、Dns 和弱网策略。网络栈选型还要补上业务层边界。

| 方案 | 适合做什么 | 不适合做什么 | 验证点 |
|---|---|---|---|
| OkHttp | 常规 REST API、拦截器体系、Kotlin/Java App 网络层 | 需要 HTTP/3/QUIC 的路径；跨端统一网络栈 | EventListener 分段、连接池复用、Dispatcher 队列 |
| Cronet | 需要 Chromium 网络栈、HTTP/3 over QUIC、Brotli、缓存、媒体/gRPC 集成 | 强依赖 OkHttp 拦截器模型的业务层；需要深度改写 socket 策略 | QUIC 成功率、fallback、缓存命中、请求完成指标 |
| Android `HttpEngine` | Android 平台内的 Cronet 风格 HTTP stack 能力 | 旧系统兼容和第三方分发一致性 | API level、模块版本、QUIC/Brotli/cache 开关 |
| 自研长连接 / Mars 类方案 | IM、推送、弱网保活、跨端 socket 层策略 | 通用 HTTP API 的完整替代 | 心跳、重连、前后台状态、服务端接入层协同 |

Android Developers 的 Cronet 文档说明，Cronet 是面向 Android App 的 Chromium network stack，目标是降低延迟、提高吞吐；它原生支持 HTTP、HTTP/2、HTTP/3 over QUIC，请求默认异步，并支持缓存和 Brotli 压缩。 [已验证: 官方文档, https://developer.android.com/develop/connectivity/cronet]

`android-17.0.0_r1` 中的 `android.net.http.HttpEngine.Builder` 也能看到相同方向的能力：`setEnableQuic()` 默认启用 QUIC，`setEnableHttp2()` 默认启用 HTTP/2，`setEnableBrotli()` 开启后会在 `Accept-Encoding` 中声明 Brotli，`setEnableHttpCache()` 可缓存 HTTP 数据和 QUIC server information，`addQuicHint()` 可提示某个 host 支持 QUIC，并说明跨 session 的 0-RTT 需要 disk HTTP cache。 [已验证: android-17.0.0_r1, NetworkStack, android/net/http/HttpEngine.java]

Cronet 不能让所有请求直接变快。接入前要用灰度实验回答四个问题：QUIC 建连成功率是否足够高；失败后回退到 TCP/TLS 的尾延迟是否可控；缓存和 Brotli 是否降低首屏字节数；业务层的重试、鉴权、trace id、日志脱敏能否迁移。

## DNS、建连和连接复用要组合设计

DNS 优化解决的是“连到哪里”，连接池解决的是“少建几次连接”，协议升级解决的是“同一连接上怎么承载请求”。三者不要混在一个拦截器里。

HTTPDNS 的同步接入边界见 24.10：OkHttp `Dns.lookup()` 位于 route 生成路径，返回前请求无法进入 connect；把实时 HTTPDNS 请求放进 `lookup()` 会把弱网 HTTP 请求塞进建连前置路径。更稳的模型是后台异步刷新，`lookup()` 只读缓存，缓存缺失或过期时回退系统 DNS。 [已验证: 本地章节, src/part5-app/ch24-io-network/10-httpdns-okhttp-dns-boundary.md]

建连策略按风险分层：

- 高价值域名可以做短窗口预连接，但要限制前后台状态和网络类型，避免唤醒 radio 后又没有用户请求。
- 多 IP 返回要保留失败隔离，隔离维度至少包含 hostname、IP、Network、失败类型和时间窗。
- IPv6/IPv4 fallback 要记录尝试顺序和失败原因，不能只上报最终成功 IP。
- HTTP/2 connection coalescing 会让不同域名复用同一条 TLS 连接，证书 SAN、DNS 结果、IP 和 host 策略要一起验证，不能只按域名统计连接数。

Android 的网络切换事件不要用同步查询补状态。`ConnectivityManager.NetworkCallback` 文档说明，`onAvailable()` 从 Android O 起会紧跟 `onCapabilitiesChanged()` 与 `onLinkPropertiesChanged()`，并明确不要在 callback 中调用 `getNetworkCapabilities()` 或 `getLinkProperties()` 等同步方法，因为结果可能过期或为空。 [已验证: android-17.0.0_r1, android/net/ConnectivityManager.java]

## 弱网治理：先收敛失败，再谈加速

弱网下最容易出问题的是请求风暴。一次超时触发多层重试，DNS、网络库、业务层、图片库、下载器各重试一次，用户看到的是更慢，服务端看到的是流量突增。

弱网策略建议按这条顺序处理：

1. 区分失败类型：DNS 失败、connect timeout、TLS 失败、read timeout、HTTP 5xx、业务错误码分开统计。
2. 限制重试对象：只对幂等 GET、可恢复下载、明确幂等的 POST 重试；支付、下单、状态变更接口靠服务端幂等 key。
3. 给重试加预算：按页面或任务设置最大重试次数和总耗时，超出后切缓存或降级 UI。
4. 按网络切换刷新策略：Wi-Fi/蜂窝/VPN 切换后刷新 DNS 与连接池状态，但保留短时兜底缓存，避免切网瞬间全部重建。
5. 降低请求体积：弱网模式下裁剪字段、降低图片规格、推迟非首屏接口、关闭自动播放。

弱网不能用单一阈值概括。直播、游戏、文件下载和普通 API 对 RTT、丢包、吞吐的权重不同。点播更看重持续吞吐，游戏和语音更看重 RTT 与抖动，feed 首屏更看重 DNS、connect、TTFB 和首屏字节数。策略表要按业务类型拆开。

## 压缩、缓存和预取要用请求形态验证

Cronet 和 Android `HttpEngine` 都暴露了 Brotli 开关，HTTP cache 还能缓存 HTTP 数据和 QUIC server information。 [已验证: android-17.0.0_r1, NetworkStack, android/net/http/HttpEngine.java] 压缩和缓存的收益要按请求形态看。

| 请求形态 | 优先策略 | 容易误判的点 |
|---|---|---|
| 小 JSON 配置 | ETag / Cache-Control / 服务端聚合 | gzip/Brotli 的 CPU 成本可能高于字节收益 |
| 首屏 feed | 字段裁剪、分页、图片规格降级、预取下一页 | 预取过多会浪费流量和电量 |
| 大文件下载 | 断点续传、分块校验、后台约束 | 多连接下载可能被服务端限速或触发风控 |
| 图片/视频 | CDN、尺寸协商、AVIF/WebP、ABR | HTTP API 的结论不能直接套到媒体栈 |
| 日志上报 | 批量、压缩、充电/Wi-Fi 约束 | 失败重试容易放大后台移动数据 |

Android 官方 network access optimization 文档把无线电状态机作为省电依据：每次创建新网络连接都会让 radio 进入高功耗状态，频繁小传输会让 radio 长时间停在高功耗；批量传输和预取可以减少独立传输会话，降低 radio 激活次数，同时改善延迟和下载时间。 [已验证: 官方文档, https://developer.android.com/develop/connectivity/network-ops/network-access-optimization]

预取要有退出条件：只预取用户下一步大概率会用到的数据；网络切到计费、受限、后台或低电量时停止；缓存命中率、废弃率和预取字节数必须上报。预取命中率低于业务阈值时，省下的等待会被浪费的流量和电量抵消。

## 后台网络要按电量和 Vitals 指标约束

后台网络任务不能复用前台的“越快越好”策略。Android power 文档把网络请求与电量消耗直接关联；Android Vitals 的 excessive mobile network usage 页面说明，后台移动网络会唤醒 CPU 和 radio，反复执行会消耗电量，Play Console 会对后台移动网络使用过多给出提醒。 [已验证: 官方文档, https://developer.android.com/topic/performance/power/network/index.html] [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/bg-network-usage]

工程上把后台网络拆成三类：

- 用户可感知但可延迟：草稿同步、离线缓存、上传队列。使用 WorkManager 约束网络、电量和充电状态。
- 用户不可感知：埋点、日志、模型配置、AB 配置。批量上报，限制移动网络和失败重试。
- 业务保活：IM、推送、实时协作。单独设计心跳和退避，不能和普通 API 共享重试器。

`TrafficStats` 可作为 App 侧流量基线：android-17.0.0_r1 文档说明它提供发送/接收字节和包数，范围包括所有接口、移动接口和 per-UID；统计值重启后清零，Android N 起查询其他 UID 会因隐私限制返回 `UNSUPPORTED`，历史网络统计应使用 `NetworkStatsManager`。 [已验证: android-17.0.0_r1, android/net/TrafficStats.java]

## 指标采集要覆盖客户端、接入层和业务层

网络优化必须用同一套 trace id 把客户端事件、接入层日志和业务服务日志串起来。客户端只知道 DNS、connect、TLS、读写和本地解码，服务端只知道接入层排队、上游耗时和响应字节；两边不关联，TTFB 慢很容易被误判成“网络差”。

推荐的最小指标集：

| 层级 | 指标 | 用途 |
|---|---|---|
| 客户端请求 | 协议、network type、DNS 耗时、connect 耗时、TLS 耗时、TTFB、body bytes、失败类型 | 找出慢在哪一段 |
| 客户端流量 | UID Rx/Tx、移动网络字节、后台字节、预取废弃字节 | 约束电量和流量 |
| 网络库状态 | 连接池命中、HTTP/2 stream 数、QUIC 使用率、fallback 次数 | 验证网络栈收益 |
| 接入层 | region、IDC/CDN、upstream latency、5xx、限流、重试 | 区分客户端网络与服务端问题 |
| 业务层 | 页面阶段、接口优先级、缓存命中、降级状态 | 判断用户是否真的变快 |

参考书提到插桩、Native Hook、TrafficStats、接入层监控这些方向。当前章节不建议把 Hook 当成默认方案：Aspect/OkHttp interceptor 适合统一自家网络层；Native Hook 能覆盖更底层 socket，但兼容性、稳定性和隐私风险更高，适合 APM SDK 或实验环境。常规业务 App 先把网络库事件和 TrafficStats 做准。 [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md]

## 不同场景不要套同一套网络结论

普通 API、WebView、Media3/ExoPlayer、文件下载和 IM 长连接使用的网络栈可能不同。Cronet integration 文档说明 Cronet 可以与 ExoPlayer、gRPC、OkHttp、Glide、Dart 等库集成；这说明网络栈有机会统一，但不代表所有库天然共用同一套连接池和指标。 [已验证: 官方文档, https://developer.android.com/develop/connectivity/cronet/integration]

场景拆分建议：

- API 请求：以 OkHttp/Cronet 请求事件为主，关注 DNS、connect、TLS、TTFB。
- 媒体播放：以 ABR、buffer health、CDN、range request、播放器 network stack 为主，详见 24.5 与媒体章节。
- WebView：网络栈受 WebView/Chromium 版本影响，App 的 OkHttp 拦截器通常覆盖不到。
- 下载器：关注断点续传、校验、后台约束、失败恢复和服务端限速。
- 长连接：关注心跳、前后台状态、NAT 超时、重连退避和服务端接入层。

## 检查清单

上线前按这张表验收：

- 每条请求能拆出 DNS、connect、TLS、TTFB、body read、decode 耗时。
- DNS 优化没有把 HTTPDNS 网络请求放进 OkHttp `Dns.lookup()` 同步路径。
- 多 IP fallback 有失败隔离和总耗时预算。
- QUIC/HTTP/3 有成功率、fallback、尾延迟和服务端成本数据。
- 预取有命中率、废弃字节、移动网络字节和后台状态限制。
- 后台同步使用网络、电量、充电、计费约束，并独立统计 Android Vitals 风险。
- 大响应体、上传和下载有断点恢复、校验和重试预算。
- 客户端 trace id 能关联接入层和业务服务日志。
- WebView、媒体、下载和长连接没有直接套用普通 API 的优化结论。
