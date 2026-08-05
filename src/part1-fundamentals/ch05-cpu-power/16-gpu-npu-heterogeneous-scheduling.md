---
title: "GPU/NPU 异构负载调度与功耗归因"
chapter: "5.16"
section: "5.16"
status: finalized
drafted_date: "2026-05-22"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-22"
last_verified_against: "AOSP android-17.0.0_r1 + Android 官方文档 + LiteRT docs + Perfetto docs"
confidence: medium
tags: "[gpu, npu, heterogeneous-compute, adpf, thermal, power, litert]"
related_chapters: "[\"5.3\", \"5.4\", \"5.9\", \"5.11\", \"5.12\", \"5.13\", \"5.14\", \"17.2\", \"22.10\", \"25.11\"]"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "章节深挖/素材驱动/官方文档"
gap_score: 16
material_count: 6
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/performance-hint-api"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf"
  - type: official
    path: "https://developer.android.com/ndk/guides/neuralnetworks/migration-guide"
  - type: official
    path: "https://source.android.com/docs/core/interaction/neural-networks/device-discovery"
  - type: official
    path: "https://ai.google.dev/edge/litert/overview"
  - type: official
    path: "https://ai.google.dev/edge/litert/android/npu/overview"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-freq"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/battery-counters"
  - type: official
    path: "https://developer.android.com/reference/android/content/pm/PackageManager#FEATURE_NEURAL_PROCESSING_UNIT"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: research
    path: "DeepResearch/2026-05-20-android-17-npu-aicore-nnapi-research.md"
  - type: research
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-adpf-non-game-scenarios-and-profiling-trigger-type-anomaly.md"
reviewed_date: '2026-06-04'
reviewed_by: "openclaw-task6"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
pipeline_stage: ready-to-publish
last_task6_at: '2026-06-04T22:12:00+08:00'
last_task6_review_log: "logs/review/2026-05-22-01-review.md"
task9_result: auto-fixed
task9_reviewed_date: "2026-06-04"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-06-04T18:15:00+08:00"
last_task9_review_log: "logs/deep-review/2026-06-04-18-deep-review.md"
task2b_state: fixed
task2b_result: fixed-lite
p0: 1
p1: 0
p2: 0
task9_review_notes: "2026-06-04 Task9 18: auto-fixed。P0 1:Android 17 NPU feature 边界由旧 `android.hardware.neural_processing_unit`/未公开改为 API 37 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT`、常量值 `android.hardware.npu`;同时保留 delegate/AICore/配额外推边界。回到 Task6 复审。"
last_task2b_lite_at: 2026-06-04
last_task9_autofix_at: "2026-06-04"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-04
last_task6_audit: "2026-07-16T21:17:00+08:00"
---

# 5.16 GPU/NPU 异构负载调度与功耗归因

<!-- outline-start -->
## 要点

### 🔹 异构负载不等于 CPU 空闲
说明 GPU/NPU 卸载后,CPU 仍负责输入预处理、buffer 搬运、delegate 调度、结果后处理和 UI 合成;性能归因要看端到端路径,而不是只看加速器子图耗时。

### 🔹 GPU、NPU、CPU 三类路径的适用边界
对比渲染类 GPU 负载、ML delegate / LiteRT NPU 负载、CPU fallback 的典型收益和代价,明确算子覆盖率、内存布局、同步等待和热状态对结果的影响。

### 🔹 ADPF 能表达线程工作量,不能直接控制加速器
梳理 `PerformanceHintManager.Session`、Power HAL、thermal headroom 与 GPU/NPU 频率之间的关系,避免把 ADPF 写成应用侧绑核、调频或 NPU 调度 API。

### 🔹 Perfetto 与厂商工具的观测分层
建立观测清单:CPU sched/freq、GPU frequency/counters、thermal status、power rails、FrameTimeline、delegate 日志和厂商 NPU trace;说明普通发布版设备上哪些信号可能不可见。

