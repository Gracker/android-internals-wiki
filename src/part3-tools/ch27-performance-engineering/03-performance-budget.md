---
title: "性能预算体系"
chapter: "27.3"
section: "27.3"
status: ready-for-review
drafted_date: "2026-06-21"
drafted_by: "openclaw"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-21"
last_verified_against: "ThoughtWorks 性能工程成熟度模型；Android Developers benchmarking / vitals / app size docs"
confidence: medium
sources:
  - type: blog
    path: "https://www.thoughtworks.com/zh-cn/insights/blog/platforms/performance-engineering-maturity-model"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking"
  - type: official
    path: "https://developer.android.com/topic/performance/reduce-apk-size"
tags: [performance-engineering, performance-budget, ci, benchmark, governance]
related_chapters: ["15.10", "19.14", "8.1", "9.1"]
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-21
last_task6_at: 2026-06-21T15:06:00+08:00
task9_state: pending
---

# 性能预算体系

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 性能预算是性能工程里的“看护定界”：为体验目标设定资源上限和失败处理方式。
- 预算必须说明统计口径、设备范围、采样方式、阈值、例外流程和 owner。
- Android 预算要覆盖帧、内存、启动、网络、功耗和包体积，且按页面与设备段分级。
- 预算失败需要分级：阻断、豁免、灰度观察和技术债进入不同处理路径。
- 预算要进入代码评审、CI、发布 scorecard 和线上看板，形成一致证据链。

<!-- outline-end -->

性能预算是团队愿意为一个体验目标支付的资源上限。它把“页面不能太卡”“启动要快一点”“包不能太大”改成可度量、可验收、可升级的工程约束。预算服务于工程边界和取舍，不用于惩罚开发者。

Android App 的预算体系通常覆盖帧、内存、启动、网络、功耗和包体积。每个预算都要说明统计口径、设备范围、采样方式、阈值、例外流程和 owner。没有这些字段，预算会变成一句口号。

在 ThoughtWorks 的性能工程框架里，预算对应“看护定界”：不是等线上变慢后再解释原因，而是在研发过程中定义哪些资源消耗已经越界。Android 团队可以把看护定界落成三类规则：合入前的静态规则，nightly 的 benchmark 阈值，灰度和线上阶段的 SLO 告警。三类规则使用同一套预算语言，后续归因才不会断裂。

## 帧预算

帧预算来自显示刷新周期。60 Hz 设备每帧约 16.67 ms，90 Hz 设备约 11.11 ms，120 Hz 设备约 8.33 ms。应用层不能把整段时间都占满，因为 input、Choreographer、主线程任务、RenderThread、GPU、SurfaceFlinger 和 HWC 都要在同一帧内协作。对业务页面来说，预算更适合以 jank rate、slow frame、frozen frame 和关键交互耗时表达。

可执行的帧预算示例：

- 首页信息流：60 Hz 设备 slow frame 占比低于 3%，frozen frame 占比低于 0.1%，列表连续滑动 10 秒的 P95 frame duration 小于 32 ms。
- 商品详情：首屏进入后的 2 秒内不允许出现超过 700 ms 的主线程连续阻塞，图片加载期间 frozen frame 低于 0.2%。
- 动画场景：转场动画期间主线程单个任务不超过 4 ms，RenderThread 长帧需要有 trace 归因。

帧预算要按页面分级。首页、支付、拍摄、播放等路径应使用硬预算；低频设置页可以使用软预算。硬预算失败会阻断发布或合入，软预算失败进入风险评估。

## 内存预算

内存预算需要区分 Java heap、native heap、graphics、WebView、Bitmap 和缓存。只看 Java heap 容易漏掉 native 分配，只看 PSS 又难以定位到代码。Android 团队可以按页面和功能设预算，再用线上 OOM、ApplicationExitInfo、KOOM、LeakCanary 和 heapprofd 数据校验。

一个实用的内存预算可以这样写：低端设备进入商品详情页后，Java heap 增量不超过 35 MB，图片解码峰值不超过 20 MB，离开页面 30 秒后保留对象不超过 5 MB；连续进入 5 个详情页后，不允许出现 Activity、Fragment、ViewModel 或 adapter 持有旧页面引用。

内存预算的难点是数据规模。空列表、10 条数据和 200 条数据的结果完全不同。预算必须绑定准备数据，例如“首页 6 个模块、每个模块 10 个商品、首屏 12 张图、网络图片走真实缓存策略”。没有数据约束，预算结果没有比较价值。

