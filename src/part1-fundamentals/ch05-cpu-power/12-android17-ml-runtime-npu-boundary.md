---
title: "Android 17 ML Runtime 与 NPU 访问边界"
chapter: "5.12"
section_title: "Android 17 ML Runtime 与 NPU 访问边界"
section: "5.12"
status: "finalized"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-02"
last_verified_against: "Android 17 / API 37 PackageManager reference, Android 17 release notes, source.android.com NNAPI Runtime docs, LiteRT Next docs"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/about/versions/17/release-notes"
  - type: official
    path: "developer.android.com/ai/custom"
  - type: official
    path: "developer.android.com/ndk/guides/neuralnetworks/migration-guide"
  - type: official
    path: "ai.google.dev/edge/litert/next/npu"
  - type: official
    path: "ai.google.dev/edge/litert/next/qualcomm"
  - type: official
    path: "ai.google.dev/edge/litert/next/mediatek"
  - type: aosp
    path: "hardware/interfaces/neuralnetworks/1.3/"
  - type: aosp
    path: "hardware/interfaces/neuralnetworks/aidl/"
  - type: aosp
    path: "frameworks/base/core/java/android/content/pm/PackageManager.java"
  - type: research
    path: "DeepResearch/2026-05-26-android-17-npu-aicore-lert-capability-boundary.md"
tags: [android17, litert, npu, nnapi, on-device-ai, performance]
related_chapters: ["5.10", "5.11", "16.5", "25.11"]
task6_state: reviewed
task9_state: "reviewed"
task2b_state: fixed
pipeline_stage: "ready-to-publish"
---

# 5.12 Android 17 ML Runtime 与 NPU 访问边界

Android 17 为神经网络处理器（Neural Processing Unit，NPU）访问增加了明确的系统控制层：目标 API 为 37 的应用如果要直接访问 NPU，必须在应用清单中声明 `android.hardware.npu`。这项变化用于决定某个用户标识符（User Identifier，UID）能否直接向 NPU 提交工作，以及系统如何将应用优先级传给 NPU 调度层。它没有为普通应用增加一个可以“执行任意模型”的通用 Android framework（系统框架）API。

应用仍需选择 LiteRT、厂商软件开发套件（Software Development Kit，SDK）、系统托管服务或旧版神经网络 API（Neural Networks API，NNAPI）路径。每条路径都有自己的模型格式、运行时、硬件覆盖和分发方式。本文按照 Android 17 / API 37 / `android-17.0.0_r1` 核对平台行为，讨论直接访问限制，以及 LiteRT `CompiledModel`、提前 / 即时编译（AOT / JIT）、Neural Networks HAL 和厂商后端如何衔接。

端侧推理的通用性能分析见 5.10 节；LLM 的 TTFT、TPOT、DVFS 与能效测量见 5.11 节。

## `android.hardware.npu`：声明、安装过滤与能力检测

Android 17 发布说明（release notes）的要求很具体：**以 Android 17 为目标版本的应用需要直接访问 NPU 时，必须声明 NPU 硬件 feature**。这里的 feature 是写入应用清单的设备能力声明。API 37 在 `PackageManager` 中新增以下常量：

```java
public static final String FEATURE_NEURAL_PROCESSING_UNIT =
        "android.hardware.npu";
```

这段代码定义了 feature 对应的字符串。应用清单通常这样声明该 feature：

```xml
<uses-feature
    android:name="android.hardware.npu"
    android:required="false" />
```

这段 XML 将 NPU 声明为可选能力。需要区分两个维度：

- 是否存在 `<uses-feature>`，决定目标 API 为 37 的应用能否获得直接访问资格；
- `android:required` 决定应用商店和安装器是否排除缺少该 feature 的设备。

大多数同时提供中央处理器（CPU）/ 图形处理器（GPU）路径的应用应使用 `required="false"`。这样既保留了 NPU 声明，使 Android 17 能识别应用请求 NPU 能力，又允许没有 NPU 的设备安装应用并改用 CPU 或 GPU。只有核心功能无法在其他后端运行时，才适合使用 `required="true"`。

