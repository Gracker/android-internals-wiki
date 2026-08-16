---
title: statsd 与系统级指标采集
chapter: 14.12
section: 14.12
status: finalized
applicable_versions: Android 11 (API 30) - Android 17 (API 37)
last_verified: 2026-08-13
last_verified_against: AOSP android-17.0.0_r1 / android17-6.18-2026-06_r6 / source.android.com Statsd 文档更新于 2026-07-13
confidence: medium
sources: 
  - type: official
    path: "https://source.android.com/docs/core/ota/modular-system/statsd"
  - type: aosp
    path: "packages/modules/StatsD/statsd/src/StatsService.cpp"
  - type: aosp
    path: "packages/modules/StatsD/statsd/src/main.cpp"
  - type: aosp
    path: "packages/modules/StatsD/statsd/src/statsd_config.proto"
  - type: aosp
    path: "packages/modules/StatsD/lib/libstatssocket/statsd_writer.cpp"
  - type: aosp
    path: "packages/modules/StatsD/framework/java/android/app/StatsManager.java"
  - type: aosp
    path: "packages/modules/StatsD/service/java/com/android/server/stats/StatsManagerService.java"
  - type: aosp
    path: "packages/modules/StatsD/service/java/com/android/server/stats/StatsCompanionService.java"
  - type: aosp
    path: "frameworks/proto_logging/stats/atoms.proto"
  - type: kernel
    path: "android17-6.18-2026-06_r6/io_uring/"
  - type: official
    path: "https://source.android.com/reference/tradefed/com/android/tradefed/util/statsd/ConfigUtil"
  - type: official
    path: "https://developer.android.com/tools/adb"
tags: [statsd, observability, perfetto, tools]
related_chapters: ["13.8", "13.9", "14.23", "15.3", "26.3"]
task2b_state: fixed
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
---

# 14.12 statsd 与系统级指标采集

Android 平台的系统级指标并不只来自 Perfetto Trace。平台会把 ANR（Application Not Responding，应用无响应）、LMK（low memory kill，低内存杀进程）、JobScheduler 状态、启动、功耗和网络统计等信号写成 atom；atom 是由 Protocol Buffers（protobuf）schema（数据结构定义）描述的结构化事件或状态记录。statsd 再按配置把 atom 聚合成 metric（指标）报告。

本章说明 statsd 在系统观测中的位置、atom 和 metric 的建模方式、本地调试流程，以及它和 Perfetto、logcat、dumpsys（输出系统服务当前状态的命令）的分工。线上出现系统事件而 Trace 缺少完整时序时，应先判断需要补充哪类信号。

## statsd 适合回答什么问题

statsd 是 Android 平台侧的指标守护进程。AOSP 文档把 Statsd 模块定义为两部分：后台运行的 native（C++）服务 statsd，以及运行在 `system_server`（Android 核心 Java 进程）中的 Java 服务 `StatsCompanionService`。该模块以 APEX（可独立更新的系统组件容器）形式发布，模块名为 `com.android.os.statsd`，Android 11 及以上设备可用；Android 12 起，StatsD 相关源码从 `frameworks/base/cmds/StatsD`、`frameworks/base/apex/StatsD` 和 `system/core/libstats` 迁移到 `packages/modules/StatsD`。

statsd 把系统事件和状态样本按配置聚合成 metric 报告，不录制逐线程、逐调度事件的完整时序。Perfetto 回答“这段时间内线程和内核事件按什么顺序发生”，statsd 回答“某类事件是否发生、发生多少次、按 UID、包名或状态切分后的分布如何”。UID 是 Android 用来标识应用身份的数字，同一应用的多个进程通常共享 UID。

几个组件的分工如下：

