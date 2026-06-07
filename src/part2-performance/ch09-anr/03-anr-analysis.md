---
title: "ANR 分析方法"
chapter: "9.3"
section: "9.3"
status: finalized
drafted_date: "2026-04-02"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-05-08"
last_verified_against: "AOSP android-16.0.0_r1"
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
confidence: medium
sources:
  - type: blog
    path: "Personal-Knowlodge/source/Android-ANR-02-How-to-analysis-ANR.md"
  - type: blog
    path: "Personal-Knowlodge/source/Android-ANR-03-ANR-Case-Share.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_ANR-分类以及分析流程.md"
  - type: official
    path: "developer.android.com/topic/performance/anrs"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int)"
  - type: official
    path: "https://developer.android.com/reference/android/app/ApplicationExitInfo"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingTrigger"
tags: ['anr', 'traces', 'perfetto', 'analysis', 'cpu-usage']
related_chapters: ["9.1", "9.2", "9.4", "9.5", "1.4", "2.4"]
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-06
last_task9_at: "2026-06-06T18:20:00+08:00"
review_round: 3
last_task2b_at: "2026-05-08T19:44:22"
task2b_fixed_at: "2026-04-26T13:40:00+08:00"
rework_by: openclaw-task2b
rework_type: "review回炉修复（External P95 问题单：SIGQUIT诊断可信度/android.anr track/frontmatter版本号）"
task9_review_notes: "2026-05-08 task9 deep-review: needs-rework。P0 1 / P1 0 / P2 1；ANR trace 非主进程 dump 范围需按 AOSP firstPids/lastPids/nativePids 修正。 | 2026-05-08 Task9 14:32：needs-rework。P0 0 / P1 1 / P2 0；AnrLatencyTracker 版本边界与作用描述仍需回炉。 | 2026-05-08 Task9 20:30：pass-tech-review。P0 0 / P1 0 / P2 1；ProfilingTrigger ANOMALY 触发器的 Android 17 表述仍有公开文档语义边界问题，已在 suggestions.md 既有条目记录，本轮不重复追加；无 P0/P1。 自动晋升 finalized。 | 2026-06-06 Task9 闲时抽检 auto-fix：修正 ProfilingManager/ProfilingTrigger AOSP 源码路径，公开 API 位于 Mainline Profiling 模块 packages/modules/Profiling/framework/java/android/os/，非 frameworks/base/core/java/android/os/；P0 1 / P1 0 / P2 0，回到 Task6 复审。"

reviewed_date: "2026-05-08"
reviewed_by: openclaw-task6
task2b_state: fixed
task2b_result: fixed
task6_state: reviewed  # updated by task2b-verifier 2026-06-06
task6_result: pass-light-edit
task9_state: reviewed
pipeline_stage: ready-to-publish  # updated by task2b-verifier 2026-06-06
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-05-08T20:05:00+08:00"
last_task6_audit: "2026-05-26"
last_task6_review_log: "logs/review/2026-05-08-20-review.md"
review_notes: "2026-05-08 task6 revisiting review: pass-light-edit。按写作规范修正禁用/填充词、结构性元叙述与中英文格式；无新增 B 类回炉问题。 | 2026-05-08 Task6 14:05：复审 Task2B 修复后的文稿，完成 frontmatter 去重、代码围栏语言标注与 L1/L2 小修；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-05-08 Task6 20:05：复审 Task2B 修复后的文稿，完成 L1/L2 轻量精修（重复句、用途句、口语化表达与结构性提示）；无新增 B 类回炉问题，等待 Task9 技术复审。"
last_task9_review_log: logs/deep-review/2026-06-06-18-audit.md
last_task9_audit: "2026-06-06"
last_task9_audit_log: "logs/deep-review/2026-06-06-18-audit.md"
last_task9_autofix_at: "2026-06-06"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-07
---

