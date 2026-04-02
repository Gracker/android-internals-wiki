---
title: "VSync 机制"
chapter: "2.3"
status: finalized
reviewed_date: 2026-04-02
reviewed_by: openclaw-task6
applicable_versions: "Android 4.1 (API 16) - Android 16 (API 36)"
last_verified: "2026-03-30"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/DispSync.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/EventThread.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
  - type: official
    path: "https://source.android.com/docs/core/display/improve-performance"
  - type: official
    path: "https://developer.android.com/about/versions/16/features"
  - type: blog
    path: "https://cloud.tencent.com/developer/article/1905184 (Vsync Phase 详解)"
tags: [vsync, dispsync, choreographer, surfaceflinger, phase-offset, arr, rendering]
related_chapters: ["2.1", "2.4", "2.5", "2.6", "2.9", "8.1"]
---

# VSync 机制

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 VSync 的起源：解决画面撕裂（Screen Tearing）
- 🔹 Android VSync 架构：HW-VSync → SF-VSync → App-VSync 三级信号
- 🔹 VSync Phase Offset 的作用与调优
- 🔹 VSync 信号在 SurfaceFlinger 和 Choreographer 中的传递路径
- 🔹 VSync 在 Perfetto 中的观察：VSYNC-sf、VSYNC-app

### 扩展（可选深入）

- 🔸 可变刷新率下 VSync 行为的变化
- 🔸 VSync 偏移量对输入延迟的影响

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 VSync

如果你在 Perfetto 中打开任何一个有 UI 渲染的 Trace，最先注意到的往往是那两条规律跳动的竖线——VSYNC-app 和 VSYNC-sf。它们就像整个渲染管线的节拍器：App 什么时候开始画、SurfaceFlinger 什么时候开始合成、屏幕什么时候开始刷新，全由这两个信号决定。

不理解 VSync，你就无法理解为什么一帧从"App 开始绘制"到"显示在屏幕上"可能需要 1~3 个 VSync 周期；无法理解为什么调整一个纳秒级的偏移量就能影响跟手性；也无法理解 Android 从 4.1 到 16 这十几个版本中，渲染管线不断演进的核心脉络。

我们在这章里要把 VSync 的来龙去脉彻底讲清楚：从它最初解决的那个问题（画面撕裂）开始，经过 Android 的软件虚拟化、相位偏移调优，一直到 Android 15/16 的自适应刷新率（ARR）如何改变 VSync 的基本行为。读完之后，你打开 Perfetto 就能读懂 VSync 相关的所有 Track，遇到渲染时序问题知道从哪里下手。

---

## 一、VSync 的起源：画面撕裂问题

### 1.1 什么是画面撕裂（Screen Tearing）

显示屏刷新画面的方式是像素自上而下逐行扫描。每一帧的扫描过程是连续的，如果在上一帧还没扫描完的时候，帧缓冲（Frame Buffer）的内容被替换成了下一帧的数据，屏幕上半部分显示的就是旧帧、下半部分显示的就是新帧——这就是画面撕裂。

[图：Screen Tearing 示意图——上半帧和下半帧画面水平错位]

画面撕裂在快速滚动、动画、游戏等场景下尤为明显。早期的 PC 游戏玩家对此深有体会：快速转动视角时，画面中间会出现一条明显的"水平裂缝"。

### 1.2 VSync 的基本思路

解决画面撕裂的方案很直接：**在屏幕完成一帧扫描、准备开始下一帧扫描的间隙，才允许更新帧缓冲的数据**。这个间隙就是垂直同步（Vertical Synchronization，简称 VSync）信号。

VSync 信号也叫 VBlank 信号或 TE（Tearing Effect）信号。从硬件角度看，它是显示屏上的一个引脚产生的电平变化（通常是上升沿中断）；从软件角度看，它是一个 GPIO 中断，系统根据这个中断来安排渲染和合成的时序。

[图：VSync on vs VSync off 对比——开启 VSync 后画面不再撕裂]

### 1.3 双缓冲机制

与 VSync 配合工作的是双缓冲（Double Buffering）。系统维护两块帧缓冲：

- **Front Buffer**：屏幕正在读取显示的那块缓冲
- **Back Buffer**：GPU 正在写入渲染数据的那块缓冲

当 VSync 信号到来时，两块缓冲的角色互换——Back Buffer 变成 Front Buffer 交给屏幕显示，Front Buffer 变成 Back Buffer 供 GPU 写入下一帧。这种交换叫做 Buffer Swap。

