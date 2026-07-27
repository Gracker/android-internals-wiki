---
title: "可变刷新率渲染管线"
chapter: "18.19"
status: finalized
applicable_versions: "多刷新率背景：Android 11 (API 30) - Android 14；ARR 主体：Android 15-QPR1 - Android 17 (API 37)；Display 查询 API：Android 16 (API 36)"
last_verified: "2026-07-26"
last_verified_against: "AOSP android-17.0.0_r1 frameworks/base + frameworks/native SurfaceFlinger Scheduler；Android Developers ARR/View/Display/Surface 文档；Perfetto android.frames.timeline stdlib"
confidence: high
sources:
  - type: official
    path: https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate
  - type: official
    path: https://developer.android.com/reference/android/view/View
  - type: official
    path: https://developer.android.com/reference/android/view/Display
  - type: official
    path: https://developer.android.com/reference/android/view/Surface
  - type: official
    path: https://perfetto.dev/docs/analysis/stdlib-docs
  - type: aosp
    path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java
  - type: aosp
    path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java
  - type: aosp
    path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java
  - type: aosp
    path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp
  - type: aosp
    path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp
  - type: aosp
    path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp
tags: ["VRR", "ARR", "Variable-Refresh-Rate", "LTPO", "setFrameRate", "FrameTimeline", "渲染管线"]
related_chapters: ["2.3", "2.18", "2.19"]
created_by: "rendering-pipelines-merge"
created_date: "2026-04-09"
pipeline_stage: ready-to-publish
reviewed_by: openclaw-task6
reviewed_date: "2026-06-12"
task6_result: pass-light-edit
task6_state: reviewed
last_task6_audit: "2026-06-13"
task9_result: auto-fixed
task9_state: reviewed
task9_reviewed_date: 2026-06-12
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-12T00:20:00+08:00"
last_task9_audit: 2026-06-12
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-04-26T14:46:27+08:00"
repaired_date: "2026-04-26"
repaired_by: openclaw-task2b
last_task9_autofix_at: 2026-06-12
last_task9_review_log: "logs/deep-review/2026-06-12-00-audit.md"
updated_date: 2026-06-12
updated_by: openclaw-task9
task9_review_notes: "2026-06-12 00:20 Task9 idle audit auto-fix: 修正 18.19 源码补充段的版本锚点与两个源码符号名；AOSP android-16.0.0_r4 与官方 ARR/Perfetto 文档复核无新增 P0/P1，回到 Task6 复审。"
last_idle_audit_at: "2026-07-26T10:37:31+08:00"
last_idle_audit_run_id: "20260726-103558-idle-audit-c11ac4a7"
last_idle_audit_log: "logs/audit/2026-07-26-20260726-103558-idle-audit-c11ac4a7-idle-audit.md"
last_task9_audit_log: "logs/audit/2026-07-26-20260726-103558-idle-audit-c11ac4a7-idle-audit.md"
idle_audit_notes: "2026-07-26 Hermes idle audit: 补齐 last_verified/confidence/sources；按 android-17.0.0_r1 复核 Scheduler.cpp 与 RefreshRateSelector.cpp 的同名入口，修正源码锚点函数名 calculateLayerScoreLocked；未发现 Android 18/API38 越界或需降级问题。"

last_task6_at: "2026-06-12T04:05:00+08:00"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-05
---

<!-- outline-start -->

**锚点（必须覆盖）：**
- VRR、多刷新率、ARR 的边界
- App 端 API：`Surface.setFrameRate()`、Android 15 的 `View.setRequestedFrameRate()` / Compose、Android 16 的 `Display` 查询 API
- `VSYNC-app` / `VSYNC-sf` 的动态周期
- missed deadline 仍会表现为 app / sf jank，ARR 不会把慢帧直接修成准时帧
- 在 Perfetto 中按统一口径分析：`VSYNC-app`、`VSYNC-sf`、`expected_frame_timeline_slice`、`actual_frame_timeline_slice`、refresh-rate selection slice

**扩展（可选深入）：**
- LTPO 面板与 device-specific HAL support
- 视频播放场景的帧率投票
- 静态页面的低刷新率驻留

<!-- outline-end -->

## 为什么这一节容易误判

固定刷新率设备上，分析入口很稳定。60Hz 对应 16.67ms，120Hz 对应 8.33ms，超过预算就去找慢帧。到了支持可变刷新率的设备，这个预算不再固定。`VSYNC-app` 和 `VSYNC-sf` 的间隔可能在 8.33ms、16.67ms、33.3ms 或其他离散档位之间变化，静态页面和低帧率内容也会主动把目标周期拉长。

