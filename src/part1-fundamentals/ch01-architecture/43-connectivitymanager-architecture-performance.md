---
title: "Android 17 ConnectivityManager：架构、网络选择与性能"
chapter: "1.43"
section: "1.43"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1 + ACK android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "packages/modules/Connectivity/framework/src/android/net/ConnectivityManager.java"
  - type: aosp
    path: "packages/modules/Connectivity/framework/src/android/net/NetworkAgent.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/ConnectivityService.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkAgentInfo.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/connectivity/FullScore.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkRanker.java"
  - type: aosp
    path: "packages/modules/NetworkStack/src/com/android/server/connectivity/NetworkMonitor.java"
  - type: aosp
    path: "packages/modules/Connectivity/service-t/src/com/android/server/net/NetworkStatsService.java"
  - type: aosp
    path: "packages/modules/Connectivity/service-t/src/com/android/server/net/NetworkStatsFactory.java"
  - type: aosp
    path: "packages/modules/Connectivity/service/src/com/android/server/BpfNetMaps.java"
  - type: aosp
    path: "packages/modules/Connectivity/bpf/progs/netd.c"
  - type: aosp
    path: "kernel/common/net/core/filter.c @ android17-6.18-2026-06_r6"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/net/NetworkPolicyManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/connectivity/Vpn.java"
  - type: aosp
    path: "frameworks/base/core/java/android/net/VpnService.java"
  - type: aosp
    path: "frameworks/base/core/res/AndroidManifest.xml"
  - type: aosp
    path: "frameworks/base/telephony/java/android/telephony/SubscriptionInfo.java"
  - type: official
    path: "developer.android.com/reference/android/net/ConnectivityManager"
  - type: official
    path: "developer.android.com/privacy-and-security/local-network-permission"
  - type: official
    path: "developer.android.com/about/versions/17/behavior-changes-17"
tags: [connectivity, network, system-service, mainline, network-monitor, netstats, vpn]
related_chapters: ["1.42", "1.44", "5.7", "12.1", "12.3", "24.17"]
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part2-performance/ch12-apk-network/05-connectivity-service-network-callback.md"
  - "src/part2-performance/ch12-apk-network/08-networkagent-lifecycle-scoring.md"
---

# 1.43 Android 17 ConnectivityManager：架构、网络选择与性能

## 进程模型

应用看到的 `ConnectivityManager` 是 SDK 客户端。它通过 `IConnectivityManager` 访问 `ConnectivityService`。Android 17 中，这套代码已经属于 Connectivity Mainline 模块，可以作为系统模块独立于完整系统镜像更新；服务本身仍运行在 `system_server`。模块归属决定代码如何更新，进程归属决定它使用哪些线程和内存、故障会影响哪个进程，两者不能混为一谈。

网络验证又有不同的边界。`NetworkMonitor` 的实现位于 NetworkStack 模块，`AndroidManifest.xml` 把 `NetworkStackService` 放在独立的 `com.android.networkstack.process` 进程。`ConnectivityService` 通过稳定 AIDL `INetworkStackConnector.makeNetworkMonitor()` 为网络创建监视器。验证探测卡住时，不能直接推断 `system_server` 的 Connectivity 线程正在执行 HTTP 请求。

`netd` 是原生守护进程，负责执行网络创建、路由、权限和防火墙等内核配置。NetworkStats 的部分 Java 代码也由 Connectivity 模块交付并运行在 `system_server`，其内核计数来自 pin 在 BPF 文件系统中的 map；pin 表示为 BPF 对象建立持久路径，map 则是内核与用户空间交换计数数据的容器。

```text
应用进程
  ConnectivityManager / NetworkStatsManager / VpnManager
        │ Binder
        ▼
system_server
  ConnectivityService
    ├─ NetworkAgentInfo / NetworkRanker
    ├─ NetworkStatsService
    ├─ NetworkPolicyManagerService
    └─ VpnManagerService / Vpn
        │                         │
        │ NetworkStack AIDL       │ netd AIDL / netlink
        ▼                         ▼
com.android.networkstack.process  netd
  NetworkMonitor / IpClient       路由、BPF、防火墙、socket 规则
        ▲
        │ INetworkMonitorCallbacks
        └──────────────────────── ConnectivityService

网络提供者所在进程
  Wi-Fi / Telephony / Ethernet / VPN
    NetworkProvider ──请求通知──► 提供者 Looper
    NetworkAgent    ──Binder────► ConnectivityService
```

需要区分三个位置：

1. `ConnectivityService` 不再位于 `frameworks/base/services/core/java/com/android/server/ConnectivityService.java`；Android 17 的实现路径是 `packages/modules/Connectivity/service/src/com/android/server/ConnectivityService.java`。
2. `NetworkMonitor` 不在 `system_server` 内执行探测。
3. 网络提供者不等于某个 HAL。Wi-Fi、蜂窝和以太网各自先维护物理或逻辑链路，再用 `NetworkAgent` 把一个可以参与系统网络选择的网络交给 Connectivity。

