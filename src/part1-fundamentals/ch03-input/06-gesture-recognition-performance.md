---

title: 手势识别算法与性能优化
chapter: '3.6'
section: '3.6'
status: finalized
task2b_result: fixed
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
drafted_by: openclaw-task
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
version_notes: "DEFAULT_STRATEGY_BY_AXIS 仅 Android 14+ (API 34+) 可用"
confidence: medium
sources:
- type: aosp
  path: frameworks/base/core/java/android/view/VelocityTracker.java
- type: aosp
  path: frameworks/native/libs/input/VelocityTracker.cpp
- type: aosp
  path: frameworks/base/core/java/android/view/GestureDetector.java
- type: aosp
  path: frameworks/base/core/java/android/view/ViewConfiguration.java
- type: aosp
  path: frameworks/base/core/java/android/view/ViewGroup.java
- type: aosp
  path: frameworks/base/core/res/res/values/config.xml
- type: androidx
  path: frameworks/support/core/core/src/main/java/androidx/core/widget/NestedScrollView.java
tags:
- android
- performance
- input
- gesture
- velocitytracker
- gesturedetector
- nestedscroll
related_chapters:
- '3.1'
- '3.2'
- '3.3'
- '3.4'
- '2.4'

task9_result: auto-fixed
task9_reviewed_date: 2026-06-06
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-06T09:20:00+08:00"
reviewed_date: "2026-04-20"
reviewed_by: "openclaw-task6"
last_task6_audit: "2026-06-19"
task6_result: "pass-light-edit"
review_notes: '2026-04-12 task6 review: needs-rework。小修 8 处（frontmatter 标签、禁用词替换、段落拆分、代码注释格式统一）。回炉
  4 项（VelocityTracker 版本演进、双击回调语义、Perfetto 证据、扩展素材与来源）。评分: 结构 4/5·措辞 4/5·一致性 3/5·验证
  3/5·元数据 4/5。'
last_task9_audit: "2026-06-12"
last_task2b_lite_at: "2026-06-06"
last_task2b_at: "2026-06-03T21:33:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-06-09-deep-review.md"
last_task9_autofix_at: "2026-06-12"
task9_review_notes: "2026-06-06 09:20 Task9 deep-review: pass-tech-review。VelocityTracker Android 10-16 策略演进与 View/GestureDetector/ViewConfiguration 源码锚点复核通过；仅写入 P2 数据支撑建议。Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-12 13:20 Task9 idle audit: auto-fixed。修正 VelocityTracker.getXVelocity() 源码片段与 Compose MotionEventAdapter/PointerInputEvent 命名；Android 17 tag 未公开，未扩展为 Android 17 已验证结论。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-22
---

# 手势识别算法与性能优化

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 VelocityTracker 内部实现：速度计算算法（移动平均 vs 最小二乘法）、策略选择策略（strategy）、内存复用机制
- 🔹 GestureDetector 源码解析：onDown/onScroll/onFling 状态机、双击检测、长按超时
- 🔹 手势冲突检测与解决：嵌套滑动（NestedScroll）的协调机制、同方向手势冲突（横滑 vs 竖滑）、ViewGroup.requestDisallowInterceptTouchEvent
- 🔹 自定义手势识别的性能陷阱：onTouchEvent 中分配对象、过度计算、View 层级过深
- 🔹 触摸斜率（TouchSlop）与速度阈值（VelocityThreshold）的版本演进及性能影响

### 扩展（可选深入）

- 🔸 厂商手势增强方案：边缘手势防误触、游戏场景的手势优先级
- 🔸 Compose 手势系统的架构差异与性能特点

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解手势识别算法

当用户抱怨"滑动列表不跟手"或"快速滑动时松手后列表没有惯性滚动"时，Perfetto Trace 里大概率不会出现明显的掉帧。问题往往出在**手势识别本身**：速度计算不准导致 Fling 速度太小，TouchSlop 过大导致误判为"没滑动"，或者手势冲突导致事件被外层 View 截获。

手势识别是 Input 事件分发之后、UI 渲染之前的"决策层"。它决定了用户的触摸行为会被解读成什么——点击、滑动、快速滑动、长按、还是双击。这个决策层的算法质量，直接决定了用户对 App "流畅度"的感知。

手势识别还是一个**高频路径**。每次 ACTION_MOVE 都会触发 VelocityTracker 的速度更新，每次 ACTION_DOWN 都会触发 GestureDetector 的状态初始化。

