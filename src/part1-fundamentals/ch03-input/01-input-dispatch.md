---
title: "Input 事件分发全流程"
chapter: "3.1"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 16 (API 36)"
last_verified: "2026-04-10"
last_verified_against: "AOSP android-14.0.0_r1"
version_note: "正文以 android-14 验证为主；Android 12 InputFlinger 分离和 Android 13 ANR Tracker 变更基于官方文档和社区素材，标注 [待验证]。建议后续补充 android-12/13 源码级验证"
confidence: high
reviewed_date: "2026-04-07"
reviewed_by: openclaw-task6
rework2_date: "2026-04-10"
rework2_by: "openclaw-task2b"
rework2_reason: "Task9 Deep Tech Review: applicable_versions 补充版本验证说明; DEFAULT_INPUT_DISPATCHING_TIMEOUT_NANOS 经 web search 验证确在 WMS.java(Task9误报); §9.2 交叉引用经查实存在(Task9误报)"
polish_count: 1
polish_date: "2026-04-05"
polish_by: "task2b-polish"
sources:
  - type: blog
    path: "https://utzcoz.github.io/2020/05/06/Analyze-AOSP-input-architecture.html"
  - type: blog
    path: "https://kernel.meizu.com/2023/10/27/Android-inputTuning-and-Optimizing/"
  - type: official
    path: "https://source.android.com/docs/core/interaction/input"
  - type: blog
    path: "https://mp.weixin.qq.com/s/Analyze-AOSP-input-architecture"
tags: ['input', 'inputdispatcher', 'inputreader', 'eventhub', 'inputchannel', 'anr', 'inputflinger', 'socketpair', 'touch', 'view-hierarchy']
related_chapters: ["3.2", "3.3", "2.5", "9.1", "9.2"]
reviewed_by: openclaw-task6
reviewed_date: "2026-04-15"
task6_result: pass-light-edit
pipeline_stage: task9_pending
task6_state: reviewed
task9_state: pending
task9_state: pending
task2b_state: idle
---

# Input 事件分发全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 输入事件完整链路：硬件 → Kernel InputDriver → EventHub → InputReader → InputDispatcher → App ViewRootImpl → View 树
- 🔹 InputDispatcher 的分发策略：焦点窗口、触摸窗口、ANR 超时
- 🔹 App 侧的事件分发：ViewRootImpl → DecorView → Activity.dispatchTouchEvent → ViewGroup → View
- 🔹 InputChannel 与 Socket pair 机制
- 🔹 关键超时参数：5s ANR for Key, 5s for Touch (Android 不同版本变化)

### 扩展（可选深入）

- 🔸 InputFlinger 的角色与演进
- 🔸 输入事件在 Systrace 中的完整追踪：deliverInputEvent → input event latency
- 🔸 Pointer Event 与 Motion Event 的区别

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Input 事件分发

当我们在 Perfetto 中追踪一次点击卡顿或滑动不跟手的问题时，最常看到的线索之一就是 `deliverInputEvent` 这个 Trace tag——它对应的就是 App 侧 UI 线程被 Input 事件唤醒并开始处理的那段时间。如果我们不理解 Input 事件是怎么从硬件一路走到这个 tag 的，就无法判断问题出在哪个环节：是底层报点延迟？是 InputDispatcher 分发不及时？还是 App 主线程本身卡住了？

理解 Input 事件分发的完整路径，就是为了在分析这类问题时，能够在 Perfetto 的每一个关键 Track 上精确定位：事件在哪个环节被延迟了，延迟了多少，以及为什么。

## 从硬件到 App：一条完整的事件传递路径

一次触摸事件从手指触碰屏幕到 App 开始处理，要经历一条很长的路径。我们可以把这条路径分成四段来看：

[图：Input 事件分发全路径架构图——从触控 IC 到 App View 树]

**第一段：硬件 → Linux 内核**。触摸屏的触控 IC 芯片捕获电压/电流变化，计算出触摸坐标，通过 I²C 总线通知 CPU。Linux 内核的 Input 子系统按照统一的协议规范，将原始事件写入 `/dev/input/eventX` 设备文件。这一段对 Android Framework 来说是透明的，我们用 `adb shell getevent` 命令看到的就是这一层的原始数据。

