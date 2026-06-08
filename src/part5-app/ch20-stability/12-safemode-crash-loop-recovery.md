---
title: "SafeMode 崩溃循环判定与启动补偿链路"
chapter: "20.12"
section: "20.12"
status: finalized
drafted_date: "2026-05-16"
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-06-09"
last_verified_against: "AOSP android-16.0.0_r4 / developer.android.com; Android 17 tag not public on android.googlesource at audit time"
confidence: medium
sources:
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 39.md"
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
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task6_result: pass-light-edit
reviewed_date: "2026-05-16"
reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-05-16"
last_task6_at: "2026-05-16T15:12:00+08:00"
last_task6_audit: "2026-06-08"
task6_review_notes: "2026-05-16 task6 review: 完成 L1/L2 轻修 4 处；无 Task2B 回炉项，进入 Task9 技术审查。"
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_reviewed_date: 2026-05-16
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-09T04:26:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-09-04-audit.md"
auto_promoted_by: task9-deep-tech-review
auto_promoted_at: "2026-05-16T15:38:55+08:00"
task2b_state: "fixed"
last_task9_audit: "2026-06-09"
last_task9_audit_log: "logs/deep-review/2026-06-09-04-audit.md"
last_task9_autofix_at: "2026-06-09"
task9_review_notes: "2026-06-09 Task9 闲时抽检：auto-fixed。AOSP android-17.0.0_r1 未在 android.googlesource 公开；本轮将 AtomicFile / RuntimeInit / ActivityManager / ApplicationExitInfo / WebView 相关源码锚点从 AOSP master 收敛到已复核的 android-16.0.0_r4，并将适用上限暂回退到 Android 16。P0 0 / P1 1（已修）/ P2 1（日志记录）。"
---

# 20.12 SafeMode 崩溃循环判定与启动补偿链路

20.7 节已经给出异常处理架构里的 SafeMode 分层，本节补齐工程落点：怎样判断启动期崩溃循环，怎样用启动 marker 和 `ApplicationExitInfo` 补偿缺失现场，怎样把 WebView Renderer 退出从进程级崩溃里拆出来。

这里的 SafeMode 指 App 自己的保护模式，不是 Android 系统安全模式。它的目标很窄：当同一版本、同一进程、同一启动路径反复失败时，让下一次启动跳过高风险模块，保住基础页面和修复入口。

## 崩溃循环的状态机设计

启动崩溃循环不能只靠“最近崩溃次数”判断。合理的状态机要把启动状态、退出原因、版本边界和恢复动作放在一起，否则很容易把用户强杀、系统低内存回收、后台进程退出误判成启动崩溃。

一个可执行的最小状态机如下：

| 状态 | 写入时机 | 下次启动的解释 |
| --- | --- | --- |
| `idle` | 正常退出 SafeMode 判定后 | 没有待处理启动失败 |
| `launching` | `Application.attachBaseContext()` 或主进程 `onCreate()` 开头 | 上一次启动没有走到成功标记，需要结合退出原因判断 |
| `started` | 首个可交互页面 `onResume()` 后，或首页首帧完成后 | 上一次启动通过关键路径，不计入启动失败 |
| `degraded` | 命中 SafeMode 规则并打开本地降级开关 | 本次启动应跳过高风险模块 |
| `recovered` | 同一版本连续若干次冷启动成功 | 可退出保护模式，保留一段观察窗口 |

判定入口读取的是“上一轮启动留下的 marker”。如果 marker 停在 `launching`，说明进程没有走到团队定义的启动成功点；这时再看退出证据：Java Crash、Native Crash、ANR、LMK、`SIGKILL`、WebView Renderer gone。只有 marker 和退出证据能对上，才把它计入崩溃循环。

推荐把计数维度限定到：`versionCode + processName + startupRoute + crashSignature`。`startupRoute` 可以是首页、登录页、支付回调、Push 拉起等枚举；`crashSignature` 对 Java 取异常类型和前几帧，对 Native 取 signal、so 名、符号化后的函数或 pc bucket，对 ANR 取主线程阻塞摘要。这样做的目的不是做服务端级聚类，而是避免“不同问题凑够次数”后错误进入 SafeMode。

阈值要同时有本地默认值和远程配置：

