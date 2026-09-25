---
title: Android Vitals 与 Play Console 质量指标归因
chapter: '26.8'
section: '26.8'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37); Google Play Android vitals 2026 口径
last_verified: '2026-08-15'
last_source_verified_at: '2026-08-15'
last_verified_against: Current Android Vitals docs including app startup updated 2026-07-28 and excessive partial wake locks updated 2026-06-10, plus Play Developer Reporting API metric set docs updated 2026-06-26 and v1beta1 query references retrieved 2026-08-15
confidence: high
tags:
- observability
- android-vitals
- play-console
- quality-metrics
- release-quality
related_chapters:
- '20.1'
- '21.1'
- '22.10'
- '23.7'
- '25.2'
- '26.1'
- '26.4'
- '26.5'
sources:
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md
- type: legacy-reference-preserved
  path: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md
- type: official
  path: https://developer.android.com/topic/performance/vitals
- type: official
  path: https://developer.android.com/topic/performance/vitals/anr
- type: official
  path: https://developer.android.com/topic/performance/vitals/crash
- type: official
  path: https://developer.android.com/topic/performance/vitals/render
- type: official
  path: https://developer.android.com/topic/performance/vitals/slow-session
- type: official
  path: https://developer.android.com/topic/performance/vitals/lmk
- type: official
  path: https://developer.android.com/topic/performance/vitals/excessive-wakelock
- type: official
  path: https://developer.android.com/topic/performance/vitals/wakeup
- type: official
  path: https://developer.android.com/topic/performance/vitals/excessive-battery-usage
- type: official
  path: https://developer.android.com/topic/performance/vitals/launch-time
- type: official
  path: https://developer.android.com/blog/posts/battery-technical-quality-enforcement-is-here-how-to-optimize-common-wake-lock-use-cases
- type: official
  path: https://developers.google.com/play/developer/reporting/metricset-intro
- type: official
  path: https://developers.google.com/play/developer/reporting/reference/rest/v1alpha1/vitals.anrrate
- type: official
  path: https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/vitals.crashrate/query
- type: official
  path: https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/vitals.anrrate/query
- type: official
  path: https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/vitals.slowstartrate/query
- type: official
  path: https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/vitals.slowrenderingrate/query
pipeline_stage: ready-to-publish
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
last_draft_polish_at: '2026-08-15T20:52:07+08:00'
last_draft_polish_run_id: 20260815-205207-gracker-writing-473
last_review_finalize_at: '2026-08-15T20:52:07+08:00'
last_review_finalize_run_id: 20260815-205207-gracker-writing-473
last_rework_at: '2026-08-15T20:52:07+08:00'
last_rework_run_id: 20260815-205207-gracker-writing-473
---

# Android Vitals 与 Play Console 质量指标归因

Android Vitals 是 Google Play 对线上技术质量的外部观测。它统计从 Play 安装应用、允许共享使用情况与诊断数据的用户所经历的稳定性、性能和功耗问题。内部应用性能监控（application performance monitoring，APM）负责定位问题所在的版本、场景和调用路径，帮助团队在只向部分用户逐步发布的灰度阶段暂停异常版本。两套数据的采集范围、分母和时效不同，应分别判断趋势，再按版本、设备和错误类型相互校验，不能直接比较两个百分比的大小。

指标口径以 2026 年 8 月 15 日可见的公开文档为准，平台版本上界为 Android 17 / API 37。Vitals 的指标定义、阈值和 Play 可见性策略由 Google Play 服务端制定，不在 `android-17.0.0_r1` 的 Android 开源项目（Android Open Source Project，AOSP）API 契约内。Android 17 源码可用于解释应用无响应（ANR）、低内存终止守护进程（low memory killer daemon，LMKD）、帧时间或唤醒机制，无法据此证明 Play 的服务端阈值。升级平台源码锚点不应连带改写这些阈值；Play 文档变更也不表示 Android 框架同时发生了对应改动。

