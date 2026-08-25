---
title: Android 17 FrameTimeline、FrameTracer 与合成边界
chapter: '2.17'
section: '2.17'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-07-08'
last_verified_against: AOSP android-17.0.0_r1
confidence: medium
tags:
- rendering
- frametimeline
- gpu-cpu-boundary
- android17
- surfaceflinger
- hwc
- perfetto
related_chapters:
- '2.1'
- '2.3'
- '2.5'
- '2.8'
sources:
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h
- type: aosp
  path: frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp
- type: aosp
  path: frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp
- type: aosp
  path: frameworks/base/core/java/android/view/Choreographer.java
- type: aosp
  path: external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto
- type: aosp
  path: external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: blog
  path: https://androidperformance.com
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_consolidated_at: '2026-08-11'
consolidated_from:
- src/part1-fundamentals/ch02-rendering/2.32-android-17-frametimeline-数据结构.md
- src/part1-fundamentals/ch02-rendering/2.52-android17-gpu-debug-performance-tools.md
---

# Android 17 FrameTimeline、FrameTracer 与合成边界

FrameTimeline 用于判断一帧是否按调度器预测的时间显示，以及延误更接近应用、SurfaceFlinger、GPU composition（GPU 合成）还是 Display HAL（显示硬件抽象层）。它无法覆盖所有 Producer（内容生产者），也不能单独证明某段 CPU 或 GPU 工作就是根因。

以下分析以 Android 17（API 37）的 `android-17.0.0_r1` 为平台版本，以 `android17-6.18-2026-06_r6` 为内核同步版本。公共显示主线如下：

```text
Producer 生成内容
  → queueBuffer / SurfaceControl.Transaction + acquire fence
  → SurfaceFlinger 接收、选择并 latch buffer
  → HWC validate / present，必要时 RenderEngine 生成 client target
  → present fence 给出显示提交的完成反馈
  → release fence 约束旧 buffer 何时可以复用
```

这条主线把“应用提交”“SurfaceFlinger 采纳”“合成”“显示反馈”和“buffer 复用”分成不同边界。acquire fence 表示新 buffer 何时可读，latch 表示 SurfaceFlinger 采纳 buffer，client target 是 RenderEngine（SurfaceFlinger 的 GPU 合成组件）的合成结果，present fence 与 release fence 分别约束显示完成反馈和旧 buffer 复用。HWC 是 Hardware Composer（硬件合成器）。`queueBuffer()` 返回只代表提交动作完成，不能作为上屏时间。

## 先确认 FrameTimeline 覆盖了哪条出图路径

FrameTimeline 对标准 App Window 最有解释力。页面包含独立 Surface、外部流或多个 Producer 时，应先画出 layer（图层）与 BufferQueue（buffer 生产者和消费者之间的队列）拓扑，再决定 FrameTimeline 能证明哪一段。下表中的 Expected 表示预测区间，Actual 表示观测到的实际区间。

| 出图类型 | FrameTimeline 能直接观察的部分 | 必须补充的证据 |
|---|---|---|
| 标准 View 或 Compose App Window | 宿主应用的 Expected、Actual SurfaceFrame，及其关联的 SF DisplayFrame | `Choreographer#doFrame`、`DrawFrame`、RenderThread、BufferQueue 与 fence |
| `TextureView` | Texture 内容被采样后形成的宿主 App Window 帧 | 上游 `SurfaceTexture` BufferQueue、`updateTexImage()` 与 acquire、外部 Producer |
| `SurfaceView`、自管 `SurfaceControl` | 可能看到部分 transaction 或 display 结果；Perfetto 官方 FrameTimeline 文档仍声明 `SurfaceView` 主体不受完整支持 | 独立 layer、`BufferTX`、queue、latch，以及 acquire、present、release fence |
| Camera、MediaCodec、视频 overlay、sideband（旁路视频流） | 宿主控制层或最终 DisplayFrame | Camera、codec、provider（服务提供方）、HAL 的 Producer、独立队列、HWC 与厂商显示轨迹 |
| Native game | 使用 Choreographer token 并随 buffer transaction 传递时可获得部分关联 | `AChoreographer`、引擎线程、EGL 或 Vulkan 提交、独立 BufferQueue、GPU 与 fence |
| 混合页面、多窗口 | 一个 DisplayFrame 可关联多个进程、多个 SurfaceFrame | 每个 layer 的 Producer、Z-order（层级顺序）、transform（变换）、刷新率与独立队列 |

这张表有两个工程含义：

