# 高爷博客系列文章（Gracker's Blog Series）

> 来源：https://www.androidperformance.com/
> 作者：Gracker（高爷）
> 类型：高质量原创
> 融入策略：保留核心表达和观点，重新组织结构以符合章节逻辑，补充引用和交叉链接
> 总计：42 篇（11 系列 + 独立文章）

---

## Perfetto 系列（11 篇，已完结）→ Ch13 Perfetto

| # | 标题 | URL | 发布日期 | 映射章节 | 关键词 |
|---|------|-----|----------|----------|--------|
| 1 | Android Perfetto 101 | https://www.androidperformance.com/2024/03/27/Android-Perfetto-101/ | 2024-03-27 | 13.1 简介 | Perfetto 入门、概述、Trace 分析工具 |
| 2 | Perfetto 基础——什么是 Perfetto | https://www.androidperformance.com/2024/05/21/Android-Perfetto-01-What-is-perfetto/ | 2024-05-21 | 13.1 简介 | Perfetto 定义、架构、与 Systrace 关系 |
| 3 | Perfetto 基础——如何获取 Trace | https://www.androidperformance.com/2024/05/21/Android-Perfetto-02-how-to-get-perfetto/ | 2024-05-21 | 13.2 采集 | Trace 抓取、命令行、UI 采集 |
| 4 | Perfetto 基础——如何分析 Trace | https://www.androidperformance.com/2024/05/21/Android-Perfetto-03-how-to-analysis-perfetto/ | 2024-05-21 | 13.3 分析 | Trace 分析方法、UI 操作、Slice |
| 5 | Perfetto 进阶——命令行打开大 Trace | https://www.androidperformance.com/2025/02/08/Android-Perfetto-04-Open-Big-Trace-With-Command-Line/ | 2025-02-08 | 13.4 进阶 | 大文件 Trace、命令行工具、trace_processor |
| 6 | Perfetto 专题——Choreographer | https://www.androidperformance.com/2025/03/26/Android-Perfetto-05-Chorergrapher/ | 2025-03-26 | 13.5 专题解读 | Choreographer、VSync、doFrame |
| 7 | Perfetto 专题——为什么是 120Hz | https://www.androidperformance.com/2025/04/26/Android-Perfetto-06-Why-120Hz/ | 2025-04-26 | 13.5 专题解读 | 120Hz、刷新率、高帧率 |
| 8 | Perfetto 专题——MainThread 与 RenderThread | https://www.androidperformance.com/2025/08/02/Android-Perfetto-07-MainThread-And-RenderThread/ | 2025-08-02 | 13.5 专题解读 | MainThread、RenderThread、渲染管线 |
| 9 | Perfetto 专题——Vsync | https://www.androidperformance.com/2025/08/05/Android-Perfetto-08-Vsync/ | 2025-08-05 | 13.5 专题解读 | VSync、垂直同步、HWUI |
| 10 | Perfetto 专题——CPU | https://www.androidperformance.com/2025/11/12/Android-Perfetto-09-CPU/ | 2025-11-12 | 13.6 CPU 分析 | CPU 调度、负载、频率 |
| 11 | Perfetto 专题——Binder | https://www.androidperformance.com/2025/11/16/Android-Perfetto-10-Binder/ | 2025-11-16 | 13.5 专题解读 | Binder、IPC、通信延迟 |

## Systrace 系列（10 篇）→ 多章节

