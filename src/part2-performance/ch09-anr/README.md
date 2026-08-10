# 第 9 章：ANR

ANR 表示系统判定应用未在规定时间内响应。

一份 `traces.txt` 只能记录采样时刻的线程状态。ANR 分析还要结合超时类型、触发时间、Binder、锁、系统负载和用户可感知时间线。

分析应回到超时发生前的时间线，区分最终堆栈、触发原因和放大因素。

## 内容索引

- [9.1 ANR 设计思想](01-anr-design.md)
- [9.2 ANR 类型与触发条件](02-anr-types.md)
- [9.3 ANR 分析方法](03-anr-analysis.md)
- [9.4 特殊场景的 ANR](04-special-anr.md)
- [9.5 案例集](05-case-studies.md)
- [9.6 Notification 性能与 ANR](06-notification-performance-anr.md)
- [9.7 ANR 非技术故障诊断](07-non-technical-anr-diagnosis.md)
- [9.8 ANR Kernel Trace 联合诊断与系统事件关联](08-anr-kernel-trace-joint-diagnosis.md)
- [9.9 ContentProvider ANR 双路径](09-contentprovider-anr-double-path.md)
- [9.10 Android 17 ANR 预警回调与类型枚举](10-android17-anr-warning-callback.md)
- [9.11 企业级 ANR 监控平台架构设计](9.11-enterprise-anr-monitoring-platform-design.md)
- [9.12 Android 17 ANR 输入事件超时检测双层预警机制](9-12-android17-anr-输入事件超时检测双层预警机制.md)
- [9.13 ANR 日志 CPU 数据系统化分析方法论](13-anr-log-cpu-analysis-methodology.md)

## 阅读建议

- 系统学习 ANR：按 `9.1 → 9.2 → 9.3` 阅读。
- 事后堆栈无法解释触发点：重点查看 `9.1`、`9.3`、`9.8`。
- Notification、前台服务和多进程边界：进入对应专项条目。
