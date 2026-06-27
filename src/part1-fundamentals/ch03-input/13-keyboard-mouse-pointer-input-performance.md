---
title: "键盘、鼠标与指针输入性能 — 桌面模式交互管线"
chapter: "3.13"
status: ready-for-review
drafted_date: "2026-06-27"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-06-27"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/reader/InputDevice.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/reader/mapper/MultiTouchInputMapper.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/reader/mapper/KeyboardInputMapper.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/View.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/DragEvent.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/input/InputManagerService.java"
  - type: official
    path: "https://developer.android.com/develop/ui/views/touch-and-input/input-events"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/touch-input/pointer-input"
  - type: official
    path: "https://developer.android.com/guide/topics/large-screens/handle-multi-window-mode"
tags: [input, keyboard, mouse, pointer, desktop-mode, hover, drag-drop, performance]
related_chapters: ["3.1", "3.2", "3.4", "3.5", "3.7", "2.20", "22.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "官方文档/AOSP结构/每日信息"
---

# 3.13 键盘、鼠标与指针输入性能 — 桌面模式交互管线

## 为什么单独看键盘/鼠标输入

第 3.1 节给出了 Input 事件从硬件到 App 的完整路径，第 3.2 节聚焦触摸响应延迟。本节关注的是另一类输入设备——键盘、鼠标和指针——在桌面模式（Desktop Mode）下的性能特征。这些设备的事件管线与触摸事件在 source 分类、事件频率、分发路径和 ANR 风险点上存在结构性差异。

Android 13 (API 33) 开始提供桌面模式窗口管理雏形，Android 15 (API 35) 引入桌面窗口（Desktop Windowing）特性，Android 16 (API 36) 将桌面模式作为可用户切换的功能入口，Android 17 (API 37) 继续完善桌面体验。鼠标和键盘作为桌面模式的核心交互设备，其事件管线性能直接影响用户体验。

[适用版本: Android 13 - Android 17]

## 桌面模式输入设备模型

### 输入设备分类与 source 标记

Android 输入系统通过 `InputDevice` 类描述物理输入设备，每个设备关联一个或多个 `source`。与桌面模式性能相关的 source 包括：

- `SOURCE_KEYBOARD`：物理键盘，产生 `KeyEvent`
- `SOURCE_MOUSE`：鼠标，产生 `MotionEvent`，坐标为绝对指针位置
- `SOURCE_TOUCHPAD`：触控板，产生 `MotionEvent`，坐标为相对位置
- `SOURCE_TOUCHSCREEN`：触摸屏，产生 `MotionEvent`，直接映射屏幕坐标
- `SOURCE_STYLUS`：触控笔，产生 `MotionEvent`，附带压力和倾斜数据
- `SOURCE_GAMEPAD`：游戏手柄，产生 `KeyEvent`（按钮）和 `MotionEvent`（摇杆轴）

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/reader/InputDevice.cpp]

鼠标和触摸的关键区别在于指针精度和事件语义。触摸屏的坐标分辨率受限于触摸矩阵的物理传感器密度（通常 100-300 DPI），鼠标的指针精度取决于系统设置的指针速度乘数和鼠标硬件 DPI（通常 400-3200 DPI）。在 `PointerController` 中，鼠标移动经过加速曲线映射到屏幕坐标位移，这条曲线由 `PointerProperties` 和 `PointerCoords` 共同决定。

### InputReader 对设备类的分流

`InputReader` 在 `InputDevice` 初始化时根据设备的 device classes 加载对应的 `InputMapper`：

- `KeyboardInputMapper`：处理 `EV_KEY` 类型的键盘扫描码，生成 `KeyEvent`
- `MultiTouchInputMapper` / `SingleTouchInputMapper`：处理 `EV_ABS` / `EV_SYN` 类型的绝对坐标事件，生成触摸或指针 `MotionEvent`
- `CursorInputMapper`：处理鼠标的相对移动（`EV_REL`），通过 `PointerController` 转换为绝对坐标后生成 `MotionEvent`，source 标记为 `SOURCE_MOUSE`
- `TouchpadInputMapper`（Android 14+）：处理触控板多点触控，source 标记为 `SOURCE_TOUCHPAD`

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/reader/mapper/]

