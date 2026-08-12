---
title: "稳定性度量与指标体系"
chapter: "20.6"
section: "20.6"
status: "finalized"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-10"
last_verified_against: "AOSP android-17.0.0_r1 RuntimeInit/ActivityManagerConstants/BroadcastConstants/ContentResolver/ContentProviderClient/ContentProviderHelper/ApplicationExitInfo/InputDispatcher; developer.android.com Android Vitals/ANR/FGS docs; Google Play Console"
confidence: medium
sources:
  - type: official
    path: "https://support.google.com/googleplay/android-developer/answer/9844486"
  - type: clippings-structure-ref
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java"
tags: [metrics, crash-rate, anr-rate, play-vitals, slo, dashboard]
related_chapters: ["20.1", "26.1", "15.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_state: "fixed"
---

# 稳定性度量与指标体系

20.1 节说明了 Crash、ANR 与 OOM 的边界。同一批故障数据还要算出可以解释、可以复算、可以指导发版的指标。

这里的平台基准是 Android 17（API 37，`android-17.0.0_r1`）。Google Play 和 Firebase 的统计规则独立于 AOSP 版本，文中的阈值与产品口径按 2026 年 7 月的官方文档核对。把这些外部数字写进长期门禁之前，仍要确认服务端文档没有更新。

## 先确定统计对象

“崩溃率”这个名字至少可能指五种分数。它们的分母不同，回答的问题也不同。

| 统计对象 | 分子 | 分母 | 回答的问题 |
|---|---|---|---|
| 活跃安装实例日 | 当天至少发生一次故障的安装实例日 | 当天活跃安装实例日 | 有多大比例的日活受到影响 |
| 用户或安装实例 | 观察期内至少发生一次 fatal 的去重实例 | 观察期内有活动的去重实例 | 观察期内有多少实例保持无崩溃 |
| 会话 | 至少发生一次 fatal 的会话 | 有效会话 | 一次使用过程有多大概率因崩溃结束 |
| 启动尝试 | 以 fatal 或进程异常退出结束的启动尝试 | 有效启动尝试 | 用户能否进入可用界面 |
| 原始故障事件 | Crash、ANR 或其他故障事件 | 启动数、会话数或运行时长 | 故障发生频率与诊断负荷 |

文档、埋点协议和 SQL 必须写出分子、分母、时间窗、范围和去重键。只写“UV 崩溃率”或“PV 崩溃率”仍然不够：UV 可能是账号、设备或安装实例；PV 在多数分析系统中表示页面浏览量，不应拿来代称 Session。

### 原始事件和派生指标分开保存

端侧至少要为一次故障携带这些关联键：

- `event_id`：一次采集事件的稳定标识，用来消除重传产生的重复记录；
- `installation_id`：经过隐私设计的安装实例标识，不要直接上传账号、IMEI 或 Android ID；
- `process_start_id`：区分同一安装实例的不同进程生命周期；
- `session_id`：由团队明确规则生成的会话标识；
- `launch_id`：一次有效启动尝试的标识；
- `cluster_id`：服务端符号化、归一化之后得到的问题簇标识。

原始事件表保留每次故障。诸如“同一安装实例、同一问题簇、五分钟只算一次”的规则只能用于派生表，不能覆盖原始事件，否则重复崩溃和 crash loop 会被数据清洗隐藏。

分母也需要可观测。会话开始记录没有成功上传、旧版本没有接入 SDK、用户关闭采集、进程在 SDK 初始化前退出，都会让指标看起来偏好。建议同时展示：

- 具备采集能力的版本覆盖率；
- 会话开始与会话结束的上报完整率；
- 崩溃本地暂存和下次启动补传的成功率；
- Java mapping、Native 符号表和 Build ID 的匹配率；
- Google Play 安装来源、用户授权和隐私门槛带来的样本范围。

遥测缺口不是脚注，它决定了指标能不能用于门禁。

## 常用 Crash 指标

### 日活受影响率

内部系统常把匿名安装实例近似为“用户”。在这种定义下，日活受影响率为：

$$
\text{Daily affected rate}
=
\frac{\text{当天至少发生一次 Crash 的去重安装实例数}}
{\text{当天活跃安装实例数}}
$$

同一个安装实例当天崩溃一次或十次，分子都只增加一。这项指标适合描述影响面，却看不出重复崩溃的严重程度。用户每天使用时长、会话次数和设备分布也会改变暴露机会，因此不同产品之间不宜直接横比。

若产品使用账号去重，必须额外说明游客、多账号和多设备的处理方式。Google Play 与 Crashlytics 都不是按业务账号统计，不能把三个系统的“用户”当成同一个实体。

### Crash-Free Users

[Firebase Crashlytics 的官方定义](https://firebase.google.com/docs/crashlytics/crash-free-metrics)是：

$$
\text{Crash-Free Users}
=
1 -
\frac{\text{观察期内发生过 fatal 的去重安装实例数}}
{\text{观察期内有活动的去重安装实例数}}
$$

Crashlytics 把一台设备上的一次应用安装视为一个 user。一个人在两台设备上安装应用，会被计为两个 user。这个指标只使用 fatal 事件；non-fatal 与 ANR 过滤条件不会进入 Crash-Free 图表。

它是整个观察期的去重聚合，并非每天 Crash-Free Users 的算术平均。观察期越长，同一实例遇到至少一次崩溃的机会越大，所以 1 天与 28 天的数值不能直接比较。

### Crash-Free Sessions

Crash-Free Sessions 的分子是“未因 fatal 结束的会话数”：

$$
\text{Crash-Free Sessions}
=
1 -
\frac{\text{发生 fatal 的去重会话数}}
{\text{全部有效会话数}}
$$

这个公式不能改写为 `1 - 崩溃事件数 / 会话数`。一个会话即使记录到多次重试或重复 fatal，上面的分子也只能计一个受影响会话。

Crashlytics 当前把冷启动视为新会话；应用进入后台至少 30 分钟后再次回到前台，也开始新会话。自建指标可以采用别的边界，但名字中要标明是内部会话，避免与 Crashlytics 数值互相校验时产生误判。

会话口径减少了“重度用户只计一个 user”的影响，却没有消除会话长度、前后台切换习惯和埋点完整率的差异。跨应用比较前，仍要确认会话定义和采集范围一致。

### 启动失败率

把 `Application.onCreate()` 到第一个 Activity `onResume()` 当作启动窗口，会漏掉 `Application.onCreate()` 之前的崩溃，也无法区分“界面出现”与“内容可用”。更稳妥的做法是为冷启动、温启动和热启动分别建立启动尝试，并为每次尝试记录终态：

- `first_frame_presented`：首帧已经提交，用户能看到界面；
- `fully_drawn`：关键内容可用，可与 `Activity.reportFullyDrawn()` 的语义对应；
- `fatal`：启动窗口内发生 Java 或 Native Crash；
- `abnormal_exit`：没有 fatal 事件，但系统记录到相关进程异常退出；
- `abandoned`：应用转入后台或用户离开，不能误算为成功。

以“关键内容可用”为成功条件时，可以计算：

$$
\text{Startup failure rate}
=
\frac{\text{以 fatal 或 abnormal\_exit 结束的有效 launch\_id 数}}
{\text{全部有效 launch\_id 数}}
$$

API 35 起，[`ApplicationStartInfo`](https://developer.android.com/reference/android/app/ApplicationStartInfo) 提供系统记录的应用启动信息；`ActivityManager.addStartInfoTimestamp()` 允许在 `reportFullyDrawn()` 之前补充开发者时间点。它们可以改善启动时间线，但进程内采集仍看不到自身启动前的所有故障，需要和 Android vitals、Crash 平台以及下次进程启动读取的退出记录互相补充。

启动门禁不应照搬一个通用百分比。支付、导航等关键路径与内容浏览应用面临的风险不同；冷启动量、灰度样本和历史波动也不同。目标应来自稳定版本基线和产品容忍度。

### 重复崩溃与 crash loop

“相同堆栈事件数 / 全部崩溃事件数”混合了问题热度、用户活跃度和重试次数，不能单独表示恢复能力。更有解释力的两个指标是：

$$
\text{Repeated-affected rate}_{cluster}
=
\frac{\text{观察期内该簇发生至少两次的受影响安装实例数}}
{\text{观察期内该簇的全部受影响安装实例数}}
$$

$$
\text{Crash-loop launch rate}_{cluster}
=
\frac{\text{连续若干次启动均命中该簇的安装实例数}}
{\text{该簇受影响安装实例数}}
$$

“连续若干次”和观察窗口要由产品的启动频率确定。例如，短时间内连续三次启动都在同一初始化簇崩溃，可以作为 crash loop 候选；低频工具应用可能需要更长窗口。这个条件是团队规则，不是 Android 系统阈值。

## Google Play Android vitals 的口径

Android vitals 使用系统侧数据，覆盖范围受安装来源、设备认证、用户数据共享选择和匿名报告门槛影响。它与自建 SDK 的数据不必完全一致。[官方 FAQ](https://developer.android.com/topic/performance/vitals)也明确列出了 SDK 初始化前故障、统计范围和分母差异。

### Crash

[Android vitals Crash 文档](https://developer.android.com/topic/performance/vitals/crash)给出三项不同指标：

| 指标 | 官方分子 |
|---|---|
| Crash rate | 当天经历过任意类型 Crash 的日活用户 |
| User-perceived crash rate | 当天在应用处于 active use 时至少经历一次 Crash 的日活用户 |
| Multiple crash rate | 当天至少经历两次 Crash 的日活用户 |

这里的 daily active user 是“单个设备上的单日活跃用户”：同一人在两台设备使用应用，会贡献两个日活；多人当天使用同一设备，只计一个日活。一次日活可以包含多个应用会话。

对手机和平板，active use 指应用正在显示 Activity 或执行 foreground service。后台组件崩溃仍会进入总体 Crash rate，只是不一定进入 user-perceived crash rate。Wear OS 有单独规则，不能沿用手机口径。

User-perceived crash rate 才是 Google Play 的 core vital。任意内部“UV 崩溃率”只有在事件范围、日活定义和采样范围均一致时，才可能与它接近。

### ANR

[Android vitals ANR 文档](https://developer.android.com/topic/performance/vitals/anr)也区分总体 ANR rate、user-perceived ANR rate 和 multiple ANR rate。当前只有 `Input dispatching timed out` 被计为 user-perceived ANR。Service、Broadcast、ContentProvider、JobService 等 ANR 仍要进入内部故障分析，但不能直接加到 Play 的 user-perceived 分子里。

各类 ANR 的系统期限和版本差异见 20.4 节。不能用一张“统一超时表”代替系统判断，因为 Input、Broadcast、Service、FGS 与 Provider 走的是不同检测路径，部分超时也会以异常退出而非 ANR 收场。

### Bad behavior thresholds

截至 2026 年 7 月，[Google Play 公布的手机阈值](https://developer.android.com/topic/performance/vitals)如下：

| Core vital | 全机型阈值 | 单手机型号阈值 |
|---|---:|---:|
| User-perceived crash rate | 1.09% | 8% |
| User-perceived ANR rate | 0.47% | 8% |

达到或超过阈值属于 bad behavior。Play 可能降低应用的可见度，也可能在商店详情页显示警告；不能把“可能”写成每次都会降权或展示标签。Play 按最近 28 天的数据评估质量，这些阈值是商店质量边界，不是团队 SLO 的推荐值。

也不能用 `100% - 1.09% = 98.91%` 推导 Crashlytics 的 Crash-Free Users 门禁。两边的故障范围、用户定义、采样范围和时间聚合均不相同。

## Android 17 下的 ANR 观测

### 四类数据各有边界

| 数据来源 | 能看到什么 | 不能据此断言什么 |
|---|---|---|
| Google Play Android vitals | Play 范围内的系统 Crash/ANR、问题簇与 core vitals | 不能代表全部安装来源，也没有应用自定义上下文 |
| 主线程 watchdog | 消息延迟、线程栈和卡顿前后的业务状态 | 检测到卡顿不等于系统已经判定 ANR |
| `ApplicationExitInfo` | API 30+ 的近期进程死亡记录；部分 ANR trace | ANR 可能恢复而不杀进程；历史记录是环形缓冲，trace 也可能为空 |
| ANR warning / profiling trigger | 系统给出的预警信息或诊断产物 | 回调和产物均为 best effort，不能当成必达事件 |

普通应用不能依赖读取 `/data/anr/`。`FileObserver` 即使能观察路径变化，也不意味着进程有权读取系统 traces。

API 30 起，`ActivityManager.getHistoricalProcessExitReasons()` 返回近期进程死亡记录。只有关联记录存在时，才能从 [`ApplicationExitInfo.getTraceInputStream()`](https://developer.android.com/reference/android/app/ApplicationExitInfo#getTraceInputStream()) 尝试读取 trace；该方法允许返回 `null`，系统的全局环形缓冲也可能已经覆盖旧数据。API 37 的 `ApplicationExitInfo.getAnrInfo()` 会在 `reason == REASON_ANR` 时提供结构化 ANR 信息，其他退出原因返回 `null`。

API 36 起，可以通过 [`ProfilingTrigger.TRIGGER_TYPE_ANR`](https://developer.android.com/reference/android/os/ProfilingTrigger#TRIGGER_TYPE_ANR) 请求系统在识别 ANR 后提供运行中的 system trace 快照。触发不表示应用一定被杀，系统也不保证每次都返回产物。

API 37 新增 [`ActivityManager.registerAnrWarningListener()`](https://developer.android.com/reference/android/app/ActivityManager#registerAnrWarningListener(java.util.concurrent.Executor,%20java.util.function.Consumer%3Candroid.app.AnrWarningResult%3E))。下面的示意代码只负责在非主线程保存轻量预警字段：

```kotlin
@RequiresApi(37)
fun registerAnrWarningCollector(
    activityManager: ActivityManager,
    executor: Executor,
    persist: (AnrWarningResult) -> Unit,
): Consumer<AnrWarningResult> {
    val listener = Consumer<AnrWarningResult> { warning ->
        persist(warning)
    }
    activityManager.registerAnrWarningListener(executor, listener)
    return listener
}
```

调用方要保存返回的同一个 `Consumer`，停止采集时传给 `unregisterAnrWarningListener()`。执行器不能是主线程，`persist` 也应有严格耗时上限。`AnrWarningResult` 提供 `anrId`、`anrType`、`consumedMillis`、`timeoutMillis` 和不保证格式稳定的描述；若事件后来成为 ANR，`anrId` 可与退出信息关联。预警回调可能缺席，也可能来不及执行，不能在这里安排网络请求或复杂恢复。

## Crash 采集与问题聚类

### 端侧只做必要工作

Java/Kotlin 未捕获异常可以由 `Thread.UncaughtExceptionHandler` 记录。自定义处理器必须把异常继续交给安装前保存的默认处理器，并限制磁盘写入量。Android 17 的 [`RuntimeInit.KillApplicationHandler`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)在 `finally` 中调用 `Process.killProcess()` 和 `System.exit(10)`；吞掉默认处理会破坏系统 Crash 语义，也可能让 OOM profiling trigger 等能力拿不到预期信号。更完整的实现和故障边界见 20.2 节。

Native Crash 不能只写成“读取 debuggerd tombstone”。普通应用不能任意读取系统 tombstone。可用数据包括自有信号处理器生成的 minidump、Crash 平台 SDK 产物，以及 API 31+ 在 `ApplicationExitInfo` 中可能提供的 `REASON_CRASH_NATIVE` protobuf tombstone。Native 符号化必须按 ABI、版本和 Build ID 找到完全匹配的未裁剪符号，详见 20.3 节。

Crash 或 ANR 时进程随时可能结束，端侧应优先写入应用私有目录的短记录，并在下次启动补传。同步网络上报、长时间加锁、大对象序列化和再次分配大量内存都会扩大失败概率。

### 聚类键不能只取前几帧

同一根因在混淆、协程、内联和版本变化后，堆栈前几帧可能变化；不同根因也可能共享顶部框架帧。聚类至少要考虑：

- Java/Kotlin：异常类型、cause 链、归一化后的应用代码根因帧、mapping 版本；
- Native：signal、fault 类型、归一化后的应用帧、ABI、Build ID 和符号版本；
- ANR：ANR 类型、主线程阻塞点、锁持有者或 Binder 对端、组件类型；
- 公共字段：应用版本、动态模块版本、Android 版本和必要的功能开关。

聚类算法更新时要保留旧 `cluster_id` 到新 `cluster_id` 的映射，否则看板会把算法变化误判成新问题或问题消失。

问题排序也不应只看事件数。建议同时展示受影响实例数、受影响会话数、重复受影响率、crash loop、是否命中启动或支付等关键路径、首次出现版本和近期增长速度。

## 看板怎样组织

一张图承载不了商店风险、发版判断、问题诊断和采集健康度。更清楚的做法是分成四层。

### 质量概览

- Play user-perceived crash rate 与 user-perceived ANR rate，标出 28 天窗口和官方阈值；
- 内部 all-crash、all-ANR 与 OOM/LMK 等分类指标；
- Crash-Free Users、Crash-Free Sessions、启动成功率；
- 当前版本覆盖率、Play 灰度比例和主要渠道占比。

不同量纲使用对齐的上下图，不用双 Y 轴制造视觉相关性。每条曲线在图例中写明数据源和分母。

### 发版对比

新旧版本对比要满足相近的日期、渠道、国家、Android 版本、机型档位与使用场景。灰度比例很小时，绝对事件数低并不表示质量更好。

比例指标应同时给出：

- 分子、分母和点估计；
- 绝对变化，例如增加 `0.03` 个百分点；
- 相对变化，例如相对基线增加 `20%`；
- Wilson 区间或其他适合二项比例的置信区间；
- 与基线同口径的版本和时间窗。

“从 0.10% 上升到 0.12%”的相对增幅是 20%，绝对增幅只有 0.02 个百分点。只展示其中一个数字都可能放大或掩盖风险。样本很小时，区间会很宽；此时应继续灰度或补充分层证据，不能把波动直接归因给新版本。

### 问题诊断

问题簇表至少包含影响实例数、事件数、受影响会话数、首次与近期出现时间、版本、机型/API 分布、符号化状态、责任模块和修复状态。Top N 是展示限制，不代表前 N 个问题必然覆盖固定比例。

机型与 API 热力图的每个格子要同时显示分母。只有三次启动的机型出现一次崩溃，点估计会很高，但证据不足以支持大范围机型屏蔽。

### 遥测健康

单独展示 SDK 覆盖率、上报成功率、延迟分布、事件重传率、会话配对率、符号匹配率和各数据源差异。采集链路异常时，质量曲线下降可能只是漏报。

## 告警与灰度门禁

固定写死“上涨 20% 就停发”会同时产生两类错误：低基数的小波动触发大量告警，高基数的严重绝对增量却可能被放过。稳健的规则通常组合四类信号：

1. **绝对质量边界**：超过团队 SLO 或 Play bad behavior threshold；
2. **相对回归**：同人群、同时间窗下显著差于稳定版本；
3. **新问题簇**：新簇命中启动、登录、支付等高风险路径；
4. **重复失败**：出现 crash loop 或同一实例短时间多次 ANR。

规则还要设置最小分母、置信条件、持续时间和恢复条件。P1/P2 的响应时限由团队值班能力与业务损失确定，不存在适用于所有 Android 应用的每日告警配额。

灰度系统应记录每次扩量、暂停和回滚的时间点。告警评估使用当时的暴露量，而不是用全量 DAU 作为新版本分母。设备、国家和渠道分层异常可以只暂停对应人群，不必在证据不足时直接推断全局回归。

## 用 SLO 和 Error Budget 管理稳定性

### SLI、SLO 与 SLA

- **SLI（Service Level Indicator）**：带完整统计规则的观测指标；
- **SLO（Service Level Objective）**：某个时间窗内 SLI 要达到的目标；
- **SLA（Service Level Agreement）**：面向外部的承诺及违约后果。

多数 Android 团队需要的是内部 SLO。若没有对客户或合作方作出带后果的承诺，不必把内部门禁称为 SLA。

一个可执行的 SLO 要写全六项：事件范围、分母、观察窗口、用户范围、数据延迟与完整率要求、例外处理。例如：

> 生产环境 Google Play 渠道中，已接入指定采集版本的有效会话，滚动 30 天 Crash-Free Sessions 不低于 99.8%；会话开始记录完整率低于 99% 时，该窗口只告警采集异常，不给出发版通过结论。

上面的 99.8% 只是演示写法，不是行业推荐值。团队应根据稳定版本分布、关键场景风险和可承受的故障量选择目标。

### Error Budget 的单位必须与 SLI 一致

如果 SLO 是 Crash-Free Sessions：

$$
\text{Allowed bad-session ratio}
=
1 - \text{SLO target}
$$

假设滚动 30 天有 3000 万个有效会话，目标为 99.8%，预算是 6 万个受影响会话。一个受影响会话里出现多条 Crash 记录，仍只消耗一个会话单位。

如果 SLI 使用日活受影响率，预算单位则是“受影响安装实例日”，不是跨 30 天去重后的“用户数”。把 `30 × DAU × 0.2%` 描述成允许崩溃的独立用户数，会重复计算多日活跃的同一实例。

### Burn rate 让告警对应预算消耗

Burn rate 表示当前坏事件比例相对允许比例的倍数：

$$
\text{Burn rate}
=
\frac{\text{observed bad-event ratio}}
{\text{allowed bad-event ratio}}
$$

目标 99.8% 时，允许坏会话比例为 0.2%。若最近一小时坏会话比例为 0.6%，该小时 burn rate 为 3。短窗口能发现突发故障，长窗口能过滤瞬时噪声；把两者组合，比单个固定百分比更适合控制 30 天预算。

预算耗尽后的动作也要预先约定，例如暂停扩量、只允许稳定性修复进入版本，或回滚命中高风险路径的变更。动作强度取决于剩余预算、问题范围和修复把握，不由某个匿名“行业及格线”决定。

## 复核清单

发布稳定性数据或把它接入门禁前，可以按下面的顺序复核：

1. 指标名称之后是否写清分子、分母、时间窗、范围和去重键；
2. Google Play、Crashlytics 与内部系统的“用户”“会话”“前台”是否被错误等同；
3. 原始事件是否保留，重复事件与受影响实体是否分别统计；
4. 启动、Crash、ANR、OOM、LMK 的终态是否互斥且可解释；
5. 新旧版本是否在相近暴露人群上比较，并展示分母和统计区间；
6. API 30/31/35/36/37 的采集能力是否按版本降级，best-effort 数据是否被当成必达；
7. 看板是否能识别漏报、延迟、符号缺失和 SDK 覆盖变化；
8. Error Budget 的单位是否与 SLI 一致。

稳定性指标的用途，是把“哪些用户在什么场景受到何种影响”变成可复查的证据。口径写清之后，团队才知道应该暂停灰度、修哪个问题簇，以及修复后该用什么数据证明风险已经下降。

## 参考资料

- [Android vitals 总览与 bad behavior thresholds](https://developer.android.com/topic/performance/vitals)
- [Android vitals：Crashes](https://developer.android.com/topic/performance/vitals/crash)
- [Android vitals：ANR](https://developer.android.com/topic/performance/vitals/anr)
- [Google Play Console：监控应用技术质量](https://support.google.com/googleplay/android-developer/answer/9844486)
- [Firebase Crashlytics：Crash-Free 指标定义](https://firebase.google.com/docs/crashlytics/crash-free-metrics)
- [Android 17 `RuntimeInit.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/com/android/internal/os/RuntimeInit.java)
- [`ApplicationExitInfo`](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [`ActivityManager.registerAnrWarningListener()`](https://developer.android.com/reference/android/app/ActivityManager#registerAnrWarningListener(java.util.concurrent.Executor,%20java.util.function.Consumer%3Candroid.app.AnrWarningResult%3E))
- [`ProfilingTrigger`](https://developer.android.com/reference/android/os/ProfilingTrigger)
