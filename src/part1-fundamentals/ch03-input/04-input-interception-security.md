---
status: "finalized"
title: 输入事件拦截与安全机制
chapter: '3.4'
section: '3.4'
applicable_versions: Android 10 (API 29) - Android 17 (API 37), 主线源码基准已复核 android-17.0.0_r1, Android 10-16 仅作历史演进参照, 密码输入场景的 InputMonitor 切断暂不作为 AOSP 源码结论
confidence: medium
last_verified: "2026-07-10"
last_verified_against: "AOSP android-17.0.0_r1 input/security paths and Android Developers APIs"
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
---

# 3.4 输入事件拦截与安全机制

## 为什么要了解输入事件拦截与安全机制

第 3.1 节追踪了输入事件从硬件到 View 树的完整路径。正常分发之外，系统还允许特权组件在不同位置监控、过滤或注入事件。

如果 InputDispatcher 队列和应用主线程都没有明显阻塞，事件仍可能停留在 `system_server` 的过滤器 Handler 消息队列、无障碍按键待决队列或监视窗口（spy window）的手势接管阶段。忽略这些分支，容易把事件未到达应用误判成 View 分发问题。

平台源码以 AOSP `android-17.0.0_r1` 为基线；Android 10—16 只在确有版本差异时作为沿革参照。涉及 Linux input 子系统与 evdev 接口的边界以 `android17-6.18-2026-06_r6` 为内核基线，不从通用内核代码推断厂商触控驱动策略。

## InputFilter：系统级事件拦截

### 什么是 InputFilter

`InputFilter` 是隐藏的系统级全局过滤机制。硬件按键、触摸或其他运动事件经过 WindowManagerPolicy 的早期策略回调后，如果过滤器已启用，`InputDispatcher` 会先把事件交给过滤器，而不直接放入目标窗口的分发队列。

它与 `ViewGroup.onInterceptTouchEvent()` 的作用域不同：前者位于系统分发链，最多只能安装一个，影响全局硬件输入；后者只决定本 View 树中的触摸归属。`InputFilter` 不接收 Instrumentation 等普通注入入口产生的事件，这可防止注入事件再次进入过滤器形成循环。

### InputFilter 的注册流程

InputFilter 的入口不是公开的 `IWindowManager` Binder API。`WindowManagerInternal#setInputFilter()` 由 `WindowManagerService.LocalService` 实现，再把过滤器交给 InputManagerService（IMS，输入管理服务）。IMS 保存当前过滤器、创建 `InputFilterHost`、调用 `filter.install(mInputFilterHost)`，然后只把是否启用的布尔状态同步到原生层。

下面的源码摘录用于确认 Java 层保存过滤器对象并安装 `InputFilterHost`，原生层只接收启用状态。

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

原生 `InputDispatcher` 不持有 Java `IInputFilter`。`mInputFilterEnabled` 为 `true` 时，它调用系统策略接口的 `filterInputEvent(...)`：

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
if (shouldSendMotionToInputFilterLocked(args)) {
    policyFlags |= POLICY_FLAG_FILTERED;
    if (!mPolicy.filterInputEvent(event, policyFlags)) {
        return; // 原事件不进入普通 dispatch queue
    }
}
```

返回 `false` 的含义是“当前原事件不再继续入队”，不等于过滤器已经永久消费它。`InputManagerService.filterInputEvent()` 会把事件交给 `IInputFilter.filterInputEvent()`；`InputFilter` 再通过自己的 Handler 调用 `onInputEvent()`。默认实现调用 `sendInputEvent()`，由 `InputFilterHost` 加上 `FLAG_FILTERED` 并异步注回原生分发器。

完整链路如下：

`WindowManagerInternal.setInputFilter()` → `InputManagerService.setInputFilter()` → `filter.install(host)` → `mNative.setInputFilterEnabled(true)` → `InputDispatcher.filterInputEvent()` → `InputFilter` Handler → `InputFilterHost.sendInputEvent()` → `mNative.injectInputEvent(... FLAG_FILTERED)`

按键使用同一模型，只是原生判断入口换成 `shouldSendKeyToInputFilterLocked()`。启用或禁用过滤器时，`InputDispatcher#setInputFilterEnabled()` 会调用 `resetAndDropEverythingLocked()` 清理进行中的分发状态；系统选择丢弃当前事件流，是为了避免新旧过滤器状态拼成不一致的手势。

