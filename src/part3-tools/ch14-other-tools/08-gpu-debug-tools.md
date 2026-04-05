---
title: "GPU 图形调试与分析工具"
chapter: "14.8"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [gpu, agi, renderdoc, gapid, profiling, graphics]
related_chapters: ["2.10", "14.1", "13.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "AOSP结构+官方文档+研究素材"
---

# 14.8 GPU 图形调试与分析工具

<!-- outline-start -->
## 要点

### 🔹 锚点 1：为什么需要专门的 GPU 分析工具
- CPU profiling 工具（Perfetto/Simpleperf）无法看到的 GPU 内部状态
- GPU 分析的独特价值：shader 执行、draw call 开销、带宽利用率
- GPU 分析与 CPU 分析的互补关系
- 不同 GPU 分析场景：游戏、UI 渲染、视频解码

### 🔹 锚点 2：Android GPU Inspector (AGI)
- AGI 的定位与功能（原 GAPID 的继任者）
- AGI 的 Frame Profiler：逐 draw call 的 GPU 时间分析
- AGI 的 System Profiler：系统级 GPU 利用率追踪
- AGI 的 Vulkan 和 GLES 支持
- 如何使用 AGI 捕获和分析一个完整的渲染帧

### 🔹 锚点 3：Perfetto 中的 GPU 分析能力
- GPU counter track 的启用与配置
- 关键 GPU 指标解读：GPU frequency、GPU utilization、memory bandwidth
- GPU activity slice（Vulkan/GLES 提交）在 Perfetto 中的表现
- GPU 协议（gpu.mem、gpu.frequency）的 TraceConfig 配置

### 🔹 锚点 4：RenderDoc 在 Android 上的使用
- RenderDoc 的 Android 远程调试能力
- Frame Capture：捕获单帧的所有 draw call 和资源状态
- Texture Viewer：查看每个 render target 的中间结果
- Pipeline State：逐阶段分析渲染管线状态
- Shader Debugger：单步调试 shader 执行

### 🔹 锚点 5：GPU 性能分析的核心指标
- GPU 时间 vs CPU 时间：如何判断瓶颈在 CPU 还是 GPU
- Draw call 数量对性能的影响
- Overdraw 在 GPU 层面的开销
- Shader 复杂度与 GPU ALU 利用率
- 带宽瓶颈的识别与优化

### 🔹 锚点 6：实战案例：GPU 性能分析与优化
- 案例 1：游戏场景中 GPU 帧时间过长的分析（AGI）
- 案例 2：UI 渲染中 GPU 带宽瓶颈的诊断（Perfetto GPU counter）
- 案例 3：Shader 编译卡顿的识别与预热策略

## 扩展

### 🔸 扩展点 1：不同 GPU 厂商的专用工具
- Adreno Profiler（高通）
- ARM Streamline + Mali GPU 工具
- MediaTek GPU 分析工具
- 不同工具的数据与 Perfetto/AGI 的对比

### 🔸 扩展点 2：GPU 分析的注意事项
- GPU profiling 的性能开销（特别是全帧捕获）
- profileable vs debuggable 对 GPU 工具的影响
- GPU 工具在不同 Android 版本上的可用性

<!-- outline-end -->

> 本节内容待加工。
