---
status: "finalized"
title: Input 事件分发全流程
chapter: '3.1'
section: '3.1'
last_task6_at: "2026-06-07T12:12:00+08:00"
last_task2b_lite_at: "2026-06-07"
task2b_lite_notes: "2026-06-07 删除重复 H1+outline+intro 块(L55-102);代码块语言标记待后续修复"
last_task6_review_log: "logs/review/2026-06-07-11-review.md"
task6_review_notes: "2026-05-30 01: Task6 revisiting review: needs-rework;L1/L2 小修 6 处;参考资料后仍有未融合源码调研素材块，新增 queue 回炉。 | 2026-06-07 11:06:B类问题-文件存在重复的H1+outline+intro块(第55-102行),需Task2B删除第一个不完整实例;L1/L2无新增小修项。 | 2026-06-07 12:12:task6 revisiting review(第3轮):修复 13 处代码块语言标记(```text→```cpp/```java + 闭合标签规范化);L1/L2 通过;无 B 类大问题;queue 中 3.1 的 pending 条目为 task2b 已修复的陈旧条目，建议清理。"
applicable_versions: Android 12 (API 31) - Android 16 (API 36)
last_verified: '2026-04-27'
last_verified_against: AOSP android-12/13/14/15/16 InputDispatcher.cpp / InputClassifier.cpp
version_note: 已补核 Android 12/13 的 InputClassifier、Android 14+ 的 InputProcessor、Android
confidence: high
reviewed_date: "2026-06-07"
reviewed_by: "openclaw-task6"
rework2_date: '2026-04-15'
rework2_by: openclaw-task2b
rework2_reason: 'Task9 Deep Tech Review: 修正 DEFAULT_INPUT_DISPATCHING_TIMEOUT 常量源码路径(frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp)'
polish_count: 1
polish_date: '2026-04-05'
polish_by: task2b-polish
sources: 
- type: blog
path: https://mp.weixin.qq.com/s/Analyze-AOSP-input-architecture
tags: 
related_chapters: 
task6_result: "pass-light-edit"
task6_state: "reviewed"
pipeline_stage: "ready-to-publish"
task6_reviewed_date: "2026-06-07"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: "fixed"
task2b_result: "fixed-lite"
task2b_notes: "修复 Task6 2026-05-30 回炉问题:移除未进入 Android 17 的 DeliQueue 推测内容，清理参考资料后未融合的源码调研素材块。2026-06-07 Task2B 主修复：修正 HwTimeoutMultiplier() 版本表入口（Android 13 已存在）；修复 frontmatter 重复 pipeline_stage 键。"
task2b_fixed_by: openclaw-task2b
task2b_fixed_at: "2026-06-07T10:50:00+08:00"
task9_reviewed_date: "2026-06-07"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-07T12:24:00+08:00"
review_notes: "2026-06-07 Task9 深度技术审计通过：无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task2b_at: "2026-05-30T00:50:00+08:00"
repaired_date: '2026-04-27'
repaired_by: openclaw-task2b
last_task9_review_log: "logs/deep-review/2026-06-07-12-deep-review.md"
task6_reviewed_by: "openclaw-task6"
task6_l1_l2_fixes: 19
task6_l3_l4_issues: 1
task6_new_rework: true
review_type: "task6-writing-quality-review"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-07
---

# Input 事件分发全流程

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 输入事件完整路径:硬件 → Kernel InputDriver → EventHub → InputReader → InputClassifier/InputProcessor → InputDispatcher → App ViewRootImpl → View 树
- 🔹 InputDispatcher 的分发策略:焦点窗口、触摸窗口、ANR 超时
- 🔹 App 侧的事件分发:ViewRootImpl → DecorView → Activity.dispatchTouchEvent → ViewGroup → View
- 🔹 InputChannel 与 Socket pair 机制
- 🔹 关键超时参数:5s ANR for Key, 5s for Touch (Android 不同版本变化)

### 扩展(可选深入)

- 🔸 InputFlinger 的角色与演进
- 🔸 输入事件在 Systrace 中的完整追踪:deliverInputEvent → input event latency
- 🔸 Pointer Event 与 Motion Event 的区别

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Input 事件分发

当我们在 Perfetto 中追踪一次点击卡顿或滑动不跟手的问题时,最常看到的线索之一就是 `deliverInputEvent` 这个 Trace tag--它对应的就是 App 侧 UI 线程被 Input 事件唤醒并开始处理的那段时间。如果我们不理解 Input 事件是怎么从硬件一路走到这个 tag 的,就无法判断问题出在哪个环节:是底层报点延迟?是 InputDispatcher 分发不及时?还是 App 主线程本身卡住了?

理解 Input 事件分发的完整路径,就是为了在分析这类问题时,能够在 Perfetto 的每一个关键 Track 上精确定位:事件在哪个环节被延迟了,延迟了多少,以及为什么。

## 从硬件到 App:一条完整的事件传递路径

一次触摸事件从手指触碰屏幕到 App 开始处理,要经历一条很长的路径。我们可以把这条路径分成四段来看:

[图:Input 事件分发全路径架构图--从触控 IC 到 App View 树]