**第二段：EventHub → InputReader**。这是 Android Framework 层的第一道关卡。`EventHub` 利用 Linux 的 `epoll` 机制监听 `/dev/input/` 目录下的设备文件，当有新事件时可读取。`InputReader` 是一个跑在 `system_server` 进程中的 Native 循环线程，它不断从 `EventHub` 读取原始的 `struct input_event`，然后根据设备类型（触摸屏、键盘、鼠标等）交给对应的 `InputMapper` 做"加工"（cook）——把原始数据转成 Android 层认识的 `KeyEvent`、`MotionEvent`。

**第三段：InputDispatcher → 目标窗口**。`InputReader` 加工完事件后，交给同样跑在 `system_server` 中的 `InputDispatcher` 线程。`InputDispatcher` 负责找到该事件的目标窗口（焦点窗口或触摸区域命中的窗口），然后通过 `InputChannel`（底层是 `socketpair`）跨进程把事件发送给 App。

**第四段：App 侧分发**。App 进程通过 `WindowInputEventReceiver` 收到事件，经过 `ViewRootImpl` 的责任链式 `InputStage` 管线处理，最终分发到 View 树中的具体控件。

整个过程涉及两个进程（`system_server` 和 App）、四个关键组件（`EventHub`、`InputReader`、`InputDispatcher`、`ViewRootImpl`），以及一个跨进程通信机制（`InputChannel`/`socketpair`）。我们接下来逐一拆解。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/]
> [已验证: 官方文档, source.android.com — Input pipeline architecture]

## EventHub：事件入口的哨兵

`EventHub` 是整个 Input 系统的入口。它的核心工作是监听 `/dev/input/` 目录下设备文件的变化，并对外提供 `getEvents()` 接口。

```cpp
// frameworks/native/services/inputflinger/reader/EventHub.cpp
EventHub::EventHub(void) {
    mEpollFd = epoll_create(EPOLL_SIZE_HINT);  // 创建 epoll 实例
    mINotifyFd = inotify_init();                // 监听设备插拔
    // ...
}

size_t EventHub::getEvents(int timeoutMillis, RawEvent* buffer, size_t bufferSize) {
    for (;;) {
        int pollResult = epoll_wait(mEpollFd, mPendingEventItems,
                                    EPOLL_MAX_EVENTS, timeoutMillis);
        // 读取设备文件中的事件，封装为 RawEvent
        // 如果没有事件，epoll_wait 会阻塞
    }
}
```

这里有两个值得注意的机制：

**第一，`epoll` 机制**。`EventHub` 不是轮询，而是利用 Linux 的 `epoll` 在设备文件有数据可读时才被唤醒。这意味着在没有事件的时候，`InputReader` 线程会安静地休眠，不会消耗 CPU。

**第二，`inotify` 机制**。`EventHub` 同时监听 `/dev/input/` 目录本身的变化——当有新设备插入或拔出时（比如蓝牙键盘连接），`inotify` 会产生一个事件，`EventHub` 就能感知到并执行设备打开/关闭操作。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/reader/EventHub.cpp]

## InputReader：从原始数据到 Android 事件

`InputReader` 的职责不仅是"读"，更重要的是"加工"（cook）。它把内核上报的原始 `struct input_event` 转换成 Android Framework 能理解的 `KeyEvent`、`MotionEvent` 对象。

```cpp
// frameworks/native/services/inputflinger/reader/InputReader.cpp
void InputReader::loopOnce() {
    size_t count = mEventHub->getEvents(timeoutMillis, mEventBuffer, EVENT_BUFFER_SIZE);
    if (count) {
        processEventsLocked(mEventBuffer, count);  // 解析并加工事件
    }
    // ... 配置刷新处理
}
```

`InputReader` 为每种输入设备类型分配了对应的 `InputMapper`：

- 触摸屏设备 → `MultiTouchInputMapper`（继承自 `TouchInputMapper`）
- 键盘设备 → `KeyboardInputMapper`
- 鼠标/轨迹球设备 → `CursorInputMapper`

以触摸事件为例，`TouchInputMapper` 会将多点触控的原始坐标数据加工为包含坐标、压力、触摸点数量等完整信息的 `NotifyMotionArgs`，然后通过 `InputDispatcher::notifyMotion()` 提交给分发队列。

一个容易忽略的细节：开发者选项中的 "Show taps"（显示触摸操作）功能，就是在 `InputReader` 这一层处理的，而不是在 App 层。`TouchInputMapper` 在加工触摸事件时，如果检测到 `showTouches` 配置开启，会通过 `PointerController` 直接在系统层绘制触摸圆点。这样做的好处是响应更快、不占用 App 进程资源。这也是为什么即使 App 卡住了，我们依然能看到触摸圆点在动。

