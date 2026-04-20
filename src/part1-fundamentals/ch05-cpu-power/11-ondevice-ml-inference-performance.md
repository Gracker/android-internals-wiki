---
title: "端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线"
chapter: "5.11"
status: ready-for-review
applicable_versions: "Android 8.1 (API 27) - Android 17 (API 37)"
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
last_verified: "2026-04-12"
last_verified_against: "AOSP android-17-beta3 + developer.android.com + ai.google.dev/edge/litert/android/gpu"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/ndk/guides/neuralnetworks"
  - type: official
    path: "developer.android.com/ai/aicore"
  - type: official
    path: "ai.google.dev/edge/litert/android/gpu"
  - type: aosp
    path: "frameworks/ml/nn/"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-20"
task6_result: pass-light-edit
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-04-20"
last_task9_at: "2026-04-20T08:57:48+08:00"
---

# 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线

过去三年，端侧 AI 推理从实验室技术变成了 Android 性能工程师必须面对的生产问题。当 App 把图像分类、OCR、语音理解或生成式模型塞进前台交互过程后，推理任务就会直接占用 CPU 时间片、拉高内存峰值，并持续推动 GPU / NPU / thermal 子系统进入高负载状态。它不只是“AI 功能能不能跑起来”的问题，更是掉帧、发热、后台进程被杀和续航下降会不会一起冒出来的问题。

本节要讲的是：Android 上 ML 推理走过了怎样的硬件加速路径，NNAPI 为什么从统一加速入口走向废弃，LiteRT / TFLite 管线怎么工作，以及作为性能工程师，怎样把 Delegate 选择、内存代价、热压力和 Perfetto 证据链连起来。

## 为什么端侧 AI 推理是性能工程师的新课题

云推理首先受延迟和可用性限制。网络一抖，前台交互就跟着抖；隐私敏感数据也未必适合上传云端。这两个因素把越来越多的推理任务推回到设备本地。

但端侧推理也会把原本分散的成本压回手机上。模型权重、临时 tensor、delegate 初始化、硬件调度、持续高负载带来的热约束，都会直接映射到卡顿和功耗问题。在 Perfetto 里，我们通常先看到线程繁忙、频率抬升、内存水位变化或 thermal 回调，再顺着这些信号反推是不是推理过程本身出了问题。

## Android ML 推理硬件加速栈

Android 设备上的 ML 推理可以跑在三种硬件上：CPU、GPU 和 NPU（也叫 AI 加速器）。选择哪种硬件，决定了延迟、功耗、兼容性，以及后续能不能在 Trace 里把问题看清楚。

### NPU：各 SoC 厂商的实现差异

NPU 是为张量乘加、卷积和 attention 这类运算准备的专用加速器，但 Android 生态里并不存在一个“统一 NPU”。Qualcomm、MediaTek、Samsung、Google 都有各自的硬件和 runtime。对性能工程师来说，更有用的是把注意力放在三件事上：当前模型能不能完整落到该加速器上，fallback 会不会回到 CPU，以及在 Trace 里有没有对应的可观测证据。

Qualcomm 的公开路径从 Hexagon DSP 逐步演进到 HTA 和更新的 AI Engine / NPU；MediaTek 使用 APU；Google Tensor 平台则有自己的端侧 AI 加速路径。这些代际名字可以帮助我们理解生态演进，但单独引用 TOPS、tokens/s 或“某代首 token 延迟”帮助不大，因为它们强依赖模型大小、量化方式、prefill / decode 口径和测试负载。

在 Perfetto 里，NPU 工作负载没有统一的标准 track。部分厂商会暴露 vendor tracepoint 或 atrace 标签，更多时候我们只能通过 CPU 利用率下降、GPU 频率变化、thermal 状态和 delegate 日志做交叉判断。只看一个 counter，通常不够。

### GPU 推理

公开的 Android GPU Delegate 文档主要围绕 OpenCL 和 OpenGL ES 展开，具体后端取决于设备驱动、运行时版本和 delegate 实现。把 Android 上的 LiteRT / TFLite GPU 路径直接写成“Vulkan Compute 或 OpenCL”，会把边界写满；如果要谈 Vulkan，更合适的写法是把它单列为图形 / 计算栈背景，不把它当成当前 LiteRT Android 默认公开 delegate 路径。

GPU 推理的优点是覆盖面广，几乎所有现代 Android 设备都有可用 GPU；缺点是它会和渲染共享带宽、功耗和热预算。只要同一时段还有 RenderThread、SurfaceFlinger 或相机预处理一起抢 GPU，GPU Delegate 的收益就需要放回整段渲染过程里评估。