在这条路径上的任何额外开销，例如对象分配、不必要的计算、过深的 View 遍历，都会在快速滑动时被放大。


## VelocityTracker：速度计算的底层引擎

VelocityTracker 是 Android 手势识别系统中最基础的组件。它的职责只有一个：根据最近收到的若干个 Touch 事件的位置和时间戳，计算出当前的手指移动速度。

这个速度值是 Fling 手势判断的核心依据。`GestureDetector.onFling()` 的两个速度参数（`velocityX`、`velocityY`）就来自 VelocityTracker。

### 核心接口：obtain / addMovement / computeCurrentVelocity

```java
// frameworks/base/core/java/android/view/VelocityTracker.java
static public VelocityTracker obtain() {
    VelocityTracker instance = sPool.acquire();
    return (instance != null) ? instance
            : new VelocityTracker(VELOCITY_TRACKER_STRATEGY_DEFAULT);
}

private VelocityTracker(@VelocityTrackerStrategy int strategy) {
    ...
    mPtr = nativeInitialize(mStrategy);
}

public void addMovement(MotionEvent event) {
    nativeAddMovement(mPtr, event);
}

public void computeCurrentVelocity(int units, float maxVelocity) {
    nativeComputeCurrentVelocity(mPtr, units, maxVelocity);
}

public float getXVelocity() {
    return getXVelocity(ACTIVE_POINTER_ID);
}

public void recycle() {
    if (mStrategy == VELOCITY_TRACKER_STRATEGY_DEFAULT) {
        clear();
        sPool.release(this);
    }
}
```

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/VelocityTracker.java]

### 对象池复用：避免 GC 压力

VelocityTracker 的 `obtain()` / `recycle()` 使用了 `Pools.SynchronizedPool` 做对象复用。这在滑动场景中很重要，一个 RecyclerView 的每一次滑动都涉及 `ACTION_DOWN` 时 obtain、`ACTION_UP` 时 recycle 的完整生命周期。

如果不做复用，快速滑动时会产生大量短生命周期对象，增加 GC 压力。

```java
// frameworks/base/core/java/android/view/VelocityTracker.java
private static final Pools.SynchronizedPool<VelocityTracker> sPool =
    new Pools.SynchronizedPool<>(2);  // 池容量为 2
```

池容量只有 2，因为同一时间通常只有一个活跃的 VelocityTracker 实例（一个手指触摸）。这个设计在多指触摸场景下可能不够用，但考虑到多指同时计算速度的场景很少，这是一个合理的取舍。

### 速度计算算法：Java wrapper + JNI + native strategy matrix (Android 14+)

前面那几个 Java API 只是入口。公开 AOSP 里的真实调用链是 `android.view.VelocityTracker` 把事件交给 JNI，再由 `frameworks/native/libs/input/VelocityTracker.cpp` 按 axis 选择策略并完成拟合。Java 层负责对象池、策略 ID 和 `MotionEvent` 封装，不负责真正的速度拟合。


`obtain(String strategy)` 和 `obtain(int strategy)` 也确实存在，但注释写得很直白，它们是 “For testing and comparison purposes only”。平时业务代码用 `obtain()` 即可。只有在做算法对比、回归测试或排查设备差异时，才会显式指定 strategy。

JNI 进入 native 后，`VelocityTracker.cpp` 会根据 axis 选择默认策略：

```cpp
// frameworks/native/libs/input/VelocityTracker.cpp
static const std::map<int32_t, VelocityTracker::Strategy> DEFAULT_STRATEGY_BY_AXIS =
        {{AMOTION_EVENT_AXIS_X, VelocityTracker::Strategy::LSQ2},
         {AMOTION_EVENT_AXIS_Y, VelocityTracker::Strategy::LSQ2},
         {AMOTION_EVENT_AXIS_SCROLL, VelocityTracker::Strategy::IMPULSE}};

void VelocityTracker::configureStrategy(int32_t axis) {
    ...
    createdStrategy = createStrategy(DEFAULT_STRATEGY_BY_AXIS.at(axis),
                                     /*deltaValues=*/isDifferentialAxis);
}
```

