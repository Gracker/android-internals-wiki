---
title: "Android 17 流媒体网络预算与本地网络权限适配"
chapter: "24.14"
section: "24.14"
status: finalized
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
last_verified: "2026-08-15"
last_verified_against: "Android 17 stable behavior changes / API 37 reference / Local Network Permission docs 2026-08 / AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionInfo#getStreamingAppMaxDownlinkKbps()"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionInfo#getStreamingAppMaxUplinkKbps()"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveSubscriptionInfoList()"
  - type: official
    path: "https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveDataSubscriptionId()"
  - type: official
    path: "https://developer.android.com/reference/android/net/NetworkCapabilities#getSubscriptionIds()"
  - type: official
    path: "https://developer.android.com/privacy-and-security/local-network-permission"
  - type: official
    path: "https://developer.android.com/privacy-and-security/local-network-definition"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/blog/posts/android-17-is-here"
  - type: official
    path: "https://developer.android.com/reference/android/net/nsd/NsdManager"
  - type: official
    path: "https://developer.android.com/privacy-and-security/local-network-permission#errors"
  - type: official
    path: "https://developer.android.com/reference/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection"
  - type: official
    path: "https://developer.android.com/reference/androidx/media3/exoplayer/upstream/DefaultBandwidthMeter"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
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
pipeline_stage: finalized
task6_state: reviewed
task9_state: reviewed
---

# Android 17 流媒体网络预算与本地网络权限适配

## 范围

Android 17 同时增加了流媒体数据计划速率接口和本地网络访问权限。两项改动都涉及网络，但输入和授权对象不同：

- `SubscriptionInfo` 的新接口描述运营商为某个订阅提供的流媒体速率上限，用于视频、音频、直播或实时音视频通信（RTC）的质量预算。
- `ACCESS_LOCAL_NETWORK` 控制应用能否发现或连接局域网设备，也控制局域网设备能否连接应用进程中的服务器。
- 登录、信息流（Feed）、配置和图片列表等互联网请求仍按域名解析（DNS）、连接、重试与弱网规则处理。

平台基准为正式发布的 Android 17、API 37 与 Android 开源项目（AOSP）标签 `android-17.0.0_r1`。低带宽与卫星网络见 24.10，请求预算见 24.4，ECH 与证书透明度见 24.15。

## 按网络路径分类

同一页面可能同时包含媒体分片、诊断事件上报和投屏发现。若只按页面统计网络失败，三种问题会混在一起。ABR 是 Adaptive Bitrate 的缩写，指播放器根据带宽和缓冲状态自动切换码率；mDNS 是组播 DNS，SSDP 是简单服务发现协议，两者常用于局域网设备发现。

| 路径 | 典型业务 | Android 17 变化 | 主要失败形态 | 决策入口 |
| --- | --- | --- | --- | --- |
| 蜂窝流媒体 | 点播、直播、音频流、RTC 上行 | 订阅对象提供流媒体上下行速率上限 | 初始质量过高、缓冲增加、上行编码超出预算 | ABR、编码器和清晰度选择 |
| 本地网络 | Google Cast 投屏、物联网（IoT）、mDNS、SSDP、本地 HTTP 服务 | 目标 API 37 后默认阻断，需系统设备选择器或运行时权限 | 发现失败、UDP `EPERM`、TCP 超时、入站连接失败 | 权限与设备选择流程 |
| 普通互联网请求 | 登录、信息流、配置、图片、诊断事件 | 不由上述速率上限或本地网络权限统一控制 | DNS、传输层安全协议（TLS）、连接、服务端或队列失败 | 24.9、24.4、26.14 |

建议在诊断事件中记录取值种类固定且较少的低基数字段 `request_class`，例如 `media_segment`、`lan_discovery` 和 `api`。低基数字段便于聚合，也不会因每个用户或设备都产生新取值而放大存储成本。订阅标识、设备地址和服务实例名不得写入通用诊断事件。

## 流媒体速率接口表达什么

Android 17 为 `SubscriptionInfo` 增加：

- `getStreamingAppMaxDownlinkKbps()`：流媒体应用在该订阅上的最大下行速率。
- `getStreamingAppMaxUplinkKbps()`：流媒体应用在该订阅上的最大上行速率。

单位均为 Kbps（kilobits per second，每秒千比特），语义来自移动通信行业组织 GSMA 的 TS.43 服务配置规范。运营商未提供该值或该值不适用时，接口返回 `SubscriptionPlan.BITRATE_UNKNOWN`；在 API 37 的公开签名中，该常量为 `-1L`。这个值表达数据计划或运营商策略。播放器测得的端到端吞吐、服务器供给能力、无线传输状态和设备解码能力仍要单独测量。