# ANR 分析方法

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 ANR traces.txt 的解读方法：主线程堆栈、锁信息、等待对象
- 🔹 从 Perfetto/Systrace 分析 ANR：主线程在 ANR 时间窗口内的活动
- 🔹 常见 ANR 根因分类：死锁、主线程 I/O、Binder 调用超时、CPU 饥饿、系统负载高
- 🔹 CPU 使用率信息（ANR info 中的 CPU usage）的解读
- 🔹 线上 ANR 的分析流程与工具链

### 扩展（可选深入）

- 🔸 ANR Rate 的量化与监控体系搭建
- 🔸 使用 Perfetto SQL 批量分析 ANR Trace

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要掌握 ANR 分析方法


ANR 是 Android 性能分析里最容易误判的一类问题。和卡顿不同，卡顿只是“不够流畅”；ANR 代表系统已经判定应用长时间没有响应，用户看到的是无响应对话框，部分厂商 ROM 还可能直接把应用退回桌面。更麻烦的是，很多 ANR 并不只来自应用代码：系统负载过高、内存紧张、Binder 通信阻塞，甚至内核级 Bug，都可能触发一次 ANR。只看 traces.txt 里主线程停在 `nativePollOnce`，很难判断下一步该查哪里。

这一节交付一套可执行的 ANR 分析流程：先判断 traces.txt 的可信度，再结合 Perfetto 时间线、CPU 使用率、SystemLog 和线上回捞工具，区分应用侧问题、系统侧问题和两者叠加的场景。

## traces.txt 的解读方法

当 ANR 发生时，系统会通过发送 `SIGQUIT` 信号给目标进程，触发 ART 虚拟机 dump 所有线程的调用栈。这份输出就是 traces.txt。在较新的 Android 版本中，可以通过 `adb bugreport` 获取，也可以直接从设备的 `/data/anr/` 目录拉取。

### traces.txt 的结构

一份典型的 traces.txt 以 ANR 进程的 PID 和触发原因开头，后面跟着进程中每一个线程的详细信息。最先关注的是主线程（通常名为 `"main"`）的段落。

下面是一段主线程处于空闲等待状态的 trace（这是正常的）：

```text
"main" prio=5 tid=1 Native
  | group="main" sCount=1 dsCount=0 flags=1 obj=0x72c8bbf8 self=0xb400007b0ec10800
  | sysTid=5991 nice=-10 cgrp=default sched=0/0 handle=0x7b95f61500
  | state=S schedstat=( 807053249 267562324 1494 ) utm=63 stm=17 core=3 HZ=100
  | stack=0x7fcccd9000-0x7fcccdb000 stackSize=8192KB
  | held mutexes=
  native: #00 pc 00000000000c6418  libc.so (__epoll_pwait+8)
  native: #01 pc 0000000000019a9c  libutils.so (Looper::pollInner+184)
  native: #02 pc 000000000001997c  libutils.so (Looper::pollOnce+112)
  native: #03 pc 0000000000114310  libandroid_runtime.so (android_os_MessageQueue_nativePollOnce+44)
  at android.os.MessageQueue.nativePollOnce(Native method)
  at android.os.MessageQueue.next(MessageQueue.java:339)
  at android.os.Looper.loop(Looper.java:198)
  at android.app.ActivityThread.main(ActivityThread.java:8142)
```


这段 trace 表明：主线程停在 `nativePollOnce`，也就是在 `Looper` 中等待下一条 Message。这是正常状态——如果 ANR 时主线程显示的是这个堆栈，说明 ANR 发生的时刻主线程并没有在执行耗时操作，问题很可能出在别的地方。

### 头部元数据字段

trace 头部包含大量诊断信息，以下是关键字段的含义：

- **prio**：线程优先级。主线程正常是 5（`THREAD_PRIORITY_DEFAULT`），如果被改低了可能影响调度
- **tid**：ART 虚拟机内部的线程 ID
- **sysTid**：操作系统层面的线程 ID，和 top/Perfetto 中看到的一致
- **nice**：Linux nice 值。主线程通常是 -10（`THREAD_PRIORITY_FOREGROUND`）
- **sCount**：线程被挂起的次数。如果值很大，说明线程频繁被暂停（可能是 GC 或调试器导致）
- **state**：线程状态。`S` 表示 Sleeping，`R` 表示 Running，`B` 表示 Blocked（等待 monitor 锁），`D` 表示 Uninterruptible Sleep（通常是 I/O 等待或被冻结）
- **utm/stm**：用户态/内核态 CPU 时间（单位约 10ms），可以大致判断线程的 CPU 消耗


