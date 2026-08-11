---
title: "线上性能监控"
chapter: "15.5"
last_task6_review_log: "logs/review/2026-05-28-19-review.md"
last_task6_at: "2026-05-28T19:05:00+08:00"
reviewed_date: "2026-05-28"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
section: "15.5"
status: finalized
drafted_date: "2026-04-04"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1; Android 17 / API 37 ApplicationStartInfo, ApplicationExitInfo.AnrInfo, AnrWarningResult, ProfilingManager and ProfilingTrigger; current Android Vitals, JankStats and Perfetto SDK documentation"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/monitoring-overview"
  - type: official
    path: "https://developer.android.com/reference/android/view/FrameMetrics"
  - type: official
    path: "https://developer.android.com/topic/performance/jankstats"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationStartInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo.AnrInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/AnrWarningResult"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/slow-session"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/tracing-sdk"
  - type: aosp
    path: "art/runtime/signal_catcher.cc"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingManager.java"
  - type: aosp
    path: "packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java"
tags: [monitoring, APM, FrameMetrics, JankStats, ANR, startup, production]
related_chapters: ["7.1", "7.3", "8.1", "9.3", "14.1", "14.9", "14.10", "15.3", "15.4", "15.9", "15.10"]
pipeline_stage: ready-to-publish
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
last_task9_at: "2026-05-28T19:20:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-28"
task9_result: pass-tech-review
repaired_date: "2026-04-25"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-05-28T18:50:00+08:00"
last_task9_audit: "2026-07-06"
last_task9_audit_at: "2026-07-06T11:23:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-07-06-11-audit.md"
last_task9_review_log: "logs/deep-review/2026-05-28-19-deep-review.md"
review_notes: "2026-05-21 Task9 deep review: needs-rework。P0：FrameMetrics 指标表使用不存在的公开常量名；P1：GPU_DURATION/API31 版本边界与 ANR 触发口径需补。"
task9_review_notes: "2026-05-28 Task9 deep review: pass-tech-review; no P0/P1; P2 suggestions written to intake/suggestions.md; auto-promoted finalized."
last_task6_audit: "2026-06-10"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-03
---
# 线上性能监控

## 为什么线下测试无法替代线上监控

Perfetto、Macrobenchmark 和稳定的实验环境适合回答“某条路径为什么慢”。线上监控回答另一组问题：问题出现在哪些版本、机型和业务场景，波及多少用户，修复后是否回到基线。两类工作使用的证据不同，也处在排障流程的不同位置。

实验室很难完整复制线上设备的组合。SoC、GPU 驱动、内存容量、温控状态、刷新率、厂商调度策略、网络质量和用户数据规模都会改变结果。测试用例还受预设路径约束；线上用户可能从通知、分享链接、桌面小组件或恢复任务进入应用，启动和渲染路径随之改变。

一套可维护的监控系统需要完成四件事：

1. 用有明确语义的事件记录现象；
2. 为事件附上页面、交互、版本和设备上下文；
3. 用稳定分母与采样概率计算总体指标；
4. 把异常样本关联到 trace、退出记录或实验复现。

帧回调、启动埋点或 ANR watchdog 只能提供局部信号。单个信号未经口径约束，容易被误称为“掉帧”“冷启动”或“系统 ANR”，统计结果也就失去了可比性。

## 监控系统的三个层次

| 层次 | 产物 | 适合的实现 |
|---|---|---|
| 信号层 | 帧、启动、主线程停顿、进程退出等事件 | `JankStats`、`FrameMetrics`、`ApplicationStartInfo`、`ApplicationExitInfo`、业务埋点 |
| 证据层 | 异常前后的栈、trace、breadcrumb 和资源状态 | 本地环形缓冲区、`ProfilingManager`、Perfetto SDK、受控实验 |
| 分析层 | 分位数、比率、分群、回归检测和样本回查 | Android Vitals、第三方 APM、自建数据系统 |

信号层应保持低开销，证据层按预算触发，分析层负责分母、采样校正和数据完整性。将三层分开后，客户端可以独立调整采样，服务端也能识别每条记录来自系统判定、库的启发式判定，还是业务规则。

### 事件协议要先于 SDK 接入

每类事件至少携带以下字段：

| 字段 | 作用 |
|---|---|
| `event_schema_version` | 支持字段和算法演进 |
| `app_version`、`build_id` | 定位发布回归 |
| `session_id`、`process_start_id` | 区分会话与进程 |
| `scene`、`interaction` | 关联页面和用户操作 |
| `source`、`classification` | 标明系统结果或启发式结果 |
| `timebase`、`timestamp`、`duration` | 防止混用 wall clock、uptime 与 elapsed realtime |
| `sample_probability` | 服务端计算抽样权重 |
| `device`、`os`、`display_mode` | 支持机型、版本和刷新率分群 |

同一时长的起点与终点必须来自同一个时钟。主线程停顿、帧耗时和 `ApplicationStartInfo` 的启动时间适合使用单调时钟；自然日和版本发布时间使用 wall clock。跨设备记录不能用本地单调时间戳直接排序。

## 帧监控：先说明观测对象

