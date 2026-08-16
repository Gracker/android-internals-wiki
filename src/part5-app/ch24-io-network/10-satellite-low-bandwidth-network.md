---
title: "卫星与低带宽网络适配"
chapter: "24.10"
section: "24.10"
status: finalized
pipeline_stage: finalized
applicable_versions: "Android 15 (API 35) - Android 17 (API 37); Android 16 QPR2 约束卫星网络能力；低带宽/高时延网络场景"
last_verified: "2026-08-15"
last_verified_against: "Android constrained satellite network guide current through 2026-08-15; Android 17 / API 37 docs and android-17.0.0_r1 source; FCM REST and Firebase Admin docs; current T-Satellite product pages"
confidence: high
tags: [network, satellite, low-bandwidth, connectivity, reliability]
related_chapters: ["12.1", "1.62", "12.3", "24.4", "24.5", "24.7", "24.9", "26.3"]
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
  - type: official
    path: "https://developer.android.com/reference/android/net/ConnectivityManager"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/satellite/SatelliteManager"
  - type: official
    path: "https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages#androidconfig"
  - type: official
    path: "https://firebase.google.com/docs/reference/admin/node/firebase-admin.messaging.androidconfig"
  - type: aosp
    path: "packages/modules/Connectivity/framework/src/android/net/NetworkCapabilities.java"
  - type: aosp
    path: "packages/modules/Connectivity/framework/src/android/net/ConnectivityManager.java"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/ServiceState.java"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/satellite/SatelliteManager.java"
  - type: carrier
    path: "https://www.t-mobile.com/coverage/satellite-phone-service"
  - type: carrier
    path: "https://www.t-mobile.com/news/network/t-satellite-data-ready-app-expansion"
  - type: clipping
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: local
    path: "intake/daily-info/2026-05-20.md"
---

# 卫星与低带宽网络适配

卫星直连是手机与卫星直接通信、在地面基站覆盖不足时提供有限连接的方式。这类网络通常吞吐较低、往返时延较高，连接可能间歇可用，系统还可能限制后台应用访问。本文把应用在一种网络状态下允许使用的字节数、访问频率和后台活动范围统称为“数据预算”。适配工作不能停在显示卫星图标；请求优先级、离线队列、媒体规格、推送投递和监控都要遵守同一份预算。

平台基准是 Android 17 / API 37 / `android-17.0.0_r1`。Android 15 和 Android 16 QPR2 用于说明公开 API 的版本变化；QPR（Quarterly Platform Release）是 Android 的季度平台更新。卫星短信、紧急通信、运营商开通和卫星调制解调器控制不属于普通应用的数据网络适配范围。

## 平台版本与能力边界

Android 平台分三步向应用公开相关信号：

| 版本 | 公开能力 | 应用能得出的结论 |
| --- | --- | --- |
| Android 15 / API 35 | `TRANSPORT_SATELLITE`；`ServiceState.isUsingNonTerrestrialNetwork()` | 网络使用卫星传输；电话业务注册在非地面网络 |
| Android 16 / API 36 | `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED`；卫星管理器公开类型 | 网络是否受带宽约束；卫星状态监听受权限约束 |
| Android 16 QPR2 至 Android 17 | constrained satellite network（约束卫星网络）产品能力与应用显式接入 | 在 `AndroidManifest.xml` 中声明已优化的应用，可以在仅有约束卫星网络时使用数据 |

