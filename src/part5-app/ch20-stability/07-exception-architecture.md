---
title: "异常处理架构设计"
chapter: "20.7"
section: "20.7"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-15"
last_verified_against: "AOSP android-16.0.0_r1, Android Developers docs, Kotlin docs, Clippings structure references"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 1
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java"
  - type: aosp
    path: "art/runtime/thread.cc"
  - type: aosp
    path: "system/core/debuggerd/crash_dump.cpp"
  - type: official
    path: "https://developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/crash"
  - type: official
    path: "https://kotlinlang.org/docs/exception-handling.html"
  - type: source
    path: "kotlinx-coroutines-core/common/src/CoroutineExceptionHandler.kt"
  - type: source
    path: "kotlinx-coroutines-core/jvm/src/internal/CoroutineExceptionHandlerImpl.kt"
  - type: source
    path: "kotlinx-coroutines-android/src/AndroidExceptionPreHandler.kt"
tags: [exception-handling, safemode, hotfix, graceful-degradation]
related_chapters: ["20.2", "20.3", "26.2"]
pipeline_stage: task6_pending
task6_state: revisiting
reviewed_by: openclaw-task6
reviewed_date: "2026-05-15"
task6_result: needs-rework
last_task6_at: "2026-05-15T06:05:00+08:00"
last_task6_review_log: "logs/review/2026-05-15-06-review.md"
task6_review_notes: "2026-05-15 Task6 06:05：needs-rework。完成 L1/L2 小修 6 处；沿用 Task9 风险信号标注 4 处并合并 queue，交 Task2B。"
task9_state: reviewed
task2b_state: fixed
last_task2a_at: "2026-05-15T05:33:00+08:00"
task9_result: "needs-rework"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-15"
last_task9_at: "2026-05-15T05:50:05+08:00"
last_task9_review_log: "logs/deep-review/2026-05-15-05-deep-review.md"
task9_review_notes: "2026-05-15 Task9：needs-rework。P0 1：WebView renderer 进程模型误写为可安装 Crash handler 的 App 进程；P1 3：ApplicationExitInfo native tombstone API 边界、SafeMode launch marker/退出补偿链路、崩溃文件 fsync/rename 持久化边界。"

task2b_result: fixed---

# 异常处理架构设计

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 全局异常捕获框架设计
- 🔹 安全气囊（SafeMode）机制
- 🔹 降级策略：功能降级、页面降级、兜底页
- 🔹 灰度发布与热修复集成

### 扩展（可选深入）

- 🔸 多进程异常隔离
- 🔸 Kotlin Coroutine 异常处理

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

异常处理架构解决的不是“把异常都捕获后吞掉”，而是在进程可能退出、功能可能不可用、版本可能已经放量的情况下，尽量保留现场、限制影响面，并给下一次启动留下恢复路径。

20.2、20.3 已经分别讲过 Java Crash 和 Native Crash 的系统机制，26.2 讲 Crash 上报体系。本节聚焦 App 侧架构：捕获入口怎样接入，SafeMode 怎样避免崩溃循环，降级和热修复怎样接入发布系统。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md]

## 全局异常捕获框架设计

全局异常捕获框架分三层：语言运行时入口、进程内最小现场、下次启动补偿。三层职责分开后，Crash handler 里就不会塞进数据库、网络请求、复杂线程调度这些高风险动作。

```mermaid
flowchart TD
  A[Java 未捕获异常 / Native 信号 / 协程无传播异常] --> B[捕获入口]
  B --> C[生成最小异常记录]
  C --> D[原子写入本地文件]
  D --> E[交还系统默认退出路径]
  F[下次启动] --> G[读取未上报记录]
  G --> H[补齐版本 / 设备 / 页面 / 实验上下文]
  H --> I[SafeMode 判定]
  I --> J[上报与聚合]
```

Java 入口使用 `Thread.UncaughtExceptionHandler`。Android 官方文档说明，线程因未捕获异常即将终止时，虚拟机会通知对应 handler；AOSP `RuntimeInit.commonInit()` 默认注册 `LoggingHandler` 和 `KillApplicationHandler`，前者写 `FATAL EXCEPTION` 日志，后者通知 AMS 并结束进程。自定义 handler 处理完后必须调用上一个 handler，不能吞掉系统退出路径。详见 20.2。[已验证: 官方文档, developer.android.com/reference/java/lang/Thread.UncaughtExceptionHandler][已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/com/android/internal/os/RuntimeInit.java]

