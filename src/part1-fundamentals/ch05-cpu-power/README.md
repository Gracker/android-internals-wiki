# 第 5 章：CPU 调度与能耗管理

线程运行得慢，可能来自 runnable 等待、CPU placement、频率限制、idle 唤醒、内存 stall、thermal cap 或后台执行政策。只看 CPU usage，无法区分这些原因。

复核锚点如下：

- platform：Android 17 / API 37 / `android-17.0.0_r1`；
- kernel：`android17-6.18-2026-06_r6`；
- 调度器、CPUFreq、CPUIdle 与 thermal 的公共语义按固定 kernel tag 核对；
- Power HAL、GPU/NPU governor、SoC 电源域和 thermal policy 常有厂商实现，设备行为需要源码、配置和 trace 共同证明。

## 1. 五个相互作用的控制面

| 控制面 | 主要对象 | 决定什么 | 常用证据 |
|---|---|---|---|
| CPU scheduler | fair/RT/DL class、EEVDF、PELT、uclamp、EAS | 哪个 runnable task 在哪个 CPU 上运行 | `sched_switch`、`sched_wakeup`、runnable delay、migration、util/capacity |
| CPUFreq | cpufreq policy、schedutil、driver、OPP | 一个 policy domain 当前可用频率 | `cpu_frequency`、policy、util、iowait boost、thermal cap |
| CPUIdle | idle state、governor、driver | 空闲 CPU 进入多深的低功耗状态 | `cpu_idle`、wake source、exit latency、residency |
| Power/ADPF | Power HAL、mode/boost、hint session、uclamp/vendor hook | 向系统表达场景与工作时限 | power mode/boost、ADPF target/actual duration、vendor trace |
| Thermal | sensor、thermal zone、cooling device、Thermal HAL | 温度压力如何限制 CPU/GPU/设备能力 | temperature、thermal status、cooling state、frequency cap |

这些控制面不会组成一条固定调用链。调度器放置任务，schedutil 可用 PELT/util 信号请求频率，Power HAL 可能改变 uclamp 或厂商参数，thermal 还能压低 policy 上限。CPUIdle 处理没有 runnable work 的时段，与 DVFS 的频率选择也要分开。

## 2. Android 17 调度基线

### 2.1 Fair class 已使用 EEVDF

旧文章常把 Linux 普通任务调度概括为“CFS 按 vruntime 选最小值”。`android17-6.18-2026-06_r6` 的 fair scheduler 已采用 EEVDF 选择 eligible entity 和 virtual deadline。CFS 的权重、虚拟时间、PELT、负载均衡等基础仍在，但选择模型不能停留在旧红黑树叙述。

分析应用卡顿时，先看目标线程是否 runnable：

- running：线程正在 CPU 上执行；
- runnable：具备运行条件，正在 runqueue 等待；
- sleeping/blocking：等待锁、futex、Binder、I/O、timer 或其他事件；
- throttled/capped：可能受 cgroup、uclamp、thermal 或频率上限影响。

只有 runnable wait 才直接属于 CPU 调度等待。阻塞态时间要回到对应 wait reason。

### 2.2 EAS 是 fair wakeup placement 的一部分

EAS 使用 Energy Model、CPU capacity、task utilization、uclamp 和 domain 状态评估候选 CPU。它不是与 CFS/EEVDF 并列的独立 scheduler class。

系统处于 overutilized 状态时，energy-aware placement 可以停用；后续仍由 fair scheduler 的 placement/load-balance 逻辑处理。把这段写成“回退到性能优先 CFS”会夸大实现语义。

### 2.3 DVFS、Power Hint 与 thermal cap

CPUFreq governor 根据 utilization 和 policy 选择频率请求，driver 再映射到硬件支持的 performance state。Power HAL mode/boost 或 ADPF hint session 可以影响系统策略，但公开 hint 不等于应用直接指定 CPU/GPU 频率。

thermal framework 与设备 cooling policy 可以压低 CPU/GPU 上限。此时 utilization 不满、频率也不高，仍可能是 cap 或 memory stall。需要同时检查 requested/current/max frequency、thermal status 和 runnable delay。

## 3. 时间尺度决定分析方法

| 时间尺度 | 常见问题 | 适合的观察 |
|---|---|---|
| 微秒—毫秒 | wakeup delay、抢占、migration、idle exit | 单线程 sched slice、wakeup→running、CPU idle/frequency |
| 一帧 | UI/RenderThread/GPU deadline | FrameTimeline、线程状态、频率、thermal、fence |
| 数秒 | boost/hint、频率爬升、任务突发 | power/ADPF trace、cpufreq、load、binder/I/O |
| 数分钟 | thermal soak、battery drain、后台配额 | temperature/cooling、energy counter、BatteryStats、JobScheduler |
| 数小时—天 | standby、hibernation、usage bucket | App Standby、Doze、Low Power Standby、job/alarm history |

短 trace 能证明一次调度延迟，不能代表长期电量。BatteryStats 或整段耗电也不能定位某一帧的 runnable wait。实验窗口应与问题时间尺度匹配。

