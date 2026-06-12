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
  date: android-16.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/AnrHelper.java
  title: ANR reporting helper
  date: android-16.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
  title: Service timeout constants
  date: android-16.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java
  title: Broadcast timeout record
  date: android-16.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java
  title: Content provider ANR entry
  date: android-16.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/ContentResolver.java
  title: ContentProvider timeout constants
  date: android-16.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/ContentProviderClient.java
  title: Provider not-responding detector
  date: android-16.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
  title: ContentProvider timeout messages
  date: android-16.0.0_r1
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed-lite
last_task2b_lite_at: "2026-06-04"
section: '9.7'
reviewed_by: openclaw-task6
reviewed_date: "2026-06-04"
task6_result: pass-light-edit
task9_result: auto-fixed
task2b_result: rework-fixed
last_verified: '2026-04-14'
last_verified_against: AOSP android-16.0.0_r1
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-06-13
last_task9_at: "2026-06-13T01:20:00+08:00"
review_notes: "2026-05-18 task9 idle audit: needs-rework。P1 2(ContentProvider timeout/source semantics;Android 15+ 16KB page-size version boundary),P2 1(InputDispatcher Android 8-10 path note);已写入 queue/suggestions,等待 Task2B 回炉。 | 2026-05-23 task6 idle audit: queue 中仍有 pending 回炉项,撤销 finalized 状态,保持 task2b_pending。"
auto_promoted: true
last_task9_autofix_at: 2026-06-13
last_task9_audit: 2026-06-13
last_task6_audit: "2026-06-04"
last_task9_review_log: logs/deep-review/2026-06-13-01-audit.md
task9_review_notes: "2026-06-13 Task9 idle audit auto-fix: 修正 ContentProvider WAIT_FOR_CONTENT_PROVIDER_TIMEOUT_MSG 与 setDetectNotResponding 路径混用。P0 1(auto-fixed) / P1 0 / P2 0；回到 Task6 复审。"
finalized_date: "2026-06-04"
finalized_by: openclaw-task9-auto-promote
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

## 为什么要单独看"非技术故障" ANR

ANR 报告把责任先落在"超时的进程"上,这一步只够告诉我们谁被系统判了无响应,不够回答根因在哪。很多线上 ANR 都是这个结构:App 主线程栈里看不到明显的长计算,业务代码也没有复现稳定规律,超时窗口里却冒出了 `system_server` 锁争用、Binder 对端停摆、CPU 饥饿、存储 stall,或者输入框架本身的历史 bug。

9.7 这节要解决的就是这类场景。目标是把证据按"超时类型 → 等待对象 → 对端进程 → 系统状态"这条顺序收拢起来。这样我们才能判断下一步该继续看业务线程,还是把材料转给 Framework、OEM、驱动或内核同学。相关的基础分析动作在 [[ANR 分析方法|§9.3 ANR 分析方法]],线程状态读取方法在 [[线程 CPU 状态分析|§13.6 线程 CPU 状态分析]],归因边界在 [[如何区分系统问题和 App 问题|§15.2 如何区分系统问题和 App 问题]]。

## 第 1 步:先判 ANR 类型,不要先猜业务代码

不同类型的 ANR,超时预算、触发线程和排查入口都不一样。拿到 `am_anr` 或 Play Vitals 的 subject 后,先把类型钉住。

| 类型 | 典型 subject / reason | 常见预算 | 排查入口 | 容易误判成"App 写错"的系统侧场景 |
|---|---|---:|---|---|
| Input dispatch | `Input dispatching timed out` | 5s | InputDispatcher + traces + Perfetto | `system_server` 卡死、`no focused window`、输入框架回归、Binder 对端阻塞 |
| Service | `executing service ...` | 前台 20s,后台 200s | `ActiveServices` + traces + Perfetto | 冷启动过慢、主线程被别的组件占住、系统负载高 |
| Broadcast | `Broadcast of Intent ...` | 前台 10s,后台 60s;Android 14+ CPU-starved 场景可拉长到 10-20s / 60-120s | `BroadcastQueueImpl` + EventLog + Perfetto | CPU 饥饿、进程冷启动、共享 worker 线程被别的任务占住 |
| ContentProvider | Provider publish / provider call timeout | publish 10s（`CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`）；call 超时由 `ContentProviderClient.setDetectNotResponding()` 配置 | `ContentProviderHelper` + traces + Perfetto | Provider 进程冷启动、Binder 线程池耗尽、系统存储路径卡顿 |

[已验证: 官方文档, https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs]