- FrameTimeline 没有 App slice（带起止时间的 trace 片段），不等于应用没有提交 buffer；
- FrameTimeline 标记 App 正常，也不能排除未纳入该 SurfaceFrame 的 Camera、视频或游戏 Producer 迟到。

## FrameTimeline 的数据模型

### SurfaceFrame 与 DisplayFrame

`frame_timeline_event.proto`（FrameTimeline trace 协议定义）包含两类对象：

- `SurfaceFrame` 表示某个应用或 layer 的一次帧更新；
- `DisplayFrame` 表示 SurfaceFlinger 把多个 layer 组织成一次显示更新。

二者是多对一关系。关联条件写在 proto 注释中：

```text
DisplayFrame.token = SurfaceFrame.display_frame_token
```

等式表示一个 SurfaceFrame 通过 `display_frame_token` 指向所属 DisplayFrame。同一个应用 token（关联帧的整数标识）还可能对应多个 layer，例如一个进程同时更新多个 Surface。查询时必须保留 `upid`（Perfetto 进程标识）与 `layer_name`，不能只按 token 去重。

### token 怎样从应用到达 SurfaceFlinger

Android 17 的关键对象是 `FrameTimelineInfo`：

1. `Choreographer` 或 `AChoreographer` 从当前 VSync（垂直同步）timeline 取得 `vsyncId`；
2. HWUI（Android 硬件加速 UI 管线）或原生 Producer 把 `vsyncId`、帧开始时间、dequeue（取得可写 buffer）等信息写入 `FrameTimelineInfo`；
3. 标准窗口路径由 BLAST（以 BLASTBufferQueue 管理窗口 buffer 的路径）按 frame number（帧序号）保存这份信息，并在 `Transaction::setFrameTimelineInfo()` 中随 buffer transaction 发给 SurfaceFlinger；
4. `FrameTimeline::createSurfaceFrameForToken()` 用 `vsyncId` 查询预测值并创建 `SurfaceFrame`；
5. SurfaceFlinger 完成本轮 display 分类时，把对应 `DisplayFrame` token 写入 SurfaceFrame trace packet（trace 数据包）。

`FrameTimelineInfo.aidl` 中还包含 `startTimeNanos`、`vsyncResyncedJitterNanos` 与 `dequeueBufferDurationNanos`。token 除了标识 UI 帧，还携带分类所需的应用侧时序信息。

token 可能无效或过期。`SurfaceFrame::trace()` 会跳过无效 token；预测过期时，expected 时间戳已经不能用于正常比较，Android 17 会采用专门的过期分类与 trace 处理。因此，看到 `prediction_type = Expired Prediction` 时，应先检查 token 传递与调度延迟，不能继续机械计算 Expected 与 Actual 的差。

### TokenManager 的容量边界

源码注释把预测描述为大约保留 120 ms，但 Android 17 的具体实现是固定容量环形缓冲区，不是为每个 token 建一个 TTL（Time To Live，存活时间）定时器。生产速度、刷新率和是否及时消费都会影响某个 token 何时被覆盖。分析 `prediction expired` 时，应检查 token 创建、transaction 到达和 SurfaceFlinger 消费之间的真实时间，不要把 120 ms 当作精确过期闹钟。

## FrameTracer 与 FrameTimeline 的身份边界

Android 图形 trace 中有两个独立的数据源：

| 维度 | FrameTracer | FrameTimeline |
|---|---|---|
| 数据源 | `android.surfaceflinger.frame` | `android.surfaceflinger.frametimeline` |
| 核心标识 | buffer ID、frame number、layer name | surface token、display token、PID、layer name |
| 主要问题 | buffer 在 dequeue、queue、fence、latch、present 哪段停留 | Expected 与 Actual 是否偏离、哪一侧被分类为 jank（卡顿） |
| Trace Processor | `frame_slice` | `expected_frame_timeline_slice`、`actual_frame_timeline_slice` |

两套 proto 没有声明 `FrameTracer.frame_number = FrameTimeline.surface_frame_token`。可靠关联需要同一 layer、Producer、相邻时间窗、buffer 与 transaction 事件和 display token 共同收窄；只按整数相等执行 join（表连接）会把无关帧拼在一起。

FrameTracer 的事件时间位于外层 `TracePacket.timestamp`。带 fence 的事件会先进入 pending tracker（待完成事件跟踪器），fence signal（发出完成信号）后再闭合 span（时间区间）；立即完成的事件可能表现为 instant（瞬时事件）。Trace Processor 依据事件 phase（阶段）构造 `frame_slice`，因此不能假设每个枚举都对应一条固定 duration slice，也不能由协议中存在某个枚举推断 Android 17 的生产代码一定发射它。

