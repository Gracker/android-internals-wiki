# 第 14 章：其他分析工具

Perfetto 提供统一时间轴，其他工具用于回答 CPU sampling、heap、布局、GPU、构建产物和线上观测等不同问题。

工具选择应由问题和证据类型决定。CPU sample、Heap Dump、命令行快照、GPU capture 与线上 telemetry 不能互相替代。

## 内容索引

- [14.1 Android Studio Profiler](01-as-profiler.md)
- [14.2 Simpleperf](02-simpleperf.md)
- [14.3 内存分析工具](03-memory-tools.md)
- [14.4 dumpsys 系列命令](04-dumpsys.md)
- [14.5 三方性能库](05-third-party-libs.md)
- [14.6 自动化测试工具](06-automation-tools.md)
- [14.7 ProfilingManager](07-profiling-manager.md)
- [14.8 GPU 图形调试与分析工具](08-gpu-debug-tools.md)
- [14.9 Android Camera 性能与 Perfetto 分析](09-camera-performance-analysis.md)
- [14.10 eBPF/BPF 在 Android 性能分析中的应用](10-ebpf-performance-analysis.md)
- [14.11 Battery Historian 与功耗分析工具](11-battery-historian.md)
- [14.12 APM / 可观测性平台与 SDK 选型](12-apm-observability.md)
- [14.13 Hook 基础设施与性能工具实现原理](13-hook-infrastructure.md)
- [14.14 Android Studio LeakCanary Profiler 与 Heap Dump 分析](14-android-studio-leakcanary-profiler.md)
- [14.15 Winscope 与窗口/合成状态可视化调试](15-winscope-window-composition-debugging.md)
- [14.16 Layout Inspector 与 ViewDebug 布局调试](16-layout-inspector-viewdebug.md)
- [14.17 statsd 与系统级指标采集](17-statsd-system-metrics.md)
- [14.18 Android Performance Analyzer 与系统性能分析](18-android-performance-analyzer.md)
- [14.19 Android CLI 与 Agent 化性能调试工作流](19-android-cli-agent-performance-workflow.md)
- [14.20 R8 Configuration Analyzer 与 keep 规则体积归因](20-r8-configuration-analyzer.md)
- [14.21 eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织](21-ebpf-bpfloader-architecture.md)
- [14.22 HPROF Heap Dump 管线与 Perfetto java_hprof data source](22-hprof-heapdump-javahprof-datasource.md)
- [14.23 StrictMode 性能检查与开发期诊断](23-strictmode-performance-diagnostics.md)
- [14.24 Android 17 simpleperf 微架构级性能采样与工作流增强](24-android17-simpleperf-microarch-profiling.md)
- [14.25 Android 17 eBPF 性能可观测性程序 matrix 扩展](25-android17-ebpf-observability-matrix.md)
- [14.27 Macrobenchmark 框架与自动化性能门禁](27-macrobenchmark-automation-gate.md)
- [14.28 Perfetto GPU Counter 与 GPU Memory 事件分析](28-gpu-performance-profiling-advanced.md)
- [14.29 Android 17 AGI Frame Profiler gapii Spy 架构与单帧 GPU 捕获机制](14.29-android17-agi-frame-profiler-gapii-spy.md)
- [14.30 GpuService GPU 内存可观测性架构](14.30-android17-gpuservice-gpu-memory-observability.md)
- [14.31 FTrace：内核 tracefs + atrace 桥 + Perfetto probe](14.31-android17-ftrace-atrace-perfetto-bridge.md)
- [14.32 ARM Topdown 微架构性能分析方法论与 Android 实践](32-arm-topdown-microarch-performance-analysis.md)

## 阅读建议

- 如果你已经会看 Perfetto，这一章会告诉你什么时候该换工具，而不是继续硬看 trace。
- 线上治理场景可优先阅读 APM、Hook、ProfilingManager 与自动化条目。