| 组件 | 位置 | 职责 | 排障时提供的信息 |
| --- | --- | --- | --- |
| `statsd` | `packages/modules/StatsD/statsd/src/` | 接收 atom、维护配置、聚合 metric、生成报告 | 事件计数、状态持续时间、拉取样本、异常触发 |
| `StatsManager` / `StatsManagerService` | `packages/modules/StatsD/framework/java/android/app/StatsManager.java`、`packages/modules/StatsD/service/java/com/android/server/stats/StatsManagerService.java` | 管理特权客户端的配置、报告、query、pull atom callback 注册和权限检查 | 配置是否注册、报告/query 是否允许读取、statsd 重启后是否重新注册客户端回调 |
| `StatsCompanionService` | `packages/modules/StatsD/service/java/com/android/server/stats/`，历史路径在 `frameworks/base/services/core/java/com/android/server/stats/` | 作为 `system_server` 内的辅助服务，处理 alarm（定时触发）、UID 映射、pulled atom 和 statsd ready 通知 | 定时任务、UID 映射、pull atom、系统服务侧状态 |
| `StatsLog` / `FrameworkStatsLog` | 由 proto 生成的日志 API | 平台代码写入 pushed atom（事件发生时主动发送的 atom） | 某个系统事件发生的事实和字段 |
| `atoms.proto` | `frameworks/proto_logging/stats/atoms.proto` | 用 Protocol Buffers schema 定义 atom ID、字段和 pushed / pulled 分类 | 字段含义、版本差异、模块归属 |
| `statsd_config.proto` | `packages/modules/StatsD/statsd/src/statsd_config.proto` | 定义 metric、matcher（匹配规则）、predicate（条件区间）、alert 等配置 | 采集什么、按什么条件聚合、何时上报 |

配置、report、query 这条 Java API 路径不直接经过 `StatsCompanionService`：`StatsManager` 调用 `system_server` 中的 `StatsManagerService`，后者按入口检查 `DUMP` + `PACKAGE_USAGE_STATS`、`REGISTER_STATS_PULL_ATOM` 或 `READ_RESTRICTED_STATS` 等特权权限，再通过 `IStatsd` 的 Binder（Android 跨进程调用机制）接口与 native statsd 通信。

statsd 重启后，`StatsCompanionService.statsdReady()` 会调用 `StatsManagerService.statsdReady(IStatsd)`。`sayHiToStatsd()` 随后向新进程重新注册五类客户端入口：pull callback、data-fetch operation、active-config-changed operation、broadcast subscriber、restricted-metrics-changed operation；这些 operation 和 subscriber 通过 `PendingIntent` 通知客户端。源码先在锁保护下复制注册列表，再释放锁执行 Binder 调用，避免跨进程调用长时间占锁。`registerAllPullers()` 完成后还调用 `allPullersFromBootRegistered()`；puller 是向 statsd 提供 pulled atom 的数据源回调。这里没有缓存或重放 `StatsdConfig` 内容，不能把“客户端注册恢复”写成“配置由 StatsManagerService 持久化”。

pushed atom 的实际写入路径也不经过 `StatsCompanionService`。生成的 `StatsLog` API 最终进入 socket 写入库 `libstatssocket`；Android 17 的 `statsd_writer.cpp` 创建 non-blocking Unix datagram socket（不会等待缓冲区腾空的 Unix 数据报套接字），连接 `/dev/socket/statsdw`，再用 `writev()` 一次写入多个内存片段。statsd 过载时，发送端可能收到 `EAGAIN`（暂时无法写入）；源码明确说明写入可能丢失但不会阻塞，并维护 drop 计数供后续上报。

Android 17 的 native `main.cpp` 新增 API 37 门槛的 io_uring listener 分支。`io_uring` 是 Linux 的异步 I/O 接口；feature flag（运行时功能开关）开启且 `IOUringSocketHandler::IsIouringSupported()` 检测通过时，statsd 使用 `StatsSocketListenerIoUring` 监听 socket，其余情况使用 `StatsSocketListener`。两条路径都先把事件放入上限为 50000 条的 `LogEventQueue`，待 `StatsService::Startup()` 后消费。对应的 Android 17 common kernel tag `android17-6.18-2026-06_r6` 包含 `io_uring/` 实现，但设备是否走该分支仍由平台 flag、运行时检测和产品配置共同决定。

