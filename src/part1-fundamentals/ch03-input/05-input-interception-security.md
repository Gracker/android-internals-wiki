---


status: "finalized"
title: 输入事件拦截与安全机制
chapter: '3.5'
section: '3.5'
drafted_by: openclaw-task
applicable_versions: Android 10 (API 29) - Android 17 (API 37), 主线源码基准已复核 android-17.0.0_r1, Android 10-16 仅作历史演进参照, 密码输入场景的 InputMonitor 切断暂不作为 AOSP 源码结论
confidence: medium
last_verified: "2026-07-10"
last_verified_against: "AOSP android-17.0.0_r1 input/security paths and Android Developers APIs"
reviewed_date: "2026-07-10"
reviewed_by: "openclaw-task6"
task6_result: "pass-light-edit"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
pipeline_stage: "ready-to-publish"
sources:
- type: official
  path: https://source.android.com/docs/core/interaction/input
- type: official
  path: https://developer.android.com/reference/android/accessibilityservice/AccessibilityService
- type: official
  path: https://developer.android.com/reference/android/app/Instrumentation
- type: official
  path: https://developer.android.com/reference/android/app/UiAutomation
tags:
- android
- input
- security
- accessibility
- InputDispatcher
- Perfetto
related_chapters:
- '3.1'
- '3.2'
- '9.1'
- '9.2'
review_notes: >-
  2026-04-19 task6 re-review: pass-light-edit. L1小修7处(删除旧稿/编辑痕迹)。无需回炉。 | 2026-05-12 Task6 16:15：写作复审通过；清理 frontmatter 重复字段；Task9 已通过且 queue 无 pending，自动晋升 finalized。 | Task2B Verifier (2026-07-10T03:34:07+08:00): 状态修正 — status: finalized → ready-for-review, task9_state: reviewed → pending。Task9 auto-fix 后 status 未从 finalized 重置为 ready-for-review，导致 Task6 无法拾取；已修正。
task2b_result: fixed-lite
task9_result: "pass-tech-review"
task9_reviewed_date: "2026-07-10"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-07-10T04:30:34+08:00"
last_task6_at: "2026-07-10T04:12:20+08:00"
last_task6_review_log: "logs/review/2026-07-10-04-review.md"
task6_review_notes: "2026-07-10 Task6 revisiting-review (round 3): pass-light-edit。Task9 auto-fix(源码锚点升级android-17.0.0_r1, SystemUI back gesture InputMonitorCompat路径, GameManagerService power mode方法名)回流后写作层复审通过；L1 禁用词/高频词/物理动词/元叙述零命中；L2 开头/节奏/结构/读者引导全部通过；outline 5/5 锚点全覆盖；否定-纠正结构1处(限额内)；无 L1/L2 问题，无 L3/L4 回炉项。送 Task9 终审确认。"
last_task9_review_log: "logs/deep-review/2026-07-10-04-deep-review.md"
task9_review_notes: "2026-07-10 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；复核 InputFilter/InputMonitor/Accessibility 注入、SystemUI back gesture InputMonitorCompat、GameManagerService power mode 的 android-17.0.0_r1 锚点；Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-07-10-04-deep-review.md。 | 2026-06-02 Task9 deep review: pass-tech-review。InputFilter/InputMonitor/Accessibility 注入与 Android 16/17 版本边界复核通过；P0 0 / P1 0 / P2 0，queue 无 pending，自动晋升 finalized。 | 2026-07-10 Task9 idle audit auto-fix：将主线源码锚点切到 android-17.0.0_r1，修正 SystemUI back gesture InputMonitorCompat 源码路径和 GameManagerService power mode 方法名；回到 Task6 复审。"
last_task9_audit: "2026-07-10"
last_task9_audit_log: "logs/deep-review/2026-07-10-01-audit.md"
last_task9_autofix_at: "2026-07-10"
last_task9_autofix_log: "logs/deep-review/2026-07-10-01-audit.md"
last_task6_audit: "2026-07-07"
last_task2b_lite_at: '2026-06-01'
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_new_rework: false
p0: 0
p1: 0
p2: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-10
updated_by: "openclaw-task9"
updated_date: "2026-07-10"
---

# 输入事件拦截与安全机制

## 为什么要了解输入事件拦截与安全机制

第 3.1 节追踪了输入事件从硬件到 View 树的完整路径。正常分发之外，系统还允许特权组件在不同位置监控、过滤或注入事件。

如果 InputDispatcher 队列和 App 主线程都没有明显阻塞，事件仍可能停留在 system_server 的 filter Handler、无障碍按键待决队列或 spy window 手势接管阶段。忽略这些分支，容易把事件未到达 App 误判成 View 分发问题。

平台源码以 AOSP `android-17.0.0_r1` 为锚点；Android 10—16 只在确有版本差异时作为沿革参照。涉及 Linux input/evdev 的边界以 `android17-6.18-2026-06_r6` 为 kernel 锚点，不从通用内核代码推断厂商触控驱动策略。

