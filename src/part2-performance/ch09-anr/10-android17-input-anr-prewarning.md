---
title: "Android 17 Input ANR 与 pre-ANR 实现"
chapter: "9.10"
section: "9.10"
status: ready-for-review
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-03"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/input/InputManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/native/libs/input/android/os/IInputConstants.aidl"
  - type: research
    path: "DeepResearch/2026-07-02-android17-input-anr-mechanism.md"
  - type: research
    path: "DeepResearch/2026-06-15-anr-detection-inputdispatcher-ams-anrhelper-source.md"
tags: [ANR, InputDispatcher, pre-ANR, Android17, TimeoutRecord, AnrTimer]
related_chapters: ["9.1", "9.2", "9.9", "3.1"]
---

# 9.10 Android 17 Input ANR 与 pre-ANR 实现

本章以 Android 17 / API 37 / `android-17.0.0_r1` 为源码核对版本。先明确 InputDispatcher 的 pre-ANR（ANR 到期前预警）覆盖范围：

- Android 17 的 InputDispatcher pre-ANR 目前只覆盖 **no focused window（没有焦点窗口）**；
- 已有窗口迟迟不确认输入事件的 **window unresponsive（窗口无响应）** 路径没有对应的 InputDispatcher pre-ANR producer（产生预警的系统路径）；
- pre-ANR 受 feature flag（功能开关）控制，是到期前按 best-effort（尽力而为、不保证到达）方式投递的 warning；
- 正式 ANR 仍由原 deadline（完成期限）、WMS（WindowManagerService）责任判断，以及 AMS（ActivityManagerService）/AnrHelper 处理流程决定。

所以，“输入 ANR 都会在 50% 处收到预警”“收到预警的进程一定成为 ANR 责任方”都不成立。

## 1. 两类输入 ANR 要分开

InputDispatcher 处理的两类超时都表现为“输入没有按期完成”，但计时对象不同。

| 路径 | 开始条件 | 计时状态 | 到期对象 | Android 17 pre-ANR |
|---|---|---|---|---|
| no focused window | 有 focused application（当前应获得焦点的应用），没有 focused window，并出现需要焦点目标的事件 | `mNoFocusedWindowAnrState` | `InputApplicationHandle` | 有，flag 开启时生效 |
| window unresponsive | 事件已发给窗口或 input monitor（输入事件观察者），连接 wait queue（已派发、待完成的事件队列）长时间没有完成 | `mAnrTracker` + `Connection.waitQueue` | window/input monitor connection | 当前实现没有 |

### 1.1 no focused window

`findFocusedWindowTargetLocked()` 只有在事件需要焦点目标时才启动这次倒计时。源码注释以 KeyEvent 为例。若 focused application 和 focused window 都为空，事件直接失败；若窗口已存在，则走正常派发。

状态首次建立时保存：

- 输入事件的 `eventTime`（发生时间）与 `eventId`（事件标识）；
- 当前 focused application；
- `timeoutEndTime`；
- 本次实际 `timeoutDuration`（超时时长）；
- `notifiedPreAnr = false`。

实际 timeout 来自 `focusedApplicationHandle->getDispatchingTimeout(DEFAULT_INPUT_DISPATCHING_TIMEOUT)`，因此不能假设每次都是 5 秒。应用焦点改变、窗口出现或其他重置条件发生时，InputDispatcher 会清除这次等待。

### 1.2 window unresponsive

窗口已有 connection（输入连接）后，InputDispatcher 把等待确认的 `DispatchEntry`（一次事件派发记录）放进 wait queue，并用 `mAnrTracker` 快速找到最近的 deadline。到期后，它取 connection wait queue 中最老的事件来构造诊断 reason（原因描述）。

源码特意说明：最老事件未必就是最早达到 deadline 的事件，因为窗口 timeout 可能变化；但应用通常按顺序处理输入，用最老事件解释现场更有诊断价值。因此，reason 中的 event 与精确触发 deadline 的 entry 可能不是同一条记录。

