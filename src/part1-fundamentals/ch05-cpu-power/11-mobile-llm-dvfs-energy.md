---

title: "移动端 LLM 推理的 DVFS 与能效边界"
chapter: "5.11"
section: "5.11"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-05-16"
last_verified_against: "AOSP android-16.0.0_r1 + Android 官方文档 + Google AI Edge LLM docs 2026-05-28 + Perfetto docs + arXiv 2507.02135"
confidence: medium
tags: [android, dvfs, eas, adpf, llm, on-device-ai, power]
related_chapters: ["5.2", "5.4", "5.5", "5.9", "5.10", "11.3"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
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
    path: "https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference/android"
  - type: official
    path: "https://github.com/google-ai-edge/mediapipe-samples/blob/main/examples/llm_inference/android/README.md"
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
task9_state: "reviewed"
task2b_state: fixed
---

# 5.11 移动端 LLM 推理的 DVFS 与能效边界

端侧大语言模型（Large Language Model，LLM）推理会同时占用中央处理器（Central Processing Unit，CPU）、图形处理器（Graphics Processing Unit，GPU）或神经网络处理器（Neural Processing Unit，NPU）、内存带宽和设备散热能力。计算方式会随阶段变化：预填充（prefill）负责一次处理输入上下文，解码（decode）负责持续生成输出；模型加载、后端编译、采样和键值缓存（Key-Value cache，KV cache）管理还会在这两段计算之外引入额外开销。只看平均 CPU 利用率或某一次每秒生成 token 数（tokens/s），通常无法解释用户感受到的等待、速度波动和发热。

本文按照 Android 17 / API 37 / `android-17.0.0_r1` 核对平台行为，按照 `android17-6.18-2026-06_r6` 核对内核实现，并讨论四个工程问题：

1. 首个 token 等待时间（Time to First Token，TTFT）、每个输出 token 的平均时间（Time per Output Token，TPOT）与单 token 能耗（energy per token）应该如何定义和测量；
2. EAS、CPU 调频框架（CPUFreq）、GPU / 内存 DVFS、Android 动态性能框架（Android Dynamic Performance Framework，ADPF）和温控分别负责什么；
3. 普通应用能调节哪些负载参数，哪些操作只适用于系统、厂商或取得最高系统权限的 root 实验；
4. 如何判断一次优化确实节能，或只是将耗电和热限频推迟到下一轮请求。

EAS、CPUFreq、ADPF、端侧 AI 后端和温控的基础分别见 5.2、5.4、5.9、5.10、5.5 节。本节将这些机制放到同一条 LLM 请求时间线上观察。

## 先统一指标和测量边界

LLM 性能指标只有在起止点一致时才具有可比性。建议在应用侧为每个请求分配标识符（ID），并记录下列时间戳：

- `t_request`：请求进入推理 API；
- `t_prefill_start`、`t_prefill_end`：后端开始和结束处理输入；
- `t_first_token`：第一个可交付 token（模型处理文本时使用的基本单位）到达应用；
- `t_i`：第 `i` 个输出 token 到达应用；
- `t_done`：生成结束、取消或报错。

下面的公式给出本文采用的 TTFT、TPOT 和单请求每输出 token 能耗定义：

```text
TTFT = t_first_token - t_request

TPOT = (t_last_token - t_first_token) / (N_output - 1)
       仅在 N_output > 1 时定义

request_energy_per_output_token
    = (E_done - E_request) / N_output
```

这里的 TTFT 包括分词器（tokenizer）处理、排队和冷启动，适合描述用户实际等待时间。如果需要分析执行后端，还应报告 `t_prefill_end - t_prefill_start`，并分别测量模型文件读取、权重映射、委托后端（delegate）初始化、计算图编译和首轮计算内核（kernel）预热。不能把预热后的后端时间称为冷启动 TTFT。

TPOT 是整段 decode 的平均值，容易掩盖个别 token 的停顿。工程报告还应给出相邻 token 延迟（inter-token latency）的第 50、95 百分位数（P50、P95）、最大值和随时间变化的曲线。采用推测解码（speculative decoding）、并行解码或一次提交多个 token 的运行时，输出回调与硬件 kernel 可能不再一一对应；此时仍可用 token 到达间隔描述用户体验，但不能据此推断每个 token 在硬件上的执行周期。

能耗也需要明确分母：

- `prefill_energy / input_token` 反映长输入提示（prompt）的处理成本；
- `decode_energy / output_token` 适合比较连续生成；
- `request_energy / output_token` 包含加载、prefill、decode 和应用开销；
- `joules / successful_request` 以焦耳 / 成功请求为单位，还能反映取消、超时与失败造成的能量浪费。

不同口径可以同时报告，不能把其中一个简称为“模型能效”后横向比较。

## 一次请求经过哪些硬件

典型端侧推理请求会经过多个执行层。具体分工由模型格式、运行时和 delegate 决定。下面的表格用于建立排查顺序，不表示每台设备都采用相同后端。

| 层级 | 常见工作 | 容易漏看的成本 |
|---|---|---|
| 应用与 tokenizer | 文本预处理、分词（tokenize）、流式回调、用户界面（UI）更新 | Java / Kotlin 对象分配、日志、频繁跨语言调用 |
| CPU 运行时 | 图调度、采样、算子补位、GPU/NPU 命令提交 | 单线程串行段、线程迁移、锁与唤醒 |
| GPU | 张量乘加、向量算子、部分注意力计算（attention）与后处理 | 短 kernel 间隙、命令提交等待、频率从低档升到高档所需的时间 |
| NPU | 支持范围内的编译图与加速算子 | 图切分、回退、编译缓存、厂商驱动约束 |
| 动态随机存取内存（DRAM）/ 系统缓存 | 读取权重和 KV cache，交换各后端数据 | 带宽竞争、容量压力、数据布局转换 |
| 存储 | 首次读取模型与编译产物 | 尚未进入内存缓存的文件页（冷页）、解压、校验、存储空间不足 |
| 显示、网络及其他进程 | 展示流式文本、下载上下文、系统并发任务 | 全机功耗与模型功耗混在一起 |

### Prefill：并行度较高，但先别假定它只受算力限制

Prefill 会一次处理较长的输入序列，其张量运算通常比单 token decode 更容易形成批量工作。随着 prompt 增长，计算量、权重读取、attention 中间数据和 KV cache 写入都可能增加。GPU 或 NPU 利用率高，不能自动证明瓶颈位于计算单元；内存带宽、计算图分区、首次编译和 CPU 提交也可能延长 TTFT。

### Decode：周期性明显，但并非恒定周期

传统自回归 decode 每轮根据已有上下文生成后续 token。各轮之间存在数据依赖，可批量并行的工作通常少于 prefill。CPU 可能负责采样、运行时调度与命令提交，加速器则读取权重和不断增长的 KV cache。token 周期还会受到采样策略、停止条件、上下文长度、计算图回退和系统抢占影响。

因此，decode 常呈现“CPU 短暂工作—提交—等待加速器—读取结果—采样”的交替过程。某个硬件在一个采样窗口内利用率不高，其运行频率仍可能影响端到端 token 间隔。

## Android 17 的调度与频率控制分工

动态电压频率调节（Dynamic Voltage and Frequency Scaling，DVFS）会按负载与约束调整硬件电压和频率。讨论 LLM DVFS 时，不能把能量感知调度（Energy-Aware Scheduling，EAS）、CPUFreq 调频策略（governor）和电源硬件抽象层（Power HAL）当作同一个控制器。Android 17 的执行路径需要分层理解。

### EAS 负责 CPU 放置

在 `android17-6.18-2026-06_r6` 中，`kernel/sched/fair.c` 的 `find_energy_efficient_cpu()` 会调用 `compute_energy()`，借助能耗模型（Energy Model）估算将刚被唤醒的任务放到不同 CPU 后的能量变化。它回答“这个任务放在哪个可用 CPU 上更合适”。

Energy Model 只用于估算调度选择，不是测量整机功耗的仪器。估算结果还会受到任务利用率、CPU 容量、调度域、CPU 空闲状态、利用率限制（utilization clamping，uclamp）和厂商扩展影响。它不知道一次 LLM 请求的 token 截止时间（deadline），也不直接控制 GPU 或内存频率。

### schedutil 与 CPUFreq 负责 CPU 频率

在同一内核版本中，`kernel/sched/cpufreq_schedutil.c` 的 schedutil governor 根据调度器利用率计算下一个目标频率。`get_next_freq()` 会经过 `map_util_freq()` 等映射，并考虑策略容量、输入输出等待加速（I/O wait boost）、更新速率等条件；Android 厂商钩子（vendor hook）`android_vh_map_util_freq` 允许厂商调整这项映射。最终频率还受 CPUFreq policy 的最低 / 最高值、频率服务质量（`freq_qos`）请求、热限制和硬件可用频点约束。

下面的流程概括选核、选频与最终硬件频点之间的关系：

```text
任务唤醒
  ├─ EAS / fair scheduler：选择可运行的 CPU
  └─ scheduler utilization → schedutil / vendor policy
                         → CPUFreq target
                         → policy、QoS、thermal clamp
                         → 硬件频点
```

这段流程中的选核与选频会互相影响：任务落到哪个 CPU 核簇（cluster）会改变可用容量和频点，频率又会影响执行时间。不过，两条路径必须分开观察。任务迁核后变快，不能直接归因于 governor 升频；看到 `cpu_frequency` 变化，也不能断定 EAS 改变了放置决策。

### GPU 与内存 DVFS 多由厂商实现

Linux 提供设备调频（devfreq）框架和通用 governor，但 Android 设备的 GPU、片上互连、内存控制器、带宽请求，以及相关遥测数据（telemetry），往往由 SoC 厂商驱动和策略管理。Android 开源项目（Android Open Source Project，AOSP）没有让普通应用指定 GPU 或 DRAM 频点的统一 API。某台设备上的 sysfs（内核向用户空间暴露状态和控制项的虚拟文件系统）节点、跟踪点（tracepoint）或频率表，不能当作跨设备接口。

GPU delegate、NPU delegate 或厂商运行时可能通过驱动提交工作，并间接触发性能状态变化。是否升频、升到哪里、维持多久，仍受厂商实现、系统功耗模式和热预算约束。

### Power HAL、ADPF 与 Thermal 是约束和提示层

Android 17 的 Android 接口定义语言（Android Interface Definition Language，AIDL）接口 `IPower` 支持创建性能提示会话（hint session）。Android framework（系统框架）将应用线程组、目标工作时长和实际工作时长交给 Power HAL。系统和厂商可以用这些信息调整调度、频率或其他策略，也可以在不支持相应能力时忽略提示。性能提示不会向应用返回一个得到保证的 CPU / GPU 频点。

温度达到限制后，热冷却设备（thermal cooling device，即系统用来执行降频等降温动作的抽象）、CPUFreq / Devfreq 限制、Power HAL 和厂商策略都可能降低性能上限。此时增加负载、增加线程数或反复发送性能提示，可能只会增加排队与功耗，无法突破热限制。

## 为什么独立的利用率反馈会误读 LLM decode

利用率驱动的策略并没有“失效”，但它只掌握局部信号。LLM decode 在以下条件下容易让局部信号与端到端目标不一致：

1. **串行依赖**：CPU 必须等待加速器结果后才能采样并发起下一轮，任一侧空闲都可能表示正在等待前一阶段；
2. **短时突发（burst）**：短 kernel 的利用率会在采样窗口内被平均；频率尚未稳定升高，工作可能已经结束；
3. **跨设备交接**：CPU 提交慢会让 GPU 暂时没有工作，GPU 执行慢又会让 CPU 休眠，两边的平均利用率都可能不高；
4. **状态切换成本**：升降频、唤醒 cluster、加载计算图和恢复缓存都需要时间；
5. **带宽瓶颈**：计算单元频率提高后，如果权重或 KV cache 受带宽限制，延迟改善会很小；
6. **热与功率上限**：观测到的低频可能来自热限制（thermal clamp）或平台功率预算，不一定是 governor 低估了利用率；
7. **后台竞争**：相机、显示、网络、系统服务和其他应用会共同消耗 CPU、内存带宽与热余量。

因此，诊断应从 token 时间线开始，再关联 CPU 放置、CPU / GPU 频率、调度、内存、功耗和温度。单张利用率（utilization）截图无法证明升频策略存在问题。

## FUSE 论文：有边界的 Pixel 7 案例

论文 *Dissecting the Impact of Mobile DVFS Governors on LLM Inference Performance and Energy Efficiency*（arXiv:2507.02135）提供了一个有明确边界的案例：各 governor 独立选择的频率组合，可能偏离某个 LLM 请求在给定能耗预算下的低延迟组合。FUSE 是论文提出并评估的联合频率选择原型。

先看实验边界：

- 设备为已取得 root 权限的 Pixel 7 / Pixel 7 Pro，片上系统（System on Chip，SoC）是 Tensor G2，GPU 是 Mali-G710 MP7；
- 系统为 Android 13，CPU 使用论文所述 `sched-pixel` / EAS 配置，GPU governor 为 `quickstep`，内存策略为 `interactive`；
- 推理运行时为带 OpenCL / CLBlast 计算后端的 llama.cpp，论文原型基于 llama.cpp `b2202`；
- 设备经过拆机并绕过电池供电，屏幕关闭，Monsoon 外置功耗仪以 0.2 ms 间隔采样；
- 实验通过 root 接口将最低 / 最高频率设为同一值，从而固定频率；
- FUSE 评估包含 4-bit 模型和 ShareGPT 请求子集，prompt 与输出长度受到论文设定限制。

在这些条件下，论文报告了以下代表性现象：

| 场景 | governor 观测值 | 固定频率实验 | 论文报告的 TPOT 变化 |
|---|---:|---:|---:|
| TinyLlama decode / GPU | 约 424.4 MHz | 848 MHz | 降低 41.0% |
| StableLM decode / GPU | 约 411.4 MHz | 762 MHz | 降低 34.6% |
| TinyLlama decode / CPU | 约 1130.8 MHz | 2252 MHz | 降低 13.2% |
| StableLM decode / CPU | 约 1038.8 MHz | 2401 MHz | 降低 13.4% |

TinyLlama 的 GPU 案例中，论文给出的 TPOT 从 215.1 ms 降到 126.9 ms，单 token 能耗从 396.5 mJ 变为 402.7 mJ；mJ 表示毫焦耳。该数据说明，在这台设备与这一请求上，缩短执行时间抵消了大部分瞬时功率增加。它不能支持“GPU 总应保持高频”这一普遍结论。

FUSE 联合搜索 CPU、GPU 与内存频率组合，再按请求特征选择配置。论文在其工作负载上报告：单 token 能耗相同时，TTFT 平均改善 7.0%～16.9%，TPOT 平均改善 25.4%～36.8%。

这项研究能支持的工程判断是：需要联合测量 CPU、GPU、内存和请求阶段，独立利用率策略可能错过更好的组合。它不能直接外推到：

- Android 17 的调度器和厂商策略；
- Snapdragon、MediaTek 或其他 Tensor 代际；
- 当前 LiteRT-LM、其他 llama.cpp 版本或不同算子后端；
- NPU delegate；
- 未 root 的量产应用；
- 屏幕点亮、联网、边充边测等不同整机条件。

复现论文时，应将其视为 root 实验机上的机制验证。固定频率脚本无法移植到普通量产应用，而且会绕过平台功耗与温控约束。

## 普通应用、系统组件与 root 实验的权限边界

| 能力 | 普通应用 | 系统 / 厂商组件 | root 实验机 |
|---|---|---|---|
| 选择模型、量化、上下文长度、采样参数 | 可以 | 可以 | 可以 |
| 选择运行时公开的 CPU/GPU/NPU 后端 | 可以，受设备支持限制 | 可以 | 可以 |
| 调整线程数、批次与请求队列 | 可以 | 可以 | 可以 |
| 创建 ADPF hint session | API 与设备支持时可以 | 可以 | 可以 |
| 查询公开 thermal status / thermal headroom | API 支持时可以 | 可以访问更多内部信号 | 可以 |
| 调用 AIDL Power HAL | 不可以直接调用 | 可以按平台权限和架构调用 | 可实验，不代表应用接口 |
| 固定 CPU/GPU/内存频率 | 不可以 | 厂商策略可管理 | 常可通过调试接口（debug）/ sysfs 实验 |
| 修改 governor、调度器或 thermal 配置 | 不可以 | 平台集成阶段可以 | 可实验 |
| 读取原始 PowerStats / 厂商能量通道 | 通常受权限限制 | 可以按权限获取 | 常可获取 |

普通应用应通过模型、上下文长度、线程数和请求队列等参数改变工作负载，并向系统描述时间目标，而不能指定硬件频率。Power HAL、调度参数、GPU / 内存策略和 thermal 配置适合由系统团队评估。两类结论需要分开记录，避免把 root 实验结果写成软件开发套件（SDK）能力。

## 用 ADPF 描述周期工作

Android 17 的 `android.os.PerformanceHintManager` 可以为一组相互关联、长期存在的线程创建性能提示 `Session`。下面的代码创建会话并报告一次 decode 的实际工作时长：

```java
PerformanceHintManager manager =
        context.getSystemService(PerformanceHintManager.class);

long targetNanos = initialDecodeTargetNanos;
PerformanceHintManager.Session session =
        manager.createHintSession(workerTids, targetNanos);

if (session != null) {
    session.reportActualWorkDuration(actualDecodeNanos);
}
```

这段代码表达“这些线程会周期性完成一轮工作，并希望在目标时间内结束”。`createHintSession()` 可能返回 `null`，因此应用必须保留没有 hint session 时仍可正确执行的路径。线程 ID 应来自长期负责推理的工作线程（worker），不能用 UI 线程 ID 代替真实执行线程。

Android 17 源码中的主要操作包括：

- `updateTargetWorkDuration(long)`：目标发生变化时更新期限；
- `reportActualWorkDuration(long)`：每个周期报告实际时长；
- `setThreads(int[])`：长期 worker 集合变化时更新线程；
- `setPreferPowerEfficiency(boolean)`：在相应的 flagged API（由平台功能开关控制是否可用的 API）可用时表达能效偏好；
- `reportActualWorkDuration(WorkDuration)`：在相应 flagged API 可用时报告总时长及 CPU / GPU 时长；
- `close()`：工作结束后释放 session。

LLM decode 具有周期性，可以把一个稳定的 token 生成过程或一组 token 作为工作周期，但需要满足三个条件：

1. session 覆盖长期 worker，不能每生成一个 token 就创建和销毁 session；
2. target 来自产品可接受的 token 周期或吞吐目标，不能长期填一个无法达到的极小值；
3. actual duration 的边界固定，不能这轮只量 GPU、下一轮又把采样与 UI 回调计入。

Prefill 往往是一段较长的批量工作。如果运行时没有稳定、可重复的 prefill 分块（chunk）周期，强行将整段 prefill 当作高频周期上报，会使信号难以解释。可以为边界明确的 prefill chunk 使用独立 session，也可以只为 decode 建立 session，并用性能跟踪（trace）单独评估 TTFT。

目标时长也不是越短越好。如果产品只要求稳定达到某个 token 速率，可以将 target 设在体验预算附近，并在温度升高、电量策略变化或应用进入后台时适当放宽。`setPreferPowerEfficiency(true)` 只表达偏好，最终选择仍由平台决定；调用前还要检查当前 SDK、功能开关（flag）和设备能力。

普通应用不应直接调用 `IPower.createHintSession()`。Framework API 负责身份、权限、生命周期与版本兼容处理，AIDL HAL 则是系统与厂商实现之间的接口。

## 从模型和运行时减少无效工作

频率策略只能在既定工作量上作取舍。对普通应用而言，优先减少每个请求必须完成的计算和数据传输，通常比寻找某个固定频点更稳定。

### 量化与模型尺寸

降低权重位宽，即用更少的二进制位表示权重，通常能减小模型体积和权重带宽需求，但收益取决于后端是否有相应的高效 kernel。某种量化格式的文件更小，不表示设备上的 delegate 一定更快。需要同时检查：

- 后端是否原生支持该位宽与分组方式；
- 不支持的算子是否回退 CPU；
- 反量化（将低位宽数值转换为计算所需格式）是否增加临时内存和计算；
- 精度、输出稳定性和安全评测是否仍满足产品要求。

### KV cache 与上下文长度

下面的公式用于粗略估算未压缩 KV cache 的主体容量：

```text
KV bytes ≈ 2 × layers × tokens
           × num_kv_heads × head_dim × bytes_per_element
```

公式中的系数 2 对应键（key）和值（value）。采用分组查询注意力（Grouped-Query Attention，GQA）、多查询注意力（Multi-Query Attention，MQA）、分页 cache、量化 cache、滑动窗口或特殊布局后，公式参数和额外元数据都会变化。上下文越长，cache 容量与访问成本通常越高，也更容易触发内存压力。应记录运行时真实分配、常驻集大小（RSS）和比例集大小（PSS），不能只根据模型配置推算。

产品可以控制历史消息长度、检索片段数量、系统提示词（system prompt）大小和最大输出 token 数。截断规则要与语义评测一起验证，避免以明显降低回答质量为代价换取更高的 tokens/s。

### 后端选择与图切分

选择 CPU、GPU 或 NPU 后端，不表示整张计算图都会在相应硬件上执行。应通过运行时日志、delegate 诊断或厂商工具确认：

- 哪些算子被加速后端接收；
- 是否发生 CPU 回退，即不受加速器支持的部分转由 CPU 执行，以及是否存在频繁同步；
- 权重格式是否匹配目标后端；
- 编译缓存是否命中；
- 首次请求和后续请求是否使用同一路径。

切换后端前，需要按设备型号、模型和版本建立对照基线。GPU 在某台设备上更快，不表示它在短 prompt、低电量或持续受温控限制时仍然更省电。

### 模型与 session 生命周期

如果内存预算允许，应复用模型映射、已编译计算图、tokenizer 和长期运行的 session，避免每次对话都重复加载与编译。复用时还需处理：

- 前后台生命周期与进程回收；
- 多会话 KV cache 的容量上限和淘汰策略；
- 模型升级后的缓存失效；
- 取消请求后 worker、缓冲区（buffer）和 hint session 的清理；
- 低内存回调和设备热状态变化。

### LiteRT-LM 的版本边界

LiteRT-LM 是 Google AI Edge 在 AOSP 之外维护的端侧生成式 AI 运行时项目。其公开仓库提供 Kotlin / C++ 接口、`.litertlm` 模型格式，以及 CPU、GPU、NPU 后端支持说明；具体硬件覆盖受版本、模型和设备影响。应用应固定经过验证的 LiteRT-LM 版本和模型产物，并保存运行时日志。

`android-17.0.0_r1` 只能确定 Android 平台 API、Framework 与 HAL 的版本，不能用来确定 LiteRT-LM 仓库版本。AOSP 源码和 LiteRT-LM 发布版本（release）必须分别记录。系统服务提供的模型能力也不等同于应用内嵌 LiteRT-LM；二者的模型、权限、更新和资源管理边界不同，详见 5.10 节。

## 建立可复现的能效实验

### 1. 固定工作负载组合

至少记录以下维度：

- 设备型号、SoC、系统构建版本（build）、内核 build；
- 模型名称、精度、量化格式和文件哈希；
- 运行时、delegate、驱动版本；
- prompt token 数、目标输出 token 数和采样参数；
- CPU 线程数、CPU 亲和性（affinity，即线程允许运行在哪些 CPU 上）或运行时调度选项；
- 冷启动、热启动、首轮预热（warm-up）是否计入；
- 屏幕亮度、网络、充电状态、后台进程；
- 环境温度、测试开始时的电池温度和热状态（thermal status）。

结果要按这些维度分组。将 32-token prompt 和 2K-token prompt 的 TTFT 混合求平均，所得数值很难用于指导优化。

### 2. 用应用 trace 标记请求阶段

为请求、prefill、decode、采样（sampling）、回调和模型加载添加 Perfetto 时间区间（slice）。token 事件应包含请求 ID 与序号，避免并发请求互相覆盖。只在阶段边界记录事件，不要为每个很小的函数生成大量 trace 事件，以免测量本身改变 token 周期。

### 3. 同时采集 CPU 频率变化与轮询值

Perfetto 的 `power/cpu_frequency` 跟踪点（tracepoint）只在频率变化时产生事件，trace 开始时不保证给出初始频率。`linux.sys_stats` 的 `cpufreq_period_ms` 可以补充周期性读取的频率值。下面是同时采集频率变化、CPU 空闲、调度事件和 100 ms 频率轮询的精简配置：

```protobuf
buffers {
  size_kb: 65536
  fill_policy: RING_BUFFER
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
    }
  }
}

data_sources {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      cpufreq_period_ms: 100
    }
  }
}
```

这段配置使用环形缓冲区（ring buffer），数据写满后会覆盖旧数据。100 ms 适合作为观察长期趋势的起点，不适合解析单个很短的 kernel。分析短周期时，应结合频率变化事件、调度 slice 和应用 token 标记，同时评估 trace 本身的开销。GPU、NPU、互连和内存频率数据源依赖设备，采集前要确认计数器（counter）的名称、单位和更新含义。

### 4. 明确整机功耗和部件能量的区别

下面的 Perfetto `android.power` 配置每 250 ms 采集电量百分比、电流、电压等电池计数器，并请求采集部件能量轨道（power rails）：

```protobuf
data_sources {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 250
      battery_counters: BATTERY_COUNTER_CHARGE
      battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
      battery_counters: BATTERY_COUNTER_CURRENT
      battery_counters: BATTERY_COUNTER_VOLTAGE
      collect_power_rails: true
    }
  }
}
```

这段配置中的电池电流和电压代表整机，屏幕、蜂窝通信模块（调制解调器）与后台任务都会计入结果。USB 充电会改变电池计数器的含义，边充电边测试的数据不能直接与放电测试比较。`collect_power_rails` 依赖设备的 `IPowerStats` 实现，很多量产设备不会提供可用的部件能量轨道（rail）；没有 rail 数据时应报告“不可用”，不能用估算值填补。

Android 17 的 `IPowerStats` 将能量消费者和能量通道作为厂商定义的数据返回。累计能量使用微瓦秒等明确单位；调用方还要处理结果暂不可用、缺少按用户标识符（User Identifier，UID）归因，以及通道名称因设备而异等情况。原始 HAL 数据通常不在普通应用的权限范围内。

使用外置功耗仪时，要记录供电路径、采样频率、电压设置、电池是否被旁路、屏幕状态与 Android 调试桥（ADB）连接状态。外置仪器能提高采样一致性，但拆机并旁路电池后的结论仍只适用于相应实验条件，不能与正常电池供电数据混用。

### 5. 积分、基线与重复试验

若测得随时间变化的电压 `V(t)` 和电流 `I(t)`，可以用下面的积分近似计算请求窗口能量：

```text
E_request = ∫ V(t) × I(t) dt
```

公式表示把每个时刻的功率 `V(t) × I(t)` 按时间累加。电流正负方向由数据源定义，积分前必须核对。如果要扣除空闲基线（idle baseline），应使用相同的屏幕、网络、温度和采样配置，在相近时间测量，并同时保留未扣除的整机能量。基线扣除（baseline subtraction）会放大短请求的误差。

每组配置都需要多次重复，并随机安排测试顺序，避免所有“高性能配置”都在设备尚未升温时运行，而所有“节能配置”都在设备已经升温时运行。至少报告样本数、中心趋势、离散程度和失败请求；长时间测试还应按时间窗口分别展示结果。

## 把温控纳入性能结论

短时间基准测试（benchmark）往往让激进升频策略表现更好，连续对话则更容易暴露热约束。一个完整测试应包含：

1. 一组从相同初始温度开始的短请求，用于分析 TTFT 和单轮 decode；
2. 持续多轮或固定时长的稳态（steady-state）测试；
3. thermal status、thermal headroom、CPU / GPU 频率上限和 token 延迟的同一时间轴记录；
4. 进入限制前、限制发生时、限制后的分段统计；
5. 冷却后复测，排除后台任务与偶发驱动错误。

“尽快完成后进入空闲”（race to idle）只有在更高瞬时功率被更短执行时间抵消，并且没有提前触发温控或占用其他部件预算时，才有能效优势。判断依据是请求总能量、持续 TPOT、热状态和恢复时间，不能只看峰值频率。

应用可以按产品目标采取降载措施：

- 缩短允许的上下文或输出上限；
- 降低并发请求数；
- 切换更小模型或更低成本后端；
- 放宽 token 速率目标；
- 在后台或高温时暂停非必要 prefill；
- 提前向用户展示“设备较热，生成速度可能下降”，并支持取消。

热余量（thermal headroom）是预测信号，其数值方向和可用性要按 API 文档处理。它适合辅助选择负载档位，但不能保证未来某一时刻仍有固定的频率预算。相关 API 与 Android 17 的阈值含义见 5.5 节。

## 常见现象的排查顺序

| 现象 | 先检查 | 后续验证 |
|---|---|---|
| 冷启动 TTFT 高，热启动正常 | 模型读取、权重映射、计算图编译、缓存（cache）命中 | 分开测量输入输出（I/O）、编译（compile）和首轮 kernel slice |
| 冷热 TTFT 都高 | prompt 长度、prefill 后端、CPU 回退 | 固定输入，比较后端覆盖和频率 / 带宽 |
| 平均 TPOT 尚可，偶发停顿明显 | P95 inter-token latency、线程抢占、垃圾回收（GC）、回调阻塞 | 对齐 `sched_switch`、GC 与 token 事件 |
| CPU / GPU 利用率都不高但 TPOT 高 | 跨设备等待、短 burst、单线程采样 | 查看线程状态、提交间隙和频率变化 |
| 频率提高后速度不变 | 内存带宽、计算图回退、串行阶段、thermal clamp | 比较算子时间与 CPU / GPU 上限 |
| 前几轮快，随后持续变慢 | 温度、频率上限、系统 thermal status | 冷却复测并观察限制发生点 |
| tokens/s 提高但能量明显增加 | 请求总时长、瞬时功率与任务结束后的空闲尾部功耗（idle tail） | 比较焦耳 / 请求（joules/request）和焦耳 / token（joules/token） |
| 更换 NPU 后端反而慢 | 计算图分区、编译、数据转换、CPU 回退（fallback） | 查看后端日志和冷 / 热启动差异 |
| 并发吞吐提高但单请求体验变差 | 队列等待、带宽竞争、热预算 | 分开报告吞吐、TTFT、TPOT 和公平性 |

排查时每轮只改变一个主要变量。如果同时更换模型、delegate、线程数和系统版本，即使结果改善，也无法判断是哪项变化产生了作用。

## 发布前检查清单

- [ ] Android 平台结论已按 `android-17.0.0_r1` 复核；
- [ ] 内核调度与 CPUFreq 结论已按 `android17-6.18-2026-06_r6` 复核；
- [ ] EAS 选核与 schedutil / CPUFreq 选频已分开解释；
- [ ] GPU、NPU、内存频率数据标明设备和厂商边界；
- [ ] TTFT 的冷 / 热启动口径明确；
- [ ] TPOT 同时提供 P50 / P95 或时间曲线；
- [ ] 能耗分母和采样窗口明确；
- [ ] prompt、输出长度、模型、运行时与 delegate 固定；
- [ ] root 固频实验没有写成普通应用能力；
- [ ] ADPF session 使用长期 worker，target 与 actual 边界一致；
- [ ] Power rail 不可用时，没有用估算值冒充部件能量；
- [ ] 持续测试包含 thermal status/headroom 与频率上限；
- [ ] 性能收益通过回答质量、失败率和取消路径验证。

## 版本边界与源码索引

### Android 17 平台

- `frameworks/base/core/java/android/os/PerformanceHintManager.java`
  - `createHintSession()`
  - `Session.updateTargetWorkDuration()`
  - `Session.reportActualWorkDuration()`
  - `Session.setThreads()`
  - flagged `Session.setPreferPowerEfficiency()`
  - flagged `Session.reportActualWorkDuration(WorkDuration)`
- `hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl`
  - `createHintSession()`
  - `createHintSessionWithConfig()`
  - hint session 通道（channel）与支持信息
- `hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl`
  - 能量消费者（energy consumer）、能量计量器（energy meter）与驻留时间（residency）接口

上述平台路径按 `android-17.0.0_r1` 复核。

### Android 17 内核

- `kernel/sched/fair.c`
  - `find_energy_efficient_cpu()`
  - `compute_energy()`
- `kernel/sched/cpufreq_schedutil.c`
  - `get_next_freq()`
  - `map_util_freq()`
  - Android 厂商钩子（vendor hook）`android_vh_map_util_freq`
- `drivers/cpufreq/cpufreq.c`
  - CPUFreq policy 与服务质量（Quality of Service，QoS）约束
- `drivers/devfreq/`
  - 通用 devfreq 框架；具体 GPU/内存实现需继续查看设备内核

上述内核路径按 `android17-6.18-2026-06_r6` 复核。

### 外部运行时与研究

- LiteRT-LM：<https://github.com/google-ai-edge/LiteRT-LM>
- FUSE 论文：<https://arxiv.org/abs/2507.02135>
- Perfetto CPU frequency：<https://perfetto.dev/docs/data-sources/cpu-freq>
- Perfetto battery counters：<https://perfetto.dev/docs/data-sources/battery-counters>
- Android Performance Hint API：<https://source.android.com/docs/core/perf/performance-hint-api>

LiteRT-LM 和论文各自使用独立版本，不会随 `android-17.0.0_r1` 标签固定在同一版本。
