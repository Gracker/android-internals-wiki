---
title: "Android 17 流媒体网络预算与本地网络权限适配"
chapter: "24.14"
section: "24.14"
status: finalized
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
last_verified: "2026-05-24"
last_verified_against: "Android Developers API reference / Android 17 behavior changes / Local Network Permission docs 2026-05；AOSP android-17 tag 待复核"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionInfo#getStreamingAppMaxDownlinkKbps()"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionInfo#getStreamingAppMaxUplinkKbps()"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveSubscriptionInfoList()"
  - type: official
    path: "https://developer.android.com/privacy-and-security/local-network-permission"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/reference/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection"
  - type: official
    path: "https://developer.android.com/reference/androidx/media3/exoplayer/upstream/DefaultBandwidthMeter"
  - type: research-feed
    path: "intake/research-feeds/2026-04-08-11-android17-network-data-plan-streaming-access-local-network-tls.md"
  - type: daily-info
    path: "intake/daily-info/2026-05-24.md"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]"
tags: [network, android17, streaming, local-network, connectivity]
related_chapters: ["12.1", "12.2", "16.5", "24.4", "24.9", "24.10", "26.14"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
---

# Android 17 流媒体网络预算与本地网络权限适配

## 范围

Android 17 同时增加了流媒体数据计划速率接口和本地网络访问权限。它们都属于网络功能，却没有共同的控制对象：

- `SubscriptionInfo` 的新接口描述运营商为某个订阅提供的流媒体速率上限，用于视频、音频、直播或 RTC 的质量预算。
- `ACCESS_LOCAL_NETWORK` 控制应用能否发现或连接局域网设备，也控制局域网设备能否连接应用进程中的服务器。
- 登录、Feed、配置和图片列表等互联网请求仍按 DNS、连接、重试与弱网规则处理。

平台基准为 Android 17 / API 37 / `android-17.0.0_r1`。24.10 说明低带宽与卫星网络，24.4 说明请求预算，24.15 说明 ECH 与证书透明度；这里集中处理流媒体速率信号和局域网授权。

## 先给网络路径分类

同一页面可能同时包含媒体分片、埋点和投屏发现。若只按页面统计“网络失败”，三种问题会混在一起。

| 路径 | 典型业务 | Android 17 变化 | 主要失败形态 | 决策入口 |
| --- | --- | --- | --- | --- |
| 蜂窝流媒体 | 点播、直播、音频流、RTC 上行 | 订阅对象提供流媒体上下行速率上限 | 初始质量过高、缓冲增加、上行编码超出预算 | ABR、编码器和清晰度编排 |
| 本地网络 | Cast、IoT、mDNS、SSDP、本地 HTTP 服务 | 目标 API 37 后默认阻断，需系统设备选择器或运行时权限 | 发现失败、UDP `EPERM`、TCP 超时、入站连接失败 | 权限与设备选择流程 |
| 普通互联网请求 | 登录、Feed、配置、图片、遥测 | 不由上述速率上限或本地网络权限统一控制 | DNS、TLS、连接、服务端或队列失败 | 24.9、24.4、26.14 |

建议在诊断事件中记录低基数的 `request_class`，例如 `media_segment`、`lan_discovery` 和 `api`。不要把订阅标识、设备地址或服务实例名写入通用遥测。

## 流媒体速率接口表达什么

Android 17 为 `SubscriptionInfo` 增加：

- `getStreamingAppMaxDownlinkKbps()`：流媒体应用在该订阅上的最大下行速率。
- `getStreamingAppMaxUplinkKbps()`：流媒体应用在该订阅上的最大上行速率。

单位均为 Kbps，语义来自 GSMA TS.43。运营商未提供该值或该值不适用时，接口返回 `SubscriptionPlan.BITRATE_UNKNOWN`；在 API 37 的公开签名中，该常量为 `-1L`。它是数据计划或运营商策略信号，不是播放器刚测得的端到端吞吐，也不保证服务器、无线链路和设备解码能达到该速率。

读取订阅列表还有两个前提：

- `getActiveSubscriptionInfoList()` 要求 `READ_PHONE_STATE` 或运营商权限。普通媒体应用不应为了一个可选优化，在没有产品理由时强迫用户授予电话状态权限。
- 返回值只包含调用方可见的活动订阅。Android SDK 35 起文档承诺不再返回 `null`，但仍可能是空列表，也可能因设备不支持订阅功能而抛出 `UnsupportedOperationException`。

### 读取当前数据订阅，而非所有 SIM 的最小值

双卡设备的两份 `SubscriptionInfo` 可能对应不同套餐。对所有可见订阅取最小值，会让一张未承载当前媒体流量的 SIM 限制另一张 SIM。下面的代码只读取系统默认数据订阅，并把未知、无权限和不支持都表示为 `null`。

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

这段代码没有提供任意默认码率。调用方收到 `null` 后应继续使用已经验证过的冷启动档位和实时估计。它也只适用于媒体流量走默认蜂窝数据订阅的场景；Wi-Fi、VPN、应用绑定的其他 `Network` 或企业专用网络需要按媒体连接的实际路径判断，不能机械套用默认数据订阅的值。

默认数据订阅变化、活动订阅变化、飞行模式恢复以及媒体连接从 Wi-Fi 切到蜂窝时，都要重新计算。不要把 `subscriptionId` 当作稳定用户标识上传。

## 把运营商上限接入 ABR

自适应码率至少有三类输入：

| 输入 | 含义 | 更新时机 | 适合影响 |
| --- | --- | --- | --- |
| 运营商速率上限 | 该订阅为流媒体分配的最大上下行速率 | 订阅或承载网络变化 | 候选质量上界、初始质量、编码目标 |
| `BandwidthMeter` 估计 | 最近媒体传输样本推导的可用吞吐 | 分片传输持续更新 | 播放中的升降档 |
| 缓冲与播放状态 | 已缓冲时长、卡顿、直播延迟和解码能力 | 播放会话内更新 | 是否允许升档、是否快速降档 |

复核所用的 Media3 版本中，`AdaptiveTrackSelection.DEFAULT_BANDWIDTH_FRACTION` 为 `0.7f`，`DefaultBandwidthMeter.DEFAULT_INITIAL_BITRATE_ESTIMATE` 为 `1_000_000` bps。它们属于具体版本的默认参数，基线必须记录播放器和 Media3 的精确版本，不能把默认值当作所有版本的固定规则。

运营商上限也不能直接写成视频轨道的最大码率。一次媒体会话还包含音频、容器、清单、加密、请求头、重传和质量探测等成本。合理的顺序是：

1. 将已知的 Kbps 按十进制换算为 bps。
2. 根据音频与协议成本，为视频或上行编码保留经过实验验证的余量。
3. 使用该预算过滤候选轨道或约束编码器目标。
4. 仍由实时吞吐、缓冲状态和解码能力在剩余候选中选择。

不要用运营商上限覆写 `DefaultBandwidthMeter` 的采样结果。这样会把“数据计划允许多少”和“当前路径传得多快”混成一个数，网络切换后的估计也会失真。

点播与直播下行可以约束候选视频轨道，RTC 或直播推流则使用上行接口约束编码目标。信令、小型控制请求和鉴权不属于媒体码率本身，不应因为上行速率未知而阻止建连。

若服务端参与清晰度编排，客户端只需上传离散的预算档位或受控区间。服务端仍要保留兼容清单与切换能力，不能根据一次上报永久删除更低质量的轨道。

## Android 17 如何界定本地网络

本地网络保护作用于使用广播能力接口的 Wi-Fi、以太网等网络，不包含蜂窝 WWAN 或 VPN。官方定义覆盖的范围比 RFC 1918 更广，包括：

- IPv4 链路本地地址、`100.64.0.0/10`、RFC 1918 地址。
- IPv6 链路本地、直连路由、Thread 等存根网络和多子网。
- IPv4/IPv6 组播地址以及 IPv4 广播地址。

因此，应用不能靠 `192.168.x.x` 这一种前缀判断是否需要权限。mDNS、SSDP、`.local` 解析、局域网 HTTP、OkHttp/Cronet 访问本地地址、WebView 内的本地请求，以及应用监听端口接受局域网连接，都在影响范围内。WebView 使用宿主应用的权限状态。

系统 DNS 服务器位于本地网络时，发往其 53 端口的 DNS 流量属于文档列出的例外。该例外不等于应用可以绕过权限访问任意本地 DNS 服务或其他端口。

## Android 16 到 Android 17 的迁移

| 环境 | 默认行为 | 测试或发布要求 |
| --- | --- | --- |
| Android 16 | 本地网络限制由应用通过兼容性变更主动启用；测试期间使用 `NEARBY_WIFI_DEVICES` 恢复访问 | 在目标 API 升级前覆盖发现、连接、监听和撤权 |
| Android 17，`targetSdk < 37` | 持有 `INTERNET` 的旧应用获得临时隐式授权 | 不要声明或请求 `ACCESS_LOCAL_NETWORK`；这只是迁移兼容 |
| Android 17，`targetSdk >= 37` | 本地网络默认阻断 | 使用系统设备选择器，或声明并请求 `ACCESS_LOCAL_NETWORK` |

Android 16 的兼容性测试需要启用变更并重启设备。下面命令用于测试包，不应出现在应用运行逻辑中。

```shell
adb shell am compat enable RESTRICT_LOCAL_NETWORK com.example.app
adb reboot
```

启用后，应用进程中的本地网络套接字会受到限制。Android 16 文档同时指出，像 `NsdManager` 这样在应用进程外执行本地网络操作的框架 API 不受这次主动测试完整覆盖，因此仍要在 Android 17 / API 37 真机上复测系统设备选择器和权限拒绝路径。

## 两条授权路径

### 路径一：系统设备选择器

只需要连接用户明确选择的一台设备时，优先使用系统介导路径：

- Cast 场景可使用 Output Switcher，让系统完成设备选择。
- mDNS/DNS-SD 场景可使用 `DiscoveryRequest.FLAG_SHOW_PICKER`。
- 用户选中的服务会获得按服务授权，不需要应用取得整个局域网的访问权限。

Android 17 的 NSD 设备选择器 API 同时发布在 T SDK Extension 22。运行在可接收 SDK Extension 更新的旧平台时，应检查 T 扩展版本；以下示例只展示 Android 17 直接路径。

下面的代码显示一次系统 NSD 设备选择。回调对象需要由页面或控制器保存，以便在生命周期结束时取消注册。

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

`FLAG_SHOW_PICKER` 一次最多返回一个用户选择的服务，并在用户选择或取消后停止本次发现。连接时使用回调给出的 `getHostAddresses()`、端口和 `getNetwork()`；不要只保存 IP，因为 DHCP、IPv6 地址和承载网络都可能变化。

系统会记住用户批准的服务，授权可跨重启保留，但用户或系统仍可能撤销。再次连接前可用 `checkPermissionForService()` 查询权限，并通过 `registerServiceInfoCallback(NsdServiceInfo, ...)` 获取最新地址。需要无界面查找曾批准服务时使用 `FLAG_USER_APPROVED_ONLY`；它不能与 `FLAG_SHOW_PICKER` 同时设置。

### 路径二：运行时权限

持续扫描、多设备控制、后台维护连接、本地服务器或自定义发现协议通常需要广泛访问。目标 API 37 的应用先在清单中声明：

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

权限属于 `NEARBY_DEVICES` 权限组。用户已经允许同组其他权限时，系统可能直接返回已授权，不显示新弹窗。拒绝或在设置中撤销后，要停止扫描、关闭相关套接字，并提供系统设备选择器、手动操作或离线说明；不要在后台反复发起权限请求。

## 失败分类与系统证据

本地网络权限、TLS 和弱网的外观可能都是“连接失败”，诊断字段必须分开。

| 类别 | Android 17 常见表现 | 记录字段 | 不应推断 |
| --- | --- | --- | --- |
| 本地网络阻断 | UDP 与一般权限拒绝通常返回 `EPERM`；TCP 通常表现为超时 | target SDK、权限状态、传输协议、目标地址类别、设备选择器路径 | 服务器下线或 TLS 证书错误 |
| TLS / ECH | TLS 握手、证书验证、SNI/ECH 或 ALPN 失败 | 域名分组、TLS 版本、网络库、证书错误类别 | 缺少本地网络权限 |
| 弱网与低带宽 | 首包慢、媒体分片超时、缓冲下降 | 网络会话、吞吐估计、缓冲时长、运营商速率是否已知 | 运营商上限一定生效 |
| NSD 选择器 | `FAILURE_PERMISSION_DENIED`、未选择服务、服务授权被撤销 | API/扩展版本、服务类型分组、授权查询结果 | 用户拒绝广泛权限 |

Native 网络代码可以在 TCP 套接字上调用 `android_getnetworkblockedreason(sockFd)`；返回 `ANDROID_NETWORK_BLOCKED_REASON_LNP` 时，才能把该连接归因到本地网络保护。普通 Java/Kotlin TCP 超时没有同等精确的公开错误码，不能见到超时就上报为权限拒绝。

`android-17.0.0_r1` 的实现提供了两条可核对的证据：

- `PermissionMonitor` 接收 `ACCESS_LOCAL_NETWORK` 权限位，并把结果同步到网络 BPF 权限映射。
- native Connectivity 接口读取套接字的 `SO_ANDROID_DROP_REASON`，只在包含本地网络保护原因时返回 `ANDROID_NETWORK_BLOCKED_REASON_LNP`。

这也解释了为何更换 OkHttp、Cronet 或 Java Socket 不能绕开限制：保护位于网络栈下层，而不是某个 HTTP 客户端的权限检查。

## 与低带宽、卫星和 ECH 的关系

运营商流媒体上限只是媒体预算来源之一。应用仍要结合 `NetworkCapabilities`、实时吞吐、缓冲、漫游、计费和卫星网络状态：

- `media_plan_limit_kbps` 只约束当前订阅上的媒体质量。
- `measured_bps` 反映近期路径吞吐，用于短周期升降档。
- `network_profile` 描述蜂窝、Wi-Fi、卫星、VPN、漫游和计费状态。
- `local_access_state` 描述广泛权限、设备选择授权、拒绝和旧应用隐式授权。
- `request_class` 决定媒体、本地发现、控制和普通 API 各自使用哪组规则。

本地网络权限拒绝不能触发所有互联网请求降级，蜂窝数据计划上限也不能限制 Wi-Fi 局域网控制。

Android 17 对目标 API 37 的应用还默认启用 ECH 配置。只有网络库和服务端都支持时才会协商 ECH；没有配置时可能发送 ECH GREASE。`<domainEncryption>` 控制域名级 ECH 模式，它不授予局域网访问，也不改变 `ACCESS_LOCAL_NETWORK` 的判定。详细安全边界见 24.15。

## 验证与灰度

### 流媒体速率实验

对照组和候选组使用相同播放器、Media3 版本、媒体清单、CDN 和服务端配置，只改变运营商速率上限如何进入质量选择。至少并列报告：

- 速率上限已知、未知、无读取权限和不支持订阅功能的样本数。
- 当前网络、默认数据订阅是否匹配，以及网络切换前后的重新计算结果。
- 启播成功率、首缓冲分布、首个媒体分片质量、升降档次数、重缓冲次数与时长。
- 下行媒体字节、重复下载字节、直播延迟或 RTC 上行质量。
- 按运营商分组的结果，但不保存原始订阅标识。

只统计成功播放会隐藏因候选策略导致的早期失败。质量提升也要同时检查流量、功耗、解码丢帧和设备温度。

### 本地网络迁移实验

`targetSdkVersion` 写在应用清单中，不能在同一个安装包里按用户随机切换。可使用以下顺序降低迁移风险：

1. 在 Android 16 实验室设备上启用兼容性变更，盘点直接套接字与框架 API。
2. 使用目标 API 37 的预发布构建，在 Android 17 真机验证系统设备选择器、广泛权限和拒绝路径。
3. 通过测试轨道或分阶段发布比较新旧应用版本，分开记录 target SDK 和版本号。
4. 发布期间为投屏、设备发现、设备连接、本地服务器和权限入口分别设置停止条件。

权限授权率的分母应是用户主动触发且业务确需广泛访问的次数。已有 `NEARBY_DEVICES` 授权的用户可能没有弹窗，设备选择器路径也不会请求广泛权限，把这些会话放进同一个弹窗转化率会产生错误结论。

本地网络功能至少覆盖：

- 出站 TCP，入站 TCP，本地 UDP 单播、组播和广播。
- mDNS、SSDP、`.local` 名称、本地 HTTP/HTTPS、WebView 内本地请求。
- 系统设备选择器选择、取消、跨重启重连、服务地址变化和授权撤销。
- 广泛权限首次允许、拒绝、设置中撤销和再次进入功能。
- Wi-Fi、以太网、IPv4、IPv6、多子网，以及 VPN 和蜂窝不应被误判的路径。

### 把回调延迟和链路延迟分开

套接字或播放器已经收到数据后，主线程排队仍可能延迟界面更新。Android 17 的 MessageQueue/DeliQueue 变化属于 16.5 的回调投递回归，不能算进 DNS、连接或媒体吞吐。应分别记录网络完成、播放器消费和界面提交事件。

## `android-17.0.0_r1` 源码锚点

| 职责 | 源码 | 复核重点 |
| --- | --- | --- |
| 公开 API 集合 | [`37.0/public/api/android.txt`](https://android.googlesource.com/platform/prebuilts/sdk/+/refs/tags/android-17.0.0_r1/37.0/public/api/android.txt) | 两个流媒体速率接口、`BITRATE_UNKNOWN`、权限和 NSD 设备选择器签名 |
| 订阅速率字段 | [`SubscriptionInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/SubscriptionInfo.java) | 上下行值的单位、未知值和对象字段 |
| 活动订阅读取 | [`SubscriptionManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/telephony/java/android/telephony/SubscriptionManager.java) | 权限、可见订阅、默认数据订阅 |
| 权限声明 | [`AndroidManifest.xml`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/AndroidManifest.xml) | `ACCESS_LOCAL_NETWORK` 的危险权限声明 |
| NSD 请求 | [`DiscoveryRequest.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework-t/src/android/net/nsd/DiscoveryRequest.java) | `FLAG_SHOW_PICKER` 与 `FLAG_USER_APPROVED_ONLY` 的约束 |
| NSD 生命周期 | [`NsdManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework-t/src/android/net/nsd/NsdManager.java) | 服务选择、权限查询、回调注册与取消 |
| 权限传播 | [`PermissionMonitor.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/connectivity/PermissionMonitor.java) | 权限位如何进入网络 BPF 映射 |
| 阻断原因 | [`connectivity_native.cpp`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/libconnectivity/src/connectivity_native.cpp) | `SO_ANDROID_DROP_REASON` 与 LNP 原因映射 |

源码锚点用于确认 Android 17 首发版本的实现边界。应用代码仍应调用公开 SDK，并记录设备系统构建、SDK Extension、播放器与网络库版本；不能依赖隐藏接口或具体 BPF 映射布局。

## 发布前检查清单

- 流媒体速率上限只用于实际承载媒体流量的订阅和网络。
- 未知、无权限、无订阅功能都有经过验证的默认质量策略。
- 双卡读取系统默认数据订阅，没有对所有 SIM 取最小值。
- 运营商上限没有覆写实时吞吐估计，也没有直接等同于视频轨道码率。
- 下行、上行、普通 API 与局域网请求使用各自的预算和错误分类。
- 目标 API 37 前已完成 Android 16 兼容性测试和 Android 17 真机测试。
- 只连接用户选择设备的业务优先使用 Output Switcher 或 NSD 设备选择器。
- 广泛权限只在明确的用户动作后请求，拒绝和撤销会停止相关网络操作。
- 系统选择的 NSD 服务在每次连接前刷新地址与 `Network`。
- TCP 超时不直接标记为 LNP；Native 诊断使用明确的阻断原因。
- ECH、TLS、本地网络权限和弱网指标没有混用。
- 每次灰度同时观察功能成功率、媒体体验、字节、功耗和权限路径。

## 参考资料

- [Android 17 目标版本行为变更](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 本地网络权限](https://developer.android.com/privacy-and-security/local-network-permission)
- [Android 本地网络定义](https://developer.android.com/privacy-and-security/local-network-definition)
- [`SubscriptionInfo` API](https://developer.android.com/reference/android/telephony/SubscriptionInfo)
- [`SubscriptionManager.getActiveSubscriptionInfoList()`](https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveSubscriptionInfoList)
- [`SubscriptionPlan.BITRATE_UNKNOWN`](https://developer.android.com/reference/android/telephony/SubscriptionPlan#BITRATE_UNKNOWN)
- [`NsdManager` API 与本地服务授权](https://developer.android.com/reference/android/net/nsd/NsdManager)
- [`DiscoveryRequest` API](https://developer.android.com/reference/android/net/nsd/DiscoveryRequest)
- [Media3 `AdaptiveTrackSelection`](https://developer.android.com/reference/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection)
- [Media3 `DefaultBandwidthMeter`](https://developer.android.com/reference/androidx/media3/exoplayer/upstream/DefaultBandwidthMeter)
- [Android 网络安全配置与 ECH](https://developer.android.com/privacy-and-security/security-config)