> [来源: obsidian/Cubox/从显示 Tap 原理一探 Android 12 的 Input 系统-2022-03-21.md]
> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/reader/]

## InputDispatcher 的分发策略

`InputDispatcher` 是整个事件分发流程中策略最复杂的组件。它要解决的核心问题是：**给定一个输入事件，应该把它发送给哪个窗口？**

### 焦点窗口 vs 触摸窗口

`InputDispatcher` 对不同类型的事件采用不同的目标窗口查找策略：

**KeyEvent（按键事件）** 走焦点窗口路径。`InputDispatcher` 通过 `findFocusedWindowTargetsLocked()` 查找当前拥有焦点的窗口，将按键事件发送给它。焦点窗口由 `WindowManagerService` 通过 `InputMonitor` 设置到 `InputDispatcher` 中。

**MotionEvent（触摸事件）** 走触摸区域命中路径。`InputDispatcher` 通过 `findTouchedWindowTargetsLocked()` 遍历所有窗口，找到触摸点坐标落在其 `touchableRegion` 内的那个窗口。窗口的 `touchableRegion` 来自 `WindowState.getTouchableRegion()`，由 WMS 管理。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
bool InputDispatcher::dispatchMotionLocked(nsecs_t currentTime,
        std::shared_ptr<MotionEntry> entry, DropReason* dropReason, nsecs_t* nextWakeupTime) {
    // ...
    if (isPointerEvent) {
        // 触摸事件：按触摸区域查找
        injectionResult = findTouchedWindowTargetsLocked(currentTime, *entry,
            inputTargets, nextWakeupTime, &conflictingPointerActions);
    } else {
        // 非触摸事件（如轨迹球）：按焦点窗口查找
        injectionResult = findFocusedWindowTargetsLocked(currentTime, *entry,
            inputTargets, nextWakeupTime);
    }
    // ...
    dispatchEventLocked(currentTime, entry, inputTargets);
}
```

这里有一个重要的设计决策：为什么触摸事件不用焦点窗口？因为触摸事件的天然语义就是"点到谁就给谁"。如果用户点了一个悬浮窗下方的按钮，应该由悬浮窗接收事件（因为它在上面），而不是焦点窗口。而按键事件没有空间信息，只能用焦点窗口来决定接收者。

### 三大队列：iq / oq / wq

在 Perfetto 中追踪 Input 问题时，我们经常看到三个计数器 Track：`iq`、`oq`、`wq`。它们对应 `InputDispatcher` 内部的三个关键队列：

**InboundQueue（iq）**：`InputReader` 加工完的事件首先进入这个队列。`InputDispatcher` 的主循环从这个队列取出事件进行分发。在 Perfetto 中通过 `ATRACE_INT("iq", mInboundQueue.size())` 追踪。

**OutboundQueue（oq）**：每个窗口连接（`Connection`）都有一个独立的 `outboundQueue`，存放即将通过 `InputChannel` 发送给该窗口的事件。事件从 `iq` 取出后，找到目标窗口，放入对应窗口的 `oq`。在 Perfetto 中格式为 `oq:{windowName}`。

**WaitQueue（wq）**：事件通过 `socketpair` 发送给 App 后，从 `oq` 移到 `wq`，等待 App 处理完毕的反馈。收到 App 的 `FINISHED` 回调后，事件从 `wq` 移除。在 Perfetto 中格式为 `wq:{windowName}`。

这三个队列的生命周期反映了一个事件在 `InputDispatcher` 中的完整旅程：

```
iq（等待分发）→ oq（准备发送）→ wq（等待 App 反馈）→ 移除
```

如果我们在 Perfetto 中看到 `wq` 的值持续增长不下降，说明 App 没有及时处理 Input 事件——这是 Input ANR 的前兆。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### 按键拦截：PhoneWindowManager 的特殊角色

在按键事件到达目标窗口之前，还有一个拦截环节。`InputDispatcher` 在分发按键事件时，会先询问 `PhoneWindowManager`（通过 `InputDispatcherPolicyInterface`）是否要拦截这个按键。

```cpp
// 拦截决策的入口
nsecs_t delay = mPolicy->interceptKeyBeforeDispatching(
    commandEntry->inputWindowHandle, &event, entry->policyFlags);
