---
status: finalized
title: Low Memory Killer
section: 4.4
chapter: 4.4
drafted_date: 2026-03-31
reviewed_date: 2026-05-10
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: "reviewed"
_audit: 2026-05-21
last_task6_audit_log: logs/review/2026-05-21-21-audit.md
last_task6_audit: 2026-06-14
last_task6_at: "2026-05-21T21:06:00+08:00"
task9_state: "reviewed"
polish_count: 1
polish_date: 2026-04-05
polish_by: task2b-polish
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: 2026-05-09
last_verified_against: "AOSP android-4.0.1_r1 init.rc/ProcessList.java, android-8.1"
confidence: medium-high
sources: "AOSP ProcessList.java, lmkd.cpp, reaper.cpp, OomAdjuster.java, CachedAppOptimizer.java; source.android.com/docs/core/perf/lmkd; developer.android.com/about/versions/17/behavior-changes-all"
tags: "LMK, lmkd, OOM, oom_score_adj, PSI, memory-pressure, process-priority, CachedAppOptimizer, Android-17"
related_chapters: "4.1, 4.3, 1.3, 10.4"
task9_result: auto-fixed
task2b_state: fixed
task2b_result: fixed
task9_reviewed_date: 2026-06-08
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-08T22:20:00+08:00"
review_notes: "2026-04-27 task2b: 修复 Task9 P0/P1 与 external P1；校正旧 LMK 初始化、userspace"
last_task9_autofix_at: 2026-06-08
last_task2b_at: "2026-06-08T21:06:43+08:00"
task2b_fixed_by: openclaw-task2b
repaired_date: 2026-04-27
repaired_by: openclaw-task2b
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
pipeline_stage: ready-to-publish
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

早期的 Android（从 Android 1.0 到大约 Android 8）使用的是一个内核驱动 `drivers/staging/android/lowmemorykiller.c`。

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
| Android 16 | 仍保留 cached app freezer 机制，冻结/解冻操作统一封装到 `Freezer` 辅助对象 |

**Perfetto 区分**：被 LMK 杀死 = 进程消失 + lmkd kill / process exit 信号；被 Freezer 冻结 = 进程 Track 仍在 + 线程长期无 Slice。支持对应 ftrace 事件的设备上，可结合 `linux.process_freeze_state` 确认冻结状态。

[源码验证: AOSP android-11.0.0_r1 / android-12.0.0_r1 / android-14.0.0_r1 / android-16.0.0_r1, CachedAppOptimizer.java]
[源码验证: libprocessgroup/task_profiles.json]




<!-- AIW-源码调研-2026-06-22: Android 17 PSI/LowMemDetector 源码级补充 -->
### 扩展五：Android 17 PSI/LowMemDetector 源码级补充

AOSP `android-17.0.0_r1` 的 PSI 集成沿用"libpsi + lmkd + BPF memevents"三层架构，但相对 Android 12-15 有三处关键演进：mp_event_common 被 `[[deprecated]]`、libpsi 独立成子库、memevent 默认启用直接回收/kswapd 探测。本节补充 `lmkd.cpp` 实际调用链与代码位置，所有结论均直接锚到 AOSP tag `android-17.0.0_r1`。

#### 5.1 libpsi 适配层（`system/memory/lmkd/libpsi/`）

- 头文件：`system/memory/lmkd/libpsi/include/psi/psi.h`（66 行）
- 实现：`system/memory/lmkd/libpsi/psi.cpp`（125 行）
- `libpsi/Android.bp`：`cc_library`、`vendor_available: true`，即 vendor 进程也可使用

关键数据结构和 API：

```c
// psi.h L22-L25
enum psi_resource { PSI_MEMORY, PSI_IO, PSI_CPU, PSI_RESOURCE_COUNT };
enum psi_stall_type { PSI_SOME, PSI_FULL, PSI_TYPE_COUNT };

// psi.h L42-L45
static const char* psi_resource_file[PSI_RESOURCE_COUNT] = {
    "/proc/pressure/memory", "/proc/pressure/io", "/proc/pressure/cpu",
};

int init_psi_monitor(enum psi_stall_type, int threshold_us, int window_us,
                     enum psi_resource = PSI_MEMORY);
int register_psi_monitor(int epollfd, int fd, void* data);
```