AOSP 的 `atoms.proto` 说明 `Atom` 定义 raw stats log events，也就是尚未聚合的原始统计事件；`stats-log-api-gen` 在构建期生成日志常量和方法。顶层 `Atom` 消息用作 schema 容器，不直接编入系统；statsd 按 `atoms.proto` 与 `stats_log.proto` 的格式生成 protobuf 数据。

因此，报告中的 ANR 或 LMK 条目只证明对应 atom 到达 statsd、命中配置并进入报告。它不能替代 ANR trace、tombstone、Perfetto trace 或 dumpsys 现场；报告中没有条目也不能单独证明事件未发生。

## Atom 模型：事件、拉取样本和 metric 配置

statsd 的输入是 atom，输出是 metric 报告。atom 负责描述平台事件或状态样本，metric 配置负责描述如何筛选、切分和聚合。

`atoms.proto` 把 atom 分成两类：

- pushed atom：由系统服务或 native 组件在事件发生时写入。例如 `ScheduledJobStateChanged`、`WakelockStateChanged`、`AppCrashOccurred`、`ANROccurred`、`LmkKillOccurred`、`AppStartOccurred` 都属于 pushed atom。事件通过 stats log API 和专用 socket 送到 statsd，再由 matcher、predicate 与 metric 配置决定是否保留和如何聚合。
- pulled atom：statsd 按配置或命令向系统数据源请求当前状态。例如 `KernelWakelock`、`CpuTimePerUid`、`CpuTimePerUidFreq`、`ProcessMemoryState`、`SystemElapsedRealtime` 等位于 pulled 区间。AOSP 中 pulled atom 的 field number（同时也是 atom ID）从 10000 开始。

metric 配置定义在 `statsd_config.proto`。这一层不关心“系统怎么产生事件”，只关心“哪些 atom 算命中、怎么聚合、报告里保留哪些字段”。常用对象包括：

| 配置对象 | 作用 | 典型用途 |
| --- | --- | --- |
| `AtomMatcher` | 按 atom ID 和字段条件匹配事件 | 只收集某类 ANR、某个 UID 的 JobScheduler 状态 |
| `Predicate` | 用 start / stop atom 表示条件区间 | 统计前台期间 wakelock 持续时间 |
| `EventMetric` | 记录命中的事件 | 保留 ANR、LMK、启动事件明细 |
| `CountMetric` | 按 bucket（聚合时间窗口）计数 | 统计某类事件每小时次数 |
| `DurationMetric` | 统计状态持续时间；`SUM` 累加区间，`MAX_SPARSE` 保留对应维度在 bucket 内已结束区间的最大持续时长 | 统计 wakelock、前台服务、Job 运行时长 |
| `GaugeMetric` | 对 pulled atom 或触发事件做采样 | 周期性采集 CPU 时间、内存状态、电量相关样本 |
| `ValueMetric` / `KllMetric` | 对数值字段做聚合；`KllMetric` 用 KLL quantile sketch（紧凑的分位数摘要）估计分布 | 统计耗时、大小、数量等数值指标 |

`StatsdConfig` 把这些对象组合在同一个 protobuf 配置里：`event_metric`、`count_metric`、`value_metric`、`gauge_metric`、`duration_metric`、`kll_metric`、`atom_matcher`、`predicate`、`alert`、`subscription` 等字段都在这个 proto 中定义。

排障时要把 atom 和 metric 分开看。atom 描述原始事件或状态样本，metric 描述筛选、切分和聚合规则。同一个 atom 可以被多个 metric 以不同维度聚合。报告缺少条目时，应依次检查 `allowed_log_source`（允许写入该配置的来源）、matcher/predicate、metric activation（控制 metric 何时启用）、当前未结束的 bucket 是否被包含、报告是否已被导出并清除、pull 是否超时，以及 socket 或队列是否发生丢失。