FrameTimeline 的 Expected、Actual start packet 用 cookie（配对标识）建立 slice，end packet 用同一 cookie 闭合。Trace Processor 再把 surface token、display token、PID、layer、present type、prediction type 和 jank bit（卡顿位标记）暴露给 SQL。数据源名称不是 SQL 表名，FrameTracer 的 `frame_slice` 也不是 FrameTimeline actual 表的别名。

## 怎样解读预期值与实际值

### 应用侧 SurfaceFrame

应用侧四个边界的含义如下：

| 字段或区间 | Android 17 口径 |
|---|---|
| Expected start | 调度器预测应用开始处理该帧的时间 |
| Expected end | 应用应当完成 buffer 提交与相关 GPU 工作的 deadline（截止时间） |
| Actual start | 优先使用应用传入的 `startTimeNanos`；没有时回退到预测 start |
| Actual end | `max(actual queue time, acquire fence signal time)`；acquire fence 仍 pending（未完成）时暂用 queue time |

`SurfaceFrame::setAcquireFenceTime()` 给出了 Actual end 的直接依据：

```cpp
if (acquireFenceTime == Fence::SIGNAL_TIME_PENDING) {
    mActuals.endTime = mActualQueueTime;
} else {
    mActuals.endTime = std::max(acquireFenceTime, mActualQueueTime);
}
```

这段代码把 CPU 提交完成与 Producer GPU 完成分开处理。应用很早调用 `queueBuffer()`，但 acquire fence 很晚才 signal，Actual SurfaceFrame 仍会延长到 GPU 可供 Consumer（消费者）读取的时刻。

SurfaceFrame 的 Actual slice 结束于上述 ready（可供后续读取）边界，不延伸到最终上屏；`present_type` 与 `jank_type` 会在 DisplayFrame 获得 present 反馈后回填分类结果。slice 右边界不能直接作为屏幕更新时间。

### SurfaceFlinger 侧 DisplayFrame

DisplayFrame 的 Actual slice 从 SurfaceFlinger 为该帧醒来或开始工作延伸到 actual present：

- start 来自 `onSfWakeUp()` 或相应的实际开始记录；
- SF CPU end 由调用 `setSfPresent()` 时的时间保存；
- actual present 来自 pacesetter display（提供本轮显示节奏基准的 Display）的 present fence signal；
- client composition 存在时，分类还会把 GPU done fence（GPU 完成栅栏）纳入 ready deadline。

DisplayFrame 的 slice 时长包含 Composer、Display HAL 与 present 反馈，不等于 SurfaceFlinger 主线程纯 CPU 时间。分析 SF CPU 时仍要看线程 slice 与调度；分析 SF GPU 时要看 client target GPU fence 和 GPU track（轨道）；分析 Display HAL 时要看“SF 已按时完成，但 present 仍晚”的组合证据。

### 三个字段不能互相替代

| 字段 | 回答的问题 | 常见误读 |
|---|---|---|
| `on_time_finish` | 该对象是否在预测 end 前 ready | `true` 不保证按时 present |
| `present_type` | actual present 相对 predicted present 是 on-time、late、early、dropped 还是 unknown（按时、晚、早、丢弃或未知） | early 不自动等于 pacing bug（节奏控制错误） |
| `prediction_type` | 用于比较的预测是否仍有效 | expired 仍直接比较两个 slice |

FrameTimeline 的 jank 定义围绕 predicted present 与 actual present 是否匹配。单独用 `Actual Display Time - Expected Display Time > 0` 作为所有场景的“用户可见卡顿”判据，会把持续但平滑的高延迟状态、预测误差、模式切换和无效预测混在一起。

## GraphicsFrameEvent：buffer 与 fence 的补充证据

`graphics_frame_event.proto` 定义了 `DEQUEUE`、`QUEUE`、`POST`、`ACQUIRE_FENCE`、`LATCH`、`HWC_COMPOSITION_QUEUED`、`FALLBACK_COMPOSITION`、`PRESENT_FENCE`、`RELEASE_FENCE` 等枚举。枚举存在只表示协议允许表达该事件，不表示 Android 17 的生产代码一定发出它。

在 `android-17.0.0_r1` 的 SurfaceFlinger 生产调用点中，可以确认的事件如下：

