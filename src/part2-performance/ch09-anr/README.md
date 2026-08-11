# 第 9 章：ANR

ANR 表示系统判定应用未在规定时间内响应。

一份 `traces.txt` 只能记录采样时刻的线程状态。ANR 分析还要结合超时类型、触发时间、Binder、锁、系统负载和用户可感知时间线。

分析应回到超时发生前的时间线，区分最终堆栈、触发原因和放大因素。

## 内容索引

- [9.1 ANR 设计思想](01-anr-design.md)
- [9.2 ANR 类型与触发条件](02-anr-types.md)
- [9.3 ANR 分析方法](03-anr-analysis.md)
- [9.4 特殊与跨边界 ANR](04-special-anr.md)
- [9.5 案例集](05-case-studies.md)
- [9.6 Notification 性能与 ANR](06-notification-performance-anr.md)
- [9.7 ANR 与 Kernel Trace 联合诊断](07-anr-kernel-trace-joint-diagnosis.md)
- [9.8 ContentProvider 超时与 ANR 四路径](08-contentprovider-timeout-anr.md)
- [9.9 Android 17 ANR 预警回调与类型枚举](09-android17-anr-warning-callback.md)
- [9.10 Android 17 Input ANR 与 pre-ANR 实现](10-android17-input-anr-prewarning.md)

## 阅读建议

- 系统学习 ANR：按 `9.1 → 9.2 → 9.3` 阅读。
- 事后堆栈无法解释触发点：重点查看 `9.1`、`9.3`、`9.7`。
- Notification、前台服务和多进程边界：进入对应专项条目。
- 线上监控、事件落盘与聚合治理：查看 `26.4`。
