---
title: "ArgusAPM"
chapter: "19"
section: "19.08"
status: finalized
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "历史 APM 架构参考（公开 sample：compileSdk 27 / targetSdk 27 / Java 7）；现代 Android 版本需单独验证"
last_verified: "2026-04-27"
last_verified_against: "Qihoo360/ArgusAPM README + argus-apm-aop + argus-apm-gradle + argus-apm-gradle-asm"
confidence: medium
tags: [apm, aop, gradle-plugin, monitoring, legacy]
related_chapters: ["19.0"]
sources:
  - type: blog
    path: "https://github.com/Qihoo360/ArgusAPM"
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_reviewed_date: "2026-05-05"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-05"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-04"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-04T08:42:32+08:00"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-05-04T07:45:27.214044+08:00"
review_notes: "2026-05-03 task9 deep-review: needs-rework。P0 1；源码路径需回炉修正，已写入 queue.json。；2026-05-04 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0，Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task6_at: "2026-05-05T22:07:00+08:00"
last_task6_audit: "2026-06-25T18:05:00+08:00"
last_task9_audit: "2026-06-17"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-25
---
# ArgusAPM

<!-- outline-start -->

## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 ArgusAPM 是早期开源一体化 APM 方案，重点价值在架构学习和存量项目评估，新项目要谨慎接入。
- 🔹 [架构] 拆 Gradle Plugin、AOP / ASM 织入、采集模块、缓存、上报、后端依赖；画出模块关系。
- 🔹 [能力范围] 按启动、页面、网络、卡顿、内存、崩溃等方向列数据来源和报告产物。
- 🔹 [兼容风险] 明确 AGP、Kotlin、R8、Android 版本、仓库活跃度带来的维护成本。
- 🔹 [AOP 适用性] 说明函数耗时、页面生命周期、点击、网络拦截适合织入；Binder、native、系统调度不适合靠 AOP 判断。
- 🔹 [多进程] 设计主进程、常驻业务进程、短命进程、WebView / renderer 的采集策略和去重规则。
- 🔹 [网络监控] 用现代网络阶段拆分 DNS、connect、TLS、request、server wait、response、retry、queue wait。
- 🔹 [迁移建议] 给存量项目保留、替换、封装上报协议、逐步停用模块的方案。
- 🔹 [学习价值] 提炼早期 APM 的工程设计：插件化采集、统一事件模型、端侧缓存、服务端分析。
- 🔹 [边界] 明确不要把 ArgusAPM 作为最新最佳实践，需要和 Matrix、Firebase、Sentry、官方 SDK 对照。

### 扩展（可选深入）

- 🔸 增加代码阅读索引：从 Gradle 插件入口、采集模块初始化、网络 interceptor、上报接口开始。
- 🔸 补一个迁移前评估表，覆盖功能替代、数据兼容、开关回滚、历史看板保留。
- 🔸 对 Qihoo360/ArgusAPM 仓库活跃度、依赖版本和已知 issue 做核对。
- 🔸 增加与 Matrix、Measure、Firebase、Sentry 的差异表。
- 🔸 补一个“早期 APM 方案为什么会遇到现代 AGP / Android 限制”的解释段。

### 流水线加工要求

- 评价 ArgusAPM 时必须把历史价值和当前可维护性分开写。
- 涉及 AOP 织入的内容必须说明能观测什么、观测不到什么。
- 迁移建议要给顺序和验收方式，不能只写“替换为新方案”。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## ArgusAPM 是早期开源的一体化方案

ArgusAPM 是 360 开源的 Android 性能监控平台，仓库 README 把它定义为移动端可视化性能监控平台。它覆盖交互分析、网络、内存、进程、文件、卡顿、ANR 等指标，并提供 Gradle Plugin 做接入和 AOP 织入。

截至 2026-04-24，仓库 README 仍保留一条公告：由于公司业务调整及成本原因，ArgusAPM 停止支持服务端免费新增接入，已接入产品不受影响。再往下看公开 sample，基线也停在较早期：`compileSdkVersion 27`、`targetSdkVersion 27`、`JavaVersion.VERSION_1_7`，示例里依赖的 OkHttp 还是 `3.10.0`。这个状态决定了它更适合作为架构参考或存量项目维护对象，不适合作为新项目默认选型。

