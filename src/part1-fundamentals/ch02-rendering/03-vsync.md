---
title: "VSync 机制"
chapter: "2.3"
reviewed_date: "2026-05-10"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-04"
polish_by: "task2b-polish"
applicable_versions: "Android 4.1 (API 16) - Android 17 (API 37)"
last_verified: "2026-05-10"
last_verified_against: "AOSP android-16.0.0_r1 Scheduler/VSyncPredictor.cpp + VSyncReactor.cpp + VSyncDispatchTimerQueue"
confidence: high
sources:
  - "frameworks/native/services/surfaceflinger/Scheduler/VSyncPredictor.cpp"
  - "frameworks/native/services/surfaceflinger/Scheduler/VSyncReactor.cpp"
  - "frameworks/native/services/surfaceflinger/Scheduler/VsyncSchedule.cpp"
  - "frameworks/native/services/surfaceflinger/Scheduler/EventThread.cpp"
  - "frameworks/native/services/surfaceflinger/Scheduler/MessageQueue.cpp"
  - "frameworks/native/services/surfaceflinger/Scheduler/VSyncDispatchTimerQueue.cpp"
  - "frameworks/base/core/java/android/view/Choreographer.java"
  - "frameworks/base/core/java/android/os/Looper.java"
  - "frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java"
  - "frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java"
  - "frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java"
  - "https://source.android.com/docs/core/graphics/implement-vsync"
  - "https://developer.android.com/about/versions/16/features"
tags: "[vsync, dispsync, choreographer, surfaceflinger, phase-offset, arr, rendering, vsyncschedule]"
related_chapters: "[\"2.1\", \"2.4\", \"2.5\", \"2.6\", \"2.9\", \"8.1\"]"
task6_state: reviewed
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-09"
review_round: 4
repaired_date: "2026-05-09"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-05-09T12:43:00+08:00"
status: "finalized"
pipeline_stage: ready-to-publish
task9_result: "auto-fixed"
task9_reviewed_date: "2026-06-09"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-09T14:20:00+08:00"
task2b_state: "fixed"
last_task2b_at: "2026-05-15T03:17:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-09-14-audit.md"
task9_review_notes: "2026-06-09 Task9 闲时抽检：auto-fixed。修正 NDK Choreographer API 名 `AChoreographer_vsyncCallback`；AOSP android-16.0.0_r1 header 已复核，Android 17 tag 当前未在 android.googlesource 公开，章节 Android 17 内容保留待验证边界。P0 1（已修）/ P1 0 / P2 1（既有 suggestions，不重复）。"
task2b_result: "fixed"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
last_task6_audit: "2026-06-30"
task9_state: "reviewed"
last_task9_audit: "2026-06-09"
last_task9_audit_log: "logs/deep-review/2026-06-09-14-audit.md"
last_task9_autofix_at: "2026-06-09"
---

# VSync 机制

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 VSync 的起源:解决画面撕裂(Screen Tearing)
- 🔹 Android VSync 架构:HW-VSync → SF-VSync → App-VSync 三级信号
- 🔹 VSync Phase Offset 的作用与调优
- 🔹 VSync 信号在 SurfaceFlinger 和 Choreographer 中的传递路径
- 🔹 VSync 在 Perfetto 中的观察:VSYNC-sf、VSYNC-app

### 扩展(可选深入)

- 🔸 可变刷新率下 VSync 行为的变化
- 🔸 VSync 偏移量对输入延迟的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 VSync

在 Perfetto 中观察任何 UI 渲染 Trace,最显著的特征是两条规律跳动的竖线--VSYNC-app 和 VSYNC-sf。这两条信号是整个渲染管线的节拍器:App 开始绘制、SurfaceFlinger 开始合成、屏幕开始刷新的时序全部由它们控制。

VSync 决定了渲染延迟的基准线。不理解 VSync，你无法解释为什么同一帧从 App 绘制完成到屏幕显示可能需要 1~3 个 VSync 周期；无法理解纳秒级偏移量调整如何直接影响跟手性；也无法把握 Android 从 4.1 到 16 的渲染演进逻辑。掌握 VSync 是解决渲染时序问题的根本前提。

本章将从 VSync 解决画面撕裂问题的历史说起,经过软件虚拟化实现、相位偏移调优,一直到 Android 15/16 的自适应刷新率(ARR)。学完后,你将能够读懂 Perfetto 中的 VSync Track,准确定位渲染时序问题的根源。
---

## 一、VSync 的起源:画面撕裂问题

### 1.1 什么是画面撕裂(Screen Tearing)

显示屏刷新画面的方式是像素自上而下逐行扫描。每一帧的扫描过程是连续的,如果在上一帧还没扫描完的时候,帧缓冲(Frame Buffer)的内容被替换成了下一帧的数据,屏幕上半部分显示的就是旧帧、下半部分显示的就是新帧--这就是画面撕裂。

[图:Screen Tearing 示意图--上半帧和下半帧画面水平错位]

画面撕裂在快速滚动、动画、游戏等场景下尤为明显。早期的 PC 游戏玩家对此深有体会:快速转动视角时,画面中间会出现一条明显的"水平裂缝"。

### 1.2 VSync 的基本思路

解决画面撕裂的方案是:**在屏幕完成一帧扫描、准备开始下一帧扫描的间隙,才允许更新帧缓冲的数据**。这个间隙就是垂直同步(Vertical Synchronization,简称 VSync)信号。

VSync 信号也叫 VBlank 信号或 TE (Tearing Effect) 信号。从硬件角度看,它是显示屏上的一个引脚产生的电平变化(通常是上升沿中断);从软件角度看,它是一个 GPIO 中断,系统根据这个中断来安排渲染和合成的时序。

[图:VSync on vs VSync off 对比--开启 VSync 后画面不再撕裂]

### 1.3 双缓冲机制

与 VSync 配合工作的是双缓冲(Double Buffering)。系统维护两块帧缓冲:

- **Front Buffer**:屏幕正在读取显示的那块缓冲
- **Back Buffer**:GPU 正在写入渲染数据的那块缓冲

当 VSync 信号到来时,两块缓冲的角色互换--Back Buffer 变成 Front Buffer 交给屏幕显示,Front Buffer 变成 Back Buffer 供 GPU 写入下一帧。这种交换叫做 Buffer Swap。

双缓冲配合 VSync 基本解决了撕裂问题,但也带来了新的挑战:如果 App 的渲染耗时超过一个 VSync 周期(比如 60Hz 屏幕的 16.66ms),Back Buffer 还没准备好,Buffer Swap 就不会发生,屏幕只能再显示一次旧帧--这就是**掉帧(Jank)**。

`[已验证: 官方文档, source.android.com/docs/core/graphics/implement-vsync]`

---

## 二、Android VSync 三级信号架构

### 2.1 从 Project Butter 说起