## InputFilter：系统级事件拦截

### 什么是 InputFilter

`InputFilter` 是隐藏的系统级全局过滤机制。硬件 key/motion event 经过 WindowManagerPolicy 的早期 policy 回调后，如果 filter 已启用，`InputDispatcher` 会先把事件交给 filter，而不直接入队给目标窗口。

它与 `ViewGroup.onInterceptTouchEvent()` 的作用域不同：前者位于系统分发链，最多只能安装一个，影响全局硬件输入；后者只决定本 View 树中的触摸归属。`InputFilter` 不接收 Instrumentation 等普通注入入口产生的事件，这可防止注入事件再次进入过滤器形成循环。

### InputFilter 的注册流程

InputFilter 的入口不是公开的 `IWindowManager` Binder API。`WindowManagerInternal#setInputFilter()` 由 `WindowManagerService.LocalService` 实现，再把 filter 交给 `InputManagerService`。IMS 保存当前 filter、创建 `InputFilterHost`、调用 `filter.install(mInputFilterHost)`，然后只把 enabled 布尔值同步到 Native 层。

```java
// WindowManagerService.LocalService
@Override
public void setInputFilter(IInputFilter filter) {
    mInputManager.setInputFilter(filter);
}

// frameworks/base/services/core/java/com/android/server/input/InputManagerService.java
public void setInputFilter(IInputFilter filter) {
    synchronized (mInputFilterLock) {
        ...
        if (filter != null) {
            mInputFilter = filter;
            mInputFilterHost = new InputFilterHost();
            filter.install(mInputFilterHost);
        }
        mNative.setInputFilterEnabled(filter != null);
    }
}
```

Native `InputDispatcher` 不持有 Java `IInputFilter`。`mInputFilterEnabled` 为 `true` 时，它调用 policy 的 `filterInputEvent(...)`：

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
if (shouldSendMotionToInputFilterLocked(args)) {
    policyFlags |= POLICY_FLAG_FILTERED;
    if (!mPolicy.filterInputEvent(event, policyFlags)) {
        return; // 原事件不进入普通 dispatch queue
    }
}
```

返回 `false` 的含义是“当前原事件不再继续入队”，不等于 filter 已经永久消费它。`InputManagerService.filterInputEvent()` 会把事件交给 `IInputFilter.filterInputEvent()`；`InputFilter` 再通过自己的 Handler 调用 `onInputEvent()`。默认实现调用 `sendInputEvent()`，由 `InputFilterHost` 加上 `FLAG_FILTERED` 并异步注回 Native dispatcher。

完整链路如下：

`WindowManagerInternal.setInputFilter()` → `InputManagerService.setInputFilter()` → `filter.install(host)` → `mNative.setInputFilterEnabled(true)` → `InputDispatcher.filterInputEvent()` → `InputFilter` Handler → `InputFilterHost.sendInputEvent()` → `mNative.injectInputEvent(... FLAG_FILTERED)`

按键使用同一模型，只是 Native 判断入口换成 `shouldSendKeyToInputFilterLocked()`。启用或禁用 filter 时，`InputDispatcher#setInputFilterEnabled()` 会调用 `resetAndDropEverythingLocked()` 清理进行中的分发状态；系统选择丢弃当前流，是为了避免新旧 filter 状态拼成不一致的手势。

### InputFilter 的事件处理模型

`InputFilter#onInputEvent()` 默认调用 `sendInputEvent(event, policyFlags)` 放行。自定义 filter 可以不发送原事件，也可以构造替代事件再发布。事件在回调返回后会被回收；需要跨回调保存时必须复制。

该机制会拦下原事件，再决定是否发出另一个事件，而非在原地修改共享状态。`InputFilter` 文档也强调事件一致性：如果过滤器重组一串 `MotionEvent`，必须保证 down/move/up 序列仍然合法，否则下游窗口会收到不成对的事件。

Android 默认的 `AccessibilityInputFilter` 运行在 system_server。接口本身是隐藏 API，而且全局 filter 由 WMS/IMS 管理；普通 App 无法注册。若系统把自定义 filter 放在其他进程，`InputFilterHost.sendInputEvent()` 还会检查调用者是否持有 `INJECT_EVENTS`。

### InputFilter 在 Perfetto 中的表现

两类耗时需要分开：

- filter 通用开销来自事件复制、Handler 排队、变换逻辑和 filtered event 重新注入。Native policy 回调带有 `filterInputEvent` atrace slice，但异步 Handler 与再次注入之间不能只靠这一条 slice 量完。
- 无障碍按键过滤还会进入 `KeyboardInterceptor` 和 `KeyEventDispatcher`，等待一个或多个服务异步返回 `setOnKeyEventResult()`。这个等待不会让 InputDispatcher 线程同步卡在远端 Binder 上。

