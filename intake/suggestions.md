## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：源码准确性
- **位置**：Section 4.3 "Android 17（API 37）Perfetto 启用方式的变化"
- **问题**：`debug.perfetto.enabled` 与 DeviceConfig 的关系描述不准确，可能导致开发者误解
- **建议**：修正为 `debug.perfetto.enabled` 与 DeviceConfig 提供细粒度运行时控制能力，与 `persist.traced.enable=1` 共同构成完整启用机制

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：知识盲区
- **位置**：Section 4.4 "自适应刷新率场景的帧数据分析"
- **问题**：FrameTimeline 的 Expected vs Actual 分析缺少具体的 SQL 查询示例
- **建议**：补充类似章节 4.3 的 trace_processor SQL 查询代码，提供完整的查询示例

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：知识盲区
- **位置**：Section 4.4 和整体章节
- **问题**：heapprofd 在生产环境的默认部署状态（user 构建默认不拉起）未说明
- **建议**：补充说明 heapprofd 在不同构建类型（user vs userdebug）下的默认行为和启用条件

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：交叉引用一致性
- **位置**：Section 4.4 "自适应刷新率场景的帧数据分析"
- **问题**：提及 "详见 2.30 章" 但缺少具体关联点
- **建议**：补充 2.30 章与本章节的具体关联描述，明确读者可以在 2.30 章找到哪些补充信息

## [Task9 Deep Review] 13.21-perfetto-version-evolution — Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-04
- **类型**：知识盲区
- **位置**：FrameTimeline 多显示器场景描述
- **问题**：`DisplayFrameTracker` 与 `FrameTracer` 的协同工作机制可以更深入
- **建议**：补充具体的源码实现细节，说明两个类如何协同工作实现多显示器追踪

## [Task9 Deep Review] 13.21-perfetto-version-evolution — Perfetto 版本演进与 Android 9-17 新特性验证 — 2026-07-04
- **类型**：交叉引用一致性
- **位置**：整体章节
- **问题**：提及 "详见 2.30 章" 但缺少具体关联点
- **建议**：补充 2.30 章与本章节的具体关联描述，明确 FrameTimeline GPU/CPU 合成边界的分析位置

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：源码准确性
- **位置**：Section 4.3.4 "Android 17（API 37）Perfetto 启用方式的变化"
- **问题**：`debug.perfetto.enabled` 系统属性描述与实际AOSP android-17.0.0_r1代码不符，该属性实际不存在
- **建议**：修正或删除不存在的属性引用，改为通过DeviceConfig机制控制的正确描述

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：版本差异
- **位置**：Section 4.3.4 "Android 17（API 37）Perfetto 启用方式的变化"
- **问题**：未提及Android 17中VSync offset动态调整机制的具体变化
- **建议**：补充VSync offset调整算法的具体实现或参考源码位置

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：知识盲区
- **位置**：Section 4.3 "Perfetto trace_processor 实战"
- **问题**：SQL查询示例缺少实际trace数据验证，未说明在实际trace中能否找到对应数据
- **建议**：补充Perfetto trace中对应表结构的验证信息
## [2026-07-04] 知识缺口挖掘 — 第4轮无候选 (连续第4轮)

**本轮检查方向**（全部 < 14分）：
1. CursorWindow/ContentResolver 批量操作性能 (7/20) — Room/SQLite已覆盖
2. SystemServer Watchdog 超时检测 (9/20) — 系统级, 应用开发者关注度低
3. Android Motion Prediction 输入预测 (10/20) — OEM特性, ch03已有input-latency-prediction
4. Gradle/构建系统性能 (10/20) — 非运行时性能, 不属于本书范围
5. WebSocket/HTTP长连接性能 (11/20) — 社区文章丰富但ch24已广泛覆盖网络性能
6. KMP Android性能边界 (10/20) — KMP生态发展中, AOSP不覆盖
7. 插件化包体积优化 (9/20) — DFM已取代, 过时趋势
8. DownloadManager性能 (4/20) — 过时API
9. Intent Resolution选择器性能 (7/20) — OEM/系统侧关注
10. Privacy Sandbox性能 (9/20) — 已有07-privacy-sandbox-performance.md

