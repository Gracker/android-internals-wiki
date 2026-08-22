---
title: "Android 17 MemoryLimiter：memcg 限制与超限诊断"
chapter: "4.13"
status: ready-for-review
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
---

# 4.13 Android 17 MemoryLimiter：memcg 限制与超限诊断

> 源码以 AOSP `android-17.0.0_r1` 与内核 `android17-6.18-2026-06_r6` 为基准。内容沿源码调用链展开：启用条件、memcg 写入、从事件监听到轮询的切换、联合超限后的延迟终止流程，以及现场监控口径。

## 先确认实现边界

MemoryLimiter 是 `system_server` 内按进程配置和监控内存控制组（memory cgroup，简称 memcg）的机制。cgroup v2 是 Linux 第二版控制组接口，可以按进程或进程组统计并限制资源。MemoryLimiter 根据进程状态选择一组内存参数，再通过 JNI（Java Native Interface，Java 原生接口）写入该进程的 cgroup v2 文件；当进程持续处于高内存区间时，它还可以采集诊断信息，并请求 ActivityManagerService（AMS）终止进程。

这套实现有四个边界：

1. Android 17 的 JNI 写入 `memory.high` 和 `memory.swap.max`。Java 层仍使用 `swapHigh`、`LIMIT_TYPE_SWAP`，部分注释甚至写着 `memory.swap.high`；这些名称不能替代 JNI 中的实际文件路径。
2. `memory.high` 是会施加回收压力并产生节流效果的软边界；`memory.swap.max` 是交换空间用量的硬上限。两者的内核语义不同。
3. 原生层只监听 `memory.events` 中的 `high` 计数变化，并未监听 `memory.swap.events`。联合超限由轮询得到的 `anon + shmem + swap.current` 计算，不依赖第二个交换空间事件。
4. 联合超限后的 30 秒留给可选的系统性能剖析（profiling）。MemoryLimiter 不会向目标应用发送 `onTrimMemory()`，因此这段时间不是供应用主动释放内存的“自救窗口”。

## 从 ProcessRecord 到 memcg

### Java 层负责策略，原生层负责文件与事件

这里的进程状态（proc state）是 ActivityManager 对进程重要程度的分类。Android 17 的主要职责分布如下：

| 位置 | 职责 |
|---|---|
| `ProcessRecord` | 在 PID、UID 和进程状态变化时通知对应的 `MemoryLimiter.Limiter` |
| `MemoryLimiter.Limiter` | 记录单个进程的 PID、UID、包名和最近一组限制 |
| `ControllerEnabled` | 读取设备厂商（vendor）配置，建立进程状态映射，在后台 `Handler` 上依次向原生层发送命令，并处理超限回调、statsd 统计上报和进程终止 |
| JNI `Monitor` | 找到进程 cgroup，写入限制文件，监听 `memory.events`，维护红区进程并定时轮询 |
| cgroup v2 内存控制器 | 执行 `memory.high` 的回收/节流，以及 `memory.swap.max` 的交换空间硬限制 |

`ProcessRecord` 在构造时创建一个 `Limiter`。设置 PID、绑定 `UidRecord` 以及更新进程状态时，它分别调用 `setPid()`、`setUidRecord()` 和 `onProcStateUpdated()`，把生命周期变化传给 `Limiter`。Java 层只在选出的 `Limits` 与上一组不同时发送 `MESSAGE_CONFIG`，所以在使用同一档配置的状态之间切换不会重复下发。

`Handler` 保证命令在 `BackgroundThread` 上按队列顺序执行，但源码没有合并队列中连续的配置消息。“相同配置不重复发送”只发生在入队前，不能理解为 `Handler` 会自动删除旧消息、只保留最后一条。

### 启用条件与配置选择

默认实例要进入 `ControllerEnabled`，需要同时满足：

- `Flags.memoryLimiterEnable()` 为真；
- 当前进程使用 `system` UID；
- `/vendor/etc/memory-limiter-config.xml` 存在；
- 配置中至少有一组 `minimumRequiredMemTotal` 不大于设备 `/proc/meminfo` 中的物理内存总量 `MemTotal`。