### 🔹 持续推理和前台交互的资源竞争
覆盖相机预览、实时翻译、AI 修图、游戏 AI 辅助等场景中,NPU/GPU 持续工作如何影响帧预算、温控和后台任务,交叉引用 5.13、22.10、25.11。

### 🔹 Android 17 NPU feature 与 LiteRT 迁移后的新边界
把 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT` / `android.hardware.npu`、LiteRT `CompiledModel`、NNAPI deprecated、厂商 delegate 与 AICore 生态能力拆开,形成可发布事实表。

## 扩展

### 🔸 GPU/NPU 与 EAS / devfreq cooling 的交互
从调度器、devfreq cooling、thermal governor 角度说明 CPU 线程迁移、GPU/NPU 降频和功耗预算共享的分析方法。

### 🔸 端侧 AI 性能实验模板
给出同机型 CPU / GPU / NPU 对照、冷启动 / 稳态、p50 / p90 / p99、功耗与温度的实验字段清单。

### 🔸 厂商 SoC 差异与可迁移结论
整理 Qualcomm、MediaTek、Tensor 等平台的公开能力边界,避免把单个平台的 delegate 行为写成 Android 通用结论。

<!-- outline-end -->
把模型交给 GPU 或 NPU，只改变了其中一段计算由谁执行。输入解码、张量转换、命令提交、同步等待、结果后处理和画面合成仍可能落在 CPU、GPU 与内存子系统上。因此，异构计算的优化目标应写成一条完整的链路：

> 在满足正确性与质量要求的前提下，让端到端延迟、尾延迟、能耗和热稳定性同时符合产品预算。

本节以 Android 17 / API 37 / `android-17.0.0_r1` 为平台基线，以 `android17-6.18-2026-06_r6` 为内核基线，说明怎样拆开这条链路、怎样理解各层调度，以及怎样为性能结论找到足够的证据。ADPF 的基础用法见 5.9，持续推理与热管理分别见 5.13 和 5.12，Android 17 的 NPU 接口边界见 5.14。

## 先把一次异构任务拆成阶段

“NPU 推理耗时 8 ms”不能代表用户等待 8 ms。一次相机识别、图像增强或模型推理通常包括以下阶段：

| 阶段 | 常见执行方 | 主要成本 | 建议观测 |
|---|---|---|---|
| 输入获取 | Camera、文件系统、CPU | 等帧、解码、裁剪 | Camera 时间戳、自定义 trace slice |
| 输入准备 | CPU、GPU、内存 | 格式转换、归一化、张量排布、拷贝 | CPU 调度、slice、分配与 DMA-BUF |
| 图划分与编译 | LiteRT、delegate、厂商编译器 | 算子划分、AOT/JIT 编译、缓存加载 | runtime 日志、首次运行时间 |
| 命令提交 | CPU、驱动 | buffer 绑定、队列提交、Binder 或 ioctl | 线程 slice、阻塞栈、驱动事件 |
| 加速器执行 | GPU、NPU、DSP | kernel 或子图执行 | GPU 事件、厂商 NPU trace |
| 同步与回读 | CPU、驱动、内存 | fence 等待、cache 一致性、结果拷贝 | 线程状态、fence、DMA-BUF |
| 后处理与呈现 | CPU、GPU、显示系统 | 解码输出、业务逻辑、RenderThread、合成 | FrameTimeline、SurfaceFlinger |

假设加速器执行从 30 ms 降到 10 ms，而输入准备、同步和后处理合计仍为 18 ms，用户可见延迟只会从约 48 ms 降到约 28 ms。若优化同时引入额外的布局转换或读回，收益还会继续缩小。

应用应为各阶段添加稳定的 trace 名称，例如 `ml/preprocess`、`ml/compile`、`ml/invoke` 和 `ml/postprocess`。名称要对应可解释的边界，避免用一个 `inference` slice 包住整条路径。只有拆开阶段，才能回答线程是在计算、排队、等待 fence，还是被温控压低了运行速度。

## CPU、GPU 与 NPU 的选择依据

三类执行路径可以同时出现在一次推理中。模型的某些子图由 NPU 执行，不支持的算子回到 GPU 或 CPU；输出又可能由 GPU 直接消费。因而，“使用了 NPU”只是运行时决策的一部分。

| 路径 | 常见优势 | 常见代价 | 适合作为判断依据的证据 |
|---|---|---|---|
| CPU | 覆盖完整、启动成本低、便于调试 | 持续负载可能有较高能耗和热压力 | 线程 CPU time、频率、调度延迟 |
| GPU | 并行吞吐高，可与图像处理衔接 | 可能与 UI 渲染争用 GPU 和带宽 | GPU queue、频率、counter、FrameTimeline |
| NPU | 对受支持模型可提供较好的能效 | 覆盖、编译、工具和驱动差异大 | delegate 报告、编译结果、厂商 NPU trace |

CPU 路径应始终作为基线保留。小模型、短序列或低频任务中，delegate 初始化、编译和数据转换可能比加速器节省的执行时间更长。CPU 基线还能暴露两类问题：模型本身发生了变化，以及所谓 NPU 结果中混入了大比例 CPU fallback。

GPU 适合并行度较高、布局匹配的张量计算，也常负责图像预处理和结果渲染。计算与 UI 若共用同一 GPU，推理吞吐上升可能伴随渲染排队和掉帧。此时只看模型 latency 会得到错误方向，必须把 GPU 队列与 FrameTimeline 放在同一时间轴上。

NPU 的收益取决于模型、精度、形状、算子覆盖、编译方式、驱动和 SoC。Android 17 提供 NPU 能力声明与调度接口，但没有规定所有设备必须支持相同算子或达到相同性能。工程报告必须绑定机型、SoC、系统构建、runtime、delegate、模型和精度。

### Fallback 与部分委派需要单独计量

LiteRT `CompiledModel` 支持为 NPU 不可用或子图不受支持的情况指定 GPU、CPU fallback。当前官方 NPU 文档也说明，部分委派时未被 NPU 接收的子图可以在所选的 GPU 或 CPU 后端执行。这个能力提高了兼容性，也会让“调用成功”失去归因价值。

至少记录以下信息：

- 加速器候选顺序；
- 是否允许 fallback；
- 被委派的子图和算子比例；
- 编译、首次运行和稳态运行时间；
- fallback 阶段的执行方；
- 输出误差与质量检查结果。

算子数量占比也不能代替耗时占比。一个未委派的算子可能很少，却造成大张量回到 CPU、两次格式转换和一次同步等待。端到端 trace 与 runtime 报告需要一起看。

### AOT、JIT 与运行时分发是不同变量

NPU 模型可采用预编译的 AOT 产物，也可在设备上 JIT 编译。AOT 能减少设备端编译工作，但产物与芯片、编译器版本和兼容性范围相关；JIT 更容易适配当前设备，却会增加首次运行成本和缓存管理变量。

LiteRT 当前公开资料还显示，不同芯片系列支持的模式并不一致。例如当前 Google Tensor 路径以 AOT 为主，Qualcomm 与 MediaTek 的公开路径包含 AOT 和 JIT。这里的“当前”绑定文档版本，不能扩展成 Android 17 的平台承诺。

测试时应把以下时间分开：

1. runtime 与 delegate 初始化；
2. 模型加载或编译缓存读取；
3. 首次编译；
4. 首次推理；
5. 缓存命中后的稳态推理。

把首次编译混入稳态 p50，或只删除应用缓存却保留厂商编译缓存，都会破坏对照实验。

## 数据搬运与同步常常决定端到端收益

异构系统中，计算单元之间通过共享内存、专用内存、IOMMU 映射和驱动队列交换数据。每一次格式转换、CPU 读回和同步都可能抵消硬件执行收益。

`AHardwareBuffer` 可以作为跨 Camera、GPU、NPU 和显示路径共享数据的载体。LiteRT 的 NPU 文档给出了从 `AHardwareBuffer` 创建张量缓冲区的零拷贝示例。不过，使用这个类型只满足了共享的一个条件。端到端是否省去拷贝，还取决于：

- producer 与 consumer 是否都能导入该格式和 usage；
- 张量的形状、stride、对齐和量化布局是否兼容；
- runtime 是否插入转换或 staging buffer；
- cache 一致性和同步 fence 是否正确；
- CPU 是否又把结果读回普通数组。

“代码中出现 `AHardwareBuffer`”不能直接写成“实现了零拷贝”。可验证的方法是比较 DMA-BUF 分配、buffer 生命周期、CPU memcpy slice、驱动导入记录和端到端时间。若工具无法看到设备内部拷贝，应把结论限定为“应用侧避免了显式拷贝”。

同步也要计入预算。CPU 线程阻塞在 fence 或驱动调用中时，CPU 使用率可能下降，但用户等待时间没有消失。GPU/NPU 利用率很高也可能只是队列拥堵。判断时至少区分：

- producer 尚未完成，consumer 等输入；
- 加速器队列已有前序任务；
- 硬件执行时间较长；
- 结果已完成，CPU 回调迟迟未被调度；
- CPU 读回触发了额外同步或 cache 维护。

## Android 17 的调度与调频分属多层

异构任务没有一个统一的 Android 调度器。CPU 线程、GPU 命令和 NPU 工作分别进入不同控制面，最终通过内存带宽、电源域和热预算相互影响。

```text
应用 / LiteRT
  ├─ CPU 线程 ── Linux scheduler ── EAS 放置 ── schedutil / CPUFreq
  ├─ GPU 命令 ── 图形或计算 runtime ── GPU driver ── devfreq / 厂商策略
  └─ NPU 子图 ── LiteRT / 编译产物 ── NPU driver
                                      └─ Android 17 NPU scheduling HAL（UID 级提示）

