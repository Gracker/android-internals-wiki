---
title: "GPU 性能分析进阶 — 跨厂商计数器标准化与工作负载剖析"
chapter: "14.28"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [gpu, profiling, adreno, mali, powervr, vulkan, ray-tracing, npu]
related_chapters: ["2.10", "2.14", "14.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-06"
gap_source: "素材驱动/AOSP结构/官方文档"
task6_state: pending
task9_state: pending
pipeline_stage: task6_pending
last_draft_polish_at: "2026-07-27T19:35:27+08:00"
last_draft_polish_run_id: "20260727-193527-draft-polish-30f4d38e"
last_verified: "2026-07-27"
confidence: medium
sources:
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/common/gpu_counter_descriptor.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/trace/gpu/gpu_counter_event.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/protos/perfetto/trace/gpu/gpu_mem_event.proto"
  - "AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/importers/proto/gpu_counter_sequence_state.h"
  - "AOSP android-17.0.0_r1: external/perfetto/src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql"
---

# 14.28 GPU 性能分析进阶 — 跨厂商计数器标准化与工作负载剖析

> Draft-polish 状态：本轮未新增外部材料，只把既有源码调研稿推进到 Task6 复查入口。正文可信范围限定为 Android 17 / `android-17.0.0_r1` 中 Perfetto GPU counter、GPU memory event 与 trace processor 相关结构；outline 中的工作负载阈值、Ray Tracing、NPU/ML 协同、远程调试等主题仍属于后续 source-apply/rework 候选，不作为本章已验证结论。

<!-- outline-start -->
## 要点

> 本 outline 仅保留选题结构。缺少一手材料支撑的段落不得在 Task6 前被当成正文结论引用；后续若要扩写，需补充 Android 17 基线下的 AOSP/官方文档或可复现实验材料。

### 🔹 跨厂商 GPU 计数器映射体系
- Adreno (Qualcomm)、Mali (Arm)、PowerVR (Imagination) 三大 GPU 厂商的计数器命名与定义差异
- Perfetto `gpu_counter_config.proto` 中 `counter_ids` 字段的厂商特定映射
- 计数器归一化策略：如何建立跨厂商可比的 GPU 性能基线

### 🔹 GPU 工作负载分类与性能基线
- 待补材料：按负载类型分类的 GPU 性能参考范围（UI 渲染、游戏、视频、计算摄影等）
- 待补材料：各负载下的关键指标阈值（GPU 利用率、显存带宽、Draw Call 数量、着色器吞吐等）
- 待补材料：正常/警告/异常值的判定标准与实战参考数据

### 🔹 Vulkan Ray Tracing 性能分析
- 待补材料：Android 17 对 Vulkan Ray Tracing 相关扩展的支持边界
- 待补材料：Ray Tracing 管线（BLAS/Ray Query）性能开销分析方法
- 待补材料：Ray Tracing 场景下的 GPU 利用率与功耗特征

### 🔹 NPU/ML 加速器协同性能分析
- 待补材料：Android 17 中 NNAPI/厂商加速器与 GPU 渲染负载之间的可观测交互边界
- 待补材料：NPU 任务调度对 GPU 渲染管线的影响
- 待补材料：端侧 AI 推理场景下 GPU+NPU 异构性能剖析

### 🔹 GPU Profiling 隐私与安全
- 待补材料：`profileable` manifest flag 对 GPU 计数器可见性的影响
- 待补材料：Android 14-17 profileable 应用可用的 GPU 计数器类型差异
- 待补材料：生产环境 GPU 性能采集的安全合规框架

### 🔹 AGI (Android GPU Inspector) 实战工作流
- 待补材料：AGI 与 Perfetto 的 GPU 数据源协同分析
- 待补材料：AGI Frame Capture + Layer Override 性能分析方法
- 待补材料：从 GAPID 到 AGI 的演进与迁移指南

### 🔹 Perfetto GPU Trace 分析进阶
- 本轮已覆盖：Perfetto GPU counter descriptor/event 与 trace processor SQL 视图的协议链路
- 待补材料：GPU Render Stages track 的深度解读、GPU 频率（DVFS）与渲染管线联合分析
- 待补材料：SurfaceFlinger HWC Composer 与 GPU 负载的因果关系追踪

## 扩展

### 🔸 云端 GPU 分析与远程调试工具链
- 云端 GPU 性能分析的技术可行性与延迟挑战
- 远程 GPU profiling 的安全与隐私考量

### 🔸 跨设备 GPU 性能基准自动化
- 建立自动化跨设备 GPU 性能基线测试流水线
- SoC 差异、驱动版本、内存配置对 GPU 性能的影响因子建模

### 🔸 GPU 性能回归检测
- 版本升级后 GPU 性能回归的自动检测策略
- GPU 驱染特性降级（fallback）的性能影响量化

<!-- outline-end -->

## 标准化协议：`GpuCounterDescriptor`（2026-07-11 源码调研补）

> 本节补充内容来自 AOSP `android-17.0.0_r1` 中 `external/perfetto`（同步自上游 `google/perfetto` `main` 分支）的一手 proto 与 trace-processor 源码引用。

### 协议层固定的语义骨架

`protos/perfetto/common/gpu_counter_descriptor.proto` 给出三层结构：

1. **8 类固定语义分组**（`GpuCounterGroup`）：
   `UNCLASSIFIED=0; SYSTEM=1; VERTICES=2; FRAGMENTS=3; PRIMITIVES=4; MEMORY=5; COMPUTE=6; RAY_TRACING=7`
   ——这是协议层硬约束，所有 OEM producer 必须从此枚举取值。
2. **41 项度量单位**（`MeasureUnit`）：`next id: 41` 注释明确。覆盖 BIT/BYTE/HERTZ/SECOND/VERTEX/PIXEL/TRIANGLE/PRIMITIVE/FRAGMENT/MILLIWATT/WATT/JOULE/VOLT/AMPERE/CELSIUS/PERCENT/INSTRUCTION 等。**派生单位**用 `numerator_units` × `denominator_units` 表达，如 `PIXEL/SECOND` 即"每秒像素"。
3. **`GpuCounterSpec`**：单条计数器声明，字段含 `counter_id, name, description, peak_value, numerator_units, denominator_units, select_by_default, groups, value_direction`。其中 `value_direction`（`BACKWARDS_LOOKING` vs `FORWARDS_LOOKING`，issue #5683）是近年新增的跨 producer 一致性关键字段——AGI/历史 producer 约定为 BACKWARDS（采样时刻之前的窗口），新规约倾向 FORWARDS（之后窗口）。两种约定下同一组数据在 UI 上的峰值会偏移一个采样周期。

### 硬件 counter island 建模

`GpuCounterBlock { block_id, block_capacity, name, counter_ids }` 字段用于描述一组计数器共享同一硬件 block 时的**同时启用上限**。因此 UI 或自动化采集脚本在配置 `counter_ids` 时不能只按名称平铺选择，而应按 `block_id`/`block_capacity` 做 grouping-aware 选取；否则可能在厂商 producer 或 driver 层被拒绝。

### 事件流：两种 emission 模式

`protos/perfetto/trace/gpu/gpu_counter_event.proto`：

```proto
message GpuCounterEvent {
  oneof desc {
    GpuCounterDescriptor counter_descriptor = 1;   // Mode 1：CDD/CTS 合规
    uint64 counter_descriptor_iid = 4;             // Mode 2：interned
  }
  message GpuCounter { optional uint32 counter_id = 1;
    oneof value { int64 int_value = 2; double double_value = 3; } }
  repeated GpuCounter counters = 2;
  optional int32 gpu_id = 3;
}
```

源码注释明确：
- **Mode 1**（descriptor 直挂）是"Android OEMs to be compliant with CDD/CTS tests"的**必须**路径。
- **Mode 2**（`InternedGpuCounterDescriptor` + `iid`）适用于多 producer、多 GPU 场景，能节省 `(descriptor_size - 8) bytes`/packet。

数据源注册字段：`DataSourceConfig.gpu_counter_config = 108 [lazy = true]`（`protos/perfetto/config/data_source_config.proto`），`[lazy = true]` 表示仅 GPU counter data source 启动时才解析。

### Trace Processor 端的状态机

`src/trace_processor/importers/proto/gpu_counter_sequence_state.h`：

```cpp
struct GpuCounterSequenceState : PacketSequenceStateGeneration::CustomState {
  struct CounterTrackInfo { TrackId track_id; bool forwards_looking; };
  // Key: counter_descriptor_iid. Value: per-descriptor map of counter_id -> track info.
};
```

注释明确：**两个不同 producer 必然位于不同 packet sequence**（因此不同 IncrementalState），`iid` 即使冲突也不会相互污染。descriptor 在 tokenization 阶段就物化到 track（"the descriptors are parsed once at tokenization time (tracks interned, counter groups inserted)"），避免每次 GpuCounterEvent 都查表。

### 上层 SQL 视图模板

`src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql`：

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

`{{counter_name}}` 在编译期替换为具体 counter 名，`LEAD() + PARTITION BY track_id` 是把瞬时采样点序列转换为区间持续时间（dur = 下一采样时刻 - 当前采样时刻）的标准手法。`gpu_id IS NOT NULL` 用于排除 CPU 计数器行。

测试用例（`test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto`）展示了 AGI / Perfetto UI 默认期望的**标准 counter 名**：
- `"GPU Frequency"`（`denominator_units: SECOND` → 实际为 Hz）
- `"Fragments / vertex"`（`FRAGMENT / VERTEX`）
- `"Fragment / Second"`（`PIXEL / SECOND`）
- `"Triangle Acceleration"`（`TRIANGLE / (MILLISECOND·MILLISECOND)`）

→ 跨厂商基准建立时，应优先寻找这些同名或同单位语义的 counter；若 OEM producer 没有直接 emit 同名项，则需要在来源映射中显式说明替代关系，不能把不同语义的 counter 强行归一。

### GPU 内存事件的平台级标准化

`protos/perfetto/trace/gpu/gpu_mem_event.proto`：

```proto
// Generated by Android's GpuService.
message GpuMemTotalEvent {
  optional uint32 gpu_id = 1;
  optional uint32 pid = 2;
  optional uint64 size = 3;
}
```

注释明确"由 Android 的 GpuService 生成"——这是**Android 平台原生 producer**，与厂商 GPU counter producer 平行。`pid + gpu_id + size` 提供进程级 GPU 内存占用报告，可作为跨设备 GPU 内存池基准。

### 性能影响（基于源码推断）

1. **Trace 体积**：若粗略按每个 `GpuCounter` 采样含 `counter_id + int_value` ≈ 12 bytes 估算，启用 50 counter × 60s × 1kHz 采样约为 36,000,000 bytes（约 34.3 MiB）单独贡献（仅此 data source，未计 packet/framing/interning 开销）。
2. **Interned 模式**比直挂 descriptor 节省 (descriptor_size − 8) bytes/包，长 trace 下显著。
3. **`block_capacity` 上限**是 UI 选取 counter 的硬约束，必须 grouping-aware。

### 已知盲区（一手未验证）

- AOSP `gpucounterservice` 真实路径（`/frameworks/native/services/gpucounterservice/` 还是其他 SELinux-protected 进程）未抓到——cs.android.com 401。
- CDD/CTS 中是否枚举了"必选"counter 名（`GPU Frequency`、`GPU Utilization %` 等）的官方清单，需翻 CDD 文档一手确认。
- AGI / GAPIC 跨厂商标准化映射层的具体实现（`gapic/.../perfetto/models/CombinedCountersTrack.java` 之外是否还有）未完整追踪。
- Xclipse (Samsung AMD RDNA) 是否上游了独立 producer 待验证。

### 信息源

所有引用均来自 `github.com/google/perfetto` `main` 分支（与 AOSP `android-17.0.0_r1` 中的 `external/perfetto` 同步）：
- `protos/perfetto/common/gpu_counter_descriptor.proto`
- `protos/perfetto/trace/gpu/gpu_counter_event.proto`
- `protos/perfetto/config/gpu/gpu_counter_config.proto`
- `protos/perfetto/config/data_source_config.proto`
- `protos/perfetto/trace/gpu/gpu_mem_event.proto`
- `src/trace_processor/importers/proto/gpu_counter_sequence_state.h`
- `src/trace_processor/metrics/sql/android/gpu_counter_span_view.sql`
- `test/trace_processor/diff_tests/parser/graphics/gpu_counter_specs.textproto`

<!-- AIW-源码调研-2026-07-11 -->

## Task6 复查入口

- **已可复查**：`GpuCounterDescriptor`/`GpuCounterEvent`/`GpuMemTotalEvent` 的字段语义、descriptor intern 模式、trace processor track 建模与 SQL span 视图。
- **复查重点**：确认上述路径在 `android-17.0.0_r1` 中与上游 Perfetto main 的同步边界，避免把后续 mainline 变化误写成本章结论。
- **不得自动晋升的缺口**：工作负载阈值、Ray Tracing、NPU/ML 协同、profileable 权限差异、AGI 工作流仍缺一手材料，本轮只在 outline 标注“待补材料”。