“FPS”“慢帧”“错过 deadline”描述的是不同现象：

- FPS 是一段时间内呈现帧数量与时间的比值；
- 慢帧是应用或系统定义的帧耗时分类；
- deadline miss 表示一帧没有在系统给定的时间预算内完成；
- 用户可见卡顿还受缓冲、SurfaceFlinger 合成和重复呈现影响。

应用侧 API 能看到窗口或 View 渲染的一部分信息。需要判断帧是否按期呈现、卡在 App、RenderThread、GPU 还是合成阶段时，应回到 FrameTimeline 与渲染流水线分析，参见 §2.4、§7.1 和 §8.1。

### Choreographer.FrameCallback：VSync 邻近信号

`Choreographer.FrameCallback.doFrame(frameTimeNanos)` 的参数表示该帧使用的 VSync 时间。持续重新注册回调，可以观察主 Looper 能否按 VSync 节奏运行：

```java
Choreographer.FrameCallback callback = new Choreographer.FrameCallback() {
    private long previousVsyncNanos;

    @Override
    public void doFrame(long frameTimeNanos) {
        if (previousVsyncNanos != 0L) {
            vsyncIntervalHistogram.record(frameTimeNanos - previousVsyncNanos);
        }
        previousVsyncNanos = frameTimeNanos;
        Choreographer.getInstance().postFrameCallback(this);
    }
};

Choreographer.getInstance().postFrameCallback(callback);
```

这段代码的用途是记录相邻回调使用的 VSync 时间差。回调只注册一次，因此要在 `doFrame()` 中重新注册；采样与计数之外的工作应移到后台线程。

这个信号有三条限制：

- 持续收到回调不等于应用持续产出了新 buffer。没有 UI 更新时，回调仍可按 VSync 执行。
- 相邻 `frameTimeNanos` 的差值不能直接解释为某一帧的 CPU、GPU 或端到端呈现耗时。
- 固定用 16.67 ms 判断卡顿会忽略 90 Hz、120 Hz、动态刷新率和应用帧率投票。

因此，FrameCallback 适合做主线程节奏探针或低版本兼容信号，不应单独作为“用户实际 FPS”的权威来源。

### FrameMetrics：窗口内的帧耗时分项

Android 7（API 24）加入 `Window.OnFrameMetricsAvailableListener`。硬件加速窗口完成一帧后，监听器可以读取公开的 `FrameMetrics` 指标：

| 指标 | 解释 | 版本边界 |
|---|---|---|
| `UNKNOWN_DELAY_DURATION` | 已知阶段之外、开始处理前后的未归类延迟 | API 24+ |
| `INPUT_HANDLING_DURATION` | 输入处理阶段 | API 24+ |
| `ANIMATION_DURATION` | 动画回调阶段 | API 24+ |
| `LAYOUT_MEASURE_DURATION` | measure/layout 阶段 | API 24+ |
| `DRAW_DURATION` | UI 线程记录绘制命令阶段 | API 24+ |
| `SYNC_DURATION` | UI 与 RenderThread 同步阶段 | API 24+ |
| `COMMAND_ISSUE_DURATION` | RenderThread 向图形驱动提交命令的阶段 | API 24+ |
| `SWAP_BUFFERS_DURATION` | buffer swap 阶段 | API 24+ |
| `TOTAL_DURATION` | 这些阶段覆盖的总时长 | API 24+ |
| `FIRST_DRAW_FRAME` | 是否为窗口首次绘制 | API 24+ |
| `GPU_DURATION` | GPU 完成该帧工作的时长 | API 31+ |
| `DEADLINE` | 系统分配给该帧的完成预算 | API 31+ |

`COMMAND_ISSUE_DURATION` 长只能说明命令提交阶段耗时，不能替代 `GPU_DURATION`。同理，`TOTAL_DURATION` 也不包含 SurfaceFlinger 后续合成与显示硬件扫描输出的完整端到端路径。

API 31 起，可用如下关系判断应用是否在预算内完成：

```text
hit_deadline = TOTAL_DURATION < DEADLINE
miss_deadline = TOTAL_DURATION >= DEADLINE
```

这里用严格小于。Android 17 的 `FrameMetrics` 文档把 `TOTAL_DURATION < DEADLINE` 定义为按期完成；等于 deadline 不能计入按期样本。

API 24—30 没有公开 `DEADLINE`。用 `1 / display.refreshRate` 只能得到当前显示模式的名义周期，无法还原系统给某帧使用的精确预算，也无法覆盖刷新率切换与不同流水线深度。低版本可以保留“超过名义周期”的独立指标，字段名要体现它是估算值。

监听器使用注册时传入的 `Handler`。回调中应复制必需字段并做常数级聚合；序列化、压缩、落盘和网络发送放到工作线程。还要记录 `dropCountSinceLastInvocation`，否则回调积压会让样本看起来比现场更平稳。

### JankStats：启发式分类加 UI 状态

JankStats 以窗口为监控单元。API 24+ 使用 FrameMetrics，API 23 及以下使用 `OnPreDrawListener`。它增加了两项工程能力：

