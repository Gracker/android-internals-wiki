---
title: 帧率与刷新率
chapter: '2.2'
section: '2.2'
status: finalized
reviewed_date: "2026-04-30"
reviewed_by: openclaw-task6
review_note: Task 6 三审(2026-04-30):移除 AIW 编辑注释 3 处、frontmatter 去重 1 处;task9 仍 needs-rework
rework_date: '2026-04-02'
rework_by: openclaw-task2b
polish_count: 1
polish_date: '2026-04-06'
polish_by: task2b-polish
applicable_versions: Android 4.1 (API 16) - Android 16 (API 36)
last_verified: '2026-04-24'
last_verified_against: AOSP android-16.0.0_r1, 官方文档最新版本, Android 35 SDK sources
confidence: high
sources:
- type: official
  path: https://developer.android.com/reference/android/view/Choreographer
- type: official
  path: https://developer.android.com/games/sdk/frame-pacing
- type: official
  path: https://developer.android.com/develop/ui/views/layout/swinging-area
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
- type: official
  path: https://developer.android.com/reference/android/view/View#setRequestedFrameRate(float)
- type: official
  path: https://developer.android.com/reference/android/view/Window#setFrameRatePowerSavingsBalanced(boolean)
- type: aosp
  path: frameworks/base/core/java/android/view/DisplayEventReceiver.java
- type: research
  path: Android-Internal-Wiki/intake/research-feeds/2026-03-30-15-arr-vsync-android15-16.md
- type: aosp
  path: frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
tags:
- framerate
- refresh-rate
- frame-time
- jank
- frame-pacing
- LTPO
- VRR
- ARR
- SurfaceFlinger
related_chapters:
- '2.1'
- '2.3'
- '2.4'
- '2.6'
- '2.9'
- '7.1'
re-review-result: 已纳入1条素材(部分纳入:OEM VSync修改误区+交叉引用),0处修正,待正常review质检
pipeline_stage: ready-to-publish
task6_result: pass-light-edit
task6_state: revisiting
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-23"
task2b_result: fixed
task2b_state: "fixed"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-23T00:20:00+08:00"
last_task9_audit: "2026-05-22"
last_task9_audit_log: "logs/deep-review/2026-05-22-22-audit.md"
task9_review_notes: "2026-05-23 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 3；仅留下官方文档 URL、Perfetto SQL 可执行性与功耗数据口径建议。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
task2b_rework_note: "2026-05-22 2B修复: getSnapshot→summarize+chooseRefreshRateForContent; LayerVoteType 7→9种(补ExplicitGte/ExplicitCategory); ExplicitExact条件化(supportsAppFrameRateOverrideByContent). 前轮: Frame Time口径拆分; setFrameTimeline版本边界拆分"
last_task6_audit: "2026-05-19"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-28
---

# 帧率与刷新率

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 帧率基础:FPS、帧时间(Frame Time)、帧间隔一致性
- 🔹 刷新率演进:60Hz → 90Hz → 120Hz → LTPO 动态刷新率
- 🔹 多刷新率下的渲染挑战:SurfaceFlinger 如何选择刷新率
- 🔹 Frame Pacing:Choreographer 如何对齐帧边界
- 🔹 掉帧(Missed Frame / Janky Frame)的定义与量化

### 扩展(可选深入)

- 🔸 Game Mode / Frame Rate 策略对渲染的影响
- 🔸 LTPO 面板的工作原理与 Android 的适配
- 🔸 120Hz 场景的功耗权衡与智能降帧策略

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 开头:为什么要理解帧率与刷新率

打开 Perfetto,我们会看到主线程上一段一段的 `Choreographer#doFrame` 切片--有的短短几毫秒,有的却拖成了一条长长的红条。如果我们数一下这些切片之间的间距,可能会发现一个有趣的现象:大部分切片之间是等距的(比如每隔 16.6ms 一个),但偶尔会出现一个间距突然变成了 33ms 或更长。这个"突然变长"的间距,就是掉帧--用户感知到的卡顿。

要理解为什么会掉帧、怎么分析掉帧,我们先得搞清楚两个基本概念:**帧率**(App 画得多快)和**刷新率**(屏幕刷新得多快)。这两个东西听起来简单,但在现代 Android 设备上,它们之间的关系远比"画得快就显示得快"复杂得多。

原因在于,从 Android 11 开始,设备可以支持多种刷新率(60Hz、90Hz、120Hz 甚至动态 1-120Hz),而 App 的渲染帧率可以是任意的。当 App 的帧率和屏幕的刷新率不匹配时,就会出现画面不流畅、输入延迟增大、功耗浪费等问题。理解这两个维度的关系,是分析一切渲染性能问题的基础。

读完这一节,我们会知道:在 Perfetto 中看到"红色帧"时该怎么判断是帧率问题还是刷新率问题;为什么同一个 App 在 60Hz 手机上流畅,在 120Hz 手机上反而可能更卡;以及 Android 系统在背后做了哪些"匹配"工作来让这两者协调一致。

## 帧率基础:FPS、帧时间(Frame Time)、帧间隔一致性

### FPS:帧率的最直观度量

FPS(Frames Per Second)是我们最熟悉的帧率指标:一秒钟内 App 成功渲染了多少帧。60 FPS 意味着每秒 60 帧,每一帧的"预算时间"是 1000ms / 60 ≈ 16.6ms。120 FPS 对应 8.3ms,90 FPS 对应 11.1ms。

但 FPS 作为度量有一个明显的局限:它是一个**统计值**。一秒钟内渲染了 60 帧,整体 FPS 是 60,但实际可能是前 500ms 渲染了 55 帧(极快),后 500ms 只渲染了 5 帧(卡顿),用户感知到的却是明显的卡顿。也就是说,**同样的 60 FPS,流畅度可以天差地别**。

### 帧时间(Frame Time):每一帧的真实耗时

帧时间(Frame Time)是比 FPS 更精确的度量指标,它记录的是**单帧从开始到完成的耗时**。在 Perfetto 中,`Choreographer#doFrame` 切片的长度反映的是主线程帧回调的工作量——从 VSync-app 信号触发到 `doFrame()` 返回。这只是单帧耗时的一部分:它不包含 RenderThread 的 GPU 命令执行、SurfaceFlinger 的合成、以及从提交到屏幕呈现的等待时间。分析帧间隔和主线程工作量时用 `doFrame` 就够了;要量化完整帧耗时(Jank、呈现偏差)应优先看 Frame Timeline / FrameMetrics 的 TOTAL_DURATION、DEADLINE、GPU_DURATION。

帧时间的价值在于它能暴露 FPS 掩盖的问题。假设 60 FPS 目标下,连续四帧的帧时间分别是:8ms、8ms、40ms、8ms。FPS 计算看起来还不错(平均每帧 16ms),但那帧 40ms 的帧意味着用户看到了一个明显的卡顿--屏幕在那 40ms 内没有更新,用户的手指滑动在那一刻"粘住"了。

在 Perfetto 中,我们可以直接看到每一帧的帧时间。正常的帧时间应该在预算以内且波动很小(比如 60Hz 下每帧都在 10-16ms 之间)。如果某一帧突然跳到 30ms 或 50ms,那就是一个 Jank。

### 帧间隔一致性:流畅度的真正决定因素

帧间隔(Frame Interval)是连续两帧之间的时间差。这是决定用户感知流畅度的**最关键指标**。