## 4. 内容索引

### 4.1 调度、拓扑、频率、idle 与 thermal

- [5.1 Linux 进程调度基础](01-linux-scheduling.md)：scheduler class、线程状态、优先级、runqueue 与 trace。
- [5.2 EAS 能量感知调度](02-eas.md)：Energy Model、capacity、utilization、uclamp 与 overutilized 边界。
- [5.3 大小核架构](03-big-little.md)：CPU topology、capacity 与 migration，不用“大核必快”替代测量。
- [5.4 DVFS 与功耗管理](04-dvfs.md)：CPUFreq、schedutil、OPP、iowait boost 与频率观测。
- [5.5 Thermal 管控](05-thermal.md)：thermal zone、cooling device、HAL 与性能上限。
- [5.6 Android 功耗管理](06-android-power.md)：PowerManagerService、wake lock、Power HAL、Doze 与 BatteryStats。
- [5.7 CPU 版本演进](07-cpu-evolution.md)：按 kernel/platform tag 对照 scheduler 与 power 接口。
- [5.31 Android 17 EEVDF](31-android17-eevdf-scheduler.md)：从 CFS 基础对象进入 EEVDF eligible/deadline 选择。

### 4.2 深入 thermal、SoC 与调频边界

- [5.12 Thermal 管控深入](12-thermal-management-deep-dive.md)：kernel thermal、Thermal HAL、cooling device 与 ADPF 反馈。
- [5.21 SoC 厂商电池优化架构](5.21-android17-battery-optimization-soc-architecture.md)：区分 AOSP 接口与 Qualcomm/MediaTek/其他厂商实现。
- [5.22 IPower HAL 与 schedutil 协作边界](5.22-android17-soc-vendor-power-hal-schedutil-loop.md)：mode/boost、hint session、uclamp/vendor hook 和 governor。
- [5.28 PELT、AMU/PMU 与调频事实核查](5.28-android17-pelt-boost-revert-amu-pmu-microarch-frequency-limiting.md)：区分 mainline、Android common 与 vendor extension。
- [5.29 GPU DVFS Headroom 与 PowerAdvisor](5.29-android17-gpu-dvfs-headroom-power-advisor.md)：GPU/vendor counter、SurfaceFlinger PowerAdvisor 与证据缺口。
- [5.32 Linux 6.10 BPF/DVFS 版本边界](5.32-linux-610-bpf-dvfs-schedutil-loop.md)：历史 kernel 资料不能覆盖当前 `android17-6.18-2026-06_r6`，BPF 控频还需目标设备实现。

### 4.3 后台执行、JobScheduler 与省电状态

- [5.8 后台执行限制](08-background-execution.md)：Doze、App Standby、后台 service 与系统限制。
- [5.10 JobScheduler/WorkManager](10-jobscheduler-workmanager-performance.md)：constraint、quota、batch、expedited work 与进程生命周期。
- [5.17 FGS 类型与后台性能](17-fgs-type-declaration-background-performance.md)：foreground service type、权限和启动限制。
- [5.21 Adaptive Battery 与 App Standby Bucket](21-adaptive-battery-app-standby-coordination.md)：usage bucket、job/alarm quota 与状态变化。
- [5.23 JobScheduler 系统节流](23-android17-jobscheduler-system-throttling.md)：quota controller、device state、connectivity、battery 与 execution limit。
- [5.24 App Hibernation](24-android17-app-hibernation-performance.md)：hibernation、权限重置、存储与冷启动恢复。
- [5.25 Low Power Standby](25-low-power-standby-background-performance.md)：网络、wake lock 与豁免边界。
- [5.26 JobSchedulerService CPU quota](05.26-android17-jobscheduler-service-cpu-quota.md)：辨别公开 JobScheduler quota、execution time 与材料中的“CPU 时间配额”命名。
- [5.23 后台音频与 LE Audio power source](5.23-android17-background-audio-hardening-leaudio-power-source.md)：音频 FGS、路由、codec/offload 与后台限制。

Foreground service 不保证更高 CPU 优先级，wake lock 也不保证最高频率。它们改变生命周期或睡眠条件，scheduler、DVFS 与 thermal 仍按各自策略工作。

### 4.4 ADPF、端侧 ML 与异构负载

