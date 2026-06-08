---

status: finalized
title: Low Memory Killer
section: 4.4
chapter: 4.4
drafted_date: 2026-03-31
reviewed_date: 2026-05-10
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: reviewed  # updated by task2b-verifier 2026-06-08last_task6_audit: 2026-05-21
last_task6_audit_log: logs/review/2026-05-21-21-audit.md
last_task6_at: 2026-05-21T21:06:00+08:00
task9_state: reviewed
pipeline_stage: ready-to-publish  # promoted by task2b-verifier 2026-06-08polish_count: 1
polish_date: 2026-04-05
polish_by: task2b-polish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: 2026-05-09
last_verified_against: AOSP android-4.0.1_r1 init.rc/ProcessList.java, android-8.1
confidence: medium-high
sources: 
tags: 
related_chapters: 
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
task9_reviewed_date: 2026-06-08
task9_reviewed_by: openclaw-task9
last_task9_at: 2026-06-08T22:20:00+08:00
review_notes: 2026-04-27 task2b: 修复 Task9 P0/P1 与 external P1；校正旧 LMK 初始化、userspace
last_task9_autofix_at: 2026-06-08
last_task2b_at: 2026-06-08T21:06:43+08:00
task2b_fixed_by: openclaw-task2b
repaired_date: 2026-04-27
repaired_by: openclaw-task2b
---



# Low Memory Killer

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 LMK 的设计目标：在内存不足时有序释放进程
- 🔹 传统 LowMemoryKiller（内核模块）→ lmkd（用户空间守护进程）的演进
- 🔹 oom_score_adj 与进程优先级的映射关系
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

这就是 Low Memory Killer（LMK）存在的意义。LMK 是一套根据 Android 应用生命周期设计的分级回收策略——先杀谁、后杀谁、什么条件下才杀前台 App，都有明确的规则。

## 从内核模块到用户空间守护进程的演进

### 第一代：in-kernel LowMemoryKiller

早期的 Android（从 Android 1.0 到大约 Android 8）使用的是一个内核驱动 `drivers/staging/android/lowmemorykiller.c`。它的工作方式很直接：

系统启动时，`init.rc` 只把 `/sys/module/lowmemorykiller/parameters/{adj,minfree}` 的 owner 和权限交给 `system`。实际阈值不由 init 写入，而是由 `frameworks/base/services/.../ProcessList.java` 根据设备内存和屏幕尺寸计算，再通过 `updateOomLevels()` / `writeFile()` 写入 `adj` 和 `minfree`。当系统空闲内存低于某个阈值时，内核模块遍历进程，按候选门槛选择 `oom_adj` 较高的进程并发送 `SIGKILL`。

[已验证: AOSP android-4.0.1_r1, system/core/rootdir/init.rc]
[已验证: AOSP android-4.0.1_r1, frameworks/base/services/java/com/android/server/am/ProcessList.java]
[已验证: AOSP android-4.0.1_r1, drivers/staging/android/lowmemorykiller.c]

这套机制简单有效，但有几个根本性问题：

**内核不了解 Android 语义。** `ActivityManagerService`（AMS）知道哪个 App 是前台 App、哪个在播放音乐、哪个只是缓存的后台进程——但内核不知道。它只能看 `oom_adj` 这个数字，无法理解背后的语义。内核端的 LMK 只能做一个"按数字排序后杀最大值"的简单操作，无法实现更智能的策略。

**与 Linux 自身 OOM Killer 功能重叠。** Linux 内核已经有自己的 OOM Killer，两者在内存极度紧张时可能产生冲突——两个 Killer 同时工作，可能杀死过多进程。

**策略不灵活。** minfree 阈值是写死的，无法根据运行时情况动态调整。遇到内存抖动（短时间内频繁低于和高于阈值），内核 LMK 可能在短时间内反复杀进程又停止，造成性能抖动。

**被移出主线内核。** 随着 Linux 内核社区对代码质量要求的提高，这个 Android 特有的驱动在 Linux 4.12 中被正式移除。这也推动了 Android 向用户空间方案迁移。

### 第二代：用户空间 lmkd

[已验证: 官方文档, source.android.com/docs/core/perf/lmkd]

