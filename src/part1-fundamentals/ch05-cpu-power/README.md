# 第 5 章：CPU 调度与能耗管理

线程运行得慢，可能来自 runnable 等待、CPU placement、频率限制、idle 唤醒、内存 stall、thermal cap 或后台执行政策。只看 CPU usage，无法区分这些原因。

本章以 Android 17 / API 37 / `android-17.0.0_r1` 和 Android common kernel `android17-6.18-2026-06_r6` 为上界。Power HAL、GPU/NPU governor、SoC 电源域、thermal policy 和硬件计数器常由厂商实现，设备结论需要源码、配置与 trace 共同证明。

## 控制面与证据

| 控制面 | 决定什么 | 主要证据 |
| --- | --- | --- |
| Scheduler | runnable task 何时、在哪个 CPU 运行 | `sched_switch`、`sched_wakeup`、runnable delay、migration |
| CPUFreq / devfreq | 性能域请求哪个工作档位 | utilization、policy、requested/current/max frequency、driver/firmware |
| CPUIdle / suspend | 空闲 CPU 或整机进入多深的低功耗状态 | `cpu_idle`、wakeup source、residency、`suspend_resume` |
| Power / ADPF | Framework 与应用怎样表达场景和 deadline | mode/boost、HintSession target/actual duration、vendor trace |
| Thermal | 温度压力怎样限制 CPU/GPU 与系统工作 | temperature、severity、cooling state、frequency cap |
| Background policy | App 何时可在后台继续工作 | Doze、bucket、job reason/quota、FGS、LPS、hibernation |

这些控制面不是固定串行调用链。调度器选择任务，schedutil 可依据 PELT/UClamp 等信号请求频率，Power HAL 可能改变厂商策略，thermal 还能压低可用上限。CPUIdle 处理没有 runnable work 的时段，不能与 DVFS 混成一个“省电开关”。

## 连续阅读目录

- [5.1 Linux 进程调度基础](01-linux-scheduling.md)：fair/EEVDF、调度类、优先级、Android task profile、`sched_ext` 与 Perfetto。
- [5.2 EAS 能量感知调度](02-eas.md)：Energy Model、capacity、PELT、UClamp、wakeup placement 与 overutilized 边界。
- [5.3 大小核架构](03-big-little.md)：CPU topology、capacity、migration 与“同频不同效”的测量边界。
- [5.4 DVFS 与功耗管理](04-dvfs.md)：CPUFreq/schedutil、OPP、Power HAL、BPF performance target、GPU/DDR 调频与 PMU/AMU。
- [5.5 Thermal 管控](05-thermal.md)：kernel thermal、Thermal HAL、Framework 聚合、cooling device、应用降载与可复现实验。
- [5.6 Android 功耗管理](06-android-power.md)：PowerManagerService、WakeLock、CPUIdle、system suspend、Low Power Standby 与 Batterystats。
- [5.7 后台执行限制与优化](07-background-execution.md)：Doze、App Standby/Adaptive Battery、FGS、Alarm、缓存进程冻结与 Android 17 后台音频。
- [5.8 JobScheduler/WorkManager 调度与后台任务性能](08-jobscheduler-workmanager-performance.md)：约束、elapsed-time quota、并发槽位、生命周期、调试接口与任务选型。
- [5.9 ADPF 自适应性能框架](09-adpf.md)：Performance Hint、`WorkDuration`、CPU/GPU/thermal headroom、Game Mode 与端侧 AI 线程边界。
- [5.10 端侧 AI 推理性能：NPU/GPU 加速与 LiteRT 管线](10-ondevice-ml-inference-performance.md)：LiteRT/NNAPI、CPU/GPU/NPU、buffer/fence、内存、benchmark 与观测。
- [5.11 移动端 LLM 推理的 DVFS 与能效边界](11-mobile-llm-dvfs-energy.md)：prefill/decode、memory bandwidth、token latency、thermal 与能量实验。
- [5.12 Android 17 ML Runtime 与 NPU 访问边界](12-android17-ml-runtime-npu-boundary.md)：NPU feature、LiteRT provider、AOT/JIT、partial delegation 与迁移。
- [5.13 SensorService 与传感器批处理功耗模型](13-sensorservice-batching-power.md)：sensor hub、FIFO、batch latency、wake-up sensor 与 suspend。
- [5.14 CPU Cache 友好代码与数据布局优化](14-cpu-cache-friendly-code-data-layout.md)：locality、false sharing、AoS/SoA、DEX layout、Simpleperf 与 PMU。
- [5.15 系统托管 GenAI：AICore、OnDeviceIntelligence 与资源竞争](15-genai-app-integration-performance.md)：AICore、ML Kit GenAI、OnDeviceIntelligence、资源归属与前台限制。
- [5.16 Bluetooth LE Audio 延迟与功耗性能](16-bluetooth-le-audio-performance.md)：LC3、ISO、路由、offload、扫描、广播音频与两端功耗。
- [5.17 Android 17 App Hibernation 状态机与冷启动恢复性能](17-android17-app-hibernation-performance.md)：用户级/全局休眠、权限与存储影响、恢复路径和冷启动实验。

## 按现象选择入口

| 现象 | 阅读顺序 | 先找什么证据 |
| --- | --- | --- |
| 主线程 runnable 但迟迟不运行 | 5.1 → 5.2 → 5.3 | wakeup、runqueue wait、policy/priority、CPU placement |
| CPU 频率低或升频迟 | 5.4 → 5.5 → 5.9 | util、policy、requested/current/max frequency、thermal cap、hint |
| 灭屏后仍耗电或任务不执行 | 5.6 → 5.7 → 5.8 → 5.17 | suspend、WakeLock、bucket、job reason、hibernation |
| 游戏持续降帧 | 5.9 → 5.5 → 渲染章节 | frame/GPU time、target/actual duration、headroom、thermal |
| 端侧模型慢且耗电高 | 5.10 → 5.11 → 5.12 → 5.15 | delegate/provider、copy/fence、CPU/GPU/NPU time、thermal、energy |
| 周期性传感器或音频唤醒 | 5.6 → 5.13/5.16 | wake source、batch/offload、radio/audio 周期、idle residency |
| Cache miss 或 false sharing | 5.14 → Simpleperf/Perfetto 章节 | workload、PMU event、线程/CPU、数据布局与重复 benchmark |

短 trace 能定位一次 runnable delay，不能代表长期耗电；Batterystats 能观察长时间归因，也不能解释某一帧为什么错过 deadline。实验窗口要匹配问题时间尺度，并固定 workload、温度起点、供电、屏幕、网络和刷新率。

## 本轮收敛说明

本章由 38 篇正文收敛为 17 篇。版本综述回到各机制文章；EEVDF、`sched_ext`、PELT/AMU/PMU、Power HAL/schedutil、GPU headroom 与 PMS/cpuidle 内容并入 5.1～5.6、5.9；FGS、Adaptive Battery、LPS 和后台音频分别并入 5.6、5.7；两篇 JobScheduler 深挖并入 5.8；异构 AI/ADPF 并入 5.9～5.10；OnDeviceIntelligence 并入 5.15；跨应用 Agent、Binder 与 App Performance Score 回到第 16、1、26 章的唯一正文。详细旧路径映射见 [`metadata/content-consolidation-audit.md`](../../../metadata/content-consolidation-audit.md)。
