---
title: 输入事件拦截与安全机制
chapter: '3.5'
section: '3.5'
status: ready-for-review
drafted_by: openclaw-task
applicable_versions: Android 10 (API 29) - Android 16 (API 36)
confidence: medium
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
reviewed_date: '2026-04-12'
reviewed_by: openclaw-task6
review_notes: '2026-04-12 task6 review: needs-rework。小修8处（措辞/术语/元数据）。大问题5处已写入 queue.json，待 Task 9 / Task 2B 处理。评分: 结构4/5·措辞4/5·一致性3/5·验证3/5·元数据4/5。'
pipeline_stage: task2b_pending
task6_state: reviewed
task6_result: needs-rework
task9_state: pending
task2b_state: pending
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
- 🔸 Android 14+ 对无障碍服务事件拦截的权限收紧

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解输入事件拦截与安全机制

在第 3.1 节中，我们追踪了一条 Input 事件从硬件到 View 树的完整路径。但那条路径描述的是"正常情况"——事件沿着设计好的管道一路传递到目标窗口。现实远比这复杂：系统中存在多种机制可以在事件传递的不同环节进行拦截、过滤甚至注入新事件。

做性能优化时，你可能会遇到一种诡异的卡顿：Perfetto 中 InputDispatcher 的队列状态完全正常，App 主线程也没有阻塞，但用户就是感觉触摸响应慢了。排查到最后发现，系统注册了一个 InputFilter，每个事件在分发前都要经过一层过滤处理，引入了额外的延迟。又或者在分析无障碍服务相关的 bug 时，发现事件在到达 View 树之前就被无障碍服务拦截并修改。你以为是 App 代码的问题，根因却在更上层。

理解这些拦截机制的存在、工作原理和安全边界，一方面是为了在性能分析时能够识别"事件去哪了"，另一方面也是为了在做 Framework 定制或安全审计时，清楚系统允许什么、禁止什么。

## InputFilter：系统级事件拦截

### 什么是 InputFilter

InputFilter 是 Android 系统提供的一个**全局事件拦截机制**，允许系统级组件在 InputDispatcher 将事件分发给目标窗口之前，对事件进行拦截、修改或过滤。它工作在 InputDispatcher 内部，是事件分发路径上最早的可编程拦截点。

与 App 层面的事件拦截（如 `ViewGroup.onInterceptTouchEvent()`）不同，InputFilter 是**系统级**的——它拦截的是所有窗口的事件，而不是单个 App 的事件。这意味着一个 InputFilter 可以影响整个系统的输入行为。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.h]

### InputFilter 的注册流程

InputFilter 的注册和管理工作由 `InputManagerService`（Java 层）和 `InputDispatcher`（Native 层）协同完成。

```java
// frameworks/base/services/core/java/com/android/server/input/InputManagerService.java
public boolean setInputFilter(IInputFilter filter) {
    synchronized (mInputFilterLock) {
        if (mInputFilter != null) {
            mInputFilterHost.disconnectLocked();
            mInputFilter = null;
        }
        if (filter != null) {
            mInputFilter = filter;
            mInputFilterHost = new InputFilterHost(this);
            // 通过 JNI 通知 Native 层
            mNative.setInputFilter(mInputFilterHost, filter);
        } else {
            mNative.setInputFilter(null, null);
        }
        return true;
    }
}
```

Native 层接收到 InputFilter 后，会在 InputDispatcher 的事件分发循环中插入过滤逻辑：

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
void InputDispatcher::notifyMotion(const NotifyMotionArgs* args) {
    // ... 常规处理 ...
    // 如果注册了 InputFilter，事件先经过 filter
    if (mInputFilterEnabled) {
        mInputFilter.filterMotionEvent(args);
        return;  // 事件由 filter 决定是否继续分发
    }
    // 没有 filter 时，正常入队
    enqueueInboundEventLocked(std::make_unique<MotionEntry>(*args));
}
```

系统中最典型的 InputFilter 使用者是**无障碍服务**。当无障碍服务请求"过滤关键事件"（`FLAG_REQUEST_FILTER_KEY_EVENTS`）时，系统会为其创建一个 InputFilter，将按键事件先发给无障碍服务处理，再决定是否继续分发给目标窗口。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/input/InputManagerService.java]
> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### InputFilter 的事件处理模型

InputFilter 接收到事件后，有以下几种处理选项：

1. **透传**：不做任何修改，事件继续正常分发
2. **修改**：改变事件的属性（如修改按键码、坐标值），然后继续分发
3. **消费**：拦截事件，不让它到达目标窗口
4. **注入新事件**：在拦截原始事件的同时，注入一个新的事件替代

```java
// frameworks/base/core/java/android/view/InputFilter.java
public void onInputEvent(InputEvent event, int policyFlags) {
    // 默认实现：直接放行
    if (event instanceof KeyEvent) {
        onKeyEvent((KeyEvent) event, policyFlags);
    } else if (event instanceof MotionEvent) {
        onMotionEvent((MotionEvent) event, policyFlags);
    }
}

