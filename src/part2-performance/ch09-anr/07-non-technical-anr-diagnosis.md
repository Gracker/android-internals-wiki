---

title: ANR 非技术故障诊断
chapter: '9.7'
status: finalized
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
tags:
- anr
- non-technical
- fault-diagnosis
- system_server
- binder
- perfetto
related_chapters:
- '9.3'
- '13.6'
- '15.2'
- '1.4'
created_by: task2a-knowledge-gap
created_date: '2026-04-10'
gap_source: 研究素材
confidence: medium
sources:
- type: blog
  path: Cubox/有时候你APP发生的ANR不是你的错-分享 1个 Google 工程师没 bug 改出 bug 的一个案例-2025-04-21.md
  title: 有时候你 APP 发生的 ANR 不是你的错
  date: '2025-04-21'
- type: official
  path: https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs
  title: Diagnose and fix ANRs
  date: '2026-04-14'
- type: official
  path: https://developer.android.com/topic/performance/vitals/anr
  title: Android vitals, ANR
  date: '2026-04-14'
- type: official
  path: https://perfetto.dev/docs/data-sources/cpu-scheduling
  title: Perfetto CPU scheduling
  date: '2026-04-14'
- type: aosp
  path: frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
  title: Input dispatch timeout tracking
  date: android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/AnrHelper.java
  title: ANR reporting helper
  date: android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
  title: Service timeout constants
  date: android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java
  title: Broadcast timeout record
  date: android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java
  title: Content provider ANR entry
  date: android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/ContentResolver.java
  title: ContentProvider timeout constants
  date: android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/ContentProviderClient.java
  title: Provider not-responding detector
  date: android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
  title: ContentProvider timeout messages
  date: android-17.0.0_r1
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: 2026-07-13
section: '9.7'
reviewed_by: openclaw-task6
reviewed_date: "2026-06-04"
task6_result: pass-light-edit
task9_result: auto-fixed
last_verified: "2026-07-13"
last_verified_against: AOSP android-17.0.0_r1
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-13
last_task9_at: "2026-06-13T01:20:00+08:00"
review_notes: "2026-05-18 task9 idle audit: needs-rework。P1 2(ContentProvider timeout/source semantics;Android 15+ 16KB page-size version boundary),P2 1(InputDispatcher Android 8-10 path note);已写入 queue/suggestions,等待 Task2B 回炉。 | 2026-05-23 task6 idle audit: queue 中仍有 pending 回炉项,撤销 finalized 状态,保持 task2b_pending。"
auto_promoted: true
last_task9_autofix_at: 2026-06-13
last_task9_audit: 2026-06-13
last_task6_audit: "2026-07-12"
last_task9_review_log: logs/deep-review/2026-06-13-01-audit.md
task9_review_notes: "2026-06-13 Task9 idle audit auto-fix: 修正 ContentProvider WAIT_FOR_CONTENT_PROVIDER_TIMEOUT_MSG 与 setDetectNotResponding 路径混用。P0 1(auto-fixed) / P1 0 / P2 0；回到 Task6 复审。"
finalized_date: "2026-06-04"
finalized_by: openclaw-task9-auto-promote
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-16
---

# ANR 非技术故障诊断

<!-- outline-start -->
## 要点

### 🔹 锚点 1:按 ANR 类型确定超时预算与责任边界
### 🔹 锚点 2:用 EventLog、traces 和 Perfetto 还原等待链
### 🔹 锚点 3:识别 system_server、Binder、CPU/内存、存储 四类系统侧根因
### 🔹 锚点 4:按 Android 8-17 的工具边界选择抓取手段
### 🔹 锚点 5:用公开案例说明 App 如何被框架层 bug 连坐
<!-- outline-end -->

## “非技术故障”在本节指什么

这个标题沿用知识库的原始命名，含义是“根因不在被记账应用的业务代码”。system_server 锁竞争、远端 Binder 阻塞、调度饥饿、存储停顿和平台缺陷都属于技术故障，只是责任边界跨出了当前 App。

