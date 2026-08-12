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

端侧 LLM 推理同时占用 CPU、GPU 或 NPU、内存带宽以及散热预算。其计算形态会随阶段变化：prefill 负责处理输入上下文，decode 负责持续生成输出；模型加载、后端编译、采样和 KV cache 管理又会在两段计算之外引入额外开销。只看平均 CPU 利用率或一次 tokens/s，通常不足以解释用户感受到的等待、抖动和发热。

平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`，内核锚点为 `android17-6.18-2026-06_r6`。工程问题分为四项：

1. TTFT、TPOT 与 energy-per-token 应该怎样定义和测量；
2. EAS、CPUFreq、GPU/内存 DVFS、ADPF 和温控分别负责什么；
3. 普通应用能调节哪些负载参数，哪些操作只属于系统、厂商或 root 实验；
4. 怎样判断优化是在节能，还是把耗电和热限频推迟到下一轮请求。

EAS、CPUFreq、ADPF、端侧 AI 后端和温控的基础分别见 5.2、5.4、5.9、5.10、5.5 节。这里将这些机制放到同一条 LLM 请求时间线上。

## 先统一指标和测量边界

LLM 性能指标只有在起止点一致时才能比较。建议在应用侧给每个请求分配 ID，并记录下列时间戳：

- `t_request`：请求进入推理 API；
- `t_prefill_start`、`t_prefill_end`：后端开始和结束处理输入；
- `t_first_token`：第一个可交付 token 到达应用；
- `t_i`：第 `i` 个输出 token 到达应用；
- `t_done`：生成结束、取消或报错。

常见指标可按下式计算：

```text
TTFT = t_first_token - t_request

TPOT = (t_last_token - t_first_token) / (N_output - 1)
       仅在 N_output > 1 时定义

request_energy_per_output_token
    = (E_done - E_request) / N_output
