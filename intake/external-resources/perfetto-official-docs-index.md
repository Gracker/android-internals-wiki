# Perfetto 官方文档索引（perfetto.dev/docs/）

> 来源：https://perfetto.dev/docs/
> 类型：官方文档
> 融入策略：提取事实性知识点，用自己的语言重述，标注原始出处
> 纳入加工：Ch13 相关最高，其他按章节映射排序

## 快速入门（→ Ch13 基础）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/tracing-101 | Tracing 101 | 13.1 简介 | ✅ |
| /docs/getting-started/start-using-perfetto | 开始使用 Perfetto | 13.1 | ✅ |
| /docs/getting-started/system-tracing | 系统级 Trace | 13.2 抓取 | ✅ |
| /docs/getting-started/android-trace-analysis | Android Trace 分析 | 13.3 View 解读 | ✅ |
| /docs/getting-started/ftrace | FTrace 基础 | 13.2 + 新增 FTrace 节 | ✅ |
| /docs/getting-started/cpu-profiling | CPU Profiling | 13.6 CPU 分析 | ✅ |
| /docs/getting-started/memory-profiling | 内存 Profiling | 13.5 专题 | ✅ |
| /docs/getting-started/atrace | ATrace | 13.2 | ✅ |
| /docs/getting-started/in-app-tracing | 应用内 Trace 插桩 | 13.7 高级用法 | ✅ |
| /docs/getting-started/converting | Trace 格式转换 | 13.7 | ✅ |
| /docs/getting-started/other-formats | 其他格式支持 | 13.7 | ✅ |
| /docs/getting-started/periodic-trace-snapshots | 周期性 Trace 快照 | 13.7 | ✅ |

## 核心概念（→ Ch13 理论基础）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/concepts/config | TraceConfig 详解 | 13.2 抓取 | ✅ |
| /docs/concepts/buffers | Buffer 机制 | 13.2 + 附录C | ✅ |
| /docs/concepts/clock-sync | 时钟同步 | 13.3 | ✅ |
| /docs/concepts/service-model | Service 架构 | 13.1 | ✅ |
| /docs/concepts/detached-mode | Detached 模式 | 13.7 | ✅ |
| /docs/concepts/concurrent-tracing-sessions | 并发 Trace 会话 | 13.7 | ✅ |

## 数据源（→ 多章节交叉）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/data-sources/atrace | ATrace 数据源 | 13.2 | ✅ |
| /docs/data-sources/cpu-freq | CPU 频率 | 5.4 DVFS | ✅ |
| /docs/data-sources/cpu-scheduling | CPU 调度 | 5.1 调度基础 | ✅ |
| /docs/data-sources/frametimeline | FrameTimeline | 2.17 Frame Pacing | ✅ |
| /docs/data-sources/java-heap-profiler | Java Heap Profiler | 10.1 App 内存分析 | ✅ |
| /docs/data-sources/native-heap-profiler | Native Heap Profiler | 10.2 内存泄漏 | ✅ |
| /docs/data-sources/memory-counters | 内存计数器 | 4.1 + 10.4 | ✅ |
| /docs/data-sources/syscalls | Syscall 追踪 | 1.1 架构 | ✅ |
| /docs/data-sources/android-log | Android Log | 14.4 dumpsys | ✅ |
| /docs/data-sources/battery-counters | 电池计数器 | 11.1 功耗模型 | ✅ |
| /docs/data-sources/android-game-intervention-list | 游戏干预列表 | 7.4 | ✅ |
| /docs/data-sources/previous-boot-trace | 上次启动 Trace | 8.2 启动分析 | ✅ |

## 分析方法（→ Ch13 SQL/自动化）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/analysis/trace-processor | Trace Processor | 13.3 | ✅ |
| /docs/analysis/perfetto-sql-getting-started | SQL 入门 | 13.3 | ✅ |
| /docs/analysis/perfetto-sql-syntax | SQL 语法 | 13.3 | ✅ |
| /docs/analysis/sql-tables | SQL 表参考 | 13.3 | ✅ |
| /docs/analysis/builtin | 内置函数 | 13.3 | ✅ |
| /docs/analysis/stdlib-docs | 标准库文档 | 13.3 | ✅ |
| /docs/analysis/metrics | Metrics 指标 | 13.6 + 15.3 | ✅ |
| /docs/analysis/trace-summary | Trace 摘要 | 13.3 | ✅ |
| /docs/analysis/sql-stats | SQL 统计 | 13.3 | ✅ |
| /docs/analysis/trace-processor-python | Python API | 13.7 | ✅ |
| /docs/analysis/batch-trace-processor | Batch 处理 | 13.7 | ✅ |
| /docs/analysis/perfetto-sql-backcompat | SQL 向后兼容 | 13.3 | ✅ |
| /docs/analysis/style-guide | SQL 风格指南 | 13.3 | ✅ |
| /docs/analysis/debug-tracks | Debug Tracks | 13.3 | ✅ |

