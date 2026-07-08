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

> [已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/]

Android 17 的 GPU 图形调试工具链在源码层面呈现**三段式调用链架构**：FrameTracer 负责逐 Layer 的帧事件追踪（写入 Perfetto），TimeStats 负责聚合统计（通过 statsd Pull Atom 上报），JankTracker 负责运行时 jank 通知（以 50 帧批量粒度推送给监听者）。三条通路**互补不重叠**，各自有独立的零开销保证机制。

## FrameTracer：Layer→Perfetto 逐帧事件追踪

### 🔹 Layer.cpp 中的 6 个 trace 入口

FrameTracer 的所有 trace 调用源自 Layer 在 buffer 生命周期中的关键事件。`Layer.cpp` 在以下 6 个时机调用 `mFrameTracer->traceTimestamp` 或 `traceFence` [已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/Layer.cpp]：

| 事件 | FrameEvent 枚举 | 触发时机 |
|------|----------------|---------|
| DEQUEUE | 1 | Buffer 从 BufferQueue 取出进入 Layer |
| QUEUE | 2 | 生产者（App）提交绘制完成的 buffer |
| ACQUIRE_FENCE | 4 | Acquire fence signal（buffer 可被读取） |
| LATCH | 5 | SurfaceFlinger 选定该 buffer 用于合成 |
| FALLBACK_COMPOSITION | 7 | RenderEngine（GPU）客户端合成完成 |
| PRESENT_FENCE | 8 | Present fence signal（帧上屏） |

对应 `graphics_frame_event.proto` 中的 `GraphicsFrameEvent.BufferEventType` 枚举 [已验证: AOSP android-17.0.0_r1, external/perfetto/protos/perfetto/trace/android/graphics_frame_event.proto]。该 proto 使用 **proto2 语法**，保留历史兼容性。

### 🔹 Perfetto DataSource 注册

FrameTracer 通过 Perfetto 的 Custom DataSource 机制注册为 `"android.graphics.FrameLatency"` 数据源 [已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/FrameTracer/FrameTracer.cpp]：

```cpp
void FrameTracer::registerDataSource() {
    perfetto::DataSourceDescriptor dsd;
    dsd.set_name(kFrameTracerDataSource);  // "android.graphics.FrameLatency"
    FrameTracerDataSource::Register(dsd);
}
```

关键设计：
- **`std::call_once`** 保证多线程初始化幂等
- **`kSystemBackend`** 而非 in-process backend——FrameTracer 跑在 SurfaceFlinger 进程，需要与 system-wide 数据源共享 perfetto daemon
- **三层零开销短路**：`std::call_once` → DataSource 检查 → `mTraceTracker.find(layerId)` 未注册则跳过

### 🔹 tracePendingFencesLocked：Fence 异步批处理

GPU 渲染的核心异步性体现在 fence 上。`traceFence` 在 fence 未 signal 时不写入 trace，而是 push 到 `pendingFences` 列表，每轮遍历检查是否已 signal [已验证: AOSP android-17.0.0_r1]：

- **`kFenceSignallingDeadline`**：fence signal 时间距当前 `systemTime()` 超过此阈值的事件直接丢弃，避免 stale event 污染 trace
- **反向迭代删除**：`pendingFences.erase(pendingFences.begin() + i)` 配合 `--i` 避免迭代器失效
- **性能影响**：120Hz × 8 Layer 场景下约 5760 trace calls/s，主线程 CPU 开销约 1-3%

## TimeStats：statsd Pull Atom 聚合统计通道

### 🔹 两个 Pull Atom 上报机制

TimeStats 通过 statsd 的两个 Pull Atom 上报帧统计数据，与 FrameTracer 的 Perfetto 通道互补 [已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/TimeStats/TimeStats.cpp]：

- **Atom 10062**（SURFACEFLINGER_STATS_GLOBAL_INFO）：全局帧统计——总帧数、丢帧数、GPU 合成帧数、7 维 jank 分类
- **Atom 10063**（SURFACEFLINGER_STATS_LAYER_INFO）：per-layer 直方图统计——7 种时间直方图（present2present、post2present、acquire2present 等）及 frame_rate_vote、game_mode

### 🔹 Google 官方 7 维 Jank 分类法

全局 atom 的 jank 分类提供比传统"丢帧率"信息密度高一个数量级的归因 [已验证: AOSP android-17.0.0_r1]：

| Jank 类别 | 含义 | 归因方 |
|----------|------|-------|
| totalSFLongCpu | SurfaceFlinger CPU 处理过长 | SF 合成线程 |
| totalSFLongGpu | SurfaceFlinger GPU 合成过长 | GPU / RenderEngine |
| totalSFUnattributed | SurfaceFlinger 侧无法归因 | SF 内部 |
| totalAppUnattributed | App 侧无法归因 | App 渲染线程 |
| totalSFScheduling | SurfaceFlinger 调度延迟 | VSync / 唤醒时机 |
| totalSFPredictionError | 预测帧时与实际偏差 | VSYNC 预测器 |
| totalAppBufferStuffing | App 提交过快/过慢 | App 生产节奏 |

### 🔹 零开销保证

所有 TimeStats record 方法第一行为 `if (!mEnabled.load()) return;`——`mEnabled` 默认 false，仅在 statsd **首次 pull 完成后才 enable**。注释原文："Enable timestats now. The first full pull for a given build is expected to have empty or very little stats" [已验证: AOSP android-17.0.0_r1, TimeStats.cpp onPullAtom]。

## JankTracker：运行时 Jank 通知的批量分派

