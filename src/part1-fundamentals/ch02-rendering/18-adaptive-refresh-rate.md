---

task2b_rework_date: "2026-05-25T07:27:11+08:00"

status: "ready-for-review"
title: Adaptive Refresh Rate 与动态帧率控制
chapter: '2.18'
section: '2.18'
drafted_date: '2026-04-05'
drafted_by: openclaw-task2a
applicable_versions: ARR 主体：Android 15-QPR1 及以上；背景：Android 11-14 多刷新率支持
last_verified: '2026-04-26'
last_verified_against: "AOSP android-16.0.0_r1 + developer.android.com + perfetto.dev + external review 2026-04-25"
confidence: high
sources:
- type: official
  path: https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
- type: official
  path: https://developer.android.com/reference/android/view/Display
- type: official
  path: https://developer.android.com/reference/android/view/View
- type: official
  path: https://developer.android.com/reference/android/view/Surface
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer.FrameData
- type: official
  path: https://developer.android.com/games/sdk/frame-pacing
- type: research
  path: intake/research-feeds/2026-04-05-19-android16-arr-surfaceflinger-choreographer-frame-pacing.md
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
tags:
- ARR
- refresh-rate
- VSync
- SurfaceFlinger
- Choreographer
- LTPO
- frame-pacing
- Android-16
related_chapters:
- '2.2'
- '2.3'
- '2.4'
- '2.6'
- '2.13'
- '2.16'
pipeline_stage: task2b_pending
last_task9_at: "2026-05-25T07:30:00+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-25"
task6_state: "reviewed"
task9_state: reviewed
task2b_state: pending
reviewed_by: openclaw-task6
reviewed_date: "2026-05-25"
task6_result: pass-light-edit
task9_result: needs-rework
task2b_result: "fixed"
last_task2b_at: '2026-05-17T19:17:39'
repaired_date: '2026-04-26'
repaired_by: openclaw-task2b
task9_review_notes: "2026-05-25 07 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 0；FrameTimeline display_frame_token gap 不能直接判定调度器错过目标 VSYNC。"
task6_reviewed_date: "2026-05-25"
last_task9_review_log: "logs/deep-review/2026-05-25-07-deep-review.md"
last_task6_at: "2026-05-25T08:15:00+08:00"
last_task6_review_log: "logs/review/2026-05-25-08-review.md"
task6_review_notes: "2026-05-25 Task6：小修 L1/L2 1 处；未新增 Task6 L3/L4 回炉。既有 Task9 P1 队列仍 pending：display_frame_token gap 不能单独定责 Scheduler。"
p0: 0
p1: 1
p2: 0
---


# 2.18 Adaptive Refresh Rate 与动态帧率控制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **ARR 的适用范围要和 Android 11-14 的多刷新率背景分开写**：[已验证: developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]
  Android 11-14 重点是多刷新率与 mode switching，ARR 主体能力面向 Android 15-QPR1 及以上，且依赖设备 HAL 支持。

- 🔹 **SurfaceFlinger 通过 Scheduler 做 refresh-rate selection**：[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp]
  调用点在 `SurfaceFlinger.cpp` 的 `mScheduler->chooseRefreshRateForContent(...)`，不是把选择函数简单归到 SurfaceFlinger 某个公开方法名上。

- 🔹 **Display 查询 API 的真实语义**：[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Display.java]
  `hasArrSupport()`、`getSupportedRefreshRates()`、`getSuggestedFrameRate(int)` 是 Android 16 / API 36 公开查询入口；ARR 系统能力从 Android 15-QPR1 起步，App 可见 API 晚一版公开。`getSuggestedFrameRate(int)` 只接受 `FRAME_RATE_CATEGORY_NORMAL/HIGH` 这两个类别。

- 🔹 **View / RecyclerView / Compose 才是普通 UI 应用的主入口**：[已验证: developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]
  `setRequestedFrameRate()`、`setFrameContentVelocity()`、`Modifier.preferredFrameRate()` 负责表达 UI 偏好，`Surface.setFrameRate()` 属于更底层的 Surface 提示。

