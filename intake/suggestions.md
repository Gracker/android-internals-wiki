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
## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04

- **类型**：源码准确性/版本差异/知识盲区
- **位置**：Section 3.2 版本兼容性
- **问题**：FrameRateOverrides API 的部分实现机制描述不够完整，缺少与 WindowManager 的交互细节
- **建议**：补充 FrameRateOverrides 如何影响帧调度计划、VSync 偏移动态调整、以及与 FrameTimeline Expected Timeline 的协同机制

- **类型**：版本差异
- **位置**：Section 3.2 Android 17 新增内容
- **问题**：Android 17 中 DeviceConfig 的具体实现细节描述不够准确，需要补充具体的 proto 文件和配置机制
- **建议**：补充 Android 17 中 Perfetto DeviceConfig 机制的具体实现细节，包括配置选项和动态调整能力

- **类型**：知识盲区
- **位置**：Section 3.2 版本兼容性
- **问题**：缺少对 Android 17 中 Adaptive RefreshRate 对性能分析影响的深入讨论
- **建议**：分析 Adaptive RefreshRate 场景下的 VSync 调整对渲染管线的影响，以及如何在这种场景下进行性能分析

## [Task14 参考书扫描] ch10 ch04 — 2026-07-04
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
- **建议补充**：maps 文件解析内部机制 — load_maps() 源码中对每块内存区域的分类逻辑（HEAP_NATIVE/HEAP_DALVIK/HEAP_SO/HEAP_DEX/HEAP_ART/HEAP_GL_DEV 等），如何按 maps 条目名（[heap]、[anon:libc_malloc]、[anon:dalvik-]等）归类到 dumpsys meminfo 输出的各个类别。ch10/01 已展示 dumpsys meminfo 输出格式，但缺少内部 load_maps 分类逻辑的源码级说明
- **参考书覆盖深度**：深入（含源码 walkthrough）
- **价值**：帮助读者理解 meminfo 数据来源和分类原理，对线上内存异常监控时上传 maps 文件做服务端解析有直接指导意义

## [Task14 参考书扫描] ch10 — 2026-07-04
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
- **建议补充**：Graphic 内存三类细分 — Gfx dev（映射到进程的 GPU 内存，高通 kgsl-3d0 路径）、GL mtrack（未映射的纹理/顶点/shader）、EGL mtrack（Layer Surface via gralloc）。参考书提供了 /d/kgsl/proc/{pid}/mem 文件解析和高通 kgsl_memtrack_get_memory 源码。ch10/08-gpu-memory-tracking 可能已有覆盖，建议交叉验证
- **参考书覆盖深度**：深入（含 HAL 层源码和文件节点示例）
- **价值**：GPU/Graphic 内存排查时的关键参考

## [Task14 参考书扫描] ch04 — 2026-07-04
- **类型**：版本更新
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
- **过时内容**：通过读取/解析 maps 文件获取内存数据无频控限制
- **建议更新至**：Android 10 起对 maps 读取加了 5 分钟频控（因性能开销大），ch04/02-linux-memory 已讨论 page fault 等机制但未提及此限制。建议在 ch10/01 或 ch04 中补充该限制说明

## [Task14 参考书扫描] ch25 — 2026-07-04
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md]
- **建议补充**：Dex 文件数据段详解 — header/string_ids/type_ids/proto_ids/field_ids/method_ids/class_def/data 各段含义和索引→数据区查找机制。ch25.6 已覆盖 APK 结构概述和 R8 优化，但缺少 dex 文件内部数据段级别的说明
- **参考书覆盖深度**：中等（表格形式列出各段含义）
- **价值**：理解 dex 体积优化的底层依据

## [Task14 参考书扫描] ch25 — 2026-07-04
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：重新认识 APK 安装包.md]
- **建议补充**：APK 构建流程详解 — 编译流程（aapt 资源编译→javac→R8）和打包流程（zip压缩→签名→字节对齐），以及 gradle task 全景表。ch25.6 侧重体积分析方法，构建流程细节可作为背景知识补充
- **参考书覆盖深度**：中等（含 DX→D8→R8 演进和 gradle task 表）
- **价值**：在构建流程中发现体积优化切入点

