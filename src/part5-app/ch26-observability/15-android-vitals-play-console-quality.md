---
title: "Android Vitals 与 Play Console 质量指标归因"
chapter: "26.15"
section: "26.15"
status: ready-for-review
drafted_date: "2026-05-21"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37); Google Play Android vitals 2026 口径"
last_verified: "2026-05-21"
last_verified_against: "Android Developers / Play Developer Reporting API docs, updated 2026-03-05"
confidence: high
tags: [observability, android-vitals, play-console, quality-metrics, release-quality]
related_chapters: ["20.6", "21.8", "22.8", "23.7", "25.2", "26.3", "26.6", "26.7", "26.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-21"
gap_source: "官方文档/Clippings结构参考/AOSP结构对照"
gap_score: 18
material_count: 13
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

# 26.15 Android Vitals 与 Play Console 质量指标归因

<!-- outline-start -->
## 要点

### 🔹 Android Vitals 的指标层级
梳理 Android Vitals 在 Play Console 中覆盖的稳定性、性能、功耗和权限类指标，区分 core vitals、普通 vitals、游戏专属 Slow Sessions、Wear OS 电池指标和 App 自建 APM 指标。

### 🔹 28 天窗口、整体阈值与机型阈值
解释 Play 以最近 28 天数据评估质量的口径，重点覆盖 Crash、ANR、Battery core vitals 的整体阈值和 per-device / per-watch-model 阈值，以及越线后对曝光、商店页提示和发版决策的影响。

### 🔹 User-perceived Crash / ANR 与自建 Crash 上报的差异
把 Android Vitals 的 user-perceived 口径与 SDK 本地 crash store、native tombstone、ApplicationExitInfo、ANR trace、前后台状态和去重规则对齐，说明哪些问题只能靠自建 APM 补证据。

### 🔹 启动、渲染、LMK 与 Slow Sessions 的归因路径
建立 Play Console 入口到内部证据的回查流程：启动耗时回连 21.8，慢渲染回连 22.8，User-perceived LMK 回连 23.7，游戏 Slow Sessions 回连 ADPF、Swappy、Frame Pacing 和设备性能分层。

### 🔹 功耗类 vitals 与后台任务治理
覆盖 excessive partial wake locks、excessive wakeups、background Wi-Fi scans、background network usage、Wear OS excessive battery usage，对接 WakeLock / Alarm / WorkManager / JobScheduler 和后台网络重试治理。

### 🔹 Play 指标到发版门禁的映射
把 Android Vitals 越线、趋势预警、设备分群、版本分群、灰度放量和 A/B 实验护栏放到同一张决策表中，避免只看自建指标或只看 Play Console 滞后结果。

### 🔹 数据延迟、采样盲区与误判边界
说明 Android Vitals 适合做外部质量裁决和趋势校验，不适合替代实时报警；列出低量级 App、非 Play 分发、国内渠道、灰度短窗口和 OEM ROM 差异造成的盲区。

## 扩展

### 🔸 Play Developer Reporting API 与内部数据仓库对接
整理可自动拉取 Android Vitals 指标的 API 边界、权限、分组维度和与内部 crash / performance warehouse 的 join key 设计。

### 🔸 技术质量政策与商店可见性风险
跟踪 Google Play 对 core vitals 的技术质量执行策略，补充过线后的商店曝光、警告和版本治理动作。

<!-- outline-end -->

Android Vitals 是 Play Console 给出的外部质量裁决口径。它不替代 App 自建 APM，而是补上另一类问题：同一个版本在 Google Play 分发用户里，是否已经在稳定性、功耗、启动、渲染或内存上触发平台质量判断。

对工程团队来说，Android Vitals 不能只当一张报表看。它要接到版本、设备、系统、场景和内部证据上，才能回答三个问题：哪类用户受影响、内部指标是否同步恶化、发版是否要暂停或回滚。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md] 中把质量平台放在开发、测试、灰度和发布流程里理解；[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md]、[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]、[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md] 分别提供了卡顿、启动、功耗在线上监控的覆盖顺序。这里借用的是组织方式，不复用原文段落和示例代码。

## Android Vitals 的指标层级