### SIGQUIT 响应延迟与诊断可信度


traces.txt 是 SIGQUIT 信号触发后的一个时间点快照，但它不一定准确反映 ANR 发生的"第一案发现场"。诊断可信度需要按版本区分：

**Android 13 及以下**：从 ANR 触发到 SIGQUIT 发送、再到所有线程被挂起并 dump 完调用栈，中间可能经过数秒。在这段时间里，主线程的状态可能已经发生了变化——导致 ANR 的耗时操作可能在 dump 之前就执行完了，trace 里看到的只是后续空闲状态（比如 `nativePollOnce`）。这种情况下，traces.txt 里的堆栈可能已经滞后，需要结合 Perfetto 时间线还原真实过程。

**Android 14+**：`AnrLatencyTracker` 在 ANR 处理的关键节点写入 Perfetto trace slice/counter 与延迟分解（`anrRecordPlacedOnQueue`、`anrProcessing`、`dumpStackTraces()` 等），可以还原从 ANR 触发到 trace dump 的时间差。主线程是否仍在触发时的代码路径，需要靠 Perfetto 的 sched、slice 数据与 traces.txt 交叉验证——时间差越短，堆栈可信度越高。实测经验表明，在 dump 延迟 < 500ms 的场景中，主线程堆栈与 Perfetto 时间线高度吻合；随着延迟拉长，堆栈漂移的概率会上升。AOSP 源码中并没有定义“90% 可信”或“2 秒阈值”的硬性常量——这两个数字不应作为判断标准。

**排查建议**：Android 14+ 设备上，先在 Perfetto 中确认 `dumpStackTraces()` 与 `anrRecordPlacedOnQueue` 的时间差。时间差越小，主线程堆栈越值得信赖；如果时间差超过数百毫秒，需要交叉比对 Perfetto 主线程 slice，确认 dump 时刻主线程是否已经离开了 ANR 触发时的代码路径。

### 锁信息与等待关系


当主线程处于 Blocked 状态时，trace 中会显示锁的等待关系，这是排查死锁的关键线索：

```text
"main" prio=5 tid=1 Blocked
  | held mutexes=
  at com.facebook.cache.disk.DiskStorageCache.e(DiskStorageCache.java:3)
  - waiting to lock <0x0e57c91f> (a java.lang.Object) held by thread 89
```

这里的信息非常明确：主线程在等待一个 Object 锁（地址 `0x0e57c91f`），而这个锁被线程 89 持有。下一步是在 trace 文件中搜索 `tid=89`，检查那个线程在做什么——如果它也在等主线程持有的锁，那就是死锁；如果它在做耗时操作，那就是锁竞争导致的阻塞。

### 线程状态对照

| traces.txt 中显示 | 对应 Thread.State | 含义 |
|---|---|---|
| Native | RUNNABLE | 正在执行 JNI native 方法，通常是在 epoll_wait 等 |
| Blocked | BLOCKED | 等待获取 monitor 锁 |
| Waiting | WAITING | 调用了 Object.wait()，无超时 |
| TimedWaiting | TIMED_WAITING | 调用了 Object.wait(timeout) 或 Thread.sleep() |
| Sleeping | TIMED_WAITING | Thread.sleep() |
| Runnable | RUNNABLE | 正在执行 Java 代码 |

注意：`Native` 状态是最常见的"正常"状态——主线程在 `nativePollOnce` 中等待 Message 时就显示为 Native。不要看到 `Native` 就以为有问题。

## 从 Perfetto/Systrace 分析 ANR


traces.txt 能说明 ANR 发生时各个线程在做什么，但它只是一个时间点的快照。Perfetto 补上的是 ANR 前后一段时间内的过程视角：主线程什么时候开始忙、什么时候被调度、什么时候恢复空闲，都需要回到时间线里看。