| 事件 | Android 17 发射条件 | 判读重点 |
|---|---|---|
| `DEQUEUE` | `Layer::setBuffer()` 收到有效的 `bufferData.dequeueTime` | Producer 取得该 buffer 的时间；不是所有路径都携带 |
| `QUEUE` | 与上项同一条件，时间戳使用 transaction 的 `postTime` | 该 buffer update（更新）进入 SF transaction 的时间锚点 |
| `ACQUIRE_FENCE` | `latchBufferStatsAndHandles()` 追踪 buffer acquire fence | fence span 的终点是 signal time；表示 Consumer 可安全读取 |
| `LATCH` | SF 采纳该 buffer | queue 与 latch 之间可包含 transaction readiness（事务就绪条件）、fence 与调度等待 |
| `FALLBACK_COMPOSITION` | `outputLayer->requiresClientComposition()` | 该 output layer 本轮进入 RenderEngine client composition |
| `PRESENT_FENCE` | per-layer（逐 layer）记录 display present fence；无有效 fence 时可回退到 HWC present timestamp | 是显示侧反馈，不是 panel（面板）光学响应 |

`POST`、`HWC_COMPOSITION_QUEUED`、`RELEASE_FENCE` 等枚举在这组 Android 17 SurfaceFlinger 生产调用点中没有活跃发射点。分析脚本不应要求每帧出现完整枚举序列，也不应仅因缺少 `RELEASE_FENCE` 事件便断言 buffer 已经或尚未可复用。

`android.surfaceflinger.frame` 数据源承载这些 `GraphicsFrameEvent`；`android.surfaceflinger.frametimeline` 承载 SurfaceFrame 与 DisplayFrame。两者用途不同，需要结合 layer、buffer ID、frame number 与相邻时间关系观察。

## CLIENT、DEVICE 与 `gpu_composition`

### HWC 决策会逐帧变化

SurfaceFlinger 每轮根据当前可见 layer 集合准备 CompositionEngine 输出，并与 HWC（Hardware Composer，硬件合成器）交互。Android 17 既可能走 `presentOrValidate()` 快路径，也可能进入 validate：

1. HWC 检查当前 display 与 layer 状态；
2. validate 返回 composition type changes（合成类型变化）与 requests（附加请求）；
3. SurfaceFlinger 与 CompositionEngine 接受变化；
4. 需要 CLIENT 的 layer 由 RenderEngine 合成到 client target；
5. client target 与可做 DEVICE composition 的 layer 一起交给 HWC present。

overlay plane（硬件叠加平面）数量、format（格式）、transform、dataspace（颜色语义）、blend（混合）、protected content（受保护内容）、display mode 与厂商 Composer 能力都会影响结果。不能把流程写成“SurfaceFlinger 发现 CLIENT layer 太多，再把一部分改成 GPU”；composition type changes 来自 HWC validate 协议与 CompositionEngine 的当前策略。

### SurfaceFrame 标志是 layer 粒度

`Layer::onCompositionPresented()` 的条件是：

```cpp
if (outputLayer && outputLayer->requiresClientComposition()) {
    mFrameTracer->traceTimestamp(..., FrameEvent::FALLBACK_COMPOSITION);
    mDrawingState.bufferSurfaceFrameTX->setGpuComposition();
}
```

这段条件只在对应 output layer 需要 client composition 时写入标志。因此，SurfaceFrame 的 `gpu_composition = true` 表示该 layer 在这一轮需要 client composition。`FALLBACK_COMPOSITION` 是 proto 的历史事件名，不能扩写成“原本一定可以由 HWC 合成，后来因异常退回 GPU”。

### DisplayFrame 标志是 pacesetter display 粒度

`SurfaceFlinger::onCompositionPresented()` 只在 display 的 `usesClientComposition` 为真时取得 client target acquire fence，并把 pacesetter display 的 fence 交给 `FrameTimeline::setSfPresent()`。`DisplayFrame::traceActuals()` 随后使用下面的条件：

```cpp
actualDisplayFrameStartEvent->set_gpu_composition(
        mGpuFence != FenceTime::NO_FENCE);
```

代码以是否存在 `mGpuFence` 写入 DisplayFrame 标志，由此可以得到几个严格边界：

- DisplayFrame `gpu_composition = true`：本轮 pacesetter display 存在 SF client composition GPU fence；
- DisplayFrame `gpu_composition = false`：FrameTimeline 没有记录这条 SF client composition fence；
- `false` 不能证明应用没用 GPU，HWUI、游戏或视频 Producer 仍可能在生产自己的 buffer；
- `true` 不能单独证明 GPU 是瓶颈，还要检查 GPU fence、RenderEngine 与 GPU track，以及 deadline；
- DEVICE composition 表示 SF 这一层的图层叠加交给 HWC，不等于系统中“没有 CPU”或“没有 GPU 工作”。

