---
title: 线上网络质量监控与接入层协同
chapter: '26.14'
section: '26.14'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-07-12'
last_verified_against: Android Developers docs + AOSP android-17.0.0_r1 Connectivity sources + OkHttp 5.x docs + Cronet API 143.7445.0 + Clippings references
confidence: medium
sources:
- type: clippings
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md
- type: clippings
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md
- type: clippings
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md
- type: official
  path: https://developer.android.com/reference/android/net/TrafficStats
- type: official
  path: https://developer.android.com/reference/android/net/NetworkCapabilities
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/reading-network-state
- type: official
  path: https://square.github.io/okhttp/5.x/okhttp/okhttp3/-event-listener/
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework-t/src/android/net/TrafficStats.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java
- type: official
  path: https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo
- type: library-api
  path: https://dl.google.com/dl/android/maven2/org/chromium/net/cronet-api/143.7445.0/cronet-api-143.7445.0.aar
tags:
- observability
- network
- trafficstats
- apm
- alerting
related_chapters:
- '19.18'
- '24.4'
- '24.10'
- '26.3'
- '26.5'
drafted_date: '2026-05-22'
created_by: task2a-knowledge-gap
created_date: '2026-05-22'
gap_source: 参考书素材/知识盲区/官方文档/AOSP结构
last_task2a_at: '2026-05-22T15:04:00+08:00'
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task6_review_notes: "2026-07-13 Task6 re-review: pass-light-edit。L1/L2 clean; 而不是 pattern 3→2 fixed; task9_result aligned to pass-tech-review; auto-promoted to finalized。"
task9_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: '2026-07-13'
last_task6_at: '2026-07-13T01:10:47+08:00'
last_task6_review_log: logs/review/2026-07-13-01-review.md
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-06-04'
last_task9_at: '2026-07-12T21:39:02+08:00'
last_task9_audit: '2026-07-12'
last_task9_audit_log: logs/deep-review/2026-07-12-21-audit.md
last_task9_audit_at: '2026-07-12T21:39:02+08:00'
last_task9_audit_result: auto-fixed
last_task9_audit_notes: 'idle audit auto-fix: source anchors updated from local android-35 SDK / Chromium lkgr to AOSP android-17.0.0_r1 Connectivity sources and versioned Cronet API evidence; no queue item.'
last_task9_autofix_at: '2026-07-12T21:39:02+08:00'
last_task9_autofix_log: logs/deep-review/2026-07-12-21-audit.md
last_task9_review_log: logs/deep-review/2026-06-04-09-deep-review.md
task9_review_notes: '2026-06-04 Task9 deep review: pass-tech-review。P0/P1 0；HTTP/3/Cronet
  Android 17 指标字段保留为 P3 follow-up，不阻塞发布。'
task2b_result: fixed
task2b_state: fixed
last_task2b_at: '2026-06-03T14:50:00+08:00'
task2b_fixed_by: openclaw-task2b
task2b_fixed_date: '2026-06-03'
last_task2b_review_log: logs/deep-review/2026-05-22-15-deep-review.md
updated_by: openclaw-task9
updated_date: '2026-07-12'
p0: '0'
p1: '0'
p2: '0'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: '2026-06-27'
---

# 26.14 线上网络质量监控与接入层协同

网络质量监控回答三个问题：时间花在哪个阶段，哪些用户受到影响，客户端和接入层记录的是否为同一次请求。只存接口总耗时会把队列、DNS、路由尝试、传输握手、请求发送、首个响应头、响应体读取、重定向与重试混在一个数值里。

平台行为以 `android-17.0.0_r1` 为锚点。OkHttp 5.x 和 Cronet 是独立发布的库，不能从 API 37 推导其事件字段；事件必须记录网络库、库版本和协议。连接管理见 24.4，HTTPDNS 见 24.10，底层网络 APM 见 19.18，通用采样与上报见 26.3。

## 网络监控的分层目标

一次网络故障至少有三套观察口径：客户端样本、接入层日志、系统网络状态。三者回答的问题不同。