Android 8.1 已经出现 userspace `lmkd` 及控制 socket，`ProcessList.java` 包含 `LMK_TARGET`、`LMK_PROCPRIO`、`LMK_PROCREMOVE` 三类命令。Android 9/10 之后，userspace `lmkd` 逐步成为主路径；Android 10+ 默认使用 PSI monitors 作为内存压力检测机制。新版本源码位于 `system/memory/lmkd/`，旧版本在 `system/core/lmkd/`。

`lmkd` 的设计是把杀进程的决策权从内核搬回用户空间，让 AMS 的进程优先级信息能更直接地参与决策。具体来说：

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

AMS 为不同状态进程分配的 `oom_score_adj` 值如下。理解这个层次结构，是理解 LMK 杀进程顺序的关键。

[图：进程优先级层次图，从上到下为 NATIVE(-1000) → SYSTEM(-900) → PERSISTENT(-800) → FOREGROUND(0) → VISIBLE(100) → PERCEPTIBLE(200) → BACKUP(300) → HEAVY_WEIGHT(400) → SERVICE(500) → HOME(600) → PREVIOUS(700) → SERVICE_B(800) → CACHED(900)]

**不会被杀的层级（oom_score_adj < 0）：**

- **NATIVE_ADJ（-1000）**：AMS 对"不由系统管理、没有 AMS 分配 oom adj 的 native 进程"的内部分类/打印值，定义在 `ProcessList.java` 中。这类进程不受 AMS 优先级调整，AMS 仅为其赋 `NATIVE_ADJ` 作为内部记值。`lmkd` 的保护依赖于 init 进程的 service 管理机制（`lmkd.rc` 中声明），而非依赖 oom_score_adj 值防止被杀。
- **SYSTEM_ADJ（-900）**：`system_server` 进程。杀死它等于让整个 Android Framework 停摆。
- **PERSISTENT_PROC_ADJ（-800）**：在 Manifest 中声明了 `android:persistent="true"` 的进程。通常是电话、系统 UI 等核心服务。

**尽量不杀的层级（0 到 200）：**

- **FOREGROUND_APP_ADJ（0）**：当前正在与用户交互的 App。杀掉它等于 App 崩溃，用户体验直接受损。
- **VISIBLE_APP_ADJ（100）**：Activity 可见但不在前台。比如当前 App 上弹了一个透明 Dialog，下面的 Activity 所在进程就是这个级别。
- **PERCEPTIBLE_APP_ADJ（200）**：用户能感知到但看不到界面的进程。最典型的例子是后台播放音乐的 App。杀掉它用户会立刻发现（音乐停了），所以优先级比一般后台进程高。

**可以被杀的层级（300 到 900）：**

- **BACKUP_APP_ADJ（300）**：正在执行备份操作的进程。被杀了损失不大，下次可以重新备份。
- **HEAVY_WEIGHT_APP_ADJ（400）**：在 `<application>` 上声明 `android:cantSaveState="true"` 后，系统会设置 `ApplicationInfo.PRIVATE_FLAG_CANT_SAVE_STATE`。AMS / ATMS 根据这个 flag 把对应 package 作为 heavy-weight process 处理，`ProcessList` 再把这类进程映射到 `HEAVY_WEIGHT_APP_ADJ`。电池优化白名单和前台服务通知属于另一组机制。
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

这套机制把"对用户的重要性"这个主观概念，转化为 `-1000` 到 `1000` 的数字。负值段通常留给 native、system、persistent 等高优先级进程；`lmkd` 的常规候选多从非负段开始，并优先从 `oom_score_adj` 较高的 cached/service B/previous 进程中选择目标。

## lmkd 的杀进程策略

### 两种工作模式

`lmkd` 有两种主要的内存压力检测模式：

**传统模式（minfree 阈值模式）：**

当属性 `ro.lmk.use_minfree_levels=true` 时，`lmkd` 使用类似旧内核 LMK 的逻辑：配置一组 `(minfree, min_adj)` 对。当空闲内存低于某个 `minfree` 值时，候选门槛降到对应 `min_adj`，再从 `oom_score_adj >= min_adj` 的进程里挑目标。

