---
title: "Perfetto GPU Counter 与 GPU Memory 事件分析"
chapter: "14.28"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [gpu, profiling, perfetto, gpu-counter, gpu-memory, android17]
related_chapters: ["2.10", "2.14", "13.10", "14.8"]
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
last_verified: "2026-07-27"
confidence: medium-high
rework_resolution: "收窄章节标题与正文范围，仅保留 android-17.0.0_r1 可由 external/perfetto 一手 proto、trace processor parser 与 SQL 视图支撑的 Perfetto GPU counter / GPU memory 事件链路；移除未取证的跨厂商阈值、Ray Tracing、NPU/ML、远程调试与 AGI 工作流结论。"
sources:
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/common/gpu_counter_descriptor.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/trace/gpu/gpu_counter_event.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/config/gpu/gpu_counter_config.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/config/data_source_config.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/trace/android/gpu_mem_event.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/importers/proto/gpu_event_parser.h"
  - "AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/importers/proto/gpu_event_parser.cc"
  - "AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql"
  - "AOSP android-17.0.0_r1: external/perfetto/test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto"
---

# 14.28 Perfetto GPU Counter 与 GPU Memory 事件分析

> **版本边界**：本章只讨论 Android 17 / `android-17.0.0_r1` 可在 AOSP `external/perfetto` 中核验的 GPU counter descriptor、GPU counter event、GPU memory event 与 Trace Processor 导入链路。早期 outline 中的跨厂商性能阈值、Ray Tracing、NPU/ML 协同、远程 GPU 调试与完整 AGI 工作流没有进入本章结论。

## 要点

1. `GpuCounterDescriptor` 提供 counter 的协议级元数据：语义分组、度量单位、counter spec 与硬件 counter block 容量约束。
2. `GpuCounterEvent` 有 descriptor 直挂与 interned descriptor 两种事件发射模式；Android OEM 合规路径依赖直挂 descriptor，多 producer / 多 GPU 场景可用 interned descriptor 降低重复描述开销。
3. Trace Processor 在 `gpu_event_parser.h/.cc` 中维护 GPU counter track 与上一条 counter row 状态；`android-17.0.0_r1` 没有早稿曾引用的 `gpu_counter_sequence_state.h`。
4. `gpu_counter_span_view.sql` 用 `LEAD() OVER (PARTITION BY track_id ORDER BY ts)` 将 counter 采样点转为 span，适合按 GPU track 计算区间持续时间。
5. `GpuMemTotalEvent` 位于 `protos/perfetto/trace/android/gpu_mem_event.proto`，由 Android `GpuService` 生成，提供 `gpu_id + pid + size` 的平台级 GPU 内存占用事件。

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

`MeasureUnit` 的 `next id: 41` 注释表明该 tag 中已有 41 项单位枚举，覆盖 `BIT`、`BYTE`、`HERTZ`、`SECOND`、`VERTEX`、`PIXEL`、`TRIANGLE`、`PRIMITIVE`、`FRAGMENT`、`MILLIWATT`、`WATT`、`JOULE`、`VOLT`、`AMPERE`、`CELSIUS`、`PERCENT`、`INSTRUCTION` 等。派生单位通过 `numerator_units` × `denominator_units` 表达，例如 `PIXEL / SECOND` 表示每秒像素。

### Counter spec 字段边界

`GpuCounterSpec` 在 `android-17.0.0_r1` 中包含：

```text
counter_id
name
description
peak_value
numerator_units
denominator_units
select_by_default
groups
```

本 tag 的 `GpuCounterSpec` 不含 `value_direction` 字段。因此，不能把 Perfetto 上游后续设计或其他分支字段写成 Android 17 已有协议字段。Trace Processor 的 `gpu_event_parser.cc` 仍在 parser 逻辑中把 GPU counters 按回看式采样处理：先插入当前采样行，再用当前 timestamp 回填上一条 counter row 的 duration。

### Counter block 容量约束

`GpuCounterBlock { block_id, block_capacity, name, counter_ids }` 用于描述一组 counter 共享同一硬件 block 时的同时启用上限。采集配置不能只按 counter 名称平铺选择；自动化脚本或 UI 应按 `block_id` / `block_capacity` 做 grouping-aware 选取，否则可能在 producer 或驱动层被拒绝。

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