### 抓取包含 ANR 的 Perfetto Trace

分析 ANR 时,Perfetto 的抓取窗口要完整覆盖 ANR 发生前后的时间线。建议打开 sched、binder、input、am、view、wm 等关键 track,抓取时长 60 秒左右。


### 在 Perfetto 中定位 ANR 时间窗口

**方法一：搜索 am_anr 事件。** 在 Perfetto 的搜索栏中搜索 `am_anr`，ANR 触发时 ActivityManager 会在 EventLog 中输出对应的时间线标记。

**方法二：根据时间范围跳转。** 如果从 bugreport 中已经知道了 ANR 的精确时间（通过搜索 `am_anr`），可以在 Perfetto UI 的时间轴上直接跳转到对应时间。

### 主线程活动分析


定位到时间窗口后，重点观察主线程的 CPU 调度状态变化——Perfetto 中主线程的每个 slice 对应一段执行或等待，连续阅读这些 slice 就能还原 ANR 前主线程经历了什么。以下是四种典型模式：

**模式一：主线程一直在跑 CPU（Running 状态）。** 在 Perfetto 的 CPU track 中看到主线程长时间占据 CPU slice。通常是主线程代码本身有耗时操作：复杂布局、大量计算、数据库查询等。

**模式二：主线程频繁在 Running 和 Runnable 之间切换。** 说明主线程拿不到足够的 CPU 时间。可能是系统负载过高、主线程优先级被降低、或 CPU 频率被限制（温控）。结合 CPU 频率 track 和整体 CPU 使用率来判断。

**模式三：主线程处于 D 状态（Uninterruptible Sleep）。** 如果 Kernel Callstack 中看到 `__refrigerator`，说明进程被系统冻结了（通常是由于灭屏后的功耗优化）。这是系统行为，不是应用的问题。

**模式四：主线程处于 Sleep 但非 nativePollOnce。** 如果主线程在 sleep 状态但不是正常的 epoll_wait，而是等待 Binder 返回（`binder_thread_read` 或 `IPCThreadState::talkWithDriver`），说明主线程在同步等待其他进程的响应。需要进一步追踪 Binder 事务的对端。

[图：Perfetto 中 ANR 时间窗口内主线程的四种典型活动模式对比]

## 常见 ANR 根因分类与排查思路


分析 ANR 的核心思路是区分"应用的问题"还是"系统的问题"。这个判断会直接决定后续的优化方向。

ANR 的根因可以归为三类：主线程被阻塞（等着拿不到的东西）、主线程在干不该干的事（I/O、计算）；主线程拿不到 CPU（别人占着）。后面的分类按照这三种模式展开，每一类都有对应的 trace 特征和排查路径。

### 死锁

死锁是最容易排查的 ANR 类型。在 traces.txt 中，主线程的状态为 `Blocked`，trace 会明确给出"waiting to lock <地址> held by thread X"。

排查步骤：
1. 找到主线程 trace 中的 `waiting to lock` 信息
2. 根据 `held by thread N` 在 trace 文件中搜索 `tid=N`
3. 检查持锁线程是否也在等待其他线程持有的锁
4. 如果形成环路 → 死锁；如果没有环路 → 锁竞争（持锁线程在执行耗时操作）


### 主线程 I/O


主线程做 I/O 是最常见的 ANR 原因之一。在 trace 中，主线程堆栈会显示 `FileOutputStream.write`、`FileInputStream.read`、`SharedPreferencesImpl.writeToDisk` 等文件操作。

SharedPreferences 容易踩一个坑：`apply()` 看起来是异步的，但在 Activity 的 `onPause/onStop` 生命周期回调中，系统会等待 `apply()` 的写入完成（通过 `waitToFinish` 机制）。如果在 `onPause` 之前积攒了大量 `apply()` 调用，在生命周期切换时就会一次性等待所有写入完成，导致 ANR。

### Binder 调用超时


