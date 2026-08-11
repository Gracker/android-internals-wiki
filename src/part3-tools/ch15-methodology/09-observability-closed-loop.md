---
title: "从采集到治理的反馈回路"
chapter: "15.9"
section: "15.9"
status: ready-for-review
drafted_date: "2026-04-21"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) – Android 17 (API 37)"
last_verified: "2026-08-08"
last_verified_against: "AndroidX metrics-performance 1.0.0 sources（FrameData.copy、JankStats.createAndTrack、JankStatsApi31Impl DEADLINE overrun）；Android 17 / API 37 / AOSP android-17.0.0_r1；Android Vitals 与 Perfetto 官方文档；2026-08-08 deep review verified source anchors, version boundaries, and body markers"
last_rework_at: "2026-08-07T13:42:07+08:00"
last_rework_run_id: "20260807-133523-rework-26b6fba8"
last_rework_log: "logs/rework/2026-08-07-20260807-133523-rework-26b6fba8-rework.md"
rework_result: "ready-for-review"
rework_notes: "2026-08-07 rework：复核上游质量标记；正文未发现未闭合核验标记，补充来源边界段，frontmatter 保留 AndroidX/Android Vitals/Perfetto/AOSP android-17.0.0_r1/android17-6.18 source anchors；章节回流 ready-for-review 等待 Task6/Task9 复审。"
confidence: medium-high
last_deep_review_at: "2026-08-08T20:35:37+08:00"
last_deep_review_run_id: "20260808-203537-deep-review-26b6fba8"
last_deep_review_log: "logs/deep-review/2026-08-08-20260808-203537-deep-review-26b6fba8-deep-review.md"
deep_review_result: "ready-for-review"
deep_review_notes: "2026-08-08 deep review：抽查 JankStats FrameData.copy/createAndTrack、FrameMetrics.DEADLINE overrun、ApplicationExitInfo 与 Perfetto 边界；正文仅做结构层级和措辞收敛，未提升平台上限；无 P0/P1。"
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "https://developer.android.com/topic/performance/jankstats"
  - type: source
    path: "https://dl.google.com/dl/android/maven2/androidx/metrics/metrics-performance/1.0.0/metrics-performance-1.0.0-sources.jar"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java"
  - type: source
    path: "https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java"
  - type: official
    path: "https://perfetto.dev/docs/instrumentation/track-events"
  - type: official
    path: "https://perfetto.dev/docs/getting-started/in-app-tracing"
  - type: source
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6"
tags: [observability, apm, pipeline, governance, monitoring]
related_chapters: ["7.1", "8.1", "9.1", "14.10", "15.3", "15.5", "15.6", "15.10"]
pipeline_stage: ready-for-review
task6_state: pending-review
task6_result: rework-applied
reviewed_date: 2026-07-04
reviewed_by: openclaw-task6
last_task6_at: 2026-07-04T13:09:00+08:00
task9_state: pending-review
repaired_date: "2026-04-22"
repaired_by: "codex"
task9_result: rework-applied
task9_reviewed_date: "2026-07-04"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-04T18:20:00+08:00"
last_task6_audit: "2026-07-04"
last_task6_audit_log: "logs/review/2026-07-03-07-audit.md"
last_task9_audit: "2026-07-04"
last_task9_idle_audit: "2026-07-04"
task2b_state: finalized
task2b_result: finalized
task2b_verifier_note: "2026-07-04T18:20:00+08:00 Auto-promoted to finalized: Task9 pass-tech-review (0 P0/P1), Task6 pass-light-edit, queue empty for this section"
last_task2b_rework_at: "2026-07-04T12:52:06+08:00"
last_task2b_rework_log: "Task2B 2026-07-04: 按 Task9 Deep Review 问题单修复 JankStats API 完整声明、异常→Backlog SLA 映射、版本声明一致性、多租户数据隔离、告警阈值参考。"
auto_promoted: true
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-24"
---
# 从采集到治理的反馈回路

## 监控系统何时开始失效