- 根据平台可用信息进行可配置的 jank 判定；
- 通过 `PerformanceMetricsState` 把页面和交互状态放入帧记录。

以下示例只在回调里复制当前帧，随后交给有界缓冲区。`FrameData` 会被 JankStats 重用，不能把原对象交给异步任务：

```kotlin
private val jankStats = JankStats.createAndTrack(window) { frame ->
    val sample = FrameSample(
        startNanos = frame.frameStartNanos,
        uiDurationNanos = frame.frameDurationUiNanos,
        isJank = frame.isJank,
        states = frame.states.map { StateSample(it.key, it.value) }
    )
    frameBuffer.tryAdd(sample)
}

private val stateHolder =
    PerformanceMetricsState.getHolderForHierarchy(window.decorView)

fun onFeedScrollStarted() {
    stateHolder.state?.putState("scene", "home_feed")
    stateHolder.state?.putState("interaction", "scroll")
}
```

`FrameSample`、`StateSample` 和 `frameBuffer` 是项目内的数据结构。缓冲区应有容量上限和丢弃计数，状态值使用低基数枚举，避免把商品 ID、URL 或用户输入放进聚合维度。

JankStats 的回调线程也有版本差异：API 23 及以下在主线程，API 24+ 在 FrameMetrics 使用的线程。两个分支都要尽快返回。API 31+ 的 `FrameDataApi31.frameOverrunNanos` 能直接表达超出 deadline 的时间；API 24+ 的 `FrameDataApi24.frameDurationCpuNanos` 提供非 GPU 部分的时长信息。

JankStats 的 `isJank` 属于库的启发式分类，FrameMetrics 的 duration 属于平台观测值。服务端应保留原始时长、算法版本和阈值配置，避免库升级后把历史趋势误读为性能变化。

### View 渲染与游戏渲染要分开

FrameMetrics、JankStats 以及 Android Vitals 的慢帧/冻结帧统计面向使用 View/Canvas UI Toolkit 的窗口。直接使用 OpenGL、Vulkan、Unity 或 Unreal 的主画面不在该套 Vitals 渲染统计范围内。

Google Play 为游戏提供 Slow Sessions。它从 SurfaceFlinger 所见的应用 surface 估算帧率，覆盖 OpenGL、Vulkan 与 Android UI Toolkit，并且当前只面向游戏。应用若同时包含普通 View 页面和游戏 surface，应分别定义两套指标与分母，不能把 View 帧时长和游戏 session FPS 合在同一张趋势图里。

## 启动监控：TTID、TTFD 与业务可用时间

启动指标先要定义区间：

| 指标 | 起点 | 终点 | 回答的问题 |
|---|---|---|---|
| TTID | 系统启动请求 | 第一帧完成 | 用户何时看到初始画面 |
| TTFD | 系统启动请求 | `reportFullyDrawn()` | 应用声明何时完成延后加载 |
| 业务可用时间 | 已定义的启动入口 | 业务状态满足条件 | 某个页面何时可操作或展示目标内容 |

TTID 可能止于 SplashScreen 或内容不完整的首帧。TTFD 依赖应用在合适时机调用 `reportFullyDrawn()`。业务可用时间由产品语义决定，无法由平台自动推断。三者可以同时采集，字段名与终点语义必须分开。

冷、温、热启动也应沿用系统分类。进程不存在时的冷启动、进程存在但 Activity 需要重建时的温启动、已有 Activity 恢复到前台时的热启动，不能用单一分布相互比较。

### API 35+：ApplicationStartInfo 是系统启动记录

Android 15（API 35）加入 `ApplicationStartInfo`。应用可通过 `ActivityManager.addApplicationStartInfoCompletionListener()` 在首帧完成时收到本次记录，也可以使用 `getHistoricalProcessStartReasons()` 查询历史记录。

`getStartupTimestamps()` 返回单调时钟下的纳秒时间戳。记录可包含：

- `START_TIMESTAMP_LAUNCH`；
- `START_TIMESTAMP_FORK`；
- `START_TIMESTAMP_APPLICATION_ONCREATE`；
- `START_TIMESTAMP_BIND_APPLICATION`；
- `START_TIMESTAMP_FIRST_FRAME`；
- `START_TIMESTAMP_FULLY_DRAWN`；
- 初始 RenderThread 帧和 SurfaceFlinger 合成相关时间戳。

各字段是否存在取决于启动状态和路径。完成监听器在第一帧时触发，不会等待 `reportFullyDrawn()`；需要 TTFD 时，应在调用 `reportFullyDrawn()` 后再查历史记录。`getStartType()` 在首帧完成状态下给出 cold、warm 或 hot，`getReason()` 与高版本的 `getStartComponent()` 可区分 launcher、push、service、broadcast 等入口。

计算时只对同一条 `ApplicationStartInfo` 记录做差：

```text
TTID = START_TIMESTAMP_FIRST_FRAME - START_TIMESTAMP_LAUNCH
TTFD = START_TIMESTAMP_FULLY_DRAWN - START_TIMESTAMP_LAUNCH
```