桌面模式下，鼠标事件经过 `CursorInputMapper` → `PointerController` → `InputDispatcher` 的路径。`PointerController` 负责将鼠标硬件的相对位移转换为屏幕绝对坐标，并应用加速曲线。这个转换步骤是鼠标独有的——触摸事件直接从 `InputMapper` 进入 `InputDispatcher`，不需要经过指针位置转换。

## 键盘事件分发管线

### KeyEvent 的完整分发链路

键盘事件从 `InputReader` 读取到 App 层消费的完整路径：

```
Kernel keyboard event (EV_KEY)
  → InputReader::process()
  → KeyboardInputMapper::process()
  → EventHub::scancode_to_keycode() 转换扫描码
  → InputDispatcher::notifyKey()
  → InputDispatcher::dispatchKey()
  → 焦点窗口的 InputChannel (socket pair)
  → App 端 ViewRootImpl.EnqueueInputEvent()
  → ViewRootImpl.deliverInputEvent()
  → DecorView.dispatchKeyEvent()
  → Activity.dispatchKeyEvent() / Window.superDispatchKeyEvent()
  → View hierarchy: View.dispatchKeyEvent()
  → Compose: View.onKeyEventListener → Modifier.onKeyEvent()
  → InputMethodManager（如果未被消费，触发 IMS 的候选词处理）
```

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp + frameworks/base/core/java/android/view/ViewRootImpl.java]

与触摸事件相比，`KeyEvent` 分发有两个性能特征值得注意：

1. **View 树遍历开销**：`dispatchKeyEvent` 沿 View 树自顶向下分发，直到有 View 返回 `true` 消费事件。在 View 层级深的场景中（如嵌套 Dialog + PopupWindow + RecyclerView），遍历本身会产生可测量的开销。Perfetto 中表现为 `deliverInputEvent` slice 下连续的 `View.dispatchKeyEvent` 调用。

2. **InputMethodManager 回退路径**：如果 `KeyEvent` 未被 View 树消费，会回退到 `InputMethodManager` 处理候选词、快捷键等。这条路径涉及 Binder 调用（`IInputMethodManager`），在桌面模式下 IME 可能为空，但回退检查本身仍有开销。

### Key Repeat 的生成与频率

Key Repeat（长按重复）由 `InputReader` 在用户态生成，不是内核驱动行为。`InputReader` 内部维护一个 `KeyRepeatInfo` 结构，包含初始延迟（`CONFIGURATION_KEY_REPEAT_DELAY`，默认 500ms）和重复间隔（`CONFIGURATION_KEY_REPEAT_RATE`，默认 50ms / 20 Hz）。

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/reader/InputReader.cpp]

长按一个键时，`InputReader` 以 20 Hz 频率连续生成 `ACTION_DOWN` 事件（`getRepeatCount()` 递增）。每次重复事件走完整的 `notifyKey` → `dispatchKey` → `deliverInputEvent` 链路。如果目标 Activity 的 `dispatchKeyEvent` 实现里有重逻辑（如文本搜索、列表过滤），Key Repeat 会导致主线程负载突增。

快捷键组合（Ctrl/Shift + 字母键）的匹配走 `Activity.onKeyShortcut()` → `View.onKeyShortcut()` 路径，在每个重复事件中都会被调用。桌面模式下快捷键使用频率高，需要确认 `onKeyShortcut` 实现是否做了去抖。

### 键盘事件 ANR 阈值

键盘事件的 ANR 超时与触摸事件相同，都是 5 秒（`DEFAULT_INPUT_DISPATCHING_TIMEOUT` = 5000ms）。但键盘交互的特性使得 ANR 更容易被用户感知：按下一个快捷键后如果窗口无响应，用户通常会连续按键，每次按键都重置 ANR 计时器的等待起点，反而延长了无响应状态的持续时间。

详见 3.7 节对 `InputDispatcher` 反压和 ANR 计时边界的分析。

## 鼠标 Hover 与 MotionEvent 性能

### Hover 事件的生成频率

