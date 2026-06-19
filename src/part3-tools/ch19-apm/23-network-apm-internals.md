---
status: "finalized"
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
chapter: '19'
confidence: high
drafted_by: gemini
drafted_date: '2026-04-24'
last_task2b_at: "2026-05-31T19:35:00+08:00"
last_task2b_lite_at: "2026-05-31"
last_task6_at: "2026-05-31T20:10:00+08:00"
last_task6_audit: "2026-06-19T21:06:00+08:00"
last_task6_review_log: "logs/review/2026-05-31-20-review.md"
last_task9_at: "2026-05-31T21:20:00+08:00"
last_task9_review_log: "logs/deep-review/2026-05-31-21-deep-review.md"
last_verified: '2026-04-24'
pipeline_stage: "ready-to-publish"
related_chapters:
- '19.0'
- '19.08'
- '19.17'
review_notes: '2026-05-01 task6 re-review (revisiting): pass-light-edit. L1: no banned
  words. L2: excellent structure and rhythm. All 7 anchors + 3 extensions covered.
  task9_result=needs-rework, not eligible for auto-promotion. | ⚡ 2026-05-01 task6
  re-confirm (revisiting→reviewed): content clean, no new L1/L2 issues. task9 issues
  previously fixed in queue. task9 re-review needed for auto-promotion. | 2026-05-05
  task6 review: L1/L2 小修完成（术语换为“分解”，结束动作改成“请求结束”）；无新增 L3/L4 回炉项，等待 Task9 复审。'
reviewed_by: openclaw-task6
reviewed_date: "2026-05-31"
section: '19.23'
sources:
- https://square.github.io/okhttp/features/events/
- https://square.github.io/okhttp/features/interceptors/
- https://developer.android.com/reference/tools/gradle-api/8.6/com/android/build/api/instrumentation/AsmClassVisitorFactory
- https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/UrlRequest.Callback
- https://developer.android.com/develop/connectivity/cronet/reference/org/chromium/net/RequestFinishedInfo
tags:
- apm
- network
- okhttp
- asm
- cronet
task2b_result: "fixed-lite"
task2b_state: "fixed"
task6_result: "pass-light-edit"
task6_reviewed_at: "2026-05-31T20:10:00+08:00"
task6_reviewed_by: openclaw-task6
task6_state: reviewed
task9_result: "pass-tech-review"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-31"
task9_state: "reviewed"
title: 网络 APM 底层捕获原理
task9_review_notes: "2026-05-31 Task9 deep review: 复核 OkHttp EventListener attempt/exchange 建模、responseBodyEnd 应用消费边界、AGP Instrumentation API、Cronet/eBPF/QUIC 边界，无 P0/P1，自动晋升 finalized。"
task6_review_notes: "2026-05-15 task6 revisiting-review: pass-light-edit。L1/L2 clean；既有 Task9 P0 queue pending（activeExchange 状态机），Task6 不裁决，等待 Task2B。 | 2026-05-18 12:26 Task6：revisiting 文稿复审；L1/L2 小修 1 处，承接 Task9 技术边界项 1 个，已在正文标注并并入 queue.json，等待 Task2B/Task9。 | 2026-05-31 20:10 Task6：Task2B fixed-lite 后复审，L1/L2 clean，无新增回炉项，送 Task9 复核。"
---
# 网络 APM 底层捕获原理

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明商业与开源 APM 如何“无侵入”地拿到网络数据，讲清背后的采集方式，而不是只停留在看板展示。
- 🔹 [OkHttp 捕获] 详细分解 `EventListener` 与 `Interceptor` 在网络 APM 中的组合使用；说明为何只用 Interceptor 拿不到 DNS 和 TCP 耗时。
- 🔹 [字节码插桩] 解释如何通过 ASM 或 Transform 无侵入地 Hook `HttpURLConnection` 和三方 SDK 内部封装的网络请求。
- 🔹 [Native 网络捕获] 探讨对于基于 C/C++ 的底层网络库（如 Cronet、微信 Mars），APM 如何通过 PLT Hook 或 eBPF 获取流量与耗时。
- 🔹 [指标分解模型] 将一次网络请求分解为 DNS、TCP 握手、TLS 握手、Request 发送、Server Wait (TTFB)、Response 接收。
- 🔹 [弱网与重试识别] 说明 APM 如何在底层识别因弱网导致的多次建连重试，避免将重试耗时算入单次请求 Server 耗时。
- 🔹 [隐私与安全] 规定端侧在捕获时如何进行 URL Pattern 聚类、Query 参数剥离、Body 截断以及 Header 过滤。