主线程通过 Binder 与 system_server 或其他进程通信时，如果对端处理慢或线程池满了，主线程就会被阻塞。在 trace 中，堆栈通常包含 `Binder.proxyXXX`、或 native 层的 `IPCThreadState::waitForResponse`。

系统日志中的 `binder_sample` 条目能直接给出哪个 Binder 调用耗时多久：

```text
binder_sample: [android.view.accessibility.IAccessibilityManager,6,2010,com.xxx.community,100]
```

这条日志表示某进程执行 `IAccessibilityManager` 的 code=6 方法，耗时 2010ms。

### CPU 饥饿


有些 ANR 场景下，主线程代码本身没有耗时操作，但拿不到 CPU 时间。在 Perfetto 中表现为：主线程处于 Runnable 状态（已经准备好运行了），但长时间没有被调度到 CPU 上执行。

CPU 饥饿的判断需要结合 CPU 使用率信息和 Perfetto 的全局视图。如果在 ANR 时间窗口内，整体 CPU 使用率接近饱和（比如 8 核全满），而应用 CPU 占比很低，那就可以判定是 CPU 饥饿导致的 ANR。

### 系统负载高

还有一种情况：应用和系统都没有明显的 Bug，但系统整体负载过高，导致主线程拿不到足够的 CPU 时间。这种情况下，关注几个关键系统进程的 CPU 占用往往能快速定位瓶颈来源：

以下几种系统进程的异常是重要的信号：
- **system_server CPU 占用异常高**：可能是内部有死循环或锁竞争
- **kswapd0 CPU 占用高**：内存紧张，内核在高频回收页面
- **logd CPU 占用高**：日志系统过载，所有进程的日志输出都被阻塞
- **surfaceflinger CPU 占用高**：合成线程繁忙，可能影响 VSync 信号的分发

## CPU 使用率信息的解读


ANR 日志中搜索 `ANR in` 可以找到系统在 ANR 前后收集的 CPU 使用率快照。这部分信息是区分应用侧问题和系统侧问题的依据——它回答两个问题：ANR 发生时 CPU 被谁占了？内存压力有多大？

### 信息结构

一份完整的 CPU 信息通常包含两段统计：

```text
// ANR 前一段时间的 CPU 使用情况（通常 10-15 秒）
CPU usage from 0ms to 13135ms later:
  191% 1948/system_server: 72% user + 119% kernel / faults: 78816 minor 9 major
  30% 5991/com.xxx.launcher: 23% user + 6.4% kernel / faults: 118172 minor 2 major

// ANR 前短时间内的 CPU 使用情况（通常 1 秒）
CPU usage from 246ms to 1271ms later:
  290% 1948/system_server: 114% user + 176% kernel / faults: 9353 minor
```

### 关键指标解读

**Load（负载）**：`Load: 15.29 / 5.19 / 1.87` 分别表示 1 分钟、5 分钟、15 分钟的系统平均负载。对于 8 核 CPU，负载 8.0 意味着所有核心满负荷。

**user / kernel 比例**：kernel 占比异常高（比如 system_server 的 119% kernel），通常意味着系统在进行大量的系统调用（I/O、Binder、内存操作）。

**faults**：`minor` 表示高速缓存缺页，`major` 表示磁盘缺页。`major` 数量大说明当时 I/O 负载高。

### Memory 压力信息


较新的 Android 版本还会输出 `/proc/pressure/memory` 的内容：

```text
----- Output from /proc/pressure/memory -----
some avg10=1.35 avg60=0.31 avg300=0.06 total=346727
full avg10=0.00 avg60=0.00 avg300=0.00 total=34803
----- End output from /proc/pressure/memory -----
```

- **some**：至少有一个任务在内存分配上被阻塞的时间占比
- **full**：所有非 idle 任务同时被内存阻塞的时间占比——这个值高意味着整个系统因为内存不足而停滞
- **avg10/avg60/avg300**：分别对应 10 秒、60 秒、300 秒的滑动窗口

如果 `full avg10` 不为 0，说明系统正在经历严重的内存压力，ANR 很可能是内存紧张导致的连锁反应。

