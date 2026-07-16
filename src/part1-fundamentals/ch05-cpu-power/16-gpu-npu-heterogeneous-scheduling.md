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
说明 GPU/NPU 卸载后,CPU 仍承担输入预处理、buffer 搬运、delegate 调度、结果后处理和 UI 合成;性能归因要看端到端路径,而不是只看加速器子图耗时。

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

把推理任务交给 GPU 或 NPU 之后，CPU 就闲下来了吗？实际并非如此——CPU 仍然要准备输入数据、提交加速器命令、等结果回来、做后处理，最后把结果合进 UI。把关注点从"加速器跑得快不快"转向"端到端路径哪里在等、谁在耗电、哪个信号可验证"，是本节要建立的视角。

5.3、5.9、5.11、5.12 和 5.13 已经分别讲过大小核、ADPF、端侧 AI、Thermal 和 LLM 推理。这里只补异构负载的归因方法:同一个 trace 里同时出现 CPU 等待、GPU 频率抬升、NPU delegate 日志和 thermal 降级时,怎么把它们放进同一个判断框架。

## 异构卸载后的 CPU 仍在路径上

"模型跑到 NPU 了"只说明某些算子子图被 delegate 接走。一次推理或图像处理仍包含多段 CPU 工作:输入解码、tensor 排布转换、buffer 生命周期管理、delegate 调用、同步等待、后处理、UI 层提交。只看加速器执行时长,很容易把 CPU 的准备成本和等待成本漏掉。

典型路径可以拆成五段:

| 阶段 | 主要执行对象 | 常见成本 | Trace 观察点 |
|---|---|---|---|
| 输入准备 | CPU / 内存 | 图片解码、裁剪、归一化、tensor copy | App 自定义 slice、CPU sched、内存分配 |
| Delegate 分配 | LiteRT / TFLite runtime | 算子划分、buffer 绑定、fallback 决策 | delegate 日志、native slice、线程唤醒 |
| 加速器执行 | GPU / NPU / DSP | kernel 或 driver queue 执行、硬件等待 | GPU counters、厂商 NPU trace、thermal 状态 |
| 同步与回读 | CPU + driver | fence 等待、结果拷贝、cache 同步 | blocked thread、futex、binder、driver ioctl |
| 结果消费 | CPU / GPU / UI pipeline | 后处理、RenderThread、SurfaceFlinger 合成 | FrameTimeline、RenderThread、SurfaceFlinger |

这张表的用法是先定边界,再看证据。若推理本体从 40ms 降到 12ms,但输入准备和回读各占 8ms,端到端延迟不会按 40→12 的比例下降。若推理结果要马上进入 Compose 或 View 绘制,RenderThread 和 SurfaceFlinger 还会把图形路径重新拉回性能预算内。渲染侧证据详见 22.10 节,LLM 推理的 TTFT / TPOT 口径详见 5.13 节。

[已验证: 官方文档, developer.android.com/ndk/guides/neuralnetworks][已验证: 官方文档, ai.google.dev/edge/litert/overview]

## CPU、GPU、NPU 三类执行路径的边界

CPU 路径胜在可预测和可观测。它适合小模型、短 batch、算子覆盖复杂或 delegate 初始化成本高的场景。代价是持续运行时功耗和热压力更容易压到整机预算上,后台任务也会和 UI 线程争用调度资源。

GPU 路径适合并行度较高、内存访问规律清楚的张量计算,也适合图像处理和渲染前后的计算任务。Android 上公开的 LiteRT / TFLite GPU 文档主要围绕 OpenCL / OpenGL ES delegate 展开;把它直接写成"Vulkan 默认路径"会越过公开文档边界。GPU 路径的风险来自同步等待、纹理或 buffer 布局转换,以及和 UI 渲染抢同一块 GPU / 内存带宽预算。

NPU 路径适合被厂商 delegate 覆盖的模型子图,尤其是卷积、张量乘加、量化模型等硬件友好的工作负载。Android 的 NNAPI device discovery 文档把 `ACCELERATOR` 定义为专用 NPU,设备能力通过 NN HAL 暴露;但应用层能否用上 NPU,取决于 runtime、delegate、模型算子、厂商驱动和设备分发状态。NPU 不可见时,不要把 CPU 降低当成"必然走了 NPU",还要看 delegate 日志、厂商 trace 或同机型对照实验。