<!-- AIW-源码调研-2026-06-06 -->
**⚠️ 重要源码锚点修正**：ContentProvider 实际存在两条正交的超时路径，当前表格表述不够精确：

- **路径 1：Provider 进程 publish 超时（10s）**：`CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`（10s × HW_TIMEOUT_MULTIPLIER）在 `attachApplicationLocked` 中发送 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG=57`，超时后调用 `ContentProviderHelper.processContentProviderPublishTimedOutLocked` → `removeProcessLocked` + `REASON_INITIALIZATION_FAILURE`（杀进程，**不弹 ANR 对话框**，Perfetto 中只见 `am_proc_died` 无 `am_anr`）。
- **路径 2：Provider call hang 检测**：仅当具备系统权限的调用方配置 `ContentProviderClient.setDetectNotResponding()` 时开启，`ContentProviderClient.NotRespondingRunnable` 会经 `ContentResolver.appNotRespondingViaProvider()` 进入 `ContentProviderHelper.appNotRespondingViaProvider` → `AnrHelper.appNotResponding`（**真 ANR**；是否弹框取决于后续 ANR 策略）。

**常量定义位置修正**：`CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` 等常量定义在 `ContentResolver`（android-16 为 l.788-807），非 `ContentProviderHelper`。`CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG=57` 用于 provider publish 超时；`WAIT_FOR_CONTENT_PROVIDER_TIMEOUT_MSG=73` 只用于等待 provider publish 状态超时，不是 `setDetectNotResponding()` 的 call-hang ANR 消息。

**排查入口区分**：若遇到 "Unable to launch app ... for provider ... launching app became null" 或 `REASON_INITIALIZATION_FAILURE`，应查路径 1；若遇到 ANR 对话框且 subject 包含 "ContentProvider not responding"，应查路径 2 + `setDetectNotResponding` 的调用方。
<!-- AIW-源码调研-2026-06-06 -->

[已验证: 官方文档, https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs]

[已验证: 官方文档, https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs]

原稿把这些超时都写成 AMS 内部状态错乱、`Message.timeout`、电池异常之类的伪机制,这会把读者直接带偏。真实入口在 timeout record 和等待队列里,不在虚构的 framework API 里。

### Input ANR 的真实入口在 inputflinger

Input ANR 的超时检测发生在 native input pipeline。AOSP android-16 的 `InputDispatcher.cpp` 里,默认 budget 来自 `DEFAULT_INPUT_DISPATCHING_TIMEOUT`,调度循环里会周期性执行 `processAnrsLocked()`:

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp  (Android 11+)
// Android 8.1/10.0 路径为 services/inputflinger/InputDispatcher.cpp
const std::chrono::duration DEFAULT_INPUT_DISPATCHING_TIMEOUT = std::chrono::milliseconds(
        android::os::IInputConstants::UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS *
        HwTimeoutMultiplier());
...
const nsecs_t nextAnrCheck = processAnrsLocked();
```

这里的判断对象是输入等待队列，不是某个"AMS 状态不一致"回调。输入事件发出去之后，目标窗口迟迟不给 ack，InputDispatcher 才会把超时上报到 system_server 的 ANR 处理路径。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### Service、Broadcast、Provider 也都有各自的 timeout record

Service 预算不是拍脑袋来的,AOSP 常量写在 `ActivityManagerConstants.java`:

```java
// frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java
private static final long DEFAULT_SERVICE_TIMEOUT = 20 * 1000 * Build.HW_TIMEOUT_MULTIPLIER;
private static final long DEFAULT_SERVICE_BACKGROUND_TIMEOUT = DEFAULT_SERVICE_TIMEOUT * 10;
```

Broadcast 的 ANR 会在 `BroadcastQueueImpl` 里生成 `TimeoutRecord` 再回到 `appNotResponding()`:

```java
// frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java
TimeoutRecord tr = TimeoutRecord.forBroadcastReceiver(r.intent, packageName, className)
        .setExpiredTimer(timer);
mService.appNotResponding(queue.app, tr);
```

ContentProvider 这条线也有独立入口:

```java
// frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java
void appNotRespondingViaProvider(IBinder connection) {
    ...
}
```

这些代码足够说明一件事,Service、Broadcast、Provider 的超时都有清晰的系统入口,排查时要顺着真实入口走,不要把全部 ANR 都折叠成"主线程某条 Message 超时"。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java]

## 第 2 步:把证据拆成三层

### 第 2.1 层:EventLog 负责定时点

