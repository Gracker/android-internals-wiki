---
title: "Android 17 ECH 与 domainEncryption 网络适配"
chapter: "24.15"
section: "24.15"
status: ready-for-review
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [network, tls, ech, android17, network-security-config]
related_chapters: ["12.2", "24.4", "24.5", "24.14"]
last_verified: "2026-05-25"
last_verified_against: "Android Developers Android 17 behavior changes / Network Security Config / API reference, RFC 9849 / RFC 9460"
confidence: medium
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
  - type: rfc
    path: "https://www.rfc-editor.org/rfc/rfc9849"
  - type: rfc
    path: "https://www.rfc-editor.org/rfc/rfc9460"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]"
---

# Android 17 ECH 与 domainEncryption 网络适配

## 适配范围

Android 17 / API 37 为网络库提供了 ECH 所需的 DNS、TLS 与按域名策略接口。应用以 `targetSdkVersion 37` 运行时，`domainEncryption` 的默认模式从 `disabled` 变为 `enabled`。这个默认值只表达应用策略；网络库仍须读取策略、查询 HTTPS DNS 记录并把 ECH 配置交给平台 TLS 实现，服务端也要支持 RFC 9849。

因此，验收问题不能缩成“HTTPS 能否连接”。团队还要确认：

- 当前网络库版本是否已经接入 Android 17 ECH API。
- 设备使用的解析路径能否取得 HTTPS 资源记录中的 `ech` 参数。
- 服务端 ECH 配置、公开名称、证书与轮换流程是否一致。
- 没有 ECH 配置、配置失配、代理拦截和证书透明度失败时分别发生什么。
- 连接复用、DNS 等待和协议切换是否改变业务耗时。

平台源码锚点为 `android-17.0.0_r1`。ECH 不依赖应用可见的内核接口，因此不引用内核标签。TLS 1.3、证书链、连接池和 HTTP/2、HTTP/3 原理见 12.2、24.4 与 24.5。

## ECH 的 Android 17 适配边界

ECH 把 TLS ClientHello 分成外层 `ClientHelloOuter` 和加密的 `ClientHelloInner`。真实 SNI 等敏感扩展位于内层；外层仍包含用于路由的公开名称。RFC 9849 同时定义了配置失配后的重试信息与 ECH GREASE。

ECH 保护范围有限：

- 目标 IP 地址仍对网络路径可见。
- 公开名称仍可能出现在外层 ClientHello。
- 使用明文 DNS 时，查询名称仍可能泄露；ECH 不替代加密 DNS。
- 流量大小、时序与连接目的地仍可用于流量分析。
- 客户端、服务端、代理与业务日志仍能看到各自处理的数据。