Android 17 源码也体现了这一区别。`packages/modules/NpuManager` 中的 `PriorityManager.doesPackageUseNpuFeature()` 遍历 `PackageInfo.reqFeatures`（应用请求的 feature 列表），检查名称是否等于 `FEATURE_NEURAL_PROCESSING_UNIT`；它不使用 `required` 标志决定直接访问资格。`required` 仍只影响安装兼容性。

下面的代码在运行时检测设备是否声明该 feature：

```kotlin
val hasNpuFeature = context.packageManager.hasSystemFeature(
    PackageManager.FEATURE_NEURAL_PROCESSING_UNIT
)
```

返回 `true` 只说明设备声明了 NPU 或类似的 AI 加速硬件。它不能回答下列问题：

- LiteRT NPU 运行时（runtime）和厂商库是否已安装；
- 当前 SoC 是否在所用 LiteRT 版本的兼容范围内；
- 模型能否编译；
- 算子、数据类型、动态形状和量化格式是否受支持；
- 运行时最终使用 NPU、部分回退，还是完全改用其他后端；
- NPU 路径是否比 CPU/GPU 更快或更省电。

因此，`hasSystemFeature()` 只是访问前置条件之一，不能检测模型兼容性。应用还要调用所选运行时的兼容性 API，并分别处理模型编译、缓冲区（buffer）创建和首轮执行失败。

使用低于 37 的编译 SDK（`compileSdk`）时，清单仍可写字符串 `android.hardware.npu`；Java / Kotlin 代码无法引用 API 37 常量，可以暂时使用同一字符串。项目升级到 API 37 后应改用常量，让集成开发环境（IDE）、静态检查工具 lint 和 API 检查协助维护。

## Android 17 如何阻断未声明的直接访问

Android 17 的检查链跨越 framework 的 feature 信息、NpuManager 模块和新的 NPU 调度硬件抽象层（scheduling HAL）。下面的流程展示声明信息如何变为厂商 NPU 调度实现可以使用的配置：

```text
PackageManager.FEATURE_NEURAL_PROCESSING_UNIT
                    │
                    ▼
packages/modules/NpuManager
  PriorityManager 读取 targetSdk 与 reqFeatures
                    │
                    ▼
android.hardware.npu.SchedulingConfig
  uid / priority / hasDirectAccess / canAttributeOtherUid
                    │
                    ▼
android.hardware.npu.IScheduling
  setSchedulingConfigs() / updateSchedulingConfigs()
                    │
                    ▼
厂商 NPU 调度实现
```

在这条流程中，`SchedulingConfig` 同时携带身份、优先级和直接访问资格。在 `android-17.0.0_r1` 中，`PriorityManager.createPriorityInfo()` 会对 `targetSdkVersion >= Build.VERSION_CODES.CINNAMON_BUN` 的应用检查 NPU feature。相应功能开关（feature flag）启用时，缺少声明会使 `SchedulingConfig.hasDirectAccess` 变为 `false`。应用包更新后，`onPackageModified()` 还会重新判断目标 SDK 与 feature，并更新直接访问状态。

`hardware/interfaces/npu/aidl/android/hardware/npu/SchedulingConfig.aidl` 定义了四个关键字段：

- `uid`：应用的 Linux UID；
- `priority`：UID 级优先级，数值越小优先级越高；
- `hasDirectAccess`：该 UID 能否直接在 NPU 上执行；
- `canAttributeOtherUid`：中介服务能否将工作归因到另一个 UID。

`IScheduling` 以完整表格或增量更新的方式将配置交给 NPU，还可以注册调度事件回调。HAL 文档要求厂商尽力遵循优先级，但硬件能力仍可能限制实际执行顺序。该接口不向应用承诺固定延迟或专属 NPU 时间片。