Thermal HAL / thermal framework / 厂商热策略
  └─ 对 CPU、GPU、NPU、内存等可用性能施加设备相关限制
```

这张关系图用于确定归因层级，不表示每台设备都使用同一 GPU governor、同一 NPU 驱动或同一 cooling device。

### EAS 选择 CPU，schedutil 计算 CPU 频率

在 `android17-6.18-2026-06_r6` 中，`kernel/sched/fair.c` 的 `find_energy_efficient_cpu()` 为唤醒任务挑选候选 CPU，并调用 `compute_energy()` 借助 Energy Model 比较任务放到不同 CPU 后的能耗增量。这是 CPU 任务放置逻辑。

CPU 频率请求位于另一条路径。`kernel/sched/cpufreq_schedutil.c` 的 `get_next_freq()` 根据利用率和容量计算候选频率，再交由 CPUFreq policy 与驱动约束。Android common kernel 在这里还保留了 `trace_android_vh_map_util_freq` 厂商 hook。由此可以得到两个明确结论：

- 线程迁移到哪颗 CPU 与该 CPU policy 选择什么频率需要分别分析；
- 平台源码给出的算法边界不等于具体设备没有厂商调节。

所以，“EAS 把 GPU/NPU 升频”在机制上不成立。EAS 只处理 CPU 调度实体，GPU/NPU 的变化属于其他控制路径。

### GPU 常见 devfreq 路径仍是设备实现

Linux devfreq 为非 CPU 设备提供频率管理框架，`drivers/devfreq/` 包含 governor 与设备注册逻辑。`drivers/thermal/devfreq_cooling.c` 可以把 devfreq 设备注册成 thermal cooling device，并通过 cooling state 限制可用性能状态。

这段通用源码说明内核具备相应框架，不能据此认定某台 Android 设备的 GPU 或 NPU 一定接入了通用 devfreq cooling。移动 GPU 驱动、利用率采样、频点决策和热限制经常含有厂商实现。设备树、驱动源码、trace 事件或厂商文档至少要提供一项证据，才能写具体 governor 名称和控制关系。

### Android 17 NPU scheduling HAL 管理 UID 级策略

Android 17 的 `android.hardware.npu.IScheduling` 用于把 UID 的优先级与访问配置传给 NPU。接口说明要求 NPU尽力遵循优先级，数值越小优先级越高；硬件能力不同，执行细节也可以不同。`SchedulingConfig` 包含：

- `uid`；
- `priority`；
- `hasDirectAccess`；
- `canAttributeOtherUid`。

它不是模型图执行接口，也没有向普通应用提供 NPU 频点、核心选择或队列时隙控制。应用的模型仍通过 LiteRT、厂商 runtime 或其他上层服务执行。Android 17 新增的是系统与 NPU 之间的调度和访问边界。

## ADPF 能帮助 CPU 关键线程，不能代替加速器调度

`PerformanceHintManager.Session` 把一组相关线程及其周期性工作描述给系统。应用提供目标工作时长，并持续报告实际工作时长，系统再结合设备策略调整这些 CPU 线程的核心放置和频率。它适合输入准备、命令提交、游戏主循环、RenderThread 邻近任务等有明确周期的 CPU 关键路径。

Android 17 平台源码中的 Java 常规接口包括：

- `createHintSession()`；
- `updateTargetWorkDuration(long)`；
- `reportActualWorkDuration(long)`；
- `setThreads(int[])`；
- `close()`。

`setPreferPowerEfficiency(boolean)` 与接收 `WorkDuration` 的重载受 feature flag 控制。`WorkDuration` 可报告总时长以及 CPU、GPU 时长组成。源码要求起始时间和总时长大于零，CPU/GPU 时长不能为负，并且两者至少有一个大于零。

边界还要再限制加强一层：Java 中的 `CPU_LOAD_*`、`GPU_LOAD_*` 常量和 `sendHint()` 标为 `@TestApi` / `@hide`，普通应用不应把它们当成稳定公开 SDK。Android 17 NDK 头文件则公开了更完整的原生接口：

- API 35 的 `APerformanceHint_reportActualWorkDuration2()`；
- API 36 的 `APerformanceHint_notifyWorkloadIncrease()`；
- API 36 的 `APerformanceHint_notifyWorkloadReset()`；
- API 36 的 `APerformanceHint_notifyWorkloadSpike()`。

这些 workload-change hint 用于即将发生的一次变化，应在变化前或周期早期发送，受支持检查与频率限制约束；持续高负载仍应靠周期时长报告。它们表达 CPU、GPU 工作组成和变化，不授予应用 GPU/NPU 调频权。

对 NPU 推理尤其要注意：NPU 执行期间，hint session 中的 CPU 线程可能在睡眠。系统从线程时长报告中无法推导 NPU 队列深度、算子覆盖率或所需频点。ADPF 可以改善喂数、提交和后处理线程的 CPU 资源决策，却不能证明 NPU 已升频或获得更高优先级。

## Android 17 NPU feature 的准确含义

Android 17 / API 37 的 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT` 常量值为 `android.hardware.npu`。它表示设备具备 NPU 或用于 AI 加速的类似硬件。需要直接访问 NPU 且 targetSdk 为 37 或更高的应用，应在 manifest 中声明该 feature。