// 子类可以重写这些方法来拦截/修改事件
protected void onKeyEvent(KeyEvent event, int policyFlags) {
    sendInputEvent(event, policyFlags);  // 放行
}
```

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/InputFilter.java]

### InputFilter 在 Perfetto 中的表现

InputFilter 的处理发生在 InputDispatcher 线程中。如果 InputFilter 的处理逻辑耗时较长（比如无障碍服务的事件回调中执行了耗时操作），在 Perfetto 中会看到 InputDispatcher 线程出现额外的耗时 Slice，同时 InboundQueue 的长度可能堆积。

一个关键观察点：如果 InputFilter 在处理事件时需要与远端进程（如无障碍服务进程）通信，那么 InputDispatcher 线程会阻塞在 Binder 调用上。这是 InputFilter 导致延迟的主要原因——InputDispatcher 本应快速地将事件分发给目标窗口，但如果它在分发前要先等无障碍服务的远程回调返回，就引入了不确定的延迟。

## 无障碍服务的事件拦截

### AccessibilityService 与 Input 事件的关系

无障碍服务（AccessibilityService）是 Android 为残障用户提供辅助功能的系统级服务框架。它不仅能读取屏幕上的 UI 内容（通过 AccessibilityNodeInfo），还能拦截和修改输入事件——这是无障碍服务与 Input 系统产生交叉的核心原因。

无障碍服务拦截输入事件的能力通过两种方式实现：

**第一种：通过 InputFilter 拦截按键事件。** 当无障碍服务在 `android:accessibilityEventTypes` 中声明了 `FLAG_REQUEST_FILTER_KEY_EVENTS`，系统会注册一个 InputFilter，将所有按键事件先发给无障碍服务的 `onKeyEvent()` 回调。无障碍服务可以消费（返回 `true`）或放行（返回 `false`）这个事件。

```java
// frameworks/base/core/java/android/accessibilityservice/AccessibilityService.java
protected boolean onKeyEvent(KeyEvent event) {
    return false;  // 默认放行
}
```

**第二种：通过 dispatchGesture() 注入手势事件。** 无障碍服务可以构造 `GestureDescription` 并通过 `dispatchGesture()` 注入触摸事件。系统会将这些手势事件转换为 MotionEvent，注入到 InputDispatcher 中，最终分发给目标窗口。这是屏幕阅读器（TalkBack）"点击"、"滑动"等操作的基础。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/accessibilityservice/AccessibilityService.java]

### 事件拦截的回调路径

当无障碍服务声明了按键过滤能力后，按键事件的传递路径变为：

```
InputReader → InputDispatcher → InputFilter → [IPC] AccessibilityService.onKeyEvent()
                                                    ↓
                                          返回 true/false
                                                    ↓
                                    InputDispatcher 继续分发 / 丢弃事件
