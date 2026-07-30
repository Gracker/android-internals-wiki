---

title: "BufferQueue 阻塞的 Perfetto 识别"
chapter: "13.15"
section: "13.15"
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
 - type: official
 - type: official
 - type: aosp
 - type: aosp
 - type: aosp
 - type: aosp
 - type: aosp
 - type: material
 - type: material
path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-03-bufferqueue-dequeueblocking-mechanism-detail.md"
tags: [perfetto, bufferqueue, frametimeline, jank, surfaceflinger, rendering]
related_chapters: ["2.13", "2.16", "7.15", "18.20"]
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

# 13.15 BufferQueue 阻塞的 Perfetto 识别

Perfetto 中的 `Buffer Stuffing` 描述队列积压状态。App 仍在提交新帧，前一批 buffer 尚未按时 present，输入到上屏的延迟可能逐帧增加。这个标签本身不能证明 App 绘制代码超时，也不能直接定位到某个 Surface。

可靠诊断需要把 FrameTimeline、目标 Layer、RenderThread、BLASTBufferQueue counter、SurfaceFlinger 帧以及 release 时刻放进同一时间窗。BufferQueue 的 slot 和 fence 机制可回到 2.13、2.16 节；跨渲染路径的选择见 18.20 节。

## 从 FrameTimeline 找到目标 Surface

Android 12 起，FrameTimeline 在 App 和 SurfaceFlinger 两侧提供 Expected / Actual Timeline。App `Actual Timeline` slice 从 `Choreographer#doFrame` 或 `AChoreographer_vsyncCallback` 开始，结束点取 GPU 完成与 post 到 SurfaceFlinger 两者中较晚的时刻。Perfetto 对 `Buffer Stuffing` 的定义是：App 在前一帧尚未 present 时继续提交新帧，BufferQueue 中待显示的 buffer 逐渐积压。

排查时先读取四组字段：

| 字段 | 含义 | 用途 |
|---|---|---|
| `surface_frame_token` | App 帧 token | 关联 App `doFrame`、RenderThread slice |
| `display_frame_token` | SurfaceFlinger display frame token | 关联 SF `Actual Timeline` 和 flow |
| `jank_type` | 帧分类字符串 | 筛选 `Buffer Stuffing` |
| `layer_name` | 该帧对应的 Layer / Surface | 区分主窗口、视频、Camera、SurfaceView 等独立 Surface |

先按 `jank_type` 找候选帧，再按 `layer_name` 收窄 Surface，随后用两个 token 追 App 帧和 display frame。UI 颜色会随版本与主题调整，不能作为稳定查询接口；报告中应保存 `jank_type` 原始字符串。

## `dequeueBuffer` 为什么会等

`android-17.0.0_r1` 的 `BufferQueueProducer::dequeueBuffer()` 会调用 `waitForFreeSlotThenRelock()`。源码中有两类等待条件：

1. 找不到可复用的 free buffer 或 free slot；
2. 快速断开重连等场景造成 `mQueue.size() > getMaxBufferCountLocked()`。

阻塞模式下，producer 进入 `waitForBufferRelease()`，在 `mDequeueCondition` 上执行 `wait()` 或带超时的 `wait_for()`。非阻塞或 async 模式满足源码条件时会返回 `WOULD_BLOCK`。producer 已经 dequeue 到上限时则返回 `INVALID_OPERATION`，这和等待空闲 slot 是两条不同分支。

Trace 中应组合检查这些信号：

- `RenderThread` 或原生渲染线程出现较长的 `dequeueBuffer`、EGL swap 或 HWUI 提交 slice；
- 同一窗口的 `thread_state` 进入 `S`（可中断睡眠）或 `D`（不可中断睡眠），并与 dequeue 窗口重叠；
- App Actual Timeline 出现 `Buffer Stuffing`，目标 Layer 的 BLAST counter 同期升高；
- SurfaceFlinger 侧的 acquire、latch、composition、present 或 release 能解释 buffer 何时返回；
- App/SF deadline 字段与 `present_type` 能排除单纯的 App CPU 超时。