缺少终点字段时记录为“未观测到”，不要补零，也不要用客户端 wall clock 拼接。Android 16（Baklava）及以下的 service start 存在 `START_TIMESTAMP_LAUNCH` 已知边界；面向 Activity 的启动面板应按 `startComponent` 或启动 reason 过滤。

### API 24—34：手动埋点要承认观测边界

`Process.getStartUptimeMillis()` 从 API 24 可用，可作为进程启动的单调时钟锚点。它早于应用代码，但表示进程启动时间，不能替代系统收到 Activity launch 的时间。`Application.attachBaseContext()` 更晚，只能标记应用代码已经开始执行。

`Activity.onWindowFocusChanged()` 也不等于 TTID。窗口可能多次获得焦点，焦点到达与首帧呈现没有固定先后关系。它可以定义某项业务交互指标，但事件名不应写成 TTID。

低版本线上数据可以拆成以下区间：

- process start → `Application.onCreate()`；
- `Application.onCreate()` → 首个 Activity 的 `onCreate()`；
- 页面创建 → 首个内容绘制回调；
- 页面创建 → 业务可用条件；
- 入口 → `reportFullyDrawn()`。

这些区间有助于定位初始化、数据和 UI 阶段，无法完整复制系统 TTID。跨版本看板应标明 source，避免把 API 35+ 系统时间戳与低版本客户端近似值放进同一序列。

### Jetpack App Startup 管理初始化，不负责测量启动

App Startup 用单个 `InitializationProvider` 发现并运行 `Initializer`，还能声明初始化依赖与手动延迟初始化。它提供的是初始化组织方式，没有自动产生 TTID、TTFD 或 initializer 耗时指标。

接入 App Startup 后，可以围绕每个 initializer 增加 `android.os.Trace` 切片和轻量计时，再用 Macrobenchmark 与线上启动记录核对收益。初始化顺序、主线程约束和依赖关系仍要按库文档处理；将多个 provider 迁移到 App Startup 也不能预设固定的毫秒收益。

## ANR 监控：区分预警、系统判定与退出证据

系统 ANR 包括 input dispatch、broadcast、service、foreground service、JobService、content provider 等路径。每条路径的计时起点、超时预算和进程状态都可能不同。“主线程连续数秒没有处理消息”只能描述 Looper stall，不能代替系统的 ANR 分类。

线上事件建议至少分成三类：

| 分类 | 来源 | 能说明什么 |
|---|---|---|
| `main_looper_stall_candidate` | watchdog | 主线程探针在预算内未执行 |
| `anr_warning` | API 37 `AnrWarningResult` | 系统认为当前路径接近 ANR timeout |
| `process_exit_anr` | `ApplicationExitInfo.REASON_ANR` | 历史记录显示进程因 ANR 被终止 |

Android Vitals 还有自己的统计分母与用户感知口径。客户端记录、进程退出历史和 Play 指标需要并列展示，不能用一个数替换另一个数。

### Watchdog：主 Looper 停顿候选

watchdog 在线程中向主 `Handler` 投递序号，等待主线程确认。超过项目定义的预算后，它可以保存：

- 连续未确认时长；
- 主线程栈；
- 当前页面和交互；
- 最近消息、锁等待或业务 breadcrumb；
- CPU、内存和前后台状态的轻量快照。

预算使用 `SystemClock.uptimeMillis()` 或 `elapsedRealtime()`，起点与终点保持同源。探针间隔、判定预算、重复事件合并窗口和休眠行为都要进入 schema。系统冻结、调试器暂停、设备休眠和严重 CPU 饥饿都会影响结果，所以服务端分类名称应保留 `candidate`。

watchdog 在 API 30 以下仍有诊断价值，在高版本也能捕获应用恢复且未退出的长停顿。它提供应用侧现场，不能声称与系统 ANR 一一对应。

### API 30+：ApplicationExitInfo 在后续进程读取退出历史

进程重新启动后，可调用 `ActivityManager.getHistoricalProcessExitReasons()` 读取 `ApplicationExitInfo`。`REASON_ANR` 表示该进程因 ANR 被系统终止；它记录时间、PID、importance、PSS/RSS、description 等退出上下文。

`getTraceInputStream()` 需要按可空结果处理。系统维护的记录和 artifact 都有容量限制，旧内容可能被覆盖。ANR 后应用若恢复运行，后续又因其他原因退出，该条退出记录仍可能附带早先的 ANR trace，因此读取 artifact 时应同时保存退出 reason、trace 类型和时间，避免只在 `REASON_ANR` 分支读取。

API 31+ 的 native crash artifact 可能是 protobuf tombstone，不能总按文本 ANR trace 解析。上传前还要限制大小、清理敏感路径与业务 tag，并记录解析失败。

`ApplicationExitInfo` 只描述退出历史。用户关闭 ANR 对话框、系统终止进程或应用自行恢复会产生不同结果；它也不能实时通知当前进程“刚刚发生了所有类型的 ANR”。Android Vitals 的用户感知 ANR 率按 opted-in Play 数据和日活用户分母计算，与本地退出记录的事件率不同。

### API 37：ANR 预警与结构化 AnrInfo

