---




title: "InputFlinger Rust 组件与自适应刷新率协同"
chapter: "3.8"
section: "3.8"
status: finalized
pipeline_stage: ready-to-publish
task2b_state: fixed
last_task9_at: "2026-06-05T17:24:00+08:00"
last_task9_audit: "2026-06-15"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-05"
task9_result: pass-tech-review
task9_state: reviewed
drafted_date: "2026-05-16"
drafted_by: openclaw-task2a
applicable_versions: "Android 15-QPR1 (API 35) - Android 17 (API 37)"
last_verified: "2026-06-04"
last_verified_against: "AOSP android-16.0.0_r1：frameworks/native/services/inputflinger、frameworks/base/services/core/java/com/android/server/power、frameworks/native/services/surfaceflinger；spot-check AOSP android-15.0.0_r36 inputflinger/rust/input_filter.rs；Android Developers ARR 文档；AOSP ARR 文档"
confidence: medium
sources:
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-10-inputflinger-rust-arr-input-system.md"
  - type: aosp
    path: "frameworks/native/services/inputflinger/InputManager.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/InputFilter.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/InputFilterCallbacks.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/rust/lib.rs"
  - type: aosp
    path: "frameworks/native/services/inputflinger/rust/input_filter.rs"
  - type: aosp
    path: "frameworks/native/services/inputflinger/rust/bounce_keys_filter.rs"
  - type: aosp
    path: "frameworks/native/services/inputflinger/rust/slow_keys_filter.rs"
  - type: aosp
    path: "frameworks/native/services/inputflinger/rust/sticky_keys_filter.rs"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp"
  - type: official
    path: "https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate"
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
  - type: official
    path: "https://source.android.com/docs/core/graphics/arr"
tags: [inputflinger, rust, arr, refresh-rate, input, accessibility]
related_chapters: ["3.1", "3.3", "3.4", "2.18", "2.19"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "研究素材/AOSP结构"
task6_state: reviewed
task6_result: pass-light-edit
reviewed_date: "2026-06-04"
reviewed_by: "openclaw-task6"
last_task2b_lite_at: '2026-06-04'
task2b_result: fixed-lite
last_task6_at: "2026-06-04T11:05:00+08:00"
version_boundary_note: "Android 17/API 37 未核到公开 android-17.0.0_r1，本节不写 Android 17-only 结论"
last_task9_autofix_at: "2026-06-04"
last_task9_review_log: "logs/deep-review/2026-06-05-17-deep-review.md"
task9_review_notes: "2026-06-04 Task9 auto-fix: replaced unversioned source anchors with android-16.0.0_r1, narrowed verified Android 17 scope, and corrected InputFilter enablement claim. | 2026-06-05 Task9 深度复审：pass-tech-review。P0 0 / P1 0 / P2 0；InputFlinger Rust filter 边界、KeyEvent/MotionEvent 分流、ARR touch hint 与 Android 17 非结论边界复核通过，满足自动晋升 finalized 条件。"
task6_reviewed_date: 2026-06-04
task6_reviewed_by: openclaw-task6
task6_review_notes: "2026-06-04 Task6 revisiting-review: pass-light-edit。L1/L2 全部通过（禁用词0/AI套话0/高频词0/元叙述0/结构性元叙述0）。无B类大问题。代码路径和验证标注完整，[已验证] tags与AOSP锚点一一对应。task9 auto-fix后回到task6复审，写作质量无回退。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-05
---



# 3.8 InputFlinger Rust 组件与自适应刷新率协同

<!-- outline-start -->
## 要点

### 🔹 InputFlinger 中 Rust 组件的引入边界
说明 Rust 只落在 InputFilter wrapper 与 accessibility filters，不替换 InputReader / InputDispatcher。

### 🔹 bounce / slow / sticky keys filter 的位置
区分 Bounce / Slow / Sticky Keys 的处理对象、等待或丢弃策略，以及对按键延迟的影响。

### 🔹 C++ 与 Rust 之间的 FFI 调用边界
说明 cxxbridge、IInputFlingerRust、IInputFilterCallbacks 与 InputFilterThread 的回传路径。

### 🔹 触摸事件触发刷新率策略的入口
说明 MotionEvent 触发 user activity、interaction boost 和 Scheduler touch hint，而不是进入 Rust filter。

### 🔹 输入事件、RefreshRatePolicy 与 SurfaceFlinger 的关系
拆开 WindowManager frame-rate vote、Power touch hint 与 SurfaceFlinger RefreshRateSelector 的职责。

### 🔹 版本适用范围与可观测信号
标注 Android 15-QPR1 / Android 16 / Android 17 的适用范围和 Perfetto / dump 观察入口。

## 扩展

### 🔸 辅助功能输入过滤对延迟的影响
说明 Slow Keys 的有意等待与普通分发阻塞的判读边界。

### 🔸 桌面模式和外接输入设备的刷新率策略
说明外接键盘、鼠标、触控板和多显示场景下的输入 / 刷新率边界。
<!-- outline-end -->

## 为什么要把这两个话题放在一起

InputFlinger Rust 和 ARR 经常被放在同一个“输入系统重构”的话题里，但它们不在同一条事件处理路径上。Rust 进入的是 InputFlinger 里的辅助功能输入过滤层，当前主要处理键盘类 KeyEvent；ARR 的触摸升频路径走的是 user activity / power boost / SurfaceFlinger Scheduler。把这两件事分开，才能判断一次输入延迟到底发生在按键过滤、事件分发，还是显示刷新节奏变化上。

这里按已核到源码和官方文档的边界展开：InputReader、InputProcessor、InputDispatcher 仍是 C++ 主体；Rust 组件是 InputFilter 的实现之一；触摸事件不会因为 Rust filter 多走一遍。ARR 侧要看 SurfaceFlinger Scheduler 和 View / RecyclerView / Compose 的帧率投票，不能把 `DisplayPolicy.onUserActivityEventTouch()` 写成刷新率选择入口。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputManager.cpp] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputFilter.cpp] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp]