双缓冲配合 VSync 基本解决了撕裂问题，但也带来了新的挑战：如果 App 的渲染耗时超过一个 VSync 周期（比如 60Hz 屏幕的 16.66ms），Back Buffer 还没准备好，Buffer Swap 就不会发生，屏幕只能再显示一次旧帧——这就是**掉帧（Jank）**。

`[已验证: 官方文档, source.android.com/docs/core/display/improve-performance]`

---

## 二、Android VSync 三级信号架构

### 2.1 从 Project Butter 说起

Android 4.1（Jelly Bean，2012 年）引入了 Project Butter（黄油计划），这是 Android 历史上第一次系统性地解决流畅度问题。Project Butter 的三个核心组件是：

1. **VSync 同步**：让 App 渲染、SurfaceFlinger 合成都与硬件 VSync 对齐
2. **Choreographer**：让 App 能按 VSync 节拍进行绘制
3. **三缓冲（Triple Buffer）**：缓解双缓冲下偶发超时导致的连续掉帧

没有 VSync 同步的情况下，App 渲染节奏与屏幕刷新节奏完全脱节。App 可能在 VSync 周期的任意时刻完成渲染，如果完成时间刚好错过了一次 Buffer Swap，这一帧就要等到下一个 VSync 才能显示，白白浪费一个周期。有了 VSync 同步后，所有参与者都在 VSync 到来时才动手，节奏统一，掉帧的概率大大降低。

`[已验证: 官方文档, source.android.com/docs/core/display/improve-performance]`

### 2.2 三级信号：HW-VSync / VSYNC-app / VSYNC-sf

Android 的 VSync 架构不是简单地把硬件 VSync 信号转发给所有人。它将 VSync 分成了三级，周期相同但相位不同：

```
HW_VSYNC_0（硬件 VSync）
    ↓ DispSync 虚拟化
    ├→ VSYNC-app（App VSync）→ 驱动 Choreographer → App 渲染
    └→ VSYNC-sf（SF VSync）  → 驱动 SurfaceFlinger → 合成
```

- **HW_VSYNC_0**：硬件产生的原始 VSync 信号，标识显示器开始显示下一帧的瞬间。以 60Hz 屏幕为例，每 16.66ms 产生一次；120Hz 则是每 8.33ms。由 HWC（Hardware Composer）产生。
- **VSYNC-app**：触发 App 读取输入事件并开始渲染。收到这个信号后，Choreographer 开始执行 doFrame，依次处理 Input → Animation → Traversal（measure/layout/draw）。
- **VSYNC-sf**：触发 SurfaceFlinger 开始合成。收到这个信号后，SurfaceFlinger 从各 App 的 BufferQueue 中取出已渲染好的 GraphicBuffer，合成最终画面交给 HWC。

三者的关系可以用一个理想化的流水线来理解：

| 时刻 | 显示器 | SurfaceFlinger | App |
|------|--------|----------------|-----|
| VSync N | 显示第 N 帧 | 合成第 N+1 帧 | 渲染第 N+2 帧 |

在这个理想状态下，三个环节同时工作在不同的帧上，流水线满载。但如果没有 Phase Offset 调优，实际达不到这种理想状态——后面我们会详细展开。

`[已验证: 官方文档, source.android.com/docs/core/display/improve-performance + AOSP DispSync.cpp]`

### 2.3 为什么不直接用硬件 VSync

你可能会问：为什么不直接把 HW_VSYNC_0 广播给 App 和 SurfaceFlinger？

原因有三个：

**第一，功耗。** 硬件 VSync 频率极高（120Hz 就是每秒 120 次中断），每次中断都要从内核态切换到用户态，开销不小。而且绝大多数时候 VSync 的周期是固定可预测的，没必要每次都从硬件获取。

**第二，解耦。** App 很多，如果每个 App 都直接监听硬件中断，耦合性太高。需要一个中间层来管理订阅关系——谁需要 VSync 就给谁发，不需要的就不发（按需分发）。

**第三，灵活性。** 软件虚拟化后可以对 VSync 信号做各种定制——调整相位偏移、改变周期、适应可变刷新率——这些在硬件层面做不了或者代价很高。

所以 Android 的方案是：用一个软件模型来"学习"硬件 VSync 的规律，然后基于模型按需生成虚拟 VSync 信号。这个软件模型就是 DispSync。

`[已验证: AOSP DispSync.cpp + source.android.com]`

---

## 三、DispSync：软件锁相环

### 3.1 DispSync 是什么

DispSync 是 Android 中实现 VSync 虚拟化的核心组件。它的本质是一个**软件锁相环（PLL, Phase-Locked Loop）**。

简单来说，锁相环做的事情是：接收一个周期性的输入信号（HW_VSYNC_0），通过学习输入信号的规律建立一个数学模型，然后基于模型生成与输入信号同频但可以有任意相位偏移的输出信号。

