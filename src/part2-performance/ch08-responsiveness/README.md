# 第 8 章：响应速度

响应速度关注从用户操作到界面给出可见反馈或恢复可交互状态所需的时间；流畅性关注连续画面的帧间隔是否稳定。

两类问题给人的感受可能相似，但分析指标和责任路径不同。帧率正常时，点击反馈仍可能延迟；首帧按时显示后，内容也可能暂时无法交互。应用从后台恢复、准备数据，或把输入事件传递到画面的过程，都可能产生响应延迟。

分析时，应把“感觉慢”转换成有明确起点和终点的时间区间，再分别测量和归因。

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

- 启动体验：优先阅读 `8.1`、`8.2`、`8.3`；需要逐次检查 IPC（跨进程调用）时再读 `8.8`。
- “点了没反应”“切页慢”“首屏空白久”：从 `8.1` 和 `8.4` 开始。
- 并发、Flow 和线程调度从 `8.6` 开始；登录与可信校验相关内容见 `8.9`、`8.10`、`8.12`。
- 多媒体和游戏的端到端分析分别见 `18.21` 与 `18.16`；ProfilingManager、JNI、动态链接和 Broadcast 分别见 `14.11`、`1.15`、`1.58`、`1.33`。