Native 入口通常交给 Crashpad、Breakpad 或厂商 APM SDK。信号处理函数的安全边界比 Java handler 更窄，不能依赖锁、堆分配、日志框架和网络。端侧只写最小记录，堆栈符号化、聚合和告警放到 26.2 的上报系统处理。详见 20.3。[已验证: AOSP android-16.0.0_r1, system/core/debuggerd/crash_dump.cpp]

异常记录建议拆成两份：崩溃当下写入 `crash_envelope`，下次启动再补 `runtime_context`。

| 记录 | 写入时机 | 字段 | 设计边界 |
|------|----------|------|----------|
| `crash_envelope` | 崩溃入口 | 时间、进程名、线程名、异常类型、栈顶摘要、版本号、构建号 | 只做原子文件写入，不做网络请求 |
| `runtime_context` | 下次启动 | 设备、系统版本、页面、登录态摘要、实验分组、最近开关变更 | 可读数据库和配置中心，但要脱敏 |
| `exit_reason` | Android 11+ 下次启动 | `ApplicationExitInfo` 的 reason、status、importance、trace | 用于补 Java/Native handler 没拿到的退出原因 |

Android 11 引入 `ApplicationExitInfo`，应用可通过 `ActivityManager.getHistoricalProcessExitReasons()` 查询历史进程退出原因。它适合补偿“进程被系统杀死、handler 没来得及执行、Native crash 只留下系统 trace”的场景，但不能替代 Crash handler；它拿到的是系统记录，不保证包含业务上下文。[已验证: 官方文档, developer.android.com/reference/android/app/ApplicationExitInfo]

[需确认: `ApplicationExitInfo.getTraceInputStream()` 对 native tombstone 的 API 边界、空 trace fallback 需按 Task9 问题单补齐。]

全局捕获框架的边界要写进 SDK 契约：

- 捕获入口只保证留证，不保证恢复当前进程。
- Java Crash handler 处理完必须交还默认 handler。
- Native signal handler 只做异步信号安全范围内的记录。
- 业务上下文在下次启动补齐，不能在崩溃线程里临时查数据库。
- 多个 SDK 同时接管 handler 时，注册顺序必须可观测，后注册者要保存并调用前一个 handler。

[结构参考: Clippings/Android 应用稳定性剖析与优化 - Java 堆栈：深入了解 Throwable.md]

## 安全气囊（SafeMode）机制

SafeMode 是 App 侧的“崩溃循环保护”。它不等同于 Android 系统安全模式；它只在应用内部关闭高风险模块，让用户能进入基础页面，给远程配置、热修复或版本回滚争取时间。

进入 SafeMode 的判定来自本地崩溃记录。常用规则是：同一版本、同一进程、短时间内连续启动失败，且栈顶摘要或崩溃类型高度相似。阈值不要写死在代码里，应当由本地默认值和远程配置共同决定；远程配置不可用时，本地默认值仍然能生效。[待验证: 具体阈值需要结合产品 DAU、启动路径和 Crash 分布设定]

SafeMode 的判定时机要早于大多数 SDK 初始化。实践上可以放在 `Application.attachBaseContext()` 或主进程 `Application.onCreate()` 的最前段，至少要早于动态配置拉取、AB 实验初始化、广告 SDK、埋点 SDK 和首页业务容器。这样即使问题来自这些模块，也能先把它们关掉。

下面这段示意代码表达 SafeMode 的最小判定模型，重点看“读取本地崩溃记录 → 命中规则 → 写入本地降级开关”三步。

```kotlin
// 示意代码：SafeMode 判定，不代表可直接复制到生产环境。
class SafeModeController(
    private val crashStore: CrashStore,
    private val localSwitch: LocalSwitch
) {
    fun evaluate(appVersion: String, processName: String): SafeModeDecision {
        val recent = crashStore.recentCrashes(appVersion, processName)
        val matched = recent
            .groupBy { it.stackFingerprint }
            .any { (_, crashes) -> crashes.size >= localSwitch.safeModeCrashThreshold }

        return if (matched) {
            localSwitch.enable("safe_mode")
            SafeModeDecision.Enabled(reason = "repeated_crash")
        } else {
            SafeModeDecision.Disabled
        }
    }
}
```