## 2. `dispatchOnce()` 里的两次检查

Android 17 在每次 dispatcher loop 末尾计算下一次唤醒时刻。相关源码结构如下：

```cpp
nextWakeupTime = std::min({
        nextWakeupTime,
        processPreAnrsLocked(),
        processAnrsLocked()
});
```

这里的一次迭代不是 UI frame（界面帧）。两个函数会在一次 `dispatchOnce()` 循环中、持有 dispatcher lock（InputDispatcher 内部锁）时执行，返回值用于决定 `pollOnce()` 下一次何时醒来。

`processPreAnrsLocked()` 当前只有一个具体分支：

```cpp
nsecs_t InputDispatcher::processPreAnrsLocked() {
    if (!mAnrWarningCallbackInputDispatcherEnabled) {
        return LLONG_MAX;
    }
    return std::min(
            nsecs_t{LLONG_MAX},
            processNoFocusedWindowPreAnrLocked());
}
```

这段实现为未来增加其他 pre-ANR 类型保留了入口，但 `android-17.0.0_r1` 没有 window-unresponsive pre-ANR helper（辅助函数）。`mAnrWarningCallbackInputDispatcherEnabled` 的初始值来自 `enable_anr_warning_callback_input_dispatcher` flag。

## 3. pre-ANR 时间公式

no-focused-window 的 warning 时刻由下面的公式决定：

```text
pre_window = max(actual_timeout / 2, 2000 ms × HwTimeoutMultiplier)
warning_at = timeout_end - pre_window
consumed   = actual_timeout - (timeout_end - now)
```

`IInputConstants.aidl` 把未乘硬件系数的最小 pre-ANR window 定为 **2000 ms**。默认 dispatch timeout 是 **5000 ms**。两项 fallback（默认备用）常量都会乘 `HwTimeoutMultiplier()`，该值来自产品配置属性 `ro.hw_timeout_multiplier`。

`max` 选出更长的“deadline 前剩余窗口”，因此 warning 会更早发出。默认情况下，它保证留给诊断的时间不少于 2 秒，并不会推迟 warning。

以 `HwTimeoutMultiplier = 1` 为例：

| 实际 timeout | `timeout / 2` | 最小 pre window | warning 已消耗时间 |
|---:|---:|---:|---:|
| 5000 ms | 2500 ms | 2000 ms | 2500 ms |
| 3000 ms | 1500 ms | 2000 ms | 1000 ms |
| 1000 ms | 500 ms | 2000 ms | 首次检查时立即满足 |

默认 5 秒路径恰好在一半附近发出 warning。自定义 timeout 较短时，warning 会早于 50% 进度；若计算出的 `warning_at` 已经过去，InputDispatcher 会立即排队通知。

`notifiedPreAnr` 保证同一 `mNoFocusedWindowAnrState` 只排队一次。状态被重置后，新事件可以开始新的预警周期。

## 4. pre-ANR 会直接到达公开 warning API

旧资料常把 Native pre-ANR 和 `ActivityManager.registerAnrWarningListener()` 写成两套无关机制。Android 17 源码给出了直接调用关系，其中 JNI（Java Native Interface）负责连接 native 与 Java 层。

```mermaid
flowchart TD
    Dispatcher["InputDispatcher<br/>processNoFocusedWindowPreAnrLocked"]
    Policy["InputDispatcherPolicyInterface<br/>notifyPreNoFocusedWindowAnr"]
    JNI["NativeInputManager JNI"]
    IMS["InputManagerService<br/>notifyPreNoFocusedWindowAnr"]
    IMC["InputManagerCallback"]
    WMS["WMS AnrController<br/>notifyPreAppUnresponsive"]
    Trace["可选 LongMethodTracer<br/>3 秒窗口"]
    AMS["ActivityManagerInternal<br/>inputDispatchingTimedOutWarning"]
    Controller["AMS notifyAnrWarning<br/>AnrWarningController"]
    App["同 UID 已注册进程<br/>AnrWarningResult"]

    Dispatcher --> Policy --> JNI --> IMS --> IMC --> WMS
    WMS --> Trace
    WMS --> AMS --> Controller --> App
```