## 可视化（→ Ch13 UI 操作）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/visualization/perfetto-ui | UI 使用 | 13.3 | ✅ |
| /docs/visualization/large-traces | 超大 Trace 处理 | 13.4 | ✅ |
| /docs/visualization/commands-automation-reference | 命令自动化 | 13.7 | ✅ |
| /docs/visualization/deep-linking-to-perfetto-ui | 深度链接 | 13.3 | ✅ |
| /docs/visualization/ui-automation | UI 自动化 | 13.7 | ✅ |
| /docs/visualization/extending-the-ui | UI 扩展 | 13.7 | ✅ |
| /docs/visualization/extension-servers | 扩展服务 | 13.7 | ✅ |
| /docs/visualization/extension-server-protocol | 扩展协议 | 13.7 | ✅ |

## 案例研究（→ Ch07/Ch08/Ch10）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/case-studies/android-boot-tracing | Android 启动 Trace | 8.2 App 启动 | ✅ |
| /docs/case-studies/scheduling-blockages | 调度阻塞分析 | 5.1 + 7.2 | ✅ |
| /docs/case-studies/memory | 内存分析案例 | 10.5 案例集 | ✅ |
| /docs/case-studies/android-outofmemoryerror | OOM 分析 | 10.4 低内存 | ✅ |

## 插桩指南（→ Ch13 高级用法）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/instrumentation/track-events | Track Events | 13.7 | ✅ |
| /docs/instrumentation/tracing-sdk | Tracing SDK | 13.7 | ✅ |
| /docs/instrumentation/interceptors | Interceptors | 13.7 | ✅ |

## 参考手册（→ 附录）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/reference/android-version-notes | Android 版本变更 | 附录A | ✅ |
| /docs/reference/perfetto-cli | Perfetto CLI | 13.2 | ✅ |
| /docs/reference/trace-config-proto | TraceConfig Proto | 附录C | ✅ |
| /docs/reference/trace-packet-proto | TracePacket Proto | 13.3 | ✅ |
| /docs/reference/traced | traced 守护进程 | 13.1 | ✅ |
| /docs/reference/traced_probes | traced_probes | 13.1 | ✅ |
| /docs/reference/heap_profile-cli | Heap Profile CLI | 10.1 | ✅ |
| /docs/reference/kernel-track-event | Kernel Track Event | 13.2 | ✅ |
| /docs/reference/synthetic-track-event | Synthetic Track Event | 13.3 | ✅ |
| /docs/reference/tracebox | tracebox | 13.7 | ✅ |

## 部署（→ 线上监控/CI）
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/deployment/deploying-bigtrace-on-a-single-machine | BigTrace 单机部署 | 15.5 线上监控 | ✅ |
| /docs/deployment/deploying-bigtrace-on-kubernetes | BigTrace K8s 部署 | 15.5 线上监控 | ✅ |

## 其他
| URL | 标题 | 映射章节 | 纳入加工 |
|-----|------|---------|--------|
| /docs/faq | FAQ | 13.1 | ✅ |
| /docs/learning-more/android | Android 进一步学习 | 15.7 | ✅ |
| /docs/learning-more/tracing-in-background | 后台 Trace | 15.5 | ✅ |
| /docs/quickstart/traceconv | traceconv 工具 | 13.7 | ✅ |

## 统计
- 总文档数：~90 篇
- 全部纳入加工：~90 篇（按章节映射分批处理）
- 跨章节引用：data-sources 和 case-studies 覆盖 Ch01/Ch02/Ch04/Ch05/Ch07/Ch08/Ch10/Ch11/Ch13/Ch15 + 附录