| 规则 | 示例值 | 适用场景 |
| --- | --- | --- |
| 连续启动失败 | 同一版本 3 次冷启动未完成 | 首页初始化、动态配置、数据库迁移失败 |
| 短窗口重复失败 | 10 分钟内同一签名 2 次 | 灰度版本集中爆发 |
| 单次高危失败 | Native crash / ANR 发生在启动 marker 未完成前 | 无法保证 handler 写完整样本的场景 |
| 远程强制降级 | 服务端下发 feature kill switch | 已确认某模块线上故障 |

本地规则只用于保命，不能替代发布平台和 Crash 看板。20.6 节的启动崩溃率、重复崩溃率和灰度门禁仍然是团队层面的判断依据。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md]

## 启动 marker 的写入、完成与清理

启动 marker 要在高风险 SDK 初始化之前写入。主进程建议放在 `Application.attachBaseContext()` 或 `onCreate()` 的第一段；多进程应用要按进程分别写，文件名里带 `processName` 或进程角色，避免推送进程、WebView 预加载进程和主进程互相覆盖。

marker 字段只保留判定所需的信息：

| 字段 | 用途 | 边界 |
| --- | --- | --- |
| `session_id` | 关联本次启动、本地 crash envelope 和后续补偿记录 | UUID 或递增号，不含用户标识 |
| `version_code` / `version_name` | 版本升级后切断旧计数 | 版本升级可清理旧 SafeMode 状态 |
| `process_name` / `pid` | 区分主进程与子进程 | pid 只能作为辅助，进程重启后会变化 |
| `started_elapsed_ms` / `started_wall_time_ms` | 判断 marker 是否过期，并与 `ApplicationExitInfo.timestamp` 匹配 | `elapsedRealtime()` 用于本地过期判断，墙钟时间只用于系统记录匹配 |
| `startup_route` | 区分不同拉起路径 | 只写枚举，不写 URL、订单号、搜索词 |
| `stage` | `launching`、`started`、`degraded` 等状态 | 状态变化必须原子落盘 |
| `safe_mode_level` | 本次是否降级启动 | 用于恢复后复盘 |

这段示例代码表达 marker 的原子写入方式，重点看 `startWrite()`、`finishWrite()` 和失败回滚三步。

```kotlin
// 示意代码：启动 marker 持久化。生产环境还要补进程锁、序列化异常处理和日志脱敏。
class LaunchMarkerStore(private val file: File) {
    private val atomicFile = AtomicFile(file)

    fun write(marker: LaunchMarker) {
        var stream: FileOutputStream? = null
        try {
            stream = atomicFile.startWrite()
            stream.write(marker.toJsonBytes())
            atomicFile.finishWrite(stream)
        } catch (t: Throwable) {
            if (stream != null) {
                atomicFile.failWrite(stream)
            }
            throw t
        }
    }
}
```

AOSP `AtomicFile` 的 `finishWrite()` 会对输出流做 sync，关闭后把 `.new` 文件 rename 到目标文件；`failWrite()` 会 sync、关闭并删除 `.new` 文件。应用侧如果不用 `AtomicFile`，也要遵守同一套协议：写临时文件、`fsync` 文件内容、关闭、rename 到正式文件，必要时再处理父目录持久化。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/android/util/AtomicFile.java]

启动成功点不要放得太早。`Application.onCreate()` 结束只说明初始化函数返回了，不代表用户能进入页面。常见做法是设两个标记：

- `process_started`：`Application.onCreate()` 完成后写入，说明基础初始化通过。
- `interactive_started`：首个关键 Activity `onResume()` 后，或首页首帧 / 首屏数据达到可交互条件后写入，说明启动体验通过。

SafeMode 判定应以 `interactive_started` 为主。只写 `process_started` 会漏掉首页容器、WebView 首屏、数据库迁移后的页面恢复等启动后半段问题。

清理规则也要明确：同一版本连续成功 N 次后清理失败计数；版本升级、安装来源变化、ABI 变化后清理旧签名；用户清除数据后自然重置；远程配置命中新开关时只清理对应模块，不要把所有历史证据抹掉。

## Java / Native / ANR / LMK 的证据差异

SafeMode 的误判大多来自证据混用。Java Crash、Native Crash、ANR 和 LMK 都会让启动中断，但能拿到的证据、写入时机和可信度不同。

