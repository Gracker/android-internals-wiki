# 第 5 章：CPU 调度与能耗管理

线程运行得慢，可能是已经处于可运行状态（runnable）却仍在运行队列中等待，也可能来自 CPU 放置选择、频率限制、空闲态唤醒、内存停顿、温控上限或后台执行政策。只看 CPU 使用率，无法区分这些原因。

本章以 Android 17 / API 37 / `android-17.0.0_r1` 和 Android common kernel `android17-6.18-2026-06_r6` 为上界。Power HAL、GPU/NPU 调频器（governor）、SoC 电源域、温控策略和硬件计数器通常由厂商实现，因此设备结论需要源码、配置与性能跟踪（trace）共同证明。

## 控制面与证据

| 控制面 | 决定什么 | 主要证据 |
| --- | --- | --- |
| 调度器（Scheduler） | 可运行任务何时、在哪个 CPU 上执行 | `sched_switch`、`sched_wakeup`、可运行等待时长、CPU 迁移 |
| CPUFreq / devfreq | CPU 或其他性能域请求哪个工作档位 | 利用率、调频策略、请求/当前/最高频率、驱动与固件 |
| CPUIdle / 系统挂起 | 空闲 CPU 或整机进入多深的低功耗状态 | `cpu_idle`、唤醒源、各空闲态驻留时间、`suspend_resume` |
| Power / ADPF | Framework 与应用如何表达场景和完成时限 | 模式/短时加速、HintSession 目标/实际耗时、厂商跟踪事件 |
| 温控（Thermal） | 温度压力如何限制 CPU/GPU 与系统工作 | 温度、严重级别、冷却状态、频率上限 |
| 后台政策 | 应用何时可以在后台继续工作 | Doze、待机分组、任务原因/配额、前台服务（FGS）、低功耗待机（LPS）、应用休眠 |

这些控制面不是固定的串行调用链。调度器选择任务；schedutil 可以根据 PELT 负载跟踪和 UClamp 利用率约束请求频率；Power HAL 可能改变厂商策略；温控机制还能压低可用上限。CPUIdle 处理没有可运行任务的时段，DVFS（动态电压频率调节）则调整运行时的电压与频率，二者不能混为一个“省电开关”。

## 连续阅读目录

- [5.1 Linux 进程调度基础](01-linux-scheduling.md)：公平调度、按虚拟截止时间选择任务的 EEVDF、调度类、优先级、Android 任务配置文件、可扩展调度器 `sched_ext` 与 Perfetto。
- [5.2 EAS 能量感知调度](02-eas.md)：能量模型（Energy Model）、CPU 算力、PELT 负载跟踪、UClamp 利用率约束、唤醒放置与系统过载边界。
- [5.3 大小核架构](03-big-little.md)：CPU 拓扑、算力、任务迁移与“同频不同效”的测量边界。
- [5.4 DVFS 与功耗管理](04-dvfs.md)：CPUFreq/schedutil、性能档位 OPP、Power HAL、BPF 性能目标、GPU/DDR 调频，以及性能/活动监控单元 PMU/AMU。
- [5.5 Thermal 管控](05-thermal.md)：内核温控、Thermal HAL、Framework 聚合、冷却设备、应用降载与可复现实验。
- [5.6 Android 功耗管理](06-android-power.md)：PowerManagerService、唤醒锁（WakeLock）、CPUIdle、系统挂起、低功耗待机（Low Power Standby）与 Batterystats。
- [5.7 后台执行限制与优化](07-background-execution.md)：Doze 休眠模式、应用待机/自适应电量、前台服务、闹钟、缓存进程冻结与 Android 17 后台音频。
- [5.8 JobScheduler/WorkManager 调度与后台任务性能](08-jobscheduler-workmanager-performance.md)：约束、按实际运行时间计算的配额、并发槽位、生命周期、调试接口与任务选型。
- [5.9 ADPF 自适应性能框架](09-adpf.md)：Android 动态性能框架（ADPF）、性能提示（Performance Hint）、`WorkDuration`、CPU/GPU 性能余量与温控余量（headroom）、游戏模式与端侧 AI 线程边界。
- [5.10 端侧 AI 推理性能：NPU/GPU 加速与 LiteRT 管线](10-ondevice-ml-inference-performance.md)：LiteRT/NNAPI、CPU/GPU/NPU、缓冲区与同步栅栏、内存、基准测试和观测方法。
- [5.11 移动端 LLM 推理的 DVFS 与能效边界](11-mobile-llm-dvfs-energy.md)：提示词预填充/逐 token 解码、内存带宽、token 延迟、温控与能量实验。
- [5.12 Android 17 ML Runtime 与 NPU 访问边界](12-android17-ml-runtime-npu-boundary.md)：NPU 功能声明、LiteRT 后端提供者、提前/即时编译（AOT/JIT）、部分委托执行与迁移。
- [5.13 SensorService 与传感器批处理功耗模型](13-sensorservice-batching-power.md)：传感器中枢、先进先出队列（FIFO）、批处理延迟、唤醒型传感器与系统挂起。
- [5.14 CPU Cache 友好代码与数据布局优化](14-cpu-cache-friendly-code-data-layout.md)：访问局部性、伪共享（false sharing）、结构体数组（AoS）/按字段拆分的数组（SoA）、DEX 布局、Simpleperf 与 PMU。
- [5.15 系统托管 GenAI：AICore、OnDeviceIntelligence 与资源竞争](15-genai-app-integration-performance.md)：系统托管的生成式 AI（GenAI）、AICore、ML Kit GenAI、OnDeviceIntelligence、资源归属与前台限制。
- [5.16 Bluetooth LE Audio 延迟与功耗性能](16-bluetooth-le-audio-performance.md)：LC3 音频编解码、ISO 等时传输、路由、硬件卸载（offload）、扫描、广播音频与两端功耗。
- [5.17 Android 17 App Hibernation 状态机与冷启动恢复性能](17-android17-app-hibernation-performance.md)：用户级/全局休眠、权限与存储影响、恢复路径和冷启动实验。