**第一段:硬件 → Linux 内核**。触摸屏的触控 IC 芯片捕获电压/电流变化,计算出触摸坐标,通过 I2C 总线通知 CPU。Linux 内核的 Input 子系统按照统一的协议规范,将原始事件写入 `/dev/input/eventX` 设备文件。这一段对 Android Framework 来说是透明的,我们用 `adb shell getevent` 命令看到的就是这一层的原始数据。

**第二段:EventHub → InputReader**。这是 Android Framework 层的第一道关卡。`EventHub` 利用 Linux 的 `epoll` 机制监听 `/dev/input/` 目录下的设备文件,当有新事件时可读取。`InputReader` 是一个跑在 `system_server` 进程中的 Native 循环线程,它不断从 `EventHub` 读取原始的 `struct input_event`,然后根据设备类型(触摸屏、键盘、鼠标等)交给对应的 `InputMapper` 做"加工"(cook)--把原始数据转成 Android 层认识的 `KeyEvent`、`MotionEvent`。

**第三段:InputClassifier/InputProcessor → InputDispatcher → 目标窗口**。触摸事件在进入分发线程前还有一层版本化处理:Android 12/13 的代码路径是 `InputReader → InputClassifier → InputDispatcher`,Android 14+ 演进为 `InputReader → InputProcessor → InputDispatcher`。这一层负责触摸分类、palm rejection、stylus 等处理;不需要分类的事件会直接透传到 queued listener,然后进入 `InputDispatcher`。`InputDispatcher` 再找到目标窗口(焦点窗口或触摸区域命中的窗口),通过 `InputChannel`(底层是 `socketpair`)跨进程把事件发送给 App。

**第四段:App 侧分发**。App 进程通过 `WindowInputEventReceiver` 收到事件,经过 `ViewRootImpl` 的责任链式 `InputStage` 管线处理,最终分发到 View 树中的具体控件。

整个过程涉及两个进程(`system_server` 和 App)、四个关键组件(`EventHub`、`InputReader`、`InputDispatcher`、`ViewRootImpl`),以及一个跨进程通信机制(`InputChannel`/`socketpair`)。这条路径可以按这四个环节继续展开。

## EventHub:事件入口的哨兵

`EventHub` 是整个 Input 系统的入口。它的核心工作是监听 `/dev/input/` 目录下设备文件的变化,并对外提供 `getEvents()` 接口。

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
        // 读取设备文件中的事件,封装为 RawEvent
        // 如果没有事件,epoll_wait 会阻塞
    }
}
```

这里有两个机制:

**第一,`epoll` 机制**。`EventHub` 不是轮询,而是利用 Linux 的 `epoll` 在设备文件有数据可读时才被唤醒。在没有事件的时候,`InputReader` 线程会休眠,不会消耗 CPU。

**第二,`inotify` 机制**。`EventHub` 同时监听 `/dev/input/` 目录本身的变化--当有新设备插入或拔出时(比如蓝牙键盘连接),`inotify` 会产生一个事件,`EventHub` 就能感知到并执行设备打开/关闭操作。


## InputReader:从原始数据到 Android 事件

`InputReader` 的核心职责是"加工"(cook)--把内核上报的原始 `struct input_event` 转换成 Android Framework 能理解的 `KeyEvent`、`MotionEvent` 对象。

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

`InputReader` 为每种输入设备类型分配了对应的 `InputMapper`:

- 触摸屏设备 → `MultiTouchInputMapper`(继承自 `TouchInputMapper`)
- 键盘设备 → `KeyboardInputMapper`
- 鼠标/轨迹球设备 → `CursorInputMapper`

以触摸事件为例,`TouchInputMapper` 会将多点触控的原始坐标数据加工为包含坐标、压力、触摸点数量等完整信息的 `NotifyMotionArgs`。之后的提交路径要按版本拆开:Android 12/13 通过 `services/inputflinger/InputClassifier.cpp` 的 `InputClassifier::notifyMotion()` 进入 queued listener;Android 14+ 对应 `services/inputflinger/InputProcessor.cpp` 的 `InputProcessor::notifyMotion()`。代码里专门把 MotionClassifier 放到独立 HAL thread,目的就是避免分类 HAL 的耗时直接卡住输入分发。

普通触摸 Trace 中不一定会出现单独的 `InputClassifier` 或 `InputProcessor` 长 slice;更常见的信号仍是 `InputReader`、`InputDispatcher`、`iq/oq/wq` 和 App 侧 `deliverInputEvent`。当怀疑触摸分类、手掌误触、stylus 过滤影响延迟时,再结合 `dumpsys input`、设备配置和 inputflinger 日志确认这一层。

开发者选项中的 "Show taps"(显示触摸操作)功能,也是在 `InputReader` 这一层处理,不在 App 层。`TouchInputMapper` 在加工触摸事件时,如果检测到 `showTouches` 配置开启,会通过 `PointerController` 直接在系统层绘制触摸圆点。这样即使 App 卡住了,我们依然能看到触摸圆点在动。

## InputDispatcher 的分发策略

`InputDispatcher` 是整个事件分发流程中策略最复杂的组件。它负责决定:**给定一个输入事件,应该把它发送给哪个窗口?**

### 焦点窗口 vs 触摸窗口

`InputDispatcher` 对不同类型的事件采用不同的目标窗口查找策略:

**KeyEvent(按键事件)** 走焦点窗口路径。`InputDispatcher` 通过 `findFocusedWindowTargetsLocked()` 查找当前拥有焦点的窗口,将按键事件发送给它。焦点窗口由 `WindowManagerService` 通过 `InputMonitor` 设置到 `InputDispatcher` 中。

**MotionEvent(触摸事件)** 走触摸区域命中路径。`InputDispatcher` 通过 `findTouchedWindowTargetsLocked()` 遍历所有窗口,找到触摸点坐标落在其 `touchableRegion` 内的那个窗口。窗口的 `touchableRegion` 来自 `WindowState.getTouchableRegion()`,由 WMS 管理。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
bool InputDispatcher::dispatchMotionLocked(nsecs_t currentTime,
        std::shared_ptr<MotionEntry> entry, DropReason* dropReason, nsecs_t* nextWakeupTime) {
    // ...
    if (isPointerEvent) {
        // 触摸事件:按触摸区域查找
        injectionResult = findTouchedWindowTargetsLocked(currentTime, *entry,
            inputTargets, nextWakeupTime, &conflictingPointerActions);
    } else {
        // 非触摸事件(如轨迹球):按焦点窗口查找
        injectionResult = findFocusedWindowTargetsLocked(currentTime, *entry,
            inputTargets, nextWakeupTime);
    }
    // ...
    dispatchEventLocked(currentTime, entry, inputTargets);
}
```

