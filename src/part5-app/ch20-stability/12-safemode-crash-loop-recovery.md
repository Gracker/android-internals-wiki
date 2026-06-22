---

title: "SafeMode 崩溃循环判定与启动补偿链路"
chapter: "20.12"
section: "20.12"
status: "ready-for-review"
drafted_date: "2026-05-16"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-22"
last_verified_against: "AOSP android-17.0.0_r1 / developer.android.com"
confidence: medium
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
pipeline_stage: "task6_pending"
task6_state: "revisiting"
task6_result: "pass-light-edit"
reviewed_date: "2026-06-22"
reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-06-22"
last_task6_at: "2026-06-22T11:11:00+08:00"
last_task6_audit: "2026-06-22"
task6_review_notes: "2026-06-22 task6 review: 无 L1/L2 问题需修复;发现 L3/L4 问题需 Task2B 处理。内容深度和工程实践经验需补充。"
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-22"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-22T11:30:21+08:00"
last_task9_review_log: "logs/deep-review/2026-06-22-11-deep-review.md"
auto_promoted_by: task9-deep-tech-review
auto_promoted_at: "2026-05-16T15:38:55+08:00"
task2b_state: "fixed"
last_task9_audit: "2026-06-09"
last_task9_audit_log: "logs/deep-review/2026-06-09-04-audit.md"
last_task9_autofix_at: "2026-06-22"
task9_review_notes: "2026-06-22 Task9 复审:auto-fixed。修正 tombstoned android-17 O_TMPFILE/linkat 源码锚点、AtomicFile fsync 注释、RecoverySystem BCB 写入链路、AppExitInfoTracker 查询维度表述；无新增 queue 技术回炉项。"
task2b_result: "fixed"
last_task2b_main_at: "2026-06-22T10:50:00+08:00"
last_task2b_lite_at: "2026-06-22"
---

# 20.12 SafeMode 崩溃循环判定与启动补偿链路

20.7 节已经给出异常处理架构里的 SafeMode 分层,本节补齐工程落点:怎样判断启动期崩溃循环,怎样用启动 marker 和 `ApplicationExitInfo` 补偿缺失现场,怎样把 WebView Renderer 退出从进程级崩溃里拆出来。

这里的 SafeMode 指 App 自己的保护模式,不是 Android 系统安全模式。它的目标很窄:当同一版本、同一进程、同一启动路径反复失败时,让下一次启动跳过高风险模块,保住基础页面和修复入口。

## 崩溃循环的状态机设计

启动崩溃循环不能只靠"最近崩溃次数"判断。合理的状态机要把启动状态、退出原因、版本边界和恢复动作放在一起,否则很容易把用户强杀、系统低内存回收、后台进程退出误判成启动崩溃。

一个可执行的最小状态机如下:

| 状态 | 写入时机 | 下次启动的解释 |
| --- | --- | --- |
| `idle` | 正常退出 SafeMode 判定后 | 没有待处理启动失败 |
| `launching` | `Application.attachBaseContext()` 或主进程 `onCreate()` 开头 | 上一次启动没有走到成功标记,需要结合退出原因判断 |
| `started` | 首个可交互页面 `onResume()` 后,或首页首帧完成后 | 上一次启动通过关键路径,不计入启动失败 |
| `degraded` | 命中 SafeMode 规则并打开本地降级开关 | 本次启动应跳过高风险模块 |
| `recovered` | 同一版本连续若干次冷启动成功 | 可退出保护模式,保留一段观察窗口 |

判定入口读取的是"上一轮启动留下的 marker"。如果 marker 停在 `launching`,说明进程没有走到团队定义的启动成功点;这时再看退出证据:Java Crash、Native Crash、ANR、LMK、`SIGKILL`、WebView Renderer gone。只有 marker 和退出证据能对上,才把它计入崩溃循环。

推荐把计数维度限定到:`versionCode + processName + startupRoute + crashSignature`。`startupRoute` 可以是首页、登录页、支付回调、Push 拉起等枚举;`crashSignature` 对 Java 取异常类型和前几帧,对 Native 取 signal、so 名、符号化后的函数或 pc bucket,对 ANR 取主线程阻塞摘要。这样做的目的不是做服务端级聚类,而是避免"不同问题凑够次数"后错误进入 SafeMode。

阈值要同时有本地默认值和远程配置:

| 规则 | 示例值 | 适用场景 |
| --- | --- | --- |
| 连续启动失败 | 同一版本 3 次冷启动未完成 | 首页初始化、动态配置、数据库迁移失败 |
| 短窗口重复失败 | 10 分钟内同一签名 2 次 | 灰度版本集中爆发 |
| 单次高危失败 | Native crash / ANR 发生在启动 marker 未完成前 | 无法保证 handler 写完整样本的场景 |
| 远程强制降级 | 服务端下发 feature kill switch | 已确认某模块线上故障 |