ANR subject 记录被系统判定为无响应的进程或组件。它不是根因判决书。跨进程场景要按下面的顺序取证：

1. 确认超时检测器、预算和被记账对象；
2. 找到超时线程正在等待的资源；
3. 沿 Binder、锁、输入连接或进程启动链找到对端；
4. 检查超时窗口内的调度、内存、I/O 和进程状态；
5. 给结论标注“应用侧”“系统侧”“共同作用”或“证据不足”。

通用采集流程见 [[ANR 分析方法|§9.3 ANR 分析方法]]，线程状态见 [[线程 CPU 状态分析|§13.6 线程 CPU 状态分析]]，归因规则见 [[如何区分系统问题和 App 问题|§15.2 如何区分系统问题和 App 问题]]。

## 第一步：先认出超时检测器

不同 ANR 的计时起点和结束条件不同。下面的预算是 AOSP/Pixel 默认范围，OEM 可通过超时倍数或平台实现调整。

| 检测器 | 常见 subject / reason | AOSP 默认预算 | 计时范围 |
|---|---|---:|---|
| Input connection | `Input dispatching timed out (... is not responding)` | 5 秒 | 事件派发后等待 connection 完成 |
| No focused window | `Application does not have a focused window` | 5 秒 | focused application 存在，却迟迟没有 focused window |
| Execute service | `executing service ...` | 进程按前台执行 20 秒，后台执行 200 秒 | 包含必要的冷启动与 Service 回调 |
| Broadcast receiver | `Broadcast of Intent ...` | 前台 10 秒、后台 60 秒；Android 14+ 在 CPU-starved 时可扩到 20/120 秒 | 派发到 `onReceive()` 返回或 `PendingResult.finish()` |
| ContentProvider call | `ContentProvider not responding` | 由系统客户端调用 `setDetectNotResponding()` 配置 | 远端 Provider 调用总时长，可能包含冷启动 |

Service 的“前台/后台”取决于 AMS 对进程执行 Service 的状态，例如 `isExecServicesFg()`，不能只看 Service 是否调用过 `startForeground()`。Broadcast 的前台预算由 Intent 的 `FLAG_RECEIVER_FOREGROUND` 决定。

### Input：连接等待与焦点等待是两条路径

Android 17 的 `InputDispatcher::processAnrsLocked()` 同时检查两类条件：connection 的 waitQueue 是否有事件超过 timeout，以及 focused application 是否长时间没有 focused window。

下面的源码片段给出默认预算来源和调度循环入口：

```cpp
const auto DEFAULT_INPUT_DISPATCHING_TIMEOUT =
        std::chrono::milliseconds(
                android::os::IInputConstants::
                        UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS
                * HwTimeoutMultiplier());

const nsecs_t nextAnrCheck = processAnrsLocked();
```

connection 超时已经有事件进入 waitQueue，需要追踪消费者和完成回执。No-focused-window 超时还没有可派发的焦点窗口，需要追踪 Activity、WindowManager、转场与焦点状态。两条路径都可能把前台应用写进 subject，证据入口不同。

InputChannel 名称里的 `(server)` / `(client)` 由 `openInputChannelPair()` 给端点命名。`(server) is not responding` 不等于“system_server 不响应”，必须从 connection 或窗口句柄解析消费者 PID。

### Service 与 Broadcast：TimeoutRecord 负责描述原因

Android 17 的 Service 基线常量仍是 20 秒和十倍的后台预算。Broadcast 超时路径会创建 `TimeoutRecord.forBroadcastReceiver(...)`，再进入应用无响应处理。下面的缩写只展示两个源码锚点：

```java
private static final long DEFAULT_SERVICE_TIMEOUT =
        20 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;
private static final long DEFAULT_SERVICE_BACKGROUND_TIMEOUT =
        DEFAULT_SERVICE_TIMEOUT * 10;

TimeoutRecord record = TimeoutRecord.forBroadcastReceiver(
        intent, packageName, className);
```