## 一个网络在系统中如何表示

### NetworkAgent：提供者交给系统的控制端点

网络提供者准备好一组初始属性后，构造并注册 `NetworkAgent`：

- `NetworkCapabilities`：网络的传输类型和能力，例如 Wi-Fi、蜂窝、`INTERNET`、`NOT_METERED`、`NOT_SUSPENDED`；
- `LinkProperties`：接口名、地址、路由、DNS、代理、MTU；
- `NetworkScore`：提供者可声明的选择策略，以及仅供兼容和日志使用的 legacy int（旧版整数分数）；
- `NetworkAgentConfig`：显式选择、是否接受未验证网络、VPN 属性等稳定配置；
- `providerId`：创建它的 `NetworkProvider`。

Android 17 的 agent 注册和更新通道是 Binder：

1. `NetworkAgent.register()` 把 `INetworkAgent.Stub`、初始属性和 provider ID 交给 `ConnectivityService.registerNetworkAgent()`。
2. 服务返回 `Network` 和 `INetworkAgentRegistry`。
3. agent 通过 registry 的 `sendNetworkCapabilities()`、`sendLinkProperties()`、`sendScore()` 等方法发送更新。
4. 服务通过 `INetworkAgent` 回告验证状态、带宽更新请求、keepalive 等事件。

Android 17 的 agent 数据通道不再使用 `AsyncChannel`。`NetworkProvider` 的传统请求通知仍使用 `Messenger` 投递到构造时指定的 `Looper`；较新的 `offerNetwork()` 则为一项网络供给提议（offer）绑定回调和 `Executor`。两条协议分别服务于“系统是否需要提供者建立网络”和“已经建立的网络怎样上报状态”两个阶段。

注册只让服务认识这个 agent；agent 标记为 connected 后，网络才可出现在公开查询中、满足请求并参与默认网络选择。`unregister()` 才结束它的生命周期。

### NetworkAgentInfo：ConnectivityService 的权威状态

服务为每个 agent 建立 `NetworkAgentInfo`（NAI）。它持有：

- 不变的 `Network`/netId 和 `INetworkAgent`；
- 当前 `NetworkCapabilities` 与 `LinkProperties`；
- `NetworkMonitorManager`；
- `FullScore`；
- 当前和历史验证时间；
- 当前强制门户（captive portal）、部分连通、销毁和 linger（暂留旧网络以便连接收尾）状态；
- 该网络正在满足的 `NetworkRequest` 集合。

这里的多个状态有明确区别：

| 判断 | 含义 |
| --- | --- |
| agent 已注册 | `ConnectivityService` 已分配 `Network`，尚不代表可用 |
| native network 已创建 | 已通知 `netd` 创建内核数据通路使用的 netId 及相关规则 |
| agent 已 connected | 可以满足请求并出现在 API 中 |
| 有 `NET_CAPABILITY_INTERNET` | 提供者声明该网络设计上可访问互联网 |
| 有 `NET_CAPABILITY_VALIDATED` | 系统最近一次验证认为互联网连通 |
| 有 `NET_CAPABILITY_PARTIAL_CONNECTIVITY` | 验证只得到部分连通结果 |
| 成为默认网络 | 对某个 UID 而言，它是当前最佳匹配；VPN 和策略可能使不同 UID 看到不同结果 |

源码没有为 NAI 定义一个覆盖全部阶段的单一枚举，而是用时间戳与多个状态组合表达生命周期。`mCreatedTime`、`mConnectedTime`、`mFirstValidationTime`、`mCurrentValidationTime`、`mFirstEvaluationConcludedTime` 和 `mDestroyedTime` 分别帮助判断 native network 创建、首次 connected、首次/当前验证、首轮评估结束和数据通路销毁。netId 在网络销毁后可以复用，长期日志还要关联 transport（Wi-Fi、蜂窝等传输类型）、接口与创建时刻。

`INTERNET` 是网络提供者对用途的声明，`VALIDATED` 是系统探测得到的结果。只检查前者会把已经关联却无法出网的 Wi-Fi 误判为可用；建立连接前又不可能要求已经具有后者，因为 `VALIDATED` 是连接建立后才产生并且会变化的能力。

## 从注册到可用：真实生命周期

一次 Wi-Fi 或蜂窝网络上线包含以下步骤：

```text
提供者建立链路
    │
    ├─ NetworkAgent.register()
    │      └─ ConnectivityService 创建 netId 与 NetworkAgentInfo
    │
    ├─ ConnectivityService 请求 NetworkStack 创建 NetworkMonitor
    │
    ├─ NetworkAgent.markConnected()
    │      ├─ 网络开始满足不要求验证的请求
    │      └─ ConnectivityService 触发匹配和排序
    │
    ├─ NetworkMonitor 执行探测
    │      └─ 通过 INetworkMonitorCallbacks 回报结果
    │
    ├─ ConnectivityService 更新 VALIDATED / CAPTIVE_PORTAL /
    │  PARTIAL_CONNECTIVITY 等能力
    │
    └─ 再次匹配请求，必要时切换各 UID 的默认网络
```

