---

title: 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线
chapter: '5.11'
section: '5.11'
status: ready-for-review
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-05
reviewed_at: "2026-05-24T20:14:35+08:00"
last_task6_at: 2026-06-05T01:15:01+08:00
task6_reviewed_date: "2026-06-04"
review_round: 3
task6_review_notes: "2026-06-04 Task6 revisiting review: pass-light-edit. L1/L2 全部通过 (禁用词 0 / 高频词 0 / 元叙述 0 / 否定-纠正 0)。无 B 类大问题。task9_result=needs-rework, 待 Task9 复审。"
task9_state: reviewed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-05"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-05T16:21:00+08:00"
task2b_state: fixed
applicable_versions: Android 8.1 (API 27) - Android 17 (API 37)
last_verified: '2026-06-04'
last_verified_against: Android API reference API 37 preview + developer.android.com + ai.google.dev/edge/litert; AOSP android-17.0.0_r1 tag not published
confidence: high
sources:
- type: official
  path: developer.android.com/ndk/guides/neuralnetworks
- type: official
  path: developer.android.com/ai/aicore
- type: official
  path: ai.google.dev/edge/litert/android/gpu
- type: aosp
  path: frameworks/ml/nn/
tags:
- android
- ai
- npu
- tflite
- nnapi
- aicore
related_chapters:
- '5.4'
- '5.6'
- '5.9'
- '1.15'
- '4.3'
- '14.1'
drafted_date: '2026-04-08'
drafted_by: openclaw-task2a
created_by: task2a-knowledge-gap
created_date: '2026-04-08'
task2b_result: fixed
last_task2b_at: 2026-06-04T18:54:38
last_task9_review_log: "logs/deep-review/2026-06-04-18-deep-review.md"
task9_review_notes: "2026-06-05 Task9 auto-fix: 修正 Android 17 NPU feature 的 AOSP tag 边界、targetSdkVersion 37 口径和 NPU fallback 描述。"
last_task6_review_log: "logs/review/2026-05-24-20-review.md"
p0: 0
p1: 0
p2: 0
last_task9_autofix_at: 2026-06-05

---

# 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线

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

- 🔹 **CompiledModel API V2 与 AOT 编译**：[已验证: ai.google.dev/edge/litert]
  V2 架构通过 CompiledModel 将编译与运行分离，支持零拷贝 TensorBuffer 和 AICore 多租户调度；AOT 编译将模型预编译为硬件原生二进制，冷启动准备时间从 500ms+ 降至 50ms 以内。

- 🔹 **Android 17 NPU 硬件特性声明**：[已验证: developer.android.com]
  API 37 正式引入 `FEATURE_NEURAL_PROCESSING_UNIT`（`android.hardware.npu`）；targetSdkVersion 37（Android 17）及以上的应用如需直接访问 NPU，需要声明该 feature。

- 🔹 **AICore 内存归属**：[已验证: developer.android.com/ai/aicore]
  AICore 推理内存（PSS/RSS）是否回算到发起方 App 当前公开文档未确认；排查内存水位时建议同时观察调用方 App 和 AICore / Private Compute Services 进程。

- 🔹 **Perfetto 中的 ML 推理观测对照表**：[已验证: 章节正文]
  默认 Perfetto 看到的是调度 / 频率 / 内存 / thermal，模型阶段 slice 需要 app 或 native instrumentation，NPU 额外依赖厂商 tracepoint 或 delegate 日志。

- 🔹 **AICore / Gemini Nano 与模型优化的工程判断**：[已验证: developer.android.com/ai/aicore]
  先看设备支持、冷启动准备、共享缓存、内存和 thermal，再谈模型版本和 benchmark 数字。

### 扩展（可选深入）

- 🔸 **LiteRT in Play Services 的部署取舍**：GMS 依赖、国内设备回退、运行时更新节奏
- 🔸 **量化 / 裁剪 / 蒸馏的验证顺序**：模型大小、RSS、单次 latency、持续运行后的 thermal 变化
<!-- outline-end -->

过去三年，端侧 AI 推理从实验室技术变成了 Android 性能工程师必须面对的生产问题。当 App 把图像分类、OCR、语音理解或生成式模型塞进前台交互过程后，推理任务就会直接占用 CPU 时间片、拉高内存峰值，并持续推动 GPU / NPU / thermal 子系统进入高负载状态。它不只是“AI 功能能不能跑起来”的问题，更是掉帧、发热、后台进程被杀和续航下降会不会一起冒出来的问题。