| 观察层 | 能回答的问题 | 常见盲区 | 适合的动作 |
| --- | --- | --- | --- |
| 客户端样本 | 用户当时的网络能力、阶段耗时、失败异常、路由尝试、页面场景 | 上报通道也可能受故障影响；采样和延迟上传会改变可见分布 | 判断用户体验、圈出版本、设备、粗粒度地域或网络分组 |
| 接入层日志 | 请求是否到达入口、入口流量是否下跌、服务端处理耗时、状态码分布 | 客户端 DNS 失败、建连失败、被代理/VPN 拦截的请求可能看不到 | 秒级告警、定位入口集群/CDN/域名异常 |
| 系统网络状态 | 默认网络、传输类型、VPN、计费网络、互联网验证、受限网络 | App 拿不到无线驱动、基站、运营商内部路由的完整状态 | 解释网络切换、Captive Portal、代理/VPN 干扰 |

客户端样本解释用户侧经历，接入层日志显示已到达入口的请求，系统状态说明 App 当时可见的默认网络。三者用 `trace_id`、`request_id` 和 `attempt_id` 关联：DNS、connect 或 TLS 阶段失败的 attempt 不会到达服务器，应作为客户端记录对接入层记录的 left anti-join 结果保留，不能因服务端没有同名 ID 就丢弃。

## 客户端阶段耗时采集

客户端阶段耗时要按请求生命周期记录，不能只存一个 `duration_ms`。建议先区分四个对象：

- `trace_id` 对应一次用户操作或业务链路；
- `request_id` 对应网络库的一次逻辑调用；
- `attempt_id` 对应一次路由或连接尝试；
- `exchange_id` 对应一次请求与响应交换，重定向、认证质询等 follow-up 会产生新的 exchange。

这四层 ID 解决的是聚合问题。一个 `request_id` 下面可能出现多次 DNS、connect 或 `connectionAcquired`，也可能复用已有连接而完全没有 DNS、connect 和 TLS 事件。若采集器只为每个阶段保留一个开始时间，后一次路由尝试会覆盖前一次失败，计算出的分段之和也可能和调用总耗时对不上。

OkHttp 5.x 的 [`EventListener`](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt) 是常用采集入口。dispatcher 排队、DNS、connect、secure connect、连接获取、请求发送和响应读取事件都属于同一个 `Call`，其中 connect 系列事件可能因候选路由与 Fast Fallback 重复出现，`connectionAcquired` 也可能在一个 `Call` 中出现多次。连接复用时，DNS、connect 和 TLS 事件可能缺席。采集器应保存有序事件和对应的 attempt/exchange，不能假设事件序列固定。

Cronet 的公开入口是 `org.chromium.net.RequestFinishedInfo.Listener`。固定到这里核验的 Cronet API `143.7445.0`，[`RequestFinishedInfo.Metrics`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo.Metrics) 提供请求开始、DNS、connect、SSL、sending、response start 和 request end 时间戳，以及 socket 复用、TTFB、总耗时和可空的传输字节数。没有发生或无法取得的阶段返回 `null`；复用连接时 DNS、connect 和 SSL 通常都为空。DNS 命中本地缓存但没有复用 socket 时，Cronet 仍可给出 DNS 时间戳，所以“存在 DNS 事件”不能直接等价为“访问了远端 DNS”。

字节字段也要注明来源。`Metrics#getReceivedByteCount()` 是当前请求的传输层接收字节，不包含之前的重定向；`UrlResponseInfo#getReceivedByteCount()` 是从请求开始累计到当前响应的最小接收字节估计，包含重定向但不覆盖所有协议开销。两个字段不能混入同一指标序列。

AOSP `android-17.0.0_r1` 并未给 App 提供 `android.net.http.RequestFinishedInfo` 这一公共 API。Cronet 是独立于平台版本发布的库；App 应使用 `org.chromium.net` 公共 API，并在事件中记录 Cronet 版本。它也不会观测绕过 Cronet 的 OkHttp、`HttpURLConnection` 或 Native 自研协议。

自研网络库应把阶段事件纳入接口设计。最小事件模型可以这样设计：