### InputFilter 的事件处理模型

`InputFilter#onInputEvent()` 默认调用 `sendInputEvent(event, policyFlags)` 放行。自定义过滤器可以不发送原事件，也可以构造替代事件再发布。事件在回调返回后会被回收；需要跨回调保存时必须复制。

该机制会拦下原事件，再决定是否发出另一个事件，并不会原地修改共享状态。`InputFilter` 文档也强调事件一致性：如果过滤器重组一串 `MotionEvent`，必须保证 `ACTION_DOWN`、`ACTION_MOVE`、`ACTION_UP` 序列仍然合法，否则下游窗口会收到不成对的事件。

Android 默认的 `AccessibilityInputFilter` 运行在 `system_server`。接口本身是隐藏 API，而且全局过滤器由 WindowManagerService（WMS，窗口管理服务）和 IMS 管理；普通应用无法注册。若系统把自定义过滤器放在其他进程，`InputFilterHost.sendInputEvent()` 还会检查调用者是否持有 `INJECT_EVENTS`。

### InputFilter 在 Perfetto 中的表现

两类耗时需要分开：

- 过滤器通用开销来自事件复制、Handler 排队、变换逻辑和带 `FLAG_FILTERED` 事件的重新注入。原生策略回调带有 `filterInputEvent` atrace 轨迹区段，但异步 Handler 与再次注入之间的耗时不能只靠这一段量完。
- 无障碍按键过滤还会进入 `KeyboardInterceptor` 和 `KeyEventDispatcher`，等待一个或多个服务异步返回 `setOnKeyEventResult()`。这个等待不会让 InputDispatcher 线程同步卡在远端 Binder 上。

Android 17 在过滤器启用时，不会为 InputReader 读入的原始事件记录 `InputDispatcher` 的单设备延迟指标。因此，缺少这项指标不能证明过滤器没有开销。

## InputMonitor：特权组件的旁路监控

### 什么是 InputMonitor

`InputMonitor` 允许特权组件在不是普通触摸目标窗口时也能接收指针事件流。`InputManagerService.monitorGestureInput()` 会创建 `InputChannel`、手势监视器 Surface 和监视窗口（spy window）。监视窗口不参与普通前台目标窗口的命中选择，但可以作为额外目标收到事件。

调用方必须持有隐藏权限 `android.permission.MONITOR_INPUT`。`android-17.0.0_r1` 的平台清单将它声明为 `signature|recents`，不属于通用的 `privileged` 权限。普通应用和第三方无障碍服务拿不到这个入口。

### 监视窗口与 `pilferPointers()`

手势监视器对应的窗口带有 `SPY` 输入配置，表示它可以旁路观察同一显示区域内的指针事件。Android 17 还强制所有监视窗口同时为可信叠加层，也就是只能由系统信任的组件创建这类叠加窗口。它有两种工作状态：

1. **监控阶段**：监视窗口与普通目标各自通过自身连接接收事件。它不替代命中的前台窗口，也不会因为“看见了事件”就消费目标流；监视器自身仍须及时读取并确认 `InputChannel` 中的事件。
2. **接管阶段**：调用 `pilferPointers()` 后，InputDispatcher 从其他允许被抢占的窗口移走当前指针，并向被取消的目标合成取消事件。典型结果是原目标窗口收到 `ACTION_CANCEL`，后续事件流由请求抢占的监视窗口持有；标记了 `DO_NOT_PILFER` 的窗口例外。

SystemUI 的边缘返回手势使用这套模式：先用手势监视器观察边缘触摸，确认系统返回手势后再抢占指针。“收到副本”与“主动接管”对目标应用的影响完全不同。

在 Perfetto 中，目标窗口的触摸轨迹区段会以 `ACTION_CANCEL` 中断，同时 SystemUI 进程开始处理手势。如果应用的触摸流意外中断，可以检查是否有系统监视窗口抢占了指针。

### InputMonitor 与 InputFilter 的区别