这段代码只描述判定流程。生产实现还要处理文件损坏、跨进程并发写入、系统时间回拨、版本升级后清理旧记录等边界。

[需补充素材: SafeMode 判定还缺 launch marker 状态机、启动成功标记、退出原因过滤和离线补偿链路，交 Task2B 按 Task9 问题单补齐。]

SafeMode 打开的内容要分级，避免“一进保护模式就什么都不能用”：

| 等级 | 触发条件 | 动作 | 用户体验 |
|------|----------|------|----------|
| L1 | 新版本轻微崩溃升高 | 关闭实验、延迟非必要 SDK、停用高风险入口 | 首页可用，部分功能隐藏 |
| L2 | 启动阶段连续崩溃 | 跳过首页复杂容器，进入轻量首页或兜底页 | 可登录、可查看基础内容 |
| L3 | 主进程启动即崩 | 只保留修复入口、反馈入口和升级提示 | 功能受限，但进程不再循环退出 |

退出 SafeMode 也要有规则。常见做法是版本升级后自动清理；同一版本连续若干次冷启动成功后降级为 L1；远程配置确认问题已关闭后退出。退出规则不能只依赖服务端，因为触发 SafeMode 的设备可能正处在离线状态。

[自动发现] Android Vitals 的用户感知崩溃率会影响 Google Play 上的质量评估。SafeMode 的价值不只是减少 crash 次数，也是在新版本出现集中问题时减少用户感知崩溃。阈值和告警策略应与 20.6、26.2 的稳定性指标合并设计。[已验证: 官方文档, developer.android.com/topic/performance/vitals/crash]

## 降级策略：功能降级、页面降级、兜底页

降级策略要和异常类型绑定。所有异常都跳到兜底页，会把可恢复的小问题放大成产品不可用；所有异常都只打日志，又会让启动崩溃反复发生。

### 功能降级

功能降级适合“单个模块失败但主流程可继续”的场景，例如推荐排序异常、图片编辑组件初始化失败、某个 SDK 初始化超时。处理方式是关闭模块入口、切换本地实现、延迟初始化，或返回缓存数据。

功能降级的实现依赖本地开关表。开关表必须具备三个能力：启动前可读、远程配置可覆盖、版本升级可重置。不要把降级开关只放在内存里；进程崩溃后，下一次启动还要继续生效。

### 页面降级

页面降级适合“页面容器或数据组合失败”的场景。典型例子是首页某个 feed 模块崩溃、WebView 容器初始化失败、Compose 页面状态恢复失败。页面层不要把异常直接抛到进程级 handler，而应当在页面边界捕获并切换轻量页面。

页面降级需要保留来源信息：页面名、路由参数摘要、实验分组、最近一次配置版本。没有这些信息，服务端只能看到一批相似堆栈，无法判断是页面代码、配置数据还是实验导致的问题。

### 兜底页

兜底页是 L2/L3 SafeMode 的保护入口。它只承担三件事：让进程稳定存活、给用户明确反馈、提供恢复动作。兜底页不应该继续加载复杂 SDK、广告、推荐流和动态容器。

兜底页至少包含这些动作：

- 重新尝试进入主流程，但要限制频率。
- 清理最近一次动态配置、实验分组或页面缓存。
- 引导升级到新版本或打开反馈入口。
- 写入一条明确的 SafeMode 事件，供 26.2 的上报体系聚合。

降级策略的设计原则是“尽量缩小故障半径”。模块能降级就不影响页面，页面能降级就不影响进程，进程已进入崩溃循环才进入 SafeMode。

## 灰度发布与热修复集成

异常处理架构要和发布系统共用同一套风险控制字段：版本号、构建号、渠道、设备型号、系统版本、实验分组、功能开关版本。Crash 上报、SafeMode 判定、灰度暂停和热修复命中都依赖这些字段。

灰度发布阶段建议把异常分成三类处理：

| 类型 | 判定依据 | 发布动作 |
|------|----------|----------|
| 明确代码缺陷 | 新版本新堆栈、集中在同一代码路径、复现稳定 | 暂停灰度，准备热修复或新包 |
| 配置 / 实验问题 | 同版本内只影响某个实验组或配置版本 | 关闭实验、回滚配置、保持版本灰度暂停 |
| 设备 / 系统相关 | 集中在特定机型、系统版本或 ABI | 限制设备放量，补兼容策略 |

