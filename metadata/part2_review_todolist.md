# Part 2 Performance Review Todolist

> 历史 Review 完成清单；路径已按当前 canonical 目录核验，不作为活动 queue。

## 第 7 章：流畅性 (ch07-smoothness)
- [x] 7.1 卡顿的定义与分类 (`src/part2-performance/ch07-smoothness/01-jank-definition.md`)
- [x] 7.2 卡顿原因体系 (`src/part2-performance/ch07-smoothness/02-jank-causes.md`)
- [x] 7.3 卡顿 analysis 方法论 (`src/part2-performance/ch07-smoothness/03-jank-methodology.md`)
- [x] 7.4 典型场景分析 (`src/part2-performance/ch07-smoothness/04-typical-scenarios.md`)
- [x] 7.5 优化策略 (`src/part2-performance/ch07-smoothness/05-optimization.md`)
- [x] 7.6 案例集 (`src/part2-performance/ch07-smoothness/06-case-studies.md`)
- [x] 7.7 Jetpack Compose 性能优化 (`src/part2-performance/ch07-smoothness/07-compose-performance.md`)
- [x] 7.8 RecyclerView 列表滑动性能深度优化 (`src/part2-performance/ch07-smoothness/08-recyclerview-performance.md`)
- [x] 7.9 感知流畅性：步幅波动与无掉帧卡顿 (`src/part2-performance/ch07-smoothness/09-perceived-smoothness.md`)
- [x] 7.10 View 体系性能优化 (`src/part2-performance/ch07-smoothness/10-view-layout-performance.md`)
- [x] 7.11 SystemUI 性能分析 (`src/part2-performance/ch07-smoothness/11-systemui-performance.md`)
- [x] 7.12 HWC Overlay Plane 与合成降级排查 (`src/part2-performance/ch07-smoothness/12-hwc-overlay-composition-downgrade.md`)
- [x] 7.13 AccessibilityManagerService 与无障碍服务性能影响 (`src/part2-performance/ch07-smoothness/13-accessibility-manager-performance.md`)
- [x] 7.14 ContentCaptureService 与 Autofill 性能影响 (`src/part2-performance/ch07-smoothness/14-contentcapture-autofill-performance.md`)

> 原 7.14 GAPS 已移至 14.26；图片、WebView、场景手册与 Fragment 专题的审阅结果已合并到当前 canonical 正文，映射见 `metadata/content-consolidation-audit.md`。

## 第 8 章：响应速度 (ch08-responsiveness)
- [x] 8.1 响应速度原理 (`src/part2-performance/ch08-responsiveness/01-responsiveness-principles.md`)
- [x] 8.2 App 启动全流程 (`src/part2-performance/ch08-responsiveness/02-app-launch.md`)
- [x] 8.3 启动优化策略 (`src/part2-performance/ch08-responsiveness/03-launch-optimization.md`)
- [x] 8.4 其他响应速度场景 (`src/part2-performance/ch08-responsiveness/04-other-scenarios.md`)
- [x] 8.5 案例集 (`src/part2-performance/ch08-responsiveness/05-case-studies.md`)
- [x] 8.6 Kotlin Coroutine、Flow 与线程调度实践 (`src/part2-performance/ch08-responsiveness/06-coroutine-performance.md`)
- [x] 8.7 Baseline Profiles 与编译优化实践 (`src/part2-performance/ch08-responsiveness/07-baseline-profiles.md`)
- [x] 8.8 Binder Trace 驱动的 Activity 冷启动性能分析 (`src/part2-performance/ch08-responsiveness/08-binder-trace-cold-start-analysis.md`)
- [x] 8.9 Keystore/KeyMint 调用延迟与登录链路性能 (`src/part2-performance/ch08-responsiveness/09-keystore-keymint-latency.md`)
- [x] 8.10 BiometricPrompt 与 Credential Manager 登录链路性能 (`src/part2-performance/ch08-responsiveness/10-biometric-credential-login-performance.md`)
- [x] 8.11 推送通知管线性能 (`src/part2-performance/ch08-responsiveness/11-push-notification-pipeline-performance.md`)
- [x] 8.12 Play Integrity API 性能与集成延迟 (`src/part2-performance/ch08-responsiveness/12-play-integrity-api-performance.md`)