Android 17 在 filter 启用时不为原始 InputReader event 记录 `InputDispatcher` 的 per-device latency tracker，因此不能把缺失的 latency metric 解释成“filter 没有开销”。

## InputMonitor：特权组件的旁路监控

### 什么是 InputMonitor

`InputMonitor` 允许特权组件在不是普通触摸目标窗口时接收 pointer stream。`InputManagerService.monitorGestureInput()` 会创建 input channel、gesture monitor surface 和 spy window；spy window 不参与普通前台目标窗口的命中选择，但可以作为额外目标收到事件。

调用方必须持有隐藏权限 `android.permission.MONITOR_INPUT`。`android-17.0.0_r1` 的 manifest 将它声明为 `signature|recents`，不属于通用 `privileged` 权限。普通 App 和普通第三方无障碍服务拿不到这个入口。

### spy window 与 pilferPointers

gesture monitor 对应的窗口带有 **spy** input config。Android 17 还强制所有 spy window 同时为可信叠加层。它有两种工作状态：

1. **监控阶段**：spy window 与普通目标各自通过自身连接接收事件。它不替代命中的前台窗口，也不会因为“看见了事件”就消费目标流；monitor 自身仍须及时消费通道中的 channel。
2. **接管阶段**：调用 `pilferPointers()` 后，InputDispatcher 从其他可被 pilfer 的窗口移走当前 pointer，并向被取消的目标合成 cancellation event。典型结果是原目标窗口收到 `ACTION_CANCEL`，后续事件流由请求 pilfer 的 spy window 持有；标记了 `DO_NOT_PILFER` 的窗口例外。

SystemUI 的边缘返回手势使用这套模式：先用 gesture monitor 观察边缘触摸，确认系统返回手势后再 pilfer。“收到副本”与“主动接管”对目标 App 的影响完全不同。

在 Perfetto 中，目标窗口的 touch slice 会以 `ACTION_CANCEL` 中断，同时系统 UI 进程开始处理手势。如果 App 的触摸流意外中断，可以检查是否有系统监视窗口截取了指针。

### InputMonitor 与 InputFilter 的区别

| 能力 | InputFilter | InputMonitor (spy window) |
|------|-------------|--------------------------|
| 能否消费事件 | 是（`onInputEvent()` 不调用 `sendInputEvent()`） | 监控时只拿额外副本；接管需另调 `pilferPointers()` |
| 能否拿走 pointer stream | 否 | 是（`pilferPointers()`） |
| 能否发出替代事件 | 是（`sendInputEvent()`） | 否（只能读，不能注入） |
| 权限要求 | 隐藏系统入口，由 WMS/IMS 管理 | `MONITOR_INPUT`，`signature|recents` |
| 典型使用方 | `AccessibilityInputFilter`、厂商定制 filter | SystemUI `EdgeBackGestureHandler`（手势导航返回）、系统 UI 手势识别 |

三类输入旁路能力的边界：

1. **旁路监控副本**（InputMonitor / spy window）：只读，不改变事件流。用于系统手势检测、导航手势识别。
2. **拿走 pointer stream**（`pilferPointers()`）：把当前 pointer stream 从目标窗口转移到 spy window。用于系统导航手势接管。
3. **消费/重发事件**（InputFilter）：拦截原始事件，决定放行、消费或发出替代事件。用于全局输入策略和无障碍变换。

## 无障碍服务的事件拦截

### AccessibilityService 与 Input 事件的关系

无障碍和 Input 的系统侧交叉点主要在 `AccessibilityInputFilter`。系统按已启用功能组装 transformation chain：按键可进入 `KeyboardInterceptor`，触摸可进入 `TouchExplorer`、放大手势处理器或 `MotionEventInjector`。未被 transformation 消费的事件最终通过 filter host 重新注入 InputDispatcher。

按键过滤的前提不是在 `android:accessibilityEventTypes` 里写一个 flag。真实约束分成两步：

1. 服务 metadata 中声明 `android:canRequestFilterKeyEvents="true"`，系统据此赋予 `AccessibilityServiceInfo.CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`
2. 服务运行时把 `AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS` 放进 `AccessibilityServiceInfo.flags`

Android 10 到 Android 17 都使用 capability + runtime flag 这套门禁。`onKeyEvent()` 收到的是副本，返回 `true` 表示消费，返回 `false` 表示继续向系统分发；修改这个副本不会修改下游收到的原事件。

触摸和其他 motion source 有三种容易混淆的公开能力：