## [Task14 参考书扫描] ch04 — 2026-07-04
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]
- **建议补充**：malloc 内存分配策略 — malloc < 128k 时使用 sbrk()（移动 brk 指针），≥ 128k 时使用 mmap() 匿名映射。ch04/02 已覆盖 mmap 和 page fault 机制但未提及此阈值行为
- **参考书覆盖深度**：概述
- **价值**：理解 Native Heap 分配行为差异，对大对象内存优化有参考意义

## [Task14 参考书扫描] ch05 ch27 — 2026-07-04
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
- **建议补充**：CPU 时间公式作为理论框架 — CPU时间 = 程序指令数 × 时钟周期时间 × 每条指令平均时钟周期数(CPI)。ch05.1 侧重 Linux 调度器原理，ch27 侧重实战配置，但缺少这个三因子理论模型作为优化思路串联。基于三因子可衍生：减少指令数（多核并发/精简代码/预加载/转移计算）、降低时钟周期（避免降频）、降低 CPI（减少IO等待/编译优化）
- **参考书覆盖深度**：概述（含三因子拆解和各类优化方案映射）
- **价值**：为散乱的 CPU 优化手段提供统一理论框架

## [Task14 参考书扫描] ch05 — 2026-07-04
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
- **建议补充**：存储器层次结构与缓存命中率优化 — 寄存器→L1→L2→L3→主存→磁盘的读写速度差距（以骁龙888 L2=1M/L3=3M为例），局部性原理提升缓存命中率的方法论。参考书提及 Dex class 文件重排提升高速缓存命中率的思路
- **参考书覆盖深度**：概述
- **价值**：为缓存优化类方案提供底层依据，Dex 重排思路值得在 ch08 启动优化中展开


## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：知识盲区
- **位置**：Section 4.3 "Perfetto trace_processor 实战"
- **问题**：缺少 Perfetto 在 low-memory 设备上的替代方案（如使用 perfetto --size 限制采集大小，或者使用 ftrace + simpleperf 组合方案）
- **建议**：补充低内存环境下的性能分析策略，包括内存限制下的采样配置、轻量级替代方案等

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据缺失
- **位置**：Section 7.1 "验证的铁三角"
- **问题**："性能改动后自动跑一遍所有性能用例"缺少具体的自动化方案（如使用 AndroidX Benchmark 库，还是基于 Espresso 的自定义性能测试）
- **建议**：补充具体的性能测试自动化工具链和实现方案，包括主流库的选择依据和配置示例

## [Task2A Gap Mining Round 6] 2026-07-04 — Coverage Saturated

已检查方向（全部已覆盖或 <14 分）：
1. Desktop Mode / Freeform Window 性能 → 22.14 已覆盖 (ready-for-review)
2. Adaptive Refresh Rate → 22.18 已覆盖 (ready-for-review, 273 lines)
3. BLE Audio / LE Audio → ch05/22 已覆盖
4. Vulkan GPU 编译管线 → 22.29 已覆盖 (ready-for-review)
5. sched_ext OEM BPF 调度器 → ch17/04 已覆盖
6. 模块化启动框架 → ch21 已有多进程启动章节 (21.7)
7. heapprofd 生产部署 → ch14 Perfetto 工具链已覆盖
8. LMKD batch/thrashing → 4.5 已覆盖 (ready-for-review, 504 lines)
9. Binder 死亡通知批量派发 → ch01 Binder 系列已覆盖
10. NSD / Wi-Fi Direct / BLE 近场通信 → 非核心性能主题 (<14)
11. Compose Paging 3 → 库使用模式，非系统性能 (<14)
12. 模拟器 vs 真实设备差异 → research-gaps 已记录，ch15 覆盖
13. 新 DeepResearch (LMKD/Binder/Modular Startup/heapprofd) → 全部是现有章节的素材补充
14. 新 Task14 参考书扫描建议 → 全部是现有章节的内容增强
15. 队列清理：1.50/1.51/1.52/4.12/9.12 标记为 deprecated（重复章节）

结论：第 6 轮连续无 ≥14 分候选。全书 577 节，覆盖已饱和。
剩余 pending 队列 2 条（1.25 Binder 线程池补充、14.22 HPROF 补充），均为现有章节素材注入。

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：源码准确性
- **位置**：Section 3.2 "版本兼容性"
- **问题**：Android 17 中 DeviceConfig.perfetto 相关配置的具体实现细节未在源码中验证
- **建议**：补充 DeviceConfig 中具体的 perfetto 相关 key 名称和配置范围，或者在无法验证时明确标注为待验证

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据支撑
- **位置**：Section 7.1 "验证的铁三角"
- **问题**：灰度发布所需的最小样本量缺少具体数值指导
- **建议**：补充不同置信度水平下所需的最低样本量计算公式或经验值（如 P99 指标需要比 P50 更大样本量）

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据支撑
- **位置**：Section 4.4 "自适应刷新率场景的帧数据分析"
- **问题**：FrameRateOverrides API 的性能影响缺少实测数据支撑
- **建议**：补充典型场景下使用 FrameRateOverrides 前后的性能对比数据，包括不同刷新率设置对用户体验的实际影响


## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：源码准确性
- **位置**：Section 3.2 "版本兼容性"
- **问题**：Android 17 中 DeviceConfig.perfetto 相关配置的具体实现细节未在源码中验证
- **建议**：补充 DeviceConfig 中具体的 perfetto 相关 key 名称和配置范围，或者在无法验证时明确标注为待验证

## [Task9 Deep Review] ch15-methodology — Android 性能优化研究方法论 — 2026-07-04
- **类型**：数据支撑
- **位置**：Section 7.1 "验证的铁三角"
- **问题**：灰度发布所需的最小样本量缺少具体数值指导
- **建议**：补充不同置信度水平下所需的最低样本量计算公式或经验值（如 P99 指标需要比 P50 更大样本量）

## [Task9 Deep Review] 15.9 — 从采集到治理的反馈回路 — 2026-07-04
- **类型**：知识盲区
- **位置**：整体章节未涉及企业级平台设计
- **问题**：章节未说明多租户场景下的数据隔离问题，这是企业级监控平台的重要考量
- **建议**：补充多租户数据隔离架构设计和访问控制机制说明

## [Task9 Deep Review] 15.9 — 从采集到治理的反馈回路 — 2026-07-04
- **类型**：数据缺失
- **位置**：治理回路八步流程
- **问题**：治理回路八步中缺少具体的数据指标示例和阈值设定参考，难以指导实际落地
- **建议**：补充典型场景下的异常检测阈值设定参考和数据规模说明（如"每分钟处理多少个异常样本"）

## [Task9 Deep Review] 15.9 — 从采集到治理的反馈回路 — 2026-07-04
- **类型**：知识盲区
- **位置**：整体章节架构设计
- **问题**：章节缺少离线数据缓存与同步机制的说明，影响监控系统的可用性设计
- **建议**：补充离线数据缓存策略、同步机制和断网场景下的数据采集处理方案

## [Task9 Deep Review] 15.9 — 从采集到治理的反馈回路 — 2026-07-04
- **类型**：知识盲区
- **位置**：数据采样与治理
- **问题**：章节未提及数据采样中的伦理和隐私考量，这在现代监控系统中越来越重要
- **建议**：补充数据采样的隐私保护机制、用户授权流程和数据脱敏方案

## [Task9 Deep Review] 15.9 — 从采集到治理的反馈回路 — 2026-07-04
- **类型**：交叉引用一致性
- **位置**：章节与15.3节的关系
- **问题**：与15.3章节中提到的指标体系存在不完全一致的情况，影响知识体系的连贯性
- **建议**：统一与15.3章节的指标体系描述，确保术语定义和分类标准的一致性


## [Task2A Gap Mining Round 7] 2026-07-04 09:15 — Coverage Saturated (Round 7)

已检查方向（全部已覆盖或 <14 分）：
1. Repository suspend fun / 结构化并发性能 → 架构模式，非系统性能主题 (8/20)
2. Clean Architecture / UseCase 分层 → 软件工程，非运行时性能 (7/20)
3. Compose Pager 性能 → UI 组件教程，非系统级性能 (9/20)
4. GUI 代理基准 (AndroidDaily) → AI/ML 评估，非性能优化 (6/20)
5. 构建失败诊断研究 → 构建时，非运行时性能 (5/20)
6. 代码指标预测应用受欢迎度 → 代码质量，非性能 (5/20)
7. MVVM/MVI 架构对比 → 架构模式，非性能 (7/20)
8. Linux 内核沙箱 (Z-Jail) → 安全隔离，非性能优化 (6/20)
9. NSD/Wi-Fi Direct/BLE 近场通信 → Round 4-6 已评估 <14 (9/20)
10. Android 17 ML Scheduler → ch01.43 已覆盖
11. Linux 6.10 内存碎片整理 → ch06.19 已覆盖
12. Desktop Experience → 22.14 已覆盖

