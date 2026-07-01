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

- [第 6 章：存储性能](part1-fundamentals/ch06-storage/README.md)
  - [6.2 Android 17 SharedPreferencesImpl ANR 机制](part1-fundamentals/ch06-storage/6.2-sharedpreferences-anr-optimization.md)

- [第 8 章：启动优化](part1-fundamentals/ch08-startup/README.md)
  - [8.1 Android 17 系统启动优化与 bootanalyze 工具链](part1-fundamentals/ch08-startup/8.1-bootanalyze-optimization-toolchain.md)

- [26.23 生产级 ART 动态方法追踪 — XTrace 架构与实战](part5-app/ch26-observability/26.23-xtrace-art-dynamic-method-tracing.md)
- [5.27 端侧大模型推理能效选型：MoE 架构与量化策略](part1-fundamentals/ch05-cpu-power/5.27-ondevice-llm-inference-energy-efficiency.md)

  - [Android 17 Binder IPC 优先级继承机制与内核批处理流水线](part1-fundamentals/ch01-architecture/1.9-binder-ipc-优先级继承内核批处理流水线-draft.md)

  - [Android 17 androidx DataStore 多进程 IPC 底层实现源码级验证](part1-fundamentals/ch06-storage/6.1-androidx-datastore--ipc-源码级验证-draft.md)
  - [1.47 Android 17 ResourcesManager Configuration 性能优化](part1-fundamentals/ch01-architecture/1.47-android17-resourcesmanager-configuration-performance.md)
  - [1.48 Android 17 Staged Install 状态机与原子性安装](part1-fundamentals/ch01-architecture/1.48-android17-staged-install-state-machine.md)

  - [9.10 Android 17 ANR 预警回调与类型枚举](part2-performance/ch09-anr/10-android17-anr-warning-callback.md)
  - [14.24 Android 17 simpleperf 微架构级性能采样与工作流增强](part3-tools/ch14-other-tools/24-android17-simpleperf-microarch-profiling.md)
  - [14.25 Android 17 eBPF 性能可观测性程序矩阵扩展](part3-tools/ch14-other-tools/25-android17-ebpf-observability-matrix.md)
