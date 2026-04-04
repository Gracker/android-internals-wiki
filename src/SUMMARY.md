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
  - [1.2 系统启动全流程](part1-fundamentals/ch01-architecture/02-boot-process.md)
  - [1.3 进程模型与生命周期管理](part1-fundamentals/ch01-architecture/03-process-model.md)
  - [1.4 Binder IPC 机制与性能影响](part1-fundamentals/ch01-architecture/04-binder.md)
  - [1.5 线程模型](part1-fundamentals/ch01-architecture/05-threading-model.md)
  - [1.6 Android 版本演进中的架构变化](part1-fundamentals/ch01-architecture/06-version-evolution.md)
  - [1.7 ART 编译管线与 dex2oat 优化](part1-fundamentals/ch01-architecture/07-art-compilation.md)

- [第 2 章：渲染系统](part1-fundamentals/ch02-rendering/README.md)
  - [2.1 Android 渲染架构全景](part1-fundamentals/ch02-rendering/01-rendering-overview.md)
  - [2.2 帧率与刷新率](part1-fundamentals/ch02-rendering/02-framerate.md)
  - [2.3 VSync 机制](part1-fundamentals/ch02-rendering/03-vsync.md)
  - [2.4 Choreographer 与渲染流水线](part1-fundamentals/ch02-rendering/04-choreographer.md)
  - [2.5 MainThread 与 RenderThread 协作](part1-fundamentals/ch02-rendering/05-main-render-thread.md)
  - [2.6 SurfaceFlinger 与合成](part1-fundamentals/ch02-rendering/06-surfaceflinger.md)
  - [2.7 Hardware Layer](part1-fundamentals/ch02-rendering/07-hardware-layer.md)
  - [2.8 过度绘制](part1-fundamentals/ch02-rendering/08-overdraw.md)
  - [2.9 渲染机制的版本演进](part1-fundamentals/ch02-rendering/09-rendering-evolution.md)
  - [2.10 GPU 渲染深入](part1-fundamentals/ch02-rendering/10-gpu-rendering.md)
  - [2.11 Flutter 渲染管线与性能](part1-fundamentals/ch02-rendering/11-flutter-rendering.md)
  - [2.12 Window Manager Service 与窗口管理](part1-fundamentals/ch02-rendering/12-window-manager.md)

- [第 3 章：输入系统](part1-fundamentals/ch03-input/README.md)
  - [3.1 Input 事件分发全流程](part1-fundamentals/ch03-input/01-input-dispatch.md)
  - [3.2 触摸响应的性能分析](part1-fundamentals/ch03-input/02-touch-performance.md)
  - [3.3 手势导航与系统交互](part1-fundamentals/ch03-input/03-gesture-navigation.md)

- [第 4 章：内存管理](part1-fundamentals/ch04-memory/README.md)
  - [4.1 Android 内存模型全景](part1-fundamentals/ch04-memory/01-memory-overview.md)
  - [4.2 Linux 内核内存管理](part1-fundamentals/ch04-memory/02-linux-memory.md)
  - [4.3 ART 虚拟机内存管理](part1-fundamentals/ch04-memory/03-art-memory.md)
  - [4.4 Low Memory Killer](part1-fundamentals/ch04-memory/04-lmk.md)
  - [4.5 App 内存优化](part1-fundamentals/ch04-memory/05-app-memory-optimization.md)
  - [4.6 内存相关的版本演进](part1-fundamentals/ch04-memory/06-memory-evolution.md)

- [第 5 章：CPU 调度与能耗管理](part1-fundamentals/ch05-cpu-power/README.md)
  - [5.1 Linux 进程调度基础](part1-fundamentals/ch05-cpu-power/01-linux-scheduling.md)
  - [5.2 EAS 能量感知调度](part1-fundamentals/ch05-cpu-power/02-eas.md)
  - [5.3 大小核架构](part1-fundamentals/ch05-cpu-power/03-big-little.md)
  - [5.4 DVFS 与功耗管理](part1-fundamentals/ch05-cpu-power/04-dvfs.md)
  - [5.5 Thermal 管控](part1-fundamentals/ch05-cpu-power/05-thermal.md)
  - [5.6 Android 功耗管理](part1-fundamentals/ch05-cpu-power/06-android-power.md)
  - [5.7 CPU 相关的版本演进](part1-fundamentals/ch05-cpu-power/07-cpu-evolution.md)

