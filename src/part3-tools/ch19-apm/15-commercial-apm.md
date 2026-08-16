---
title: "商业 APM 平台（Sentry、APMPlus、Bugly）"
chapter: "19"
section: "19.15"
status: "finalized"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-14"
last_verified_against: "Sentry Android 8.53.0 and Gradle plugin 6.19.0 releases, Sentry current profiling/replay docs plus AAR and source packages, Bugly Pro docs plus Maven metadata, APMPlus Android docs, Android 16KB page size docs and API 37 reference"
confidence: medium
tags: [apm]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://docs.sentry.io/platforms/android/"
  - type: official
    path: "https://www.volcengine.com/docs/6431"
  - type: official
    path: "https://bugly.qq.com/docs/"
  - type: official
    path: "https://bugly.tds.qq.com/docs/"
  - type: official
    path: "https://github.com/getsentry/sentry-java/releases/tag/8.53.0"
  - type: official
    path: "https://github.com/getsentry/sentry-android-gradle-plugin/releases/tag/6.19.0"
  - type: official
    path: "https://docs.sentry.io/platforms/android/profiling/legacy/"
  - type: official
    path: "https://repo1.maven.org/maven2/io/sentry/sentry-android/maven-metadata.xml"
  - type: official
    path: "https://repo1.maven.org/maven2/com/tencent/bugly/bugly-pro/maven-metadata.xml"
  - type: official
    path: "https://repo1.maven.org/maven2/com/tencent/bugly_16kb/bugly-pro/maven-metadata.xml"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: fixed
---

# 商业 APM 平台（Sentry、APMPlus、Bugly）

## 商业平台买的是服务能力和维护成本

APM（Application Performance Monitoring，应用性能监控）用于收集和分析 App 的稳定性、耗时与运行上下文。Sentry、APMPlus、Bugly 这类商业平台的付费内容主要包括 SDK、服务端、看板、告警、权限、符号文件、数据保留、工单协作和技术支持。符号文件包括 R8/ProGuard 的 `mapping` 与 native symbol，它们用于把混淆名或 native 地址还原成可读堆栈。团队由此减少采集后端维护、值班运营、告警规则维护和跨端数据分析工作。

选型前要先确认团队缺少哪种能力：崩溃治理、性能指标、用户会话回看、跨端追踪、国内访问、合规审计、私有化部署，或数据迁移。商业 APM 接入后会进入 App 启动、异常捕获、网络、页面和用户标识等敏感路径，采购评审必须同时看能力、成本和退出方式。

以下 Android 端版本按 2026 年 8 月 14 日的公开文档与发布仓库核对。PoC（Proof of Concept，小范围可行性验证）必须使用项目实际拿到的 artifact（仓库发布的 SDK 制品）、合同能力表和部署清单；商业合同也可能提供不同于公开仓库的分支。

| 平台 | 核对的公开 Android 制品 | 版本边界 |
|---|---|---|
| Sentry | `io.sentry:sentry-android:8.53.0`、Android Gradle plugin `6.19.0` | core AAR 的 `minSdk=21`；Session Replay 源码只在 API 26+ 启用；API 35+ profiling 使用 `ProfilingManager` |
| APMPlus 国内版 | `apm_insight:1.5.25.cn`、`apm_insight_crash:1.5.21`、plugin `1.4.2` | 国内与海外制品、上报地域不同，不能混用 |
| APMPlus 海外版 | `apm_insight:1.5.24.oversea`、`apm_insight_crash:1.5.21.oversea` | 当前公开接入页写明上报到马来西亚柔佛 |
| Bugly Pro | Maven Central 最新为 `com.tencent.bugly:bugly-pro:4.4.7.16` | 16KB page size 要选择 `com.tencent.bugly_16kb` 下的同版本；公开更新日志目前只说明到 `4.4.7.8` |

仓库中的最新版本只证明制品可下载，无法补足厂商尚未公开的行为说明。对 Bugly `4.4.7.8` 之后、截至 `4.4.7.16` 的版本做能力判断时，应以实际 AAR、合同说明和 PoC 结果为准。

Android 17 / API 37 没有一套通用于所有商业 APM 的新采集协议。需要验证厂商 SDK 在 API 37 上使用的公开 API、native library（C/C++ 等本地代码库）、前后台判断、网络插桩和采样行为。“兼容 Android 17”这句宣传本身不足以形成可复现的验收结论。

## 三个平台的定位

### Sentry：错误监控起家，移动端 APM 能力逐步补齐

Sentry Android 除了错误捕获，还支持 tracing（记录跨操作的调用链）、profiling（抽样调用栈）、Session Replay（会话画面回放）、logs、user feedback 和 release health（按发布版本统计会话与故障）。Gradle plugin 负责上传 source context（出错位置附近的源码）、mapping、native symbol 等构建产物；运行时 SDK 负责事件、span、profile 和 replay。两者的版本与开关要分别管理。

