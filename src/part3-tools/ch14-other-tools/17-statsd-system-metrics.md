---


title: statsd 与系统级指标采集
chapter: 14.17
status: ready-for-review
drafted_date: 2026-05-20
applicable_versions: Android 11 (API 30) - Android 17 (API 37)
last_verified: 2026-05-20
last_verified_against: AOSP android-17.0.0_r1 packages/modules/StatsD, frameworks/proto_logging/stats/atoms.proto, source.android.com Statsd 文档
confidence: medium
sources: 
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system/statsd"
  - type: aosp
    path: "packages/modules/StatsD/statsd/src/StatsService.cpp"
  - type: aosp
    path: "packages/modules/StatsD/statsd/src/statsd_config.proto"
  - type: aosp
    path: "packages/modules/StatsD/service/java/com/android/server/stats/StatsCompanionService.java"
  - type: aosp
    path: "frameworks/proto_logging/stats/atoms.proto"
  - type: official
    path: "https://source.android.com/reference/tradefed/com/android/tradefed/util/statsd/ConfigUtil"
  - type: official
    path: "https://developer.android.com/tools/adb"
tags: [statsd, observability, perfetto, tools]
related_chapters: ["13.9", "13.10", "14.10", "15.3", "26.3"]
created_by: task2a-knowledge-gap
created_date: 2026-05-20
gap_source: AOSP结构/官方文档/已有章节深挖
task2b_result: fixed-lite
task2b_state: fixed
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: reviewed
last_task2b_lite_at: 2026-07-02
task9_result: auto-fixed
last_task9_autofix_at: 2026-07-02
last_task9_at: 2026-07-02
task9_review_notes: "2026-07-02 Task9 deep-review AUTO-FIX: P0 0 / P1 1 / P2 0；收窄 AOSP 证据锚点到 android-17.0.0_r1，补齐 StatsManagerService 在配置/权限/重注册链路中的角色，修正 DeepResearch 延伸阅读中的 JNI/Android 17 新增权限表述；回到 Task6 复审。详见 logs/deep-review/2026-07-02-07-deep-review.md。"
---
-

# 14.17 statsd 与系统级指标采集

Android 平台的系统级指标并不只来自 Perfetto Trace。许多事件型信号，例如 ANR、LMK、JobScheduler 状态、启动事件、功耗和网络统计，都通过 statsd 汇总成 atom，再按配置生成报告。

本节讲清 statsd 在观测体系中的位置、atom 和 metric 的建模方式、本地调试流程，以及它和 Perfetto、logcat、dumpsys 的分工。读完后，遇到“线上看到了某个系统事件，但 Trace 里找不到完整时序”这类问题，应该知道下一步查哪个信号。

<!-- outline-start -->
## 要点

### 🔹 statsd 在 Android 观测体系中的位置
说明 statsd、StatsCompanionService、StatsLog、atoms.proto 与 Mainline 模块的分工，明确它和 Perfetto、logcat、dumpsys 各自回答的问题。

### 🔹 Atom 模型：pushed、pulled 与 metric 配置
梳理 pushed atom、pulled atom、event metric、duration metric、gauge metric 的用途，以及配置、触发、聚合、拉取报告的基本路径。

### 🔹 性能排障常见数据入口
整理 ANR、JobScheduler、LMK、Game Mode、UprobeStats、功耗相关 atom 在排障中的使用方式，避免把 statsd 事件误当成完整 trace。

### 🔹 adb / cmd stats 调试流程
给出本地验证路径：推送配置、触发场景、拉取报告、清理配置，并说明 shell 权限、userdebug / eng 与量产机差异。

### 🔹 与 Perfetto、logcat、dumpsys 的交叉验证
建立排障顺序：statsd 定位事件是否发生，Perfetto 还原时序，logcat / dumpsys 补系统状态，避免单一信号误判。

### 🔹 权限、版本与 OEM 边界
说明 StatsD APEX、Android 版本差异、厂商 atom 扩展、隐私限制和线上采集边界，给出适合写进排障手册的安全用法。

## 扩展

### 🔸 Tradefed / CTS 中的 statsd collector
补充测试框架如何下发 statsd 配置、收集指标，以及适合做性能回归门禁的场景。

