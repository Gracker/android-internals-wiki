---
title: "启动优化复盘框架与案例模板"
chapter: "21.9"
section: "21.9"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-02"
last_verified_against: "AOSP android-17.0.0_r1 Activity.reportFullyDrawn / ActivityMetricsLogger.notifyFullyDrawn, Android Developers launch-time / App Startup / Baseline Profiles docs"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "https://developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile"
  - type: aosp
    path: "frameworks/base/core/java/android/app/Activity.java#reportFullyDrawn"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java#notifyFullyDrawn"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md"
  - type: clippings-structure-ref
    path: "Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md"
  - type: local
    path: "src/part5-app/ch21-startup/01-startup-analysis.md"
  - type: local
    path: "src/part5-app/ch21-startup/02-startup-framework.md"
  - type: local
    path: "src/part5-app/ch21-startup/04-baseline-profile-practice.md"
tags: [case-study, startup, optimization, baseline-profile, startup-framework]
related_chapters: ["21.1", "21.2", "21.4"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-05-19"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-19"
task2b_state: "fixed"
task2b_result: "fixed"
last_task6_at: "2026-05-19T08:16:46+08:00"
last_task6_audit: "2026-06-11"
last_task6_review_log: logs/review/2026-05-19-08-review.md
last_task9_at: "2026-05-19T08:27:59+08:00"
last_task9_audit: "2026-07-02"
last_task9_review_log: logs/deep-review/2026-05-19-08-deep-review.md
task9_review_notes: "2026-05-19 Task9：pass-tech-review。P0 0 / P1 0 / P2 0；源码锚点、App Startup、Baseline Profile 与 TTFD 链路复核通过；满足 Task6+Task9+queue 条件，自动晋升 finalized。"
auto_promoted_by: task9-deep-tech-review
auto_promoted_at: "2026-05-19T08:27:59+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-17
---

# 启动优化复盘框架与案例模板

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 大型 App 启动优化实战
- 🔹 启动框架演进案例
- 🔹 Baseline Profile 实施效果

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要看启动优化复盘框架

前面几节已经把启动分析、任务编排、`ContentProvider`、Baseline Profile、启动页、延迟初始化、多进程和线上监控逐一拆开讲过。本章收束到复盘框架视角：拿到一个启动慢的大型 App，怎样把 trace、任务清单、profile、线上指标串成一次可复用的优化过程。

本节不重复前文原理，重点放在三个工程场景的排查框架：`Application` 初始化过重、启动框架从散点初始化演进为任务图、Baseline Profile 从“文件已生成”走到“收益可验证”。

> **定位说明**：本节提供排查框架和复盘模板，暂不包含脱敏后的真实案例。团队拿到自己的 Perfetto trace 和线上指标后，按末尾“启动案例复盘模板”填写，就能产出可复查的优化记录；有可脱敏分享的真实案例时，再补充到对应场景。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

## 大型 App 启动优化实战

### `Application.onCreate()` 被 SDK 初始化占满

大型 App 的冷启动慢，最常见的形态是 `Application.onCreate()` 里堆了大量同步初始化：Crash、埋点、推送、广告、网络、配置、数据库、实验平台、图片库都想抢启动入口。每个 SDK 单看只花 20-50 ms，串起来就是几百毫秒。

排查时先把启动分成 4 段量出来，再决定改动位置：进程创建到 `attachBaseContext()`、`Application` 初始化、入口 `Activity` 创建、首帧绘制。21.1 节已经给出 TTID / TTFD 和 Perfetto 读法，本案例只看 `Application` 段。

可执行的复盘表如下：

| 任务 | 线程 | 启动前是否必需 | 耗时口径 | 处理方式 |
|---|---|---|---|---|
| Crash SDK | 主线程 / 后台线程 | 启动前必需，但只需要最小捕获能力 | wall time + CPU time | 拆成同步安装 handler、异步上传历史报告 |
| 埋点 SDK | 后台线程 | 首帧前不必完整初始化 | wall time | 首帧后补全，启动阶段只缓存事件 |
| 推送 SDK | 主线程回调较多 | 多数业务不需要阻塞首帧 | wall time | 延迟到首页首帧后，或按进程判断跳过 |
| 数据库打开 | 主线程风险高 | 首屏如不读取本地数据就不必启动前打开 | I/O time | 改为懒打开，升级迁移放到后台窗口 |
| 远程配置 | 网络 / I/O | 不应阻塞首帧 | 等待时间 | 使用本地缓存，网络刷新放到首帧后 |

这张表用来区分三类任务：首帧前必须完成、首帧前只要完成最小能力、首帧后再做也不影响用户第一眼内容。改完后再对比 TTID、TTFD、启动慢帧和启动阶段 Crash / ANR，防止把启动耗时转移成首屏不可用。

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

### 从 trace 里判断优化方向

同样是 300 ms，trace 中的形态不同，处理方式也不同。

| 观测现象 | 更可能的问题 | 优先处理 |
|---|---|---|
| 主线程长时间 Running，函数集中在 JSON、反射、初始化逻辑 | CPU 计算或类加载成本高 | 精简代码路径、拆任务、Baseline Profile |
| 主线程 Blocked / Sleeping，附近有文件读写或数据库 | I/O 或锁等待 | 移出启动路径、使用缓存、拆锁 |
| `HeapTaskDaemon` 在启动阶段抢占 CPU，伴随频繁对象分配 | 启动分配过多触发 GC 压力 | 减少临时对象、复用缓存、推迟大对象创建 |
| 后台线程过多，CPU 被大量初始化任务占满 | 并发过度 | 限制启动线程池、按优先级分层执行 |

把速度优化拆成 CPU、缓存、任务调度三个方向来看，放到启动场景里对应的工程动作是：减少启动路径上必须执行的代码；让会被马上访问的类、资源、配置更早命中缓存；让首帧相关线程拿到足够 CPU 时间。不要把线程数开大当成通用解法——启动阶段 CPU 核心有限，过量并发会让主线程和 RenderThread 排队。


### 对 GC 抑制方案的取舍

有一类激进方案值得了解：通过分析 ART 的 `HeapTaskDaemon` 和 `ConcurrentGCTask`，在启动阶段延后 GC 执行。这个方向说明了一个事实：启动期 GC 会抢 CPU，也会放大锁等待。但 App 侧不建议把 hook ART 内部符号作为常规线上方案。

App 侧优先按这个顺序处理：

- 减少启动期对象分配，尤其是大 JSON、临时集合、反射元数据和一次性 Bitmap。
- 把非首屏对象创建推迟到首帧后，避免 `Application` 和入口 `Activity` 同时制造分配峰值。
- 用 Perfetto 或 Android Studio Profiler 确认 GC 是否出现在启动关键区间，不能只凭“启动慢”推断 GC。
- 只有在实验分支中评估底层 hook，且要按 Android 版本、ABI、厂商 ROM 单独验证崩溃和兼容性。

这类方案适合作为研究素材，不适合作为启动优化的默认动作。


## 启动框架演进案例

### 阶段一：散点初始化

早期项目通常有三类初始化入口：`Application.onCreate()`、多个 SDK 的 `ContentProvider`、入口 Activity 的临时代码。入口多不一定是问题；缺少统一的依赖关系、耗时统计和失败策略，才会让启动阶段失控。

Jetpack App Startup 官方文档指出，多个组件各自声明 `ContentProvider` 会增加启动成本，并且系统初始化不同 Provider 的顺序不适合表达复杂依赖。App Startup 用单个 Provider 和 `Initializer` 依赖声明改善这个问题，适合把多个静态初始化点集中管理。

[已验证: 官方文档, developer.android.com/topic/libraries/app-startup]

### 阶段二：统一清单和分层执行

当启动任务超过几十个，只靠 App Startup 的拓扑依赖不够用。团队需要维护一张启动任务清单，给每个任务补齐字段：

| 字段 | 用途 |
|---|---|
| `taskId` | 稳定标识，便于 trace、日志、看板互相对应 |
| `dependencies` | 声明必须等待哪些任务完成 |
| `threadMode` | 标记主线程、I/O、CPU、任意线程 |
| `priority` | 标记首帧前必需、首帧前最小能力、首帧后执行 |
| `timeoutMs` | 防止软依赖无限等待 |
| `owner` | 任务异常、耗时回归时能找到负责人 |
| `metricsName` | 对应线上启动阶段指标 |

这张清单是启动框架演进的分水岭。有了它，启动任务会按依赖、优先级和线程约束调度，不再由 `Application` 中的代码顺序决定执行顺序。21.2 节已经展开 DAG、关键路径和线程池策略，本案例关注演进结果：每个任务有位置、有耗时、有责任人、有可回滚开关。

[已验证: 官方文档, developer.android.com/topic/libraries/app-startup]

### 阶段三：把框架接入发布流程

启动框架除了运行时调度任务，还要进入发布检查。一个实用的发布门禁可以包含这些项：

| 检查项 | 阈值建议 | 失败动作 |
|---|---|---|
| 新增首帧前任务 | 每个版本必须 review | 没有 owner 和耗时预估不允许合入 |
| 单任务启动耗时 | 主线程任务超过 10 ms 需要说明 | 拆分、延迟或移到后台线程 |
| 启动关键路径长度 | 相比上个版本上升需解释 | 关联变更列表，灰度前修复 |
| 任务超时次数 | 灰度阶段持续出现要报警 | 降级软依赖或关闭任务 |
| 入口 Provider 数量 | 增加必须说明原因 | 改用 App Startup 或显式初始化 |

这些阈值需要按项目基线调整。稳定的做法是先连续观测 2-3 个版本，确认 P50 / P90 / P95 波动范围，再把阈值写进 CI 和灰度看板。

## Baseline Profile 实施效果

### 文件生成了，但收益不稳定

Baseline Profile 失败时常表现为本地测试有收益，线上新安装用户收益不稳定。原因通常出在三个位置：profile 没打进正确 variant、生成脚本没有覆盖真实启动路径、设备侧还没按 profile 完成编译。

验证顺序要按 21.4 节的清单走：源码文件、构建产物、设备编译状态、性能收益。跳过任一层，都会把问题看错。

| 验证层 | 具体检查 | 常见问题 |
|---|---|---|
| 源码 | `baseline-prof.txt` 是否随启动改动更新 | 脚本只跑入口 Activity，漏掉登录态、弹窗、首页 tab |
| 构建 | APK / AAB 是否包含 `baseline.prof` 和 `baseline.profm` | 只在 benchmark variant 生效，release 包没带上 |
| 安装 | 安装渠道是否支持 profile 交付 | 侧载包、第三方商店、Play 分发路径不同 |
| 编译 | `ProfileVerifier` 或 `dumpsys package dexopt` 是否显示已按 profile 编译 | profile 已入队但还没完成编译 |
| 收益 | Macrobenchmark 与线上 A/B 是否方向一致 | 样本状态不同，网络、缓存、弹窗污染结果 |

[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/overview]
[已验证: 官方文档, developer.android.com/topic/performance/baselineprofiles/create-baselineprofile]

### Baseline Profile 适合解决哪类启动慢

Baseline Profile 解决的是启动路径上的类加载、解释执行、JIT 预热和代码布局相关成本。它不能处理主线程 I/O、网络等待、锁竞争、数据库升级和 SDK 同步初始化。

判断是否应该优先做 profile，可以看 trace：

| trace 表现 | Profile 优先级 | 说明 |
|---|---|---|
| 启动路径里类加载、反射、Compose 首次进入占比高 | 高 | profile 可以让热点方法更早编译 |
| 首装首开慢，打开几次后明显变快 | 高 | 符合 JIT / profile 收敛特征 |
| 主线程卡在文件、数据库、锁等待 | 低 | 先移除同步等待 |
| 启动慢来自远程配置、广告、网络请求 | 低 | profile 不会缩短网络等待 |
| 首页首帧很快，内容完整时间很慢 | 中 | 需要拆 TTID 和 TTFD，看慢在代码还是数据 |

AOSP `Activity.reportFullyDrawn()` 的注释说明，系统会用这个信号辅助启动耗时诊断和优化；`ActivityMetricsLogger` 也会在 fully drawn 时更新启动统计。做 profile A/B 时，TTID 和 TTFD 都要看，不能只看首帧。

[已验证: AOSP, frameworks/base/core/java/android/app/Activity.java#reportFullyDrawn]
[已验证: AOSP, frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java#notifyFullyDrawn]

### 和 Dex 布局优化的关系

Redex 的 Dex 类重排序可以解释空间局部性：把启动路径上会连续访问的类排得更近，减少加载和缓存 miss。现代 Android 工程里，Baseline Profile、Startup Profile、AGP / R8 / D8 的 profile 处理已经覆盖了很大一部分工作。

工程上不建议同时叠很多黑盒优化。App 侧先按这条路径验证：

1. 用 Macrobenchmark 生成覆盖启动和高频路径的 Baseline Profile。
2. 检查构建产物和设备编译状态。
3. 用同一设备池对比 `CompilationMode.None()` 和 `CompilationMode.Partial()`。
4. 如果仍然有明确的 Dex 布局问题，再评估 Redex 或构建系统级布局优化。


## 启动案例复盘模板

启动优化案例写成文章或内部复盘时，建议保留同一套字段。否则每次复盘都只剩“优化了几个点、快了多少”，后续版本很难复用。

| 字段 | 内容 |
|---|---|
| 背景 | 版本、设备池、用户状态、冷 / 温 / 热启动口径 |
| 问题 | TTID、TTFD、启动慢帧、启动 ANR 或 Crash 的异常表现 |
| 证据 | Perfetto trace、Macrobenchmark、线上看板、代码变更 |
| 瓶颈 | CPU、I/O、锁、GC、类加载、渲染、网络中的哪一类 |
| 改动 | 删除、延迟、并行、降级、profile、缓存、框架调整 |
| 风险 | 首屏不可用、初始化顺序变化、上报延迟、低端机副作用 |
| 验证 | 本地多轮测试、灰度 A/B、低端机、回滚开关 |
| 后续 | 新增门禁、任务 owner、指标看板、待验证项 |

这个模板和 21.8 的启动监控配合使用：本地 trace 负责解释原因，线上指标负责证明影响范围。案例的价值来自后续复用：下一次启动退化时，团队能更快定位到任务、owner 和版本变更。

[来源: src/part5-app/ch21-startup/01-startup-analysis.md]
[来源: src/part5-app/ch21-startup/02-startup-framework.md]
[来源: src/part5-app/ch21-startup/04-baseline-profile-practice.md]
