---
title: "Android 17 流媒体网络预算与本地网络权限适配"
chapter: "24.16"
section: "24.16"
status: finalized
drafted_date: "2026-05-24"
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
related_chapters: ["12.2", "12.4", "16.5", "24.10", "24.11", "24.14", "26.17"]
created_by: "task2a-knowledge-gap"
drafted_by: "openclaw-task2a"
created_date: "2026-05-24"
gap_source: "研究素材/官方文档/每日信息/Clippings结构参考"
gap_score: 16
material_count: 5
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
reviewed_by: openclaw-task6
reviewed_date: "2026-05-24"
last_task6_at: "2026-05-24T19:14:00+08:00"
last_task6_audit: "2026-07-01"
last_task6_review_log: "logs/review/2026-05-24-19-review.md"
task6_l1_l2_fixes: 7
task6_l3_l4_issues: 0
task6_new_rework: false
task9_reviewed_date: "2026-05-24"
task9_reviewed_by: openclaw-task9
last_task9_at: 2026-05-24T19:30:00+08:00
last_task9_review_log: "logs/deep-review/2026-05-24-19-deep-review.md"
last_task9_audit: "2026-06-14"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-04
---

# 24.16 Android 17 流媒体网络预算与本地网络权限适配

<!-- outline-start -->
## 要点

### 🔹 场景边界：流媒体限速、本地设备发现与普通 API 请求
区分视频/音频流媒体码率决策、Cast/IoT/局域网设备发现、普通 HTTP API 请求三类网络路径，避免把 Android 17 的连接性变更写成所有网络请求的统一优化入口。

### 🔹 Data Plan Streaming API 的使用边界
梳理 `SubscriptionInfo.getStreamingAppMaxDownlinkKbps()` / `getStreamingAppMaxUplinkKbps()`、`SubscriptionPlan.BITRATE_UNKNOWN`、运营商数据计划和 ABR 码率选择之间的关系。

### 🔹 ACCESS_LOCAL_NETWORK 对局域网链路的影响
覆盖 Android 16 opt-in 到 Android 17 targetSdk 37 强制执行的迁移路径，说明 mDNS、SSDP、本地 HTTP server、投屏和 IoT 控制的权限与降级策略。

### 🔹 与卫星/低带宽网络适配的关系
复用 24.11 的低带宽预算思想，把运营商流媒体速率上限、本地网络权限拒绝和弱网/卫星网络能力合并到请求调度策略中。

### 🔹 TLS 与本地网络权限的取证差异
说明 TLS/ECH/证书失败属于 12.4 的安全连接问题，本地网络权限失败属于权限与目标 SDK 问题；两者按异常类型、日志和用户授权路径分别记录。

### 🔹 灰度实验与线上指标
设计 targetSdk 36/37 对照、权限授权率、局域网发现成功率、流媒体首缓冲、码率切换、卡顿率和运营商网络分组指标，用于上线验证。

## 扩展

### 🔸 Media3 ABR 与平台流媒体速率上限的映射
记录 Media3/ExoPlayer 的码率估计如何接入运营商上限，避免把瞬时测速和 data plan cap 混成同一个信号。

### 🔸 Cast / IoT 场景的权限替代路径
整理 output switcher、系统选择器和显式 runtime permission 三种路径的产品取舍。

### 🔸 Android 17 网络行为变更回归清单
建立 targetSdk 37 前后的局域网、TLS、卫星/低带宽、DeliQueue 回调投递回归项。

<!-- outline-end -->

## 这节解决什么问题

Android 17 把两类网络适配推到应用侧：流媒体可以读取运营商分配的上下行速率上限，本地网络访问在 `targetSdkVersion >= 37` 后进入运行时权限模型。前者影响视频、音频、直播和 RTC 的码率选择；后者影响投屏、局域网设备发现、本地 HTTP 服务和 IoT 控制。

这两个变化各走各的路径，不要合并成笼统的“网络请求优化”。普通 REST / GraphQL API 继续走 24.10 和 24.14 的 DNS、连接复用、超时、重试、弱网策略；本节只处理媒体码率预算和 LAN 访问授权。低带宽、卫星网络和请求分段策略见 24.11、24.14，TLS / ECH / 证书透明度见 12.4。

## 三类网络路径要分开建模

Android 17 相关改动落到三条路径上，触发条件和失败形态不同。

