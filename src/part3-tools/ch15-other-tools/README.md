# 第 15 章：其他分析工具

Perfetto 适合把调度、进程、渲染和应用事件放到同一条时间轴上。本章补充需要专门采集方式或其他证据形态的工具：CPU sampling（周期采集调用栈，估算 CPU 时间集中在哪些函数）、Heap Dump（某一时刻的堆对象快照）、布局层级检查、GPU capture（记录单帧命令、资源和管线状态）、构建产物分析，以及 production telemetry（线上长期汇总的指标和事件）。

工具选择取决于问题和所需证据。CPU sample 提供统计调用栈，Heap Dump 提供对象关系，命令行快照提供某一时刻的系统状态，GPU capture 提供单帧细节，线上 telemetry 则用于观察较长时间和大量设备上的趋势。它们回答的问题不同，结论也不能直接互换。

## 内容索引


- [15.1 Android Studio Profiler](01-as-profiler.md)
- [15.2 Simpleperf 与 ARM Topdown 微架构分析](02-simpleperf-arm-topdown.md)
- [15.3 内存分析、HPROF 与 Heap Dump 工具](03-memory-hprof-heapdump-tools.md)
- [15.4 dumpsys 系列命令](04-dumpsys.md)
- [15.5 Battery Historian 与功耗分析工具](05-battery-historian.md)
- [15.6 自动化性能测试与 CLI Agent 工作流](06-automation-cli-agent-workflow.md)
- [15.7 ProfilingManager](07-profiling-manager.md)
- [15.8 statsd 与系统级指标采集](08-statsd-system-metrics.md)
- [15.9 StrictMode 性能检查与开发期诊断](09-strictmode-performance-diagnostics.md)
- [15.10 三方性能库、Hook 与可观测性基础设施](10-third-party-hook-observability.md)
- [15.11 GPU 调试与 AGI 单帧分析](11-gpu-debug-agi-frame-analysis.md)
- [15.12 GPU Counter、内存与 GpuService 可观测性](12-gpu-counter-memory-observability.md)
- [15.13 Android Performance Analyzer 与 GAPS：性能追踪与目标可达性](13-performance-analyzer-gaps.md)
- [15.14 Camera 性能分析工具：Perfetto、SQL 与 GFXReconstruct](14-camera-performance-analysis.md)
- [15.15 Winscope、Layout Inspector 与 UI 状态调试](15-winscope-layout-inspector-ui-debugging.md)
- [15.16 Android eBPF 架构与性能观测](16-android-ebpf-architecture-observability.md)
- [15.17 R8 Configuration Analyzer 与 keep 规则体积归因](17-r8-configuration-analyzer.md)

## 阅读建议

- 如果你已经会看 Perfetto，可先判断所需证据是否存在于系统 trace；缺少函数调用栈、对象图或单帧 GPU 状态时，再选择对应的专用工具。
- CPU 调查可在 15.1—15.2 中选择 IDE 集成分析器、simpleperf 采样器或基于 PMU（处理器硬件性能计数器）的微架构分析；内存对象与 Heap Dump 调查转到 15.3。
- 系统命令快照与功耗工具见 15.4—15.5；自动化回归、线上 profiling、statsd、StrictMode 和 CLI/Agent 工作流见 15.6—15.9。这里的 Agent 工作流指由自动化代理编排命令、采集和分析步骤。
- GPU、相机、窗口合成和布局层级问题集中在 15.11—15.15，应按问题选择帧捕获、GPU Counter、Camera Trace、Winscope 或 Layout Inspector。
- 第三方 Hook、动态可达性、eBPF 与 R8 规则分析分别见 15.10、15.13、15.16 和 15.17。使用前应先确认 Android 版本、构建类型、权限和数据安全边界。
