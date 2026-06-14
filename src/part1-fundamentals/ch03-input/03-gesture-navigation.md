---
last_task9_at: "2026-04-30T16:20:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-04-30"
title: "手势导航与系统交互"
section: "3.3"
chapter: "3.3"
status: "finalized"
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
review_type: "post-polish-quality-gate"
review_round: 3
drafted_date: "2026-03-31"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-29"
last_task6_audit: "2026-06-14"
last_task9_audit: "2026-06-12"
last_task9_audit_log: "logs/deep-review/2026-06-12-05-audit.md"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-03-31"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: blog
    path: "TechMerger - 深入理解 Android 系统 Back Gesture 的实现 (微信)"
  - type: blog
    path: "郭霖 - Android 15 新特性：预测性返回手势 (微信)"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/BackPanelController.kt"
  - type: aosp
    path: "frameworks/base/packages/SystemUI/shared/src/com/android/systemui/shared/system/InputMonitorCompat.java"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/window/OnBackInvokedCallback.java"
  - type: aosp
    path: "frameworks/base/core/java/android/window/OnBackAnimationCallback.java"
  - type: aosp
    path: "frameworks/base/core/java/android/window/OnBackInvokedDispatcher.java"
  - type: official
    path: "https://perfetto.dev/docs/quickstart/android-tracing"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: official
    path: "https://developer.android.com/training/gestures/gesturenav"
  - type: official
    path: "https://developer.android.com/about/versions/13/features/predictive-back-gesture"
  - type: official
    path: "https://developer.android.com/reference/android/window/OnBackInvokedDispatcher"
  - type: official
    path: "https://developer.android.com/reference/android/window/OnBackInvokedCallback"
  - type: official
    path: "https://developer.android.com/reference/android/window/OnBackAnimationCallback"
  - type: official
    path: "https://developer.android.com/reference/android/view/WindowInsets"
  - type: official
    path: "https://developer.android.com/reference/androidx/activity/OnBackPressedCallback"
tags: [gesture-navigation, input-monitor, back-gesture, predictive-back, edge-swipe, systemui, windowinsets]
related_chapters: ["3.1", "3.2", "2.3", "2.4", "1.5"]
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: fixed
task2b_result: fixed
task9_review_notes: "2026-04-30 16:20 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 2；queue 无 pending，已自动晋升 finalized / ready-to-publish。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-31
---

# 3.3 手势导航与系统交互

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 EdgeBackGestureHandler 与 Gesture Monitor 的拦截流程
- 🔹 `setSystemGestureExclusionRects()` / `systemGestureInsets` 与边缘冲突处理
- 🔹 Predictive Back 的回调模型、版本演进与返回时序变化
- 🔹 边缘滑动检测的性能敏感点与误判场景
- 🔹 在 Perfetto 中识别手势导航相关问题的方法

### 扩展（可选深入）

- 🔸 多指触控、长按超时与沉浸式场景的特殊边界
- 🔸 Gesture Monitor、Back 注入与 InputDispatcher 的源码锚点

### OpenClaw 加工指引

> 锚点是最低覆盖要求，加工时必须逐条落实并标注验证状态。
> 扩展内容视素材完整度决定是否展开，涉及版本差异或返回分发细节的断言优先保守表述。
> Perfetto 观察点如果没有真实 Trace 素材，先保留文字版图示或 `[图：...]` 占位，不要把未验证的 slice 名写成确定结论。
<!-- outline-end -->

## 为什么要了解手势导航

如果我们在 Perfetto 中看到用户的一次触摸操作从 InputDispatcher 发出后，App 端迟迟没有收到对应的 MotionEvent，或者收到了但在 MainThread 上处理时间特别长，我们的第一反应可能是"App 卡了"或者"Input 管线出了问题"。但有一个可能性经常被忽略：**那次触摸事件被系统手势截获了**。

