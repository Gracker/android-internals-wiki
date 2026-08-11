---
title: "Privacy Sandbox 退场与广告 SDK 启动治理"
chapter: "21.9"
section: "21.9"
status: ready-for-review
drafted_date: "2026-05-19"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1 AdServices and SDK sandbox APIs + Android Developers / Privacy Sandbox phaseout status"
confidence: medium
sources:
  - type: official
    path: "https://developers.google.com/privacy-sandbox/relevance/sdk-runtime/developer-guide"
  - type: official
    path: "https://privacysandbox.google.com/private-advertising/sdk-runtime/architecture"
  - type: official
    path: "https://developer.android.com/design-for-safety/privacy-sandbox/reference/sdksandbox/SdkSandboxManager"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime"
  - type: official
    path: "https://privacysandbox.google.com/overview/status"
  - type: official
    path: "https://privacysandbox.google.com/blog/update-on-plans-for-privacy-sandbox-technologies"
  - type: aosp
    path: "platform/prebuilts/fullsdk/sources/android-34/android/app/sdksandbox/SdkSandboxManager.java"
  - type: aosp
    path: "platform/prebuilts/fullsdk/sources/android-34/android/app/sdksandbox/SandboxedSdkProvider.java"
  - type: aosp
    path: "platform/prebuilts/fullsdk/sources/android-34/android/app/sdksandbox/SandboxedSdk.java"
  - type: aosp
    path: "packages/modules/AdServices/adservices/framework/java/android/adservices/topics/TopicsManager.java"
  - type: aosp
    path: "packages/modules/AdServices/adservices/framework/java/android/adservices/adselection/AdSelectionManager.java"
  - type: aosp
    path: "packages/modules/AdServices/adservices/framework/java/android/adservices/measurement/MeasurementManager.java"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md"
tags: [sdk-runtime, privacy-sandbox, startup, ads-sdk, ipc]
related_chapters: ["8.2", "21.1", "21.2", "21.6", "25.10", "26.3"]
last_consolidated_at: "2026-08-11"
consolidated_from:
  - "src/part2-performance/ch12-apk-network/07-privacy-sandbox-performance.md"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "官方文档/AOSP结构/每日信息"
gap_score: 16
material_count: 4
source_refs:
  - "https://developer.android.com/design-for-safety/privacy-sandbox/guides/sdk-runtime"
  - "https://developer.android.com/design-for-safety/privacy-sandbox/reference/sdksandbox/SdkSandboxManager"
  - "https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime"
  - "intake/daily-info/2026-05-19.md"
---

# Privacy Sandbox 退场与广告 SDK 启动治理

Privacy Sandbox on Android 的 Topics、Protected Audience、Attribution Reporting 与 SDK Runtime 都已进入退场过程。理解这段版本演进很重要，因为旧文章和设计页仍会展示 `getTopics()`、`selectAds()`、`registerSource()`、`SdkSandboxManager.loadSdk()` 与独立 sandbox 进程；面向 Android 17 的新代码却不能继续把它们当作可采用的平台方案。

讨论分为两部分：

- Android 14–16 遗留 SDK Runtime 的行为与迁移边界；
- Android 17 上普通嵌入式广告 SDK 的启动治理。

启动任务编排见[启动任务编排框架](./02-startup-framework.md)，Provider 自动初始化见[ContentProvider 启动优化](./03-contentprovider-optimization.md)，懒初始化见[延迟与懒初始化](./06-lazy-initialization.md)，多进程成本见[多进程启动优化](./07-multiprocess-startup.md)，指标设计见[启动监控与度量](./08-startup-monitoring.md)。

## 1. Android 17 版本结论

### 1.1 平台 API 已明确退场

Android 17 / API 37 的公开 API 文档对 `SdkSandboxManager`、`SandboxedSdkProvider` 和 `SandboxedSdk` 给出相同结论：这些类在 API 37 deprecated，SDK sandbox 不再受支持。