```

这组定义把 tokenizer、排队和冷启动都计入 TTFT，适合描述用户等待。如果需要分析后端，应同时报告 `t_prefill_end - t_prefill_start`，并把模型文件读取、权重映射、delegate 初始化、图编译和首轮 kernel warm-up 分开。不能把预热后的后端时间称为冷启动 TTFT。

TPOT 是整段 decode 的平均值，容易掩盖卡顿。工程报告还应给出 inter-token latency 的 P50、P95、最大值和随时间变化的曲线。采用 speculative decoding、并行解码或一次提交多个 token 的运行时，输出回调与硬件 kernel 可能不再一一对应；此时仍可用 token 到达间隔描述用户体验，但不能据此推断每个 token 的底层执行周期。

能耗也需要明确分母：

- `prefill_energy / input_token` 反映长 prompt 的处理成本；
- `decode_energy / output_token` 适合比较连续生成；
- `request_energy / output_token` 包含加载、prefill、decode 和应用开销；
- `joules / successful_request` 还能覆盖取消、超时与失败带来的浪费。

不同口径可以同时报告，不能把其中一个简称为“模型能效”后横向比较。

## 一次请求经过哪些硬件

典型端侧推理请求会经过多个执行层。具体分工由模型格式、运行时和 delegate 决定，下面的表格用于建立排查顺序，不代表每台设备都采用同一后端。

| 层级 | 常见工作 | 容易漏看的成本 |
|---|---|---|
| 应用与 tokenizer | 文本预处理、tokenize、流式回调、UI 更新 | Java/Kotlin 分配、日志、频繁跨语言调用 |
| CPU 运行时 | 图调度、采样、算子补位、GPU/NPU 命令提交 | 单线程串行段、线程迁移、锁与唤醒 |
| GPU | 张量乘加、向量算子、部分 attention 与后处理 | 短 kernel 间隙、命令提交等待、频率爬升 |
| NPU | 支持范围内的编译图与加速算子 | 图切分、回退、编译缓存、厂商驱动约束 |
| DRAM / 系统缓存 | 读取权重和 KV cache，交换各后端数据 | 带宽竞争、容量压力、数据布局转换 |
| 存储 | 首次读取模型与编译产物 | 冷页、解压、校验、低存储空间 |
| 显示、网络及其他进程 | 展示流式文本、下载上下文、系统并发任务 | 全机功耗与模型功耗混在一起 |

### Prefill：并行度较高，但先别假定它只受算力限制

Prefill 会一次处理较长的输入序列，张量运算通常比单 token decode 更容易形成批量工作。随着 prompt 增长，计算量、权重读取、attention 中间数据和 KV cache 写入都可能增加。GPU 或 NPU 利用率高并不自动证明瓶颈在计算单元；内存带宽、图切分、首次编译和 CPU 提交也可能拉长 TTFT。

### Decode：周期性明显，但并非恒定周期

传统自回归 decode 每轮根据已有上下文生成后续 token。每轮之间存在数据依赖，批量并行空间通常小于 prefill。CPU 可能负责采样、运行时调度与命令提交，加速器读取权重和不断增长的 KV cache。token 周期还会受到采样策略、停止条件、上下文长度、图回退和系统抢占影响。

因此，decode 常呈现“CPU 短暂工作—提交—等待加速器—读取结果—采样”的交替形态。某个硬件在一个采样窗口内不够忙，不等于它的频率不会影响端到端 token 间隔。

## Android 17 的调度与频率控制分工

讨论 LLM DVFS 时，最容易出现的概念错误是把 EAS、CPUFreq governor 和 Power HAL 写成同一个控制器。Android 17 的执行路径应分层理解。

### EAS 负责 CPU 放置

在 `android17-6.18-2026-06_r6` 中，`kernel/sched/fair.c` 的 `find_energy_efficient_cpu()` 会调用 `compute_energy()`，借助 Energy Model 估算把唤醒任务放到不同 CPU 后的能量变化。它回答的是“这个任务放在哪个可用 CPU 上更合适”。

Energy Model 是估算模型，不是全机功耗计。估算结果还会受到任务利用率、CPU 容量、调度域、CPU 空闲状态、利用率钳制以及厂商扩展影响。它不能看到一次 LLM 请求的 token deadline，也不直接控制 GPU 或内存频率。

### schedutil 与 CPUFreq 负责 CPU 频率

同一内核锚点下，`kernel/sched/cpufreq_schedutil.c` 的 schedutil governor 从调度器利用率推导下一目标频率。`get_next_freq()` 会经过 `map_util_freq()` 一类映射，并考虑策略容量、I/O wait boost、更新速率等条件；Android vendor hook `android_vh_map_util_freq` 允许厂商介入映射。最终频率还受 CPUFreq policy 的 `min` / `max`、`freq_qos` 请求、热限制和硬件可用频点约束。

简化后的关系如下：

```text
任务唤醒
  ├─ EAS / fair scheduler：选择可运行的 CPU
  └─ scheduler utilization → schedutil / vendor policy
                         → CPUFreq target
                         → policy、QoS、thermal clamp
                         → 硬件频点