误判通常出在第二步。刷新周期变长，不等于系统把一帧已经超时的工作补救回来。刷新率选择仍然要经过 App 投票、内容节奏判断、Scheduler 决策和设备能力约束。某一帧一旦错过自己的 `expected_frame_timeline_slice`，Perfetto 里依旧会落到 app jank 或 sf jank。ARR 改变的是目标节拍，不会消掉 deadline。

分析时还要分开三种频率：

- **内容帧率**：视频、游戏或动画每秒产生多少个不同内容帧，例如 24fps。
- **应用 render rate**：Choreographer/producer 被允许或选择以多快的节奏生成帧。
- **Display refresh rate**：面板每秒刷新多少次，例如 120Hz。

24fps 内容可以在 120Hz Display 上每帧重复 5 次；60fps render rate 也可能运行在 120Hz 面板上。`setFrameRate(24)` 表达内容/渲染偏好，不保证面板一定切成 24Hz，更不是 producer 的限速器。

## VRR、多刷新率和 ARR 的边界

| 名称 | 关注点 | 章节里怎么用 |
|:---|:---|:---|
| 多刷新率 | 设备在 60Hz、90Hz、120Hz 等固定 Display mode 之间选择 | Android 11–14 的公开帧率 API 主要在这个背景下使用 |
| VRR | 面板/Composer 能在能力范围内动态改变 VSync 周期，不必把每个 render rate 都表示成独立固定 mode | 硬件与 HAL 能力，不能只由“面板是 LTPO”推出 |
| ARR | Android 根据 View/Surface vote、内容 cadence、touch/transition 等策略选择 render/refresh rate | 支持设备从 Android 15-QPR1+ 提供，Android 16 增加公开能力查询 |

LTPO 面板常和 ARR 同时出现，因为它更容易覆盖宽刷新率范围；它不是 ARR 的充分条件。官方要求设备运行 Android 15-QPR1+ 并实现指定 HAL API。应用到 API 36 才能通过 `Display.hasArrSupport()` 做公开查询。

## 系统如何决定刷新节奏

刷新率选择可以拆成三层。

- **App 投票层**：Android 11+ 的 `Surface.setFrameRate()`、Android 15（API 35）的 `View.setRequestedFrameRate()`，以及滚动时的 `setFrameContentVelocity()` 表达内容更新需求。Compose 1.9 的 `preferredFrameRate()` 会汇总 composable 的偏好。
- **系统策略层**：SurfaceFlinger 汇总可见 layer 的 vote/历史 cadence，并结合 focus、touch boost、window transition、idle、policy range 等信号给候选 render/physical rate 评分。
- **设备能力层**：Display mode、seamless switch group、面板和 device-specific HAL support 约束最终能否使用 ARR；不满足 ARR 条件时仍可能做离散 mode switching。

```text
App vote / content cadence
        ↓
SurfaceFlinger + Scheduler choose refresh rate
        ↓
VSYNC-app / VSYNC-sf interval changes
        ↓
App draw → queueBuffer → SurfaceFlinger compose → present
```

这张图里的 vote 是提示，不是命令。当前可见的其他 App/SystemUI layer、触控状态和电源策略都可能改变结果；刷新周期已经变化，也不能反向证明某一个 View vote 被原样采纳。

## App 端 API

### Android 11+：`Surface.setFrameRate()` 表达 Surface 内容节奏

Android 11 把 `Surface.setFrameRate()` 放进公开 API。视频、游戏和独立 `SurfaceView` producer 常在这一层告诉系统当前 Surface 的目标节奏。

```java
surface.setFrameRate(24f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
surface.setFrameRate(60f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
surface.setFrameRate(0f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
```

`FRAME_RATE_COMPATIBILITY_FIXED_SOURCE` 适合视频等固定 cadence 内容，系统可以选择其整数倍刷新率。`DEFAULT` 更适合游戏/UI 等可随显示节奏运行的 producer。该 API 不会替应用 pacing：请求 60fps 后仍以 120fps 连续 queue buffer，依旧可能产生 buffer stuffing 和额外功耗。

