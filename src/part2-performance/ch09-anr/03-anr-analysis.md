---

title: "ANR 分析方法"
chapter: "9.3"
section: "9.3"
status: finalized
drafted_date: "2026-04-02"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-16"
last_verified_against: "AOSP android-17.0.0_r1 / Android Common Kernel android17-6.18-2026-06_r6"
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
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ProcessCpuTracker.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/ResourcePressureUtil.java"
tags: ['anr', 'traces', 'perfetto', 'analysis', 'cpu-usage', 'processcputracker', 'psi']
related_chapters: ["9.1", "9.2", "9.4", "9.5", "1.4", "2.4", "26.20"]
consolidated_from:
  - "src/part2-performance/ch09-anr/13-anr-log-cpu-analysis-methodology.md"
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
task6_state: "reviewed"
task6_result: pass-light-edit
task9_state: "reviewed"
task6_reviewed_date: "2026-05-08"
last_task6_at: "2026-05-08T20:05:00+08:00"
last_task6_audit: "2026-07-13T06:05:00+08:00"
last_task6_review_log: "logs/review/2026-05-08-20-review.md"
review_notes: "2026-05-08 task6 revisiting review: pass-light-edit。按写作规范修正禁用/填充词、结构性元叙述与中英文格式；无新增 B 类回炉问题。 | 2026-05-08 Task6 14:05：复审 Task2B 修复后的文稿，完成 frontmatter 去重、代码围栏语言标注与 L1/L2 小修；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-05-08 Task6 20:05：复审 Task2B 修复后的文稿，完成 L1/L2 轻量精修（重复句、用途句、口语化表达与结构性提示）；无新增 B 类回炉问题，等待 Task9 技术复审。"
last_task9_review_log: logs/deep-review/2026-06-06-18-audit.md
last_task9_audit: "2026-06-06"
last_task9_audit_log: "logs/deep-review/2026-06-06-18-audit.md"
last_task9_autofix_at: "2026-06-06"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-07
pipeline_stage: ready-to-publish
---

# 9.3 ANR 分析方法

## 先建立证据模型

ANR 表示系统认定某个响应期限已经超时。它没有直接说明是哪一行代码造成了超时，也没有保证保存的线程栈仍停在触发超时的代码上。分析工作的目标，是用多个时间点、多个层级的证据还原这段期限内发生的事。

源码锚点为 AOSP `android-17.0.0_r1` 和 Android Common Kernel `android17-6.18-2026-06_r6`。历史设备仍可能生成名为 `traces.txt` 的文件；Android 17 的 `StackTracesDumpHelper` 则在 `/data/anr/` 下创建以 `anr_` 开头的文件。下文用“ANR trace”统称这些线程转储文件。

一份可靠结论通常要回答五个问题：

1. **哪个监视器判定了超时**：输入、广播、Service、ContentProvider、Job 等类型的期限和触发点不同。
2. **目标进程在采样时停在哪里**：ANR trace 提供线程栈、锁等待和部分进程状态。
3. **主线程在期限内经历了什么**：Perfetto、系统事件和业务埋点提供连续时间线。
4. **系统当时能否及时调度它**：CPU 调度、频率、内存与 I/O 压力决定代码的墙上时间。
5. **证据采集晚了多久、缺了哪些进程**：采样延迟和 dump 范围决定结论强度。

单独看到 `nativePollOnce`、高 Load 或某个 `D` 状态，都不足以给 ANR 定责。先写现象，再写能够排除哪些解释，等调用链、时间线和资源证据闭合后再写根因。

## Android 17 如何生成 ANR trace

把“系统向进程发送 `SIGQUIT`，ART 写出 `traces.txt`”当作通用历史模型很容易误导排查。Android 17 的主路径由 system_server 创建 ANR 文件，再通过 `Debug.dumpJavaBacktraceToFileTimeout()` 或 native backtrace 接口请求 tombstoned/debuggerd 写入。仅在 trace 文件创建失败等退化路径上，`ProcessErrorStateRecord` 才直接向目标进程发送 `SIGQUIT`。

`StackTracesDumpHelper` 为整轮 dump 设置约 20 秒预算；单个 native dump 的超时约为 2 秒，这些值还会乘以 HW timeout multiplier。文件可能按顺序包含：

- `Subject`、超时起止时间、额外诊断头和 CriticalEventLog；
- `firstPids` 中各进程的线程栈；
- 条件允许时的 `nativePids`；
- `ProcessCpuTracker` 选出的 `extraPids`；
- 目标进程第一段 dump 之后附加的 `AnrLatencyTracker` 延迟数据。

因此，文件开头不一定紧接着 PID，文件末尾也不代表所有候选进程都成功完成了 dump。超时、进程退出、权限和本轮预算都可能留下失败标记或截断结果。

### dump 的进程范围

Android 17 在 `ProcessErrorStateRecord.appNotResponding()` 中构造三组候选：

- `firstPids` 以 ANR 目标进程开头，还可包含其 parent、system_server、persistent 进程，以及被视作 Activity 或很可能是当前输入法的进程；
- `lastPids` 收集剩余的 LRU Java 进程，随后由 `ProcessCpuTracker` 按本轮 CPU 活动挑选额外进程；
- `nativePids` 来自 `NATIVE_STACKS_OF_INTEREST`，并受调用方、进程类型和系统配置限制。