`SchedulingConfig` 还明确区分直接访问与中介访问：`hasDirectAccess=false` 的应用不能直接执行 NPU 工作，但仍可能通过获准的中介服务请求能力。这与 release notes 使用的“directly access”一致。调用系统托管的 AI 服务，与在应用进程内加载厂商 NPU runtime，是两种不同的访问方式，必须分别遵循各自文档，不能套用同一条 manifest 结论。

Android 17 的兼容性测试套件（Compatibility Test Suite，CTS）为 NpuManager 提供了两类缺少 feature 的测试：

- 通过 NNAPI 路径运行推理应失败；
- 通过测试用 LiteRT / 厂商 delegate 路径直接运行推理也应失败。

这些测试证明系统控制层覆盖多种直接访问路径，但没有规定上层库必须抛出哪一种异常，也没有保证库会自动改用 CPU / GPU。应用仍应按照运行时文档配置后备路径（fallback），并记录最终选中的加速器（accelerator）。

## NpuManager 的系统管理职责边界

`packages/modules/NpuManager/framework/java/android/npumanager/NpuManager.java` 容易因名称而被误认为应用侧推理入口。Android 17 的 API 签名显示：

- `NpuManager` 是受功能开关控制的系统 API（flagged `@SystemApi`）；
- 模型装载请求受 `ACCESS_NPU_MODEL_MANAGER_API` 权限保护；
- 接口用于协调模型能否加载、卸载通知、模型大小和加载策略；
- 公共 SDK 没有借此获得提交张量或执行模型的通用接口。

NpuManager 的模型加载策略用于管理共享 NPU 资源：它可以根据普通 / 后台（normal / background）优先级、模型大小和预算，决定某个模型当前能否加载，或请求已经加载的模型释放资源。普通应用不能将这些 `@SystemApi` 当作公共 SDK 调用。

同样，`android.hardware.npu.IScheduling` 是系统与 NPU 实现之间的稳定 Android 接口定义语言（Android Interface Definition Language，AIDL）HAL。普通应用既不能直接配置 UID 优先级，也不能注册该 HAL 的调度回调。应用可见的稳定入口仍来自 LiteRT、厂商公开 SDK 或系统服务文档。

## LiteRT CompiledModel 的执行边界

LiteRT 由 Google AI Edge 独立发布，不会与 Android 开源项目（Android Open Source Project，AOSP）的 `android-17.0.0_r1` 固定在同一版本。当前官方文档将 `CompiledModel` 作为 Android 上面向 CPU、GPU、NPU 的现代推理 API，`Interpreter` 继续承担兼容路径。工程记录应分别固定并记录：

- Android 系统构建版本（build）与目标 / 编译 SDK；
- LiteRT Maven/C++ 版本；
- 模型文件哈希和量化格式；
- NPU 编译器插件（compiler plugin）、调度分发库（dispatch library）和厂商 runtime 版本；
- 设备 SoC、固件和驱动版本。

### 创建模型前先选择可用产物

使用 NPU 并非只需将 `Accelerator.CPU` 改为 `Accelerator.NPU`。官方示例先根据片上系统（System on Chip，SoC）兼容性选择模型产物和 runtime，再创建 `CompiledModel`。下面的流程展示这两个阶段：

```text
设备 feature 与 NPU compatibility
              │
              ├─ 选择 AOT AI Pack 中匹配的模型
              │
              └─ 或选择设备侧编译使用的原始模型
                         │
                         ▼
Environment + NPU runtime/compiler libraries
                         │
                         ▼
CompiledModel.Options(NPU, fallback...)
                         │
                         ▼
createInputBuffers / createOutputBuffers / run
```

流程中的 `ModelSelector`、`AiPackModelProvider` 和 `NpuCompatibilityChecker` 负责匹配模型产物与设备；`CompiledModel.Options` 描述候选 accelerator。模型产物选择与执行后端选择虽然相邻，仍是两个不同决定，需要分别记录。

### Fallback 需要显式配置并验证

