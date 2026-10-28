---
title: netd 与 DnsResolver：DNS 解析性能和故障诊断
chapter: '12.2'
section: '12.2'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
last_verified: '2026-10-24'
last_verified_against: Android 17 / API 37 与 S Extensions 22 公开 API；AOSP android-17.0.0_r1；OkHttp 5.3.0；组合查询线程与取消边界按固定源码分别披露
last_review_finalize_at: '2026-08-25T16:10:03+08:00'
confidence: high
tags:
- netd
- dnsresolver
- network-performance
- connectivity
- diagnostics
related_chapters:
- '12.1'
- '1.22'
- '24.5'
- '24.7'
sources:
- type: official
  path: https://source.android.com/docs/core/ota/modular-system/dns-resolver
- type: official
  path: https://developer.android.com/reference/android/net/DnsResolver
- type: official
  path: https://developer.android.com/reference/android/net/dns/HttpsEndpoint
- type: official
  path: https://developer.android.com/privacy-and-security/local-network-permission
- type: official
  path: https://developer.android.com/ndk/reference/group/networking
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/DnsResolver.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/service/src/com/android/server/ConnectivityService.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/service/src/com/android/server/connectivity/DnsManager.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/DnsResolverService.cpp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/ResolverController.cpp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/DnsQueryLog.cpp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/PrivateDnsConfiguration.cpp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/service/src/com/android/server/connectivity/NetworkDiagnostics.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/binder/android/net/IDnsResolver.aidl
- type: aosp
  path: https://android.googlesource.com/platform/system/netd/+/android-17.0.0_r1/server/NetdNativeService.cpp
- type: external
  path: https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt
---

# netd 与 DnsResolver：DNS 解析性能和故障诊断

建立一条新连接前通常要先解析域名，但一次 HTTP 请求不一定触发解析：连接池能复用现有连接，HTTP/2、HTTP/3 也能在同一连接上承载多次请求。诊断 DNS 问题时，先确认本次请求有没有触发解析、解析绑定在哪条网络、后续连接实际用了哪个结果，再区分系统 resolver（解析器）与 HTTPDNS（通过 HTTP API 获取解析结果的应用侧方案）。

[12.1 Android 网络与 TLS 性能优化](01-android-network-tls-performance.md)介绍请求阶段、连接和传输协议，[1.22 Connectivity 服务、网络选择与回调](../../part1-fundamentals/ch01-architecture/22-connectivity-service.md)说明平台网络状态与系统如何选择默认网络。诊断时先要把这些应用侧事件与 Android 17 的系统调用路径对应起来，才能落到具体的系统证据上。

## 一、四层边界：调用方、框架、resolver、netd

Android 应用常用的解析入口包括：

- `InetAddress.getAllByName()` 与 `Network.getAllByName()`；
- API 29 起提供的 `android.net.DnsResolver`；
- OkHttp 默认的 `Dns.SYSTEM`，它在 Android 上委托 `InetAddress.getAllByName()`；
- native（C/C++ 层）代码的 `android_getaddrinfofornetwork()` 等 NDK 网络 API。

传入明确的 `Network` 时，普通系统查询使用该网络的 resolver 配置；未指定网络时，则按该入口的进程绑定与系统 DNS 网络选择规则处理，不能一概理解为物理默认网。数值地址、localhost 和受支持网络上的 `.local` 可能走专门路径。DNS 绑定也不会自动绑定后续任意 socket；要让解析与连接使用同一网络，连接侧仍须使用相应 `Network` 的 socket 工厂或绑定机制。Wi-Fi、蜂窝、VPN 同时存在时，应分别记录解析网络与实际连接网络。

<!-- gracker-diagram: ch12-02-02-dns-socket-network -->
![解析网络与后续 socket 的网络选择](../../assets/diagrams/ch12/ch12-02-02-dns-socket-network.png)

图：解析与连接两侧分别确定Network，不能只绑定DNS就推断后续路由。 未指定网络还受进程绑定与入口规则影响；数值地址、localhost、.local有专门路径。

| 层级 | 典型组件 | 主要职责 | 应用侧证据 |
|---|---|---|---|
| 调用方 | OkHttp、Cronet、`InetAddress`、应用自定义 resolver | 决定查询时机、缓存策略和后续连接 | DNS 阶段事件、异常、连接目标 |
| Framework API（框架接口） | `DnsResolver`、`Network` | 指定 `Network`、查询类型、取消和回调线程 | `DnsException`、rcode（DNS 响应码）、结果数量 |
| DNS Resolver 模块 | `com.android.resolv`、`IDnsResolver` | 按 `netId`（系统分配的网络标识）保存配置与缓存，执行 DNS 查询和 Private DNS | `dumpsys dnsresolver` |
| native 网络管理 | `netd`（Android 原生网络管理服务） | 创建网络、路由、接口、权限、转发规则 | `dumpsys connectivity`、平台日志 |

“netd 负责 Android DNS”这个说法把两个服务混成了一个。Android 17 的 resolver 源码在 `packages/modules/DnsResolver`，native `netd` 在 `system/netd`；`ConnectivityService` 会在同一个网络生命周期里分别调用它们。

<!-- gracker-diagram: ch12-02-01-resolver-control-query -->
![应用查询路径与系统配置路径分工](../../assets/diagrams/ch12/ch12-02-01-resolver-control-query.png)

图：区分应用查询数据通路、系统配置Binder和native网络管理。 App连线是概念调用路径，省略Bionic/兼容代理细节；IDnsResolver是系统受权配置入口，不是普通应用查询Binder。

## 二、版本迁移：从 netd 内部代码到独立主线模块

这段历史解释了旧资料里的路径从哪来；排查 Android 17 时，以当前目录和服务边界为准。