```text
# ProcessList 生成的 6 档语义（Android 8.1 低端设备基线，minfree 以 KB 表示）
# minfree_kb: 12288, 18432, 24576, 36864, 43008, 49152
# min_adj:       0,   100,   200,   300,   900, CACHED_APP_MAX_ADJ
# 含义:      FOREGROUND, VISIBLE, PERCEPTIBLE, BACKUP, CACHED_MIN, CACHED_MAX
```

`min_adj=0` 表示候选范围已经下探到 `FOREGROUND_APP_ADJ` 及其以下优先级的所有进程。cached 进程通常落在 `oom_score_adj` 900 及以上，因此 cached 档应对应 `CACHED_APP_MIN_ADJ` / `CACHED_APP_MAX_ADJ`。

这种方式阈值固定，无法反映实际内存压力程度。有时空闲内存低是因为文件页缓存较多，并不需要杀进程。

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
- **`memory.full`**：所有进程都在等待内存。系统已经严重缺乏可用内存，前台 App 的响应也会受到影响。

`lmkd` 的 PSI 阈值配置存在版本差异：

- **Android 10**：PSI 阈值硬编码在 `lmkd.c` 中，`psi_thresholds` 数组为 some=70ms / some=100ms / full=70ms，不支持通过系统属性调整
- **Android 11+**：引入 `ro.lmk.psi_partial_stall_ms`（默认 70ms）和 `ro.lmk.psi_complete_stall_ms`（默认 700ms）属性。低内存设备（`ro.config.low_ram=true`）的 partial stall 默认值为 200ms。AOSP `lmkd.cpp` 中定义为 `DEF_PARTIAL_STALL=70`、`DEF_COMPLETE_STALL=700`

[已验证: AOSP android-10.0.0_r1 system/core/lmkd/lmkd.c 硬编码阈值; android-11.0.0_r1 system/memory/lmkd/lmkd.cpp DEF_PARTIAL_STALL/DEF_COMPLETE_STALL]

PSI 相比旧版 `vmpressure` 信号有本质区别。`vmpressure` 基于内存回收事件的数量来判断压力，但它经常产生误报——内核正常的后台内存回收也会触发信号，导致 `lmkd` 在没有真正压力时就启动杀进程。PSI 则直接度量了"任务被阻塞了多久"，这是一个更直接、更准确的压力指标。

> **为什么 PSI 更好？** 想象一个类比：`vmpressure` 相当于看"垃圾桶被清空的次数"来判断是否需要做大扫除——日常清理也会触发。而 PSI 相当于看"有多少人因为找不到东西而等待"——只有真正影响使用时才会报警。

### 杀进程的执行流程

`lmkd` 的执行流程要分成两条路径看。

**legacy vmpressure / minfree 路径。** 如果设备关闭了 PSI，或者显式设置 `ro.lmk.use_minfree_levels=true`，`lmkd` 会按 `ro.lmk.low`、`ro.lmk.medium`、`ro.lmk.critical` 和 minfree 档位工作。这条路径和旧版内核 LMK 接近，内存水位跌破阈值后，再按 `oom_score_adj` 选择候选进程。

**Android 10+ 的 PSI 路径。** PSI 事件只是入口，不直接等价于“切到 `ro.lmk.critical`”。AOSP `lmkd.cpp` 在收到 stall 信号后，还会继续看 watermark、file-backed page cache、workingset refault thrashing、swap 和可回收页状态。常规低内存场景下，候选门槛由 `ro.lmk.lowmem_min_oom_score` 控制，默认值是 `PREVIOUS_APP_ADJ + 1`，也就是从 cached app 开始。只有进入 `critical stall`，或者 thrashing / file cache 状态已经说明系统快失去前台响应能力时，门槛才会继续下探，最坏可以降到 `oom_score_adj = 0`。

门槛确定后，`lmkd` 仍然按 `oom_score_adj` 从高到低挑候选，优先回收 cached、service B、previous 这类进程。现代路径和旧路径的差别，不在“杀谁”，而在“什么条件下允许杀到哪一层”。

### userspace lmkd 的 kill 与回收流程