它适合这些团队：

- 已经用 Sentry 管 Web、后端或 iOS 错误，希望移动端统一入口。
- 需要异常、performance transaction、profiling 和 release health 放在一起看。
- 面向海外用户，Sentry SaaS（由厂商托管的在线服务）可稳定访问。

从 SDK `8.51.0` 起，Sentry UI Profiling 会按系统版本选择两条路径：Android 15（API 35）及以上调用系统 `ProfilingManager`，结果是 Perfetto trace；API 34 及以下默认回退到旧 ART runtime tracer。`8.53.0` 仍采用这套分支。设置 `enableLegacyProfiling=false` 可以关闭旧设备回退，也会关闭所有 transaction-based profiling；API 35+ 的 `ProfilingManager` UI Profiling 不受该开关影响。

两条路径都需要低采样，但风险不同。系统会对 `ProfilingManager` 请求限流，因此 API 35+ 即使命中 SDK 采样，也不保证每次请求都有 profile；这个后端也不支持 app-start profiling。旧 ART tracer 才涉及 Sentry 文档列出的 runtime crash 风险。如果 API 34 及以下新增 crash 集中在 `libart.so`、`art::Trace::StopTracing`、`pthread_getcpuclockid` 等 runtime 栈附近，应先关闭 legacy profiling 或降低采样率，再按 Sentry SDK、Android 版本和机型分组复现。升级 SDK 也要重新做灰度（先只向少量用户发布），不能把这些 runtime crash 全部归因给业务 native code。

Sentry Android 各能力存在 SDK/API 版本门槛，接入前要按版本表核对：

| 能力 | 最低 SDK / API 版本 | 边界与约束 |
|---|---|---|
| Session Replay | Sentry Android SDK `7.12.0+`；运行时 API 26+ | 默认遮盖文本、图片和 WebView；PixelCopy 仍可能出现遮盖位置偏差 |
| UI Profiling | Sentry Android SDK `8.7.0+`；`ProfilingManager` 后端需要 `8.51.0+` 和 API 35+ | manual 与 trace lifecycle 两种模式互斥；API 21～34 默认使用 legacy ART tracer |
| Transaction-based profiling | Sentry Android SDK 6.16.0+、API 22+ | legacy 能力，单次最长 30 秒；Sentry 文档建议迁移到 UI Profiling |
| App start profiling | Sentry Android SDK 7.3.0+ | 仅 legacy profiler 支持；API 35+ 的 `ProfilingManager` 后端忽略该开关；安装后的首次运行不会执行 |

Sentry 的主 profiling 页和 `8.51.0` changelog 都把 `ProfilingManager` 的起始版本写为 `8.51.0`，但 legacy 页导语目前写成 `8.47.0`。这里采用有对应发布记录的 `8.51.0` 作为可验证边界。

Session Replay 默认遮盖不代表已经满足业务合规要求。默认 PixelCopy 策略通过 Android 异步截图 API 取图，再依据 View hierarchy（界面控件树）计算遮盖位置，二者时序不一致时可能错位；实验性的 Canvas 策略在重绘时遮盖文本和图片，更可靠但开销更高。`SurfaceView` 把内容绘制到独立 surface，需要单独开启实验性采集，而且只能整体处理，无法遮盖其中某个地图标签、视频帧或 Unity 元素。涉及支付、健康、聊天或身份信息的页面，应在 PoC 中逐屏检查录制结果。`8.53.0` 修复了一种硬件视频编码器卡住后引发 ANR 的问题，但这项修复不能替代目标机型上的 replay 稳定性测试。

### APMPlus：国内移动 APM 平台型方案

APMPlus 是火山引擎的应用性能监控产品，覆盖 Android、iOS、鸿蒙、Web、PC、服务端等多平台。公开文档中 App 侧能力包括崩溃、卡顿、内存、网络、启动、自定义事件、日志回捞、报警和自定义看板等。日志回捞指平台按授权和配置，让指定设备补充上传故障附近的本地日志；它涉及的权限与数据范围需要单独审核。

它适合国内业务、需要托管平台和移动端专项能力的团队。当前 Android 接入页把国内与海外 artifact 分开：国内版上报到中国，海外版上报到马来西亚柔佛。数据地域应以合同、网络抓包和实际项目配置三方核对，不能只看依赖后缀。

公开验证页还给出了几个边界：crash 默认 100% 上报；其他监控项要命中平台采样配置；ANR（Application Not Responding，应用无响应）需要同时接入 crash 组件，只有性能组件时看不到 ANR 日志；网络自动监控依赖 Gradle plugin 和对应网络开关。PoC 设备应加入测试白名单，使其强制进入采集范围，或把目标模块临时调到 100%；否则“没有数据”可能只说明设备没有命中采样。

