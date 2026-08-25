---
title: GPU Counter、内存与 GpuService 可观测性
chapter: '15.12'
section: '15.12'
status: finalized
applicable_versions: Android 17 (API 37)（源码结论以 android-17.0.0_r1 为准；跨版本使用时需重新核对 proto 定义与导入实现）
tags:
- gpu
- profiling
- perfetto
- gpu-counter
- gpu-memory
- android17
- GPU
- GpuService
- GpuMem
- eBPF
- Perfetto
- statsd
- memory-tracking
- observability
related_chapters:
- '2.7'
- '14.7'
- '15.11'
- '10.3'
- '15.16'
- '13.9'
task6_state: reviewed
task9_state: reviewed
pipeline_stage: ready-to-publish
last_draft_polish_at: '2026-07-27T19:35:27+08:00'
last_draft_polish_run_id: 20260727-193527-draft-polish-30f4d38e
last_review_finalize_at: '2026-07-27T20:13:43+08:00'
last_review_finalize_run_id: 20260727-201343-4b671d13
last_rework_at: '2026-07-27T21:36:40+08:00'
last_rework_run_id: 20260727-213543-rework-30f4d38e
last_verified: '2026-08-20'
last_verified_against: AOSP android-17.0.0_r1 external/perfetto 的 9 个固定源码文件（含 GpuCounterSpec reserved tag 4 / deprecated unit 边界）；Writer rendering_pipelines S01/S02/S03/S04/S05/S11/S12/S13
last_idle_audit_at: '2026-08-20T18:37:07+08:00'
last_idle_audit_run_id: 20260820-183531-idle-audit-6c1cc491
confidence: high
sources:
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/common/gpu_counter_descriptor.proto'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/trace/gpu/gpu_counter_event.proto'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/config/gpu/gpu_counter_config.proto'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/config/data_source_config.proto'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/trace/android/gpu_mem_event.proto'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/importers/proto/gpu_event_parser.h'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/importers/proto/gpu_event_parser.cc'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql'
- type: aosp
  path: 'AOSP android-17.0.0_r1: external/perfetto/test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto'
- type: material
  path: Writer/rendering_pipelines/S01_rendering_types_overview.md
- type: material
  path: Writer/rendering_pipelines/S02_aosp_standard_type.md
- type: material
  path: Writer/rendering_pipelines/S03_surfaceview_type.md
- type: material
  path: Writer/rendering_pipelines/S04_textureview_type.md
- type: material
  path: Writer/rendering_pipelines/S05_mixed_rendering_type.md
- type: material
  path: Writer/rendering_pipelines/S11_camera_type.md
- type: material
  path: Writer/rendering_pipelines/S12_video_overlay_hwc_type.md
- type: material
  path: Writer/rendering_pipelines/S13_game_type.md
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/GpuService.cpp
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/gpumem/GpuMem.cpp
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/gpumem/include/gpumem/GpuMem.h
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/bpfprogs/gpuMem.c
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/tracing/GpuMemTracer.cpp
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/tracing/include/tracing/GpuMemTracer.h
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/gpustats/GpuStats.cpp
- type: aosp
  tag: android-17.0.0_r1
  path: frameworks/native/services/gpuservice/gpustats/include/gpustats/GpuStats.h
- type: aosp
  tag: android-17.0.0_r1
  path: hardware/interfaces/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part3-tools/ch15-other-tools/16-gpu-performance-profiling-advanced.md
- src/part3-tools/ch15-other-tools/19-android17-gpuservice-gpu-memory-observability.md
---

# GPU Counter、内存与 GpuService 可观测性

> **版本边界**：本文只讨论 Android 17 / `android-17.0.0_r1` 中可在 AOSP `external/perfetto` 核验的 GPU counter descriptor、GPU counter event、GPU memory event 与 Trace Processor 导入链路。跨厂商性能阈值、Ray Tracing（光线追踪）、NPU（神经网络处理器）/ML（机器学习）协同、远程 GPU 调试与完整 AGI 工作流不在讨论范围内。

下文沿用 Perfetto 源码名称：counter 是按时间记录的 GPU 指标样本；producer 是向 Perfetto 声明数据源并写入事件的实现；descriptor 是解释 counter ID、名称、单位和采样能力的元数据；Trace Processor 则把 trace packet（追踪数据包）解析成可查询的表与时间轨道。

GPU 可观测信号分为执行计数器、频率/利用率、内存当前量和分配时间线。Perfetto、GpuService、eBPF 与 statsd 覆盖的对象和时间粒度不同，查询前要先确定需要回答的问题。

## GPU Counter、频率与内存事件

### 要点

1. `GpuCounterDescriptor` 提供 counter 的协议级元数据：语义分组、度量单位、counter spec（单项指标说明）与硬件 counter block 容量约束。
2. `GpuCounterEvent` 有 descriptor 直挂与 interned descriptor 两种事件写入模式。interning 会把 descriptor 存入同一 packet 序列的数据表，后续事件只引用其 ID；多 producer / 多 GPU 场景可借此避免协调全局 counter ID。Android OEM 的 CDD（Android 兼容性定义文档）/ CTS（兼容性测试套件）合规路径则要求使用直挂 descriptor。
3. Trace Processor 在 `gpu_event_parser.h/.cc` 中维护 GPU counter track（时间序列轨道）与上一条 counter row（样本行）的状态，并把回看式采样值写回上一行；`android-17.0.0_r1` 不包含 `gpu_counter_sequence_state.h`。
4. `gpu_counter_span_view.sql` 用 `LEAD() OVER (PARTITION BY track_id ORDER BY ts)` 将 counter 采样点转为 span（带起止范围的区间），适合按 GPU track 计算持续时间。
5. `GpuMemTotalEvent` 位于 `protos/perfetto/trace/android/gpu_mem_event.proto`，由 Android `GpuService` 生成；`pid=0` 表示全局总量，其他 pid（进程 ID）表示进程归属。
6. `GpuCounterEvent` 不携带 pid、tid（线程 ID）、layer、FrameTimeline token（帧关联标识）或 GPU submission ID（GPU 提交批次标识）。单条 counter track 只能直接说明某个 `gpu_id` 上的设备级变化；归因到 App、SurfaceFlinger 或某一显示帧还需要其他时间线证据。

### `GpuCounterDescriptor`：协议层的描述结构

`protos/perfetto/common/gpu_counter_descriptor.proto` 把单个 counter spec、共享硬件资源的 counter block，以及 producer 的采样能力放在同一个 descriptor 中。

#### 语义分组

`GpuCounterGroup` 在 `android-17.0.0_r1` 中包含：

```text
UNCLASSIFIED = 0
SYSTEM       = 1
VERTICES     = 2
FRAGMENTS    = 3
PRIMITIVES   = 4
MEMORY       = 5
COMPUTE      = 6
RAY_TRACING  = 7
```

`GpuCounterSpec.groups` 若被 producer 填写，只能从该枚举取值；若未填写，Trace Processor 会按未分类 counter 处理。这个分组能表达 producer 对 counter 语义的声明，但不能单独证明不同厂商 counter 的跨设备等价性。

#### 度量单位

