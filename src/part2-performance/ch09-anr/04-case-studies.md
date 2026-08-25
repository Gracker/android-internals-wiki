---
title: 案例集
chapter: '9.4'
section: '9.4'
status: finalized
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: 2026-07-02
last_verified_against: AOSP android-17.0.0_r1
confidence: medium
sources:
- type: blog
  path: Obsidian/Cubox/ANR-实例分析-启动应用失败-2024-12-18.md
- type: blog
  path: Obsidian/Cubox/ANR-实例分析-Input dispatching timed out-2024-12-18.md
- type: blog
  path: Obsidian/Cubox/ANR-实例分析-负载过高-2024-12-18.md
- type: blog
  path: Obsidian/Cubox/今日头条 ANR 优化实践系列 - 告别 SharedPreference 等待-2023-12-20.md
- type: blog
  path: Obsidian/Cubox/疑难ANR原因分析-冻结导致直播讲解相关完整笔记-2025-02-22.md
- type: aosp
  path: frameworks/base/core/java/android/app/SharedPreferencesImpl.java
- type: aosp
  path: frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
- type: aosp
  path: frameworks/native/libs/binder/ProcessState.cpp
tags:
- anr
- case-study
- input-dispatching
- sharedpreferences
- system-load
- binder
- process-freeze
- deadlock
- lock-ordering
- synchronized
related_chapters:
- '9.1'
- '9.2'
- '9.3'
- '1.3'
consolidated_from:
- src/part2-performance/ch09-anr/07-non-technical-anr-diagnosis.md
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
---

# 案例集

相关基础定义见 §9.1 ANR 机制、类型与触发条件、§9.2 ANR 与 Kernel Trace 联合诊断，以及 §9.3 特殊与跨边界 ANR。

## 先给证据分级

案例分析最容易犯的错误，是在时间线上找到一个可疑点，便把它写成根因。每个结论都应标明证据强度：

| 等级 | 判定条件 | 文中措辞 |
|---|---|---|
| 已确认 | 日志、trace、源码语义，加上复现或 A/B 验证，能够组成因果链；A/B 验证指只改变一个条件，对比问题是否随之出现或消失 | 根因已确认 |
| 强推断 | 多项证据指向同一方向，仍缺少一段直接证据 | 高概率相关因素 |
| 未闭合 | 只找到相关日志、异常负载或静态堆栈，时间或对象无法对齐，因果链仍有缺口 | 保留线索，继续取证 |

以下包含五个线上样本、一个匿名化的锁顺序示例，以及一个有 AOSP 提交记录支撑的历史平台缺陷。样本中的包名、时间和关键数值来自原始材料；锁顺序示例只用于完整演示死锁图的还原过程，并非线上原始事件。

| 案例 | ANR 表象 | 结论强度 | 能学到什么 |
|---|---|---|---|
| 1 | Launcher 没有焦点窗口 | 强推断 | 怎样结合 PSI、iowait 和主线程 native 栈判断系统压力 |
| 2 | Gesture Monitor 连接超时 | 未闭合 | 怎样识别时间错位和错误归因 |
| 3 | `QueuedWork.waitToFinish()` | 已确认到等待点 | `apply()`、组件收尾和 SharedPreferences（SP）初次加载的边界 |
| 4 | 被冻结进程持有输入连接 | 已确认 | freezer 日志、输入连接与 A/B 验证 |
| 5 | 目标进程启动超时后无焦点 | 强推断 | `am_process_start_timeout` 的源码含义 |
| 6 | Service 执行期间两锁互等 | 已确认于示例 | 锁图、修复边界与 Binder 资源环 |
| 7 | finished signal（输入事件完成信号）丢失导致队列积压 | 平台缺陷已确认 | 怎样用日志、源码演进和系统镜像 A/B 判断 App 是否应当负责 |

## 案例 1：高内存与 I/O 压力下的无焦点窗口 ANR

### ANR 信息

设备采用 MTK 平台并运行 Android 14，用户看到 Launcher 偶发无响应。下面的 event log（系统事件日志）确认了 ANR 类型和被记录为事件主体的进程：

```text
04-07 03:13:49.417 1444 8816 I am_anr : [0,2135,com.android.launcher,
 751550021, Input dispatching timed out
 (Application does not have a focused window)]
```

这条记录表示 InputDispatcher 等待可接收输入的焦点窗口超时。它没有说明 Launcher 主线程正在执行慢代码，也没有给出焦点消失的原因。

### 主线程不是普通的空闲等待

原始 trace 在 `03:13:49.397` 抓取。下面保留了判断线程状态所需的 native 调用链：