- API 34 起，服务可用 `AccessibilityServiceInfo.setMotionEventSources()` 选择 generic motion source，并在 `AccessibilityService.onMotionEvent()` 收到事件。被选中的 source 不再发给系统其余部分；回调返回 `void`，不是“修改后放行”接口。若任一服务开启 touch exploration，`onMotionEvent()` 不会接收 touchscreen event。
- `FLAG_SEND_MOTION_EVENTS` 是 touch exploration 的配套 flag，用于把已识别、取消或 passthrough 手势的 motion samples 发送给服务。它与 API 34 的 generic source 监听不是同一个开关。
- `TouchInteractionController` 用于观察和控制 touchscreen interaction；`dispatchGesture()` 则生成一段新的 accessibility injected 手势。

### 事件拦截的回调路径

按键过滤可以拆成两个阶段看。

**阶段 1：Input 子系统把按键送进 accessibility filter。**

`InputReader → InputDispatcher → mPolicy.filterInputEvent(...) → AccessibilityInputFilter → KeyboardInterceptor`

这一步发生在 system_server 一侧，`InputDispatcher` 只负责把事件交给 filter。

**阶段 2：无障碍服务异步给出“消费/放行”结果。**

`KeyboardInterceptor → AccessibilityManagerService.notifyKeyEvent() → KeyEventDispatcher.notifyKeyEventLocked() → AccessibilityService.onKeyEvent()`

`KeyEventDispatcher` 会为待判定的按键创建 `PendingKeyEvent`，并启动 500ms 超时计时。服务稍后通过 `setOnKeyEventResult()` 回传结果：

- 至少一个服务返回 handled，且所有服务都已返回或超时后，事件在无障碍层结束；
- 所有服务都返回 unhandled，或未响应服务到达 500ms 超时后，`KeyEventDispatcher` 把按键送回 input filter，再继续分发。

多个服务的等待并行记在同一个 pending event 上，不能把 500ms 乘以服务数量。分析按键延迟时，应看 `AccessibilityManagerService`、`KeyEventDispatcher` 和服务进程自己的处理时间。

### 事件修改的安全限制

无障碍或系统 filter 的修改范围分为三类。

1. **原始硬件事件不能被服务直接原位改写。** 触摸从 `EventHub/InputReader` 进入系统后，普通服务拿不到内核事件缓冲。无障碍通常消费原事件，再通过 `MotionEventInjector` 或 `dispatchGesture()` 发出替代手势。
2. **按键判定是“消费还是放行”，不是修改原 `KeyEvent` 再放行。** `AccessibilityService.onKeyEvent()` 给出的只是一个布尔结果。若服务想产生另一组按键，仍然要走注入入口。
3. **`source` 不能拿来判断无障碍注入。** `MotionEvent.getSource()` / `KeyEvent.getSource()` 描述设备类别。Native 会把 accessibility policy flag 转换成 `FLAG_IS_ACCESSIBILITY_EVENT`，但 Android 17 中 KeyEvent 与 MotionEvent 的这个常量都是 `@TestApi @hide`。系统或测试代码可以使用，普通 App 没有受支持的通用 injected-event 检测 API。`POLICY_FLAG_INJECTED`、`POLICY_FLAG_INJECTED_FROM_ACCESSIBILITY` 也只在系统内部流转。

## 系统级事件注入

### 几种常见事件注入路径

这些入口都生成 injected event，但调用身份、目标范围和进入 filter 的位置不同。`InputFilter.java` 明确说明：Instrumentation 等普通注入入口产生的事件不再交给全局 InputFilter。只有专用的 accessibility filter 测试入口，或 `dispatchGesture()` 在 filter transformation chain 内生成的事件，才会经过 accessibility filter 语义。

#### 1. Instrumentation.sendPointerSync()

`Instrumentation.sendPointerSync()` 在 `DOWN` 前和 `UP` 后同步 window transaction，然后调用 `InputManagerGlobal.injectInputEvent(..., Process.myUid())`。target UID 限制注入只能命中 instrumentation target 自身拥有的窗口；命中其他 UID 的窗口会失败。

```java
// frameworks/base/core/java/android/app/Instrumentation.java
public void sendPointerSync(MotionEvent event) {
    ...
    syncInputTransactionsAndInjectEventIntoSelf(event);
}

private void syncInputTransactionsAndInjectEventIntoSelf(MotionEvent event) {
    ...
    InputManagerGlobal.getInstance().injectInputEvent(
            event, InputManager.INJECT_INPUT_EVENT_MODE_WAIT_FOR_FINISH, Process.myUid());
}
```

它没有直接写 `ViewRootImpl` 的 InputChannel，底层仍进入 `InputManagerService.injectInputEventToTarget()`。方法使用 `WAIT_FOR_FINISH`，只等待接收方 finish input event，不保证对应 UI 已完成绘制或 present。

#### 2. UiAutomation.injectInputEvent()

`UiAutomation.injectInputEvent()` 通过受信任的 `UiAutomationConnection` 调用标准 `InputManagerGlobal.injectInputEvent()`，可以跨应用窗口工作。它会按 `DOWN` / `UP` 边界同步 window transaction，并根据 `sync` 参数选择 `WAIT_FOR_FINISH` 或 `ASYNC`。作为标准 injected event，它不进入 InputFilter。