`ConnectivityService.registerNetworkAgentInternal()` 会先发起异步 `makeNetworkMonitor()`。源码专门处理了 monitor 尚未返回而 agent 已继续更新的时间窗口，因此排障时不要把日志出现顺序简单理解为同一条同步调用栈。

网络断开也不是 `NetworkMonitor` 进入某个 `LOST` 状态。物理链路断开或 agent 注销由提供者和 Connectivity 管理；对应用而言，`onLost()` 还可能只表示该网络不再满足当前请求。对于默认网络回调，旧网络被更优网络替代后仍可能继续存在。

native network 与 DNS cache 由 `ConnectivityService` 协调创建。不同能力和 VPN 场景会让创建发生在 agent 注册期或首次 connected 处理期；销毁时，服务先重新匹配请求和默认网络，再调用 netd、DnsResolver 与 DnsManager 清理旧数据通路，最后释放 netId。这个顺序用于减少切换中断，不能简化成“清 DNS 导致断网”。

## NetworkMonitor：验证的是互联网质量，不是物理链路

Android 17 的 `NetworkMonitor` 是一个事件驱动的 `StateMachine`。源码中的主要状态包括 `EvaluatingState`、`ProbingState`、`CaptivePortalState`、`EvaluatingPrivateDnsState` 和 `ValidatedState`。它会综合以下输入：

- DNS 探测；
- HTTP、HTTPS 和 fallback 探测；
- PAC（自动代理配置）场景；
- RFC 8908 Captive Portal API（CAPPORT，门户网络向系统说明登录状态的接口）信息；
- strict mode Private DNS（只使用指定加密 DNS 服务器）解析与探测；
- 连接后的 DNS/TCP 数据停滞信号，用于触发重新验证。

探测 URL、并行策略和超时受资源配置、DeviceConfig、网络属性及模块版本影响。单个探测代码中虽有超时常量，也不能据此写成“所有验证固定 30 秒”。失败后状态机会按逐渐延长等待时间的退避策略重试；验证失败不会自行宣布物理网络断开。

结果要这样理解：

- `VALIDATED`：验证成功，或某些不要求互联网验证的网络按规则跳过验证；
- `CAPTIVE_PORTAL`：探测或 CAPPORT 信息表明网络要求用户先登录或确认；
- `PARTIAL_CONNECTIVITY`：组合探测得到有限连通结果，系统内部能力名是
  `NET_CAPABILITY_PARTIAL_CONNECTIVITY`；
- Private DNS：strict mode 下还要解析并验证指定服务器，它有自己的状态和重试。

`PARTIAL_CONNECTIVITY` 不能通过 `NET_CAPABILITY_CAPTIVE_PORTAL` 判断，也不能定义成“Google 可达、第三方 CDN 不可达”。系统依据配置的验证端点及探测组合产生结论，设备厂商和网络环境都可能改变端点行为。

`NET_CAPABILITY_PARTIAL_CONNECTIVITY` 在 Android 17 仍是隐藏的 `@SystemApi`。系统组件可以直接检查它；普通 SDK 应用不能把这个常量写进可发布代码。对普通应用来说，稳妥的策略是：

- 用 `INTERNET + VALIDATED` 判断通用互联网可用性；
- 可公开检查 `CAPTIVE_PORTAL`，对其余未验证状态依赖业务请求结果并给出可恢复错误；
- 最终仍对业务请求设置连接、读写和整体超时，因为系统验证不等于你的服务端健康。

## 网络选择：有序策略，不是加分公式

### legacy int 已退出实际排名

`NetworkScore.Builder.setLegacyInt()` 在 Android 17 的源码注释中写明：该值供测量和日志使用，不再参与网络之间的排名。`FullScore` 把 agent 策略与 Connectivity 管理的状态合并成一组布尔策略位，例如：

- 当前或曾经验证；
- VPN；
- 用户曾显式选择、接受未验证网络或要求避开未验证网络；
- 是否为主传输、是否即将退出、是否为 VCN（Virtual Carrier Network，运营商配置的虚拟网络层）；
- 已销毁但暂留以等待替换；
- 即使暂时未满足请求也要保持连接的原因（keep-connected reason）。

因此，下面这类公式没有 Android 17 源码依据：

```text
Wi-Fi 60 + validated 40 = 100
Cellular 50 + validated 40 = 90
Partial connectivity +20
```

原生 `Vpn` 仍会构造 legacy int 为 101 的 `NetworkScore`，这是历史兼容值。`FullScore` 会基于 `TRANSPORT_VPN` 设置 VPN 策略；不能据此描述成“VPN 继承底层网络分数”。

legacy int 还有一个受限的 prospective-offer（尚未建网时的预期供给）特例：provider 在真正建网前可用 `NetworkOffer` 表示可能提供的能力，`FullScore.makeProspectiveScore()` 会把高于 `NetworkRanker.LEGACY_INT_MAX` 的 filter 值映射为 `POLICY_IS_INVINCIBLE`，只用于判断这条 offer 是否值得尝试建网。网络 connected 后仍按完整策略链排序，不能用这个兼容分支恢复旧整数打分模型。

