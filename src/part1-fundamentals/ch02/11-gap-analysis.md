---
title: "Android 17 SurfaceFlinger GPU 帧追踪三段式架构"
chapter: "2.11"
status: ready-for-review
drafted_date: "2026-07-08"
applicable_versions: "Android 15 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-08"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/TimeStats/TimeStats.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Jank/JankTracker.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/Layer.cpp"
  - type: aosp
    path: "external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto"
  - type: aosp
    path: "external/perfetto/protos/perfetto/trace/gpu/gpu_counter_event.proto"
  - type: deepresearch
    path: "DeepResearch/2026-07-07-android17-gpu-debug-tools-deep-dive.md"
  - type: deepresearch
    path: "DeepResearch/2026-07-06-android17-gpu-debug-performance-tools-source.md"
tags: ["Android-17", "ch02", "源码分析", "性能优化", "FrameTracer", "TimeStats", "JankTracker", "GPU调试"]
related_chapters: ["2.10", "2.51", "13.19", "14.8", "14.28"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-08"
gap_source: "AOSP结构"
---

# 2.11 Android 17 SurfaceFlinger GPU 帧追踪三段式架构

## 复核范围

顶部 `applicable_versions` 中的“Android 15 (API 34)”是旧稿映射错误；正确对应为 Android 14 / API 34、Android 15 / API 35、Android 16 / API 36、Android 17 / API 37。该字段原文为 Hermes 兼容而保留，正文按正确映射解释。

FrameTracer、TimeStats 和 JankTracker 都位于 SurfaceFlinger，但服务于不同消费者：

| 组件 | 输出 | 粒度 | 适合回答的问题 |
|---|---|---|---|
| FrameTracer | Perfetto `GraphicsFrameEvent` packet | layer/buffer event | 某个 buffer 在 queue、fence、latch、composition、present 等边界经历了什么 |
| TimeStats | statsd pull atom 与 SurfaceFlinger time stats | global/per-layer 聚合 | 一段采样期内有多少帧、直方图和 jank 分类 |
| JankTracker | `IJankListener` Binder callback | per-layer `JankData` batch | 已注册监听者怎样接收运行时 jank 数据 |

它们不是 GPU profiler，也不能替代 GPU queue、counter、frequency、fence 和 shader/frame capture。三者会描述相邻的 frame/jank 现象，不能写成“完全不重叠”；启用数据采集后也会产生 packet、锁、容器、后台任务或 Binder 开销。

GPU/显示工具的主入口已经整理到：

- [2.15 Android 17 GPU 图形调试工具链](../ch02-rendering/2.15-android17-gpu-debug-tools.md)
- [2.51 GPU Trace 数据源与 Trace Processor](../ch02-rendering/2.51-android17-gpu-debug-performance-tools.md)
- [2.52 帧诊断工具边界](../ch02-rendering/2.52-android17-gpu-debug-performance-tools.md)
- [18.20 渲染管线分析方法](../../part2-performance/ch18-rendering-pipelines/20-pipeline-analysis-methodology.md)

本页只解释 Android 17 中三个 SurfaceFlinger 组件的源码边界。

## 1. FrameTracer：layer/buffer 事件写入 Perfetto

`FrameTracer` 注册自定义 Perfetto data source。SurfaceFlinger 在 layer 生命周期和 buffer 处理路径调用 `traceTimestamp()`/`traceFence()`，生成 `GraphicsFrameEvent`。

Android 17 的 proto 定义了这些 `BufferEventType`：

| 值 | 事件 |
|---|---|
| 1/2/3 | `DEQUEUE`、`QUEUE`、`POST` |
| 4/5 | `ACQUIRE_FENCE`、`LATCH` |
| 6/7 | `HWC_COMPOSITION_QUEUED`、`FALLBACK_COMPOSITION` |
| 8/9 | `PRESENT_FENCE`、`RELEASE_FENCE` |
| 10—13 | `MODIFY`、`DETACH`、`ATTACH`、`CANCEL` |

proto 枚举表示 trace packet 能表达的事件集合，不表示每个 layer、每帧都会产生全部事件。实际事件取决于调用路径、data source 是否启用、layer 是否已登记、fence 状态和 trace 配置。

### Fence 事件

`traceFence()` 读取 `FenceTime`：

- fence 已 signal 时，可以按 signal time 写 span；
- fence 仍 pending 时，记录进入对应 layer/buffer 的 pending list；
- 后续事件触发 `tracePendingFencesLocked()` 时再次检查；
- signal time 无效，或超过 `kFenceSignallingDeadline` 的旧 pending 项，不会按正常事件继续写入。

因此，trace 中没有 fence span不能直接证明系统没有 fence。data source、pending 清理、layer 生命周期和 capture 时间窗都可能影响可见结果。

### 成本边界

Perfetto data source 和 `mTraceTracker` 检查提供 disabled fast path；启用后仍会执行：

- `FenceTime` 状态读取；
- mutex 与 map/vector 操作；
- trace packet 构造和 shared-memory 写入。

旧稿中的“120 Hz × 8 layer 固定 1%—3% CPU”没有设备、layer 行为、trace buffer 与实现版本，不能复用为通用开销。

## 2. TimeStats：statsd 聚合统计

`TimeStats::onPullAtom()` 处理两个 atom id：

- `10062`：`SURFACEFLINGER_STATS_GLOBAL_INFO`；
- `10063`：`SURFACEFLINGER_STATS_LAYER_INFO`。

代码在第一次 global/layer pull 结束后调用 `enable()`。在此之前，多数 record 方法以 `if (!mEnabled.load()) return` 快速返回，所以首次完整 pull 可能为空或数据很少。

启用后，TimeStats 记录 global frame 计数、composition strategy、refresh-rate switch、RenderEngine duration，以及 per-layer post/acquire/latch/present 等时间与直方图。一次 pull 会序列化并清理对应聚合数据。它适合统计采样期，不提供每个 CPU/GPU 命令的逐帧执行栈。

“首行 atomic load”只能说明 disabled fast path 很短。启用状态下仍有 mutex、map、histogram 和 serialization 成本，因此不能称为零开销。

## 3. JankTracker：监听者回调

Android 17 的 `JankTracker` 按 layer id 管理 `IJankListener`：

- `sListenerCount == 0` 时，`onJankData()` 直接返回；
- 有监听者时，把处理提交给 low-priority `BackgroundExecutor`；
- 对应 layer 没有监听者时，后台任务丢弃数据；
- 单 layer 累积到 `kJankDataBatchSize = 50` 时自动 flush；
- 调用方也可以显式 `flushJankData()`，所以每次回调不保证恰好 50 条；
- listener 消失或 Binder 返回 null-pointer exception 时，tracker 会移除对应注册。

这些行为减少 SurfaceFlinger 合成线程上的同步工作，但数据搬运、容器和 listener Binder IPC 仍然存在。Copyright 2024 只能说明文件版权起始年份，不能据此认定 Android 17 是“第二个主版本”或推导稳定性。

## 4. GPU counter 是另一条数据通路

`GpuCounterEvent` proto 支持两种 descriptor：

1. `GpuCounterDescriptor` 使用 global counter id，Android GPU vendor 为满足相关 CDD/CTS 约束采用该模式；
2. `InternedGpuCounterDescriptor` 通过 sequence-scoped iid 支持多 producer/multi-GPU 等复杂场景。

这个协议定义 counter 的传输与 descriptor，不会统一不同 GPU 的硬件 counter 语义。Adreno、Mali、PowerVR 或其他 GPU 可以暴露不同名字、单位、采样周期和权限条件。跨设备比较要选择可比指标并记录 driver/firmware，不能只按相似轨道名换算“GPU 利用率”。

FrameTracer 的 `GraphicsFrameEvent` 与 GPU counter 也不能互相替代：

- FrameTracer 给出 layer/buffer 生命周期边界；
- GPU counter 描述 producer 提供的硬件活动/计数；
- GPU frequency 表示时钟状态；
- GPU queue/fence 表示提交和完成关系；
- AGI frame capture 用于单帧 API/shader/render-pass 分析。

## 5. 使用顺序

### 单帧晚显示

1. 用 FrameTimeline 或目标 present 找到异常帧；
2. 确定 Producer、Surface、layer 和 display；
3. 对齐 `queueBuffer`、acquire fence、latch、composition 与 present；
4. 需要 GPU 归因时补 GPU queue、frequency/counter、fence 或 AGI；
5. 用 CPU scheduler/thermal 轨道检查提交线程与 SurfaceFlinger 是否获得资源。

### 长期 jank 比例

1. 明确统计窗口、display mode、应用版本和场景；
2. 使用 TimeStats/FrameTimeline 聚合统计；
3. 按 app/SF、CPU/GPU、buffer stuffing、prediction/display 等分类分组；
4. 回到代表帧 trace 验证聚合分类；
5. 修改后以同一场景与窗口复测。

### 运行时 listener

1. 确认 API/权限和目标 layer；
2. 记录注册、flush、remove 与进程生命周期；
3. 不把 batch callback 时间当成单帧发生时间；
4. 用 `frameVsyncId` 等标识与显示轨迹对齐。

## 6. 原稿中需撤销的结论

- FrameTracer、TimeStats、JankTracker 不是 Android 17 新增的统一 GPU 调试框架；
- 三条通路没有“独立零开销”保证；
- JankTracker 的 50 是自动 flush threshold，显式 flush 可发送更小 batch；
- proto 注释不能证明所有 OEM 暴露同一 counter 集；
- SurfaceFlinger property 的默认值与 vendor overlay/composition 行为要按目标 build 核对；
- FrameTracer event、TimeStats atom 和 Jank callback 不应强行放进同一张逐帧 SQL 表。

## 7. 固定源码入口

- [`FrameTracer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/FrameTracer/FrameTracer.cpp)
- [`TimeStats.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/TimeStats/TimeStats.cpp)
- [`JankTracker.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Jank/JankTracker.cpp)
- [`Layer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/services/surfaceflinger/Layer.cpp)
- [`graphics_frame_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/android/graphics_frame_event.proto)
- [`gpu_counter_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/gpu/gpu_counter_event.proto)

本页结论固定到 `android-17.0.0_r1`。GPU counter、property、driver trace、AGI 能力和 permission 仍需按目标设备与工具版本确认。
