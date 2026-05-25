---
title: "Android 17 ECH 与 domainEncryption 网络适配"
chapter: "24.18"
section: "24.18"
status: ready-for-review
drafted_date: "2026-05-25"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
tags: [network, tls, ech, android17, network-security-config]
related_chapters: ["12.4", "24.4", "24.5", "24.16"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/每日信息"
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

# 24.18 Android 17 ECH 与 domainEncryption 网络适配

<!-- outline-start -->
## 要点

### 🔹 ECH 的 Android 17 适配边界
说明 ECH 只在 Android 17 起可用，且依赖网络库、服务端 HTTPS DNS 记录和远端 ECH 支持，不把平台默认行为写成所有连接必然加密 SNI。

### 🔹 `domainEncryption` 配置方式
整理 `base-config` 与 `domain-config` 的配置位置、文档列出的 mode 取值差异，以及按域名灰度关闭的场景。

### 🔹 网络库支持矩阵
区分 HttpEngine、WebView、OkHttp/Conscrypt 路径，说明配置只有在网络库接入 ECH 后才生效。

### 🔹 失败与回退判定
覆盖 ECH 协商失败、ECH GREASE、标准 TLS 回退、证书透明度默认启用和代理/网关兼容性排查。

### 🔹 性能观测方法
设计 DNS HTTPS 记录查询、TLS 握手耗时、连接复用命中、失败率和地域/运营商维度监控，不给未验证的固定耗时收益。

### 🔹 灰度发布策略
给出白名单域名、关键接口降级、实验分组、抓包限制和隐私合规协同的工程检查项。

## 扩展

### 🔸 与 12.4 TLS 性能章节的边界
12.4 负责 TLS/证书/握手基础，本节只处理 Android 17 ECH 与应用侧配置。

### 🔸 与 24.16 本地网络权限适配的关系
两者都属于 Android 17 网络行为变化，但一个影响公网 TLS 握手，一个影响 LAN 访问权限。

<!-- outline-end -->

## 这节解决什么问题

Android 17 把 Encrypted Client Hello（ECH）放进平台网络安全配置面。对应用来说，升级 `targetSdkVersion` 后不能只看 TLS 是否能连通，还要确认网络库是否读取平台配置、服务端是否发布 HTTPS DNS 记录、失败时是否走到预期的 GREASE 或禁用路径。

本节不重复 TLS 1.3、证书链、连接池和 HTTP/2 / HTTP/3 的原理，这些内容详见 12.4、24.4 和 24.5。这里只处理 Android 17 的 ECH 配置、灰度、观测和回退。参考书只用于组织性能排查顺序：先拆速度来源，再看线程等待、缓存命中和连接复用，不使用参考书原文段落。 [结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md] [结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md] [结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

## ECH 的 Android 17 适配边界

ECH 是 TLS 1.3 的扩展，用来加密 ClientHello 中的敏感字段，最常见的是 SNI。标准 TLS 握手里，网络中间节点即使看不到 HTTP 内容，也能从明文 SNI 判断客户端访问的域名；ECH 把这部分放进加密的 inner ClientHello，外层只保留可路由的 public name。 [已验证: RFC 9849, https://www.rfc-editor.org/rfc/rfc9849]

Android 17 的公开文档给了三条边界：ECH 只从 API 37 开始提供；应用使用的网络库必须接入 ECH；远端服务器也要支持 ECH 协议。`domainEncryption` 写进 XML 后，不会让所有 HTTPS 请求自动拥有加密 SNI。网络库没有接入、服务端没有 HTTPS/SVCB 记录、记录里没有可用 `ech` 参数、代理或网关拦截了相关路径，都会让最终行为偏离预期。 [已验证: 官方文档, https://developer.android.com/privacy-and-security/security-config]

Android 17 还给 `DnsResolver`、`HttpsRecord` 和 `SSLSockets` 增加了公开入口。`DnsResolver` 可以查询 A / AAAA / HTTPS 记录并返回 `HttpsEndpoint`，`HttpsRecord#getEchConfigList()` 可以取出 HTTPS 记录里的 ECH 配置，`SSLSockets#setEchConfigList()` 可以在 TLS 握手前把配置传给平台 socket。应用通常不该自己拼这一套流程；这些 API 更适合作为网络库接入和排查时的事实边界。 [已验证: 官方文档, https://developer.android.com/about/versions/17/features] [已验证: 官方文档, https://developer.android.com/reference/android/net/dns/HttpsRecord] [已验证: 官方文档, https://developer.android.com/reference/android/net/ssl/SSLSockets]

## `domainEncryption` 放在 Network Security Config 里

`domainEncryption` 属于 Network Security Configuration 的子元素，可放在 `base-config` 或 `domain-config` 下。`base-config` 影响没有被特定域名规则覆盖的连接；`domain-config` 按域名覆盖，匹配规则仍沿用 Network Security Config 的域名继承和最长匹配语义。 [已验证: 官方文档, https://developer.android.com/privacy-and-security/security-config]

这段 XML 展示灰度阶段的常见写法，重点看全局默认和单域名覆盖：

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

这段配置的语义是：默认允许网络库对支持 ECH 的连接使用 ECH；访问 `legacy-gateway.example.com` 及其子域时，不尝试 ECH 或 ECH GREASE。适合用在网关、代理、企业客户专线或旧 CDN 节点还没有完成验证的灰度期。

2026-05-25 复核官方英文文档时，`domainEncryption` 的语法列出 `enabled` 和 `disabled` 两个值；Android 17 features 页面仍用“opportunistically or mandating”描述策略取向，部分本地化页面和早期说明还出现过 `opportunistic`。发布配置时按英文 Network Security Config 页面和本地构建工具校验为准，不要在生产 XML 里依赖文档尚未稳定的 mode 值。 [待验证: `opportunistic` mode 是否会在正式 Android 17 SDK XML schema 中保留]

`enabled` 不能理解成“所有连接失败就降级成明文 SNI”。官方配置页描述的是：TLS 握手建立时如果提供了 ECH 配置，就对该连接执行 ECH；如果没有 ECH 配置，则启用 ECH GREASE。`disabled` 则是不尝试 ECH 和 GREASE。对应用侧更实用的判断是：把 `enabled` 当成升级后的默认策略，把 `disabled` 留给明确有兼容问题的域名。

## 网络库支持矩阵

ECH 在应用里通常有三条路径：平台 HTTP 引擎、WebView、以及 OkHttp / 自定义 TLS 栈。三条路径的配置面不同，排查入口也不同。

| 路径 | 应用侧配置入口 | ECH 生效条件 | 排查重点 |
| --- | --- | --- | --- |
| `HttpEngine` / Cronet 路径 | 平台或库内部读取 Network Security Config | 使用的版本接入 Android 17 ECH API；服务端发布 HTTPS 记录和 ECH config | 协议、DNS HTTPS 记录、QUIC / HTTP/2 fallback、失败码 |
| WebView | WebView 网络栈和应用 Network Security Config | 设备 WebView / Chromium 网络栈版本支持 ECH；目标域支持 ECH | WebView 版本、企业代理、证书策略、页面资源域名 |
| OkHttp + 平台 TLS provider | OkHttp 版本、平台 TLS provider、Network Security Config | OkHttp 对 Android 17 ECH 配置完成接入；socket 来自平台 TLS provider | OkHttp 版本、Conscrypt / provider、EventListener 建连分段 |
| 自定义 `SSLSocket` / native TLS | 业务代码或三方库直接处理 TLS | 主动查询 HTTPS 记录并在握手前传入 ECH config，且实现符合平台 API | [待验证] 不建议业务层自行维护，优先交给网络库 |

Android 17 文档把 HttpEngine、WebView、OkHttp 作为示例网络库提到，但语义是“网络库接入后才生效”，不能推导出“所有版本已经生效”。升级前要在测试包记录网络库版本、设备 Android 版本、TLS provider、WebView 版本和服务端 ECH 发布状态。 [已验证: 官方文档, https://developer.android.com/about/versions/17/behavior-changes-17]

自定义 TLS 栈要谨慎。`domainEncryption` 是 Android 平台配置，BoringSSL、OpenSSL 或业务自带 QUIC/TLS 栈不会天然读取这份 XML。若某个 SDK 自带 TLS 实现，它可能绕过平台 Network Security Config、证书透明度和 ECH 配置。对这类 SDK，验收项应改成“SDK 明确说明如何处理 Android 17 ECH 与 CT”，单靠 App XML 不够。

## 失败与回退判定

ECH 失败不能只看“请求失败”或“TLS 握手失败”。同一个用户反馈里，可能同时存在 DNS HTTPS 记录缺失、ECH config 过期、企业代理替换证书、证书透明度不通过、HTTP/3 被阻断和本地网络权限失败。需要先给失败分类。

| 现象 | 常见原因 | 处理方式 | 关联章节 |
| --- | --- | --- | --- |
| 目标域没有 ECH，但连接成功 | 没有 HTTPS 记录或没有 `ech` 参数，`enabled` 下使用 GREASE | 记录为“ECH 未命中”，不当成连接失败 | 12.4 |
| TLS 握手失败 | ECH config 与服务端不匹配、证书链异常、CT 默认启用后证书不合规 | 按域名临时 `disabled`，同时修服务端记录和证书 | 12.4 |
| 企业代理或网关环境失败 | 中间设备不支持 ECH、拦截 TLS、替换证书 | 建立企业网络分桶，保留域名级禁用开关 | 24.4 |
| HTTP/3 失败但 HTTP/2 成功 | UDP / QUIC 被阻断，和 ECH 不一定相关 | 保留 HTTP/2 fallback，分开记录协议失败 | 24.5 |
| LAN / Cast / IoT 失败 | Android 17 本地网络权限阻断 | 不归因到 ECH，走 24.16 的权限路径 | 24.16 |

ECH GREASE 的目的不是隐藏真实域名。它在没有可用 ECH 配置时让网络生态持续看到形状类似 ECH 的扩展，降低中间设备把未知扩展当异常的概率。GREASE 命中时，SNI 仍可能是普通 TLS 路径；因此指标里要区分“ECH 成功”“GREASE”“禁用”“无配置”。 [已验证: RFC 9849, https://www.rfc-editor.org/rfc/rfc9849]

Android 17 对 `targetSdkVersion >= 37` 的应用默认启用 Certificate Transparency。ECH 迁移时经常会顺手调整 CDN、证书和 DNS，如果证书 SCT 不符合 Android CT 策略，表现会落在 TLS 失败上，不能直接归因到 ECH。排查顺序建议是：证书链和 CT、DNS HTTPS 记录、ECH config、新旧网络库版本、代理/网关、协议 fallback。

## 性能观测方法

ECH 的性能评估要按阶段拆开，不要给一个全局固定收益或固定开销。移动网络里的主要波动来自 DNS、RTT、连接复用和协议 fallback，HPKE 计算成本通常要放在设备、算法套件和实现版本里单独压测。没有这组条件时，正文和监控都不写“ECH 固定增加 X ms”。

| 阶段 | 指标 | 采集方式 | 判断 |
| --- | --- | --- | --- |
| DNS HTTPS 记录 | HTTPS 记录命中率、`ech` 参数命中率、解析耗时 | 服务端 DNS 日志、客户端网络库事件、灰度探针 | 区分“域名未发布 ECH”和“客户端没查到” |
| TLS 握手 | 握手耗时、TLS 版本、cipher suite、ECH 状态 | OkHttp EventListener、HttpEngine / Cronet metrics、服务端 TLS 日志 | 对比同域名 targetSdk 36 / 37 或 ECH on / off |
| 连接复用 | 新建连接率、复用命中率、HTTP/2 stream 数 | 连接池事件、`connectionAcquired`、服务端连接数 | 避免把短连接放大的握手成本算到 ECH |
| 失败率 | `UnknownHost`、TLS alert、证书错误、QUIC fallback、代理失败 | 统一错误码、网络类型、运营商、地域分桶 | 找出兼容性失败，避免只看平均值变化 |
| 用户侧体验 | 首包、接口 P90/P99、页面首屏、视频首缓冲 | APM、播放器指标、业务埋点 | 只在业务指标恶化时回滚，不因单段指标波动误判 |

服务端侧至少补三类日志：HTTPS DNS 记录查询量、TLS 握手 ECH 接受/拒绝状态、证书透明度相关失败。客户端侧补网络库版本、Android 版本、target SDK、域名、网络类型、代理/VPN 状态和协议。企业网络、校园网、运营商 NAT、VPN 都要单独分桶，因为这些环境最容易暴露未知 TLS 扩展兼容问题。

外部验证可以用 DNS 工具确认记录发布状态。下面的命令只验证域名是否发布 HTTPS 记录，不代表 Android 端一定启用了 ECH：

```bash
dig HTTPS api.example.com
```

命令结果里如果没有 HTTPS/SVCB 记录或没有 ECH 参数，Android 网络库即使支持 ECH，也拿不到服务端配置。若记录存在但客户端仍失败，再查 DNS 缓存、网络库接入和 TLS 握手日志。

## 灰度发布策略

ECH 迁移适合按域名和业务级别推进，不适合一次性覆盖所有请求。先选登录后低风险的读接口或静态资源域名，保留域名级 `disabled` 开关；支付、登录、消息发送、配置拉取这类接口要等证书、DNS、代理、服务端日志都能互相印证后再扩大比例。

一套可执行的灰度顺序如下：

1. 服务端为候选域名发布 HTTPS 记录和 ECH config，记录 TTL、CDN 节点覆盖率和证书状态。
2. 客户端灰度 targetSdk 37 包，记录 ECH 状态、TLS 错误、协议 fallback、首包和接口 P90/P99。
3. 对企业客户、VPN、代理、校园网、海外运营商建立分桶，给问题域名准备 `domainEncryption mode="disabled"` 热修复方案。
4. 对低风险域名扩大流量，观察一周以上的失败率和尾延迟，再推进登录、支付、消息等关键接口。
5. 保留 `targetSdkVersion 36` 或 ECH disabled 对照组，确认问题来自 Android 17 ECH / CT，避免把同一版本里的业务改动算进去。

隐私合规也要同步处理。ECH 会减少网络中间节点看到真实域名的机会，但客户端和服务端仍会处理完整域名、IP、证书和业务请求日志。监控字段只保留排障所需的域名、错误类别和粗粒度网络环境，不记录完整 URL、token、用户输入或证书明文内容。

## 与 12.4 TLS 性能章节的边界

12.4 负责解释 TLS 1.3、证书、CT、SNI、HPKE 和安全连接成本；本节只处理 Android 17 上应用怎样配置和灰度 ECH。遇到握手耗时、证书链过长、TLS session resumption、0-RTT、证书透明度策略时，正文只引用 12.4，不在这里重写原理。

本节给出的判断更偏上线流程：哪些域名能先开、怎么发现服务端没发布 ECH、怎么把 GREASE 和 ECH 成功分开、怎么用 `domainEncryption` 做域名级禁用。读者如果要理解 TLS 握手本身，应回到 12.4。

## 与 24.16 本地网络权限适配的关系

24.16 处理的是 Android 17 `ACCESS_LOCAL_NETWORK`、LAN 设备发现、Cast / IoT / 本地 HTTP server 和流媒体速率上限。本节处理公网 HTTPS 连接的 ECH 与 Network Security Config。两者都属于 Android 17 网络行为变化，但失败位置完全不同。

排障时先看目标地址。公网域名的 TLS 握手失败，进入 ECH / CT / 证书 / 协议 fallback 路径；RFC1918、link-local、`.local`、mDNS、SSDP、本地 HTTP 服务失败，进入本地网络权限路径。把这两类错误拆开，线上工单才能直接分配给网络安全、播放器、IoT 或基础网络库团队。