- 🔹 **Choreographer 公开的是 `FrameData` / `FrameTimeline`**：[已验证: developer.android.com/reference/android/view/Choreographer.FrameData]
  App 回调签名是 `onVsync(FrameData data)`，公开 API 没有 `refreshRate` 字段，刷新节奏要结合时间线和 Display / View API 判断。

- 🔹 **Perfetto 分析 ARR 时先看 VSYNC 间隔和 FrameTimeline，再判断异常**：[已验证: developer.android.com/games/sdk/frame-pacing]
  VSYNC 周期变化本身可能是正常降频，不能直接按固定 16.67ms 阈值判掉帧。

### 扩展（可选深入）

- 🔸 **触摸与 Game Mode 对刷新率选择的影响**
- 🔸 **Swappy 在游戏场景里的帧节奏控制**
- 🔸 **非 LTPO 设备上的模式切换与短暂卡顿**
<!-- outline-end -->


## 为什么要了解 ARR

在固定刷新率设备上，60Hz 可以按 16.67ms、120Hz 按 8.33ms 理解，然后用这个固定周期判断是否掉帧。到了支持 ARR 的设备，这个前提不再稳定。滚动时面板可能跑到较高刷新率，静止后又降到更低值，VSYNC-app 和 VSYNC-sf 的间隔会跟着变化。如果还用“超过 16.67ms 就一定异常”的老办法看 Trace，很容易把正常降频看成故障。

ARR 解决的是内容节奏和面板刷新率不匹配的问题。内容只有 24fps、30fps 或静态页面时，面板没有必要一直以 120Hz 工作。系统把刷新率压到更合适的档位，可以少做无效刷新，显示子系统的功耗也会跟着下降。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

[图：Perfetto 对比图。左侧为固定高刷场景，VSYNC-app 间隔稳定在 8.33ms；右侧为 ARR 场景，滑动时保持 8.33ms，静止后拉长到 16.67ms 或更长。重点标出 VSYNC-app、VSYNC-sf、FrameTimeline 三个观察点。]

## 从多刷新率到 ARR

Android 11 起，系统已经支持多刷新率和 `Surface.setFrameRate()`。这时设备通常在几个固定 Display Mode 之间切换，比如 60Hz 和 120Hz。它能解决一部分场景，但本质还是“切模式”，不是在同一模式里按内容节奏细调刷新周期。

官方 ARR 文档把正式能力收在 Android 15-QPR1 及以上，并要求设备实现对应 HAL API。分析时要把“Android 11-14 的多刷新率背景”和“Android 15-QPR1+ 的 ARR 正式能力”分开看。前者让系统学会在多个模式之间做选择，后者才让支持的面板在更细的刷新档位里跟着内容变化。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

LTPO 面板之所以经常和 ARR 一起出现，是因为它更适合低频到高频的宽范围调节。但有没有 LTPO 不是 App 能直接假定的前提。**该检查的是设备是否公开支持 ARR**，以及当前系统给出的刷新率范围。

## 系统里谁在做什么

DisplayManager 这一层先决定系统允许在哪些模式里挑。AOSP android-16.0.0_r1 里，`DisplayModeDirector#getDesiredDisplayModeSpecs()` 会把用户设置、低电量、亮度区间、App request range 和 switching type 折叠成 `DesiredDisplayModeSpecs`，里面带着 base mode、physical/render refresh-rate ranges 和 `allowGroupSwitching`。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java]

`DisplayManagerService` 的 `DesiredDisplayModeSpecsObserver` 取到这组 specs 后，会把它写进 `LogicalDisplay`，再由 `LocalDisplayAdapter` 转成 `SurfaceControl.DesiredDisplayModeSpecs` 下发给 SurfaceFlinger。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/display/DisplayManagerService.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/display/LogicalDisplay.java] [已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/display/LocalDisplayAdapter.java]

