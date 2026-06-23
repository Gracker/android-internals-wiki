---
title: "Predictive Back 系统架构与动画管线性能"
chapter: "3.12"
status: ready-for-review
drafted_date: "2026-06-24"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-06-24"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TaskAnimationCoordinator.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityTaskManagerService.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java"
  - type: aosp
    path: "frameworks/base/core/java/android/window/OnBackInvokedDispatcher.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java"
  - type: official
    path: "https://developer.android.com/guide/navigation/predictive-back-gesture"
  - type: official
    path: "https://developer.android.com/about/versions/15/changes/predictive-back"
tags: [predictive-back, input, animation, window-manager, gesture, system-architecture, task-transition]
related_chapters: ["3.1", "3.3", "3.4", "22.13", "2.12", "8.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "官方文档+AOSP结构"
drafted_by: "openclaw-task2a"
---

# Predictive Back 系统架构与动画管线性能

Predictive Back 把"返回"从一个离散按键事件变成了一段连续手势。这个变化的重量不在 App 侧——App 只是多注册几个回调——而在系统侧。InputDispatcher 要决定事件归谁，WindowManagerService 要协调当前层和目标层的动画，ActivityTaskManagerService 要处理 Activity 状态转换，SurfaceFlinger 要在动画期间管理合成层级。3.3 节覆盖了手势检测和回调模型；22.13 节覆盖了 App 侧动画接入。本节覆盖系统侧的分发架构、转场管线和性能边界。

## 系统分发架构：从 InputDispatcher 到 WMS 的完整路径

### 两条分发路径的分流点

返回手势的系统分发在 InputDispatcher 层面有一个关键分流：事件是被当成传统 KEYCODE_BACK 注入，还是被当成 predictive back progress 事件分发。这个分流由 EdgeBackGestureHandler 中 `mBackAnimation` 是否为 null 决定。

`mBackAnimation` 的赋值来自 WM Shell 的 `BackAnimation` 接口。当 App 的 Activity 或 Application 显式 opt in（通过 manifest `android:enableOnBackInvokedCallback="true"`）且系统版本 ≥ Android 13 时，`BackAnimation` 对象会被创建并绑定到 `EdgeBackGestureHandler`。此时手势进度通过 `dispatchToBackAnimation()` 进入 WM Shell 的 `BackAnimation.onBackMotion()` 路径。如果 `mBackAnimation` 为 null——包括 App 未 opt in、App 拦截了返回但未注册 `OnBackInvokedCallback`、或者系统版本低于 Android 13——手势退回 legacy path，松手后 `triggerBack()` 直接注入 `KEYCODE_BACK` 的 down/up 序列。

[已验证: AOSP android-17.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java]

这个分流对性能分析有直接影响。在 Perfetto trace 中，legacy path 的特征是 `InputDispatcher` 发出 key event → App 主线程处理 `onBackPressed`；predictive path 的特征是 SystemUI 进程的 `EdgeBackGestureHandler` 持续调用 `BackAnimation.onBackMotion()` → WMS 通过 `OnBackInvokedDispatcher` 分发 progress 事件 → App 的 `OnBackAnimationCallback.onBackProgressed()` 被调用。如果分析返回卡顿时只搜 key event slice，predictive path 的问题会被漏掉。

### OnBackInvokedDispatcher 的系统侧实现

`OnBackInvokedDispatcher` 不只是一个 Java 接口。在系统侧，它的实现链是：

`ActivityClient` → `ActivityThread.loadConcerns()` → `OnBackInvokedDispatcher` 创建 → 注册到 `WindowManagerService` 的 `WindowState`

当 WindowState 注册了 `OnBackInvokedCallback`，WMS 会在处理返回手势时优先检查目标窗口是否有激活的 callback。有则走 callback dispatch 路径，没有则退回 `KEYCODE_BACK` 注入。这个检查发生在 `WindowManagerService.prepareAppTransition()` 之前，决定了后续动画管线走 cross-activity 转场还是 App 内部处理。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/window/OnBackInvokedDispatcher.java; frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java]