- **Mode 1：descriptor 直挂**。`counter_descriptor = 1` 直接随事件发送，注释说明这是 Android OEMs 为满足 CDD / CTS 合规测试需要使用的路径。
- **Mode 2：interned descriptor**。`counter_descriptor_iid = 4` 引用 `InternedGpuCounterDescriptor`，适合多 producer / 多 GPU 场景，并可节省每包重复携带 descriptor 的开销。

数据源配置入口在 `protos/perfetto/config/data_source_config.proto`：

```proto
optional GpuCounterConfig gpu_counter_config = 108 [lazy = true];
```

`[lazy = true]` 表示该字段只在 GPU counter data source 启动时解析，而不是对所有 data source 常驻解析。

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

`android-17.0.0_r1` 未包含早稿曾引用的 `gpu_counter_sequence_state.h`；相关描述必须回到 `gpu_event_parser.h/.cc`。

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

`test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto` 展示了测试中使用的标准 counter 名与单位组合，例如：

- `GPU Frequency`：`denominator_units: SECOND`，即频率类 counter。
- `Fragments / vertex`：`FRAGMENT / VERTEX`。
- `Fragment / Second`：`PIXEL / SECOND`。
- `Triangle Acceleration`：`TRIANGLE / (MILLISECOND · MILLISECOND)`。

这些测试样例可以作为解析链路和 UI 期望名称的证据，但不能直接外推为所有 Android 17 设备都必须暴露的跨厂商性能基准。

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

注释明确该事件由 Android `GpuService` 生成。它与厂商 GPU counter producer 平行，提供进程级 GPU 内存占用报告。`gpu_id + pid + size` 可以用于观察某进程在某个 GPU 上的内存占用，但不能替代厂商 GPU counter，也不能自动推出带宽、shader throughput 或功耗阈值。

## 采集与分析建议

1. **先看 descriptor，再解释数值**：分析 counter value 前，应先确认 `counter_id` 对应的 `name`、`numerator_units`、`denominator_units` 与 `groups`。
2. **尊重 block capacity**：批量启用 counter 时，应按 `GpuCounterBlock.block_capacity` 检查是否超出同一硬件 block 的同时采样能力。
3. **区分平台事件与厂商 counter**：`GpuMemTotalEvent` 是 Android 平台 GPU memory 事件；GPU 频率、fragment、triangle 等 counter 仍依赖 GPU counter producer 暴露。
4. **避免跨厂商强归一**：仅凭同属 `MEMORY`、`FRAGMENTS` 或 `COMPUTE` 分组不足以证明 counter 可比。若要建立跨设备基准，必须记录厂商 producer、counter 名称、单位、采样频率与替代映射依据。
5. **控制 trace 体积**：若粗略按每个 `GpuCounter` 采样含 `counter_id + int_value` 约 12 bytes 估算，50 个 counter、60 秒、1 kHz 采样会产生约 36,000,000 bytes（约 34.3 MiB）的 counter payload；实际 trace 还会叠加 packet、framing 与 interning 开销。

## 不在本章结论范围内的主题

下列主题需要另行补充 Android 17 基线下的一手材料或可复现实验后再写入正文结论：

- Adreno / Mali / PowerVR / Xclipse 的厂商 counter 私有命名表与等价映射。
- UI 渲染、游戏、视频、计算摄影等工作负载下的正常 / 警告 / 异常阈值。
- Vulkan Ray Tracing 管线开销与 Android 17 设备支持边界。
- NNAPI、厂商 NPU / ML 加速器与 GPU 渲染负载之间的调度影响。
- `profileable`、权限、SELinux 或生产采集策略对 GPU counter 可见性的影响。
- AGI Frame Capture、Layer Override、GAPID 到 AGI 迁移等完整工具工作流。

## 信息源

所有源码引用均按 AOSP `android-17.0.0_r1` 中 `external/perfetto` 路径复核：

- `protos/perfetto/common/gpu_counter_descriptor.proto`
- `protos/perfetto/trace/gpu/gpu_counter_event.proto`
- `protos/perfetto/config/gpu/gpu_counter_config.proto`
- `protos/perfetto/config/data_source_config.proto`
- `protos/perfetto/trace/android/gpu_mem_event.proto`
- `src/trace_processor/importers/proto/gpu_event_parser.h`
- `src/trace_processor/importers/proto/gpu_event_parser.cc`
- `src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql`
- `test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto`

<!-- AIW-rework-verified-2026-07-27 -->
