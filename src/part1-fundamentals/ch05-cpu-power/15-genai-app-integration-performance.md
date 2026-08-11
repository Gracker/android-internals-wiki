---
title: "系统托管 GenAI：AICore、OnDeviceIntelligence 与资源竞争"
chapter: "5.15"
section: "5.15"
status: ready-for-review
drafted_date: "2026-06-18"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-26"
last_verified_against: "Android 17/API 37 公开文档"
confidence: medium-low
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/5.30-android17-ondevice-intelligence-framework-performance.md"
sources:
  - type: official
    path: "developer.android.com/ai/aicore"
  - type: official
    path: "developer.android.com/ai/reference/kotlin/com/google/ai/edge/aicore/package-summary"
  - type: blog
    path: "developer.android.com/ai/get-started"
  - type: deepresearch
    path: "DeepResearch/2026-06-23-android17-ondevice-llm-inference-architecture.md"
tags: ["GenAI", "AICore", "端侧AI", "性能优化", "NPU", "IPC"]
related_chapters: ["5.9", "5.10", "5.11", "5.12", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/章节深挖"
task6_state: fixed
task9_state: reviewed
pipeline_stage: ready-for-review
last_rework_at: "2026-07-26T09:35:49+08:00"
last_rework_run_id: "20260726-093549-rework-4d26677f"
rework_summary: "修复待核验标记：更正 AICore 进程段落错字，移除未经核验的具体模型内存表，改为 Android 17 基线下的安全观测口径；补充 DeepResearch 来源并明确剩余风险。"
---

# 5.15 系统托管 GenAI：AICore、OnDeviceIntelligence 与资源竞争

在 Android 17 / API 37 上讨论端侧 GenAI，先要分清“平台版本”和“模型服务版本”。Android 17 决定 App 可使用的系统 API；AICore、Gemini Nano 模型和 ML Kit GenAI 库仍可独立更新。同一台 Android 17 设备上，模型版本、支持的能力和下载状态都可能不同。因此，`SDK_INT >= 37` 不能代替运行时能力检测。

“Google Intelligence API” 是早期公开资料使用过的称谓。面向应用的当前入口是 **ML Kit GenAI APIs**：摘要、校对、改写、图片描述、语音识别等场景优先使用专用 API，自定义文本或多模态提示词使用 Prompt API。它们在 AICore 上调用 Gemini Nano。旧版 `com.google.ai.edge.aicore` 示例不能直接当作当前 ML Kit API 使用。

平台锚点为 Android 17 / `android-17.0.0_r1`。AICore 和 Gemini Nano 不属于该 AOSP 源码标签，涉及它们的结论以当前公开 API 契约为准；公开文档没有说明的进程名、Binder 次数、加速器选择、队列策略和 OOM 优先级均不作实现承诺。

## 先选清楚执行架构

端侧生成式 AI 常见的两条路径，资源归属和可控范围差别很大：

| 维度 | ML Kit GenAI + AICore | App 内 LiteRT-LM |
|---|---|---|
| 模型 | 系统管理并供多个 App 共享的 Gemini Nano | App 选择并管理的 `.litertlm` 模型 |
| 可用性 | 受设备、模型版本、功能配置和下载状态共同影响 | 受模型文件、ABI、运行时和所选后端支持情况影响 |
| 硬件控制 | AICore 隐藏底层硬件接口，App 不指定具体 NPU/GPU 路径 | App 在运行时支持范围内选择 CPU、GPU 或 NPU 后端 |
| 存储与模型生命周期 | AICore 负责模型分发和更新 | App 负责下载、校验、存储、初始化与释放 |
| 内存观测 | App 进程指标只覆盖调用端分配，不能代表系统总开销 | 权重、KV cache、工作区等主要进入 App 的进程与驱动分配 |
| 适合场景 | 支持设备上的标准能力、低接入成本、共享系统模型 | 自选模型、离线模型版本控制、专用后端和自定义推理流程 |

两条路径都在设备上执行，但工程责任并不相同。AICore 路径应围绕“状态、配额、前台限制和端到端延迟”设计；LiteRT-LM 路径还要负责模型文件、内存峰值、后端兼容和引擎关闭等工作。

Android 17 还包含受权限保护的 OnDeviceIntelligence（ODI）framework。它由 OEM 提供管理 service 与隔离推理 service，通过 `Feature`、prepare/process/streaming request、数据补充回调和 `InferenceInfo` 组织系统级能力。ODI 是 `@SystemApi`/特权集成面，不是普通应用替代 ML Kit GenAI 的公共 SDK；AICore 的模型、配额和设备支持契约也不能套到 OEM ODI provider 上。

ODI 的 system_server 逻辑会按调用 UID 的前台 importance 建立带 `BIND_SCHEDULE_LIKE_TOP_APP` 的高优先级连接。这能提高绑定服务的进程调度地位，但不构成模型、token 或 deadline 的统一推理优先队列，也不直接控制 NPU 频率。`InferenceInfo` 只记录 UID、开始/结束与暂停时长，不包含能量或加速器类型；OEM 若要做功耗归因，还需额外结合 runtime 与 SoC counter。

## AICore 公开保证了什么

官方文档对 AICore 给出的稳定边界包括：

- AICore 是 Android 的系统级服务，负责运行 Gemini Nano、管理模型分发与更新，并使用设备硬件加速推理。
- ML Kit GenAI 在 AICore 之上提供高阶接口。同一设备上的 App 可以复用系统已有的 Gemini Nano，避免每个 App 重复保存模型。
- 提示词、推理和输出在设备本地处理。AICore 不直接访问互联网；包括模型下载在内的网络请求经 Private Compute Services 处理。
- AICore 隔离各次请求，处理结束后不保存输入和输出记录。

下图只表达公开文档能支持的层级关系，不把内部调用拆成未经公开保证的 Binder 事务或固定 HAL：

```text
App
  └─ ML Kit GenAI API
       └─ AICore 系统服务
            ├─ Gemini Nano、功能配置与安全处理
            ├─ 设备选择的硬件加速路径
            └─ Private Compute Services（模型下载等网络请求）
```

这条链路说明控制权的边界：App 能控制请求内容、调用时机和结果消费方式；AICore 负责模型、运行时和底层硬件。即使某台设备的 trace 显示了特定包名、Binder 调用或 GPU/NPU 活动，也只能把它当作该设备当时版本的观测结果。

### 不要从“系统服务”推导内部细节

以下推论都超出了公开契约：

- 固定 AICore 包名或进程名；
- 每个请求固定发生两次 Binder 事务；
- 一定经过 NNAPI HAL，或一定使用 NPU/GPU；
- 回调一定运行在 Binder 线程池；
- AICore 对前后台 App 使用某种确定的排队或时间片策略；
- AICore 拥有固定 `oom_score_adj`，内存压力时一定先杀其他 App。

这些实现可能随设备厂商、AICore 模块和模型版本变化。应用代码不应依赖它们，性能报告也应写清设备、系统构建、AICore/ML Kit 版本、基础模型名和测试时的热状态。

## ML Kit GenAI 的准备状态机

Prompt API 的可用性至少由设备支持、AICore 配置和模型下载状态共同决定。当前公开 API 使用四个具名状态：

- `FeatureStatus.UNAVAILABLE`：设备不支持，或设备尚未取得可用配置；
- `FeatureStatus.DOWNLOADABLE`：支持该能力，但模型尚未下载；
- `FeatureStatus.DOWNLOADING`：下载正在进行；
- `FeatureStatus.AVAILABLE`：当前可以使用。

下面的代码用于展示状态判断、下载和可选预热的顺序。它保留具名枚举，不使用来源不明的整数值：

```kotlin
private val generativeModel by lazy { Generation.getClient() }

suspend fun preparePromptModel(warmUpForInteractiveUse: Boolean): Boolean {
    when (generativeModel.checkStatus()) {
        FeatureStatus.AVAILABLE -> Unit

        FeatureStatus.DOWNLOADABLE -> {
            var completed = false
            generativeModel.download().collect { event ->
                when (event) {
                    DownloadStatus.DownloadCompleted -> completed = true
                    is DownloadStatus.DownloadFailed -> throw event.e
                    else -> Unit // DownloadStarted 或 DownloadProgress
                }
            }
            if (!completed) return false
        }

        FeatureStatus.DOWNLOADING,
        FeatureStatus.UNAVAILABLE -> return false

        else -> return false
    }

    if (warmUpForInteractiveUse) {
        generativeModel.warmup()
    }
    return true
}
```

这段代码只负责“本次是否可进入推理”。`DOWNLOADING` 应映射成可理解的 UI 状态，并在下载状态变化后重新检查；`UNAVAILABLE` 应走产品预先设计的替代功能。`warmup()` 会把 Gemini Nano 加载进内存并初始化运行时组件，可改善第一次推理的延迟，也会提前产生时间、内存和能耗开销。它适合用户即将进入交互式生成场景时调用，不适合在每次任务开始前无条件重复调用。

生成长响应时，流式接口能更早把内容交给 UI。它改善的是可感知的首段响应时间，不代表总计算量一定下降。消费 `Flow` 时仍需限制文本累计、Markdown 解析和 UI 刷新频率，避免每个很小的分片都触发一次完整重组或布局。

### 不能只检查 `SDK_INT`

当前官方支持列表会随模型和设备扩展，专用 GenAI API 与 Prompt API 的设备列表也不相同。还应注意：

- 同一 API 在不同设备上可能使用不同 Gemini Nano 版本；
- `getBaseModelName()` 可用于记录当前基础模型名；
- 相同提示词在不同模型版本上可能得到不同输出；
- 解锁 bootloader 的设备不支持当前 ML Kit GenAI API；
- AICore 刚初始化、清除数据或重新安装后，配置同步可能尚未完成。

因此，UI 入口是否显示、是否提示下载、是否启用功能，都应由 API 的实时状态决定。SDK 版本适合做最低平台 API 检查，不能用来猜测模型是否可用。

## 前台限制与配额是硬边界

ML Kit GenAI 当前只允许 **top foreground application** 执行推理。App 离开前台后，即使保留前台服务，调用仍会收到 `ErrorCode.BACKGROUND_USE_BLOCKED`。这会直接否定两类常见设计：

- 不能把 AICore 推理放进 WorkManager，期待离开页面后继续完成；
- 不能用 foreground service 规避前台限制。

页面切到后台时，应停止提交新请求，取消不再需要的结果收集，并把 UI 标记为可恢复状态。恢复前台后重新检查能力和业务上下文，不要假设旧请求仍会完成。

AICore 还按 App 执行推理配额：

- 短时间请求过多可能返回 `ErrorCode.BUSY`；官方建议采用指数退避；
- 长时间累计使用可能返回 `ErrorCode.PER_APP_BATTERY_USE_QUOTA_EXCEEDED`。

指数退避要有最大次数和用户可见的终止状态。交互页面中无限重试会同时放大耗电、热量和排队时间。App 内也应合并重复请求，并限制并发数；这是调用方的流量控制，不应被描述成 AICore 的多租户调度规则。

## 线程、取消与 UI 更新

Kotlin 的 Prompt API 以挂起函数和 `Flow` 表达异步工作，Java 包装层使用 `ListenableFuture` 和显式 `Executor`。调用方应遵循所选 API 的线程契约，不要假定回调来自 Binder 线程。

工程上可以按三段拆开：

1. 在 App 自己的工作线程中完成图片缩放、文本整理、token 预算和业务数据读取；
2. 通过 ML Kit 发起请求，不在主线程同步等待 Java `Future.get()`；
3. 对流式结果做节流和增量渲染，把需要操作 View 的工作切到主线程。

取消也要按产品语义设计。用户修改输入、离开页面或开始新请求时，旧结果通常已经失去价值；停止收集输出可避免继续更新 UI。但“调用端停止收集”是否立即停止设备侧计算，应以具体 API 版本的取消契约和实测为准，不能由协程取消自行推导。

## 内存归属：App 指标不等于系统总成本

AICore 管理共享模型，使 App 不必把 Gemini Nano 放进自己的 APK、数据目录和模型运行时预算。这个优势不表示调用方没有内存开销：

- Prompt 字符串、输入图片及其缩放副本属于 App；
- 请求构造、结果对象、流式文本累计和 UI 富文本缓存属于 App；
- AICore 管理的模型权重、运行时与服务侧工作不在 App 的 Java/Kotlin heap 中；
- 驱动共享缓冲区和硬件工作区的归属还会受设备实现与统计口径影响。

所以，`Debug.getMemoryInfo()` 或对 App 单进程执行 `dumpsys meminfo`，只能回答“调用端增长了多少”，不能回答“这次功能给整机增加了多少内存压力”。公开文档也没有给出跨设备通用的 Gemini Nano RSS/PSS 数字。

建议分层观测：

| 层级 | 记录内容 | 能回答的问题 |
|---|---|---|
| App | Java/native/graphics 内存、输入图片大小、结果累计长度 | 调用端是否有泄漏、重复位图或无界文本缓存 |
| 相关系统组件 | 在可观测的测试设备上记录服务进程 PSS/RSS、启动与下载阶段 | 模型准备或推理期间，服务侧水位是否明显变化 |
| 整机 | MemAvailable、PSI、lmkd 事件、后台进程回收 | 功能是否把设备推入持续内存压力 |
| 业务 | 请求成功率、页面重建、进程死亡与恢复 | 内存压力是否已经影响用户流程 |

不要根据“系统服务”身份猜测 LMK 的回收顺序，也不要假定调用方死亡后推理一定继续。若需要分析回收原因，应把 lmkd 事件、进程状态、PSI 和请求时间线放在一起。§4.4 说明了 Android 17 的 LMK 机制，§5.14 说明了 Cache 与内存统计的层级边界。

## 渲染、CPU 与共享硬件资源

AICore 隐藏具体加速器，但推理仍会消耗 CPU、内存带宽和某类硬件执行资源。App 侧还会负责预处理、结果解析与 UI 更新。因此，生成期间出现掉帧有多种可能：

- 主线程对输入图片做缩放或格式转换；
- 每个流式分片都触发 Compose 重组、Markdown 全量解析或 RecyclerView 更新；
- App 的工作线程挤占主线程和 RenderThread 所需的 CPU 时间；
- 服务侧工作与渲染在内存带宽、功耗或设备选定的加速器上相互影响；
- 持续生成使设备进入更强的热限制。

GPU frequency 上升不能单独证明 AICore 正在用 GPU；CPU frequency 上升也可能来自输入处理、安全处理或 UI。更可靠的方法是做成对实验：相同页面、相同输入、相同热起点，分别关闭和开启推理，多次比较帧时间、首段延迟、总延迟、CPU 调度和热状态。

流式输出的 UI 更新建议按时间窗口或字符量批处理。例如每 50～100 ms 合并一次短分片，再更新可见文本。这个数值是 UI 调度策略的起点，需要用目标设备的帧时间验证，不是 AICore 的性能保证。

## ADPF 能做的事很有限

Android 17 的 `PerformanceHintManager.createHintSession()` 要求线程 ID 属于调用进程的线程组；`Session.setThreads()` 对不属于该 App 的线程会抛出 `SecurityException`。`setPreferPowerEfficiency(true)` 描述的也是该 hint session 内线程的调度偏好。

边界很明确：App 可以为自己长期存在的预处理、后处理或渲染相关工作线程建立 ADPF 会话，不能把 AICore 内部线程加入会话，也不能借此要求 AICore 的 NPU/GPU 选择某个频率。把 `setPreferPowerEfficiency(true)` 写在 `checkStatus()` 和 `generateContent()` 之间，不会自动把推理切到“能效 NPU 模式”。

对短促且到达时间不固定的请求，也不要为了“用了 ADPF”临时创建线程和会话。AOSP 源码要求 hint session 面向一组相互关联、长期存在的线程；周期性工作应报告目标时间和实际工作时间。具体用法见 §5.9。

## 热状态与降级

Android 的 `PowerManager.addThermalStatusListener()` 能通知设备当前的整体热限制级别。该状态适合做产品降级信号，但它是粗粒度、设备相关的信号，不能换算成固定的 NPU 频率或 token/s。

“持续 30～60 秒后从 200 ms 上升到 500～1000 ms”没有跨设备依据，性能数据应按机型测量以下指标：

- cold start、warm start 和预热后的首段延迟；
- prefill 时间、首 token 时间、decode token/s 和完整请求时间；
- 连续请求中的 P50、P95、P99 及随时间的变化；
- 请求期间的 thermal status、thermal headroom、帧时间与电量消耗；
- `BUSY`、电量配额、后台阻止、下载失败和模型不可用的比例。

降级策略可以包括缩短输入、限制最大输出、降低连续请求频率、暂停非必要生成，或切换到规则功能/云端服务。是否在 `THERMAL_STATUS_MODERATE` 就降级，应由功能的交互要求和目标设备测试决定，不应写成所有 App 共用的阈值。

## 需要自选模型时：LiteRT-LM

如果产品需要固定模型版本、自己管理上下文、选择后端，或目标设备不在 AICore 支持列表中，可以评估 LiteRT-LM。当前官方 Kotlin API 支持 Android，并提供 CPU、GPU 和 NPU 后端；`Engine.initialize()` 可能耗时较长，官方要求放在后台线程或协程中，同时在使用结束后关闭 `Conversation` 与 `Engine`。

下面的代码用于说明资源生命周期。生产代码还要补上版本固定、模型校验、设备能力探测和可观测的错误处理：

```kotlin
withContext(Dispatchers.IO) {
    val config = EngineConfig(
        modelPath = modelPath,
        backend = Backend.GPU(),
        cacheDir = context.cacheDir.path,
    )

    Engine(config).use { engine ->
        engine.initialize()
        engine.createConversation().use { conversation ->
            conversation.sendMessageAsync(prompt).collect { message ->
                consumeIncrementally(message)
            }
        }
    }
}
```

这里的 `GPU` 只是一次显式选择示例，不是所有 Android 设备的默认答案。GPU 需要清单中的相应 native library 声明；NPU 还可能需要厂商库目录。初始化失败时应记录后端、设备和模型信息，再按目标设备验证过的策略回退。“GPU → 多模态 CPU → 纯文本 CPU”的固定三级顺序不是 LiteRT-LM 的通用要求，也不应捕获所有 `Throwable` 后静默继续。

LiteRT-LM 把更多控制权交给 App，也把模型存储、进程内内存、引擎初始化、会话并发和关闭责任交给 App。它与 AICore 是两种资源模型，不能只比较一次请求的平均延迟。

## AppFunctions 不负责模型推理

AppFunctions 从 Android 16 起提供 Android 平台 API 和 Jetpack 库，让 App 把自身操作注册成设备上的工具；调用者必须拥有 `EXECUTE_APP_FUNCTIONS` 权限。它与 MCP 的概念相近，解决的是“授权调用者如何发现并执行 App 能力”。

截至 Android 17，官方仍把 AppFunctions 标为 experimental preview；截至 2026 年 5 月，与 Gemini 的集成仍是 private preview。AppFunctions 没有承诺由 AICore 执行模型，也没有给出“支持 8 小时 agent”的运行保证。一个 agent 可以使用 AICore、云端模型或其他本地运行时来决定调用哪个工具，这与 AppFunction 本身的执行协议是两个问题。

## 性能测量清单

### 每个请求都记录

- 设备型号、Android build fingerprint、App/ML Kit 版本；
- `getBaseModelName()`、`checkStatus()` 结果、是否发生下载和预热；
- 输入类型、输入 token/图片尺寸、`maxOutputTokens`；
- 请求开始、首分片、最终分片、取消和失败时间；
- 错误码、前后台状态、当前 thermal status；
- 同一页面的帧时间和流式 UI 更新次数。

Prompt API 当前要求输入少于 4000 token，并建议避开超过 4K token 的长输出。把 token 数写进性能记录，才能区分“模型变慢”和“请求规模变大”。

### 把一次请求拆成阶段

| 阶段 | 计时边界 | 常见问题 |
|---|---|---|
| 能力检查 | 调用 `checkStatus()` 到返回 | 配置未完成、服务连接、设备不支持 |
| 下载 | `DownloadStarted` 到 `DownloadCompleted` | 网络、磁盘、配置与模型分发 |
| 预热 | `warmup()` 开始到返回 | 模型装载与运行时初始化 |
| 首段 | 发起生成到收到第一段 | 冷启动、prefill、排队、热限制 |
| 持续生成 | 第一段到最终一段 | decode 速度、配额、热限制 |
| UI 消费 | 收到分片到画面呈现 | 主线程、解析、重组与布局 |

只记录“点击到完整文本出现”的总时间，无法判断优化应放在模型准备、请求规模还是 UI。也不要把墙钟时间直接命名为 Binder 延迟、NPU 时间或 AICore 排队时间，除非 trace 中有能支持该分解的设备级证据。

### Perfetto 的正确用途

App 应为状态检查、下载、预热、推理请求、首分片和结束点增加自定义 trace。Perfetto 可以帮助对齐：

- App 主线程、工作线程和 RenderThread 调度；
- 帧时间、CPU frequency、GPU counter（设备支持时）；
- 内存计数器、PSI、lmkd 和 thermal 事件；
- 可见的 Binder 与系统服务活动。

Perfetto 中看到时间重叠只说明相关性。要证明某个资源竞争导致延迟，应配合关闭推理的对照组、重复实验和目标设备上的更细指标。

## 审查时常见的错误结论

| 错误写法 | 可验证的改写 |
|---|---|
| Android 17 设备都支持 Gemini Nano | Android 版本只是条件之一，以支持列表和运行时状态为准 |
| AICore 固定运行在某个进程名 | 进程名是设备实现细节，应用只依赖公开 API |
| 每次生成固定两次 Binder | IPC 形态和流式回调属于实现细节，不把次数写成契约 |
| AICore 一定走 NPU | 官方只保证使用设备硬件加速并隐藏底层接口 |
| App PSS 正常说明推理内存正常 | App PSS 只覆盖调用端，需结合相关组件和整机压力 |
| ADPF 可以调 AICore/NPU 频率 | App 的 hint session 只包含本进程线程 |
| 前台服务可以继续生成 | 当前 ML Kit GenAI 要求 App 是 top foreground |
| AppFunctions 由 AICore 提供推理 | AppFunctions 提供工具注册与调用协议，不规定模型运行时 |

## 与其他章节的关联

- **§5.10 端侧 AI 推理性能**：LiteRT、模型优化和设备后端的基础。
- **§5.11 移动端 LLM 推理的 DVFS 与能效边界**：prefill、decode 与持续负载测量。
- **§5.12 Android 17 ML Runtime 与 NPU 访问边界**：平台与厂商加速器边界。
- **§5.9 ADPF 自适应性能框架**：本进程工作线程的 hint session 用法。
- **§5.14 CPU Cache 友好代码与数据布局**：Cache 与内存统计的层级边界。
- **§4.4 Low Memory Killer**：lmkd、PSI 与进程状态。
- **§2.5 MainThread 与 RenderThread**：流式结果更新与帧时间。

## 参考资料

- [Gemini Nano 与 AICore 架构](https://developer.android.com/ai/gemini-nano)：AICore 的系统服务定位、隐私边界、Private Compute Services、模型管理与硬件加速。
- [ML Kit GenAI APIs 概览](https://developers.google.com/ml-kit/genai)：共享模型、设备支持、模型版本、配额和前台限制。
- [Prompt API Android 入门](https://developers.google.com/ml-kit/genai/prompt/android/get-started)：`FeatureStatus`、下载、生成、流式输出、`warmup()` 与输入限制。
- [LiteRT-LM Android Kotlin API](https://developers.google.com/edge/litert-lm/android)：`Engine`、后端选择、初始化、会话和资源关闭。
- [AppFunctions 概览](https://developer.android.com/ai/appfunctions)：Android 16+、实验状态、权限与工具协议边界。
- [PerformanceHintManager.java（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/os/PerformanceHintManager.java)：hint session 的线程归属和能效偏好。
- [PowerManager.java（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/base/core/java/android/os/PowerManager.java)：thermal status 与监听器。
