---

title: "线上网络质量监控与接入层协同"
chapter: "26.17"
status: finalized
drafted_date: "2026-05-22"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-22"
last_verified_against: "Android Developers docs 2026-05-22 + local Android SDK sources android-34/android-35 + OkHttp 5.x docs + Clippings structure references"
confidence: medium
sources:
 - type: clippings
 path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
 - type: clippings
 path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
 - type: clippings
 path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 20.md"
 - type: official
 path: "https://developer.android.com/reference/android/net/TrafficStats"
 - type: official
 path: "https://developer.android.com/reference/android/net/NetworkCapabilities"
 - type: official
 path: "https://developer.android.com/develop/connectivity/network-ops/reading-network-state"
 - type: official
 path: "https://square.github.io/okhttp/5.x/okhttp/okhttp3/-event-listener/"
 - type: aosp
 path: "/Users/gracker/Android/sources/android-35/android/net/TrafficStats.java"
 - type: aosp
 path: "/Users/gracker/Android/sources/android-35/android/net/NetworkCapabilities.java"
 - type: aosp
 path: "/Users/gracker/Android/sources/android-35/android/net/ConnectivityManager.java"
 - type: aosp
 path: "https://chromium.googlesource.com/chromium/src/+/lkgr/components/cronet/android/api/src/org/chromium/net/RequestFinishedInfo.java"