```text
"main" prio=5 tid=1 Native
 | state=S schedstat=( 10985995408825 3939822638104 29985904 )
 native: #00 pc 0009013c libc.so (syscall+28)
 native: #01 pc 0022cfac libart.so
   (art::ConditionVariable::WaitHoldingLocks+140)
 native: ... JNI CallObjectMethod ...
 native: ... android::NativeDisplayEventReceiver::dispatchVsync ...
 at android.os.MessageQueue.nativePollOnce(Native method)
```

Java 栈顶显示 `nativePollOnce`，native 栈却还位于 VSync（垂直同步信号）回调的返回路径，并在 ART 条件变量上等待。因此，不能把这份栈简化成“主线程空闲”。单凭 `WaitHoldingLocks` 也无法确认发生了 GC；还需要 GC cause（触发原因）、暂停日志或 Perfetto 中对应的 ART slice（带起止时间的事件片段）。

### 压力证据

ANR 报告里的 PSI 和 load 数据如下：

```text
Load: 56.48 / 30.74 / 22.68
----- Output from /proc/pressure/memory -----
some avg10=82.71 avg60=58.68 avg300=20.55
full avg10=51.17 avg60=34.93 avg300=12.29
----- Output from /proc/pressure/io -----
some avg10=85.37 avg60=63.13 avg300=23.13
full avg10=38.46 avg60=20.76 avg300=7.13
```

三个 load（系统平均负载）值依次对应 1、5、15 分钟，所以 1 分钟 load 是 `56.48`。PSI（Pressure Stall Information，资源压力停顿信息）的 `some` 表示统计窗口内至少有任务因该资源停顿，`full` 表示所有非 idle（非空闲）任务同时停顿；memory PSI 不能直接解释成“所有任务都在等待内存回收”。

同一份报告还给出了 CPU 构成：

```text
80% 84/kswapd0
55% 1444/system_server (29% kernel)
21% com.ss.android.ugc.aweme (17% kernel, many major faults)
CPU usage TOTAL: 99% 14% user + 36% kernel + 43% iowait
```

`kswapd0`（内核后台内存回收线程）活跃、major fault（需要从存储载入页面的缺页）、memory PSI、I/O PSI 和 `43% iowait` 同时出现，足以确认设备正处于严重的内存与存储压力中。`iowait` 表示 CPU 空闲期间存在尚未完成的 I/O，不能直接当作某个进程的 I/O 耗时。load 还会计入不可中断睡眠任务，因此不能只用“load 除以 CPU 核数”判断 CPU 是否饱和。

### 根因结论

**结论强度：强推断。** 系统压力是该次无响应的高概率相关因素，证据支持“线程调度和 I/O 完成被大幅延迟”。现有材料没有记录焦点从哪个窗口转移、目标窗口为何未建立，也没有覆盖 ANR 前后的 WindowManager/InputDispatcher 时间线，所以“系统压力导致无焦点窗口”仍缺一段因果证据。

若要补齐根因，需要按同一时钟收集：

- `input_focus`、窗口转场和目标 Activity 启动事件；
- Perfetto 的 `sched`（线程调度）、`ftrace/print`（内核 trace 标记）、block I/O、reclaim（内存页回收）与 ART 数据源；
- Launcher 主线程从进入 VSync 回调到返回的完整 slice；
- ANR 前后进程的 `D` 状态、major fault 和设备存储延迟。

### 修复方向

系统团队应先定位压力来源：匿名页（没有文件作为后备存储的内存页）增长、文件页反复回收和载入、频繁 major fault、写回拥塞、低速存储或某个进程的突发 I/O。应用团队应移除主线程上的文件访问、大对象分配和高频数据库写入，并在压测中复现相近的 PSI 区间。调整 I/O 优先级或 WAL checkpoint（检查点回写）参数，必须以设备、数据库页大小和写入模型的测量结果为依据；本案例不支持给出固定阈值。

这个案例留下一个实用提醒：`nativePollOnce` 只是单个采样点的 Java 入口。结合 native 栈、调度历史和系统压力，才能判断采样时主线程正在空闲、退出回调，还是等待资源。

---

## 案例 2：Gesture Monitor 连接超时，但 Notifier 证据时间错位

### ANR 信息

Launcher 在 Android 14 设备上收到下面的 Input ANR：

```text
07-20 15:01:37.293 1385 20230 I am_anr : [0,3450,com.android.launcher,
 Input dispatching timed out
 ([Gesture Monitor] swipe-up (server) is not responding.
 Waited 5001ms for MotionEvent)]
```

`Gesture Monitor` 是手势监听连接名称的一部分，括号内的完整字符串来自 InputChannel（输入通道）名称。AOSP 创建一对输入通道时，会给两个端点附加 `(server)` 和 `(client)`；这里的后缀只区分通道两端，不能证明事件消费者运行在 `system_server`，也不能单独锁定责任进程。

### 对齐时间再解释日志

原材料里还有一条 `system_server` 主线程的慢消息：

```text
07-20 15:00:45.316 1385 1385 W Looper :
 Slow dispatch took 10578ms main
 h=com.android.server.power.Notifier$NotifierHandler
```