### NetworkRanker 的决策顺序

对一个 `NetworkRequest`，`NetworkRanker` 先排除不满足 capabilities、transport、specifier（指定某个网络实例或提供者的附加条件）、UID 等要求的网络，再逐项缩小候选集。Android 17 源码中的重要顺序是：

1. 标记为不可被其他候选覆盖的网络供给（invincible offer）；
2. 已连接 VPN；
3. 用户选择且接受未验证的网络；
4. 已验证或被用户接受的网络，并处理允许蜂窝等候选让位给低质量 Wi-Fi 的 `yield-to-bad-Wi-Fi` 兼容策略；
5. 未标记为即将退出的 `POLICY_EXITING` 网络；
6. 同一 transport 中被提供者标为 primary 的网络；
7. 仍无法区分时按 Ethernet、Wi-Fi、Bluetooth、Cellular 的 transport 顺序；
8. 等价蜂窝候选中的 VCN；
9. 尚未进入“已销毁数据通路、等待替代者”状态的网络；
10. 全部等价时保持当前满足该请求的网络（satisfier），减少无意义切换。
11. 前述条件仍不能区分时，从剩余等价候选中返回一个。

`FullScore` 中虽有 `POLICY_IS_UNMETERED`，Android 17 的 `NetworkRanker` 对应筛选仍是带 TODO 的注释代码。不能据此声称所有非计费网络都会直接获得更高数值分数。

这份顺序用于理解源码，不适合在业务代码中复制一套“系统打分器”。运营商配置、Wi-Fi 策略、VPN、每 UID 路由和后续平台版本都会影响最终选择。

网络提供者的 `NetworkOffer` 也不是建网承诺。offer 表示“如果系统需要，我可能提供具有这些能力和策略的网络”。系统只有在它可能胜过当前 satisfier 时才通知 provider 尝试建网，从而减少没有收益的扫描、拨号和耗电。

score、能力或验证状态变化后，重匹配的主要方法边界是：

```text
rematchAllNetworksAndRequests()
  -> computeNetworkReassignment()
       -> NetworkRanker.getBestNetwork(...)
  -> applyNetworkReassignment()
  -> issueNetworkNeeds()
```

计算阶段遍历需要重新评估的 request/layer（请求及其优先级层），应用阶段更新 satisfier、默认网络、可用/丢失通知、被动监听和不活动状态，随后才通知 provider 新的网络需求。源码明确提示 rematch 可能较慢；实际耗时应从调试日志中的 compute/apply/issue 三段测量，不能用固定复杂度或毫秒常数替代。

## NetworkRequest 与 NetworkCallback

### 三类常见需求不要混用

| API | 系统含义 | 适用场景 |
| --- | --- | --- |
| `registerDefaultNetworkCallback()` | 观察当前应用的默认网络 | 大多数应用的联网状态 |
| `registerNetworkCallback(request, ...)` | 被动观察所有匹配网络 | 观察 Wi-Fi、非计费网络等候选，不要求系统为此建网 |
| `registerBestMatchingNetworkCallback()` | 只跟踪当前最佳匹配 | API 31+ 只需单个候选的观察场景 |
| `requestNetwork(request, ...)` | 主动请求系统尝试提供最佳匹配网络 | 确实需要系统建立或保持额外网络的短期任务 |
| `reserveNetwork(request, ...)` | 预留未来由软硬件组件提供的能力 | API 36+ 的专门供给流程，不用于在线状态监听 |

`requestNetwork()` 可能促使 radio、扫描或数据网络保持活动，不能当成轮询网络状态的工具。完成后必须调用 `unregisterNetworkCallback()`。

默认网络是“当前应用的默认网络”。某个 UID 处于 VPN、企业网络偏好或其他策略下时，它看到的默认网络可能与系统默认物理网络不同。

### 回调顺序和线程

Android 8.0 起，`onAvailable()` 后会按顺序收到：

1. `onCapabilitiesChanged()`；
2. `onLinkPropertiesChanged()`；
3. `onBlockedStatusChanged()`。

不要在 `onAvailable()` 内同步调用 `getNetworkCapabilities()` 或 `getLinkProperties()`。网络可能已经再次变化，同步查询结果会与当前回调乱序。使用随后回调携带的对象，可以保留 framework 保证的事件顺序。

无 `Handler` 参数时，回调运行在 framework 为应用创建的 Connectivity 线程；传入 `Handler` 后，运行在该 handler 对应的 Looper。回调先经跨进程通知进入应用，再由 `CallbackHandler` 串行分发，并不直接执行在应用 Binder 线程池里。

默认回调不只在默认网络对象变化时触发。当前网络的 capabilities、link properties 或 blocked status 改变时，应用仍会收到对应回调。