为什么触摸事件不用焦点窗口?因为触摸事件的天然语义就是"点到谁就给谁"。如果用户点了一个悬浮窗下方的按钮,应该由悬浮窗接收事件(因为它在上面),而不是焦点窗口。而按键事件没有空间信息,只能用焦点窗口来决定接收者。

### 手势排除区域

在 Android 16 的 AOSP 主线源码中,手势排除区域(g gesture exclusion)尚未作为独立机制进入 `InputDispatcher` 的分发路径。`InputDispatcher.cpp` 没有专门处理手势排除区域的代码分支,`WindowInfo.h` 中也未出现 `gesture exclusion` 相关的结构字段。此前一些资料提到的"10ms 优化收益",在现有 AOSP 主线中缺乏源码依据。

排查边缘触控问题时,仍以窗口命中判断、系统手势区域和 `InputDispatcher` 的分发耗时(slice)为主要分析手段。如果后续版本确认手势排除逻辑下沉到 Native 输入循环,再结合对应源码 tag 和 Perfetto trace 样本补充。

### 三大队列:iq / oq / wq

在 Perfetto 中追踪 Input 问题时,我们经常看到三个计数器 Track:`iq`、`oq`、`wq`。它们对应 `InputDispatcher` 内部的三个关键队列:

**InboundQueue(iq)**:`InputReader` 加工完的事件先进入这个队列。`InputDispatcher` 的主循环从这个队列取出事件进行分发。在 Perfetto 中通过 `ATRACE_INT("iq", mInboundQueue.size())` 追踪。

**OutboundQueue(oq)**:每个窗口连接(`Connection`)都有一个独立的 `outboundQueue`,存放即将通过 `InputChannel` 发送给该窗口的事件。事件从 `iq` 取出后,找到目标窗口,放入对应窗口的 `oq`。在 Perfetto 中格式为 `oq:{windowName}`。

**WaitQueue(wq)**:事件通过 `socketpair` 发送给 App 后,从 `oq` 移到 `wq`,等待 App 处理完毕的反馈。收到 App 的 `FINISHED` 回调后,事件从 `wq` 移除。在 Perfetto 中格式为 `wq:{windowName}`。

这三个队列的生命周期反映了一个事件在 `InputDispatcher` 中的完整旅程:

```text
iq(等待分发)→ oq(准备发送)→ wq(等待 App 反馈)→ 移除
```

如果我们在 Perfetto 中看到 `wq` 的值持续增长不下降,说明 App 没有及时处理 Input 事件--这是 Input ANR 的前兆。

### 按键拦截:PhoneWindowManager 的特殊角色

在按键事件到达目标窗口之前,还有一个拦截环节。`InputDispatcher` 在分发按键事件时,会先询问 `PhoneWindowManager`(通过 `InputDispatcherPolicyInterface`)是否要拦截这个按键。

```cpp
// 拦截决策的入口
nsecs_t delay = mPolicy->interceptKeyBeforeDispatching(
    commandEntry->inputWindowHandle, &event, entry->policyFlags);
```

如果 `PhoneWindowManager.interceptKeyBeforeDispatching()` 返回 -1,表示这个按键被系统消费了,`InputDispatcher` 会丢弃该事件。像 `ALT+TAB`(最近任务)、电源键、音量键等系统级按键,都是在这里被拦截处理的。

这也解释了一个常见的困惑:为什么有些按键事件在 App 的 `dispatchKeyEvent` 里收不到?因为它们已经被 `PhoneWindowManager` 在分发前拦截了。

### 返回键分发与预测性返回的边界

返回键的处理链路需要区分两层:

**第一层:按键分发(InputDispatcher → App)**。`KEYCODE_BACK` 作为标准按键事件,走的是和音量键一样的 `InputDispatcher → InputChannel → ViewRootImpl → View 树` 分发路径。`InputDispatcher` 本身不解析返回键的语义,只负责把按键送到焦点窗口。

