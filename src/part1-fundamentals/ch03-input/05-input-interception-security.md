---
status: finalized
title: 输入事件拦截与安全机制
chapter: '3.5'
section: '3.5'
drafted_by: openclaw-task
applicable_versions: Android 10 (API 29) - Android 17 (API 37), InputMonitor 部分基于 android-16.0.0_r1 核验, 密码输入场景的 InputMonitor 切断暂不作为 AOSP 源码结论
confidence: medium
reviewed_date: "2026-06-01"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
pipeline_stage: ready-to-publish
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
review_notes: '2026-04-19 task6 re-review: pass-light-edit. L1小修7处(删除旧稿/编辑痕迹)。无需回炉。 | 2026-05-12 Task6 16:15：写作复审通过；清理 frontmatter 重复字段；Task9 已通过且 queue 无 pending，自动晋升 finalized。'
task2b_result: fixed-lite
task9_result: pass-tech-review
task9_reviewed_date: "2026-06-02"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-02T00:25:54+08:00"
last_task6_at: "2026-06-01T23:07:00+08:00"
last_task6_review_log: "logs/review/2026-06-01-23-review.md"
task6_review_notes: "2026-06-01 23:07 Task6 revisiting-review：L1/L2 小修 1 处；保留既有待补充/待验证边界标注，锚点覆盖完整，未新增 L3/L4 回炉项，送 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-06-02-00-deep-review.md"
task9_review_notes: "2026-06-02 Task9 deep review: pass-tech-review。InputFilter/InputMonitor/Accessibility 注入与 Android 16/17 版本边界复核通过；P0 0 / P1 0 / P2 0，queue 无 pending，自动晋升 finalized。"
last_task9_audit: "2026-05-24"
last_task9_audit_log: "logs/deep-review/2026-05-24-14-audit.md"
last_task2b_lite_at: '2026-06-01'
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_new_rework: false
p0: 0
p1: 0
p2: 0
---

# 输入事件拦截与安全机制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 InputFilter 机制：系统级事件拦截的实现原理、注册流程、性能影响
- 🔹 无障碍服务（AccessibilityService）的事件拦截：onKeyEvent/onTouchEvent 回调、事件流修改能力、安全限制
- 🔹 系统级事件注入：Instrumentation.sendPointerSync、uiautomator、adb shell input 的实现路径
- 🔹 Input 事件的安全边界：哪些环节可以被拦截/修改、哪些环节不可篡改、安全策略的版本演进
- 🔹 事件拦截对性能的影响：InputFilter 的延迟开销、无障碍服务对事件分发路径的性能影响

### 扩展（可选深入）

- 🔸 厂商定制的拦截增强方案（游戏模式中的输入优先级、防误触）
- 🔸 Android 14+ 对无障碍服务事件拦截的权限限制变化

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解输入事件拦截与安全机制

第 3.1 节追踪了一条 Input 事件从硬件到 View 树的完整路径。那条路径描述的是"正常情况"——事件沿着设计好的管道一路传递到目标窗口。现实远比这复杂：系统中存在多种机制可以在事件传递的不同环节进行拦截、过滤甚至注入新事件。

做性能优化时，常见一种诡异卡顿：Perfetto 中 InputDispatcher 的队列状态完全正常，App 主线程也没有阻塞，但用户仍然感觉触摸响应慢。继续排查后发现，系统注册了一个 InputFilter，每个事件在分发前都要经过一层过滤处理，引入了额外延迟。又或者在分析无障碍服务相关的 bug 时，事件在到达 View 树之前就被无障碍服务拦截并修改。看起来像 App 代码问题，根因却在更上层。

理解这些拦截机制的存在、工作原理和安全边界，一方面是为了在性能分析时能够识别"事件去哪了"，另一方面也是为了在做 Framework 定制或安全审计时，清楚系统允许什么、禁止什么。

## InputFilter：系统级事件拦截

### 什么是 InputFilter

InputFilter 是 Android 系统提供的一个**全局事件拦截机制**，允许系统级组件在 InputDispatcher 将事件分发给目标窗口之前，对事件进行拦截、修改或过滤。它工作在 InputDispatcher 内部，是事件分发路径上最早的可编程拦截点。

与 App 层面的事件拦截（如 `ViewGroup.onInterceptTouchEvent()`）不同，InputFilter 是**系统级**的——它拦截的是所有窗口的事件，而不是单个 App 的事件。影响范围覆盖整个系统的输入行为。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.h]

### InputFilter 的注册流程

InputFilter 的入口不在 InputManagerService 自己对外暴露的公开 API，而是 WindowManagerService 通过 IWindowManager.setInputFilter() 把过滤器交给 InputManagerService。`InputManagerService` 保存当前 filter、创建 `InputFilterHost`、调用 `filter.install(mInputFilterHost)`，然后只把一个布尔开关同步到 Native 层。