排查 ANR 时,`am_anr` 往往比后续 traces 更接近"超时被系统认定"的时间点。我们先拿到这三个字段:

- ANR 类型和 reason
- 进程名、pid、组件名
- 发生时间

如果 traces 的输出时间比 `am_anr` 晚很多,说明当时系统已经很忙,dump 下来的栈不一定还是第一案发现场。这种场景里,Perfetto 和 EventLog 的对时比单看一份 traces 更有价值。这个判断在 [[ANR 分析方法|§9.3 ANR 分析方法]] 已经给出详细流程,这里只保留与"非技术故障"直接相关的一步:拿 `am_anr` 锁住时间,再看对端和系统状态。

### 第 2.2 层:traces 负责定等待对象

traces 最有用的地方,是把线程正在等什么暴露出来。

| traces / 栈形态 | 优先怀疑的对象 | 后续动作 |
|---|---|---|
| `BinderProxy.transactNative` / `IPCThreadState::waitForResponse` | 远端 Binder 服务、`system_server`、vendor daemon | 去看对端进程的 Binder 线程、锁和 CPU 状态 |
| `waiting to lock <...>` | Java 锁竞争或死锁 | 找持锁线程,再看持锁线程在等谁 |
| `nativePollOnce` | dump 瞬间线程空闲,不能直接免责 | 回到 `am_anr` 时间点,看历史消息和 Perfetto 轨迹 |
| `D` 状态、文件系统或块层调用 | 存储 stall、page fault、系统 reclaim | 看全局 I/O、`kswapd`、多进程是否同时卡住 |
| 主线程没有长栈,Perfetto 里长时间 Runnable | CPU 饥饿、优先级不利、系统负载高 | 看 CPU 调度、频率、前后台进程竞争 |

这一层的任务是找"等待对象",不是急着定责。App 主线程卡在同步 Binder 上,根因可能在远端;App 主线程 dump 到 `nativePollOnce`,也不代表它前一秒没堵过队。

### 第 2.3 层:Perfetto 负责定根因

Perfetto 把单点 traces 变成时间线。做 9.7 这类问题时,建议至少把下面四条轨放到同一个时间窗口:

- App 进程主线程的 slice 和 `thread_state`
- `system_server` 里相关 Binder 线程或主线程
- CPU Scheduling / CPU Frequency
- Binder transaction 或能代表阻塞对象的 slice

[图:Perfetto 中 App 主线程、system_server 线程、CPU Scheduling 与 Binder 事务放到同一时间窗口]

看到的模式通常只有几种:

- 主线程 Running 很长,Wall≈CPU,问题更像 App 自己在做重活。
- 主线程 Runnable 很长,CPU 一直满,问题更像调度竞争。
- 主线程 Sleep 在 Binder wait 上,远端线程被锁住或 CPU 抢不到,问题在对端。
- 多个进程都出现 D 状态,块层或文件系统轨迹一起变长,问题更像系统存储路径。

