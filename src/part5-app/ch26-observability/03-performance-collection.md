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
last_task9_audit: "2026-05-18"
task2b_state: done
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

Part 5 的启动、渲染、内存章节已经分别展开单项监控方法。这些单项监控最终要放回同一个 App 可观测性系统里：启动耗时、慢帧、内存水位、业务耗时都要走统一事件模型，否则后端很难把同一版本、同一页面、同一用户会话里的性能变化关联起来。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

## 启动耗时、帧率、内存水位等指标采集

端侧指标要分成两类：低频状态样本和事件触发样本。低频状态样本适合描述内存、线程数、进程前后台状态；事件触发样本适合描述启动、页面停留、慢帧窗口、业务操作耗时。两类样本的采集频率、上报时机和字段都不同。

| 指标组 | 推荐采集时机 | 主要字段 | 治理用途 | 关联章节 |
| --- | --- | --- | --- | --- |
| 启动耗时 | 冷 / 温 / 热启动结束、`reportFullyDrawn()` 调用、慢启动触发 | TTID、TTFD、启动类型、首屏 Activity、入口来源、版本、设备档位 | 判断启动退化、区分首帧和内容可用时间 | 21.8 |
| 帧率与慢帧 | Activity 前台停留窗口、页面切换、滚动场景结束 | 页面、场景、刷新率、总帧数、慢帧数、冻帧数、P90/P99 帧间隔 | 发现页面级流畅性退化 | 22.8 |
| 内存水位 | 前台每 3-5 分钟、页面切换、低内存回调、OOM 前后 | PSS、Java Heap、Native Heap、RSS、图片缓存、进程名、前后台 | 发现泄漏、缓存膨胀和 OOM 前兆 | 23.7 |
| 业务耗时 | 用户操作开始 / 结束、网络请求完成、关键任务完成 | trace 名称、场景 ID、耗时、结果码、是否缓存命中、网络类型 | 把性能退化定位到业务路径 | 26.1 |

启动指标要采用系统口径和业务口径两套字段。Android Vitals 使用 TTID 判断首帧展示；`Activity.reportFullyDrawn()` 对应的 TTFD 更接近首屏内容可用。线上采集时，TTID 用来和 Vitals 对标，TTFD 用来判断业务体验。两者不能互相替代。[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

渲染指标默认不要逐帧上报。AndroidX JankStats 会报告耗时过长的应用帧，并支持给帧附加 UI 状态。线上更适合按页面停留窗口聚合：总帧数、jank 帧数、frozen 帧数、P90/P99、最大连续慢帧时长。命中阈值后再抽样上传慢帧现场或 Perfetto 片段。[已验证: 官方文档, developer.android.com/topic/performance/jankstats]

内存指标要把页口径和对象口径分开。`Debug.MemoryInfo` / `ActivityManager.getProcessMemoryInfo()` 适合记录 PSS、dalvik / native / other PSS 等页级数据；`Runtime.totalMemory() - Runtime.freeMemory()` 适合记录 Java Heap 对象使用量。两个口径都叫“内存”，但它们解释的问题不同，不能相加后当作单一结论。[已验证: 官方文档, developer.android.com/reference/android/os/Debug.MemoryInfo；developer.android.com/reference/android/app/ActivityManager#getProcessMemoryInfo(int[])]

采集入口要足够轻。主线程上只记录时间戳、枚举字段和少量数值；序列化、压缩、落盘和上传放到后台线程。Clippings 里的上报组件章节把高频埋点拆成采样、存储、上报、容灾四块，这个拆法适合性能指标系统复用：采集入口不要负责存储和网络。[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 33.md]

## 自定义 Trace 与业务埋点

平台指标只能告诉团队“哪里慢了”，业务 Trace 负责说明“慢的是哪个场景”。一个支付页慢帧、一个搜索页慢启动、一次首屏接口超时，如果没有稳定的 `scene_id` 和 trace 名称，后端只能按 Activity 聚合，分派时仍要人工翻日志。

自定义 Trace 建议采用三层命名：产品场景、技术阶段、结果状态。

| Trace 层级 | 示例 | 说明 |
| --- | --- | --- |
| 产品场景 | `home.feed.refresh`、`pay.cashier.submit` | 对应用户可感知的操作或页面段落 |
| 技术阶段 | `db.query`、`image.decode`、`layout.bind`、`network.request` | 对应可归因的执行阶段 |
| 结果状态 | `success`、`timeout`、`cache_hit`、`fallback` | 用于区分慢和失败是否同源 |

Android 官方 tracing 文档支持在 Java / Kotlin 代码里用 `Trace.beginSection()` / `Trace.endSection()` 添加自定义 trace section，native 代码里用 `ATrace_beginSection()` / `ATrace_endSection()`。这些切片会出现在系统 trace 里，适合线下和灰度诊断；线上常规上报只记录同名阶段的摘要耗时，避免把完整 trace 文件变成常驻数据。[已验证: 官方文档, developer.android.com/topic/performance/tracing/custom-events；developer.android.com/topic/performance/tracing/custom-events-native]

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

Macrobenchmark 的 `StartupTimingMetric`、`FrameTimingMetric`、`TraceSectionMetric` 适合做线下基准和 CI 门禁。线上指标负责观察真实用户分布，线下 benchmark 负责在可控设备和场景里复现变化。二者使用同名指标和同名场景，可以减少“实验室变快、线上没变化”的对账成本。[已验证: 官方文档, developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics]

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

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]
[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 34.md]

## [自动发现] 上报组件自监控

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
