---
title: "Android Vitals 与 Play Console 质量指标归因"
chapter: "26.12"
section: "26.12"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); Google Play Android vitals 2026 口径"
last_verified: "2026-05-21"
last_verified_against: "Android Developers / Play Developer Reporting API docs, updated 2026-03-05"
confidence: high
tags: [observability, android-vitals, play-console, quality-metrics, release-quality]
related_chapters: ["20.6", "21.8", "22.8", "23.7", "25.2", "26.3", "26.6", "26.7"]
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/anr"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/crash"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/render"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/slow-session"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/lmk"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/wakeup"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-battery-usage"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/blog/posts/battery-technical-quality-enforcement-is-here-how-to-optimize-common-wake-lock-use-cases"
  - type: official
    path: "https://developers.google.com/play/developer/reporting/metricset-intro"
  - type: official
    path: "https://developers.google.com/play/developer/reporting/reference/rest/v1alpha1/vitals.anrrate"
---

# 26.12 Android Vitals 与 Play Console 质量指标归因

Android Vitals 是 Google Play 对线上技术质量的外部观测。它回答的是：从 Play 安装应用、允许共享使用情况与诊断数据的用户，是否正在经历稳定性、性能或功耗问题。内部 APM 回答的是另一个问题：问题出现在哪个版本、场景和调用路径，能否在灰度阶段定位并止损。两套数据的采集范围、分母和时效不同，应当相互校验，不能直接比较两个百分比的大小。

指标口径以 2026 年 7 月公开文档为准，平台版本上界为 Android 17 / API 37。Vitals 的指标定义、阈值和 Play 可见性策略都由 Google Play 服务端定义，不属于 `android-17.0.0_r1` 的 AOSP API 契约。Android 17 源码可用于解释 ANR、LMKD、帧时间或唤醒机制，却不能证明 Play 的服务端阈值。团队升级平台源码锚点时，不应顺手改写这些阈值；Play 文档变更时，也不表示 Android framework 同时发生了对应改动。

## Android Vitals 的指标层级

发布评审最需要区分的是 core vitals、其他 Vitals 和内部 APM。Core vital 越过 Play 定义的 bad behavior threshold，可能影响应用在 Google Play 的可见性；其他 Vitals 仍有诊断价值，但不能因为名称里带有 “vital” 就套用相同政策。

| 层级 | 2026 年代表指标 | 它能回答什么 | 仍需内部补充什么 |
|---|---|---|---|
| Core vitals | user-perceived crash rate、user-perceived ANR rate、excessive partial wake locks；表盘应用另有 excessive battery usage | Play 用户是否达到官方不良行为阈值 | 版本变更、调用栈、trace、业务场景和止损动作 |
| 其他 Android Vitals | crash / ANR rate、multiple crash / ANR rate、user-perceived LMK、slow startup、slow/frozen frames、excessive wakeups、stuck background wakelocks、权限拒绝等 | 某类线上体验是否恶化，问题集中在哪些版本、设备或地区 | 实时告警、细粒度场景和可复现证据 |
| 游戏专项 | Slow Sessions 的 20 FPS、30 FPS 观察口径 | 游戏会话是否长期处于低帧率 | scene、画质档、SoC/GPU、温控、Swappy、ADPF session |
| 表盘专项 | watch face excessive battery usage 及 CPU、partial wakelock 贡献因素 | 表盘在非充电、没有其他应用使用设备时的耗电情况 | AoD 配置、刷新频率、Complication 更新、资源与动画成本 |
| 内部 APM | crash-free users、启动分位数、页面卡顿、内存水位、业务错误率 | 当前版本是否回归，问题发生在什么路径 | 与 Play 维度一致的版本、设备、系统和渠道标识 |

“表盘应用”这个限定不能省略。`excessive battery usage` 目前只对具有足够数据的 watch face app 提供，不是所有 Wear OS 应用的通用 core vital。类似地，Slow Sessions 只适用于游戏，普通应用应使用 UI 渲染指标和端侧帧证据。

Core vital 也不是唯一的发版门禁。一个版本可以尚未达到 Play 阈值，但相对上个版本已经出现显著回归；这时内部灰度指标应先阻止继续放量。反过来，Play 上的存量问题也可能被 28 天窗口保留，不能仅凭当天内部指标恢复就宣布问题结束。

## 28 天窗口、整体阈值与机型阈值