文件不存在，或没有适合当前内存容量的配置时，默认控制器保持禁用。XML 版本错误、字段缺失或解析失败会转换为 `IllegalArgumentException`；源码并不会把所有配置错误都静默降级。

配置格式由 `services/core/xsd/memory-limiter-config/memory-limiter-config.xsd` 定义。下面的示例只展示 XML 结构，具体数值应由设备厂商结合整机内存、ZRAM 和实际负载验证后填写：

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

所有容量字段都以 MiB 为单位。`getConfiguration()` 会在满足条件的 `limitSet` 中选择 `minimumRequiredMemTotal` 最大的一组，再换算成字节。源码里的 4 GiB/2 GiB/2 GiB/2 GiB `sDefaultConfig` 明确用于测试，不能视为 Android 17 设备的统一默认值。

此外还有三类独立开关：

- `Flags.memoryLimiterTrigger()` 决定原生监控线程是否工作；
- `Flags.memoryLimiterSwap()` 决定是否配置交换空间限制；
- `memory_limiter_disable_limits` 与 `memory_limiter_disable_kill` 可在运行时分别关闭后续限制下发和进程终止。

运行时关闭限制后，`getStateLimit()` 返回 `max/max`，但这组值要等进程下一次状态变化才会下发。开关发生变化时，系统不会立即遍历并改写所有受控进程。

启用控制器时还会初始化豁免列表：`initializeExemptList()` 读取 framework 资源 `config_defaultOnDeviceSandboxedInferenceService`，解析出默认的设备端沙箱推理服务包名，再加入 `mExemptList`。

因此，排查“处于同一进程状态，为什么某些进程没有收到限制”时，除了功能开关、vendor XML 和 UID 忽略状态，还要核对目标包是否属于默认豁免项。仅凭进程状态映射表，无法断定系统一定会写入 cgroup。

## 从进程状态到内存限制的映射

`initializeMemoryLimits()` 将进程状态归入五类：

| 类别 | `memory.high` 参数 | `memory.swap.max` 参数 | 进程状态 |
|---|---:|---:|---|
| 忽略（ignored） | 不写 | 不写 | `UNKNOWN`、`NONEXISTENT` |
| 无限制（unlimited） | `max` | `max` | `PERSISTENT`、`PERSISTENT_UI` |
| 可见（visible） | `memVisible` | `swapVisible` | `TOP`、`BOUND_TOP`、`IMPORTANT_FOREGROUND`、`TOP_SLEEPING` |
| 不可见（not-visible） | `memNotVisible` | `swapNotVisible` | `FOREGROUND_SERVICE`、`BOUND_FOREGROUND_SERVICE`、`IMPORTANT_BACKGROUND`、`TRANSIENT_BACKGROUND`、`BACKUP`、`SERVICE`、`RECEIVER`、`HEAVY_WEIGHT`、`HOME`、`LAST_ACTIVITY` |
| 缓存（cached） | 不改当前值 | `max` | `CACHED_ACTIVITY`、`CACHED_ACTIVITY_CLIENT`、`CACHED_RECENT`、`CACHED_EMPTY` |

这里有两个特殊值：

- `LIMIT_IS_DISABLED = -1`：原生层写入字符串 `max`，明确取消该项限制；
- `LIMIT_IS_IGNORED = -2`：原生层跳过本次写入，保留 cgroup 文件中的当前值。

因此，不能把缓存进程简单描述为“完全不受 MemoryLimiter 限制”。进程从受控状态转为缓存状态时，交换空间上限会被取消，而 `memory.high` 使用“忽略”语义，之前写入的值可能继续保留在 cgroup 文件中。这个细节会影响现场排查：只看当前进程状态，无法断定 `memory.high` 一定是 `max`。

## 两个 cgroup 文件，两种内核语义

### `memory.high`

内核文档 `Documentation/admin-guide/cgroup-v2.rst` 将 `memory.high` 定义为内存使用节流边界。超过它以后，cgroup 内任务会承受较强的回收压力，并可能被限制执行速度；越界本身不会触发该 memcg 的内存耗尽终止机制（OOM killer），而且在极端情况下允许暂时超过边界。