因此，“开启 ECH”不能写成“域名对所有观察者不可见”。网络库和服务端完成协商时，ECH 加密 ClientHello 内的真实 SNI 等字段，降低网络中间节点直接读取这些字段的能力。[RFC 9849](https://www.rfc-editor.org/rfc/rfc9849) 给出协议细节，[RFC 9460](https://www.rfc-editor.org/rfc/rfc9460) 定义 HTTPS 与 SVCB 资源记录。

Android 17 的平台能力按下面的顺序工作：

1. 网络库通过 `NetworkSecurityPolicy.getDomainEncryptionMode(hostname)` 读取应用对目标域名的策略。
2. 网络库通过 `DnsResolver` 并发查询 A、AAAA 与 HTTPS 记录，得到 `HttpsEndpoint`。
3. `HttpsRecord.getEchConfigList()` 从 ServiceMode HTTPS 记录中解析可选的 `EchConfigList`。
4. 网络库在握手开始前调用 `SSLSockets.setEchConfigList()` 或 `SSLEngines.setEchConfigList()`。
5. 平台 TLS 实现发送 ECH ClientHello；服务端接受配置，或返回配置失配及可选的重试配置。

这条顺序说明了 `domainEncryption` 的职责：它提供按域名策略，不负责自动改造每个网络库。Android 官方文档也明确要求网络库已经接入 ECH。

## `domainEncryption` 放在 Network Security Config 里

`domainEncryption` 可放在 `base-config` 或 `domain-config` 下。`base-config` 适用于没有被域名规则覆盖的连接；多个规则同时匹配时，平台使用域名最长的规则。`includeSubdomains="true"` 会让规则覆盖该域名及各级子域。

下面的 XML 明确声明全局启用，并为一个已知不兼容的网关域名禁用 ECH：

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

正式 Android 17 的 Network Security Configuration 语法只接受两个 XML 值：

| XML 模式 | 语义 |
| --- | --- |
| `enabled` | 握手获得 ECH 配置时使用 ECH；没有配置时启用 ECH GREASE |
| `disabled` | 不使用 ECH，也不使用 ECH GREASE |

`NetworkSecurityPolicy` 的公开常量还包含 `DOMAIN_ENCRYPTION_MODE_OPPORTUNISTIC` 与 `DOMAIN_ENCRYPTION_MODE_UNKNOWN`。它们是网络库读取策略时可能遇到的 API 值，不是当前 XML 语法允许填写的字符串。不要在 Network Security Configuration 中写入 `mode="opportunistic"`。

下面的诊断函数用于确认某个主机名经过 Network Security Configuration 匹配后得到的策略值：

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

这个返回值只能证明平台解析出的策略，不能证明 DNS 返回了 ECH 配置，也不能证明某次 TLS 握手使用了 ECH。诊断日志不应记录完整 URL、查询参数或用户标识。

模式与默认值以 [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config#domain-encryption) 为准，API 常量见 [`NetworkSecurityPolicy`](https://developer.android.com/reference/android/security/NetworkSecurityPolicy)。

## Android 17 API 与源码边界

`DnsResolver` 在 API 37 增加了返回 `HttpsEndpoint` 的查询重载。它会并发发出 A、AAAA 和 HTTPS 查询，并允许调用方通过 `httpsTimeoutMillis` 决定地址记录完成后还要等待 HTTPS 记录多久。`DnsResolver.getInstance()` 在 API 37 已废弃，新代码应使用接收 `Context` 与 `Looper` 的构造函数。

`HttpsRecord` 表示 RFC 9460 的 HTTPS 记录。`priority == 0` 表示 AliasMode，这类记录不携带 IP 提示、端口、ALPN 或 ECH 配置；ServiceMode 记录才可能通过 `getEchConfigList()` 返回 ECH 配置。返回值可以为 `null`，格式错误会抛出 `InvalidEchDataException`。

`SSLSockets.setEchConfigList()` 和 `SSLEngines.setEchConfigList()` 必须在握手开始前调用，而且只接受平台 TLS provider 创建的 socket 或 engine。自带 BoringSSL、OpenSSL 或原生 QUIC 实现的 SDK 不会因为应用增加了 XML 就自动执行这些 API。

在 `android-17.0.0_r1` 中可以直接核对这些实现：

- [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) 发起 A、AAAA 与 HTTPS 查询，并构建 `HttpsEndpoint`。
- [`HttpsRecord.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/dns/HttpsRecord.java) 解析 `EchConfigList`。
- [`DomainEncryptionMode.java`](https://android.googlesource.com/platform/external/conscrypt/+/refs/tags/android-17.0.0_r1/common/src/main/java/org/conscrypt/DomainEncryptionMode.java) 给出平台 TLS 内部使用的模式枚举。
- [`Platform.java`](https://android.googlesource.com/platform/external/conscrypt/+/refs/tags/android-17.0.0_r1/platform/src/main/java/org/conscrypt/Platform.java) 把 ECH 配置失配转换为 Android 公共异常。

应用通常不应重写这套解析与重试逻辑。自定义网络库如果必须接入，应完整处理 `HttpsEndpoint` 选择、平台 TLS provider 检查、握手前配置、取消、超时和配置失配，不能只把一段 ECH 字节写入 socket。

## 网络库支持状态要按版本核对

Android 17 的功能页面说明 HttpEngine、WebView 与 OkHttp 将在后续更新中接入平台 API；[行为变更页面](https://developer.android.com/about/versions/17/behavior-changes-17#ech) 同样以“网络库已经集成”为生效前提。因此，库名称出现在文档中不等于应用当前解析到的版本已经支持 ECH。

截至 2026-07-29，可验证的公开状态如下：

| 路径 | 可验证事实 | 适配判断 |
| --- | --- | --- |
| Android 平台 API | DNS、策略、TLS 与失配异常 API 已进入 API 37 | 提供接入能力，不替网络库完成接入 |
| OkHttp | 主分支已于 2026-07-24 合并初始 Android API 37 ECH 支持的 [PR #9573](https://github.com/square/okhttp/pull/9573)，并于 2026-07-26 合并按 `NetworkSecurityPolicy` 选择模式的 [PR #9596](https://github.com/square/okhttp/pull/9596)；[`parent-5.4.0`](https://github.com/square/okhttp/tree/parent-5.4.0) 标签早于这两次合并 | 主分支具备接入代码不等于应用使用的发布版本已经包含它，必须核对依赖版本或提交号 |
| Chromium / WebView / Cronet | 2026-06-22 的 [Chromium 提交](https://chromium.googlesource.com/chromium/src/net/+/b91f5ad12e2adc0166183b0172cd4cbc0a04a934) 加入按主机读取平台模式，但提交说明明确写着执行逻辑另行加入 | 含该提交的版本仍需验证模式是否被执行 |
| 自定义 `SSLSocket` / `SSLEngine` | 公共 API 已可用 | 应由网络库维护完整 DNS、策略与重试流程 |
| 自带原生 TLS 的 SDK | 是否读取 Android XML 取决于 SDK | 要求供应方给出版本、源码或测试证据 |

上线记录应包含网络库坐标与版本、WebView provider 版本、Android 构建号、TLS provider、是否使用自定义 DNS、服务端 ECH 发布状态。只记录“使用 OkHttp”或“使用 WebView”不够精确。

HTTPDNS 与只返回 IP 地址的自定义 `Dns` 接口需要单独审查。ECH 配置位于 HTTPS 资源记录中；解析实现若只交付 A、AAAA 结果，网络库可能拿不到 `EchConfigList`。HTTPDNS 的适配边界见 24.9。

## 失败与回退判定

ECH 失败应按发生阶段分类：

| 现象 | 可能原因 | 核对动作 |
| --- | --- | --- | --- |
| 连接成功，没有 ECH 配置 | HTTPS 记录缺失、AliasMode、记录没有 `ech` 参数、自定义 DNS 丢失记录 | 对比权威 DNS、设备解析结果和网络库日志 |
| 发送 GREASE 后连接成功 | `enabled` 下没有可用 ECH 配置 | 记为 GREASE，不能记为 ECH 成功 |
| `InvalidEchDataException` | HTTPS 记录里的 ECH 数据为空、长度错误或格式无效 | 修复 DNS 发布内容，检查缓存与 TTL |
| `EchConfigMismatchException` | 客户端缓存的配置与服务端当前配置不一致 | 验证公开名称与证书，再使用服务端给出的重试配置 |
| 普通 TLS 证书失败 | 证书链、主机名、证书透明度或代理证书问题 | 单独核对证书错误，禁用 ECH 不会修复证书 |
| HTTP/3 失败而 HTTP/2 成功 | UDP、QUIC、地址或协议协商问题 | 按 24.5 的协议路径分析 |
| 私网地址、`.local` 或设备发现失败 | `ACCESS_LOCAL_NETWORK` 未获授权 | 按 24.14 的本地网络权限路径分析 |

ECH GREASE 用随机内容模拟 ECH 扩展，帮助发现会阻断未知扩展的中间设备。它没有可用的服务端 ECH 配置，不能加密真实 SNI。观测系统至少要分开记录 ECH 被接受、GREASE、策略禁用、没有配置、配置失配与其他 TLS 错误。

配置失配不能盲目重试。`EchConfigMismatchException` 要求客户端先取得 `getPublicHostname()`，用主机名验证器确认证书对该公开名称有效；公开名称为 `null` 时必须忽略重试配置。验证成功且 `getRetryConfigList()` 非空后，网络库才可以新建连接重试。公共 API 的约束见 [`EchConfigMismatchException`](https://developer.android.com/reference/android/net/ssl/EchConfigMismatchException)。

Android 17 对 `targetSdkVersion 37` 及以上的应用默认启用证书透明度。CT 与 ECH 共享 TLS 失败表象，但配置和校验阶段不同。使用系统 CA 时应核对 SCT 与 CT 策略；使用用户 CA 或内嵌 CA 时，Network Security Configuration 可能按信任锚规则关闭 CT，除非域名规则显式启用。禁用 ECH 不会改变证书链或 CT 结果。

`domainEncryption` 位于 APK 的资源 XML 中，普通远程配置不能修改它。把某个域名改成 `disabled` 通常需要发布新版本；网络库自带的策略开关属于另一套配置，必须确认它与平台策略的优先级。因此，不能把 XML 域名覆盖规则当作远程热修复开关。

## 性能观测方法

ECH 对耗时的影响可能来自 HTTPS DNS 查询等待、配置失配后的新连接、TLS 计算和连接复用变化。不能用一个固定毫秒数描述所有设备与网络。

| 阶段 | 建议记录 | 解释限制 |
| --- | --- | --- | --- |
| DNS | A、AAAA、HTTPS 各阶段耗时；HTTPS 记录与 ECH 配置是否存在 | 权威 DNS 有记录不代表设备解析路径取得了记录 |
| TLS | 新连接握手耗时、ECH 接受、GREASE、失配、证书错误 | 通用 HTTP 事件监听器未必暴露 ECH 状态，需要网络库或服务端证据 |
| 重试 | 配置失配次数、是否收到重试配置、新连接次数 | 重试会改变尾部耗时，不能并入首次握手后只看平均值 |
| 连接池 | 新建连接率、复用率、HTTP/2 流与 HTTP/3 会话 | 已复用连接不会重新执行完整握手 |
| 业务 | 首包、关键接口分位数、页面首屏、媒体首缓冲 | 同时记录网络类型、代理、VPN、地域与运营商 |

`DnsResolver` 的 `HTTPS_QUERY_WAIT_NONE` 会在地址查询完成后立即回调，即使 HTTPS 查询尚未返回；官方不建议把它用于安全或延迟敏感场景。`HTTPS_QUERY_WAIT_UNTIL_TIMEOUT` 会等待 HTTPS 查询完成或超时，在丢弃 HTTPS 查询的网络中可能增加延迟。网络库通常应从 `HTTPS_QUERY_WAIT_AUTO` 开始，并按实测调整，应用不应随意覆盖内部选择。

下面的命令用于从当前命令行所用解析器检查域名是否发布 HTTPS 记录：

```bash
dig HTTPS api.example.com +short
```

命令结果可以验证发布格式，却不能代表 Android 设备在蜂窝网络、专用 DNS、VPN 或 HTTPDNS 下获得同一答案。客户端解析日志、服务端 DNS 日志与 TLS 服务端的 ECH 接受状态需要一起核对。

抓包可以观察是否出现形似 ECH 的扩展、连接重试和协议选择，但无法仅凭扩展存在区分有效 ECH 与 GREASE，也不应尝试从 ECH 中恢复内层 SNI。业务性能数据仍要来自网络库事件、应用 trace 与服务端日志。

## 灰度发布策略

灰度前先建立能力清单，避免把“XML 已配置”当成完成：

- 固定网络库、WebView provider、TLS provider 和 Android 17 构建版本。
- 确认库版本包含策略读取、HTTPS DNS 查询、握手配置与失配重试。
- 为候选域名发布 HTTPS 记录，记录 TTL、CDN 节点、公开名称和证书覆盖。
- 让服务端提供 ECH 接受、拒绝与配置轮换日志。
- 选择低风险域名测试，再处理登录、支付、消息与配置获取等关键接口。
- 分开观察普通网络、企业代理、VPN、校园网、蜂窝网络和不同地域。

`targetSdkVersion 36` 与 37 的对照会同时包含 CT 等其他行为变化，不能单独归因到 ECH。控制变量更少的做法是在相同网络库与代码下使用两份 Network Security Configuration 构建测试包，一份保持 `enabled`，另一份对候选域名设为 `disabled`。这适合实验室与受控测试；生产发布仍要评估应用版本更新的时效。

回退手段有三类：

- 服务端修正或轮换 ECH 配置，并在失配响应中提供有效重试配置。
- DNS 撤下或修正 `ech` 参数；客户端缓存会按 TTL 延迟生效。
- 发布应用更新，将确认不兼容的域名设为 `disabled`。

降低 `targetSdkVersion` 会同时改变其他 Android 17 安全行为，也可能不符合应用商店要求，不应作为 ECH 的常规回退方案。远程开关只有在网络库明确支持并定义了与平台策略的关系时才可使用。

隐私日志保留域名分类、错误类型、网络库版本、粗粒度网络环境和协议即可。不要记录完整 URL、令牌、用户输入、证书私钥材料或 ECH 配置原始字节。

## 与 12.2 TLS 性能章节的边界

12.2 解释 TLS 1.3、证书、CT、SNI、HPKE、会话恢复和安全连接成本。这里说明 Android 17 如何表达按域名 ECH 策略、网络库如何取得 ECH 配置，以及应用怎样验证接入。握手耗时、证书链和 0-RTT 等问题仍按 12.2 的方法分析。

## 与 24.14 本地网络权限适配的关系

24.14 处理 Android 17 `ACCESS_LOCAL_NETWORK`、局域网设备发现、Cast、IoT 与本地 HTTP 服务。这里处理公网 HTTPS 连接中的 ECH 与 Network Security Configuration。两者的失败阶段不同。

公网域名的 TLS 握手失败应检查 DNS HTTPS 记录、ECH、CT、证书与协议回退。RFC 1918 地址、链路本地地址、`.local`、mDNS、SSDP 和本地 HTTP 服务失败时，应先检查本地网络权限。工单中记录目标地址类别和失败阶段，可以避免把权限拒绝误报为 TLS 问题。

## 小结

Android 17 提供了 ECH 所需的平台接口，并为 `targetSdkVersion 37` 的应用把 `domainEncryption` 默认设为 `enabled`。生效仍取决于网络库接入和服务端支持。正式 XML 只接受 `enabled` 与 `disabled`；公开 API 中的 `opportunistic` 常量不能直接写入 XML。

验收时要沿着策略、HTTPS DNS、TLS 配置、服务端协商和重试逐段取证。没有 ECH 配置时发送的是 GREASE，不能计为 ECH 成功；配置失配时必须验证公开名称后再使用重试配置。CT、HTTP/3 和本地网络权限各有独立触发条件，不能因它们都表现为连接失败就归入 ECH。