| 能力 | InputFilter | InputMonitor（监视窗口） |
|------|-------------|--------------------------|
| 能否消费事件 | 是（`onInputEvent()` 不调用 `sendInputEvent()`） | 监控时只拿额外副本；接管需另调 `pilferPointers()` |
| 能否拿走指针事件流 | 否 | 是（`pilferPointers()`） |
| 能否发出替代事件 | 是（`sendInputEvent()`） | 否（只能读，不能注入） |
| 权限要求 | 隐藏系统入口，由 WMS/IMS 管理 | `MONITOR_INPUT`，`signature|recents` |
| 典型使用方 | `AccessibilityInputFilter`、厂商定制过滤器 | SystemUI `EdgeBackGestureHandler`（手势导航返回）、系统界面手势识别 |

三类输入旁路能力的边界：

1. **旁路监控副本**（InputMonitor 监视窗口）：只读，不改变事件流，用于系统手势检测和导航手势识别。
2. **拿走指针事件流**（`pilferPointers()`）：把当前指针事件流从目标窗口转移到监视窗口，用于系统导航手势接管。
3. **消费或重发事件**（InputFilter）：拦截原始事件，决定放行、消费或发出替代事件，用于全局输入策略和无障碍变换。

## 无障碍服务的事件拦截

### AccessibilityService 与 Input 事件的关系

无障碍子系统和输入系统的主要交叉点是 `AccessibilityInputFilter`。系统按已启用功能组装变换链（transformation chain）：按键可进入 `KeyboardInterceptor`，触摸可进入 `TouchExplorer`、放大手势处理器或 `MotionEventInjector`。未被变换器消费的事件最终通过 `InputFilterHost` 重新注入 InputDispatcher。

按键过滤的前提不是在 `android:accessibilityEventTypes` 里写一个标志。实际约束分成两步：

1. 在服务配置元数据（metadata）中声明 `android:canRequestFilterKeyEvents="true"`，系统据此赋予 `AccessibilityServiceInfo.CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS` 能力；
2. 服务运行时把 `AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS` 放进 `AccessibilityServiceInfo.flags`。

Android 10 到 Android 17 都使用“配置能力加运行时标志”这套门禁。`onKeyEvent()` 收到的是副本，返回 `true` 表示消费，返回 `false` 表示继续向系统分发；修改这个副本不会修改下游收到的原事件。

触摸和其他运动事件来源有三种容易混淆的公开能力：

- API 34 起，服务可用 `AccessibilityServiceInfo.setMotionEventSources()` 选择通用运动事件来源（generic motion source），并在 `AccessibilityService.onMotionEvent()` 收到事件。被选中的来源不再发给系统其余部分；回调返回 `void`，不是“修改后放行”接口。若任一服务开启触摸探索（touch exploration），`onMotionEvent()` 不会接收触摸屏事件。
- `FLAG_SEND_MOTION_EVENTS` 是触摸探索的配套标志，用于把已识别、取消或透传手势的运动样本发送给服务。它与 API 34 的通用事件来源监听不是同一个开关。
- `TouchInteractionController` 用于观察和控制触摸屏交互；`dispatchGesture()` 则生成一段新的无障碍注入手势。

### 事件拦截的回调路径

按键过滤可以拆成两个阶段看。

**阶段 1：输入子系统把按键送进无障碍过滤器。**

`InputReader → InputDispatcher → mPolicy.filterInputEvent(...) → AccessibilityInputFilter → KeyboardInterceptor`

这一步发生在 `system_server` 一侧，`InputDispatcher` 只负责把事件交给过滤器。

**阶段 2：无障碍服务异步给出“消费/放行”结果。**

`KeyboardInterceptor → AccessibilityManagerService.notifyKeyEvent() → KeyEventDispatcher.notifyKeyEventLocked() → AccessibilityService.onKeyEvent()`

`KeyEventDispatcher` 会为待判定的按键创建 `PendingKeyEvent`，并启动 500 ms 超时计时。服务稍后通过 `setOnKeyEventResult()` 回传结果：

- 至少一个服务返回“已处理”，且所有服务都已返回或超时后，事件在无障碍层结束；
- 所有服务都返回“未处理”，或未响应服务到达 500 ms 超时后，`KeyEventDispatcher` 把按键送回输入过滤器，再继续分发。

多个服务的等待并行记在同一个待决事件上，不能把 500 ms 乘以服务数量。分析按键延迟时，应看 `AccessibilityManagerService`、`KeyEventDispatcher` 和服务进程自己的处理时间。

### 事件修改的安全限制

无障碍或系统过滤器的修改范围分为三类。