**新增检查维度**（相比前3轮）：
- Clippings 缓存优化章节 → 已有 18-cpu-cache-friendly-code-data-layout.md
- 25+ 关键词全文搜索（gradle/macrobenchmark/16kb-page/breakpad/ptrace等）
- Clippings MUSCHED调度论文 → OEM专属, 无AOSP源码锚点
- ContentResolver/CursorWindow 数据访问层 → Room/SQLite深度已覆盖

**结论**：全书589个文件，覆盖范围已饱和。建议后续挖掘周期转向「深度扩展」（已有章节的🔸扩展点）而非「广度新增」。


## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：源码准确性
- **位置**：Section 3.2 "版本兼容性"
- **问题**：文中提到 src/perfetto_cmd/perfetto_cmd.cc，但正确路径应为 external/perfetto/src/perfetto_cmd/perfetto_cmd.cc
- **建议**：统一所有 Perfetto 相关源码路径为 external/perfetto/src/ 前缀，确保与 AOSP android-17.0.0_r1 一致

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据缺失
- **位置**：Section 10 "案例复盘"
- **问题**："启动快了但首页帧率掉了 5%" 的优化失败案例未提供具体数据支撑
- **建议**：补充该案例的具体数据（如优化前后指标对比、影响范围验证方法）或明确标注为假设性示例

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：知识盲区
- **位置**：整体章节未涉及 Android 14+ 隐私限制
- **问题**：未讨论 Android 14+ 的隐私限制（如严格的后台执行限制、精确位置权限变化）对性能分析的影响
- **建议**：补充隐私限制条件下的性能分析替代方案和数据采集技巧

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：知识盲区
- **位置**：整体章节
- **问题**：未讨论跨厂商设备（Samsung、小米、OPPO 等）的 Perfetto 行为差异
- **建议**：补充主要厂商定制 ROM 中 Perfetto 实现的差异性说明及调试技巧

## [2026-07-04] 知识缺口挖掘 — 第5轮无候选 (连续第5轮)

**本轮检查方向**（全部 < 14分）：
1. Jetpack Glance / App Widget 性能 (11/20) — 已有 24-app-widget-performance.md
2. Predictive Back 手势性能 (12/20) — 已有 13-predictive-back-performance.md
3. Desktop Mode / 大屏适配性能 (11/20) — 已有 14-desktop-windowing + 27-adaptive-layout
4. 16KB Page Size 兼容性性能 (12/20) — 已在 ch16-aosp/05 + ch20-stability/13 中覆盖
5. WorkManager 性能优化 (8/20) — 系统调度层面，ch16已有覆盖
6. Room Database 性能 (9/20) — 已有 02-database-optimization + 17-room3-kmp
7. Android Virtualization Framework (pKVM) (10/20) — 已有 32-virtualization-framework
8. Media3 / ExoPlayer 性能 (9/20) — 已有 media-pipeline + audio-offload 覆盖
9. Compose Navigation 性能 (8/20) — 已有 22.23-navigation-compose-performance
10. Compose Macrobenchmark / Baseline Profiles (9/20) — 已在 ch21-startup/04 + ch16-aosp/01 中覆盖
11. Satellite API 性能 (7/20) — 已有 11-satellite-low-bandwidth + 22-location-services
12. 线上疑难问题参考书内容映射 (N/A) — 59篇全部映射到现有章节

**检查维度**：
- Clippings 三本参考书（稳定性15篇、性能优化16篇、线上疑难59篇）→ 全部主题已有对应章节
- AOSP frameworks/base 核心服务 → WindowManager/ActivityManager/Telephony/Connectivity/PowerManager 均已覆盖
- 12个候选关键词全文搜索 → 均有对应章节
- 每日信息 + 研究素材 → 无新方向

**结论**：全书 ~577 个小节，覆盖范围已饱和（连续第5轮确认）。建议后续挖掘周期转为已有章节深度扩展。
