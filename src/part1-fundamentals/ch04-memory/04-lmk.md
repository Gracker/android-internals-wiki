---
title: "Low Memory Killer"
chapter: "4.4"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"
last_verified: "2026-03-31"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "system/memory/lmkd/"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java"
  - type: official
    path: "https://source.android.com/docs/core/perf/lmkd"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: blog
    path: "https://android-developers.googleblog.com/2020/07/lmkd-userspace-low-memory-killer-daemon.html"
tags: ['lmk', 'lmkd', 'oom_adj', 'oom_score_adj', 'PSI', 'memory-pressure', 'process-kill']
related_chapters: ["4.1", "4.2", "4.3", "1.3", "10.4"]
---

# Low Memory Killer

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 LMK 的设计目标：在内存不足时有序释放进程
- 🔹 传统 LowMemoryKiller（内核模块）→ lmkd（用户空间守护进程）的演进
- 🔹 oom_adj_score 与进程优先级的映射关系
- 🔹 lmkd 的杀进程策略：PSI（Pressure Stall Information）驱动的现代策略 vs 传统 minfree 阈值触发，PSI 信号的含义与使用
- 🔹 LMK 在性能问题中的角色：频繁 kill → 频繁冷启动 → 用户感知卡顿

### 扩展（可选深入）

- 🔸 各厂商对 lmkd 的定制化策略
- 🔸 通过 Perfetto 观察 lmkd 行为的方法
- 🔸 Android 16 上 lmkd 的变化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要 LMK：移动设备的内存困境

我们在第四章的开头讲过，Android 把所有 App 都留在内存里是为了快速切换——用户按 Home 键退出一个 App，再回来时几乎瞬间恢复。但内存是有限的。一台 8GB RAM 的手机，系统服务、桌面、输入法这些常驻进程吃掉一半，留给 App 的空间本就不多。如果用户连续打开了十几个 App，内存就会被逐渐填满。

这时候系统面临一个残酷的选择：要么让新 App 无法启动（内存不足，malloc 失败），要么把一些旧 App 从内存里清理出去。

Linux 内核有自己的 OOM Killer，但它的设计面向服务器场景——服务器上进程的重要性通常由管理员预设，而且 OOM Killer 触发时系统已经处于严重内存不足的状态，响应往往又慢又粗暴。Android 需要一种更精细的机制：在内存还没耗尽之前，就根据 App 对用户的"重要程度"有序地回收进程，保证前台体验不受影响。

这就是 Low Memory Killer（LMK）存在的意义。它不是一个简单的"内存不够就杀进程"的工具，而是一套根据 Android 应用生命周期设计的分级回收策略——先杀谁、后杀谁、什么条件下才杀前台 App，都有明确的规则。

## 从内核模块到用户空间守护进程的演进

### 第一代：in-kernel LowMemoryKiller

早期的 Android（从 Android 1.0 到大约 Android 8）使用的是一个内核驱动 `drivers/staging/android/lowmemorykiller.c`。它的工作方式很直接：

系统启动时，`init` 进程会向 `/sys/module/lowmemorykiller/parameters/minfree` 写入一组内存阈值（例如 `18432,23040,27648,32256,36864,46080`，单位是页），同时向 `adj` 写入对应的 `oom_adj` 值。当系统空闲内存低于某个阈值时，内核遍历所有进程，找到 `oom_adj` 值最大的（即优先级最低的）进程，发送 `SIGKILL` 信号将其杀死。

[已验证: AOSP android-4.0.1_r1, drivers/staging/android/lowmemorykiller.c]

这套机制简单有效，但有几个根本性问题：

**内核不了解 Android 语义。** `ActivityManagerService`（AMS）知道哪个 App 是前台 App、哪个在播放音乐、哪个只是缓存的后台进程——但内核不知道。它只能看 `oom_adj` 这个数字，无法理解背后的语义。这意味着内核端的 LMK 只能做一个"按数字排序后杀最大值"的简单操作，无法实现更智能的策略。

**与 Linux 自身 OOM Killer 功能重叠。** Linux 内核已经有自己的 OOM Killer，两者在内存极度紧张时可能产生冲突——两个 Killer 同时工作，可能杀死过多进程。