### 🔸 statsd report 与线上 APM 的边界
讨论 statsd 更适合系统级事件和聚合指标，线上 APM 更适合 App 内埋点、用户路径和业务维度。

### 🔸 自定义 Atom / 厂商扩展的兼容性风险
记录自定义 atom、vendor atom、版本升级和字段语义变化对长期指标看板的影响。

<!-- outline-end -->

## statsd 适合回答什么问题

statsd 是 Android 平台侧的指标守护进程。AOSP 文档把 Statsd 模块定义为两部分：后台运行的 native 服务 statsd，以及运行在 system_server 进程中的 Java 服务 StatsCompanionService。文档还说明该模块以 APEX 形式发布，模块名为 `com.android.os.statsd`，Android 11 及以上设备可用；Android 12 起，StatsD 相关源码从 `frameworks/base/cmds/StatsD`、`frameworks/base/apex/StatsD` 和 `system/core/libstats` 迁移到 `packages/modules/StatsD`。[已验证: 官方文档, source.android.com/docs/core/ota/modular-system/statsd]

这套设计决定了 statsd 的定位：它不是录制每一段执行时序的工具，而是把系统事件和状态样本按配置聚合成 metric report。Perfetto 更适合回答“这一段时间线程和内核事件按什么顺序发生”，statsd 更适合回答“某类事件有没有发生、发生了多少次、按 UID / 包名 / 状态切分后分布如何”。

几个组件的分工如下：

| 组件 | 位置 | 职责 | 排障时提供的信息 |
| --- | --- | --- | --- |
| `statsd` | `packages/modules/StatsD/statsd/src/` | 接收 atom、维护配置、聚合 metric、生成 report | 事件计数、状态持续时间、拉取样本、异常触发 |
| `StatsManager` / `StatsManagerService` | `packages/modules/StatsD/framework/java/android/app/StatsManager.java`、`packages/modules/StatsD/service/java/com/android/server/stats/StatsManagerService.java` | 管理特权客户端的配置、report、query、pull atom callback 注册和权限检查 | 配置是否注册、report/query 是否允许读取、statsd 重启后的注册回灌 |
| `StatsCompanionService` | `packages/modules/StatsD/service/java/com/android/server/stats/`，历史路径在 `frameworks/base/services/core/java/com/android/server/stats/` | 作为 statsd 的 system_server helper，处理 alarm、uid map、pulled atom、statsd ready 通知 | alarm、uid map、pull atom、系统服务侧状态 |
| `StatsLog` / `FrameworkStatsLog` | 由 proto 生成的日志 API | 平台代码写入 pushed atom | 某个系统事件发生的事实和字段 |
| `atoms.proto` | `frameworks/proto_logging/stats/atoms.proto` | 定义 atom ID、字段和 pushed / pulled 分类 | 字段口径、版本差异、模块归属 |
| `statsd_config.proto` | `packages/modules/StatsD/statsd/src/statsd_config.proto` | 定义 metric、matcher、predicate、alert 等配置 | 采集什么、按什么条件聚合、何时上报 |

配置、report、query 这条 Java API 路径不直接走 StatsCompanionService：`StatsManager` 调用 system_server 中的 `StatsManagerService`，后者检查 `DUMP` + `PACKAGE_USAGE_STATS`、`REGISTER_STATS_PULL_ATOM` 或 `READ_RESTRICTED_STATS` 等权限，再通过 `IStatsd` 与 native statsd 通信；statsd 重启后，`StatsCompanionService.statsdReady()` 会触发 `StatsManagerService.statsdReady(IStatsd)`，把已缓存的 puller、data fetch、active config、subscriber 和 restricted metric 回灌给 native 端。[已验证: AOSP android-17.0.0_r1, packages/modules/StatsD/service/java/com/android/server/stats/StatsManagerService.java; packages/modules/StatsD/service/java/com/android/server/stats/StatsCompanionService.java]

