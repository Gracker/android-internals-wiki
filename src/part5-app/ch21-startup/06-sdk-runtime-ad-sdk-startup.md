---
title: Privacy Sandbox 退场与广告 SDK 启动治理
chapter: '21.6'
section: '21.6'
status: finalized
applicable_versions: Android 13 (API 33) - Android 17 (API 37)
last_verified: '2026-08-14'
last_verified_against: AOSP android-17.0.0_r1 SDK sandbox, Topics, Ad Selection, Custom Audience and Measurement sources; current Android API 37, Privacy Sandbox phaseout, SDK Runtime compatibility and AndroidX alpha19 release docs
confidence: high
sources:
- type: official
  path: https://developers.google.com/privacy-sandbox/relevance/sdk-runtime/developer-guide
- type: official
  path: https://privacysandbox.google.com/private-advertising/sdk-runtime/architecture
- type: official
  path: https://developer.android.com/design-for-safety/privacy-sandbox/reference/sdksandbox/SdkSandboxManager
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime
- type: official
  path: https://privacysandbox.google.com/overview/status
- type: official
  path: https://privacysandbox.google.com/blog/update-on-plans-for-privacy-sandbox-technologies
- type: aosp
  path: platform/prebuilts/fullsdk/sources/android-34/android/app/sdksandbox/SdkSandboxManager.java
- type: aosp
  path: platform/prebuilts/fullsdk/sources/android-34/android/app/sdksandbox/SandboxedSdkProvider.java
- type: aosp
  path: platform/prebuilts/fullsdk/sources/android-34/android/app/sdksandbox/SandboxedSdk.java
- type: aosp
  path: packages/modules/AdServices/adservices/framework/java/android/adservices/topics/TopicsManager.java
- type: aosp
  path: packages/modules/AdServices/adservices/framework/java/android/adservices/adselection/AdSelectionManager.java
- type: aosp
  path: packages/modules/AdServices/adservices/framework/java/android/adservices/measurement/MeasurementManager.java
- type: clippings-structure
  path: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md
- type: clippings-structure
  path: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md
- type: clippings-structure
  path: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md
- type: clippings-structure
  path: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md
tags:
- sdk-runtime
- privacy-sandbox
- startup
- ads-sdk
- ipc
related_chapters:
- '8.2'
- '21.1'
- '21.2'
- '25.8'
- '26.1'
pipeline_stage: finalized
last_consolidated_at: '2026-08-11'
consolidated_from:
- src/part2-performance/ch12-apk-network/07-privacy-sandbox-performance.md
---

# Privacy Sandbox 退场与广告 SDK 启动治理

Privacy Sandbox on Android 是一组曾用于隐私广告与第三方 SDK 隔离的平台技术。其中 Topics 用于提供粗粒度兴趣主题，Protected Audience 用于设备端广告受众和选取，Attribution Reporting 用于广告归因，SDK Runtime 用独立进程承载适配后的 SDK。Google 已决定让这四项技术退出。旧文章和设计页仍会展示 `getTopics()`、`selectAds()`、`registerSource()`、`SdkSandboxManager.loadSdk()` 与独立 sandbox（隔离运行环境）进程，但面向 Android 17 的新代码不能继续把它们当作可采用的平台方案。

讨论分为两部分：

- Android 14–16 遗留 SDK Runtime 的行为与迁移边界；
- Android 17 上普通嵌入式广告 SDK 的启动治理。

启动任务编排见 [启动任务编排框架](02-startup-task-lazy-concurrency.md)，Provider 自动初始化见 [ContentProvider 启动优化](03-contentprovider-multiprocess-startup.md)，懒初始化见 [延迟与懒初始化](02-startup-task-lazy-concurrency.md)，多进程成本见 [多进程启动优化](03-contentprovider-multiprocess-startup.md)，指标设计见 [启动监控与度量](01-app-startup-path-monitoring.md)。

## 1. Android 17 版本结论

### 1.1 平台 API 已明确退场

