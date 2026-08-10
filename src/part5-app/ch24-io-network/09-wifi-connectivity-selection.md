---
title: "Wi-Fi 评分、网络选择与连接切换性能"
chapter: "24.9"
section: "24.9"
status: finalized
drafted_date: "2026-05-15"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: '2026-06-04'
last_verified_against: 'AOSP android-16.0.0_r1 (packages/modules/Wifi, packages/modules/Connectivity, packages/modules/NetworkStack) + Android Developers / source.android.com docs'
confidence: medium
sources:
  - type: aosp
    path: "packages/modules/Wifi/service/java/com/android/server/wifi/WifiNetworkSelector.java"
  - type: aosp
    path: "packages/modules/Wifi/service/java/com/android/server/wifi/WifiCandidates.java"
  - type: aosp
    path: "packages/modules/Wifi/framework/java/android/net/wifi/WifiManager.java"
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
reviewed_date: "2026-06-04"
task6_result: pass-light-edit
task6_state: "reviewed"
last_task6_at: "2026-06-04T03:10:02+08:00"
task6_review_notes: "2026-06-04 Task6 revisiting review: pass-light-edit（revisit）。L1/L2 禁用词/高频词/AI填充词零命中。无新增回炉项。task9_result=auto-fixed 未达 pass-tech-review 口径，不自动晋升，待 task9 复审。"
task9_state: "reviewed"
task9_result: 'auto-fixed'
task2b_state: 'fixed'
task9_reviewed_by: 'openclaw-task9'
task9_reviewed_date: '2026-06-04'
last_task9_at: '2026-06-04T00:20:00+08:00'
last_task9_review_log: 'logs/deep-review/2026-06-04-00-deep-review.md'
task2b_result: 'fixed'
task2b_fixed_date: '2026-06-03'
task2b_fixed_at: '2026-06-03T10:53:52'
last_task2b_at: '2026-06-03T10:53:52'
last_task9_autofix_at: '2026-06-04'
task9_review_notes: '2026-06-04 Task9 00:20：auto-fixed。将 Wi-Fi / Connectivity 源码锚点收敛到 android-16.0.0_r1，并修正 WifiConnectedNetworkScorer 的真实源码位置为 WifiManager 嵌套 SystemApi；回到 Task6 复审。'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-04
task6_l1_l2_fixes: 0
pipeline_stage: ready-to-publish
---

# 24.9 Wi-Fi 评分、网络选择与连接切换性能

平台源码锚点是 Android 17（API 37）/ `android-17.0.0_r1`。应用看到默认网络可用之前，系统至少完成了两类决策：Wi-Fi 模块在可连接的 AP 中选择网络，Connectivity 模块在 Wi-Fi、蜂窝、以太网、VPN 等并存网络中为每个请求选择满足者。两类决策使用不同的输入，不能合并成一个“网络分数”。

Wi-Fi 图标、RSSI、`NET_CAPABILITY_VALIDATED` 和业务接口成功分别描述无线关联、链路信号、系统公网探测和目标服务可达性。它们可以同时出现不同结果。排查连接切换时，要把系统选择事件、HTTP 交换和业务恢复分开记录。连接池、TLS 与 HTTP 协议细节见 12.2、12.3、24.4 和 24.5。

## 要点

### 🔹 ConnectivityService 与 Wi-Fi 模块分工

下面的路径只描述主要控制关系，不代表每次扫描都会触发重选或重新关联：

```text
Wi-Fi 扫描结果
  → WifiNetworkSelector 判断当前连接是否足够好
  → 过滤不合格的非当前 BSSID
  → NetworkNominator 生成候选网络
  → ThroughputScorer 对候选网络和 BSSID 评分
  → WifiNetworkAgent 把已连接网络作为 NetworkAgent 上报
  → ConnectivityService 为 NetworkRequest 筛出满足能力的 NetworkAgent
  → NetworkRanker 按策略选择当前满足者
  → App 通过 ConnectivityManager 观察默认网络变化
```

