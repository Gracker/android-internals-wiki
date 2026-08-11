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
related_chapters: ["12.1", "1.62", "12.3", "24.4", "24.5", "24.7", "24.10", "26.3"]
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

卫星直连让移动网络重新受到严格的数据预算约束：吞吐有限，往返时延较高，连接可能
间歇可用，系统还可能限制后台应用访问。应用适配不能停在显示一个卫星图标。请求优先
级、离线队列、媒体规格、推送投递和监控都要响应同一个网络预算。

平台基准是 Android 17 / API 37 / `android-17.0.0_r1`。Android 15 和
Android 16 QPR2 的内容只用于说明公开 API 的版本演进。卫星短信、紧急通信、运营商
开通和卫星调制解调器控制不属于普通应用的数据网络适配范围。

## 平台版本与能力边界

Android 平台分三步向应用公开相关信号：

| 版本 | 公开能力 | 应用能得出的结论 |
| --- | --- | --- |
| Android 15 / API 35 | `TRANSPORT_SATELLITE`；`ServiceState.isUsingNonTerrestrialNetwork()` | 网络使用卫星传输；电话业务注册在非地面网络 |
| Android 16 / API 36 | `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED`；卫星管理器公开类型 | 网络是否受带宽约束；卫星状态监听受权限约束 |
| Android 16 QPR2 至 Android 17 | constrained satellite network 产品能力与应用 opt-in | 声明已优化的应用可以在仅有约束卫星网络时使用数据 |