Android 17 / API 37 的公开 API 文档对 `SdkSandboxManager`、`SandboxedSdkProvider` 和 `SandboxedSdk` 给出相同结论：这些类在 API 37 deprecated（已废弃，不应再用于新代码），SDK sandbox 不再受支持。

Android 17 的 `packages/modules/AdServices` 源码与公开文档一致：

- `SdkSandboxManager` 类带有 `@Deprecated`，并受 SDK sandbox API deprecation feature flag（控制功能是否启用的系统开关）约束；
- `SandboxedSdkProvider` 与 `SandboxedSdk` 同样 deprecated；
- `sandbox_app_flags.aconfig` 定义 `sdk_sandbox_no_op_impl` 和 `sdk_sandbox_api_deprecation`；
- `loadSdk()` 的 no-op（不执行实际加载）分支会在传入的 Executor（指定回调执行线程的调度接口）上返回 `LoadSdkException(LOAD_SDK_SDK_SANDBOX_DISABLED, ...)`。

API 符号仍然存在，只能说明代码可以编译，不能证明设备上的能力可用。`SDK_INT >= 34` 也不能作为接入判断。Android 17 新项目不应围绕 `SdkSandboxManager`、runtime-enabled SDK（为 SDK Runtime 改造的 SDK）交付包或旧 sandbox 生命周期构建广告架构。

### 1.2 其他 AdServices API 也不能作为新依赖

Google 在 2025 年 10 月 17 日公告退役相关技术，官方状态页把 Android 上的 Topics、Protected Audience、Attribution Reporting、SDK Runtime 等能力列为“Deprecate and remove”，但没有给出一个适用于所有能力的 Android 移除版本。源码存在、manager 对象可以取得或旧接入文档仍在线，都不能单独证明能力可用于新业务。

Android 17 Framework 的边界更具体：

| 能力 | Android 17 行为 | 迁移判断 |
| --- | --- | --- |
| Topics | `TopicsManager` 已废弃；Android 17 客户端无论服务返回成功或失败，都会向调用方返回废弃异常 | 停止新查询，不再为它提前启动服务进程 |
| Ad Selection / Custom Audience | 两个 manager 均已废弃；广告选取、加入/离开受众等入口会把结果改写为废弃异常 | 移除设备端竞价与受众维护依赖 |
| Attribution Measurement | `MeasurementManager` 已废弃，但注释明确处于 soft removal（先废弃、随后分阶段拒绝调用） | 停止新集成；把当前仍能成功的调用视作迁移窗口，不视作长期保证 |
| SDK Runtime | API 37 deprecated，官方说明 sandbox 不再受支持 | Android 17 明确关闭平台路径 |

旧 Topics epoch（平台定期更新主题的一段时间）、竞价 JavaScript、registration URI（注册端点地址）网络获取和延迟报告只用于解释遗留流量。它们不再构成需要继续优化的 Android 17 高频启动路径。Privacy Sandbox 退场也没有自动扩大 GAID（Google Advertising ID，广告标识符）、App Set ID（同一开发者应用集合标识）或第一方标识的用途；替代方案仍需重新通过隐私、政策、安全和性能评审。

### 1.3 版本表

| 系统 / 工具 | 状态 | 工程决策 |
| --- | --- | --- |
| Android 13 / API 33 | 加入 `SdkSandboxManager` 与状态查询；平台 `loadSdk()` 尚未加入 | 只用于识别旧 API 表面与兼容层，不视作平台 SDK 加载能力 |
| Android 14–16 / API 34–36 | 平台 `loadSdk()` 的历史支持区间；设备状态与可独立更新的 Ad Services 扩展版本仍会影响可用性 | 只维护已发布产品，必须检查能力并准备失败降级 |
| Android 17 / API 37 | 平台 API deprecated，官方说明 SDK sandbox 不再受支持 | 停止新接入；遗留代码在 API 37 明确关闭 |
| AndroidX `privacysandbox-sdkruntime` | 预发布版 `1.0.0-alpha19` 已 deprecated，release note 说明不会再更新 | 不作为 Android 17 替代方案；现有使用方制定移除计划 |
| 普通嵌入式广告 SDK | 通常随 AAR（Android 库归档）放入宿主 App 进程，除非 SDK 自己提供其他受支持的进程模型 | 按 Provider、Application、线程、I/O、内存和隐私约定治理 |