1. **原始硬件事件不能被服务直接原位改写。** 触摸从 `EventHub`、`InputReader` 进入系统后，普通服务拿不到内核事件缓冲。无障碍通常消费原事件，再通过 `MotionEventInjector` 或 `dispatchGesture()` 发出替代手势。
2. **按键判定是“消费还是放行”，不是修改原 `KeyEvent` 再放行。** `AccessibilityService.onKeyEvent()` 给出的只是一个布尔结果。若服务想产生另一组按键，仍然要走注入入口。
3. **`source` 不能拿来判断无障碍注入。** `MotionEvent.getSource()` 和 `KeyEvent.getSource()` 描述设备类别。原生层会把无障碍策略标志转换成 `FLAG_IS_ACCESSIBILITY_EVENT`，但 Android 17 中 `KeyEvent` 与 `MotionEvent` 的这个常量都是 `@TestApi @hide`。系统或测试代码可以使用，普通应用没有受支持的通用注入事件检测 API。`POLICY_FLAG_INJECTED`、`POLICY_FLAG_INJECTED_FROM_ACCESSIBILITY` 也只在系统内部流转。

## 系统级事件注入

### 几种常见事件注入路径

这些入口都会生成注入事件，但调用身份、目标范围和进入过滤器的位置不同。`InputFilter.java` 明确说明：Instrumentation 等普通注入入口产生的事件不再交给全局 InputFilter。只有专用的无障碍过滤器测试入口，或 `dispatchGesture()` 在过滤器变换链内生成的事件，才会经过无障碍过滤器。

#### 1. Instrumentation.sendPointerSync()

`Instrumentation.sendPointerSync()` 在 `ACTION_DOWN` 前和 `ACTION_UP` 后同步窗口事务，然后调用 `InputManagerGlobal.injectInputEvent(..., Process.myUid())`。目标 UID 限制注入只能命中 Instrumentation 测试目标自身拥有的窗口；命中其他 UID 的窗口会失败。

下面的源码摘录用于确认该方法仍通过 `InputManagerGlobal` 注入，并把目标 UID 固定为当前进程 UID。

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

它没有直接写 `ViewRootImpl` 的 InputChannel，底层仍进入 `InputManagerService.injectInputEventToTarget()`。方法使用 `WAIT_FOR_FINISH`，只等待接收方完成事件处理并回传 `FINISHED`，不保证对应界面已经绘制或呈现。

#### 2. UiAutomation.injectInputEvent()

`UiAutomation.injectInputEvent()` 通过受信任的 `UiAutomationConnection` 调用标准 `InputManagerGlobal.injectInputEvent()`，可以跨应用窗口工作。它会按 `ACTION_DOWN`、`ACTION_UP` 边界同步窗口事务，并根据 `sync` 参数选择 `WAIT_FOR_FINISH` 或 `ASYNC`。作为标准注入事件，它不进入 InputFilter。

#### 3. UiAutomation.injectInputEventToInputFilter()

这是标为 `@TestApi` 且已弃用的过滤器测试入口。它通过 `UiAutomationConnection` 调到 `AccessibilityManagerService.injectInputEventToInputFilter()`，直接把事件交给无障碍输入过滤器，不代表普通测试或应用注入路径。

#### 4. adb shell input

Android 17 的 `cmds/input/input.sh` 只转调 `cmd input`；命令逻辑位于 `InputShellCommand`，最终调用 `InputManagerGlobal.injectInputEvent()`。它依赖 shell 身份拥有的注入权限，走标准注入事件路径，不进入 InputFilter。

#### 5. AccessibilityService.dispatchGesture()

`dispatchGesture()` 不使用普通应用的 `INJECT_EVENTS` 入口。服务连接先通过 `canPerformGestures()` 安全检查，再取得对应显示屏的 `MotionEventInjector`。注入器在无障碍变换链中生成 `MotionEvent`，加入内部标志 `FLAG_INJECTED_FROM_ACCESSIBILITY`；若服务声明自己是无障碍工具，还会加入 `FLAG_INJECTED_FROM_ACCESSIBILITY_TOOL`。到达原生分发器后，这些策略标志才会转换成 MotionEvent 内部标志。

下面的源码摘录显示了显示屏选择、安全身份和注入器调用之间的关系。

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

`displayId` 决定事件注入哪块显示屏，`isAccessibilityTool()` 则决定是否附加“来自无障碍工具”的内部标志。几种入口的差异如下：

