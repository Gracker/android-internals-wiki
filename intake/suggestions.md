## [Task9 Deep Review] 1.5 线程模型 — 2026-07-07
- **类型**：版本差异
- **位置**：源码版本锚点声明
- **问题**：章节声明适用 Android 5.0 - Android 17，但主要源码引用基于 android-16.0.0_r1，与 Android 17 (android-17.0.0_r1) 存在版本差异。源码版本锚点与覆盖范围不匹配。
- **建议**：明确区分 android-16.0.0_r1 与 Android 17 的版本边界，在源码引用处标注具体版本，并补充说明 Android 17 中 MessageQueue 默认启用边界（USE_NEW_MESSAGEQUEUE）和 RenderThread 调度策略的重要变化。

## [Task2B Verifier] §18.18 PIP 与自由窗口渲染 — 2026-07-07
- **类型**：blocked-need-rework-evidence
- **位置**：src/part2-performance/ch18-rendering-pipelines/18-pip-freeform.md
- **问题**：task9_result=needs-rework，但 queue.json 无 pending 条目。Task2B Lite 已修复（TaskOrganizer 版本标注），Task6 已复审通过。needs-rework 可能来自 verifier 重复键解析（pass-tech-review → needs-rework），需 Task9 明确复审
- **建议**：Task9 下一轮应复审 §18.18，出具 pass-tech-review 或写入新 queue 条目

## [Task2B Verifier] §14.11 Battery Historian — 2026-07-07
- **类型**：blocked-need-rework-evidence
- **位置**：src/part3-tools/ch14-other-tools/11-battery-historian.md
- **问题**：task9_result=needs-rework，queue.json 中 14.11 全部 completed。Task2B 已修复全部 P0/P1，Task6 多轮复审通过。needs-rework 可能是 frontmatter 重建后的残留状态
- **建议**：Task9 下一轮应复审 §14.11，出具 pass-tech-review 或写入新 queue 条目


## [Task2A 知识缺口挖掘] 已检查方向记录 — 2026-07-07 08:00

**本轮结论**：全书 625 个小节，0 个空 draft，Task2B backlog = 0。经过系统性缺口挖掘（8 个方向），本轮未发现评分 ≥ 14 的知识缺口。

**已检查方向（避免重复挖掘）**：

1. **素材索引高质量未映射** — source-index.json 为空（0 条），无素材驱动的缺口
2. **研究素材（research-feeds）** — 最近 10 个研究素材均已有对应章节（ART HeapTask、CPU cache locality、Perfetto v54/v57、background audio hardening、Compose Pausable、frame timeline 等）
3. **每日信息（daily-info）** — 近 3 天热点（Compose Pager、Clean Architecture UseCase、Repository suspend fun）均已有对应章节或属于非性能话题
4. **AOSP 源码结构** — 对照 frameworks/base、packages/modules、system/ 下的核心组件：
   - ✅ Binder IPC（ch01 多节）、PackageManager/Staged Install（ch01）、WindowManager（ch02）、ActivityManager（ch01）
   - ✅ Memory/lmkd（ch04 多节）、Power/thermal（ch05 多节）、Storage/vold（ch06）
   - ✅ AudioFlinger（ch12）、Camera HAL3（ch18）、InputDispatcher（ch03）
   - ✅ SurfaceFlinger（ch02 多节）、Perfetto/simpleperf（ch13/14）
5. **官方文档** — Android 17 行为变更和新 API（ML Scheduler、DeliQueue、MTE、16KB Page、Predictive Back、Pausable Composition、Privacy Sandbox、ECH、Network Quota 等）全部已有对应章节
6. **research-gaps.md 已有条目** — 检查所有 ≥14 分的历史缺口：
   - GPU cross-vendor counter → 已有 14.28
   - Battery Historian/PowerMonitor OEM 差异 → 14.11 已有 ODPM/PowerStats HAL 深度覆盖
   - Android 17 signal handler → 已有 20.19
   - LMK kernel→userspace → ch04 多节覆盖
   - Binder thread pool → ch01 多节覆盖
   - VNDK isolation perf → 评分 10，低于阈值
7. **Clippings 三本参考书对照** —
   - 《Android 应用稳定性剖析与优化》15 篇：全部已有对应章节（Java Crash/Native Crash/OOM/Binder/FD/Thread/ASM/Native Hook/Backtrace）
   - 《Android 性能优化》16 篇：CPU 优化、Native 内存、体积优化、GC 抑制、虚拟内存、缓存优化 → 缓存优化已有 ch05/18 深度覆盖（评分 11）
   - 《线上疑难问题》59 篇：Xlog/Logan、动态部署、性能监控平台 → ch26 可观测性系列已覆盖
8. **已有章节深挖** — ch22-rendering-practice（30 节）、ch20-stability（20 节）、ch26-observability（26 节）等核心 Part 5 章节已极度密集，无扩展点值得独立成节

**结论**：全书在 Android 性能领域已达到极高覆盖密度。后续缺口挖掘可重点关注：
- 新发布的 Android 17 后续季度更新特性
- 新兴交叉领域（如 AI Agent 性能沙箱的深入实战）
- 与游戏引擎/Flutter/跨平台框架的最新版本适配


