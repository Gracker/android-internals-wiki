---
title: "启动监控与度量"
chapter: "21.8"
section: "21.8"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-13"
last_verified_against: "Android Developers docs, Google Play Android Vitals, Clippings structure refs"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/performance/appstartup/analysis-optimization"
  - type: official
    path: "https://developer.android.com/reference/android/app/Activity#reportFullyDrawn()"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
tags: [startup-monitoring, metrics, p50, p90, regression, android-vitals]
related_chapters: ["21.1", "26.3", "15.3", "15.5"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-03"
last_task9_at: "2026-06-03T05:27:37+08:00"
last_task9_audit: "2026-07-02"
last_task9_review_log: "logs/deep-review/2026-06-03-05-deep-review.md"
task2b_result: fixed-lite
task2b_state: fixed
last_task2b_lite_at: "2026-06-02"
reviewed_by: openclaw-task6
reviewed_date: "2026-06-03"
task6_reviewed_date: "2026-06-03"
task6_result: pass-light-edit
last_task6_at: "2026-06-03T03:06:00+08:00"
last_task6_review_log: "logs/review/2026-06-03-03-review.md"
task6_review_notes: "2026-06-03 Task6 复审：pass-light-edit。L1/L2 复审通过；禁用词扫描仅有 `线上分位值` 假阳性；锚点覆盖完整。Task9 仍 pending/needs-rework，未自动晋升。"
task9_review_notes: "2026-06-03 Task9 深度复审：pass-tech-review。P0 0 / P1 0 / P2 0；ApplicationStartInfo、reportFullyDrawn 与 Android Vitals 启动阈值口径复核通过，自动晋升 finalized。"
---

# 启动监控与度量

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 启动耗时埋点方案设计
- 🔹 线上启动性能采集与分位值分析
- 🔹 启动劣化检测与归因
- 🔹 Vitals 启动指标对标

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解启动监控与度量

21.1 到 21.7 节已经拆过启动链路、任务编排、ContentProvider、Baseline Profile、Splash Screen、延迟初始化和多进程启动。剩下的工程问题：**优化完成后，怎么在线上持续判断启动有没有变快、有没有退化、退化由谁引入**。

启动监控不是在 `Application.onCreate()` 前后打两个点。`Application` 只能覆盖 App 代码开始执行后的区间，漏掉了进程创建、Zygote fork、类加载、资源加载、首帧绘制和用户感知完成等关键阶段。线上度量要把系统口径、业务口径和用户体感放在一张表里，否则容易出现 Trace 里变快、用户仍觉得慢的情况。

## 启动耗时埋点方案设计

### 先拆清测量对象

启动耗时至少要拆成三类指标。每类指标回答的问题不同，不能混用。

| 指标 | 起点 | 终点 | 用途 | 局限 |
|------|------|------|------|------|
| 进程启动耗时 | 系统创建进程或 App 可观测的最早时间点 | `Application.onCreate()` 开始 / 结束 | 观察进程创建、类加载、初始化开销 | Android 10-14 上 App 很难拿到系统级精确起点 |
| TTID（Time To Initial Display） | 启动请求 | 首帧可见 | 判断用户何时看到第一屏 | 首屏可见不代表内容可用 |
| TTFD（Time To Full Display） | 启动请求 | `reportFullyDrawn()` 对应的内容就绪点 | 判断用户何时能使用核心内容 | 依赖业务准确上报，漏报会让数据失真 |

Android 官方文档把启动分为冷启动、温启动和热启动，并建议用首帧展示时间与完全绘制时间观察启动体验。`Activity.reportFullyDrawn()` 是 TTFD 的标准上报入口，适合在首屏核心数据、首屏列表或首个可交互区域准备完成后调用。[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

21.1 节已经解释冷 / 温 / 热启动的系统链路。这里保留引用关系：启动类型由启动原因、进程是否存活、Activity 是否复用共同决定，不在业务代码里用单个布尔值粗暴判断。

### 端侧埋点点位

一套可用的启动埋点需要覆盖系统入口、App 初始化、页面生命周期、首帧和业务完成点。

| 点位 | 推荐采集位置 | 记录字段 | 说明 |
|------|--------------|----------|------|
| `process_observed` | 最早执行的轻量入口，如 `Application.attachBaseContext()` | 进程名、版本、构建号、启动原因（如可得） | App 可观测起点，不等同于系统进程创建时间 |
| `app_on_create_start/end` | `Application.onCreate()` 前后 | 主线程耗时、初始化任务列表 | 用来拆分 App 初始化开销 |
| `activity_on_create/start/resume` | 首屏 Activity 生命周期 | Activity 名、Intent 来源、是否冷启动 | 用来识别首屏路径差异 |
| `first_draw` | 首屏 View 首次绘制后 | 首帧时间、窗口类型 | 对应用户看到第一屏的时间 |
| `content_ready` | 首屏核心内容可用时 | 页面、数据来源、是否缓存命中 | 业务口径的可用时间，适合映射到 TTFD |
| `report_fully_drawn` | 调用 `Activity.reportFullyDrawn()` 处 | 是否首次调用、调用时机 | 系统口径的完全绘制时间 |

[已验证: 官方文档, developer.android.com/reference/android/app/Activity#reportFullyDrawn()]

这里有两个常见误区。

第一，不能为了更早埋点而随意新增一个 `ContentProvider`。`ContentProvider` 会在 `Application.onCreate()` 之前初始化，本身也会增加启动成本。已有 21.3 节专门讲 ContentProvider 启动治理，本节只建议在已存在的基础设施入口中记录极轻量时间戳，不为了监控增加新的启动组件。

第二，`onResume()` 不是首帧。`onResume()` 表示 Activity 进入可交互生命周期，不代表第一帧已经完成合成。首帧至少要结合 `ViewTreeObserver.OnPreDrawListener`、`Choreographer` 或平台侧展示日志来校验。线上 SDK 可以记录近似点，线下诊断仍要回到 Perfetto / Android Studio Profiler 里看 `Choreographer#doFrame`、主线程和 RenderThread 的时序。

### 埋点字段清单

启动耗时不能只上传一个数字。服务端要做归因，端侧至少要附带以下字段。

| 字段 | 示例 | 作用 |
|------|------|------|
| App 版本 / 构建号 | `8.12.0 / 812003` | 版本归因和发版回归判断 |
| 启动类型 | cold / warm / hot | 分开计算阈值，避免热启动稀释冷启动问题 |
| 进程名 | `com.example` / `:push` | 区分主进程和子进程启动 |
| 首屏 Activity | `HomeActivity` | 按页面拆分启动路径 |
| 入口来源 | 桌面图标 / push / deep link / widget | 入口不同，启动任务集合不同 |
| 设备维度 | 机型、Android 版本、ABI、内存档位 | 排查系统和设备差异 |
| 运行状态 | 是否首次安装后启动、是否升级后首次启动、是否命中缓存 | 排查冷路径和迁移任务 |
| 任务摘要 | 初始化任务名、耗时、是否主线程 | 把退化指向具体初始化任务 |

字段越多，隐私和数据成本越高。采集原则是：只采集能服务归因的字段，不上传用户敏感内容；页面名、任务名、入口来源使用枚举值；用户操作序列只保留稳定性和性能排查需要的最小信息。详见 26.3 节的性能指标采集与上报。

## 线上启动性能采集与分位值分析

### 分位值比平均值更适合启动监控

启动耗时分布通常是长尾分布。少数低端机、升级后首次启动、弱网拉取配置、数据库迁移和冷路径 I/O 会把平均值拉高。只看平均值会误判两个方向：一个版本 P50 变好但 P99 变差，平均值可能不明显；另一个版本只有少数用户退化，平均值也可能被大量热启动样本掩盖。

线上看板建议固定展示四个分位值：

| 指标 | 含义 | 用途 |
|------|------|------|
| P50 | 中位用户体验 | 判断主路径是否变快 |
| P75 | 较慢用户体验 | 观察普通长尾是否扩大 |
| P90 | 慢启动用户体验 | 发版门禁和回归告警的主指标 |
| P99 | 极端慢启动 | 排查低端机、升级迁移、弱网和设备异常 |

分位值必须按启动类型拆开。冷启动 P90、温启动 P90、热启动 P90 是三条不同曲线。把三者合在一起，会让热启动样本把冷启动问题冲淡。

15.3 节已经给出分位数指标的通用解释。启动场景的口径可以压成一句：**冷启动看 P50/P90，热启动看 P90/P99，升级后首次启动单独看**。升级后首次启动包含 dexopt、数据库迁移、缓存重建和配置初始化，应该从常规冷启动样本中拆出来。

### 采样与上报策略

启动监控的上报量大，不能每个点位都全量上传明细。推荐分两层采集。

| 层级 | 采集内容 | 上报策略 | 用途 |
|------|----------|----------|------|
| 指标层 | TTID、TTFD、启动类型、版本、页面、设备维度 | 高采样率或全量聚合 | 看板、告警、版本对比 |
| 诊断层 | 初始化任务耗时、主线程长任务、I/O 摘要、线程池状态 | 低采样率，只对慢启动样本打开 | 退化归因 |

慢启动样本可以按规则触发诊断上报：冷启动 TTID 超过 P90 阈值、TTFD 超过业务阈值、首屏 Activity 首次打开、升级后首次启动。这样既能控制成本，又能保证慢样本有足够上下文。

### 看板拆分方式

启动看板最少需要五个视图。

| 视图 | 观察方式 | 直接用途 |
|------|----------|----------|
| 版本趋势 | 每个版本的冷 / 温 / 热启动 P50/P90/P99 | 判断新版本是否退化 |
| 页面排行 | 按首屏 Activity 展示 TTID / TTFD | 找慢启动入口 |
| 设备热力图 | 机型 × Android 版本 × 内存档位 | 找设备集中问题 |
| 任务耗时排行 | 初始化任务名 × 主线程耗时 × 出现率 | 找具体初始化任务 |
| 慢样本列表 | 单次启动的时间线和环境字段 | 做个案复盘 |

看板上的每个数字都要带样本量。P90 只有 20 个样本时没有稳定意义，低流量灰度版本尤其容易出现这种问题。灰度阶段建议同时看绝对耗时和样本数，样本不足时只做风险提示，不直接拦截版本。

## 启动劣化检测与归因

### 劣化检测规则

启动劣化检测要同时看相对变化和绝对阈值。只看相对变化，低基线页面容易被小波动触发；只看绝对阈值，已经很慢的页面可能长期没有告警。

推荐的基础规则如下。

| 规则 | 条件 | 建议级别 | 处理动作 |
|------|------|----------|----------|
| 冷启动 P90 退化 | 新版本较上一稳定版本上升 ≥ 15%，且样本量 ≥ 1000 | P1 | 暂停灰度，拉取慢样本 |
| TTID 绝对超线 | 冷启动 P90 超过内部阈值，如 3s | P1 | 检查首屏主线程和 I/O |
| TTFD 绝对超线 | 首屏内容可用 P90 超过业务阈值 | P2 | 检查首屏数据、缓存和网络 |
| 页面局部退化 | 单个入口 P90 上升 ≥ 25% | P2 | 分派给页面负责人 |
| 设备局部退化 | 某机型 / OS P90 是整体的 2 倍以上，样本量 ≥ 100 | P2 | 排查 ROM、SoC、WebView 和图形栈差异 |
| 升级后首次启动异常 | 升级首启 P90 上升 ≥ 30% | P1 | 检查迁移任务、dexopt 和缓存重建 |

这些阈值是起点，不能直接复制到所有产品。内容型 App、工具型 App、金融 App 的首屏任务不同，内部阈值要结合历史 P90、用户留存和业务入口重要度设定。

### 归因维度

一次启动退化通常来自四类原因。

| 归因方向 | 典型证据 | 排查入口 |
|----------|----------|----------|
| 初始化任务增加 | 某个任务耗时或出现率上升 | 21.2 节启动任务编排 |
| 主线程被占用 | 主线程长任务、锁等待、同步 I/O 增多 | Perfetto 主线程轨道、StrictMode、任务耗时排行 |
| 资源与编译变化 | 首次安装 / 升级后首启变慢，Baseline Profile 命中下降 | 21.4 节 Baseline Profile 实战 |
| 设备或系统差异 | 某 OS / 机型集中退化 | 17 章 OEM 差异、15.5 节线上性能监控 |

归因时不要直接把慢启动派给“启动框架”。先看退化是否只出现在某个首屏、某个入口、某个版本或某类设备。启动框架负责提供时间线和任务归属，业务模块负责解释自己新增的初始化成本。

### 版本归因流程

一条可执行的版本归因流程如下。

1. 固定对比基线：当前灰度版本 vs 上一个稳定版本，不跨多个大版本比较。
2. 拆启动类型：冷启动、温启动、热启动分别比较 P50/P90/P99。
3. 拆入口和页面：确认退化是全局退化，还是某个入口退化。
4. 拉慢样本：取 TTID 或 TTFD 超过 P90 的样本，查看初始化任务时间线。
5. 对提交窗口：把退化首次出现时间与版本构建时间、灰度时间、配置发布时间对齐。
6. 分派负责人：按任务名、页面名、模块所有者分派，无法归因时再升级到启动治理负责人。

这套流程的价值在于把“启动变慢了”拆成“哪个版本、哪个入口、哪类用户、哪个任务变慢”。没有这一层拆分，启动优化很容易变成全员猜测。

### Android 15+ 的平台启动信息

Android 15 起，平台增加了应用启动信息相关 API（`ApplicationStartInfo`，added in API 35），用于提供启动类型、启动原因、时间戳等信息。获取入口是 `ActivityManager.getHistoricalProcessStartReasons(int)` 或 `addApplicationStartInfoCompletionListener()`。核心字段包括 `getReason()`、`getStartType()`、`getStartupState()`、`getStartupTimestamps()`；时间戳为 monotonic nanoseconds，覆盖 `START_TIMESTAMP_FORK` / `BIND_APPLICATION` / `APPLICATION_ONCREATE` / `FIRST_FRAME` / `FULLY_DRAWN` 等阶段。[已验证: Android Developers reference, API 35; Task9 确认 2026-05-17]

`addApplicationStartInfoCompletionListener()` 的完成回调以 first frame drawn 为边界，不等待业务调用 `Activity.reportFullyDrawn()`。如果要用平台时间戳校准 TTFD / FULLY_DRAWN，必须先在业务内容可用后调用 `reportFullyDrawn()`，再通过 `getHistoricalProcessStartReasons()` 或后续拿到的 `ApplicationStartInfo` 副本读取 `START_TIMESTAMP_FULLY_DRAWN`；否则这个时间戳可能不存在。[已验证: Android Developers ActivityManager/ApplicationStartInfo reference, API 35]

它适合补齐 App 自建埋点拿不到的系统侧起点，但只能覆盖 Android 15+ 设备，线上监控仍需要保留 Android 10-14 的兼容采集路径。

这个能力更适合作为校准源：在 Android 15+ 设备上对比平台时间戳和自建埋点，确认 TTID / TTFD 的端侧口径是否偏移；不要把它当成替代全版本启动监控的方案。

## Vitals 启动指标对标

### Android Vitals 的启动阈值

Google Play Android Vitals 会统计应用启动时间，并按启动类型给出慢启动阈值。公开文档中的阈值口径如下：

| 启动类型 | Android Vitals 慢启动阈值 | 工程含义 |
|----------|----------------------------|----------|
| 冷启动 | ≥ 5 秒 | 用户从零启动 App，系统需要创建进程并完成首帧展示 |
| 温启动 | ≥ 2 秒 | 进程可能存在，但 Activity 需要重新创建或恢复 |
| 热启动 | ≥ 1.5 秒 | 进程和 Activity 状态较完整，用户期望更快返回 |

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

这些阈值是 Play 侧的外部基线，不适合作为团队内部唯一目标。内部发版门禁通常要更严格：冷启动 P90 要低于 Vitals 阈值，并且核心入口的 TTFD 要满足业务可用标准。对启动体验敏感的首页、支付页、拍摄页，要单独设更低阈值。

### Vitals 与自建监控的差异

Android Vitals 和自建启动监控的差异主要在四个方面。

| 维度 | Android Vitals | 自建监控 |
|------|----------------|----------|
| 覆盖范围 | Google Play 用户和满足采集条件的设备 | 可覆盖全渠道、灰度、内测和国内分发 |
| 延迟 | 有统计延迟 | 可分钟级接近实时 |
| 维度 | 系统维度和基础设备维度 | 可附加页面、入口、任务和业务字段 |
| 用途 | 外部质量基线、商店风险 | 内部归因、发版门禁、负责人分派 |

因此，Vitals 适合做外部对标，自建监控适合做日常治理。二者数字不一致时，要先检查口径：启动类型是否一致、是否只看前台启动、是否包含升级后首次启动、是否按页面拆分、是否存在采样偏差。

### 内部目标建议

一个可执行的内部启动目标可以分三层。

| 层级 | 指标 | 示例目标 | 用途 |
|------|------|----------|------|
| 外部底线 | Vitals 慢启动占比 | 不触发 Play 慢启动风险 | 防止商店侧质量问题 |
| 版本门禁 | 冷启动 TTID P90 | 新版本不高于上一稳定版本 15% | 控制版本退化 |
| 核心入口目标 | 首页 TTFD P90 | 达到产品设定的可用时间 | 对齐用户体感 |

目标设定后，要固定三件事：统计窗口、样本量下限和豁免条件。比如升级后首次启动、首次安装后启动、低端机首启可以单独建基线，但不能从总数据里无说明地剔除。

## 小结

启动监控的工作顺序是：先定义 TTID / TTFD 和启动类型，再采集端侧时间线与归因字段，随后用 P50/P90/P99 建看板和告警，并把 Android Vitals 作为外部校准。优化是否有效，不由单次 Trace 决定，而由线上分位值、慢样本归因和版本趋势共同决定。