```

如果 `PhoneWindowManager.interceptKeyBeforeDispatching()` 返回 -1，表示这个按键被系统消费了，`InputDispatcher` 会丢弃该事件。像 `ALT+TAB`（最近任务）、电源键、音量键等系统级按键，都是在这里被拦截处理的。

这也解释了一个常见的困惑：为什么有些按键事件在 App 的 `dispatchKeyEvent` 里收不到？因为它们已经被 `PhoneWindowManager` 在分发前拦截了。

> [来源: obsidian/Cubox/Analyze AOSP input architecture - Blog-2024-06-17.md]

## InputChannel 与 Socket Pair：跨进程的事件管道

`InputDispatcher` 运行在 `system_server` 进程，而目标窗口运行在 App 进程，两者之间的通信靠的是 `InputChannel`，底层实现是 Linux 的 `socketpair()`。

### 为什么用 socketpair 而不是 Binder？

这是面试中常被问到的问题。`InputDispatcher` 选择 `socketpair` 而非 `Binder` 有三个关键原因：

**第一，事件排队能力**。`InputDispatcher` 需要跟踪每个事件是否已被 App 处理完成（`FINISHED` 回调），`socketpair` 天然支持这种"发送-等待确认"的模式。事件发送后留在 `waitQueue` 中，只有收到 App 的 `FINISHED` 消息才移除。而 `Binder` 是同步调用模型，不适合这种异步确认场景。

**第二，窗口区分**。一个 App 进程可能有多个窗口（如 `Dialog`、悬浮窗等），每个窗口需要独立的 `InputChannel`。通过 `socketpair`，一个进程可以创建多对 socket 来标识不同窗口。而 `Binder` 只能获取调用者的 `pid`，无法区分同一进程内的不同窗口。

**第三，`ANR` 检测**。`socketpair` 的 `FINISHED` 回调机制天然支持超时检测——如果 5 秒内没有收到 `FINISHED`，就触发 Input ANR。

### InputChannel 的创建过程

`InputChannel` 在窗口创建时建立，整个流程如下：

[图：InputChannel 创建时序图——ViewRootImpl -> WMS -> InputDispatcher 的 socketpair 建立过程]

```
ViewRootImpl.setView()
  → Session.addToDisplay()
    → WindowManagerService.addWindow()
      → WindowState.openInputChannel()
        → InputChannel.openInputChannelPair()  // 创建 socketpair
        → sockets[0] → InputDispatcher.registerInputChannel()  // 服务端
        → sockets[1] → 回传给 ViewRootImpl  // 客户端
```

`WindowState.openInputChannel()` 调用 `InputChannel.openInputChannelPair()`，内部通过 `socketpair()` 创建一对已连接的全双工 socket。`sockets[0]`（server 端）注册到 `InputDispatcher`，封装为 `Connection` 对象保存在 `mConnectionsByFd` 中；`sockets[1]`（client 端）通过 Binder 回传给 App 进程，保存在 `ViewRootImpl` 的 `mInputChannel` 中。

App 端拿到 `InputChannel` 后，会用它创建 `WindowInputEventReceiver`：

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
mInputEventReceiver = new WindowInputEventReceiver(inputChannel, Looper.myLooper());
```

在 native 层，`NativeInputEventReceiver` 的构造函数中，会把这个 socket fd 注册到 App 主线程的 native `Looper` 上监听。当 `InputDispatcher` 往 server 端写入事件数据时，App 主线程的 `Looper` 被 epoll 唤醒，回调到 `NativeInputEventReceiver::consumeEvents()`，完成事件接收。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/libs/input/InputTransport.cpp]
> [来源: obsidian/Cubox/Android图形系统（五）番外篇：触摸事件详解-2023-03-03.md]

## App 侧的事件分发：从 ViewRootImpl 到 View 树

到这里，事件已经从 `system_server` 通过 `socketpair` 到达了 App 进程。接下来的旅程，是从 `ViewRootImpl` 的 native 层回调开始，经过一条精心设计的 `InputStage` 责任链，最终分发到 View 树中的具体控件。不少开发者对 View 树的 `dispatchTouchEvent` / `onInterceptTouchEvent` / `onTouchEvent` 三件套很熟悉，但在这之前的 `InputStage` 处理、IME 优先级、native 层拦截等环节，往往是知识盲区。我们把整条路径完整走一遍。

### InputStage 责任链