```

选核与选频会互相影响：任务落到哪个 cluster 会改变可用容量和频点，频率又会影响执行时间。不过，两条路径必须分开观察。看到任务迁核后变快，不能直接归因为 governor 升频；看到 `cpu_frequency` 变化，也不能断言 EAS 改了放置决策。

### GPU 与内存 DVFS 多由厂商实现

Linux 提供 devfreq 框架和通用 governor，但 Android 设备的 GPU、互连、内存控制器、带宽投票以及相关 telemetry 往往由 SoC 厂商驱动和策略管理。AOSP 没有面向普通应用的统一 API，让应用指定 GPU 或 DRAM 频点。某台设备上的 sysfs 节点、tracepoint 或频率表不能当作跨设备接口。

GPU delegate、NPU delegate 或厂商运行时可能通过驱动提交工作，并间接触发性能状态变化。是否升频、升到哪里、维持多久，仍受厂商实现、系统功耗模式和热预算约束。

### Power HAL、ADPF 与 Thermal 是约束和提示层

Android 17 的 AIDL `IPower` 支持创建 hint session，框架把应用线程组、目标工作时长及实际工作时长交给 Power HAL。系统和厂商可以用这些信息调节调度、频率或其他策略，也可以在不支持相应能力时忽略提示。提示不会给应用返回一个已保证的 CPU/GPU 频点。

温度达到限制后，thermal cooling device、CPUFreq/Devfreq 限制、Power HAL 和厂商策略都可能降低性能上限。此时增加负载、放宽线程数或反复请求性能提示，可能只会增加排队与功耗，无法越过热限制。

## 为什么独立的利用率反馈会误读 LLM decode

利用率驱动的策略并没有“失效”；它只掌握局部信号。LLM decode 在以下条件下容易让局部信号和端到端目标错位：

1. **串行依赖**：CPU 必须等待加速器结果后才能采样和发起下一轮，任一侧的空闲可能代表依赖等待；
2. **短 burst**：短 kernel 在采样窗口内被平均，频率还没升稳，工作已经结束；
3. **跨设备交接**：CPU 提交慢会让 GPU 出现空洞，GPU 执行慢又会让 CPU 睡眠，两边的平均利用率都可能不高；
4. **状态切换成本**：升降频、唤醒 cluster、加载图和缓存恢复都需要时间；
5. **带宽瓶颈**：计算单元频率提高后，如果权重或 KV cache 受带宽限制，延迟改善会很小；
6. **热与功率上限**：观测到的低频可能来自 thermal clamp 或平台功率预算，并非 governor 对利用率判断偏低；
7. **后台竞争**：相机、显示、网络、系统服务和其他应用会共同消耗 CPU、内存带宽与热余量。

所以，诊断顺序应从 token 时间线出发，再关联 CPU 放置、CPU/GPU 频率、调度、内存、功耗和温度。单张 utilization 截图无法证明升频策略有问题。

## FUSE 论文：有边界的 Pixel 7 案例

论文 *Dissecting the Impact of Mobile DVFS Governors on LLM Inference Performance and Energy Efficiency*（arXiv:2507.02135）提供了一个很有价值的案例：独立 governor 选择的频率组合，可能偏离某个 LLM 请求在给定能耗预算下的低延迟组合。

先看实验边界：

- 设备为已 root 的 Pixel 7 / Pixel 7 Pro，SoC 是 Tensor G2，GPU 是 Mali-G710 MP7；
- 系统为 Android 13，CPU 使用论文所述 `sched-pixel` / EAS 配置，GPU governor 为 `quickstep`，内存策略为 `interactive`；
- 推理运行时为带 OpenCL / CLBlast 后端的 llama.cpp，论文原型基于 llama.cpp `b2202`；
- 设备拆机并绕过电池供电，屏幕关闭，Monsoon 以 0.2 ms 间隔采样；
- 实验通过 root 接口把 min/max 设为同一值来固定频率；
- FUSE 评估包含 4-bit 模型和 ShareGPT 请求子集，prompt 与输出长度受到论文设定限制。

在这些条件下，论文报告了以下代表性现象：

| 场景 | governor 观测值 | 固定频率实验 | 论文报告的 TPOT 变化 |
|---|---:|---:|---:|
| TinyLlama decode / GPU | 约 424.4 MHz | 848 MHz | 降低 41.0% |
| StableLM decode / GPU | 约 411.4 MHz | 762 MHz | 降低 34.6% |
| TinyLlama decode / CPU | 约 1130.8 MHz | 2252 MHz | 降低 13.2% |
| StableLM decode / CPU | 约 1038.8 MHz | 2401 MHz | 降低 13.4% |

TinyLlama 的 GPU 案例中，论文给出的 TPOT 从 215.1 ms 降到 126.9 ms，单 token 能耗从 396.5 mJ 变为 402.7 mJ。这个数据说明，在该设备与该请求上，缩短执行时间抵消了大部分瞬时功率增加。它不支持“GPU 总应该跑高频”这一结论。

FUSE 把 CPU、GPU 与内存频率组合一起搜索，再按请求特征选择组合。论文在其工作负载上报告：相同 energy-per-token 条件下，TTFT 平均改善 7.0%～16.9%，TPOT 平均改善 25.4%～36.8%。

这项研究能支持的工程判断是：需要联合测量 CPU、GPU、内存和请求阶段，独立利用率策略可能错过更好的组合。它不能直接外推到：

- Android 17 的调度器和厂商策略；
- Snapdragon、MediaTek 或其他 Tensor 代际；
- 当前 LiteRT-LM、其他 llama.cpp 版本或不同算子后端；
- NPU delegate；
- 未 root 的量产应用；
- 屏幕点亮、联网、边充边测等不同整机条件。

复现论文时，应把它当作 root 实验机上的机制验证。把固定频率脚本放入量产应用既不可移植，也会绕过平台功耗与温控约束。

## 普通应用、系统组件与 root 实验的权限边界

| 能力 | 普通应用 | 系统 / 厂商组件 | root 实验机 |
|---|---|---|---|
| 选择模型、量化、上下文长度、采样参数 | 可以 | 可以 | 可以 |
| 选择运行时公开的 CPU/GPU/NPU 后端 | 可以，受设备支持限制 | 可以 | 可以 |
| 调整线程数、批次与请求队列 | 可以 | 可以 | 可以 |
| 创建 ADPF hint session | API 与设备支持时可以 | 可以 | 可以 |
| 查询公开 thermal status / thermal headroom | API 支持时可以 | 可以访问更多内部信号 | 可以 |
| 调用 AIDL Power HAL | 不可以直接调用 | 可以按平台权限和架构调用 | 可实验，不代表应用接口 |
| 固定 CPU/GPU/内存频率 | 不可以 | 厂商策略可管理 | 常可通过 debug/sysfs 实验 |
| 修改 governor、调度器或 thermal 配置 | 不可以 | 平台集成阶段可以 | 可实验 |
| 读取原始 PowerStats / 厂商能量通道 | 通常受权限限制 | 可以按权限获取 | 常可获取 |

普通应用的优化重点是改变工作负载形状并向系统描述期限，而不是指定硬件频率。系统团队才适合评估 Power HAL、调度参数、GPU/内存策略和 thermal 配置。两类结论要分开记录，避免把 root 实验结果写成 SDK 能力。

## 用 ADPF 描述周期工作

Android 17 的 `android.os.PerformanceHintManager` 为一组相互关联的长生命周期线程创建 `Session`：

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

这段代码表达“这些线程周期性完成一轮工作，希望在目标时间内结束”。`createHintSession()` 可能返回 `null`，应用必须保留没有 hint session 时的正确执行路径。线程 ID 应来自负责推理工作的长期 worker，不能填 UI 线程 ID 来替代真实执行线程。

Android 17 源码中的主要操作包括：

- `updateTargetWorkDuration(long)`：目标发生变化时更新期限；
- `reportActualWorkDuration(long)`：每个周期报告实际时长；
- `setThreads(int[])`：长期 worker 集合变化时更新线程；
- `setPreferPowerEfficiency(boolean)`：在对应 flagged API 可用时表达能效偏好；
- `reportActualWorkDuration(WorkDuration)`：在对应 flagged API 可用时报告总时长及 CPU/GPU 时长；
- `close()`：工作结束后释放 session。

LLM decode 有周期性，可以把稳定的 token 或一组 token 作为工作周期，但需要满足三个条件：

1. session 覆盖长期 worker，不要每生成一个 token 就创建和销毁 session；
2. target 来自产品可接受的 token 周期或吞吐目标，不能长期填一个无法达到的极小值；
3. actual duration 的边界固定，不能这轮只量 GPU、下一轮又把采样与 UI 回调计入。

Prefill 往往是一段较长的批量工作。若运行时没有稳定、可重复的 prefill chunk 周期，硬把整段 prefill 当作高频周期上报会削弱信号含义。可以为具有明确边界的 prefill chunk 使用独立 session，也可以只为 decode 建立 session，并用 trace 单独评估 TTFT。

目标时长也不应等同于“越短越好”。如果产品只要求稳定达到某个 token 速率，可以把 target 设在体验预算附近，并在温度升高、电量策略变化或后台化时放宽。`setPreferPowerEfficiency(true)` 表达的是偏好，最终选择仍由平台决定；调用前还要检查当前 SDK、flag 和设备能力。

普通应用不要直接调用 `IPower.createHintSession()`。Framework API 负责身份、权限、生命周期与兼容处理，AIDL HAL 是系统和厂商之间的接口。

## 从模型和运行时减少无效工作

频率策略只能在既定工作量上做取舍。对普通应用，先减少每个请求必须完成的计算和数据搬运，通常比寻找某个频点更稳定。

### 量化与模型尺寸

权重位宽降低通常能减少模型体积和权重带宽，但收益取决于后端是否有对应的高效 kernel。某种量化格式文件更小，不代表设备上的 delegate 一定更快。需要同时检查：

- 后端是否原生支持该位宽与分组方式；
- 不支持的算子是否回退 CPU；
- 反量化是否增加临时内存和计算；
- 精度、输出稳定性和安全评测是否仍满足产品要求。

### KV cache 与上下文长度

未压缩 KV cache 的主体容量可用下式做一阶估算：

```text
KV bytes ≈ 2 × layers × tokens
           × num_kv_heads × head_dim × bytes_per_element