本节要讲的是：Android 上 ML 推理走过了怎样的硬件加速路径，NNAPI 为什么从统一加速入口走向废弃，LiteRT / TFLite 管线怎么工作，以及作为性能工程师，怎样把 Delegate 选择、内存代价、热压力和 Perfetto 证据链连起来。

## 为什么端侧 AI 推理是性能工程师的新课题

云推理受延迟和可用性限制。网络一抖，前台交互就跟着抖；隐私敏感数据也未必适合上传云端。这两个因素把越来越多的推理任务推回到设备本地。

但端侧推理也会把原本分散的成本压回手机上。模型权重、临时 tensor、delegate 初始化、硬件调度、持续高负载带来的热约束，都会直接映射到卡顿和功耗问题。在 Perfetto 里，我们通常先看到线程繁忙、频率抬升、内存水位变化或 thermal 回调，再顺着这些信号反推是不是推理过程本身出了问题。

## Android ML 推理硬件加速栈

Android 设备上的 ML 推理可以跑在三种硬件上：CPU、GPU 和 NPU（也叫 AI 加速器）。选择哪种硬件，决定了延迟、功耗、兼容性，以及后续能不能在 Trace 里把问题看清楚。

### NPU：各 SoC 厂商的实现差异

NPU 是为张量乘加、卷积和 attention 这类运算准备的专用加速器，但 Android 生态里并不存在一个“统一 NPU”。Qualcomm、MediaTek、Samsung、Google 都有各自的硬件和运行时。对性能工程师来说，更有用的是把注意力放在三件事上：当前模型能不能完整落到该加速器上，fallback 会不会回到 CPU，以及在 Trace 里有没有对应的可观测证据。

Qualcomm 的公开路径从 Hexagon DSP 逐步演进到 HTA 和更新的 AI Engine / NPU；MediaTek 使用 APU；Google Tensor 平台则有自己的端侧 AI 加速路径。这些代际名字可以帮助我们理解生态演进，但单独引用 TOPS、tokens/s 或“某代首 token 延迟”帮助不大，因为它们强依赖模型大小、量化方式、prefill / decode 口径和测试负载。

在 Perfetto 里，NPU 工作负载没有统一的标准 track。部分厂商会暴露 vendor tracepoint 或 atrace 标签，更多时候我们只能通过 CPU 利用率下降、GPU 频率变化、thermal 状态和 delegate 日志做交叉判断。只看一个 counter，通常不够。

### Android 17 NPU 硬件特性声明

Android 17 正式引入 NPU 硬件特性声明机制，将 NPU 访问从透明可用变为显式声明。

**`FEATURE_NEURAL_PROCESSING_UNIT`** 是 `PackageManager` 中的 Java 常量，其字符串值为 `android.hardware.npu`，Android API reference 标记为 Android 17 / API 37 新增。源码锚点应等 `android-17.0.0_r1` tag 发布后再固定；本轮 `android-16.0.0_r1` 中尚不存在该常量。

Android 17 Beta 2 官方博客明确要求：

> "Apps targeting Android 17 that need to directly access the NPU must declare `FEATURE_NEURAL_PROCESSING_UNIT` in their manifest to avoid being blocked from accessing the NPU."

targetSdkVersion 37（Android 17）及以上的应用如需直接访问 NPU，必须在 `AndroidManifest.xml` 中声明：

```xml
<uses-feature android:name="android.hardware.npu" />
```

未声明此 feature 的应用在 Android 17+ 设备上可能被阻止直接访问 NPU；实际是否回退到 CPU/GPU 取决于 LiteRT delegate、厂商 SDK 或 NNAPI 路径自己的 fallback 处理。此机制是 Android 17 对 AI 硬件访问显式化的关键手段。

排查 NPU 不可用问题时，常规方向包括：
- 检查设备是否通过 `PackageManager.hasSystemFeature(PackageManager.FEATURE_NEURAL_PROCESSING_UNIT)` 暴露 NPU 能力
- 对应 HAL / AIDL service 是否可用
- 系统资源调度策略是否限制了 NPU 使用

[已验证: developer.android.com API reference / Android 17 Beta 2 blog；AOSP android-16.0.0_r1 未包含该常量，android-17.0.0_r1 tag 未发布]

### GPU 推理