| # | 标题 | URL | 发布日期 | 映射章节 | 关键词 |
|---|------|-----|----------|----------|--------|
| 1 | Systrace 系列——开篇 | https://www.androidperformance.com/2019/05/28/Android-Systrace-About/ | 2019-05-28 | 13.1 简介 | Systrace 概述、工具链、适用场景 |
| 2 | Systrace 系列——SystemServer | https://www.androidperformance.com/2019/06/29/Android-Systrace-SystemServer/ | 2019-06-29 | 1.8 AMS | SystemServer、AMS、Activity 管理 |
| 3 | Systrace 系列——基础| https://www.androidperformance.com/2019/07/23/Android-Systrace-Pre/ | 2019-07-23 | 13.2 采集 | Systrace 基础、准备工作、参数配置 |
| 4 | Systrace 系列——Input | https://www.androidperformance.com/2019/11/04/Android-Systrace-Input/ | 2019-11-04 | 3.1 Input | Input 事件分发、触摸事件、输入延迟 |
| 5 | Systrace 系列——MainThread 与 RenderThread | https://www.androidperformance.com/2019/11/06/Android-Systrace-MainThread-And-RenderThread/ | 2019-11-06 | 2.5 渲染 | MainThread、RenderThread、UI 线程 |
| 6 | Systrace 系列——Vsync | https://www.androidperformance.com/2019/12/01/Android-Systrace-Vsync/ | 2019-12-01 | 2.3 VSync | VSync、垂直同步、Choreographer |
| 7 | Systrace 系列——Binder | https://www.androidperformance.com/2019/12/06/Android-Systrace-Binder/ | 2019-12-06 | 1.4 Binder | Binder 通信、IPC、跨进程调用 |
| 8 | Systrace 系列——Triple Buffer | https://www.androidperformance.com/2019/12/15/Android-Systrace-Triple-Buffer/ | 2019-12-15 | 2.13 BufferQueue | Triple Buffer、BufferQueue、双缓冲 |
| 9 | Systrace 系列——CPU | https://www.androidperformance.com/2019/12/21/Android-Systrace-CPU/ | 2019-12-21 | 5.1 CPU | CPU 调度、频率、负载分析 |
| 10 | Systrace 系列——SurfaceFlinger | https://www.androidperformance.com/2020/02/14/Android-Systrace-SurfaceFlinger/ | 2020-02-14 | 2.6 SurfaceFlinger | SurfaceFlinger、合成、图层 |

## ANR 系列（3 篇）→ Ch09 ANR

| # | 标题 | URL | 发布日期 | 映射章节 | 关键词 |
|---|------|-----|----------|----------|--------|
| 1 | Android ANR 01——ANR 的设计 | https://www.androidperformance.com/2025/02/08/Android-ANR-01-ANR-Design/ | 2025-02-08 | 9.1 ANR 原理 | ANR 设计原理、超时机制、触发条件 |
| 2 | Android ANR 02——如何分析 ANR | https://www.androidperformance.com/2025/02/08/Android-ANR-02-How-to-analysis-ANR/ | 2025-02-08 | 9.3 ANR 分析 | ANR 分析方法、traces.txt、排查流程 |
| 3 | Android ANR 03——ANR 案例分享 | https://www.androidperformance.com/2025/02/08/Android-ANR-03-ANR-Case-Share/ | 2025-02-08 | 9.5 ANR 案例 | ANR 案例、实战分析、常见原因 |

## Memory 系列（4 篇）→ Ch04 内存

| # | 标题 | URL | 发布日期 | 映射章节 | 关键词 |
|---|------|-----|----------|----------|--------|
| 1 | Android 性能优化——内存篇之 Android 资源 | https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-AndroidResource/ | 2015-07-20 | 4.5 内存优化实践 | 资源内存、Bitmap、图片优化 |
| 2 | Android 性能优化——内存篇之 Google 内存优化 | https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-Google/ | 2015-07-20 | 4.1 内存管理 | Google 内存优化方案、Memory Analyzer |
| 3 | Android 性能优化——内存篇之 Java 内存 | https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-Java/ | 2015-07-20 | 4.3 Java 堆 | Java 内存模型、GC、堆内存 |
| 4 | Android 性能优化——内存篇之 onTrimMemory | https://www.androidperformance.com/2015/07/20/Android-Performance-Memory-onTrimMemory/ | 2015-07-20 | 4.4 LMK | onTrimMemory、LMK、内存回收 |

## CPU 状态系列（3 篇）→ Ch05 CPU