| 退出类型 | 当场证据 | 下次启动补偿 | SafeMode 使用方式 |
| --- | --- | --- | --- |
| Java Crash | `UncaughtExceptionHandler` 可写异常类型、线程、栈摘要 | `ApplicationExitInfo.REASON_CRASH` | marker 未完成且栈签名稳定时计入 |
| Native Crash | 信号处理器只能做极小动作；系统 tombstone 更可靠 | API 31+ 可通过 `getTraceInputStream()` 读取 tombstone protobuf | 用 signal、so、pc bucket 归因，业务上下文从 marker 补 |
| ANR | 进程通常已经无法在主线程执行补救逻辑 | API 30+ `REASON_ANR`，trace 可能可读 | 只在启动 marker 未完成或前台关键路径阻塞时计入 |
| LMK / 低内存 kill | App 内 handler 不会执行 | 支持设备返回 `REASON_LOW_MEMORY`；不支持时可能表现为 `REASON_SIGNALED` + `SIGKILL` | 只作为内存降级依据，通常不直接计入崩溃循环 |
| 用户强杀 / 任务移除 | 没有 crash 现场 | `REASON_USER_REQUESTED`、`REASON_USER_STOPPED` 或相关 subreason | 排除，不触发 SafeMode |

Java Crash 的系统默认路径在 `RuntimeInit` 中：`LoggingHandler` 记录 fatal exception，`KillApplicationHandler` 设置 `mCrashing` 防止重入，调用 `ActivityManager` 上报后执行 `killProcess()` 和 `System.exit(10)`。应用自定义 handler 要做的不是“救回”进程，而是在系统终止前写下足够小的 envelope。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/com/android/internal/os/RuntimeInit.java][结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控：实现自定义 Crash 处理器.md]

Native Crash 的证据重心在系统侧。参考书把 Native Crash 拆成信号监听和 backtrace 获取两段，这个拆法适合作为 APM 结构参考；生产环境里，信号处理器不应做复杂序列化、锁、分配内存或网络请求。SafeMode 只需要拿到最小摘要，完整 tombstone 和符号化交给 20.3、26.2 的链路处理。[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控：为我们应用插上监控 Native Crash 的电子眼.md][结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Backtrace：Native 堆栈信息获取.md]

ANR 和 LMK 更依赖下次启动补偿。Android Vitals 文档也把 `ApplicationExitInfo` 列为诊断 ANR 的可用工具；它能说明进程为何退出，但不能自动说明哪段业务逻辑导致失败。要把 `processStateSummary`、启动 marker、前台页面、最近阶段事件拼起来，才能形成 SafeMode 判定证据。[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

## ApplicationExitInfo 的补偿入口

`ApplicationExitInfo` 从 Android 11（API 30）开始可用，适合在新进程启动早期读取上一进程的系统退出记录。`ActivityManager.getHistoricalProcessExitReasons(packageName, pid, maxNum)` 返回匹配记录，顺序是从近到远；系统保存的是环形缓冲，旧记录可能被覆盖。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/android/app/ActivityManager.java]

`ApplicationExitInfo` 里与 SafeMode 相关的字段主要有四类：

| 字段 / API | 用途 | 边界 |
| --- | --- | --- |
| `reason` / `status` / `importance` | 判断 Java Crash、Native Crash、ANR、LMK、用户请求等退出类型 | reason 只能说明系统分类，不能替代业务归因 |
| `timestamp` / `pid` / `processName` | 与启动 marker 匹配 | pid 复用风险低但仍要结合时间窗口 |
| `getProcessStateSummary()` | 读取进程死亡前写入的 128 字节状态摘要 | 官方要求不要写 PII / SPII，只适合放枚举和短摘要 |
| `getTraceInputStream()` | 读取 ANR trace；API 31+ Native tombstone protobuf | trace 保存在全局环形缓冲里，可能返回 null |

AOSP 注释说明，`getTraceInputStream()` 通常在 `REASON_ANR` 时可用；从 API 31 开始，`REASON_CRASH_NATIVE` 可返回 tombstone protobuf；由于 trace 存在独立的全局环形缓冲里，可能被新的 crash 覆盖，因此调用方必须处理 null。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/android/app/ApplicationExitInfo.java][已验证: 官方文档, developer.android.com/ndk/guides/debug]

这段示例代码展示补偿读取的最小逻辑，重点看“只处理 marker 时间窗口内的退出记录”。