Android 10 引入的全屏手势导航（Gesture Navigation）改变了用户与系统的交互方式。Home 键变成了底部上滑，最近任务变成了底部悬停，而返回键则变成了从屏幕两侧边缘向内滑动。这些手势不是由 App 处理的，而是由系统在 App 之前拦截的。理解这套机制，对性能分析有直接的影响：当我们分析一次"卡顿"或"无响应"时，我们需要知道事件是被系统拿走了，还是没有送达 App。

Android 13 引入了 Predictive Back 相关 API。到 Android 15，官方文档明确把 back-to-home、cross-task、cross-activity 系统动画从开发者选项后面移了出来，但前提仍然是 App 或 Activity 已 opt in。返回处理从“松手后再决定怎么退”变成了“手势过程中就要准备回调和预览”，返回阶段的渲染分析也跟着变了。

读完这一节，我们将理解：系统手势是怎么在 App 之前截获 Touch 事件的；App 怎么通过 `setSystemGestureExclusionRects()` 声明"这个区域不要触发系统手势"；Predictive Back 的架构如何影响返回事件的分发时序；以及在 Perfetto 中如何识别和排查手势导航相关的性能问题。

## Android 10+ 手势导航的系统实现

### SystemUI 中的 EdgeBackGestureHandler

返回手势的入口仍然是 SystemUI 的 `EdgeBackGestureHandler`，但 android-16.0.0_r1 的实现与 Android 10 初版资料有几处关键差异。当前版本里，`updateIsEnabledInner()` 在手势导航模式启用后会完成三件事：向 WMS 注册 `ISystemGestureExclusionListener`、为当前 display 创建 `InputMonitorResource`、调用 `resetEdgeBackPlugin()` 挂起默认的边缘反馈插件。

`InputMonitorResource` 内部并没有自己发明一套输入通道，它只是用 `InputMonitorCompat("edge-swipe", displayId)` 包装 `InputManagerGlobal.monitorGestureInput()`，让 SystemUI 在当前屏幕上收到名为 `edge-swipe` 的 gesture monitor 事件流。视觉反馈这一侧，旧资料经常提 `NavigationBarEdgePanel`，但 android-16.0.0_r1 当前默认插件已经换成 `BackPanelController` / `BackPanel.kt`，通过 `TYPE_NAVIGATION_BAR_PANEL` overlay window 显示边缘箭头和面板动画。

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java; frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/BackPanelController.kt; frameworks/base/packages/SystemUI/shared/src/com/android/systemui/shared/system/InputMonitorCompat.java]

### InputMonitor 的工作原理

`InputMonitorCompat` 本身不负责“抢”事件，它做的是在 InputDispatcher 旁边挂一条 monitor 通道。SystemUI 在这条通道上注册 `InputEventReceiver`，和目标 App 一起观察同一批 `MotionEvent`。

这里要分清两个阶段。阈值之前，App 和 `edge-swipe` monitor 确实并行观察同一条 pointer stream。SystemUI 会先判断触点是否命中左右 back edge、是否落在 `mExcludeRegion`、是否被 PiP / desktop corner / overlay exclusion 挡住，然后再根据位移方向、长按超时和阈值判断是否继续。

legacy back path 里，一旦横向位移越过阈值且 `mBackAnimation == null`，`EdgeBackGestureHandler` 会调用 `pilferPointers()`。这一调用最终进入 `InputDispatcher::pilferPointersLocked()`，后者会对原目标窗口合成 `CANCEL_POINTER_EVENTS`。App 端收到的不是“完整滑到结束的一串 MotionEvent”，而是一条被系统夺走后的 cancel 结尾。边缘冲突里常见的“手指还在动，App 为什么突然不再收到后续 MOVE”，根因通常就在这里。

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java; frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

### 从边缘滑动到返回事件的完整流程

完整流程可以拆成两条路径。

**一条是 Android 10-12 为主的 legacy back gesture 路径。**