## 性能排障中的常见 atom 入口

statsd 在性能排障里最有价值的地方，是提供跨版本相对稳定的系统事件索引。它适合做“线索表”，再把线索交给 Perfetto、logcat、dumpsys 或问题专项工具验证。

| 场景 | 常见 atom / 字段入口 | 能回答的问题 | 不能替代的证据 |
| --- | --- | --- | --- |
| ANR | `ANROccurred`、`ANRLatencyReported` | 哪个 UID / 进程发生 ANR，reason 字段如何，ANR 处理各阶段耗时是否异常 | traces.txt、Perfetto 主线程和 Binder 时序、ActivityManager 日志 |
| 崩溃 | `AppCrashOccurred`、`AppDied` | 崩溃是否发生，进程和错误来源字段是什么 | Java / native crash 堆栈、tombstone（系统生成的 native 崩溃转储）、崩溃平台聚合 |
| LMK / 低内存 | `LmkKillOccurred`、`LowMemReported`、`ProcessMemoryState` | 哪个进程被杀、系统是否报告低内存、拉取到的内存状态样本 | lmkd 日志、`ApplicationExitInfo`、Perfetto memory counter，详见 10.x 与 23.x 相关章节 |
| JobScheduler | `ScheduledJobStateChanged`、`DeferredJobStatsReported`、`DeviceWideJobConstraintChanged` | Job 状态变化、约束变化、是否存在延迟执行迹象 | `dumpsys jobscheduler`、WorkManager 日志，详见 5.10 节 |
| 启动 | `AppStartOccurred`、`AppStartCanceled`、`AppStartFullyDrawn`、`AppStartMemoryStateCaptured` | 启动事件、fully drawn（界面已完整绘制）、启动期间内存快照 | Macrobenchmark、Perfetto app startup 切片，详见 21.x |
| 功耗 | `WakelockStateChanged`、`KernelWakelock`、`BatterySaverModeStateChanged`、`CpuTimePerUidFreq` | wakelock（阻止设备休眠的锁）、CPU 时间、节电状态变化 | Batterystats、Battery Historian、Perfetto power rail（电源轨采样），详见 25.x |
| 游戏与帧相关 | `GameModeChanged`、`GameModeConfigurationChanged`、`InputEventLatencyReported` | 游戏模式和输入延迟相关事件是否出现 | FrameTimeline、SurfaceFlinger、GPU counter，详见 22.x |
| UprobeStats / eBPF | `UprobeStatsInternalError`、`UprobeStatsInvocation`、`UprobeStatsBpfAttached`、`UprobeStatsBpfMapPolled` | 用户态探针 uprobe 是否挂载、eBPF（内核中的受限程序）是否运行、eBPF map（内核与用户态共享的数据结构）是否被读取，或是否出现内部错误 | eBPF 程序、Perfetto trace、UprobeStats 模块日志，详见 14.23 节 |

表里的字段不应该直接写死到长期看板里。`atoms.proto` 会随平台版本演进，同名 atom 的字段语义、可见范围、模块归属都有变动风险。长期看板要记录 Android 版本、构建指纹、atom ID、字段版本，并保留配置文件的版本号。

## adb / cmd stats 本地调试流程

本地验证 statsd 采集，通常走四步：准备二进制 StatsdConfig、下发配置、触发场景、拉取报告。`cmd stats` 的 shell 命令入口在 `StatsService::handleShellCommand()` 中实现，只允许 root 或 shell UID 调用。

下面是一份只收集 `AppStartOccurred`（atom ID 48）的最小 textproto，也就是便于人阅读和编辑的 protobuf 文本格式。matcher ID 与 metric ID 只需在该配置内唯一；这里把 config 内的 `id` 和命令行配置 ID 都设为 `123456`，便于复查。