```kotlin
// 示意代码：下次启动补偿读取。生产环境要补采样、异常保护和上传队列。
fun collectExitCompensation(
    context: Context,
    previousMarker: LaunchMarker,
    maxRecords: Int = 8
): List<ExitEvidence> {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return emptyList()

    val am = context.getSystemService(ActivityManager::class.java)
    return am.getHistoricalProcessExitReasons(context.packageName, 0, maxRecords)
        .asSequence()
        .filter { info -> info.processName == previousMarker.processName }
        .filter { info -> info.timestamp >= previousMarker.startedWallTimeMs }
        .map { info ->
            ExitEvidence(
                reason = info.reason,
                status = info.status,
                importance = info.importance,
                processStateSummary = info.processStateSummary,
                hasTrace = try {
                    info.traceInputStream?.use { true } ?: false
                } catch (_: IOException) {
                    false
                }
            )
        }
        .toList()
}
```

补偿逻辑不要把“最近一条退出记录”直接绑定到“上一轮启动失败”。多进程 App、外部 service、后台进程、预加载进程都可能留下记录。稳妥做法是按 `processName`、marker 时间、`session_id` 摘要和启动阶段一起匹配；匹配不上就只上报，不触发 SafeMode。

LMK 还要判断设备是否支持低内存 kill 上报。AOSP `ActivityManager.isLowMemoryKillReportSupported()` 读取 `persist.sys.lmk.reportkills`；不支持时，内存压力下的 kill 可能退化为 `REASON_SIGNALED` 和 `SIGKILL`。这类样本可以推动内存预算和 WebView 降级，不能直接等同于代码崩溃。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/android/app/ActivityManager.java]

## WebView renderer 退出的单独处理

WebView Renderer 退出要从 App 进程崩溃里拆出来。Renderer 属于 WebView 多进程模型的一部分，它退出时宿主进程可以继续运行；只有没有正确处理 `onRenderProcessGone()`，或者回调返回 `false`，宿主应用才会崩溃或被系统结束。

AOSP `WebViewClient.onRenderProcessGone()` 的注释给出三个处理契约：多个 WebView 可能共用一个 Renderer，受影响的 WebView 会分别收到回调；回调参数里的 `view` 已不可继续使用；宿主要把它从 View 树移除并清理所有引用。默认实现返回 `false`。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/android/webkit/WebViewClient.java]

这段示例代码把 Renderer 退出记录成页面级证据，而不是直接升级成进程级 SafeMode。

```kotlin
class RecoverableWebViewClient(
    private val recorder: RendererGoneRecorder,
    private val container: ViewGroup
) : WebViewClient() {
    override fun onRenderProcessGone(
        view: WebView,
        detail: RenderProcessGoneDetail
    ): Boolean {
        recorder.record(
            didCrash = detail.didCrash(),
            priorityAtExit = detail.rendererPriorityAtExit()
        )
        container.removeView(view)
        view.destroy()
        showFallbackPage()
        return true
    }
}
```

SafeMode 的策略应分两层：

- 单个页面 Renderer gone：页面级兜底，重建 WebView 或展示轻量页，不影响整个 App。
- 启动期反复 Renderer gone：只关闭 H5 首页、WebView 池、预加载、离线包注入或高风险 JS Bridge，不要把所有 Native / Java 功能一起关掉。

`WebViewRenderProcessClient` 提供 Renderer 无响应和恢复回调，最小无响应回调间隔为 5 秒；应用可以选择终止 Renderer，但必须同时处理所有相关 WebView 的 `onRenderProcessGone()`，否则会导致应用终止。这个 API 适合提前降载，不适合替代退出后的恢复路径。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/android/webkit/WebViewRenderProcessClient.java]

20.10 节已经展开 WebView Renderer OOM 与白屏恢复，本节只把它接入 SafeMode 证据链：Renderer gone 是页面 / 容器证据，只有当它让宿主进程退出，或启动 marker 多次停在同一 H5 路径上，才进入进程级保护。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 39.md]

## SafeMode 降级动作与恢复条件

SafeMode 的动作要按故障半径分级。降级过重会把可恢复的小问题变成“应用不可用”；降级过轻又拦不住启动崩溃。