**第二层:返回手势/预测性返回(Framework 窗口层)**。Android 13+ 引入的预测性返回(Predictive Back)和 `OnBackInvokedDispatcher` / `OnBackInvokedCallback` 是 **Framework 窗口层**(`Window.java` / `Activity.java` / `OnBackInvokedDispatcher.java`)的机制,不是 `InputDispatcher` 内部的逻辑。当 App 注册了 `OnBackInvokedCallback` 后,返回手势的拦截和回调发生在 App 进程的窗口层,而不是 `system_server` 的 `InputDispatcher` 里。

排查返回键事件"消失"时,先确认是按键事件没从 `InputDispatcher` 发出来(查 `iq/oq/wq` 和 `dumpsys input`),还是 App 侧窗口层消费后没有回调到 `dispatchKeyEvent`(查 `OnBackInvokedDispatcher` 注册状态)。两者发生在不同层,不要混在一起判断。


## InputChannel 与 Socket Pair:跨进程的事件管道

`InputDispatcher` 运行在 `system_server` 进程,而目标窗口运行在 App 进程,两者之间的通信靠的是 `InputChannel`,底层实现是 Linux 的 `socketpair()`。

### 为什么用 socketpair 而不是 Binder?

这是面试中常被问到的问题。`InputDispatcher` 选择 `socketpair` 而非 `Binder` 有三个关键原因:

**第一,事件排队能力**。`InputDispatcher` 需要跟踪每个事件是否已被 App 处理完成(`FINISHED` 回调),`socketpair` 天然支持这种"发送-等待确认"的模式。事件发送后留在 `waitQueue` 中,只有收到 App 的 `FINISHED` 消息才移除。而 `Binder` 是同步调用模型,不适合这种异步确认场景。

**第二,窗口区分**。一个 App 进程可能有多个窗口(如 `Dialog`、悬浮窗等),每个窗口需要独立的 `InputChannel`。通过 `socketpair`,一个进程可以创建多对 socket 来标识不同窗口。而 `Binder` 只能获取调用者的 `pid`,无法区分同一进程内的不同窗口。

**第三,`ANR` 检测**。`socketpair` 的 `FINISHED` 回调机制天然支持超时检测--如果 5 秒内没有收到 `FINISHED`,就触发 Input ANR。

### InputChannel 的创建过程

`InputChannel` 在窗口创建时建立,整个流程如下:

[图:InputChannel 创建时序图--ViewRootImpl -> WMS -> InputDispatcher 的 socketpair 建立过程]

```text
ViewRootImpl.setView()
  → Session.addToDisplay()
    → WindowManagerService.addWindow()
      → WindowState.openInputChannel()
        → InputChannel.openInputChannelPair()  // 创建 socketpair
        → sockets[0] → InputDispatcher.registerInputChannel()  // 服务端
        → sockets[1] → 回传给 ViewRootImpl  // 客户端
```

`WindowState.openInputChannel()` 调用 `InputChannel.openInputChannelPair()`,内部通过 `socketpair()` 创建一对已连接的全双工 socket。`sockets[0]`(server 端)注册到 `InputDispatcher`,封装为 `Connection` 对象保存在 `mConnectionsByFd` 中;`sockets[1]`(client 端)通过 Binder 回传给 App 进程,保存在 `ViewRootImpl` 的 `mInputChannel` 中。

创建失败时,问题通常停在 `InputChannel.openInputChannelPair()` 或 JNI 封装层。`socketpair()` 返回失败后,Framework 会向上抛出运行时异常,窗口无法完成输入通道建立。线上常见原因是进程或系统 fd 耗尽(`EMFILE` / `ENFILE`)以及内存不足(`ENOMEM`)。这类问题不会表现为普通的 `wq` 堆积,因为事件还没有进入目标窗口连接;更常见的现象是窗口添加失败、焦点窗口迟迟不可用,随后触发 No Focus Window ANR 或窗口初始化异常。

App 端拿到 `InputChannel` 后,会用它创建 `WindowInputEventReceiver`:

```java
// frameworks/base/core/java/android/view/ViewRootImpl.java
mInputEventReceiver = new WindowInputEventReceiver(inputChannel, Looper.myLooper());
```

在 native 层,`NativeInputEventReceiver` 的构造函数中,会把这个 socket fd 注册到 App 主线程的 native `Looper` 上监听。当 `InputDispatcher` 往 server 端写入事件数据时,App 主线程的 `Looper` 被 epoll 唤醒,回调到 `NativeInputEventReceiver::consumeEvents()`,完成事件接收。如果接收器初始化失败,`ViewRootImpl` 侧不会得到可用的 `mReceiverPtr`;后续 `finishInputEvent()` 会走空指针保护路径,但这已经说明输入通道没有正常进入工作状态。

### InputChannel 断开后的清理路径

`InputChannel` 还负责失败感知。App 进程退出、窗口销毁或 socket 断开后,`InputDispatcher` 会在对应 `Connection` 上看到 channel broken / zombie 状态,随后移除 fd 监听、清理 `mConnectionsByFd` 中的连接,并让策略层刷新窗口状态。窗口正常销毁时,`WindowToken` / `WindowState` 侧的 dispose 回调也会触发 InputDispatcher 注销通道,避免已经消失的窗口继续持有输入连接。线上遇到"窗口已经消失但还在等输入反馈"的问题时,要把这条失败路径纳入排查。