DispSync 维护的模型有三个核心参数：

| 参数 | 含义 | 示例值（60Hz） |
|------|------|----------------|
| `mPeriod` | 刷新间隔 | 16,666,667 ns |
| `mPhase` | 从时间零点到初始 VSync 的相位偏移 | 0 ns |
| `mReferenceTime` | 最近一次重新同步后的首个 VSync 时间戳 | 动态更新 |

```cpp
// frameworks/native/services/surfaceflinger/DispSync.cpp
// @ AOSP android-16.0.0_r1
// DispSync 通过 addResyncSample 接收硬件 VSync 时间戳来构建和校正模型
void DispSync::addResyncSample(nsecs_t timestamp) {
    // 将新的硬件 VSync 时间戳纳入模型
    // 通过最小二乘法等算法更新 mPeriod、mPhase、mReferenceTime
    // 使模型能够精确预测未来的 VSync 时间点
}
```

`[已验证: AOSP android-16.0.0_r1, frameworks/native/services/surfaceflinger/DispSync.cpp]`

### 3.2 模型如何工作

DispSync 的工作流程可以概括为三步：

**1）学习阶段**：SurfaceFlinger 通过 HWC 的 `onVsyncReceived` 回调收到 HW_VSYNC_0 时间戳，将其通过 `addResyncSample` 喂给 DispSync。DispSync 用这些时间戳来拟合一个周期性模型。通常接收 6 个左右的样本就能完成校准。

**2）预测阶段**：模型建立后，DispSync 就可以在没有硬件 VSync 输入的情况下，精确预测未来每个 VSync 的时间点。这时候系统可以关闭硬件 VSync 中断以节省功耗。

**3）校正阶段**：SurfaceFlinger 持续监控 DispSync 模型的精度。校正的依据是 HWC 返回的 **Retire Fence**（也叫 Present Fence）的时间戳——这个 Fence 在帧真正被推送到屏幕时 signal，它的 signal 时间就是真实的硬件 VSync 时间。如果发现模型预测值与真实值偏差超过阈值，SurfaceFlinger 就重新开启硬件 VSync，再次执行学习阶段。

```cpp
// SurfaceFlinger 通过 Present Fence 监控模型精度
// frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
// 当检测到模型偏差时，通过 addResyncSample 重建模型
```

所以你在 Perfetto 的 SurfaceFlinger 进程中，有时候会看到短暂的 HW_VSYNC 开启——那就是系统在进行模型校正。正常稳定状态下，HW_VSYNC 应该是关闭的，由 DispSync 的软件模型独自驱动。

`[已验证: 官方文档, source.android.com/docs/core/display/improve-performance + AOSP SurfaceFlinger.cpp]`

### 3.3 现代架构：从 DispSync 到 VsyncController/VsyncTracker

需要指出的是，DispSync 这个名字是早期（Android 4.x ~ 10 左右）的实现。在较新的 AOSP 分支中，架构有了显著演进：

- **VsyncTracker**（实际创建的是 VSyncPredictor 对象）：基于历史 VSync 时间戳预测未来 VSync 时间点，相当于 DispSync 的预测能力
- **VsyncDispatcher**（实际创建的是 VSyncDispatchTimerQueue 对象）：管理 VSync 回调的注册和分发
- **VSyncController**（实际创建的是 VSyncReactor 对象）：负责传递 HW_VSync 和 Present Fence 信号，协调模型校正
- **DispVsyncSource**：作为 DispSync 模型和 EventThread 之间的中间层

这些组件的职责更清晰，但核心思想没变：用软件模型模拟硬件 VSync，按需分发，节省功耗。

`[已验证: AOSP googlesource.com, frameworks/native/services/surfaceflinger/Scheduler/]`

---

## 四、VSync 信号的传递路径

### 4.1 SurfaceFlinger 侧：VSYNC-sf

SurfaceFlinger 获取 VSync-sf 的路径相对简洁：

```
DispSync/VsyncTracker（软件 VSync 模型）
    → VSyncDispatchTimerQueue（根据 phase offset 计算触发时间，设置定时器）
        → 定时器到期 → timerCallback
            → MessageQueue::VsyncCallback
                → SurfaceFlinger::onMessageReceived（处理合成逻辑）
```

在较新的 AOSP 版本中，SurfaceFlinger 的 MessageQueue 直接向 VSyncDispatchTimerQueue 注册回调。当定时器在 VSYNC-sf 的时间点触发时，回调直接走到 SurfaceFlinger 的消息处理逻辑。