**策略不灵活。** minfree 阈值是写死的，无法根据运行时情况动态调整。遇到内存抖动（短时间内频繁低于和高于阈值），内核 LMK 可能在短时间内反复杀进程又停止，造成性能抖动。

**被移出主线内核。** 随着 Linux 内核社区对代码质量要求的提高，这个 Android 特有的驱动在 Linux 4.12 中被正式移除。这也推动了 Android 向用户空间方案迁移。

### 第二代：用户空间 lmkd

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd]

从 Android 9（Pie）开始，Google 引入了用户空间的 `lmkd`（Low Memory Killer Daemon）。它的源码位于 `system/memory/lmkd/`，作为 `init` 启动的一个守护进程运行。

`lmkd` 的核心思路是：**把杀进程的决策权从内核搬回用户空间，让 AMS 的进程优先级信息能更直接地参与决策。** 具体来说：

AMS 在调整进程优先级时，通过 `/proc/<pid>/oom_score_adj` 文件将最新的优先级写入内核。`lmkd` 则通过内核提供的内存压力信号来判断何时需要杀进程。两者通过 `/proc` 文件系统实现信息共享，不需要额外的 Binder 调用。

相比内核 LMK，`lmkd` 有几个关键优势：

- **策略可编程**：用户空间的 C 代码比内核驱动更容易修改和升级，OEM 也可以根据自己的设备特点定制策略
- **更丰富的信息**：`lmkd` 可以读取 `/proc/meminfo`、`/proc/zoneinfo` 等内核导出的详细内存信息，做出更精确的判断
- **不依赖内核版本**：`lmkd` 使用的是标准的 Linux 内核接口（PSI、meminfo 等），不需要特定的内核补丁

[已验证: 官方文档, Android 10+ lmkd 使用 PSI monitors 作为默认内存压力检测机制]

## oom_score_adj：进程优先级的量化标尺

### 从 oom_adj 到 oom_score_adj

Linux 内核有两个 OOM 相关的进程调整值：

- **`oom_adj`**：老的接口，取值范围 -17 到 15，Android 早期版本使用
- **`oom_score_adj`**：新的接口，取值范围 -1000 到 1000，Android 从 API 17 开始使用

`oom_score_adj` 是 `oom_adj` 的更精细版本。Android 内部使用一套 `_ADJ` 常量来定义进程优先级，然后通过 `ProcessList.java` 将这些常量映射为 `/proc/<pid>/oom_score_adj` 的值。