读取订阅列表还有两个前提：

- `getActiveSubscriptionInfoList()` 要求 `READ_PHONE_STATE`，或者应用拥有运营商特权（carrier privilege），即 SIM 或运营商授予特定应用的电话接口访问资格。普通媒体应用不应为了一个可选优化，在没有明确业务理由时强迫用户授予电话状态权限。
- 返回值只包含调用方可见的活动订阅。Android SDK 35 起文档承诺不再返回 `null`，但仍可能是空列表，也可能因设备不支持订阅功能而抛出 `UnsupportedOperationException`。

### 匹配承载媒体的订阅，避免对所有 SIM 取最小值

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

## 把运营商上限接入 ABR

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

## Android 17 如何界定本地网络

本地网络保护作用于具有广播或组播能力的 Wi-Fi、以太网等接口，不包含蜂窝无线广域网（WWAN）或 VPN 连接。官方范围比 RFC 1918 私有 IPv4 地址更广：

- IPv4 链路本地地址、运营商级网络地址转换（CGNAT）使用的 `100.64.0.0/10` 共享地址，以及 RFC 1918 私有地址。
- IPv6 链路本地地址、直连路由、Thread 等存根网络和多子网。存根网络只连接上级网络，不转发其他网络之间的流量；这里的 Thread 是面向物联网设备的低功耗网状网络协议，不是程序线程。
- IPv4/IPv6 组播地址以及 IPv4 广播地址。组播把数据发给加入同一组的一批接收者，广播则面向同一广播域内的所有设备。

应用不能只检查 `192.168.x.x` 前缀来判断是否需要权限。mDNS、SSDP、`.local` 名称解析、局域网 HTTP、OkHttp 或 Cronet 访问本地地址、WebView 内的本地请求，以及应用监听端口接受局域网连接，都在影响范围内。WebView 沿用宿主应用的权限状态。

系统配置的 DNS 服务器位于本地网络时，发往其 53 端口的域名解析流量属于官方列出的例外。这个例外只保证系统 DNS 可用，不允许应用绕过权限访问其他本地 DNS 服务或端口。

## Android 16 到 Android 17 的迁移

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

## 两条授权路径

### 路径一：系统设备选择器

只需要连接用户明确选择的一台设备时，优先使用系统代为发现和授权的路径：

- Google Cast 场景可使用 Output Switcher，也就是系统提供的媒体输出设备面板。
- 基于 DNS 的服务发现（DNS-SD）场景可使用 `DiscoveryRequest.FLAG_SHOW_PICKER`；mDNS 常用来在局域网内承载 DNS-SD 查询。
- 用户选中的服务会获得按服务授权，不需要应用取得整个局域网的访问权限。

NSD 是 Network Service Discovery 的缩写，即 Android 的网络服务发现 API。Android 17 的 NSD 设备选择器也通过 T SDK Extension 22 提供；这里的 T 指 Android 13，SDK Extension 是系统模块更新带来的 API 版本，可能在不升级完整 Android 大版本的设备上增加新接口。运行在可接收模块更新的旧平台时，应检查 T 扩展版本；示例只展示 Android 17 直接路径。

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

### 路径二：运行时权限

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

## 失败分类与系统证据

本地网络权限、TLS 和弱网在界面上都可能表现为连接失败，诊断字段必须分开。TLS 负责加密传输；ECH 加密 TLS 初始握手中的服务器名称指示（SNI），减少网络中间设备看到目标域名的机会；应用层协议协商（ALPN）用于在握手时选择 HTTP/2 等上层协议。

| 类别 | Android 17 常见表现 | 记录字段 | 不应推断 |
| --- | --- | --- | --- |
| 本地网络阻断 | UDP 与一般权限拒绝通常返回 `EPERM`，即操作系统的权限不足错误；TCP 通常表现为超时 | target SDK、权限状态、传输协议、目标地址类别、设备选择器路径 | 服务器下线或 TLS 证书错误 |
| TLS / ECH | TLS 握手、证书验证、SNI/ECH 或 ALPN 失败 | 域名分组、TLS 版本、网络库、证书错误类别 | 缺少本地网络权限 |
| 弱网与低带宽 | 首包慢、媒体分片超时、缓冲下降 | 网络会话、吞吐估计、缓冲时长、运营商速率是否已知 | 运营商上限一定生效 |
| NSD 选择器 | `FAILURE_PERMISSION_DENIED`、未选择服务、服务授权被撤销 | API/扩展版本、服务类型分组、授权查询结果 | 用户拒绝广泛权限 |

