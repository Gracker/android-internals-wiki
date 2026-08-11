# 第 8 章：响应速度

响应速度衡量操作到可见或可交互反馈的延迟，流畅性衡量连续画面的稳定程度。

两类问题的主观感受可能相似，分析指标和责任路径却不同。帧率正常时，点击反馈仍可能很慢；首帧及时显示后，内容也可能尚不可交互；后台恢复、数据准备或输入到显示路径同样会表现为响应延迟。

分析时需要把“感觉慢”拆成可量化、可观测、可归因的时间区间。

## 内容索引

- [8.1 响应速度原理](01-responsiveness-principles.md)
- [8.2 App 启动全流程](02-app-launch.md)
- [8.3 启动优化策略](03-launch-optimization.md)
- [8.4 其他响应速度场景](04-other-scenarios.md)
- [8.5 案例集](05-case-studies.md)
- [8.6 Kotlin Coroutine、Flow 与线程调度实践](06-coroutine-performance.md)
- [8.7 Baseline Profiles 与编译优化实践](07-baseline-profiles.md)
- [8.8 Binder Trace 驱动的 Activity 冷启动性能分析](08-binder-trace-cold-start-analysis.md)
- [8.9 Keystore/KeyMint 调用延迟与登录链路性能](09-keystore-keymint-latency.md)
- [8.10 BiometricPrompt 与 Credential Manager 登录链路性能](10-biometric-credential-login-performance.md)
- [8.11 推送通知管线性能](11-push-notification-pipeline-performance.md)
- [8.12 Play Integrity API 性能与集成延迟](12-play-integrity-api-performance.md)

## 阅读建议

- 启动体验：优先阅读 `8.1`、`8.2`、`8.3`；需要逐笔 IPC 归因时再读 `8.8`。
- “点了没反应”“切页慢”“首屏空白久”：从 `8.1` 和 `8.4` 开始。
- 并发、Flow 与线程调度统一从 `8.6` 进入；登录与可信校验阅读 `8.9`、`8.10`、`8.12`。
- 多媒体和游戏的端到端主文已回归 `18.21` 与 `18.16`；ProfilingManager、JNI、动态链接和 Broadcast 分别由 `14.11`、`1.15`、`1.58`、`1.33` 承载。
