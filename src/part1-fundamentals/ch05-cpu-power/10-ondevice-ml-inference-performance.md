---

title: 端侧 AI 推理性能：NPU/GPU 加速与 LiteRT 管线
chapter: '5.10'
section: '5.10'
status: finalized
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task9_state: reviewed
task2b_state: fixed
applicable_versions: Android 8.1 (API 27) - Android 17 (API 37)
last_verified: '2026-06-04'
last_verified_against: Android API reference API 37 + developer.android.com + ai.google.dev/edge/litert; AOSP android-17.0.0_r1
confidence: high
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/16-gpu-npu-heterogeneous-scheduling.md"
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
---

# 5.10 端侧 AI 推理性能：NPU/GPU 加速与 LiteRT 管线

端侧推理进入相机、OCR、语音、搜索和生成式功能后，模型执行时间就成了前台交互预算的一部分。一次推理可能同时占用 CPU 时间、GPU 带宽、专用加速器、文件页和匿名内存；持续执行还会抬高温度，触发降频。于是，实验室里更快的后端，放进真实页面后未必能带来更稳定的帧时间。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，工程问题分为三项：

1. 应用发起的一次推理，经过哪些准备和执行阶段；
2. CPU、GPU、NPU 与 AICore 分别属于哪条路径；
3. 如何用可复现的测试和系统证据判断瓶颈，避免只看一组平均耗时。

## 先把四条软件路径分开

Android 上的“端侧 AI”包含数套职责不同的组件。排查性能前，先确认产品使用的是哪一条路径。

| 路径 | 应用面对的接口 | 模型与运行时由谁管理 | 常见执行设备 |
|---|---|---|---|
| LiteRT 自带运行时 | `Interpreter`、delegate，或新的 `CompiledModel` API | 应用及其依赖 | CPU、GPU、NPU |
| LiteRT in Google Play services | Play services 提供的 LiteRT 接口 | Play services 更新运行时，应用管理模型 | CPU、GPU，具体能力看接口与设备 |
| AICore / ML Kit GenAI | ML Kit GenAI 等高层 API | AICore 管理 Gemini Nano、请求和安全能力 | 由受支持设备的系统实现决定 |
| NNAPI | NDK Neural Networks API 或 NNAPI delegate | Android NNAPI runtime 与厂商驱动 | CPU、GPU、DSP、NPU，取决于驱动 |

这四条路径可以出现在同一台设备上，但它们没有共同的应用层生命周期。`CompiledModel` 属于 LiteRT；AICore 是系统服务。Android 17 的 NPU 调度组件负责直接 NPU 访问的资格与调度信息，也不等同于模型推理 API。把这几层混在一张调用图里，会误判初始化、内存归属和失败后的处理方式。

## 为什么端侧推理容易变成性能问题

一次完整推理通常至少包含以下阶段：

```text
输入采集
  → 解码 / 缩放 / 归一化 / 分词
  → 模型与运行时初始化
  → delegate 分区或模型编译
  → 输入传输与 tensor 准备
  → 加速器执行
  → 输出读取与后处理
  → UI 更新
```

用户感知的是端到端延迟，运行时报告的 kernel 时间只覆盖其中一段。常见成本包括：

- **首次准备**：打开模型、映射文件、创建运行时、分配 tensor、加载 delegate、编译子图；
- **稳态执行**：算子计算、输入输出传输、同步等待和后处理；
- **并发干扰**：GPU 推理与渲染、相机或视频处理争用带宽和执行时间；
- **内存压力**：权重、tensor arena、delegate workspace、硬件缓冲区和编译缓存同时驻留；
- **热衰减**：连续推理几分钟后，CPU、GPU 或 NPU 频率受热策略限制；
- **队列延迟**：请求排队、跨进程调用、系统服务或厂商运行时调度。

异构管线还要显式记录 buffer 所有权与同步边界。CPU 预处理、GPU/NPU 执行和 CPU 后处理之间可能经过 tensor 重排、cache flush/invalidate、`AHardwareBuffer`/dmabuf 导入以及 fence 等待。零拷贝只在格式、布局、allocator、生命周期和后端都兼容时成立；共享一个 buffer 对象并不自动消除驱动内部复制。测量表应至少分开提交、排队、执行、fence wait 与数据转换，避免把 CPU 等待时间算成加速器计算。