```java
// frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java
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

这里最容易写错的是 Native 侧的关系。`InputDispatcher` 并不会直接持有 Java 层的 `IInputFilter` 对象，也不会调用 `mInputFilter.filterMotionEvent(args)`。实际做法是，当 `mInputFilterEnabled` 为 `true` 时，`InputDispatcher` 把事件交给 policy 的 `filterInputEvent(...)`，是否继续分发由这个调用的返回值决定。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
if (shouldSendMotionToInputFilterLocked(args)) {
    policyFlags |= POLICY_FLAG_FILTERED;
    if (!mPolicy.filterInputEvent(event, policyFlags)) {
        return; // event was consumed by the filter
    }
}
```

按键事件也是同一套做法，只是入口换成 `shouldSendKeyToInputFilterLocked()`。把这几层放在一起看，比较准确的流程是：

`WindowManagerService.setInputFilter()` → `InputManagerService.setInputFilter()` → `filter.install(...)` → `mNative.setInputFilterEnabled(true)` → `InputDispatcher` 在分发前调用 `mPolicy.filterInputEvent(...)`。

### InputFilter 的事件处理模型

`InputFilter` 的 Java 合同很直接，`onInputEvent(InputEvent event, int policyFlags)` 默认马上调用 `sendInputEvent(event, policyFlags)` 放行。自定义 filter 可以消费事件，也可以构造替代事件再调用 `sendInputEvent()` 重新发布。

这件事更像“拦下原事件，再决定要不要发出另一个事件”，不是在原地改一块共享状态。`InputFilter` 文档也强调了事件一致性，如果 filter 自己重组了一串 `MotionEvent`，它要保证 down/move/up 序列仍然合法，不然下游窗口会收到不成对的事件。

`InputFilter` 运行在 system_server 这一侧。普通 App 只能接收过滤后的结果，不能自己挂一个全局 filter。

### InputFilter 在 Perfetto 中的表现

两类耗时需要分开看。

一类是 filter 本身在 system_server 里的本地处理时间，例如 Java 回调、事件复制、坐标变换、`sendInputEvent()` 重新发布。这部分会直接拉长“事件进入 Input 子系统之后，到达目标窗口之前”的时间。

另一类是无障碍按键判定带来的额外等待。它不是 `InputDispatcher` 线程同步等远端 Binder 返回，而是 `KeyboardInterceptor` 把按键交给 `AccessibilityManagerService`，再由 `KeyEventDispatcher` 异步等服务调用 `setOnKeyEventResult()`。InputDispatcher 并没有同步卡在 Binder 上等远端返回。

当前素材没有对应的真实 trace 截图，本节只保留可从源码核对到的结论。Perfetto 图例暂记为 `[待补充：InputDispatcher、AccessibilityManagerService、无障碍服务进程的时间关系]`。

## InputMonitor：特权组件的旁路监控

### 什么是 InputMonitor

前面讲的 `InputFilter` 是"拦截-决定放行或消费"的模型。Android 还有一套更隐蔽的系统能力——`InputMonitor`，允许特权组件在**不是目标窗口**时监控 `InputEvent` 流。它不做拦截，只拿一份副本。

`InputMonitor` 的注册入口是 `InputManagerService.monitorGestureInput()`，调用方需要持有 `android.permission.MONITOR_INPUT` 权限——这个权限只签发给系统签名应用或 `privileged` 应用。普通 App 和第三方无障碍服务都无法获取。

> [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/input/InputManagerService.java]

### spy window 与 pilferPointers

`InputMonitor` 创建的输入通道在 InputDispatcher 内部被标记为 **spy window**。spy window 的特点是：

1. **收到事件的副本**，不影响正常分发流程。目标窗口的事件不会因为 spy window 的存在而延迟或丢失。
2. **可以 pilfer pointers**。`pilferPointers()` 让 spy window 从目标窗口拿走当前 pointer stream。手势导航模式下，SystemUI 的 `EdgeBackGestureHandler` 创建 `InputMonitorCompat("edge-swipe")` 监听边缘滑动，确认为返回手势后调用 `pilferPointers()` 接管触摸流——原始目标窗口收到 `ACTION_CANCEL`。

> [已验证: AOSP android-16.0.0_r1, packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java]

它在 Perfetto 中的表现为：目标窗口的 touch slice 突然中断（`ACTION_CANCEL`），同时系统 UI 进程开始处理手势。如果分析时发现 App 的触摸流被意外中断，可以检查是否存在系统 spy window 在 pilfer。

### InputMonitor 与 InputFilter 的区别

| 能力 | InputFilter | InputMonitor (spy window) |
|------|-------------|--------------------------|
| 能否消费事件 | 是（filter 返回 false 则事件不再分发） | 否（只拿副本，不影响分发） |
| 能否拿走 pointer stream | 否 | 是（`pilferPointers()`） |
| 能否发出替代事件 | 是（`sendInputEvent()`） | 否（只能读，不能注入） |
| 权限要求 | 系统签名，由 WMS 注册 | `MONITOR_INPUT`，系统签名或 privileged |
| 典型使用方 | `AccessibilityInputFilter`、厂商定制 filter | SystemUI `EdgeBackGestureHandler`（手势导航返回）、系统 UI 手势识别 |