## Android Vitals 的指标层级

发布评审要区分核心指标（core vitals）、其他 Vitals 和内部 APM。Play 为 core vitals 规定不良行为阈值（bad behavior threshold）；指标越过阈值后，应用在 Google Play 的可见性可能受影响。其他 Vitals 仍有诊断价值，但不适用同一套商店政策。

| 层级 | 2026 年代表指标 | 它能回答什么 | 仍需内部补充什么 |
|---|---|---|---|
| Core vitals | user-perceived（用户可感知）crash rate、user-perceived ANR rate、excessive partial wake locks；表盘应用另有 excessive battery usage | Play 用户是否达到官方不良行为阈值 | 版本变更、调用栈、系统跟踪文件（trace）、业务场景和发布动作 |
| 其他 Android Vitals | crash / ANR rate、multiple crash / ANR rate、user-perceived LMK、slow startup、slow/frozen frames、excessive wakeups、stuck background wakelocks、权限拒绝等 | 某类线上体验是否恶化，问题集中在哪些版本、设备或地区 | 实时告警、细粒度场景和可复现证据 |
| 游戏专项 | Slow Sessions 的 20 FPS、30 FPS 观察口径；FPS 表示 frames per second（每秒帧数） | 游戏会话是否长期处于低帧率 | 场景、画质档、SoC（片上系统）/GPU（图形处理器）、温控、Swappy 帧节奏库、ADPF（Android 动态性能框架）会话 |
| 表盘专项 | watch face excessive battery usage 及 CPU、partial wakelock 贡献因素 | 表盘在非充电、没有其他应用使用设备时的耗电情况 | AoD（常亮显示）配置、刷新频率、Complication（表盘信息组件）更新、资源与动画成本 |
| 内部 APM | crash-free users（无崩溃用户率）、启动分位数、页面卡顿、内存水位、业务错误率 | 当前版本是否回归，问题发生在什么路径 | 与 Play 维度一致的版本、设备、系统和渠道标识 |

“表盘应用”这个限定不能省略。`excessive battery usage` 目前只为具备足够数据的表盘应用提供，并不覆盖所有 Wear OS 应用。Slow Sessions 也只适用于游戏，普通应用应使用 UI 渲染指标和端侧帧证据。

Play 阈值只是发版暂停规则之一。一个版本可能尚未达到该阈值，却已经相对上个版本明显恶化；这时内部灰度指标应先阻止继续放量。反过来，Play 上的存量问题也可能在 28 天窗口中继续出现，不能仅凭当天内部指标恢复就宣布问题结束。

## 28 天窗口、整体阈值与机型阈值

Google Play 每天检查 core vitals，通常依据最近 28 天的用户加权结果评估质量；遇到突增时可能更早采取措施。整体阈值与机型阈值约束的范围不同：整体越线可能影响所有设备上的可见性，机型越线主要影响对应设备。Android Developers 的 2026 年口径如下。

| Core vital | 整体 bad behavior threshold | 机型 threshold | 统计对象 |
|---|---:|---:|---|
| User-perceived crash rate | ≥ 1.09% | 手机机型 ≥ 8%；手表机型 ≥ 4% | 28 天窗口内经历至少一次用户可感知崩溃的 DAU |
| User-perceived ANR rate | ≥ 0.47% | 手机机型 ≥ 8%；手表机型 ≥ 5% | 28 天窗口内经历至少一次用户可感知 ANR 的 DAU |
| Excessive partial wake locks | > 5% | 无机型阈值 | 发生 excessive partial wake lock 的 app sessions |
| Excessive battery usage（表盘） | > 1% | 手表机型 > 1% | 电量消耗超过 4.44%/hour 的 watch face sessions |

DAU 是 daily active user（每日活跃用户）的缩写，统计单位是“某一天、某台设备上使用应用的一名用户”，与安装数和启动次数分开计算。同一用户当天使用两台设备会贡献两个 DAU；多人当天共用一台设备只计一个。同一用户多次发生 Crash、ANR 或 LMK，不会让“至少一次”的 rate（受影响比例）分子重复增加。若要观察循环失败，应同时查看 multiple crash rate 和 multiple ANR rate。

