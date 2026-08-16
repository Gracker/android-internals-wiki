---
title: "Android 17 ECH 与 domainEncryption 网络适配"
chapter: "24.15"
section: "24.15"
status: finalized
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [network, tls, ech, android17, network-security-config]
related_chapters: ["12.2", "24.4", "24.5", "24.14"]
last_verified: "2026-08-15"
last_verified_against: "Android 17 stable behavior changes / Network Security Configuration and API reference 2026-08 / RFC 9849 / RFC 9460 / OkHttp and Chromium upstream"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://developer.android.com/about/versions/17/features"
  - type: official
    path: "https://developer.android.com/reference/android/net/DnsResolver"
  - type: official
    path: "https://developer.android.com/reference/android/net/dns/HttpsRecord"
  - type: official
    path: "https://developer.android.com/reference/android/net/ssl/SSLSockets"
  - type: official
    path: "https://developer.android.com/reference/android/net/ssl/SSLEngines"
  - type: official
    path: "https://developer.android.com/reference/android/net/ssl/EchConfigMismatchException"
  - type: official
    path: "https://developer.android.com/reference/android/security/NetworkSecurityPolicy"
  - type: rfc
    path: "https://www.rfc-editor.org/rfc/rfc9849"
  - type: rfc
    path: "https://www.rfc-editor.org/rfc/rfc9460"
  - type: upstream
    path: "https://github.com/lysine-dev/okhttp/pull/9573"
  - type: upstream
    path: "https://github.com/lysine-dev/okhttp/pull/9596"
  - type: upstream
    path: "https://github.com/lysine-dev/okhttp/tree/parent-5.4.0"
  - type: upstream
    path: "https://chromium.googlesource.com/chromium/src/net/+/40d5138e2f148890a937d6653284074cd3c3676d"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]"
pipeline_stage: finalized
---

# Android 17 ECH 与 domainEncryption 网络适配

## 适配范围

Android 17 / API 37 为网络库提供了加密客户端问候（Encrypted Client Hello，ECH）所需的域名解析（DNS）、传输层安全协议（TLS）和按域名策略接口。ECH 会加密 TLS 初始握手中的敏感字段，主要是服务器名称指示（Server Name Indication，SNI）。

`domainEncryption` 是 Android 网络安全配置中的 XML 元素。应用把目标系统版本 `targetSdkVersion` 设为 37 时，它的默认模式从 `disabled` 变为 `enabled`。这个默认值只表达应用策略。网络库仍须读取策略、从 DNS 的 HTTPS 资源记录取得 ECH 配置，并在 TLS 握手中应用；使用平台 TLS 提供方（provider，Java 安全框架中的 TLS 实现组件）的网络库可以调用 Android 17 新增接口，自带 TLS 实现的网络库则要完成等价处理。服务端也要支持互联网标准 RFC 9849。

DNS 的 HTTPS 资源记录描述服务连接参数，与以 `https://` 开头的网页地址无关。HTTPS 最终能连通只说明连接路径可用；验收还要确认：

- 当前网络库版本是否已经接入 Android 17 ECH API。
- 设备使用的解析路径能否取得 HTTPS 资源记录中的 `ech` 参数。
- 服务端 ECH 配置、用于外层握手路由的公开名称、证书与轮换流程是否一致。
- 没有 ECH 配置、配置失配、代理拦截和证书透明度（CT）失败时分别发生什么。
- 连接复用、DNS 等待和协议切换是否改变业务耗时。

平台源码以 Android 开源项目（AOSP）的 `android-17.0.0_r1` 标签为基准。ECH 的 Android 实现位于用户空间的 DNS 与 TLS 组件，没有供应用调用的内核接口。TLS 1.3、证书链、连接池和 HTTP/2、HTTP/3 原理见 12.2、24.4 与 24.5。

## ECH 的 Android 17 适配边界

