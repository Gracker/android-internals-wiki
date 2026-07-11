---
title: 卡顿的定义与分类
section: '7.1'
chapter: '7.1'
status: "finalized"
drafted_date: '2026-03-30'
drafted_by: openclaw-task2
applicable_versions: Android 4.1 (API 16) - Android 17 (API 37)
last_verified: "2026-07-11"
last_verified_against: "AOSP android-17.0.0_r1 FrameTimeline/JankInfo/VsyncConfiguration + Perfetto android.frames.timeline/android.binder stdlib / Android Developers docs"
polish_count: 3
polish_date: '2026-05-08'
polish_by: task2b-rework
review_type: post-polish-quality-gate
task2b_result: fixed
task2b_state: "fixed"
task6_state: reviewed
task9_state: "reviewed"
pipeline_stage: "ready-to-publish"
confidence: high
sources:
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp
- type: aosp
  path: frameworks/native/libs/gui/include/gui/JankInfo.h
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://developer.android.com/topic/performance/vitals/render
- type: official
  path: https://developer.android.com/topic/performance/vitals/anr
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/metrics/performance/JankStats
- type: official
  path: https://developer.android.com/reference/android/view/FrameMetrics
- type: blog
  path: Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md
- type: blog
  path: Personal-Knowlodge/source/Android-Perfetto-05-Chorergrapher.md
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/VsyncConfiguration.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/sysprop/SurfaceFlingerProperties.sysprop
tags:
- jank
- smoothness
- FrameTimeline
- Choreographer
- 掉帧
- 渲染性能
related_chapters:
- '2.1'
- '2.3'
- '2.4'
- '2.5'
- '7.2'
- '7.3'
- '7.15'
- '8.1'
- '9.1'
task9_result: "pass-tech-review"
last_task2b_at: 2026-05-08T17:58:58+08:00
repaired_date: '2026-04-22'
repaired_by: openclaw-task2b
review_round: 10
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-11"
last_task9_at: "2026-07-11T13:28:01+08:00"
last_task9_audit: "2026-07-11"
last_task9_audit_log: "logs/deep-review/2026-07-11-11-audit.md"
task9_review_notes: "2026-07-11 Task6 re-round2 revisiting-review: pass-light-edit。Task9 12:37 deep-review auto-fix(IPackageManager/WindowManager/Trace.beginSection/freezer语义)回流后写作层复审通过; L1禁用词/高频词/物理动词/元叙述零命中; L2开头/节奏/结构/读者引导全部通过; outline 6/6锚点全覆盖; 否定-纠正结构2处(限额内); 无L1/L2问题无L3/L4回炉项; task9_result=auto-fixed≠pass-tech-review不满足自动晋升; 送Task9终审确认。 | 2026-07-11 Task9 deep-review AUTO-FIX: P0 1 / P1 0 / P2 0；修正 Android 17 VsyncConfiguration 源码锚点：实际调用为 sysprop::vsync_event_phase_offset_ns(1000000) / sysprop::vsync_sf_event_phase_offset_ns(1000000)，不是零参数调用；回到 Task6 复审。详见 logs/deep-review/2026-07-11-12-deep-review.md。 | 2026-07-11 Task6 revisiting-review: pass-light-edit。Task9 idle-audit auto-fix(VSync phase源码锚点修正)回流后写作层复审通过；L1禁用词/高频词/物理动词/元叙述零命中；L2开头/节奏/结构/读者引导全部通过；outline 6/6锚点全覆盖；否定-纠正结构2处(限额内)；无L1/L2问题, 无L3/L4回炉项。送Task9终审确认。 | 2026-07-11 Task9 idle-audit AUTO-FIX: P0 1 / P1 0 / P2 0；修正 VSync phase 源码锚点：Android 17 使用 VsyncConfiguration.cpp 中的 sysprop::vsync_event_phase_offset_ns(1000000) / sysprop::vsync_sf_event_phase_offset_ns(1000000) 与 ro.surface_flinger.* 属性，不再写成不存在的 VSYNC_EVENT_PHASE_OFFSET_NS / SF_VSYNC_EVENT_PHASE_OFFSET_NS；回到 Task6 复审。详见 logs/deep-review/2026-07-11-11-audit.md。 | 2026-05-01 task9 deep-review: needs-rework。P1 2（JankType 版本边界、未验证枚举）/ P2 5 | 2026-05-08 Task9 06:20：needs-rework。P1 1；Binder Trace 新增块将 Binder 阻塞与 AppDeadlineMissed/SF/BufferStuffing 一一映射，缺少 FrameTimeline deadline 与 BufferQueue 因果条件，已写入 queue。 | 2026-05-08 Task9 07:30：needs-rework。P1 1；Binder SQL 仍未用 actual_frame_timeline_slice 的帧窗口、client_upid/client_utid 与 binder_txn_id 约束，会从全局 Binder 事务反推 AppDeadlineMissed 证据，已写入 queue。P2 2 写入 suggestions。 | 2026-05-08 Task9 09:27：needs-rework。P1 1；Binder SQL 已按进程收窄，但仍缺 client_utid / doFrame 或 RenderThread 关键线程约束，且时间条件不是重叠区间，仍可能把同进程后台 Binder 事务误归因到 AppDeadlineMissed，已写入 queue。 | 2026-05-08 Task9 14:32：needs-rework。P0 1 / P1 1 / P2 0；Perfetto FrameTimeline `jank_type` 等值与 UI 线程定位仍需回炉。 | 2026-05-08 Task9 17:38：needs-rework。P0 1 / P1 0 / P2 0；7.1 Binder SQL 使用不存在的 android_frames.utid 列且未 include android.frames.timeline，示例无法执行，需回炉修正。 | 2026-05-08 Task9 18:39：pass-tech-review。P0/P1/P2 0；前轮 Binder SQL P0 已按 Perfetto android.frames.timeline / android.binder 源码复核通过，自动晋升 finalized。 | 2026-06-20 Task9 闲时抽检：auto-fixed。Android 17/API 37 公开 tag 已可核验；FrameTimeline.cpp 在 Android 17 移至 Scheduler/FrameTimeline.cpp，JankInfo.h 新增 NonAnimating/AppResyncedJitter/DisplayNotOn/DisplayModeChangeInProgress/DisplayPowerModeChangeInProgress；已修正源码锚点、版本边界和旧待验证枚举口径，回到 Task6 复审。 | 2026-06-21 Task9 00:25：pass-tech-review。P0/P1/P2 0；复核 Android 17 FrameTimeline/JankInfo、Perfetto android.frames.timeline/android.binder SQL 列、Android vitals/JankStats 官方口径；queue 无 pending，基于 task6_result=pass-light-edit 自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-07-11-13-deep-review.md"
reviewed_date: "2026-07-11"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task6_reviewed_date: "2026-07-11"
last_task6_at: "2026-07-11T13:06:00+08:00"
last_task6_review_log: "logs/review/2026-07-11-13-review.md"
last_task6_audit: "2026-07-04"
review_notes: "2026-07-11 Task9 deep-review AUTO-FIX: P0 1 / P1 0 / P2 0；修正 Android 17 VsyncConfiguration 源码锚点：实际调用为 sysprop::vsync_event_phase_offset_ns(1000000) / sysprop::vsync_sf_event_phase_offset_ns(1000000)，不是零参数调用；回到 Task6 复审。详见 logs/deep-review/2026-07-11-12-deep-review.md。 | 2026-07-11 Task6 revisiting-review: pass-light-edit。Task9 idle-audit auto-fix(VSync phase源码锚点修正)回流后写作层复审通过；L1禁用词/高频词/物理动词/元叙述零命中；L2开头/节奏/结构/读者引导全部通过；outline 6/6锚点全覆盖；否定-纠正结构2处(限额内)；无L1/L2问题, 无L3/L4回炉项。送Task9终审确认。 | 2026-07-11 Task9 idle-audit AUTO-FIX: P0 1 / P1 0 / P2 0；修正 VSync phase 源码锚点：Android 17 使用 VsyncConfiguration.cpp 中的 sysprop::vsync_event_phase_offset_ns(1000000) / sysprop::vsync_sf_event_phase_offset_ns(1000000) 与 ro.surface_flinger.* 属性，不再写成不存在的 VSYNC_EVENT_PHASE_OFFSET_NS / SF_VSYNC_EVENT_PHASE_OFFSET_NS；回到 Task6 复审。详见 logs/deep-review/2026-07-11-11-audit.md。 | 2026-05-08 Task6 06:05：发现 AIW Binder Trace 新增块位于参考资料后且未融入主线，已标注并写入 Task2B queue；同步完成 L1/L2 标点格式小修。 | 2026-05-08 Task9 06:20：needs-rework。P1 1；Binder Trace 新增块将 Binder 阻塞与 AppDeadlineMissed/SF/BufferStuffing 一一映射，缺少 FrameTimeline deadline 与 BufferQueue 因果条件，已写入 queue。 | 2026-05-08 Task6 07:24：Task2B 已将 Binder 段改为 FrameTimeline deadline 因果链，本轮将该段移入 FrameTimeline 主体并完成 L1/L2 小修；文稿通过，等待 Task9 技术复审。 | 2026-05-08 Task9 07:30：needs-rework。P1 1；Binder SQL 仍未用 actual_frame_timeline_slice 的帧窗口、client_upid/client_utid 与 binder_txn_id 约束，会从全局 Binder 事务反推 AppDeadlineMissed 证据，已写入 queue。P2 2 写入 suggestions。 | 2026-05-08 Task6 09:07：复审 Task2B 修复后的 Binder SQL 段与全文 L1/L2；压掉少量第一人称和填充式标题，文稿通过，等待 Task9 技术复审。 | 2026-05-08 Task9 09:27：needs-rework。P1 1；Binder SQL 已按进程收窄，但仍缺 client_utid / doFrame 或 RenderThread 关键线程约束，且时间条件不是重叠区间，仍可能把同进程后台 Binder 事务误归因到 AppDeadlineMissed，已写入 queue。 | 2026-05-08 Task6 14:05：复审 Task2B 修复后的文稿，完成 frontmatter 去重、代码围栏语言标注与 L1/L2 小修；无新增 B 类回炉问题，等待 Task9 技术复审。 | 2026-05-08 task6 revisit: pass-light-edit。清理重复 frontmatter 并复审 Task2B 修复后的 Binder SQL 段；未发现新增 L1/L2 文风问题；无新增 B 类回炉项；转入 Task9 复审。 | 2026-05-08 Task9 17:38：needs-rework。P0 1 / P1 0 / P2 0；7.1 Binder SQL 使用不存在的 android_frames.utid 列且未 include android.frames.timeline，示例无法执行，需回炉修正。 | 2026-05-08 Task6 18:20：复审 Task2B P0 修复后的文稿，完成代码围栏语言标注与第一/二人称痕迹小修；无新增 B 类回炉项；转入 Task9 复审。 | 2026-06-20 Task9 闲时抽检：auto-fixed。Android 17/API 37 公开 tag 已可核验；FrameTimeline.cpp 在 Android 17 移至 Scheduler/FrameTimeline.cpp，JankInfo.h 新增 NonAnimating/AppResyncedJitter/DisplayNotOn/DisplayModeChangeInProgress/DisplayPowerModeChangeInProgress；已修正源码锚点、版本边界和旧待验证枚举口径，回到 Task6 复审。 | 2026-06-21 Task9 00:25：pass-tech-review。P0/P1/P2 0；复核 Android 17 FrameTimeline/JankInfo、Perfetto android.frames.timeline/android.binder SQL 列、Android vitals/JankStats 官方口径；queue 无 pending，基于 task6_result=pass-light-edit 自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-21
last_task9_autofix_at: "2026-07-11"
last_task9_audit_at: "2026-07-11T11:28:55+08:00"
last_task9_audit_result: "auto-fixed"
task9_audit_notes: "2026-07-11 Task9 闲时抽检 AUTO-FIX：Android 17 VSync phase 源码锚点已从不存在的 uppercase 标识修正为 VsyncConfiguration sysprop 与 ro.surface_flinger.* 属性；FrameTimeline/JankInfo/Perfetto SQL 口径未发现新增 P0/P1；回到 Task6 复审。"
task9_reviewed_at: "2026-07-11T11:28:55+08:00"
last_task9_audit_notes: "idle audit AUTO-FIX: Android 17 VSync phase 源码锚点已从不存在的 uppercase 标识修正为 VsyncConfiguration sysprop 与 ro.surface_flinger.* 属性；FrameTimeline/JankInfo/Perfetto SQL 口径未发现新增 P0/P1。"
p0: 0
p1: 0
p2: 0
updated_by: openclaw-task9
updated_date: "2026-07-11"
last_task2b_verifier_at: "2026-07-11T11:34:06+08:00"
task2b_verifier_notes: "Task9 idle-audit auto-fix on 2026-07-11 set task6_state: revisiting + pipeline_stage: task6_pending, but status remained finalized. Corrected to ready-for-review for Task6 re-review."
last_task9_review_notes: "2026-07-11 Task9 deep-review: pass-tech-review。P0/P1/P2 0；复核 Android 17 FrameTimeline/JankInfo、VsyncConfiguration phase、Perfetto android.frames.timeline/android.binder SQL 口径，Task6 已通过且 queue 无 pending，自动晋升 finalized。详见 logs/deep-review/2026-07-11-13-deep-review.md。"
---
# 卡顿的定义与分类

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 广义流畅性：卡顿、响应慢、ANR 是同一条体验链上的不同失效形式
- 🔹 Jank 的标准定义：帧未在预期 VSync 周期内完成（60Hz=16.67ms / 90Hz=11.11ms / 120Hz=8.33ms）
- 🔹 Google 的 Jank 分类：App Jank vs SF Jank vs Display Jank
- 🔹 FrameTimeline 与 JankType 的对应关系（Android 12+）
- 🔹 掉帧率（Janky Frame Rate）、连续掉帧（Frozen Frame）的区别
- 🔹 用户感知与技术指标的映射：多少 ms 延迟人能感知到