`AnrController.notifyPreAppUnresponsive()` 先解析 `InputApplicationHandle` 对应的 Activity。Activity 不存在、已经 stopped（停止）或没有进程时，部分动作会被跳过。存在进程时，AMS warning 使用以下数据：

- UID：候选 Activity 所属应用的身份编号；
- `anrId`：Native 输入事件 id；
- type：`ANR_TYPE_INPUT_DISPATCH_NO_FOCUSED_WINDOW`；
- consumed time：InputDispatcher 计算的已消耗时间；
- timeout：本次实际 timeout；
- description：Android 17 该调用点传空字符串。

`AnrWarningController` 再向该 UID 下已经注册 listener（监听器）的进程投递。warning payload（载荷）没有 PID 或 Activity token（系统识别 Activity 的句柄）；多进程应用应按 `(type, id, boot/session)` 去重，其中 boot/session 表示本次开机或应用会话。

公开 API、11 个类型和载荷字段见 [9.9 Android 17 ANR 预警回调](09-android17-anr-warning-callback.md)。

## 5. warning 时可选的 Long Method Trace

WMS 的 `enableInputDispatcherLongMethodTracing` flag 开启时，pre-ANR 还会尝试调用 `LongMethodTracer.trigger(pid, 3000)`。`LongMethodTracer` 自身又受 `com.android.server.utils` 的 `longMethodTrace` flag 控制，因此只有两个开关都启用时，系统才会尝试这项诊断，结果仍不保证成功。

目标 PID 的选择有两种：

1. 当前 focus holder（焦点持有者）已经持有焦点至少一个 dispatch timeout 时，WMS 可以把它视为阻碍焦点切换的候选目标；
2. 没有这样的 focus target（焦点目标）时，使用缺少 focused window 的 Activity 进程。

`LongMethodTracer` 通过 native signal-based mechanism（基于信号的 native 机制）请求固定时长的方法追踪。类注释写明，若目标进程在 tracing window（追踪窗口）内或之后发生 ANR，采集信息会进入 ANR report。触发返回 `false`、进程退出或 flag 关闭，都可能导致产物缺失。

warning callback 与 Long Method Trace 是相互独立的动作。应用收到 callback 不表示追踪已经成功，追踪成功也不保证应用注册了 listener。

## 6. 到期路径仍有两条

### 6.1 no focused window 到期

`processAnrsLocked()` 发现当前时间达到 `mNoFocusedWindowAnrState.timeoutEndTime` 后，会重新检查：

- 当前 focused application 是否仍为等待中的 application；
- focused window 是否仍为空。

条件仍成立才调用 `onAnrLocked(application)`。随后 Native policy 回调携带 `eventId`、原事件 `eventTime` 和配置 timeout 进入 Java。

### 6.2 window unresponsive 到期

`mAnrTracker.firstTimeout()` 到期后，InputDispatcher 会执行以下步骤：

1. 取得对应 connection；
2. 标记 `connection->responsive = false`；
3. 从 tracker 移除 token，避免继续为这条连接安排唤醒；
4. 在 `onAnrLocked(connection)` 中确认 wait queue 仍不为空；
5. 保存 `mLastAnrState`；
6. 通知 policy，并取消该 connection 的 ANR 事件。

这一路没有经过 `processNoFocusedWindowPreAnrLocked()`，所以不能期待 API 37 input warning。

## 7. 正式回调如何进入 AMS

两条到期路径都经过 NativeInputManager JNI 回到 `InputManagerService`：