[已验证: AOSP frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

### 进程优先级层次

我们来看 AMS 为不同状态进程分配的 `oom_score_adj` 值。理解这个层次结构，是理解 LMK 杀进程顺序的关键。

[图：进程优先级层次图，从上到下为 NATIVE(-1000) → SYSTEM(-900) → PERSISTENT(-800) → FOREGROUND(0) → VISIBLE(100) → PERCEPTIBLE(200) → BACKUP(300) → HEAVY_WEIGHT(400) → SERVICE(500) → HOME(600) → PREVIOUS(700) → SERVICE_B(800) → CACHED(900)]

**不会被杀的层级（oom_score_adj < 0）：**

- **NATIVE_ADJ（-1000）**：纯 Native 进程，不在 AMS 管理范围内。比如 `lmkd` 自身就运行在这个优先级——杀进程的守护进程不能把自己杀了。
- **SYSTEM_ADJ（-900）**：`system_server` 进程。杀死它等于让整个 Android Framework 停摆。
- **PERSISTENT_PROC_ADJ（-800）**：在 Manifest 中声明了 `android:persistent="true"` 的进程。通常是电话、系统 UI 等核心服务。

**尽量不杀的层级（0 到 200）：**

- **FOREGROUND_APP_ADJ（0）**：当前正在与用户交互的 App。杀掉它等于 App 崩溃，用户体验直接受损。
- **VISIBLE_APP_ADJ（100）**：Activity 可见但不在前台。比如当前 App 上弹了一个透明 Dialog，下面的 Activity 所在进程就是这个级别。
- **PERCEPTIBLE_APP_ADJ（200）**：用户能感知到但看不到界面的进程。最典型的例子是后台播放音乐的 App。杀掉它用户会立刻发现（音乐停了），所以优先级比一般后台进程高。

**可以被杀的层级（300 到 900）：**

- **BACKUP_APP_ADJ（300）**：正在执行备份操作的进程。被杀了损失不大，下次可以重新备份。
- **HEAVY_WEIGHT_ADJ（400）**：重量级进程，通常是用户明确通过通知栏设置为"不被优化"的 App。
- **SERVICE_ADJ（500）**：运行着后台 Service 的进程。
- **HOME_APP_ADJ（600）**：桌面（Launcher）进程。虽然不在前台，但用户按 Home 键会立刻用到。
- **PREVIOUS_APP_ADJ（700）**：上一个使用的 App。保留它可以让用户快速切回去。
- **SERVICE_B_ADJ（800）**：较旧的 Service 进程，Activity 已经不在了。
- **CACHED_APP_MIN_ADJ 到 CACHED_APP_MAX_ADJ（900-999）**：缓存进程，只保留了 Activity 状态。这些是最先被杀的候选者。

> **注意：** 以上数值基于 AOSP `ProcessList.java` 中的常量定义，不同 Android 版本和 OEM 厂商可能有微调。[待验证: OEM 厂商通常调整哪些 oom_score_adj 值]

### AMS 如何动态调整优先级

进程的 `oom_score_adj` 不是固定不变的。AMS 在以下事件中会重新计算并更新：

1. **Activity 切换**：当用户从 App A 切换到 App B，A 从 FOREGROUND 变为 PREVIOUS，B 从 BACKGROUND 变为 FOREGROUND
2. **Service 启停**：启动一个后台 Service 会把进程提升到 SERVICE_ADJ
3. **前台 Service**：启动前台 Service（带通知栏）会把进程提升到 PERCEPTIBLE_ADJ
4. **ContentProvider 访问**：如果进程中的 ContentProvider 正在被前台 App 访问，进程优先级会被临时提升

[已验证: AOSP frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

这套动态调整机制的精妙之处在于：它把"对用户的重要性"这个主观概念，转化为了一个 0-1000 的数字。而 `lmkd` 只需要根据这个数字做排序，就能决定先杀谁。

## lmkd 的杀进程策略

### 两种工作模式

`lmkd` 有两种主要的内存压力检测模式：

**传统模式（minfree 阈值模式）：**

当属性 `ro.lmk.use_minfree_levels=true` 时，`lmkd` 使用类似旧内核 LMK 的逻辑：配置一组 `(minfree, oom_adj)` 对，当空闲内存低于某个 `minfree` 值时，杀掉 `oom_adj` 大于等于对应阈值的进程。

```
# 典型的 minfree 配置（单位：页）
# minfree         oom_adj
18432  0         # 约 72MB，杀 CACHED 进程
23040  100       # 约 90MB，杀 VISIBLE 以下的进程
27648  200       # 约 108MB，杀 PERCEPTIBLE 以下的进程
```

这种方式简单直接，但阈值是固定的，无法反映实际的内存压力程度——有时候空闲内存低是因为缓存了大量文件页（这是正常的），不需要杀进程。

**现代模式（PSI 驱动模式）：**

从 Android 10 开始，`lmkd` 默认使用 PSI（Pressure Stall Information）作为内存压力信号。

### PSI：更精准的内存压力度量

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd — PSI 监控机制说明]

PSI 是 Linux 内核在 4.20（主线合入）中引入的一个机制，Android 将其 backport 到了 4.9 和 4.14 内核。它的核心理念是：**不要看空闲内存有多少，而要看有多少任务因为内存不足而被阻塞了。**

内核为每种内存资源（memory, CPU, IO）提供两个级别的 Stall 信号：

- **`some`**：至少有一个任务因资源不足而等待
- **`full`**：所有任务都在因资源不足而等待（这是最严重的状态）

`lmkd` 关注的是 memory 的 `some` 和 `full` 信号：

- **`memory.some`**：部分进程因内存分配而等待（Page Fault 需要换入、需要回收内存页等）。这表示系统开始感到内存压力。
- **`memory.full`**：所有进程都在等待内存。这意味着系统已经严重缺乏可用内存，可能影响前台 App 的响应。

`lmkd` 通过两个属性来配置 PSI 阈值：

- **`ro.lmk.psi_partial_stall_ms`**（默认 70ms）：在时间窗口内，如果 `memory.some` 的 stall 时间累计超过这个值，触发"中等"内存压力
- **`ro.lmk.psi_complete_stall_ms`**（默认 70ms）：`memory.full` 的 stall 时间累计超过这个值，触发"严重"内存压力

[已验证: AOSP system/memory/lmkd/lmkd.cpp]

PSI 相比旧版 `vmpressure` 信号有本质区别。`vmpressure` 基于内存回收事件的数量来判断压力，但它经常产生误报——内核正常的后台内存回收也会触发信号，导致 `lmkd` 在没有真正压力时就启动杀进程。PSI 则直接度量了"任务被阻塞了多久"，这是一个更直接、更准确的压力指标。

> **为什么 PSI 更好？** 想象一个类比：`vmpressure` 相当于看"垃圾桶被清空的次数"来判断是否需要做大扫除——日常清理也会触发。而 PSI 相当于看"有多少人因为找不到东西而等待"——只有真正影响使用时才会报警。

### 杀进程的执行流程

当 PSI 信号触发后，`lmkd` 按以下步骤执行：

**第一步：确定压力级别。** 根据 PSI 信号区分"中等"和"严重"两个级别。

**第二步：选择目标 oom_adj 阈值。**
- 中等压力：使用 `ro.lmk.low`（默认 1001，即不杀任何进程）配置的最低 oom_adj
- 严重压力：使用 `ro.lmk.critical`（默认 0）配置的最低 oom_adj

**第三步：遍历进程列表。** `lmkd` 从 `/proc` 读取所有进程的 `oom_score_adj`，按值从大到小排序。

**第四步：选择并杀死进程。** 在满足 oom_adj 阈值要求的进程中，选择 `oom_score_adj` 最大的（优先级最低的）进程，调用 `kill(pid, SIGKILL)`。

**第五步：等待并评估。** 杀死一个进程后等待一小段时间，检查 PSI 信号是否缓解。如果仍然有压力，继续杀下一个优先级最低的进程。

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd]

