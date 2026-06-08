---
title: "HTTPDNS 与 OkHttp Dns 执行边界"
chapter: "24.10"
section: "24.10"
drafted_date: "2026-05-16"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37) / OkHttp 4.x - 5.x"
last_verified: "2026-06-09"
last_verified_against: "OkHttp 5.x docs + OkHttp source 728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab + DeepResearch 2026-05-14 + Clippings 结构参考"
confidence: medium
sources:
  - type: official
    path: "https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dns/"
  - type: official
    path: "https://square.github.io/okhttp/features/connections/"
  - type: official
    path: "https://square.github.io/okhttp/features/events/"
  - type: source
    path: "https://raw.githubusercontent.com/square/okhttp/728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt"
  - type: source
    path: "https://raw.githubusercontent.com/square/okhttp/728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealRoutePlanner.kt"
  - type: source
    path: "https://raw.githubusercontent.com/square/okhttp/728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab/okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RouteSelector.kt"
  - type: source
    path: "https://raw.githubusercontent.com/square/okhttp/728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab/okhttp-dnsoverhttps/src/main/kotlin/okhttp3/dnsoverhttps/DnsOverHttps.kt"
  - type: source
    path: "https://raw.githubusercontent.com/square/okhttp/728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab/okhttp-dnsoverhttps/README.md"
  - type: blog
    path: "DeepResearch/2026-05-14-okhttp-dns-lookup-httpdns-engineering.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