本地规则只用于保命,不能替代发布平台和 Crash 看板。20.6 节的启动崩溃率、重复崩溃率和灰度门禁仍然是团队层面的判断依据。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 2.md]

## 启动 marker 的写入、完成与清理

启动 marker 要在高风险 SDK 初始化之前写入。主进程建议放在 `Application.attachBaseContext()` 或 `onCreate()` 的第一段;多进程应用要按进程分别写,文件名里带 `processName` 或进程角色,避免推送进程、WebView 预加载进程和主进程互相覆盖。

marker 字段只保留判定所需的信息:

| 字段 | 用途 | 边界 |
| --- | --- | --- |
| `session_id` | 关联本次启动、本地 crash envelope 和后续补偿记录 | UUID 或递增号,不含用户标识 |
| `version_code` / `version_name` | 版本升级后切断旧计数 | 版本升级可清理旧 SafeMode 状态 |
| `process_name` / `pid` | 区分主进程与子进程 | pid 只能作为辅助,进程重启后会变化 |
| `started_elapsed_ms` / `started_wall_time_ms` | 判断 marker 是否过期,并与 `ApplicationExitInfo.timestamp` 匹配 | `elapsedRealtime()` 用于本地过期判断,墙钟时间只用于系统记录匹配 |
| `startup_route` | 区分不同拉起路径 | 只写枚举,不写 URL、订单号、搜索词 |
| `stage` | `launching`、`started`、`degraded` 等状态 | 状态变化必须原子落盘 |
| `safe_mode_level` | 本次是否降级启动 | 用于恢复后复盘 |

这段示例代码表达 marker 的原子写入方式,重点看 `startWrite()`、`finishWrite()` 和失败回滚三步。

