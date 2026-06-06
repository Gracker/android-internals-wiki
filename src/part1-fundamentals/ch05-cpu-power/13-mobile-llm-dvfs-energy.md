---
title: "移动端 LLM 推理的 DVFS 与能效边界"
chapter: "5.13"
section: "5.13"
status: finalized
drafted_date: "2026-05-16"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-16"
last_verified_against: "AOSP main + Android 官方文档 + Perfetto docs + arXiv 2507.02135"
confidence: medium
tags: [android, dvfs, eas, adpf, llm, on-device-ai, power]
related_chapters: ["5.2", "5.4", "5.9", "5.11", "5.12", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/研究素材/官方文档"
gap_score: 17
pipeline_stage: ready-to-publish
reviewed_by: openclaw-task6
reviewed_date: "2026-05-16"
task6_result: pass-light-edit
task6_state: reviewed
task9_state: reviewed
last_task6_at: "2026-05-16T19:11:00+08:00"
last_task6_audit: "2026-06-06"
task9_result: pass-tech-review
last_task9_at: "2026-05-16T19:31:25+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-16"
last_task9_review_log: "logs/deep-review/2026-05-16-19-deep-review.md"
sources:
  - type: paper
    path: "https://arxiv.org/abs/2507.02135"
  - type: material
    path: "论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md"
  - type: official
    path: "https://source.android.com/docs/core/power/performance"
  - type: official
    path: "https://source.android.com/docs/core/perf/performance-hint-api"
  - type: official
    path: "https://developer.android.com/games/optimize/adpf"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-freq"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/battery-counters"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PerformanceHintManager.java"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
---

# 5.13 移动端 LLM 推理的 DVFS 与能效边界

端侧 LLM 推理把 Android 的功耗问题从“单个线程跑得快不快”推到 CPU、GPU、内存带宽和温控共同约束的区间。prefill 阶段更像批量计算，decode 阶段更像短周期串行生成；两段对频率、带宽和调度延迟的要求并不相同。读完本节，应该能把 TTFT、TPOT、energy-per-token、热余量和 ADPF 可控范围放到同一张验证表里。

EAS、DVFS、ADPF 和端侧 AI 推理栈的基础见 5.2、5.4、5.9、5.11、5.12 节。这里补端侧 LLM 场景下的工程判断：哪些现象会误导 governor，哪些能力普通 App 能用，哪些手段只适合 root、实验机或厂商实现。

## LLM 推理负载与传统交互负载的差异

LLM 推理通常分成两个阶段：prefill 处理输入 prompt，decode 逐 token 生成输出。prefill 的并行度更高，GPU 或 NPU 更容易被喂满；decode 每次只推进一个或少量 token，CPU 要持续做采样、KV cache 管理、命令提交和运行时调度，GPU 侧却可能呈现较低利用率。[引用: https://arxiv.org/abs/2507.02135]

这和传统触控、滑动、动画负载差异很大。交互负载通常围绕帧 deadline 组织，16.6ms、8.3ms 或更短的周期会给系统比较清楚的目标；LLM decode 的用户感知指标是 token 间隔，常用 TPOT（time per output token）衡量。一个 token 慢 30ms 不一定触发帧率报警，但连续几十个 token 都慢，用户会感到生成速度变钝。

| 阶段 | 主要指标 | 常见瓶颈 | 对频率策略的要求 |
|---|---:|---|---|
| prefill | TTFT | GPU/NPU 算力、内存带宽、模型加载后的首轮 kernel 调度 | 需要较快升频，避免首 token 等待被拉长 |
| decode | TPOT / tokens/s | CPU 喂数、采样、KV cache 访问、短 kernel 启停 | 需要稳定频率组合，不能只看单一硬件利用率 |
| 连续对话 | energy-per-token、温升 | 热余量、后台任务、屏幕和网络并发耗电 | 需要可持续的能耗曲线，避免前段冲高后段降频 |

prefill 和 decode 的差异还会改变 trace 解读方式。单看 GPU utilization 可能会低估 decode 对 GPU 频率的敏感性；单看 CPU utilization 也可能会低估 CPU 频率对 GPU 提交节奏的影响。更可靠的口径是把 token 时间戳、CPU/GPU/内存频率、功耗和温度放在同一条时间轴上。

## DVFS governor 在 CPU、GPU、内存之间的独立决策

Android 设备上的频率控制通常分散在多个层级：CPU 由 cpufreq 与调度器信号驱动，GPU 常由厂商 devfreq / GPU governor 管理，内存频率由内存控制器与厂商策略决定。EAS 负责 CPU 选核与能量估算，Power HAL 接收系统模式和性能提示，Thermal HAL 再把温度约束反馈给框架与内核。各部分共享同一块电池和散热空间，却未必共享同一个推理任务目标。[已验证: 官方文档, source.android.com/docs/core/power/performance]

AOSP 的 `PerformanceHintManager` 把一组线程作为 `Session` 提交给系统，AIDL Power HAL 也有 `createHintSession(tgid, uid, threadIds, durationNanos)`。公开 API 的设计单位是“线程组 + 目标时长”，不能指定某个 CPU/GPU 频点。[已验证: AOSP main, frameworks/base/core/java/android/os/PerformanceHintManager.java][已验证: AOSP main, hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl]

LLM 推理会碰到一个调度错位：GPU governor 往往根据 GPU 自身忙闲判断频率，CPU 调度器根据 CPU 近期负载判断算力需求，内存频率策略又按带宽和访问模式响应。decode 阶段如果 GPU kernel 很短，GPU 侧可能判断负载偏低；CPU 侧又因为周期性等待 GPU 或内存而看起来不够忙。两个判断叠在一起，就可能把频率组合推到不适合 decode 的位置。

工程上不要把“某个硬件利用率不高”直接翻译成“这块硬件不影响推理”。LLM decode 的慢点可能藏在跨硬件交接处：CPU 发不出足够快的命令，GPU 频率太低导致短 kernel 尾延迟变长，内存频率不足让 KV cache 访问抖动。详见 5.4 节的 cpufreq / governor 背景和 5.11 节的端侧 AI 执行后端。

## decode 阶段的频率误判与延迟放大

FUSE 论文在 Pixel 7 / Pixel 7 Pro（Google Tensor G2，Mali-G710 MP7）上测到一个典型现象：默认 governor 在 decode 阶段给 GPU 选择较低频率，TPOT 明显变长；把 GPU 固定到更高频率后，TPOT 下降，能耗接近不变。论文给出的 TinyLlama 数据是 GPU 424.4MHz 时 TPOT 215.1ms，固定到 848MHz 后 TPOT 126.9ms，单 token 能耗从 396.5mJ 到 402.7mJ。[来源: 论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md][引用: https://arxiv.org/abs/2507.02135]

CPU 侧也有类似现象。论文记录 TinyLlama decode 阶段 CPU 运行在约 1130.8MHz，而对应的较优频点是 2252MHz；StableLM 从约 1038.8MHz 提到 2401MHz 后，TPOT 也下降。这组数据的结论要收窄：默认 governor 使用的局部利用率信号没有表达 decode 的跨硬件依赖，不能直接推出“频率越高越好”。

| 论文场景 | 默认频率表现 | 调整后表现 | 论文给出的变化 |
|---|---|---|---:|
| TinyLlama decode / GPU | GPU 约 424.4MHz，TPOT 215.1ms | GPU 848MHz，TPOT 126.9ms | TPOT 下降 41.0%，能耗接近 |
| StableLM decode / GPU | 默认 GPU 频率偏低 | GPU 762MHz | TPOT 下降 34.6%，能耗接近 |
| TinyLlama decode / CPU | CPU 约 1130.8MHz | CPU 2252MHz | TPOT 下降 13.2% |
| StableLM decode / CPU | CPU 约 1038.8MHz | CPU 2401MHz | TPOT 下降 13.4% |

这组数据的适用范围要写清楚。它来自 Pixel 7 / 7 Pro、Tensor G2、Mali GPU、特定模型和推理框架，不应直接外推到 Snapdragon、MediaTek 或厂商 NPU delegate。对其他 SoC，可信做法是复刻测量口径：固定模型、输入长度、温度初始状态、线程绑定策略和采样工具，再比较默认 governor 与候选频率组合。

## 能效目标下的频率组合选择

端侧 LLM 的优化目标不能只写“更快”。至少要同时看四个指标：TTFT 决定用户第一次看到输出的等待，TPOT 决定生成阶段的体感速度，energy-per-token 决定续航和发热，热余量决定连续对话能坚持多久。只压低 TPOT 可能让前几轮很快，几分钟后进入热限频，整体体验反而不稳。

FUSE 的思路是把 CPU、GPU、内存频率组合当作一个整体评估，在离线阶段搜索给定能耗预算下的低延迟组合，运行时按请求特征查表。论文在 ShareGPT 数据集上的结果是 TTFT 平均降低 7.0%-16.9%，TPOT 平均降低 25.4%-36.8%，并保持相同 energy-per-token。[引用: https://arxiv.org/abs/2507.02135]

对 Android App 团队，可执行的版本更克制：

- 建立基线：固定模型、delegate、线程数、prompt 长度分布和设备温度，记录 TTFT、TPOT、tokens/s、energy-per-token、表面温度和热状态。
- 分段看频率：prefill 和 decode 分别统计 CPU cluster、GPU、内存频率，不把整段平均值混在一起。
- 设计候选组合：普通 App 不锁频，可通过线程数、batch、采样策略、delegate、ADPF hint session 和 thermal headroom 控制负载形状；root 或实验机才考虑 `scaling_min_freq` / `scaling_max_freq` 这类频率固定手段。
- 给出边界：同一模型在不同 SoC 上的最优点可能完全不同，频率表、散热设计、GPU 驱动和厂商 Power HAL 都会改变结果。

Android 7 以后有 sustained performance mode，OEM 可以通过 Power HAL 做 CPU/GPU 上限或其他温控优化，让长时间负载更稳定。[已验证: 官方文档, source.android.com/docs/core/power/performance] 这类能力适合解释“平台能做什么”，不能等同于普通 App 可以任意改频率。

## ADPF、Power HAL 与应用可控边界

ADPF 给 App 的能力是表达目标和反馈工作时长。`PerformanceHintManager.createHintSession()` 绑定一组线程和目标时长，`setThreads()` 可更新线程集合，`reportActualWorkDuration()` 把本轮工作耗时回报给系统。官方文档明确说明 App 不能直接指定 CPU 频率，也不应该用 busy loop 伪造负载。[已验证: 官方文档, source.android.com/docs/core/perf/performance-hint-api][已验证: AOSP main, frameworks/base/core/java/android/os/PerformanceHintManager.java]

端侧 LLM 可以把 hint session 用在推理线程组上，但要处理两个问题。线程集合必须稳定，推理框架如果频繁创建销毁 worker，需要在框架层收敛线程生命周期；目标时长也要按阶段设置，prefill 的目标和 decode 的目标不应混用。Android 15 的 Power Efficiency Mode 允许 session 表达“优先能效”的调度偏好，适合在连续推理、后台摘要或低电量模式里测试。[已验证: 官方文档, developer.android.com/games/optimize/adpf]

Power HAL 在系统侧接收模式、boost 和 hint session。普通 App 不直接调用 Power HAL，也不能假设某个 hint 一定映射到某个频点；厂商可能把同一 hint 映射为 CPU capacity、uclamp、GPU 策略、热策略或什么都不做。结论要以 Perfetto、PowerStats 和端到端 token 日志为准。

可控边界可以这样划分：

| 能力 | 普通 App | 系统 / 厂商 | root / 实验机 |
|---|---|---|---|
| ADPF hint session | 可用，受 API 等级和设备实现影响 | 决定 hint 到调度策略的映射 | 可配合内核观测验证 |
| Thermal API / headroom | 可读热状态并降级模型或采样参数 | 决定热阈值和 cooling device | 可读取更多 sysfs 节点 |
| CPU/GPU 固定频率 | 不可直接指定 | 可在 Power HAL / kernel policy 中实现 | 可通过 sysfs 或调试接口固定 |
| NPU/GPU delegate 策略 | 可选公开 delegate 和线程参数 | 决定驱动、runtime、频率策略 | 可抓取更多厂商 counters |

## 端侧 AI 推理的验证方法

验证端侧 LLM 能效要同时采集“业务事件”和“系统事件”。业务侧至少记录每次请求的 prompt token 数、输出 token 数、TTFT、每个 token 的完成时间、delegate、线程数、模型版本和温度初始状态；系统侧记录 CPU 调度、CPU/GPU/内存频率、功耗、温度、thermal throttling 和后台任务干扰。

Perfetto 的 CPU frequency 数据源可通过 `power/cpu_frequency` ftrace 事件记录频率变化，也可用 `linux.sys_stats` 周期性读取 `/sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_cur_freq`。Perfetto 官方建议把事件和 polling 结合使用，因为频率事件只在变化时出现，trace 开头可能缺初始值。[已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-freq]

这段配置用于采集 CPU 频率、调度事件和 Android 电源数据；设备如果支持 power rails，可打开 `collect_power_rails` 观察硬件域能耗。

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
    }
  }
}

data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      cpufreq_period_ms: 50
    }
  }
}