到了 SurfaceFlinger 这一层，`mScheduler->chooseRefreshRateForContent(...)` 才开始根据当前可见 Layer 的内容节奏做 content-based selection。这里的输入已经带着前面那层收窄后的 allowed ranges，所以 Battery Saver、用户峰值刷新率和 App 请求范围会先影响候选集合，再交给 Scheduler 做评分。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp]

`VsyncModulator` 负责在某些阶段调整 VSYNC offset，给事务提交和合成留出时间余量。它的源码路径是 `frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp`，阅读入口可以从 `VsyncModulator::setVsyncConfigSet()` 和 `VsyncModulator::updateVsyncConfig()` 开始。前者装载 Early / EarlyGl / Late 等 offset 配置，后者根据 transaction、刷新率变化和调度状态选择本轮使用哪组配置。当刷新率变化、事务开始或系统需要更早唤醒 App / SurfaceFlinger 时，offset 会跟着调整。所以 Trace 里看到 VSYNC-app 与 VSYNC-sf 的间距短暂变化，不必马上把它当成异常。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp]

## App 侧可以用的 ARR API

### Display 查询 API

想知道“这台设备支不支持 ARR、系统建议用什么档位”，入口在 `Display`。这组查询 API 属于 Android 16（API 36）公开接口；Android 15-QPR1 先提供系统侧 ARR 能力，App 可见查询晚到 API 36。

- `Display.hasArrSupport()`：检查显示设备是否支持 ARR。
- `Display.getSupportedRefreshRates()`：Android 16+（API 36）返回 display supported render rates；Android 15 及以下旧行为只返回默认 mode 的 refresh rates，需要更多选项时用 `getSupportedModes()`。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Display.java]
- `Display.getSuggestedFrameRate(int category)`：按类别获取系统建议值，入参只接受 `FRAME_RATE_CATEGORY_NORMAL` 和 `FRAME_RATE_CATEGORY_HIGH`。

`getSuggestedFrameRate()` 的语义不能写成“给 45fps，系统返回 90Hz 或 60Hz”。AOSP `Display.java` 里它只接受类别型参数，内部也是按 `FRAME_RATE_CATEGORY_NORMAL` / `FRAME_RATE_CATEGORY_HIGH` 去取系统给出的建议值，不处理任意 fps 到任意 Hz 的映射。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Display.java]

```java
// Android 16 (API 36)+
Display display = context.getDisplay();
if (display != null && display.hasArrSupport()) {
    float normal = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_NORMAL);
    float high = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_HIGH);
    float[] supported = display.getSupportedRefreshRates();
}
```

如果业务在意 45fps 这种具体目标，应该把它当成“内容自己的生产节奏”，再结合设备支持档位、系统建议值和 Surface / View 投票结果去决定策略，而不是把这个判断塞给 `getSuggestedFrameRate()`。

### View / RecyclerView / Compose 这一层才是主入口

ARR 文档把 View 层 API 放在更靠前的位置。`View.setRequestedFrameRate(float)` 可以直接给出偏好的帧率，也可以用类别常量表达意图。AOSP `View.java` 里可用的类别包括 `REQUESTED_FRAME_RATE_CATEGORY_NO_PREFERENCE`、`LOW`、`NORMAL`、`HIGH`。文档对这几个类别的解释也很明确，系统会根据 View 的投票结果选一个更合适的档位。[已验证: 官方文档, developer.android.com/reference/android/view/View] [已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/View.java]

```java
view.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_NORMAL);
animationView.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
staticPanel.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_LOW);
```

如果组件自己在做滚动或 fling，应该在每帧更新内容速度。对应 API 是 `View.setFrameContentVelocity(float pixelsPerSecond)`。这是官方 ARR 文档推荐的滚动适配方式，也是 AndroidX 自动接入滚动组件的基础。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate] [已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/View.java]

官方文档给出的现成接入点有两类：

- `RecyclerView`，需要 `AndroidX.recyclerview` 1.4.0 及以上
- `NestedScrollView`，需要 `AndroidX.core` 1.15.0 及以上