这张轴级策略表最早出现在 Android 14（API 34）。Android 10/11 只有全局 `DEFAULT_STRATEGY = "lsq2"`，所有轴统一用最小二乘法。Android 12/13 中 `Strategy::DEFAULT` 仍然通过 `configureStrategy()` 映射到同一个全局 LSQ2 策略，没有按轴区分。直到 Android 14 引入 `DEFAULT_STRATEGY_BY_AXIS`，才为 X/Y 保留 LSQ2 的同时给 scroll 轴单独换上 IMPULSE——在排查线上问题时，滚动轴的速度计算行为在不同 Android 版本上可能不同，排查时不能把 IMPULSE 当作全版本通用结论。

从排查角度看，这里要先分清两件事：一是当前取的是哪个 axis，二是代码是否显式覆盖了默认 strategy。把问题一概写成“Android 13 引入 FallbackStrategy，Android 14 默认 Impulse”会把分析入口带偏。

### Perfetto 视角：VelocityTracker 的性能影响

在 Perfetto 中追踪滑动性能时，VelocityTracker 的计算通常不会单独出现为一个 Trace slice——它是 `dispatchTouchEvent` 调用链中的一部分。但如果我们在 App 中自定义了 `computeCurrentVelocity()` 的调用频率，可以在 Trace 中观察到对应的耗时。

**关键性能指标**：

- **单次 `addMovement()` 耗时**：通常在 1-5μs，Native 层的环形缓冲区写入非常轻量
- **单次 `computeCurrentVelocity()` 耗时**：通常在 5-20μs，取决于策略和缓冲区中的采样点数量
- **内存分配**：正常路径下零分配（Native 层预分配缓冲区，Java 层使用对象池）

如果在 `onTouchEvent()` 的 ACTION_MOVE 分支中过度频繁地调用 `computeCurrentVelocity()`（比如每次 MOVE 都算一次），虽然单次开销不大，但在 16ms 的帧预算中累积起来也可能造成问题。最佳实践是在需要速度值时才计算（如 ACTION_UP 或判断 Fling 条件时）。

## GestureDetector：手势状态机的设计哲学

GestureDetector 是 Android 对外暴露的手势识别高层 API。它封装了 VelocityTracker，在此基础上实现了**状态机**来判断用户正在执行哪种手势。

### 核心状态转换

GestureDetector 内部维护了一个隐式的状态机，基于 `MotionEvent` 的序列来判定手势类型：

```
IDLE → DOWN → TAP / LONG_PRESS / SCROLL → FLING / TAP
```

```java
// frameworks/base/core/java/android/view/GestureDetector.java
public boolean onTouchEvent(MotionEvent ev) {
    switch (ev.getActionMasked()) {
        case MotionEvent.ACTION_DOWN:
            if (mDoubleTapListener != null) {
                boolean hadTapMessage = mHandler.hasMessages(TAP);
                if (hadTapMessage) mHandler.removeMessages(TAP);
                if ((mCurrentDownEvent != null) && (mPreviousUpEvent != null)
                        && hadTapMessage
                        && isConsideredDoubleTap(mCurrentDownEvent, mPreviousUpEvent, ev)) {
                    mIsDoubleTapping = true;
                    handled |= mDoubleTapListener.onDoubleTap(mCurrentDownEvent);
                    handled |= mDoubleTapListener.onDoubleTapEvent(ev);
                } else {
                    mHandler.sendEmptyMessageDelayed(TAP, DOUBLE_TAP_TIMEOUT);
                }
            }
            ...
            break;

        case MotionEvent.ACTION_UP:
            if (mIsDoubleTapping) {
                handled |= mDoubleTapListener.onDoubleTapEvent(ev);
            } else if (mAlwaysInTapRegion && !mIgnoreNextUpEvent) {
                handled = mListener.onSingleTapUp(ev);
                if (mDeferConfirmSingleTap && mDoubleTapListener != null) {
                    mDoubleTapListener.onSingleTapConfirmed(ev);
                }
            } else if (!mIgnoreNextUpEvent) {
                velocityTracker.computeCurrentVelocity(1000, mMaximumFlingVelocity);
                ...
                handled = mListener.onFling(mCurrentDownEvent, ev, velocityX, velocityY);
            }
            ...
    }
    return handled;
}
```

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/GestureDetector.java]

### 双击检测机制

GestureDetector 把“立即回调”和“延迟确认”分成了两套接口，混在一起时最容易写错。