这些附加进程不是 Binder 对端清单。一个进程出现在文件里，只能证明它满足本轮候选规则。Binder 因果关系还要靠事务流、调用栈、transaction log 或对端业务日志确认。

后台静默 ANR、启动早期和排队过久等场景会缩小采集范围。Android 17 的 `AnrHelper` 在 ANR 报告进入处理队列后等待超过 10 秒时，把报告视作过期并启用 `onlyDumpSelf`；系统启动后的前 10 分钟也使用相同收缩策略。这里的 10 秒描述“报告在 system_server 队列里等了多久”，没有定义线程栈的可信阈值。

### 应用能回捞到哪一段

`AppExitInfoTracker` 保存 ANR trace 时，只复制从文件开头到目标进程第一段结束偏移的区间并压缩。应用通过 `ApplicationExitInfo.getTraceInputStream()` 读取到的是这个子集，无法据此假定 system_server、native daemon 和额外热点进程也在里面。文件可能被覆盖、清理或未成功保存，API 允许返回 `null`。

## 阅读 ANR trace

### 从头部确定问题边界

先记录 `Subject`、`Reason`、`Timeout`、进程名、PID、时间戳和触发组件。输入分发超时与广播超时即使留下相似主线程栈，分析窗口和责任链也不同。头部若包含 `TimeoutStart`，可用它对齐 Perfetto；若构建版本没有该字段，就以 `am_anr`、bugreport 时间戳和业务日志建立允许误差的时间区间。

随后确认文件是否完整：

- 目标 PID 的 `----- pid ... at ... -----` 与 `----- end ... -----` 是否成对；
- 是否出现 dump timeout、process exited、copy failed 等错误；
- 目标进程是不是第一段；
- 多进程段落是否属于同一次 ANR，避免把追加文件或相邻事件混为一组。

### 主线程栈只描述采样瞬间

下面的片段用于识别 Looper 在采样点处于空闲轮询的形态：

```text
"main" prio=5 tid=1 Native
  | sysTid=5991 nice=-10 cgrp=default sched=0/0
  | state=S schedstat=( 807053249 267562324 1494 )
  native: #00 pc ... libc.so (__epoll_pwait+...)
  native: #01 pc ... libutils.so (Looper::pollInner+...)
  native: #02 pc ... libutils.so (Looper::pollOnce+...)
  at android.os.MessageQueue.nativePollOnce(Native method)
  at android.os.MessageQueue.next(MessageQueue.java:...)
  at android.os.Looper.loopOnce(Looper.java:...)
  at android.os.Looper.loop(Looper.java:...)
  at android.app.ActivityThread.main(ActivityThread.java:...)
```

这份栈只能证明 dump 时主线程正在等下一条消息。它不能排除上一条消息刚执行完，也不能排除 ANR 监视器等待的是窗口焦点、广播完成回调、异步 Service 工作或另一进程。此时应把采样点移到 Perfetto 时间线上，向前覆盖完整超时窗口。

反过来，主线程停在业务方法也只说明采样时仍在执行该路径。定责还需确认该调用进入时间、持续时间，以及它是否位于对应 ANR 的期限内。

### 区分三类“状态”

同一线程段落里可能同时出现 ART 状态、Linux 调度状态和 Java 栈语义：

| 证据 | 示例 | 可得出的结论 |
|---|---|---|
| ART 线程状态 | `Blocked`、`Waiting`、`TimedWaiting`、`Native`、`Runnable` | ART 在 suspend point 观察到的运行或等待类型 |
| Linux 状态 | `state=R/S/D` | 内核在采样点看到的 task state |
| Java/native 栈 | `Object.wait`、`futex_wait`、`nativePollOnce` | 当前等待原语或执行路径 |

`Native` 不等于线程正在消耗 CPU。主线程在 epoll 中等消息时也显示 `Native`。`sCount` 是 ART 当前 suspend count，不能解释成历史上被 GC 或调试器暂停了多少次。

在 6.18 内核锚点中，`D` 对应 `TASK_UNINTERRUPTIBLE` 一类不可中断等待。它常见于 I/O、驱动、futex 或内核同步路径，但状态字母没有携带根因。Freezer 还有独立的 `TASK_FROZEN` 状态；cgroup v2 则通过 `cgroup.freeze` 发起冻结，并在完成后把 `cgroup.events` 的 `frozen` 更新为 `1`。只有同时出现冻结控制状态、freeze/unfreeze 事件或可闭合的调度证据，才应把停顿归到 freezer。

### 沿锁地址建立等待图

下面的片段用于演示 monitor 等待者与持有者如何关联：

```text
"main" prio=5 tid=1 Blocked
  at com.example.cache.DiskCache.read(DiskCache.kt:84)
  - waiting to lock <0x0e57c91f> (a java.lang.Object)
    held by thread 89

"CacheWriter" prio=5 tid=89 Native
  at java.io.FileDescriptor.sync(Native method)
  at com.example.cache.DiskCache.flush(DiskCache.kt:146)
  - locked <0x0e57c91f> (a java.lang.Object)
```