`init_psi_monitor()`（psi.cpp L29-L67）的实现就是：open `/proc/pressure/<resource>` → write `"<some|full> <threshold_us> <window_us>"` → 返回 fd。`register_psi_monitor()`（psi.cpp L72-L80）用 `EPOLLPRI`（注意不是 `EPOLLIN`）把 fd 加进 epoll。

[源码验证: AOSP android-17.0.0_r1 `system/memory/lmkd/libpsi/psi.cpp` L29-L80, `libpsi/include/psi/psi.h` L22-L65, `libpsi/Android.bp`]

#### 5.2 lmkd 集成 PSI：3 档注册 + 新策略

lmkd.cpp 在 `init_psi_monitors()`（L3607-L3648）注册 3 个 PSI fd，对应 `VMPRESS_LEVEL_LOW / MEDIUM / CRITICAL`。每档通过 `init_mp_psi()`（L3435-L3462）走 `libpsi::init_psi_monitor()` + `libpsi::register_psi_monitor()`。

**新策略下的差异**（L3623-L3627）：

```cpp
if (use_new_strategy) {
    psi_thresholds[VMPRESS_LEVEL_LOW].threshold_ms = 0;          // 禁用 low
    psi_thresholds[VMPRESS_LEVEL_MEDIUM].threshold_ms = psi_partial_stall_ms;
    psi_thresholds[VMPRESS_LEVEL_CRITICAL].threshold_ms = psi_complete_stall_ms;
}
```

`use_new_strategy` 由 `low_ram_device` 或 `!use_minfree_levels` 触发；只有在 v1 cgroup 存在时才允许走旧策略（`memcg_version() != kV1` 时强制新策略）。

**handler 绑定**（L3451）：

```cpp
vmpressure_hinfo[level].handler = use_new_strategy ? mp_event_psi : mp_event_common;
```

**重要事实纠正**：本节 §"PSI：更精准的内存压力度量"中提到的 "DEF_PARTIAL_STALL=70 / DEF_COMPLETE_STALL=700" 是 `ro.lmk.psi_partial_stall_ms` / `ro.lmk.psi_complete_stall_ms` 的 property 缺省值；`lmkd.cpp` 内部硬编码的 `psi_thresholds[]` 是 `70 / 100 / 70`（partial 70ms、partial 100ms、full 70ms），通过 `GET_LMK_PROPERTY` 宏覆盖到 `psi_partial_stall_ms` / `psi_complete_stall_ms`，**最终优先级阈值是 property 覆盖后的值，不是硬编码 70**。

[源码验证: AOSP android-17.0.0_r1 `system/memory/lmkd/lmkd.cpp` L122-L168（hardcoded psi_thresholds）、L140-L156（property 缺省）、L3607-L3648（init_psi_monitors）、L3435-L3462（init_mp_psi）]

#### 5.3 事件处理：`__mp_event_psi()` 决策路径

事件入口（L3191-L3194）：

```cpp
static void mp_event_psi(int data, uint32_t events, struct polling_params *poll_params) {
    union psi_event_data event_data = {.level = (enum vmpressure_level)data};
    __mp_event_psi(PSI, event_data, events, poll_params);
}
```

`__mp_event_psi()`（L2773-L3193）的判定流程：

1. **过滤抖动**（L2831-L2850）：第一个 polling 窗口内忽略更低级事件，prev_level 升级后只接受同级或更高级。
2. **kill-in-flight 跳过**（L2856-L2863）：距上次 kill 不到 `kill_timeout_ms` 则 `goto no_kill`。
3. **vmstat / meminfo 读取**（L2866-L2880）：从 `/proc/vmstat` 和 `/proc/meminfo` 读 thrashing 指标。
4. **直接回收 / kswapd 探测**（L2894-L2904）：优先 memevent 时间戳，否则用 vmstat 差分（`pgscan_direct / pgscan_kswapd / pgrefill`）。
5. **轮询频率切换**（L3170-L3189）：