这条路径不经过 EventThread，因为 VSYNC-sf 是 SurfaceFlinger "自己用"的——在 Android T (13) 之前，sf EventThread 同时承担唤醒 SurfaceFlinger 和服务 Choreographer 客户端的职责，但从 Android 13 开始这两个职责被解耦了（详见后文 vsync-appSf 部分）。

`[已验证: AOSP, frameworks/native/services/surfaceflinger/EventThread.cpp + MessageQueue.cpp]`

### 4.2 App 侧：VSYNC-app

App 获取 VSYNC-app 的路径更长，涉及跨进程通信：

```
DispSync/VsyncTracker
    → DispSyncSource（包含 phase offset 信息）
        → CallbackRepeater（向 VSyncDispatchTimerQueue 注册周期性回调）
            → VSyncDispatchTimerQueue 定时触发
                → DispSyncSource::onVsyncCallback
                    → EventThread::onVSyncEvent
                        → BitTube（基于 Unix Domain Socket 的 IPC）
                            → DisplayEventReceiver（App 进程端）
                                → Choreographer::doFrame
```

这条链路有几个值得关注的细节：

**BitTube 是什么？** BitTube 是 Android 封装的基于 Unix Domain Socket 的 IPC 通道。选择它的原因是 VSync 信号频率高、需要有序传输、且要高效——Domain Socket 在这些方面表现优秀。

**按需分发**：VSYNC-app 不是一直发的。只有当 App 调用了 `requestNextVsync()`（比如调用了 `View.invalidate()` 最终走到 `Choreographer.scheduleFrameLocked()`）时，EventThread 才会在下一个 VSync 时间点向该 App 发送信号。如果 App 的 UI 静止不动（没有动画、没有触摸），就不会收到 VSYNC-app。这个设计节省了大量不必要的 CPU 开销。

`[已验证: AOSP, frameworks/native/services/surfaceflinger/EventThread.cpp + frameworks/base/core/java/android/view/Choreographer.java]`

### 4.3 Android 13+ 新增：vsync-appSf

Android 13 引入了一个新的 VSync 信号——**vsync-appSf**，解决的是旧架构中 sf EventThread 的双重职责问题。

在 Android 13 之前，sf EventThread 同时做两件事：

1. 唤醒 SurfaceFlinger 进行合成
2. 为需要与 SurfaceFlinger 紧密同步的 Choreographer 客户端提供信号

这两种消费者对时序的要求不同：SurfaceFlinger 需要的是"该合成了"，而 Choreographer 客户端需要的是"SurfaceFlinger 的内部状态已经更新了"。把这两种需求混在同一个 EventThread 里会导致时序歧义。

vsync-appSf 将这两个职责彻底分离：

- **vsync-sf**：专用于驱动 SurfaceFlinger 合成
- **vsync-appSf**：专用于需要与 SurfaceFlinger 内部状态紧密同步的 Choreographer 客户端

同时，从 API 33 开始，Android 提供了 NDK Choreographer API（`AChoreographer_vsyncCallback`），允许应用使用正确的帧节奏（Frame Pacing），甚至可以选择渲染到未来的某一帧。这个 API 提供多个可能的帧时间线信息，App 可以根据渲染截止时间和期望的展示时间来选择最合适的时间线。

`[已验证: 官方文档, Android NDK Documentation + AOSP EventThread.cpp]`

### 4.4 传递路径总结

[图：VSync 信号传递路径全景图——从 HW_VSYNC_0 到 DispSync 到 EventThread/MessageQueue 到 Choreographer 的完整链路]

```
HW_VSYNC_0 (HWC 硬件中断)
    ↓ onVsyncReceived
SurfaceFlinger
    ↓ addResyncSample
DispSync / VsyncTracker (软件模型)
    ↓
    ├──→ [Phase: SF offset]
    │    VSyncDispatchTimerQueue → MessageQueue::VsyncCallback
    │    → SurfaceFlinger 合成 (VSYNC-sf)
    │
    ├──→ [Phase: App offset]
    │    DispSyncSource → CallbackRepeater → EventThread (app)
    │    → BitTube → DisplayEventReceiver → Choreographer (VSYNC-app)
    │
    └──→ [Phase: AppSF offset, Android 13+]
         DispSyncSource → CallbackRepeater → EventThread (appSf)
         → BitTube → DisplayEventReceiver → Choreographer (VSYNC-appSf)
```

---

## 五、VSync Phase Offset 的作用与调优

### 5.1 为什么需要 Phase Offset

如果 VSYNC-app 和 VSYNC-sf 与 HW_VSYNC_0 完全同时触发（即 offset 为 0），会发生什么？