[已验证: ai.google.dev/edge/litert/android/gpu, Android GPU delegate public docs focus on OpenCL / OpenGL ES]

### DSP 推理

Qualcomm 的 Hexagon DSP 在旧设备（Android 8-10 时代）上是 ML 推理的主要硬件加速路径。TFLite 的 Hexagon Delegate 可以将推理卸载到 DSP。随着 NPU 的普及，DSP 推理在新设备上已经逐渐边缘化，但在低端设备和旧设备上仍然是重要的加速手段。

## NNAPI 的兴衰与迁移路径

NNAPI（Neural Networks API）在 Android 8.1（API 27）引入，目标是提供统一的硬件加速入口，让上层框架把模型提交给系统，再由厂商驱动决定跑在 NPU、GPU 还是 DSP 上。

### 为什么 NNAPI 被废弃

Android 官方文档现在明确把 NNAPI 标为 deprecated，并建议对性能敏感 workload 迁移到其他路径，例如 TF Lite GPU runtime。问题并不神秘：

第一，**驱动碎片化严重**。每家 SoC 厂商的 NNAPI HAL 实现质量参差不齐。同一个模型在 Qualcomm 平台上可能正常运行，在 MediaTek 平台上可能因为某个算子不支持而 fallback 到 CPU。兼容性测试很快会变成设备数 × SoC 厂商数 × Android 版本数的组合问题，几乎不可能全面覆盖。

第二，**fallback 导致性能不可预测**。NNAPI 的设计是：如果某个算子在硬件加速器上不支持，就静默 fallback 到 CPU 执行。同一个模型在不同设备上的实际推理路径可能完全不同，在旗舰设备上是全 NPU 执行，在中端设备上可能是部分 NPU + 部分 CPU，在低端设备上则可能全程跑在 CPU 上。开发者很难提前预测实际性能。

第三，**性能在某些场景下反而不如纯 CPU**。NNAPI 的驱动调度有固定开销（构建计算图、内存拷贝、跨进程通信）。对于小模型或简单推理任务，这个开销可能已经足够抵消硬件加速带来的收益。

[已验证: developer.android.com/ndk/guides/neuralnetworks, NNAPI available on Android 8.1 (API 27)+ and deprecated in Android 15]

### 迁移路径

Google 推荐的迁移方向是 **TFLite in Google Play Services**，现在的命名是 **LiteRT in Play Services**。运行时不再由每个 App 单独打包，而是由 Google Play Services 提供和更新。这样做的好处是兼容性修复和运行时升级可以脱离 App 发版；代价是要同时考虑 GMS 依赖，以及没有 Play Services 时的回退路径。

## LiteRT / TFLite 管线与 Play Services 集成

### LiteRT / TFLite 架构

LiteRT / TFLite 的推理管线可以分为四个阶段：

1. **模型加载**：从 `.tflite` 文件（FlatBuffer 格式）解析计算图和权重。FlatBuffer 的优势是零拷贝映射，模型文件可以直接被运行时读取。

2. **Interpreter 初始化**：构建推理上下文，分配中间 tensor 的内存。模型越大，这一步越容易在冷启动时成为显著成本。

3. **Delegate 绑定**：根据设备能力选择执行后端。XNNPACK 是稳定的 CPU 基线；Android GPU Delegate 的公开路径以 OpenCL / OpenGL ES 为主；NNAPI Delegate 则把执行请求交给厂商驱动。

4. **推理执行**：调用 `interpreter.run(input, output)` 或等价接口执行一次前向传播。

### XNNPACK Delegate：先拿到可重复的 CPU 基线

XNNPACK 是 Google 的优化 CPU 推理库，针对 ARM NEON / SVE 指令集做了长期优化。对性能工程师来说，它最大的价值在于结果稳定、兼容性好、fallback 边界清楚。分析新模型时，先用 XNNPACK 在同机型上跑出一条 CPU 基线，再和 GPU Delegate 或 NNAPI Delegate 对比，通常比直接引用别人的 benchmark 更可靠。

如果一份 benchmark 没写清模型版本、输入尺寸、batch size、线程数和量化策略，它只能帮助我们判断趋势，不能直接拿来做 SLA 或选型决策。

## AICore 与 Gemini Nano：什么时候需要把它当成性能问题

### AICore 的系统角色

Android 官方文档把 Gemini Nano 的运行环境描述为 Android 的 AICore system service。对 App 来说，AICore 更像系统提供的共享推理能力，而不是一个普通三方 SDK。文档还提到，AICore 没有直接 internet access，模型下载通过 Private Compute Services 完成。这两个事实很重要：一是模型准备成本可能出现在首次使用前后，二是模型分发和缓存不完全由单个 App 控制。