Google Play 每天检查 core vitals，通常依据最近 28 天的用户加权结果评估质量；遇到突增时可能更早采取措施。整体阈值与机型阈值约束的范围不同：整体越线可能影响所有设备上的可见性，机型越线主要影响对应设备。Android Developers 的 2026 年口径如下。

| Core vital | 整体 bad behavior threshold | 机型 threshold | 统计对象 |
|---|---:|---:|---|
| User-perceived crash rate | ≥ 1.09% | 手机机型 ≥ 8%；手表机型 ≥ 4% | 28 天窗口内经历至少一次用户可感知崩溃的 DAU |
| User-perceived ANR rate | ≥ 0.47% | 手机机型 ≥ 8%；手表机型 ≥ 5% | 28 天窗口内经历至少一次用户可感知 ANR 的 DAU |
| Excessive partial wake locks | > 5% | 无机型阈值 | 发生 excessive partial wake lock 的 app sessions |
| Excessive battery usage（表盘） | > 1% | 手表机型 > 1% | 电量消耗超过 4.44%/hour 的 watch face sessions |

这里的 DAU 不是安装数，也不是一次启动。Play 把“某一天、某台设备上使用应用的一名用户”计为一个 daily active user：同一用户当天使用两台设备会贡献两个 DAU；多人当天共用一台设备只计一个。Crash、ANR 或 LMK 多次发生，不会让“至少一次”的 rate 分子重复增加。若要观察循环失败，应同时查看 multiple crash rate 和 multiple ANR rate。

Vitals 的 user session 也不是一次 launch。官方将其定义为从太平洋时间午夜开始的 24 小时内，应用全部使用活动的总和；当天没有记录到使用活动时，不产生 session。涉及 partial wake lock、表盘耗电或其他 session rate 时，应沿用这一日会话口径，不能拿内部的一次启动会话直接充当分母。

阈值附近还要注意比较符号。Crash 和 ANR 文档使用 “at least”，达到阈值即属于 bad behavior；partial wake lock 与表盘耗电文档使用 “more than”。工程门禁可以比官方阈值更严格，但应把内部阈值命名为团队护栏，不能写成 Play 官方规则。

### Partial wake lock 的当前规则

Android Vitals 将所有符合统计条件的 partial wake lock 时长相加：若它们在 24 小时内累计达到 2 小时或以上，这个会话被判为 excessive。统计时只计算应用位于后台或正在运行前台服务时的持有时间；当前文档列出的豁免包括音频、定位和 JobScheduler user-initiated API 等具有明确用户收益的场景。28 天内 excessive 会话超过 5%，可能影响 Play 可见性。

