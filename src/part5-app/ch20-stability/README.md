# 第 20 章：应用稳定性治理

应用稳定性治理面对几类不同的故障结局：应用崩溃（Crash）、系统判定应用未及时响应（ANR，Application Not Responding）、内存不足及相关分配失败（OOM，Out of Memory）、文件描述符或线程等资源耗尽，以及应用启动后反复崩溃的崩溃循环（Crash Loop）。排查时要保留能确定责任模块的日志、堆栈、系统状态和版本信息，限制一次故障波及的功能与用户，并用可复现测试确认恢复策略有效。

第 9 章分析系统如何判定、记录和处理 ANR；本章转向应用开发与线上治理，整理异常监控、问题定位、修复验证和指标度量的工程实践。

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

## 索引术语速览

| 术语 | 本章中的含义 |
|---|---|
| Java Crash / Native Crash | 前者通常来自 Java 或 Kotlin 线程中未处理的异常；后者多指 C、C++ 或 JNI（Java 与 Native 代码的调用接口）触发的致命信号与主动终止。 |
| WebView Renderer | 负责网页内容执行与绘制的 WebView 渲染进程；它退出时，承载 WebView 的应用进程可能仍然存活。 |
| MTE / GWP-ASan | MTE（Memory Tagging Extension，内存标签扩展）用内存标签发现标签不匹配的访问；GWP-ASan 通过抽样保护部分堆分配，捕获释放后访问和越界等问题。两者都用于定位 Native 内存安全缺陷。 |
| 16 KB Page Size | 系统以 16 KB 作为基础内存页大小。Native 库的 ELF（可执行文件和动态库采用的文件格式）对齐、打包和运行时假设都要兼容这一配置。 |
| FD | File Descriptor，文件描述符。进程用这个整数编号引用已打开的文件、网络套接字（socket）、管道（pipe）等内核对象。 |
| DCL | Dynamic Code Loading，动态代码加载。本章 20.13 关注运行时写入或下载 Native 动态库后再调用 `System.load()` 的场景。 |
| Android Keystore | Android 提供的密钥存储服务。应用通常只持有密钥别名，通过系统接口生成、导入或使用密钥。 |
| Binder IPC | IPC 指进程间通信。一次看似本地的方法调用，可能经过 AIDL（Android 接口定义语言）接口、Binder 驱动和远端进程。 |
| 堆栈回溯 / 符号化 | 回溯从寄存器和栈中恢复调用帧；符号化再把程序地址转换成函数名、内联调用和源码行。 |
| Native Hook | 在运行时拦截或替换 Native 函数调用路径的技术，常用于监控和兼容处理，也会引入并发、ABI（二进制代码之间的接口约定）与平台防护风险。 |
| 结构化并发 | 把协程子任务绑定到明确的作用域和生命周期，使取消、失败和资源释放能够沿父子关系传播。 |
| SDK | Software Development Kit，软件开发工具包；本章主要指集成到应用进程中的第三方功能库及其代码、资源和运行开销。 |

## 阅读建议

- 按故障类型选择对应条目，无须按编号顺序阅读。
- 第一次建立稳定性指标时，可先读 20.1 和 20.6。
- 应用发生崩溃循环时，先读 20.7；Native Crash、ANR 和线程问题分别参见 20.3、20.4 和 20.19。
- Native 内存安全检测先读 20.10；文件描述符、线程、Native 内存和协程的泄漏问题依次参见 20.12、20.19、20.20 和 20.21。