CPU 采样主要覆盖线程正在运行的时段，通常无法给睡眠区间提供完整用户态调用栈。它适合观察进入等待前的执行路径；等待点本身应依赖明确的 slice、`thread_state`、内核 blocked reason 或可符号化的调试 trace。

`AppDeadlineMissed` 常见于主线程、RenderThread 或 GPU 工作超过预算。BufferQueue 背压的观察点更靠近 buffer 获取、提交和回收，但两者可以同时出现：下游合成变慢会把压力传回 producer，producer 等待又会扩大 App 帧时长。

## `QueuedBuffer - <layer>` 不是原始队列长度

Android 17 的 `BLASTBufferQueue.cpp` 为每个实例建立 `QueuedBuffer - <name>BLAST#<id>` counter。源码写入的值是：

`mNumFrameAvailable + mNumAcquired - mPendingRelease.size()`

这个 counter 反映 BLAST 侧尚未消化的压力，不等同于 `BufferQueueCore::mQueue.size()`。结合源码公式判读：

- counter 上升：frame available 或 acquired 数量增加，释放进度没有同步抵消；
- counter 长时间高位：BLAST/SF 处理或 release callback 可能落后；
- counter 上升后 `dequeueBuffer` 变长：下游积压已经向 producer 传导；
- counter 已回落而渲染仍停顿：检查 release fence、GPU/driver 等待、线程调度和应用锁。

多个 Surface 同时更新时，应把 counter 名、`layer_name` 和 frame token 配对。主窗口的 `Buffer Stuffing` 不能自动归因给同进程的视频 Layer。

## Producer 到 display 的证据时间线

下面的时序图用于标出每一段应寻找的 trace 证据：

```text
App / RenderThread
  dequeueBuffer → 绘制或提交 GPU 命令 → queueBuffer
      ↓
BLASTBufferQueue / BufferQueue
  queued buffer 等待 acquire / latch
      ↓
SurfaceFlinger
  acquireBuffer → latch → composition → present
      ↓
HWC / Display
  present fence signal
      ↓
SurfaceFlinger / Consumer
  releaseBuffer → slot 回到 free buffers
      ↓
App / Producer
  下一次 dequeueBuffer 重新检查可用 slot
```

`BufferQueueConsumer::releaseBuffer()` 会把非 shared slot 从 `mActiveBuffers` 移到 `mFreeBuffers`，随后调用 `notifyBufferReleased()`。`BufferQueueCore` 维护 `mFreeSlots`、`mFreeBuffers`、`mActiveBuffers` 和 `mQueue`。producer 被唤醒后仍要持锁重新检查条件，唤醒并不保证当前线程立刻拿到 slot。

release fence 还要单独理解。slot 回到 producer 后可能携带尚未 signal 的 fence；图形栈在复写 buffer 前必须等待该 fence。条件变量等待解决“有没有可复用 slot”，fence 等待解决“这个 buffer 是否已经安全可写”，两种等待在 trace 中不能混为一类。

如果 SF 对应帧及时 present、consumer 很快 release，`dequeueBuffer` 长窗口就需要继续查 fence、调度或应用同步。如果 `queueBuffer` 后很久才被 acquire/latch，同时 BLAST counter 高位，BufferQueue 背压的证据更完整。

## 多 Surface 场景

视频列表、Camera 预览和混合渲染页面往往有多个 Surface 参与合成。分析前先列出主窗口、视频 Surface、Camera preview、WebView/GL Surface 对应的 Layer。