Android 17 的 JNI 使用普通的 `android::base::WriteStringToFile()` 写入该节点，没有以非阻塞标志 `O_NONBLOCK` 打开。因此，下调 `memory.high` 时触发的回收可能同步发生在 MemoryLimiter 的后台 `Handler`/JNI 调用路径上。它不会阻塞持有 AMS 锁的调用者，但仍会占用 MemoryLimiter 后台处理线程。

### `memory.swap.max`

`memory.swap.max` 是该 cgroup 的交换空间使用硬上限。达到上限后，该 cgroup 的匿名页不能继续换出。它不具备 `memory.high` 那样的软边界语义，也不能写成 `memory.swap.high`。

JNI 中的关键映射是：

```cpp
case CgroupFile::kMemoryHigh:
    return (mCgroupRoot / "memory.high").string();
case CgroupFile::kSwapMax:
    return (mCgroupRoot / "memory.swap.max").string();
```

Java 字段 `swapHigh` 只是遗留名称。排查设备行为时，应以 JNI 返回的路径和设备上的 cgroup 文件为准。

## 事件监听如何切换到红区轮询

进程触发 `memory.high`、但尚未确认联合超限的阶段，称为红区（red zone）。进入红区后，监控方式会从事件监听切换为定时轮询。

### 第一步：只监听 `memory.events`

原生层先找到受控进程的 `MemEvents` cgroup 属性所对应的目录，再调用：

```cpp
inotify_add_watch(memory.events, IN_MODIFY)
```

这行调用为 `memory.events` 建立文件修改监听。开始监听时，代码会记录其中的 `high` 计数作为基准值（baseline）。收到文件修改通知后，监控器会再次读取计数；只有 `high` 与基准值不同才算目标事件，其余修改计入 `false-events`。

源码虽然保留 `kSwapMax`、`LIMIT_TYPE_SWAP` 等枚举，但 `getEventCount(kSwapMax)` 返回 0，监听描述符也只可能映射为 `kMemoryHigh`。所以，Android 17 并未同时监听内存和交换空间两个事件文件。

### 第二步：首次 `memory.high` 事件进入红区

确认 `high` 计数变化后，原生层依次完成这些动作：

1. 保存事件发生前的进程快照；
2. 移除对该进程 `memory.events` 文件的监听；
3. 将 `mMemWatcher.mTriggered` 置为真；
4. 重新下发限制；
5. 回调 Java，事件类型为 `LIMIT_TYPE_MEMORY`；
6. 标记当前存在红区进程，把轮询周期切换为 30 秒。

重新下发时，已触发的 `memory.high` 会增加 100 MiB 裕量（margin）：

```text
写入 memory.high = 配置的 memHigh + 100 MiB
联合阈值          = 配置的 memHigh + 配置的 swapMax
```

这 100 MiB 裕量为进程继续执行和回收匿名内存留出空间。它不会改变 Java 层保存的原始 `memHigh`，也不会增加联合阈值。

### 第三步：轮询联合指标

原生监控线程只有一个 `epoll_wait()` 事件循环。在生产环境中：

- 没有红区进程时，5 分钟超时用于清理已经退出的 PID；
- 存在红区进程时，超时缩短为 30 秒，并在一轮中检查所有红区进程；
- 测试模式使用 1 秒周期。

因此，多个进程不会各自创建一个 30 秒定时器。

每次红区轮询都会读取以下数值：

```text
anonSwapMetric = memory.stat:anon
               + memory.stat:shmem
               + memory.swap.current
anonSwapLimit  = configured memHigh + configured swapMax
```

`testAnonSwap()` 返回四个枚举值：