排查 InputChannel 连接问题时,可以从几个关键状态入手。先用 `dumpsys input` 检查目标窗口 Connection 的 status,确认是 NORMAL、BROKEN、ZOMBIE 还是 NOT_RESPONDING。如果连接已经 broken 但 `wq:{windowName}` 仍长时间存在,继续追踪窗口移除流程和 WMS/SurfaceFlinger 的窗口信息刷新是否滞后。App 进程死亡时,结合 `process_exit`、Activity/Window 销毁日志和 `InputDispatcher` warning,判断连接清理是否完整。如果窗口根本没拿到 `InputChannel`,先查 fd 数量、`logcat` 中的 `EMFILE` / `ENFILE` / `ENOMEM`,再对比 WMS 添加窗口失败和 No Focus Window ANR 的时间点。

## App 侧的事件分发:从 ViewRootImpl 到 View 树

到这里,事件已经从 `system_server` 通过 `socketpair` 到达了 App 进程。接下来的旅程,是从 `ViewRootImpl` 的 native 层回调开始,经过一条精心设计的 `InputStage` 责任链,最终分发到 View 树中的具体控件。不少开发者对 View 树的 `dispatchTouchEvent` / `onInterceptTouchEvent` / `onTouchEvent` 三件套很熟悉,但在这之前的 `InputStage` 处理、IME 优先级、native 层拦截等环节,往往是知识盲区。我们把整条路径完整走一遍。

### InputStage 责任链

`ViewRootImpl` 收到事件后,不是直接丢给 View 树,而是先经过一个 `InputStage` 责任链:

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

这个责任链的处理顺序是:

1. **NativePreImeInputStage** - native 层的输入法预处理
2. **ViewPreImeInputStage** - Java 层的输入法预处理(如 `View.onKeyPreIme()`)
3. **ImeInputStage** - 输入法处理(键盘事件先给输入法消费)
4. **EarlyPostImeInputStage** - 输入法处理后的早期处理
5. **NativePostImeInputStage** - native 层后处理
6. **ViewPostImeInputStage** - **主要的 View 树分发入口**
7. **SyntheticInputStage** - 合成事件处理(如从未处理的触摸事件合成滚动)

[图:InputStage 责任链处理顺序--从 NativePreIme 到 SyntheticInput 的七阶段流水线,标注每阶段的主要职责]

每个 Stage 可以选择自己处理(返回 `FINISH_HANDLED`)、传递给下一个 Stage(返回 `FORWARD`)或丢弃。把事件分发到 View 树的是第 6 个 Stage:`ViewPostImeInputStage`。

### 事件到达 View 树的完整路径

在 `ViewPostImeInputStage` 中,触摸事件的处理路径如下:

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

这个路径看起来绕了一圈(DecorView → Activity → DecorView → ViewGroup),原因是 DecorView 把事件先交给 Activity 处理,给 Activity 一个拦截的机会;如果 Activity 不处理,最终回到 ViewGroup 的标准分发流程。

### ViewGroup 的分发、拦截与消费

`ViewGroup.dispatchTouchEvent()` 是 View 树事件分发的核心。下面我们聚焦 `MotionEvent` 在 ViewGroup 与子 View 之间的分发逻辑(完整的 `onInterceptTouchEvent` / `onTouchEvent` 交互细节可参考官方文档和第 3.2 节「触摸响应的性能分析」)。它的逻辑可以概括为三个步骤:

**第一步:检查是否拦截。** 如果事件是 `ACTION_DOWN` 或者有子 View 消费了之前的事件(`mFirstTouchTarget != null`),就进入拦截判断:

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
    intercepted = true;  // 没有子 View 消费,直接拦截
}
```

子 View 可以通过 `requestDisallowInterceptTouchEvent(true)` 设置 `FLAG_DISALLOW_INTERCEPT` 标志,禁止父 ViewGroup 拦截事件。这在嵌套滑动场景中非常常用(如 `RecyclerView` 嵌套 `ViewPager`)。

**第二步:遍历子 View 分发。** 如果没有拦截,对 `ACTION_DOWN` 事件,ViewGroup 会从后往前(Z 轴最上层优先)遍历子 View,检查触摸坐标是否落在子 View 的范围内,如果是,调用子 View 的 `dispatchTouchEvent()`。

**第三步:自身消费。** 如果没有子 View 消费(`mFirstTouchTarget == null`),ViewGroup 调用自己的 `onTouchEvent()`。如果子 View 消费了 `ACTION_DOWN`,后续的 `MOVE`、`UP` 事件会直接分发给记录在 `mFirstTouchTarget` 中的那个子 View,不再遍历。

**`mFirstTouchTarget` 链表**是整个分发机制的关键数据结构。它记录了消费了 `ACTION_DOWN` 事件的子 View。后续的 `MOVE`、`UP` 事件直接沿着这个链表分发,不再重新查找目标。这保证了整个触摸序列(DOWN → MOVE... → UP)由同一个 View 处理,避免了滑动过程中事件在不同 View 之间跳来跳去的混乱。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
void InputDispatcher::onWindowInfosChanged(
        const std::vector<WindowInfo>& windowInfos,
        const std::vector<DisplayInfo>& displayInfos) {
    mWindowInfoByToken.clear();
    for (const auto& info : windowInfos) {
        mWindowInfoByToken[info.token] = info;
    }
    mDisplayInfo = displayInfos;
    mAnrController.onWindowInfosChanged(windowInfos, displayInfos);
}
```

