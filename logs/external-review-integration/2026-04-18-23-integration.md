# External Review 自动整合日志 — 2026-04-18 23:15

## 扫描范围
logs/external-review/ 根目录活跃文件

## 扫描结果
- 活跃文件数：23
- 已整合：23
- 跳过：0

## 整合摘要

### queue.json
新增 13 条外部 review 回炉问题单（P0=9, P1=4）

### research-gaps.md
新增 27 条知识盲区

### suggestions.md
新增 23 条一般建议

## 涉及章节
- 13.1 （3.5/5 ⚠️ 回炉）
- 13.2 （4.0/5 ⚠️ 回炉）
- 13.3 （3.5/5 ⚠️ 回炉）
- 13.4 （3.5/5 ⚠️ 回炉）
- 13.5 （5.0/5）
- 13.6 （4.5/5）
- 13.7 （3.5/5 ⚠️ 回炉）
- 13.8 （5.0/5）
- 13.9 （5.0/5）
- 13.10 （4.5/5）
- 14.1 （3.5/5 ⚠️ 回炉）
- 14.2 （4.0/5 ⚠️ 回炉）
- 14.3 （4.0/5 ⚠️ 回炉）
- 14.4 （4.5/5）
- 14.5 （3.5/5 ⚠️ 回炉）
- 14.6 （4.5/5）
- 14.7 （3.0/5 ⚠️ 回炉）
- 14.8 （4.5/5）
- 14.9 （4.5/5）
- 14.10 （3.5/5 ⚠️ 回炉）
- 14.11 （4.5/5）
- 15.1 （?/5）
- 15.2 （?/5）

## 知识资产保留
以下高价值知识资产已保留在 external-review 文件本体：
- 13.1 : 1
- **核心结论**：AOSP 中 Perfetto 的真身始终位于 `external/perfetto` 路径，而非传统认知里的 `system/core` 或 `system/tracing`（后者多为包装或遗留配置）。
- 13.2 : 2
- **核心结论**：`atrace_apps: "*"` 是进行整机未分类应用卡顿排查的黄金配置，它解除了只针对单个 App 的视角限制。
- 13.3 : 3
- **核心结论**：明确剥离了 Android 12-13（onMessageReceived/REFRESH）与 Android 14+（commit/composite/present）的 SurfaceFlinger 主循环 T
- 13.4 : 4
- **核心结论**：系统化归纳了 `slice → thread_track → thread → process` 这一最高频的 JOIN 查询模式，大幅降低了初学者学习 Perfetto SQL 的门槛。
- 13.5 : 5
- **核心结论 1**：明确给出了流畅度分析的“版本、数据源与判读入口对照表”，一锤定音地解决了旧版 Systrace 教程在 Perfetto 时代水土不服的问题（如 `actual_frame_timeline_slice` 查 
- 13.7 : 7-external-review.md`
- 13.8 : 8
- **核心结论**：提炼出了针对滑动卡顿、ANR 输入超时、冷启动响应这三大典型场景的即插即用 SQL 模板。具有极高的查阅和“拿来主义”价值。

## 七、落盘信息
- 已写入文件：`logs/external-review/202
- 14.1 : 章节：`01-as-profiler.md` | 一手资料：AOSP 官方文档 | 关键源码路径：`android.os.ProfilingManager` | 关键调用逻辑：`ProfilingManager.requestProfili
- 14.10 : 章节：`10-ebpf-performance-analysis.md` | 一手资料：AOSP + Cubox | 关键知识点：UprobeStats 完整架构（StatsD → 配置 → oatdump 偏移解析 → BPF attac
- 14.10 : 章节：`10-ebpf-performance-analysis.md` | 一手资料：kernel.org | 关键知识点：sched_ext 的 Bypass Mode 安全兜底机制 | 为什么保留：这个设计是 sched_ext 能用
- 14.11 : 章节：`11-battery-historian.md` | 一手资料：官方文档 | 关键知识点：ODPM Power Rail 完整表格（CPU Big/Mid/Little、GPU、Display、Cellular、WLAN、GPS、C
- 14.11 : 章节：`11-battery-historian.md` | 一手资料：实战经验 | 关键知识点：四种常见功耗问题模式（Wakelock 泄漏、频繁网络、GPS 持续活跃、后台 CPU 高）的标准分析流程 | 为什么保留：模式化的排查方法论
- 14.2 : 章节：`02-simpleperf.md` | 一手资料：Brendan Gregg 火焰图模型 | 关键调用逻辑：“平台(plateau)”与“尖塔(spire)”的火焰图读图法则 | 为什么保留：非常精炼地总结了怎么看火焰图，这属于实战
- 14.3 : 章节：`03-memory-tools.md` | 一手资料：AOSP | 关键源码逻辑：`dumpsys meminfo` 与 `procrank` 底层均依赖 `system/core/libmeminfo`。 | 为什么保留：这个知识
- 14.4 : 章节：`04-dumpsys.md` | 一手资料：AOSP 15 | 关键知识点：Android 15 SurfaceFlinger dumpsys 输出变化（Frontend 架构引入 `Composition list` 和 `Inp
- 14.5 : 章节：`05-third-party-libs.md` | 一手资料：Rhea 技术博客 | 关键逻辑：Trace 工具从 Systrace -> Method Trace -> 动态一体化 Trace 的三阶段演进 | 为什么保留：这个演
- 14.6 : 章节：`06-automation-tools.md` | 一手资料：官方文档 | 关键知识点：Macrobenchmark 测试必须在独立 `com.android.test` 模块中运行，与 Espresso 不兼容，底层依赖 UI A
- 14.6 : 章节：`06-automation-tools.md` | 一手资料：官方文档 + 实战 | 关键知识点：完整的 GitHub Actions + Firebase Test Lab CI/CD 集成示例 | 为什么保留：端到端的 CI 管
- 14.7 : 章节：`07-profiling-manager.md` | 一手资料：官方 API 参考 | 关键知识点：完整的 ProfilingTrigger 版本归属表（从官方 API 参考中整理，含 API 36 / 36.1 / 37 的区分）
- 14.8 : 章节：`08-gpu-debug-tools.md` | 一手资料：AGI 2025-2026 路线图 | 关键知识点：AGI System Profiler 将开源，Frame Profiler 将基于 GFXReconstruct 重建
- 14.8 : 章节：`08-gpu-debug-tools.md` | 一手资料：实战经验 | 关键知识点：GPU 利用率高≠GPU 是瓶颈、ALU 利用率 vs 带宽瓶颈的判断方法 | 为什么保留：这些判断范式是 GPU 性能分析的核心方法论，可复用到
- 14.9 : 章节：`09-camera-performance-analysis.md` | 一手资料：Cubox + AOSP | 关键知识点：Camera 启动时间自动化拆解脚本（Python SDK + SQL） | 为什么保留：这是可直接复用到
- 14.9 : 章节：`09-camera-performance-analysis.md` | 一手资料：字节跳动西瓜视频案例 | 关键知识点：CameraMetaDataNative 的 Finalizer → Native OOM 路径 | 为什么保