| 返回值 | 判定 | 后续动作 |
|---|---|---|
| `kCold` | 联合指标低于 `memHigh - 10 MiB` | 重新监听 `memory.events`，退出红区 |
| `kOkay` | 尚未超过联合阈值，也没有低到恢复监听的边界 | 继续 30 秒轮询 |
| `kHot` | 联合指标大于 `anonSwapLimit` | 置位联合超限并回调 Java |
| `kTriggered` | 联合超限已经置位 | 内部终态标记；该进程已不再满足 `isRed()` |

这些枚举是单次轮询的判定结果，不要求按 `kCold → kOkay → kHot → kTriggered` 的顺序逐级迁移。一个进程可以在第一次红区轮询时直接得到 `kHot`。

10 MiB 是上下阈值之间的滞回量，也就是为状态切换预留的缓冲区间，用于减少临界点附近的反复切换。

## 联合超限之后发生什么

原生层发现 `kHot` 后，以事件类型 `LIMIT_TYPE_ANON_SWAP` 回调 Java 层。`ControllerEnabled` 随后按以下顺序处理：

1. 记录日志，并在令牌桶允许时向 statsd 写入结构化事件 `MEMORY_LIMITER_OVER_LIMIT_EVENT`；
2. 把 `memory.high` 和 `memory.swap.max` 都配置为 `max`；
3. 在两个性能剖析功能开关（feature flag）均打开且能取得包名时，通知 `ProfilingServiceHelper`；
4. 向后台 `Handler` 投递延迟 30 秒的 `MESSAGE_KILL`；
5. 到期后，如果 `memory_limiter_disable_kill` 没有打开，通过 `IActivityManager.killPids()` 请求终止目标 PID。

这里需要区分两个同为 30 秒的值：

- `RED_POLL_PERIOD_MS = 30s`：检查红区联合指标的周期；
- `KILL_DELAY_MS = 30s`：联合超限回调后等待系统性能剖析的时间。

源码注释明确说明，延迟终止是为了等待性能剖析器（profiler）完成，并留有将来改为“剖析完成后终止进程”的 TODO。代码没有调用目标应用的 `scheduleTrimMemory()`，也没有发送供应用确认恢复的回调。即使应用在这 30 秒内主动释放内存，队列中的 `MESSAGE_KILL` 也不会因内存下降而自动取消。

单独发生 `memory.high` 事件时，只会触发日志、statsd 上报和红区监控，不会直接安排进程终止。当前原生实现也不会产生独立的 `LIMIT_TYPE_SWAP` 回调。

## statsd 令牌桶的准确含义

statsd 是 Android 的结构化统计收集服务，单条结构化记录称为 atom。MemoryLimiter 用令牌桶限制这类记录的上报频率：`ControllerEnabled` 的桶容量为 4，每过一个小时补充 1 个令牌，最多恢复到 4；每写入一条 atom 消耗 1 个令牌。

这不等于“每小时允许 4 条”。令牌桶耗尽后的持续速率是每小时 1 条；容量 4 只表示空闲一段时间后，最多可以连续上报 4 条。源码注释把整体效果描述为每天最多 28 条；讨论精确的滑动时间窗口时，还要考虑首次调用、整点取整和观察窗口边界。

限流只影响 statsd atom，不会阻止日志记录、解除限制、性能剖析或进程终止流程。

## 与 lmkd、CachedAppOptimizer 的关系

MemoryLimiter、lmkd 和 CachedAppOptimizer 使用不同信号：

| 机制 | 主要输入 | 主要动作 |
|---|---|---|
| MemoryLimiter | 单进程状态、memcg `memory.high` 事件、匿名内存与交换空间联合指标 | 配置进程 cgroup、记录超限、执行可选的性能剖析，并在联合超限后终止指定进程 |
| lmkd | 系统 PSI、可用内存、交换空间状态、进程优先级等 | 在系统压力下选择要终止的进程 |
| CachedAppOptimizer | 缓存状态、压缩/冻结策略及相关触发条件 | 压缩或冻结缓存进程 |

这三套机制可能作用于同一个进程生命周期，但源码中没有统一的状态机保证它们按固定顺序执行。尤其要避免两种过度简化：

- 缓存状态下的 `memory.high` 使用“忽略”语义，可能保留旧值；
- MemoryLimiter 延迟 30 秒终止进程，不代表 lmkd 也会等待。