### 扩展（可选深入）

- 🔸 提供一段完整的 `OkHttp EventListener` 埋点核心代码。
- 🔸 增加一段 ASM Hook `openConnection` 的伪代码或指令说明。
- 🔸 解析 HTTP/3 (QUIC) 对现有网络 APM 捕获机制带来的挑战与应对思路。

### 流水线加工要求

- 必须从架构师的视角解释“如何造轮子”，而不仅是“如何用轮子”。
- 所有网络指标分解必须符合真实的网络协议栈阶段。
- 强调插桩与拦截器引入的性能开销及防劣化方案。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->

网络 APM 的难点不在看板，而在采样点。请求从业务代码出发，到 DNS、建连、TLS、请求发送、服务端等待、响应读取，中间跨了应用层、库层、Socket 层，有时还跨了 Java 和 Native。端侧想拿到一条可复盘的网络样本，通常要把三层能力拼起来：请求语义层的拦截、阶段时序层的事件回调、以及库实现不可见时的插桩或 Native Hook。

## 1. “无侵入”拿数据，实际是分层采集

“无侵入”通常指业务方不需要在每个请求点手写埋点，不是系统平白把数据送出来。常见实现分四层：

| 层级 | 入口 | 能拿到什么 | 常见盲区 |
| --- | --- | --- | --- |
| Java 请求层 | `Interceptor`、`EventListener` | URL、方法、状态码、异常、分阶段耗时 | 三方 SDK 内部封装的请求入口可能不可见 |
| 构建期插桩层 | ASM / AGP Instrumentation API | `HttpURLConnection`、封装 SDK 内部调用点、统一 trace id 注入 | 只能看到被插到的类；静态链接或反射路径可能漏掉 |
| Native 库层 | Cronet 指标、PLT Hook | `connect`、`SSL_read`、`SSL_write`、字节数、失败 errno | 静态链接、自定义协议栈、符号不可见时覆盖不全 |
| 系统/内核层 | eBPF、系统网络统计 | 每 UID 流量、重传、RTT、socket 级事件 | 普通应用权限不够，线上 App 很难直接用 |

商业 APM 的常见做法是把这几层串成一个统一样本：上层给请求名、页面、用户会话、业务标签；中层给 DNS/TCP/TLS/TTFB 等阶段耗时；底层补失败码、重试、发送和接收字节数。最终写入一条 request sample，再异步批量上报。

## 2. OkHttp：`EventListener` 负责阶段，`Interceptor` 负责语义

如果应用的主通道是 OkHttp，最稳的做法是同时接 `EventListener` 和 `Interceptor`。

### 2.1 两个接口各自负责什么

- `EventListener`：负责时序观察。OkHttp 官方提供了 `dnsStart/dnsEnd`、`connectStart/connectEnd/connectFailed`、`secureConnectStart/secureConnectEnd`、`requestHeadersStart`、`responseHeadersStart`、`responseBodyEnd` 等事件，适合拆分阶段耗时。
- `Interceptor`：负责请求和响应语义。它适合读取或改写 header、补 trace id、记录业务接口名、状态码、异常类型、请求体大小、脱敏后的 URL。

只靠 `Interceptor` 拿不到 DNS 和 TCP 耗时，原因在于 Interceptor API 没有阶段回调。DNS 查询、Socket 建连、TLS 握手这些阶段由 OkHttp 内部的 `RealCall` / `ExchangeFinder` 驱动，Interceptor 链条只看到最终的请求和响应对象，拿不到 `dnsStart`、`connectStart` 这类事件。网络拦截器虽然比应用拦截器更靠近网络，但它仍然只在请求/响应层面观察。

### 2.2 一段可执行的 `EventListener` 埋点代码

