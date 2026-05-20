---
title: "卫星与低带宽网络适配"
chapter: "24.11"
section: "24.11"
status: ready-for-review
drafted_date: "2026-05-20"
applicable_versions: "Android 15 (API 35) - Android 17 (API 37); Android 16 QPR2 约束卫星网络能力；低带宽/高时延网络场景"
last_verified: "2026-05-20"
last_verified_against: "Android Developers constrained satellite networks 2026-02-26; Android 17 features; AOSP main NetworkCapabilities.java / ServiceState.java"
confidence: medium
tags: [network, satellite, low-bandwidth, connectivity, reliability]
related_chapters: ["12.2", "12.5", "12.6", "24.4", "24.5", "24.7", "24.10", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-20"
gap_source: "官方文档/每日信息/章节深挖"
gap_score: 15
sources:
  - type: official
    path: "https://developer.android.com/develop/connectivity/satellite/constrained-networks"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/about/versions/15/features"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/reading-network-state"
  - type: official
    path: "https://developer.android.com/reference/android/net/NetworkCapabilities"
  - type: aosp
    path: "packages/modules/Connectivity/framework/src/android/net/NetworkCapabilities.java"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/ServiceState.java"
  - type: carrier
    path: "https://www.t-mobile.com/coverage/satellite-phone-service"
  - type: carrier
    path: "https://www.t-mobile.com/news/network/t-satellite-data-ready-app-expansion"
  - type: clipping
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: local
    path: "intake/daily-info/2026-05-20.md"
---

# 24.11 卫星与低带宽网络适配

卫星直连把网络退回到稀缺资源模型：吞吐低、RTT 高、覆盖有间隙，系统和运营商都可能限制 App 的数据访问。App 适配的重点不是识别到“卫星”后换一个图标，而是把请求调度、缓存、媒体、同步和监控都切到低带宽模式。

应用侧策略只引用系统网络状态和协议结论，不重复展开 ConnectivityService、DNS、HTTPDNS 和协议栈原理；对应机制分别见 12.5、12.6、24.10 和 24.5 节。

## 场景边界与版本口径

Android 15 已公开卫星连接状态感知能力，`ServiceState.isUsingNonTerrestrialNetwork()` 可用于判断设备是否连接到非地面网络；Android 15 同时支持 SMS、MMS 和预装 RCS 在卫星连接下发送接收消息。[已验证: 官方文档, developer.android.com/about/versions/15/features] [已验证: AOSP main, frameworks/base/telephony/java/android/telephony/ServiceState.java]

Android 17 features 页面把“低带宽卫星网络”列为连接性改进，并说明该能力已随 Android 16 QPR2 上线。[已验证: 官方文档, developer.android.com/about/versions/17/features] 对 App 来说，更可操作的入口是 Android Developers 的 constrained satellite networks 指南：App 默认不会使用这类网络；如果要使用，需要在 manifest 声明已针对卫星数据约束优化，并在运行时按网络能力降级。[已验证: 官方文档, developer.android.com/develop/connectivity/satellite/constrained-networks]

四类网络的处理边界不同：

- 普通弱网：Wi-Fi 或蜂窝仍是常规网络，只是 RTT、丢包或吞吐指标变差，App 可通过测速、超时率和失败率进入弱网模式。
- 蜂窝拥塞或计费网络：`NET_CAPABILITY_NOT_CONGESTED`、`NET_CAPABILITY_NOT_METERED`、`NET_CAPABILITY_TEMPORARILY_NOT_METERED` 可辅助判断，但它们不等同于卫星网络。
- 非地面网络：Android 15 的 `ServiceState.isUsingNonTerrestrialNetwork()` 能解释为什么完整网络服务不可用；它属于 telephony 视角，不替代 `ConnectivityManager` 的数据网络选择。
- 约束卫星网络：Android 16 QPR2 / Android 17 的 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED` 和 `TRANSPORT_SATELLITE` 更接近 App 降级入口。缺少 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED` 表示该网络受带宽约束；具备 `TRANSPORT_SATELLITE` 表示网络传输类型为卫星。[已验证: AOSP main, packages/modules/Connectivity/framework/src/android/net/NetworkCapabilities.java]

运营商侧的 T-Satellite 文档说明了另一层现实边界：卫星数据面向“select satellite-ready apps”，数据速度有限，服务可能延迟、受限、不可用，部分 App 可能无法运行或表现不同。[引用: https://www.t-mobile.com/coverage/satellite-phone-service] 这类规则不是 Android 平台通用契约，只能作为运营商白名单与产品边界参考。

## 网络能力识别与降级开关

降级开关建议由三类输入共同驱动：系统网络能力、App 自测指标、服务端策略。只看 `hasTransport(WIFI)` 或 `hasTransport(CELLULAR)` 会误判，官方网络状态文档也明确提醒：transport 不是带宽和计费状态的可靠代理，带宽应看 `getLinkDownstreamBandwidthKbps()` / `getLinkUpstreamBandwidthKbps()`，计费应看 `NET_CAPABILITY_NOT_METERED`。[已验证: 官方文档, developer.android.com/develop/connectivity/network-ops/reading-network-state]

Manifest 只表达 App 已完成约束网络适配，库不要替宿主声明。

```xml
<meta-data
    android:name="android.telephony.PROPERTY_SATELLITE_DATA_OPTIMIZED"
    android:value="com.example.app" />
```

这个声明允许 App 在约束卫星网络是唯一网络时使用该网络，也让系统知道该 App 可出现在卫星可用 App 列表中。[已验证: 官方文档, developer.android.com/develop/connectivity/satellite/constrained-networks]

运行时判定只保留降级入口；请求层、媒体层和同步层各自订阅这个状态。

```kotlin
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.Build
import android.os.Handler
import android.os.HandlerThread

fun registerConstrainedNetworkMode(
    connectivityManager: ConnectivityManager,
    onModeChanged: (Network, Boolean) -> Unit,
): ConnectivityManager.NetworkCallback {
    val thread = HandlerThread("ConstrainedNetworkMonitor").apply { start() }
    val handler = Handler(thread.looper)
    val request = NetworkRequest.Builder()
        .removeCapability(NetworkCapabilities.NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED)
        .build()

    val callback = object : ConnectivityManager.NetworkCallback() {
        override fun onCapabilitiesChanged(network: Network, caps: NetworkCapabilities) {
            onModeChanged(network, caps.isConstrainedOrSatellite())
        }
    }
    connectivityManager.registerNetworkCallback(request, callback, handler)
    return callback
}

private fun NetworkCapabilities.isConstrainedOrSatellite(): Boolean {
    val constrained = Build.VERSION.SDK_INT >= 36 &&
        !hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED)
    val satellite = Build.VERSION.SDK_INT >= 35 &&
        hasTransport(NetworkCapabilities.TRANSPORT_SATELLITE)
    return constrained || satellite
}
```

这段代码的边界有两点：`NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED` 是 API 36 / U Extensions 16 能力，`TRANSPORT_SATELLITE` 是 API 35 / U Extensions 12 能力；业务代码仍要兼容能力不存在、回调延迟和默认网络切换。生产实现还要加入注销回调、线程退出、错误兜底和服务端配置覆盖。

## 请求调度、超时与重试退避

约束卫星网络适合短时间突发传输，再长时间空闲。实时同步、边请求边等待 UI 的流程会被高 RTT 放大，连续重试还会挤占本来就少的数据窗口。[已验证: 官方文档, developer.android.com/develop/connectivity/satellite/constrained-networks]

请求分级可以按“是否影响用户安全和当前任务完成”来排：

- P0：紧急消息、登录态续期、关键确认回执。允许在约束网络下发送，payload 控制在最小字段集，失败后进入本地待确认队列。
- P1：配置拉取、灰度开关、离线队列提交。合并相邻请求，用幂等键保护重试，服务端返回 429 / 5xx 时按指数退避。
- P2：普通列表刷新、图片缩略图、地图轻量更新。降低分页大小，禁用预取和自动播放，只在用户明确触发时请求。
- P3：高清视频、大文件上传、全量同步、埋点批量回放。默认暂停，等到非约束网络或充电 + Wi-Fi 条件恢复后再执行。

超时不要只按常规蜂窝网络配置沿用。连接超时可以适度放宽，读写超时按业务分级设置；重试次数要少，退避要带 jitter，失败隔离要按 host / 接口 / 业务队列分开。弱网下最危险的不是单次请求失败，而是所有模块都在“失败后立刻补一次”，把有限窗口耗在重复握手和重复 payload 上。

FCM 有单独入口：服务端发送 Android 消息时可使用 `bandwidth_constrained_ok`，表示该消息允许在约束网络下投递；未带该标记的消息只在非约束网络下投递。这个标记只应给已适配低带宽模式的 App 使用。[已验证: 官方文档, developer.android.com/develop/connectivity/satellite/constrained-networks]

## 数据压缩、缓存与离线优先

低带宽模式下，缓存目标从“提升速度”扩展为“减少网络占用”。《Android 性能优化》的缓存章节给出的结构参考是：缓存容量受限时，命中率监控、淘汰策略和预加载策略要一起设计；热数据与冷数据分开处理，比单纯依赖最近访问记录更适合高频业务场景。[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

落到 App 网络层，可以按这张表拆策略：

| 对象 | 低带宽策略 | 失败兜底 | 观测指标 |
| --- | --- | --- | --- |
| 文本列表 | 字段裁剪、分页减半、只拉增量 | 使用本地快照并标注更新时间 | 响应字节数、分页成功率、缓存命中率 |
| 图片 | 只请求缩略图，按屏幕密度和可见区域裁剪 | 占位图 + 延后加载 | 图片字节数、解码失败率、P2 请求暂停数 |
| 视频/音频 | 降码率或暂停自动播放 | 明确提示当前网络不适合播放 | 首包时间、缓冲次数、用户主动重试数 |
| 写入队列 | 本地先落盘，合并同类操作，按优先级提交 | 幂等键去重，冲突由服务端返回可解释状态 | 队列长度、最老任务等待时间、提交成功率 |
| 埋点 | 本地聚合，抽样上报，延迟批量回放 | 超过保留窗口后按策略丢弃低价值事件 | 批量大小、丢弃率、回放耗时 |

离线优先架构见 24.7 节。这里补的边界是：卫星连接不是“离线”，但它的成本足够高，很多 P2/P3 行为应按离线处理。UI 要把“已本地保存、等待网络同步”和“已发送到服务端”区分清楚，否则用户会在信号恢复前误判任务已经完成。

## 协议与传输选型

不要把协议选择写成固定答案。HTTP/2、HTTP/3、gRPC、WebSocket、长轮询和短连接在高 RTT / 低吞吐网络下的表现，取决于握手次数、连接复用、队头阻塞、服务端支持、代理路径、心跳频率和 payload 形态。没有同机、同网络、同业务 payload 的数据，不能写“某协议一定更快”。

工程上更稳的做法是先减少字节和轮次，再讨论协议：

- 复用已有连接，减少 DNS、TCP/TLS 或 QUIC 握手次数；DNS 与 HTTPDNS 边界见 24.10 节。
- 把强同步接口改成“提交 + 本地状态 + 回执确认”，避免 UI 卡在一次长 RTT 上。
- WebSocket / gRPC streaming 要降低心跳频率，断线后按服务端配置退避重连，避免后台保活变成隐形耗流量任务。
- HTTP/3 的收益要按路径验证。QUIC 在部分网络能减少握手成本，但卫星链路、运营商网关和服务器配置都会影响结果。
- 大 payload 优先做语义裁剪：字段、图片规格、分页、采样率、压缩格式。压缩算法不要让低端设备在 CPU 和电量上付出更高代价，功耗侧见 25.x 相关章节。

T-Mobile 的公开材料显示，卫星可用 App 以消息、位置、天气、地图和轻量社交为主，运营商也强调“关键服务，而不是完整重数据体验”。[引用: https://www.t-mobile.com/news/network/t-satellite-data-ready-app-expansion] 这说明产品形态本身要收窄，不能只靠网络库参数把重业务改成卫星友好。

## 可观测性与灰度门禁

低带宽适配要进监控面板，否则线上只会看到“超时率升高”，看不到 App 是否按设计降级。指标采集与上报框架见 26.3 节，这里新增一组维度：

- 网络状态：`TRANSPORT_SATELLITE`、是否缺少 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED`、上下行估算带宽、是否计费、是否漫游、是否默认网络。
- 请求耗时：DNS、连接、TLS、TTFB、下载、上传、总耗时，按 host 和接口分组。
- 数据量：请求字节数、响应字节数、图片字节数、埋点批量大小、压缩前后大小。
- 稳定性：超时率、重试次数、退避命中次数、熔断次数、失败隔离次数。
- 体验结果：关键路径成功率、离线队列积压长度、最老待同步任务等待时间、用户主动重试率。
- 降级命中：预取禁用次数、P2/P3 暂停次数、低清资源命中率、缓存命中率。

灰度门禁建议按 App 版本、运营商、设备型号、国家/地区和功能模块拆。进入约束网络后，P0/P1 成功率不能低于预设阈值；P2/P3 的自动请求量必须下降；重试次数和后台网络唤醒不能上升。只要出现“低带宽模式打开后总字节数没降、重试反而上升”，就应回滚该策略。

## 运营商白名单与 App 适配边界

运营商白名单代表服务入口，不代表 Android 平台保证。T-Satellite 的公开说明包含兼容设备、户外可见天空、区域、套餐、部分 App 可用、延迟或不可用等限制。[引用: https://www.t-mobile.com/coverage/satellite-phone-service] 文档里列出的 App 类型可作为产品拆分参考：消息、位置、天气、地图、应急协作比高清视频、全量 feed 和大文件上传更适合卫星连接。

App 适配时建议把“平台能力”和“运营商策略”分开配置：平台能力由 Android API 上报；运营商策略由服务端按 MCC/MNC、国家/地区、App 版本和合作状态下发。这样即使某个运营商调整白名单或服务范围，客户端也不必重新发版。

## 多设备形态与紧急通信场景

卫星低带宽场景常发生在户外、灾害、车载、旅行和蜂窝盲区。设备形态不同，降级目标也不同：

- 手机：保消息、位置、紧急联系人和少量地图瓦片；重媒体默认暂停。
- 平板：更常见离线内容浏览，优先保证已下载资料、待同步笔记和地图缓存。
- 车载：保导航路线、位置上报、道路风险提示；不要让后台娱乐内容占用链路。
- 可穿戴：保 SOS、位置和短消息，交互要少步骤、少确认、少图片。

紧急场景里，文案要说清“已保存、发送中、已送达、发送失败”四种状态。卫星服务可能延迟或不可用，UI 不能把本地入队写成已送达。

## 与 HTTPDNS / OkHttp Dns 的关系

24.10 节已经覆盖 HTTPDNS 与 OkHttp `Dns.lookup()` 的同步执行边界。低带宽模式下沿用那里的结论：不要在 `lookup()` 内实时发 HTTPDNS 请求；应异步预取、读缓存、按 TTL 刷新，并准备系统 DNS 兜底。卫星网络下，递归依赖同一个 `OkHttpClient` 或每次建连都触发 HTTPDNS 请求，会把高 RTT 放大到所有业务请求上。

## 小结

卫星与低带宽适配的落点是资源预算：哪些请求能发、一次发多少、失败后等多久、什么时候回放、怎么确认降级有效。Android 16 QPR2 / Android 17 给了 constrained satellite networks 的平台入口，App 侧要把它接到请求调度、缓存、协议、离线队列和监控门禁里。