地址 `<0x0e57c91f>` 把两段栈连成一条边：主线程等 `CacheWriter`，后者持锁执行同步写盘。若持锁线程又等待主线程持有的锁，等待图形成环路，可判为死锁；没有环路时，它属于长临界区或锁竞争。修复点通常落在缩短持锁范围、把 I/O 移出临界区或消除相反锁序。

不要只搜索 `tid=89`。ART 的 `tid`、Linux 的 `sysTid` 和 Perfetto 的 TID 属于不同命名空间；trace 内按 ART `tid` 找持锁者，跨到 Perfetto 时用 `sysTid`。

### 识别 Binder 等待

主线程同步 Binder 调用常落在 `android.os.BinderProxy.transactNative()`、`IPCThreadState::transact()` 或 `IPCThreadState::waitForResponse()` 一带。`binder_thread_read` 常见于 Binder 线程池等待新事务，单独看到它无法证明主线程正在等某个出站调用。

Binder 分析应闭合四段证据：

1. 调用方主线程的 Java 接口与 transaction code；
2. Binder transaction 的 from/to TID、PID 和时序；
3. 对端 Binder 线程从收到事务到发送回复的运行、等待和嵌套调用；
4. 回复到达后调用方何时重新获得 CPU。

对端耗时可能来自线程池排队、对端锁竞争、磁盘 I/O、再次同步调用第三方进程，或者调用方已收到回复却长期处于 Runnable。只写“Binder 慢”会把这些不同修复方向揉在一起。

## 用采集延迟校准线程栈

Android 17 的 `AnrLatencyTracker` 为 ANR 处理过程写入 Perfetto slice/counter，并在目标进程第一段后附加 `DurationsV5` 延迟数据。常见名称包括：

- `anrRecordPlacedOnQueue` 与 `anrRecordsQueueSize`；
- `anrProcessing`；
- `dumpStackTraces()`；
- `dumpingPid#<pid>`；
- `dumpingFirstPids`、`dumpingNativePids`、`dumpingExtraPids`。

这些字段回答“报告何时排队、何时开始处理、各组 dump 花了多久”。AOSP 没有给出“低于 500 ms 就可信”之类的通用边界。栈是否仍对应触发现场，要看应用执行路径在触发时刻与采样时刻之间有没有变化。

推荐给每份证据标记以下时间：

| 时间点 | 用途 |
|---|---|
| `T_deadline` | 监视器判定超时的时刻 |
| `T_queue` | ANR 记录进入 system_server 处理队列 |
| `T_process` | ANR 消费者开始处理 |
| `T_dump_main` | 目标进程线程栈完成采样 |
| `T_log` | `ANR in` 等报告写入日志 |

若 `T_dump_main` 时主线程已进入 `nativePollOnce`，但 Perfetto 在 `T_deadline` 前显示它连续执行同一条耗时消息，时间线可以找回丢失的现场。若采样期间主线程仍停在同一路径，点快照与时间线互相增强。若两者冲突且缺少完整采集窗口，结论要降级为“疑似”，并明确缺失证据。

## 从 Perfetto 还原超时窗口

### 采集源必须覆盖问题

搜索不到 `am_anr` 不代表 trace 内没有 ANR，也可能是采集配置没有包含 Android log/EventLog 数据源。用于 ANR 的配置通常需要覆盖：

- `linux.ftrace`：调度、频率、idle、Binder 等所需事件；
- `track_event`：应用和系统的 trace section；
- `android.log`：需要用 `am_anr` 对时的 EventLog/logcat；
- `linux.process_stats`：进程、线程和部分计数器；
- 设备支持时的内存、I/O、thermal 与 power 数据源。

Android 17 的 system_server 在功能开关启用时还会发出名为 `ANR Detected` 的 Perfetto SDK instant，并携带 `anrId`、`errorId`。这是构建和开关相关信号，不能当作所有设备都具备的固定 track。

离线复现时可用下面的命令保留互补证据：

```bash
adb shell perfetto --txt -c /data/local/tmp/anr.cfg \
  -o /data/misc/perfetto-traces/anr.perfetto-trace
adb bugreport bugreport-anr.zip
adb shell ls -lt /data/anr
```

Perfetto 配置决定 trace 包含哪些数据；bugreport 补充 ANR 报告、EventLog、进程与系统快照。`/data/anr` 通常需要 root、userdebug/eng 构建或 bugreport 权限，普通应用和量产 user build 不能直接拉取。

### 选对时间窗

以 `T_deadline` 为中心，向前至少覆盖该 ANR 类型的完整响应期限，再向后覆盖目标进程 dump。输入超时需要回看输入进入、窗口焦点和分发；广播超时需要回看 receiver 调度、`onReceive()`、`goAsync()` 与 `finish()`；Service 和 Job 则要对齐对应生命周期回调。

不要从对话框出现时刻向前固定截取几秒。对话框、系统通知、`ANR in` 日志和线程 dump 都可能晚于监视器超时。

### 阅读主线程调度轨迹