`Slow dispatch took 10578ms` 表示这次 Handler 回调执行了约 10.6 秒。它发生在 `15:00:45` 附近，而 ANR 发生在 `15:01:37.293`；两者相差约 52 秒，已经离开此次 5 秒输入超时的直接观察窗口。

trace 头的时间也必须纳入比对：

```text
----- pid 3450 at 2024-07-20 15:00:45.488 -----
```

这份 Launcher trace 与 Notifier 慢消息接近，却比 ANR 早约 52 秒。它不能回答 `15:01:32` 至 `15:01:37` 期间 Launcher、连接消费者或 system_server 正在做什么。

ANR 报告覆盖 `15:01:27.683` 至 `15:01:37.233` 的 CPU 窗口，`system_server` 达到 `215%`，全局 CPU 约为 `64%`，同时存在 memory、CPU 和 I/O PSI。`215%` 表示多个线程合计使用了超过一个 CPU 核的算力，值得继续追查；它不能单独证明 `system_server` 主线程被阻塞。

### 根因结论

**结论强度：未闭合。** 可以确认 `[Gesture Monitor] swipe-up` 输入连接没有及时完成事件，也可以确认 `system_server` 在 ANR 窗口内 CPU 占用较高。现有 Notifier 日志和 trace 都落在约 52 秒前，不能用它们解释本次超时。

下一轮取证应完成四项对齐：

1. 从 `dumpsys input` 找到该 InputChannel 对应的 connection（连接对象）、窗口句柄、PID 和 monitor 类型。
2. 抓取 ANR 5 秒窗口内该 PID 的 Java/native trace，以及所有 `system_server` 线程的 Perfetto slice。
3. 检查 WaitQueue（已经派发、尚未收到完成通知的输入事件队列）中最老事件的序号、派发时间、超时时间和完成回调。
4. 把高 CPU 占用细分到线程，确认消耗来自 `system_server` 主线程、Binder 线程、GC 线程还是其他 native 线程。

### 修复方向

修复对象取决于补充证据。若连接消费者线程被长任务占用，应把任务移出该线程或缩短临界区；若输入 monitor（输入事件观察者）已经失去有效消费者，应修复注册和销毁时序；若 `system_server` 因调度或 I/O 延迟无法及时运行，则继续定位压力源。当前材料不足以要求修改 `Notifier`。

这个案例的价值在于展示一次应当撤回的归因：日志内容很可疑，时间却对不上。ANR 分析里，时钟和对象身份优先于关键词相似度。

---

## 案例 3：SharedPreferences 写入在组件收尾阶段阻塞主线程

### ANR 信息

原始样本在 Activity 切换期间出现下面的主线程栈：

```text
"main" prio=5 tid=1 WAIT
 at android.app.QueuedWork.waitToFinish(QueuedWork.java:176)
 at android.app.ActivityThread.handlePauseActivity(ActivityThread.java:4640)
```

这份栈确认主线程进入了 `QueuedWork.waitToFinish()`。它来自旧平台或厂商分支；Android 17 对 Activity 的等待位置已经不同。

### Android 17 的调用边界

以 `android-17.0.0_r1` 为核对版本，组件收尾与 `QueuedWork` 的关系如下：

| 组件路径 | Android 17 行为 |
|---|---|
| `ActivityThread.handlePauseActivity()` | 仅 pre-Honeycomb（Android 3.0 之前）兼容路径调用 `waitToFinish()` |
| `ActivityThread.handleStopActivity()` | 执行 stop 回调后调用 `waitToFinish()` |
| `handleServiceArgs()`、`handleStopService()` | Service 回调完成后调用 `waitToFinish()` |
| manifest Receiver 的 `PendingResult.finish()` | 仍有待处理任务时，把 `sendFinished()` 作为 finisher（收尾任务）排到 `QueuedWork` 后面 |

`SharedPreferencesImpl.apply()` 会先更新内存，再创建写盘任务和 finisher。Android 17 的 `QueuedWork.waitToFinish()` 会在当前调用线程执行尚未处理的 work（任务），随后等待并运行所有 finisher。于是，原本排给单线程 executor（执行器）的写入，可能在组件收尾点变成主线程上的同步操作。

诊断时还要区分两个栈：

- `QueuedWork.waitToFinish()` 指向全进程共享的待完成任务，常见来源是 `apply()`，也可能来自其他框架代码；
- `SharedPreferencesImpl.awaitLoadedLocked()` 表示该 SharedPreferences 实例仍在读取和解析文件，属于初次加载或加载未完成。

看到前者后，应继续寻找 `SharedPreferencesImpl$EditorImpl`、`enqueueDiskWrite()`、`writeToFile()`、`fsync()` 或 block I/O（块设备读写）证据。看到后者后，应检查文件大小、XML 解析、备份文件恢复和调用时机。两种等待不能合并成同一个根因。