Privacy Sandbox 的 SDK Runtime architecture 与 developer guide 仍可用于理解 Android 14–16 的设计，但页面也注明内容属于可能变化的设计提案。判断 Android 17 当前能力时，以 API 37 的废弃说明、AndroidX release note（版本说明）和 `android-17.0.0_r1` 源码为准。

## 2. Android 14–16 的历史行为

这一节只服务于维护旧设备和迁移遗留代码。Android 17 不再走这条路径。

### 2.1 `loadSdk()` 做了什么

在历史实现中，App 的调用链如下。`system_server` 是承载 Android 核心系统服务的进程，SDK sandbox process 是为当前 App 创建的隔离进程，`IBinder` 是跨进程接口句柄：

```text
App process
  -> SdkSandboxManager.loadSdk(name, params, executor, receiver)
  -> system_server / SDK sandbox service
  -> 为该 App 创建或复用 SDK sandbox process
  -> SandboxedSdkProvider.onLoadSdk(params)
  -> 返回 SandboxedSdk(IBinder)
  -> App 通过 Binder 调用 SDK 接口
```

这条链路包含进程创建、SDK 代码加载、Provider 准备和 Binder（Android 进程间通信机制）回调。`loadSdk()` 是异步 API，只表示结果稍后通过 receiver（结果接收回调）返回，并不表示工作没有成本；调用方若在首帧前等待 receiver，仍会让页面等待 sandbox 冷启动。

历史 API 还有这些边界：

- 第一个 SDK 触发该 App 的 sandbox 进程创建，后续 SDK 可以复用同一 sandbox；
- `loadSdk()` 只允许前台调用，后台调用通过 receiver 返回失败；
- `SandboxedSdkProvider.onLoadSdk()` 只应完成“能够处理后续请求”的准备，不应做长时间 I/O、网络或依赖其他 SDK 已加载的初始化；
- sandbox 死亡后，已加载 SDK、Binder 与远程 UI 状态都会丢失，客户端需要监听死亡并重新建立状态；
- `SandboxedSdk.getInterface()` 返回 Binder，事务仍要处理线程安全、远程进程死亡、超时和大 payload（一次调用携带的大量数据）。

### 2.2 SharedPreferences 同步不是共享内存

历史 `addSyncedSharedPreferencesKeys()` 只同步 App 默认 `SharedPreferences`（持久化少量键值配置的 API）中显式登记的 key。官方 API 文档注明：

- App 重启后需要重新登记同步 key；
- 同一应用不能从多个进程共同使用这套同步管理；
- 移除 key 后，已经同步到 sandbox 的对应值会被删除。

同步适合少量稳定标量，也就是字符串、数字、布尔值这类单个值，不适合复制整份业务配置。每个 key 都应有数据所有者、默认值、版本与隐私用途。高频状态通过一次携带完整业务含义的接口传递；大对象使用文件描述符或受支持的数据通道，避免在 Binder 与 `Bundle` 中反复复制。

### 2.3 遗留能力探测

维护 Android 14–16 时，能力判断需要同时约束系统版本和 sandbox 状态。下面的代码只用于现有迁移层；面向 API 37 编译时会产生 deprecated 警告，因此用局部 `Suppress` 抑制警告，并把这处仍需移除的兼容代码明确标成技术债：

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

返回 `false` 只表示平台 sandbox 路径不可用，不等于可以在主线程同步加载旧广告 SDK。是否存在嵌入式版本、功能是否应关闭、能否延后加载，要由广告网关（业务页面与各家广告 SDK 之间的统一接口）的明确策略决定。API 37 直接返回 `false`，不再尝试 deprecated `loadSdk()`。

### 2.4 AndroidX compat 的历史语义