热修复适合修确定性代码缺陷，不适合修资源生命周期混乱、线程时序竞争、Native ABI 不匹配这类难以验证的问题。热修复补丁上线前要经过三个检查：补丁是否能在目标版本加载，是否能覆盖崩溃栈对应代码，失败时是否会回退到旧逻辑而不是制造新崩溃。[待验证: 具体热修复框架的加载时机、类加载边界和兼容范围需按项目 SDK 验证]

SafeMode 与热修复的关系可以这样设计：

1. SafeMode 先抑制崩溃循环，保证用户能启动应用。
2. 远程配置关闭高风险功能，降低继续触发的概率。
3. 热修复或新包解决代码缺陷。
4. 连续稳定启动后退出 SafeMode，恢复功能开关。

灰度系统还要把“未命中热修复但进入 SafeMode”的设备单独标出来。这类设备往往存在网络不可用、补丁下载失败、ABI 不匹配、补丁被清理等问题，不能只看服务端补丁成功率。

## 多进程异常隔离

多进程架构能把故障限制在某个进程里，但也会让异常捕获变复杂。每个进程都有自己的 `Application`、默认 handler、文件锁和初始化路径；只在主进程注册 Crash handler，会漏掉远程服务进程、播放器进程和推送进程的崩溃。

多进程异常隔离建议按进程角色设计：

| 进程 | 典型职责 | 异常策略 |
|------|----------|----------|
| 主进程 | UI、路由、账号、基础业务 | 捕获完整上下文，触发 SafeMode 判定 |
| 远程服务进程 | 下载、播放、长任务 | 独立记录 crash，失败后由主进程决定是否重启 |
| App 自有 WebView 进程（`:web` / `:h5`） | H5、动态页面 | 页面级兜底优先，必要时销毁容器进程 |
| 上传进程 | Crash 样本上传 | 只做补偿上传，不能依赖主进程内存状态 |

这里要区分两类 WebView 进程：App 在 `AndroidManifest.xml` 中声明的自有 `:web` / `:h5` 进程，和 Android 系统为 WebView 渲染创建的 renderer 进程。自有进程走上面的 Crash handler 注册逻辑，与主进程类似。系统 WebView renderer 进程则不同：它由 WebView 提供方（Android System WebView 或 Chrome）管理，App 不能在 renderer 进程里安装 Crash handler，也不能控制它的生命周期。App 侧通过 `WebViewClient.onRenderProcessGone()` 接收 renderer 退出通知：

```java
@Override
public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
    // 1. 记录崩溃信息
    if (detail.didCrash()) {
        // renderer 崩溃退出，记录堆栈上下文
        crashReporter.log("WebView renderer crashed");
    } else {
        // renderer 被 OS 杀死（OOM / 内存压力），不是崩溃
        crashReporter.log("WebView renderer killed by OS");
    }
    // 2. 销毁受影响的 WebView 实例
    view.destroy();
    // 3. 显示兜底页或重建 WebView
    showFallbackPage();
    return true; // 已处理，不让系统走默认行为
}
```