线程状态的读法和颜色含义,统一以 [[线程 CPU 状态分析|§13.6 线程 CPU 状态分析]] 为准。[已验证: 官方文档, https://perfetto.dev/docs/data-sources/cpu-scheduling]

## 高发的四类"App 躺枪"场景

### 1. `system_server` 锁争用或服务端卡死

这类场景里,App 只是同步等系统服务返回。ANR 栈常见形态是 `BinderProxy.transactNative`、`IActivityTaskManager`、`IPackageManager`、`IAccessibilityManager` 之类的 Binder 调用。对端如果是 `system_server`,下一步就去看它的主线程或 Binder 线程有没有锁争用、长 Runnable、长 Running。

输入侧的 `(server) is not responding` 和 `no focused window`,都很容易落到这一类。它们看上去是"某个前台 App 的 Input ANR",证据链却常常指向 `system_server` 的窗口管理、输入回调、焦点切换、手势监控。遇到这种 subject,别只盯着 App trace。

快速定性"no focused window"的操作路径:

1. 从 `am_anr` 的 reason 字段拿到 ANR 时间点
2. 在同时间段的 EventLog 里搜索 `wm_focus` 和 `am_focused_activity`,看焦点窗口在 ANR 前后是否发生了切换、丢失或延迟授予
3. 在 Perfetto 的 `wm` 轨道或 `InputDispatcher` slice 里确认 InputDispatcher 的 `focusedWindow` 是否为空
4. 如果焦点丢失和 `system_server` 主线程的锁争用 / 长操作时间重合,归因就指向系统侧

Bugreport 里搜系统侧卡顿,AOSP 基线关键词是 `Slow Looper` 和 `Slow operation`(system_server 内置的 Looper 慢消息检测)。厂商定制的系统监控组件会使用各自的日志标签--在 Bugreport 的 `system_server` 线程栈附近搜索 `Slow`、`Block`、`Monitor`、`Watchdog`、`Looper` 等关键词族,可以快速定位系统侧慢操作或锁争用。如果只看 App 自己的 traces,对端证据会被完全漏掉。

### 2. Binder 线程池耗尽或远端进程卡死

主线程同步发起 Binder 调用时,只要远端线程池空不出来,或者远端线程拿到请求后又被锁、I/O、CPU 饥饿卡住,调用方就会一起等。ContentProvider、媒体服务、定位、厂商服务都可能落进这条链。

识别方式：

- App 主线程卡在 Binder wait。
- 远端进程没有空闲 Binder 线程,或者 Binder 线程都在做长事务。
- 把调用挪到子线程后,ANR 消失,功能仍然慢。

旧资料里常出现 `cat /proc/binder/stats` 这类命令。现在不能把它当通用入口。很多商用设备没有对 user build 开放 binder debug 节点,路径也可能是 binderfs 或 debugfs,需要 root / eng / userdebug 前提。它能作为辅证,不能当默认第一手资料。

### 3. CPU 饥饿、reclaim、freezer

如果 Perfetto 里主线程长时间 Runnable,CPU 区域又一直满载,问题就从"线程做了什么"转成"线程为什么排不上"。这种场景下,系统负载、后台重活、频率受限、reclaim 都会放大超时风险。Broadcast、Service、冷启动型 ContentProvider ANR 特别容易被这类系统状态拖垮。

`kswapd` 活跃、major fault 飙升、主线程或对端线程出现 D 状态,都说明系统在为内存或存储付账。Android 12+ 还多了一类 freezer 证据:事件本来该送达,目标进程却被冻结了,EventLog 里能看到 `am_freeze` / `unfreeze`。这类现象在手势监控、截图、后台辅助进程里并不罕见。

Android 15 起支持 16KB 页大小配置（非所有设备默认启用，取决于内核和设备配置），启用后页表条目减少，`mmap`/`munmap` 路径上的 VMA 锁竞争频率随之降低。在已启用 16KB 页大小的 API 35+ 设备上，如果主线程进入 D 状态却没有密集 I/O 的证据（块层无 pending request、`iowait` 不高），排查方向应该优先转向硬件驱动层锁或厂商定制内核模块，而非传统的内核 VMA 锁。

高负载不等于 App 自动免责。更稳妥的写法是:高负载会放大 App 侧耗时,也可能单独构成系统侧根因。要不要定成"系统问题",回到 Wall/CPU、等待对象和对端状态一起看。这个归因边界在 [[如何区分系统问题和 App 问题|§15.2 如何区分系统问题和 App 问题]] 有完整展开。

### 4. 存储 stall 与 Provider / 冷启动路径

ContentProvider 这条线最容易被写错。Provider 的 CRUD 工作通常跑在 Provider 进程的 Binder 线程池,不是天然跑在主线程;会直接把调用方拖进 ANR 的,往往是下面两种情况:

- Provider 进程冷启动或 publish 太慢,调用方一直等远端 ready。
- Provider 端 Binder 线程池被慢查询、SQLite open、文件 I/O 或系统存储 stall 堵住了。

这一类如果只盯调用方的 UI 线程,很容易得出"主线程没干重活却超时"的假象。把调用方和 Provider 进程一起放进 Perfetto,看有没有多线程同步掉进 D 状态、有没有 SQLite open / 文件系统调用拉长,才知道根因是在 App 自己的数据路径,还是整个系统存储路径都在抖。

## Android 8-17 的工具边界

原稿把 `systrace.py`、`atrace`、`/proc/binder/stats`、`watch -n 1` 混成一套,读者照抄很容易跑不通。排查边界如下：

| Android 版本 | 主抓取手段 | 适合做什么 | 不要默认假设 |
|---|---|---|---|
| 8-9 | bugreport、`/data/anr/traces.txt`、必要时 legacy `atrace` / Systrace | 先拿 ANR 时间点、主线程栈、基础调度信息 | Perfetto UI/trace 能力与新版本完全等价 |
| 10-11 | bugreport、`/data/anr/`、Perfetto | traces + 调度 + Binder + CPU | 旧的 `systrace.py` 仍是主入口 |
| 12-17 | bugreport、`/data/anr/anr_*`、Perfetto | 以 Perfetto 为主线,同时观察 `thread_state`、Binder、CPU、系统服务 | `/proc/binder/stats`、debugfs 节点在所有量产机都可读 |

一套稳妥的最小抓取组合是:

```bash
adb logcat -b events | grep am_anr
adb bugreport
adb shell ls /data/anr
```

设备允许抓 trace 时,再补一份 Perfetto。对系统服务型 ANR,bugreport 和 Perfetto 的组合价值通常高过单独看一份主线程 trace。

## 公开案例:InputTransport 历史 bug 让王者荣耀背锅

原始公开材料里有一条很典型的"App 躺枪"案例。手机上概率性出现王者荣耀 Input ANR,EventLog 是这样写的:

```text
am_anr : [0,22222,com.tencent.tmgp.sgame,448932,Input dispatching timed out
(Waiting to send non-key event because the touched window has not finished
processing certain input events that were delivered to it over 500.0ms ago.
Wait queue length: 27. Wait queue head age: 5504.1ms.)]
```

同一时刻的 InputDispatcher 日志也给出了相同的等待队列信息:

```text
InputDispatcher: Application is not responding:
Window{927f72 u0 com.tencent.tmgp.sgame/com.tencent.tmgp.sgame.SGameActivity}.
It has been 5004.8ms since event, 5004.4ms since wait started.
Reason: Waiting to send non-key event because the touched window has not finished
processing certain input events that were delivered to it over 500.0ms ago.
Wait queue length: 27. Wait queue head age: 5504.1ms.
```

[来源: Cubox/有时候你APP发生的ANR不是你的错-分享 1个 Google 工程师没 bug 改出 bug 的一个案例-2025-04-21.md]

这条案例最有价值的地方,是它没有停在"主线程 ANR"四个字上。公开材料继续给了两条关键证据:

1. **Looper trace 没看到长消息阻塞。** 这说明 App 主线程没有明显的单条消息跑满 5 秒。
2. **动态 input log 把问题收敛到 `InputTransport.cpp`。** 文中定位到 2015 年 Google 一次为 `fsanitize=integer` 重构输入序列链表的提交,`seqChain` 在某些 `chainIndex` 路径下漏记,后续由手机厂商在 2017 年提交补丁修复。

原始材料给出的 Gerrit 链接如下:

- `[引用: https://android-review.googlesource.com/c/platform/frameworks/native/+/172237/4/libs/input/InputTransport.cpp]`
- `[引用: https://android-review.googlesource.com/c/platform/frameworks/native/+/396876]`

这份材料的结论：ANR 的表象落在游戏 App,根因却在输入传输层的历史 bug。读者该记住的是下面这套证据顺序:

- Input ANR 的 reason 明确写着 wait queue 积压。
- App looper 没有对应的长消息。
- 动态 input log 把问题收敛到 InputTransport。
- 框架补丁能稳定解释和修复问题。

[图:原始公开材料中的动态 input log 截图,定位到 InputTransport.cpp 的 `seqChain` 漏记]

这类案例写进技术书时,不该再发明 `ActivityState.CREATED`、`generateANRReport()` 这类不存在的 framework API。保留"现象 + 证据 + 推理链"就够了,而且更能复核。

## 常见误区

### `nativePollOnce` 就能证明主线程没问题

不能。它只说明 dump 的那一刻主线程在等消息。超时真正发生时,主线程可能刚好把重活做完,也可能一直在等远端 Binder 返回。

### Input ANR 都是前台 App 自己慢

不能这么写。`(server) is not responding`、`Application does not have a focused window`、输入框架历史回归,都能把前台 App 放到 ANR subject 上。

### 一条 Binder 命令能解决所有定位

也不成立。量产机上的 binder debug 节点经常受 SELinux、binderfs、build type 限制。EventLog、traces、Perfetto 才是跨设备更稳定的主线。

## 参考资料

- `https://developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs`
- `https://developer.android.com/topic/performance/vitals/anr`
- `https://perfetto.dev/docs/data-sources/cpu-scheduling`
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` (Android 11+)；Android 8.1/10.0 为 `services/inputflinger/InputDispatcher.cpp`
- `frameworks/base/services/core/java/com/android/server/am/AnrHelper.java`
- `frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java`
- `frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java`
- `frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java`
- `Cubox/有时候你APP发生的ANR不是你的错-分享 1个 Google 工程师没 bug 改出 bug 的一个案例-2025-04-21.md`