| 场景 | 常见 trace 形态 | 检查重点 |
|---|---|---|
| RecyclerView 内嵌播放器 | 主窗口产生滚动帧，视频有独立 Layer | 确认 `Buffer Stuffing` 属于哪个 Layer，再检查 Surface 重建、尺寸变化和滚动时序 |
| SurfaceView 视频 | 视频与 App 主窗口分属不同 Surface | 分开归因主窗口 jank 和视频 Layer jank |
| TextureView 视频 | 视频纹理进入 App 渲染路径 | 联合查看 `updateTexImage`、RenderThread、GPU busy 和主窗口 BLAST counter |
| CameraX 预览 | camera producer、preview Surface、App UI 可能跨线程或跨进程 | 用 Layer 名、进程轨道和 preview counter 建立对应关系 |

只有完成 Layer 对应后，token、counter 和 `dequeueBuffer` 才能进入同一条证据时间线。跨 Layer 拼接事件会把相关性误写成因果关系。

## 容易混淆的四类等待

1. **App 执行超时**：`doFrame`、`performTraversals`、RecyclerView bind 或 Binder 回调超过预算，dequeue 窗口没有明显等待。
2. **GPU 或 fence 等待**：GPU 写入、SF/HWC 读取或 release fence 尚未完成，证据落在 fence、GPU timeline 和 driver wait。
3. **SF/HWC 合成慢**：SF Actual Timeline 变长，jank type 指向 `SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed` 或 `DisplayHAL`。producer 等待可能是下游变慢的反馈。
4. **应用同步或 Binder 等待**：渲染相关线程卡在应用锁、Binder transaction 或资源加载，时间窗与 BufferQueue release 对不上。

BufferQueue 背压需要同一 Layer 上的成组证据：`Buffer Stuffing`、BLAST counter 高位、producer 等待以及可解释的 acquire/present/release 延迟。报告可写成：

> `playerSurface` 连续 6 帧被标为 `Buffer Stuffing`；对应 BLAST counter 在 3 个 VSync 内保持高位；同进程 RenderThread 的 dequeue slice 与窗口重叠 18.4 ms；SF display frame 晚一个 VSync present，consumer release 发生在等待结束前。

其中每个数值都应能回到 SQL 行、时间选择区间或截图。

## Android 15、16、17 的源码边界

这三个标签使用同一个条件变量，差异主要是封装和 flag 的生命周期：

| 平台标签 | 等待路径 | 唤醒路径 |
|---|---|---|
| `android-15.0.0_r1` | `waitForFreeSlotThenRelock()` 直接调用 `mDequeueCondition.wait()` / `wait_for()` | 多个释放点直接调用 `mDequeueCondition.notify_all()` |
| `android-16.0.0_r1` | `BUFFER_RELEASE_CHANNEL` flag 打开时调用 `waitForBufferRelease()`；函数内部仍等待 `mDequeueCondition` | flag 打开时调用 `notifyBufferReleased()`；函数内部仍执行 `notify_all()` |
| `android-17.0.0_r1` | `waitForBufferRelease()` 已成为无条件路径；内部仍等待 `mDequeueCondition` | `notifyBufferReleased()` 已成为无条件路径；内部仍执行 `mDequeueCondition.notify_all()` |

因此，`BUFFER_RELEASE_CHANNEL` 在 Android 16 表示迁移开关；Android 17 源码已去掉这些调用点外的 flag 分支。两个包装函数没有在上述标签中实现按 slot 或按 waiter 的定向 channel。只凭函数改名无法推出锁竞争下降，也无法推出 BufferQueue 阻塞已经被系统版本修复。

Perfetto 判读在三个版本上保持一致：观察等待时长、目标 Layer、consumer release 和下游帧时序。内部函数名只用于源码定位。

## PerfettoSQL：先找候选帧