## 线上 ANR 的分析流程与工具链


### 标准分析流程

**第一步：确认 ANR 日志的有效性。** 搜索 EventLog 中的 `am_anr`，确认 ANR 的精确时间。然后搜索 `ANR in`，对比两者时间是否一致。如果 `ANR in` 的输出时间比 `am_anr` 延迟了 10 秒以上，说明当时系统负载很重，trace 的堆栈可能已经不是触发现场了。

**第二步：提取 ANR 基本信息。** 从 `ANR in` 行中提取进程名和 PID、ANR 原因、CPU Load 值。

**第三步：分析 traces.txt 主线程堆栈。** 根据主线程的状态和堆栈，初步判断 ANR 类型：
- Blocked → 可能是死锁或锁竞争
- Native（非 nativePollOnce）→ 可能是 I/O 等待、Binder 等待、或被冻结
- Native（nativePollOnce）→ 主线程本身没有耗时操作，可能是系统调度问题
- TimedWaiting → 主线程主动 sleep 或 wait

**第四步：分析 CPU 使用率信息。** 判断系统当时的整体状态。

**第五步：结合 SystemLog 还原场景。** 在 ANR 时间窗口内搜索 `Slow operation`、`dvm_lock_sample`、`binder_sample`、`am_kill`、`lmkd` / `lowmemorykiller`、`freeze/unfreeze` 等关键日志。

**第六步：得出结论。** 综合判断是应用问题、系统问题、还是两者叠加。

**Android 14+ trace 分组边界**：ANR trace 中出现的非主进程堆栈来源由 `ProcessErrorStateRecord.appNotResponding()` 中的 `firstPids` / `lastPids` / `nativePids` 三组列表决定。`firstPids` 包含 ANR 目标进程、parent 进程、system_server、persistent 进程、top-app IME 以及按 CPU 占用排序的热点进程；`lastPids` 包含被收集了 Binder 对端 pid 的进程；`nativePids` 是 native daemon 列表。因此 trace 中出现其他进程的堆栈，不一定是 Binder 对端——可能是 parent、system_server、IME、CPU 热点进程或 native daemon。排查时应先按分组判断来源，只有在线程栈、Binder 日志或调用链能闭合时，再判定为对端因果进程。

线上排查不一定按六步机械执行。经验丰富的工程师通常会先快速扫描 traces.txt 主线程堆栈和 CPU 使用率（第三步和第四步），形成初步假设，再根据假设决定深入哪个方向。完整流程的价值是避免漏掉关键线索，尤其是线上偶现 ANR 这种“可能只有一次机会拿到日志”的场景。

### 线上监控工具链


**ANR Watchdog 方案**：开启独立线程，定期向主线程 post 消息并检测是否被执行。实现简单（几十行代码），但有误报率，主线程 GC 或系统调度抖动都可能触发假阳性。

**ApplicationExitInfo 主路径**（Android 11+）：线上先调用 `ActivityManager.getHistoricalProcessExitReasons()` 拉取最近的进程退出记录，再筛出 `ApplicationExitInfo.reason == REASON_ANR` 的条目，并通过 `getTraceInputStream()` 读取系统在进程死亡前保存的 ANR trace。这个入口不需要拦截 `SIGQUIT`，适合做合规的离线回捞；边界是它拿到的是该进程的历史 trace 子集，不等于一份完整的 bugreport。

这段 Kotlin 代码只演示 Android 11+ 的最小回捞流程，重点看 `getHistoricalProcessExitReasons()`、`REASON_ANR` 和 `getTraceInputStream()` 三个入口：

```kotlin
val am = context.getSystemService(ActivityManager::class.java)
val exits = am.getHistoricalProcessExitReasons(null, 0, 20)
val anrExit = exits.firstOrNull { it.reason == ApplicationExitInfo.REASON_ANR }
anrExit?.getTraceInputStream()?.use { input ->
    val traceBytes = input.readBytes()
    // 落盘或上传到诊断后端
}
```

这个流程适合做线上回捞和聚合分析。如果需要更早拿到现场，或者希望补充更多线程上下文，再叠加自建监控。