`MeasureUnit` 在协议中传输的枚举编号（wire value）从 `NONE = 0` 延伸到 `INSTRUCTION = 40`，覆盖 `BIT`、`BYTE`、`HERTZ`、`SECOND`、`VERTEX`、`PIXEL`、`TRIANGLE`、`PRIMITIVE`、`FRAGMENT`、`MILLIWATT`、`WATT`、`JOULE`、`VOLT`、`AMPERE`、`CELSIUS`、`PERCENT`、`INSTRUCTION` 等。`next id: 41` 只是提醒维护者从 41 分配下一个枚举编号，不是协议字段。派生单位由可重复出现的 `numerator_units` 和 `denominator_units` 组合，例如 `PIXEL / SECOND` 表示每秒像素。

#### Counter spec 字段边界

`GpuCounterSpec` 在 `android-17.0.0_r1` 中包含：

```text
counter_id
name
description
reserved 4  // deprecated MeasureUnit unit 的旧 tag，本版本不再作为可写字段
oneof peak_value {
  int_peak_value
  double_peak_value
}
numerator_units
denominator_units
select_by_default
groups
```

`reserved 4` 对应早期已弃用的 `MeasureUnit unit` tag；Android 17 的 Trace Processor 只按 `numerator_units` 与 `denominator_units` 生成单位字符串。`oneof peak_value` 表示整数峰值与浮点峰值最多选择一种。本版本标签（tag）的 `GpuCounterSpec` 不含 `value_direction` 字段，因此不能把 Perfetto 上游后续设计或其他分支字段写成 Android 17 已有协议字段。Trace Processor 的 `gpu_event_parser.cc` 把 GPU counter 视为回看式采样：收到时间戳 `t(n)` 的事件时，先在 `t(n)` 插入值为 0 的占位行，再把事件携带的 value 写入上一条 counter row。区间时长不在这一步回填，而由后面的 SQL span 视图计算。

#### Counter block 容量约束

`GpuCounterBlock { block_id, block_capacity, name, description, counter_ids }` 描述共享同一硬件计数资源组（block）的 counter，以及它们能同时启用的数量上限；`block_capacity` 未设置时表示不设上限。自动化脚本或 UI 选择 counter 时，应按 `block_id` / `block_capacity` 预先校验，不能只按名称列出后全部启用。proto 没有规定超限后的处理方式，因此无法统一断言 producer 会拒绝、轮转采样或不提示地丢弃部分选择。

### `GpuCounterEvent`：descriptor 直挂与 interned descriptor

`protos/perfetto/trace/gpu/gpu_counter_event.proto` 中的核心结构如下：

```proto
message GpuCounterEvent {
  oneof desc {
    GpuCounterDescriptor counter_descriptor = 1;
    uint64 counter_descriptor_iid = 4;
  }

  message GpuCounter {
    optional uint32 counter_id = 1;
    oneof value {
      int64 int_value = 2;
      double double_value = 3;
    }
  }

  repeated GpuCounter counters = 2;
  optional int32 gpu_id = 3;
}
```

`oneof desc` 表示直挂 descriptor 与 `counter_descriptor_iid` 最多出现一种；嵌套的 `oneof value` 同样最多携带整数值或浮点值中的一种。`iid` 是 interned ID，也就是查找已存 descriptor 的编号。源码注释区分两种事件写入模式：

- **Mode 1：descriptor 直挂**。`counter_descriptor = 1` 直接随事件发送。源码注释要求 Android OEM 使用这条路径满足 CDD/CTS 测试；每次 trace session（一次录制会话）的首个 packet 必须声明 descriptor。该模式的 counter ID 是全局编号，多 producer 必须自行协调。
- **Mode 2：interned descriptor**。`counter_descriptor_iid = 4` 引用 trusted sequence（Perfetto 可信 packet 序列）中的 `InternedGpuCounterDescriptor`，适合多 producer / 多 GPU 场景。descriptor 存在 `InternedData` 中，`sequence-scoped` 表示其 ID 只在该序列内有效；事件随后只传 `iid`，不再重复整份 counter spec。若 event 外层和 interned descriptor 都提供 `gpu_id`，以后者为准。

数据源配置入口在 `protos/perfetto/config/data_source_config.proto`：

```proto
optional GpuCounterConfig gpu_counter_config = 108 [lazy = true];
```

该字段对应的数据源名是 `gpu.counters`。`[lazy = true]` 是 protobuf 字段的延迟解码选项，只影响消息何时解析，不能据此推导 GPU data source 的启动时机或常驻状态。采集行为由 `GpuCounterConfig` 的以下字段表达：

- `counter_period_ns`：期望采样周期；descriptor 若声明了 `min_sampling_period_ns` 与 `max_sampling_period_ns`，配置应落在该 producer 支持的范围内；
- `counter_ids`：要采集的 counter id，含义以本次 producer descriptor 为准；
- `instrumented_sampling`：请求在 GPU command buffer（命令缓冲区）中插入计数器采样操作，使用前应检查 descriptor 的 `supports_instrumented_sampling`；
- `fix_gpu_clock`：请求在 trace 期间固定 GPU 时钟，会改变动态调频条件，不能与日常运行数据混为同一基线。

### Trace Processor 如何导入事件

`src/trace_processor/importers/proto/gpu_event_parser.h/.cc` 是 Android 17 基线下 GPU counter 事件导入的实际实现位置。每个 track 保存一串按时间排列的样本，`last_id` 指向该轨道上一条 counter row。头文件中可见两类记录方式：

```cpp
struct GpuCounterState {
  TrackId track_id;
  std::optional<tables::CounterTable::Id> last_id;
};
base::FlatHashMap<uint32_t, GpuCounterState> gpu_counter_state_;

// Track-level last_id for the interned counter_descriptor_iid path.
base::FlatHashMap<TrackId, std::optional<tables::CounterTable::Id>>
    gpu_counter_last_id_;
```

由此可以得到两个边界清晰的结论：

1. legacy inline（旧版内联）`counter_descriptor` 路径按全局 `counter_id` 维护 `GpuCounterState`。
2. interned `counter_descriptor_iid` 路径先从当前 packet sequence 查到 `InternedGpuCounterDescriptor`，再按 track 维护 `last_id`。

`android-17.0.0_r1` 不包含 `gpu_counter_sequence_state.h`；相关行为应以 `gpu_event_parser.h/.cc` 为准。

`PushGpuCounterValue()` 的写入顺序会影响 trace 首尾的解释。第一条事件只建立占位行，要等下一条事件到达后，前一个时间点的值才被写入；trace 结束前的末行可能仍是值为 0 的占位行。分析短 trace 或低频采样时，应检查首尾样本，不能把这个 0 自动解释为 GPU 空闲。

### SQL span 视图：从采样点到区间

`src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql` 先删除同名旧视图；其中负责创建区间视图的 `CREATE VIEW` 片段如下：

```sql
CREATE PERFETTO VIEW {{table_name}}_span AS
SELECT
  ts,
  LEAD(ts, 1, trace_end()) OVER (PARTITION BY track_id ORDER BY ts) - ts AS dur,
  gpu_id,
  value AS {{table_name}}_val
FROM counter c JOIN gpu_counter_track t
  ON t.id = c.track_id
WHERE name = '{{counter_name}}' AND gpu_id IS NOT NULL;
```

