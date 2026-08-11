---
title: "Android 网络安全与 TLS 性能优化"
chapter: "12.2"
section: "12.2"
status: finalized
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 6.0 (API 23) - Android 17 (API 37)"
last_verified: "2026-07-31"
last_verified_against: "Android 17 / API 37; AOSP android-17.0.0_r1 Conscrypt and DnsResolver; RFC 8446 / 9180 / 9849; OkHttp 5.3.0 and Cronet 18.0.1 public APIs"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://developer.android.com/privacy-and-security/certificate-transparency-policy"
  - type: official
    path: "https://developer.android.com/about/versions/10/features#tls-1.3"
  - type: official
    path: "https://developer.android.com/reference/android/crypto/hpke/package-summary"
  - type: official
    path: "https://developer.android.com/reference/android/crypto/hpke/Hpke"
  - type: official
    path: "https://developer.android.com/reference/android/crypto/hpke/HpkeSpi"
  - type: official
    path: "https://android.googlesource.com/platform/external/conscrypt/+/android-17.0.0_r1/common/src/main/java/org/conscrypt/SSLParametersImpl.java"
  - type: official
    path: "https://android.googlesource.com/platform/external/conscrypt/+/android-17.0.0_r1/platform/src/main/java/org/conscrypt/Platform.java"
  - type: official
    path: "https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/PrivateDnsConfiguration.cpp"
  - type: official
    path: "https://www.rfc-editor.org/rfc/rfc8446"
  - type: official
    path: "https://www.rfc-editor.org/rfc/rfc9180"
  - type: official
    path: "https://www.rfc-editor.org/rfc/rfc9849"
  - type: official
    path: "https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ConnectionPool.kt"
  - type: official
    path: "https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/QuicOptions.Builder.html"