> 原多媒体、游戏、ProfilingManager、Native 加载、JNI 与 Broadcast 正文已合并到对应主文；Flow 与线程调度并入 8.6。完整映射见 `metadata/content-consolidation-audit.md`。

## 第 9 章：ANR (ch09-anr)
- [x] 9.1 ANR 设计思想 (`src/part2-performance/ch09-anr/01-anr-design.md`)
- [x] 9.2 ANR 类型与触发条件 (`src/part2-performance/ch09-anr/02-anr-types.md`)
- [x] 9.3 ANR 分析方法 (`src/part2-performance/ch09-anr/03-anr-analysis.md`)
- [x] 9.4 特殊与跨边界 ANR (`src/part2-performance/ch09-anr/04-special-anr.md`)
- [x] 9.5 案例集 (`src/part2-performance/ch09-anr/05-case-studies.md`)
- [x] 9.6 Notification 性能与 ANR (`src/part2-performance/ch09-anr/06-notification-performance-anr.md`)
- [x] 9.7 ANR 与 Kernel Trace 联合诊断 (`src/part2-performance/ch09-anr/07-anr-kernel-trace-joint-diagnosis.md`)
- [x] 9.8 ContentProvider 超时与 ANR 四路径 (`src/part2-performance/ch09-anr/08-contentprovider-timeout-anr.md`)
- [x] 9.9 Android 17 ANR 预警回调与类型枚举 (`src/part2-performance/ch09-anr/09-android17-anr-warning-callback.md`)
- [x] 9.10 Android 17 Input ANR 与 pre-ANR 实现 (`src/part2-performance/ch09-anr/10-android17-input-anr-prewarning.md`)

> 原“非技术故障诊断”的通用归因内容回收到 9.2—9.4，历史 InputTransport 平台缺陷并入 9.5；CPU 日志方法论并入 9.3；企业监控平台设计并入 26.4。完整映射见 `metadata/content-consolidation-audit.md`。

## 第 10 章：内存性能 (ch10-memory-perf)
- [x] 10.1 App 内存分析 (`src/part2-performance/ch10-memory-perf/01-app-memory-analysis.md`)
- [x] 10.2 内存泄漏 (`src/part2-performance/ch10-memory-perf/02-memory-leak.md`)
- [x] 10.3 内存持续增长 (`src/part2-performance/ch10-memory-perf/03-memory-growth.md`)
- [x] 10.4 低内存对系统性能的影响 (`src/part2-performance/ch10-memory-perf/04-low-memory-impact.md`)
- [x] 10.5 案例集 (`src/part2-performance/ch10-memory-perf/05-case-studies.md`)
- [x] 10.6 内存抖动与频繁 GC (`src/part2-performance/ch10-memory-perf/06-memory-churn.md`)
- [x] 10.7 GPU 与图形内存统计 (`src/part2-performance/ch10-memory-perf/07-gpu-graphics-memory-tracking.md`)

> 原 SQLite/Room 正文归入 24.2，ART GC 碎片与 compaction 正文归入 4.7；重复的全章优化导读由本章 README 与 10.1 统一承载。完整映射见 `metadata/content-consolidation-audit.md`。

## 第 11 章：功耗 (ch11-power)
- [x] 11.1 Android 功耗模型 (`src/part2-performance/ch11-power/01-power-model.md`)
- [x] 11.2 App 耗电优化 (`src/part2-performance/ch11-power/02-app-power-optimization.md`)
- [x] 11.3 系统级功耗优化 (`src/part2-performance/ch11-power/03-system-power-optimization.md`)
- [x] 11.4 案例集 (`src/part2-performance/ch11-power/04-case-studies.md`)
- [x] 11.5 WakeLock 机制与功耗分析 (`src/part2-performance/ch11-power/05-wakelock.md`)
- [x] 11.6 Bluetooth 扫描与连接功耗分析 (`src/part2-performance/ch11-power/06-bluetooth-scan-connection-power.md`)
- [x] 11.7 用户设置对能耗的影响：亮度、刷新率与深色模式 (`src/part2-performance/ch11-power/07-user-settings-energy-impact.md`)