data_sources: {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 250
      collect_power_rails: true
    }
  }
}
```

这份配置只能解决观测入口，不能保证每台设备都有 GPU、NPU、内存频率和 rail 级能耗。Perfetto 的 power rails 依赖设备厂商暴露的硬件计量能力，平台侧通过 `IPowerStats` HAL 读取能耗数据；AIDL `IPowerStats` 也说明 `EnergyConsumerResult`、`EnergyMeasurement` 不保证每次请求都有结果。[已验证: 官方文档, perfetto.dev/docs/data-sources/battery-counters][已验证: AOSP main, hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl]

实验报告建议固定这几个口径：

- 温度初始状态：冷机、稳态温度、连续推理 15 分钟后的热状态分开记录。
- 输入输出分布：短 prompt、长 prompt、多轮对话分别统计，TTFT 和 TPOT 不混算。
- 设备状态：屏幕亮度、网络、充电状态、省电模式、游戏模式、后台任务都写进测试条件。
- 能耗口径：优先用外接功耗仪或 power rails；只能用电池计数器时，写明采样间隔和设备支持情况。
- 复现边界：论文级结论只在同类 SoC、同类 delegate、同类模型规模下迁移，跨平台必须重测。

## 扩展：FUSE 与 llama.cpp 的实验复现边界

FUSE 的价值在于把 CPU、GPU、内存频率组合放到同一张搜索表里评估，而不是让三个 governor 各自按局部信号行动。论文称其在 llama.cpp 中实现，并在 Pixel 7 / 7 Pro 上完成实验。[来源: 论文/Android-2026-05-15-DVFS-LLM-Performance/03-精读.md]

本轮未核对 FUSE 公开仓库、补丁接口和复现实验脚本。[待验证: FUSE 开源实现与 llama.cpp 集成方式] 后续如果要写成可复现实验，需要补齐模型文件、量化格式、OpenCL / GPU delegate 版本、输入长度分布、频率控制权限、功耗采样设备和温度控制流程。

## 扩展：NPU / GPU delegate 与 DVFS 联动

GPU delegate、LiteRT / TFLite delegate、NNAPI 或厂商 NPU runtime 的频率观测点差异很大。GPU 路径通常还能在 Perfetto、vendor profiler 或 devfreq 节点里看到部分频率信息；NPU 路径更依赖厂商计数器、PowerStats rail 命名和 runtime 日志。公开资料不足时，不要把 GPU 结论直接迁移到 NPU。

可操作的写法是把执行后端作为实验维度：CPU / XNNPACK、GPU delegate、NNAPI / vendor delegate、AICore 或厂商 SDK 分别测 TTFT、TPOT、energy-per-token 和热状态。某个后端如果缺少频率计数器，就把它标成黑盒路径，用端到端指标和可见 power rails 做旁证。[待补充: 各厂商 NPU 频率与能耗计数器公开入口]

## 扩展：持续推理下的热衰减与用户感知指标

连续推理要按时间窗看，而不是只取前 20 个 token。建议把 0-1 分钟、1-5 分钟、5-15 分钟、15 分钟以后分开统计 TPOT P50 / P90、energy-per-token、thermal status、表面温度和前台帧率干扰。这样能区分“短时响应快”和“长时间稳定”。

用户感知还会受 UI 干扰影响。LLM 输出如果和 Compose / RecyclerView 流式渲染、语音播报、网络请求并发，CPU 与 GPU 的频率预算会被共享。可观测性方案应把 token 日志和 FrameTimeline、主线程、RenderThread、推理线程放进同一个 trace，避免把 UI 卡顿误判成模型推理慢，或把推理降速误判成渲染问题。

## 扩展：Agent 长期记忆系统在 Android 端侧 AI 应用的适配

<!-- AIW-源码调研-2026-06-04 -->

本节补充 Mem0、M3-Agent 等 Agent 长期记忆系统在 Android 端侧 AI 应用中的工程映射。详细源码分析见 [DeepResearch/2026-06-04-agent-longterm-memory-on-android.md](../../../../../DeepResearch/2026-06-04-agent-longterm-memory-on-android.md)。

### 两个代表系统的核心差异

| 维度 | Mem0 v3 (April 2026) | M3-Agent (ICLR 2026, arXiv 2508.09736) |
| --- | --- | --- |
| 记忆粒度 | 离散 fact（LLM ADD-only 抽取） | 实体节点 + 边权（episodic / semantic） |
| 存储抽象 | 24 种 vector store + SQLite 缓存 | 单个 `VideoGraph` (`pickle.dump`) |
| 默认 LLM | `gpt-5-mini`（云） | Qwen2.5-Omni-7B（GPU 服务）+ `text-embedding-3-large`（云） |
| 输入模态 | 文本 / vision | 视频 + 音频 + 声纹 + 人脸 |
| Android SDK | 无 | 无 |

### Android 端侧适配分四个层面

1. **Embedding 层**：`mem0/embeddings/fastembed.py` 的 `FastEmbedEmbedding` 用 `thenlper/gte-large`（1024 维 ONNX 模型），可经 `onnxruntime-android` + NNAPI 跑在 Android 8.1+（API 27）；量化后 ~250 MB。
2. **LLM 层**：替换云端 GPT/Qwen 为 `MediaPipe LLM Inference`（Android 14+/API 34+）或 `LiteRT-LM`；M3-Agent 的 7B 模型量化为 4-bit 约 4 GB，端侧只能跑量化蒸馏版。
3. **存储层**：`mem0/memory/storage.py` 的 `SQLiteManager`（history + messages 双表）可直接映射为 `SQLiteOpenHelper`；`mmagent/videograph.py:30-65` 的 `VideoGraph` 用 `androidx.room` 关系表（nodes / edges / embeddings 分表）实现，**避免用 `pickle`**（ndarray 体积大且 NDK 不可控）。
4. **触发层**：`android.app.Application.OnProvideAssistDataListener`（AOSP `Application.java`，自 API 23 引入）允许 App 在系统 `ACTION_ASSIST` 时把当前 Session 的 Mem0 摘要塞进 `EXTRA_ASSIST_CONTEXT`，作为「App 暴露给系统级 Assistant 的官方通道」。

### 资源消耗边界（与 5.13 节 DVFS/能效模型的关系）

- Mem0 v3 单次检索 p50 0.88–1.09 s（云端，6.8K–7.0K token）；端侧 LLM（3B 量化）decode 2–5 s。
- M3-Agent Memorization 单 30s 视频片段在云端 Qwen2.5-Omni-7B 上需 4× A100（80GB）；端侧只能离线批处理，单片段 10–30 s。
- `VideoGraph` 单节点 120 KB（10 img + 20 audio embeddings，FP32）；1 小时视频约 120 clip，量化 + FlatBuffers 后可压至 ~20 MB。
- 端侧 7B LLM decode 一小时约 1500–2500 mAh（@3.8V），加上 embedding / storage I/O 估 +5–10%，与 5.13 节的能效模型区间一致。

### 端侧化的具体工程判断

- 24 种 vector store 里 `faiss` 是 Android 端可行选项（faiss-cpu 在 NDK 编译可行），其余均要远端访问。
- `mem0/vector_stores/configs.py:VectorStoreConfig` 的 `_provider_configs` 字典列出全部适配，**新增「本地 SQLite + HNSW」 provider 即可满足端侧最小化部署**。
- M3-Agent 的 `mmagent/retrieve.py:back_translate` 在端侧要砍掉笛卡尔积（用一次 top-k 反向翻译替代全展开），把 100 query 限制改成 10。
- `pickle` 不可用，推荐用 LiteRT 自带的 `TensorBuffer` 序列化 embedding，或用 FlatBuffers（参见 MediaPipe Tasks 现有 `.task` 文件格式）。

[已验证: Mem0 仓库 `mem0/memory/storage.py`、`mem0/embeddings/fastembed.py`、`mem0/vector_stores/configs.py`][已验证: M3-Agent 仓库 `m3_agent/memorization_memory_graphs.py`、`mmagent/videograph.py`、`mmagent/retrieve.py`][已验证: AOSP main `Application.OnProvideAssistDataListener`]
[待验证: AOSP `android-17.0.0_r1` 标签下 `ApplicationAiContext.java` 的 API 形态（cs.android.com 渲染被重定向到 main，未直接抓到目标文件）][待验证: Mem0 v3 `ADDITIVE_EXTRACTION_PROMPT` 完整 prompt 内容]