选定目标以后，Android 16 的 userspace `lmkd` 不只是调一次 `kill(pid, SIGKILL)`。AOSP 里实际走的是 `kill_one_process()` → `reaper.kill()`。`reaper` 线程先用 `pidfd_send_signal()` 发送 `SIGKILL`，再调用 `process_mrelease()` 促使内核尽快回收目标进程的匿名页和页表。

这段执行流程和性能分析直接相关。我们在 trace 里看到“进程已经收到 kill 信号”与“内存真正回到系统可用池”之间，可能还隔着一段 reclaim 延迟。判断 LMK 是否正在拖慢系统时，不能只盯着 kill 事件，也要看 kill 之后的内存回收速度。

[已验证: AOSP android-16.0.0_r1, system/memory/lmkd/lmkd.cpp + reaper.cpp]

### 低内存设备（Android Go）的特殊策略

对于配置了 `ro.config.low_ram=true` 的低内存设备（通常 RAM <= 2GB），`lmkd` 会把门槛设得更激进：

- 更低的 PSI / thrashing 阈值，更早开始回收后台进程
- 更依赖 swap 使用率、page cache 和 refault 情况来判断压力
- 单轮仍然只 kill one task，不会在一次决策里连续杀多个进程

AOSP android-16.0.0_r1 的 low-RAM 分支在 `do_kill` 处直接写了 `For Go devices kill only one task`。低内存设备和普通设备的差别，主要在阈值和压力判断，不在单轮 kill 的数量。

[已验证: AOSP android-16.0.0_r1, system/memory/lmkd/lmkd.cpp]

## LMK 在性能问题中的角色

### 频繁 Kill 的连锁反应

判断性能问题时，LMK 的行为必须纳入分析，因为它会直接改变用户感知到的卡顿来源。问题通常不是"LMK 杀错了进程"，而是"LMK 不得不频繁杀进程"，这类现象通常说明系统整体内存不足。

当一个缓存 App 被 LMK 杀死后，如果用户切回这个 App，系统必须重新走完整的冷启动流程：Zygote fork → 加载 APK → 初始化 Application → 创建 Activity → 布局渲染。这个过程可能需要数百毫秒甚至数秒，远比从缓存中恢复（通常 < 100ms）慢得多。

这个连锁反应是自我加剧的：LMK 杀掉后台 App 后，用户切回时触发冷启动，冷启动消耗大量 CPU 和 I/O，同时分配大量内存，这又加剧了内存压力，导致 LMK 再次行动。在重度使用场景下（比如用户频繁在多个 App 之间切换），这个循环会持续运转，系统整体性能螺旋式下降。

在 Perfetto 中，这种模式表现为：我们会在 System Trace 中看到 `lmkd` 进程频繁活动（kill 事件密集出现），同时在 App 进程中看到大量的冷启动 pattern（Zygote fork → ActivityThread.main → Activity.onCreate）。

### 如何判断 LMK 是否在影响 App

如果我们怀疑 LMK 在杀死后台进程，可以通过以下方法确认：

最直接的确认方式是查看 logcat。`lmkd` 在杀死进程时会输出日志，包含被杀进程的 PID、oom_score_adj 值和释放的内存大小：

```bash
adb logcat | grep "lmkd"
```

如果想了解系统整体的内存水位，可以用 `dumpsys meminfo` 查看详情。如果输出中 `Cached` 和 `Free` 的值持续很低，说明系统处于内存紧张状态：

```bash
adb shell dumpsys meminfo --checkin
```

更精确的分析要先分实现路径。旧版 in-kernel LMK 可以抓 `lowmemorykiller/lowmemory_kill`；Android 9+ 的 userspace `lmkd` 更适合抓 `atrace_apps: "lmkd"` 配合 `linux.sys_stats`。如果设备没有打开 `LMKD_TRACE_KILLS`，我们再回退到 logcat、statsd 和 `dumpsys meminfo` 联合判断。

[图：Perfetto 中 lmkd track 的示例，标注 kill 事件、被杀进程名、oom_score_adj 值]

在 App 侧，我们能接到的入口是 `ComponentCallbacks2.onTrimMemory(int)`，常见实现位置是 `Application#onTrimMemory()` 或自定义 `ComponentCallbacks2`。