Android 17（API 37）新增 `ActivityManager.registerAnrWarningListener()`。系统在应用接近某条 ANR timeout 时，以尽力而为的方式调用监听器。回调可能未执行，也可能没有足够时间完成工作；官方要求 executor 不使用主线程。

下面的接入只复制结构化字段与内存中的最近状态。监听器对象需要由组件长期持有，注销时传回同一个对象：

```kotlin
@RequiresApi(37)
fun registerAnrWarning(
    activityManager: ActivityManager,
    executor: Executor
): Consumer<AnrWarningResult> {
    val listener = Consumer<AnrWarningResult> { warning ->
        anrWarningBuffer.tryAdd(
            AnrWarningSample(
                type = warning.anrType,
                id = warning.anrId,
                consumedMillis = warning.consumedMillis,
                timeoutMillis = warning.timeoutMillis,
                description = warning.description,
                breadcrumbs = breadcrumbRing.snapshot()
            )
        )
    }
    activityManager.registerAnrWarningListener(executor, listener)
    return listener
}
```

该回调中不要做网络请求、压缩、大范围线程遍历或同步磁盘 IO。`description` 是面向调试的非稳定字符串，可用于辅助聚类，不能解析成长期兼容协议。

如果进程随后以 `REASON_ANR` 退出，API 37 的 `ApplicationExitInfo.getAnrInfo()` 会返回结构化 `AnrInfo`，其中包括 ANR type、ANR ID、timeout 和 `isUserPerceptible()`。warning 与 exit 记录可用 type + ID 关联。预警出现而退出记录缺席，可能代表应用恢复、回调误差或记录尚未读取，不能直接改写为“已发生致死 ANR”。

### FileObserver 监听 traces.txt：普通应用应停用

早期方案常监听 `/data/anr/traces.txt`。Android 17 的 AOSP 已不使用单一固定文件：`StackTracesDumpHelper` 把目录定义为 `/data/anr`，文件使用 `anr_` 与 `temp_anr_` 前缀。普通第三方应用受文件权限与 SELinux 限制，无法把该目录当作稳定、可读的公开接口。

因此：

- 普通应用不应再接入 `FileObserver("/data/anr/traces.txt")`；
- 平台签名应用或系统镜像工具若读取 `/data/anr`，也要按当前文件命名、权限和清理逻辑验证；
- API 30+ 使用 `ApplicationExitInfo` 读取系统公开的退出 artifact；
- API 37 可增加 ANR warning，低版本以 watchdog 记录停顿候选。

这项历史方案只用于说明迁移边界，不代表它在 Android 17 上仍是可行的应用 API。

### SIGQUIT 与 ART SignalCatcher：不要在量产 SDK 中争抢信号

Android 17 的 ANR 路径会向目标进程发送 `SIGQUIT`。ART 的 `SignalCatcher` 线程通过 `sigwait` 接收信号并生成 Java 线程 dump。普通 `sigaction(SIGQUIT, ...)` 不能保证先于 ART 收到；修改线程信号掩码、hook SignalCatcher 或吞掉 SIGQUIT 还可能破坏系统取栈。

量产应用应把这条路径视为平台实现证据，不把 signal hook 当作公开 ANR API。强控制环境中的系统组件若要扩展信号采集，需要在目标 Android 版本、ART 实现、ABI 与厂商改动上单独验证，并保证原有 dump 流程继续执行。

## 采样：基线样本与异常样本分开

高频信号若全部上传，会增加 CPU、存储、网络和后端成本。采样设计要同时解决覆盖率与可估计性。

### 稳定的头部采样

头部采样在会话或进程开始时决定是否采集，并在整个采样单元内保持稳定。可对匿名 install ID、app version 和采样配置版本做哈希，获得可复现的选择结果。这样能避免同一会话中只留下少量孤立帧，也便于灰度调整。

每条记录保存入选概率 `p`。随机抽样且入选概率已知时，服务端可使用 `1 / p` 作为权重估计总体计数。若不同机型、国家或版本使用不同概率，应按分层概率分别加权，不能直接相加样本数。

采样决定不能依赖待估计的性能值。只采“启动很慢”的会话无法估计慢启动率，因为正常会话没有进入分母。

### 异常触发样本只用于诊断

ANR warning、严重主线程停顿、极端启动或用户反馈可以触发额外上下文与 artifact 保存。这类尾部样本适合定位根因，但选择概率依赖结果，不能进入总体发生率和分位数的无偏估计。

建议保留两条逻辑通道：

- `baseline_sample`：稳定概率、可加权，用于趋势和 SLO；
- `diagnostic_sample`：事件触发，用于聚类、栈与 trace 回查。

服务端展示诊断样本时，应标明“条件样本”，避免把异常集合中的机型占比解释成全体用户占比。

### 设备端聚合

逐帧原始事件通常无须全部发送。设备端可按 session、window、scene 和 display mode 聚合：

- 总帧数、JankStats jank 数、deadline miss 数；
- 帧时长或 overrun 的固定桶直方图；
- TTID、TTFD 与业务阶段时长；
- watchdog 候选次数与最长持续时间；
- 本地缓冲、FrameMetrics 回调和上传队列的丢弃计数。