#### 3. UiAutomation.injectInputEventToInputFilter()

这是 `@TestApi` 且已 deprecated 的 filter 测试入口。它通过 `UiAutomationConnection` 调到 `AccessibilityManagerService.injectInputEventToInputFilter()`，直接把事件交给 accessibility input filter，不代表普通测试或 App 注入路径。

#### 4. adb shell input

Android 17 的 `cmds/input/input.sh` 只转调 `cmd input`；命令逻辑位于 `InputShellCommand`，最终调用 `InputManagerGlobal.injectInputEvent()`。它依赖 shell 身份拥有的注入权限，走标准 injected event 路径，不进入 InputFilter。

#### 5. AccessibilityService.dispatchGesture()

`dispatchGesture()` 不使用普通 App 的 `INJECT_EVENTS` 入口。服务连接先通过 `canPerformGestures()` 安全检查，再取得对应 display 的 `MotionEventInjector`。injector 在 accessibility transformation chain 中生成 `MotionEvent`，加入内部 `FLAG_INJECTED_FROM_ACCESSIBILITY`；若服务声明自己是 accessibility tool，还会加入 `FLAG_INJECTED_FROM_ACCESSIBILITY_TOOL`。到达 Native dispatcher 后，这些 policy flag 才转换成 MotionEvent 内部 flag。

```java
// frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityServiceConnection.java
public void dispatchGesture(int sequence, ParceledListSlice gestureSteps, int displayId) {
    ...
    MotionEventInjector motionEventInjector =
            mSystemSupport.getMotionEventInjectorForDisplayLocked(displayId);
    ...
    motionEventInjector.injectEvents(
            gestureSteps.getList(), mClient, sequence, displayId,
            mAccessibilityServiceInfo.isAccessibilityTool());
}
```

几种入口的差异如下：

| 方式 | 进入方式 | InputFilter 关系 | 目标范围 | 普通 App 的受支持标记 |
|------|----------|------------------|----------|------------------------|
| `Instrumentation.sendPointerSync()` | 标准注入，target UID = `Process.myUid()` | 绕过 | instrumentation target 的窗口 | 无 |
| `UiAutomation.injectInputEvent()` | 受信任 UiAutomation 连接下的标准注入 | 绕过 | 可跨应用 | 无 |
| `UiAutomation.injectInputEventToInputFilter()` | accessibility filter 专用测试入口 | 直接进入 | filter 测试 | 无稳定 public API |
| `adb shell input` | shell → `InputShellCommand` → 标准注入 | 绕过 | shell 权限允许的目标 | 无 |
| `AccessibilityService.dispatchGesture()` | `MotionEventInjector` 在 accessibility chain 内生成 | 在 filter 内产生，再以 filtered event 注入 | 指定 display 上的命中窗口 | 无；系统/测试代码有隐藏 accessibility flag |

`POLICY_FLAG_INJECTED` 是 InputDispatcher 内部 policy flag，`InputEvent` 基类也没有统一的 `getFlags()`。`MotionEvent.isFromSource()` 只能判断设备 source，不能区分 injected event 和硬件事件。

### 注入事件的权限控制

标准注入入口最终都会过 `InputManagerService.injectInputEventToTarget()` 的权限检查。`android-17.0.0_r1` 调用 `checkCallingPermission(INJECT_EVENTS, ..., checkInstrumentationSource = true)`：先检查直接调用者，再按需检查 instrumentation source UID。两者都不满足时抛出 `SecurityException`。

`Instrumentation` 和 `UiAutomation` 的可用性来自测试框架建立的受控身份，并不表示普通 App 获得全局注入权。`dispatchGesture()` 使用另一套门禁：服务 metadata 需要声明 `canPerformGestures`，连接还要通过无障碍安全策略校验。

## Input 事件的安全边界

### 哪些环节可以被拦截/修改

Input 事件从硬件到 App 之间，可编程拦截点包括：

| 位置 | 能做什么 | 典型实现 |
|------|----------|----------|
| `InputReader` / policy | 设备级重映射、丢弃、策略判断 | 系统 policy、厂商输入定制 |
| `InputFilter` | 放行、消费、发出替代事件 | 自定义系统 filter、`AccessibilityInputFilter` |
| `AccessibilityInputFilter` 内部变换器 | 按键判定、触摸探索、手势注入 | `KeyboardInterceptor`、`TouchExplorer`、`MotionEventInjector` |
| App 自己的 `InputStage` / `ViewGroup` | 只影响本进程窗口 | `ViewRootImpl`、`onInterceptTouchEvent()` |

普通 App 或普通服务无法访问以下位置：