这段代码的用途是把一次 OkHttp 调用拆成 request 级样本和 attempt 级阶段耗时。重点看四点：一是 `EventListener.Factory` 为每个 `Call` 创建独立监听器；二是 `callId` 与请求对象解耦；三是 `connectFailed` 会形成新的 attempt；四是复用连接时 DNS/TCP/TLS 字段可能为空。

```kotlin
class NetworkMetricEventListenerFactory(
    private val sink: NetworkMetricSink,
    private val clock: () -> Long = { System.nanoTime() }
) : EventListener.Factory {
    override fun create(call: Call): EventListener =
        NetworkMetricEventListener(sink, clock)
}

val client = OkHttpClient.Builder()
    .eventListenerFactory(NetworkMetricEventListenerFactory(metricSink))
    .build()

private class NetworkMetricEventListener(
    private val sink: NetworkMetricSink,
    private val clock: () -> Long = { System.nanoTime() }
) : EventListener() {

    // Exchange: 单次 request/response 往返。
    // OkHttp EventListener 文档明确写明"Events and sequences of events
    // may be repeated for retries and follow-ups"。同一个 Call 内，
    // redirect、auth follow-up、缓存条件请求都会让 requestHeaders/responseHeaders
    // 等事件重复触发。如果不拆层，后一次会覆盖前一次的耗时数据。
    private data class Exchange(
        var requestHeadersStartNs: Long? = null,
        var requestHeadersEndNs: Long? = null,
        var requestBodyStartNs: Long? = null,
        var requestBodyEndNs: Long? = null,
        var responseHeadersStartNs: Long? = null,
        var responseHeadersEndNs: Long? = null,
        var responseBodyStartNs: Long? = null,
        var responseBodyEndNs: Long? = null
    )

    private data class Attempt(
        var dnsStartNs: Long? = null,
        var dnsEndNs: Long? = null,
        var connectStartNs: Long? = null,
        var connectEndNs: Long? = null,
        var secureStartNs: Long? = null,
        var secureEndNs: Long? = null,
        var connectionAcquiredNs: Long? = null,
        var connectionReleasedNs: Long? = null,
        var requestFailed: String? = null,
        var responseFailed: String? = null,
        val exchanges: MutableList<Exchange> = mutableListOf(),
        var failure: String? = null
    ) {
        // 当前活跃 exchange：responseBodyEnd 标志 exchange 结束。
        // redirect / follow-up 会触发新一轮 requestHeadersStart，此时上一个
        // exchange 的 responseBodyEnd 已调用（即使 body 为空），responseBodyEndNs
        // 非空，activeExchange() 会正确创建新 exchange。
        // 不检查 responseHeadersEndNs：header 完成后 body 仍属于同一个 exchange。
        fun activeExchange(): Exchange {
            val last = exchanges.lastOrNull()
            if (last != null && last.responseBodyEndNs == null) {
                return last
            }
            return Exchange().also { exchanges += it }
        }
    }

    private val callId = java.util.UUID.randomUUID().toString()
    private val attempts = mutableListOf(Attempt())
    private var callStartNs: Long = 0L

    private fun currentAttempt(): Attempt = attempts.last()

    // 当前 attempt 已结束（有 failure 或已 connectEnd），需要为新的路由尝试创建 attempt
    private fun ensureActiveAttemptForNewRoute() {
        val cur = currentAttempt()
        if (cur.failure != null || cur.connectEndNs != null) {
            attempts += Attempt()
        }
    }

    override fun callStart(call: Call) {
        callStartNs = clock()
    }

    override fun dnsStart(call: Call, domainName: String) {
        ensureActiveAttemptForNewRoute()
        currentAttempt().dnsStartNs = clock()
    }

    override fun dnsEnd(call: Call, domainName: String, inetAddressList: List<InetAddress>) {
        currentAttempt().dnsEndNs = clock()
    }

    override fun connectStart(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy) {
        // 确保 attempt 处于活跃状态：上一轮 connectFailed 或 connectEnd 后应创建新 attempt
        ensureActiveAttemptForNewRoute()
        currentAttempt().connectStartNs = clock()
    }

    override fun secureConnectStart(call: Call) {
        currentAttempt().secureStartNs = clock()
    }

    override fun secureConnectEnd(call: Call, handshake: Handshake?) {
        currentAttempt().secureEndNs = clock()
    }

    override fun connectEnd(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
        protocol: Protocol?
    ) {
        currentAttempt().connectEndNs = clock()
    }

    override fun responseHeadersEnd(call: Call, response: Response) {
        currentAttempt().activeExchange().responseHeadersEndNs = clock()
    }

    override fun connectionAcquired(call: Call, connection: Connection) {
        currentAttempt().connectionAcquiredNs = clock()
    }

    override fun connectionReleased(call: Call, connection: Connection) {
        currentAttempt().connectionReleasedNs = clock()
    }

    override fun requestFailed(call: Call, ioe: IOException) {
        currentAttempt().requestFailed = ioe.javaClass.simpleName
    }

    override fun responseFailed(call: Call, ioe: IOException) {
        currentAttempt().responseFailed = ioe.javaClass.simpleName
    }

    override fun connectFailed(
        call: Call,
        inetSocketAddress: InetSocketAddress,
        proxy: Proxy,
        protocol: Protocol?,
        ioe: IOException
    ) {
        currentAttempt().failure = ioe.javaClass.simpleName
        // 不在这里创建新 attempt，等下一次 connectStart/dnsStart 时再懒创建
        // 如果这是终止前的失败，callFailed 会把当前 attempt（含 failure 信息）记录下来
        // 避免产生一个空 attempt 导致 attempt_count 多算、retry_overhead_ms 归因被污染
    }

    override fun requestHeadersStart(call: Call) {
        currentAttempt().activeExchange().requestHeadersStartNs = clock()
    }

    // OkHttp 3.11+ 提供 requestHeadersEnd 回调，用于精确分隔 header 写入与 body 写入
    override fun requestHeadersEnd(call: Call, request: Request) {
        currentAttempt().activeExchange().requestHeadersEndNs = clock()
    }

    // requestBodyStart 标记 body 写入开始（有请求体时才有）
    override fun requestBodyStart(call: Call) {
        currentAttempt().activeExchange().requestBodyStartNs = clock()
    }

    override fun requestBodyEnd(call: Call, byteCount: Long) {
        currentAttempt().activeExchange().requestBodyEndNs = clock()
    }

    override fun responseHeadersStart(call: Call) {
        currentAttempt().activeExchange().responseHeadersStartNs = clock()
    }

    override fun responseBodyStart(call: Call) {
        currentAttempt().activeExchange().responseBodyStartNs = clock()
    }

    override fun responseBodyEnd(call: Call, byteCount: Long) {
        currentAttempt().activeExchange().responseBodyEndNs = clock()
    }

    override fun callEnd(call: Call) {
        sink.record(call.request(), callId, callStartNs, clock(), attempts)
    }

    override fun callFailed(call: Call, ioe: IOException) {
        currentAttempt().failure = ioe.javaClass.simpleName
        // 过滤没有任何阶段时间的空 attempt，避免归因污染
        val validAttempts = attempts.filter { att ->
            att.dnsStartNs != null || att.connectStartNs != null ||
            att.exchanges.any { it.requestHeadersStartNs != null } || att.failure != null
        }
        sink.record(call.request(), callId, callStartNs, clock(), validAttempts)
    }
}
```