直方图桶边界和算法版本属于 schema。修改桶边界后要升级版本，旧数据不能无说明地与新数据合并。高基数字段放在诊断样本中，不宜作为常规聚合标签。

## 聚合：分母、分群与延迟

每项指标要写清分母。常见口径包括：

| 指标 | 示例分子 | 示例分母 |
|---|---|---|
| 用户感知 ANR 率 | 当日发生至少一次目标 ANR 的用户 | 当日 eligible active users |
| 会话 ANR 率 | 含目标 ANR 的会话 | eligible sessions |
| 帧 deadline miss 率 | miss 的观测帧 | 同一渲染栈下的 eligible frames |
| 慢启动会话率 | 超出目标的启动会话 | 同类型、同入口的启动会话 |
| TTFD 分位数 | 有效 TTFD 样本 | 已调用并观测到 `reportFullyDrawn()` 的启动 |

事件率、用户率和会话率不能互换。一次会话中重复发生十次 ANR，对事件率和用户率的影响不同。TTFD 缺失率也应单独展示，否则团队可能通过漏调用 `reportFullyDrawn()` 获得看似更好的曲线。

分群从可行动维度开始：app version、Android version、device model/SoC、RAM 档位、启动类型、入口、scene、渲染栈和前后台状态。分群样本低于最小有效量时，不触发自动结论。

P50、P90、P95、P99 用于观察分布，均值可用于某些可加总成本，但不能单独描述长尾。任何分位数都需要附样本量、覆盖率和采样口径。数据到达可能延迟，Play Vitals 也按日更新；跨系统对比时要等各自窗口稳定。

## 报警：SLO、回归和数据质量一起判断

可执行的报警通常组合四类条件：

1. 绝对目标：指标超过团队或外部平台定义的 SLO；
2. 相对回归：新版本相对稳定版本、灰度对照或历史同周期恶化；
3. 最小数据量：eligible 用户、会话或帧达到统计要求；
4. 数据健康：覆盖率、延迟、schema 分布和丢弃率正常。

多窗口 burn-rate 适合同时发现短时间急剧恶化与持续缓慢恶化。新版本报警还应关联 rollout 比例，避免样本量增长造成告警抖动。固定阈值应来自 §15.3 的指标合同、Google Play 当前 bad behavior threshold 或团队 SLO，不另设通用 P0/P1 数字。

报警事件应附带：

- 指标定义与当前值、基线值；
- 时间窗、样本量、覆盖率和采样概率；
- 受影响最大的可行动分群；
- 对应发布版本、变更记录与负责人；
- 可回查的诊断样本、trace 或 ANR cluster；
- 数据延迟与完整性状态。

没有证据链接的趋势告警只会产生人工查询。没有数据健康检查的告警则容易把 SDK 关闭、字段缺失或上传故障误判为性能改善。

## ProfilingManager：由系统提供重型证据

Android 15（API 35）加入 `ProfilingManager`，应用可以请求 Java heap dump、heap profile、stack sampling 和 system trace。结果通过监听器异步返回，并受系统资源、速率和并发限制；请求成功不代表一定会得到 artifact。

Android 16（API 36）加入 `ProfilingTrigger`，系统可在事件发生时生成诊断结果。到 Android 17 / API 37，触发类型包括：

| 类型 | 行为摘要 |
|---|---|
| `APP_FULLY_DRAWN` | 冷启动调用 `reportFullyDrawn()` 后触发 |
| `ANR` | 系统识别 ANR 后、可能终止应用前，返回运行中 system trace 的 snapshot |
| `APP_REQUEST_RUNNING_TRACE` | 应用请求当前运行中的 system trace |
| `KILL_FORCE_STOP`、`KILL_RECENTS`、`KILL_TASK_MANAGER` | 对应系统终止路径 |
| `OOM` | 对应 OOM 条件，返回 Java heap dump |
| `ANOMALY`、`APP_COMPAT` | 系统异常或兼容性条件，artifact 随类型变化 |
| `KILL_EXCESSIVE_CPU_USAGE` | 因 CPU 资源使用过量被终止 |
| `COLD_START` | 冷启动尽早开启新 system trace 与 stack sampling |

`COLD_START` 触发会持续到 `reportFullyDrawn()`，未调用时默认在 5 秒后停止；它使用 discard buffer，缓冲区满后保留较早事件。`ANR` 触发表示系统已识别 ANR，但不保证进程随后被终止。

Android 17 源码位于 `packages/modules/Profiling`。该能力由 Mainline Profiling 模块演进，官方参考文档中的部分方法标为 version 36.1，例如 `requestRunningSystemTrace()`。接入时应同时做 SDK/API 检查、运行时能力检查与错误处理，不能只按 `SDK_INT` 推断所有 trigger 都可用。`addAllProfilingTriggers()` 也要受服务端采样与本地预算约束。

线上使用还需设定：

- 每类 trigger 的允许版本、场景与采样率；
- artifact 最大尺寸、保留期限和上传条件；
- 用户数据、路径、线程名、trace tag 与对象内容的隐私审查；
- 无结果、被限流、功能关闭和解析失败的可观测状态；
- 与轻量事件关联的 session、process、ANR ID 或 startup ID。