一套平台可以持续接收指标，却无法回答某次回归由谁处理、依据是什么、修复是否有效。数据采集只完成了观测工作，治理还要求异常经过识别、调查、流转和验收。

判断回路是否运转，不看图表数量，检查一条异常能否形成以下记录：

- 明确的指标契约、受影响人群与开始时间；
- 可以回查的会话、进程、页面和证据；
- 责任人、优先级、处理时限与当前状态；
- 修复版本、验证范围、对照基线和回滚条件；
- 验收结论以及没有解决时的后续动作。

任一项长期缺失，监控数据都会与工程工作脱节。常见表现包括告警重复、工单没有证据、同类问题反复调查，以及修复上线后无人核对结果。

技术边界限于公开的 AndroidX `metrics-performance:1.0.0` 源码、Android Vitals 与 Perfetto 官方文档，以及 AOSP `android-17.0.0_r1` / Android common kernel `android17-6.18` 可核验接口。阈值与 SLA 均用于说明团队内部治理方法；具体产品红线还要在工单或规则旁记录分母、样本量和制定依据，不能从通用示例外推出平台结论。

## 先区分四种数据

指标、事件、trace 和工单解决的问题不同。将它们放进同一张宽表，常会丢失各自的语义。

| 数据类型 | 适合回答 | 不适合单独回答 |
|---|---|---|
| 指标与分布 | 发生率、分位数、趋势、分群差异 | 单个样本的执行路径 |
| 事件与会话时间线 | 某次操作经历了哪些阶段 | 系统调度或跨进程根因 |
| trace、profile、heap、ANR trace | 线程、调用、锁、调度、内存等现场 | 整体用户影响 |
| 工单与发布记录 | 谁处理、何时发布、如何验收 | 运行时技术证据 |

指标负责发现异常，样本证据负责缩小调查范围，代码和实验负责确认因果，工单负责推进状态。trace 与异常时间相邻只能建立相关性；归因还要结合线程状态、调用关系、版本变化和可重复实验。

## 治理回路的八个阶段

### 1. 采集：先定义问题，再选 API

采集设计从用户问题和指标契约开始。每个指标至少写清：

- 事件起点、终点和单位；
- 分子、分母与排除条件；
- 一个用户、设备、会话或事件如何去重；
- 哪个线程和时钟产生时间戳；
- 支持的 Android 与库版本；
- 采样概率、数据保留期和隐私级别。

同名指标若定义不同，不应合并。Play Console 的 user-perceived ANR rate 以日活用户为分母；客户端上报的“ANR 次数 / 启动次数”采用另一分母，两条曲线不能直接比较。

#### 帧信号：JankStats 的准确边界

AndroidX 版本固定为 `androidx.metrics:metrics-performance:1.0.0`。源码中的入口是 `JankStats.createAndTrack(window, JankStats.OnFrameListener)`，回调参数是 `FrameData`，不存在 `FrameData.getFrames()`。

JankStats 按 Window 工作。API 24 及以上基于 `FrameMetrics`，更早版本回退到 `OnPreDrawListener`；讨论范围从 API 26 开始。所有版本都提供 `frameStartNanos`、`frameDurationUiNanos`、`isJank` 和 `states`。API 24 及以上的对象可表现为 `FrameDataApi24`，增加 `frameDurationCpuNanos`；API 31 及以上可表现为 `FrameDataApi31`，再增加 `frameDurationTotalNanos` 和 `frameOverrunNanos`。

`FrameDataApi31.frameOverrunNanos` 来自 `FrameMetrics.TOTAL_DURATION - FrameMetrics.DEADLINE`。它为正表示帧超过平台给出的 deadline，为负表示仍有余量。`isJank` 由 JankStats 的 UI duration heuristic 判断，默认 multiplier 为 2；这两个字段的判定口径不同。

下面的代码只演示安全地接收帧数据并标记页面状态。`frameSink` 应由业务实现为有界、非阻塞的内存队列，上传和聚合放到其他线程。