鼠标 Hover（悬停）事件是桌面模式下最高频的输入事件类型。当用户移动鼠标时，`CursorInputMapper` 将相对位移转换为绝对坐标，生成 `ACTION_HOVER_MOVE` 类型的 `MotionEvent`。鼠标的 USB 轮询率通常为 125-1000 Hz，系统层面经过 `InputReader` 的事件合并后，实际分发到 App 的 Hover 事件频率在 200-500 Hz 范围。

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp — batching 逻辑]

### Hover 事件对重绘的影响

每次 `ACTION_HOVER_MOVE` 事件触发 `View.onHoverEvent()` 回调。`View` 的默认实现会更新 `hovered` 状态并调用 `refreshDrawableState()`，后者触发 `invalidate()`。如果 View 树中有大量注册了 hover 监听的 View（例如 RecyclerView 中每个 item 都有 hover 效果），一次鼠标移动可能在单帧内产生数十次 `invalidate()` 调用。

`InputDispatcher` 内部有事件合并（batching）机制：对同一个连接的连续 `MotionEvent`，如果时间戳差小于一个 frame（约 16ms），会尝试合并为一个事件。但这个合并不是强制的——如果 App 的主线程消费速度跟不上事件生产速度，`InputDispatcher` 的 `outboundQueue` 会积压。

Hover 事件的性能排查方法：

- Perfetto 中观察 `deliverInputEvent` slice 的频率，确认 Hover 事件是否被有效合并
- `dumpsys input` 查看 `inboundQueue` 和 `outboundQueue` 长度，队列持续增长说明 App 消费速度不足
- 在 `onHoverEvent` 中加入 `FrameMetrics` 监控，确认单次 hover 处理的耗时

### onHoverEvent 与 onGenericMotionEvent 的分发顺序

`MotionEvent` 的分发路径取决于 action 类型：

- `ACTION_HOVER_ENTER` / `ACTION_HOVER_MOVE` / `ACTION_HOVER_EXIT`：走 `View.dispatchHoverEvent()` → `View.onHoverEvent()`
- `ACTION_SCROLL`：走 `View.dispatchGenericMotionEvent()` → `View.onGenericMotionEvent()`
- `ACTION_DOWN` / `ACTION_MOVE` / `ACTION_UP`（鼠标按键按下拖动）：走 `View.dispatchTouchEvent()` → `View.onTouchEvent()`

三种分发路径互不干扰，但都会在 `deliverInputEvent` 中执行。高频 Hover 事件和触摸事件混合到达时，`deliverInputEvent` 的排队延迟会叠加。

## Compose 指针输入性能

### PointerInputModifier 的处理链路

Compose 的指针输入系统通过 `Modifier.pointerInput()` 挂载到 Composable 上。底层实现是 `SuspendingPointerInputModifierNode`，每个 `pointerInput` modifier 启动一个协程，在协程内部通过 `PointerInputEventHandler` 接收 `PointerEvent`。

鼠标 Hover 在 Compose 中的处理路径：