## 按现象选择入口

| 现象 | 阅读顺序 | 先找什么证据 |
| --- | --- | --- |
| 主线程处于可运行状态却迟迟不执行 | 5.1 → 5.2 → 5.3 | 唤醒事件、运行队列等待、策略/优先级、CPU 放置 |
| CPU 频率低或升频迟 | 5.4 → 5.5 → 5.9 | 利用率、调频策略、请求/当前/最高频率、温控上限、性能提示 |
| 灭屏后仍耗电或任务不执行 | 5.6 → 5.7 → 5.8 → 5.17 | 系统挂起、WakeLock、待机分组、任务原因、应用休眠 |
| 游戏持续降帧 | 5.9 → 5.5 → 渲染章节 | 帧/图形处理器耗时、目标/实际耗时、温控余量、温控状态 |
| 端侧模型慢且耗电高 | 5.10 → 5.11 → 5.12 → 5.15 | 委托器/后端提供者、复制/同步栅栏、CPU/GPU/NPU 耗时、温控、能量 |
| 周期性传感器或音频唤醒 | 5.6 → 5.13/5.16 | 唤醒源、批处理/硬件卸载、无线电/音频周期、空闲态驻留时间 |
| 高速缓存未命中或伪共享 | 5.14 → Simpleperf/Perfetto 章节 | 工作负载、PMU 事件、线程/CPU、数据布局与重复基准测试 |

短时间性能跟踪可以定位一次可运行等待，但不能代表长期耗电；Batterystats 可以观察长时间的电量归因，却无法解释某一帧为什么错过完成时限。实验窗口要匹配问题的时间尺度，并固定工作负载、起始温度、供电、屏幕、网络和刷新率。

## 本轮整合说明

本章由 38 篇正文整合为 17 篇。版本综述回到各机制文章；EEVDF、`sched_ext`、PELT/AMU/PMU、Power HAL/schedutil、GPU headroom（性能余量）与 PowerManagerService（PMS）/CPUIdle 内容并入 5.1～5.6、5.9；FGS、自适应电量、LPS 和后台音频分别并入 5.6、5.7；两篇 JobScheduler 专题并入 5.8；异构 AI/ADPF 并入 5.9～5.10；OnDeviceIntelligence 并入 5.15；跨应用 Agent、Binder 与 App Performance Score 回到第 16、1、26 章的唯一正文。详细旧路径映射见 [`metadata/content-consolidation-audit.md`](../../../metadata/content-consolidation-audit.md)。