**SIGQUIT 监听方案**（XCrash、Raphael 等）：通过监听 `SIGQUIT` 信号，在系统 dump traces.txt 的同时自行 dump 一份更完整的 trace。它更接近案发时刻，但要自己处理兼容性、权限边界和上传流程。

**Matrix / ArgusAPM 等完整 APM 方案**：包含 ANR 监控、卡顿监控、内存监控等完整能力，通常会把 watchdog、SIGQUIT、自定义日志聚合到同一套上报流程里。

**Perfetto 系统触发式追踪**：`ProfilingManager` 是 Android 15（API 35）新增的 profiling 服务，先提供 `requestProfiling()` 和 `registerForAllProfilingResults()` 这类基础能力；到 Android 16（API 36），再加入 `ProfilingTrigger.TRIGGER_TYPE_ANR`、`ProfilingTrigger.Builder` 和 `addProfilingTriggers()`，应用才可以把“发生 ANR 时抓一份系统 trace”注册给系统。

这段 Kotlin 代码展示 Android 16+ 的注册流程，重点看全局结果回调和 `TRIGGER_TYPE_ANR` 的绑定关系：

```kotlin
if (Build.VERSION.SDK_INT >= 36) {
    val profilingManager = context.getSystemService(ProfilingManager::class.java)
    profilingManager.registerForAllProfilingResults(context.mainExecutor) { result ->
        val path = result.resultFilePath
        // 读取并上传系统生成的 trace / profile 文件
    }
    profilingManager.addProfilingTriggers(
        listOf(
            ProfilingTrigger.Builder(ProfilingTrigger.TRIGGER_TYPE_ANR)
                .setRateLimitingPeriodHours(24)
                .build()
        )
    )
}
```

系统触发的 profiling 结果只会通过 `registerForAllProfilingResults()` 回来，Android 15 设备还没有 `addProfilingTriggers()` 这个 ANR 注册入口，只能走手动 `requestProfiling()`。

## 系统关键日志信号速查


| 日志关键词 | 含义 | 分析价值 |
|---|---|---|
| `Slow operation` | AMS 关键操作耗时 >50ms | system_server 内部繁忙 |
| `Slow dispatch` / `Slow delivery` | Handler 消息分发/投递慢 | 主线程或系统线程的 Message 处理慢 |
| `dvm_lock_sample` | 锁等待超时（默认 500ms） | 锁竞争的具体位置和持锁者 |
| `binder_sample` | Binder 调用超时（默认 500ms） | 定位哪个 Binder 接口耗时 |
| `IPCThreadState: binder thread pool starved` | Binder 线程池耗尽 | 进程间通信瓶颈 |
| `am_kill` / `am_proc_died` | 进程被杀 | 系统内存紧张或用户操作 |
| `lowmemorykiller` / `lmkd` | 低内存回收与杀进程 | 判断是否存在内存压力放大效应 |
| `freeze` / `unfreeze` | 应用被冻结/解冻 | 功耗优化导致的假死 |

## 与其他章节的关系

- **§9.1 ANR 设计思想**：理解了 ANR 的"埋雷"机制，才能理解为什么 trace 中看到的堆栈可能不是"第一案发现场"
- **§9.2 ANR 类型与触发条件**：不同类型的 ANR 有不同的超时阈值和触发路径，分析时需要区别对待
- **§1.4 Binder IPC**：Binder 超时是常见 ANR 原因，理解 Binder 通信模型有助于分析 binder_sample 日志
- **§2.4 Choreographer 与渲染流水线**：`nSyncAndDrawFrame` 出现在主线程堆栈中时，需要理解它与渲染管线的关联
- **§9.4 特殊场景的 ANR**：一些特殊场景（如冻结、Window 焦点丢失）需要额外的分析技巧
- **§9.5 ANR 案例集**：将本节的分析流程应用到具体案例中

## 常见问题与误区

**"主线程 trace 显示 `nativePollOnce`，所以 ANR 不是我的问题。"** `nativePollOnce` 只表示 dump 的那一瞬间主线程在等消息。不排除导致 ANR 的 Message 刚好在 dump 之前执行完了。