1. **`EventHub → InputReader` 的原始设备事件。** 这是内核输入设备到系统服务的边界。
2. **`InputChannel` 的 socket 传输。** 事件进入 socket 之后，App 只能从自己那一端读，不能改 system_server 已经写出的包。
3. **InputDispatcher 内部 policy flag。** 例如 `POLICY_FLAG_INJECTED` 只在分发器里流转，不是 public API。

这些边界区分了全局过滤器与 App View 层各自能做的操作。

### 安全策略的版本演进

当前只保留能直接从 AOSP 和官方文档核对到的结论。

| 版本/来源 | 能直接核对到的结论 | 证据 |
|-----------|--------------------|------|
| android-10.0.0_r1 | `canRequestFilterKeyEvents` metadata 会转成 `CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`；运行时用 `FLAG_REQUEST_FILTER_KEY_EVENTS` 打开按键过滤 | `AccessibilityServiceInfo.java` |
| API 34 | 新增 `AccessibilityService.onMotionEvent()` 与 `setMotionEventSources()`；被选择的 motion source 不再继续发给系统其他部分 | Android API reference、`AccessibilityService.java` |
| android-17.0.0_r1 | 按键过滤仍使用 capability + runtime flag；标准 injected event 绕过 InputFilter | `AccessibilityServiceInfo.java`、`InputFilter.java` |
| android-17.0.0_r1 | accessibility policy flag 会转换成 event 内部的 accessibility flag，但对应 Java 常量是 `@TestApi @hide` | `InputDispatcher.cpp`、`KeyEvent.java`、`MotionEvent.java` |
| API 34—37 | `View.setAccessibilityDataSensitive(...)` 同时约束非 accessibility-tool 服务的节点交互、事件数据和 injected touch | `View.java`、`AccessibilityInteractionController.java` |

### Android 17 基线：从权限控制到查询通道隔离

`accessibilityDataSensitive` 在 API 34 引入。Android 17 中，`ACCESSIBILITY_DATA_SENSITIVE_YES` 或自动推断为 sensitive 的 View 会受到多层保护：

- `AccessibilityInteractionController` 不向非 accessibility-tool 请求返回该 View 的节点；
- AccessibilityEvent 会携带数据敏感属性，由系统按接收服务身份过滤；
- `View#onFilterTouchEventForSecurity()` 会丢弃非 accessibility-tool 服务注入到敏感 View 的触摸；
- 父 View 的 sensitive 状态会传给后代，启用 `filterTouchesWhenObscured` 的 View 默认也会推断为 sensitive。

这组限制同时作用于无障碍查询通道和 View 触摸安全检查。它不关闭 InputDispatcher，也不表示系统已经停止所有 InputMonitor 副本。

## 事件拦截对性能的影响

### InputFilter 的延迟开销

`InputFilter` 自身带来的延迟主要来自事件复制、Handler 排队、本地变换和 filtered event 重新注入。没有同设备 trace 或 microbenchmark 时，不应给出固定毫秒数。

空 filter 也必然经过异步 Handler 和一次重新注入；复杂 filter 还会叠加对象分配、手势状态机或跨进程等待。量化时，应在同一设备、同一 trace 配置下比较 filter 关闭、只放行和实际变换三种状态。

### 无障碍服务对事件分发路径的性能影响

无障碍的性能成本要按事件类型分开看。

**按键事件。** 开启 `FLAG_REQUEST_FILTER_KEY_EVENTS` 后，事件会先到 `KeyboardInterceptor`，再交给 `KeyEventDispatcher` 等待服务结果。等待窗口上限是 500ms。这个等待发生在无障碍子系统维护的 `PendingKeyEvent` 队列里，不是 `InputDispatcher` 同步等远端 Binder。

**触摸事件。** `TouchExplorer`、放大镜手势处理器、`MotionEventInjector` 可能把一段原始触摸重写成另一串 `MotionEvent`。这会增加事件数量，也会让时序更复杂。TalkBack 的“朗读后双击激活”就是这类变换的典型例子。

**服务进程自身的耗时。** `AccessibilityService.onKeyEvent()` 的 Binder callback 经服务执行器运行；如果执行线程被占用，结果返回就会变慢，待决按键在 `KeyEventDispatcher` 中停留更久。`onAccessibilityEvent()` 的重任务也可能争用同一服务执行资源。

分析时，不要只看 Binder slice，还要检查：
- `KeyboardInterceptor` / `KeyEventDispatcher` 是否积压待判定按键
- 服务进程回结果是否接近 500ms 超时
- `dispatchGesture()` 是否把一次用户动作扩成了更多 injected `MotionEvent`

### 性能影响对比表

