# 目录

[写在前面](preface/intro.md)
- [本书的使用方式](preface/how-to-use.md)
- [适用读者](preface/target-audience.md)
- [内容验证标准说明](preface/verification-standards.md)
- [版本约定](preface/version-conventions.md)
- [阅读路径推荐](preface/reading-paths.md)

---

# 第一部分：Android 系统运行机制

- [第 1 章：系统架构全景](part1-fundamentals/ch01-architecture/README.md)
  - [1.1 Android 分层架构](part1-fundamentals/ch01-architecture/01-layered-architecture.md)
  - [1.43 Android 17 机器学习驱动任务调度器](part1-fundamentals/ch01-architecture/1.43-android17-ml-scheduler.md)
  - [1.44 Android 17 Binder IPC 优先级继承与内核批处理流水线](part1-fundamentals/ch01-architecture/1.44-binder-ipc-priority-inheritance.md)
  - [1.45 Android 17 Staged Install 状态机与原子性安装](part1-fundamentals/ch01-architecture/1.45-staged-install-state-machine.md)
  - [1.46 Android 17 ResourcesManager 与 Configuration 变更性能](part1-fundamentals/ch01-architecture/1.46-resourcesmanager-configuration-performance.md)

- [第 4 章：内存管理](part1-fundamentals/ch04-memory/README.md)
  - [4.5 Android 17 LMKD 与 AppFlow 兼容性方案](part1-fundamentals/ch04-memory/4.5-appflow-lmkd-compatibility.md)

  - [4.9 Android 17 ARM MTE 内存标签扩展实战](part1-fundamentals/ch04-memory/4.9-android17-memory-tagging-extension-mte.md)- [第 6 章：存储性能](part1-fundamentals/ch06-storage/README.md)
  - [6.2 Android 17 SharedPreferencesImpl ANR 机制](part1-fundamentals/ch06-storage/6.2-sharedpreferences-anr-optimization.md)

- [第 8 章：启动优化](part1-fundamentals/ch08-startup/README.md)
  - [8.1 Android 17 系统启动优化与 bootanalyze 工具链](part1-fundamentals/ch08-startup/8.1-bootanalyze-optimization-toolchain.md)

- [26.23 生产级 ART 动态方法追踪 — XTrace 架构与实战](part5-app/ch26-observability/26.23-xtrace-art-dynamic-method-tracing.md)
- [5.27 端侧大模型推理能效选型：MoE 架构与量化策略](part1-fundamentals/ch05-cpu-power/5.27-ondevice-llm-inference-energy-efficiency.md)

  - [Android 17 Binder IPC 优先级继承机制与内核批处理流水线](part1-fundamentals/ch01-architecture/1.9-binder-ipc-优先级继承内核批处理流水线-draft.md)

  - [Android 17 androidx DataStore 多进程 IPC 底层实现源码级验证](part1-fundamentals/ch06-storage/6.1-androidx-datastore--ipc-源码级验证-draft.md)
  - [1.48 Android 17 ResourcesManager/Configuration 与 Activity Relaunch 判定模型](part1-fundamentals/ch01-architecture/1.48-Android-17-ResourcesManager-Configuration-Activity-Relaunch-判定模型.md)
  - [1.49 Android 17 Staged Install 状态机与提交/恢复链路](part1-fundamentals/ch01-architecture/1.49-Android-17-Staged-Install-状态机-提交-恢复链路.md)

  - [9.10 Android 17 ANR 预警回调与类型枚举](part2-performance/ch09-anr/10-android17-anr-warning-callback.md)
  - [14.24 Android 17 simpleperf 微架构级性能采样与工作流增强](part3-tools/ch14-other-tools/24-android17-simpleperf-microarch-profiling.md)
  - [14.25 Android 17 eBPF 性能可观测性程序矩阵扩展](part3-tools/ch14-other-tools/25-android17-ebpf-observability-matrix.md)
- [第 8 章：响应速度优化](src/part2-performance/ch08-responsiveness/README.md)
  - [8.1 响应速度原理](src/part2-performance/ch08-responsiveness/01-responsiveness-principles.md)
  - [8.2 App 启动全流程](src/part2-performance/ch08-responsiveness/02-app-launch.md)
  - [8.3 启动优化策略](src/part2-performance/ch08-responsiveness/03-launch-optimization.md)
  - [8.6 Kotlin Coroutine 性能实践](src/part2-performance/ch08-responsiveness/06-coroutine-performance.md)
  - [8.7 Baseline Profiles 与编译优化实践](src/part2-performance/ch08-responsiveness/07-baseline-profiles.md)
  - [8.11 Native 库加载与动态链接性能](src/part2-performance/ch08-responsiveness/11-native-library-loading-dynamic-linker.md)
  - [8.12 Keystore/KeyMint 调用延迟与登录链路性能](src/part2-performance/ch08-responsiveness/12-keystore-keymint-latency.md)
  - [8.13 BiometricPrompt 与 Credential Manager 登录链路性能](src/part2-performance/ch08-responsiveness/13-biometric-credential-login-performance.md)
  - [8.14 推送通知管线性能：FCM 投递延迟与 NotificationManagerService 渲染](src/part2-performance/ch08-responsiveness/14-push-notification-pipeline-performance.md)
  - [8.17 Kotlin Flow 背压、操作符链与响应式性能边界](src/part2-performance/ch08-responsiveness/17-kotlin-flow-backpressure-performance.md)
  - [8.18 Binder Trace 驱动的 Activity 冷启动性能分析](src/part2-performance/ch08-responsiveness/18-binder-trace-cold-start-analysis.md)

- [第 9 章：ANR 监控与分析](src/part2-performance/ch09-anr/README.md)
  - [9.1 Android ANR 机制概述](src/part2-performance/ch09-anr/01-anr-intro.md)
  - [9.2 ANR 类型与触发条件](src/part2-performance/ch09-anr/02-anr-types.md)
  - [9.3 ANR 分析方法](src/part2-performance/ch09-anr/03-anr-analysis.md)
  - [9.4 主线程耗时检测](src/part2-performance/ch09-anr/04-main-thread-time-consuming.md)
  - [9.5 工具使用：ANR 分析实战](src/part2-performance/ch09-anr/05-anr-tools.md)
  - [9.6 案例分析：典型 ANR 场景](src/part2-performance/ch09-anr/05-case-studies.md)
  - [9.7 非技术性 ANR 诊断](src/part2-performance/ch09-anr/07-non-technical-anr-diagnosis.md)
  - [9.8 ANR 监控方案设计](src/part2-performance/ch09-anr/08-anr-monitoring-design.md)
  - [9.9 Android 17 ANR 预警系统](src/part2-performance/ch09-anr/09-android17-anr-warning-system.md)
  - [9.10 Android 17 ANR 预警回调与类型枚举](src/part2-performance/ch09-anr/10-android17-anr-warning-callback.md)
  - [9.11 企业级 ANR 监控平台架构设计](src/part2-performance/ch09-anr/9.11-enterprise-anr-monitoring-platform-design.md)
- [23.13 应用虚拟内存优化实战](part5-app/ch23-memory-practice/13-virtual-memory-optimization.md)

---

# 附录

- [附录 G：Android 性能学习路线](appendix/android-performance-learning-path.md)