| 时间线形态 | 解释方向 | 仍需确认 |
|---|---|---|
| 长时间 Running | 主线程持续执行 CPU 工作 | 调用栈、方法 trace、是否降频 |
| 长时间 Runnable，Running 很少 | 线程已可运行却没及时拿到 CPU | 每次唤醒延迟、优先级、cpuset、uclamp、竞争任务 |
| `S` 睡眠 | 等待可中断事件 | 等待原语、唤醒源、消息或 Binder 回复 |
| `D` 等待 | 不可中断内核等待 | kernel callstack、I/O/驱动事件、等待对象 |
| Blocked monitor | Java 锁未取得 | 持锁线程、锁序、持锁区工作 |

CPU 饥饿要用“Runnable 区间远大于 Running 区间”和显著 wakeup-to-run 延迟证明。整机 CPU 百分比高只能提供环境背景；大小核调度、cpuset 限制、uclamp、温控降频或一个高优先级线程都可能让主线程挨饿，即使整机仍有空闲核。

### 跟踪同步 Binder

在 Perfetto 中从调用方的 Binder transaction flow 跳到服务端线程，检查以下阶段：

- 调用方发起事务前是否已经在主线程做了重活；
- 事务是否排队等待对端 Binder 线程；
- 服务端处理期间是否被锁、I/O 或嵌套 Binder 卡住；
- reply 产生后，调用方何时被唤醒并运行；
- one-way 调用是否因队列拥塞间接影响服务端资源。

接口名和 transaction code 可以帮助定位 Stub 方法，但不同构建的 EventLog tag 或采样格式不保证相同。优先依赖 Binder flow 与双方调用栈，日志字段按该设备的 `event-log-tags` 解释。

### 用 Perfetto SQL 批量抽取线程状态

这条查询用于导出指定进程主线程的状态区间，便于计算期限内 Running、Runnable 与阻塞时间：

```sql
SELECT
  thread_state.ts,
  thread_state.dur,
  thread_state.state,
  thread_state.cpu
FROM thread_state
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE process.name = 'com.example.app'
  AND thread.name = 'main'
ORDER BY thread_state.ts;
```

`ts` 和 `dur` 使用 trace processor 的纳秒时间基准。不同 Perfetto 版本对状态字符串和可选列可能有差异，批处理前应通过 `.schema thread_state` 核对当前 trace processor，再按 `T_deadline` 的时间范围过滤和聚合。SQL 结果给出状态时长，根因仍需调用栈、flow 和系统计数器支持。

## 常见根因的证据链

### 主线程执行过久

特征是主线程在期限内持续 Running，栈落在布局、序列化、图片处理、正则、大集合遍历或业务循环。采样点可能只命中路径尾部，因此应结合 method trace、自定义 section 和多个样本确认热点。

修复时把工作拆成两部分：

- UI 状态读取与 View 更新留在主线程，限制单次预算；
- 可并行的计算、解析、解码移到后台，并在回主线程前处理取消、过期结果和生命周期。

把一个长任务切成大量主线程消息只能改善单次占用，消息总量和 deadline 仍需测量。

### 主线程 I/O

Java 栈可能出现 `FileInputStream.read()`、`FileOutputStream.write()`、SQLite、`fsync()`、资源解压或类加载；native 栈和 Perfetto 则可能显示 page fault、block I/O 或 `D` 等待。少量代码也可能因冷页、存储抖动和同步落盘产生很长墙上时间。

`SharedPreferences.apply()` 的数据写入异步排队，但组件停止阶段可能通过 `QueuedWork.waitToFinish()` 等待未完成工作。分析时要检查此前累计写入量、生命周期边界和 `fsync()`，不能只看 `apply()` 调用本身返回得快。

修复方向包括后台 I/O、批量提交、减少同步持久化、缓存热身和缩小关键路径。涉及用户可见状态时，还要设计进程被杀后的恢复语义。

### 锁竞争与死锁

死锁需要一条闭合等待环；单向等待属于锁竞争。常见放大器有：

- 持锁执行磁盘或 Binder 调用；
- 主线程与工作线程使用相反锁序；
- 回调在持锁状态下调用未知代码；
- 大对象复制、遍历或清理放进临界区；
- 读写锁的写者饥饿。

线程栈只能显示采样点的等待图。短时重复竞争还可结合 `monitor contention`、`dvm_lock_sample`、Perfetto slice 或应用埋点统计持锁时长。

### 同步 Binder 卡住

调用方主线程等回复时，根因多半位于调用链更深处。先找服务端执行线程，再判断是排队、服务代码、服务端锁、服务端 I/O、嵌套调用还是调用方调度延迟。

可控接口应避免在主线程发起无期限同步工作，或把重操作改为异步协议。系统服务接口无法改动时，可减少调用次数、缓存稳定结果、把允许异步的查询移出 UI 期限，并处理服务死亡与超时降级。不要在未知线程安全约束下机械搬运 API。

### CPU 饥饿与系统负载

CPU 饥饿的直接证据是目标线程可运行却迟迟没有 Running。追查顺序可按：

1. 同 CPU 或同 cpuset 上有哪些竞争线程；
2. 目标线程 nice、调度组、uclamp 和优先级是否异常；
3. CPU 频率、idle、thermal 是否压低可用算力；
4. GC、JIT、编解码、system_server 或厂商守护进程是否制造突发负载；
5. 唤醒路径是否存在调度器或驱动异常。

