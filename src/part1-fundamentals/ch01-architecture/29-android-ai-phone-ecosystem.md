---
title: Android AI 手机技术栈：平台接口、端侧推理与协作边界
chapter: '1.29'
section: '1.29'
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: Android 15 (API 35) - Android 17 (API 37); 当前源码锚点 android-17.0.0_r1
tags:
- android
- ai
- ecosystem
- hardware
- llm
- performance
related_chapters:
- '1.9'
- '1.3'
- '5.4'
- '5.5'
last_verified: '2026-08-09'
last_verified_against: AOSP android-17.0.0_r1; Android/ML Kit/LiteRT official docs current to 2026-08-09
confidence: high
sources:
- type: aosp
  path: android-17.0.0_r1:frameworks/base/core/java/android/app/appfunctions/AppFunctionManager.java
- type: aosp
  path: android-17.0.0_r1:frameworks/base/core/java/android/app/appfunctions/AppFunctionService.java
- type: aosp
  path: android-17.0.0_r1:hardware/interfaces/neuralnetworks/aidl
- type: aosp
  path: android-17.0.0_r1:frameworks/base/packages/NeuralNetworks/framework/platform/java/android/app/ondeviceintelligence/OnDeviceIntelligenceManager.java
- type: official-doc
  path: https://developer.android.com/ai/overview
- type: official-doc
  path: https://developer.android.com/ai/appfunctions
- type: official-doc
  path: https://developer.android.com/ndk/guides/neuralnetworks
- type: official-doc
  path: https://developers.google.com/ml-kit/genai
- type: official-doc
  path: https://developers.google.com/edge/litert/android
---

# Android AI 手机技术栈：平台接口、端侧推理与协作边界

手机上的 AI 能力可能由系统服务、应用内运行时、云端模型或跨应用代理交付；接口名称相似，并不代表执行位置、数据边界和可用性相同。选型时应先确定能力由谁交付、模型在哪里运行、失败后由谁兜底，再比较具体 API。

## 1.15.1 先区分由谁交付

“Android AI 手机”常把芯片、AOSP、Google 系统组件、应用 SDK 和云模型混在一起。工程分析应先确认每一层由谁交付：

| 层次 | 典型组件 | 负责什么 | 不保证什么 |
|---|---|---|---|
| 芯片与厂商软件 | CPU、GPU、DSP/NPU、驱动、厂商 delegate | 提供计算与内存能力 | 同一模型在不同设备上的算子覆盖和性能一致性 |
| AOSP Android 17 | AppFunctions、Binder、进程/权限、Power/Thermal API、Neural Networks HAL | 跨应用执行框架、系统隔离、资源与驱动接口 | 预装某个大模型，或向普通应用开放统一 NPU 指令集 |
| Google 设备组件 | AICore、Gemini Nano、ML Kit GenAI | 在兼容设备上提供共享端侧基础模型与高层 API | 所有 Android 17 设备都可用，或不同 Nano 版本输出一致 |
| 应用推理运行时 | LiteRT、MediaPipe、自研或厂商 SDK | 加载自带模型并选择 CPU/GPU/NPU 路径 | 自动得到最优 delegate、质量或功耗 |
| 云端模型 | Gemini 等服务 | 更大模型、在线知识和服务端算力 | 离线可用、固定成本或数据不出设备 |

这里的 delegate 是推理运行时连接特定硬件后端的适配器。Qualcomm Hexagon、MediaTek APU 和 Google Tensor 的 TPU 都属于芯片或厂商层；TensorFlow、LiteRT、ML Kit 则是软件框架或 SDK，不能与硬件单元并列。即使两台手机都宣传有 NPU，它们支持的数值精度、算子、内存布局、并发能力和驱动质量也可能不同。算子是模型计算图中的单项运算，例如卷积或矩阵乘法。

系统版本相同，AI 能力仍可能不同。应用需要检测具体 API 和模型是否可用，并准备 CPU、其他本地实现或云端回退。

## 1.15.2 NNAPI 与 Neural Networks HAL：应用入口已经改变

NNAPI 从 Android 8.1 开始提供 C API，让上层推理框架把计算图交给 CPU、GPU、DSP 或专用加速器。它提供模型、编译、内存和执行等抽象，也支持同步或异步执行与编译缓存。

Android 15（API 35）起，NNAPI NDK API 已弃用。官方迁移说明还提醒：未来多数设备可能使用 CPU 后端，性能敏感的工作负载应迁移到其他方案，例如 LiteRT GPU 运行时。因此，新项目不应再把 `ANeuralNetworks*` API 当作 Android 17 推荐的应用接口。

Neural Networks HAL 仍然受支持，`android-17.0.0_r1` 也保留 `hardware/interfaces/neuralnetworks/aidl`。这里要区分两件事：

