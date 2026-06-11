---
title: "性能指标采集与上报"
chapter: "26.3"
section: "26.3"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-15"
last_verified_against: "Android Developers docs + Clippings structure references"
confidence: medium
drafted_date: "2026-05-15"
polish_count: 0
sources:
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 5.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md"
  - type: clipping
    path: "Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/performance/jankstats"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/custom-events"
  - type: official
    path: "https://developer.android.com/topic/performance/tracing/custom-events-native"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics"
  - type: official
    path: "https://developer.android.com/reference/android/os/Debug.MemoryInfo"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getProcessMemoryInfo(int[])"
tags: [performance-metrics, trace, percentile, regression-detection]
related_chapters: ["26.1", "21.8", "22.8", "23.7", "15.3"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_review_notes: '2026-05-15 task6 review: pass-light-edit。L1/L2 结构性元叙述小修 5 处；Task9 已通过且 queue 无 pending，自动晋升 finalized。'
last_task6_at: "2026-05-15T01:12:00+08:00"
task6_result: pass-light-edit
reviewed_date: "2026-05-15"
reviewed_by: openclaw-task6
task9_state: reviewed
task9_reviewed_date: "2026-05-15"
task9_reviewed_by: openclaw-task9
task9_result: pass-tech-review
last_task9_audit: "2026-06-11"
task9_idle_audit: true
last_idle_audit_at: "2026-06-11"
task2b_state: done
last_task6_audit: "2026-06-07"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-12
---
# 性能指标采集与上报

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 启动耗时、帧率、内存水位等核心指标采集
- 🔹 自定义 Trace 与业务埋点
- 🔹 性能数据分位值统计（P50 / P90 / P99）
- 🔹 性能基线与劣化检测

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解性能指标采集与上报

性能指标采集解决的是线上治理的入口问题：哪些数字要长期记录，哪些样本要保留现场，哪些变化应该拦截发版。26.1 节已经讲过 Metrics / Logs / Traces 的架构分层；这里聚焦性能 Metrics 的端侧采集、上报口径、分位值计算和劣化检测。

Part 5 各章已经分别讲了启动、渲染、内存的单点监控方法。但这些单点监控最终要放进同一个可观测性系统：启动耗时、慢帧、内存水位、业务耗时必须走统一事件模型，否则后端没法把同一个版本、同一个页面、同一会话里的性能变化串起来看。

## 启动耗时、帧率、内存水位等指标采集

端侧指标要分成两类：低频状态样本和事件触发样本。低频状态样本适合描述内存、线程数、进程前后台状态；事件触发样本适合描述启动、页面停留、慢帧窗口、业务操作耗时。两类样本的采集频率、上报时机和字段都不同。

| 指标组 | 推荐采集时机 | 主要字段 | 治理用途 | 关联章节 |
| --- | --- | --- | --- | --- |
| 启动耗时 | 冷 / 温 / 热启动结束、`reportFullyDrawn()` 调用、慢启动触发 | TTID、TTFD、启动类型、首屏 Activity、入口来源、版本、设备档位 | 判断启动退化、区分首帧和内容可用时间 | 21.8 |
| 帧率与慢帧 | Activity 前台停留窗口、页面切换、滚动场景结束 | 页面、场景、刷新率、总帧数、慢帧数、冻帧数、P90/P99 帧间隔 | 发现页面级流畅性退化 | 22.8 |
| 内存水位 | 前台每 3-5 分钟、页面切换、低内存回调、OOM 前后 | PSS、Java Heap、Native Heap、RSS、图片缓存、进程名、前后台 | 发现泄漏、缓存膨胀和 OOM 前兆 | 23.7 |
| 业务耗时 | 用户操作开始 / 结束、网络请求完成、关键任务完成 | trace 名称、场景 ID、耗时、结果码、是否缓存命中、网络类型 | 把性能退化定位到业务路径 | 26.1 |

启动指标要采用系统口径和业务口径两套字段。Android Vitals 使用 TTID 判断首帧展示；`Activity.reportFullyDrawn()` 对应的 TTFD 更接近首屏内容可用。线上采集时，TTID 用来和 Vitals 对标，TTFD 用来判断业务体验。两者不能互相替代。

渲染指标默认不要逐帧上报。AndroidX JankStats 会报告耗时过长的应用帧，并支持给帧附加 UI 状态。线上更适合按页面停留窗口聚合：总帧数、jank 帧数、frozen 帧数、P90/P99、最大连续慢帧时长。命中阈值后再抽样上传慢帧现场或 Perfetto 片段。

内存指标要把页口径和对象口径分开。`Debug.MemoryInfo` / `ActivityManager.getProcessMemoryInfo()` 适合记录 PSS、dalvik / native / other PSS 等页级数据；`Runtime.totalMemory() - Runtime.freeMemory()` 适合记录 Java Heap 对象使用量。两个口径都叫“内存”，但它们解释的问题不同，不能相加后当作单一结论。)]