Wi-Fi 模块主要回答“连接哪个 Wi-Fi 网络或 BSSID”。Connectivity 模块回答“哪个 `Network` 满足某个 `NetworkRequest`”。默认网络只是系统请求中的一类；VPN 还可能让不同 UID 看到不同的应用默认网络。

Android 17 的 `WifiNetworkSelector.filterScanResults()` 会排除低于入网 RSSI 阈值、命中 BSSID 阻止列表、被 MBO/OCE 拒绝关联、不满足设备管理策略或使用已弃用安全类型的结果。已连接的当前 BSSID 会在这些普通过滤条件之前保留；当前 BSSID 未出现在一次扫描中时，源码还可能放弃本轮选择，避免由不完整扫描触发激进切换。

`getCandidatesFromScan()` 让已注册的 nominator 产生保存网络、Suggestion 网络等候选，并保留当前连接作为候选。`selectNetwork()` 通过活动的 `CandidateScorer` 选择结果，再应用用户连接选择兼容逻辑。Android 17 的预设 scorer 是 `ThroughputScorer`。

Connectivity 先保留能满足请求能力的网络，再执行 `NetworkRanker.getBestNetworkByPolicy()`。Android 17 的主要规则按源码顺序如下：

| 顺序 | 优先保留的候选 | 说明 |
| --- | --- | --- |
| 1 | `POLICY_IS_INVINCIBLE` | 系统内部不可被普通候选替代的网络 |
| 2 | 已连接 VPN | 应用默认网络可能是 VPN，物理承载网络位于其下层 |
| 3 | 用户选择且接受未验证 | 保留用户明确接受的无互联网网络 |
| 4 | 已验证或允许未验证 | 同时处理蜂窝向“较差 Wi-Fi”让路的策略 |
| 5 | 未进入退出状态 | 避开即将断开的网络 |
| 6 | 同传输类型中的 primary | 例如双 SIM 的主数据网络 |
| 7 | 传输类型偏好 | 源码顺序为以太网、Wi-Fi、蓝牙、蜂窝 |
| 8 | VCN、未销毁网络、当前满足者 | 处理等价候选并减少无意义切换 |

这里的验证状态、VPN 和销毁状态来自 Connectivity 生成的 `FullScore`；`POLICY_TRANSPORT_PRIMARY`、`POLICY_EXITING` 等属性由 `NetworkScore` 表达。Android 17 的通用排序代码没有实现“所有网络一律未计费优先”，源码在该位置仍保留 TODO。`NET_CAPABILITY_NOT_METERED` 可以决定一个带该能力要求的请求能否被满足，Wi-Fi 候选评分也会奖励未计费网络，但这两件事不能外推为所有默认网络的统一排序公式。

版本演进需要保留：

| 版本 | Connectivity 选择机制 | 边界 |
| --- | --- | --- |
| Android 10 / 11（API 29–30） | NetworkAgent 整数分数，加上验证状态、VPN 等奖励或惩罚 | 同分行为未定义 |
| Android 12–17（API 31–37） | `NetworkScore` 与 `FullScore` 策略，由 `NetworkRanker` 逐项筛选 | 旧整数只用于日志和兼容观测，不再参与网络间排序 |

Wi-Fi RSSI 下降后，应用不一定马上收到默认网络变化。当前 Wi-Fi 仍可能被判定足够好；候选连接和验证也需要时间；策略等价时，`NetworkRanker` 还会保留当前满足者。

### 🔹 Wi-Fi 评分输入

#### 当前连接是否需要重选

Android 17 的 `WifiNetworkSelector.isNetworkSufficient()` 依次检查连接状态、用户近期选择、OSU、外部 scorer 给出的可用性、连接分数、OEM paid/private、计费属性、历史无互联网状态、IP 配置以及链路质量。只有 RSSI 不足且收发流量也不活跃时，末项才判为不足。

这段逻辑使用 Wi-Fi 子系统内部状态和可覆盖资源，不能由普通应用用 RSSI 复刻。官方 Wi-Fi network selection 页面主要描述 Android 12 行为，并明确提示 AOSP 源码才是后续版本的最终依据。

