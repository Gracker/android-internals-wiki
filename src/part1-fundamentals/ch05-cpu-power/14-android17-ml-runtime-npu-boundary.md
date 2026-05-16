---
title: "Android 17 ML Runtime 与 NPU 访问边界"
chapter: "5.14"
status: draft
applicable_versions: "Android 14 (API 34) - Android 17 (API 36)"
tags: [android17, litert, npu, nnapi, on-device-ai, performance]
related_chapters: ["5.11", "5.13", "16.5", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/官方文档/AOSP结构"
gap_score: 18
material_count: 5
source_refs:
  - DeepResearch/2026-05-15-android-17-npu-litert-aicore.md
  - DeepResearch/2026-05-15-android-ml-inference-npu-litert.md
  - https://developer.android.com/ai/custom
  - https://developer.android.com/blog/posts/the-second-beta-of-android-17
  - https://developer.android.com/ndk/guides/neuralnetworks/migration-guide
---

# 5.14 Android 17 ML Runtime 与 NPU 访问边界

<!-- outline-start -->
## 要点

### 🔹 NPU 能力声明与 Android 17 访问限制
区分 `android.hardware.neural_processing_unit` 声明、PackageManager feature 检测、目标 API 约束，以及未声明时的直接 NPU 访问边界。

### 🔹 LiteRT CompiledModel 的执行模型
梳理 `CompiledModel`、`Accelerator.NPU/GPU/CPU` fallback、模型加载、输入输出 buffer 与运行时调度路径。

### 🔹 AOT 编译与 AI Pack 分发
说明主机侧编译、设备 SoC 匹配、Google Play AI Pack 下发、首次推理延迟和包体积之间的取舍。

### 🔹 NNAPI HAL 与厂商 NPU delegate
连接 `hardware/interfaces/neuralnetworks/1.3/`、QNN/Neuron 等厂商 delegate、支持 op 查询和 partial delegation。

### 🔹 端侧推理的性能与功耗边界
围绕 TTFT、单次推理延迟、峰值内存、热降频、后台限制建立可观测指标。

### 🔹 公开 API、Preview 能力与闭源组件边界
标清 LiteRT、NNAPI、AICore、厂商 SDK 的可验证范围，避免把 GMS 闭源能力误写成 AOSP 公共能力。

## 扩展

### 🔸 Google Tensor / EdgeTPU 能力验证
补充 Tensor 设备上 NPU delegate 的公开能力与待验证项。

### 🔸 LiteRT 与旧 TFLite/NNAPI 迁移对照表
整理旧项目从 TFLite delegate 迁移到 LiteRT 的工程检查清单。

<!-- outline-end -->

> 本节内容待加工。