`ViewRootImpl` 收到事件后，不是直接丢给 View 树，而是先经过一个 `InputStage` 责任链：

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
// 在 setView() 中设置责任链
mSyntheticInputStage = new SyntheticInputStage();
InputStage viewPostImeStage = new ViewPostImeInputStage(mSyntheticInputStage);
InputStage nativePostImeStage = new NativePostImeInputStage(viewPostImeStage, ...);
InputStage earlyPostImeStage = new EarlyPostImeInputStage(nativePostImeStage);
InputStage imeStage = new ImeInputStage(earlyPostImeStage, ...);
InputStage viewPreImeStage = new ViewPreImeInputStage(imeStage);
InputStage nativePreImeStage = new NativePreImeInputStage(viewPreImeStage, ...);
```

这个责任链的处理顺序是：

1. **NativePreImeInputStage** — native 层的输入法预处理
2. **ViewPreImeInputStage** — Java 层的输入法预处理（如 `View.onKeyPreIme()`）
3. **ImeInputStage** — 输入法处理（键盘事件先给输入法消费）
4. **EarlyPostImeInputStage** — 输入法处理后的早期处理
5. **NativePostImeInputStage** — native 层后处理
6. **ViewPostImeInputStage** — **主要的 View 树分发入口**
7. **SyntheticInputStage** — 合成事件处理（如从未处理的触摸事件合成滚动）

[图：InputStage 责任链处理顺序——从 NativePreIme 到 SyntheticInput 的七阶段流水线，标注每阶段的主要职责]

每个 Stage 可以选择自己处理（返回 `FINISH_HANDLED`）、传递给下一个 Stage（返回 `FORWARD`）或丢弃。真正把事件分发到 View 树的是第 6 个 Stage：`ViewPostImeInputStage`。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/ViewRootImpl.java]

### 事件到达 View 树的完整路径

在 `ViewPostImeInputStage` 中，触摸事件的处理路径如下：

```
ViewPostImeInputStage.processPointerEvent()
  → mView.dispatchPointerEvent(event)     // mView 是 DecorView
    → DecorView.dispatchTouchEvent()
      → Window.Callback.dispatchTouchEvent()   // 即 Activity.dispatchTouchEvent()
        → Activity.getWindow().superDispatchTouchEvent()
          → PhoneWindow.superDispatchTouchEvent()
            → DecorView.superDispatchTouchEvent()
              → ViewGroup.dispatchTouchEvent()     // 进入 View 树分发
