# 第 20 章：应用稳定性治理

应用稳定性治理覆盖 Crash、ANR、OOM、资源耗尽和崩溃循环等问题。工作重点包括保留可归因的现场、控制故障影响范围，以及验证恢复策略。

第 9 章分析系统侧的 ANR 机制；这里转向 App 侧，整理异常监控、问题定位、修复验证和指标度量的工程实践。

## 内容索引

- [20.1 应用稳定性全景](01-stability-overview.md)
- [20.2 Java Crash 治理](02-java-crash-governance.md)
- [20.3 Native Crash 分析与治理](03-native-crash-governance.md)
- [20.4 ANR 治理策略](04-anr-governance.md)
- [20.5 OOM 治理](05-oom-governance.md)
- [20.6 稳定性度量与指标体系](06-stability-metrics.md)
- [20.7 异常处理架构设计](07-exception-architecture.md)
- [20.8 崩溃聚合与归因分析](08-crash-aggregation.md)
- [20.9 稳定性治理案例集](09-stability-case-studies.md)
- [20.10 WebView Renderer OOM 与白屏恢复](10-webview-renderer-oom-recovery.md)
- [20.11 MTE memtagMode 与 Native 崩溃治理](11-mte-memtag-native-crash.md)
- [20.12 SafeMode 崩溃循环判定与启动补偿链路](12-safemode-crash-loop-recovery.md)
- [20.13 16KB Page Size 兼容性与 Native 崩溃治理](13-16kb-page-size-native-compatibility.md)
- [20.14 线程与 FD 资源监控治理](14-thread-fd-resource-monitoring.md)
- [20.15 Android 17 Native DCL 只读约束与动态库加载稳定性](15-android17-native-dcl-stability.md)
- [20.15 补充：Native Hook 技术选型与实现](20.15-native-hook-technology-selection-implementation.md)
- [20.16 Android 17 Keystore 配额与登录故障治理](16-keystore-quota-login-stability.md)
- [20.17 Binder 异常体系与 IPC 故障性能边界](17-binder-exception-ipc-fault-performance.md)
- [20.18 Native 堆栈回溯与符号化机制](18-native-stack-unwinding-symbolication.md)
- [20.19 Android 17 信号处理架构与 debuggerd / linker 协作](19-android17-signal-handler-debuggerd-migration.md)
- [20.22 Binder 通信监控实战：传输耗时、异常检测与 IPC 性能治理](22-binder-communication-monitoring.md)
- [20.23 GWP-ASan 灰度检测演进与 Android 17 内存安全防线](23-gwp-asan-probabilistic-memory-safety-android17.md)
- [20.24 Crash 状态下 Java 线程堆栈获取与锁等待分析](24-crash-java-stack-lock-wait-analysis.md)
- [20.25 线程泄漏与匿名线程监控实战](25-thread-leak-anonymous-thread-monitoring.md)
- [20.26 Native 内存泄漏线上监控实战：malloc Hook、Scudo 追踪与 mallinfo 治理](26-native-memory-leak-online-monitoring.md)
- [20.27 Kotlin 协程泄漏诊断与结构化并发性能监控](20.27-coroutine-leak-diagnosis-structured-concurrency-performance.md)
- [20.28 第三方 SDK 性能影响评估与治理实战](28-sdk-performance-governance.md)

## 阅读建议

- 按故障类型选择对应条目，无须按编号顺序阅读。
- 第一次建立稳定性指标时，可先读 20.1 和 20.6。
- 20.9 汇总了多类问题的分析和治理案例。