```protobuf
id: 123456
allowed_log_source: "AID_SYSTEM"

atom_matcher {
  id: 1001
  simple_atom_matcher {
    atom_id: 48
  }
}

event_metric {
  id: 2001
  what: 1001
}
```

在 AOSP 根目录可用与该 tag 匹配的 `statsd_config.proto` 编码；下面假设 `protoc` 已在 `PATH` 中。

```bash
protoc -I packages/modules/StatsD/statsd/src \
  --encode=android.os.statsd.StatsdConfig \
  statsd_config.proto < config.textproto > config.pb
```

`allowed_log_source` 限制哪些 UID 可以写入这份配置；`AID_SYSTEM` 对应写入 `AppStartOccurred` 的 system 侧。换 atom 时必须同时核对 atom ID、实际 log source 和字段含义，不能只替换数字。

下面这组命令展示最小调试路径。这里假设 `config.pb` 已经是 wire-encoded `StatsdConfig`（按 protobuf wire format 编码的二进制数据），`123456` 是数字配置 ID。AOSP 源码要求 `config update` 从 stdin（标准输入）读取配置，并把 `NAME` 解析成 int64 配置 ID。

```shell
# 下发或更新配置；省略 UID 时使用调用方 UID
adb shell cmd stats config update 123456 < config.pb

# 触发待观察场景，例如启动 App、制造测试 Job、执行压测脚本
adb shell am start -n com.example/.MainActivity

# 拉取二进制报告；调试时常保留数据并包含当前 bucket
adb shell cmd stats dump-report 123456 --keep_data --include_current_bucket --proto > report.pb

# 清理该配置
adb shell cmd stats config remove 123456
```

这套流程里有四个容易踩的点：

- `config.pb` 必须是二进制 proto，不是文本 proto。命令帮助里也写明配置通过 stdin 传入 wire-encoded protobuf。
- 省略 UID 时使用当前调用方 UID；显式读取或写入其他 UID 的配置只对 eng / userdebug（工程或调试系统构建）开放。量产 user 构建不要把跨 UID 调试当成可用能力。
- `dump-report` 默认会清除已导出的数据；调试时加 `--keep_data`，否则下一次拉取可能拿不到同一批样本。
- Android 17 的参数解析从命令尾部依次识别 `--proto`、`--include_current_bucket`、`--keep_data`，按示例顺序书写最稳妥。`config remove` 同时省略 UID 与 NAME 会删除内存和磁盘中的全部配置，清理脚本必须传入明确的配置 ID。

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

`10009` 在 Android 17 的 `atoms.proto` 中对应 `CpuTimePerUid`。`pull-source` 只验证当前 puller（提供 pulled atom 的数据源）能否返回结果，不会替你创建 metric 或证明周期采集成功；`print-logs` 需要 root 权限。

这些命令适合做本地验证，不适合直接放进量产自动化。量产环境的 statsd 配置、隐私约束、上报路径通常由系统镜像、GMS（Google Mobile Services）、厂商平台或内部分发机制控制，普通 App 不能下发平台级配置。

## 与 Perfetto、logcat、dumpsys 的交叉验证

statsd 和 Perfetto 经常出现在同一次排障里，但两者的证据类型不同。statsd 是聚合后的指标和事件报告，Perfetto 是时间轴。排障顺序可以按下面的方式组织：

1. 用 statsd 确认事件是否发生：查报告中的 atom、UID、包名、reason、bucket、次数和状态持续时间。
2. 用 Perfetto 还原事件附近的时序：查主线程、`RenderThread`（渲染线程）、Binder、调度、memory counter（内存数值轨道）、FrameTimeline（逐帧生命周期轨道）。Perfetto 采集基础设施详见 13.8 节，SQL 分析详见 13.9 节。
3. 用 logcat 和 dumpsys 补系统状态：ActivityManager、JobScheduler、PowerManager、lmkd、SurfaceFlinger 等日志或 dump 能解释 statsd 字段背后的状态。
4. 用专项工具复核指标定义：功耗看 Batterystats / Battery Historian，内存看 heapprofd / meminfo，渲染看 FrameTimeline / SurfaceFlinger，APM（Application Performance Monitoring，应用性能监控）上报看 26.3 节。