声明方式如下；若应用允许安装到没有这项能力的设备，应按产品的 fallback 策略决定 `required`：

```xml
<uses-feature
    android:name="android.hardware.npu"
    android:required="false" />
```

`required="false"` 只影响安装筛选，不会创造 NPU 能力。运行时仍需调用 `hasSystemFeature(PackageManager.FEATURE_NEURAL_PROCESSING_UNIT)`，并处理 runtime 初始化、编译或执行失败。

AOSP 的 `packages/modules/NpuManager` 进一步给出直接访问规则：`PriorityManager` 为 targetSdk 37 及以上的包检查该 feature；在对应 flag 启用时，缺少声明会把 `SchedulingConfig.hasDirectAccess` 设为 `false`。这条规则针对直接 NPU 访问。应用通过系统中间服务请求 AI 能力时，应按该服务的公开契约判断，不能把直接访问规则照搬过去。

还要区分三组接口：

| 接口 | 职责 | 应用侧含义 |
|---|---|---|
| `android.hardware.npu.IScheduling` | UID 优先级、直接访问和归因配置 | 系统到 NPU 的调度控制面 |
| Neural Networks HAL | NNAPI 设备发现与执行接口 | NNAPI NDK 已弃用不代表 HAL 立即消失 |
| LiteRT `CompiledModel` / delegate | 模型编译、后端选择、执行与 fallback | 应用选择当前推荐运行时路径 |

