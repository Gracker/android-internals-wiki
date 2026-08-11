---

title: "BufferQueue 阻塞的 Perfetto 识别"
chapter: "13.14"
section: "13.14"
status: finalized
drafted_date: "2026-05-17"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-10"
last_verified_against: "Perfetto FrameTimeline docs; AOSP android-17.0.0_r1 BufferQueueProducer/Consumer/Core; android-15/16 release comparison for BUFFER_RELEASE_CHANNEL boundary"
last_task2b_lite_at: "2026-05-30"
confidence: medium
pipeline_stage: ready-to-publish
task6_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-07-10"
finalized_by: "openclaw-task6-auto-promote"
finalized_date: "2026-07-10"
task6_result: pass-light-edit
task9_state: reviewed
sources:
- type: material
  path: OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-bufferqueue-dequeueblocking-mechanism-detail.md
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/docs/data-sources/frametimeline.md
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueCore.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/include/gui/BufferReleaseChannel.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Layer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferStuffing.md
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-15.0.0_r1/libs/gui/BufferQueueProducer.cpp
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
tags: [perfetto, bufferqueue, frametimeline, jank, surfaceflinger, rendering]
related_chapters: ["2.13", "2.16", "7.4", "18.20"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/章节深挖"
gap_score: 19
material_count: 4
source_refs: 
 - OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-bufferqueue-dequeueblocking-jank-perfetto.md
 - OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-bufferqueue-dequeueblocking-mechanism-detail.md
 - https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/libs/gui/BufferQueueProducer.cpp
 - https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/libs/gui/BufferQueueConsumer.cpp
 - https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/libs/gui/BufferQueueCore.cpp
 - https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:frameworks/native/libs/gui/include/gui/BufferQueueCore.h
task9_result: auto-fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_at: "2026-07-10T06:37:44+08:00"
last_task9_review_log: "logs/deep-review/2026-07-10-06-audit.md"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: "2026-05-28T08:50:00+08:00"
rework_date: "2026-05-28"
rework_by: openclaw-task2b
review_notes: "2026-05-28 task2b: corrected BUFFER_RELEASE_CHANNEL version boundary; 2026-07-10 Task9 verified Android 16 flag path and Android 17 release notify path."
last_task6_at: "2026-07-10T08:12:38+08:00"
last_task6_review_log: "logs/review/2026-05-28-09-review.md"
last_task6_audit: "2026-06-22"
task6_l1_l2_fixes: 9
task6_l3_l4_issues: 0
task6_review_notes: "2026-07-10 Task6 revisiting-review: pass-light-edit;L1 banned word fix (对齐/链路);outline covered;无 L3/L4 回炉项。Task9 auto-fixed 已确认。"
task6_reviewed_by: openclaw-task6
task6_reviewed_at: "2026-07-10T08:12:38+08:00"
updated_by: openclaw-task9
updated_date: "2026-07-10"
last_task9_at: "2026-07-10T06:36:58+08:00"
task9_review_notes: "2026-07-10 Task9 idle-audit AUTO-FIX: P0 0 / P1 1 / P2 0;修正 BufferQueue release notify 版本边界与源码锚点到 android-17.0.0_r1: Android 16 为 BUFFER_RELEASE_CHANNEL flag 形态,Android 17 保留 waitForBufferRelease/notifyBufferReleased 路径且最终 notify_all;回到 Task6 复审。详见 logs/deep-review/2026-07-10-06-audit.md。 | 2026-05-28 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0;Task6 已通过且 queue 无 pending,自动晋升 finalized。"
last_task9_audit: "2026-07-10"
last_task9_autofix_at: "2026-07-10"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-16
---

# 13.14 BufferQueue 阻塞的 Perfetto 识别

平台源码锚点是 Android 17 / API 37、`android-17.0.0_r1`；涉及调度状态与 fence 内核语义时，锚点是 `android17-6.18-2026-06_r6`。Android 12—16 只用于解释版本演进。

Perfetto 文档把 `Buffer Stuffing` 定义为一种队列状态：App 在前一帧尚未 present 时继续提交新帧，未显示的 buffer 增加，后续帧即使按时完成也会带着额外延迟。队列耗尽后，Producer 还可能进入 `dequeueBuffer()` 等待。这个分类不能单独证明 App 绘制超时，也不能直接指出哪一条 BufferQueue 阻塞。

可靠诊断需要把 FrameTimeline、目标 layer、Producer 线程、BLAST 计数器、SurfaceFlinger 帧和 release 时刻放进同一时间窗。开始查询前还要确认出图拓扑：

- 标准 HWUI 窗口的 RenderThread 把宿主 App Window buffer 交给窗口 BLAST 队列；
- SurfaceView 内容拥有独立 Surface、BufferQueue 和 SurfaceFlinger child layer，宿主窗口与内容队列不能合并归因；
- TextureView 先由外部 Producer 写 SurfaceTexture，再由宿主 HWUI 采样进 App Window，至少要区分输入队列与宿主窗口队列；
- Camera、视频和游戏的 Producer 可能跨进程，并且可以有不同的排队策略。

BufferQueue 的 slot 与 fence 基础见 2.13、2.16 节；标准窗口、SurfaceView、TextureView、混合渲染和 Camera 的路径选择见 18.20 节。

## 从 FrameTimeline 找到目标 Surface

Android 12 起，FrameTimeline 在 App 和 SurfaceFlinger 两侧提供 Expected / Actual Timeline。App `Actual Timeline` slice 从 `Choreographer#doFrame` 或 `AChoreographer_vsyncCallback` 开始，结束点取 GPU 完成与 post 到 SurfaceFlinger 两者中较晚的时刻。Perfetto 对 `Buffer Stuffing` 的定义是：App 在前一帧尚未 present 时继续提交新帧，BufferQueue 中待显示的 buffer 逐渐积压。

排查时先读取四组字段：

| 字段 | 含义 | 用途 |
|---|---|---|
| `surface_frame_token` | App SurfaceFrame token | 关联 App `doFrame`、RenderThread slice |
| `display_frame_token` | SurfaceFlinger display frame token | 关联 SF `Actual Timeline` 和 flow |
| `jank_type` | 帧分类字符串 | 筛选 `Buffer Stuffing` |
| `layer_name` | 该帧对应的 Layer / Surface | 区分主窗口、视频、Camera、SurfaceView 等独立 Surface |

先按 `jank_type` 找候选帧，再用 `upid`、`layer_name` 和两个 token 追 App SurfaceFrame 与 DisplayFrame。同名 layer 可能来自不同实例或生命周期，能够取得 layer id、track id、BufferQueue 名或 frame number 时要一并记录。

FrameTimeline 文档明确标注 SurfaceView 尚未完整支持。SurfaceView 主体内容应优先使用独立 child layer、对应 Producer、BufferQueue frame number、acquire/release fence 和 SurfaceFlinger present 复原；不能因为缺少 App Actual Timeline slice 就判定它没有更新。TextureView 的 App FrameTimeline 主要描述宿主窗口，外部 SurfaceTexture 输入帧仍要另行关联。UI 颜色会随版本与主题调整，报告中应保存 `jank_type` 原始字符串。

## `dequeueBuffer` 为什么会等

`android-17.0.0_r1` 的 `BufferQueueProducer::dequeueBuffer()` 会调用 `waitForFreeSlotThenRelock()`。源码中有两类等待条件：

1. 找不到可复用的 free buffer 或 free slot；
2. 快速断开重连等场景造成 `mQueue.size() > getMaxBufferCountLocked()`。

阻塞模式下，Producer 进入虚函数 `waitForBufferRelease()`。Android 17 有两种实现：

- 通用 `BufferQueueProducer` 仍在 `mDequeueCondition` 上执行 `wait()` 或带超时的 `wait_for()`；
- App Window 使用的 `BBQBufferQueueProducer` 覆盖了该函数，通过 `BufferReleaseReader::readBlocking()` 在 `BufferReleaseChannel` 上等待。这个通道是 SurfaceFlinger 到 App 的 Unix domain socket，消息携带 `ReleaseCallbackId`、release fence 和当前 `maxAcquiredBufferCount`；`eventfd` 用于因其它释放原因中断阻塞读取并重新检查 slot。

非阻塞或 async 模式满足源码条件时返回 `WOULD_BLOCK`。Producer 已经 dequeue 到上限时返回 `INVALID_OPERATION`，这和等待空闲 slot 是不同分支。Android 17 的 BLAST 覆盖函数带有 `ATRACE_CALL()`，因此外层 `dequeueBuffer` 内可能出现嵌套的 `waitForBufferRelease` slice；通用队列未必有这条内层 slice。

Trace 中应组合检查这些信号：

- `RenderThread` 或原生渲染线程出现 `dequeueBuffer`、`waitForBufferRelease`、EGL swap 或 HWUI 提交 slice；
- 同一线程的 `thread_state` 与等待窗口重叠；条件变量和 `epoll_wait` 常表现为 `S`，`D` 往往指向另一类内核或驱动等待；
- App Actual Timeline 出现 `Buffer Stuffing`，目标 layer 的 BLAST 计数器同期变化；
- SurfaceFlinger 侧的 acquire、latch、composition、present 或 release 能解释 buffer 何时返回；
- App/SF deadline 字段与 `present_type` 能排除单纯的 App CPU 超时。

CPU 采样主要覆盖线程正在运行的时段，通常无法给睡眠区间提供完整用户态调用栈。它适合观察进入等待前的执行路径；等待点本身应依赖明确的 slice、`thread_state`、内核阻塞原因或可符号化的调试 trace。

`AppDeadlineMissed` 常见于主线程、RenderThread 或 GPU 工作超过预算。BufferQueue 背压的观察点更靠近 buffer 获取、提交和回收，但两者可以同时出现：下游合成变慢会把压力传回 Producer，Producer 等待又会扩大 App 帧时长。

Android 17 还把 BLAST 的等待时长回调到 `Choreographer.onWaitForBufferRelease()`。等待超过上一帧间隔的一半时，Choreographer 会标记 stuffed 状态；后续 `doFrame()` 可以主动延迟一帧，让排队深度下降，并在恢复期间调整动画时间。Perfetto 中可搜索 `Buffer stuffing recovery`、`buffer stuffed` 和 `Negative offset`。这些事件说明系统正在降低生产节奏，不代表 CPU 执行变慢。

## 三种“积压”信号不能当成同一个队列长度

Android 17 的 `BLASTBufferQueue.cpp` 为每个实例建立 `QueuedBuffer - <name>BLAST#<id>` 计数器。源码写入的值是：

`mNumFrameAvailable + mNumAcquired - mPendingRelease.size()`

这个计数器描述 App 进程内 BLAST 的内部状态，不等同于 `BufferQueueCore::mQueue.size()`。公式中的 `mNumFrameAvailable` 是等待 BLAST 消费的可用 frame 数，`mNumAcquired` 是 BLAST 已取得的 buffer 数，`mPendingRelease` 是 BLAST 暂存的 release 回调。相减后的值不能直接翻译成 QUEUED slot 数。

另一个常见计数器是 SurfaceFlinger 侧的 `BufferTX - <layerName>`。`Layer` 在 buffer transaction 到达服务端时增加该值，在 latch 或 drop 时减少。它描述尚未 latch/drop 的服务端 buffer transaction，也不是 App BufferQueue 的 slot 数。

| 信号 | 所在层 | 能回答什么 |
|---|---|---|
| FrameTimeline `Buffer Stuffing` | App SurfaceFrame 分类 | App 持续生产而前帧尚未 present，输入延迟已经增加 |
| `QueuedBuffer - <name>BLAST#<id>` | App 进程 BLAST | BLAST 内部 available、acquired 与 pending-release 的组合变化 |
| `BufferTX - <layerName>` | SurfaceFlinger `Layer` | buffer transaction 到达服务端后是否及时 latch 或 drop |
| `BufferQueueCore::mQueue.size()` | 某条 BufferQueue 内部 | 该队列的 queued `BufferItem` 数；常规 Perfetto trace 不直接给出这个成员 |

结合源码公式判读 `QueuedBuffer`：

- 计数器上升：可用帧或 acquired buffer 数量增加，释放进度没有同步抵消；
- 计数器长时间高位：BLAST 处理、SurfaceFlinger 消费或 release 回调可能落后，也要检查同步 transaction 是否暂时阻止 BLAST 消费；
- 计数器上升后 `dequeueBuffer` 变长：下游积压已经向 Producer 传导；
- 计数器已回落而渲染仍停顿：检查 release fence、GPU/driver 等待、线程调度和应用锁。

多个 Surface 同时更新时，应把计数器名、`layer_name`、layer id、BufferQueue 名和 frame token 配对。主窗口的 `Buffer Stuffing` 不能自动归因给同进程的视频 layer。

## Producer 到 display 的证据时间线

这张时序骨架描述 Android 17 App Window 的 BLAST 路径，读图时要分清 App 进程内的 BufferQueue Consumer 与 SurfaceFlinger 的 layer transaction。

```text
App / RenderThread Producer
  dequeueBuffer → 绘制或提交 GPU 命令 → queueBuffer(buffer, acquire fence)
      ↓
App 进程 / BLASTBufferQueue Consumer
  onFrameAvailable → acquireBuffer → 写入 SurfaceControl.Transaction
      ↓
SurfaceFlinger / 目标 Layer
  接收 buffer transaction → 判断可用性 / latch → composition → present
      ↓
RenderEngine / HWC
  返回该 layer 的 release fence；display 另有 present fence
      ↓
SurfaceFlinger → BufferReleaseChannel
  ReleaseCallbackId + release fence + max acquired count
      ↓
App 进程 / BLASTBufferQueue
  releaseBufferCallback → BufferQueueConsumer::releaseBuffer
      ↓
App / Producer
  slot 可复用；dequeueBuffer 返回 release fence，复写前遵守 fence
```

`BufferQueueConsumer::releaseBuffer()` 会把非 shared slot 从 `mActiveBuffers` 移到 `mFreeBuffers`，随后调用 `notifyBufferReleased()`。通用 `BufferQueueCore` 用它唤醒 `mDequeueCondition`；BLAST 专用 `BBQBufferQueueCore` 用它中断 `BufferReleaseReader`，促使等待方重新检查 slot。`BufferQueueCore` 维护 `mFreeSlots`、`mFreeBuffers`、`mActiveBuffers` 和 `mQueue`，任何唤醒都不保证当前线程立刻拿到 slot。

release fence 还要单独理解。slot 回到 Producer 后可能携带尚未 signal 的 fence；图形栈在复写 buffer 前必须遵守该 fence。slot 等待回答“有没有可复用 buffer”，fence 等待回答“这个 buffer 何时安全可写”，两种等待在 trace 中不能混为一类。

present fence 与 per-layer release fence 也不能合并。present fence 描述本次 display present 的完成边界；per-layer release fence 描述 HWC 或 RenderEngine 不再读取某个 layer buffer 的边界。若 SF 对应帧及时 present、release 消息很快返回，`dequeueBuffer` 长窗口就要继续查 fence、调度或应用同步。若 buffer transaction 到达后长期未 latch，两个 BLAST 计数器同期升高，release 又明显延后，BufferQueue 背压的证据才闭合。

## 多 Surface 场景

视频列表、Camera 预览和混合渲染页面往往有多条内容生产路径。分析前先列出每个 Producer、Consumer、BufferQueue、SurfaceControl layer、宿主关系和最终 DisplayFrame。

| 场景 | 队列拓扑 | 检查重点 |
|---|---|---|
| 标准列表或纯 Compose 页面 | 宿主 HWUI → App Window BLAST | 从主线程、RenderThread、宿主 `QueuedBuffer` / `BufferTX` 和 App SurfaceFrame 建立单窗口证据 |
| SurfaceView 视频 | 宿主 App Window 与视频 child layer 各有队列 | 分开归因宿主交互与视频内容；FrameTimeline 不能完整代表 SurfaceView 主体 |
| TextureView 视频 | 视频 Producer → SurfaceTexture；宿主 HWUI → App Window BLAST | 分开检查外部输入队列与宿主窗口队列；SF 通常只看到最终宿主 layer |
| CameraX 预览 | Camera/HAL Producer 写 Preview Surface；载体可能是 SurfaceView 或 TextureView | 先确认实际载体，再沿 request/result、buffer fence、预览队列和最终 layer 关联 |
| 多窗口或 Popup/Dialog | 每个 ViewRoot/窗口拥有自己的 App Window BLAST | 同进程、同 RenderThread 不代表共用 BufferQueue；按窗口 layer 与 BLAST id 分组 |

只有完成对象对应后，token、计数器和 `dequeueBuffer` 才能进入同一条证据时间线。跨 layer、跨窗口或跨 TextureView 两套队列拼接事件，会把同时发生误写成因果关系。

## 容易混淆的四类等待

1. **App 执行超时**：`doFrame`、`performTraversals`、RecyclerView bind 或 Binder 回调超过预算，dequeue 窗口没有明显等待。
2. **GPU 或 fence 等待**：GPU 写入、SF/HWC 读取或 release fence 尚未完成，证据落在 fence、GPU timeline 和 driver wait。
3. **SF/HWC 合成慢**：SF Actual Timeline 变长，jank type 指向 `SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed` 或 `DisplayHAL`。Producer 等待可能是下游变慢的反馈。
4. **应用同步或 Binder 等待**：渲染相关线程卡在应用锁、Binder transaction 或资源加载，时间窗与 BufferQueue release 对不上。

BufferQueue 背压需要同一 layer 上的成组证据：`Buffer Stuffing`、BLAST 计数器高位、Producer 等待以及可解释的 acquire/present/release 延迟。报告应逐项列出目标 layer/BufferQueue 身份、候选帧 token、`QueuedBuffer` 与 `BufferTX` 变化、等待 slice、线程状态、latch/present/release 时间，并为每个数值附上 SQL 行、时间区间或截图。缺少队列身份时只能写“同进程等待与该帧重叠”，不能写成目标 Surface 已经确认阻塞。

## Android 15、16、17 的源码边界

三个标签的通用算法都在 `waitForFreeSlotThenRelock()` 中重新检查 slot，但等待传输机制已经变化：

| 平台标签 | 通用 BufferQueue | App Window BLAST 队列 |
|---|---|---|
| `android-15.0.0_r1` | 直接等待 `mDequeueCondition`，释放点调用 `notify_all()` | 沿用条件变量路径 |
| `android-16.0.0_r1` | `BUFFER_RELEASE_CHANNEL` 分支启用时经虚函数进入通用条件变量实现；关闭时仍在调用点直接等待条件变量 | 同一开关启用时，`BBQBufferQueueProducer` 覆盖 `waitForBufferRelease()` 并读取 release 通道；关闭时回到条件变量 |
| `android-17.0.0_r1` | 无条件调用虚函数，默认实现仍等待 `mDequeueCondition` | `BufferReleaseChannel` 成为无条件实现；BLAST 覆盖函数用 `epoll_wait` 读取 release 消息，`BBQBufferQueueCore` 用 `eventfd` 中断等待 |

Android 17 的通道消息带有明确的 `ReleaseCallbackId` 与 release fence，SurfaceFlinger 可经该通道把 release 结果直接送到对应 BLAST 客户端。这个变化只覆盖使用 BLAST 专用 Producer 的队列；SurfaceTexture、ImageReader 或其它通用 BufferQueue 仍可能走条件变量。源码结构变化也不能证明某台设备已经消除 BufferQueue 阻塞，Perfetto 仍要核对等待时长、目标队列、release fence 和下游帧时序。

## PerfettoSQL：先找候选帧

这条查询从 App Actual Timeline 中筛出 Buffer Stuffing，并保留进程、layer 与两个 token：

```sql
SELECT
  afts.ts,
  afts.dur,
  afts.upid,
  afts.surface_frame_token AS app_token,
  afts.display_frame_token AS sf_token,
  afts.jank_type,
  afts.on_time_finish,
  afts.present_type,
  afts.layer_name,
  process.name AS process_name
FROM actual_frame_timeline_slice AS afts
LEFT JOIN process USING (upid)
WHERE afts.surface_frame_token != 0
  AND LOWER(afts.jank_type) GLOB '*buffer*stuff*'
ORDER BY afts.ts;
```

查询结果回答哪个进程、哪个 layer、哪些 token 进入候选集合。`on_time_finish = 1` 也可能出现 `Buffer Stuffing`，因为 App 可以按期完成，但排队使帧延迟 present。`jank_type` 仍要原样保留，便于核对分析器版本和 UI 展示。

## PerfettoSQL：关联同进程的 dequeue slice

以下查询把 Producer 等待限制到同一 `upid`，并要求 slice 与 App Actual Timeline 精确重叠。它同时覆盖 Android 17 的外层 `dequeueBuffer`、BLAST 内层 `waitForBufferRelease` 和 Android 16 release 通道路径的 `waiting for free buffer`：

```sql
WITH stuffing AS (
  SELECT
    ts,
    dur,
    surface_frame_token AS app_token,
    display_frame_token AS sf_token,
    layer_name,
    upid
  FROM actual_frame_timeline_slice
  WHERE LOWER(jank_type) GLOB '*buffer*stuff*'
),
producer_wait AS (
  SELECT
    slice.ts,
    slice.dur,
    slice.name,
    thread.utid,
    thread.name AS thread_name,
    process.name AS process_name,
    process.upid
  FROM slice
  JOIN thread_track ON slice.track_id = thread_track.id
  JOIN thread USING (utid)
  JOIN process USING (upid)
  WHERE slice.dur > 0
    AND (
      LOWER(slice.name) GLOB '*dequeuebuffer*' OR
      LOWER(slice.name) GLOB '*waitforbufferrelease*' OR
      LOWER(slice.name) GLOB '*waiting for free buffer*'
    )
)
SELECT
  stuffing.ts AS stuffing_ts,
  stuffing.dur / 1e6 AS stuffing_dur_ms,
  stuffing.layer_name,
  stuffing.app_token,
  stuffing.sf_token,
  producer_wait.utid,
  producer_wait.process_name,
  producer_wait.thread_name,
  producer_wait.name AS wait_slice,
  producer_wait.dur / 1e6 AS wait_ms
FROM stuffing
JOIN producer_wait
  ON producer_wait.upid = stuffing.upid
 AND producer_wait.ts < stuffing.ts + stuffing.dur
 AND stuffing.ts < producer_wait.ts + producer_wait.dur
ORDER BY stuffing.ts, producer_wait.dur DESC;
```

只比较 slice 起点会漏掉从窗口前开始、持续到窗口内的等待；不约束 `upid` 会误关联其他进程的同名 slice。查询结果仍是候选集：同一进程可能拥有多个窗口、SurfaceView 或 TextureView 队列，厂商渲染后端也可能使用不同的 slice 名称。还要用 layer、BLAST id、thread track、frame number 和相邻计数器确认队列身份。

## PerfettoSQL：核对线程状态

这条查询直接裁切每个候选等待 slice 对应的线程状态，不再用固定线程名或人为时间窗口：

```sql
WITH producer_wait AS (
  SELECT
    slice.id AS wait_slice_id,
    slice.ts,
    slice.dur,
    slice.name AS wait_slice,
    thread_track.utid
  FROM slice
  JOIN thread_track ON slice.track_id = thread_track.id
  WHERE slice.dur > 0
    AND (
      LOWER(slice.name) GLOB '*dequeuebuffer*' OR
      LOWER(slice.name) GLOB '*waitforbufferrelease*' OR
      LOWER(slice.name) GLOB '*waiting for free buffer*'
    )
),
intersection AS (
  SELECT
    producer_wait.wait_slice_id,
    producer_wait.wait_slice,
    producer_wait.utid,
    thread_state.state,
    thread_state.io_wait,
    thread_state.blocked_function,
    MIN(producer_wait.ts + producer_wait.dur,
        thread_state.ts + thread_state.dur) -
      MAX(producer_wait.ts, thread_state.ts) AS overlap_dur
  FROM producer_wait
  JOIN thread_state
    ON thread_state.utid = producer_wait.utid
   AND thread_state.dur > 0
   AND thread_state.ts < producer_wait.ts + producer_wait.dur
   AND producer_wait.ts < thread_state.ts + thread_state.dur
)
SELECT
  intersection.wait_slice_id,
  intersection.wait_slice,
  thread.utid,
  thread.name AS thread_name,
  process.name AS process_name,
  intersection.state,
  intersection.io_wait,
  intersection.blocked_function,
  SUM(intersection.overlap_dur) / 1e6 AS overlap_ms
FROM intersection
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE intersection.overlap_dur > 0
GROUP BY
  intersection.wait_slice_id,
  intersection.wait_slice,
  thread.utid,
  thread.name,
  process.name,
  intersection.state,
  intersection.io_wait,
  intersection.blocked_function
ORDER BY intersection.wait_slice_id, overlap_ms DESC;
```

`Running` 表示正在 CPU 上执行，`R` 表示可运行但等待 CPU，`R+` 表示被抢占后的可运行状态，`S` 表示可中断睡眠，`D` 表示不可中断睡眠。Android 17 的 release 通道使用 `epoll_wait`，通用条件变量通常落在 futex 路径，两者常见状态都是 `S`。

`blocked_function` 主要来自内核 `sched_blocked_reason` 事件，对 `D` 状态更有帮助。字段为 `NULL` 可能是线程处于可中断睡眠、事件未采集或内核符号不可见，不能反向证明没有等待。线程状态只说明调度层发生了什么，仍需和等待 slice、release 消息与目标队列相互印证。

## 小结

BufferQueue 背压需要一组时间上闭合的证据：FrameTimeline 提供排队状态，layer 与 BLAST id 确认目标队列，Producer 线程暴露等待，`QueuedBuffer` / `BufferTX` 描述两侧积压，SurfaceFlinger、HWC 和 release 通道解释 buffer 返回过程。缺少队列身份、release 或 display 时序时，应写成“疑似 BufferQueue 背压”，并列出还需补采的数据。

## 源码与官方资料

- [Android 17 Perfetto FrameTimeline 文档](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/docs/data-sources/frametimeline.md)
- [Android 17 BufferQueueProducer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)
- [Android 17 BufferQueueConsumer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp)
- [Android 17 BufferQueueCore](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueCore.cpp)
- [Android 17 BLASTBufferQueue](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
- [Android 17 BufferReleaseChannel](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/include/gui/BufferReleaseChannel.h)
- [Android 17 SurfaceFlinger Layer release](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/Layer.cpp)
- [Android 17 Buffer stuffing 设计说明](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferStuffing.md)
- [Android 17 Choreographer recovery](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [Android 16 BufferQueueProducer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/libs/gui/BufferQueueProducer.cpp)
- [Android 16 BLASTBufferQueue](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
- [Android 15 BufferQueueProducer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-15.0.0_r1/libs/gui/BufferQueueProducer.cpp)
- [Kernel 6.18 `sched_blocked_reason`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
- [Kernel 6.18 dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