冷启动属于预算的一部分。主线程可能还没进入 Service 或 Receiver 回调，已经被 Application 初始化、另一个组件或调度延迟消耗了大量时间。`goAsync()` 也不会获得额外预算，结束点改为 `PendingResult.finish()`。

### ContentProvider：publish failure 与 call ANR 分开看

Provider 有三组容易混淆的 timer：

| 路径 | Android 17 源码入口 | 结果 |
|---|---|---|
| 进程 attach 后未发布 Provider | `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG`，预算为 `10s × HW_TIMEOUT_MULTIPLIER` | AMS 以 initialization failure 清理进程，不走 `AnrHelper` |
| 调用方等待 Provider ready | `WAIT_FOR_CONTENT_PROVIDER_TIMEOUT_MSG` 与 ready timeout | 结束该次等待状态，不是 `setDetectNotResponding()` 的消息 |
| 已取得远端 Provider 后调用过慢 | `ContentProviderClient.NotRespondingRunnable` | 经 `appNotRespondingViaProvider()` 进入 ANR |

`ContentProviderClient.setDetectNotResponding()` 是 `@SystemApi`，要求 `REMOVE_TASKS` 权限。普通应用不能把它当作通用公开监控 API。调用方没有设置该检测时，不能用一个固定的“Provider call 10 秒”解释 ANR。