1. 用户从左右边缘按下，`MotionEvent` 同时送到 App 和 `edge-swipe` monitor。
2. `EdgeBackGestureHandler` 判断边缘命中、排除区、纵横向位移和长按超时。
3. 横向位移越过阈值后，handler 调用 `pilferPointers()`，InputDispatcher 向原目标窗口发送 cancel。
4. 用户松手后，`triggerBack()` 在 `mBackAnimation == null` 条件下通过 `sendEvent()` 注入 `KEYCODE_BACK` 的 down/up。
5. 这组按键再按普通 key 分发链进入焦点 Window，App 侧最终走 `OnBackPressedDispatcher` 或更老的 `Activity.onBackPressed()` 处理。

**另一条是 Android 13+ opt-in 后的 Predictive Back / ahead-of-time back dispatch 路径。**

1. `EdgeBackGestureHandler` 仍然从边缘手势起步，正文不能再把结尾概括成“统一注入 `KEYCODE_BACK`”。
2. 当 `mBackAnimation != null` 时，MOVE 事件会继续交给 `dispatchToBackAnimation()`，由 WM Shell 的 `BackAnimation.onBackMotion()` 接管进度。
3. 手势提交时，`triggerBack()` 走的是 `mBackAnimation.setTriggerBack(true)`；手势取消时走 `setTriggerBack(false)`。
4. App 侧配合的入口也从“接收一个 Back 按键”改成 `OnBackInvokedDispatcher` / `OnBackInvokedCallback`，或者 AndroidX 的 `OnBackPressedDispatcher` / `OnBackPressedCallback`。如果需要进度回调，还要进一步落到 `OnBackAnimationCallback` 或 AndroidX 1.8.0 的 progress API。

这个拆分直接影响性能分析。legacy path 里常见的现象，是 pointer 被 pilfer 之后 App 为什么突然收到 cancel；predictive path 里更常见的现象，是 back progress 动画、跨 Activity 预览和 App 自定义返回动画之间的配合是否掉帧。

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java; frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp; frameworks/base/core/java/android/window/OnBackInvokedCallback.java; frameworks/base/core/java/android/window/OnBackAnimationCallback.java]

## 手势冲突处理：系统手势优先区域 vs App 的 WindowInsets

系统手势和 App 手势的冲突，主要集中在左右 back edge 和底部 Home / quick-switch 区域。`View.setSystemGestureExclusionRects()` 只该拿来声明“这里的侧边手势先给 App”，不能把它当成一个通用的系统手势豁免开关。

### 系统手势排除区域（System Gesture Exclusion Rects）

当 App 在边缘放了抽屉、滑块或自定义返回区域时，可以通过 `View.setSystemGestureExclusionRects()` 把这块区域上报给系统。上报流程仍然是 View 侧收集 rect，`ViewRootImpl` 通过 `WindowSession.reportSystemGestureExclusionChanged()` 交给 WMS，再由 `DisplayContent.calculateSystemGestureExclusion()` 汇总成每个 display 的排除 `Region`，再通过 `ISystemGestureExclusionListener` 通知 SystemUI。

```kotlin
override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
    super.onLayout(changed, l, t, r, b)
    val exclusionRect = Rect(0, 0, drawerWidth, height)
    setSystemGestureExclusionRects(listOf(exclusionRect))
}
```

这套机制的目标很明确，解决的是左右 back edge 和 App 自己的侧边手势冲突。官方文档对它的建议也是“selectively opt out of the back gesture”，范围要尽量小。