API 31+ 的三参数重载还允许选择 `CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS` 或 `CHANGE_FRAME_RATE_ALWAYS`。后者可能引起可见黑屏/闪烁，只适合长时间视频等“匹配内容收益大于切换成本”的场景。清除 vote 时用 frame rate 0；API 34+ 也可调用语义更清楚的 `clearFrameRate()`。不要让上一段视频的 24fps vote 污染后续 UI。

### Android 15：View / Compose 开始直接表达刷新率偏好

`View.setRequestedFrameRate(float)` 在 API 35 加入。它既能写具体 fps，也能写类别常量。普通 UI 组件在这一层投票更自然，滚动场景还可以用 `setFrameContentVelocity(float)` 上报像素速度。

```java
view.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_NORMAL);
animationView.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
slowVisualizer.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_LOW);
list.setFrameContentVelocity(2400f);
```

View vote 有三个容易漏掉的约束：

- View 需要 redraw 时才投票；静止且不再 invalidated 的 View 不会永久占住高刷。
- API 35 在 `ViewGroup` 上调用不会自动传给 child View；API 36+ 若需要对子树生效，可评估 `ViewGroup.propagateRequestedFrameRate()`。
- `setFrameContentVelocity()` 的单位是 pixels/second，值只对下一次 drawn frame 有效；自定义 fling 组件要在每个绘制帧更新，而不是手势开始时只写一次。

Compose 1.9 对应 `Modifier.preferredFrameRate(frameRate)` 和 `Modifier.preferredFrameRate(frameRateCategory)`。同一帧里的 composable vote 会被收集、汇总，再作为偏好传到下层 layer；它不绕过 View/SurfaceFlinger 的策略。

`Display.hasArrSupport()` 不属于 API 35。面向 Android 15 的代码要把刷新率投票和设备能力查询拆开：投票走 `View` / Compose，能力查询只在 API 36+ 调用。

### Android 16：`Display` 查询 API 用来读能力和建议值

Android 16（API 36）补齐查询入口。`Display.hasArrSupport()` 判断设备是否公开支持 ARR，`Display.getSuggestedFrameRate(int)` 读取系统为 NORMAL/HIGH 类别配置的建议值。`getSupportedRefreshRates()` 在 Android 16+ 返回 Display 支持的 render rates；调查旧平台或分辨率与刷新率组合时还要看 `getSupportedModes()`。

```java
Display display = context.getDisplay();
if (display != null && display.hasArrSupport()) {
    float normal = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_NORMAL);
    float high = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_HIGH);
    float[] supported = display.getSupportedRefreshRates();
}
```

`getSuggestedFrameRate(int)` 的入参是类别，不是任意 fps。它适合回答“系统建议普通动画跑多快”或“当前场景是否值得升到高刷”，不适合把 45fps、72fps 这类业务目标直接塞进去做映射。

Android 15-QPR1 设备可能有 ARR 调度逻辑，却没有 API 36 的公开查询。应用在 API 35 上可以安全提交 View/Surface hint，由系统按能力处理；不要读取私有属性或维护机型白名单。诊断时再结合设备文档、实际 VSync 周期和 SurfaceFlinger 的 refresh-rate selection 证据确认是否启用。

### Android 15+：Window 级策略开关

API 35 还提供 Window 级的 `setFrameRateBoostOnTouchEnabled()` 和 `setFrameRatePowerSavingsBalanced()`。默认 touch boost 会在触摸和释放后一段时间提高节奏，普通交互窗口不建议关闭。power-savings balance 允许系统按需降低刷新率；只有出现经过 trace 证实的体验问题时才考虑禁用，因为代价通常是更高功耗。

这些开关是 Window policy，不是给某一帧指定 Hz。局部动画优先使用 View/Compose vote，视频/游戏 Surface 使用 `Surface.setFrameRate()`。

### 静态页面与视频不要用同一套 vote

静态页面没有新 invalidation/buffer 时，Scheduler 可以根据 idle 与 layer history 降低驻留刷新率；不必让每个静态 View 长期投 LOW。进入滚动或动画前，View toolkit 的 touch/motion policy 与新的 redraw vote 会再提高节奏。

视频更适合在承载视频的 Surface 上提交 `FIXED_SOURCE` vote，例如 24/30fps，让系统选择匹配 cadence 的 rate 或整数倍。若视频上方还有持续 60/120fps 更新的控件、字幕或 SystemUI layer，整屏选择要综合这些可见 layer，不能只按视频 fps 预测。

## Android 17 的 Scheduler 怎样处理 vote