“系统负载高”描述环境，不自动免除应用责任。若主线程仍放着可移除的同步 I/O 或长计算，高负载会让这段工作更容易超过时间预算；若主线程长期 Runnable 且应用路径没有超预算工作，责任更可能落在调度与系统资源侧。结论里应把触发条件和可修复因素分开写。

### 内存回收、GC 与 page fault

GC 需要结合 pause slice、并发阶段、分配速率和主线程停顿判断。`minor faults` 表示无需从块设备读取即可处理的缺页；`major faults` 通常涉及存储后备页读入，但数量要放在统计区间、进程工作集和 I/O 时间线上解释。单个 major fault 计数不能证明 ANR 来自磁盘。

若 `kswapd`、direct reclaim、频繁 major fault、memory PSI 与 lmkd 事件在同一窗口出现，内存压力链条更可信。还要区分应用工作集膨胀、系统全局压力和厂商内存策略。

## 解读 ANR 报告里的 CPU 与压力信息

### CPU 百分比

ActivityManager 使用 `ProcessCpuTracker` 输出某个采样区间内各进程的 user、kernel 与总 CPU 占比。多核设备上单进程超过 100% 合法，表示它在区间内并行消耗了一个以上 CPU 核的时间。

下面的片段用于说明字段之间的关系：

```text
CPU usage from 0ms to 13135ms later:
  191% 1948/system_server: 72% user + 119% kernel
      / faults: 78816 minor 9 major
  30% 5991/com.example.app: 23% user + 6.4% kernel
      / faults: 118172 minor 2 major
```

这份快照说明 system_server 在该区间消耗了约 1.91 个核的 CPU 时间，其中内核态占比较高。它没有指出内核时间花在 Binder、文件系统、内存管理还是驱动上；需要 Perfetto callstack、系统计数器或更细的 profile 继续拆分。

分析时同时看：

- 统计区间是否覆盖 `T_deadline`；
- 目标进程、system_server 与全局总量；
- user/kernel 的相对变化；
- 短区间和长区间是否呈现同一热点；
- 进程 CPU 低时，主线程是 Sleeping、Blocked、`D` 还是长期 Runnable。

### Load Average

`Load: 15.29 / 5.19 / 1.87` 是 1、5、15 分钟指数移动平均，统计可运行任务与不可中断等待任务。它不等于 CPU 利用率。8 核设备的 Load 为 8，既可能是八个任务持续使用 CPU，也可能混有等待 I/O 的 `D` 状态任务；短暂 ANR 还可能被 1 分钟平均稀释。

Load 适合提示“系统近期有多少任务在争用或等待”，不能单独证明 CPU 满载。用 Perfetto 的 sched、CPU frequency/idle 与 I/O 轨迹区分来源。

### PSI

Android 17 所用 6.18 内核通过 `/proc/pressure/{cpu,memory,io}` 暴露 Pressure Stall Information：

- `some`：至少有一部分任务因该资源停顿的时间占比；
- `full`：所有 non-idle 任务同时因该资源停顿的时间占比；
- `avg10`、`avg60`、`avg300`：10、60、300 秒趋势百分比；
- `total`：自启动以来累计停顿微秒数。

系统级 `cpu.pressure` 的 `full` 没有可用语义，为兼容保持为 0。memory 或 I/O 的 `full` 非零说明窗口内发生过全体 non-idle 工作停顿，但一次很短的尖峰可能与当前 ANR 无关。应计算 ANR 窗口内 `total` 的增量，配合 avg 趋势、reclaim、block I/O 与目标线程状态判断相关性。

下面的样例用于说明 PSI 行的格式：

```text
----- Output from /proc/pressure/memory -----
some avg10=1.35 avg60=0.31 avg300=0.06 total=346727
full avg10=0.00 avg60=0.00 avg300=0.00 total=34803
----- End output from /proc/pressure/memory -----
```

这里的 `full avg10=0.00` 只表示按显示精度计算的最近 10 秒趋势为零；累计 `total` 仍可能包含更早的 full stall。要判断当前事件，应比较两个邻近采样的 `total`，不能用启动以来的累计值直接归因。

### CPU 摘要的两种采样窗口

Android 17 的 ANR 路径可能输出两套 `ProcessCpuTracker` 结果，二者不能混成同一时间窗：

| 结果 | 采样器 | 内容 | 时间边界 |
|---|---|---|---|
| 全局进程榜 | `AppProfiler.mProcessCpuTracker` | 最多十个活跃进程，不含线程明细 | 长期复用；两次更新至少间隔 5 秒，区间可能跨过 ANR |
| 临时进程榜 | `new ProcessCpuTracker(true)` | 活跃进程及其活跃线程 | `init()` 后等待约 200 ms 再 `update()`；用于挑选最多两个额外抓栈进程，静默后台 ANR 可能跳过 |

`ProcessErrorStateRecord` 记录的 `anrTime` 位于 ANR 处理开始附近。临时榜通常在它之后采样，因此标题可以出现 `ms later`；长期榜则可能覆盖 deadline 之前、之后或两侧。解析每个 CPU 块时应保存 `sample_start`、`sample_end`、`duration`、相对 `anrTime` 的方向、采样器类型，以及与超时窗口的重叠关系。只覆盖转储阶段的数据，只能说明“抓栈时仍观察到该现象”。