窗口信息会影响目标窗口选择、触摸命中判断、ANR 判责和 blocked 状态处理。性能分析时,这条路径解释的是"输入拓扑如何跟随窗口/Surface 状态刷新",不是 App 侧事件处理耗时本身。


## ANR 超时机制:为什么是 5 秒

前面说到 InputDispatcher 把事件发给 App 后放入 waitQueue 等待反馈——如果 App 一直不回应,系统怎么办? 答案就是 Input ANR 超时机制:发送事件时"埋下炸弹",收到 App 的 FINISHED 回调时"拆除炸弹",5 秒没拆就引爆。

### 两种 Input ANR

Input 系统有两种不同类型的 ANR:

**No Focus Window ANR**:当 `InputDispatcher` 处理按键事件时,调用 `findFocusedWindowTargetsLocked()` 查找焦点窗口,如果当前有焦点 App 但没有焦点窗口(窗口还没准备好),就设置一个 5 秒超时。如果 5 秒内窗口准备好了,超时取消;否则触发 ANR。(关于 ANR 的完整设计思想,参见第 9.1 节「ANR 设计思想」。)

这种情况常见于 Activity 在 `onResume()` 中执行耗时操作导致窗口没有及时显示。比如:

```java
@Override
protected void onResume() {
    Thread.sleep(10000);  // 窗口还没准备好
    super.onResume();
}
```

**Dispatch Timeout ANR**:事件通过 `socketpair` 发送给 App 后,放入 `waitQueue` 并在 `mAnrTracker` 中注册超时。App 处理完事件后发送 `FINISHED` 回调,`InputDispatcher` 收到后从 `waitQueue` 和 `mAnrTracker` 中移除。5 秒内没收到 `FINISHED` 就触发 ANR。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
// 在 startDispatchCycleLocked 中设置 ANR
if (connection->responsive) {
    mAnrTracker.insert(dispatchEntry->timeoutTime,
                       connection->inputChannel->getConnectionToken());
}
```

### 5 秒超时的来源

默认超时时间在 InputDispatcher 中定义。Android 14/15/16 的代码已经是 `std::chrono` 写法,默认 5 秒来自 `IInputConstants.UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS`,并会经过 `HwTimeoutMultiplier()` 放大:

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
// [已验证: AOSP android-14.0.0_r1 / android-16.0.0_r1]
const std::chrono::duration DEFAULT_INPUT_DISPATCHING_TIMEOUT = std::chrono::milliseconds(
        android::os::IInputConstants::UNMULTIPLIED_DEFAULT_DISPATCHING_TIMEOUT_MILLIS *
        HwTimeoutMultiplier());
```

窗口级超时由窗口信息中的 `dispatchingTimeout` 覆盖。InputDispatcher 查到目标窗口后,会走 `window->getDispatchingTimeout(DEFAULT_INPUT_DISPATCHING_TIMEOUT)`;没有目标窗口可用时才回退到默认值。

在 Perfetto 中,如果我们看到某个 App 的 `wq` 值持续大于 0 超过 5 秒,那么接下来就会出现 Input ANR。这就是为什么分析 Input 问题时,`wq` Track 是最重要的观察指标之一。

## 在 Perfetto 中的完整表现

前面已经梳理了 Input 事件从硬件到 View 树的每一个环节。把这些环节放回 Perfetto Trace 中,就能对应到各自的 Track、形态和定位入口。

### system_server 进程中的 Track

在 Perfetto 中,`system_server` 进程有以下关键 Track:

- **InputReader 线程**:`InputReader` 读取事件的 slice 反映了事件读取活动。正常情况下每次读取都很短,如果发现 InputReader 长时间 `Runnable`(就绪但没被调度到),说明线程调度有问题。
- **InputDispatcher 线程**:反映了事件分发的活动。
- **`iq` 计数器**:`InboundQueue` 的长度。通常很短,持续为 0 说明消费正常。
- **`oq:{windowName}` 计数器**:每个窗口的 `OutboundQueue` 长度。
- **`wq:{windowName}` 计数器**:每个窗口的 `WaitQueue` 长度。**这是最关键的一个**--如果 `wq` 值持续堆积,说明 App 没有及时处理事件,ANR 风险很高。

### App 进程中的 Track

在 App 进程的主线程(UI Thread)中:

- **`deliverInputEvent`**:这是 App 开始处理 Input 事件的标记。从 `ViewRootImpl.deliverInputEvent()` 到 `finishInputEvent()` 之间的时间,就是 App 处理这个事件所花费的时间。
- **`aq:pending:{windowName}` 计数器**:App 侧待处理的 Input 事件队列长度。
- **`InputResponse` 区域**:包含一个 `ACTION_DOWN` + 若干 `ACTION_MOVE` + 一个 `ACTION_UP` 的完整处理阶段。


## Pointer Event 与 Motion Event

Android 的 Input 系统区分两种基本的指针类事件:

**Motion Event** 是 View 体系(`android.view.MotionEvent`)中的标准事件类型。所有通过 `InputChannel` 传递到 App 的触摸、轨迹球、鼠标事件,在 Java 层都表现为 `MotionEvent`,通过 `OnTouchListener.onTouch(view, event)` 或 `View.onTouchEvent(event)` 分发。