Android 4.1(Jelly Bean,2012 年)引入了 Project Butter(黄油计划),这是 Android 历史上第一次系统性地解决流畅度问题。Project Butter 的三个核心组件是:

1. **VSync 同步**:让 App 渲染、SurfaceFlinger 合成都跟硬件 VSync 同步
2. **Choreographer**:让 App 能按 VSync 节拍进行绘制
3. **三缓冲(Triple Buffer)**:缓解双缓冲下偶发超时导致的连续掉帧

没有 VSync 同步的情况下，App 渲染节奏与屏幕刷新节奏完全脱节。App 可能在 VSync 周期的任意时刻完成渲染，如果完成时间刚好错过了一次 Buffer Swap，这一帧就要等到下一个 VSync 才能显示，白白浪费一个周期。有了 VSync 同步后，所有参与者都在 VSync 到来时才动手，节奏统一，掉帧的概率大大降低。

`[已验证: 官方文档, source.android.com/docs/core/graphics/implement-vsync]`

### 2.2 三级信号:HW-VSync / VSYNC-app / VSYNC-sf

Android 的 VSync 架构将硬件 VSync 分成了三级,周期相同但相位不同:

```
HW_VSYNC_0(硬件 VSync)
    ↓ DispSync 虚拟化
    ├→ VSYNC-app(App VSync)→ 驱动 Choreographer → App 渲染
    └→ VSYNC-sf(SF VSync)  → 驱动 SurfaceFlinger → 合成
```

- **HW_VSYNC_0**:硬件产生的原始 VSync 信号,标识显示器开始显示下一帧的瞬间。以 60Hz 屏幕为例,每 16.66ms 产生一次;120Hz 则是每 8.33ms。由 HWC (Hardware Composer) 产生。
- **VSYNC-app**:触发 App 读取输入事件并开始渲染。收到这个信号后,Choreographer 开始执行 doFrame,依次处理 Input → Animation → Traversal(measure/layout/draw)。
- **VSYNC-sf**:触发 SurfaceFlinger 开始合成。收到这个信号后,SurfaceFlinger 从各 App 的 BufferQueue 中取出已渲染好的 GraphicBuffer,合成最终画面交给 HWC。

三者的关系可以用一个理想化的流水线来理解:

| 时刻 | 显示器 | SurfaceFlinger | App |
|------|--------|----------------|-----|
| VSync N | 显示第 N 帧 | 合成第 N+1 帧 | 渲染第 N+2 帧 |

在这个理想状态下,三个环节同时工作在不同的帧上,流水线满载。但如果没有 Phase Offset 调优,实际达不到这种理想状态--后面我们会详细展开。

`[已验证: 官方文档 implement-vsync + AOSP android-16.0.0_r1, Scheduler/VSyncPredictor.cpp + Scheduler/VSyncReactor.cpp]`

### 2.3 为什么不直接用硬件 VSync

一个自然的疑问是:为什么不直接把 HW_VSYNC_0 广播给 App 和 SurfaceFlinger?

原因有三个:

**第一，功耗。** 硬件 VSync 频率极高（120Hz 就是每秒 120 次中断），每次中断都要从内核态切换到用户态，开销不小。而且绝大多数时候 VSync 的周期是固定可预测的，没必要每次都从硬件获取。

**第二，解耦。** App 很多，如果每个 App 都直接监听硬件中断，耦合性太高。需要一个中间层来管理订阅关系——谁需要 VSync 就给谁发，不需要的就不发（按需分发）。

**第三，灵活性。** 软件虚拟化后可以对 VSync 信号做各种定制——调整相位偏移、改变周期、适应可变刷新率——这些在硬件层面做不了或者代价很高。

所以 Android 的方案是:用一个软件模型来"学习"硬件 VSync 的规律,然后基于模型按需生成虚拟 VSync 信号。这个软件模型就是 DispSync。

`[已验证: AOSP android-16.0.0_r1, Scheduler/VSyncPredictor.cpp + Scheduler/VSyncReactor.cpp + 官方文档 implement-vsync]`

---

## 三、DispSync:软件锁相环

### 3.1 DispSync 是什么

如果只看早期 Android 文章,VSync 虚拟化的中心名词通常是 DispSync。这个叫法没有错,但按本文 `last_verified_against: android-16.0.0_r1` 的公开源码来看,这套职责已经拆进 `services/surfaceflinger/Scheduler/` 目录,不再由单个 `DispSync.cpp` 承担。

从分析视角看,我们关心的事情没有变:系统拿到少量真实的硬件时间戳后,先建立一个可以预测下一次 VSync 的软件模型,再把预测结果分发给 App 和 SurfaceFlinger。只是到了 Android 16,这几个职责分别落在不同文件里:

- `VSyncReactor.cpp`:接收 HW_VSYNC 和 Present Fence 样本,决定是否继续采样
- `VSyncPredictor.cpp`:把样本写入预测器,估算未来的 VSync 时间点
- `EventThread.cpp`:把 VSYNC-app / vsync-appSf 分发给应用侧连接
- `MessageQueue.cpp`:把 VSYNC-sf 送回 SurfaceFlinger 自己的合成消息队列

因此,本文后面仍沿用"DispSync 模型"这个历史称呼,方便和旧资料对应;一旦落到 Android 16 当前实现,就以 Scheduler 目录下的这些文件为准。

从抽象层面看,这个模型始终围绕三个量展开:显示周期、参考时间、相位偏移。早期实现会把这些量直接放在 `mPeriod`、`mReferenceTime`、`mPhase` 一类成员里;新的实现改成预测器和时间线对象来表达,但你在 Perfetto 里看到的现象没有变,仍然是"同一周期,不同相位"的多路 VSync。

### 3.2 模型如何工作

在 Android 16 当前实现里,学习和校正不是靠 `DispSync::addResyncSample()` 一条路径完成,而是 `VSyncReactor` 把样本交给 `VSyncPredictor`:

```cpp
// services/surfaceflinger/Scheduler/VSyncReactor.cpp
// @ AOSP android-16.0.0_r1
bool VSyncReactor::addHwVsyncTimestamp(nsecs_t timestamp,
                                       std::optional<nsecs_t> hwcVsyncPeriod,
                                       bool* periodFlushed) {
    ...
    mTracker.addVsyncTimestamp(timestamp);
    mMoreSamplesNeeded = mTracker.needsMoreSamples();
}
```

这几行代码说明两件事。第一,硬件 VSync 并不会直接广播给所有消费者,而是先作为"样本"送进跟踪器。第二,系统会持续判断 `needsMoreSamples()`,也就是当前模型是否还需要更多真实样本。

真正负责更新预测模型的是 `VSyncPredictor`:

```cpp
// services/surfaceflinger/Scheduler/VSyncPredictor.cpp
// @ AOSP android-16.0.0_r1
bool VSyncPredictor::addVsyncTimestamp(nsecs_t timestamp) {
    ...
    if (!validate(timestamp)) {
        ...
    }
    ...
}
```