| 执行路径 | 适合场景 | 主要代价 | 工程判断 |
|---|---|---|---|
| CPU | 小模型、fallback、复杂控制流、调试基线 | 功耗高,持续负载易触发温控 | 作为基线必须保留,便于验证 delegate 收益 |
| GPU | 图像处理、并行 tensor、渲染邻近任务 | 与 UI 渲染共享 GPU 和内存带宽 | 同时看 GPU 频率、FrameTimeline 和同步等待 |
| NPU | 厂商 delegate 覆盖良好的模型子图 | 可观测性差,fallback 隐蔽,设备差异大 | 必须记录 delegate、SoC、模型、算子覆盖率 |

这三类路径不是互斥关系。一个模型可能前半段走 NPU,中间某个不支持算子回到 CPU,后处理再走 GPU。性能归因要按阶段记录,而不是按"使用了某个 delegate"给整次推理定性。

[已验证: 官方文档, source.android.com/docs/core/interaction/neural-networks/device-discovery][已验证: 官方文档, ai.google.dev/edge/litert/android/npu/overview]

## ADPF 线程工作量与 GPU workload hint 版本边界

先厘清 ADPF 的能力边界。它的公开抽象是 `PerformanceHintManager.Session`：应用把一组线程 ID 和目标工作时长交给系统，再报告实际工作时长。系统侧再通过 power hint 服务和厂商 Power HAL 影响调度与频率策略。这个接口表达的是"这些线程接下来需要怎样的 CPU / 调度预算"，不是应用侧调 GPU 频、绑大核或指定 NPU 的控制面。

API 31/33 的原始 `reportActualWorkDuration()` 只接受 total duration。API 35 新增 `reportActualWorkDuration2()`，要求至少填入 actual CPU duration 或 actual GPU duration 其中一项大于 0（`AWorkDuration` setter），系统侧可以据此区分 CPU/GPU 工作组成。API 36 新增 `notifyWorkloadIncrease/Reset/Spike(session, bool cpu, bool gpu, ...)` ，应用可以声明 CPU 或 GPU workload 变化。这两组扩展让 ADPF 从"只能表达线程 CPU 工作量"演进到"可表达 GPU workload 组成和变化"，但仍不能直接控制 GPU/NPU 频率或调度策略。[已验证: AOSP android-16.0.0_r1 performance_hint.h L96-L102, L312-L338, L362-L420]

这条边界在异构负载里很容易写错。NPU 或 GPU 执行期间,应用线程可能处于等待状态;如果只把等待时间上报给 hint session,系统看到的是线程没有占满 CPU,而不是加速器需要更高频率。反过来,输入准备和后处理如果一直跑在 CPU 上,ADPF 可以帮助系统更早理解这组线程的工作节奏,但它仍不能保证厂商 GPU governor 或 NPU driver 同步响应。

Android 15 引入的 power efficiency hint 适合长时任务:应用可以声明某组线程优先能效,让系统在可接受的延迟内倾向更省电的调度方式。它适合后台批处理、离线模型预处理、相册索引这类场景;不适合前台相机预览或实时字幕的逐帧路径。实时路径更应该用帧预算和 thermal headroom 判断是否降分辨率、降帧率或延后低优先级推理。

| 场景 | ADPF 适合表达 | ADPF 不能保证 |
|---|---|---|
| UI 帧内图像增强 | 线程组目标时长、实际帧工作时长 | 强制 GPU / NPU 升频 |
| 后台相册索引 | 能效优先、长时批处理节奏 | 让 NPU 长时间独占资源 |
| LLM decode | CPU 喂数线程和采样线程的目标时长 | 修正所有 GPU / NPU 短 kernel 频率误判 |
| 相机实时翻译 | 前台线程预算和热余量反馈 | 跳过 Camera / GPU / NPU 之间的带宽竞争 |