选型时要验证 SDK 支持的 Android 版本、targetSdk、ABI（应用二进制接口，此处主要指 `arm64-v8a` 等 CPU 架构）、主流网络库，卡顿 / ANR / OOM（Out of Memory，内存不足）/ native crash 的采集口径，符号文件与版本的绑定方式，日志回捞授权流程，以及远程采样和阈值调整能力。若采购专有云或私有化形态，应让厂商给出采集网关、消息缓冲、计算、查询存储、对象存储、冷热分层、备份恢复的实际 BOM（Bill of Materials，组件与资源清单）和容量模型；不能根据同厂商其他产品推测 APMPlus 使用了哪种数据库或流处理组件。

### Bugly：普通版和 Pro 版要拆开评估

Bugly 普通版更偏 crash、ANR、符号文件和版本稳定性看板。公开普通版 Android changelog 的最新条目仍是 `3.4.4`（2021 年），不能拿普通版文档推断 Bugly Pro `4.4.x` 的 API 或能力。

Bugly Pro 不能按普通版边界评估。Pro 版公开文档覆盖 crash、ANR、OOM、卡顿、FPS（Frames Per Second，每秒帧数）、内存、启动和页面回放等能力。ANR 有两组容易混淆的配置：

- `enableAllThreadStackAnr=true`：ANR 发生时抓取线程堆栈，当前 builder 文档标为默认开启；`4.4.6.2` 的更新说明写明全线程抓取时不再重复抓主线程。
- `setEnableRecordAnrMainStack(true)`：记录 ANR 发生前的主线程堆栈，`4.4.7.3` 新增，当前示例默认 `false`。

这两者采集时点不同。控制台缺少某份 stack（线程调用栈）时，要先核对配置、系统是否在采集完成前终止进程，以及当前机型能否取得 ANR trace。

## 选型表

| 平台 | 更适合 | 能力边界 | 数据与部署 | 成本和退出点 |
|---|---|---|---|---|
| Sentry | 海外业务、跨端错误监控、tracing / profiling / replay 统一 | profiling 和 replay 必须低采样；API 34 及以下的 legacy ART 风险、API 35+ 的系统限流、遮盖可靠性、国内访问和 PII（可识别个人的信息）规则要分别核验 | SaaS 与 self-hosted（自行部署）在功能、升级和支持责任上不同 | 按事件量、seat（付费账号席位）、保留周期、附件、profile 和 replay 用量估算；退出时导出 issue、release、event、trace、alert |
| APMPlus | 国内业务、移动端性能和稳定性一体化平台 | 启动、卡顿、ANR、OOM、网络、内存、日志回捞、单点查询、报警和看板较全 | 公开接入页区分中国与柔佛上报；专有云或私有化能力以合同为准 | 费用与事件量、留存、日志回捞、部署资源、支持服务相关；退出时迁移指标口径和 dashboard |
| Bugly Regular | 国内稳定性治理、崩溃 / ANR / 符号文件 | 偏稳定性入口，性能能力按套餐确认 | SaaS 为主，和腾讯生态流程结合较深 | 接入成本低；退出时要处理 crash issue、mapping、symbol、Webhook（HTTP 回调）和版本趋势 |
| Bugly Pro | 需要卡顿、内存、启动 Span、页面回放等增强能力 | Maven 最新是 `4.4.7.16`，公开能力说明只到 `4.4.7.8`；远端配置要逐项验收，16KB 还要选对 groupId | 关注 ANR 诊断字段、replay、Span 数据和合同部署形态 | 费用和数据量、采样、保留周期相关；退出时迁移诊断字段、附件和 Span 数据 |

选型结论不要只看功能列表。商业平台越深入 App 运行路径，越要确认数据归属、字段合规、留存周期、费用模型、16KB Page Size 适配和退出成本。

## 商业 APM 的评审维度

16KB Page Size 验收包含两个层次：`.so` 的 ELF load segment 要按 16KB 边界对齐，APK 中未压缩 `.so` 的 ZIP 存放位置也要对齐。ELF 是 native library 的可执行文件格式；APK 是安装包，AAB 是交给应用商店生成 APK 的发布包。两个检查都通过，才能说明最终交付物满足 16KB 加载要求。