这段代码只负责采时间点，不在回调里做 JSON 序列化、数据库写入或网络上报。回调线程可能落在发起请求的业务线程或 OkHttp 的内部线程，采样逻辑越重，对请求路径的干扰越大。

注册方式必须用 `eventListenerFactory(...)`。`eventListener(...)` 会把同一个 listener 实例复用到所有并发 `Call`，只适合没有 per-call mutable state 的监听器；上面的实现把 `callId`、`attempts`、`callStartNs` 放在实例字段里，必须让每个 `Call` 独占一个实例。

### 2.3 `Interceptor` 该做哪些事

`Interceptor` 适合补这几类信息：

- 业务路由名：例如把 `/feed/list` 归一成 `feed_list`
- 统一请求 id：放在 request header、tag 或 thread local 里，跟 `EventListener` 的 callId 关联
- 响应语义：HTTP 状态码、业务错误码、重定向链条、缓存命中
- 脱敏：Query 参数剥离、header 白名单、body 截断

把两个接口混用时，稳妥的结构是：`Interceptor` 生成 request sample 外壳，`EventListener` 填充 attempt 级细项，请求结束时再合并。

## 3. `HttpURLConnection` 与三方 SDK：靠构建期插桩补入口

很多旧工程还在用 `HttpURLConnection`，还有一批三方 SDK 把请求封在内部，业务代码拿不到 OkHttp Client。此时 APM 常用构建期插桩补入口。