- HAL 面向 Android 系统实现者和硬件厂商，用来连接系统运行时与加速器驱动。
- 普通应用通过 LiteRT、ML Kit 或厂商公开 SDK 使用推理能力，不应直接绑定 HAL AIDL。

“AIDL HAL + NNAPI 是 Android 17 应用统一 AI 通路”的说法已经过时。HAL 是否存在，也不能证明某个应用模型会完整运行在 NPU 上；不受支持的算子可能回退到 CPU，跨处理器同步与内存复制甚至会使混合执行慢于纯 CPU。

## 1.15.3 路线一：AICore 与 ML Kit GenAI

ML Kit GenAI API 通过 AICore 使用设备上的 Gemini Nano。当前公开能力包括摘要、校对、改写、图像描述、语音识别和 Prompt API。模型由设备共享，应用无需把基础模型打进 APK，也不直接管理模型文件。

这条路线适合希望使用受支持端侧生成能力、又不需要控制底层模型实现的应用。接入时必须处理下面的运行条件：

- **设备与功能可用性**：不同 API、设备和 Gemini Nano 版本的支持范围不同；调用前使用对应 API 的功能状态（feature status）检查。
- **模型准备状态**：新设备或 AICore 重置后，配置和模型可能尚未准备好，应用要显示可恢复状态，而不是卡住主线程等待。
- **前台限制**：当前 GenAI 推理只允许位于最前台、用户正在交互的应用使用；前台服务不能绕过该限制。
- **配额**：短时间请求过多可能返回 `BUSY`，长期使用还可能触发每应用电量配额错误。重试需要退避，并允许用户取消。
- **模型版本差异**：应用可读取基础模型名称；同一提示在不同版本上可能产生不同输出，质量测试不能只覆盖一台设备。
- **流式结果**：长结果优先使用流式接口缩短首个可见结果的等待，但流式不会减少总计算量。

AICore 是 Google 在兼容设备上交付的系统组件。Android 17 源码中另有 `android.app.ondeviceintelligence` / `android.service.ondeviceintelligence` 这组端侧智能（On-Device Intelligence，ODI）系统 API 与服务协调代码，但它属于平台或设备厂商的服务边界，不等同于 Google AICore 或 Gemini Nano 模型本身。分析 AOSP 平台能力时，不能把 AICore 当成 Android 17 兼容性定义文档（CDD）要求的通用服务。

## 1.15.4 路线二：LiteRT 与自带模型

需要自定义模型、离线控制或更广设备覆盖时，应用可以自带或按需下载模型，再由 LiteRT 等运行时执行。LiteRT 当前把 `CompiledModel` 作为高性能推理的主要 API，可在支持条件满足时使用 CPU、GPU 或 NPU；`Interpreter` API 继续用于兼容场景。

典型调用链如下：

```text
App → LiteRT CompiledModel / Interpreter
    → CPU backend 或 GPU/NPU delegate
    → 厂商运行时与驱动
    → 计算单元和内存
```

箭头越靠下，设备差异越大。运行时能创建某个 delegate，不代表整个计算图都由该加速器执行。以 GPU delegate 为例，不受支持的算子会让计算图分段在 CPU 与 GPU 上执行；频繁同步和数据转换可能抵消并行计算收益。

自带模型路线需要应用承担更多工作：

- 选择模型、精度和量化方式，并验证质量损失。
- 管理下载、版本、完整性、回滚和存储空间。
- 复用已编译模型和输入输出缓冲区，避免每次请求重新初始化。
- 按设备验证 delegate 覆盖率，也就是有多少算子真正交给目标加速器执行，并为失败或性能倒退准备后端回退。
- 对用户输入、输出内容和模型安全负责。

不能仅按“模型小于 100 MB”或“模型大于 1 GB”决定本地还是云端。参数量、上下文长度、KV cache（生成模型保存历史键和值的缓存）、数据类型、峰值临时张量、内存带宽和散热条件都会改变可运行性。最终选择要以目标设备上的测量结果为准。

## 1.15.5 AppFunctions：把应用能力提供给智能代理

AppFunctions 解决的是跨应用能力发现和执行。提供方声明函数元数据，并用 `AppFunctionService` 或 Android 17 的运行时注册实现函数；持有相应权限的系统级智能代理（agent）可以搜索函数、读取状态并发起调用。

AOSP `AppFunctionService` 要求服务声明 `BIND_APP_FUNCTION_SERVICE`，只有 `system_server` 可以绑定。跨包执行还受 `EXECUTE_APP_FUNCTIONS` 或系统级权限约束。它不是一个让任意应用自由调用其他应用的通用远程调用（RPC）注册表。

Android 17 源码明确标注了函数执行回调的线程边界：