三类输入旁路能力的边界：

1. **旁路监控副本**（InputMonitor / spy window）：只读，不改变事件流。用于系统手势检测、导航手势识别。
2. **拿走 pointer stream**（`pilferPointers()`）：把当前 pointer stream 从目标窗口转移到 spy window。用于系统导航手势接管。
3. **消费 / 重发事件**（InputFilter）：拦截原始事件，决定放行、消费或发出替代事件。用于全局输入策略和无障碍变换。

## 无障碍服务的事件拦截

### AccessibilityService 与 Input 事件的关系

无障碍和 Input 的交叉点主要在 `AccessibilityInputFilter`。系统在服务能力和 flags 满足条件时启用它，然后把按键处理交给 `KeyboardInterceptor`，把触摸相关变换交给 `TouchExplorer`、放大镜手势处理器或 `MotionEventInjector`。

按键过滤的前提不是在 `android:accessibilityEventTypes` 里写一个 flag。真实约束分成两步：

1. 服务 metadata 中声明 `android:canRequestFilterKeyEvents="true"`，系统据此赋予 `AccessibilityServiceInfo.CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`
2. 服务运行时把 `AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS` 放进 `AccessibilityServiceInfo.flags`

android-10.0.0_r1 和 android-14.0.0_r1 都是这套做法，所以“Android 10+ 只有系统无障碍服务能用这个 flag”这句话不能保留。

触摸事件的情况也不能简单写成“无障碍通过 UI 树间接操作”。`AccessibilityInputFilter.onInputEvent()` 会直接收到 `MotionEvent`，按启用的功能把事件交给 `TouchExplorer`、放大镜相关 handler，或 `MotionEventInjector`。无障碍服务主动产生手势时，再通过 `dispatchGesture()` 走另一条注入流程。

### 事件拦截的回调路径

按键过滤可以拆成两个阶段看。

**阶段 1：Input 子系统把按键送进 accessibility filter。**

`InputReader → InputDispatcher → mPolicy.filterInputEvent(...) → AccessibilityInputFilter → KeyboardInterceptor`

这一步发生在 system_server 一侧，`InputDispatcher` 只负责把事件交给 filter。

**阶段 2：无障碍服务异步给出“消费/放行”结果。**

`KeyboardInterceptor → AccessibilityManagerService.notifyKeyEvent() → KeyEventDispatcher.notifyKeyEventLocked() → AccessibilityService.onKeyEvent()`

`KeyEventDispatcher` 会为待判定的按键建一个 `PendingKeyEvent`，并启动 500ms 超时计时。服务稍后通过 `setOnKeyEventResult()` 回传结果：

- 服务返回 handled，事件在无障碍层结束，不再发给 App
- 服务返回 unhandled，或 500ms 内没有回结果，`KeyEventDispatcher` 把原始按键重新送回 input filter，再继续分发给目标窗口

分析按键延迟时，应该看 `AccessibilityManagerService`、`KeyEventDispatcher` 和服务进程自己的处理时间，而不是假定 `InputDispatcher` 一直堵着不动。

### 事件修改的安全限制

无障碍或系统 filter 的“可改”范围，最好按三件事来理解。

1. **原始硬件事件不能被服务直接原位改写。** 触摸从 `EventHub/InputReader` 进入系统后，普通服务拿不到那份内核事件缓冲。无障碍更常见的做法是消费原事件，再通过 `MotionEventInjector` 或 `dispatchGesture()` 发出替代手势。
2. **按键判定是“消费还是放行”，不是修改原 `KeyEvent` 再放行。** `AccessibilityService.onKeyEvent()` 给出的只是一个布尔结果。若服务想产生另一组按键，仍然要走注入入口。
3. **`source` 不能拿来判断无障碍注入。** `MotionEvent.getSource()` / `KeyEvent.getSource()` 描述的是设备类别。App 侧能直接看到的标记是 `KeyEvent.FLAG_IS_ACCESSIBILITY_EVENT` 和 `MotionEvent.FLAG_IS_ACCESSIBILITY_EVENT`。`POLICY_FLAG_INJECTED`、`POLICY_FLAG_INJECTED_FROM_ACCESSIBILITY` 属于 InputDispatcher 内部 policy flag，不是 public API。

## 系统级事件注入

### 几种常见事件注入路径

这些入口都叫“注入事件”，但它们进入系统的地方并不一样。把它们混成一类，后面就会把可观测性和权限边界全写乱。

#### 1. Instrumentation.sendPointerSync()

`Instrumentation.sendPointerSync()` 会做一次 window transaction 同步，然后调用 `InputManagerGlobal.getInstance().injectInputEvent(..., Process.myUid())`。AOSP 注释写得很直白，它只会把事件定向到 instrumentation target 自己拥有的窗口，不会像 `UiAutomation` 那样跨 App。

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