[图：InputFlinger Rust 与 ARR 两条路径对照图。左侧为 KeyEvent：InputReader → UnwantedInteractionBlocker → InputFilter(C++ wrapper) → Rust bounce/slow/sticky filters → InputDispatcher。右侧为 Touch：InputDispatcher 标记 USER_ACTIVITY_EVENT_TOUCH → PowerManagerService 发送 Boost.INTERACTION → SurfaceFlinger.notifyPowerBoost → Scheduler.onTouchHint → RefreshRateSelector / FrameRate vote。]

## Rust 进入 InputFlinger 的位置

AOSP `InputManager.cpp` 里的事件流注释给了这条 Native 管线：`InputReader → UnwantedInteractionBlocker → InputFilter → PointerChoreographer → InputProcessor → InputDeviceMetricsCollector → InputDispatcher`。Rust 组件挂在 `InputFilter` 这个节点，不替换 InputReader 或 InputDispatcher。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputManager.cpp]

`InputManager` 构造时创建 `mInputFlingerRust`，并把 C++ `InputFilter` wrapper 固定插入 listener 管线。`InputFilter` 内部通过 `isFilterEnabled()` 查询 Rust 侧状态：启用时 KeyEvent 进入 Rust filter，未启用时直接透传到下一层 listener。`InputFilter` wrapper 的注释写明，它是围绕 Rust 实现的一层 C++ 包装。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputManager.cpp] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputFilter.cpp] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputFilter.h]

这给出三个边界：

1. Rust filter 是 InputFilter wrapper 下的辅助功能过滤实现，不是 InputFlinger 全部迁移到 Rust。
2. C++ wrapper 只在 `isFilterEnabled()` 返回 true 时把 KeyEvent 交给 Rust；未启用时直接把事件传给下一层 listener。
3. `notifyMotion()` 在 C++ `InputFilter` 里直接透传，触摸类 MotionEvent 不进入当前 Rust bounce / slow / sticky 过滤器。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputFilter.cpp]

第三点对性能分析很有用。滑动不跟手、触摸后刷新率没有拉高、FrameTimeline 异常这些问题，优先看 InputDispatcher、PowerManager、SurfaceFlinger 和 App 渲染侧。Rust accessibility filter 更可能影响外接键盘、实体键盘或辅助功能按键场景。

## bounce / slow / sticky keys filter 在做什么

Rust 侧的入口在 `frameworks/native/services/inputflinger/rust/lib.rs`。C++ 通过 cxxbridge 调 `create_inputflinger_rust()`，Rust 创建 `InputFlingerRust` binder 对象，再通过 bootstrap callback 把 `IInputFlingerRust` 回传给 C++。`IInputFlingerRust.aidl` 只有一个主要方法：`createInputFilter(IInputFilterCallbacks callbacks)`。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/lib.rs] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/aidl/com/android/server/inputflinger/IInputFlingerRust.aidl]