```kotlin
// 示意代码:启动 marker 持久化。生产环境还要补进程锁、序列化异常处理和日志脱敏。
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

AOSP `AtomicFile` 的 `finishWrite()` 会对输出流做 sync,关闭后把 `.new` 文件 rename 到目标文件;`failWrite()` 会 sync、关闭并删除 `.new` 文件。应用侧如果不用 `AtomicFile`,也要遵守同一套协议:写临时文件、`fsync` 文件内容、关闭、rename 到正式文件,必要时再处理父目录持久化。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/util/AtomicFile.java]

启动成功点不要放得太早。`Application.onCreate()` 结束只说明初始化函数返回了,不代表用户能进入页面。常见做法是设两个标记:

- `process_started`:`Application.onCreate()` 完成后写入,说明基础初始化通过。
- `interactive_started`:首个关键 Activity `onResume()` 后,或首页首帧 / 首屏数据达到可交互条件后写入,说明启动体验通过。

SafeMode 判定应以 `interactive_started` 为主。只写 `process_started` 会漏掉首页容器、WebView 首屏、数据库迁移后的页面恢复等启动后半段问题。

清理规则也要明确:同一版本连续成功 N 次后清理失败计数;版本升级、安装来源变化、ABI 变化后清理旧签名;用户清除数据后自然重置;远程配置命中新开关时只清理对应模块,不要把所有历史证据抹掉。

## Java / Native / ANR / LMK 的证据差异

SafeMode 的误判大多来自证据混用。Java Crash、Native Crash、ANR 和 LMK 都会让启动中断，但能拿到的证据、写入时机和可信度不同。

| 退出类型 | 当场证据 | 下次启动补偿 | SafeMode 使用方式 |
| --- | --- | --- | --- |
| Java Crash | `UncaughtExceptionHandler` 可写异常类型、线程、栈摘要 | `ApplicationExitInfo.REASON_CRASH` | marker 未完成且栈签名稳定时计入 |
| Native Crash | 信号处理器只能做极小动作;系统 tombstone 更可靠 | API 31+ 可通过 `getTraceInputStream()` 读取 tombstone protobuf | 用 signal、so、pc bucket 归因,业务上下文从 marker 补 |
| ANR | 进程通常已经无法在主线程执行补救逻辑 | API 30+ `REASON_ANR`,trace 可能可读 | 只在启动 marker 未完成或前台关键路径阻塞时计入 |
| LMK / 低内存 kill | App 内 handler 不会执行 | 支持设备返回 `REASON_LOW_MEMORY`;不支持时可能表现为 `REASON_SIGNALED` + `SIGKILL` | 只作为内存降级依据,通常不直接计入崩溃循环 |
| 用户强杀 / 任务移除 | 没有 crash 现场 | `REASON_USER_REQUESTED`、`REASON_USER_STOPPED` 或相关 subreason | 排除,不触发 SafeMode |

Java Crash 的系统默认路径在 `RuntimeInit` 中:`LoggingHandler` 记录 fatal exception,`KillApplicationHandler` 设置 `mCrashing` 防止重入,调用 `ActivityManager` 上报后执行 `killProcess()` 和 `System.exit(10)`。应用自定义 handler 要做的不是"救回"进程,而是在系统终止前写下足够小的 envelope。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/com/android/internal/os/RuntimeInit.java][结构参考: Clippings/Android 应用稳定性剖析与优化 - Java Crash 监控:实现自定义 Crash 处理器.md]

Native Crash 的证据重心在系统侧。参考书把 Native Crash 拆成信号监听和 backtrace 获取两段,这个拆法适合作为 APM 结构参考;生产环境里,信号处理器不应做复杂序列化、锁、分配内存或网络请求。SafeMode 只需要拿到最小摘要,完整 tombstone 和符号化交给 20.3、26.2 的链路处理。[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Crash 监控:为我们应用插上监控 Native Crash 的电子眼.md][结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Backtrace:Native 堆栈信息获取.md]

ANR 和 LMK 更依赖下次启动补偿。Android Vitals 文档也把 `ApplicationExitInfo` 列为诊断 ANR 的可用工具;它能说明进程为何退出,但不能自动说明哪段业务逻辑导致失败。要把 `processStateSummary`、启动 marker、前台页面、最近阶段事件拼起来,才能形成 SafeMode 判定证据。[已验证: 官方文档, developer.android.com/topic/performance/vitals/anr]

## ApplicationExitInfo 的补偿入口

`ApplicationExitInfo` 从 Android 11(API 30)开始可用,适合在新进程启动早期读取上一进程的系统退出记录。`ActivityManager.getHistoricalProcessExitReasons(packageName, pid, maxNum)` 返回匹配记录,顺序是从近到远;系统保存的是环形缓冲,旧记录可能被覆盖。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ActivityManager.java]

`ApplicationExitInfo` 里与 SafeMode 相关的字段主要有四类:

| 字段 / API | 用途 | 边界 |
| --- | --- | --- |
| `reason` / `status` / `importance` | 判断 Java Crash、Native Crash、ANR、LMK、用户请求等退出类型 | reason 只能说明系统分类,不能替代业务归因 |
| `timestamp` / `pid` / `processName` | 与启动 marker 匹配 | pid 复用风险低但仍要结合时间窗口 |
| `getProcessStateSummary()` | 读取进程死亡前写入的 128 字节状态摘要 | 官方要求不要写 PII / SPII,只适合放枚举和短摘要 |
| `getTraceInputStream()` | 读取 ANR trace;API 31+ Native tombstone protobuf | trace 保存在全局环形缓冲里,可能返回 null |

AOSP 注释说明,`getTraceInputStream()` 通常在 `REASON_ANR` 时可用;从 API 31 开始,`REASON_CRASH_NATIVE` 可返回 tombstone protobuf;由于 trace 存在独立的全局环形缓冲里,可能被新的 crash 覆盖,因此调用方必须处理 null。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ApplicationExitInfo.java][已验证: 官方文档, developer.android.com/ndk/guides/debug]

这段示例代码展示补偿读取的最小逻辑,重点看"只处理 marker 时间窗口内的退出记录"。

```kotlin
// 示意代码:下次启动补偿读取。生产环境要补采样、异常保护和上传队列。
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

补偿逻辑不要把"最近一条退出记录"直接绑定到"上一轮启动失败"。多进程 App、外部 service、后台进程、预加载进程都可能留下记录。稳妥做法是按 `processName`、marker 时间、`session_id` 摘要和启动阶段一起匹配;匹配不上就只上报,不触发 SafeMode。

LMK 还要判断设备是否支持低内存 kill 上报。AOSP `ActivityManager.isLowMemoryKillReportSupported()` 读取 `persist.sys.lmk.reportkills`;不支持时,内存压力下的 kill 可能退化为 `REASON_SIGNALED` 和 `SIGKILL`。这类样本可以推动内存预算和 WebView 降级,不能直接等同于代码崩溃。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ActivityManager.java]

## WebView renderer 退出的单独处理

WebView Renderer 退出要从 App 进程崩溃里拆出来。Renderer 属于 WebView 多进程模型的一部分,它退出时宿主进程可以继续运行;只有没有正确处理 `onRenderProcessGone()`,或者回调返回 `false`,宿主应用才会崩溃或被系统结束。

AOSP `WebViewClient.onRenderProcessGone()` 的注释给出三个处理契约:多个 WebView 可能共用一个 Renderer,受影响的 WebView 会分别收到回调;回调参数里的 `view` 已不可继续使用;宿主要把它从 View 树移除并清理所有引用。默认实现返回 `false`。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebViewClient.java]