## [Task9 Deep Review] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-07-07
- **类型**：源码准确性
- **位置**：关于 Binder FDA 的描述
- **问题**：文中提到"Android 16 通过 FDA 降低 SurfaceFlinger 多图层 CPU 开销 20%-40%"的说法缺少源码锚点和 benchmark 条件，未在 GraphicBuffer.cpp 中确认直接接入 Binder FDA 批量安装路径
- **建议**：如需讨论 FDA，应从 Binder / Parcel 层源码和可复现 benchmark 入手，并与 GraphicBuffer transport fd 数组的语义分开

## [Task9 Deep Review] 1.5 线程模型 — 2026-07-07
- **类型**：知识盲区
- **位置**：16KB page size 对 buffer allocation 的影响
- **问题**：章节提到 16KB page size 对像素 payload、stride 和映射进程数的影响，但 metadata region 和 reservedSize 在 16KB page size 下的页粒度取整成本放大效应可以补充更具体的分析
- **建议**：补充 metadata region、reservedSize 在 16KB 设备上的分配预算影响案例，包括小尺寸 buffer、图标 atlas 的实际内存成本计算示例


## [Task2A 知识缺口挖掘] 已检查方向记录 — 2026-07-07 12:00

**本轮结论**：全书 607 个小节，0 个空 draft，Task2B backlog = 0。本轮在 08:00 挖掘基础上进行了 80+ 个细分主题的补充扫描，仍未发现评分 ≥ 14 的知识缺口。

**新增检查方向（本轮补充）**：

9. **Clippings 参考书交叉比对** — 逐篇检查三本参考书（15+16+59=90 篇）的知识点，全部已有对应章节覆盖：
   - 稳定性（Java Crash / Native Crash / OOM / Binder / FD / Thread / ASM / Native Hook / Backtrace）→ ch20
   - 性能优化（CPU 线程池 / Native 内存 / 体积优化 / GC 抑制 / 虚拟内存 / 缓存优化 / 任务调度）→ ch05/ch23/ch25/ch27
   - 线上疑难排查（APM 平台 / 内存监控 / 启动监控 / 网络监控 / 包体积监控 / 编译插桩 / 动态调试）→ ch19/ch26

10. **Android 17 新 API 普查** — 对照官方 behavior changes 和新 API：
    - ✅ Gemini Nano / AICore → 已有 9 篇覆盖（16-gpu-npu, 20-genai-app, 14-ml-runtime）
    - ✅ Desktop windowing → 已有 10 篇覆盖
    - ✅ Predictive Back → 已有 14 篇覆盖
    - ✅ 16KB page size → 已有 80 篇覆盖
    - ✅ Photo Picker → 已有 7 篇覆盖
    - ✅ Edge-to-edge → 已有 7 篇覆盖
    - ✅ Credential Manager / passkey → 已有 5 篇覆盖

11. **AOSP 子系统普查** — 检查 frameworks/base 核心服务：
    - ✅ Accessibility → 19-accessibility-manager-performance
    - ✅ WindowManager → ch08-window-manager 多节
    - ✅ NotificationManager → 14-push-notification-pipeline-performance
    - ✅ TaskSnapshot → 29-tasksnapshot-recents-rendering
    - ✅ SurfaceFlinger → 208 篇提及，深度覆盖

12. **底层存储与内存机制** — 
    - ✅ f2fs → 17 篇覆盖
    - ✅ ZRAM/swap → 30 篇覆盖
    - ✅ SparseArray/ArrayMap → 28 篇覆盖
    - ✅ StrictMode → 32 篇覆盖（含 23-strictmode-performance-diagnostics）

13. **构建与工具链性能** —
    - ✅ Gradle build → 41 篇覆盖
    - ✅ R8/ProGuard → ch25 多节
    - ✅ K2 compiler → 10 篇覆盖
    - ✅ Macrobenchmark → 140 篇覆盖
    - ✅ Baseline Profiles → 58 篇覆盖

14. **未覆盖但评分不足的候选**（< 14 分）：
    - Bubble API 性能（8/20）— 小众通知特性，性能影响有限
    - KSP2/K2 构建性能（9/20）— 构建期而非运行时性能
    - App Cloning 性能（7/20）— 小众多用户特性
    - Health Connect 性能（5/20）— 健康数据 API，非性能核心
    - React Native 性能（9/20）— 跨平台框架，仅 2 篇 Flutter 存在但 AIW 聚焦原生
    - VNDK 隔离性能影响（10/20）— 08:00 已评估

**两轮挖掘汇总（08:00 + 12:00）**：共检查 14 个方向、80+ 个细分主题，全书 607 个小节已达到极高覆盖密度。下一阶段建议聚焦：
- 跟踪 Android 17 QPR1/QPR2 可能引入的新性能相关 API
- 关注 Jetpack Compose 1.9+ 运行时的重大变更
- 监控 Game SDK / AGDK 的版本更新
- 新兴 AI Agent 应用的性能 profiling 实战案例积累