因此，优化目标应写成可测量的产品预算，例如“相机预览期间 P95 端到端延迟低于一帧、无新增卡顿、连续运行十分钟温度等级可接受”。单次最短推理耗时不足以代表用户体验。

## CPU、GPU、NPU 与 DSP 的选择

### CPU：兼容性基线

CPU 路径适合建立同机型基线，也适合小模型、动态 shape、多分支控制流和加速器覆盖不足的模型。LiteRT 的 CPU 后端会使用针对移动 CPU 优化的 kernel；具体线程数仍需实测。

线程越多并不保证端到端越快。前台页面还需要主线程、RenderThread、Binder 线程和系统合成线程。推理线程占满大核后，模型数字可能变好，页面帧时间和整机功耗却可能恶化。基准测试应同时记录线程数、CPU 调度、帧时间与温度。

### GPU：吞吐收益伴随图形争用

LiteRT 在 Android 上公开的 GPU 路径主要使用 OpenCL 和 OpenGL。它适合并行度高、算子覆盖良好、输入规模足够大的模型。输入过小、频繁创建 delegate、CPU 与 GPU 间多次搬运时，提交与同步成本可能抵消计算收益。

需要重点检查三个边界：

- 旧式 `Interpreter` GPU delegate 对创建与调用线程有约束；不要随意跨线程调用；
- `TensorBuffer`、OpenGL buffer 或 `AHardwareBuffer` 只有在格式、布局、生命周期和后端均兼容时，才可能减少复制；
- GPU 与 RenderThread、SurfaceFlinger、相机和视频管线共享资源。GPU 推理耗时下降，不代表页面也更流畅。

GPU 频率只能说明设备改变了工作点，不能单独证明 GPU 利用率或模型已经完整委托。应结合 GPU work period、驱动 slice、帧时间、delegate 日志和 CPU 等待状态判断。

### NPU：模型覆盖与运行时版本决定收益

NPU 面向卷积、大规模张量乘加、attention 等计算。Android 设备上的 NPU 没有一套面向普通应用的通用图执行 ABI；LiteRT NPU delegate 和厂商 SDK 仍需适配具体 SoC 与运行时。

评估 NPU 时至少回答以下问题：

1. 当前设备、ABI、系统与运行时版本是否受支持；
2. 模型中的哪些子图能进入 NPU，哪些会留在 CPU 或 GPU；
3. 首次编译或加载缓存需要多久；
4. 输入输出是否发生额外复制或格式转换；
5. 连续运行后的延迟、温度和功耗怎样变化；
6. delegate 失败时，产品是否配置了明确的回退顺序。

当前 LiteRT NPU 文档同时描述 AOT 与 JIT 两类部署。AOT 在目标 SoC 已知时预先生成设备相关产物，可以减少设备端首次准备；JIT 在设备上完成编译，分发灵活，但第一次创建可能更慢。两者的支持范围随厂商和 LiteRT 版本变化，不能把某家芯片的结果推广到全部 Android 设备。

### DSP：仍可能存在于旧设备与厂商栈

DSP 擅长低功耗信号处理，也曾是许多 Android 设备的神经网络加速资源。新设备的产品资料更常使用 NPU、APU 或 AI accelerator 等名称，但厂商实现内部仍可能组合 DSP 与专用张量单元。应用不应根据营销名称推断 delegate 覆盖率；应以运行时兼容列表和本机执行证据为准。

## NNAPI：仍在源码中，但迁移方向已经明确

NNAPI 在 Android 8.1 / API 27 引入。它让框架构造计算图，再由系统 runtime 和厂商驱动选择设备并准备执行。Android 15 / API 35 起，官方将 NNAPI 标记为 deprecated，并建议性能敏感的应用迁移。

Android 17 源码没有删除 NNAPI。当前锚点包含：

- `packages/modules/NeuralNetworks/runtime/include/NeuralNetworks.h`：NDK API 带有 API 35 弃用标记；
- `packages/modules/NeuralNetworks/runtime/`：NNAPI runtime；
- `hardware/interfaces/neuralnetworks/1.3/`：旧版 HIDL HAL；
- `hardware/interfaces/neuralnetworks/aidl/`：NNAPI 的 AIDL HAL。