排查 ADPF 是否有效时,先看 5.9 节的 session 创建、线程 ID 更新和实际时长上报,再把 CPU freq、thermal 和功耗数据叠到同一条时间轴。若问题发生在 GPU/NPU 内部,ADPF 只能作为间接信号,不能当作根因证据。

[已验证: 官方文档, source.android.com/docs/core/perf/performance-hint-api][已验证: 官方文档, developer.android.com/games/optimize/adpf]

## Perfetto 与厂商工具要分层使用

普通发布版设备上,Perfetto 能稳定给出 CPU 调度、CPU 频率、线程 slice、FrameTimeline、battery counters、部分 power rails 和 thermal 相关信号。GPU counter、NPU trace、power rail 覆盖范围受设备、权限和厂商实现影响很大。不能因为 trace 里没有 NPU 轨道,就断定没有 NPU;也不能因为看到 GPU 频率变化,就断定推理任务由 GPU 主导。

建议把观测信号分成三层:

| 层级 | 信号 | 可靠用途 | 边界 |
|---|---|---|---|
| Android 通用层 | sched、CPU freq、FrameTimeline、battery counters、thermal status | 判断线程是否忙、是否掉帧、是否热降级 | 看不到多数 NPU 内部队列 |
| Perfetto / AGI 扩展层 | GPU frequency、GPU counters、render stages、power rails | 判断 GPU 忙闲、频率和功耗变化 | 设备和权限差异明显 |
| 厂商 / runtime 层 | NPU trace、delegate 日志、QNN / Neuron / Tensor 相关工具 | 判断算子覆盖率、fallback、driver 队列 | 不具备跨厂商可迁移性 |

一次比较可靠的 trace 应该同时有三类标记:应用侧给输入准备、delegate 调用、后处理打自定义 slice;系统侧采 CPU / GPU / thermal / power;runtime 侧打开 delegate 日志或厂商工具。三类证据对上,才能判断"优化后推理更快"到底来自算子下沉、copy 减少、CPU 频率变化,还是热状态不同。

Perfetto 的 power rails 数据来自设备暴露的 power rail 读数,适合比较同一设备、同一测试条件下某段时间的累计能耗差。它不适合直接横向比较两台手机,也不适合在 rail 命名不清楚时强行归因到"GPU"或"NPU"。功耗归因的发布口径必须写清楚设备、系统版本、采样配置、是否充电、温度起点和 workload。

[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-freq][已验证: 官方文档, perfetto.dev/docs/data-sources/battery-counters]

## 持续推理会和前台交互抢预算

相机预览、实时翻译、AI 修图和游戏 AI 辅助都有一个共同点:推理是持续任务，跟前台交互并行运行。它会持续占用计算资源、内存带宽和散热空间,进而影响 UI 帧、Camera pipeline、SurfaceFlinger 合成或后台任务。

相机实时翻译可以按三条路径拆:Camera HAL 输出 buffer,推理 runtime 取帧做 OCR / 翻译,UI 层叠加结果。这里的关键不是 NPU 单次推理是否足够快,而是 buffer 交接、图像格式转换、结果回到 UI 的节奏是否稳定。若每帧都做全量推理,GPU/NPU 即使能吃下模型,也可能把整机推到 thermal 降级,几分钟后帧率和延迟一起变差。

游戏 AI 辅助也类似。游戏主线程、RenderThread、GPU 渲染、音频、网络和模型推理同时存在。把 NPU 当成"额外免费算力"是危险假设;它仍消耗电力和散热预算,部分 SoC 还会通过共享电源域或 thermal governor 影响 CPU / GPU 频率。游戏场景的帧率策略详见 22.10 节,包体和模型分发成本详见 25.11 节。

工程上更稳的策略是把持续推理纳入前台预算:前台高交互时降低推理频率或使用轻量模型;热余量下降时降分辨率、降 batch 或延后低优先级任务;切后台后转为能效模式或 WorkManager 约束任务。判断标准不是单次 latency 最低,而是 p90 / p99 延迟、温升和掉帧率能否长期稳定。

[已验证: 官方文档, source.android.com/docs/core/power/thermal-mitigation][来源: DeepResearch/2026-05-20-android-17-npu-aicore-nnapi-research.md]

## Android 17 NPU feature 与 LiteRT 迁移边界

