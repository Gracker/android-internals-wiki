---

title: "Wi-Fi 评分、网络选择与连接切换性能"
chapter: "24.9"
status: ready-for-review
drafted_date: "2026-05-15"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-15"
last_verified_against: "AOSP main (packages/modules/Wifi, packages/modules/Connectivity, packages/modules/NetworkStack) + Android Developers / source.android.com docs"
confidence: medium
sources:
  - type: aosp
    path: "packages/modules/Wifi/service/java/com/android/server/wifi/WifiNetworkSelector.java"
  - type: aosp
    path: "packages/modules/Wifi/service/java/com/android/server/wifi/WifiCandidates.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkRanker.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/connectivity/FullScore.java"
  - type: aosp
    path: "packages/modules/NetworkStack/src/com/android/server/connectivity/NetworkMonitor.java"
  - type: official
    path: "https://source.android.com/docs/core/connect/wifi-network-selection"
  - type: official
    path: "https://source.android.com/docs/core/connect/network-selection"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/reading-network-state"
  - type: official
    path: "https://developer.android.com/reference/android/net/NetworkCapabilities"
  - type: blog
    path: "DeepResearch/2026-05-14-android-wifi-scoring-connectivity-service.md"
  - type: book_structure
    path: "Clippings/Android 性能优化 - 原理:重新认识应用的速度优化.md"
  - type: book_structure
    path: "Clippings/Android 性能优化 - CPU 优化(下):减少 CPU 闲置时刻和等待,提升利用率.md"
  - type: book_structure
    path: "Clippings/Android 性能优化 - 缓存优化:冷热端分离+重排序,提升缓存命中率.md"
  - type: book_structure
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 18.md"
  - type: book_structure
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 19.md"
  - type: book_structure
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 20.md"
tags: [wifi, connectivity, network, latency, scoring, performance]
related_chapters: ["12.2", "12.3", "24.4", "24.5", "15.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-15"
gap_source: "AOSP结构/研究素材"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-15"
task6_result: pass-light-edit
task6_state: 'reviewed'
last_task6_at: '2026-06-03T12:15:21+08:00'
task6_review_notes: '2026-06-03 Task6 12:15：pass-light-edit（revisit）。L1/L2 扫描无新增问题；禁用词/高频词/AI 填充词零命中。无新增回炉项。'
task9_state: 'pending'
pipeline_stage: 'task6_pending'
task9_result: needs-rework
task2b_state: 'fixed'
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-15
last_task9_at: 2026-05-15T16:20:00+08:00
last_task9_review_log: logs/deep-review/2026-05-15-16-deep-review.md
task2b_result: 'fixed'
task2b_fixed_date: '2026-06-03'
task2b_fixed_at: '2026-06-03T10:53:52'
last_task2b_at: '2026-06-03T10:53:52'
---

# 24.9 Wi-Fi 评分、网络选择与连接切换性能

App 看到的"网络可用",通常已经经过系统侧两层筛选:Wi-Fi 模块先在候选 AP 里选一个,Connectivity 模块再在 Wi-Fi、蜂窝、VPN 等网络之间选默认网络。工程上最容易误判的是:Wi-Fi 信号还在,请求却突然变慢、断开或切到蜂窝;App 侧要把系统选择、请求阶段和降级策略分开记录。

连接池、TLS、HTTP/2、HTTP/3 的协议细节详见 12.2、12.3、24.4、24.5;这里讨论系统网络选择和 App 侧观测。

## 要点

### 🔹 ConnectivityService 与 Wi-Fi 模块分工

系统网络选择可以拆成两级。

```text
Wi-Fi 扫描结果
  → WifiNetworkSelector 过滤弱信号、黑名单、策略限制
  → NetworkNominator 生成候选网络
  → CandidateScorer 给同一组候选排序
  → WifiNetworkAgent 把已连接网络作为 NetworkAgent 上报
  → ConnectivityService(Android 10/11 integer score / Android 12+ NetworkRanker 策略规则)在所有 NetworkAgent 中选择默认网络
  → App 通过 ConnectivityManager 观察默认网络变化
```

Wi-Fi 模块回答"连哪个 AP"。Connectivity 模块回答"当前请求走哪个 Network"。这两个问题相关,但不能混成一个评分。

AOSP `WifiNetworkSelector` 的 `filterScanResults()` 会过滤 RSSI 低于 entry threshold 的 BSSID、被 blocklist 命中的 BSSID、被管理策略限制的 SSID,以及部分 deprecated security type。之后 `selectNetwork()` 使用 `WifiCandidates.CandidateScorer` 对分组候选评分,并把选中的 scan result 写回 `WifiConfigManager.setNetworkCandidateScanResult()`。[已验证: AOSP main, packages/modules/Wifi/service/java/com/android/server/wifi/WifiNetworkSelector.java]

Connectivity 侧已经从传统整数分数演进到策略规则。source.android.com 的 network selection 文档说明,现代 Android 的网络选择策略位于 Connectivity 模块的 `NetworkRanker` 及其辅助类;设备厂商不能直接替换选择代码,只能通过 `NetworkScore` 的 flags 表达网络属性。[已验证: 官方文档, https://source.android.com/docs/core/connect/network-selection]

两个版本段的默认网络选择方式不同,不能混用:

| 版本 | 选择机制 | 评分方式 |
| --- | --- | --- |
| Android 10 / 11 (API 29-30) | ConnectivityService 基于 NetworkAgent 上报的 integer score 排序 | `NetworkAgentInfo.score` + validated/VPN/metered bonus/penalty;同分时行为未定义 |
| Android 12+ (API 31+) | `NetworkRanker.getBestNetworkByPolicy()` 策略规则排序 | `NetworkScore` flags(`POLICY_TRANSPORT_PRIMARY` / `POLICY_EXITING` / `POLICY_IS_VALIDATED` 等)决定优先级 |

App 不能假设所有用户设备都运行 Android 12+。线上仍有 Android 10/11 设备时,网络选择可能基于旧版 integer score,同分 BSSID 之间的行为无保证。建议在 APM 中记录 `Build.VERSION.SDK_INT` 和默认网络来源,后续排查才能对齐系统行为。

`NetworkRanker.getBestNetworkByPolicy()` 的排序不是简单"分数越大越好"。代码先处理 invincible network、VPN、用户显式选择并接受未验证网络、validated / accept-unvalidated,再处理 exiting、primary transport、transport preference 和 current satisfier。当前已满足请求的网络在策略等价时会被保留,避免默认网络在边界条件下频繁跳变。[已验证: AOSP main, packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkRanker.java]

这解释了一个常见线上现象:Wi-Fi RSSI 变差后,App 不一定马上看到默认网络切走。系统会同时考虑验证状态、用户选择、是否计费、VPN、当前网络是否仍能满足 request,以及切换带来的稳定性代价。

### 🔹 Wi-Fi 评分输入

Wi-Fi 选择不是只看信号格数。AOSP 和官方文档里能确认的输入至少包含这些维度:

| 输入 | 系统侧含义 | App 侧判断方式 |
|---|---|---|
| RSSI / 频段 | 低于 entry threshold 的 BSSID 会被过滤;2.4GHz、5GHz、6GHz 阈值可由 overlay 配置 | 不把"信号满格"当成吞吐保证;同时看 RTT、丢包、TTFB |
| 当前连接是否够用 | screen-on connected 场景下,当前网络满足条件时可跳过重新选择 | 观察默认网络是否切换,不要只盯 Wi-Fi scan |
| 是否 validated | 已验证互联网可达或用户允许无互联网连接,会影响是否继续选网 | `NET_CAPABILITY_INTERNET` + `NET_CAPABILITY_VALIDATED` 同时看 |
| 是否 metered | 未计费网络更适合大下载;计费 Wi-Fi 不能当成"免费网络" | 看 `NET_CAPABILITY_NOT_METERED`,不要只看 `TRANSPORT_WIFI` |
| 历史失败 / blocklist | 反复连接失败、频繁断开、AP 明确要求暂不关联的 BSSID 会被过滤 | 通过 bugreport / `dumpsys wifi` 查 blocked BSSID 和失败原因 |
| 用户选择 | 用户刚手动连接的网络会在一段时间内得到保护 | 遇到"看起来弱但不切"的 case,要检查是否用户刚手选 |
| OEM overlay | entry RSSI threshold、用户选择保护窗口、PNO 行为等可由设备配置影响 | 厂商机型必须用实机 dumpsys 和 trace 复核 |

source.android.com 的 Wi-Fi network selection 文档给出"当前网络够用即可跳过选择"的判定:RSSI 高于阈值或有足够流量,网络已验证或用户允许无互联网使用,并且网络未计费。若当前 Wi-Fi 不够用或设备未连接,框架才会调用 nominators 生成候选网络,再过滤弱 RSSI、被阻止的 BSSID 等候选。[已验证: 官方文档, https://source.android.com/docs/core/connect/wifi-network-selection]

AOSP `WifiCandidates.CandidateImpl` 暴露了 `getScanRssi()`、`getFrequency()`、`getPredictedThroughputMbps()`、`isMetered()`、`hasNoInternetAccess()`、`isUserSelected()`、`isCurrentNetwork()` 等字段。工程上可以把这些字段理解成"选择输入",不要把旧资料里 0-60、20/40/60 这类固定阈值直接写进发布判断;不同 Android 版本和厂商 overlay 都可能改变边界。[已验证: AOSP main, packages/modules/Wifi/service/java/com/android/server/wifi/WifiCandidates.java]

[结构参考: Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 18.md] 网络问题分析要先把基础网络状态、I/O 等待和业务请求阶段拆开。这里借鉴它的拆分方式,但系统选网事实以 AOSP 和官方文档为准。

### 🔹 连接切换的性能指标

网络切换不能只看"断没断"。线上监控至少要把系统网络变化和 HTTP 请求阶段分开记。

| 指标 | 起点 | 终点 | 适合回答的问题 |
|---|---|---|---|
| 默认网络切换耗时 | `NetworkCallback.onLost(old)` 或 `onAvailable(new)` | `onCapabilitiesChanged(new)` 出现可用能力 | 系统是否完成默认网络迁移 |
| 互联网验证恢复耗时 | 新 network 出现 `NET_CAPABILITY_INTERNET` | 同一 network 出现 `NET_CAPABILITY_VALIDATED` | Captive Portal、DNS、探测失败是否拖慢恢复 |
| DNS 恢复耗时 | OkHttp `dnsStart` | `dnsEnd` 或 `UnknownHostException` | 切网后 DNS 是否超时、污染或缓存失效 |
| TCP / TLS 建连耗时 | `connectStart` / `secureConnectStart` | `connectEnd` / `secureConnectEnd` | IP 质量、IPv6/IPv4、证书链和 TLS 版本问题 |
| 首包耗时 | `requestHeadersEnd` | `responseHeadersStart` | 服务端、CDN、无线链路、拥塞是否影响 TTFB |
| 用户感知中断时长 | 页面触发请求或播放卡住 | 首个成功响应 / 播放恢复 | 用户看到的"卡住多久" |

OkHttp EventListener 提供了请求生命周期事件。官方 events 文档列出了 `dnsStart/dnsEnd`、`connectStart/connectEnd`、`secureConnectStart/secureConnectEnd`、`responseHeadersStart/responseHeadersEnd` 等事件,也说明连接复用时第二次请求不会再出现 connect 事件。[已验证: 官方文档, https://square.github.io/okhttp/features/events/]

一段可用的采集代码如下。重点是每个 call 单独保存状态,避免并发请求互相覆盖时间戳。

```kotlin
class NetTimingListener(
    private val callId: Long,
    private val networkSnapshot: () -> String,
    private val report: (Map<String, Any>) -> Unit,
) : EventListener() {
    private val t = mutableMapOf<String, Long>()

    private fun mark(name: String) {
        t[name] = SystemClock.elapsedRealtime()
    }

    override fun callStart(call: Call) {
        mark("callStart")
    }

    override fun dnsStart(call: Call, domainName: String) {
        mark("dnsStart")
    }

    override fun dnsEnd(call: Call, domainName: String, inetAddressList: List<InetAddress>) {
        mark("dnsEnd")
    }

    override fun connectStart(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy) {
        mark("connectStart")
    }

    override fun secureConnectStart(call: Call) {
        mark("secureConnectStart")
    }

    override fun secureConnectEnd(call: Call, handshake: Handshake?) {
        mark("secureConnectEnd")
    }

    override fun connectEnd(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
        protocol: Protocol?,
    ) {
        mark("connectEnd")
    }

    override fun responseHeadersStart(call: Call) {
        mark("responseHeadersStart")
    }

    override fun callEnd(call: Call) {
        mark("callEnd")
        report(
            mapOf(
                "call_id" to callId,
                "network" to networkSnapshot(),
                "dns_ms" to delta("dnsStart", "dnsEnd"),
                "connect_ms" to delta("connectStart", "connectEnd"),
                "tls_ms" to delta("secureConnectStart", "secureConnectEnd"),
                "ttfb_ms" to delta("callStart", "responseHeadersStart"),
            )
        )
    }

    override fun callFailed(call: Call, ioe: IOException) {
        mark("callFailed")
        report(
            mapOf(
                "call_id" to callId,
                "network" to networkSnapshot(),
                "error" to ioe.javaClass.name,
                "message" to (ioe.message ?: ""),
            )
        )
    }

    private fun delta(start: String, end: String): Long =
        (t[end] ?: -1L).let { e -> if (e < 0) -1L else e - (t[start] ?: e) }
}
```

这里的 `networkSnapshot()` 建议记录 active network id、transport、`INTERNET`、`VALIDATED`、`NOT_METERED`、VPN 状态和网络切换事件序号。单独记录 OkHttp 耗时还不够;切网前后的 DNS 慢、连接慢和服务端慢,在 HTTP 层看到的错误形态很像。

[结构参考: Clippings/Android 性能优化 - CPU 优化(下):减少 CPU 闲置时刻和等待,提升利用率.md] 这里借用"等待 I/O 会拉长主流程耗时"的组织方式,把网络请求拆成可观测阶段。

### 🔹 弱网与多网络并存场景

弱网排查要先判断系统是否认为"有互联网"。Android 官方文档把 `NET_CAPABILITY_INTERNET` 和 `NET_CAPABILITY_VALIDATED` 分开:前者表示网络配置上可达互联网,后者表示系统探测到公网可达;Captive Portal 或 DNS 不可用时,网络可能有 `INTERNET` 但没有 `VALIDATED`。[已验证: 官方文档, https://developer.android.com/develop/connectivity/network-ops/reading-network-state] [已验证: 官方文档, https://developer.android.com/reference/android/net/NetworkCapabilities]

App 侧判断建议按下面的顺序做:

1. `getActiveNetwork() == null`: 没有默认网络。直接进入离线态,取消或暂停非必要请求。
2. 有 network 但无 `NET_CAPABILITY_INTERNET`: 这不是普通公网网络。不要发密集公网探测。
3. 有 `INTERNET` 但无 `VALIDATED`: 可能是 Captive Portal、DNS 失败、私有网络、探测服务不可达。保留本地缓存,降低重试频率。
4. 有 `VALIDATED` 但请求慢: 再看 DNS、TCP、TLS、TTFB、body download 的分段耗时。
5. 有 VPN: 同时记录 underlying transport。VPN 可能改变 DNS、路由和证书策略。

`NetworkMonitor` 负责网络验证和 Captive Portal 探测。AOSP `sendDnsProbe()` 使用 DNS resolver 做域名解析,`sendHttpProbe()` 对已知探测 URL 发起 HTTP 请求并根据响应判断。探测结果会通过 `NETWORK_VALIDATION_RESULT_VALID`、partial connectivity、skipped 等结果通知 ConnectivityService。[已验证: AOSP main, packages/modules/NetworkStack/src/com/android/server/connectivity/NetworkMonitor.java]

多网络并存时,App 常见误判有三类:

- **Wi-Fi 图标还在,但默认网络已切到蜂窝**:用户看到 Wi-Fi 图标,不代表当前请求一定走 Wi-Fi。以 `NetworkCallback` 的 default network 为准。
- **Wi-Fi validated 失败,但业务 HTTP 偶尔成功**:系统探测 URL 失败和业务域名成功可以同时发生。此时不要把系统状态当成服务端故障,也不要把单个业务成功当成全网恢复。
- **VPN 下网络变慢**:VPN 是 Connectivity 排序里的高优先级对象。排查时要把 VPN on/off、DNS server、MTU、TLS 握手失败分开记录。

### 🔹 应用侧能做什么

App 不能直接控制系统 Wi-Fi 评分,但可以避免把系统切网放大成业务故障。

#### 1. 用 NetworkCallback 建一份网络状态快照

官方文档推荐用 `registerDefaultNetworkCallback()` 监听默认网络变化,并通过 `onCapabilitiesChanged()`、`onLinkPropertiesChanged()` 更新能力和链路属性。[已验证: 官方文档, https://developer.android.com/develop/connectivity/network-ops/reading-network-state]

```kotlin
class DefaultNetworkTracker(
    context: Context,
    private val onSnapshot: (NetworkSnapshot) -> Unit,
) : ConnectivityManager.NetworkCallback() {
    private val cm = context.getSystemService(ConnectivityManager::class.java)
    private var current: Network? = null

    fun start() {
        cm.registerDefaultNetworkCallback(this)
    }

    fun stop() {
        cm.unregisterNetworkCallback(this)
    }

    override fun onAvailable(network: Network) {
        current = network
        // 不在此处同步调用 getNetworkCapabilities():NetworkCallback
        // 可能在 capabilities 尚未就绪时就触发 onAvailable。
        // 等待随后的 onCapabilitiesChanged(network, caps) 携带能力快照再发布。
    }

    override fun onCapabilitiesChanged(network: Network, caps: NetworkCapabilities) {
        if (network == current) publish(network, caps)
    }

    override fun onLost(network: Network) {
        if (network == current) {
            current = null
            onSnapshot(NetworkSnapshot.offline())
        }
    }

    private fun publish(network: Network, caps: NetworkCapabilities) {
        onSnapshot(
            NetworkSnapshot(
                networkId = network.toString(),
                wifi = caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI),
                cellular = caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR),
                vpn = caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN),
                internet = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET),
                validated = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED),
                unmetered = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED),
            )
        )
    }
}

data class NetworkSnapshot(
    val networkId: String,
    val wifi: Boolean,
    val cellular: Boolean,
    val vpn: Boolean,
    val internet: Boolean,
    val validated: Boolean,
    val unmetered: Boolean,
) {
    companion object {
        fun offline() = NetworkSnapshot("none", false, false, false, false, false, false)
    }
}
```

这段只依赖公开 API。不要用隐藏 Wi-Fi 分数做业务决策;线上 SDK 也不应该要求普通 App 权限去读系统 Wi-Fi 内部状态。

#### 2. 把失败隔离放在连接层附近

网络切换时,失败通常会集中在 DNS、TCP、TLS 和连接池复用边界。处理原则:

- DNS 失败:HTTPDNS 缓存要有 TTL、系统 DNS 兜底、空结果保护和失败 IP 短期隔离。详见 24.4。
- 连接失败:保留多 IP 候选,让 OkHttp 的 fast fallback 或 route retry 有选择空间。不要把 HTTPDNS 返回值压成单 IP。
- TLS 失败:不要把 IP URL 直接替换 HTTPS hostname,否则 SNI 和证书校验会出问题。详见 12.4。
- 连接池复用失败:切网后旧连接可能还在池里。对长连接、WebSocket、HTTP/2 multiplexing 要记录 network 变化后的重连策略。

[结构参考: Clippings/Android 性能优化 - 缓存优化:冷热端分离+重排序,提升缓存命中率.md] 参考其"缓存命中率必须可监控、淘汰策略要服务场景"的组织方式。网络侧对应到 DNS / HTTPDNS / 连接池缓存:命中率、失败率、TTL 和隔离策略要能被观测。

#### 3. 弱网降级按请求类型分层

| 请求类型 | 弱网处理 | 不建议做的事 |
|---|---|---|
| 首屏关键接口 | 短 connect timeout、缓存兜底、一次受控重试 | 无限等待或多 client 并发打同一接口 |
| 图片 / 列表资源 | 降低清晰度、分页、延后预加载 | 和首屏 API 抢同一批并发槽 |
| 埋点 / 日志 | 批量、压缩、按网络恢复发送 | 在 `onLost` 后继续密集重试 |
| 文件上传 | 断点续传、只在 validated + 合适网络下恢复 | 默认 Wi-Fi 就开始大流量上传 |
| 支付 / 下单 | 服务端幂等键、明确超时反馈 | 客户端自行无条件重发 POST |

[结构参考: Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 19.md] 参考其把弱网、DNS、QUIC 和大网络平台拆开排查的结构,不复用原文案例。

### 🔹 系统侧证据采集

单靠 App 日志很难判断"系统切网"还是"业务服务慢"。现场证据建议按下面顺序收。

#### dumpsys connectivity

关注默认网络、NetworkAgent、NetworkCapabilities、LinkProperties、validation 状态和 network request 满足关系。

```bash
adb shell dumpsys connectivity > connectivity.txt
```

检查点:

- 默认网络的 `NetworkCapabilities` 是否同时有 `INTERNET` 和 `VALIDATED`。
- 当前默认网络是否是 `TRANSPORT_WIFI`、`TRANSPORT_CELLULAR` 或 `TRANSPORT_VPN`。
- `LinkProperties` 中 DNS server、proxy、MTU 是否异常。
- 是否存在旧 Wi-Fi 和新蜂窝同时满足 default request 的过渡期。

#### dumpsys wifi

```bash
adb shell dumpsys wifi > wifi.txt
```

检查点:

- 当前连接 BSSID、频段、RSSI、link speed、score / usability 相关输出。
- 最近扫描结果里目标 BSSID 是否因 RSSI、blocklist、连接失败被过滤。
- 是否有 PNO、roam、disconnect reason、association reject、DHCP failure。
- OEM overlay 是否改变 entry RSSI threshold 或漫游策略。[待验证: 具体字段名随 Android 版本和厂商实现变化]

#### bugreport

```bash
adb bugreport bugreport-wifi-switch.zip
```

bugreport 适合复盘系统决策。它能同时包含 connectivity、wifi、netd、NetworkStack、系统日志和部分配置。线上复现难的切网问题,至少保留问题发生前后 2 分钟的时间戳、网络状态快照和请求 call id,后续才能把 App 日志和系统日志关联起来。

#### Perfetto

Perfetto 侧可重点打开这些数据:

- `linux.ftrace` 的 `sched/sched_switch`、`power/cpu_frequency`:确认网络回调或业务回调是否拖住主线程。
- `android.log`:抓 `ConnectivityService`、`NetworkMonitor`、`WifiNetworkSelector`、`WifiConnectivityManager`、`WifiNetworkAgent`、`netd` 相关 logcat。
- 自定义 trace event:App 在 `onAvailable`、`onCapabilitiesChanged`、`dnsStart`、`connectStart`、`responseHeadersStart` 打点。
- network counters:如果设备和 trace 配置支持,可观察 UID 维度收发流量变化。[待验证: counter 可用性与设备内核 / Perfetto 配置有关]

建议把 App 的请求 call id、network id 和 trace event 放在同一个字段体系里。否则 trace 里能看到网络切换,App 日志里能看到超时,但两边很难证明是同一轮问题。

## 扩展

### 🔸 OEM Wi-Fi 评分差异

AOSP 的 Connectivity 网络选择策略被 Mainline 模块约束，但 OEM 仍然可以通过 overlay、Wi-Fi HAL / firmware、漫游阈值、双 Wi-Fi、链路聚合、厂商加速 SDK 改变体验。另外，Android 框架也预留了评分扩展点：`WifiConnectedNetworkScorer` 作为 AOSP 内置的 external scorer 实现，接收已连接 Wi-Fi 的属性（RSSI、link speed、频段、是否 validated、是否 metered）并计算出外部分数，供 ConnectivityService 在选择默认网络时参考。[已验证: AOSP main, packages/modules/Wifi/service/java/com/android/server/wifi/WifiConnectedNetworkScorer.java]

工程判断要分三层：

| 层级 | 可验证材料 | 判断边界 |
|---|---|---|
| AOSP framework | `WifiNetworkSelector`、`WifiCandidates`、`NetworkRanker`、`NetworkMonitor` | 可作为通用 Android 机制 |
| OEM 配置 | `dumpsys wifi`、overlay、vendor log、机型实验 | 只能覆盖该厂商 / 该版本 |
| firmware / driver | 厂商 bugreport、内核日志、芯片文档 | 没有材料时只能标 `[待验证]` |

不要把"评分多少会切蜂窝"写成固定结论。AOSP main 已经能确认筛选维度和 Connectivity 排序策略,但具体机型上的漫游、MLO、双 Wi-Fi、链路聚合阈值,需要实机 trace 或厂商材料。[待验证: OEM scoring、roaming threshold、dual Wi-Fi / link aggregation 策略]

如果要排查厂商差异,可以做一组最小实验:同一地点、同一 SSID、同一业务请求,分别记录 Pixel / 目标厂商机型在 RSSI 从 -55dBm 降到 -80dBm 时的 default network、validated 状态、DNS/TTFB 分位数、切换次数和电量曲线。没有这组数据,不要把单机观察写成平台规律。

### 🔸 HTTP/3、QUIC 与网络切换

HTTP/3 / QUIC 对移动网络切换更友好,但不是免疫切网。它的优势来自连接 ID、用户态拥塞控制和更少的握手往返;能不能迁移,还取决于服务端、客户端库、NAT、运营商网络、连接迁移配置和安全策略。

App 侧可以把 HTTP/3 作为灰度能力处理:

- 按域名、地区、网络类型开关 HTTP/3,保留 HTTP/2 回退。
- 记录 QUIC handshake、0-RTT、migration attempt、fallback reason、HTTP/2 fallback TTFB。
- 切网前后单独统计长连接恢复时长,不把 HTTP/3 和 HTTP/2 的指标混在一个分位数里。
- 对支付、下单、上传这类请求保留幂等设计,不能把协议迁移当成业务一致性的替代品。

协议细节详见 24.5;这里保留 App 网络切换视角的观测口径。

## 工程检查清单

- 是否用 `registerDefaultNetworkCallback()` 记录默认网络变化,而不是只读一次 `activeNetwork`?
- 是否同时判断 `NET_CAPABILITY_INTERNET` 和 `NET_CAPABILITY_VALIDATED`?
- 是否用 `NET_CAPABILITY_NOT_METERED` 决定大下载 / 上传时机,而不是直接判断 Wi-Fi?
- OkHttp EventListener 是否采集 DNS、TCP、TLS、TTFB、body download 和失败类型?
- 切网时是否记录 network id、transport、VPN、validated、DNS server、proxy、MTU?
- HTTPDNS 是否避免在 `Dns.lookup()` 内实时发阻塞请求?详见 24.4。
- 是否把首屏 API、图片、埋点、上传放进不同优先级队列,避免弱网互相挤占?
- bugreport / Perfetto 是否能用 call id 关联系统网络事件和 App 请求事件?

## 参考资料

- [已验证: 官方文档, https://source.android.com/docs/core/connect/wifi-network-selection]
- [已验证: 官方文档, https://source.android.com/docs/core/connect/network-selection]
- [已验证: 官方文档, https://developer.android.com/develop/connectivity/network-ops/reading-network-state]
- [已验证: 官方文档, https://developer.android.com/reference/android/net/NetworkCapabilities]
- [已验证: 官方文档, https://square.github.io/okhttp/features/events/]
- [已验证: AOSP main, packages/modules/Wifi/service/java/com/android/server/wifi/WifiNetworkSelector.java]
- [已验证: AOSP main, packages/modules/Wifi/service/java/com/android/server/wifi/WifiCandidates.java]
- [已验证: AOSP main, packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkRanker.java]
- [已验证: AOSP main, packages/modules/Connectivity/service/src/com/android/server/connectivity/FullScore.java]
- [已验证: AOSP main, packages/modules/NetworkStack/src/com/android/server/connectivity/NetworkMonitor.java]
- [结构参考: Clippings/Android 性能优化 - 原理:重新认识应用的速度优化.md]
- [结构参考: Clippings/Android 性能优化 - CPU 优化(下):减少 CPU 闲置时刻和等待,提升利用率.md]
- [结构参考: Clippings/Android 性能优化 - 缓存优化:冷热端分离+重排序,提升缓存命中率.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 18.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 19.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 20.md]