| 方式 | 进入方式 | 与 InputFilter 的关系 | 目标范围 | 普通应用可用的受支持标记 |
|------|----------|------------------|----------|------------------------|
| `Instrumentation.sendPointerSync()` | 标准注入，目标 UID = `Process.myUid()` | 绕过 | Instrumentation 测试目标的窗口 | 无 |
| `UiAutomation.injectInputEvent()` | 受信任的 UiAutomation 连接下的标准注入 | 绕过 | 可跨应用 | 无 |
| `UiAutomation.injectInputEventToInputFilter()` | 无障碍过滤器专用测试入口 | 直接进入 | 过滤器测试 | 无稳定的公开 API |
| `adb shell input` | `shell` → `InputShellCommand` → 标准注入 | 绕过 | `shell` 权限允许的目标 | 无 |
| `AccessibilityService.dispatchGesture()` | `MotionEventInjector` 在无障碍变换链内生成 | 在过滤器内产生，再以带 `FLAG_FILTERED` 的事件注入 | 指定显示屏上的命中窗口 | 无；系统和测试代码有隐藏的无障碍标志 |

`POLICY_FLAG_INJECTED` 是 InputDispatcher 内部的策略标志，`InputEvent` 基类也没有统一的 `getFlags()`。`MotionEvent.isFromSource()` 只能判断设备来源，不能区分注入事件和硬件事件。

### 注入事件的权限控制

标准注入入口最终都会经过 `InputManagerService.injectInputEventToTarget()` 的权限检查。`android-17.0.0_r1` 调用 `checkCallingPermission(INJECT_EVENTS, ..., checkInstrumentationSource = true)`：先检查直接调用者，再按需检查 Instrumentation 来源 UID。两者都不满足时抛出 `SecurityException`。

`Instrumentation` 和 `UiAutomation` 的可用性来自测试框架建立的受控身份，并不表示普通应用获得全局注入权。`dispatchGesture()` 使用另一套门禁：服务配置元数据需要声明 `canPerformGestures`，连接还要通过无障碍安全策略校验。

## Input 事件的安全边界

### 哪些环节可以被拦截或修改

输入事件从硬件到应用之间，可编程拦截点包括：

| 位置 | 能做什么 | 典型实现 |
|------|----------|----------|
| `InputReader` 与策略层 | 设备级重映射、丢弃、策略判断 | 系统策略、厂商输入定制 |
| `InputFilter` | 放行、消费、发出替代事件 | 自定义系统过滤器、`AccessibilityInputFilter` |
| `AccessibilityInputFilter` 内部变换器 | 按键判定、触摸探索、手势注入 | `KeyboardInterceptor`、`TouchExplorer`、`MotionEventInjector` |
| 应用自己的 `InputStage` 与 `ViewGroup` | 只影响本进程窗口 | `ViewRootImpl`、`onInterceptTouchEvent()` |

普通应用或普通服务无法访问以下位置：

1. **`EventHub → InputReader` 的原始设备事件。** 这是内核输入设备到系统服务的边界。
2. **`InputChannel` 的套接字传输。** 事件进入套接字之后，应用只能从自己那一端读取，不能修改 `system_server` 已经写出的数据包。
3. **`InputDispatcher` 内部策略标志。** 例如 `POLICY_FLAG_INJECTED` 只在分发器里流转，不是公开 API。

这些边界区分了全局过滤器与应用 View 层各自能做的操作。

### 安全策略的版本演进

当前只保留能直接从 AOSP 和官方文档核对到的结论。

| 版本或来源 | 能直接核对到的结论 | 证据 |
|-----------|--------------------|------|
| android-10.0.0_r1 | `canRequestFilterKeyEvents` 配置元数据会转成 `CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`；运行时用 `FLAG_REQUEST_FILTER_KEY_EVENTS` 打开按键过滤 | `AccessibilityServiceInfo.java` |
| API 34 | 新增 `AccessibilityService.onMotionEvent()` 与 `setMotionEventSources()`；被选择的运动事件来源不再继续发给系统其他部分 | Android API 参考文档、`AccessibilityService.java` |
| android-17.0.0_r1 | 按键过滤仍使用配置能力加运行时标志；标准注入事件绕过 InputFilter | `AccessibilityServiceInfo.java`、`InputFilter.java` |
| android-17.0.0_r1 | 无障碍策略标志会转换成事件内部的无障碍标志，但对应 Java 常量是 `@TestApi @hide` | `InputDispatcher.cpp`、`KeyEvent.java`、`MotionEvent.java` |
| API 34—37 | `View.setAccessibilityDataSensitive(...)` 同时约束未标记为无障碍工具的服务对节点的交互、事件数据和注入触摸 | `View.java`、`AccessibilityInteractionController.java` |

