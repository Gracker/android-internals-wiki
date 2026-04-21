# 知识盲区清单

## [External Review Integration] 2026-04-21

本次整合未提取到知识盲区内容。外部 review 文件主要关注一般修正建议，暂未识别需要后续研究的技术盲区。

## [2026-04-21] 14.11 Battery Historian 与功耗分析工具 — 知识盲区

### 盲区描述
external-review 已命中 Android 15+ 的代码级功耗采集能力，但正文仍停留在 Studio Power Profiler 视角，缺少 `SystemHealthManager.getSupportedPowerMonitors()` / `getPowerMonitorReadings()`、`PowerMonitor`、`PowerMonitorReadings` 这一整组 PowerMonitor API。

### 重要程度
高

### 建议研究方向
- 核对 Android 15(API 35) PowerMonitor API 的入口类、异步回调模型和设备支持条件
- 研究 PowerMonitor 结果如何与 Macrobenchmark、线上监控和离线 bugreport 分析拼成统一功耗链路
- 区分真实 power rail 与 modeled energy consumer，补清适用边界

### 关联章节
- 14.11
- 11.2
- 15.5

## [2026-04-21] 15.6 Testing Best Practices — 知识盲区

### 盲区描述
稳态性能测试（Steady-state Performance）方法论缺失。现代 SoC（骁龙 8 系等）峰值功耗远超机身散热极限，持续负载下触发 20%~30% 性能衰减，但文章仅覆盖短时峰值性能测试。

### 重要程度
高

### 建议研究方向
- 明确区分微观峰值性能基准与宏观稳态性能基准的设计差异
- 针对游戏/长视频等重负载场景，建立热稳定态测试方法论
- 研究如何让设备发热到热平衡点后再采样的 Benchmark 设计模式

### 关联章节
- 15.6
- 15.8

### 外部 review 来源
- Gemini 外部 review（06-15.6）

## [2026-04-21] 14.1 Android Studio Profiler — 知识盲区

### 盲区描述
Profiler System Trace 与纯 CLI Perfetto Trace 的默认 Config 差异未梳理。虽然底层都是 Perfetto，但 Profiler 默认开启的 atrace tag 可能与命令行 `record_android_trace` 有区别。

### 重要程度
中

### 建议研究方向
- 导出 Profiler 的 `.perfetto-trace` 并在 ui.perfetto.dev 查看其 data sources 配置
- 对比 Profiler 默认 config 与 `record_android_trace` 默认 config 的差异

### 关联章节
- 14.1
- 13.1

### 外部 review 来源
- Gemini 外部 review（14-01）

## [2026-04-21] 14.2 Simpleperf — 知识盲区

### 盲区描述
Android PMU 权限管控：不同 Android 版本下 `perf_event_paranoid` 的默认值差异，以及 `simpleperf list` 在 Root / 非 Root 下的输出区别。跨厂商 PMU 事件名差异（高通 Snapdragon vs 联发科 Dimensity）。

### 重要程度
高

### 建议研究方向
- 调研不同 Android 版本下 `kernel.perf_event_paranoid` 的默认值差异
- 梳理高通 Snapdragon 与联发科 Dimensity 对自定义 PMU 事件命名的差异
- 查阅 AOSP `system/core/rootdir/init.rc` 中关于 sysctl 的配置

### 关联章节
- 14.2
- 14.10

### 外部 review 来源
- Gemini 外部 review（14-02）

## [2026-04-21] 14.3 Memory Tools — 知识盲区

### 盲区描述
缺少 `libmemunreachable` 工具的介绍。API 24 引入了该工具（通过 `dumpsys meminfo --unreachable` 触发），是零开销的 Native 内存泄漏检测方案，基于类似 GC 的标记-清除算法。

### 重要程度
中

### 建议研究方向
- 研究 `dumpsys meminfo --unreachable` 的底层工作原理及适用场景
- 评估是否应作为独立小节补充到 Native 内存排查路径中
- 与 heapprofd 的适用场景对比

### 关联章节
- 14.3
- 10.2 内存泄漏

### 外部 review 来源
- Gemini 外部 review（14-03）

## [2026-04-21] 14.4 Dumpsys 系列命令 — 知识盲区

### 盲区描述
现代 Android (10+) 中 LMKD 依赖内核的 PSI (Pressure Stall Information) 指标来触发杀进程，而不是单纯看内存水位。此机制未在任何章节中覆盖。

### 重要程度
高

### 建议研究方向
- 研究 PSI 节点在 dumpsys 或 lmkd 日志中的体现
- 分析最新的"无故杀进程"问题时 PSI 指标的使用方法
- lmkd 从 minfree 模式迁移到 PSI 模式的版本演进

### 关联章节
- 14.4
- 系统内存管理 / LMKD 专门章节

### 外部 review 来源
- Gemini 外部 review（14-04）