```

系数 2 对应 key 与 value。采用 GQA/MQA、分页 cache、量化 cache、滑动窗口或特殊布局后，公式参数和额外元数据都会变化。上下文越长，cache 容量与访问成本通常越高，也更容易触发内存压力。应记录运行时真实分配和 RSS/PSS，不能只用模型配置推算。

可以从产品侧控制历史消息长度、检索片段数量、system prompt 大小和最大输出 token。截断规则要与语义评测一起验证，避免用明显的回答质量下降换取漂亮的 tokens/s。

### 后端选择与图切分

CPU、GPU、NPU 的名字不能代表整张图都在该硬件执行。应从运行时日志、delegate 诊断或厂商工具确认：

- 哪些算子被加速后端接收；
- 是否发生 CPU 回退和频繁同步；
- 权重格式是否匹配目标后端；
- 编译缓存是否命中；
- 首次请求和后续请求是否使用同一路径。

后端切换需要按设备型号、模型和版本建立基线。GPU 在某台设备上更快，不意味着它在短 prompt、低电量或持续温控场景中仍然更省电。

### 模型与 session 生命周期

如果内存预算允许，应复用模型映射、已编译图、tokenizer 和长期运行的 session，避免每次对话重复加载与编译。复用同时需要处理：

- 前后台生命周期与进程回收；
- 多会话 KV cache 的上限和淘汰；
- 模型升级后的缓存失效；
- 取消请求后 worker、buffer 和 hint session 的清理；
- 低内存回调和设备热状态变化。

### LiteRT-LM 的版本边界

LiteRT-LM 是 Google AI Edge 在 AOSP 之外维护的端侧生成式 AI 运行时项目。其公开仓库提供 Kotlin / C++ 接口、`.litertlm` 模型格式以及 CPU、GPU、NPU 后端支持说明；具体硬件覆盖受版本、模型和设备影响。应用应锁定经过验证的 LiteRT-LM 版本和模型产物，并保存运行时日志。

`android-17.0.0_r1` 只能锚定 Android 平台 API、Framework 与 HAL，不能用来锚定 LiteRT-LM 的仓库版本。阅读 AOSP 源码和阅读 LiteRT-LM release 必须分成两条版本记录。系统服务提供的模型能力也不等同于应用内嵌 LiteRT-LM，二者的模型、权限、更新和资源管理边界不同，详见 5.10 节。

## 建立可复现的能效实验

### 1. 固定工作负载组合

至少记录以下维度：

- 设备型号、SoC、系统 build、内核 build；
- 模型名称、精度、量化格式和文件哈希；
- 运行时、delegate、驱动版本；
- prompt token 数、目标输出 token 数和采样参数；
- CPU 线程数、affinity 或运行时调度选项；
- 冷启动、热启动、首轮 warm-up 是否计入；
- 屏幕亮度、网络、充电状态、后台进程；
- 环境温度、测试开始时的电池温度和 thermal status。

结果要按这些维度分组。把 32-token prompt 和 2K-token prompt 的 TTFT 求平均，得到的数字很难指导优化。

### 2. 用应用 trace 标记请求阶段

为请求、prefill、decode、sampling、回调和模型加载添加 Perfetto slice。token 事件应带请求 ID 与序号，避免并发请求互相覆盖。标记只围绕阶段边界，不要为每个微小函数生成大量 trace 事件，以免测量本身改变 token 周期。

### 3. 同时采集 CPU 频率变化与轮询值

Perfetto 的 `power/cpu_frequency` tracepoint 只在频率变化时产生事件，trace 开始时不保证给出初始频率。`linux.sys_stats` 的 `cpufreq_period_ms` 可以补充周期轮询。下面是用于分析的精简配置片段：

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

100 ms 是观察长期趋势的起点，不适合解析单个很短的 kernel。要看短周期，应结合频率变化事件、调度 slice 和应用 token 标记，同时评估 trace 开销。GPU、NPU、互连和内存频率数据源依赖设备，采集前要确认 counter 名称、单位和更新语义。

### 4. 明确整机功耗和部件能量的区别

Perfetto `android.power` 可采集电池计数器：

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

电池电流和电压代表整机，屏幕、调制解调器与后台任务都会进入结果。USB 充电会改变电池计数器含义，边充边测的数据不能直接与放电测试比较。`collect_power_rails` 依赖设备的 `IPowerStats` 实现，很多量产设备不会提供可用的 rail；没有 rail 数据时应报告“不可用”，不能用估算值填补。

Android 17 的 `IPowerStats` 把能量消费者和能量通道作为厂商定义的数据返回。累计能量使用微瓦秒等明确单位，调用方还要处理结果暂不可用、UID 归因缺失以及通道名称因设备而异等情况。原始 HAL 数据通常不属于普通应用权限范围。

使用外置功耗仪时，要记录供电路径、采样频率、电压设置、电池是否旁路、屏幕与 ADB 状态。外置仪器能提高采样一致性，但拆机旁路电池后的结论仍属于实验条件，不能与正常电池供电数据混用。

### 5. 积分、基线与重复试验

若测得电压 `V(t)` 和电流 `I(t)`，请求窗口能量可近似为：

```text
E_request = ∫ V(t) × I(t) dt
```

电流正负方向由数据源定义，积分前必须核对。若要扣除 idle baseline，应使用相同屏幕、网络、温度和采样配置，在邻近时间测量，并同时保留未扣除的整机能量。baseline subtraction 会放大短请求的误差。

每组配置需要多次重复并随机化顺序，避免所有“高性能配置”都在冷机运行、所有“节能配置”都在热机运行。至少报告样本数、中心趋势、离散程度和失败请求；对长时间测试还应分时间窗口展示。

## 把温控纳入性能结论

短 benchmark 常奖励激进的升频策略，连续对话更容易暴露热约束。一个完整测试应包含：

1. 一组从相同初始温度开始的短请求，用于分析 TTFT 和单轮 decode；
2. 持续多轮或固定时长的 steady-state 测试；
3. thermal status、thermal headroom、CPU/GPU 频率上限和 token 延迟的同轴记录；
4. 进入限制前、限制发生时、限制后的分段统计；
5. 冷却后复测，排除后台任务与偶发驱动错误。

“race to idle”只有在更高瞬时功率被更短执行时间抵消，并且没有提前触发温控或挤压其他部件预算时才有能效优势。判断依据是请求总能量、持续 TPOT、热状态和恢复时间，不是峰值频率。

应用可以按产品目标采取降载措施：

- 缩短允许的上下文或输出上限；
- 降低并发请求数；
- 切换更小模型或更低成本后端；
- 放宽 token 速率目标；
- 在后台或高温时暂停非必要 prefill；
- 提前向用户展示“设备较热，生成速度可能下降”，并支持取消。

thermal headroom 是预测信号，数值方向和可用性要按 API 文档处理。它适合辅助选择负载档位，不能保证未来某一时刻仍有固定频率预算。相关 API 与 Android 17 的阈值语义见 5.5 节。

## 常见现象的排查顺序

| 现象 | 先检查 | 后续验证 |
|---|---|---|
| 冷启动 TTFT 高，热启动正常 | 模型读取、权重映射、图编译、cache 命中 | 分离 I/O、compile 和首轮 kernel slice |
| 冷热 TTFT 都高 | prompt 长度、prefill 后端、CPU 回退 | 固定输入，比较后端覆盖和频率/带宽 |
| 平均 TPOT 尚可，偶发停顿明显 | P95 inter-token latency、线程抢占、GC、回调阻塞 | 对齐 `sched_switch`、GC 与 token 事件 |
| CPU/GPU 利用率都不高但 TPOT 高 | 跨设备等待、短 burst、单线程采样 | 看线程状态、提交间隙和频率变化 |
| 频率提高后速度不变 | 内存带宽、图回退、串行段、thermal clamp | 比较算子时间与 CPU/GPU 上限 |
| 前几轮快，随后持续变慢 | 温度、频率上限、系统 thermal status | 冷却复测并观察限制发生点 |
| tokens/s 提高但能量明显增加 | 请求总时长、瞬时功率与 idle tail | 比较 joules/request 和 joules/token |
| 更换 NPU 后端反而慢 | 图切分、编译、数据转换、CPU fallback | 查看后端日志和冷/热启动差异 |
| 并发吞吐提高但单请求体验变差 | 队列等待、带宽竞争、热预算 | 分开报告吞吐、TTFT、TPOT 和公平性 |

排查时每轮只改变一个主要变量。若同时换模型、delegate、线程数和系统版本，即使结果改善，也无法判断哪个变化产生了作用。

## 发布前检查清单

- [ ] Android 平台结论锚定 `android-17.0.0_r1`；
- [ ] 内核调度与 CPUFreq 结论锚定 `android17-6.18-2026-06_r6`；
- [ ] EAS 选核与 schedutil/CPUFreq 选频已分开解释；
- [ ] GPU、NPU、内存频率数据标明设备和厂商边界；
- [ ] TTFT 的冷/热启动口径明确；
- [ ] TPOT 同时提供 P50/P95 或时间曲线；
- [ ] 能耗分母和采样窗口明确；
- [ ] prompt、输出长度、模型、运行时与 delegate 固定；
- [ ] root 固频实验没有写成普通应用能力；
- [ ] ADPF session 使用长期 worker，target 与 actual 边界一致；
- [ ] Power rail 不可用时没有伪造部件能量；
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
  - hint session channel 与支持信息
- `hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl`
  - energy consumer、energy meter 与 residency 接口

上述平台路径按 `android-17.0.0_r1` 复核。

### Android 17 内核

- `kernel/sched/fair.c`
  - `find_energy_efficient_cpu()`
  - `compute_energy()`
- `kernel/sched/cpufreq_schedutil.c`
  - `get_next_freq()`
  - `map_util_freq()`
  - Android vendor hook `android_vh_map_util_freq`
- `drivers/cpufreq/cpufreq.c`
  - CPUFreq policy 与 QoS 约束
- `drivers/devfreq/`
  - 通用 devfreq 框架；具体 GPU/内存实现需继续查看设备内核

上述内核路径按 `android17-6.18-2026-06_r6` 复核。

### 外部运行时与研究

- LiteRT-LM：<https://github.com/google-ai-edge/LiteRT-LM>
- FUSE 论文：<https://arxiv.org/abs/2507.02135>
- Perfetto CPU frequency：<https://perfetto.dev/docs/data-sources/cpu-freq>
- Perfetto battery counters：<https://perfetto.dev/docs/data-sources/battery-counters>
- Android Performance Hint API：<https://source.android.com/docs/core/perf/performance-hint-api>

LiteRT-LM 和论文各自使用独立版本。它们不随 `android-17.0.0_r1` 标签一起冻结。
