---

title: "SafeMode 崩溃循环判定与启动补偿链路"
chapter: "20.12"
section: "20.12"
status: "finalized"
drafted_date: "2026-05-16"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-22"
last_verified_against: "AOSP android-17.0.0_r1 / developer.android.com"
confidence: high
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控:实现自定义 Crash 处理器.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控:为我们应用插上监控 Native Crash 的电子眼.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Backtrace:Native 堆栈信息获取.md"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 2.md"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 39.md"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "https://developer.android.com/ndk/guides/debug"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/webapps/managing-webview"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ApplicationExitInfo.java"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java"
  - type: aosp
    path: "frameworks/base/core/java/android/webkit/WebViewClient.java"
  - type: aosp
    path: "frameworks/base/core/java/android/webkit/WebViewRenderProcessClient.java"
  - type: aosp
    path: "frameworks/base/core/java/android/util/AtomicFile.java"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java"
tags: [stability, safemode, crash-loop, applicationexitinfo, startup]
related_chapters: ["20.2", "20.3", "20.6", "20.7", "26.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "章节深挖/参考书素材"
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
reviewed_date: "2026-06-22"
reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-06-22"
last_task6_at: "2026-06-22T15:05:00+08:00"
task6_review_notes: '2026-06-22 Task6 复审(revisiting): 四层质检全部通过，3处小修已处理，2处需高爷确认的技术问题已标注。 | 2026-06-22 task6 复审(revisiting): L1/L2/L3/L4 全部通过，无新问题。章节从 revisiting 晋升 finalized。'
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-22"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-22T13:35:41.580031+08:00"
last_task9_review_log: "logs/deep-review/2026-06-22-13-deep-review.md"
auto_promoted_by: task6-auto-promotion
task6_auto_promoted_at: "2026-06-22T15:05:00+08:00"
task2b_state: "fixed"
last_task9_audit: "2026-06-09"
last_task9_audit_log: "logs/deep-review/2026-06-09-04-audit.md"
last_task9_autofix_at: "2026-06-22"
task9_review_notes: "2026-06-22 Task9 复审:auto-fixed。修正 ApplicationExitInfo 时间戳口径与 Android 11/14 版本边界、tombstoned unlinkat/linkat 提交表述；无新增 queue 技术回炉项。"
task2b_result: "fixed"
last_task2b_main_at: "2026-06-22T12:51:50+08:00"
last_task2b_lite_at: "2026-06-22"
task6_result: "pass-light-edit"
last_task6_audit: "2026-06-22"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
---

# 20.12 SafeMode 崩溃循环判定与启动补偿链路

20.7 节介绍了异常恢复架构中的保护模式。这里聚焦一个场景：同一版本、同一进程、同一启动路径连续失败时，应用怎样在下一次启动中绕开可选的高风险模块，同时保留诊断证据和恢复入口。

这里的 SafeMode 是应用自建的降级启动模式，不是 Android 系统安全模式。它不负责“修好”崩溃，也不允许绕过数据库一致性、账号安全或支付校验。它只负责在证据足够时选择一份更保守的启动计划，让用户能够进入基础页面、升级应用或提交反馈。

平台源码锚点是 Android 17 / API 37 / `android-17.0.0_r1`。涉及低内存回收边界时，内核锚点是 `android17-6.18-2026-06_r6`。

## 先划清判定边界

启动 marker 停在“未完成”，只能说明上一次没有走到应用定义的成功点，不能单独证明发生了崩溃。下面这些情况都可能留下相同的文件状态：

- 用户在最近任务或系统设置中停止应用；
- 系统在内存压力下回收后台进程；
- 设备重启，`elapsedRealtime()` 的时间基准随之改变；
- 应用升级或数据恢复后读到了旧版本 marker；
- 多进程同时写同一个文件；
- 进程还在运行，另一个进程却把它当成历史启动；
- 文件写入成功，但成功状态还未来得及持久化。

因此，SafeMode 需要区分三类数据：

| 数据 | 解决的问题 | 保存边界 |
| --- | --- | --- |
| 启动租约 `LaunchLease` | 上一次启动走到了哪个阶段 | 按版本、进程和启动路径隔离 |
| 失败样本 `FailureOccurrence` | 哪些退出证据能与某次启动关联 | 有数量与时间上限，去除隐私字段 |
| 降级计划 `DegradationPlan` | 下一次启动具体跳过什么 | 按模块、页面、进程和版本限定 |

不要用一个 `crash_count` 同时负责这三项职责。只保存计数会丢失证据来源，也无法解释为什么某次启动被降级。

## 状态模型：租约不是结论

一轮启动可以按以下里程碑推进：

| 状态 | 写入时机 | 含义 |
| --- | --- | --- |
| `LAUNCHING` | 读取旧租约之后、高风险初始化之前 | 新启动已经开始 |
| `PROCESS_READY` | `Application.onCreate()` 及必要基础设施完成 | 进程级必需初始化通过 |
| `INTERACTIVE` | 首个关键页面已绘制并能响应输入 | 用户已经获得基础可用能力 |
| `PROBATION` | 降级启动进入观察期 | 暂不恢复被禁用模块 |
| `HEALTHY` | 达到配置的成功条件 | 可以逐步撤销当前降级计划 |

进程退出后没有机会把状态推进到 `INTERACTIVE`，旧租约会停在较早阶段。下一次启动只能把它标记为“待核对”，再结合系统退出记录、本地崩溃信封和安装信息形成判断。

这也是为什么启动入口的顺序很重要：

1. 读取上一轮租约与已经确认的失败样本；
2. 校验版本、进程、启动路径和时间基准；
3. 为本轮启动写入新租约；
4. 依据已有的高置信证据选择普通或降级计划；
5. 在可选 SDK、插件、WebView 预热等高风险步骤之前执行计划；
6. 进入页面后推进里程碑；
7. 在后台核对 `ApplicationExitInfo`，补记上一轮退出原因；
8. 达到恢复条件后进入观察期，再逐步撤销降级。

第 4 步不能等待耗时的 trace 读取，否则 SafeMode 自身会拖慢启动。系统退出元数据的查询与 trace 复制应分开处理。

## 启动租约应记录什么

建议使用稳定枚举和内部 ID，不要保存 URL、搜索词、订单号、账号或用户输入。

| 字段 | 用途 | 注意事项 |
| --- | --- | --- |
| `schemaVersion` | 兼容持久化格式升级 | 未知版本按不可用处理 |
| `versionCode` / `lastUpdateTime` | 区分安装版本与覆盖安装 | 版本变化不应删除旧诊断证据 |
| `processName` / `processRole` | 区分主进程、推送、独立服务 | PID 只作辅助，不能跨启动关联 |
| `launchId` | 关联租约、崩溃信封与进程摘要 | 使用随机 ID，不含用户信息 |
| `route` | 区分首页、通知、深链等入口 | 只保存粗粒度枚举 |
| `startedWallMs` | 与 `ApplicationExitInfo.timestamp` 对齐 | 墙钟可能被用户或网络校时修改 |
| `startedElapsedMs` | 同一次开机内计算持续时间 | 设备重启后不能与旧值相减 |
| `bootSequence` | 判断 `elapsedRealtime` 是否仍同源 | 可记录可读的系统启动次数；取不到时保持为空 |
| `stage` | 表示启动里程碑 | 每次推进使用原子替换 |
| `planId` | 说明本轮采用的降级计划 | 便于恢复与效果分析 |

`ApplicationExitInfo.getTimestamp()` 使用墙钟时间。`SystemClock.elapsedRealtime()` 适合本次开机内的超时判断，两者不能混算。API 24 起可读取 `Settings.Global.BOOT_COUNT` 作为启动序号；读取失败时保持为空，不要改用隐藏接口。若启动序号变化、elapsed 值倒退或墙钟偏移异常，只能降低证据置信度，不能直接增加失败次数。

还要先读旧租约，再写新租约。若入口一开始便覆盖文件，上一轮启动的 `launchId`、阶段和时间范围都会丢失。

## 用 AtomicFile 保存租约

`AtomicFile` 解决的是单个文件的“旧版本或新版本可读”问题，不提供线程锁或跨进程锁。Android 17 的实现要求调用方自己串行化访问；`finishWrite()` 会同步并提交新文件，`failWrite()` 会放弃本次新文件。

下面的示例只展示单进程、单写者的提交协议。多进程应用应为每个进程使用独立文件，并由一个明确的 owner 汇总失败样本。

```kotlin
class LaunchLeaseStore(file: File) {
    private val atomicFile = AtomicFile(file)
    private val lock = Any()

    fun readOrNull(): LaunchLease? = synchronized(lock) {
        try {
            atomicFile.openRead().use { input ->
                LaunchLeaseCodec.decode(input)
            }
        } catch (_: FileNotFoundException) {
            null
        } catch (_: IOException) {
            null
        } catch (_: RuntimeException) {
            null
        }
    }

    @Throws(IOException::class)
    fun write(lease: LaunchLease) = synchronized(lock) {
        var output: FileOutputStream? = null
        try {
            output = atomicFile.startWrite()
            LaunchLeaseCodec.encode(lease, output)
            atomicFile.finishWrite(output)
            output = null
        } catch (e: IOException) {
            output?.let(atomicFile::failWrite)
            throw e
        } catch (e: RuntimeException) {
            output?.let(atomicFile::failWrite)
            throw e
        }
    }
}
```

代码没有捕获 `Throwable`，因为 `OutOfMemoryError`、`ThreadDeath` 等错误不应被伪装成普通持久化失败。生产实现还需要格式版本、长度上限、校验和与损坏文件隔离；这些措施用于保证“读不到时安全退化”，不能把损坏文件当成一次崩溃。

若多个进程共享同一个 `AtomicFile`，各进程中的 `synchronized` 互相不可见，仍可能覆盖数据。更稳妥的结构是 `lease-main`、`lease-push`、`lease-web` 分文件写入，由主进程或后台任务单向汇总。

## 两阶段证据核对

SafeMode 的入口决策分成快速路径和补偿路径。

### 快速路径：只使用已经确认的本地证据

在可选初始化之前，读取上一轮已经持久化的高置信失败样本。满足以下条件时，才允许它参与本轮降级决策：

- 样本与当前 `versionCode`、安装时间和进程角色一致；
- 样本关联到明确的 `launchId` 或受控时间窗；
- 上一轮租约尚未到达 `INTERACTIVE`；
- 失败类型属于策略允许保护的类型；
- 同一降级计划尚未超过尝试和冷却限制。

仅有一个残留 `LAUNCHING` 租约时，入口可以采用“低成本防御”，例如推迟非必要预热，但不应直接清数据库、禁用登录或永久进入保护模式。

### 补偿路径：启动后核对系统退出历史

API 30 起，`ActivityManager.getHistoricalProcessExitReasons()` 返回系统保存的历史进程退出记录，顺序由新到旧。它是有容量上限的历史记录，不是永久审计日志，也不能保证每条记录都有 trace。

核对时至少要比较：

- `processName` 与进程角色；
- `timestamp` 是否落在旧租约开始之后、下一轮启动之前的容差窗口；
- `reason`、`status`、`importance` 与租约阶段是否相符；
- 应用版本、`lastUpdateTime` 和安装边界；
- 本地崩溃信封或进程状态摘要中的 `launchId`；
- 该退出记录是否已经消费，避免重复计数。

下面的伪代码强调“先筛元数据、后处理 trace”。`clockSkewMs` 只用于吸收正常的墙钟误差，应由遥测校准并设置上限。

```kotlin
fun correlateExit(
    exits: List<ApplicationExitInfo>,
    previous: LaunchLease,
    nextLaunchWallMs: Long,
    clockSkewMs: Long
): ApplicationExitInfo? {
    val from = previous.startedWallMs - clockSkewMs
    val until = nextLaunchWallMs + clockSkewMs

    return exits.asSequence()
        .filter { it.processName == previous.processName }
        .filter { it.timestamp in from..until }
        .filterNot { alreadyConsumed(it) }
        .maxByOrNull { candidate ->
            evidenceScore(candidate, previous)
        }
        ?.takeIf { evidenceScore(it, previous) >= REQUIRED_SCORE }
}
```

这段代码没有把“时间接近”当成唯一条件。`evidenceScore()` 应把进程、版本、`launchId`、阶段和退出类型分开计分；没有唯一候选时保持未知，比选错一条记录更安全。

不要在冷启动主线程里打开并解析 `getTraceInputStream()`。选定候选记录后，再交给受限后台任务：设置输入大小和执行时间上限，复制到私有目录，记录哈希与解析状态，然后关闭流。系统 trace 可能为空，也可能已被环形缓冲区覆盖；“没有 trace”不能反证“没有 ANR 或 native crash”。

### processStateSummary 只保存关联摘要

`ActivityManager.setProcessStateSummary()` 可以给系统退出记录附带最多 128 字节的应用摘要。Android 17 源码注释明确说明它用于运行状况分析，不适合恢复 UI 状态；调用过于频繁时系统还可能节流。

摘要可以包含格式版本、`launchId` 的短哈希、进程角色、启动阶段和计划 ID。只在关键里程碑更新，不要每个生命周期回调都写，也不要加入账号、页面参数或业务内容。

## 退出原因怎样进入 SafeMode

`ApplicationExitInfo` 的 `reason` 是分类线索，不是对业务故障的完整归因。建议按置信度和用途处理：

| 退出原因 | 默认归类 | SafeMode 用法 |
| --- | --- | --- |
| `REASON_CRASH` | Java 或运行时崩溃 | 与未完成租约、进程和签名匹配后计入 |
| `REASON_CRASH_NATIVE` | native crash | 与 tombstone/本地最小信封匹配后计入 |
| `REASON_ANR` | ANR | 只有发生在启动窗口并影响关键进程时才计入 |
| `REASON_INITIALIZATION_FAILURE` | 进程初始化失败 | 高度相关，但仍需校验版本、进程与阶段 |
| `REASON_DEPENDENCY_DIED` | 依赖进程死亡 | 选择依赖模块或进程级计划，不归并成主进程崩溃 |
| `REASON_LOW_MEMORY` | 低内存回收 | 进入内存保护策略，默认不增加崩溃循环次数 |
| `REASON_EXCESSIVE_RESOURCE_USAGE` | 资源使用过量 | 单独统计并选择资源降级 |
| `REASON_USER_REQUESTED` / `REASON_USER_STOPPED` | 用户或系统设置触发 | 排除 |
| `REASON_PACKAGE_STATE_CHANGE` / `REASON_PACKAGE_UPDATED` | 包状态变化 | 切断当前启动关联，不计失败 |
| `REASON_PERMISSION_CHANGE` | 权限变更导致 | 排除崩溃循环，转入权限诊断 |
| `REASON_EXIT_SELF` | 应用主动退出 | 单独排查 `System.exit()` 调用，不直接归为 crash |
| `REASON_FREEZER` / `REASON_OTHER` | 系统管理行为 | 默认排除；说明字段只作为诊断补充 |
| `REASON_SIGNALED` | 收到信号 | 结合 `status`、前后台状态和其他证据，不把 `SIGKILL` 自动当作 crash |
| `REASON_UNKNOWN` | 证据不足 | 保持未知，不用来升级高风险降级 |

低内存是否能被可靠报告取决于设备支持。`ActivityManager.isLowMemoryKillReportSupported()` 在 AOSP 中读取 LMKD 的 report-kills 能力；不支持的设备可能只能留下更弱的信号证据。应用不应从一个 `SIGKILL` 反推“必然是 LMK”，也不应从 LMK 记录反推代码崩溃。

API 37 的 `ApplicationExitInfo.getAnrInfo()` 可以为 `REASON_ANR` 提供结构化补充，但返回值允许为空。它适合丰富诊断，不改变“退出元数据、启动阶段、trace 三者都可能不完整”的边界。ANR 也不一定立即杀进程：应用可能恢复运行，之后又因别的原因退出，因此不能看到一份 ANR trace 就覆盖后续退出原因。

## Java Crash：只做有界采集，不尝试续命

AOSP `RuntimeInit` 在进程启动时安装预处理器 `LoggingHandler` 和默认的 `KillApplicationHandler`。默认处理器会用 `mCrashing` 防止重入，向 `ActivityManager` 报告崩溃，并在 `finally` 中调用 `Process.killProcess()` 与 `System.exit(10)`。

应用安装自定义 `UncaughtExceptionHandler` 时，应保存并调用原处理器。它可以尽力写一份有长度上限的崩溃信封，但不能依赖网络、主线程、复杂 JSON、数据库事务或新的线程池，也不能把“handler 返回”当成恢复方案。

这段示例表达最小职责：记录关联信息，然后把控制权交还原处理器。

```kotlin
class CrashEnvelopeHandler(
    private val previous: Thread.UncaughtExceptionHandler,
    private val recorder: CrashEnvelopeRecorder,
    private val leaseProvider: () -> LaunchLease?
) : Thread.UncaughtExceptionHandler {

    override fun uncaughtException(thread: Thread, error: Throwable) {
        try {
            recorder.tryWriteBounded(
                launchId = leaseProvider()?.launchId,
                threadName = thread.name,
                throwable = error
            )
        } catch (_: IOException) {
            // 下次启动还会用 ApplicationExitInfo 补偿。
        } catch (_: RuntimeException) {
            // 采集失败不能阻断系统默认崩溃处理。
        } finally {
            previous.uncaughtException(thread, error)
        }
    }
}
```

`tryWriteBounded()` 应限制栈深、字符串长度、文件大小和耗时。即使这份信封没有写成，下一次启动仍可使用 `ApplicationExitInfo`；所以 SafeMode 不能把崩溃时落盘当作唯一证据。

## Native Crash：一个采集 owner，保留系统链路

native 信号上下文的可用操作非常有限。不要在 signal handler 中分配大块内存、格式化复杂字符串、获取 Java 栈、加普通互斥锁或执行网络请求。

应用若必须写本地信封，只记录预分配结构中的 `launchId`、signal、tid、pc 和少量寄存器，并使用信号安全写入方式。进程内只保留一个 native crash 采集 owner，其他 SDK 通过统一接口订阅结果，避免多个 handler 互相覆盖。

Android 的 debuggerd/tombstoned 链路仍应保留。API 31 起，部分 native crash 的 `ApplicationExitInfo.getTraceInputStream()` 可返回 tombstone protobuf；它比应用在致命信号现场做复杂回溯更适合下次启动分析。符号化、so 版本匹配和聚类在后台或服务端完成，启动路径只消费稳定的签名 ID。

## ANR：区分启动阻塞与后续退出

ANR 发生时，主线程往往已经不能执行应用补救逻辑。把“写 SafeMode 状态”安排在 ANR callback 内没有可靠性保证。

对启动期 ANR，核对应满足：

- `REASON_ANR` 的记录与上一轮进程和时间窗相符；
- 旧租约停在 `PROCESS_READY` 或更早阶段；
- trace 或 `getAnrInfo()` 指向关键启动路径，或者本地阶段证据足够；
- 后续没有更匹配的包更新、用户停止或其他退出记录。

若 ANR 出现在应用已经 `INTERACTIVE` 之后，应进入常规 ANR 治理，不要污染启动崩溃计数。相关采集、归因和指标见 20.4 节。

## SafeMode 选择“计划”，不要选择“一键全关”

合理的降级对象是可选且能被隔离的模块：

| 失败范围 | 可选计划 | 不应做的事 |
| --- | --- | --- |
| 图片库或特定 native SDK 初始化 | 延迟加载、关闭硬件路径、替换为保守实现 | 禁用全部 native 能力 |
| 非必要数据库预热 | 推迟预热、只读展示缓存 | 跳过必须完成的 schema 迁移 |
| 动态插件或热修复模块 | 停用指定模块和版本 | 加载未校验的旧代码 |
| WebView 预热或特定页面 | 取消预热、延迟创建、回退原生说明页 | 把 renderer 退出算成主进程 crash |
| 推荐、动画、埋点增强项 | 延迟或采样关闭 | 关闭登录、安全、支付校验 |
| 独立服务进程 | 禁用该进程对应的可选功能 | 把子进程计数写进主进程桶 |

计划可以表示为 `moduleId + action + scope + reason + expiry`，并绑定适用的版本和进程。远程配置只是一种输入：应用必须缓存一份已校验的配置，并保留本地保守默认值。设备已经陷入启动循环时，不能假设网络请求还能完成。

严禁自动清除用户数据、删除数据库、重置账号状态或绕过强制迁移。若必需不变量本身失败，保护模式应展示明确的修复入口，例如升级、重新安装前的数据导出说明或联系客服，而不是偷偷跳过校验。

## 阈值是策略参数，不是平台常量

不存在适用于所有应用的“三次崩溃”或“十分钟窗口”。策略至少要描述：

- 最小证据置信度；
- 连续失败数与滑动时间窗；
- 同一签名、模块或启动路径的聚合方式；
- 单次高危故障是否只启用低风险计划；
- 计划最长持续时间与最大尝试次数；
- 退出保护模式所需的成功样本；
- 观察期内复发时怎样回退；
- 版本升级、回滚和覆盖安装时怎样分桶。

这些数值应由灰度数据、误判成本、模块可逆性和业务风险决定。低风险的图片预热可以较早延迟；数据库迁移、身份认证等强不变量则不能靠放宽阈值绕过。

还要设置迟滞：进入保护模式和退出保护模式使用不同条件，避免一次成功后立即恢复全部模块，下一次又因同一问题回到保护模式。恢复可按“基础页面稳定 → 单个模块试开 → 观察成功 → 扩大恢复”推进，并始终给用户一个受控的“尝试正常启动”入口。

## 版本变化不能抹掉证据

升级到新 `versionCode` 后，旧版本失败样本不再直接触发新版本计划，但仍应保留在有界历史中，供回滚、同一 native 库版本或跨版本配置问题分析。

可采用以下命名空间：

```text
installationEpoch / versionCode / processRole / startupRoute / signature
```

这条键结构把安装、版本、进程、入口和问题签名分开。版本升级时关闭旧桶的决策权，而不是删除旧桶；若新旧版本使用相同的故障模块或远程配置，可以通过经过审核的规则继承计划。

## 多进程与并发启动

多进程应用最容易出现“主进程替子进程背锅”。需要遵守三点：

- 每个进程独立持有启动租约，`processName` 与 `processRole` 都写入；
- 只有明确的汇总 owner 能更新失败样本和降级计划；
- 独立服务或推送进程的死亡，默认只影响它负责的功能。

如果主进程和子进程近乎同时启动，不能用单个“当前 session”字段。每个租约都有自己的 `launchId`，系统退出历史也按进程名查询；聚合时再根据业务依赖关系判断是否属于同一用户操作。

进程仍存活时，其他进程不要仅凭租约文件判定它已失败。可结合文件 owner、进程存活检查和租约年龄排除并发启动，但进程存活检查也有竞态，只能作为辅助证据。

## WebView Renderer 退出属于页面级恢复

WebView renderer 通常运行在独立进程。`onRenderProcessGone()` 表示对应 renderer 已退出，不等于宿主应用发生 Java crash。处理顺序应是：

1. 停止继续使用受影响的 `WebView`；
2. 从视图树移除并销毁旧实例；
3. 在新的调用栈或调度点重建，避免回调内重入；
4. 使用受控状态恢复页面；
5. 同一页面或模块反复失败时，再选择 WebView 级降级计划。

不要在清理旧实例之前调用可能依赖 renderer 的方法，也不要无条件重放包含敏感参数的 URL。完整实现和 Android 17 边界见 20.10 节。renderer gone 可以影响 WebView 模块计划，但不能直接增加宿主主进程的崩溃循环次数。

## 观测与隐私

至少记录以下聚合指标：

- SafeMode 进入率，按版本、进程、启动路径和计划分组；
- 候选失败转为确认失败的比例；
- `ApplicationExitInfo` 匹配成功率、歧义率和 trace 可用率；
- 普通启动与降级启动的 `PROCESS_READY`、`INTERACTIVE` 成功率；
- 保护模式中的用户退出、手动重试和恢复成功率；
- 各退出原因被排除或转入其他治理路径的数量；
- 降级计划的误触发率和重复进入率。

本地与服务端都只上传稳定枚举、版本、模块 ID、签名哈希和受限堆栈。不要上传原始 URL、Intent extras、搜索词、订单、账号、剪贴板或页面正文。`processStateSummary` 的 128 字节限制不是隐私保护机制，内容仍要主动脱敏。

## 测试范围

单元测试应覆盖状态与证据的组合，而不是只测计数器：

- 旧租约处于各阶段时，Java crash、native crash、ANR、LMK、用户停止分别怎样分类；
- 墙钟前跳、后跳、设备重启和旧 elapsed 基准；
- 应用升级、降级、覆盖安装与安装时间变化；
- 同名进程的多条退出记录、记录重复消费和候选歧义；
- 租约文件为空、截断、格式版本未知和校验失败；
- 观察期成功、复发、计划过期和用户手动重试；
- 多进程并发写入与 owner 异常退出。

设备或集成测试还应注入以下故障：

| 故障 | 预期 |
| --- | --- |
| `Application.onCreate()` 的可选模块抛异常 | 下一次能选择对应模块计划 |
| JNI 初始化触发 native crash | 系统 tombstone 保留，下一次按进程和租约关联 |
| 主线程启动阶段阻塞 | ANR 证据进入补偿核对，不依赖当场写文件 |
| 用户从设置中强行停止 | 不计入崩溃循环 |
| 后台进程被内存压力回收 | 进入内存治理，不升级 crash 计划 |
| marker 写入时进程被杀 | 旧版或新版文件仍可解析，损坏时安全退化 |
| WebView renderer 反复退出 | 只触发页面或 WebView 模块计划 |
| 远程配置不可达 | 使用缓存配置或本地保守策略 |
| 降级启动连续成功 | 进入观察期，逐项恢复，不一次性全开 |

测试时不要只断言“进入了 SafeMode”，还要断言被禁用的范围、证据 ID、排除原因和恢复路径，避免一个宽泛开关掩盖错误归因。

## 源码核对点

- [`ApplicationExitInfo.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)：退出原因、时间戳、trace 与 API 37 ANR 信息的接口边界。
- [`ActivityManager.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java)：历史退出记录、`setProcessStateSummary()` 的 128 字节限制和 LMK 报告能力。
- [`Settings.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/provider/Settings.java)：`BOOT_COUNT` 的公开可读定义与版本边界。
- [`AtomicFile.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/util/AtomicFile.java)：`startWrite()`、`finishWrite()`、`failWrite()` 及调用方串行化要求。
- [`RuntimeInit.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)：Java 未捕获异常的预处理、上报与终止流程。
- [`ApplicationExitInfo` API 文档](https://developer.android.com/reference/android/app/ApplicationExitInfo)：公开 API 的版本边界与字段语义。
- [`ActivityManager` API 文档](https://developer.android.com/reference/android/app/ActivityManager)：历史退出记录和进程状态摘要的公开契约。
- [ANR 诊断文档](https://developer.android.com/topic/performance/vitals/anr)：ANR 类型、常见原因和诊断入口。
- [Linux `vmscan.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)：内核内存回收背景；应用侧仍以 Android framework 暴露的退出原因作为契约。

## 复核清单

- [ ] 是否先读取旧租约，再写本轮租约？
- [ ] 是否把残留 marker 当成候选证据，而不是崩溃结论？
- [ ] 是否按版本、安装、进程、入口和 `launchId` 关联退出记录？
- [ ] 是否区分墙钟、elapsed 时间和设备重启？
- [ ] 是否把 trace 复制与解析移出冷启动主线程？
- [ ] 是否排除用户停止、包更新、权限变化和无法归因的退出？
- [ ] 是否把 LMK、资源限制和依赖进程死亡导向各自的降级计划？
- [ ] 是否保留系统 Java crash 与 debuggerd/tombstoned 处理链路？
- [ ] 是否由单一 owner 写失败样本，多进程各自保存租约？
- [ ] 是否只关闭与故障相关的可选模块？
- [ ] 是否禁止自动清数据、跳过安全校验和绕过强制迁移？
- [ ] 是否设置观察期、迟滞、过期和手动重试？
- [ ] 是否保留旧版本的有界诊断证据？
- [ ] 是否对所有持久化、trace 和上报内容做限长与脱敏？

SafeMode 的价值不只在于拦住一次崩溃，更在于证据不完整时仍能做可解释、可逆、范围受控的启动决策。租约描述进度，系统退出历史补充原因，降级计划限制影响面；三者分开，才能让保护机制本身保持可诊断。