```

这个路径看起来绕了一圈（DecorView → Activity → DecorView → ViewGroup），原因是 DecorView 把事件先交给 Activity 处理，给 Activity 一个拦截的机会；如果 Activity 不处理，最终回到 ViewGroup 的标准分发流程。

### ViewGroup 的分发、拦截与消费

`ViewGroup.dispatchTouchEvent()` 是 View 树事件分发的核心。下面我们聚焦 `MotionEvent` 在 ViewGroup 与子 View 之间的分发逻辑（完整的 `onInterceptTouchEvent` / `onTouchEvent` 交互细节可参考官方文档和第 3.2 节「触摸响应的性能分析」）。它的逻辑可以概括为三个步骤：

**第一步：检查是否拦截。** 如果事件是 `ACTION_DOWN` 或者有子 View 消费了之前的事件（`mFirstTouchTarget != null`），就进入拦截判断：

```java
// frameworks/base/core/java/android/view/ViewGroup.java
if (actionMasked == MotionEvent.ACTION_DOWN || mFirstTouchTarget != null) {
    final boolean disallowIntercept = (mGroupFlags & FLAG_DISALLOW_INTERCEPT) != 0;
    if (!disallowIntercept) {
        intercepted = onInterceptTouchEvent(ev);
    } else {
        intercepted = false;
    }
} else {
    intercepted = true;  // 没有子 View 消费，直接拦截
}
```

子 View 可以通过 `requestDisallowInterceptTouchEvent(true)` 设置 `FLAG_DISALLOW_INTERCEPT` 标志，禁止父 ViewGroup 拦截事件。这在嵌套滑动场景中非常常用（如 `RecyclerView` 嵌套 `ViewPager`）。

**第二步：遍历子 View 分发。** 如果没有拦截，对 `ACTION_DOWN` 事件，ViewGroup 会从后往前（Z 轴最上层优先）遍历子 View，检查触摸坐标是否落在子 View 的范围内，如果是，调用子 View 的 `dispatchTouchEvent()`。

**第三步：自身消费。** 如果没有子 View 消费（`mFirstTouchTarget == null`），ViewGroup 调用自己的 `onTouchEvent()`。如果子 View 消费了 `ACTION_DOWN`，后续的 `MOVE`、`UP` 事件会直接分发给记录在 `mFirstTouchTarget` 中的那个子 View，不再遍历。

这里有一个关键设计：**`mFirstTouchTarget` 链表**。它记录了消费了 `ACTION_DOWN` 事件的子 View。后续的 `MOVE`、`UP` 事件直接沿着这个链表分发，不再重新查找目标。这保证了整个触摸序列（DOWN → MOVE... → UP）由同一个 View 处理，避免了滑动过程中事件在不同 View 之间跳来跳去的混乱。

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/ViewGroup.java]

## ANR 超时机制：为什么是 5 秒

Input ANR 的触发机制可以类比为一个"定时炸弹"：发送事件时埋下炸弹，收到 App 的 FINISHED 回调时拆除炸弹，5 秒没拆除就引爆。

### 两种 Input ANR

Input 系统有两种不同类型的 ANR：

**No Focus Window ANR**：当 `InputDispatcher` 处理按键事件时，调用 `findFocusedWindowTargetsLocked()` 查找焦点窗口，如果当前有焦点 App 但没有焦点窗口（窗口还没准备好），就设置一个 5 秒超时。如果 5 秒内窗口准备好了，超时取消；否则触发 ANR。（关于 ANR 的完整设计思想，参见第 9.1 节「ANR 设计思想」。）

这种情况常见于 Activity 在 `onResume()` 中执行耗时操作导致窗口没有及时显示。比如：

```java
@Override
protected void onResume() {
    Thread.sleep(10000);  // 窗口还没准备好
    super.onResume();
}
```

**Dispatch Timeout ANR**：事件通过 `socketpair` 发送给 App 后，放入 `waitQueue` 并在 `mAnrTracker` 中注册超时。App 处理完事件后发送 `FINISHED` 回调，`InputDispatcher` 收到后从 `waitQueue` 和 `mAnrTracker` 中移除。5 秒内没收到 `FINISHED` 就触发 ANR。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
// 在 startDispatchCycleLocked 中设置 ANR
if (connection->responsive) {
    mAnrTracker.insert(dispatchEntry->timeoutTime,
                       connection->inputChannel->getConnectionToken());
}
```

### 5 秒超时的来源

默认超时时间定义在 `WindowManagerService` 中：

```java
// frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java
// [已验证: AOSP android-14.0.0_r1; android-16 经 web search 确认常量仍在 WMS.java 中定义]
static final long DEFAULT_INPUT_DISPATCHING_TIMEOUT_NANOS = 5000 * 1000000L; // 5 sec
```

这个值可以通过 `InputWindowHandle.dispatchingTimeoutNanos` 覆盖。系统窗口（如状态栏、导航栏）可能使用不同的超时值，但 App 窗口默认是 5 秒。

在 Perfetto 中，如果我们看到某个 App 的 `wq` 值持续大于 0 超过 5 秒，那么接下来就会出现 Input ANR。这就是为什么分析 Input 问题时，`wq` Track 是最重要的观察指标之一。

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]
> [来源: obsidian/Cubox/Input ANR on Android 13-2022-12-16.md]

## 在 Perfetto 中的完整表现

前面我们拆解了 Input 事件从硬件到 View 树的每一个环节。现在把这些环节放回到 Perfetto Trace 中，看看它们各自对应哪些 Track、什么形态，以及在出问题时应该如何定位。

### system_server 进程中的 Track

在 Perfetto 中，`system_server` 进程可以看到以下关键 Track：

- **InputReader 线程**：可以看到 `InputReader` 读取事件的活动。正常情况下每次读取都很短，如果看到 InputReader 长时间 `Runnable`（就绪但没被调度到），说明线程调度有问题。
- **InputDispatcher 线程**：可以看到事件分发的活动。
- **`iq` 计数器**：`InboundQueue` 的长度。通常很短，持续为 0 说明消费正常。
- **`oq:{windowName}` 计数器**：每个窗口的 `OutboundQueue` 长度。
- **`wq:{windowName}` 计数器**：每个窗口的 `WaitQueue` 长度。**这是最关键的一个**——如果 `wq` 值持续堆积，说明 App 没有及时处理事件，ANR 风险很高。