| 版本 | 变化 | 阅读旧资料时的判断 |
|---|---|---|
| Android 9 及更早 | resolver 代码分布在 Bionic（Android 的 C 标准库）与 netd，Java 查询可经本地代理 `dnsproxyd` | 旧文章中的 `system/netd` 路径可能只适用于当时版本 |
| Android 9 | 用户设置中加入 Private DNS，公开模式以 DNS-over-TLS（DoT，通过 TLS 加密 DNS）为基础 | Private DNS 属于系统解析策略，不等同于应用 DoH |
| Android 10 | resolver 迁入 `system/netd/resolv`，以 `com.android.resolv` APEX（可独立更新的系统模块包）交付 | 这是模块化初期的源码位置 |
| Android 17 | 当前实现位于 `packages/modules/DnsResolver`；接口仍以 `IDnsResolver` 与本地代理入口服务系统调用方 | 源码锚点使用 `android-17.0.0_r1` |

官方模块文档说明，Android 10 的 DNS Resolver 模块直接服务 `/dev/socket/dnsproxyd`，resolver 配置的 Binder（Android 进程间通信机制）入口也从 netd 移入该模块。

官方模块文档的链接方向是 netd 动态链接 resolver 模块，而不是 resolver 依赖 netd 服务或其库；模块依赖 Bionic，并静态链接其余依赖。resolver 直接服务 `/dev/socket/dnsproxyd`，配置 Binder 入口也由模块自己提供，系统服务无需让 netd 转发配置。Mainline 允许单独更新模块，设备实际模块版本仍须记录。

<!-- gracker-diagram: ch12-02-03-resolver-module-migration -->
![Resolver 模块迁移与当前服务边界](../../assets/diagrams/ch12/ch12-02-03-resolver-module-migration.png)

图：用版本节点说明旧路径来源，按当前模块与服务边界排错。 版本节点不是运行时长；Mainline可单独更新，设备模块不一定等于固定源码。

模块独立也不意味着应用拿到了全局 DNS 控制权。清空所有网络的 resolver 缓存、修改别的网络的 DNS server、操纵 Private DNS 校验状态，这些能力都受系统权限和服务边界保护，普通应用用不了。

<!-- gracker-diagram: ch12-02-04-resolver-privilege-boundary -->
![普通查询能力与系统配置权限](../../assets/diagrams/ch12/ch12-02-04-resolver-privilege-boundary.png)

图：普通应用按Network查询，系统受权服务才管理全局配置和缓存。 模块可独立更新不授予应用全局DNS控制权，dump也需要DUMP权限。

## 三、Android 17 的 `DnsResolver` API

### 3.1 Looper、Executor 与取消信号分别控制什么

Android 17 新增 `DnsResolver(Context, Looper)`；API 29 的 `DnsResolver.getInstance()` 在 API 37 被标记为废弃。`Context` 用于访问系统服务；可空的 `Looper` 监视查询文件描述符事件，传 `null` 时使用主 Looper。普通 `query()` / `rawQuery()` 的 FD 就绪路径会通过传入的 `Executor` 读取结果并执行回调，Looper 不等于业务回调线程。组合查询的额外等待超时存在下述固定 r1 例外。

<!-- gracker-diagram: ch12-02-05-looper-executor-paths -->
![Looper、Executor 与组合查询超时回调](../../assets/diagrams/ch12/ch12-02-05-looper-executor-paths.png)

图：普通FD就绪路径经Executor处理，组合查询超时路径须单独核实。 固定r1聚合器Handler直接reportResult，不能把普通路径的线程约定推广到所有终态；null Looper用主Looper。

查询应绑定 `CancellationSignal`。普通 FD 路径取消会移除监听并关闭查询 fd，但不能撤销已经进入的业务回调。固定 r1 的组合查询还存在更具体的边界：额外等待到期后，`HttpsEndpointAccumulator` 在 Handler 线程直接调用 `reportResult()`，没有重新经过传入的 Executor；该超时路径在报告入口也没有再次检查用户取消信号。因此业务应在最终回调入口重新检查取消和网络会话代次，并自行切换到所需执行环境，不能只依赖“取消后绝不回调”或“所有结果均在同一 Executor”的假设。这是固定源码的控制流核对，未以真机复现代替实际模块验证。[来源：r1 组合查询聚合器](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/util/HttpsEndpointAccumulator.java)。

<!-- gracker-diagram: ch12-02-06-cancel-session-guard -->
![取消查询与已排定回调的会话校验](../../assets/diagrams/ch12/ch12-02-06-cancel-session-guard.png)

图：取消底层查询后，业务回调入口仍校验取消和网络会话代次。 固定r1超时分支未重查用户取消；图表达源码可能路径，未声称设备复现或每次取消后都会回调。

迁移到新构造方法后，可按应用生命周期复用 resolver，避免每次创建线程；长期实例使用适当生命周期的 Context。提供自有 Looper 时，要在待处理查询取消或收尾后再退出线程。API 级别或扩展版本判断仍须保留，不能把 targetSdk 升级当作旧系统自动获得新 API。

### 3.2 `query()`、`rawQuery()` 与错误信息

普通地址查询用 `query()`：不指定地址类型的重载按目标网络的 IPv4/IPv6 能力发起相应 A/AAAA 查询，聚合并按 RFC 6724 排序；指定类型的重载可单独查询地址记录。`rawQuery()` 则返回原始 DNS 应答，供需要指定报文或自行解析记录的调用方使用；A/AAAA/HTTPS 组合重载另见下节。

两类 API 都使用 `Callback.onAnswer(answer, rcode)` 或 `onError(DnsException)`；rcode 并非 raw query 独有。差别在 answer 的类型：地址查询是 `List<InetAddress>`，raw query 是 `byte[]`，组合查询是 `HttpsEndpoint`。A/AAAA 聚合中只要有一项有效成功，最终 rcode 可为 0，掩盖另一项失败；`onAnswer` 也可能携带空结果或非零 rcode，不能仅按回调名判为解析成功。