```java
import android.app.Application;
import android.content.ComponentCallbacks2;

public final class App extends Application {
    @Override
    public void onTrimMemory(int level) {
        if (level == ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN) {
            // 释放 UI 相关缓存
        }
    }
}
```

这里要把两类信号分开看。`TRIM_MEMORY_UI_HIDDEN` 只表示界面已经不可见，适合释放 Bitmap、Adapter、Surface 等 UI 资源。它不等价于“LMK 马上要杀进程”。

历史上 `TRIM_MEMORY_RUNNING_LOW`、`TRIM_MEMORY_RUNNING_CRITICAL`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 代表更强的内存压力。但从 Android 14 / API 34 开始，App 已经收不到这些级别。现代版本里，如果我们想确认 LMK 是否真的发生过，更可靠的证据来自 logcat、Perfetto、statsd 和进程是否被冷启动，而不是 trim callback 本身。

[已验证: developer.android.com/reference/android/content/ComponentCallbacks2]

### 常见误区

**误区一："我的 App 在前台被杀了，是 LMK 的锅。"**

不太可能。前台 App 的 `oom_score_adj` 为 0，是最低可杀级别。常规路径会先从 cached、service B、previous 这类进程开始回收，只有 `critical stall` 等极端条件下才可能下探到 `oom_score_adj = 0`。前台 App 被杀更常见的原因是：

- App 自身 crash（看 logcat 中的 FATAL EXCEPTION）
- 系统级 ANR（看 logcat 中的 "ANR in" 日志）
- Native crash（看 tombstone 文件）

**误区二："后台 Service 不会被杀。"**

这是一个常见的误解。普通后台 Service 的进程优先级是 `SERVICE_ADJ（500）`，远高于 CACHED 进程但仍是可杀的。如果 Service 需要长时间运行且不应该被杀，需要：

- 使用前台 Service（`startForeground()`），这会将进程提升到 `PERCEPTIBLE_ADJ（200）`
- 或者使用 WorkManager，它会在被杀后自动重新调度

**误区三："lmkd 只杀后台 App。"**

不完全正确。在极端内存压力下，`lmkd` 可能会按照优先级顺序一路杀上去，甚至杀掉 SERVICE 级别的进程。但在默认配置下，它确实会优先杀 CACHED 进程（`oom_score_adj >= 900`），只在 CACHED 进程全部被杀后才会升级到更高优先级的进程。

## 扩展一：通过 Perfetto 观察 lmkd 行为

Perfetto 这里也要分两条路径看。

**in-kernel LMK（旧路径）。** 如果分析的是早期 Android 或特定 legacy 内核，`lowmemorykiller/lowmemory_kill` 这个 ftrace event 仍然有用。它直接对应旧版 kernel LMK driver。

**userspace `lmkd`（Android 9+ 主路径）。** 现代设备的主路径是 userspace `lmkd`。AOSP android-16 的 `lmkd.cpp` 在打开 `LMKD_TRACE_KILLS` 时会通过 ATrace 记录 kill span，所以更稳妥的抓法是把 `lmkd` 纳入 atrace app 列表，再配合 `linux.sys_stats` 观察 `MemAvailable`、`Cached`、`SwapFree` 这些系统指标。

```textproto
data_sources: {
  config {
    name: "linux.ftrace"
    atrace_apps: "lmkd"
  }
}
data_sources: {
  config {
    name: "linux.sys_stats"
    meminfo_period_ms: 100
  }
}
```

如果设备构建没有打开 `LMKD_TRACE_KILLS`，trace 里可能看不到 `lmkd` 的 kill slice。这种情况下，不要误判成“系统没有触发 LMK”，而应回退到 `adb logcat | grep lmkd`、statsd 事件和 `dumpsys meminfo` 联合判断。

在 Perfetto UI 里，我们通常把三样东西放在一起看：

- `lmkd` slice 或 kill 相关系统事件
- `MemAvailable`、`Cached`、`SwapFree` 的变化曲线
- 被杀 App 之后是否马上出现冷启动流程

如果 kill 之前已经出现长期的 thrashing、`MemAvailable` 下探，kill 之后内存短暂回升，随后用户回到某个 App 又触发冷启动，这就是 LMK 正在影响体验的典型模式。