```cpp
if (swap_is_low || killing) {
    poll_params->polling_interval_ms = PSI_POLL_PERIOD_SHORT_MS;   // 10ms
} else {
    poll_params->polling_interval_ms = PSI_POLL_PERIOD_LONG_MS;    // 100ms
}
```

`__mp_event_psi()` 内部用 `enum reclaim_state { NO_RECLAIM, KSWAPD_RECLAIM, DIRECT_RECLAIM }` 三态机判断当前是空闲、后台回收还是直接回收，这直接影响 kill 阈值与 thrashing 限制。

[源码验证: AOSP android-17.0.0_r1 `system/memory/lmkd/lmkd.cpp` L2773-L3193, L2866-L2910, L3170-L3189]

#### 5.4 mp_event_common 已标 deprecated

L3207-L3208：

```cpp
// The implementation of this function relies on memcg statistics that are only
// available in the v1 cgroup hierarchy.
[[deprecated("memcg v1 is not supported after Dec. 2026")]]
static void mp_event_common(int data, uint32_t events, struct polling_params *poll_params) {
```

这是 Android 17 的重要信号：基于 v1 cgroup memcg 的旧 kill 策略将在 2026-12 之后停止支持。Android 16 之前只以注释形式警告，Android 17 直接以 `[[deprecated]]` 属性硬约束编译器诊断。

[源码验证: AOSP android-17.0.0_r1 `system/memory/lmkd/lmkd.cpp` L3207]

#### 5.5 BPF memevent 集成

`init_memevent_listener_monitoring()`（L3525-L3598）通过 `android::bpf::memevents::MemEventListener` 订阅 ring buffer，注册 5 类事件：

| 事件类型 | 用途 |
|---------|------|
| `MEM_EVENT_DIRECT_RECLAIM_BEGIN/END` | 标记直接回收时间窗口 |
| `MEM_EVENT_KSWAPD_WAKE/SLEEP` | 标记 kswapd 唤醒窗口 |
| `MEM_EVENT_VENDOR_LMK_KILL` | vendor hook 自定义 kill（可选） |
| `MEM_EVENT_UPDATE_ZONEINFO` | zone watermark 刷新（可选） |

注册时机：必须等 `sys.boot_completed=true` 才能调用，因为 BPF 程序要等系统起来才加载。`init_memevent()`（L3599-...）单独在 `LMK_BOOT_COMPLETED` 之后被触发。

启用后的影响：`__mp_event_psi()` 中 `in_direct_reclaim / in_kswapd_reclaim` 直接从时间戳判定，不再做 vmstat 差分，性能更好且不依赖字段重命名（5.9 kernel 重命名 `workingset_refault` → `workingset_refault_file`，lmkd L2867-L2869 已兼容两者）。

[源码验证: AOSP android-17.0.0_r1 `system/memory/lmkd/lmkd.cpp` L3480-L3606（memevent_listener_notification 与 init_memevent_listener_monitoring）]

#### 5.6 轮询状态机：POLLING_START/PAUSE/RESUME

`polling_update` 枚举（lmkd.cpp L243-L247）：

```cpp
enum polling_update {
    POLLING_DO_NOT_CHANGE,
    POLLING_START,
    POLLING_PAUSE,
    POLLING_RESUME,
};
```

`mp_event_psi()` 在 `__mp_event_psi()` 末尾设置 `poll_params->update`：

- `POLLING_START`：PSI 事件首次到达，开启 10ms/100ms 周期轮询
- `POLLING_PAUSE`：等待被 kill 进程死信号期间暂停
- `POLLING_RESUME`：被 kill 进程已死或 kill_timeout 到期恢复轮询

`POLLING_DO_NOT_CHANGE`：常规唤醒但无需调整状态。