1. 第一次点击的 `ACTION_UP` 落在 tap region 内时，`onSingleTapUp(ev)` 会立刻执行。
2. `ACTION_DOWN` 阶段已经投递了一个 `TAP` 消息，用来等待第二次点击。
3. 第二次 `ACTION_DOWN` 到来时，只有 `hadTapMessage == true`，并且 `isConsideredDoubleTap(firstDown, firstUp, secondDown)` 通过，才会进入双击分支。这个判断同时检查时间窗 `DOUBLE_TAP_MIN_TIME ~ DOUBLE_TAP_TIMEOUT` 和位移是否落在 `mDoubleTapSlopSquare` 内。
4. 如果超时还没有第二次点击，Handler 处理 `TAP` 消息时才回调 `onSingleTapConfirmed(mCurrentDownEvent)`。

```java
// frameworks/base/core/java/android/view/GestureDetector.java
case MotionEvent.ACTION_UP:
    ...
    handled = mListener.onSingleTapUp(ev);
    if (mDeferConfirmSingleTap && mDoubleTapListener != null) {
        mDoubleTapListener.onSingleTapConfirmed(ev);
    }

private boolean isConsideredDoubleTap(...) {
    ...
    final long deltaTime = secondDown.getEventTime() - firstUp.getEventTime();
    if (deltaTime > DOUBLE_TAP_TIMEOUT || deltaTime < DOUBLE_TAP_MIN_TIME) {
        return false;
    }
    ...
    return (deltaX * deltaX + deltaY * deltaY < mDoubleTapSlopSquare);
}
```

所以要区分三类回调：`onSingleTapUp()` 用来拿到第一时间的抬手事件，`onSingleTapConfirmed()` 用来拿到“已经排除双击”的单击确认，`onDoubleTap()` / `onDoubleTapEvent()` 用来处理第二次点击及其后续 move/up。做按钮点击反馈时，通常关心前两者的选择；做双击缩放、双击点赞这类交互时，再看 `isConsideredDoubleTap()` 的时间窗和位移窗是不是符合产品预期。

### 长按超时

长按检测通过 Handler 的延迟消息实现。`LONG_PRESS` 消息的延迟时间为 `ViewConfiguration.getLongPressTimeout()`，默认 500ms。如果在这 500ms 内手指移动超过了 TouchSlop，长按消息会被取消。

**Perfetto 视角**：长按超时本身不会造成性能问题（只是 Handler 消息的等待），但如果 App 在 `onLongPress()` 回调中做了耗时操作（如弹出 Dialog、加载资源），这些操作会阻塞 MainThread。在 Trace 中会表现为 `dispatchTouchEvent` 之后出现一个长耗时 slice。

## 手势冲突检测与解决

当多个 View 都想响应同一个触摸事件序列时，就会产生手势冲突。这是 Android 输入系统中最复杂的问题之一，也是性能分析中容易踩坑的地方。

### 嵌套滑动：NestedScroll 的协调机制

Android 5.0（API 21）引入了 NestedScrolling 机制来解决嵌套布局中的滑动冲突。经典场景是：CoordinatorLayout 内部包含一个 AppBarLayout 和一个 RecyclerView，用户向上滑动时需要先折叠 AppBar，再滚动列表。

```
用户手指滑动
    ↓
RecyclerView.onTouchEvent()
    ↓ dispatchNestedPreScroll() → CoordinatorLayout
    ↓                               ↓
    ↓                          AppBarLayout 先消费距离
    ↓                               ↓
    ← 剩余距离返回给 RecyclerView ←
    ↓
RecyclerView 自己消费剩余距离
```

```java
// 嵌套滑动的核心调用流程（简化）
// AndroidX: frameworks/support/core/core/src/main/java/androidx/core/widget/NestedScrollView.java

// 子 View 在消费滚动之前，先问父 View 要不要预消费
if (dispatchNestedPreScroll(dxConsumed, dyConsumed, mScrollConsumed, mScrollOffset)) {
    // 父 View 消费了一部分，剩余的才是子 View 的
    dyConsumed -= mScrollConsumed[1];
}

// 子 View 消费完自己的部分后，再问父 View 有没有剩余的要消费
if (dispatchNestedScroll(dxConsumed, dyConsumed, 0, dyUnconsumed, mScrollOffset)) {
    // ...
}
```

这里引用的是 AndroidX `NestedScrollView`，不是 `frameworks/base` 里的 framework 代码。NestedScrolling 支持类长期维护在 AndroidX，正文里的来源也按这个边界来标。