Android 17 的 `packages/modules/AdServices` 源码与公开文档一致：

- `SdkSandboxManager` 类带有 `@Deprecated` 和 SDK sandbox API deprecation flag；
- `SandboxedSdkProvider` 与 `SandboxedSdk` 同样 deprecated；
- `sandbox_app_flags.aconfig` 定义 `sdk_sandbox_no_op_impl` 和 `sdk_sandbox_api_deprecation`；
- `loadSdk()` 的 no-op 分支会在传入的 Executor 上回调 `LoadSdkException(LOAD_SDK_SDK_SANDBOX_DISABLED, ...)`。

API 符号仍然存在，但不能据此推断能力可用。`SDK_INT >= 34` 也不能作为接入判断。Android 17 新项目不应围绕 `SdkSandboxManager`、runtime-enabled SDK bundle 或旧 sandbox 生命周期构建广告架构。

### 1.2 其他 AdServices API 也不能作为新依赖

Google 在 2025 年 10 月 17 日公告退役 Privacy Sandbox on Android 相关技术，官方状态页将 Topics、Protected Audience、Attribution Reporting、SDK Runtime 等能力标记为计划逐步退出，但没有给出统一的 Android 移除版本。源码存在、manager 可获取或旧接入文档仍在线，都不能单独证明能力可用于新业务。

Android 17 Framework 的边界更具体：

| 能力 | Android 17 行为 | 迁移判断 |
| --- | --- | --- |
| Topics | `TopicsManager` 已废弃，服务结果会被转换为废弃异常 | 停止新查询，不再为它预热服务进程 |
| Ad Selection / Custom Audience | manager 已废弃，选取、加入等入口返回废弃错误 | 移除竞价与 audience 维护依赖 |
| Attribution Measurement | `MeasurementManager` 已废弃，但仍处于 soft removal，不能概括成所有设备立即失败 | 停止新集成；把当前成功视作迁移窗口而非长期合同 |
| SDK Runtime | API 37 deprecated，官方说明 sandbox 不再受支持 | Android 17 明确关闭平台路径 |

旧 Topics epoch、竞价 JavaScript、registration URI 网络获取和延迟报告只用于解释遗留流量。它们不再构成需要继续优化的 Android 17 热路径。Privacy Sandbox 退场也没有自动扩大 GAID、App Set ID 或第一方标识的用途；替代方案仍需重新通过隐私、政策、安全和性能评审。

### 1.3 版本表

| 系统 / 工具 | 状态 | 工程决策 |
| --- | --- | --- |
| Android 14–16 / API 34–36 | 平台 SDK Runtime 的历史支持区间，设备状态与 Ad Services 扩展仍可能影响可用性 | 只维护已发布产品，必须做能力探测和失败降级 |
| Android 17 / API 37 | 平台 API deprecated，官方说明 SDK sandbox 不再受支持 | 停止新接入；遗留代码在 API 37 明确关闭 |
| AndroidX `privacysandbox-sdkruntime` | `1.0.0-alpha19` 已 deprecated，release note 说明不再更新 | 不作为 Android 17 替代方案；现有使用方制定移除计划 |
| 普通嵌入式广告 SDK | 继续运行在宿主应用进程，除非 SDK 自己采用其他受支持的进程模型 | 按 Provider、Application、线程、I/O、内存和隐私契约治理 |

Privacy Sandbox 的 SDK Runtime architecture 与 developer guide 仍可用于理解 Android 14–16 的设计，但页面也标注设计提案可能变化。判断 Android 17 当前能力时，以 API 37 deprecation、AndroidX release note 和 `android-17.0.0_r1` 源码为准。

## 2. Android 14–16 的历史行为

这一节只服务于维护旧设备和迁移遗留代码。Android 17 不再走这条路径。

### 2.1 `loadSdk()` 做了什么

在历史实现中，应用调用：