Android 17 已公开 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT`(API 37),常量值是 `android.hardware.npu`。Release notes 同时要求 target Android 17 且需要直接访问 NPU 的应用在 manifest 声明这个 hardware feature。旧材料里的 `android.hardware.neural_processing_unit` 不是公开常量,不能写进发布稿或示例。

这个 feature 只能说明设备暴露了 NPU 或类似 AI 加速硬件,不能推出所有设备都有同等 NPU 能力,也不能替代 LiteRT delegate、NN HAL device discovery、厂商 SDK 或 AICore 的路径判断。涉及意图防火墙、电量配额审计、间接通过 AICore 使用 NPU 是否受同一声明约束,仍需源码或官方文档补证。

能确认的边界如下:

| 主题 | 可发布事实 | 不能外推的结论 |
|---|---|---|
| NNAPI | Android 15 起 NNAPI NDK API 被标记 deprecated,迁移文档建议使用 LiteRT / AICore 等路径 | NN HAL 或厂商 NPU 驱动从系统里消失 |
| NPU feature | API 37 新增 `PackageManager.FEATURE_NEURAL_PROCESSING_UNIT`,常量值 `android.hardware.npu`;target Android 17 且直接访问 NPU 的 App 需要声明 uses-feature | feature 只说明设备暴露 NPU / 类似 AI 加速硬件,不代表 delegate 可用性或性能一致 |
| LiteRT | LiteRT 文档提供 CPU / GPU / NPU 相关路径,NPU 依赖主要芯片厂商 delegate | 所有 Android 17 设备都有同等 NPU 能力 |
| AICore | AICore 是 Google AI on Android 路径的一部分,适合讨论 GMS 设备能力 | AICore 行为可以代表 AOSP 或所有国内设备 |
| CompiledModel | 文档展示 CompiledModel API 和硬件加速选择能力 | 未给设备、模型、delegate 版本时写固定收益数字 |

这张表的目的是把发布边界写清楚。5.11 节已有相关技术回炉项,那里会处理具体 API、AICore 内存归属和 CompiledModel 细节;本节只保留异构调度和功耗归因所需的边界。

[已验证: 官方文档, developer.android.com/reference/android/content/pm/PackageManager#FEATURE_NEURAL_PROCESSING_UNIT][已验证: 官方文档, developer.android.com/about/versions/17/release-notes][已验证: 官方文档, developer.android.com/ndk/guides/neuralnetworks/migration-guide][已验证: 官方文档, source.android.com/docs/core/interaction/neural-networks/device-discovery][来源: DeepResearch/2026-05-15-android-17-npu-litert-aicore.md]

## GPU/NPU 与 EAS、devfreq cooling 的交互

CPU、GPU、NPU 共享电池和散热空间,但控制路径分散。CPU 侧由调度器、cpufreq 和 EAS 估算任务需求;GPU 侧常走 devfreq / GPU governor;NPU 多数在厂商 driver 和 runtime 内部;Thermal HAL 再把传感器与 cooling device 状态反馈给系统。某一侧冲高,另一侧未必立刻知道任务语义,但会一起受温控预算影响。

这类问题的 trace 解法是按时间顺序看四件事:

- 线程迁移和 CPU 频率:判断输入准备、提交线程、回调线程是否被调到合适 CPU,以及是否被后台任务抢占。
- GPU/NPU 执行信号:有 GPU counter 或厂商 NPU trace 时,确认硬件是否忙;没有时,退回 delegate 日志和端到端阶段 slice。
- thermal severity 和 cooling device:判断降频是性能策略选择,还是温控已经介入。
- power rail 或 battery counter:比较同一设备同一 workload 下的能耗变化,避免只用温度或电量百分比做结论。

若看到 CPU 线程频繁等待、GPU 频率偏低、thermal 未介入,问题可能是 governor 对短 kernel 误判;若 thermal severity 抬升后 CPU/GPU 同时降频,问题更可能是整机热预算耗尽;若 delegate 日志显示大量 fallback,NPU 路径再快也救不了端到端延迟。对应机制分别见 5.4、5.12 和 5.13 节。

[已验证: 官方文档, source.android.com/docs/core/power/performance][已验证: 官方文档, source.android.com/docs/core/power/thermal-mitigation]

## 端侧 AI 性能实验模板

异构负载实验最怕只记录平均耗时。平均值会掩盖冷启动、p99 抖动、热降级和 fallback。实验表应至少包含这些字段:

| 类别 | 字段 | 说明 |
|---|---|---|
| 设备环境 | 机型、SoC、Android 版本、内核版本、是否充电、起始温度 | 没有这些字段,功耗和温控结论不可复核 |
| 模型信息 | 模型名、大小、量化方式、输入尺寸、batch、runtime / delegate 版本 | 解释算子覆盖和内存占用差异 |
| 路径配置 | CPU / GPU / NPU、delegate 参数、线程数、是否允许 fallback | 避免把 fallback 当成 NPU 收益 |
| 时间指标 | 冷启动、首次推理、稳态 p50 / p90 / p99、阶段 slice | 区分初始化成本和稳态成本 |
| 资源指标 | CPU freq、GPU freq / counter、RSS / PSS、power rails、thermal severity | 解释"快了但更耗电"或"慢了但更稳" |
| 交互指标 | FrameTimeline jank、相机预览帧率、触摸响应、后台任务延迟 | 判断推理是否影响用户可见路径 |

对比实验要用同机型、同系统版本、同温度起点。CPU 基线、GPU delegate、NPU delegate 至少各跑一组;如果设备没有公开 NPU 工具,就把 NPU 组标成"delegate 日志声明"或"vendor tool verified",不要只写"NPU"。持续运行建议至少覆盖冷启动、1 分钟稳态、5-10 分钟热稳定三个窗口。

发布数据时保留 p90 / p99 和失败样本。异构负载的工程风险常出现在尾部:偶发 fallback、driver queue 堵塞、热降级后的频率台阶、低电量模式介入。只给 p50 会让读者低估线上风险。

## 厂商 SoC 差异与可迁移结论

Qualcomm、MediaTek、Google Tensor、Samsung 的 AI 加速路径、GPU driver、thermal 策略和 power rail 暴露方式都不同。公开 LiteRT NPU 文档能说明主要芯片厂商 delegate 的方向,但不能替代设备实测。某个 Snapdragon 设备上成立的 QNN delegate 行为,不能直接套到 MediaTek Neuron 或 Tensor 平台。

可迁移的结论通常是方法,不是数字:

- 阶段拆分可迁移:输入准备、delegate、硬件执行、同步、后处理这五段在不同 SoC 上都能用。
- 观测分层可迁移:通用 Perfetto 信号、GPU 扩展信号、厂商 NPU 工具要分开写。
- 版本边界可迁移:NNAPI deprecated、LiteRT 迁移、ADPF session 语义来自公开文档,能作为章节基线。
- 收益数字不可迁移:latency、功耗、温升、NPU 覆盖率必须绑定设备、模型和 runtime。

归结起来，GPU/NPU 异构调度的归因不能停在"任务跑了哪个加速器"。CPU 准备阶段的成本、硬件执行期间的温度变化、同步等待与回读延迟、整机热预算的余量，每一项都影响最终结论。能在 trace 和对照实验中复现的判断，才值得写进发布稿。

## References

- [Android Performance Hint API](https://source.android.com/docs/core/perf/performance-hint-api)
- [Optimize with ADPF](https://developer.android.com/games/optimize/adpf)
- [NNAPI Migration Guide](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)
- [NNAPI device discovery and assignment](https://source.android.com/docs/core/interaction/neural-networks/device-discovery)
- [LiteRT overview](https://ai.google.dev/edge/litert/overview)
- [LiteRT delegate for NPUs](https://ai.google.dev/edge/litert/android/npu/overview)
- [Perfetto CPU frequency and idle states](https://perfetto.dev/docs/data-sources/cpu-freq)
- [Perfetto power data sources](https://perfetto.dev/docs/data-sources/battery-counters)
- [来源: DeepResearch/2026-05-20-android-17-npu-aicore-nnapi-research.md]
- [来源: OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-adpf-non-game-scenarios-and-profiling-trigger-type-anomaly.md]