<!-- gracker-diagram: ch12-02-07-query-result-contract -->
![query、rawQuery 与组合查询的返回类型](../../assets/diagrams/ch12/ch12-02-07-query-result-contract.png)

图：按返回类型与rcode/异常一起解释结果，不用回调名代替成功判定。 普通地址query也有rcode；A/AAAA聚合成功可遮盖另一项失败，空结果与非零rcode都须保留。

常规路径会把失败信息折叠。`InetAddress` 与 OkHttp 经常把多种解析失败统一成 `UnknownHostException`，从这个异常反推不出 NXDOMAIN（域名不存在）、SERVFAIL（服务器处理失败）、超时还是本地策略拒绝。

`FLAG_NO_CACHE_LOOKUP`、`FLAG_NO_CACHE_STORE` 和 `FLAG_NO_RETRY` 属于诊断或特定协议策略，不适合为了“更实时”而长期全量开启。缓存旁路会增加延迟、流量与 resolver 压力；若要对比缓存与上游行为，应控制样本量，并把实验请求与用户请求分开标记。

### 3.3 API 37 的 HTTPS 资源记录组合查询

API 37 与 S 扩展版本 22 增加 `TYPE_HTTPS`、`HttpsEndpoint` 和 A/AAAA/HTTPS 组合查询。`HttpsEndpoint.getHttpsRecords()` 按 SvcPriority 排序；`getIpAddresses()` 按 RFC 6724 排序并限制为当前网络支持的地址族，地址可来自 A/AAAA 或 HTTPS hints。每条 `HttpsRecord` 才承载 ALPN、端口、目标名称和 ECH 配置等信息。`getIpAddressHints()` 可包含当前网络不支持的地址族；AliasMode（优先级 0）也不具有普通 ServiceMode 的完整服务参数，连接实现须继续遵循记录语义。

<!-- gracker-diagram: ch12-02-08-https-record-endpoint -->
![HttpsEndpoint、服务参数与地址 hints](../../assets/diagrams/ch12/ch12-02-08-https-record-endpoint.png)

图：区分Endpoint的可用地址集合与每条HttpsRecord的服务参数。 API37/S扩展22；hints不等于已连通地址，AliasMode优先级0不同于普通ServiceMode，记录语义由连接实现处理。

`httpsTimeoutMillis` 控制地址结果完成后的 HTTPS **额外等待**，提供以下常量与显式时长：

- `HTTPS_QUERY_WAIT_NONE`：相关 A/AAAA 已收到结果而 HTTPS 尚未返回时，不再额外等待；它不禁用 HTTPS 查询，已经先到的 HTTPS 记录仍可使用；
- `HTTPS_QUERY_WAIT_AUTO`：使用平台默认额外等待；固定 r1 的值为 50 ms，属于实现参数，不能当成跨模块版本不变的性能结论；
- `HTTPS_QUERY_WAIT_UNTIL_TIMEOUT`：不启动上述额外等待截止，继续等待 HTTPS 查询自身完成或 resolver 超时；
- 显式非负毫秒数：在相关地址结果完成后，最多再等该时长；它不约束此前 A/AAAA 的等待。

如果 HTTPS 记录先到，并为当前网络需要的地址族提供足够 hints，固定 r1 可提前返回并取消剩余查询；不要求每次都等齐三类结果。若地址查询先完成，则按上面的额外等待策略处理；HTTPS 返回无数据或等待到期时，记录列表可为空。`UNTIL_TIMEOUT` 遇到上游丢弃 HTTPS 查询可能延长等待，业务端到端期限须独立管理，不能把额外等待参数当成完整 DNS 超时。

<!-- gracker-diagram: ch12-02-09-https-wait-policy -->
![HTTPS 额外等待与提前返回路径](../../assets/diagrams/ch12/ch12-02-09-https-wait-policy.png)

图：足够地址信息就绪后，按HTTPS已完成与等待策略决定交付。 AUTO固定r1默认50ms是额外等待参数，不是完整查询timeout；HTTPS先到且hints足够可早返并取消剩余查询。轨道非实测。

OkHttp 5.3 的 `Dns.lookup()` 只返回 `List<InetAddress>`。即使把 `HttpsEndpoint` 查询结果塞进自定义 `Dns`，也无法传递 ALPN、端口、优先级或 ECH 配置。需要使用这些元数据时，网络库的连接实现必须显式支持它们。

<!-- gracker-diagram: ch12-02-10-dns-list-metadata-loss -->
![OkHttp Dns 接口与 HTTPS 元数据](../../assets/diagrams/ch12/ch12-02-10-dns-list-metadata-loss.png)

图：返回IP列表的接口不能独立传递服务优先级、端口、ALPN或ECH。 解析到HttpsEndpoint不等于网络库已使用其服务参数；连接栈必须显式接入，不能把配置开关当协商证据。

## 四、Android 17 的系统调用路径

下面的时序图用于定位网络创建、DNS 配置与应用查询分别由谁处理。

<!-- gracker-diagram: ch12-02-11-network-cache-lifecycle -->
![Network 与 Resolver 缓存的创建销毁](../../assets/diagrams/ch12/ch12-02-11-network-cache-lifecycle.png)

图：同一netId由两个服务分别管理网络对象与DNS缓存。 固定r1正常路径，分别处理异常而非原子事务；销毁两次调用之间还有地址/socket清理。原Mermaid源码保留在下方。

```mermaid
sequenceDiagram
    participant NA as NetworkAgent
    participant CS as ConnectivityService
    participant ND as netd
    participant DM as DnsManager
    participant DR as DNS Resolver
    participant APP as App

    NA->>CS: LinkProperties / NetworkCapabilities
    CS->>ND: networkCreate(config)
    CS->>DR: createNetworkCache(netId)
    CS->>DM: noteDnsServersForNetwork(netId, lp)
    DM->>DR: setResolverConfiguration(params)
    CS-->>APP: network callbacks
    APP->>DR: getaddrinfo / query / rawQuery
    CS->>ND: networkDestroy(netId)
    CS->>DR: destroyNetworkCache(netId)
```