`NpuManager` 本身是受 flag 控制的 `@SystemApi`，不能作为普通第三方应用的通用推理入口。更多源码关系与迁移策略见 5.14。

## 持续推理会争用整机资源

相机实时翻译、实时抠图、游戏 AI 与屏幕内容理解有一个共同特点：推理和前台交互长期并行。即使 NPU 使用独立计算单元，它仍会消耗电池、内存带宽和散热能力；具体 SoC 还可能共享电源域、缓存或互连。

以相机实时翻译为例，可以拆成三条相互依赖的路径：

1. Camera HAL 产生图像 buffer；
2. runtime 完成 OCR 或翻译；
3. UI 将结果叠加到预览画面。

若模型每帧都运行，单次推理虽能满足帧周期，持续功耗仍可能让设备进入 thermal throttling。此后模型 latency、相机帧率与 UI 流畅度可能同时恶化。优化时可以选择降低推理频率、复用跟踪结果、减小输入、换轻量模型，或在热余量不足时降低功能质量等级。

游戏场景还要同时考虑游戏主线程、RenderThread、GPU 渲染、音频和网络。GPU delegate 可能直接挤占渲染队列；NPU 也会占用整机功耗和带宽预算。任何“额外计算单元等同于免费算力”的假设都必须用同机 trace 和长时实验验证。