进程和线程行以各自两个采样点之间的 uptime 为分母，多线程进程超过 `100%` 合法。`TOTAL` 行的分母则是所有 CPU 的 `/proc/stat` 增量总和；其非 idle 百分比包含 `iowait`，不能当作纯执行利用率，也不能和进程行直接相减。AOSP `ProcessCpuTracker` 的标准输出不会附带 `R/S/D`，带状态字符的格式应按厂商扩展或其他采集器解析，并保留来源命名空间。

`minor`、`major` fault 是两个采样点之间的事件数，不是分配量或 I/O 字节数。页大小可能是 4 KB、16 KB 或其他值，major fault 的后备介质也可能是 zram；只有当 fault 增量与 D 状态、reclaim、文件系统或 block I/O 在同一时间窗闭合时，才能提高存储或内存压力解释的可信度。

自动解析器应把输出严格分为三层：

1. **事实字段**：原始时间窗、进程/线程 user 与 kernel、fault delta、`TOTAL`、load 和 PSI；
2. **派生观察**：跨核执行、全机繁忙、资源压力，以及采样与 deadline 是否重叠；
3. **候选解释**：每项同时列出支持证据、反证、缺失材料和规则版本。

不要内置跨设备的固定结论，例如 “iowait 超过 5% 就是 I/O 瓶颈” 或 “major fault 超过 100 次就是磁盘问题”。阈值应来自同机型、同场景、同采样窗口的基线；时间不重叠、字段缺失或 OEM 格式未知时，解析器要降低置信度并保留原文。

## 一套可复用的分析流程

### 1. 固定事件身份

记录 build fingerprint、Android 版本、进程、PID/UID、ANR 类型、`anrId/errorId`（若有）、组件、`T_deadline` 和用户动作。一个 bugreport 可能包含多次 ANR，PID 也会复用，时间与事件 ID 必须一起使用。

### 2. 检查采集完整性

确认目标进程段是否完整、采样延迟、是否 `onlyDumpSelf`、ApplicationExitInfo 是否仅有第一进程段、Perfetto 数据源是否覆盖 sched/Binder/log。缺失项写进结论，避免把“没采到”写成“没有发生”。

### 3. 按 ANR 类型划定期限

从监视器的开始事件向后追到 deadline：

- 输入：输入事件、焦点窗口、目标连接、主线程分发；
- 广播：receiver 调度、`onReceive()`、异步 pending result 完成；
- Service：创建、启动、绑定或前台服务晋升所对应的检查点；
- ContentProvider：发布或跨进程调用的具体监视路径；
- Job：绑定、回调、运行期限或用户发起任务通知要求。

类型边界和 Android 17 期限见 [§9.2 ANR 类型与触发条件](02-anr-types.md)。

### 4. 为主线程分类

把期限拆成 Running、Runnable、Sleeping、monitor blocked、Binder wait、I/O/`D` wait。先找占比最大的区间，再读该区间的调用栈、锁和 flow。采样栈与时间线一致时提高置信度；不一致时解释采样漂移。

### 5. 沿等待边追到资源拥有者

锁等待找持锁线程，Binder 等待找服务端线程，I/O 等待找文件系统/块设备，Runnable 找 CPU 竞争者。每跨一层都记录 PID/TID、开始时间、结束时间和证据来源。

### 6. 检查系统放大因素

检查 CPU 竞争、频率、thermal、GC、reclaim、PSI、lmkd、I/O 和 freezer。系统异常与应用慢路径可以同时存在，报告中分别列出主因、触发条件和放大因素。

### 7. 用反事实验证修复

一个可执行根因应能回答：去掉某段同步工作、缩短某个持锁区、改变某个 Binder 协议或解除某项资源限制后，deadline 为什么能够满足。修复后用同一场景比较期限内主线程状态、P95/P99 耗时与 ANR Rate，防止只让采样栈换了位置。

## 线上工具链

### `ApplicationExitInfo` 回捞

Android 11（API 30）起，应用可查询自身历史退出记录并读取系统保留的 ANR trace。下面的代码用于把可用的第一份 ANR trace 流式保存到应用私有目录：

```kotlin
if (Build.VERSION.SDK_INT >= 30) {
    val activityManager =
        context.getSystemService(ActivityManager::class.java)
    val exit = activityManager
        .getHistoricalProcessExitReasons(null, 0, 20)
        .firstOrNull {
            it.reason == ApplicationExitInfo.REASON_ANR
        }

    exit?.traceInputStream?.use { input ->
        val destination = File(
            context.noBackupFilesDir,
            "anr-${exit.timestamp}.txt"
        )
        destination.outputStream().buffered().use { output ->
            input.copyTo(output, bufferSize = 64 * 1024)
        }
    }
}
```

`traceInputStream` 允许为 `null`，代码必须把“记录存在”和“trace 可读”分开处理。Android 17 保存的是目标进程第一段及其前置头部，不是完整 bugreport。上线还要限制保留数量、文件大小、上传网络条件，并按隐私规范清洗用户数据。

### Watchdog 与业务埋点