LiteRT NPU 文档支持在 `CompiledModel.Options` 中同时给出 NPU 与 CPU / GPU，使 NPU 不可用时可以选择后备硬件；AOT 模型也支持后备路径。官方还说明，不受 NPU 支持的子图可以部分交给 CPU / GPU 执行。

这不表示任何模型都能在不损失精度或性能的情况下回退。需要验证：

- fallback 模型产物是否包含 CPU / GPU 可执行部分；
- 候选 accelerator 的次序与当前 LiteRT 版本语义；
- NPU 子图与 CPU / GPU 子图之间有多少同步和复制；
- NPU 编译失败、runtime 库缺失、执行失败分别会走哪条路径；
- fallback 后的精度、延迟、内存和温度是否仍满足要求。

为了让线上数据可以解释，至少要记录“请求的 accelerator 集合”和“最终使用的后端 / 子图分布”。只记录 `hasNpuFeature=true`，不能证明一次请求在 NPU 上完成。

### Buffer 与零复制

`CompiledModel` 会根据模型和后端创建输入输出张量缓冲区 `TensorBuffer`。官方 NPU 文档还给出基于 `AHardwareBuffer` 的零复制示例。零复制要求数据生产者、消费者、数据布局、同步栅栏（fence）和执行后端都支持同一种 buffer。将 Java 数组写入 NPU buffer，执行后再由 CPU 读回，仍然发生数据传输。

相机、GPU 预处理与 NPU 依次连接时，应测量完整管线。下面的流程列出容易遗漏的缓冲区获取、同步和释放阶段：

```text
camera / GPU producer
        → buffer acquire 与 fence wait
        → NPU inference
        → output consumer
        → buffer release
```

这条管线表明，只报告 NPU 计算内核（kernel）时间会遗漏格式转换、缓存维护（cache maintenance）、同步和 CPU 后处理。

## AOT、设备侧编译与分发

LiteRT NPU 文档将编译分为提前编译（Ahead-of-Time，AOT）和设备侧即时编译（Just-in-Time，JIT）：

| 路径 | 适用条件 | 首次运行成本 | 分发成本 |
|---|---|---|---|
| AOT / 离线编译（offline compilation） | 目标 SoC 已知，模型较大或初始化预算紧 | 可跳过大部分设备侧编译 | 要为不同 SoC / 版本准备匹配产物 |
| 设备侧 / JIT 编译（on-device / JIT compilation） | 希望分发较通用的原始模型，设备后端支持 JIT | 首次初始化会消耗时间与内存 | 产物准备较少，但需携带编译器 / 运行时（compiler / runtime） |
| JIT 编译缓存（compilation cache） | 模型、compiler、系统构建指纹（build fingerprint）和选项稳定 | 命中时减少重复编译 | 需要应用私有可写目录和缓存失效管理 |

官方文档指出，AOT 更适合目标 SoC 已知的大模型，可以降低启动时的编译成本和内存压力。AOT 仍可能需要读取模型文件、校验产物、加载 runtime、分配 buffer 和执行首轮预热，不能将其描述为“无需初始化”。

设备侧编译的缓存键至少会受到模型、厂商 compiler plugin、Android build fingerprint 和编译选项影响。应用升级、系统无线更新（Over-the-Air，OTA）或模型替换后出现新的编译峰值，可能是缓存正常失效；需要将未命中缓存（cache miss）的原因写入诊断日志。

### Play AI Pack 与 runtime library 是两类产物

当前官方流程将它们分开：

- AOT 编译模型可导出为 Play AI Pack（按设备交付 AI 模型的资源包），由 Google Play 向目标设备交付匹配模型；
- NPU runtime library 通过 Play Feature Delivery（按需交付应用功能模块的机制）分发；
- JIT 路径将原始 `.tflite` 放入应用，并提供对应 compiler / runtime library。