可以用下面的 trace_processor SQL 做无截图复核。第一段找 `lmkd` 相关 slice，第二段把 meminfo counter 拉到同一时间轴；冷启动则在被杀包名后续的进程创建、`ActivityThread.main`、`bindApplication`、`Activity.onCreate` 附近确认。

```sql
-- lmkd / kill 相关 slice。不同构建的 slice 名可能不同，先用模糊匹配定位。
SELECT
  s.ts,
  s.dur,
  p.name AS process_name,
  t.name AS thread_name,
  s.name
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t ON tt.utid = t.utid
JOIN process p ON t.upid = p.upid
WHERE p.name = 'lmkd' OR s.name GLOB '*lmk*' OR s.name GLOB '*kill*'
ORDER BY s.ts;

-- MemAvailable / Cached / SwapFree 的同轴变化。
SELECT
  c.ts,
  ct.name,
  c.value
FROM counter c
JOIN counter_track ct ON c.track_id = ct.id
WHERE ct.name IN ('MemAvailable', 'Cached', 'SwapFree')
ORDER BY c.ts;
```

[已验证: AOSP android-16.0.0_r1, system/memory/lmkd/lmkd.cpp]
[已验证: Perfetto trace_processor SQL schema, `slice` / `counter` / `counter_track`]

## 扩展二：各厂商对 lmkd 的定制化策略

由于 `lmkd` 运行在用户空间，OEM 厂商可以根据自己设备的硬件配置定制杀进程策略。常见的定制包括：

**调整 kill 门槛与 thrashing 阈值：** legacy 路径常见 `ro.lmk.low`、`ro.lmk.medium`、`ro.lmk.critical`，PSI 路径更常见 `ro.lmk.lowmem_min_oom_score`、`ro.lmk.thrashing_limit` 和 swap 相关属性。不同 RAM 档位会配不同门槛。

**自定义 minfree 级别：** 如果设备显式启用 `ro.lmk.use_minfree_levels=true`，OEM 还会调整 `sys.lmk.minfree_levels`。

**特定进程白名单：** 一些厂商会在 init.rc 中通过 `write /proc/<pid>/oom_score_adj -1000` 来保护特定的系统进程。

**大小核感知：** 部分 SoC 厂商（如 MTK）会在 lmkd 中加入对 CPU topology 的感知——在大核上执行杀进程操作以减少延迟。

**高负载场景的激进清场：** 相机启动是典型的内存尖峰场景。主流 OEM 在相机启动时会将 `oom_score_adj >= 200`（PERCEPTIBLE 以上）的进程标记为强制回收目标，为相机进程预留约 1.5GB 内存。拍照完成后的合成进程通常有 30 秒以上的保护期，防止被 lmkd 误杀导致照片合成失败。这种场景化的激进策略不在 AOSP 默认配置中，是 OEM 根据硬件能力和相机内存需求单独调校的。

[待验证: 以上 OEM 相机场景策略来自公开技术分享，具体阈值因厂商而异]

[待验证: 以上 OEM 定制策略来自公开技术分享，具体实现因厂商而异]

## 扩展三：Android 15/16 的变化

### Android 15：16KB Page Size

Android 15 引入了对 16KB 内存页的支持（传统为 4KB）。这不会直接改变 `lmkd` 的杀进程策略，但会影响内存管理的整体格局：

- **TLB 压力降低**：更大的页意味着更少的 TLB entry，减少 Page Table Walk 的开销。
- **App 启动数据**：Android 官方 16KB Page Size 文档给出的公开数据是，在内存压力下 app launch 平均降低 3.16%，部分应用最高约 30%；camera cold start 平均降低 6.60%；系统 boot time 平均降低 8%，约 950ms。
- **内存效率**：更大的页减少页表本身占用，但可能带来内部碎片。小对象和小映射也会按 16KB 页粒度占用内存。

[已验证: 官方文档, developer.android.com — 16KB Page Size 说明；数据口径为 initial testing，actual devices may differ]

在 16KB 页模式下，单个进程的内存占用可能略有变化。分析 LMK 频繁触发时，应把页大小、页表占用、冷启动耗时和内存压力放在同一条时间线上看，应避免使用“启动一定提升 20%-40%”这种无来源数字下判断。