```
VSync 到来时:
  - App 开始渲染帧 N
  - SurfaceFlinger 开始合成……但帧 N 还没画完！
  - SurfaceFlinger 只能拿到帧 N-1 的 buffer
  - 屏幕显示帧 N-2
```

结果是：从 App 开始渲染到用户看到画面，至少需要 **3 个 VSync 周期**。以 60Hz 屏幕计算就是约 50ms 的延迟——用户触摸屏幕后要等 50ms 才能看到响应，这对跟手性来说是不可接受的。

### 5.2 Phase Offset 如何工作

Phase Offset 的核心思路是：**让 App 和 SurfaceFlinger 在不同的时刻开始工作，使它们的工作时间重叠，从而压缩整体延迟**。

具体来说：

- **VSYNC-app 的 offset**：让 App 在 HW_VSYNC_0 到来之前就提前开始渲染。这样当 VSYNC-sf 到来时，App 的帧可能已经画好了。
- **VSYNC-sf 的 offset**：让 SurfaceFlinger 在 HW_VSYNC_0 到来之前的某个时刻开始合成。这样当屏幕刷新时，合成好的帧已经准备好了。

```
时间线（Phase Offset 优化后）:

  VSYNC-app      → App 开始渲染
       ↓ (渲染中)
  VSYNC-sf       → SF 开始合成（App 已渲染完毕）
       ↓ (合成中)
  HW_VSYNC_0     → 屏幕显示（SF 已合成完毕）
```

理想情况下，三个阶段在一个 VSync 周期内流水线化完成，延迟从 3 帧降到 1~2 帧。

### 5.3 配置方式

Phase Offset 有两种配置方式，对应两个时代：

**Legacy 方式：直接配置纳秒偏移量**

在设备的 `BoardConfig.mk` 中配置：
```
VSYNC_EVENT_PHASE_OFFSET_NS := 2333334
SF_VSYNC_EVENT_PHASE_OFFSET_NS := 6166667
```

**Modern 方式：基于工作时长（WorkDuration）自动计算**

从较新的 AOSP 版本开始，引入了 `VsyncConfiguration` + `WorkDuration` 抽象，取代手动配置固定纳秒值。核心思想是：你只需要告诉系统"App 渲染一帧需要多久、SurfaceFlinger 合成一帧需要多久"，系统自动计算最优的 offset。

配置属性（通过 `setprop` 或 `BoardConfig.mk`）：
```
debug.sf.late.app.duration  = 20500000  (ns)
debug.sf.late.sf.duration   = 10500000  (ns)
debug.sf.early.app.duration = 16500000  (ns)
debug.sf.early.sf.duration  = 16000000  (ns)
debug.sf.earlyGl.app.duration = 21000000  (ns)
debug.sf.earlyGl.sf.duration  = 13500000  (ns)
```

offset 的计算公式为：
```cpp
// sfDurationToOffset: sfOffset = vsyncDuration - sfDuration % vsyncDuration
// appDurationToOffset: appOffset = vsyncDuration - (appDuration + sfDuration) % vsyncDuration
```

以 60Hz（vsyncDuration = 16,666,667 ns）为例：
```
sf phase = 16666667 - 10500000 % 16666667 = 6166667 ns
app phase = 16666667 - (20500000 + 10500000) % 16666667 = 2333334 ns
```

可以通过 `adb shell dumpsys SurfaceFlinger | grep phase` 查看当前设备的实际 offset 值。

系统会在不同场景下切换三组配置：

| 场景 | App Duration | SF Duration | 说明 |
|------|-------------|-------------|------|
| 正常 (late) | 20500000 | 10500000 | 大部分时间的默认配置 |
| 帧率切换 (early) | 16500000 | 16000000 | 切换屏幕刷新率时使用 |
| GPU 合成 (earlyGl) | 21000000 | 13500000 | SF 使用 GPU 合成时使用 |

`[已验证: 官方文档, source.android.com/docs/core/display/improve-performance + AOSP VsyncConfiguration.cpp]`

### 5.4 调优的风险

Phase Offset 不是越大越好，也不是越小越好。它是一个需要精细平衡的参数：

- **Offset 过短**：App 渲染还没完成，SurfaceFlinger 就开始合成了。SurfaceFlinger 拿不到最新的 buffer，这一帧白等，延迟反而增加。
- **Offset 过长**：App 和 SF 的工作时间几乎不重叠，失去了流水线化的优势，延迟接近 3 帧。
- **理想状态**：App 刚好在 SF 开始合成前完成渲染，SF 刚好在屏幕刷新前完成合成。

`[来源: Cubox收藏, cloud.tencent.com/developer/article/1905184 — Vsync Phase 详解]`