```kotlin
class FeedActivity : AppCompatActivity() {
    private lateinit var jankStats: JankStats

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_feed)

        jankStats = JankStats.createAndTrack(window) { volatileFrameData ->
            frameSink.offer(volatileFrameData.copy())
        }

        val state =
            PerformanceMetricsState
                .getHolderForHierarchy(window.decorView)
                .state
        state?.putState("screen", "feed")
    }

    override fun onDestroy() {
        jankStats.isTrackingEnabled = false
        super.onDestroy()
    }
}
```

`OnFrameListener` 收到的内部对象会在下一帧复用，回调返回后原引用已经不适合保存；代码在回调内调用 `copy()`。API 24 及以上回调运行在 FrameMetrics 使用的线程，API 23 及以下运行在主线程。无论版本如何，回调都不应做序列化、文件 I/O 或网络请求。状态值也要限制基数，不要把内容 ID、用户输入或完整 URL 写进 `states`。

JankStats 适合应用内页面和交互分群。定位某次慢帧仍要依赖系统 trace、FrameTimeline、RenderThread、SurfaceFlinger 与调度信息；JankStats 事件不能替代这些现场证据。

#### 进程退出：ApplicationExitInfo 的准确边界

`ApplicationExitInfo` 从 Android 11 / API 30 提供。Android 17 的 `ActivityManager.getHistoricalProcessExitReasons()` 返回最近到最早的记录；系统使用有限环形缓冲，因此记录可能被覆盖。普通应用只能查询本 UID 的包，查询其他 UID 需要 `DUMP` 权限。

下面的代码在新进程启动后读取本 UID 最近的退出记录，并映射成轻量字段。调用方应在工作线程执行，不要阻塞启动主线程。

```kotlin
data class ExitSummary(
    val timestampMillis: Long,
    val processName: String,
    val pid: Int,
    val reason: Int,
    val importance: Int,
    val pssKb: Long,
    val rssKb: Long,
)

@WorkerThread
@RequiresApi(Build.VERSION_CODES.R)
fun loadRecentExits(context: Context): List<ExitSummary> {
    val activityManager = context.getSystemService(ActivityManager::class.java)
    return activityManager
        .getHistoricalProcessExitReasons(null, 0, 20)
        .map { info ->
            ExitSummary(
                timestampMillis = info.timestamp,
                processName = info.processName,
                pid = info.pid,
                reason = info.reason,
                importance = info.importance,
                pssKb = info.pss,
                rssKb = info.rss,
            )
        }
}
```

返回的 PSS/RSS 单位是 kB，数值来自系统对进程的上一次采样，不等于死亡瞬间内存；系统来不及采样时会是 0。调用者应按进程名、pid、timestamp、reason 等字段去重，并保存“已处理游标”，否则每次启动都会重复上报同一批记录。pid 会复用，不能单独充当记录 ID。

`ApplicationExitInfo.getTraceInputStream()` 通常可为 ANR 提供 trace；API 31 及以上的 native crash 可能返回 protobuf tombstone。它允许返回 `null`，原因包括全局缓冲覆盖和平台未保留数据。ANR 恢复后进程又因其他原因死亡时，退出记录仍可能带着先前 ANR trace，因此要同时保留 `reason`、timestamp 与 trace 元信息，避免把 trace 类型直接等同于退出原因。

`ActivityManager.setProcessStateSummary()` 可以把最多 128 byte 的业务状态带入后续退出记录。Android 17 源码注明该接口可能限流，并明确禁止写入敏感信息。适合存放版本化的小型枚举或 feature bit，不适合 UI 恢复，也不适合频繁更新。

API 26—29 没有等价的退出历史 API。`getRunningAppProcesses()` 只描述调用时仍在运行的进程，无法恢复已经消失的退出原因。旧系统需要组合崩溃上报、Play Console、服务端会话缺口和下一次启动标记；这些信号仍无法完整区分 LMKD、force-stop、系统终止和进程崩溃。

#### 版本边界