**性能影响**：每次 ACTION_MOVE 都会触发 `dispatchNestedPreScroll()` 和 `dispatchNestedScroll()` 的调用。这些调用本身非常轻量，主要是在 Parent 链上做回调。

如果嵌套层级很深（比如 5+ 层），累积的调用链就会变得可观。在 Perfetto 中，如果嵌套滑动层级过深，可以在 `dispatchTouchEvent` 的 slice 内看到多个连续的小 slice。

### 同方向手势冲突：横滑 vs 竖滑

当外层 View 水平滑动、内层 View 垂直滑动时（或反过来），需要在滑动开始时判断用户的意图方向。

Android 的默认处理方式是**谁先超过 TouchSlop 谁赢**。问题在于：如果外层 View 的 `onInterceptTouchEvent()` 在内层 View 还没超过 TouchSlop 时就截获了事件，用户的垂直滑动就会被误判为水平滑动。

**正确的解决方式**是在外层 View 的 `onInterceptTouchEvent()` 中等待足够的信息再决定是否拦截：

```java
// 典型的方向冲突解决方案
@Override
public boolean onInterceptTouchEvent(MotionEvent ev) {
    switch (ev.getActionMasked()) {
        case MotionEvent.ACTION_MOVE:
            final float dx = Math.abs(ev.getX() - mLastX);
            final float dy = Math.abs(ev.getY() - mLastY);
            // 水平位移明显大于垂直位移时才拦截
            if (dx > dy && dx > touchSlop) {
                mIsDragging = true;
                return true;
            }
            break;
    }
    return super.onInterceptTouchEvent(ev);
}
```

### requestDisallowInterceptTouchEvent：子 View 的自卫机制

当子 View 确认自己需要消费事件时，可以通过 `parent.requestDisallowInterceptTouchEvent(true)` 阻止父 View 拦截后续事件。这是 Android 提供给子 View 的"自卫"机制。

```java
// frameworks/base/core/java/android/view/ViewGroup.java
public void requestDisallowInterceptTouchEvent(boolean disallowIntercept) {
    if (disallowIntercept == ((mGroupFlags & FLAG_DISALLOW_INTERCEPT) != 0)) {
        return;
    }
    if (disallowIntercept) {
        mGroupFlags |= FLAG_DISALLOW_INTERCEPT;
    } else {
        mGroupFlags &= ~FLAG_DISALLOW_INTERCEPT;
    }
    // 递归向上传递
    if (mParent != null) {
        mParent.requestDisallowInterceptTouchEvent(disallowIntercept);
    }
}
```

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/ViewGroup.java]

**性能注意**：`requestDisallowInterceptTouchEvent(true)` 会沿着 Parent 链递归向上传递。如果 View 层级很深（比如 20+ 层的嵌套布局），这个递归调用会有不可忽视的开销。RecyclerView 内部就大量使用了这个机制，在快速滑动时确保事件不被外部 View 截获。

## TouchSlop 与 VelocityThreshold：阈值模型与设备差异

### TouchSlop：判断"这是滑动还是点击"的分界线

TouchSlop 是 Android 手势识别中最重要的阈值参数之一。它定义了手指移动多少像素才能被认为是"滑动"而不是"点击"。如果移动距离小于 TouchSlop，系统认为这是一次点击（TAP）；如果超过 TouchSlop，则认为是滑动（SCROLL）。

```java
// frameworks/base/core/java/android/view/ViewConfiguration.java
private static final int TOUCH_SLOP = 8;  // 默认值，单位 dp

public int getScaledTouchSlop() {
    return mTouchSlop;
}

// 构造时根据 display density 缩放
mTouchSlop = res.getDimensionPixelSize(
    com.android.internal.R.dimen.config_viewConfigurationTouchSlop);
```

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/ViewConfiguration.java]

TouchSlop 这一段更适合按“常量 → 配置资源 → 设备 overlay”来理解，而不是硬写一张版本表。`ViewConfiguration.java` 里仍保留了 `TOUCH_SLOP = 8` 这个 fallback 常量；对大多数设备真正生效的值，是构造函数从 `config_viewConfigurationTouchSlop` 读取的 dimen；再往下，OEM 可以通过 resource overlay 覆盖同名资源来校准不同触控面板。

