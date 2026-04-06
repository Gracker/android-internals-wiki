# Google 官方文档索引（developer.android.com）

> 来源：https://developer.android.google.cn/
> 类型：官方文档
> 融入策略：提取事实性知识点，用自己的语言重述，标注原始出处
> 全部纳入加工

---

## For App 开发者

| URL | 标题 | 映射章节 | 状态 |
|-----|------|---------|------|
| /topic/performance/performance-class | Performance Class | 15.4 竞品分析 | ✅ |
| /guide/components/processes-and-threads | 进程与线程概览 | 1.3 进程模型 | ✅ |
| /topic/performance/threads | 通过线程优化性能 | 1.5 线程模型 | ✅ |
| /topic/performance/power | 优化电池续航 | 11.2 App 耗电优化 | ✅ |
| /training/monitoring-device-state/doze-standby | Doze 与 App Standby 优化 | 11.2 + 5.8 后台执行限制 | ✅ |
| /topic/performance/reduce-apk-size | 减小 APK 体积 | 12.1 APK 体积优化 | ✅ |
| /topic/performance/memory-overview | 内存管理概览 | 4.1 内存模型 | ✅ |
| /topic/performance/memory-management | 进程间内存分配 | 4.1 + 4.4 LMK | ✅ |
| /topic/performance/memory | 管理 App 内存 | 4.5 App 内存优化 | ✅ |
| /guide/practices/app-design/seamlessness | 无缝设计 | 7.1 + 8.1 | ✅ |
| /training/articles/perf-anr | 保持 App 响应（ANR） | 9.1 ANR 设计 | ✅ |
| /training/articles/smp | Android SMP 入门 | 5.3 大小核架构 | ✅ |
| /guide/practices/verifying-apps-art | ART 运行时验证 | 1.7 ART 编译管线 | ✅ |

---

## 性能分析工具

### Perfetto

| URL | 标题 | 映射章节 | 状态 |
|-----|------|---------|------|
| /studio/command-line/perfetto | Perfetto 介绍 | 13.1 | ✅ |
| https://perfetto.dev/docs/quickstart/android-tracing | Android Trace 抓取 | 13.2 | ✅ |
| https://perfetto.dev/docs/quickstart/linux-tracing | Linux Trace 抓取 | 13.2 | ✅ |
| https://perfetto.dev/docs/quickstart/trace-analysis | SQL 分析与 Metrics | 13.3 | ✅ |
| https://perfetto.dev/docs/quickstart/traceconv | Trace 格式转换 | 13.7 | ✅ |
| https://perfetto.dev/docs/quickstart/heap-profiling | Heap Profiling | 10.1 + 10.2 | ✅ |

### System Tracing

| URL | 标题 | 映射章节 | 状态 |
|-----|------|---------|------|
| /topic/performance/tracing | 系统级 Trace 概览 | 13.1 + 13.2 | ✅ |
| /topic/performance/tracing/command-line | 命令行抓取 Trace | 13.2 | ✅ |
| /topic/performance/tracing/on-device | 设备端 Trace | 13.2 | ✅ |
| /topic/performance/tracing/navigate-report | Systrace 报告导航 | 13.3 | ✅ |
| /topic/performance/tracing/custom-events | 自定义 Trace 事件（Java） | 13.7 | ✅ |
| /topic/performance/tracing/custom-events-native | 自定义 Trace 事件（Native） | 13.7 | ✅ |

### Android Vitals（→ Ch15 线上监控）

| URL | 标题 | 映射章节 | 状态 |
|-----|------|---------|------|
| /topic/performance/vitals | Android Vitals 概览 | 15.5 线上监控 | ✅ |
| /topic/performance/vitals/anr | ANR 率 | 9.2 ANR 类型 + 15.5 | ✅ |
| /topic/performance/vitals/crash | Crash 率 | 15.5 | ✅ |
| /topic/performance/vitals/wakeup | 过度唤醒 | 11.2 + 15.5 | ✅ |
| /topic/performance/vitals/wakelock | Wake Lock 卡死 | 11.2 + 15.5 | ✅ |
| /topic/performance/vitals/bg-wifi | 后台 Wi-Fi 扫描过多 | 11.2 + 15.5 | ✅ |
| /topic/performance/vitals/bg-network-usage | 后台网络使用过多 | 11.2 + 15.5 | ✅ |
| /topic/performance/vitals/launch-time | App 启动时间 | 8.2 + 15.5 | ✅ |
| /topic/performance/vitals/render | 渲染缓慢 | 7.1 + 15.5 | ✅ |
| /topic/performance/vitals/frozen | 冻结帧 | 7.1 + 15.5 | ✅ |
| /topic/performance/vitals/permissions | 权限拒绝 | 15.5 | ✅ |

### Android Studio Profilers

