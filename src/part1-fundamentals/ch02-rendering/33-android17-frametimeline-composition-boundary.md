---
title: "Android 17 FrameTimeline GPU/CPU 合成边界判定机制"
chapter: "2.33"
status: "finalized"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-08"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
drafted_date: "2026-06-30"
last_task6_audit: "2026-07-10"
last_task6_review_at: "2026-07-03T16:19:00+08:00"
last_task6_at: 2026-07-08T08:10:41+08:00
tags: [rendering, frametimeline, gpu-cpu-boundary, android17, surfaceflinger, hwc, perfetto]
related_chapters: ["2.1", "2.4", "2.6", "2.25"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-29"
gap_source: "DeepResearch"
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.h"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Scheduler/FrameTimeline.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp"
  - type: aosp
    path: "frameworks/base/core/java/android/view/Choreographer.java"
  - type: aosp
    path: "external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto"
  - type: aosp
    path: "external/perfetto/protos/perfetto/trace/android/frame_timeline_event.proto"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: blog
    path: "https://androidperformance.com"
task2b_state: fixed
task2b_result: fixed
task6_state: reviewed
task6_result: pass-light-edit
task6_review_notes_round6: "2026-07-10 Task6 revisiting-review round6: pass-light-edit (2 L1 fixes: meta-narration 本章聚焦→下面聚焦, banned word 实际上→实际被)"
task6_review_notes_round7: "2026-07-10 Task6 revisiting-review round7: pass-light-edit (无新增L1/L2问题，L3问题已标注)"
task6_review_notes_round9: "2026-07-10 Task6 revisiting-review round9: pass-light-edit (章节已多次审核，技术内容完整，符合writing-guide规范)"
task6_review_notes_round10: "2026-07-10 Task6 review round10: pass-light-edit, auto-promoted to finalized (task6+task9 passed, queue clean, frontmatter dup cleaned)"
reviewed_date: "2026-07-10"
reviewed_by: "openclaw-task6"
task9_state: reviewed
task9_result: auto-fixed
task9_result_prev: needs-rework
pipeline_stage: ready-to-publish
last_task9_at: "2026-07-10T14:39:11+08:00"
last_task9_review_log: "logs/deep-review/2026-07-10-14-deep-review.md"
last_task2b_lite_at: "2026-07-08"
last_task2b_at: 2026-07-08T06:56:51+08:00
task2b_rework_round: "3-heavy"
task2b_rework_source: "task9-deep-tech-review P95"
task6_review_notes_round2: "2026-07-03 Task6 revisiting-review round2 (post-Task9-autofix): pass-light-edit"
task6_review_notes_round3: "2026-07-08 Task6 revisiting-review round3: pass-light-edit"
task6_review_notes_round4: "2026-07-08 Task6 revisiting-review round4 (post-Task2B-heavy-rework-r3): pass-light-edit (1 L1 fix: banned word 对齐→精确关联)"
task6_review_notes_round5: "2026-07-08 Task6 revisiting-review round5: pass-light-edit, auto-promoted to finalized (task6+task9 passed, queue clean)"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-18
last_task9_autofix_at: "2026-07-10"
task9_review_notes: "2026-07-10 Task9 deep-review: auto-fixed。P0 2 / P1 1 已局部修复：DisplayFrame gpu_composition 源码片段、Perfetto stdlib SQL 表名、trace 配置边界。详见 logs/deep-review/2026-07-10-14-deep-review.md。"
---

# 2.33 Android 17 FrameTimeline：应用、SurfaceFlinger 与合成边界

FrameTimeline 用于判断一帧是否按调度器预测的时间显示，以及延误更接近应用、SurfaceFlinger、GPU 合成还是显示 HAL。它无法覆盖所有生产者，也不能单独证明某段 CPU 或 GPU 工作就是根因。

以下分析以 Android 17 / API 37 的 `android-17.0.0_r1` 为平台版本，以 `android17-6.18-2026-06_r6` 为内核同步版本。公共显示主线如下：

```text
生产者生成内容
  → queueBuffer / SurfaceControl.Transaction + acquire fence
  → SurfaceFlinger 接收、选择并锁存缓冲区
  → HWC validate / present，必要时 RenderEngine 生成 client target
  → 送显栅栏给出显示提交的完成反馈
  → 释放栅栏约束旧缓冲区何时可以复用
```

这条主线把“应用提交”“SurfaceFlinger 采纳”“合成”“显示反馈”和“缓冲区复用”分成不同边界。`queueBuffer()` 返回只代表提交动作完成，不能作为上屏时间。

## 先确认 FrameTimeline 覆盖了哪条出图路径

FrameTimeline 对标准应用窗口最有解释力。页面包含独立 Surface、外部流或多个生产者时，应先画出图层与 BufferQueue 拓扑，再判断 FrameTimeline 能证明哪一段。

| 出图类型 | FrameTimeline 能直接观察的部分 | 必须补充的证据 |
|---|---|---|
| 标准 View / Compose App Window | 宿主应用的 Expected/Actual SurfaceFrame，及其关联的 SF DisplayFrame | `Choreographer#doFrame`、`DrawFrame`、RenderThread、BufferQueue 与 fence |
| `TextureView` | Texture 内容被采样后形成的宿主 App Window 帧 | 上游 `SurfaceTexture` BufferQueue、`updateTexImage()`/acquire、外部 Producer |
| `SurfaceView`、自管 `SurfaceControl` | 可能看到部分 transaction 或 display 结果；Perfetto 官方 FrameTimeline 文档仍声明 `SurfaceView` 主体不受完整支持 | 独立 layer、`BufferTX`、queue/latch、acquire/present/release fence |
| Camera、MediaCodec、视频 overlay、sideband | 宿主控制层或最终 DisplayFrame | Camera/codec/provider/HAL 的 Producer、独立队列、HWC/厂商显示轨迹 |
| Native game | 使用 Choreographer token 并随 buffer transaction 传递时可获得部分关联 | `AChoreographer`、引擎线程、EGL/Vulkan 提交、独立 BufferQueue、GPU 与 fence |
| 混合页面、多窗口 | 一个 DisplayFrame 可关联多个进程、多个 SurfaceFrame | 每个 layer 的 Producer、Z-order、transform、刷新率与独立队列 |

这张表有两个工程含义：

- FrameTimeline 没有应用切片，不代表应用没有提交缓冲区；
- FrameTimeline 标记应用正常，也不能排除未纳入该 SurfaceFrame 的 Camera、视频或游戏生产者迟到。

## FrameTimeline 的数据模型

### SurfaceFrame 与 DisplayFrame

`frame_timeline_event.proto` 定义了两类对象：

- `SurfaceFrame` 表示某个应用或图层的一次帧更新；
- `DisplayFrame` 表示 SurfaceFlinger 把多个图层组织成一次显示更新。

二者是多对一关系。关联条件写在 proto 注释中：

```text
DisplayFrame.token = SurfaceFrame.display_frame_token
```

同一个应用令牌还可能对应多个图层，例如一个进程同时更新多个 Surface。查询时必须保留 `upid` 与 `layer_name`，不能只按令牌去重。

### 令牌怎样从应用到达 SurfaceFlinger

Android 17 的关键对象是 `FrameTimelineInfo`：

1. `Choreographer` / `AChoreographer` 从当前 VSync 时间线取得 `vsyncId`；
2. HWUI 或原生生产者把 `vsyncId`、帧开始时间、出队等信息写入 `FrameTimelineInfo`；
3. 标准窗口路径由 BLAST 按帧编号保存这份信息，并在 `Transaction::setFrameTimelineInfo()` 中随缓冲区事务发给 SurfaceFlinger；
4. `FrameTimeline::createSurfaceFrameForToken()` 用 `vsyncId` 查询预测值并创建 `SurfaceFrame`；
5. SurfaceFlinger 完成本轮 display 分类时，把对应 `DisplayFrame` token 写入 SurfaceFrame trace packet。

`FrameTimelineInfo.aidl` 中还包含 `startTimeNanos`、`vsyncResyncedJitterNanos` 与 `dequeueBufferDurationNanos`。令牌除了标识 UI 帧，还携带分类所需的应用侧时序信息。

令牌可能无效或过期。`SurfaceFrame::trace()` 会跳过无效令牌；预测过期后，预期时间戳已不能用于常规比较，Android 17 会采用专门的过期分类与轨迹处理。遇到 `prediction_type = Expired Prediction` 时，应先检查令牌传递与调度延迟，不宜继续机械计算预期值与实际值的差。

## 怎样解读预期值与实际值

### 应用侧 SurfaceFrame

应用侧四个边界的含义如下：

| 字段/区间 | Android 17 口径 |
|---|---|
| Expected start | 调度器预测应用开始处理该帧的时间 |
| Expected end | 应用应当完成 buffer 提交与相关 GPU 工作的 deadline |
| Actual start | 优先使用应用传入的 `startTimeNanos`；没有时回退到预测 start |
| Actual end | `max(actual queue time, acquire fence signal time)`；acquire fence 仍 pending 时暂用 queue time |

`SurfaceFrame::setAcquireFenceTime()` 给出了实际结束时间的直接依据：

```cpp
if (acquireFenceTime == Fence::SIGNAL_TIME_PENDING) {
    mActuals.endTime = mActualQueueTime;
} else {
    mActuals.endTime = std::max(acquireFenceTime, mActualQueueTime);
}
```

这段代码分开处理 CPU 提交完成与生产者 GPU 完成。即使应用很早调用 `queueBuffer()`，只要获取栅栏很晚才发出信号，SurfaceFrame 的实际区间仍会延长到 GPU 内容可供消费者读取的时刻。

SurfaceFrame 的实际切片结束于上述就绪边界，不延伸到最终上屏；`present_type` 与 `jank_type` 会在 DisplayFrame 获得送显反馈后回填分类结果。切片右边界不能直接作为屏幕更新时间。

### SurfaceFlinger 侧 DisplayFrame

DisplayFrame 的实际切片从 SurfaceFlinger 为该帧醒来或开始工作延伸到实际送显：

- 开始时间来自 `onSfWakeUp()` 或相应的实际开始记录；
- SF CPU 结束时间由调用 `setSfPresent()` 时的时间保存；
- 实际送显时间来自节奏基准显示器的送显栅栏信号；
- 存在客户端合成时，分类还会把 GPU 完成栅栏纳入就绪截止时间。

DisplayFrame 的 slice 时长包含 Composer、Display HAL 与 present 反馈，不等于 SurfaceFlinger 主线程纯 CPU 时间。分析 SF CPU 时仍要看线程 slice 与调度；分析 SF GPU 时要看 client target GPU fence 和 GPU track；分析 Display HAL 时要看“SF 已按时完成，但 present 仍晚”的组合证据。

### 三个字段不能互相替代

| 字段 | 回答的问题 | 常见误读 |
|---|---|---|
| `on_time_finish` | 该对象是否在预测结束时间前就绪 | `true` 不保证按时送显 |
| `present_type` | actual present 相对 predicted present 是 on-time、late、early、dropped 还是 unknown | early 不自动等于 pacing bug |
| `prediction_type` | 用于比较的预测是否仍有效 | 预测过期后仍直接比较两个切片 |

FrameTimeline 的卡顿定义围绕预测送显与实际送显是否匹配。若单独用 `Actual Display Time - Expected Display Time > 0` 判断所有场景的“用户可见卡顿”，高延迟但平滑的状态、预测误差、模式切换和无效预测都会被混在一起。

## GraphicsFrameEvent：缓冲区与栅栏的补充证据

`graphics_frame_event.proto` 定义了 `DEQUEUE`、`QUEUE`、`POST`、`ACQUIRE_FENCE`、`LATCH`、`HWC_COMPOSITION_QUEUED`、`FALLBACK_COMPOSITION`、`PRESENT_FENCE`、`RELEASE_FENCE` 等枚举。枚举存在只表示协议允许表达该事件，不表示 Android 17 的生产代码一定发出它。

在 `android-17.0.0_r1` 的 SurfaceFlinger 生产调用点中，可以确认的事件如下：

| 事件 | Android 17 发射条件 | 判读重点 |
|---|---|---|
| `DEQUEUE` | `Layer::setBuffer()` 收到有效的 `bufferData.dequeueTime` | 生产者取得该缓冲区的时间；部分路径不携带此字段 |
| `QUEUE` | 与上项条件相同，时间戳使用事务的 `postTime` | 该缓冲区更新进入 SF 事务的时间锚点 |
| `ACQUIRE_FENCE` | `latchBufferStatsAndHandles()` 追踪缓冲区获取栅栏 | 栅栏区间终点是发出信号的时间，表示消费者可安全读取 |
| `LATCH` | SF 采纳该缓冲区 | 入队与锁存之间可包含事务就绪、栅栏与调度等待 |
| `FALLBACK_COMPOSITION` | `outputLayer->requiresClientComposition()` | 该输出图层本轮进入 RenderEngine 客户端合成 |
| `PRESENT_FENCE` | per-layer 记录 display present fence；无有效 fence 时可回退到 HWC present timestamp | 是显示侧反馈，不是 panel 光学响应 |

`POST`、`HWC_COMPOSITION_QUEUED`、`RELEASE_FENCE` 等枚举在这组 Android 17 SurfaceFlinger 生产调用点中没有活跃发射点。分析脚本不应要求每帧出现完整枚举序列，也不应仅因缺少 `RELEASE_FENCE` 事件便断言缓冲区已经或尚未可复用。

`android.surfaceflinger.frame` 数据源承载这些 `GraphicsFrameEvent`；`android.surfaceflinger.frametimeline` 承载 SurfaceFrame/DisplayFrame。两者用途不同，需要结合图层、缓冲区 ID、帧编号与相邻时间关系观察。

## CLIENT、DEVICE 与 `gpu_composition`

### HWC 决策会逐帧变化

SurfaceFlinger 每轮根据当前可见图层集合准备 CompositionEngine 输出，并与 HWC 交互。Android 17 既可能走 `presentOrValidate()` 快路径，也可能进入验证流程：

1. HWC 检查当前显示器与图层状态；
2. 验证过程返回合成类型变化与请求；
3. SurfaceFlinger/CompositionEngine 接受变化；
4. 需要 CLIENT 的图层由 RenderEngine 合成到客户端目标；
5. client target 与可 DEVICE composition 的 layer 一起交给 HWC present。

overlay plane 数量、format、transform、dataspace、blend、protected content、display mode 与厂商 Composer 能力都会影响结果。不能把流程写成“SurfaceFlinger 发现 CLIENT layer 太多，再把一部分改成 GPU”；composition type changes 来自 HWC validate 协议与 CompositionEngine 的当前策略。

### SurfaceFrame 标志是图层粒度

`Layer::onCompositionPresented()` 的条件是：

```cpp
if (outputLayer && outputLayer->requiresClientComposition()) {
    mFrameTracer->traceTimestamp(..., FrameEvent::FALLBACK_COMPOSITION);
    mDrawingState.bufferSurfaceFrameTX->setGpuComposition();
}
```

SurfaceFrame 的 `gpu_composition = true` 表示对应输出图层在这一轮需要客户端合成。`FALLBACK_COMPOSITION` 是协议中的历史事件名，不能扩写成“原本一定可以由 HWC 合成，后来因异常退回 GPU”。

### DisplayFrame 标志是节奏基准显示器粒度

`SurfaceFlinger::onCompositionPresented()` 只在显示器的 `usesClientComposition` 为真时取得客户端目标的获取栅栏，并把节奏基准显示器的栅栏交给 `FrameTimeline::setSfPresent()`。`DisplayFrame::traceActuals()` 随后使用下面的条件：

```cpp
actualDisplayFrameStartEvent->set_gpu_composition(
        mGpuFence != FenceTime::NO_FENCE);
```

由此可以得到几个严格边界：

- DisplayFrame `gpu_composition = true`：本轮 pacesetter display 存在 SF client composition GPU fence；
- DisplayFrame `gpu_composition = false`：FrameTimeline 没有记录这条 SF client composition fence；
- `false` 不能证明应用没有使用 GPU，HWUI、游戏或视频生产者仍可能在生成自己的缓冲区；
- `true` 不能单独证明 GPU 是瓶颈，还要检查 GPU fence、RenderEngine/GPU track 与 deadline；
- DEVICE 合成表示 SF 这一层的图层叠加交给 HWC，不等于系统中“没有 CPU”或“没有 GPU 工作”。

这组标志描述的是 CLIENT/DEVICE 合成边界。CPU 调度与控制工作贯穿两条路径，差别在于 SurfaceFlinger 是否用 RenderEngine 生成客户端目标。

## Jank 分类与颜色

### Android 17 的主要分类

`frame_timeline_event.proto` 把 `jank_type` 定义为位掩码，一帧可以同时具有多个原因。工程分析常用的分类如下：

| 类型 | 解释 | 下一步证据 |
|---|---|---|
| `App Deadline Missed` | SurfaceFrame ready 晚于应用 deadline，并影响 present | `doFrame`、RenderThread、acquire fence、dequeue wait |
| `Buffer Stuffing` | Producer 持续提交，旧帧尚未 present，队列形成高延迟状态 | pending buffer、queue/latch/present 序列、dequeue 阻塞 |
| `SurfaceFlinger CPU Deadline Missed` | SF 的就绪时间错过截止时间，且没有客户端合成 GPU 栅栏作为 GPU 分支依据 | SF 主线程运行与调度、HWC 阻塞调用 |
| `SurfaceFlinger GPU Deadline Missed` | SF 使用 client composition，CPU end 尚可，但 client target GPU fence 迟到 | RenderEngine、GPU queue/fence、频率与带宽 |
| `Display HAL` | SF 已按时就绪，显示侧却未在预测 VSync 完成送显 | HWC/DRM/厂商显示轨迹、模式与电源状态 |
| `SurfaceFlinger Scheduling` | present 偏差符合 VSync cadence 等调度特征 | SF wakeup、VSync、线程调度 |
| `Prediction Error` | 预测送显与显示反馈的偏差不符合当前预测 | VSync 预测、刷新率/模式切换；孤立样本不宜放大 |
| `Dropped Frame` | 应用或 SF 侧帧被丢弃 | 前后令牌、图层更新、是否被更新帧取代 |
| `Unknown` / `Non Animating` | 当前证据不足，或不适合按动画连续性分类 | 检查预测、显示电源/模式与出图类型 |

Android 17 还包含 `App Resynced Jitter`、`SurfaceFlinger Stuffing`、`Display Not On`、`Display Mode Change In Progress`、`Display Power Mode Change In Progress` 等分类。显示模式或电源切换期间的样本不应直接归咎于业务渲染。

协议同时携带旧版值和实验性的卡顿/送显值，并明确标注实验字段不用于卡顿分析。报告应以 Perfetto 公开的 `jank_type`、`present_type`、`prediction_type` 为主，实验字段只用于平台开发调试。

### Perfetto 颜色的含义

| 颜色 | 含义 |
|---|---|
| 绿色 | 没有观察到 jank |
| 浅绿色 | 帧率可以保持平滑，但帧持续晚显示，输入延迟升高 |
| 红色 | 切片所属进程被判为本次卡顿的责任侧；不固定等同于应用 |
| 黄色 | 只用于应用轨迹：应用帧发生卡顿，但责任归到 SurfaceFlinger |
| 蓝色 | dropped frame；App 与 SF 侧的具体丢帧语义不同 |

颜色适合定位候选帧，根因仍需结合字段、token flow、线程切片、缓冲区与栅栏证明。

## 栅栏与 BufferQueue：区分三个方向

| 同步对象 | 生产者/消费者关系 | 能回答的问题 |
|---|---|---|
| acquire fence | Producer 随新 buffer 交给 Consumer | 新 buffer 何时写完、何时可安全读取 |
| present fence | HWC/display 对本次 display present 的反馈 | 本轮显示更新到达哪个系统完成边界 |
| release fence | Consumer/HWC 交还旧 buffer 的使用完成约束 | Producer 何时可以安全复用该 buffer |

Android 用户态通过 `Fence`/`FenceTime` 与同步文件传递这些同步对象；指定内核锚点中的 `dma_fence` 提供发出信号、等待与回调的基础。FrameTimeline 读取用户态和 HAL 传回的时间，不能把某个内核函数耗时直接当作卡顿根因。

排查缓冲区饥饿时，应观察 `dequeueBuffer` 等待、可用槽位、pending buffer、释放回调/栅栏与前序帧的送显。若把“当前实际结束时间到下一帧预期开始时间”的差当作释放栅栏时间，就会混淆两个不同对象。

Android 的 BufferQueue 与栅栏用于防止消费者读取未完成内容。遇到游戏或视频画面有撕裂感时，应区分帧节奏、重复/丢帧、变换更新不同步和厂商显示路径；只有取得绕过正常同步或显示扫描异常的证据，才能判为经典画面撕裂。

## 采集一份可解释的轨迹

Perfetto 界面的 Android 预设通常会启用 FrameTimeline。需要可复现的命令行配置时，下面的配置会同时收集两类 SurfaceFlinger 数据，以及应用/SF 常用的 atrace 数据：

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

把 `com.example.app` 替换成目标包名。`android.surfaceflinger.frametimeline` 提供预期值、实际值与卡顿分类，`android.surfaceflinger.frame` 提供缓冲区/栅栏事件，`gfx`/`view`/`sched` 用于解释应用与线程调度。

配置保存为 `/data/local/tmp/frame.pbtxt` 后，可以用下面的命令采集：

```bash
adb shell perfetto --txt \
  -c /data/local/tmp/frame.pbtxt \
  -o /data/misc/perfetto-traces/frame.perfetto-trace

adb pull /data/misc/perfetto-traces/frame.perfetto-trace
```

第一条命令按配置采集 10 秒，第二条把轨迹拉回主机。复现窗口应覆盖问题前后的稳定帧，避免只截到一次模式切换或应用刚启动的瞬态。

## 用 SQL 保留令牌、图层与进程上下文

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

结果中的 `dur` 是应用就绪区间，`present_type` 是后来根据显示反馈完成的分类。相同 `app_token` 出现多行时，应先查看进程与图层，不要立即去重。

### 按 DisplayFrame 关联应用与 SurfaceFlinger

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

一个 SF 令牌关联多条应用记录是正常现象：一次显示更新可以合成多个图层。SF 记录缺失时，应检查令牌是否无效、预测是否过期、轨迹是否从帧中途开始，以及目标是否属于 FrameTimeline 覆盖有限的独立 Surface。

### 计算逐帧超期时间

Perfetto v54 的 `android.frames.per_frame_metrics` 模块提供 `android_frame_stats`。下面的查询用于筛选超过截止时间的帧：

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

`overrun` 是 Actual end 减 Expected end，负数表示没有错过该 deadline。该表依赖能被 stdlib 关联的 `Choreographer#doFrame`、`DrawFrame` 与 FrameTimeline slice；缺行时不能把 NULL 当作 0，也不能用它替代 `jank_type` 对 SF/Display HAL 的分类。

## 四类常见问题怎样复核

### 标准 HWUI 页面：App Deadline Missed

建议按同一个应用令牌检查：

1. 实际开始时间是否已经晚于预期开始时间；
2. `Choreographer#doFrame` 内 INPUT、ANIMATION、TRAVERSAL、COMMIT 哪段变长；
3. `DrawFrame` / RenderThread 是 CPU 提交慢，还是 GPU 获取栅栏晚；
4. `dequeueBuffer` 是否因旧缓冲区尚未释放而等待；
5. 对应 DisplayFrame 是否又叠加 SF 或 Display HAL jank。

SurfaceFrame `gpu_composition = false` 只表示该图层没有被 SF 放入客户端合成，不能排除 HWUI 生成缓冲区时的 GPU 延迟。

### SurfaceView 或游戏：画面节奏不稳

不要假定原生引擎一定把 `Choreographer.FrameData` 正确传到了目标 Surface。验证令牌存在后，再沿独立图层检查：

```text
AChoreographer / engine tick
  → EGL/Vulkan submit
  → queueBuffer + acquire fence
  → BufferTX / latch
  → HWC present + present fence
```

这条序列用来定位“逻辑时钟晚、GPU 完成晚、缓冲区到达晚、SF 没有采纳、显示后段晚”中的具体一段。缓冲区早于目标时间就绪通常只是留出排队余量，不能仅凭“早”判为帧节奏错误。

### 大量 `gpu_composition = true`

这只说明 SF 频繁使用 CLIENT 合成路径。要证明它造成截止时间超期，还需要同时看到：

- `SurfaceFlinger GPU Deadline Missed` 或相符的截止时间记录；
- client target GPU fence signal 偏晚；
- RenderEngine/GPU 轨迹与该 DisplayFrame 时间重叠；
- 排除 App 自己的 GPU、HWC validate、Display HAL 或频率切换。

优化方向应根据触发 CLIENT 的具体图层状态确定。盲目移除 `ColorMatrix`、改成 `SurfaceView` 或强制使用硬件叠加层，可能改变透明度、保护内容、颜色管理与生命周期语义，而且 HWC 仍可在下一帧返回不同结果。

### 应用与 SF 都已就绪，但送显仍晚

当应用 `on_time_finish = true`、SF CPU/GPU 也在截止时间内就绪，而 DisplayFrame 仍迟到并标记 `Display HAL`，排查重点应移到 HWC/DRM/厂商显示栈、刷新率或显示模式切换。送显栅栏能给出显示侧时间锚点，但不能继续细分面板扫描与光学响应。

## 一套不跳阶段的诊断顺序

1. **确认问题窗口与刷新率**
   记录显示模式、render rate、输入事件和用户看到的现象，排除启动、旋转、亮灭屏与模式切换瞬态。

2. **确认生产者与承载对象**
   标出应用窗口、TextureView、SurfaceView、相机/视频/游戏的生产者、BufferQueue、图层名称与进程。

3. **选择一个异常令牌**
   同时查看 Expected/Actual、prediction、present、jank、severity、layer 与 flow，不按颜色直接归因。

4. **检查应用就绪边界**
   对照 `doFrame`、RenderThread、queue time 与 acquire fence，区分 CPU、Producer GPU 和 dequeue wait。

5. **检查 SF 是否采纳新内容**
   对照 QUEUE、`BufferTX`、LATCH 与待处理缓冲区。已经入队但本轮没有锁存，说明问题仍在显示前段。

6. **检查 CLIENT/DEVICE composition**
   用 SurfaceFrame/DisplayFrame 的 `gpu_composition` 找到候选，再以 validate、RenderEngine 和 GPU 栅栏证明成本。

7. **检查送显与缓冲区归还**
   送显栅栏解释显示更新，释放栅栏/回调解释缓冲区复用。二者不能交换。

8. **用相邻稳定帧复核**
   比较同一图层的正常帧与异常帧，确认结论可重复，并排除一次性的预测或显示模式变化。

## Android 12 到 Android 17 的版本边界

| 平台 | 可验证边界 |
|---|---|
| Android 12 / API 31 | FrameTimeline 开始提供应用/SF 的预期与实际时间线，是这里覆盖的最低版本 |
| Android 13 / API 33 | 公开 `Choreographer.FrameData` / FrameTimeline 查询能力；原生与自定义渲染仍要把令牌随目标帧传下去 |
| Android 14 / API 34 | 应用窗口→BLAST→SF→HWC 的公共主线继续成立；独立 Surface 与混合页面仍需额外的缓冲区/栅栏证据 |
| Android 15 / API 35 | `SurfaceControl.Transaction.setFrameTimeline(vsyncId)` 等公开能力让自管事务可表达帧时间线；它不生成缓冲区，也不消除栅栏等待 |
| Android 16 / API 36 | 令牌、预期值/实际值与 CLIENT/DEVICE 判读方法继续适用 |
| Android 17 / API 37 | 源码锚点为 `Scheduler/FrameTimeline.{h,cpp}`、当前 BLAST、CompositionEngine 与 HWC `presentOrValidate`/validate 路径 |

表中“源码位于某目录”只描述 Android 17 当前结构，不表示该文件到 Android 17 才出现。涉及更早版本时，应切换到对应标签核查函数位置和字段，不能用当前目录结构推断版本演进。

## 源码核对清单

- [`FrameTimeline.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.h) 与 [`FrameTimeline.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Scheduler/FrameTimeline.cpp)
  - 核对 SurfaceFrame/DisplayFrame 的预测、Actual end、present、jank 分类与 `gpu_composition` 写入。
- [`Layer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Layer.cpp) 与 [`FrameTracer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrameTracer/FrameTracer.cpp)
  - 核对 DEQUEUE/QUEUE、ACQUIRE_FENCE、LATCH、FALLBACK_COMPOSITION、PRESENT_FENCE 的生产调用点。
- [`BLASTBufferQueue.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp) 与 [`FrameTimelineInfo.aidl`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/aidl/android/gui/FrameTimelineInfo.aidl)
  - 核对帧编号、`vsyncId` 与应用时序信息怎样进入缓冲区事务。
- [`graphics_frame_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/android/graphics_frame_event.proto) 与 [`frame_timeline_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/android/frame_timeline_event.proto)
  - 核对协议枚举、令牌关系、送显/预测/卡顿字段及实验字段警告。
- [Perfetto FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)
  - 核对界面轨迹、颜色、SurfaceView 覆盖限制、SQL 基础表与数据源名称。
- [`dma-fence.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/dma-fence.h) 与 [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)
  - 核对 Android 17 内核锚点下的栅栏信号/等待与同步文件基础，不把用户态帧分类等同于内核耗时。

## 小结

FrameTimeline 把预测、应用就绪、SurfaceFlinger 显示工作与实际送显放进同一套令牌关系。可靠结论需要同时守住四个边界：

- SurfaceFrame 的实际结束时间取入队与获取栅栏信号时间中的较晚者，不表示上屏时间；
- DisplayFrame 的实际切片延伸到送显，不能当作 SF 主线程 CPU 时长；
- `gpu_composition` 描述 SF 的 CLIENT 合成边界，不描述应用是否使用 GPU；
- 独立 Surface、Camera、视频、游戏与混合页面必须补充 layer、BufferQueue 和 fence。

按 Producer → buffer → latch → composition → present → release 的顺序检查，才能把“帧晚了”缩小为可由源码与 trace 共同复现的问题。
