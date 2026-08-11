---
title: "Perfetto GPU Counter 与 GPU Memory 事件分析"
chapter: "14.16"
section: "14.16"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [gpu, profiling, perfetto, gpu-counter, gpu-memory, android17]
related_chapters: ["2.10", "2.14", "13.9", "14.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-06"
gap_source: "素材驱动/AOSP结构/官方文档"
task6_state: reworked
task9_state: ready-for-review
pipeline_stage: rework_verified
last_draft_polish_at: "2026-07-27T19:35:27+08:00"
last_draft_polish_run_id: "20260727-193527-draft-polish-30f4d38e"
reviewed_date: "2026-07-27"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-27T20:13:43+08:00"
last_review_finalize_run_id: "20260727-201343-4b671d13"
last_rework_at: "2026-07-27T21:36:40+08:00"
last_rework_run_id: "20260727-213543-rework-30f4d38e"
last_verified: "2026-07-30"
last_verified_against: "AOSP android-17.0.0_r1 external/perfetto；Writer rendering_pipelines S01/S02/S03/S04/S05/S11/S12/S13"
confidence: high
rework_resolution: "收窄章节标题与正文范围，仅保留 android-17.0.0_r1 可由 external/perfetto 一手 proto、trace processor parser 与 SQL 视图支撑的 Perfetto GPU counter / GPU memory 事件链路；移除未取证的跨厂商阈值、Ray Tracing、NPU/ML、远程调试与 AGI 工作流结论。"
android17_review_notes: "2026-07-30：复核 GpuCounterDescriptor、GpuCounterEvent、GpuCounterConfig、Trace Processor 回看式采样与 GpuMemTotalEvent；结合 rendering_pipelines 补充标准 HWUI、TextureView、独立 Surface、Camera/Video、Game 与混合出图的信号归属及归因边界。原 task6/task9/OpenClaw 字段完整保留。"
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
---

# 14.16 Perfetto GPU Counter 与 GPU Memory 事件分析

> **版本边界**：范围限于 Android 17 / `android-17.0.0_r1` 中可在 AOSP `external/perfetto` 核验的 GPU counter descriptor、GPU counter event、GPU memory event 与 Trace Processor 导入链路。跨厂商性能阈值、Ray Tracing、NPU/ML 协同、远程 GPU 调试与完整 AGI 工作流不在讨论范围内。

## 要点

1. `GpuCounterDescriptor` 提供 counter 的协议级元数据：语义分组、度量单位、counter spec 与硬件 counter block 容量约束。
2. `GpuCounterEvent` 有 descriptor 直挂与 interned descriptor 两种事件发射模式；Android OEM 合规路径依赖直挂 descriptor，多 producer / 多 GPU 场景可用 sequence-scoped interned descriptor 避免全局 counter id 协调。
3. Trace Processor 在 `gpu_event_parser.h/.cc` 中维护 GPU counter track 与上一条 counter row 状态，并把回看式采样值写回上一行；`android-17.0.0_r1` 不包含 `gpu_counter_sequence_state.h`。
4. `gpu_counter_span_view.sql` 用 `LEAD() OVER (PARTITION BY track_id ORDER BY ts)` 将 counter 采样点转为 span，适合按 GPU track 计算区间持续时间。
5. `GpuMemTotalEvent` 位于 `protos/perfetto/trace/android/gpu_mem_event.proto`，由 Android `GpuService` 生成；`pid=0` 表示全局总量，其他 pid 表示进程归属。
6. `GpuCounterEvent` 不携带 pid、tid、layer、FrameTimeline token 或 GPU submission id。单条 counter track 只能直接说明某个 `gpu_id` 上的设备级变化，归因到 App、SurfaceFlinger 或某一显示帧还需要其它时间线证据。

## `GpuCounterDescriptor`：协议层的标准化骨架

`protos/perfetto/common/gpu_counter_descriptor.proto` 给出三层结构。

### 语义分组

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

### 度量单位

`MeasureUnit` 的 wire value 从 `NONE = 0` 延伸到 `INSTRUCTION = 40`，覆盖 `BIT`、`BYTE`、`HERTZ`、`SECOND`、`VERTEX`、`PIXEL`、`TRIANGLE`、`PRIMITIVE`、`FRAGMENT`、`MILLIWATT`、`WATT`、`JOULE`、`VOLT`、`AMPERE`、`CELSIUS`、`PERCENT`、`INSTRUCTION` 等。`next id: 41` 是维护枚举编号的注释，不是协议字段。派生单位由 `numerator_units` 和 `denominator_units` 的重复项组合，例如 `PIXEL / SECOND` 表示每秒像素。

### Counter spec 字段边界

`GpuCounterSpec` 在 `android-17.0.0_r1` 中包含：

```text
counter_id
name
description
oneof peak_value {
  int_peak_value
  double_peak_value
}
numerator_units
denominator_units
select_by_default
groups
```

本 tag 的 `GpuCounterSpec` 不含 `value_direction` 字段。因此，不能把 Perfetto 上游后续设计或其他分支字段写成 Android 17 已有协议字段。Trace Processor 的 `gpu_event_parser.cc` 把 GPU counter 视为回看式采样：收到时间戳 `t(n)` 的事件时，先在 `t(n)` 插入值为 0 的占位行，再把事件携带的 value 写入上一条 counter row。区间 duration 不在这一步回填，而由后面的 SQL span 视图计算。

### Counter block 容量约束

`GpuCounterBlock { block_id, block_capacity, name, description, counter_ids }` 用于描述一组 counter 共享同一硬件 block 时的同时启用上限；`block_capacity` 未设置时表示不设上限。采集配置不能只按 counter 名称平铺选择，自动化脚本或 UI 应按 `block_id` / `block_capacity` 预先校验。proto 没有规定超限后的处理方式，不能统一断言 producer 会拒绝、轮转采样或静默裁剪。

## `GpuCounterEvent`：descriptor 直挂与 interned descriptor

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

源码注释区分两种 emission 模式：

- **Mode 1：descriptor 直挂**。`counter_descriptor = 1` 直接随事件发送，注释说明这是 Android OEMs 为满足 CDD / CTS 合规测试需要使用的路径；每个 session 的首个 trace packet 必须声明 descriptor。该模式的 counter id 是全局的，多 producer 必须自行协调。
- **Mode 2：interned descriptor**。`counter_descriptor_iid = 4` 引用 trusted sequence 的 `InternedGpuCounterDescriptor`，适合多 producer / 多 GPU 场景。它把 counter spec 放入 sequence-scoped `InternedData`，避免把 counter id 当成全局编号；若 event 外层和 interned descriptor 都提供 `gpu_id`，以后者为准。

数据源配置入口在 `protos/perfetto/config/data_source_config.proto`：

```proto
optional GpuCounterConfig gpu_counter_config = 108 [lazy = true];
```

该字段对应的数据源名是 `gpu.counters`。`[lazy = true]` 是 protobuf 的延迟解码选项，不能据此推导 GPU data source 的启动时机或常驻状态。采集行为由 `GpuCounterConfig` 的以下字段表达：

- `counter_period_ns`：期望采样周期；descriptor 若声明了 `min_sampling_period_ns` 与 `max_sampling_period_ns`，配置应落在该 producer 支持的范围内；
- `counter_ids`：要采集的 counter id，含义以本次 producer descriptor 为准；
- `instrumented_sampling`：请求通过 command buffer instrumentation 采样，使用前应检查 descriptor 的 `supports_instrumented_sampling`；
- `fix_gpu_clock`：请求在 trace 期间固定 GPU 时钟，会改变动态调频条件，不能与日常运行数据混为同一基线。

## Trace Processor 导入状态机

`src/trace_processor/importers/proto/gpu_event_parser.h/.cc` 是 Android 17 基线下 GPU counter 事件导入的实际实现位置。头文件中可见两类状态：

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

1. legacy inline `counter_descriptor` 路径按全局 `counter_id` 维护 `GpuCounterState`。
2. interned `counter_descriptor_iid` 路径通过 packet sequence 中的 interned message 查到 `InternedGpuCounterDescriptor`，再按 track 维护 `last_id`。

`android-17.0.0_r1` 不包含 `gpu_counter_sequence_state.h`；相关行为应以 `gpu_event_parser.h/.cc` 为准。

`PushGpuCounterValue()` 的顺序还会影响 trace 边界解释。第一条事件只建立占位行，要等下一条事件到达后，前一个时间点的值才被写入；trace 结束前的末行可能仍是值为 0 的占位行。分析短 trace 或低频采样时，应检查首尾样本，不要把这个 0 自动解释为 GPU 空闲。

## SQL span 视图：从采样点到区间

`src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql` 的模板如下：

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

这里的关键点是：

- `{{counter_name}}` 在 metric 编译期替换为具体 counter 名。
- `LEAD(ts, 1, trace_end()) OVER (PARTITION BY track_id ORDER BY ts)` 用下一条采样点时间减当前时间，得到当前 counter 值对应的持续区间。
- `gpu_id IS NOT NULL` 过滤掉非 GPU counter track。

这个模板只生成区间，不改变 parser 已写入的 value。末行会延伸到 `trace_end()`，因此它若仍是 parser 的 0 占位值，聚合前应按采样语义决定是否剔除。

`test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto` 展示了测试使用的 counter 名与单位组合，例如：

- `GPU Frequency`：`denominator_units: SECOND`，即频率类 counter。
- `Fragments / vertex`：`FRAGMENT / VERTEX`。
- `Fragment / Second`：`PIXEL / SECOND`。
- `Triangle Acceleration`：`TRIANGLE / (MILLISECOND · MILLISECOND)`。

这些是 parser 的合成测试输入，可以验证名称、单位和 group 的导入结果；它们不构成设备 counter 清单，也不能外推为所有 Android 17 设备都必须暴露的跨厂商性能基准。

## GPU memory event：Android 平台 producer

`protos/perfetto/trace/android/gpu_mem_event.proto` 定义：

```proto
// Generated by Android's GpuService.
message GpuMemTotalEvent {
  optional uint32 gpu_id = 1;
  optional uint32 pid = 2;
  optional uint64 size = 3;
}
```

注释明确该事件由 Android `GpuService` 生成。Trace Processor 的 `ParseGpuMemTotalEvent()` 按 `gpu_id` 建立 GPU 维度：`pid == 0` 时写入 global GPU memory counter，其他 pid 则关联进程并写入 process GPU memory counter。`size` 是该时间点的总量值，不是一次 allocation 的增量。

这条平台事件可以观察全局或进程归属的 GPU 内存总量，但不能替代厂商 GPU counter，也不能自动推出带宽、shader throughput、缓存命中率或功耗阈值。pid 归属还不等同于物理页的唯一持有者；跨进程共享 buffer、驱动保留和显示系统引用需要结合 GpuService、dma-buf 与厂商工具解释。

## 把 counter 放回 Android 显示路径

### 设备级 counter 没有内建的帧归属

`GpuCounterEvent.GpuCounter` 只有 `counter_id` 和一个数值，外层事件只增加 descriptor 与 `gpu_id`。协议里没有 pid、tid、layer id、BufferQueue frame number、FrameTimeline token 或 GPU submission id。Trace Processor 因此创建的是 GPU counter track，并不会自动把 counter span 挂到某个 App 或某个显示帧。

这条边界会直接影响结论强度：

| 证据 | 可以确认 | 不能单独确认 |
| --- | --- | --- |
| GPU counter span | 某个 `gpu_id` 在该区间的频率、吞吐、利用率或厂商定义事件值发生变化 | 哪个进程、layer 或 command buffer 造成变化 |
| GPU render-stage / submission 事件 | 已被 producer 标注的 GPU 工作区间与提交关系 | 未标注工作属于哪个业务帧，或该帧已经显示 |
| App / RenderThread slice | CPU 何时准备、提交或等待 GPU 工作 | GPU 何时完成，SurfaceFlinger 是否采用该 buffer |
| producer completion fence | 对应 buffer 何时可由 consumer 安全读取 | 该 buffer 是否赶上目标 display present |
| FrameTimeline、layer 与 present | App/SF 帧、buffer/layer 选择及显示时序 | counter 峰值由哪条 shader、纹理或硬件单元产生 |

归因时要用时间重叠缩小候选范围，再用 submission、buffer、fence、layer 和 frame token 建立关系。仅凭“counter 峰值与卡顿同时出现”还不能得出因果结论。

### 出图拓扑决定 counter 应该和谁对齐

以下判读表基于 Android 17 的显示模型。表中的“GPU counter”均指设备级轨道；厂商若提供更细的 context、queue 或 stage 事件，可以继续细分。

| 出图路径 | 可能进入同一 GPU counter 的工作 | 需要同时核对的证据 | 常见误判 |
| --- | --- | --- | --- |
| 标准 View / Compose App Window | HWUI/Skia 绘制 App buffer；发生 CLIENT composition 时还包含 SurfaceFlinger RenderEngine | MainThread、RenderThread、GPU stage、App completion fence、host `BufferTX`、SF composition type、present | 把 RenderThread duration 当成 GPU duration，或把所有 GPU 峰值算给 App |
| TextureView | 外部 Producer 可能使用 GPU；宿主 HWUI 还要 acquire、采样外部 image 并写 App Window | 外部 BufferQueue 与 fence、`DeferredLayerUpdater`、宿主 GPU、host layer、最终 composition | 只看到宿主 counter 变高，就断定外部视频、相机或地图 Producer 变慢 |
| SurfaceView / 独立 Surface | 游戏或自研 renderer 的 GPU 工作；若该 layer 或同屏其它 layer 转为 CLIENT，还会增加 RenderEngine 工作 | 独立 BLAST child、producer fence、per-layer composition type、client target、release/present fence | `SurfaceView` 一定不占 GPU，或 DEVICE composition 等于 Producer 没有 GPU 成本 |
| Camera / 普通视频 Surface | 主体像素可能由 ISP、codec、blitter 或其它硬件产生；TextureView、自研滤镜、CLIENT composition 才会额外引入可见 GPU 工作 | Camera/codec result、buffer timestamp、acquire fence、承载方式、HWC strategy、present | GPU counter 低就表示预览/播放链路没有瓶颈 |
| 本地游戏 | engine submit、GPU queue execution、可能的 SurfaceFlinger CLIENT composition | Input、Game/Render/RHI、submission、producer fence、queue depth、latch、present | submit 返回等于 GPU 完成，或 FPS 稳定等于输入延迟低 |
| 混合出图 | 多个 Producer、宿主采样与 RenderEngine 可能共享同一个 `gpu_id` | 每个 Surface/BufferQueue、目标 display 的可见 layer 集合、DEVICE/CLIENT 变化、各自 fence | 用一条全局 GPU track 给某个 layer 定责 |

TextureView 与独立 Surface 的差异尤其容易被 counter 隐藏。TextureView 输入进入宿主 HWUI 后，HWC 通常只看到最终 App Window；独立 Surface 保留单独 layer，HWC 可以逐层选择 DEVICE 或 CLIENT。某次 DEVICE→CLIENT 变化可能让 GPU counter 上升，但触发条件也许来自同屏 layer、透明度、变换、HDR、protected usage 或 plane 竞争，不能只检查目标 App 的 shader。

Camera 和视频还存在相反情况：主体内容通过 ISP、codec 与 HWC 路径完成，GPU counter 可能保持很低，画面仍会因 HAL/codec 晚、acquire fence 晚、requested present timestamp、HWC 或 display driver 而错过显示。GPU counter 没有覆盖这些硬件阶段。

### 一次可复用的关联顺序

1. 从异常的 display present 或 FrameTimeline actual frame 选定时间窗口，记录 `display_frame_token`、目标 layer 和 present 时间。
2. 按标准窗口、TextureView、独立 Surface、Camera/Video、Game 或混合页面建立 Producer—BufferQueue—layer 对象表。
3. 沿目标 buffer 反查 Producer CPU 工作、GPU submission/render stage、completion fence、`queueBuffer`、SF latch 与 composition type。
4. 在已经确定归属的 GPU 工作区间内读取 counter span，使用 descriptor 的名称、单位、group、采样周期和 block 配置解释数值。
5. 对比相同设备、相同 counter 配置、相同温度和显示模式下的基线。跨厂商、跨驱动或不同 counter 组合不直接比较绝对值。

这套顺序把 counter 放在逐帧证据之后。counter 适合回答“已定位的 GPU 区间为什么变重”，不适合跳过对象和同步关系直接回答“谁让这一帧卡了”。

## 采集与分析建议

1. **先看 descriptor，再解释数值**：分析 counter value 前，应先确认 `counter_id` 对应的 `name`、`numerator_units`、`denominator_units` 与 `groups`。
2. **尊重 block capacity**：批量启用 counter 时，应按 `GpuCounterBlock.block_capacity` 检查是否超出同一硬件 block 的同时采样能力。
3. **区分平台事件与厂商 counter**：`GpuMemTotalEvent` 是 Android 平台 GPU memory 事件；GPU 频率、fragment、triangle 等 counter 仍依赖 GPU counter producer 暴露。
4. **记录出图拓扑**：同一 counter 峰值在标准 HWUI、TextureView、独立 Surface 和视频 overlay 场景中的来源不同。采集说明至少记录 Surface 类型、layer、graphics API、HWC composition 与显示模式。
5. **避免跨厂商强归一**：仅凭同属 `MEMORY`、`FRAGMENTS` 或 `COMPUTE` 分组不足以证明 counter 可比。若要建立跨设备基准，必须记录厂商 producer、counter 名称、单位、采样频率与替代映射依据。
6. **控制 trace 体积**：样本数量近似为 `counter 数 × 采样频率 × 时长`，但 protobuf 的 `int_value` 是变长编码，`double_value`、嵌套 message、packet framing、descriptor 与 interning 也有额外成本。不要用固定的“每项 12 bytes”推算容量；先做短时采集，测量生成 trace 的 bytes/s，再为目标时长设置 buffer 和采样周期。

## 范围外主题

下列主题需要另行补充 Android 17 基线下的一手材料或可复现实验后再写入正文结论：

- Adreno / Mali / PowerVR / Xclipse 的厂商 counter 私有命名表与等价映射。
- UI 渲染、游戏、视频、计算摄影等工作负载下的正常 / 警告 / 异常阈值。
- Vulkan Ray Tracing 管线开销与 Android 17 设备支持边界。
- NNAPI、厂商 NPU / ML 加速器与 GPU 渲染负载之间的调度影响。
- `profileable`、权限、SELinux 或生产采集策略对 GPU counter 可见性的影响。
- AGI Frame Capture、Layer Override、GAPID 到 AGI 迁移等完整工具工作流。

## 信息源

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
