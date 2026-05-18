---
title: "InputDispatcher stale event 判定与事件丢弃"
chapter: "3.10"
section: "3.10"
status: ready-for-review
drafted_date: "2026-05-18"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)；stale timeout 以设备 HwTimeoutMultiplier 配置为准"
last_verified: "2026-05-18"
last_verified_against: "AOSP frameworks/native main InputDispatcher.cpp + InputDispatcher.h + AnrTracker.h"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/InputDispatcher.h"
  - type: aosp
    path: "frameworks/native/services/inputflinger/dispatcher/AnrTracker.h"
  - type: official
    path: "source.android.com/docs/core/interaction/input"
  - type: research
    path: "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-input-dispatcher-stale-event-versions.md"
tags: [input, inputdispatcher, stale-event, anr, latency]
related_chapters: ["3.1", "3.2", "3.7", "3.9", "9.2", "13.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-18"
gap_source: "素材驱动/AOSP结构/研究素材"
gap_score: 16
material_count: 5
source_candidates:
  - "/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-input-dispatcher-stale-event-versions.md"
  - "https://cs.android.com/android/platform/superproject/+/main:frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp"
  - "https://cs.android.com/android/platform/superproject/+/main:frameworks/native/services/inputflinger/dispatcher/InputDispatcher.h"
  - "https://source.android.com/docs/core/interaction/input"
---

# 3.10 InputDispatcher stale event 判定与事件丢弃

InputDispatcher 的 stale event 机制处理一种很具体的输入异常：事件还在队列里，但事件时间戳已经离当前时间太远，继续派发会把过期点击、过期按键或旧触摸样本送给窗口。对排查来说，它和 ANR、输入延迟、窗口阻塞很容易混在一起。本节把 stale 丢弃的判定点、和 ANR 的分工、日志与 trace 观察口径拆开。[来源: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-input-dispatcher-stale-event-versions.md]

<!-- outline-start -->
## 要点

### 🔹 stale event 解决的问题
说明 stale 事件是 InputDispatcher 对过期事件的保护性丢弃，不等同于应用主动消费，也不等同于 ANR 触发。

### 🔹 当前 AOSP 的判定入口
覆盖 `InputDispatcher::isStaleEvent()`、`STALE_EVENT_TIMEOUT`、`HwTimeoutMultiplier()` 与 policy 判定边界。

### 🔹 Key 与 Motion 的丢弃差异
解释 key 事件和 motion 事件在 stale 判定后的分流：按键可直接丢弃，触摸事件要避开正在进行的手势。

### 🔹 DropReason、取消事件与日志
梳理 `DropReason::STALE`、`dropInboundEventLocked()`、取消事件和 logcat 文案之间的关系。

### 🔹 stale timeout 与 Input ANR 的分工
说明 stale 丢弃、连接 ANR、no-focused-window ANR 和 blocked drop 的边界。

### 🔹 WindowInfo 与目标窗口状态
说明窗口可见性、可触摸区域、焦点和 touched window 状态如何影响 stale 后续分发判断。

### 🔹 排查入口：logcat、dumpsys、Perfetto
给出从日志、`dumpsys input`、Perfetto input 轨道和应用主线程堆栈定位 stale 丢弃的步骤。

### 🔹 版本边界与工程建议
记录 Android 11-17 的稳定口径、仍需实机确认的 OEM 差异，以及业务侧应避免的误判。

## 扩展

### 🔸 stale event 与连续手势取消策略
补充多指触控、hover、pointer capture 场景下的取消事件边界。

### 🔸 输入延迟与渲染延迟的联合判断
把 stale 事件、FrameTimeline、主线程阻塞和 SurfaceFlinger present 延迟放到同一条时间线上分析。

### 🔸 OEM timeout multiplier 差异
记录不同厂商是否调整 `HwTimeoutMultiplier()`，以及对 ANR 和 stale 判定的影响。
<!-- outline-end -->

## stale event 解决的问题

Android 输入系统会把硬件事件转成 Android 事件，再由 InputDispatcher 发给目标窗口。正常路径下，窗口收到事件后通过 InputChannel 回 ACK；如果窗口长时间不 ACK，后续事件会在 dispatcher 侧排队。stale event 机制处理的就是这种队列堆积后的尾部问题：事件还没送出去，但已经过期。

过期事件继续送给应用会制造两类问题。用户已经停止点击或滑动，旧事件再被处理会让页面出现迟到的跳转、重复点击或错位手势；同时，队列继续增长会让后续有效输入也被旧事件拖住。InputDispatcher 选择把过期事件丢弃，让系统从旧输入中恢复出来。

这不是应用“正常消费了事件”。logcat 中出现 `InputDispatcher: Dropped event because it is stale.` 时，含义是系统侧放弃了一个过期输入。应用没有机会处理这个事件，也不应把它当成业务回调丢失来修补。排查方向要回到：为什么目标窗口迟迟没有 ACK，为什么 dispatcher 队列里留住了旧事件。

[已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp] [已验证: 官方文档, source.android.com/docs/core/interaction/input]

## 当前 AOSP 的判定入口

AOSP main 中，stale 超时由 `STALE_EVENT_TIMEOUT` 定义：基础值是 10 秒，再乘以 `HwTimeoutMultiplier()`。`InputDispatcher::isStaleEvent()` 本身只把当前时间和事件时间戳交给 policy 判断；也就是说，判定使用的是事件产生时间，而不是应用收到事件的时间。

这段源码只需看三行：

```cpp
// frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp
const std::chrono::duration STALE_EVENT_TIMEOUT = std::chrono::seconds(10) * HwTimeoutMultiplier();

bool InputDispatcher::isStaleEvent(nsecs_t currentTime, const EventEntry& entry) {
    return mPolicy.isStaleEvent(currentTime, entry.eventTime);
}
```

这里的 `eventTime` 来自输入事件本身。触控硬件、EventHub、InputReader、InputDispatcher、应用主线程之间每多停一段时间，都会扩大 `currentTime - eventTime`。如果只看应用主线程收到事件后的耗时，很容易漏掉 dispatcher 队列中已经消耗掉的那几秒。

`HwTimeoutMultiplier()` 也要单独看。它不只影响 stale event，还会影响默认输入分发超时这类使用同一 multiplier 的时间预算。用户 debug 设备、慢速测试环境或厂商定制系统上，10 秒不一定是实机上的最终值。章节里的 10 秒应理解为 AOSP 基础值。[已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

## Key 与 Motion 的丢弃差异

Key 事件的 stale 判定比较直接。`dispatchOnceInnerLocked()` 取出 pending key 后，如果尚未被 policy、disabled 等条件丢弃，再调用 `isStaleEvent()`；命中后把 `dropReason` 置为 `DropReason::STALE`。随后 `dispatchKeyLocked()` 按这个原因完成丢弃流程。

Motion 事件多一个手势连续性的保护。AOSP main 的注释写得很明确：事件已经过期时，也只在没有正在进行的 gesture 时丢弃 stale motion，这样可以让当前 stroke 完成处理。实现上会检查对应 display 的 `TouchState`，确认同一 device 没有 touching pointers，也没有 hovering pointers，才把 `dropReason` 设为 `STALE`。

这个差异解释了一个常见现象：同样看到 InputDispatcher 队列阻塞，按键可能很快被判 stale，触摸序列却会为了不切断当前手势而继续走取消或完成路径。排查滑动卡死时，不能只拿单个 stale log 判断所有 motion 样本都被同样处理，要结合 ACTION_DOWN、MOVE、UP / CANCEL 和目标窗口 ACK 顺序看。

[已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

## DropReason、取消事件与日志

AOSP main 的 `DropReason` 枚举包括 `NOT_DROPPED`、`POLICY`、`DISABLED`、`BLOCKED`、`STALE`、`NO_POINTER_CAPTURE`。旧资料里常见的 `APP_SWITCH` 分支不应直接套到当前 main 代码上，写版本分析时要按目标 Android 分支复核。

`dropInboundEventLocked()` 命中 `DropReason::STALE` 后，会打印：

```cpp
ALOGI("Dropped event because it is stale.");
```

随后方法会按事件类型生成取消选项。对于 key，使用非 pointer 事件取消；对于 motion，取消路径要保护 pointer 状态和窗口状态。logcat 只告诉你“这个 inbound event 被丢了”，不告诉你前面哪个窗口、哪个线程、哪个锁让 ACK 迟迟没回来。

因此 stale log 适合作为入口，不适合作为结论。更稳的判断顺序是：定位 log 时间点，确认目标窗口和包名，检查同一时间段 InputDispatcher 是否等待该窗口 ACK，再看应用主线程、RenderThread、Binder 线程、系统服务调用是否卡住。只有这几项连起来，才能把“事件过期”落到具体原因上。

[已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.h] [已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

## stale timeout 与 Input ANR 的分工

stale timeout 和 Input ANR 不是同一个计时器。stale 判断面向 pending event 是否过期；ANR 判断面向连接是否长时间没有处理已经派发出去的输入，或者没有 focused window 可接收需要焦点的事件。AOSP 的 `AnrTracker` 用 multiset 保存待 ACK 事件的 timeout，并通过最早 timeout 决定下一次唤醒检查。

从排查角度，可以按下面这张表分开看：

| 机制 | 观察对象 | 典型触发条件 | 系统动作 | 排查入口 |
| --- | --- | --- | --- | --- |
| stale event | 仍在 dispatcher pending / inbound 路径上的旧事件 | `currentTime - eventTime` 超过 stale 预算 | 丢弃事件，打印 stale log | logcat、InputDispatcher 队列、目标窗口 ACK |
| connection ANR | 已派发到连接、等待 ACK 的事件 | 连接 timeout 到期 | policy 回调 ANR 决策 | ANR traces、`dumpsys input`、应用主线程 |
| no-focused-window ANR | 需要焦点窗口的事件 | 没有 focused window 且等待超时 | 丢弃/ANR 决策 | WindowManager 焦点、Activity 启动与窗口创建 |
| blocked drop | 当前应用不响应，用户开始和其他应用交互 | 新事件被旧连接阻塞 | 丢弃旧方向事件或解除阻塞 | logcat、窗口切换时间线 |

这个拆分能避免一个误判：看到 stale log 后直接说“发生 ANR”。ANR 可能已经发生，也可能被 policy 延长，也可能完全没有弹出；stale 丢弃只说明输入事件过期。反过来，发生 Input ANR 也不一定马上出现 stale log，因为 ANR 关注的是连接响应，stale 关注的是事件时间戳。

[已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/AnrTracker.h] [已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp]

## WindowInfo 与目标窗口状态

InputDispatcher 不是把所有输入直接发给当前 Activity。它要根据 display、焦点、window token、可见性、touchable region、pointer capture、遮挡状态等信息选择目标窗口。AOSP main 的 hit test 会检查窗口所在 display、`NOT_VISIBLE`、`NOT_TOUCHABLE`、touchable region 等条件，命中后才可能成为触摸目标。

这层窗口状态会影响 stale 事件之后的分析。举例来说，用户看到“点了没反应”，原因可能是应用主线程没有 ACK，也可能是焦点窗口还没创建、窗口不可触摸、pointer capture 不存在、或旧窗口的触摸状态还没清掉。stale log 只能证明某个输入在 dispatcher 侧过期，不能直接证明业务 View 的 `onClick()` 有问题。

排查窗口状态时，优先看三类信息：当前 focused window 是否符合预期，touched window 是否仍指向旧窗口，目标窗口是否设置了不可触摸或遮挡相关标志。对应到章节关系，3.1 节讲完整输入分发，3.7 节讲反压与窗口降级，本节只记录 stale 事件在这条路径中的位置。

[已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp] [关联: 3.1, 3.7]

## 排查入口：logcat、dumpsys、Perfetto

现场排查可以按时间线走，不要从 stale log 直接跳到业务结论。

1. **用 logcat 定位 stale 时间点**：搜索 `InputDispatcher` 和 `Dropped event because it is stale`，记录时间戳、前后窗口切换日志、ANR 日志和 ActivityTaskManager 日志。
2. **用 `dumpsys input` 看 dispatcher 状态**：关注 focused window、dispatch enabled / frozen、inbound / outbound / wait queue、recent events、connection 状态。不同 Android 版本的字段名会变，命令口径以实机输出为准。[待验证: 各 OEM dumpsys 字段差异]
3. **用 Perfetto 对齐线程状态**：抓取 input、sched、freq、binder_driver、view、wm、am、gfx、frametimeline 等类别，检查 InputDispatcher 线程、目标应用主线程、RenderThread、Binder 线程是否在 stale 前长期 Running、Runnable、Blocked 或 Sleeping。[待验证: 具体 track 名按 Perfetto 版本变化]
4. **回到应用主线程证据**：如果目标窗口已经收到事件但未 ACK，看主线程堆栈、锁等待、同步 I/O、Binder 调用、布局和渲染耗时；如果窗口没有收到事件，看焦点、窗口创建、可触摸区域和系统窗口遮挡。

这套步骤的目的不是证明 “InputDispatcher 出错”，而是把过期事件还原成时间线：事件什么时候进入系统，什么时候卡在 dispatcher，目标窗口当时是什么状态，应用线程在做什么，系统丢弃了哪类事件。

[来源: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-input-dispatcher-stale-event-versions.md] [关联: 13.8, 3.9]

## 版本边界与工程建议

本节按 AOSP main 复核了当前实现。Android 11-17 的输入路径仍围绕 EventHub、InputReader、InputDispatcher、WindowManager 和 InputChannel 展开，但文件位置、`DropReason` 枚举、policy 接口、WindowInfo 更新方式会随分支变化。旧文章中的 switch 分支、函数名、目录结构只能作为历史参考，不能直接写成 Android 16/17 事实。

工程侧建议保守处理三件事：

- **不要把 stale log 当成业务回调丢失**：它发生在系统丢弃过期事件时，应用通常没有拿到这个事件。
- **不要把 stale timeout 当成用户体验目标**：10 秒级保护只负责系统自救；输入跟手性要看 3.9 节的端到端延迟预算。
- **不要只修点击防抖**：如果 stale 来自主线程阻塞、窗口未就绪或 Binder 调用卡住，业务层防抖不会消除 dispatcher 队列堆积。

如果线上监控捕获到 stale log，推荐把它归入“输入无响应症状”，再和 ANR、慢帧、主线程长任务、窗口焦点异常一起聚合。单条 stale log 的价值有限，一段时间内同机型、同页面、同版本反复出现，才值得进入专项治理。

[已验证: AOSP main, frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp] [适用版本: Android 11 - Android 17]

## 扩展：stale event 与连续手势取消策略

连续手势不能按单个事件理解。AOSP main 对 motion stale 的保护就是为了避免中途切断一个 stroke：只要同一 device 仍有 touching pointers 或 hovering pointers，dispatcher 就不会简单把该 motion 设为 `DropReason::STALE`。这类场景要同时看 pointer id、ACTION_CANCEL、目标窗口和 touch state，不能只按 log 条数统计。

Pointer capture、hover 和多指触控还会改变取消事件的边界。当前章节只写通用分支；如果后续补实机 trace，建议把 stylus hover、鼠标 pointer capture、游戏多指触控分成三组样本，分别确认 stale 前后的 CANCEL 派发方式。[待补充: 多设备实机 trace]

## 扩展：输入延迟与渲染延迟的联合判断

stale event 描述的是输入事件在 dispatcher 侧过期，不描述画面何时显示。一次“点了没反应”可能同时包含输入排队、主线程阻塞、渲染错过 deadline、SurfaceFlinger present 延迟。排查时应把 stale log 的时间点和 FrameTimeline、主线程 slice、RenderThread、SurfaceFlinger present 放到同一条时间线上。

如果 stale 发生前应用主线程长期 Running 或 Blocked，输入排队大概率是症状；如果输入已经及时送达，但画面迟迟不更新，问题会转到渲染路径。对应章节可以直接引用 3.9 节的端到端预算和 13.8 节的输入延迟 SQL，不在本节重复展开。

## 扩展：OEM timeout multiplier 差异

`HwTimeoutMultiplier()` 使 AOSP 基础超时和实机行为之间存在设备差异。测试环境、debug 属性、厂商系统配置都可能放大输入分发相关 timeout；如果只按 10 秒写死，容易在 OEM 问题复盘中误判时间线。

当前已验证的是 AOSP main 中 stale timeout 使用 `std::chrono::seconds(10) * HwTimeoutMultiplier()`。各厂商是否调整 multiplier、是否对 `dumpsys input` 字段做定制、是否额外采集 dropped event 计数，需要按设备验证。[待补充: OEM 实机属性与 dumpsys 对比]

## 延伸阅读

- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp`：stale 判定、分发主循环、drop reason 处理。
- `frameworks/native/services/inputflinger/dispatcher/InputDispatcher.h`：`DropReason` 枚举和 dispatcher 状态字段。
- `frameworks/native/services/inputflinger/dispatcher/AnrTracker.h`：连接 ANR 计时集合。
- `source.android.com/docs/core/interaction/input`：Android 官方输入路径说明。
- `/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-input-dispatcher-stale-event-versions.md`：本节的素材入口。