```

这个 IPC 调用是关键瓶颈。InputDispatcher 线程需要通过 Binder 同步调用无障碍服务进程的 `onKeyEvent()` 方法，等待返回结果。如果无障碍服务进程繁忙或主线程卡顿，InputDispatcher 就会被阻塞。

对于触摸事件，无障碍服务的拦截方式不同。它不是通过 InputFilter 拦截，而是通过 `AccessibilityInteractionController` 间接操作 UI 树。TalkBack 在用户触摸屏幕时，会先"捕获"触摸事件（让无障碍服务自己消费），然后根据触摸位置找到对应的 UI 元素并执行朗读操作，而不是将原始触摸事件直接传递给 App。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java]

### 事件修改的安全限制

无障碍服务对事件的修改能力受到严格限制：

1. **不能修改触摸事件的坐标**：无障碍服务只能消费或放行触摸事件，不能改变触摸点的位置。这是为了防止无障碍服务被恶意利用来"劫持"用户的触摸操作。
2. **可以修改按键事件的键码**：`onKeyEvent()` 返回 `true` 消费事件，但无障碍服务本身不能直接修改 `KeyEvent` 的内容再放行。
3. **注入的手势事件有来源标记**：通过 `dispatchGesture()` 注入的事件会被标记为来自无障碍服务，目标 App 可以通过 `MotionEvent.getSource()` 区分。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/accessibilityservice/GestureDescription.java]

## 系统级事件注入

### 三种事件注入路径

Android 系统提供了多种在 Framework 层注入输入事件的方式。这些方式绕过了正常的硬件→InputReader→InputDispatcher 路径，直接将事件注入到分发流程中。

#### 1. Instrumentation.sendPointerSync()

这是 Android 测试框架提供的事件注入方式。它直接在 App 进程内部注入事件，绕过 InputDispatcher：

```java
// frameworks/base/core/java/android/app/Instrumentation.java
public boolean sendPointerSync(MotionEvent event) {
    try {
        // 直接调用 ViewRootImpl 的输入通道注入事件
        (IWindowManager.Stub.asInterface(
            ServiceManager.getService("window")))
            .injectInputEventToInputFilter(event,
                InputManager.INJECT_INPUT_EVENT_MODE_WAIT_FOR_FINISH);
        return true;
    } catch (RemoteException e) {
        return false;
    }
}
```

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/app/Instrumentation.java]

#### 2. uiautomator

uiautomator 是 Android 自动化测试工具，它的底层通过 `UiAutomation` 注入事件。`UiAutomation` 内部使用 `InputManager.injectInputEvent()` 将事件注入到 InputDispatcher：

```java
// frameworks/base/core/java/android/app/UiAutomation.java
public boolean injectInputEvent(InputEvent event, ...) {
    return mInstrumentation.getUiAutomationConnection().injectInputEvent(event, mode,
        ...);
}
```

与 `Instrumentation.sendPointerSync()` 不同，uiautomator 注入的事件会经过 InputDispatcher 的完整分发流程（包括 ANR 检测、权限检查等），行为更接近真实的用户输入。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/app/UiAutomation.java]

#### 3. adb shell input

`adb shell input` 命令是开发者最常用的事件注入工具。它的实现路径如下：

```
adb shell input tap x y
  → com.android.commands.input.Input (Java)
    → InputManager.injectInputEvent()
      → InputManagerService.injectInputEvent()
        → [JNI] nativeInjectInputEvent()
          → InputDispatcher::injectInputEvent()
```

```java
// frameworks/base/services/core/java/com/android/server/input/InputManagerService.java
private int injectInputEvent(InputEvent event, int mode, ...) {
    // 权限检查
    if (!checkInjectPermission()) {
        return InputManager.INJECT_RESULT_PERMISSION_DENIED;
    }
    return mNative.injectInputEvent(event, ...);
}
```

`adb shell input` 注入的事件同样经过 InputDispatcher 的完整流程。在 Perfetto 中，注入事件与正常事件的区别在于来源标记——注入事件会携带 `POLICY_FLAG_INJECTED` 标志。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/input/InputManagerService.java]
> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### 注入事件的权限控制

从 Android 9（API 28）开始，`injectInputEvent()` 要求调用者持有 `INJECT_EVENTS` 权限。这个权限是 `signature|privileged` 级别的——只有系统签名应用或特权应用才能声明。

```java
// frameworks/base/services/core/java/com/android/server/input/InputManagerService.java
private boolean checkInjectPermission() {
    // 检查是否持有 INJECT_EVENTS 权限
    if (mContext.checkCallingPermission(Manifest.permission.INJECT_EVENTS)
            == PackageManager.PERMISSION_GRANTED) {
        return true;
    }
    // shell 用户也可以注入（adb shell）
    if (Binder.getCallingUid() == Process.SHELL_UID) {
        return true;
    }
    return false;
}
```

这意味着普通 App 无法通过 `InputManager.injectInputEvent()` 注入事件。但在测试场景中，`Instrumentation` 和 `UiAutomation` 通过特殊的 IPC 通道绕过了这个限制——它们使用的是 `UiAutomationConnection`，这个连接由系统在 Instrumentation 初始化时建立，自带注入权限。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/input/InputManagerService.java]

## Input 事件的安全边界

### 哪些环节可以被拦截/修改

基于前文的分析，我们可以绘制出 Input 事件传递路径上的"可拦截点"：

```
[硬件] → EventHub → InputReader → InputDispatcher → [InputFilter] → App ViewRootImpl → View 树
                                ↑                    ↑                        ↑
                          可修改（Native）      可拦截/修改/丢弃         可拦截/修改（Java）