- [第 6 章：存储与 I/O](part1-fundamentals/ch06-storage/README.md)
  - [6.1 Android 存储架构](part1-fundamentals/ch06-storage/01-storage-architecture.md)
  - [6.2 文件系统](part1-fundamentals/ch06-storage/02-filesystem.md)
  - [6.3 I/O 调度与性能](part1-fundamentals/ch06-storage/03-io-scheduling.md)
  - [6.4 存储相关的版本演进](part1-fundamentals/ch06-storage/04-storage-evolution.md)

---

# 第二部分：性能专题

- [第 7 章：流畅性](part2-performance/ch07-smoothness/README.md)
  - [7.1 卡顿的定义与分类](part2-performance/ch07-smoothness/01-jank-definition.md)
  - [7.2 卡顿原因体系](part2-performance/ch07-smoothness/02-jank-causes.md)
  - [7.3 卡顿分析方法论](part2-performance/ch07-smoothness/03-jank-methodology.md)
  - [7.4 典型场景分析](part2-performance/ch07-smoothness/04-typical-scenarios.md)
  - [7.5 优化策略](part2-performance/ch07-smoothness/05-optimization.md)
  - [7.6 案例集](part2-performance/ch07-smoothness/06-case-studies.md)
  - [7.7 Jetpack Compose 性能优化](part2-performance/ch07-smoothness/07-compose-performance.md)

- [第 8 章：响应速度](part2-performance/ch08-responsiveness/README.md)
  - [8.1 响应速度原理](part2-performance/ch08-responsiveness/01-responsiveness-principles.md)
  - [8.2 App 启动全流程](part2-performance/ch08-responsiveness/02-app-launch.md)
  - [8.3 启动优化策略](part2-performance/ch08-responsiveness/03-launch-optimization.md)
  - [8.4 其他响应速度场景](part2-performance/ch08-responsiveness/04-other-scenarios.md)
  - [8.5 案例集](part2-performance/ch08-responsiveness/05-case-studies.md)
  - [8.6 Kotlin Coroutine 性能实践](part2-performance/ch08-responsiveness/06-coroutine-performance.md)

- [第 9 章：ANR](part2-performance/ch09-anr/README.md)
  - [9.1 ANR 设计思想](part2-performance/ch09-anr/01-anr-design.md)
  - [9.2 ANR 类型与触发条件](part2-performance/ch09-anr/02-anr-types.md)
  - [9.3 ANR 分析方法](part2-performance/ch09-anr/03-anr-analysis.md)
  - [9.4 特殊场景的 ANR](part2-performance/ch09-anr/04-special-anr.md)
  - [9.5 案例集](part2-performance/ch09-anr/05-case-studies.md)

- [第 10 章：内存性能](part2-performance/ch10-memory-perf/README.md)
  - [10.1 App 内存分析](part2-performance/ch10-memory-perf/01-app-memory-analysis.md)
  - [10.2 内存泄漏](part2-performance/ch10-memory-perf/02-memory-leak.md)
  - [10.3 内存持续增长](part2-performance/ch10-memory-perf/03-memory-growth.md)
  - [10.4 低内存对系统性能的影响](part2-performance/ch10-memory-perf/04-low-memory-impact.md)
  - [10.5 案例集](part2-performance/ch10-memory-perf/05-case-studies.md)
  - [10.6 内存抖动与频繁 GC](part2-performance/ch10-memory-perf/06-memory-churn.md)

- [第 11 章：功耗](part2-performance/ch11-power/README.md)
  - [11.1 Android 功耗模型](part2-performance/ch11-power/01-power-model.md)
  - [11.2 App 耗电优化](part2-performance/ch11-power/02-app-power-optimization.md)
  - [11.3 系统级功耗优化](part2-performance/ch11-power/03-system-power-optimization.md)
  - [11.4 案例集](part2-performance/ch11-power/04-case-studies.md)