这段示例代码把 Renderer 退出记录成页面级证据,而不是直接升级成进程级 SafeMode。

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

SafeMode 的策略应分两层:

- 单个页面 Renderer gone:页面级兜底,重建 WebView 或展示轻量页,不影响整个 App。
- 启动期反复 Renderer gone:只关闭 H5 首页、WebView 池、预加载、离线包注入或高风险 JS Bridge,不要把所有 Native / Java 功能一起关掉。

`WebViewRenderProcessClient` 提供 Renderer 无响应和恢复回调,最小无响应回调间隔为 5 秒;应用可以选择终止 Renderer,但必须同时处理所有相关 WebView 的 `onRenderProcessGone()`,否则会导致应用终止。这个 API 适合提前降载,不适合替代退出后的恢复路径。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/webkit/WebViewRenderProcessClient.java]

20.10 节已经展开 WebView Renderer OOM 与白屏恢复,本节只把它接入 SafeMode 证据链:Renderer gone 是页面 / 容器证据,只有当它让宿主进程退出,或启动 marker 多次停在同一 H5 路径上,才进入进程级保护。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪?-Android开发高手课-极客时间 39.md]

## SafeMode 降级动作与恢复条件

SafeMode 的动作要按故障半径分级。降级过重会把可恢复的小问题变成"应用不可用";降级过轻又拦不住启动崩溃。

| 等级 | 触发条件 | 动作 | 恢复条件 |
| --- | --- | --- | --- |
| L1 模块降级 | 某 SDK / 实验 / 页面簇重复失败 | 关闭实验、延迟 SDK、禁用预加载 | 同一版本成功启动 3 次,或远程开关确认问题关闭 |
| L2 启动路径降级 | 首页、登录页、H5 容器启动期失败 | 进入轻量首页、跳过复杂容器、关闭 WebView 池 | 成功进入轻量首页并完成修复配置拉取 |
| L3 保护模式 | 同一版本连续启动失败,无法确认模块 | 只初始化账号、配置、修复、上报、基础 UI | 版本升级、补丁命中,或本地连续成功启动达到阈值 |
| L4 停止自拉起 | 子进程 / 服务反复崩溃 | 暂停后台服务、指数退避重启 | 远程配置或下次版本恢复 |

降级开关必须本地可读。进入崩溃循环的设备可能离线,不能依赖服务端实时返回。远程配置只能收紧或放宽本地规则,不能成为唯一判定来源。

恢复条件要比进入条件更保守。一次成功启动只说明当前路径通过,不说明问题消失。推荐同时满足:同一版本连续成功启动 N 次、没有新的同签名失败、修复配置版本已更新、关键页面进入过一次。版本升级可以清理旧签名,但要保留"升级前进入过 SafeMode"的事件,方便灰度复盘。

用户强杀、系统更新、权限变更、包状态变化、任务移除不应触发 SafeMode。Android 13 已有 `REASON_USER_STOPPED`,Android 14 起新增 `REASON_PACKAGE_STATE_CHANGE`,并继续细化 reason / subreason;低版本或厂商 ROM 上拿不到完整分类时,宁可只上报,也不要按崩溃处理。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ApplicationExitInfo.java]

SafeMode 事件本身也要进入 Crash 上报体系。建议至少包含:进入等级、触发规则、上一轮 marker、退出原因、关联 issue、被关闭模块、恢复条件、是否成功退出。26.2 节的 Crash 上报体系负责聚合和告警,20.8 节负责把重复样本归并成可处理 issue。

## 文件落盘协议:tmp、fsync、rename

启动 marker 和 crash envelope 都属于"崩溃前关键写入",文件协议要按最坏情况设计:进程可能在写入中被 kill,磁盘可能只落了一半,另一个进程可能同时写。

推荐协议:

1. 写入独立临时文件,例如 `marker.json.new`。
2. 写完后对文件内容 `fsync`。
3. 关闭文件描述符。
4. rename 到正式文件名。
5. 下次读取时忽略残留 `.new`,必要时保留 `.bak` 做恢复。

Android `AtomicFile` 已覆盖主要路径;多进程写 marker 时要加文件锁,或按进程拆文件后由主进程汇总。Crash handler 里不要争用全局锁;锁被崩溃线程持有时,handler 再尝试加锁会卡死。

Native signal handler 的落盘边界更窄。安全做法是提前准备固定大小缓冲区和文件描述符,崩溃时只写最小二进制摘要;完整日志、符号化、压缩和上传都放到下次启动。

## 版本升级与用户强杀的排除规则

SafeMode 需要一组排除规则,否则会把正常生命周期当成故障:

- 版本升级:`versionCode` 变化后,旧版本的启动失败不再累计到新版本;但升级前的失败事件要上报。
- 用户强杀 / 从最近任务划掉:按用户行为处理,不进入保护模式。
- 权限变更和包状态变化:系统可能重启进程,按环境变化处理。
- 系统低内存:只在启动 marker 未完成且同一路径多次发生时触发内存降级;单次后台 LMK 不触发。
- 外部 service / SDK sandbox 退出:只能影响对应依赖模块,不能直接关闭主进程功能。

排除规则的落点仍然是 marker 匹配。没有 marker,只有退出原因,就上报观察;有 marker,但版本、进程、时间窗口对不上,也只上报观察。SafeMode 的判定应宁可少触发,也不要把用户带进错误的降级状态。

## 源码级深度补充(Crash 文件持久化协议可靠性边界)

AOSP 自身没有"统一"的崩溃文件持久化协议,而是分散在三套独立实现里:1 `android.util.AtomicFile`(Java 端约定俗成的原子写)走"写 `.new` → fsync → `renameTo`";2 `DropBoxManagerService` 走"写 `drop<pid>.tmp` → `createEntry()` 内 `EntryFile` 执行 `temp.renameTo(final file)` → `enrollEntry`"但**不**对 tmp 做 fsync;`init()` 启动时清理未提交的残留 `.tmp`;3 `tombstoned`(Native 端)走 `O_TMPFILE` → `linkat` + `unlink` 硬链接提交,**不**走 rename。文件系统层面 `rename(2)` 在同一文件系统内是原子的,但**不能**保证跨 power-cut 的元数据持久性--必须 `fsync(file)` + `fsync(parent dir)`。这三套实现都没有把目录 fsync 显式化,是 AOSP 自身 crash 文件持久化边界的最大盲点。锚定版本:AOSP android-17.0.0_r1;旧版本实现细节需按对应 tag 复核。

### AOSP `AtomicFile` 的 fsync + rename 实现

`frameworks/base/core/java/android/util/AtomicFile.java`(android-17.0.0_r1)。`finishWrite(FileOutputStream str)` 流程:

```java
public void finishWrite(FileOutputStream str) {
    if (str == null) return;
    if (!FileUtils.sync(str)) {              // 1 fsync(fd) - 数据+必要元数据
        Log.e(LOG_TAG, "Failed to sync file output stream");
    }
    try { str.close(); } catch (IOException e) { ... }
    rename(mNewName, mBaseName);             // 2 POSIX rename - 同 fs 内原子
    if (mCommitEventLogger != null) mCommitEventLogger.onFinishWrite();
}
```

`FileUtils.sync()`(`core/java/android/os/FileUtils.java` line 273-282)走 `stream.getFD().sync()` → `libcore.io.IoBridge.fsync` → `os.fsync(fd)`,等价于 `fsync(2)`,对文件大小、mtime、内容都做同步。AtomicFile 的 `startWrite()`(line 138-162)会处理 `.bak` 旧协议残留,然后打开 `.new`;`failWrite()` 先 `FileUtils.sync(str)` 同步,再 `close()`,最后删除 `.new` 文件。关键限制:

1. **只 fsync 文件,不 fsync 父目录**。POSIX 语义下,`rename(2)` 修改了父目录的目录项,必须 `fsync(parent_dirfd)` 才能保证元数据落盘。AtomicFile 在这一层有缺口。
2. **依赖同文件系统**。`rename(2)` 在跨 mount point 时返回 `EXDEV`,AtomicFile 不捕获这个 errno,rename 失败只打 log。
3. **fchmod 不原子**。`startWrite` 在 mkdirs 后做了 `setPermissions(parent, 0775, -1, -1)`,权限与子文件创建存在时间差。

### DropBoxManagerService 的 `.tmp` 状态机(无 fsync)

`frameworks/base/services/core/java/com/android/server/DropBoxManagerService.java`(android-17.0.0_r1)。`add()` 流程(line 511-568):

```java
temp = new File(mDropBoxDir, "drop" + Thread.currentThread().getId() + ".tmp");
try (FileOutputStream out = new FileOutputStream(temp)) {
    entry.writeTo(out.getFD());             // 1 写 .tmp,无 fsync
}                                            // 2 close 关闭 FileOutputStream,但不等于 fsync
long time = createEntry(temp, tag, flags);  // 3 EntryFile(File temp, ...) 执行 temp.renameTo(final file) → enrollEntry
temp = null;
...
} finally {
    if (temp != null) temp.delete();        // 4 仅在异常时清
}
```

`init()` 启动恢复(line 1074-1106):