Android Vitals 先按指标是否影响 Play 可见性分层，再按问题类型进入不同诊断页。发布决策里最容易混淆的是 core vitals、普通 vitals、自建 APM 三者边界。

| 层级 | 代表指标 | Play 侧用途 | 内部系统要补的证据 |
|---|---|---|---|
| core vitals | user-perceived crash rate、user-perceived ANR rate、excessive partial wake locks | 影响 Google Play 上的标题可见性；越过阈值后可能出现商店页警告或曝光下降 | crash / ANR envelope、WakeLock / Alarm 调用点、版本和设备分布 |
| 普通 Android Vitals | excessive wakeups、stuck partial wake locks、slow startup、slow rendering、frozen frames、LMK、权限拒绝等 | 反映 Play 用户体验退化，适合做趋势校验和灰度验收 | 端侧埋点、Perfetto、FrameMetrics、JankStats、ApplicationExitInfo、内存水位 |
| 游戏专项 | Slow Sessions，按 20 FPS 和 30 FPS 两档观察 | 判断游戏会话帧率是否长期低于体验目标 | Swappy / Frame Pacing 指标、ADPF hint、场景、画质档、设备性能分层 |
| Wear OS 电池指标 | watch face CPU 使用、watch face wakelock 使用 | 判断表盘类会话是否过度占用 CPU 或保持唤醒 | 表盘渲染周期、Complication 更新、后台任务、设备充电状态 |
| 自建 APM | crash-free users、P90/P99 启动、页面帧耗时、业务错误率、接口耗时 | 实时报警、灰度放量、根因定位、国内渠道和非 Play 分发覆盖 | session、user、trace、screen、experiment、release channel、feature flag |