这里的 `validate(timestamp)` 很关键。预测器不会盲目接受所有时间戳,样本明显跑偏时会清理历史窗口或重新学习,避免把错误周期带进后续预测。

Present Fence 也走同一套入口。`VSyncReactor::addPresentFence()` 在 fence signal 后同样会调用 `mTracker.addVsyncTimestamp(time)`,所以现代架构里"硬件采样"和"present fence 校正"最终都落到同一个预测器里。

把流程拉直来看,可以分成三步:

**1)学习**:`VSyncReactor` 接收 HW_VSYNC 或 Present Fence 时间戳,把样本交给 `VSyncPredictor`。模型初建、刷新率切换或校正失败时,`needsMoreSamples()` 会保持为 true,系统继续打开硬件采样。

**2)预测**:样本足够后,`VSyncPredictor::nextAnticipatedVSyncTimeFrom()` 会从当前时间点推算未来的 VSync 时间。SurfaceFlinger 和 App 侧分发使用这个预测结果,通常不等待每一拍真实中断。

**3)校正**:一旦硬件真实时间和预测结果偏差变大,`validate()` 会失败,或者 `VSyncReactor` 在刷新率切换、Present Fence 异常时重新进入采样模式。Perfetto 里短暂出现 HW_VSYNC 开启,表示系统正在重新收集样本；模型稳定后仍回到软件预测和定时分发。

`[已验证: AOSP android-16.0.0_r1, Scheduler/VSyncPredictor.cpp + Scheduler/VSyncReactor.cpp + 官方文档 implement-vsync]`

### 3.3 现代架构:Scheduler 子目录承担 DispSync 的旧职责

对照 Android 4.x 资料和 Android 16 公开源码时,容易把文件名变化误读成架构替换。实际变化主要是职责拆分,基本思路仍是采样、预测、按相位分发。

- `VSyncPredictor`:根据历史样本预测未来 VSync 时间点
- `VSyncReactor`:处理 HW_VSYNC / Present Fence,决定何时重新学习
- `VSyncDispatchTimerQueue`:按 `workDuration`、`readyDuration` 和 phase 安排回调触发时刻
- `EventThread`:服务 VSYNC-app / vsync-appSf 客户端
- `MessageQueue`:服务 VSYNC-sf,把合成消息送回 SurfaceFlinger

现代实现里,Scheduler 下的预测、校正和分发组件共同承担了旧版 DispSync 的工作。从 Android 14 起,这些组件在 SurfaceFlinger 内部由 `VsyncSchedule` 类统一持有——它组合了 `VSyncPredictor`、`VSyncReactor`、`VSyncDispatchTimerQueue` 和 `VsyncModulator`,对外提供 `nextAnticipatedVSyncTimeFrom()` 等统一入口。在分析 Perfetto 或追踪 AOSP 调用链时,可以把 `VsyncSchedule` 理解为 SurfaceFlinger Scheduler 的 VSync 总调度器。

## 四、VSync 信号的传递路径

### 4.1 SurfaceFlinger 侧:VSYNC-sf

SurfaceFlinger 获取 VSync-sf 的路径相对简洁:

```
VsyncSchedule / VSyncPredictor(软件 VSync 模型)
    → VSyncDispatchTimerQueue(根据 phase offset 计算触发时间,设置定时器)
        → 定时器到期 → timerCallback
            → MessageQueue::vsyncCallback
                → SurfaceFlinger::onMessageReceived(处理合成逻辑)
```

在较新的 AOSP 版本中,SurfaceFlinger 的 MessageQueue 直接向 VSyncDispatchTimerQueue 注册回调。当定时器在 VSYNC-sf 的时间点触发时,回调直接走到 SurfaceFlinger 的消息处理逻辑。

这条路径不经过 EventThread,因为 VSYNC-sf 是 SurfaceFlinger "自己用"的--在 Android T (13) 之前,sf EventThread 同时承担唤醒 SurfaceFlinger 和服务 Choreographer 客户端的职责,但从 Android 13 开始这两个职责被解耦了(详见后文 vsync-appSf 部分)。

`[已验证: AOSP android-16.0.0_r1, Scheduler/EventThread.cpp + Scheduler/MessageQueue.cpp]`

### 4.2 App 侧:VSYNC-app

如果按 Android 16 当前实现看,App 侧的主路径可以概括为:

```
VsyncSchedule(内部持有预测器和 dispatch)
    → VSyncDispatchTimerQueue(按 app 的 workDuration / readyDuration 计算触发时刻)
        → app EventThread
            → BitTube(基于 Unix Domain Socket 的 IPC)
                → DisplayEventReceiver(App 进程端)
                    → Choreographer::doFrame
```

这里要把"当前实现"和"历史资料"分开看。很多旧文章会写成 `DispSyncSource → CallbackRepeater → EventThread`,这是 DispSync 时代常见的描述。按 `android-16.0.0_r1` 的公开 Scheduler 树,当前主路径更接近 `VsyncSchedule → VSyncDispatchTimerQueue → EventThread`,旧类名更适合放在历史实现背景里,而不是直接当成现在的主干代码路径。

这条链路有几个值得关注的细节:

**BitTube 是什么?** BitTube 是 Android 封装的基于 Unix Domain Socket 的 IPC 通道。选择它的原因是 VSync 信号频率高、需要有序传输、且要高效,Domain Socket 在这些方面更合适。

**按需分发**:VSYNC-app 不是一直发的。只有当 App 调用了 `requestNextVsync()`,比如 `View.invalidate()` 最终走到 `Choreographer.scheduleFrameLocked()`,EventThread 才会在下一个 VSync 时间点向该 App 发送信号。如果 App 的 UI 静止不动,没有动画、没有触摸,就不会收到 VSYNC-app。这个设计节省了大量不必要的 CPU 开销。

`[已验证: AOSP android-16.0.0_r1, Scheduler/EventThread.cpp + Scheduler/VSyncDispatchTimerQueue.cpp + Choreographer.java]`

### 4.3 Android 13+ 新增:vsync-appSf

Android 13 引入了一个新的 VSync 信号--**vsync-appSf**,解决的是旧架构中 sf EventThread 的双重职责问题。

在 Android 13 之前,sf EventThread 同时做两件事:

1. 唤醒 SurfaceFlinger 进行合成
2. 为需要与 SurfaceFlinger 紧密同步的 Choreographer 客户端提供信号

这两种消费者对时序的要求不同:SurfaceFlinger 需要的是"该合成了",而 Choreographer 客户端需要的是"SurfaceFlinger 的内部状态已经更新了"。把这两种需求混在同一个 EventThread 里会导致时序歧义。

vsync-appSf 将这两个职责分离:

- **vsync-sf**:专用于驱动 SurfaceFlinger 合成
- **vsync-appSf**:专用于需要与 SurfaceFlinger 内部状态紧密同步的 Choreographer 客户端