“deprecated”表示新项目不应继续把它当作长期入口，不表示 Android 17 上所有既有 NNAPI 应用立刻失效。迁移工作需要保留旧设备回归测试，直到产品的最低版本和设备覆盖允许移除旧路径。

### 分区与回退要看实际执行计划

把 NNAPI 的行为概括成“任一算子不支持就整图静默回到 CPU”或“每个不支持的算子都会自动逐个回退”都过于绝对。框架或 delegate 可以把受支持的连续节点组成分区，把其余节点留给 CPU；设备选择、分区数量、编译失败和执行失败后的处理还受 API 调用方式与运行时配置影响。

分区过碎时，即使某些算子进入加速器，跨分区同步和 tensor 转换也可能让总时间变长。验证时应记录：

- 实际委托的节点或子图数量；
- CPU 与加速器之间的边界数量；
- prepare/compile 是否成功；
- 执行失败后是否触发应用配置的回退；
- 回退后的结果正确性与延迟。

### 迁移选择

官方 NNAPI Migration Guide 给出的主要方向是：

- 普通自定义模型：迁移到 LiteRT，可选择应用自带运行时或 Google Play services 路径；
- 适合 GPU 的模型：评估 LiteRT GPU delegate；
- 基础模型能力：在受支持设备上评估 AICore 上层 API。

没有 Google Play services 的设备需要独立部署方案。即便使用 Play services，模型、delegate、加速器支持和版本回退策略仍应在应用侧明确测试。

## LiteRT / TFLite 的准备与执行管线

LiteRT 是 TensorFlow Lite 的后续品牌与运行时演进。旧项目仍大量使用 `Interpreter` 和 delegate；新的 LiteRT API 提供 `CompiledModel` 与 `TensorBuffer`。两代接口可以共存，分析时应先确认应用打包的 artifact 与版本。

### `Interpreter` 路径

典型 `Interpreter` 管线可以拆成五段：

1. **模型访问**：读取或内存映射 `.tflite` FlatBuffer；
2. **解释器创建**：解析模型元数据，注册 kernel；
3. **tensor 准备**：确定 shape，规划并分配 arena；
4. **delegate prepare**：检查算子支持、分区、编译或创建后端资源；
5. **invoke**：填充输入、执行子图、读取并后处理输出。

内存映射可以减少把整份模型复制到 Java heap 的需求，但不等于整条推理管线都没有复制。delegate 可能变换权重、生成编译产物，输入图像也可能经历颜色转换、布局变换和硬件缓冲区导入。

CPU、GPU 或其他 delegate 的收益要以完整管线比较。只在 `invoke()` 外计时，会漏掉首次 `allocateTensors()`、delegate prepare 和输入转换。

### `CompiledModel` 路径

`CompiledModel` 以加速器优先的方式创建可执行模型，并用 `TensorBuffer` 表达输入输出。它把模型创建与多次执行分开，支持同步及异步执行能力；可用加速器和具体接口以所用 LiteRT 版本为准。

这里有三条重要边界：

- 创建 `CompiledModel` 仍可能触发图检查、编译、权重转换与资源分配，不应放在主线程；
- “compiled”不保证得到可跨设备复用的本地二进制。产物格式和缓存能力由后端决定；
- `CompiledModel` 不会因此变成 AICore 客户端。它仍属于 LiteRT 模型执行路径。

适合新接口的项目可以直接评估 `CompiledModel`；已有 `Interpreter` 项目则应先通过同模型、同输入、同设备的对照测试确认迁移收益。接口更新本身不构成性能结论。

### AOT、JIT 与冷启动

AOT 的价值是把部分设备端编译工作移到分发阶段。它通常更适合模型固定、目标 SoC 已知、首次响应敏感的场景。JIT 更适合设备覆盖广或模型动态更新的场景，但第一次创建模型可能产生编译成本。

不能给 AOT 写一个跨设备通用的“500 ms 降到 50 ms”承诺。准备时间取决于模型、厂商编译器、固件、缓存命中、存储状态和进程生命周期。正确的验证方法是分别测量：

- 无缓存的首次创建；
- 同版本缓存命中的再次创建；
- 进程重启后的创建；
- 系统或驱动升级后的缓存失效；
- AOT 产物带来的下载体积和驻留内存；
- 数值精度与模型输出是否保持在允许范围。