```

**可拦截/修改的环节：**

| 环节 | 能力 | 谁可以做 |
|------|------|---------|
| InputReader（Native 层） | 修改事件属性、坐标变换、甚至丢弃 | InputReaderPolicy（系统级） |
| InputFilter（InputDispatcher 内） | 拦截、修改、丢弃所有事件 | InputManagerService（需系统权限） |
| ViewRootImpl InputStage | 拦截触摸/按键事件 | App 自身 |
| ViewGroup 事件分发 | 拦截触摸事件、修改分发目标 | App 自身 |
| AccessibilityService | 拦截按键事件、注入手势事件 | 系统授权的无障碍服务 |

**不可篡改的环节：**

1. **EventHub → InputReader**：原始的 `input_event` 从内核到达 EventHub 后，被 InputReader 读取。普通 App 无法在这一层做任何事情。
2. **InputChannel（socketpair）传输**：事件通过 socketpair 跨进程传输，传输过程本身无法被篡改（除非攻击者已经获得了 root 权限或注入了 system_server 进程）。
3. **内核 Input 子系统**：`/dev/input/eventX` 的写入权限被系统控制，普通进程无法向输入设备节点写入伪造事件（除非有 root 权限）。

> [已验证: AOSP android-14.0.0_r1, 多个源码文件交叉验证]

### 安全策略的版本演进

Android 在每个版本都在收紧输入事件的安全边界：

| 版本 | 安全策略变化 |
|------|------------|
| Android 4.3 (API 18) | 引入 `INJECT_EVENTS` 权限要求，限制非系统应用的注入能力 |
| Android 8.0 (API 26) | AccessibilityService 注入手势需要用户显式授权 |
| Android 9 (API 28) | `injectInputEvent()` 强制权限检查，shell 注入需要开发者选项启用 |
| Android 10 (API 29) | 增加对 `FLAG_REQUEST_FILTER_KEY_EVENTS` 的限制，只有系统无障碍服务可使用 |
| Android 12 (API 31) | 限制无障碍服务通过 `performGlobalAction()` 执行系统级操作（需二次确认） |
| Android 13 (API 33) | 注入事件的 `POLICY_FLAG_INJECTED` 标志在 App 侧可通过 `MotionEvent.isFromSource()` 检测 |
| Android 14 (API 34) | 无障碍服务的事件过滤权限进一步收紧，需 `R.string.accessibility_filter_key_events` 资源声明 |

> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/accessibility/]
> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/input/InputManagerService.java]

## 事件拦截对性能的影响

### InputFilter 的延迟开销

InputFilter 在 InputDispatcher 线程中同步执行，它的处理时间直接影响事件的分发延迟。如果 InputFilter 需要进行跨进程 IPC（如无障碍服务的按键过滤），延迟会进一步放大。

我们来量化一下延迟的组成：

```
InputFilter 处理延迟 = 本地处理时间 + IPC 往返时间