同时,从 API 33 开始,Android 提供了 NDK Choreographer API(`AChoreographer_vsyncCallback`),允许应用使用正确的帧节奏(Frame Pacing),甚至可以选择渲染到未来的某一帧。这个 API 提供多个可能的帧时间线信息,App 可以根据渲染截止时间和期望的展示时间来选择最合适的时间线。

`[已验证: 官方文档 Android NDK Choreographer + AOSP android-16.0.0_r1, Scheduler/EventThread.cpp]`

### 4.4 传递路径总结

[图:VSync 信号传递路径全景图--从 HW_VSYNC_0 到 Scheduler 到 EventThread/MessageQueue 到 Choreographer 的完整链路]

```
HW_VSYNC_0 (HWC 硬件中断)
    ↓ addHwVsyncTimestamp / addPresentFence
VSyncReactor + VSyncPredictor (软件模型)
    ↓
    ├──→ [Phase: SF offset]
    │    VSyncDispatchTimerQueue → MessageQueue::vsyncCallback
    │    → SurfaceFlinger 合成 (VSYNC-sf)
    │
    ├──→ [Phase: App offset]
    │    VSyncDispatchTimerQueue → EventThread (app)
    │    → BitTube → DisplayEventReceiver → Choreographer (VSYNC-app)
    │
    └──→ [Phase: AppSF offset, Android 13+]
         VSyncDispatchTimerQueue → EventThread (appSf)
         → BitTube → DisplayEventReceiver → Choreographer (vsync-appSf)
```

---

## 五、VSync Phase Offset 的作用与调优

### 5.1 为什么需要 Phase Offset

如果 VSYNC-app 和 VSYNC-sf 与 HW_VSYNC_0 完全同时触发(即 offset 为 0),会发生什么?

```
VSync 到来时:
  - App 开始渲染帧 N
  - SurfaceFlinger 开始合成......但帧 N 还没画完!
  - SurfaceFlinger 只能拿到帧 N-1 的 buffer
  - 屏幕显示帧 N-2
```

结果是:从 App 开始渲染到用户看到画面,至少需要 **3 个 VSync 周期**。以 60Hz 屏幕计算就是约 50ms 的延迟--用户触摸屏幕后要等 50ms 才能看到响应,这对跟手性来说是不可接受的。

### 5.2 Phase Offset 如何工作

Phase Offset 的核心思路是:**让 App 和 SurfaceFlinger 在不同的时刻开始工作,使它们的工作时间重叠,从而压缩整体延迟**。

具体来说:

- **VSYNC-app 的 offset**:让 App 在 HW_VSYNC_0 到来之前就提前开始渲染。这样当 VSYNC-sf 到来时,App 的帧可能已经画好了。
- **VSYNC-sf 的 offset**:让 SurfaceFlinger 在 HW_VSYNC_0 到来之前的某个时刻开始合成。这样当屏幕刷新时,合成好的帧已经准备好了。

```
时间线(Phase Offset 优化后):

  VSYNC-app      → App 开始渲染
       ↓ (渲染中)
  VSYNC-sf       → SF 开始合成(App 已渲染完毕)
       ↓ (合成中)
  HW_VSYNC_0     → 屏幕显示(SF 已合成完毕)
```

理想情况下,三个阶段在一个 VSync 周期内流水线化完成,延迟从 3 帧降到 1~2 帧。

### 5.3 配置方式

Phase Offset 有两种配置方式,对应两个时代:

**Legacy 方式:直接配置纳秒偏移量**

在设备的 `BoardConfig.mk` 中配置:
```
VSYNC_EVENT_PHASE_OFFSET_NS := 2333334
SF_VSYNC_EVENT_PHASE_OFFSET_NS := 6166667
```

**Modern 方式:基于工作时长(WorkDuration)自动计算**

从较新的 AOSP 版本开始,引入了 `VsyncConfiguration` + `WorkDuration` 抽象,取代手动配置固定纳秒值。核心思想是:你只需要告诉系统"App 渲染一帧需要多久、SurfaceFlinger 合成一帧需要多久",系统自动计算最优的 offset。

配置属性(通过 `setprop` 或 `BoardConfig.mk`):
```
debug.sf.late.app.duration  = 20500000  (ns)
debug.sf.late.sf.duration   = 10500000  (ns)
debug.sf.early.app.duration = 16500000  (ns)
debug.sf.early.sf.duration  = 16000000  (ns)
debug.sf.earlyGl.app.duration = 21000000  (ns)
debug.sf.earlyGl.sf.duration  = 13500000  (ns)
```

offset 的计算公式为:
```cpp
// sfDurationToOffset: sfOffset = vsyncDuration - sfDuration % vsyncDuration
// appDurationToOffset: appOffset = vsyncDuration - (appDuration + sfDuration) % vsyncDuration
```

以 60Hz(vsyncDuration = 16,666,667 ns)为例:
```
sf phase = 16666667 - 10500000 % 16666667 = 6166667 ns
app phase = 16666667 - (20500000 + 10500000) % 16666667 = 2333334 ns
```

在实际分析中,可以通过 `adb shell dumpsys SurfaceFlinger | grep phase` 查看当前设备的实际 offset 值,对比配置表中的理论值来判断 offset 是否被正确应用--如果两者偏差较大,可能是设备厂商覆写了默认配置或系统切换到了不同的 WorkDuration 配置集。

系统会在不同场景下切换三组配置:

| 场景 | App Duration | SF Duration | 说明 |
|------|-------------|-------------|------|
| 正常 (late) | 20500000 | 10500000 | 大部分时间的默认配置 |
| 帧率切换 (early) | 16500000 | 16000000 | 切换屏幕刷新率时使用 |
| GPU 合成 (earlyGl) | 21000000 | 13500000 | SF 使用 GPU 合成时使用 |

`[已验证: 官方文档 implement-vsync + AOSP android-16.0.0_r1, Scheduler/VsyncConfiguration.cpp]`

### 5.4 调优的风险

Phase Offset 不是越大越好,也不是越小越好。它是一个需要精细平衡的参数:

如果 offset 过短,App 渲染还没完成 SurfaceFlinger 就开始合成了--SurfaceFlinger 拿不到最新的 buffer,这一帧白等,延迟反而增加。如果 offset 过长,App 和 SF 的工作时间几乎不重叠,失去了流水线化的优势,延迟接近 3 帧。理想状态下,App 刚好在 SF 开始合成前完成渲染,SF 刚好在屏幕刷新前完成合成--这也是 Phase Offset 调优的终极目标。

`[来源: Cubox收藏, cloud.tencent.com/developer/article/1905184 - Vsync Phase 详解]`

实际 OEM 调优中,调整 offset 是提升跟手性的常用手段。但任何改动都需要配合充分的自动化测试,因为 offset 效果高度依赖 App 渲染耗时和 SF 合成耗时,不同场景下表现差异很大。