采集入口要足够轻。主线程上只记录时间戳、枚举字段和少量数值；序列化、压缩、落盘和上传放到后台线程。Clippings 里的上报组件章节把高频埋点拆成采样、存储、上报、容灾四块，这个拆法适合性能指标系统复用：采集入口不要负责存储和网络。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

## 自定义 Trace 与业务埋点

平台指标只能告诉团队“哪里慢了”，业务 Trace 负责说明“慢的是哪个场景”。一个支付页慢帧、一个搜索页慢启动、一次首屏接口超时，如果没有稳定的 `scene_id` 和 trace 名称，后端只能按 Activity 聚合，分派时仍要人工翻日志。

自定义 Trace 建议采用三层命名：产品场景、技术阶段、结果状态。

| Trace 层级 | 示例 | 说明 |
| --- | --- | --- |
| 产品场景 | `home.feed.refresh`、`pay.cashier.submit` | 对应用户可感知的操作或页面段落 |
| 技术阶段 | `db.query`、`image.decode`、`layout.bind`、`network.request` | 对应可归因的执行阶段 |
| 结果状态 | `success`、`timeout`、`cache_hit`、`fallback` | 用于区分慢和失败是否同源 |

Android 官方 tracing 文档支持在 Java / Kotlin 代码里用 `Trace.beginSection()` / `Trace.endSection()` 添加自定义 trace section，native 代码里用 `ATrace_beginSection()` / `ATrace_endSection()`。这些切片会出现在系统 trace 里，适合线下和灰度诊断；线上常规上报只记录同名阶段的摘要耗时，避免把完整 trace 文件变成常驻数据。

这段代码只演示采集边界：`Trace` 用于系统 trace，`metrics` 用于线上摘要。线上摘要要在后台聚合后再上报。

```kotlin
inline fun <T> tracedMetric(
 name: String,
 sceneId: String,
 metrics: PerformanceMetricSink,
 block: () -> T
): T {
 val startNs = System.nanoTime()
 android.os.Trace.beginSection(name)
 return try {
 block()
 } finally {
 android.os.Trace.endSection()
 val durationMs = (System.nanoTime() - startNs) / 1_000_000.0
 metrics.recordDuration(
 name = name,
 sceneId = sceneId,
 durationMs = durationMs
 )
 }
}
```

代码里的 `PerformanceMetricSink` 是业务侧抽象，不应直接写文件或发网络。它只把样本放进有界队列，后台聚合器按 trace 名称、场景、版本和设备维度生成窗口统计。这样做的好处是，Perfetto 里能看到同名切片，线上看板也能看到同名分位值，线下诊断和线上治理能互相对照。

业务埋点还要处理三个边界：

- 字段枚举化：页面、入口、任务名、结果码使用稳定枚举，避免自由文本让聚合维度失控。
- 隐私最小化：URL 参数、用户输入、token、定位、手机号不进入性能事件；确需关联用户会话时只保留匿名 ID。
- 失败也上报：只记录成功耗时会低估问题，timeout、cancel、fallback 要进入同一指标体系，否则慢路径会从看板里消失。

## 性能数据分位值统计（P50 / P90 / P99）

性能数据通常是长尾分布。启动、页面渲染、网络请求、数据库查询都可能出现少数极慢样本；平均值会把这些样本摊薄，P90 / P99 更容易暴露尾部体验。端侧到服务端还需要统一计算口径。

| 分位值 | 代表含义 | 适合用途 | 使用边界 |
| --- | --- | --- | --- |
| P50 | 中位样本 | 判断主路径是否变快 | 不代表慢用户体验 |
| P90 | 90% 样本不超过该值 | 发版门禁、页面治理主指标 | 样本量小会不稳定 |
| P99 | 最慢 1% 附近样本 | 低端机、弱网、极端长尾排查 | 容易受离群样本影响，需要配合样本量 |
| Max | 单次最大值 | 个案诊断入口 | 不能直接作为趋势指标 |