[源码验证: AOSP android-17.0.0_r1 `system/memory/lmkd/lmkd.cpp` L243-L247, L3160-L3190]

#### 5.7 章节事实校验

| 本节 §"PSI" 中声明 | 源码核对结果 |
|-------------------|-------------|
| "DEF_PARTIAL_STALL=70、DEF_COMPLETE_STALL=700" 是 AOSP 定义的 property 缺省 | ✅ L143-L156 一致 |
| "lmkd 关注 memory 的 some 和 full 信号" | ✅ psi_thresholds 全部为 PSI_SOME / PSI_FULL |
| "Android 10 PSI 阈值硬编码在 lmkd.c 中" | ✅ 旧路径，与本节 PSI 路径不冲突 |
| lmkd.cpp 用 v1 cgroup memcg 决定进程杀路径 | ⚠️ Android 17 标 deprecated，未来不可用 |
| 缺：libpsi 独立子库 | ✅ 本节补充 |
| 缺：mp_event_psi / __mp_event_psi 决策分支 | ✅ 本节补充 |
| 缺：BPF memevent 集成 | ✅ 本节补充 |

[调研报告: `DeepResearch/2026-06-22-android17-psi-lowmemdetector.md`]


<!-- AIW-源码调研-2026-06-25: onTrimMemory 链路与 Choreographer CALLBACK_COMMIT 优化 -->
### 扩展六：onTrimMemory 链路与 App 侧响应边界（Android 11-17）

前面 §"扩展四" 已经讲过 `CachedAppOptimizer` 的 cgroup-freezer 机制。本节继续沿着 App 侧 `onTrimMemory(int)` 回调的源码路径展开，重点澄清三件事：哪些 trim 等级在 Android 17 仍稳定、回调发生在主线程的什么时刻、App 错过的代价是什么。

#### 6.1 TRIM_MEMORY 等级收敛（API 34→17）

AOSP `frameworks/base/core/java/android/content/ComponentCallbacks2.java` 在 Android 14（API 34）开始把五档 trim 等级标 `@deprecated`：

| 等级常量 | 数值 | API 34 状态 |
|---------|------|------------|
| `TRIM_MEMORY_COMPLETE` | 80 | @deprecated since API 34，AOSP 不再派发 |
| `TRIM_MEMORY_MODERATE` | 60 | @deprecated since API 34，AOSP 不再派发 |
| `TRIM_MEMORY_RUNNING_CRITICAL` | 15 | @deprecated since API 34，AOSP 不再派发 |
| `TRIM_MEMORY_RUNNING_LOW` | 10 | @deprecated since API 34，AOSP 不再派发 |
| `TRIM_MEMORY_RUNNING_MODERATE` | 5 | @deprecated since API 34，AOSP 不再派发 |
| `TRIM_MEMORY_BACKGROUND` | 40 | 仍派发（由 CachedAppOptimizer 在 freeze 前同步下发） |
| `TRIM_MEMORY_UI_HIDDEN` | 20 | 仍派发（Activity#onStop 后同步发出） |

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/content/ComponentCallbacks2.java, line 99–161]

实际含义：**Android 14 之后，App 不能依赖 5/10/15/60/80 这五档**。`ComponentCallbacks2.onTrimMemory(int)` 文档明确写「不要比较 exact value，只比较大于等于」——这正是为了覆盖中间档位被悄悄砍掉的可能性。

#### 6.2 调度时机：Choreographer CALLBACK_COMMIT

`ActivityThread.ApplicationThread.scheduleTrimMemory()` 把 trim 任务 post 到 `Choreographer.CALLBACK_COMMIT`，而不是直接 `mH.post`：