Android Gradle Plugin 新版推荐用 Instrumentation API，入口是 `AsmClassVisitorFactory`。它比旧的 Transform API 更适合做增量构建和按 Variant 生效的插桩。典型思路是只改少数稳定调用点，把真实采样逻辑放到运行时桥接类。

这段伪代码演示的用途是把 `URL.openConnection()` 替换成自定义桥接方法。重点看 owner、name、desc 三元组匹配，避免误伤同名方法。

```kotlin
// 伪代码：展示 ASM 改写调用点的思路。
class OpenConnectionMethodVisitor(
    api: Int,
    mv: MethodVisitor
) : MethodVisitor(api, mv) {

    override fun visitMethodInsn(
        opcode: Int,
        owner: String,
        name: String,
        descriptor: String,
        isInterface: Boolean
    ) {
        val hit = opcode == Opcodes.INVOKEVIRTUAL &&
            owner == "java/net/URL" &&
            name == "openConnection" &&
            descriptor == "()Ljava/net/URLConnection;"

        if (hit) {
            super.visitMethodInsn(
                Opcodes.INVOKESTATIC,
                "com/example/apm/ApmUrlHook",
                "openConnection",
                "(Ljava/net/URL;)Ljava/net/URLConnection;",
                false
            )
            return
        }

        super.visitMethodInsn(opcode, owner, name, descriptor, isInterface)
    }
}
```

运行时桥接类通常会做三件事：

1. 建一个 request id，并把它绑到 `URLConnection` 包装对象或 side table。
2. 在 `connect()`、`getInputStream()`、`getOutputStream()` 等关键点记录阶段时间。
3. 将异常、响应码、字节数写入统一 sink。

这类插桩要控制范围。只改项目代码通常已经足够；把依赖库也纳入插桩，构建耗时和兼容风险都会上升。作用域按目标分开看：

- `InstrumentationScope.PROJECT` 只处理当前工程模块里的 class，适合一方代码里直接出现的 `URL.openConnection()` 调用。
- `InstrumentationScope.ALL` 会把依赖 class 纳入处理范围，才有机会覆盖 AAR/JAR 中三方 SDK 内部的 `HttpURLConnection` 调用。使用 `ALL` 时要通过 `isInstrumentable` 包名白名单、依赖排除和构建缓存控制开销。

调用点清单也要补齐：`URL.openConnection()`、`URL.openConnection(Proxy)` 和 `URL.openStream()` 都可能出现在旧代码或 SDK 包装层里。替换这些 Java 调用点仍然看不到 Native 网络库内部请求，attempt 级重试还要靠库回调或底层 Hook。

## 4. Native 网络捕获：Cronet 先走官方指标，抓不到再考虑 Hook

### 4.1 Cronet 与自带指标接口

基于 Chromium 栈的 Cronet 已经提供 `UrlRequest.Callback` 和 `RequestFinishedInfo`。这类库优先走官方指标，因为它知道连接是否复用、是否走 QUIC、重定向发生了几次，也能给出更接近真实传输阶段的时间点。

如果工程里直接接了 Cronet，推荐的做法是：

- `UrlRequest.Callback` 负责拿请求生命周期事件
- `RequestFinishedInfo` 负责拿 request 结束后的阶段指标和失败信息
- 统一换算到和 OkHttp 一致的数据模型里，例如 `dns_ms`、`connect_ms`、`ssl_ms`、`ttfb_ms`

### 4.2 PLT Hook 能解决什么

很多商业 SDK 在 Android 端会准备一层 Native Hook 兜底，原因是请求未必走公开 Java API。PLT Hook 的常见目标有：