#### 候选如何评分

Android 17 的 `WifiCandidates.Candidate` 和 `ThroughputScorer` 可确认以下输入：

| 输入 | 系统侧含义 | App 侧判断方式 |
| --- | --- | --- |
| RSSI、频率和信道宽度 | 参与 RSSI 分和频段奖励 | 信号格数不能替代吞吐、时延和丢包观测 |
| 单链路预测吞吐 | 由制式、信道、RSSI、空间流等估算 | 它是系统估算，不是业务下载测速 |
| MLO 能力与多链路预测吞吐 | Android 17 在多链路预测值更高时采用该值 | 只在设备、AP 与协商结果均支持时出现 |
| 当前网络 | 得到可配置的 current-network bonus | 可解释边缘信号下为何暂不切换 |
| 保存、Suggestion、可信与安全属性 | 决定候选所在的优先级区间 | 应用不能读取最终内部评分 |
| 计费属性 | Wi-Fi 候选 scorer 可奖励未计费网络 | 业务仍以 `NET_CAPABILITY_NOT_METERED` 判断 |
| 历史无互联网、IP 配置超时 | 降低或清除部分奖励 | 与当前 `VALIDATED` 回调不是同一个数据口径 |
| 近期用户选择 | 在配置窗口内获得显著奖励 | 保护时间与强度可被设备配置改变 |

`ScoringParams` 和资源 overlay 控制入网阈值、足够 RSSI、吞吐奖励和多个优先级参数。旧资料中的固定阈值只能说明某个版本的 AOSP 默认配置，不能作为跨版本、跨厂商的发布条件。

### 🔹 连接切换的性能指标

普通应用看不到 `NetworkRanker` 开始决策的时刻，因此不能从公开回调直接计算“系统选网耗时”。可以稳定观测的是默认网络通知、能力变化、HTTP 事件和业务恢复：

| 指标 | 起点 | 终点 | 适合回答的问题 |
| --- | --- | --- | --- |
| 新默认网络通知 | `onAvailable(new)` | 紧随其后的 `onCapabilitiesChanged(new)` | 应用收到选择结果后，能力快照何时到达 |
| 验证状态变化 | 新网络第一次能力快照 | 同一网络取得或失去 `VALIDATED` | 系统公网探测状态如何变化 |
| 异步排队 | `dispatcherQueueStart` | `dispatcherQueueEnd` | OkHttp 异步 Dispatcher 是否排队 |
| DNS、TCP、TLS | 每组对应的 start | 同组 end 或 failed | 新解析、路由尝试和握手发生在哪一段 |
| 响应头等待 | 同一次交换的请求结束事件 | `responseHeadersStart` | 上传、网络往返、网关和服务端共同等待 |
| 业务恢复 | 业务操作进入等待或失败 | 首次满足业务语义的成功结果 | 用户可感知的中断时间 |

`onLost(old)` 不能作为默认网络切换起点。对 default callback 而言，`onAvailable(new)` 表示新的最佳网络已经由该回调跟踪；回调随后不再接收旧网络的事件。只有当前跟踪的默认网络丢失且没有替代网络时，才应把 `onLost()` 解释为应用失去默认网络。

OkHttp 5.3.0 的事件序列也不能压成每个名称一个时间戳。重试、重定向和认证会在同一个 `Call` 中产生多组 DNS、连接、请求和响应事件；复用连接时不会产生 DNS 与 connect 事件；双工请求还可能交错。

下面的监听器保留原始单调时钟时间线，让离线分析按事件顺序识别多次交换。`defaultGeneration` 是应用默认网络观察序号，只用于关联切网窗口：