Watchdog 线程定期向主线程投递探针，可以在系统判定 ANR 前保存队列、页面、业务阶段和自定义栈。它测到的是“探针没有按期执行”，GC、调度饥饿、debugger 和设备休眠都可能触发，因此不能代替系统 ANR 统计。

高价值埋点通常包括：

- 主线程长消息的开始/结束与业务标签；
- 关键同步 Binder 的接口、对端和墙上时间；
- 主线程 I/O 与锁持有时间；
- 页面、输入动作、广播/Service/Job 生命周期；
- build、设备、thermal、内存等级和采样延迟。

探针阈值要按场景和设备分层，线上上报需要采样、限流与去重。

### ProfilingManager 触发式采集

`ProfilingManager` 在 Android 15（API 35）加入公开 API；Android 16（API 36）的 `ProfilingTrigger` 提供 `TRIGGER_TYPE_ANR`。系统识别 ANR 后、可能杀进程前，可从正在后台运行的系统 trace 中取一份快照。触发不保证应用会被杀，也不保证每次都有结果：后台 trace 是否活跃、环形缓冲区、系统规则和 rate limit 都会影响产物。

下面的代码用于在 API 36 及以上注册 ANR trigger，并接收系统返回的 profiling 文件：

```kotlin
if (Build.VERSION.SDK_INT >= 36) {
    val profilingManager =
        context.getSystemService(ProfilingManager::class.java)

    profilingManager.registerForAllProfilingResults(
        context.mainExecutor
    ) { result ->
        val resultPath = result.resultFilePath
        // 在回调外执行校验、压缩与合规上传。
    }

    profilingManager.addProfilingTriggers(
        listOf(
            ProfilingTrigger.Builder(
                ProfilingTrigger.TRIGGER_TYPE_ANR
            )
                .setRateLimitingPeriodHours(24)
                .build()
        )
    )
}
```

触发式结果只投递给通过 `registerForAllProfilingResults()` 注册的全局 listener。生产代码还要检查 `ProfilingResult` 的 error code、文件生命周期和重复注册。Android 17（API 37）新增的 `TRIGGER_TYPE_ANOMALY` 面向系统检测到的通用异常，产物类型依 anomaly tag 而定；ANR 采集应继续使用语义明确的 `TRIGGER_TYPE_ANR`。

### SIGQUIT hook 的边界

部分 APM 会拦截或旁路观察 `SIGQUIT`，再自行采集线程栈。这类实现依赖 ART、信号处理、tombstoned 路径和厂商改动，可能与系统 dump 竞争，也可能在目标版本失效。Android 17 的 ANR 主路径没有保证第三方一定收到可用于 hook 的 `SIGQUIT`。它适合作为经过版本验证的补充信号，不能取代 `ApplicationExitInfo`、Perfetto 和系统事件。

## 线上指标与聚类

自建监控可同时保留三种口径：

- **事件率**：ANR 事件数 / 会话数，能反映同一会话反复发生的情况；
- **受影响会话率**：发生过至少一次 ANR 的会话数 / 会话数；
- **受影响用户率**：发生过至少一次 ANR 的用户数 / 活跃用户数。

Google Play Android vitals 按 daily active user 计算：ANR rate 的分子是当天至少遇到一次任意 ANR 的用户；user-perceived ANR rate 的分子是当天至少遇到一次用户感知 ANR 的用户。当前公开定义把 `Input dispatching timed out` 计入用户感知 ANR。厂商平台和自建 APM 可能使用会话、事件或设备作为分母，报表必须标注去重周期、前后台过滤和分母。只按事件总量排序会掩盖低频高影响事件，也会让单个重度用户放大计数。

聚类键建议从稳定到易变分层：

1. ANR 类型、组件与规范化主线程栈；
2. 第一条应用帧、等待对象或 Binder 接口；
3. build、设备 SoC、Android 版本和厂商；
4. 前台页面、业务动作与系统压力标签；
5. 采样延迟、trace 完整度和证据等级。

代码行号、混淆方法名和对象地址会随构建变化，不适合直接作为长期 fingerprint。修复验收应同时看该聚类 Rate、影响用户数、P95/P99 期限耗时和新旧 build 分布。

## 系统日志信号速查

| 信号 | 能说明什么 | 不能直接说明什么 |
|---|---|---|
| `am_anr` / `ANR in` | ANR 事件与报告信息 | 二者时间差本身不等于系统负载 |
| `Slow dispatch` / `Slow delivery` | 某条 Handler 消息调度或交付较慢 | 不自动指向当前应用 |
| `dvm_lock_sample` | ART 采样到 monitor 竞争 | 阈值和采样策略随构建配置变化 |
| `binder_sample` | 构建配置采样到慢 Binder | 字段顺序和阈值不是跨版本固定协议 |
| `binder thread pool starved` | 某进程 Binder 线程池长时间没有可用线程 | 需要继续找占用各线程的事务 |
| `am_kill` / `am_proc_died` | 进程退出或被系统处理 | 需要 reason/subreason 判断原因 |
| `lmkd` / reclaim / PSI | 内存压力及其处置 | 单条事件不能证明当前 ANR 的因果关系 |
| freeze / unfreeze | 进程或 cgroup 冻结状态变化 | 需要与目标 PID 和超时窗口对齐 |