AOSP 的 `atoms.proto` 明确写到：`Atom` 消息定义 Android 系统可用的 raw stats log events，也就是 atom；`stats-log-api-gen` 在构建期生成 `android.util.StatsLog` 相关常量和方法；`Atom` 消息本身不直接内置进系统，Android 上的 statsd 会按 `atoms.proto` 和 `stats_log.proto` 描述的格式合成这些消息。[已验证: AOSP android-17.0.0_r1, frameworks/proto_logging/stats/atoms.proto]

这也解释了一个常见误判：statsd report 里的 ANR 或 LMK 事件不是“现场”。它只能证明某个 atom 按字段口径被记录过，不能替代 traces.txt、tombstone、Perfetto Trace 或 dumpsys 状态。

## Atom 模型：事件、拉取样本和 metric 配置

statsd 的输入是 atom，输出是 metric report。atom 负责描述平台事件或状态样本，metric 配置负责描述如何筛选、切分和聚合。

`atoms.proto` 把 atom 分成两类：

- pushed atom：由系统服务或 native 组件在事件发生时写入。例如 `ScheduledJobStateChanged`、`WakelockStateChanged`、`AppCrashOccurred`、`ANROccurred`、`LmkKillOccurred`、`AppStartOccurred` 都属于 pushed atom。事件发生时写入 stats log buffer，statsd 再按配置消费。
- pulled atom：statsd 按配置或命令向系统侧拉取当前状态。例如 `KernelWakelock`、`CpuTimePerUid`、`CpuTimePerUidFreq`、`ProcessMemoryState`、`SystemElapsedRealtime` 等位于 pulled 区间。AOSP 中 pulled atom 从 field 10000 开始。[已验证: AOSP android-17.0.0_r1, frameworks/proto_logging/stats/atoms.proto]

metric 配置定义在 `statsd_config.proto`。这一层不关心“系统怎么产生事件”，只关心“哪些 atom 算命中、怎么聚合、报告里保留哪些字段”。常用对象包括：

| 配置对象 | 作用 | 典型用途 |
| --- | --- | --- |
| `AtomMatcher` | 按 atom ID 和字段条件匹配事件 | 只收集某类 ANR、某个 UID 的 JobScheduler 状态 |
| `Predicate` | 用 start / stop atom 表示条件区间 | 统计前台期间 wakelock 持续时间 |
| `EventMetric` | 记录命中的事件 | 保留 ANR、LMK、启动事件明细 |
| `CountMetric` | 按 bucket 计数 | 统计某类事件每小时次数 |
| `DurationMetric` | 统计状态持续时间，支持 `SUM` 和 `MAX_SPARSE` | 统计 wakelock、前台服务、Job 运行时长 |
| `GaugeMetric` | 对 pulled atom 或触发事件做采样 | 周期性采集 CPU 时间、内存状态、电量相关样本 |
| `ValueMetric` / `KllMetric` | 对数值字段做聚合或分布估计 | 统计耗时、大小、数量等数值指标 |

`StatsdConfig` 把这些对象组合在同一个配置里：`event_metric`、`count_metric`、`value_metric`、`gauge_metric`、`duration_metric`、`kll_metric`、`atom_matcher`、`predicate`、`alert`、`subscription` 等字段都在这个 proto 中定义。[已验证: AOSP android-17.0.0_r1, packages/modules/StatsD/statsd/src/statsd_config.proto]

排障时要把 atom 和 metric 分开看。atom 是原始事实，metric 是采集口径。同一个 atom 可以被多个 metric 以不同维度聚合；同一个 report 中缺少某个 metric，也可能只是配置没有收集，并不代表系统没有产生过对应事件。

## 性能排障中的常见 atom 入口

statsd 在性能排障里最有价值的地方，是提供跨版本相对稳定的系统事件索引。它适合做“线索表”，再把线索交给 Perfetto、logcat、dumpsys 或问题专项工具验证。