一个 ANR 例子可以说明分工：`ANROccurred` 能告诉你哪个进程、哪个组件、reason 字段和是否前台；Perfetto 能告诉你 ANR 前主线程处于 runnable（可运行）、blocked（阻塞）还是 Binder 等待；logcat 能还原 ActivityManager 的 ANR 判定路径；`traces.txt` 是记录各线程调用栈的 ANR 现场文件。缺其中任何一类证据，结论都会偏窄。

LMK 也一样。`LmkKillOccurred` 能记录“哪个进程被杀”，但不能单独说明为什么内存压力升高。还要查 `lmkd`（low memory killer daemon，低内存杀进程守护进程）日志、PSI（Pressure Stall Information，资源压力造成的停顿时间）、进程 PSS（按共享比例分摊后的内存占用）、zRAM（以内存压缩设备承载的交换空间）、adj（进程被回收的优先级分值）和前后台状态，必要时再回到 10.x 和 23.x 的内存章节。

## 权限、版本与 OEM 边界

statsd 位于系统侧，权限边界比普通 App 埋点严格。AOSP `StatsService` 对 shell 命令入口检查 root / shell UID，跨 UID 配置和报告操作又受 eng / userdebug 构建限制。`StatsManager` 是 `@SystemApi`（供系统组件和获授权应用使用的 API）；`addConfig()`、`removeConfig()`、`getReports()` 要求 `DUMP` + `PACKAGE_USAGE_STATS`，服务端还检查 usage-stats AppOp（权限之外的运行时操作授权）；`setPullAtomCallback()` 要求 `REGISTER_STATS_PULL_ATOM`；`query()` 与 restricted-metrics operation 要求 `READ_RESTRICTED_STATS`。

版本边界也要写进排障手册：

- Android 11 及以上设备通过 `com.android.os.statsd` APEX 分发 StatsD 模块；Android 12 起源码结构迁移到 `packages/modules/StatsD`。
- `atoms.proto` 的 pushed atom 从 field 2 开始，pulled atom 从 field 10000 开始，但具体 atom 是否存在、字段是否相同，要按目标版本源码确认。
- 官方模块文档注明 Statsd APEX 不支持产品侧定制。atom 命名空间另有扩展约定：field 100000–199999 留给 non-AOSP/OEM（设备厂商），300000–349999 用于 pushed generic vendor atom，350000–399999 用于 pulled generic vendor atom。厂商应使用规定的扩展路径，不能据此修改或替换 `com.android.os.statsd` 模块。
- 隐私相关字段可能被 hash（转换为摘要值）、截断或过滤。`StatsdConfig` 中有 `hash_strings_in_metric_report`、`allowed_log_source`、`uid_fields` 等配置项，报告字段要按配置解读。

团队手册可把 statsd 定位为“系统事件索引”。每个指标旁边写清三件事：atom ID 和字段来自哪个 Android 版本，metric 配置如何聚合，遇到异常后用哪类 trace、日志或 dump 复核。

## Tradefed / CTS 中的 statsd collector

AOSP Trade Federation（Android 测试执行框架）提供 `com.android.tradefed.util.statsd.ConfigUtil`，官方参考文档把它定义为“创建、交互和推送 statsd 配置文件的工具类”。它支持推送二进制 statsd 配置、按 event atom ID 生成事件型配置、删除配置，并返回新配置 ID。