这段 SQL 的关键点是：

- `{{counter_name}}` 在 metric（Perfetto 指标查询）编译时替换为具体 counter 名。
- `LEAD()` 是 SQL 窗口函数；`PARTITION BY track_id` 让每条轨道分别计算，`ORDER BY ts` 再按时间排序。下一条采样点时间减去当前时间，就是当前 counter 值对应的持续区间。
- `gpu_id IS NOT NULL` 过滤掉非 GPU counter track。

这个视图片段只生成区间，不改变导入解析器已写入的 value。末行会延伸到 `trace_end()`；它若仍是解析器留下的 0 占位值，在求和、均值等聚合计算前，应按采样语义决定是否剔除。

`test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto` 展示了测试使用的 counter 名与单位组合，例如：

- `GPU Frequency`：`denominator_units: SECOND`，即频率类 counter。
- `Fragments / vertex`：`FRAGMENT / VERTEX`。
- `Fragment / Second`：`PIXEL / SECOND`。
- `Triangle Acceleration`：`TRIANGLE / (MILLISECOND · MILLISECOND)`。

这些是解析器的合成测试输入，可以验证名称、单位和 group 的导入结果；它们不构成设备 counter 清单，也不能外推为所有 Android 17 设备都必须暴露的跨厂商性能基准。其中 `Fragment / Second` 的名称使用 Fragment，结构化单位却写成 `PIXEL / SECOND`。分析真实 trace 时应同时保存名称和单位；二者冲突时要标记 descriptor 数据不一致，不能自行补成某个设备语义。

### GPU memory event：Android 平台 producer

`protos/perfetto/trace/android/gpu_mem_event.proto` 定义：

```proto
// Generated by Android's GpuService.
message GpuMemTotalEvent {
  optional uint32 gpu_id = 1;
  optional uint32 pid = 2;
  optional uint64 size = 3;
}
```

注释明确该事件由 Android 系统的 `GpuService` 生成。Trace Processor 的 `ParseGpuMemTotalEvent()` 按 `gpu_id` 建立 GPU 维度：`pid == 0` 时写入全局 GPU memory counter，其他 pid 则关联进程并写入进程 GPU memory counter。`size` 是该时间点的总量值，不是一次内存分配（allocation）的增量。

这条平台事件可以观察全局或进程归属的 GPU 内存总量，但不能替代厂商 GPU counter，也不能自动推出带宽、shader throughput（着色器处理吞吐量）、缓存命中率或功耗阈值。事件中的 pid 归属也不等同于物理页只有该进程持有；跨进程共享 buffer、驱动保留和显示系统引用，需要结合 `GpuService`、dma-buf（Linux 跨设备共享 buffer 的机制）与厂商工具解释。

### 把 counter 放回 Android 显示路径

#### 设备级 counter 没有内建的帧归属

`GpuCounterEvent.GpuCounter` 只有 `counter_id` 和一个数值，外层事件只增加 descriptor 与 `gpu_id`。协议里没有 pid、tid、SurfaceFlinger layer ID、BufferQueue frame number、FrameTimeline token 或 GPU submission ID。Trace Processor 因此创建的是设备级 GPU counter track，不会自动把 counter span 关联到某个 App 或某个显示帧。

这条边界会直接影响结论强度：

表中的 submission 是一次提交到 GPU queue 的工作批次；slice 是时间线上带开始和结束的事件。producer completion fence 在 producer 完成 buffer 写入后发出信号，传到 consumer 一侧时就是读取该 buffer 前等待的 acquire fence；release fence 通知 producer 何时可以安全复用旧 buffer；present fence 是一轮 display present 的系统时间锚点。

| 证据 | 可以确认 | 不能单独确认 |
| --- | --- | --- |
| GPU counter span | 某个 `gpu_id` 在该区间的频率、吞吐、利用率或厂商定义事件值发生变化 | 哪个进程、layer 或 command buffer 造成变化 |
| GPU render-stage / submission 事件 | 已被 producer 标注的 GPU 工作区间与提交关系 | 未标注工作属于哪个业务帧，或该帧已经显示 |
| App / RenderThread slice | CPU 何时准备、提交或等待 GPU 工作 | GPU 何时完成，SurfaceFlinger 是否采用该 buffer |
| producer completion / acquire fence | 对应 buffer 何时可由 consumer 安全读取 | 该 buffer 是否赶上目标 display present |
| FrameTimeline、layer 与 present | App/SF 帧、buffer/layer 选择及显示时序 | counter 峰值由哪条 shader、纹理或硬件单元产生 |

归因时要用时间重叠缩小候选范围，再用 submission、buffer、fence、layer 和 frame token 建立关系。仅凭“counter 峰值与卡顿同时出现”还不能得出因果结论。

#### 出图拓扑决定 counter 应该和谁对齐

以下判读表基于 Android 17 的显示模型。表中的“GPU counter”均指设备级轨道；厂商若提供更细的 context（GPU 执行上下文）、queue 或 stage 事件，可以继续细分。

先统一系统合成术语：SurfaceFlinger（SF）是 Android 系统合成器，layer 是它接收的一项独立合成输入，latch 表示 SF 选中该 layer 的新 buffer 参与当前合成。HWC（Hardware Composer）负责与显示硬件协商逐层合成；`DEVICE` 表示该 layer 由 HWC 的硬件能力处理，`CLIENT` 表示 SF 用 RenderEngine/GPU 合成。被分配为 CLIENT 的 layers 会先合成到一个结果 buffer，这块 buffer 叫 client target，再交给 HWC 与其他 DEVICE layers 一起完成显示。`BufferTX - <layerName>` 是 SF 侧待处理 buffer transaction 的计数轨道；BLAST child 是 SurfaceView 中实际承载内容 buffer 的子 layer。

各类 producer 还有自己的中间节点：HWUI/Skia 是 Android UI 的硬件加速绘制栈，`DeferredLayerUpdater` 是其 RenderThread 取得并更新 TextureView 最新 buffer 的组件；ISP（Image Signal Processor，图像信号处理器）处理相机像素；codec 是媒体编解码器；blitter 是做图像复制或格式转换的硬件单元；RHI（Render Hardware Interface）是游戏引擎对 OpenGL ES（GLES）、Vulkan 等图形 API 的抽象层。

