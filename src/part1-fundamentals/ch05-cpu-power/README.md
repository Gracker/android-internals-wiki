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

- [5.1 Linux 调度、EAS 与大小核架构](01-linux-eas-big-little-scheduling.md)
- [5.2 DVFS、Thermal 与 Android 功耗管理](02-dvfs-thermal-android-power.md)
- [5.3 后台执行、任务调度与 App Hibernation](03-background-jobs-hibernation.md)
- [5.4 ADPF 自适应性能框架](04-adpf.md)
- [5.5 Android 端侧 AI Runtime 与 NPU 性能边界](05-ondevice-ai-runtime-npu.md)
- [5.6 移动端 LLM 推理的 DVFS 与能效边界](06-mobile-llm-dvfs-energy.md)
- [5.7 SensorService 与传感器批处理功耗模型](07-sensorservice-batching-power.md)
- [5.8 CPU Cache 友好代码与数据布局优化](08-cpu-cache-friendly-code-data-layout.md)
- [5.9 Bluetooth LE Audio 延迟与功耗性能](09-bluetooth-le-audio-performance.md)

## 按现象选择入口

| 现象 | 阅读顺序 | 先找什么证据 |
| --- | --- | --- |
| 主线程处于可运行状态却迟迟不执行 | 5.1 | 唤醒事件、运行队列等待、策略/优先级、CPU 放置 |
| CPU 频率低或升频迟 | 5.2 → 5.4 | 利用率、调频策略、请求/当前/最高频率、温控上限、性能提示 |
| 灭屏后仍耗电或任务不执行 | 5.2 → 5.3 | 系统挂起、WakeLock、待机分组、任务原因、应用休眠 |
| 游戏持续降帧 | 5.4 → 5.2 → 渲染章节 | 帧/图形处理器耗时、目标/实际耗时、温控余量、温控状态 |
| 端侧模型慢且耗电高 | 5.5 → 5.6 → 5.2 | 委托器/后端提供者、复制/同步栅栏、CPU/GPU/NPU 耗时、温控、能量 |
| 周期性传感器或音频唤醒 | 5.2 → 5.7/5.9 | 唤醒源、批处理/硬件卸载、无线电/音频周期、空闲态驻留时间 |
| 高速缓存未命中或伪共享 | 5.8 → Simpleperf/Perfetto 章节 | 工作负载、PMU 事件、线程/CPU、数据布局与重复基准测试 |

短时间性能跟踪可以定位一次可运行等待，但不能代表长期耗电；Batterystats 可以观察长时间的电量归因，却无法解释某一帧为什么错过完成时限。实验窗口要匹配问题的时间尺度，并固定工作负载、起始温度、供电、屏幕、网络和刷新率。

## 本轮整合说明

第二轮审阅把本章从 17 篇收敛为 9 篇：调度/EAS/大小核、DVFS/Thermal/系统功耗、后台执行/任务调度分别形成三条主责任链；ADPF、端侧 AI、移动端 LLM、传感器、CPU Cache 和 LE Audio 保持独立。详细旧路径映射见 [`metadata/content-consolidation-audit.md`](../../../metadata/content-consolidation-audit.md)。