它并没有直接写 `ViewRootImpl` 输入通道，底层仍然走 Input 注入入口。

#### 2. UiAutomation.injectInputEvent()

`UiAutomation.injectInputEvent()` 通过 `mUiAutomationConnection.injectInputEvent(...)` 进入标准注入流程，可以跨应用窗口工作。`UiAutomation.java` 里还写了一个例外，标准 `injectInputEvent()` 会跳过 accessibility input filter，目的是避免 feedback loop。

#### 3. UiAutomation.injectInputEventToInputFilter()

这是测试 accessibility input filter 的专用入口。名字已经说明了它的去向，事件不是走普通注入流程，而是直接送进 accessibility input filter。

#### 4. adb shell input

`adb shell input` 最终仍会落到 `InputManager.injectInputEvent()` / `InputManagerService.injectInputEventToTarget()` / `mNative.injectInputEvent(...)` 这一套标准注入入口。它和 `UiAutomation.injectInputEvent()` 一样，属于普通 injected event，不是 accessibility input filter 专用入口。

#### 5. AccessibilityService.dispatchGesture()

`dispatchGesture()` 不是普通 `INJECT_EVENTS` 权限入口。服务调用它之后，`AccessibilityServiceConnection.dispatchGesture()` 会拿到对应 display 的 `MotionEventInjector`，再由 `MotionEventInjector.injectEvents()` 生成一串 `MotionEvent`。这一类事件会带上 `FLAG_INJECTED_FROM_ACCESSIBILITY`，App 侧能看到对应的 `FLAG_IS_ACCESSIBILITY_EVENT`。

```java
// frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityServiceConnection.java
public void dispatchGesture(int sequence, ParceledListSlice gestureSteps, int displayId) {
    ...
    MotionEventInjector motionEventInjector =
            mSystemSupport.getMotionEventInjectorForDisplayLocked(displayId);
    ...
    motionEventInjector.injectEvents(gestureSteps.getList(), mServiceInterface, sequence, displayId);
}
```

几种入口的差异如下：

| 方式 | 最终入口 | 是否经过 accessibility input filter | 目标范围 | App 侧可直接看到的标记 |
|------|----------|--------------------------------------|----------|------------------------|
| `Instrumentation.sendPointerSync()` | `InputManagerGlobal.injectInputEvent(..., Process.myUid())` | 否 | instrumentation target 自己的窗口 | 无专门 injected public flag |
| `UiAutomation.injectInputEvent()` | `mUiAutomationConnection.injectInputEvent(...)` | 否 | 跨应用窗口 | 无专门 injected public flag |
| `UiAutomation.injectInputEventToInputFilter()` | accessibility input filter 测试入口 | 是 | filter 测试场景 | 取决于 filter 是否以 accessibility 方式再发布 |
| `adb shell input` | `InputManagerService.injectInputEventToTarget()` | 否 | shell 可达的标准注入目标 | 无专门 injected public flag |
| `AccessibilityService.dispatchGesture()` | `MotionEventInjector.injectEvents()` | 是 | 目标显示与目标窗口 | `FLAG_IS_ACCESSIBILITY_EVENT` |

注意一个常见错误：`POLICY_FLAG_INJECTED` 只是 InputDispatcher 内部 policy flag。普通 App 没有 `InputEvent.getFlags()` 这个统一入口去读它，也不能靠 `MotionEvent.isFromSource()` 把 injected event 和真实硬件事件区分开。

### 注入事件的权限控制

普通注入入口最终都会过 `InputManagerService.injectInputEventToTarget()` 的权限检查。android-14.0.0_r1 里，这一步调用 `checkCallingPermission(android.Manifest.permission.INJECT_EVENTS, "injectInputEvent()", true)`，没有 `INJECT_EVENTS` 的调用者会抛 `SecurityException`。

`Instrumentation` 和 `UiAutomation` 看上去像“绕过了权限”，实际不是。它们用的是系统帮测试框架建立的受控通道，最终仍然落回受权限保护的注入接口。`dispatchGesture()` 又是另一套门禁，它看的是无障碍服务是否通过 `canPerformGestures()` 校验，而不是 `INJECT_EVENTS`。

## Input 事件的安全边界

### 哪些环节可以被拦截/修改

Input 事件从硬件到 App 之间，可编程拦截点按源码可以落到这几处：

| 位置 | 能做什么 | 典型实现 |
|------|----------|----------|
| `InputReader` / policy | 设备级重映射、丢弃、策略判断 | 系统 policy、厂商输入定制 |
| `InputFilter` | 放行、消费、发出替代事件 | 自定义系统 filter、`AccessibilityInputFilter` |
| `AccessibilityInputFilter` 内部变换器 | 按键判定、触摸探索、手势注入 | `KeyboardInterceptor`、`TouchExplorer`、`MotionEventInjector` |
| App 自己的 `InputStage` / `ViewGroup` | 只影响本进程窗口 | `ViewRootImpl`、`onInterceptTouchEvent()` |