AI Pack 可以采用随安装交付（install-time）、安装后立即下载（fast-follow）或按需下载（on-demand）等方式，具体能力以 Play for On-device AI 文档为准。on-demand 可以减小首次安装下载量，但会增加首次进入功能时的网络等待和失败路径。应用应将“模型尚未下载”与“NPU 编译或执行失败”区分呈现。

Google Play 交付不覆盖所有渠道。没有 Google 移动服务（Google Mobile Services，GMS）的设备或其他应用商店需要独立方案，例如：

- 在 Android 应用安装包（APK）/ App Bundle 中携带适配产物；
- 自有下载服务按设备安全交付；
- 设备侧编译；
- 回退到可随应用分发的 CPU/GPU 路径。

多渠道方案还要检查模型许可、厂商 runtime 再分发条款、动态代码 / 原生库政策、完整性校验和磁盘配额。

## 各 NPU 后端的公开支持不同

当前 LiteRT NPU 文档列出的能力各不相同，不能概括成“Android NPU 都支持 AOT 和 JIT”：

| 后端 | `CompiledModel` 文档能力 | 需要额外确认 |
|---|---|---|
| Google Tensor | AOT 执行；Google Tensor SDK 处于 Beta，文档注明暂不支持设备侧 JIT | 支持的 Tensor 代际、模型产物和 AI Pack |
| Qualcomm AI Engine Direct | AOT 与设备侧编译 | Qualcomm Neural Network（QNN）/ Hexagon Tensor Processor（HTP）版本、支持的 SoC 与算子 |
| MediaTek NeuroPilot | AOT 与设备侧编译 | 支持的 Dimensity SoC、runtime 与算子 |
| Samsung Exynos AI LiteCore | AOT 与设备侧编译 | 公开兼容列表和 runtime 版本 |
| Intel OpenVINO | AOT 与设备侧编译 | Android / 目标平台覆盖和模型限制 |

这些列表会随 LiteRT 发布版本（release）更新，不能用 Android 17 平台版本替代。发布前应保存所用文档日期或 release、兼容性查询结果和测试设备信息。

### Google Tensor 仍需逐层验证是否实际使用 NPU

对于 Google Tensor 设备，当前可核实的公开结论是：LiteRT NPU 文档支持通过 `CompiledModel` 执行 AOT 产物，并提供使用 `NpuCompatibilityChecker.GoogleTensor` 匹配设备的示例；设备侧 JIT 仍标为不支持。

仍需验证四层证据：

1. 设备是否声明 `android.hardware.npu`；
2. LiteRT compatibility checker 是否接受该设备；
3. AI Pack 是否已交付适配相应 Tensor 代际的模型产物；
4. 运行时是否成功加载 NPU 调度分发库 / 运行时（dispatch / runtime），并按预期执行或回退。

芯片名称、营销材料或 `hasSystemFeature()` 都不能替代这四项检查。AICore 或其他系统托管模型服务也有独立的设备、地区、模型与更新条件，不等同于应用内嵌 LiteRT 的 NPU 后端。

## NNAPI、Neural Networks HAL 与 NPU scheduling HAL

Android 17 中同时存在名字相近、职责不同的接口。

### NNAPI NDK API 已进入弃用期

NNAPI 是应用通过原生开发套件（Native Development Kit，NDK）使用的 C API。官方从 Android 15 开始将 NNAPI NDK API 标记为弃用（deprecated），并建议应用迁移到 LiteRT 等受支持路径。弃用不表示 Android 17 已删除 NNAPI，也不表示已发布应用会立即无法运行；它表示新项目不应再将 NNAPI NDK API 作为长期主路径。

迁移时应保留旧设备的对照基线，并验证 LiteRT 在 CPU、GPU、NPU 上的结果与精度，不能只替换 API 名称。

### Neural Networks HAL 继续存在

官方 NNAPI Runtime 文档明确说明：

- Android 11 及以下使用 HAL 接口定义语言（HAL Interface Definition Language，HIDL）定义的 HAL 版本；
- Android 12 及以上的 NNAPI HAL 修订版（revision）使用 AIDL；
- NNAPI NDK API 弃用不影响 Neural Networks HAL 和驱动支持。