| 维度 | 要问的问题 | 验收方式 |
|---|---|---|
| SDK 覆盖 | Android 版本、targetSdk、ABI、主流网络库、Flutter / React Native（RN）/ WebView 是否支持 | 用试点 App 接入，覆盖 release、debug、混淆和包含多种 ABI 的包 |
| 稳定性 | SDK 自身 crash、ANR、启动开销、线程数、包体积 | 先发布给 1% 用户，跟踪 SDK crash、启动 P95（95% 样本不超过的耗时）、主线程耗时和包体积增量 |
| 16KB Page Size 兼容（Android 15+） | SDK 及其传递依赖中的 `.so` 是否支持 16KB ELF alignment，APK/AAB 中未压缩 native library 的 ZIP alignment 是否正确 | 用 16KB 模拟器或真机运行 release 包；执行官方 `check_elf_alignment.sh`，再用 `zipalign -c -P 16 -v 4` 检查 APK；关注加载失败与 native crash |
| 性能数据 | 启动、慢帧、卡顿、ANR、OOM、网络、磁盘、功耗是否有清晰口径 | 用已知慢帧、弱网、OOM、ANR 样本回放，核对平台展示与本地 trace / log 是否一致 |
| 故障证据 | 堆栈、日志回捞、trace、截图、session replay、用户路径 | 检查是否有授权流程、脱敏规则、采样上限和故障时的人工取证路径 |
| 符号化 | ProGuard mapping、native symbol、版本和 build id（一次构建的唯一标识）绑定 | 用一个已知混淆 crash 和一个 native crash 验证堆栈还原率 |
| 采样配置 | 远程开关、按版本 / 机型 / 页面采样、异常强制采样 | 灰度配置后核对生效延迟、回滚延迟和误采样率 |
| 数据所有权 | 原始事件、聚合指标、附件、replay、日志、trace 属于谁 | 合同写明导出格式、保留周期、删除 SLA（约定的完成时限）、离职权限回收 |
| 部署形态 | SaaS、专有云、私有化的数据边界和网络路径 | 画出数据流向图，标出端上采集、网关、存储、计算、看板、审计 |
| 价格模型 | license、seat、事件量、日志量、回放量、留存周期、私有化资源 | 做 3 档流量估算：当前量、2 倍峰值、活动峰值 |
| 迁移成本 | schema（字段结构）、trace 名、alert、dashboard、mapping、历史数据能否迁出 | 试导出 7 天数据，导入内部仓库或另一平台做字段映射 |
| 合规 | 数据区域、PII 过滤、保留周期、访问审计、删除流程 | 由法务 / 安全 / 隐私团队按字段清单签字 |
| 运营 | 告警、负责人分配、工单、Webhook、报表导出 | 用一次演练验证谁收到告警、谁看样本、谁确认修复 |

## Sentry 的 transaction 和 profiling

Sentry 的性能模型围绕 transaction / span 展开。transaction 表示一次根操作，例如页面加载；span 表示其中较小的计时区间，例如网络、解析或渲染。多个相关 transaction 和 span 组成一条 trace，移动端事件由此可以和后端服务路径关联。

下面的结构把页面加载作为根 transaction，把网络、解析和渲染作为子 span：

```text
transaction: HomeScreen.load
  span: http GET /feed
  span: json.parse
  span: db.read_cache
  span: ui.render
```

这些 span 的名称必须稳定。动态 URL、feed id 或 user id 会产生大量不同名称，不应拼进 span description；确有分析需要时，应放入经过隐私审核且取值受控的 attribute/tag。

下面的 Kotlin 示例确保子 span 和根 transaction 在成功、异常两条路径上都会结束：

```kotlin
import io.sentry.Sentry
import io.sentry.SpanStatus

fun loadHome(): Feed {
    val transaction = Sentry.startTransaction("HomeScreen.load", "ui.load")
    return try {
        val networkSpan = transaction.startChild("http.client", "GET /feed")
        try {
            api.loadFeed().also {
                networkSpan.status = SpanStatus.OK
            }
        } catch (t: Throwable) {
            networkSpan.throwable = t
            networkSpan.status = SpanStatus.INTERNAL_ERROR
            throw t
        } finally {
            networkSpan.finish()
        }
    } finally {
        transaction.finish()
    }
}
```

漏掉任意一次 `finish()` 都可能让 span 缺失或 duration 失真。生产封装应把 `try/finally` 放进 facade（内部适配层），让业务调用者只提供待计时的代码 block。

如果后端也接了 Sentry 或 OpenTelemetry（跨厂商的可观测数据标准），移动请求携带 trace headers（传播 trace 标识的 HTTP header）后，可以从 App span 关联到服务器路径。应通过 `tracePropagationTargets` 只允许自有 API host；host 在这里指服务器域名。不要把 `sentry-trace` 或 baggage（随 trace 传播的附加键值）发给广告、支付等第三方域名。客户端与后端的采样规则也要一起核对；一端有数据、另一端缺失，可能来自两端各自的采样决定。

Tracing、profiling、Session Replay 和附件要使用彼此独立的采样预算。接入评审里要单列 `tracesSampleRate`/sampler（按上下文决定是否采样的函数）、`profileSessionSampleRate`、replay 的 `sessionSampleRate` 与 `onErrorSampleRate`，还要记录回放时长、脱敏规则、附件大小、丢弃原因和上传失败策略。`1.0` 适合白名单验收设备，不适合作为默认生产配置。