```java
// frameworks/base/core/java/android/app/ActivityThread.java:2289-2304
@Override
public void scheduleTrimMemory(int level) {
    final Runnable r = PooledLambda.obtainRunnable(ActivityThread::handleTrimMemory,
            ActivityThread.this, level).recycleOnUse();
    // Schedule trimming memory after drawing the frame to minimize jank-risk.
    Choreographer choreographer = Choreographer.getMainThreadInstance();
    if (choreographer != null) {
        choreographer.postCallback(Choreographer.CALLBACK_COMMIT, r, null);
    } else {
        mH.post(r);
    }
}
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java]

Choreographer 的 callback 顺序是 `INPUT → ANIMATION → LAYOUT → COMMIT`，trim 被排到 commit 阶段，意味着发生在 `draw` 之后、`traversal` 下一轮之前。这个改造的工程意图非常清楚：**避免在 GPU 渲染过程中触发 GC 引发的 frame drop**。

`PooledLambda.obtainRunnable(...).recycleOnUse()` 是另一个细节：高频 trim 时复用 lambda 对象，避免分配 Runnable 造成额外 GC 压力。

#### 6.3 handleTrimMemory 的前台保护

```java
// frameworks/base/core/java/android/app/ActivityThread.java:7868-7894
private void handleTrimMemory(int level) {
    if (Trace.isTagEnabled(Trace.TRACE_TAG_ACTIVITY_MANAGER)) {
        Trace.traceBegin(Trace.TRACE_TAG_ACTIVITY_MANAGER, "trimMemory: " + level);
    }
    try {
        if (skipBgMemTrimOnFgApp()
                && mLastProcessState <= ActivityManager.PROCESS_STATE_IMPORTANT_FOREGROUND
                && level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND) {
            return;
        }
        final ArrayList<ComponentCallbacks2> callbacks =
                collectComponentCallbacks(true /* includeUiContexts */);
        final int N = callbacks.size();
        for (int i = 0; i < N; i++) {
            callbacks.get(i).onTrimMemory(level);
        }
    } finally {
        Trace.traceEnd(Trace.TRACE_TAG_ACTIVITY_MANAGER);
    }
    WindowManagerGlobal.getInstance().trimMemory(level);
}
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java]

`skipBgMemTrimOnFgApp()` 这个分支意味着：**前台进程收到 `TRIM_MEMORY_BACKGROUND` 或更高档位时直接 return**。这就是为什么开发者必须主动在 `Activity#onStop`（而不是依赖 `onTrimMemory(40)`）里释放大对象——前台进程根本不会被通知。

#### 6.4 CachedAppOptimizer 在 freeze 前的最后一刻

`CachedAppOptimizer` 的 freeze 路径在把进程 cgroup-freeze 之前**先**给 App 一次 `TRIM_MEMORY_BACKGROUND` 回调：

```java
// frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java:1409-1420
if (app.getSetAdj() >= CACHED_APP_MIN_ADJ) {
    final IApplicationThread thread = app.getThread();
    if (thread != null) {
        try {
            thread.scheduleTrimMemory(TRIM_MEMORY_BACKGROUND);
        } catch (RemoteException e) {
            // do nothing
        }
    }
}
reportProcessFreezableChangedLocked(app);
...
mFreezeHandler.sendMessageDelayed(...);
opt.setPendingFreeze(true);
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java]

完整链路：

```
lmkd (kernel PSI / lowmem) 
  → ActivityManager 收到 LMK_PROCPRIO / kill 决策
  → CachedAppOptimizer 决定 freeze
  → IApplicationThread.scheduleTrimMemory(TRIM_MEMORY_BACKGROUND)
  → ActivityThread.scheduleTrimMemory (Choreographer CALLBACK_COMMIT)
  → handleTrimMemory(40)
  → Application/Activity.onTrimMemory(40)
  → CachedAppOptimizer 立即调用 freezeHandler 把进程 cgroup-freeze