在 `android-17.0.0_r1` 中：

- 历史 HIDL 1.3 位于 `hardware/interfaces/neuralnetworks/1.3/`；
- 当前 AIDL 位于 `hardware/interfaces/neuralnetworks/aidl/`；
- 冻结 AIDL API 目录包含版本 1～4；
- 当前接口仍有 `IDevice.getSupportedOperations()`、模型准备（preparation）、编译缓存（compilation cache）、设备缓冲区（device buffer）、同步 / 围栏执行；
- AIDL v4 还包含 `ExecutionConfig`、`IExecution` 和接收配置（config）的执行入口。

这些接口面向 NNAPI Runtime 与厂商驱动（vendor driver）。普通应用不能将 AIDL `IDevice` 当作公共 SDK。

### NPU scheduling HAL 只管理调度身份与生命周期

Android 17 新增的 `hardware/interfaces/npu/aidl/` 提供 `IScheduling`、`SchedulingConfig`、`WorkInfo` 和回调。它传递 UID 优先级、直接访问资格、归因和工作开始 / 结束事件，但不定义模型图、张量（tensor）、算子或编译。

下面的对照概括两套 HAL 分别管理的对象：

```text
Neural Networks HAL
  关注：model / operation / prepared model / execution / buffer

NPU scheduling HAL
  关注：UID / priority / direct access / attribution / work lifecycle
```

这段对照显示，Neural Networks HAL 管理模型执行对象，NPU scheduling HAL 管理身份和工作生命周期。LiteRT NPU 还可能使用厂商 compiler plugin、dispatch library 和 runtime，不保证经过 Neural Networks HAL。只要它直接向受 Android 17 控制的 NPU 提交工作，仍需满足 `android.hardware.npu` 声明要求。

## 部分委托（Partial delegation）的收益与代价

LiteRT 官方 NPU 路径支持将未被 NPU 接收的子图交给 CPU / GPU。部分委托（partial delegation）可以提高模型兼容性，也会增加不同后端交界处的成本：

- 子图切换需要调度与同步；
- 不同后端的张量内存布局（tensor layout）可能触发转换；
- 中间 buffer 可能在 CPU、GPU、NPU 可访问的内存之间复制；
- 短小 NPU 子图的加速时间可能小于切换成本；
- CPU / GPU fallback 会重新占用原本希望节省的功耗与散热预算。

评估时至少记录：

- NPU、GPU、CPU 各自执行的子图或算子数；
- 编译警告与不支持的算子（operation，op）；
- 中间 buffer 大小和复制次数；
- 端到端延迟（latency），而非单个 NPU 子图时间；
- fallback 发生率和触发原因；
- 结果精度与确定性。

如果运行时没有公开子图分布，应将结论写成“请求 NPU 并成功完成”，再用运行时日志和系统信号说明推断依据；不能写成“模型完整运行在 NPU”。

## 性能、内存与功耗验证

只有端到端指标改善，模型使用 NPU 才具有产品价值。建议将实验分成初始化和稳态两部分。

| 指标 | 测量边界 | 常见问题 |
|---|---|---|
| 模型可用时间 | 请求下载到产物可加载 | AI Pack 未交付、磁盘不足、校验失败 |
| 编译 / 加载时间 | 创建运行环境（environment）到 `CompiledModel` 可用 | JIT 未命中缓存（cache miss）、runtime 加载、AOT 不匹配 |
| 首次推理 | buffer 准备到第一份结果 | 首轮预热、内存页、后端初始化 |
| 稳态延迟 | 固定输入、多次执行 | 调度波动、复制、partial delegation |
| LLM TTFT / TPOT | 按 5.11 节的 token 边界 | prefill / decode 后端不同、KV cache 增长 |
| 峰值内存 | 初始化和执行阶段分别采集 | 编译器工作区（compiler workspace）、tensor、cache、重复模型 |
| 请求能量 | 同一供电与屏幕条件下积分 | 整机基线、USB 充电、后台任务 |
| 持续性能 | 运行到温度和频率趋于稳定 | 热限制（thermal clamp）、共享 NPU 竞争 |