下面的示例用于维护一个可供 UI 和任务调度读取的快照。耗时探测仍应交给独立执行器。

```kotlin
class NetworkStateTracker(
    context: Context,
    looper: Looper
) : Closeable {
    private val cm = context.getSystemService(ConnectivityManager::class.java)
    private val handler = Handler(looper)

    @Volatile
    var state = State()
        private set

    data class State(
        val network: Network? = null,
        val validated: Boolean = false,
        val captivePortal: Boolean = false,
        val metered: Boolean = true,
        val blocked: Boolean = false
    )

    private val callback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            state = State(network = network)
        }

        override fun onCapabilitiesChanged(
            network: Network,
            caps: NetworkCapabilities
        ) {
            if (state.network != network) return
            state = state.copy(
                validated = caps.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_VALIDATED
                ),
                captivePortal = caps.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL
                ),
                metered = !caps.hasCapability(
                    NetworkCapabilities.NET_CAPABILITY_NOT_METERED
                )
            )
        }

        override fun onBlockedStatusChanged(network: Network, blocked: Boolean) {
            if (state.network == network) state = state.copy(blocked = blocked)
        }

        override fun onLost(network: Network) {
            if (state.network == network) state = State()
        }
    }

    init {
        cm.registerDefaultNetworkCallback(callback, handler)
    }

    override fun close() {
        cm.unregisterNetworkCallback(callback)
    }
}
```

这段代码没有在回调里启动真实联网探测，也没有假定 `onLost()` 前一定收到 `onLosing()`。生产代码还应把状态发布到 `StateFlow`、LiveData 或自己的线程安全模型，并让持有者的生命周期与注册/注销严格配对。

### 回调性能的实际约束

Android 17 对每个 UID 尚未注销的请求和回调（outstanding requests）设有 100 个上限。这个计数由多种 `registerNetworkCallback()`、`requestNetwork()` 和 `ConnectivityDiagnosticsManager` 回调共享。达到上限会抛出异常。

优化重点如下：

- 复用进程级 tracker，避免每个页面各注册一份；
- 能观察默认网络时，不注册宽泛的“所有网络”监听；
- 在 capabilities 里只提取业务需要的字段，再做快照去重；
- DNS、路由和代理变化属于 `LinkProperties`，不要等待 `onCapabilitiesChanged()`；
- 回调中不做磁盘 I/O、同步网络请求或长时间锁等待；
- 记录回调处理时长和队列等待，不能用固定“每次 Binder 小于几毫秒”替代测量。

Android 16 起的 `NET_CAPABILITY_NOT_BANDWIDTH_CONSTRAINED` 也是策略输入：缺少它时，应限制高带宽传输与访问频率，不能只根据 Wi-Fi/蜂窝 transport 推断网络是否受限。

## 默认网络切换、socket 与 DNS

默认网络切换完成，并不表示 `ConnectivityService` 会替应用迁移已经建立的 TCP/QUIC 会话。

- 没有显式绑定网络的新 socket 和新发起的主机名解析，会使用当前 UID 的默认网络；
- `Network.getSocketFactory()`、`Network.bindSocket()` 和
  `Network.getAllByName()` 可把单个操作限定到指定网络；
- `bindProcessToNetwork()` 会影响该进程随后创建的 socket 和 DNS 解析，作用范围很大，一般只供确有多网络需求的组件使用；
- 已建立连接仍关联原 netId/接口。旧网络被拆除或策略关闭 socket 时，应用要按照具体协议的语义重连；
- VPN 或库若声明了明确 underlying networks，要在承载网络变化时同步更新。

连接恢复不能只看到 `onAvailable(newNetwork)` 就重新发送全部请求。应先区分：

- 重复执行仍产生相同业务效果、可以安全重试的幂等请求；
- 需要业务 request ID 或服务端幂等键防止重复写入的请求；
- WebSocket、HTTP/2、QUIC 等由网络库自行处理迁移/重连的长连接。

### linger 与等待替代网络

请求迁到新的 satisfier 后，旧网络可能进入 linger，为旧 socket 留出收尾时间。Android 17 AOSP 的 linger 与 nascent（新网络尚未满足请求时的短暂观察期）默认延迟分别为 30 秒和 5 秒，但可以由系统配置调整，不属于 SDK 时序承诺。`onLosing()` 只是提示，应用必须允许它缺失，或几乎与 `onLost()` 同时到达。

`NetworkAgent.unregisterAfterReplacement(timeout)` 让旧 agent 先销毁 native network，再短暂保留注册状态等待等价替代者。此时 `POLICY_IS_DESTROYED` 让新网络在其他条件等价时胜出；若超时仍没有替代者，旧 agent 最终注销。linger 到期或 native network 已销毁，都不表示所有旧连接已经由业务正确恢复，重试与幂等仍由连接库和应用负责。

## NetworkStats：内核累计值与历史集合

### Android 17 的采集路径

NetworkStats 的目标是按 UID、接口等维度计数并提供历史查询，不是逐包实时性能监控。Android 17 的核心路径如下：