| 机制 | 额外工作发生位置 | 影响范围 | 当前能直接核对的结论 |
|------|------------------|----------|----------------------|
| 轻量 `InputFilter` | system_server filter 回调 | 经过 filter 的 key / motion | 会增加分发前处理时间，幅度取决于 filter 代码 |
| 无障碍按键过滤 | `KeyboardInterceptor` + `KeyEventDispatcher` + 服务进程 | 开启 key filter 的按键 | 单个 pending event 的等待上限 500ms；无人处理时继续分发 |
| 无障碍手势注入 | `MotionEventInjector` | 目标窗口 | 会额外生成 accessibility injected `MotionEvent` |
| App 自己的 `onInterceptTouchEvent()` | App 进程 | 仅本 App | 不会回过头影响全局 `InputDispatcher` |

## 厂商定制的拦截增强方案

### 游戏模式中的输入优先级

AOSP 标准 GameMode 没有独立的 InputDispatcher 游戏优先队列。Android 17 的 `GameManagerService` 在游戏 UID 进入前台时切换 `PowerManagerInternal.Mode.GAME`；性能模式上报 loading state 时还可以短时切换 `Mode.GAME_LOADING`。Game Mode interventions 还包括 frame-rate override、downscale 等图形策略。这些能力可能间接改善输入到显示的延迟，但没有改变焦点窗口选择或 InputChannel 的分发优先级。

如果厂商宣称游戏模式提升“输入优先级”，应分别检查触控报点率、CPU/线程调度、显示刷新率和 InputDispatcher queue；不能仅凭 GameMode 开关推导分发器存在加权机制。

### 防误触机制

边缘抑制、口袋模式和手掌拒绝可能由触控固件、内核驱动、InputReader 映射器或系统 filter 实现。AOSP 没有规定统一的边缘宽度、压力阈值或厂商算法。

定位实现层时可以按事件是否存在逐级判断：

1. `getevent -lt` 已经没有对应触点：优先查触控控制器或内核驱动；
2. evdev 有事件、InputReader 输出缺失或发生重分类：查设备配置与 mapper；
3. dispatcher 收到事件、目标窗口没有收到：查 policy、InputFilter、spy/pilfer 和窗口安全规则；
4. App 收到完整 stream 后自行取消：回到 View/Compose 手势逻辑。

## Android 17 基线下仍可核对到的权限边界

`android-17.0.0_r1` 中需要同时记住四类门禁：

1. **全局 filter**：隐藏系统接口，只能由 WMS/IMS 安装；
2. **gesture monitor**：调用者必须持有 `MONITOR_INPUT`，其 protection level 是 `signature|recents`；
3. **标准注入**：调用者或 instrumentation source 必须满足 `INJECT_EVENTS`；
4. **无障碍能力**：key filter 和 gesture injection 分别受 capability/runtime flag 与 `canPerformGestures()` 控制，敏感 View 还会按 `isAccessibilityTool` 再过滤。

## 在 Perfetto 中分析事件拦截问题

排查这类问题时，需要把事件停留的层次分出来。

### Step 1：确认事件有没有进入 InputDispatcher

在 `system_server` 中对齐 Native `filterInputEvent`、InputDispatcher 分发 slice 与目标进程的 `deliverInputEvent`：

- App 完全收不到事件，先确认是不是在 filter 或无障碍层被消费了
- App 能收到事件，但时间明显晚，再看 system_server 前置处理和无障碍服务回结果时间

### Step 2：把 InputFilter 本地处理和无障碍异步判定分开看

自定义 `InputFilter` 的成本分散在 native → Java copy、filter Handler 和 filtered event reinjection 三段。无障碍按键过滤还要确认 `KeyboardInterceptor` → `AccessibilityManagerService` → service process 是否接近 500 ms timeout。不要用一条 Binder slice 代替整段时序。

### Step 3：检查无障碍服务进程自己的处理时间

看服务进程主线程或工作线程上：
- `onKeyEvent()` 是否快速回结果
- `onAccessibilityEvent()` 是否挤占了主线程
- `dispatchGesture()` 之后是否又生成了更多 injected `MotionEvent`

如果服务回调本身慢，system_server 那边看到的通常是待决事件变多，不是 InputDispatcher 一条长时间静止的同步调用。

### Step 4：用 dumpsys 补足运行态信息

```bash
adb shell dumpsys input | grep -E "InputFilterEnabled|Input Dispatcher State"
adb shell dumpsys accessibility
```

`dumpsys input` 中的 `InputFilterEnabled` 直接说明 Native dispatcher 是否打开 filter。`dumpsys accessibility` 可确认已启用服务、capability 和 `A11yInputFilter Info` transformation chain。两者只能说明配置与运行态，是否消费了某个事件仍需与 trace 对齐。

## 常见问题与误区

### 误区一：App 可以注册自己的 InputFilter

不能。`InputFilter` 由 `WindowManagerService` / `InputManagerService` 管理，普通 App 没有这条入口，也拿不到全局注入所需的权限。

### 误区二：无障碍按键过滤是 InputDispatcher 同步调 `onKeyEvent()`