这两类组件接入后，系统会根据滚动速度和当前重绘需求调整刷新率。这里的主线是 `setFrameContentVelocity()`，不是“RecyclerView 自动调用 `Surface.setFrameRate()` 把屏幕拉到最高值”。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

Compose 侧对应的是 `Modifier.preferredFrameRate(frameRate: Float)` 和 `Modifier.preferredFrameRate(frameRateCategory: FrameRateCategory)`。它表达的也是“偏好”，最终仍由系统综合决定。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

### `Surface.setFrameRate()` 仍然有用，但位置更底层

`Surface.setFrameRate()` 没有失效，它适合直接围绕某个 Surface 给系统一个节奏提示，视频播放和单 Surface 渲染场景经常会用到。只是到了 ARR 章节里，它不该再被写成 App 侧最主要的入口。View / Compose 这一层才是普通 UI 应用更常见的做法，Surface API 更像单独 surface 的低层提示机制。[已验证: 官方文档, developer.android.com/reference/android/view/Surface]

```java
surface.setFrameRate(24f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
surface.setFrameRate(60f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
```

## Choreographer 回调里有什么，没有什么

公开给 App 的回调签名是 `Choreographer.VsyncCallback.onVsync(@NonNull FrameData data)`。`FrameData` 的公开方法包括 `getFrameTimeNanos()`、`getFrameTimelines()` 和 `getPreferredFrameTimeline()`。它不是 `DisplayEventReceiver.VsyncEventData` 的公开包装，也没有 `refreshRate` 这个 public 字段给 App 直接读。[已验证: 官方文档, developer.android.com/reference/android/view/Choreographer.FrameData] [已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java]

```java
choreographer.postVsyncCallback(frameData -> {
    long frameTimeNanos = frameData.getFrameTimeNanos();
    Choreographer.FrameTimeline preferred = frameData.getPreferredFrameTimeline();

    // 用时间线信息安排这一帧的工作，
    // 刷新率判断则通过 Display / View API 和实际 VSYNC 间隔综合分析。
});
```

App 如果要判断“系统当前更接近 60Hz 还是 120Hz”，做法通常有两类：

1. 通过 `Display` / `View` 的公开 API 读取系统建议值和自己的投票结果。
2. 结合 `FrameData` 的时间线信息，或者在 Trace 里直接看 VSYNC-app 间隔。

把 `VsyncEventData.refreshRate` 当成公开 API，会让示例代码无法编译，也会把 Android 13+ 的 Choreographer 行为讲错。

## SurfaceFlinger 怎样做刷新率选择

SurfaceFlinger 不会在全量 Display Mode 里随意挑选。AOSP android-16.0.0_r1 里，DisplayManager 下发的 policy 最终会进入 `setDesiredDisplayModeSpecsInternal(...)`，写到 `RefreshRateSelector`；后续 `mScheduler->chooseRefreshRateForContent(...)` 只会在 `isModeAllowed(...)` 通过的模式里，根据 Layer 的更新节奏、App 显式偏好和系统估算的内容 fps 做选择。[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp]