| 场景 | 常见 atom / 字段入口 | 能回答的问题 | 不能替代的证据 |
| --- | --- | --- | --- |
| ANR | `ANROccurred`、`ANRLatencyReported` | 哪个 UID / 进程发生 ANR，reason 字段如何，ANR 处理各阶段耗时是否异常 | traces.txt、Perfetto 主线程和 Binder 时序、ActivityManager 日志 |
| 崩溃 | `AppCrashOccurred`、`AppDied` | 崩溃是否发生，进程和错误来源字段是什么 | Java / native crash 堆栈、tombstone、崩溃平台聚合 |
| LMK / 低内存 | `LmkKillOccurred`、`LowMemReported`、`ProcessMemoryState` | 哪个进程被杀、系统是否报告低内存、拉取到的内存状态样本 | lmkd 日志、`ApplicationExitInfo`、Perfetto memory counter，详见 10.x 与 23.x 相关章节 |
| JobScheduler | `ScheduledJobStateChanged`、`DeferredJobStatsReported`、`DeviceWideJobConstraintChanged` | Job 状态变化、约束变化、是否存在延迟执行迹象 | `dumpsys jobscheduler`、WorkManager 日志，详见 5.10 节 |
| 启动 | `AppStartOccurred`、`AppStartCanceled`、`AppStartFullyDrawn`、`AppStartMemoryStateCaptured` | 启动事件、fully drawn、启动期间内存快照 | Macrobenchmark、Perfetto app startup 切片，详见 21.x |
| 功耗 | `WakelockStateChanged`、`KernelWakelock`、`BatterySaverModeStateChanged`、`CpuTimePerUidFreq` | wakelock、CPU 时间、节电状态变化 | Batterystats、Battery Historian、Perfetto power rail，详见 25.x |
| 游戏与帧相关 | `GameModeChanged`、`GameModeConfigurationChanged`、`InputEventLatencyReported` | 游戏模式和输入延迟相关事件是否出现 | FrameTimeline、SurfaceFlinger、GPU counter，详见 22.x |
| UprobeStats / eBPF | UprobeStats 模块相关扩展 atom、Perfetto statsd atom proto | 动态探针产出的系统侧事件是否进入统一指标通道 | eBPF 程序、Perfetto trace、UprobeStats 模块日志，详见 14.10 节 |

[已验证: AOSP android-17.0.0_r1, frameworks/proto_logging/stats/atoms.proto]

表里的字段不应该直接写死到长期看板里。`atoms.proto` 会随平台版本演进，同名 atom 的字段语义、可见范围、模块归属都有变动风险。长期看板要记录 Android 版本、构建指纹、atom ID、字段版本，并保留配置文件的版本号。

## adb / cmd stats 本地调试流程

本地验证 statsd 采集，通常走四步：准备二进制 StatsdConfig、下发配置、触发场景、拉取 report。`cmd stats` 的 shell 命令入口在 `StatsService::handleShellCommand()` 中实现，只允许 root 或 shell UID 调用。[已验证: AOSP android-17.0.0_r1, packages/modules/StatsD/statsd/src/StatsService.cpp]

下面这组命令展示最小调试路径。这里假设 `config.pb` 已经是 wire-encoded `StatsdConfig`，`123456` 是数字配置 ID。AOSP 源码要求 `config update` 读取 stdin，并把 `NAME` 解析成 int64 配置 ID。

```shell
# 下发或更新配置；省略 UID 时使用调用方 UID
adb shell cmd stats config update 123456 < config.pb

# 触发待观察场景，例如启动 App、制造测试 Job、执行压测脚本
adb shell am start -n com.example/.MainActivity

# 拉取二进制 report；调试时常保留数据并包含当前 bucket
adb shell cmd stats dump-report 123456 --keep_data --include_current_bucket --proto > report.pb

# 清理该配置
adb shell cmd stats config remove 123456
```

这套流程里有三个容易踩的点：

- `config.pb` 必须是二进制 proto，不是文本 proto。命令帮助里也写明配置通过 stdin 传入 wire-encoded protobuf。
- 省略 UID 时使用当前调用方 UID；要读取或写入其他 UID 的配置，AOSP 代码只允许 eng / userdebug 构建，或调用方访问自身 UID。量产 user 构建不要把跨 UID 调试当成可用能力。
- `dump-report` 默认会清除已导出的数据；调试时加 `--keep_data`，否则下一次拉取可能拿不到同一批样本。

`cmd stats` 还提供一些辅助命令：

