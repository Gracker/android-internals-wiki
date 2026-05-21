---
title: "GPU/NPU 异构负载调度与功耗归因"
chapter: "5.16"
section: "5.16"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [gpu, npu, heterogeneous-compute, adpf, thermal, power]
related_chapters: ["5.3", "5.9", "5.11", "5.12", "5.13", "5.14", "17.2", "22.10", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "章节深挖/素材驱动/官方文档"
gap_score: 16
material_count: 6
source_refs:
  - "src/part1-fundamentals/ch05-cpu-power/03-big-little.md#扩展-GPU-NPU-的协同调度概念"
  - "DeepResearch/2026-05-20-android-17-npu-aicore-nnapi-research.md"
  - "DeepResearch/2026-05-15-android-17-npu-litert-aicore.md"
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-adpf-non-game-scenarios-and-profiling-trigger-type-anomaly.md"
  - "https://source.android.com/docs/core/perf/performance-hint-api"
  - "https://ai.google.dev/edge/litert/"
---

# 5.16 GPU/NPU 异构负载调度与功耗归因

<!-- outline-start -->
## 要点

### 🔹 异构负载不等于 CPU 空闲
说明 GPU/NPU 卸载后，CPU 仍承担输入预处理、buffer 搬运、delegate 调度、结果后处理和 UI 合成；性能归因要看端到端路径，而不是只看加速器子图耗时。

### 🔹 GPU、NPU、CPU 三类路径的适用边界
对比渲染类 GPU 负载、ML delegate / LiteRT NPU 负载、CPU fallback 的典型收益和代价，明确算子覆盖率、内存布局、同步等待和热状态对结果的影响。

### 🔹 ADPF 能表达线程工作量，不能直接控制加速器
梳理 `PerformanceHintManager.Session`、Power HAL、thermal headroom 与 GPU/NPU 频率之间的关系，避免把 ADPF 写成应用侧绑核、调频或 NPU 调度 API。

### 🔹 Perfetto 与厂商工具的观测分层
建立观测清单：CPU sched/freq、GPU frequency/counters、thermal status、power rails、FrameTimeline、delegate 日志和厂商 NPU trace；说明普通发布版设备上哪些信号可能不可见。

### 🔹 持续推理和前台交互的资源竞争
覆盖相机预览、实时翻译、AI 修图、游戏 AI 辅助等场景中，NPU/GPU 持续工作如何影响帧预算、温控和后台任务，交叉引用 5.13、22.10、25.11。

### 🔹 Android 17 NPU feature 与 LiteRT 迁移后的新边界
把 `android.hardware.neural_processing_unit`、LiteRT `CompiledModel`、NNAPI deprecated、厂商 delegate 与 AICore 生态能力拆开，形成可发布事实表。

## 扩展

### 🔸 GPU/NPU 与 EAS / devfreq cooling 的交互
从调度器、devfreq cooling、thermal governor 角度说明 CPU 线程迁移、GPU/NPU 降频和功耗预算共享的分析方法。

### 🔸 端侧 AI 性能实验模板
给出同机型 CPU / GPU / NPU 对照、冷启动 / 稳态、p50 / p90 / p99、功耗与温度的实验字段清单。

### 🔸 厂商 SoC 差异与可迁移结论
整理 Qualcomm、MediaTek、Tensor 等平台的公开能力边界，避免把单个平台的 delegate 行为写成 Android 通用结论。

<!-- outline-end -->

> 本节内容待加工。