[已验证: 官方文档, https://developer.android.com/training/gestures/gesturenav]

### 系统手势区域限制（System Gesture Exclusion Limit）

排除区域不是 App 想画多宽就画多宽。`DisplayContent.calculateSystemGestureExclusion()` 会结合 `mSystemGestureExclusionLimit` 裁剪左右两侧的排除宽度，保证系统始终保留一部分 back edge 可用空间。抽屉、轮盘和自定义滑杆如果把整条边都占满，系统会直接削掉超出的部分。

这也是线上冲突分析里一个常见误判来源。代码里明明设置了 exclusion rect，用户仍然能触发系统返回，不一定是 API 没生效，也可能是区域超出了系统允许的上限。

### WindowInsets 与手势区域

只写 `systemGestureInsets` 还不够。Android 把“常规系统手势区域”和“强制系统手势区域”分成了两层：

- 左右返回边缘，通常看 `WindowInsets.Type.systemGestures()`。
- 底部 Home / quick-switch 这类系统保留区，要看 `WindowInsets.Type.mandatorySystemGestures()`；旧 API 名是 `getMandatorySystemGestureInsets()`，从 API 30 起改成统一的 `getInsets(int)` 写法。

两者的处理方式也不同。左右 back edge 可以通过 `setSystemGestureExclusionRects()` 做有限排除；底部 mandatory gesture 区域属于系统保留区，App 不能按侧边返回那样随意声明“这一整块都归我”。游戏或沉浸式场景如果确实要占用底部区域，官方建议配合 immersive mode，而不是无限扩大 exclusion rect。

Perfetto 里如果看到边缘点击命中率很差，排查顺序应该先分清是左右 back edge 冲突，还是底部 mandatory gesture 冲突。把两种区域混成一句“systemGestureInsets 没处理好”，定位会绕远路。

[已验证: 官方文档, https://developer.android.com/training/gestures/gesturenav; API 参考, https://developer.android.com/reference/android/view/WindowInsets]

## Back 手势到 Predictive Back Animation 的演进

### 传统返回手势的问题

Android 10-12 的返回手势，用户在松手前通常只知道“系统准备返回了”，不知道返回目标是谁。对于性能分析，这条链也比较单线：边缘滑动成立，系统触发返回，App 在提交点处理自己的 back 逻辑。

Predictive Back 把时序往前挪了。系统在手势进行中就要知道返回会不会被拦截、动画该往哪一层退、App 有没有自己的过渡效果。返回流程从“提交时才处理”变成了“进度阶段就要协同”。

### Predictive Back 的回调模型

回调层级可以分成 platform API 和 AndroidX API 两层。

| 层级 | 接口 | 引入版本 | 可直接确认的方法 | 作用 |
| --- | --- | --- | --- | --- |
| Platform commit callback | `OnBackInvokedCallback` | API 33 | `onBackInvoked()` | 返回已提交后的回调。没有 progress 方法。 |
| Platform progress callback | `OnBackAnimationCallback` | API 34 | `onBackStarted()` / `onBackProgressed()` / `onBackCancelled()` / `onBackInvoked()` | 返回进度、取消和提交都能收到。 |
| AndroidX 兼容层 | `OnBackPressedCallback` | `androidx.activity:activity` 1.0.0；progress API 在 1.8.0 增加 | `handleOnBackPressed()`；`handleOnBackStarted()` / `handleOnBackProgressed()` / `handleOnBackCancelled()` | 向下兼容的入口。progress 这组三个方法只有 framework API 34+ 时才会被系统驱动。 |

App 端注册时，platform 走 `OnBackInvokedDispatcher`，AndroidX 走 `OnBackPressedDispatcher`。两套 API 可以共存，但文档语义不能混写。`OnBackInvokedCallback` 只有提交回调；进度回调属于 `OnBackAnimationCallback`。AndroidX 再把这些能力包装成 `OnBackPressedCallback` 的扩展方法。

官方页面还特别提醒了一点：`OnBackPressedCallback` 是否会执行，不由 `android:enableOnBackInvokedCallback` 单独决定。这个 manifest flag 控制的是 predictive back 的系统动画 opt in / opt out，不是把 AndroidX back 逻辑整体开关掉。

[已验证: 官方文档, https://developer.android.com/about/versions/13/features/predictive-back-gesture; API 参考, https://developer.android.com/reference/android/window/OnBackInvokedCallback; https://developer.android.com/reference/android/window/OnBackAnimationCallback; https://developer.android.com/reference/androidx/activity/OnBackPressedCallback]

### 版本演进的时间线

把开发者选项、manifest flag、platform API 和动画范围拆开后，版本边界可以整理成几组条件。

| Android 版本 | API | 系统动画状态 | manifest / activity 条件 | targetSdk / 兼容边界 | 回调与预览范围 |
| --- | --- | --- | --- | --- | --- |
| Android 13 | 33 | 官方文档给出的测试入口仍是开发者选项里的 predictive back animations。 | App 或 Activity 通过 `android:enableOnBackInvokedCallback` 管理 opt in / opt out。 | platform `OnBackInvokedCallback` 从这一版开始可用；未 opt in 的工程按 legacy path 看待更稳妥。 | 官方页面能直接确认 `OnBackInvokedCallback` 和 back-to-home 测试路径。 |
| Android 14 | 34 | 系统动画测试仍和开发者选项绑定，文档没有把所有预览都写成默认行为。 | 条件和 Android 13 同一层。 | platform progress callback 从 API 34 开始；AndroidX 1.8.0 的 progress 方法也只有在 API 34+ 才会被 framework 调用。 | `OnBackAnimationCallback` 提供 started / progressed / cancelled。 |
| Android 15 | 35 | 官方文档明确写到：developer option 不再承载 back-to-home、cross-task、cross-activity 系统动画，这些动画会对 opted-in 的 App 或 Activity 直接出现。 | 仍然要看 app / activity 是否 opt in；如果 Fragment back stack 或自定义回调还在消费返回，系统动画不会接管。 | 不把 targetSdk 单独写成唯一总开关，仍要和 opt in、回调消费状态一起判断。 | 系统级 back-to-home、cross-task、cross-activity 预览在文档里有了明确落点。 |
| Android 16 | 36 | 动画基础延续 Android 15。 | 同上。 | `OnBackInvokedDispatcher.PRIORITY_SYSTEM_NAVIGATION_OBSERVER` 从 API 36 增加。 | 可以注册 observer-only callback，只观察系统级返回，不消费事件。 |

这张表故意没有把“targetSdk >= 某值就一定出现某种预览”写成硬编码结论。官方页面给出的锚点更可靠的部分，是 API 可用性、manifest / activity opt in，以及 Android 15 起系统动画默认展示范围的变化。

[已验证: 官方文档, https://developer.android.com/about/versions/13/features/predictive-back-gesture; API 参考, https://developer.android.com/reference/android/window/OnBackInvokedDispatcher]

### Predictive Back 对性能的影响

Predictive Back 把返回处理拆成 progress 阶段和 commit 阶段，性能约束也跟着变了。

1. App 在 progress 回调里更适合只改 `translationX`、`alpha`、scale 这类动画属性，避免重新做一轮复杂 measure/layout。平台这层对应 `OnBackAnimationCallback`，AndroidX 这层对应 `handleOnBackStarted()` / `handleOnBackProgressed()` / `handleOnBackCancelled()`。
2. 系统级 cross-activity / cross-task 预览会把当前层和目标层一起拉进渲染路径。掉帧时，不能只盯着当前 Activity 的 RenderThread，还要把目标 Activity 或 Launcher 的 surface 一起看。
3. observer-only 回调适合埋点和业务日志，不该在这里再去消费返回。Android 16 把这条边界单独做成 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER`，就是为了把“观察”和“拦截”拆开。

## 边缘滑动检测的性能敏感点

返回手势的边缘滑动检测逻辑本身不复杂，但在实际运行中有几个性能敏感的细节。

### 判定延迟与手感

EdgeBackGestureHandler 在收到 `ACTION_DOWN` 时需要做一系列判断：是否在边缘区域内、是否在排除区域内、是否有 Gesture Blocking Activity、系统标志是否允许。这些判断在 SystemUI 的 MainThread 上执行。如果 SystemUI 的 MainThread 在这个时间点比较忙（比如正在更新通知栏），从用户触控到返回手势开始响应之间会有一个小的延迟。

这个延迟通常很小（几毫秒级别），但在极端情况下（SystemUI MainThread 被 Binder 调用阻塞），可能达到几十毫秒。在 Perfetto 中，如果我们看到 SystemUI 进程的 MainThread 在用户触摸时刻附近有一段长时间的 Binder 调用或密集的 CPU 活动，返回手势的响应可能会受影响。

### 长按超时的影响

EdgeBackGestureHandler 中有一个 `mLongPressTimeout` 参数，它限制了从 `ACTION_DOWN` 到 `ACTION_MOVE` 的最大时间。如果用户按下后停留时间超过了这个超时（默认与系统长按超时一致，通常为 400-500ms），手势会被取消。这个机制的初衷是区分"长按"和"滑动"，但在某些场景下可能造成误判——用户从边缘开始滑动但起始速度很慢，就可能触发超时取消。

### 多指触控的取消

如果用户在返回手势进行中又放下了一根手指（`ACTION_POINTER_DOWN`），EdgeBackGestureHandler 会立即取消手势。这是为了防止误操作，但有时会和 App 的多指操作冲突。比如用户在右边缘画着返回手势的同时左手做其他操作，返回手势就会被取消。

### 动画渲染的开销

android-16.0.0_r1 默认的边缘反馈插件是 `BackPanelController` / `BackPanel.kt`，不再是很多旧资料里的 `NavigationBarEdgePanel`。它被挂到 `TYPE_NAVIGATION_BAR_PANEL` overlay window 上，手势跟随阶段会更新 panel 形态、阈值状态和返回动画进度。排查这一段的渲染成本时，更适合把 SystemUI 的 UI thread、RenderThread 和合成线程一起看，不要只盯着某个已经换掉的旧类名。

[已验证: AOSP android-16.0.0_r1, frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/BackPanelController.kt; frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/BackPanel.kt; frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java]

## 在 Perfetto 中的表现

抓取可以先从一套能复现的最小基线开始，再按 legacy / predictive 两条路径判读。目标是把输入接管、动画进度和目标层预览放回同一时间轴里，不把某个固定 slice 名当成通用答案。

### 最小抓取配置

命令行先用这组基线 category：

```bash
adb shell perfetto -o /data/misc/perfetto-traces/back-gesture.perfetto-trace -t 15s \
  sched freq idle am wm gfx view binder_driver hal input aidl
adb pull /data/misc/perfetto-traces/back-gesture.perfetto-trace
```

Android 12+ 如果还要看当前层和目标层的预览重叠，再额外开启 FrameTimeline：

```protobuf
data_sources {
  config { name: "android.surfaceflinger.frametimeline" }
}
```

这组配置能覆盖三类信息：

- `input` + `wm`：看 `edge-swipe` monitor、InputDispatcher、WindowManager / WM Shell 的接管时序
- `gfx` + `view`：看 App 主线程、`Choreographer#doFrame` 和返回动画相关 UI 工作
- `android.surfaceflinger.frametimeline`：看当前 Activity 与目标 Activity 或 Launcher surface 的预览重叠

如果要观察 App 自己的 `onBackProgressed()` 或 AndroidX progress 回调，录制时再把目标包名加入 atrace app 列表。

[已验证: Perfetto 官方文档, https://perfetto.dev/docs/quickstart/android-tracing; https://perfetto.dev/docs/data-sources/frametimeline]

### 1. legacy back gesture：看 cancel 和注入链

legacy path 的判读顺序可以按这四步走：

1. 手指从左右边缘按下时，App 窗口和 `edge-swipe` monitor 同时出现第一批触摸事件。
2. 横向位移越过阈值后，原目标窗口会在同一时间窗附近收到 cancel，和 `pilferPointers()` 的接管时刻对应。
3. 手势提交后，再去找 injected `KEYCODE_BACK` 或后续 back dispatch。
4. 如果 App 一直收到完整 pointer stream，没有 cancel，先回到 exclusion rect、生效边界，或这次没有命中 back edge。

稳定证据是“边缘按下 → cancel → back dispatch”这条时间关系，不是某一个设备私有 slice 名。

### 2. Predictive Back：看 progress 回调和目标层预览

Predictive Back 的关键区别，是提交阶段不一定再出现 injected `KEYCODE_BACK`。更稳的观察顺序是：

1. 起手仍然从 `edge-swipe` monitor 和当前窗口同时看到第一批输入。
2. 阈值越过后，WM Shell back animation、当前 Activity surface、目标 Activity 或 Launcher surface 会开始重叠。
3. 如果 App 注册了 `OnBackAnimationCallback` 或 AndroidX progress API，`onBackStarted()` / `onBackProgressed()` 对应的 UI 工作应和这段预览时间窗重合。
4. 手势取消时，目标层预览回撤；手势提交时，当前层退出，目标层接管前台。

这里最有用的是比较三条轨道的相对顺序：当前层、目标层、SystemUI / WM Shell 的动画层。看到目标层预览已经启动，却没有 App 侧 progress 更新，问题通常在回调实现或渲染路径。

### 3. 排除区冲突：Perfetto 只负责时序，命中边界还要回到 Insets 和 dumpsys

排查排除区冲突时，Perfetto 负责回答两个问题：事件有没有被 SystemUI 提前接走，SystemUI 自己有没有卡住。它不负责证明 exclusion rect 一定声明正确。遇到“边缘手势偶发被系统抢走”的 case，建议把 trace 和下面两项一起看：

- `WindowInsets.Type.systemGestures()` / `mandatorySystemGestures()` 的布局边界
- `dumpsys window` 里和 system gesture exclusion 相关的窗口状态

如果 trace 里能看到 App 完整收到 pointer stream，但用户体感仍像“系统抢了手势”，就回到排除区宽度限制和沉浸式布局边界上查，不要继续在 Perfetto 里兜圈。

## 常见问题与误区

### 误区 1：所有返回手势都会走 `KEYCODE_BACK` 注入

**错误。** 这只覆盖了 legacy edge-back 的一条路径。android-16.0.0_r1 的 `EdgeBackGestureHandler.triggerBack()` 明确写着：只有 `mBackAnimation == null` 时才注入 `KEYCODE_BACK`；启用了 predictive back / ahead-of-time back dispatch 之后，提交走的是 `mBackAnimation.setTriggerBack(true)`，App 侧配套接口也变成 `OnBackInvokedCallback` / `OnBackAnimationCallback` 或 AndroidX 的 `OnBackPressedCallback`。

### 误区 2：设置了 exclusion rect，系统就一定不会截获边缘手势

**错误。** `DisplayContent.calculateSystemGestureExclusion()` 会按系统限制裁剪左右边缘的排除宽度。声明超了，超出的部分会被系统直接忽略。

### 误区 3：`systemGestureInsets` 足够描述所有系统手势冲突

**错误。** 左右 back edge 和底部 Home / quick-switch 区域不是同一层。前者更接近 `WindowInsets.Type.systemGestures()`，后者要看 `WindowInsets.Type.mandatorySystemGestures()`。如果把这两类区域压成一句“systemGestureInsets 没处理好”，游戏、沉浸式视频和底部导航栏的冲突会很难定位。

### 误区 4：Android 13 到 Android 16 的 Predictive Back 开关和预览范围都一样

**错误。** API 33 才引入 `OnBackInvokedCallback`，API 34 才有 `OnBackAnimationCallback` 的 progress 回调，Android 15 官方文档才把 back-to-home、cross-task、cross-activity 系统动画从开发者选项后面拿出来，API 36 又新增了 observer-only 的 `PRIORITY_SYSTEM_NAVIGATION_OBSERVER`。版本边界压成一句话，读者很容易把 API 可用性、系统动画默认状态和 opt-in 条件混成一层。

### 误区 5：Gesture Monitor 收到事件副本后，App 一定还能收到完整的 pointer stream

**错误。** legacy path 越过阈值后会发生 `pilferPointers()`，InputDispatcher 随后给原目标窗口发送 `CANCEL_POINTER_EVENTS`。App 端如果在 trace 里只看到一半 `MotionEvent`，再加上一条 cancel，这正是系统接管边缘返回的典型表现。

## 与其他章节的关系

- **3.1 Input 事件分发全流程**：手势导航是 Input 分发路径的一个特殊分支——Gesture Monitor 的引入改变了 InputDispatcher 的目标选择逻辑。理解 3.1 是理解本节的前置条件。
- **3.2 触摸响应的性能分析**：手势导航的边缘滑动检测会同时消耗 SystemUI MainThread 的 CPU 时间，如果 SystemUI 响应慢，会间接影响用户的触摸体验。
- **2.3 VSync 机制** / **2.4 Choreographer 与渲染流水线**：Predictive Back 的手势跟踪动画需要紧跟 VSync 节拍，如果 App 的 `onBackProgressed()` 回调中做了耗时操作，可能导致 doFrame 超时。
- **1.5 线程模型**：手势导航涉及多个进程的 MainThread 协作——SystemUI 的 MainThread 做手势判断，App 的 MainThread 处理 Back 按键，RenderThread 处理动画渲染。

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/EdgeBackGestureHandler.java` — 返回手势判定、`triggerBack()`、`dispatchToBackAnimation()`、`pilferPointers()`
  - `frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/BackPanelController.kt` — 当前默认的边缘返回反馈插件
  - `frameworks/base/packages/SystemUI/src/com/android/systemui/navigationbar/gestural/BackPanel.kt` — 边缘面板的绘制与动画实现
  - `frameworks/base/packages/SystemUI/shared/src/com/android/systemui/shared/system/InputMonitorCompat.java` — `monitorGestureInput()` 的 SystemUI 包装层
  - `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` — `pilferPointersLocked()` 与 `CANCEL_POINTER_EVENTS` 合成
  - `frameworks/base/core/java/android/window/OnBackInvokedCallback.java` — API 33 的 commit callback
  - `frameworks/base/core/java/android/window/OnBackAnimationCallback.java` — API 34 的 progress callback
  - `frameworks/base/core/java/android/window/OnBackInvokedDispatcher.java` — observer priority 与回调注册入口
- 官方文档：
  - [Gesture navigation | Android Developers](https://developer.android.com/training/gestures/gesturenav)
  - [Predictive back gesture | Android Developers](https://developer.android.com/about/versions/13/features/predictive-back-gesture)
  - [OnBackInvokedCallback | Android Developers](https://developer.android.com/reference/android/window/OnBackInvokedCallback)
  - [OnBackAnimationCallback | Android Developers](https://developer.android.com/reference/android/window/OnBackAnimationCallback)
  - [OnBackInvokedDispatcher | Android Developers](https://developer.android.com/reference/android/window/OnBackInvokedDispatcher)
  - [WindowInsets | Android Developers](https://developer.android.com/reference/android/view/WindowInsets)
  - [OnBackPressedCallback | Android Developers](https://developer.android.com/reference/androidx/activity/OnBackPressedCallback)
  - [Android tracing quickstart | Perfetto](https://perfetto.dev/docs/quickstart/android-tracing)
  - [FrameTimeline data source | Perfetto](https://perfetto.dev/docs/data-sources/frametimeline)
- 外部参考：
  - TechMerger《深入理解 Android 系统 Back Gesture 的实现》
  - 郭霖《Android 15 新特性：预测性返回手势》