为什么帧间隔比 FPS 更重要?因为人眼对"时间上的不均匀"非常敏感。我们来看一个对比:

**场景 A(均匀 60 FPS):** 每帧间隔稳定在 16.6ms,连续 60 帧如时钟般精确。

**场景 B(不均匀 60 FPS):** 59 帧耗时 1ms,1 帧耗时 941ms。平均下来 FPS 也是 60,但用户会看到一个长达近 1 秒的明显卡顿。

在 Perfetto 的 Frame Timeline 中,帧间隔的均匀性通过 **Expected Timeline** 和 **Actual Timeline** 的对比来可视化。当 Actual 和 Expected 对齐得很好时,帧间隔就是均匀的;当 Actual 偏移或拉长时,帧间隔就出现了不一致。

在 Perfetto SQL 中,我们可以这样查询帧间隔:

```sql
-- 计算 Choreographer#doFrame 回调间隔(仅反映主线程帧回调节奏)
SELECT
  ts,
  dur,
  (ts - LAG(ts) OVER (ORDER BY ts)) / 1e6 as frame_interval_ms
FROM slice
WHERE name = 'Choreographer#doFrame'
ORDER BY ts
LIMIT 100;
```

如果 `frame_interval_ms` 的值在 16.6ms 附近小幅波动(比如 15-18ms),说明帧间隔一致性好。如果出现 33ms、50ms 甚至更大的值,就是掉帧了。注意:这个 SQL 只能量化主线程帧回调间隔;完整帧耗时分析应使用 `actual_frame_timeline` 表的 `dur` 和 `jank_type` 字段。

### 三个指标的适用场景