| 路径 | 典型业务 | Android 17 相关点 | 失败或退化形态 | 处理入口 |
| --- | --- | --- | --- | --- |
| 流媒体传输 | 点播、直播、音频流、RTC 上行 | `SubscriptionInfo` 新增 streaming app max bitrate API | 初始码率过高、首缓冲变长、频繁降码率 | ABR 上限、清晰度默认档、分运营商指标 |
| 本地网络访问 | Cast、IoT、mDNS、SSDP、本地 HTTP server | `ACCESS_LOCAL_NETWORK` 在 `targetSdkVersion >= 37` 下强制执行 | UDP `EPERM`、TCP 被 LNP 阻断、设备发现为空 | 系统选择器、运行时权限、拒绝后降级 |
| 普通 API 请求 | 登录、Feed、配置、埋点、图片列表 | 受 DNS、TLS、弱网、队列调度影响 | 超时、重试、连接失败、回调延迟 | 24.10、24.14、26.17 |

使用这张表时，先给每个请求标记 `traffic_class`，再决定用哪个策略组。媒体流不要沿用普通 API 的重试策略；局域网发现失败也不要直接归因到 DNS 或 TLS。

## Data Plan Streaming API 只是一条上限信号

Android 17 在 `SubscriptionInfo` 上新增 `getStreamingAppMaxDownlinkKbps()` 和 `getStreamingAppMaxUplinkKbps()`，返回运营商为流媒体应用分配的最大下行或上行速率，单位是 Kbps；未知或不适用时返回 `SubscriptionPlan.BITRATE_UNKNOWN`。[已验证: 官方文档, https://developer.android.com/reference/android/telephony/SubscriptionInfo#getStreamingAppMaxDownlinkKbps()]

这条信号适合做 ABR 的“外部上限”，不要拿去替代实时带宽估计。运营商上限是套餐或网络策略允许的媒体速率，`BandwidthMeter` 是最近传输样本推导出的吞吐估计——一个是上限，一个是估计值。两者冲突时，播放器取更保守的一方，同时保留冷启动默认档位。

读取 `SubscriptionInfo` 还要处理权限边界。`SubscriptionManager.getActiveSubscriptionInfoList()` 需要 `READ_PHONE_STATE` 或运营商权限，返回列表按 SIM slot 和 subscription id 排序；从 Android SDK 35 起不会返回 `null`，但仍可能返回空列表或只返回调用方可见的订阅。[已验证: 官方文档, https://developer.android.com/reference/android/telephony/SubscriptionManager#getActiveSubscriptionInfoList()]

这段代码的重点是预算层的接口行为，关键看 `BITRATE_UNKNOWN` 和 `READ_PHONE_STATE` 失败后的降级路径：

```kotlin
@RequiresApi(37)
fun streamingBudgetKbps(
    context: Context,
    fallbackKbps: Long = 2_500L,
): Long {
    val subscriptionManager = context.getSystemService(SubscriptionManager::class.java)
    val subscriptions = try {
        subscriptionManager.activeSubscriptionInfoList.orEmpty()
    } catch (security: SecurityException) {
        return fallbackKbps
    } catch (unsupported: UnsupportedOperationException) {
        return fallbackKbps
    }

    val caps = subscriptions
        .asSequence()
        .map { it.streamingAppMaxDownlinkKbps }
        .filter { it != SubscriptionPlan.BITRATE_UNKNOWN && it > 0L }
        .toList()

    return caps.minOrNull() ?: fallbackKbps
}
```

`fallbackKbps` 不要硬编码成全局常量。冷启动时应该按网络类型、历史首缓冲、地区、运营商和设备档位来取；拿到平台上限后，只把它用作 ABR 可选档位的上界。双卡设备按当前数据订阅优先；拿不到当前数据订阅到 `SubscriptionInfo` 的稳定映射时，取可见 cap 的较小值更保守。

## ABR 接入点：限制候选档位，不篡改测速

Media3 的 `AdaptiveTrackSelection` 是基于带宽的自适应选择，选中轨道会随网络条件和缓冲状态变化；默认 `DEFAULT_BANDWIDTH_FRACTION` 是 `0.7f`，用于给带宽估计留余量。[已验证: 官方文档, https://developer.android.com/reference/androidx/media3/exoplayer/trackselection/AdaptiveTrackSelection]

`DefaultBandwidthMeter` 的默认初始估计是 `1_000_000` bps，网络类型不可用或离线时会用这类初始值；它还维护 2G、3G、4G、5G 和 Wi-Fi 的默认初始估计。[已验证: 官方文档, https://developer.android.com/reference/androidx/media3/exoplayer/upstream/DefaultBandwidthMeter]

工程接入的时候，把平台 cap 转成“可选 track 的最高码率”，不要直接用运营商 cap 覆盖掉 `BandwidthMeter` 的实时估计。覆写测速样本会污染后续估计，切换网络时的判断也会变得迟钝。

| 输入信号 | 更新频率 | 适合影响 | 不适合影响 |
| --- | --- | --- | --- |
| `streamingAppMaxDownlinkKbps` | 订阅、运营商策略、网络切换时刷新 | 最大视频档、默认清晰度、首段码率 | 单个 segment 的重试时机 |
| `DefaultBandwidthMeter.bitrateEstimate` | 传输样本持续刷新 | 当前档位升降、缓冲恢复 | 套餐策略判断 |
| 首缓冲 / 卡顿指标 | 播放会话内持续采样 | 灰度回滚、地区和运营商分组 | 单次权限弹窗策略 |

如果业务有服务端清晰度编排，客户端 cap 还要同步给服务端，但只传区间或档位，不上传完整订阅标识。服务端返回的 media playlist 可以少下发超过 cap 的档位，减少 manifest 解析和错误选择成本。

## `ACCESS_LOCAL_NETWORK` 的迁移路径

Android 17 为本地网络访问引入 `ACCESS_LOCAL_NETWORK` 运行时权限。对 `targetSdkVersion >= 37` 的应用，本地网络默认被阻断；应用要么使用系统介导的设备选择器，要么在运行时请求该权限。Android 16 允许应用 opt-in 测试本地网络限制，Android 17 对目标 SDK 37 及以上强制执行。[已验证: 官方文档, https://developer.android.com/about/versions/17/behavior-changes-17]

本地网络权限属于 `NEARBY_DEVICES` 权限组。用户已经授予同组其他权限时，系统可能不再弹出新的提示；用户拒绝或在设置里撤销后，本地网络流量会被阻断。官方迁移表还说明，`targetSdkVersion < 37` 的旧应用如果已有 `INTERNET` 权限，会获得临时隐式授权，升级到 37 后不再依赖这条路径。[已验证: 官方文档, https://developer.android.com/privacy-and-security/local-network-permission]

Manifest 只解决声明问题，运行时仍要按权限状态分支。下面的声明用于 target SDK 37 后直接访问 LAN 的场景：

```xml
<uses-permission android:name="android.permission.ACCESS_LOCAL_NETWORK" />
```

权限请求前要先判断业务是否能使用系统选择器。对 Cast 类媒体投屏，output switcher 由系统处理本地发现和连接，应用可以避开宽泛权限；对 mDNS 设备发现，`DiscoveryRequest#FLAG_SHOW_PICKER`、`NsdManager#registerServiceInfoCallback` 和 `NsdManager#resolveService` 可以让用户选择设备，随后连接由系统返回的地址。需要持续扫描、批量控制或后台维护连接的 IoT 场景，才适合请求 `ACCESS_LOCAL_NETWORK`。[已验证: 官方文档, https://developer.android.com/privacy-and-security/local-network-permission]

## 本地网络失败不要和 TLS 失败混在一起

Android 17 还为目标 SDK 37 及以上应用启用 ECH。ECH 只在网络库和服务器都支持时生效；无法协商时会发送带随机内容的 ECH GREASE 扩展。平台还新增 `<domainEncryption>`，允许在 Network Security Configuration 中按域名控制 ECH 模式。[已验证: 官方文档, https://developer.android.com/about/versions/17/behavior-changes-17]

ECH、证书透明度、证书链、SNI 和 ALPN 属于互联网 TLS 取证；`ACCESS_LOCAL_NETWORK` 属于本地地址访问授权。把这两类失败混到同一个 `NetworkError`，线上排查方向就会跑偏。

| 失败类别 | 典型异常 / 现象 | 应记录字段 | 关联章节 |
| --- | --- | --- | --- |
| LNP 阻断 | UDP 返回 `EPERM`，TCP 可用 `android_getnetworkblockedreason(sockFd)` 识别 `ANDROID_NETWORK_BLOCKED_REASON_LNP` | target SDK、权限状态、协议、目标地址类型、用户是否从 picker 进入 | 16.5、24.16 |
| TLS / ECH | 握手失败、证书校验失败、ECH 配置不兼容 | domain、TLS version、cipher suite、ECH mode、证书错误码 | 12.4 |
| 弱网 / 低带宽 | 首包慢、segment 下载超时、连续降码率 | network type、RTT、throughput、buffered duration、cap Kbps | 24.11、24.14、26.17 |

浏览器、内置 WebView 容器和本地开发服务要额外记录目标 IP 是否属于 RFC1918、IPv6 ULA、link-local 或 `.local` 名称。这样能把“访问内网服务被 LNP 阻断”和“公网域名 TLS 失败”拆开。

## 和低带宽/卫星网络的关系

24.11 已把低带宽和卫星网络处理成预算模型：先识别网络能力，再收缩并发、请求体、重试和媒体质量。`streamingAppMaxDownlinkKbps()` 是这套模型里新增的媒体预算来源，不能单独驱动所有网络策略。

推荐的调度输入如下：

- `media_cap_kbps`: 来自 `SubscriptionInfo` 的流媒体上下行上限，未知时用历史和网络类型兜底。
- `measured_bps`: 来自播放器或网络库的近期吞吐估计，用于短周期升降档。
- `network_profile`: 蜂窝、Wi-Fi、卫星、VPN、漫游、低数据模式等环境标签。
- `local_access_state`: `granted`、`denied`、`picker_granted`、`legacy_implicit`、`unknown`。
- `request_class`: `media_segment`、`media_manifest`、`lan_discovery`、`lan_control`、`api`、`analytics`。

调度策略按请求类别收敛。`media_segment` 受 `media_cap_kbps` 和 `measured_bps` 约束；`lan_discovery` 受 `local_access_state` 约束；普通 `api` 请求只参考弱网策略和连接池状态。这样能避免一个权限拒绝把所有网络请求都降级，也避免蜂窝套餐 cap 影响 Wi-Fi 下的局域网设备控制。

## 灰度实验和指标口径

target SDK 37 的灰度要拆成两条实验线。

| 实验线 | 对照组 | 实验组 | 观察指标 | 回滚条件 |
| --- | --- | --- | --- | --- |
| 流媒体 cap | 只用 Media3 默认 ABR 和历史测速 | ABR 叠加 `SubscriptionInfo` cap | 首缓冲 P50/P90、首段码率、降码率次数、rebuffer ratio、播放失败率 | 首缓冲或卡顿按运营商分组升高 |
| 本地网络权限 | target SDK 36 或 Android 16 opt-in | target SDK 37 + picker / runtime permission | 权限授权率、拒绝后留存、设备发现成功率、投屏成功率、IoT 控制成功率 | 局域网发现成功率下降且 picker 不能覆盖 |

指标维度至少包含 Android 版本、target SDK、网络类型、运营商、国家/地区、是否双卡、播放器版本、Media3 版本、是否使用系统 picker。权限弹窗要单独记录入口页和业务动作，不要只记录全局授权率；投屏入口、设备列表页、播放页和设备控制页的授权转化差异需要分入口评估。

## Android 17 网络行为变更回归清单

发布前按功能回归，不按 API 名称回归。

- 流媒体播放: 蜂窝下读取 `streamingAppMaxDownlinkKbps()`，未知值走历史默认档；双卡切换、飞行模式恢复、Wi-Fi / 蜂窝切换后刷新 cap；低 cap 下不会选择超过预算的首段码率。
- RTC / 直播上行: 读取 `getStreamingAppMaxUplinkKbps()`，未知值不阻断开播；上行 cap 只影响编码目标码率，不影响信令连接。
- Cast: 优先走 output switcher；拒绝 `ACCESS_LOCAL_NETWORK` 后仍能使用系统介导路径；直接连接 receiver 的路径有权限态提示和降级文案。
- IoT / mDNS: Android 16 通过 `adb shell am compat enable RESTRICT_LOCAL_NETWORK <package_name>` 提前压测；Android 17 target SDK 37 下验证拒绝、撤销、再次授权、系统 picker 选中设备四种路径。
- TLS / ECH: 按域名验证 `<domainEncryption>` 配置；ECH 失败不应被归类成 LNP；证书透明度和证书链失败进入 12.4 的安全连接指标。
- 回调投递: 网络完成后 UI 更新延迟进入 16.5 的 MessageQueue / DeliQueue 回归项，不把它当成链路吞吐问题。

## 小结

Android 17 的网络适配要按路径拆开：流媒体用运营商 cap 收紧 ABR 候选档位，本地网络用 picker 或 `ACCESS_LOCAL_NETWORK` 处理授权，普通 API 请求沿用 DNS、TLS、弱网和连接池治理。上线判断看分组指标，不看单个 API 是否调用成功。