```kotlin
data class CallMark(
    val name: String,
    val elapsedNanos: Long,
)

data class CallTimeline(
    val callId: Long,
    val defaultGenerationAtStart: Long?,
    val terminal: String,
    val marks: List<CallMark>,
)

class TimelineEventListener(
    private val callId: Long,
    private val defaultGeneration: () -> Long?,
    private val report: (CallTimeline) -> Unit,
) : EventListener() {
    private val marks = mutableListOf<CallMark>()
    private var generationAtStart: Long? = null
    private var reported = false

    @Synchronized
    private fun mark(name: String) {
        marks += CallMark(name, SystemClock.elapsedRealtimeNanos())
    }

    override fun callStart(call: Call) {
        generationAtStart = defaultGeneration()
        mark("callStart")
    }

    override fun dispatcherQueueStart(call: Call) = mark("dispatcherQueueStart")

    override fun dispatcherQueueEnd(call: Call) = mark("dispatcherQueueEnd")

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

    override fun connectionAcquired(call: Call, connection: Connection) {
        mark("connectionAcquired")
    }

    override fun requestHeadersEnd(call: Call, request: Request) {
        mark("requestHeadersEnd")
    }

    override fun requestBodyEnd(call: Call, byteCount: Long) {
        mark("requestBodyEnd")
    }

    override fun responseHeadersStart(call: Call) {
        mark("responseHeadersStart")
    }

    override fun responseBodyEnd(call: Call, byteCount: Long) {
        mark("responseBodyEnd")
    }

    override fun callEnd(call: Call) {
        finish("callEnd")
    }

    override fun callFailed(call: Call, ioe: IOException) {
        finish("callFailed:${ioe.javaClass.name}")
    }

    private fun finish(terminal: String) {
        val timeline = synchronized(this) {
            if (reported) return
            marks += CallMark(terminal, SystemClock.elapsedRealtimeNanos())
            reported = true
            CallTimeline(
                callId = callId,
                defaultGenerationAtStart = generationAtStart,
                terminal = terminal,
                marks = marks.toList(),
            )
        }
        report(timeline)
    }
}
```

监听器应由 `EventListener.Factory` 为每个 `Call` 单独创建。分析端按完整事件序列识别交换，不能把末次 `dnsEnd` 与第一次 `dnsStart` 相减。`defaultGenerationAtStart` 也不能证明连接使用了该网络：复用连接可能建立在更早的默认网络上，显式绑定的客户端还可能使用其他 `Network`。需要证明套接字路径时，必须结合绑定配置、系统 trace 或抓包。

### 🔹 弱网与多网络并存场景

能力字段只提供分层证据：

| 能力或传输 | 表示什么 | 不表示什么 |
| --- | --- | --- |
| `NET_CAPABILITY_INTERNET` | 网络配置为可访问互联网 | 已经通过公网探测 |
| `NET_CAPABILITY_VALIDATED` | 系统探测确认公网可达 | 业务域名、账号和服务端一定可用 |
| `NET_CAPABILITY_CAPTIVE_PORTAL` | 系统探测识别到登录门户 | 所有 HTTP 请求都会失败 |
| `NET_CAPABILITY_NOT_METERED` | 系统认为用户不敏感于该网络的数据消耗 | 传输类型必定是 Wi-Fi |
| `TRANSPORT_VPN` | 应用默认网络经过 VPN | 物理承载只有一种；VPN 网络可同时带有 Wi-Fi 或蜂窝传输 |

Android 17 的 `NetworkMonitor` 会在目标 `Network` 上执行 DNS 与 HTTP/HTTPS 探测，并根据成功、门户、部分连接等结果更新 Connectivity。探测 URL、代理、Private DNS 与设备配置都可能影响结果。因此：

- 没有应用默认网络时，普通默认绑定请求无法新建连接；显式请求的其他网络要单独判断。
- 有 `INTERNET` 但没有 `VALIDATED` 时，可展示离线数据并降低后台重试，不应把所有用户操作永久禁用。
- 有 `CAPTIVE_PORTAL` 时，可引导用户完成系统登录流程。
- 已有 `VALIDATED` 时，业务请求仍需处理 DNS、路由、TLS、服务端和账号错误。
- VPN 的传输集合会随承载网络改变；诊断时同时记录 VPN、Wi-Fi 与蜂窝标记。

网络能力会动态变化，单次 `activeNetwork` 查询只能作为瞬时诊断。长期状态应来自回调。