```shell
# 查看 UID 到包名、版本的映射
adb shell cmd stats print-uid-map

# 拉取某个 pulled atom 的当前输出，适合验证 puller 是否工作
adb shell cmd stats pull-source 10009

# 打印 statsd 自身统计，必要时输出 proto
adb shell cmd stats print-stats
adb shell cmd stats print-stats --proto

# 打开或关闭 stats log 打印；源码帮助注明需要 root 权限
adb shell cmd stats print-logs
adb shell cmd stats print-logs 0
```

这些命令适合做本地验证，不适合直接塞进量产自动化。量产环境的 statsd 配置、隐私约束、上报路径通常由系统镜像、GMS、厂商平台或内部分发机制控制，普通 App 不能随意下发平台级配置。

## 与 Perfetto、logcat、dumpsys 的交叉验证

statsd 和 Perfetto 经常出现在同一次排障里，但两者的证据类型不同。statsd 是聚合后的指标和事件报告，Perfetto 是时间轴。排障顺序可以按下面的方式组织：

1. 用 statsd 确认事件是否发生：查 report 中的 atom、UID、包名、reason、bucket、次数和状态持续时间。
2. 用 Perfetto 还原事件附近的时序：查主线程、RenderThread、Binder、调度、memory counter、FrameTimeline。Perfetto 采集基础设施详见 13.9 节，SQL 分析详见 13.10 节。
3. 用 logcat 和 dumpsys 补系统状态：ActivityManager、JobScheduler、PowerManager、lmkd、SurfaceFlinger 等日志或 dump 能解释 statsd 字段背后的状态。
4. 用专项工具复核指标口径：功耗看 Batterystats / Battery Historian，内存看 heapprofd / meminfo，渲染看 FrameTimeline / SurfaceFlinger，APM 上报看 26.3 节。

一个 ANR 例子可以说明分工：`ANROccurred` 能告诉你哪个进程、哪个组件、reason 字段和是否前台；Perfetto 能告诉你 ANR 前主线程是在 runnable、blocked 还是 Binder 等待；logcat 能还原 ActivityManager 的 ANR 判定路径；traces.txt 能给出线程栈。缺其中任何一类证据，结论都会偏窄。

LMK 也一样。`LmkKillOccurred` 能把“哪个进程被杀”落成事件，但不能单独说明为什么内存压力升高。还要查 lmkd 日志、PSI、进程 PSS、zRAM、adj、前后台状态，必要时再回到 10.x 和 23.x 的内存章节。

## 权限、版本与 OEM 边界

statsd 位于系统侧，权限边界比普通 App 埋点严格。AOSP `StatsService` 对 shell 命令入口检查 root / shell UID，跨 UID 配置和 report 操作又受 eng / userdebug 构建限制。StatsManagerService 侧 API 还会按入口检查 `android.permission.DUMP` + `PACKAGE_USAGE_STATS`、`REGISTER_STATS_PULL_ATOM`、`READ_RESTRICTED_STATS` 等权限。[已验证: AOSP android-17.0.0_r1, packages/modules/StatsD/statsd/src/StatsService.cpp; packages/modules/StatsD/service/java/com/android/server/stats/StatsManagerService.java]

版本边界也要写进排障手册：

- Android 11 及以上设备通过 `com.android.os.statsd` APEX 分发 StatsD 模块；Android 12 起源码结构迁移到 `packages/modules/StatsD`。
- `atoms.proto` 的 pushed atom 从 field 2 开始，pulled atom 从 field 10000 开始，但具体 atom 是否存在、字段是否相同，要按目标版本源码确认。
- 厂商可以增加 vendor atom 或在系统镜像中接入自己的采集配置。App 侧拿到的 report 口径不一定等同于 AOSP 默认口径。
- 隐私相关字段可能被 hash、截断或过滤。`StatsdConfig` 中有 `hash_strings_in_metric_report`、`allowed_log_source`、`uid_fields` 等配置项，报告字段要按配置解读。

适合写进团队手册的做法，是把 statsd 当成“系统事件索引”，不把它当成唯一真相。每个指标旁边都写清三件事：atom ID 和字段来自哪个 Android 版本，metric 配置怎么聚合，遇到异常后用哪类 Trace / 日志 / dump 复核。

## Tradefed / CTS 中的 statsd collector

