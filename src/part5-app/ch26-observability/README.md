# 第 26 章：应用可观测性

第 19 章解释 APM（Application Performance Monitoring，应用性能监控）工具和监控 SDK（Software Development Kit，软件开发工具包）的实现原理，第 15 章讨论性能分析方法与指标体系。

本章从应用团队视角组织崩溃（Crash）上报、性能采集、线上排查和发布质量门禁（Release Quality Gate），覆盖问题发现、证据采集、影响归因、修复验证与回归防护。

## 内容索引

- [26.1 App 可观测性架构设计](01-observability-architecture.md)
- [26.2 Crash 上报体系搭建](02-crash-reporting.md)
- [26.3 性能指标采集与上报](03-performance-collection.md)
- [26.4 ANR 监控体系](04-anr-monitoring.md)
- [26.5 线上问题排查方法论](05-online-troubleshooting.md)
- [26.6 A/B Test 与性能回归防护](06-ab-testing-regression.md)
- [26.7 发版质量门禁](07-release-quality-gate.md)
- [26.8 ApplicationExitInfo 与进程退出归因](08-application-exit-info.md)
- [26.9 eBPF 在线追踪与 Binder 语义重建](09-ebpf-online-tracing-binder-semantics.md)
- [26.10 Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger](10-versioned-diagnostics.md)
- [26.11 ApplicationStartInfo 与启动归因上报](11-application-start-info.md)
- [26.12 Android Vitals 与 Play Console 质量指标归因](12-android-vitals-play-console-quality.md)
- [26.13 线上存储、I/O 与 SQLite 可观测性](13-online-storage-io-sqlite-observability.md)
- [26.14 线上网络质量监控与接入层协同](14-online-network-quality-observability.md)
- [26.15 App Performance Score 与性能质量评分归因](15-app-performance-score.md)
- [26.16 端侧高可用日志与诊断命令通道](16-client-log-diagnostic-command-channel.md)
- [26.17 Battery Historian 与性能指标集成](17-battery-historian-performance-metrics-integration.md)
- [26.18 编译期字节码插桩与监控自动化](18-bytecode-instrumentation-monitoring-automation.md)
- [26.19 heapprofd 生产级部署与权限模型](19-heapprofd-production-deployment-permissions.md)
- [26.20 ProcessCpuTracker 与 /proc 伪文件系统 CPU 数据采集](20-proc-filesystem-cpu-monitoring.md)
- [26.21 Page Fault 类型分析与 Android 实践](21-page-fault-analysis-android.md)
- [26.22 生产级 ART 动态方法追踪：XTrace 论文机制与 Android 17 边界](22-xtrace-art-dynamic-method-tracing.md)
- [26.23 Facebook Profilo 框架线上 ATrace 收集方案](23-profilo-atrace-online-collection.md)
- [26.24 非 Play 渠道性能监控与国内厂商 ROM 适配可观测性](24-non-play-channel-rom-observability.md)
- [26.25 JVMTI Agent：ART 运行时动态监控的实验入口与证据边界](25-jvmti-agent-art-runtime-dynamic-monitoring.md)

## 术语提示

- 可观测性通过指标（Metrics）、日志（Logs）和追踪记录（Traces）判断线上系统发生了什么，并保留足以解释影响范围和耗时路径的证据。APM 是其中面向应用性能的一类工具体系。
- Crash 指进程因未处理异常、原生信号等原因意外退出；ANR（Application Not Responding，应用无响应）指系统判定应用在规定时间内没有响应关键事件。长卡顿不一定构成系统 ANR，两类事件需要分别确认。
- A/B Test（A/B 实验）把用户分入不同方案并比较同口径指标；发布质量门禁把崩溃率、ANR 率、性能回归和测试结果转换为继续灰度、暂停或回滚的条件。
- `ApplicationExitInfo` 保存系统视角的近期进程退出记录，`ApplicationStartInfo` 保存系统侧启动原因、类型和时间信息。`ProfilingManager` 用于请求受系统约束的性能采集，`ProfilingTrigger` 描述由系统事件触发采集的条件。
- eBPF（extended Berkeley Packet Filter）是在内核中运行受验证程序的机制，可用于具备相应权限的系统追踪；Binder 是 Android 的进程间通信机制。普通商店应用不能据此获得任意内核或跨进程观测权限。
- ATrace 是 Android 的追踪标记接口与兼容格式，Perfetto 可同时记录应用标记、系统服务和内核事件。Profilo 是已归档的生产追踪框架；XTrace 是研究方案，二者都不是 Android 17 SDK 提供的通用线上接口。
- Android Vitals 是 Google Play 汇总的线上质量指标，Play Console 是查看这些指标和发布状态的控制台。App Performance Score 是另一套评估框架，分数不能替代团队自己的线上指标和设备验证。
- `heapprofd` 是 Perfetto 的原生堆采样组件；Page Fault（缺页异常）是 CPU 无法按当前页表状态完成内存访问时交给内核处理的同步异常。`ProcessCpuTracker` 读取 `/proc`（内核导出的进程与系统状态伪文件系统）统计 CPU，但它是 Android 框架内部类，不属于公开 SDK。
- ART（Android Runtime）是 Android 执行应用字节码的运行时；JVMTI（Java Virtual Machine Tool Interface）是 ART 提供给调试器和分析器的进程内原生接口，Agent 是加载进目标进程的原生库。普通发布应用受到调试状态和附加权限限制。
- OEM（Original Equipment Manufacturer，设备制造商）和 ROM（设备系统软件）在本章用于描述厂商实现差异。厂商指标、后台限制和权限策略需要在目标设备上验证，不能只用 AOSP 源码推断。

## 阅读建议

- 搭建体系时先读 26.1，再按稳定性、性能和发布流程进入 26.2—26.7。
- 已知线上症状时可从 26.5 选择排查入口；进程退出、启动、Play 质量、存储和网络问题分别对应 26.8—26.14。
- 发布评估可结合 26.6、26.7、26.12、26.15 和 26.17，统一实验口径、门禁阈值与外部质量指标。
- 26.9、26.19、26.22、26.23 和 26.25 涉及系统权限、实验方案或已归档项目。采用其中机制前，应确认目标 Android 版本、构建类型、权限和上游维护状态。
- 非 Play 分发与厂商系统差异见 26.24；涉及 OEM 数据时，应保留设备型号、系统构建指纹、渠道和采集权限。