- [5.9 ADPF](09-adpf.md)：PerformanceHintManager、hint session、target duration 与 actual work duration。
- [5.11 端侧 AI 推理性能](11-ondevice-ml-inference-performance.md)：TFLite/NNAPI delegate、CPU/GPU/NPU 与数据搬运。
- [5.13 移动端 LLM 的 DVFS 与能效](13-mobile-llm-dvfs-energy.md)：prefill/decode 阶段、memory bandwidth、thermal 与 token latency。
- [5.14 Android 17 ML Runtime/NPU 边界](14-android17-ml-runtime-npu-boundary.md)：公共 API、runtime/provider、driver 与设备能力。
- [5.16 GPU/NPU 异构负载调度](16-gpu-npu-heterogeneous-scheduling.md)：队列、fence、frequency、memory 与归因。
- [5.19 端侧 AI 与 ADPF](5.19-ondevice-ai-adpf-intelligent-scheduling.md)：应用如何报告工作时限，以及平台没有公开自动模型调度器的边界。
- [5.20 GenAI 应用集成](20-genai-app-integration-performance.md)：AICore/Google Intelligence API 的可用性、版本与资源竞争。
- [5.30 OnDeviceIntelligence 框架](5.30-android17-ondevice-intelligence-framework-performance.md)：service/provider、模型下载、inference session 与隔离。
- [5.21 跨应用 Agent 系统原语](5.21-cross-app-agent-system-primitive.md)：Accessibility、VoiceInteraction、AppFunction 等公开边界。

“NPU 执行”不能由线程名或模型类型推断。delegate/provider 选择、driver queue、buffer copy、频率和功耗计数都要在目标设备上确认。

### 4.5 传感器、音频与持续工作负载

- [5.15 SensorService 与 batching](15-sensorservice-batching-power.md)：sensor hub、FIFO、batch latency、wake-up sensor 与功耗。
- [5.22 Bluetooth LE Audio](22-bluetooth-le-audio-performance.md)：codec、isochronous transport、offload、buffer 与 radio/audio 功耗。

持续工作负载应同时记录 duty cycle、batch/offload 状态、wake source、CPU idle residency 和设备温度。只比较平均 CPU usage 容易漏掉周期性唤醒。

### 4.6 CPU cache、PSS 与性能归因

- [5.18 Cache 友好代码与数据布局](18-cpu-cache-friendly-code-data-layout.md)：working set、locality、false sharing、benchmark 与 PMU。
- [5.18 CPU cache locality/PSS](5.18-android17-cpu-cache-locality-pss-accounting.md)：区分 cache line、virtual memory page 与 PSS 分摊。
- [5.33 App Performance Score 归因](5.33-android17-performance-score-attribution-sourcecode.md)：样本池、分层指标与归因边界。

PMU counter、CPU cache miss、PSS 和耗电属于不同测量域。关联分析要共享相同时间窗口与 workload，不能把 PSS 变化直接解释为 cache miss 原因。

## 5. 按现象选择阅读顺序

| 现象 | 阅读顺序 | 优先证据 |
|---|---|---|
| 主线程 runnable 但迟迟不运行 | 5.1 → 5.31 → 5.2 | wakeup、runqueue wait、priority、CPU placement、capacity |
| CPU frequency 低 | 5.4 → 5.5 → 5.12 → 5.22 | util、requested/current/max frequency、thermal cap、power mode |
| 启动快慢波动 | 5.1 → 5.4 → 5.5 → 启动章节 | runnable/blocking、frequency、thermal、I/O/page fault |
| 游戏或渲染持续降帧 | 5.9 → 5.12 → 5.29 → 渲染章节 | frame/GPU time、ADPF、temperature、GPU/CPU cap |
| 后台任务延迟 | 5.8 → 5.10 → 5.21 → 5.23/5.25 | bucket、constraint、quota、Doze/LPS、job history |
| 端侧模型慢且耗电高 | 5.11 → 5.13 → 5.14 → 5.16 | delegate/provider、copy、CPU/GPU/NPU time、thermal、energy |
| 周期性唤醒耗电 | 5.6 → 5.15/5.22 | wake source、alarm/sensor/radio batch、idle residency |

实验时固定 workload、屏幕/网络、温度起点、充电状态和刷新率。对比设备还要记录 SoC、kernel、governor、Power HAL 与 vendor build；“同频率”也可能对应不同 IPC、cache、memory bandwidth 和 thermal 条件。

## 6. 固定源码入口

- [kernel `sched/fair.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)：fair scheduler、EEVDF、PELT、EAS 与 load balance；
- [kernel `cpufreq_schedutil.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/cpufreq_schedutil.c)、[`drivers/cpufreq/`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpufreq/)：schedutil 与 CPUFreq driver；
- [kernel `drivers/cpuidle/`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/cpuidle/)：idle core、governor 与 driver；
- [kernel `drivers/thermal/`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/thermal/)：thermal zone 与 cooling device；
- [`PowerManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/PowerManagerService.java)：wakefulness、wake lock、user activity 与 power state；
- [`IPower.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/aidl/android/hardware/power/IPower.aidl)：Power HAL mode、boost 与 hint session；
- [`PerformanceHintManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PerformanceHintManager.java)：ADPF 应用接口；
- [`IThermal.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/thermal/aidl/android/hardware/thermal/IThermal.aidl)：Thermal HAL 接口；
- [`JobSchedulerService.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java)：job lifecycle、controller 与 execution。

这些入口描述 AOSP 与 Android common kernel 的公共行为。调优结论还要核对目标设备的 Energy Model、capacity、uclamp/cgroup、cpufreq driver、OPP、Power HAL、thermal 配置和 GPU/NPU vendor implementation。