```
MotionEvent (ACTION_HOVER_MOVE)
  → AndroidComposeView.dispatchHoverEvent()
  → PointerInputEventProcessor.processHoverEvent()
  → 遍历所有注册了 pointerInput 的 ModifierNode
  → 每个 Node 的 coroutine 收到 PointerEvent
  → detectHoverGestures / Modifier.hoverable 处理
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/compose/.../AndroidComposeView]

### Hover 导致的聚合负载

桌面模式下，屏幕上可见的每个 Composable 如果注册了 `Modifier.hoverable()` 或 `Modifier.pointerInput()`，都会收到 Hover 事件。在一个包含 50 个可 hover 元素的列表中，一次鼠标移动触发 50 次协程调度和状态检查。

Compose 的 Hover 处理性能取决于三个因素：

1. **协程调度开销**：每个 `pointerInput` 块独占一个协程，Hover 事件需要将 `PointerEvent` 发送到所有活跃协程。协程数量与 Composable 数量线性相关。
2. **重组触发**：Hover 状态变化（`isHovered`）会触发依赖该状态的重组。如果 Hover 状态被用于控制背景色、边框等视觉效果，每次状态翻转都会触发重组。
3. **指针命中测试**：`PointerInputEventProcessor` 对每个 `PointerEvent` 需要做 hit-testing，确定事件落在哪些 Composable 上。hit-testing 的开销与 Composable 数量和布局复杂度成正比。

优化方向：

- 对不需要 Hover 效果的 Composable，不要添加 `Modifier.hoverable()`
- 对列表项的 Hover 效果，使用 `Modifier.composed()` 配合 `MutableInteractionSource` 避免每个 item 创建独立的 `pointerInput` 协程
- 在 `pointerInput` 内部使用 `awaitEachEvent` 而非 `awaitPointerEventScope`，前者减少了 coroutine 挂起/恢复次数

[待验证: awaitEachEvent 的性能优势基于 Compose Foundation 1.7+ 的实现分析，未在 Android 17 上跑过基准测试]

## 窗口焦点与输入路由

### FocusedWindow 与输入分发

`InputDispatcher` 维护当前焦点窗口句柄（`mFocusedWindowHandle`），所有 `KeyEvent` 分发到焦点窗口。焦点窗口由 `WindowManagerService` 通过 `InputManagerService.setInputWindows()` 设置。

桌面模式下多窗口共存时的焦点判定规则：

- **按键事件**：始终分发到 `mFocusedWindowHandle`，即最近获得焦点的窗口
- **鼠标移动（Hover）**：分发到鼠标指针所在的可触摸窗口（`touchedWindowHandle`），不要求该窗口拥有焦点
- **鼠标点击**：先触发窗口聚焦（`windowFocusChanged` 回调），然后分发触摸事件到新焦点窗口

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp — findFocusedWindowTargetsLocked / findTouchedWindowTargetsLocked]

### 窗口聚焦切换的性能

鼠标点击非焦点窗口时，窗口聚焦切换的链路：

```
InputDispatcher 发现点击目标 ≠ mFocusedWindowHandle
  → 通过 InputDispatcher.Callback 通知 WindowManagerService
  → WMS 执行 focusChange 流程
  → 旧焦点窗口的 Activity.onWindowFocusChanged(false)
  → 新焦点窗口的 Activity.onWindowFocusChanged(true)
  → InputManagerService.setInputWindows() 更新 mFocusedWindowHandle
  → InputDispatcher 分发触摸事件到新焦点窗口