普通 App 或普通服务碰不到这几处：

1. **`EventHub → InputReader` 的原始设备事件。** 这是内核输入设备到系统服务的边界。
2. **`InputChannel` 的 socket 传输。** 事件进入 socket 之后，App 只能从自己那一端读，不能改 system_server 已经写出的包。
3. **InputDispatcher 内部 policy flag。** 例如 `POLICY_FLAG_INJECTED` 只在分发器里流转，不是 public API。

把这些边界分清之后，就不容易把“全局 filter 可做什么”和“App 自己在 View 层能做什么”混在一起。

### 安全策略的版本演进

当前只保留能直接从 AOSP 和官方文档核对到的结论。

| 版本/来源 | 能直接核对到的结论 | 证据 |
|-----------|--------------------|------|
| android-10.0.0_r1 | `canRequestFilterKeyEvents` metadata 会转成 `CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`；运行时用 `FLAG_REQUEST_FILTER_KEY_EVENTS` 打开按键过滤 | `AccessibilityServiceInfo.java` |
| android-14.0.0_r1 | 按键过滤仍是 capability + 运行时 flag 这套机制，不存在“只有系统无障碍服务可用该 flag”的 AOSP 依据 | `AccessibilityServiceInfo.java` |
| android-14.0.0_r1 | 标准 `UiAutomation.injectInputEvent()` 会跳过 accessibility input filter；测试 filter 需要 `injectInputEventToInputFilter()` | `UiAutomation.java` |
| android-14.0.0_r1 | accessibility 注入事件会在 InputDispatcher 中转成 `FLAG_IS_ACCESSIBILITY_EVENT` 供 App 识别 | `InputDispatcher.cpp`、`KeyEvent.java`、`MotionEvent.java` |
| android-14.0.0_r1 (API 34) | `View.setAccessibilityDataSensitive(ACCESSIBILITY_DATA_SENSITIVE_YES)` 可标记敏感 View；非 `isAccessibilityTool` 的无障碍服务对该 View 的 accessibility interaction 会被限制。这限制的是 `AccessibilityInteractionClient` 的查询/操作通道，不是 InputDispatcher 的原始事件拦截 | `View.java`、`AccessibilityServiceInfo.isAccessibilityTool()` |
| android-16.0.0_r1 (API 36) | `accessibilityDataSensitive` 执行力度加强：标记后的 View 对非 `isAccessibilityTool` 无障碍服务完全不可见，`AccessibilityInteractionClient` 查询返回空，服务拿不到 View 坐标和尺寸，无法通过 `dispatchGesture()` 构造精准触摸注入 | `View.java`、`AccessibilityInteractionClient.java` |
| 待验证（未进入 Android 17 正文结论） | 密码输入场景限制非系统级 InputMonitor 副本分发的说法缺少可复核 `android-17.0.0_r1` / source anchor，当前不作为 AOSP 结论 | 待补公开 tag、Beta commit 或官方源码锚点 |
| Android in-call protections rollout | 通话期间阻塞无障碍授权、首次侧载等高风险安全动作属于 Settings / PermissionController / 安全策略 rollout，不能归因到 InputDispatcher 或 `android-17.0.0_r1` | Google Security Blog / Android 安全策略资料 |

以下结论因缺乏一手证据暂不收录：
- `MotionEvent.isFromSource()` 可检测 injected event
- Android 14 需要 `R.string.accessibility_filter_key_events` 资源声明
- Android 10 只有系统无障碍服务能使用 `FLAG_REQUEST_FILTER_KEY_EVENTS`

等补到 tag + 文件或官方文档之后，再恢复版本表。

### Android 16/17：从权限控制到物理隔离

表格末尾几项需要单独说明。

**Android 16：敏感视图隔离加强执行力度。** `accessibilityDataSensitive` 在 API 34 引入，Android 16 提升了执行力度。标记后的 View 对非 `isAccessibilityTool` 无障碍服务完全不可见——`AccessibilityInteractionClient` 查询返回空，服务拿不到 View 的坐标和尺寸。没有位置信息，`dispatchGesture()` 就无法构造精准的触摸注入。这层防御做在无障碍查询通道上，不经过 InputDispatcher 的事件拦截链。

**密码输入时的 InputMonitor 副本限制：待验证。** 公开可核验的 `android-16.0.0_r1` `InputDispatcher.cpp` 能支撑 spy window / monitor / `pilferPointers()` 的通用机制，但不能支撑“密码输入期间暂停所有非系统级 InputMonitor 副本分发”的 Android 17 AOSP 结论。该说法在补到公开 tag、Beta commit 或官方源码锚点前，只作为待验证线索保留。