## APMPlus 的移动专项能力

国内商业 APM 的优势是贴近 Android App 线上治理常见问题：崩溃、ANR、卡顿、启动、网络、内存、日志回捞、单点查询、报警和 SDK 远程配置。

APMPlus 公开文档中的“卡顿分析”监控主线程 message 执行超时；这里的 message 是 Looper 消息队列中一次待执行任务。默认卡顿阈值为 2.5 秒、严重卡顿为 4 秒。“流畅性/丢帧”属于另一组数据，不能与 Android Vitals 慢帧、JankStats jank 或系统 ANR 混成一个指标。接入时要验证这些问题：

- ANR 是系统 ANR、SDK 自判卡死，还是两者都有。
- 卡顿是 Looper message timeout、慢帧，还是方法 trace；各自阈值和分母是什么。
- 内存是 OOM、泄漏、PSS（Proportional Set Size，按共享比例分摊后的进程物理内存）、Java heap，还是 native 内存。
- 日志回捞是否按用户授权和配置触发。
- SDK 采样是否能按版本和灰度动态调整。
- 私有化是否给出存储容量、查询 QPS（Queries Per Second，每秒查询数）、冷热分层（近期高频数据与历史低频数据分开存放）、备份恢复和升级窗口。

网络模块的公开接入示例通过 `ApmPlugin.okHttp3Switch` 开启 OkHttp3 插桩。若应用使用 OkHttp 4/5、Cronet（基于 Chromium 的网络引擎）、native stack 或自研 client，应使用真实请求核对；“网络分析”这个功能名称不能证明所有协议都被覆盖。

这些名词在不同平台里的口径可能不同。合同和接入文档里要写明起止点、阈值、采样、上报时机和聚合分母，否则多个控制台即使显示同名指标，也无法比较。

## Bugly 的稳定性边界

Bugly 普通版常见价值在：

- Java crash 聚合。
- Native crash 符号化。
- ANR 上报。
- 版本维度趋势。
- mapping / symbol 管理。
- Webhook 对接内部流程。

Bugly Pro 的评审口径要扩到性能监控：ANR 发生时的线程栈、发生前主线程记录、卡顿高频抓栈、启动 Span 是不同数据源，必须分别构造样本。启用这些能力前，要确认远端开关、采样率、低端机开销、上报时机、数据留存和 16KB artifact。当前 Maven Central 最新版本是 `4.4.7.16`，但公开 changelog 最后一条仍是 `4.4.7.8`；对这之后、截至 `4.4.7.16` 的版本，不能按版本号猜测新增或修复内容。

公开 Android 接入页写明 crash、ANR、OOM 默认 100% 上报且不支持采样，其他性能监控项支持采样。这个差异会直接影响事件费用、流量与隐私评审，不能用“统一采样率”估算 Bugly Pro。

如果团队只需要 crash / ANR 基础设施，普通版可能足够。如果要把 Bugly 当完整性能平台，要按 Pro 能力做 PoC，不要用普通版经验推断 Pro 版边界。

Bugly Pro 各增强能力存在 SDK 版本门槛，PoC 前要确认当前集成版本是否覆盖：

| 能力 | 最低 SDK 版本 | PoC 验证动作 |
|---|---|---|
| 页面启动耗时 | Android SDK `4.4.3+` | 核对 Activity 的渲染耗时、加载耗时与本地时间点 |
| 页面启动 Span | Android SDK `4.4.3.5+` | 检查 `startSpan()` / `endSpan()` 成对；同名 span 后写会覆盖前写 |
| ANR 发生时线程栈 | 当前 builder 的 `enableAllThreadStackAnr=true` | 检查 ANR 详情中的线程栈；主线程可能由独立字段呈现 |
| ANR 前主线程记录 | Android SDK `4.4.7.3+`，`setEnableRecordAnrMainStack(true)` | 对比关闭与开启后的 ANR 前主线程样本 |
| 页面回放 | Android SDK `4.4.7.3+` | 检查二次启动后的附件上报、采样、敏感页面与数据遮盖 |
| 16KB Page Size | `4.4.6.2+` 开始提供独立 16KB artifact；当前 Maven 版本为 `4.4.7.16` | 依赖必须来自 `com.tencent.bugly_16kb`；对 release APK 做 ELF/ZIP alignment 和运行验证 |

Bugly 的 16KB 文档存在历史措辞差异：changelog 与 Android 接入页写的是从 `4.4.6.2` 开始提供，单独的升级指南又以 `4.4.6.4` 为示例。当前可复现的做法是使用 Maven Central 已发布的 `com.tencent.bugly_16kb:bugly-pro:4.4.7.16`，再检查最终 release 包。groupId 是 Maven 坐标中的发布组织；只升级版本号但仍使用 `com.tencent.bugly`，不足以证明选择了 16KB 制品。