## 架构分成采集模块和 Gradle Plugin

ArgusAPM 的整体结构可以看成两部分：

- **性能采集模块**：APM 采集能力、AOP 织入能力、OkHttp 网络采集等，最终以 aar 形式接入。
- **Gradle Plugin**：管理依赖并在编译期织入部分性能采集代码。

源码阅读时要把两条织入路径拆开：

| 路径 | 代表入口 | 适合的数据 | 代价 |
|---|---|---|---|
| AspectJ | `argus-apm/argus-apm-aop/src/main/java/com/argusapm/android/aop/TraceActivity.java`、`TraceNetTrafficMonitor.java`、`argus-apm-gradle/src/main/kotlin/com/argusapm/gradle/AspectJTransform.kt` | Activity 生命周期、网络流量切面等调用边界清楚、频率相对低的事件 | 接入简单，但编译慢、对 AspectJ 工具链依赖重 |
| ASM | `argus-apm-gradle-asm/…/asm/ASMWeaver.kt`、`bytecode/func/FuncClassAdapter.kt`、`bytecode/okhttp3/OkHttp3ClassAdapter.kt`、`bytecode/webview/WebClassAdapter.kt` | 方法耗时、OkHttp3、WebView 等更高频或需要直接改字节码的场景 | 控制更细，但强依赖类名、方法签名和旧 Transform 流程 |

读 `@Aspect` 入口时看 `argus-apm-aop` 和 `argus-apm-gradle`，不要只在 `argus-apm-main` 里找采集任务。

早期 Android APM 常走这套组合：客户端 SDK 负责采集，Gradle 插件负责自动插入埋点或包装调用，服务端负责展示和分析。

## 支持的监控方向

README 中列出的监控模块覆盖面较广。把它们当架构样本看时，需要把“数据从哪来”和“产出什么”写清楚：

| 方向 | 公开实现入口 / 数据来源 | 报告产物 |
|---|---|---|
| 交互分析 | Activity 生命周期回调或 AOP 织入生命周期方法 | 页面打开耗时、阶段耗时事件 |
| 网络请求分析 | `argus-apm-okhttp` 这类网络采集模块，接在 OkHttp 调用链上 | 请求样本、错误码、耗时、流量 |
| 内存分析 | 进程内存快照、阈值采样、GC / OOM 现场 | 周期性内存样本、异常快照 |
| 进程监控 | 多进程启动、存活和退出事件 | 进程启动耗时、异常存活、退出记录 |
| 文件监控 | 私有目录扫描、文件大小变化统计 | 文件增长样本、目录占用趋势 |
| 卡顿分析 | 主线程 Looper 边界 + 抓栈样本 | block 样本、堆栈签名、页面上下文 |
| ANR 分析 | ANR 现场抓取、主线程堆栈和进程状态快照 | ANR 现场样本、线程栈、版本聚类 |

这些方向至今仍是移动 APM 的主干。变化主要发生在实现细节上：Android 版本提高、权限控制收紧、AGP 插件 API 变化、隐私审查变严，都会影响旧方案直接复用。

## 新项目使用要谨慎

ArgusAPM 的主要风险来自维护状态和平台依赖。新项目直接采用会遇到几类风险：

- 服务端新增接入状态不确定，平台能力无法直接依赖。
- Gradle 插件和 AOP 织入可能不适配现代 AGP。
- 旧监控模块对 Android 12+、14+、16KB page size、隐私策略的适配需要重新验证。
- 文档和社区活跃度不足，遇到兼容问题时更多要靠自修。

公开 sample 的工具链基线直接标出了迁移顺序：