**通话中的权限授予封锁。** Google 2025 安全资料支撑的是 in-call protections：通话期间阻止关闭 Play Protect、首次侧载、授予无障碍权限等高风险安全动作。它属于 Settings / PermissionController / 安全策略 rollout，不在 InputDispatcher 的管辖范围，也不能写成 `android-17.0.0_r1` 的源码结论。

[来源: external-review 2026-04-28-ch03-05-input-interception-security]

## 事件拦截对性能的影响

### InputFilter 的延迟开销

`InputFilter` 自身带来的延迟主要来自三件事，filter Java 回调、本地变换逻辑、重新发布事件。这里没有现成 trace 数据支持“0.1ms”“2ms”这样的固定数值，因此本节不做量化对比。

如果 filter 只是做轻量判断，然后马上 `sendInputEvent()`，额外开销通常很小。若 filter 在回调里做对象分配、复杂手势状态机、跨线程切换，分发前置时间就会拉长。这个时间发生在 system_server 侧，不是 App 主线程自己造成的。

[待补充：同设备 Perfetto 或 microbenchmark，量化空 filter / 复杂 filter 的差值]

### 无障碍服务对事件分发路径的性能影响

无障碍的性能成本要按事件类型分开看。

**按键事件。** 开启 `FLAG_REQUEST_FILTER_KEY_EVENTS` 后，事件会先到 `KeyboardInterceptor`，再交给 `KeyEventDispatcher` 等待服务结果。等待窗口上限是 500ms。这个等待发生在无障碍子系统维护的 `PendingKeyEvent` 队列里，不是 `InputDispatcher` 同步等远端 Binder。

**触摸事件。** `TouchExplorer`、放大镜手势处理器、`MotionEventInjector` 可能把一段原始触摸重写成另一串 `MotionEvent`。这会增加事件数量，也会让时序更复杂。TalkBack 的“朗读后双击激活”就是这类变换的典型例子。

**服务进程自己的耗时。** `AccessibilityService.onKeyEvent()`、`onAccessibilityEvent()`、手势回调如果在主线程里做重活，结果返回就会变慢，待决按键在 `KeyEventDispatcher` 里停留更久。

分析时，不要只盯着“有没有一条 Binder slice 很长”，更该看的是：
- `KeyboardInterceptor` / `KeyEventDispatcher` 是否积压待判定按键
- 服务进程回结果是否接近 500ms 超时
- `dispatchGesture()` 是否把一次用户动作扩成了更多 injected `MotionEvent`

### 性能影响对比表

| 机制 | 额外工作发生位置 | 影响范围 | 当前能直接核对的结论 |
|------|------------------|----------|----------------------|
| 轻量 `InputFilter` | system_server filter 回调 | 经过 filter 的 key / motion | 会增加分发前处理时间，幅度取决于 filter 代码 |
| 无障碍按键过滤 | `KeyboardInterceptor` + `KeyEventDispatcher` + 服务进程 | 开启 key filter 的按键 | 等待窗口上限 500ms；超时后事件继续发给 App |
| 无障碍手势注入 | `MotionEventInjector` | 目标窗口 | 会额外生成 accessibility injected `MotionEvent` |
| App 自己的 `onInterceptTouchEvent()` | App 进程 | 仅本 App | 不会回过头影响全局 `InputDispatcher` |

## 厂商定制的拦截增强方案

### 游戏模式中的输入优先级

AOSP 标准 GameMode 没有公开的“游戏输入优先级提升”路径。可从 AOSP 核对到的能力是功耗 HAL 档位、刷新率策略和焦点窗口分发；把游戏窗口放进独立 InputDispatcher 优先队列、为 InputChannel 加权、或提高触控 IC 采样率，都属于厂商私有实现或硬件/内核层策略，不能写成 Android 通用结论。

分析厂商游戏模式时，优先把结论限定为“非 AOSP 扩展”：如果 trace 中看到触摸延迟下降，只能结合 CPU 调度、触控驱动日志、焦点窗口变化和厂商开关状态交叉判断，不能单凭 GameMode 开启推导出 InputDispatcher 存在额外优先级。

### 防误触机制

防误触也是厂商常见的 Input 定制方向。常见方案包括：

1. **边缘防误触**：在屏幕边缘区域（通常 10-20px 宽度）降低触摸灵敏度或直接忽略触摸事件。实现方式是在 InputReader 的 `TouchInputMapper` 中增加边缘区域判断逻辑
2. **口袋防误触**：通过距离传感器检测手机是否在口袋中，如果是则忽略触摸事件
3. **手掌防误触**：通过触摸面积和压力判断是否为手掌误触（面积大、压力低），如果是则忽略

这些方案的实现位置各有不同——有的在内核驱动层处理（直接不上报事件），有的在 InputReader 层处理（加工后丢弃），有的在 InputDispatcher 层通过 InputFilter 过滤。

> [待验证: 各厂商防误触实现的具体位置和方案差异]

## Android 14 时代仍可核对到的权限边界

关于 Android 14+ 权限限制变化，当前只保留能从 AOSP 或官方文档直接核对的边界。android-14.0.0_r1 里，至少有三条可以直接核对：