### Android 16：沿用 userspace lmkd + reaper 回收链

`sys.lmk.minfree_levels` 和 `sys.lmk.reportkills` 不是 Android 16 才出现的属性。它们在 Android 12-14 的 `lmkd.cpp` 里已经存在，所以不适合拿来当 Android 16 的版本里程碑。

对 Android 16 来说，和分析更相关的点是 userspace `lmkd` 路径已经稳定：PSI / thrashing / file cache 判断负责决定是否 kill，`reaper` 线程负责 `pidfd_send_signal()` + `process_mrelease()`。我们在 Android 16 设备上排查低内存卡顿时，重点应放在 kill 触发条件、kill 后 reclaim 延迟，以及 App 被杀后的冷启动连锁反应。

[已验证: AOSP android-12.0.0_r1 ~ android-16.0.0_r1, system/memory/lmkd/lmkd.cpp]

### Android 16/17：可验证边界与配额制

#### Android 16：桌面多窗场景的可见性边界

AOSP android-16.0.0_r1 的 `system/memory/lmkd/lmkd.cpp` 没有 HWC、Layer 或 Display 可见性输入，不能把“HWC 可见图层直接参与 lmkd kill 决策”写成 AOSP 默认行为。公开可验证的保护仍来自 AMS / ATMS 计算出的 `oom_score_adj`、可见 Activity、前台服务和绑定关系；如果厂商实现把显示可见性接入 lmkd，应按 OEM 定制单独验证。