旧版 backcompat（向后兼容）方案通过 `SdkSandboxManagerCompat` 统一接口。在没有平台 Runtime 的设备上，Android Gradle Plugin 与 Bundletool 会生成包含 SDK 的 APK 变体，把 SDK 的 DEX（Android 字节码文件）作为 assets（随包资源）保存；客户端库首次加载时把 DEX 提取到 `code_cache`，再用独立 ClassLoader（类加载器）放进 App 进程执行。

这里的“兼容”不等于平台隔离：

- 代码仍在应用进程内执行；
- 独立 ClassLoader 能减少类名冲突，但它不是安全隔离边界，不能提供独立 Linux 进程、UID 或内存空间；
- 首次提取 DEX、类加载和资源处理会增加存储与启动成本；
- Binder 形式的接口可以保持同一种调用接口，但 bundled SDK（随 App 打包的 SDK）位于本进程时，不一定发生跨进程事务；
- AndroidX 该库已经 deprecated，不能负责面向 Android 17 的长期抽象。

现有产品若仍依赖 alpha19，应固定版本、保留兼容测试，并与 SDK/广告供应方确认替代交付。alpha 表示尚未稳定的预发布版本，既然该库已停止更新，就不应只给 `SdkSandboxManagerCompat` 换一层名字后继续扩展新功能。

## 3. Android 17 上的广告 SDK 启动模型

SDK Runtime 退场后，广告 SDK 常见形态回到宿主进程中的 AAR、dynamic feature（按需交付的动态功能模块）或 SDK 自己声明且受支持的 Android 组件。检查启动成本要从 merged manifest（App 与所有依赖合并后的最终清单）和实际构建产物开始，不能只看 `Application` 里的几行初始化代码。

### 3.1 建立 SDK 清单

每次 SDK 升级至少记录下表信息。这里的“传递依赖”指 SDK 间接带入的库，`exported` 表示组件能否被其他 App 调用，authority 是 ContentProvider 的唯一名称：

| 维度 | 检查项 |
| --- | --- |
| 依赖 | 直接/传递 AAR、版本、构建变体、native（C/C++）库与新增方法数 |
| Manifest | Provider、Service、Receiver、Activity、metadata（清单键值配置）、进程名与 `exported` |
| 自动初始化 | Provider、AndroidX App Startup initializer（初始化器）、ContentProvider authority |
| 线程 | 启动线程、线程池大小、HandlerThread（自带消息循环的工作线程）、定时任务 |
| I/O | SharedPreferences、数据库、缓存目录、文件扫描与 native 库加载 |
| 网络 | 首个请求触发点、DNS 域名解析、TLS 加密连接、配置与素材预取 |
| 内存 | Java/native heap（托管对象与 C/C++ 分配的堆内存）、Bitmap、WebView、线程栈与主/远程进程 PSS |
| 生命周期 | 初始化是否幂等（重复调用结果不变）、Activity Context 引用、前后台切换、进程重建 |
| 数据 | 读取字段、同意状态、上传时机、保留与删除策略 |
| 控制 | 负责人、分批放量开关、关闭广告位和回滚 SDK 的路径 |

SDK 文档声称“异步初始化”也要在 trace（系统时间线）中验证。异步 API 可能在返回前同步执行类加载、Manifest 查询、Preferences 读取和线程创建；完成回调也可能回到主线程。

### 3.2 把广告能力拆成阶段

| 阶段 | 允许的工作 | 禁止依赖 |
| --- | --- | --- |
| 进程绑定 / Provider | 仅保留 SDK 强制且无法关闭的最小工作，并测量成本 | 网络、缓存扫描、大对象、广告素材 |
| `Application.onCreate()` | 注册轻量网关、读取已验证的本地功能开关 | 等待广告 SDK ready、首次广告请求 |
| 首帧前 | 页面是否保留广告容器的本地决策 | SDK 冷初始化、远程配置、广告返回 |
| 首帧后 | 设备和产品允许时触发初始化 | 无上限并发、立即与主线程或渲染线程争用 CPU |
| 临近广告入口 | 初始化、请求、素材准备 | 阻塞页面主线程 |
| 广告位可见 | 展示已 ready 内容，或按产品规则占位/跳过 | 同步执行备用初始化路径 |