页面回放在当前文档中仍标为完善中的功能。它每秒采集一张 view hierarchy 与 screenshot，crash 后缓存为附件，等 App 二次启动再上传；截图采用整图马赛克，不是按字段证明敏感信息已被可靠识别。默认采样率是 0，文档建议 `0.01～0.1`。PoC 应检查 `replay.zip` 中的 JPEG 和 JSON 原始内容、资源开销、附件权限与删除流程。

以上门槛来自 Bugly Pro 官方 Android 接入页、更新日志和功能页。Bugly 是商业 SDK，版本阈值由厂商制品控制；当前集成版本低于门槛时，应先在独立分支升级并做小流量验证。

## PoC 验收表

商业 APM 也要按小流量验证。试点时选一条完整路径：发现问题、查看样本、定位责任、验证修复、关闭告警。

| 验收项 | 构造样本 | 通过标准 |
|---|---|---|
| Java crash | 构造一个已知异常，带混淆 mapping | 平台能聚合、还原符号、按版本和用户查询 |
| Native crash | 构造一个测试 `.so` 崩溃，上传 symbol | 能显示 native 栈、build id、ABI、系统版本 |
| ANR | 在受控测试包中用 input、BroadcastReceiver、Service 等超时路径构造系统 ANR，再补锁等待 / Binder 等待 | 能区分系统 ANR 与 SDK 自判卡死；记录触发类型、主线程与相关线程栈 |
| 慢帧 / 卡顿 | 构造 60Hz 和 120Hz 页面卡顿 | 能给出慢帧时间、页面、设备、系统版本；与 Perfetto FrameTimeline 大体一致 |
| 启动 | 冷启动、温启动各跑 30 次 | 能按版本、渠道、机型看 P50（中位数）和 P95（第 95 百分位）；采样对启动耗时影响可接受 |
| 网络阶段 | 对每种受支持 client 构造 DNS 慢、connect 慢、TLS 慢、服务端慢 | 文档承诺的阶段都能出现；未支持的 client 或协议有明确补点方案 |
| OOM / 内存 | 构造 Java heap 压力和 native 内存压力 | 能拿到内存趋势、设备水位、进程存活信息；不把 LMK（系统因内存压力终止进程）误写成 Java OOM |
| 采样准确性 | 白名单设备发固定数量事件，再把采样率改为 25% 重复测试 | 100% 配置下无系统性漏报；采样配置的生效时间、误差和服务端限流可解释 |
| 告警噪声 | 构造一次低量级异常和一次集中异常 | 告警阈值可控；不会因采样波动反复报警 |
| 低端机开销 | 低端设备跑 30 分钟常用场景 | SDK 线程数、CPU、内存、流量、包体积增量在接入预算内 |
| 16KB Page Size | Android 15～17 的 16KB 环境运行 release 包并触发 crash / ANR / profiling | 所有 `.so` 的 ELF/ZIP alignment 通过；App 与 native 采集能力正常 |
| 删除与权限 | 创建专用测试用户，产生 event、replay、log、attachment 后发起删除 | 数据在合同 SLA 内删除；导出、审计和离职权限回收均有记录 |

## 成本模型与 ROI 估算

TCO（Total Cost of Ownership，总拥有成本）不只包含“每年多少钱”，还应拆成这些项：

| 成本项 | 计算口径 | 低估后的后果 |
|---|---|---|
| license / 套餐 | App 数、平台数、MAU（月活跃用户数）、事件量、seat | 后续扩端或扩团队时费用跳涨 |
| 数据量 | crash、ANR、trace、log、replay、attachment 的月增量 | 保留周期被迫缩短，线上样本查不到 |
| 私有化资源 | 计算、存储、对象存储、消息队列、带宽、备份 | 查询慢、告警延迟、活动峰值时丢数据 |
| 运维人力 | 升级、容量、备份、权限、审计、值班 | 平台买回来后仍要内部团队兜底 |
| 合规成本 | 字段梳理、脱敏、删除流程、访问审计 | 上线慢，或后续被安全团队叫停 |
| 迁移成本 | facade、schema、历史数据、dashboard、alert、mapping | 供应商更换时业务代码和看板一起返工 |

月度总成本可以按这个公式估：

```text
月度 TCO = 平台订阅费用
         + 数据增量费用
         + 存储和保留费用
         + 私有化基础设施费用
         + 运维和值班人力成本
         + 合规与审计成本
         + 迁移预留成本
```