### 扩展（可选深入）

- 🔸 各厂商对 Jank 定义的差异（如华为的标准 vs Google 的标准）
- 🔸 Perfetto FrameTimeline 中 Jank 类型的详细解读

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要先把"卡"说清楚

很多性能问题，一开始就输在定义上。

用户说"这页面有点卡"，开发说"我这里能跑到 60fps"，测试说"偶发掉帧"，平台说"这个版本 jank rate 没超阈值"。四个人都在说卡，但说的不是同一件事。如果这一层不先统一口径，后面再看 trace、看指标、定责任方，结论很容易各说各话。

本节把"卡"拆开，讲清楚哪些属于渲染问题，哪些属于响应问题，哪些已经进入 ANR。只有定义清楚，后面的分析路径才会稳定。

## 先把"广义流畅性"和"狭义 jank"分开

工程里最实用的做法，是先承认一件事：用户并不会区分掉帧、响应慢和 ANR。对用户来说，它们都属于"我操作了，但系统没有及时给反馈"。

所以从体验治理角度，可以先建立一个**广义流畅性**的概念：它包含了狭义的渲染卡顿，也包含了响应速度问题和 ANR。

但进入技术分析后，三者又必须拆开：

- **狭义 jank / 掉帧**：帧没有按预期 VSync 节奏完成。
- **响应慢**：输入到可见反馈、启动到可交互之间的时间过长。
- **ANR**：主线程或关键线程长时间没有对系统要求做出响应，超过了系统 watchdog 的阈值。