### 根因结论

**结论强度：已确认到等待点。** 该样本的主线程已经进入 `QueuedWork.waitToFinish()` 并停在那里。若 trace 或 I/O 数据还能证明等待队列中的任务来自 `SharedPreferencesImpl.apply()`，便可把根因确定为 SharedPreferences 写盘；若只有样本里的这两帧栈，仍要排除其他 `QueuedWork` 使用者。

`apply()` 保证内存更新立即可见，但不保证调用后完全避开同步等待。把 `apply()` 换成 `commit()` 会更早地同步阻塞调用线程，不能解决生命周期阶段的卡顿。

### 修复方案

- 合并同一时段的多次编辑，避免每修改一个 key 就单独调用 `apply()`；
- 控制单个 XML 的键数量和序列化体积，清理不再使用的大 value（值）；
- 避免在 Activity stop、Service 回调收尾和 Receiver 完成前集中触发持久化；
- 为写文件和 `fsync()` 采集耗时，按设备与存储状态分布分析长尾；
- 对需要事务、结构化数据或稳定异步 API 的场景，评估 Preferences DataStore、Proto DataStore 或数据库；
- 预加载只能移动首次读取成本，使用前要测量启动路径和内存代价；
- 不要反射修改 `QueuedWork`、清空 finisher 或绕过组件完成通知，这会破坏持久化和框架时序。

修复验收不能只看平均写入耗时。应在应用退后台、Service 完成、广播密集和低速存储压力下，确认主线程等待的 P95/P99 与 ANR 数量同时下降。P95/P99 表示 95%/99% 的样本不超过该耗时，用于观察少数慢样本是否改善。

---

## 案例 4：Cached Apps Freezer 冻结了输入连接消费者

### ANR 信息

Android 14 设备使用手势导航时，WindowManager 报告：

```text
02-18 20:08:25.283 WindowManager:
 ANR in input window owned by pid=3930.
 Reason: Input dispatching timed out
 ([Gesture Monitor] Screenshot 0 (server) is not responding.
 Waited 5000ms for MotionEvent)
```

Cached Apps Freezer 是 Android 冻结缓存进程、减少其资源消耗的机制。这里应沿 InputChannel 找到真正接收事件的消费者 PID，不能只看被记录为事件主体的前台应用。

### 时间线与 A/B 结果相互印证

原始日志把事件派发、进程冻结和 ANR 放在了同一个 5 秒窗口：

```text
20:08:20.276  Input event delivered to [Gesture Monitor] Screenshot 0
20:08:20.289  am_freeze: [3930,com.android.systemui:screenshot]
20:08:25.283  Input dispatching timed out, waited 5000ms
```

输入事件发出 13 毫秒后，持有该输入连接的进程被冻结；约 5 秒后，未完成事件触发超时。实验还提供了 A/B 结果：关闭 freezer 后问题不再复现，重新启用后又能复现。时间关系、对象 PID 和开关实验彼此吻合。

### 根因结论

**结论强度：已确认。** 该设备的软件分支在 Gesture Monitor 仍有未完成输入事件时冻结了 `com.android.systemui:screenshot`，消费者无法运行，InputDispatcher 因等待完成回执超时。

该 Android 14 OEM（设备厂商）系统在集成 freezer 与输入 monitor 时存在生命周期协同缺陷，不能外推为所有 Android 版本都具备同一问题。Cached Apps Freezer 的启用条件、豁免规则和厂商修改都会改变行为。

在 Android 17 源码里，event log tag 仍明确记录 `am_freeze` 和 `am_unfreeze`，字段是 PID 与进程名。复核新平台时，还应同时记录 freeze/unfreeze reason（冻结或解冻原因）、目标 cgroup（控制组）状态、输入连接身份和 event ID，防止 PID 复用或旧事件干扰判断。

### 修复方案

系统修复需要围绕对象生命周期展开：

- 持有活跃输入 monitor、存在未完成 WaitQueue 事件或关键 SystemUI 会话的进程，不应进入可冻结状态；
- monitor 销毁时先停止派发并清理连接，再允许进程降级与冻结；
- 若产品设计允许按输入活动解冻，应验证解冻到线程恢复运行的时延能覆盖输入超时预算；
- 加入回归用例：事件派发后立刻触发进程状态迁移，检查 WaitQueue 能否完成或被有序取消。

应用侧无法稳定规避系统冻结输入消费者的问题。诊断脚本应按时间和 PID 自动关联 `am_freeze`、`am_unfreeze` 与 InputDispatcher reason。

---

## 案例 5：目标进程未完成 attach，焦点恢复也没有完成

### ANR 信息

用户从 Launcher 点击拨号器后，Launcher 收到无焦点窗口 ANR：