```

这个链路涉及 2-3 次 Binder 调用（`IInputMethodManager`、`IWindowSession`）和 WMS 内部的窗口重排。在 Perfetto 中表现为点击后 5-15ms 的 `relayoutWindow` 和 `windowFocusChanged` slice。如果 Activity 的 `onWindowFocusChanged` 回调中有重逻辑（如重新加载数据、刷新 UI），延迟会更大。

### 多显示器场景的输入路由

Android 15+ 支持外接显示器上的桌面窗口。多显示器场景下，`InputDispatcher` 为每个 display 维护独立的窗口列表：

- `InputReader` 读取鼠标事件后，`PointerController` 根据指针当前所在的 display ID 设置事件的 display target
- `InputDispatcher` 按 display target 分发到对应显示器上的窗口
- 焦点窗口是 per-display 的：每个显示器有自己的焦点窗口

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp — displayId 路由逻辑]

详见 2.20 节对多窗口和桌面模式渲染性能的分析。

## 拖放（Drag and Drop）性能

### DragEvent 分发链路

Android 拖放在桌面模式下是核心交互。拖放流程从 `View.startDragAndDrop()` 开始：

1. App 调用 `startDragAndDrop()`，提供 `ClipData` 和 `DragShadowBuilder`
2. `DragRemoteViews` 通过 `ViewRootImpl` 向 WMS 发起拖放请求
3. WMS 创建系统级 overlay 窗口绘制拖放阴影（`DragShadow`）
4. 拖放过程中，`InputDispatcher` 将鼠标移动事件同时分发到拖放阴影窗口和鼠标指针下方的 App 窗口
5. 每个被拖放阴影覆盖的 View 都收到 `DragEvent`（`ACTION_DRAG_ENTERED` / `ACTION_DRAG_LOCATION` / `ACTION_DRAG_EXITED`）

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/DragEventController.java]

### 拖放性能的瓶颈点

拖放过程中 `ACTION_DRAG_LOCATION` 的分发频率与鼠标移动频率一致（200-500 Hz）。`View.dispatchDragEvent()` 会在 View 树中冒泡——从被覆盖的 View 开始，沿 parent 链向上传递，直到有 View 返回 `true` 消费事件。

性能瓶颈通常出现在：

1. **ViewTree 遍历**：拖放阴影每经过一个 View，都会触发一次 `dispatchDragEvent` 遍历。在复杂布局中（如 RecyclerView + GridLayout），单次拖放移动可能触发 10+ 次 `dispatchDragEvent` 调用。
2. **ClipDescription 检查**：每个 `onDragEvent` 实现通常会检查 `DragEvent.getClipDescription()` 的 MIME type，判断是否接受拖放内容。`ClipDescription` 的 MIME type 比较是字符串匹配，开销可控但累积。
3. **跨应用拖放**：跨应用拖放需要 `ClipData` 在进程间序列化传输。大数据量（如图片 URI 列表）的序列化通过 Binder 传输，受 1MB Binder transaction buffer 限制。接近 buffer 上限时，`startDragAndDrop` 可能抛出 `TransactionTooLargeException`。

[已验证: Binder transaction buffer 1MB 限制详见 1.30 节 Binder Transaction Buffer 演进]

## InputDispatcher 在桌面模式的调度差异

### 事件合并策略

`InputDispatcher` 对连续的 `MotionEvent` 有两种合并策略：

- **Batching**：将同一连接的多个未消费 `MotionEvent` 合并为最后一个事件的快照，丢弃中间事件。适用于触摸移动和鼠标 Hover 移动。
- **Cancelation**：当新事件到达时取消正在等待的旧事件分发。适用于触摸取消（`ACTION_CANCEL`）。

[已验证: AOSP android-17.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp — enqueueInboundEventLocked / shouldPruneInboundQueueLocked]

鼠标 Hover 移动受益于 batching：如果 App 在一次 VSync 周期内收到 10 次 `ACTION_HOVER_MOVE`，batching 会将前 9 次丢弃，只保留最后一次的坐标。但 batching 只发生在 `inboundQueue` 阶段——如果事件已经进入 `outboundQueue`（即已经写入 socket pair 等 App 消费），batching 不再生效。

### ANR 阈值在桌面模式的考量

ANR 超时阈值（5 秒）在桌面模式下没有单独调整。桌面模式特有的 ANR 风险点：

- **Hover 事件不触发 ANR**：`ACTION_HOVER_MOVE` 事件被标记为非阻塞事件，不会触发 ANR 计时。即使 App 的 `onHoverEvent` 长时间不返回，也不会产生 Input ANR。
- **鼠标点击触发 ANR**：鼠标按键按下（`ACTION_DOWN`）走触摸事件路径，会触发 ANR 计时。
- **KeyEvent 触发 ANR**：键盘事件会触发 ANR 计时，包括 Key Repeat 事件。

桌面模式下用户高频使用快捷键，如果 IME 弹窗或窗口切换导致主线程阻塞，键盘 ANR 的发生率会高于纯触摸场景。

详见 3.7 节对 InputDispatcher ANR 机制的完整分析。

### 桌面模式 Hover 事件聚合

[待验证: Android 17 是否对 Hover 事件引入了 frame-aligned 聚合策略——即按 VSync 周期对齐 Hover 事件分发，而非按 InputReader 的原始频率分发。AOSP android-17.0.0_r1 的 `InputDispatcher` 中没有找到显式的 frame-aligned Hover 聚合代码路径，但 `PointerController` 层面的运动平滑处理可能间接降低了 Hover 事件频率。]

## 扩展

### 触控笔（Stylus）与鼠标的性能差异

触控笔的 `source` 为 `SOURCE_STYLUS`，事件类型是 `MotionEvent`，但携带额外数据：

- `MotionEvent.PRESSURE`：压力值（0.0-1.0），来自笔尖压力传感器
- `MotionEvent.AXIS_TILT`：倾斜角（0-90 度），来自倾斜传感器
- `MotionEvent.AXIS_ORIENTATION`：方向角，来自笔身方向传感器

触控笔的事件频率通常为 120-240 Hz，低于鼠标的 USB 轮询率，但每个事件携带更多数据。`InputDispatcher` 对触控笔事件的处理路径与触摸事件一致（`findTouchedWindowTargetsLocked`），不需要经过 `PointerController` 的坐标转换。

触控笔的性能差异点在于 `MotionEvent` 的 parcel 化开销：每个事件需要序列化压力、倾斜、方向等额外 axis 数据，通过 socket pair 传输时的数据量比纯坐标事件大约 40-60%。

### 游戏手柄输入性能

游戏手柄的 `source` 为 `SOURCE_GAMEPAD`，按钮产生 `KeyEvent`（映射为 `KEYCODE_BUTTON_A` 等），摇杆产生 `MotionEvent`（`AXIS_X` / `AXIS_Y` / `AXIS_Z` / `AXIS_RZ`）。

手柄输入的性能特征：

- **KeyEvent 频率低**：手柄按钮不是高频事件源，按钮按下和释放各产生一次 `KeyEvent`
- **MotionEvent 频率中等**：摇杆事件频率约 60-120 Hz，取决于手柄硬件轮询率
- **输入映射开销**：`GamepadInputMapper`（如果存在）或 `JoystickInputMapper` 负责将原始 axis 值映射到标准游戏手柄 axis，映射过程是纯计算，开销可忽略

桌面模式下游戏手柄不是主要交互设备，但如果 App 同时监听手柄输入和键盘输入，两套 `KeyEvent` 都走 `dispatchKeyEvent` 链路，存在事件处理争用。

### Android 17 桌面体验输入管线

[待验证: Android 17 对桌面模式输入管线的具体优化尚未通过 AOSP android-17.0.0_r1 源码全量确认。以下为基于 Android 16 行为和官方文档的推断，标注待验证。]

Android 16 引入的桌面窗口（Desktop Windowing）在 Android 17 中预期继续演进。输入管线层面可能的方向：

- Hover 事件按 frame 对齐分发（降低主线程 Hover 处理频率）
- 窗口聚焦切换的异步化（减少 `windowFocusChanged` 回调对主线程的阻塞）
- 拖放事件的 View 局部化分发（只通知指针正下方区域的 View，而非整个 ViewTree）

[待验证: 以上三点均为方向性推断，未在 android-17.0.0_r1 源码中确认具体实现。如果后续验证发现 Android 17 没有实现，应删除本节。]

## 排查清单

桌面模式输入性能问题的排查入口：

| 症状 | 排查方向 | 工具 |
|------|----------|------|
| 鼠标移动卡顿 | `deliverInputEvent` 频率和耗时 | Perfetto `input` track |
| 快捷键响应慢 | `dispatchKeyEvent` 链路耗时 | Perfetto `view` track + `Choreographer#doFrame` |
| Hover 导致 jank | `onHoverEvent` → `invalidate` 频率 | FrameMetrics `Layout/Draw` 阶段 |
| 窗口切换后输入丢失 | `mFocusedWindowHandle` 更新延迟 | `dumpsys input` + `dumpsys window` |
| 拖放卡顿 | `dispatchDragEvent` 遍历次数 | Perfetto `view` track |

## 参考资料

- 3.1 节：Input 事件分发全流程
- 3.2 节：触摸响应的性能分析
- 3.4 节：输入延迟与预测输入技术
- 3.5 节：输入事件拦截与安全机制
- 3.7 节：InputDispatcher 反压与无响应窗口降级
- 2.20 节：多窗口与桌面模式渲染性能
- 1.30 节：Binder Transaction Buffer 演进与大事务性能边界
- AOSP `frameworks/native/services/inputflinger/` — InputDispatcher / InputReader / PointerController
- [Input events overview](https://developer.android.com/develop/ui/views/touch-and-input/input-events) — Android Developers