ROI（Return on Investment，投资回报）要用可比较的数据计算。可量化的收益包括：崩溃率下降带来的留存改善、ANR / 慢帧定位时间缩短、值班误报减少、内部 APM 后端维护人力减少、合规审计时间缩短。PoC 阶段至少记录“接入前定位一次线上 ANR 的耗时”和“接入后用平台样本定位同类问题的耗时”。

## 私有化责任表

私有化的交付范围包括内网部署，也包括部署、升级、存储、权限、审计、数据删除和故障责任。所有责任都要写进合同和验收文档。

| 事项 | 厂商应交付 | 客户侧负责 | 验收材料 |
|---|---|---|---|
| 部署架构 | 网关、采集服务、计算、存储、看板、告警的拓扑 | 网络、域名、证书、Kubernetes（容器编排）/ VM（虚拟机）资源 | 架构图、端口清单、容量模型 |
| 升级 | SDK 版本、服务端版本、兼容表、回滚方案 | 升级窗口、灰度策略、回滚审批 | 升级手册、回滚演练记录 |
| 存储 | 热数据、冷数据、对象存储、备份恢复方案 | 磁盘、备份介质、保留周期 | 容量压测、恢复演练、保留策略 |
| 权限 | 角色模型、项目隔离、审计日志 | 组织架构、离职回收、最小权限 | 权限表、审计样例 |
| 数据删除 | 用户数据删除 API、批量清理任务 | 删除工单、合规审批、回查流程 | 删除 SLA、抽样验证记录 |
| 故障责任 | 组件健康检查、告警规则、支持响应时间 | 值班人员、基础设施故障处理 | SLA、RCA（Root Cause Analysis，根因分析）模板、演练记录 |
| 成本控制 | 采样、保留、冷热分层、限流策略 | 业务峰值预估、预算上限 | 月度容量报表、费用报表 |

## 内部 APM facade 与字段合同

商业平台 SDK 不要直接散落在业务代码里。先定义内部 facade，也就是业务代码只依赖的统一监控接口，再由实现层映射到各平台 API。

```kotlin
data class MonitorContext(
    val pageName: String,
    val appVersion: String,
    val buildId: String,
    val experimentId: String?,
    val deviceTier: String
)

interface TraceHandle {
    fun addMetric(name: String, value: Long)
    fun addTag(name: String, value: String)
    fun finish(status: String)
}

interface AppMonitor {
    fun setUser(anonymousId: String?, userType: String)
    fun clearUser()
    fun setContext(context: MonitorContext)
    fun captureException(throwable: Throwable, tags: Map<String, String>)
    fun startTrace(name: String, context: MonitorContext): TraceHandle
    fun reportMetric(name: String, value: Long, tags: Map<String, String>)
}
```

实现层要保证 `finish()` 幂等，即重复调用也只结束一次，并提供内部 `try/finally` 包装，避免某个 vendor（平台供应商）要求手工结束 span 时产生没有结束时间的数据。`anonymousId` 应是经过隐私评审的假名标识：它可以关联同一主体的事件，但不直接暴露真实身份。退出登录时调用 `clearUser()`，不要把手机号、邮箱、广告标识符或可逆业务主键直接传给厂商。

字段合同要比代码接口更早定下来：

| 字段 | 约束 |
|---|---|
| `page.name` | 用产品页面名，不用 Activity 类名直接当展示名 |
| `user.type` | 匿名、登录、会员、内测等有限枚举 |
| `user.id` | 只允许经同意的假名标识；定义生成、轮换、删除和跨平台映射规则 |
| `app.version` / `build.id` | 和 release、mapping、native symbol 一一绑定 |
| `experiment.id` | 灰度、A/B、功能开关统一命名 |
| `network.stage` | DNS、connect、TLS、request、TTFB（Time to First Byte，收到首字节前的时间）、download 统一枚举 |
| `device.tier` | 低端 / 中端 / 高端规则固定，避免迁移后设备分桶（按规则分组）发生变化 |
| `trace.name` | 由内部词典生成，不直接使用 vendor 自动名 |

只要字段合同稳定，更换 Sentry、Firebase、APMPlus、Bugly 或自建平台时，业务侧不需要到处改 SDK API。

## 退出成本与迁移失败样本

商业平台还要评估退出成本：数据能否导出，事件 schema 是否能迁移，客户端 SDK 是否与业务代码耦合，自定义 trace 名称是否平台专有，告警和工单流程是否绑定平台。

迁移中常见的失败样本有三类：

| 样本 | 现场表现 | 规避方式 |
|---|---|---|
| 字段名漂移 | 旧平台用 `screen_name`，新平台用 `page`；历史看板无法和新数据合并 | 接入前建立内部字段词典，所有 vendor 字段都由映射层生成 |
| 符号文件断档 | 旧平台保存了 mapping / symbol，新平台只有新版本符号；历史 crash 无法还原 | mapping、native symbol、build id 和 release 元数据单独归档，不能只放在 vendor 平台 |
| 告警规则丢失 | 迁移后阈值、负责人、工单状态无法搬迁；值班噪声暴涨 | 把告警规则导出成内部配置，迁移前做一次影子告警对照 |