- `getaddrinfo`：主机名解析
- `connect`：建连
- `SSL_write` / `SSL_read`：HTTPS 场景下观察应用明文字节长度、TLS 错误和读写返回值
- `send` / `recv`：Socket 层传输字节、`errno`、断连和重传辅助归因；HTTPS 场景通常看到 TLS record / 密文字节

明文 HTTP 是例外：没有 TLS 层时，`send` / `recv` 看到的就是应用明文。HTTPS 路径下，`SSL_write` 的输入和 `SSL_read` 的输出更接近业务明文长度；`send` / `recv` 位于 TLS 下方，更适合看 Socket 层错误和传输规模。

PLT Hook 适合拦截动态链接符号，能覆盖部分 Cronet、Mars、libssl、libc 调用路径。它的局限也需要清楚：

- 静态链接的网络栈看不到
- 直接 syscall 或内部函数跳转看不到
- 同进程多个 SDK 都在 Hook 同一符号时，安装顺序和重入保护很容易出问题

因此，Native Hook 更适合做兜底样本，不适合作为唯一真相来源。只要库本身有官方回调，就优先走回调。

### 4.3 eBPF 的真实边界

eBPF 在 Android 系统侧已经广泛用于网络统计，但普通应用通常没有加载 eBPF 程序所需权限。它更像 ROM、设备侧、企业管控环境、测试机或 root 环境的工具，而不是面向所有线上用户的通用 App 方案。

对 APM 来说，eBPF 在这些场景里能提供常规 Java 回调拿不到的数据：

- 可以按 UID 看流量与 socket 事件
- 能观察重传、RTT、连接失败等更贴近内核的数据
- 对非 Java、非公开 SDK 的请求更友好

但把 eBPF 写成端侧 App 的默认方案，会直接碰到权限墙。量产 App 的常规路径仍然是 Java 回调、构建期插桩、Native Hook 的组合。

## 5. 指标模型：一条请求要拆成 request 和 attempt 两层

只做一层总耗时，排障很快会卡住。一个可执行的模型通常包含 request 级样本和 attempt 级样本。

### 5.1 request 级样本

| 字段 | 含义 |
| --- | --- |
| `request_id` | 单次业务请求唯一标识 |
| `route` | 已归一化的接口名或 URL pattern |
| `method` | `GET` / `POST` 等 |
| `status_code` | HTTP 状态码 |
| `error_type` | `IOException`、超时、取消等 |
| `total_cost_ms` | 从请求发起到回调结束的总耗时 |
| `attempt_count` | 建连或路由重试次数 |
| `network_type` | Wi‑Fi / Cellular / VPN / Offline |

### 5.2 attempt 与 exchange 级阶段耗时

一个 attempt 对应一次建连尝试（DNS/TCP/TLS）。一个 attempt 内可以包含多个 exchange（redirect、auth follow-up 会在同一连接上触发新一轮 request/response）。拆成两层后，弱网归因才能区分"建连阶段失败"和"请求阶段因 follow-up 被重复触发"。

| 阶段 | 起点 | 终点 | 说明 |
| --- | --- | --- | --- |
| DNS | `dnsStart` | `dnsEnd` | 连接复用时通常为空 |
| TCP 握手 | `connectStart` | `connectEnd` | 仅新建连接出现 |
| TLS 握手 | `secureConnectStart` | `secureConnectEnd` | 仅 HTTPS 且新握手时出现 |
| Request Headers | `requestHeadersStart` | `requestHeadersEnd` | header 写入耗时，通常很短 |
| Request Body | `requestHeadersEnd` / `requestBodyStart` | `requestBodyEnd` | 无请求体时此段为空 |
| Server Wait / TTFB | `requestHeadersEnd`（无 body）或 `requestBodyEnd`（有 body） | `responseHeadersStart` | 只看同一次 exchange；attempt 内如有 follow-up，每个 exchange 独立计算 TTFB |
| Response Headers End | `responseHeadersStart` | `responseHeadersEnd` | header 接收完成时刻，TTFB 可精确到此处 |
| Response Body 消费 | `responseBodyStart` | `responseBodyEnd` | OkHttp 在应用读取到 EOF 或关闭 `ResponseBody` 时触发结束；流式响应、延迟读取、边读边解析或提前 close 会混入应用消费节奏，不能直接等同 socket 下载耗时 |