| 公开 sample 基线 | 对现代项目的风险 | 建议替换顺序 |
|---|---|---|
| `compileSdkVersion 27` / `targetSdkVersion 27` | 版本边界停在早期 Android 8.x 工具链 | 1：先收敛 Gradle 插件、字节码织入和构建脚本 |
| `JavaVersion.VERSION_1_7` | 新版插件链、字节码工具和依赖兼容性差 | 1：和构建链一起升级 |
| `okhttp:3.10.0` | TLS、API、网络埋点边界都偏旧 | 2：再替换网络采集模块 |
| 历史服务端字段口径 | 迁移后看板和告警容易断档 | 3：再处理字段兼容和历史数据映射 |

如果已有项目还在用，建议先把采集模块、服务端依赖和构建插件分开评估。能保留的保留，无法适配的逐步替换成 AndroidX、Matrix、KOOM、Sentry、Firebase 或自研模块。

## 作为参考，它有学习价值

ArgusAPM 展示了一个完整移动 APM 早期形态：客户端模块化采集、编译期织入、网络库适配、多进程处理、服务端看板。这些设计问题今天仍然存在，只是工具和系统环境变了。

读这类老项目时，不要只看“现在能不能接”。更有用的是看它怎么划分采集模块、怎么处理多进程、怎么把网络和页面关联、怎么让 Debug 模式和线上采集共存。这些经验可以迁移到新的 APM 体系里。

## 早期一体化 APM 的典型形态

ArgusAPM 展示了早期 Android APM 的一条完整路线：

```mermaid
flowchart LR
    A["Gradle Plugin\n依赖管理 + AOP 织入"] --> B["客户端采集模块\nUI / 网络 / 内存 / 文件 / 卡顿 / ANR"]
    B --> C["本地聚合\n进程 / 页面 / 阈值 / 采样"]
    C --> D["服务端接收\n存储 / 聚合 / 查询"]
    D --> E["可视化平台\n版本 / 机型 / 页面 / 告警"]
```

这套结构在今天仍然成立，只是每一层的实现要更新。Gradle Transform 要迁到现代 AGP API，进程和隐私限制要重审，服务端新增接入也不能再依赖原项目公告里已经停止的免费服务。

## AOP 织入适合哪些数据

ArgusAPM 这类方案使用编译期织入，最适合处理有明确调用边界的数据。文中的 AOP 指 AspectJ 路径，主要覆盖 `TraceActivity`、`TraceNetTrafficMonitor` 这类切面；ASM 路径的匹配范围比字面含义窄——`FuncClassAdapter` 仅在 `TypeUtil.isRunMethod()` 或 `TypeUtil.isOnReceiveMethod()` 成立时才插入 `FuncMethodAdapter`，也就是只织入 `Runnable.run()` 和 `BroadcastReceiver.onReceive()` 的入口/出口计时代码；`OkHttp3ClassAdapter` 只匹配 `OkHttpClient.Builder` 构建路径；`WebClassAdapter` 只匹配 `WebViewClient.onPageFinished()` 等固定入口。不要把 ASM 路径理解成泛化的「任意方法耗时」采集。

- Activity 生命周期耗时。
- OkHttp 请求开始、结束、失败。
- 页面打开和关闭。
- 业务埋点的自动包装。
- 主线程风险 API 的静态扫描或插入。

织入前后的等价逻辑，可以用 Activity 生命周期耗时来理解：

```kotlin
// 业务代码
override fun onResume() {
    super.onResume()
    renderAboveTheFold()
}
```

```kotlin
// 字节码织入后的等价逻辑示意，省略 ArgusAPM 内部上报实现
override fun onResume() {
    val startNs = SystemClock.elapsedRealtimeNanos()
    try {
        super.onResume()
        renderAboveTheFold()
    } finally {
        val costMs = (SystemClock.elapsedRealtimeNanos() - startNs) / 1_000_000
        // 将 costMs、页面名、进程名写入采集模块
    }
}
```

不适合用 AOP 解决所有问题。系统调度、RenderThread、GPU、native heap、Binder 对端都不在 Java 方法入口出口里。AOP 能补业务上下文，不能替代系统 trace。

## 多进程采集要单独设计

README 提到 ArgusAPM 支持多进程采集。多进程 APM 的难点在三个地方：

- 每个进程是否都要初始化 SDK。
- 同一个用户会话如何跨进程关联。
- 子进程上报失败时是否会丢关键样本。