新增检查维度（相比前 6 轮）：
- 今日掘金 5 篇热门文章全部映射 → 无系统性能方向
- 今日论文精读 3 篇 → 全部非性能优化主题
- ClawFeed 技术资讯 → Linux 沙箱等非 Android 性能主题

**结论**：第 7 轮连续无 ≥14 分候选。全书 577 节，覆盖已饱和。
建议后续挖掘周期继续维持「深度扩展」策略，聚焦已有章节的 🔸 扩展点填充和 Task14 参考书扫描建议的内容注入。


## [Task2A Gap Mining Round 8] 2026-07-04 10:09 — Coverage Saturated (Round 8)

已检查方向（全部已覆盖或 <14 分）：
1. Safety Center → 安全特性，非性能优化 (6/20)
2. Companion Device Manager → 配对/连接特性，非核心性能 (7/20)
3. Backup/Restore 性能 → 后台执行，开发者关注度低 (8/20)
4. Photo Picker → ch24.13 已覆盖 (transcoding performance)
5. Play Integrity API → ch08.15 已覆盖
6. App Standby Buckets → ch25.02/25.04/25.13 已覆盖
7. Foreground Service Types → ch25.02/25.05/25.22 已覆盖
8. Splash Screen API → ch21.05 已覆盖
9. Predictive Back → ch22.13 已覆盖
10. 16KB Page Size → ch20.13/ch20.15/ch23.13 已覆盖
11. ART Module → ch01.07/ch16.01/ch23.05/ch20.03 已覆盖
12. heapprofd 权限模型 → ch14 HPROF 系列 + DeepResearch 补充
13. Binder node release batch → ch01 Binder 系列 + DeepResearch 补充
14. LMKD batch/thrashing → ch04.05 + DeepResearch 补充

新增检查维度（相比前 7 轮）：
- Safety Center / Companion Device Manager / Backup-Restore 三个全新方向
- 今日 DeepResearch 3 篇全部映射到现有章节
- 全书 577 节状态分布：finalized 341 / ready-for-review 199 / draft 16 / deprecated 20

**结论**：第 8 轮连续无 ≥14 分候选。全书 577 节，覆盖已饱和。
建议后续挖掘周期继续维持「深度扩展」策略，聚焦已有章节的 🔸 扩展点填充和 DeepResearch 素材注入。


## [Task2A Gap Mining Round 9] 2026-07-04 11:11 — Coverage Saturated (Round 9)

已检查方向（全部已覆盖或 <14 分）：
1. Android Virtualization Framework (AVF) → ch1.32 已覆盖
2. Compose Compiler 代码优化 → ch22.28 已覆盖
3. Jetpack WindowManager 性能 → ch22.14 已覆盖
4. Foldable/Multi-display 性能 → ch2.28/ch2.30/ch22.27 已覆盖
5. Input Method Framework 性能 → ch13.14/ch13.15/ch14.21 已覆盖
6. Accessibility Service 性能 → ch7.19/ch7.20/ch5.21 已覆盖
7. ContentProvider 跨进程性能 → ch10.7/ch9.2/ch9.9 已覆盖
8. DEX/Package Parser 加载性能 → ch1.7/ch1.22/ch5.18 已覆盖
9. Foreground Service Type 约束 → ch11.02/ch25 间接覆盖, 非核心性能 (<14)
10. BatteryStats/PowerStats 导出 → ch11.1/ch11.5/ch11.6 已覆盖
11. Notification Builder/Trampoline → 间接覆盖, 非独立性能主题 (<14)
12. Backup/Restore 性能 → 后台执行, 开发者关注度低 (8/20)
13. Runtime Resource Overlay (RRO) → OEM/框架层, 应用开发者无关 (6/20)
14. SystemProperty read 性能 → ch13.21 等多个章节已涉及
15. Compose Lazy Layout internals → 26 个文件涉及, 已广泛覆盖
16. App Search/AppFunctions → ch8.18 等已涉及
17. Credential Manager → ch8.12/ch8.13 已覆盖
18. Predictive Animation → ch7.08 等已覆盖
19. WindowMetrics → ch22.14 已覆盖
20. PackageInstaller Session → ch1.46/ch1 系列已覆盖