Rust `input_filter.rs` 里定义了 `Filter` trait，事件处理入口是 `notify_key()`，设备列表变化入口是 `notify_devices_changed()`。配置变化时，Rust 会重建一条 filter chain：

```text
BaseFilter
  ↑ StickyKeysFilter（stickyKeysEnabled）
  ↑ SlowKeysFilter（slowKeysThresholdNs > 0）
  ↑ BounceKeysFilter（bounceKeysThresholdNs > 0）
```

这里的“↑”表示更靠近输入入口的一层。配置项来自 `InputFilterConfiguration.aidl`：`bounceKeysThresholdNs`、`slowKeysThresholdNs`、`stickyKeysEnabled`。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/input_filter.rs] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/aidl/com/android/server/inputflinger/InputFilterConfiguration.aidl]

三个过滤器的行为各不相同：

| Filter | 处理对象 | 处理方式 | 延迟影响 |
| --- | --- | --- | --- |
| Bounce Keys | 支持的键盘设备、`Source::KEYBOARD` KeyEvent | 如果同一设备同一 keyCode 在上次 UP 后很快再次 DOWN，就丢弃这次 DOWN，并在对应 UP 到来时一起丢弃 | 主要减少误触重复输入，不主动等待 |
| Slow Keys | 支持的键盘设备、`Source::KEYBOARD` KeyEvent | DOWN 先进入 pending 队列，超过阈值后通过 InputFilterThread 发回；阈值内 UP 到来则丢弃 | 会有可配置的按键接受延迟 |
| Sticky Keys | 修饰键 KeyEvent | 捕获 Shift / Ctrl / Alt / Meta 等瞬时修饰键的 UP，维护 modifier / locked modifier state，并通过 callback 通知策略层 | 不等待阈值，主要改写 modifier state |

Bounce Keys 和 Slow Keys 都会跳过 virtual keyboard device，并根据设备列表维护 supported devices。Slow Keys 还会在 delayed DOWN 上设置 `POLICY_FLAG_DISABLE_KEY_REPEAT`，避免慢键模式下默认重复速率造成额外重复输入。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/bounce_keys_filter.rs] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/slow_keys_filter.rs] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/sticky_keys_filter.rs]

## C++ / Rust 边界怎么回到分发管线

`IInputFilter.aidl` 标注这是 local AIDL interface，用作输入事件过滤的 FFI；注释里也写明 local interface 的处理发生在调用线程。Rust filter 处理完事件后，不直接找 InputDispatcher，而是走 C++ 提供的 callbacks。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/aidl/com/android/server/inputflinger/IInputFilter.aidl]

回传路径是：

```text
Rust BaseFilter::notify_key()
  → IInputFilterCallbacks.sendKeyEvent(event)
  → C++ InputFilterCallbacks::sendKeyEvent()
  → mNextListener.notifyKey(...)
  → 后续 InputListener stage
```

`InputFilterCallbacks.cpp` 还提供了 `createInputFilterThread()`。Slow Keys 需要等待阈值，Rust 侧通过 `InputFilterThread.request_timeout_at_time()` 请求未来某个时间点回调；C++ 侧创建名为 `InputFilter` 的 `InputThread`，内部用 `Looper.sleepUntil()` 和 `wake()` 管理等待。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputFilterCallbacks.cpp] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/input_filter_thread.rs]

这条设计有一个直接后果：普通按键过滤仍在 inputflinger 的 listener 管线里完成；需要等待的 Slow Keys 不把等待塞进 InputReader 主循环，而是交给单独的 InputFilterThread。分析按键延迟时，要区分“事件被 filter 有意延后”和“InputDispatcher / App 没有及时消费”。前者会和 slow keys 配置阈值对上，后者会表现为分发队列或 App 主线程积压。

## 触摸事件怎么影响 ARR

触摸带来的刷新率提升不走 Rust InputFilter。AOSP `InputDispatcher.cpp` 里，motion event 如果满足 `MotionEvent::isTouchEvent(source, action)`，会被归类为 `USER_ACTIVITY_EVENT_TOUCH`。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