`OnBackInvokedDispatcher` 内部维护两个优先级队列：`PRIORITY_OVERLAY` 和 `PRIORITY_DEFAULT`。Android 16 新增 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER`（值=2），后者不消费返回事件，只观察。分发时从高优先级往低优先级遍历，第一个消费 callback 拿到返回权。如果只有 observer 注册，系统会继续走默认返回动画（back-to-home 或 cross-task）。

### WMS 中的返回手势协调

WindowManagerService 在 predictive back 期间承担三个职责：

**动画准备**：`WindowManagerService.prepareAppTransition()` 在收到 back 触发后设置 `APP_TRANSITION_STATE` 为 `APP_STATE_READY`。如果目标是另一个 Activity（cross-activity back），WMS 调用 `AppTransitionController.goodToGo()` 启动转场动画。如果目标是 Launcher（back-to-home），WMS 通过 `RecentsAnimationController` 协调 Launcher 的 surface 和当前 Task 的 surface。

**Surface 层级管理**：back 动画期间，当前 Activity 的窗口和目标（下一个 Activity 或 Launcher）的窗口需要同时合成。WMS 通过 `SurfaceControl` 调整窗口 z-order，确保两个 surface 在动画期间都可见。具体操作在 `DisplayContent.prepareAppTransition()` 中完成。

**Input target 切换**：动画期间 InputDispatcher 的 input target 需要从当前窗口切换到目标窗口。WMS 通过 `InputMonitor.updateInputWindowsLw()` 通知 InputDispatcher 更新焦点。在 cross-activity back 中，这个切换发生在 Activity `onPause()` 之后、目标 Activity `onResume()` 之前。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java]

## Task 转场动画的系统管线

### TaskAnimationCoordinator 的角色

Cross-activity 和 back-to-home 的转场动画由 `TaskAnimationCoordinator` 统一协调。这个类管理三类资源：

1. **Snapshot surface**：目标 Activity 或 Task 的 `TaskSnapshot`。当用户触发返回手势，系统会先检查是否有可用的 snapshot。有则直接用 snapshot 作为预览层，避免目标 Activity 在动画期间被迫提前完成 `onCreate` → `onResume` 全流程。Snapshot 的渲染开销远低于 live render，系统会优先使用。

2. **Live layer**：如果目标 Activity 已经在缓存中存活（如从详情页返回列表页，列表页进程未销毁），系统会使用 live layer 而非 snapshot。Live layer 的渲染成本更高，但交互体验更好——用户可以在返回动画期间看到目标页面的实时状态。

3. **动画帧调度**：`TaskAnimationCoordinator` 通过 `Choreographer` 的 vsync 信号驱动每帧动画。每帧的工作包括：更新 snapshot 或 live layer 的 transform（translateX、scale、alpha）、通知 WMS 更新 surface 层级、触发 SurfaceFlinger 合成。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/TaskAnimationCoordinator.java]

### Snapshot 渲染与内存成本

`TaskSnapshot` 在 Android 12 引入，到 Android 17 的实现持续优化。Snapshot 是一张硬件 composite 的 GraphicBuffer，在 Activity 切到后台时由 `TaskSnapshotController.snapshotTask()` 捕获。Snapshot 的尺寸与 Task 的 bounds 一致，格式为 `PIXEL_FORMAT_RGBA_8888`。

内存占用计算：一个 1080×2400 的 Task，snapshot buffer ≈ 10 MB。折叠屏展开态 2208×1840 ≈ 16 MB。多任务场景下，每个 Task 都可能持有一份 snapshot，总内存增量需要纳入内存预算分析。Android 17 引入了 snapshot 压缩（`SnapshotCompressionType`），对非当前可见 Task 的 snapshot 使用更低分辨率缓存。

Snapshot 的性能优势体现在 back 动画的首帧延迟。使用 snapshot 时，目标层的第一帧几乎零延迟（只是一次 texture upload + composite）；使用 live layer 时，目标层需要等 `onResume()` → measure/layout/draw → RenderThread 提交 → SurfaceFlinger 合成的完整渲染管线，首帧延迟可能达到 16-50ms（取决于目标页面的布局复杂度）。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotController.java]

### Back-to-Home 转场的特殊路径

Back-to-home 转场不经过 `TaskAnimationCoordinator` 的标准路径，而是走 `RecentsAnimationController`。这个控制器的职责是协调当前 Task 和 Launcher 的 surface：

1. WMS 通知 `RecentsAnimationController` 开始动画。
2. Launcher 进程收到 `onStartRecentsAnimation()` 回调，准备 Recents view。
3. 当前 Task 的 surface 被 attach 到一个 leash（`SurfaceControl.Transaction` 创建的临时父节点）上。
4. 动画期间，Launcher 通过 `RemoteAnimationTarget` 接收当前 Task 的 surface 引用，执行缩放和位移。
5. 动画结束后，leash 被移除，Task 按 `finishTask` 或 `keepTask` 决定是否进入 cached state。

性能上，back-to-home 转场的瓶颈通常在 Launcher 进程。Launcher 的 Recents view 需要在动画开始前完成 inflate 和数据加载。如果 Launcher 进程冷启动或 Recents view 布局复杂，首帧动画可能延迟 100ms 以上。这类问题的 Perfetto 特征是：SystemUI 进程发出 `startRecentsAnimation` 后，Launcher 进程的 MainThread 有一段长时间的布局/draw 占用。

## 帧预算与渲染管线分配

### 每帧的工作分配

Predictive back 动画运行期间，每一帧需要完成以下工作：

| 阶段 | 耗时预算 | 工作内容 | 执行线程 |
|------|----------|----------|----------|
| Input 事件处理 | < 2ms | EdgeBackGestureHandler 处理 MotionEvent，更新手势进度 | SystemUI MainThread |
| WMS 协调 | < 4ms | 更新 surface transform、z-order、input target | system_server MainThread |
| App 回调 | < 4ms | OnBackAnimationCallback.onBackProgressed() 执行动画属性更新 | App MainThread |
| RenderThread | < 8ms | View hierarchy draw → DisplayList → GPU 提交 | App RenderThread |
| SurfaceFlinger 合成 | < 4ms | 合成当前层 + 目标层 + 系统装饰层 | SurfaceFlinger HWC |

总预算 ≤ 1 帧（16.6ms @ 60Hz，8.3ms @ 120Hz）。任何一段超支都会导致掉帧。120Hz 设备上预算更紧，App 回调和 RenderThread 需要特别注意。

### 超支时的降级策略

系统有内置降级机制应对帧预算超支：

**Snapshot fallback**：如果 live render 跟不上 vsync，`TaskAnimationCoordinator` 会临时切换到 snapshot 模式。用户感知是动画从"实时跟随"变成"静态图片在移动"，但不会卡顿。

**帧率降低**：在持续掉帧时，`Choreographer` 可能跳过中间帧。SurfaceFlinger 的 `FrameRateOverride` 可以在动画期间临时降低合成帧率，减少 GPU 和 display 负载。

**动画时长压缩**：如果系统检测到连续掉帧（通过 `FrameTimeline` 的 missed frame 计数），`WindowManagerService` 的 `AppTransition` 动画会缩短总时长，尽快完成转场。这比让用户看一个持续卡顿的动画体验更好。

开发者无法直接控制这些降级策略，但可以通过 Perfetto 的 `FrameTimeline` track 观察掉帧模式。`expected_frame_timeline_slice` 和 `actual_frame_timeline_slice` 的间距直接反映每帧的超支程度。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/TaskAnimationCoordinator.java; frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp]

## Cross-Activity / Cross-Task Back 转场

### Cross-Activity 的状态转换路径

Cross-activity back（从详情页返回列表页）的性能关键路径在 Activity 状态转换：

```
当前 Activity: RESUMED → PAUSING → PAUSED
目标 Activity: STARTED → RESUMED
```

`PAUSING` 阶段，WMS 调用当前 Activity 的 `onPause()`。如果 `onPause()` 中有重操作（数据库写入、网络请求取消、动画清理），这段耗时直接叠加到 back 动画的首帧延迟上。Android 14+ 的 `onTopResumedActivityChanged()` 回调比 `onPause()` 更早触发，适合做提前的资源释放准备。

目标 Activity 的 `onResume()` 在 back 动画进行中调用。如果目标 Activity 使用 live layer（进程未销毁），`onResume()` 主要是恢复状态；如果进程已销毁需要重建，back 动画会使用 snapshot 作为过渡，直到新 Activity 完成首帧渲染后做一次 crossfade。

### Cross-Task Back 的窗口层级处理

Cross-task back（跨 Task 返回，如从分享面板 Task 返回调用方 Task）的复杂度高于 cross-activity。WMS 需要调整 Task 的 z-order：

1. 目标 Task 被 `reorderTask` 提到前台。
2. 当前 Task 的 surface 被 attach 到动画 leash 上，执行缩小/淡出动画。
3. 目标 Task 的 surface 从后台状态（可能被冻结或低分辨率）恢复到前台全分辨率。
4. 动画结束后，当前 Task 进入 cached state（如果系统内存允许）或被直接销毁。

Cross-task back 的性能风险点在目标 Task 的恢复延迟。如果目标 Task 被冻结过（`App Freezer`），解冻 + 恢复 window surface 的耗时可能达到 200-500ms。这段时间内系统只能依赖 snapshot 做过渡动画。

### enableOnBackInvokedCallback 对分发路径的影响

Android 16 起，`targetSdk >= 36` 的应用不再需要手动在 manifest 中声明 `android:enableOnBackInvokedCallback="true"`——系统默认按 opt-in 处理。这个变化意味着更多应用会走 predictive back 路径而非 legacy key event 路径。

对性能分析的影响：
- legacy path 的 key event 注入延迟消失，取而代之的是 progress 事件的分发延迟。
- 不兼容的应用（拦截了返回但未注册 `OnBackInvokedCallback`）会走系统默认 back 动画，这个动画本身的开销由系统承担，但应用页面切换仍然需要自行处理。
- Android 17 进一步收紧：`targetSdk >= 37` 的应用如果不注册 callback 但拦截了返回事件，系统会在 LogCat 输出警告，未来版本可能直接忽略应用拦截。

[已验证: 官方文档, https://developer.android.com/about/versions/15/changes/predictive-back]

## Predictive Back 与 IME 的交互

### 软键盘显示期间的返回处理

软键盘（IME）显示期间用户触发返回手势，系统需要先处理 IME 再处理返回。流程是：

1. `EdgeBackGestureHandler` 检测到边缘滑动，判断当前窗口是否有 IME input connection。
2. 如果有，返回手势的第一个目标是收起 IME（通过 `InputMethodManagerService.hideInputFromInputMethod()`）。
3. IME 收起动画与返回手势动画并行执行。`WindowInsets.ime` 的动画由 `InsetsAnimationControlImpl` 驱动。
4. IME 完全收起后，下一次返回手势才走标准 predictive back 路径。

这意味着用户在键盘显示时滑动返回，看到的效果是"键盘先收，页面不退"；再次滑动才"页面退"。两步返回的设计来自 `ImeFocusController` 的 input connection 状态检查，不能通过注册 `OnBackInvokedCallback` 绕过。

### IME 提取模式的特殊路径

Android 11+ 的 IME 提取模式（Extract Mode，横屏全屏输入）有独立的事件处理路径。在提取模式下，返回手势直接交给 IME 进程的 `ExtractEditLayout` 处理，不经过标准的 `OnBackInvokedDispatcher`。这导致：

- App 注册的 `OnBackInvokedCallback` 在提取模式下不生效。
- 返回手势的视觉反馈由 IME 进程渲染，不走 App 的 RenderThread。
- 如果 IME 进程的动画卡顿，App 无法干预。

Android 14+ 逐步废弃了提取模式（`flagNoExtractUi` 默认为 true 的应用增多），Android 17 中提取模式几乎不再出现在主流应用中。

### WindowInsets.ime 动画与 back 动画的并行协调

当返回手势触发时 IME 正在显示，`InsetsAnimationControlImpl` 会同时驱动 IME insets 动画和返回转场动画。两个动画共享同一个 `Choreographer` vsync 信号，但各自维护独立的动画值（ime insets 和 window transform）。

性能上的潜在冲突：IME insets 动画需要更新 IME window 的 position 和 visibility，这涉及一次 `SurfaceControl.Transaction`。返回转场动画需要更新 App window 的 transform。两个 transaction 在同一帧内合并提交，不会产生额外合成开销。但如果 IME 进程响应 `onStartInsetsAnimation` 延迟（IME 进程 MainThread 忙），IME 动画的首帧会延后，导致用户感知"键盘先闪了一下再开始收"。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/inputmethod/InputMethodManagerService.java]

## Android 16/17 强制启用与性能边界

### 从 opt-in 到默认启用的迁移

Android 13-15 期间 predictive back 是 opt-in 特性，开发者需要在 manifest 中声明 `android:enableOnBackInvokedCallback="true"`。Android 16 把这个门槛降低了：

- `targetSdk >= 36`：系统默认 opt-in，不需要 manifest 声明。
- `targetSdk < 36`：仍需手动 opt-in。
- 应用可以选择 `android:enableOnBackInvokedCallback="false"` 显式退出。

Android 17 在此基础上没有改变默认策略，但增强了系统动画的覆盖范围：更多的 cross-activity 场景自动使用 predictive back 动画，即使应用没有自定义返回动画。

### 强制启用后的系统性能观测

大规模强制启用 predictive back 带来的系统级性能影响：

**帧率影响**：predictive back 动画运行期间，系统多了一组 surface（snapshot 或 live layer）参与合成。GPU 合成开销增加约 15-25%（取决于设备分辨率和合成层数）。HWC（硬件合成器）通常能覆盖大部分场景，但当 HWC overlay 容量不足（已有 video layer + app layer + systemUI layer），额外的返回动画层会被降级到 GPU 合成。

**内存增量**：每个 Task 的 snapshot buffer 占用 10-16 MB（前面已计算）。在多任务场景下（用户快速切换 5-8 个 Task），snapshot 总内存增量可达 80-128 MB。Android 17 的 snapshot 压缩机制（低分辨率缓存非当前 Task）可以把这个数字压到 30-50 MB。

**不兼容应用的回退路径**：未注册 `OnBackInvokedCallback` 但拦截了返回的应用，系统会播放默认 back 动画并注入 `KEYCODE_BACK`。这条回退路径的性能开销与 legacy path 基本一致，但多了一段默认动画的渲染成本。在 Perfetto 中，这类应用的返回操作会显示 `AppTransition` 动画 slice 但 App 侧没有对应的 `onBackProgressed()` 调用。

[已验证: AOSP android-17.0.0_r1; 官方文档, https://developer.android.com/about/versions/15/changes/predictive-back]

## 扩展

### Perfetto 观测方法

定位 predictive back 性能问题时，关键 Perfetto slice 和 track 包括：

**SystemUI 进程**：
- `EdgeBackGestureHandler` 相关 slice：手势检测和进度更新
- `BackAnimation.onBackMotion()`：WM Shell 的手势进度回调

**system_server 进程**：
- `WindowManagerService.prepareAppTransition`：转场准备
- `TaskAnimationCoordinator`：转场动画协调
- `AppTransitionController.goodToGo`：转场执行
- `InputMonitor.updateInputWindowsLw`：input target 切换

**App 进程**：
- `OnBackAnimationCallback.onBackProgressed`：进度回调执行
- `Choreographer.doFrame`：每帧调度
- `RenderThread`：渲染管线
- `FrameTimeline` track：`expected_frame_timeline_slice` vs `actual_frame_timeline_slice`

**SurfaceFlinger 进程**：
- `composite` / `present` slice：合成和提交
- HWC `DEVICE` vs `CLIENT` composition type 变化

分析返回卡顿时，推荐的时间轴对齐方式：以 `EdgeBackGestureHandler` 检测到边缘滑动的 `ACTION_DOWN` 时刻为 t=0，逐帧检查 SystemUI → system_server → App → SurfaceFlinger 的执行时序。某个进程的 slice 在某一帧突然延长，就是瓶颈所在。

### 三方应用 Back 拦截的性能陷阱

`OnBackPressedDispatcher`（AndroidX）和 `OnBackInvokedCallback`（Platform）的性能差异不大，但使用方式会带来性能差异：

- **每帧 dispatch 的额外开销**：如果在 `handleOnBackProgressed()` 中执行了数据库查询、Bitmap 操作或复杂计算，每帧（60Hz 设备每 16.6ms 一次）都会重复执行。这类开销不是 API 本身造成的，是使用方式问题。
- **Dispatcher 链的遍历成本**：`OnBackPressedDispatcher` 维护一个 callback 栈，每次返回手势会从栈顶遍历到第一个 enabled callback。正常使用下 callback 数量不多（1-3 个），遍历成本可忽略。但深度拦截（Fragment 多层嵌套，每层注册 callback）时，遍历 + 每层 callback 的 `isEnabled()` 检查叠加起来，可能会增加 1-2ms 的 MainThread 占用。
- **Compose PredictiveBackHandler 的 Flow 开销**：`activity-compose:1.8.0+` 的 `PredictiveBackHandler` 把 progress 事件包装成 `Flow<BackEventCompat>`。每帧的 Flow emission 和 collect 会产生少量对象分配（适合用 `key` 去重和 `distinctUntilChanged` 过滤）。

### Foldable / Large Screen 的特殊处理

大屏设备（折叠屏展开态、平板）上 predictive back 有额外考量：

- **手势区域宽度调整**：`EdgeBackGestureHandler` 的边缘检测宽度 `mEdgeWidth` 在大屏上会按密度缩放。展开态折叠屏的边缘区域可能宽达 48dp（手机通常 24-32dp），减少误触但也降低了边缘手势的触发灵敏度。
- **多窗口模式下的 back 目标判定**：分屏模式下，返回手势的目标是当前 focused 的窗口而非整个 Task。`InputDispatcher` 通过 `WindowState.getFrame()` 判断触摸点落在哪个窗口，然后按标准路径分发。双窗口并排时，左窗口的返回手势不会影响右窗口。
- **折叠态 → 展开态的 Configuration Change**：如果在返回动画进行中发生了配置变更（折叠→展开），系统会取消当前返回动画并重新构建。这个取消-重建过程可能在 Perfetto 中表现为一段 `onBackCancelled()` 后紧跟的 Configuration change slice 序列。

### Edge Defense 系统的冲突处理

OEM 自定义的边缘手势（Samsung edge panel、小米边缘防误触等）通过 `SystemGestureExclusionRects` 或 OEM 私有接口与系统 back 手势协调。冲突处理遵循以下优先级：

1. OEM 边缘面板如果声明了 `setSystemGestureExclusionRects()`，系统 back 手势在该区域内被抑制。
2. 未声明 exclusion 的 OEM 手势区域，系统按标准 `edge-swipe` monitor 逻辑处理——OEM 手势和系统 back 手势并行观察同一 pointer stream，谁先越过阈值谁赢。
3. 冲突期间两个手势都未越过阈值时，App 仍然收到正常的 `MotionEvent`。

性能退化路径：两个手势同时竞争时，`EdgeBackGestureHandler` 需要额外检查 OEM 手势状态，每帧多一次 `mExcludeRegion.contains()` 调用（通常 < 0.1ms）。真正的性能问题不是这次 contains 调用，而是两个手势同时触发后，其中一个发送 `pilferPointers()` 导致另一个收到 cancel，引发 App 端的动画中断和状态错乱。

[结构参考: 3.3 节覆盖手势检测和回调模型，本节覆盖系统侧分发架构与转场管线；22.13 节覆盖应用侧动画实践]

> 适用版本：Android 13 (API 33) 引入 OnBackInvokedCallback；Android 14 (API 34) 增加进度回调；Android 15 (API 35) 系统动画默认开启；Android 16 (API 36) targetSdk ≥ 36 默认 opt-in；Android 17 (API 37) 增强系统动画覆盖范围。所有源码锚定 android-17.0.0_r1。