### App 进程中的 Track

在 App 进程的主线程（UI Thread）中：

- **`deliverInputEvent`**：这是 App 开始处理 Input 事件的标记。从 `ViewRootImpl.deliverInputEvent()` 到 `finishInputEvent()` 之间的时间，就是 App 处理这个事件所花费的时间。
- **`aq:pending:{windowName}` 计数器**：App 侧待处理的 Input 事件队列长度。
- **`InputResponse` 区域**：包含一个 `ACTION_DOWN` + 若干 `ACTION_MOVE` + 一个 `ACTION_UP` 的完整处理阶段。

> [来源: obsidian/Cubox/性能优化必学基础：input流程与systrace结合剖析-2025-07-12.md]
> [来源: obsidian/Cubox/Android Input 调试与优化 - 魅族内核团队-2025-08-05.md]

[待补充：Perfetto 截图——展示 iq/oq/wq Track 和 deliverInputEvent 的对应关系]

## Pointer Event 与 Motion Event

Android 的 Input 系统区分两种基本的指针类事件：

**Motion Event** 是 View 体系（`android.view.MotionEvent`）中的标准事件类型。所有通过 `InputChannel` 传递到 App 的触摸、轨迹球、鼠标事件，在 Java 层都表现为 `MotionEvent`，通过 `OnTouchListener.onTouch(view, event)` 或 `View.onTouchEvent(event)` 分发。

**Pointer Event** 是 Compose 和部分新 API 中对 `MotionEvent` 的封装。Jetpack Compose 的 `pointerInput` 修饰符使用的是 `PointerInputChange` 和 `PointerEvent`，底层仍然来自同一个 `MotionEvent`，但 Compose 层做了额外的变换（pointer id 追踪、相对位移计算、事件消费标记）。

从性能分析角度，两者在 Perfetto 中的表现完全一致——都通过同一个 `deliverInputEvent` → `dispatchTouchEvent` 路径，Trace 中看到的耗时没有区别。

> [来源: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/MotionEvent.java]

## InputFlinger 的角色与演进

在 Android 12 之前，`InputReader` 和 `InputDispatcher` 直接运行在 `system_server` 进程中。从 Android 12 开始，Google 将它们抽取到独立的 `InputFlinger` 服务中（虽然仍然运行在 `system_server` 进程），代码路径也重新组织为 `frameworks/native/services/inputflinger/`。

这个重构的主要目的是将 Input 系统的代码与 `system_server` 的其他模块解耦，使得 Input 系统可以独立演进和测试。[待验证：Android 15+ 中 InputFlinger 是否已支持独立进程隔离模式]

[待验证：InputFlinger 在 Android 12 的具体拆分粒度（reader/dispatcher 分目录结构是否从 12 开始就是当前形式）、Android 13 mAnrTracker 的源码级行为——以上基于社区素材和官方文档，未在 android-12/13 源码中逐一验证]在 Android 12+ 的代码中，`InputFlinger` 的目录结构为：

```
frameworks/native/services/inputflinger/
├── reader/          # InputReader 和 InputMapper
├── dispatcher/      # InputDispatcher
├── InputManager.cpp # 管理类
└── EventHub.cpp     # 事件入口
```

> [已验证: AOSP android-14.0.0_r1, frameworks/native/services/inputflinger/]

## 常见问题与误区

### 误区一：Input 事件通过 Binder 传递

Input 事件通过 `socketpair` 传递，不是 `Binder`。这一点在面试中经常被问到，原因我们在前面已经详细分析过。

### 误区二：事件分发是从 Activity 开始的

不少文章把 `Activity.dispatchTouchEvent()` 作为事件分发的起点，但在这之前，事件已经经历了 `ViewRootImpl` 的 `InputStage` 责任链处理。`Activity` 只是 DecorView 通过 `Window.Callback` 给到的一个拦截机会。

### 误区三：Input ANR 是 App 主线程卡了 5 秒

不完全准确。Input ANR 的触发条件是：**某个 Input 事件通过 `socketpair` 发送给 App 后，5 秒内没有收到 `FINISHED` 回调**。这 5 秒不仅包括 App 主线程执行 `deliverInputEvent` 的时间，还包括事件在 App 主线程 `MessageQueue` 中排队等待的时间。如果 App 主线程正在执行上一帧的 `doFrame`（Choreographer 回调，参见第 2.4 节），新的 Input 事件会排在消息队列后面等待——这段排队时间同样计入 5 秒超时。在 Perfetto 中，这种情况表现为 `wq` 持续堆积，但 `deliverInputEvent` 本身并不长。