图中展示两组职责和一次正常生命周期的概念顺序，省略错误恢复、重复配置及网络回调交错。netd 维护 native network 对象与转发规则，resolver 为同一 `netId` 建立缓存并接收配置。应用查询数据路径通常经 JNI/NDK 与本地 `dnsproxyd` socket，不应把图中的 App→Resolver 连线误读成应用直接调用配置 Binder `IDnsResolver`。应用回调也不能证明网络库已经停止复用旧连接。

### 4.1 网络创建与销毁

在固定 r1 的正常创建路径中，`ConnectivityService` 先调用 `mNetd.networkCreate(config)`，再调用 `mDnsResolver.createNetworkCache(netId)`；它们不是一次原子事务。销毁路径先调用 `networkDestroy(netId)`，中间还会进行地址/socket 清理，再调用 `destroyNetworkCache(netId)`。各调用分别处理异常，排错时不能仅凭其中一条成功日志认定另一侧也成功。

resolver 按网络隔离缓存，是为了避免 Wi-Fi 与蜂窝共用彼此不兼容的解析状态。应用自定义缓存也要守这条边界。只以 hostname（主机名）作为 cache key（缓存键）时，旧网络拿到的地址会继续用在新网络上，VPN 分流和企业域名最容易踩到。

### 4.2 DNS server 与 Private DNS 配置

`LinkProperties`（接口、路由、DNS 等链路属性）更新后，`ConnectivityService.updateDnses()` 把变化交给 `DnsManager.noteDnsServersForNetwork()`。`DnsManager` 生成用于跨进程传递配置的 `ResolverParamsParcel`，再经 `IDnsResolver.setResolverConfiguration()` 写入对应 `netId`。参数包括 DNS server、用于补全短主机名的搜索域、采样与超时配置、Private DNS 信息等。

DNS 配置变化时，`ConnectivityService.updateDnses()` 还会调用 `DnsManager.flushVmDnsCache()`，由后者发送系统保护的 `ACTION_CLEAR_DNS_CACHE` 广播通知 Java 运行时丢弃进程内 DNS 结果。这里至少要区分 resolver 的每网络 native cache、Java 或应用自己的解析缓存，以及网络库里的已建连接；广播不能保证清除任意自定义缓存。

<!-- gracker-diagram: ch12-02-12-dns-config-update -->
![LinkProperties 更新到配置 Binder 与 VM 广播](../../assets/diagrams/ch12/ch12-02-12-dns-config-update.png)

图：链路DNS变化通过DnsManager写入每网络配置，并单独通知VM刷新。 配置与刷新不是应用全部缓存的统一失效机制；广播不保证清理自定义resolver缓存，socket生命周期另管。

单独清理 DNS 缓存不会自动关闭 OkHttp 连接池中的 socket。切网后“解析已更新但请求仍访问旧地址”可能与已有连接、socket 绑定或其他缓存有关，不能无统计依据断言多数由复用造成。完整网络销毁则是另一条路径，ConnectivityService 可能主动清理相关 socket；需联合 connect、实际目标地址和绑定网络判断。

<!-- gracker-diagram: ch12-02-13-dns-caches-connections -->
![DNS 缓存失效与已有连接的独立生命周期](../../assets/diagrams/ch12/ch12-02-13-dns-caches-connections.png)

图：分别观测resolver缓存、进程解析结果和已建立socket。 DNS刷新不等于关闭连接；完整网络销毁可能另行清socket，解析地址更新也不能单独证明请求已换路径。

### 4.3 服务接口与 Android 17 源码位置

Android 17 的关键锚点如下。模块根目录分别为 `packages/modules/Connectivity`、`packages/modules/DnsResolver` 与 `system/netd`；文件链接保留固定 r1 的完整路径，避免长路径撑宽表格。