`onRenderProcessGone()` 返回 `true` 表示 App 已处理 renderer 退出；返回 `false` 会让系统杀掉 App 进程。renderer 退出后，受影响的 `WebView` 实例不可再用，必须调用 `destroy()` 释放资源后再重建。如果是 OOM 导致的 renderer 被杀（`didCrash()` 返回 `false`），兜底页应避免再次创建 WebView，而是提示用户稍后重试。[已验证: Android Developer Docs, developer.android.com/reference/android/webkit/WebViewClient.html#onRenderProcessGone]

记录文件要带进程名和 pid。跨进程写同一个文件容易损坏，建议按进程分文件，再由下次启动的主进程或上传进程汇总。文件写入用临时文件 + rename 的原子替换方式，避免崩溃发生在写入中间导致记录不可解析。

[需补充素材: crash 文件持久化协议只写“临时文件 + rename”不够，需补 flush/fsync、rename 后父目录 fsync、completed/tmp 扫描与 partial 清理规则。]

多进程重启要限制次数。远程服务进程崩溃后立刻拉起，可能形成后台崩溃风暴；更稳的策略是指数退避、本地计数、达到阈值后关闭该服务入口，并把“重启被抑制”作为事件上报。[待验证: 具体重启策略需要结合业务保活要求和厂商后台限制验证]

[自动发现] 线程监控也要纳入异常架构。参考书给出通过 ASM 字节码插桩把无名 `Thread()` 改成带调用来源的 `Thread(String)` 的思路。这个能力可以帮助异常记录区分 `Thread-7` 这类匿名线程，减少崩溃归因成本。现代 Android Gradle Plugin 下需要用当前项目可用的 ASM 接入点实现，不能沿用已废弃的 Transform API 方案。[待验证: AGP 版本与可用 ASM 接入点需按当前项目确认][结构参考: Clippings/Android 应用稳定性剖析与优化 - 线程监控：如何解决“匿名”线程？.md]

## Kotlin Coroutine 异常处理

协程异常不能只依赖 `Thread.UncaughtExceptionHandler`。Kotlin 官方文档把协程异常分成两类：`launch` 根协程的未捕获异常会向外报告；`async` 会把异常保存在 `Deferred` 中，直到调用 `await()` 时抛出。`CoroutineExceptionHandler` 只处理没有传播路径的异常，不能当成普通 `try/catch` 使用。[已验证: Kotlin 官方文档, kotlinlang.org/docs/exception-handling.html]

协程异常路径可以按创建方式区分：

| 创建方式 | 异常去向 | 工程处理 |
|----------|----------|----------|
| `launch` 根协程 | 交给 `CoroutineExceptionHandler` 或平台兜底 | 在业务边界注册 handler，记录协程名和页面 |
| 子协程 `launch` | 传播到父协程，通常取消父协程 | 在作用域边界处理，避免页面整体被取消后无提示 |
| `async` | 存在 `Deferred`，`await()` 时抛出 | `await()` 位置要有明确错误处理 |
| `supervisorScope` 子任务 | 子任务失败不取消同级任务 | 给子任务单独记录失败事件 |

`kotlinx.coroutines` 的 JVM 实现会通过 `ServiceLoader` 加载平台级 `CoroutineExceptionHandler`。在 Android 上，`kotlinx-coroutines-android` 提供 `AndroidExceptionPreHandler`，用于处理 Android 8.0/8.1 的 pre-handler 行为差异；之后仍会走到线程未捕获异常兜底路径。[已验证: kotlinx-coroutines-core/jvm/src/internal/CoroutineExceptionHandlerImpl.kt][已验证: kotlinx-coroutines-android/src/AndroidExceptionPreHandler.kt]

协程接入异常架构时，要补三类上下文：

- 协程名称：通过 `CoroutineName` 写入业务作用域，避免只看到 Dispatcher 线程名。
- 页面生命周期：`viewModelScope`、`lifecycleScope` 的异常要带页面和状态，方便判断是否与页面销毁时序有关。
- 结构化并发边界：`supervisorScope`、`SupervisorJob` 会改变异常传播方式，Crash 记录里要能看出作用域类型。

协程 handler 里仍然不能做重操作。它可能运行在主线程、IO 线程或自定义 Dispatcher 上，执行耗时逻辑会扩大故障影响。建议只写最小记录，然后把上报交给统一 Crash SDK。

## 小结

异常处理架构的目标是把故障分层处理：入口层保留证据，SafeMode 防止崩溃循环，降级层限制影响范围，灰度和热修复层控制版本风险。Java、Native、协程、多进程各有不同入口，但最终都要汇入同一套本地记录、上报聚合和发布控制系统。

本节没有重复 20.2、20.3 的底层机制，也没有展开 26.2 的服务端上报实现。实际接入前还要核对三件事：SafeMode 阈值是否符合业务现状，多进程文件写入是否具备原子性，热修复框架边界是否和当前项目一致。

## 参考资料

### Kotlin 协程异常处理与 UncaughtExceptionHandler 三层级联体系
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-11-kotlin-coroutine-exception-handler-analysis.md
- 类型：DeepResearch 调研结果
- 摘要：Kotlin 协程异常处理形成 CoroutineExceptionHandler（Context级）→ ServiceLoader 全局 handler → Thread.uncaughtExceptionHandler 三层级联。Android 8.0/8.1 存在 AndroidExceptionPreHandler 反射兼容问题，协程可能绕过 pre-handler。
- 注入时间：2026-05-17
- 价值：源码级梳理协程异常三级分发机制，解决协程崩溃归因与 UncaughtExceptionHandler 关系模糊的问题
