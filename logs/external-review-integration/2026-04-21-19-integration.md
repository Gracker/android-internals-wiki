# External Review Integration Log — 2026-04-21 19:25

## 概要
- 扫描活跃 external-review 文件：14 个（排除 batch-review-summary）
- 成功整合：14 个
- 跳过（已有覆盖）：0 个

## 写入结果
- queue.json：新增 8 条 + 合并 2 条（14.9、14.11 已有 task9 条目）
- research-gaps.md：新增 12 条
- suggestions.md：新增 12 条

## 处理明细

### 新增 queue 条目
| 章节 | 标题 | 优先级 | 来源文件 |
|------|------|--------|----------|
| 15.6 | Testing Best Practices | 85 | 06-15.6 |
| 14.1 | Android Studio Profiler | 85 | 14-01 |
| 14.2 | Simpleperf | 95 | 14-02 |
| 14.3 | Memory Tools | 85 | 14-03 |
| 14.5 | 三方性能库 | 95 | 14-05 |
| 14.6 | 自动化测试工具 | 85 | 14-06 |
| 14.8 | GPU 调试工具 | 95 | 14-08 |
| 14.10 | eBPF/BPF 性能分析 | 95 | 14-10 |

### 合并 queue 条目
| 章节 | 标题 | 合并来源 | 新增 issues 数 |
|------|------|----------|---------------|
| 14.9 | Camera 性能与 Perfetto 分析 | task9-deep-tech-review | 3 条 |
| 14.11 | Battery Historian | task9-deep-tech-review | 2 条 |

### 已覆盖（跳过新增 queue）
| 章节 | 原因 |
|------|------|
| 15.7 | 无 P0/P1 问题，仅含可复用知识资产 |
| 15.8 | 仅 P2 问题，已写入 suggestions |
| 14.4 | 已有 task6-review 条目覆盖所有 P0/P1 |
| 14.7 | 无 P0/P1 问题，仅含 P2 建议 |

### 涉及章节
- 15.6 Testing Best Practices
- 15.7 AOSP 源码阅读方法论
- 15.8 实证性能问题研究
- 14.1 Android Studio Profiler
- 14.2 Simpleperf
- 14.3 Memory Tools
- 14.4 Dumpsys 系列命令
- 14.5 三方性能库
- 14.6 自动化测试工具
- 14.7 ProfilingManager
- 14.8 GPU 调试工具
- 14.9 Android Camera 性能与 Perfetto 分析
- 14.10 eBPF/BPF 性能分析
- 14.11 Battery Historian 与功耗分析工具

### 可复用知识资产（保留在 external-review 文件中）
以下文件包含高价值一手资料索引、源码锚点、版本差异摘要：
- 15.6: CompilationMode API 演进（SpeedProfile → Partial）
- 15.7: ATRACE_CALL() 与 Perfetto Slice 命名映射规则
- 15.8: arXiv 2407.05090 性能问题优先级分布数据
- 14.1: ProfilingManager API 35→36 演进：主动抓取→被动捕获
- 14.2: Simpleperf + Firefox Profiler 管线（gecko_profile_generator.py）
- 14.3: Perfetto Java Heap Dumps (Android 11+) vs Java Heap Sampling (Android 12+)
- 14.5: btrace 3.0 同步抓栈采样方案；AGP Instrumentation API
- 14.7: BufferFillPolicy FLUSH_FULL 内部枚举；Trigger 类型本质区别
- 14.8: Android 14 增强 profileable GPU 计数器访问权限
- 14.9: PreviewSpacer 帧平滑"预测-等待"模型
- 14.10: GKI 内核演进时间线：Android 14 (6.1) → 15 (6.6) → 16 (6.12)
- 14.11: Android 15+ BatteryManager.getSupportedPowerMonitors() 代码级功耗读取

## 去重备注
- 14.4 dumpsys: task6-review 已于 2026-04-21T18:36:56 写入 P0/P1/P2 全量条目，本轮跳过
- 14.9 Camera: task9-deep-tech-review 已有 SQL 错误 + Camera3OutputStream 条目，本轮合并 Cleaner + PreviewSpacer + CameraX 开销
- 14.11 Battery: task9-deep-tech-review 已有 BatteryStatsService 路径 + PowerMonitor 条目，本轮合并 Docker 失效 + Perfetto power_rails
- suggestions.md 中已有 task6/task9 条目的章节，本轮仅补充未覆盖的新建议

## 归档结果

### 已归档（2 个）
- 2026-04-21-06-15.6-external-review.md → queue,suggestions,research-gaps
- 2026-04-21-08-15.8-external-review.md → suggestions

### 未归档（12 个）— 基础设施限制
归档 helper 的 `infer_section` 函数使用正则 `\d+(?:\.\d+)?` 匹配文件名中的章节号。
ch14 文件名格式为 `14-01-as-profiler`、`14-02-simpleperf` 等，无法匹配该正则，
且文件内不含 `**章节号**：` 标记，导致 `infer_section` 返回 None。
**这些文件已全部完成整合写入**，但无法被 helper 自动检测为已消费。

未归档文件列表：
- 2026-04-21-07-15.7-external-review.md（无 P0/P1，无 queue/gaps 写入，正确保留）
- 2026-04-21-14-01-as-profiler-external-review.md ✅ 已整合
- 2026-04-21-14-02-simpleperf-external-review.md ✅ 已整合
- 2026-04-21-14-03-memory-tools-external-review.md ✅ 已整合
- 2026-04-21-14-04-dumpsys-external-review.md ✅ 已整合（task6 已覆盖）
- 2026-04-21-14-05-third-party-libs-external-review.md ✅ 已整合
- 2026-04-21-14-06-automation-tools-external-review.md ✅ 已整合
- 2026-04-21-14-07-profiling-manager-external-review.md ✅ 已整合
- 2026-04-21-14-08-gpu-debug-tools-external-review.md ✅ 已整合
- 2026-04-21-14-09-camera-performance-analysis-external-review.md ✅ 已整合
- 2026-04-21-14-10-ebpf-performance-analysis-external-review.md ✅ 已整合
- 2026-04-21-14-11-battery-historian-external-review.md ✅ 已整合

### 建议修复
1. 增强 `infer_section` 使其支持 `14-01-as-profiler` → `14.1` 的映射
2. 或在 external-review 文件中统一添加 `**章节号**：14.1` 标记