| 层次 | 位置 | 作用 |
|------|------|------|
| framework fallback 常量 | `ViewConfiguration.TOUCH_SLOP = 8` | 给没有合适 `Context` 的旧代码兜底 |
| platform 配置资源 | `core/res/res/values/config.xml` 中的 `config_viewConfigurationTouchSlop = 8dp` | 由 `ViewConfiguration` 读取后换算成像素值 |
| device overlay | 设备 overlay 中覆盖同名 dimen | 厂商按触控面板和固件特性微调阈值 |

公开源码里 `config_viewConfigurationTouchSlop` 早就存在，不能写成“Android 5.0 才引入这个资源”。如果某个版本真的改了手势阈值，我们要把变更点落到具体资源、overlay 或行为差异上；如果只是同一套资源在不同设备上取值不同，就应该归到设备校准，而不是版本演进。

**性能影响**：TouchSlop 的值越大，手指需要移动更多距离才能触发滑动，这在用户体感上表现为"不跟手"。但 TouchSlop 太小又会导致误触——轻微的手指抖动就会触发滑动而不是点击。这是一个 UX 和性能之间的权衡。

### VelocityThreshold：Fling 判定的速度门槛

VelocityThreshold 定义了"多快才算快速滑动"。如果手指抬起时的速度低于这个阈值，不会触发 Fling；高于阈值才会触发惯性滚动。

```java
// frameworks/base/core/java/android/view/ViewConfiguration.java
private static final int MINIMUM_FLING_VELOCITY = 50;   // 最小 Fling 速度，dp/s
private static final int MAXIMUM_FLING_VELOCITY = 8000;  // 最大 Fling 速度，dp/s
```

> [已验证: AOSP android-14.0.0_r1, frameworks/base/core/java/android/view/ViewConfiguration.java]

`MINIMUM_FLING_VELOCITY` / `MAXIMUM_FLING_VELOCITY` 是 Java 层的 fallback 常量值。运行时真实阈值来自 `frameworks/base/core/res/res/values/config.xml` 中的 `config_viewMinFlingVelocity`（默认 50dp）和 `config_viewMaxFlingVelocity`（默认 8000dp），设备厂商可通过 overlay 覆盖这些资源值。Android 14+ 还引入了 `getScaledMinimumFlingVelocity(int inputDeviceId, int axis, int source)` / `getScaledMaximumFlingVelocity(...)` 重载，支持按输入设备、轴、输入源分别设置阈值（例如旋钮编码器 rotary encoder 有专用的 fling 阈值资源）。排查 Fling 行为异常时，不能只看 Java 常量，需要同时检查设备 overlay 和 axis/source 级重载是否改了门槛。

**关键设计**：`MAXIMUM_FLING_VELOCITY` 的存在是为了防止极端速度值导致的"飞出屏幕"效果。VelocityTracker 在 `computeCurrentVelocity()` 时会 clamp 速度值到这个范围内。这个参数的值直接影响 Fling 动画的最大速度，间接影响了用户对"滑动流畅度"的感知。

## 自定义手势识别的性能陷阱

### 陷阱一：onTouchEvent 中分配对象

这是最常见的性能问题。在 `onTouchEvent()` 的 ACTION_MOVE 分支中创建新对象，会导致快速滑动时产生大量短生命周期对象，触发 GC。

```java
// ❌ 错误示例：每次 MOVE 都分配对象
@Override
public boolean onTouchEvent(MotionEvent event) {
    if (event.getAction() == MotionEvent.ACTION_MOVE) {
        // 每次分配新对象 → GC 压力
        Point delta = new Point(
            (int)(event.getX() - mLastX),
            (int)(event.getY() - mLastY)
        );
        // ...
    }
    return true;
}

// ✅ 正确做法：预分配，复用成员变量
private final float[] mDelta = new float[2];

@Override
public boolean onTouchEvent(MotionEvent event) {
    if (event.getAction() == MotionEvent.ACTION_MOVE) {
        mDelta[0] = event.getX() - mLastX;
        mDelta[1] = event.getY() - mLastY;
        // ...
    }
    return true;
}
```

### 陷阱二：过度计算

在 ACTION_MOVE 中执行不必要的计算是另一个常见问题。比如每次 MOVE 都调用 `computeCurrentVelocity()`、执行复杂的几何计算、或者遍历大量数据。