```java
for (File file : files) {
    if (file.getName().endsWith(".tmp")) {
        Slog.i(TAG, "Cleaning temp file: " + file);
        file.delete();                      // 启动时清残留
        continue;
    }
    ...
}
```

DropBox 的实际状态机是:`.tmp` 写入完成后通过 `EntryFile.renameTo()` 提交到最终文件名,再 `enrollEntry` 注册到内存索引;启动期扫到的残留 `.tmp` 表示提交前中断,`init()` 删除(视作 partial/脏数据)。同时支持 IS_EMPTY tombstone(`enrollEntry(new EntryFile(mDropBoxDir, tag, t))` line 1236-1239)--空文件 tombstone 标记"数据被丢过"。关键限制:

1. **写 .tmp 时不 fsync**,写完后通过 renameTo 提交。完全依赖文件系统的惰性刷盘保证"写入即可见",在 power-cut 下可能丢失最近 1 个 entry。这与 AtomicFile 的显式 sync 形成区别。
2. **重启时**残留 `.tmp` 是未提交信号--`init()` 删除。这恰好提供了"partial 状态机"语义:`.tmp` 存在 = 上次提交前中断,**不需要**额外的 `partial` 标记文件。
3. **trim 策略**:ageSeconds(`Settings.Global.DROPBOX_AGE_SECONDS`)和 quotaPercent(`DROPBOX_QUOTA_PERCENT`)共同决定 `trimToFit()` 行为。

### `tombstoned` 的 linkat 提交(Native 端)

`system/core/debuggerd/tombstoned/tombstoned.cpp`(android-17.0.0_r1)。临时文件创建(line 145-167):

```cpp
CrashArtifact create_temporary_file() const {
    CrashArtifact result;
    result.fd.reset(openat(dir_fd_, ".", O_WRONLY | O_APPEND | O_TMPFILE | O_CLOEXEC, 0660));
    if (result.fd == -1) {
        PLOG(FATAL) << "failed to create temporary tombstone in " << dir_path_;
    }
    ...
    return result;
}
```

commit 协议(line 409-429):

```cpp
static bool rename_tombstone_fd(borrowed_fd fd, borrowed_fd dirfd, const std::string& path) {
    int rc = unlinkat(dirfd.get(), path.c_str(), 0);  // 1 删旧
    if (rc != 0 && errno != ENOENT) { ... return false; }
    std::string fd_path = StringPrintf("/proc/self/fd/%d", fd.get());
    rc = linkat(AT_FDCWD, fd_path.c_str(), dirfd.get(), path.c_str(), AT_SYMLINK_FOLLOW);
    if (rc != 0) { ... return false; }                // 2 linkat 提交
    return true;
}
```

关键设计差异:1 **不用 rename,用 linkat + unlink**--`O_TMPFILE` 模式下 fd 没有路径,无法 rename;只能 linkat 把 inode 接入目录树。2 **不 fsync 文件,也不 fsync 目录**--把"已提交"语义寄托在 linkat 的原子性上。3 **持久化后端** `/data/tombstones/` 位于设备数据分区,实际文件系统取决于设备;在没有 file / directory fsync 的情况下, power-cut 后最后 N 个 tombstone 仍可能丢失。

### `RecoverySystem.installPackage` 的控制文件(无 fsync / 无 rename)

`frameworks/base/core/java/android/os/RecoverySystem.java`(android-17.0.0_r1)。关键文件(line 134-150):

```java
public static final File BLOCK_MAP_FILE       = new File(RECOVERY_DIR, "block.map");
public static final File UNCRYPT_PACKAGE_FILE = new File(RECOVERY_DIR, "uncrypt_file");
public static final File UNCRYPT_STATUS_FILE  = new File(RECOVERY_DIR, "uncrypt_status");
public static final File LOG_FILE             = new File(RECOVERY_DIR, "log");
```

写入流程(line 619-660):

```java
LOG_FILE.delete();
UNCRYPT_PACKAGE_FILE.delete();
if (filename.startsWith("/data/")) {
    if (processed) {
        if (!BLOCK_MAP_FILE.exists()) throw new IOException("Failed to find block map file");
    } else {
        FileWriter uncryptFile = new FileWriter(UNCRYPT_PACKAGE_FILE);
        try { uncryptFile.write(filename + "\n"); } finally { uncryptFile.close(); }
        UNCRYPT_PACKAGE_FILE.setReadable(true, false);
        UNCRYPT_PACKAGE_FILE.setWritable(true, false);
        BLOCK_MAP_FILE.delete();
    }
    filename = "@/cache/recovery/block.map";
}
```