### 🔹 应用侧能做什么

普通应用不能读取或控制系统 Wi-Fi 最终评分。应用能做的是保留有序的网络事件，并按请求语义处理失败。

#### 1. 用 NetworkCallback 建一份网络状态快照

`registerDefaultNetworkCallback()` 需要 `ACCESS_NETWORK_STATE`。Android 8.0（API 26）起，新默认网络的 `onAvailable()` 后会立即按序收到 `onCapabilitiesChanged()` 和 `onLinkPropertiesChanged()`。回调中不要同步调用 `getNetworkCapabilities()` 或 `getLinkProperties()`，这些查询可能返回过期值或 `null`。

下面的追踪器把回调放到调用方提供的 Handler，并为每次新默认网络分配递增序号：

```kotlin
sealed interface DefaultNetworkEvent {
    data class Selected(
        val generation: Long,
        val networkId: String,
        val elapsedNanos: Long,
    ) : DefaultNetworkEvent

    data class Capabilities(
        val generation: Long,
        val networkId: String,
        val wifi: Boolean,
        val cellular: Boolean,
        val vpn: Boolean,
        val internet: Boolean,
        val validated: Boolean,
        val captivePortal: Boolean,
        val notMetered: Boolean,
        val downstreamKbpsEstimate: Int,
        val elapsedNanos: Long,
    ) : DefaultNetworkEvent

    data class Blocked(
        val generation: Long,
        val blocked: Boolean,
        val elapsedNanos: Long,
    ) : DefaultNetworkEvent

    data class Lost(
        val generation: Long,
        val elapsedNanos: Long,
    ) : DefaultNetworkEvent
}

class DefaultNetworkTracker(
    context: Context,
    private val callbackHandler: Handler,
    private val onEvent: (DefaultNetworkEvent) -> Unit,
) : ConnectivityManager.NetworkCallback() {
    private val cm = context.getSystemService(ConnectivityManager::class.java)
    private var current: Network? = null
    private var nextGeneration = 0L

    @Volatile
    var currentGeneration: Long? = null
        private set

    fun start() {
        cm.registerDefaultNetworkCallback(this, callbackHandler)
    }

    fun stop() {
        cm.unregisterNetworkCallback(this)
    }

    override fun onAvailable(network: Network) {
        current = network
        val generation = ++nextGeneration
        currentGeneration = generation
        onEvent(
            DefaultNetworkEvent.Selected(
                generation,
                network.toString(),
                SystemClock.elapsedRealtimeNanos(),
            )
        )
    }

    override fun onCapabilitiesChanged(network: Network, caps: NetworkCapabilities) {
        if (network != current) return
        val generation = currentGeneration ?: return
        onEvent(
            DefaultNetworkEvent.Capabilities(
                generation = generation,
                networkId = network.toString(),
                wifi = caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI),
                cellular = caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR),
                vpn = caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN),
                internet = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET),
                validated = caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED),
                captivePortal = caps.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL
                ),
                notMetered = caps.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_NOT_METERED
                ),
                downstreamKbpsEstimate = caps.linkDownstreamBandwidthKbps,
                elapsedNanos = SystemClock.elapsedRealtimeNanos(),
            )
        )
    }

    override fun onBlockedStatusChanged(network: Network, blocked: Boolean) {
        if (network != current) return
        val generation = currentGeneration ?: return
        onEvent(
            DefaultNetworkEvent.Blocked(
                generation,
                blocked,
                SystemClock.elapsedRealtimeNanos(),
            )
        )
    }

    override fun onLost(network: Network) {
        if (network != current) return
        val generation = currentGeneration ?: return
        current = null
        currentGeneration = null
        onEvent(
            DefaultNetworkEvent.Lost(
                generation,
                SystemClock.elapsedRealtimeNanos(),
            )
        )
    }
}
```