### 误区四：ViewGroup 的 onInterceptTouchEvent 一定会被调用

不一定。如果子 View 调用了 `requestDisallowInterceptTouchEvent(true)`，ViewGroup 的 `onInterceptTouchEvent()` 就不会被调用。此外，如果不是 `ACTION_DOWN` 事件且没有子 View 消费（`mFirstTouchTarget == null`），`onInterceptTouchEvent()` 也不会被调用。

## 版本演进

| 版本 | 变化 |
|------|------|
| Android 4.1 (API 16) | 引入 InputFlinger 框架 |
| Android 12 (API 31) | InputFlinger 代码重构，拆分 reader/ 和 dispatcher/ 子目录 |
| Android 12 (API 31) | Input ANR 增加 "no focused window" 类型 |
| Android 13 (API 33) | InputDispatcher 使用 `mAnrTracker` 替代之前的超时检测方式 |
| Android 14+ | InputFlinger 进一步模块化，增加对折叠屏、多显示器的支持 |
| Android 15 (API 35) | 输入法与 Input 系统交互优化，改善 IME 切换时的输入延迟 |
| Android 16 (API 36) | [待验证：预测性返回手势（Predictive Back）对 Input 分发路径的影响] |

## 调试技巧

1. **`adb shell getevent`**：查看内核上报的原始 Input 事件数据，确认底层是否正常报点。输出格式为 `[device] type code value`，其中 type=3 (EV_ABS) 对应触摸坐标。如果这里看不到事件，问题在硬件或内核驱动层。
2. **`adb shell dumpsys input`**：查看 Input 系统运行时信息。重点关注 `RecentQueue`（最近分发的事件）、`InboundQueue`（待处理事件）、`PendingEvent`（等待 App 反馈的事件）、以及每个窗口 `Connection` 的 `status`。如果 `status` 显示 `NOT_RESPONDING`，说明 App 已经触发 Input ANR。
3. **`adb shell input keyevent / motionevent`**：模拟按键或触摸事件，直接注入到 `InputDispatcher`，绕过底层硬件。用于验证分发逻辑是否正常（排除硬件问题）。
4. **Perfetto Trace**：分析复杂 Input 问题最强大的工具。关键 Track：`iq/oq/wq` 三个队列计数器、`deliverInputEvent`（App 处理耗时）、`InputReader` 和 `InputDispatcher` 线程活动。定位思路：`iq` 堆积 -> InputDispatcher 处理慢；`oq` 堆积 -> 连接繁忙；`wq` 堆积 -> App 处理不及时（ANR 前兆）。
5. **`adb shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'`**：快速确认当前焦点窗口和焦点 App，排查焦点相关的按键事件丢失问题。

> [来源: obsidian/Cubox/Android Input 调试与优化 - 魅族内核团队-2025-08-05.md]

## 参考资料

### AOSP 源码路径

- `frameworks/native/services/inputflinger/reader/EventHub.cpp` — 事件入口
- `frameworks/native/services/inputflinger/reader/InputReader.cpp` — 事件读取与加工
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — 事件分发
- `frameworks/native/libs/input/InputTransport.cpp` — InputChannel 与跨进程通信
- `frameworks/base/core/java/android/view/ViewRootImpl.java` — App 侧事件接收
- `frameworks/base/core/java/android/view/ViewGroup.java` — View 树事件分发

### 素材来源

- [Analyze AOSP input architecture — utzcoz Blog]（基于 AOSP 9.0，Input 架构全景）
- [Android Input 调试与优化 — 魅族内核团队]（Perfetto 分析实践）
- [Input ANR on Android 13]（ANR 机制详解，基于 Android 13）
- [Android 事件分发溯源详解 — 开发者说·DTalk]（App 侧分发链路详解）
- [性能优化必学基础：input 流程与 systrace 结合剖析]（Systrace/Perfetto 结合分析）
- [从显示 Tap 原理一探 Android 12 的 Input 系统]（Show taps 功能的完整链路分析）
- [ANR-实例分析-Input dispatching timed out]（Input ANR 实战案例）
- [Android 图形系统（五）番外篇：触摸事件详解]（从硬件到 View 的完整分析）