## 扩展：Perfetto SDK 的线上边界

Perfetto Tracing SDK 是 C++17 库，可用 Track Event 或自定义 data source 记录应用事件。它有两种 backend：

| 模式 | 能力 | 适用场景 |
|---|---|---|
| in-process | 只采当前进程，应用控制 session 和 trace 数据 | 受采样与隐私约束的应用内诊断 |
| system | 连接 `traced`，将应用事件与调度、syscall 等系统事件放到同一时间线 | 本地调试、实验室和受控测试 |

in-process backend 不需要特殊 OS 权限，适合保存应用自己的短窗口 trace。system backend 的 session 必须从进程外部控制；数据 producer 不能读回包含其他进程信息的 system trace，以避免信息泄露和侧信道风险。因此，“线上远程让普通应用自行抓取完整 system trace 并上传”不是 SDK system mode 的通用工作方式。

Android 专用且只需要 slice、async slice 或 counter 时，Perfetto 官方建议继续使用 `android.os.Trace` 或 NDK `ATrace_*`。这些事件可以进入 Perfetto，接入成本也低于引入完整 C++ SDK。已有 native 子系统、需要自定义 protobuf data source 或独立 in-process session 时，再评估 Perfetto SDK。

无论使用哪种方式，都要限制时长、buffer、类别与触发频率。trace tag 不记录账号、URL 参数、文本内容和其他敏感数据。

## 可视化与归因平台

### Android Vitals

Android Vitals 从允许自动分享使用情况与诊断数据的部分设备收集数据，并排除未认证设备以及未通过 Google Play 安装的应用版本。它不代表全部安装用户。

它适合提供统一的外部口径：

- 用户感知 ANR 率、ANR 率与 cluster；
- 冷、温、热启动 TTID；
- UI Toolkit 应用的慢帧与冻结帧；
- 游戏的 Slow Sessions；
- crash、LMK 和部分电量指标。

当前 Play 的 user-perceived ANR 只计入 `Input dispatching timed out`，分母按日活用户定义。这个口径可能演进，应在数据字典中保存外部文档版本。bad behavior threshold 统一在 §15.3 维护，避免多章复制后出现不一致。

Vitals 的 UI Toolkit 渲染统计不覆盖直接 OpenGL/Vulkan 主画面；游戏应看由 SurfaceFlinger 数据计算的 Slow Sessions。数据按日更新且可能晚到，发布当天的早期结论需要结合覆盖率。

### 第三方 APM 与自建系统

选择平台时，不应只比较图表数量。需要核对：

- Android 17、动态刷新率与多窗口支持；
- 帧、启动和 ANR 的采集源及算法版本；
- 原始事件、聚合结果和 artifact 的导出能力；
- 国内外网络、离线队列、退避与流量预算；
- 数据驻留、加密、删除和访问审计；
- 自定义 scene、interaction 与发布维度；
- 与 issue、发布灰度和负责人系统的关联。

自建系统通常由客户端 SDK、消息接收、流式或批量聚合、指标存储、artifact 存储、查询与报警组成。技术选型随组织基础设施变化，文章不绑定固定消息队列或数据库。比组件名称更值得固定的是 schema、分母、采样权重、数据保留和访问权限。

## 平台与客户端的职责

| 客户端 | 平台 |
|---|---|
| 采集平台信号和业务上下文 | 维护指标定义、分母与算法版本 |
| 控制采样、缓冲和上传预算 | 做采样校正、分群与发布对照 |
| 在异常前后保存有限证据 | 管理 SLO、报警、聚类与样本回查 |
| 上报丢弃、限流和功能状态 | 监控覆盖率、延迟与数据完整性 |
| 执行隐私最小化 | 执行访问、保留与删除策略 |

客户端无法凭一条回调完成总体判断，平台也无法从缺少现场的聚合曲线恢复线程栈。两侧通过版本化事件协议协作，才可以把趋势定位到可复现样本。

## 在 Perfetto 中核对线上结论

线上事件应能映射到线下证据：

- 帧异常：在 FrameTimeline 查看 `actual_frame_timeline_slice`、`expected_frame_timeline_slice`，再关联主线程、RenderThread、GPU 与 SurfaceFlinger；
- 启动异常：从启动请求、进程创建、bindApplication、首帧到 `reportFullyDrawn()` 对齐系统与应用切片；
- ANR：查看主线程运行/睡眠状态、锁等待、Binder 调用、调度延迟以及 `am_anr` 等系统事件；
- 业务阶段：用 `android.os.Trace` 或 ATrace tag 把线上 scene 与 trace slice 对应起来。

一条客户端帧时长不能独自断言 GPU 或 SurfaceFlinger 是瓶颈。一条 watchdog 记录也不能独自断言系统已经判定 ANR。Perfetto、ANR trace、`ApplicationExitInfo` 和版本对照提供了各自范围内的证据。

## 常见误区