[已验证: 官方文档, https://developer.android.com/topic/performance/vitals] Google Play 使用最近 28 天数据评估应用质量；core vitals 中的 crash、ANR 和 partial wake lock 会影响 Play 可见性。

这个分层会改变发版判断。自建 APM 看的是“现在这个版本是否变差”，Android Vitals 看的是“Play 用户在最近窗口内是否已经被平台判定为差体验”。两者时间尺度不同，不能互相替代。

## 28 天窗口、整体阈值与机型阈值

Android Vitals 的门槛不是单日尖峰，也不是某个内部 P99 曲线，而是最近 28 天的 Play 侧质量窗口。Crash、ANR 和电池类 core vitals 既有整体口径，也可能有按设备或 watch model 的口径；整体越线会影响所有设备上的可见性，单机型越线会影响对应设备上的可见性。

| 指标 | Play 统计口径 | 2026 官方阈值或规则 | 发版含义 |
|---|---|---|---|
| User-perceived crash rate | 发生过至少一次 user-perceived crash 的 daily active users 占比 | 整体阈值：≥ 1.09% DAU；单机型阈值：≥ 8% DAU [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/crash] | 整体越线直接暂停放量；单机型越线先查设备、ABI、系统版本、厂商 ROM 和 native 符号 |
| User-perceived ANR rate | 发生过至少一次 user-perceived ANR 的 daily active users 占比 | 整体阈值：≥ 0.47% DAU；单机型阈值：≥ 8% DAU [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/anr] | 版本内 ANR 抬升时优先查主线程、Binder、I/O、锁等待和输入分发场景；详见 20.6 节 |
| Excessive partial wake locks | 28 天内 excessive partial wake locks 会话占比 | 官方 Vitals 页写明超过 5% app sessions 会影响 Play 可见性；Google 2026 电池质量执行说明把非豁免 partial wake lock 在 screen-off 状态下平均持有至少 2 小时、且影响超过 5% user sessions 的情况纳入约束 [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/excessive-wakelock] [已验证: 官方博客, https://developer.android.com/blog/posts/battery-technical-quality-enforcement-is-here-how-to-optimize-common-wake-lock-use-cases] | 后台任务、定位、音频、上传下载、长连接和 SDK 初始化必须拆分；详见 25.2 节 |
| Slow startup | 冷启动、温启动、热启动分开统计 | 冷启动 ≥ 5s、温启动 ≥ 2s、热启动 ≥ 1.5s 被视为 excessive [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/launch-time] | 只看平均启动时间会漏掉重度用户和低端机；内部门禁要看 P90/P99 与慢开比例，详见 21.8 节 |
| Frozen frames / Slow rendering | Android 自动监控 UI 帧耗时 | frozen frame 指渲染耗时超过 700ms 的 UI 帧 [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/render] | Vitals 只能指出页面体验变差，根因要回到 FrameMetrics、JankStats 和 Perfetto，详见 22.8 节 |
| Slow Sessions（游戏） | 游戏运行一分钟后开始统计会话帧率 | slow session 指超过 25% 的帧慢于 50ms；另有 34ms 目标，对应约 30 FPS [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/slow-session] | 按场景、画质档、SoC、温控状态和 ADPF hint 归因；普通 App 不套用这个指标 |
| User-perceived LMK rate | 发生过至少一次用户可感知 LMK 的 DAU 占比 | LMK 发生在 Activity 可见或 foreground service 运行等场景时，用户会看到类似崩溃的结果；既有历史趋势也有设备分组 [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/lmk] | 要把 Play 侧 LMK 与 `ApplicationExitInfo`、PSS/RSS、低内存设备和版本内存增长合并分析；详见 23.7 节 |
| Wear OS excessive battery usage | watch face session 维度 | CPU ≥ 90s/hour、wakelock ≥ 18.5s/hour 属于高耗电观察项 [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/excessive-battery-usage] | 表盘项目要单独建维度，不能把手机 App 的后台策略直接搬过去 |

28 天窗口带来两个工程后果。

- Play 指标有滞后性。灰度当天的异常更适合由内部实时报警发现，Vitals 更适合做外部裁决、趋势复核和存量问题验收。
- 单机型问题不能被整体均值抹平。低量级但体验很差的机型，会通过 per-device bad behavior 暴露出来；内部看板必须支持 `versionCode + deviceModel + apiLevel` 组合筛选。

## User-perceived Crash / ANR 与自建 Crash 上报的差异

User-perceived 口径的目标是衡量用户能感知到的失败。自建 crash SDK 的目标是尽量收集所有异常证据。两套系统用词相近，统计对象不同。

| 对比项 | Android Vitals | 自建 APM / Crash SDK |
|---|---|---|
| 统计对象 | Play 分发用户中被平台认定为 user-perceived 的 crash / ANR | App 自己采集的 Java crash、native crash、ANR、卡死、业务异常、SDK 异常 |
| 分母 | daily active users 或 distinct users | sessions、launches、active users、devices、灰度桶、渠道包，口径由团队定义 |
| 前后台判断 | 由 Play / Android 系统侧按用户感知场景计算 | 依赖 App 前后台状态机、Activity 生命周期、foreground service、页面曝光 |
| 证据内容 | Play Console 聚合、堆栈、版本、设备、国家地区、趋势 | 本地 crash store、minidump、ANR trace、业务上下文、日志片段、feature flag、用户操作路径 |
| 时间延迟 | 聚合后进入 Play Console 和 Reporting API | SDK 可分钟级上报，取决于网络、采样和上传策略 |
| 覆盖范围 | Google Play 分发用户 | 所有接入 SDK 的渠道、测试包、灰度包、国内渠道和企业分发 |

[已验证: 官方文档, https://developers.google.com/play/developer/reporting/reference/rest/v1alpha1/vitals.anrrate] Reporting API 的 `userPerceivedAnrRate` 指标描述为聚合周期内经历至少一次 user-perceived ANR 的 distinct users 百分比，并说明当前 user-perceived ANR 是 input dispatching 类型。这个口径不能直接等同于内部“所有 ANR”。

Crash 归因建议按三层证据组织：

- Play 层：`versionCode`、`deviceModel`、`apiLevel`、国家地区、user-perceived crash rate、错误聚合堆栈。
- 系统层：Android 11+ `ApplicationExitInfo` 的 reason、timestamp、pid、process name、`getTraceInputStream()`，native crash 时补 tombstone / minidump。
- App 层：SDK 本地 crash store、用户操作路径、页面、feature flag、实验桶、最近一次发版变更。

ANR 归因同样不要只看 Play 堆栈。Play 能告诉团队“用户是否感知到 ANR”，但主线程当时卡在 Binder、I/O、锁等待、输入分发还是 CPU 饱和，需要回到内部 trace 和线程快照。稳定性指标定义和 Play Vitals 标准已在 20.6 节展开，这里只保留指标映射。

## 启动、渲染、LMK 与 Slow Sessions 的归因路径

启动、渲染、LMK、Slow Sessions 的共同特点是：Play Console 给出外部症状，内部系统负责把症状接到场景和证据上。这里的处理顺序可以固定成四步：定位版本和设备、判断是否同内部指标同步、找对应 trace / session、给发版动作。

| Vitals 入口 | 内部回查字段 | 主要证据 | 处理动作 |
|---|---|---|---|
| Slow startup | `versionCode`、启动类型、冷/温/热、设备档、系统版本、首次安装/覆盖安装 | 启动埋点、`reportFullyDrawn()`、首屏可交互时间、CPU / I/O / dexopt 片段、启动 trace | 若新版本 P90/P99 和 Play 慢启动同步上升，暂停放量；启动监控详见 21.8 节 |
| Slow rendering / frozen frames | 页面、Activity / Fragment、刷新率、FrameMetrics、JankStats state、设备档 | `FrameMetrics` 阶段耗时、JankStats state、Perfetto FrameTimeline、主线程和 RenderThread slice | Play 负责暴露分布异常；根因拆分回到 22.8 节 |
| User-perceived LMK | `ApplicationExitInfo.REASON_LOW_MEMORY`、process importance、PSS/RSS、前台服务、设备内存桶 | App 内存水位、native heap、bitmap、WebView、缓存策略、LMKD 历史退出记录 | 先判断是否版本引入内存增长，再按设备内存桶分批回滚或降级；详见 23.7 节 |
| Slow Sessions | 游戏 session、scene、FPS 档、画质档、SoC / GPU、温度、电量、ADPF session | Frame Pacing / Swappy、Vulkan / GL frame time、thermal status、ADPF hint、资源加载 | 对游戏按场景和设备性能分层设门禁；普通 App 不用 Slow Sessions 替代帧率治理 |

[自动发现] Android Vitals 的启动阈值适合做“外部慢启动”判断，内部灰度仍要保留 P90/P99 和慢开比例。5 秒冷启动阈值对 Play 用户很有用，但它不能发现 1.8s → 2.4s 这类已经影响商业转化的回归。

[自动发现] LMK 要和 crash 一起看。用户可感知 LMK 常表现成“页面突然没了”或“回到桌面”，内部 crash SDK 未必能收到 Java / native 异常；Android 11+ `ApplicationExitInfo` 是补证据的入口。

## 功耗类 vitals 与后台任务治理

功耗类 Vitals 的价值在于把后台资源使用变成可裁决的外部指标。后台 WakeLock、Alarm、Wi-Fi scan、后台网络重试、JobScheduler / WorkManager 任务，本地调试时很难复现完整环境；Play 侧能从大量设备中暴露趋势，但无法替团队指出哪一行代码申请了资源。

功耗归因要采集“申请点”和“持有结果”两类证据。

| 资源 | Play / Vitals 观察项 | App 侧采集字段 | 常见治理动作 |
|---|---|---|---|
| Partial WakeLock | excessive partial wake locks、stuck partial wake locks | tag、调用栈、acquire / release 时间、screen-on/off、前后台、任务来源、是否豁免场景 | 加超时保护、收敛 tag、改用 WorkManager / foreground service、把长任务拆成可中断任务 |
| Alarm wakeup | excessive wakeups，Reporting API 中 excessive wakeup rate 描述为每小时超过 10 次 wakeups 的 distinct users 占比 [已验证: 官方文档, https://developers.google.com/play/developer/reporting/metricset-intro] | alarm type、interval、PendingIntent、业务来源、是否 wakeup、设备空闲状态 | 合并周期任务、取消重复闹钟、改成非 wakeup alarm、用 WorkManager 约束充电和网络条件 |
| 后台网络 | background network usage | 请求域名、重试次数、payload、网络类型、前后台、任务来源 | 指数退避、失败隔离、后台批量上传、切换到系统调度任务 |
| Wi-Fi scan / Location / Sensor | background Wi-Fi scans、定位和传感器相关耗电 | 调用栈、权限状态、扫描频率、前后台、场景 | 降低频率、按需启动、退出页面释放监听、使用系统 fused provider 或被动更新 |
| Wear OS 表盘 | CPU ≥ 90s/hour、wakelock ≥ 18.5s/hour | 表盘刷新周期、Complication 更新、绘制耗时、设备是否充电 | 降低息屏刷新、缓存绘制结果、控制后台数据同步 |

25.2 节已经讲后台功耗治理的系统限制和 WorkManager / JobScheduler 选择，这里只补 Play 侧指标映射。工程上不建议把 Vitals 当作唯一报警源：当 Vitals 看到 excessive partial wake locks 时，问题已经经过 28 天窗口积累；内部系统要在灰度阶段就用 tag、调用栈和任务来源截住。

## Play 指标到发版门禁的映射

发版门禁不能只看“是否越过 Vitals 阈值”。等到 Play 越线，用户伤害已经发生。更稳的方式是把 Play 指标、内部实时指标、灰度比例和实验结果放到同一张表里，每条规则给出明确动作。

| 触发条件 | 内部交叉检查 | 发版动作 | 后续处理 |
|---|---|---|---|
| User-perceived crash rate 接近或超过 1.09% | 自建 crash-free users、crash per session、top stack、版本维度、native 符号完整性 | 停止放量；若新版本贡献明确，回滚或 hotfix | 回连 20.6 和 26.7，补版本门禁规则 |
| User-perceived ANR rate 接近或超过 0.47% | 主线程长任务、ANR trace、Input dispatching、Binder 等待、I/O、锁等待 | 停止放量；低端机单独越线时启用设备定向降级 | 把 ANR top 场景接到 Perfetto / ProfilingManager 采样 |
| 单机型 crash / ANR ≥ 8% | 机型、ABI、GPU driver、系统版本、厂商 ROM、WebView 版本 | 对该设备组关闭功能、降低灰度、必要时回滚 | 在设备兼容性清单中加入回归测试 |
| Excessive partial wake locks > 5% sessions | WakeLock tag、后台任务、充电状态、screen-off 持有时间、任务来源 | 暂停涉及后台任务的功能放量 | 调整 WorkManager 约束和超时保护，详见 25.2 |
| Slow startup 上升但未越过 Play 阈值 | P90/P99、慢开比例、首屏可交互时间、低端机分布 | 不一定回滚；按灰度护栏判断是否暂停 | 和 21.8 的启动指标共用门禁 |
| Frozen frames / Slow Sessions 上升 | 页面维度、FrameTimeline、JankStats state、游戏场景 | 暂停图形/动画/渲染相关变更 | 和 22.8、18.x 的渲染证据合并分析 |
| LMK rate 上升 | `ApplicationExitInfo`、PSS/RSS、缓存增长、native heap、低内存设备 | 对低内存设备启用降级，必要时回滚 | 和 23.7 的内存治理看板合并 |

A/B Test 不能绕过这些门禁。26.6 和 26.14 讲实验统计时已经强调护栏指标；Android Vitals 适合加入护栏，但不能等 28 天窗口完成后才判定实验风险。灰度期仍以内部 crash、ANR、启动、帧耗时、功耗采样和业务指标做早停判断。

## 数据延迟、采样盲区与误判边界

Android Vitals 很适合做外部质量裁决，但它有明确边界。

- 只覆盖 Google Play 分发和能进入 Play 统计的用户。国内渠道、企业分发、预装渠道、测试包和旁加载包要靠自建 APM。
- 低量级 App 或低量级设备分组可能缺少稳定趋势。内部看板要保留置信区间、样本数和版本分布，避免把随机波动当成回归。
- Play 指标按聚合窗口进入控制台和 API，不适合做分钟级报警。实时报警应由内部 SDK、日志系统和灰度平台承担。
- `deviceModel` 维度能暴露机型问题，但不等同于根因。SoC、GPU driver、WebView、系统补丁、ROM 后台策略和渠道配置都可能参与。
- Vitals 的 user-perceived 口径会过滤一部分后台或不可感知事件。内部系统仍要采集后台 crash、worker crash、native tombstone、短时卡死和业务异常。
- 权限、隐私、采样和上传失败会影响自建 APM；Play 数据和内部数据出现差异时，要先核对分母和采集范围。

这套边界能避免两个常见误判：内部指标没报警就忽略 Play 单机型越线；Play 指标没越线就允许内部 P99 大幅变差。正确做法是把两套数据当成不同视角的证据。

## Play Developer Reporting API 与内部数据仓库对接

Play Developer Reporting API 可以把 Android Vitals 从人工看板变成数据仓库输入。官方文档列出的 metric sets 包括 `vitals.anrrate`、`vitals.crashrate`、`vitals.lmkrate`、`vitals.excessivewakeuprate`、`vitals.stuckbackgroundwakelockrate`、`vitals.slowstartuprate` 和 `vitals.errors.counts` 等；维度支持 `versionCode`、`apiLevel`、`deviceModel`、`deviceType`、`deviceRamBucket`、国家地区等。[已验证: 官方文档, https://developers.google.com/play/developer/reporting/metricset-intro]

接入时按三张表设计更清楚：

| 表 | 主键建议 | 字段 | 用途 |
|---|---|---|---|
| `play_vitals_daily` | date、package、metric、versionCode、apiLevel、deviceModel、countryCode | rate、7d rolling、28d rolling、distinctUsers、freshness timestamp | 保存 Play 侧日粒度指标，做趋势和门禁输入 |
| `app_quality_daily` | date、app、versionCode、channel、deviceModel、apiLevel | crash rate、ANR rate、P90/P99 启动、slow frame rate、LMK count、wake lock duration | 保存内部 APM 指标，和 Play 口径对照 |
| `quality_incident` | incident id、metric、versionCode、deviceModel、start date | 触发条件、证据链接、处理动作、回滚版本、负责人 | 记录每次越线或接近越线的处理过程 |

查询策略也要跟 API 边界匹配。

- 使用 freshness 信息判断数据是否更新；多数质量指标不适合高频轮询。
- 大 App 查询时按日期范围和分组数量控制请求规模，避免一次拉取所有维度导致超时。
- `distinctUsers` 不能在多个分组上直接相加；跨维度汇总要回到 API 聚合结果或内部原始口径。
- 错误详情表可以拉 `errorReportCount` 和 `distinctUsers`，但要和内部 crash id / minidump id 用时间、版本、设备和 top frame 做弱匹配，不要假设存在完全相同的事件 id。

这部分数据进入仓库后，26.7 的发版质量门禁可以自动生成 Play 侧风险卡片：本版本是否接近整体阈值、是否有单机型越线、是否有相邻版本趋势恶化、内部 APM 是否同步恶化。

## 技术质量政策与商店可见性风险

Google Play 对技术质量的执行已经从“控制台提示”走向“影响可见性”。官方 Vitals 文档写明：应用或游戏越过 bad behavior threshold 后，Play 可能降低标题可见性，也可能在商店页向用户显示警告。[已验证: 官方文档, https://developer.android.com/topic/performance/vitals]

这类风险不应只交给发布同学处理。工程侧要把它拆成三个可执行动作：

- 版本策略：每个版本在灰度前预设 crash、ANR、启动、渲染、功耗护栏，达到暂停线就停止放量。
- 设备策略：per-device 越线时能按 `deviceModel / apiLevel / ABI / WebView version` 关闭功能或降低策略，不必全量回滚。
- 证据策略：每个 Play Vitals 事件都能跳到内部证据页，包含 top stack、trace、session、实验桶、灰度配置和最近变更。

Android Vitals 的价值在于把“用户体验差”变成外部可裁决的质量信号。能降低风险的做法，是在 Play 指标变红之前，内部系统已经从灰度、实验和设备分组里发现同一条趋势。

## 参考资料

- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/crash]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/anr]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/render]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/slow-session]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/lmk]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/excessive-wakelock]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/wakeup]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/excessive-battery-usage]
- [已验证: 官方文档, https://developer.android.com/topic/performance/vitals/launch-time]
- [已验证: 官方博客, https://developer.android.com/blog/posts/battery-technical-quality-enforcement-is-here-how-to-optimize-common-wake-lock-use-cases]
- [已验证: 官方文档, https://developers.google.com/play/developer/reporting/metricset-intro]
- [已验证: 官方文档, https://developers.google.com/play/developer/reporting/reference/rest/v1alpha1/vitals.anrrate]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 22.md]