AOSP Trade Federation 提供 `com.android.tradefed.util.statsd.ConfigUtil`，官方参考文档把它定义为“创建、交互和推送 statsd 配置文件的工具类”。它支持推送二进制 statsd 配置、按 event atom ID 生成事件型配置、删除配置，并返回新配置 ID。[已验证: 官方文档, source.android.com/reference/tradefed/com/android/tradefed/util/statsd/ConfigUtil]

这类能力适合做回归测试门禁：测试开始前下发配置，测试过程中执行固定场景，测试结束后拉取 report，再用脚本判断事件次数、耗时分布或状态持续时间是否超阈值。比起只看 logcat，statsd 的优势是字段口径固定、可跨设备聚合；代价是只能看配置里收集的 atom，不能临场补现场。

CTS 也依赖 statsd 验证平台 atom 和 StatsD 功能。AOSP Statsd 官方文档写明，Android Compatibility Test Suite 会验证 statsd 功能以及发布管理依赖的 atom。对 ROM 或系统模块团队来说，statsd 不是可有可无的观测工具，而是兼容性和发布安全的一部分。

## statsd report 与线上 APM 的边界

线上 APM 负责 App 内部事件：页面、用户操作、业务 trace、网络请求、缓存命中、实验分组。statsd 负责系统侧事件和状态样本：进程生命周期、ANR、LMK、Job、wakelock、CPU 时间、电量状态。两者的粒度和权限不同，不应该互相替代。

在 App 性能平台里，比较稳的接法是：APM 负责用户会话和业务维度，statsd 或系统指标负责平台事件维度。后端按时间、版本、设备、UID / 包名做关联，但保留原始来源字段。这样既能知道“用户这次页面卡了”，也能知道“同一窗口系统侧有没有 LMK、CPU 限频、输入延迟或 Job 约束变化”。

26.3 节已经讲过性能指标采集和上报口径。这里补一条工程约束：APM 能稳定采到的数据，不要绕到 statsd；只有系统侧才知道、App 无权限拿到、或者需要跨进程统一口径的事件，才值得引入 statsd。

## 自定义 Atom 与厂商扩展风险

自定义 atom 最大的问题不是“能不能写进去”，而是长期兼容。atom ID、字段编号、字段含义、隐私处理、模块归属都会影响报表的可比性。某个 OEM 在 Android 15 上增加的 vendor atom，到 Android 17 可能字段变了，甚至被新的平台 atom 替代。

长期看板要遵守四条规则：

- 固定配置版本：每次变更 `StatsdConfig` 都记录版本号、变更说明和灰度范围。
- 固定字段契约：看板字段绑定 atom ID + field number + Android 版本，不只绑定字段名。
- 固定验证样本：每个版本保留一份触发脚本和预期 report，发版前跑一轮 userdebug 设备验证。
- 固定降级策略：目标设备没有对应 atom、权限不足或 report 为空时，明确回退到 Perfetto、dumpsys、logcat 或 App 侧指标。

这样处理后，statsd 才能成为排障体系的一层稳定索引，而不是另一个口径不清的指标来源。

## 延伸阅读


### Android 17 StatsD 三层架构链路边界验证（StatsManagerService/StatsCompanionService/native daemon）
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-07-statsd-service-chain-validation.md
- 类型：DeepResearch 调研结果
- 摘要：StatsD 系统三层架构源码验证：Java 层 StatsManagerService 负责权限和配置/report/query 入口，StatsCompanionService 通过 Binder 处理 statsd ready、alarm、uid map 和 pulled atom 辅助能力，native statsd 通过 StatsSocketListener / StatsSocketListenerIoUring 监听 stats log socket 事件。StatsManagerService 对 addConfig/getReports、pull atom callback、query/restricted metrics 分别检查 DUMP + PACKAGE_USAGE_STATS、REGISTER_STATS_PULL_ATOM、READ_RESTRICTED_STATS；DeviceConfig.NAMESPACE_STATSD_JAVA 在 Android 17 源码中存在，但不作为 Android 17 新增结论。
- 注入时间：2026-06-08
- 价值：验证 StatsD 三层架构的源码实现和权限边界，补齐 ch14.17 缺少的服务链路验证

## 延伸阅读