前台服务、后台调度和进程优先级只决定一部分资源条件。WorkManager 可以约束任务何时运行，却不能为持续 NPU 工作保留热预算。产品层需要明确降级顺序，例如：

1. 降低低优先级推理频率；
2. 减小输入或 batch；
3. 切换低成本模型；
4. 延后非交互任务；
5. 在达到安全阈值时暂停相关能力。

降级条件应使用 Thermal API、端到端延迟与掉帧等可观测指标，避免仅凭一次温度读数决策。

## 观测要分成四层

Android 发布版设备对 GPU/NPU 的可见性差异很大。建议按层收集证据：

| 层级 | 可观测内容 | 能回答的问题 | 主要限制 |
|---|---|---|---|
| 应用层 | 自定义 slice、端到端 latency、质量、失败码 | 哪个业务阶段变慢 | 看不到驱动内部排队 |
| runtime 层 | delegate、编译、子图和 fallback 日志 | 模型被怎样划分 | 日志粒度和格式随版本变化 |
| Android 通用层 | sched、CPU freq、FrameTimeline、thermal、battery | CPU、交互和整机状态怎样变化 | NPU 内部通常不可见 |
| 设备扩展层 | GPU counter、power rail、NPU trace、厂商 profiler | 加速器执行和设备功耗细节 | 权限、命名和覆盖不统一 |

证据不足时，应缩小结论范围：

- 没有 NPU 轨道，只能说当前 trace 未暴露 NPU 内部活动；
- delegate 报告 NPU 成功，只能证明运行时选择，不能证明整图都在 NPU；
- GPU 频率升高只能证明频率变化，需结合 queue/counter 才能归因到模型；
- rail 名称含有 `NPU` 也要核对厂商定义，可能包含互连或共享电源域。