`network.toString()` 只适合在同一次设备运行中关联事件，不能当成跨重启稳定标识。`linkDownstreamBandwidthKbps` 是系统估计值，也不能替代应用吞吐测量。`onEvent` 应快速入队；数据库写入、上传等较长工作转交其他线程。追踪器还要与进程级生命周期绑定并确保只注册一次，避免耗尽每 UID 的回调额度。

#### 2. 把失败隔离放在连接层附近

官方文档说明，新连接在默认网络变化后使用新网络，旧默认网络上的既有连接稍后会被系统终止。应用不需要在每次 `onAvailable()` 时销毁共享 `OkHttpClient` 或清空整个连接池，这会同时破坏仍可复用的健康连接。

- DNS 返回多个地址时保留候选，让 OkHttp 的路由重试与 `fast fallback`（快速备用连接）有选择空间。
- HTTPS URL 始终保留原主机名；把 URL 改成 IP 会破坏 SNI、证书校验和虚拟主机路由。
- GET 等可安全重试的操作由网络库按配置恢复；POST、支付和提交操作需要幂等键或查询结果接口。
- WebSocket、流式响应和上传任务保存应用层进度，在终端失败后按协议重连。
- 后台可延后任务使用 WorkManager 的网络约束，避免常驻监听器自行轮询。

显式绑定其他网络属于少数高级场景，申请后台网络还涉及 `CHANGE_NETWORK_STATE` 权限。获取目标 `Network` 后，要同时使用 `network.socketFactory` 与 `network.getAllByName()`，否则套接字和 DNS 可能走不同网络。目标网络丢失后，应取消相关请求；若需要独立清理连接，该绑定客户端应使用专用连接池。大多数应用应继续使用系统默认网络。

#### 3. 弱网降级按请求类型分层

| 请求类型 | 弱网处理 | 不建议做的事 |
| --- | --- | --- |
| 首屏读取 | 本地数据、分阶段加载、按错误类型重试 | 并发复制同一个请求 |
| 图片与列表资源 | 分页、调整资源质量、延后预取 | 与交互接口争用全部异步额度 |
| 遥测与日志 | 批量、压缩、持久队列 | 网络变化时集中重发 |
| 文件传输 | 断点、校验、持久任务状态 | 仅凭 `TRANSPORT_WIFI` 启动大流量任务 |
| 支付与提交 | 服务端幂等键、结果查询、明确未知状态 | 连接异常后无条件重发 |

超时、并发、重试次数和恢复窗口来自项目基线与服务端契约，不存在跨业务通用数值。

### 🔹 系统侧证据采集

应用日志只能证明应用观察到了什么，不能单独证明系统为何选择某个网络。可复现设备上应同时采集 Connectivity、Wi-Fi 与请求时间线。

#### dumpsys connectivity

下面的命令保存 ConnectivityService 当前状态：

```bash
adb shell dumpsys connectivity > connectivity.txt
```

输出用于检查 NetworkAgent、能力、链路属性、验证状态和请求满足关系。系统默认网络不一定等于受 VPN 策略影响后的某个应用默认网络，判断时要结合目标 UID。

检查以下信息：

- 候选 NetworkAgent 是否满足目标请求；
- `INTERNET`、`VALIDATED`、`CAPTIVE_PORTAL`、`NOT_METERED` 与传输集合；
- `LinkProperties` 中的 DNS、代理、路由、接口和 MTU；
- VPN 与底层物理网络是否同时存在；
- 请求与网络的满足关系是否在问题窗口发生变化。

#### dumpsys wifi

下面的命令保存 Wi-Fi 服务状态：

```bash
adb shell dumpsys wifi > wifi.txt
```

不同版本和厂商会改变输出字段，不能让解析脚本依赖一段固定文本。人工复核时关注：

- 当前网络、BSSID、频段、RSSI、链路速率与 usability；
- 候选与过滤原因，包括低 RSSI、阻止列表、管理策略和关联拒绝；
- roam、断开原因、认证、关联和 IP 配置失败；
- PNO、MLO、双 STA、外部 scorer 与设备 overlay；
- 时间戳是否能与应用的网络 generation 和请求编号对齐。

#### bugreport