### 低内存设备（Android Go）的特殊策略

对于配置了 `ro.config.low_ram=true` 的低内存设备（通常 RAM <= 2GB），`lmkd` 会使用更激进的策略：

- 更低的 PSI 阈值，更早开始杀进程
- 同时考虑 Swap 使用率（如果启用了 ZRAM）
- 杀进程时一次可能杀掉多个，而不是一次一个

[已验证: AOSP system/memory/lmkd/lmkd.cpp — use_low_mem_swap preset logic]

## LMK 在性能问题中的角色

### 频繁 Kill 的连锁反应

理解 LMK 对性能分析至关重要，因为 LMK 的行为直接决定了用户能感知到的卡顿来源。问题通常不是"LMK 杀错了进程"，而是"LMK 不得不频繁杀进程"——这意味着系统整体内存不足。

当一个缓存 App 被 LMK 杀死后，如果用户切回这个 App，系统必须重新走完整的冷启动流程：Zygote fork → 加载 APK → 初始化 Application → 创建 Activity → 布局渲染。这个过程可能需要数百毫秒甚至数秒，远比从缓存中恢复（通常 < 100ms）慢得多。

连锁反应是这样的：

1. 系统内存不足 → LMK 杀掉后台 App
2. 用户切回被杀的 App → 冷启动，耗费大量 CPU 和 I/O
3. 冷启动过程中大量内存分配 → 加剧内存压力
4. 内存压力再次触发 LMK → 又杀掉其他后台 App
5. 循环往复

在 Perfetto 中，这种模式表现为：你会在 System Trace 中看到 `lmkd` 进程频繁活动（kill 事件密集出现），同时在 App 进程中看到大量的冷启动 pattern（Zygote fork → ActivityThread.main → Activity.onCreate）。

### 如何判断 LMK 是否在影响你的 App

如果你怀疑 LMK 在杀死你的后台进程，可以通过以下方法确认：

**方法一：logcat 过滤**

```bash
adb logcat | grep "lmkd"
```

`lmkd` 在杀死进程时会输出日志，包含被杀进程的 PID、oom_score_adj 值和释放的内存大小。

**方法二：dumpsys meminfo**

```bash
adb shell dumpsys meminfo --checkin
```

查看系统整体内存使用情况。如果 `Cached` 和 `Free` 的值持续很低，说明系统处于内存紧张状态。

**方法三：Perfetto Trace**