OkHttp 的 `responseBodyEnd` 代表应用把 `ResponseBody` 消费完或关闭完成。APM 可以用 `responseBodyStart → responseBodyEnd` 记录 body 消费窗口，但线上归因要把它标成“应用读取/关闭耗时”，不能把延迟读取造成的变长直接算作网络下载变慢。

几个实现细节要统一：

- 没有请求体的场景，TTFB 从 `requestHeadersEnd` 算到 `responseHeadersStart`（不包括客户端写 header 的时间）。有请求体时，TTFB 从 `requestBodyEnd` 算到 `responseHeadersStart`。
- 连接复用时，DNS/TCP/TLS 应该记为 `null` 或 `0`，不能拿上一次连接的耗时回填。
- HTTP/2 多路复用时，请求共享一条连接，阶段耗时和 socket 级事件不再一一对应。

### 5.3 EventListener 的空阶段字段怎么解释

看板里大量请求的 DNS/TCP/TLS 字段为空，不一定是采集失败。OkHttp 的事件口径要和连接复用一起看：

| 观察现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 没有 `dnsStart` / `connectStart` | 连接池复用已有连接 | 阶段字段记为 `null`，不要回填历史连接耗时 |
| 多个请求共用同一条连接 | HTTP/2 multiplexing | request 级样本保留独立 TTFB，socket 级指标只做连接维度参考 |
| 看到 `connectionAcquired` 后直接进入请求发送 | 后续请求复用连接 | 在样本中标记 `connection_reused = true`，避免误报“缺少 DNS/TCP 数据” |

## 6. 弱网与重试：一定要把“总耗时”和“服务端等待”分开

弱网环境里最容易报错的一件事，是把多次失败建连、路由切换、代理切换、连接池失效，全都算进一次请求的服务端耗时。这样出来的 TTFB 没有诊断价值。

稳妥做法是把重试拆成 attempt：

- 一次 `Call` 可以对应多个 attempt
- 每个 attempt 都有独立的 DNS/TCP/TLS/TTFB
- request 级样本保留 `attempt_count` 和 `retry_reason`

识别重试可用这些信号：

- OkHttp 出现多次 `connectStart` / `connectFailed`（新 attempt）
- 同一 attempt 内出现多次 `requestHeadersStart`（新 exchange，通常是 redirect 或 follow-up）
- 同一 request id 下 host、IP、proxy 发生切换
- `RouteException`、超时、连接重置后又继续发起请求
- Cronet 或自研栈暴露了内部重试原因码

归因时要遵守一个简单规则：

- `server_wait_ms` 只来自最终成功或最终失败的那个 attempt
- `retry_overhead_ms` 单独累计前面失败 attempt 的耗时
- 看板上同时展示 `total_cost_ms` 和 `server_wait_ms`

这样做之后，排障就能区分三类现场：

- `server_wait_ms` 高：更像服务端慢或上游依赖慢
- `retry_overhead_ms` 高：更像弱网、DNS 波动、建连失败或 TLS 抖动
- `response_receive_ms` 高：更像大包下载、带宽不足或下行丢包

## 7. 隐私与安全：端侧采样默认做裁剪

网络 APM 很容易踩隐私线，因为 URL、Query、Header、Body 都可能带账号、token、手机号、定位、订单号。端侧策略必须在采样入口就生效，不能等服务端再兜底。

推荐的默认规则如下：

### 7.1 URL Pattern 聚类

- 保留 path 结构，剥离动态 id
- `/user/12345/order/888` 归一成 `/user/:id/order/:id`
- Query 参数默认不采原值，只保留 key 列表或白名单 key

### 7.2 Header 过滤

- 默认只留允许清单，例如 `content-type`、`content-length`、业务 trace id
- `authorization`、`cookie`、`set-cookie`、`x-device-id`、`x-user-id` 默认直接移除

### 7.3 Body 处理

- 文本 body 只保留前 N 字节摘要
- 二进制 body 只保留大小和 mime type
- 文件上传不采文件名原文，改成类型与尺寸区间

### 7.4 用户标识

