# 第 26 章：应用可观测性

第 17 章解释 APM（Application Performance Monitoring，应用性能监控）工具和监控 SDK（Software Development Kit，软件开发工具包）的实现原理，第 16 章讨论性能分析方法与指标体系。

本章从应用团队视角组织崩溃（Crash）上报、性能采集、线上排查和发布质量门禁（Release Quality Gate），覆盖问题发现、证据采集、影响归因、修复验证与回归防护。

## 内容索引


- [26.1 App 可观测性架构与性能数据采集](01-app-observability-performance-collection.md)
- [26.2 Crash 与 ANR 监控体系](02-crash-anr-monitoring.md)
- [26.3 线上排障、诊断通道与非 Play ROM 适配](03-online-troubleshooting-diagnostic-rom.md)
- [26.4 A/B Test 与性能回归防护](04-ab-testing-regression.md)
- [26.5 性能评分与发版质量门禁](05-performance-score-release-gate.md)
- [26.6 ApplicationExitInfo 与版本化线上诊断](06-application-exit-versioned-diagnostics.md)
- [26.7 ApplicationStartInfo 与启动归因上报](07-application-start-info.md)
- [26.8 Android Vitals 与 Play Console 质量指标归因](08-android-vitals-play-console-quality.md)
- [26.9 线上存储、I/O 与 SQLite 可观测性](09-online-storage-io-sqlite-observability.md)
- [26.10 线上网络质量监控与接入层对账](10-online-network-quality-observability.md)
- [26.11 Battery Historian 与功耗指标集成](11-battery-historian-performance-metrics-integration.md)
- [26.12 编译期字节码插桩与监控自动化](12-bytecode-instrumentation-monitoring-automation.md)
- [26.13 heapprofd、procfs CPU 与 Page Fault 分析](13-heapprofd-procfs-page-fault.md)
- [26.14 eBPF、ATrace 与线上系统追踪](14-ebpf-atrace-online-tracing.md)
- [26.15 ART 动态方法追踪与 JVMTI 边界](15-art-dynamic-tracing-jvmti.md)

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

- 搭建体系时先读 26.1，再按稳定性、线上排障和发布流程进入 26.2—26.5。
- 已知线上症状时可从 26.3 选择排查入口；进程退出、启动、Play 质量、存储和网络问题分别对应 26.6、26.7—26.10。
- 发布评估可结合 26.4、26.5、26.8 和 26.11，统一实验口径、门禁阈值与外部质量指标。
- 26.14、26.13 和 26.15 涉及系统权限或实验方案。采用其中机制前，应确认目标 Android 版本、构建类型、权限和上游维护状态。
- 非 Play 分发与厂商系统差异见 26.3；涉及 OEM 数据时，应保留设备型号、系统构建指纹、渠道和采集权限。