现代项目里常见进程包括主进程、推送进程、WebView renderer、播放器进程、插件进程、短命工具进程。采集策略应该分层：

| 进程类型 | 建议 |
|---|---|
| 主进程 | 完整采集页面、启动、卡顿、网络、内存 |
| 常驻业务进程 | 采集稳定性、CPU、内存和关键业务事件 |
| 短命进程 | 只采 Crash / ANR / exit，避免重模块初始化 |
| WebView / renderer | 依赖系统和 WebView 侧指标，谨慎注入 |

去重规则也要提前设计。常见做法是每个样本都带 `session_id`、`trace_id`、`process_name`、`pid` 和单调递增的 `msg_id`：

- 主进程发起的用户操作生成 `trace_id`，子进程沿用它。
- 端侧落盘以 `process_name + msg_id` 去重，避免重试上传时重复写入。
- 服务端按 `session_id + trace_id + stage` 聚合同一条操作链，把主进程页面事件和子进程 Crash / ANR 关联起来。

多进程一刀切初始化，会增加启动成本，也会制造重复上报。

## 网络监控的现代适配

ArgusAPM 里有 `argus-apm-okhttp` 这类网络采集模块。现代网络监控除了总耗时，还要区分：

- DNS、connect、TLS、request body、server wait、response body。
- HTTP code、业务 code、异常类型、重试次数。
- 请求队列等待时间。
- 缓存命中和离线缓存。
- URL pattern 脱敏。

只靠 `Interceptor` 拿不到 DNS / connect / TLS 这些阶段，阶段拆分要靠 `EventListener`；`Interceptor` 更适合补请求 ID、业务 code 和页面上下文。

这段 `EventListener` 示例属于迁移后的写法。OkHttp 的 `EventListener` 在 3.9 进入预览，3.11 才成为稳定 API；ArgusAPM sample 仍是 `okhttp:3.10.0`，存量工程不要直接复制这段阶段拆分。迁移顺序应先升级网络采集模块，再把旧 Interceptor / 流量包装改成 `EventListener + Interceptor` 分工。

```kotlin
class StageEventListener : EventListener() {
    private var dnsStartNs = 0L
    private var connectStartNs = 0L

    override fun dnsStart(call: Call, domainName: String) {
        dnsStartNs = System.nanoTime()
    }

    override fun dnsEnd(call: Call, domainName: String, inetAddressList: List<InetAddress>) {
        val dnsMs = (System.nanoTime() - dnsStartNs) / 1_000_000
        // 记录 DNS 耗时
    }

    override fun connectStart(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy) {
        connectStartNs = System.nanoTime()
    }

    override fun connectEnd(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy, protocol: Protocol?) {
        val connectMs = (System.nanoTime() - connectStartNs) / 1_000_000
        // 记录 connect 耗时
    }
}
```

```kotlin
class RequestContextInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val requestId = UUID.randomUUID().toString()
        val request = chain.request().newBuilder()
            .header("X-Trace-Id", requestId)
            .build()
        val response = chain.proceed(request)
        // 这里补 route、业务 code、response.code、requestId
        return response
    }
}
```

如果平台只记录“接口耗时 1200ms”，定位价值有限。书稿级 APM 应该把网络请求拆成阶段指标，并和页面、用户操作、服务端 trace id 关联。

## 存量项目迁移建议

已有 ArgusAPM 存量接入时，建议按模块拆迁，不要一次推倒：

1. 保留服务端能用的历史数据，避免趋势断档。
2. 先替换构建链风险最高的 Gradle / AOP 插件。
3. 再处理网络模块，把旧 OkHttp 依赖和阶段统计口径换成现代实现。
4. 卡顿和帧指标迁到 JankStats / FrameMetrics 或 Matrix。
5. Crash / ANR 迁到 Bugly、Sentry、APMPlus 或自建平台。
6. 页面、版本、机型维度保持字段兼容，方便前后对比。

旧 APM 最大的价值是历史口径。迁移时如果字段全变，平台会失去版本对比能力；如果字段不变、采集链先稳住，再逐个替换底层实现，迁移风险会小很多。