| Java 入口 | `TimeoutRecord` kind | 附带对象 |
|---|---|---|
| `notifyNoFocusedWindowAnr()` | `INPUT_DISPATCH_NO_FOCUSED_WINDOW` | application handle |
| `notifyWindowUnresponsive()` | `INPUT_DISPATCH_WINDOW_UNRESPONSIVE` | input token、可选 PID、reason |

`InputManagerService.timeoutMessage()` 还会用 `SurfaceControl.getStalledTransactionInfo(pid)` 检查关联 surface（图形缓冲区提交目标）是否因 unsignaled fence（尚未发出完成信号的图形同步栅栏）卡住。命中时，reason 会补充 layer（图层）、buffer id 和 frame number，提示可能存在 GPU hang（GPU 长时间没有完成工作）。这些信息仍只是诊断上下文，WMS/AMS 还要继续解析责任进程。

## 8. `TimeoutRecord` 与 `ExpiredTimer` 的准确关系

Android 17 在 `includeAnrInfo` flag 开启时，对两条正式输入 ANR路径执行：

```java
AnrTimer.ExpiredTimer expiredTimer =
        new AnrTimer.ExpiredTimer(
                eventId,
                eventTimeNs / 1_000_000,
                timeoutDurationMs);
timeoutRecord.setExpiredTimer(expiredTimer);
```

这里复用了 `AnrTimer.ExpiredTimer` 作为只承载三个字段的数据对象：

- `mTimerId`：输入 event id；
- `mStartMs`：输入 event time 转为毫秒；
- `mDurationMs`：本次传入的 timeout duration。

输入 deadline 仍由 InputDispatcher 的 `mNoFocusedWindowAnrState` 或 `mAnrTracker` 驱动，Java `AnrTimer` 没有为它启动 native timer。

两条路径的 duration 口径也不同：

- no focused window 传入配置的 timeout threshold（超时阈值）；
- window unresponsive 传入 wait queue 最老 entry（队列项）截至 `onAnrLocked()` 的实际等待时长。

后续 `ProcessErrorStateRecord.createAnrInfo()` 读取这个对象，生成 API 37 `ApplicationExitInfo.AnrInfo`。`includeAnrInfo` 关闭时不影响 ANR 检测，只会失去这份结构化关联数据。

## 9. WMS 归因可能改变责任进程

no-focused-window warning 会先投给候选 Activity UID。到期后，`AnrController.notifyAppUnresponsive()` 还会查看当前 input focus（输入焦点）。

若当前 focus target 的 focus request age（等待焦点请求的时间）已经达到其 dispatch timeout，WMS 会尝试把正式 window-unresponsive 责任交给该 focus target；否则仍按原 Activity 处理。pre-ANR 的可选 long method trace 也用相同规则挑选候选 PID。

这带来一个平台关联边界：

- warning 的 `(type, id)` 属于原 Activity UID；
- 正式 ANR 可能归到另一个 PID/UID；
- 同 UID 内可用 `ApplicationExitInfo.AnrInfo` 关联；
- 跨 UID 改归因时，普通 App 端无法读取另一方退出历史。

系统/OEM 平台应保留 event id、原 application token、focus target 和责任判断过程。普通应用的 APM（应用性能监控）只能把未匹配 warning 标成 recovered（已恢复）、unmatched（未匹配）或 possible-reattribution（可能改判责任方），不能强行关联到本进程。

## 10. AMS 与 AnrHelper

WMS 解析出 Activity 或 PID 后，调用 `ActivityManagerInternal.inputDispatchingTimedOut()`。AMS：

- 要求调用方具有 `FILTER_EVENTS`；
- 按 PID 查 `ProcessRecord`；
- 调试中的进程不进入标准 ANR；
- active instrumentation（正在控制该应用的测试或调试框架）会收到取消结果；
- 其他有效进程交给 `mAnrHelper.appNotResponding()`。