```java
@MainThread
public abstract void onExecuteFunction(
        ExecuteAppFunctionRequest request,
        String callingPackage,
        SigningInfo callingPackageSigningInfo,
        CancellationSignal cancellationSignal,
        OutcomeReceiver<ExecuteAppFunctionResponse, AppFunctionException> callback);
```

回调从主线程进入，耗时 I/O、数据库和模型推理必须切到工作线程，并响应 `CancellationSignal`，最终通过 `callback` 返回成功或错误，否则智能代理的调用会直接造成应用主线程卡顿。

Android 17（API 37）还增加了运行时注册、Activity 或全局作用域、函数状态观察等能力。运行时注册只在相应进程和 `Context` 生命周期内有效，调用者必须保存 `AppFunctionRegistration`，并在不再需要时调用 `unregister()`。

AppFunctions 不负责动态模型加载、模型版本回滚或推理调度。它可以把“总结当前笔记”暴露为函数，但该函数内部使用 AICore、自带模型还是云端，是提供方自己的实现选择。

## 1.15.6 VoiceInteractionService 的位置

`VoiceInteractionService`、`VoiceInteractionSession` 和语音交互界面早于端侧大模型多年。它们负责系统选定语音交互服务的生命周期、会话与辅助上下文数据（assist data），不等同于语音识别模型或生成式推理运行时。

Android 17 的 AppFunctions 可以与当前 Activity 建立关联；例如 `VoiceInteractionSession` 可转换出 `AppFunctionActivityId`，让智能代理查询该 Activity 暴露的函数。这个连接只说明语音或智能代理入口可以调用应用能力，没有规定语音识别必须在本地运行，也没有给出固定的延迟、准确率、CPU 或内存指标。

语音功能应分别测量录音、端点检测、识别、意图/提示构造、模型推理、文本或语音输出。把这些阶段合成“端到端小于 500 ms”会隐藏网络、设备与交互模式的差异。

## 1.15.7 性能测量：先建立阶段时间线

一次 AI 请求至少拆成下面几段：

1. **能力检查与模型准备**：功能状态检查、模型下载或首次解压。
2. **运行时初始化**：创建会话或 `CompiledModel`、选择 delegate、编译计算图。
3. **输入处理**：图像解码与缩放、音频分帧、分词和缓冲区填充。
4. **推理**：首个结果延迟、单次推理延迟，或生成模型的首个 token（生成单位）延迟与持续吞吐。
5. **输出处理**：解码、过滤、结构化、持久化与界面更新。
6. **稳态影响**：PSS/RSS 进程内存、原生堆、GPU/NPU 缓冲区、电量、温度和降频后的尾部延迟。

应用可用 `android.os.Trace` 给自己的阶段添加区间。下面的写法确保发生异常时也能正常结束系统轨迹区间：

```kotlin
Trace.beginSection("ai/preprocess")
try {
    preprocess(input)
} finally {
    Trace.endSection()
}
```

对编译、推理和后处理分别添加区间，再与线程调度、Binder 调用、内存和温控轨道对齐。Perfetto 可以显示 CPU 线程是否被抢占、主线程是否等待，以及 AICore Binder 调用持续多久；能否看到 NPU 内部执行，要看设备厂商是否提供相应数据源。缺少 NPU 轨道时，不要仅凭 CPU 空闲推断推理一定在 NPU 上。

基准至少分成冷、热两组：

- 冷路径包含进程启动、模型映射、delegate 初始化和首次编译。
- 热路径复用会话、`CompiledModel` 和缓冲区，测量稳定请求。
- 连续运行覆盖热平衡后的性能，避免只记录设备尚未升温的前几次。
- 结果按设备型号、系统版本、运行时版本、模型版本和后端分组。

## 1.15.8 内存、量化与并发的常见误区

### 量化需要同时验性能和质量

INT8、FP16 或其他量化格式可能减小模型并减少内存流量，但收益取决于后端是否原生支持。量化是用更低位宽表示模型权重或中间数据。若 delegate 需要在 CPU 上频繁量化与反量化，或某些算子因此回退，延迟反而可能上升。质量评估应使用产品数据集，不能只看模型文件缩小比例。

### 批处理偏向吞吐，不一定适合交互

批量推理能提高离线任务吞吐，却会让第一个请求等待凑批，并提高峰值内存。聊天、相机预览和实时语音通常更关注首个结果与尾延迟；相册离线分类才更可能从批处理获益。

### 缓存要区分对象和产物

复用分词器（tokenizer）、推理会话、`CompiledModel` 与输入输出缓冲区，通常能减少延迟波动。磁盘上的编译缓存还必须绑定模型内容、运行时、delegate 和设备；版本不匹配时应安全失效，不能长期复用旧二进制产物。

### 并发不是越多越快

