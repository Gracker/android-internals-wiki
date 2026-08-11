# 第 26 章：应用可观测性

第 19 章详细拆解 APM 工具生态和监控 SDK 的实现原理，第 15 章讨论性能分析方法与指标体系。

应用可观测性从 App 团队视角组织 Crash 上报、性能采集、线上排查和 Release Quality Gate，覆盖问题发现、定位、处置与回归防护。

## 内容索引

- 26.1 App 可观测性架构设计
- 26.2 Crash 上报体系搭建
- 26.3 性能指标采集与上报
- 26.4 ANR 监控体系
- 26.5 线上问题排查方法论
- 26.6 A/B Test 与性能回归防护
- 26.7 发版质量门禁
- 26.8 ApplicationExitInfo 与进程退出归因
- 26.9 eBPF 在线追踪与 Binder 语义重建
- 26.10 Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger
- 26.11 ApplicationStartInfo 与启动归因上报
- 26.12 Android Vitals 与 Play Console 质量指标归因
- 26.13 线上存储、I/O 与 SQLite 可观测性
- 26.14 线上网络质量监控与接入层协同
- 26.15 App Performance Score 与性能质量评分归因
- 26.16 端侧高可用日志与诊断命令通道
- 26.17 Battery Historian 与性能指标集成
- 26.18 编译期字节码插桩与监控自动化
- 26.19 heapprofd 生产级部署与权限模型
- 26.20 ProcessCpuTracker 与 /proc 伪文件系统 CPU 数据采集
- 26.21 Page Fault 类型分析与 Android 实践
- 26.22 生产级 ART 动态方法追踪：XTrace 论文机制与 Android 17 边界
- 26.23 Facebook Profilo 框架线上 ATrace 收集方案
- 26.24 非 Play 渠道性能监控与国内厂商 ROM 适配可观测性
- 26.25 JVMTI Agent：ART 运行时动态监控的实验入口与证据边界

## 阅读建议

- 可按问题类型直接进入对应条目。
- 各条目尽量自包含；首次阅读可先看 26.1 的体系结构。
- 26.5 的案例索引适合从症状进入排障，26.6 负责实验统计与回归判定。