---

## 六、VSync 在 Perfetto 中的观察

### 6.1 关键 Track

在 Perfetto 中,VSync 相关的信息主要出现在以下 Track:

- **VSYNC-app**:在 App 进程中可见,标识 Choreographer 收到 VSync 信号的时刻。每次跳变对应一次 `doFrame` 调用
- **VSYNC-sf**:在 SurfaceFlinger 进程中可见,标识 SF 收到 VSync 信号的时刻。每次跳变对应一次合成操作
- **HW_VSYNC**:在 SurfaceFlinger 进程中可见,偶尔出现(系统检测到模型需要校正时才开启)。在 Perfetto 中表现为 SurfaceFlinger 进程里短暂的硬件 VSync 采样脉冲

### 6.2 正常 vs 异常的 VSync 表现

**正常情况:**

在 Perfetto 中,VSYNC-app 和 VSYNC-sf 以稳定的间隔规律跳动。在 60Hz 设备上,间隔约 16.66ms;在 120Hz 设备上约 8.33ms。两者之间有一个固定的时间差(即 Phase Offset)。

[图:Perfetto 中正常的 VSYNC-app 和 VSYNC-sf Track--间隔均匀、相位稳定]

**异常情况 1:VSync 抖动**

VSync 间隔不稳定,忽大忽小。可能原因:
- DispSync 模型精度不足,频繁开启 HW_VSYNC 校正
- 热限频(Thermal Throttling)导致系统时钟不稳
- 某些厂商的 HAL 实现问题

**异常情况 2:VSYNC-sf 跳变延迟**

正常情况下 VSYNC-sf 在每个 VSync 周期的固定时刻触发。如果发现触发时间明显偏移,说明 SurfaceFlinger 被其他工作阻塞(比如 GPU 合成耗时过长),来不及按时响应 VSync 回调。

**异常情况 3:HW_VSYNC 频繁开启**

如果在 Perfetto 中观察到 HW_VSYNC 一直处于开启状态,说明 DispSync 模型始终无法建立足够的精度。可能是显示驱动或 HWC 实现有问题。

### 6.3 用 dumpsys 查看 VSync 配置

```bash
# 查看当前 Phase Offset 配置
adb shell dumpsys SurfaceFlinger | grep phase

# 输出示例:
# app phase: 2333334 ns      SF phase: 6166667 ns
# early app phase: 833334 ns  early SF phase: 6666667 ns
# GL early app phase: 15500001 ns GL early SF phase: 3166667 ns
```

```bash
# 查看 VSync 相关的 HWC 信息
adb shell dumpsys SurfaceFlinger | grep -i vsync
```

`[待补充:Perfetto Trace 截图--VSYNC-app、VSYNC-sf、HW_VSYNC 的典型表现]`

---

## 七、三缓冲(Triple Buffer)

### 7.1 双缓冲的局限

双缓冲配合 VSync 解决了撕裂问题,但引入了一个新问题:如果某一帧的渲染耗时超过一个 VSync 周期,就会发生连续掉帧。

原因在于:当 App 渲染耗时超过一个 VSync 周期时,Back Buffer 被 App 占用无法释放,SurfaceFlinger 无 Buffer 可用,只能等待。下一个 VSync 到来时,SurfaceFlinger 拿到的是刚画完的帧,但此时 App 又没有 Back Buffer 可用来画下一帧--需要等到再下一个 VSync 才能开始。结果是**一次超时渲染导致连续两帧 Jank**。

### 7.2 三缓冲如何缓解

三缓冲在 Front Buffer 和 Back Buffer 之外,增加了第三块缓冲。当 App 渲染超时时,第三块缓冲可以作为新的 Back Buffer 供 App 使用,而不需要等待当前 Back Buffer 被释放。

[图:双缓冲 vs 三缓冲对比--双缓冲下一次超时导致 2 次 Jank,三缓冲下只导致 1 次 Jank]

三缓冲的代价:
- **内存消耗增加**:多一块完整的帧缓冲(1920×1080 RGBA 约需 8MB,4K 分辨率需要约 32MB)
- **输入延迟增加**:多了一个缓冲的队列深度,触摸响应的理论延迟增加一帧

在 Project Butter 之后,Android 默认启用了三缓冲。对于性能优化来说,三缓冲是"安全网"而不是"优化手段"--目标是减少连续 Jank,最优情况仍然是一帧渲染在一个 VSync 周期内完成。

`[已验证: 官方文档, source.android.com/docs/core/graphics/implement-vsync]`

---

## 八、与其他机制的关系

### 8.1 VSync → Choreographer → MainThread/RenderThread

VSync 是整个渲染管线的起点:

1. **VSYNC-app 到来** → Choreographer.doFrame() 被调用
2. **doFrame 依次执行**:Input 回调 → Animation 回调 → Traversal 回调(measure/layout/draw)
3. **主线程完成 draw** → 如果启用了硬件加速,draw 生成 DisplayList 交给 RenderThread
4. **RenderThread 执行 GPU 渲染** → 将结果写入 GraphicBuffer
5. **GraphicBuffer 通过 queueBuffer 提交给 BufferQueue**

这一整条链路都是 VSync 驱动的。理解 VSync 的时序,是理解渲染管线性能的基础。详细流程见 → [2.4 Choreographer 与渲染流水线] 和 → [2.5 MainThread 与 RenderThread 协作]。

### 8.2 VSync → SurfaceFlinger → HWC

1. **VSYNC-sf 到来** → SurfaceFlinger 开始合成
2. **SurfaceFlinger 从各 App 的 BufferQueue 获取已渲染的 GraphicBuffer**
3. **SurfaceFlinger 指示 HWC 进行图层合成**(Overlay 或 GPU 合成)
4. **合成结果通过 Present Fence 确认** → 帧被推送到屏幕

这一路的细节见 → [2.6 SurfaceFlinger 与合成]。

### 8.3 VSync 与 Input 事件

触摸事件从驱动到 App 的传递也需要时间。以 120Hz 采样率的触摸屏为例,中断处理到 App 收到 Input 事件大约需要半个 VSync 周期。如果 App 的 VSYNC-app offset 设置得当,可以让 App 在收到 VSync 时 Input 事件已经到达,从而减少触摸到显示的端到端延迟。

这个主题的深入分析见 → [3.1 Input 事件分发全流程] 和 → [8.1 响应速度原理]。

---

## 九、版本演进

VSync 架构从 Android 4.1 的 Project Butter 确立基本框架以来,经历了从手动配置纳秒值到自适应调优的持续演进。下面我们按时间线梳理关键节点,重点关注每个变化对实际性能分析和 Perfetto 观测的影响。

### 9.1 Android 4.1 (Project Butter)

引入 VSync 同步、Choreographer、三缓冲。这是 Android VSync 架构的起点。

