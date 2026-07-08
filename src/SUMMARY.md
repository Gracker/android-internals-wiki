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
  - [1.53 Android 17 Binder IPC 优先级继承与异步批处理流水线](part1-fundamentals/ch01-architecture/1-53-android17-binder-ipc-优先级继承与异步批处理流水线.md)

  - [1.54 Android 17 Binder 线程池实现机制与调优参数](part1-fundamentals/ch01-architecture/1.54-binder-thread-pool-implementation.md)
- [第 2 章：渲染管线](part2-performance/ch02-rendering/README.md)
  - [2.1 GPU 渲染管线架构演进](part2-performance/ch02-rendering/2.1-gpu-rendering-pipeline-evolution.md)  - [Compose Pager 从基础到高级动画](part2-performance/ch2-rendering/2.52-Compose-Pager-从基础到高级动画.md)
  - [2.3 GPU 调试性能工具链源码调研](part2-performance/ch02-rendering/2.3-gpu-debug-performance-tools.md)
  - [2.51 Android 17 GPU 调试性能工具链](part1-fundamentals/ch02-rendering/2.51-android17-gpu-debug-performance-tools.md)

  - [2.6 Android 17 eBPF观测增强](part1-fundamentals/ch01-architecture/2.6-ebpf-observability-enhancement.md)
  - [2.7 Android 17 GPU 图形调试与性能优化工具链](part1-fundamentals/ch01-architecture/2.7-gpu-debug-performance-tools-chain.md)
- [第 4 章：内存管理](part1-fundamentals/ch04-memory/README.md)


  - [4.9 Android 17 ARM MTE 内存标签扩展实战](part1-fundamentals/ch04-memory/4.9-android17-memory-tagging-extension-mte.md)
  - [4.37 Android 17 LMKD 用户态迁移 + PSI 协同机制](part1-fundamentals/ch01-architecture/4.37-lmkd-userspace-migration-psi.md)
- [4.34 Android 17 ART HeapTask 系统的 7 个子类实现](part1-fundamentals/ch04-memory/4.34-android17-art-heaptask-system-7-subclasses.md)
  - [4.35 Android 17 CPU 缓存局部性与 PSS 内存核算源码机制](part1-fundamentals/ch04-memory/4.35-android17-cpu-cache-locality-pss-accounting.md)

  - [4.9 Android 17 ARM MTE 内存标签扩展实战](part1-fundamentals/ch04-memory/4.9-android17-memory-tagging-extension-mte.md)- [第 6 章：存储性能](part1-fundamentals/ch06-storage/README.md)
  - [6.2 Android 17 SharedPreferencesImpl ANR 机制](part1-fundamentals/ch06-storage/6.2-sharedpreferences-anr-optimization.md)
  - [6.4 Android 17 SharedPreferencesImpl ANR 真因分析与迁移方案](part1-fundamentals/ch06-architecture/6-4-android17-sharedpreferencesimpl-anr-真因分析与迁移方案.md)
  - [4.11 Android 17 AppFlow 与 LMKD v2 内存联合调度协作机制](part1-fundamentals/ch04-architecture/4-11-android17-appflow-与-lmkd-v2-内存联合调度协作机制.md)
  - [4.21 ART HeapTask 调度管线与 Android 17 新增子类](part1-fundamentals/ch04-memory/21-art-heaptask-scheduling-pipeline.md)

- [第 8 章：启动优化](part1-fundamentals/ch08-startup/README.md)
  - [8.1 Android 17 系统启动优化与 bootanalyze 工具链](part1-fundamentals/ch08-startup/8.1-bootanalyze-optimization-toolchain.md)
  - [8.31 Android 17 启动流程深度洞察](part1-fundamentals/ch08-startup/8.31-android17-startup-insights-gaps.md)
  - [8.32 Android 17 应用启动信息分析](part1-fundamentals/ch08-startup/8.32-android17-application-start-info.md)