### Android 17 基线：从权限控制到查询通道隔离

`accessibilityDataSensitive` 是 API 34 引入的“无障碍数据敏感”属性。Android 17 中，设为 `ACCESSIBILITY_DATA_SENSITIVE_YES` 或被系统自动推断为敏感的 View 会受到多层保护：

- `AccessibilityInteractionController` 不会向未标记为无障碍工具的请求返回该 View 的节点；
- `AccessibilityEvent` 会携带数据敏感属性，由系统按接收服务身份过滤；
- `View#onFilterTouchEventForSecurity()` 会丢弃非无障碍工具服务注入到敏感 View 的触摸；
- 父 View 的敏感状态会传给后代，启用 `filterTouchesWhenObscured` 的 View 默认也会推断为敏感。

这组限制同时作用于无障碍查询通道和 View 触摸安全检查。它不关闭 InputDispatcher，也不表示系统已经停止所有 InputMonitor 副本。

## 事件拦截对性能的影响

### InputFilter 的延迟开销

`InputFilter` 自身带来的延迟主要来自事件复制、Handler 排队、本地变换和带 `FLAG_FILTERED` 事件的重新注入。没有同设备性能跟踪或微基准数据时，不应给出固定毫秒数。

即使过滤器只原样放行，事件也要经过异步 Handler 和一次重新注入；复杂过滤器还会叠加对象分配、手势状态机或跨进程等待。量化时，应在同一设备、同一跟踪配置下比较过滤器关闭、只放行和实际变换三种状态。

### 无障碍服务对事件分发路径的性能影响

无障碍的性能成本要按事件类型分开看。

**按键事件。** 开启 `FLAG_REQUEST_FILTER_KEY_EVENTS` 后，事件会先到 `KeyboardInterceptor`，再交给 `KeyEventDispatcher` 等待服务结果。等待窗口上限是 500 ms。这个等待发生在无障碍子系统维护的 `PendingKeyEvent` 队列里，不是 `InputDispatcher` 同步等待远端 Binder。

**触摸事件。** `TouchExplorer`、放大镜手势处理器、`MotionEventInjector` 可能把一段原始触摸重写成另一串 `MotionEvent`。这会增加事件数量，也会让时序更复杂。TalkBack 的“朗读后双击激活”就是这类变换的典型例子。

**服务进程自身的耗时。** `AccessibilityService.onKeyEvent()` 的 Binder 回调经服务执行器运行；如果执行线程被占用，结果返回就会变慢，待决按键在 `KeyEventDispatcher` 中停留更久。`onAccessibilityEvent()` 中的耗时任务也可能争用同一服务执行资源。

分析时，不能只看 Binder 轨迹区段，还要检查：

- `KeyboardInterceptor`、`KeyEventDispatcher` 是否积压待判定按键；
- 服务进程返回结果是否接近 500 ms 超时；
- `dispatchGesture()` 是否把一次用户动作扩展成更多注入的 `MotionEvent`。

### 性能影响对比表

| 机制 | 额外工作发生位置 | 影响范围 | 当前能直接核对的结论 |
|------|------------------|----------|----------------------|
| 轻量 `InputFilter` | `system_server` 的过滤器回调 | 经过过滤器的按键和运动事件 | 会增加分发前处理时间，幅度取决于过滤器代码 |
| 无障碍按键过滤 | `KeyboardInterceptor`、`KeyEventDispatcher` 与服务进程 | 开启按键过滤的事件 | 单个待决事件的等待上限为 500 ms；无人处理时继续分发 |
| 无障碍手势注入 | `MotionEventInjector` | 目标窗口 | 会额外生成无障碍注入的 `MotionEvent` |
| 应用自己的 `onInterceptTouchEvent()` | 应用进程 | 仅本应用 | 不会回过头影响全局 `InputDispatcher` |