这组标志描述的是 CLIENT 与 DEVICE 合成边界。CPU 调度与控制工作贯穿两条路径，差别在于 SurfaceFlinger 是否用 RenderEngine 生成 client target。

## Jank 分类与颜色

### Android 17 的主要分类

`frame_timeline_event.proto` 把 `jank_type` 定义为 bitmask（位掩码），一帧可以同时具有多个原因。工程分析常用的分类如下：

| 类型 | 解释 | 下一步证据 |
|---|---|---|
| `App Deadline Missed` | SurfaceFrame ready 晚于应用 deadline，并影响 present | `doFrame`、RenderThread、acquire fence、dequeue wait（出队等待） |
| `Buffer Stuffing` | Producer 持续提交，旧帧尚未 present，队列形成高延迟状态 | pending（待处理）buffer、queue、latch、present 序列，以及 dequeue 阻塞 |
| `SurfaceFlinger CPU Deadline Missed` | SF 的就绪时间错过截止时间，且没有 client composition GPU fence 作为 GPU 分支依据 | SF 主线程运行与调度、HWC 阻塞调用 |
| `SurfaceFlinger GPU Deadline Missed` | SF 使用 client composition，CPU end 尚可，但 client target GPU fence 迟到 | RenderEngine、GPU queue 与 fence、频率与带宽 |
| `Display HAL` | SF ready 尚可，显示侧没有在预测 VSync 完成 present | HWC、DRM（Direct Rendering Manager，Linux 显示子系统）、厂商 display trace、模式与电源状态 |
| `SurfaceFlinger Scheduling` | present 偏差符合 VSync cadence（显示节奏）等调度特征 | SF wakeup（唤醒）、VSync、线程调度 |
| `Prediction Error` | predicted present 与显示反馈的偏差不符合当前预测 | VSync 预测、刷新率或模式切换；孤立样本不宜放大 |
| `Dropped Frame` | App 或 SF 侧帧被丢弃 | 前后 token、layer 更新、是否被更新帧取代 |
| `Unknown`、`Non Animating` | 当前证据不足，或不适合按动画连续性分类 | 先检查 prediction、display power、mode 与出图类型 |

Android 17 还包含 `App Resynced Jitter`、`SurfaceFlinger Stuffing`、`Display Not On`、`Display Mode Change In Progress`、`Display Power Mode Change In Progress` 等分类。显示模式或电源切换期间的样本不应直接归咎于业务渲染。

proto 同时携带 legacy（旧版）与 experimental（实验性）的 jank、present 值，并明确标注 experimental 字段不用于 jank 分析。报告应以 Perfetto 公开的 `jank_type`、`present_type`、`prediction_type` 为主，实验字段只用于平台开发调试。

### Perfetto 颜色的含义

| 颜色 | 含义 |
|---|---|
| 绿色 | 没有观察到 jank |
| 浅绿色 | 帧率可以保持平滑，但帧持续晚显示，输入延迟升高 |
| 红色 | slice 所属进程被判为本次 jank 的责任侧；不是固定等同于 App |
| 黄色 | 只用于 App track：应用帧被标为 janky（发生卡顿），但责任被归到 SurfaceFlinger |
| 蓝色 | dropped frame；App 与 SF 侧的具体丢帧语义不同 |

颜色适合定位候选帧，根因仍需结合字段、token flow（token 关联流）、线程 slice、buffer 与 fence 证明。

## TimeStats 与 JankTracker 的统计边界

FrameTimeline 负责逐帧计划、完成时间和 jank 分类；另外两套机制处理聚合与通知：

- `TimeStats` 按 layer 与 display 汇总 present-to-present、post-to-present、acquire-to-present、jank、composition 等趋势，可通过受控的 `dumpsys SurfaceFlinger --timestats` 或 statsd pull（拉取聚合统计）做前后对照。它不是逐帧根因表，也不保证提供任意分位数。
- `JankTracker` 接收已经分类的结果，按 listener（监听器）批量投递；Android 17 的 batch（批次）以 50 条为边界，并支持显式 flush（立即发送积累结果）。通知晚到只说明批量或调度延迟，不表示 jank 到那一刻才被判定。

一轮诊断应先用 FrameTimeline 找出同一 SurfaceFrame 与 DisplayFrame 的异常，再用 FrameTracer、线程 slice、BufferTX、fence 与 HWC 解释阶段；最后用 TimeStats 验证现象是否在稳定样本中持续。若业务需要在线反馈，再核对 JankTracker listener 收到的 bit（分类位）、批次和 flush 时机。