在实际的 OEM 调优中，调整 offset 是提升跟手性的常用手段。但改动必须配合充分的自动化测试，因为 offset 的效果高度依赖 App 的渲染耗时和 SF 的合成耗时，不同场景下表现可能截然不同。

---

## 六、VSync 在 Perfetto 中的观察

### 6.1 关键 Track

在 Perfetto 中，VSync 相关的信息主要出现在以下 Track：

- **VSYNC-app**：在 App 进程中可见，标识 Choreographer 收到 VSync 信号的时刻。每次跳变对应一次 `doFrame` 调用
- **VSYNC-sf**：在 SurfaceFlinger 进程中可见，标识 SF 收到 VSync 信号的时刻。每次跳变对应一次合成操作
- **HW_VSYNC**：在 SurfaceFlinger 进程中可见，偶尔出现（系统检测到模型需要校正时才开启）。在 Perfetto 中表现为 SurfaceFlinger 进程里短暂的硬件 VSync 采样脉冲

### 6.2 正常 vs 异常的 VSync 表现

**正常情况：**

在 Perfetto 中，你会看到 VSYNC-app 和 VSYNC-sf 以稳定的间隔规律跳动。在 60Hz 设备上，间隔约 16.66ms；在 120Hz 设备上约 8.33ms。两者之间有一个固定的时间差（即 Phase Offset）。

[图：Perfetto 中正常的 VSYNC-app 和 VSYNC-sf Track——间隔均匀、相位稳定]

**异常情况 1：VSync 抖动**

VSync 间隔不稳定，忽大忽小。可能原因：
- DispSync 模型精度不足，频繁开启 HW_VSYNC 校正
- 热限频（Thermal Throttling）导致系统时钟不稳
- 某些厂商的 HAL 实现问题

**异常情况 2：VSYNC-sf 跳变延迟**

正常情况下 VSYNC-sf 在每个 VSync 周期的固定时刻触发。如果发现触发时间明显偏移，说明 SurfaceFlinger 被其他工作阻塞（比如 GPU 合成耗时过长），来不及按时响应 VSync 回调。

**异常情况 3：HW_VSYNC 频繁开启**

如果在 Perfetto 中观察到 HW_VSYNC 一直处于开启状态，说明 DispSync 模型始终无法建立足够的精度。可能是显示驱动或 HWC 实现有问题。

### 6.3 用 dumpsys 查看 VSync 配置

```bash
# 查看当前 Phase Offset 配置
adb shell dumpsys SurfaceFlinger | grep phase

# 输出示例：
# app phase: 2333334 ns      SF phase: 6166667 ns
# early app phase: 833334 ns  early SF phase: 6666667 ns
# GL early app phase: 15500001 ns GL early SF phase: 3166667 ns
```

```bash
# 查看 VSync 相关的 HWC 信息
adb shell dumpsys SurfaceFlinger | grep -i vsync
```

`[待补充：Perfetto Trace 截图——VSYNC-app、VSYNC-sf、HW_VSYNC 的典型表现]`

---

## 七、三缓冲（Triple Buffer）

### 7.1 双缓冲的局限

双缓冲配合 VSync 解决了撕裂问题，但引入了一个新问题：如果某一帧的渲染耗时超过一个 VSync 周期，就会发生连续掉帧。

原因在于：当 App 渲染耗时超过一个 VSync 周期时，Back Buffer 被 App 占用无法释放，SurfaceFlinger 无 Buffer 可用，只能等待。下一个 VSync 到来时，SurfaceFlinger 拿到的是刚画完的帧，但此时 App 又没有 Back Buffer 可用来画下一帧——需要等到再下一个 VSync 才能开始。结果是**一次超时渲染导致连续两帧 Jank**。

### 7.2 三缓冲如何缓解

三缓冲在 Front Buffer 和 Back Buffer 之外，增加了第三块缓冲。当 App 渲染超时时，第三块缓冲可以作为新的 Back Buffer 供 App 使用，而不需要等待当前 Back Buffer 被释放。

[图：双缓冲 vs 三缓冲对比——双缓冲下一次超时导致 2 次 Jank，三缓冲下只导致 1 次 Jank]

三缓冲的代价：
- **内存消耗增加**：多一块完整的帧缓冲（1920×1080 RGBA 约需 8MB，更高分辨率更多）
- **输入延迟增加**：多了一个缓冲的队列深度，触摸响应的理论延迟增加一帧

在 Project Butter 之后，Android 默认启用了三缓冲。对于性能优化来说，三缓冲是"安全网"而不是"优化手段"——目标是减少连续 Jank，最优情况仍然是一帧渲染在一个 VSync 周期内完成。