- 端上只记录内部 user key 或 hash
- 试验组、地区、登录态等字段用低基数枚举值
- 不把手机号、邮箱、身份证等直接写进样本

### 7.5 删除与合规

- request sample 与 user session 分离存储
- 保留按 user key 执行删除请求的映射索引
- 跨区部署时，把地区和数据驻留策略写进上报网关，而不是散落在客户端判断里

## 8. 开销控制：APM 自己不能变成网络问题来源

网络埋点最常见的副作用有三类：对象分配过多、主线程串行化、以及日志体积失控。

可执行的防劣化措施如下：

- 监听回调只写内存结构，不做同步 I/O
- 采用对象池或轻量 DTO，避免每个阶段都分配大对象
- 大字段采样率单独控制，例如 body 摘要只抽样 1%-5%
- 上报批量化，网络空闲或下次启动再传
- 对失败风暴加熔断，防止故障期反向放大流量
- 一方代码优先用 `InstrumentationScope.PROJECT`；要审计三方 SDK 内部请求时再用 `InstrumentationScope.ALL`，并配合包名白名单和依赖排除

## 9. HTTP/3 / QUIC 带来的新口径

HTTP/3 之后，很多团队会继续沿用 DNS/TCP/TLS/TTFB 这套字段名，但底层意义已经变了：

- QUIC 没有 TCP 三次握手
- 握手与加密协商合在 QUIC 层完成
- 连接迁移和 0-RTT 让“建连耗时”不再等于一次固定的 TCP 建链

因此，面向 HTTP/3 的 APM 更适合这样处理：

- 保留统一字段名，便于跨协议看板聚合
- 在样本里加 `transport = tcp | quic`
- `connect_ms` 对 QUIC 解释为 transport handshake，不再写成 TCP 握手
- 对连接迁移、路径切换、重传等细节，优先使用 Cronet 或底层库暴露的附加指标

如果没有协议类型字段，同一张看板里把 HTTP/2 和 HTTP/3 直接横比，很容易误判阶段耗时。

## 10. 一套能上线的网络 APM 组装方式

把前面的能力压成工程实现，通常会得到下面这条路径：

1. Java 主通道走 `EventListener + Interceptor`
2. `HttpURLConnection` 与旧 SDK 走 ASM 插桩补入口
3. Cronet 先接官方 `RequestFinishedInfo`，Native 黑盒库再补 PLT Hook
4. request sample 与 attempt sample 分层建模
5. 采样入口默认做隐私裁剪
6. 回调线程只记轻量数据，批量异步上报

这套方案的优点是可扩展。以后接入 WebView、gRPC、QUIC、自研 RPC，不需要推翻已有模型，只要把阶段事件映射到同一份 schema。

## 11. 参考资料与延伸阅读

- OkHttp Events：官方事件生命周期文档，适合核对 `dnsStart`、`connectStart`、`responseBodyEnd` 等回调顺序
- OkHttp Interceptors：官方拦截器文档，适合区分应用拦截器与网络拦截器的职责边界
- AGP `AsmClassVisitorFactory`：构建期字节码插桩入口，适合替代旧 Transform 方案
- Cronet `UrlRequest.Callback` / `RequestFinishedInfo`：适合补齐 QUIC、连接复用和 request 结束后的原生指标

## 12. 锚点覆盖核对

- [已覆盖] 定位：说明“无侵入”本质是分层采集
- [已覆盖] OkHttp 捕获：拆分 `EventListener` 与 `Interceptor` 的职责，解释 DNS/TCP 盲区
- [已覆盖] 字节码插桩：给出 ASM Hook `openConnection` 的伪代码与工程边界
- [已覆盖] Native 网络捕获：说明 Cronet 指标、PLT Hook、eBPF 权限边界
- [已覆盖] 指标分解模型：给出 request / attempt 双层模型与阶段表
- [已覆盖] 弱网与重试识别：拆分 `retry_overhead_ms` 与 `server_wait_ms`
- [已覆盖] 隐私与安全：补齐 URL、Query、Header、Body、删除请求策略
- [扩展已覆盖] `OkHttp EventListener` 核心代码
- [扩展已覆盖] ASM Hook `openConnection` 伪代码
- [扩展已覆盖] HTTP/3 / QUIC 口径变化