## 厂商定制的拦截增强方案

### 游戏模式中的输入优先级

AOSP 标准游戏模式（GameMode）没有独立的 InputDispatcher 游戏优先队列。Android 17 的 `GameManagerService` 在游戏 UID 进入前台时切换 `PowerManagerInternal.Mode.GAME`；性能模式上报游戏加载状态时，还可以短时切换 `Mode.GAME_LOADING`。游戏模式干预项还包括帧率覆盖（frame-rate override）和降低渲染分辨率（downscale）等图形策略。这些能力可能间接改善输入到显示的延迟，但没有改变焦点窗口选择或 InputChannel 的分发优先级。

如果厂商宣称游戏模式提升“输入优先级”，应分别检查触控报点率、CPU 与线程调度、显示刷新率和 InputDispatcher 队列；不能仅凭 GameMode 开关推导分发器存在加权机制。

### 防误触机制

边缘抑制、口袋模式和手掌拒绝可能由触控固件、内核驱动、InputReader 映射器或系统过滤器实现。AOSP 没有规定统一的边缘宽度、压力阈值或厂商算法。

定位实现层时可以按事件是否存在逐级判断：

1. `getevent -lt` 已经没有对应触点：优先查触控控制器或内核驱动；
2. evdev 有事件、InputReader 输出缺失或发生重分类：查设备配置与映射器；
3. 分发器收到事件、目标窗口没有收到：查系统策略、InputFilter、监视窗口、指针抢占和窗口安全规则；
4. 应用收到完整事件流后自行取消：回到 View 或 Compose 手势逻辑。

## Android 17 基线下仍可核对到的权限边界

`android-17.0.0_r1` 中需要同时记住四类门禁：

1. **全局过滤器**：隐藏系统接口，只能由 WMS 或 IMS 安装；
2. **手势监视器**：调用者必须持有 `MONITOR_INPUT`，其保护级别是 `signature|recents`；
3. **标准注入**：调用者或 Instrumentation 来源必须满足 `INJECT_EVENTS`；
4. **无障碍能力**：按键过滤和手势注入分别受配置能力、运行时标志与 `canPerformGestures()` 控制，敏感 View 还会按 `isAccessibilityTool` 再过滤。

## 在 Perfetto 中分析事件拦截问题

排查这类问题时，需要把事件停留的层次分出来。

### 步骤 1：确认事件有没有进入 InputDispatcher

在 `system_server` 中对齐原生 `filterInputEvent`、InputDispatcher 分发轨迹区段与目标进程的 `deliverInputEvent`：

- 应用完全收不到事件，先确认是否在过滤器或无障碍层被消费；
- 应用能收到事件但时间明显偏晚，再检查 `system_server` 的前置处理和无障碍服务返回结果所需的时间。

### 步骤 2：把 InputFilter 本地处理和无障碍异步判定分开看

自定义 `InputFilter` 的成本分散在“原生层到 Java 层的事件复制”“过滤器 Handler 排队”“带 `FLAG_FILTERED` 事件重新注入”三段。无障碍按键过滤还要确认 `KeyboardInterceptor` → `AccessibilityManagerService` → 服务进程这段是否接近 500 ms 超时。不能用一条 Binder 轨迹区段代替整段时序。

### 步骤 3：检查无障碍服务进程自己的处理时间

查看服务进程的主线程或工作线程：

- `onKeyEvent()` 是否快速返回结果；
- `onAccessibilityEvent()` 是否挤占了主线程；
- `dispatchGesture()` 之后是否又生成了更多注入的 `MotionEvent`。

如果服务回调本身慢，`system_server` 一侧通常表现为待决事件变多，而不是 InputDispatcher 出现一条长时间不动的同步调用。

### 步骤 4：用 dumpsys 补足运行态信息

下面两条命令分别查看输入过滤器状态和无障碍服务运行状态。

```bash
adb shell dumpsys input | grep -E "InputFilterEnabled|Input Dispatcher State"
adb shell dumpsys accessibility
```

`dumpsys input` 中的 `InputFilterEnabled` 直接说明原生分发器是否打开过滤器。`dumpsys accessibility` 可确认已启用服务、配置能力和 `A11yInputFilter Info` 变换链。两者只能说明配置与运行状态；某个事件是否被消费，仍需与性能跟踪对齐。

## 常见问题与误区