PowerManagerService 收到 user activity 后，在 `userActivityNoUpdateLocked()` 中发 `Boost.INTERACTION`。SurfaceFlinger 的 `notifyPowerBoost()` 收到 `Boost::INTERACTION` 后调用 `mScheduler->onTouchHint()`；Scheduler 里这个方法会 reset touch timer，并重置 pacesetter display 的 kernel idle timer。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp]

刷新率选择发生在 SurfaceFlinger Scheduler / RefreshRateSelector。`RefreshRateSelector.cpp` 里有一段专门处理 UI Toolkit 通过 `HighHint` category vote 发送 touch signal 的逻辑：同一 UID 的 layer 如果有 `HighHint`，且没有 `ExplicitDefault` vote，就可能作为 app touch boost；这也解释了为什么游戏或明确调用 `setFrameRate()` 的场景会抑制 touch boost。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp]

App 侧公开入口则落在 ARR 文档里的 View / RecyclerView / Compose / Surface API。Android 15-QPR1 及以上、且设备 HAL 支持时，ARR 能让显示刷新率按内容帧率用离散 VSync 步进调整；Android 16 增加了 `Display.hasArrSupport()`、`Display.getSuggestedFrameRate(int)`，并恢复 `getSupportedRefreshRates()` 供 App 查询。RecyclerView 1.4 在 fling 或 smooth scroll settling 阶段已经接入 ARR；自定义滚动组件可以在平滑滚动或 fling 的每帧调用 `setFrameContentVelocity()` 提供速度信息。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate] [已验证: 官方文档, developer.android.com/about/versions/16/features]

## RefreshRatePolicy 在这里承担什么角色

`RefreshRatePolicy.java` 属于 WindowManager 的窗口刷新率策略，它读取窗口属性、preferred display mode、preferred refresh rate、低刷新率包名单等信息，给某个 WindowState 计算偏好。它不是 InputFlinger 的一部分，也不是 Rust filter 的下游。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/RefreshRatePolicy.java]

`DisplayPolicy.onUserActivityEventTouch()` 也容易被误放到 ARR 主路径里。当前源码里，它处理的是设备不处于 awake 时的触摸 user activity：例如 AOD 或屏下指纹 overlay 场景下，临时把相关进程标成 animating，让 dozing UI 更快响应。`PhoneWindowManager.userActivity()` 会在默认显示、触摸事件下调用它，但这段代码没有直接操作 `RefreshRatePolicy`。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/DisplayPolicy.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/policy/PhoneWindowManager.java]

分析刷新率时，可以把职责分成三层：

1. **WindowManager / View 层**：窗口属性、View frame rate category、滚动速度、Surface frame rate vote。
2. **Power / Touch hint 层**：user activity 触发 interaction boost，SurfaceFlinger Scheduler 接收 touch hint。
3. **SurfaceFlinger / HWC 层**：RefreshRateSelector 排名候选刷新率，ARR 设备再通过 composer / panel 能力做离散 VSync 步进。

AOSP ARR 文档还给出硬件条件：Android 15 引入 ARR，OEM 需要支持 kernel / system 改动，并实现 `android.hardware.graphics.composer3` version 3 相关 API；`DisplayConfiguration.aidl` 的 `vrrConfig` 表示某个配置启用 ARR，`vsyncPeriod` 和 `minFrameIntervalNs` 决定可派生的离散刷新率范围。[已验证: 官方文档, source.android.com/docs/core/graphics/arr]

## 在 Perfetto 和日志里看什么

这类问题不要只盯 App 主线程。Rust filter、InputDispatcher、PowerManager、SurfaceFlinger 分别有不同观察点：

- **按键辅助功能延迟**：看是否启用了 Bounce Keys / Slow Keys / Sticky Keys。Slow Keys 的延迟应接近配置阈值；如果阈值内 UP 到来，事件会被丢弃。C++ dump 中 `InputFilter` 和 Rust dumpFilter 可打印 filter 状态。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputFilter.cpp]
- **触摸分发延迟**：看 InputDispatcher 到 App 的 input latency、目标窗口是否可接收、App `deliverInputEvent` 是否被主线程阻塞。详见 3.1、3.7 节。
- **触摸后刷新率未提升**：看 PowerManager 的 `userActivity` trace、SurfaceFlinger 是否收到 `Boost.INTERACTION`，以及 Scheduler touch timer / refresh-rate selector 是否有高刷候选。
- **ARR 正常降频被误判成掉帧**：看 VSYNC 间隔、FrameTimeline、SurfaceFlinger refresh rate 变化。ARR 下 VSYNC 周期变化不等同于 jank，详见 2.18、2.19 节。