```text
App process
  -> SdkSandboxManager.loadSdk(name, params, executor, receiver)
  -> system_server / SDK sandbox service
  -> 为该 App 创建或复用 SDK sandbox process
  -> SandboxedSdkProvider.onLoadSdk(params)
  -> 返回 SandboxedSdk(IBinder)
  -> App 通过 Binder 调用 SDK 接口
```

这条链路包含进程创建、SDK 代码加载、Provider 准备和 Binder 回调。`loadSdk()` 是异步 API，不代表工作没有成本；调用方若在首帧前等待 receiver，仍会把 sandbox 冷启动带回主路径。

历史 API 还有这些边界：

- 第一个 SDK 触发该 App 的 sandbox 进程创建，后续 SDK 可以复用同一 sandbox；
- `loadSdk()` 只允许前台调用，后台调用通过 receiver 返回失败；
- `SandboxedSdkProvider.onLoadSdk()` 只应完成“能够处理后续请求”的准备，不应做长时间 I/O、网络或依赖其他 SDK 已加载的初始化；
- sandbox 死亡后，已加载 SDK、Binder 与远程 UI 状态都会丢失，客户端需要监听死亡并重新建立状态；
- `SandboxedSdk.getInterface()` 返回 Binder，事务仍要处理线程安全、死亡、超时和大 payload。

### 2.2 SharedPreferences 同步不是共享内存

历史 `addSyncedSharedPreferencesKeys()` 只同步应用默认 `SharedPreferences` 中显式登记的 key。源码注明：

- App 重启后需要重新登记同步 key；
- 同一应用不能从多个进程共同使用这套同步管理；
- 移除 key 后，已经同步到 sandbox 的对应值会被删除。

同步适合少量稳定标量，不适合复制整份业务配置。每个 key 都应有数据所有者、默认值、版本与隐私用途。高频状态通过粗粒度接口传递；大对象使用文件描述符或受支持的数据通道，避免在 Binder 与 `Bundle` 中反复复制。

### 2.3 遗留能力探测

维护 Android 14–16 时，能力判断需要同时约束系统版本和 sandbox 状态。下面的代码只用于现有迁移层，编译到 API 37 时会看到 deprecated，因此用局部 suppress 标明技术债：

```kotlin
@Suppress("DEPRECATION")
fun canUseLegacyPlatformSdkSandbox(): Boolean {
    if (Build.VERSION.SDK_INT !in 34..36) {
        return false
    }

    return SdkSandboxManager.getSdkSandboxState() ==
        SdkSandboxManager.SDK_SANDBOX_STATE_ENABLED_PROCESS_ISOLATION
}
```

返回 `false` 只表示平台 sandbox 路径不可用，不等于可以在主线程同步加载旧广告 SDK。是否存在嵌入式版本、功能是否应关闭、能否延后加载，要由广告网关的显式策略决定。API 37 直接返回 `false`，不再尝试 deprecated `loadSdk()`。

### 2.4 AndroidX compat 的历史语义

旧版 backcompat 方案通过 `SdkSandboxManagerCompat` 统一接口。在没有平台 Runtime 的设备上，构建工具把 SDK 放入应用 APK 变体，客户端库从 assets 提取 DEX，并用独立 ClassLoader 在应用进程加载。

这里的“兼容”不等于平台隔离：

- 代码仍在应用进程内执行；
- 独立 ClassLoader 能减少类名冲突，不能提供独立 Linux 进程、UID 或内存空间；
- 首次提取 DEX、类加载和资源处理会增加存储与启动成本；
- Binder 形式的接口可以保持调用形状，却不一定发生跨进程事务；
- AndroidX 该库已经 deprecated，不能负责面向 Android 17 的长期抽象。

现有产品若仍依赖 alpha19，应固定版本、保留兼容测试，并与 SDK/广告供应方确认替代交付。不要仅把 `SdkSandboxManagerCompat` 改名封装后继续扩展新功能。

## 3. Android 17 上的广告 SDK 启动模型