Android 17 的
[`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)
定义 `TRANSPORT_SATELLITE = 10` 和
`NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED = 37`。前者在 API 35 / U 扩展 12
公开，后者在 API 36 / U 扩展 16 公开。Android 17 功能页说明，约束卫星网络支持已
随 Android 16 QPR2 上线；Android 17 延续并正式记录这项能力。

这两个信号表达的维度不同：

- `hasTransport(TRANSPORT_SATELLITE)` 表示网络使用卫星传输。
- 缺少 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED` 表示网络受带宽约束。
- 卫星网络也可能带有“不受带宽约束”能力。官方仍建议在所有卫星网络上减少数据用量。
- 非卫星网络也可能缺少“不受带宽约束”能力，应用应按约束网络处理。

`NET_CAPABILITY_NOT_METERED` 表示计费属性，
`NET_CAPABILITY_NOT_CONGESTED` 表示当前是否拥塞。两者都不能替代带宽约束能力。
上下行带宽字段是首跳估算值，也不是应用端到端吞吐的测量结果。

## manifest 声明是接入承诺

Android 应用默认不使用约束卫星网络。应用完成数据预算适配后，才应在
`<application>` 中加入平台要求的元数据。下面的清单片段用于声明应用已经针对卫星
数据做过优化：

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<application ...>
    <meta-data
        android:name="android.telephony.PROPERTY_SATELLITE_DATA_OPTIMIZED"
        android:value="com.example.app" />
</application>
```

`INTERNET` 用于联网，`ACCESS_NETWORK_STATE` 用于注册网络回调；`android:value`
要替换为应用包名。根据
[`constrained satellite networks` 指南](https://developer.android.com/develop/connectivity/satellite/constrained-networks)，
这项声明允许应用在约束卫星网络是唯一网络时使用该网络，也让系统设置页能够识别已经
优化的应用。它不会保证设备具备卫星功能、用户已经订阅服务、运营商允许该应用或当前
位置有卫星覆盖。

Android 库不能替宿主加入这项元数据。声明代表完整应用已经控制数据量和访问频率；
一个网络库无法替宿主的图片、视频、埋点和后台任务作出这个承诺。

## 以“最佳匹配网络”驱动应用预算

普通 `registerNetworkCallback()` 会报告所有匹配网络。如果应用把其中任一网络的
能力直接写进全局布尔值，Wi-Fi、蜂窝与卫星并存时，较晚到达的回调会覆盖正在使用的
网络。官方示例使用 `registerBestMatchingNetworkCallback()`，让一个回调只跟踪满足
请求的最佳网络。

下面的 Android 17 实现用于产生一份不可变网络预算快照。调用方提供已有的
`Handler`，因此监听器不私自创建无法释放的线程：

```kotlin
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.Handler
import android.os.Looper
import androidx.annotation.RequiresApi
import java.io.Closeable

@RequiresApi(36)
class ConstrainedNetworkMonitor(
    private val connectivityManager: ConnectivityManager,
    private val handler: Handler,
    private val onChanged: (Snapshot?) -> Unit,
) : Closeable {

    data class Snapshot(
        val network: Network,
        val constrained: Boolean,
        val satellite: Boolean,
        val validated: Boolean,
        val metered: Boolean,
        val suspended: Boolean,
        val blocked: Boolean,
        val downstreamKbps: Int,
        val upstreamKbps: Int,
    ) {
        val useReducedDataMode: Boolean
            get() = constrained || satellite

        val canTransfer: Boolean
            get() = validated && !suspended && !blocked
    }

    private var current: Network? = null
    private var latestCaps: NetworkCapabilities? = null
    private var blocked: Boolean? = null
    private var registered = false

    private val request = NetworkRequest.Builder()
        .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
        .removeCapability(
            NetworkCapabilities.NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED,
        )
        .build()

    private val callback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            current = network
            latestCaps = null
            blocked = null
        }

        override fun onCapabilitiesChanged(
            network: Network,
            caps: NetworkCapabilities,
        ) {
            if (network != current) return
            latestCaps = caps
            publish(network)
        }

        override fun onBlockedStatusChanged(
            network: Network,
            blocked: Boolean,
        ) {
            if (network != current) return
            this@ConstrainedNetworkMonitor.blocked = blocked
            publish(network)
        }

        private fun publish(network: Network) {
            val caps = latestCaps ?: return
            val isBlocked = blocked ?: return
            onChanged(
                Snapshot(
                    network = network,
                    constrained = !caps.hasCapability(
                        NetworkCapabilities.NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED,
                    ),
                    satellite = caps.hasTransport(
                        NetworkCapabilities.TRANSPORT_SATELLITE,
                    ),
                    validated = caps.hasCapability(
                        NetworkCapabilities.NET_CAPABILITY_VALIDATED,
                    ),
                    metered = !caps.hasCapability(
                        NetworkCapabilities.NET_CAPABILITY_NOT_METERED,
                    ),
                    suspended = !caps.hasCapability(
                        NetworkCapabilities.NET_CAPABILITY_NOT_SUSPENDED,
                    ),
                    blocked = isBlocked,
                    downstreamKbps = caps.linkDownstreamBandwidthKbps,
                    upstreamKbps = caps.linkUpstreamBandwidthKbps,
                ),
            )
        }

        override fun onLost(network: Network) {
            if (network == current) {
                current = null
                latestCaps = null
                blocked = null
                onChanged(null)
            }
        }
    }

    private fun requireHandlerThread() {
        check(Looper.myLooper() == handler.looper)
    }

    fun start() {
        requireHandlerThread()
        check(!registered)
        connectivityManager.registerBestMatchingNetworkCallback(
            request,
            callback,
            handler,
        )
        registered = true
    }

    override fun close() {
        requireHandlerThread()
        if (!registered) return
        connectivityManager.unregisterNetworkCallback(callback)
        registered = false
        current = null
        latestCaps = null
        blocked = null
    }
}
```

`NetworkRequest.Builder` 默认要求“不受带宽约束”。代码移除该能力，表示约束网络也
可匹配；它没有请求一个新的卫星网络。`onAvailable()` 之后等待有序的
`onCapabilitiesChanged()`，避免同步查询能力造成竞态。代码等到能力和 UID blocked
状态都到达后再发布快照；自动传输还要确认网络已验证、未暂停且当前 UID 未被限制。
`onLost()` 只清除当前网络，防止旧网络的丢失事件覆盖刚出现的新网络。
`start()`、`close()` 和回调共享同一 `Handler` 线程，避免生命周期字段发生数据竞争；
若调用方拥有 `HandlerThread`，应先注销回调，再退出线程。

这段实现面向 Android 17。兼容旧系统时应同时满足编译 SDK、API 级别与 SDK 扩展
要求；不支持该能力的平台继续使用默认网络回调和应用实测指标。官方指南允许为旧版本
使用常量数值，但项目如果没有跨 QPR 的验证环境，不宜把直接写入的常量扩散到业务层。
Android 16 设备注册回调时还要按官方建议处理 `ConnectivityManager` 抛出的异常。

`registerBestMatchingNetworkCallback()` 反映请求的最佳匹配网络。若应用把某个
`Network` 显式绑定到专用客户端，应读取该绑定网络的能力，不要把全局快照套在所有
套接字上。VPN 也可能改变应用的实际出站路径，测试中要覆盖 VPN 开关。

## NTN 状态不能替代数据网络能力

Android 15 的
[`ServiceState.isUsingNonTerrestrialNetwork()`](https://developer.android.com/reference/android/telephony/ServiceState#isUsingNonTerrestrialNetwork%28%29)
表示设备的电话业务注册信息中存在非地面网络。Android 17
[`ServiceState.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/ServiceState.java)
遍历 `NetworkRegistrationInfo`，只要一个条目标记为 NTN 就返回 `true`。

