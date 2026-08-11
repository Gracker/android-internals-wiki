---
title: "Android 17 MemoryLimiter：memcg 限制与超限诊断"
chapter: "4.13"
status: ready-for-review
drafted_date: "2026-07-02"
applicable_versions: "Android 17 (API 37)"
last_verified: "2026-08-07"
last_verified_against: "AOSP android-17.0.0_r1 / android17-6.18-2026-06_r6"
last_deep_review_at: "2026-08-07T20:36:02+08:00"
last_deep_review_run_id: "20260807-203506-deep-review-44dab4a0"
task6_state: deep-reviewed
task9_state: pending-final-audit
pipeline_stage: deep-review
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java (1291 lines)"
  - type: aosp
    path: "frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp (1276 lines)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryUsageStats.java (108 lines)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryStatUtil.java (148 lines)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/xsd/memory-limiter-config/memory-limiter-config.xsd"
  - type: kernel-doc
    path: "kernel.org Documentation/admin-guide/cgroup-v2.rst"
tags: [MemoryLimiter, memory, cgroup-v2, memcg, system-architecture, Android-17]
related_chapters: ["4.4", "4.5", "4.11", "4.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-02"
gap_source: "章节深挖"
---

# 4.13 Android 17 MemoryLimiter：memcg 限制与超限诊断

> 源码以 AOSP `android-17.0.0_r1` 与内核 `android17-6.18-2026-06_r6` 为基准。本文沿源码调用链说明启用条件、memcg 写入、从事件监听到轮询的切换、联合超限后的延迟杀进程流程，以及现场监控口径。

## 先确认实现边界

MemoryLimiter 是 `system_server` 内的一套按进程配置和监控 memcg 的机制。它根据进程状态选择一组内存参数，由 JNI 写入该进程的 cgroup v2 文件；当进程进入持续高内存区间时，它还可以采集诊断信息并请求 AMS 杀进程。

这套实现有四个边界：

1. Android 17 JNI 写入的是 `memory.high` 和 `memory.swap.max`。Java 层仍使用 `swapHigh`、`LIMIT_TYPE_SWAP`，部分注释甚至写着 `memory.swap.high`，这些名称不能替代 JNI 的文件路径。
2. `memory.high` 是带回收压力和节流效果的软边界；`memory.swap.max` 是 swap 使用量的硬上限。两者的内核语义不同。
3. Native 层只监听 `memory.events` 中的 `high` 计数变化，没有监听 `memory.swap.events`。联合超限由轮询 `anon + shmem + swap.current` 计算，不依赖第二个 swap 事件。
4. 联合超限后的 30 秒用于可选的系统 profiling。MemoryLimiter 不会向目标应用发送 `onTrimMemory()`，这段时间不能称为“应用自救窗口”。

## 从 ProcessRecord 到 memcg

### Java 层负责策略，Native 层负责文件与事件

Android 17 的主要职责分布如下：

| 位置 | 职责 |
|---|---|
| `ProcessRecord` | 在 PID、UID 和 proc state 变化时通知对应的 `MemoryLimiter.Limiter` |
| `MemoryLimiter.Limiter` | 记录单个进程的 PID、UID、包名和最近一组限制 |
| `ControllerEnabled` | 读取 vendor 配置，建立 proc state 映射，在后台 `Handler` 上串行发送 Native 命令，处理超限回调、statsd 和 kill |
| JNI `Monitor` | 找到进程 cgroup，写限制文件，监听 `memory.events`，维护 red-zone 进程并定时轮询 |
| cgroup v2 memory controller | 执行 `memory.high` 的回收/节流和 `memory.swap.max` 的 swap 硬限制 |

`ProcessRecord` 在构造时创建一个 `Limiter`。设置 PID、绑定 `UidRecord` 以及更新进程状态时，分别调用 `setPid()`、`setUidRecord()` 和 `onProcStateUpdated()` 将生命周期变化传给 Limiter。Java 层只在选出的 `Limits` 与上一组不同时发送 `MESSAGE_CONFIG`，所以在使用同一档配置的状态之间切换不会重复下发。

`Handler` 保证命令在 `BackgroundThread` 上按队列顺序执行，但源码没有合并队列中连续的配置消息。不要把“相同配置不重复发送”理解为 Handler 会自动只保留最终一条。

### 启用条件与配置选择

默认实例要进入 `ControllerEnabled`，需要同时满足：

- `Flags.memoryLimiterEnable()` 为真；
- 当前进程是 system UID；
- `/vendor/etc/memory-limiter-config.xml` 存在；
- 配置中至少有一组 `minimumRequiredMemTotal` 不大于设备的 `MemTotal`。

文件不存在或没有适合当前内存容量的配置时，默认控制器保持禁用。XML 版本错误、字段缺失或解析失败会转换为 `IllegalArgumentException`；源码没有把所有配置错误都静默降级。

配置模式由 `services/core/xsd/memory-limiter-config/memory-limiter-config.xsd` 定义。下面只展示结构，数值应由设备厂商根据整机内存、ZRAM 和工作负载验证后填写：

```xml
<MemoryLimiterConfig>
  <version>1</version>
  <configList>
    <limitSet>
      <minimumRequiredMemTotal>10240</minimumRequiredMemTotal>
      <memVisible>6144</memVisible>
      <memNotVisible>3072</memNotVisible>
      <swapVisible>3072</swapVisible>
      <swapNotVisible>3072</swapNotVisible>
    </limitSet>
  </configList>
</MemoryLimiterConfig>
```

所有容量字段以 MiB 为单位。`getConfiguration()` 会从满足条件的 `limitSet` 中选择 `minimumRequiredMemTotal` 最大的一组，再换算成字节。源码里的 4 GiB/2 GiB/2 GiB/2 GiB `sDefaultConfig` 明确用于测试，不能当成 Android 17 设备的统一默认值。

此外还有三类独立开关：

- `Flags.memoryLimiterTrigger()` 决定 Native 监控线程是否工作；
- `Flags.memoryLimiterSwap()` 决定是否配置 swap 限制；
- `memory_limiter_disable_limits` 与 `memory_limiter_disable_kill` 可在运行时分别关闭后续限制下发和杀进程。

运行时关闭限制后，`getStateLimit()` 返回 `max/max`，但要等进程下一次状态变化才会下发这组值。它并不会在开关变化的瞬间遍历并改写所有受控进程。

启用控制器还会初始化豁免列表：`initializeExemptList()` 会读取 framework 资源 `config_defaultOnDeviceSandboxedInferenceService`，解析出包名后加入 `mExemptList`。因此，排查“同一 proc state 下为什么某些进程没有被下发限制”时，除了功能开关、vendor XML 和 UID ignore 状态，还要核对目标包是否落入这类默认豁免；不要只用进程状态表反推一定会写入 cgroup。

## ProcState 到 Limits 的映射

`initializeMemoryLimits()` 将进程状态归入五类：

| 类别 | `memory.high` 参数 | `memory.swap.max` 参数 | 进程状态 |
|---|---:|---:|---|
| ignored | 不写 | 不写 | `UNKNOWN`、`NONEXISTENT` |
| unlimited | `max` | `max` | `PERSISTENT`、`PERSISTENT_UI` |
| visible | `memVisible` | `swapVisible` | `TOP`、`BOUND_TOP`、`IMPORTANT_FOREGROUND`、`TOP_SLEEPING` |
| not-visible | `memNotVisible` | `swapNotVisible` | `FOREGROUND_SERVICE`、`BOUND_FOREGROUND_SERVICE`、`IMPORTANT_BACKGROUND`、`TRANSIENT_BACKGROUND`、`BACKUP`、`SERVICE`、`RECEIVER`、`HEAVY_WEIGHT`、`HOME`、`LAST_ACTIVITY` |
| cached | 不改当前值 | `max` | `CACHED_ACTIVITY`、`CACHED_ACTIVITY_CLIENT`、`CACHED_RECENT`、`CACHED_EMPTY` |

这里有两个特殊值：

- `LIMIT_IS_DISABLED = -1`：Native 写入字符串 `max`，明确取消该项限制；
- `LIMIT_IS_IGNORED = -2`：Native 跳过这次写入，保留 cgroup 文件当前值。

因此，cached 不能简单描述成“MemoryLimiter 完全豁免”。进程从受控状态转入 cached 时，swap 上限会被取消，而 `memory.high` 使用 ignored 语义，之前写入的值可能继续留在 cgroup 文件中。这个细节会影响现场排查：只看当前 proc state，无法推断 `memory.high` 一定是 `max`。

## 两个 cgroup 文件，两种内核语义

### `memory.high`

内核 `Documentation/admin-guide/cgroup-v2.rst` 将 `memory.high` 定义为内存使用节流边界。超过它以后，cgroup 内任务会承受较强的回收压力并可能被节流；越界本身不会调用 memcg OOM killer，而且极端情况下允许暂时超过边界。

Android 17 JNI 使用普通的 `android::base::WriteStringToFile()` 写入该节点，没有以 `O_NONBLOCK` 打开。因此，下调 `memory.high` 时触发的回收可能同步发生在 MemoryLimiter 后台 Handler/JNI 调用路径上。它不阻塞 AMS 锁内的调用者，但仍会占用 MemoryLimiter 后台处理线程。

### `memory.swap.max`

`memory.swap.max` 是该 cgroup 的 swap 使用硬上限。达到上限后，该 cgroup 的匿名页不能继续换出。它不会提供 `memory.high` 那样的软边界语义，也不能写成 `memory.swap.high`。

JNI 中的关键映射是：

```cpp
case CgroupFile::kMemoryHigh:
    return (mCgroupRoot / "memory.high").string();
case CgroupFile::kSwapMax:
    return (mCgroupRoot / "memory.swap.max").string();
```

Java 字段 `swapHigh` 只是遗留命名。排查设备行为时，应以 JNI 路径和设备上的 cgroup 文件为准。

## 事件监听如何切换到 red-zone 轮询

### 第一步：只监听 `memory.events`

Native 为受控进程找到 `MemEvents` cgroup 属性对应的目录，然后用：

```cpp
inotify_add_watch(memory.events, IN_MODIFY)
```

建立监听。开始监听时记录 `memory.events` 的 `high` 计数作为 baseline。收到文件修改通知后还会重新读取计数；只有 `high` 与 baseline 不同才算目标事件，其余修改计入 `false-events`。

源码虽然保留 `kSwapMax`、`LIMIT_TYPE_SWAP` 等枚举，但 `getEventCount(kSwapMax)` 返回 0，watch descriptor 也只可能映射为 `kMemoryHigh`。所以 Android 17 不能被描述为同时监听 memory 与 swap 两个事件文件。

### 第二步：首次 `memory.high` 事件进入 red zone

确认 `high` 计数变化后，Native 依次完成这些动作：

1. 保存事件发生前的进程快照；
2. 移除该进程的 `memory.events` watch；
3. 将 `mMemWatcher.mTriggered` 置为真；
4. 重新下发限制；
5. 回调 Java，事件类型为 `LIMIT_TYPE_MEMORY`；
6. 标记存在 red-zone 进程，使轮询周期切换为 30 秒。

重新下发时，已触发的 `memory.high` 会增加 100 MiB margin：

```text
写入 memory.high = 配置的 memHigh + 100 MiB
联合阈值          = 配置的 memHigh + 配置的 swapMax
```

margin 给进程继续执行和回收匿名内存留出空间。它不会改变 Java 保存的原始 `memHigh`，也不会增加联合阈值。

### 第三步：轮询联合指标

Native 监控线程只有一个 `epoll_wait()` 循环。生产环境下：

- 没有 red-zone 进程时，5 分钟超时用于清理已经退出的 PID；
- 存在 red-zone 进程时，超时缩短为 30 秒，并在一轮中检查所有 red-zone 进程；
- 测试模式使用 1 秒周期。

因此，多个进程不会各自创建一个 30 秒定时器。

每次 red-zone 轮询读取：

```text
anonSwapMetric = memory.stat:anon
               + memory.stat:shmem
               + memory.swap.current
anonSwapLimit  = configured memHigh + configured swapMax
```

`testAnonSwap()` 返回四个枚举值：

| 返回值 | 判定 | 后续动作 |
|---|---|---|
| `kCold` | 联合指标低于 `memHigh - 10 MiB` | 重新监听 `memory.events`，退出 red zone |
| `kOkay` | 尚未超过联合阈值，也没有低到恢复监听的边界 | 继续 30 秒轮询 |
| `kHot` | 联合指标大于 `anonSwapLimit` | 置位联合超限并回调 Java |
| `kTriggered` | 联合超限已经置位 | 内部终态标记；该进程已不再满足 `isRed()` |

这些枚举是一次轮询的判定结果，不要求按 `kCold → kOkay → kHot → kTriggered` 的顺序逐级迁移。一个进程可以在第一次 red-zone 轮询时直接得到 `kHot`。10 MiB 是恢复事件监听的滞回量，用于减少边界附近的反复切换。

## 联合超限之后发生什么

Native 发现 `kHot` 后将事件类型 `LIMIT_TYPE_ANON_SWAP` 回调到 Java。`ControllerEnabled` 的处理顺序如下：

1. 记录日志，并在令牌桶允许时写入 `MEMORY_LIMITER_OVER_LIMIT_EVENT`；
2. 把 `memory.high` 和 `memory.swap.max` 都配置为 `max`；
3. 在两个 profiling feature flag 均打开且能取得包名时，通知 `ProfilingServiceHelper`；
4. 向后台 Handler 投递延迟 30 秒的 `MESSAGE_KILL`；
5. 到期后，如果 `memory_limiter_disable_kill` 没有打开，通过 `IActivityManager.killPids()` 请求杀掉目标 PID。

这里需要区分两个同为 30 秒的值：

- `RED_POLL_PERIOD_MS = 30s`：检查 red-zone 联合指标的周期；
- `KILL_DELAY_MS = 30s`：联合超限回调后等待系统 profiling 的时间。

杀进程延迟的源码注释明确指向 profiler 完成时间，并带有未来改为“profiling 完成后杀进程”的 TODO。代码没有调用目标应用的 `scheduleTrimMemory()`，也没有发送任何供应用确认恢复的回调。即使应用在这 30 秒内主动释放内存，已排队的 kill 消息也不会因内存下降自动取消。

`memory.high` 单项事件只会触发日志、statsd 和 red-zone 监控，不会直接安排 kill。当前 Native 实现也不会产生独立的 `LIMIT_TYPE_SWAP` 回调。

## statsd 令牌桶的准确含义

`ControllerEnabled` 的桶容量为 4，每过一个小时补充 1 个 token，最多恢复到 4。一次允许的 atom 写入消耗 1 个 token。

这不等于“每小时允许 4 条”。空桶后的持续速率是每小时 1 条，4 只表示空闲一段时间后最多可以连续上报 4 条。源码注释把整体效果描述为每天最多 28 条；讨论精确滑动窗口时还要考虑首次调用、整点取整和观察窗口边界。

限流只影响 statsd atom，不会阻止日志、解除限制、profiling 或 kill 流程。

## 与 lmkd、CachedAppOptimizer 的关系

MemoryLimiter、lmkd 和 CachedAppOptimizer 使用不同信号：

| 机制 | 主要输入 | 主要动作 |
|---|---|---|
| MemoryLimiter | 单进程 proc state、memcg `memory.high` 事件、匿名内存与 swap 联合指标 | 配置进程 cgroup、记录超限、可选 profiling、联合超限后定点 kill |
| lmkd | 系统 PSI、可用内存、swap 状态、进程优先级等 | 在系统压力下选择牺牲进程 |
| CachedAppOptimizer | cached 状态、压缩/冻结策略及相关触发 | 压缩或冻结 cached 进程 |

这三套机制可能作用于同一个进程生命周期，但源码中没有一条统一状态机保证它们按固定先后顺序执行。尤其要避免两种过度简化：

- cached 的 `memory.high` 使用 ignored，可能保留旧值；
- MemoryLimiter 的 30 秒延迟 kill 不代表 lmkd 也会等待。

做性能归因时，应同时查看进程状态变化、cgroup 文件、MemoryLimiter 日志、lmkd 日志和进程退出记录，不能只凭一次 PSS 下降判断是哪套机制生效。

## 现场检查清单

### 1. 先确认功能有没有启用

检查 vendor 配置文件是否存在、当前 `MemTotal` 是否能匹配一组 `limitSet`，并从 `dumpsys activity` 的 Memory limiter 段确认控制器状态。没有配置文件的设备上，不应仅凭 Android 版本推断该功能已启用。

### 2. 再确认目标进程所在 cgroup

JNI 通过 `CgroupGetAttributePathForProcess("MemEvents", uid, pid, ...)` 解析路径。设备的 cgroup 布局可能随 task profile 配置变化，不要在脚本中写死目录。

找到目录后重点读取：

```text
memory.high
memory.events
memory.stat
memory.swap.current
memory.swap.max
```

连续采样时同时记录 `memory.events:high`、`memory.stat` 的 `anon/shmem` 与 `memory.swap.current`，才能还原从 high 事件到联合超限的过程。

### 3. 解释结果时保留三个时间点

- proc state 改变、下发限制的时间；
- `memory.events:high` 增长、进入 red zone 的时间；
- 联合指标越界、排队延迟 kill 的时间。

三者分开记录，可以区分“下调 `memory.high` 时同步回收”“超过 high 后的持续节流”和“联合超限后的终止”。

## Android 17 版本边界

以下结论只适用于 `android-17.0.0_r1`。文件版权年份、feature flag 名称或某个开发分支中的提交时间，都不足以单独证明该机制在哪个公开 Android 版本首次交付。若要分析 Android 15、16 到 17 的演进，需要分别对照对应 release tag 的 Java、JNI、flags 与设备配置。

Android 17 中还存在若干命名与实现不一致之处，例如 Java 的 `swapHigh`、`memory.swap.high` 注释与 Native 的 `memory.swap.max`。阅读后续版本时，应重新核对文件映射、watch 类型与 feature flag，不能只比较类名是否存在。

## Android 17 源码补记

`android-17.0.0_r1` 的 Java/JNI/XSD 源码中，`MemoryLimiter.java` 为 1291 行，`com_android_server_am_MemoryLimiter.cpp` 为 1276 行，`memory-limiter-config.xsd` 为 54 行。绑定 UID 的 `ProcessRecord` 入口是 `setUidRecord()`，不要和 Limiter 内部保存 UID 的动作混写成 `setUid()`；默认 on-device sandboxed inference service 包名还会进入 `mExemptList`，因此不能把 proc state 映射表理解成所有同状态进程都会被配置限制。其余关键边界包括：JNI 实际写入 `memory.swap.max`、Native watch 只挂在 `memory.events`、cached 状态对 `memory.high` 使用 ignored 语义、联合超限后的 30 秒延迟服务于系统 profiling 而不是应用回调自救。

## 源码索引

- `frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`
  - `getDefaultController()`：启用条件
  - `initializeExemptList()`：默认 sandboxed inference service 豁免
  - `initializeMemoryLimits()`：proc state 映射
  - `shouldLogAtom()`：statsd 令牌桶
  - `onLimitExceeded()`：解除限制、profiling 与延迟 kill
- `frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp`
  - `Process::setLimit()`：`memory.high` 与 `memory.swap.max` 写入
  - `Process::watch()` / `Monitor::handle_modify()`：`memory.events` 监听
  - `Process::testAnonSwap()` / `Monitor::handle_timeout()`：red-zone 联合指标
- `frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java`
  - `setPid()`、`setUidRecord()`、`onProcStateUpdated()`：生命周期挂接点
- `frameworks/base/services/core/xsd/memory-limiter-config/memory-limiter-config.xsd`
  - vendor XML 的字段与单位
- Linux `Documentation/admin-guide/cgroup-v2.rst`
  - `memory.high` 与 `memory.swap.max` 的内核语义

可直接核对的公开标签入口：

- [MemoryLimiter.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [MemoryLimiter JNI @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)
- [ProcessRecord.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessRecord.java)
- [memory-limiter-config.xsd @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/xsd/memory-limiter-config/memory-limiter-config.xsd)
- [cgroup v2 文档 @ android17-6.18-2026-06_r6](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)

## 延伸阅读

- §4.4 系统内存压力与 lmkd：包括 PSI、thrashing 与 kill 决策
- §4.11 Cached App Freezer、外部页回收与 GC 边界
- §4.14 `onTrimMemory()` 回调：MemoryLimiter 不向目标应用发送专属 trim