### Perfetto 的基础采集

CPU 频率事件只在频率变化时产生，而且 Perfetto 不记录 trace 开始前的初始频率。为避免短 trace 开头出现空白，应同时启用 ftrace 事件和周期轮询：

```textproto
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
    }
  }
}
data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config { cpufreq_period_ms: 500 }
  }
}
```

这份配置用于建立 CPU 基线。真实实验还要加入应用 atrace、FrameTimeline、进程统计和设备支持的数据源，并控制采样开销。

GPU frequency 可通过设备支持的 `power/gpu_frequency` 等事件采集，GPU counter、render stage 和 NPU 轨道则取决于驱动、权限和工具。先用 `perfetto --query-raw`、数据源列表或一段试采确认能力，不要把空轨道当成工作负载为空。

### 电池计数器与 power rail 的口径

Perfetto 的 `android.power` 可采集电池电量、charge、电流和电压。电池计数器表示整机电池侧数据，包含 SoC、屏幕、基带和其他部件；USB 充电会改变电流方向与读数，因此充电状态必须写入实验条件。

设备若提供 On-Device Power Rail Monitor，Perfetto 可通过 `IPowerStats` 读取 power rails。官方文档明确指出，这类硬件在很多量产手机上仍不可用，rail 的存在、分辨率和命名由厂商决定。它适合同一设备、相同条件下的差分比较，不适合未经校准的跨机型绝对比较。

温度也不能替代能量。温升受到环境温度、机身材料、散热路径和先前负载影响；短时间内功耗升高时，传感器温度可能尚未响应。应并列报告能量、温度、thermal status、频率与性能。

## 常见症状怎样逐层定位

| 症状 | 先查什么 | 可能原因 | 后续验证 |
|---|---|---|---|
| 加速器时间下降，端到端变化很小 | 阶段 slice | 预处理、拷贝、同步占比上升 | 检查布局和 buffer 路径 |
| NPU 模式 CPU 仍很忙 | runtime 日志与 CPU stack | fallback、预处理、轮询等待 | 关闭 fallback 对照，核对子图 |
| GPU 推理快但 UI 掉帧 | GPU queue 与 FrameTimeline | 推理和渲染争用 GPU | 降推理频率或错开提交 |
| 冷启动慢，稳态正常 | 编译与缓存阶段 | JIT、delegate 初始化 | 分离首次编译和缓存命中 |
| 运行一段时间后全线变慢 | thermal、频率、功耗 | 热限制或整机预算耗尽 | 控制起始温度并延长实验 |
| trace 中没有 NPU 活动 | 数据源与 runtime 报告 | 设备未暴露轨道或没有走 NPU | 用厂商工具或对照实验 |
| CPU 线程等待且 GPU 频率不高 | fence、队列、counter | 短任务策略、依赖未满足 | 延长 slice、核对 producer |

表中的“可能原因”只用于安排验证顺序。一次 trace 里的时间相关性不能单独证明因果关系。最可靠的办法是每次只改变一个变量，并观察对应阶段和系统信号是否按预期变化。

## 可复核的实验设计

### 固定环境

每组结果至少记录：

- 机型、SoC、RAM 与系统 build fingerprint；
- Android 版本与内核版本；
- 应用、LiteRT、delegate、驱动可见版本；
- 模型哈希、输入尺寸、batch、精度与量化方式；
- 电量、是否充电、环境温度和起始设备温度；
- 屏幕亮度、刷新率、网络和相机状态；
- 电源模式、Thermal 状态与后台负载。

若设备无法读取驱动或 delegate 版本，就明确写“不可见”，不要用系统版本代替。

### 建立对照组

至少比较 CPU、GPU 和 NPU 候选路径；设备不支持其中一条时，记录探测结果与失败方式。每组都要明确是否允许 fallback。为了定位拷贝成本，还可以增加保留同一执行后端、只改变 buffer 路径的对照。