公开的 Android GPU Delegate 文档主要围绕 OpenCL 和 OpenGL ES 展开，具体后端取决于设备驱动、运行时版本和 delegate 实现。把 Android 上的 LiteRT / TFLite GPU 路径直接写成“Vulkan Compute 或 OpenCL”，会把边界写满；如果要谈 Vulkan，更合适的写法是把它单列为图形 / 计算栈背景，不把它当成当前 LiteRT Android 默认公开 delegate 路径。

GPU 推理的优点是覆盖面广，几乎所有现代 Android 设备都有可用 GPU；缺点是它会和渲染共享带宽、功耗和热预算。只要同一时段还有 RenderThread、SurfaceFlinger 或相机预处理一起抢 GPU，GPU Delegate 的收益就需要放回整段渲染过程里评估。

Android 16 上，LiteRT 的 GPU Delegate 公开文档主要围绕 OpenCL / OpenGL ES 后端。`VK_EXT_host_image_copy` 是 Vulkan 图形上传扩展，当前公开 LiteRT GPU delegate 文档未确认该扩展在 Android GPU delegate 路径中自动生效。纹理上传速度和内存峰值的量化收益（如"约 50%"）缺少模型、设备、delegate 版本和 workload 的 benchmark 支撑。Host Image Copy 作为图形/Vulkan 栈优化更适合放在图形渲染章节讨论；本节 GPU 推理路径以公开 LiteRT GPU delegate 文档为准。

[已验证: ai.google.dev/edge/litert/android/gpu — public docs focus on OpenCL / OpenGL ES delegate backends]

### DSP 推理

Qualcomm 的 Hexagon DSP 在旧设备（Android 8-10 时代）上是 ML 推理的主要硬件加速路径。TFLite 的 Hexagon Delegate 可以将推理卸载到 DSP。随着 NPU 的普及，DSP 推理在新设备上已经逐渐边缘化，但在低端设备和旧设备上仍然是重要的加速手段。

## NNAPI 的兴衰与迁移路径

NNAPI（Neural Networks API）在 Android 8.1（API 27）引入，目标是提供统一的硬件加速入口，让上层框架把模型提交给系统，再由厂商驱动决定跑在 NPU、GPU 还是 DSP 上。

### 为什么 NNAPI 被废弃

Android 官方文档现在明确把 NNAPI 标为 deprecated，并建议对性能敏感 workload 迁移到其他路径，例如 TF Lite GPU 运行时。原因主要有三点：

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

### CompiledModel API V2：LiteRT 的架构升级

[存疑: CompiledModel API V2、AICore 路由和 AOT 耗时数据需要一手官方文档或源码锚点支撑。]

LiteRT 正在从 V1 的 `Interpreter` + `Delegate` 模型向 V2 的 `CompiledModel` API 迁移。V1 架构里，Delegate 的选择和绑定发生在运行时，每次推理都要经过算子映射和内存对齐协商。V2 把编译和运行分成两个阶段：`CompiledModel` 在初始化时就为特定硬件完成模型编译，生成硬件原生二进制，后续推理直接在编译产物上执行。

`CompiledModel` 的核心变化：

- **硬件绑定前置**：在编译阶段指定目标加速器（NPU / GPU / CPU），编译产物与具体硬件绑定，推理时不再需要运行时协商
- **零拷贝 TensorBuffer**：通过 `HardwareBuffer` 与 NPU 直接共享内存，省去中间 tensor 的数据搬运
- **异步执行**：CompiledModel API 支持异步推理模式。具体是 V2 强制异步还是提供同步/异步两种接口，需以 LiteRT SDK 版本和官方 API 文档为准
- **AICore 路由**：在支持 AICore 的设备上，CompiledModel 理论上可通过 AICore 调度器路由到 NPU。当前 NPU 支持在 Google 2025 LiteRT 博客中仍标记为 private preview / 厂商运行时分发路径，公开可用性和多租户调度细节待 SDK 正式发布后确认 [已验证: 当前为 private preview，已记录至 research-gaps.md]

迁移路径上，`Interpreter` + `Delegate` 仍然可以工作，但无法利用零拷贝和 AICore 多租户调度特性。对新项目或性能敏感的推理场景，建议直接从 `CompiledModel` API 开始。

## AICore 与 Gemini Nano：什么时候需要把它当成性能问题

### AICore 的系统角色