Android 17 的 [`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) 定义 `TRANSPORT_SATELLITE = 10` 和 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED = 37`。前者在 API 35 / U 扩展 12 公开，后者在 API 36 / U 扩展 16 公开。Android 17 功能页说明，约束卫星网络支持随 Android 16 QPR2 上线；Android 17 延续并记录这项能力。

这两个信号描述不同属性：

- `hasTransport(TRANSPORT_SATELLITE)` 表示网络使用卫星传输。
- 缺少 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED` 表示网络受带宽约束。
- 卫星网络也可能带有“不受带宽约束”能力。官方仍建议在所有卫星网络上减少数据用量。
- 非卫星网络也可能缺少“不受带宽约束”能力，应用应按约束网络处理。

`NET_CAPABILITY_NOT_METERED` 表示计费属性，`NET_CAPABILITY_NOT_CONGESTED` 表示当前是否拥塞。两者都不能替代带宽约束能力。上下行带宽字段是首跳估算值，也就是设备到接入网络这一段的预测能力，并非应用到服务端的实际吞吐。

## AndroidManifest.xml 声明代表接入承诺

Android 应用默认不使用约束卫星网络。应用完成数据预算适配后，才应在 `<application>` 中加入平台要求的元数据。这段应用清单声明应用已经针对卫星数据做过优化：

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<application ...>
    <meta-data
        android:name="android.telephony.PROPERTY_SATELLITE_DATA_OPTIMIZED"
        android:value="com.example.app" />
</application>
```

`INTERNET` 用于联网，`ACCESS_NETWORK_STATE` 用于注册网络回调；`android:value` 要替换为应用包名。根据 [`constrained satellite networks` 指南](https://developer.android.com/develop/connectivity/satellite/constrained-networks)，这项声明允许应用在约束卫星网络是唯一网络时使用该网络，也让系统设置页能够识别已经优化的应用。声明不代表设备一定具备卫星功能，也不代表用户已经订阅服务、运营商允许该应用或当前位置有卫星覆盖。

Android 库不能替宿主加入这项元数据。声明代表完整应用已经控制数据量和访问频率；一个网络库无法替宿主的图片、视频、遥测事件和后台任务作出这个承诺。遥测事件是应用为分析运行情况而记录并上传的行为或性能数据。

## 以“最佳匹配网络”驱动应用预算

普通 `registerNetworkCallback()` 会报告所有匹配网络。如果应用把任一网络的能力直接写进全局布尔值，Wi-Fi、蜂窝与卫星并存时，较晚到达的回调会覆盖正在使用的网络。官方示例使用 `registerBestMatchingNetworkCallback()`，让一个回调只跟踪满足请求的最佳网络；这个调用用于监听，不会主动请求系统建立新的网络。

这段 Android 17 实现产生一份不可变网络预算快照。快照是发布后不再修改的一组网络状态，读取方不会看到更新到一半的数据。调用方提供已有的 `Handler`，因此监听器不会自行创建难以释放的线程：

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

`NetworkRequest.Builder` 默认要求“不受带宽约束”。代码移除该能力，表示约束网络也可匹配；它没有请求系统建立新的卫星网络。`onAvailable()` 之后等待按序到达的 `onCapabilitiesChanged()`，避免回调与同步查询读取到不同时间点的状态。代码等到网络能力和 `onBlockedStatusChanged()` 报告的应用身份限制状态都到达后再发布快照；UID 是系统分配给应用的 Linux 用户标识，这里的 `blocked` 状态表示系统当前限制该 UID 使用这条网络。自动传输还要确认网络已通过公网验证、没有暂停，且当前 UID 未被限制。`onLost()` 只清除当前网络，防止旧网络的丢失事件覆盖刚出现的新网络。

`start()`、`close()` 和回调共享同一 `Handler` 线程，避免生命周期字段被多个线程同时修改。若调用方拥有 `HandlerThread`，也就是带消息循环的后台线程，应先注销回调，再退出线程。当前 [`ConnectivityManager`](https://developer.android.com/reference/android/net/ConnectivityManager) 文档规定，每个 UID 通过该类 API 提交且尚未释放的网络请求与回调合计最多 100 个；重复注册却不注销会达到上限并触发运行时异常。

这段实现面向 Android 17。兼容旧系统时要同时满足编译 SDK、设备 API 级别与 SDK 扩展版本要求：编译 SDK 决定代码能否引用符号，API 级别和扩展版本决定运行设备是否提供该能力。不支持该能力的平台继续使用默认网络回调和应用实测指标。官方指南允许在较低版本上直接使用常量数值，但项目若没有跨 QPR 验证环境，不应让这些数值进入业务层。Android 16 设备注册回调时还要按官方建议处理 `ConnectivityManager` 抛出的异常。

`registerBestMatchingNetworkCallback()` 反映请求的最佳匹配网络。若应用把某个 `Network` 显式绑定到专用客户端，应读取该绑定网络的能力，不能把全局快照套在所有套接字上。VPN 也可能改变应用的实际出站路径，测试中要覆盖 VPN 开关。

## NTN（非地面网络）状态不能替代数据网络能力

NTN 是 non-terrestrial network，即非地面网络。Android 15 的 [`ServiceState.isUsingNonTerrestrialNetwork()`](https://developer.android.com/reference/android/telephony/ServiceState#isUsingNonTerrestrialNetwork%28%29) 表示设备的电话业务注册信息中存在非地面网络。Android 17 [`ServiceState.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/ServiceState.java) 遍历 `NetworkRegistrationInfo`；只要一个电话业务注册条目标记为 NTN，就返回 `true`。

这个值适合解释电话业务状态，不能证明当前应用数据正在经过卫星。应用还可能使用 Wi-Fi、VPN 或另一张订阅的数据网络。数据访问与低数据模式决策应以 `NetworkCapabilities` 为准；确有电话业务界面需要时，再通过具备相应权限的电话服务回调读取 `ServiceState`。

`SatelliteManager` 的公开范围也要区分。普通应用可以使用 `PROPERTY_SATELLITE_DATA_OPTIMIZED`，并在具备 `READ_BASIC_PHONE_STATE`、`READ_PHONE_STATE`、`READ_PRIVILEGED_PHONE_STATE` 或运营商权限之一时注册公开的状态监听器。Android 17 源码中的 `getSatelliteDataOptimizedApps()`、`requestNtnSignalStrength()`、`requestTimeForNextSatelliteVisibility()` 和 `getSatelliteDisallowedReasons()` 都标为 `@SystemApi`，并要求 `SATELLITE_COMMUNICATION` 特权权限。`@SystemApi` 只向指定系统组件开放，普通第三方应用不能依赖这些方法制定网络策略。

## 先定义数据预算，再调整网络参数

约束网络更适合把少量待发送数据合并后一次传完；空闲时应停止轮询，也不发送只为维持连接的周期心跳。每个功能先回答四个问题：

- 用户没有立即发起时，这项请求能否推迟；
- 发送失败后，数据是否已经安全保存在本地；
- 同一目标能否和相邻操作合并；
- 服务端能否用幂等键识别重复提交。幂等键是客户端为一次业务操作生成的唯一标识；同一个操作重传时沿用该标识，服务端据此只处理一次。

可以把请求分成四类。分类依据是这项操作对用户的意义，不能只看 URL 或 HTTP 方法：

| 类别 | 典型操作 | 约束网络策略 |
| --- | --- | --- |
| 用户关键 | 用户主动发送短文本、确认回执、当前任务必需的小型配置 | 允许发送，缩减字段，分别显示本地保存与服务端确认状态 |
| 用户交互 | 手动刷新轻量列表、低清地图或缩略图 | 用户触发后发送，减小页大小，不连续预取 |
| 可延迟 | 内容预取、推荐刷新、非必要配置轮询 | 暂停，等待非约束网络 |
| 批量传输 | 原图、视频、大文件、全量同步、历史行为事件回传 | 默认暂停；确需发送时采用可恢复协议并给出进度 |

“用户关键”不代表可以无限重试。每次尝试都会消耗握手、请求头和载荷字节。客户端要把排队状态、最近一次错误和下一次允许尝试的时间写入持久化存储，进程重启后继续遵守同一策略。

## 超时、重试与退避围绕可恢复性设计

高时延网络不适合沿用普通移动网络的超时值，也不适合把所有超时统一放大。建立连接、写入请求、等待响应头和读取响应体是不同阶段，应根据真实卫星链路的测量分布和业务期限分别配置。

只有同时满足这些条件，重试才有意义：

- 请求是幂等的，或服务端支持幂等键；
- 失败发生在可恢复的网络阶段；
- 本地仍有足够的数据预算；
- 计划的重试时间不早于服务端 `Retry-After` 响应头指定的时间；
- 新尝试不会越过用户可理解的任务期限。

连续失败后应逐步延长等待时间，这就是重试退避；还要在等待时间上加入小幅随机偏移，让大量设备不会在同一时刻再次请求，这个偏移常称为随机抖动。退避状态按主机、接口和业务队列隔离。HTTP 429 表示请求过多，503 表示服务暂时不可用，两者要和网络不可达分别记录。TLS 证书错误、身份验证（鉴权）失败和业务校验失败不能靠网络重试解决。应用从无网络恢复时也不要同时启动所有队列，调度器应按优先级分批提交。

Android 后台任务框架 WorkManager 的 `UNMETERED` 约束只表示网络不按流量计费，不能表达 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED`。WorkManager 批量任务开始传输前，需要再次读取应用保存的网络预算；发现约束网络后结束本次工作或延后执行，同时避免反复重新入队造成额外唤醒。

## Firebase Cloud Messaging（FCM）投递也要声明数据预算

FCM HTTP v1 的 Android 配置支持 `bandwidth_constrained_ok`。项目内可能留存这种旧示意写法：

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

这个片段不能直接发送到 FCM HTTP v1：`fid` 表示 Firebase Installation ID（Firebase 安装标识符），但 HTTP v1 的 `Message` 目标应使用注册令牌 `token`、主题 `topic` 或条件 `condition`。保留该片段是为了帮助维护者识别旧配置，不能把键名原样复制到生产请求。

按当前 FCM HTTP v1 接口定义，向一个设备注册令牌发送低带宽提示可写成：

```json
{
  "message": {
    "token": "FCM_REGISTRATION_TOKEN",
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

`bandwidth_constrained_ok` 位于 `message.android`。未设置时，Android 约束卫星网络指南说明消息会等待非约束网络再投递。这个标记只用于已适配低数据模式、且用户需要及时知道的轻量消息；数据载荷保留资源标识，让客户端按当前预算决定是否获取详情。

当前 FCM HTTP v1 配置还提供 `restricted_satellite_ok`，Firebase Admin Node.js SDK 中对应 [`restrictedSatelliteOk`](https://firebase.google.com/docs/reference/admin/node/firebase-admin.messaging.androidconfig#restrictedSatelliteOk)；它表示消息可在受限卫星网络上投递。Admin SDK 中 `bandwidth_constrained_ok` 对应的属性名是 `bandwidthConstrainedOk`。带宽约束网络与受限卫星网络是两类投递条件，后者能否使用还取决于运营商设置和设备型号，服务端应按实际接入的产品选择，不能给所有推送一并开启。

`FCM_REGISTRATION_TOKEN` 要替换为目标应用实例的 FCM 注册令牌。`collapse_key` 是折叠键：同一设备上属于同一组、尚未投递的旧消息可以由新消息替代，适合“只需最新状态”的提示。TTL（time to live，存活时间）决定 FCM 最长为发送端保留消息多久。两者都要按消息语义设置，避免网络恢复后集中投递已经过期的通知。

## 先减少载荷和网络往返

协议参数只能降低剩余开销，无法抵消过大的业务载荷。低数据模式可以从这些位置减少字节：

- 列表只取当前界面需要的字段，控制单页记录数；增量游标是服务端返回的同步位置标记，客户端下次携带它，只请求该位置之后的变化；
- 图片按显示尺寸请求缩略图，禁止自动下载原图；
- 音视频关闭自动播放，按实测选择较低的每秒数据量（码率），无法维持体验时明确暂停；
- 写操作先持久化，合并可交换的相邻操作，保留每项操作的幂等键；
- 产品行为事件（常称埋点）先聚合和采样，超过保留期限后按产品规则丢弃低价值事件；
- 服务端响应避免重复返回客户端已持有的静态配置。

压缩要同时比较传输字节减少量、设备 CPU 时间、耗电和服务端兼容性。图片、视频和加密数据通常已经压缩，再套一层通用压缩的收益往往有限。压缩算法与缓存策略见 24.6，离线写入与冲突处理见 24.7。

缓存的界面文案要区分：

- 已保存到本地；
- 等待网络发送；
- 服务端已经接收；
- 发送失败，需要用户处理。

卫星覆盖可能间歇中断，本地入队不能显示成“已送达”。删除、支付、权限修改等敏感操作还要显示服务端确认结果，不能只根据客户端已经写出请求就更新完成状态。

## 协议选型没有卫星专用答案

HTTP/1.1、HTTP/2、HTTP/3、gRPC 和 WebSocket 的表现取决于代理、网关、服务端、握手复用与连接存活时间。RTT（round-trip time，往返时间）是数据从客户端到对端再返回所需的时间。RTT 较高时，减少往返次数、复用已建立连接通常有价值，但不能据此断言某个协议在卫星网络上固定胜出。

工程决策可以遵守这些边界：

- 保持请求主机集合稳定，复用已有连接，避免每项小操作都建立独立客户端；
- 同步交互改为“本地提交、后台发送、回执更新”，界面不等待一次长往返；
- WebSocket 和 gRPC 流的心跳、重连受服务端策略控制，后台不可用时停止保活；
- HTTP/3 需要在真实运营商路径上验证；它使用的 QUIC 传输协议通常基于 UDP，可能受网关和 UDP 路径可用性影响；
- 大文件使用可恢复上传或 HTTP 范围请求（按字节范围分段下载）时，要同时控制分块数量，避免过小分块增加往返次数；
- HTTPDNS（通过 HTTP 或 HTTPS 获取域名解析结果）查询不进入 `Dns.lookup()` 的同步路径，按 24.9 的缓存与系统解析边界处理。

卫星网络可能只允许部分应用、目标地址和协议。连接库识别出卫星传输，不代表运营商允许访问任意站点。产品界面需要提供“当前服务不可用”的明确状态。

## 运营商产品规则不属于 Android API 契约

平台元数据只表明应用已经按低数据预算适配；运营商仍可按设备、套餐、地区、覆盖和合作范围决定服务可用性。T-Mobile 的 [`T-Satellite` 服务页](https://www.t-mobile.com/coverage/satellite-phone-service) 和 [应用扩展公告](https://www.t-mobile.com/news/network/t-satellite-data-ready-app-expansion)可以用于了解一个商用产品的限制，但不能推断所有 Android 卫星网络都采用相同的受支持应用列表、速度或应用类别。

客户端应根据平台能力控制数据预算，再由服务端功能配置决定自家功能是否开放。不能用一家运营商的公开列表推断其他运营商的状态，也不能把应用清单声明显示成“服务已经开通”。

## 观测数据要区分平台判断和业务结果

每次网络预算变化记录一项轻量事件，每个请求继续使用已有网络监控系统采集各阶段耗时。建议保留这些信息：

| 观察对象 | 字段 | 用途 |
| --- | --- | --- |
| 平台能力 | 是否卫星、是否约束、是否具备 `NET_CAPABILITY_VALIDATED`、是否计费、网络切换序号 | 解释为何进入低数据模式；网络切换序号由应用在当前 `Network` 变化时递增，用于关联同一条路径上的事件 |
| 带宽提示 | 首跳上下行估算值、值是否未知 | 观察平台提示，避免当成设备到服务端的实际测速 |
| 请求阶段 | 域名解析（DNS）、连接、TLS 加密握手、首字节等待时间（TTFB）、上传、下载、总耗时 | 定位高时延出现在哪一段；TTFB 是发出请求后等到响应首个字节的时间 |
| 数据预算 | 请求与响应字节、压缩后字节、重试额外字节 | 检查降级是否减少流量 |
| 队列状态 | 待发送数量、最老任务年龄、合并数、丢弃原因 | 判断离线队列是否可恢复 |
| 用户结果 | 用户关键操作成功率、取消率、手动重试率 | 判断策略是否影响任务完成 |

`NetworkCapabilities` 的带宽字段是首跳估算，数值未知时不能替换成虚构的默认值。记录请求字节时还要注明测量范围：应用载荷、HTTP 头、TLS 加密开销与链路层开销处在不同层，不能把来源不同的数字直接比较。

卫星、位置和运营商信息可能构成敏感数据。日志使用网络类别和内部切换序号即可，避免上报精确位置、完整域名、订阅标识或设备可见卫星信息。普通应用没有必要为了性能面板申请电话状态权限。

## 验证覆盖状态变化与故障恢复

单元测试通过构造网络预算快照验证业务策略：

- 约束但非卫星、卫星但不约束、两者同时存在三种组合；
- 网络未验证、已验证、丢失和快速切换；
- 批量任务暂停后不会循环入队；
- 幂等提交在进程重启后不产生重复业务结果；
- FCM 提示只触发轻量拉取，不自动启动大同步；
- 缓存界面在本地保存、发送中、确认和失败之间正确转换。

集成测试使用可控的服务端延迟、限速、断连和错误响应，验证请求往返次数、字节数、超时与退避。平台回调可以由测试替身模拟；测试替身是行为可控、用于代替真实系统组件的实现。设备验收仍需要支持该服务的设备、系统版本和运营商网络。只模拟一个 `TRANSPORT_SATELLITE` 标志，无法覆盖真实卫星链路的网关、覆盖变化与访问控制。

上线门槛来自应用现有目标和实验基线；基线是改动前的历史数据或同一实验中的对照组：

- 用户关键任务成功率的下降没有超过团队预先约定的范围；
- 自动预取、批量上传和后台唤醒按设计减少；
- 重试产生的额外字节没有抵消载荷优化；
- 从约束网络切回普通网络后，队列分批恢复，不在短时间内集中发出大量请求；
- HTTPDNS、推送和业务服务任一不可用时，队列仍能保持可恢复状态。

不存在通用的吞吐、时延或重试阈值。卫星产品、地区和业务差异很大，脱离测试条件的固定数字没有参考价值。每个阈值都要附带设备、运营商、网络状态、样本量和业务载荷。

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
- 图片、媒体、分页、行为事件和批量同步是否共享同一网络预算；
- 指标是否区分平台首跳估算和应用到服务端的实际结果；
- 真实设备验证是否覆盖运营商限制、VPN、切网和间歇断连。

## 参考与验证

- [Android 约束卫星网络指南](https://developer.android.com/develop/connectivity/satellite/constrained-networks)
- [Android 17 功能与 API](https://developer.android.com/about/versions/17/features)
- [Android 17 `NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java)
- [Android 17 `ConnectivityManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/ConnectivityManager.java)
- [Android `NetworkCapabilities` API](https://developer.android.com/reference/android/net/NetworkCapabilities)
- [Android `ConnectivityManager` API](https://developer.android.com/reference/android/net/ConnectivityManager)
- [Android `ConnectivityManager.NetworkCallback` API](https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback)
- [Android `ServiceState` API](https://developer.android.com/reference/android/telephony/ServiceState)
- [Android 17 `ServiceState.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/ServiceState.java)
- [Android `SatelliteManager` API](https://developer.android.com/reference/android/telephony/satellite/SatelliteManager)
- [Android 17 `SatelliteManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/satellite/SatelliteManager.java)
- [FCM HTTP v1 AndroidConfig](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages#androidconfig)
- [Firebase Admin Android message configuration](https://firebase.google.com/docs/reference/admin/node/firebase-admin.messaging.androidconfig)