排查触摸滑动卡顿时，不应把 Rust InputFilter 当作默认嫌疑点——它当前只处理键盘辅助功能过滤。触摸场景如果没有 KeyEvent 或实体键盘参与，排查顺序应从 InputDispatcher、PowerManager interaction boost、SurfaceFlinger Scheduler、App 渲染预算开始。

## 版本边界

| 版本 | 可确认变化 | 分析边界 |
| --- | --- | --- |
| Android 15 / 15-QPR1 | ARR 能力面向支持 HAL 的设备引入；Rust InputFilter 路径已在 android-15.0.0_r36 抽查到 | App 不能假定设备支持 ARR；InputFlinger Rust 细节以已核 tag 为准 |
| Android 16 / API 36 | `hasArrSupport()`、`getSuggestedFrameRate(int)`、`getSupportedRefreshRates()` 提供 App 查询入口；RecyclerView 1.4 支持部分滚动 ARR 场景 | 查询 API 只说明显示能力和建议，不等于本帧一定切到某个刷新率 |
| Android 17 / API 37 | 未核到公开 `android-17.0.0_r1` AOSP tag，本节不写 Android 17-only 行为 | 后续 tag 发布后再复核 InputFilter Rust、FrameRateCategory、composer3 / ARR 文档变化 |

写源码分析时，最稳的表述是：Android 15/16 的 InputFlinger 已引入 Rust 组件承载 accessibility input filters；触摸驱动的 ARR 协同在 power boost、SurfaceFlinger Scheduler 和 FrameRate vote 侧完成。两者同属输入体验优化，但不在同一段代码路径里。

## 辅助功能输入过滤对延迟的影响

Bounce Keys 和 Sticky Keys 对延迟的影响较小：前者按阈值丢弃重复按键，后者维护 modifier state。Slow Keys 会有配置阈值内的有意等待，按键 DOWN 到达后被改写为 `downTime + slow_key_threshold_ns`，等 timeout 到期后再发回 C++ listener；如果 UP 在阈值到期前到来，pending DOWN 被移除，本次按键不会进入后续分发。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/slow_keys_filter.rs]

这不是性能退化，而是辅助功能语义。排查外接键盘“按下没反应”时，要先确认系统辅助功能设置和 input filter dump，再判断是否存在 dispatcher 或 App 侧阻塞。

## 桌面模式和外接输入设备的刷新率策略

外接键盘、鼠标、触控板会让输入类型更复杂。生效范围需要拆开描述：Bounce / Slow Keys 受 supported keyboard devices 与 `Source::KEYBOARD` 限制；Sticky Keys 的实现不同——`StickyKeysFilter.notify_key()` 不检查 `supported_devices` 或 `Source`，而是按 `KeyEvent` 的 modifier keycode 维护 `down_key_map`、`modifier_state`、`locked_modifier_state`，因此作用范围比前两者更广。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/sticky_keys_filter.rs] 鼠标移动、触控板 pointer motion、触摸屏滑动仍走 motion event 路径。刷新率策略取决于可见 Layer 的 frame rate vote、交互 boost、设备支持的 ARR / MRR 能力，而不是某个输入设备是否经过 Rust filter。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/rust/bounce_keys_filter.rs] [已验证: AOSP android-16.0.0_r1, frameworks/native/services/inputflinger/InputFilter.cpp]

桌面模式或多显示器下还要看 pacesetter display、display group、WindowManager 对不同显示的策略。当前章节只覆盖默认显示和主输入路径；外接显示刷新率仲裁建议放到 2.18 / 2.19 的多显示扩展里继续核源码。[待补充]

## 小结

InputFlinger Rust 组件的定位是“键盘辅助功能过滤器的 Rust 实现”，不是输入分发主干重写。触摸驱动 ARR 的路径在 user activity、interaction boost、SurfaceFlinger Scheduler、FrameRate vote 和 HWC / panel 能力之间。遇到输入体验问题，先按事件类型分流：KeyEvent 看 Rust InputFilter 和辅助功能配置；Touch / MotionEvent 看 InputDispatcher、PowerManager、SurfaceFlinger 和 App 帧预算。