SDK Runtime 退场后，广告 SDK 常见形态回到宿主进程中的 AAR、动态特性或 SDK 自有受支持组件。启动治理的起点是 merged manifest 和依赖产物，不是 `Application` 里能看到的几行初始化代码。

### 3.1 建立 SDK 清单

每次 SDK 升级至少记录：

| 维度 | 检查项 |
| --- | --- |
| 依赖 | 直接/传递 AAR、版本、变体、native 库与方法数 |
| manifest | Provider、Service、Receiver、Activity、metadata、进程名与 exported |
| 自动初始化 | Provider、AndroidX App Startup initializer、ContentProvider authority |
| 线程 | 启动线程、线程池大小、HandlerThread、定时任务 |
| I/O | SharedPreferences、数据库、缓存目录、文件扫描与 native 库加载 |
| 网络 | 首个请求触发点、DNS/TLS、配置与素材预取 |
| 内存 | Java/native heap、Bitmap、WebView、线程栈与主/远程进程 PSS |
| 生命周期 | 初始化幂等、Activity Context 引用、前后台切换、进程重建 |
| 数据 | 读取字段、同意状态、上传时机、保留与删除策略 |
| 控制 | owner、灰度开关、关闭广告位和回滚 SDK 的路径 |

SDK 文档声称“异步初始化”也要在 trace 中验证。异步 API 可能在调用前同步做类加载、manifest 查询、Preferences 读取和线程创建；回调线程也可能是主线程。

### 3.2 把广告能力拆成阶段

| 阶段 | 允许的工作 | 禁止依赖 |
| --- | --- | --- |
| 进程绑定 / Provider | 仅保留 SDK 强制且无法关闭的最小工作，并测量成本 | 网络、缓存扫描、大对象、广告素材 |
| `Application.onCreate()` | 注册轻量网关、读取已验证的本地功能开关 | 等待广告 SDK ready、首次广告请求 |
| 首帧前 | 页面是否保留广告容器的本地决策 | SDK 冷初始化、远程配置、广告返回 |
| 首帧后 | 设备和产品允许时触发初始化 | 无上限并发、立即抢占主/渲染线程 |
| 临近广告入口 | 初始化、请求、素材准备 | 阻塞页面主线程 |
| 广告位可见 | 展示已 ready 内容，或按产品规则占位/跳过 | 同步 fallback 初始化 |

“首帧后”仍可能影响 TTFD 和第一段交互。低端设备、首屏动画或 Compose 首次稳定期间，应延迟到明确空闲窗口或临近广告入口，并用实验确认首个广告可用率与启动体验的取舍。

### 3.3 用状态机管理一次会话的初始化

页面不应各自调用 SDK init。广告网关持有应用级状态，合并并发请求，并把失败变成可观察结果。

下面的示例把一次会话的初始化共享成同一个 `Deferred`。它不假设 SDK 可在后台线程初始化，具体 `initializer` 必须遵守供应方要求并切到正确线程：

```kotlin
sealed interface AdSdkState {
    data object Idle : AdSdkState
    data object Initializing : AdSdkState
    data class Ready(val client: AdClient) : AdSdkState
    data class Failed(val cause: Throwable) : AdSdkState
}

class AdSdkGateway(
    private val appScope: CoroutineScope,
    private val initializer: suspend () -> AdClient,
) {
    private val mutex = Mutex()
    private var inFlight: Deferred<Result<AdClient>>? = null

    private val _state =
        MutableStateFlow<AdSdkState>(AdSdkState.Idle)
    val state: StateFlow<AdSdkState> = _state.asStateFlow()

    suspend fun start(): Deferred<Result<AdClient>> =
        mutex.withLock {
            inFlight?.let { return@withLock it }

            appScope.async {
                _state.value = AdSdkState.Initializing
                runCatching { initializer() }
                    .also { result ->
                        _state.value = result.fold(
                            onSuccess = AdSdkState::Ready,
                            onFailure = AdSdkState::Failed,
                        )
                    }
            }.also { inFlight = it }
        }

    suspend fun awaitReady(
        timeoutMillis: Long,
    ): Result<AdClient>? =
        withTimeoutOrNull(timeoutMillis) {
            start().await()
        }
}
```