### 9.2 Android 7.0 ~ 10:DispSync 成熟期

DispSync 的软件锁相环模型在这一时期逐渐稳定,成为 Android VSync 虚拟化的标准实现。Phase Offset 通过 `BoardConfig.mk` 中的纳秒值直接配置,OEM 需要根据自己设备的渲染耗时手动调优。这一时期在 Perfetto 中,DispSync 模型行为已经稳定--HW_VSYNC 仅在校正时短暂开启。

### 9.3 Android 11 ~ 12:VsyncConfiguration 引入

开始引入 `VsyncConfiguration` 和 `WorkDuration` 抽象,Phase Offset 的配置方式从手动指定纳秒值演变为基于工作时长自动计算。这意味着 OEM 不再需要凭经验填写纳秒值,而是告诉系统「App 渲染一帧需要多久、SF 合成一帧需要多久」,系统自动计算最优 offset。这个转变为后续的自适应刷新率打下了基础。

### 9.4 Android 13 (T):vsync-appSf 分离

引入 vsync-appSf 信号,将 sf EventThread 的双重职责彻底解耦(详见本文「VSync 信号的传递路径」一节)。在 Perfetto 中，这个变化对应 VSync Track 的拆分——原来单一的 sf EventThread 变成了 sf 和 appSf 两条独立的路径。同时,Android 13 提供了 NDK Choreographer API(API 33+),支持正确的帧节奏(Frame Pacing)和未来帧选择,这对于游戏和视频类应用的帧率控制尤其重要。

### 9.5 Android 15 ~ 16:自适应刷新率(ARR)

Android 15 引入、Android 16 显著增强的**自适应刷新率(Adaptive Refresh Rate, ARR)**从根本上改变了 VSync 的行为模式。

ARR 允许兼容硬件上的显示刷新率通过**离散 VSync 步进(Discrete VSync Steps)**动态调整到内容帧率。例如:

- 60fps 的游戏运行时,刷新率降到 60Hz(VSync 周期变为 16.66ms)
- 24fps 的视频播放时,刷新率可以降到 48Hz 或 24Hz(如果硬件支持)
- 滚动列表时,刷新率升到 120Hz 以获得最大流畅度

这对 VSync 管线的影响是深远的:

1. **VSync 周期不再固定**:DispSync 的 `mPeriod` 需要适应运行时变化的刷新间隔
2. **帧节奏库(Frame Pacing Library)**需要配合变化的时间窗口调整渲染节奏
3. **Choreographer 的调度逻辑**需要处理帧率切换期间的时序过渡

Android 16 新增的 API:
- `hasArrSupport()`:查询设备是否支持 ARR
- `getSuggestedFrameRate(int)`:获取建议的帧率
- RecyclerView 1.4 内置 ARR 支持(fling 和 smooth scroll 自动切换帧率)

实现要求:
- 需要 HWC HAL v3(`android.hardware.graphics.composer3`)
- 需要支持离散 VSync 步进的显示硬件
- 需要内核/系统层的配合变更

`[已验证: 官方文档, developer.android.com/about/versions/16 features + developer.android.com/about/versions/15 features]`

### 9.6 Android 17:消息队列演进对 VSync 的影响

Android 17 的消息队列优化属于 `Looper` / `MessageQueue` 层,不直接影响 SurfaceFlinger 的 VSync 生成机制。它的价值在于减少 `VSYNC-app` 到达应用进程后的排队成本:`DisplayEventReceiver` → `Choreographer` → 主线程消息队列的传递效率提升。

按公开稳定源码 `android-16.0.0_r1` 来看,主线程消息队列已经不是单一实现。`Looper.java` 仍通过 `new MessageQueue(quitAllowed)` 统一入口创建队列,而 `core/java/android/os/CombinedMessageQueue/MessageQueue.java`、`core/java/android/os/ConcurrentMessageQueue/MessageQueue.java`、`core/java/android/os/LegacyMessageQueue/MessageQueue.java` 已经把兼容实现和并发实现拆开了。也就是说,主线程队列的并发化不是凭空冒出来的新概念,公开源码里已经能看到这条演进路线。

这对 VSync 分析意味着两层变化。

第一层,**VSync 的节拍生成没有变**。`EventThread` 仍负责把显示事件送到应用侧,`Choreographer` 仍按 VSync 节拍组织 `doFrame()`。如果 App 错过一帧,我们先看的还是 VSYNC-app 是否按时到达、主线程是否被长任务占住、RenderThread 是否超时,而不是先把问题归因到消息队列实现。

第二层,**主线程排队成本可能下降**。如果消息插入和取出时的锁竞争更少,`VSYNC-app` 到 `doFrame()` 之间的排队抖动理论上会更小,尤其是在多线程频繁 `post()`、动画回调密集或测试工具大量插桩的场景下。这个收益是间接影响,不是"VSync 机制本身变快了"。

截至本次修复,公开材料仍缺两类需要的锚点:一是 Android 17 正式 tag 下最终采用的 MessageQueue 源码路径;二是可公开复核的量化数据来源。因此,这里先不给"掉帧下降 X%""锁竞争下降 Y%"这类数字,也不把它写成已经定案的架构结论。

如果后续要在 Perfetto 里验证这类变化,更值得盯三处时间差:

1. `VSYNC-app` 到 `Choreographer#doFrame` 之间是否更稳定
2. 主线程 `monitor contention` / runnable 排队时间是否下降
3. 多线程频繁 `post()` 时,UI 线程是否更少因为消息队列竞争而错过渲染窗口

`[待验证: Android 17 正式源码公开后,补充 Looper/MessageQueue 的最终路径、targetSdk 生效条件,以及公开可复核的性能数据来源。]`

## 十、可变刷新率下 VSync 行为的变化(扩展)

### 10.1 ARR 如何改变 VSync

在传统架构中,VSync 周期是固定的(如 16.66ms),DispSync 只需要学习一个固定周期即可。但在 ARR 下:

- 刷新率可能在 1Hz 到 120Hz 之间动态切换
- 每次切换意味着 VSync 周期的突变
- DispSync 模型需要快速适应新周期

这要求 DispSync/VsyncTracker 具备快速重新校准的能力。在 Android 15/16 的实现中,刷新率切换时系统会:

首先通知 VsyncConfiguration 更新 VSync 周期参数,然后临时切换到 `early` 配置集(使用更保守的 offset,给予更多缓冲),等新周期稳定后再恢复正常的 Phase Offset。

### 10.2 VSync 偏移量对输入延迟的影响

Phase Offset 直接影响输入到显示的端到端延迟。以 60Hz 设备为例:

| 配置 | App→显示延迟 | 说明 |
|------|-------------|------|
| 无 offset(0,0) | ~3 帧(50ms) | App 和 SF 同时工作,需要等 3 个周期 |
| 典型 offset | ~1.5 帧(25ms) | 流水线化,App 和 SF 工作时间重叠 |
| 激进 offset | ~1 帧(16.66ms) | App 极早开始渲染,但风险高 |