ClientHello 是客户端发出的第一条 TLS 握手消息，其中包含支持的算法和 SNI 等信息。ECH 把它拆成外层 `ClientHelloOuter` 和加密的 `ClientHelloInner`：真实 SNI 等敏感扩展位于内层，外层保留供服务端路由的公开名称。RFC 9849 还定义了配置失配后的重试信息和 ECH GREASE。GREASE 是内容随机的兼容性测试扩展，用来检查网络中间设备能否容忍 ECH 格式；它本身不会加密真实 SNI。

ECH 保护范围有限：

- 目标 IP 地址仍对网络路径可见。
- 公开名称仍会出现在外层 ClientHello。
- 使用明文 DNS 时，查询名称仍可能泄露；ECH 不替代加密 DNS。
- 流量大小、时序与连接目的地仍可用于流量分析。
- 客户端、服务端、代理与业务日志仍能看到各自处理的数据。

ECH 不会让域名对所有观察者不可见。网络库和服务端完成协商后，它只加密 ClientHello 内的真实 SNI 等字段，降低网络中间设备直接读取这些字段的能力。[RFC 9849](https://www.rfc-editor.org/rfc/rfc9849) 给出 ECH 协议细节，[RFC 9460](https://www.rfc-editor.org/rfc/rfc9460) 定义 HTTPS 与服务绑定（SVCB）资源记录。

采用 Android 17 平台 API 接入 ECH 的网络库，可按以下顺序处理：

1. 网络库通过 `NetworkSecurityPolicy.getDomainEncryptionMode(hostname)` 读取应用对目标域名的策略。
2. 网络库通过 `DnsResolver` 并发查询 IPv4 地址记录（A）、IPv6 地址记录（AAAA）和 HTTPS 记录，得到描述候选连接端点的 `HttpsEndpoint`。
3. `HttpsRecord.getEchConfigList()` 从服务模式（ServiceMode）的 HTTPS 记录中解析可选的 ECH 配置列表 `EchConfigList`。
4. 网络库在握手开始前调用 `SSLSockets.setEchConfigList()` 或 `SSLEngines.setEchConfigList()`。
5. 平台 TLS 实现发送 ECH ClientHello；服务端接受配置，或返回配置失配及可选的重试配置。

`domainEncryption` 只提供按域名策略，不会自动改造网络库。网络库还要完成 DNS 查询、握手配置和失配处理，Android 官方文档也把网络库已接入 ECH 列为生效前提。

## 在网络安全配置中声明 `domainEncryption`

网络安全配置（Network Security Configuration）是应用资源中的 XML 文件。`domainEncryption` 可放在 `base-config` 或 `domain-config` 下：`base-config` 是未被域名规则覆盖时使用的默认配置，`domain-config` 只匹配指定域名。多个规则同时匹配时，平台使用域名最长、范围最具体的一条；`includeSubdomains="true"` 会让规则覆盖该域名及各级子域。

这份 XML 明确声明全局启用，并为一个已知不兼容的网关域名禁用 ECH：

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config>
        <domainEncryption mode="enabled" />
    </base-config>

    <domain-config>
        <domain includeSubdomains="true">legacy-gateway.example.com</domain>
        <domainEncryption mode="disabled" />
    </domain-config>
</network-security-config>
```

这段配置要求支持该策略的网络库对普通域名使用 `enabled`；访问 `legacy-gateway.example.com` 及其子域时，不发送 ECH，也不发送 ECH GREASE。对 `targetSdkVersion 37` 的应用，平台默认已经是 `enabled`，显式写入 `base-config` 可以记录应用策略。

Android 17 正式版的 XML 语法只接受两个值：

| XML 模式 | 语义 |
| --- | --- |
| `enabled` | 握手获得 ECH 配置时使用 ECH；没有配置时启用 ECH GREASE |
| `disabled` | 不使用 ECH，也不使用 ECH GREASE |

`NetworkSecurityPolicy` 的公开常量还包含 `DOMAIN_ENCRYPTION_MODE_OPPORTUNISTIC` 与 `DOMAIN_ENCRYPTION_MODE_UNKNOWN`。`OPPORTUNISTIC` 表示有服务端配置时尝试 ECH、没有配置时不发送 GREASE；`UNKNOWN` 要求网络库退回普通 TLS。它们是网络库读取策略时可能遇到的 API 值，不是当前 XML 语法允许填写的字符串。网络安全配置中不能写 `mode="opportunistic"`。

这段诊断函数用于确认某个主机名经过 Network Security Configuration 匹配后得到的策略值：

```kotlin
@RequiresApi(37)
fun domainEncryptionMode(hostname: String): String {
    val mode = NetworkSecurityPolicy.getInstance()
        .getDomainEncryptionMode(hostname)

    return when (mode) {
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_DISABLED -> "disabled"
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_OPPORTUNISTIC -> "opportunistic"
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_ENABLED -> "enabled"
        NetworkSecurityPolicy.DOMAIN_ENCRYPTION_MODE_UNKNOWN -> "unknown"
        else -> "unrecognized:$mode"
    }
}
```

返回值只能证明平台解析出的策略，不能证明 DNS 返回了 ECH 配置，也不能证明某次 TLS 握手使用了 ECH。诊断日志不应记录完整 URL、查询参数或用户标识。

模式与默认值以 [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config#domain-encryption) 为准，API 常量见 [`NetworkSecurityPolicy`](https://developer.android.com/reference/android/security/NetworkSecurityPolicy)。

## Android 17 API 与源码边界

`DnsResolver` 在 API 37 增加了返回 `HttpsEndpoint` 的查询重载。它会并发发出 A、AAAA 和 HTTPS 查询，并允许调用方通过 `httpsTimeoutMillis` 指定地址记录完成后还要等待 HTTPS 记录多久。`DnsResolver.getInstance()` 在 API 37 已废弃，新代码应使用接收 `Context` 与 `Looper` 的构造函数。

`HttpsRecord` 表示 RFC 9460 的 HTTPS 记录。`priority == 0` 表示别名模式（AliasMode），只把查询指向另一个名称，不携带 IP 提示、端口、ALPN 或 ECH 配置。其他优先级表示服务模式（ServiceMode），可携带连接参数；ALPN 是应用层协议协商，用于声明 HTTP/1.1、HTTP/2 等可选上层协议。`getEchConfigList()` 可能返回 `null`，ECH 配置二进制格式无效时会抛出 `InvalidEchDataException`。

`SSLSocket` 封装基于套接字（socket）的 TLS 连接，`SSLEngine` 则提供不直接绑定套接字的 TLS 状态机。`SSLSockets.setEchConfigList()` 和 `SSLEngines.setEchConfigList()` 必须在握手开始前调用，而且只接受平台 TLS 实现创建的对应对象。自带 BoringSSL、OpenSSL 等 TLS 库，或自带 QUIC 实现的 SDK，不会因为应用增加了 XML 就自动执行这些 API；QUIC 是 HTTP/3 使用的基于 UDP 的传输协议。

在 `android-17.0.0_r1` 中可以直接核对这些实现：

- [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) 发起 A、AAAA 与 HTTPS 查询，并构建 `HttpsEndpoint`。
- [`HttpsRecord.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/dns/HttpsRecord.java) 解析 `EchConfigList`。
- [`DomainEncryptionMode.java`](https://android.googlesource.com/platform/external/conscrypt/+/refs/tags/android-17.0.0_r1/common/src/main/java/org/conscrypt/DomainEncryptionMode.java) 给出平台 TLS 实现 Conscrypt 内部使用的模式枚举。
- [`Platform.java`](https://android.googlesource.com/platform/external/conscrypt/+/refs/tags/android-17.0.0_r1/platform/src/main/java/org/conscrypt/Platform.java) 把 ECH 配置失配转换为 Android 公共异常。

应用通常不应重写这套解析与重试逻辑。自定义网络库如果必须接入，应完整处理 `HttpsEndpoint` 选择、平台 TLS 对象检查、握手前配置、取消、超时和配置失配。只把一段 ECH 字节交给套接字，不足以完成安全的协商与重试。

## 网络库支持状态要按版本核对

Android 17 [行为变更页面](https://developer.android.com/about/versions/17/behavior-changes-17#ech) 把 HttpEngine、WebView 与 OkHttp 列为网络库示例，同时明确规定 ECH 只在网络库已经集成支持时生效。文档出现库名称，不能证明应用当前安装或依赖的版本已经支持 ECH。

截至 2026-08-15，可验证的上游状态如下：

| 路径 | 可验证事实 | 适配判断 |
| --- | --- | --- |
| Android 平台 API | DNS、策略、TLS 与失配异常 API 已进入 API 37 | 提供接入能力，不替网络库完成接入 |
| OkHttp | `square/okhttp` 现重定向到上游仓库 `lysine-dev/okhttp`。主分支于 2026-07-24 合并初始 Android API 37 ECH 支持的 [PR #9573](https://github.com/square/okhttp/pull/9573)，并于 2026-07-26 合并按 `NetworkSecurityPolicy` 选择模式的 [PR #9596](https://github.com/square/okhttp/pull/9596)；最新 [`parent-5.4.0`](https://github.com/square/okhttp/tree/parent-5.4.0) 标签创建于 2026-06-08，早于两次合并 | 主分支已经有接入代码，`parent-5.4.0` 尚未包含；核对依赖版本或提交号 |
| Chromium / WebView / Cronet | 2026-06-22 的 [Chromium 提交](https://chromium.googlesource.com/chromium/src/net/+/b91f5ad12e2adc0166183b0172cd4cbc0a04a934) 加入按主机读取平台模式；2026-07-11 的 [后续提交](https://chromium.googlesource.com/chromium/src/net/+/40d5138e2f148890a937d6653284074cd3c3676d) 已在 TLS 与 QUIC 路径执行 ECH 模式 | 主分支已具备读取和执行逻辑；设备上的 WebView 或 Cronet 仍要确认其版本包含这两次提交 |
| 自定义 `SSLSocket` / `SSLEngine` | 公共 API 已可用 | 应由网络库维护完整 DNS、策略与重试流程 |
| 自带原生 TLS 的 SDK | 是否读取 Android XML 取决于 SDK | 要求供应方给出版本、源码或测试证据 |

主分支状态不能直接代表已发布制品或设备组件。上线记录应包含 Maven 依赖坐标与版本、WebView 实现版本、Android 构建号、TLS 实现、是否使用自定义 DNS，以及服务端 ECH 发布状态。Maven 坐标用于唯一标识依赖库，WebView 实现是设备上可独立更新的系统网页组件。仅记录库名无法还原实际能力。

HTTPDNS 是应用通过 HTTP 请求调用第三方 DNS 服务、不使用系统解析器的方案。它和只返回 IP 地址的自定义 `Dns` 接口都需要单独审查。ECH 配置位于 HTTPS 资源记录中；解析实现若只交付 A、AAAA 结果，网络库可能拿不到 `EchConfigList`。HTTPDNS 的适配边界见 24.9。

## 失败与回退判定

ECH 失败应按发生阶段分类。表中的缓存生存时间（time to live，TTL）表示 DNS 记录可以缓存多久。

| 现象 | 可能原因 | 核对动作 |
| --- | --- | --- |
| 连接成功，没有 ECH 配置 | HTTPS 记录缺失、AliasMode、记录没有 `ech` 参数、自定义 DNS 丢失记录 | 对比权威 DNS、设备解析结果和网络库日志 |
| 发送 GREASE 后连接成功 | `enabled` 下没有可用 ECH 配置 | 记为 GREASE，不能记为 ECH 成功 |
| `InvalidEchDataException` | HTTPS 记录里的 ECH 数据为空、长度错误或格式无效 | 修复 DNS 发布内容，检查缓存与 TTL |
| `EchConfigMismatchException` | 客户端缓存的配置与服务端当前配置不一致 | 验证公开名称与证书，再使用服务端给出的重试配置 |
| 普通 TLS 证书失败 | 证书链、主机名、证书透明度或代理证书问题 | 单独核对证书错误，禁用 ECH 不会修复证书 |
| HTTP/3 失败而 HTTP/2 成功 | UDP、QUIC、地址或协议协商问题 | 按 24.5 的协议路径分析 |
| 私网地址、`.local` 或设备发现失败 | `ACCESS_LOCAL_NETWORK` 未获授权 | 按 24.14 的本地网络权限路径分析 |

ECH GREASE 用随机内容模拟 ECH 扩展，帮助发现会阻断未知扩展的网络中间设备。它没有可用的服务端 ECH 配置，不能加密真实 SNI。诊断事件至少要区分 ECH 被接受、GREASE、策略禁用、没有配置、配置失配与其他 TLS 错误。

配置失配后不能跳过校验直接重试。`EchConfigMismatchException` 要求客户端先取得 `getPublicHostname()`，用主机名验证器确认证书对该公开名称有效；公开名称为 `null` 时必须忽略重试配置。验证成功且 `getRetryConfigList()` 非空后，网络库才可以新建连接重试。公共 API 的约束见 [`EchConfigMismatchException`](https://developer.android.com/reference/android/net/ssl/EchConfigMismatchException)。

Android 17 对 `targetSdkVersion 37` 及以上的应用默认启用证书透明度（Certificate Transparency，CT）。证书颁发机构（CA）签发证书后，签名证书时间戳（SCT）可证明该证书已提交到 CT 日志。CT 与 ECH 都可能表现为 TLS 失败，但校验阶段不同。使用系统 CA 时应核对 SCT 与 CT 策略；使用用户 CA 或应用内嵌 CA 时，网络安全配置可能因信任锚不是系统 CA 而关闭 CT，除非域名规则显式启用。禁用 ECH 不会改变证书链或 CT 结果。

`domainEncryption` 位于 Android 安装包（APK）的资源 XML 中，普通远程配置不能修改它。把某个域名改成 `disabled` 通常需要发布新版本；网络库自带的策略开关属于另一套配置，必须确认它与平台策略的优先级。XML 域名覆盖规则不能充当远程即时修复开关。

## 性能观测方法

ECH 对耗时的影响可能来自 HTTPS DNS 查询等待、配置失配后的新连接、TLS 计算和连接复用变化。不同设备与网络的结果会变，不能用一个固定毫秒数概括。

| 阶段 | 建议记录 | 解释限制 |
| --- | --- | --- |
| DNS | A、AAAA、HTTPS 各阶段耗时；HTTPS 记录与 ECH 配置是否存在 | 权威 DNS 有记录不代表设备解析路径取得了记录 |
| TLS | 新连接握手耗时、ECH 接受、GREASE、失配、证书错误 | 通用 HTTP 事件监听器未必暴露 ECH 状态，需要网络库或服务端证据 |
| 重试 | 配置失配次数、是否收到重试配置、新连接次数 | 重试会增加高分位慢样本，不能只看首次握手的平均值 |
| 连接池 | 新建连接率、复用率、HTTP/2 流与 HTTP/3 会话 | 已复用连接不会重新执行完整握手 |
| 业务 | 首包、关键接口分位数、页面首屏、媒体首缓冲 | 同时记录网络类型、代理、VPN、地域与运营商 |

`DnsResolver` 的 `HTTPS_QUERY_WAIT_NONE` 会在地址查询完成后立即回调，即使 HTTPS 查询尚未返回；官方不建议把它用于安全或延迟敏感场景。`HTTPS_QUERY_WAIT_UNTIL_TIMEOUT` 会等待 HTTPS 查询完成或超时，在丢弃 HTTPS 查询的网络中可能增加延迟。网络库通常应从 `HTTPS_QUERY_WAIT_AUTO` 开始，并按实测调整，应用不应随意覆盖内部选择。

`dig` 是查询 DNS 记录的命令行工具。这条命令使用当前电脑配置的解析器，检查域名是否发布 HTTPS 记录：

```bash
dig HTTPS api.example.com +short
```

命令结果可以验证发布格式，却不能代表 Android 设备在蜂窝网络、专用 DNS、VPN 或 HTTPDNS 下获得同一答案。专用 DNS 是 Android 提供的系统级加密 DNS 设置，VPN 则可能接管解析路径。客户端解析日志、服务端 DNS 日志与 TLS 服务端的 ECH 接受状态需要一起核对。

抓包可以观察是否出现形似 ECH 的扩展、连接重试和协议选择，但无法仅凭扩展存在区分有效 ECH 与 GREASE，也不应尝试从 ECH 中恢复内层 SNI。业务性能数据仍要来自网络库事件、应用性能追踪数据（trace）与服务端日志。

## 分阶段发布策略

分阶段发布前先核对这些条件，XML 已配置只是其中一项：

- 固定网络库、WebView 实现、TLS 实现和 Android 17 构建版本。
- 确认库版本包含策略读取、HTTPS DNS 查询、握手配置与失配重试。
- 为候选域名发布 HTTPS 记录，记录 TTL、内容分发网络（CDN）节点、公开名称和证书覆盖。
- 让服务端提供 ECH 接受、拒绝与配置轮换日志。
- 选择低风险域名测试，再处理登录、支付、消息与配置获取等关键接口。
- 分开观察普通网络、企业代理、VPN、校园网、蜂窝网络和不同地域。

`targetSdkVersion 36` 与 37 的对照会同时包含 CT 等其他行为变化，不能把差异单独归因到 ECH。实验室可在相同网络库和代码下构建两份网络安全配置：一份保持 `enabled`，另一份对候选域名设为 `disabled`。这样只改变 ECH 策略，便于归因；生产发布还要考虑应用版本更新需要的时间。

回退手段有三类：

- 服务端修正或轮换 ECH 配置，并在失配响应中提供有效重试配置。
- DNS 撤下或修正 `ech` 参数；客户端缓存会按 TTL 延迟生效。
- 发布应用更新，将确认不兼容的域名设为 `disabled`。

降低 `targetSdkVersion` 会同时改变其他 Android 17 安全行为，也可能不符合应用商店要求，不应作为 ECH 的常规回退方案。远程开关只有在网络库明确支持，并定义了它与平台策略的优先级时才能使用。

隐私日志保留域名分类、错误类型、网络库版本、粗粒度网络环境和协议即可。不要记录完整 URL、令牌、用户输入、证书私钥材料或 ECH 配置原始字节。

## 与 12.2 TLS 性能章节的边界

12.2 解释 TLS 1.3、证书、CT、SNI、混合公钥加密（HPKE）、会话恢复和安全连接成本。ECH 使用 HPKE 加密 ClientHello 内层。Android 17 的按域名策略、配置获取和接入验证构成本节的范围。握手耗时、证书链和 0-RTT 等问题仍按 12.2 的方法分析；0-RTT 指恢复会话时在完整握手结束前发送早期数据。

## 与 24.14 本地网络权限适配的关系

24.14 处理 Android 17 `ACCESS_LOCAL_NETWORK`、局域网设备发现、Google Cast 投屏、物联网（IoT）设备与本地 HTTP 服务。ECH 与网络安全配置适用于公网 HTTPS 连接，两类问题的失败阶段不同。

公网域名的 TLS 握手失败应检查 DNS HTTPS 记录、ECH、CT、证书与协议回退。RFC 1918 私有 IPv4 地址、仅在当前网段有效的地址、`.local`、组播 DNS（mDNS）、简单服务发现协议（SSDP）和本地 HTTP 服务失败时，应先检查本地网络权限。工单中记录目标地址类别和失败阶段，可以避免把权限拒绝误报为 TLS 问题。

## 小结

Android 17 提供了 ECH 所需的平台接口，并为 `targetSdkVersion 37` 的应用把 `domainEncryption` 默认设为 `enabled`。生效仍取决于网络库接入和服务端支持。正式 XML 只接受 `enabled` 与 `disabled`；公开 API 中的 `opportunistic` 常量不能直接写入 XML。

验收时要沿着策略、HTTPS DNS、TLS 配置、服务端协商和重试逐段取证。没有 ECH 配置时发送的是 GREASE，不能计为 ECH 成功；配置失配时必须验证公开名称后再使用重试配置。CT、HTTP/3 和本地网络权限各有独立触发条件，不能因它们都表现为连接失败就归入 ECH。