[已验证: AOSP android-16.0.0_r1, system/memory/lmkd/lmkd.cpp / frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

#### 内存配额制：MemoryLimiter（Android 17）

Android 17（API 37）引入了基于设备总 RAM 的 app memory limits，并且只在部分设备上启用。它和传统 `lmkd` 的整体内存压力响应不同：当进程触发系统设定的内存限制时，`ApplicationExitInfo.getDescription()` 会包含 `MemoryLimiter:AnonSwap`，退出原因是 `REASON_OTHER`。

排查这类退出时，不能只看 `oom_score_adj` 和整体水位，还要看 memory limiter 状态与被杀进程的退出描述。Android 17 还支持用 `ProfilingManager` 的 `TRIGGER_TYPE_ANOMALY` 在系统处理异常内存使用前采集 heap dump。

[已验证: Android 17 官方文档, Behavior changes: all apps / Manage your app's memory]



<!-- AIW-源码调研-2026-04-20: CachedAppOptimizer 机制补充 -->
### 扩展四：Android 11+ CachedAppOptimizer 与 cgroup Freezer（源码级补充）

AOSP android-11.0.0_r1 已经有 `CachedAppOptimizer.java`、`KEY_USE_FREEZER` 和 `Process.setProcessFrozen()` 调用。它和 lmkd 的 kill 路径不同：freezer 把 cached 进程冻结在内存中，进程 Track 仍存在，但线程不再继续运行；LMK 则会让进程退出，后续再进入冷启动。

| 版本 | 已核验事实 |
|------|------------|
| Android 11 | 已存在 `CachedAppOptimizer.java`、`KEY_USE_FREEZER`、`Process.setProcessFrozen()` |
| Android 12/13 | `DEFAULT_FREEZER_DEBOUNCE_TIMEOUT = 600_000L`，默认 debounce 为 10 分钟 |
| Android 14/15 | `DEFAULT_FREEZER_DEBOUNCE_TIMEOUT = 10_000L`，默认 debounce 调整为 10 秒 |
| Android 16 | 仍保留 cached app freezer 机制，冻结/解冻封装进一步收口到 `Freezer` 辅助对象 |

**Perfetto 区分**：被 LMK 杀死 = 进程消失 + lmkd kill / process exit 信号；被 Freezer 冻结 = 进程 Track 仍在 + 线程长期无 Slice。支持对应 ftrace 事件的设备上，可结合 `linux.process_freeze_state` 确认冻结状态。

[源码验证: AOSP android-11.0.0_r1 / android-12.0.0_r1 / android-14.0.0_r1 / android-16.0.0_r1, CachedAppOptimizer.java]
[源码验证: libprocessgroup/task_profiles.json]


### PSI 驱动的 Android LMKD 进程杀机制（DeepResearch 调研材料）
- 来源：`DeepResearch/PSI 驱动的 Android LMKD 进程杀机制 — 源码级深度调研.md`
- 类型：DeepResearch 调研结果
- 摘要：从 vmpressure 到 PSI 的范式转移完整源码路径分析，覆盖 kernel/sched/psi.c → lmkd.cpp 完整信号链，包含 PSI stall threshold 配置、lmkd 事件订阅机制、进程选择策略、per-UID 防护、swap+zRAM 配合、Android 10-15 演进编年史，以及 Google A/B 实测数据。
- 注入时间：2026-04-24（首次），后续 2026-04-28/29/30 追加摘要更新
- 价值：源码级贯通 PSI→LMKD 完整信号链，填补 AIW ch04-lmk 的 PSI 机制源码分析空白



### Cached App Freezer 与 GC 触发路径独立验证（AIW-源码调研-2026-05-19）

- 来源：`DeepResearch/2026-05-19-android-cached-app-freezer-gc-trigger.md`
- 类型：DeepResearch 调研结果
- 摘要：本题验证了 Android Cached App Freezer 与 GC 触发路径的独立性。关键发现：
  - `CachedAppOptimizer.java` 的 `FREEZER_CUTOFF_ADJ = CACHED_APP_MIN_ADJ = 900`，决定哪些 adj ≥ 900 的进程可被冻结
  - Freezer 与 LMK 共用同一 Adj 范围但独立决策：`CACHED_APP_LMK_FIRST_ADJ` (950) 以上由 LMK 先杀，900 及以上由 freezer 可能冻结
  - 解冻原因（`UNFREEZE_REASON_*`）共 30+ 种，包括 ACTIVITY, BIND_SERVICE, START_SERVICE, UI_VISIBILITY, FILE_LOCKS, BINDER_TXNS 等
  - GC 触发由 `art/runtime/gc/heap.cc` 的 `NeedGC()` 独立判断，与 freezer 完全解耦
  - 16KB 页大小影响内存分配粒度（页对齐），不影响 freezer 决策和 GC 触发阈值
  - Android 14 引入 `FrozenStateChangeCallback` API，允许系统服务感知进程冻结状态

[源码验证: AOSP android-14.0.0_r1 / android-16.0.0_r1, `CachedAppOptimizer.java`, `ProcessList.java`, `OomAdjuster.java`]

## 参考资料

### AOSP 源码
- `system/core/lmkd/lmkd.c` — Android 8.1-10 userspace lmkd 旧路径
- `system/memory/lmkd/` — lmkd 守护进程源码
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java` — oom_adj / oom_score_adj 常量和 LMK socket 命令
- `frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java` — 优先级动态调整逻辑
- `frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java` — cached app freezer 机制
- `frameworks/base/core/java/android/content/ComponentCallbacks2.java` — `onTrimMemory()` 与 trim 级别定义
- `system/memory/lmkd/reaper.cpp` — kill 后回收执行链

### 官方文档
- [lmkd — source.android.com](https://source.android.com/docs/core/perf/lmkd)
- [Memory Management — developer.android.com](https://developer.android.com/topic/performance/memory)
- [ComponentCallbacks2 — developer.android.com](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [16KB Page Size — developer.android.com](https://developer.android.com/guide/practices/page-sizes)
- [Android 17 App memory limits — developer.android.com](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)

### 技术博客
- [Userspace lmkd — Android Developers Blog](https://android-developers.googleblog.com/2020/07/lmkd-userspace-low-memory-killer-daemon.html)
- [PSI in the Android Ecosystem — LPC 2019](https://lpc.events/2019/slides.html)

### 交叉引用
- 本章 4.1 节「Android 内存模型全景」— 系统内存组成和度量方法
- 本章 4.3 节「ART 虚拟机内存管理」— Java 堆的内存分配与回收
- 第 1 章第 3 节「进程模型与生命周期管理」— 进程优先级的生命周期管理
- 第 10 章第 4 节「低内存对系统性能的影响」— 低内存场景的深度分析