### 误区一：应用可以注册自己的 InputFilter

不能。`InputFilter` 由 `WindowManagerService` 和 `InputManagerService` 管理，普通应用没有这条入口，也拿不到全局注入所需的权限。

### 误区二：无障碍按键过滤是 InputDispatcher 同步调用 `onKeyEvent()`

不是。`InputDispatcher` 把事件交给过滤器后，“是否消费”的判定发生在 `AccessibilityManagerService`、`KeyEventDispatcher` 和服务进程这一侧，并带有 500 ms 超时。

### 误区三：触摸无障碍只能“间接操作 UI 树”，不碰 `MotionEvent`

不对。`AccessibilityInputFilter.onInputEvent()` 会直接处理 `MotionEvent`，并按启用功能把事件交给 `TouchExplorer`、放大镜处理器或 `MotionEventInjector`。无障碍并不需要先经过 `AccessibilityInteractionController` 才能影响触摸流。

### 误区四：应用可以用 `InputEvent.getFlags()` 或 `MotionEvent.isFromSource()` 判断注入事件

不对。`InputEvent` 基类没有 `getFlags()`，`source` 只表示设备来源。`KeyEvent.getFlags()` 和 `MotionEvent.getFlags()` 虽然公开，但 `FLAG_IS_ACCESSIBILITY_EVENT` 在 Android 17 是 `@TestApi @hide`；读取硬编码位也不构成稳定的公开 API。普通应用不能可靠地区分所有注入事件与硬件事件。

### 误区五：InputFilter 只影响按键事件

不对。`android-17.0.0_r1` 的 `InputDispatcher` 在 `mInputFilterEnabled` 为真时，会把按键和触摸都送到 `filterInputEvent(...)`。无障碍场景下，`KeyboardInterceptor` 负责按键，`TouchExplorer` 等组件负责触摸，两边都在过滤器这一层工作。

## 参考资料

### AOSP 源码路径

- `frameworks/base/services/core/java/com/android/server/wm/WindowManagerInternal.java`、`WindowManagerService.java` — 隐藏的 `setInputFilter()` 本地服务
- `frameworks/base/services/core/java/com/android/server/input/InputManagerService.java` — `setInputFilter()`、`injectInputEventToTarget()`、`monitorGestureInput()`
- `frameworks/base/services/core/java/com/android/server/input/InputShellCommand.java` — `cmd input` 的标准注入
- `frameworks/base/core/res/AndroidManifest.xml` — `MONITOR_INPUT` 保护级别
- `packages/SystemUI/src/com/android/systemui/navigationbar/gestural/DisplayBackGestureHandler.kt` — `InputMonitorCompat("edge-swipe", displayId)`、`pilferPointers()` 调用
- `packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java` — 返回手势判定后转调 `pilferPointers()`
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — `filterInputEvent()` 调用点、`injectInputEvent()`
- `frameworks/native/services/inputflinger/dispatcher/TouchState.cpp` — 监视与指针抢占后的指针归属
- `frameworks/base/core/java/android/view/InputFilter.java` — `InputFilter` 抽象与 `sendInputEvent()`
- `frameworks/base/core/java/android/view/View.java` — `accessibilityDataSensitive`
- `frameworks/base/core/java/android/view/AccessibilityInteractionController.java` — 敏感 View 的无障碍查询过滤
- `frameworks/base/core/java/android/accessibilityservice/AccessibilityService.java` — `onKeyEvent()`、`onMotionEvent()`、`dispatchGesture()`
- `frameworks/base/core/java/android/accessibilityservice/AccessibilityServiceInfo.java` — `CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`、`FLAG_REQUEST_FILTER_KEY_EVENTS`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityInputFilter.java` — 无障碍过滤器的按键与运动事件入口
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/KeyboardInterceptor.java` — 按键预处理
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java` — `notifyKeyEvent()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/KeyEventDispatcher.java` — `PendingKeyEvent`、500 ms 超时、`setOnKeyEventResult()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityServiceConnection.java` — `dispatchGesture()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/MotionEventInjector.java` — 无障碍手势注入
- `frameworks/base/core/java/android/app/Instrumentation.java` — `sendPointerSync()`
- `frameworks/base/core/java/android/app/UiAutomation.java`、`UiAutomationConnection.java` — 标准注入与过滤器测试入口
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