在 120Hz 设备上,同样的流水线优化效果更明显,因为每个 VSync 周期更短(8.33ms),即使增加一个周期的延迟也只有 8.33ms。

`[来源: Cubox收藏, cloud.tencent.com/developer/article/1905184]`

---

## 十一、常见问题与误区

### 常见问题:"VSync 开启就一定流畅"

Android 从 Project Butter 开始始终开启 VSync,但实际效果取决于 Phase Offset、DispSync 模型精度、缓冲策略等参数的综合配置。参数不当可能反而增加延迟。

### 常见问题："三缓冲能彻底解决掉帧"

三缓冲仅能减少连续掉帧的次数（从 2 次降到 1 次），无法消除单帧超时导致的掉帧。如果 App 渲染耗时持续超过 VSync 周期，三缓冲无效。

### 误区 3:"Phase Offset 越小延迟越低"

Offset 过小会导致 App 或 SF 来不及完成工作,错过 VSync 窗口,反而增加延迟。合理的 offset 需要根据实际的渲染耗时和合成耗时来计算。

### 误区 4:"HW_VSYNC 一直开着才准确"

恰恰相反。稳定状态下 HW_VSYNC 应该是关闭的,由 DispSync 软件模型驱动。频繁开启 HW_VSYNC 说明模型不稳定,可能是驱动或 HAL 的问题。

### 误区 5:"120Hz 屏幕不需要 VSync 优化"

120Hz 屏幕的 VSync 周期更短(8.33ms),这意味着 App 和 SF 的工作时间窗口更紧。Phase Offset 的调优在 120Hz 下同样重要,而且对精度的要求更高。

---

## 参考资料

### AOSP 源码
- `frameworks/native/services/surfaceflinger/Scheduler/VSyncPredictor.cpp` - 预测未来的 VSync 时间点
- `frameworks/native/services/surfaceflinger/Scheduler/VSyncReactor.cpp` - 接收 HW_VSYNC / Present Fence 样本并校正预测器
- `frameworks/native/services/surfaceflinger/Scheduler/EventThread.cpp` - 向应用侧分发 VSYNC-app / vsync-appSf
- `frameworks/native/services/surfaceflinger/Scheduler/MessageQueue.cpp` - 向 SurfaceFlinger 自身分发 VSYNC-sf
- `frameworks/native/services/surfaceflinger/Scheduler/VSyncDispatchTimerQueue.cpp` - 按 phase offset 调度 app / sf / appSf 回调
- `frameworks/native/services/surfaceflinger/Scheduler/VsyncConfiguration.cpp` - 根据工作时长计算 phase offset
- `frameworks/base/core/java/android/view/Choreographer.java` - App 侧 VSync 接收与渲染调度
- `frameworks/base/core/java/android/os/Looper.java` - 主线程消息循环入口
- `frameworks/base/core/java/android/os/CombinedMessageQueue/MessageQueue.java` - 兼容实现与并发实现的统一入口
- `frameworks/base/core/java/android/os/ConcurrentMessageQueue/MessageQueue.java` - 并发消息队列实现
- `frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java` - 旧队列实现,便于理解 Android 17 之前后的演进关系