| 等级 | 触发条件 | 动作 | 恢复条件 |
| --- | --- | --- | --- |
| L1 模块降级 | 某 SDK / 实验 / 页面簇重复失败 | 关闭实验、延迟 SDK、禁用预加载 | 同一版本成功启动 3 次，或远程开关确认问题关闭 |
| L2 启动路径降级 | 首页、登录页、H5 容器启动期失败 | 进入轻量首页、跳过复杂容器、关闭 WebView 池 | 成功进入轻量首页并完成修复配置拉取 |
| L3 保护模式 | 同一版本连续启动失败，无法确认模块 | 只初始化账号、配置、修复、上报、基础 UI | 版本升级、补丁命中，或本地连续成功启动达到阈值 |
| L4 停止自拉起 | 子进程 / 服务反复崩溃 | 暂停后台服务、指数退避重启 | 远程配置或下次版本恢复 |

降级开关必须本地可读。进入崩溃循环的设备可能离线，不能依赖服务端实时返回。远程配置只能收紧或放宽本地规则，不能成为唯一判定来源。

恢复条件要比进入条件更保守。一次成功启动只说明当前路径通过，不说明问题消失。推荐同时满足：同一版本连续成功启动 N 次、没有新的同签名失败、修复配置版本已更新、关键页面进入过一次。版本升级可以清理旧签名，但要保留“升级前进入过 SafeMode”的事件，方便灰度复盘。

用户强杀、系统更新、权限变更、包状态变化、任务移除不应触发 SafeMode。Android 13 已有 `REASON_USER_STOPPED`，Android 14 起新增 `REASON_PACKAGE_STATE_CHANGE`，并继续细化 reason / subreason；低版本或厂商 ROM 上拿不到完整分类时，宁可只上报，也不要按崩溃处理。[已验证: AOSP android-16.0.0_r4, frameworks/base/core/java/android/app/ApplicationExitInfo.java]

SafeMode 事件本身也要进入 Crash 上报体系。建议至少包含：进入等级、触发规则、上一轮 marker、退出原因、关联 issue、被关闭模块、恢复条件、是否成功退出。26.2 节的 Crash 上报体系负责聚合和告警，20.8 节负责把重复样本归并成可处理 issue。

## 文件落盘协议：tmp、fsync、rename

启动 marker 和 crash envelope 都属于“崩溃前关键写入”，文件协议要按最坏情况设计：进程可能在写入中被 kill，磁盘可能只落了一半，另一个进程可能同时写。

推荐协议：

1. 写入独立临时文件，例如 `marker.json.new`。
2. 写完后对文件内容 `fsync`。
3. 关闭文件描述符。
4. rename 到正式文件名。
5. 下次读取时忽略残留 `.new`，必要时保留 `.bak` 做恢复。

Android `AtomicFile` 已覆盖主要路径；多进程写 marker 时要加文件锁，或按进程拆文件后由主进程汇总。Crash handler 里不要争用全局锁；锁被崩溃线程持有时，handler 再尝试加锁会卡死。

Native signal handler 的落盘边界更窄。安全做法是提前准备固定大小缓冲区和文件描述符，崩溃时只写最小二进制摘要；完整日志、符号化、压缩和上传都放到下次启动。

## 版本升级与用户强杀的排除规则

SafeMode 需要一组排除规则，否则会把正常生命周期当成故障：

- 版本升级：`versionCode` 变化后，旧版本的启动失败不再累计到新版本；但升级前的失败事件要上报。
- 用户强杀 / 从最近任务划掉：按用户行为处理，不进入保护模式。
- 权限变更和包状态变化：系统可能重启进程，按环境变化处理。
- 系统低内存：只在启动 marker 未完成且同一路径多次发生时触发内存降级；单次后台 LMK 不触发。
- 外部 service / SDK sandbox 退出：只能影响对应依赖模块，不能直接关闭主进程功能。

排除规则的落点仍然是 marker 匹配。没有 marker，只有退出原因，就上报观察；有 marker，但版本、进程、时间窗口对不上，也只上报观察。SafeMode 的判定应宁可少触发，也不要把用户带进错误的降级状态。

## 小结

SafeMode 能否拦住崩溃循环，取决于三件事：启动 marker 写得足够早，退出证据补得足够准，降级动作足够窄。Java Crash、Native Crash、ANR、LMK、WebView Renderer gone 都能打断启动，但它们不是同一种故障；统一进入“保护模式”之前，必须先按证据来源分层。

工程上可以从最小路径开始：主进程 marker、Java Crash envelope、API 30+ `ApplicationExitInfo` 补偿、WebView `onRenderProcessGone()` 页面级记录、L1/L2 两档降级。等这条路径稳定后，再补 Native 最小摘要、多进程汇总、远程阈值和发布平台联动。