“首帧后”仍可能影响 TTFD（Time to Full Display，主要内容完整可用时间）和第一段交互。低端设备、首屏动画或 Jetpack Compose 首次生成并稳定 UI 的期间，应延迟到明确空闲窗口或临近广告入口，并用实验确认首个广告可用率与启动体验的取舍。

### 3.3 用状态机管理一次会话的初始化

页面不应各自调用 SDK init（初始化）。广告网关应持有 App 级状态，把同时到达的多次请求合并成同一个任务，并把失败保存为调用方可以读取的结果。

下面的状态机把初始化限制为 `Idle`（未开始）、`Initializing`（进行中）、`Ready`（可用）和 `Failed`（本次会话失败）。所有调用方共享同一个 `Deferred`，也就是稍后产生结果、可以被多个协程等待的对象。示例不假设 SDK 可在后台线程初始化，具体 `initializer` 必须遵守供应方要求并切到正确线程：

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

`appScope` 是由 App 生命周期管理的协程作用域，应使用 `SupervisorJob`，避免一个 SDK 子任务失败时取消同作用域的无关任务。调用方等待超时后返回 `null`，共享初始化仍可继续；如果产品需要取消，SDK 必须提供可验证的取消协议。示例把失败保持为本次进程会话的状态；若允许重试，应由网关按错误类型和逐次延长的等待间隔重置，不能由多个页面各自循环触发。

若供应方要求主线程调用 init，`initializer` 可以只在主线程提交轻量入口，后续重工作是否异步仍由 trace 验证。`Dispatchers.IO` 是 Kotlin 协程面向阻塞 I/O 的共享线程池；把整个 gateway 切到这里，也不能强迫看不到内部实现的 SDK 改变自己的线程行为。

## 4. 首屏广告怎样取舍

首屏广告、App Open（打开 App 时展示的）广告或首页首个广告位会让广告等待直接影响启动体验。技术方案需要产品先确定默认行为：

- SDK 未 ready 时跳过本次广告；
- 展示固定尺寸占位，内容 ready 后再填充；
- 等待一个很短的业务 deadline（最晚等待时刻），超时立即进入页面；
- 广告是业务入口本身时，使用独立且可取消的加载页，并把等待计入 TTFD/业务 ready（业务就绪时间）。

不能用无限加载页等待广告，也不能在新路径失败后立即回到主线程执行旧 SDK 的同步初始化。若备用路径比正常路径更重，少量错误样本就可能集中到 P99（99% 的样本不超过的耗时）、ANR（Application Not Responding，应用无响应）和用户差评中。

广告容器还要避免素材出现后让正文突然移位。预留尺寸时使用产品确定的广告规格；跳过广告时及时移除占位。远程素材到达后触发的布局和图片解码，应纳入首屏帧耗时与内存 guardrail（实验不可越过的保护指标）。

## 5. Provider 与多进程边界

### 5.1 自动初始化发生在 `Application` 之前

广告 SDK 通过 Provider 自动初始化时，`Application.onCreate()` 里的进程分支和延迟开关已经来不及阻止 Provider `onCreate()`。因此要检查最终 merged manifest：

- SDK 是否支持移除 Provider metadata 或切换手动初始化；
- Provider 属于主进程还是指定远程进程；
- authority 是否稳定且不冲突；
- App Startup initializer 是否仍由依赖库合并回来；
- 升级 SDK 后的 Manifest diff（前后差异）是否新增组件。

移除自动初始化必须按供应方支持方式操作，不能直接删 Provider 后假设 SDK 仍可用。修改后要覆盖冷启动、通知/deep link、配置变更、进程重建和所有广告入口。

### 5.2 放进自有远程进程不等于 SDK Runtime

把广告 Service 或宿主组件声明到 `android:process=":ads"`，得到的是 App 私有远程进程：