- [26.23 生产级 ART 动态方法追踪 — XTrace 架构与实战](part5-app/ch26-observability/26.23-xtrace-art-dynamic-method-tracing.md)
- [5.21 Android 17 SoC 厂商电池优化架构](part1-fundamentals/ch05-cpu-power/5.21-android17-battery-optimization-soc-architecture.md)

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
  - [8.3 Android 17 Startup Insights 缺口分析](src/part1-fundamentals/ch08-startup/8.3-startup-insights-gaps.md)
  - [8.6 Kotlin Coroutine 性能实践](src/part2-performance/ch08-responsiveness/06-coroutine-performance.md)
  - [8.7 Baseline Profiles 与编译优化实践](src/part2-performance/ch08-responsiveness/07-baseline-profiles.md)
  - [8.11 Native 库加载与动态链接性能](src/part2-performance/ch08-responsiveness/11-native-library-loading-dynamic-linker.md)
  - [8.12 Keystore/KeyMint 调用延迟与登录链路性能](src/part2-performance/ch08-responsiveness/12-keystore-keymint-latency.md)
  - [8.13 BiometricPrompt 与 Credential Manager 登录链路性能](src/part2-performance/ch08-responsiveness/13-biometric-credential-login-performance.md)
  - [8.14 推送通知管线性能：FCM 投递延迟与 NotificationManagerService 渲染](src/part2-performance/ch08-responsiveness/14-push-notification-pipeline-performance.md)
  - [8.17 Kotlin Flow 背压、操作符链与响应式性能边界](src/part2-performance/ch08-responsiveness/17-kotlin-flow-backpressure-performance.md)
  - [8.18 Binder Trace 驱动的 Activity 冷启动性能分析](src/part2-performance/ch08-responsiveness/18-binder-trace-cold-start-analysis.md)
  - [8.3 Android 17 系统启动优化与 bootanalyze 工具链增强](part2-fundamentals/ch08-architecture/8-3-android17-系统启动优化与-bootanalyze-工具链增强.md)
  - [8.6 Android 17 WindowManager 性能优化实战](part2-performance/ch08-window-manager/8.6-window-manager-performance.md)
  - [8.7 Android 17 ActivityManager 性能优化实战](part2-performance/ch08-activity-manager/8.7-activity-manager-performance.md)
  - [8.8 Android 17 TelephonyManager 性能优化实战](part2-performance/ch08-telephony-manager/8.8-telephony-manager-performance.md)
  - [8.9 Android 17 ConnectivityManager 性能优化实战](part2-performance/ch08-connectivity-manager/8.9-connectivity-manager-performance.md)
  - [8.10 Android 17 PowerManager 性能优化实战](part2-performance/ch08-power-manager/8.10-power-manager-performance.md)
- [第 11 章：网络性能优化](part2-performance/ch11-network-optimization/README.md)
  - [11.1 Android 17 网络性能优化实战](part2-performance/ch11-network-optimization/11.1-Android 17 网络性能优化实战.md)

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
  - [9.11 企业级 ANR 监控平台架构设计](src/part2-performance/ch09-anr/9.11-enterprise-anr-monitoring-platform-design.md)  - [9.12 Android 17 ANR 输入事件超时检测双层预警机制](part2-fundamentals/ch09-architecture/9-12-android17-anr-输入事件超时检测双层预警机制.md)
- [第 12 章：音频性能优化](part3-system/ch12-audio-performance/README.md)
  - [12.33 Android 17 后台音频硬化与 LE Audio 功耗治理](part3-system/ch12-audio-performance/12.33-android17-background-audio-hardening-leaudio-power.md)

- [23.13 应用虚拟内存优化实战](part5-app/ch23-memory-practice/13-virtual-memory-optimization.md)

---

  - [14.27 Macrobenchmark 框架与自动化性能门禁](part3-tools/ch14-other-tools/27-macrobenchmark-automation-gate.md)
  - [13.26 android.os.Trace API 深度解析与应用级自定义追踪](part3-tools/ch13-perfetto/13.26-android-trace-api-custom-tracing.md)
  - [13.27 Android 17 Perfetto v57 AI 技能与状态轨道](part3-tools/ch13-perfetto/13.27-android17-perfetto-v57-ai-skill-state-tracks.md)
  - [21.17 Startup Insights API 与启动性能可观测性](part5-app/ch21-startup/17-startup-insights-api-observability.md)
  - [17.9 SoC 特异性功耗优化策略：高通/联发科/三星](part4-system/ch17-oem/09-soc-specific-power-optimization.md)
  - [17.21 Android 17 SoC 厂商 Power HAL 与 schedutil 闭环](part4-system/ch17-oem/17.21-android17-soc-vendor-power-hal-schedutil-loop.md)
  - [22.30 Impeller Shader 编译性能与 Flutter 渲染稳定性](part5-app/ch22-rendering-practice/30-impeller-shader-compilation-flutter.md)

  - [4.22 Android 17 AI Agent 内存沙箱化与跨应用数据复用](part1-fundamentals/ch04-memory/4.22-android17-ai-agent-memory-sandboxed-data-reuse.md)
  - [14.28 GPU 性能分析进阶 — 跨厂商计数器标准化与工作负载剖析](part3-tools/ch14-other-tools/28-gpu-performance-profiling-advanced.md)
  - [26.24 heapprofd 生产级部署与权限模型](part5-app/ch26-observability/24-heapprofd-production-deployment-permissions.md)
  - [20.19 Android 17 信号处理架构迁移与 debuggerd bionic/linker 重构](part5-app/ch20-stability/19-android17-signal-handler-debuggerd-migration.md)

#   - [8.33 Android 17 模块化启动框架与依赖图优化](src/part1-fundamentals/ch08-startup/8.33-android17-modular-startup-dependency-graph.md)
  - [4.36 Android 17 高级内存优化与治理](src/part1-fundamentals/ch04-memory/4.36-android17-advanced-memory-optimization.md)
附录

- [附录 G：Android 性能学习路线](appendix/android-performance-learning-path.md)