服务端计算分位值时，必须先分桶再计算。至少按 `metric_name`、`scene_id`、`app_version`、`startup_type`、`device_tier`、`android_version` 拆开；把首页启动、详情页滚动、低端机内存水位混在一个分布里，分位值会失去工程意义。

样本量要和分位值一起展示。一个灰度版本只有 80 个启动样本时，P99 只对应最慢的 1 个样本，稳定性不足；这时适合显示风险提示，而不是直接拦截发版。P90 至少要有数百级样本才适合做趋势判断，P99 通常需要更高样本量。

端侧采样会改变分位值解释。性能事件如果按用户采样，服务端要记录 `sample_rate`、`sampling_policy_version` 和命中时间窗。计算 UV / PV 比例时按采样规则还原；做单次样本回查时保留原始耗时。缺少采样字段时，后端很容易把“没有采到”判断成“没有发生”。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

Macrobenchmark 的 `StartupTimingMetric`、`FrameTimingMetric`、`TraceSectionMetric` 适合做线下基准和 CI 门禁。线上指标负责观察真实用户分布，线下 benchmark 负责在可控设备和场景里复现变化。二者使用同名指标和同名场景，可以减少“实验室变快、线上没变化”的对账成本。

## 性能基线与劣化检测

基线不是一个固定数字，而是一组带条件的历史分布。冷启动 P90、首页首屏 TTFD P90、低端机 feed 慢帧率、前台 30 分钟 PSS P90，这些指标都要按版本、场景、设备和启动类型分别建立基线。

推荐用三类规则组合判断劣化：

| 规则类型 | 示例 | 适合发现的问题 |
| --- | --- | --- |
| 相对变化 | 新版本首页冷启动 P90 比上一稳定版本上升 15% | 中等页面的明显退化 |
| 绝对阈值 | 冷启动 P90 超过 5 秒，冻帧率超过 0.1% | 已经影响用户感知的问题 |
| 分群异常 | 某机型 Android 版本组合的慢帧率上升 2 倍 | 全局均值掩盖的设备问题 |

检测流程要先过滤噪音：样本量不足不告警，灰度比例过低只提示风险；同一指标连续多个时间窗异常再升级；服务端、网络、活动运营引起的外部波动要有 suppress 机制。没有这些约束，性能告警会很快变成噪音。

发版门禁建议分成实验室门禁和线上门禁。实验室门禁使用 Macrobenchmark 或自动化脚本在固定设备上跑启动、滚动、页面切换；线上门禁在灰度阶段看真实用户的 P90/P99、慢帧率、内存水位和 Crash / ANR。实验室门禁失败，阻止合入或发包；线上门禁失败，停止扩大灰度并触发回滚评估。

劣化归因要把指标和样本连起来。每条告警至少带上：指标名、版本、场景、受影响用户数、样本量、基线值、当前值、变化幅度、Top 设备 / Android 版本、可回查样本列表。没有样本列表，告警只能说明“变差了”，不能支持工程团队立刻排查。

## 上报组件自监控

性能指标系统本身也要被监控。采集 SDK 如果写入过慢、队列堆积、上传失败或本地文件膨胀，会反过来制造性能问题。高可用上报组件章节已经提到数据自监控；在性能采集里，它也是必要配套能力。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

自监控至少保留这些字段：

| 自监控字段 | 说明 | 处理动作 |
| --- | --- | --- |
| `enqueue_cost_p99` | 采集入口入队耗时 | 超阈值后关闭高频事件或降采样 |
| `drop_count` | 队列满、文件满、编码失败造成的丢弃数 | 进入看板，避免误判业务指标下降 |
| `local_bytes` | 本地暂存文件总大小 | 超配额后按优先级清理旧数据 |
| `upload_success_rate` | 批量上传成功比例 | 弱网或服务端异常时调整上传间隔 |
| `config_version` | 采样配置版本 | 发现旧配置用户占比过高时排查配置下发 |