当前 LiteRT NPU 文档显示，不同厂商对 AOT 与 JIT 的支持并不相同。发布前应锁定 LiteRT artifact、设备清单、SoC/驱动版本和模型版本。

## Android 17：直接访问 NPU 需要 feature 声明

Android 17 / API 37 在 `PackageManager` 中加入：

```java
PackageManager.FEATURE_NEURAL_PROCESSING_UNIT
// 字符串值：android.hardware.npu
```

该常量表示设备具有 NPU 或相近的 AI 加速器。它只说明系统报告了这类硬件能力，不保证某个模型、算子、精度格式或 LiteRT 版本可以使用它。

面向 Android 17、需要直接访问 NPU 的应用，应在 manifest 声明 feature。若应用还有 CPU/GPU 回退，不希望应用商店据此过滤无 NPU 设备，可以这样声明：

```xml
<uses-feature
    android:name="android.hardware.npu"
    android:required="false" />
```

`required="false"` 保留安装覆盖，同时仍把 NPU feature 写进请求列表。Android 17 的 `NpuManager` 源码按 feature 名称检查声明，并不要求 `required` 必须为 `true`。若产品没有无 NPU 路径，可以使用默认的 `required="true"`，让兼容性筛选与产品要求一致。

运行时还要检查设备能力：

```kotlin
val hasNpu = packageManager.hasSystemFeature(
    PackageManager.FEATURE_NEURAL_PROCESSING_UNIT
)
```

这个检查只完成设备能力分支。后续仍需处理 delegate 创建失败、模型不兼容、资源繁忙和执行错误。直接访问包括 LiteRT NPU delegate、厂商 SDK 与已弃用的 NNAPI 等路径；仅仅把推理放到工作线程，并不会绕过 Android 17 的访问检查。

### Android 17 NPU 调度层在做什么

Android 17 的 AOSP 新增 `NpuManager` 模块和 `hardware/interfaces/npu/aidl/`。两者共同描述的是 NPU 访问与调度控制面：

- `PriorityManager` 读取目标 SDK、manifest feature 和 UID 重要性；
- 对 targetSdk 37 及以上且缺少声明的应用，系统可将 `hasDirectAccess` 设为 false；
- `SchedulingConfig` 传递 UID、优先级、直接访问资格和归属能力；
- `WorkInfo` 与 `ISchedulingCallback` 描述工作请求、开始和结束；
- 数值更小的 priority 表示更高优先级，厂商实现按 best-effort 处理。

这套 AIDL 没有定义模型图、tensor 或算子执行接口。LiteRT 或厂商 runtime 仍负责推理。`NpuManager` 的 Java 接口是受权限保护的 `@SystemApi`，普通三方应用不应把它当成可直接调用的公共 SDK。

在支持并启用该服务的 Android 17 系统镜像上，可以通过 service 列表和 `dumpsys npu` 检查服务状态；量产设备是否开放详细信息取决于系统构建与权限。缺少这些信息时，应优先查看应用 delegate 日志和厂商工具。

## AICore / Gemini Nano：系统服务路径

Android 官方将 Gemini Nano 的设备内运行环境描述为 AICore system service。应用通常通过 ML Kit GenAI 等高层 API 请求能力。AICore 负责模型可用性、下载更新、请求处理和相关安全机制；模型下载通过 Private Compute Services，AICore 本身没有直接互联网访问。

这条路径与应用自带 `.tflite` 模型不同：

- 应用不能假设模型已经下载完成；
- 首次请求可能包含能力检查、模型准备或下载等待；
- 设备、地区、系统版本和具体 API 会影响可用性；
- 系统服务可以复用模型资源，但请求上下文和并发策略由服务管理；
- 应用应按 API 契约处理忙碌、取消、超时与不可用状态。

AICore 文档没有把它定义成 `CompiledModel` 的调度器，也没有公开承诺其内部必须经过 NNAPI。分析 AICore 时，以高层 API、系统服务和官方设备支持范围为边界，不根据论坛描述推断内部后端。

### AICore 的内存应怎样观察

跨进程推理会把内存分散到调用方、AICore、Private Compute Services、驱动和共享缓冲区。PSS 按共享页比例计算，RSS 反映各进程映射，二者都不等同于“这次请求应由哪个应用负责”的业务归属。