### Trace 能看到什么

Perfetto 通常可以稳定采集应用时间区间（slice）、CPU 调度、CPU 频率、进程内存与部分电源 / 温度信号。GPU、NPU、互连和内存频率轨道依赖设备与厂商数据源。没有 NPU 轨道（track）时，可以联合观察：

- 应用标注的编译 / 运行（compile / run）slice；
- LiteRT 或厂商 runtime 日志；
- CPU/GPU 执行时间与频率；
- PowerStats 可用的能量消费者或部件能量轨道（power rail）；
- 热状态 / 热余量（thermal status / headroom）；
- 输出回调时间。

这些信号可用于形成有证据支持的推断，但不能单独将“CPU 利用率下降”当作模型使用 NPU 的证明。整机电流也不能直接当作 NPU 部件功耗。

### 稳态测试要覆盖共享资源

NPU 可能由系统模型服务、相机、语音或其他应用共享。测试应包含单请求、并发请求、前后台切换和持续运行。Android 17 的 scheduling HAL 支持 UID 级优先级和工作生命周期回调，但第三方应用不能因此自行设置最高优先级。

持续测试需要运行到 token / 帧延迟、温度和频率上限呈现稳定趋势，并按时间窗口报告。固定规定“运行 3 分钟”或“运行 10 分钟”不适用于所有设备；终止条件和环境温度应写入报告。

## 后台执行边界

NPU feature 只描述设备能力与访问资格，不会授予应用额外的后台执行机会。JobScheduler、WorkManager、前台服务、设备休眠（Doze）、应用待机（App Standby）和电池策略仍会决定任务何时运行、能运行多久。

按用户意图选择执行方式：

- 用户正在等待的即时推理，应与可见界面和取消操作绑定；
- 允许延迟的摘要、索引或批处理，使用 JobScheduler / WorkManager 约束；
- 体积大的模型下载交给合适的下载和存储管理组件；
- 高温、低电量或后台受限时，减少并发、缩小模型或推迟非必要任务。

系统中介服务能否代应用访问 NPU，取决于该服务的公共 API 约定、配额和归因规则。不能因为 `SchedulingConfig` 包含 `canAttributeOtherUid`，就推断任意应用都可通过 Binder（Android 进程间通信机制）服务绕过 feature 要求。

## 从 TFLite / NNAPI 迁移到 LiteRT

迁移前先保存可比较的旧路径基线：

| 检查项 | 迁移前要记录 | LiteRT 路径要验证 |
|---|---|---|
| 模型 | 文件哈希、输入形状、量化 | 转换后精度和支持的 op |
| CPU | 线程数、XNNPACK（LiteRT 的优化 CPU 后端）、CPU 亲和性 | `CompiledModel` CPU 基线 |
| GPU | delegate 配置、缓存、精度 | GPU 后端（backend）与渲染竞争 |
| NNAPI | 设备选择、fallback、缓存 | NPU / CPU / GPU 候选和失败处理 |
| 冷启动 | 加载、编译、预热 | AOT / JIT / cache 分段 |
| 内存 | 权重、工作区（workspace）、tensor | 编译器（compiler）峰值与 buffer 生命周期 |
| 分发 | APK、动态模块、渠道 | AI Pack、Play Feature Delivery（PFD）与非 Play 方案 |
| 可观测性 | 旧日志和 trace | 最终 accelerator、子图分布、错误码 |

推荐按以下顺序迁移：

1. 用 LiteRT CPU 路径复现旧 CPU 路径的正确性和性能；
2. 加入 GPU，验证算子覆盖、精度和 UI 渲染竞争；
3. 对兼容设备加入 NPU feature、runtime 与模型产物；
4. 明确配置 `CompiledModel.Options` 的 fallback；
5. 分开测 AOT、JIT 首次编译和缓存命中；
6. 做持续功耗、温控、后台与并发测试；
7. 最终决定哪些设备启用 NPU，哪些设备保留 GPU / CPU。