下面的查询从 App Actual Timeline 中筛出 Buffer Stuffing，并保留进程、Layer 与两个 token：

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
WHERE LOWER(afts.jank_type) GLOB '*buffer*stuff*'
ORDER BY afts.ts;
```

查询结果回答哪个进程、哪个 Layer、哪些 token 进入候选集合。`jank_type` 仍要原样保留，便于核对分析器版本和 UI 展示。

## PerfettoSQL：关联同进程的 dequeue slice

下面的查询把 dequeue 候选限制到同一 `upid`，并用区间重叠判断代替“slice 起点落入窗口”。前后各留 30 ms 只用于初筛，报告时应根据刷新率和帧边界收紧：

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
dequeue_slice AS (
  SELECT
    slice.ts,
    slice.dur,
    slice.name,
    thread.name AS thread_name,
    process.name AS process_name,
    process.upid
  FROM slice
  JOIN thread_track ON slice.track_id = thread_track.id
  JOIN thread USING (utid)
  JOIN process USING (upid)
  WHERE LOWER(slice.name) GLOB '*dequeuebuffer*'
    AND slice.dur > 0
)
SELECT
  stuffing.ts AS stuffing_ts,
  stuffing.layer_name,
  stuffing.app_token,
  stuffing.sf_token,
  dequeue_slice.process_name,
  dequeue_slice.thread_name,
  dequeue_slice.name AS dequeue_slice,
  dequeue_slice.dur / 1e6 AS dequeue_ms
FROM stuffing
JOIN dequeue_slice
  ON dequeue_slice.upid = stuffing.upid
 AND dequeue_slice.ts < stuffing.ts + stuffing.dur + 30000000
 AND dequeue_slice.ts + dequeue_slice.dur > stuffing.ts - 30000000
ORDER BY stuffing.ts, dequeue_slice.dur DESC;
```

原查询若只比较 slice 起点，会漏掉从窗口前开始、持续到窗口内的等待；若不约束 `upid`，还会误关联其他进程的同名 slice。修正后的结果仍是候选集，因为厂商和渲染后端可能使用不同的 slice 名称。

## PerfettoSQL：核对线程状态

下面的模板默认检查整段 trace。把 `target_process`、`window_start` 和 `window_end` 替换成上一条查询得到的进程及绝对纳秒时间：

```sql
WITH params AS (
  SELECT
    'com.example.app' AS target_process,
    trace_start() AS window_start,
    trace_end() AS window_end
)
SELECT
  thread.name AS thread_name,
  process.name AS process_name,
  thread_state.ts,
  thread_state.dur / 1e6 AS dur_ms,
  thread_state.state,
  thread_state.io_wait,
  thread_state.blocked_function
FROM thread_state
JOIN thread USING (utid)
JOIN process USING (upid)
CROSS JOIN params
WHERE process.name = params.target_process
  AND thread.name = 'RenderThread'
  AND thread_state.dur > 0
  AND thread_state.ts < params.window_end
  AND thread_state.ts + thread_state.dur > params.window_start
ORDER BY thread_state.ts;
```

`Running` 表示正在 CPU 上执行，`R` 表示 runnable 等待 CPU，`S` 表示可中断睡眠，`D` 表示不可中断睡眠。`blocked_function` 来自可用的调度 blocked-reason 数据，可能因为事件未采集或符号不可见而为 `NULL`；它不是周期采样字段。线程状态只能说明调度层发生了什么，仍需和 dequeue slice 及 release 时刻相互印证。

## 小结

BufferQueue 背压需要一组时间上闭合的证据：FrameTimeline 提供队列状态，Layer 名锁定 Surface，RenderThread 暴露 producer 等待，BLAST counter 反映积压压力，SF/HWC/release 时间线解释 buffer 返回过程。证据缺口应明确标为“疑似 BufferQueue 背压”，再补录制配置、符号或源码定位。

## 源码与官方资料

- [Perfetto FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)
- [Android 17 BufferQueueProducer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp)
- [Android 17 BufferQueueConsumer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp)
- [Android 17 BufferQueueCore](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueCore.cpp)
- [Android 17 BLASTBufferQueue](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
- [Android 16 BufferQueueProducer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/libs/gui/BufferQueueProducer.cpp)
- [Android 15 BufferQueueProducer](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-15.0.0_r1/libs/gui/BufferQueueProducer.cpp)