公开文档没有给出 AICore 全部 PSS/RSS 回算到调用方的保证。排查内存峰值时，应同时观察：

- 调用方的 Java heap、native heap、graphics 和总 PSS；
- AICore 与相关系统进程的变化；
- `dmabuf`、GPU 或厂商驱动分配；
- 请求结束后缓存是否保留，以及内存能否在压力下回收。

不同系统版本的进程名和权限可能变化，脚本不要写死单一进程名。先通过 package、service 与进程列表确认本机实现。

## 一次推理的内存由哪些部分组成

“模型文件只有 100 MB，所以推理最多占 100 MB”是常见误判。运行时内存大致包括：

| 类别 | 典型内容 | 观察提示 |
|---|---|---|
| 模型映射 | FlatBuffer、权重文件页 | 区分 file-backed RSS/PSS 与匿名内存 |
| 权重转换 | delegate 打包、重排、量化展开或编译缓存 | 首次 prepare 后可能持续驻留 |
| tensor | 输入、输出、中间激活、KV cache | shape、batch、序列长度会改变峰值 |
| workspace | CPU scratch、GPU/NPU 临时缓冲区 | 可能位于 native heap、driver 或 `dmabuf` |
| I/O 管线 | Bitmap、YUV/RGB、纹理、`HardwareBuffer` | 重复格式转换会制造额外峰值 |
| 服务进程 | AICore 或其他跨进程 runtime | 不会全部出现在应用自身 heap |

测量时要给生命周期打点：模型打开前、runtime 创建后、第一次执行后、稳定运行后、释放后和内存压力下。只截一张 `dumpsys meminfo` 很难分清一次性准备、可回收缓存和持续泄漏。

## 模型与管线优化

### 先优化端到端管线

推理应离开主线程，但“放到后台线程”只是线程正确性的起点。还要避免：

- 页面每次进入都重新创建 interpreter 或 delegate；
- 相机每帧积压，旧帧还没处理完又提交新帧；
- 输入在 `Bitmap`、数组、`ByteBuffer` 和纹理间反复转换；
- 推理结束后在主线程做重型排序、解码或文本处理；
- 多个模型各自占满线程池或加速器队列。

实时场景通常更适合限长队列或只保留最新输入。双缓冲可以重叠准备与执行，但必须限制同时在途的请求数量，防止内存和延迟随队列增长。

### 量化先验证精度与后端覆盖

INT8、FP16 等量化可以减少模型体积、带宽和计算，但收益依赖目标后端的 kernel 支持。Post-training quantization 接入较快；quantization-aware training 可以改善部分模型的精度保持，但会增加训练成本。

每次量化都应同时验证：

- 业务数据集上的准确率、召回率或生成质量；
- delegate 覆盖率是否提高或下降；
- 初始化、首次和稳态延迟；
- 峰值内存、能耗与持续运行后的温度；
- 不支持设备上的 CPU 回退质量与速度。

### 裁剪、稀疏与蒸馏

非结构化稀疏不会自动换来移动加速器上的等比例加速。只有运行时和硬件支持对应稀疏格式时，减少的参数才可能转化为执行收益。结构化裁剪更容易改变张量尺寸；蒸馏则用训练成本换取更小的学生模型。两者都要回到目标 delegate 和真实输入重新测量。

### 预热、缓存和批处理

预热可以提前触发内存规划、JIT 编译和 kernel 选择，但会把 CPU、内存和热成本移到更早的时刻。预热不能与首帧、启动 I/O 或页面动画争用关键资源。

编译缓存应包含模型、运行时、设备和驱动版本边界，并处理失效与磁盘空间。批处理能够摊薄固定调度成本，却会增加等待时间和 tensor 内存，交互式请求通常需要更小的 batch。

## 建立可复现的 benchmark

一次可靠测试至少报告以下指标：

- runtime、delegate、模型、量化方式、输入 shape、batch 和线程数；
- 设备、SoC、Android build、驱动与电量状态；
- 模型创建时间、第一次执行时间、预热次数；
- 稳态 P50、P95、P99 与吞吐；
- 端到端延迟，以及预处理、执行、后处理的分段时间；
- 峰值 PSS/RSS、native heap、`dmabuf` 或 GPU 内存；
- 连续运行后的温度、频率、功耗和降频点；
- 委托比例、回退路径和输出正确性。

