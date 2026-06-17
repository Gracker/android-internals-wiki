---
title: "GenAI 应用集成性能边界：AICore 调度、Google Intelligence API 与资源竞争"
chapter: "5.20"
status: ready-for-review
drafted_date: "2026-06-18"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-06-18"
last_verified_against: "Android 17/API 37 公开文档"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/ai/aicore"
  - type: official
    path: "developer.android.com/ai/reference/kotlin/com/google/ai/edge/aicore/package-summary"
  - type: blog
    path: "developer.android.com/ai/get-started"
tags: ["GenAI", "AICore", "端侧AI", "性能优化", "NPU", "IPC"]
related_chapters: ["5.11", "5.13", "5.14", "5.19", "25.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-18"
gap_source: "官方文档/章节深挖"
---

# 5.20 GenAI 应用集成性能边界：AICore 调度、Google Intelligence API 与资源竞争

应用集成端侧 GenAI 能力时，性能开销不只来自推理本身。AICore 作为独立系统进程运行，每次推理请求都要跨进程通信；推理占用的内存归在 AICore 进程名下，App 自身的内存压力指标可能看不出异常；多个 App 同时请求推理时，NPU 时间片的分配由系统决定，调用方无法控制优先级。这些边界条件决定了 GenAI 集成方案的性能天花板。

本章关注 App 调用 AICore / Google Intelligence API 时的工程性能边界。模型推理本身的基础设施（NNAPI、LiteRT、TFLite 运行时选型）详见 §5.11，ADPF 会话调度与热管理详见 §5.19。

## AICore 进程模型与 IPC 管线

### AICore 不是进程内 SDK

AICore 以 Mainline 模块（Project Mainline）形式存在，运行在独立进程 `com.google.android.aicore` 中（包名以实际设备为准，部分文档和抓包结果显示该进程名可能因设备而异）。App 通过 Google AI Edge SDK 或 ML Kit GenAI APIs 发起推理请求时，请求经 Binder IPC 传递到 AICore 进程，推理完成后结果再经 Binder 返回。

调用链路：

```
App 进程
  → ML Kit GenAI API / Google AI Edge SDK
    → Binder IPC（推理请求序列化）
      → AICore 系统服务进程
        → NNAPI HAL → NPU/GPU 执行
      ← Binder IPC（推理结果反序列化）
    ← 回调 / Future
  ← 结果返回给业务代码
```

[已验证: developer.android.com/ai/aicore — AICore 作为系统服务运行，模型管理独立于 App]

每次推理至少经历两次 Binder 事务（请求 + 响应），生成式推理的流式输出（streaming）还会产生多次回调。Binder 本身的单次开销在亚毫秒级，对大模型推理（首 token 延迟通常 200ms 以上）占比可忽略。但如果推理请求频繁（如实时翻译逐句调用），Binder 事务的序列化 / 反序列化开销和线程切换成本会累积。

### Private Compute Services 的角色

AICore 没有直接的 internet access。模型下载和更新由 Private Compute Services（PCS）完成。这意味着模型准备阶段涉及另一个独立进程：

- 首次使用 GenAI 能力时，AICore 向 PCS 发起模型下载请求
- 模型文件可能已经缓存（系统 OTA 或其他 App 触发过下载），也可能需要现场下载
- 模型校验、解压、优化编译在 AICore 进程中完成，CPU 和 I/O 开销归在 AICore 进程

[已验证: developer.android.com/ai/aicore — "AICore 没有直接的 internet access，模型下载通过 Private Compute Services 完成"]

对 App 性能的影响：首次冷启动延迟不可预测。同样的推理调用，在模型已缓存的设备上 200ms 返回，在需要下载的设备上可能要等待数十秒。App 侧需要检测模型可用性（`Availability` 回调），并为未就绪状态准备 fallback。

### Google Intelligence API 的版本映射

Google Intelligence API 是 AICore 对外暴露的高阶接口（`com.google.ai.edge.aicore` 包）。API 层面包含：

- `InferenceSession`：管理推理上下文和会话生命周期
- `GenerativeAIException.ErrorCode`：错误码枚举，包括模型不可用、安全过滤触发、资源不足等
- `DownloadCallback`：模型下载进度和状态回调

[已验证: developer.android.com/ai/reference/kotlin/com/google/ai/edge/aicore/package-summary]

API 能力随 AICore 模块版本演进，不受系统大版本严格绑定。AICore 起源于 Android 14（API 34），通过 Mainline 更新机制可以独立于系统版本迭代。App 集成时需要做运行时能力检测，不能按 `Build.VERSION.SDK_INT` 硬编码能力假设。

## 推理调用与线程调度

### 同步调用的主线程风险

AICore 推理 API 设计为异步模式（回调或 `ListenableFuture`），但开发者的使用方式可能引入同步阻塞：

- 在回调中直接执行后续逻辑，回调本身运行在 Binder 线程池而非主线程
- 使用 `Future.get()` 同步等待结果，阻塞调用线程
- 流式输出回调中触发 UI 更新时，如果未切回主线程，可能引入线程安全风险

推理期间 App 进程的线程状态变化：发起推理的线程（通常是业务线程）在等待回调期间处于 WAITING/BLOCKED；Binder 线程池中有一个线程负责接收 AICore 返回的回调。如果 App 在回调中执行重逻辑（如 JSON 解析、数据库写入），Binder 线程会被占用，影响其他 IPC 事务的响应速度。

### 推理与渲染的资源争抢

GenAI 推理任务执行期间，NPU/GPU 和 CPU 都可能被占用。对前台 App 来说，最直接的影响是：

- **GPU 争抢**：如果推理使用 GPU 路径（部分模型通过 GPU delegate 执行），与 RenderThread 的 GPU 命令队列竞争同一硬件队列。表现为帧时间变长、GPU frequency 被拉满但帧率下降。
- **CPU 争抢**：推理的预处理和后处理（tokenization、tensor 转换、安全过滤）在 AICore 进程的 CPU 线程上执行，与 App 的主线程和工作线程共享 CPU 时间片。大 SoC 上影响较小，中低端 SoC 上可能导致明显卡顿。
- **内存带宽争抢**：推理期间的高带宽内存访问（模型权重读取、中间 tensor 计算）会挤占渲染管线和 UI 布局的内存带宽，这种争抢在 Perfetto trace 里不容易直接观测到。

排查推理导致的卡顿时，先在 Perfetto 中对比推理开始前后的帧时间分布、CPU frequency 和 GPU frequency 变化。如果推理期间 CPU/GPU frequency 都在高位但帧率下降，资源争抢的概率高于纯 CPU 耗尽。

## 内存归属与竞争边界

### AICore 推理内存不归 App 管

AICore 迨行在独立进程中，模型权重、推理中间 tensor、Delegate workspace 等内存开销都记录在 AICore 进程的 PSS/RSS 下，而不是调用方 App。这意味着：

- App 侧的 `Debug.getMemoryInfo()` 或 `ActivityManager.getProcessMemoryInfo()` 不会反映推理内存
- 系统 LMK 判定基于进程级别内存压力，AICore 进程的内存增长可能触发 LMK 杀其他后台进程，而不是杀调用方 App
- App 被 LMK 杀掉后 AICore 推理可能仍在执行，造成资源浪费

[已验证: 当前公开文档未确认 AICore 内存回算机制 — developer.android.com/ai/aicore 和 Android memory 文档未描述跨进程工作归属]

Android 16 引入了 `ATTRIBUTE_WORK_TO_OTHER_APPS` 属性用于标记跨进程工作归属。该属性的设计意图是让系统在做资源调度决策时能正确归因跨进程工作。AICore 是否使用该属性回算推理内存到调用方 App，当前公开文档未确认。排查内存水位时建议同时观察调用方 App 和 AICore / Private Compute Services 进程的内存变化。

### 模型大小与内存占用范围

端侧 GenAI 模型的内存占用主要由模型权重决定，量化后的范围大致为：

| 模型 | 参数量 | 量化方式 | 权重大小 | 运行时 RSS 范围 |
|------|--------|---------|---------|---------------|
| Gemini Nano | ~1.8B | INT4 | ~1.5 GB | 1.8-2.5 GB |
| Gemini Nano 4 | ~4B | INT4 | ~2.5 GB | 3-4 GB |
| Gemma 4 | ~4B | INT4 | ~2.5 GB | 3-4 GB |

[待验证: 模型参数和内存数据来自 AICore Developer Preview 文档和社区测试，未经 AOSP 源码一手验证。具体数字以官方兼容列表和机型实测为准。]

这些内存不是在 App 进程中分配的，但系统总内存是有限的。在 8GB 或 12GB 的设备上，一个占用 2-4 GB 内存的推理任务会把系统内存压力推到很高水平，间接影响所有前台和后台进程。

### 与 LMK 的交互

当 AICore 推理导致系统内存压力升高时，LMD（lmkd）会按 oom_adj 分数从高到低杀进程。AICore 进程的 oom_adj 通常较低（系统服务级别），不会被优先杀掉。被杀的更可能是后台 App（包括调用方 App 的后台实例）。如果调用方 App 在前台，推理期间一般安全；但如果 App 在推理过程中切到后台，被 LMK 杀掉的概率取决于系统的整体内存压力。

详见 §4.4 关于 LMK 机制和 oom_adj 的分析。

## ADPF Thermal 与推理降级

### GenAI 推理是热源

大模型推理是典型的计算密集任务，持续推理会快速拉高 SoC 温度。AICore 内部有温度监控机制，但 App 侧也需要关注热状态变化对推理性能的影响。

推理导致 thermal throttling 时的典型表现：

1. 首次推理正常（NPU frequency 未被限制），延迟在预期范围
2. 持续推理 30-60 秒后，温度触发 thermal mitigation，NPU/GPU frequency 被降低
3. 推理延迟从 200ms 上升到 500ms-1000ms，流式输出的 token rate 明显下降
4. 温度恢复后，frequency 回升，但恢复速度取决于设备的散热能力

ADPF 的角色：App 可以通过 PerformanceHintManager 的 `setPreferPowerEfficiency(true)` 告诉系统「这个会话更注重能效而非峰值性能」。系统会据此调整 CPU/NPU frequency 调度策略，可能在更低的频率稳定运行，减少热降频的概率。

[已验证: PerformanceHintManager.Session.setPreferPowerEfficiency — API 35+]

ADPF 会话管理和 hint 机制的详细使用方式详见 §5.19。

### 降级策略设计

GenAI 集成方案应该内置降级策略，不能假设推理性能恒定：

- **模型降级**：准备多个量化级别的模型或多个模型版本。温度升高时切换到更小、更快的模型，牺牲精度换取响应速度。
- **请求延迟**：非实时场景（如批量内容生成）可以降低请求频率或暂停推理，让设备冷却。
- **功能 fallback**：当 AICore 不可用（设备不支持、模型未下载、温度过高）时，退回到规则引擎或云端推理。

降级触发条件不应只看 App 自身的性能指标，还要监听系统 thermal 状态。`PowerManager.addThermalStatusListener` 可以获取当前热状态（`THERMAL_STATUS_NONE` 到 `THERMAL_STATUS_SHUTDOWN`），在 `THERMAL_STATUS_MODERATE` 以上时就应该考虑降级。

[已验证: PowerManager.addThermalStatusListener — API 29+]

## 多 App 推理调度

### 共享 NPU 的时间片分配

AICore 作为系统级服务，可能同时接收多个 App 的推理请求。NPU 硬件时间片的分配由 AICore 调度器和 NPU 驱动决定，调用方 App 无法指定优先级。这意味着：

- 前台 App 的推理请求与后台 App 的推理请求在 AICore 内部可能被同等对待
- 多个 App 交替推理时，每个 App 观察到的延迟会高于独占时的延迟
- 如果一个 App 发起长时间流式推理，其他 App 的推理请求可能排队等待

App 侧能做的有限：优先使用流式输出而非整段生成，减少单次推理的 NPU 占用时间；在非实时场景中使用 `WorkManager` 错峰调度推理任务；监听 `onTrimMemory` 回调，在系统资源紧张时主动暂停推理。

### 观测多租户推理的方法

Perfetto trace 中不会直接标注"AICore 正在为谁推理"。排查多 App 推理争抢问题时：

1. 查看 `com.google.android.aicore` 进程的 CPU 线程活跃度，判断是否有多个推理并发执行
2. 对比 NPU/GPU frequency 持续时间和单次推理预期耗时，间接判断是否存在排队
3. 在 App 侧的推理调用前后打 `Trace.beginSection("aicore_inference_request")`，测量从发起到回调的实际墙钟时间
4. 如果回调延迟方差很大（同一模型有时 200ms 有时 800ms），排队或 thermal throttling 的可能性高

## Perfetto 观测要点

| 观测目标 | Track / Counter | 预期表现 |
|---------|----------------|---------|
| 推理期间 CPU 负载 | CPU track + CPU frequency | AICore 进程线程活跃，CPU frequency 抬升 |
| GPU 路径推理争抢 | GPU frequency + GPU work | frequency 拉高，与 RenderThread 重叠时帧时间变长 |
| 内存压力 | RSS / memory counter | AICore 进程 RSS 上升，系统可用内存下降 |
| Thermal 变化 | Thermal track | 持续推理后温度上升，frequency 被限制 |
| Binder 延迟 | Binder track | 推理请求和回调的 Binder 事务耗时 |
| 推理墙钟延迟 | App 自定义 Trace section | 从请求到回调的完整时间，方差大说明存在排队 |

默认 system trace 能稳定看到线程调度、CPU/GPU frequency、内存水位和 thermal 变化。模型内部推理阶段的细节（tokenization、权重加载、NPU 执行）在 AICore 进程内部，App 侧无法通过 Perfetto 直接观测。

## 与其他章节的关联

- **§5.11 端侧 AI 推理性能**：NNAPI、LiteRT、模型优化技术的基础设施
- **§5.19 端侧 AI 调度与 ADPF 智能优化**：ADPF 会话管理、PerformanceHintManager 使用方式
- **§5.13 移动端 LLM 推理的 DVFS 与能效边界**：LLM 推理的能效分析
- **§5.14 Android 17 ML Runtime 与 NPU 访问边界**：NPU 访问的版本演进
- **§4.4 Low Memory Killer**：推理内存压力与 LMK 的交互
- **§1.4 Binder IPC**：Binder 事务的基础机制
- **§2.5 MainThread 与 RenderThread**：推理与渲染的资源争抢
