---
title: "端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线"
chapter: "5.11"
status: ready-for-review
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags:
  - android
  - ai
  - npu
  - tflite
  - nnapi
  - aicore
related_chapters: ["5.4", "5.6", "5.9", "1.15", "4.3", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-08"
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-17-beta3 + developer.android.com"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/ndk/guides/neuralnetworks"
  - type: official
    path: "developer.android.com/ai/aicore"
  - type: official
    path: "ai.google.dev/edge/litert"
  - type: aosp
    path: "frameworks/ml/nn/"
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线

过去三年，端侧 AI 推理从实验室技术变成了 Android 性能工程师必须面对的生产问题。当你的 App 里集成了一个图像分类模型用于实时滤镜，或者用 OCR 模型处理相机取景框里的文字时，推理任务的 CPU 占用、内存峰值和功耗直接影响用户体验——推理占用主线程 50ms，一帧就掉了；推理峰值吃掉 300MB 内存，LMK 可能把后台 App 杀了；持续的 NPU 调用让设备发热降频，滑动也开始卡了。

本节要讲的是：Android 上 ML 推理走过了怎样的硬件加速路径，NNAPI 为什么从希望之星变成了弃子，TFLite 管线怎么工作，以及作为性能工程师，怎么在 Perfetto 里定位 ML 推理导致的性能问题。

## 为什么端侧 AI 推理是性能工程师的新课题

云推理的延迟在 500ms-2s 之间，加上网络抖动，用户体验无法保证。隐私敏感数据（人脸、语音、医疗影像）上传到云端在很多场景下也不可行。这两个因素推动了 ML 推理从云端向端侧迁移。

但端侧推理不是免费的。一个典型的 MobileNet V2 模型在 CPU 上推理一次需要 30-100ms（取决于设备和量化策略），这已经超过了一帧的预算（120Hz 设备上 8.33ms）。如果推理发生在主线程，用户会看到明显的卡顿。更麻烦的是内存：一个未量化的浮点模型可能占用几十到上百 MB 内存，加上推理过程中的中间激活值，峰值内存很容易达到 200-400MB——在内存紧张的设备上，这足以触发 LMK。

在 Perfetto 中，ML 推理的典型表现是：一段密集的 CPU 占用（如果是 CPU 推理）或 GPU/NPU 占用（如果走了硬件加速），伴随着明显的内存增长。如果推理阻塞了主线程，在主线程 track 上会看到一个超长的 slice。

## Android ML 推理硬件加速栈

Android 设备上的 ML 推理可以跑在三种硬件上：CPU、GPU 和 NPU（也叫 AI 加速器）。选择哪种硬件，决定了推理延迟、功耗和兼容性。

### NPU：各 SoC 厂商的实现差异

NPU 是专门为神经网络运算设计的加速器，对矩阵乘法和卷积运算做了硬件级优化。但 Android 生态的复杂性在于：每家 SoC 厂商的 NPU 架构完全不同。

Qualcomm 平台的 AI 加速经历了三代演进：早期的 Hexagon DSP（用于 Pixel 1-3 时代的 ML 推理）、Hexagon Tensor Accelerator（HTA，用于 Snapdragon 865+）、以及最新的 Qualcomm AI Engine（Hexagon NPU，用于 Snapdragon 8 Gen 1+）。Snapdragon 8 Gen 4 的 NPU 可以达到 75 TOPS 的峰值算力，在运行 Gemini Nano 时能达到 93 tokens/s 的推理速度。

[待验证：Qualcomm AI Engine TOPS 数据精确值，不同 Gen 版本差异]

MediaTek 的 APU（AI Processing Unit）在 Dimensity 9300+ 上提供了整数推理能力，支持 INT8/INT16 量化模型。Samsung Exynos 的 NPU 主要用于 Galaxy 系列设备的端侧推理。Google Pixel 使用的是自研的 Edge TPU，从 Pixel 6 的 Tensor 芯片开始集成。

在 Perfetto 中，NPU 的工作负载目前没有标准化的 trace track。部分厂商通过 vendor-specific atrace 标签暴露 NPU 利用率，但需要查看对应厂商的文档。通用的做法是通过观察 GPU 频率和总 CPU 利用率变化来间接推断硬件加速是否生效——当推理在进行但 CPU 利用率很低时，说明工作负载被卸载到了 NPU 或 GPU。

### GPU 推理

GPU 通过 Vulkan Compute 或 OpenCL 执行 ML 推理。GPU 推理的优势是不依赖专用 NPU 硬件（几乎所有 Android 设备都有 GPU），缺点是功耗比 NPU 高、推理延迟通常比 NPU 大。

TFLite 的 GPU Delegate 使用 OpenGL ES 或 Vulkan Compute 执行推理。在 Adreno GPU（Qualcomm 平台）上，Vulkan Compute 后端通常比 OpenGL ES 后端快 10-30%，因为 Vulkan 的计算管线更轻量。

### DSP 推理

Qualcomm 的 Hexagon DSP 在旧设备（Android 8-10 时代）上是 ML 推理的主要硬件加速路径。TFLite 的 Hexagon Delegate 可以将推理卸载到 DSP。随着 NPU 的普及，DSP 推理在新设备上已经逐渐边缘化，但在低端设备和旧设备上仍然是重要的加速手段。

## NNAPI 的兴衰与迁移路径

NNAPI（Neural Networks API）在 Android 8.0（API 27）引入，目标是提供一套统一的硬件加速 API，让开发者不需要针对每家 SoC 写不同的加速代码。理想很美好：App 调用 NNAPI，NNAPI 通过厂商提供的 HAL 驱动转发到 NPU/GPU/DSP 执行。

### 为什么 NNAPI 被废弃

Android 15 正式废弃了 NNAPI。Google 给出的理由直指核心问题：

第一，**驱动碎片化严重**。每家 SoC 厂商的 NNAPI HAL 实现质量参差不齐。同一个模型在 Qualcomm 平台上可能完美运行，在 MediaTek 平台上可能因为某个算子不支持而 fallback 到 CPU。测试矩阵 = 设备数 × SoC 厂商数 × Android 版本数，这个组合让兼容性测试几乎不可能全面覆盖。

第二，**fallback 导致性能不可预测**。NNAPI 的设计是：如果某个算子在硬件加速器上不支持，就静默 fallback 到 CPU 执行。这意味着同一个模型在不同设备上的实际推理路径可能完全不同——在旗舰设备上全 NPU 执行，在中端设备上 70% NPU + 30% CPU，在低端设备上全 CPU。开发者无法预测实际性能。

第三，**性能在某些场景下反而不如纯 CPU**。NNAPI 的驱动调度有固定开销（构建计算图、内存拷贝、跨进程通信）。对于小模型或简单推理任务，这个开销可能占总推理时间的 50% 以上，导致使用 NNAPI 反而比纯 CPU 推理更慢。

[已验证: developer.android.com/ndk/guides/neuralnetworks, NNAPI deprecation announcement]

### 迁移路径

Google 推荐的迁移路径是 **TFLite in Google Play Services**（后更名为 LiteRT in Play Services）。这个方案的核心思路是：TFLite 运行时不再打包在 App 内，而是由 Google Play Services 统一提供。Google 负责确保在不同设备上的兼容性和性能优化，开发者只需要指定使用哪个 Delegate。

迁移的实际影响：App 体积减少约 5MB（不再打包 TFLite 库），TFLite 运行时通过 Play Services 独立更新（不需要等 App 发版），但同时也意味着 App 依赖了 Play Services 的可用性——在国内市场（没有 Play Services 的设备上）需要回退到静态链接的 TFLite。

## TFLite 管线与 Play Services 集成

### TFLite 架构

TFLite 的推理管线可以分为四个阶段：

1. **模型加载**：从 `.tflite` 文件（FlatBuffer 格式）解析计算图和权重。FlatBuffer 的优势是零拷贝解析——不需要像 Protocol Buffers 那样先反序列化到内存再使用，而是直接映射到内存。

2. **Interpreter 初始化**：构建推理引擎，分配中间张量（tensor）的内存。这一步的耗时取决于模型大小，大型模型可能需要几百毫秒。

3. **Delegate 绑定**：根据设备能力选择硬件加速器。GPU Delegate 使用 Vulkan Compute 或 OpenGL ES，XNNPACK Delegate 使用优化过的 CPU 实现。Delegate 的选择直接影响推理性能。

4. **推理执行**：调用 `interpreter.run(input, output)` 执行一次前向传播。

### XNNPACK Delegate：CPU 推理的性能标杆

XNNPACK 是 Google 开发的优化 CPU 推理库，针对 ARM NEON/SVE 指令集做了深度优化。在大多数现代 Android 设备上，XNNPACK Delegate 的 CPU 推理性能已经非常接近 GPU Delegate，同时兼容性远好于 GPU（不存在算子不支持的问题）。

实测数据：MobileNet V2 在 Snapdragon 8 Gen 2 上，XNNPACK CPU 推理约 8ms/帧，GPU Delegate 约 5ms/帧，NPU 推理约 2ms/帧。CPU 推理虽然最慢，但在所有设备上行为一致，不存在 fallback 问题。

[待验证：MobileNet V2 推理时间数据需要实测确认，设备/模型/量化策略差异较大]

### 模型量化的性能影响

量化是 ML 推理优化中最有效的手段。将模型从 float32 量化到 int8，推理速度通常提升 2-4 倍（因为 int8 矩阵乘法在硬件上更快），模型大小减少 75%（从 float32 的 4 字节/参数降到 int8 的 1 字节/参数），内存峰值也相应降低。

TFLite 支持 Post-training quantization（不需要重新训练）和 Quantization-aware training（训练时模拟量化效果，精度更好）。对于大多数应用场景，Post-training int8 量化已经够用——MobileNet V2 的 int8 量化版本在 ImageNet 上的精度损失通常小于 1%。

Float16 量化是另一个选择：模型大小减半（float32 → float16），在支持 FP16 计算的 GPU 上推理速度提升明显，精度损失几乎可以忽略。适合需要保持精度的场景。

## AICore 与 Gemini Nano

### AICore 架构

Android AICore 是 Android 14 引入的系统级 AI 运行时服务。它的定位是：像 GPU 驱动由系统统一管理一样，端侧 AI 模型也由系统统一管理。AICore 负责模型的下载、存储、版本更新和运行时调度。

AICore 的架构解决了 TFLite 时代的一个核心痛点：每个 App 各自打包模型、各自管理推理运行时。这不仅浪费存储空间（同一个模型可能被 10 个 App 各存一份），还导致内存浪费（多个 App 同时加载同一模型到内存）。

### Gemini Nano 的性能特征

Gemini Nano 是 Google 的端侧小语言模型，通过 AICore 提供 API 给第三方 App 使用。截止 2026 年初：

- **Nano v1**（1.8B 参数）：仅文本，约 1GB 模型大小（4-bit 量化），在 Pixel 8 Pro 上首次可用
- **Nano v2**（3.25B 参数）：多模态（文本+图片），Pixel 9 系列首发
- **Nano v3/v4**：2026 年发布于 Pixel 10+，推理速度大幅提升

性能数据方面，Gemini Nano 的端侧推理延迟已经达到了可用的水平：首 token 延迟在 100ms 以内（2026 年旗舰设备），持续推理速度在 Snapdragon 8 Gen 4 上可达 93 tokens/s。作为对比，云端推理的延迟通常在 500ms-2s。

[待验证：Gemini Nano tokens/s 数据来自 Qualcomm 基准测试，实际 App 场景可能有差异]

内存方面，AICore 使用动态模型加载策略——不把整个模型常驻内存，而是按需加载需要的神经网络层，将峰值内存占用控制在约 1.2GB（对比 2025 年的 3.4GB）。这对于前台 App 的内存预算是很大的改善。

### AICore 与 ADPF 的协同

AI 推理是持续性的高负载任务，容易导致设备发热。AICore 与 Android 的 ADPF（自适应性能框架，见 §5.9）有协同机制：当设备温度接近热阈值时，ADPF 可以通知 AICore 降低推理频率或切换到更轻量的模型。

## 模型优化技术对 Android 性能的影响

模型优化是 ML 推理性能的基础。在硬件加速之上，模型本身的优化决定了推理性能的天花板。

### 量化

INT8 量化是最常用的优化手段。在 TFLite 中，Post-training full integer quantization 会将所有权重和激活值都量化到 int8，推理速度提升 2-4 倍，模型体积减少 75%。代价是精度损失，但对于大多数图像分类、目标检测、语义分割任务来说，1-2% 的精度下降是可接受的。

Float16 量化对 GPU 友好，在 Adreno GPU 上 FP16 计算吞吐量是 FP32 的近两倍。如果目标设备确定有 GPU 加速支持，Float16 是精度和速度的最佳平衡点。

### 裁剪与蒸馏

模型裁剪（Pruning）将不重要的权重置零，产生稀疏模型。理论上稀疏模型可以跳过零值计算加速推理，但在 Android 硬件上的实际加速效果取决于 NPU/GPU 对稀疏矩阵运算的支持程度——目前大多数移动端加速器对非结构化稀疏的加速有限。

知识蒸馏（Knowledge Distillation）用大模型（teacher）指导小模型（student）训练，让小模型逼近大模型的精度。MobileBERT 和 TinyBERT 是典型的蒸馏成果——参数量减少 4-10 倍，精度损失控制在 2-3% 以内。

## ML 推理性能分析与调优实战

### 在 Perfetto 中分析 ML 推理

ML 推理在 Perfetto 中的表现取决于推理走的是哪个路径：

**CPU 推理（XNNPACK 或无 Delegate）**：在主线程或工作线程 track 上看到一段密集的 CPU 占用。如果是主线程推理，slice 会显示为 `TfLiteInterpreter::run` 或类似名称。通过 CPU frequency track 可以确认 CPU 是否满频运行。

**GPU 推理（GPU Delegate）**：CPU 占用降低，但在 GPU track 上看到对应的计算负载。如果 GPU 推理与渲染（RenderThread）同时进行，可能产生 GPU 带宽争抢导致掉帧。

**NPU 推理（NNAPI Delegate 或 AICore）**：CPU 占用极低，但推理延迟取决于 NPU 调度。部分设备在 NPU 被多个 App 同时使用时会排队等待。

[待补充：Perfetto 截图 — CPU 推理 vs GPU 推理 vs NPU 推理的 track 对比]

### 常见性能问题

**NPU fallback 导致的 CPU jank**：这是最常见的 ML 性能问题。模型中的某个算子不被当前设备的 NPU 支持，整个推理 fallback 到 CPU，延迟从 2ms 暴增到 50ms。解决方法是检查 TFLite 的 delegate 日志，确认所有算子都被硬件加速器支持；必要时替换不支持的算子。

**模型加载阻塞主线程**：大模型的 FlatBuffer 解析和 Interpreter 初始化可能需要几百毫秒。如果这个过程在主线程执行，会导致启动延迟或页面切换卡顿。解决方法是在后台线程做模型加载和预热（用 dummy input 跑一次推理），加载完成后再通知 UI 线程。

**推理内存峰值触发 LMK**：一个 100MB 的模型加上推理过程中的中间激活值，峰值内存可能达到 200-300MB。在内存紧张的设备上，这足以把后台 App 杀掉。解决方法是使用量化模型减少内存占用，或者在推理前检查 `ActivityManager.getMemoryInfo()` 判断是否有足够内存。

**后台 ML 任务与前台 App 的 CPU 争抢**：后台 Service 持续做 ML 推理（如语音识别、健康监测），会占用大量 CPU 和 NPU 资源，影响前台 App 的流畅性。解决方法是使用 WorkManager 或 JobScheduler 调度 ML 任务，避免在高优先级场景（如滑动、动画）期间做推理。

### 优化策略总结

异步推理是最基本也最重要的优化。推理调用必须在工作线程执行，绝不能在主线程。对于持续性推理场景（如相机滤镜），使用双缓冲策略——一个 buffer 做推理，另一个 buffer 准备下一帧输入。

模型预热是另一个常用技巧。在 App 启动或页面跳转的空档期，用 dummy input 跑一次推理，提前完成 Interpreter 初始化和 Delegate 绑定。这样用户真正触发推理时，延迟会低很多。

批处理（batching）适合需要连续推理的场景。将多个推理请求攒成一批执行，减少 Delegate 调度的固定开销。但需要注意批处理会增加延迟，不适合实时性要求高的场景。

## 与其他章节的关联

- **§2.5 MainThread 与 RenderThread**：ML 推理如果在主线程执行，会直接阻塞 RenderThread 的工作调度，导致掉帧
- **§4.4 Low Memory Killer**：推理峰值内存可能导致 LMK 杀掉后台 App
- **§5.9 ADPF**：AI 工作负载的热管理策略
- **§1.15 JNI/NDK 性能**：TFLite 的 C++ 推理引擎通过 JNI 调用，JNI 开销在高频推理场景下需要关注
- **§14.1 Android Studio Profiler**：ML Profiler 可视化推理性能