### Android 16 StatsD 缓存与配置重注册链路（statsdReady 全量回灌机制）
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-08-android-statsd-config-cache-reregister.md
- 类型：DeepResearch 调研结果
- 摘要：StatsManagerService 维护五类 ArrayMap 订阅缓存（puller/dataFetch/activeConfig/broadcastSubscriber/restrictedMetrics），native statsd 重启时通过 statsdReady() 信号触发 sayHiToStatsd() 全量重注册。客户端侧缓存是 authoritative state，native 端是 mirror，registerAll* 方法采用锁内浅拷贝+锁外 binder 调用模式避免 IPC 死锁。
- 注入时间：2026-06-08
- 价值：补充 statsd 缓存恢复与配置持久化机制的源码级细节，是理解 statsd 服务可用性设计的关键材料



## 参考资料

### Android 17 有什么需要适配的？2026 Android 禁止侧载又是什么？
- 来源：https://juejin.cn/post/7610233341305389099
- 类型：技术文章
- 摘要：Android 17（API 37）适配清单与 2026 开发者强制认证政策的全维度解读。非 target 变更包括 usesCleartextTraffic 弃用预警（迁移到 Network Security Config）、旋转后键盘状态不再自动恢复、后台音频收紧需 WIU 能力的前台服务。targetSdk=37 关键变更：MessageQueue 升级为无锁 DeliQueue（Treiber 栈+最小堆）、BAL 限制扩展到 IntentSender、新增 USE_LOOPBACK_INTERFACE 安装时权限、Certificate Transparency 默认启用、Safer DCL 扩展到 native（System.load 加载的库必须只读）、大屏强制自适应。2026 年 9 月起部分地区应用必须经开发者认证才能安装。
- **推荐映射章节**：ch13
- **内容类型**：技术文章
- **相关标签**：#Android新版本 #适配
- 入库时间：2026-06-26
- 评分：16/20

### Android 要变天：桌面端这次真的来了！
- 来源：https://juejin.cn/post/7622696665740558386
- 类型：技术文章
- 摘要：Google 正式发布 Desktop Experience 设计指南和 Android Design Gallery，把桌面端体验列为一等公民。核心定义：当 App 处于桌面模式（键盘/鼠标/外接显示器）即视为桌面体验。三个核心原则：多任务是核心（必须适配各种窗口尺寸）、鼠标精度远高于手指（可提高信息密度）、光标交互是全新战场（hover 状态、文本/移动/手型光标、自定义图标）。开发者行动优先级：跑 Adaptive Design Lab、用模拟器测自由窗口模式、研究 Adaptive App Quality Guidelines、补键盘快捷键/鼠标 hover/右键菜单。Android 从口袋走向桌面不是渐进改良，而是平台战略转变。
- **推荐映射章节**：ch13
- **内容类型**：技术文章
- **相关标签**：#Android新版本 #桌面模式 #多窗口
- 入库时间：2026-06-26
- 评分：14/20

### Android 17 来了！新特性介绍与适配建议
- 来源：https://juejin.cn/post/7612545160434188297
- 类型：技术文章
- 摘要：Android 17 Beta 2 适配全指南（拭心版）。最关键是大屏自适应强制化：targetSdk 37 后，sw>600dp 设备上 screenOrientation/resizeableActivity/minAspectRatio/maxAspectRatio 等属性全部失效（游戏类除外），2027 年 8 月 Google Play 强制要求。相机预览变形方案：CameraX PreviewView 首选、CameraViewfinder 兼容老项目、Camera2 手动计算需用 window metrics 而非屏幕尺寸。Bubbles 浮窗模式（长按桌面图标）、EyeDropper 颜色拾取（不需截屏权限）、联系人选择器（替代 READ_CONTACTS）、触控板指针捕获优化、跨设备 Handoff API、UWB DL-TDOA、ACCESS_LOCAL_NETWORK 运行时权限、OTP 短信读取延迟 3 小时、NPU 访问需声明 FEATURE_NEURAL_PROCESSING_UNIT、ICU 78 + Unicode 17。
- **推荐映射章节**：ch13
- **内容类型**：技术文章
- **相关标签**：#Android新版本 #API37
- 入库时间：2026-06-26
- 评分：14/20