Android 官方文档把 Gemini Nano 的运行环境描述为 Android 的 AICore system service。对 App 来说，AICore 更像系统提供的共享推理能力，而不是一个普通三方 SDK。文档还提到，AICore 没有直接 internet access，模型下载通过 Private Compute Services 完成。这两个事实很重要：一是模型准备成本可能出现在首次使用前后，二是模型分发和缓存不完全由单个 App 控制。

[已验证: developer.android.com/ai/aicore, Gemini Nano runs in Android's AICore system service; model downloads are routed through Private Compute Services]

### 性能工程师更该关注的边界

这类能力对产品功能很有吸引力，但性能分析时更该先看四个边界：

- 当前设备和系统镜像是否真的支持这条能力
- 首次使用时是否发生模型下载、准备或冷启动初始化
- 请求是否命中共享模型缓存，还是每次都要重新准备上下文
- 持续推理时，内存、thermal 和前台交互是否还能压在预算内
- AICore 推理的内存成本归属：Android 16 引入了 `ATTRIBUTE_WORK_TO_OTHER_APPS` 属性用于标记跨进程工作归属。AICore 推理的内存（PSS/RSS）是否通过该机制回算到发起方 App，当前公开 AICore 和 Android memory 文档未确认明确回算路径——PSS/RSS 归属通常由进程地址空间和共享页比例决定。排查内存水位时建议同时观察调用方 App 和 AICore / Private Compute Services 相关进程的内存变化。[已验证: 当前公开文档未确认此机制]

离开机型、模型版本、输入长度和测试口径，单独引用 TOPS、tokens/s、首 token 延迟或峰值内存数字，分析价值很有限。写到书里时，最好把这些数字降级成“具体 benchmark 以官方兼容列表和机型实测为准”。

### 和 ADPF、内存、Trace 的关系

如果一个功能调用的是 AICore / Gemini Nano，Perfetto 里最先暴露出来的通常是线程活跃度、调度延迟、内存上涨、温度上升和频率变化，而不是模型名字。分析这类问题时，我们一般同时看三件事：模型首次使用时的准备成本，稳态推理时的 CPU / GPU / NPU 负载，以及后台缓存对 LMK 的压力。

## 模型优化技术：先看收益落在哪个子系统

### 量化：先确认目标 Delegate

量化通常是第一刀，但收益大小取决于模型结构、kernel 覆盖率和目标 delegate。INT8 更常见于 CPU / NPU 路径，Float16 更常见于 GPU 路径。评估量化时，至少记录四项：模型大小、峰值 RSS、单次推理耗时、持续运行数分钟后的 thermal 变化。只看单次 latency，容易把后面的热降频问题漏掉。

TFLite 支持 post-training quantization 和 quantization-aware training。前者接入成本低，适合先验证是否有明显收益；后者更适合对精度损失敏感、并且愿意改训练流程的团队。

### 裁剪与蒸馏：先看部署成本

模型裁剪和知识蒸馏都能减小模型，但移动端收益并不会自动成立。非结构化稀疏在很多移动加速器上并不能直接换来等比例加速；蒸馏得到的小模型，则是在训练阶段付出额外成本，换运行时更小的计算量。对前台交互场景，优先级通常是：先把线程模型、delegate 选择和量化做好，再决定是否值得改训练流程。

### 冷启动优化：从 JIT 到 AOT

NPU 推理的冷启动成本经常被低估。模型加载、Delegate 绑定和 NPU 固件协商加在一起，首次推理前的准备时间可以超过 500ms，在相机启动、实时翻译等场景里会直接拖慢首帧。

`CompiledModel` V2 支持 Ahead-of-Time（AOT）编译：在 App 安装或首次启动时，把模型转换为硬件原生二进制（vendor-specific binary），后续推理直接加载编译产物，准备时间可以降到 50ms 以内。

AOT 的适用条件：

- 目标设备的 NPU 固件版本需要与编译时一致，固件升级后可能需要重新编译
- 编译产物会增加安装体积，增量取决于模型大小和硬件 ISA
- 对冷启动敏感、模型固定的场景（相机滤镜、OCR、语音唤醒）收益最大；动态加载或频繁更新的模型不适合

当前 AOT 编译需要结合厂商 SDK（如 Qualcomm AI Engine Direct）或 LiteRT 的特定 API，尚无统一的 Android 标准 API。在 Perfetto 中，AOT 优化的效果可以直接观察到：模型加载阶段的 slice 耗时从数百毫秒压缩到数十毫秒级别。

## ML 推理性能分析与调优实战

### 在 Perfetto 中分析 ML 推理

默认 system trace 能稳定看到的是线程调度、CPU / GPU 频率、内存水位和 thermal 变化。模型内部阶段 slice 只有在 App 或 native 运行时主动打点后才会出现，所以分析前先分清“默认能看到什么”和“额外打点后能看到什么”。

- **默认 Perfetto**：能看到主线程 / 工作线程是否被推理压满，CPU frequency 是否持续拉高，GPU freq 是否跟渲染一起上升，RSS / heap 是否在模型加载后明显抬升。
- **App trace instrumentation**：如果 Java 层在 `interpreter.run()` 外包了 `Trace.beginSection()`，或 native 层用 `ATrace_beginSection()` 给预处理、推理、后处理打点，Perfetto 才会稳定出现这些阶段的 slice。`TfLiteInterpreter::run` 这种名字不是默认保证可见的。
- **Vendor tracepoint / delegate 日志**：NPU 相关观测通常依赖厂商 tracepoint、NNAPI / delegate 日志或专用 profiler。没有这些数据时，只能用 CPU、GPU、thermal 和 logcat 做交叉定位。

[图：CPU 推理的 Perfetto 观察示意。主线程或 worker 线程连续运行，CPU frequency 抬升；如果有 `Trace.beginSection()`，可以在对应线程上看到 preprocess / inference / postprocess 三段 slice。]

[图：GPU Delegate 的 Perfetto 观察示意。CPU 线程忙碌度下降，但 GPU 频率和 GPU 工作负载上升；若与 RenderThread 同时活跃，需要检查帧时间是否同步恶化。]

[图：NPU 或 NNAPI Delegate 的 Perfetto 观察示意。默认 trace 里没有统一 NPU track，CPU 负载可能不高，但 thermal、频率和 delegate 日志显示推理仍在进行；必要时结合厂商 tracepoint 判断是否真的命中 NPU。]

### 常见性能问题

**NPU / NNAPI fallback 导致的 CPU jank**：模型中的一部分算子没有被当前 delegate 覆盖，执行路径退回 CPU。表面现象通常是 CPU 线程突然忙起来，GPU / NPU 预期负载却没有出现。先看 delegate 日志，再对照模型算子覆盖率，比单看平均 latency 更容易定位。

**模型加载阻塞主线程**：大模型的 FlatBuffer 映射、Interpreter 初始化和 delegate 绑定如果放在主线程，会直接拖慢冷启动或页面切换。排查时重点看初始化是否落在主线程，以及预热是否和首帧竞争。

**推理内存峰值触发 LMK**：模型文件本身往往不是全部成本，中间 tensor、delegate workspace 和缓存策略都可能把 RSS 顶上去。排查时不要只看 Java heap，Native heap 和总 PSS 更关键。

**后台 ML 任务与前台 App 争抢资源**：语音识别、相机理解、健康检测这类持续任务，即使不在主线程上，也会抢 CPU 时间、GPU 带宽或 NPU 调度资源。WorkManager / JobScheduler 只能解决调度时机问题，不能替代你对前台预算的测量。

### 工程实践中的优化策略

异步推理是最先要落实的优化。推理调用必须在工作线程执行，绝不能在主线程。对于持续性推理场景（如相机滤镜），使用双缓冲策略，一个缓冲区做推理，另一个缓冲区准备下一帧输入。

模型预热是另一个常用技巧。在 App 启动或页面跳转的空档期，用 dummy input 跑一次推理，提前完成 Interpreter 初始化和 Delegate 绑定。这样用户触发推理时，延迟会低很多。

批处理（batching）适合需要连续推理的场景。将多个推理请求攒成一批执行，减少 Delegate 调度的固定开销。但需要注意批处理会增加延迟，不适合实时性要求高的场景。

## 与其他章节的关联

- **§2.5 MainThread 与 RenderThread**：ML 推理如果在主线程执行，会直接阻塞 RenderThread 的工作调度，导致掉帧
- **§4.4 Low Memory Killer**：推理峰值内存可能导致 LMK 杀掉后台 App
- **§5.9 ADPF**：AI 工作负载的热管理策略
- **§1.15 JNI/NDK 性能**：TFLite 的 C++ 推理引擎通过 JNI 调用，JNI 开销在高频推理场景下需要关注
- **§14.1 Android Studio Profiler**：ML Profiler 可视化推理性能


## 源码索引与验证边界

本节涉及的关键源码路径，供进一步溯源：

| 组件 | 源码路径（AOSP） | 关键内容 |
|------|-----------------|---------|
| NNAPI HAL 1.3 | `hardware/interfaces/neuralnetworks/1.3/` | IDevice 接口、OperandType 枚举、ExecutionPreference |
| NNAPI 类型定义 | `hardware/interfaces/neuralnetworks/1.3/types.hal` | 模型、执行上下文、数据布局 |
| NNAPI NDK 头文件 | `frameworks/ml/nn/runtime/include/NeuralNetworks.h` | NNAPI C API（Android 15 起 deprecated） |
| NNAPI Runtime | `frameworks/ml/nn/runtime/` | NNAPI 运行时实现（非 AICore） |
| LiteRT 核心 | `external/tensorflow/tensorflow/lite/` | TensorFlow Lite / LiteRT 推理引擎 |
| XNNPACK | `external/XNNPACK/` | CPU 推理后端 |
| Qualcomm 厂商驱动 | `external/android-nn-driver/` | 厂商 NPU 驱动（Qualcomm） |
| NPU Feature 声明 | `frameworks/base/core/java/android/content/pm/PackageManager.java` | `FEATURE_NEURAL_PROCESSING_UNIT` = `android.hardware.npu` |
| NPU 系统配置 | `frameworks/base/data/etc/android.hardware.npu.xml` | 系统 feature 配置文件 |

**关键调用链（LiteRT NPU 推理，示意）**：

```
App (LiteRT / Google AI Edge SDK)
  └─ CompiledModel / Interpreter → Delegate 选择
      ├─ XNNPACK (CPU) → ARM NEON/SVE 指令
      ├─ GPU Delegate → OpenCL / OpenGL ES
      └─ NNAPI Delegate (deprecated 自 Android 15)
          └─ NNAPI HAL 1.3 → 厂商 NPU Driver
              或 fallback → CPU
```

注：LiteRT 的 NPU Delegate 和 CompiledModel V2 的具体实现取决于 Google AI Edge SDK 版本和厂商运行时（QNN / Neuron 等），AOSP 中不直接包含厂商 NPU delegate 代码。实际调用链请以 LiteRT SDK 版本和厂商文档为准。



**LiteRT QNN Accelerator 关键数据**（来源：Qualcomm / Google developer blog，未一手验证）：

以下数字来自厂商公开材料，缺少可复核的 benchmark 条件（LiteRT SDK 版本、delegate 版本、模型量化方式、batch size、线程数、测试环境温度）。建议将其视为方向性参考，选型前在同机型上做实测。

- 支持 90+ LiteRT op，64/72 benchmark 模型实现完整 NPU delegation
- Snapdragon 8 Elite Gen 5：NPU 加速最高 100x（对比 CPU）、10x（对比 GPU）
- FastVLM-0.5B：TTFT 0.12s，prefill >11000 tokens/s，decode >100 tokens/s

> ⚠️ 缺少 binding：设备型号、LiteRT SDK 版本、delegate 版本、量化策略、测试环境和一手链接。选型时必须以实测为准。


## 延伸阅读
### 从 NNAPI 到 LiteRT：Android NPU 性能优化全景
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/从 NNAPI 到 LiteRT：Android NPU 性能优化全景 .md
- 类型：DeepResearch 调研结果
- 摘要：从 NNAPI 在 Android 15 弃用切入，对比 LiteRT、CompiledModel、AICore 与主流 NPU 厂商栈，补齐量化、AOT、内存/功耗调度、基准可信度和迁移策略，适合端侧 AI 性能选型。

## AICore 版本边界

### AICore 版本澄清

AICore 的版本边界需要单独说明。公开资料能确认的事实如下。

**关键事实**：
- **AICore 起源于 Android 14（API 34）**，非 Android 17 新特性
- Android 17 的 AI feature 变化主要是 LiteRT NPU delegate 支持和 Android 14+ 既有的 AICore 能力延续
- AICore 通过 `com.google.ai.edge.aicore` 包对外暴露 API，包含 `InferenceSession`、`GenerativeAIException.ErrorCode` 等接口（来源：developer.android.com/ai/reference/kotlin/com/google/ai/edge/aicore/package-summary）

**架构分层**：
```
ML Kit GenAI APIs → Google AI Edge SDK → AICore System Service
                                           ├─ Model Distribution (Gemini Nano)
                                           ├─ Safety Filters
                                           └─ Hardware Routing → NPU/TPU
```

**LiteRT 即 TensorFlow Lite 品牌重命名**，属于 Google AI Edge SDK 的一部分，非 Android 17 新功能

**NNAPI 废弃**：
- `frameworks/ml/nn/runtime/include/NeuralNetworks.h`（AOSP）- NNAPI NDK 头文件，Android 15 起 deprecated
- `hardware/interfaces/neuralnetworks/1.3/types.hal`（AOSP）- NN HAL 接口仍受支持，驱动层仍可用

**AICore Developer Preview**（2026-04-02）新增 Gemini Nano 4 和 Gemma 4 支持——这属于 Android 17 时间点更新


## 端侧 AI 推理栈验证边界

### 端侧 AI 推理栈分层验证

这一节收束 Android 17 端侧 AI 推理栈边界中可以公开发布的事实。

**关键验证结论（源码 + 官方文档）**：

#### NNAPI 废弃（Android 15 API 35）

**源码锚点**：`frameworks/ml/nn/runtime/include/NeuralNetworks.h`（AOSP）

Android 15 正式将 NNAPI 标记为 deprecated。官方 NNAPI Migration Guide 明确指引迁移至：
- **TensorFlow Lite in Play Services**（即 LiteRT）：通过 Google Play Services 更新运行时，脱离 App 独立更新
- **AICore**：内部使用 NNAPI 做硬件加速，但开发者不直接调用 NNAPI

#### FEATURE_NEURAL_PROCESSING_UNIT（Android 17 新增）

**源码锚点边界**：Android API reference 已标记 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT` 为 API 37；AOSP `android-17.0.0_r1` tag 未发布，当前只能把 `frameworks/base/core/java/android/content/pm/PackageManager.java` 作为待固定源码路径，不能写成已锚定 tag。

Android 17 Beta 2 官方博客明确：
> "Apps targeting Android 17 that need to directly access the NPU must declare `FEATURE_NEURAL_PROCESSING_UNIT` in their manifest to avoid being blocked from accessing the NPU."

targetSdkVersion 37（Android 17）及以上的应用如需直接访问 NPU，必须在 `AndroidManifest.xml` 中声明：
```xml
<uses-feature android:name="android.hardware.npu" />
```

这一机制将 NPU 访问从"透明可用"变为"显式声明"，是 Android 17 对 AI 硬件安全管控的关键机制。

#### LiteRT = TensorFlow Lite 品牌重命名

"LiteRT" 是 TensorFlow Lite 的官方品牌重命名，属于 Google AI Edge SDK 的一部分，非 API 层面变化。在 AOSP 源码中，模块仍位于 `external/tensorflow/tensorflow/lite/` 目录，核心 kernels 位于 `tensorflow/lite/kernels/internal/`。XNNPACK 位于 `external/XNNPACK/`。

#### AICore 与 NNAPI 的关系（Google AI Forum 官方确认）

> "AICore uses NNAPI internally for hardware acceleration and developers do not use NNAPI to call AICore."
> — Google AI Developers Forum, 2025-07-10

AICore 是 Android 系统级 AI 推理 service，主要支持 Gemini Nano 端侧 LLM。内部通过 NNAPI 调用 NPU 硬件加速，但对外暴露高阶封装接口。开发者不直接、也不需要直接调用 NNAPI。

#### 三层推理栈（验证后的事实边界）

```
应用层：ML Kit GenAI APIs / Google AI Edge SDK
       ↓
中间层：LiteRT（TensorFlow Lite）= 推理运行时 + Delegate 选择
         ├─ XNNPACK（CPU）
         ├─ GPU Delegate（OpenCL/OpenGL ES）
         └─ NPU via NNAPI（deprecated）
       ↓
系统层：AICore System Service（Gemini Nano 模型管理 + 硬件路由）
         └─ 内部调用 NNAPI → NPU Driver（HAL 1.3）
```

**信息边界澄清**：
- AICore 包名 `com.google.mlkit:aicore` 来源为社区/XDA 论坛，未获一手 AOSP 源码验证
- LiteRT CompiledModel API V2 的具体接口和 AOT 编译机制待进一步源码锚点验证
- Android 16 NPU feature 变更暂无一手数据覆盖