日志中的固定毫秒数往往来自设备配置、采样率或厂商修改。分析报告应保留原始字段并注明构建版本，避免把某台设备的阈值写成 Android 平台契约。

## 常见误判

### `nativePollOnce` 代表应用没有责任

它仅证明采样点空闲。回看 `T_deadline` 前的主线程消息、输入 flow 和 ANR 类型，才能知道导致期限耗尽的工作是否已结束。

### 应用 CPU 占比最高就要优化 CPU

前台计算、渲染和启动都可能让应用成为区间热点。确认主线程是否长期 Running、热点是否位于 deadline 路径、移除后能否降低墙上时间，再决定优化对象。

### `D` 状态等于磁盘慢或被冻结

`D` 只给出不可中断等待类别。kernel callstack、block I/O、驱动事件或 cgroup 冻结证据决定具体解释。

### 高 Load 足以证明系统问题

Load 同时计入可运行和不可中断等待任务，并使用较长移动窗口。ANR 期限内的 sched、频率、I/O 与 PSI 才能说明目标线程受到了什么影响。

### trace 中的附加进程都是 Binder 对端

Android 17 还会收集 parent、system_server、persistent、可能的输入法、native interest 进程和 CPU 活跃进程。只有 transaction flow 或双方栈能证明对端关系。

### 一份 ANR trace 足够覆盖全程

线程转储是采样点，ApplicationExitInfo 还只保存目标第一段。疑难问题需要 Perfetto、系统日志、业务事件和多次同类样本补足过程。

## 已验证的公开 API 演进

- **Android 11（API 30）**：加入 `ActivityManager.getHistoricalProcessExitReasons()` 与 `ApplicationExitInfo`，应用可查询 `REASON_ANR` 并尝试读取保留 trace。
- **Android 15（API 35）**：加入 `ProfilingManager`，支持应用请求 profiling 并注册全局结果 listener。
- **Android 16（API 36）**：加入 `ProfilingTrigger`、`TRIGGER_TYPE_ANR` 与触发式 profiling 注册。
- **Android 17（API 37）**：加入通用 `TRIGGER_TYPE_ANOMALY`；它没有替代专用的 ANR trigger。

文件名、dump 进程范围和日志格式属于实现细节，应以目标构建源码为准。平台实现锚点固定为 `android-17.0.0_r1`。

## 与其他章节的关系

- [§9.1 ANR 设计思想](01-anr-design.md)：监视器、deadline 与报告路径。
- [§9.2 ANR 类型与触发条件](02-anr-types.md)：各类型的 Android 17 触发边界。
- [§1.4 Binder IPC](../../part1-fundamentals/ch01-architecture/04-binder.md)：同步事务、线程池与调用链。
- [§2.4 Choreographer 与渲染流水线](../../part1-fundamentals/ch02-rendering/04-choreographer.md)：主线程帧调度和渲染期限。
- [§9.4 特殊与跨边界 ANR](04-special-anr.md)：冻结、焦点和厂商场景。
- [§9.5 ANR 案例集](05-case-studies.md)：把证据流程用于完整案例。

## 参考资料

- [Android Developers：诊断和修复 ANR](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Android Developers：Android vitals 的 ANR 指标](https://developer.android.com/topic/performance/vitals/anr)
- [Android Developers：ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [Android Developers：ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Android Developers：trigger-based capture](https://developer.android.com/topic/performance/tracing/profiling-manager/trigger-based-capture)
- [AOSP android-17.0.0_r1：ProcessErrorStateRecord](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessErrorStateRecord.java)
- [AOSP android-17.0.0_r1：ProcessCpuTracker](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ProcessCpuTracker.java)
- [AOSP android-17.0.0_r1：AppProfiler](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppProfiler.java)
- [AOSP android-17.0.0_r1：ResourcePressureUtil](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/ResourcePressureUtil.java)
- [AOSP android-17.0.0_r1：StackTracesDumpHelper](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/StackTracesDumpHelper.java)
- [AOSP android-17.0.0_r1：AnrHelper](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java)
- [AOSP android-17.0.0_r1：AnrLatencyTracker](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/anr/AnrLatencyTracker.java)
- [AOSP android-17.0.0_r1：AppExitInfoTracker](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppExitInfoTracker.java)
- [AOSP android-17.0.0_r1：ApplicationExitInfo](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java)
- [AOSP android-17.0.0_r1：ProfilingManager](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingManager.java)
- [AOSP android-17.0.0_r1：ProfilingTrigger](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [Android Common Kernel android17-6.18-2026-06_r6：PSI](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/accounting/psi.rst)
- [Android Common Kernel android17-6.18-2026-06_r6：task state](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/sched.h)
- [Android Common Kernel android17-6.18-2026-06_r6：cgroup v2 freezer](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/Documentation/admin-guide/cgroup-v2.rst)
- [高爷：Android App ANR 系列 2——ANR 分析套路和关键 Log 介绍](https://www.androidperformance.com/2025/02/08/Android-ANR-02-How-to-analysis-ANR/)
- [高爷：Android App ANR 系列 3——ANR 案例分享](https://www.androidperformance.com/2025/02/08/Android-ANR-03-ANR-Case-Share/)