建议至少设置四组对照：

1. CPU 基线；
2. 目标 delegate，无缓存首次创建；
3. 目标 delegate，缓存命中与预热后；
4. 与真实 UI、相机或音频负载并发。

LiteRT 的 `benchmark_model` 工具可以测量初始化、预热和稳态执行，但工具参数随 runtime 版本与 delegate 变化。先用 `--help` 确认当前二进制支持的选项，再把完整命令、模型校验值和环境写入测试记录。

## 用 Perfetto 建立证据

默认系统 trace 主要回答“线程何时运行、CPU/GPU 工作点如何变化、内存和温度发生了什么”。模型算子、delegate 分区和 NPU 内部阶段通常需要运行时、应用或厂商额外打点。

### 应用分段打点

为了区分输入、推理和输出，可以在关键阶段加 trace section：

```kotlin
Trace.beginSection("ml/preprocess")
try {
    preprocess()
} finally {
    Trace.endSection()
}

Trace.beginSection("ml/inference")
try {
    runInference()
} finally {
    Trace.endSection()
}
```

这类 slice 用来对齐 UI 帧、线程调度、频率和内存事件。命名应稳定并带上必要的请求类型；不要把用户内容、文件名或提示词写进 trace。

### LiteRT 内部 tracing

LiteRT 的 performance measurement 文档把 interpreter internal tracing 标为 LiteRT v2.4 起提供。只有应用使用的 runtime 达到对应版本时，下面的属性才有预期效果：

```bash
adb shell setprop debug.tflite.trace 1
# 录制目标场景
adb shell setprop debug.tflite.trace 0
```

录制完成后立即关闭属性，避免污染后续测试。若部署版本较旧，就依靠应用打点、benchmark 工具和 delegate 日志，不应期待系统自动显示每个模型算子。

### 不同后端的观测重点

| 后端 | Perfetto 中常见证据 | 还需要什么 |
|---|---|---|
| CPU | worker 长 slice、run queue、CPU freq、调度迁核 | 线程数、CPU backend 配置、算子 profile |
| GPU | GPU work、频率、CPU 提交/等待、FrameTimeline | GPU delegate 日志、驱动计数器、渲染并发对照 |
| NPU | 应用提交/等待、NpuManager 控制事件、温度与系统调度 | LiteRT/厂商日志、NPU profiler、模型委托比例 |
| AICore | Binder 等待、调用方 slice、系统进程 CPU/内存变化 | ML Kit 状态、模型准备事件、服务侧可见日志 |

Android 17 AOSP 的 NpuManager 包含 constructor、model load/unload、policy 和 UID importance 等 trace section。它们可帮助确认控制面活动，但不提供通用的逐算子 NPU 时间。性能结论仍需 delegate 或厂商侧证据。

GPU 频率上升、CPU 利用率下降、NPU feature 存在都只是旁证。确认加速器命中需要至少一项直接证据，例如 delegate 的成功分区记录、厂商 profiler、编译日志或运行时统计。

## 常见问题的定位顺序

### 首次请求慢

先把模型下载、文件打开、runtime 创建、delegate prepare、编译、第一次执行和后处理分段。再比较进程重启、缓存命中和系统升级后的差异。不要用一次总耗时推断 AOT 或 JIT 的作用。

### 平均延迟正常，但页面掉帧

对齐 `ml/*` slice 与 FrameTimeline，检查主线程阻塞、大核占用、GPU 与渲染重叠、内存回收和后处理。降低推理线程数或限制提交频率，有时会让模型平均耗时略升，却让交互 P95 更稳定。

### 标称启用 NPU，CPU 仍然很忙

CPU 还要负责预处理、后处理、图中未委托节点和提交等待。检查 Android 17 feature 声明、设备能力、delegate 创建结果、分区日志与模型支持列表，再判断是正常的混合执行还是回退。

### 连续运行越来越慢

同时观察 thermal severity、CPU/GPU 频率、NPU 或厂商状态、帧时间和功耗。固定散热条件，分别记录冷机、升温和稳定温度阶段。只增加预热次数无法解决热降频。

### 释放模型后内存没有立刻下降