```text
05-30 12:15:49.544 am_anr : [0,2758,com.android.launcher,
 Input dispatching timed out
 (Application does not have a focused window)]
```

该 reason 由 InputDispatcher 的 focused application（当前应获得焦点的应用）超时路径生成，表示系统已经选定目标应用，等待期间却没有出现可接收输入的 focused window（焦点窗口）。

### 用 event log 还原启动与焦点

关键事件按时间排列如下：

```text
05-30 12:15:25.131 am_proc_start:
  [0,8341,10150,com.google.android.dialer]
05-30 12:15:25.138 input_focus:
  [Focus leaving ... com.android.launcher (server), reason=NO_WINDOW]
05-30 12:15:35.143 am_process_start_timeout:
  [0,8341,com.google.android.dialer]
05-30 12:15:35.153 am_kill:
  [0,8341,com.google.android.dialer,-10000,start timeout]
05-30 12:15:49.544 am_anr:
  [0,2758,com.android.launcher,... Application does not have a focused window]
```

系统在 `12:15:25` 创建 Dialer 进程并让焦点离开 Launcher。约 10 秒后，Dialer 因 process start timeout 被杀；又过了 14 秒，Launcher 所在显示区域仍没有恢复出可接收输入的焦点窗口。

### Android 17 源码怎样定义 start timeout

在 `android-17.0.0_r1` 中，`ProcessList` 启动进程后安排 `PROC_START_TIMEOUT_MSG`。应用进程通过 Binder attach（向系统注册并建立连接）到 `ActivityManagerService`；系统进入 `attachApplication()` 并准备发送 `bindApplication` 时，会移除这条 timeout 消息。若计时到期，系统会以 `ApplicationExitInfo.REASON_INITIALIZATION_FAILURE` 和 `start timeout` 终止进程。

因此，`am_process_start_timeout` 表示新进程没有按时 attach 到 AMS。这个阶段早于 `ActivityThread.handleBindApplication()` 和应用的 `Application.onCreate()`，不能用该日志证明 `Application.onCreate()` 初始化过慢。

### 根因结论

**结论强度：强推断。** Dialer 未完成 attach 与焦点窗口长期缺失处在同一条启动链上，焦点回退未完成是 Launcher 后续 Input ANR 的直接前置条件。Dialer 为何没有 attach 仍未查明，焦点为何在进程被杀后没有恢复也缺少 WindowManager 转场记录。

Dialer attach 失败时，应检查 zygote fork（由 Zygote 创建应用进程）的返回结果、进程是否进入 `D` 状态、调度延迟、native runtime 启动、seccomp/SELinux 安全策略拒绝、崩溃信号和 Binder attach 事务。此时进程尚未进入应用 Java 初始化，因此优化 `Application.onCreate()` 不是这条证据链的起点。

### 修复方案

进程侧修复取决于 attach 前的阻塞点。系统侧应在目标进程 start timeout 或启动事务取消时，撤销对应的 focused application 和 transition（窗口转场）状态，并让上一个可见窗口重新参与焦点计算。回归测试需要同时断言：

- 新进程未 attach 时会按预算终止；
- 启动 Activity 与转场记录被正确清理；
- 原窗口或错误界面重新取得输入焦点；
- InputDispatcher 中不存在已经失去对应进程或窗口的 focused application 记录。

排查“Application does not have a focused window”时，Launcher 的静态 trace 常常信息很少。`input_focus`、Activity 启动、进程 attach 和窗口可见性时间线更有辨识度。

---

## 案例 6：两把锁构成的 Service ANR

### 样本性质与 ANR 信息

本案例是从常见线上死锁形态抽出的匿名化示例，用于演示锁图分析。下面的 event log 表示系统在 Service 执行期间触发 ANR：

```text
09-12 14:37:22.815 1000 2451 I am_anr : [0,18932,com.example.app,
 852340012, executing service com.example.app.sync.SyncService]
```

Service 超时预算由 AMS（ActivityManagerService）记录的 Service 执行状态决定。常见的 20 秒前台预算取决于 `isExecServicesFg()` 等系统状态，不能只凭“这是 foreground service（前台服务）”或某个回调名判定。ANR reason 也没有说明超时发生在 `onCreate()`、`onStartCommand()`、`onBind()` 还是销毁路径，需要由调用栈进一步区分。

### 从两份线程栈画出等待环

主线程栈显示它持有 `DataManager` 锁，正在等待 `DatabaseHelper`：

```text
"main" prio=5 tid=1 BLOCKED
 | waiting to lock <0x0f3c2a81> (a DatabaseHelper)
 | held by thread "SyncWorker-2"
 at DataManager.flushCache(DataManager.java:187)
 at SyncService.onBind(SyncService.java:45)
```

主线程的等待边是 `main → DatabaseHelper`，表示主线程正在申请 `DatabaseHelper` 锁；持有边是 `DataManager → main`，表示主线程已经持有 `DataManager` 锁。