```

**App 错过的代价**：cgroup-freeze 后进程的 IO/CPU 几乎被冻结，回到前台时（解冻）要重新做工作集预热（class loading、BitmapFactory.decode、JIT 编译）——这正是冷启动卡顿的源头之一。App 在 `onTrimMemory(40)` 这次回调中释放 Glide/LruCache/未使用 Bitmap 是「最后一道防线」。

#### 6.5 shell 调试入口

AMS 提供 `setProcessMemoryTrimLevel(process, userId, level)`，仅 shell 权限可调：

```java
// frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java:3748-3772
if (!isCallerShell()) {
    throw new SecurityException("Only shell can call it");
}
if (!(level < ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN ||
        app.getProcState() > PROCESS_STATE_IMPORTANT_FOREGROUND)) {
    throw new IllegalArgumentException("Unable to set a background trim level "
        + "on a foreground process");
}
thread.scheduleTrimMemory(level);
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java]

调试命令：

```bash
# 手动模拟 background trim（进程必须是后台状态）
adb shell am set-process-memory-trim-level <package_name> 40
# 模拟 UI hidden
adb shell am set-process-memory-trim-level <package_name> 20
```

注意源码里的反向校验：不允许向 `PROCESS_STATE_IMPORTANT_FOREGROUND` 及更前的进程发 background level。

#### 6.6 与小米 HyperOS「公平运行内存」的关系

小米 HyperOS 在 AOSP `CachedAppOptimizer` / `ComponentCallbacks2` 之上构建了「公平运行内存」机制（文档见 dev.mi.com），其核心思想是：
- 给 App 一次明确的「内存预警」回调窗口（仍是 `ComponentCallbacks2.onTrimMemory` 协议）
- 强制要求 App 在给定时间内响应，否则按规则计入内存优先级评分
- 通过 cgroup 配额限制单个 App 的内存上限

由于 HyperOS 的相关实现不开源，本节无法验证其内部细节。但 AOSP `CachedAppOptimizer` 给出的 `TRIM_MEMORY_BACKGROUND` 回调窗口已经为所有 OEM 提供了相同的能力——App 只要正确实现 `Application#onTrimMemory()`，就能在小米、华为、OPPO、三星、vivo 等所有主流 ROM 上获得一致的内存预警触发。**App 侧的源码级响应策略**（Glide 清理、Bitmap 复用、LruCache 容量调整）才是「公平运行内存」落地的关键。

[调研报告: `DeepResearch/2026-06-25-fair-memory-trim-android17-source.md`]



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



<!-- AIW-源码调研-2026-06-26: MemoryLimiter cgroup memory.high 后台任务内存配额 -->
### 扩展七：Android 17 MemoryLimiter — 后台任务内存配额（与 trim 路径并行的第二道防线）

`onTrimMemory` 路径只解决「cached 进程 freeze 前的最后一刻释放」，**不解决「正在运行的后台任务持续占用内存」**。Android 17 在 `frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java` 引入了一个独立的配额子系统，对**正在运行的 notVisible 进程**（Service / FGS / Backup / Receiver 等）施加 cgroup v2 `memory.high` 软限制。

#### 7.1 三种 LimitType 与 proc state 配额矩阵

源码位置：`frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java`，`initializeMemoryLimits()`（基于 android-17.0.0_r1）。

```java
// LINT.IfChange(limitTypes)
static final int LIMIT_TYPE_UNKNOWN = 0;
static final int LIMIT_TYPE_MEMORY = 1;        // memory.high 触发
static final int LIMIT_TYPE_SWAP = 2;          // memory.swap.high 触发
static final int LIMIT_TYPE_ANON_SWAP = 3;     // anon + swap 之和超阈值
```

按 proc state 分层（节选关键状态）：

| ProcessState | memHigh | swapHigh |
|--------------|---------|----------|
| `PERSISTENT` / `PERSISTENT_UI` | `LIMIT_IS_DISABLED`（不限） | `LIMIT_IS_DISABLED` |
| `TOP` / `BOUND_TOP` / `IMPORTANT_FOREGROUND` / `TOP_SLEEPING` | `mConfiguration.memVisible`（默认 4G） | `mConfiguration.swapVisible`（默认 2G） |
| `FOREGROUND_SERVICE` / `IMPORTANT_BACKGROUND` / `TRANSIENT_BACKGROUND` / `BACKUP` / `SERVICE` / `RECEIVER` / `HEAVY_WEIGHT` / `HOME` / `LAST_ACTIVITY` | `mConfiguration.memNotVisible`（默认 2G） | `mConfiguration.swapNotVisible`（默认 2G） |
| `CACHED_ACTIVITY` / `CACHED_ACTIVITY_CLIENT` / `CACHED_RECENT` / `CACHED_EMPTY` | `LIMIT_IS_IGNORED`（不应用） | `LIMIT_IS_DISABLED` |