区分 allocator 保留、文件页缓存、delegate 缓存、驱动分配和仍被引用的 tensor。重复执行“创建—运行—释放—内存压力”周期，观察水位是否无上限增长。进程 RSS 没有立刻回到初始值，本身不能证明泄漏。

## Android 版本边界

| 版本 | 与端侧推理相关的变化 |
|---|---|
| Android 8.1 / API 27 | 引入 NNAPI |
| Android 14 代设备 | AICore / Gemini Nano 开始面向部分设备提供系统级能力 |
| Android 15 / API 35 | NNAPI 标记为 deprecated，官方给出迁移指南 |
| Android 17 / API 37 | 加入 `FEATURE_NEURAL_PROCESSING_UNIT`；面向 Android 17 且直接访问 NPU 的应用需要 manifest 声明；AOSP 增加 NpuManager 与 NPU scheduling AIDL |

版本表表达平台边界，不代表每台相应 Android 版本设备都提供 NPU、AICore 或同一套 LiteRT delegate。运行时能力还要看设备 feature、Google Play services、厂商组件和模型兼容性。

## 源码锚点

以下路径均以 Android 17 / `android-17.0.0_r1` 为平台锚点：

| 组件 | 路径 | 用途 |
|---|---|---|
| NPU feature 常量 | `frameworks/base/core/java/android/content/pm/PackageManager.java` | `FEATURE_NEURAL_PROCESSING_UNIT` |
| NPU service 名称 | `frameworks/base/core/java/android/content/Context.java` | `NPU_SERVICE = "npu"` |
| NPU feature 检查与 UID 优先级 | `packages/modules/NpuManager/service/java/com/android/server/npumanager/PriorityManager.java` | direct-access 判定 |
| NPU flags | `packages/modules/NpuManager/flags/npumanager_flags.aconfig` | Android 17 feature gate |
| NPU scheduling AIDL | `hardware/interfaces/npu/aidl/android/hardware/npu/` | 调度配置与工作回调 |
| NNAPI NDK 头文件 | `packages/modules/NeuralNetworks/runtime/include/NeuralNetworks.h` | API 35 弃用标记 |
| NNAPI runtime | `packages/modules/NeuralNetworks/runtime/` | 既有 NNAPI 执行层 |
| NNAPI HAL | `hardware/interfaces/neuralnetworks/1.3/`、`hardware/interfaces/neuralnetworks/aidl/` | 既有厂商驱动接口 |

`hardware/interfaces/npu/aidl/` 与 `hardware/interfaces/neuralnetworks/` 的职责不同。前者是 Android 17 的 NPU 调度控制接口；后者属于 NNAPI 推理 HAL。项目里若看到两者同时存在，不应据此判断新的 NPU AIDL 已替代所有模型执行接口。

LiteRT 是独立演进的 Google AI Edge 项目，API、artifact 和 delegate 支持应以应用实际依赖的 LiteRT 版本为准，不要用平台 AOSP tag 推断其最新版本。

## 官方资料

- [NNAPI overview](https://developer.android.com/ndk/guides/neuralnetworks/)
- [NNAPI Migration Guide](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)
- [Android 17 release notes](https://developer.android.com/about/versions/17/release-notes)
- [`FEATURE_NEURAL_PROCESSING_UNIT`](https://developer.android.com/reference/android/content/pm/PackageManager#FEATURE_NEURAL_PROCESSING_UNIT)
- [LiteRT for Android with `CompiledModel`](https://developers.google.com/edge/litert/next/android_kotlin)
- [LiteRT NPU acceleration](https://developers.google.com/edge/litert/next/npu)
- [LiteRT GPU acceleration](https://developers.google.com/edge/litert/next/gpu)
- [LiteRT performance measurement](https://developers.google.com/edge/litert/models/measurement)
- [Gemini Nano and AICore](https://developer.android.com/ai/gemini-nano)

## 与其他章节的关联

- **§2.5 MainThread 与 RenderThread**：推理、GPU 渲染和帧调度之间的竞争；
- **§4.4 Low Memory Killer**：模型、tensor 和服务进程内存对整机压力的影响；
- **§5.9 ADPF**：持续工作负载、性能提示与热策略；
- **§1.15 JNI/NDK 性能**：native runtime 的调用、缓冲区与线程边界；
- **§14.1 Android Studio Profiler**：应用侧 CPU 和内存分析。