Vitals 的 user session（用户会话）按日聚合，与一次 launch（启动）分别计量。官方将其定义为太平洋时间午夜起 24 小时内应用全部使用活动的总和；当天没有记录到使用活动时，不产生 session。涉及 partial wake lock、表盘耗电或其他 session rate 时，应沿用这一日会话口径，不能拿内部的一次启动会话直接充当分母。

阈值附近还要注意比较符号。Crash 和 ANR 文档使用 “at least”，达到阈值即属于 bad behavior；partial wake lock 与表盘耗电文档使用 “more than”。内部暂停阈值可以比官方阈值更严格，但字段名必须表明它属于团队规则，不能写成 Play 官方阈值。

### Partial wake lock 的当前规则

Partial wake lock（局部唤醒锁）在设备屏幕关闭后仍让 CPU 继续运行，因此持有过久会阻止设备进入低功耗状态。Android Vitals 将所有符合统计条件的 partial wake lock 时长相加：若它们在 24 小时内累计达到 2 小时或以上，这个会话被判为 excessive。统计时只计算应用位于后台或正在运行前台服务时的持有时间；现行文档列出的豁免包括音频、定位和由用户发起的 JobScheduler API 等具有明确用户收益的场景。28 天内 excessive 会话超过 5%，可能影响 Play 可见性。