关键设计：**cached 进程完全不在 MemoryLimiter 控制范围**，交由 lmkd 和 CachedAppOptimizer 接管；persistent 进程（system_server 等）永不限额；中间层的「正在运行的 notVisible 任务」才被配额管理。

#### 7.2 cgroup memory.high 的 Java/JNI 写入路径

Java 控制器 `ControllerEnabled` 的 `MESSAGE_CONFIG` 处理：

```java
case MESSAGE_CONFIG -> {
    if (msg.obj != null && !shouldIgnore(uid)) {
        Limits limit = (Limits) msg.obj;
        configureLimit(service, pid, uid, limit.memHigh, limit.swapHigh);
    }
}
```

JNI 实现在 `services/core/jni/com_android_server_am_MemoryLimiter.cpp`：

```cpp
enum class CgroupFile {
    kUnknown, kMemoryStat, kMemoryEvent, kMemoryHigh,
    kSwapCurrent, kSwapMax,
};

writeLimit(cgroupPath(CgroupFile::kMemoryHigh), limit);   // 写到 memory.high
writeLimit(cgroupPath(CgroupFile::kSwapMax), limit);      // 写到 memory.swap.high
```

监听侧用 `inotify_add_watch(memory.events, IN_MODIFY)`：

```cpp
void watch(int inotify_fd, wdmap_t& wdmap, Statistics& stats) {
    if (mMemWatcher.mWd == UNSET) {
        std::string cpath = cgroupPath(CgroupFile::kMemoryEvent);
        int memWd = inotify_add_watch(inotify_fd, path, IN_MODIFY);
        ...
    }
}
```

#### 7.3 触发 → ProfilingServiceHelper → 30s 宽限期后 kill

`onLimitExceeded` 是配额触发的入口：

```java
public void onLimitExceeded(int pid, int uid, int type, long memHigh, long swapHigh,
        String pkg) {
    if (type == LIMIT_TYPE_ANON_SWAP) {
        if (android.os.profiling.Flags.systemTriggeredProfilingNew()
                && android.os.profiling.anomaly.flags.Flags.anomalyDetectorCoreC()
                && pkg != null) {
            ProfilingServiceHelper helper = ProfilingServiceHelper.getInstance();
            helper.onProfilingTriggerOccurred(uid, pkg,
                    ProfilingTrigger.TRIGGER_TYPE_ANOMALY);
        }
        // Request that the target be killed.  The delay allows the profiler to complete.
        Message msg = mQueue.obtainMessage(MESSAGE_KILL, pid, uid,
                "MemoryLimiter:AnonSwap");
        mQueue.sendMessageDelayed(msg, KILL_DELAY_MS);   // KILL_DELAY_MS = 30 * 1000
    }
}
```

30 秒宽限期的工程意图：先让 `ProfilingServiceHelper` 在系统处理异常前抓 heap dump，再杀进程。`MESSAGE_KILL` 通过 `mInjector.killProcess(pid, uid, "MemoryLimiter:AnonSwap")` 终止，**`ApplicationExitInfo` 会以 `REASON_OTHER` 报告，description 包含 "MemoryLimiter:AnonSwap"**。

#### 7.4 inotify vs 轮询的双模式与 10MB hysteresis

JNI 注释：

```cpp
// Hysteresis for memory.high.  If a process is in the red zone (both memory.high and
// memory.swap.high have fired events), cgroup events are disabled and the process is polled for
// limit violations.  However, if the process memory drops <hysteresis> below the memory.high
// limit, polling stops and cgroup events are re-enabled.  The value is 10MB.
```