- 通常仍使用 App 的 UID（Linux 用户身份）与权限；
- SDK 能否在该进程工作取决于 SDK 自身实现与许可；
- UI、Activity Context（绑定 Activity 生命周期和主题的上下文）与 WebView 可能要求主进程交互；
- Binder 调用、远程进程冷启动、独立堆内存和进程死亡恢复都由 App 负责；
- Provider 只在其所属进程安装，但 `Application` 会在该进程创建。

这与历史 SDK sandbox 的独立 UID、受控 API 和独立 SDK package（安装包）模型不同。没有供应方明确支持和完整测试时，不要强行把内部实现不可见的广告 SDK 移到远程进程。

## 6. 失败与回退策略

| 失败 | 会话策略 | 启动约束 |
| --- | --- | --- |
| Android 17 平台 sandbox 不受支持 | 不调用 deprecated load；使用受支持的嵌入式 SDK 或关闭能力 | 不尝试循环探测 |
| Android 14–16 sandbox disabled | 标记遗留平台路径不可用 | 不在首帧前重试 |
| 普通 SDK init 超时 | 页面占位、跳过或使用产品允许的其他广告源 | 调用方停止等待，不等于后台初始化已取消 |
| SDK init 抛错 | 会话级 Failed，按逐次延长间隔的退避策略与错误类型决定重试 | 禁止主线程同步执行备用路径 |
| SDK 进程/Binder 死亡 | 清理已失效的远程接口，遗留路径按可见页面需求恢复 | 重连与业务请求分开计时 |
| 配置或 SDK 缺失 | 关闭对应广告源并上报构建/配置错误 | 用户路径不负责下载修复 |
| 同意状态未满足 | 不发起受限制的初始化或请求，按产品合规策略展示 | 不用旧缓存绕过状态 |

业务页面只依赖 `Disabled / Idle / Initializing / Ready / Failed` 这组稳定状态，不直接认识某家 SDK 的错误码。网关保留原始错误码供诊断，再映射成跨 SDK 都能理解的业务分类。

## 7. 观测与验收

### 7.1 时间线

至少记录下列单调时间戳。单调时钟只向前推进，不会受用户修改系统时间或网络校时影响，适合计算同一次启动内的耗时：

| 事件 | 解释 |
| --- | --- |
| `ad_gateway_trigger` | 哪个页面/策略决定开始初始化 |
| `ad_sdk_init_call` | 进入供应方 API 前 |
| `ad_sdk_init_callback` | 成功或失败回调 |
| `ad_first_request_call` | 第一个广告请求 |
| `ad_first_response` | 填充、无填充或错误 |
| `ad_first_render_ready` | 素材达到可提交 UI 的状态 |
| `ad_first_impression` | 按供应方定义产生一次广告曝光 |

这些事件与 TTID（首次显示时间）、TTFD、首屏 frame（UI 帧）和首个操作放在同一 session timeline（本次启动时间线）。初始化回调耗时、广告请求耗时和渲染耗时不能合并成一个 `ad_ready` 数字，否则无法判断慢在 SDK 初始化、网络还是 UI。

### 7.2 资源与稳定性

| 维度 | 指标 |
| --- | --- |
| 主线程 | init 调用同步耗时、首帧前 Binder/I/O、长时间占用线程的任务 |
| CPU | App/远程进程 CPU 时间、处于 Runnable（可运行、等待 CPU）状态的线程竞争、初始化线程数 |
| 内存 | 主进程与远程进程 PSS、Java/native heap、WebView/Bitmap 峰值 |
| 帧 | TTID 后首屏 slow/frozen frame（明显延迟或长时间停住的帧）、广告填充时布局和解码 |
| 稳定性 | init 错误、超时、ANR、Crash（崩溃）、Binder death（远程接口因进程退出而失效）、重试次数 |
| 业务 | 广告 ready、填充、展示、跳过、占位时长与首个广告可用率 |
| 数据质量 | 采样率、回调缺失、会话终止、SDK/配置版本 |