难以稳定复现的问题使用 bugreport 保存跨服务现场：

```bash
adb bugreport bugreport-wifi-switch.zip
```

bugreport 可包含 Connectivity、Wi-Fi、netd、NetworkStack、系统日志和设备配置。采集时记录操作步骤、单调时钟时间、应用请求编号和预期结果。文件可能含网络标识、地址与用户数据，应限制访问并按隐私策略删除。

#### Perfetto

Perfetto 适合判断网络回调之后是否又被线程调度、主线程工作或存储 I/O 延迟：

- 调度事件用于检查回调线程、网络线程和主线程是否长期不可运行；
- `android.log` 数据源在设备允许时保存 Connectivity、NetworkMonitor、Wi-Fi 与 netd 日志；
- 应用 trace event 标记 `onAvailable`、能力变化、OkHttp 事件和业务恢复；
- 流量字节使用应用或系统已有的、已验证过口径的统计源，不假设任意设备都提供某个 Perfetto 网络计数器。

应用事件、系统 trace 与服务端日志至少共享请求编号和时间基准。没有这层关联，只能得到“切网和超时在相近时间发生”，不能确认因果。

## 扩展

### 🔸 OEM Wi-Fi 评分差异

AOSP 的 Connectivity 选择逻辑位于 Mainline 模块。设备厂商通过 `NetworkScore` 属性表达网络策略，同时还能通过 Wi-Fi 资源 overlay、HAL、固件、驱动、漫游策略、双 STA 和厂商服务改变 Wi-Fi 行为。

`WifiManager.WifiConnectedNetworkScorer` 是 `@SystemApi`，并要求 `WIFI_UPDATE_USABILITY_STATS_SCORE` 权限，普通第三方应用不能把它当成公开扩展点。Android 17 的 `ScoreUpdateObserver` 对各回传值给出了清楚边界：

- `notifyScoreUpdate()` 的数值只用于 Wi-Fi 指标采集，不直接驱动网络选择；
- `notifyStatusUpdate()` 可报告当前连接是否可用；
- `requestNudOperation()` 请求邻居可达性检测；
- `blocklistCurrentBssid()` 建议暂时阻止当前 BSSID；
- 受功能标志控制的 `setPreEvaluationEnabled()` 可让下一次连接先进入受限预评估，再决定是否向其他应用开放。

外部 scorer 的输入可来自 `WifiUsabilityStatsEntry`，包括 RSSI、链路速率、频率和分组统计。接口存在不代表所有设备都安装了外部 scorer，也不代表设备启用了 Android 17 源码中的受标志控制行为。

工程判断要分三层：

| 层级 | 可验证材料 | 判断边界 |
| --- | --- | --- |
| AOSP framework | `WifiNetworkSelector`、`ThroughputScorer`、`NetworkRanker`、`NetworkMonitor` | 说明 Android 17 通用机制 |
| 设备配置 | overlay、功能标志、`dumpsys wifi`、厂商日志 | 结论限于该构建与配置 |
| 固件和驱动 | 厂商 bugreport、内核日志、芯片资料、射频实验 | 缺少材料时不推断具体阈值 |

跨机型实验应固定 AP、频段、信道、业务请求、服务端和干扰条件，使用可控衰减逐步改变信号，并同时记录默认网络 generation、能力、候选原因、HTTP 时间线、切换次数和功耗。单台设备的一次观察不能成为平台规律。

### 🔸 HTTP/3、QUIC 与网络切换

前面的 `EventListener` 以 OkHttp 5.3.0 为样本。OkHttp 自身支持 HTTP/1.1 与 HTTP/2，不提供 HTTP/3。需要 HTTP/3 over QUIC 时，应评估 Android `HttpEngine` 或 Cronet，也可以评估以 Cronet 作为 OkHttp 传输层的官方集成。

QUIC 的连接 ID 为迁移提供了协议基础，但迁移不会凭 HTTP/3 自动发生。`HttpEngine` 和 Cronet 都提供连接迁移选项；只有启用默认网络迁移、请求使用 QUIC 且服务端支持迁移时，活动连接才有机会迁到新默认网络。允许迁往非默认网络还可能消耗计费流量。

