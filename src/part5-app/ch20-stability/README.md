# 第 20 章：应用稳定性治理

应用稳定性治理面对几类不同的故障结局：应用崩溃（Crash）、系统判定应用未及时响应（ANR，Application Not Responding）、内存不足及相关分配失败（OOM，Out of Memory）、文件描述符或线程等资源耗尽，以及应用启动后反复崩溃的崩溃循环（Crash Loop）。排查时要保留能确定责任模块的日志、堆栈、系统状态和版本信息，限制一次故障波及的功能与用户，并用可复现测试确认恢复策略有效。

第 9 章分析系统如何判定、记录和处理 ANR；本章转向应用开发与线上治理，整理异常监控、问题定位、修复验证和指标度量的工程实践。

## 内容索引


- [20.1 应用稳定性度量、聚合与归因](01-stability-metrics-aggregation-attribution.md)
- [20.2 Java Crash、异常架构与线程堆栈分析](02-java-crash-exception-stack-analysis.md)
- [20.3 Native Crash、堆栈回溯与符号化](03-native-crash-unwinding-symbolication.md)
- [20.4 ANR 治理策略](04-anr-governance.md)
- [20.5 OOM、进程资源治理与 WebView Renderer 恢复](05-oom-webview-renderer-recovery.md)
- [20.6 Native 内存泄漏的线上分层监控](06-native-memory-leak-online-monitoring.md)
- [20.7 FD 耗尽监控与故障排查](07-fd-resource-monitoring.md)
- [20.8 线程与协程泄漏治理](08-thread-coroutine-leak-governance.md)
- [20.9 Binder IPC 故障判断与性能诊断](09-binder-ipc-fault-monitoring.md)
- [20.10 Android 17 Keystore 密钥配额与登录恢复](10-keystore-quota-login-stability.md)
- [20.11 MTE 与 GWP-ASan Native 内存安全检测](11-mte-gwp-asan-native-memory-safety.md)
- [20.12 Native Hook 技术选型与实现](12-native-hook-technology-selection-implementation.md)
- [20.13 Native 动态库安全发布、装载与回滚](13-native-dcl-secure-loading.md)
- [20.14 第三方 SDK 性能影响评估与治理实战](14-sdk-performance-governance.md)

## 索引术语速览

| 术语 | 本章中的含义 |
|---|---|
| Java Crash / Native Crash | 前者通常来自 Java 或 Kotlin 线程中未处理的异常；后者多指 C、C++ 或 JNI（Java 与 Native 代码的调用接口）触发的致命信号与主动终止。 |
| WebView Renderer | 负责网页内容执行与绘制的 WebView 渲染进程；它退出时，承载 WebView 的应用进程可能仍然存活。 |
| MTE / GWP-ASan | MTE（Memory Tagging Extension，内存标签扩展）用内存标签发现标签不匹配的访问；GWP-ASan 通过抽样保护部分堆分配，捕获释放后访问和越界等问题。两者都用于定位 Native 内存安全缺陷。 |
| 16 KB Page Size | 系统以 16 KB 作为基础内存页大小。ELF 对齐、打包和运行时假设的统一检查见 [4.5](../../part1-fundamentals/ch04-memory/05-16kb-page-size.md)。 |
| FD | File Descriptor，文件描述符。进程用这个整数编号引用已打开的文件、网络套接字（socket）、管道（pipe）等内核对象。 |
| DCL | Dynamic Code Loading，动态代码加载。20.13 关注 Native 动态库的可信发布、Android 17 `System.load()` 只读约束与回滚。 |
| Android Keystore | Android 提供的密钥存储服务。应用通常只持有密钥别名，通过系统接口生成、导入或使用密钥。 |
| Binder IPC | IPC 指进程间通信。一次看似本地的方法调用，可能经过 AIDL（Android 接口定义语言）接口、Binder 驱动和远端进程。 |
| 堆栈回溯 / 符号化 | 回溯从寄存器和栈中恢复调用帧；符号化再把程序地址转换成函数名、内联调用和源码行。 |
| Native Hook | 在运行时拦截或替换 Native 函数调用路径的技术，常用于监控和兼容处理，也会引入并发、ABI（二进制代码之间的接口约定）与平台防护风险。 |
| 结构化并发 | 把协程子任务绑定到明确的作用域和生命周期，使取消、失败和资源释放能够沿父子关系传播。 |
| SDK | Software Development Kit，软件开发工具包；本章主要指集成到应用进程中的第三方功能库及其代码、资源和运行开销。 |

## 阅读建议

- 第一次建立稳定性指标时，先读 20.1；Crash、ANR 和 OOM 按需进入 20.2—20.5。
- OOM 之后按资源层层下钻：20.6 定位 Native 内存增长，20.7 和 20.8 分别治理 FD 与线程/协程生命周期。
- IPC 与密钥容量问题见 20.9 和 20.10；Native 内存安全、Hook 和动态装载的风险边界依次见 20.11—20.13。
- 第三方 SDK 的跨类型准入、度量和退出协议收束在 20.14。