### 官方文档
- [Implement VSync](https://source.android.com/docs/core/graphics/implement-vsync) - Android VSync 架构官方说明
- [Android 16 Features](https://developer.android.com/about/versions/16/features) - ARR 相关 API
- [Android 15 Features](https://developer.android.com/about/versions/15/features) - ARR 初始引入

### 推荐阅读
- [一文带你看懂 Vsync Phase](https://cloud.tencent.com/developer/article/1905184) - Phase Offset 调优实战
- [一文搞定 Android VSync 机制来龙去脉](https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247489959) - VSync 全链路详解
- [Systrace 基础知识 - Vsync 产生与工作机制解读](https://www.androidperformance.com/2019/12/01/Android-Systrace-Vsync/) - 高爷原创
- [Android Perfetto 系列 8:深入理解 Vsync 机制与性能分析](https://androidperformance.com/2025/08/05/Android-Perfetto-08-Vsync/) - 高爷原创
<!-- AIW-源码调研-2026-04-24 -->
## 十二、VSyncPredictor 线性回归算法详解（Android 14+ 源码补充）

前面第三章讲 DispSync 时，关注的是系统"用模型预测 VSync"的整体思路。如果你需要深入到预测算法的具体实现——比如模型怎么从历史样本算出下一次 VSync 时间、异常样本怎么被过滤、VRR 下怎么适应变化的刷新率——下面这部分是对 android-16.0.0_r1 源码的逐段分析，可以作为第三章的源码级对照阅读。


AOSP mainline 的 `VSyncPredictor.cpp`（路径 `services/surfaceflinger/Scheduler/VSyncPredictor.cpp`）实现了基于**简单线性回归**的软件 VSync 周期预测算法，替代了早期 DispSync 使用的简单平均方法。

### 12.1 核心算法

VSyncPredictor 维护一个**环型缓冲区** `mTimestamps`（`kHistorySize=20`），记录最近的硬件 VSync 时间戳。android-13.0.0_r1 至 android-16.0.0_r1 各版本 `VsyncSchedule::createTracker()` 均使用 `kHistorySize=20`、`kDiscardOutlierPercent=20`，未发现"早期版本为 32"或"tolerance 10%"的证据。计算周期时使用线性回归：

```
slope = Σ((X_i - mean(X)) × (Y_i - mean(Y))) / Σ((X_i - mean(X))²)
intercept = mean(Y) - slope × mean(X)
```

其中：
- X = 时间戳序号（ordinal），即第几个 VSync
- Y = VSync 时间戳（纳秒）
- slope ≈ VSync 周期（period）
- intercept ≈ 首个 VSync 时间戳

源码关键片段（VSyncPredictor.cpp 行 110-170）：

```cpp
// This is a 'simple linear regression' calculation of Y over X,
// with Y being the vysnc timestamps, and X being the ordinal of vysnc count.
std::vector<nsecs_t> vyncTS(numSamples);
std::vector<nsecs_t> ordinals(numSamples);

// Normalizing to the oldest timestamp reduces error in calculating the intercept
const auto oldest = *std::min_element(mTimestamps.begin(), mTimestamps.end());
for (size_t i = 0; i < numSamples; i++) {
    const auto timestamp = mTimestamps[i] - oldest;
    vyncTS[i] = timestamp;
    // ordinal = round(vsync_timestamp / current_period × scaling_factor)
    const auto ordinal = currentPeriod == 0
        ? 0
        : (vyncTS[i] + currentPeriod / 2) / currentPeriod * kScalingFactor;
    ordinals[i] = ordinal;
    meanOrdinal += ordinal;
}
```

### 12.2 异常值过滤

新样本进入 `addVsyncTimestamp()` 时,`validate()` 会先把它和当前 `idealPeriod()` 模型比较。源码将 `(timestamp - aValidTimestamp) % idealPeriod()` 转成百分比；结果落在 `20% ~ 80%` 区间时（`kDiscardOutlierPercent=20`），表示样本离最近的理想 VSync 点太远,预测器拒绝这个样本。放宽容差、缩短窗口的策略意图是：容忍小抖动以换取模型稳定性,避免因少数异常样本频繁触发重新学习。

```cpp
// services/surfaceflinger/Scheduler/VSyncPredictor.cpp
// @ AOSP android-16.0.0_r1
const auto percent =
        (timestamp - aValidTimestamp) % idealPeriod() * kMaxPercent / idealPeriod();
if (percent >= kOutlierTolerancePercent &&
    percent <= (kMaxPercent - kOutlierTolerancePercent)) {
    return false;
}
```

`validate()` 还会检查重复时间戳：新时间戳如果离历史样本太近,会被当作 duplicate timestamp 拒绝。被拒绝的样本不会进入 `mTimestamps` 环形缓冲区；学习期样本不足时,预测器会清空时间戳并重新开始学习。样本已经足够时,预测器更新 `mKnownTimestamp`,保留现有时间线,避免单次硬件抖动直接改写后续 `nextAnticipatedVSyncTimeFrom()` 的预测结果。

### 12.3 多帧采样（Android 15+）

`mNumVsyncsPerFrame` 参数支持多帧采样预测，在 android-15.0.0_r1 和 android-16.0.0_r1 的 `VSyncPredictor.h/cpp` 中可见（`numVsyncsPerFrame(displayModePtr)` 路径）；android-14.0.0_r75 中未发现该字段。

```cpp
// VSyncPredictor.h (android-15.0.0_r1 / android-16.0.0_r1)
nsecs_t minFramePeriod() const;
nsecs_t minFramePeriodLocked() const;
// mNumVsyncsForFrame: 在 VRR / 多速率显示模式下，每帧对应的 VSync 数量
```

多帧采样让预测在 VRR 场景下更稳定，减少单帧抖动对周期估计的影响。

### 刷新率切换与 VSyncPredictor 的重新校准

当 SurfaceFlinger 切换显示模式（刷新率变化）时，VSyncPredictor 需要重新校准。android-16.0.0_r1 的调用链：

1. SurfaceFlinger mode/render rate 切换触发 `resyncToHardwareVsync()`
2. `Scheduler::updatePhaseConfiguration()` 更新 phase offset
3. `VsyncModulator::onRefreshRateChangeInitiated()` / `onRefreshRateChangeCompleted()` 控制临时 early 配置与稳定后恢复
4. `VSyncPredictor::setDisplayModePtr()` 更新显示模式；`mNumVsyncsForFrame` 根据 `numVsyncsPerFrame(displayModePtr)` 重新计算
5. ARR discrete VSync steps 按 minFramePeriod 生成不同的 VSync 间隔

在 Perfetto 中，刷新率切换期间 VSync 周期变化和 phase config 切换可以通过 `VsyncTimeline` 轨道和 `SurfaceFlinger` 的 `setVsyncEnabled`/`resyncToHardwareVsync` slice 观察。

### 12.4 VsyncModulator 的三相动态调整

`VsyncModulator`（路径 `services/surfaceflinger/Scheduler/VsyncModulator.h`）根据事务状态、GPU 合成负载和刷新率变化，动态切换 VSync 配置：

默认无事务、无 GPU 合成负载、无刷新率变化时，`getNextVsyncConfigType()` 返回 **Late**——这才是 SurfaceFlinger 的常态配置。其他两种配置是“临时提升”状态，由特定条件触发，持续时间有限。

| 配置类型 | 触发条件 | 设计意图 |
|---------|---------|------------|
| **Early** | 存在 early wakeup request、或 `setTransactionSchedule(EarlyEnd)` 后 `earlyTransactionFrames > 0`、或 `refreshRateChangePending` | 给 App 更早的 VSync 偏移，减少输入延迟 |
| **EarlyGpu** | 近期存在 GPU 合成（`recentComposition > 0`） | 给 GPU 更多时间完成合成 |
| **Late** | 默认状态，无上述条件时回到 | SurfaceFlinger 正常偏移 |

关键参数：

```cpp
// VsyncModulator.h
static constexpr int MIN_EARLY_TRANSACTION_FRAMES = 2;  // 事务后保持 early 偏移的帧数
static constexpr int MIN_EARLY_GPU_FRAMES = 2;          // GPU 合成后保持 early 偏移的帧数
```

当 `onTransactionCommit()` 被调用时，VsyncModulator 的行为是：
1. 记录 `mLastTransactionCommitTime`
2. 把非 Late 的 `mTransactionSchedule` 设回 Late 并调用 `updateVsyncConfig()`
3. 早期帧数消耗发生在 `onDisplayRefresh()` 中——每帧递减 `mEarlyTransactionFrames`，直到归零后回到 Late

换言之，`onTransactionCommit()` 不是“重置 Early 帧数”，而是“提交后退出显式 early schedule”。后续由 `onDisplayRefresh()` 消耗剩余的 early 帧数，逐步过渡回 Late。

### 12.5 VSync 信号生成调用路径

早期 DispSync 资料里的主路径常写成：

```
硬件 VSync 中断
    ↓
HWC omposer → SurfaceFlinger
    ↓
DispSync::addResyncSample()
    ↓
DispSync 计算软件 VSync 模型
    ↓
EventThread 分发 VSYNC-app / VSYNC-sf
```

这条路径适合阅读 Android 4.x 到 Android 10 前后的实现。放到 Android 14+/16 当前 Scheduler 目录时,应按下面的路径核对：

```
HWC VSync 回调 / Present Fence signal
    ↓
SurfaceFlinger Scheduler 采样入口
    ↓
VSyncReactor::addHwVsyncTimestamp() / VSyncReactor::addPresentFence()
    ↓
VSyncPredictor::addVsyncTimestamp() — 校验样本并更新线性回归模型
    ↓
VSyncPredictor::nextAnticipatedVSyncTimeFrom() — 预测下一次 VSync
    ↓
VSyncDispatchTimerQueue — 根据 workDuration / readyDuration / phase 安排回调时间
    ↓
EventThread 分发 VSYNC-app / vsync-appSf；MessageQueue 分发 VSYNC-sf
    ↓
Choreographer#doFrame() / SurfaceFlinger 合成消息
```

VSync Offset 在当前实现中的落点是 `VsyncConfig { workDuration, readyDuration }` 和分发队列的触发时间。它不再表现为一个单独写死的纳秒偏移值；调度器根据预测时间、工作时长和准备时长算出 App 与 SurfaceFlinger 各自的回调时间。