| 出图路径 | 可能进入同一 GPU counter 的工作 | 需要同时核对的证据 | 常见误判 |
| --- | --- | --- | --- |
| 标准 View / Compose App Window | HWUI/Skia 绘制 App buffer；发生 CLIENT composition 时还包含 SurfaceFlinger RenderEngine | MainThread、RenderThread、GPU stage、App completion fence、宿主 `BufferTX`、SF composition type、present | 把 RenderThread duration 当成 GPU duration，或把所有 GPU 峰值算给 App |
| TextureView | 外部 producer 可能使用 GPU；宿主 HWUI 还要 acquire、采样外部 image 并写 App Window | 外部 BufferQueue 与 fence、`DeferredLayerUpdater`、宿主 GPU、宿主 layer、最终 composition | 只看到宿主 counter 变高，就断定外部视频、相机或地图 producer 变慢 |
| SurfaceView / 独立 Surface | 游戏或自研 renderer 的 GPU 工作；若该 layer 或同屏其它 layer 转为 CLIENT，还会增加 RenderEngine 工作 | 独立 BLAST child、producer fence、per-layer composition type、client target、release/present fence | `SurfaceView` 一定不占 GPU，或 DEVICE composition 等于 producer 没有 GPU 成本 |
| Camera / 普通视频 Surface | 主体像素可能由 ISP、codec、blitter 或其它硬件产生；TextureView、自研滤镜、CLIENT composition 才会额外引入可见 GPU 工作 | Camera/codec result、buffer timestamp、acquire fence、承载方式、HWC 逐层合成决策、present | GPU counter 低就表示预览/播放链路没有瓶颈 |
| 本地游戏 | engine submit、GPU queue execution、可能的 SurfaceFlinger CLIENT composition | Input、Game/Render/RHI、submission、producer fence、queue depth、latch、present | submit 返回等于 GPU 完成，或 FPS 稳定等于输入延迟低 |
| 混合出图 | 多个 producer、宿主采样与 RenderEngine 可能共享同一个 `gpu_id` | 每个 Surface/BufferQueue、目标 display 的可见 layer 集合、DEVICE/CLIENT 变化、各自 fence | 用一条全局 GPU track 给某个 layer 定责 |

TextureView 与独立 Surface 的差异尤其容易被 counter 隐藏。TextureView 输入进入宿主 HWUI 后，HWC 通常只看到最终 App Window；独立 Surface 保留单独 layer，HWC 可以逐层选择 DEVICE 或 CLIENT。某次 DEVICE→CLIENT 变化可能让 GPU counter 上升，但触发条件也许来自同屏 layer、透明度、变换、HDR（High Dynamic Range，高动态范围）、protected usage（受保护内容的 buffer 使用标记），或多个 layer 竞争有限的 HWC hardware plane（硬件叠加层资源）。此时不能只检查目标 App 的 shader。

Camera 和视频还存在相反情况：主体内容通过 ISP、codec 与 HWC 路径完成，GPU counter 可能保持很低，画面仍会因 HAL（Hardware Abstraction Layer，硬件抽象层）或 codec 输出晚、acquire fence 晚、requested present timestamp（producer 请求的显示时间）、HWC 或 display driver 延迟而错过显示。GPU counter 没有覆盖这些硬件阶段。

#### 一次可复用的关联顺序

1. 从异常的 display present 或 FrameTimeline actual frame（实际发生的帧时间线记录）选定时间窗口，记录 `display_frame_token`（关联 SurfaceFlinger DisplayFrame 的标识）、目标 layer 和 present 时间。
2. 按标准窗口、TextureView、独立 Surface、Camera/Video、Game 或混合页面建立 producer—BufferQueue—layer 对象表。
3. 沿目标 buffer 反查 producer CPU 工作、GPU submission/render stage、completion/acquire fence、`queueBuffer`、SF latch 与 composition type。
4. 在已经确定归属的 GPU 工作区间内读取 counter span，使用 descriptor 的名称、单位、group、采样周期和 block 配置解释数值。
5. 对比相同设备、相同 counter 配置、相同温度和显示模式下的基线。跨厂商、跨驱动或不同 counter 组合不直接比较绝对值。

这套顺序把 counter 放在逐帧证据之后。counter 适合回答“已定位的 GPU 区间为什么变重”，不适合跳过对象和同步关系直接回答“谁让这一帧卡了”。

### 采集与分析建议

1. **先看 descriptor，再解释数值**：分析 counter value 前，应先确认 `counter_id` 对应的 `name`、`numerator_units`、`denominator_units` 与 `groups`。
2. **尊重 block capacity**：批量启用 counter 时，应按 `GpuCounterBlock.block_capacity` 检查是否超出同一硬件 block 的同时采样能力。
3. **区分平台事件与厂商 counter**：`GpuMemTotalEvent` 是 Android 平台 GPU memory 事件；GPU 频率、fragment、triangle 等 counter 仍依赖 GPU counter producer 暴露。
4. **记录出图拓扑**：同一 counter 峰值在标准 HWUI、TextureView、独立 Surface 和视频 overlay（独立视频 layer 由 HWC 直接合成的路径）场景中的来源不同。采集说明至少记录 Surface 类型、layer、graphics API、HWC composition 与显示模式。
5. **不要强行跨厂商比较**：仅凭同属 `MEMORY`、`FRAGMENTS` 或 `COMPUTE` 分组不足以证明 counter 可比。若要建立跨设备基准，必须记录厂商 producer、counter 名称、单位和采样频率；若用不同名称作为同类指标，还要写明映射依据。
6. **控制 trace 体积**：样本数量近似为 `counter 数 × 采样频率 × 时长`，但 Protocol Buffers（protobuf）的 `int_value` 使用 varint（按数值大小改变字节数的整数编码）；`double_value`、嵌套 message（嵌套消息）、packet framing（数据包边界信息）、descriptor 与 interning 引用也有额外成本。不要用固定的“每项 12 bytes”推算容量；先做短时采集，测量生成 trace 的 bytes/s，再为目标时长设置 buffer 和采样周期。

### 范围外主题

下列主题需要另行补充 Android 17 基线下的一手材料或可复现实验后再写入正文结论：

- Adreno / Mali / PowerVR / Xclipse 的厂商 counter 私有命名表与等价映射。
- UI 渲染、游戏、视频、计算摄影等工作负载下的正常 / 警告 / 异常阈值。
- Vulkan Ray Tracing 管线开销与 Android 17 设备支持边界。
- NNAPI（Android 神经网络 API）、厂商 NPU / ML 加速器与 GPU 渲染负载之间的调度影响。
- `profileable`、权限、SELinux 访问控制或生产采集策略对 GPU counter 可见性的影响。
- AGI Frame Capture、Layer Override（图形 layer 替换）、GAPID 到 AGI 迁移等完整工具工作流。

### 信息源

所有源码引用均按 AOSP `android-17.0.0_r1` 中 `external/perfetto` 路径复核：