**"CPU 使用率里我的应用占比最高，所以一定是我的问题。"** 不一定。前台应用占用高 CPU 本身并不异常，要看应用在做什么。

**"ANR trace 中 D 状态就是死锁。"** 不是一回事。D 状态(Uninterruptible Sleep)通常意味着线程在等待 I/O 操作完成,或被系统 freezer 冻结。Java 层面的死锁在 trace 中显示为 `Blocked` 状态,两者不能混用。

**"系统负载高，所以 ANR 不是我的问题。"** 高负载暴露了应用主线程中本不应该存在的耗时操作。正确说法是：高负载放大了应用的潜在问题。

**"线上 ANR 发生概率极低（十万分之一），不值得修。"** 如果根因明确指向应用的某个代码路径，即使发生概率很低也建议修复——同一个根因可能在其他场景下更容易触发。

**"traces.txt 已经够用了，不需要 Perfetto。"** traces.txt 只是一个时间点的快照，无法还原 ANR 前后的完整过程。Android 17 引入了更丰富的时段采样画像能力，通过 `ProfilingManager` 的 ANOMALY 触发器，系统可以在内存压力、ANR 等异常发生前持续采集 trace 数据，为疑难问题提供时间维度的连续信息，弥补点快照模型的局限。

## 版本演进

- **Android 8.0（API 26）**：traces.txt 的格式基本定型
- **Android 10（API 29）**：ANR 日志中开始包含 Memory Pressure 信息
- **Android 11（API 30）**：新增 `ActivityManager.getHistoricalProcessExitReasons()` 和 `ApplicationExitInfo`，应用可以回捞 `REASON_ANR` 历史记录并读取 `getTraceInputStream()`
- **Android 12（API 31）**：ANR traces 的 dump 路径改为 `/data/anr/<process_name>_anr_<timestamp>`
- **Android 13（API 33）**：ANR traces 开始包含更完整的 Native 线程调用栈，Perfetto 系统层面 trace 覆盖范围扩大
- **Android 14（API 34）**：引入 `com.android.internal.os.anr.AnrLatencyTracker`，在 ANR 处理各阶段写入 Perfetto trace slice/counter（`anrRecordPlacedOnQueue`、`anrProcessing`、`dumpStackTraces()` 等）和 `ANR_LATENCY_REPORTED` statsd atom，ANR 触发到 dump 的时序可在 Perfetto 中通过这些 slice 精确观察
- **Android 15（API 35）**：新增 `ProfilingManager`，应用可以主动请求 profiling，并注册全局结果回调
- **Android 16（API 36）**：新增 `ProfilingTrigger.TRIGGER_TYPE_ANR` 和 `addProfilingTriggers()`，系统触发式 ANR profiling 正式可用

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java`
  - `frameworks/base/core/java/android/app/ApplicationExitInfo.java`
  - `packages/modules/Profiling/framework/java/android/os/ProfilingManager.java`
  - `packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java`
  - `art/runtime/thread_state.h`
  - `art/runtime/signal_catcher.cc`
- 高爷原创系列：
  - [Android App ANR 系列 2：ANR 分析套路和关键 Log 介绍](https://www.androidperformance.com/2025/02/08/Android-ANR-02-How-to-analysis-ANR/)
  - [Android App ANR 系列 3：ANR 案例分享](https://www.androidperformance.com/2025/02/08/Android-ANR-03-ANR-Case-Share/)
- [duanqz - ANR 分析](https://duanqz.github.io/2015-10-12-ANR-Analysis)
- [Gityuan - App Not Response](http://gityuan.com/2016/12/02/app-not-response/)
- [Google Developer Documentation - Diagnose ANRs](https://developer.android.com/topic/performance/anrs)
- [ActivityManager.getHistoricalProcessExitReasons()](https://developer.android.com/reference/android/app/ActivityManager#getHistoricalProcessExitReasons(java.lang.String,%20int,%20int))
- [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- [ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