迁移前要做一次 7 天影子运行：两个平台同时接收数据，老平台继续报警，新平台只记录、不通知值班人员。对比 crash 聚合数、ANR 数、慢帧 P95、网络错误率、告警数量、误报样本和缺失样本，再决定切流比例，也就是逐步把多少正式监控与告警转到新平台。

## 核验来源

商业 APM 的实现不是 AOSP 组成部分，无法用 Android 17 platform tag（AOSP 对应版本标签）验证厂商闭源逻辑。核验采用三层证据：

1. 厂商公开接入页、功能页和 changelog，用于确认制品版本、开关和产品口径。
2. 可下载 AAR 的 Manifest、source package（源码包）和最终 APK，用于确认 `minSdk`、API 分支、native library 与打包结果。
3. Android 8～17 真机或模拟器的构造样本，用于确认运行行为、采样、上传、符号化和开销。

“文档写了支持”只完成第一层。采购验收要把第二、三层的制品哈希、测试包 build id、设备、系统版本和平台截图归档。

## 参考资料

### Sentry

- [Sentry Android SDK](https://docs.sentry.io/platforms/android/)
- [Android tracing](https://docs.sentry.io/platforms/android/tracing/)
- [Android profiling](https://docs.sentry.io/platforms/android/profiling/)
- [Android legacy profiling](https://docs.sentry.io/platforms/android/profiling/legacy/)
- [Android profiling troubleshooting](https://docs.sentry.io/platforms/android/profiling/troubleshooting/)
- [Android Session Replay](https://docs.sentry.io/platforms/android/session-replay/)
- [Sentry Java/Android SDK 8.53.0 release](https://github.com/getsentry/sentry-java/releases/tag/8.53.0)
- [Sentry Java/Android SDK 8.51.0 release](https://github.com/getsentry/sentry-java/releases/tag/8.51.0)
- [Sentry Android Gradle plugin 6.19.0 release](https://github.com/getsentry/sentry-android-gradle-plugin/releases/tag/6.19.0)
- [`sentry-android` Maven metadata](https://repo1.maven.org/maven2/io/sentry/sentry-android/maven-metadata.xml)
- [Sentry Java/Android SDK 8.50.1 release](https://github.com/getsentry/sentry-java/releases/tag/8.50.1)

### APMPlus

- [APMPlus 产品简介](https://www.volcengine.com/docs/6431/69088)
- [Android SDK 接入](https://www.volcengine.com/docs/6431/68852)
- [Android SDK 数据上报验证](https://www.volcengine.com/docs/6431/1175072)
- [卡顿分析](https://www.volcengine.com/docs/6431/68854)
- [内存优化](https://www.volcengine.com/docs/6431/68858)

### Bugly

- [Bugly Pro 文档中心](https://bugly.tds.qq.com/docs/)
- [Bugly Pro Android SDK 接入](https://bugly.tds.qq.com/docs/sdk/android/)
- [Bugly Pro SDK 更新日志](https://bugly.tds.qq.com/docs/sdk/change_log/)
- [Bugly Pro 16KB Page Size 升级指南](https://bugly.tds.qq.com/docs/tutorial/Android/16kb_version)
- [Bugly Pro 16KB `4.4.7.16` Maven artifact](https://repo1.maven.org/maven2/com/tencent/bugly_16kb/bugly-pro/4.4.7.16/)
- [Bugly Pro `4.4.7.16` Maven artifact](https://repo1.maven.org/maven2/com/tencent/bugly/bugly-pro/4.4.7.16/)
- [Bugly Pro 16KB `4.4.7.8` Maven artifact](https://repo1.maven.org/maven2/com/tencent/bugly_16kb/bugly-pro/4.4.7.8/)
- [Bugly Pro Maven metadata](https://repo1.maven.org/maven2/com/tencent/bugly/bugly-pro/maven-metadata.xml)
- [Bugly Pro 16KB Maven metadata](https://repo1.maven.org/maven2/com/tencent/bugly_16kb/bugly-pro/maven-metadata.xml)
- [Bugly Pro ANR](https://bugly.tds.qq.com/docs/tutorial/Android/anr)
- [Bugly Pro 页面启动耗时](https://bugly.tds.qq.com/docs/tutorial/Android/pagelaunch/)
- [Bugly Pro 页面回放](https://bugly.tds.qq.com/docs/tutorial/Android/replay_report)
- [Bugly 普通版 Android changelog](https://bugly.qq.com/docs/release-notes/release-android-bugly/)

### Android

- [Support 16 KB page sizes](https://developer.android.com/guide/practices/page-sizes)