这类能力适合做回归测试的发布判定：测试开始前下发配置，测试过程中执行固定场景，测试结束后拉取报告，再用脚本判断事件次数、耗时分布或状态持续时间是否超阈值。在相同 Android 版本和配置内，statsd 的字段含义明确，便于跨设备聚合；报告只包含配置选中的 atom，遗漏的现场无法在测试结束后补录。

CTS（Compatibility Test Suite，兼容性测试套件）也依赖 statsd 验证平台 atom 和 StatsD 功能。AOSP Statsd 官方文档写明，CTS 会验证 statsd 功能以及发布管理依赖的 atom。ROM 或系统模块团队需要把这些 atom 的兼容性纳入发布验证。

## statsd 报告与线上 APM 的边界

线上 APM 负责 App 内部事件：页面、用户操作、业务 trace、网络请求、缓存命中、实验分组。statsd 负责系统侧事件和状态样本：进程生命周期、ANR、LMK、Job、wakelock、CPU 时间、电量状态。两者的粒度和权限不同，不应该互相替代。

在 App 性能平台里，较清晰的分工是：APM 负责用户会话和业务维度，statsd 或系统指标负责平台事件维度。后端按时间、版本、设备、UID / 包名做关联，同时保留原始来源字段。这样既能知道“用户这次页面卡了”，也能知道“同一窗口系统侧有没有 LMK、CPU 限频、输入延迟或 Job 约束变化”。

26.3 节已经讲过性能指标定义和上报规则。这里补一条工程约束：APM 能稳定采到的数据不必改由 statsd 采集；只有系统侧才知道、App 无权限拿到、或者需要跨进程统一定义的事件，才值得引入 statsd。

## 自定义 Atom 与厂商扩展风险

厂商 atom 的长期兼容取决于 atom ID、字段编号、字段含义、隐私处理和模块归属。某个 OEM 在 Android 15 上增加的 vendor atom（厂商扩展 atom），到 Android 17 可能改变字段，也可能由新的平台 atom 取代。

长期看板要遵守四条规则：

- 固定配置版本：每次变更 `StatsdConfig` 都记录版本号、变更说明和逐步放量范围。
- 固定字段约定：看板字段绑定 atom ID + field number + Android 版本，不只绑定字段名。
- 固定验证样本：每个版本保留一份触发脚本和预期报告，发版前跑一轮 userdebug 设备验证。
- 固定降级策略：目标设备没有对应 atom、权限不足或报告为空时，明确回退到 Perfetto、dumpsys、logcat 或 App 侧指标。

做到这四点后，statsd 才适合作为长期排障索引；缺少字段契约与版本记录的报告不宜直接跨版本比较。

## 参考资料

- [AOSP Statsd 模块说明](https://source.android.com/docs/core/ota/modular-system/statsd)
- [Android 17 `statsd/src/main.cpp`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/statsd/src/main.cpp)
- [Android 17 `StatsService.cpp`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/statsd/src/StatsService.cpp)
- [Android 17 `statsd_config.proto`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/statsd/src/statsd_config.proto)
- [Android 17 `statsd_writer.cpp`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/lib/libstatssocket/statsd_writer.cpp)
- [Android 17 `StatsManager.java`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/framework/java/android/app/StatsManager.java)
- [Android 17 `StatsManagerService.java`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/service/java/com/android/server/stats/StatsManagerService.java)
- [Android 17 `StatsCompanionService.java`](https://android.googlesource.com/platform/packages/modules/StatsD/+/refs/tags/android-17.0.0_r1/service/java/com/android/server/stats/StatsCompanionService.java)
- [Android 17 `atoms.proto`](https://android.googlesource.com/platform/frameworks/proto_logging/+/refs/tags/android-17.0.0_r1/stats/atoms.proto)
- [Android 17 common kernel `io_uring/`, `android17-6.18-2026-06_r6`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/io_uring/)
- [Tradefed `ConfigUtil`](https://source.android.com/reference/tradefed/com/android/tradefed/util/statsd/ConfigUtil)
