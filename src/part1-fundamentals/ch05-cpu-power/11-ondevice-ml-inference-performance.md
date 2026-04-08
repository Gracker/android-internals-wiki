---
title: "端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线"
chapter: "5.11"
status: draft
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [ai-inference, npu, tflite, nnapi, aicore, hardware-acceleration, power]
related_chapters: ["5.4", "5.6", "5.9", "1.15", "4.3", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
gap_source: "AOSP结构+官方文档+读者需求+时效性"
gap_score: "15/20"
---

# 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线

<!-- outline-start -->
## 要点

### 🔹 为什么端侧 AI 推理是性能工程师的新课题
- 从云端推理到端侧推理的产业趋势：延迟、隐私、离线可用性
- Android 上 ML 推理的性能影响维度：CPU 占用、GPU/NPU 调度、内存峰值、功耗
- 哪些场景受影响最大：图像分类、OCR、语音识别、实时滤镜、LLM 推理
- NNAPI 在 Android 15 废弃的背景和替代方案

### 🔹 Android ML 推理硬件加速栈
- NPU（Neural Processing Unit）：各 SoC 厂商的实现差异（Qualcomm Hexagon DSP/HTA → AI Engine → Snapdragon X Elite NPU、MediaTek APU、Samsung NPU、Google Edge TPU）
- GPU 推理：Vulkan Compute、OpenCL、Adreno GPU 的 ML 工作负载
- DSP 推理：Hexagon DSP 在旧设备上的角色
- Android 硬件加速器抽象层：IPeripheralController 与 IDeviceFactory
- 在 Perfetto 中如何观察 NPU/GPU 的 ML 工作负载

### 🔹 NNAPI 的兴衰与迁移路径
- NNAPI（Android 8.0 引入，Android 15 废弃）的设计目标与局限
- NNAPI 驱动模型：厂商 HAL 实现 → ANeuralNetworksDevice → 应用层
- NNAPI 废弃原因：驱动碎片化、版本兼容性噩梦、性能不可预测
- 迁移路径：NNAPI → TFLite in Play Services + NnApiDelegate → 直接 GPU/DSP
- NNAPI 废弃对性能的影响：迁移期间的 fallback 开销

### 🔹 TFLite 管线与 Play Services 集成
- TFLite 架构：FlatBuffer 模型格式 → Interpreter → Delegate 链 → 硬件执行
- TFLite in Play Services：独立于 App 更新的运行时、Google 负责兼容性
- Delegate 机制：GPU Delegate、NNAPI Delegate（过渡期）、Core ML Delegate
- TFLite 性能调优：线程数配置、XNNPACK Delegate、模型量化（INT8/Float16）
- TFLite 性能数据：量化后推理延迟降低 2-4x、内存占用降低 75%

### 🔹 AICore 与 Gemini Nano
- Android AICore 架构：系统级 AI 运行时、进程内/跨进程调用模式
- Gemini Nano 的 Android 集成：通过 AICore API 访问、多模态扩展
- AICore 性能特征：模型加载时间、推理延迟、内存占用、NPU 调度策略
- AICore 与 ADPF（§5.9）的协同：AI 工作负载的热管理与性能提示
- Android 16/17 AICore 新特性

### 🔹 模型优化技术对 Android 性能的影响
- 量化（Quantization）：Post-training quantization vs Quantization-aware training
  - INT8 量化：推理速度 2-4x 提升，精度损失取决于模型
  - Float16 量化：GPU 友好，精度几乎无损
  - 混合量化：关键层保持高精度
- 模型裁剪（Pruning）：稀疏模型对 Android 硬件的实际加速效果
- 知识蒸馏（Knowledge Distillation）：大模型→小模型，MobileBERT/TinyBERT 案例
- 这些优化在 Android 上的实测数据

### 🔹 ML 推理性能分析与调优实战
- Android Studio ML Profiler 的使用方法
- 使用 Perfetto 分析 ML 推理：CPU/GPU/NPU 利用率、线程调度、内存分配模式
- 常见性能问题：
  - NPU 不可用时的 CPU fallback 导致 jank
  - 模型加载阻塞主线程
  - 推理内存峰值触发 LMK
  - 后台 ML 任务与前台 App 的 CPU 争抢
- 优化策略：异步推理、模型预热、内存池化、批处理

## 扩展

### 🔸 Core ML 与 Android ML 的跨平台对比
- iOS Core ML vs Android TFLite 的硬件加速差异
- 跨平台 ML 框架（ONNX Runtime Mobile、PyTorch Mobile）在 Android 上的性能表现

### 🔸 Android 17+ ML 推理趋势
- AppFunctions 与 Gemini Agent 生态对端侧推理的新需求
- 系统级 AI 的性能预算与资源隔离
- 端侧 LLM 推理（4B-8B 参数模型）在手机上的可行性分析

<!-- outline-end -->

> 本节内容待加工。