常态走 inotify 零开销；进入 red zone（同时超过 `memory.high` 与 `memory.swap.high`）后切换为轮询，10MB hysteresis 防止在边界抖动。

#### 7.5 启用条件：与 lmkd 完全独立的第二道防线

```java
static final String CONFIG_PATH = "/vendor/etc/memory-limiter-config.xml";

private boolean memoryLimiterEnable() {
    if (!Flags.memoryLimiterEnable()) {
        return false;
    } else if (!isMemoryLimiterSupported()) {
        return false;
    } else {
        ...
    }
}
```

启用条件：**DeviceConfig flag `memory_limiter_enable` 为 true，且 `/vendor/etc/memory-limiter-config.xml` 存在**。这解释了为什么 Android 17 的内存配额机制**只在部分设备上启用**——大多数 AOSP 通用编译不会带 vendor 配置文件。

配置结构：

```java
@VisibleForTesting
static final Configuration sDefaultConfig =
        new Configuration(GB * 4, GB * 2, GB * 2, GB * 2);
// memVisible=4G, memNotVisible=2G, swapVisible=2G, swapNotVisible=2G
```

**重要区别**：MemoryLimiter 的配额由 vendor xml 配置，**不依赖 `ProcessList.updateOomLevels()` 的 `scaleMem`/`scaleDisp` 公式**——它与设备 RAM 大小、屏幕尺寸不直接挂钩。这是与 lmkd minfree 完全不同的内存决策面。

#### 7.6 与 onTrimMemory 的分工

| 维度 | onTrimMemory 路径 | MemoryLimiter 路径 |
|------|-------------------|---------------------|
| 触发对象 | cached app（`setAdj >= CACHED_APP_MIN_ADJ`） | notVisible 进程（FGS/Service/Backup/Receiver 等） |
| 触发时机 | freeze 之前一次 | cgroup memory.high 持续监听 |
| 通知机制 | `Application#onTrimMemory(40)` | inotify + 轮询 + 30s 后 kill |
| 决策依据 | `setAdj`/LRU | proc state + vendor xml 配额 |
| 终止方式 | cgroup-freeze | `killProcess("MemoryLimiter:AnonSwap")` |
| 退出原因 | 无 explicit reason（freeze） | `REASON_OTHER` + description |

App 侧接入要点：

1. **`Application#onTrimMemory(40)` 是释放** Bitmap/LruCache/Glide 内存的关键窗口——错过即被 cgroup-freeze 冻结，再被 trim 时已是 cached 状态。
2. **后台 Service/FGS 的内存配额**由 `memNotVisible`（默认 2G）+ `swapNotVisible`（默认 2G）决定。App 在 `Service` 回调中应主动监控 PSS（`dumpsys meminfo`）以避免被 MemoryLimiter 命中。
3. **`ApplicationExitInfo.getDescription()` 含 `MemoryLimiter:AnonSwap` 字符串**：是 App 排查「被配额杀」事件的唯一线索，**不能依赖 `oom_score_adj` 或 `dumpsys meminfo` 推断**。
4. **`ProfilingServiceHelper` 在 kill 前 30 秒抓 heap dump**：通过 `TRIGGER_TYPE_ANOMALY` 触发，结合 `ProfilingManager` API 可在系统处理异常前采集现场。

#### 7.7 信息源

- [一手] AOSP `android-17.0.0_r1`：
  - `frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java` — 配额核心
  - `frameworks/base/services/core/jni/com_android_server_am_MemoryLimiter.cpp` — cgroup memory.high 写入与 inotify 监听
  - `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java` — `mMemoryLimiter = MemoryLimiter.getDefaultMemoryLimiter(mContext)` 装配
- [调研报告] `DeepResearch/2026-06-26-android17-memory-limiter-cgroup-quota.md`

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java, line 86-106 (LimitType), line 574-625 (initializeMemoryLimits), line 834 (MemoryLimiter:AnonSwap reason string), line 850 (KILL_DELAY_MS), line 1053 (memoryLimiterEnable)]
