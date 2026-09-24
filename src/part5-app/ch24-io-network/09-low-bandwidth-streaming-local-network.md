---
title: 低带宽、流媒体与本地网络适配
chapter: '24.9'
section: '24.9'
status: finalized
pipeline_stage: finalized
applicable_versions: Android 15 (API 35) - Android 17 (API 37); Android 16 QPR2 约束卫星网络能力；低带宽/高时延网络场景
last_verified: '2026-08-15'
last_verified_against: Android constrained satellite network guide current through 2026-08-15; Android 17 / API 37 docs and android-17.0.0_r1 source; FCM REST and Firebase Admin docs; current T-Satellite product pages
confidence: high
tags:
- network
- satellite
- low-bandwidth
- connectivity
- reliability
- android17
- streaming
- local-network
related_chapters:
- '12.1'
- '1.21'
- '12.2'
- '24.5'
- '24.6'
- '24.3'
- '24.7'
- '26.1'
- '18.1'
- '26.10'
sources:
- type: official
  path: https://developer.android.com/develop/connectivity/satellite/constrained-networks
- type: official
  path: https://developer.android.com/about/versions/17/features
- type: official
  path: https://developer.android.com/about/versions/15/features
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/reading-network-state
- type: official
  path: https://developer.android.com/reference/android/net/NetworkCapabilities
- type: official
  path: https://developer.android.com/reference/android/net/ConnectivityManager
- type: official
  path: https://developer.android.com/reference/android/telephony/satellite/SatelliteManager
- type: official
  path: https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages#androidconfig
- type: official
  path: https://firebase.google.com/docs/reference/admin/node/firebase-admin.messaging.androidconfig
- type: aosp
  path: packages/modules/Connectivity/framework/src/android/net/NetworkCapabilities.java
- type: aosp
  path: packages/modules/Connectivity/framework/src/android/net/ConnectivityManager.java
- type: aosp
  path: frameworks/base/telephony/java/android/telephony/ServiceState.java
- type: aosp
  path: frameworks/base/telephony/java/android/telephony/satellite/SatelliteManager.java
- type: carrier
  path: https://www.t-mobile.com/coverage/satellite-phone-service
- type: carrier
  path: https://www.t-mobile.com/news/network/t-satellite-data-ready-app-expansion
- type: clipping
  path: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md
- type: local
  path: intake/daily-info/2026-05-20.md
- type: official
  path: https://developer.android.com/reference/android/telephony/SubscriptionInfo#getStreamingAppMaxDownlinkKbps()
- type: official
  path: https://developer.android.com/reference/android/telephony/SubscriptionInfo#getStreamingAppMaxUplinkKbps()
- type: official
  path: https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveSubscriptionInfoList()
- type: official
  path: https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveDataSubscriptionId()
- type: official
  path: https://developer.android.com/reference/android/net/NetworkCapabilities#getSubscriptionIds()
- type: official
  path: https://developer.android.com/privacy-and-security/local-network-permission
- type: official
  path: https://developer.android.com/privacy-and-security/local-network-definition
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/blog/posts/android-17-is-here
- type: official
  path: https://developer.android.com/reference/android/net/nsd/NsdManager
- type: official
  path: https://developer.android.com/privacy-and-security/local-network-permission#errors
- type: official
  path: https://developer.android.com/reference/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection
- type: official
  path: https://developer.android.com/reference/androidx/media3/exoplayer/upstream/DefaultBandwidthMeter
- type: official
  path: https://developer.android.com/privacy-and-security/security-config
- type: research-feed
  path: intake/research-feeds/2026-04-08-11-android17-network-data-plan-streaming-access-local-network-tls.md
- type: daily-info
  path: intake/daily-info/2026-05-24.md
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]'
- type: clippings-structure
  path: '[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]'
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part5-app/ch24-io-network/10-satellite-low-bandwidth-network.md
- src/part5-app/ch24-io-network/14-android17-streaming-local-network.md
---

# 低带宽、流媒体与本地网络适配

卫星直连指手机与卫星直接通信，在地面基站覆盖不足时提供有限连接。这类网络通常吞吐较低、往返时延较高，连接可能间歇可用，系统还可能限制后台应用访问。本文把应用在一种网络状态下允许使用的字节数、访问频率和后台活动范围统称为“数据预算”。适配工作不能停在显示卫星图标；请求优先级、离线队列、媒体规格、推送投递和监控都要遵守同一份预算。

平台基准是 Android 17 / API 37 / `android-17.0.0_r1`。Android 15 和 Android 16 QPR2 用于说明公开 API 的版本变化；QPR（Quarterly Platform Release）是 Android 的季度平台更新。卫星短信、紧急通信、运营商开通和卫星调制解调器控制不属于普通应用的数据网络适配范围。

低带宽和卫星网络要求应用缩小请求、延长容错窗口并允许离线；流媒体还要根据吞吐预算调整码率。Android 17 本地网络权限影响局域网发现和连接；局域网访问是另一项必须显式处理的网络能力。

## 低带宽与卫星网络的数据预算

### 平台版本与能力边界

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

`NET_CAPABILITY_NOT_METERED` 表示计费属性，`NET_CAPABILITY_NOT_CONGESTED` 表示当前是否拥塞。两者都不能替代带宽约束能力。上下行带宽字段是首跳估算值，也就是对设备到接入网络这一段能力的预测，并非应用到服务端的实际吞吐。

### AndroidManifest.xml 声明代表接入承诺

Android 应用默认不使用约束卫星网络。应用完成数据预算适配后，才应在 `<application>` 中加入平台要求的元数据。这段应用清单声明该应用已经针对卫星数据做过优化：

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

