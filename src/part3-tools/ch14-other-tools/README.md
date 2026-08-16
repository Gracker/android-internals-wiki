# 第 14 章：其他分析工具

Perfetto 适合把调度、进程、渲染和应用事件放到同一条时间轴上。本章补充需要专门采集方式或其他证据形态的工具：CPU sampling（周期采集调用栈，估算 CPU 时间集中在哪些函数）、Heap Dump（某一时刻的堆对象快照）、布局层级检查、GPU capture（记录单帧命令、资源和管线状态）、构建产物分析，以及 production telemetry（线上长期汇总的指标和事件）。

工具选择取决于问题和所需证据。CPU sample 提供统计调用栈，Heap Dump 提供对象关系，命令行快照提供某一时刻的系统状态，GPU capture 提供单帧细节，线上 telemetry 则用于观察较长时间和大量设备上的趋势。它们回答的问题不同，结论也不能直接互换。

## 内容索引

- [14.1 Android Studio Profiler](01-as-profiler.md)
- [14.2 Simpleperf](02-simpleperf.md)
- [14.3 Android 17 simpleperf 微架构级性能采样与工作流增强](03-android17-simpleperf-microarch-profiling.md)
- [14.4 ARM Topdown 微架构性能分析方法论与 Android 实践](04-arm-topdown-microarch-performance-analysis.md)
- [14.5 内存分析工具](05-memory-tools.md)
- [14.6 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源](06-hprof-heapdump-javahprof-datasource.md)
- [14.7 dumpsys 系列命令](07-dumpsys.md)
- [14.8 Battery Historian 与功耗分析工具](08-battery-historian.md)
- [14.9 自动化性能测试与回归门禁](09-automation-tools.md)
- [14.10 三方性能库与可观测性选型](10-third-party-libs-observability.md)
- [14.11 ProfilingManager](11-profiling-manager.md)
- [14.12 statsd 与系统级指标采集](12-statsd-system-metrics.md)
- [14.13 StrictMode 性能检查与开发期诊断](13-strictmode-performance-diagnostics.md)
- [14.14 Android CLI 与 Agent 化性能调试工作流](14-android-cli-agent-performance-workflow.md)
- [14.15 GPU 图形调试与分析工具](15-gpu-debug-tools.md)
- [14.16 Perfetto GPU Counter 与 GPU Memory 事件分析](16-gpu-performance-profiling-advanced.md)
- [14.17 Android Performance Analyzer 与系统性能分析](17-android-performance-analyzer.md)
- [14.18 Android 17 AGI Frame Profiler gapii Spy 架构与单帧 GPU 捕获机制](18-android17-agi-frame-profiler-gapii-spy.md)
- [14.19 GpuService GPU 内存可观测性架构](19-android17-gpuservice-gpu-memory-observability.md)
- [14.20 Android Camera 性能与 Perfetto 分析](20-camera-performance-analysis.md)
- [14.21 Winscope 与窗口/合成状态可视化调试](21-winscope-window-composition-debugging.md)
- [14.22 Layout Inspector 与 ViewDebug 布局调试](22-layout-inspector-viewdebug.md)
- [14.23 eBPF/BPF 在 Android 性能分析中的应用](23-ebpf-performance-analysis.md)
- [14.24 eBPF 系统架构：bpfloader Rust 化与 BPF 程序组织](24-ebpf-bpfloader-architecture.md)
- [14.25 Android 17 eBPF 性能可观测性程序矩阵扩展](25-android17-ebpf-observability-matrix.md)
- [14.26 Hook 基础设施与性能工具实现原理](26-hook-infrastructure.md)
- [14.27 R8 Configuration Analyzer 与 keep 规则体积归因](27-r8-configuration-analyzer.md)
- [14.28 GAPS：Android 动态分析目标可达性路径重建](28-gaps-dynamic-analysis.md)

## 阅读建议

- 如果你已经会看 Perfetto，可先判断所需证据是否存在于系统 trace；缺少函数调用栈、对象图或单帧 GPU 状态时，再选择对应的专用工具。
- CPU 调查可在 14.1—14.4 中选择 IDE 集成分析器、simpleperf 采样器或基于 PMU（处理器硬件性能计数器）的微架构分析；内存对象与 Heap Dump 调查转到 14.5—14.6。
- 系统命令快照与功耗工具见 14.7—14.8；自动化回归、线上 profiling、statsd、StrictMode 和 CLI/Agent 工作流见 14.9—14.14。这里的 Agent 工作流指由自动化代理编排命令、采集和分析步骤。
- GPU、相机、窗口合成和布局层级问题集中在 14.15—14.22，应按问题选择帧捕获、GPU Counter、Winscope 或 Layout Inspector。
- 14.23—14.28 覆盖 eBPF（在内核验证后运行的观测程序）、Hook（在函数或事件路径上插入拦截点）、R8 规则分析与动态可达性分析。使用前应先确认 Android 版本、构建类型、权限和数据安全边界。