1. **按键过滤仍然依赖 capability + 运行时 flag。** 代码位置在 `AccessibilityServiceInfo.java`，不是某个 `R.string.*` 资源开关。
2. **手势注入要过无障碍安全检查。** `AccessibilityServiceConnection.dispatchGesture()` 会先看 `mSecurityPolicy.canPerformGestures(this)`，拿到 `MotionEventInjector` 之后才会发事件。
3. **标准 injected event 和 accessibility injected event 是两回事。** 前者走普通注入入口，后者会在 `MotionEventInjector` / `InputDispatcher` 里补上 accessibility 标记。

如果后续补到 Android 15/16 的一手材料，再单独写版本增量会更稳。没有证据的“14+ 白名单限制变化”描述不放入正文。

## 在 Perfetto 中分析事件拦截问题

排查这类问题时，需要把事件停留的层次分出来。

### Step 1：确认事件有没有进入 InputDispatcher

在 `system_server` 里看 InputDispatcher 相关线程和目标 App 的 `deliverInputEvent` / `InputEventReceiver` 节奏。

- App 完全收不到事件，先确认是不是在 filter 或无障碍层被消费了
- App 能收到事件，但时间明显晚，再看 system_server 前置处理和无障碍服务回结果时间

### Step 2：把 InputFilter 本地处理和无障碍异步判定分开看

如果是自定义 `InputFilter` 做了重处理，延迟会体现在 system_server 这一侧的前置工作里。  
如果是无障碍按键过滤，不要把排查目标锁死在“InputDispatcher 卡 Binder”上。实际更该确认的是 `KeyboardInterceptor` → `AccessibilityManagerService` → 服务进程这一段有没有积压，以及是否接近 500ms 超时。

[待补充：对应 trace 截图，标出 InputDispatcher、AccessibilityManagerService、服务进程主线程]

### Step 3：检查无障碍服务进程自己的处理时间

看服务进程主线程或工作线程上：
- `onKeyEvent()` 是否快速回结果
- `onAccessibilityEvent()` 是否挤占了主线程
- `dispatchGesture()` 之后是否又生成了更多 injected `MotionEvent`

如果服务回调本身慢，system_server 那边看到的通常是待决事件变多，不是 InputDispatcher 一条长时间静止的同步调用。

### Step 4：用 dumpsys 补足运行态信息

```bash
adb shell dumpsys input | grep -A 20 "Input Filter"
adb shell dumpsys accessibility
```

`dumpsys input` 适合确认当前是否启用了 input filter。  
`dumpsys accessibility` 更适合确认哪些服务处于启用状态、是否声明了相关 capability，以及当前是不是存在会影响输入的 accessibility 组件。

## 常见问题与误区

### 误区一：App 可以注册自己的 InputFilter

不能。`InputFilter` 由 `WindowManagerService` / `InputManagerService` 管理，普通 App 没有这条入口，也拿不到全局注入所需的权限。

### 误区二：无障碍按键过滤是 InputDispatcher 同步调 `onKeyEvent()`

不是。`InputDispatcher` 把事件交给 filter 之后，“是否消费”的判定发生在 `AccessibilityManagerService` / `KeyEventDispatcher` / 服务进程这一侧，并带 500ms 超时。

### 误区三：触摸无障碍只能“间接操作 UI 树”，不碰 MotionEvent

不对。`AccessibilityInputFilter.onInputEvent()` 会直接处理 `MotionEvent`，并按启用功能把事件交给 `TouchExplorer`、放大镜处理器或 `MotionEventInjector`。无障碍并不需要先经过 `AccessibilityInteractionController` 才能影响触摸流。

### 误区四：App 可以用 `InputEvent.getFlags()` 或 `MotionEvent.isFromSource()` 判断 injected event

不对。`InputEvent` 基类没有 `getFlags()`。`source` 表示设备来源，不等于 injected 标记。对 App 来说，能直接看到的是 `KeyEvent.getFlags()` / `MotionEvent.getFlags()` 暴露出来的 public flag，其中和无障碍最相关的是 `FLAG_IS_ACCESSIBILITY_EVENT`。

### 误区五：InputFilter 只影响按键事件

不对。android-14.0.0_r1 的 `InputDispatcher` 在 `mInputFilterEnabled` 为真时，会把按键和触摸都送去 `filterInputEvent(...)`。无障碍场景下，`KeyboardInterceptor` 负责按键，`TouchExplorer` 等组件负责触摸，两边都在 filter 这一层工作。

## 参考资料

### AOSP 源码路径