| 平台范围 | 帧数据 | 进程退出 | 系统级现场 |
|---|---|---|---|
| Android 8—10 / API 26—29 | JankStats 经 FrameMetrics；也可直接使用 FrameMetrics | 无 ApplicationExitInfo | Perfetto/atrace、bugreport、开发设备 ANR 文件 |
| Android 11 / API 30 | 同左 | ApplicationExitInfo | Perfetto system trace |
| Android 12—17 / API 31—37 | JankStats 可返回 FrameDataApi31；系统 trace 可看 FrameTimeline | ApplicationExitInfo；native tombstone stream 从 API 31 开始 | FrameTimeline、sched、Binder、memory、power 等 |

Android 17 的 `FrameMetrics.java` 含 `DEADLINE` 与 `FRAME_TIMELINE_VSYNC_ID`。`metrics-performance:1.0.0` 的 `JankStatsApi31Impl` 使用 `DEADLINE` 计算 overrun，但 `FrameData` 没有公开 VSync ID 字段。需要逐帧跨 app、HWUI 和 compositor 对齐时，应采集 FrameTimeline，而不是从 JankStats 推导一个不存在的 ID。

### 2. 采样：让概率和证据链都可解释

轻量计数器也会消耗 CPU、网络、电量和存储；trace、heap 与 profile 的成本更高。采样策略应包含明确预算：

- **基线采样**：对轻量事件采用固定概率或确定性 hash，保存 `sample_rate` 或 inclusion probability；
- **分群采样**：提高新版本、灰度、重点设备或新功能的覆盖，同时保留未加权与加权结果；
- **会话采样**：会话开始时作出一次决定，使启动、页面、网络和帧事件能够关联；
- **异常补采**：本地有界环形缓冲保留异常前后少量上下文，触发后再固化允许上传的部分；
- **诊断任务**：trace、profile、heap 等重证据通过远程配置限定版本、设备、时长、次数与截止日期。

按异常触发的样本天然偏向慢设备和失败会话，不能拿它估算总体发生率。总体指标来自概率已知的基线样本；异常样本用于调查。采样规则发生变化时提高 schema/config 版本，避免趋势图把策略变化显示成性能变化。

诊断采集要设置止损条件：单日设备配额、全局字节预算、温度/电量/网络限制、服务端熔断和远程关闭。触发采集也要遵守用户授权、商店政策和适用地区的数据要求。

### 3. 聚合：分母、分群和样本量同屏展示

单次事件用于回查，趋势判断依赖分布。常见维度包括：

- app version、build、channel、experiment；
- SDK level、设备型号、SoC/GPU、ABI、刷新率；
- page、scene、startup type、前后台与多窗口状态；
- 网络类型、thermal 状态和内存档位；
- 数据源、schema version、sampling config。

维度越多，稀疏分组越多。平台应限制 metric label 的基数，把 `session_id`、`trace_id`、原始设备标识等高基数字段留在事件索引中。设备型号还要做最小样本门槛，避免一个用户或一台测试机制造醒目的百分比。

聚合侧至少保留 count、分母、缺失率、时间窗和分布摘要。不能平均各机型 P95 得到全局 P95，也不能把不同刷新率下的“超过 16.67 ms”统一叫慢帧。帧指标优先使用 deadline/overrun 或明确的刷新率预算。

Play Vitals 与自建指标可以放在同一治理页面，但要标出来源。官方当前对 user-perceived ANR rate 的定义是：一天内至少遇到一次 input dispatching timeout 的日活用户占比。Google Play 公布的 bad behavior threshold 是全局 0.47%、单设备型号 8%。这是 Play 的发布质量边界，不等于团队内部告警必须等到该值才触发。

### 4. 归因：从群体异常走到单个证据

归因页需要同时提供分群变化和可回查样本。建议按以下顺序工作：

1. 确认指标定义、数据完整性、采样配置和 schema 是否变化。
2. 找出异常开始的 build、时间窗和受影响分群。
3. 对照发布、远程配置、服务端和系统环境变化。
4. 选择同分群的正常与异常样本，比较阶段耗时。
5. 打开 trace、ANR trace、stack、heap 或退出记录，沿执行关系调查。
6. 用本地复现、benchmark、开关实验或回滚验证假设。