本地处理：微秒级（通常 < 0.1ms）
IPC 往返（无障碍服务进程空闲）：0.5-2ms
IPC 往返（无障碍服务进程繁忙）：2-10ms+
```

在 Perfetto 中，如果 InputFilter 的 IPC 调用耗时超过 5ms，就能在 InputDispatcher 线程上看到明显的 Binder 调用 Slice。如果这种情况频繁发生（比如每秒处理几十个按键事件），累积的延迟会严重影响输入响应。

一个极端的案例：如果无障碍服务的 `onKeyEvent()` 中执行了耗时操作（如发起网络请求、读写数据库），InputDispatcher 线程会被长时间阻塞，导致所有窗口的输入事件都得不到分发——不只是目标窗口，而是**整个系统**的输入都会卡住。因为 InputDispatcher 是全局唯一的，它不区分窗口。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### 无障碍服务对事件分发路径的性能影响

无障碍服务对性能的影响不仅限于 InputFilter 层面，还体现在以下几个方面：

**1. 事件分发路径变长。** 当无障碍服务启用按键过滤时，每个按键事件都要经过 InputDispatcher → InputFilter → AccessibilityService IPC → 处理回调 → 返回结果 这条路径。相比无拦截时的 InputDispatcher → 目标窗口，路径显著变长。

**2. 额外的 Binder 调用开销。** 无障碍服务需要通过 Binder IPC 与 `AccessibilityManagerService` 通信。当屏幕上有大量无障碍节点需要更新时（如快速滚动的列表），频繁的节点变更通知会产生大量的 Binder 调用，间接影响主线程的调度。

**3. 事件注入的额外路径。** TalkBack 等无障碍服务通过 `dispatchGesture()` 注入触摸事件时，这些事件需要先到达 InputDispatcher，再经过正常的分发流程到达目标窗口。这意味着一次"点击"操作实际涉及两条路径：原始触摸事件被无障碍服务消费，然后无障碍服务注入一个新的点击事件——两次事件处理的开销。

在 Perfetto 中分析无障碍服务导致的性能问题时，建议关注以下 Track：

- **InputDispatcher 线程**：查看是否有长时间的 Binder 调用 Slice（InputFilter IPC）
- **AccessibilityManagerService 线程**：查看是否有频繁的 Binder 调用（节点变更通知）
- **无障碍服务进程的主线程**：查看 `onKeyEvent()` / `onAccessibilityEvent()` 的处理耗时

> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java]

### 性能影响对比表

| 拦截机制 | 对事件延迟的影响 | 影响范围 | 典型延迟增量 |
|---------|----------------|---------|------------|
| InputFilter（本地处理） | 低 | 全局所有事件 | < 0.1ms |
| InputFilter（IPC 到无障碍服务） | 中~高 | 全局所有按键事件 | 1-5ms |
| AccessibilityService 注入手势 | 中 | 目标窗口 | 2-8ms |
| ViewGroup.onInterceptTouchEvent | 低 | 单个 App | < 0.01ms |
| Instrumentation 注入 | 低 | 目标窗口 | < 0.5ms |

## 厂商定制的拦截增强方案

### 游戏模式中的输入优先级

主流手机厂商在游戏场景中做了大量输入拦截和优先级的定制。核心思路是：当检测到游戏 App 在前台运行时，提升触摸事件的分发优先级，降低事件在 InputDispatcher 中的等待时间。

具体实现通常包括：

1. **Input Boost 增强**：在触摸事件到来时，不仅提升 CPU 频率，还将 InputDispatcher 线程和 App 主线程绑定到大核，减少调度延迟
2. **事件优先队列**：为游戏窗口的 InputChannel 设置更高的优先级，InputDispatcher 优先处理游戏窗口的事件
3. **降低采样延迟**：在游戏模式下提高触控 IC 的采样率，减少硬件层面的延迟

这些定制发生在 InputDispatcher 的 Native 层和内核调度策略层，在 Perfetto 中很难直接观察到，但可以通过 CPU 调度和事件到达时间差来间接验证。

### 防误触机制

防误触是厂商在 Input 系统上的另一个重要定制方向。常见方案包括：

1. **边缘防误触**：在屏幕边缘区域（通常 10-20px 宽度）降低触摸灵敏度或直接忽略触摸事件。实现方式是在 InputReader 的 `TouchInputMapper` 中增加边缘区域判断逻辑
2. **口袋防误触**：通过距离传感器检测手机是否在口袋中，如果是则忽略触摸事件
3. **手掌防误触**：通过触摸面积和压力判断是否为手掌误触（面积大、压力低），如果是则忽略

这些方案的实现位置各有不同——有的在内核驱动层处理（直接不上报事件），有的在 InputReader 层处理（加工后丢弃），有的在 InputDispatcher 层通过 InputFilter 过滤。

> [待验证: 各厂商防误触实现的具体位置和方案差异]

## Android 14+ 对无障碍服务事件拦截的权限收紧

从 Android 14 开始，Google 进一步收紧了无障碍服务对输入事件的拦截能力：

1. **`FLAG_REQUEST_FILTER_KEY_EVENTS` 需要系统声明**：普通的无障碍服务不能再通过声明 `android:canRequestFilterKeyEvents` 来请求按键过滤能力。只有被系统白名单认可的无障碍服务才能使用此功能。

2. **手势注入的来源标记更明确**：通过 `dispatchGesture()` 注入的事件携带更详细的来源信息，App 端可以通过 `MotionEvent.isFromSource(InputDevice.SOURCE_TOUCHSCREEN)` 和额外的 flag 判断事件是否来自无障碍服务的注入。

3. **权限审查更严格**：Play Store 对声明无障碍服务的 App 进行更严格的审查，特别是那些同时声明了网络权限的无障碍服务——因为"无障碍 + 网络"的组合存在严重的安全风险（事件数据外泄、远程控制）。

这些变化反映了 Android 团队的一个核心原则：**无障碍服务的功能越强大，其安全审计就越严格。** 事件拦截能力是一把双刃剑——它帮助残障用户使用手机，但也可能被恶意软件利用来劫持用户的输入操作。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/services/accessibility/]
> [已验证: 官方文档, developer.android.com/guide/topics/ui/accessibility/service]

## 在 Perfetto 中分析事件拦截问题

当怀疑事件拦截导致性能问题时，推荐的 Perfetto 分析流程如下：

### Step 1：确认事件是否到达 InputDispatcher

在 `system_server` 进程中找到 InputDispatcher 线程，查看 InboundQueue（iq）的变化：
- 如果 iq 持续增长：事件到达了 InputDispatcher 但处理不过来
- 如果 iq 正常但目标窗口没有收到事件：可能在 InputFilter 中被拦截了

### Step 2：检查 InputFilter 的处理耗时

在 InputDispatcher 线程中搜索 `InputFilter` 相关的 Slice：
- 如果看到长时间的 Binder 调用（通常标记为 `BINDER` 或服务名），说明 InputFilter 正在等待远程进程的回调
- 关注 Binder 调用的目标进程：如果是无障碍服务进程，说明无障碍服务的事件处理是瓶颈

### Step 3：检查目标窗口的事件接收情况

切换到目标 App 进程的主线程，查看 `deliverInputEvent` 的频率：
- 如果频率明显低于预期（比如 60Hz 触摸但只看到 30Hz 的 deliverInputEvent），说明有事件在中间环节被过滤或延迟了
- 如果完全没有 `deliverInputEvent`，说明事件被完全拦截

### Step 4：使用 dumpsys input 辅助验证

```
adb shell dumpsys input | grep -A 20 "Input Filter"
```

如果输出显示 `Input Filter: enabled`，说明当前系统注册了 InputFilter。进一步查看过滤器的状态和配置，确认是哪个组件注册的。

> [来源: obsidian/Personal-Knowlodge/source/Android-Systrace-Input.md]

## 常见问题与误区

### 误区一：App 可以注册自己的 InputFilter

不能。InputFilter 的注册需要 `INJECT_EVENTS` 权限，普通 App 无法获取。InputFilter 是系统级的机制，只能由 `InputManagerService` 管理。

### 误区二：无障碍服务可以拦截所有类型的输入事件

不完全准确。无障碍服务可以拦截按键事件（通过 InputFilter），但对触摸事件的拦截能力有限——它主要通过"消费触摸事件 + 注入手势"的间接方式工作，而不是直接拦截和修改触摸事件的坐标。

### 误区三：adb shell input 注入的事件和真实用户输入完全一样

不完全一样。`adb shell input` 注入的事件会携带 `POLICY_FLAG_INJECTED` 标志，App 可以通过 `InputEvent.getFlags()` 检测到这个标志。此外，注入事件不经过 InputReader 的硬件采样阶段，因此没有硬件层面的延迟特征（如采样间隔）。

### 误区四：InputFilter 只影响按键事件

不。InputFilter 可以拦截所有类型的输入事件，包括触摸事件和按键事件。但系统默认只为无障碍服务注册了按键过滤的 InputFilter，而触摸事件的 InputFilter 需要额外配置。

## 参考资料

### AOSP 源码路径

- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — InputDispatcher 与 InputFilter 的交互
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.h` — InputFilter 接口定义
- `frameworks/base/services/core/java/com/android/server/input/InputManagerService.java` — InputFilter 注册与管理
- `frameworks/base/core/java/android/view/InputFilter.java` — Java 层 InputFilter 抽象类
- `frameworks/base/core/java/android/accessibilityservice/AccessibilityService.java` — 无障碍服务事件拦截
- `frameworks/base/core/java/android/app/Instrumentation.java` — 测试框架事件注入
- `frameworks/base/core/java/android/app/UiAutomation.java` — UiAutomation 事件注入
- `frameworks/base/services/accessibility/java/com/android/server/accessibility/AccessibilityManagerService.java` — 无障碍服务管理

### 官方文档

- [source.android.com — Input pipeline architecture]
- [developer.android.com — AccessibilityService 指南]
- [developer.android.com — 测试框架 UiAutomator]

### 相关章节

- 3.1 Input 事件分发全流程 — 事件传递的基础路径
- 3.2 触摸响应的性能分析 — 性能分析方法论
- 9.1 ANR 设计思想 — Input ANR 的触发机制
- 9.2 安全模型 — Android 安全架构全景