这些字段不需要高频上报。每次 App 启动、配置更新、上传批次结束或 SDK 熔断时上报摘要即可。它们的作用是解释监控系统的盲区：某个版本指标样本突然减少，可能是体验变好，也可能是采集 SDK 被熔断或上传失败。

## Android 15 BatteryUsageStats：平台级电池归因数据通道

### 平台侧电池归因数据通路（系统级）

Android 15 引入的 `BatteryUsageStats` 体系是平台给端侧 APM 的**第一条标准化的电池归因数据通道**，重要性等同于 §26.1 提到的 Metrics / Logs / Traces 三层架构在功耗维度的落地。

**核心数据模型**（`frameworks/base/core/java/android/os/BatteryUsageStats.java` android-platform-15.0.0_r17）：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `mStatsStartTimestampMs` / `mStatsEndTimestampMs` | long | 统计会话起止（UTC 毫秒） |
| `mBatteryCapacityMah` | double | 电池容量 mAh |
| `mDischargePercentage` | int | 累计放电百分比（可 >100） |
| `mDischargedPowerLower/Upper` | double | 实际放电功率区间 |
| `mUidBatteryConsumers` | `List<UidBatteryConsumer>` | 每 UID 功耗归因（CursorWindow 存储） |
| `mAggregateBatteryConsumers[2]` | 数组 | 设备级 + 全应用聚合 |
| `mBatteryStatsHistory` | `BatteryStatsHistory` | 可选 history 序列 |

**关键常量**（同文件 L123-129）：
- `BATTERY_CONSUMER_CURSOR_WINDOW_SIZE = 5_000 * 700` ≈ **3.5 MB** CursorWindow
- `STATSD_PULL_ATOM_MAX_BYTES = 45000` —— statsd 单次 pull atom 硬上限
- `UID_USAGE_TIME_PROCESS_STATES = {FOREGROUND, BACKGROUND, FOREGROUND_SERVICE}` —— 进程态时间维度

**调用链**：
```
App 进程 (BatteryUsageStatsManager.getBatteryUsageStats)
 → IBatteryStats.getBatteryUsageStats(queries) [Binder, 需 BATTERY_STATS 权限]
 → system_server: BatteryStatsService$BinderService.getBatteryUsageStats (L729-731)
 → BatteryStatsService.getBatteryUsageStats (L1061-1075)
 → BatteryUsageStatsProvider.getBatteryUsageStats(mStats, queries)
 → mStats (BatteryStatsImpl) 从 mHistoryBuffer 重建快照
 → BatteryUsageStats 实例 (Parcelable, Closeable)
```

**statsd 集成关键路径**（`BatteryUsageStats.getStatsProto()` L431-461）：
1. **三段式降级**：起始 `maxRawSize = STATSD_PULL_ATOM_MAX_BYTES * 1.75 = 78,750` 字节；最多 3 次尝试，每次按 `maxRawSize = 45000 * rawSize / protoOutput.length - 1024` 比例回退；兜底用 `rawSize = 45000` 强切
2. **UID 排序权重**：`weight = consumedPower + timeInFG * (100/3600000) + timeInBG * (300/3600000)`，**1 小时前台 ≈ 100 mAh、1 小时后台 ≈ 300 mAh**（L558-567）
3. **截断条件**：`if (proto.getRawSize() >= maxRawSize) break;` —— **只保留最耗电 + 最久前台/后台的 UID，长尾小应用被丢弃**
4. **过滤条件**：`(fgMs == 0 && bgMs == 0 && !hasBaseData)` 的 UID 跳过

**对端侧 APM 的启示**：
- App 不应再自造"估算功耗"体系。直接走 `BatteryStatsManager.getBatteryUsageStats(BatteryUsageStatsQuery)`（系统 API）拿 UID 级 power 归因
- 监听 statsd atom 时注意**长尾小应用归因数据被截断**——这是 45 KB 容量限制下的**有意取舍**，不是 bug
- 想拿完整数据应走 Binder API 拉 `BatteryUsageStats` 实例（`CursorWindow` 零拷贝传输），而非监听 statsd pull atom

**PowerStats 路径**（`frameworks/base/services/core/java/com/android/server/powerstats/StatsPullAtomCallbackImpl.java`）：
- 注册 `SUBSYSTEM_SLEEP_STATE` 和 `ON_DEVICE_POWER_MEASUREMENT` 两个 statsd pull atom
- 每次 pull 通过 `PowerStatsInternal` → `android.hardware.power.stats` HAL 读取底层实测数据
- **2 秒同步超时**（`STATS_PULL_TIMEOUT_MILLIS = 2000`）—— 超过 2 秒 statsd 标记 pull 失败