Android 17 的 `Scheduler::chooseRefreshRateForContent()` 先让 `LayerHistory` 汇总可见 layer 的近期需求，再把 content requirements 交给 policy/selector。`RefreshRateSelector` 对候选 render rate 与 physical mode 排序，评分会考虑：

- layer 的可见权重、focus 和期望 frame rate；
- `ExplicitExact`、`ExplicitExactOrMultiple`、`ExplicitGte`、`ExplicitDefault`、`ExplicitCategory`、`Heuristic` 等 vote 语义；
- 候选刷新率是否能整除/覆盖内容 cadence；
- switch 是否 seamless、候选是否在 primary physical/render range；
- touch、idle、power mode 等全局信号。

这不是一张固定的“vote 优先级表”。例如 `ExplicitExact` 在支持 per-app frame-rate override 时可以接受目标 rate 的整数倍；`ExplicitGte` 对不低于目标的候选给满分；`NoVote`、`NoPreference` 和 `Min` 在 layer 评分循环中跳过。最终结果还要叠加其他可见 layer 的权重和系统 policy。

源码入口是 [Android 17 `Scheduler.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp) 与 [`RefreshRateSelector.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp) 的 `calculateLayerScoreLocked()` / `getRankedFrameRates()`。

`Scheduler.cpp` 里的 `FPS_THRESHOLD_FOR_KERNEL_TIMER = 65_Hz` 属于 hardware VSync idle 控制：timer reset 且当前 peak rate 高于 65Hz 时允许重新同步硬件 VSync；timer expired 且 rate 不高于 65Hz 时可关闭空闲 hardware VSync。它不是“低于 65fps 就把应用降频”的策略，也不能用于解释某一层的 frame-rate vote。

## 渲染过程里的 deadline 没有消失

支持 ARR 的设备上，`VSYNC-app` 和 `VSYNC-sf` 的节拍会跟着当前内容变化。滚动时周期可能收紧，静态页面可能拉长，SurfaceFlinger 侧也会出现 refresh-rate selection 相关的决策 slice。这个变化会直接改写“这一帧应该在多久内完成”的预算。

预算会变，deadline 还在。`expected_frame_timeline_slice` 给出的窗口一旦确定，App 线程、RenderThread 或 SurfaceFlinger 任何一段超时，`actual_frame_timeline_slice` 仍会留下 `on_time_finish`、`present_type`、`jank_type` 这些字段。分析慢帧时，应该把“当前目标周期是多少”和“这一帧有没有按时完成”分开读。

## 在 Perfetto 中分析 VRR / ARR

观察顺序和 §2.3、§2.18 保持一致：

- `VSYNC-app`：App 侧收到的节拍有没有从 8.33ms 拉到 16.67ms、33.3ms 或其他档位
- `VSYNC-sf`：SurfaceFlinger 的合成节拍是否同步变化
- `expected_frame_timeline_slice`：当前帧的目标窗口
- `actual_frame_timeline_slice`：真实完成情况、`on_time_finish`、`present_type`、`jank_type`
- refresh-rate selection slice：刷新率选择有没有频繁来回切换

不同 build 的 Scheduler slice/counter 名称可能变化。先用 SurfaceFlinger/Scheduler 轨道确认 active physical mode 与 render rate，再按时间关联 `chooseRefreshRateForContent`、ranking/selection、VSync 周期和 FrameTimeline token；不要只靠模糊匹配到的一条 “RefreshRate” slice 下结论。

### Android 12+：以 FrameTimeline 为入口

FrameTimeline 是 Android 12+ 更稳的入口。下面按 `upid + surface_frame_token + layer_name` 对齐 expected/actual，直接看到同一 SurfaceFrame 的预算和结果。不要使用错误的 `android_frames.jank_type` 列名，也不要写不存在的 `android.frames` 模块。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

WITH target_process AS (
  SELECT upid
  FROM process
  WHERE name = 'com.example.app'
  LIMIT 1
),
expected AS (
  SELECT *
  FROM expected_frame_timeline_slice
  WHERE upid = (SELECT upid FROM target_process)
    AND surface_frame_token IS NOT NULL
),
actual AS (
  SELECT *
  FROM actual_frame_timeline_slice
  WHERE upid = (SELECT upid FROM target_process)
    AND surface_frame_token IS NOT NULL
)
SELECT
  CAST(e.ts / 1e6 AS INTEGER) AS expected_ts_ms,
  e.layer_name,
  e.surface_frame_token,
  e.display_frame_token,
  CAST(e.dur / 1e6 AS FLOAT) AS budget_ms,
  CAST(a.dur / 1e6 AS FLOAT) AS actual_ms,
  a.on_time_finish,
  a.present_type,
  a.jank_type