在 Perfetto 中抓取 trace 时，确保包含 `meminfo` 和 `lmkd` 相关的 ftrace 事件。在 Perfetto UI 中，你可以在 `lmkd` track 上看到每次杀进程的记录，鼠标悬停可以看到被杀进程的详细信息。

[图：Perfetto 中 lmkd track 的示例，标注 kill 事件、被杀进程名、oom_score_adj 值]

**方法四：Process Lifecycle 监控**

在 App 中注册 `ActivityManager.OnTrimMemory` 回调。当系统回调 `TRIM_MEMORY_UI_HIDDEN` 或更低级别时，说明系统正在要求 App 释放内存——这通常是 LMK 即将行动的前兆。

```java
// ComponentCallbacks2 的 onTrimMemory 回调级别
TRIM_MEMORY_UI_HIDDEN       = 20  // UI 不可见，可以释放 UI 资源
TRIM_MEMORY_RUNNING_LOW     = 10  // 内存开始紧张
TRIM_MEMORY_RUNNING_CRITICAL = 15 // 内存严重紧张
TRIM_MEMORY_MODERATE        = 60  // 进程在 LRU 列表中间，可能被杀
TRIM_MEMORY_COMPLETE        = 80  // 进程即将被杀，释放一切可以释放的
```

[已验证: 官方文档, developer.android.com/reference/android/content/ComponentCallbacks2]

### 常见误区

**误区一："我的 App 在前台被杀了，是 LMK 的锅。"**

不太可能。前台 App 的 `oom_score_adj` 为 0，是最低可杀级别。`lmkd` 只有在极端的 `critical` 压力下才会杀 `oom_score_adj` 为 0 的进程，而且默认配置下 `ro.lmk.critical` 就是为保护前台 App 而设的。前台 App 被杀更可能是：

- App 自身 crash（看 logcat 中的 FATAL EXCEPTION）
- 系统级 ANR（看 logcat 中的 "ANR in" 日志）
- Native crash（看 tombstone 文件）

**误区二："后台 Service 不会被杀。"**

错误。普通后台 Service 的进程优先级是 `SERVICE_ADJ（500）`，远高于 CACHED 进程但仍是可杀的。如果你的 Service 需要长时间运行且不应该被杀，需要：

- 使用前台 Service（`startForeground()`），这会将进程提升到 `PERCEPTIBLE_ADJ（200）`
- 或者使用 WorkManager，它会在被杀后自动重新调度

**误区三："lmkd 只杀后台 App。"**

不完全正确。在极端内存压力下，`lmkd` 可能会按照优先级顺序一路杀上去，甚至杀掉 SERVICE 级别的进程。但在默认配置下，它确实会优先杀 CACHED 进程（`oom_score_adj >= 900`），只在 CACHED 进程全部被杀后才会升级到更高优先级的进程。

## 扩展一：通过 Perfetto 观察 lmkd 行为

在 Perfetto 中观察 LMK 行为是一个高级但非常有用的分析方法。具体操作如下：

**抓取配置：** 确保你的 Perfetto 配置包含以下数据源：

```
# 在 trace config 中添加
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_events: "lowmemorykiller/lowmemory_kill"
    }
}
data_sources: {
    config {
        name: "linux.sys_stats"
        meminfo_period_ms: 100
    }
}
```

[已验证: Perfetto 官方文档, perfetto.dev — ftrace 配置说明]

**在 Perfetto UI 中的表现：**

当你打开 trace 文件后，在进程列表中找到 `lmkd` 进程。它的 track 上会出现一些短暂的 CPU 活动尖峰——每次尖峰对应一次杀进程操作。

你可以在 `lmkd` track 上看到具体的事件，包含被杀进程的 PID。将这个 PID 与同一 trace 中的进程对应，你就能知道是哪个 App 被杀了。

同时观察 `meminfo` track（通常在 System Stats 下面），你可以看到 `MemFree` 和 `MemAvailable` 的变化趋势。如果这两个值持续走低然后突然上升（因为 LMK 杀了进程释放了内存），这就是典型的 LMK 干预模式。

**关联分析技巧：**

- 将 LMK kill 事件与前台 App 的冷启动时间关联：如果你看到 LMK kill 后紧接着某个 App 的 Activity.onCreate，说明用户切回了一个被杀的 App
- 将 LMK 活动频率与系统整体内存趋势关联：如果 `MemAvailable` 长期低于某个值（通常 500MB 以下），LMK 会非常活跃
- 对比 kill 前后的 `Cached` 内存值：如果 kill 后 Cached 值大幅下降，说明系统确实需要这些内存

