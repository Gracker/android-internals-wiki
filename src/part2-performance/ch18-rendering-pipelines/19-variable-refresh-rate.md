---
title: "可变刷新率渲染管线"
chapter: "18.19"
status: finalized
applicable_versions: "多刷新率背景：Android 11 (API 30) - Android 14；ARR 主体：Android 15-QPR1 - Android 17 (API 37)；Display 查询 API：Android 16 (API 36)"
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

last_task6_at: "2026-06-12T04:05:00+08:00"
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

## VRR、多刷新率和 ARR 的边界

| 名称 | 关注点 | 章节里怎么用 |
|:---|:---|:---|
| 多刷新率 | 设备在 60Hz、90Hz、120Hz 这类固定 mode 之间切换 | 这是 Android 11-14 的主要背景 |
| ARR | 系统按内容节奏选择更合适的刷新率，减少高刷驻留和 mode switch 抖动 | 公开能力从 Android 15-QPR1+ 开始完整出现 |
| VRR | 面板和显示栈支持动态变频的硬件能力 | 这是设备条件，是否可用以系统 API 和 HAL 支持为准 |

LTPO 面板经常和 ARR 一起出现，因为它更容易覆盖更宽的刷新率范围。但 LTPO 不是 ARR 的充分条件。设备需要公开相应的 HAL 能力，App 再通过公开 API 判断系统是否支持。

## 系统如何决定刷新节奏

刷新率选择可以拆成三层。

- **App 投票层**：Android 11+ 的 `Surface.setFrameRate()`、Android 15（API 35）的 `View.setRequestedFrameRate()` / Compose `preferredFrameRate()`，以及滚动时的 `setFrameContentVelocity()` 都在表达内容需要多快更新。Android 16（API 36）的 `Display.hasArrSupport()` 只负责能力查询，不参与 API 35 设备上的投票调用。
- **系统决策层**：SurfaceFlinger 收集可见 Layer 的更新节奏、事务状态和显示约束，再由 Scheduler 选当前更合适的刷新率。
- **设备能力层**：面板能力和 device-specific HAL support 决定系统到底能不能用 ARR；不满足时只能回到多刷新率 mode switching。

```text
App vote / content cadence
        ↓
SurfaceFlinger + Scheduler choose refresh rate
        ↓
VSYNC-app / VSYNC-sf interval changes
        ↓
App draw → queueBuffer → SurfaceFlinger compose → present
```

这里的边界有两层：Composer 版本和面板类型不能写成唯一前提；慢帧和刷新周期拉长也不是同一件事，否则会漏掉 Scheduler 决策和设备能力约束。

## App 端 API

### Android 11-14：`Surface.setFrameRate()` 是公开入口

Android 11 把 `Surface.setFrameRate()` 放进公开 API，App 可以直接告诉系统当前 Surface 更接近哪种内容节奏。视频播放和单 Surface 渲染场景最常用这一层。

```java
surface.setFrameRate(24f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE);
surface.setFrameRate(60f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
surface.setFrameRate(0f, Surface.FRAME_RATE_COMPATIBILITY_DEFAULT);
```

这套能力主要服务多刷新率设备。系统会在支持的 mode 集合里做选择，分析时要把它和 Android 15-QPR1+ 的 ARR 分开写。

### Android 15：View / Compose 开始直接表达刷新率偏好

`View.setRequestedFrameRate(float)` Added in API level 35 (Android 15)。它既能写具体 fps，也能写类别常量。普通 UI 组件在这一层给投票更自然，滚动场景还可以配合 `setFrameContentVelocity(float)` 告诉系统当前内容速度。

```java
view.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_NORMAL);
animationView.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
staticPanel.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_LOW);
list.setFrameContentVelocity(2400f);
```

Compose 对应的是 `Modifier.preferredFrameRate(frameRate)` 和 `Modifier.preferredFrameRate(frameRateCategory)`。这一层表达的是偏好，系统会综合这些输入做刷新率选择。

`Display.hasArrSupport()` 不属于 API 35。面向 Android 15 的代码要把刷新率投票和设备能力查询拆开：投票走 `View` / Compose，能力查询只在 API 36+ 调用。

### Android 16：`Display` 查询 API 用来读能力和建议值

Android 16 (API 36) 补齐了查询入口。`Display.hasArrSupport()` 判断设备是否公开支持 ARR，`Display.getSuggestedFrameRate(int)` 读取系统建议值。支持档位仍可通过 `getSupportedRefreshRates()` 查看。

```java
Display display = context.getDisplay();
if (display != null && display.hasArrSupport()) {
    float normal = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_NORMAL);
    float high = display.getSuggestedFrameRate(Display.FRAME_RATE_CATEGORY_HIGH);
    float[] supported = display.getSupportedRefreshRates();
}
```

`getSuggestedFrameRate(int)` 的入参是类别，不是任意 fps。它适合回答“系统建议普通动画跑多快”或“当前场景是否值得升到高刷”，不适合把 45fps、72fps 这类业务目标直接塞进去做映射。

Android 15 QPR 设备可能已经有 ARR 调度逻辑，但没有 `Display.hasArrSupport()`。这类设备只能用机型白名单和 Perfetto 中 refresh-rate selection 片段辅助确认，不能把 API 36 查询失败直接判成不支持。

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