**完全没有 fsync,也没有 rename 协议**--直接 `FileWriter.write` + `close`,依赖 Java IO 内部 flush。崩溃时 `uncrypt_file` 可能为空或不完整。RecoverySystem 的最终 commit 信号是 BCB;Java 层通过 Binder 调用 `RecoverySystemService.setupBcb()`,system_server 拉起 init 的 `setup-bcb` 服务,再通过 `/dev/socket/uncrypt` 发送 BCB command。`BLOCK_MAP_FILE` 的存在性即状态机:`exists()` = 已经预先处理;不存在 = 启动时需要 uncrypt。两态机但**没有** partial 状态,崩溃恢复依赖 BCB + recovery image。

### 应用层 `crash_envelope` 的推荐设计

综合 AOSP 三套实现,应用层 SafeMode 的 crash_envelope 持久化协议应做四件事:1 **三态机**(`tmp`/`completed`/`partial`);2 **fsync 文件 + fsync 父目录**;3 **内容校验字段**(magic + version + size + sha256);4 **启动期扫描 partial → 决策层回收**。具体规范如下:

**1. 三态机定义**:

| 状态 | 文件名约定 | 写入期 | 提交动作 | 启动期扫描 |
|---|---|---|---|---|
| `tmp` | `crash_<id>.tmp` | append + 周期 fsync(file) | rename(tmp → envelope) | 读到 `.tmp` → 转 partial |
| `completed` | `crash_<id>.envelope` | 已 commit | fsync(parent dir) | 正常解析 |
| `partial` | `crash_<id>.partial` | 上次崩溃留下的不完整 tmp | - | 决策层决定是否重传 |

**2. envelope 头部字段**(最少 32 字节):

```
[0..4]   magic = "ENV1"
[4..6]   version = 1
[6..14]  size(u64 LE,正文长度)
[14..22] reserved
[22..30] reserved
[30..32] reserved
[32..N]  正文
[N..N+32] sha256(正文) - 末尾校验
```

读时先校验 magic + size,再读正文 + 末尾 sha256,**校验失败走 partial 路径**。AOSP `AtomicFile` 不做内容校验(只靠 rename 原子性),tombstoned 同样不做--应用层应补上。

**3. fsync 协议**(必须显式做):

```java
// 写 envelope
FileDescriptor fd = raf.getFD();
fd.sync();                              // fsync file
File dir = new File(".../envelopes").getAbsoluteFile();
FileDescriptor dirFd = Os.open(dir.getPath(), OsConstants.O_RDONLY, 0);
Os.fsync(dirFd);                        // fsync parent dir - AOSP 自己漏掉了
Os.close(dirFd);
```

`Os.fsync(FileDescriptor)` 是公开系统调用封装,无需版本限定。`FileUtils.sync()` 只对文件做 fsync,对父目录无效。

**4. 跨进程并发**:多进程同时写 marker 时要加文件锁(`FileChannel.tryLock()`)或按进程拆文件后由主进程汇总。Crash handler 里不要争用全局锁--锁被崩溃线程持有时,handler 再尝试加锁会卡死。

**5. Native signal handler 落盘边界更窄**:安全做法是提前准备固定大小缓冲区和文件描述符,崩溃时只写最小二进制摘要(magic + 时间戳 + crash type + backtrace pointer list);完整日志、符号化、压缩和上传都放到下次启动。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/util/AtomicFile.java、core/java/android/os/FileUtils.java、services/core/java/com/android/server/DropBoxManagerService.java、core/java/android/os/RecoverySystem.java、services/core/java/com/android/server/recoverysystem/RecoverySystemService.java、system/core/debuggerd/tombstoned/tombstoned.cpp;本节调研对应《2026-06-16-crash-file-persistence-protocol-reliability.md》]


## 源码级深度补充(AOSP AppExitInfoTracker 参照)

AOSP 自身在 `frameworks/base/services/core/java/com/android/server/am/AppExitInfoTracker.java` 维护一个进程退出状态机,可作为本节工程设计的参考实现。锚定版本:AOSP android-17.0.0_r1。

### 状态机选型:环形缓冲 + LRU + 时间窗

AOSP 把每个 package / uid 容器的退出记录限定在 16 条以内(`config_app_exit_info_history_list_size = 16`,`core/res/res/values/config.xml`),超出后按时间戳最小者淘汰。App 侧 SafeMode 实现也应限定在 8~16 条,超过按 LRU 驱逐;N 太小会冲掉灰度期集中爆发,N 太大调试难定位。

### 字段五元组:定义一次进程死亡

AOSP 查询时先按 `packageName + uid` 定位容器,再按 `pid` 过滤;`AppExitInfoContainer.getExitInfosLocked()` 把结果按 `timestamp` 倒序返回,`realUid` 主要用于孤立进程 / SDK sandbox 映射和 zygote、lmkd 外部信号匹配。App 侧建议把 marker 匹配维度限定到 `(versionCode, packageName, processName, startupRoute, startedWallTimeMs)`,再叠加 `ApplicationExitInfo.timestamp` 做时间窗校验,窗口 ±60s 内才计入崩溃循环。