后台线程栈给出了相反方向：

```text
"SyncWorker-2" prio=5 tid=23 BLOCKED
 | waiting to lock <0x0a1b7d43> (a DataManager)
 | held by thread "main"
 at DatabaseHelper.query(DatabaseHelper.java:92)
 at SyncWorker.syncContacts(SyncWorker.java:134)
```

后台线程的等待边是 `SyncWorker-2 → DataManager`，持有边是 `DatabaseHelper → SyncWorker-2`。四条边组成一个有向循环，静态采样已经足以确认死锁。

### 代码路径

主线程路径在持有 `DataManager` monitor（`synchronized` 使用的对象锁）时跨类调用：

```java
public synchronized void flushCache() {
    databaseHelper.write(cache);
}
```

方法级 `synchronized` 让 `databaseHelper.write()` 整段调用都处于 `DataManager` 锁内。

后台路径在持有 `DatabaseHelper` monitor 时回调：

```java
public synchronized Cursor query(String table, String selection) {
    RawData data = readLocked(table, selection);
    return dataManager.buildCursor(data);
}
```

`buildCursor()` 需要 `DataManager` 锁，于是两条路径以相反顺序获取同一对锁：`DataManager`→`DatabaseHelper` 与 `DatabaseHelper`→`DataManager`。

### 根因与修复

**结论强度：已确认于示例。** 两个线程以相反顺序获取同一组锁，满足循环等待条件。

优先修复跨锁调用。下面的结构把受保护数据复制到局部变量，释放内部锁后再调用另一个对象：

```java
public Cursor query(String table, String selection) {
    RawData snapshot;
    synchronized (databaseLock) {
        snapshot = readLocked(table, selection);
    }
    return dataManager.buildCursor(snapshot);
}
```

这段改动消除了“持有 Database 锁时获取 DataManager 锁”的等待边。仍需确认 `snapshot` 由哪个对象负责修改，以及多个线程读取它是否安全，避免消除死锁后又引入数据竞争。

项目还应维护可执行的锁规则：

- 为跨模块锁定义固定层级，所有路径都按同一顺序获取锁；
- 禁止在锁内执行 Binder、文件 I/O、来源不受控的回调，或等待 Future（异步任务的结果）；
- trace 中记录锁地址、持有线程和等待线程，自动检测有向环；
- 用 Error Prone、SpotBugs 或自定义静态检查，标记持锁期间的跨类调用；
- `tryLock(timeout)` 只适合业务允许取消或降级的路径，不能当作通用死锁修复方法。

### Binder 场景的同类问题

跨进程死锁通常同时包含 Java 锁、同步 Binder 调用和线程池资源。典型的循环等待如下：

1. 进程 A 主线程持有锁 L，同步调用进程 B；
2. 进程 B 处理事务时同步回调进程 A；
3. A 的 Binder 线程为完成回调等待锁 L；
4. A 主线程等待 B 返回，锁 L 一直无法释放。

即便还有空闲 Binder 线程，这个锁等待循环也不会自行解除。另一种形态是所有处理线程都被嵌套事务或外部等待占用，新回调无法获得执行线程。

Android 17 的 `ProcessState.cpp` 定义 `DEFAULT_MAX_BINDER_THREADS = 15`，并把它作为 Binder driver（内核驱动）可以请求的默认最大线程数。调用线程主动加入线程池、已经启动的线程和 Binder 实现细节，都会影响进程中观察到的线程总数。`15` 不是固定池大小，“再留一个线程”也无法证明系统不会死锁。诊断时应画出事务方向、同步或异步属性、线程状态、锁持有关系，以及 executor（执行器）或线程池的容量。

---

## 案例 7：InputTransport finished signal 的历史平台缺陷

一个公开的旧版 Android 游戏案例记录了 InputDispatcher 等待队列持续堆积：

```text
Input dispatching timed out
(Waiting to send non-key event because the touched window has not finished
processing certain input events that were delivered to it over 500.0ms ago.
Wait queue length: 27. Wait queue head age: 5504.1ms.)
```

这段 reason 只能证明派发端当时看到 27 个未完成事件，不能单独证明游戏主线程慢，也不能直接证明平台缺陷。案例报告称 Looper 历史中没有持续到超时期限的长消息，并通过动态 input 日志把排查范围缩小到 `InputTransport.cpp`；由于原始 bugreport 与 trace 没有公开，这部分只能作为次级证据。

AOSP Gerrit 给出了更强的源码证据：

1. 2015 年 change `172237` 为适配 integer sanitizer（整数运算错误检测器），重写了若干 unsigned decrement loop（无符号整数递减循环）；
2. 2017 年 change `396876` 明确修复 `sendFinishedSignal` 的逻辑错误；
3. 后一提交说明，前一改动漏掉了把 head sequence（队首事件序号）加入 `mSeqChains` 的关键迭代步骤，使一批事件序号无法正确标记为 finished，最终令 wait queue 持续增长并触发 ANR。