这层统一视角的价值，不在概念本身，而在排障顺序。先把问题归到哪一类失效，再决定去看 `FrameTimeline`、启动过程还是 ANR 栈，效率会高很多。后面的 `7.15` 会把这套入口继续落成更具体的现场手册。

## Jank 的标准定义：帧没有按时到达

Android 系统的渲染管线是围绕 VSync 信号构建的。在 60Hz 屏幕上，VSync 信号每 16.67ms 到来一次；在 120Hz 屏幕上，这个间隔缩短到 8.33ms。每一个 VSync 周期，系统预期 App 能渲染出一帧新内容、SurfaceFlinger 能完成合成、最终屏幕能显示这一帧。

**Jank 的标准定义是：某一帧没有在预期的 VSync 周期内完成渲染和上屏。**

这里的"预期"指调度器给这一帧分配的呈现时间。系统不是简单地看"这一帧渲染花了多长时间"，而是看"这一帧实际被呈现（present）的时间，是否与调度器（Scheduler）预测的呈现时间一致"。如果实际呈现时间晚于预期，那就是 Jank。

VSync 是渲染管线的基本时钟，每一帧必须在分配给自己的 VSync 周期内完成渲染和上屏。按时完成，画面连贯；错过了当前周期，这一帧只能等到下一个 VSync 才能上屏，中间的空档就是用户感知到的"不连贯"。

### 不同刷新率下的帧预算

| 刷新率 | 单个刷新周期 |
|--------|--------------|
| 60Hz | 16.67ms |
| 90Hz | 11.11ms |
| 120Hz | 8.33ms |

这个周期表示相邻两次硬件刷新之间的间隔，不等于"MainThread、RenderThread、SurfaceFlinger 的全部工作都要串行塞进同一个窗口"。Android 的显示栈是流水线化的。App 侧围绕 VSync-app 准备下一帧，SurfaceFlinger 围绕随后到来的 VSync-sf 做合成，两边靠 offset 错峰推进。这里的 offset 对应两套 VSync phase：Android 17 源码中，App 侧配置来自 `sysprop::vsync_event_phase_offset_ns(1000000)`（`ro.surface_flinger.vsync_event_phase_offset_ns`），SurfaceFlinger 侧配置来自 `sysprop::vsync_sf_event_phase_offset_ns(1000000)`（`ro.surface_flinger.vsync_sf_event_phase_offset_ns`）。系统会在硬件 VSync 到来前按这两个 phase 分别唤醒 App 和 SurfaceFlinger，渲染与合成因此能够错开推进。

