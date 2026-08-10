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
- [8.6 Kotlin Coroutine 性能实践](06-coroutine-performance.md)
- [8.7 Baseline Profiles 与编译优化实践](07-baseline-profiles.md)
- [8.8 Android 多媒体管线性能](08-media-pipeline.md)
- [8.9 Android 游戏性能与 Game Mode/State API](09-game-performance.md)
- [8.10 ProfilingManager 系统触发式性能追踪](08-system-triggered-profiling.md)
- [8.11 Native 库加载与动态链接性能](11-native-library-loading-dynamic-linker.md)
- [8.12 Keystore/KeyMint 调用延迟与登录链路性能](12-keystore-keymint-latency.md)
- [8.13 BiometricPrompt 与 Credential Manager 登录链路性能](13-biometric-credential-login-performance.md)
- [8.14 推送通知管线性能](14-push-notification-pipeline-performance.md)
- [8.15 Play Integrity API 性能与集成延迟](15-play-integrity-api-performance.md)
- [8.17 Kotlin Flow 背压、操作符链与响应式性能边界](17-kotlin-flow-backpressure-performance.md)
- [8.18 Binder Trace 驱动的 Activity 冷启动性能分析](18-binder-trace-cold-start-analysis.md)
- [8.19 Android 线程模型与调度器选型实战](19-thread-model-dispatcher-selection.md)
- [8.20 JNI 调用开销与 Native 互操作性能边界](20-jni-overhead-native-interop-performance.md)
- [8.21 Broadcast 性能与跨进程通信开销治理](21-broadcast-performance-cross-process-overhead.md)

## 阅读建议

- 启动体验：优先阅读 `8.1`、`8.2`、`8.3`。
- “点了没反应”“切页慢”“首屏空白久”：从 `8.1` 和 `8.4` 开始。
- 多媒体、游戏、登录、推送等专项场景：进入对应扩展条目。