Android 17 官方迁移文档把 `android_getnetworkblockedreason(sockFd)` 称为 NDK API。C/C++ 网络代码可在 TCP 套接字失败后查询它。只有返回 `ANDROID_NETWORK_BLOCKED_REASON_LNP`，才能把该连接归因到本地网络保护（Local Network Protection，LNP）。截至 2026-08-15，NDK 公开参考页尚未列出这个符号；网络库需要按构建所用 NDK 和设备版本检查声明与符号是否可用，不能假定旧版本可直接链接。普通 Java/Kotlin TCP 超时没有同等精确的公开错误码，也不能见到超时就上报为权限拒绝。

`android-17.0.0_r1` 的实现提供了两条可核对的证据：

- `PermissionMonitor` 接收 `ACCESS_LOCAL_NETWORK` 权限位，并把结果同步到网络 BPF 权限映射。BPF 是 Linux 内核中可编程的数据包处理机制，这里的映射保存应用在 Linux 中的用户标识（UID）及其联网策略。
- Connectivity 的 C/C++ 接口读取套接字的 `SO_ANDROID_DROP_REASON`，只在阻断原因包含本地网络保护时返回 `ANDROID_NETWORK_BLOCKED_REASON_LNP`。

保护位于操作系统网络栈，更换 OkHttp、Cronet 或 Java Socket 不会改变权限结果。

## 与低带宽、卫星和 ECH 的关系

运营商流媒体上限只是媒体预算来源之一。应用仍要结合 `NetworkCapabilities`、实时吞吐、缓冲、漫游、计费和卫星网络状态。以下字段名是一份诊断事件示例，不是 Android 强制规定的接口：

- `media_plan_limit_kbps` 只约束当前订阅上的媒体质量。
- `measured_bps` 反映近期路径吞吐，用于短周期升降档。
- `network_profile` 描述蜂窝、Wi-Fi、卫星、VPN、漫游和计费状态。
- `local_access_state` 描述广泛权限、设备选择授权、拒绝和旧应用隐式授权。
- `request_class` 决定媒体、本地发现、控制和普通 API 各自使用哪组规则。

本地网络权限拒绝不能触发所有互联网请求降级，蜂窝数据计划上限也不能限制 Wi-Fi 局域网控制。

Android 17 为目标 API 37 及以上应用把 ECH 默认模式设为 `enabled`。这项配置只对已经集成 ECH 的网络库生效，远端服务器也必须发布可用配置；HttpEngine、WebView 或 OkHttp 等库的具体版本仍需单独确认。协商条件不满足时，支持该机制的客户端会发送内容随机的 ECH GREASE 扩展，避免中间设备只接受未携带 ECH 的固定握手格式。`<domainEncryption>` 控制全局或指定域名的 ECH 模式，它不授予局域网访问，也不改变 `ACCESS_LOCAL_NETWORK` 的判定。详细安全边界见 24.15。

## 验证与分阶段发布

### 流媒体速率实验

对照组和候选组使用相同播放器、Media3 版本、媒体清单、内容分发网络（CDN）和服务端配置，只改变运营商速率上限如何进入质量选择。至少并列报告：

- 速率上限已知、未知、无读取权限和不支持订阅功能的样本数。
- 当前网络、默认数据订阅是否匹配，以及网络切换前后的重新计算结果。
- 启播成功率、首缓冲分布、首个媒体分片质量、升降档次数、重缓冲次数与时长。
- 下行媒体字节、重复下载字节、直播延迟或 RTC 上行质量。
- 按运营商分组的结果，但不保存原始订阅标识。

只统计成功播放会漏掉候选策略导致的早期失败。评估质量变化时，还要同时检查流量、功耗、解码丢帧和设备温度。

### 本地网络迁移实验

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

### 区分回调延迟与网络传输延迟

套接字或播放器已经收到数据后，主线程排队仍可能延迟界面更新。Android 17 为目标 API 37 及以上应用启用新的无锁 `MessageQueue` 实现，源码中称为 DeliQueue；它改变的是消息入队和投递，不是网络传输。应分别记录网络完成、播放器消费和界面提交事件，再按 16.5 的回调投递方法排查。

## `android-17.0.0_r1` 源码锚点

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

## 发布前检查清单

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