到了 120Hz，变紧的是每个阶段各自的 deadline。App 侧如果晚于自己的 expected timeline，FrameTimeline 会记成 App jank；SurfaceFlinger 或显示末端晚了，则会落到 SurfaceFlinger 或 DisplayHAL 一侧。分析高刷 trace 时，先分清"谁错过了谁的 deadline"，再去看具体线程，不要把整条流程粗暴压成一个 8.33ms 总包预算。

[已验证: Perfetto 文档, https://perfetto.dev/docs/data-sources/frametimeline]
[已验证: 官方文档, https://developer.android.com/topic/performance/vitals/render]

### FPS 不等于流畅度

工程排查里常先看 FPS，但 FPS 最容易把人带偏。它只回答"一秒里总共画了多少帧"，不回答"这些帧是不是均匀到达"。

举个极端的例子：一秒内渲染了 50 帧。如果这 50 帧是均匀分布的（每 20ms 一帧），用户看到的是稳定的 50fps 体验，虽然不是最流畅，但不会觉得"卡"。但如果前 200ms 只渲染了 1 帧，后 800ms 突然渲染了 49 帧，FPS 同样是 50，但用户会感受到明显的卡顿——因为那 200ms 的空白期打破了视觉惯性。

腾讯音乐技术团队在分析里特别强调过这一点：**帧率不能直接代表是否卡顿**。Google 之所以把重点放在"每一帧是否按时到达"，而不是"平均帧率是多少"，原因就在这里。用户感知到的，是节奏稳定不稳定，而不是统计意义上的总产量。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md]

## Google 的 Jank 分类体系

Android 12 之后，FrameTimeline 会给每一帧写下责任归因。Perfetto 里先看 `Jank Type`，再决定回链到 App、SurfaceFlinger 还是显示末端。把这些类型拆开，排查路径才不会跑偏。

[已验证: Perfetto 文档, https://perfetto.dev/docs/data-sources/frametimeline]

### AppDeadlineMissed

`AppDeadlineMissed` 表示 App 一侧没有按时交帧。Perfetto 文档把 App frame 的时间范围定义为：起点是 `Choreographer` 回调计划运行后的 App 开工时刻，终点落在 App 实际 `queueBuffer` 的时间与 fence signal time 中较晚的那个时间点。AOSP `FrameTimeline.cpp` 里的 `SurfaceFrame::setActualQueueTime()` 与 `setAcquireFenceTime()` 分别写入这两个时间点；对 GPU 渲染来说，后者通常落在 GPU 完成之后。`queueBuffer` 对应 App 把 buffer 交给 BufferQueue，所以这类 jank 既可能来自 MainThread，也可能来自 RenderThread 或 GPU 工作未及时结束。

[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp；AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp]

Trace 里先点 App 的 `Actual Timeline` slice，再顺 token 回到 `Choreographer#doFrame` 和 `RenderThread`。如果 `On time finish` 为 `false`，而 `Jank Type` 是 `AppDeadlineMissed`，说明问题就在 App 自己这一段。

### SurfaceFlingerCpuDeadlineMissed

`SurfaceFlingerCpuDeadlineMissed` 表示 SurfaceFlinger 主线程的 CPU 工作超了自己的 deadline。device composition 走硬件合成时，主线程会把合成相关工作算在这段 CPU time 里；如果主线程本身就没收住，这类 jank 会直接落到 CPU deadline miss。

排查入口在 SurfaceFlinger 侧的 `Actual Timeline` 与 `onMessageReceived`，而不是 App `doFrame`。App 侧通常只会显示"这帧 janky，但责任不在 App"。

### SurfaceFlingerGpuDeadlineMissed

`SurfaceFlingerGpuDeadlineMissed` 说明 SurfaceFlinger 主线程本身还在 deadline 内，但 GPU composition 没有按时准备好，frame 被推迟到下一个 vsync。它和 CPU miss 的分界点，正好在 Perfetto details 面板里的 `GPU Composition`、`On time finish` 以及 SurfaceFlinger 侧 token 回链上。

遇到黄色 frame 时，如果只盯着 MainThread，很容易把 GPU 合成拖慢误判成 App jank。这里要回到 SurfaceFlinger 轨道看 GPU/client composition 这一段。

### DisplayHAL

`DisplayHAL` 表示 SurfaceFlinger 已经按时把 frame 往下交了，但 frame 没按预测的那个 vsync 显示出来。Perfetto 文档写得很明确，这类问题有两种常见解释：一种是 HAL / 显示末端自己慢，另一种是 SurfaceFlinger 留给 HAL 的时间不够。两种情况都要看证据，不能直接写成"厂商 HAL 慢"。

排查时先看 details 面板里的 `Present Type`、`On time finish`、`GPU Composition`。如果 App 和 SurfaceFlinger 都按时完成，frame 还是 late，才有理由继续怀疑 Display HAL / display pipeline 末端。

### PredictionError

`PredictionError` 不是 App 或 SurfaceFlinger "干慢了"，而是 scheduler 对 hardware vsync 的预测漂移了。Perfetto 文档里的例子是：系统预计 20ms present，实际硬件 vsync 到了 23ms，预测自己偏了 3ms。scheduler 会周期性修正，所以这类 jank 往往成片出现后又自己收敛。

碰到 `PredictionError`，先看 `Present Type` 和 `Valid Prediction`，判断是不是调度预测漂移，不要直接把责任记到 App 线程上。

### BufferStuffing

Perfetto 文档把 `BufferStuffing` 描述为一种状态，而不是独立的 jank 类型。它指的是 App 在上一帧还没 present 时，又继续往 SurfaceFlinger 塞新 buffer，队列里堆了多帧待显示内容。结果是画面还能持续刷新，但输入反馈越来越晚，严重时 App 还会卡在 dequeue 等待 buffer 归还。

这类问题先看 FrameTimeline 的 `Jank Type` 和高延迟状态（`High latency state`），再用 BufferQueue 轨道、dequeue blocking、SurfaceFlinger 侧 flow event 做佐证。不要把 `queued > 1` 这类经验信号写成唯一判据。

### 其他 JankType：Android 12 已定义与后续版本补充

上面六种是 FrameTimeline 中最常遇到的归因类型。AOSP `JankInfo.h` 里还定义了另外几个 JankType，遇到的时候不至于在 details 面板里找不到对应解释。

下表列出 Android 12（android-12.0.0_r1）的 `JankInfo.h` 中除前面六种之外已定义的枚举：

| JankType | 值 | 触发条件 | 排查入口 |
|----------|------|----------|----------|
| `SurfaceFlingerScheduling` | 0x20 | SurfaceFlinger 唤醒/调度时机偏差导致 present early/late | 检查 SF 唤醒时序、VsyncModulator 配置、HWC vsync 偏移 |
| `Unknown` | 0x80 | 归因条件无法匹配任何已知类型 | 通常伴随其他 JankType 出现，需结合 FrameTimeline details 面板综合判断 |
| `SurfaceFlingerStuffing` | 0x100 | 上一帧占用了当前 expected vsync 的窗口，把当前帧推向下一个 vsync | 检查 BufferQueue 堆积、前一帧 GPU composition 是否超时 |

[已验证: AOSP android-12.0.0_r1 ~ android-16.0.0_r1, frameworks/native/libs/gui/include/gui/JankInfo.h]

`Dropped`（值 0x200）在 Android 14 QPR 及后续 tag 的 JankInfo.h 中出现，Android 12/13 的公开 tag 中不一定暴露。分析 Android 14 以下设备时，看到 `Dropped Frame` 归因以 Perfetto details 面板实际输出为准。

Android 17（`android-17.0.0_r1`）的 `JankInfo.h` 在 `Dropped` 之后继续新增五类状态：

| JankType | 值 | 触发条件 | 排查入口 |
|----------|------|----------|----------|
| `NonAnimating` | 0x400 | frame 没有按时 present，但不属于动画内容，通常不构成可感知 jank | 先确认 layer 是否处在动画或跟手交互路径 |
| `AppResyncedJitter` | 0x800 | App 修改了该帧的 vsync time | 检查 App 侧 vsync resync、FrameTimeline token 与调度时间 |
| `DisplayNotOn` | 0x1000 | 屏幕关闭或处于 doze 状态 | 结合 Display state / PowerManager 状态过滤 |
| `DisplayModeChangeInProgress` | 0x2000 | 显示模式切换过程中产生的 late frame | 检查刷新率 / 分辨率切换窗口 |
| `DisplayPowerModeChangeInProgress` | 0x4000 | 显示电源模式切换过程中产生的 late frame | 检查 power mode 切换和亮灭屏时序 |

Android 16 及更早公开 tag 未定义这五项。历史材料中如果列出与上表不一致的枚举值，以 `android-17.0.0_r1` 的 `JankInfo.h` 为准。

[已验证: AOSP android-17.0.0_r1, frameworks/native/libs/gui/include/gui/JankInfo.h]

### Dropped Frame

`Dropped Frame` 表示这一帧被直接跳过了。Perfetto 文档区分了两种场景：

- 对 SurfaceFlinger 来说，是跳过当前 frame，优先显示更新的 frame。
- 对 App 来说，是 UI 线程的状态更新没来得及推到 RenderThread，RenderThread 用旧状态把这一帧画完了。

用户看到的结果都是"内容跳了一下"，但根因路径不同。

### FrameTimeline 里的颜色和枚举怎么看

Perfetto 的颜色是 UI 层面的归因提示，不是 `JankType` 到颜色的一一映射。精确类型要看 details 面板里的 `Jank Type`。

| Perfetto 颜色 | 常见归因 | 读法 | 第一观察点 |
|---------------|----------|------|------------|
| 绿色 | `None` | 正常 frame | 无需回溯 |
| 浅绿色 | 高延迟状态（`High latency state`），常见于 `BufferStuffing` 一类状态 | 画面节奏还算平，但输入延迟在涨 | `Present Type`、`Jank Type`、BufferQueue / dequeue 佐证 |
| 红色 | `AppDeadlineMissed` | App 自己没按时交帧 | `Actual Timeline` → `doFrame` / `RenderThread` |
| 黄色 | `SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed`、`DisplayHAL`、`PredictionError` 等 App 非责任侧问题 | App 看到了 jank，但责任不在 App | SurfaceFlinger `Actual Timeline`、`onMessageReceived`、details 面板 |
| 蓝色 | `Dropped Frame` | 这一帧被跳过 | App / SurfaceFlinger 两侧都要看 |

## FrameTimeline：Android 12+ 的 Jank 追踪核心

### Expected Timeline vs Actual Timeline

Perfetto 给每个出现在屏幕上的应用加两条 track。

- `Expected Timeline` 表示系统给这帧分配的时间窗口。它的起点是 `Choreographer` 回调计划开始执行的时刻。
- `Actual Timeline` 表示 App 实际花掉的时间。它从 `Choreographer#doFrame` 或 `AChoreographer_vsyncCallback` 开始，结束点取 `max(actualQueueBufferTime, actualGpuCompletionTime)`：前者对应 App 调用 `queueBuffer` 把 Buffer 交给 BufferQueue 的时刻，后者对应 GPU 完成这帧内容的 fence signal 时刻。

两条线贴得住，说明 App 这一段按时完成。`Actual Timeline` 晚于 `Expected Timeline`，再结合 `Jank Type` 才能知道迟到是 App、SurfaceFlinger 还是显示末端造成的。

### Token 怎么把一帧串起来

FrameTimeline 会给每一帧分配一个 token。这个 token 会同时出现在 App 的 `doFrame` / `RenderThread` slice 和 SurfaceFlinger 的 `onMessageReceived` slice 上。点中 App 的 `Actual Timeline` slice 时，Perfetto 还会画 flow event，把这一帧连到对应的 SurfaceFlinger timeline slice；点中 DisplayFrame，还能看到多个 layer frame 是怎么合到同一帧屏幕上的。

排查顺序最好是这样：

1. 在 `Actual Timeline` 选中 janky frame。
2. 看 details 面板里的 `Jank Type`、`Present Type`、`On time finish`、`GPU Composition`、`Layer Name`。
3. 沿 token 回到 App 的 `doFrame` / `RenderThread`，或 SurfaceFlinger 的 `onMessageReceived`。
4. 再决定继续看 MainThread、RenderThread、SurfaceFlinger CPU、GPU composition，还是 display 末端。

`Choreographer#doFrame` 和 `RenderThread` 很有用，但它们是回溯锚点，不是 FrameTimeline 主视图的替代品。主视图还是 `Expected Timeline` / `Actual Timeline`。

### Android 12 之前怎么看

Android 12 之前没有 FrameTimeline。那时只能靠 `Choreographer#doFrame`、`DrawFrame`、SurfaceFlinger 轨道和 VSync 时序关系手动判断是否超时。能抓到 FrameTimeline 的设备，优先用 FrameTimeline；老设备再回退到传统方法。

[已验证: Perfetto 文档, https://perfetto.dev/docs/data-sources/frametimeline]

### Binder 阻塞如何佐证 AppDeadlineMissed

在实战中，`AppDeadlineMissed` 的一类常见根因是 Binder 阻塞——主线程或 RenderThread 在帧周期内调了 Binder，被远端卡住了。但要记住，Binder 阻塞本身不等于某一类 JankType，需要回到 FrameTimeline 的 deadline 体系里做因果连接。

#### Binder 阻塞定位为帧关键路径证据

排查 AppDeadlineMissed 时，如果 `Actual Timeline` 超出 `Expected Timeline`，沿 token 回到 App 线程后，常见的一条证据链是：

1. FrameTimeline 标记 `AppDeadlineMissed`，`On time finish = false`。
2. App 主线程或 RenderThread 在该帧的 `doFrame` / `DrawFrame` 区间内出现 `binder transaction` slice。
3. 同一时段 `thread_state: Sleeping`，`blocked_function: binder_thread_read`。

此时 Binder 阻塞是 AppDeadlineMissed 的直接原因——App 线程在帧周期内花时间等 Binder 返回，导致 `queueBuffer` 超出 deadline。

#### 不要把 Binder 直接映射到 SF 或 BufferStuffing

Binder 阻塞出现在 SurfaceFlinger 线程上时，需要额外证据才能指向 `SurfaceFlingerCpuDeadlineMissed`：SF 主线程在 `onMessageReceived` 里等 Binder 返回，导致合成超时。仅凭"服务端处理慢"不能跳过 FrameTimeline 的 SF deadline 判定。

`BufferStuffing` 的因果条件是 BufferQueue 堆积。Binder 调用频率高可能间接导致堆积，但 BufferStuffing 的判定依据是 FrameTimeline 的 `Jank Type` + `Present Type` + BufferQueue 轨道的 dequeued/queued 计数，不是 Binder 调用次数。

#### Perfetto SQL 佐证

确认 FrameTimeline 归因后，用帧窗口约束的 Binder SQL 定位具体调用。直接查 `android_binder_txns` 全局排序会抓到无关事务——必须先锁定 janky frame 的时间范围和线程：

```sql
-- Step 1: 锁定 AppDeadlineMissed 的 janky frame，并定位该帧对应的关键线程
INCLUDE PERFETTO MODULE android.frames.timeline;
INCLUDE PERFETTO MODULE android.binder;
INCLUDE PERFETTO MODULE android.binder_breakdown;

WITH janky_frame AS (
  SELECT af.ts, af.dur, af.upid,
         f.ui_thread_utid AS ui_utid,
         f.render_thread_utid AS rt_utid
  FROM actual_frame_timeline_slice af
  JOIN android_frames f ON af.id = f.actual_frame_timeline_id
  WHERE af.jank_type GLOB '*App Deadline Missed*'
    AND af.on_time_finish = 0
  ORDER BY af.dur DESC
  LIMIT 1
),
-- Step 2: 找与该帧时间窗口重叠的 Binder 事务
-- 关键约束：只看 UI/RenderThread 的事务，且用区间重叠而非起点包含
frame_binder AS (
  SELECT b.client_process, b.server_process,
         b.client_dur/1e6 AS client_ms,
         b.server_dur/1e6 AS server_ms,
         b.aidl_name, b.is_main_thread, b.binder_txn_id
  FROM android_binder_txns b, janky_frame jf
  WHERE b.client_upid = jf.upid
    AND (b.client_utid = jf.ui_utid OR b.client_utid = jf.rt_utid
         OR b.is_main_thread = 1)  -- 回退：is_main_thread 标记兜底
    AND b.client_ts < jf.ts + jf.dur        -- 事务起点早于帧结束
    AND b.client_ts + b.client_dur > jf.ts  -- 事务结束晚于帧起点（区间重叠）
    AND b.client_dur > 1000000  -- > 1ms
  ORDER BY b.client_dur DESC
)
SELECT * FROM frame_binder;
```

拿到 `binder_txn_id` 后，在同一 WITH 查询块中用 `android_binder_client_breakdown` 按 reason 拆分延迟来源：

```sql
-- 接续上面的 CTE 链，把 frame_binder 作为子查询使用
SELECT reason, count(*) AS count, sum(dur)/1e6 AS total_ms
FROM android_binder_client_breakdown
WHERE binder_txn_id IN (
  SELECT b.binder_txn_id
  FROM android_binder_txns b,
       (SELECT af.ts, af.dur, af.upid,
               f.ui_thread_utid AS ui_utid,
               f.render_thread_utid AS rt_utid
        FROM actual_frame_timeline_slice af
        JOIN android_frames f ON af.id = f.actual_frame_timeline_id
        WHERE af.jank_type GLOB '*App Deadline Missed*' AND af.on_time_finish = 0
        ORDER BY af.dur DESC LIMIT 1) jf
  WHERE b.client_upid = jf.upid
    AND (b.client_utid = jf.ui_utid OR b.client_utid = jf.rt_utid
         OR b.is_main_thread = 1)
    AND b.client_ts < jf.ts + jf.dur
    AND b.client_ts + b.client_dur > jf.ts
    AND b.client_dur > 1000000
)
GROUP BY reason
ORDER BY total_ms DESC;
```

排查顺序：**先看 FrameTimeline 归因 → 确认哪条线程在帧周期内阻塞 → 再用 Binder SQL 定位具体调用**。不要跳过 FrameTimeline 直接从 Binder 调用反推 JankType。

## 掉帧率、连续掉帧与卡顿率

逐帧归因回答的是"这一帧为什么晚了"；项目交付还要回答"整体体验差到什么程度"。这时会用到慢帧、Frozen Frame、Janky Frame Rate 一类聚合指标。

### 慢帧、Frozen Frame、ANR 不是同一套类型

Android vitals 把 slow frames、frozen frames 和 ANRs 放在一张对照表里，便于理解用户感知，但它们不是 FrameTimeline 的同一条 severity ladder。前两者是渲染问题，ANR 是响应性问题。

| 类型 | 典型时间范围 | 主要现象 | 归属 |
|------|--------------|----------|------|
| Slow Frame | 16ms - 700ms | 滑动、动画不顺 | 渲染问题 |
| Frozen Frame | 700ms - 5s | 画面像停住了一样 | 渲染问题 |
| ANR | > 5s | 系统弹出无响应对话框，或输入 / 广播 / 服务超时 | 响应性问题 |

Android vitals 对 Frozen Frame 的要求更硬，文档直接写了：应用里不应该出现任何一帧超过 700ms。

### Janky Frame Rate 怎么设目标

`Janky Frame Rate = janky frames / total frames` 这个公式没问题，但目标值不能写成一个跨场景通用数字。连续滑动、页面切换、冷启动首帧、120Hz 高刷列表，它们的刷新率、统计窗口和用户容忍度都不同。Android vitals 也没有给"所有 App 都用 5%"这一类统一门槛。

更稳的做法是按场景建目标：

- 持续滑动和跟手交互，优先压慢帧比例和高延迟状态（`High latency state`）。
- 页面切换、冷启动首帧，单独看过渡阶段，不把初始化的特例混进常态滚动指标。
- 高刷设备按 90Hz / 120Hz 的 frame period 单独统计，不拿 60Hz 标准混算。

### Stutter、方差和工具私有指标

很多工具还会给 `stutter`、帧时间方差、连续掉帧段落等聚合指标。这些指标对横向对比版本回归很有用，但公式和阈值常常是工具私有实现。只要工具版本、统计窗口或刷新率设定一变，数字就会跟着变。

所以在工程实践里，FrameTimeline / Android vitals 负责给系统级归因口径；PerfDog、内部脚本、自动化平台负责给团队自己的回归阈值。两类数字可以并用，不要直接混写成同一级"标准定义"。

[已验证: 官方文档, https://developer.android.com/topic/performance/vitals/render]

## 用户感知与技术指标的映射

技术指标还要接回用户感受：这些数字对应的体验是什么？用户不会看 Perfetto Trace，只会说"这个列表滑起来不顺手"或"这个动画一卡一卡的"。

### 视觉惯性与帧率稳定性

用户对流畅度的感知不仅取决于帧率的高低，更取决于帧率的**稳定性**。这涉及到一个概念叫"视觉惯性"——当用户持续看到 60fps 的画面时，潜意识里预期下一帧也是同样的节奏。如果突然有一帧延迟了，打破了这种惯性，用户就会感知到"卡了一下"。

这就是为什么稳定的 40fps 可能比在 60fps 和 30fps 之间来回跳变的体验更好——稳定低帧率让用户建立了新的视觉惯性，而不稳定的帧率不断打破惯性。

电影帧率（24fps，约每帧 41.67ms）是一个参考下限。低于这个帧率，人眼基本能感知到画面的不连续性。但电影有自然运动模糊来"掩盖"低帧率，而 UI 动画没有这种效果，所以 UI 对帧率的要求更高。

### 延迟感知的阈值

研究表明，用户对延迟的感知有几个常用阈值：

- **< 100ms**：用户感觉系统是"即时响应"的。Jakob Nielsen 的研究表明，100ms 是用户感觉"系统在直接响应我的操作"的极限。在这个范围内，用户认为操作和结果是直接关联的。
- **100ms - 300ms**：用户能感知到延迟，但仍然觉得在"可接受"范围内。此时用户能感觉到操作和结果之间有轻微的间隔。
- **300ms - 1s**：用户明显感到等待，注意力开始分散。
- **> 1s**：用户的思维连续性被打断，开始觉得系统"慢"。
- **> 5s**：用户失去耐心，系统弹出 ANR 对话框。

对于 Android 的 UI 渲染来说，一个 VSync 周期（60Hz 下 16.67ms）的延迟通常不会让用户直接感知到——因为单帧的微小波动被前后帧的连续性"平滑"掉了。但如果连续多帧都 Jank，累积的延迟很快就会超过 100ms 的感知阈值。比如连续 3 个 VSync 周期没有新画面（约 50ms 的空白），在滑动场景下用户就能感知到"不跟手"。

[已验证: 官方文档, https://developer.android.com/topic/performance/vitals]
[引用: https://www.nngroup.com/articles/response-times-3-important-limits/]

### 不同场景下的感知差异

用户对卡顿的感知还取决于交互场景：

- **连续滑动**（列表、页面滚动）：这是用户对卡顿最敏感的场景。滑动时用户的视线在跟随手指移动内容，任何帧率的波动都能被感知到。推荐目标：稳定达到屏幕刷新率。
- **动画过渡**（页面切换、展开/收起）：对卡顿的敏感度略低于连续滑动，因为动画的方向和节奏是预设的。但突然的"跳帧"仍然很明显。
- **静态界面**：完全不对帧率有要求——画面不动就没有 Jank。

## [自动发现] JankStats：Google 官方的 Jank 监测库

来源：https://developer.android.com/reference/kotlin/androidx/metrics/performance/JankStats

JankStats 适合在测试环境或线上埋点里回答"哪一段 UI 状态更容易出 jank"。它基于 `FrameMetrics` / 平台帧信息收集每帧数据，能够把 Activity、页面状态、交互上下文一起带出来。FrameTimeline 更适合离线 trace 里做单帧归因，两者分工不同。

JankStats 里有一个 `jankHeuristicMultiplier`。官方 reference 写得很直接：阈值等于 `current refresh period × multiplier`，默认 multiplier 是 `2`。默认阈值是当前刷新周期的 2 倍，超过才报告 jank。注意这和"超过 1 个 VSync 就算 jank"不同。

在 Android 12+ 上，`frameOverrunNanos` 可以补"超了多少时间"；在旧版本上，JankStats 仍然能给出较粗的运行时 jank 统计，但归因粒度不如 FrameTimeline。用法上，JankStats 用来找"哪里经常卡"；Perfetto / FrameTimeline 用来查"这一帧为什么卡"。

如果要把 JankStats 结果接回章节前面的分类体系，最稳的方式是：线上先用 JankStats 标出高风险页面，再抓 Perfetto trace，用 `Expected Timeline` / `Actual Timeline` 和 token 回到 App、SurfaceFlinger、Display 责任链。

[已验证: AndroidX API reference, https://developer.android.com/reference/kotlin/androidx/metrics/performance/JankStats]

## 常见问题与误区

### 误区 1：「FPS 高就等于流畅」

这是最常见的误解。FPS 衡量的是帧的产量，不是帧的节奏。一秒内 50 帧全部挤在后半段，FPS 数值依然好看，但用户感受到的是前半段的"冻住"。正确的做法是关注 Jank 率和帧时间标准差，而不是盯着 FPS 不放。

### 误区 2：「Jank 都是 App 的问题」

从本节的分类可以看出，Jank 可能来自 App（AppDeadlineMissed）、SurfaceFlinger（SurfaceFlingerCpuDeadlineMissed）、甚至 Display HAL。在着手优化之前，先在 Perfetto 的 FrameTimeline 中确认 JankType，避免在错误的方向上浪费时间。

### 误区 3：「掉帧率必须做到 0%」

工程上要清理的是稳定重现的 jank 峰值、Frozen Frame 和高延迟状态，不是盯着一个抽象的 0%。列表高速滑动、复杂动画、启动首帧、高刷设备，容忍区间都不同。把所有场景压成一个全局掉帧率数字，既不利于定位，也不利于版本回归。更实用的做法是按交互路径、刷新率和统计窗口分别设预算。

### 误区 4：「120Hz 设备不需要优化，因为帧预算变小了」

120Hz 设备的帧预算只有 8.33ms，比 60Hz 的 16.67ms 紧了一半。原本在 60Hz 设备上刚好达标的渲染耗时，到了 120Hz 设备上可能就成了 Jank。高刷新率设备对渲染效率的要求更高，不是更低。

## 与其他章节的关系

- **2.1 渲染架构全景**：Jank 发生在渲染管线的各个环节，理解渲染架构是定位 Jank 的基础
- **2.3 VSync 机制**：Jank 的定义依赖于 VSync 周期，理解 VSync 才能理解 Jank 的"截止时间"
  - **VSync Offset 机制**：Android 14+ 的 VSyncPredictor（线性回归预测周期）和 VsyncModulator（三相动态调整 Early/EarlyGpu/Late）是影响 Jank 的底层因素，详见 → [2.3 VSync 机制] 第十一节源码补充
- **2.4 Choreographer 与渲染流水线**：App Jank 的核心检测点在 Choreographer 的 doFrame 流程中
- **2.5 MainThread 与 RenderThread 协作**：App Jank 可以进一步细分为主线程 Jank 和 RenderThread Jank
- **7.2 卡顿原因体系**：本节定义了"什么是卡顿"，7.2 则详细分析"卡顿是怎么产生的"
- **7.3 卡顿分析方法论**：基于本节的 Jank 分类，7.3 提供系统化的分析方法

## 参考资料

- AOSP 源码路径：
  - `frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp` - FrameTimeline 归因逻辑（Android 17）
  - `frameworks/native/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp` - FrameTimeline 归因逻辑（Android 16 及更早）
  - `frameworks/native/libs/gui/include/gui/JankInfo.h` - JankType 定义
  - `frameworks/base/core/java/android/view/Choreographer.java` - App 侧 frame 调度入口
  - `frameworks/base/core/java/android/view/FrameMetrics.java` - UI frame 指标接口
- 官方文档：
  - [Android Jank detection with FrameTimeline | Perfetto Docs](https://perfetto.dev/docs/data-sources/frametimeline)
  - [Slow rendering | Android Developers](https://developer.android.com/topic/performance/vitals/render)
  - [Diagnose and fix ANRs | Android Developers](https://developer.android.com/topic/performance/vitals/anr)
  - [JankStats | Android Developers](https://developer.android.com/reference/kotlin/androidx/metrics/performance/JankStats)
  - [FrameMetrics API | Android Developers](https://developer.android.com/reference/android/view/FrameMetrics)
  - [Response Time Limits | Nielsen Norman Group](https://www.nngroup.com/articles/response-times-3-important-limits/)
- 博客与文章：
  - 腾讯音乐：Android 深入卡顿分析与实践（来源：obsidian/Personal-Knowlodge/source/2026-03-07_wechat_Android深入卡顿分析与实践.md）
  - 高爷：Android Perfetto 系列 6 - 为什么是 120Hz（来源：obsidian/Personal-Knowlodge/source/Android-Perfetto-06-Why-120Hz.md）
  - 高爷：Android Perfetto 系列 5 - Choreographer 渲染流程（来源：obsidian/Personal-Knowlodge/source/Android-Perfetto-05-Chorergrapher.md）