| 职责 | 模块 | 源码文件 |
|---|---|---|
| Framework DNS API | Connectivity | [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) |
| 网络生命周期协调 | Connectivity | [`ConnectivityService.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/ConnectivityService.java) |
| resolver 参数生成 | Connectivity | [`DnsManager.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/connectivity/DnsManager.java) |
| Binder 接口 | DnsResolver | [`IDnsResolver.aidl`](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/binder/android/net/IDnsResolver.aidl) |
| resolver 服务与 dump | DnsResolver | [`DnsResolverService.cpp`](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/DnsResolverService.cpp) |
| resolver 配置与统计 | DnsResolver | [`ResolverController.cpp`](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/ResolverController.cpp) |
| DoT/DoH 状态 | DnsResolver | [`PrivateDnsConfiguration.cpp`](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/PrivateDnsConfiguration.cpp) |
| native 网络管理 | netd | [`NetdNativeService.cpp`](https://android.googlesource.com/platform/system/netd/+/refs/tags/android-17.0.0_r1/server/NetdNativeService.cpp) |

遇到把 Android 10 的 `system/netd/resolv` 当作当前目录的资料，保留它的迁移史结论，再回到上表的 Android 17 文件核对实现。

## 五、Private DNS、DoT、DoH 与 `.local`

### 5.1 用户设置名称不能直接代表内部传输

Android 的公开 Private DNS 设置向用户展示 DoT 模式和 provider hostname（提供商主机名）。Android 17 的 resolver 内部同时存在 DoT 与 DNS-over-HTTPS（DoH，通过 HTTPS 发送 DNS 查询）的配置、验证和统计代码，DoH 实现还包括 `packages/modules/DnsResolver/rust/src/doh/`。内部采用哪种加密传输，受平台版本、provider 与实验配置影响。

应用从 `InetAddress`、OkHttp `Dns` 或普通 `DnsResolver.query()` 回调里不能可靠判断单次查询使用 DoT 还是 DoH。普通公开状态可记录 `LinkProperties.isPrivateDnsActive()` 与 `getPrivateDnsServerName()`；已验证服务器详情和实际传输路径应从有权访问的平台 dump、日志或内部状态核对，不能把 `getDnsServers()` 当作“本次实际使用的加密上游”。诊断报告应区分 Private DNS 状态、配置与单次实际传输。

<!-- gracker-diagram: ch12-02-14-private-dns-signals -->
![Private DNS 设置、配置与单次实际传输](../../assets/diagrams/ch12/ch12-02-14-private-dns-signals.png)

图：公开状态说明PrivateDNS语境，DoT/DoH实际路径需要平台证据。 getDnsServers不是本次加密上游清单；Java地址回调不能可靠识别DoT/DoH，模块/配置/实验会影响内部选择。

Private DNS 保护系统 resolver 到上游 DNS provider 之间的 DNS 流量。它不替代 HTTPS，也不自动隐藏 TLS ClientHello 中的服务器名称；ECH 的适用条件见 12.1。

### 5.2 应用 DoH 是另一套解析策略

应用自带 DoH 后，上游、缓存、bootstrap 和 fallback 都由应用维护，可能不使用系统 Private DNS、VPN DNS 命名空间、企业 split DNS 与门户网络的解析策略。这不等于 DoH 数据流必然绕过 VPN 隧道；实际路由还取决于进程/socket 绑定、VPN 覆盖和系统规则。安全收益、泄露面与兼容成本应分别核实：

- 公网固定域名可按业务策略使用应用 resolver；
- 企业内网域名、VPN 域名和门户网络优先遵循系统策略；
- fallback 是否允许从加密解析切到系统 DNS，应由安全与隐私策略定义；
- DoH 服务自身的域名解析不能再次调用同一个业务客户端，否则会形成无法完成的递归依赖。

<!-- gracker-diagram: ch12-02-15-app-doh-bootstrap -->
![应用 DoH 的 bootstrap、回退与网络策略](../../assets/diagrams/ch12/ch12-02-15-app-doh-bootstrap.png)

图：应用自管上游和缓存时，独立解决bootstrap并明确fallback政策。 不采用VPN DNS命名空间不等于绕开VPN数据隧道；实际路由、隐私和企业域名需要分别核实。

### 5.3 mDNS 与 Android 17 本地网络权限

支持该功能的 DNS Resolver 模块可对 `.local` 名称发起一次性 mDNS 查询，适用于已知名字的地址解析。官方模块文档与固定 r1 `res_cache.cpp` 都排除蜂窝和 VPN 网络；不能把“系统支持 .local”推广到任意 Network。它也不提供 NSD 那样持续发现与跟踪服务的生命周期。

Android 17 上 targetSdk 37 的广泛本地网络访问需要 `ACCESS_LOCAL_NETWORK` 运行时授权，`.local` 解析也在限制范围内。官方还提供由 NSD 系统 picker 选择设备并授予限定访问的路径，不能把该有限授权等同于任意 LAN 或任意 `.local` 查询权限。TCP、UDP、OkHttp、Cronet 与 WebView 的本地访问均须核实适用规则；失败时先检查运行系统、target、实际授予范围与目标网络。

<!-- gracker-diagram: ch12-02-16-mdns-nsd-permission -->
![一次性 mDNS、持续 NSD 与局域网授权](../../assets/diagrams/ch12/ch12-02-16-mdns-nsd-permission.png)

图：分开已知名字解析、服务发现生命周期和实际访问授权。 系统.local mDNS排除VPN/蜂窝；picker授予限定设备访问，不能推广为任意LAN或任意.local解析权限。

## 六、从业务错误到系统证据的诊断顺序

### 6.1 先确认请求是否停在 DNS

一次请求至少记录这些相邻事件：

1. DNS 开始、结束或失败；
2. connect（连接）开始、目标地址与结束；
3. TLS 握手开始、结束；
4. HTTP 请求头发送、库读到响应头的事件与响应消费终态；若测 wire 首字节，另记对应数据源，不能直接用 OkHttp `responseHeadersStart` 代替；
5. 取消、网络切换和进程生命周期事件。

复用已有连接时，没有 DNS 与 connect 事件属于正常现象。若 DNS 很快而 connect 超时，应检查路由、地址族与目标 IP；若 TLS 慢，回到 12.1 检查握手与证书；若首字节慢，应检查服务端、CDN 与回源链路。

<!-- gracker-diagram: ch12-02-17-failure-stage-routing -->
![先定位请求阶段，再选择 DNS 或连接证据](../../assets/diagrams/ch12/ch12-02-17-failure-stage-routing.png)

图：从实际阶段事件分流DNS、路由、TLS与服务端问题。 复用可能跳过阶段，跨主机合并仍可能先解析；OkHttp头事件不等于wire首字节，缺席也不能填0ms。

### 6.2 记录故障对应的网络上下文

每次故障至少关联：

- 应用进程内的网络会话标识；
- Wi-Fi、蜂窝、VPN 等传输类型；
- `NetworkCapabilities` 中的 `VALIDATED`（系统公网探测通过）与 `CAPTIVE_PORTAL` 等标志；这些不能保证业务域名、TLS 或服务端正常；
- `LinkProperties` 中的接口、DNS server 数量和 Private DNS 状态；
- 默认网络变化到请求开始之间的时间；
- 查询来源：系统、HTTPDNS、应用 DoH 或缓存。

`netId` 由系统重复分配，同一个值可能先后属于不同网络，它只是平台内部标识，不能当成稳定的设备属性。线上长期聚合可以用进程内递增的网络会话号，或使用带定期更换盐值的标识。

<!-- gracker-diagram: ch12-02-18-network-session-context -->
![按网络会话关联解析与实际连接](../../assets/diagrams/ch12/ch12-02-18-network-session-context.png)

图：一次故障关联请求、网络会话、解析来源与连接结果。 netId可复用，不能当稳定设备属性；VALIDATED是系统探测通过，不能保证业务host正常。

### 6.3 三组 shell 证据

下面的命令用于受控测试设备，或已经获准收集 bugreport（系统诊断包）的环境；resolver dump（状态转储）需要 `DUMP` 权限，普通第三方应用不能在生产设备中自行执行。

```shell
adb shell dumpsys connectivity
adb shell dumpsys dnsresolver
adb shell dumpsys dnsresolver querylog
```

<!-- gracker-diagram: ch12-02-19-three-dump-evidence -->
![三组 dumpsys 证据的用途与范围](../../assets/diagrams/ch12/ch12-02-19-three-dump-evidence.png)

图：系统网络、resolver状态与querylog各自提供不同层次的证据。 受控shell/bugreport取证，服务dump需要DUMP权限；三者都不能替代应用每次请求的阶段计时。

第一条核对网络、LinkProperties、能力、VPN 与 Private DNS。第二条是 resolver 的每网络配置、缓存相关信息、上游采样统计与 Private DNS 状态，不能当作完整缓存条目或应用请求清单。第三条输出有界 query log：固定 r1 的 DnsProxyListener 跳过反向查询，主要记录存在缓存未命中事件的查询；DnsQueryLog 输出 hostname 首字符和首个 IPv4/IPv6 地址的前缀，同时保留时间、netId、UID/PID 与耗时。遮蔽不等于匿名，也不保证记录所有业务请求。

<!-- gracker-diagram: ch12-02-20-querylog-scope-redaction -->
![querylog 的记录条件与残留字段](../../assets/diagrams/ch12/ch12-02-20-querylog-scope-redaction.png)

图：先检查查询是否进入日志，再理解遮蔽后的信息与局限。 固定r1跳过反向查询，纯缓存命中不记该日志；hostname首字符和地址前缀、时间/UID/PID等仍可识别关联。

`ResolverController::dump()` 的 server 数字由 resolver 保存的样本聚合，包含成功、错误、超时、内部错误、平均 RTT、最近样本时间和可用状态；样本受配置的有效期与数量约束，“total”不是设备生命周期全部 DNS 请求。它适合观察对应网络和上游的集中失败，不能替代应用耗时或分位数；应用可能命中其他缓存、等待调度或复用连接。

<!-- gracker-diagram: ch12-02-21-resolver-statistics-scope -->
![Resolver 上游样本统计与应用分位数](../../assets/diagrams/ch12/ch12-02-21-resolver-statistics-scope.png)

图：按样本窗口解释上游total/平均RTT，并与应用延迟分布分开。 样本受有效期和数量约束；平均RTT不是p99，也不包含应用全部缓存、排队与连接复用的体验。

### 6.4 NetworkDiagnostics 能证明什么

固定 r1 的 `NetworkDiagnostics` 将探测 socket 绑定到指定 Network，按其 LinkProperties、路由和 Private DNS 配置准备 ICMP、UDP DNS 与 DoT 检查。DoT 检查确实包含到 853 端口的连接、TLS 握手和 DNS 报文交换；但它不是对业务 HTTPS、ECH、DoH 或企业域名语义的完整验证，也不能因为未出现某类检查就断言该协议不可用。

这类平台探测能缩小系统网络故障范围，但不能证明业务域名、CDN 地址或应用 HTTPDNS 正常。应用问题仍要把平台探测结果与同一时间的 hostname 类别、查询来源和 connect 目标关联。

<!-- gracker-diagram: ch12-02-22-network-diagnostics-probes -->
![NetworkDiagnostics 的绑定探测与证明范围](../../assets/diagrams/ch12/ch12-02-22-network-diagnostics-probes.png)

图：平台在指定Network上执行配置相关的探测，业务端点仍需自己的证据。 固定r1按LinkProperties/路由/PrivateDNS准备ICMP、UDP DNS、DoT；不是业务HTTPS、DoH、ECH或HTTPDNS成功证明。

### 6.5 常见现象的证据分流

| 现象 | 优先核对 | 暂时不要推断 |
|---|---|---|
| `UnknownHostException` 增长 | 使用的解析入口、网络会话、resolver/HTTPDNS 结果、超时与取消 | 一定是 NXDOMAIN |
| DNS 高分位延迟增长 | 冷缓存请求（查询时没有可用缓存结果）比例、上游 server RTT、网络切换、线程排队、查询类型 | 换 HTTPDNS 一定更快 |
| 切网后第一个请求失败 | socket 是否复用旧网络、缓存是否带网络维度、新网络是否验证 | DNS 缓存一定污染 |
| VPN 下公网正常、内网域名失败 | VPN DNS、split DNS、绑定的 `Network`、应用 DoH/HTTPDNS 覆盖 | 运营商 DNS 劫持 |
| DNS 成功但 `VALIDATED` 丢失 | Captive Portal、路由、HTTP 探测、Private DNS 校验 | 网络已经可用 |
| `.local` 失败 | API 37 本地网络权限、目标网络、mDNS 适用范围 | 公网 DNS server 故障 |

## 七、HTTPDNS 与 OkHttp 自定义 `Dns`

系统 resolver 与 HTTPDNS 解决不同问题。系统路径继承 `Network`、VPN、Private DNS 与平台缓存策略；HTTPDNS 能提供业务域名调度和独立的上游服务。接入 HTTPDNS 之后，网络隔离、TTL（Time to Live，缓存有效期）、并发、bootstrap 和 fallback 都要应用自己维护。

OkHttp 的 `Dns.lookup(hostname)` 是同步接口，并且可能被多个请求并发调用。可执行的实现边界包括：

- `lookup()` 内优先读取线程安全的内存缓存；
- 缓存 key 至少包含 hostname 与网络会话，必要时加入地址族和用户网络策略；
- TTL 遵循 DNS/HTTPDNS 服务协议；NXDOMAIN、NODATA 与瞬时超时、SERVFAIL、权限或取消分别分类，不能把所有查询失败按同一负缓存期限保存；
- 缓存缺失时若要同步访问 HTTPDNS，这段耗时会进入建连前的 DNS 阶段；
- 异步预取应由明确的业务触发，过期结果不能无限续用；
- 持久化地址只适用于能正确保存 TTL、网络分区和数据版本的设计，默认优先使用内存；
- HTTPDNS 客户端使用独立、最小化的 bootstrap 路径，不能递归调用同一个自定义 `Dns`；
- 系统 fallback 由产品的可用性、隐私和企业网络策略共同决定。

<!-- gracker-diagram: ch12-02-23-httpdns-cache-bootstrap -->
![同步 Dns.lookup 的并发缓存与上游路径](../../assets/diagrams/ch12/ch12-02-23-httpdns-cache-bootstrap.png)

图：同步并发lookup优先使用安全的分区缓存，上游访问受bootstrap和回退政策约束。 同步HTTPDNS耗时计入建连前DNS；权威否定与瞬时错误分别缓存，不能无限续用过期地址或递归调用自身。

使用解析得到的 IP 建立连接时，URL 仍应保留原始 hostname，让 TLS SNI（握手中携带的目标主机名）、证书主机名校验和 HTTP Host 保持一致。直接把 URL 改为 IP，再关闭主机名校验，属于安全缺陷。

<!-- gracker-diagram: ch12-02-24-dns-ip-domain-identity -->
![DNS 地址候选与 HTTPS 域名身份](../../assets/diagrams/ch12/ch12-02-24-dns-ip-domain-identity.png)

图：自定义地址调度保持URL域名，连接地址与身份语义分别处理。 仅替换裸IP并关闭校验是安全缺陷；只补Host头也不能自动恢复SNI和证书验证的目标身份。

连接池会改变 DNS 统计：已有连接直接可用时通常跳过 `lookup()`，但 OkHttp 5.3.0 为检查跨主机 HTTP/2 合并路由，也可能先解析再复用同一连接，因此不能用“有 DNS 事件”推出“必有新连接”。多地址的尝试与回退由连接策略决定。应联合 DNS、connect 与 connectionAcquired 记录，完整边界见 12.1 与 24.7。

<!-- gracker-diagram: ch12-02-25-dns-before-coalescing -->
![有 DNS 事件仍可能复用 HTTP/2 连接](../../assets/diagrams/ch12/ch12-02-25-dns-before-coalescing.png)

图：跨主机HTTP/2合并可能先解析路由，再判断已有连接是否可用。 固定OkHttp5.3.0；同host直接复用可跳过解析，但有DNS不能推出必然新connect，实际顺序以事件为准。

## 八、指标、日志与告警

### 8.1 分位数应服务于 SLO

中位数、p90、p95 和 p99 描述的是不同百分位的延迟，p90 表示 90% 的样本延迟不超过该值。分位数按业务请求量和 SLO（Service Level Objective，服务等级目标）来选；低流量域名的 p99 波动很大，固定套用只会制造噪声。聚合时至少要区分：

- 解析来源与缓存状态；
- 网络传输类型、VPN 和 Private DNS 状态；
- 冷启动、前后台与网络切换会话；
- A、AAAA、HTTPS 等查询类型；
- 成功、空结果、超时、取消和可获得的 rcode；
- DNS 结束后的 connect 成功、失败及地址族。

DNS 分位数以实际发生的解析事件为样本；未解析而复用连接的请求，应记为阶段未发生，不能填 0 ms 混入分布。另报 DNS 触发率、缓存命中率、样本数和失败率，避免仅用成功样本解释总体体验。“切网后故障”也不套通用秒数：记录 `elapsed_since_default_network_change_ms`，按线上分布与期限划窗口，并分开复用与新连接。

<!-- gracker-diagram: ch12-02-26-dns-metric-denominators -->
![DNS 分布、触发率与业务体验的分母](../../assets/diagrams/ch12/ch12-02-26-dns-metric-denominators.png)

图：先确认解析是否发生，再按来源、网络、类型和结果计算分布。 未解析不填0ms，失败不从体验结论中消失；低样本p99需要样本数，不能把单个平均RTT当尾延迟。

### 8.2 最小事件字段

一条解析事件可包含：

| 字段 | 用途 |
|---|---|
| `request_id` / `trace_id` | 与 connect、TLS、HTTP 阶段关联 |
| `network_session_id` | 区分切网前后的解析和连接 |
| `resolver_source` | system、HTTPDNS、app DoH、memory cache |
| `query_type` | A、AAAA、HTTPS 或组合查询 |
| `duration_ms` | 查询或缓存读取耗时 |
| `result_count` / `address_family` | 判断空结果与地址族变化 |
| `error_stage` / `error_class` / `rcode` | 在 API 能提供时区分失败 |
| `fallback_from` / `fallback_to` | 评估降级是否有效 |
| `connect_outcome` | 验证解析结果能否建立连接 |

完整 hostname、DNS server、返回 IP 和 provider name 都可能成为敏感网络信息。生产埋点可使用服务端分配的域名类别、受控 allowlist（明确允许采集的列表）、轮换 HMAC（使用定期更换的密钥生成消息认证码）或网段级分类；诊断包的访问权限、保留时间和导出范围也要受控。哈希前若候选域名很少，攻击者仍可能离线枚举并恢复原值，因此无盐散列不能视为匿名化。

<!-- gracker-diagram: ch12-02-27-dns-fields-privacy -->
![解析事件字段与敏感网络数据处理](../../assets/diagrams/ch12/ch12-02-27-dns-fields-privacy.png)

图：关联请求、网络会话和解析结果，并限制可识别网络字段。 无盐散列在低熵域名集合中可被枚举；轮换HMAC或类别化也不自动消除关联风险，诊断包仍按授权范围管理。

### 8.3 告警要能指向动作

| 告警信号 | 关联证据 | 可能的处置方向 |
|---|---|---|
| system DNS 超时上升 | 按网络和运营商分组的统计、resolver RTT、Private DNS 状态 | 核对特定网络或 provider |
| HTTPDNS fallback 上升 | HTTPDNS 服务耗时、bootstrap、缓存过期 | 隔离服务故障或调整预取 |
| DNS 正常但 connect 失败 | 返回地址族、目标 IP 分类、路由和连接池 | 检查地址可达性与旧连接 |
| 切网会话错误集中 | 网络变化间隔、缓存来源、连接是否复用 | 修正网络维度缓存或客户端生命周期 |
| 企业/VPN 用户异常 | VPN、代理、split DNS、应用 resolver 覆盖 | 缩小自定义解析范围 |

<!-- gracker-diagram: ch12-02-28-dns-alert-action -->
![从告警现象到可验证的处置](../../assets/diagrams/ch12/ch12-02-28-dns-alert-action.png)

图：按来源和失败阶段选择证据，使告警能指向具体动作。 相同UnknownHost或切网标签不自动说明同一根因；调整策略前核实窗口、样本与配置变化。

## 九、Tethering offload 不属于本机 DNS 路径

硬件 tethering offload 加速的是下游设备经手机转发的 IP 流量，不是本机应用的 Java/NDK 名称查询本身。但热点 DNS 不能因此排除：下游客户端可能使用手机提供的 DNS 转发服务或自行连接上游，固定 r1 同时可见 netd 的 legacy DNS proxy 配置和 IDnsResolver 的 `setDnsForwarding` 接口。具体路径取决于 Tethering 实现与配置，需与硬件数据转发分别核实。

反馈来自热点下游设备时，先判断失败发生于其自身解析、手机 DNS 转发、上游选择还是数据转发/NAT/offload，再沿实际路径取证；本机应用则从 Network、LinkProperties、resolver、应用缓存与连接池定位。两个场景可以共享上游故障，但不能仅因都涉及 netd 就使用同一条调用链解释。

<!-- gracker-diagram: ch12-02-29-tethering-dns-offload -->
![本机解析、热点 DNS 转发与硬件 offload](../../assets/diagrams/ch12/ch12-02-29-tethering-dns-offload.png)

图：本机API解析与下游DNS转发、IP数据加速分别定位。 固定r1可见legacy DNS proxy和IDnsResolver转发接口，具体启用路径依Tethering配置；硬件offload不等于执行本机DNS查询。

## 小结

Android 17 的 DNS 诊断以 `Network` 为主线串起证据链。`ConnectivityService` 协调网络生命周期，netd 管理平台内部网络，DNS Resolver 主线模块维护每个 `netId` 的配置、缓存和 Private DNS，应用网络库决定查询时机、连接复用与自定义解析策略。

排查时先确认请求是否发生 DNS，再记录对应的网络会话和解析来源；随后使用客户端阶段事件、`dumpsys connectivity`、`dumpsys dnsresolver` 与脱敏 query log（查询日志）相互印证。HTTPDNS 或应用 DoH 能补充业务调度与安全策略，但接入时仍要设计 TTL、网络隔离、bootstrap、企业网络兼容和隐私保护。

## 参考资料

- [DNS Resolver 模块](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
- [`DnsResolver` API 参考](https://developer.android.com/reference/android/net/DnsResolver)
- [`HttpsEndpoint` API 参考](https://developer.android.com/reference/android/net/dns/HttpsEndpoint)
- [Android 17 本地网络权限](https://developer.android.com/privacy-and-security/local-network-permission)
- [NDK Networking API](https://developer.android.com/ndk/reference/group/networking)
- [`DnsResolver.java`（Android 17）](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/framework/src/android/net/DnsResolver.java)
- [`ConnectivityService.java`（Android 17）](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/service/src/com/android/server/ConnectivityService.java)
- [`DnsManager.java`（Android 17）](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/service/src/com/android/server/connectivity/DnsManager.java)
- [`NetworkDiagnostics.java`（Android 17）](https://android.googlesource.com/platform/packages/modules/Connectivity/+/android-17.0.0_r1/service/src/com/android/server/connectivity/NetworkDiagnostics.java)
- [`IDnsResolver.aidl`（Android 17）](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/binder/android/net/IDnsResolver.aidl)
- [`DnsResolverService.cpp`（Android 17）](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/DnsResolverService.cpp)
- [`ResolverController.cpp`（Android 17）](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/ResolverController.cpp)
- [`DnsQueryLog.cpp`（Android 17）](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/DnsQueryLog.cpp)
- [`PrivateDnsConfiguration.cpp`（Android 17）](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/PrivateDnsConfiguration.cpp)
- [`NetdNativeService.cpp`（Android 17）](https://android.googlesource.com/platform/system/netd/+/android-17.0.0_r1/server/NetdNativeService.cpp)
- [OkHttp `Dns.kt`（5.3.0）](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt)
- [`HttpsEndpointAccumulator.java`（固定 r1，额外等待、回调与取消边界）](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/util/HttpsEndpointAccumulator.java)
- [`HttpsRecord` API](https://developer.android.com/reference/android/net/dns/HttpsRecord)
- [`DnsProxyListener.cpp`（固定 r1，查询 socket 与 querylog 范围）](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/DnsProxyListener.cpp)
- [`res_cache.cpp`（固定 r1，网络缓存与 mDNS 网络限制）](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/res_cache.cpp)
- [`LinkProperties` 公开 API](https://developer.android.com/reference/android/net/LinkProperties)
- [Tethering hardware offload](https://source.android.com/docs/core/data/tethering-offload)