```text
数据包经过内核 BPF 程序
    │
    ├─ iface stats map
    ├─ app UID stats map
    └─ active UID/tag/interface stats map
             │
             ▼
NetworkStatsFactory
  交换 active/inactive stats map
  读取并清空 inactive map
  合并开机以来累计快照
  处理 464xlat 与 TUN VPN 归属迁移
             │
             ▼
NetworkStatsService
  NetworkStatsRecorder / NetworkStatsCollection
  FileRotator 持久化历史
             │ Binder session
             ▼
NetworkStatsManager 查询
```

以下内核行为以 ACK `android17-6.18-2026-06_r6` 为准。Android 17 的 `bpf/progs/netd.c` 为 6.18 定义了专用 ingress（入站）统计变体，进入 `bpf_traffic_account()` 后更新 UID、tag（应用为 socket 流量设置的分类标签）、interface 维度的 map；egress（出站）也进入同一计数函数。用户空间随后消费这些累计值。这里没有沿用更高版本内核的 BPF 行为。

源码固定了多个 BPF map 路径，例如 `map_netd_app_uid_stats_map`、`map_netd_stats_map_A/B` 和 `map_netd_iface_stats_map`。读取详细统计前会交换当前由内核写入的 active map，再读取暂时停止写入的 inactive map，从而减少与内核更新计数的竞争。

历史数据不存放在 SQLite 中。`NetworkStatsRecorder` 使用 `FileRotator`（按时间轮换历史文件）和 `NetworkStatsCollection` 管理按时间段聚合的 bucket 记录。`queryDetailsForUid()` 打开统计 session，读取权限允许的历史集合；它不能概括成“Binder 后直接查询单个 UID 的 BPF map”。

### 何时采集

默认 `NetworkStatsSettings.getPollInterval()` 是 30 分钟，使用允许系统合并触发时间的不精确重复闹钟。除此之外，网络状态变化、上游变化、全局流量阈值警报、注册用量 callback、强制更新、UID 删除及 dumpsys 参数都可能引发采集或持久化。排障时要记录触发本次采集的具体原因（poll reason）。

查询和 poll 可能涉及：

- BPF map 遍历与合并；
- TUN VPN/464xlat 流量归属调整；
- 历史文件加载、时间 bucket 聚合和按权限裁剪结果；
- stats provider 同步；
- 持久化 I/O。

所以 `NetworkStatsManager` 的查询 API 标注为 `@WorkerThread`，表示不应在 UI 主线程调用。数据规模、时间范围、tag 数量、设备 I/O 和缓存状态共同决定耗时，不存在通用的“低于 10 ms”保证。

需要较高频率观察当前进程收发量时，可以在其统计语义允许的范围内使用 `TrafficStats` 计算前后差值；需要计费口径和跨时间段历史时再用 `NetworkStatsManager`。两者的统计范围、更新时效和权限都不同。

## NetworkPolicy：限制的是 UID 在某类网络上的访问

`NetworkPolicyManagerService` 根据 UID 状态、用户设置、网络是否计费和省电状态计算规则，再通过 Connectivity、`netd` 和 BPF 防火墙执行。常见约束包括：

| 约束 | 核心语义 |
| --- | --- |
| Data Saver | 对计费网络限制未获豁免的后台 UID |
| 用户禁止后台流量 | 该 UID 在计费网络后台受限 |
| 低电耗模式（Doze） | 通过 dozable 等防火墙链约束不在允许列表中的 UID |
| App Standby | 对处于应用待机状态的应用使用对应防火墙规则 |
| Restricted mode | 只允许具有相应权限或豁免的 UID |
| Lockdown VPN | 必须走 VPN 的 UID 在 VPN 不可用时受阻 |

Data Saver 不是给前台应用“降速”。Doze 也不能概括成关闭所有网络：系统维护允许列表、允许后台任务执行的维护窗口及多条防火墙链，具体 UID 的结果由规则组合决定。

Android 17 的 Connectivity 代码会从 BPF 规则状态取得所跟踪 UID 的 blocked reasons（被阻止的原因位集合）。网络的计费属性或 UID 规则变化时，系统向匹配回调发送 `onBlockedStatusChanged()`。`onAvailable()` 表示网络满足请求，blocked 回调表示当前 UID 是否能在该网络上正常发送流量；一个网络可以已经 available，同时仍对该 UID blocked。

普通 SDK 应用收到的是 `onBlockedStatusChanged(Network, boolean)`，只能知道是否被阻止。携带 blocked-reason 位掩码的重载是面向 module libraries 的 `@SystemApi`。因此，应用可以把布尔状态与 Data Saver、前后台状态等公开信息结合展示，但不能仅凭这个 callback 断定限制一定来自 Doze、Data Saver 或 VPN。

应用应把阻止状态作为调度输入，停止无意义的重试或把工作交给 JobScheduler/WorkManager，而不是循环创建 socket 验证限制是否解除。

## VPN：区分应用隧道和平台 IKEv2/IPsec

### 应用 VpnService