**History 持久化**（`frameworks/base/core/java/com/android/internal/os/BatteryStatsHistory.java`）：
- `mHistoryBuffer`（Parcel-backed）达到 `BatteryStatsImpl.Constants.MAX_HISTORY_BUFFER` 时刷新到 `/data/system/battery-history/battery-history-N.bh`
- 文件数达 `MAX_HISTORY_FILES` 时**FIFO 淘汰最旧文件**
- `VERSION = 210`（Parcel 格式版本号）
- `EXTRA_BUFFER_SIZE_WHEN_DIR_LOCKED = 100_000` —— 目录锁竞争时允许 100 KB 溢出，避免 watchdog 杀 system_server
- Delta 编码：`DELTA_TIME_MASK = 0x7ffff` 区分 4 字节 int / 8 字节 long / 完整 absolute update 三种时间 delta 格式

### 进程态功耗切片（关键 API 升级）

`BatteryUsageStatsAtomsProto.PowerComponentUsageSlice`（`frameworks/base/core/proto/android/os/batteryusagestats.proto` L75-92）首次引入**按进程态的功耗切片**：

```protobuf
message PowerComponentUsageSlice {
 optional PowerComponentUsage power_component = 1;
 enum ProcessState {
 UNSPECIFIED = 0;
 FOREGROUND = 1;
 BACKGROUND = 2;
 FOREGROUND_SERVICE = 3;
 CACHED = 4;
 }
 optional ProcessState process_state = 2;
}
```

这是 Android 15 相对 Android 14 最大的能力升级：**「cpu 在后台」** 这类细粒度归因数据可被平台直接产出，端侧 APM 无需自行估算。

### 与 §26.3 已有内容的衔接

§26.3 现有的「启动耗时、帧率、内存水位、业务耗时」四类指标都是**应用侧自采**。Android 15 的 `BatteryUsageStats` 体系是**系统侧归因**——解决「我这个 App 到底消耗了多少 mAh」的根本问题，建议在 APM 端把两者通过 `trace_id` / `session_id` 关联，形成「**业务耗时 × 系统功耗**」的二维分析能力。

### 反哺要点（建议加入正文）

1. 电池归因指标应优先复用 `BatteryUsageStats`（系统 API），不要自造估算体系
2. UID 切片按 weight 排序截断，长尾小应用数据**不会被 statsd 拉取到**
3. PowerStats HAL 路径只在设备支持 `android.hardware.power.stats` 时才有数据，否则回退 PowerProfile
4. 进程态功耗切片是 Android 15 首次平台级提供，建议 APM 端接入

> 一手资料：`BatteryUsageStats.java` (L1-600)、`BatteryUsageStatsQuery.java` (L1-330)、`BatteryStatsHistory.java` (L1-180)、`batteryusagestats.proto` (L1-105)、`BatteryStatsService.java` (grep 关键行)、`StatsPullAtomCallbackImpl.java` (L1-80)
> 详细报告：`DeepResearch/2026-06-11-android15-batteryusagestats-statsd-pipeline.md`

## 小结

性能指标采集要服务于治理动作。启动、帧率、内存、业务耗时都要使用统一事件模型，字段要能关联版本、场景、设备和用户会话；分位值要按场景和分群计算；劣化检测要同时看相对变化、绝对阈值和分群异常。

26.4 会继续处理 ANR 监控，26.5 会把指标、日志和 trace 放到线上排查流程里。

## 参考资料

- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 5.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]
- [结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]
- App startup time: https://developer.android.com/topic/performance/vitals/launch-time
- JankStats Library: https://developer.android.com/topic/performance/jankstats
- Custom trace events: https://developer.android.com/topic/performance/tracing/custom-events
- Native custom trace events: https://developer.android.com/topic/performance/tracing/custom-events-native
- Macrobenchmark metrics: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics
- Debug.MemoryInfo: https://developer.android.com/reference/android/os/Debug.MemoryInfo
- ActivityManager.getProcessMemoryInfo: https://developer.android.com/reference/android/app/ActivityManager#getProcessMemoryInfo(int[])