| URL | 标题 | 映射章节 | 状态 |
|-----|------|---------|------|
| /studio/profile/android-profiler | Profiler 概览 | 14.1 | ✅ |
| /studio/profile/cpu-profiler | CPU Profiler | 14.1 | ✅ |
| /studio/profile/record-traces | 录制 Trace | 14.1 | ✅ |
| /studio/profile/export-traces | 导出 Trace | 14.1 | ✅ |
| /studio/profile/import-traces | 导入 Trace | 14.1 | ✅ |
| /studio/profile/inspect-traces | 检查 Trace | 14.1 | ✅ |
| /studio/profile/jank-detection | UI Jank 检测 | 14.1 + 7.1 | ✅ |
| /studio/profile/generate-trace-logs | 生成 Trace 日志（插桩） | 14.1 | ✅ |
| /studio/profile/memory-profiler | Memory Profiler | 14.3 内存分析工具 | ✅ |
| /studio/profile/energy-profiler | Energy Profiler | 11.1 + 14.1 | ✅ |
| /studio/profile/apk-profiler | APK Profiler | 14.1 | ✅ |

### Benchmark Tools（→ Ch15 性能测试）

| URL | 标题 | 映射章节 | 状态 |
|-----|------|---------|------|
| /studio/profile/benchmarking-overview | Benchmark 概览 | 15.6 性能测试 | ✅ |
| /studio/profile/microbenchmark-overview | Microbenchmark 概览 | 15.6 | ✅ |
| /studio/profile/microbenchmark-write | 编写 Microbenchmark | 15.6 | ✅ |
| /studio/profile/microbenchmark-profile | Profiling Microbenchmark | 15.6 | ✅ |
| /studio/profile/microbenchmark-instrumentation-args | Microbenchmark 参数 | 15.6 | ✅ |
| /studio/profile/microbenchmark-without-gradle | 无 Gradle 构建 Microbenchmark | 15.6 | ✅ |
| /studio/profile/macrobenchmark-overview | Macrobenchmark 概览 | 15.6 + 8.3 启动优化 | ✅ |
| /studio/profile/macrobenchmark-metrics | Macrobenchmark 指标 | 15.6 | ✅ |
| /studio/profile/macrobenchmark-control-app | Macrobenchmark 控制 App | 15.6 | ✅ |
| /studio/profile/macrobenchmark-instrumentation-args | Macrobenchmark 参数 | 15.6 | ✅ |
| /studio/profile/benchmarking-in-ci | CI 中的 Benchmark | 15.6 | ✅ |
| /studio/profile/jankstats | JankStats 库 | 7.1 + 15.6 | ✅ |
| /studio/profile/baselineprofiles | Baseline Profiles | 8.7 | ✅ |
| /studio/profile/measuring-performance | 性能测量概览 | 15.6 | ✅ |
| /studio/profile/performance-measurement-examples | 性能测量与分析示例 | 15.6 | ✅ |

### Simpleperf

| URL | 标题 | 映射章节 | 状态 |
|-----|------|---------|------|
| /ndk/guides/simpleperf | Simpleperf 官方文档 | 14.2 | ✅ |
| https://www.ruanyifeng.com/blog/2017/09/flame-graph.html | 如何读懂火焰图 | 14.2 | ✅ |
| http://www.brendangregg.com/flamegraphs.html | Flame Graphs（Brendan Gregg） | 14.2 | ✅ |

---

## 覆盖章节汇总

| AIW 章节 | 文档数 |
|---------|--------|
| 1.3 进程模型 | 1 |
| 1.5 线程模型 | 1 |
| 1.7 ART 编译管线 | 1 |
| 4.1 内存模型 | 2 |
| 4.5 App 内存优化 | 1 |
| 5.3 大小核架构 | 1 |
| 5.8 后台执行限制 | 1 |
| 7.1 卡顿定义 | 3 |
| 8.1 响应速度原理 | 1 |
| 8.2 App 启动 | 1 |
| 8.3 启动优化 | 1 |
| 8.7 Baseline Profiles | 1 |
| 9.1 ANR 设计 | 1 |
| 9.2 ANR 类型 | 1 |
| 10.1 App 内存分析 | 1 |
| 10.2 内存泄漏 | 1 |
| 11.1 功耗模型 | 1 |
| 11.2 App 耗电优化 | 3 |
| 12.1 APK 体积优化 | 1 |
| 13.1 Perfetto 简介 | 2 |
| 13.2 Trace 抓取 | 4 |
| 13.3 View 解读 | 2 |
| 13.7 高级用法 | 3 |
| 14.1 AS Profiler | 7 |
| 14.2 Simpleperf | 3 |
| 14.3 内存分析工具 | 1 |
| 15.4 竞品分析 | 1 |
| 15.5 线上监控 | 11 |
| 15.6 性能测试 | 14 |
| **合计** | **~70 篇** |

## 特别关注

### Android Vitals（11 篇 → 15.5 线上监控）
这是目前 AIW 中覆盖最薄的一块。15.5 "线上性能监控" 如果已有草稿，这 11 篇官方文档是最权威的素材来源，建议优先融入。

### Benchmark Tools（14 篇 → 15.6 性能测试）
Microbenchmark + Macrobenchmark + JankStats + Baseline Profiles 是完整的性能测试工具链，15.6 可以基于这组文档构建完整的性能测试最佳实践章节。

### Energy Profiler（1 篇 → 11.1 + 14.1）
功耗分析目前 AIW 覆盖较浅，Energy Profiler 的官方文档可以帮助补充 11.1 功耗模型和 14.1 的工具覆盖。