tags: [observability, network, trafficstats, apm, alerting]
related_chapters: ["19.23", "24.4", "24.10", "26.3", "26.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "参考书素材/知识盲区/官方文档/AOSP结构"
last_task2a_at: "2026-05-22T15:04:00+08:00"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task6_result: pass-light-edit
task9_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-06-04"
last_task6_at: "2026-06-04T03:10:02+08:00"
last_task6_review_log: "logs/review/2026-05-22-15-review.md"
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-04"
last_task9_at: "2026-06-04T09:20:00+08:00"
last_task9_audit: "2026-06-22"
last_task9_audit_log: logs/deep-review/2026-06-22-06-audit.md
last_task9_review_log: logs/deep-review/2026-06-04-09-deep-review.md
task9_review_notes: "2026-06-04 Task9 deep review: pass-tech-review。P0/P1 0；HTTP/3/Cronet Android 17 指标字段保留为 P3 follow-up，不阻塞发布。"
task2b_result: fixed
task2b_state: fixed
last_task2b_at: "2026-06-03T14:50:00+08:00"
task2b_fixed_by: "openclaw-task2b"
task2b_fixed_date: "2026-06-03"
last_task2b_review_log: "logs/deep-review/2026-05-22-15-deep-review.md"
updated_by: "openclaw-task9"
updated_date: "2026-06-04"
p0: 0
p1: 0
p2: 0
section: "26.17"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-27
---

# 26.17 线上网络质量监控与接入层协同

<!-- outline-start -->
## 要点

### 🔹 网络监控的分层目标
说明客户端样本、接入层日志和系统网络状态各自回答的问题，避免只用接口总耗时判断网络故障。

### 🔹 客户端阶段耗时采集
覆盖 DNS、建连、TLS、首包、响应体、重试、队列等待等阶段，并说明 OkHttp、Cronet、自研网络库的采集入口差异。

### 🔹 流量与网络状态维度
梳理 TrafficStats、NetworkCapabilities、默认网络切换、VPN/代理/计费网络等维度在归因中的作用。

### 🔹 Native Hook 与统一网络库的边界
对比插桩、PLT Hook、统一网络库、官方指标接口的覆盖面、成本和发布风险。

### 🔹 客户端与接入层对账
说明客户端未到达接入层、接入层秒级告警、客户端维度更丰富三类差异，以及 request id / trace id 的对账方式。

### 🔹 实时告警与离线分析
区分分钟级 PV/错误率告警、小时级维度圈选、P90/P99 尾延迟分析和运营商/地域/CDN 归因。

### 🔹 网络故障证据包
定义一次线上网络故障应保留的字段：网络类型、运营商、域名、IP、协议、错误码、阶段耗时、重试次数和上报通道状态。

## 扩展

### 🔸 QUIC / HTTP/3 指标口径
说明 QUIC 下 TCP/TLS 字段不再直接适用，需要协议类型、连接迁移和 0-RTT 单独建模。

### 🔸 AIOps 报警算法边界
对规则告警、时间序列异常检测和混合策略做工程取舍，标注误报、漏报和历史基线要求。

### 🔸 Wi-Fi 稳定性与系统网络验证
关联 NetworkCapabilities VALIDATED、Captive Portal、厂商 Wi-Fi 质量判断与应用侧可观测边界。

<!-- outline-end -->

网络质量监控回答三个问题：慢发生在哪一段？影响哪些用户？客户端和接入层看到的是不是同一件事？只看接口总耗时，DNS、建连、TLS、服务端等待、响应体读取、重试和本地队列等待全搅在一起，排障时只能按经验猜。

本节把 24.4 的连接管理、24.10 的 HTTPDNS 边界、19.23 的网络 APM 采集和 26.3 的指标上报模型串到同一张网络质量表里，让读者能从一条慢请求出发，判断瓶颈在哪一段，圈出影响范围，再用接入层日志对账。

## 网络监控的分层目标

一次网络故障至少有三套观察口径：客户端样本、接入层日志、系统网络状态。三者回答的问题不同。

| 观察层 | 能回答的问题 | 常见盲区 | 适合的动作 |
| --- | --- | --- | --- |
| 客户端样本 | 用户当时的网络类型、阶段耗时、失败异常、重试次数、页面场景 | 上报通道也可能受故障影响；采样会丢失部分长尾样本 | 判断用户体验、圈出机型/运营商/地域/版本 |
| 接入层日志 | 请求是否到达入口、入口流量是否下跌、服务端处理耗时、状态码分布 | 客户端 DNS 失败、建连失败、被代理/VPN 拦截的请求可能看不到 | 秒级告警、定位入口集群/CDN/域名异常 |
| 系统网络状态 | 默认网络、传输类型、VPN、计费网络、互联网验证、受限网络 | App 拿不到无线驱动、基站、运营商内部路由的完整状态 | 解释网络切换、Captive Portal、代理/VPN 干扰 |

客户端样本适合解释“用户为什么慢”，接入层日志适合发现“服务入口是否异常”，系统网络状态适合判断“这条样本处在什么网络环境”。一个可靠的看板要能把同一个 `request_id` 或 `trace_id` 同时落在三套口径里，否则客户端和服务端各看一张图，很容易把同一场故障拆成两个结论。

## 客户端阶段耗时采集

客户端阶段耗时要按请求生命周期记录，不要只存一个 `duration_ms`。一条 HTTP 请求至少要保留这些时间段：排队等待、DNS、TCP 建连、TLS 握手、连接复用命中、请求头/请求体发送、首包等待、响应体读取、重试与 follow-up。24.10 已经讲过 `Dns.lookup()` 在 OkHttp 建连前同步执行，这里只记录网络质量看板需要的指标口径，避免重复展开 HTTPDNS 接入细节。

OkHttp 的 `EventListener` 是 Android 端最常用的阶段采集入口。官方文档列出的事件包含 dispatcher queue、DNS、connect、secure connect、connection acquire/release、request headers/body、response headers/body，并且说明连接复用时 DNS 和 connect 事件可能不会出现，重试和 follow-up 会重复触发事件序列。采集代码要按一次 `Call` 内的多次 exchange 建模，不能把第二次重试的 `connectStart` 覆盖到第一次失败样本上。

Cronet 的口径更接近 Chromium 网络栈。公开 Cronet API 的稳定包名是 `org.chromium.net.RequestFinishedInfo`，其中 `Metrics` 提供 DNS、connect、SSL、sending、response 阶段时间戳、socket 复用判断、TTFB、总耗时和传输字节数。采集入口是 `RequestFinishedInfo.Listener` 的 `onRequestFinished(RequestFinishedInfo)` 回调。

需要注意：Android platform 的 `android.net.http.RequestFinishedInfo` 是隐藏/版本化实现细节（android-34 SDK source 中带 `{@hide}` / prototype 注释，android-35 SDK source 中已无该文件），不作为 App 侧稳定 API。App 接入应使用 `org.chromium.net` 包下的 public Cronet API，或通过 AndroidX Cronet wrapper（`androidx.cronet`）。

Cronet 适合统一接入 Chromium 网络栈的业务，但不能覆盖绕过 Cronet 的 OkHttp、`HttpURLConnection` 或 Native 自研协议。

自研网络库要从开始就把阶段事件作为协议的一部分，不要等线上问题多了再补埋点。最小事件模型可以这样设计：

| 字段组 | 示例字段 | 说明 |
| --- | --- | --- |
| 请求身份 | `request_id`、`trace_id`、`scene_id`、`host_pattern`、`path_pattern` | `host_pattern` 和 `path_pattern` 负责聚合，不能直接上报完整 URL Query |
| 阶段时间 | `queue_ms`、`dns_ms`、`tcp_ms`、`tls_ms`、`ttfb_ms`、`body_ms`、`total_ms` | 缺失阶段用显式状态表示，例如 connection reuse 时 `tcp_ms=null`、`reused=true` |
| 网络上下文 | `transport`、`validated`、`metered`、`vpn`、`proxy`、`network_id` | 结合 `NetworkCapabilities` 和业务网络层记录 |
| 失败与重试 | `error_domain`、`errno`、`http_code`、`retry_count`、`route_index`、`ip_hash` | IP 可 hash 或按网段聚合，避免泄露内部拓扑 |
| 上报状态 | `sample_rate`、`upload_channel`、`upload_delay_ms`、`dropped_reason` | 网络故障时，上报失败本身也是证据 |

这张表和 26.3 的性能指标模型保持一致：端侧入口只记录轻量时间戳和枚举字段，序列化、压缩、落盘、上传放到后台。主线程或 OkHttp callback 里做重 I/O，会让监控代码变成新的尾延迟来源。

## 流量与网络状态维度

`TrafficStats` 适合记录 App 级流量变化。Android API reference 提供 `getUidRxBytes()`、`getUidTxBytes()`、`getTotalRxBytes()`、`getTotalTxBytes()` 等接口；本地 Android 35 SDK source 中 `getUidRxBytes(int uid)` 和 `getUidTxBytes(int uid)` 仍是 UID 维度读取入口。它能说明“这段时间 App 收发了多少字节”，不能说明某个请求慢在 DNS、TLS 还是服务端等待。

流量指标适合放在三类场景里：

- **版本回归**：新版本同等 PV 下 UID 发送字节数上升，可能是重试次数、图片规格、日志上报或轮询策略变化。
- **故障旁证**：某个运营商请求失败率升高，同时发送字节数上升、接收字节数下降，常见原因是连接建立后响应读不到或重试风暴。
- **上报通道健康度**：业务请求失败率升高时，监控上报自身的发送/接收量和延迟要单独看，避免把“没有上报”误读成“没有故障”。

`NetworkCapabilities` 负责描述当前网络能做什么。Android 官方文档把 `NET_CAPABILITY_VALIDATED` 用于表示系统验证过该网络可访问公共互联网；Captive Portal 登录后网络会获得 `VALIDATED` 并失去 `CAPTIVE_PORTAL`。它还提供 `TRANSPORT_WIFI`、`TRANSPORT_CELLULAR`、`TRANSPORT_VPN` 等传输类型，以及 `NET_CAPABILITY_NOT_METERED`、`NET_CAPABILITY_NOT_ROAMING` 等能力。

网络状态要按“样本发生时”记录，而不是只在 App 启动时读一次。默认网络可能在一次会话中从 Wi-Fi 切到蜂窝，VPN 的 underlying network 也可能变化。`ConnectivityManager.NetworkCallback` 能收到可用性、丢失和能力变化；Android 文档说明 callback 默认运行在 App 的 connectivity thread。采集代码只更新内存态网络快照，不要在 callback 中做同步上报。

## Native Hook 与统一网络库的边界

网络监控入口有四类：编译期插桩、库层回调、Native Hook、统一网络库。它们分别对应不同覆盖面、成本和风险。

| 方案 | 覆盖面 | 优点 | 风险 |
| --- | --- | --- | --- |
| 编译期插桩 | App 代码和可插桩三方 SDK 中的 `HttpURLConnection` / OkHttp 创建点 | 接入成本低，能补业务 trace id | 反射、动态加载、Native 请求、已混淆封装可能漏采 |
| OkHttp / Cronet 官方指标 | 使用对应网络库的请求 | 阶段口径清楚，版本兼容性由库维护 | 覆盖不到绕开统一库的 SDK；事件语义要按连接复用和重试建模 |
| Native / PLT Hook | `connect`、`send`、`recv`、`SSL_read`、`SSL_write` 等底层调用 | 能发现绕过 Java 网络层的调用和总流量 | Android 版本、ABI、符号、加固、静态链接都会影响稳定性；发布前必须灰度 |
| 统一网络库 | App 自有业务请求 | 最适合做策略、埋点、trace id、HTTPDNS、重试和容灾 | 迁移成本高；三方 SDK 和 WebView 仍需旁路监控 |

工程决策上，Hook 适合补盲区，统一网络库适合承载稳定能力。19.23 已经展开网络 APM 的底层捕获原理；放到线上质量监控里，指标可解释要排在覆盖所有 socket 前面。覆盖率提高但误归因增加，看板会更难用。（详见 19.23 节）

发布风险按能力分级。纯 `EventListener` 采集可以随版本发布；ASM 插桩要配合构建期白名单和回滚开关；Native Hook 必须有 ABI 灰度、崩溃率护栏、远程关闭和端上自检。不要在全量用户上直接启用新的 Hook 表。

## 客户端与接入层对账

客户端和接入层的数字不同很正常，差异要可解释。常见差异有三类。

| 差异类型 | 客户端看到 | 接入层看到 | 排查方向 |
| --- | --- | --- | --- |
| 请求未到达入口 | DNS 失败、connect timeout、TLS failure、代理/VPN 失败 | 没有对应 `request_id`，入口 PV 下跌 | DNS、运营商、CDN、证书、网络切换、HTTPDNS 缓存 |
| 入口秒级异常 | 客户端样本延迟到达或上报失败 | 入口流量、错误率、处理耗时秒级变化 | 服务端发布、入口集群、CDN、机房、限流策略 |
| 客户端维度更丰富 | 某机型/系统/版本/网络类型集中异常 | 入口只看到域名、状态码、地域或 IP 段 | App 版本、设备兼容、网络库升级、代理/VPN、运营商 |

对账字段要在请求开始时生成，并贯穿客户端、接入层和业务服务。推荐做法是业务 trace id 描述一次用户操作，request id 描述一次网络请求，attempt id 描述一次路由尝试或重试。接入层日志至少要记录 request id、trace id、入口节点、源 IP 段、协议、状态码、服务端处理耗时和响应字节数；客户端样本记录同一组 id 与阶段耗时。

未到达接入层的样本要保留失败证据。DNS 返回的 IP 列表、被尝试的 IP hash、连接错误码、TLS 错误、代理/VPN 状态、默认网络 id、`NetworkCapabilities` 快照，都比一句 `timeout` 更有价值。对 CDN 或多 IP 调度来说，只记录域名会把故障范围放大，定位人员看不到是哪组 IP 或哪条 route 出问题。

## 实时告警与离线分析

网络质量监控要拆成两个节奏：实时告警负责发现问题，离线分析负责圈出范围和解释原因。

| 节奏 | 时间窗口 | 指标 | 维度控制 | 输出 |
| --- | --- | --- | --- | --- |
| 实时告警 | 秒级到分钟级 | PV、错误率、超时率、入口 5xx、P90 / P99 总耗时、上报延迟 | 只保留域名、版本、国家/省份、运营商、网络类型等少数字段 | 告警、影响面初判、是否回滚或切流 |
| 小时级分析 | 30 分钟到数小时 | 阶段耗时分位值、错误码分布、重试次数、上报失败率 | 放开机型、系统、App 版本、CDN、IP 段、协议、页面场景 | 圈定故障范围和触发条件 |
| 日级复盘 | 天级 | 长尾分布、失败样本聚类、版本对比、地域/运营商趋势 | 全字段离线聚合，过滤低样本噪声 | 修复验证、容量规划、规则调整 |

实时告警不要把所有维度都展开。维度过多会让单个桶样本数过低，误报和漏报都会增加。分钟级监控通常舍弃 UV，只按 PV 和少数维度做报警；这个取舍仍适合移动端网络监控。用户数、尾延迟细分和复杂归因放到离线分析里做。

尾延迟要看阶段分布，不要只看总耗时 P99。DNS P99 升高通常指向解析、调度或网络切换；connect P99 升高更接近 TCP 可达性、运营商、CDN 或防火墙；TTFB P99 升高可能是服务端处理、入口拥塞或请求排队；body P99 升高常见于大响应体、限速、弱网和应用消费速度。分段指标能让告警直接指向下一步证据。

## 网络故障证据包

一次线上网络故障的证据包要能支持三件事：判定影响范围、复现或模拟条件、验证修复是否生效。字段不必一次全量上报，但命中严重故障、用户反馈、重试上限、长尾阈值时，要把证据补齐。

| 字段组 | 必要字段 | 用途 |
| --- | --- | --- |
| 用户与版本 | 匿名用户 ID、会话 ID、App 版本、渠道、设备型号、Android 版本、系统语言/地区 | 判断是否集中在版本、机型、地区或灰度人群 |
| 网络环境 | 默认网络 transport、`VALIDATED`、`CAPTIVE_PORTAL`、VPN、代理、计费网络、漫游、运营商、MCC/MNC、国家/省份/城市 | 解释网络切换、运营商和受限网络问题 |
| 请求身份 | trace id、request id、attempt id、域名、path pattern、协议、端口、CDN/接入点、IP hash | 与接入层日志对账，定位入口或 IP 段 |
| 阶段耗时 | queue、DNS、TCP、TLS、TTFB、body、total、重试间隔、连接复用状态 | 判断慢发生在哪一段 |
| 失败信息 | Java 异常类、errno、TLS alert、HTTP 状态码、业务错误码、超时类型、重试次数、是否命中降级 | 区分网络失败、服务端失败和业务失败 |
| 上报健康度 | 样本采样率、落盘成功、上传时间、上传网络、丢弃原因、压缩后大小 | 判断监控数据是否受同一故障影响 |

26.5 已经给出通用线上问题证据包模板；网络场景要把“请求尝试”和“接入层日志索引”加进去。排障单里至少要能填出：哪个域名、哪个协议、哪个网络类型、哪个运营商、哪一段耗时异常、客户端样本是否到达接入层、上报通道是否正常。（详见 26.5 节）

## QUIC / HTTP/3 指标口径

QUIC / HTTP/3 会改变传统 TCP/TLS 阶段的含义。HTTP/3 基于 QUIC，连接建立、TLS 1.3 加密握手和传输可靠性都在 QUIC 层处理；0-RTT、连接迁移、connection id、UDP 路径验证都会影响耗时解释。继续把所有字段命名为 `tcp_ms`、`tls_ms`，会让看板误导排障人员。（Android 17 / Cronet 当前 HTTP/3 指标字段官方文档待补充）

协议字段要升级成显式模型：`protocol=h1/h2/h3`、`transport=tcp/quic`、`handshake_ms`、`zero_rtt_used`、`connection_migration_count`、`path_validation_ms`、`packet_loss_estimate`。在 h1/h2 下继续记录 TCP/TLS 分段；在 h3 下记录 QUIC handshake 和首包等待，并把连接迁移单独作为事件。这样同一张看板可以比较用户体验，又不会把协议内部阶段强行套成 TCP 字段。

## AIOps 报警算法边界

网络报警适合规则和时间序列模型混合使用。规则报警适合处理明确阈值，例如入口 PV 暴跌、5xx 率超过基线、某域名 DNS 失败率突增。时间序列异常检测适合处理周期性流量和地域差异，例如午晚高峰、节假日、运营活动带来的自然波动。

算法不能替代指标设计。输入字段缺少阶段耗时、运营商、地域、协议和上报健康度，再复杂的模型也只能发现“某个总耗时变了”。工程上更稳的做法是先用少量强规则保护主入口，再对高流量域名和高价值场景启用历史基线。低流量接口不要强行做 P99 异常检测，样本不足时用错误样本聚类和人工复核更可靠。

误报和漏报要被当成产品指标管理。每条告警规则记录触发次数、确认故障次数、误报原因、漏报补录原因和处置动作。规则变更也要走灰度：先影子运行，只记录不通知；确认一段时间后再接入值班通知。

## Wi-Fi 稳定性与系统网络验证

应用侧不能直接知道 Wi-Fi 射频质量、AP 拥塞和基站状态，但可以利用系统给出的网络能力缩小范围。`NET_CAPABILITY_VALIDATED` 表示系统验证网络可访问公共互联网；`NET_CAPABILITY_CAPTIVE_PORTAL` 表示网络可能需要登录门户。用户投诉“Wi-Fi 满格但打不开”时，客户端样本里的 `VALIDATED=false`、`CAPTIVE_PORTAL=true`、默认网络频繁切换，会比 RSSI 文案更有排障价值。

厂商 Wi-Fi 助手、蜂窝补偿和自适应 WLAN 会让同一会话内的默认网络切换更频繁。应用侧要把网络快照绑定到每次请求，而不是绑定到页面。请求 A 在 Wi-Fi 上失败，请求 B 已经切到蜂窝成功，这两条样本不能被聚合成“同一网络下恢复”。网络 id、transport、validated 状态和时间戳要一起进入样本。

## 收束

线上网络质量监控的可用性，取决于样本能否解释差异。客户端保留阶段耗时和网络状态，接入层保留秒级入口事实，二者用 request id / trace id 对账。告警用少量强指标快速发现问题，离线分析再展开地域、运营商、协议、CDN 和机型。排障人员拿到的就是一组可对账的证据，而不是一串互相矛盾的平均耗时。