常用责任方向包括 App MainThread、RenderThread/GPU、SurfaceFlinger/显示链路、Binder/system_server、文件与网络 I/O、内存/GC、CPU 调度、thermal 以及厂商实现。平台可以给出候选分类，不应在缺少调用链时把候选写成结论。

### 5. 告警：把发布红线与内部预警分开

告警规则至少包含：

- 指标与分群；
- 绝对门槛或相对基线；
- 最小分子、分母和完整窗口数；
- 新问题、持续问题与恢复的判定；
- owner、值班渠道、静默与合并规则；
- 回查链接和期望动作。

固定阈值适合稳定的用户体验边界；动态基线适合季节性、地域和流量变化。两者可以同时使用。发布阻断采用明确预算，日常预警采用较低门槛和连续窗口，容量异常采用增长速度与剩余空间。

“TTFD 2.5 s”“Binder P99 50 ms”“每分钟 3 个 frozen frame”缺少产品基线和官方来源，不能作为通用 SLA。团队应从自身 SLO、历史分布、用户影响、样本量和处理能力推导阈值，并在规则旁记录制定日期与依据。

告警消息应描述“发生了什么”，例如“版本 B 的 Feed warm start P95 相对同设备分群的版本 A 上升，样本量满足门槛”。归因结果在证据确认后补充。这样可以避免把网络波动、采样切换或设备构成变化提前写成代码根因。

### 6. 回查：连接键要稳定，也要控制基数

以下键分别服务于不同范围：

| 键 | 生命周期与用途 |
|---|---|
| `event_id` | 单个事件幂等、重试去重 |
| `session_id` | 一次前台或业务会话；会话结束后轮换 |
| `page_instance_id` | 一次页面实例，区分同页多次进入 |
| `trace_id` | 一次跨阶段或跨服务请求；可为空 |
| `process_instance_id` | 一次进程生命周期，避免仅依赖复用的 pid |
| `build_id` / `version_code` | 对齐二进制、mapping 与 native symbol |
| `sampling_config_version` | 解释采样率和触发策略变化 |

这些 ID 适合事件查找，不适合进入时序指标标签。ID 应随机生成或采用不可逆、可轮换的伪标识，不能把帐号、手机号、广告 ID 或设备硬件标识直接编码进去。

时间字段至少区分 wall clock 与 monotonic clock。服务端排序和跨设备查询使用 UTC wall time；进程内阶段耗时使用 `elapsedRealtimeNanos()` 或库定义的 monotonic 时间。JankStats 的 `frameStartNanos` 不能直接与服务端毫秒时间戳相减。跨进程系统 trace 的时钟对齐交给 Perfetto clock snapshot 与 Trace Processor，业务上传数据则需要记录自己的时钟语义。

### 7. 修复：异常进入 backlog 时要携带证据

一条可执行的性能工单应包含：

- 指标契约链接、异常时间窗和影响分群；
- 基线版本、回归版本、绝对值与变化量；
- 样本量、采样策略和数据缺口；
- 正常/异常样本及 trace、ANR、heap 等受控链接；
- 已验证事实、仍需确认的假设和候选 owner；
- 优先级依据、计划版本、风险与回滚条件；
- 线下测试与线上验收指标。

优先级通常由用户影响、发生范围、严重度、持续时间、证据置信度和修复风险共同决定。技术耗时不能单独决定优先级；一次 200 ms Binder 调用若位于不可见后台路径，与每次输入都发生的 40 ms 调用，用户影响不同。

状态机可以采用 `detected → triaged → investigating → fixing → validating → resolved`，并为 `false-positive`、`duplicate`、`cannot-reproduce` 和 `accepted-risk` 保留明确终态。每次状态变化记录操作者、时间和理由，避免“关闭”同时表示已修复、暂不修复和数据错误。

### 8. 验收：确认用户指标与技术证据同时改善