不是。`InputDispatcher` 把事件交给过滤器后，“是否消费”的判定发生在 `AccessibilityManagerService` / `KeyEventDispatcher` / 服务进程这一侧，并带 500ms 超时。

### 误区三：触摸无障碍只能“间接操作 UI 树”，不碰 MotionEvent

不对。`AccessibilityInputFilter.onInputEvent()` 会直接处理 `MotionEvent`，并按启用功能把事件交给 `TouchExplorer`、放大镜处理器或 `MotionEventInjector`。无障碍并不需要先经过 `AccessibilityInteractionController` 才能影响触摸流。

### 误区四：App 可以用 `InputEvent.getFlags()` 或 `MotionEvent.isFromSource()` 判断 injected event

不对。`InputEvent` 基类没有 `getFlags()`，`source` 只表示设备来源。`KeyEvent.getFlags()` 和 `MotionEvent.getFlags()` 虽然公开，但 `FLAG_IS_ACCESSIBILITY_EVENT` 在 Android 17 是 `@TestApi @hide`；读取硬编码 bit 也不构成稳定 public API。普通 App 不能可靠地区分所有 injected event 与硬件事件。

### 误区五：InputFilter 只影响按键事件

不对。android-17.0.0_r1 的 `InputDispatcher` 在 `mInputFilterEnabled` 为真时，会把按键和触摸都送到 `filterInputEvent(...)`。无障碍场景下，`KeyboardInterceptor` 负责按键，`TouchExplorer` 等组件负责触摸，两边都在 filter 这一层工作。

## 参考资料

### AOSP 源码路径

- `frameworks/base/services/core/java/com/android/server/wm/WindowManagerInternal.java`、`WindowManagerService.java` — 隐藏的 `setInputFilter()` local service
- `frameworks/base/services/core/java/com/android/server/input/InputManagerService.java` — `setInputFilter()`、`injectInputEventToTarget()`、`monitorGestureInput()`
- `frameworks/base/services/core/java/com/android/server/input/InputShellCommand.java` — `cmd input` 的标准注入
- `frameworks/base/core/res/AndroidManifest.xml` — `MONITOR_INPUT` protection level
- `packages/SystemUI/src/com/android/systemui/navigationbar/gestural/DisplayBackGestureHandler.kt` — `InputMonitorCompat("edge-swipe", displayId)`、`pilferPointers()` 调用
- `packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java` — 返回手势判定后转调 `pilferPointers()`
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — `filterInputEvent()` 调用点、`injectInputEvent()`
- `frameworks/native/services/inputflinger/dispatcher/TouchState.cpp` — spy/pilfer 后的 pointer 归属
- `frameworks/base/core/java/android/view/InputFilter.java` — `InputFilter` 抽象与 `sendInputEvent()`
- `frameworks/base/core/java/android/view/View.java` — `accessibilityDataSensitive`
- `frameworks/base/core/java/android/view/AccessibilityInteractionController.java` — 敏感 View 的无障碍查询过滤
- `frameworks/base/core/java/android/accessibilityservice/AccessibilityService.java` — `onKeyEvent()`、`onMotionEvent()`、`dispatchGesture()`
- `frameworks/base/core/java/android/accessibilityservice/AccessibilityServiceInfo.java` — `CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`、`FLAG_REQUEST_FILTER_KEY_EVENTS`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityInputFilter.java` — 无障碍 filter 的 key / motion 入口
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/KeyboardInterceptor.java` — 按键预处理
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java` — `notifyKeyEvent()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/KeyEventDispatcher.java` — `PendingKeyEvent`、500ms 超时、`setOnKeyEventResult()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityServiceConnection.java` — `dispatchGesture()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/MotionEventInjector.java` — accessibility 手势注入
- `frameworks/base/core/java/android/app/Instrumentation.java` — `sendPointerSync()`
- `frameworks/base/core/java/android/app/UiAutomation.java`、`UiAutomationConnection.java` — 标准注入与 filter 测试入口
- `frameworks/base/core/java/android/hardware/input/InputManagerGlobal.java` — `injectInputEvent()`
- `frameworks/base/services/core/java/com/android/server/app/GameManagerService.java` — `Mode.GAME`、`Mode.GAME_LOADING`

### 官方文档

- `https://source.android.com/docs/core/interaction/input`
- `https://developer.android.com/reference/android/accessibilityservice/AccessibilityService`
- `https://developer.android.com/reference/android/accessibilityservice/AccessibilityServiceInfo`
- `https://developer.android.com/reference/android/app/Instrumentation`
- `https://developer.android.com/reference/android/app/UiAutomation`

### 相关章节

- 3.1 Input 事件分发全流程 — 事件传递的基础路径
- 9.1 安全边界与权限模型 — 输入注入与系统权限的交叉点
- 9.2 无障碍服务的安全风险与审计 — 无障碍能力的安全侧分析