- [第 12 章：包体积与其他](part2-performance/ch12-apk-network/README.md)
  - [12.1 APK 体积优化](part2-performance/ch12-apk-network/01-apk-size.md)
  - [12.2 网络性能优化](part2-performance/ch12-apk-network/02-network-performance.md)

---

# 第三部分：工具与方法论

- [第 13 章：Perfetto](part3-tools/ch13-perfetto/README.md)
  - [13.1 Perfetto 简介与演进](part3-tools/ch13-perfetto/01-perfetto-intro.md)
  - [13.2 Trace 抓取](part3-tools/ch13-perfetto/02-trace-capture.md)
  - [13.3 Perfetto View 解读](part3-tools/ch13-perfetto/03-perfetto-view.md)
  - [13.4 命令行打开超大 Trace](part3-tools/ch13-perfetto/04-large-traces.md)
  - [13.5 专题解读](part3-tools/ch13-perfetto/05-topic-analysis.md)
  - [13.6 线程 CPU 状态分析](part3-tools/ch13-perfetto/06-thread-cpu-states.md)
  - [13.7 Perfetto 的高级用法](part3-tools/ch13-perfetto/07-advanced-usage.md)

- [第 14 章：其他分析工具](part3-tools/ch14-other-tools/README.md)
  - [14.1 Android Studio Profiler](part3-tools/ch14-other-tools/01-as-profiler.md)
  - [14.2 Simpleperf](part3-tools/ch14-other-tools/02-simpleperf.md)
  - [14.3 内存分析工具](part3-tools/ch14-other-tools/03-memory-tools.md)
  - [14.4 dumpsys 系列命令](part3-tools/ch14-other-tools/04-dumpsys.md)
  - [14.5 三方性能库](part3-tools/ch14-other-tools/05-third-party-libs.md)
  - [14.6 自动化测试工具](part3-tools/ch14-other-tools/06-automation-tools.md)
  - [14.7 ProfilingManager](part3-tools/ch14-other-tools/07-profiling-manager.md)

- [第 15 章：方法论](part3-tools/ch15-methodology/README.md)
  - [15.1 性能优化的术、道、器](part3-tools/ch15-methodology/01-philosophy.md)
  - [15.2 如何区分系统问题和 App 问题](part3-tools/ch15-methodology/02-system-vs-app.md)
  - [15.3 性能指标体系](part3-tools/ch15-methodology/03-metrics.md)
  - [15.4 竞品分析方法](part3-tools/ch15-methodology/04-competitive-analysis.md)
  - [15.5 线上性能监控](part3-tools/ch15-methodology/05-online-monitoring.md)
  - [15.6 性能测试最佳实践](part3-tools/ch15-methodology/06-testing-best-practices.md)
  - [15.7 AOSP 代码阅读](part3-tools/ch15-methodology/07-aosp-reading.md)

---

# 第四部分：系统级优化与行业实践

- [第 16 章：AOSP 性能优化](part4-system/ch16-aosp/README.md)
  - [16.1 Google 官方的性能优化思路](part4-system/ch16-aosp/01-google-optimization.md)
  - [16.2 各 Android 版本性能变更追踪](part4-system/ch16-aosp/02-version-changes.md)
  - [16.3 AOSP 源码编译与调试环境](part4-system/ch16-aosp/03-aosp-build.md)

- [第 17 章：厂商优化实践](part4-system/ch17-oem/README.md)
  - [17.1 OEM 性能优化的通用思路](part4-system/ch17-oem/01-oem-overview.md)
  - [17.2 SoC 平台差异](part4-system/ch17-oem/02-soc-differences.md)
  - [17.3 行业案例](part4-system/ch17-oem/03-industry-cases.md)

---

# 附录

- [A. Android 版本性能变更速查表](appendix/version-changelog.md)
- [B. 常用 adb / dumpsys 命令速查](appendix/commands-cheatsheet.md)
- [C. Perfetto TraceConfig 模板集](appendix/perfetto-templates.md)
- [D. 性能分析 Checklist](appendix/analysis-checklist.md)
- [E. 术语表（中英对照）](appendix/glossary.md)
- [F. 推荐阅读与资源](appendix/recommended-reading.md)