PSS（Proportional Set Size）会按比例分摊进程间共享的内存页，RSS（Resident Set Size）则把每个进程驻留的共享页都计入。主进程 PSS 下降不能单独证明整体内存改善；若采用供应方支持的远程进程，应看各进程合计 PSS，不能直接相加 RSS，否则共享页会被重复计算。

### 7.3 A/B 条件

A/B 实验是把条件相同的用户随机分到基准组与改动组进行对比。这里的 cold 表示需要创建 App 进程，warm 表示保留部分状态但仍需重建一部分启动路径，hot 表示进程和目标 Activity 仍在内存中。广告初始化实验至少固定：

- 相同 App 与 SDK 版本；
- 相同同意状态、广告位和服务端配置；
- cold/warm/hot、安装状态与入口；
- 设备档位、Android 版本和渠道；
- 相同超时、占位和跳过策略。

实验要同时观察启动、稳定性和广告业务保护指标。首帧变快但广告填充骤降，或收入改善但 ANR/P99 上升，都需要产品与技术共同决定，不能只由一个指标自动判定。

## 8. 迁移清单

清单保留代码和交付系统里的原名：runtime-enabled SDK 是为旧 SDK Runtime 改造的 SDK，ASB 是 Android SDK Bundle 交付包，`<uses-sdk-library>` 是 App 声明所需 SDK 包的 Manifest 元素，Binder DTO 是跨进程传递的数据对象，endpoint 是服务端地址，rate limit 是调用频率上限。

### 从旧 Privacy Sandbox 业务 API 退出

- [ ] 搜索 `TopicsManager`、`AdSelectionManager`、`CustomAudienceManager` 与 `MeasurementManager` 的调用点、权限、配置和依赖。
- [ ] 用远程开关停止新请求，页面布局和广告填充不再等待这些结果。
- [ ] 区分已废弃（deprecated）、不支持（unsupported）、已关闭（disabled）、权限/安全拒绝（security）、频率受限（rate limit）、网络错误与调用方本地超时；永久废弃错误不进入重试队列。
- [ ] 盘点 registration（注册）、bidding（竞价）、trusted-data（竞价所需可信数据）与 reporting endpoint（报告地址）的剩余流量，确认旧后台任务和数据库记录的删除边界。
- [ ] 只记录受控的功能名、调用位置、平台/Ad Services extension 版本、结果分类、端到端时间和备用路径；不上传 topic、audience、竞价信号或完整 registration URI。
- [ ] 替代广告、归因和标识方案分别完成合规评审，不把 GAID 当作默认回退。

### 从 Android 14–16 SDK Runtime 迁移到 Android 17

- [ ] 搜索 `SdkSandboxManager`、`SandboxedSdkProvider`、`SandboxedSdk` 和 `*Compat` 使用点。
- [ ] 记录 runtime-enabled SDK、ASB、Manifest `<uses-sdk-library>` 与商店交付依赖。
- [ ] API 37 明确关闭平台 sandbox 路径，不仅检查类是否存在。
- [ ] 删除 `loadSdk()` 的首帧前等待和同步备用路径。
- [ ] 与 SDK 供应方确认 Android 17 支持的嵌入式/替代版本。
- [ ] 移除或冻结 deprecated AndroidX alpha19，验证构建产物不再携带无用 DEX/assets。
- [ ] 把 Binder DTO 转换为当前 SDK 接口时，保留数据版本和错误映射。
- [ ] 对比 merged manifest，确认替代 SDK 新增的 Provider 和组件。
- [ ] 分批放量时观察 TTID、TTFD、帧耗时、ANR/Crash、PSS 和广告保护指标。
- [ ] 为旧 Android 14–16 用户保留受控迁移窗口和可回滚版本。

### Android 17 广告 SDK 启动检查清单