## fence 与 BufferQueue：不要把三个方向混在一起

| 同步对象 | 生产者与消费者关系 | 能回答的问题 |
|---|---|---|
| acquire fence | Producer 随新 buffer 交给 Consumer | 新 buffer 何时写完、何时可安全读取 |
| present fence | HWC、display 对本次 display present 的反馈 | 本轮显示更新到达哪个系统完成边界 |
| release fence | Consumer、HWC 交还旧 buffer 的使用完成约束 | Producer 何时可以安全复用该 buffer |

Android 用户态通过 `Fence`、`FenceTime` 与 sync file（同步文件对象）传递这些同步对象；指定内核锚点中的 `dma_fence` 提供 signal、wait 与 callback 基础。FrameTimeline 读取的是用户态和 HAL 传回的时间，不是直接把某个内核函数耗时当作 jank 根因。

排查 buffer starvation（可用 buffer 不足）时，应观察 `dequeueBuffer` 等待、可用 slot（槽位）、pending buffer、release callback 与 fence，以及前序帧的 present。把“当前 Actual end 到下一帧 Expected start”的差当作 release fence 时间，会混淆两个不同对象。

Android 的 BufferQueue 与 fence 设计用于避免 Consumer 读取未完成内容。看到游戏或视频画面撕裂感时，先区分 frame pacing（帧节奏控制）、重复帧或丢帧、transform 更新不同步和厂商显示路径；只有拿到绕过正常同步或显示扫描异常的证据，才适合使用 classic tearing（经典撕裂）结论。

## 采集一份可解释的 trace

Perfetto UI 的 Android preset（预设配置）通常会启用 FrameTimeline。需要可复现的命令行配置时，下面的配置会同时收集两类 SurfaceFlinger 数据，以及 App 与 SF 常用的 atrace（Android trace 标记）数据：

```protobuf
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}

duration_ms: 10000

data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}

data_sources {
  config {
    name: "android.surfaceflinger.frame"
  }
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "sched"
      atrace_apps: "com.example.app"
    }
  }
}
```

把 `com.example.app` 替换成目标包名。`android.surfaceflinger.frametimeline` 提供 Expected、Actual 与 jank 分类，`android.surfaceflinger.frame` 提供 buffer 和 fence 事件，`gfx`、`view`、`sched` 用于解释应用与线程调度。

配置保存为 `/data/local/tmp/frame.pbtxt` 后，可以用下面的命令采集：

```bash
adb shell perfetto --txt \
  -c /data/local/tmp/frame.pbtxt \
  -o /data/misc/perfetto-traces/frame.perfetto-trace

adb pull /data/misc/perfetto-traces/frame.perfetto-trace
```

第一条命令按配置采集 10 秒，第二条把 trace 拉回主机。复现窗口应覆盖问题前后的稳定帧，避免只截到一次模式切换或应用刚启动的瞬态。

## 用 SQL 保留 token、layer 与进程上下文

### 查询应用侧 SurfaceFrame

下面的查询用于列出应用侧 Actual SurfaceFrame，并保留归因所需字段：

```sql
SELECT
  a.ts,
  a.dur,
  a.surface_frame_token AS app_token,
  a.display_frame_token AS sf_token,
  p.name AS process_name,
  a.layer_name,
  a.present_type,
  a.on_time_finish,
  a.gpu_composition,
  a.jank_type,
  a.prediction_type
FROM actual_frame_timeline_slice AS a
LEFT JOIN process AS p USING (upid)
WHERE a.surface_frame_token IS NOT NULL
ORDER BY a.ts;
```

结果中的 `dur` 是应用 ready 区间，`present_type` 是后来根据显示反馈完成的分类。相同 `app_token` 出现多行时，应先查看 process（进程）与 layer，不要立即去重。

### 按 DisplayFrame 关联 App 与 SurfaceFlinger

下面的查询用 `display_frame_token` 把每个应用 SurfaceFrame 关联到同一轮 SF DisplayFrame：

```sql
WITH app AS (
  SELECT *
  FROM actual_frame_timeline_slice
  WHERE surface_frame_token IS NOT NULL
),
sf AS (
  SELECT *
  FROM actual_frame_timeline_slice
  WHERE surface_frame_token IS NULL
)
SELECT
  app.ts AS app_ts,
  app.surface_frame_token AS app_token,
  app.display_frame_token AS sf_token,
  app.layer_name,
  app.jank_type AS app_jank,
  app.gpu_composition AS app_client_composition,
  sf.ts AS sf_ts,
  sf.dur AS sf_dur,
  sf.present_type AS sf_present_type,
  sf.jank_type AS sf_jank,
  sf.gpu_composition AS sf_client_composition
FROM app
LEFT JOIN sf USING (display_frame_token)
ORDER BY app.ts;
```