### 不可覆盖白名单:`preventExitInfoUpdate`

AOSP 维护一份「AM 自杀不可覆盖」的 reason 白名单:`REASON_ANR`、`REASON_CRASH`、`REASON_CRASH_NATIVE` 一旦写入就不允许被后续 AM 自身的 kill 覆盖(`AppExitInfoTracker.preventExitInfoUpdate`)。`handleNoteAppKillLocked` 在覆盖前先 `if (info == null || preventExitInfoUpdate(info)) { addExitInfoLocked(raw); }`,未命中白名单才就地覆盖。App 侧 SafeMode 状态机应对应两条写入路径:

- **不可被覆盖的高可信事件**:Native crash、Java crash、ANR 触发的 `fatal_exited` marker,跨次启动只增不减。
- **可被覆盖的低可信事件**:`launching` 状态可被同一次启动的后续 `started` 覆盖;上次启动因 LMK / 用户划掉导致 marker 卡在 `launching`,本次启动应识别为新会话、重置计数。

### 时间窗:防止 pid 复用污染

AOSP 在更新已有记录前先做 `isFresh` 时间窗校验(`AppExitInfoTracker.updateExistingExitInfoRecordLocked` 注释明确「if the record is way outdated, don't update it then (because of potential pid reuse)」)。`getHistoricalProcessExitReasons(packageName, pid, maxNum)` 的 pid=0 语义是不过滤 pid,但调用方仍要在客户端结合 timestamp 做二次校验。App 侧做 marker + exit evidence 匹配时同样必须做时间窗,建议 marker 用 `System.currentTimeMillis()` 写入,与 `ApplicationExitInfo.timestamp` 配对。

### 多源信号聚合:zygote + lmkd + AM + 15s 去抖

AOSP 维护三个独立信号源(`mAppExitInfoSourceZygote`、`mAppExitInfoSourceLmkd`、AM 自身 `scheduleNoteAppKill`),优先级 **lmkd > zygote SIGCHLD > AM 自杀**。写入 statsd 之前先去抖 15 秒(`APP_EXIT_INFO_STATSD_LOG_DEBOUNCE`),让更准确信号先到达。App 侧「marker + 退出证据」可对应这套多源模型:

- 信号源 A:App 自己的 CrashHandler / SignalHandler(最高优先级)
- 信号源 B:`ApplicationExitInfo`(次优先级,跨进程重启后才有)
- 信号源 C:用户行为日志 / 任务移除(最低优先级,只做排除)

判定时按 A > B > C 取最可信的一类;冲突时以 A 为准,C 永远只做排除项。

### 持久化与离线兜底

AOSP 把退出记录写到 `/data/system/procexitstore/procexitinfo`(`AtomicFile` 包装,30 分钟刷盘一次),崩溃时只丢 30 分钟内的记录;`onSystemReady` 时异步加载(`loadExistingProcessExitInfo`)。App 侧 SafeMode 本地规则必须不依赖任何远程信号:启动时先读本地 marker,再读 `ApplicationExitInfo`;远程配置作为「放宽/收紧」的二次开关,不能作为唯一判定来源。断网、远程配置降级、首次冷启场景下,SafeMode 仍能基于本地历史做兜底。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AppExitInfoTracker.java、core/java/android/app/ApplicationExitInfo.java、core/java/android/app/ActivityManager.java、services/core/java/com/android/server/am/ProcessList.java、core/res/res/values/config.xml;本节调研对照《2026-06-16-appsafemode-state-machine-and-launch-success-marker.md》]

### 深度调研源

- SafeMode launch marker 状态机 AOSP 源码核验 - 详细核验 ApplicationExitInfo 17 个 REASON_* 常量、AtomicFile.finishWrite() 持久化协议、AppExitInfoTracker 30分钟 debounce + 16条记录限制、Process.killProcess 三条路径

## 小结

SafeMode 能否拦住崩溃循环,取决于三件事:启动 marker 写得足够早,退出证据补得足够准,降级动作足够窄。Java Crash、Native Crash、ANR、LMK、WebView Renderer gone 都能打断启动,但它们不是同一种故障;统一进入"保护模式"之前,必须先按证据来源分层。

工程上可以从最小路径开始:主进程 marker、Java Crash envelope、API 30+ `ApplicationExitInfo` 补偿、WebView `onRenderProcessGone()` 页面级记录、L1/L2 两档降级。等这条路径稳定后,再补 Native 最小摘要、多进程汇总、远程阈值和发布平台联动。