**Pointer Event** 是 Compose 和部分新 API 中对 `MotionEvent` 的封装。Jetpack Compose 的 `pointerInput` 修饰符使用的是 `PointerInputChange` 和 `PointerEvent`,底层仍然来自同一个 `MotionEvent`,但 Compose 层做了额外的变换(pointer id 追踪、相对位移计算、事件消费标记)。

从性能分析角度,两者在 Perfetto 中的表现完全一致--都通过同一个 `deliverInputEvent` → `dispatchTouchEvent` 路径,Trace 中看到的耗时没有区别。

## InputFlinger 的角色与版本边界

Android 12 到 Android 16 的 `InputReader`、`InputDispatcher`、`InputProcessor` 等实现都位于 `frameworks/native/services/inputflinger/`。这说明源码按 inputflinger 模块组织,但 AOSP 主线默认运行形态仍是通过 `libinputflinger` 等库进入 `system_server`;独立 `inputflinger` 进程仍停留在 TODO 或 OEM 形态。

### 已核验的版本事实

| 版本 | 已核验事实 |
|------|------------|
| Android 12 | `dispatcher/InputDispatcher.cpp` 中的 stale 判定是静态 `isStaleEvent(...)`;触摸分类路径使用 `InputClassifier.cpp` |
| Android 13 | 引入 `DispatcherWindowListener` / `addWindowInfosListener()`;触摸分类路径仍是 `InputClassifier.cpp` |
| Android 14 | 触摸分类路径演进为 `InputProcessor.cpp`;`DEFAULT_INPUT_DISPATCHING_TIMEOUT` 使用 `std::chrono` + `HwTimeoutMultiplier()` |
| Android 15 | stale 判定改为 `mPolicy.isStaleEvent(currentTime, entry.eventTime)` |
| Android 16 | stale 判定路径延续 Android 15;`services/inputflinger/Android.bp` 仍保留 "Move inputflinger to its own process" TODO |

`services/inputflinger/Android.bp` 中的 TODO 说明独立进程化仍不是 AOSP 12-16 的默认事实。某些产品/OEM 可以调整服务形态,但正文只能按可核验的 AOSP 主线描述。

## 常见问题与误区

### 误区一:Input 事件通过 Binder 传递

Input 事件通过 `socketpair` 传递,不是 `Binder`。这一点在面试中经常被问到,原因我们在前面已经详细分析过。

### 误区二:事件分发是从 Activity 开始的

不少文章把 `Activity.dispatchTouchEvent()` 作为事件分发的起点,但在这之前,事件已经经历了 `ViewRootImpl` 的 `InputStage` 责任链处理。`Activity` 只是 DecorView 通过 `Window.Callback` 给到的一个拦截机会。

### 误区三:Input ANR 是 App 主线程卡了 5 秒

不完全准确。Input ANR 的触发条件是:**某个 Input 事件通过 `socketpair` 发送给 App 后,5 秒内没有收到 `FINISHED` 回调**。这 5 秒不仅包括 App 主线程执行 `deliverInputEvent` 的时间,还包括事件在 App 主线程 `MessageQueue` 中排队等待的时间。如果 App 主线程正在执行上一帧的 `doFrame`(Choreographer 回调,参见第 2.4 节),新的 Input 事件会排在消息队列后面等待--这段排队时间同样计入 5 秒超时。在 Perfetto 中,这种情况表现为 `wq` 持续堆积,但 `deliverInputEvent` 本身并不长。

### 误区四:ViewGroup 的 onInterceptTouchEvent 一定会被调用

不一定。如果子 View 调用了 `requestDisallowInterceptTouchEvent(true)`,ViewGroup 的 `onInterceptTouchEvent()` 就不会被调用。此外,如果不是 `ACTION_DOWN` 事件且没有子 View 消费(`mFirstTouchTarget == null`),`onInterceptTouchEvent()` 也不会被调用。

## 版本演进

版本演进表只保留已经补过源码的差异。没有补核到源码的推断,不再直接写进表里。

| 版本 | 已核验变化 |
|------|------------|
| Android 12 (API 31) | `InputDispatcher.cpp` 中的 stale 判定是静态 `isStaleEvent(...)`;窗口信息仍走 `setInputWindows()` 路径;触摸分类使用 `InputClassifier.cpp` |
| Android 13 (API 33) | 引入 `DispatcherWindowListener` / `addWindowInfosListener()`;`setInputWindows()` 仍作为兼容入口存在;stale/dispatch timeout 路径已出现 `HwTimeoutMultiplier()` |
| Android 14 (API 34) | 触摸分类路径演进为 `InputProcessor.cpp`;默认 dispatch timeout 改用 `std::chrono` 写法,`HwTimeoutMultiplier()` 延续 Android 13 已引入的机制 |
| Android 15 (API 35) | stale 判定改为 `mPolicy.isStaleEvent(currentTime, entry.eventTime)` |
| Android 16 (API 36) | stale 判定路径延续 Android 15;AOSP 主线仍没有默认把 inputflinger 独立成单独进程 |

[版本边界:Predictive Back 已在上文限定为 Framework 窗口层机制;AOSP android-16.0.0_r1 未见其进入 `InputDispatcher` 主分发路径。IME 交互优化仍需单独源码锚点,不写入本表。]