`VpnService.Builder.establish()` 通过 `VpnManagerService` 创建 TUN（向用户空间收发 IP 包的虚拟网络接口），并把封装文件描述符的 `ParcelFileDescriptor` 返回应用。应用从 fd 读取出站 IP 包，经自建隧道发送；从隧道收到的数据写回 fd。隧道控制 socket 必须调用 `protect()` 排除在 VPN 路由之外，否则它本身可能再次被送进 VPN，形成循环。

这条路径的性能取决于：

- TUN 与用户空间之间的包搬运、批处理和 buffer 管理；
- 加密库及算法；
- 线程切换和锁；
- MTU、分片与封装开销；
- underlying network 切换后的恢复策略。

### 平台 IKEv2/IPsec

`Ikev2VpnProfile` 由 `VpnManager` 配置（provision）后，可以由系统运行，不要求 VPN 应用持续在后台处理数据包。`Vpn.IkeV2VpnRunner` 使用 IKE 密钥协商会话、`IpSecTunnelInterface` 和 `IpSecTransform`；双方支持时，可以用 MOBIKE 在底层网络变化后更新 IKE/IPsec 路径。其数据通路与用户空间 `VpnService` 不同，不能把所有 VPN 都画成“应用读写 TUN”。

两种路径最终都会注册 VPN `NetworkAgent`，并在 capabilities 中设置受影响的 UID 和 underlying networks（承载隧道的底层网络）。VPN 在排序中有显式策略优先级；底层 Wi-Fi 或蜂窝仍负责承载隧道，但 VPN 不通过复制底层 score 成为默认网络。

VPN 优化要测端到端指标：

- TUN 读写速率、批大小和队列等待；
- 加密线程 CPU 时间和调度延迟；
- 隧道 MTU、重传、分片或 ICMP Packet Too Big 报文；
- underlying network 变化到隧道恢复的时间；
- DNS 是否走预期网络；
- 分流隧道（split tunnel）、允许绕过 VPN（bypass）和强制 VPN（lockdown）规则是否符合设计。

固定“VPN 增加多少 CPU”或“每条规则耗时多少微秒”无法跨设备、算法和包长成立。

## Android 17 / API 37 的应用可见变化

### ACCESS_LOCAL_NETWORK

Android 17 对 targetSdk 37 及以上应用强制本地网络保护：

- `android.permission.ACCESS_LOCAL_NETWORK` 是需要用户在运行时授权的 dangerous permission；
- 它属于 `NEARBY_DEVICES` 权限组；
- TCP、UDP 单播、组播、广播、入站连接以及 `.local` 局域网服务解析都可能受影响；
- targetSdk 36 及以下应用暂时继续通过 `INTERNET` 获得隐式访问，不应提前请求该权限；
- 系统提供隐私保护选择器（picker）的场景，应优先使用选择器缩小授权范围。

权限被拒绝时，应用必须把 LAN（局域网）不可达与公网故障分开呈现。反复请求公网、切换 Wi-Fi 或清 DNS 都不会解除权限阻断。

官方文档给出的典型表现也不同：TCP 连接常表现为超时，UDP 和一般权限拒绝通常返回表示“不允许操作”的 `EPERM`。使用 NDK 的 TCP 客户端可调用 `android_getnetworkblockedreason(fd)`，检查是否为 `ANDROID_NETWORK_BLOCKED_REASON_LNP`。这个接口只用于解释失败原因，不会绕过权限。

AOSP 侧不只增加了 Manifest 声明。Connectivity 的 `BpfNetMaps` 维护本地网络权限传播开关、UID/network/host 允许列表和缓存 generation（用于识别规则版本变化的代数）；这也解释了限制为何能作用于由运行时管理的 socket、原生 socket 和上层网络库。

### 流媒体套餐上下行速率

Android 17 新增：

```java
SubscriptionInfo.getStreamingAppMaxDownlinkKbps()
SubscriptionInfo.getStreamingAppMaxUplinkKbps()
```

它们位于 `android.telephony.SubscriptionInfo`，不在 `NetworkStatsManager`。数值表示运营商依据 GSMA TS.43 配置的流媒体应用上下行最大速率，单位为 Kbps；未知或不适用时返回 `SubscriptionPlan.BITRATE_UNKNOWN`。

这个值是套餐/运营商策略输入，不是当前链路吞吐量。码率控制还要结合播放器缓冲区、实际传输采样、丢包、RTT（网络往返时延）、`NetworkCapabilities` 带宽估计和服务端策略。

Android 17 还加入 `NET_CAPABILITY_PRIORITIZE_UNIFIED_COMMUNICATIONS`，面向符合条件的 OTT（通过互联网提供）语音/视频通话。它表示网络可能提供优先通信路径，不保证一定获得隔离资源的 5G network slice；普通列表、图片和遥测流量不应申请。显式请求这类能力时，要处理不可用、超时、回到默认网络以及 callback 注销。

### ECH