HTTP/3 灰度至少分开记录：

- 实际协商协议与网络 generation；
- QUIC 建连、迁移尝试、迁移结果和回退原因；
- HTTP/3 与 HTTP/2 各自的请求分布和失败分类；
- 切网前后的长连接恢复；
- 非默认计费网络的使用情况。

支付、下单和上传仍需幂等与恢复协议。连接迁移只能改变传输连续性，不能提供业务一致性。协议细节见 24.5。

## 工程检查清单

- 默认网络由 `registerDefaultNetworkCallback()` 持续观测，回调与进程生命周期一致。
- `INTERNET`、`VALIDATED`、`CAPTIVE_PORTAL`、`NOT_METERED` 和传输集合分别记录。
- 新默认网络用 `onAvailable()` 识别，没有等待旧网络 `onLost()`。
- OkHttp 保存完整事件序列，多次交换不会覆盖前一组时间戳。
- 请求编号、网络 generation、系统 trace 与服务端日志能够关联。
- 大文件任务依据计费能力、用户意图与持久任务状态执行。
- DNS、连接、TLS 与业务重试都保留失败分类和幂等边界。
- VPN、OEM 配置、MLO、双 STA 与 HTTP/3 结论都有对应设备证据。

## 参考与验证

- [AOSP android-17.0.0_r1 · WifiNetworkSelector.java](https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/tags/android-17.0.0_r1/service/java/com/android/server/wifi/WifiNetworkSelector.java)
- [AOSP android-17.0.0_r1 · WifiCandidates.java](https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/tags/android-17.0.0_r1/service/java/com/android/server/wifi/WifiCandidates.java)
- [AOSP android-17.0.0_r1 · ThroughputScorer.java](https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/tags/android-17.0.0_r1/service/java/com/android/server/wifi/ThroughputScorer.java)
- [AOSP android-17.0.0_r1 · ScoringParams.java](https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/tags/android-17.0.0_r1/service/java/com/android/server/wifi/ScoringParams.java)
- [AOSP android-17.0.0_r1 · WifiManager.java](https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/tags/android-17.0.0_r1/framework/java/android/net/wifi/WifiManager.java)
- [AOSP android-17.0.0_r1 · NetworkScore.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkScore.java)
- [AOSP android-17.0.0_r1 · NetworkRanker.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/connectivity/NetworkRanker.java)
- [AOSP android-17.0.0_r1 · FullScore.java](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/connectivity/FullScore.java)
- [AOSP android-17.0.0_r1 · NetworkMonitor.java](https://android.googlesource.com/platform/packages/modules/NetworkStack/+/refs/tags/android-17.0.0_r1/src/com/android/server/connectivity/NetworkMonitor.java)
- [Android Open Source Project · Wi-Fi network selection](https://source.android.com/docs/core/connect/wifi-network-selection)
- [Android Open Source Project · Network selection](https://source.android.com/docs/core/connect/network-selection)
- [Android Developers · Read network state](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Android Developers · ConnectivityManager.NetworkCallback](https://developer.android.com/reference/android/net/ConnectivityManager.NetworkCallback)
- [Android Developers · NetworkCapabilities](https://developer.android.com/reference/android/net/NetworkCapabilities)
- [Android Developers · Define work requests](https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work)
- [Android Developers · HttpEngine.Builder](https://developer.android.com/reference/android/net/http/HttpEngine.Builder)
- [Android Developers · ConnectionMigrationOptions.Builder](https://developer.android.com/reference/android/net/http/ConnectionMigrationOptions.Builder)
- [Android Developers · Network stacks](https://developer.android.com/media/media3/exoplayer/network-stacks)
- [Android Developers · Use Cronet with other libraries](https://developer.android.com/develop/connectivity/cronet/integration)
- [OkHttp · Connections](https://lysine.dev/okhttp/features/connections/)
- [OkHttp 5.3.0 · EventListener.kt](https://github.com/lysine-dev/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)