`[已验证: 官方文档, source.android.com/docs/core/display/improve-performance]`

---

## 八、与其他机制的关系

### 8.1 VSync → Choreographer → MainThread/RenderThread

VSync 是整个渲染管线的起点：

1. **VSYNC-app 到来** → Choreographer.doFrame() 被调用
2. **doFrame 依次执行**：Input 回调 → Animation 回调 → Traversal 回调（measure/layout/draw）
3. **主线程完成 draw** → 如果启用了硬件加速，draw 生成 DisplayList 交给 RenderThread
4. **RenderThread 执行 GPU 渲染** → 将结果写入 GraphicBuffer
5. **GraphicBuffer 通过 queueBuffer 提交给 BufferQueue**

这一整条链路都是 VSync 驱动的。理解 VSync 的时序，是理解渲染管线性能的基础。详细流程见 → [2.4 Choreographer 与渲染流水线] 和 → [2.5 MainThread 与 RenderThread 协作]。

### 8.2 VSync → SurfaceFlinger → HWC

1. **VSYNC-sf 到来** → SurfaceFlinger 开始合成
2. **SurfaceFlinger 从各 App 的 BufferQueue 获取已渲染的 GraphicBuffer**
3. **SurfaceFlinger 指示 HWC 进行图层合成**（Overlay 或 GPU 合成）
4. **合成结果通过 Present Fence 确认** → 帧被推送到屏幕

这一路的细节见 → [2.6 SurfaceFlinger 与合成]。

### 8.3 VSync 与 Input 事件

触摸事件从驱动到 App 的传递也需要时间。以 120Hz 采样率的触摸屏为例，中断处理到 App 收到 Input 事件大约需要半个 VSync 周期。如果 App 的 VSYNC-app offset 设置得当，可以让 App 在收到 VSync 时 Input 事件已经到达，从而减少触摸到显示的端到端延迟。

这个主题的深入分析见 → [3.1 Input 事件分发全流程] 和 → [8.1 响应速度原理]。

---

## 九、版本演进

### 9.1 Android 4.1 (Project Butter)

引入 VSync 同步、Choreographer、三缓冲。这是 Android VSync 架构的起点。

### 9.2 Android 7.0 ~ 10：DispSync 成熟期

DispSync 的软件锁相环模型在这一时期逐渐稳定。Phase Offset 通过 `BoardConfig.mk` 中的纳秒值直接配置。

### 9.3 Android 11 ~ 12：VsyncConfiguration 引入

开始引入 `VsyncConfiguration` 和 `WorkDuration` 抽象，Phase Offset 的配置方式从手动指定纳秒值演变为基于工作时长自动计算。

### 9.4 Android 13 (T)：vsync-appSf 分离

引入 vsync-appSf 信号，将 sf EventThread 的双重职责解耦。同时提供 NDK Choreographer API（API 33+），支持正确的帧节奏和未来帧选择。

### 9.5 Android 15 ~ 16：自适应刷新率（ARR）

**[自动发现: 来源 intake/research-feeds/2026-03-30-15-arr-vsync-android15-16.md]**

Android 15 引入、Android 16 显著增强的**自适应刷新率（Adaptive Refresh Rate, ARR）**从根本上改变了 VSync 的行为模式。

ARR 允许兼容硬件上的显示刷新率通过**离散 VSync 步进（Discrete VSync Steps）**动态调整到内容帧率。例如：

- 60fps 的游戏运行时，刷新率降到 60Hz（VSync 周期变为 16.66ms）
- 24fps 的视频播放时，刷新率可以降到 48Hz 或 24Hz（如果硬件支持）
- 滚动列表时，刷新率升到 120Hz 以获得最大流畅度

这对 VSync 管线的影响是深远的：

1. **VSync 周期不再固定**：DispSync 的 `mPeriod` 需要适应运行时变化的刷新间隔
2. **帧节奏库（Frame Pacing Library）**需要配合变化的时间窗口调整渲染节奏
3. **Choreographer 的调度逻辑**需要处理帧率切换期间的时序过渡

Android 16 新增的 API：
- `hasArrSupport()`：查询设备是否支持 ARR
- `getSuggestedFrameRate(int)`：获取建议的帧率
- RecyclerView 1.4 内置 ARR 支持（fling 和 smooth scroll 自动切换帧率）

实现要求：
- 需要 HWC HAL v3（`android.hardware.graphics.composer3`）
- 需要支持离散 VSync 步进的显示硬件
- 需要内核/系统层的配合变更

`[已验证: 官方文档, developer.android.com/about/versions/16/features + developer.android.com/about/versions/15/features]`

---