**结论强度：平台缺陷已确认，具体产品事件为强推断。** AOSP 提交足以确认历史代码缺陷及其机制；产品日志与这一机制吻合，但缺少完整原始现场，不能宣称每个事件都已经与缺陷代码对应。该问题在 Android 17 源码中早已修复，不应重新套用旧补丁。

这个案例提供了一套平台归因方法：先从 reason 确认存在未完成事件，再检查 App 侧是否有足以耗尽期限的长任务；随后用 sequence/finish 动态日志缩小范围，以源码补丁解释队列为何不下降；最后在修补前后的系统镜像上运行同一输入压力测试。完成这些验证后，才能区分“系统把 ANR 记在哪个应用名下”和“问题实际产生在哪一层”。

---

## 如何用 InputDispatcher WaitQueue 分析以上案例

Android 17 的 InputDispatcher 为每个 connection（输入连接）维护 `waitQueue`，其中保存已经派发、尚未收到完成通知的事件。源码提供两组观测入口：

- `dumpsys input` 输出 connection 的 `status`、`responsive`、`isFocusMonitor`、`WaitQueue: length=` 以及队列条目；
- atrace counter（时间线计数器）`iq` 表示 inbound queue（入站队列），`oq:<channel>` 表示每个连接的 outbound queue（待派发队列），`wq:<channel>` 表示每个连接的 wait queue。

`isConnectionResponsive()` 会遍历 `waitQueue`，检查事件的 `timeoutTime`（超时时刻）是否已经过去。生成连接 ANR reason 时，`onAnrLocked()` 会读取队首条目用于诊断；源码注释也提醒，超时预算发生变化后，队首条目不一定就是触发当前超时判断的事件。

所以，队列长度只描述积压数量：

- 单个条目可能是一项长时间未完成的事件，也可能刚进入等待；
- 多个条目可能来自消费者处理速度不足、不同事件类型、MOVE 事件合并或超时预算变化；
- `length=1` 不能证明单个主线程长任务，较长队列也不能直接证明系统负载过高。

排查时要读取每个条目的 event type（事件类型）、sequence（序号）、delivery time（派发时间）、timeout time 和 connection 身份，再与主线程/Binder 线程 trace、`wq/oq` counter、调度 slice 和进程冻结事件对齐。公开 AOSP 中没有名为 `android.input.input_event_waiting_duration` 的固定 Perfetto track（时间线轨道），采集配置不应依赖这个名称。

## 一套可复用的案例复盘顺序

1. 从 `am_anr` 和 reason 确认 detector（触发超时判定的系统检测器）、被记录为事件主体的进程与输入连接名称。
2. 校验 trace 头时间、ANR 时间、CPU 统计窗口和日志时钟来源。
3. 阅读主线程 Java/native 栈，并继续追踪锁持有者、Binder 对端或 I/O 对象。
4. 用 PSI、CPU、调度、reclaim 和 block I/O 判断系统是否削弱了线程运行机会。
5. 对 Input ANR 补齐 focused application/window、connection、WaitQueue 和消费者 PID。
6. 对进程状态变化补齐 start、attach、kill、freeze、unfreeze 与 PID 生命周期。
7. 把结论写成证据链；缺少的环节保留为待取证项，不用猜测补全。

§9.2 介绍通用采集流程。复盘时，每一条日志都要同时回答“什么时候”“属于谁”“源码里代表什么”。

## 线上 ANR 聚合实践

### 官方退出信息的能力边界

Android 11（API 30）加入 `ActivityManager.getHistoricalProcessExitReasons()`。普通应用可查询自身历史退出记录，找到 `ApplicationExitInfo.REASON_ANR` 后再调用 `getTraceInputStream()`。流可能为 `null`，保留时长和数量也受系统实现与存储状态影响。

这个输入流并非完整 `/data/anr/traces.txt` 的稳定副本。Android 17 的 ANR 保存路径面向目标进程，内容通常包括头信息和目标进程的第一段 trace；不能假定流中还包含其他进程、CPU/PSI、event log 与完整系统上下文。具备系统 `DUMP` 特权权限的诊断工具与普通应用的可见范围也不同。

采集器可以按下面的公开 API 入口筛选 ANR：

```kotlin
val am = context.getSystemService(ActivityManager::class.java)
val exits = am.getHistoricalProcessExitReasons(
    context.packageName,
    0,
    32
)
val anr = exits.firstOrNull { it.reason == ApplicationExitInfo.REASON_ANR }
anr?.traceInputStream?.use { stream ->
    uploadWithSizeLimit(stream, maxBytes = 512 * 1024)
}
```

这段代码只展示查询和限量读取入口。生产实现还要对 exit record（退出记录）去重、校验时间戳、限制网络与磁盘开销，并处理 trace 缺失的情况。