> 原 11.8 的 TARE 历史边界并入 5.8；Android 17 控制器、配额、pending reason 与排障内容由 5.8 既有正文统一承载。11.2 的重复 WakeLock 教程收束为 11.5 的入口。完整映射见 `metadata/content-consolidation-audit.md`。

## 第 18 章：渲染链路全景 (ch18-rendering-pipelines)
- [x] 18.1 渲染链路分类与选择矩阵 (`src/part2-performance/ch18-rendering-pipelines/01-pipeline-overview.md`)
- [x] 18.2 Android View 标准链路 (BLAST) (`src/part2-performance/ch18-rendering-pipelines/02-android-view-standard.md`)
- [x] 18.3 Android View 软件渲染链路 (`src/part2-performance/ch18-rendering-pipelines/03-android-view-software.md`)
- [x] 18.4 Android View 混合渲染链路 (`src/part2-performance/ch18-rendering-pipelines/04-android-view-mixed.md`)
- [x] 18.5 Android View 多窗口链路 (`src/part2-performance/ch18-rendering-pipelines/05-android-view-multi-window.md`)
- [x] 18.6 SurfaceView 直出链路 (`src/part2-performance/ch18-rendering-pipelines/06-surfaceview.md`)
- [x] 18.7 TextureView 合成链路 (`src/part2-performance/ch18-rendering-pipelines/07-textureview.md`)
- [x] 18.8 OpenGL ES 渲染链路 (`src/part2-performance/ch18-rendering-pipelines/08-opengl-es.md`)
- [x] 18.9 Vulkan 原生渲染链路 (`src/part2-performance/ch18-rendering-pipelines/09-vulkan-native.md`)
- [x] 18.10 SurfaceControl API 深入 (`src/part2-performance/ch18-rendering-pipelines/10-surface-control-api.md`)
- [x] 18.11 ANGLE (`src/part2-performance/ch18-rendering-pipelines/11-angle-gles-vulkan.md`)
- [x] 18.12 Flutter 渲染链路 (`src/part2-performance/ch18-rendering-pipelines/12-flutter-rendering.md`)
- [x] 18.13 WebView 渲染链路 (`src/part2-performance/ch18-rendering-pipelines/13-webview-rendering.md`)
- [x] 18.14 Camera 渲染管线 (`src/part2-performance/ch18-rendering-pipelines/14-camera-pipeline.md`)
- [x] 18.15 视频叠加与 HWC (`src/part2-performance/ch18-rendering-pipelines/15-video-overlay-hwc.md`)
- [x] 18.16 游戏引擎渲染链路 (`src/part2-performance/ch18-rendering-pipelines/16-game-engine.md`)
- [x] 18.17 Hardware Buffer Renderer (`src/part2-performance/ch18-rendering-pipelines/17-hardware-buffer-renderer.md`)
- [x] 18.18 PIP 与自由窗口渲染 (`src/part2-performance/ch18-rendering-pipelines/18-pip-freeform.md`)
- [x] 18.19 可变刷新率渲染管线 (`src/part2-performance/ch18-rendering-pipelines/19-variable-refresh-rate.md`)
- [x] 18.20 链路分析方法论 (`src/part2-performance/ch18-rendering-pipelines/20-pipeline-analysis-methodology.md`)
- [x] 18.21 EyeDropper API 与跨设备协作性能 (`src/part2-performance/ch18-rendering-pipelines/21-eyedropper-crossdevice.md`)

## 第 12 章：网络性能 (ch12-apk-network)
- [x] 12.1 网络性能优化 (`src/part2-performance/ch12-apk-network/01-network-performance.md`)
- [x] 12.2 Android 网络安全与 TLS 性能优化 (`src/part2-performance/ch12-apk-network/02-network-security-tls-performance.md`)
- [x] 12.3 netd 与 DnsResolver：DNS 解析性能和故障诊断 (`src/part2-performance/ch12-apk-network/03-netd-dnsresolver-network-diagnostics.md`)

> 原 APK 体积总览归入 25.6，客户端网络深浅两版合并为 12.1；ConnectivityService/NetworkAgent 归入 1.62，Privacy Sandbox 退场归入 21.10。完整映射见 `metadata/content-consolidation-audit.md`。