- [ ] merged manifest 与传递依赖已经纳入检查。
- [ ] 自动初始化可以关闭时，使用供应方支持的手动路径。
- [ ] `Application` 只注册轻量网关，不等待 SDK ready。
- [ ] 页面并发 init 被合并成一个会话任务。
- [ ] SDK 要求的调用线程已按对应版本的官方文档验证。
- [ ] 首帧后初始化经过低端设备 CPU/帧竞争验证。
- [ ] 超时、取消、重试和会话级失败的含义清楚。
- [ ] 失败不会触发主线程同步执行旧 SDK 备用路径。
- [ ] UI 占位、跳过和布局变化有产品规则。
- [ ] 数据、同意状态和上传时机有显式契约。
- [ ] 主进程与任何远程进程资源合并统计。
- [ ] SDK 升级有版本、负责人、分批放量开关和可供回滚的构建产物。

## 小结

Android 17 已终止 SDK sandbox 的平台支持，旧的 `loadSdk()` 启动隔离方案只用于维护 Android 14–16 遗留产品。API 37 新代码应停止探测和调用已废弃的平台路径，AndroidX 向后兼容库也不能接替长期维护职责。

广告 SDK 的启动问题随之回到常规工程边界：检查最终 Manifest，控制 Provider 和 Application 的工作，合并并发初始化，明确首帧、TTFD 与广告可用时间的关系，处理失败与重试，并把主线程、帧、内存、稳定性和广告指标放在同一次实验中。隔离能力退场不影响这些原则，但团队需要重新选择受支持的 SDK 交付和运行方式。

## 参考资料

- [Android 17 `SdkSandboxManager.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/framework/java/android/app/sdksandbox/SdkSandboxManager.java)：API 37 deprecation 与 no-op `loadSdk()` 路径。
- [Android 17 `SandboxedSdkProvider.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/framework/java/android/app/sdksandbox/SandboxedSdkProvider.java)：Provider deprecation 与历史 `onLoadSdk()` 边界。
- [Android 17 SDK sandbox flags](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/sdksandbox/flags/sandbox_app_flags.aconfig)：no-op 与 API deprecation flag。
- [Privacy Sandbox technology retirement announcement](https://privacysandbox.google.com/blog/update-on-plans-for-privacy-sandbox-technologies)：2025 年 10 月 17 日的退场决定与后续分阶段移除说明。
- [Privacy Sandbox feature status](https://privacysandbox.google.com/overview/status)：Android 各项技术当前的 phaseout 状态。
- [Android 17 `TopicsManager.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/adservices/framework/java/android/adservices/topics/TopicsManager.java)：无论服务结果如何均返回废弃异常的客户端路径。
- [Android 17 `AdSelectionManager.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/adservices/framework/java/android/adservices/adselection/AdSelectionManager.java)：广告选取入口的废弃标记与回调转换。
- [Android 17 `CustomAudienceManager.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/adservices/framework/java/android/adservices/customaudience/CustomAudienceManager.java)：受众加入、离开等入口的废弃回调。
- [Android 17 `MeasurementManager.java`](https://android.googlesource.com/platform/packages/modules/AdServices/+/refs/tags/android-17.0.0_r1/adservices/framework/java/android/adservices/measurement/MeasurementManager.java)：Attribution Measurement 的 soft removal 注释与过渡调用路径。
- [`SdkSandboxManager` API reference](https://developer.android.com/reference/android/app/sdksandbox/SdkSandboxManager)：API 37 deprecated 和“不再受支持”的公开说明。
- [`SandboxedSdkProvider` API reference](https://developer.android.com/reference/android/app/sdksandbox/SandboxedSdkProvider)：历史加载约束与 API 37 deprecation。
- [SDK Runtime overview](https://privacysandbox.google.com/private-advertising/sdk-runtime/architecture)：Android 14–16 设计目标、进程与通信模型。
- [SDK Runtime backward compatibility](https://privacysandbox.google.com/private-advertising/sdk-runtime/backward-compatibility)：旧版 in-app ClassLoader 兼容模型。
- [AndroidX Privacy Sandbox SDK Runtime releases](https://developer.android.com/jetpack/androidx/releases/privacysandbox-sdkruntime)：alpha19 deprecation 与停止更新说明。