`appScope` 应由应用生命周期管理，并使用 `SupervisorJob` 避免一次 SDK 失败取消无关任务。调用方等待超时后返回 `null`，共享初始化仍可继续；如果产品需要取消，SDK 必须提供可验证的取消协议。示例把失败保持为会话级状态，重试应由显式退避策略重置，不能由多个页面循环触发。

若供应方要求主线程调用 init，`initializer` 可以只在主线程提交轻量入口，重工作是否异步仍由 trace 验证。把整个 gateway 放到 `Dispatchers.IO` 不能强迫封闭 SDK 遵守线程约束。

## 4. 首屏广告怎样取舍

首屏广告、App Open 广告或首页首个广告位会把收入目标与启动体验放在同一路径上。技术方案需要产品先确定缺省行为：

- SDK 未 ready 时跳过本次广告；
- 展示固定尺寸占位，内容 ready 后再填充；
- 等待一个很短的业务 deadline，超时立即进入页面；
- 广告是业务入口本身时，使用独立的可取消 loading，并把等待计入 TTFD/业务 ready。

不能使用无限 loading 等广告，也不能在新路径失败后立即回到主线程执行旧 SDK 同步 init。失败回退如果比主路径更重，会让少量错误样本成为 P99、ANR 和差评来源。

广告容器还要避免布局跳动。预留尺寸时使用产品确定的广告规格；跳过广告时及时移除占位。远程素材到达后触发布局与图片解码，应进入首屏 frame 和内存 guardrail。

## 5. Provider 与多进程边界

### 5.1 自动初始化发生在 `Application` 之前

广告 SDK 通过 Provider 自动初始化时，`Application.onCreate()` 里的进程分支和延迟开关已经来不及阻止 Provider `onCreate()`。检查最终 merged manifest：

- SDK 是否支持移除 Provider metadata 或切换手动初始化；
- Provider 属于主进程还是指定远程进程；
- authority 是否稳定且不冲突；
- App Startup initializer 是否仍由依赖库合并回来；
- 升级 SDK 后 manifest diff 是否新增组件。

移除自动初始化必须按供应方支持方式操作，不能直接删 Provider 后假设 SDK 仍可用。修改后要覆盖冷启动、通知/deep link、配置变更、进程重建和所有广告入口。

### 5.2 放进自有远程进程不等于 SDK Runtime

把广告 Service 或宿主组件声明到 `android:process=":ads"`，得到的是应用私有远程进程：

- 通常仍使用应用 UID 与权限；
- SDK 能否在该进程工作取决于 SDK 自身实现与许可；
- UI、Activity Context 和 WebView 可能要求主进程交互；
- Binder、进程冷启动、独立堆和死亡恢复都由应用负责；
- Provider 只在其所属进程安装，但 `Application` 会在该进程创建。

这与历史 SDK sandbox 的独立 UID、受控 API 和 SDK package 模型不同。没有供应方明确支持和完整测试时，不要强行把封闭广告 SDK 移到远程进程。

## 6. 失败与回退策略

| 失败 | 会话策略 | 启动约束 |
| --- | --- | --- |
| Android 17 平台 sandbox 不受支持 | 不调用 deprecated load；使用受支持的嵌入式 SDK 或关闭能力 | 不尝试循环探测 |
| Android 14–16 sandbox disabled | 标记遗留平台路径不可用 | 不在首帧前重试 |
| 普通 SDK init 超时 | 页面占位、跳过或使用产品允许的其他广告源 | 等待方超时不等于 init 已取消 |
| SDK init 抛错 | 会话级 Failed，按退避与错误类型决定重试 | 禁止主线程同步 fallback |
| SDK 进程/Binder 死亡 | 清理代理，遗留路径按可见页面需求恢复 | 重连与业务请求分开计时 |
| 配置或 SDK 缺失 | 关闭对应广告源并上报构建/配置错误 | 用户路径不负责下载修复 |
| 同意状态未满足 | 不发起受限制的初始化或请求，按产品合规策略展示 | 不用旧缓存绕过状态 |