这一政策从 2026 年 3 月 1 日起已进入可见性约束阶段。旧资料中的“3 小时”或“仍处于不影响可见性的 beta”已不适合作为当前结论；诊断时应以 2026-06-10 更新的 [Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock) 页面和 [Android Vitals 总览](https://developer.android.com/topic/performance/vitals) 为准。

### 表盘耗电的当前规则

表盘会话的电量消耗超过 4.44%/hour 时，计入 excessive battery usage；官方给出的优化目标是 80% 会话低于 3.2%/hour。CPU 使用达到 90 秒/小时、partial wakelock 达到 18.5 秒/小时，是控制台为表盘提供的贡献因素。Play 没有把这两个数值设为所有 Android 应用的独立阈值，它们也不能替代手机应用的 wakelock 或 CPU 暂停阈值。

## User-perceived Crash / ANR 与自建 Crash 上报的差异

Vitals 的 rate 以受影响用户为中心，自建 Crash SDK（崩溃采集软件开发工具包）常以事件、会话或启动为中心。分析前要先确认分母；同一版本在两边呈现不同趋势，往往来自统计单位和覆盖范围的差异。

| 对比项 | Android Vitals | 自建 APM / Crash SDK |
|---|---|---|
| 覆盖范围 | 通过 Google Play 安装、设备通过认证、用户允许共享数据且达到隐私展示门槛的数据 | 所有接入并成功上报的渠道、测试包或企业分发包 |
| 分母 | DAU 或 Reporting API 聚合周期内的 `distinctUsers` | user、device、session、launch 等团队自定义口径 |
| User-perceived crash | 用户主动使用应用时至少发生一次崩溃；活动使用包括显示 Activity 或执行 foreground service | 是否标为前台取决于 SDK 的进程状态和生命周期实现 |
| User-perceived ANR | 当前只计 `Input dispatching timed out` 类型 | SDK 可能通过 watchdog（周期性检查主线程是否响应的监测器）、主线程消息耗时或系统 trace 识别更多卡死 |
| 多次问题 | multiple crash / ANR rate 统计一天内至少两次的受影响用户 | 事件表通常保留每次发生记录 |
| 时效 | 每日更新并受聚合与隐私门槛影响 | 可做到分钟级，但受采样、进程死亡和上传成功率影响 |

Wear OS 的 user-perceived crash 有一项单独规则：官方 crash 文档将前台和后台崩溃都纳入手表的 user-perceived 口径。若把这条手表规则直接套用到手机应用，会高估 Play 在后台崩溃上的统计范围。

### 三层证据如何配合

Play 层用于确定影响面：`versionCode`（应用版本号）、`deviceModel`（设备型号）、`apiLevel`（Android API 级别）、`deviceType`（设备形态）、地区、rate 和错误聚类。系统层用于确认退出原因：Android 11 及以上可查询 `ApplicationExitInfo` 的 reason、timestamp、process name 和可用 trace；native crash（原生代码崩溃）还要保留符号化 tombstone（系统崩溃转储）或 minidump（精简崩溃转储）。应用层补充用户路径、页面、实验桶、feature flag（远程功能开关）、网络状态和最近变更。

三层数据通常没有可跨系统使用的事件 ID。可按版本、时间桶、设备维度、进程名和 top frame（最靠近故障点的关键栈帧）建立弱关联；“弱”表示它只能筛出候选事件，还要打开少量原始证据验证。两个聚合数字相近不能证明它们来自同一批事件，Play 聚类 ID 也不应写入内部事件主键。

ANR 不能只看一张堆栈。`Input dispatching timed out` 说明用户输入没有在系统规定时间内得到处理，根因可能发生在输入回调之外。主线程可能在同步 Binder、磁盘 I/O、锁竞争、类初始化或 CPU 密集计算中等待；应回到 ANR trace、Perfetto 和相邻线程状态判断。详细的稳定性归因见 20.1 节。

## 启动、渲染、LMK 与 Slow Sessions 的归因路径

这些指标只给出症状和影响面。回查时先锁定版本与设备分组，再确认内部指标是否同向变化，然后查找可复现的内部 session（连续使用记录）或 trace，据此决定继续放量、设备降级还是回滚。

| Vitals 入口 | 官方统计边界 | 内部证据 | 归因重点 |
|---|---|---|---|
| Slow startup | TTID（time to initial display，首帧显示耗时）；cold ≥ 5s、warm ≥ 2s、hot ≥ 1.5s 计为 excessive | 启动类型、TTID/TTFD（time to full display，达到可交互状态的耗时）、`ApplicationStartInfo`、Macrobenchmark、Perfetto、I/O 与 dexopt（DEX 字节码优化） | 区分进程创建、Activity 创建、首帧和可交互，不用 `reportFullyDrawn()` 代替 TTID |
| Slow / frozen rendering | View/UI Toolkit 路径；frozen frame > 700ms，直接使用 Vulkan/OpenGL/Unity/Unreal 的渲染时间可能不在该报表中 | FrameTimeline、FrameMetrics、JankStats 状态标签、主线程、RenderThread、GPU 和刷新率 | 确认慢帧来自 UI thread（界面线程）、RenderThread、GPU、BufferQueue 或调度延迟 |
| User-perceived LMK | DAU 中至少经历一次可感知 LMK（low memory kill，低内存终止）；例如 Activity 正在显示或 foreground service 正在运行 | `ApplicationExitInfo.REASON_LOW_MEMORY`、PSS/RSS、native heap、bitmap、WebView、设备 RAM 桶 | 同时判断版本内存增长与设备整体压力，不能把每个 `REASON_LOW_MEMORY` 都归咎于单一对象泄漏 |
| Slow Sessions | 仅游戏；运行满一分钟后统计；超过 25% 帧的 present-to-present 间隔不低于 50ms 即为 20 FPS slow session，另有 34ms/30 FPS 指标 | Swappy、SurfaceFlinger（系统显示合成服务）timestats、ADPF、thermal status、场景、画质档、SoC/GPU | 统计相邻画面呈现间隔，覆盖 OpenGL、Vulkan 和 UI Toolkit surface（应用提交画面的缓冲区载体），不等同于应用 CPU frame time |

这些渲染诊断项位于不同层次：FrameTimeline 记录一帧从应用到系统合成的时间线，FrameMetrics 提供应用窗口的帧耗时，JankStats 状态标签给慢帧附加页面或交互信息；RenderThread 是执行部分渲染工作的线程，BufferQueue 是生产者向显示消费者传递图形缓冲区的队列。

内存项中，PSS 是按共享比例折算后的进程内存，RSS 是进程当前驻留在物理内存中的总量，native heap 是 C/C++ 等原生代码使用的堆，设备 RAM 桶则按物理内存容量给设备分组。单独一个数值不足以解释 LMK，需要结合设备内存分组和同机内存压力。

Slow Sessions 的 present-to-present 指相邻两帧送达屏幕合成端的时间间隔；thermal status 是设备因温度变化进入的性能限制状态。因此 Slow Sessions 统计的是用户看到的出帧节奏，无法直接代替 CPU 或 GPU 单阶段耗时。

Slow startup 的固定秒数适合识别严重慢开，却无法识别从 1.8 秒退化到 2.4 秒这类未达到 Play 门槛的回归。灰度暂停规则仍需比较相同启动类型、相同设备档和相同安装状态下的分布；第 21.1 节给出了启动数据的详细边界。

Frozen frame 与 ANR 使用不同判定条件。超过 700ms 的一帧会产生明显停顿，只有满足相应系统超时条件才形成 ANR。渲染归因应以 FrameTimeline 和线程调度证据为准，不能由“超过 700ms”直接推导出 ANR。

User-perceived LMK 常呈现为界面消失或进度丢失，Java crash handler 不会收到异常。Android 11 及以上的 `ApplicationExitInfo` 能补充历史退出原因，但查询到 `REASON_LOW_MEMORY` 仍只是诊断起点。设备上同时运行的进程、交换空间（swap）、内核回收压力和应用自身内存峰值都可能参与决策，详见 23.7 节。

现行 LMK 页面把高于 1% 称为需要立即处理的警戒信号。该数字用于诊断优先级；Android Vitals 总览没有把 user-perceived LMK 列为 core vital，也没有为它声明商店可见性阈值，因此发版规则中应标成内部警戒线，不能写成 Play 政策门槛。

## 功耗类 vitals 与后台任务治理

功耗问题经常跨越一次应用会话：Alarm 唤醒进程，任务获取 wakelock，网络失败触发重试，下一次调度又重复这组操作。Play 指标能显示影响比例，端侧采集必须保留“由谁申请、持有多久、为何结束”。

| 资源 | Play / Reporting API 观察项 | 端侧建议字段 | 修复方向 |
|---|---|---|---|
| Partial wakelock | 现行 excessive partial wake locks；Reporting API 另有旧指标 `stuckBgWakelockRate`，定义为后台持有超过 1 小时的 `distinctUsers` 占比 | 锁 tag（系统记录的锁名称）、责任组件、调用栈、获取/释放时间、超时、前后台、屏幕状态、任务来源 | 为直接获取的锁设置超时并保证异常路径释放；审查间接获取 wakelock 的 API |
| AlarmManager | `excessiveWakeupRate`，定义为每小时 wakeup 超过 10 次的 `distinctUsers` 占比 | alarm 类型、PendingIntent 标识、窗口、周期、业务来源、触发与取消时间 | 合并任务、减少精确和 wakeup alarm、取消失效任务、优先使用受约束调度 |
| WorkManager / JobScheduler | 可能间接贡献 wakelock、网络和唤醒 | work/job ID、约束、重试次数、停止原因、实际运行时间、网络量 | 设置正确约束和退避；检查无界重试、链式任务和重复入队 |
| 后台网络、Wi-Fi 与定位 | Console 中可能提供相应功耗观察项；2026 core vital 阈值不包含这些项目 | 请求域名、字节数、重试、网络类型、扫描/定位频率、前后台 | 批量传输、退避重试并加入随机延迟、按需注册、离开场景后注销 |
| 表盘 | excessive battery usage 以及 CPU、wakelock 贡献因素 | AoD、刷新频率、绘制耗时、Complication、资源大小、充电状态 | 优先使用 Watch Face Format；降低 AoD 更新、动画和高频数据源 |

`stuckBgWakelockRate` 与 2026 年 `excessive partial wake locks` 使用不同定义。前者属于 Reporting API 指标集（metric set），表示后台持有超过 1 小时的用户率；后者属于 Play core vital，规则是“24 小时累计至少 2 小时且 28 天影响超过 5% 会话”。仓库中可以同时保存两者，但告警标题和字段必须带上具体定义。

音频、定位等豁免也不表示可以无限持有锁。Play 是否豁免取决于其当前分类和用户收益判断；内部仍要检查资源生命周期、设备发热和电量。后台调度的 API 选择与系统限制见 25.2 节。

## Play 指标与发版暂停规则

官方 threshold 表示政策边界，团队还需要更早的内部暂停线。发布动作可分成“已越过官方阈值”“内部确认新版本回归”“证据不足”三类，避免把“接近阈值”写成没有样本和基线依据的固定数字。

| 观察结果 | 需要确认的证据 | 建议动作 |
|---|---|---|
| 新版本分组已越过 crash / ANR 整体阈值 | Reporting API 的 freshness（数据新鲜度，即最新可用数据点）、28 天用户加权指标、版本流量、内部同口径趋势、主要错误聚类（top clusters） | 停止放量；若发布时间和聚类均指向新版本，回滚或发布紧急修复版本（hotfix） |
| 某手机或手表机型越过对应阈值 | `deviceModel`、系统版本、ABI（应用二进制接口）、SoC/GPU、WebView、ROM（设备系统构建）、该分组 `distinctUsers` | 暂停该设备组；可安全降级时使用远程配置，否则回滚 |
| Partial wake lock core vital 越线 | 非豁免 tag、24 小时累计时长、受影响会话、任务来源、版本变化 | 停止相关后台功能放量，修复资源生命周期和调度策略 |
| 表盘耗电越线 | 充电状态、会话耗电、CPU/wakelock 贡献、AoD 与表盘版本 | 暂停表盘版本；优先降低刷新和动态资源成本 |
| Play 未越线，但内部指标相对对照版本显著恶化 | 实验分组是否随机、样本量、置信区间（估计值可能落入的范围）、设备与版本构成、数据漏报 | 按内部灰度暂停规则处理；不要等待 28 天窗口 |
| Play 指标升高，内部没有对应变化 | 分母、渠道、用户同意范围、时区、版本过滤、内部上报成功率 | 保持灰度或降低放量速度，补齐证据后再决定，不能按“无复现”关闭问题 |
| 存量窗口仍越线，但修复版本趋势持续改善 | 修复版本覆盖率、旧版本占比、错误聚类是否消退、freshness | 控制放量并继续观察；不要把窗口残留误判为修复无效 |

每个团队都可以设置比 Play 更早的趋势预警，但预警值应由历史基线、当前样本量和可接受风险推导，并保留变更记录。直接把 1.09% 或 0.47% 乘一个固定系数，无法处理低流量版本、设备集中度和指标季节性。

A/B 实验同样受质量暂停规则约束。内部 crash、ANR、启动、帧耗时和功耗数据用于实验期间早停；Android Vitals 用于外部复核和较长窗口的风险观察。实验统计与多重检验见 26.4 节。

## 数据延迟、采样盲区与误判边界

Vitals 的覆盖条件决定了它不能代表全部线上用户。

- 数据来自允许自动共享使用情况与诊断数据的用户，仅覆盖部分设备与系统版本。
- Vitals 排除未认证设备和通过 Google Play 以外渠道安装的应用版本。国内渠道、企业分发、预装和旁加载必须由其他观测系统覆盖。
- 指标需要达到隐私展示门槛。低流量应用、小版本或小设备分组可能没有可见数据；“没有数据”不能解释为零问题。
- 数据每日更新，不同系统版本的到达时间可能不同。查询或评审前要读取 freshness，不能把未完成的一天与完整历史日比较。
- Play 的 DAU、daily session、app session 和 watch face session 各有独立分母。跨指标做比例比较前必须记录单位。
- Play Console 的时间窗口、Reporting API 的聚合周期和内部看板时区可能不同。Reporting API 的 DAILY 数据固定使用 `America/Los_Angeles`，HOURLY 使用 UTC。
- `deviceModel` 能定位影响集中度，但不能单独证明设备厂商（OEM）是原因。应用版本、WebView、驱动、SoC、地区和服务器配置可能共同变化。
- User-perceived 会排除一部分后台事件；内部仍需观察后台进程退出、后台任务失败、native tombstone、业务错误和短时卡死。

内部 crash-free sessions 与 Play user-perceived crash rate 不能在同一张图上直接相减。前者分母可能是会话，后者分母是 DAU；重复崩溃、后台崩溃和渠道范围也不同。应分别判断各自趋势，再用版本、设备和错误聚类验证两边是否指向同一变更。

Vitals 未越线也不足以判定性能合格。Play 的固定启动或 frozen frame 边界用于识别明显问题，无法代替业务关键路径的分位数和用户完成率。内部指标有可靠对照且确认回归时，应先按灰度策略处理。

## Play Developer Reporting API 与内部数据仓库对接

Play Developer Reporting API 用 metric set（指标集）组织指标，同一个 metric set 内的指标共享数据新鲜度、聚合粒度和可用维度。2026 年稳定性和性能 rate（比例指标）的主要入口为 `v1beta1`，包括 `vitals.anrrate`、`vitals.crashrate`、`vitals.lmkrate`、`vitals.excessivewakeuprate`、`vitals.stuckbackgroundwakelockrate`、`vitals.slowstartrate` 和 `vitals.slowrenderingrate`；错误报告计数仍有 `v1alpha1` 资源。API 版本、metric set 名称和指标名应按官方 schema（字段、类型和约束定义）保存，不能从 Console 文案自行拼接。

一次 `query` 请求包含四类核心信息：

- `timelineSpec`：聚合粒度和时间范围。DAILY 只支持 `America/Los_Angeles`，HOURLY 只支持 UTC；部分 rolling metric（滚动窗口指标）只提供 DAILY 数据。
- `metrics`：例如 `userPerceivedCrashRate`、`userPerceivedCrashRate28dUserWeighted`、`distinctUsers`。
- `dimensions`：用于切片的维度，例如版本、机型和地区。每个 metric set 支持的集合可能不同，提交请求前应读取对应 endpoint（具体 API 接口资源）文档。
- `filter`、分页和 `userCohort`：过滤分组、读取完整结果，并用 user cohort（用户群组）区分公开系统版本、应用测试用户或系统 beta 用户。

API 使用 `https://www.googleapis.com/auth/playdeveloperreporting` OAuth scope（OAuth 授权范围，用来声明访问权限）。每个 metric set 资源还提供 freshness 查询，可得到各粒度最新可用数据点。定时任务应先读 freshness，只在数据推进后拉取新增区间，并记录服务端 freshness、抓取时间、API 版本和请求维度。

### 仓库模型不假设精确关联键

Play 与内部系统没有共享的事件标识，因此数据仓库应把 Play 聚合事实、内部聚合事实和质量事件分开存储。`join key`（关联键）指两张表用于确认同一条记录的共同字段；这里只能构造候选关联条件，无法得到事件级精确键。

| 数据集 | 最小关键字段 | 用途 |
|---|---|---|
| Play metric fact（Play 指标事实表） | package（包名）、metric set、metric、aggregation period（聚合周期）、start time、维度集合、rate、`distinctUsers`、freshness | 保留官方聚合值和查询条件 |
| Internal quality fact（内部质量事实表） | app、version、channel、time bucket（时间分桶）、device/OS、metric、value、sample unit（样本单位）、sample size（样本量） | 保存内部 APM、实验和灰度指标 |
| Quality incident（质量事件表） | incident id（事件编号）、触发规则、受影响版本/设备、证据链接、动作、状态 | 记录调查和发布决策 |

维度集合适合按固定顺序和格式保存为键值对，避免为某个 endpoint 预建一组假定永远存在的列。若团队经常按 `versionCode`、`apiLevel` 和 `deviceModel` 查询，可以在仓库侧提取这些常用列，同时保留原始维度对象。

`distinctUsers` 是近似值，并会按数量级取整；官方明确警告不要跨维度行继续相加，否则同一用户可能被重复计数。需要整体值时，应发起不带 breakdown（拆分维度）的独立查询。

7 天和 28 天字段是按每日 `distinctUsers` 加权的 rolling rate（滚动比例），服务端已经让用户量较大的日期占更高权重，不应对日值再求一次简单平均。

Play 与内部事件没有通用的精确 `join key`。仓库应提供按版本、时间、设备、地区和错误特征的候选关联，再由 trace 或堆栈确认。`errorReportCount` 记录错误报告数量，crash rate 则用受影响用户数除以用户总数，二者不能用同一条公式合并。

查询规模也需要控制。官方建议应用越大、breakdown 越多，单次时间范围越短，以免读取过多数据而超时。

分页时除 `pageToken` 外必须保持原查询参数不变；任务还应保存失败重试和缺口检查，避免一页失败后留下看似完整的曲线。

## 技术质量政策与商店可见性风险

越过 core vital threshold 后，Google Play 可能降低应用或游戏的可见性；机型维度存在 bad behavior 时，Play 可能让对应设备用户更少看到该应用，并可能在商店详情页显示警告。文档使用的是 “may” 或 “likely”，不应改写成每次越线都会立即降权的确定承诺。

Crash 和 ANR 的新出现问题（emerging issues）还有一条独立时效：当问题在设备上持续超过 7 天时，Android Vitals 会将其标记出来，并给开发者最长 21 天处理。这个机制不会改变 28 天 core vital 统计定义，也不能当作继续放量的宽限承诺。

工程侧至少要准备三类能力：

- 版本动作：灰度平台能暂停放量、回滚，并能查询仍在贡献 28 天窗口的旧版本。
- 设备动作：远程配置或发布策略能够按 `deviceModel`、API level、ABI 等可靠条件关闭高风险功能；条件表达式必须在目标设备上验证。
- 证据入口：Play 指标和错误聚类应链接到内部趋势、堆栈、trace、实验与变更记录，并明确标注关联是精确还是推测。

Android Vitals 提供一套由 Play 定义、会影响分发结果的外部证据，不能当作版本质量的证明。内部系统越早发现同一趋势，团队越有机会在 28 天窗口和商店风险扩大前完成修复。

## 全文小结

Android Vitals 适合判断 Play 覆盖用户的影响面和商店政策风险，内部 APM 则负责更快地定位版本、设备、场景和调用路径。两者没有共同的事件级主键，指标分母、时间窗口、渠道范围也不同；正确做法是分别保留原始口径，再按版本、时间、设备和错误特征建立候选关联。

发布门禁应早于官方阈值响应内部回归，同时把 Play 的 core vital 阈值、机型风险和数据 freshness 作为外部约束。Reporting API 数据入仓时要保存 metric set、维度、时区、样本单位与查询条件，避免把缺数当成零问题，或对已经聚合、加权的数据再次错误汇总。

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
- [Slow rendering rate `v1beta1` query schema](https://developers.google.com/play/developer/reporting/reference/rest/v1beta1/vitals.slowrenderingrate/query)
- [2026 电池技术质量执行说明](https://developer.android.com/blog/posts/battery-technical-quality-enforcement-is-here-how-to-optimize-common-wake-lock-use-cases)