## 启动预算

启动预算要区分 cold start、warm start 和 hot start。cold start 包含进程创建、Application、ContentProvider、首个 Activity、首帧和关键内容；warm start 复用进程但重建 Activity；hot start 主要是前后台切换。团队需要明确使用 Android Vitals、Macrobenchmark `StartupTimingMetric`、自研埋点还是 Perfetto trace 作为判定口径。

启动预算示例：

- cold start：核心设备段首页首帧 P50 小于 1200 ms，P95 小于 2500 ms；关键内容完成 P95 小于 3200 ms。
- warm start：P95 小于 1200 ms，不允许出现主线程同步网络、磁盘数据库迁移或 SDK 重初始化。
- hot start：P95 小于 500 ms，前后台恢复不得触发全量首页刷新。

启动预算的执行点包括启动任务注册、ContentProvider 审核、第三方 SDK 接入评审、Baseline Profiles 更新和 Macrobenchmark 回归。新增启动任务必须说明是否阻塞首帧、是否可延迟、是否有远程开关。

## 网络预算

网络预算同时约束 payload 大小、接口数量、延迟和失败恢复。Android 端经常把“接口慢”推给后端，但客户端也会制造问题：首屏串行请求过多、字段冗余、图片规格过大、弱网无缓存、重试策略失控、WebView 与 Native 重复拉取同一数据。

核心页面可以按下面方式设预算：首屏关键接口数量不超过 3 个，压缩后 JSON payload 小于 200 KB，弱网 4G 条件下端到端 P95 小于 1200 ms；图片首屏总下载量小于 1 MB，必须支持尺寸裁剪和 WebP/AVIF 等格式策略；非关键推荐、广告和埋点不得阻塞可交互。

网络预算需要后端共同签字。客户端预算只能约束请求方式和解析成本，服务端 P95、错误率、字段裁剪和缓存头需要服务端 owner 承担。

## 功耗和后台预算

功耗预算关注后台 CPU、wake lock、定位、蓝牙、传感器、网络轮询和 JobScheduler / WorkManager 任务。Android 8 以后后台执行限制逐步增强，Android Vitals 也会关注 excessive wakeups、stuck wake locks 和后台资源使用。功耗预算不能只靠实验室测一次电流，要结合线上后台时长、唤醒次数和用户投诉。

可执行预算包括：后台每小时唤醒次数低于固定阈值；单个 wake lock 持有不超过 30 秒；非用户可见同步任务必须满足充电、Wi-Fi 或空闲约束；定位请求必须有超时和生命周期绑定；前台服务必须有明确用户可见任务。

功耗预算常被业务“实时性”挑战。处理方式是把实时性分级：消息、支付和安全事件可以高优先级；营销配置、推荐刷新和日志上报应合并、延迟或批处理。

## APK 体积预算

包体积预算是发布成本约束。它影响下载转化、安装成功率、低端机存储压力和升级速度。预算应按 base APK、dynamic feature、native so、资源、Dex、字体和图片分别统计。

常见规则包括：单个 release base 下载体积增长不超过 1 MB；单个业务模块增长超过 200 KB 需要说明；新增 native so 必须说明 ABI、压缩策略和是否可按需下载；新增字体、Lottie、视频、模型文件和高分辨率图片必须有替代方案评估。bundletool、APK Analyzer 和 Gradle task 可以把这些检查放到 CI 中。

## 执行与升级

预算要进入 CI/CD 和代码评审。PR 阶段适合做包体积、R8 规则、资源大小、主线程风险扫描和 Microbenchmark；nightly 适合跑 Macrobenchmark、内存巡检和启动 trace；发布前适合跑完整 benchmark suite 和灰度对比。

预算失败时需要分级处理：

- P0：核心路径硬预算失败，阻断合入或发布，必须修复或回滚。
- P1：重要指标明显退化，但有业务必要性，需负责人、补偿计划和灰度观察。
- P2：软预算超限，进入技术债队列，并在下个季度路线图评估。

例外流程必须有到期时间。性能预算一旦允许“永久豁免”，后续每次版本都会引用旧例外。比较稳的做法是给豁免设置版本上限，并要求在 release note 或性能 scorecard 中说明风险和恢复计划。

Jetpack Benchmark、Macrobenchmark、自研脚本和 APM 看板只是执行工具。预算体系的关键是让阈值、证据和责任边界一致：同一个启动回归，在 PR、nightly、灰度和线上看板里应该能找到同一条证据链。