| 字段组 | 示例字段 | 说明 |
| --- | --- | --- |
| 请求身份 | `trace_id`、`request_id`、`attempt_id`、`exchange_id`、`scene_id`、`endpoint_id` | `endpoint_id` 来自受控的 host/path 模板，不上传完整 URL 与 query |
| 实现信息 | `engine`、`engine_version`、`negotiated_protocol`、`collector_version` | 区分平台、网络库和采集器升级引起的口径变化 |
| 阶段时间 | `queue_ms`、`dns_ms`、`connect_ms`、`secure_handshake_ms`、`ttfb_ms`、`body_ms`、`total_ms` | 每个阶段同时记录 `observed`、`not_observed` 或 `unsupported`；连接复用不是零耗时 |
| 网络上下文 | `network_snapshot_id`、`transports`、`validated`、`metered`、`vpn`、`proxy_present` | `network_snapshot_id` 是端侧短期关联键，不上传原始 `Network` 标识 |
| 失败与重试 | `error_domain`、`error_code`、`http_code`、`route_index`、`retry_reason`、`peer_group_id` | Java 异常未必暴露稳定 errno；错误类和库内枚举优先于解析异常文案 |
| 上报状态 | `sample_rate`、`upload_channel`、`upload_delay_ms`、`dropped_reason` | 网络故障时，上报失败本身也是证据 |

这张表和 26.3 的性能指标模型保持一致：事件回调只记录轻量时间戳、枚举和引用，序列化、压缩、落盘、上传交给后台任务。主线程、OkHttp callback 或 Cronet listener 中的磁盘 I/O 会直接干扰被测请求。

## 流量与网络状态维度