冷启动与稳态需要分组统计。测试持续到性能、温度或 thermal status 呈现稳定趋势；达到这一条件所需时间由设备和负载决定，不宜预设统一的“一分钟稳态”。对持续功能，还应覆盖热限制后的长期窗口。

### 指标要覆盖性能、质量和能量

建议报告：

- 初始化、编译、首次推理；
- 端到端和各阶段 p50、p90、p99；
- 吞吐、超时、失败与 fallback 次数；
- 输出精度或产品质量指标；
- CPU time、GPU/NPU 可见忙时与内存峰值；
- 单次或单位工作量能量；
- 温度、thermal status 和频率变化；
- FrameTimeline jank、相机丢帧等用户可见影响。

平均值可以保留，但不能取代尾延迟和失败样本。每个能耗数字要说明积分窗口及其包含的业务阶段；只量加速器执行段与量完整交互流程回答的是两个问题。

### 结论要绑定适用范围

可以跨 SoC 迁移的是拆段方法、对照原则和证据层级。具体 latency、能效、算子覆盖、频点与热行为都依赖设备实现。发布结论时用下面的句式限定范围：

> 在设备 A、系统构建 B、runtime C、模型 D 和测试条件 E 下，NPU 候选路径相对 CPU 基线把端到端 p90 从 X 降到 Y；runtime 报告委派比例为 Z，单位任务能量变化为 W。

这种表述允许读者复核，也给后续系统、驱动或模型升级留下重新测试的位置。

## 源码核对索引

本节的平台判断以以下 Android 17 与内核 6.18 源码为准：

- `frameworks/base/core/java/android/os/PerformanceHintManager.java`
  - Java hint session、`WorkDuration`、flagged API 与 `@TestApi` 边界。
- `frameworks/native/include/android/performance_hint.h`
  - NDK API level、工作时长约束和 workload-change hint。
- `frameworks/base/core/java/android/content/pm/PackageManager.java`
  - `FEATURE_NEURAL_PROCESSING_UNIT = "android.hardware.npu"`。
- `packages/modules/NpuManager/service/.../PriorityManager.java`
  - targetSdk 37、feature 声明与 `hasDirectAccess` 的关系。
- `hardware/interfaces/npu/aidl/android/hardware/npu/IScheduling.aidl`
  - NPU UID 优先级的 best-effort 语义。
- `hardware/interfaces/npu/aidl/android/hardware/npu/SchedulingConfig.aidl`
  - UID、priority、direct access 与 attribution 字段。
- `kernel/sched/fair.c`
  - `find_energy_efficient_cpu()` 和 `compute_energy()`。
- `kernel/sched/cpufreq_schedutil.c`
  - `get_next_freq()`、`map_util_freq()` 与厂商 hook。
- `drivers/thermal/devfreq_cooling.c`
  - devfreq cooling device 的状态与功率接口。

## References

- [AOSP Android 17 `PerformanceHintManager`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)
- [AOSP Android 17 NDK Performance Hint API](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/include/android/performance_hint.h)
- [Android Performance Hint API](https://source.android.com/docs/core/perf/performance-hint-api)
- [AOSP Android 17 NPU scheduling AIDL](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/npu/aidl/android/hardware/npu/)
- [Android 17 changes summary](https://developer.android.com/about/versions/17/summary)
- [NNAPI migration guide](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)
- [LiteRT NPU acceleration](https://developers.google.com/edge/litert/next/npu)
- [Perfetto CPU frequency and idle states](https://perfetto.dev/docs/data-sources/cpu-freq)
- [Perfetto GPU data sources](https://perfetto.dev/docs/data-sources/gpu)
- [Perfetto power data sources](https://perfetto.dev/docs/data-sources/battery-counters)
- [Android common kernel 6.18 EAS](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [Android common kernel 6.18 schedutil](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)
- [Android common kernel 6.18 devfreq cooling](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/thermal/devfreq_cooling.c)