多个推理任务可能争用同一内存带宽和加速器队列，并加速升温。应用应限制并发，给交互请求优先级，并允许后台任务暂停或取消。AICore 还会执行自己的每应用请求与电量配额，线程池大小不能绕过这些限制。

## 1.15.9 功耗与热管理

普通应用不能可靠地指定 NPU 频率，也不应假设可以通过某个公开 API 固定动态电压与频率调节（DVFS）。频率和热节流由内核、Power HAL、温控服务与芯片固件共同决定。

应用可做的是控制工作量：

- 通过 `PowerManager` 的热状态监听器观察设备温度状态，降低采样率、输出长度或任务并发。
- 在 UI 不可见或生命周期结束时取消推理，避免无用户价值的后台计算。
- 对 AICore 的 `BUSY`、电量配额和后台禁止错误提供明确降级。
- 连续生成时记录温度状态变化前后的延迟与吞吐，不以单次峰值代表持续性能。
- 把电量测试放到固定亮度、网络、温度和电池状态下，比较完成同一任务所需的能量，而非只比较瞬时功率。

CPU、GPU 或 NPU 的标签本身不能决定能效。若 NPU 不支持关键算子、GPU 需要大量格式转换，或者小模型在 CPU 上已足够快，专用加速路径可能没有优势。

## 1.15.10 选型与回退清单

| 问题 | ML Kit GenAI / AICore | LiteRT 自带模型 | 云端模型 | AppFunctions |
|---|---|---|---|---|
| 核心目的 | 使用共享 Gemini Nano 能力 | 完全控制本地模型 | 使用服务端模型与知识 | 把应用动作提供给受信任的智能代理 |
| 设备覆盖 | 受设备、功能和模型版本限制 | 由最低 SDK、模型和后端决定 | 主要受网络与服务可用性限制 | Android 16+，仍处实验或预览阶段 |
| 模型管理 | AICore 负责共享模型 | 应用负责交付与版本 | 服务端负责 | 不管理模型 |
| 离线 | 支持，但要先完成模型准备 | 支持 | 通常不支持 | 取决于函数实现 |
| 主要约束 | 前台、配额、功能覆盖范围 | 包体或下载、内存、delegate 差异 | 延迟、费用、隐私 | 权限、元数据、目标应用生命周期 |

上线前至少回答这些问题：

1. 目标设备上如何判断功能可用，失败时回退到哪里？
2. 冷启动、首个结果、热路径和持续运行的指标分别是多少？
3. 模型、运行时或系统组件更新后，质量回归如何发现？
4. 输入是否允许离开设备，日志是否会记录敏感内容？
5. 应用进入后台、用户取消、设备升温或内存紧张时如何停止工作？
6. AppFunctions 的耗时工作是否已离开主线程，是否正确处理权限、取消和生命周期？

工程选型应以上述检查结果为依据，不能只看 NPU TOPS、模型文件大小或一次实验室峰值。TOPS 表示每秒可执行多少万亿次运算，是硬件理论吞吐指标，不能直接换算成某个模型的响应时间。Android 17 提供了跨应用能力框架和系统资源边界；端侧模型的可用性与性能，仍要在具体设备、具体运行时和具体模型上验证。

## 参考资料

- [Find the right AI/ML solution for your app](https://developer.android.com/ai/overview) — Android 官方对 ML Kit GenAI、LiteRT、云模型与 AppFunctions 的选型边界。
- [Overview of AppFunctions](https://developer.android.com/ai/appfunctions) — 可用版本、权限与预览状态。
- [AppFunctionManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionManager.java) — Android 17 搜索、状态、执行与运行时注册接口。
- [AppFunctionService.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/appfunctions/AppFunctionService.java) — 绑定权限、主线程回调与取消语义。
- [Neural Networks API](https://developer.android.com/ndk/guides/neuralnetworks) — NNAPI 弃用状态与历史运行模型。
- [Neural Networks API drivers](https://source.android.com/docs/core/interaction/neural-networks) — NNAPI 弃用后 Neural Networks HAL 仍受支持的边界。
- [OnDeviceIntelligenceManager.java](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/packages/NeuralNetworks/framework/platform/java/android/app/ondeviceintelligence/OnDeviceIntelligenceManager.java) — Android 17 ODI 系统 API 边界，区别于 Google AICore/Gemini Nano 交付。
- [ML Kit GenAI APIs](https://developers.google.com/ml-kit/genai) — AICore、设备支持、前台限制与配额。
- [LiteRT for Android](https://developers.google.com/edge/litert/android) — `CompiledModel`、`Interpreter` 与硬件加速入口。
- [LiteRT GPU delegates](https://developers.google.com/edge/litert/performance/gpu) — 算子覆盖、分段执行与缓冲区优化注意事项。
