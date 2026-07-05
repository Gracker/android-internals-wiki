# 第 5 章：CPU 调度与能耗管理

很多性能问题最后都会落到一句很朴素的话上：**线程有没有及时拿到资源。**

这个资源有时是 CPU 时间片，有时是频率，有时是 thermal 预算，有时是后台执行窗口。  
所以一旦开始分析卡顿、启动慢、ANR、功耗，调度和能耗几乎绕不过去。

这一章想讲清楚的是：线程到底怎样被放到不同核心上执行，频率和热控怎样影响它的真实速度，为什么“同样的代码”在不同设备和不同温度下表现会差很多。

调度、频率和热控不是三个独立子系统，而是一个动态平衡系统：

1. **CFS（Completely Fair Scheduler）** 是 Linux 默认进程调度器，按虚拟运行时间公平分配 CPU 时间片。大小核架构出现后，CFS 无法感知核心能效差异，只看“时间公平”。
2. **EAS（Energy Aware Scheduling）** 在 CFS 基础上引入能量模型（EM），唤醒路径上通过 `find_energy_efficient_cpu()` 把任务优先放到能效核，节省功耗。EAS 的有效边界由 overutilized 阈值控制——系统负载过高时 EAS 退让，回退到 CFS 的性能优先策略。
3. **DVFS（Dynamic Voltage and Frequency Scaling）** 根据负载动态调整 CPU/GPU 频率和电压。Android 上通过 `sysfs` 或 `hint` 接口驱动，Perfetto 里对应 CPU frequency 轨道。
4. **Thermal 管控** 监控 SoC 温度，通过 Thermal HAL 和 `thermal-engine` 在温度超限时降频、迁移任务或杀后台进程。Thermal 状态变化直接影响 DVFS 可用的最高频率。

四个子系统形成循环反馈：调度器决定任务放哪个核 → DVFS 根据负载调频 → 温度升高触发 Thermal 降频 → 降频反过来影响调度决策。分析性能问题时，如果只看调度不看频率、只看频率不看温度，容易得出“CPU 没跑满”却找不到原因的结论。

## 本章内容

- Linux 进程调度基础
- EAS 能量感知调度
- 大小核架构
- DVFS 与功耗管理
- Thermal 管控
- Android 功耗管理
- CPU 相关的版本演进

## 阅读建议

- 如果你做的是 App 性能问题排查，`5.1`、`5.4`、`5.5` 最常直接影响判断。
- 如果你更靠近系统或 ROM，`5.2`、`5.3`、`5.4`、`5.5` 会更关键。
- 读这一章时，最好配合 Perfetto 的调度轨道一起看，理解会快很多。

## 参考资料

### Android 17 性能优化：新调度器减少 30% 启动时间
- 来源：https://android-developers.googleblog.com/2026/06/android-17-performance-optimization
- 类型：技术深度分析
- 摘要：Android 17 引入了全新的任务调度器，通过智能优先级算法和延迟启动机制，应用启动时间平均减少 30%。新调度器采用机器学习模型预测用户行为，优先启动高频...
- 入库时间：2026-07-04
- 评分：18/20

### Android 17 不同 SoC 架构下的电池优化策略深度分析
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-05-android17-battery-optimization-soc-architecture-power-management.md
- 类型：DeepResearch 调研结果
- 摘要：分层架构设计（硬件层 Perfetto → 框架层 BatteryManager → 服务层 PMS → 应用层 JobScheduler），SoC 差异化策略（ARM Big.LITTLE / Qualcomm Adreno / MediaTek APU），BatteryCounters proto 指标定义，电源域管理粒度对比。
- 注入时间：2026-07-05
- 价值：提供不同 SoC 厂商电源优化策略的系统性对比，补强 ch05 功耗优化章节参考资料

### Android 17 PowerManagerService × cpuidle menu governor × schedutil 三层协作闭环
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-04-android17-pms-cpuidle-schedutil-closed-loop.md
- 类型：DeepResearch 调研结果
- 摘要：PMS 17 个 DIRTY_* 位掩码 + 10 个 WAKE_LOCK_* 状态聚合、adjustWakeLockSummary 隐含状态推断、IPower AIDL Hint Session、schedutil sugov_get_util() 聚合 uclamp/iowait boost、cpuidle menu governor 6-bucket 预测。源码锚定 android-17.0.0_r1。
- 注入时间：2026-07-05
- 价值：三层协作闭环的源码级剖析，填补 PMS→HAL→内核调度链路空白