普通 persistent process（常驻系统进程）没有“天然跳过输入 ANR”的通用分支。是否显示 UI、是否静默终止进程、栈转储范围和 DropBox（系统诊断报告存储）处理，会在更后面的 `ProcessErrorStateRecord` 中决定。

这部分完整时序见 [9.1 ANR 设计思想](01-anr-design.md)；线程转储与报告入口见 [9.3 ANR 分析](03-anr-analysis.md)。

## 11. 一条正确的时序

默认 timeout 5 秒、硬件乘数 1、feature flag 全部开启时，no-focused-window 的理想时序是：

```text
T0       发现 focused application 存在，但 focused window 为空
T0+2.5s  InputDispatcher 排队 pre-ANR
          ├─ WMS 可选触发 3s Long Method Trace
          └─ AMS 向已注册 UID 投递 AnrWarningResult
T0+5.0s  InputDispatcher 重新检查 application 与 window
          └─ 条件仍成立才进入正式 ANR 归因
T0+5.0s+ WMS / AMS / AnrHelper 处理栈、报告、UI 或 kill
```

实际时间可能偏离上面的理想值，误差主要来自四处：

- dispatcher 或 `system_server` 调度延迟；
- JNI、WMS global lock 和 Binder 回调耗时；
- App listener executor 排队；
- 自定义 timeout 值和硬件乘数。

若系统在 `warning_at` 之后才得到运行机会，pre-warning 与正式 ANR 可能非常接近。公开回调没有“至少剩余 N 毫秒”的 SLA（服务级别保证）。

## 12. `2s / 5s / 10s` 不是三级 ANR

Android 17 源码附近还有两个常量：

- `SLOW_EVENT_PROCESSING_WARNING_TIMEOUT = 2s`；
- `STALE_EVENT_TIMEOUT = 10s × HwTimeoutMultiplier()`。

它们不能和 5 秒 dispatch timeout 排成“2 秒预警、5 秒 ANR、10 秒丢弃”的统一状态机，因为三者监视的对象不同：

- slow-event warning 用于记录事件处理过慢的日志；
- pre-ANR 的 2 秒指 deadline 前最小剩余 window；
- stale-event timeout 判断进入 dispatcher 的事件是否已经陈旧；
- 正式 dispatch timeout 可来自 window/application 配置，不固定为 5 秒。

名称相近不代表同一计时对象。

## 13. Trace 与日志如何对齐

Android 17 在这些位置留下系统 trace 标记：

- Native policy JNI 回调使用 `ATRACE_CALL()`；
- WMS pre 路径使用 `notifyPreAppUnresponsive()` trace section（自定义 trace 区间）；
- `LongMethodTracer.trigger()` 使用 ActivityManager trace tag；
- AMS 正式路径使用 `inputDispatchingTimedOut()`；
- 有目标 callback 时，`AnrWarningController` 还会发出带 id 的 Perfetto instant（瞬时事件）。

分析时按以下顺序对齐：

1. 找 warning 的 `(anrType, anrId)` 与 callback uptime；
2. 找 WMS `notifyPreAppUnresponsive()` 和可选的 long-method trace（长方法追踪）；
3. 检查 T0 到 deadline 期间 focused application/window 的变化；
4. 找 `inputDispatchingTimedOut()` 与 ANR report 的 ErrorId（错误标识）；
5. 用 main thread（主线程）、Binder、fence、CPU 和 I/O 时间轴判断为何窗口没有出现。

Perfetto 不会自动生成固定的 `/data/anr` 产物。需要预先配置持续 trace、triggered trace（按事件触发的 trace）或 Profiling trigger，详见 [9.7 ANR 与 Kernel Trace 联合诊断](07-anr-kernel-trace-joint-diagnosis.md)。

## 14. 工程接入建议

### 普通 App