这个值适合解释电话业务状态，不能证明当前应用数据正在经过卫星。应用还可能使用
Wi-Fi、VPN 或另一张订阅的数据网络。数据访问与降级决策以 `NetworkCapabilities`
为准；确有电话业务界面需要时，再通过具备相应权限的 telephony 回调读取
`ServiceState`。

`SatelliteManager` 的公开面也要区分。普通应用可使用
`PROPERTY_SATELLITE_DATA_OPTIMIZED`，并在具备电话状态权限时注册公开的状态监听器。
Android 17 源码中的 `getSatelliteDataOptimizedApps()`、
`requestNtnSignalStrength()`、`requestTimeForNextSatelliteVisibility()` 和
`getSatelliteDisallowedReasons()` 都是 `@SystemApi`，还要求卫星通信特权。普通应用
不能依赖这些方法做网络策略。

## 先定义数据预算，再调整网络参数

约束网络适合短时成批传输，长时间没有网络活动。每个功能应先回答四个问题：

- 用户没有立即发起时，这项请求能否推迟；
- 发送失败后，数据是否已经安全保存在本地；
- 同一目标能否和相邻操作合并；
- 服务端能否用幂等键识别重复提交。

可以把请求分成以下四类。分类属于产品契约，不能只由 URL 或 HTTP 方法推导：

| 类别 | 典型操作 | 约束网络策略 |
| --- | --- | --- |
| 用户关键 | 用户主动发送短文本、确认回执、当前任务所需的小型配置 | 允许发送，缩减字段，明确显示本地保存与服务端确认 |
| 用户交互 | 手动刷新轻量列表、低清地图或缩略图 | 用户触发后发送，减小页大小，不连续预取 |
| 可延迟 | 内容预取、推荐刷新、非必要配置轮询 | 暂停，等待非约束网络 |
| 批量传输 | 原图、视频、大文件、全量同步、历史埋点回放 | 默认暂停；确需发送时采用可恢复协议并给出进度 |

“用户关键”不代表无限重试。每次尝试都会消耗握手、请求头和载荷字节。客户端要把
排队状态、最近一次错误和下一次允许尝试的时间写入持久化存储，进程重启后继续遵守
同一策略。

## 超时、重试与退避围绕可恢复性设计

高时延网络不适合沿用短网络的超时值，也不适合统一把所有超时放大。连接、写入、响应
头和响应体是不同等待阶段，应从真实卫星链路的分布和业务期限推导配置。

重试满足以下条件才有意义：

- 请求是幂等的，或服务端支持幂等键；
- 失败发生在可恢复的网络阶段；
- 本地仍有足够的数据预算；
- 服务端没有通过 `Retry-After` 要求更晚重试；
- 新尝试不会越过用户可理解的任务期限。

退避使用随机抖动，并按主机、接口和业务队列隔离。429、503 与网络不可达要分别记录；
TLS 证书错误、鉴权失败和业务校验失败不能用网络重试处理。应用从无网络恢复时也不要
同时唤醒所有队列，队列调度器应按优先级分批提交。

WorkManager 的 `UNMETERED` 约束只能表达计费属性，不能表达
`NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED`。批量任务需要在 worker 开始传输前再次
读取应用保存的网络预算；发现约束网络后返回或延后，并避免在循环重调度中产生额外
唤醒。

## FCM 投递也要声明数据预算

FCM HTTP v1 的 Android 配置支持 `bandwidth_constrained_ok`。下面的请求片段用于
允许一条已经压缩过的关键消息在带宽约束网络下投递：

```json
{
  "message": {
    "fid": "FIREBASE_INSTALLATION_ID",
    "data": {
      "type": "message_hint",
      "id": "server_message_id"
    },
    "android": {
      "bandwidth_constrained_ok": true,
      "collapse_key": "message_hint"
    }
  }
}
```

该字段位于 `message.android`。未设置时，官方 constrained-network 指南说明消息会
等到非约束网络再投递。只给已经适配低带宽模式、并且用户需要及时知道的消息设置它；
数据载荷保留资源标识，让客户端按预算决定是否获取详情。

