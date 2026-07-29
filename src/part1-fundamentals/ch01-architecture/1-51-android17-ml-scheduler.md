---
title: "Android 17 ML 驱动任务调度器"
chapter: "1.51"
status: deprecated
applicable_versions: "Android 17 (API 37)"
tags: [任务调度, 机器学习, EAS, EEVDF, CPU性能]
related_chapters: ["1.43", "5.1", "8.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-03"
gap_source: "AOSP结构"
---
> ⚠️ **本节已废弃 (deprecated 2026-07-04)**：与 1.43 内容重复。



# 1.51 Android 17 ML 驱动任务调度器

<!-- outline-start -->
## 要点

### 🔹 LSTM 预测引擎架构
- 任务执行时间序列的 LSTM 模型
- 历史行为数据的特征提取算法
- 预测结果的置信度评估机制
- 预测错误的自适应修正策略

### 🔹 多因素加权调度算法
- CPU 使用率权重计算
- IO 等待时间权重因子
- 电池状态权重配置
- 用户交互优先级权重

### 🔹 A/B 测试调优框架
- 实验组/对照组的划分策略
- 调度算法的实时切换机制
- 性能指标的量化评估
- 渐进式部署的安全边界

### 🔹 性能基准测试体系
- 调度延迟基准测试
- 响应时间测量方法
- 功耗性能权衡分析
- 多设备一致性验证

### 🔹 智能调度决策引擎
- 实时负载感知机制
- 任务优先级动态调整
- 资源竞争的仲裁策略
- 长期任务规划的优化

## 扩展

### 🔸 机器学习模型部署
- 模型大小与内存占用优化
- 推理延迟的实时监控
- 模型热更新的无缝切换
- 设备差异化的模型选择

### 🔸 调度策略可观测性
- 调度决策的日志记录
- 性能异常的检测算法
- 用户反馈的收集机制
- 策略效果的量化展示

### 🔸 边缘场景处理
- 低电量模式下的调度优化
- 高负载场景的降级策略
- 实时任务的优先级保证
- 后台任务的公平调度

<!-- outline-end -->

> 本页已废弃。上方历史提纲为流水线追踪而保留，其中列出的 LSTM 预测器、多因素 ML 打分、模型热更新和平台 A/B 切换框架没有 Android 17 AOSP 证据。请勿把提纲当作平台能力说明。

## 核查结论

基于平台 `android-17.0.0_r1`、内核 `android17-6.18-2026-06_r6` 和 Android 17 官方发布资料，AOSP 没有名为 “ML Scheduler” 的通用任务调度组件，也没有一套用 LSTM 同时调度 Activity、Service、Job、Binder 事务与 Linux runnable task 的公开协议。提纲中的模型结构、置信度、在线修正、设备模型选择和实验组切换均缺少类名、接口、源码路径或可重复实验，不能写成 Android 17 特性。

Android 17 中能够核验的是多套职责分离的机制：

| 调度对象 | 可核验机制 | 能说明什么 |
| --- | --- | --- |
| 应用后台工作 | JobScheduler controllers、quota、standby bucket、idle 与网络约束 | Job 在哪些条件下获得运行资格 |
| 进程资源资格 | AMS、OomAdjuster、进程状态与 task profile | 进程重要性、回收顺序及资源分组 |
| 可周期提示的线程 | ADPF `PerformanceHintManager` 与 Power HAL | 应用报告目标和实测工作时长后，设备策略如何响应 |
| CPU runnable task | Linux fair scheduler / EEVDF、EAS、PELT、uclamp、schedutil | 线程进入可运行状态后如何选任务、选核与调频 |
| 产品定制策略 | OEM 服务、vendor hook、私有模型 | 只对具体设备与源码版本成立，不能外推为 API 37 契约 |

JobScheduler 的 prefetch 任务可能使用 UsageStats 提供的预计启动时间，但 AOSP 默认估计逻辑采用历史时间规则；它不会创建提纲所述的统一 LSTM 优先级。ADPF 接收应用显式上报的工作时长，也不预测用户接下来打开哪个应用。内核 EEVDF 根据虚拟运行时间、lag、eligibility 与 virtual deadline 选择 fair-class 任务，不接收 framework 生成的通用 ML 分数。

低电量、温控、前后台状态和用户交互会经各自策略影响任务资格、CPU 约束与频率，但源码没有把这些输入合成提纲中的固定加权公式。若 OEM 宣称使用预测调度，需要补充服务名、模型文件或推理调用、策略输出到 task profile/uclamp/cpufreq 的路径，以及同设备对照实验。

完整事实核查与源码阅读入口见 [1.59 Android 17「ML 驱动任务调度器」事实核查](./1.59-android17-ml-task-scheduler-comprehensive.md)。

## 参考源码与文档

- [Android 17 官方发布说明](https://android-developers.googleblog.com/2026/06/Android-17.html)
- [AOSP `JobSchedulerService.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/JobSchedulerService.java)
- [AOSP `PrefetchController.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/apex/jobscheduler/service/java/com/android/server/job/controllers/PrefetchController.java)
- [Android common kernel `fair.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/fair.c)
- [Android 官方 Performance Hint API](https://source.android.com/docs/core/perf/performance-hint-api)