修复合入只代表实现完成。验收需要回答：

- Macrobenchmark 或可重复实验是否覆盖原场景；
- 同设备、同网络、同启动类型下技术指标是否改善；
- 修复版本在线上是否达到预设成功条件；
- crash、ANR、内存、能耗或功能正确性是否回归；
- 灰度期是否足够覆盖工作日、周末和长尾设备；
- 未达到目标时是回滚、继续观察还是重新调查。

前后版本比较要控制设备构成、流量和配置变化。具备灰度或实验条件时，优先比较同时段对照组；只能做前后对比时，保留相同分群并说明外部变化。验收窗口、最小样本和成功门槛应在发布前写入工单，避免看完结果再选择口径。

治理系统还要记录负向结果。某次优化在线下减少 10 ms，却没有改变线上 tail，可能说明目标函数选错、场景覆盖不足或线上瓶颈位于其他阶段；这个结论应回到知识库和后续实验设计。

## 从指标到 trace 的关联设计

Perfetto Track Event 提供 slice、counter 和 flow。slice 表示一段工作，counter 表示随时间变化的值，flow 连接不同 track 上相关的事件。对于 native 代码，Perfetto SDK 可将自定义 Track Event 写入应用内 trace，也可连接 Android 的 system backend，与 sched、Binder、FrameTimeline 等系统数据共同采集。

Java/Kotlin 代码可以使用平台或 AndroidX tracing 注解把业务阶段放入 system trace。事件名保持低基数，例如 `FeedLoad`；动态 ID 作为参数或业务事件字段保存，不要把每个内容 ID 拼进事件名。trace 里仍可能出现 URL、查询参数、文本和业务对象，上传前要做字段审计。

指标事件与 trace 常见的连接方式有两种：

- 异常事件保存 trace artifact ID，并由受控后端返回短期访问链接；
- 业务阶段同时写入稳定的 request/flow 标识，使事件时间线可以定位 trace 中对应 slice。

平台应允许从聚合图进入异常分群，再进入若干匿名样本；也应允许从单个 trace 返回同版本、同设备类和同场景的发生率。前者回答“哪里变坏”，后者回答“这个现场是否具有代表性”。

## Schema 演进与存储成本

### 事件信封

通用事件信封建议包含：

| 字段 | 约束 |
|---|---|
| `event_name`、`event_schema_version` | 含义变化时升版本，旧 reader 可拒绝不支持的版本 |
| `event_id` | 客户端重试幂等，不进入指标 label |
| `occurred_at_unix_ms` | UTC wall time，并记录客户端时钟异常 |
| `elapsed_realtime_ns` | 进程/设备内时序，禁止跨设备直接比较 |
| `app_version_code`、`build_id` | 对齐代码、mapping、symbols |
| `sdk_int`、`device_class` | 系统版本与受控设备分组 |
| `session_id`、`process_instance_id`、`page_instance_id` | 可轮换的匿名关联键 |
| `sample_rate`、`sampling_config_version` | 支持加权、审计策略变化 |
| `payload` | 事件专属字段，遵守大小、基数和隐私限制 |

新增可选字段通常保持向后兼容；删除字段或改变单位需要新 schema 版本。字段重命名不能只改 dashboard，因为离线任务、告警和历史数据仍依赖旧语义。生产者、消费者和指标定义应在同一变更记录中说明兼容窗口。

### 热数据、冷数据和诊断附件

存储可按用途分层：

- 热层保存近期聚合与可检索事件，服务告警和日常调查；
- 冷层保存降采样后的长期趋势，用于版本与季度比较；
- trace、heap、tombstone 等附件单独加密存储，设置更短 TTL、访问审计和下载权限；
- 原始事件超过保留期后删除，派生指标保留其 schema、采样和计算版本。

每个数据源都应有事件大小、日量、保留天数、查询成本和删除机制。没有 owner 或查询记录的数据源应进入停采评估。诊断任务结束后关闭补采配置，防止一次调查演变成长期成本。

### 多租户隔离