[已验证: developer.android.com/ai/aicore, Gemini Nano runs in Android's AICore system service; model downloads are routed through Private Compute Services]

### 对性能工程师真正重要的边界

这类能力对产品功能很有吸引力，但性能分析时更该先看四个边界：

- 当前设备和系统镜像是否真的支持这条能力
- 首次使用时是否发生模型下载、准备或冷启动初始化
- 请求是否命中共享模型缓存，还是每次都要重新准备上下文
- 持续推理时，内存、thermal 和前台交互是否还能压在预算内

离开机型、模型版本、输入长度和测试口径，单独引用 TOPS、tokens/s、首 token 延迟或峰值内存数字，分析价值很有限。写到书里时，最好把这些数字降级成“具体 benchmark 以官方兼容列表和机型实测为准”。

### 和 ADPF、内存、Trace 的关系

如果一个功能调用的是 AICore / Gemini Nano，Perfetto 里最先暴露出来的通常是线程活跃度、调度延迟、内存上涨、温度上升和频率变化，而不是模型名字。分析这类问题时，我们一般同时看三件事：模型首次使用时的准备成本，稳态推理时的 CPU / GPU / NPU 负载，以及后台缓存对 LMK 的压力。

## 模型优化技术：先看收益落在哪个子系统

### 量化：先确认目标 Delegate

量化通常是第一刀，但收益大小取决于模型结构、kernel 覆盖率和目标 delegate。INT8 更常见于 CPU / NPU 路径，Float16 更常见于 GPU 路径。评估量化时，至少记录四项：模型大小、峰值 RSS、单次推理耗时、持续运行数分钟后的 thermal 变化。只看单次 latency，容易把后面的热降频问题漏掉。

TFLite 支持 post-training quantization 和 quantization-aware training。前者接入成本低，适合先验证是否有明显收益；后者更适合对精度损失敏感、并且愿意改训练流程的团队。

### 裁剪与蒸馏：先看部署成本

模型裁剪和知识蒸馏都能减小模型，但移动端收益并不会自动成立。非结构化稀疏在很多移动加速器上并不能直接换来等比例加速；蒸馏得到的小模型，则是在训练阶段付出额外成本，换运行时更小的计算量。对前台交互场景，优先级通常是：先把线程模型、delegate 选择和量化做好，再决定是否值得改训练流程。

## ML 推理性能分析与调优实战

### 在 Perfetto 中分析 ML 推理

默认 system trace 能稳定看到的是线程调度、CPU / GPU 频率、内存水位和 thermal 变化。模型内部阶段 slice 只有在 App 或 native runtime 主动打点后才会出现，所以分析前先分清“默认能看到什么”和“额外打点后能看到什么”。

- **默认 Perfetto**：能看到主线程 / 工作线程是否被推理压满，CPU frequency 是否持续拉高，GPU freq 是否跟渲染一起上升，RSS / heap 是否在模型加载后明显抬升。
- **App trace instrumentation**：如果 Java 层在 `interpreter.run()` 外包了 `Trace.beginSection()`，或 native 层用 `ATrace_beginSection()` 给预处理、推理、后处理打点，Perfetto 才会稳定出现这些阶段的 slice。`TfLiteInterpreter::run` 这种名字不是默认保证可见的。
- **Vendor tracepoint / delegate 日志**：NPU 相关观测通常依赖厂商 tracepoint、NNAPI / delegate 日志或专用 profiler。没有这些数据时，只能用 CPU、GPU、thermal 和 logcat 做交叉定位。

[图：CPU 推理的 Perfetto 观察示意。主线程或 worker 线程连续运行，CPU frequency 抬升；如果有 `Trace.beginSection()`，可以在对应线程上看到 preprocess / inference / postprocess 三段 slice。]

[图：GPU Delegate 的 Perfetto 观察示意。CPU 线程忙碌度下降，但 GPU 频率和 GPU 工作负载上升；若与 RenderThread 同时活跃，需要检查帧时间是否同步恶化。]

[图：NPU 或 NNAPI Delegate 的 Perfetto 观察示意。默认 trace 里没有统一 NPU track，CPU 负载可能不高，但 thermal、频率和 delegate 日志显示推理仍在进行；必要时结合厂商 tracepoint 判断是否真的命中 NPU。]

### 常见性能问题

**NPU / NNAPI fallback 导致的 CPU jank**：模型中的一部分算子没有被当前 delegate 接住，执行路径退回 CPU。表面现象通常是 CPU 线程突然忙起来，GPU / NPU 预期负载却没有出现。先看 delegate 日志，再对照模型算子覆盖率，比单看平均 latency 更容易定位。

**模型加载阻塞主线程**：大模型的 FlatBuffer 映射、Interpreter 初始化和 delegate 绑定如果放在主线程，会直接拖慢冷启动或页面切换。排查时重点看初始化是否落在主线程，以及预热是否和首帧竞争。

**推理内存峰值触发 LMK**：模型文件本身往往不是全部成本，中间 tensor、delegate workspace 和缓存策略都可能把 RSS 顶上去。排查时不要只看 Java heap，Native heap 和总 PSS 更关键。

**后台 ML 任务与前台 App 争抢资源**：语音识别、相机理解、健康检测这类持续任务，即使不在主线程上，也会抢 CPU 时间、GPU 带宽或 NPU 调度资源。WorkManager / JobScheduler 只能解决调度时机问题，不能替代你对前台预算的测量。

### 工程实践中的优化策略

异步推理是最先要落实的优化。推理调用必须在工作线程执行，绝不能在主线程。对于持续性推理场景（如相机滤镜），使用双缓冲策略，一个缓冲区做推理，另一个缓冲区准备下一帧输入。

模型预热是另一个常用技巧。在 App 启动或页面跳转的空档期，用 dummy input 跑一次推理，提前完成 Interpreter 初始化和 Delegate 绑定。这样用户真正触发推理时，延迟会低很多。

批处理（batching）适合需要连续推理的场景。将多个推理请求攒成一批执行，减少 Delegate 调度的固定开销。但需要注意批处理会增加延迟，不适合实时性要求高的场景。

## 与其他章节的关联

- **§2.5 MainThread 与 RenderThread**：ML 推理如果在主线程执行，会直接阻塞 RenderThread 的工作调度，导致掉帧
- **§4.4 Low Memory Killer**：推理峰值内存可能导致 LMK 杀掉后台 App
- **§5.9 ADPF**：AI 工作负载的热管理策略
- **§1.15 JNI/NDK 性能**：TFLite 的 C++ 推理引擎通过 JNI 调用，JNI 开销在高频推理场景下需要关注
- **§14.1 Android Studio Profiler**：ML Profiler 可视化推理性能

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **端侧 AI 推理为什么会变成性能问题**：[已验证: 章节正文 + developer.android.com]
  端侧推理会把 latency、内存、thermal 和硬件调度成本一起带回设备，本质是前台交互预算问题。

- 🔹 **Android ML 硬件加速栈**：[已验证: developer.android.com/ndk/guides/neuralnetworks, ai.google.dev/edge/litert/android/gpu]
  CPU / GPU / NPU / DSP 各有优缺点，公开 GPU Delegate 路径以 OpenCL / OpenGL ES 为主，NPU 可观测性依赖厂商实现。

- 🔹 **NNAPI 的版本边界与迁移方向**：[已验证: developer.android.com/ndk/guides/neuralnetworks]
  NNAPI 在 Android 8.1（API 27）引入，在 Android 15 被官方标记为 deprecated，对性能敏感 workload 建议迁移。

- 🔹 **LiteRT / TFLite 管线与 Delegate 选择**：[已验证: ai.google.dev/edge/litert/android/gpu]
  模型加载、Interpreter 初始化、Delegate 绑定、执行四阶段决定冷启动成本和稳态表现。

- 🔹 **Perfetto 中的 ML 推理观测对照表**：[已验证: 章节正文]
  默认 Perfetto 看到的是调度 / 频率 / 内存 / thermal，模型阶段 slice 需要 app 或 native instrumentation，NPU 额外依赖厂商 tracepoint 或 delegate 日志。

- 🔹 **AICore / Gemini Nano 与模型优化的工程判断**：[已验证: developer.android.com/ai/aicore]
  先看设备支持、冷启动准备、共享缓存、内存和 thermal，再谈模型版本和 benchmark 数字。

### 扩展（可选深入）

- 🔸 **LiteRT in Play Services 的部署取舍**：GMS 依赖、国内设备回退、运行时更新节奏
- 🔸 **量化 / 裁剪 / 蒸馏的验证顺序**：模型大小、RSS、单次 latency、持续运行后的 thermal 变化
<!-- outline-end -->

## 延伸阅读
### 从 NNAPI 到 LiteRT：Android NPU 性能优化全景
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/从 NNAPI 到 LiteRT：Android NPU 性能优化全景 .md
- 类型：DeepResearch 调研结果
- 摘要：从 NNAPI 在 Android 15 弃用切入，对比 LiteRT、CompiledModel、AICore 与主流 NPU 厂商栈，补齐量化、AOT、内存/功耗调度、基准可信度和迁移策略，适合端侧 AI 性能选型。
- 注入时间：2026-04-19
- 价值：对 AI 手机时代的 NPU 路线迁移和性能选型很有参考价值。