## 第 13 章：Perfetto (ch13-perfetto)
- [x] 13.1 Perfetto 简介与演进 (`src/part3-tools/ch13-perfetto/01-perfetto-intro.md`)
- [x] 13.2 Trace 抓取 (`src/part3-tools/ch13-perfetto/02-trace-capture.md`)
- [x] 13.3 Perfetto View 解读 (`src/part3-tools/ch13-perfetto/03-perfetto-view.md`)
- [x] 13.4 命令行打开超大 Trace (`src/part3-tools/ch13-perfetto/04-large-traces.md`)
- [x] 13.5 线程 CPU 状态分析 (`src/part3-tools/ch13-perfetto/05-thread-cpu-states.md`)
- [x] 13.6 Perfetto 指标、自动化与高级用法 (`src/part3-tools/ch13-perfetto/06-advanced-usage.md`)
- [x] 13.7 Perfetto 输入延迟 SQL 深度分析 (`src/part3-tools/ch13-perfetto/07-input-latency-sql.md`)
- [x] 13.8 Android Tracing 基础设施 (`src/part3-tools/ch13-perfetto/08-tracing-infrastructure.md`)
- [x] 13.9 Perfetto SQL 性能分析实战手册 (`src/part3-tools/ch13-perfetto/09-perfetto-sql-cookbook.md`)
- [x] 13.10 SPAN_JOIN 与窗口函数 (`src/part3-tools/ch13-perfetto/10-perfetto-span-join-window-functions.md`)
- [x] 13.11 Profile 导入与 Flamegraph 分析 (`src/part3-tools/ch13-perfetto/11-perfetto-profiles-flamegraph.md`)
- [x] 13.12 CPU 频率与 DVFS 关联分析 (`src/part3-tools/ch13-perfetto/12-cpu-frequency-dvfs-analysis.md`)
- [x] 13.13 DataGrid、Data Explorer 与 Jank CUJ (`src/part3-tools/ch13-perfetto/13-perfetto-data-explorer-jank-cuj.md`)
- [x] 13.14 BufferQueue 阻塞的 Perfetto 识别 (`src/part3-tools/ch13-perfetto/14-bufferqueue-blocking-perfetto.md`)
- [x] 13.15 Agent 辅助 Perfetto 分析协议 (`src/part3-tools/ch13-perfetto/15-agent-perfetto-analysis-protocol.md`)
- [x] 13.16 Perfetto SDK 与应用内 Trace 数据源 (`src/part3-tools/ch13-perfetto/16-perfetto-sdk-in-app-tracing.md`)
- [x] 13.17 SmartPerfetto 与可复用 Trace 分析平台 (`src/part3-tools/ch13-perfetto/17-smartperfetto-trace-analysis-platform.md`)
- [x] 13.18 FrameTracer 与 Graphics Frame Event (`src/part3-tools/ch13-perfetto/18-frametracer-graphics-frame-event.md`)
- [x] 13.19 FrameTimeline：Expected 与 Actual (`src/part3-tools/ch13-perfetto/19-frame-timeline-api33-perfetto-analysis.md`)
- [x] 13.20 android.os.Trace 与应用级自定义追踪 (`src/part3-tools/ch13-perfetto/20-android-trace-api-custom-tracing.md`)
- [x] 13.21 Perfetto v57 状态轨道与版本边界 (`src/part3-tools/ch13-perfetto/21-perfetto-v57-state-tracks.md`)
- [x] 13.22 Trace 采集可靠性与可复现诊断 (`src/part3-tools/ch13-perfetto/22-trace-reliability.md`)

> 原专题解读中的 I/O/功耗查询并入 13.9；重复的版本综述、数据源综述和 pprof/Simpleperf 专题由 13.1、13.11、13.18、13.19 统一承载；闭源 PerfDog 实现推测不再作为规范正文。完整映射见 `metadata/content-consolidation-audit.md`。

# All Tasks Completed
The comprehensive technical audit for Part 2 (Performance) has been finalized. 69 detailed review reports have been generated and archived in `logs/external-review/`. All Android 15/16/17 performance characteristics have been synchronized.