这一政策从 2026 年 3 月 1 日起已进入可见性约束阶段。旧资料中的“3 小时”或“仍处于不影响可见性的 beta”已不适合作为当前结论；诊断时应以 2026-06-10 更新的 [Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock) 页面和 [Android Vitals 总览](https://developer.android.com/topic/performance/vitals) 为准。

### 表盘耗电的当前规则

表盘会话的电量消耗超过 4.44%/hour 时，计入 excessive battery usage；官方给出的优化目标是 80% 会话低于 3.2%/hour。CPU 使用达到 90 秒/小时、partial wakelock 达到 18.5 秒/小时，是控制台提供的贡献因素，不是所有 Android 应用的独立 Play 阈值。它们不能替代手机应用的 wakelock 或 CPU 门禁。

## User-perceived Crash / ANR 与自建 Crash 上报的差异

Vitals 的 rate 以受影响用户为中心，自建 SDK 常以事件、会话或启动为中心。若不先统一分母，同一版本在两边呈现不同趋势并不意外。

| 对比项 | Android Vitals | 自建 APM / Crash SDK |
|---|---|---|
| 覆盖范围 | 通过 Google Play 安装、设备通过认证、用户允许共享数据且达到隐私展示门槛的数据 | 所有接入并成功上报的渠道、测试包或企业分发包 |
| 分母 | DAU 或 Reporting API 聚合周期内的 `distinctUsers` | user、device、session、launch 等团队自定义口径 |
| User-perceived crash | 用户主动使用应用时至少发生一次崩溃；活动使用包括显示 Activity 或执行 foreground service | 是否标为前台取决于 SDK 的进程状态和生命周期实现 |
| User-perceived ANR | 当前只计 `Input dispatching timed out` 类型 | SDK 可能通过 watchdog、主线程消息耗时或系统 trace 识别更多卡死 |
| 多次问题 | multiple crash / ANR rate 统计一天内至少两次的受影响用户 | 事件表通常保留每次发生记录 |
| 时效 | 每日更新并受聚合与隐私门槛影响 | 可做到分钟级，但受采样、进程死亡和上传成功率影响 |

Wear OS 的 user-perceived crash 还有一个值得记录的差异：官方 crash 文档将前台和后台崩溃都纳入手表的 user-perceived 口径。手机应用若直接复用手表结论，会高估 Play 在后台崩溃上的统计范围。

### 三层证据如何配合

Play 层用于确定影响面：`versionCode`、`deviceModel`、`apiLevel`、`deviceType`、地区、rate 和错误聚类。系统层用于确认退出原因：Android 11 及以上可查询 `ApplicationExitInfo` 的 reason、timestamp、process name 和可用 trace，native crash 还要保留符号化 tombstone 或 minidump。应用层补充用户路径、页面、实验桶、feature flag、网络状态和最近变更。

三层数据通常没有可跨系统使用的事件 ID。可行的关联方式是按版本、时间桶、设备维度、进程名和 top frame 做弱关联，再打开少量原始证据验证假设。不要把两个聚合数字相近当成同一批事件，也不要把 Play 聚类 ID写入内部事件主键。

ANR 更需要避免只看一张堆栈。`Input dispatching timed out` 说明用户输入没有在系统规定时间内得到处理，不等于根因就在输入回调。主线程可能在同步 Binder、磁盘 I/O、锁竞争、类初始化或 CPU 密集计算中等待；应回到 ANR trace、Perfetto 和相邻线程状态判断。详细的稳定性归因见 20.6 节。

## 启动、渲染、LMK 与 Slow Sessions 的归因路径

这些指标只给出症状和影响面。稳妥的回查顺序是：先锁定版本与设备分组，再确认内部指标是否同向变化，然后查找可复现 session 或 trace，据此决定继续放量、设备降级还是回滚。

| Vitals 入口 | 官方统计边界 | 内部证据 | 归因重点 |
|---|---|---|---|
| Slow startup | TTID；cold ≥ 5s、warm ≥ 2s、hot ≥ 1.5s 计为 excessive | 启动类型、TTID/TTFD、`ApplicationStartInfo`、Macrobenchmark、Perfetto、I/O 与 dexopt | 区分进程创建、Activity 创建、首帧和可交互，不用 `reportFullyDrawn()` 代替 TTID |
| Slow / frozen rendering | View/UI Toolkit 路径；frozen frame > 700ms，直接使用 Vulkan/OpenGL/Unity/Unreal 的渲染时间可能不在该报表中 | FrameTimeline、FrameMetrics、JankStats state、主线程、RenderThread、GPU 和刷新率 | 先确定慢帧属于 UI thread、RenderThread、GPU、BufferQueue 还是调度延迟 |
| User-perceived LMK | DAU 中至少经历一次可感知 LMK；例如 Activity 正在显示或 foreground service 正在运行 | `ApplicationExitInfo.REASON_LOW_MEMORY`、PSS/RSS、native heap、bitmap、WebView、设备 RAM 桶 | 判断版本内存增长与设备整体压力，不能把每个 `REASON_LOW_MEMORY` 都归咎于单一对象泄漏 |
| Slow Sessions | 仅游戏；运行满一分钟后统计；超过 25% 帧的 present-to-present 间隔不低于 50ms 即为 20 FPS slow session，另有 34ms/30 FPS 指标 | Swappy、SurfaceFlinger timestats、ADPF、thermal status、scene、画质档、SoC/GPU | 这是呈现间隔指标，包含 OpenGL、Vulkan 和 UI Toolkit 表面，不等同于应用 CPU frame time |

Slow startup 的固定秒数适合识别严重慢开，却无法识别从 1.8 秒退化到 2.4 秒这类未达到 Play 门槛的回归。灰度门禁仍需比较相同启动类型、相同设备档和相同安装状态下的分布；第 21.8 节给出了启动数据的详细边界。

Frozen frame 与 ANR 也不是同一指标。超过 700ms 的一帧会产生明显停顿，但只有满足相应系统超时条件才形成 ANR。渲染归因应以 FrameTimeline 和线程调度证据为准，不能由“超过 700ms”直接推导出 ANR。

User-perceived LMK 常呈现为界面消失或进度丢失，Java crash handler 不会收到异常。Android 11 及以上的 `ApplicationExitInfo` 能补充历史退出原因，但查询到 `REASON_LOW_MEMORY` 仍只是诊断起点。设备上同时运行的进程、swap、内核回收压力和应用自身内存峰值都可能参与决策，详见 23.7 节。

## 功耗类 vitals 与后台任务治理

功耗问题经常跨越一次 App 会话：Alarm 唤醒进程，任务获取 wakelock，网络失败触发重试，下一次调度又重复整条路径。Play 指标能显示影响比例，端侧采集必须保留“由谁申请、持有多久、为何结束”。

| 资源 | Play / Reporting API 观察项 | 端侧建议字段 | 修复方向 |
|---|---|---|---|
| Partial wakelock | current excessive partial wake locks；Reporting API 另有 legacy `stuckBgWakelockRate`，定义为后台持有超过 1 小时的 distinct users 占比 | tag、owner、调用栈、acquire/release、timeout、前后台、screen state、任务来源 | 为直接获取的锁设置超时并保证异常路径释放；审查间接获取 wakelock 的 API |
| AlarmManager | `excessiveWakeupRate`，定义为每小时 wakeup 超过 10 次的 distinct users 占比 | alarm type、PendingIntent 标识、窗口、周期、业务来源、触发与取消时间 | 合并任务、减少精确和 wakeup alarm、取消失效任务、优先使用受约束调度 |
| WorkManager / JobScheduler | 可能间接贡献 wakelock、网络和唤醒 | work/job id、约束、attempt、stop reason、实际运行时间、网络量 | 设置正确约束和退避；检查无界重试、链式任务和重复 enqueue |
| 后台网络、Wi-Fi 与定位 | Console 中可能提供相应功耗观察项；它们不是 2026 core vital 阈值 | 请求域名、字节数、重试、网络类型、扫描/定位频率、前后台 | 批量传输、退避与抖动、按需注册、离开场景后注销 |
| 表盘 | excessive battery usage 以及 CPU、wakelock 贡献因素 | AoD、刷新频率、绘制耗时、Complication、资源大小、充电状态 | 优先使用 Watch Face Format；降低 AoD 更新、动画和高频数据源 |

`stuckBgWakelockRate` 与 2026 年 `excessive partial wake locks` 不是可互换名称。前者是 Reporting API 现有 metric set 的“后台超过 1 小时”用户率；后者是 Play 当前 core vital 的“24 小时累计至少 2 小时且 28 天影响超过 5% 会话”规则。仓库中可以同时保存两者，但告警标题和字段必须带上具体定义。

音频、定位等豁免也不表示可以无限持有锁。Play 是否豁免取决于其当前分类和用户收益判断；内部仍要检查资源生命周期、设备发热和电量。后台调度的 API 选择与系统限制见 25.2 节。

## Play 指标到发版门禁的映射

官方 threshold 是政策边界，不是团队唯一的暂停线。建议把发布动作分成“已越过官方阈值”“内部确认新版本回归”“证据不足”三类，避免把“接近阈值”写成没有样本和基线依据的固定数字。

| 观察结果 | 需要确认的证据 | 建议动作 |
|---|---|---|
| 新版本分组已越过 crash / ANR 整体阈值 | Reporting API freshness、28 天用户加权指标、版本流量、内部同口径趋势、top clusters | 停止放量；若因果时间和聚类均指向新版本，回滚或发 hotfix |
| 某手机或手表机型越过对应阈值 | `deviceModel`、系统版本、ABI、SoC/GPU、WebView、ROM、该分组 `distinctUsers` | 暂停该设备组；可安全降级时使用远程配置，否则回滚 |
| Partial wake lock core vital 越线 | 非豁免 tag、24 小时累计时长、受影响会话、任务来源、版本变化 | 停止相关后台功能放量，修复资源生命周期和调度策略 |
| 表盘耗电越线 | 充电状态、会话耗电、CPU/wakelock 贡献、AoD 与表盘版本 | 暂停表盘版本；优先降低刷新和动态资源成本 |
| Play 未越线，但内部指标相对对照版本显著恶化 | 实验分组是否随机、样本量、置信区间、设备与版本构成、数据漏报 | 按内部灰度护栏暂停；不要等待 28 天窗口 |
| Play 指标升高，内部没有对应变化 | 分母、渠道、用户同意范围、时区、版本过滤、内部上报成功率 | 保持灰度或降低放量速度，补齐证据后再决定，不能按“无复现”关闭问题 |
| 存量窗口仍越线，但修复版本趋势持续改善 | 修复版本覆盖率、旧版本占比、错误聚类是否消退、freshness | 控制放量并继续观察；不要把窗口残留误判为修复无效 |

每个团队都可以设置比 Play 更早的趋势预警，但预警值应由历史基线、当前样本量和可接受风险推导，并保留变更记录。直接把 1.09% 或 0.47% 乘一个固定系数，无法处理低流量版本、设备集中度和指标季节性。

A/B 实验同样受质量护栏约束。内部 crash、ANR、启动、帧耗时和功耗数据用于实验期间早停；Android Vitals 用于外部复核和较长窗口的风险观察。实验统计与多重检验见 26.6 节。

## 数据延迟、采样盲区与误判边界

Vitals 的覆盖条件决定了它不能代表全部线上用户。

- 数据来自允许自动共享使用情况与诊断数据的用户，仅覆盖部分设备与系统版本。
- Vitals 排除未认证设备，以及并非从 Google Play 安装的应用版本。国内渠道、企业分发、预装和旁加载必须由其他观测系统覆盖。
- 指标需要达到隐私展示门槛。低流量应用、小版本或小设备分组可能没有可见数据；“没有数据”不能解释为零问题。
- 数据每日更新，不同系统版本的到达时间可能不同。查询或评审前要读取 freshness，不能把未完成的一天与完整历史日比较。
- Play 的 DAU、daily session、app session 和 watch face session 不是同一个分母。跨指标做比例比较前必须记录单位。
- Play Console 的时间窗口、Reporting API 的聚合周期和内部看板时区可能不同。Reporting API 的 DAILY 数据固定使用 `America/Los_Angeles`，HOURLY 使用 UTC。
- `deviceModel` 能定位影响集中度，却不能单独证明 OEM 原因。应用版本、WebView、驱动、SoC、地区和服务器配置可能共同变化。
- User-perceived 会排除一部分后台事件；内部仍需观察后台进程退出、worker 失败、native tombstone、业务错误和短时卡死。

一个常见错误是把内部 crash-free sessions 与 Play user-perceived crash rate 放在同一张图上直接相减。前者分母可能是会话，后者分母是 DAU；重复崩溃、后台崩溃和渠道范围也不同。正确做法是分别判断各自趋势，再用版本、设备和错误聚类验证两边是否指向同一变更。

另一个错误是把 Vitals 未越线视为性能合格。Play 的固定启动或 frozen frame 边界用于识别明显问题，无法代替业务关键路径的分位数和用户完成率。内部指标有可靠对照且确认回归时，应先按灰度策略处理。

## Play Developer Reporting API 与内部数据仓库对接

Play Developer Reporting API 以 metric set 组织指标。2026 年稳定性和性能 rate 的主要入口为 `v1beta1`，包括 `vitals.anrrate`、`vitals.crashrate`、`vitals.lmkrate`、`vitals.excessivewakeuprate`、`vitals.stuckbackgroundwakelockrate` 和 `vitals.slowstartrate`；错误报告计数仍有 `v1alpha1` 资源。API 版本、metric set 名称和指标名应按官方 schema 保存，不能从 Console 文案自行拼接。

一次 `query` 请求包含四类核心信息：

- `timelineSpec`：聚合粒度和时间范围。DAILY 只支持 `America/Los_Angeles`，HOURLY 只支持 UTC；并非每个 rolling metric 都支持 HOURLY。
- `metrics`：例如 `userPerceivedCrashRate`、`userPerceivedCrashRate28dUserWeighted`、`distinctUsers`。
- `dimensions`：用于切片的维度。每个 metric set 支持的集合可能不同，提交请求前应读取对应 endpoint 文档。
- `filter`、分页和 `userCohort`：过滤分组、读取完整结果，并区分公开系统版本、测试用户或系统 beta 用户。

API 使用 `https://www.googleapis.com/auth/playdeveloperreporting` OAuth scope。每个 metric set 资源还提供 freshness 查询，可得到各粒度最新可用数据点。定时任务应先读 freshness，只在数据推进后拉取新增区间，并记录服务端 freshness、抓取时间、API 版本和请求维度。

### 仓库模型不要假设不存在的 join key

建议把 Play 聚合事实、内部聚合事实和质量事件分开存储。

| 数据集 | 最小关键字段 | 用途 |
|---|---|---|
| Play metric fact | package、metric set、metric、aggregation period、start time、维度集合、rate、`distinctUsers`、freshness | 保留官方聚合值和查询上下文 |
| Internal quality fact | app、version、channel、time bucket、device/OS、metric、value、sample unit、sample size | 保存内部 APM、实验和灰度指标 |
| Quality incident | incident id、触发规则、受影响版本/设备、证据链接、动作、状态 | 记录调查和发布决策 |

维度集合适合保存为稳定序列化的键值对，而不是为某个 endpoint 预建一组假定永远存在的列。若团队经常按 `versionCode`、`apiLevel` 和 `deviceModel` 查询，可以在仓库侧提取这些常用列，同时保留原始维度对象。

`distinctUsers` 是近似值，并会按数量级取整；官方明确警告不要跨维度行继续相加，否则同一用户可能被重复计数。需要整体值时，应发起不带该 breakdown 的独立查询。

7 天和 28 天字段是按每日 distinct users 加权的 rolling rate，也不应对日值再求一次简单平均。

Play 与内部事件没有通用的精确 join key。仓库应提供按版本、时间、设备、地区和错误特征的候选关联，再由 trace 或堆栈确认。`errorReportCount` 是错误报告数量，不是 crash rate 的分母；二者不能用同一条公式合并。

查询规模也需要控制。官方建议应用越大、breakdown 越多，单次时间范围越短，以免读取过多数据而超时。

分页时除 `pageToken` 外必须保持原查询参数不变；任务还应保存失败重试和缺口检查，避免一页失败后留下看似完整的曲线。

## 技术质量政策与商店可见性风险

越过 core vital threshold 后，Google Play 可能降低应用或游戏的可见性；机型维度存在 bad behavior 时，Play 可能让对应设备用户更少看到该应用，并可能在商店详情页显示警告。文档使用的是 “may” 或 “likely”，不应改写成每次越线都会立即降权的确定承诺。

Crash 和 ANR 的 emerging issues 还有一条独立时效：当新问题在设备上持续超过 7 天时，开发者可获得最长 21 天的处理窗口。它是帮助处理新问题的机制，不会改变 28 天 core vital 统计定义，也不能当作继续放量的宽限承诺。

工程侧至少要准备三类能力：

- 版本动作：灰度平台能暂停放量、回滚，并能查询仍在贡献 28 天窗口的旧版本。
- 设备动作：远程配置或发布策略能够按 `deviceModel`、API level、ABI 等可靠条件关闭高风险功能；条件表达式必须在目标设备上验证。
- 证据入口：从 Play 指标和错误聚类可导航到内部趋势、堆栈、trace、实验与变更记录，但明确标注关联是精确还是推测。

Android Vitals 提供一套由 Play 定义、会影响分发结果的外部证据，不能当作版本质量印章。内部系统越早发现同一趋势，团队越有机会在 28 天窗口和商店风险扩大前完成修复。

## 参考资料

- [Android Vitals 总览与 2026 core vital 阈值](https://developer.android.com/topic/performance/vitals)
- [Crash rate 的 DAU 与 user-perceived 定义](https://developer.android.com/topic/performance/vitals/crash)
- [ANR rate 与当前 user-perceived ANR 定义](https://developer.android.com/topic/performance/vitals/anr)
- [Excessive partial wake locks 当前规则](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [表盘 Excessive battery usage](https://developer.android.com/topic/performance/vitals/excessive-battery-usage)
- [启动时间与 excessive startup 边界](https://developer.android.com/topic/performance/vitals/launch-time)
- [Slow rendering 与 frozen frame](https://developer.android.com/topic/performance/vitals/render)
- [游戏 Slow Sessions](https://developer.android.com/topic/performance/vitals/slow-session)
- [User-perceived LMK](https://developer.android.com/topic/performance/vitals/lmk)
- [Play Developer Reporting API metric sets](https://developers.google.com/play/developer/reporting/metricset-intro)
- [Crash rate `v1beta1` query schema](https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/vitals.crashrate/query)
- [ANR rate `v1beta1` query schema](https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/vitals.anrrate/query)
- [2026 电池技术质量执行说明](https://developer.android.com/blog/posts/battery-technical-quality-enforcement-is-here-how-to-optimize-common-wake-lock-use-cases)