- [`protos/perfetto/common/gpu_counter_descriptor.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/common/gpu_counter_descriptor.proto)
- [`protos/perfetto/trace/gpu/gpu_counter_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/gpu/gpu_counter_event.proto)
- [`protos/perfetto/config/gpu/gpu_counter_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/config/gpu/gpu_counter_config.proto)
- [`protos/perfetto/config/data_source_config.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/config/data_source_config.proto)
- [`protos/perfetto/trace/android/gpu_mem_event.proto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/trace/android/gpu_mem_event.proto)
- [`src/trace_processor/importers/proto/gpu_event_parser.h`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/proto/gpu_event_parser.h)
- [`src/trace_processor/importers/proto/gpu_event_parser.cc`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/importers/proto/gpu_event_parser.cc)
- [`src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql)
- [`test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto)


## GpuService 数据源、时间线与驱动统计

通用计数器描述负载趋势，GpuService 进一步提供进程或驱动侧内存信号。当前量、事件时间线和累计统计不能混用。

Android 17（`android-17.0.0_r1`）中，`frameworks/native/services/gpuservice/` 承载多条 GPU 观测路径。这里的“可观测性”是把驱动上报的数值和事件提供给诊断工具，不表示 GpuService 负责管理这些内存。

GPU 内存路径从 `gpu_mem_total` tracepoint（内核或驱动预先定义的静态追踪事件）开始。`gpuMem.c` 中的 BPF 程序读取事件，把每个 GPU 与进程最近上报的当前总量写入 map；`GpuMem` 再读取 map，通过 dumpsys 和 Perfetto 暴露结果。

`GpuStats` 是另一条路径，只记录 GL、Vulkan、ANGLE 驱动加载和图形功能使用信息，并通过 dumpsys 与 statsd（Android 系统统计守护进程）输出；它不记录 GPU 内存字节。buffer 的分配、复用与回收仍由 gralloc（系统与厂商之间的图形 buffer 分配接口）、图形实现和厂商驱动负责。

平台侧核验基线是 `android-17.0.0_r1`，内核侧核验基线是 `android17-6.18-2026-06_r6`。Android 12 至 Android 16 只用于说明能力演进。

### 三条并列观测链路：GPU 内存总量与驱动统计要分开

GpuService 中与 GPU 内存和驱动状态相关的主体分为三条链路。前两条描述 GPU 内存当前总量及其时间变化，第三条描述驱动加载和功能使用：

| 链路 | 组件 | 输入 | 输出 / 消费方 | 适合回答的问题 |
| --- | --- | --- | --- | --- |
| 当前总量 | `GpuMem` + `gpuMem.c` BPF 程序 | GPU 驱动发出的 `gpu_mem/gpu_mem_total` tracepoint | `dumpsys gpu --gpumem`、`traverseGpuMemTotals()` | 每个 `(gpu_id, pid)` 最近上报的当前总量是多少？ |
| Perfetto 时间线 | `GpuMemTracer` + ftrace | BPF map 起始值；驱动后续发出的 tracepoint | Perfetto 的初始 `gpu_mem_total_event` 与持续 `gpu_mem/gpu_mem_total` 更新 | trace 开始时占用多少，随后怎样变化？ |
| 驱动统计 | `GpuStats` | GL / Vulkan / ANGLE 驱动加载与功能使用上报 | statsd pull atom、`dumpsys gpu --gpustats` | 驱动加载是否成功、耗时多久、使用了哪些图形功能？ |

这三个通道术语分别表示：

- BPF map：内核 BPF 程序与用户态共享的键值表；
- ftrace：把内核 tracepoint 事件写入 trace 的追踪机制；
- statsd pull atom：statsd 在采集时向数据提供方主动拉取的结构化记录。

`GpuMem` 持有只读 BPF map，`GpuMemTracer` 通过 `GpuMem::traverseGpuMemTotals()` 遍历它，Perfetto 的 ftrace 更新来自驱动的同一个 tracepoint ABI（事件字段与布局约定）。排查 GPU 内存增长时，GpuMem 与 Perfetto 负责占用趋势，GpuStats 只补充驱动选择和失败模式。

### GpuService 启动与初始化边界

`GpuService.cpp` 的构造函数同步创建核心对象，然后把可能阻塞的 BPF 初始化放到独立线程里。BPF 在这里指由内核校验后执行、用于处理 tracepoint 事件的小程序。下面的源码片段展示两条初始化线程：

```cpp
GpuService::GpuService()
    : mGpuMem(std::make_shared<GpuMem>()),
      mGpuWork(std::make_shared<gpuwork::GpuWork>()),
      mGpuStats(std::make_unique<GpuStats>()),
      mGpuMemTracer(std::make_unique<GpuMemTracer>()),
      mFeatureOverrideParser(kConfigFilePath) {
    mGpuMemAsyncInitThread = std::make_unique<std::thread>([this] {
        mGpuMem->initialize();
        mGpuMemTracer->initialize(mGpuMem);
    });
    mGpuWorkAsyncInitThread = std::make_unique<std::thread>([this] {
        mGpuWork->initialize();
    });
}
```

这段代码体现了三个边界：

1. `GpuMem → GpuMemTracer` 是串行依赖：`GpuMemTracer::initialize()` 要求传入的 `GpuMem` 已经初始化成功，否则不能从 BPF map 读取起始 counter（计数值）。
2. `GpuWork` 独立并行：GPU work period（GPU 工作时长区间）的 BPF 聚合与 GPU memory total 的 BPF 聚合是两条互补链路，这里只把 GpuWork 作为旁路观测来源。
3. 主服务构造不等待 BPF attach：attach 指把 BPF 程序挂到 tracepoint，使事件发生时执行该程序。`mGpuMem->initialize()` 会等待 bpfloader（系统 BPF 加载器），并可能等待 GPU tracepoint 出现；独立线程让构造函数先返回。

析构期会给 GpuMem 与 GpuWork 设置停止标志，再用 `join()` 等待两条初始化线程退出。成员对象随后析构，`GpuMem::~GpuMem()` 调用 `bpf_detach_tracepoint()`。

`stop()` 只会让 attach 重试循环退出。已经启动的 `GpuMemTracerThread` 是 detached thread（与创建者分离、不能再 `join()` 的线程），源码没有为它定义独立停止协议。gpuservice 通常与所在进程同寿命，不能把这段实现当作可反复创建和销毁的通用组件模板。

### GpuMem：基于 eBPF 的进程级 GPU 内存快照

`GpuMem.h` 定义了 tracepoint，以及 pinned program 和 map 的路径。pinned object 是绑定到 BPF 文件系统路径的 BPF 对象，用户态进程可通过该路径重新打开它。下面是与初始化直接相关的常量：

```cpp
static constexpr char kGpuMemTraceGroup[]      = "gpu_mem";
static constexpr char kGpuMemTotalTracepoint[] = "gpu_mem_total";
static constexpr char kGpuMemTotalProgPath[]   =
    "/sys/fs/bpf/prog_gpuMem_tracepoint_gpu_mem_gpu_mem_total";
static constexpr char kGpuMemTotalMapPath[]    =
    "/sys/fs/bpf/map_gpuMem_gpu_mem_total_map";
static constexpr int  kGpuWaitTimeout          = 30;  // seconds
```

`GpuMem::initialize()` 的工作顺序是：

1. 调 `bpf::waitForProgsLoaded()` 等待系统 BPF 程序加载完成；
2. 从 `/sys/fs/bpf/prog_gpuMem_tracepoint_gpu_mem_gpu_mem_total` 取出 pinned BPF program 的 fd（文件描述符）；
3. 调 `bpf_attach_tracepoint(fd, "gpu_mem", "gpu_mem_total")` 绑定 GPU 驱动 tracepoint；
4. 如果 attach 失败且 `mStop` 未置位，每次失败后等待 1 秒再试；累计等待约 30 秒后，下一次 attach 仍失败便结束初始化，用来覆盖 GPU 驱动晚于 gpuservice 启动的窗口；
5. 用只读包装 `bpf::BpfMapRO<uint64_t, uint64_t>(kGpuMemTotalMapPath)` 打开 map，成功后把 `mInitialized` 置为 true。

用户态使用 `BpfMapRO`，表示 GpuService 只读；附着在 tracepoint 上的 BPF 程序负责更新。pinned object 的文件权限和 SELinux（Android 强制访问控制机制）规则仍参与访问控制，`BpfMapRO` 本身不负责判断驱动上报是否正确。

#### BPF key 编码与 map 更新语义

内核 `android17-6.18-2026-06_r6` 的 `gpu_mem_total` tracepoint 规定：

- `pid == 0` 表示该 GPU 的全局总量；
- 正 PID 表示进程总量；
- `size` 是更新后的总字节数，不是本次分配的增量；
- 驱动在 GPU 可寻址空间发生 allocate、free、import 或 unimport 后发出事件；这里的 GPU 可寻址空间指已经映射、可由 GPU 访问的内存范围。

GpuService 的 BPF 程序把事件保存到 map。下面是删减后的片段，用中文注释省略了实际的 delete/update 语句，只展示容量、key 和零值删除语义：

```c
#define GPU_MEM_TOTAL_MAP_SIZE 1024

DEFINE_BPF_MAP_GRO(gpu_mem_total_map, HASH, uint64_t, uint64_t,
                   GPU_MEM_TOTAL_MAP_SIZE, AID_GRAPHICS);

struct gpu_mem_total_args {
    uint64_t ignore;
    uint32_t gpu_id;
    uint32_t pid;
    uint64_t size;
};

DEFINE_BPF_PROG("tracepoint/gpu_mem/gpu_mem_total", AID_ROOT, AID_GRAPHICS,
                tracepoint_gpu_mem_gpu_mem_total)
(struct gpu_mem_total_args* args) {
    uint64_t key = ((uint64_t)args->gpu_id << 32) | args->pid;
    uint64_t cur_val = args->size;
    /* cur_val == 0 时删除 key；否则 update / insert size */
}
```

key 是 `uint64_t = (gpu_id << 32) | pid`：高 32 位放 `gpu_id`，低 32 位放 `pid`。value 保存该 GPU / PID 组合最近一次上报的总字节数。`cur_val == 0` 时 BPF 程序删除 entry（map 中的一条键值记录）；若驱动完整遵守 tracepoint ABI，条目消失表示该组合已归零。

这里还有三个容易漏掉的限制：

1. tracepoint payload（事件携带的字段）只有 `gpu_id`、`pid`、`size`，没有 DMA-BUF inode、fd、buffer handle 或 allocation callsite。DMA-BUF 是 Linux 跨设备共享 buffer 的机制，inode 是内核对象标识，callsite 是触发分配的代码位置；
2. `GPU_MEM_TOTAL_MAP_SIZE = 1024` 限制的是 `(gpu_id, pid)` entry 数，pid 0 的全局 entry 也占一个位置；
3. 新 key 使用 `BPF_NOEXIST`（仅当 key 不存在时插入），程序没有检查插入返回值。map 填满后，新组合可能没有进入统计。

`dump()` 和 `traverseGpuMemTotals()` 通过 `getFirstKey()` / `getNextKey()` 逐项读取 map。遍历期间驱动仍可更新 map，因此输出是 best-effort（尽力而为、不同 entry 可能取自相邻时刻）快照，不具备跨 entry 的原子一致性；中途的 value 或 next-key 读取错误还会提前结束遍历。

GpuMem 能回答驱动最近上报的进程总量，无法指出哪一个 DMA-BUF 或 BufferQueue slot（队列中复用 buffer 的槽位）占用最大。

### `dumpsys gpu`：即时查询入口

`GpuService.cpp::doDump()` 对 shell / dump 权限调用方开放，调用方需要满足 `uid == AID_SHELL` 或持有 `android.permission.DUMP`。常用命令如下：

C++ 组件名是 `GpuService`，注册到 ServiceManager（Binder 系统服务注册表）的服务名是 `gpu`：`GpuService::SERVICE_NAME = "gpu"`。`dumpsys` 按 Binder 服务名查找目标，因此命令入口是 `dumpsys gpu`。

| 命令 | 触发模块 | 用途 |
| --- | --- | --- |
| `dumpsys gpu` | dumpAll=true，全部模块输出 | 一次性查看 GameDriverInfo、GpuMem、GpuStats、GpuWork |
| `dumpsys gpu --gpumem` | `mGpuMem->dump()` | 只看 `(gpu_id, pid)` GPU 内存快照 |
| `dumpsys gpu --gpustats` | `mGpuStats->dump()` | 只看 GL / Vulkan / ANGLE 驱动加载统计 |
| `dumpsys gpu --gpudriverinfo` | GameDriverInfo | 查看 `ro.gfx.driver.*` 相关驱动信息 |
| `dumpsys gpu --gpuwork` | `mGpuWork->dump()` | 查看按 UID / GPU 聚合的 work period 统计 |

`GpuMem::dump()` 中的两个边界输出很适合排查启动问题：

- `Failed to initialize GPU memory eBPF`：`mInitialized` 为 false 或 BPF map 无效，通常意味着 BPF 程序、tracepoint attach 或初始化时序未完成；
- `GPU memory total usage map is empty`：源码在 `getFirstKey()` 返回任意错误时输出这句话。常见情况是 GPU 驱动尚未上报非零条目或当前没有活跃占用，但该字符串没有区分空 map 与其他 key 枚举错误。

排查建议：不要用单次 dumpsys 判断泄漏。`--gpumem` 是瞬时快照，应在场景前、中、后多次采样，关注同一 pid 的 `size` 是否随场景退出归零或回落。

### GpuMemTracer 与 ftrace：初始值加后续更新

`GpuMemTracer` 把同一份 `GpuMem` map 作为 Perfetto 初始状态。下面的常量是 Android 17 注册的数据源名，配置时必须逐字匹配：

```cpp
static constexpr char kGpuMemDataSource[] = "android.gpu.memory";
```

该名称是 `android.gpu.memory`，下划线形式 `android.gpu_mem` 不对应这份源码。

初始化后，GpuMemTracer 向 system backend（系统 Perfetto tracing service）注册 data source，并启动分离的 `GpuMemTracerThread`。Perfetto 调用 `OnStart()` 时，线程执行一次 `traceInitialCounters()`。遍历到的每个 map entry 会形成一个 `GpuMemTotalEvent`：

```cpp
auto* event = packet->set_gpu_mem_total_event();
event->set_gpu_id(gpuId);
event->set_pid(pid);
event->set_size(size);
packet->set_timestamp_clock_id(
    perfetto::protos::pbzero::BUILTIN_CLOCK_MONOTONIC);
packet->set_timestamp(ts);
```

这段代码给 trace 提供起始基线。`traverseGpuMemTotals()` 在遍历每个 entry 时分别调用 `systemTime()`，所以各 packet（trace 数据包）的时间戳可能略有差异，整组数据也不是原子快照。

后续变化由 ftrace 的 `gpu_mem/gpu_mem_total` 事件提供。要得到从起点开始的时间序列，Perfetto 配置应同时启用初始 data source 和 ftrace 事件。下面是这两项的最小配置片段：

```textproto
data_sources {
  config {
    name: "android.gpu.memory"
    target_buffer: 0
  }
}

data_sources {
  config {
    name: "linux.ftrace"
    target_buffer: 0
    ftrace_config {
      ftrace_events: "gpu_mem/gpu_mem_total"
    }
  }
}
```

`android.gpu.memory` 写入 trace 启动时已有的非零 entry；`linux.ftrace` 记录会话期间驱动发出的更新。只启用前者会得到一次起始遍历，只启用后者可能缺少首次变化之前的基线。该链路由事件触发，不做固定周期 polling（定时读取）；驱动没有发出 tracepoint 时，轨道也不会变化。

### GpuStats：statsd 驱动加载与功能使用统计

`GpuStats` 保存图形驱动加载和功能使用信息，不保存 GPU 内存字节数。GpuStats 通过 pull atom 在 statsd 请求时生成结构化统计记录。`GpuStats.h` 为自身内存占用设置了以下上限：

```cpp
static const size_t MAX_NUM_LOADING_TIMES = 16;
static const size_t MAX_NUM_APP_RECORDS   = 100;
static const size_t APP_RECORD_HEADROOM   = 10;
```

每个 App 的 GL、Vulkan 和 ANGLE loading-time（驱动加载耗时）数组各自最多保存 16 个样本。App 记录达到 100 条时，`purgeOldDriverStats()` 按 `lastAccessTime` 排序并删除最旧的 10 条，为后续记录预留空间。源码注释给出的目标是让 GpuStats 内存占用低于约 10KB。

Android 17 把 ANGLE 作为独立驱动类别。下面的分支累计全局加载次数和失败次数：

```cpp
case GpuStatsInfo::Driver::ANGLE:
    outGlobalInfo->angleLoadingCount++;
    if (!isDriverLoaded) outGlobalInfo->angleLoadingFailureCount++;
    break;
```

应用维度用 driver enum（驱动类别枚举值）或包名识别本次报告是否使用 ANGLE：

```cpp
appInfo.angleInUse =
    driver == GpuStatsInfo::Driver::ANGLE || driverPackageName == "angle";
```

现有记录再次收到 `insertDriverStats()` 时，`angleInUse` 会被这次判断覆盖，无法作为只增不减的历史标志。`angleLoadingCount` 与 `angleLoadingFailureCount` 可帮助解释驱动路径差异，不能证明 GPU 内存泄漏。

GpuStats 在第一次收到驱动或目标统计时，才向 statsd 注册 `GPU_STATS_GLOBAL_INFO` 与 `GPU_STATS_APP_INFO` 两个 pull callback（由 statsd 拉取时调用的回调）。每次 pull 成功返回后，对应的 `mGlobalStats` 或 `mAppStats` 都会被清空。

因此，一个 atom 只表示相邻两次 pull 之间累计的信息，不是开机以来永不清零的计数。

`dumpsys gpu --gpustats --global` 与 `--app` 可以限定输出；追加 `--clear` 会清除所选统计。`--clear` 会改变后续 dumpsys 和 statsd pull 的结果，采集证据前不要使用。

`toggleAngleAsSystemDriver(enabled)` 只允许 appId 为 `AID_SYSTEM` 且持有 `android.permission.ACCESS_GPU_SERVICE` 的调用方切换，开启时尝试写入持久系统属性 `persist.graphics.egl=angle`。

`/system/etc/angle/feature_config_vk.binarypb` 是另一条配置路径，其中 `binarypb` 表示二进制 protobuf 文件。`FeatureOverrideParser` 在 GpuService 构造期间解析一次并缓存，文件后续变化不会自动重载。系统驱动属性、feature override（功能覆盖配置）与 GpuStats 彼此有关联，但源码没有把它们实现成单向的三阶段处理链。

### 从进程总量走到 DMA-BUF

GpuMem 只有进程总量，没有 DMA-BUF 标识。要定位到具体 buffer，需要补充其他数据源：

| 数据源 | 统计口径 | 能回答的问题 |
| --- | --- | --- |
| `dumpsys gpu --gpumem` | 驱动上报的 `(gpu_id, pid)` 当前总量 | 哪个进程的 GPU 可寻址内存增长？ |
| `dumpsys meminfo <pid>` / memtrack HAL | Framework 内存核算中的 GL 与 Graphics | 未进入 smaps 的 GPU private 和 DMA-BUF PSS 有多少？ |
| `dmabuf_dump <pid>` | 进程持有或映射的 DMA-BUF | 哪些 DMA-BUF inode 被该进程引用？ |
| `dmabuf_dump -b` | 每个 buffer、exporter 和 device 的统计 | 大 buffer 来自哪个 exporter 或设备？ |
| `dumpsys SurfaceFlinger` / `--list` | 当前 layer 与合成状态 | 哪些 layer 与当前 buffer 状态可关联？ |
| Perfetto GPU memory | 初始总量和 tracepoint 更新 | 增长发生在哪个业务时间窗？ |

memtrack HAL 是厂商实现的设备内存核算接口，`dumpsys meminfo` 会使用其数据。`/proc/<pid>/smaps` 是按进程内存映射列出核算信息的内核接口，PSS（Proportional Set Size）把共享内存按引用者比例分摊。GPU private 指厂商 memtrack 按 GL 类别报告、未计入 smaps 的 GPU 私有分配，它不一定有 DMA-BUF identity。inode 是 DMA-BUF 的内核对象标识，exporter 是创建并导出该 DMA-BUF 的驱动或子系统。

`IMemtrack.aidl`（memtrack 的稳定 AIDL 接口定义）对核算口径有明确约束：

- `MemtrackType::GRAPHICS` 与 `FLAG_SMAPS_UNACCOUNTED` 应报告 CPU-mapped 与 GPU-mapped DMA-BUF 的 PSS，并去掉两组之间的重叠；
- `MemtrackType::GL` 与 `FLAG_SMAPS_UNACCOUNTED` 应报告指定 PID 下未计入 `/proc/<pid>/smaps` 的 GPU private allocation；
- PID 0 的 GL 查询应返回全局 GPU-private memory；PID 0 配合其他 type 应返回 0；
- 同一块内存不能同时计入两个 memtrack type。

因此，GpuMem、memtrack 与 DMA-BUF 统计的数字不要求相等。它们覆盖的对象、共享内存分摊方式和去重规则不同。严谨的表述应是“多种口径同时增长”或“某口径没有同步回落”，不能要求数字逐字节守恒。

Android 17 的 `dmabuf_dump` 来自 `system/memory/libmeminfo`。在 6.18 及更新内核上，VTS（Vendor Test Suite，供应商接口测试）要求 DMA-BUF BPF iterator 可用；iterator 是由 BPF 实现的内核对象遍历接口。

较早内核还可能通过 `CONFIG_DMABUF_SYSFS_STATS` 提供 per-buffer（逐 buffer）统计。这个 BPF iterator 与 GpuMem 的 `gpu_mem_total_map` 是两套独立机制。

下面这组命令先找增长进程，再查该进程引用的 DMA-BUF，最后结合 SurfaceFlinger layer 缩小范围。`dmabuf_dump` 读取其他进程和内核对象时通常需要 userdebug/eng（可调试的系统构建变体）环境与 root 权限。

```bash
app_id=com.example.game
pid=$(adb shell pidof -s "$app_id")
adb shell dumpsys gpu --gpumem
adb shell dumpsys meminfo "$pid"

# userdebug / eng 设备
adb root
adb wait-for-device
pid=$(adb shell pidof -s "$app_id")
adb shell dmabuf_dump "$pid"
adb shell dmabuf_dump -b

adb shell dumpsys SurfaceFlinger --list
adb shell dumpsys SurfaceFlinger
```

示例用 `com.example.game` 演示 PID 获取，运行时改成目标包名；多进程应用应指定执行图形工作的进程。`dumpsys gpu` 定位进程总量，meminfo 核对 Framework 内存分类，`dmabuf_dump` 给出 inode 与 exporter 线索，SurfaceFlinger 输出用于关联 layer。

`adb root` 会重启 adbd（设备侧 adb 守护进程），所以示例在 `adb wait-for-device` 后重新读取 PID。Android 17 的 `SurfaceFlinger::doDump()` 命令表没有 `--bufferstats`，不要依赖该参数。默认 SurfaceFlinger dump 也不是完整的 DMA-BUF 引用跟踪器，只能提供当前合成与 layer 上下文。

#### 一次增长排查的时间顺序

1. 记录包名、PID、进程启动时间、GPU ID 和场景起止 marker（写入 trace 的阶段标记）；
2. 在场景前保存一次 `--gpumem`、meminfo 与 DMA-BUF 数据；
3. Perfetto 同时启用 `android.gpu.memory` 和 `gpu_mem/gpu_mem_total`；
4. 执行固定输入的场景，保留峰值和退出后的稳定窗口，即数值不再明显变化的一段时间；
5. 重复快照，确认增长来自 GPU private、DMA-BUF，或两者都有；
6. 用 DMA-BUF inode、exporter、进程引用与 SurfaceFlinger layer 缩小持有者范围；
7. 进程退出后核对旧 PID entry 是否删除，避免 PID 复用造成误判。

进程总量在场景结束后没有立即归零，也不自动构成泄漏。驱动缓存、对象延迟销毁、异步 fence（表示 GPU 或显示工作何时完成的同步对象）和进程仍存活都可能让内存暂时保留。判断依据应包含稳定窗口、多轮重复和对象生命周期证据。

### 各组件的职责边界

- `GpuService / GpuMem`：读取驱动上报的全局与进程 GPU 内存总量，不拥有这些 allocation（内存分配对象）。
- `GpuMemTracer / Perfetto ftrace`：提供 trace 起始值和会话内更新，用于观察时间变化。
- `GpuStats / statsd`：保存驱动加载、失败、耗时和图形功能使用信息；pull 后相应累计值清空。
- `memtrack HAL / dumpsys meminfo`：按 Framework 规则核算 GL、Graphics 和其他设备专属内存。
- `dmabuf_dump`：读取 DMA-BUF identity（对象标识）、exporter、device 与进程引用，是 buffer 级排查的主要补充。
- `SurfaceFlinger dump`：提供 layer 与合成状态，不能替代 DMA-BUF 引用分析。
- `gfxinfo / GraphicsStats`：报告帧耗时与 jank（掉帧或卡顿事件），不提供 GPU 内存总账。

§10.4 讨论应用与图形内存症状，§15.11 介绍 GPU 调试工具，§15.16 展开 eBPF 观测范围。这里的范围限于 GpuService、GPU memory tracepoint、GpuStats 和 DMA-BUF 对账之间的接口关系。

### 失败模式与结论强度

#### GpuMem 初始化失败

初始化失败可能发生在 pinned program 获取、tracepoint attach 或 map 打开阶段。attach 会在约 30 秒内重试；超时后该 GpuMem 实例不会在后台无限重试，GpuMemTracer 也因 `isInitialized() == false` 而不注册数据源。

设备晚加载驱动时，要结合 logcat（Android 系统日志）、tracefs（内核追踪文件系统）event 与 pinned object 状态判断具体停在哪一步。

#### map 为空

空 map 可能表示当前没有非零 entry，也可能表示驱动没有实现或没有完整发出 tracepoint。内核头文件只定义 ABI，厂商 GPU 驱动是否在 allocate、free、import、unimport 后准确上报，需要查看对应驱动源码或真机验证。

#### Perfetto 只有起始快照

若配置只启用 `android.gpu.memory`，只有启动遍历符合预期。若同时启用 ftrace 后仍没有变化，应确认 tracefs 中存在 `gpu_mem/gpu_mem_total`，并检查场景期间驱动是否发出事件。

#### 数值不一致

GpuMem、memtrack 和 DMA-BUF 的口径不同；先按各自定义解释，再判断差异是否异常。GPU private allocation 可能没有 DMA-BUF identity，共享 DMA-BUF 又会按 PSS 分摊。没有厂商实现证据时，只能把差异记录为待验证项。

#### 可发布的结论

以下结论可由 Android 17 与 6.18 固定 tag 的源码直接支持：

- GpuMem map 保存驱动上报的 `(gpu_id, pid) → total bytes`；
- pid 0 代表全局总量，size 0 会删除 entry；
- `android.gpu.memory` 负责 Perfetto 初始值，ftrace 负责后续变化；
- GpuStats 不保存 GPU 内存字节，statsd pull 会清空相应累计值；
- memtrack、DMA-BUF 与 GpuMem 使用不同核算口径；
- Android 17 SurfaceFlinger 没有 `--bufferstats` dump 选项。

厂商 tracepoint 是否完整上报、设备权限是否满足、Perfetto UI 怎样展示、HAL 对账是否准确以及缓存何时回收，都需要实机证据。


## 参考资料

- [AOSP android-17.0.0_r1：GpuService.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/GpuService.cpp)
- [AOSP android-17.0.0_r1：GpuMem.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/gpumem/GpuMem.cpp)
- [AOSP android-17.0.0_r1：gpuMem.c](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/bpfprogs/gpuMem.c)
- [AOSP android-17.0.0_r1：GpuMemTracer.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/tracing/GpuMemTracer.cpp)
- [AOSP android-17.0.0_r1：GpuStats.cpp](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/gpuservice/gpustats/GpuStats.cpp)
- [Android common kernel android17-6.18-2026-06_r6：gpu_mem tracepoint](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/gpu_mem.h)
- [AOSP android-17.0.0_r1：IMemtrack.aidl](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl)
- [AOSP android-17.0.0_r1：dmabuf_dump.cpp](https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/libdmabufinfo/tools/dmabuf_dump.cpp)
- [AOSP android-17.0.0_r1：6.18 DMA-BUF BPF iterator VTS](https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/libdmabufinfo/vts/vts_dmabufinfo_test.cpp)
- [AOSP android-17.0.0_r1：SurfaceFlinger dump 命令表](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [Perfetto：GPU memory data source](https://perfetto.dev/docs/data-sources/gpu)