| 场景 | 用什么指标 | 为什么 |
|------|-----------|--------|
| 快速评估整体性能 | FPS | 简单直观,适合对比 |
| 定位单帧卡顿 | Frame Time | 能精确找到问题帧 |
| 评估流畅度 | 帧间隔一致性 | 最接近用户感知 |
| 自动化监控 | FPS + Jank 比例 | 可设置告警阈值 |

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]
[已验证: 官方文档, perfetto.dev/docs/reference/track-events#android]

## 刷新率演进:60Hz → 90Hz → 120Hz → LTPO 动态刷新率

### 60Hz 时代:一个标准统治了十年

从第一代 Android 到 2019 年前后,几乎所有的 Android 手机都运行在 60Hz 刷新率。60Hz 是流畅度与功耗之间的工程平衡点:每帧 16.6ms 的预算足以让 UI 动画看起来流畅,同时对 CPU/GPU 和电池的压力在可接受范围内。

在 60Hz 时代,整个渲染管线都是围绕这个固定值设计的:Choreographer 每收到一个 VSync-app 信号就触发一次 `doFrame()`,SurfaceFlinger 每收到一个 VSync-sf 信号就合成一次。帧率目标和刷新率目标是同一个值--60,一切都很简单。

### 90Hz/120Hz 的到来:流畅度的飞跃与工程挑战

2019-2020 年,以一加 7 Pro(90Hz)和三星 Galaxy S20 系列(120Hz)为代表,高刷新率屏幕开始在 Android 阵营普及。120Hz 意味着每帧预算从 16.6ms 压缩到了 8.3ms--对 App 来说,必须在 8.3ms 内完成所有的 measure、layout、draw 和 GPU 渲染工作,才能不掉帧。

这对渲染管线提出了巨大的压力。在 60Hz 设备上表现良好的 App,在 120Hz 设备上可能频繁掉帧,因为它的帧时间本来就接近或超过 16.6ms,现在被要求在 8.3ms 内完成,自然力不从心。反过来,一些 App 即使能跑在 120Hz,也会因为持续满负荷渲染而导致功耗飙升。

高刷新率还带来一个新问题:**帧率和刷新率的匹配**。一个 App 以 60 FPS 渲染,在 120Hz 屏幕上会怎样?答案是每一帧会被屏幕显示两次(repeating),画面依然是流畅的,因为 120 正好是 60 的整数倍。但如果 App 以 45 FPS 渲染,在 120Hz 屏幕上就会出现不均匀的帧显示--有的帧显示 2 次(16.6ms),有的帧显示 3 次(25ms),造成微卡顿(micro-jank)。

### LTPO:从固定刷新率到动态刷新率

LTPO(Low-Temperature Polycrystalline Oxide)不是一种刷新率,而是一种**显示面板技术**,它让屏幕能够在更大的范围内动态调整刷新率--从最低 1Hz 到最高 120Hz(甚至更高)。

传统 LTPS(Low-Temperature Polycrystalline Silicon)面板的刷新率是固定的,要切换刷新率需要做一次完整的显示模式切换(display mode switch),这个过程有几十毫秒的开销,期间可能出现黑屏闪烁。LTPO 则通过在面板驱动层混合使用 LTPS 和 IGZO(Indium Gallium Zinc Oxide)晶体管,实现了在**同一显示模式下**的刷新率动态调整。

在 Android 层面,LTPO 面板的动态刷新率能力被抽象为一系列**支持的刷新率档位**。比如一块 LTPO 面板可能支持:1Hz、5Hz、10Hz、24Hz、30Hz、48Hz、60Hz、90Hz、120Hz 等多个离散档位。SurfaceFlinger 会根据当前的渲染需求,在这些档位之间选择最合适的一个。

LTPO 的典型工作场景:

- **静态页面**(如阅读新闻):刷新率降到 1-10Hz,屏幕几乎不耗电
- **视频播放**:匹配视频帧率(24Hz/30Hz/60Hz),避免帧率不匹配带来的 judder
- **普通滑动**:60Hz 就够用
- **快速滑动/游戏**:120Hz 提供最佳跟手性

[待补充:LTPO 面板在 Perfetto 中的刷新率变化 Track 截图]

### Android 对多刷新率的支持时间线

| Android 版本 | 刷新率相关能力 |
|-------------|--------------|
| Android 4.1-10 | 仅 60Hz(部分厂商自行实现高刷) |
| Android 11 | 正式支持多刷新率,引入 `Surface.setFrameRate()` API 和 Config Group |
| Android 12 | Frame Timeline 模块,可在 Perfetto 中可视化帧匹配情况 |
| Android 14 | Frame Rate Override 机制,系统可以针对特定 App 强制指定帧率 |
| Android 15 | 自适应刷新率(ARR),显示 VSync 率与刷新率解耦 |
| Android 16 | ARR 增强,`hasArrSupport()` / `getSuggestedFrameRate()` 新 API |

[已验证: 官方文档, developer.android.com/about/versions/11/features (多刷新率)]
[已验证: 官方文档, developer.android.com/about/versions/15/features (ARR)]
[已验证: 研究素材, Android-Internal-Wiki/intake/research-feeds/2026-03-30-15-arr-vsync-android15-16.md]

## 多刷新率下的渲染挑战:SurfaceFlinger 如何选择刷新率

### 核心问题:不再是"一个刷新率走天下"

在只有 60Hz 的时代,SurfaceFlinger 的工作很简单:每个 VSync-sf 信号到来时合成一次,帧率 = 刷新率,不需要做选择。但在支持 60Hz/90Hz/120Hz 的设备上,SurfaceFlinger 需要动态决定当前使用哪个刷新率。

这个决定不是随便做的。选错了,要么浪费功耗(120Hz 显示一个静态页面),要么产生卡顿(60Hz 显示一个 24FPS 的视频导致 judder)。

### SurfaceFlinger 的刷新率选择策略

SurfaceFlinger 会先拿到 Display policy 允许的候选刷新率,再按每个可见 Layer 的 vote、目标帧率、内容检测结果、触摸状态、是否支持 seamless 切换等信号给候选模式打分,选出分数最高的一项。整数倍关系只是部分 vote 的高分条件,不是唯一规则。

举个例子,如果屏幕上同时有两个活跃图层:
- 视频 Layer 以 24 FPS 播放
- UI Layer 以 60 FPS 更新

120Hz 往往会排在前面,因为它同时照顾了 24 FPS 视频的整数倍显示和 60 FPS UI 的交互节奏。如果 Battery Saver 把上限压到 60Hz,或者 Display policy 不允许某个模式参与排序,最终结果也可能是 60Hz 或 90Hz。

具体来说,SurfaceFlinger 的刷新率决策涉及以下输入:

1. **每个 Layer 的 `setFrameRate()` 请求**:App 通过 `Surface.setFrameRate()` 告知系统自己期望的帧率
2. **Layer 的实际提交频率与内容检测结果**:SurfaceFlinger 会统计 Layer 实际提交 Buffer 的平均 FPS,并把这类信息交给 `RefreshRateSelector` 做排序
3. **触摸状态**:当用户正在触摸屏幕时,会临时提升刷新率(touch boost),以改善跟手性
4. **DisplayManager 的策略边界**:系统会限定最低和最高刷新率范围,并过滤掉不允许参与的模式
5. **省电模式与其他系统约束**:在 Battery Saver 等场景下,刷新率上限可能被进一步收窄

### RefreshRateSelector 内部评分与投票合并算法

上面提到 SurfaceFlinger 会"给候选模式打分",具体怎么打分、投票怎么合并,源码中有明确的算法描述。

**投票合并三规则**(`RefreshRateSelector` 层的顶层逻辑):

1. **倍数优先**:投票 30Hz + 90Hz → 选取 90Hz。原理是整数倍关系在 LCD 显示中可避免拍频(beat frequency)。
2. **非倍数分类**:任意投票 > 60Hz → 归入 "HIGH" 类别;所有投票 ≤ 60Hz → "NORMAL" 类别。
3. **混合类别**:60Hz vote + HIGH vote → 120Hz(任一 HIGH 即推高到设备最高档);60Hz vote + 120Hz vote → 120Hz(倍数优先)。

**评分算法**(`RefreshRateSelector::getRankedFrameRates`):对每个候选刷新率计算 score,分数由以下因素构成:

| 因素 | 效果 |
|------|------|
| 匹配度(ratio = displayHz / desiredHz) | score 与 ratio2 成反比,偏差越大分数越低 |
| 整数倍加分 | exact match 或 integer multiple 有额外加分 |
| 无缝切换加成 | 同 Config Group 内的切换有约 5% 加成(seamless switch bonus) |
| 功耗偏好 | 较低刷新率模式有轻微功耗加分 |

**三种策略(Policy)**:`RefreshRateSelector` 实现三个策略层:

1. **DisplayManagerPolicy**:DisplayManager 设置的硬性范围约束(min/max Hz)
2. **OverridePolicy**:系统覆盖(如 Game Mode、开发者选项强制 120Hz),优先级最高
3. **NoOverridePolicy**:纯内容驱动,依赖 LayerHistory 汇总的 vote 和应用显式请求

**LayerHistory**(`services/surfaceflinger/Scheduler/LayerHistory.cpp`):负责追踪每个活跃 Layer 的帧率请求。它通过统计 Layer 实际提交 Buffer 的时间戳来估算平均 FPS。`LayerHistory::summarize(const RefreshRateSelector&, nsecs_t)` 由 `Scheduler::chooseRefreshRateForContent()` 周期性调用,汇总当前所有活跃 Layer 的 vote summary,再交给 `applyPolicy(&Policy::contentRequirements, ...)` 进行排序决策。

### App 如何参与刷新率选择

从 Android 11 开始,App 可以通过两个 API 来影响刷新率决策:

**Surface.setFrameRate()**:告诉系统自己期望的帧率。这是一个"建议"而非"命令"--最终决策权仍在 SurfaceFlinger。

```java
// 示例:视频播放 App 告知系统期望 24 FPS
surface.setFrameRate(24f, Surface.FRAME_RATE_COMPATIBILITY_FIXED_SOURCE,
    Surface.CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS);
```

`CHANGE_FRAME_RATE_ONLY_IF_SEAMLESS` 参数表示只有在不产生视觉中断(无缝切换)的情况下才切换刷新率。如果从 60Hz 切换到 120Hz 需要 mode switch(有黑屏风险),那系统可能就不会切换。

**WindowManager.LayoutParams.preferredDisplayModeId**:直接指定一个显示模式(包含分辨率和刷新率的组合)。这比 `setFrameRate()` 更强力,但需要 App 知道具体的 mode ID,且切换时可能有视觉中断。

### Android 15:View 和 Window 级帧率提示

Android 15(API 35)把帧率提示从 Surface 扩到了 View / Window 层,适合 UI 驱动的高刷场景。

- `View.setRequestedFrameRate(float)`:可以直接传 90f、120f 这类目标值,也可以传 `REQUESTED_FRAME_RATE_CATEGORY_NO_PREFERENCE`、`LOW`、`NORMAL`、`HIGH` 这四个类别常量。请求只作用在当前 View,不会从 ViewGroup 自动下传到子 View;View 持续 invalidation、持续出帧时,系统才会把它纳入后续决策。
- `Window.setFrameRatePowerSavingsBalanced(true)`:告诉系统这个窗口接受"流畅度和功耗一起平衡"。在高温、低电量或系统有功耗压力时,系统可以更积极地把窗口拉回较低刷新率。

```java
recyclerView.setRequestedFrameRate(View.REQUESTED_FRAME_RATE_CATEGORY_HIGH);
heroCard.setRequestedFrameRate(90f);
window.setFrameRatePowerSavingsBalanced(true);
```

这几层接口要分开用。视频、Camera 预览、游戏 Surface 这类直接 producer 继续优先用 `Surface.setFrameRate()`;普通 View 树里某一块区域需要更高跟手性时,再用 `View.setRequestedFrameRate()`;整窗愿意换续航时,再补 `Window.setFrameRatePowerSavingsBalanced(true)`。Android 15 没有单独的 `setRequestedFrameRateCategory()` 方法,类别常量就是传给 `setRequestedFrameRate(float)` 的特殊取值。

[已验证: Android 35 SDK sources, android/view/View.java、android/view/Window.java、api-versions.xml]

### Config Group:让切换无缝

Android 11 引入了 Config Group 的概念。厂商可以将"分辨率相同、仅刷新率不同"的显示模式归入同一组。在同一组内切换刷新率是"无缝的"(seamless),不会触发完整的 mode switch,因此不会有黑屏或闪烁。

这就是为什么现代手机在 60Hz 和 120Hz 之间切换时用户感知不到--因为这两个模式在同一个 Config Group 中,切换只是调整驱动参数,而不是重新配置整个显示管线。

### 在 Perfetto 中的表现

在 Perfetto 中,刷新率变化可以通过以下方式观察:

1. **Display Refresh Rate Track**:直接显示当前刷新率的变化。当刷新率切换时,这个 Track 上会出现阶梯状的变化。
2. **SurfaceFlinger 的 VSync-sf 间隔**:VSync-sf 信号之间的间距会随刷新率变化。120Hz 间距约 8.3ms,60Hz 时约 16.6ms。
3. **Frame Timeline**:Expected Timeline 的宽度会随刷新率变化,反映每帧预算时间的变化。

```sql
-- 在 Perfetto SQL 中查看刷新率变化事件
SELECT * FROM track_event
WHERE name LIKE '%refreshRate%'
ORDER BY ts;
```

[待补充:Perfetto 中 Display Refresh Rate Track 的截图,展示 60Hz/120Hz 切换过程]

[已验证: 官方文档, source.android.com/docs/core/display/multiple-refresh-rate]
[已验证: 官方文档, developer.android.com/reference/android/view/Surface#setFrameRate]

## Frame Pacing:Choreographer 如何对齐帧边界

### 为什么需要 Frame Pacing

假设一个 App 的渲染速度略快于屏幕刷新率--比如在 60Hz 屏幕(16.6ms 一帧)上,App 的帧时间是 15ms。看起来没问题对吧?每帧都在预算内完成。但实际表现可能会出现微卡顿。

原因如下:由于 App 的帧时间(15ms)略小于 VSync 周期(16.6ms),帧的提交时间会逐渐"漂移"。经过几帧之后,一帧的提交时间刚好跨过了 VSync 边界--前一帧的提交刚好赶上了 VSync N,但下一帧的提交虽然只晚了 15ms,却已经过了 VSync N+1 的时刻。于是这一帧要等到 VSync N+2 才能显示,导致这一帧的显示间隔变成了 16.6 + (16.6 - 15) = 18.2ms,而下一帧变成了 16.6 - 1.6 = 15ms。这种不均匀的显示间隔就是微卡顿。

Frame Pacing 的目标就是解决这类问题--确保帧的提交与 VSync 边界精确对齐,让每一帧的显示时间都尽可能均匀。

### Choreographer 的帧对齐机制

Choreographer 的核心设计就是基于 VSync 的帧对齐。当 App 调用 `invalidate()` 或 `requestLayout()` 时,不会立即开始绘制,而是通过 Choreographer 向系统"订阅"下一个 VSync-app 信号。等到信号到来时,Choreographer 才执行 `doFrame()`,开始这一帧的渲染工作。

这个"等 VSync"的机制本身就是一种 Frame Pacing--它保证每帧的渲染都从 VSync 边界开始,与屏幕刷新同步。在 2.3 节(VSync 机制)中我们详细讲了 VSync-app 信号的来源和分发,这里我们关注的是这个同步机制对帧率的影响。

Choreographer 在一个 VSync 周期内只会触发一次 `doFrame()`。也就是说,即使 App 在一个 16.6ms 周期内多次调用 `invalidate()`,最终也只会渲染一帧。这个设计通过 `mFrameScheduled` 标志位实现:

```java
// frameworks/base/core/java/android/view/Choreographer.java
// @ AOSP android-16.0.0_r1
private void scheduleFrameLocked(long now) {
    if (!mFrameScheduled) {
        mFrameScheduled = true;  // 只在未调度时才申请
        // ...
        mDisplayEventReceiver.scheduleVsync();
    }
}
```

这就是为什么在 Perfetto 中看到的 `Choreographer#doFrame` 是等间距的--它们与 VSync 同步。

### Android Frame Pacing Library(Swappy)

对于游戏等不使用 Choreographer 的场景(它们有自己的渲染循环),Android 提供了 Frame Pacing Library(Swappy),它是 Android Game Development Kit(AGDK)的一部分。

Swappy 的工作原理:

1. **利用 Choreographer 获取 VSync 时序**:即使是游戏,Swappy 也会通过 Choreographer 获取当前设备的 VSync 频率和相位信息。

2. **使用 Presentation Timestamp**:通过 OpenGL 的 `eglPresentationTimeANDROID` 或 Vulkan 的 `vkSwapchain` 的 `presentMode`,精确控制帧的呈现时间,而不是"渲染完就提交"。

3. **Sync Fence 防止管线堵塞**:使用 GPU 同步栅栏(EGL fence / VkFence)来检测 GPU 是否还在使用前一帧的 Buffer。如果 GPU 还没完成,Swappy 会主动等待,避免向渲染管线塞入过多帧导致延迟堆积。

4. **自动选择最佳刷新率**:在支持多刷新率的设备上,Swappy 会根据游戏的实际渲染速度,通过 `setFrameRate()` 向 SurfaceFlinger 传递刷新率偏好,由 SurfaceFlinger 做出最终决策。比如,一个跑不到 60 FPS 的游戏,在 90Hz 设备上可能会被安排以 45 FPS(90Hz 的一半)运行,而不是在 60Hz 下挣扎。


### API 33+ 的 Frame Timeline 选择

从 Android 13(API 33)开始,Choreographer 提供了更精细的帧对齐控制。`doFrame()` 回调现在可以获取多个候选的帧时间线(frame timeline),App 可以根据自己的渲染能力和需求选择最合适的一个:

```java
// API 33+ 使用 Choreographer.VsyncCallback 获取 Frame Timeline 信息
// frameworks/base/core/java/android/view/Choreographer.java
Choreographer.getInstance().postVsyncCallback(new Choreographer.VsyncCallback() {
    @Override
    public void onVsync(@NonNull Choreographer.FrameData frameData) {
        // frameData.getFrameTimeNanos() - 当前帧的 VSync 时间戳
        // frameData.getPreferredFrameTimeline() - 系统推荐的时间线
        Choreographer.FrameTimeline preferred = frameData.getPreferredFrameTimeline();
        long expectedPresentNanos = preferred.getExpectedPresentationTimeNanos();
        long deadlineNanos = preferred.getDeadlineNanos();

        // frameData.getFrameTimelines() - 所有候选时间线(按时间排序)
        // App 可以在其中选择一个最合适的来提交帧
        for (Choreographer.FrameTimeline timeline : frameData.getFrameTimelines()) {
            // 根据渲染能力和场景选择最合适的时间线
        }
    }
});
```

`FrameData` 是 API 33 新增的类,它封装了 VSync 相关的全部信息。相比之前只有一个 `frameTimeNanos`,现在 App 能拿到多个候选的帧时间线(`FrameTimeline`),每个时间线包含预期的呈现时间和渲染截止时间。这让 App 可以更智能地选择"我这帧应该在哪个 VSync 时刻显示"--如果渲染比较重,可以选择一个稍晚的时间线,避免匆忙提交导致掉帧。

`FrameTimeline` 中的 `deadlineNanos` 是这帧必须完成渲染的截止时间。如果 App 发现自己无法在系统推荐的时间线内完成,可以主动选择一个更晚的时间线,通过 `SurfaceControl.Transaction.setFrameTimeline()` 告知 SurfaceFlinger。这种"协商"机制比之前"死等 VSync"的方式灵活得多。但 `Choreographer.FrameTimeline` 的读取能力(API 33 `FrameData.getFrameTimelines()`)和向 SurfaceFlinger 设置目标呈现时间的能力版本门槛不同:API 33 起可读取候选 vsyncId 和预期呈现时间;`SurfaceControl.Transaction.setFrameTimeline(long)` 的公开入口则是 Android 16 通过 `@FlaggedApi(FLAG_SDK_DESIRED_PRESENT_TIME)` 释放的,Android 13-15 只有内部/系统路径或 NDK `SurfaceControl` 受限接口可用。


这个机制的目的是让 App 告诉 SurfaceFlinger:"我这帧在哪个 VSync 时刻显示最合适"。SurfaceFlinger 会据此在正确的时间提交帧,实现更精确的 Frame Pacing。

### 在 Perfetto 中观察 Frame Pacing

在 Perfetto 中,Frame Pacing 的效果可以通过 **Frame Timeline** 模块直观地看到:

- **Expected Timeline**(预期时间线):每一帧"应该"在什么时间段内完成渲染。这是系统根据刷新率计算出来的理想时间窗口。
- **Actual Timeline**(实际时间线):每一帧实际完成渲染并提交的时间。

当 Actual Timeline 和 Expected Timeline 紧密对齐时,Frame Pacing 工作良好。当 Actual 超出 Expected 的范围,就说明出现了问题:

- Actual 比 Expected 长 → 这帧渲染超时(Jank)
- Actual 在 Expected 之后很远才开始 → 这帧被延迟调度了

```sql
-- 在 Perfetto 中查找 Frame Timeline 相关的 Track
SELECT * FROM track_event
WHERE name LIKE '%FrameTimeline%' OR name LIKE '%Expected%'
ORDER BY ts
LIMIT 50;
```

[已验证: 官方文档, developer.android.com/games/sdk/frame-pacing]
[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/view/Choreographer.java]

## 掉帧(Missed Frame / Janky Frame)的定义与量化

### 什么是掉帧

掉帧(Dropped Frame / Missed Frame / Janky Frame)指的是某一帧没能在预算时间内完成渲染,导致屏幕在应该显示新帧的时候只能继续显示旧帧。用户感知到的就是画面"卡了一下"或"粘住了一瞬间"。

严格来说,"Missed Frame"和"Janky Frame"有细微区别:

- **Janky Frame**:帧时间超过了预算时间(比如 60Hz 下超过 16.6ms)。这是一帧"有问题"。
- **Missed Frame**:由于 Jank,这一帧没赶上 VSync 截止时间,被完全跳过,屏幕多显示了一次旧帧。这是 Jank 的严重后果。

所有的 Missed Frame 都是 Janky Frame,但不是所有 Janky Frame 都会导致 Missed Frame--如果一帧虽然超时但还来得及在下一个 VSync 之前提交(比如通过三缓冲),它就只是 Jank 但不是 Miss。

### 掉帧的量化方法

#### 方法一:FrameMetrics API(API 24+)

`FrameMetrics` 是 Android 提供的官方帧耗时监控 API,它可以细粒度地测量一帧的各个阶段耗时:

```java
// 在 Activity 中注册 FrameMetrics 监听
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
    Handler handler = new Handler(Looper.getMainLooper());
    getWindow().addOnFrameMetricsAvailableListener(
        (window, frameMetrics, dropCountSinceLastInvocation) -> {
            long totalDuration = frameMetrics.getMetric(
                FrameMetrics.TOTAL_DURATION);
            long inputDuration = frameMetrics.getMetric(
                FrameMetrics.INPUT_HANDLING_DURATION);
            long drawDuration = frameMetrics.getMetric(
                FrameMetrics.DRAW_DURATION);
            long issueDuration = frameMetrics.getMetric(
                FrameMetrics.COMMAND_ISSUE_DURATION);
            long gpuDuration = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                ? frameMetrics.getMetric(FrameMetrics.GPU_DURATION)
                : 0L;

            boolean isJanky = totalDuration > targetFrameTimeNanos;
            if (isJanky) {
                Log.w("FrameMetrics",
                    String.format("Jank! total=%.1fms input=%.1fms draw=%.1fms issue=%.1fms gpu=%.1fms",
                        totalDuration / 1e6,
                        inputDuration / 1e6,
                        drawDuration / 1e6,
                        issueDuration / 1e6,
                        gpuDuration / 1e6));
            }
        },
        handler);
}
```

FrameMetrics 提供的度量维度包括:

- `TOTAL_DURATION`:从 VSync 到帧显示完成的总耗时
- `INPUT_HANDLING_DURATION`(API 24+):Input 事件处理耗时
- `ANIMATION_DURATION`:动画计算耗时
- `LAYOUT_MEASURE_DURATION`:measure/layout 耗时
- `DRAW_DURATION`:draw 耗时
- `SYNC_DURATION`:同步阶段耗时(将绘制命令同步给 RenderThread)
- `COMMAND_ISSUE_DURATION`:命令下发阶段耗时,适合观察 UI 线程把绘制工作提交给渲染后端的成本
- `GPU_DURATION`(API 31+):GPU 实际执行渲染命令的耗时

API 24 到 API 30 没有独立的 `GPU_DURATION` 常量,排查 GPU 压力时通常把 `DRAW_DURATION`、`COMMAND_ISSUE_DURATION` 和 Perfetto 的 Frame Timeline 一起看;API 31+ 再把 `GPU_DURATION` 加进来做分段判断。

[已验证: 官方文档, developer.android.com/reference/android/view/FrameMetrics]

#### 方法二:JankStats 库(Jetpack)

Jetpack 的 JankStats 库在 FrameMetrics 的基础上做了增强,它提供了:

1. **自动的 Jank 判定**:默认阈值是帧时间的 2 倍(即 60Hz 下 33.2ms 以上算 Jank)
2. **状态标记**:记录出现 Jank 时的 UI 状态(在哪个页面、执行什么操作),方便定位
3. **报告聚合**:自动汇总 Jank 数据并回调给调用方

```kotlin
// 使用 JankStats 监控
val jankStats = JankStats.createAndTrack(
    window,
    OnFrameListener { frameData ->
        if (frameData.isJank) {
            // 记录 Jank 发生时的状态
            analytics.logEvent("jank_detected", bundleOf(
                "duration_ms" to frameData.frameDurationMs,
                "states" to frameData.states.joinToString()
            ))
        }
    }
)
```

[已验证: 官方文档, developer.android.com/reference/androidx/metrics/performance/JankStats]

#### 方法三:dumpsys gfxinfo

最简单直接的命令行工具,可以快速查看 App 的帧统计:

```bash
adb shell dumpsys gfxinfo <package_name>
```

输出中的关键字段:

```
Total frames rendered: 15234
Janky frames: 423 (2.78%)
50th percentile: 8ms
90th percentile: 14ms
95th percentile: 18ms
99th percentile: 42ms
```

其中 `Janky frames` 的数量和百分比是判断 App 渲染健康度的重要指标。一般经验:Janky frames 比例超过 5% 时用户能明显感知到卡顿。

[已验证: 官方文档, developer.android.com/studio/profile/dumpsys]

#### 方法四:Perfetto Frame Timeline

在 Perfetto 中,Frame Timeline 模块提供了最直观的掉帧可视化。每个 App 会有两条 Track:

1. **Expected Timeline**:每一帧的预期时间窗口,宽度等于 VSync 周期(60Hz = 16.6ms)
2. **Actual Timeline**:每一帧的实际渲染时间

颜色编码的含义:

- **绿色**:正常帧,Actual 在 Expected 内完成
- **红色**:App 侧 Jank,Actual 超出了 Expected,且原因是 App 渲染太慢
- **黄色**:系统侧 Jank,App 本身渲染没问题但 SurfaceFlinger 合成延迟了
- **蓝色**:Dropped Frame,这帧被完全跳过(SurfaceFlinger 用更新的帧替换了它)
- **浅绿色**:高延迟帧,虽然帧率稳定但帧总是"晚到",导致输入延迟增大

[待补充:Perfetto Frame Timeline 的截图,展示不同颜色的帧]

### 掉帧的常见原因

了解如何量化掉帧后,我们来快速看一下在 Perfetto 中遇到掉帧时,可以从哪些方向排查。详细的排查方法论在第 7 章(卡顿分析)中展开。

| 掉帧类型 | Perfetto 特征 | 常见原因 |
|---------|--------------|---------|
| 主线程 Jank | `doFrame` 切片过长,内部某个子阶段突出 | layout 过于复杂、主线程 I/O、频繁 GC |
| RenderThread Jank | `DrawFrame` 切片过长 | GPU 命令过多、复杂 Shader |
| 调度延迟 | `doFrame` 开始时间比 VSync 晚很多 | CPU 被其他进程抢占、线程优先级过低 |
| Input 延迟 | Input 事件到 `doFrame` 之间间隔过长 | Input 事件堆积、InputDispatcher 调度延迟 |
| Buffer 缺乏 | 连续多帧无 `doFrame` | BufferQueue 耗尽、SurfaceFlinger 合成不及时 |

## 扩展:Game Mode / Frame Rate 策略对渲染的影响

前面的内容主要围绕 UI 渲染场景展开。对于游戏这类使用自建渲染循环的应用,Android 提供了额外的系统级控制手段来协调帧率与刷新率。

### Game Mode API(Android 12+)

Android 12 引入了 Game Mode API,允许用户通过系统设置选择游戏的性能模式:

- **PERFORMANCE**:最大化性能,系统会提升 CPU/GPU 频率、使用高刷新率
- **BATTERY**:降低性能以节省电量,系统可能限制刷新率、降低 CPU 频率

App 可以通过 `GameManager` API 查询当前模式并调整自己的渲染策略:

```java
GameManager gameManager = getSystemService(GameManager.class);
int gameMode = gameManager.getGameMode();

switch (gameMode) {
    case GameManager.GAME_MODE_PERFORMANCE:
        // 使用最高画质和高帧率
        break;
    case GameManager.GAME_MODE_BATTERY:
        // 降低画质,锁定 30 FPS
        break;
}
```

### Frame Rate Override(Android 14+)

Android 14 引入了 Frame Rate Override 机制,系统可以直接覆盖 App 请求的帧率。这在以下场景很有用:

- **省电模式**下强制 App 降到 30 FPS
- **热管理**时降帧以降低 SoC 温度
- **Game Mode** 设为省电时限制游戏帧率

App 没有直接的公开 API 获取帧率覆盖通知。以下两种方式可以间接推断:

```java
// 方法一:通过 DisplayManager 监听刷新率变化(间接检测 Frame Rate Override)
// 当系统覆盖了 App 请求的帧率时,通常伴随着显示刷新率的调整
DisplayManager displayManager = getSystemService(DisplayManager.class);
displayManager.registerDisplayListener(new DisplayManager.DisplayListener() {
    @Override
    public void onDisplayChanged(int displayId) {
        Display display = displayManager.getDisplay(displayId);
        float refreshRate = display.getRefreshRate(); // 当前实际刷新率
        // 如果刷新率与通过 setFrameRate() 请求的不一致,
        // 说明可能被系统 Override 了(省电模式、热管理等)
    }
    @Override public void onDisplayAdded(int displayId) {}
    @Override public void onDisplayRemoved(int displayId) {}
}, null);

// 方法二:通过 Choreographer.VsyncCallback (API 33+) 监测实际帧间隔
// 连续帧间隔偏离预期时,可推断帧率被系统调整
Choreographer.getInstance().postVsyncCallback(frameData -> {
    long frameTime = frameData.getFrameTimeNanos();
    // 记录连续帧间隔,如果稳定偏离 setFrameRate() 对应的周期,
    // 则说明帧率可能被系统覆盖
});
```

Android 目前没有提供直接的"帧率被覆盖"回调 API(如 `OnFrameRateOverrideListener`)。上面两种方法都是间接检测:第一种通过显示刷新率变化推断,第二种通过实际帧间隔推断。如果只需要知道当前的显示刷新率,`Display.getRefreshRate()` 是最简单可靠的方式。

> **注意**:`android.view.DisplayEventReceiver.FrameRateOverride` 是系统内部类（`DisplayEventReceiver` 的事件载荷）,不属于公开 SDK。检测帧率覆盖的公开路径仍然依赖 `DisplayManager.DisplayListener` 和 `Choreographer.VsyncCallback` 的间接推断。如果后续 Android 版本开放了公开 API,可以替换为直接检测方式。

[已修正: 明确 FrameRateOverride 非公开 API,公开检测路径仍为间接推断]

[已验证: 官方文档, developer.android.com/games/sdk/game-mode]

## 扩展:LTPO 面板的工作原理与 Android 的适配

### LTPO 的底层技术

LTPO 面板的像素驱动电路中混合使用了两种 TFT 技术:

- **LTPS 晶体管**:电子迁移率高、开关速度快,负责"高速"部分--高刷新率下快速刷新像素
- **IGZO 晶体管**:漏电流极低、功耗极小,负责"保持"部分--低刷新率下保持像素状态

传统 LTPS 面板如果要降到低刷新率(比如 1Hz),由于 LTPS 晶体管的漏电流较大,像素的电荷会在低刷新率的间隔内泄漏,导致显示亮度不均或闪烁。IGZO 晶体管解决了这个问题--它能长时间保持像素电荷,使得 1Hz 的超低刷新率成为可能。

### Android 对 LTPO 的适配

从系统层面看,LTPO 的适配主要在以下几层:

1. **Kernel / DRM 驱动层**:驱动程序需要支持可变刷新率(VRR),将上层设置的刷新率转换为面板驱动信号。

2. **HWC HAL 层**:Hardware Composer HAL 需要声明支持的刷新率列表,并实现无缝切换。

3. **SurfaceFlinger 层**:根据活跃 Layer 的帧率请求,选择最合适的刷新率。对于 LTPO 面板,SurfaceFlinger 的选择范围更大(从 1Hz 到 120Hz),因此需要更精细的决策逻辑。

4. **Android 15 ARR 层**:自适应刷新率(Adaptive Refresh Rate)让刷新率切换更加平滑。ARR 通过"离散步进"(discrete VSync steps)来调整 VSync 周期,而不是做完整的 mode switch,这减少了切换时的视觉中断。

[已验证: AOSP 源码 + 官方文档, 详见底部引用]

### 源码深度:VRR vs ARR 分层 + RefreshRateSelector 评分算法

**VRR(Variable Refresh Rate)≠ ARR(Adaptive Refresh Rate)**,两者是不同层级的概念:

- **VRR**:硬件能力。LTPO 面板能够在 1Hz~120Hz+ 范围内连续变化刷新率,通过面板 TE(Tearing Effect)信号实现帧率与刷新率的动态匹配。VRR 是面板级特性,与 Android 系统无关。
- **ARR**:Android 15 系统级策略。在 VRR 硬件之上,SurfaceFlinger 的 RefreshRateSelector 通过 HWC Composer3 HAL 接口,决策何时以及如何利用 VRR 能力。ARR 在**单一显示模式内**通过离散 VSync 步进来调整刷新率,不触发 DisplayMode 切换(避免 jank)。

**分层关系**:硬件层(LTPO/VRR Panel)→ HWC HAL v3(Composer3 API)→ SurfaceFlinger RefreshRateSelector(ARR 策略决策)→ DisplayManager(Policy 边界)。

**源码位置**:`frameworks/native/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp`

#### RefreshRateSelector 评分算法(比"整除"复杂得多)

LayerVoteType 有 9 种类型(Android 16 `RefreshRateSelector.h` L152-L166),每种对应不同评分策略:

| LayerVoteType | 含义 | 评分策略 |
|---|---|---|
| `NoVote` | 不关心刷新率 | 不参与评分 |
| `Min` | 只要最低刷新率 | 最低刷新率满分 |
| `Max` | 只要最高刷新率 | 与最大刷新率距离的平方 |
| `Heuristic` | 平台内容检测帧率 | 非整除评分(0.95 penalty)|
| `ExplicitDefault` | App 设置 Default | 计算实际渲染帧率(displayPeriod 最小倍数)|
| `ExplicitExactOrMultiple` | App 设置 ExactOrMultiple | 整除=1.0;fractional pair=0.8 |
| `ExplicitExact` | App 设置 Exact | 条件化(见下文) |
| `ExplicitGte` | App 设置"至少 X fps" | 请求帧率及以上的候选均可得高分 |
| `ExplicitCategory` | View/Window 级 category 投票(HighHint / touch boost 路径) | Android 15+ 新增,按 category 优先级映射到高低刷新率档 |

`ExplicitExact` 的评分受 `supportsAppFrameRateOverrideByContent()` 配置影响:
- 不支持 frame-rate override by content 时:只接受 `divisor == 1`(严格整除)
- 支持时:允许 `divisor > 0` 的刷新率得分,系统通过 `FrameRateOverride` 把 App 限到目标帧率

源码锚点:`RefreshRateSelector.cpp` L449-L458,`mFrameRateOverrideConfig`。

> 版本边界:`ExplicitGte` 和 `ExplicitCategory` 是 Android 15/API 35 新增枚举值,Android 11-14 的 `LayerVoteType` 只有前 7 种。

关键评分逻辑(`RefreshRateSelector::calculateLayerScoreLocked()`):
整除 → 满分 1.0;非整除 → 0.95 penalty;fractional pair(如 59.94fps@60Hz)→ 0.8 分。

全局信号优先级(`getRankedFrameRatesLocked()`):
1. `powerOnImminent` → 最高刷新率
2. `touch`(无 Explicit 层)→ 最高刷新率
3. `idle`(主范围非单一刷新率)→ 最低刷新率
4. 正常评分选择

**LayerHistory 内容检测**:`services/surfaceflinger/Scheduler/LayerHistory.cpp`,通过分析 Buffer present timestamps 估算内容帧率。启用条件:`ro.surface_flinger.use_content_detection_for_refresh_rate`

#### VSync 周期动态变化对 Choreographer 的影响

SurfaceFlinger 切换刷新率后,**Choreographer 自动适应**,无需 App 侧干预。已在 Choreographer 中排队的 `FrameCallback` 会**自动按新周期重新调度**(基于绝对时间戳比较),不会丢弃已有订阅。

| API | 引入 | 用途 |
|---|---|---|
| `AChoreographer_registerRefreshRateCallback` | API 30 NDK | 刷新率变化时收到 vsyncPeriodNanos |
| `DisplayManager.DisplayListener.onDisplayChanged()` | API 21 | 刷新率变化通知 |
| `Choreographer.VsyncCallback` | API 33 | 提供 FrameData 含多个候选时间线 |

API 30 NDK callback 可能在回调触发后短时间内返回**过期的刷新率**值;API 31+ 保证一致性。

[已验证: AOSP RefreshRateSelector.cpp + RefreshRateSelector.h 源码 + Android Developer 官方文档]



[已验证: 研究素材, Android-Internal-Wiki/intake/research-feeds/2026-03-30-15-arr-vsync-android15-16.md]

## 扩展:120Hz 场景的功耗权衡与智能降帧策略

### 功耗:高刷新率的代价

屏幕是手机上最大的功耗组件之一,而刷新率直接影响屏幕功耗。简单估算:

- 60Hz → 每秒扫描 60 次
- 120Hz → 每秒扫描 120 次

虽然不是严格线性关系(因为还有像素充放电等功耗),但 120Hz 的屏幕功耗通常比 60Hz 高 20-40%。同时,120Hz 也意味着 CPU/GPU 需要以两倍的频率渲染帧,进一步增加 SoC 功耗。

### 智能降帧策略

为了平衡流畅度和功耗,现代 Android 设备采用了多种智能降帧策略:

**1. 基于内容类型的自动降帧**

SurfaceFlinger 会根据前台 App 的类型自动决定是否使用高刷新率:

- 静态内容(如电子书阅读器、设置页面)→ 降到 60Hz 甚至更低
- 视频播放 → 匹配视频帧率(24/30/60Hz)
- 滑动/动画 → 提升到 120Hz
- 游戏 → 根据 `setFrameRate()` 请求选择

**2. Touch Boost**

当用户触摸屏幕时,SurfaceFlinger 会临时提升刷新率(比如从 60Hz 升到 120Hz),以提供最好的跟手性。触摸停止后一段时间(通常 2-3 秒),如果没有新的触摸事件,刷新率会逐步降回来。

**3. 基于温度的降帧**

当 SoC 温度超过阈值时,Thermal 管理机制会介入,限制最高刷新率。在极端温度下,可能从 120Hz 直接降到 60Hz 甚至更低,以减少发热。

**4. 基于电量的降帧**

在低电量模式(Battery Saver)下,系统会强制限制刷新率为 60Hz,延长续航。

### 对 App 开发者的建议

1. **不要盲目追求 120Hz**:如果 App 的 `doFrame` 耗时在 10-15ms,在 120Hz 下会频繁掉帧。不如稳定运行在 60Hz。
2. **按内容层级声明帧率需求**:视频、Camera 预览、游戏 Surface 用 `Surface.setFrameRate()`;View 树里的局部高刷区域用 `View.setRequestedFrameRate()`;窗口允许续航优先时,再打开 `Window.setFrameRatePowerSavingsBalanced(true)`。
3. **关注帧间隔一致性**:在 120Hz 设备上,即使 FPS 显示 120,如果帧间隔波动大(比如 6ms、8ms、10ms、5ms 交替),用户感知到的流畅度可能还不如稳定的 60Hz。

[已验证: 官方文档, developer.android.com/reference/android/view/Surface#setFrameRate]

## 常见问题与误区

### "高刷新率屏幕 = 更流畅"--不一定

这是一个非常常见的误解。高刷新率屏幕只有在 App 的帧率能跟上时才更流畅,帧率跟不上时反而可能更卡。原因很简单:120Hz 屏幕每 8.3ms 就要刷新一次,如果 App 的帧时间是 12ms(在 60Hz 下完全够用),在 120Hz 下每帧都会超时,导致持续掉帧。用户看到的往往是卡顿更明显了。在 Perfetto 中,这种情况表现为 Frame Timeline 中大量红色帧。

更反直觉的是,有些 App 在 60Hz 设备上流畅但在 120Hz 设备上反而卡顿--不是设备不行,是 App 的渲染能力在 8.3ms 的预算下力不从心。

### "FPS 达到 60 就够了"--忽略了帧间隔

FPS 是一个统计指标,60 FPS 只说明"一秒钟内渲染了 60 帧",但不反映这 60 帧是怎么分布的。如果 59 帧都在前 100ms 内完成,最后一帧拖了 900ms,FPS 仍然是 60,但用户体验是灾难性的。

真正决定流畅度的是帧间隔的一致性。在 Perfetto 中,我们关注的不只是 `Choreographer#doFrame` 的数量,更是它们之间的间距是否均匀。帧间隔从 16ms 突然跳到 33ms 或 50ms,即使平均 FPS 看起来还行,用户也能感知到卡顿。

### "120Hz 设备上所有 App 都更流畅"--需要 App 主动适配

系统默认不会强制所有 App 以 120Hz 渲染。如果 App 没有通过 `setFrameRate()` 告知系统自己的帧率需求,SurfaceFlinger 可能会选择一个保守的刷新率。更关键的是,App 的渲染代码必须能在 8.3ms 内完成一帧--这不是换一台手机就能解决的,需要 App 开发者优化自己的布局、绘制和 GPU 工作量。

### "掉帧 = 主线程卡了"--只说对了一半

主线程确实是掉帧的最常见原因(复杂的 layout、主线程 I/O、频繁 GC 等),但 RenderThread 的 GPU 命令堆积、SurfaceFlinger 合成延迟、CPU 调度不及时(线程被抢占或优先级过低)同样会导致掉帧。在 Perfetto 中区分它们的方法是:主线程 Jank 表现为 `doFrame` 切片内部某个子阶段过长;RenderThread Jank 表现为 `DrawFrame` 切片过长;调度延迟表现为 `doFrame` 开始时间比 VSync 时刻晚很多。

### "setFrameRate() 是命令"--它只是建议

`Surface.setFrameRate()` 告诉 SurfaceFlinger "我希望以这个帧率渲染",但最终刷新率由 SurfaceFlinger 综合所有活跃 Layer 的需求、功耗策略、温度状态和省电模式来决定。如果一个视频播放器设置了 24 FPS,但屏幕上同时有一个 60 FPS 的 UI Layer,SurfaceFlinger 会选择 120Hz(因为 120 同时是 24 和 60 的公倍数),而不是切换到 24Hz。

### "VSync 回调时序在所有设备上都可靠"--OEM 修改可能打破这个假设

原版 AOSP 中,Choreographer 的四类回调(INPUT → ANIMATION → TRAVERSAL → COMMIT)在每个 VSync 周期内严格按序执行一次。但部分 OEM 厂商会修改 VSync 调度逻辑。一个实际案例:华为在某些系统版本中,在一个 VSync 周期内额外注入了伪造的 VSync 信号,只触发 CALLBACK_ANIMATION 类型的回调,导致 Animation 回调的时序与 Input/Traversal 回调脱节。

这类修改会造成三个问题:回调时序与真实 VSync 不对齐、VSync 周期出现长短交替、时间戳偏差。对于依赖 Choreographer 回调做帧调度(如游戏引擎、自定义动画框架)的 App,这些 OEM 定制行为可能导致帧间隔抖动和掉帧。

在 Perfetto 中,这类问题的特征是 `Choreographer#doFrame` 的间隔出现规律性的长短交替(比如 8ms / 24ms / 8ms / 24ms),而不是正常的均匀 16.6ms。

除了华为的额外 VSync 注入，小米 HyperOS 2.0 采取了一种更激进的策略：据社区报道，通过在驱动层注入高频虚拟 VSync 信号，使 Choreographer 在一个物理刷新周期内可以处理多次输入事件，旨在将触控响应延迟压缩到接近物理极限。这种做法打破了“一个 VSync 处理一次输入”的传统假设——在高频注入模式下，Choreographer 的 `CALLBACK_INPUT` 回调在一个物理帧内可能被触发多次。[待验证: HyperOS 高频 VSync 注入机制缺乏官方文档、源码或 Perfetto trace 证据，目前仅有社区报道。如果读者有逆向分析或 Perfetto trace 截图，欢迎补充] 代价是 CPU 唤醒频率显著增加，功耗上升，因此 HyperOS 通常只在游戏、手写笔等对延迟极度敏感的场景下激活。

[待验证: 华为 VSync 修改是否在最新系统版本(HarmonyOS 4+)中已修复]
> OEM 对 VSync 的定制行为在第 17 章(OEM 定制与差异化)中详细讨论。


## 总结

帧率和刷新率是 Android 渲染性能分析中两个最基础、也最容易被混淆的概念。理解它们的区别和协作方式,是解读 Perfetto Trace 的前提:

1. **帧率(FPS)是 App 的指标**:App 每秒能渲染多少帧。它受 App 代码质量、布局复杂度、GPU 性能等因素影响。
2. **刷新率是硬件的指标**:屏幕每秒刷新多少次。现代设备支持多档刷新率,SurfaceFlinger 会根据场景动态选择。
3. **帧间隔一致性决定流畅度**:平均 FPS 高并不够,每一帧之间的间隔还得均匀。
4. **Frame Pacing 保证同步**:Choreographer 和 Frame Pacing Library 确保帧的提交与 VSync 对齐。
5. **掉帧 = 帧时间超过预算**:量化掉帧需要看 Frame Time 分布,而不只是平均 FPS。

在 Perfetto 中分析渲染问题时,记住这个路径:先看 Frame Timeline(Expected vs Actual),找到 Jank 帧 → 看对应 `Choreographer#doFrame` 的子阶段耗时 → 定位是哪个阶段(Input/Animation/Traversal/GPU)导致了超时。具体的分析方法在第 7 章(卡顿分析)中展开。

## 参考资料

1. **官方文档**:
   - [FrameMetrics API](https://developer.android.com/reference/android/view/FrameMetrics)
   - [Surface.setFrameRate()](https://developer.android.com/reference/android/view/Surface#setFrameRate)
   - [View.setRequestedFrameRate()](https://developer.android.com/reference/android/view/View#setRequestedFrameRate(float))
   - [Window.setFrameRatePowerSavingsBalanced()](https://developer.android.com/reference/android/view/Window#setFrameRatePowerSavingsBalanced(boolean))
   - [Android Frame Pacing Library](https://developer.android.com/games/sdk/frame-pacing)
   - [Game Mode API](https://developer.android.com/games/sdk/game-mode)
   - [JankStats 库](https://developer.android.com/reference/androidx/metrics/performance/JankStats)
   - [多刷新率支持](https://source.android.com/docs/core/display/multiple-refresh-rate)
   - [Android 16 ARR](https://developer.android.com/about/versions/16/features)

2. **AOSP 源码**:
   - [Choreographer.java](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/Choreographer.java)
   - [SurfaceFlinger.cpp](https://android.googlesource.com/platform/frameworks/native/+/android-16.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)

3. **相关章节**:
   - [2.1 Android 渲染架构全景](01-rendering-overview.md)
   - [2.3 VSync 机制](03-vsync.md)
   - [2.4 Choreographer 与渲染流水线](04-choreographer.md)
   - [2.6 SurfaceFlinger 与合成](06-surfaceflinger.md)
   - [2.9 渲染机制的版本演进](09-rendering-evolution.md)

4. **研究素材**:
   - [华为手机系统 VSync 调度问题研究](https://zhuanlan.zhihu.com/p/450899407) - OEM VSync 定制行为案例分析

5. **工具文档**:
   - [Perfetto Frame Timeline](https://perfetto.dev/docs/reference/track-events#android)
   - [dumpsys gfxinfo](https://developer.android.com/studio/profile/dumpsys)