## [2026-04-21] 14.5 三方性能库 — 知识盲区

### 盲区描述
AGP 8.0+ 的 Instrumentation API (`AsmClassVisitorFactory`) 插桩新范式；ShadowHook（字节跳动 Inline Hook 库）原理；btrace 3.0 同步抓栈采样机制。

### 重要程度
高

### 建议研究方向
- 研究 Instrumentation API 与旧版 Transform API 在性能、并行处理、增量编译上的实现差异
- 研究 ShadowHook 如何解决 ARM/ARM64 架构下的指令重写与寄存器状态保存问题
- 研究 btrace 3.0 同步抓栈方案如何在保证精度同时极大地降低开销

### 关联章节
- 14.5
- 编译构建/插桩相关章节

### 外部 review 来源
- Gemini 外部 review（14-05）

## [2026-04-21] 14.6 自动化测试工具 — 知识盲区

### 盲区描述
ODPM 硬件支持限制：哪些设备能够真正跑通 PowerMetric 高精度模式。BaselineProfileRule 自动化生成 Baseline Profile 的工程应用。

### 重要程度
高

### 建议研究方向
- 明确支持 ODPM 的设备列表及 PowerMetric 高精度模式的前提条件
- 研究 BaselineProfileRule 与 MacrobenchmarkRule 同源工具的 CI 集成策略

### 关联章节
- 14.6
- 第 8 章启动优化（Baseline Profile 生成流程）

### 外部 review 来源
- Gemini 外部 review（14-06）

## [2026-04-21] 14.7 ProfilingManager — 知识盲区

### 盲区描述
Android 17 的 `TRIGGER_TYPE_ANOMALY` 判定机制：如何对异常 Binder 调用和内存进行判定并自动触发 trace。

### 重要程度
中

### 建议研究方向
- 结合 AOSP 中新增的 Anomaly 判定服务源码，研究其异常行为定义与识别逻辑
- 关注 Android 17 稳定版发布后的官方文档更新

### 关联章节
- 14.7

### 外部 review 来源
- Gemini 外部 review（14-07）

## [2026-04-21] 14.8 GPU 调试工具 — 知识盲区

### 盲区描述
Tile-Based Rendering 对 GPU 计数器的影响：Mali/Adreno 在 Tilers 阶段的专用计数器含义差异。ANGLE 对 Shader 编译时间的影响：原生驱动 vs ANGLE 初次运行编译尖刺差异。

### 重要程度
高

### 建议研究方向
- 研究 Mali/Adreno 在 Tilers 阶段的专用计数器含义差异
- 比较原生驱动 vs ANGLE 在初次运行时的 Shader 编译时间差异

### 关联章节
- 14.8
- 2.9 GPU 渲染管线

### 外部 review 来源
- Gemini 外部 review（14-08）

## [2026-04-21] 14.9 Android Camera 性能与 Perfetto 分析 — 知识盲区

### 盲区描述
16 KB Page Size 对 Camera Buffer 的影响：Android 15 引入 16KB Page 支持，对 Camera 大块 Buffer 的对齐和碎片化有何影响未覆盖。

### 重要程度
中

### 建议研究方向
- Android 15 16KB Page 对 Camera Buffer 分配和对齐策略的影响
- Display Sync 与 PreviewSpacer 在启用 Display Sync 模式下的交互行为

### 关联章节
- 14.9
- 内存管理相关章节

### 外部 review 来源
- Gemini 外部 review（14-09）

## [2026-04-21] 14.10 eBPF/BPF 性能分析 — 知识盲区

### 盲区描述
uprobe 探针在 Android ARM64 设备上的精确执行延迟定量数据；脱离 AOSP 完整源码树使用 NDK 编译 Android 可用 BPF 程序的工具链构建方法。

### 重要程度
高

### 建议研究方向
- 设计 Benchmark，测量空方法、带 uprobe 的空方法、系统调用的耗时对比
- 研究如何在脱离 AOSP 完整源码树的情况下使用 NDK 编译 Android 可用的 BPF 程序

### 关联章节
- 14.10
- 15.6 性能测试方法论

### 外部 review 来源
- Gemini 外部 review（14-10）

## [2026-04-21] 14.11 Battery Historian — 知识盲区补充

### 盲区描述
Perfetto `android.power_rails` 数据源的分析方法：ODPM 轨道功耗数据记录在系统级 Trace 中，可通过 Perfetto SQL 深度分析与 CPU 调度/线程事件的关联。

### 重要程度
高

### 建议研究方向
- Perfetto 官方文档关于功耗轨道的 SQL 查询实战
- power_rails 与 CPU 调度事件的 join 关联分析
- 线上 APM 与自动化 CI 测试场景中的功耗数据采集方案

### 关联章节
- 14.11
- 15.5 线上性能监控

### 外部 review 来源
- Gemini 外部 review（14-11）

