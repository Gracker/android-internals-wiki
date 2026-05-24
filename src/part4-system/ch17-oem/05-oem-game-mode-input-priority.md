---
title: "OEM 游戏模式输入优先级与触控调度"
chapter: "17.5"
status: ready-for-review
drafted_date: "2026-05-17"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-17"
last_verified_against: "AOSP android-15.0.0_r1; Android Developers Game Mode API; Android ViewGroup touch docs"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/app/GameManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/RefreshRatePolicy.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowState.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewGroup.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/WindowManager.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api"
  - type: official
    path: "https://developer.android.com/develop/ui/views/touch-and-input/gestures/viewgroup"
  - type: research
    path: "DeepResearch/2026-05-12-oem-game-mode-input-priority-research.md"
tags: [oem, game-mode, input, touch-latency, refresh-rate, perfetto]
related_chapters: ["3.5", "3.9", "8.9", "17.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "研究素材/AOSP结构/官方文档"
gap_score: 17
material_count: 3
source_refs:
  - "DeepResearch/2026-05-12-oem-game-mode-input-priority-research.md"
  - "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/app/GameManagerService.java"
  - "https://cs.android.com/android/platform/superproject/+/master:frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - "https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api"
---

# 17.5 OEM 游戏模式输入优先级与触控调度

本节处理一个容易误判的归因问题：厂商游戏模式让触控变跟手，收益到底来自输入分发、刷新率、提频，还是触控固件。AOSP 的公开代码能证明一件事：标准 Game Mode 没有一条独立的“游戏输入优先级”通道。能落到证据上的分析，要把焦点窗口、View 层拦截、帧率选择、Power HAL 和厂商私有改动分开看。

## AOSP Game Mode 的能力边界

Android 12 引入的 Game Mode API 主要解决“用户为某个游戏选择性能 / 省电 / 标准模式后，游戏和系统怎样拿到这个状态”。公开 SDK 侧，游戏通过 `GameManager#getGameMode()` 查询当前模式；官方文档要求游戏在 `onResume()` 重新读取，避免前后台切换后沿用旧状态。[已验证: 官方文档, developer.android.com/games/optimize/adpf/gamemode/gamemode-api]

AOSP 服务端的职责也集中在模式管理、配置读取、状态上报和功耗提示。下面这段代码用于确认 `GameManagerService` 能做什么，重点看 `GAME_MODE_PERFORMANCE` 和 `Mode.GAME_LOADING` 两处。

```java
// frameworks/base/services/core/java/com/android/server/app/GameManagerService.java
final boolean boostEnabled =
        getGameMode(packageName, userId) == GameManager.GAME_MODE_PERFORMANCE;

mPowerManagerInternal.setPowerMode(Mode.GAME_LOADING, isLoading);
```

这段逻辑说明两层边界：`GAME_MODE_PERFORMANCE` 是模式条件，`Mode.GAME_LOADING` 是加载阶段的功耗提示。代码里没有把某个游戏包名传给 `InputDispatcher`，也没有修改输入事件在 system_server 或 inputflinger 中的排队规则。[已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/app/GameManagerService.java]

因此，“游戏模式提升输入优先级”不能直接写成 AOSP Game Mode 的标准能力。更稳的表述是：Game Mode 让游戏和系统拿到用户偏好；设备厂商可在 HAL、内核调度、触控固件或系统服务里叠加私有策略；私有策略需要用 trace、日志或厂商源码单独证明。详见 §8.9 对 Game Mode / Game State / OEM interventions 的边界拆分。

## 焦点窗口与 InputDispatcher 分发路径

AOSP 的输入分发先回答“这次事件应该给哪个窗口”。按键和非触摸事件走焦点窗口；触摸事件走命中测试和 touch state，手指按下后同一个 pointer stream 会沿着已记录的目标窗口继续分发。这里的判断来源是窗口焦点、触点坐标、窗口 flags 和安全策略，不是 Game Mode。

下面这段 `InputDispatcher.cpp` 用来定位非触摸事件的目标窗口。

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
sp<WindowInfoHandle> focusedWindow =
        findFocusedWindowTargetLocked(currentTime, *entry, nextWakeupTime,
                                      /*byref*/ injectionResult);

addWindowTargetLocked(focusedWindow, InputTarget::DispatchMode::AS_IS,
                      InputTarget::Flags::FOREGROUND, getDownTime(*entry),
                      inputTargets);
```

触摸事件则进入 `findTouchedWindowTargetsLocked()`。新手指按下时，InputDispatcher 根据显示、坐标和窗口栈找目标窗口；后续 move / up 继续使用 touch state，保证同一段手势不会在窗口之间乱跳。[已验证: AOSP android-15.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

游戏窗口获得焦点后，自然会成为按键、手柄、部分非触摸事件的目标；触摸落在游戏窗口内时，也会成为该 pointer stream 的目标。这是标准窗口路由，不等同于“游戏模式给了输入线程特殊优先级”。如果 trace 显示 `InputDispatcher` 队列很短、目标窗口 ACK 很快，而用户仍感觉慢，原因通常在应用消费、渲染提交或 present 阶段，详见 §3.9。

## 帧率优先级如何影响触摸到显示延迟

很多“游戏触控更快”的体感来自呈现阶段，而不是输入事件更早到达 App。Android 的刷新率选择会参考窗口的焦点和 `preferredDisplayModeId`，然后把 frame rate selection priority 写到 `SurfaceControl`，交给图形栈做刷新率决策。

下面这段代码用于确认帧率优先级的语义，重点看 `LAYER_PRIORITY_FOCUSED_WITH_MODE` 的注释和 `setFrameRateSelectionPriority()`。

```java
// frameworks/base/services/core/java/com/android/server/wm/RefreshRatePolicy.java
/** Windows that are in focus and voted for the preferred mode ID have the highest priority. */
static final int LAYER_PRIORITY_FOCUSED_WITH_MODE = 0;

// frameworks/base/services/core/java/com/android/server/wm/WindowState.java
final int priority = refreshRatePolicy.calculatePriority(this);
getPendingTransaction().setFrameRateSelectionPriority(mSurfaceControl,
        mFrameRateSelectionPriority);
```

这个优先级影响的是显示刷新率选择，不是输入事件队列。游戏窗口请求 120Hz 或 144Hz 后，单帧间隔从 16.67 ms 降到 8.33 ms / 6.94 ms，应用和 SurfaceFlinger 等下一次 present 的时间变短，端到端触摸反馈可能因此下降一帧。但如果主线程、渲染线程或 GPU 队列已经堵住，高刷不会让 `MotionEvent` 更早出队。[已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/RefreshRatePolicy.java; frameworks/base/services/core/java/com/android/server/wm/WindowState.java]

排查时要把两件事分开写：

- **输入分发延迟**：`InputDispatcher` 到目标窗口 ACK 的时间，反映事件是否及时交给 App。
- **触摸到显示延迟**：从输入样本到新画面 present 的时间，受 Choreographer、渲染提交、BufferQueue、SurfaceFlinger 和刷新率共同影响。

详见 §2.18、§3.9 和 §8.9。§17.5 只讨论厂商游戏模式下这些机制怎样叠加。

## 游戏 View 如何保证触摸序列完整

游戏里的摇杆、滑动瞄准、连招区域通常要求同一段触摸序列完整送到游戏 View。AOSP 提供的是 View 层的拦截协商：子 View 调用 `requestDisallowInterceptTouchEvent(true)` 后，父 `ViewGroup` 不再通过 `onInterceptTouchEvent()` 抢走后续事件。

下面这段代码用于确认 `FLAG_DISALLOW_INTERCEPT` 的作用范围。

```java
// frameworks/base/core/java/android/view/ViewGroup.java
@Override
public void requestDisallowInterceptTouchEvent(boolean disallowIntercept) {
    if (disallowIntercept) {
        mGroupFlags |= FLAG_DISALLOW_INTERCEPT;
    } else {
        mGroupFlags &= ~FLAG_DISALLOW_INTERCEPT;
    }
    if (mParent != null) {
        mParent.requestDisallowInterceptTouchEvent(disallowIntercept);
    }
}

final boolean disallowIntercept = (mGroupFlags & FLAG_DISALLOW_INTERCEPT) != 0;
if (!disallowIntercept || isBackGestureInProgress) {
    intercepted = onInterceptTouchEvent(ev);
} else {
    intercepted = false;
}
```

这段代码解决的是 App 内部 View 层“父容器是否拦截事件”的问题。它不能改变 `InputDispatcher` 的调度优先级，也不能绕过窗口焦点、安全策略或系统手势。游戏引擎使用 `GameActivity`、`SurfaceView`、Unity / Unreal native input queue 时，也仍然要遵守窗口焦点、surface 生命周期和系统手势边界。[已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/view/ViewGroup.java] [已验证: 官方文档, developer.android.com/develop/ui/views/touch-and-input/gestures/viewgroup]

工程上，这个 API 适合处理三类问题：

- **滑动控件抢事件**：游戏区域嵌在 `ViewPager2`、抽屉或自定义父容器里，父容器在 move 阶段拦截，导致摇杆或拖拽中断。
- **手势序列断裂**：down 在子 View，move / up 被父容器接管，游戏状态机收不到完整序列。
- **系统手势例外**：返回手势、隐私敏感窗口和系统级 gesture exclusion 不属于普通父子 View 拦截，不能靠这个 API 全部解决。

## OEM 专有输入优化的验证路径

厂商游戏模式可能改的层级很多，不能只看宣传词。下面这张表把可验证入口和证据类型放在一起，写报告时按证据强度归因。

| 层级 | 可能改动 | 可验证证据 | 归因边界 |
|---|---|---|---|
| 触控固件 / 驱动 | 提高采样率、降低滤波窗口、改变报点策略 | 触控 IC 日志、`getevent -lt` 报点间隔、厂商内核节点 | 影响原始样本到达 Android 的时间，不证明 InputDispatcher 优先级变化 |
| inputflinger / WMS | 调整 `InputDispatcher.cpp`、焦点策略、窗口 flags 或 ANR 超时 | 厂商 framework diff、符号表、trace 中 dispatcher 队列变化 | 无公开源码时标 `[待验证]` |
| Power HAL / vendor daemon | 触摸 boost、游戏包名提频、渲染线程或输入线程 uclamp 调整 | `sched`、`freq`、`power` trace，vendor service 日志 | 能解释调度延迟下降，不等于输入分发规则改变 |
| SurfaceFlinger / 刷新率 | 锁高刷、提高游戏 layer 的刷新率投票权重 | `SurfaceFlinger` trace、FrameTimeline、display mode 切换日志 | 影响 present 等待和帧节奏，不直接改变 `MotionEvent` 出队 |
| 游戏工具服务 | 游戏空间、悬浮面板、触控防误触、录屏旁路 | 包名、服务日志、`dumpsys window/input`、系统设置开关 | 属于 OEM 产品策略，需要按设备记录 |

公开 AOSP 只能证明标准路径没有通用的“游戏输入优先级 API”。如果某台设备打开游戏模式后 `InputDispatcher` 队列出现下降，结论应写成“该设备的厂商实现降低了输入分发等待”，并补上设备型号、系统版本、游戏模式开关、trace 对照和可复现脚本。[待验证: 各厂商 `InputDispatcher.cpp` / `WindowManagerService` / Power HAL 私有实现]

## Perfetto 实机验证口径

验证游戏模式时，最好做成 A/B 对照，而不是只抓一条 trace。推荐四组样本：

1. **基线**：关闭厂商游戏面板，固定刷新率、亮度、温度、网络和游戏画质。
2. **标准 Game Mode**：只切 `adb shell cmd game mode standard|performance|battery <PACKAGE>`，不打开厂商面板。
3. **游戏自身策略**：游戏读取 `getGameMode()` 后调整目标帧率或画质，记录引擎侧参数。
4. **OEM 面板**：打开厂商游戏模式、触控增强、插帧或高刷锁定，其他条件保持一致。

采集项建议覆盖 `input`、`view`、`wm`、`sched`、`freq`、`power`、`gfx`、`SurfaceFlinger` 和 FrameTimeline。判断顺序如下：

- **先看输入交付**：`InputDispatcher` 是否出现 wait queue、目标窗口 ACK 是否变慢、`android.input` stdlib 里的 dispatch latency 是否下降。
- **再看线程调度**：游戏主线程、RenderThread、native game thread、GPU driver 线程的 runnable 到 running 间隔是否减少，CPU 频率和 uclamp 是否同步变化。
- **再看呈现阶段**：FrameTimeline 是否少了一帧 present 延迟，SurfaceFlinger 是否切到更高刷新率，BufferQueue 是否还在堆积。
- **归因**：输入队列下降才讨论输入分发侧收益；present 等待下降写成渲染呈现收益；CPU 频率上升写成功耗 / 调度策略收益。

这套口径能避免一个误判：游戏模式打开后手感变好，就把所有收益写成“InputDispatcher 优先级提升”。端到端延迟下降可能来自更短的 VSync 间隔、加载阶段提频、触控采样率提高、渲染队列减少，也可能来自厂商私有输入路径。没有对应证据时，按 `[待验证]` 处理。

## GameService 与厂商游戏工具服务

Android 的 Game Service / GameSession 能让 OEM 游戏工具与游戏场景协作，例如展示悬浮面板、录屏、性能信息或游戏控制入口。它是产品集成接口，不是输入系统的优先级接口。厂商游戏空间如果提供“触控增强”“防误触”“肩键映射”等功能，通常会走系统应用、特权权限、vendor daemon 或硬件节点，不能把这些能力归到公开 Game Service API 上。[待验证: 各 OEM GameServiceProvider 与游戏空间服务的具体实现]

写技术报告时可按三层描述：

- **公开 API 层**：`GameManager#getGameMode()`、`GameManager#setGameState()`、Game Service / GameSession。
- **系统策略层**：Power HAL、刷新率选择、Game Mode interventions、ADPF。
- **厂商产品层**：游戏空间、触控增强、防误触、肩键、录屏和网络加速。

三层混写会让读者以为 Android SDK 提供了输入优先级开关，后续排障会走错方向。

## 多窗口、折叠屏与外设输入

多窗口、自由窗口、桌面模式和折叠屏会改变焦点、显示和输入设备的组合。游戏不再一定占满主显示，外接手柄、键鼠、触控板也不完全走同一套触摸命中逻辑。

排查这类场景时，先记录四个事实：

- **焦点窗口**：`dumpsys window` 里的 focused window 是游戏、系统面板，还是外接显示上的另一个窗口。
- **目标显示**：输入事件带的 displayId 是否和游戏 Surface 所在显示一致。
- **输入设备类型**：触摸、手柄、鼠标、键盘、触控板分别走不同的分发分支，不能混用同一套触摸延迟结论。
- **窗口模式**：自由窗口、PIP、分屏和折叠态会改变窗口 bounds，触摸命中结果可能和全屏模式不同。

如果多窗口下游戏模式收益消失，优先检查焦点窗口、display mode vote 和厂商游戏空间是否只对全屏游戏包名生效。外设输入出现延迟时，按键 / 手柄更接近焦点窗口路径，鼠标和触控板还要看 pointer capture、hover、光标合成和应用自己的输入处理。

## 参考资料

- [来源: DeepResearch/2026-05-12-oem-game-mode-input-priority-research.md]
- [已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/app/GameManagerService.java]
- [已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/RefreshRatePolicy.java]
- [已验证: AOSP android-15.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/WindowState.java]
- [已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/view/ViewGroup.java]
- [已验证: AOSP android-15.0.0_r1, frameworks/base/core/java/android/view/WindowManager.java]
- [已验证: AOSP android-15.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]
- [已验证: 官方文档, developer.android.com/games/optimize/adpf/gamemode/gamemode-api]
- [已验证: 官方文档, developer.android.com/develop/ui/views/touch-and-input/gestures/viewgroup]
- [交叉引用: §3.5 输入事件拦截与安全机制]
- [交叉引用: §3.9 端到端输入延迟预算与感知阈值]
- [交叉引用: §8.9 Android 游戏性能与 Game Mode/State API]
- [交叉引用: §17.2 SoC 平台差异]

### 厂商游戏模式输入优先级机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-24-android-game-mode-input-priority-mechanism.md
- 类型：DeepResearch 调研结果
- 摘要：AOSP InputDispatcher 无原生游戏模式概念，输入优先级依赖 TouchFocus + Policy Interface 扩展点。厂商通过 override notifyWindowResponsive()/interceptInput() 检测游戏窗口并重定向输入，或利用 injectInputEvent ASYNC 模式实现零延迟注入。TouchFocus 按 Z-order 最高窗口确定。
- 注入时间：2026-05-25
- 价值：AOSP 标准机制源码锚定（InputDispatcher TouchFocus、Policy扩展点、injectInputEvent），补全厂商实现典型路径

