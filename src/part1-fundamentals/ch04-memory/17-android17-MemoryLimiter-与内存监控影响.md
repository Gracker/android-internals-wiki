---
title: "Android 17 MemoryLimiter 与内存监控影响"
chapter: "4.17"
status: ready-for-review
drafted_date: "2026-06-28"
applicable_versions: "Android 16 (API 36) - Android 17 (API 37)"
last_verified: "2026-06-28"
last_verified_against: "AOSP android-17.0.0_r1"
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
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java (mMemoryLimiter mount points)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java (Limiter instantiation)"
  - type: aosp
    path: "frameworks/base/core/java/android/os/Debug.java (MemoryInfo + getMemoryInfo)"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java (trim levels)"
tags: [MemoryLimiter, memory, cgroup, monitoring, Debug.MemoryInfo, PSS, swap, APM]
related_chapters: ["4.4", "4.5", "4.11", "4.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "daily-info + research-gaps"
---

# 4.17 Android 17 MemoryLimiter 与内存监控影响

Android 17 的 `system_server` 包含 `MemoryLimiter`：它按照应用进程的 proc state 配置 cgroup v2 `memory.high` 和 `memory.swap.max`，监听 `memory.high` 事件，并在匿名内存与 swap 的联合用量持续越界时请求诊断、延迟终止进程。

它与 lmkd、CachedAppOptimizer 解决的问题不同：

| 组件 | 主要输入 | 主要动作 |
|---|---|---|
| lmkd | 系统 PSI、内存事件、进程优先级等 | 在系统压力下选择进程并终止 |
| CachedAppOptimizer | cached 状态、冻结和压缩策略 | 冻结 cached 进程，按策略压缩进程内存 |
| MemoryLimiter | 单进程 proc state、vendor 限额、memcg 事件 | 写每进程 cgroup 限额，记录越界，满足联合条件后延迟终止 |

本节以 `android-17.0.0_r1` 为平台源码锚点，以 `android17-6.18-2026-06_r6` 为内核语义锚点。重点放在两个问题：MemoryLimiter 怎样工作，以及应用监控数据怎样避免错误归因。

## 1. 先确认设备是否启用

源码中存在 `MemoryLimiter`，不代表每台 Android 17 设备都在执行限制。默认 controller 要同时满足：

1. `Flags.memoryLimiterEnable()` 为真；
2. 当前进程是 `system_server`；
3. `/vendor/etc/memory-limiter-config.xml` 存在；
4. 配置文件有效，并且至少一组 `minimumRequiredMemTotal` 适合本机总内存。

缺少配置文件或没有匹配的 `LimitSet` 时，系统使用 `ControllerDisabled`。文件存在但 XML 无效、版本不为 1 或列表为空时，解析会抛出 `IllegalArgumentException`；这和“解析失败后安静禁用”是两种行为。

即便 controller 已创建，以下开关仍会改变运行结果：

| 开关 | Android 17 源码中的作用 |
|---|---|
| `memory_limiter_enable` aconfig flag | 决定构造 enabled controller 还是 disabled controller |
| `memory_limiter_trigger` aconfig flag | 决定 native 是否创建 inotify/epoll 监控线程并处理进程限额 |
| `memory_limiter_swap` aconfig flag | 决定是否配置 `memory.swap.max` |
| `memory_limiter_disable_limits` DeviceConfig | 运行时让后续 proc-state 更新改用无限额配置 |
| `memory_limiter_disable_kill` DeviceConfig | 保留检测与记录，但跳过延迟 kill |

不要只看 Android 版本或 feature flag 名字推断现场状态。平台调试时先执行：

```text
adb shell am memory-limiter status
```

该命令会报告 limits、monitoring、killing、visible/not-visible 配额以及 native 统计。是否允许执行取决于 shell 命令的权限环境。

## 2. 配额来自 vendor XML，不是固定的 4GB/2GB

配置文件给出一组或多组绝对 MiB 数值：

- `memVisible`
- `memNotVisible`
- `swapVisible`
- `swapNotVisible`
- `minimumRequiredMemTotal`

`getConfiguration()` 选择 `minimumRequiredMemTotal <= MemTotal` 中门槛最高的一组。源码中的 `Configuration(4GB, 2GB, 2GB, 2GB)` 标有 `@VisibleForTesting`，注释也明确提醒生产使用前需要重新评估。监控系统不应把这组测试值当成 Android 17 的平台默认配额。

每个 `ProcessRecord` 持有一个 `MemoryLimiter.Limiter`。PID、UID 和包名准备好且 UID 属于应用范围后，Limiter 才开始工作；proc state 变化时，它把新配置异步发到 BackgroundThread，再由 JNI 写入 cgroup。

Android 17 的状态分组如下：

| 组别 | proc state | `memory.high` | `memory.swap.max` |
|---|---|---|---|
| unrestricted | `PERSISTENT`、`PERSISTENT_UI` | `max` | `max` |
| visible | `TOP`、`BOUND_TOP`、`IMPORTANT_FOREGROUND`、`TOP_SLEEPING` | `memVisible` | `swapVisible` |
| not-visible | `FOREGROUND_SERVICE`、`BOUND_FOREGROUND_SERVICE`、`IMPORTANT_BACKGROUND`、`TRANSIENT_BACKGROUND`、`BACKUP`、`SERVICE`、`RECEIVER`、`HEAVY_WEIGHT`、`HOME`、`LAST_ACTIVITY` | `memNotVisible` | `swapNotVisible` |
| cached | 四个 `CACHED_*` 状态 | `IGNORED`：不改写现值 | `max` |
| ignored | `UNKNOWN`、`NONEXISTENT` | 不改写 | 不改写 |

cached 进程的 `memory.high` 会保留先前值，swap 上限则写成 `max`。所以“cached 进程完全移除所有 MemoryLimiter 配置”并不符合这份源码。

另外，`config_defaultOnDeviceSandboxedInferenceService` 指向的包会进入豁免名单。普通系统 UID、无效 PID/UID 也不会进入每应用限制。

## 3. 写入的是 `memory.high` 与 `memory.swap.max`

JNI 中 `Process::CgroupFile` 的实际路径映射为：

```cpp
kMemoryStat   -> memory.stat
kMemoryEvent  -> memory.events
kMemoryHigh   -> memory.high
kSwapCurrent  -> memory.swap.current
kSwapMax      -> memory.swap.max
```

这里没有配置 `memory.swap.high`。部分 Java/C++ 注释仍出现 `swap.high` 字样，但 `cgroupPath()`、`setLimit()` 和 feature flag 的执行代码都指向 `memory.swap.max`，判断行为时应以执行代码为准。

### 3.1 内核对两个限制的定义

在 `android17-6.18-2026-06_r6` 的 cgroup v2 文档中：

- `memory.high` 是内存使用量的 throttle 边界。越界会让 cgroup 内任务承受回收压力和节流；单独越过它不会调用 OOM killer，极端情况下允许暂时超出。
- `memory.swap.max` 是 swap 使用硬上限。达到上限后，该 cgroup 的匿名内存不能继续换出。
- `memory.swap.current` 单独报告当前 swap 使用量。
- `memory.current` 报告 cgroup 及其后代的当前内存使用量，swap 另由 `memory.swap.current` 报告。

因此，`memory.high` 与 `memory.swap.max` 的效果不能都写成“软限制”。也不能把 `memory.current` 描述成已经包含 swap 的总数。

MemoryLimiter 通过普通 `WriteStringToFile()` 写限额，没有用 `O_NONBLOCK` 打开 `memory.high`。内核文档说明，降低 `memory.high` 引起的回收可在写入方同步发生；JNI 源码也留下了同样的注释。

## 4. 从首次 `memory.high` 事件到联合越界

native 端只给 `memory.events` 添加 inotify watch，并以其中 `high` 计数变化识别首次越界。Android 17 中 `LIMIT_TYPE_SWAP` / `kSwapMax` 虽有枚举位置，当前 `watch()`、`getLimitType()` 和 `getEventCount()` 没有建立独立 swap event watch；不要据枚举推断存在一条 `memory.swap.high` 回调。

### 4.1 正常监控阶段

进程加入监控后，native 记录 `memory.events:high` 的 baseline。发生 `IN_MODIFY` 时再次读取计数；计数没变的通知记为 false event，计数变化才进入 over-limit 处理。

首次 `memory.high` 越界会：

1. 回调 Java，记录 `LIMIT_TYPE_MEMORY`；
2. 移除当前 `memory.events` watch；
3. 把 `mMemWatcher.mTriggered` 置为真；
4. 重新写限额，此时 `memory.high` 在原始 `memHigh` 上增加 100MB margin；
5. 进入 native 所说的 red zone，改用较短周期轮询。

100MB margin 只在 `memory.high` 已经触发后加入。常态写入值仍是配置中的 `memHigh`。margin 的目的，是让进程在高压回收后仍有运行和减少 anon 的余量。

### 4.2 red-zone 轮询

native 监控线程使用 epoll：

- 无 red-zone 进程时，超时周期为 5 分钟，主要清理已经退出的 PID；
- 存在 red-zone 进程时，周期为 30 秒；
- 测试模式以及监控线程初始轮询使用 1 秒。

轮询计算的联合指标是：

```text
memory.stat:anon
+ memory.stat:shmem
+ memory.swap.current
```

它与原始 `memHigh + swapMax` 比较：

| `AnonSwapState` | 条件与动作 |
|---|---|
| `kHot` | 联合指标大于联合限额，生成 `LIMIT_TYPE_ANON_SWAP` |
| `kCold` | 联合指标低于 `memHigh - 10MB`，重新安装 `memory.events` watch |
| `kOkay` | 位于中间区间，保持轮询 |
| `kTriggered` | 联合事件已经生成，不重复触发 |

10MB 是回到事件监控的滞回量。源码注释说明该值没有特殊理论依据，只是足够小且便于测试。

需要留意三个口径差异：

1. `memory.high` 事件面向 cgroup 总内存使用；
2. 后续联合指标只取 `anon + shmem + swap`；
3. 指标属于进程 cgroup，可能包含该 cgroup 的后代，不等同于单个 PID 的 PSS。

## 5. 联合越界后的 30 秒

native 生成 `LIMIT_TYPE_ANON_SWAP` 后，Java 依次执行：

1. 写 `memory.high=max`、`memory.swap.max=max`，解除两个限制；
2. 受令牌桶约束地写入 statsd atom；
3. 在两个 profiling flag 都开启且能取得包名时，调用 `ProfilingServiceHelper.onProfilingTriggerOccurred()`；
4. 向 BackgroundThread handler 投递延迟 30 秒的 kill 消息。

源码对 30 秒的解释很具体：给已配置的 profiler 留出完成时间，并计划在 profiling API 支持 “kill when finished” 后移除固定延迟。MemoryLimiter 没有在这里向目标应用派发 `onTrimMemory()`，这 30 秒也不是应用可依赖的“自救回调窗口”。

profiling 请求需要同时满足：

- `systemTriggeredProfilingNew()`；
- `anomalyDetectorCoreC()`；
- 包名非空。

源码没有承诺这些 flag 在所有 Android 17 产品上都开启。进程被 MemoryLimiter 终止，也不保证一定存在对应 heap profile。

### 5.1 kill 的退出归因

延迟消息调用 `IActivityManager.killPids(..., "MemoryLimiter:AnonSwap", true)`。AMS 随后使用：

- `ApplicationExitInfo.REASON_OTHER`
- `ApplicationExitInfo.SUBREASON_KILL_PID`
- 人类可读原因 `"MemoryLimiter:AnonSwap"`

应用下次启动时可以查询 `getHistoricalProcessExitReasons()`。`getDescription()` 可能带出该原因，但 `ApplicationExitInfo` 的 API 文档明确说明 description 格式不保证跨设备、跨版本稳定。可靠策略是保存 reason、status、importance、timestamp、description 原文和自己的前台/后台状态，再在服务端按版本做归因；不要把某个 description 子串当成唯一且永久的协议。

statsd 的 token bucket 初始最多允许连续 4 条，此后每小时补 1 条，上限仍为 4；源码注释将其概括为每天最多 28 条。statsd 适合受控的系统遥测，不是应用侧逐事件告警接口。通过反射 hook `MemoryLimiter$ControllerEnabled` 既依赖隐藏实现，也会受到 hidden-API 与权限限制，不应作为普通应用方案。

## 6. PSS、SwapPss 与 memcg 指标不要相互代替

MemoryLimiter 不读取 `Debug.MemoryInfo`。它使用 cgroup 的 anon、shmem 和 swap 数据；应用常见的 PSS 则来自进程内存映射统计，按共享页映射者数量分摊。两者用途不同。

### 6.1 Android 17 的 `getTotalPss()` 已计入 SwapPss

`Debug.MemoryInfo.getTotalPss()` 在 `android-17.0.0_r1` 中定义为：

```java
return dalvikPss
        + nativePss
        + otherPss
        + getTotalSwappedOutPss();
```

所以，“`getTotalPss()` 完全不含 swap”在该版本并不成立。内核能报告 SwapPss 时，方法会把 proportional swapped-out PSS 加进结果；`hasSwappedOutPss()` 为假时，对应项为 0。

`getMemoryStat("summary.total-swap")` 另行返回 total swapped-out KB。它不是 SwapPss。把 `getTotalPss()` 再加 `/proc/<pid>/status` 的 `VmSwap` 会把已经计入的 SwapPss 重复相加，而且 VmSwap 没有按共享 swap 分摊。更稳妥的监控方式是把下列数值分栏保存：

| 指标 | 适合回答的问题 | 注意点 |
|---|---|---|
| `getTotalPss()` | 进程对内存的比例归属及可用时的 SwapPss | 单位 KB；共享页按比例；可能含 SwapPss |
| `summary.total-swap` / `VmSwap` | 进程换出规模 | 非比例口径，不要直接追加到 total PSS |
| RSS | 当前驻留页规模 | 共享页在每个进程重复计算 |
| cgroup `memory.stat` anon/shmem | memcg 内匿名与共享内存 charge | cgroup 口径，需要相应权限 |
| `memory.swap.current` | memcg 当前 swap charge | 与 `memory.current` 分开 |
| `memory.events:high` | `memory.high` 节流/回收事件计数 | 需要读取目标 cgroup，普通应用通常不可用 |

### 6.2 PSS 下降没有唯一原因

`memory.high` 造成的回收、换出或应用自身 GC 可能让 PSS/RSS 变化，文件页丢弃、解除映射、共享者数量变化也会改变结果。只看到一条 PSS 下降曲线，无法证明 MemoryLimiter 已触发。

普通应用没有 MemoryLimiter 越界回调，也通常不能读取目标 memcg 文件。监控平台可采用分级证据：

- 应用内：记录 PSS、swap、RSS、proc state、trim level、GC 和关键业务阶段；
- 测试设备：同时抓 `am memory-limiter status`、logcat、cgroup 文件与 system trace；
- 进程重启后：查询 `ApplicationExitInfo`，保留原始字段；
- OEM/system app：在已有权限允许时，将 `memory.events:high` 与同一时钟上的进程指标关联。

不能用 `onTrimMemory(TRIM_MEMORY_BACKGROUND)` 给 PSS 波动贴上“内核回收”标签。该回调表达进程/UI 状态与系统内存提示，MemoryLimiter 的首次越界和联合越界代码都没有派发它。

## 7. `Debug.MemoryInfo` 与系统统计为何可能不同

### 7.1 自进程与跨进程 API 边界

`Debug.getMemoryInfo(MemoryInfo)` 直接读取当前进程可见的低层数据，源码注释提醒它可能看不到 graphics 等受保护分配。`ActivityManager.getProcessMemoryInfo()` 面向调试或用户可见的进程管理 UI；从 Android 10 起，普通应用只能取得同 UID 进程的数据，调用过快还会得到缓存的旧样本。

因此，1Hz 调用不保证获得 1Hz 的新数据。监控 SDK 应记录采样 API、采样时间和数据新鲜度，避免把服务端限频返回的重复值解释成“PSS 冻结”。

### 7.2 DMA-BUF 修正属于 system_server 统计

Android 17 的 `MemoryUsageStats.getTotalPss()` 会：

- PSS 未覆盖 `VM_PFNMAP` 映射时，以 mapped DMA-BUF 替换 memtrack Graphics；
- GPU private usage 可用时，减去已经计入 kernel memory 的 memtrack GL，避免重复计算。

这是 `system_server` 内部汇总逻辑，不是 `Debug.MemoryInfo` 暴露给应用的通用修正公式。应用无法通过 `dalvikPss` 推导 DMA-BUF，也不应自行复制一段缺少 memtrack 和 GPU 权限数据的计算。

### 7.3 `MemoryStatUtil` 已退回 procfs

`MemoryStatUtil.MemoryStat` 的字段注释仍保留“memcg 可用时”的历史说明，但 Android 17 的 `readMemoryStatFromFilesystem()` 直接调用 `readMemoryStatFromProcfs(pid)`。它读取 `/proc/<pid>/stat` 的 page fault、major fault 和第 24 个字段 RSS（数组索引 23）；`cacheInBytes` 与 `swapInBytes` 不会由这条路径填充。

这个 helper 与 MemoryLimiter JNI 读取的 `memory.stat` 不是同一数据源。不能从相似的类名推导它们共享 memcg 统计。

## 8. `onTrimMemory()` 的正确边界

Android 14 / API 34 起，应用不再收到以下五档：

- `TRIM_MEMORY_COMPLETE`
- `TRIM_MEMORY_MODERATE`
- `TRIM_MEMORY_RUNNING_CRITICAL`
- `TRIM_MEMORY_RUNNING_LOW`
- `TRIM_MEMORY_RUNNING_MODERATE`

仍应处理 `TRIM_MEMORY_UI_HIDDEN` 与 `TRIM_MEMORY_BACKGROUND`，并按 `>=` 比较已支持的等级，为将来新增中间值留出空间。回调适合释放可重建的 UI 资源和后台缓存；运行中的 FGS 或 Service 不一定会先收到 `BACKGROUND`。

不要把 `onTrimMemory()` 当作 MemoryLimiter 专属信号，也不要主动调用 `System.gc()` 代替资源治理。`ComponentCallbacks2` 源码说明，runtime 可以随应用状态变化自行触发 GC。

## 9. 应用与平台监控建议

### 9.1 普通应用

普通应用看不到 vendor 限额与 native 状态机，可做的工作是：

1. 对每个样本记录单位、API 和进程身份；
2. 分开上报 total PSS、total swap、RSS，不自行拼成一个“精确总内存”；
3. 记录 UI 可见性、FGS/Service 状态、trim 回调、GC 和大分配阶段；
4. 下次启动查询 `ApplicationExitInfo`，保留完整记录；
5. 只在测试和 profile 证明有收益时减少分配或缓存，不因单次 PSS 波动改写内存策略。

### 9.2 平台与 OEM

具备系统权限时，还应记录：

- `am memory-limiter status` 输出；
- 生效的 vendor `LimitSet` 与 aconfig/DeviceConfig 状态；
- proc state 变化及实际写入的 cgroup 值；
- `memory.events:high`、`memory.stat`、`memory.swap.current`；
- `MemoryLimiter` logcat、statsd atom、profiling 结果和 AMS kill 记录；
- 同时段 PSI、lmkd 决策、GC 与调度数据。

把这些数据放在同一时间轴后，才能区分：

- 应用自身释放或 GC；
- `memory.high` 触发的回收与节流；
- swap 达上限后匿名页无法继续换出；
- lmkd 在系统压力下先行终止；
- MemoryLimiter 联合越界后的延迟终止。

## 10. 版本边界

Android 15 / `android-15.0.0_r1` 与 Android 16 / `android-16.0.0_r1` 都没有这组 `MemoryLimiter.java` 与 JNI 文件；Android 17 / `android-17.0.0_r1` 才能在对应稳定标签中找到它们。本节所有字段、状态与时序均以 Android 17 为准。

MemoryLimiter 仍受多个 flag、vendor 配置和产品策略控制。升级或分析 OEM 分支时，应重新核对：

- `flags.aconfig` 与运行时 DeviceConfig；
- `MemoryLimiter.java` 的 proc-state 表和 kill 处理；
- JNI 实际打开、监听和写入的 cgroup 文件；
- vendor XML schema 与选配规则；
- 内核 cgroup v2 文档和设备挂载层次。

## 小结

- Android 17 MemoryLimiter 配置 `memory.high` 与 `memory.swap.max`，没有配置 `memory.swap.high`。
- 首次 `memory.high` 事件后才增加 100MB margin，并切换到 30 秒 red-zone 轮询。
- 最终联合指标是 `anon + shmem + swap.current`，阈值是原始 `memHigh + swapMax`。
- 联合越界后先解除限制，再按条件请求 profiling，30 秒后由 AMS 以 `REASON_OTHER / SUBREASON_KILL_PID` 终止。
- MemoryLimiter 不派发专属 `onTrimMemory()`，普通应用也没有公开的越界回调。
- Android 17 的 `Debug.MemoryInfo.getTotalPss()` 已包含可用的 SwapPss，不能再无条件追加 VmSwap。
- PSS、RSS、swap 和 memcg charge 是不同口径；监控系统应分别保存并用同一时间轴关联。

## 源码索引

- [MemoryLimiter 设计说明](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.md)
- [MemoryLimiter.java：配置、proc state、profiling 与 kill](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [MemoryLimiter JNI：cgroup 文件、事件与轮询状态](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)
- [ActivityManager flags.aconfig](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/flags.aconfig)
- [ActivityManager performance_flags.aconfig](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/performance_flags.aconfig)
- [ProcessRecord：每进程 Limiter 与 proc-state 更新](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessRecord.java)
- [ActivityManagerService：MemoryLimiter 初始化与 killPids 归因](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [Debug.MemoryInfo：PSS、SwapPss、RSS 与公开统计](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/Debug.java)
- [MemoryUsageStats：DMA-BUF 与 GPU 汇总修正](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryUsageStats.java)
- [MemoryStatUtil：Android 17 procfs 路径](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryStatUtil.java)
- [ComponentCallbacks2：API 34 之后的 trim 等级](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [Kernel cgroup v2：memory 与 swap 接口](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)