Publish timeout 常量定义在 `ContentResolver`。AMS 在包含 launching provider 的进程 attach 后安排 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG`；超时处理会清理进程。诊断中看到 `REASON_INITIALIZATION_FAILURE`、`start timeout` 或 Provider 启动失败时，先查 publish/进程启动路径。Subject 明确为 `ContentProvider not responding` 时，再沿配置该 detector 的系统客户端与 Provider Binder 线程查 call path。

## 第二步：用三类证据还原等待链

### EventLog 和 ANR 报告确定时间与对象

先记录以下字段，不急着解释：

- `am_anr` 的时间、PID、进程、reason 和组件；
- trace 头的抓取时间与进程 PID；
- CPU 统计、PSI 和 event log 各自覆盖的时间范围；
- InputChannel、Binder interface、锁地址或 Provider authority 等对象标识。

trace 可能在 detector 触发后才开始抓取。系统繁忙时，采样延迟会更长；线程也可能已经从阻塞点恢复。时间不重合的 trace 只能描述采样瞬间，不能直接解释早先的超时。

PID 还可能复用。跨越进程死亡与重启的日志必须同时比对进程名、UID、start/kill 事件和启动时间。

### Traces 找等待对象

下面这张表只给调查方向，不自动给责任方：

| 栈或状态 | 它能证明什么 | 还要补什么 |
|---|---|---|
| `BinderProxy.transactNative` / `IPCThreadState::waitForResponse` | 线程在同步等 Binder reply | transaction 对端、服务线程、嵌套调用与锁 |
| `waiting to lock` / `held by thread` | Java monitor 有明确等待与持有关系 | 持有者栈、其他锁边、有向环 |
| Java 栈顶 `nativePollOnce` | 当前位于 MessageQueue native 入口 | 完整 native 栈、trace 时间、Looper 历史 |
| Perfetto `R` / Runnable | 线程可运行却没有上 CPU | CPU 占用者、优先级、频率、cgroup |
| Perfetto `D` | 线程处于不可中断睡眠 | `blocked_function`、驱动/文件系统/块层事件 |

`nativePollOnce` 只有在完整 native 栈呈现 epoll/poll 等消息、且没有 native callback 尚未返回时，才支持“采样瞬间 Looper 空闲”。VSync、JNI 回调和 ART 等待也可能让 Java 栈停在同一入口。即便采样时空闲，late dump 仍可能错过先前的长任务。

Linux `D` 状态也不能直接翻译成磁盘慢。驱动、文件系统、块设备和其他内核等待都可能产生不可中断睡眠，要结合 `blocked_function` 和对应 tracepoint。

### Perfetto 连接时间线

至少把这些轨放在同一个 detector 窗口：

- 被记账进程的主线程、组件线程与 Binder 线程；
- Binder transaction 的 client/server 两端；
- system_server 或远端服务的执行线程与锁等待；
- CPU scheduling、frequency、idle 和进程 cgroup；
- memory reclaim、PSI、文件系统与块 I/O（按问题开启）；
- InputDispatcher、WindowManager 或进程启动相关事件。

线程状态的常见组合如下：

- 长 Running 且 thread CPU time 接近 wall time：线程在消耗 CPU；
- 长 Runnable：线程想运行，调度机会不足；
- Sleeping 且落在同步 Binder：等待 reply，继续找服务端；
- 多进程同时进入 `D`，并与同一驱动或 I/O 事件对齐：系统共享资源是强线索；
- 线程状态正常，Input connection 的 waitQueue 仍未完成：继续检查消费者身份、finish signal 和平台输入链。

CPU 满载、低频或 PSI 高只能说明系统条件。应用已经执行 4.8 秒的主线程任务，再遇到 0.3 秒调度延迟，也可能越过 5 秒预算。归因要同时保留应用耗时和系统放大因素。

## 四类高发的系统侧或跨进程根因

### 1. system_server 锁竞争与焦点状态

应用主线程同步调用 `IActivityTaskManager`、`IPackageManager`、`IAccessibilityManager` 等接口时，system_server 的锁和调度会直接影响返回时间。取证步骤是：

1. 从 Binder transaction 找 system_server 服务线程；
2. 检查该线程等待的 Java/native 锁；
3. 找锁持有者以及它正在执行或等待的对象；
4. 比对锁等待是否覆盖 ANR detector 窗口。

No-focused-window 需要另一组证据：focused application、focused window、目标 Activity 启动、窗口可见性和转场。应用首帧慢、窗口带 `FLAG_NOT_FOCUSABLE`、目标进程启动失败、WMS 转场清理异常都可能产生同一 reason。

Bugreport 中的 `Slow Looper`、`Slow operation` 和 Watchdog 记录可用作入口，厂商分支也可能使用自己的标签。关键词命中后仍要核对时间、线程和锁，旧日志不能解释新 ANR。

### 2. Binder 线程与嵌套调用

同步 Binder 调用会把远端延迟传给调用方。常见结构包括：

- 远端所有可用 Binder 线程都在处理长事务；
- 服务线程持锁做 I/O 或再同步调用其他进程；
- A 调 B、B 回调 A，并与 Java 锁组成等待环；
- 进程的 executor 已满，Binder 线程同步等待 executor 任务。

Android 17 `ProcessState.cpp` 中的 `DEFAULT_MAX_BINDER_THREADS = 15` 是向 driver 请求的默认最大值，不是进程内固定线程总数。判断“线程池耗尽”要看每条 Binder 线程的状态、当前 transaction 和是否仍有未处理请求。

把主线程调用移到 worker 可以消除 UI 线程暴露，功能仍然慢则说明远端问题还在。它是隔离手段，不能充当根因证明。

量产 user build 往往限制 binderfs/debugfs 节点。`/proc/binder/stats`、`/sys/kernel/debug/binder/*` 或厂商节点只能在权限与 build 条件满足时作为补充，不能当跨设备必备命令。

### 3. 调度、内存压力与 freezer

长 Runnable 配合 CPU 满载，说明目标线程没有获得足够运行时间。继续检查：

- 同 cgroup 中哪些线程占用 CPU；
- 目标线程优先级、uclamp、CPU affinity 与 thermal/frequency；
- memory PSI 的 `some/full`、major fault、direct reclaim 和 `kswapd`；
- 目标进程是否被放入 frozen cgroup。

PSI `some` 表示统计窗口内至少有任务因资源停顿，`full` 表示所有非 idle 任务同时停顿。它不提供具体受害线程，也不能代替线程级调度证据。

Cached Apps Freezer 在 Android 11+ 平台及厂商配置中可能出现。`am_freeze`、`am_unfreeze` 要与 PID、进程生命周期、输入 event ID 或 Binder transaction 对齐。仅看到一次 freeze 日志还不足以证明它覆盖了超时对象。

物理页大小也不能改变上述归因规则。16KB 页设备仍可能出现文件系统、驱动、reclaim 或锁等待；缺少 block I/O 不能自动把问题归到某类厂商驱动。

### 4. 存储停顿与 ContentProvider

远端 Provider 的 `query()`、`insert()` 等调用通常进入 Provider 进程 Binder 线程。调用线程可能因以下原因长时间等待：

- Provider 进程冷启动或发布状态迟迟未完成；
- Binder 线程在 SQLite open、锁、文件读取或 `fsync()` 上阻塞；
- Provider Binder 线程被其他事务占满；
- 多个进程同时遭遇文件系统、块设备或内存回收停顿。

调用方 trace 只会显示同步 Binder wait。要区分 Provider 自身数据路径和系统存储问题，需要同时查看 Provider 线程、其他受影响进程、文件系统/块层 slice、PSI 与调度。

## Android 8—17 的工具边界

| 平台 | 主线工具 | 能补充什么 | 权限边界 |
|---|---|---|---|
| Android 8—9 | bugreport、events、`traces.txt`、legacy atrace/Systrace | 主线程栈和基础调度 | 普通应用不能读 `/data/anr` |
| Android 10 | bugreport、`/data/anr/anr_*`（shell/root 条件）、Perfetto | Binder、sched、CPU 时间线 | Perfetto 数据源受 build 与权限限制 |
| Android 11—16 | 上述工具 + `ApplicationExitInfo`（API 30） | 应用读取自身历史退出原因与可用 trace | trace stream 可为空，范围有限 |
| Android 17 | bugreport、Perfetto、ApplicationExitInfo、平台诊断工具 | 与 `android-17.0.0_r1` 源码方法和事件对齐 | vendor/内核私有轨仍需相应权限 |

普通应用线上采集优先使用公开 API 和自有埋点。实验室或 OEM 场景再使用 root、userdebug、binder debug 节点和完整 `/data/anr`。

下面是一组不依赖 root 的基础命令，设备需已开启调试：

```bash
adb logcat -b events -d | grep 'am_anr'
adb bugreport ./bugreport.zip
adb shell perfetto --query
```

前两条保存 ANR 时间和 bugreport；`perfetto --query` 只检查设备支持的数据源，不会开始采集。发现故障后再按问题构造 trace config，避免用一份固定配置覆盖所有 ANR。

## 公开案例：InputTransport 的历史 finished-signal 缺陷

本案例有两层证据：

- 产品现象来自二手公开文章，报告某 Android 设备上的游戏 Input ANR；
- 代码缺陷与修复由 AOSP Gerrit 的合入记录和提交说明直接支持。

公开文章给出的历史日志如下：

```text
am_anr: [0,22222,com.tencent.tmgp.sgame,448932,
Input dispatching timed out
(Waiting to send non-key event because the touched window has not finished
processing certain input events that were delivered to it over 500.0ms ago.
Wait queue length: 27. Wait queue head age: 5504.1ms.)]

InputDispatcher: Application is not responding:
Window{927f72 u0 com.tencent.tmgp.sgame/com.tencent.tmgp.sgame.SGameActivity}.
It has been 5004.8ms since event, 5004.4ms since wait started.
Wait queue length: 27. Wait queue head age: 5504.1ms.
```

这段旧版 reason 证明 InputDispatcher 当时看到一批未完成输入事件。它不单独证明游戏主线程慢，也不单独证明平台有 bug。

文章还报告 Looper trace 没有对应长消息，并通过动态 input 日志把范围缩到 `InputTransport.cpp`。这部分属于案例报告，缺少原始 bugreport 与 trace，证据强度低于 Gerrit 记录。

AOSP 主证据提供了完整的代码演进：

1. 2015 年 change `172237` 合入，主题为 “Eliminate multiple benign overflow conditions”。它为适配 integer sanitizer 重写了多个 unsigned decrement loop。
2. 2017 年 change `396876` 合入，主题为 “Fix a anr bug caused by sendFinishedSignal logical error”。
3. 2017 年提交说明指出，2015 年的 loop 语义变化漏掉了把 head sequence 放入 `mSeqChains` 的关键迭代，导致一批 sequence 无法被正确 finished，最终触发 ANR。

产品案例与 AOSP 修复方向一致：应用处理输入的完成信号没有按预期回到派发端，wait queue 持续积压，InputDispatcher 便把窗口记为不响应。

这个缺陷早已修入平台，Android 17 源码不需要重新套用旧补丁。它提供的是诊断范式：

- reason 指向未完成事件；
- App 侧没有足以解释窗口的长任务证据；
- 动态 input 日志缩小到 sequence/finish 路径；
- 平台补丁的提交说明能解释等待队列为何不下降；
- 修补系统镜像后应通过相同输入压力测试验证。

## 归因检查表

- [ ] subject 只用于识别 detector 与被记账对象，没有直接当根因
- [ ] trace 时间覆盖超时窗口，PID 没有跨进程重启
- [ ] InputChannel `(server)` 没有被解释成 system_server
- [ ] no-focused-window 与 connection waitQueue 分开调查
- [ ] `nativePollOnce` 阅读了完整 native 栈和采样延迟
- [ ] Binder 等待找到了 transaction 对端和服务线程
- [ ] Runnable、Sleeping、`D` 按调度状态解释，没有只看颜色
- [ ] PSI、load、iowait 与具体线程/时间线对齐
- [ ] Provider publish failure 与 configured call ANR 分开
- [ ] 平台缺陷有源码、补丁或稳定 A/B 验证，不依赖单条可疑日志

## 参考资料

### Android 17 / API 37 源码

- [InputDispatcher.cpp：connection 与 no-focused-window ANR](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)
- [InputTransport.cpp：InputChannel 与 finished signal](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/input/InputTransport.cpp)
- [AnrHelper.java：系统 ANR 报告入口](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/AnrHelper.java)
- [ActivityManagerConstants.java：Service timeout](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerConstants.java)
- [BroadcastQueueImpl.java：Broadcast TimeoutRecord](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/BroadcastQueueImpl.java)
- [ContentResolver.java：Provider publish/ready timeout](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ContentResolver.java)
- [ContentProviderClient.java：configured call ANR detector](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ContentProviderClient.java)
- [ContentProviderHelper.java：Provider publish 与 ANR 处理](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ContentProviderHelper.java)
- [ProcessState.cpp：Binder 默认线程请求值](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/binder/ProcessState.cpp)

### 官方文档与案例

- [Android Developers：诊断和修复 ANR](https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs)
- [Android Developers：Android vitals ANR](https://developer.android.com/topic/performance/vitals/anr)
- [Perfetto：CPU scheduling](https://perfetto.dev/docs/data-sources/cpu-scheduling)
- [AOSP Gerrit 172237：2015 unsigned loop 重构](https://android-review.googlesource.com/c/platform/frameworks/native/+/172237)
- [AOSP Gerrit 396876：2017 sendFinishedSignal 修复](https://android-review.googlesource.com/c/platform/frameworks/native/+/396876)

本地案例素材：`../Cubox/有时候你APP发生的ANR不是你的错-分享 1个 Google 工程师没 bug 改出 bug 的一个案例-2025-04-21.md`。
