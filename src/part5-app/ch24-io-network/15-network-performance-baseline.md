---
title: "移动网络性能优化实战：DNS、连接、传输与容灾"
chapter: "24.15"
status: ready-for-review
drafted_date: "2026-05-22"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-22"
last_verified_against: "AOSP local sources android-35; Android Developers connectivity/Cronet docs 2026-02/03"
confidence: medium
tags: [network, cronet, http3, dns, weak-network, performance]
related_chapters: ["12.2", "12.3", "12.4", "24.4", "24.5", "24.10", "24.14", "26.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "参考书素材/官方文档/AOSP结构"
material_sources:
  - "intake/research-gaps.md#2026-05-22-网络性能优化"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
  - "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
  - "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - "https://developer.android.com/develop/connectivity/cronet"
sources:
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/network-access-optimization"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/CronetEngine.Builder"
  - type: official
    path: "https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/NetworkQualityRttListener"
  - type: official
    path: "https://developer.android.com/develop/connectivity/network-ops/reading-network-state"
  - type: official
    path: "https://developer.android.com/privacy-and-security/security-config"
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system/dns-resolver"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/DnsResolver.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/NetworkCapabilities.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-35/android/net/TrafficStats.java"
  - type: aosp
    path: "/Users/gracker/Android/sources/android-30/com/android/server/ConnectivityService.java"
  - type: clipping-structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 18.md"
  - type: clipping-structure
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 19.md"
---

# 24.15 移动网络性能优化实战：DNS、连接、传输与容灾

## 范围

性能基线是一份带条件的分布记录：测了哪条用户路径、使用什么版本、网络处于什么状态、请求走了哪种缓存与连接路径、成功和失败如何计数。缺少这些前提的“平均耗时”无法用于回归判断。

平台基准为 Android 17 / API 37 / `android-17.0.0_r1`，重点是建立可重复的网络实验。24.14 已给出请求事件与重试预算，24.5 解释 HTTP/2、HTTP/3 和 QUIC，24.10 解释 HTTPDNS 接入；这里沿用这些机制，讨论样本设计、对照实验和发布门禁。

## 三类基线各自回答一个问题

工程中至少保留三类基线。它们的环境和用途不同，不能把数据合并后计算一个分位值。

| 基线 | 环境 | 回答的问题 | 适合做门禁的指标 |
| --- | --- | --- | --- |
| 确定性基线 | 本地测试服务、固定响应、受控故障代理 | 客户端排队、读写、解码、取消和重试语义是否退化 | 操作耗时、调用数、尝试数、字节数、功能不变量 |
| 设备实验室基线 | 固定真机、系统版本、接入点、网络整形和服务端 | DNS、建连、协议、切网与功耗改动是否符合预期 | 分阶段分布、成功率、协议使用率、恢复时间、能耗 |
| 线上基线 | 真实地区、运营商、设备与服务端版本 | 改动对用户路径和尾延迟有什么影响 | 页面完成、请求成功、P50/P95/P99、后台流量、业务护栏 |

确定性基线可以进入每次提交的 CI。公共互联网和生产 CDN 会受调度、拥塞、证书、服务端发布与时间段影响，适合定时实验和线上灰度，不适合作为每次提交的单一阻断条件。

基线对象也应从用户路径开始。例如“首页可交互”可能包含配置、列表、图片和本地解码，单个 API 变快不保证页面变快。每条关键路径都要定义：

- 开始事件与完成事件。
- 必须成功的请求、允许使用旧缓存的请求和可延后请求。
- 用户等待截止时间与取消条件。
- 允许的网络调用数、物理尝试数和总字节。
- 服务端写操作的幂等与结果查询方式。

## 请求阶段拆分使用同一份指标字典

基线字段沿用 24.14 的请求时间线。报告至少保留逻辑操作、网络库调用、物理连接尝试和 HTTP 交换四个层级，避免一次内部回退被误算成多个用户请求。

| 阶段 | 起止边界 | 缺失时如何解释 | 不能混入的时间 |
| --- | --- | --- | --- |
| 业务队列 | 用户动作到调用网络层 | 无队列也要记录零或明确缺失原因 | OkHttp `Dispatcher` 等待 |
| 调度队列 | 网络库接收调用到开始执行 | 同步调用或未排队时可能没有独立事件 | DNS、代理选择、缓存查找 |
| 缓存路径 | 缓存判定到命中，或转入网络 | 未配置缓存与缓存未命中要分开 | 响应解码与业务缓存 |
| DNS | 解析开始到结果或错误 | 复用连接时通常没有 DNS | 地址建连和 Fast Fallback 等待 |
| connect | 每次地址尝试开始到成功或失败 | 复用连接时没有新建连 | TLS 与后续交换 |
| TLS | 握手开始到验证结束 | 明文、复用连接或库未暴露时为空 | 服务端应用处理 |
| 上传 | 请求头发送开始到请求体完成 | 无请求体时以请求头发送完成为界 | 排队和响应等待 |
| TTFB | 请求发送完成到最终响应开始 | 缓存命中与双工流要使用单独定义 | 响应体下载 |
| 下载 | 响应体开始到读取或关闭 | 提前关闭要记录取消或截断 | 解压、反序列化与界面提交 |
| 本地消费 | 字节可用到业务消费完成 | 后台预取可能没有界面事件 | 网络等待 |

阶段值允许为空。连接复用时把 DNS、connect、TLS 填成零，会把“没有发生”误写成“瞬间完成”；失败发生在 DNS 时，后续阶段同样应为空。聚合前应按缓存路径、连接复用、协议、成功/失败和取消分别统计。

### 用结构化键阻止不兼容样本混算

下面的 Kotlin 数据结构给实验记录建立最小约束。它不负责发请求，只规定哪些环境字段必须随样本保存。

```kotlin
enum class RequestPathState {
    NETWORK_NEW_CONNECTION,
    NETWORK_REUSED_CONNECTION,
    CACHE_HIT,
    CACHE_REVALIDATED,
}

enum class OperationOutcome {
    SUCCEEDED,
    FAILED,
    CANCELED,
    DEADLINE_EXCEEDED,
}

data class NetworkBaselineKey(
    val platformApi: Int,
    val platformBuildId: String,
    val appVersionCode: Long,
    val networkStackName: String,
    val networkStackVersion: String,
    val networkStackConfigId: String,
    val scenarioId: String,
    val requestPathState: RequestPathState,
    val networkSessionId: Long,
    val transports: Set<Int>,
    val validated: Boolean,
    val metered: Boolean,
)

data class NetworkBaselineSample(
    val key: NetworkBaselineKey,
    val operationElapsedNanos: Long,
    val outcome: OperationOutcome,
    val negotiatedProtocol: String?,
    val sentBytes: Long?,
    val receivedBytes: Long?,
    val networkCallCount: Int,
    val connectionAttemptCount: Int,
)
```

`networkSessionId` 是进程内为每个新观察到的 `Network` 分配的临时编号，不上传系统网络句柄。实验室可保存完整系统构建号；线上数据应使用受控分桶，避免形成设备指纹。`scenarioId`、网络栈配置编号和传输集合必须来自白名单，也不能包含账号、URL、IP 或文档名。

分位值只在 `NetworkBaselineKey` 相同或分析者明确选择的维度内计算。系统版本、网络栈提供程序、缓存路径或计费状态不同的样本直接混合，会把环境构成变化误判成代码回归。

## DNS 与地址选择的基线怎么建

Android 10 / API 29 起公开的 `DnsResolver` 支持异步查询，并可传入 `Network`。`android-17.0.0_r1` 的 [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) 仍按目标网络的 `netId` 发起解析。它属于系统解析入口，不等同于业务自建 HTTPDNS。

每种解析方案单独建组：

| 解析路径 | 固定条件 | 必须记录 | 不能由结果推断 |
| --- | --- | --- | --- |
| 系统 DNS | Android `Network`、Private DNS 状态、网络会话 | 是否执行查询、耗时、结果数量、错误类别 | 具体递归解析器的完整内部耗时 |
| HTTPDNS | 服务版本、缓存版本、系统 DNS 回退策略 | 本地命中、过期、请求结果、回退原因 | 返回地址一定可连接或证书一定匹配 |
| 应用内 DoH | DoH 提供方、引导地址、连接复用状态 | 引导方式、查询耗时、HTTP 状态、回退 | Android 系统 DNS 的行为 |
| 平台 Private DNS | 系统设置与 `LinkProperties` 快照 | 是否启用、是否验证、默认网络会话 | 应用请求一定使用某个特定服务器 |

“冷 DNS”需要谨慎命名。应用可以清理自己的 HTTPDNS 缓存，却通常不能在普通测试进程里独占或可靠清理系统解析缓存。若无法控制系统缓存，报告应写“新应用客户端、无应用缓存”，不要写成“系统冷解析”。

地址选择要保留候选数量、地址族、每次尝试的顺序、是否并行、失败类型和获胜尝试。OkHttp 5 的 Fast Fallback 可能并行建立多个连接；只记录最终 IPv4 或 IPv6 会隐藏另一组地址持续失败的问题。生产遥测不保存原始 IP，可使用地址族、匿名化边缘节点编号和服务端返回的区域标记。

TTL 到期只影响后续解析。已经复用的连接不会因为 TTL 到期自动失效，基线也不能用清空连接池来模拟普通 TTL 刷新。HTTPDNS 与 OkHttp 的同步边界继续见 24.10。

## 连接复用与队头阻塞要分路径测试

至少建立四种请求路径：

| 路径 | 实验准备 | 验证目标 |
| --- | --- | --- |
| 新连接 | 无可复用连接，明确 DNS 缓存条件 | 解析、地址选择、connect、TLS 和首个交换 |
| 复用空闲连接 | 同一网络、代理、地址与安全配置，前一请求已完成 | 连接池命中与省去握手后的收益 |
| 多路复用并发 | 同一 HTTP/2 或 HTTP/3 连接发出多请求 | 流数量、优先级、丢包时的尾延迟与大响应干扰 |
| HTTP 缓存 | 分别制造直接命中、条件请求和未命中 | 缓存语义、线上字节与本地读取成本 |

新建一个客户端不一定等于网络全冷：系统 DNS、TLS 状态、Cronet 磁盘数据、服务器 QUIC 信息和 CDN 边缘状态都可能保留。报告要列出清理了哪些状态、保留了哪些状态。

HTTP/1.1 的并发通常依赖多条连接；HTTP/2 在一条 TCP 连接上复用多个流，TCP 丢包会影响该连接上的发送进度；HTTP/3 在 QUIC 中为流提供独立的有序交付，单个流的数据丢失不会按 HTTP/2 的 TCP 字节序阻塞其他流。QUIC 仍共享连接级拥塞控制和路径容量，因此某个流占用大量带宽仍可能影响其他流。

连接合并也要单独标记。不同主机复用 HTTP/2 连接取决于证书、DNS、代理、地址和网络库实现。主机数不能代替连接数，连接复用率也不能单独证明页面更快。

## Cronet、OkHttp、HttpEngine 与 Mars 的可比性

选型实验应记录实际实现，不使用“Cronet 组”“OkHttp 组”这种过宽标签。

| 网络栈 | 基线必须固定 | 可用观测 | 主要边界 |
| --- | --- | --- | --- |
| OkHttp 5.x | 精确版本、拦截器顺序、`Dispatcher`、连接池、DNS、协议列表 | `EventListener`、`Response.protocol`、应用事件 | 默认客户端没有 HTTP/3；事件可因复用、重试和重定向而缺失或重复 |
| Cronet 库 | Maven 版本、实际 `CronetProvider`、引擎版本、缓存目录和配置 | `RequestFinishedInfo.Metrics`、`UrlResponseInfo`、网络质量估计、NetLog | Java 回退实现与原生实现不等价；NetLog 只用于受控诊断 |
| 平台 `HttpEngine` | API/SDK 扩展版本、模块版本、缓存与 QUIC/Brotli 配置 | `UrlResponseInfo` 与公开回调 | `android-17.0.0_r1` 没有后续 37.1 才加入的完整请求计时 API |
| Mars 或自有长连接 | 仓库提交、协议版本、心跳、连接复用、加密与重连策略 | 团队定义的消息确认、积压、重连和字节指标 | 指标需和 HTTP 请求分开，不能用库名称代替具体实现 |

Cronet 的 `RequestFinishedInfo.Metrics` 能提供请求、DNS、连接、TLS、发送、响应开始和结束等时间。复用套接字时 DNS、连接和 TLS 时间为空；重定向相关计时与字节按该 API 的定义累计，分析前要阅读所用 Cronet 版本的接口说明。`UrlRequest.Builder.addRequestAnnotation()` 可关联请求类型，但注解对象仍要遵守低基数和无个人信息原则。

Cronet 网络质量估计器的 RTT 样本可能来自 TCP、QUIC 或 URL 请求层，吞吐样本来自网络栈观察。它们是网络状态信号，不是某条请求的 DNS、TTFB 或下载耗时替代值。未启用估计器或没有足够观察时，API 会返回未知值，不能填入默认网速。

跨网络栈比较时，业务拦截器、缓存、压缩、Cookie、代理、证书验证、线程执行器和响应读取方式必须一致。若同时从 OkHttp 切到 Cronet 并启用 HTTP/3，结果包含“实现变化”和“协议变化”两个变量，无法单独归因给 QUIC。

## HTTP/3、QUIC 与网络切换的实验设计

隔离协议影响时，优先在同一个 Cronet 或 HttpEngine 实现中只改变 QUIC 开关，其余配置保持一致。实验组还要按以下状态分开：

- 首次连接、已有 QUIC 服务器信息、具备可用会话状态。
- HTTP/3 成功、主动禁用、UDP 不可达后回到 HTTP/2 或 HTTP/1.1。
- 直接响应、重定向、HTTP 缓存命中和条件请求。
- 请求前切网、上传期间切网、等待响应时切网、下载期间切网。

每次切网实验记录旧、新 `Network` 的临时编号和能力快照、切换发生时的请求阶段、已发送与已接收字节、最终协议、是否重新建连、业务层是否重复提交。QUIC 支持连接迁移不表示每个提供程序、服务端和路径都会迁移成功；代理、VPN、NAT、服务器配置和连接迁移选项都会改变结果。

UDP 阻断测试必须保留从首次 QUIC 尝试到 HTTP 回退完成的总耗时。只比较成功的 HTTP/3 与成功的 HTTP/2，会漏掉协议探测失败造成的尾延迟。服务端同时记录 ALPN、QUIC 版本、连接 ID 迁移、重试令牌和错误分类，客户端不要从端口或 URL 推断协议。

0-RTT 单独建组，并只用于可重放的操作。客户端与服务端要共同验证重复到达时的语义，状态变更请求不能因“更快”直接进入早期数据。

QUIC 状态机位于用户空间网络栈，Android common kernel 负责 UDP 套接字、IP、路由、队列和驱动。内核证据以 `android17-6.18-2026-06_r6` 为基准，UDP 发送路径可从 [`net/ipv4/udp.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c) 继续检查。应用层不能把内核 UDP 统计直接当作 HTTP/3 请求结果。

## 弱网容灾基线检查不变量

故障注入的目标是验证行为，而非追求某个漂亮耗时。每种故障都要写出客户端允许做什么、禁止做什么。

| 故障 | 要验证的行为 | 主要风险 |
| --- | --- | --- |
| DNS 超时、无答案、NXDOMAIN | 错误分类、系统 DNS 或缓存回退、总截止时间 | 多层解析同时重试 |
| 单个地址超时或拒绝连接 | Fast Fallback、失败隔离、尝试上限 | 并行连接过多 |
| 证书链或主机名错误 | 立即失败并保留安全错误 | 被错误归类为可重试弱网 |
| 上传后连接断开 | 结果未知、幂等查询或恢复 | 重复下单、支付或发消息 |
| 429、503 与 `Retry-After` | 尊重服务端等待要求和逻辑操作截止时间 | 客户端请求风暴 |
| 响应头慢、响应体截断 | TTFB 与下载阶段分离、关闭资源 | 只记录响应码为成功 |
| 网络切换、VPN 变化 | 取消或恢复符合幂等规则 | 全量清池与集中重建 |
| 页面退出与任务取消 | 网络调用停止、回调不再更新界面 | 遗留下载和无效解码 |

超时参数来自用户路径截止时间和各阶段历史分布，不能复制一组全局数字。网络库内部恢复、业务重试、图片库重试和 WorkManager 退避都要计入同一个逻辑操作。有关实现顺序与幂等边界见 24.14。

熔断的粒度通常是具体服务、路由或接入点，并带有限制并发的探测恢复。对全站使用一个熔断状态，可能让局部故障扩大成整站不可用。备用域名和 IP 还必须通过证书、SNI、Host、Cookie、鉴权和服务端风控校验。

## 数据体积与传输成本分两个轴比较

序列化格式决定业务数据怎样表示，内容编码决定表示结果怎样压缩。两者是正交变量，应比较 JSON、Protocol Buffers 等表示在相同字段集合下的大小和解析成本，再比较 gzip、Brotli、Zstandard 等内容编码在相同输入上的线上字节与 CPU。

| 变量 | 需要固定 | 需要测量 | 兼容边界 |
| --- | --- | --- | --- |
| JSON 字段集合 | 业务语义、空值与默认值策略 | 未压缩字节、解析 CPU、对象分配 | 服务端与旧客户端字段兼容 |
| Protocol Buffers | schema、未知字段、默认值与版本 | 编码字节、序列化/反序列化 CPU | schema 演进和调试工具 |
| gzip | 压缩级别、服务端实现、响应类型 | 线上字节、压缩与解压 CPU | 客户端透明解压后的字段口径 |
| Brotli | 质量等级、静态或动态响应、网络栈开关 | 线上字节、首包与 CPU | HttpEngine 默认关闭 Brotli，实际配置要入样本 |
| Zstandard | 客户端/服务端支持、内容协商、可选字典版本 | 线上字节、CPU、内存和失败回退 | 不能假定所有 Android 网络栈自动支持 |
| 业务字典 | 字典 ID、版本、灰度与回滚 | 命中率、字节、解码失败 | 客户端与服务端必须同时拥有兼容字典 |

请求字段裁剪、分页和差量更新往往比更换压缩算法更早减少无用数据。基线因此要同时记录业务使用字节和线上传输字节，防止“压缩率提高”掩盖响应仍包含大量首屏不用的字段。

字节指标必须带口径。Cronet `UrlResponseInfo.getReceivedByteCount()` 返回处理该请求所需的最小网络接收字节，发生在解压前，包含重定向的头部与数据，但不保证包含 IP、TCP/UDP、TLS 和代理等全部开销。OkHttp 事件字节、响应体长度、`TrafficStats` UID 差值也各有定义，不能放进同一列直接比较。

序列化和解压 CPU 可用 Microbenchmark 在固定输入上测量；端到端页面可用 Macrobenchmark 配合本地固定响应观察。远程网络波动会污染 CPU 微基准，不应把真实互联网请求放入循环微基准。

## 验证与回归防护

### 固定环境，再做 A/B

同一轮对照实验至少固定：

- 物理设备、Android 版本、系统构建和相关 Mainline 模块状态。
- 发布型 APK、编译状态、代码压缩配置和应用数据准备方式。
- 网络接入点、代理/整形配置、计费与验证能力、VPN 和 Private DNS 状态。
- 网络栈版本、提供程序、缓存目录、协议开关和连接预热方式。
- 服务端版本、响应内容、缓存指令、边缘节点与证书配置。
- 实验顺序、并发背景任务、充电与温度条件。

Android 官方性能指南要求使用接近发布的构建，并在同一设备与系统版本上做 A/B。Debug 构建、调试器、持续抓包和详细 NetLog 都会增加开销，只用于定位，不进入正式基线。

为降低时间漂移，可以在同一设备上交错运行基线组与候选组，并随机化用例顺序。网络切换、DNS 缓存、CDN 状态等跨用例状态仍需显式重置或记录；“重新启动应用”不是完整清理方案。

### 统计时先看分母

报告顺序建议固定为：

1. 样本数、成功、失败、取消和截止时间超限。
2. 每个逻辑操作的网络调用数、连接尝试数和总字节。
3. 成功样本的 P50、P95、P99 与置信区间。
4. 按缓存路径、协议、网络能力、地区、运营商、设备和版本分组。
5. 页面完成、业务正确性、后台流量和功耗护栏。

只对成功样本计算延迟会产生幸存者偏差：候选方案若更早失败，成功请求可能看起来更快。成功率和延迟必须并列展示，失败请求也要保留失败阶段与已消耗时间。

回归阈值来自用户体验目标、历史波动、样本量和实验成本。固定的通用毫秒阈值无法覆盖首页 API、媒体、长连接和后台同步。门禁配置应保存基线版本、适用场景、统计窗口和阈值来源，基线也不能永远指向“上一轮结果”，否则连续小幅退化会逐次被接受。

### 工具各看一层

| 工具 | 适合观察 | 不适合回答 |
| --- | --- | --- |
| OkHttp `EventListener` | 调度、DNS、连接、TLS、交换、缓存和重试决策 | Cronet、WebView 或自有套接字流量 |
| Cronet 完成信息与网络质量估计 | Cronet 请求时间、字节、协议与网络状态样本 | 平台外部网络栈或业务页面完成 |
| `NetworkCapabilities` / `LinkProperties` | 网络会话、能力、传输集合、路由与 DNS 配置 | 端到端实测速率；带宽字段只是首跳估算 |
| `TrafficStats` | 当前 UID 跨接口的粗粒度累计字节 | 单请求、单域名、后台移动流量或协议开销 |
| Perfetto 与应用 Trace | 线程调度、CPU、Binder、GC 和本地处理时间关系 | 完整 DNS、TLS、HTTP/3 语义 |
| 服务端追踪记录 | 接入层排队、上游耗时、响应字节与限流 | 客户端队列、无线网络和本地解码 |
| Macrobenchmark | 带固定数据源的用户路径完成与系统 Trace | 不受控公共互联网的稳定协议门禁 |

Android vitals 的后台移动网络、Play Console 业务指标和线上请求遥测属于发布护栏。实验室协议收益成立后，仍要分阶段灰度，并为失败率、P99、重试数、后台字节、服务端 CPU 和业务成功率设置独立停止条件。

## 扩展：Android 10 到 Android 17 的网络基线变化

版本演进会改变实验环境，同一应用版本也可能因 Mainline 模块更新而出现差异。

| 平台节点 | 与基线相关的变化 | 记录要求 |
| --- | --- | --- |
| Android 10 / API 29 | `DnsResolver` 成为公开异步 API；DNS Resolver 以 `com.android.resolv` APEX 交付 | 系统构建、解析路径、Private DNS 和模块状态 |
| Android 14 / API 34 | 平台加入 `HttpEngine`，也标注为 Android S 扩展 7 | API/扩展版本、HttpEngine 配置与实现版本 |
| Android 17 / API 37 | CT 默认策略变化；平台提供 ECH 支持与网络安全配置 | `targetSdk`、安全配置、网络库 ECH 支持和系统构建 |

`NetworkCapabilities.getLinkDownstreamBandwidthKbps()` 与上行对应接口只表示系统估计的首跳传输带宽，不是服务器到应用的端到端吞吐。Wi-Fi、蜂窝、VPN 和卫星等传输类型也不能直接代表计费、延迟或可用带宽。Android 17 源码定义可在 [`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) 中核对。

IPv6 也不单独判定快慢。IPv6-only/NAT64、双栈地址顺序、代理、运营商、边缘节点和服务端路由共同决定请求结果。基线用连接尝试与端到端结果回答问题，不用地址族做先验结论。

## 扩展：安全策略也是基线条件

Android 17 / API 37 的网络安全配置需要进入 TLS 基线。面向 API 37 的应用默认启用证书透明度；ECH 的平台配置默认开启，但只有网络库和服务端都支持时才会使用，协商失败时还可能发送 ECH GREASE。配置为 enabled 不能证明某条请求已协商 ECH，只有网络栈公开结果或受控服务端记录能提供证据。详细机制见 24.18。

性能实验不得安装“信任所有证书”的 `TrustManager`、宽松主机名验证或明文回退。若测试代理需要解密 HTTPS，应使用仅存在于测试构建的调试 CA，并把“经过代理”和“直接连接”分成两组。

Android 官方文档不建议普通应用进行证书固定。固定公钥会把服务端证书轮换与客户端版本覆盖绑定在一起；若风险评估后仍采用，基线必须包含备用公钥、过期策略、旧版本客户端和轮换演练。客户端无法连到服务端时，所谓远程开关也未必能送达。

TLS 会话恢复与 0-RTT 不能合并成“复用握手”一个字段。0-RTT 有重放风险，只允许经过服务端确认的可重放操作；测试还要验证早期数据被拒绝后的重发语义。

## 扩展：系统侧证据锚点

应用观察到 DNS 慢、切网或连接失败时，按职责查源码：

| 层级 | Android 17 锚点 | 能回答的问题 |
| --- | --- | --- |
| 应用 DNS API | [`DnsResolver.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/DnsResolver.java) | 查询如何绑定 `Network`、取消和回调 |
| 网络能力模型 | [`NetworkCapabilities.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/framework/src/android/net/NetworkCapabilities.java) | 验证、计费、受限、传输与首跳带宽字段语义 |
| 系统网络选择 | [`ConnectivityService.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/ConnectivityService.java) | 默认网络匹配、能力变化与回调分发 |
| DNS Resolver 模块 | [`packages/modules/DnsResolver`](https://android.googlesource.com/platform/packages/modules/DnsResolver/+/refs/tags/android-17.0.0_r1/) | 系统 stub resolver、缓存和解析实现 |
| Linux UDP | [`udp.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/ipv4/udp.c) | QUIC 下方的 UDP 发送、套接字与错误路径 |

DNS Resolver 从 Android 10 起以 `com.android.resolv` APEX 交付。官方模块说明指出，它由 `netd` 动态链接，同时直接服务 `/dev/socket/dnsproxyd`，解析器配置的 Binder 入口也已移到该模块。Android 17 上不应继续用 Android 9 以前“所有解析都由 netd 内部实现”的结构解释问题。

这些源码用于确认平台职责和公开语义。普通应用仍应通过 SDK、网络库和服务端观测定位，不绕过平台路由、权限、证书验证或后台限制。

## 上线前检查清单

- 每条基线都带场景、版本、网络栈配置、网络会话、缓存路径和结果状态。
- 确定性 CI、设备实验室和线上基线没有混算。
- 冷 DNS、冷连接、复用连接与缓存命中的准备条件写清楚。
- 失败、取消和截止时间超限进入分母，不只统计成功请求。
- DNS、connect、TLS 缺失表示阶段未发生或不可观测，不填零。
- 协议来自网络栈公开结果，HTTP/3 失败后的回退时间计入逻辑操作。
- A/B 只改变计划验证的变量；网络栈与协议同时变化时明确承认混杂。
- 弱网用例检查幂等、取消、资源关闭和尝试上限。
- 压缩比较区分业务表示、线上编码、解压后字节和 UID 总流量。
- Android 17 的 CT、ECH、网络能力和 Mainline 模块状态进入实验记录。
- 发布门禁说明阈值来源，并同时检查成功率、尾延迟、字节、功耗与业务护栏。

## 参考资料

- [Android 17 / API 37 公开 API 签名](https://android.googlesource.com/platform/prebuilts/sdk/+/refs/tags/android-17.0.0_r1/37.0/public/api/android.txt)
- [读取 Android 网络状态](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)
- [Cronet 功能与接入](https://developer.android.com/develop/connectivity/cronet)
- [Cronet RequestFinishedInfo 源码](https://chromium.googlesource.com/chromium/src/+/lkgr/components/cronet/android/api/src/org/chromium/net/RequestFinishedInfo.java)
- [Cronet 网络质量 RTT](https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/NetworkQualityRttListener)
- [Android 网络安全配置](https://developer.android.com/privacy-and-security/security-config)
- [Android 17 行为变化](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android DNS Resolver 模块](https://source.android.com/docs/core/ota/modular-system/dns-resolver)
- [Android 应用性能测量](https://developer.android.com/topic/performance/measuring-performance)
- [Android Benchmark 概览](https://developer.android.com/topic/performance/benchmarking/benchmarking-overview)
- [TrafficStats API](https://developer.android.com/reference/android/net/TrafficStats)
- [Zstandard Content-Encoding：RFC 9659](https://www.rfc-editor.org/rfc/rfc9659.html)