新增检查维度（相比前 8 轮）：
- AVF/pKVM/crosvm 虚拟化性能 → ch1.32
- Compose Foundation Lazy internals 深度搜索 → 26 文件命中
- FGS Type / Notification Trampoline / RRO / Backup 四个全新方向
- Jetpack WindowManager / WindowMetrics 精确搜索
- SystemProperty read 性能（底层 IPC 性能）
- 全书 577 节，覆盖已饱和（第 9 次确认）

**结论**：第 9 轮连续无 ≥14 分候选。全书 577 节，覆盖已饱和。
当前 16 个 draft 章节中 8.9/8.10（各 40 行有效内容）需 Task 2B 深化处理，
不属于 Task 2A 空 draft 加工范围。
建议后续挖掘周期降低频次（每 3-6 轮挖掘一次即可），
将算力转向已有章节的 🔸 扩展点填充和 Clippings 参考书素材注入。


## [Task2A Gap Mining Round 10] 2026-07-04 12:14 — Coverage Saturated (Round 10)

已检查方向（全部已覆盖或 <14 分）：
1. VibratorManagerService HAL 性能 → 硬件特定，非性能核心 (6/20)
2. ClipboardService 持久化开销 → 非性能核心主题 (6/20)
3. AlarmManager exact alarm 批处理合并 → ch25.3/ch25.20 已覆盖
4. PermissionManager 运行时权限检查开销 → 权限检查非核心瓶颈 (6/20)
5. AccountManagerService token 获取延迟 → 后台认证，非性能优化核心 (6/20)
6. DownloadManager 大文件传输 → ch24 网络系列已覆盖
7. MediaSession 播放队列 IPC → ch25.17 后台音频已覆盖
8. WifiRTT (802.11mc) 测距性能 → 室内定位，开发者使用率低 (6/20)
9. NfcAdapter HCE 性能 → NFC 非性能核心 (6/20)
10. VoiceInteractionService hotword 检测 → 语音助手特定 (6/20)
11. TvInputService/TV 框架性能 → TV 特定，非手机核心 (6/20)
12. DreamService 屏保性能 → 开发者关注度极低 (6/20)
13. AttentionService 人脸检测开销 → Attention Service 非核心 (6/20)
14. FaceService 生物识别管线延迟 → ch8.12-8.13 已覆盖
15. GnssMeasurementProvider 定位获取成本 → ch25.22 已覆盖
16. IHwBinder vs binder 性能 → ch1.4 IPC 全景已覆盖
17. IncidentReport 系统遥测开销 → 系统遥测，非应用关注 (6/20)
18. DropBoxManager 崩溃日志写入开销 → 系统日志写入 (6/20)
19. AppOpsManager 操作检查开销 → 操作审计 (6/20)
20. UsageStatsManager 查询开销 → 使用统计 (6/20)
21. TextClassifierManager 文本分类 → 边缘 AI 服务 (6/20)
22. TranslationService 翻译开销 → 翻译服务 (6/20)
23. Companion Device Manager → Round 8 已评估 (8/20)
24. RecoverySystem/SystemUpdateManager → OTA 更新，非性能核心 (6/20)
25. RoleManager 角色检查 → 角色管理 (6/20)
26. SearchManager/GlobalSearchService → 搜索框架 (6/20)
27. ContentSuggestionsManager → 内容建议 (6/20)
28. SmartSelectionService → 文本选择 (6/20)
29. InputContentInfo URI permission → ch3.11 IMM 已覆盖
30. MagisterService/ArtService → ch1.7 ART 已覆盖
31. HardwarePropertiesManager 温度查询 → ch5.12 thermal 已覆盖
32. SensorManager batch flush → ch25.5 已覆盖
33. MediaCodec async mode → ch18.23 Codec2 已覆盖
34. Camera2 state callback overhead → ch2.29-2.32/ch18.03 已覆盖

新增检查维度（相比前 9 轮）：
- 32 个 frameworks/base 与 system/ 下的系统服务/API 全面扫描
- 包含 HIDL/HwBinder、TV/NFC/Vibrator 等硬件相关服务
- 包含权限/审计/统计/搜索/翻译等框架服务
- 今日 daily-info 无新性能方向（Compose Pager/局域网通信/Clean Architecture 均非性能优化主题）
- 全书 589 节，覆盖已饱和（第 10 次确认）

**结论**：第 10 轮连续无 ≥14 分候选。全书 589 节，覆盖已饱和。
建议后续挖掘周期降低频次为每日仅检查 daily-info 新增内容，
如连续 3 轮仍无新候选，可将 gap mining 改为每周执行一次。