| # | 标题 | URL | 发布日期 | 映射章节 | 关键词 |
|---|------|-----|----------|----------|--------|
| 1 | Systrace CPU 状态——Runnable | https://www.androidperformance.com/2022/01/21/android-systrace-cpu-state-runnable/ | 2022-01-21 | 5.1 CPU | Runnable 状态、CPU 调度、等待执行 |
| 2 | Systrace CPU 状态——Running | https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-running/ | 2022-03-13 | 5.1 CPU | Running 状态、CPU 执行、时间片 |
| 3 | Systrace CPU 状态——Sleep | https://www.androidperformance.com/2022/03/13/android-systrace-cpu-state-sleep/ | 2022-03-13 | 5.1 CPU | Sleep 状态、休眠、唤醒 |

## 独立文章（11 篇）→ 各章节

| # | 标题 | URL | 发布日期 | 映射章节 | 关键词 |
|---|------|-----|----------|----------|--------|
| 1 | Android 硬件层（Hardware Layer） | https://www.androidperformance.com/2019/07/27/Android-Hardware-Layer/ | 2019-07-27 | 2.7 硬件加速 | Hardware Layer、硬件加速、GPU 渲染 |
| 2 | Android Activity 启动模式 | https://www.androidperformance.com/2019/09/01/Android-Activity-Lunch-Mode/ | 2019-09-01 | 8.2 启动模式 | Activity 启动模式、launchMode、任务栈 |
| 3 | Android Jank 调试 | https://www.androidperformance.com/2019/09/05/Android-Jank-Debug/ | 2019-09-05 | 7.3 Jank 调试 | Jank 调试、卡顿分析、工具使用 |
| 4 | Android Jank——App 导致的卡顿 | https://www.androidperformance.com/2019/09/05/Android-Jank-Due-To-App/ | 2019-09-05 | 7.2 Jank 原因 | App 侧卡顿、主线程耗时、布局 |
| 5 | Android Jank——System 导致的卡顿 | https://www.androidperformance.com/2019/09/05/Android-Jank-Due-To-System/ | 2019-09-05 | 7.2 Jank 原因 | 系统侧卡顿、GC、Binder 等待 |
| 6 | Android 后台应用被杀 Debug | https://www.androidperformance.com/2019/09/17/Android-Kill-Background-App-Debug/ | 2019-09-17 | 4.4 LMK | 后台杀进程、LMK、进程优先级 |
| 7 | Android 低内存导致的卡顿 | https://www.androidperformance.com/2019/09/18/Android-Jank-Due-To-Low-Memory/ | 2019-09-18 | 10.4 低内存 | 低内存卡顿、内存压力、系统性能 |
| 8 | Android Choreographer | https://www.androidperformance.com/2019/10/22/Android-Choreographer/ | 2019-10-22 | 2.4 Choreographer | Choreographer、VSync、帧调度 |
| 9 | Android 后台动画优化 | https://www.androidperformance.com/2019/10/24/Android-Background-Animation/ | 2019-10-24 | 7.4 动画优化 | 后台动画、功耗、动画性能 |
| 10 | Android 应用启动优化 | https://www.androidperformance.com/2019/11/18/Android-App-Lunch-Optimize/ | 2019-11-18 | 8.3 启动优化 | 应用启动、优化策略、冷启动 |
| 11 | Android 应用链式唤醒 | https://www.androidperformance.com/2020/05/07/Android-App-Chain-Wakeup/ | 2020-05-07 | 8.1 启动流程 | 链式唤醒、广播、AlarmManager |

---

## 融入优先级建议

1. **P0（高优先级）**：Perfetto 系列、ANR 系列 — 内容新、完整度高、直接对应未填充章节
2. **P1（中优先级）**：Systrace 系列 — 内容经典但部分与 Perfetto 有重叠，需去重后融入
3. **P2（低优先级）**：Memory 系列、CPU 状态系列、独立文章 — 单篇价值高但篇幅短，作为补充材料