tags: [network-security, tls, ech, hpke, certificate-transparency, cleartext, performance]
related_chapters: ["12.1", "12.3", "1.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "官方文档+AOSP结构"
gap_score: 14
task6_state: "reviewed"
pipeline_stage: "ready-to-publish"
task6_auto_promotion_note: "2026-05-07 Task6 auto-promotion：finalized。条件满足：task6_result=pass-light-edit、task9_result=pass-tech-review、queue 无 pending 条目。"
finalized_by: "openclaw-task9-auto-promote"
finalized_date: "2026-07-08"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: "fixed"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-28"
last_task6_at: "2026-07-08T01:15:53+08:00"
last_task6_audit: "2026-06-14"
task6_result: "pass-light-edit"
review_round: 3
task2b_result: "fixed"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-08"
last_task9_at: "2026-07-08T01:27:42+08:00"
last_task2b_at: "2026-05-28T06:50:00+08:00"
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
last_task9_audit: "2026-07-07"
last_task9_audit_log: "logs/deep-review/2026-07-07-22-audit.md"
task9_review_notes: "2026-05-20 task9 idle audit: needs-rework. P0 3 / P1 1 / P2 0 / P3 0. P0: Android 15 0-RTT anti-replay 已验证断言缺官方依据；AAPM 强制 ECH+DoH3 与当前文档冲突；DoH/DoT 不能隐藏 SNI。P1: Android 17 domainEncryption opportunistic 枚举疑似过期。2026-05-28 Task2B fallback 已修复上述 4 项，回流 Task6/Task9。 2026-05-28 Task9 deep-review: auto-fixed。P1 1：修正 Android 17 ECH enabled 模式下“协商失败必然回退普通 TLS”的过宽断言，回到 Task6 复审。 2026-05-28 08 Task9 deep-review: auto-fixed。P0 0 / P1 0 / P2 2。AUTO-FIX: 删除 ECH CPU 固定比例无源断言，替换 CT Policy stale 待验证注记，回到 Task6 复审。 | 2026-05-28 10 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 1；复核 Android 17 ECH/CT、HPKE SPI、cleartext 默认策略、DNS 加密传输边界；无 P0/P1。 自动晋升 finalized。 | 2026-06-14 06 Task9 idle audit: auto-fixed。P0 2 / P1 0 / P2 0 / P3 1。AUTO-FIX: 修正 Android 10 TLS 1.3 已验证链接（旧 /about/versions/10/security 404 -> /about/versions/10/features#tls-1.3）；修正 Android CT Policy 参考资料链接（旧 source.android.com/docs/security/cert-transparency 404 -> developer.android.com/privacy-and-security/certificate-transparency-policy）；同步规范化 Conscrypt Security Provider 重定向链接。回到 Task6 复审。 | 2026-06-14 08 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 0；复核 Android 17 ECH/domainEncryption、CT 默认启用、Android CT Policy、Android 10 TLS 1.3、HPKE SPI 与 cleartext 默认策略；无阻断问题，Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-07-07 22 Task9 idle audit: auto-fixed。P0 1 / P1 0 / P2 0 / P3 0。AUTO-FIX: 修正 DoH 版本锚点；AOSP android-11.0.0_r1 DnsResolver 未见 DoH 集成路径，android-13.0.0_r1 已出现 setDoh/dohQuery，android-17.0.0_r1 仍保留 DoH/DoT 路径。回到 Task6 复审。 | 2026-07-08 01 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0 / P3 1；复核 Android 17 ECH/domainEncryption、CT 默认启用与 Android CT Policy、HttpEngine/Cronet 0-RTT 边界、HPKE SPI、cleartext 默认策略、DnsResolver DoH/DoT 版本锚点；无阻断问题，Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task6_review_log: "logs/review/2026-07-08-01-review.md"
task6_l3_l4_issues: 0
task6_l1_l2_fixes: 0
task6_review_notes: "2026-05-28 09 Task6 revisiting-review: pass-light-edit；L1/L2 小修 0 处；outline 5/5 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，送 Task9 复核。 | 2026-07-08 01 Task6 revisiting-review: pass-light-edit；L1 小修 1 处（重复句删除）；outline 5/5 覆盖；无 L3/L4 回炉项。Task9 result 为 auto-fixed，送 Task9 复核。"
last_task9_review_log: "logs/deep-review/2026-07-08-01-deep-review.md"
updated_by: "openclaw-task9"
updated_date: "2026-07-08"
last_task9_autofix_at: "2026-07-07"
p0: 0
p1: 0
p2: 0
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-05-28T09:06:00+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-08
last_task2b_verifier_at: "2026-07-07T23:28:23+08:00"
---

# 12.2 Android 网络安全与 TLS 性能优化

一个 HTTPS 请求在传输业务数据前，可能依次经过 DNS、传输层建连、TLS 握手和证书验证。短请求的业务数据很少，建连阶段反而可能占据大部分等待时间。分析这类问题时，不能把所有耗时都记到“TLS”名下，也不能用降低验证强度来换取表面上的延迟下降。

平台锚点为 Android 17（API 37）和 AOSP `android-17.0.0_r1`。以下内容说明 TLS 1.3、连接复用、Encrypted Client Hello（ECH）、Certificate Transparency（CT）、明文流量策略与 HPKE 的职责边界；版本迭代只保留影响迁移判断的节点。

## 先把一次安全连接分段

RTT（Round-Trip Time）表示报文往返一次的时间。不同网络制式、无线信号、运营商路由和服务端地域会让 RTT 相差很大，因此不使用固定毫秒数估算握手成本。一次新 HTTPS 连接可按下列阶段记录：

| 阶段 | 常见工作 | 观测重点 |
|:---|:---|:---|
| DNS | A/AAAA 查询；ECH 场景还可能读取 HTTPS 资源记录 | 缓存命中、解析器类型、查询并发 |
| 传输层 | TCP 三次握手，或 QUIC 的传输层建连 | 新连接比例、IPv4/IPv6 竞速、丢包 |
| TLS | ClientHello、密钥协商、证书和 Finished 消息 | TLS 版本、完整握手或恢复、ECH |
| 证书验证 | 信任链、主机名、有效期、CT 等检查 | 失败类型、证书链、SCT |
| HTTP | 发送请求并等待响应头与响应体 | 协议、连接复用、服务端处理 |

HTTP/2 或 HTTP/3 可以让多个请求复用一条连接。复用命中时，前四段不会为每个请求重新执行；这通常比微调某个加密算法更值得检查。

## TLS 1.3 减少了哪些等待

### 完整握手

在常见的 TLS 1.2 完整握手中，客户端要在收到服务器第一轮握手消息后发送密钥交换与 Finished，服务器确认后才进入应用数据阶段，连接成本通常按两个网络往返理解。TLS 1.3 让客户端在首个 ClientHello 中发送 key share，完整握手可在一个往返后发送应用数据。这里比较的是协议消息路径，不能直接换算成固定百分比或固定毫秒数。

Android 10（API 29）起，平台 TLS 实现默认启用 TLS 1.3。该版本的 Android 文档同时明确：平台 TLS 1.3 socket 不支持 0-RTT。Android 17 上，应用通过 `SSLSocket`、`SSLEngine` 或依赖平台 provider 的网络库使用 TLS 1.3，仍要以网络库公开的能力和服务端协商结果为准。

### 连接复用和会话恢复

这三个概念容易混淆：

| 机制 | 是否新建传输层连接 | 是否重新进行 TLS 握手 | 适用时机 |
|:---|:---:|:---:|:---|
| HTTP 连接复用 | 否 | 否 | 原连接仍可用 |
| TLS 会话恢复 | 是 | 是，但使用 PSK/session state 缩短协商 | 原连接已关闭，双方仍保留恢复状态 |
| TLS 1.3 0-RTT | 是 | 恢复握手中提前发送 early data | 网络栈、服务端和业务语义均允许 |

OkHttp 5.3 的默认连接池保留最多 5 条空闲连接，每条空闲连接的 keep-alive 时长为 5 分钟。“5”是空闲连接上限，不是客户端总并发连接数。不要因为某个经验数字就扩大连接池；应先统计 `connectionAcquired` 命中、新建连接率、域名数量和服务端空闲超时，再调整 `maxIdleConnections` 与 keep-alive。

会话恢复发生在新连接上。客户端有可用 ticket，并不保证服务端接受恢复：服务端重启、ticket key 轮换、负载均衡路由和 ticket 有效期都可能让连接转为完整握手。仅看客户端的 `secureConnectStart`/`secureConnectEnd` 也无法可靠判断是否恢复，应结合 TLS 库日志或服务端的 full/resumed handshake 指标。

### 0-RTT 的限制来自“可重放”

TLS 1.3 early data 可能被攻击者重放，RFC 8446 要求应用协议评估重复执行的后果。HTTP 方法名只能作为初筛条件：一个 GET 请求也可能消费一次性令牌、改变计数器或读取带时序约束的敏感资源；某些 POST 请求在业务上则可能具备幂等键。安全条件应写成“该请求被重复执行也不会产生不可接受后果”，不能简化为 GET/HEAD 白名单。

OkHttp 5.3 的稳定公开协议配置没有 HTTP/3 或 TLS early-data 开关。Cronet 的 `QuicOptions.Builder.enableTlsZeroRtt()` 面向 QUIC/TLS 0-RTT；平台 `HttpEngine` 的 QUIC hint 也不等于某个请求已使用 early data。启用前应确认以下事项：

- 网络库版本和具体传输协议支持 0-RTT；
- 服务端具备 replay 防护，并能区分 early data；
- 请求语义允许重放，鉴权材料也允许在 early data 中发送；
- 指标能区分普通恢复、0-RTT 被接受和 0-RTT 被拒绝后重发。

## Android 网络安全能力的版本边界

| 版本 | 已核对的平台变化 | 迁移含义 |
|:---|:---|:---|
| Android 6.0 / API 23 | `android:usesCleartextTraffic` 与 `NetworkSecurityPolicy` 进入平台 | 应用可声明和查询明文策略 |
| Android 7.0 / API 24 | Network Security Configuration 上线 | 可按域名配置明文、信任锚、调试证书和证书固定 |
| Android 9 / API 28 | targetSdk 28 及以上默认不允许明文流量 | 旧应用升级 targetSdk 时要检查 HTTP 端点 |
| Android 10 / API 29 | 平台 TLS 1.3 默认启用；平台 TLS socket 不支持 0-RTT | TLS 版本与 early data 能力要分别判断 |
| Android 15 / API 35 | 新增 `android.crypto.hpke.HpkeSpi` | provider 实现层获得标准 SPI |
| Android 16 / API 36 | 应用可在 Network Security Configuration 中选择启用 CT | 升级 targetSdk 37 前可先做兼容性验证 |
| Android 17 / API 37 | ECH 进入平台网络安全配置；targetSdk 37 及以上默认启用 CT；新增应用层 HPKE API | 同时核对运行系统、targetSdk、网络库和服务端 |

Android 的 Java TLS 路径由 Conscrypt 等安全 provider 实现，底层使用 BoringSSL。模块化更新能让部分实现随 Google Play 系统更新交付，但设备、模块版本和厂商支持存在差异。诊断报告应记录设备 build fingerprint、provider 名称与版本，不能只记录“Android 17”。

## Android 17 的 Encrypted Client Hello

普通 TLS ClientHello 会暴露 SNI 等元数据。ECH（RFC 9849）把敏感的 ClientHello 内容放入加密的 inner ClientHello，外层仍保留可完成路由和兼容协商的信息。网络观察者仍可能依据 IP、流量形态和 DNS 看到部分元数据，ECH 不等于隐藏全部访问行为。

### 四个生效条件

Android 17 的 `<domainEncryption>` 提供 `enabled` 和 `disabled` 两种公开模式。对于运行在 Android 17、targetSdk 37 及以上的应用，平台配置默认启用 ECH。一次连接要发出有效 ECH，还要同时满足：

1. 应用使用的网络库已经接入 Android ECH 能力；
2. DNS 或网络库获得了服务端可用的 ECHConfig；
3. 服务端终止 TLS 的基础设施支持对应配置；
4. 当前连接路径没有绕过平台网络安全策略。

官方文档对 `enabled` 的定义很具体：存在 ECHConfig 时要求使用 ECH；没有配置时发送 ECH GREASE，以降低协议僵化风险。`disabled` 既不启用 ECH，也不发送 GREASE。应用通常不应自行解析和安装 ECHConfig，交给已经完成平台接入的网络库处理。

AOSP `android-17.0.0_r1` 中，Conscrypt 的 `SSLParametersImpl.getEchOptions()` 根据网络安全策略生成 ECH 选项；`Platform` 会把配置不匹配包装为 `android.net.ssl.EchConfigMismatchException`，其中可携带服务端返回的重试配置。这说明“ECH 失败后静默改用普通 TLS”不是可靠的统一行为。网络库可能按重试配置重连，也可能把失败交给调用者。

### ECH 的性能应分两段测量

ECHConfig 常由 DNS HTTPS 资源记录分发。查询是否产生额外网络等待，取决于缓存、解析器是否并行查询 A/AAAA 与 HTTPS 记录、加密 DNS 连接是否复用，以及网络库自己的解析流程。不能统一写成“ECH 增加一次 DNS RTT”。

ClientHello 加密使用 HPKE。客户端只在新 TLS 握手中执行相关密码运算，已建立连接上的 HTTP 请求不会重复执行。评估时分别记录：

- HTTPS 资源记录的缓存命中和查询时长；
- 有 ECHConfig、仅 GREASE、配置不匹配三类连接；
- 完整握手、会话恢复和连接复用比例；
- 同一设备、同一网络条件下的 CPU 时间与握手墙钟时间。

## Android 17 的 Certificate Transparency

CA 签名和系统信任链只能证明证书能追溯到受信任根。CT 通过公开日志和 Signed Certificate Timestamp（SCT）提供额外的可审计证据，用于发现误签或恶意签发。

### 默认值由运行时和 targetSdk 共同决定

Android 16（API 36）提供 CT opt-in。应用运行在 Android 17 且 targetSdk 37 及以上时，平台默认启用 CT。运行在旧系统上的同一 APK 不会获得 Android 17 的平台 CT 验证；targetSdk 低于 37 的应用也不能仅凭“设备是 Android 17”推断默认已开启。

Network Security Configuration 的规则还包含一个容易遗漏的分支：

1. 当前域显式启用 CT 时，执行 CT 验证；
2. 当前域使用用户证书或内联自定义信任锚时，默认不执行 CT；
3. 其他情况继承上层配置。

私有 PKI 和抓包调试环境常落入第二种情况。它解释了为何同一应用的公网站点执行 CT，而使用企业根证书的内网站点表现不同。若业务确需让自定义信任锚也执行 CT，应显式配置并验证证书签发流程，不能用公网证书的经验替代测试。

### Android CT Policy 不是固定的“SCT 至少两个”

策略会按 SCT 交付方式、证书有效期、日志状态和日志运营者判断：

| SCT 交付方式 | Android CT Policy 的检查要点 |
|:---|:---|
| 嵌入证书 | 至少 1 个 SCT 来自检查时处于 Qualified、Usable 或 ReadOnly 状态的日志；证书有效期不超过 180 天时需要来自 2 个不同日志，超过 180 天时需要 3 个；满足数量的 SCT 至少覆盖 2 个日志运营者 |
| OCSP stapling 或 TLS 扩展 | 至少 2 个 SCT 来自检查时合格的不同日志，并覆盖至少 2 个日志运营者 |

日志状态和 Android CT log list 会变化。证书部署流水线应以当前 Android CT Policy 和预发布设备测试为准，不要把表中的数字固化成多年不变的服务端规则。

CT 检查通常使用握手携带的证书、OCSP 响应或 TLS 扩展在本地验证，不应按“额外一次网络请求”估算。迁移期间更常见的影响是握手直接失败，例如 SCT 缺失、日志状态不满足政策、证书链发送错误。客户端要保留异常类型、域名、系统版本和证书摘要；服务端要监控 targetSdk 37 灰度期间的 TLS 失败率。

## 明文策略、信任锚和证书链

### 明文默认值

Android 7.0 及以上可使用 Network Security Configuration 按域名管理明文和信任锚。应用 targetSdk 28 及以上时，`cleartextTrafficPermitted` 的默认值为 `false`；targetSdk 27 及以下默认为 `true`。这是 targetSdk 默认值，不代表所有第三方或 native 网络实现都会遵守。网络库是否查询 `NetworkSecurityPolicy`，需要核对对应代码。

从 HTTP 迁移时，客户端应直接配置 HTTPS URL。先访问 HTTP 再跟随 301/302 会多一次明文请求、一次服务端响应和一条新的 HTTPS 连接路径，还会在重定向前暴露请求元数据。WebView 的 mixed content 策略是另一组配置，不能用普通 API 客户端的明文策略推断 WebView 行为。

### 证书链与证书固定

TLS 服务端应发送叶子证书和客户端建立信任链所需的中间证书，通常不发送根证书，也不发送无关中间证书。证书数据会进入握手字节数；在带宽低、丢包高的网络上，过大的握手更容易跨越多个传输包并触发重传。判断“过长”应看实际链路字节和兼容性，不能套用固定层数。

Network Security Configuration 支持 certificate pinning，但 Android 官方文档不建议一般应用把 pinning 当作默认方案：服务端证书或 CA 轮换处理不当会使应用失联。如果威胁模型要求 pinning，需要准备 backup pin、合理的失效时间、证书轮换演练和远端恢复方案。删除证书校验、信任所有证书或放宽主机名校验都不属于性能优化。

## API 35 与 API 37 的 HPKE 不是同一层接口

HPKE（RFC 9180）把 KEM、KDF 和 AEAD 组合成标准公钥加密方案。它适合用接收方公钥加密较短的消息或会话材料，不替代 HTTPS 的身份验证、连接管理和传输协议。

Android 的 API 演进分为两步：

- Android 15 / API 35 新增 `android.crypto.hpke.HpkeSpi`。它是安全 provider 实现 HPKE 引擎的 SPI，应用开发者不应把它当作日常加密入口。
- Android 17 / API 37 新增 `Hpke`、`Sender`、`Recipient`、`Message` 及参数规范。`Hpke.getInstance()` 提供实例获取，`seal()`/`open()`提供 one-shot 操作，`Sender`/`Recipient`面向多条消息的上下文。

当前 Android 文档标明平台 HPKE 只支持 RFC 9180 的 base mode。base mode 不认证发送方身份；如果业务要求发送方认证，应在协议层增加经过审计的签名或身份绑定设计，不能把“使用接收方公钥加密”当作双向身份认证。

ECH 协议内部也使用 HPKE 加密 inner ClientHello，但应用不需要调用 `android.crypto.hpke.Hpke` 来实现 ECH。自行用应用层 HPKE 包裹 HTTP payload，也不会获得 ECH 对 ClientHello 元数据的保护。

## 加密 DNS 与 ECH 的关系

Android 9 引入 Private DNS 的 DNS over TLS（DoT）设置。AOSP `android-17.0.0_r1` 的 DnsResolver `PrivateDnsConfiguration.cpp` 同时包含 DoT 与 DoH 的配置和查询路径。DoT/DoH 保护客户端到解析器之间的 DNS 传输；ECH 保护 TLS ClientHello 中的敏感字段。两者处理不同的泄露面：

- 只有 DoT/DoH：旁路观察者不易读取 DNS 查询内容，但普通 TLS SNI 仍可能暴露目标域名；
- 只有 ECH：ClientHello 的敏感字段被保护，但明文 DNS 仍可能暴露查询；
- 两者均启用：仍不能隐藏目标 IP、包长、时序和连接频率。

DoH 首次查询也不等于固定增加一个 RTT。已有 HTTP/2/HTTP/3 连接、DNS 缓存、连接竞速和解析器实现都会改变成本。应用层自定义 DNS 还可能绕过系统 Private DNS、HTTPS 记录处理或网络切换语义，采用前要评估这些副作用。

## 建立可核对的性能证据

### 客户端事件

OkHttp `EventListener` 可记录 `dnsStart`/`dnsEnd`、`connectStart`、`secureConnectStart`/`secureConnectEnd`、`connectionAcquired`、`responseHeadersStart` 和失败回调。这些时间点能回答“时间花在哪一段”，却不能独自证明会话已恢复、ECH 已被接受或 CT 的某条规则已命中。

Perfetto 不会自动生成通用的 OkHttp 握手轨道。若要把网络阶段与线程、CPU、Radio 和进程状态对齐，应在网络回调中加入应用 trace slice，或使用 Cronet NetLog、平台网络日志和服务端 TLS 指标补充协议证据。生产日志不要记录会话密钥、完整证书、鉴权头或用户请求内容。

### 服务端指标

服务端至少应能按应用版本和灰度批次观察：

- TLS 版本、cipher suite、ALPN 与完整/恢复握手比例；
- HTTP/2、HTTP/3 连接比例和 0-RTT 接受/拒绝情况；
- ECH 接受、GREASE、配置不匹配和重试；
- 证书链版本、SCT 交付方式与 TLS alert；
- 新连接率、连接寿命、空闲超时和负载均衡迁移。

客户端和服务端时间基准可能不同。分析单次请求时，用 request ID 关联事件；比较分布时，使用同一网络类型、同一设备组和同一发布阶段，避免把用户构成变化误判为协议收益。

### 排查对照表

| 现象 | 优先核对 | 常见误判 |
|:---|:---|:---|
| 同一域名频繁出现 `secureConnectStart` | 客户端实例是否复用、服务端 keep-alive、网络切换、连接失败 | 直接增大空闲连接上限 |
| 首次请求慢，后续请求正常 | DNS 缓存、新连接、完整 TLS 握手、服务端冷路径 | 把整段都归为证书验证 |
| targetSdk 37 灰度后 TLS 失败增加 | Android 17 设备占比、CT Policy、SCT 与自定义信任锚 | 关闭全部证书校验 |
| Android 17 上 ECH 连接失败 | 网络库是否接入、HTTPS 记录、ECHConfig 轮换、`EchConfigMismatchException` | 假定平台总会静默降级 |
| 开启 DoH 后解析变慢 | DoH 连接复用、缓存、解析器地域、网络切换 | 固定认为多一个 RTT |
| HPKE 解密失败 | suite、info、AAD、密钥格式和 base mode 边界 | 把 HPKE 当作 TLS 会话 |

## 与其他章节的关联

- **§12.1 网络性能优化**：连接池、缓存、HTTP/2、HTTP/3 与 OkHttp 事件决定新连接出现的频率并提供分段指标。
- **§12.3 netd 与 DnsResolver**：系统 DNS、Private DNS、HTTPS 资源记录与每网络解析状态。
- **§1.6 版本演进**：适合核对 targetSdk 与运行系统共同改变行为的案例。

## 参考资料

- [Android 17 behavior changes](https://developer.android.com/about/versions/17/behavior-changes-17)：ECH 与 targetSdk 37 的 CT 默认行为。
- [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config)：明文、信任锚、CT、ECH 和证书固定配置。
- [Android Certificate Transparency Policy](https://developer.android.com/privacy-and-security/certificate-transparency-policy)：SCT 数量、日志状态和运营者要求。
- [Android 10 TLS 1.3](https://developer.android.com/about/versions/10/features#tls-1.3)：TLS 1.3 默认启用及平台 0-RTT 边界。
- [Android HPKE package](https://developer.android.com/reference/android/crypto/hpke/package-summary)、[Hpke](https://developer.android.com/reference/android/crypto/hpke/Hpke) 与 [HpkeSpi](https://developer.android.com/reference/android/crypto/hpke/HpkeSpi)：API 35/37 的接口层次与 base mode 限制。
- [AOSP Conscrypt `SSLParametersImpl.java`](https://android.googlesource.com/platform/external/conscrypt/+/android-17.0.0_r1/common/src/main/java/org/conscrypt/SSLParametersImpl.java) 与 [`Platform.java`](https://android.googlesource.com/platform/external/conscrypt/+/android-17.0.0_r1/platform/src/main/java/org/conscrypt/Platform.java)：Android 17 ECH 策略映射与配置不匹配异常。
- [AOSP DnsResolver `PrivateDnsConfiguration.cpp`](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/android-17.0.0_r1/PrivateDnsConfiguration.cpp)：Android 17 DoT/DoH 实现锚点。
- [RFC 8446: TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446)、[RFC 9180: HPKE](https://www.rfc-editor.org/rfc/rfc9180)、[RFC 9849: ECH](https://www.rfc-editor.org/rfc/rfc9849)。
- [OkHttp 5.3 `ConnectionPool.kt`](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/ConnectionPool.kt) 与 [`EventListener.kt`](https://github.com/square/okhttp/blob/parent-5.3.0/okhttp/src/commonJvmAndroid/kotlin/okhttp3/EventListener.kt)：连接池默认值和客户端事件边界。
- [Cronet `QuicOptions.Builder`](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/QuicOptions.Builder.html)：QUIC/TLS 0-RTT 的公开配置面。