如果目标是缩短首次结果等待时间，就重点比较模型交付、编译和预热；如果目标是降低持续功耗，就比较稳态下的请求能量、温度和吞吐。单个平均延迟值无法同时回答这两个问题。

## 发布前检查清单

- [ ] 目标 API 37 的直接 NPU 访问路径声明了 `android.hardware.npu`；
- [ ] `required` 与产品的安装范围一致；
- [ ] 运行时同时检查设备 feature、SoC 兼容性和模型编译结果；
- [ ] Android build、LiteRT、runtime、compiler、模型与 SoC 版本均可追溯；
- [ ] `NpuManager` 没有被写成普通应用推理 API；
- [ ] NPU scheduling HAL 与 Neural Networks HAL 的职责已分开；
- [ ] AOT、JIT 和缓存命中的初始化时间分别记录；
- [ ] AI Pack 与 NPU runtime library 的分发方式分别记录；
- [ ] Google Tensor、Qualcomm、MediaTek 等后端按各自文档写边界；
- [ ] fallback 与 partial delegation 有运行时证据；
- [ ] 端到端 latency 包含复制、同步、预处理和后处理；
- [ ] 功耗结论包含供电、屏幕、温度与持续时间；
- [ ] 无 GMS 或非 Play 渠道有替代模型 / runtime 交付方案；
- [ ] NNAPI 弃用没有被写成 HAL 或驱动已删除。

## Android 17 源码索引

以下路径均已按照 `android-17.0.0_r1` 复核：

- `frameworks/base/core/java/android/content/pm/PackageManager.java`
  - `FEATURE_NEURAL_PROCESSING_UNIT`
- `packages/modules/NpuManager/service/java/com/android/server/npumanager/PriorityManager.java`
  - `createPriorityInfo()`
  - `doesPackageUseNpuFeature()`
  - `onPackageModified()`
- `packages/modules/NpuManager/framework/java/android/npumanager/NpuManager.java`
  - flagged `@SystemApi` 模型加载协调接口
- `packages/modules/NpuManager/tests/cts/cts_npu_manager_test.py`
  - 有 / 无 NPU feature 时的 NNAPI 与 delegate 访问测试
- `hardware/interfaces/npu/aidl/android/hardware/npu/`
  - `IScheduling.aidl`
  - `SchedulingConfig.aidl`
  - `WorkInfo.aidl`
  - `ISchedulingCallback.aidl`
- `hardware/interfaces/neuralnetworks/aidl/android/hardware/neuralnetworks/`
  - `IDevice.aidl`
  - `IPreparedModel.aidl`
  - `IExecution.aidl`
  - `ExecutionConfig.aidl`
- `hardware/interfaces/neuralnetworks/1.3/`
  - Android 11 及以下 HIDL 历史接口

## 参考资料

- Android 17 release notes：<https://developer.android.com/about/versions/17/release-notes>
- `PackageManager` API 37 reference：<https://developer.android.com/reference/android/content/pm/PackageManager>
- NNAPI Runtime：<https://source.android.com/docs/core/ota/modular-system/nnapi>
- NNAPI migration guide：<https://developer.android.com/ndk/guides/neuralnetworks/migration-guide>
- LiteRT Android：<https://developers.google.com/edge/litert/android>
- LiteRT NPU acceleration：<https://developers.google.com/edge/litert/next/npu>
- Qualcomm NPU：<https://developers.google.com/edge/litert/next/qualcomm>
- MediaTek NPU：<https://developers.google.com/edge/litert/next/mediatek>

LiteRT、Play for On-device AI 和厂商兼容列表会独立更新。使用这些资料时应记录 runtime release 和查询日期，不能只记录 Android 17 平台版本。
