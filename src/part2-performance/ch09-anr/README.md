# 第 9 章：ANR

ANR（Application Not Responding，应用无响应）表示系统判定应用没有在规定时间内完成某类关键响应，例如处理输入事件、广播或服务回调。

一份 `traces.txt` 只记录抓取堆栈那一刻的线程状态，无法单独还原此前发生了什么。ANR 分析还要结合超时类型、触发时刻、Binder 等待、锁竞争、系统负载和用户可感知的操作时间线。

分析应回到超时发生前的时间线：最终堆栈说明采样时线程停在哪里，触发原因解释哪项响应未按时完成，放大因素则包括高负载、调度延迟等让问题更容易出现的条件。三者要分别取证。

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
- 事后堆栈无法解释超时从何处开始：重点查看 `9.1`、`9.3`、`9.7`。
- Notification、前台服务和多进程边界：进入对应专项条目。
- 线上监控、事件写入本地文件与聚合分析：查看 `26.4`。