### Android 12+：以 FrameTimeline 为入口

FrameTimeline 是 Android 12+ 更稳的入口。这里直接查 `actual_frame_timeline_slice`，不要再用错误的 `android_frames.jank_type` 列名，也不要再写不存在的 `android.frames` 模块。

```sql
INCLUDE PERFETTO MODULE android.frames.timeline;

SELECT
  CAST(ts / 1e6 AS INTEGER) AS ts_ms,
  layer_name,
  CAST(dur / 1e6 AS FLOAT) AS actual_ms,
  on_time_finish,
  present_type,
  jank_type
FROM actual_frame_timeline_slice
WHERE upid = (
  SELECT upid
  FROM process
  WHERE name = 'com.example.app'
  LIMIT 1
)
ORDER BY ts DESC
LIMIT 30;
```

正常样本里，`VSYNC-app` 间隔会跟着交互状态变化，但 `actual_frame_timeline_slice` 大多仍然是 `jank_type = 'None'`，`on_time_finish = 1`。异常样本里，刷新率切换窗口附近会同时出现长 `actual_ms`、非空 `jank_type`，或者 refresh-rate selection slice 短时间反复切换。

### Android 10/11：回到 `doFrame` 和 VSync 时间窗

Android 10/11 没有 FrameTimeline 主表时，判断顺序回到 `Choreographer#doFrame`、`VSYNC-app`、`VSYNC-sf` 和 SurfaceFlinger 的同一时间窗。固定 16.67ms 阈值在低帧率目标下会误报，诊断时先确认当前节拍有没有变化，再看 `doFrame` 是否真的超出这一档的预算。

```sql
SELECT
  CAST(ts / 1e6 AS INTEGER) AS ts_ms,
  CAST(dur / 1e6 AS FLOAT) AS doframe_ms
FROM slice
WHERE name = 'Choreographer#doFrame'
ORDER BY dur DESC
LIMIT 20;
```

这一步只负责圈出慢帧窗口。后续还要回到 UI，把 `VSYNC-app`、`VSYNC-sf` 和 SurfaceFlinger 合成片段放到同一时间窗里比较，确认问题出在 App、合成，还是刷新率选择本身。

## 版本演进

| 版本 | 公开能力 | 分析重点 |
|:---|:---|:---|
| Android 11 | `Surface.setFrameRate()` + 多刷新率 mode switching | 区分固定 mode 切换和普通慢帧 |
| Android 12-14 | Android 12 开始有 FrameTimeline，可把目标窗口和真实完成时间拆开看 | 这一阶段仍以多刷新率背景为主 |
| Android 15 / 15-QPR1+ | `View.setRequestedFrameRate()`、`setFrameContentVelocity()`、Compose `preferredFrameRate()`；支持设备开始公开 ARR 能力 | 把 View / Compose 投票和 Scheduler 决策放到同一张图里读 |
| Android 16 | `Display.hasArrSupport()`、`Display.getSuggestedFrameRate(int)` | 先判断设备支持，再读取系统建议值 |

把这张时间线拆开之后，章节里的边界会更稳。Android 11-14 负责交代多刷新率背景，Android 15-QPR1+ 才进入 ARR 主体，Android 16 再把能力查询入口补齐。

## 与其他章节的关系

- **2.3 VSync 机制**：解释 `VSYNC-app`、`VSYNC-sf` 和 phase offset
- **2.18 Adaptive Refresh Rate**：展开 ARR 的机制、API 和 Scheduler 选择逻辑
- **2.19 刷新率切换与帧率适配**：继续看 mode switching 和切换开销

## 参考资料

- Android 官方文档：<https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate>
- Android 官方文档：<https://developer.android.com/reference/android/view/View>
- Android 官方文档：<https://developer.android.com/reference/android/view/Display>
- Android 官方文档：<https://developer.android.com/reference/android/view/Surface>
- Perfetto stdlib：<https://perfetto.dev/docs/analysis/stdlib-docs>
- AOSP 路径：
  - `frameworks/base/core/java/android/view/View.java`
  - `frameworks/base/core/java/android/view/Display.java`
  - `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`

---


<!-- AIW-源码调研-2026-05-31 -->
**源码锚点补充（android-16.0.0_r4 复核）：**
- `Scheduler.cpp` 的 `chooseRefreshRateForContent()` 实际通过 `RefreshRateSelector::getRankedFrameRates()` 计算分数
- `RefreshRateSelector.cpp` 的 `calculateLayerScore()` 中，`FrameRateCategory::NoPreference` 或 `isNoVote()` 的 Layer 直接跳过（关键剪枝逻辑）
- LayerVote 优先级：ExplicitExact(1.0) > ExplicitGte(0.75f 阈值) > Heuristic(计算 divisor 距离) > Min(跳过)
- VRR 启用时 `VSYNC-app/sf` 周期动态变化，但 missed deadline **仍表现为 jank**，ARR 只改变目标节拍不补救慢帧
- `KernelIdleTimerController` / `IdleTimer` 控制 kernel idle timer；`Scheduler.cpp` 里 `FPS_THRESHOLD_FOR_KERNEL_TIMER = 65_Hz`，刷新率 ≤65Hz 时用于降功耗

<!-- AIW-源码调研-2026-05-31 -->
