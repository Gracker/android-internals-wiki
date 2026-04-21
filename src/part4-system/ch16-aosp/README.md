# 第 16 章：AOSP 性能优化

> 本章节正在建设中。

## 本章内容

- Google 官方的性能优化思路
- 各 Android 版本性能变更追踪
- AOSP 源码编译与调试环境

## 延伸阅读

### AOSP App 冻结策略深度调研与 AOSP 原生改造方案
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/AOSP App 冻结策略深度调研与 AOSP 原生改造方案.md
- 类型：DeepResearch 调研结果
- 摘要：拉通 Android 14-17 App freezer 从 OomAdjuster、CachedAppOptimizer/Freezer、Binder 冻结到 cgroup.freeze 的完整路径，并提出多信号冻结决策、进程依赖图级联解冻等 AOSP 原生改造方案，适合作为系统冻结策略设计与 OEM 调优参考。
- 注入时间：2026-04-20
- 价值：既有源码链路又有改造方案，能支撑系统级冻结策略设计和回炉扩展。

### AIOS 架构深度解析与 Android Agent OS 演进全景
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/AIOS 架构深度解析与 Android Agent OS 演进全景.md
- 类型：DeepResearch 调研结果
- 摘要：从学术原型 AIOS 的 LLM Core、Scheduler、Memory/Storage/Tool/Access Manager 出发，对照 Android 的 AICore、AppFunctions、PCC、Binder/SystemService 架构，梳理移动端 Agent OS 已有能力、缺口与 A2A/AppFunctions 的分工边界。
- 注入时间：2026-04-21
- 价值：适合作为 AI × 手机体系化参考，帮助 AIW 把 Agent OS 讨论落到 Android 分层与系统服务上。