业务页面只依赖 `Disabled / Idle / Initializing / Ready / Failed`，不直接认识某家 SDK 的错误码。网关保留原始错误码供诊断，再映射成稳定的业务分类。

## 7. 观测与验收

### 7.1 时间线

至少记录这些单调时间戳：

| 事件 | 解释 |
| --- | --- |
| `ad_gateway_trigger` | 哪个页面/策略决定开始初始化 |
| `ad_sdk_init_call` | 进入供应方 API 前 |
| `ad_sdk_init_callback` | 成功或失败回调 |
| `ad_first_request_call` | 第一个广告请求 |
| `ad_first_response` | 填充、无填充或错误 |
| `ad_first_render_ready` | 素材达到可提交 UI 的状态 |
| `ad_first_impression` | 按供应方定义产生曝光 |

这些事件与 TTID、TTFD、首屏 frame、首个操作放在同一 session timeline。回调耗时、广告请求耗时和渲染耗时不能合并成一个 `ad_ready` 数字，否则无法判断瓶颈在 SDK init、网络还是 UI。

### 7.2 资源与稳定性

| 维度 | 指标 |
| --- | --- |
| 主线程 | init 调用同步耗时、首帧前 Binder/I/O、长 task |
| CPU | App/远程进程 CPU 时间、Runnable 竞争、初始化线程数 |
| 内存 | 主进程与远程进程 PSS、Java/native heap、WebView/Bitmap 峰值 |
| 帧 | TTID 后首屏 slow/frozen frame、广告填充时布局和解码 |
| 稳定性 | init 错误、超时、ANR、Crash、Binder death、重试次数 |
| 业务 | 广告 ready、填充、展示、跳过、占位时长与首个广告可用率 |
| 数据质量 | 采样率、回调缺失、会话终止、SDK/配置版本 |

主进程 PSS 下降不能单独证明资源改善。若采用供应方支持的远程进程，应同时看进程合计 PSS；多个进程 RSS 直接相加会重复计算共享页。

### 7.3 A/B 条件

广告初始化实验至少固定：

- 相同 App 与 SDK 版本；
- 相同同意状态、广告位和服务端配置；
- cold/warm/hot、安装状态与入口；
- 设备档位、Android 版本和渠道；
- 相同超时、占位和跳过策略。

实验同时观察启动、稳定性和广告业务 guardrail。首帧变快但广告填充骤降，或收入改善但 ANR/P99 上升，都需要产品与技术共同决定，不由单一指标自动判定。

## 8. 迁移清单

### 从旧 Privacy Sandbox 业务 API 退出

- [ ] 搜索 `TopicsManager`、`AdSelectionManager`、`CustomAudienceManager` 与 `MeasurementManager` 的调用点、权限、配置和依赖。
- [ ] 用远程开关停止新请求，页面布局和广告填充不再等待这些结果。
- [ ] 区分 deprecated、unsupported、disabled、security、rate limit、网络错误与调用方本地超时；永久废弃错误不进入重试队列。
- [ ] 盘点 registration、bidding、trusted-data 与 reporting endpoint 的剩余流量，确认旧后台任务和数据库记录的删除边界。
- [ ] 只记录受控的 feature、call-site、平台/extension 版本、结果分类、端到端时间和 fallback；不上传 topic、audience、竞价信号或完整 registration URI。
- [ ] 替代广告、归因和标识方案分别完成合规评审，不把 GAID 当作默认回退。

### 从 Android 14–16 SDK Runtime 迁移到 Android 17