- `frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java` — `setInputFilter()`
- `frameworks/base/services/core/java/com/android/server/input/InputManagerService.java` — `setInputFilter()`、`injectInputEventToTarget()`、`monitorGestureInput()`
- `packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java` — `InputMonitorCompat("edge-swipe")`、`pilferPointers()` 调用
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — `filterInputEvent()` 调用点、`injectInputEvent()`
- `frameworks/base/core/java/android/view/InputFilter.java` — `InputFilter` 抽象与 `sendInputEvent()`
- `frameworks/base/core/java/android/accessibilityservice/AccessibilityServiceInfo.java` — `CAPABILITY_CAN_REQUEST_FILTER_KEY_EVENTS`、`FLAG_REQUEST_FILTER_KEY_EVENTS`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityInputFilter.java` — 无障碍 filter 的 key / motion 入口
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/KeyboardInterceptor.java` — 按键预处理
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java` — `notifyKeyEvent()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/KeyEventDispatcher.java` — `PendingKeyEvent`、500ms 超时、`setOnKeyEventResult()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityServiceConnection.java` — `dispatchGesture()`
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/MotionEventInjector.java` — accessibility 手势注入
- `frameworks/base/core/java/android/app/Instrumentation.java` — `sendPointerSync()`
- `frameworks/base/core/java/android/app/UiAutomation.java` — 标准注入与 `injectInputEventToInputFilter()`
- `frameworks/base/core/java/android/hardware/input/InputManagerGlobal.java` — `injectInputEvent()`

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


## 扩展：厂商游戏模式输入优先级机制（源码级验证）

> **调研时间**：2026-05-12 | **调研引擎**：AutoResearchClaw | **源码版本**：android-15.0.0_r1

### 核心结论

**AOSP 标准 GameMode 框架不包含独立的输入优先级提升机制。**

Android 标准 GameMode（GameManagerService + GameServiceController）的核心能力：
1. **帧率策略控制**：`RefreshRatePolicy` 通过 `LAYER_PRIORITY_*` 影响 SurfaceFlinger 刷新率决策
2. **功耗模式切换**：`PowerManager.setMode(Mode.GAME, true)` 调整 CPU/GPU 功耗档位
3. **GameService API**：GameSession/GameServiceProvider 接口用于 OEM 游戏工具集成

### 关键源码发现

#### 1. GameManagerService：不包含输入优先级逻辑

```java
// services/core/java/com/android/server/app/GameManagerService.java
if (gameMode == GameMode.GAME_MODE_PERFORMANCE) {
    mPowerManagerInternal.setMode(Mode.GAME, true);  // 只影响功耗档位
} else {
    mPowerManagerInternal.setMode(Mode.GAME, false);
}
```

`GAME_MODE_PERFORMANCE` 激活的是功耗 HAL 档位，不涉及输入事件分发优先级。

#### 2. 帧率优先级机制（非输入分发优先级）

```java
// services/core/java/com/android/server/wm/RefreshRatePolicy.java
static final int LAYER_PRIORITY_FOCUSED_WITH_MODE = 0;   // 最高
static final int LAYER_PRIORITY_FOCUSED_WITHOUT_MODE = 1;
static final int LAYER_PRIORITY_NOT_FOCUSED_WITH_MODE = 2;
```

这是**渲染优先级**机制（通知 SurfaceFlinger 哪个窗口的刷新率请求更重要），不是**输入分发优先级**机制。

#### 3. DISALLOW_INTERCEPT：View 层触摸完整性保证

```java
// core/java/android/view/ViewGroup.java, line 3225
public void requestDisallowInterceptTouchEvent(boolean disallowIntercept) {
    if (disallowIntercept) {
        mGroupFlags |= FLAG_DISALLOW_INTERCEPT;
    }
    // 传递给父容器
    if (mParent != null) {
        mParent.requestDisallowInterceptTouchEvent(disallowIntercept);
    }
}
```

游戏等需要完整触摸序列的场景可以调用此方法防止父容器拦截事件，这是 View 层设计，AOSP 无系统级输入优先级机制。

#### 4. 焦点窗口：输入分发的唯一标准机制

Android 中输入事件分发给焦点窗口（focused window），焦点窗口的确定在 WindowManagerService 层：

```java
// services/core/java/com/android/server/wm/WindowManagerService.java, line 1882
boolean focusChanged = updateFocusedWindowLocked(UPDATE_FOCUS_WILL_ASSIGN_LAYERS, false);
```

**游戏窗口获得焦点后自然优先收到输入事件，但这不涉及独立的"游戏模式输入优先级"机制。**

### 结论

§3.5 中关于"厂商游戏模式输入优先级"的描述：
- "游戏模式中输入优先级提升机制"如果指的是独立于焦点之外的机制，属于**厂商定制范畴**，AOSP 无公开源码支撑
- 游戏窗口的"输入优先级"对应的是**焦点窗口机制**
- 游戏模式下触摸响应优化依赖：**帧率优先级** + **HAL Game 档位** + **DISALLOW_INTERCEPT**

**调研结论**：AOSP 标准 GameMode 框架中不存在独立的"游戏输入优先级提升"机制。厂商实现此功能依赖非公开修改或专有 Framework 扩展。

---

<!-- AIW-源码调研-2026-05-12 -->