应用没有接入 ARR API，设备也可能在滚动时升频、静止后降频。系统会从 Layer 的更新节奏里估算内容帧率，再在 allowed range 里选更合适的模式。[已验证: 官方文档, developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

触摸和游戏模式会继续影响选择空间。触摸开始后，系统往往会更积极地把刷新率抬高，以保证滑动和动画的跟手感；Game Mode 可能降低或提高刷新率上限。分析 Trace 时，要把内容帧率、触摸状态、DisplayManager policy 和 SurfaceFlinger 的选择结果放在同一时间窗里看。

[待验证] `RefreshRateSelector::chooseRefreshRate()` 在 16KB 页设备上是否存在 `SmallVector` 替换 `std::map` 的优化，以及对应的 TLB 局部性收益和 12% 耗时下降——AOSP android-16.0.0_r1 的 `RefreshRateSelector.cpp` 仍使用 `std::map<Key, DisplayModeIterator, KeyLess> ratesMap`，未能找到 SmallVector 替换或对应的 perf 数据。如有后续版本确认，再补回该段。

[图：模式切换或升频示意图。标出触摸开始后 VSYNC-app 间隔从 16.67ms 收缩到 8.33ms，触摸结束后一段时间再回落。同步标出 SurfaceFlinger 的 refresh-rate selection slice。]

## 在 Perfetto 里怎么判断 ARR 是否工作

ARR 场景最值得看的对象有四个：

- `VSYNC-app`：看 App 这一侧收到的节拍是否在变。
- `VSYNC-sf`：看 SurfaceFlinger 的合成节拍是否同步变化。
- `FrameTimeline`：看 preferred timeline 和实际提交是否一致。
- `SurfaceFlinger` 主线程或工作线程上的 refresh-rate selection 相关 slice。

如果滑动时 `VSYNC-app` 长期保持 8.33ms，停止后逐步拉长到 16.67ms 或更长，同时 `FrameTimeline` 没有明显 missed frame，这通常是 ARR 在正常工作。相反，如果看到刷新率切换前后伴随一两个明显的长间隔，再加上 mode change 相关 slice，就更像是传统多刷新率设备在做模式切换。

SQL 入口更适合先看 Frame Timeline。Perfetto 官方文档公开了 `expected_frame_timeline_slice` 和 `actual_frame_timeline_slice` 两张表，它们分别表示目标时间线和实际时间线，比把 `VSYNC-app` 当成固定 slice 名更稳。`VSYNC-app` 在 Perfetto UI 里更像轨道语义，常见显示名是 `VSYNC-app` 或 `FrameDisplayEventReceiver.onVsync`，不同版本和 trace 配置下名字会变。分析时先在 UI 里确认轨道，再决定要不要按 `track.id` 继续查。[已验证: Perfetto 官方文档, perfetto.dev/docs/data-sources/frametimeline] [已验证: Perfetto 官方文档, perfetto.dev/docs/analysis/stdlib-docs]

```sql
SELECT
  process.name AS process_name,
  ROUND(actual.ts / 1e6, 2) AS actual_ts_ms,
  ROUND(actual.dur / 1e6, 2) AS actual_dur_ms,
  ROUND(expected.dur / 1e6, 2) AS expected_dur_ms,
  actual.present_type,
  actual.jank_type,
  actual.layer_name
FROM actual_frame_timeline_slice AS actual
LEFT JOIN expected_frame_timeline_slice AS expected
  ON actual.display_frame_token = expected.display_frame_token
 AND actual.surface_frame_token = expected.surface_frame_token
LEFT JOIN process
  USING (upid)
WHERE process.name = 'your.package.name'
ORDER BY actual.ts;
```

这条查询适合先判断两件事：一是 `expected_dur_ms` 有没有在 8.33ms、16.67ms、33.33ms 这类目标值之间切换，二是切换时 `actual_dur_ms`、`jank_type` 和 `present_type` 有没有一起恶化。目标时长在变而 jank 没有明显抬升，通常说明 ARR 在按内容工作；目标时长切换时伴随连续 jank，再结合 mode change 或 `Refresh Rate Selection` slice，才更像传统模式切换带来的抖动。

这组表从 Android 12 起可用。Android 11 或 trace 没打开 Frame Timeline 时，回到 Perfetto UI 里直接看 `VSYNC-app` 轨道间隔，再和 `VSYNC-sf`、`Refresh Rate Selection` slice 放在同一时间窗里对照。需要写 SQL 时，先在 UI 里确认目标轨道，再用 `slice.track_id` 查询，不要把 `WHERE name = 'VSYNC-app'` 当成通用写法。

### 利用 VSync ID 分析切换瞬间的预测误差

ARR 切换刷新率时，偶尔出现的一两帧长间隔不一定是 bug。调度器需要从旧频率的 VSYNC 时序过渡到新频率，过渡期间预测模型可能出现偏差。判断长间隔是正常过渡还是异常，可以关联 `display_frame_token`（即 VSync ID）的连续性：

1. 在 `FrameTimeline` 中找到刷新率切换的时间点（`expected_dur_ms` 从 8.33ms 变到 16.67ms 的位置）
2. 提取该帧前后的 `display_frame_token` 序列
3. 如果 `display_frame_token` 在切换点出现跳变（比如从连续递增变为跳过一个 token），说明调度器在切换时错过了目标 VSYNC
4. 如果 `display_frame_token` 序列连续，但 `actual_dur_ms` 明显大于 `expected_dur_ms`，问题更可能在 App 侧——App 没有在新频率下及时提交帧

```sql
SELECT
  actual.display_frame_token,
  ROUND(actual.ts / 1e6, 2) AS ts_ms,
  ROUND(actual.dur / 1e6, 2) AS actual_dur_ms,
  ROUND(expected.dur / 1e6, 2) AS expected_dur_ms,
  CASE WHEN actual.display_frame_token - LAG(actual.display_frame_token) OVER (ORDER BY actual.ts) > 1
       THEN 'vsync_gap' ELSE 'continuous' END AS vsync_continuity
FROM actual_frame_timeline_slice AS actual
LEFT JOIN expected_frame_timeline_slice AS expected
  ON actual.display_frame_token = expected.display_frame_token
 AND actual.surface_frame_token = expected.surface_frame_token
ORDER BY actual.ts
LIMIT 100;
```

切换点出现 `vsync_gap` 不一定需要修复。但如果 `vsync_gap` 伴随 `jank_type` 不为空，且频繁出现在同一个刷新率过渡方向（比如总是 120Hz→60Hz 时出现），就值得检查 `RefreshRateSelector` 的切换阈值是否合理。

[图：Game Mode 交互示意图。普通模式下刷新率上限较低，切到 Performance 模式后 VSYNC-app 间隔缩短，FrameTimeline 目标时长也随之缩短。]

## 功耗和体验上的取舍

高刷新率会让显示面板、显示子系统和合成节奏都更忙。页面长时间静止时继续保持高刷，收益很小，功耗却不会白白消失。ARR 的价值就在这里，它让系统在不牺牲当前体验的前提下，把无效刷新压下去。

这里不直接给固定百分比。不同面板、亮度、分辨率、OEM 策略和测试场景差异很大，离开测试条件去写“60Hz 到 120Hz 一定增加多少功耗”，说服力不够。做性能分析时，更实用的结论是：滚动、动画和游戏需要更高刷新率，静态阅读、AOD、低帧率视频更适合较低刷新率，是否切得准要回到 Trace 和电流数据里判断。

### 低频闪烁与 Gamma 补偿

LTPO 面板可以把刷新率压到极低（1Hz 甚至更低），用于 AOD 或静态内容展示。但物理面板在极低刷新率下会出现亮度抖动——驱动电压在长间隔内漂移，导致相邻帧之间的亮度不一致。这种抖动在低亮度环境下更明显。

[待验证] 部分面板/OEM 在低刷新率下通过硬件或固件层实现 Gamma 补偿，缓解驱动电压漂移导致的亮度抖动。source.android.com 的 ARR 文档只覆盖了 HWC3 `DisplayConfiguration.vrrConfig`、`vsyncPeriod`、`VrrConfig.minFrameIntervalNs`、`notifyExpectedPresent` 等 HAL 接口，未涉及实时 Gamma 补偿的 AIDL 字段或 Display HAL 接口定义。如果设备在低频模式下出现周期性亮度波动，可以先在面板厂商文档或 OEM HAL 实现中查找补偿逻辑，再决定是否需要在 Perfetto 中观察对应 counter。

## 版本演进要分两层看

- **Android 11-14**：系统已经支持多刷新率、`Surface.setFrameRate()` 和更成熟的 mode switching。这一阶段的重点是“能选多个刷新率”。
- **Android 15-QPR1 及以上**：官方 ARR 文档把 ARR 支持放在这个窗口，并要求设备实现对应 HAL API。这一阶段的重点是“刷新率能更细地跟着内容变化”。
- **Android 16（API 36）**：`Display.hasArrSupport()`、`Display.getSuggestedFrameRate()`、`Display.getSupportedRefreshRates()` 这组公开查询 API 让 App 更容易知道设备能力和系统建议值。ARR 系统能力与 App 可见 API 的版本边界需要分开写。[已验证: 官方文档, developer.android.com/reference/android/view/Display]

按这个时间线区分，适用范围就很明确。谈 Android 11-14 时，主要是在交代背景；谈 ARR 主体时，焦点应该放在 Android 15-QPR1 及以上。

## 常见误区

**把 `getSuggestedFrameRate()` 当成任意 fps 映射器。**  
它吃的是类别参数，不是 45、72、90 这类任意目标帧率。要谈具体 fps 到面板档位的关系，应该放到系统选择策略里讲。

**把 `FrameData` 写成带 `refreshRate` 字段的公开对象。**  
公开回调只有 `FrameData` 和 `FrameTimeline` 这些 API。`VsyncEventData` 是内部承载结构，不是 App 直接操作的对象。

**把 `Surface.setFrameRate()` 当成所有 UI 的主入口。**  
普通 View / RecyclerView / Compose 场景，先看 View 层和 Compose 层的 API。Surface 这一层更适合单独 surface 的媒体或游戏场景。

**看到 VSYNC 间隔变化就判成抖动。**  
ARR 本来就会改 VSYNC 周期。先分清是正常降频、模式切换，还是 missed frame。

## 扩展：Swappy 为什么还值得单独讲

游戏场景经常不直接跟着 Java UI 的节拍走，这时 Android Frame Pacing Library（Swappy）仍然很有价值。官方文档给出的说明很直接，它用 Android Choreographer 做同步，用 presentation timestamps 保证展示时机，再用 sync fences 避免 buffer stuffing。设备支持多刷新率时，Swappy 也会帮游戏把帧节奏对准当前显示能力。[已验证: 官方文档, developer.android.com/games/sdk/frame-pacing]

这部分和普通 View UI 的 ARR 不是同一层。前者更接近游戏渲染循环和 Surface / EGL / Vulkan 的提交时序，后者更偏向 View、Compose 和系统滚动组件的刷新率投票。

## 参考资料

### Android 17 RefreshRateSelector 多维度评分算法与 ARR 实现机制
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-13-android-refreshrate-selector-arr.md
- 类型：DeepResearch 调研结果
- 摘要：源码级解析 Android 15 引入的 ARR（Adaptive Refresh Rate）机制：RefreshRateSelector 多维度评分算法（帧率 divisor 匹配、亮度阈值、场景优先级、功耗预算），DisplayModeDirector 核心编排逻辑，HWC HAL v3 帧率提示接口。厘清 ARR 与传统 VRR 的本质差异（单模内动态调整 vs 模式切换）。
- 注入时间：2026-05-14
- 价值：对理解 Android 自适应刷新率完整架构和 VSync 解耦机制有直接帮助，填补 ARR 概念盲区


- AOSP 源码路径：
  - `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp`（内容刷新率选择）
  - `frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.h`
  - `frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java`（policy/range 控制）
  - `frameworks/base/services/core/java/com/android/server/display/DisplayManagerService.java`
  - `frameworks/base/core/java/android/view/Display.java`
  - `frameworks/base/core/java/android/view/View.java`
  - `frameworks/base/core/java/android/view/Choreographer.java`
  - `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`
  - `frameworks/native/services/surfaceflinger/Scheduler/VsyncModulator.cpp`
- 官方文档：
  - `https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate`
  - `https://developer.android.com/reference/android/view/Display`
  - `https://developer.android.com/reference/android/view/View`
  - `https://developer.android.com/reference/android/view/Surface`
  - `https://developer.android.com/reference/android/view/Choreographer.FrameData`
  - `https://developer.android.com/games/sdk/frame-pacing`
  - `https://perfetto.dev/docs/data-sources/frametimeline`
  - `https://perfetto.dev/docs/analysis/stdlib-docs`