FROM expected e
LEFT JOIN actual a
  ON a.upid = e.upid
 AND a.surface_frame_token = e.surface_frame_token
 AND a.layer_name = e.layer_name
ORDER BY e.ts DESC
LIMIT 30;
```

`budget_ms` 随当前调度目标变化是正常现象；`actual_ms > budget_ms` 也要以 `on_time_finish`、`present_type` 和 `jank_type` 的 FrameTimeline 判定为准。刷新率切换附近若出现异常，应把 selection slice、VSync 周期和对应 SurfaceFrame/DisplayFrame 放在同一时间窗，不能只凭一个长 duration 判为切换抖动。

### Android 10/11：回到 `doFrame` 和 VSync 时间窗

Android 10/11 没有 FrameTimeline 主表时，判断顺序回到 `Choreographer#doFrame`、`VSYNC-app`、`VSYNC-sf` 和 SurfaceFlinger 的同一时间窗。固定 16.67ms 阈值在低帧率目标下会误报，诊断时先确认当前节拍有没有变化，再看 `doFrame` 是否真的超出这一档的预算。

```sql
SELECT
  CAST(ts / 1e6 AS INTEGER) AS ts_ms,
  CAST(dur / 1e6 AS FLOAT) AS doframe_ms
FROM slice
WHERE name GLOB 'Choreographer#doFrame*'
ORDER BY dur DESC
LIMIT 20;
```

这一步只负责圈出慢帧窗口。后续还要回到 UI，把 `VSYNC-app`、`VSYNC-sf` 和 SurfaceFlinger 合成片段放到同一时间窗里比较，确认问题出在 App、合成，还是刷新率选择本身。

## 版本演进

| 版本 | 公开能力 | 分析重点 |
|:---|:---|:---|
| Android 11 | `Surface.setFrameRate()` + 多刷新率 mode switching | 区分固定 mode 切换和普通慢帧 |
| Android 12-14 | Android 12 开始有 FrameTimeline，可把目标窗口和真实完成时间拆开看 | 这一阶段仍以多刷新率背景为主 |
| Android 15 / 15-QPR1+ | `View.setRequestedFrameRate()`、`setFrameContentVelocity()`、Window touch/power policy；支持设备启用 ARR | 把 View vote、touch/scroll policy 与 Scheduler 决策放到同一时间窗 |
| Android 16 | `Display.hasArrSupport()`、`Display.getSuggestedFrameRate(int)` | 公开查询能力和 NORMAL/HIGH 建议值 |
| Android 17 | 延续 ARR API，并以 `android-17.0.0_r1` 的 layer ranking、attached Choreographer 更新和 per-display Scheduler 为源码基线 | 不把某条 vote、LTPO 标签或 65Hz idle timer 阈值当作最终选择结果 |

Android 11–14 负责交代多刷新率背景，Android 15-QPR1+ 进入 ARR 主体，Android 16 补齐公开能力查询，Android 17 仍沿用同一职责划分。

Compose 1.9 的 `preferredFrameRate()` 属于 Jetpack 版本演进，不和某个 Android 平台版本一一绑定；能否产生 ARR 效果仍取决于运行设备的系统与 Display 能力。

## 与其他章节的关系

- **2.3 VSync 机制**：解释 `VSYNC-app`、`VSYNC-sf` 和 phase offset
- **2.18 Adaptive Refresh Rate**：展开 ARR 的机制、API 和 Scheduler 选择逻辑
- **2.19 刷新率切换与帧率适配**：继续看 mode switching 和切换开销

## 参考资料

- [Android Developers：Adaptive refresh rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
- [Android API：View](https://developer.android.com/reference/android/view/View)
- [Android API：Display](https://developer.android.com/reference/android/view/Display)
- [Android API：Surface](https://developer.android.com/reference/android/view/Surface)
- [Android API：Window](https://developer.android.com/reference/android/view/Window)
- [Perfetto：FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [PerfettoSQL：android.frames.timeline](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Android 17 AOSP：View.java](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/View.java)
- [Android 17 AOSP：Display.java](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Display.java)
- [Android 17 AOSP：Surface.java](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java)
- [Android 17 AOSP：Scheduler.cpp](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/Scheduler.cpp)
- [Android 17 AOSP：RefreshRateSelector.cpp](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp)