一个 SF token 关联多条 App 记录是正常现象：一次显示更新可以合成多个 layer。SF 记录缺失时，应检查 token 是否无效、预测是否过期、trace 是否从帧中途开始，以及目标是否属于 FrameTimeline 覆盖有限的独立 Surface。

### 计算 per-frame deadline overrun（逐帧超期量）

Perfetto v54 的 `android.frames.per_frame_metrics` 模块提供 `android_frame_stats`。下面的查询用于按 deadline overrun 排序：

```sql
INCLUDE PERFETTO MODULE android.frames.per_frame_metrics;

SELECT
  frame_id,
  overrun / 1e6 AS overrun_ms,
  cpu_time / 1e6 AS cpu_time_ms,
  ui_time / 1e6 AS ui_time_ms,
  was_jank
FROM android_frame_stats
ORDER BY overrun DESC;
```

`overrun` 是 Actual end 减 Expected end，负数表示没有错过该 deadline。该表依赖能被 stdlib（Perfetto 标准模块库）关联的 `Choreographer#doFrame`、`DrawFrame` 与 FrameTimeline slice；缺行时不能把 `NULL` 当作 0，也不能用它替代 `jank_type` 对 SF 或 Display HAL 的分类。

## 四类常见问题怎样复核

### 标准 HWUI 页面：App Deadline Missed

建议按同一个 App token 检查：

1. Actual start 是否已经晚于 Expected start；
2. `Choreographer#doFrame` 内 INPUT、ANIMATION、TRAVERSAL、COMMIT 哪段变长；
3. `DrawFrame` 或 RenderThread 是 CPU 提交慢，还是 GPU acquire fence 晚；
4. `dequeueBuffer` 是否因旧 buffer 尚未 release（释放）而等待；
5. 对应 DisplayFrame 是否又叠加 SF 或 Display HAL jank。

SurfaceFrame `gpu_composition = false` 只表示该 layer 没有被 SF 放入 client composition，不能排除 HWUI 生成 buffer 时的 GPU 延迟。

### SurfaceView 或游戏：画面节奏不稳

不要假定 Native（原生）引擎一定把 `Choreographer.FrameData` 正确传到了目标 Surface。验证 token 存在后，再沿独立 layer 检查：

```text
AChoreographer / engine tick
  → EGL/Vulkan submit
  → queueBuffer + acquire fence
  → BufferTX / latch
  → HWC present + present fence
```

这条序列用来定位“逻辑 tick（引擎帧节拍）晚、GPU 完成晚、buffer 到达晚、SF 没采纳、显示后段晚”中的哪一段。buffer 早于目标时间 ready 通常只是留出排队余量，不能单凭“早”判为 pacing 错误。

### 大量 `gpu_composition = true`

这只说明 SF 频繁使用 CLIENT composition 路径。要证明它造成 deadline miss（错过截止时间），还需要同时看到：

- `SurfaceFlinger GPU Deadline Missed` 或相符的 deadline；
- client target GPU fence signal 偏晚；
- RenderEngine、GPU track 与该 DisplayFrame 时间重叠；
- 排除 App 自己的 GPU、HWC validate、Display HAL 或频率切换。

优化方向应根据触发 CLIENT 的具体 layer 状态确定。直接移除 `ColorMatrix`、改成 `SurfaceView` 或强制 overlay，可能改变透明度、保护内容、颜色管理与生命周期语义，而且 HWC 仍可在下一帧返回不同结果。

### App 与 SF 都 ready，但 present 仍晚

当 App `on_time_finish = true`、SF 的 CPU 与 GPU 也在 deadline 内 ready，而 DisplayFrame 仍 late 并标记 `Display HAL`，排查重点应移到 HWC、DRM、厂商显示栈、刷新率或显示模式切换。present fence 能给出显示侧时间锚点，但不能继续细分 panel scanout（面板扫描输出）与光学响应。

## 一套不跳阶段的诊断顺序

1. **确认问题窗口与刷新率**
   记录显示 mode、render rate（渲染帧率）、输入事件和用户看到的现象，排除启动、旋转、亮灭屏与模式切换瞬态。

2. **确认 Producer 与承载对象**
   标出 App Window、TextureView、SurfaceView，以及 Camera、video、game 的 Producer、BufferQueue、layer name 与进程。