## 调试技巧

1. **`adb shell getevent`**:查看内核上报的原始 Input 事件数据,确认底层是否正常报点。输出格式为 `[device] type code value`,其中 type=3 (EV_ABS) 对应触摸坐标。如果这里看不到事件,问题在硬件或内核驱动层。
2. **`adb shell dumpsys input`**:查看 Input 系统运行时信息。重点关注 `RecentQueue`(最近分发的事件)、`InboundQueue`(待处理事件)、`PendingEvent`(等待 App 反馈的事件)、以及每个窗口 `Connection` 的 `status`。如果 `status` 显示 `NOT_RESPONDING`,说明 App 已经触发 Input ANR。
3. **fd / 内存状态**:窗口添加失败但 `iq/oq/wq` 不明显时,检查进程 fd 数、`logcat` 里的 `EMFILE` / `ENFILE` / `ENOMEM`,判断是否卡在 `InputChannel` 创建阶段。
4. **`adb shell input keyevent / motionevent`**:模拟按键或触摸事件,直接注入到 `InputDispatcher`,绕过底层硬件。用于验证分发逻辑是否正常(排除硬件问题)。
5. **Perfetto Trace**:分析复杂 Input 问题最强大的工具。关键 Track:`iq/oq/wq` 三个队列计数器、`deliverInputEvent`(App 处理耗时)、`InputReader` 和 `InputDispatcher` 线程活动。定位思路:`iq` 堆积 -> InputDispatcher 处理慢;`oq` 堆积 -> 连接繁忙;`wq` 堆积 -> App 处理不及时(ANR 前兆)。
6. **`adb shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'`**:快速确认当前焦点窗口和焦点 App,排查焦点相关的按键事件丢失问题。


### InputFlinger 线程优先级管理演进

Android 早中期版本中,`InputFlinger.cpp` 曾显式设置高优先级:

```cpp
// 旧版 InputFlinger.cpp(Android 7-10 左右)
setpriority(PRIO_PROCESS, 0, -20);  // nice=-20,最高用户态优先级
set_sched_policy(0, SP_FOREGROUND);  // 前台调度策略
```

`nice=-20` 是 Linux 用户态进程的最高优先级(数值越低优先级越高)。`SP_FOREGROUND` 确保 InputFlinger 线程归属 foreground 调度组,获得约 95% 的 CPU 时间片。

后续版本中,这些显式调用被移除,InputFlinger 的高优先级由 `InputThread` 构造时通过 `mThread->run(..., ANDROID_PRIORITY_URGENT_DISPLAY)` 设置(源码锚点:`services/inputflinger/InputThread.cpp`)。`ANDROID_PRIORITY_URGENT_DISPLAY` 对应 nice=-8,高于 foreground 的 nice=0。作为对比,`AudioFlinger` 的 mixer 线程使用 `SCHED_FIFO (priority=2)` 实现实时调度,InputFlinger 不使用实时调度策略,以避免抢占关键系统路径。

### AnrTracker 的超时驱动机制(Android 12+)

`AnrTracker`(`services/inputflinger/dispatcher/AnrTracker.cpp`)从 Android 12 起已存在,实现是按 timeout 排序的容器(`std::multimap`),提供 `insert` / `erase` / `eraseToken` / `firstTimeout` / `firstToken` 接口。它用最早超时时间驱动下一次 ANR 检查--`processAnrsLocked()` 只需检查 `mAnrTracker` 中最早到期的时间点,如果已过期就触发 ANR 流程。

```cpp
// AnrTracker 核心:按超时时间排序,最早到期的在最前面
// dispatch 时插入
mAnrTracker.insert(dispatchEntry->timeoutTime, connection->inputChannel->getConnectionToken());

// processAnrsLocked 中检查最早的超时
nsecs_t nextTimeout = mAnrTracker.firstTimeout();
if (nextTimeout <= currentTime) {
    // 有连接超时,触发 ANR
}
```

动态超时更新:窗口超时时间变更时,AnrTracker 保留已派发事件的原始超时值--已派发事件按原超时处理,新事件按新超时处理。这个机制在 Android 12-16 之间保持稳定。

> [未验证: InputFlinger priority setpriority 移除的具体 commit 版本]

## 延伸阅读

### Android Input/Touch/Scroll 性能与延迟深度调研
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android Input:Touch:Scroll 性能与延迟深度调研 —— 服务 SmartPerfetto 分析 Skill.md
- 类型：DeepResearch 调研结果
- 摘要：完整剖析 Android input 链路跨进程流水线：硬件中断→内核 evdev→InputReader/InputDispatcher(socketpair)→App InputChannel→ViewRootImpl InputStage 责任链→Choreographer CALLBACK_INPUT。量化 input latency 三种口径，给出触摸 resampling 精确常量（RESAMPLE_LATENCY=5ms 等）、MotionPredictor TFLite 模型细节、FrameTimeline jank_type 归因 SQL。面向 SmartPerfetto 技能开发提出 framework input 链路 slice 识别与 jank 归因 SQL 方案。
- 注入时间：2026-06-02
- 价值：Input 链路全栈剖析含 socketpair 机制、resampling 常量、MotionPredictor TFLite 细节，对 AIW 输入章节有直接技术补充