对 targetSdk 37 及以上应用，Android 17 为已经集成支持的网络库启用 Encrypted Client Hello（ECH，加密客户端问候）。客户端库和服务端都支持时，可以保护 TLS ClientHello 中暴露目标主机名的 SNI；无法协商时使用 ECH GREASE，以兼容方式发送类似 ECH 的扩展并发现中间设备兼容问题。应用可通过 Network Security Config 的 `<domainEncryption>` 按全局或域名选择模式。

ECH 属于 TLS 栈和网络安全配置，不由 `ConnectivityManager` 完成，也不保证连接会更快。握手行为要根据实际使用的 HttpEngine、WebView、OkHttp/平台 TLS 集成和服务端配置验证。

## 一套可复用的排障顺序

网络问题按以下顺序检查，可以减少在错误层级反复试验：

1. **提供者是否建链**：Wi-Fi 关联、IP provisioning（获取地址、路由和 DNS 等 IP 配置）、蜂窝数据网络是否成功；
2. **agent 是否注册并 connected**：netId、网络接口和 capabilities 是否存在；
3. **LinkProperties 是否完整**：地址、默认路由、DNS、MTU、代理；
4. **验证结果**：validated、portal、partial、Private DNS；
5. **请求是否匹配**：transport、capability、specifier 和 UID；
6. **为何赢得或失去默认网络**：VPN、validation、即将退出、primary、VCN 等策略；
7. **UID 是否 blocked**：Data Saver、Doze、应用待机、restricted mode、lockdown VPN；
8. **socket 和 DNS 绑定**：旧连接是否仍在旧 netId，解析是否使用预期网络；
9. **业务端点**：TLS、HTTP、服务端和 CDN 是否健康。

常用只读命令如下：

```bash
adb shell dumpsys connectivity
adb shell dumpsys network_stack
adb shell dumpsys dnsresolver
adb shell dumpsys netd
adb shell dumpsys netpolicy
adb shell dumpsys netstats
adb shell dumpsys vpn_management
adb shell ip rule
adb shell ip route show table all
```

这些命令依次用于查看 Connectivity 的网络与请求、验证日志、DNS 配置、native 网络、UID 策略、统计采集、VPN 状态和最终路由。不同构建类型会删去部分敏感字段；某条命令无输出时，应先检查服务是否存在和调用者权限。

性能问题再配合 Perfetto：

- `binder_driver`：跨进程注册、回调或 netd 调用是否排队；
- `sched`：Connectivity、NetworkStack、VPN 线程是否被抢占，或已经 runnable 却长期没有获得 CPU；
- `power`/网络相关数据源：radio 活跃和网络请求生命周期；
- 应用自定义 trace：从回调进入到业务状态更新、重连和首包成功。

## 结论

Android 17 的 Connectivity 体系可以概括为四个职责：

- 网络提供者负责建链并通过 `NetworkAgent` 上报；
- `ConnectivityService` 负责匹配、排序、每 UID 默认网络和策略协调；
- 独立 NetworkStack 进程中的 `NetworkMonitor` 负责互联网与 Private DNS 验证；
- `netd`、BPF 和内核负责路由、权限、防火墙与计数执行。

做性能分析时，应先定位职责边界，再测量队列、探测、路由、socket、DNS 和业务请求。不要用旧的 AsyncChannel 图、固定加分表、固定验证超时或通用耗时数字解释 Android 17。

## 源码导航与官方资料

- `packages/modules/Connectivity/framework/src/android/net/ConnectivityManager.java`
- `packages/modules/Connectivity/framework/src/android/net/NetworkAgent.java`
- `packages/modules/Connectivity/framework/src/android/net/NetworkProvider.java`
- `packages/modules/Connectivity/service/src/com/android/server/ConnectivityService.java`
- `packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkAgentInfo.java`
- `packages/modules/Connectivity/service/src/com/android/server/connectivity/FullScore.java`
- `packages/modules/Connectivity/service/src/com/android/server/connectivity/NetworkRanker.java`
- `packages/modules/NetworkStack/src/com/android/server/connectivity/NetworkMonitor.java`
- `packages/modules/Connectivity/service-t/src/com/android/server/net/NetworkStatsService.java`
- `packages/modules/Connectivity/service-t/src/com/android/server/net/NetworkStatsFactory.java`
- `packages/modules/Connectivity/bpf/progs/netd.c`
- `kernel/common/net/core/filter.c`（`android17-6.18-2026-06_r6`）
- `frameworks/base/services/core/java/com/android/server/net/NetworkPolicyManagerService.java`
- `frameworks/base/services/core/java/com/android/server/connectivity/Vpn.java`
- [ConnectivityManager API](https://developer.android.com/reference/android/net/ConnectivityManager)
- [读取网络状态](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Android 17 本地网络权限](https://developer.android.com/privacy-and-security/local-network-permission)
- [Android 17 targetSdk 行为变化](https://developer.android.com/about/versions/17/behavior-changes-17)
- [SubscriptionInfo API](https://developer.android.com/reference/android/telephony/SubscriptionInfo)
