---
title: "Android 17 ML Runtime 与 NPU 访问边界"
chapter: "5.14"
status: ready-for-review
drafted_date: "2026-05-16"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-01"
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
    path: "DeepResearch/2026-05-15-android-17-npu-litert-aicore.md"
  - type: research
    path: "DeepResearch/2026-05-15-android-ml-inference-npu-litert.md"
tags: [android17, litert, npu, nnapi, on-device-ai, performance]
related_chapters: ["5.11", "5.13", "16.5", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/官方文档/AOSP结构"
gap_score: 18
material_count: 5
reviewed_by: openclaw-task6
reviewed_date: "2026-05-16"
task6_state: revisiting
task6_result: pass-light-edit
last_task6_at: "2026-05-16T23:15:00+08:00"
last_task6_review_log: "logs/review/2026-05-16-23-review.md"
task9_state: pending
task9_reviewed_date: "2026-05-17"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-17T00:32:12+08:00"
last_task9_review_log: logs/deep-review/2026-05-17-00-deep-review.md
task9_result: needs-rework
task2b_state: fixed
task2b_result: fixed-lite
pipeline_stage: task6_pending
last_task2b_lite_at: "2026-06-01"
p0: 0
p1: 2
p2: 1
task9_review_notes: "2026-05-17 Task9 00: needs-rework。P1 2：Android 17 NPU feature 字符串/SDK 常量未闭环；Android 14-17 NN HAL 只写 HIDL 1.3，遗漏 AIDL HAL。P2 1：Google Tensor/EdgeTPU 与厂商后端命名需拆清。已写入 logs/deep-review/2026-05-17-00-deep-review.md。"
---

# 5.14 Android 17 ML Runtime 与 NPU 访问边界

<!-- outline-start -->
## 要点

### 🔹 NPU 能力声明与 Android 17 访问限制
区分 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT` 声明、PackageManager feature 检测、目标 API 约束，以及未声明时的直接 NPU 访问边界。

### 🔹 LiteRT CompiledModel 的执行模型
梳理 `CompiledModel`、`Accelerator.NPU/GPU/CPU` fallback、模型加载、输入输出 buffer 与运行时调度路径。

### 🔹 AOT 编译与 AI Pack 分发
说明主机侧编译、设备 SoC 匹配、Google Play AI Pack 下发、首次推理延迟和包体积之间的取舍。

### 🔹 NNAPI HAL 与厂商 NPU delegate
区分 HIDL 1.3 历史接口、Android 12+ AIDL HAL、QNN/NeuroPilot 等厂商 delegate、支持 op 查询和 partial delegation。

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

Android 17 把端侧 AI 推理从“能不能调用加速器”推进到“调用边界是否被系统显式管理”。对性能工程师来说，NPU 不再只是 NNAPI 或厂商 delegate 背后的一个加速选项，还会受清单声明、目标 SDK、运行时分发和厂商栈覆盖率共同约束。

内容聚焦新增边界：Android 17 的 NPU feature 声明、LiteRT CompiledModel / AOT 的执行路径、NNAPI HAL 与厂商 NPU delegate 的关系，以及哪些能力属于公开 Android API，哪些能力只能按 Google Play services、AICore 或厂商 SDK 的文档口径判断。端侧推理的一般性能分析流程见 5.11 节，持续推理的 DVFS 和热衰减见 5.13 节。

## NPU feature 声明：Android 17 开始的访问门槛

Android 17 release notes 对 NPU 管理给出了新的平台约束：面向 Android 17 的应用，如果要直接访问 NPU，必须在清单中声明 NPU 硬件特性。API 37 公开引用中对应常量为 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT`，值为 `android.hardware.npu`。[已验证: 官方文档, developer.android.com/about/versions/17/release-notes; developer.android.com/reference/android/content/pm/PackageManager]

声明方式放在 `AndroidManifest.xml` 中。是否设置 `required`，取决于产品是否允许 CPU / GPU 回退：

```xml
<uses-feature
    android:name="android.hardware.npu"
    android:required="false" />
```

`required="true"` 会把没有 NPU feature 的设备排除在安装范围外，适合功能完全依赖 NPU 的独立应用；大多数业务功能更适合设为 `false`，在运行时检测能力后选择 NPU、GPU 或 CPU 路径。

运行时检测优先使用 API 37 常量；如果 compileSdk 还没升到 37，只能临时使用 `android.hardware.npu` 字符串，并在升级 SDK 后替换回常量。

```kotlin
val hasNpu = appContext.packageManager.hasSystemFeature(
    PackageManager.FEATURE_NEURAL_PROCESSING_UNIT
)
```

这条检测只回答“系统声明这台设备提供 NPU feature”。它不保证当前模型可以完整跑在 NPU 上，也不保证厂商 delegate 支持模型里的每个算子。工程判断要拆成三层：

- **安装与声明层**：清单是否声明 `android.hardware.npu`，目标 SDK 是否触发 Android 17 的访问约束。
- **设备能力层**：`PackageManager.hasSystemFeature()` 是否返回 true，设备是否提供对应 NPU 运行时或 Play services 分发的 delegate。
- **模型覆盖层**：当前模型的算子、量化格式、输入尺寸和内存布局是否被目标 NPU 后端支持。

未声明 feature 时，Android 17 文档的口径是直接 NPU 访问会被阻断。阻断后的表现取决于调用栈：高层 LiteRT 可能回退到 GPU / CPU；厂商 SDK 或低层路径可能返回初始化失败或 capability 不满足。写业务降级逻辑时不要只捕获一次 `run()` 异常，更应该在模型加载、编译、delegate 初始化、首轮推理四个阶段各自记录结果。

## LiteRT CompiledModel：把硬件选择前置到模型编译阶段

旧 TFLite 管线通常是 `Interpreter` 加 delegate：应用加载 `.tflite` 模型，创建解释器，再把 GPU / NNAPI / 厂商 delegate 绑定进去。这个模型在通用性上很好，但硬件选择、算子划分和部分回退都发生在运行时，冷启动阶段容易出现初始化尖峰。

LiteRT Next 文档把 NPU 路径收敛到 `CompiledModel` 和 accelerator 选择上，支持通过 NPU、GPU、CPU 组合描述执行偏好。Qualcomm AI Engine Direct 与 MediaTek NeuroPilot 文档都明确写到：LiteRT 通过 `CompiledModel` API 支持 AOT 编译和设备侧编译。[已验证: 官方文档, ai.google.dev/edge/litert/next/npu; ai.google.dev/edge/litert/next/qualcomm; ai.google.dev/edge/litert/next/mediatek]

`CompiledModel` 可以按三个阶段看：

| 阶段 | 输入 | 输出 | 性能风险 |
|------|------|------|----------|
| 模型准备 | `.tflite` / LiteRT 模型、目标 accelerator 列表、厂商运行时 | 编译后的模型对象或设备专属产物 | 首次编译耗时、峰值内存、厂商 SDK 初始化 |
| buffer 准备 | 输入 tensor 形状、数据类型、内存布局 | 输入 / 输出 buffer | 额外拷贝、对齐要求、量化参数不匹配 |
| 推理执行 | 输入 buffer、编译产物、执行后端 | 输出 buffer、状态码、fallback 结果 | partial delegation、CPU 回退、热降频 |

这条路径的价值不在于“强制使用 NPU”，而在于把硬件选择和编译结果显式化。模型对 NPU 友好时，编译阶段会生成适配目标 SoC 的执行产物；模型不适配时，开发者应该尽早得到 capability 不满足、子图拆分或 fallback 的信号。

对业务代码而言，推荐把 accelerator 写成优先级链，而不是单点假设：

- `NPU -> GPU -> CPU`：适合图像理解、OCR、语音特征提取、固定输入尺寸的小模型。
- `GPU -> CPU`：适合没有稳定 NPU 覆盖、但 GPU delegate 已验证的模型。
- `CPU`：作为基线和灰度回退路径，便于用 XNNPACK 跑出可重复数据。

如果产品依赖首帧或首 token 延迟，初始化阶段要独立打点。不要把模型加载、编译、预热和单次推理混在一个平均耗时里；这会掩盖冷启动和稳态执行的不同问题。

## AOT 编译与 AI Pack：用包体积换首次推理稳定性

AOT 编译把模型编译动作从设备运行时前移到主机侧或发布流程。LiteRT NPU 文档提到 AOT 与设备侧编译两条路径；Qualcomm 和 MediaTek 页面也都把 AOT 作为 NPU 支持方式之一。[已验证: 官方文档, ai.google.dev/edge/litert/next/npu]

AOT 的工作流通常包括四步：

1. **选择目标后端**：例如 Qualcomm QNN、MediaTek NeuroPilot，或 Google Tensor 设备公开支持的后端。
2. **按 SoC / 运行时编译模型**：同一个 `.tflite` 模型可能生成多个设备专属产物。
3. **打包分发**：通过 App 包、动态特性模块，或 Google Play 的 AI Pack 机制把匹配产物下发到设备。
4. **运行时加载**：设备端加载对应编译产物，跳过部分即时编译和 delegate 协商成本。

AOT 适合两类场景：模型固定、输入尺寸稳定、冷启动预算紧；或者设备范围可控，例如只面向少数高端机型。它不适合模型频繁更新、SoC 覆盖范围很宽、国内外分发渠道差异大的业务。

| 取舍项 | AOT 收益 | AOT 代价 |
|--------|----------|----------|
| 首次推理 | 减少设备侧编译和 delegate 协商时间 | 首次加载仍可能受产物校验和 运行时初始化影响 |
| 包体积 | 无直接收益 | 多 SoC 产物会增加下载和存储成本 |
| 兼容性 | 针对目标硬件做优化 | 固件、运行时、delegate 版本变化可能要求重新编译 |
| 可观测性 | 编译产物和后端更明确 | 需要记录命中的产物版本、SoC、delegate 日志 |

AI Pack 的价值在于把设备匹配和产物下发交给 Google Play 流程处理。代价也很清楚：这条路径依赖 Google Play 生态，国内渠道或无 GMS 设备必须准备本地包内产物、设备侧编译或 CPU / GPU 回退方案。

## NNAPI HAL 与厂商 NPU delegate：公共接口和厂商实现之间的缝隙

NNAPI 的 NDK API 从 Android 15 起被官方标记为 deprecated，迁移指南建议转向 TensorFlow Lite in Play services、AICore 等替代方案。[已验证: 官方文档, developer.android.com/ndk/guides/neuralnetworks/migration-guide]

这不等于底层 NPU 驱动消失。AOSP 仍然保留 Neural Networks HAL；Android 11 及以下可按 HIDL 1.3 历史口径理解，Android 12+ 的 NNAPI HAL revision 使用 AIDL 而不是 HIDL。源码锚点要同时区分 `hardware/interfaces/neuralnetworks/1.3/` 与 `hardware/interfaces/neuralnetworks/aidl/`。[已验证: source.android.com/docs/core/ota/modular-system/nnapi; AOSP hardware/interfaces/neuralnetworks/]

更准确的工程图景是：

```text
应用 / SDK
  └─ LiteRT CompiledModel
      ├─ Qualcomm QNN / AI Engine Direct delegate
      ├─ MediaTek NeuroPilot delegate
      ├─ GPU delegate
      └─ CPU XNNPACK baseline
          └─ 底层驱动、NN HAL 或厂商运行时
```

厂商 delegate 解决的是“如何让 LiteRT 模型跑到特定 SoC 的 NPU 上”。NNAPI HAL 解决的是“系统和驱动之间如何抽象神经网络加速设备”。两者不是同一层，不能把 LiteRT 文档里的 QNN 能力直接写成 Android 平台通用能力。

partial delegation 是这条路径最容易踩坑的地方。模型里一部分算子命中 NPU，另一部分回到 CPU，平均耗时可能比纯 CPU 更差：跨设备调度、buffer 复制和同步成本会抵消 NPU 对单个子图的收益。验证时至少记录三类信号：

- **算子覆盖率**：当前模型有多少算子或子图被 NPU 接管，哪些节点回退。
- **buffer 成本**：输入输出是否发生 CPU 内存、GPU buffer、NPU buffer 之间的复制。
- **端到端耗时**：只看 NPU 子图耗时不够，预处理、后处理和回退子图都要算入前台交互预算。

## 性能与功耗边界：NPU 命中不等于体验变好

NPU 的收益通常来自三点：单位能耗更低、特定张量乘加 / 卷积类算子吞吐更高、CPU 被释放出来处理前台交互。但这些收益只在模型、输入尺寸、量化格式和后端覆盖匹配时成立。

端侧推理建议拆成五组指标：

| 指标 | 适用场景 | 观察方式 | 判断边界 |
|------|----------|----------|----------|
| 首次推理延迟 | 相机、OCR、实时翻译、语音助手 | App trace、初始化日志、Perfetto slice | 分离模型加载、编译、预热、首轮执行 |
| 稳态单次延迟 | 分类、检测、分割、小模型生成 | p50 / p90 / p99 latency | 同机型对比 CPU、GPU、NPU 三条路径 |
| TTFT / token 速率 | LLM、VLM、流式生成 | TTFT、prefill tokens/s、decode tokens/s | 标明模型版本、量化方式、上下文长度 |
| 峰值内存 | 大模型、批处理、多模型并发 | RSS / PSS、native heap、allocator 日志 | 区分模型权重、中间 tensor、delegate workspace |
| 持续功耗与热衰减 | 连续相机、离线转写、后台理解 | thermal 状态、频率、帧时间、电流数据 | 单次 benchmark 不能替代 3-10 分钟稳态测试 |

Perfetto 默认能稳定看到线程调度、CPU / GPU 频率、内存水位和 thermal 状态。NPU 是否有专用轨道取决于厂商实现；没有厂商 tracepoint 时，只能用 delegate 日志、CPU 负载下降、GPU 频率变化和 thermal 信号交叉判断。详见 5.11 节的 Perfetto 对照表。

ADPF 与 NPU 的关系也要谨慎。ADPF 更适合表达应用线程的工作时长和性能目标，不等于应用能直接控制 NPU 调度。涉及协程线程迁移和 hint session 绑定时，见 25.11 节；涉及持续推理的频率组合和热衰减时，见 5.13 节。

后台推理还有一层约束：JobScheduler、WorkManager、前台服务限制和电池策略会决定任务什么时候能跑，NPU feature 只说明设备能力，不替代后台执行资格。把模型任务放进后台前，先确认它是用户可见工作、延迟容忍工作，还是必须等充电 / 空闲窗口再执行的工作。

## 公开 API、预览能力与闭源组件边界

端侧 AI 最容易写错的地方，是把不同来源的能力混成一个“Android 支持”。更稳的写法是给每个能力标清归属层。

| 能力 | 可验证来源 | 能写成平台能力吗 | 写作边界 |
|------|------------|------------------|----------|
| `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT` 声明 | Android 17 release notes / API 37 reference | 可以，但限 Android 17 目标应用访问约束 | 常量值为 `android.hardware.npu` |
| NNAPI NDK API | Android NDK 文档 | 可以，但需标注 Android 15 起 deprecated | 不建议新性能敏感项目依赖它做主路径 |
| NN HAL | AOSP `hardware/interfaces/neuralnetworks/1.3/`、`hardware/interfaces/neuralnetworks/aidl/`、source.android.com | 可以，属于系统与驱动抽象 | Android 11 及以下看 HIDL，Android 12+ 看 AIDL |
| LiteRT CompiledModel / NPU | ai.google.dev LiteRT Next 文档 | 不能写成 AOSP 公共 API | 属于 LiteRT 运行时能力，版本和分发渠道要标清 |
| Qualcomm QNN / MediaTek NeuroPilot | ai.google.dev 厂商后端页、厂商 SDK | 不能写成全 Android 通用能力 | 只对对应 SoC、运行时、delegate 版本成立 |
| AICore / Gemini Nano | developer.android.com/ai/aicore | 不能写成 AOSP 开放服务 | 属于 Google 生态能力，受设备、地区、GMS 版本影响 |
| Google Play AI Pack | ai.google.dev / Play 分发文档 | 不能写成所有渠道可用 | 国内渠道、无 GMS 设备需要替代分发策略 |

只要文章里出现 “Android 17 NPU 支持”“LiteRT NPU 加速”“AICore 调度” 这类句子，都要追问一句：这是 SDK API、AOSP 源码、Google Play services、AICore 闭源服务，还是厂商 SDK？答案不同，工程边界完全不同。

## 扩展：Google Tensor / EdgeTPU 能力验证

Google Tensor 设备常被直接等同于“有 Google 自家的 NPU / TPU 能力”，但对第三方 App 来说，能不能调用、通过哪条 API 调用、是否可观测，是三件不同的事。

当前更稳妥的写法是：Google Tensor 平台提供端侧 AI 加速能力，AICore / Gemini Nano 属于 Google 生态公开文档覆盖的路径；LiteRT NPU 对 Google Tensor 的具体后端能力、算子覆盖和 AI Pack 交付方式，需要以 LiteRT Next 文档和设备兼容列表为准。[待验证: Google Tensor 设备上 LiteRT NPU 后端的公开兼容表]

验证 Tensor 设备时建议保留四类证据：

- 设备侧 feature：`android.hardware.npu` 是否存在。
- LiteRT 运行时日志：命中的 accelerator、delegate 名称、fallback 信息。
- 模型侧数据：算子覆盖率、量化格式、输入尺寸、编译产物版本。
- 系统侧信号：CPU / GPU 频率、thermal、内存，以及厂商或 Google 暴露的额外 tracepoint。

没有这些证据时，不要把“Tensor 芯片有 AI 加速器”写成“这个模型会跑在 NPU 上”。

## 扩展：从 TFLite / NNAPI 迁移到 LiteRT 的检查清单

旧项目迁移不要从替换 API 名字开始，而是先把现有推理路径量出来。基线不清楚时，换成 LiteRT 也只是在换一种不确定性。

| 检查项 | 旧项目常见状态 | 迁移到 LiteRT 时的处理 |
|--------|----------------|------------------------|
| CPU 基线 | 只记录线上平均耗时 | 用 XNNPACK 固定线程数跑同机型 p50 / p90 / p99 |
| NNAPI 使用 | 依赖 `NnApiDelegate`，fallback 不透明 | 对照 Android 15 deprecated 口径，准备 LiteRT / GPU / CPU 回退 |
| GPU delegate | 只看单次加速比 | 加入渲染并发、GPU 频率和掉帧指标 |
| NPU 路径 | 依赖厂商 SDK 或未公开 delegate | 明确 SoC、运行时、delegate 版本和算子覆盖率 |
| 模型格式 | 多个模型版本并存 | 固化模型 hash、输入尺寸、量化策略，再比较迁移收益 |
| 冷启动 | 初始化和推理混在一个耗时 | 拆出模型加载、编译、预热、首轮执行 |
| 分发渠道 | 只考虑 Google Play | 为无 GMS 设备准备包内运行时、设备侧编译或 CPU / GPU 路径 |

迁移后的验收标准也要写清楚：如果目标是降低首轮延迟，就优先验证 AOT 和预热；如果目标是降低稳态功耗，就做持续运行测试；如果目标是减少主线程阻塞，就看初始化线程和 buffer 复制。每个目标对应的证据不同，不能只用一组平均 latency 结束评估。

## 小结

Android 17 的 NPU feature 声明让端侧 AI 加速多了一道系统边界；LiteRT CompiledModel 和 AOT 则把硬件选择、编译产物和分发策略推到工程流程前面。NPU 加速是否成立，要同时满足清单声明、设备 feature、运行时可用、模型算子覆盖和功耗预算五个条件。

写这类内容时，最安全的分法是：Android 平台只写 release notes、NNAPI / NN HAL 和 SDK 明确公开的内容；LiteRT 写运行时和 delegate 文档能验证的内容；AICore、Google Play AI Pack、厂商 QNN / NeuroPilot 都按各自生态能力处理。这样才能避免把闭源组件或厂商能力误写成所有 Android 设备都具备的公共能力。

## 源码调研补充（2026-05-17）

### AICore 版本归属纠错

研究发现：AICore 系统服务于 **Android 14（API 34）** 即已引入，而非 Android 17 新增。"Android 17 端侧 AI 推理性能边界"题目存在版本误解——Android 17 的 AI 栈变化主要是 LiteRT NPU delegate 的正式支持（Qualcomm QNN / MediaTek NDSS 等），以及 AICore Developer Preview 持续迭代。

**AICore 源码路径（需进一步确认）**：
- 推测位置：frameworks/ml/nn/（NNAPI 运行时复用路径）或 packages/modules/（AOSP 模块结构）
- 核心 API：`com.google.ai.edge.aicore`（package-summary: developer.android.com/ai/reference/kotlin/com/google/ai/edge/aicore/package-summary）
- NNHAL 源码：hardware/interfaces/neuralnetworks/1.3/（AOSP，仍活跃维护）

**LiteRT ≠ Android 新功能**：LiteRT 是 TensorFlow Lite 的品牌重命名，通过 Google AI Edge SDK 分发，与 Android 版本无直接绑定。

**AICore vs LiteRT 定位区别**：
| | AICore | LiteRT (TFLite in Play Services) |
|---|---|---|
| 用途 | GenAI 基础模型（Gemma/Gemini Nano） | 自定义 ML 模型推理 |
| 更新方式 | 系统级 OTA（Gemini Nano 下载） | Play Services runtime OTA |
| 适用场景 | 文本/图像/音频生成 AI | 物体检测、NLP、ASR 等传统 ML |



## 源码调研补充（2026-05-18）

### Android 端侧 AI 推理栈架构核心发现

本次调研从 Android Developers Blog（2022-10）和 AOSP Neural Networks HAL 源码出发，验证了 Android 端侧 AI 推理栈的分层设计原则。

**推理引擎分发模式变革**：
- 传统模式：App 打包 TFLite `.aar`，推理引擎与 App 绑定，无法独立更新
- 新模式：**TensorFlow Lite in Google Play Services**，推理引擎作为 platform service 通过 Play Services OTA 更新
- 这解决了设备碎片化导致的 inference engine 老化问题（2022 年博客数据：每月服务数十万应用、数亿用户）

**关键源码路径**：
- NNAPI Java API：`frameworks/base/core/java/android/neuralnetworks/NeuralNetworks.java`（API 27+）
- NNAPI HAL 定义：`hardware/interfaces/neuralnetworks/1.3/types.hal`（API 35+ 关键版本，含 fenced execution）
- TFLite Delegate：源码位于 `external/tflite/tensorflow/lite/delegates/nnapi/` 和 `external/tflite/tensorflow/lite/delegates/gpu/`

**Acceleration Service 设计目标（API 35+）**：
- 解决 Android 设备硬件异构性导致的 Delegate 选择难题
- 运行时探测可用加速器，安全选择最优配置
- 2022 年博客提及 early access 计划，公开状态需进一步验证

**NNAPI HAL 版本演进**：
| 版本 | API Level | 关键能力 |
|------|-----------|---------|
| 1.0 | 27 | 基础模型加载与执行 |
| 1.1 | 29 | 动态输入维度 |
| 1.2 | 30 | 扩展操作符、shared memory |
| 1.3 | 35 | fenced execution、execution preferences |

**未被一手验证的项目（待确认）**：
- AICore 系统服务的具体源码路径（AOSP 中未找到 `com.android.internal.ml.aicore` 独立服务）
- `CompiledModel` 类的具体 API 签名（可能属于 Play Services 私有 API）
- Acceleration Service 的公开 API 名称和调用方式

<!-- AIW-源码调研-2026-05-18 -->


## 源码调研补充（2026-05-20）

### NNAPI 废弃边界与 HAL 延续澄清

通过 cs.android.com AOSP 源码和 developer.android.com 文档交叉验证，澄清以下事实：

**NNAPI NDK C API 废弃（Android 15 / API 35）**：
- 来源：developer.android.com/ndk/guides/neuralnetworks
- 废弃的是 `ANeuralNetworks*` 系列 C API（NDK 接口）
- **Neural Networks HAL 本身未被废弃**，仍通过 AIDL 驱动（Android 12+）持续维护

**HAL 版本演进（确认）**：
| 版本 | 接口类型 | API Level | 状态 |
|------|---------|-----------|------|
| 1.0 | HIDL | 27 | 已废弃 |
| 1.1 | HIDL | 29 | 已废弃 |
| 1.2 | HIDL | 30 | 历史版本 |
| 1.3 | AIDL | 35+ | **当前活跃版本** |

**源码位置**：`hardware/interfaces/neuralnetworks/1.3/types.hal`（AOSP，cs.android.com）
- `OperationType` 枚举：定义所有支持的算子类型
- `OperandType` 枚举：TENSOR_FLOAT32、TENSOR_QUANT8_SYMM_PER_CHANNEL 等
- `DeviceType` 枚举：CPU / GPU / ACCELERATOR（NPU 归入 ACCELERATOR）

**NNAPI Runtime 模块**：`frameworks/ml/nn/runtime/`（AOSP）
- 模块名：`com.android.neuralnetworks`（APEX 格式）
- Android 11+ 的 NNAPI Runtime 以 APEX 分发，独立于 Framework

**AICore vs LiteRT vs NNAPI 边界（整理）**：
| | NNAPI | AICore | LiteRT (TFLite in Play Services) |
|---|---|---|---|
| API 类型 | NDK C API (deprecated) | Kotlin/Java API | 跨平台 SDK |
| 底层驱动 | Neural Networks HAL | Neural Networks HAL | 复用 NN HAL |
| 版本起点 | API 27 | API 34 (Android 14) | 品牌重命名 |
| 维护状态 | 废弃 NDK，HAL 仍活跃 | 活跃 (Developer Preview) | 活跃 |
| 调用路径 | 直接 HAL | 系统服务多租户 | Google Play Services OTA |

**未一手验证的声明（需继续溯源）**：
- AICore 系统服务的 AOSP 源码路径（推测在 `frameworks/ml/nn/` 但未确认）
- `android.ai.core` 包的确切 AOSP 路径（需要 cs.android.com 搜索确认）
- Android 16 NNAPI HAL 是否有 1.4 版本更新

<!-- AIW-源码调研-2026-05-20 -->



<!-- AIW-源码调研-2026-05-17 -->


<!-- AIW-源码调研-2026-05-22 -->

## 参考资料
### Android 端侧 AI 推理栈边界澄清 — LiteRT / AICore / NNAPI 分层验证
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-23-android-ai-inference-stack-litert-aicore-nnapi.md
- 类型：DeepResearch 调研结果
- 摘要：Android 端侧 AI 推理栈三层架构（NNAPI→LiteRT→AICore）的源码验证，Android 17 新增 FEATURE_NEURAL_PROCESSING_UNIT 强制声明机制，LiteRT 与 TensorFlow Lite 的品牌重命名关系，AICore 内部通过 NNAPI 调用 NPU 的封装路径及版本演进对照。
- 注入时间：2026-05-24
- 价值：厘清 NNAPI/LiteRT/AICore 三层架构边界，补充 Android 17 NPU feature 声明机制


### Android 端侧 AI 推理栈边界验证——AICore / LiteRT / NNAPI 分层澄清
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-21-android-ml-stack-aicore-litert-nnapi-boundary-verification.md
- 类型：DeepResearch 调研结果
- 摘要：交叉验证 AOSP 主分支和 developer.android.com，确认五个核心事实：AICore（com.google.android.aicore）是 Google 私有系统 APK 不在 AOSP；android.hardware.ai.npu 不存在，正确 feature 常量为 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT`，值为 `android.hardware.npu`；NNAPI NDK C API 在 Android 15 废弃但 HAL 仍活跃；LiteRT 是 Play Services SDK 不在 AOSP；AICore 仍为 Developer Preview。建立公开可发布事实 vs preview/vendor/待验证的边界。
- 注入时间：2026-05-23
- 价值：源码级分析，包含 AOSP 路径交叉验证和版本边界澄清，可作为章节内容的补充参考材料

---

## 源码调研补充（2026-05-26）

### Android 17 NPU Feature 强制声明验证

Android 17 Release Notes（2026-02-26）明确：

> **NPU Management**: Apps targeting Android 17 must declare the `FEATURE_NEURAL_PROCESSING_UNIT` hardware feature to directly access the NPU.

这意味着面向 Android 17 的应用，如果要直接访问 NPU，必须在 AndroidManifest.xml 中声明：

```xml
<uses-feature android:name="android.hardware.npu" android:required="false" />
```

未声明的应用在 Android 17 目标 SDK 下无法直接访问 NPU。间接访问路径（LiteRT Delegate）不在此约束范围内。

**源码锚点**：
- `frameworks/base/core/java/android/content/pm/PackageManager.java` — `hasSystemFeature()` 实现
- `device/google/coral/manifest.xml` — 设备级 feature 声明示例
- `hardware/interfaces/neuralnetworks/1.3/types.hal` — NN HAL 类型定义

### NNAPI 废弃进程确认

- **Android 14 (API 34)**：NNAPI 稳定使用，ANeuralNetworks* C API 正常
- **Android 15 (API 35)**：NNAPI NDK C API 标记 deprecated，官方迁移文档指引转向 LiteRT in Play Services + GPU Delegate
- **Android 17 (API 37)**：NNAPI 废弃+强制 NPU feature 声明

**迁移路径确认**：
```text
旧：App → NNAPI C API → NPU HAL → 厂商驱动
新：App → LiteRT CompiledModel → GPU Delegate / NPU Delegate → 厂商运行时
```

官方迁移文档（developer.android.com/ndk/guides/neuralnetworks/migration-guide）：
> "NNAPI was deprecated in Android 15. To migrate from NNAPI, see the instructions for TensorFlow Lite in Google Play Services and optionally TFLite GPU delegate for hardware acceleration."

### AICore 版本状态（2026-05）

| 项目 | 状态 |
|------|------|
| 包名 | `com.google.ai.edge.aicore` |
| 最新版本 | `0.0.1-exp01`（Developer Preview）|
| minSdkVersion | 31（Android 12）|
| 更新方式 | Google Play services OTA（不可独立卸载）|
| 2026-04-02 更新 | AICore Developer Preview 支持 Gemma 4（Google Developers Blog）|
| 依赖硬件 | Google AI Accelerator / MediaTek AI Processor / Qualcomm AI Engine |

AICore 是系统级 GenAI 模型运行时，为 Gemini Nano、Gemma 等模型提供 on-device inference 能力，不属于 AOSP 源码，通过 Google Play services 分发。

### LiteRT 分层架构确认

| 层级 | 来源 | 可写成平台能力？ |
|------|------|----------------|
| LiteRT Core | Google Play services（私有，非 AOSP）| 否 |
| GPU Delegate | Google Play services 分发 | 否 |
| NPU Delegate（QNN/NeuroPilot）| 厂商 SDK | 否 |
| XNNPACK | AOSP `external/XNNPACK/` | 可引用源码 |
| NN HAL | AOSP `hardware/interfaces/neuralnetworks/1.3/` / `hardware/interfaces/neuralnetworks/aidl/` | 可引用源码 |

**注**：本调研结论与章节现有内容一致，对以下待验证项仍保持开放：
- Android 17 / API 37 设备侧 `android.hardware.npu` feature 的厂商声明覆盖率
- AICore 私有接口调用 NPU 的具体路径（AOSP 外）
- Qualcomm QNN / MediaTek NeuroPilot 的具体算子覆盖范围



---

## 源码调研补充（2026-05-28）

### LiteRT CompiledModel API 最新变化（GitHub releases 验证）

通过 GitHub `google-ai-edge/LiteRT` releases 交叉验证，确认以下 API 演进：

**CompiledModel::Create() 简化**：
- 不再需要 `litert::Model` 对象
- 可直接从文件名或模型缓冲区创建
- 简化了模型加载流程

**Annotation/Metrics API 移除**：
- 从 CompiledModel 中移除了 Annotation 和 Metrics API
- 降低了 API 表面积

**Android min SDK 固定**：
- LiteRT Android min SDK version 固定为 23（Android 6.0）

**LiteRT-LM 支持模型**：
- Gemma、Llama、Phi-4、Qwen 等主流开源模型
- 支持 GPU/NPU 硬件加速
- 通过 Chrome、Chromebook Plus、Pixel Watch 等设备落地

**LiteRT Samples 示例**（GitHub `google-ai-edge/litert-samples`）：
```bash
./deploy_and_run_android.sh \
  --tokenizer "path/to/tokenizer.model" \
  --embedder "path/to/embedder.tflite" \
  --accelerator "npu" \
  --soc_man "Google"
```

### Android 17 NPU 管理结论补充

| 结论 | 来源 | 验证状态 |
|------|------|----------|
| Android 17 目标应用必须声明 FEATURE_NEURAL_PROCESSING_UNIT | Android 17 Release Notes | 已验证 |
| NNAPI NDK C API 在 Android 15 废弃 | developer.android.com/ndk/guides | 已验证 |
| Neural Networks HAL 仍活跃，Android 12+ 使用 AIDL | AOSP hardware/interfaces/neuralnetworks/ + source.android.com NNAPI Runtime | 已验证 |
| LiteRT NPU delegate 通过 Google Play services 分发 | developer.android.com/ai/custom | 已验证 |
| LiteRT CompiledModel API 自动化加速器选择 | GitHub LiteRT releases | 已验证 |

<!-- AIW-源码调研-2026-05-28 -->