- 用 FrameCallback 次数计算“实际呈现 FPS”，忽略窗口是否产出新 buffer。
- 在 API 24—30 用名义刷新周期冒充 FrameMetrics 的精确 `DEADLINE`。
- 异步持有 JankStats 的 `FrameData`，忽略对象会被下一帧重用。
- 用 `onWindowFocusChanged()` 作为 TTID，或把 `attachBaseContext()` 当作系统 launch 起点。
- 把 App Startup 描述成启动监控库。
- 把 watchdog 的主线程停顿候选计入系统 ANR 率。
- 在 Android 17 的普通应用中监听 `/data/anr/traces.txt`。
- hook SIGQUIT 后影响 ART SignalCatcher 的系统取栈。
- 用异常触发样本计算总体发生率。
- 改变采样率、jank 算法或桶边界，却不升级 schema。
- 把 View 渲染指标用于 OpenGL/Vulkan 游戏主画面。
- 报警只有阈值，没有样本量、覆盖率和发布对照。

## 接入顺序

1. 写出指标合同：区间、分母、时钟、source、版本和隐私等级。
2. 接入低开销基线：JankStats/FrameMetrics、启动记录、退出历史与 watchdog 候选。
3. 建立 scene、interaction、session 和 process 关联。
4. 增加稳定头部采样、设备端聚合、丢弃计数和离线上传。
5. 建立覆盖率、延迟、schema 与采样概率的数据健康面板。
6. 将 SLO、发布对照、最小样本量和多窗口规则接入报警。
7. 为异常样本配置 `ProfilingManager`、in-process trace 或受控复现。
8. 定期用 Perfetto、Macrobenchmark、ANR trace 和 Android Vitals 交叉核对。

## 与其他章节的关系

- §2.4、§7.1、§8.1 解释 Choreographer、FrameTimeline 与图形流水线。
- §7.3 提供卡顿归因步骤。
- §9.3 解释系统 ANR 类型、超时与 trace 分析。
- §14.9 说明自动化测试与 Macrobenchmark 回归门禁。
- §15.3 定义指标合同、SLO 与 Google Play 外部口径。
- §15.4 讨论跨应用测量时的可比性。
- §15.9 将监控、实验、修复和验证组织成持续流程。
- §15.10 讨论团队责任与发布机制。

## FAQ

### 帧监控会不会制造新的卡顿？

开销取决于回调中的工作量和采样覆盖。回调只复制少量字段、更新固定桶并写入有界内存队列时，风险可控；逐帧分配大对象、输出日志、序列化或同步写盘会污染测量。上线前要用 Macrobenchmark、Perfetto 和功耗测试比较开启/关闭监控的差异。

### API 30+ 还有必要保留 watchdog 吗？

两者记录的事件不同。`ApplicationExitInfo` 在后续进程提供退出证据，watchdog 能在当前进程记录主 Looper 长停顿，包括恢复且未退出的样本。可以同时保留，但字段和看板要区分 `candidate` 与 `REASON_ANR`。

### API 37 的 ANR warning 能阻止 ANR 吗？

不能保证。回调按尽力而为执行，可能没被调用，也可能来不及完成。它适合复制已经存在于内存中的诊断上下文，业务修复仍要消除主线程阻塞、超时组件或资源争用。

### 采样率提高后，指标一定更可信么？

更大的随机样本通常降低抽样误差，但无法修复选择偏差、错误分母、字段缺失和算法变化。采样概率、覆盖分群与数据健康比单一百分比更有解释力。

### 第三方 APM 能否覆盖业务指标？

它能提供通用信号和平台能力。首屏目标内容可用、下单链路某阶段完成等业务终点仍需应用定义。自定义指标也要沿用同一套时钟、采样、schema 和隐私规则。

## 参考资料

### AOSP android-17.0.0_r1

- `frameworks/base/core/java/android/view/Choreographer.java`
- `frameworks/base/core/java/android/view/FrameMetrics.java`
- `frameworks/base/core/java/android/view/Window.java`
- `frameworks/base/core/java/android/app/ApplicationExitInfo.java`
- `frameworks/base/services/core/java/com/android/server/am/ProcessErrorStateRecord.java`
- `frameworks/base/services/core/java/com/android/server/am/StackTracesDumpHelper.java`
- `art/runtime/signal_catcher.cc`
- `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`
- `packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java`

### 官方文档

- [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
- [JankStats Library](https://developer.android.com/topic/performance/jankstats)
- [ApplicationStartInfo](https://developer.android.com/reference/android/app/ApplicationStartInfo)
- [ActivityManager](https://developer.android.com/reference/android/app/ActivityManager)
- [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [ApplicationExitInfo.AnrInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo.AnrInfo)
- [AnrWarningResult](https://developer.android.com/reference/android/app/AnrWarningResult)
- [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [App startup time](https://developer.android.com/topic/performance/vitals/launch-time)
- [Jetpack App Startup](https://developer.android.com/topic/libraries/app-startup)
- [ANRs](https://developer.android.com/topic/performance/vitals/anr)
- [Slow rendering](https://developer.android.com/topic/performance/vitals/render)
- [Slow Sessions](https://developer.android.com/topic/performance/vitals/slow-session)
- [Android Vitals data definitions](https://support.google.com/googleplay/android-developer/answer/9844486)
- [Perfetto Tracing SDK](https://perfetto.dev/docs/instrumentation/tracing-sdk)