- [ ] 搜索 `SdkSandboxManager`、`SandboxedSdkProvider`、`SandboxedSdk` 和 `*Compat` 使用点。
- [ ] 记录 runtime-enabled SDK、ASB、manifest `<uses-sdk-library>` 与商店交付依赖。
- [ ] API 37 明确关闭平台 sandbox 路径，不仅检查类是否存在。
- [ ] 删除 `loadSdk()` 的首帧前等待和同步 fallback。
- [ ] 与 SDK 供应方确认 Android 17 支持的嵌入式/替代版本。
- [ ] 移除或冻结 deprecated AndroidX alpha19，验证构建产物不再携带无用 DEX/assets。
- [ ] 把 Binder DTO 转换为当前 SDK 接口时，保留版本和错误映射。
- [ ] 对比 merged manifest，确认替代 SDK 新增的 Provider 和组件。
- [ ] 灰度观察 TTID、TTFD、frame、ANR/Crash、PSS 和广告 guardrail。
- [ ] 为旧 Android 14–16 用户保留受控迁移窗口和可回滚版本。

### Android 17 广告 SDK 启动检查清单

- [ ] merged manifest 与传递依赖已经纳入检查。
- [ ] 自动初始化可以关闭时，使用供应方支持的手动路径。
- [ ] `Application` 只注册轻量网关，不等待 SDK ready。
- [ ] 页面并发 init 被合并成一个会话任务。
- [ ] SDK 要求的调用线程已按对应版本的官方文档验证。
- [ ] 首帧后初始化经过低端设备 CPU/帧竞争验证。
- [ ] timeout、取消、重试和会话级失败语义清楚。
- [ ] 失败不会触发主线程同步旧 SDK fallback。
- [ ] UI 占位、跳过和布局变化有产品规则。
- [ ] 数据、同意状态和上传时机有显式契约。
- [ ] 主进程与任何远程进程资源合并统计。
- [ ] SDK 升级有版本、owner、灰度开关和回滚产物。

## 小结

Android 17 已终止 SDK sandbox 的平台支持，旧的 `loadSdk()` 启动隔离方案只能作为 Android 14–16 遗留知识维护。API 37 新代码应停止探测和调用 deprecated 平台路径，AndroidX backcompat 也不能接替长期维护职责。

广告 SDK 的启动问题随之回到更基础的工程边界：看 merged manifest，控制 Provider 和 Application 工作，合并并发初始化，明确首帧/TTFD/广告 ready 的关系，处理失败与重试，并把主线程、帧、内存、稳定性和广告指标放在同一次实验中。隔离能力退场不影响这些原则，它只要求团队重新选择受支持的 SDK 交付和运行方式。

## 参考资料

- [Android 17 `SdkSandboxManager.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/framework/java/android/app/sdksandbox/SdkSandboxManager.java)：API 37 deprecation 与 no-op `loadSdk()` 路径。
- [Android 17 `SandboxedSdkProvider.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/framework/java/android/app/sdksandbox/SandboxedSdkProvider.java)：Provider deprecation 与历史 `onLoadSdk()` 边界。
- [Android 17 SDK sandbox flags](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/flags/sandbox_app_flags.aconfig)：no-op 与 API deprecation flag。
- [`SdkSandboxManager` API reference](https://developer.android.com/reference/android/app/sdksandbox/SdkSandboxManager)：API 37 deprecated 和“不再受支持”的公开说明。
- [`SandboxedSdkProvider` API reference](https://developer.android.com/reference/android/app/sdksandbox/SandboxedSdkProvider)：历史加载约束与 API 37 deprecation。
- [SDK Runtime overview](https://privacysandbox.google.com/private-advertising/sdk-runtime/architecture)：Android 14–16 设计目标、进程与通信模型。
- [SDK Runtime backward compatibility](https://privacysandbox.google.com/private-advertising/sdk-runtime/backward-compatibility)：旧版 in-app ClassLoader 兼容模型。
- [AndroidX Privacy Sandbox SDK Runtime releases](https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime)：alpha19 deprecation 与停止更新说明。