当前 Firebase Admin SDK 还公开了
[`restrictedSatelliteOk`](https://firebase.google.com/docs/reference/admin/node/firebase-admin.messaging.androidconfig#restrictedSatelliteOk)，
它表示消息可在 restricted satellite network 上投递。它与
`bandwidthConstrainedOk` 的网络类别不同，服务端应根据应用接入的卫星产品选择，
不要对所有推送同时开启。折叠键和 TTL 仍要按消息语义设置，避免恢复网络后一次投递
大量过期通知。

## 字节数和网络轮次优先

协议参数只能优化剩余成本，不能抵消过大的业务载荷。低数据模式可以从这些位置减少
字节：

- 列表只取当前界面需要的字段，使用增量游标，控制单页记录数；
- 图片按显示尺寸请求缩略图，禁止自动下载原图；
- 音视频关闭自动播放，按实测选择较低码率，无法维持体验时明确暂停；
- 写操作先持久化，合并可交换的相邻操作，保留每项操作的幂等键；
- 埋点先聚合和采样，超过保留期限后按产品规则丢弃低价值事件；
- 服务端响应避免重复返回客户端已持有的静态配置。

压缩要比较“传输字节减少量、设备 CPU 时间、耗电和服务端兼容”四项结果。已经压缩的
图片、视频和加密数据继续通用压缩，收益通常有限。压缩算法与缓存策略分别见 24.6，
离线写入与冲突处理见 24.7。

缓存的界面文案要区分：

- 已保存到本地；
- 等待网络发送；
- 服务端已经接收；
- 发送失败，需要用户处理。

卫星覆盖可能间歇中断，本地入队不能显示成“已送达”。删除、支付、权限修改等敏感
操作还要显示服务端确认结果，不能只根据客户端请求已经写出就更新最终状态。

## 协议选型没有卫星专用答案

HTTP/1.1、HTTP/2、HTTP/3、gRPC 和 WebSocket 的表现取决于代理、网关、服务端、
握手复用与连接存活时间。高 RTT 环境中，减少轮次和复用已建立连接通常有价值，但不
能据此断言某个协议在卫星网络上固定胜出。

工程决策可以遵守这些边界：

- 保持请求主机集合稳定，复用已有连接，避免每项小操作都建立独立客户端；
- 同步交互改为“本地提交、后台发送、回执更新”，界面不等待一次长往返；
- WebSocket 和 gRPC 流的心跳、重连受服务端策略控制，后台不可用时停止保活；
- HTTP/3 需要在真实运营商路径上验证，QUIC 可能受网关和可用 UDP 路径影响；
- 大文件使用可恢复上传或 Range 下载时，要同时控制分块数量，避免过小分块增加轮次；
- HTTPDNS 查询不进入 `Dns.lookup()` 的同步路径，按 24.10 的缓存与系统解析边界处理。

卫星网络可能只允许部分应用、目标和协议。连接库成功识别卫星传输，不代表运营商一定
允许任意站点。产品设计需要保留“当前服务不可用”的明确状态。

## 运营商产品规则不属于 Android API 契约

平台元数据表达应用已经优化，运营商仍可按设备、套餐、地区、覆盖和合作范围决定服务
可用性。T-Mobile 的
[`T-Satellite` 服务页](https://www.t-mobile.com/coverage/satellite-phone-service)
和[应用扩展公告](https://www.t-mobile.com/news/network/t-satellite-data-ready-app-expansion)
可以用于了解一个商用产品的限制，但不能推广成所有 Android 卫星网络都使用相同白
名单、速度或应用类别。

客户端应以平台能力控制数据预算，以服务端功能配置控制自家功能是否开放。不要根据
一个运营商的公开名单推导其他运营商状态，也不要把 manifest 声明显示成“服务已经
开通”。

## 可观测性要区分平台判断和业务结果

每次网络预算变化记录一项轻量事件，每个请求继续使用已有网络事件系统采集阶段耗时。
建议保留以下维度：

| 维度 | 字段 | 用途 |
| --- | --- | --- |
| 平台能力 | 是否卫星、是否约束、是否 validated、是否计费、网络代次 | 解释为何进入低数据模式 |
| 带宽提示 | 首跳上下行估算值、值是否未知 | 观察平台提示，避免当成端到端测速 |
| 请求阶段 | DNS、连接、TLS、TTFB、上传、下载、总耗时 | 定位高时延出现在哪一段 |
| 数据预算 | 请求与响应字节、压缩后字节、重试额外字节 | 检查降级是否减少流量 |
| 队列状态 | 待发送数量、最老任务年龄、合并数、丢弃原因 | 判断离线队列是否可恢复 |
| 用户结果 | 用户关键操作成功率、取消率、手动重试率 | 判断策略是否影响任务完成 |

`NetworkCapabilities` 的带宽字段是首跳估算，数值为未知时不能替换成虚构默认值。
请求字节也要说明统计口径：应用载荷、HTTP 头、TLS 与链路层开销不属于同一个层次。

卫星与位置、运营商信息可能构成敏感数据。日志使用网络类别和内部代次即可，避免上报
精确位置、完整域名、订阅标识或设备可见卫星信息。普通应用没有必要为了性能面板申请
电话状态权限。

## 验证覆盖状态变化与故障恢复

单元测试通过构造网络预算快照验证业务策略：

- 约束但非卫星、卫星但不约束、两者同时存在三种组合；
- 网络未验证、已验证、丢失和快速切换；
- 批量任务暂停后不会循环入队；
- 幂等提交在进程重启后不产生重复业务结果；
- FCM 提示只触发轻量拉取，不自动启动大同步；
- 缓存界面在本地保存、发送中、确认和失败之间正确转换。

集成测试使用可控服务端延迟、限速、断连和错误响应，验证请求轮次、字节数、超时与
退避。平台回调可以在测试替身中模拟，但最终验收仍需要支持该服务的设备、系统版本和
运营商网络。模拟一个 `TRANSPORT_SATELLITE` 位不能代表真实卫星链路的网关、覆盖与
访问控制。

上线门槛来自应用现有目标和实验基线：

- 用户关键任务成功率没有超出允许的回归范围；
- 自动预取、批量上传和后台唤醒按设计减少；
- 重试产生的额外字节没有抵消载荷优化；
- 从约束网络切回普通网络后，队列分批恢复且不形成请求洪峰；
- HTTPDNS、推送和业务服务任一不可用时，队列仍能保持可恢复状态。

不存在通用的吞吐、时延或重试阈值。卫星产品、地区和业务差异很大，固定数字会掩盖
测试条件。每个阈值都要附带设备、运营商、网络状态、样本量和业务载荷。

## 工程检查清单

- 应用是否已经完成数据预算适配，再加入卫星优化元数据；
- 库是否避免替宿主声明 `PROPERTY_SATELLITE_DATA_OPTIMIZED`；
- 用于监听或接受约束网络的请求是否移除默认的 `NOT_BANDWIDTH_CONSTRAINED` 能力；
- 是否同时检查缺少该能力和 `TRANSPORT_SATELLITE`；
- 是否用最佳匹配网络或实际绑定网络生成预算，避免所有网络共用一个布尔值；
- 回调是否按生命周期注销，`HandlerThread` 若由应用创建是否正常退出；
- 是否把 `ServiceState` 限定为电话业务视角；
- 是否避免调用 `SatelliteManager` 的 `@SystemApi` 方法；
- 请求是否按产品语义分级，用户关键操作是否先持久化；
- 重试是否仅用于可恢复且幂等的请求，并遵守服务端退避；
- WorkManager 任务是否在传输前复查约束网络状态；
- FCM 标记是否只用于已经适配且需要及时投递的轻量消息；
- 图片、媒体、分页、埋点和批量同步是否共享同一网络预算；
- 指标是否区分平台首跳估算和应用端到端结果；
- 真实设备验证是否覆盖运营商限制、VPN、切网和间歇断连。

## 源码与文档索引

- [Android 约束卫星网络指南](https://developer.android.com/develop/connectivity/satellite/constrained-networks)
- [Android 17 功能与 API](https://developer.android.com/about/versions/17/features)
- [Android 17 `NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)
- [Android 17 `ConnectivityManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java)
- [Android `NetworkCapabilities` API](https://developer.android.com/reference/android/net/NetworkCapabilities)
- [Android `ConnectivityManager.NetworkCallback` API](https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback)
- [Android `ServiceState` API](https://developer.android.com/reference/android/telephony/ServiceState)
- [Android 17 `ServiceState.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/ServiceState.java)
- [Android `SatelliteManager` API](https://developer.android.com/reference/android/telephony/satellite/SatelliteManager)
- [Android 17 `SatelliteManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/satellite/SatelliteManager.java)
- [FCM HTTP v1 AndroidConfig](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages#androidconfig)
- [Firebase Admin Android message configuration](https://firebase.google.com/docs/reference/admin/node/firebase-admin.messaging.androidconfig)