```java
// ❌ 错误示例：每次 MOVE 都计算速度
case MotionEvent.ACTION_MOVE:
    mVelocityTracker.computeCurrentVelocity(1000);  // 不必要的频繁计算
    float speed = mVelocityTracker.getYVelocity();
    // 仅在特定条件下才需要速度值
    if (speed > mThreshold) {
        // ...
    }
    break;

// ✅ 正确做法：只在需要时计算
case MotionEvent.ACTION_UP:
    mVelocityTracker.computeCurrentVelocity(1000);  // 仅在 UP 时计算
    if (mVelocityTracker.getYVelocity() > mMinimumFlingVelocity) {
        // Fling 处理
    }
    break;
```

### 陷阱三：View 层级过深

手势识别的性能不仅取决于算法本身，还取决于事件分发的路径长度。每次 `dispatchTouchEvent()` 都会从 DecorView 开始向下遍历 View 树。如果布局层级过深（比如 20+ 层），ACTION_MOVE 事件在到达目标 View 之前就会消耗掉可观的帧预算。

在 Perfetto 中，这表现为 `dispatchTouchEvent` 的 slice 在 MOVE 事件时明显比 DOWN 事件长（因为 MOVE 事件数量远多于 DOWN，累积效应更明显）。

**优化建议**：

1. **使用 ConstraintLayout 减少嵌套层级**，从源头上缩短事件分发路径
2. **在合适的位置调用 `requestDisallowInterceptTouchEvent(true)`**，避免事件被不必要的中间层拦截和重新分发
3. **对于复杂的自定义手势 View，考虑直接处理 Raw Touch 事件**，跳过不必要的中间层

以上三个陷阱覆盖了 App 层手势性能的主要问诘。下面两节为扩展内容，分别看厂商驱动层和 Compose 的手势差异。

## 厂商手势增强方案（扩展）

### 边缘手势防误触

手机厂商（如 MTK、高通方案）在触控驱动层实现了多种防误触机制：

- **边缘抑制（Edge Rejection）**：在屏幕边缘 2-3mm 范围内，要求更大的 TouchSlop 才能触发滑动
- **手掌抑制（Palm Rejection）**：通过触摸面积和压力判断是否为手掌误触
- **水滴抑制（Water Rejection）**：多指同时触摸时抑制异常报点

这些机制在驱动层实现，对 Framework 透明。但在 Perfetto Trace 中，如果发现 App 收到的 ACTION_MOVE 事件的坐标在边缘区域"跳变"，可能是驱动层的防误触算法在工作。

### 游戏场景的手势优先级

游戏场景对手势响应的要求远高于普通 App。部分厂商提供了游戏模式下的手势增强：

- **降低 TouchSlop**：从 8dp 降低到 4-5dp，提高操作灵敏度
- **降低 Touch Latency**：缩短驱动层的事件上报间隔
- **多点触控优化**：提高多指同时触控的报点频率

> [已验证: 部分厂商实现，非 AOSP 标准 API，具体行为因设备而异]

## Compose 手势系统的架构差异（扩展）

厂商方案在驱动层做了透明干预，而 Compose 的差异是架构级的：它的手势系统与 View 系统有本质不同。

Jetpack Compose 的手势系统与 View 系统有本质的架构差异：

**View 系统**：基于 `onInterceptTouchEvent()` / `onTouchEvent()` 的责任链模式，事件从外层向内层分发，拦截权由外层控制。

**Compose 系统**：基于 `PointerInputScope` 的修饰符模式，手势通过 `Modifier.pointerInput()` 附加到 Composable 上。Compose 内部使用 `PointerInputChange` 代替 `MotionEvent`，并通过 `awaitPointerEventScope()` 提供协程式的异步手势 API。

```kotlin
// Compose 的手势识别示例
Modifier.pointerInput(Unit) {
    detectDragGestures { change, dragAmount ->
        // 拖拽处理
    }
}
```

**性能特点**：Compose 的手势系统在底层仍然依赖 Android 的 `MotionEvent`，但手势判定逻辑运行在 Compose 的 pointer input 层中。

因此，Compose 的手势识别可以更细粒度地与 Composable 的重组和布局阶段集成，但 Android 平台层仍需要通过 `MotionEventAdapter` 把 `MotionEvent` 转换为 Compose 内部的 `PointerInputEvent` / `PointerInputChange`，这一步会引入额外的转换开销。

> [已验证: Jetpack Compose 1.6+, androidx.compose.ui.input.pointer]
