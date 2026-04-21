# 一般建议清单

## [External Review Integration] 2026-04-21

本批次整合了 22 个外部 review 文件，共提取 41 条一般修正建议。主要涉及工具使用说明、案例补充、权限说明等方面。

### GPU 调试工具相关 (14.8)
- **类型**: 数据支撑
- **位置**: 工具使用说明段
- **问题**: 缺少真实案例分析
- **建议**: 补充 GPU 性能问题的实际调试案例
- **来源**: 外部 AI Review

### 内存工具相关 (03)
- **类型**: 原理修正
- **位置**: Perfetto Java 堆分析段
- **问题**: 严重低估了 Perfetto 的 Java 堆分析能力
- **建议**: 明确区分 Perfetto 的 Java Heap Dumps (Android 11+) 和 Java Heap Sampling (Android 12+) 两种能力
- **来源**: 外部 AI Review

- **类型**: 权限说明
- **位置**: 底层工具使用段
- **问题**: 缺少工具执行权限要求说明
- **建议**: 明确指出  和  强依赖  或 userdebug/eng 系统镜像
- **来源**: 外部 AI Review

### 性能管理器相关 (14.7)
- **类型**: 方法改进
- **位置**: 性能分析段
- **问题**: 缺少机器学习模型的调优建议
- **建议**: 补充 AML 模型训练和部署的最佳实践
- **来源**: 外部 AI Review

### 自动化测试工具相关 (14.6)
- **类型**: 工具增强
- **位置**: 自动化脚本段
- **问题**: 缺少自动化脚本示例
- **建议**: 提供性能测试自动化脚本模板
- **来源**: 外部 AI Review

### Battery Historian 相关 (14.11)
- **类型**: 数据支撑
- **位置**: 功耗分析方法段
- **问题**: 缺少实际功耗分析案例
- **建议**: 补充 Battery Historian 在实际项目中的应用案例
- **来源**: 外部 AI Review

### Simpleperf 相关 (14.2)
- **类型**: 功能补充
- **位置**: 性能分析工具段
- **问题**: 缺少特定场景的使用指南
- **建议**: 补充 Simpleperf 在特定性能场景下的使用技巧
- **来源**: 外部 AI Review

### 三方性能库相关 (14.5)
- **类型**: 版本兼容性
- **位置**: 性能库使用段
- **问题**: 缺少版本兼容性说明
- **建议**: 补充各版本 Android 下的三方库兼容性注意事项
- **来源**: 外部 AI Review

## 涉及章节总结
- 14.8: GPU 调试工具
- 03: 内存工具
- 14.7: 性能管理器
- 14.6: 自动化测试工具
- 14.11: Battery Historian 与功耗分析
- 14.2: Simpleperf
- 14.5: 三方性能库
- 14.4: Dumpsys
- 14.1: AS Profiler
- 14.01: 自动化脚本
- 其他章节...

## 建议
1. 优先处理涉及 P1 级别问题的章节（如内存工具章节的 Perfetto 能力修正）
2. 补充工具权限要求的详细说明，提升实战指导价值
3. 增加真实案例分析，提升内容的实用性

## [Task6 Review] 13.1 Perfetto 简介与演进 — 2026-04-21
- **类型**：需修正 + 需补充
- **位置**：参考资料 / Perfetto 的架构
- **问题**：(P0) AOSP源码路径 system/tracing/ 不存在，正确路径为 external/perfetto/src/traced/；(P1) 架构章节遗漏 heapprofd 和 traced_perf 两个核心组件
- **建议**：修正源码路径；在 traced_probes 之后补充 heapprofd/traced_perf 的角色说明
- **来源**：external-review/2026-04-21-22-13.1-external-review.md
- **review 日志**：logs/review/2026-04-21-18-review.md

## [Task6 Review] 14.4 dumpsys 系列命令 — 2026-04-21
- **类型**：需修正 + 需补充 + 需确认
- **位置**：meminfo USS段落 / window焦点段落 / activity进程优先级
- **问题**：(P0) LMKD不使用USS，使用RSS+oom_score_adj；(P1) 遗漏dumpsys input联动；(P2) VISIBLE_APP_ADJ值在Android 10前后不同
- **建议**：修正USS描述；补充dumpsys input建议；说明ADJ版本变化
- **来源**：external-review/2026-04-21-14-04-dumpsys-external-review.md
- **review 日志**：logs/review/2026-04-21-18-review.md

## [Task9 Deep Review] 14.7 ProfilingManager — 2026-04-21
- **类型**：交叉引用
- **位置**：结果分发 / trigger 版本对照表 / 相关章节
- **问题**：文中多次写“详见 §8.8 ProfilingManager 系统触发式性能追踪”，但当前 `8.8` 实际是“Android 多媒体管线性能”，引用目标不存在。
- **建议**：把交叉引用改成真实存在的章节编号或文件路径，再同步正文里的“§8.8”描述。

## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-21
- **类型**：数据缺失/案例泛化
- **位置**：SQL 查询：量化帧率和帧间隔
- **问题**：示例把 `thread.name like '%PreviewSpacer%'` 写成默认筛选条件，但没有说明它不是稳定的公开 AOSP 命名，也没有给通用 fallback。
- **建议**：补充“该筛选依赖具体 trace/实现”的边界，并给出按 `cameraserver` + `queueBuffer`/stream track 做通用筛选的替代写法。

## [Task9 Deep Review] 14.11 Battery Historian 与功耗分析工具 — 2026-04-21
- **类型**：交叉工具链
- **位置**：ODPM 的工作原理 / Power Profiler vs Energy Profiler
- **问题**：章节把 ODPM 基本限定在 Android Studio Profiler 视角，缺少 Perfetto `android.power_rails` trace 与 SQL 分析链路。
- **建议**：补一段 Perfetto 抓取 power rails、和 CPU 调度/线程事件联查的入口，避免工具链割裂。