- 用 API 37 SDK 编译，并用 `SDK_INT >= 37` 保护 warning listener；
- listener 使用独立 executor，只复制小型内存快照；
- 用 `(type, id, boot/session)` 去重多进程回调；
- 记录 callback 到达时间，不能把它当作 Native warning 精确时刻；
- 下次启动读取 `ApplicationExitInfo.AnrInfo`，允许 warning 无 exit、exit 无 warning；
- 保留 Activity、页面和启动阶段的 breadcrumbs（最近事件轨迹），帮助解释 no-focused-window。

### 系统与 OEM

- 分别验证 input warning、long method tracing 和 `includeAnrInfo` 三组 flag（功能开关）；
- 在事件日志中保存 original activity（最初 Activity）、focus target 和最终 blamed target（被归责目标）；
- 记录 warning 生成、AMS 投递、listener 接收的三段延迟；
- 测试自定义 dispatch timeout、硬件乘数和锁竞争；
- 对 trace 失败、PID 已退出和跨 UID 改归因保留明确状态。

### 测试用例

至少覆盖：

- Activity 已成为 focused application，但延迟添加窗口；
- 窗口在 warning 后、deadline 前出现；
- focused application 在倒计时期间切换；
- 当前 focus holder 长时间阻碍新 focus；
- 已有窗口不确认输入事件，确认不会收到 no-focus warning；
- warning listener 多进程重复；
- flag 分别关闭；
- deadline 前 `system_server` 被 CPU 或锁延迟；
- `ApplicationExitInfo.AnrInfo` 存在与缺失两条分支。

## 15. 版本边界

| 平台 | 已核对结论 |
|---|---|
| Android 14—16 | 不能从对应 release tag（发布版本标签）找到这套 `processPreAnrsLocked()` / no-focus warning 实现 |
| Android 17 / API 37 | 增加 InputDispatcher no-focus pre-ANR、公开 warning 投递、可选 long method tracing 与 input `AnrInfo` 载荷 |

输入 timeout、WMS 归因和 ANR 主路径在更早版本已经存在，但 Android 17 的 pre-warning 行为不能倒推到 Android 14—16。

## 16. 结论

Android 17 为 no-focused-window 输入 ANR 增加了一次 deadline 前的观测机会：

1. InputDispatcher 根据实际 timeout 计算 warning_at；
2. warning 经 JNI 和 WMS 直接进入 AMS 的公开 warning 流程；
3. WMS 可按 flag 触发 3 秒 Long Method Trace；
4. deadline 到期后重新检查焦点状态，再决定正式 ANR；
5. `TimeoutRecord` 携带 input event id，支持后续 `ApplicationExitInfo.AnrInfo` 关联。

这套机制没有覆盖 window-unresponsive pre-warning，也不保证 callback 领先 deadline 固定时长。诊断系统应把 warning、可选 trace、正式责任判断和退出记录视为四份各自可能缺失的证据。

## 参考资料

- [AOSP `InputDispatcher.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.cpp)
- [AOSP `InputDispatcher.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/InputDispatcher.h)
- [AOSP `InputDispatcherPolicyInterface.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/inputflinger/dispatcher/include/InputDispatcherPolicyInterface.h)
- [AOSP `IInputConstants.aidl`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/input/android/os/IInputConstants.aidl)
- [AOSP NativeInputManager JNI（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/jni/com_android_server_input_InputManagerService.cpp)
- [AOSP `InputManagerService.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/input/InputManagerService.java)
- [AOSP WMS `InputManagerCallback.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/InputManagerCallback.java)
- [AOSP WMS `AnrController.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/AnrController.java)
- [AOSP `ActivityManagerService.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
- [AOSP `TimeoutRecord.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/TimeoutRecord.java)
- [AOSP `LongMethodTracer.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/utils/LongMethodTracer.java)
- [Android Developers：`ActivityManager.registerAnrWarningListener()`](<https://developer.android.com/reference/android/app/ActivityManager#registerAnrWarningListener(java.util.concurrent.Executor,java.util.function.Consumer)>)