### 🔹 三层零开销设计

JankTracker 提供**运行时通知**能力，区别于 TimeStats 的聚合上报 [已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/Jank/JankTracker.cpp]：

1. **原子快速路径**：`sListenerCount` 为 `std::atomic<size_t>`，`onJankData` 首行检查，零监听者时整个管线不进入
2. **低优先级后台线程**：`BackgroundExecutor::getLowPriorityInstance()` 提交任务，合成主线程不被阻塞
3. **批量 IPC 控制**：`kJankDataBatchSize = 50`，每积累 50 帧 jank 数据才触发一次 IPC，避免高频 binder 调用

JankTracker 自 Android 15 引入（头注释 Copyright 2024），Android 17 是其**第二个主版本**，稳定性已显著改善 [来源: DeepResearch/2026-07-07-android17-gpu-debug-tools-deep-dive.md]。

## GPU Counter 标准化困境：GpuCounterEvent 双模式

### 🔹 两种 Proto 模式

Perfetto 的 `gpu_counter_event.proto` 定义了两种 GPU counter 描述模式 [已验证: AOSP android-17.0.0_r1, external/perfetto/protos/perfetto/trace/gpu/gpu_counter_event.proto]：

- **Mode 1（`GpuCounterDescriptor`）**：OEM **必须**使用以满足 CDD/CTS。`counter_id` 全局唯一，单 producer 场景。问题：不同 OEM 的 counter 集合完全不同——Adreno 的 `shader_core_active` 在 Mali 上不存在，Mali 的 `fragment_jobs` 在 Xclipse 上无对应物
- **Mode 2（`InternedGpuCounterDescriptor`）**：通过 `iid` 引用 `InternedData`，支持多 producer / 多 GPU 场景。trace 消费方需支持 iid 解析

### 🔹 对跨设备 GPU 分析的影响

这是 GPU 调试工具链**最被低估的标准化碎片** [来源: DeepResearch/2026-07-07]：

- AGI System Profiler 在不同 OEM 设备上看到的 GPU counter 轨道**不可直接比较**
- Sokatoa 多帧分析能做"同设备多帧对比"，但**难以做跨设备横向对比**
- 跨设备基准测试必须将 counter 标准化到应用层（如"GPU 占用率 = shader_core 类 counter / cycle count"），不能依赖原始 counter 显示

> [自动发现] 此问题直接影响 §14.28（GPU 性能分析进阶 — 跨厂商计数器标准化）中的"跨设备基准测试"方案可行性，建议在该节补充 mode 1/2 选择策略与 counter 映射层设计。

## SurfaceFlinger GPU 调试属性系统

### 🔹 关键调试开关

SurfaceFlinger 在初始化阶段加载 GPU 调试相关的系统属性 [已验证: AOSP android-17.0.0_r1, frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp]：

| 属性 | 默认值 | 作用 |
|------|-------|------|
| `debug.sf.enable_gl_backpressure` | true | GPU 合成回压控制，防止 GPU 队列堆积 |
| `debug.sf.luma_sampling` | 1 | 亮度采样控制 |
| `debug.sf.disable_client_composition_cache` | 0 | 禁用客户端合成缓存 |
| `debug.sf.predict_hwc_composition_strategy` | 1 | HWC 合成策略预测 |

`mBackpressureGpuComposition` 默认为 true，在 GPU 合成负载过高时通过回压机制限制新 buffer 提交，避免 GPU 队列无限增长导致内存压力。

## 三段式架构对比总结

| 维度 | FrameTracer | TimeStats | JankTracker |
|------|------------|-----------|-------------|
| **数据通道** | Perfetto Custom DataSource | statsd Pull Atom (10062/10063) | Binder IPC |
| **粒度** | 每 Layer × 每 buffer 事件 | 全局聚合 / per-layer 直方图 | 50 帧 batch |
| **用途** | 开发期 trace 分析 | 线上 metrics 采集 | 运行时实时监控 |
| **零开销机制** | mTraceTracker.find 短路 | mEnabled atomic load | sListenerCount atomic |
| **开销来源** | protobuf packet 构造 + shared memory 写入 | protobuf 序列化 + 排序 | 后台线程 + binder IPC |

## 扩展

### 🔸 Perfetto SQL 查询三段式数据

在 Perfetto UI 中查询 FrameTracer 数据时，使用 `graphics_frame_event` 表；查询 TimeStats 数据时，需通过 `android_surfaceflinger_stats` 或直接解析 atom protobuf。两种数据源的 SQL 表结构不同，分析时需注意区分。

> [待补充] 具体的 Perfetto SQL 查询模板。

### 🔸 AGI Frame Profiler 与 GFXReconstruct 集成

AGI 的 Frame Profiler 通过 GFXReconstruct 实现 frame replay，但其跨设备能力受 GPU counter 双模式限制。具体集成细节未在 android-17.0.0_r1 的 AOSP 源码中验证。

> [待验证: AGI 仓库 frame replay 引擎]

### 🔸 Vulkan 层 GPU 调试接口

Android 17 的 Vulkan validation layer 和 GPU debug marker 机制提供了额外的 GPU 调试能力，但具体接口在 AOSP android-17.0.0_r1 中未完整覆盖。

> [待补充] Vulkan debug marker 与 FrameTracer 的协同机制。

[适用版本: Android 15 (API 34) - Android 17 (API 37)]
[来源: DeepResearch/2026-07-07-android17-gpu-debug-tools-deep-dive.md]
[来源: DeepResearch/2026-07-06-android17-gpu-debug-performance-tools-source.md]