### 主线程历史

ANR 瞬时 trace 可能采到 `nativePollOnce`、锁等待或耗时工作已经返回后的状态。应用可以用公开的 `Looper.setMessageLogging(Printer)` 记录主线程消息的开始和结束，但它会增加消息分发热路径上的开销，输出也不保证包含同步屏障（用于暂时阻止同步消息执行的队列标记）、native 回调和每个耗时来源。`Looper.Observer` 属于隐藏接口，不应绕过 Hidden API 限制后部署到普通应用。

历史窗口应按内存预算和目标 ANR 类型配置，并用覆盖最旧记录的环形缓冲区保存。固定“过去 10 秒”只是一种工程选择；Input、前台 Service、后台 Service 和广播的超时预算不同。采样数据至少要包含消息目标、开始/结束时间、线程 CPU 时间、wall time（实际经过时间）、队列延迟和采集版本。

### 聚合键

只按 Handler 类名与 message code（消息编号）聚合，容易把不同原因混在一起。归一化是把容易随样本变化的部分转换为稳定特征，可以采用以下维度：

- ANR detector 与 reason 模板；
- 首个应用栈帧、等待锁类型或 Binder 接口；
- 主线程前一条超长消息；
- 应用版本、Android 版本、设备/SoC（片上系统）和进程状态；
- CPU/PSI 压力桶（按压力数值划分的区间）、采样相对 ANR 的时间偏移；
- focused-window、process-start、freeze 等特征。

聚合结果应保留若干原始样本供人工复核。这里的“簇”指被归入同一组的相似 ANR；某个簇的数量很大，并不代表每个样本都共享同一根因。证据完整度应作为簇内字段参与排序。

## 检查清单

- [ ] trace 时间覆盖 ANR 的超时窗口，没有拿旧 trace 解释新事件
- [ ] InputChannel 的 `(server)`/`(client)` 只作为端点名称解析
- [ ] PSI `some`/`full`、load 1/5/15 分钟顺序没有写反
- [ ] `nativePollOnce` 结合 native 栈和调度数据解释
- [ ] `QueuedWork.waitToFinish()` 与 `awaitLoadedLocked()` 分开归因
- [ ] `am_process_start_timeout` 没有归到 `Application.onCreate()`
- [ ] freezer 结论包含 PID、事件、冻结时刻和验证实验
- [ ] 锁等待图包含持有边与等待边，能检查是否成环
- [ ] WaitQueue 读取条目时序，没有用长度直接判根因
- [ ] `ApplicationExitInfo` trace 按可空、有限、目标进程范围处理

## 参考资料

### Android 17 / API 37 源码核对版本

- [InputDispatcher.cpp：连接响应、WaitQueue、ANR reason 与 atrace counter](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)
- [InputTransport.cpp：InputChannel pair 的 server/client 端点命名](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputTransport.cpp)
- [ActivityThread.java：Activity、Service 与 QueuedWork 收尾位置](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [QueuedWork.java：待完成工作、finisher 与 waitToFinish](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/QueuedWork.java)
- [SharedPreferencesImpl.java：apply、加载等待与文件写入](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/SharedPreferencesImpl.java)
- [ProcessList.java：进程启动超时消息](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ProcessList.java)
- [ActivityManagerService.java：attachApplication 与 start timeout 处理](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [ProcessState.cpp：Binder 默认最大线程请求值](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/ProcessState.cpp)
- [InputTransport.cpp：finished signal](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputTransport.cpp)
- [am_event_tags.logtags：freeze/unfreeze event 定义](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/EventLogTags.logtags)

### 案例来源与平台文档

- [ANR 实例分析：启动应用失败](https://mp.weixin.qq.com/s?__biz=MzI0NDUxNTQ2NA==&mid=2247483907)
- [ANR 实例分析：Input dispatching timed out](https://mp.weixin.qq.com/s?__biz=MzI0NDUxNTQ2NA==&mid=2247483912)
- [ANR 实例分析：负载过高](https://mp.weixin.qq.com/s?__biz=MzI0NDUxNTQ2NA==&mid=2247483930)
- [今日头条 ANR 优化实践：告别 SharedPreference 等待](https://mp.weixin.qq.com/s/kfF83UmsGM5w43rDCH544g)
- [疑难 ANR 原因分析：冻结导致](https://mp.weixin.qq.com/s?__biz=MzkzOTQ4NDUyNg==&mid=2247489094)
- [Android Developers：诊断 ANR](https://developer.android.com/topic/performance/vitals/anr)
- [AOSP Gerrit 172237：2015 unsigned loop 重构](https://android-review.googlesource.com/c/platform/frameworks/native/+/172237)
- [AOSP Gerrit 396876：2017 sendFinishedSignal 修复](https://android-review.googlesource.com/c/platform/frameworks/native/+/396876)