[待补充: Perfetto 截图 — 展示 lmkd kill 事件与 meminfo 变化的关联]

## 扩展二：各厂商对 lmkd 的定制化策略

由于 `lmkd` 运行在用户空间，OEM 厂商可以根据自己设备的硬件配置定制杀进程策略。常见的定制包括：

**调整 oom_adj 杀进程阈值：** 通过 `ro.lmk.low`、`ro.lmk.medium`、`ro.lmk.critical` 属性配置。内存更大的设备可以设置更保守的阈值（允许更多后台 App 存活），而低内存设备需要更激进的阈值。

**自定义 minfree 级别：** 即使在 PSI 模式下，`lmkd` 也可能回退到 minfree 模式。OEM 会根据设备 RAM 大小调整 `sys.lmk.minfree_levels`。

**特定进程白名单：** 一些厂商会在 init.rc 中通过 `write /proc/<pid>/oom_score_adj -1000` 来保护特定的系统进程。

**大小核感知：** 部分 SoC 厂商（如 MTK）会在 lmkd 中加入对 CPU topology 的感知——在大核上执行杀进程操作以减少延迟。

[待验证: 以上 OEM 定制策略来自公开技术分享，具体实现因厂商而异]

## 扩展三：Android 15/16 的变化

### Android 15：16KB Page Size

Android 15 引入了对 16KB 内存页的支持（传统为 4KB）。这不会直接改变 `lmkd` 的杀进程策略，但会影响内存管理的整体格局：

- **TLB 压力降低**：更大的页意味着更少的 TLB entry，减少 Page Table Walk 的开销
- **App 冷启动加速**：Google 声称冷启动速度提升 20%-40%
- **内存效率**：更大的页减少了页表本身占用的内存，但可能导致内部碎片增加（小对象也需要占用 16KB 页）

[已验证: 官方文档, developer.android.com — 16KB Page Size 说明]

这意味着在 16KB 页模式下，虽然单个进程的内存开销可能略有增加，但系统整体性能的改善（尤其是冷启动速度）可以缓解 LMK 频繁杀进程带来的用户体验问题。

### Android 16：lmkd 配置属性的标准化

Android 16 对 `lmkd` 本身没有引入重大的算法变更，但系统在属性配置方面进行了标准化：

- `sys.lmk.minfree_levels`：标准化的 minfree-to-oom_adj_score 配对属性
- `sys.lmk.reportkills`：标识设备是否支持向客户端报告进程 kill 事件

[已验证: AOSP android-16.0.0_r2, system/memory/lmkd/]

更重要的是，Android 16 在系统层面的内存优化（如 16KB 页的进一步推广、ART 分配器的改进）减少了 `lmkd` 需要介入的频率。当系统整体内存效率提升后，自然就不需要那么频繁地杀后台进程了。

## 参考资料

### AOSP 源码
- `system/memory/lmkd/` — lmkd 守护进程源码
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java` — oom_adj 常量定义
- `frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java` — 优先级动态调整逻辑
- `frameworks/base/core/java/android/app/ActivityManager.java` — OnTrimMemory 回调定义

### 官方文档
- [lmkd — source.android.com](https://source.android.com/docs/core/perf/lmkd)
- [Memory Management — developer.android.com](https://developer.android.com/topic/performance/memory)
- [16KB Page Size — developer.android.com](https://developer.android.com/guide/practices/page-sizes)

### 技术博客
- [Userspace lmkd — Android Developers Blog](https://android-developers.googleblog.com/2020/07/lmkd-userspace-low-memory-killer-daemon.html)
- [PSI in the Android Ecosystem — LPC 2019](https://lpc.events/2019/slides.html)

### 交叉引用
- 本章 4.1 节「Android 内存模型全景」— 系统内存组成和度量方法
- 本章 4.3 节「ART 虚拟机内存管理」— Java 堆的内存分配与回收
- 第 1 章第 3 节「进程模型与生命周期管理」— 进程优先级的生命周期管理
- 第 10 章第 4 节「低内存对系统性能的影响」— 低内存场景的深度分析