3. **选择一个异常 token**
   同时查看 Expected、Actual、prediction、present、jank、severity（严重程度）、layer 与 flow（跨轨道关联），不按颜色直接归因。

4. **检查应用 ready 边界**
   对照 `doFrame`、RenderThread、queue time 与 acquire fence，区分 CPU、Producer GPU 和 dequeue wait。

5. **检查 SF 是否采纳新内容**
   对照 QUEUE、`BufferTX`、LATCH 与 pending buffer。已经入队但本轮没有 latch，说明问题仍在显示前段。

6. **检查 CLIENT 与 DEVICE composition**
   用 SurfaceFrame、DisplayFrame 的 `gpu_composition` 找到候选，再以 validate、RenderEngine 和 GPU fence 证明成本。

7. **检查 present 与 buffer 归还**
   present fence 解释显示更新，release fence 与回调解释 buffer 复用。二者不能交换。

8. **用相邻稳定帧复核**
   比较同一 layer 的正常帧与异常帧，确认结论可重复，并排除一次性的 prediction 或 display mode 变化。

## Android 12 到 Android 17 的版本边界

| 平台 | 可验证边界 |
|---|---|
| Android 12（API 31） | FrameTimeline 开始提供 App、SF 的 Expected 与 Actual timeline，作为这里分析的最低版本 |
| Android 13（API 33） | 公开 `Choreographer.FrameData` 与 FrameTimeline 查询能力；原生与自定义渲染仍要把 token 随目标帧传下去 |
| Android 14（API 34） | 公共 App Window→BLAST→SF→HWC 主线继续成立；独立 Surface 与混合页面仍需额外 buffer、fence 证据 |
| Android 15（API 35） | `SurfaceControl.Transaction.setFrameTimeline(vsyncId)` 等公开能力让自管 transaction 可表达帧 timeline；它不生成 buffer，也不消除 fence wait（等待） |
| Android 16（API 36） | 这里的 token、Expected 与 Actual、CLIENT 与 DEVICE 判读方法继续适用 |
| Android 17（API 37） | 源码锚点为 `Scheduler/FrameTimeline.{h,cpp}`、当前 BLAST、CompositionEngine，以及 HWC `presentOrValidate` 与 validate 路径 |

表中“源码位于某目录”只描述 Android 17 当前结构，不表示该文件到 Android 17 才出现。涉及更早版本时，应切换到对应 tag 核查函数位置和字段，不能用当前目录结构推断版本演进。

## 源码核对清单

- [`FrameTimeline.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.h) 与 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)
  - 核对 SurfaceFrame、DisplayFrame 的预测、Actual end、present、jank 分类与 `gpu_composition` 写入。
- [`Layer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Layer.cpp) 与 [`FrameTracer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrameTracer/FrameTracer.cpp)
  - 核对 DEQUEUE、QUEUE、ACQUIRE_FENCE、LATCH、FALLBACK_COMPOSITION、PRESENT_FENCE 的生产调用点。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp) 与 [`FrameTimelineInfo.aidl`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/aidl/android/gui/FrameTimelineInfo.aidl)
  - 核对 frame number、vsyncId 与应用时序信息怎样进入 buffer transaction。
- [`graphics_frame_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/android/graphics_frame_event.proto) 与 [`frame_timeline_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/android/frame_timeline_event.proto)
  - 核对协议枚举、token 关系、present、prediction、jank 字段及 experimental 警告。
- [Perfetto FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)
  - 核对 UI track、颜色、SurfaceView 覆盖限制、SQL 基础表与数据源名称。
- [`dma-fence.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/dma-fence.h) 与 [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)
  - 核对 Android 17 kernel 锚点下 fence signal、wait 与 sync file 基础，不把用户态帧分类等同于内核耗时。

## 小结

FrameTimeline 的强项是把预测、应用 ready、SurfaceFlinger display work（显示处理）与 actual present 放进同一套 token 关系中。可靠结论需要同时守住四个边界：

- SurfaceFrame Actual end 是 queue 与 acquire fence 的较晚者，不是上屏时间；
- DisplayFrame Actual slice 延伸到 present，不能当作 SF 主线程 CPU 时长；
- `gpu_composition` 描述 SF 的 CLIENT composition 边界，不描述应用是否使用 GPU；
- 独立 Surface、Camera、视频、游戏与混合页面必须补充 layer、BufferQueue 和 fence。

按 Producer → buffer → latch → composition → present → release 的顺序检查，才能把“帧晚了”缩小为可由源码与 trace 共同复现的问题。