tags: [network, httpdns, okhttp, dns, latency]
related_chapters: ["12.2", "12.3", "24.4", "24.5", "26.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "章节深挖/研究素材"
last_task2a_at: "2026-05-16T16:04:00+08:00"
status: finalized
reviewed_by: openclaw-task6
reviewed_date: "2026-05-16"
task6_state: revisiting
task6_result: pass-light-edit
task9_state: reviewed
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
pipeline_stage: task6_pending
last_task6_at: "2026-05-16T16:10:00+08:00"
last_task6_audit: "2026-06-08"
last_task6_review_log: "logs/review/2026-05-16-16-review.md"
task6_l1_l2_fixes: 9
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-16 Task6：首次写作质检通过；修复 outline 重复描述、禁用词和兜底表述 9 处；无 L3/L4 回炉项，送 Task9 技术复核。"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-16"
last_task9_at: "2026-05-16T16:30:00+08:00"
last_task9_audit: "2026-06-09"
last_task9_autofix_at: "2026-06-09"
last_task9_review_log: "logs/deep-review/2026-05-16-16-deep-review.md"
task9_review_notes: "2026-05-16 Task9：深度技术审计通过；OkHttp Dns.lookup()、RouteSelector、DnsOverHttps bootstrap、EventListener 与 fast fallback 口径已核对；无 P0/P1/P2，自动晋升 finalized / ready-to-publish。 | 2026-06-09 Task9 闲时抽检：auto-fixed。P0 源码锚点 2 处；修正 OkHttp Dns.kt master 路径、RealRoutePlanner commit 归属，并将 frontmatter OkHttp raw source pin 到 source 728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab。"
---

# 24.10 HTTPDNS 与 OkHttp Dns 执行边界

<!-- outline-start -->
## 要点

### 🔹 OkHttp Dns.lookup() 的调用位置
说明 `Dns.lookup()` 在 `RealRoutePlanner` / `RouteSelector` 中同步参与 route 生成，返回前请求无法进入 connect。

### 🔹 HTTPDNS 同步查询的阻塞风险
说明在 `lookup()` 内发起 HTTPDNS 请求会把弱网、递归解析和 Dispatcher 挤占带进建连路径。

### 🔹 异步预取与缓存读取模型
说明 HTTPDNS 网络请求应前置到后台刷新，`lookup()` 只读取缓存并在失败时兜底系统 DNS。

### 🔹 失败 IP 隔离与系统 DNS 兜底
说明按 hostname + IP + network 做失败隔离，避免单点失败污染整个域名。

### 🔹 网络切换后的 TTL 与缓存刷新
说明 Wi-Fi、蜂窝和 VPN 切换后如何保留短时兜底并刷新高价值域名。

### 🔹 弱网验证与线上指标设计
说明用 EventListener、弱网演练和线上指标验证 DNS 优化没有拉高尾延迟。

## 扩展

### 🔸 DoH / HTTPDNS / 系统 DNS 的选型对照表
待结合素材验证后展开。

### 🔸 多 IP fast fallback 与连接池复用边界
待结合素材验证后展开。

<!-- outline-end -->

HTTPDNS 接入最容易出问题的位置不在“能不能拿到 IP”，而在 `Dns.lookup()` 被 OkHttp 调用的时机。这个回调属于建连前的路由规划路径，返回 IP 列表之前，请求不能继续进入 TCP connect。把实时 HTTPDNS 请求塞进 `lookup()`，会把弱网 HTTP 请求、服务可用性和递归解析风险一起带进建连路径。

24.4 已经讲过网络层的连接、解析、调度、容错四个控制面；12.3 负责连接池、TLS 和传输细节。本节只展开 HTTPDNS 与 OkHttp `Dns` 的工程边界：同步路径只读缓存，网络查询放到异步预取，兜底路径保留系统 DNS。

参考书用于组织写作顺序：拆等待段、看任务预取和缓存命中，再落到指标验证。正文不使用参考书原文，也不复用参考书代码。 [结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md] [结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md] [结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

## OkHttp Dns.lookup() 在哪条路径上执行

OkHttp 的 `Dns` 文档把接口定义得很窄：给定 hostname，返回 OkHttp 将按顺序尝试的 IP 地址列表；实现必须支持并发调用。默认实现是 `Dns.SYSTEM`，内部委托 `InetAddress.getAllByName()`。 [已验证: 官方文档, https://square.github.io/okhttp/5.x/okhttp/okhttp3/-dns/] [已验证: OkHttp source, okhttp3/Dns.kt]

连接规划里，URL 会被拆成 `Address` 和 `Route`。OkHttp connections 文档说明，`Route` 包含 DNS 查询得到的具体 IP、代理和 TLS 版本；没有 route，就没法创建 socket。 [已验证: 官方文档, https://square.github.io/okhttp/features/connections/]

在 OkHttp 5 当前源码里，路径可以压缩成这样：

```text
RealRoutePlanner.plan()
  → planConnect()
    → RouteSelector.next()
      → resetNextInetSocketAddress(proxy)
        → address.dns.lookup(socketHost)
        → InetSocketAddress(inetAddress, socketPort)
```

`RealRoutePlanner.planConnect()` 的注释直接写出“List available IP addresses for the current proxy. This may block in Dns.lookup().”；`RouteSelector.resetNextInetSocketAddress()` 在非 SOCKS 代理路径下调用 `address.dns.lookup(socketHost)`，空结果会抛出 `UnknownHostException`。 [已验证: OkHttp source, RealRoutePlanner.kt] [已验证: OkHttp source, RouteSelector.kt]

这条路径带来三个约束：

- `lookup()` 是同步回调，返回前会占住当前 call 的建连流程。
- `lookup()` 可能被多个请求同时调用，内部缓存、失败隔离表和刷新状态都要并发安全。
- `lookup()` 抛出的 `UnknownHostException` 会变成这次路由规划失败，不能把可降级错误随意抛出去。

## HTTPDNS 同步查询会放大哪些风险

HTTPDNS 服务本身也是 HTTP 服务。若在 `lookup()` 内实时请求 HTTPDNS，就会把一个 HTTP call 嵌进另一个 HTTP call 的建连前置阶段。

```kotlin
class BlockingHttpDns(
    private val client: OkHttpClient,
    private val endpoint: HttpUrl,
) : Dns {
    override fun lookup(hostname: String): List<InetAddress> {
        // 反例：业务请求的 DNS 阶段又发起一次 HTTP 请求。
        val request = Request.Builder()
            .url(endpoint.newBuilder().addQueryParameter("host", hostname).build())
            .build()

        client.newCall(request).execute().use { response ->
            return parseAddresses(response.body.string())
        }
    }
}
```

这段代码有四类风险。

| 风险 | 触发条件 | 线上表现 |
|---|---|---|
| 建连路径阻塞 | HTTPDNS 服务慢、弱网、TLS 握手慢 | `dnsStart → dnsEnd` 变长，所有新连接排队 |
| 递归解析 | HTTPDNS 请求复用同一个配置了自定义 `Dns` 的 client | HTTPDNS 域名也进入同一个 `lookup()`，递归或超时 |
| Dispatcher 互相挤占 | HTTPDNS 请求和业务请求共用 Dispatcher | 首屏请求等待 HTTPDNS 查询队列，故障时互相拖慢 |
| 错误传播过重 | HTTPDNS 返回空、5xx、超时后直接抛异常 | 系统 DNS 本可成功，请求却以 `UnknownHostException` 结束 |

OkHttp 的 DoH 模块提供了一个很好的对照。`DnsOverHttps.lookup()` 内部会发 HTTP 请求，并用 `CountDownLatch.await()` 等待 A / AAAA 响应；它的 Builder 会给 DoH client 设置 bootstrap DNS，README 示例也使用 `bootstrapClient` 和 `bootstrapDnsHosts(8.8.4.4, 8.8.8.8)`，避免 DoH 服务自身还要依赖未完成的自定义 DNS 解析。 [已验证: OkHttp source, okhttp-dnsoverhttps/DnsOverHttps.kt] [已验证: OkHttp README, okhttp-dnsoverhttps/README.md]

自研 HTTPDNS 也要沿用这个边界：HTTPDNS 查询可以使用独立 bootstrap client；业务主 client 的 `Dns.lookup()` 不做实时网络 I/O。

## 异步预取与缓存读取模型

更稳的模型是把 HTTPDNS 拆成两条路径：后台刷新路径负责发网络请求，`Dns.lookup()` 同步路径只读本地结果。

```text
App 启动 / 首页前置 / 网络恢复
  → HttpDnsPrefetcher.refresh(hosts)
    → bootstrapClient 请求 HTTPDNS 服务
    → 校验 TTL、IP 格式、网络类型
    → 写入内存缓存和磁盘快照

OkHttp 建连
  → Dns.lookup(hostname)
    → 读内存缓存
    → 内存未命中时读磁盘快照
    → 过滤过期与隔离 IP
    → 无可用结果时 fallback 到 Dns.SYSTEM
```

这个设计把“提升命中率”和“控制等待段”放到了同一套工程动作里。参考书里讲预加载和缓存命中率的思路，在这里对应两个具体动作：在用户进入高概率网络场景前预取域名；在建连路径上只做常数级缓存读取。 [结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md] [结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

同步 `Dns` 可以写成下面这种形态。代码是工程骨架，字段和持久化格式按项目替换。

```kotlin
class CachedHttpDns(
    private val memory: HttpDnsMemoryCache,
    private val disk: HttpDnsDiskSnapshot,
    private val quarantine: IpQuarantine,
    private val fallback: Dns = Dns.SYSTEM,
    private val refresh: (String) -> Unit,
    private val clock: Clock,
) : Dns {
    override fun lookup(hostname: String): List<InetAddress> {
        val nowMs = clock.millis()
        val cached = memory.get(hostname, nowMs)
            ?: disk.get(hostname, nowMs)?.also { memory.put(hostname, it) }

        val usable = cached
            ?.addresses
            .orEmpty()
            .filterNot { quarantine.isBlocked(hostname, it, nowMs) }

        if (cached == null || cached.shouldRefresh(nowMs)) {
            refresh(hostname)
        }

        if (usable.isNotEmpty()) return usable
        return fallback.lookup(hostname)
    }
}
```

这段实现只做本地读取和过滤，不在 `lookup()` 内执行 HTTP 请求。`refresh(hostname)` 只投递后台任务；即使刷新失败，也不影响当前请求用系统 DNS 继续建连。

后台预取器单独持有 bootstrap client。它可以使用系统 DNS、固定 bootstrap IP、DoH bootstrap host 或厂商 SDK 提供的初始化入口；不要复用业务主 client 的自定义 `Dns`。

```kotlin
class HttpDnsPrefetcher(
    private val bootstrapClient: OkHttpClient,
    private val endpoint: HttpUrl,
    private val memory: HttpDnsMemoryCache,
    private val disk: HttpDnsDiskSnapshot,
) {
    fun refresh(hostname: String) {
        val request = Request.Builder()
            .url(endpoint.newBuilder().addQueryParameter("host", hostname).build())
            .tag("httpdns-prefetch")
            .build()

        bootstrapClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                // 记录失败，不清空仍在 TTL 内的旧结果。
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val record = parseAndValidate(hostname, it)
                    memory.put(hostname, record)
                    disk.put(hostname, record)
                }
            }
        })
    }
}
```

预取触发点要保守：启动后一小段空闲期、登录后、首页业务域名固定时、网络从不可用恢复到可用时。列表滚动、按钮点击、接口请求同步路径里不要触发大批预取，否则优化动作会和前台请求抢资源。

## TTL、失败 IP 隔离与系统 DNS 兜底

HTTPDNS 缓存不能只按 hostname 存一组 IP。至少要保存 TTL、来源、网络快照和失败状态。

```kotlin
data class HttpDnsRecord(
    val hostname: String,
    val addresses: List<InetAddress>,
    val source: Source,
    val expireAtMs: Long,
    val refreshAfterMs: Long,
    val networkKey: String,
)
```

| 字段 | 用途 | 判断边界 |
|---|---|---|
| `expireAtMs` | 确认结果是否还能返回给 OkHttp | 过期结果不能继续当主路径使用 |
| `refreshAfterMs` | 提前刷新，避免 TTL 到期瞬间集中未命中 | 通常早于 `expireAtMs`，具体比例来自 HTTPDNS 服务契约 |
| `networkKey` | 区分 Wi-Fi、蜂窝、VPN、默认 network 变化 | 网络切换后优先刷新，不盲目沿用旧 IP |
| `source` | 区分 HTTPDNS、磁盘快照、系统 DNS | 线上排查要能看到命中路径 |
| quarantine | 隔离短时间失败的 IP | 单 IP 失败不等于 hostname 不可用 |

失败隔离要按“hostname + IP + 网络”记录。某个 IP connect timeout、TLS 失败或连续 HTTP 5xx 后，可以短时间降低排序或移出候选；同一 hostname 的其他 IP 仍应保留。隔离窗口不能过长，否则 CDN 调度恢复后 App 还在避开可用节点。

系统 DNS 兜底是发布级 HTTPDNS 的安全阀。HTTPDNS 查询失败、缓存为空、缓存全过期、IP 全被隔离时，`lookup()` 返回 `Dns.SYSTEM.lookup(hostname)` 的结果。系统 DNS 也失败时，再把 `UnknownHostException` 交给 OkHttp。

## 网络切换后的刷新策略

移动端的 DNS 结果和当前网络强相关。Wi-Fi 切蜂窝、蜂窝切 Wi-Fi、VPN 打开、Captive Portal 登录完成，都会改变可达 IP、最优 CDN 节点和代理路径。24.9 已经展开系统网络选择；HTTPDNS 侧要做的事更简单：监听默认网络变化，给缓存打网络维度标记，优先刷新高价值域名。

```kotlin
class NetworkAwareDnsRefresher(
    private val connectivityManager: ConnectivityManager,
    private val prefetcher: HttpDnsPrefetcher,
    private val hosts: () -> List<String>,
) : ConnectivityManager.NetworkCallback() {
    override fun onAvailable(network: Network) {
        hosts().forEach(prefetcher::refresh)
    }

    override fun onLost(network: Network) {
        // 不清空缓存。等待新的默认网络出现后刷新。
    }

    override fun onCapabilitiesChanged(
        network: Network,
        capabilities: NetworkCapabilities,
    ) {
        if (capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)) {
            hosts().forEach(prefetcher::refresh)
        }
    }
}
```

切网后不要立刻删除所有旧缓存。新网络刚出现时，系统验证、代理、DNS 和链路质量可能仍在变化；保留旧结果作为短时兜底，再对高价值域名刷新，能减少集中未命中。大下载、上传、视频这类长连接场景还要结合 24.5 的 HTTP/3/QUIC 连接迁移或业务层断点恢复处理。

## 弱网验证与线上指标设计

HTTPDNS 是否有效，不能只看平均 DNS 耗时。弱网下更该看尾延迟、失败分布和兜底命中率。

OkHttp EventListener 能采集 `dnsStart/dnsEnd`、`connectStart/connectEnd`、`secureConnectStart/secureConnectEnd`、`responseHeadersStart` 等事件。文档示例也提醒：连接复用的第二次请求不会再触发 DNS 和 connect 事件；并发请求要用 `EventListener.Factory` 为每个 call 保留独立状态。 [已验证: 官方文档, https://square.github.io/okhttp/features/events/]

建议把 HTTPDNS 埋点拆成三组。

| 指标组 | 字段 | 用途 |
|---|---|---|
| 解析路径 | `dns_source`、`cache_hit`、`record_age_ms`、`ip_count` | 判断命中 HTTPDNS、磁盘、系统 DNS 的比例 |
| 等待段 | `dns_ms`、`connect_ms`、`tls_ms`、`ttfb_ms` | 区分解析慢、建连慢、TLS 慢、服务端慢 |
| 失败分布 | `UnknownHostException`、`connect_timeout`、`ssl_error`、`httpdns_empty`、`fallback_used` | 判断兜底策略是否降低故障影响 |

弱网压测至少覆盖下面几类场景：

- HTTPDNS 服务不可达：`lookup()` 应快速走系统 DNS，`fallback_used=true`。
- HTTPDNS 返回空列表：不把空列表交给 OkHttp，直接兜底。
- 单个 IP connect timeout：隔离该 IP，下一次返回剩余 IP。
- 多 IP + IPv6/IPv4 混合：保留地址族候选，让 OkHttp fast fallback 发挥作用。
- 网络切换：旧缓存不被立刻清空，新网络 validated 后刷新高价值域名。
- HTTPDNS 预取队列堆积：前台业务请求的 Dispatcher 不被预取任务占满。

验收标准可以这样写：HTTPDNS 上线后，`dns_ms` 的 P90/P99 不应恶化；`UnknownHostException` 率不应高于系统 DNS baseline；HTTPDNS 服务故障演练期间，请求成功率由系统 DNS 兜底保持在可接受范围内；切网后 30 秒内的 DNS 失败率和建连失败率不能出现明显尖刺。没有这些数据，HTTPDNS 只能算功能接入，不能算性能优化。

## DoH、HTTPDNS、系统 DNS 的选型对照表

| 方案 | 优点 | 代价 | 适用场景 |
|---|---|---|---|
| 系统 DNS | 和平台网络选择、VPN、私有 DNS、企业代理兼容性最好 | 受本地 DNS 质量影响，调度能力受限 | 默认路径、兜底路径、长尾域名 |
| HTTPDNS | 可按业务域名做调度、容灾和灰度，能绕开部分本地 DNS 问题 | 要维护 TTL、缓存、兜底、服务 SLA 和合规策略 | 核心 API、CDN、跨运营商质量差异明显的域名 |
| DoH | 标准化，OkHttp 有模块可复用，传输加密 | 仍有 bootstrap 问题，部分网络或企业环境可能拦截 | 对隐私和标准化要求高、可接受依赖公开或自建 DoH 服务的场景 |

HTTPDNS 与 DoH 都不能替代系统 DNS 成为唯一出口。移动端会遇到 VPN、企业代理、校园网、Captive Portal、私有域名、内网测试环境；系统 DNS 往往最了解当前网络的约束。更稳的策略是把自定义解析当作加速和容灾层，把系统 DNS 留作兼容层。

## 多 IP fast fallback 与连接池复用边界

OkHttp 5 的 fast fallback 会按 Happy Eyeballs 思路并发尝试多个 TCP 连接，文档写明它会交替 IPv6 / IPv4 地址、相邻尝试间隔 250 ms、保留最先成功的 TCP 连接。 [已验证: 官方文档, https://square.github.io/okhttp/features/connections/]

HTTPDNS 返回结果时不要只给“最优单 IP”。单 IP 看起来减少了尝试次数，却移除了连接层回退空间；这个 IP 在某个运营商、某个小区网络或某段时间失败时，OkHttp 没有候选 route 可换。更稳的返回顺序是：同一 hostname 保留 2-4 个候选，IPv6/IPv4 都有验证数据时混排，失败隔离只移除短时坏 IP。

连接池复用和 DNS 也有边界。OkHttp 找到可复用连接时，不一定触发 DNS；新建连接、连接不健康、连接池没有可用连接、HTTP/2 coalescing 需要更多 route 信息时，才会进入路由规划。线上分析不要把“没有 dnsStart 事件”误判成 DNS 模块失效，它也可能只是连接池命中。



<!-- AIW-源码调研-2026-05-17 -->
## 源码补充：DnsOverHttps 同步化机制（2026-05-17 验证）

> 以下补充于 2026-05-17 每日源码调研，基于 OkHttp 官方源码验证。

### DnsOverHttps 内部 CountDownLatch 同步化

`DnsOverHttps.lookup()` 虽然内部使用 `client.newCall(...).enqueue(callback)` 发起**异步 HTTP 请求**，但通过 `CountDownLatch.await()` 将其同步化，调用线程仍被阻塞：

```kotlin
// okhttp-dnsoverhttps/DnsOverHttps.kt
private fun executeRequests(...): List<InetAddress> {
    val latch = CountDownLatch(networkRequests.size)
    for (call in networkRequests) {
        call.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) { ... latch.countDown() }
            override fun onResponse(call: Call, response: Response) { ... latch.countDown() }
        })
    }
    try {
        latch.await()  // ← 调用线程被阻塞，直到所有 DOH 查询完成
    } catch (e: InterruptedException) {
        failures.add(e)
    }
}
```

**影响**：在弱网下，这会导致连接池调度线程被阻塞数秒，而非快速失败切换系统 DNS。

### 完整调用链（源码堆栈重建）

```
StreamAllocation.findConnection
  → RouteSelector.next()
    → RouteSelector.nextProxy()
      → RouteSelector.resetNextInetSocketAddress()
        → address.dns().lookup(hostname)   // ← 同步阻塞点
```

堆栈来源：GitHub issues #3122、#3919 的 `UnknownHostException` 堆栈，重建了 OkHttp 4.x 的 `Dns$1.lookup()` → `RouteSelector.resetNextInetSocketAddress()` 路径。

### OkHttp 5 AsyncDns 草案状态

GitHub issue #8318（2024-03）讨论了 OkHttp 5 引入 `AsyncDns` 接口的可能性，允许真正的异步 DNS 查询：

```kotlin
interface AsyncDns {
    fun onAddresses(hasMore: Boolean, hostname: String, addresses: List<InetAddress>)
    fun onFailure(hasMore: Boolean, hostname: String, e: IOException)
}
```

但截至目前（OkHttp 5.0.x 正式 release 前），**标准 `Dns` 接口仍为同步阻塞**，AsyncDns 未进入正式版。

### Dns 接口类型（Kotlin SAM）

OkHttp 4.x/5.x 使用 `fun interface Dns`，编译后等价于 Java 抽象类：

```kotlin
fun interface Dns {
    @Throws(UnknownHostException::class)
    fun lookup(hostname: String): List<InetAddress>
}
```

`fun interface` = Kotlin SAM（Single Abstract Method）接口，只能有一个抽象方法，编译后生成 `$DefaultImpls` 静态内部类。实现可以是 lambda：`Dns { hostname -> Dns.SYSTEM.lookup(hostname) }`。

来源：`github.com/square/okhttp/blob/728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab/okhttp/src/commonJvmAndroid/kotlin/okhttp3/Dns.kt`

<!-- AIW-源码调研-2026-05-17 end -->
## 工程检查清单

- `Dns.lookup()` 内是否只读内存/磁盘缓存，不发 HTTP 请求。
- `Dns` 实现里的缓存、隔离表、刷新状态是否并发安全。
- HTTPDNS 查询是否使用独立 bootstrap client，避免复用业务主 client 的自定义 `Dns`。
- HTTPDNS 域名自身是否有系统 DNS、固定 bootstrap IP 或 DoH bootstrap host。
- 缓存是否保存 TTL、刷新时间、来源、网络快照和 IP 列表。
- 单 IP 失败是否短时隔离，而不是清空整个 hostname。
- 缓存为空、过期、全隔离时是否回退到 `Dns.SYSTEM`。
- 网络切换后是否刷新高价值域名，同时保留旧缓存短时兜底。
- 是否通过 EventListener 同时采集 DNS、connect、TLS、TTFB、失败类型。
- 弱网演练是否覆盖 HTTPDNS 服务不可达、返回空、多 IP 失败、网络切换和 Dispatcher 挤占。



<!-- AIW-源码调研-2026-05-25 -->
## 源码补充：ExchangeFinder.findConnection() 与 RealRoutePlanner 同步调用链（2026-05-25 验证）

> 以下补充于 2026-05-25 每日源码调研，基于 square/okhttp commit 19cb19ab4ac31aa789bc94759d13898f64f93ce3 的 ExchangeFinder 源码，以及 OkHttp 5.x source 728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab 的 RealRoutePlanner 源码验证。

### RealRoutePlanner.planConnect() 阻塞注释

OkHttp 5.x `RealRoutePlanner.kt` 的 `planConnect()` 方法注释直接写明：
> "List available IP addresses for the current proxy. **This may block in Dns.lookup().**"

这是 OkHttp 官方代码对 `Dns.lookup()` 同步阻塞特性的最直接确认。

### ExchangeFinder.findConnection() 完整路径（335 行 Kotlin 源码）

```kotlin
// ExchangeFinder.kt 节选（findConnection 方法核心路径）
private fun findConnection(...): RealConnection {
    // 1. 先在池内查找已有连接（无 DNS）
    if (connectionPool.callAcquirePooledConnection(address, call, null, false)) {
        foundPooledConnection = true
        result = call.connection
    } else if (nextRouteToTry != null) {
        selectedRoute = nextRouteToTry
    }

    // 2. 池命中失败 → 创建 RouteSelector 并调用 .next()（触发同步 DNS）
    if (selectedRoute == null && (routeSelection == null || !routeSelection!!.hasNext())) {
        val localRouteSelector = RouteSelector(address, call.client.routeDatabase, call, eventListener)
        this.routeSelector = localRouteSelector
        newRouteSelection = true
        routeSelection = localRouteSelector.next()  // ← 同步阻塞 DNS lookup 在这里
    }

    // 3. 创建 RealConnection 并执行 TCP+TLS handshake（也是阻塞调用）
    result!!.connect(connectTimeout, readTimeout, writeTimeout, pingIntervalMillis, ...)
}
```

关键点：`routeSelector.next()` 是 `RouteSelector.next()`，内部调用 `resetNextInetSocketAddress()` → `address.dns().lookup()`。

### Dns 接口并发安全要求（官方文档原文）

OkHttp Dns 接口文档（square.github.io/5.x）：
> "**Implementations must support concurrent execution.**"

这意味着：即使 `lookup()` 在建连前被同步调用，OkHttp 要求实现必须并发安全——内部缓存、失败隔离表等数据结构必须能承受多线程同时调用。

### Fast Fallback 与 Happy Eyeballs（OkHttp 5.x 新特性）

| 规则 | 说明 |
|------|------|
| 地址族交替 | 优先交替 IPv6/IPv4，IPv6 优先 |
| 尝试间隔 | 新尝试延迟 250ms 后发起 |
| 连接保留 | 保留最先成功 TCP 连接，取消其他 |
| TLS 时机 | 只在 winning TCP 连接上做 TLS handshake |

Fast Fallback 可以缓解 DNS 解析慢导致的建连延迟，但无法消除 `lookup()` 同步阻塞本身。

### 来源

- `github.com/square/okhttp` commit `19cb19ab4ac31aa789bc94759d13898f64f93ce3`
  - `okhttp/src/main/java/okhttp3/internal/connection/ExchangeFinder.kt`（335 行，raw 源码）
- `github.com/square/okhttp` source `728e4d575d8e9a09bbab04ef09bb24ff6b1fa0ab`
  - `okhttp/src/commonJvmAndroid/kotlin/okhttp3/internal/connection/RealRoutePlanner.kt`（注释来源）
- square.github.io/okhttp/features/connections/（Fast Fallback 文档）

<!-- AIW-源码调研-2026-05-25 end -->


## 延伸阅读


### OkHttp Dns.lookup() 执行边界与 HTTPDNS 工程化陷阱
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-14-okhttp-dns-lookup-httpdns-engineering.md
- 类型：DeepResearch 调研结果
- 摘要：OkHttp Dns.lookup() 同步阻塞，RouteSelector 在建连前调用。HTTPDNS 在 lookup() 内实时请求会递归依赖同一 OkHttpClient 形成死锁。Square 推荐 bootstrap client 独立实例模式。OkHttp 5.0+ 支持 Happy Eyeballs。
- 注入时间：2026-05-18
- 价值：源码级分析 OkHttp DNS 调用链与 HTTPDNS 递归依赖陷阱，bootstrap client 最佳实践