### 以“最佳匹配网络”驱动应用预算

普通 `registerNetworkCallback()` 会报告所有匹配网络。如果应用把任一网络的能力直接写进全局布尔值，Wi-Fi、蜂窝与卫星并存时，较晚到达的回调会覆盖正在使用的网络所对应的值。官方示例使用 `registerBestMatchingNetworkCallback()`，让一个回调只跟踪满足请求的最佳网络；这个调用用于监听，不会主动请求系统建立新的网络。

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

`NetworkRequest.Builder` 默认要求“不受带宽约束”。代码移除该能力，表示约束网络也可匹配；它没有请求系统建立新的卫星网络。

`onAvailable()` 之后等待按序到达的 `onCapabilitiesChanged()`，避免回调与同步查询读取到不同时间点的状态。代码等到网络能力和 `onBlockedStatusChanged()` 报告的应用身份限制状态都到达后再发布快照；UID 是系统分配给应用的 Linux 用户标识，这里的 `blocked` 状态表示系统当前限制该 UID 使用这条网络。

自动传输还要确认网络已通过公网验证、没有暂停，且当前 UID 未被限制。`onLost()` 只清除当前网络，防止旧网络的丢失事件覆盖刚出现的新网络。

`start()`、`close()` 和回调共享同一 `Handler` 线程，避免生命周期字段被多个线程同时修改。若调用方拥有 `HandlerThread`，也就是带消息循环的后台线程，应先注销回调，再退出线程。当前 [`ConnectivityManager`](https://developer.android.com/reference/android/net/ConnectivityManager) 文档规定，每个 UID 通过该类 API 提交且尚未释放的网络请求与回调合计最多 100 个；重复注册却不注销会达到上限并触发运行时异常。

这段实现面向 Android 17。兼容旧系统时要同时满足编译 SDK、设备 API 级别与 SDK 扩展版本要求：编译 SDK 决定代码能否引用符号，API 级别和扩展版本决定运行设备是否提供该能力。不支持该能力的平台继续使用默认网络回调和应用实测指标。

官方指南允许在较低版本上直接使用常量数值，但项目若没有跨 QPR 验证环境，不应让这些数值进入业务层。

Android 16 设备注册回调时还要按官方建议处理 `ConnectivityManager` 抛出的异常。

`registerBestMatchingNetworkCallback()` 反映请求的最佳匹配网络。若应用把某个 `Network` 显式绑定到专用客户端，应读取该绑定网络的能力，不能把全局快照套在所有套接字上。VPN 也可能改变应用的实际出站路径，测试中要覆盖 VPN 开关。

### NTN（非地面网络）状态不能替代数据网络能力

NTN 是 non-terrestrial network，即非地面网络。Android 15 的 [`ServiceState.isUsingNonTerrestrialNetwork()`](https://developer.android.com/reference/android/telephony/ServiceState#isUsingNonTerrestrialNetwork%28%29) 表示设备的电话业务注册信息中存在非地面网络。

Android 17 [`ServiceState.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/ServiceState.java) 遍历 `NetworkRegistrationInfo`；只要一个电话业务注册条目标记为 NTN，就返回 `true`。

这个值适合解释电话业务状态，不能证明当前应用数据正在经过卫星。应用还可能使用 Wi-Fi、VPN 或另一张订阅的数据网络。数据访问与低数据模式决策应以 `NetworkCapabilities` 为准；确有电话业务界面需要时，再通过具备相应权限的电话服务回调读取 `ServiceState`。

`SatelliteManager` 的公开范围也要区分。普通应用可以使用 `PROPERTY_SATELLITE_DATA_OPTIMIZED`，并在具备 `READ_BASIC_PHONE_STATE`、`READ_PHONE_STATE`、`READ_PRIVILEGED_PHONE_STATE` 或运营商权限之一时注册公开的状态监听器。

Android 17 源码中的 `getSatelliteDataOptimizedApps()`、`requestNtnSignalStrength()`、`requestTimeForNextSatelliteVisibility()` 和 `getSatelliteDisallowedReasons()` 都标为 `@SystemApi`，并要求 `SATELLITE_COMMUNICATION` 特权权限。`@SystemApi` 只向指定系统组件开放，普通第三方应用不能依赖这些方法制定网络策略。

### 先定义数据预算，再调整网络参数

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

### 超时、重试与退避围绕可恢复性设计

高时延网络不适合沿用普通移动网络的超时值，也不适合把所有超时统一放大。建立连接、写入请求、等待响应头和读取响应体是不同阶段，应根据真实卫星链路的测量分布和业务期限分别配置。

只有同时满足这些条件，重试才有意义：

- 请求是幂等的，或服务端支持幂等键；
- 失败发生在可恢复的网络阶段；
- 本地仍有足够的数据预算；
- 计划的重试时间不早于服务端 `Retry-After` 响应头指定的时间；
- 新尝试不会越过用户可理解的任务期限。

连续失败后应逐步延长等待时间，这就是重试退避；还要在等待时间上加入小幅随机偏移，让大量设备不会在同一时刻再次请求，这个偏移常称为随机抖动。退避状态按主机、接口和业务队列隔离。HTTP 429 表示请求过多，503 表示服务暂时不可用，两者要和网络不可达分别记录。TLS 证书错误、身份验证（鉴权）失败和业务校验失败不能靠网络重试解决。应用从无网络恢复时也不要同时启动所有队列，调度器应按优先级分批提交。

Android 后台任务框架 WorkManager 的 `UNMETERED` 约束只表示网络不按流量计费，不能表达 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED`。WorkManager 批量任务开始传输前，需要再次读取应用保存的网络预算；发现约束网络后结束本次工作或延后执行，同时避免反复重新入队造成额外唤醒。

### Firebase Cloud Messaging（FCM）投递也要声明数据预算

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

### 先减少载荷和网络往返

协议参数只能降低剩余开销，无法抵消过大的业务载荷。低数据模式可以从这些位置减少字节：

- 列表只取当前界面需要的字段，控制单页记录数；增量游标是服务端返回的同步位置标记，客户端下次携带它，只请求该位置之后的变化；
- 图片按显示尺寸请求缩略图，禁止自动下载原图；
- 音视频关闭自动播放，按实测选择较低的每秒数据量（码率），无法维持体验时明确暂停；
- 写操作先持久化，合并可交换的相邻操作，保留每项操作的幂等键；
- 产品行为事件（常称埋点）先聚合和采样，超过保留期限后按产品规则丢弃低价值事件；
- 服务端响应避免重复返回客户端已持有的静态配置。

压缩要同时比较传输字节减少量、设备 CPU 时间、耗电和服务端兼容性。图片、视频和加密数据通常已经压缩，再套一层通用压缩的收益往往有限。压缩算法、缓存策略、离线写入与冲突处理统一见 [24.3 数据缓存与离线优先](03-data-cache-offline-first.md)。

缓存的界面文案要区分：

- 已保存到本地；
- 等待网络发送；
- 服务端已经接收；
- 发送失败，需要用户处理。

卫星覆盖可能间歇中断，本地入队不能显示成“已送达”。删除、支付、权限修改等敏感操作还要显示服务端确认结果，不能只根据客户端已经写出请求就更新完成状态。

### 协议选型没有卫星专用答案

HTTP/1.1、HTTP/2、HTTP/3、gRPC 和 WebSocket 的表现取决于代理、网关、服务端、握手复用与连接存活时间。RTT（round-trip time，往返时间）是数据从客户端到对端再返回所需的时间。RTT 较高时，减少往返次数、复用已建立连接通常有价值，但不能据此断言某个协议在卫星网络上固定胜出。

工程决策可以遵守这些边界：

- 保持请求主机集合稳定，复用已有连接，避免每项小操作都建立独立客户端；
- 同步交互改为“本地提交、后台发送、回执更新”，界面不等待一次长往返；
- WebSocket 和 gRPC 流的心跳、重连受服务端策略控制，后台不可用时停止保活；
- HTTP/3 需要在真实运营商路径上验证；它使用的 QUIC 传输协议通常基于 UDP，可能受网关和 UDP 路径可用性影响；
- 大文件使用可恢复上传或 HTTP 范围请求（按字节范围分段下载）时，要同时控制分块数量，避免过小分块增加往返次数；
- HTTPDNS（通过 HTTP 或 HTTPS 获取域名解析结果）查询不进入 `Dns.lookup()` 的同步路径，按 [24.7 HTTPDNS 与 OkHttp Dns 的执行边界](07-httpdns-okhttp-dns-boundary.md)处理。

卫星网络可能只允许部分应用、目标地址和协议。连接库识别出卫星传输，不代表运营商允许访问任意站点。产品界面需要提供“当前服务不可用”的明确状态。

### 运营商产品规则不属于 Android API 契约

平台元数据只表明应用已经按低数据预算适配；运营商仍可按设备、套餐、地区、覆盖和合作范围决定服务可用性。T-Mobile 的 [`T-Satellite` 服务页](https://www.t-mobile.com/coverage/satellite-phone-service) 和 [应用扩展公告](https://www.t-mobile.com/news/network/t-satellite-data-ready-app-expansion)可以用于了解一个商用产品的限制，但不能推断所有 Android 卫星网络都采用相同的受支持应用列表、速度或应用类别。

客户端应根据平台能力控制数据预算，再由服务端功能配置决定自家功能是否开放。不能用一家运营商的公开列表推断其他运营商的状态，也不能把应用清单声明显示成“服务已经开通”。

### 观测数据要区分平台判断和业务结果

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

### 验证覆盖状态变化与故障恢复

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

### 工程检查清单

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

### 低带宽部分的参考与验证

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


## 区分流媒体、本地网络与普通互联网请求

通用低带宽策略确定后，流媒体按播放缓冲和码率控制流量；局域网功能则要在权限未授予时停止发现或提供替代入口。

### 两类 Android 17 新输入

Android 17 同时增加了流媒体数据计划速率接口和本地网络访问权限。两项改动都涉及网络，但输入和授权对象不同：

- `SubscriptionInfo` 的新接口描述运营商为某个订阅提供的流媒体速率上限，用于视频、音频、直播或实时音视频通信（RTC）的质量预算。
- `ACCESS_LOCAL_NETWORK` 控制应用能否发现或连接局域网设备，也控制局域网设备能否连接应用进程中的服务器。
- 登录、信息流（Feed）、配置和图片列表等互联网请求仍按域名解析（DNS）、连接、重试与弱网规则处理。

平台基准为正式发布的 Android 17、API 37 与 Android 开源项目（AOSP）标签 `android-17.0.0_r1`。低带宽与卫星网络见本文前半部分；通用请求预算见 [24.5 移动网络架构、连接生命周期与容灾策略](05-mobile-network-connection-resilience.md)，ECH 与证书透明度见 [24.6 HTTP/2、HTTP/3、gRPC 与 ECH](06-http2-http3-grpc-ech.md)。

### 按网络路径分类

同一页面可能同时包含媒体分片、诊断事件上报和投屏发现。若只按页面统计网络失败，三种问题会混在一起。ABR 是 Adaptive Bitrate 的缩写，指播放器根据带宽和缓冲状态自动切换码率；mDNS 是组播 DNS，SSDP 是简单服务发现协议，两者常用于局域网设备发现。

| 路径 | 典型业务 | Android 17 变化 | 主要失败形态 | 决策入口 |
| --- | --- | --- | --- | --- |
| 蜂窝流媒体 | 点播、直播、音频流、RTC 上行 | 订阅对象提供流媒体上下行速率上限 | 初始质量过高、缓冲增加、上行编码超出预算 | ABR、编码器和清晰度选择 |
| 本地网络 | Google Cast 投屏、物联网（IoT）、mDNS、SSDP、本地 HTTP 服务 | 目标 API 37 后默认阻断，需系统设备选择器或运行时权限 | 发现失败、UDP `EPERM`、TCP 超时、入站连接失败 | 权限与设备选择流程 |
| 普通互联网请求 | 登录、信息流、配置、图片、诊断事件 | 不由上述速率上限或本地网络权限统一控制 | DNS、传输层安全协议（TLS）、连接、服务端或队列失败 | 24.7、24.6、26.10 |

建议在诊断事件中记录 `request_class` 这类取值种类固定且较少的低基数字段，例如 `media_segment`、`lan_discovery` 和 `api`。低基数字段便于聚合，也不会因每个用户或设备都产生新取值而放大存储成本。订阅标识、设备地址和服务实例名不得写入通用诊断事件。

## 流媒体码率预算

### 流媒体速率接口表达什么

Android 17 为 `SubscriptionInfo` 增加：

- `getStreamingAppMaxDownlinkKbps()`：流媒体应用在该订阅上的最大下行速率。
- `getStreamingAppMaxUplinkKbps()`：流媒体应用在该订阅上的最大上行速率。

单位均为 Kbps（kilobits per second，每秒千比特），语义来自移动通信行业组织 GSMA 的 TS.43 服务配置规范。运营商未提供该值或该值不适用时，接口返回 `SubscriptionPlan.BITRATE_UNKNOWN`；在 API 37 的公开签名中，该常量为 `-1L`。运营商上限表达数据计划或运营商策略。播放器测得的端到端吞吐、服务器供给能力、无线传输状态和设备解码能力仍要单独测量。

读取订阅列表还有两个前提：

- `getActiveSubscriptionInfoList()` 要求 `READ_PHONE_STATE`，或者应用拥有运营商特权（carrier privilege），即 SIM 或运营商授予特定应用的电话接口访问资格。普通媒体应用不应为了一个可选优化，在没有明确业务理由时强迫用户授予电话状态权限。
- 返回值只包含调用方可见的活动订阅。Android SDK 35 起文档承诺不再返回 `null`，但仍可能是空列表，也可能因设备不支持订阅功能而抛出 `UnsupportedOperationException`。

#### 匹配承载媒体的订阅，避免对所有 SIM 取最小值

双卡设备的两份 `SubscriptionInfo` 可能对应不同套餐。对所有可见订阅取最小值，会让未承载当前媒体流量的 SIM 限制另一张 SIM。示例有意只读取用户设置的系统默认数据订阅，并把未知、无权限和不支持都表示为 `null`。

```kotlin
data class StreamingPlanLimit(
    val subscriptionId: Int,
    val downlinkKbps: Long?,
    val uplinkKbps: Long?,
)

@RequiresApi(37)
fun readDefaultDataStreamingPlanLimit(
    context: Context,
): StreamingPlanLimit? {
    val supportsSubscriptions = context.packageManager.hasSystemFeature(
        PackageManager.FEATURE_TELEPHONY_SUBSCRIPTION,
    )
    if (!supportsSubscriptions) {
        return null
    }

    val subscriptionId = SubscriptionManager.getDefaultDataSubscriptionId()
    if (!SubscriptionManager.isValidSubscriptionId(subscriptionId)) {
        return null
    }

    val manager = context.getSystemService(SubscriptionManager::class.java)
        ?: return null
    val subscriptions = try {
        manager.activeSubscriptionInfoList.orEmpty()
    } catch (_: SecurityException) {
        return null
    } catch (_: UnsupportedOperationException) {
        return null
    }

    val subscription = subscriptions.firstOrNull {
        it.subscriptionId == subscriptionId
    } ?: return null

    fun known(value: Long): Long? {
        return value.takeIf {
            it != SubscriptionPlan.BITRATE_UNKNOWN && it > 0L
        }
    }

    val downlink = known(subscription.streamingAppMaxDownlinkKbps)
    val uplink = known(subscription.streamingAppMaxUplinkKbps)
    if (downlink == null && uplink == null) {
        return null
    }

    return StreamingPlanLimit(
        subscriptionId = subscriptionId,
        downlinkKbps = downlink,
        uplinkKbps = uplink,
    )
}
```

这段代码没有自行设定默认码率。调用方收到 `null` 后，应继续使用经过验证的初始质量和实时吞吐估计。

默认数据订阅只表示用户配置的默认项，可能不同于当前承载蜂窝互联网流量的活动数据订阅。机会型订阅是系统在条件合适时临时选用的辅助蜂窝订阅；支持这种订阅或自动数据切换的应用，应优先读取 `SubscriptionManager.getActiveDataSubscriptionId()`，并在 `TelephonyCallback.ActiveDataSubscriptionIdListener` 通知后重新计算。注册这个回调同样需要 `READ_PHONE_STATE` 或运营商特权。

Wi-Fi、虚拟专用网络（VPN）、企业专用网络，以及应用主动绑定的其他 `Network` 都不能套用默认订阅值。若应用请求了指定订阅的蜂窝网络，应在请求网络时自行保留订阅 ID；普通应用也不能依赖 `NetworkCapabilities.getSubscriptionIds()` 反查，因为系统只会为持有 `NETWORK_FACTORY` 特权的调用方填充该字段。无法确认媒体流量由哪份订阅承载时，忽略运营商上限比误用另一张 SIM 的值更稳妥。

默认或活动数据订阅变化、飞行模式恢复以及媒体连接从 Wi-Fi 切到蜂窝时，都要重新计算。`subscriptionId` 只在设备本地用于匹配，不能当作稳定用户标识上传。

### 把运营商上限接入 ABR

自适应码率（ABR）至少有三类输入。Media3 是 AndroidX 的媒体播放库，ExoPlayer 是其中的播放器实现；`BandwidthMeter` 是 Media3 根据近期媒体传输样本估算可用带宽的组件。

| 输入 | 含义 | 更新时机 | 适合影响 |
| --- | --- | --- | --- |
| 运营商速率上限 | 该订阅为流媒体分配的最大上下行速率 | 订阅或承载网络变化 | 候选质量上界、初始质量、编码目标 |
| `BandwidthMeter` 估计 | 最近媒体传输样本推导的可用吞吐 | 分片传输持续更新 | 播放中的升降档 |
| 缓冲与播放状态 | 已缓冲时长、卡顿、直播延迟和解码能力 | 播放会话内更新 | 是否允许升档、是否快速降档 |

截至 2026-08-15 的 Media3 API 参考中，`AdaptiveTrackSelection.DEFAULT_BANDWIDTH_FRACTION` 为 `0.7f`，表示轨道选择默认只使用估算带宽的 70%；`DefaultBandwidthMeter.DEFAULT_INITIAL_BITRATE_ESTIMATE` 为 `1_000_000` bps（bits per second，每秒比特），用于离线或无法判断网络类型时的初始估计。两者都是库版本相关的默认参数，性能基线必须记录播放器和 Media3 的精确版本。

运营商上限不能直接写成视频轨道的最大码率。候选轨道是同一内容提供的不同码率或分辨率版本；一轮媒体会话还包含音频、封装格式、媒体清单、加密、请求头、重传和质量探测等流量。处理顺序如下：

1. 将已知的 Kbps 按十进制换算为 bps。
2. 根据音频与协议成本，为视频或上行编码保留经过实验验证的余量。
3. 使用该预算过滤候选轨道或约束编码器目标。
4. 仍由实时吞吐、缓冲状态和解码能力在剩余候选中选择。

运营商上限和 `DefaultBandwidthMeter` 的采样结果应作为两个独立输入。合并成一个数会混淆数据计划允许的速率与当前路径测得的吞吐，网络切换后的估计也会失真。

点播与直播下行可以约束候选视频轨道，RTC 或直播推流则使用上行接口约束编码目标。信令、小型控制请求和鉴权不属于媒体码率本身，不应因为上行速率未知而阻止建连。

若服务端参与清晰度选择，客户端只需上传离散的预算档位或受控区间。服务端仍要保留兼容的媒体清单和切换能力。HLS 和 DASH 是两种常见的分段流媒体协议，它们用媒体清单列出可选轨道；一次上报不能成为永久删除低质量轨道的依据。

## Android 17 本地网络授权

### Android 17 如何界定本地网络

本地网络保护作用于具有广播或组播能力的 Wi-Fi、以太网等接口，不包含蜂窝无线广域网（WWAN）或 VPN 连接。官方范围比 RFC 1918 私有 IPv4 地址更广：

- IPv4 链路本地地址、运营商级网络地址转换（CGNAT）使用的 `100.64.0.0/10` 共享地址，以及 RFC 1918 私有地址。
- IPv6 链路本地地址、直连路由、Thread 等存根网络和多子网。存根网络只连接上级网络，不转发其他网络之间的流量；这里的 Thread 是面向物联网设备的低功耗网状网络协议，不是程序线程。
- IPv4/IPv6 组播地址以及 IPv4 广播地址。组播把数据发给加入同一组的一批接收者，广播则面向同一广播域内的所有设备。

应用不能只检查 `192.168.x.x` 前缀来判断是否需要权限。mDNS、SSDP、`.local` 名称解析、局域网 HTTP、OkHttp 或 Cronet 访问本地地址、WebView 内的本地请求，以及应用监听端口接受局域网连接，都在影响范围内。WebView 沿用宿主应用的权限状态。

系统配置的 DNS 服务器位于本地网络时，发往其 53 端口的域名解析流量属于官方列出的例外。这个例外只保证系统 DNS 可用，不允许应用绕过权限访问其他本地 DNS 服务或端口。

### Android 16 到 Android 17 的迁移

| 环境 | 默认行为 | 测试或发布要求 |
| --- | --- | --- |
| Android 16 | 应用可通过兼容性变更开关提前启用限制；测试期间使用 `NEARBY_WIFI_DEVICES` 恢复访问 | 在目标 API 升级前覆盖发现、连接、监听和撤权 |
| Android 17，`targetSdk < 37` | 持有 `INTERNET` 的旧应用获得临时隐式授权 | 不要声明或请求 `ACCESS_LOCAL_NETWORK`；这只是迁移兼容 |
| Android 17，`targetSdk >= 37` | 本地网络默认阻断 | 使用系统设备选择器，或声明并请求 `ACCESS_LOCAL_NETWORK` |

兼容性变更是系统提供的测试开关，用于在旧目标版本上提前模拟新行为。Android 16 测试需要启用变更并重启设备；这两条命令只用于测试包，不能放进应用运行逻辑。

```shell
adb shell am compat enable RESTRICT_LOCAL_NETWORK com.example.app
adb reboot
```

启用后，应用进程中的本地网络套接字会受到限制。Android 16 文档同时指出，`NsdManager` 等由系统服务代替应用执行网络操作的框架 API，不受这次主动测试完整覆盖。系统设备选择器和权限拒绝路径仍要在 Android 17 / API 37 真机上复测。

### 两条授权路径

#### 路径一：系统设备选择器

只需要连接用户明确选择的一台设备时，优先使用系统代为发现和授权的路径：

- Google Cast 场景可使用 Output Switcher，也就是系统提供的媒体输出设备面板。
- 基于 DNS 的服务发现（DNS-SD）场景可使用 `DiscoveryRequest.FLAG_SHOW_PICKER`；mDNS 常用来在局域网内承载 DNS-SD 查询。
- 用户选中的服务会获得按服务授权，不需要应用取得整个局域网的访问权限。

NSD 是 Network Service Discovery 的缩写，即 Android 的网络服务发现 API。Android 17 的 NSD 设备选择器也通过 T SDK Extension 22 提供；这里的 T 指 Android 13，SDK Extension 是系统模块更新带来的 API 版本，让设备在不升级完整 Android 大版本的情况下也可能获得新接口。运行在可接收模块更新的旧平台时，应检查 T 扩展版本；示例只展示 Android 17 直接路径。

这段代码发起一次系统 NSD 设备选择。页面或控制器要保存回调对象，并在生命周期结束时调用 `unregisterServiceInfoCallback()` 取消注册。

```kotlin
@RequiresApi(37)
fun showNsdServicePicker(
    nsdManager: NsdManager,
    executor: Executor,
    serviceType: String,
    onSelected: (NsdServiceInfo) -> Unit,
    onError: (Int) -> Unit,
): NsdManager.ServiceInfoCallback {
    val request = DiscoveryRequest.Builder(serviceType)
        .setFlags(DiscoveryRequest.FLAG_SHOW_PICKER)
        .build()

    val callback = object : NsdManager.ServiceInfoCallback {
        override fun onServiceUpdated(serviceInfo: NsdServiceInfo) {
            onSelected(serviceInfo)
        }

        override fun onServiceLost() = Unit

        override fun onServiceInfoCallbackRegistrationFailed(errorCode: Int) {
            onError(errorCode)
        }

        override fun onServiceInfoCallbackUnregistered() = Unit
    }

    nsdManager.registerServiceInfoCallback(request, executor, callback)
    return callback
}
```

`FLAG_SHOW_PICKER` 一次最多返回一个用户选择的服务，并在用户选择或取消后停止本次发现。连接时使用回调给出的 `getHostAddresses()`、端口和 `getNetwork()`。DHCP（动态主机配置协议）可能重新分配 IPv4 地址，IPv6 地址和承载网络也可能变化，因此不能只保存上次的 IP。

系统会记住用户批准的服务，授权可跨重启保留，但用户或系统仍可能撤销。再次连接前可用 `checkPermissionForService()` 查询权限，并通过 `registerServiceInfoCallback(NsdServiceInfo, ...)` 获取最新地址。需要在不显示选择界面的情况下查找已批准服务时，使用 `FLAG_USER_APPROVED_ONLY`；它不能与 `FLAG_SHOW_PICKER` 同时设置。

#### 路径二：运行时权限

持续扫描、多设备控制、后台维护连接、本地服务器或自定义发现协议通常需要访问整个局域网。目标 API 37 的应用先在清单中声明：

```xml
<uses-permission android:name="android.permission.ACCESS_LOCAL_NETWORK" />
```

声明不会自动授权。下面的 `ComponentActivity` 片段只在用户启动直接局域网功能时请求权限，并为旧系统保留原有路径。

```kotlin
private val requestLocalNetworkPermission =
    registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            startDirectLanFlow()
        } else {
            showSystemPickerOrOfflineAlternative()
        }
    }

private fun startLanFeature() {
    val granted = Build.VERSION.SDK_INT < 37 ||
        ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_LOCAL_NETWORK,
        ) == PackageManager.PERMISSION_GRANTED

    if (granted) {
        startDirectLanFlow()
    } else {
        requestLocalNetworkPermission.launch(
            Manifest.permission.ACCESS_LOCAL_NETWORK,
        )
    }
}
```

权限属于 `NEARBY_DEVICES`（附近设备）权限组。用户已经允许同组其他权限时，系统可能直接返回已授权，不显示新弹窗。拒绝或在设置中撤销后，要停止扫描、关闭相关套接字，并改用系统设备选择器或说明功能暂不可用。手动输入本地 IP 仍会受到权限限制，不能作为绕过路径；应用也不能在后台反复发起权限请求。

### 失败分类与系统证据

本地网络权限、TLS 和弱网在界面上都可能表现为连接失败，诊断字段必须分开。TLS 负责加密传输；ECH 加密 TLS 初始握手中的服务器名称指示（SNI），减少网络中间设备看到目标域名的机会；应用层协议协商（ALPN）用于在握手时选择 HTTP/2 等上层协议。

| 类别 | Android 17 常见表现 | 记录字段 | 不应推断 |
| --- | --- | --- | --- |
| 本地网络阻断 | UDP 与一般权限拒绝通常返回 `EPERM`，即操作系统的权限不足错误；TCP 通常表现为超时 | target SDK、权限状态、传输协议、目标地址类别、设备选择器路径 | 服务器下线或 TLS 证书错误 |
| TLS / ECH | TLS 握手、证书验证、SNI/ECH 或 ALPN 失败 | 域名分组、TLS 版本、网络库、证书错误类别 | 缺少本地网络权限 |
| 弱网与低带宽 | 首包慢、媒体分片超时、缓冲下降 | 网络会话、吞吐估计、缓冲时长、运营商速率是否已知 | 运营商上限一定生效 |
| NSD 选择器 | `FAILURE_PERMISSION_DENIED`、未选择服务、服务授权被撤销 | API/扩展版本、服务类型分组、授权查询结果 | 用户拒绝广泛权限 |

Android 17 官方迁移文档把 `android_getnetworkblockedreason(sockFd)` 称为 NDK API。C/C++ 网络代码可在 TCP 套接字失败后查询它。只有返回 `ANDROID_NETWORK_BLOCKED_REASON_LNP`，才能把该连接归因到本地网络保护（Local Network Protection，LNP）。

截至 2026-08-15，NDK 公开参考页尚未列出这个符号；网络库需要按构建所用 NDK 和设备版本检查声明与符号是否可用，不能假定旧版本可直接链接。普通 Java/Kotlin TCP 超时没有同等精确的公开错误码，也不能见到超时就上报为权限拒绝。

`android-17.0.0_r1` 的实现提供了两条可核对的证据：

- `PermissionMonitor` 接收 `ACCESS_LOCAL_NETWORK` 权限位，并把结果同步到网络 BPF 权限映射。BPF 是 Linux 内核中可编程的数据包处理机制，这里的映射保存应用在 Linux 中的用户标识（UID）及其联网策略。
- Connectivity 的 C/C++ 接口读取套接字的 `SO_ANDROID_DROP_REASON`，只在阻断原因包含本地网络保护时返回 `ANDROID_NETWORK_BLOCKED_REASON_LNP`。

保护位于操作系统网络栈，更换 OkHttp、Cronet 或 Java Socket 不会改变权限结果。

## 跨路径诊断、验证与发布

### 保持预算、权限与安全边界独立

运营商流媒体上限只是媒体预算来源之一。应用仍要结合 `NetworkCapabilities`、实时吞吐、缓冲、漫游、计费和卫星网络状态。以下字段名取自一份诊断事件示例，不是 Android 强制规定的接口：

- `media_plan_limit_kbps` 只约束当前订阅上的媒体质量。
- `measured_bps` 反映近期路径吞吐，用于短周期升降档。
- `network_profile` 描述蜂窝、Wi-Fi、卫星、VPN、漫游和计费状态。
- `local_access_state` 描述广泛权限、设备选择授权、拒绝和旧应用隐式授权。
- `request_class` 决定媒体、本地发现、控制和普通 API 各自使用哪组规则。

本地网络权限拒绝不能触发所有互联网请求降级，蜂窝数据计划上限也不能限制 Wi-Fi 局域网控制。

Android 17 为目标 API 37 及以上应用把 ECH 默认模式设为 `enabled`。这项配置只对已经集成 ECH 的网络库生效，远端服务器也必须发布可用配置；HttpEngine、WebView 或 OkHttp 等库的具体版本仍需单独确认。协商条件不满足时，支持该机制的客户端会发送内容随机的 ECH GREASE 扩展，避免中间设备只接受未携带 ECH 的固定握手格式。

`<domainEncryption>` 控制全局或指定域名的 ECH 模式，它不授予局域网访问，也不改变 `ACCESS_LOCAL_NETWORK` 的判定。详细安全边界见 [24.6 HTTP/2、HTTP/3、gRPC 与 ECH](06-http2-http3-grpc-ech.md)。

### 验证与分阶段发布

#### 流媒体速率实验

对照组和候选组使用相同播放器、Media3 版本、媒体清单、内容分发网络（CDN）和服务端配置，只改变运营商速率上限如何进入质量选择。至少并列报告：

- 速率上限已知、未知、无读取权限和不支持订阅功能的样本数。
- 当前网络、默认数据订阅是否匹配，以及网络切换前后的重新计算结果。
- 启播成功率、首缓冲分布、首个媒体分片质量、升降档次数、重缓冲次数与时长。
- 下行媒体字节、重复下载字节、直播延迟或 RTC 上行质量。
- 按运营商分组的结果，但不保存原始订阅标识。

只统计成功播放会漏掉候选策略导致的早期失败。评估质量变化时，还要同时检查流量、功耗、解码丢帧和设备温度。

#### 本地网络迁移实验

`targetSdkVersion` 是构建时写入应用清单的目标系统版本，不能在同一个安装包里按用户随机切换。可按以下顺序验证：

1. 在 Android 16 实验室设备上启用兼容性变更，盘点直接套接字与框架 API。
2. 使用目标 API 37 的预发布构建，在 Android 17 真机验证系统设备选择器、广泛权限和拒绝路径。
3. 通过应用商店测试轨道或逐步增加发布比例，对比新旧应用版本，并分别记录 target SDK 和版本号。
4. 发布前为投屏、设备发现、设备连接、本地服务器和权限入口分别设定停止放量的指标阈值。

权限授权率的分母应是用户主动触发且业务确需广泛访问的次数。已有 `NEARBY_DEVICES` 授权的用户可能看不到弹窗，设备选择器路径也不会请求广泛权限；这些会话应单独统计，不能并入权限弹窗转化率。

本地网络功能至少覆盖：

- 出站 TCP，入站 TCP，本地 UDP 单播、组播和广播。
- mDNS、SSDP、`.local` 名称、本地 HTTP/HTTPS、WebView 内本地请求。
- 系统设备选择器选择、取消、跨重启重连、服务地址变化和授权撤销。
- 广泛权限首次允许、拒绝、设置中撤销和再次进入功能。
- Wi-Fi、以太网、IPv4、IPv6、多子网，以及 VPN 和蜂窝不应被误判的路径。

#### 区分回调延迟与网络传输延迟

套接字或播放器已经收到数据后，主线程排队仍可能延迟界面更新。Android 17 为目标 API 37 及以上应用启用新的无锁 `MessageQueue` 实现，源码中称为 DeliQueue；它改变的是消息入队和投递，不是网络传输。应分别记录网络完成、播放器消费和界面提交事件，再按 1.8 的回调投递方法排查。

### `android-17.0.0_r1` 源码锚点

| 职责 | 源码 | 复核重点 |
| --- | --- | --- |
| 公开 API 集合 | [`37.0/public/api/android.txt`](https://android.googlesource.com/platform/prebuilts/sdk/+/refs/tags/android-17.0.0_r1/37.0/public/api/android.txt) | 两个流媒体速率接口、`BITRATE_UNKNOWN`、权限和 NSD 设备选择器签名 |
| 订阅速率字段 | [`SubscriptionInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/SubscriptionInfo.java) | 上下行值的单位、未知值和对象字段 |
| 活动订阅读取 | [`SubscriptionManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/SubscriptionManager.java) | 权限、可见订阅、默认数据订阅 |
| 权限声明 | [`AndroidManifest.xml`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/AndroidManifest.xml) | `ACCESS_LOCAL_NETWORK` 的危险权限声明 |
| NSD 请求 | [`DiscoveryRequest.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework-t/src/android/net/nsd/DiscoveryRequest.java) | `FLAG_SHOW_PICKER` 与 `FLAG_USER_APPROVED_ONLY` 的约束 |
| NSD 生命周期 | [`NsdManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework-t/src/android/net/nsd/NsdManager.java) | 服务选择、权限查询、回调注册与取消 |
| 权限传播 | [`PermissionMonitor.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/connectivity/PermissionMonitor.java) | 权限位如何进入网络 BPF 策略映射 |
| 阻断原因 | [`connectivity_native.cpp`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/libconnectivity/src/connectivity_native.cpp) | `SO_ANDROID_DROP_REASON` 与 LNP 原因映射 |

源码锚点用于确认 Android 17 首发版本的实现边界。应用代码仍应调用公开 SDK，并记录设备系统构建、SDK Extension、播放器与网络库版本；不能依赖隐藏接口或具体 BPF 映射布局。

### 发布前检查清单

- 流媒体速率上限只用于实际承载媒体流量的订阅和网络。
- 未知、无权限、无订阅功能都有经过验证的默认质量策略。
- 双卡设备优先匹配活动数据订阅或业务指定订阅，没有对所有 SIM 取最小值。
- 运营商上限没有覆写实时吞吐估计，也没有直接等同于视频轨道码率。
- 下行、上行、普通 API 与局域网请求使用各自的预算和错误分类。
- 目标 API 37 前已完成 Android 16 兼容性测试和 Android 17 真机测试。
- 只连接用户选择设备的业务优先使用 Output Switcher 或 NSD 设备选择器。
- 广泛权限只在明确的用户动作后请求，拒绝和撤销会停止相关网络操作。
- 系统选择的 NSD 服务在每次连接前刷新地址与 `Network`。
- TCP 超时不直接标记为 LNP；NDK/C++ 诊断使用明确的阻断原因。
- ECH、TLS、本地网络权限和弱网指标没有混用。
- 每次分阶段发布同时观察功能成功率、媒体体验、字节、功耗和权限路径。

## 全文小结

低带宽与卫星网络要求应用先建立统一数据预算，再让请求分级、持久队列、超时重试、推送和媒体载荷共同遵守它。卫星传输、带宽约束、计费与公网验证是不同信号；平台能力只能决定采用哪套策略，不能替代真实业务吞吐和成功率。

流媒体速率上限、本地网络授权与普通互联网请求又是三条独立决策路径。运营商上限约束媒体质量但不替代实时 ABR，本地网络功能按设备选择器或运行时权限授权，TLS/ECH、弱网和权限错误分别归因。最终发布应同时验证网络切换、权限撤销、离线恢复、媒体体验、流量和功耗。


## 参考资料

- [Android 17 正式发布](https://developer.android.com/blog/posts/android-17-is-here)
- [Android 17 目标版本行为变更](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 本地网络权限](https://developer.android.com/privacy-and-security/local-network-permission)
- [Android 本地网络定义](https://developer.android.com/privacy-and-security/local-network-definition)
- [`SubscriptionInfo` API](https://developer.android.com/reference/android/telephony/SubscriptionInfo)
- [`SubscriptionManager.getActiveSubscriptionInfoList()`](https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveSubscriptionInfoList)
- [`SubscriptionManager.getActiveDataSubscriptionId()`](https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveDataSubscriptionId())
- [`NetworkCapabilities.getSubscriptionIds()`](https://developer.android.com/reference/android/net/NetworkCapabilities#getSubscriptionIds())
- [`SubscriptionPlan.BITRATE_UNKNOWN`](https://developer.android.com/reference/android/telephony/SubscriptionPlan#BITRATE_UNKNOWN)
- [`NsdManager` API 与本地服务授权](https://developer.android.com/reference/android/net/nsd/NsdManager)
- [`DiscoveryRequest` API](https://developer.android.com/reference/android/net/nsd/DiscoveryRequest)
- [Android 本地网络权限错误说明](https://developer.android.com/privacy-and-security/local-network-permission#errors)
- [Media3 `AdaptiveTrackSelection`](https://developer.android.com/reference/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection)
- [Media3 `DefaultBandwidthMeter`](https://developer.android.com/reference/androidx/media3/exoplayer/upstream/DefaultBandwidthMeter)
- [Android 网络安全配置与 ECH](https://developer.android.com/privacy-and-security/security-config)