做性能归因时，应同时查看进程状态变化、cgroup 文件、MemoryLimiter 日志、lmkd 日志和进程退出记录。一次 PSS（按比例分摊共享页后的内存占用）下降，不足以判断是哪套机制生效。

## 现场检查清单

### 1. 先确认功能有没有启用

检查 vendor 配置文件是否存在、当前 `MemTotal` 是否能匹配一组 `limitSet`，并从 `dumpsys activity` 的 `Memory limiter` 段确认控制器状态。设备上没有配置文件时，不能仅凭 Android 版本推断该功能已经启用。

### 2. 再确认目标进程所在 cgroup

JNI 通过 `CgroupGetAttributePathForProcess("MemEvents", uid, pid, ...)` 解析路径。设备的 cgroup 布局可能随任务配置文件（task profile）变化，不要在脚本中写死目录。

找到目录后重点读取：

```text
memory.high
memory.events
memory.stat
memory.swap.current
memory.swap.max
```

连续采样时，应同时记录 `memory.events:high`、`memory.stat` 中的 `anon`/`shmem` 和 `memory.swap.current`。这些数据合在一起，才能还原从 `high` 事件到联合超限的过程。

### 3. 解释结果时保留三个时间点

- 进程状态改变并下发限制的时间；
- `memory.events:high` 增长并进入红区的时间；
- 联合指标越界并排队等待终止进程的时间。

三者分开记录，可以区分“下调 `memory.high` 时同步回收”“超过 high 后的持续节流”和“联合超限后的终止”。

## Android 17 版本边界

以下结论只适用于 `android-17.0.0_r1`。文件版权年份、功能开关名称或某个开发分支中的提交时间，都不足以单独证明该机制最早在哪个公开 Android 版本交付。若要分析 Android 15、16 到 17 的演进，需要分别对照相应的发布标签（release tag）、Java/JNI 源码、功能开关与设备配置。

Android 17 中还有若干命名与实现不一致之处，例如 Java 的 `swapHigh`、`memory.swap.high` 注释与原生层实际使用的 `memory.swap.max`。阅读后续版本时，应重新核对文件映射、监听类型与功能开关，不能只比较类名是否存在。

## Android 17 源码补记

在 `android-17.0.0_r1` 的 Java/JNI/XSD 源码中，`MemoryLimiter.java` 为 1291 行，`com_android_server_am_MemoryLimiter.cpp` 为 1276 行，`memory-limiter-config.xsd` 为 54 行。绑定 UID 的 `ProcessRecord` 入口是 `setUidRecord()`，不要把它和 `Limiter` 内部保存 UID 的动作混写成 `setUid()`。默认的设备端沙箱推理服务包名还会进入 `mExemptList`，所以进程状态映射表并不意味着所有同状态进程都会被配置限制。

其他边界包括：JNI 实际写入 `memory.swap.max`；原生层只监听 `memory.events`；缓存状态对 `memory.high` 使用“忽略”语义；联合超限后的 30 秒延迟服务于系统性能剖析，不是等待应用收到回调后主动释放内存。

## 源码索引

- `frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`
  - `getDefaultController()`：启用条件
  - `initializeExemptList()`：默认沙箱推理服务豁免
  - `initializeMemoryLimits()`：进程状态映射
  - `shouldLogAtom()`：statsd 令牌桶
  - `onLimitExceeded()`：解除限制、性能剖析与延迟终止
- `frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp`
  - `Process::setLimit()`：`memory.high` 与 `memory.swap.max` 写入
  - `Process::watch()` / `Monitor::handle_modify()`：监听 `memory.events`
  - `Process::testAnonSwap()` / `Monitor::handle_timeout()`：红区联合指标
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

- §4.4 系统内存压力与 lmkd：包括 PSI、反复换入换出与进程终止决策
- §4.11 Cached App Freezer、外部页回收与 GC 边界
- §4.14 `onTrimMemory()` 回调：MemoryLimiter 不向目标应用发送专用内存整理回调