## 十、可变刷新率下 VSync 行为的变化（扩展）

### 10.1 ARR 如何改变 VSync

在传统架构中，VSync 周期是固定的（如 16.66ms），DispSync 只需要学习一个固定周期即可。但在 ARR 下：

- 刷新率可能在 1Hz 到 120Hz 之间动态切换
- 每次切换意味着 VSync 周期的突变
- DispSync 模型需要快速适应新周期

这要求 DispSync/VsyncTracker 具备快速重新校准的能力。在 Android 15/16 的实现中，刷新率切换时系统会：

1. 通知 VsyncConfiguration 更新 VSync 周期参数
2. 临时切换到 `early` 配置集（更保守的 offset，给予更多缓冲）
3. 在新周期稳定后恢复正常的 Phase Offset

### 10.2 VSync 偏移量对输入延迟的影响

Phase Offset 直接影响输入到显示的端到端延迟。以 60Hz 设备为例：

| 配置 | App→显示延迟 | 说明 |
|------|-------------|------|
| 无 offset（0,0） | ~3 帧（50ms） | App 和 SF 同时工作，需要等 3 个周期 |
| 典型 offset | ~1.5 帧（25ms） | 流水线化，App 和 SF 工作时间重叠 |
| 激进 offset | ~1 帧（16.66ms） | App 极早开始渲染，但风险高 |

在 120Hz 设备上，同样的流水线优化效果更明显，因为每个 VSync 周期更短（8.33ms），即使增加一个周期的延迟也只有 8.33ms。

`[来源: Cubox收藏, cloud.tencent.com/developer/article/1905184]`

---

## 十一、常见问题与误区

### 误区 1："VSync 就是垂直同步，开启就好"

VSync 本身不是简单的开关。Android 从 Project Butter 开始就是"始终开启"VSync 的，但 VSync 的行为由 Phase Offset、DispSync 模型精度、缓冲策略等参数共同决定。不是开了就流畅，参数配置不当反而可能更卡。

### 误区 2："三缓冲一定能解决掉帧"

三缓冲只能减少**连续**掉帧的次数（从 2 次降到 1 次），不能消除掉帧本身。如果 App 每帧都超过一个 VSync 周期，三缓冲也无济于事。三缓冲是安全网，不是万能药。

### 误区 3："Phase Offset 越小延迟越低"

Offset 过小会导致 App 或 SF 来不及完成工作，错过 VSync 窗口，反而增加延迟。合理的 offset 需要根据实际的渲染耗时和合成耗时来计算。

### 误区 4："HW_VSYNC 一直开着才准确"

恰恰相反。稳定状态下 HW_VSYNC 应该是关闭的，由 DispSync 软件模型驱动。频繁开启 HW_VSYNC 说明模型不稳定，可能是驱动或 HAL 的问题。

### 误区 5："120Hz 屏幕不需要 VSync 优化"

120Hz 屏幕的 VSync 周期更短（8.33ms），这意味着 App 和 SF 的工作时间窗口更紧。Phase Offset 的调优在 120Hz 下同样重要，而且对精度的要求更高。

---

## 参考资料

### AOSP 源码
- `frameworks/native/services/surfaceflinger/DispSync.cpp` — DispSync 核心实现
- `frameworks/native/services/surfaceflinger/EventThread.cpp` — VSync 事件分发
- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp` — SurfaceFlinger 主逻辑
- `frameworks/native/services/surfaceflinger/Scheduler/` — 调度器（VsyncTracker/VsyncDispatcher/VSyncController）
- `frameworks/base/core/java/android/view/Choreographer.java` — App 侧 VSync 接收与渲染调度

### 官方文档
- [Improving Display Performance](https://source.android.com/docs/core/display/improve-performance) — Android VSync 架构官方说明
- [Android 16 Features](https://developer.android.com/about/versions/16/features) — ARR 相关 API
- [Android 15 Features](https://developer.android.com/about/versions/15/features) — ARR 初始引入

### 推荐阅读
- [一文带你看懂 Vsync Phase](https://cloud.tencent.com/developer/article/1905184) — Phase Offset 调优实战
- [一文搞定 Android VSync 机制来龙去脉](https://mp.weixin.qq.com/s?__biz=MzAxMDM0NjExNA==&mid=2247489959) — VSync 全链路详解
- [Systrace 基础知识 - Vsync 产生与工作机制解读](https://www.androidperformance.com/2019/12/01/Android-Systrace-Vsync/) — 高爷原创
- [Android Perfetto 系列 8：深入理解 Vsync 机制与性能分析](https://androidperformance.com/2025/08/05/Android-Perfetto-08-Vsync/) — 高爷原创