`TrafficStats` 适合观察 App 的流量趋势，但它提供的是累计计数器。`android-17.0.0_r1` 的 [`TrafficStats.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework-t/src/android/net/TrafficStats.java) 明确了以下口径：

- 计数覆盖自开机以来、所有网络接口上的网络层流量，包含 TCP 和 UDP，设备重启后归零；
- `getUidRxBytes()` 和 `getUidTxBytes()` 聚合同一 UID 下的所有进程；Android 7.0 起，普通 App 查询其他 UID 会得到 `UNSUPPORTED`；
- 设备不支持某项统计时也会返回 `UNSUPPORTED`，不能把 `-1` 当作有效字节数；
- `getTotalRxBytes()` 和 `getTotalTxBytes()` 是整台设备口径，不代表当前 App。

看板应保存 `boot_id` 或等价的本次启动标记、采集时间和前后差值。发现计数变小、启动标记变化或任一端为 `UNSUPPORTED` 时，舍弃该区间差值。`TrafficStats.tagSocket()` 可以给 socket 计账加标签，却不会生成 DNS、握手和首包时间，也不能替代网络库的逐请求事件。

流量指标常用于三类分析：

- **版本回归**：新版本同等 PV 下 UID 发送字节数上升，可能是重试次数、图片规格、日志上报或轮询策略变化。
- **故障旁证**：某个运营商请求失败率升高，同时发送字节数上升、接收字节数下降，常见原因是连接建立后响应读不到或重试风暴。
- **上报通道健康度**：业务请求失败率升高时，监控上报自身的发送/接收量和延迟要单独看，避免把“没有上报”误读成“没有故障”。

`NetworkCapabilities` 描述系统当前知道的网络属性。`NET_CAPABILITY_INTERNET` 表示网络被配置为可访问互联网，不代表已经连通；`NET_CAPABILITY_VALIDATED` 表示系统探测到公共互联网，仍不能证明某个业务域名可达。Captive Portal 探测期间通常有 `INTERNET` 和 `CAPTIVE_PORTAL`，没有 `VALIDATED`。Wi-Fi、蜂窝和 VPN 是 transport；一张网络可以同时具有多个 transport，例如 VPN 运行在 Wi-Fi 与蜂窝之上。

网络状态要按样本发生时记录。使用 `registerDefaultNetworkCallback()` 时，Android 8.0 及以上会在 `onAvailable()` 后立即给出 `onCapabilitiesChanged()` 和 `onLinkPropertiesChanged()`；不要在 `onAvailable()` 内同步查询新网络属性，否则存在竞态。默认 callback 的 `onLost()` 只说明这张网络不再是 App 的默认网络，它未必已经断开。

callback 默认运行在 App 的 Connectivity 线程。回调中只更新不可变的内存快照，耗时计算与上传放到工作线程，并在不再使用时注销 callback。`Network` 对象仅在该次连接存续期内有效，同一接入点重连后也会得到新对象，因此只能在端侧短期关联，不能当作跨会话设备或网络标识。

## Native Hook 与统一网络库的边界

网络监控入口有四类：编译期插桩、库层回调、Native Hook、统一网络库。它们分别对应不同覆盖面、成本和风险。

| 方案 | 覆盖面 | 优点 | 风险 |
| --- | --- | --- | --- |
| 编译期插桩 | App 代码和可插桩三方 SDK 中的 `HttpURLConnection` / OkHttp 创建点 | 接入成本低，能补业务 trace id | 反射、动态加载、Native 请求、已混淆封装可能漏采 |
| OkHttp / Cronet 官方指标 | 使用对应网络库的请求 | 阶段口径清楚，版本兼容性由库维护 | 覆盖不到绕开统一库的 SDK；事件语义要按连接复用和重试建模 |
| Native / PLT Hook | 动态链接且符号可见的 `connect`、`send`、`recv`、`SSL_read`、`SSL_write` 等调用 | 能发现部分绕过 Java 网络层的调用和总流量 | Android 版本、ABI、符号、加固和静态链接都会影响覆盖率；发布前必须灰度 |
| 统一网络库 | App 自有业务请求 | 最适合做策略、埋点、trace id、HTTPDNS、重试和容灾 | 迁移成本高；三方 SDK 和 WebView 仍需旁路监控 |

PLT Hook 只能拦截经过目标 PLT 项的动态调用。静态链接的 BoringSSL、隐藏符号、直接系统调用以及 Cronet 的 QUIC/UDP 协议状态都可能绕开这些入口；即使捕获到 `send`/`recv`，也不能可靠恢复 HTTP/2 stream、QUIC stream 或一次逻辑请求的边界。Hook 适合补充覆盖，统一网络库和官方事件接口更适合提供可解释的阶段指标。（详见 19.18 节）

每条 Hook 样本还应记录采集器版本、ABI、命中入口与已知覆盖范围。ASM 插桩要配合构建期白名单和回滚开关；Native Hook 需要 ABI 灰度、崩溃率护栏、远程关闭和端上自检。采集失败必须 fail-open，不能阻断业务网络请求。

## 客户端与接入层对账

客户端和接入层的数字不会天然相等，差异本身也是故障信号。

| 差异类型 | 客户端看到 | 接入层看到 | 排查方向 |
| --- | --- | --- | --- |
| 请求未到达入口 | DNS 失败、connect timeout、TLS failure、代理/VPN 失败 | 没有对应 `request_id`；入口 PV 可能下跌 | DNS、运营商、CDN、证书、网络切换、HTTPDNS 缓存 |
| 入口秒级异常 | 客户端样本延迟到达或上报失败 | 入口流量、错误率、处理耗时秒级变化 | 服务端发布、入口集群、CDN、机房、限流策略 |
| 客户端维度更丰富 | 某机型/系统/版本/网络类型集中异常 | 入口只看到域名、状态码、地域或 IP 段 | App 版本、设备兼容、网络库升级、代理/VPN、运营商 |

对账 ID 必须在客户端发起请求前生成。`trace_id` 描述业务链路，`request_id` 描述网络库调用，`attempt_id` 描述客户端路由或重试。只有请求头成功发到入口时，服务端才可能读到这些 ID；DNS、connect、TLS 阶段失败的 attempt 只存在于客户端。接入层记录收到的 ID、入口节点、协商协议、状态码、服务端处理耗时和响应字节数，客户端记录相同 ID 对应的阶段与 attempt 结局。

对账时先按 `request_id + attempt_id` 区分三种集合：两侧都有记录、只有客户端记录、只有接入层记录。第一类可比较端到端耗时与服务端耗时；第二类用于分析入口前失败；第三类提示客户端采样、ID 注入或上报丢失。重定向和重试还要按 `exchange_id` 或接入层生成的 span 区分，避免把多次响应的字节数、状态码和耗时相加后误认为一次请求。

未到达入口的样本仍应保存受控证据，例如候选地址数量、脱敏后的 peer 分组、库级错误枚举、TLS 错误类别、代理/VPN 标记和网络快照。原始 DNS 列表、完整 IP、完整 URL、query、代理地址与系统 `Network` 标识不应作为通用遥测字段。

## 实时告警与离线分析

网络质量监控分为实时发现、交互式分析和离线复盘。时间窗口由业务流量与响应目标决定，下面描述职责，不给所有应用套一组固定时长。

| 层次 | 指标 | 维度控制 | 输出 |
| --- | --- | --- | --- |
| 实时发现 | 入口请求量、错误率、超时率、5xx、关键接口延迟、客户端上报延迟与预计到达量 | 只保留 endpoint、版本、粗粒度地域、网络分组等低基数字段 | 告警、影响面初判、是否回滚或切流 |
| 交互式分析 | 阶段耗时分位值、错误类别、路由尝试、重试、样本覆盖率、上报丢失率 | 按需要展开设备、系统、App 版本、CDN、peer 分组、协议和场景 | 确定故障范围和触发条件 |
| 离线复盘 | 长尾分布、失败样本聚类、版本对比、地域或网络分组趋势 | 受权限控制的明细与聚合数据，过滤低样本噪声 | 修复验证、容量规划、规则调整 |

实时告警不展开高基数字段。每个分位值与错误率都要同时展示样本数、采样率、覆盖率和数据新鲜度；低样本量下的 P90/P99 波动不能直接解释为用户体验突变。客户端网络故障还会阻断遥测上传，因此“已收到的失败率”存在幸存者偏差。接入层请求量下降、客户端待上传队列增长、上传延迟升高和预计样本缺口应一起报警。

尾延迟需要结合阶段分布。DNS 长尾提示检查解析、调度和网络切换；connect 长尾提示检查候选路由、可达性、CDN 和防火墙；TTFB 同时包含客户端到入口的传输、入口排队与服务端处理，不能单凭这一项归因服务端；body 长尾还会受响应大小、链路吞吐和应用消费速度影响。指标用于缩小检索范围，结论仍需客户端事件、接入层日志和服务端 span 相互验证。

## 网络故障证据包

一次线上网络故障的证据包要支持判定影响范围、模拟触发条件和验证修复。字段按采样策略与数据分级收集，严重故障也不能绕过隐私、权限和保留期限约束。

| 字段组 | 必要字段 | 用途 |
| --- | --- | --- |
| 用户与版本 | 轮换或 HMAC 化的关联 ID、App 版本、渠道、设备类别、Android 版本、粗粒度地区 | 判断是否集中在版本、设备类别、地区或灰度人群 |
| 网络环境 | network snapshot、transport 集合、`VALIDATED`、`CAPTIVE_PORTAL`、VPN、proxy present、计费与漫游状态、网络分组 | 解释网络切换和受限网络；MCC/MNC 在双卡或 VPN 场景不等同于请求所用链路 |
| 请求身份 | trace id、request id、attempt id、exchange id、endpoint id、协商协议、CDN/接入点、peer group | 与接入层日志对账；不记录完整 URL、query 和原始 IP |
| 阶段耗时 | queue、DNS、connect、secure handshake、sending、TTFB、body、total、复用状态与阶段可用性 | 判断可观测时间花在哪一段 |
| 失败信息 | 网络库、异常类、稳定错误枚举、HTTP 状态码、业务错误码、超时类别、路由与重试结局 | Java 层没有稳定 errno 时保留 `unknown`，不解析本地化异常消息 |
| 上报健康度 | 样本采样率、落盘成功、上传时间、上传网络、丢弃原因、压缩后大小 | 判断监控数据是否受同一故障影响 |

运营商、MCC/MNC、城市、IP、DNS server、代理、SSID/BSSID 都可能构成敏感或可识别信息。能由接入层生成的地域、网络分组和 peer 分组优先在服务端生成；端侧只收集诊断所需的最小粒度，并保留“未知”，不要用设备 SIM 信息强行填补链路归属。

26.5 给出了通用线上问题证据包模板。网络场景再补充请求尝试、阶段可用性、接入层日志索引和遥测上传状态，排障人员就能回答：哪个 endpoint 与协议受影响、客户端在哪个阶段结束、请求是否到达入口、服务端记录如何、样本缺口有多大。（详见 26.5 节）

## QUIC / HTTP/3 指标口径

HTTP/3 基于 QUIC，不能把 `connect_ms` 固定解释为 TCP 三次握手，也不能把 `secure_handshake_ms` 固定解释为 TCP 上的 TLS。公共指标需要使用协议中性的字段名，并记录 `negotiated_protocol`。Cronet 的 [`UrlResponseInfo#getNegotiatedProtocol()`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/UrlResponseInfo) 返回协商协议，也可能为空。

在 Cronet `143.7445.0` 中，QUIC 的 SSL 开始/结束分别等于 connect 开始/结束；0-RTT 时，connect end 表示握手确认，可能晚于 sending start。HTTP/2 与 QUIC 的后续复用 stream 会报告 socket reused，DNS、connect 和 SSL 时间随之为空。因此，同一请求中 `sendingStart < connectEnd` 只能按 Cronet 文档解释时间顺序，不能据此生成准确的 `zero_rtt_used=true`。

该版本公开的 `RequestFinishedInfo.Metrics` 没有稳定字段暴露 0-RTT 是否使用、连接迁移次数、路径验证耗时或丢包率。只有选定引擎通过公开且有版本说明的 API 提供这些数据时，才能把它们放入扩展字段，并同时记录 `engine`、`engine_version`、`metric_source` 和 availability。不要从 socket 重用、阶段先后顺序或异常文本推算协议内部状态。

## AIOps 报警算法边界

网络报警适合组合规则与时间序列模型。规则处理入口请求量突变、5xx 偏离基线、某 endpoint DNS 失败率异常等明确现象；时间序列模型处理流量周期、地域时区、节假日和运营活动带来的自然波动。

算法不能弥补指标缺失。输入没有阶段耗时、协议、样本覆盖率和上报健康度，模型只能发现某个总耗时发生变化。主入口可采用少量可解释规则，高流量 endpoint 和关键场景再使用按星期、时段和发布状态分组的历史基线。低流量接口不适合独立做 P99 异常检测，可使用错误样本聚类、相邻 endpoint 联动和人工复核。

误报和漏报也要计量。每条规则记录触发、确认故障、误报原因、漏报补录和处置动作；模型版本、训练区间、特征 availability 与阈值配置需要可追溯。规则变更先影子运行，再根据历史回放和线上反馈决定是否通知值班。

## Wi-Fi 稳定性与系统网络验证

应用侧无法从普通公共 API 获得 Wi-Fi 射频、AP 拥塞和运营商内部路由的完整事实，但可以使用系统能力缩小检索范围。`NET_CAPABILITY_VALIDATED` 只说明系统探针在最近一次判断中访问了公共互联网；它不保证 App 的业务域名、证书链、代理路径或当前时刻仍然可用。`CAPTIVE_PORTAL=true` 且 `VALIDATED=false` 是门户登录的重要旁证，也不是业务错误的唯一原因。

Wi-Fi 不能被默认标记为“不计费”或“比蜂窝快”，应分别读取 `NOT_METERED` 和系统给出的带宽估计，并把估计值当作提示而非实测吞吐。VPN 网络还可能同时带有 VPN、Wi-Fi 和蜂窝 transport，数据模型应保存集合，不要用单值枚举覆盖信息。

系统和厂商的网络选择策略会在会话内切换默认网络。网络快照应绑定到 request/attempt：请求 A 在旧默认网络失败，请求 B 切换后成功，两条样本不能聚合成同一网络的自动恢复。默认 callback 的 `onLost()` 也只代表网络失去默认地位；若业务显式绑定了其他 `Network`，必须使用该请求选中的网络快照，而不是全局默认快照。

Android 官方的 [Read network state](https://developer.android.com/develop/connectivity/network-ops/reading-network-state) 说明了 `Network` 生命周期、多 transport、`VALIDATED`、callback 顺序和 `onLost()` 边界；平台实现可对照 `android-17.0.0_r1` 的 [`ConnectivityManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java) 与 [`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)。

## 收束

可用的网络质量系统不会把所有问题压成一个平均耗时。客户端保存逻辑调用、attempt、exchange、阶段 availability 和请求所用网络的快照；接入层保存已经到达入口的事实；遥测链路报告自身的延迟与缺口。三侧记录用 trace/request/attempt ID 对账，再结合协议、网络分组和库版本解释差异。这样得到的结论既能指出时间花在哪一段，也会明确哪些阶段没有观测到、哪些请求从未到达服务器。