`tenant_id` 应由受信任的服务端身份或发布配置确定，不能相信客户端任意上报的租户值。查询层必须强制执行 tenant + role 授权；在 session 前缀中加入租户名只避免 ID 碰撞，不构成访问隔离。

逻辑分区、独立表、独立库或独立实例应根据监管、故障域、规模和成本选择。无论采用哪种存储，附件对象、缓存、导出任务、告警渠道和审计日志都要携带租户边界。跨租户查询必须经过单独授权并留下审计记录。

## 一个可运行的最小回路

小团队可以从一个黄金场景开始，例如 Feed warm start：

1. 固定 TTID/TTFD、帧 overrun 和退出原因的指标契约。
2. 采用会话级基线采样，保存版本、设备类、场景和采样配置。
3. 为异常会话保留小型时间线；诊断期对指定分群采集少量 system trace。
4. 每个工作日检查自动分群结果，满足规则时创建带证据的工单。
5. 用 Macrobenchmark 守住线下回归，用灰度分群验证线上 tail。
6. 验收后关联 commit、build、工单与指标窗口；失败则恢复调查状态。

这套最小实现不要求自建完整 APM。Play Vitals、现有事件系统、对象存储、工单系统和测试流水线可以分别提供能力，连接键与状态规则把它们组成可追踪的过程。

## 常见失效模式

| 现象 | 常见原因 | 修正方向 |
|---|---|---|
| 全局曲线稳定，用户仍投诉 | 均值掩盖尾部或设备分群 | 看分位数、失败率和重点设备 |
| 告警发布后突然增加 | schema、采样或设备构成变化 | 先审计数据变更，再调查代码 |
| 工单长期无 owner | 告警只给现象，没有分群和证据 | 增加 triage 责任与回查入口 |
| 同一事件重复上报 | 客户端重试没有幂等键 | 用 event_id 去重并监控重试 |
| trace 很完整，无法判断影响 | 只有诊断样本，没有基线分母 | 保留概率已知的轻量指标 |
| 修复上线后结论反复 | 验收门槛在看数据后才确定 | 发布前固定窗口、样本和目标 |
| 查询成本持续增长 | 高基数标签、无限保留原始数据 | 分离事件与指标，设置 rollup/TTL |
| 多业务线可互相看到附件 | 只在 UI 过滤 tenant | 在鉴权、查询、对象存储全程校验 |

## 与其他章节的关系

- §7、§8、§9 描述流畅性、启动和 ANR 的机制与证据。
- §15.3 定义指标契约和分母。
- §15.5 讨论线上采集、保护开关和监控实现。
- §15.9 把指标、样本、工单、发布与验收组织成持续过程。
- §15.10 继续讨论团队责任、门禁和长期运行。

Android 平台源码锚点固定为 `android-17.0.0_r1`，最高平台版本为 Android 17 / API 37。涉及 sched、cgroup、Binder driver 等内核证据时，使用 `android17-6.18-2026-06_r6`；厂商设备必须对照设备对应的 kernel build 与源码。JankStats 属于 AndroidX 库，版本边界单独固定为 `metrics-performance:1.0.0`，不能用平台 API 37 代替库版本。

## 参考资料

- [Android Vitals](https://developer.android.com/topic/performance/vitals)
- [Android Vitals：ANRs](https://developer.android.com/topic/performance/vitals/anr)
- [JankStats 官方指南](https://developer.android.com/topic/performance/jankstats)
- [AndroidX metrics-performance 1.0.0 sources](https://dl.google.com/dl/android/maven2/androidx/metrics/metrics-performance/1.0.0/metrics-performance-1.0.0-sources.jar)
- [ApplicationExitInfo API](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android 17 `ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [Android 17 `ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [Android 17 `FrameMetrics.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/FrameMetrics.java)
- [Perfetto Track Event](https://perfetto.dev/docs/instrumentation/track-events)
- [Perfetto in-app tracing](https://perfetto.dev/docs/getting-started/in-app-tracing)
- [Android common kernel `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6)
