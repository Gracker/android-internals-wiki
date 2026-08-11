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
- [20.9 WebView Renderer OOM 与白屏恢复](09-webview-renderer-oom-recovery.md)
- [20.10 MTE 与 GWP-ASan Native 内存安全检测](10-mte-gwp-asan-native-memory-safety.md)
- [20.11 16KB Page Size 兼容性与 Native 崩溃治理](11-16kb-page-size-native-compatibility.md)
- [20.12 FD 资源监控与治理](12-fd-resource-monitoring.md)
- [20.13 Android 17 Native DCL 只读约束与动态库加载稳定性](13-android17-native-dcl-stability.md)
- [20.14 Android 17 Keystore 配额与登录故障治理](14-keystore-quota-login-stability.md)
- [20.15 Binder IPC 故障与性能监控](15-binder-ipc-fault-monitoring.md)
- [20.16 Native 堆栈回溯与符号化机制](16-native-stack-unwinding-symbolication.md)
- [20.17 Native Hook 技术选型与实现](17-native-hook-technology-selection-implementation.md)
- [20.18 Crash 状态下 Java 线程堆栈获取与锁等待分析](18-crash-java-stack-lock-wait-analysis.md)
- [20.19 线程泄漏与匿名线程监控实战](19-thread-leak-anonymous-thread-monitoring.md)
- [20.20 Native 内存泄漏线上监控实战](20-native-memory-leak-online-monitoring.md)
- [20.21 Kotlin 协程泄漏诊断与结构化并发性能监控](21-coroutine-leak-diagnosis-structured-concurrency-performance.md)
- [20.22 第三方 SDK 性能影响评估与治理实战](22-sdk-performance-governance.md)

## 阅读建议

- 按故障类型选择对应条目，无须按编号顺序阅读。
- 第一次建立稳定性指标时，可先读 20.1 和 20.6。
- Crash Loop 进入 20.7；Native/ANR/线程案例已分别回流到 20.3、20.4 和 20.19。
- Native 内存安全检测先读 20.10，资源生命周期问题按 20.12、20.19、20.20、20.21 分层阅读。
