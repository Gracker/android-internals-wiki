## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：源码准确性
- **位置**：Canvas.drawRect 示例源码路径
- **问题**：源码路径错误，未展示正确的AOSP实现路径
- **建议**：修正源码路径为 frameworks/base/graphics/java/android/graphics/BaseCanvas.java，补充完整的调用链说明

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：原理链完整性
- **位置**：GPU渲染管线章节
- **问题**：从Vertex Shader直接跳到Fragment Shader，缺少图元装配和光栅化阶段
- **建议**：补充图元装配（Primitive Assembly）和光栅化（Rasterization）阶段的详细说明，包括GPU内部的完整处理流程

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-11
- **类型**：源码准确性
- **位置**：Game Mode API使用示例
- **问题**：`GameManager.GAME_MODE_CUSTOM`常量在公开API中不存在
- **建议**：移除不存在的常量，使用兼容性处理逻辑，明确API边界和fallback机制

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-11
- **类型**：版本差异
- **位置**：Android 16渲染章节
- **问题**：Android 16相比Android 15的具体渲染机制变化描述不足
- **建议**：明确列出Android 16在渲染方面的具体变化，包括Vulkan Profile要求、ARR增强、新API特性等

## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-11
- **类型**：数据缺失
- **位置**：Vulkan vs OpenGL ES性能对比章节
- **问题**：性能改进数据缺乏基准测试数据支持
- **建议**：补充实际测试数据，包括不同分辨率、不同场景下的性能对比测试结果

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-11
- **类型**：数据缺失
- **位置**：ADPF热管理收益章节
- **问题**：声称的"57%收益"缺乏具体测试条件和数据支撑
- **建议**：提供具体的测试场景、设备型号、测试方法和量化数据，确保数据可验证性
## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：源码准确性
- **位置**：SQL 查询示例中的 sched 表查询
- **问题**：使用了不存在的 prev_cpu 字段，实际应为 cpu 字段 + LAG 窗口函数
- **建议**：修正 SQL 查询使用正确的字段和窗口函数，确保与 Perfetto sched 表实际结构匹配

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：原理链完整性
- **位置**：全大核架构下的迁移成本解释
- **问题**：仅提到 DSU 存在但未解释实际迁移开销机制
- **建议**：补充跨核迁移的实际开销分析，包括缓存未命中、uclamp、集群策略等因素的具体影响

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：GPU 性能对比部分
- **问题**：缺乏具体 Perfetto trace 片段示例
- **建议**：补充不同 SoC 上 GPU 渲染的 Perfetto track 实际截图对比，展示架构差异导致的 pipeline 特性

## [Task9 Deep Review] 20.4 ANR 治理策略 — 2026-05-12
- **类型**：原理链完整性
- **位置**：Dispatchers.IO 降级逻辑
- **问题**：未解释线程池耗尽时的降级机制和调度策略
- **建议**：补充 kotlinx-coroutines 线程池耗尽时的降级逻辑，包括 limitedParallelism 视图的具体行为和调度策略

## [Task9 Deep Review] 20.4 ANR 治理策略 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：ANR 治理策略整体
- **问题**：缺乏实际 ANR 案例的完整分析流程和决策过程
- **建议**：添加 2-3 个完整的 ANR 案例分析，包含实际排查过程、决策依据和优化效果

## [Task9 Deep Review] 20.8 崩溃聚合与归因分析 — 2026-05-12
- **类型**：原理链完整性
- **位置**：崩溃聚合算法分析
- **问题**：缺少具体实现细节和时间复杂度分析
- **建议**：详细分析主流崩溃聚合算法（如堆栈相似度计算、指纹生成算法）的实现细节和性能特征

## [Task9 Deep Review] 20.8 崩溃聚合与归因分析 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：崩溃聚合效果部分
- **问题**：缺乏崩溃聚合效果的量化数据和基准测试
- **建议**：添加不同聚合算法在实际应用中的效果对比数据，包括聚合准确率、处理性能、存储效率等指标

## [Task9 Deep Review] 20.8 崩溃聚合与归因分析 — 2026-05-12
- **类型**：数据与案例支撑
- **位置**：实战指导部分
- **问题**：缺乏具体实战案例和作者经验分享
- **建议**：补充完整的崩溃治理实战案例，包括问题发现、分析过程、修复决策和效果验证

## [Task14 参考书扫描] 1.15 JNI/NDK 性能优化 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native Hook 全解析：Native 闯关入门秘籍.md]
- **建议补充**：Native Hook 三大方案（GOT/PLT Hook、Inline Hook、dlsym 家族）的原理对比与适用场景；GOT 表 hook 完整实现流程（基地址获取 via /proc/self/maps → 重定位偏移 via readelf -r → mprotect 改写权限 → 替换函数指针）；Android 各版本 dlsym 限制差异；bhook/bytehook 等成熟框架选型建议
- **参考书覆盖深度**：深入（含完整代码示例和 ELF 原理）
- **知识点属性**：有代码示例、有案例、适用 Android 全版本、无过时风险

## [Task14 参考书扫描] 4.3 ART 虚拟机内存管理 / 4.5 App 内存优化 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - Native 内存泄漏监控：寻找 Native 中不可达内存.md]
- **建议补充**：libmemunreachable 系统级 Native 内存泄漏检测原理（fork 子进程 + pipe 通信 + root 引用链遍历）；32→64 位架构迁移的虚拟内存差异；CollectAllocations 中 heap/anon/globals/stack 四类映射的 Root 标记策略；Android N+ 系统自带能力的使用方式
- **参考书覆盖深度**：深入（含 AOSP 源码分析）

## [Task14 参考书扫描] 4.3 ART 虚拟机内存管理 / 4.5 App 内存优化 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - OOM 发生路径：了解 OOM 是如何产生的.md]
- **建议补充**：OOM 两大分类框架（Java 堆限制 vs 虚拟内存不足）的 ART 源码级分析；Heap::AllocObjectWithAllocator → AllocateInternalWithGc → Heap::ThrowOutOfMemoryError 完整调用链；Thread::CreateNativeThread 中 pthread_create 失败导致的 OOM 路径；JNI 层 NewString 等分配的 OOM 触发条件；各 space（NonMoving/Main/BumpPointer/Region/LOS）的 OOM 日志差异
- **参考书覆盖深度**：深入（含 ART 源码级调用链分析）

## [Task14 参考书扫描] 4.1 Android 内存模型全景 — 2026-05-12
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 应用稳定性剖析与优化 - 初识内存：内存是什么？.md]
- **建议补充**：OOM pending exception 机制的底层实现（throwing_OutOfMemoryError TLS 标志位 → ThrowNewException → UncaughtExceptionHandler 捕获）；堆内存 OOM 与虚拟内存 OOM 的独立性说明及典型错误信息格式对比
- **参考书覆盖深度**：概述（基础概念，但 OOM 投递机制有参考价值）


---

[Task2B 回炉失败] 22.3 — 原因：需要高爷确认

**问题**：Task 9 深度技术 Review 指出 Pausable Composition 在 Compose 1.10 中是实验性版本，正式默认启用在 Compose 1.11。当前章节标题写的是"Pausable Composition（Compose 1.10 默认启用）"。

**需要确认**：
1. Pausable Composition 的默认启用版本是 Compose 1.10 还是 1.11？
2. 如果是 1.11，需要同步更新章节标题和相关描述

**Queue 条目 ID**：task9-22.3-pausable-comp-version-error
**状态**：blocked

记录时间：2026-05-12 07:16


## [Task9 Deep Review] 22.3 Jetpack Compose 性能优化 — 2026-05-12
- **类型**：版本差异/知识盲区
- **位置**：工具介绍部分
- **问题**：Android Studio Compose Profiler 遗漏，未介绍 Android Studio 2024.1+ 的 Compose Profiler 工具使用方法
- **建议**：补充工具使用方法和最佳实践

## [Task9 Deep Review] 22.3 Jetpack Compose 性能优化 — 2026-05-12
- **类型**：数据缺失
- **位置**：优化效果说明
- **问题**：性能对比数据不充分，缺乏具体的性能提升数据支撑
- **建议**：补充基准测试数据和性能提升百分比

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：交叉引用错误
- **位置**：GPU 架构描述
- **问题**：与章节 2.10 的 GPU 渲染管线描述存在术语不一致
- **建议**：统一 GPU 相关术语使用

## [Task9 Deep Review] 17.2 SoC 平台差异 — 2026-05-12
- **类型**：数据缺失
- **位置**：Oryon 处理器参数
- **问题**：性能参数缺乏一手资料锚定，Oryon L1/L2 cache 一手资料边界仍未闭合
- **建议**：标注参数来源和验证边界

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-12
- **类型**：知识盲区
- **位置**：DeliQueue 机制说明
- **问题**：DeliQueue 同步屏障机制描述不完整，需查阅 postSyncBarrier() 实现
- **建议**：补充同步屏障机制的详细实现说明

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-12
- **类型**：数据缺失
- **位置**：性能提升说明
- **问题**：性能提升数据缺乏具体测试条件，缺乏具体的测试环境和测试条件说明
- **建议**：补充测试环境和基线数据

## [Task9 Deep Review] 1.5 线程模型 — 2026-05-12
- **类型**：数据缺失
- **位置**：L234 IdleHandler 1-2ms 阈值缺少测试条件
- **问题**：“控制在 1-2ms 以内”是经验阈值，但正文未给设备、刷新率、Trace 或业务场景。
- **建议**：补一条 Perfetto 示例或改成“不得超过当前帧预算中的空闲窗口”，避免固定阈值被当成平台规则。

## [Task9 Deep Review] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-05-12
- **类型**：数据缺失
- **位置**：L334 WebGPU 90%-95% Vulkan 吞吐量缺少一手数据
- **问题**：AndroidX WebGPU release notes 只说明 alpha 版本与 Dawn commit 更新，未给 Android 17 compute pipeline 对 Vulkan 90%-95% 的公开基准。
- **建议**：补 benchmark 来源、设备、driver、workload、样本数；否则删除百分比，只保留 WebGPU 是更高层 Kotlin binding / Dawn 路线。

## [Task6 Review] 4.3 ART 虚拟机内存管理 — 2026-05-12
- **类型**：需重写 / 需补充素材
- **位置**：参考资料之后的 ART FinalizerDaemon 与 ReferenceQueue 调研段落；全章实践与诊断部分
- **问题**：源码调研材料追加在参考资料之后，结构上像未消化素材；同时缺少大型应用 ART GC 诊断案例和作者经验。
- **建议**：将调研材料整合回正文对应小节或移为附录；补 1 个 Perfetto/Memory Profiler 诊断案例（现象、观察点、判断依据、修复动作、结果）。
- **review 日志**：logs/review/2026-05-12-16-review.md

## [Task6 Review] 4.5 App 内存优化 — 2026-05-12
- **类型**：需补充素材 / 需确认
- **位置**：监控兜底、内存抖动与高刷掉帧、Bitmap / inBitmap 优化收益
- **问题**：Perfetto/Memory Profiler 观察说明不足；“3ms 黄金停顿”“掉帧率下降 3-5 倍”“inBitmap 减少 80% 以上分配”等量化描述缺少测试条件或来源。
- **建议**：补充设备、系统版本、刷新率、负载场景、采样方法和对比数据；无数据时保留帧预算推导，删除固定百分比。
- **review 日志**：logs/review/2026-05-12-16-review.md


## [Task9 Deep Review] 5.2 EAS 能量感知调度 — 2026-05-12
- **类型**：数据缺失
- **位置**：L261 全大核架构的调度边界
- **问题**：骁龙 8 Elite Performance 核 capacity≈837、Prime/Performance 差距约 18% 缺少设备 kernel capacity、公开芯片资料或实机 `/sys/devices/system/cpu/cpu*/cpu_capacity` 锚点。
- **建议**：补一手来源或实机命令输出；否则改成定性描述，避免把单机型估算写成通用数值。

## [Task9 Deep Review] 5.7 CPU 相关的版本演进 — 2026-05-12
- **类型**：源码准确性/引用边界
- **位置**：L329 Android 17 已确认的功耗行为变更
- **问题**：“Reduced Wakelocks for Idle Alarms”和 `ProfilingManager.KILL_EXCESSIVE_CPU_USAGE` 被归到 behavior changes all-apps / target-37 页面，但此前审计已指出这两项更像 release notes / API reference 口径。
- **建议**：拆成 behavior changes、release notes、API reference 三类来源，分别标注，避免把 API 引用写成平台行为变更页结论。

## [Task6 Review] 20.5 OOM 治理 — 2026-05-12
- **类型**：需确认
- **位置**：Native 内存 OOM / Unsafe.allocateMemory
- **问题**：正文将 Gson 无空参构造函数反序列化归到 Unsafe.allocateMemory → malloc → native alloc OOM 路径；该路径可能应区分 Unsafe.allocateInstance 与 allocateMemory。
- **建议**：Task9 核对 Gson/Unsafe 实际调用链和 ART 抛 OOM 入口；Task2B 根据核对结果修正文中示例。
- **review 日志**：logs/review/2026-05-12-18-review.md

## [Task6 Review] 20.5 OOM 治理 — 2026-05-12
- **类型**：需确认
- **位置**：FD 泄漏导致的 OOM / FD 耗尽与 pthread_create
- **问题**：正文原先把 FD 耗尽与 pthread_create 内部分配 epoll FD 直接绑定；epoll FD 通常来自 Looper 初始化，不一定是 pthread_create 本身。
- **建议**：Task9 核对 pthread_create、Looper epoll 初始化、FD 耗尽三者的边界；Task2B 将线程创建 OOM 与 FD 泄漏 OOM 拆开写。
- **review 日志**：logs/review/2026-05-12-18-review.md


## [Task9 Deep Review] 7.6 案例集 — 2026-05-12
- **类型**：数据缺失
- **位置**：全文 7 个案例的 Trace 与效果对比
- **问题**：章节已标注原始 trace 与截图尚未归档，当前耗时区间、Jank 率、内存数值都只能作为案例化示例；案例型章节如果没有至少 1-2 份可复核 trace，读者无法验证判断链。
- **建议**：为每类根因补 trace 文件名、设备型号、Android 版本、刷新率、采样窗口、样本次数和前后对比表；未补齐前保留 `[待验证]`，不要把数值写成实测结论。

## [Task9 Deep Review] 20.5 OOM 治理 — 2026-05-12
- **类型**：知识盲区 / 风险边界
- **位置**：L349-L367 Native 层 `sigsetjmp` / `siglongjmp` 线程级兜底
- **问题**：该方案属于 Native crash 防护，不是 OOM 专属治理；信号处理、非 async-signal-safe 调用、锁状态、堆状态和业务一致性都有风险，正文当前只给实现骨架，缺少适用边界。
- **建议**：补充 signal-safety、备用信号栈、只限非关键后台线程、恢复后必须隔离/上报/停止复用该线程等边界；否则降低为“工程参考”，不要作为通用 OOM 兜底策略。


## [Task6 Review] 20.6 稳定性度量与指标体系 — 2026-05-12
- **类型**：需补充素材 / 需确认
- **位置**：行业参考值、行业对标参考、PV 崩溃率命名
- **问题**：行业对标数值缺公开来源或内部口径说明；PV 崩溃率与 Session Crash Rate 的术语关系需要确认。
- **建议**：补官方文档、公开分享或内部指标口径；无法补源的行业值改成匿名经验区间并标注边界。术语由 Task9 确认后统一。
- **review 日志**：logs/review/2026-05-12-19-review.md

## [Task6 Review] 21.2 启动框架设计与任务编排 — 2026-05-12
- **类型**：需确认
- **位置**：IO 线程池 ThreadFactory 示例、线程优先级策略表格
- **问题**：`Thread.getId()` 与 `Process.setThreadPriority()` 的用法可能不可靠；关键启动线程 `-2 ~ -4` 的可设置范围和权限边界需要核对。
- **建议**：Task9 对照 Android 线程优先级 API / 常量确认；必要时改为在线程执行体内设置优先级，并补充权限边界。
- **review 日志**：logs/review/2026-05-12-19-review.md


## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-05-12
- **类型**：数据缺失/版本差异
- **位置**：§WorkManager 2.10 与 Android 17 的协同优化
- **问题**：`WorkManager 2.10 深度适配 DeliQueue` 和“掉帧率下降约 4%”缺 Jetpack WorkManager release note、源码提交或独立 benchmark。当前证据更像 Android 17 MessageQueue/DeliQueue 的系统级收益，不能直接归因到 WorkManager 2.10。
- **建议**：补 AndroidX WorkManager 2.10 对 MessageQueue/DeliQueue 的具体改动链接与实验条件；补不到时改成“Android 17 DeliQueue 可降低密集 enqueue 场景的主线程锁等待”，避免把收益归到 WorkManager 版本。

## [Task9 Deep Review] 6.3 I/O 调度与性能 — 2026-05-12
- **类型**：源码准确性/边界说明
- **位置**：§ionice：进程级 I/O 优先级
- **问题**：示例直接写“将前台 App 设为 RT”的 `ionice -c 1`，但普通 App 不能在量产设备上任意设置 RT I/O class；该操作通常需要 root/userdebug 或系统权限。缺少权限边界会误导读者把调试命令当成应用侧优化手段。
- **建议**：标明这是 rooted/userdebug/系统进程排查命令；应用侧应通过系统公开入口、后台任务策略和设备 task profile 间接影响 I/O，而不是自行 `ionice`。

## [Task9 Deep Review] 6.4 存储相关的版本演进 — 2026-05-12
- **类型**：数据缺失
- **位置**：§16KB 页对齐、§EROFS 的核心技术优势
- **问题**：`PSS 平均增加约 9%`、EROFS `24%-45%`、`App 启动最高提升 22.9%` 等数字缺设备、Android 版本、页面大小、分区大小、压缩算法、测试 workload 和原始链接。作为版本演进章节，这些数字会影响读者对收益/代价的判断。
- **建议**：补官方或论文/演讲出处、测试条件和基线；无法补齐时保留方向性结论，删除固定百分比或标成待验证案例。

## [Task6 Review] 5.1 Linux 进程调度基础 — 2026-05-12
- **类型**：需确认 / 内容结构
- **位置**：常见问题与误区之后「Android OOM Adj 与 TrimMemory 机制」
- **问题**：该段更接近 §7.3 内存回收/进程优先级内容，插在 Linux 调度章节末尾会打断主线。5.1 另有既存 L3/L4 回炉项：调度器深度分析和实战决策指导不足。
- **建议**：Task 2B 判断是否移回 §7.3；若保留在 5.1，只保留与调度优先级、cgroup、oom_score_adj 的交叉引用。
- **review 日志**：logs/review/2026-05-12-20-review.md

## [Task6 Review] 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线 — 2026-05-12
- **类型**：需确认 / 技术证据
- **位置**：Android 17 NPU 硬件特性声明；CompiledModel API V2 与 AOT 编译
- **问题**：Android 17 NPU feature、意图防火墙、电量配额审计、CompiledModel V2、AICore 路由和 AOT 耗时数据等断言缺少一手官方文档或源码锚点。Task 6 不裁决真伪，已在正文加 `[存疑]` 标注。
- **建议**：Task 9 先核对 Android SDK / AOSP / LiteRT / AICore 官方资料；Task 2B 再按复核结果补证据、降级表述或删除无法验证的数值。
- **review 日志**：logs/review/2026-05-12-20-review.md


## [Task9 Deep Review] 21.1 启动全链路分析（App 视角） — 2026-05-12
- **类型**：数据缺失/版本边界
- **位置**：L115-L119 冷启动典型耗时、L406 GC 抑制 2 秒、L494 Baseline Profile 20%-40% 收益
- **问题**：这些数字和版本结论缺设备、系统版本、采样方法、官方文档或实验来源。尤其“Android 8+ 启动时自动抑制 GC 2 秒”和 Baseline Profile 20%-40% 收益会影响读者对优化优先级的判断。
- **建议**：补 Android Developers / ART 源码 / Macrobenchmark 数据来源；补不到时改成经验区间或 `[待验证]`，不要作为通用 Android 10-16 结论。

## [Task9 Deep Review] 21.2 启动框架设计与任务编排 — 2026-05-12
- **类型**：源码准确性/实现边界
- **位置**：L216 Jetpack App Startup “按依赖拓扑排序执行所有 Initializer”
- **问题**：AndroidX AppInitializer 实现是先发现 metadata，再递归初始化 dependencies；它满足依赖先执行，但不是一个可调度的全局拓扑排序执行器，也没有并行、优先级或超时语义。当前表述容易和后文 Alpha/自研 DAG 调度器混淆。
- **建议**：改成“递归初始化依赖并做环检测”，避免把 App Startup 描述成完整 DAG scheduler。

## [Task6 Review] 1.9 Package Manager Service 与应用安装性能 — 2026-05-12
- **类型**：需确认 / 需补充素材
- **位置**：`## Android 16 云端编译与 SDM 机制深度分析`
- **问题**：前文已声明 Android 16 云端编译 / SDM 缺少可交叉核对的一手资料，不下确定性结论；后文又以 AOSP 源码形式给出 `PackageSnapshotCompiler`、`SDM`、`CloudCompilerNetworkService` 等类名和调用链，并给出 30-50% / 15-25% 等性能数值。Task 6 不裁决真伪，已在正文加 `[存疑]` 标注。
- **建议**：Task 9 先核对 AOSP / Android Developers / Source.android.com 是否存在这些类、接口、数值和版本边界；Task 2B 再按复核结果补证据、降级表述或删除无法验证的深度段。
- **review 日志**：logs/review/2026-05-12-21-review.md

## [Task9 Deep Review] 4.1 Android 内存模型全景 — 2026-05-12
- **类型**：版本验证/数据缺失
- **位置**：frontmatter `last_verified_against`；正文 `[待补充]` 标记
- **问题**：正文已包含 Android 17 app memory limits / MemoryLimiter:AnonSwap / TRIGGER_TYPE_ANOMALY，但验证基线仍主要写 AOSP android-16.0.0_r1；同时 dumpsys/Perfetto/Graphics/内存泄漏示例仍有截图或 Trace 样本待补充。
- **建议**：补 Android 17 官方 behavior changes / ProfilingManager 触发式 profiling 来源；补样本时标注设备型号、Android 版本、page size、TraceConfig 数据源和采样周期。

## [Task9 Deep Review] 8.8 Android 多媒体管线性能 — 2026-05-12
- **类型**：数据缺失/观察边界
- **位置**：L175-L178 AudioTimestamp；版本演进 Android 16 条目
- **问题**：`AudioTimestamp` 未说明来自 `AudioTrack.getTimestamp()`，也未交代 HAL 时间戳精度边界；16KB page / Gralloc AIDL V2 对 4K/8K 编解码吞吐的收益缺公开 benchmark 支撑。
- **建议**：补 AudioTrack timestamp API 与设备精度边界；16KB/Gralloc 收益改成 `[待验证]` 或补设备、内容、codec、分辨率、fps、TLB/CPU counter 对照数据。


## [Task6 Review] 2.10 GPU 渲染深入 — 2026-05-12
- **类型**：需重写 / 需补充素材
- **位置**：参考资料之后的源码调研补充；实战案例“社交应用图片滚动中的 GPU 瓶颈定位”
- **问题**：参考资料之后继续展开正文内容，结构边界断裂；实战案例给出设备、帧耗时、帧率和优化收益，但缺真实 Trace/AGI 截图、采样条件或匿名复现说明。
- **建议**：Task 2B 将补充内容整合回正文或附录；补一手证据与测试条件。若只是示意案例，改成“示例场景”并删除固定收益数值。
- **review 日志**：logs/review/2026-05-12-23-review.md

## [Task6 Review] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-05-12
- **类型**：需确认 / 需补充素材
- **位置**：WebGPU / Dawn：另一条新接口
- **问题**：“Jetpack WebGPU 在 Android 17 上的计算管线基准测试达到 Vulkan 原生实现 90%-95% 吞吐量”缺 benchmark 来源、设备、库版本和 workload 条件。
- **建议**：补官方或上游 benchmark 链接与测试条件；补不齐时改成定性描述，避免把单一测试写成通用结论。
- **review 日志**：logs/review/2026-05-12-23-review.md

## [Task6 Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-12
- **类型**：需确认 / 技术证据
- **位置**：补充：DeliQueue drain 触发机制和 Generational CMC gating 条件深度验证 / ProfilingManager 触发器内部判断逻辑
- **问题**：该小节以源码级口吻给出 `ProfilingManagerService` 内部判断伪代码和触发器行为差异，但缺 API 37 源码锚点、提交或官方 reference。Task 6 不裁决真伪，已在正文加 `[存疑]` 标注。
- **建议**：Task 9 先核对 API 37 / AOSP preview 源码；无法核实时降级为示意流程，删除具体阈值与函数名。
- **review 日志**：logs/review/2026-05-12-23-review.md

## [Task6 Review] 21.5 Splash Screen 与感知启动速度 — 2026-05-13
- **类型**：需确认
- **位置**：SplashScreen API 适配 / 在 Activity 中安装 SplashScreen
- **问题**：代码示例与文字说明对 `installSplashScreen()` 和 `super.onCreate()` 的顺序描述不一致，属于 API 行为边界。
- **建议**：Task 9 按当前 AndroidX core-splashscreen / 官方文档复核调用顺序；Task 2B 再统一示例和正文说明。
- **review 日志**：logs/review/2026-05-13-01-review.md

## [Task6 Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-05-13
- **类型**：需补充素材
- **位置**：WorkManager 2.10 与 Android 17 DeliQueue 协同优化；Android 17 Power Check 阈值描述
- **问题**：正文保留了“掉帧率下降约 4%”和 Power Check 检查周期/阈值分段等量化口径，但当前来源列表与段落标注没有给出官方发布说明、benchmark 条件或实测记录。
- **建议**：补充官方文档、发布说明或实测 trace；如果只能作为观察结论，应改成待验证表述并给出测试条件。
- **review 日志**：logs/review/2026-05-13-02-review.md

## [Task6 Review] 17.2 SoC 平台差异 — 2026-05-13
- **类型**：需重写
- **位置**：常见问题之后的 “sched_ext 在 Android OEM 上的 BPF 调度器实现” 素材块
- **问题**：sched_ext 调研素材仍以资料卡片形式堆在正文末尾，和前文 CPU 调度策略、Perfetto 观测差异没有形成叙述链路。
- **建议**：由 Task2B 将素材拆入“厂商调度策略差异”和“不同 SoC 上 Perfetto 数据的差异”，按 Qualcomm / MediaTek / Google Pixel 三类 OEM 调度器说明适用版本、证据边界和 trace 观察点。
- **review 日志**：logs/review/2026-05-13-02-review.md

## [Task9 Deep Review] 7.3 卡顿分析方法论 — 2026-05-13
- **类型**：源码准确性/指标口径
- **位置**：L388-L389 FrameMetrics `TOTAL_DURATION` / `DEADLINE`
- **问题**：`TOTAL_DURATION` 被描述为“从 Choreographer 回调开始到 GPU 完成渲染”，容易和 API 31+ 的 `GPU_DURATION`、FrameTimeline Actual 中的 GPU work 混淆；官方只把它定义为 total frame duration，`DEADLINE` 是系统给 App 产出一帧的可用时长。
- **建议**：改为“FrameMetrics 各阶段总时长 / total frame duration；GPU 侧单独看 `GPU_DURATION` 或 FrameTimeline Actual”，保留 `TOTAL_DURATION > DEADLINE` 作为线上粗筛。

## [Task9 Deep Review] 7.3 卡顿分析方法论 — 2026-05-13
- **类型**：数据缺失
- **位置**：多处 `[待补充：Trace 截图]`（三线程 Pin、FrameTimeline、线程状态、Critical Path）
- **问题**：本节是方法论章节，关键判断依赖 Trace 观察，但核心截图仍为空位；不影响技术结论通过，但会削弱读者复现能力。
- **建议**：补 1 份 Android 12+ FrameTimeline Trace 与 1 份调度延迟 Trace，标注设备、版本、刷新率、TraceConfig 与问题帧 token。

## [Task9 Deep Review] 7.8 RecyclerView 列表滑动性能深度优化 — 2026-05-13
- **类型**：源码准确性
- **位置**：L124-L132 ViewHolder 回收复用的四级缓存
- **问题**：AttachedScrap 被解释成“被移出屏幕但还会回来”的缓存层，容易与 `mCachedViews` 混淆；源码里还存在 `mChangedScrap`，pre-layout/change animation 场景下语义不同。
- **建议**：按 `mAttachedScrap` / `mChangedScrap`、`mCachedViews`、`ViewCacheExtension`、`RecycledViewPool` 分开说明，明确 AttachedScrap 是 layout pass 中临时 detach/scrap 的已附着 ViewHolder。

## [Task9 Deep Review] 7.8 RecyclerView 列表滑动性能深度优化 — 2026-05-13
- **类型**：原理链完整性
- **位置**：L413-L500 GapWorker bindTime 与 ConstraintLayout 多次测量
- **问题**：同一盲区在 2026-04-25 与 2026-05-04 两段中重复展开，后一段还包含“源码改进建议”伪代码，容易把当前 AndroidX 行为与作者推演方案混在一起。
- **建议**：合并为一段“已验证现状 + Perfetto 识别 + 工程应对”，把平台/库级改进设想移到 research note 或明确标 `[建议方向]`。

## [Task9 Deep Review] 8.2 App 启动全流程 — 2026-05-13
- **类型**：数据缺失
- **位置**：L185-L187 16KB page size 冷启动收益
- **问题**：“冷启动平均提速约 3.16%”缺少 Google 原文链接、测试设备、样本 App、page size 对照条件；`libwebviewchromium.so` 等大小也会随版本和 ABI 变化。
- **建议**：补 Android 15 16KB page size 官方 benchmark 链接和测试条件；补不到则保留定性解释，把 3.16% 降级为 `[待验证]`。

## [Task6 Review] 21.7 多进程启动优化 — 2026-05-13
- **类型**：需确认
- **位置**：跨进程初始化依赖管理 / `MODE_MULTI_PROCESS` 段落
- **问题**：当前段落写成“官方 `Application` 文档里……”，但该常量/警告的官方引用路径可能应为 `Context` / `SharedPreferences` 相关文档；Task 6 不裁决真伪，已在正文加 `[需确认]` 标注。
- **建议**：Task 9 按当前 Android Developers reference 复核来源路径和废弃说明；Task 2B 再统一正文措辞与验证标注。
- **review 日志**：logs/review/2026-05-13-03-review.md

## [Task9 Deep Review] 8.6 Kotlin Coroutine 性能实践 — 2026-05-13
- **类型**：数据缺失
- **位置**：L249、L592-L600 Kotlin 2.2 性能提升约 15%
- **问题**：正文把 15% 写成已验证结论，但同章末尾又标注“待验证官方 benchmark 数据”。
- **建议**：补充具体 benchmark 来源、测试条件和 kotlinx.coroutines/Kotlin 版本；未找到官方数据前删除 15% 或改为待验证。

## [Task9 Deep Review] 13.6 线程 CPU 状态分析 — 2026-05-13
- **类型**：交叉引用/SQL
- **位置**：L495-L524 SQL 示例
- **问题**：同章前文引用 Perfetto 官方 sched_slice 表，但后文 CPU 统计 SQL 使用 sched 表；CPU 利用率也未说明多核下可能超过 100% 或是否按核心数归一化。
- **建议**：统一改用 sched_slice 或标注 sched 兼容视图；补充“单核百分比/总核归一化”两种口径。

## [Task9 Deep Review] 14.3 内存分析工具 — 2026-05-13
- **类型**：数据缺失
- **位置**：L551 malloc hooks 性能 2-5 倍分配延迟
- **问题**：“2-5 倍”缺少测试设备、分配大小、hook 行为和来源，且 hook 空实现与记录调用栈的开销差异很大。
- **建议**：补充自测 microbenchmark 或 AOSP/官方说明；无数据前改为“会显著增加分配路径开销，需实测”。

## [Task6 Review] 21.8 启动监控与度量 — 2026-05-13
- **类型**：需确认
- **位置**：Android 15+ 的平台启动信息 / `ApplicationStartInfo` 段落
- **问题**：正文提到 Android 15+ `ApplicationStartInfo` 可提供启动类型、启动原因、时间戳等信息，但字段名称、Android 15/16 可用性和版本边界仍需源码/API 复核。Task 6 不裁决 API 真伪，已在正文加 `[需确认]` 标注。
- **建议**：Task 9 对照 Android Developers reference 与 AOSP API 定义核对字段、权限和版本差异；Task 2B 再把结论改成已验证口径或降级为兼容性提示。
- **review 日志**：logs/review/2026-05-13-04-review.md


## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-13
- **类型**：原理链/源码支撑
- **位置**：L153-L155
- **问题**：Graphite 被解释为“Front-to-Back + Early-Z 跳过遮挡像素”的核心设计，但正文没有给 Skia 一手设计文档或 Android HWUI 集成源码锚点；容易把 Graphite 的任务图/资源管理/现代 GPU 后端演进误写成单一遮挡剔除机制。
- **建议**：补 Skia Graphite 官方设计资料；若无法核实，降级为“Graphite 是 Skia 下一代 GPU 后端，Android HWUI 默认启用仍待集成验证”，删除 Early-Z 作为核心机制的强断言。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-13
- **类型**：数据缺失
- **位置**：L436
- **问题**：“16KB Page Size 让 TLB 命中率提升约 9%，渲染管线有效带宽增益”缺少设备、内核页大小、SoC、workload、采样方法和来源；该行被放进版本时间线，读者会把它当成平台通用结论。
- **建议**：补可复现实验或官方性能数据；否则删掉百分比，改成“16KB 页会改变 TLB/内存映射开销，具体收益依赖设备和 workload”。

## [Task6 Review] 21.9 启动优化案例集 — 2026-05-13
- **类型**：需补充素材
- **位置**：全文案例段落 / 开头问题标注
- **问题**：本节定位为案例集，但现有 `Application` 初始化、启动框架演进、Baseline Profile 三段更像通用复盘框架，缺少真实设备、Android 版本、Perfetto 截图或匿名化 TTID / TTFD 数据，案例证据链不足。
- **建议**：Task 2B 补至少 1 个完整启动优化案例（设备与版本、启动口径、关键 trace 观察、改动列表、TTID / TTFD 或线上 A/B 结果、风险与回滚）；补不齐时，将“案例”表述降级为“复盘模板”。
- **review 日志**：logs/review/2026-05-13-05-review.md


## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-05-13
- **类型**：数据缺失
- **位置**：L124 / L378 预览卡顿阈值
- **问题**：30fps 预览“标准差超过 5ms 可感知”、单帧 40/50ms、低端 GPU 纹理上传 5-10ms 等阈值缺少设备、刷新率、预览分辨率、统计窗口和来源；这些数字会被读者当成通用判据。
- **建议**：补一组 Perfetto trace 样本或公开报告；至少把阈值改成“经验告警线”，并标明 30fps、设备档位、窗口长度、SurfaceView/TextureView 路径。

## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-05-13
- **类型**：数据缺失
- **位置**：L513 HAL3 管线延迟 / Binder IPC
- **问题**：`Binder IPC 虽然单次延迟只有 1-2ms` 缺少 trace 样本和系统负载边界；Camera metadata 大小、binder 线程池状态和厂商 HAL 进程负载都会改变该值。
- **建议**：用 `binder_driver` trace 给出同机样本，或者降级为“Binder IPC 通常不是主耗时，但在高负载/大 metadata/线程池拥塞时会放大”。

## [Task9 Deep Review] 18.2 Android View 标准管线（BLAST 深入） — 2026-05-13
- **类型**：版本差异
- **位置**：L155 / L208 Buffer release 回路
- **问题**：正文把槽位释放写成单一路径 `TransactionCompleted → releaseBufferCallbackLocked()`；android-16 `BLASTBufferQueue.cpp` 还包含 `BUFFER_RELEASE_CHANNEL` 条件路径，`waitForBufferRelease()` 可直接从 release channel 读 releaseFence 后调用 `releaseBufferCallback()`。
- **建议**：保留 TransactionCompleted 作为基础路径，同时补 Android 15/16 之后可能存在的 BufferReleaseChannel 快路径/条件编译边界，避免读者只按一种 trace 形态排查。

## [Task9 Deep Review] 18.2 Android View 标准管线（BLAST 深入） — 2026-05-13
- **类型**：数据缺失
- **位置**：L225-L239 Trace 正常耗时阈值
- **问题**：`Choreographer#doFrame <8ms`、`超过 16ms 必定掉帧`、`DrawFrame <8ms` 等阈值没有区分 60/90/120/144Hz、FrameTimeline deadline、SurfaceView/TextureView 和设备档位；“必定掉帧”也与后文 FrameTimeline 口径冲突。
- **建议**：改成按刷新率预算和 FrameTimeline deadline 判断，并把表格阈值标注为 60Hz 经验参考；高刷设备单独给 8.3ms/11.1ms 边界。

## [Task9 Deep Review] 19.21 Benchmark 应用 — 2026-05-13
- **类型**：版本差异/术语
- **位置**：L168-L173 Android Performance Class
- **问题**：正文示例写 `PC12、PC13、PC14、PC15`，但平台 API `Build.VERSION.MEDIA_PERFORMANCE_CLASS` 暴露的是 media performance class 的 API level 值（未声明时为 0），工程落库时应保留原始整数和 Android 版本映射。
- **建议**：改成 `media_performance_class=31/33/34/35/0` 这类可落库字段，再在展示层映射为 Android 12/13/14/15 Performance Class；补 Jetpack Core Performance 的兼容查询版本边界。

## [Task9 Deep Review] 19.21 Benchmark 应用 — 2026-05-13
- **类型**：数据缺失
- **位置**：L155-L176 机型分层方法
- **问题**：章节给出 CPU/GPU/存储/热稳定性维度，但没有示例 bucket 边界、工具版本、取值策略和线上 APM join 示例的真实字段定义；落地时仍缺“怎么分层”的可执行口径。
- **建议**：补一个匿名化设备字典样例：Geekbench/3DMark/CPDT 工具版本、分数区间、温度条件、bucket 规则，以及与启动 P95/慢帧率 join 后如何验证分层有效。


## [Task9 Deep Review] 1.5 线程模型 — 2026-05-13
- **类型**：原理链/诊断边界
- **位置**：L488-L490 RenderThread 延迟分析
- **问题**：只凭 RenderThread `DrawFrame` 超过一个 VSync 周期就判定“GPU 渲染是性能瓶颈”过粗；`DrawFrame` 可能包含 UI renderer CPU 工作、dequeue/wait fence、buffer 压力或 GPU 执行，单靠 slice 长度无法区分。
- **建议**：补 FrameTimeline missed reason、GPU counters / fence wait、SurfaceFlinger/BufferQueue 观察点；改成“RenderThread/GPU 路径成为候选瓶颈，需要继续拆分”。

## [Task9 Deep Review] 20.4 ANR 治理策略 — 2026-05-13
- **类型**：数据缺失
- **位置**：L586 系统负载 ANR 过滤阈值
- **问题**：`CPU iowait > 30%` 被写成过滤特征，但缺设备档位、采样窗口、内核统计口径和来源；容易被线上策略直接照搬。
- **建议**：补一组真实 ANR 样本的 iowait 分布和采样方法；补不到时改为“iowait 异常升高”并标注为经验信号，不给固定阈值。

## [Task9 Deep Review] 22.1 布局优化策略 — 2026-05-13
- **类型**：数据缺失/版本边界
- **位置**：L105 ConstraintLayout 2017 benchmark
- **问题**：40% 平均耗时下降来自 2017 年 support ConstraintLayout 示例，章节适用 Android 10-16 / AndroidX ConstraintLayout 2.x；现文已提醒不能当固定收益，但缺新版本复现实验或边界说明。
- **建议**：补 AndroidX ConstraintLayout 2.x + Macrobenchmark / FrameMetrics 复测条件；补不到时把该数据明确标为“历史官方样例”，正文结论以同机 trace 实测为准。
- **review 日志**：logs/deep-review/2026-05-13-06-deep-review.md

## [Task14 参考书扫描] 21.1 启动全链路分析 — 2026-05-13
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **建议补充**：冷热端分离的 LruCache 方案——将单一 LruCache 拆分为热端（按使用频率排序）和冷端（LRU），在低容量缓存场景下提升命中率。具体场景：聊天 App 会话页图片缓存被公众号图片冲刷导致命中率下降。AIW 已引用此参考书但未展开冷热端分离的具体实现逻辑。
- **参考书覆盖深度**：中等（含思路和流程图，无完整代码）

## [Task9 Deep Review] 21.3 ContentProvider 启动治理 — 2026-05-13
- **类型**：源码准确性/进程语义
- **位置**：L102 `跨进程唤醒`
- **问题**：表格容易被读者理解成主进程冷启动会自动安装并拉起所有独立进程 Provider。AOSP `handleBindApplication()` 安装的是当前进程的 provider；`android:process=":remote"` 的 Provider 只有在远程进程启动或主进程主动访问它时，才会由系统启动对应进程。
- **建议**：把“启动时拉起子进程”改成带条件表述：主进程 Provider 进入主进程冷启动关键路径；remote Provider 不随主进程自动安装，但被同步访问会触发远程进程启动和跨进程等待。诊断项保留 `ps` / Perfetto process track。

## [Task9 Deep Review] 22.6 图片加载与显示优化 — 2026-05-13
- **类型**：源码准确性/版本差异
- **位置**：L136-L169 `inSampleSize` 与 `inBitmap`
- **问题**：`inSampleSize` 未说明非 2 的幂会向下取整到最近 2 的幂；`inBitmap` 未补 API 19+ reusable allocationByteCount 约束。
- **建议**：补官方规则：`inSampleSize=3` 实际按 2 处理；API 19+ 复用要求解码后 byte count 不超过 `getAllocationByteCount()`，API 19 前约束更严。

## [Task9 Deep Review] 22.6 图片加载与显示优化 — 2026-05-13
- **类型**：API 版本差异
- **位置**：L197-L200 `BitmapRegionDecoder.newInstance()`
- **问题**：只写“API 31 起部分入口 deprecated”，没有列出弃用的是带 `boolean isShareable` 的重载。
- **建议**：明确 `newInstance(String, boolean)`、`newInstance(byte[], int, int, boolean)`、`newInstance(InputStream, boolean)` 在 API 31 弃用，替换为不带 `isShareable` 的重载。

## [Task9 Deep Review] 22.6 图片加载与显示优化 — 2026-05-13
- **类型**：数据精度/版本口径
- **位置**：L95-L113 框架对比与像素内存示例
- **问题**：Glide/Coil 对比未标注版本基准；4000×3000 对 1000×750 的像素比值是 16 倍，正文写“15 倍以上”。
- **建议**：标明基于 Glide 4.x / Coil 3.x；像素内存例子直接写 16 倍。

## [Task9 Deep Review] 22.7 WebView 性能优化实战 — 2026-05-13
- **类型**：源码准确性
- **位置**：L163-L167 `WebViewWarmup.release()` 与 L431-L443 `destroyWebView()`
- **问题**：`WebView.destroy()` 必须在创建 WebView 的线程调用；`release()` 未标注 MainThread 约束。`loadUrl("about:blank")` 后立即 `clearHistory()` 也不能保证异步 blank 导航完成后历史完全为空。
- **建议**：在 `release()` 内加主线程检查或 `Handler.post`；在清理顺序旁说明 `about:blank` 异步导航的历史栈边界。

## [Task9 Deep Review] 22.7 WebView 性能优化实战 — 2026-05-13
- **类型**：源码准确性/原理精度
- **位置**：L176-L189 `WebSettings.getDefaultUserAgent()` 预热
- **问题**：“只能提前触发一部分 provider 初始化”描述偏模糊；AOSP 路径是触发 WebViewFactory/provider 加载与 native library 初始化，但不创建 WebView/AwContents/renderer/compositor。
- **建议**：把预热边界写成“provider + native library 可提前，renderer 与页面资源不可提前”。

## [Task9 Deep Review] 22.7 WebView 性能优化实战 — 2026-05-13
- **类型**：工程边界
- **位置**：L276-L296 `shouldInterceptRequest()` 示例
- **问题**：main frame 默认进入 offlineStore 查找，但代码未显式展示可信域名/manifest 白名单；读者可能误把主文档和子资源拦截边界混在一起。
- **建议**：补注释：main frame 仅限离线包 manifest 命中的受控 URL；子资源也要走 allowlist，校验失败立即返回 null 走网络兜底。

## [Task9 Deep Review] 22.8 帧率监控与线上卡顿治理 — 2026-05-13
- **类型**：数据口径
- **位置**：L315-L330 `jank_count` / `frozen_count` / `frozen_frame_rate`
- **问题**：`frozen_count` 与 `frozen_frame_rate` 未定义阈值来源，容易和 Android Vitals 的 frozen frame（通常以 >700ms 为口径）或业务自定义严重卡顿口径混用。
- **建议**：明确每个计数字段的判定来源：JankStats `isJank`、FrameMetrics/JankStats overrun、Android Vitals frozen frame 阈值或业务阈值；服务端聚合时保留 `metric_source` / `threshold_ms`。

## [Task9 Deep Review] 22.8 帧率监控与线上卡顿治理 — 2026-05-13
- **类型**：版本差异/采集边界
- **位置**：L110-L161 `FrameCadenceSampler` 刷新率预算
- **问题**：示例把 `displayRefreshHz` 固定在构造参数中；Android 11+ 高刷和 Android 12+ 动态刷新率设备可能在页面生命周期内切换刷新率，固定预算会放大误报或漏报。
- **建议**：补充动态刷新率处理：采集窗口记录当前 display mode/refresh rate，监听 DisplayManager 变化，或优先使用 JankStats / FrameMetrics deadline、overrun 口径。


## [Task6 Review] 22.9 渲染优化案例集 — 2026-05-13
- **类型**：需补充素材（L3 内容深度 / L4 活人感）
- **位置**：全文案例内容，尤其是「列表滑动卡顿优化实战」「Compose 迁移性能踩坑」「复杂页面渲染优化」三节
- **问题**：章节标题和锚点都指向案例/实战，但正文主要是排查框架、指标口径和模板，缺少至少一个真实案例的设备环境、复现路径、优化前后指标、Perfetto/JankStats/Macrobenchmark 证据与改动代价。读者能获得排查清单，但还看不到可复查的现场过程。
- **建议**：Task2B 补 1-2 个真实或脱敏案例：场景与设备刷新率、复现步骤、慢帧/P95/P99/frozen frame 基线、关键 trace slice、改动前后对比和边界代价；没有一手数据时保留模板定位，章节标题或段落明确为“案例复盘模板/排查框架”。
- **review 日志**：logs/review/2026-05-13-15-review.md

## [Task9 Deep Review] 11.3 系统级功耗优化 — 2026-05-13
- **类型**：数据缺失
- **位置**：L389-L423 厂商后台冻结与功耗报告差异
- **问题**：MIUI/HyperOS 后台冻结“通常 10 分钟左右”、不同厂商电池消耗报告“3-5 倍”等量化口径来自公开经验汇总，当前缺少 ROM 版本、设备、复现条件或 trace/dumpsys 证据。
- **建议**：补 dontkillmyapp/OEM 文档链接、机型与 ROM 版本，或用一次 WorkManager 延迟实验标出 trace、dumpsys jobscheduler/alarm 与电池策略设置；无法复核时把固定数值降为经验范围并标注 [待验证]。

## [Task9 Deep Review] 13.2 Trace 抓取 — 2026-05-13
- **类型**：采集开销/数据口径
- **位置**：L763 CPU Callstack Sampling 采样频率
- **问题**：正文把 100-1000 Hz 作为多数场景合理范围。Perfetto CPU profiling 文档提示非 native 调用栈 unwind 成本高，建议低于 200 Hz per CPU；1000 Hz 容易带来 unwinder 过载、丢样和目标进程扰动。
- **建议**：将默认建议收敛为 100 Hz 起步，Java/JIT 混合栈保持 <200 Hz；native-only/短窗口实验再谨慎升高，并要求记录 dropped samples/overhead。


## [Task6 Review] 22.3 Jetpack Compose 性能优化 — 2026-05-13
- **类型**：需补充素材
- **位置**：Compose 编译器报告与性能诊断 / 结尾自动发现段
- **问题**：章节仍缺 Android Studio Compose Profiler 的官方入口和使用边界说明；结尾“后台文本布局预热”自动发现项缺少官方文档或 release notes 来源。
- **建议**：由 Task2B 补齐官方文档、release notes 或 Android Studio 工具说明；涉及版本/API 口径的部分交 Task9 复核。
- **review 日志**：logs/review/2026-05-13-16-review.md

## [Task9 Deep Review] 18.10 SurfaceControl API 深入 — 2026-05-13
- **类型**：交叉引用错误
- **位置**：L699-L701 交叉引用
- **问题**：BufferQueue / SurfaceFlinger / Sync Fence 三个相对链接指向当前 ch18 目录，实际文件在 src/part1-fundamentals/ch02-rendering/ 下。当前 Markdown 链接不可跳转。
- **建议**：把链接修为 ../../part1-fundamentals/ch02-rendering/13-buffer-queue.md、06-surfaceflinger.md、16-sync-fence.md。


## [Task9 Deep Review] 18.10 SurfaceControl API 深入 — 2026-05-13
- **类型**：原理链/示例边界
- **位置**：L329-L345 chooseFrameTimeline()
- **问题**：当 desiredPresentTimeNanos 晚于所有 candidate timeline 时，示例 fallback 到 preferred index，会把低帧率/主动延后场景重新绑回较早 timeline；这和前文“选择 expectedPresentTime 不早于目标时间”的规则不一致。
- **建议**：fallback 改成最后一个 candidate，或明确“超过候选范围时不绑定 frameTimeline，仅保留 setDesiredPresentTime/等待下一次 vsync callback”的策略。

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-05-13
- **类型**：源码精度/版本口径
- **位置**：进程重要性表 `perceptible / foreground service` 行
- **问题**：短前台服务被概括为“perceptible medium 区间”，但 Android 16 `OomAdjuster` 实际使用 `PERCEPTIBLE_MEDIUM_APP_ADJ + 1`；最近从 top 转入 FGS 的宽限期还会使用 `PERCEPTIBLE_RECENT_FOREGROUND_APP_ADJ + 1`。
- **建议**：表格或脚注补齐 regular FGS=200、short FGS=226、recent short FGS=51 的分支口径，并说明具体值仍以设备源码/分支为准。

## [Task9 Deep Review] 1.4 Binder IPC 机制与性能影响 — 2026-05-13
- **类型**：API 语义/版本口径
- **位置**：L426 `RemoteCallbackList` `FrozenCalleePolicy`
- **问题**：正文写成“自动丢弃高频数据回调”过窄。API 36 文档定义的是 callback recipient 进程被冻结时的策略：`DROP`、`ENQUEUE_ALL`、`ENQUEUE_MOST_RECENT`、`UNSET`，是否丢弃取决于构建 RemoteCallbackList 时选择的 policy。
- **建议**：改成“允许服务端为 frozen callback recipient 配置丢弃、全量排队或仅保留最近一次回调”，并补充 `maxQueueSize` / executor 的使用边界。

## [Task9 Deep Review] 3.4 输入延迟与预测输入技术 — 2026-05-13
- **类型**：数据缺失/可复现性
- **位置**：L267-L303 Perfetto 输入延迟量化
- **问题**：章节给出了 `android_input_events` 查询，但缺少最小 trace 配置与字段非空条件，读者可能把采集不足导致的空字段误判成没有延迟。
- **建议**：补充 Perfetto 采集清单（至少覆盖 `android.input.inputevent` 与 FrameTimeline/graphics 相关数据源），并说明 `end_to_end_latency_dur` 非空依赖 input event 与 frame event 关联。


## [Task6 Review] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-05-13
- **类型**：需确认 / 技术风险交接
- **位置**：`allocate2()` / `AHardwareBuffer_allocateWithOptions()`、libdmabufheap 池化、Binder FDA 收益
- **问题**：Task9 已将该章节列为 needs-rework（P0 1 / P1 3）。Task6 本轮只完成 L1/L2 小修，不裁决这些源码/API/版本差异；当前仍不满足发布条件。
- **建议**：优先处理 queue.json 中 `task9-2.15-gralloc-api-and-dmabuf-unsupported-claims`，修复后再进入 Task6 / Task9 复核。
- **review 日志**：logs/review/2026-05-13-20-review.md

## [Task9 Deep Review] 19.27 千万级 DAU 的 APM 端侧架构 — 2026-05-13
- **类型**：原理链/示例边界
- **位置**：L132-L155 `ApmRecorder` queue 示例
- **问题**：正文说“有界 RingBuffer / 无锁队列”，代码只注入 `Channel<ApmEvent>`，未展示 capacity、overflow 策略或实际 MPSC RingBuffer。`trySend()` 是否失败、是否有界，取决于调用方构造方式。
- **建议**：示例改成显式有界 `Channel(capacity = N, onBufferOverflow = DROP_OLDEST/DROP_LATEST)` 或自定义 MPSC RingBuffer，并说明入口 O(1)、失败只记 dropped counter。

## [Task9 Deep Review] 19.27 千万级 DAU 的 APM 端侧架构 — 2026-05-13
- **类型**：数据缺失
- **位置**：L173-L188 JSON / Protobuf Lite / FlatBuffers 协议对比
- **问题**：二进制协议节省 CPU、降低 GC、压缩网络流量的判断缺少字段规模、事件频率、设备、payload 大小、序列化耗时或分配量对比。
- **建议**：补一个 1k/10k 事件 benchmark，记录 payload bytes、encode/decode time、alloc bytes、GC 次数；没有数据时收窄为定性判断。


## [Task6 Review] 2.19 刷新率切换与帧率适配性能 — 2026-05-13
- **类型**：需确认 / 技术风险交接
- **位置**：`HWC 4.0 预判式切换（Android 16）`、`VsyncModulator 原子化相位切换（Android 16）`、`精确 fps 请求、category 请求和 range 请求怎么选`
- **问题**：Task9 已将本节列为 needs-rework：`expectedPresentTime` 版本与源码锚点、`VsyncModulator` 原子化声明、`Surface.FrameRateParams` / `setFrameRate(FrameRateParams)` FlaggedApi 边界仍需修正。Task6 本轮只补 `[存疑]` 标注和 L1/L2 小修，不裁决技术真伪。
- **建议**：Task2B 优先处理 queue.json 中 `task9-20260513-2.19-hwc-vsyncmodulator-version-errors`，修复后再进入 Task6 / Task9 复核。
- **review 日志**：logs/review/2026-05-13-22-review.md
## [Task9 Deep Review] 20.5 OOM 治理 — 2026-05-13
- **类型**：交叉引用/资源分类
- **位置**：L246-L254 FD 消耗者表
- **问题**：表格把“Binder 连接”放在 Socket 类 FD 示例中；Binder IPC 不是 socket 连接模型，普通 Binder 调用不会为每个连接消耗 socket FD，容易把 FD 泄漏排查方向带偏。
- **建议**：改成“Binder 驱动设备 FD / Binder 对象句柄与 socket FD 分开”；Socket 类只保留网络连接、Unix domain socket 等真实 socket。

## [Task9 Deep Review] 23.1 内存泄漏检测与治理 — 2026-05-13
- **类型**：交叉引用一致性
- **位置**：frontmatter related_chapters 与 L77 LeakCanary 章节引用
- **问题**：项目中 LeakCanary 章节的 section 是 `19.05`，正文和 frontmatter 写成 `19.5`；自动目录或章节索引可能匹配不到。
- **建议**：统一改为 `19.05`，并在相关章节清单中保持和 ch19 文件 frontmatter 一致。

## [Task9 Deep Review] 5.4 DVFS 与功耗管理 — 2026-05-13
- **类型**：数据缺失/待验证项
- **位置**：L150-L158 4GHz 限频收益、L365 升频延迟 Trace、L511-L513 内存频率观察
- **问题**：章节保留了多处 `[待验证]` / `[待补充]`：4GHz 限频收益缺设备和 workload，升频延迟缺 Perfetto 片段，LPDDR/DDR 调频缺可观测方法。
- **建议**：补设备型号、内核版本、频率上限、workload、功耗采样方式和 Perfetto trace；内存频率若无通用 Perfetto 数据源，应明确依赖 vendor/devfreq/debugfs 节点，不要写成通用能力。

## [Task9 Deep Review] 21.5 Splash Screen 与感知启动速度 — 2026-05-14
- **类型**：版本差异 / 依赖版本
- **位置**：SplashScreen API 适配 / 添加依赖（L139-L144）
- **问题**：正文示例仍写 `androidx.core:core-splashscreen:1.2.0-alpha02`，并建议生产使用 `1.0.1`。Google Maven metadata 显示 `core-splashscreen` 最新稳定版已为 `1.2.0`（2025-11-05 release），2026-05 的稿件不应默认推荐 alpha 或旧稳定版。
- **建议**：改成“当前稳定版以 Google Maven metadata / AndroidX release notes 为准；截至 2026-05 可使用 1.2.0，历史项目如锁 1.0.1 需说明原因”。

## [Task9 Deep Review] 21.7 多进程启动优化 — 2026-05-14
- **类型**：源码准确性 / 引用路径
- **位置**：跨进程初始化依赖管理 / `MODE_MULTI_PROCESS` 段落（L134）
- **问题**：`MODE_MULTI_PROCESS` 废弃结论成立，但主证据写成 Application 文档不够精确；官方主路径应是 `Context#MODE_MULTI_PROCESS`，另用 `SharedPreferences` API reference 的“does not support use across multiple processes”作补充。
- **建议**：把 `[已验证]` 来源改成 `developer.android.com/reference/android/content/Context#MODE_MULTI_PROCESS` + `developer.android.com/reference/android/content/SharedPreferences`。

## [Task9 Deep Review] 21.8 启动监控与度量 — 2026-05-14
- **类型**：版本差异 / API 细节补全
- **位置**：Android 15+ 的平台启动信息 / `ApplicationStartInfo` 段落（L216-L218）
- **问题**：正文高层描述正确，但仍停留在“需确认”；缺少 API 35、获取入口和 timestamp 常量，Task2B 修复时容易只删标注不补证据。
- **建议**：补 `ActivityManager.getHistoricalProcessStartReasons()` / `addApplicationStartInfoCompletionListener()`，以及 `START_TIMESTAMP_FORK`、`BIND_APPLICATION`、`APPLICATION_ONCREATE`、`FIRST_FRAME`、`FULLY_DRAWN` 等关键时间戳；说明时间戳是 monotonic nanoseconds。

## [Task9 Deep Review] 23.3 Native 内存管理与优化 — 2026-05-14
- **类型**：源码引用准确性 / 锚点补充
- **位置**：L83 `dumpsys meminfo` VMA 分类源码引用
- **问题**：正文把 VMA 名称分类锚到 `frameworks/base/core/jni/android_os_Debug.cpp`；该文件只调用 `ExtractAndroidHeapStats()`，具体 `[heap]` / `[anon:libc_malloc]` / `[anon:scudo:*]` / `[anon:GWP-ASan*]` 与 `.so/.jar/.apk` 分类在 `system/memory/libmeminfo/androidprocheaps.cpp`。
- **建议**：保留 `android_os_Debug.cpp` 作为 JNI 入口，同时补 `system/memory/libmeminfo/androidprocheaps.cpp` 作为分类规则源码锚点。



## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-14
- **类型**：原理链 / 指标归属
- **位置**：L134 RenderThread 流程步骤
- **问题**：正文写“RenderThread 完成后通过 `FrameMetrics` 或 `FrameTimeline` 通知帧完成”。`FrameMetrics` 是 per-window 指标回调，`FrameTimeline` 是 Choreographer / SurfaceFlinger 关联 expected/actual timeline 的观测框架，不是 RenderThread 的帧完成通知通道。
- **建议**：改成“RenderThread 完成 DisplayList 回放和 buffer 提交；帧耗时随后可通过 FrameMetrics（App 侧）或 FrameTimeline/Perfetto（系统侧）观察”。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-14
- **类型**：版本差异 / 交叉一致性
- **位置**：L518 总结句 BLASTBufferQueue 版本线
- **问题**：正文前文和 FAQ 已写 BLAST 主窗口迁移从 Android 11 开始、Android 12 扩展到更多 Surface 类型，但总结句又写“`BLASTBufferQueue` 从 Android 12 开始取代 `BufferQueue`”。同一章节内版本线不一致。
- **建议**：统一为“Android 11 主窗口开始迁移到 BLASTBufferQueue，Android 12 扩展覆盖范围并完善 FrameTimeline/VSyncId 观测”。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-05-14
- **类型**：数据缺失 / 主题边界
- **位置**：L445 16KB Page Size 行
- **问题**：“TLB 命中率提升约 9%，渲染管线有效带宽增益”缺少设备、benchmark、workload 和来源；该行也偏内存/系统页大小主题，不属于渲染机制版本演进主线。
- **建议**：删除该行，或移到内存/系统版本演进章节，并补来源、测试条件、指标定义和是否为通用结论。

## [Task9 Deep Review] 22.4 自定义 View 性能优化 — 2026-05-14
- **类型**：源码准确性 / API 版本
- **位置**：L159 `canvas.save()` / `restore()` 分配点表
- **问题**：`canvas.save()` / `restore()` 的嵌套成本主要是 Canvas native 状态栈和绘制状态管理，不应写成 Java 对象分配来源；“改用 `save()/restore()` 的指定 flag 版本”也不适合现代 API，`save(int flags)` 相关 save flags 在 API 26 后已被废弃/弱化。
- **建议**：把该项从“对象分配”表移到“绘制状态栈成本”或删除；建议使用最小必要的 `save()` / `restore()` 范围，避免推荐 flags 版本。

## [Task9 Deep Review] 22.4 自定义 View 性能优化 — 2026-05-14
- **类型**：API 语义边界
- **位置**：L195-L204 `setLayerType()` 小节
- **问题**：“`setLayerType()` 控制的是 View 的缓存策略，不是硬件加速的开关”表述过绝对。`LAYER_TYPE_SOFTWARE` 本身就是 View 级软件渲染 fallback，会绕开该 View 的硬件绘制路径；`LAYER_TYPE_HARDWARE` 则是硬件 layer 缓存策略。
- **建议**：改成“`setLayerType()` 不是全局硬件加速开关；它在单个 View 维度选择无 layer / hardware layer / software layer，其中 software layer 可作为局部关闭硬件绘制的 fallback”。


## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-05-14
- **类型**：观测方法 / 数据支撑
- **位置**：L79、L277、L325（Perfetto / AGI 中 Vertex、Fragment 阶段判断）
- **问题**：正文把“Perfetto 中可看到顶点处理时间”“Fragment Shader 超过 60% / Vertex 超过 50% 即可判定瓶颈”写得过确定。Perfetto 是否有 `gpu.renderstages`、阶段粒度和 counter 语义取决于 GPU producer / vendor；AGI 阈值也不能脱离 workload 固化成统一线。
- **建议**：改成启发式诊断流程：先确认设备是否暴露 render stages / counters，再用 AGI 或厂商 profiler 结合 draw call、overdraw、纹理采样和带宽 counter 交叉判断；阈值只作为示例，并标注测试条件。

## [Task9 Deep Review] 2.14 图形 API 演进与选择策略 — 2026-05-14
- **类型**：原理链边界
- **位置**：L197-L199（Command Buffer 复用与静态 UI）
- **问题**：正文把 Vulkan Command Buffer 复用直接套到 Android View 静态 UI，并写成“静态 UI 的帧提交开销几乎为零”。这对 app 自管 Vulkan 渲染在特定 swapchain / framebuffer 条件下才可能成立，不能代表 HWUI / SkiaVulkan 的 View 渲染路径。
- **建议**：限定为“应用自管 Vulkan workload 可在内容和 framebuffer 依赖稳定时复用 command buffer”；Android View 静态内容应回到 RenderNode DisplayList / damage / Skia backend 机制解释。

## [Task9 Deep Review] 5.9 ADPF 自适应性能框架 — 2026-05-14
- **类型**：数据缺失
- **位置**：L549-L557 “2026 旗舰机 Hint 响应延迟对照”
- **问题**：表格给出小米 17 Ultra / Pixel 10 / 三星 S26 Ultra 的 ADPF Hint → 频率生效延迟，但只有 `[待验证]`，缺测试固件、Perfetto/频点观测方法、样本数和 workload 条件。
- **建议**：补实测 trace、机型固件版本、采样方法和统计口径；补不齐时降级为“需实测的对比维度”，不要保留具体毫秒数。

## [Task9 Deep Review] 23.7 内存监控与线上治理 — 2026-05-14
- **类型**：版本差异 / 源码准确性
- **位置**：L90-L92 RSS 采集入口
- **问题**：`Debug.getRss()` 官方文档标注 Added in API level 35，而章节适用范围是 Android 10-16；当前表格未在采集入口处标出 API 35+ 边界。
- **建议**：在表格中标注 `Debug.getRss()` 仅适用于 API 35+；Android 10-14 的线上兼容路径优先使用 `/proc/self/status` 的 `VmRSS` 或既有 PSS/Debug.MemoryInfo 口径。

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-14
- **类型**：源码准确性
- **位置**：L174 LargeObjectSpace 实现选择
- **问题**：FreeList / Map 选择写成“arm64 vs 非 arm64”过窄；AOSP 默认由 `USE_ART_LOW_4G_ALLOCATOR` 决定。
- **建议**：按宏/架构条件说明，避免把所有 arm64/非 arm64 设备简单二分。

## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-14
- **类型**：数据缺失
- **位置**：L251-L253、L379 CC/TLAB 性能数字
- **问题**：32%、85%、70%、18 倍等数字缺设备、版本、负载和原始来源。
- **建议**：补官方原文或一手 benchmark；补不到则改为定性描述并保留版本边界。

## [Task9 Deep Review] 4.5 App 内存优化 — 2026-05-14
- **类型**：数据缺失
- **位置**：L197、L605、L830 等量化断言
- **问题**：3ms GC 准则、掉帧率 3-5 倍、ASan 2-5 倍、16KB Bitmap 页浪费均缺设备/负载/采样方法。
- **建议**：补一手 benchmark 或降级为定性描述。

## [Task9 Deep Review] 4.5 App 内存优化 — 2026-05-14
- **类型**：源码准确性
- **位置**：L340-L346 Glide/Coil/Fresco 对比
- **问题**：Coil “Bitmap Pool=基于 Coroutine”、Glide 默认池大小等表述需官方文档或源码复核。
- **建议**：保留可核实能力，删除未核实实现细节。

## [Task9 Deep Review] 4.5 App 内存优化 — 2026-05-14
- **类型**：知识盲区
- **位置**：L869-L876 ApplicationStartInfo
- **问题**：Android 17 `ApplicationStartInfo` 峰值内存相关能力已标 `[待验证]`，发布前不宜留在正文主路径。
- **建议**：移入 research gap 或补官方 API 37 文档。

## [Task9 Deep Review] 20.6 稳定性度量与指标体系 — 2026-05-14
- **类型**：源码/系统行为
- **位置**：L231-L233 Native Crash 采集
- **问题**：“信号处理器上报 tombstone”容易混淆系统 debuggerd tombstone 与 App 侧 minidump/handler。
- **建议**：改成“系统 tombstone + ApplicationExitInfo / 自建 minidump”两类来源。

## [Task9 Deep Review] 20.6 稳定性度量与指标体系 — 2026-05-14
- **类型**：交叉引用
- **位置**：L145 详见 26.1
- **问题**：26.1 当前仍是 draft/空壳，不适合作为可读延伸章节。
- **建议**：改指向已成稿的 15.3 或删除该引用。

## [Task6 Review] 23.8 内存优化案例集 — 2026-05-14
- **类型**：需补充素材 / 内容深度 / 活人感
- **位置**：全文，尤其是“为什么要看内存优化案例”与三类案例小节
- **问题**：章节目前以排查模板、治理口径和复盘字段为主，缺少可脱敏真实案例的修复前后数据、Heap Dump / heapprofd 观察点或线上 PSS 趋势。作为“案例集”，这会导致 L3 论据支撑不足，L4 作者在场感偏弱。
- **建议**：Task2B 补 1-2 个可脱敏案例：至少覆盖 Bitmap 大图、Native 泄漏或预算门禁中的一个；每个案例包含现象、指标、证据、根因、修复、验证和防复发字段。涉及技术真伪或版本口径的新增内容再交 Task9 复核。
- **review 日志**：logs/review/2026-05-14-06-review.md


## [Task9 Deep Review] 22.9 渲染优化案例集 — 2026-05-14
- **类型**：数据缺失/指标口径
- **位置**：L127-L133 `FrameTimingMetric` 验收表
- **问题**：当前只列 `frameDurationCpuMs` P95/P99，复杂列表与高刷场景更需要同时观察 deadline miss 口径；Macrobenchmark 的 `frameOverrunMs` 能直接表达帧相对 deadline 的提前/超时。
- **建议**：验收表补 `frameOverrunMs` P95/P99，说明正值表示错过 deadline，和 vitals 慢帧/frozen frame 口径分开使用。

## [Task9 Deep Review] 23.8 内存优化案例集 — 2026-05-14
- **类型**：交叉引用
- **位置**：L80、L195 指向 26.3
- **问题**：26.3 当前仍是 draft，作为“指标上报体系/完整监控设计”延伸阅读会把读者导向未完成章节。
- **建议**：发布前改指向已成稿的 23.7，或在 26.3 完成前删除该引用/标注“待成稿”。

## [Task9 Deep Review] 24.1 文件 I/O 优化 — 2026-05-14
- **类型**：源码准确性/版本标注
- **位置**：frontmatter `last_verified_against`、L85、L117-L119、L180
- **问题**：章节适用范围写 Android 10-16，但源码锚点标为 AOSP master；master 会随 Android 17+ 开发变化漂移，不能作为 Android 10-16 的稳定复核锚点。
- **建议**：将 SharedPreferencesImpl、QueuedWork、StrictMode、AtomicFile 的源码锚点 pin 到 `android-16.0.0_r1` 或明确的 tag；若保留 master 观察，正文标为 Android 17+ 待验证。

## [Task9 Deep Review] 24.1 文件 I/O 优化 — 2026-05-14（交叉引用）
- **类型**：交叉引用
- **位置**：L156 指向 24.2
- **问题**：24.2 当前仍是 draft，正文把“多表查询、分页、事务关系交给 Room/SQLite，见 24.2 节”写成可读延伸章节，发布态不成立。
- **建议**：24.2 成稿前删除“见 24.2 节”，或改为内部待补引用；发布前再恢复交叉链接。
## [Task14 参考书扫描] 23.2 Bitmap 与图片内存优化 — 2026-05-14
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]
- **建议补充**：ASM/Lancet 字节码插桩 Hook Bitmap.createBitmap 的实战方案，用于线上大图检测。ch23.2 已覆盖 Bitmap 内存计算和 inSampleSize，但缺少通过插桩拦截 Bitmap 创建进行阈值监控的具体实现代码。
- **参考书覆盖深度**：中等（有代码示例，但 Lancet 框架已较老）

## [Task14 参考书扫描] 25.6 APK 体积分析与瘦身 — 2026-05-14
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - so 文件的体积优化实战.md]
- **建议补充**：(1) gc-sections (-ffunction-sections -fdata-sections + -Wl,--gc-sections) 编译配置移除无用 Native 代码；(2) LTO 链接阶段优化 (-flto -O3)；(3) 去符号表(strip)可减少 so 体积 50%+，以及 -Wl,--exclude-libs,ALL 删除静态库引入的符号；(4) extractNativeLibs=true 开启 so 压缩的收益与代价（安装时间增加）；(5) 自定义 zstd/7z 压缩 + 运行时按需解压的完整方案（含 Lancet hook System.loadLibrary）
- **参考书覆盖深度**：深入（有完整代码示例和流程图）

## [Task14 参考书扫描] 25.6 APK 体积分析与瘦身 — 2026-05-14
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - so 文件的体积优化实战.md]
- **建议补充**：CPU 架构精简策略——仅需 arm64-v8a + armeabi-v7a，当 32 位设备占比 <1% 时可直接只保留 64 位 so。参考书提出了「精简/压缩/动态化」三种包体积优化方法论，可作为 ch25.6 的组织框架。
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] 5.1 Linux 进程调度基础 — 2026-05-14
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]
- **建议补充**：Process.setThreadPriority（Android API）vs Thread.setThreadPriority（Java API）的对比，推荐使用前者（后者有子线程时序 bug 可能误设主线程优先级）。ch5.1 已覆盖 nice/sched_setaffinity 原理，但缺少 API 选型的实践指导。
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 21.1 启动全链路分析（App 视角）— 2026-05-14
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]
- **建议补充**：(1) 启动时提升主线程优先级（Application.attach 中调用 Process.setThreadPriority(-19)）的实战方案；(2) 通过 /proc/pid/task 遍历找到 RenderThread tid 并提升其优先级的具体代码实现；(3) 提升核心线程优先级 + 降低非核心线程优先级的配合策略
- **参考书覆盖深度**：深入（有完整代码）

## [Task14 参考书扫描] 4.1 Android 内存模型全景 — 2026-05-14
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]
- **建议补充**：(1) Graphics 内存的三部分细分：Gfx dev（已映射到进程的 GPU 内存，高通芯片在 /dev/kgsl-3d0）、GL mtrack（纹理/顶点数据，未映射）、EGL mtrack（Layer Surface via gralloc，未映射）；(2) Android 10+ 对 /proc/pid/smaps 读取加了 5 分钟频控，线上监控需注意此限制；(3) 高通 GPU 内存节点 /d/kgsl/proc/pid/mem 的数据格式与用途
- **参考书覆盖深度**：深入（有源码分析和实际数据样本）

## [Task14 参考书扫描] 23.2 Bitmap 与图片内存优化 — 2026-05-14
- **类型**：版本更新
- **来源**：[结构参考: Clippings/Android 性能优化 - Native 内存优化（下）：Bitmap 的内存占用优化.md]
- **过时内容**：参考书使用 Gradle Transform API 进行 ASM 插桩，但 Gradle 7.0+ 已移除 Transform API，需改用 AndroidComponentsExtension
- **建议更新至**：Android 16/17 使用 ArtifactTransform / AsmClassVisitorFactory 替代 Transform API，或使用官方 Instrumentation API

## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-05-14
- **类型**：源码准确性/AndroidX 源码锚点
- **位置**：L258-L269 `WorkManagerImpl.createSchedulers()` 简化片段
- **问题**：正文用 `androidx/work/impl/WorkManagerImpl.java` 和 `createSchedulers()` 表达调度器选择，但未 pin AndroidX WorkManager 版本与真实源码路径；当前 WorkManager 调度器选择主要应落到 AndroidX `Schedulers` / `SystemJobScheduler` / `SystemAlarmScheduler` / `GreedyScheduler` 的具体版本实现上。
- **建议**：补 AndroidX WorkManager 2.10.x tag 的源码链接与真实方法名；如果只是概念化流程，代码块标为“示意”，避免读者按该类/方法去查源码。

## [Task9 Deep Review] 24.2 数据库性能优化（SQLite/Room） — 2026-05-14
- **类型**：源码准确性/版本标注
- **位置**：frontmatter `last_verified_against`、L89-L91 AOSP 源码锚点
- **问题**：章节适用范围写 Android 10-16，但源码锚点使用 “AOSP master snapshot 2026-05-14”。`SQLiteDatabase`、`SQLiteConnectionPool`、`SQLiteGlobal` 和 `config.xml` 都会随 master 漂移，不适合作为 Android 10-16 的稳定复核依据。
- **建议**：将源码锚点 pin 到 `android-16.0.0_r1` 或对应 release tag；若保留 master 观察，单独标为 Android 17+ 待验证。

## [Task9 Deep Review] 24.2 数据库性能优化（SQLite/Room） — 2026-05-14（WAL page size）
- **类型**：数据/版本边界
- **位置**：L122 WAL 检查项
- **问题**：“16KB page size 设备上，100 页 checkpoint 对应的数据量比 4KB page size 更大”容易把 Linux/设备页大小与 SQLite `PRAGMA page_size` 直接绑定。AOSP `SQLiteGlobal.getDefaultPageSize()` 从 `/data` block size 取默认值，最终数据库页大小仍应以实际库的 `PRAGMA page_size` 为准。
- **建议**：改成“如果该库的 `PRAGMA page_size` 为 16KB，则 100 页约 1.6MB；默认值需在目标设备/数据库上查询确认”，并给出 `PRAGMA page_size; PRAGMA wal_autocheckpoint;` 的验证命令。

## [Task6 Review] 2.9 渲染机制的版本演进 — 2026-05-14
- **类型**：需补充素材
- **位置**：版本演进时间线总览｜16KB 页行
- **问题**：时间线保留“TLB 命中率提升约 9%，渲染管线有效带宽增益”的数据化表述，但缺少设备、page size 配置、测试 workload、引用来源和适用边界。
- **建议**：Task2B 补来源和测试条件；补不齐时改成定性边界表述，再交 Task9 复核。
- **review 日志**：logs/review/2026-05-14-08-review.md


## [Task9 Deep Review] 22.3 Jetpack Compose 性能优化 — 2026-05-14
- **类型**：源码准确性/状态读取阶段
- **位置**：L125 `Modifier.onSizeChanged { }`
- **问题**：`onSizeChanged` 是尺寸变化回调，不是官方“延迟状态读取到 Layout phase”的典型入口；把它和 `Modifier.layout { }` 并列会误导读者在回调里读取状态。
- **建议**：改用官方示例口径：Layout 阶段列 `Modifier.offset { }` / `Modifier.layout { }` 等 lambda modifier；`onSizeChanged` 单独作为尺寸回调说明，不作为读状态优化入口。

## [Task9 Deep Review] 22.3 Jetpack Compose 性能优化 — 2026-05-14（derivedStateOf）
- **类型**：原理链/数据支撑
- **位置**：L158-L187
- **问题**：`derivedStateOf` 的官方约束是“昂贵，只在结果变化频率低于输入时使用”；正文新增“无内存分配，否则 SnapshotStateObserver 监听判断失准”缺少源码/官方依据，且容易被理解成硬性 API 契约。
- **建议**：保留“输入高频、输出低频、计算无副作用”的主线；将“避免在计算里创建大对象/复杂对象”降级为性能建议，并补 DerivedState.kt 或官方 side-effects 文档引用。

## [Task9 Deep Review] 22.3 Jetpack Compose 性能优化 — 2026-05-14（后台文本布局）
- **类型**：知识盲区/来源缺失
- **位置**：L450 自动发现段
- **问题**：“Compose 1.9 后台文本布局预热、无需开发者额外配置”当前只有待验证标注，未给 release notes、API 名称或默认启用条件。
- **建议**：补 Compose UI/Foundation release notes 或源码 flag；补不齐时删除该自动发现段，避免和 LazyLayout prefetch / text measurement 混在一起。

## [Task9 Deep Review] 24.3 序列化性能对比与选型 — 2026-05-14
- **类型**：数据/案例支撑
- **位置**：L105-L123 Moshi benchmark 示例
- **问题**：正文把示例称为 Moshi Codegen 基线，但代码没有展示 `@JsonClass(generateAdapter = true)`、KSP/kapt codegen 依赖或如何确认拿到 generated adapter；读者可能实际测到 reflection adapter。
- **建议**：补 `@JsonClass(generateAdapter = true)` 的模型片段、Gradle 依赖和 adapter 来源验证方式；或把示例标题改成“同 payload benchmark 骨架”。

## [Task9 Deep Review] 24.3 序列化性能对比与选型 — 2026-05-14（源码 tag）
- **类型**：源码准确性/版本标注
- **位置**：frontmatter `last_verified_against`、Parcel / TransactionTooLargeException 段
- **问题**：章节适用 Android 10-16，但 `last_verified_against` 写 AOSP master snapshot；`Parcel.java` 与 `TransactionTooLargeException.java` 应 pin 到稳定 release tag，避免 master 随 Android 17+ 开发漂移。
- **建议**：把源码锚点改成 `android-16.0.0_r1`；如保留 master 观察，单独标为 Android 17+ 待验证材料。

## [Task9 Deep Review] 22.5 动画性能优化 — 2026-05-14
- **类型**：数据缺失
- **位置**：L129 帧动画内存估算
- **问题**：正文写“30 张 1080p RGBA 图片接近 240MB”，并标注 `[待验证]`；该数字需要明确 1920×1080×4×30 的计算口径、MB/MiB 差异、Bitmap.Config 与采样策略边界。
- **建议**：补公式和单位；若按 MiB 表达应约 237MiB，按十进制 MB 约 249MB，并说明硬件位图、压缩包体积与解码后内存不是同一个指标。

## [Task9 Deep Review] 24.4 网络架构与连接管理 — 2026-05-14
- **类型**：源码准确性 / 原理链
- **位置**：L111 OkHttp 连接复用边界
- **问题**：正文把复用边界概括为 `Address`，只覆盖同 host 基本复用；OkHttp HTTP/2 还存在 connection coalescing：非 host 配置相同、HTTP/2、路由 IP 匹配、证书覆盖新 host、HostnameVerifier / CertificatePinner 通过时，不同 hostname 也可能复用同一连接。
- **建议**：把“边界是 Address”改成“同 Address 是基本复用条件”，补充 HTTP/2 coalescing 的源码条件和安全边界；引用 `RealConnection.isEligible()` / `supportsUrl()`。

## [Task9 Deep Review] 24.5 网络协议优化（HTTP/2、HTTP/3、gRPC） — 2026-05-14
- **类型**：版本差异
- **位置**：frontmatter `applicable_versions` / `last_verified_against`，以及 L137-L146 HttpEngine / ConnectionMigrationOptions 段
- **问题**：章节适用范围写 Android 10-16，但源码锚点主要是 Android 35 SDK sources；HttpEngine / QUIC / ConnectionMigrationOptions 属于版本敏感 API，Android 16/API36 口径尚未在正文闭环。
- **建议**：若继续声明 Android 16，补 API36 / android-16.0.0_r1 对应文档或源码锚点；否则把源码验证口径明确限定为 Android 35，并说明 API34+ / S extensions 7 的运行时 guard。

## [Task9 Deep Review] 22.5 动画性能优化 — 2026-05-14（FrameTimeline 版本边界）
- **类型**：版本差异 / 观测口径
- **位置**：L150-L154、工程检查清单中的 `FrameTimeline`
- **问题**：章节适用 Android 10-16，但 `FrameTimeline` 主要对应 Android 12/API 31+ 的帧时间线观测；Android 10/11 设备上需要退回 `Choreographer#doFrame`、`SurfaceFlinger`/`gfx`、`sched`、`RenderThread DrawFrame` 等信号。
- **建议**：补充 Perfetto 观测口径的版本分支：API 31+ 看 FrameTimeline / Jank，API 29-30 用 UI Thread、RenderThread、SurfaceFlinger 和帧间隔推断卡顿。



## [Task9 Deep Review] 24.6 数据压缩与缓存策略 — 2026-05-14
- **类型**：源码准确性/版本边界
- **位置**：L86 OkHttp CompressionInterceptor / BrotliInterceptor 描述
- **问题**：正文没有固定 OkHttp 5.x 具体版本，把默认 `BridgeInterceptor` 的 gzip 透明解压、`okhttp-brotli` 的 Brotli 拦截器、`CompressionInterceptor` 的可配置算法列表和请求体压缩放在一起描述，容易让读者误以为请求/响应压缩都由同一个拦截器自动处理。
- **建议**：拆成三段：默认 OkHttp 只在未显式设置 `Accept-Encoding` 时透明处理 gzip；接入 `okhttp-brotli` 后再说明 br/gzip 协商，并标注核对的 OkHttp tag；请求体 `Content-Encoding` 压缩需业务自定义并确认服务端支持。

## [Task9 Deep Review] 2.0 渲染系统总纲 — 2026-05-14
- **类型**：版本差异/交叉引用
- **位置**：本章内容中 2.14、2.18、2.19 的 Android 16/17 能力摘要
- **问题**：总纲标注适用到 Android 17，但 `last_verified_against` 仍停在 AOSP android-16.0.0_r1；部分小节摘要使用“Vulkan 1.4 必选扩展”“ANGLE 强制化”“Android 15/16 ARR”等较新的版本判断，总纲没有说明这些判断来自对应子章节而非本节独立复核。
- **建议**：发布前与 2.14、2.18、2.19 的最终 Task9 结论同步一轮；总纲只写已被子章节验证的稳定结论，对 Android 17 仍在 DP/Beta 的行为标注来源或降级为“关注点”。

## [Task6 Review] 20.1 应用稳定性全景 — 2026-05-14
- **类型**：需确认
- **位置**：ANR 超时阈值表 / ANR 发生后的系统行为
- **问题**：BroadcastReceiver timeout 仍写成固定前台 10 秒 / 后台 60 秒，缺少 Android 14+ CPU-starved 场景 10-20 秒 / 60-120 秒口径；“向用户弹出应用无响应对话框”表述也缺少前台可见、后台 / silent ANR 的边界。
- **建议**：Task 2B 按 Task9 技术结论和官方文档补版本边界；无法确认时降级为“典型前台场景”，并标注设备 / 系统差异。
- **review 日志**：logs/review/2026-05-14-12-review.md

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-14
- **类型**：源码准确性
- **位置**：L138-L149 Manifest 声明
- **问题**：正文写 `android:appCategory="game"` 与 `game_mode_config.xml` “两者缺一不可”。`GameManager` reference 说明应用可用 `android:isGame="true"` 或 `android:appCategory="game"` 标识游戏；当前说法把 `appCategory` 写成唯一入口。
- **建议**：改成“现代工程推荐 `android:appCategory="game"`；旧路径/兼容口径还存在 `android:isGame="true"`，Game Mode XML 只负责声明支持/退出的模式”。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-05-14
- **类型**：数据缺失/技术断言过宽
- **位置**：L368、L382 Swappy/ARR 与 Vulkan GPU 瓶颈判断
- **问题**：`Swappy` 与 ARR 错位导致 16/33ms 周期跳变、以及“Vulkan 下 Draw Call 数量不再是 CPU 侧主要瓶颈”的判断都缺少设备、引擎、驱动、trace 片段或官方资料支撑；后者也过度绝对，Vulkan 仍可能在命令录制、提交、同步和资源管理上出现 CPU 瓶颈。
- **建议**：补一段真实 Perfetto/AGI 样例和适用边界；将 Vulkan 判断改为“相比 OpenGL ES 降低部分 driver overhead，但 CPU/GPU 瓶颈仍需按 command recording、queue submit、barrier、render pass 与 shader/带宽分别验证”。

## [Task9 Deep Review] 24.7 离线优先架构 — 2026-05-14
- **类型**：代码准确性
- **位置**：L100-L115、L126-L142、L177-L202 示例代码
- **问题**：`SyncStatus` 作为 Room 字段需要 enum TypeConverter 或可直接持久化的基础类型；`CoroutineWorker` 构造函数注入 `OfflineRepository` 需要 HiltWorker/自定义 WorkerFactory/DelegatingWorker，默认 WorkManager 不能直接实例化该构造函数。
- **建议**：在代码前标注“骨架代码”，并补一句生产接入边界：Room enum 用 TypeConverter，Worker 依赖通过 Hilt/WorkerFactory/DelegatingWorker 注入。

## [Task9 Deep Review] 24.7 离线优先架构 — 2026-05-14
- **类型**：知识盲区
- **位置**：L91-L96、L146-L164 数据模型与冲突处理
- **问题**：outbox/sync state 覆盖了新增和更新，但删除同步、tombstone、操作顺序、账号切换/登出后队列归属没有展开。这些是离线优先落地时最容易制造“幽灵数据”或跨账号污染的边界。
- **建议**：补充 `deletedAt`/tombstone、单对象 op sequence/server revision、accountId/tenantId、登录态失效后的队列冻结或迁移规则。

## [Task9 Deep Review] 24.7 离线优先架构 — 2026-05-14
- **类型**：数据缺失
- **位置**：L164 同步批量窗口 20-100 条
- **问题**：“20-100 条作为初始窗口”是可用经验值，但缺少 payload 大小、Room 事务耗时、低端机 I/O、服务端限流和失败率基线。
- **建议**：补最小验收指标：每批事务 P95、单批 payload 字节数、失败重试率、队列清空耗时；无法提供数据时改成“从小批量开始压测后调整”。

## [Task9 Deep Review] 25.1 功耗诊断与分析方法 — 2026-05-14
- **类型**：数据缺失/工具边界
- **位置**：L89-L91 / L115 Power Profiler 与 Macrobenchmark `PowerMetric`
- **问题**：表格把 power rail 峰值与 CI 守门写得偏直接，但 ODPM/PowerMetric 的 rail 数据是设备/子系统级能量，不是 App 级直接归因；官方 Macrobenchmark power metrics 也限制在 Pixel 6/Pixel 6 Pro 及后续支持设备。
- **建议**：补“power rail 只能做时间相关性，不能单独证明某段代码耗电；CI 守门需固定支持 ODPM 的实体设备、温度/电量/亮度条件，并用 `PowerMetric.deviceSupportsHighPrecisionTracking()` 或等价检查做能力判断”。

## [Task9 Deep Review] 25.1 功耗诊断与分析方法 — 2026-05-14
- **类型**：交叉引用
- **位置**：L162 / L168 / L203 指向 §25.2、§25.3、§25.5
- **问题**：正文把后台功耗、WakeLock/Alarm、定位治理交给 §25.2/§25.3/§25.5，但这些章节当前仍是 draft stub，只有 outline 和“待加工”。如果 25.1 先进入发布态，读者会跳到空章节。
- **建议**：在 25.1 发布前确认 25.2/25.3/25.5 已完成，或把这些引用临时降级为“后续章节将展开”，避免形成无内容交叉引用。

## [Task9 Deep Review] 25.4 WorkManager 实战与后台任务调度 — 2026-05-14（GreedyScheduler 约束路径）
- **类型**：源码准确性 / 原理链
- **位置**：L82-L84 `GreedyScheduler` 描述
- **问题**：正文只强调 `GreedyScheduler` 处理 unconstrained、non-timed work。AndroidX `androidx-main` 当前实现里，`GreedyScheduler.schedule()` 对已到运行时间、非 idle、非 content-uri trigger 的 constrained work 会启动 `WorkConstraintsTracker`；约束满足时 `startWork()`，约束失效时 `stopWorkWithReason()`。只写 unconstrained 会让读者在排查“进程还活着但有约束任务也被拉起/停止”时漏掉进程内约束跟踪路径。
- **建议**：保留源码注释口径，同时补实现分支：无约束 work 直接进程内启动；有普通约束的 work 由 `WorkConstraintsTracker` 跟踪；`requiresDeviceIdle()` 与 content-uri trigger 仍交给系统调度路径。

## [Task9 Deep Review] 25.4 WorkManager 实战与后台任务调度 — 2026-05-14（停止原因版本边界）
- **类型**：版本差异 / 观测口径
- **位置**：L197-L201 `WorkInfo.getStopReason()` / `JobParameters.getStopReason()`
- **问题**：正文把停止原因作为通用回归守门字段，但未写版本和库边界。WorkManager release notes 显示 `WorkInfo.getStopReason()` / Worker `getStopReason()` 是 WorkManager 2.9.0 起的重要变化；`JobParameters.getStopReason()` 在 Android 12/API 31 才成为公开 API。Android 10-11 设备或 WorkManager 低版本不能按同一方式采集。
- **建议**：补采集矩阵：WorkManager 2.9+ 读取 `WorkInfo.getStopReason()`；直接 JobScheduler 在 API 31+ 读取 `JobParameters.getStopReason()`；低版本用 Worker 结果、取消原因、运行时长、约束状态和日志事件做替代字段。

## [Task9 Deep Review] 25.4 WorkManager 实战与后台任务调度 — 2026-05-14（约束兼容性）
- **类型**：源码准确性 / 知识盲区
- **位置**：L86-L106 约束和退避策略说明
- **问题**：正文列出 `DeviceIdle`、多约束叠加和 backoff，但未说明 `requiresDeviceIdle()` 与 `setBackoffCriteria()` 不能同时设置。AndroidX `OneTimeWorkRequest.Builder.buildInternal()` 与 `PeriodicWorkRequest.Builder.buildInternal()` 都会在 `backoffCriteriaSet && constraints.requiresDeviceIdle()` 时抛出 `IllegalArgumentException("Cannot set backoff criteria on an idle mode job")`。这会影响读者把“空闲 + 退避”组合到同一个请求的实战代码。
- **建议**：在约束段补一条兼容性规则：idle 任务不要设置 backoff；如果需要失败退避，改用 charging/network/battery-not-low 等约束，或拆成 idle 触发的粗粒度任务与内部重试逻辑。



## [Task9 Deep Review] 1.0 第 1 章：系统架构全景 — 2026-05-14
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters` / L63、L65、L71
- **问题**：正文和 `last_verified_against` 已引用 `1.15`、`1.17`，但 frontmatter `related_chapters` 只列到 `1.16` 且漏掉 `1.15`、`1.17`。后续自动图谱或发布索引会把 JNI/NDK 与 IPC 全景从本章关联中丢掉。
- **建议**：把 `related_chapters` 补齐到 `1.1`-`1.17`，至少加入 `"1.15"` 和 `"1.17"`；同步核对 `src/SUMMARY.md`。

## [Task9 Deep Review] 1.0 第 1 章：系统架构全景 — 2026-05-14
- **类型**：数据/源码锚点
- **位置**：L38 Android 15/16 平台变化摘要
- **问题**：`Parallel Module Loading` 只在 README 总览中出现，当前 ch01 子章节没有对应展开或来源锚点；同句其他能力多数能跳到 `1.6`、`1.7`、`1.9`、`1.12`、`16.5` 等章节。
- **建议**：给 `Parallel Module Loading` 补官方 release note / AOSP 入口并在 `1.6` 或 `1.2` 展开；补不齐时从总览中删除或标为待验证关注点。

## [Task9 Deep Review] 25.5 定位与传感器功耗优化 — 2026-05-14
- **类型**：数据缺失/技术断言过宽
- **位置**：L128-L139 `setMaxUpdateDelayMillis(1h)` 批量定位示例
- **问题**：正文写“App 唤醒次数从 6 次降到 1 次”，但 Google Play services `LocationRequest.Builder#setMaxUpdateDelayMillis()` 文档只承诺“may save power by delivering locations in batches”，且 batching 支持会随硬件/设备实现变化。
- **建议**：把该数字改成“理想情况下最多从每小时 6 次降到 1 次”，并补 `dumpsys location`/回调日志/电量场景作为验证口径；不要把 batching 写成所有设备必然行为。

## [Task9 Deep Review] 25.5 定位与传感器功耗优化 — 2026-05-14
- **类型**：知识盲区
- **位置**：L94-L181 FLP / Geofencing / 被动定位
- **问题**：章节把 Fused Location Provider 作为主要实现，但 FLP 属于 Google Play services；AOSP-only、无 GMS、国内 OEM 或企业管控设备上可能需要平台 `LocationManager`、OEM 定位服务或业务降级策略。
- **建议**：补一段运行环境边界：有 GMS 时优先 FLP；无 GMS 时退回平台 `LocationManager`/OEM SDK，并明确 geofence、passive request、批量能力和耗电表现需要重新验证。

## [Task9 Deep Review] 25.5 定位与传感器功耗优化 — 2026-05-14（跨章节命名）
- **类型**：交叉引用一致性
- **位置**：25.5 L165-L177；25.2 L231、L239、L252
- **问题**：25.5 使用当前 Google Play services `Priority.PRIORITY_PASSIVE`，但 §25.2 仍使用旧口径 `PRIORITY_NO_POWER`。两节都在讲被动/机会主义定位，命名不一致会让读者误以为是两个策略。
- **建议**：统一到 `Priority.PRIORITY_PASSIVE`；如保留 `PRIORITY_NO_POWER`，明确标注为旧版 Google Play services / 旧 API 名称。

## [Task9 Deep Review] 1.0 第 1 章：系统架构全景 — 2026-05-14（Android 17 MessageQueue 边界）
- **类型**：版本差异/源码准确性
- **位置**：L38、L71 `ConcurrentMessageQueue` / DeliQueue 摘要
- **问题**：README 写“Android 17 已确认的平台行为包括 `ConcurrentMessageQueue` 无锁投递、DeliQueue 命令调度”，但入口页没有同步 §1.13 中的 targetSdk 37+ 默认启用边界；读者可能理解为所有 Android 17 上运行的 App 都自动进入新 MessageQueue 路径。
- **建议**：在摘要里补“面向 targetSdk 37+ 应用默认启用”的限定，并指向 §1.13 的版本/targetSdk 细节。

## [Task9 Deep Review] 25.8 App Bundle 与按需分发 — 2026-05-14
- **类型**：知识盲区/PAD 运行时边界
- **位置**：L207-L212 Play Asset Delivery 风险列表
- **问题**：PAD 风险只写弱网、版本一致性、磁盘占用和观测指标，缺少官方文档里的 asset pack 运行时边界：install-time asset pack 作为 split APK 分发；fast-follow/on-demand 作为 archive 展开到内部存储，App 不能假设文件长期存在或路径稳定，文件可能被用户删除或被 Play Asset Delivery Library 跨 session 移动，且应按只读资源处理。更新时 fast-follow/on-demand pack 还会被 invalidated，资源未就绪时要有“update in progress”兜底。
- **建议**：在 PAD 小节补一段“资源定位与更新状态机”：每次使用前通过 PAD API 查询 pack location/status；不要缓存绝对路径作为长期契约；对更新中、被清理、未下载、下载失败分别给 UI/降级路径；asset pack 内容不要作为可写业务缓存。

## [Task9 Deep Review] 25.9 功耗与包体积案例集 — 2026-05-14
- **类型**：交叉引用错误
- **位置**：L225 / frontmatter sources
- **问题**：正文以 `[已验证]` 引用了 `developer.android.com/topic/performance/vitals/wakeup`，但 frontmatter `sources` 未列出该官方来源，source-index 难以追踪 excessive wakeup alarm 依据。
- **建议**：在 sources 中补 `https://developer.android.com/topic/performance/vitals/wakeup`，或改成引用 §25.3 已覆盖的 AlarmManager 文档。
## [Task9 Deep Review] 26.1 App 可观测性架构设计 — 2026-05-15
- **类型**：交叉引用
- **位置**：L64、L175
- **问题**：正文把 26.2、26.4、26.5 写成后续可承接章节，但这三个文件当前仍是 draft；26.1 本轮会晋升发布态，发布后会指向未成稿章节。
- **建议**：发布前把这些引用标成“后续规划/待成稿”，或等 26.2、26.4、26.5 进入 ready-for-review 后再恢复正式交叉引用。

## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-05-15
- **类型**：源码准确性
- **位置**：L114-L130
- **问题**：自定义 Trace 示例直接把业务 trace name 传给 `Trace.beginSection(name)`，但 Android `Trace.beginSection()` 的 sectionName 上限是 127 Unicode code units，超长名称会触发 `IllegalArgumentException`；高基数字段也会污染 Perfetto 切片聚合。
- **建议**：在示例或说明中补充 trace section name 的 sanitize/truncate/hash 策略：限制长度、禁止动态 ID/URL/用户输入进入 sectionName，并把高基数字段放入 metrics attributes。

## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-05-15
- **类型**：数据缺失
- **位置**：L162
- **问题**：“P90 至少数百级样本、P99 通常需要更高样本量”是经验阈值，当前没有说明统计口径；不同分桶、分布形状、采样率和置信区间会让所需样本量差异很大。
- **建议**：把这句话标成工程经验，并补充最低样本量与置信度/误差范围的关系，或给出团队门禁示例：如 P90/P99 分别需要的窗口样本量、灰度比例、连续异常窗口数。

## [Task9 Deep Review] 26.3 性能指标采集与上报 — 2026-05-15
- **类型**：交叉引用
- **位置**：L209
- **问题**：小结指向 26.4、26.5，但这两个文件当前仍是 draft；如果 26.3 先通过 Task9，读者会被导向未完成章节。
- **建议**：在 26.4、26.5 成稿前，把引用改成“后续章节计划处理”，或暂时指向已 finalized 的 15.3/15.9 作为可读延伸。

## [Task9 Deep Review] 26.4 ANR 监控体系 — 2026-05-15
- **类型**：数据缺失
- **位置**：L149-L161 主线程卡顿监控阈值
- **问题**：100ms / 300ms / 700ms / 2s / 5s 阈值是可用工程策略，但正文没有给设备、业务场景或采样开销依据。
- **建议**：补一段“默认阈值是经验起点”的边界说明，给一组低端机 / 中高端机抓栈开销样例，或说明团队应按页面类型与设备分桶校准。

## [Task9 Deep Review] 19.13 androidx.tracing（Tracing SDK） — 2026-05-15
- **类型**：数据缺失
- **位置**：L152-L168 trace 调用开销表
- **问题**：表内“亚微秒级 / 百纳秒级 / 每帧 6-14μs”等数字缺少设备、Android 版本、trace enabled 配置、benchmark 方法和样本范围。
- **建议**：补充 microbenchmark 条件，或把数字降级为待复测量级；至少给出 `androidx.benchmark` 测试方法、设备型号、系统版本与 trace 配置。

## [Task9 Deep Review] 19.23 网络 APM 底层捕获原理 — 2026-05-15
- **类型**：指标口径
- **位置**：L432-L450 attempt / exchange 阶段表与 L281-L282 responseBodyEnd 示例
- **问题**：正文使用 `responseHeadersStart → responseBodyEnd` 表示 Response 接收，示例也未记录 `responseBodyStart`。OkHttp EventListener 提供 `responseBodyStart/End`，如果看大包下载或弱网下行，应把 header 接收和 body 接收分开。
- **建议**：增加 `responseBodyStartNs` 字段；`response_header_ms=responseHeadersStart→responseHeadersEnd`，`response_body_ms=responseBodyStart→responseBodyEnd`，看板上再按需要汇总为 response_receive_ms。

## [Task9 Deep Review] 20.1 应用稳定性全景 — 2026-05-15
- **类型**：数据缺失
- **位置**：L190-L200 行业实践中的度量维度
- **问题**：`Crash Rate 0.2%`、`Crash-Free Session Rate ≥99.5%`、`ANR Rate 0.1%`、`Native Crash Rate ≤0.05%`、`OOM ≤5%` 被写成行业/大厂门禁，但缺少来源、统计口径、采样窗口、前后台范围和适用业务规模。
- **建议**：补官方/厂商/团队一手基线；没有来源的数值降级为示例，并标注“按 DAU、会话定义、版本阶段和业务场景调整”。

## [Task9 Deep Review] 26.6 A/B Test 与性能回归防护 — 2026-05-15
- **类型**：数据缺失/统计边界
- **位置**：L85/L98/L100
- **问题**：正文已经提醒“边看边停会抬高误判概率”，但没有给出频繁看数、多分群、多护栏指标同时检查时的校正办法；性能实验上线后很容易每天看数并按设备、系统、国家多维拆分，假阳性会被放大。
- **建议**：补充预注册中途检查窗口、sequential testing / alpha spending，或至少要求多重比较校正/FDR 与连续异常窗口；A/A Test 除主指标无系统性差异外，也应检查关键分群的 SRM 和假阳性率。

## [Task6 Review] 26.6 A/B Test 与性能回归防护 — 2026-05-15
- **类型**：需补充素材
- **位置**：§性能 A/B Test 的设计与统计方法 / 样本量字段
- **问题**：样本量计算只列 `baseline_value`、`minimum_detectable_effect`、`alpha`、`power`，缺历史方差或完整分布、统计检验对象、allocation ratio 与关键分群最小样本量。
- **建议**：Task2B 结合 Task9 意见补统计模型边界；均值、比例、P90/P99 分开说明。
- **review 日志**：logs/review/2026-05-15-05-review.md

- **类型**：需确认
- **位置**：§性能回归自动检测 / Macrobenchmark 指标口径
- **问题**：适用范围覆盖 Android 10-16，但 `FrameTimingMetric.frameOverrunMs` 的 Android 12/API 31+ 边界未在正文写清。
- **建议**：Task2B/Task9 核对后补版本边界；Android 10/11 门禁口径补替代指标。
- **review 日志**：logs/review/2026-05-15-05-review.md

- **类型**：需确认
- **位置**：§性能劣化的自动归因 / 贡献度排序
- **问题**：`样本量 × P90 delta` 用于 P90/P99 分位值归因存在统计口径风险，当前文本容易误导读者。
- **建议**：Task2B/Task9 补可复核的尾部贡献算法，如阈值违约数、原始样本 counterfactual 或 bootstrap 口径。
- **review 日志**：logs/review/2026-05-15-05-review.md

## [Task9 Deep Review] 20.7 异常处理架构设计 — 2026-05-15
- **类型**：数据与指标口径
- **位置**：L160 Android Vitals 与 SafeMode 价值
- **问题**：SafeMode 对 Google Play Vitals user-perceived crash rate 的改善链路写得过直；该指标按 DAU 中至少一次前台 crash 的用户计数，首次 crash 已发生的设备当天不会因为 SafeMode 退出而从分子移除。
- **建议**：补充指标边界：SafeMode 直接降低重复崩溃、启动循环和 crash-free sessions 损失；对 Vitals 用户感知崩溃率的改善依赖远程配置、灰度暂停或跨天避免再次命中。

## [Task6 Review] 20.7 异常处理架构设计 — 2026-05-15
- **类型**：需确认
- **位置**：§全局异常捕获框架设计 / `ApplicationExitInfo`
- **问题**：Task9 已指出 native tombstone trace 的 API 边界和空 trace fallback 未写清；Task6 已在正文加 `[需确认]` 标注，不做技术裁决。
- **建议**：由 Task2B 按 Task9 问题单拆分 API 30+ 退出原因、API 31+ native tombstone trace、ANR trace 与 null fallback。
- **review 日志**：logs/review/2026-05-15-06-review.md

## [Task6 Review] 20.7 异常处理架构设计 — 2026-05-15
- **类型**：需补充素材
- **位置**：§安全气囊（SafeMode）机制
- **问题**：SafeMode 判定只有 crashStore 聚合，缺 launch marker 状态机、启动成功标记、退出原因过滤和离线补偿链路；Task6 已标注回炉。
- **建议**：由 Task2B 补启动状态机和 ApplicationExitInfo 结合规则，再交 Task9 复核。
- **review 日志**：logs/review/2026-05-15-06-review.md

## [Task6 Review] 20.7 异常处理架构设计 — 2026-05-15
- **类型**：需确认
- **位置**：§多进程异常隔离 / WebView 独立进程
- **问题**：Task9 指出 WebView renderer 进程不能按 App 自有多进程 Crash handler 模型处理；Task6 已在正文标注区分 App 自有容器进程与系统 WebView renderer。
- **建议**：由 Task2B 补 `WebViewClient.onRenderProcessGone()` 处理边界、记录字段和页面兜底策略。
- **review 日志**：logs/review/2026-05-15-06-review.md

## [Task6 Review] 20.7 异常处理架构设计 — 2026-05-15
- **类型**：需补充素材
- **位置**：§多进程异常隔离 / crash 文件写入
- **问题**：正文只写“临时文件 + rename”，缺 flush/fsync、rename 后父目录 fsync、completed/tmp 扫描与 partial 清理规则；Task6 已标注回炉。
- **建议**：由 Task2B 补完整 crash 样本持久化协议，并让 Task9 复核崩溃/断电边界。
- **review 日志**：logs/review/2026-05-15-06-review.md


## [Task9 Deep Review] 26.7 发版质量门禁 — 2026-05-15
- **类型**：数据缺失 / 发布信号口径
- **位置**：L85、L145、L169 Android Vitals 作为灰度门禁信号
- **问题**：正文已经写到 Vitals 使用 28 天窗口，但灰度状态机又把 Vitals 放进 50%-100% 阶段的同源异常判断，缺少“慢信号”边界。Play Vitals 更适合做外部质量守门、上架风险和回滚后长期确认，不能和分钟级 APM / Crash 上报混成同一放量判定窗口。
- **建议**：把门禁信号拆成 fast signals（APM、Crash/ANR 上报、启动/帧率分群、客服/日志）和 slow signals（Vitals 28 天窗口、Play warning、商店可见性影响）。状态机里说明 50%-100% 阶段以 fast signals 决定是否升档/暂停，Vitals 用于发布后复核和外部质量红线。

## [Task9 Deep Review] 26.7 发版质量门禁 — 2026-05-15
- **类型**：数据缺失 / 官方资料边界
- **位置**：L153-L164 全量发布后的 halt 能力
- **问题**：正文引用 `edits.tracks` / `tracks` 说明 `inProgress` staged release 可更新为 `halted`，但 L164 又写“已 100% 发布后使用商店 halt 能力”。全量 halt 是 Play Console 另一个能力，当前参考资料没有覆盖；且 halt 只能阻止更多用户拿到问题版本，不能让已安装用户自动降级。
- **建议**：如果保留“全量 halt”结论，补充 Play Console Help 的 fully rolled-out release halt 资料与限制（排除 internal test track、通过 Play Console/Publishing API、不会修复既有安装）；否则把 L164 改成“已全量后以修复包 + 服务端降级为主，仍处于 staged rollout 时才 halt”。


## [Task14 参考书扫描] 8.3 启动优化 — 2026-05-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]
- **建议补充**：ThreadPoolExecutor 构造函数 7 个参数的工程解读（corePoolSize、maximumPoolSize、keepAliveTime、workQueue 类型选择：LinkedBlockingDeque 用于 CPU 线程池、SynchronousQueue 用于 IO 线程池），以及 execute() 源码中「队列满才创建非核心线程」的调度顺序。AIW §8.3 仅有一句「分为 CPU 线程池和 IO 线程池」，缺少参数级指导。
- **参考书覆盖深度**：深入（含源码分析和参数对比表）

## [Task14 参考书扫描] 7.5 卡顿优化 / 2.5 MainThread 与 RenderThread — 2026-05-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]
- **建议补充**：(1) Process.setThreadPriority 的 Nice 值常量表（THREAD_PRIORITY_DEFAULT=0, THREAD_PRIORITY_DISPLAY=-4, THREAD_PRIORITY_URGENT_DISPLAY=-8 等），AIW §7.5 提到 PRIORITY_DISPLAY 但无完整对照表；(2) Thread.setPriority 不推荐用于子线程的原因（时序 Bug：子线程未创建成功时设置到主线程）；(3) 通过 /proc/pid/task 遍历找到 RenderThread TID 的具体方法。AIW §7.5 已确认 AOSP 不做 cgroup 绑核，但缺少 Nice 值表和找 TID 的工程路径。
- **参考书覆盖深度**：中等（API 使用指导为主，AOSP 源码层较浅）

## [Task14 参考书扫描] 8.1 响应速度原理 / 25.1 功耗诊断 — 2026-05-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - CPU 优化（下）：减少 CPU 闲置时刻和等待，提升利用率.md]
- **建议补充**：(1) /proc/stat 各列字段含义（user/nice/system/idle/iowait/irq/softirq）和 CPU 总运行时间计算方法；(2) /proc/pid/stat 前 24 项字段含义（pid/state/ppid/utime/stime 等）；(3) 基于以上数据的 CPU 占用率计算公式。AIW §25.1 引用了此文件但正文未展开 proc 文件节点的数据读取方法。
- **参考书覆盖深度**：中等（proc 节点字段解读详细，但 times() 方案未展开）

## [Task14 参考书扫描] 10.3 内存增长治理 — 2026-05-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **建议补充**：冷热端分离的 LruCache 改造方案——按访问频率将缓存拆分为热端（高频数据，按频率排序）和冷端（低频数据，仍用 LRU），热端满时将队尾降级到冷端头部，冷端满时淘汰队尾。AIW §10.3 详细介绍了 LruCache 基本原理和 trim 策略，但未讨论「最近最少使用 ≠ 不频繁使用」的问题和冷热分离淘汰策略。该方案对低内存设备上的图片缓存命中率有显著提升。
- **参考书覆盖深度**：概述（思路和图解清晰，无代码实现）

## [Task6 Review] 26.7 发版质量门禁 — 2026-05-15
- **类型**：需确认
- **位置**：§自动化性能测试集成 / Macrobenchmark 指标段与示例配置
- **问题**：Task9 指出 TTFD / `frameOverrunMs` 版本与采集前提缺少边界；Task6 已在正文标注回炉，不裁决指标可用性。
- **建议**：由 Task2B 补 `reportFullyDrawn()`、Android 10 / API 29、API 31+、`metric_available` / fallback 边界，再交 Task9 复核。
- **review 日志**：logs/review/2026-05-15-07-review.md

## [Task6 Review] 26.7 发版质量门禁 — 2026-05-15
- **类型**：需补充素材
- **位置**：§灰度发布与性能监控联动 / 50%-100% 状态机
- **问题**：Vitals 是 28 天窗口的慢信号，但当前状态机把它和分钟级 APM / Crash / ANR 信号混在同一放量条件里；Task6 已标注回炉。
- **建议**：由 Task2B 拆清 fast signals / slow signals 的用途：快信号决定升档或暂停，Vitals 用于外部质量红线和发布后复核。
- **review 日志**：logs/review/2026-05-15-07-review.md

## [Task6 Review] 26.7 发版质量门禁 — 2026-05-15
- **类型**：需确认
- **位置**：§版本回滚决策流程 / 已 100% 发布后的 halt 动作
- **问题**：当前引用能支撑 staged rollout 的 `inProgress` → `halted`，但已全量后的 halt 能力、限制和既有安装用户不会自动降级的边界还缺官方资料；Task6 已标注回炉。
- **建议**：由 Task2B 补 Play Console / Publishing API 资料；如果资料不足，把动作改为“修复包 + 服务端降级”为主。
- **review 日志**：logs/review/2026-05-15-07-review.md

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-15
- **类型**：数据缺失
- **位置**：L600 / DeliQueue 实际数据结构补充
- **问题**：`内存开销 ... 比旧单链表多约 20-30%` 给出了具体百分比，但 Android Developers Blog 和当前章节引用的 AOSP 路径没有提供这组量化口径。
- **建议**：删除 20-30% 数字，或补充可复现测量条件（设备、队列长度、消息对象数量、heap/stack 统计方式）和来源链接。

## [Task9 Deep Review] 26.8 可观测性案例集 — 2026-05-15
- **类型**：数据缺失
- **位置**：L169-L174 CI 门禁基线与阻断条件
- **问题**：正文写“最近 N 次绿色构建”“P95 明显超过基线”，但没有给出 N、样本量、波动处理、相对/绝对阈值或复跑规则。性能门禁如果只写模糊阈值，团队落地时容易把一次噪声当退化，或把真实小幅退化放过。
- **建议**：补一段门禁判定协议：每个场景固定 warmup/iteration，基线窗口例如最近 5-10 次绿色构建；阻断条件同时满足相对退化和绝对退化（例如 P95 +10% 且 +50ms，具体数值由团队校准）；波动大时自动复跑或转人工确认；报告保留 device/build/thermal/battery/metric_available 字段。

## [Task9 Deep Review] 26.8 可观测性案例集 — 2026-05-15
- **类型**：知识盲区
- **位置**：L90-L140 事件模型与证据包；L226-L287 下载/启动/卡顿证据字段；L282 ProfilingManager 结果上传
- **问题**：章节列出了 URL 模板、文件路径 hash、操作日志、Trace/profile 等证据，但没有定义脱敏、加密、保留期、上传授权和字段 allowlist。APM/线上 profile 很容易带出 URL query、header、堆对象、文件路径、用户操作序列等敏感信息，缺少数据治理边界会影响线上可用性。
- **建议**：在 APM 第一版验收或 Runbook 模板里补“数据治理”栏：只采 URL 模板不采 raw URL/query；header/body 默认禁采、按 allowlist 开；日志/trace/profile 本地加密并设置 TTL；大文件上传需远程开关、采样和用户/地区合规策略；服务端索引对 session_id/request_id 做权限隔离。

## [Task9 Deep Review] 13.11 Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数 — 2026-05-15
- **类型**：版本差异 / 工具版本边界
- **位置**：frontmatter L8-L10；L352-L359 Trace Processor 标准库与宏能力
- **问题**：章节把适用范围写成 Android 12-17，但 `SPAN_JOIN`、`CREATE PERFETTO TABLE/MACRO`、`intervals.*` / `slices.*` 标准库模块属于 Trace Processor / PerfettoSQL 能力，和分析端的 Perfetto 版本绑定，不由被分析设备的 Android API level 决定。Android 版本只影响 trace 里有没有 Frame Timeline、cpufreq counter、ART slice 等输入数据。当前口径会让读者误以为 Android 12 以下不能用 SPAN_JOIN，或忽略旧 Android Studio / AGI 内置 Trace Processor 不支持新 stdlib 的风险。
- **建议**：补一段“工具版本前提”：使用当前 `trace_processor_shell` 或 ui.perfetto.dev，并确认支持 `SPAN_JOIN`、`CREATE PERFETTO TABLE/MACRO`、`INCLUDE PERFETTO MODULE intervals.*`；旧工具不支持时导出 trace 到新 Trace Processor 分析。Android 12+ 只作为 Frame Timeline / 采集数据示例的边界，不作为 SPAN_JOIN 本身的适用版本。

## [Task6 Review] 13.11 Perfetto 时间跨度关联：SPAN_JOIN 与窗口函数 — 2026-05-15
- **类型**：需确认 / 结构补齐
- **位置**：帧 × CPU 频率统计 SQL；GC pause 与 frame overlap SQL；全文大纲
- **问题**：Task9 已指出两个技术阻塞点：帧 × CPU 频率示例未按 frame 边界裁剪 `joined.dur`，GC pause 示例可能把全局 GC slice 合并进同一 `utid` 分区。Task6 不做技术裁决，已在正文加 `[存疑]` 标注。另发现本节缺少 `outline-start` / `outline-end` 大纲块，Task6 无法按锚点做覆盖核验。
- **建议**：Task2B 按 Task9 队列项修正 SQL 口径；同时补齐本节锚点大纲，覆盖 SPAN_JOIN 定义、counter 转 span、PARTITIONED 约束、帧 × CPU 频率、Binder/GC 交叉分析、标准库配合、CI 复用和排查清单。
- **review 日志**：logs/review/2026-05-15-10-review.md

## [Task9 Deep Review] 17.4 sched_ext 与 OEM BPF 调度器 — 2026-05-15
- **类型**：源码锚点缺失
- **位置**：L260 Android common kernel OPPO scx tracepoint / symbol list 线索
- **问题**：正文写“搜索结果中也能看到 OPPO 相关 scx tracepoint / symbol list 线索”，但没有给出具体 Android common 路径、commit、symbol 名或搜索 URL。该句现在无法复核，也无法区分是 Android common 通用代码、厂商提交残留，还是搜索噪声。
- **建议**：补具体源码锚点或删除该判断；如果只能保留为线索，应改成 `[待验证]` 并给出搜索关键词、commit id 或 Gerrit 链接。


## [Task9 Deep Review] 20.10 WebView Renderer OOM 与白屏恢复 — 2026-05-15
- **类型**：源码准确性
- **位置**：`rendererPriorityAtExit()` 说明（L124 / L213）
- **问题**：正文只写“返回退出时 Renderer 优先级”，未说明多个 WebView 共用 Renderer 时该值可能高于当前 WebView 自己请求的优先级。
- **建议**：补充“rendererPriorityAtExit 反映 Renderer 最终优先级；多 WebView 共用时由 attached WebViews 的最大优先级决定，不能直接反推当前 view 的 policy”。

## [Task9 Deep Review] 20.10 WebView Renderer OOM 与白屏恢复 — 2026-05-15
- **类型**：源码准确性
- **位置**：ApplicationExitInfo 归因段（L245）
- **问题**：结论方向正确，但依据标成 WebViewClient 文档；WebViewClient 只能证明 return false 的 crash/kill 行为，不能证明 ApplicationExitInfo 的进程退出归因能力边界。
- **建议**：引用 `ActivityManager#getHistoricalProcessExitReasons()` 与 `ApplicationExitInfo` 文档；明确它是宿主进程死亡后的补偿信号，不是 Renderer gone 的实时事件源。

## [Task9 Deep Review] 20.10 WebView Renderer OOM 与白屏恢复 — 2026-05-15
- **类型**：源码准确性
- **位置**：Provider 版本采集建议（L255）
- **问题**：`WebViewCompat.getCurrentWebViewPackage()` 写成无参调用；AndroidX 版本需要 `Context` 参数，framework `WebView.getCurrentWebViewPackage()` 才是 API 26+ 无参。
- **建议**：本章适用 API 26+ 时优先写 `WebView.getCurrentWebViewPackage()`；若保留 AndroidX，改成 `WebViewCompat.getCurrentWebViewPackage(context)`。

## [Task9 Deep Review] 21.5 Splash Screen 与感知启动速度 — 2026-05-15
- **类型**：源码准确性
- **位置**：`postSplashScreenTheme` 说明（L164）
- **问题**：正文写“缺失或指向不存在主题，Activity 会崩溃”过于绝对；缺失通常导致 Activity 继续使用启动主题或样式不正确，资源不存在更多是编译/资源解析问题。
- **建议**：拆开说明：必须配置正确的 `postSplashScreenTheme` 才能切回正常主题；缺失会造成主题残留/视觉异常；引用不存在资源应按构建或资源解析错误处理。

## [Task9 Deep Review] 21.5 Splash Screen 与感知启动速度 — 2026-05-15
- **类型**：数据缺失
- **位置**：`reportFullyDrawn()` 度量说明（L416）
- **问题**：`PowerTube` 不是公开可核验的 Android 启动度量入口；该段缺少官方指标名和采集面边界。
- **建议**：改为 Logcat `Displayed` / `Fully drawn`、Perfetto/FrameTimeline、Play Console Android Vitals（如适用）等可核验入口；删除或标注 `PowerTube` 来源。

## [Task6 Review] 18.2 Android View 标准管线（BLAST 深入） — 2026-05-15
- **类型**：需整合素材 / 发布稿编辑痕迹
- **位置**：附录「源码调研补充 — ART Generational CC 与 BLAST BufferQueue 协同机制」
- **问题**：附录仍保留 AIW 每日源码调研、来源、注入时间、价值等加工记录，读起来像素材 dump；内容与正文和参考资料重复，且部分技术点已被 Task9 标记为高风险。
- **建议**：Task2B 先按 Task9 复核技术口径，再把可用内容整合进 BLAST 生命周期或 Compose/GC 小节；发布稿不保留 AIW 注入记录和未核验结论。
- **review 日志**：logs/review/2026-05-15-12-review.md
## [Task9 Deep Review] 4.9 ART FinalizerDaemon 与 ReferenceQueue 性能边界 — 2026-05-15
- **类型**：源码准确性
- **位置**：L119 ReferenceQueue.remove() 描述
- **问题**：“remove() 阻塞在队列锁上”容易被理解成等待期间一直持有 queue.lock。源码里 remove() 进入 synchronized(lock) 后调用 lock.wait(timeout)，等待期间会释放 monitor，唤醒后再重新竞争锁并 poll。
- **建议**：改成“remove() 在同一把 lock 下检查队列；无元素时 wait() 释放 monitor 并等待 notify/timeout”。

- **类型**：源码引用/版本细节
- **位置**：L283-L285 FinalizerWatchdogDaemon 超时说明
- **问题**：引用行号 Daemons.java 414-449 只覆盖 watchdog 类头和 TOLERATED_REFERENCE_QUEUE_TIMEOUTS 常量，真正的 waitForProgress()/timedOut() 行为在约 L561-L735。ReferenceQueueDaemon 超时也不是一次阈值即异常，而是 observedReferenceQueueTimeouts > 5 后才返回 refQueueTimeoutException。
- **建议**：修正源码锚点，并补“FinalizerDaemon 单对象超时”和“ReferenceQueueDaemon 连续多次无进展才升级”的区别。

- **类型**：源码路径规范
- **位置**：frontmatter L15-L18 sources.path
- **问题**：AOSP tag 不应作为 platform/libcore 下的目录段。正文 L71-L72 的写法是可复核的；frontmatter 中 platform/libcore/android-16.0.0_r1/... 不是 Gitiles/AOSP 实际路径。
- **建议**：统一成 platform/libcore/ojluni/... @ android-16.0.0_r1，或写完整 Gitiles URL refs/tags/android-16.0.0_r1。

## [Task9 Deep Review] 13.12 Perfetto Profile 导入与 Flamegraph 分析 — 2026-05-15
- **类型**：交叉引用一致性
- **位置**：`src/part3-tools/ch13-perfetto/README.md` L7-L18、L49-L60；13.12 frontmatter `related_chapters`
- **问题**：`src/SUMMARY.md` 已包含 13.11/13.12，但 ch13 README 仍停在 13.1-13.10，`last_verified_against` 也写 13.1-13.10；13.12 正文 L227 引用 13.11，但 frontmatter `related_chapters` 没有列 13.11。
- **建议**：同步 ch13 README 的章节列表、阅读顺序和 `related_chapters` 到 13.12，并在 13.12 frontmatter 增加 13.11，避免读者按章节入口找不到新增 SQL/Profile 内容。

## [Task9 Deep Review] 22.10 RenderEffect 与 RuntimeShader 性能实践 — 2026-05-15
- **类型**：版本差异/API 边界
- **位置**：L123 页面级毛玻璃 / backdrop effect
- **问题**：表格把 View.setRenderEffect() 与 backdrop effect 放在同一行。View.setRenderEffect() 处理的是 View/RenderNode 自身绘制结果；真正的 backdrop blur 需要隐藏 API setBackdropRenderEffect() 一类能力，普通应用不能依赖。SDK sources 中 android-31~34 无 setBackdropRenderEffect，android-35 才可见 @hide 入口。
- **建议**：拆成“自身内容 blur”和“背后内容 blur”两种语义：普通应用用 RenderEffect 只能处理自己掌控的背景/截图/子树；backdrop effect 标为 hidden API、版本不稳定，不作为工程推荐路径。

- **类型**：版本差异/数据缺失
- **位置**：L258 GPU Headroom 降级口径
- **问题**：Android 16 官方说明提供 SystemHealthManager + CpuHeadroomParams/GpuHeadroomParams，用于在 supported devices 上估算可用 CPU/GPU 资源；当前正文仍保留待验证标注，且未说明 supported devices、采样窗口、average/min resource availability 等参数边界。
- **建议**：补成“Android 16+ 且设备支持时可用 GPU Headroom 辅助质量降级；不支持或返回无效值时回退到帧耗时/温控/灰度开关”。若引用 2.10，需等 2.10 的 GPU Headroom/gpu_busy pending 项修正后再同步。

- **类型**：数据缺失
- **位置**：L279-L283 厂商 GPU blur / AGSL 成本曲线
- **问题**：“同一段 AGSL 在旗舰设备上可能只增加 1-2ms，在低端机或温控状态下可能跨过整帧预算”是量化判断，但正文没有给设备型号、刷新率、效果面积、blur 半径/采样次数、Perfetto/AGI 采样条件。
- **建议**：要么降级为定性风险提示；要么补一张最小实测表：Adreno/Mali/低端机各一台，记录无效果、小半径、大半径、AGSL 的 P50/P90/P99、jank、Graphics/GL mtrack 与可用 GPU counter。

## [Task9 Deep Review] 24.9 Wi-Fi 评分、网络选择与连接切换性能 — 2026-05-15
- **类型**：公开 API 使用边界
- **位置**：L253-L270 DefaultNetworkTracker 示例
- **问题**：`onAvailable()` 内经 `publish(network)` 同步读取 `getNetworkCapabilities(network)`，与 Android NetworkCallback 官方文档的 race 条件提示冲突。
- **建议**：`onAvailable()` 只记录事件和 current network；能力快照从 `onCapabilitiesChanged(network, caps)` 发布，`publish()` 不要在回调内默认同步查询 capabilities。

## [Task9 Deep Review] 24.9 Wi-Fi 评分、网络选择与连接切换性能 — 2026-05-15
- **类型**：知识盲区 / OEM Wi-Fi scoring
- **位置**：L380-L388 OEM Wi-Fi 评分差异
- **问题**：OEM 差异漏掉官方 Wi-Fi network selection 文档中的 `WifiConnectedNetworkScorer` / external scorer 扩展点。
- **建议**：在 OEM 差异表补 external scorer：注册 API、输入的 Wi-Fi usability stats、输出 score，以及 dumpsys/overlay/包名等验证材料。


## [Task9 Deep Review] 26.9 ApplicationExitInfo 与进程退出归因 — 2026-05-15
- **类型**：数据支撑 / 字段语义边界
- **位置**：L118、L154-L155、L252 `pss` / `rss`
- **问题**：正文把 `pss` / `rss` 当作“当时资源水位”。AOSP `ApplicationExitInfo#getPss()` / `getRss()` 注释说明它们是进程最后一次采样值，不是死亡前精确内存；系统来不及采样时可能为 0。
- **建议**：改成“last sampled PSS/RSS”，并在 ExitEnvelope 增加 sample_age / 是否系统采样为空；低内存归因要结合端侧自采样、`isLowMemoryKillReportSupported()`、importance 与前后台状态。

## [Task9 Deep Review] 26.9 ApplicationExitInfo 与进程退出归因 — 2026-05-15
- **类型**：API 使用边界
- **位置**：L252 `process_state_summary`
- **问题**：正文建议保存 `ActivityManager.setProcessStateSummary()` 摘要，但没有说明官方限制：最大 128 bytes、不要包含 PII/SPII，系统可能 throttle 过高频调用并抛 `RuntimeException`；它也不应用来恢复 UI 状态。
- **建议**：把该字段限定为短小、低频、非敏感的状态标签，例如实验组、关键页面/阶段 ID、启动阶段码；不要放完整 JSON、URL、用户标识或恢复状态。

## [Task9 Deep Review] 25.10 Hybrid/WebView 功耗与原生化取舍 — 2026-05-15
- **类型**：数据缺失/工具边界
- **位置**：L156-L162 Macrobenchmark PowerMetric 口径
- **问题**：Macrobenchmark PowerMetric 被列为能耗估算采集方式，但缺少官方限制：结果是 system-wide consumption，不是 per-app attribution；官方文档限定 Pixel 6 / Pixel 6 Pro 及后续设备。Hybrid/WebView 实验中，WebView provider、浏览器、后台账号同步和温控都可能污染 system-wide 数据。
- **建议**：补 PowerMetric 可用设备、system-wide 属性和干扰控制；per-app 判断回到 BatteryStats / Power Profiler / Perfetto / APM 的 CPU time、网络、PSS/RSS 与页面会话字段。

## [Task9 Deep Review] 20.4 ANR 治理策略 — 2026-05-15
- **类型**：源码准确性/数据支撑
- **位置**：L154 WorkManager 后台任务模式
- **问题**：WorkManager 示例后标注的验证来源是 AOSP ActiveServices.java，无法支撑 AndroidX WorkManager 的调度语义；读者会误以为 WorkManager 行为由 ActiveServices 直接定义。
- **建议**：改引 AndroidX WorkManager 官方文档或 androidx.work 源码；补一句 WorkManager 受约束、配额和后台调度策略影响，不保证立即执行。

## [Task9 Deep Review] 20.4 ANR 治理策略 — 2026-05-15
- **类型**：数据缺失/风险过滤
- **位置**：L586-L596 系统负载 ANR 识别与过滤
- **问题**：“nativePollOnce 更可能是系统侧阻塞”“CPU iowait >30%”“标记但不上报”缺少可复现实验或线上统计支撑；nativePollOnce 单独不能证明系统原因，直接不上报会丢失排障样本。
- **建议**：改为多信号判定：ANR reason、waitQueue head age、system_server trace、CPU/iowait、LMK/event log 同时满足才标记 likely_system_caused；策略改成“上报并标记/降权”，不要直接丢弃。

## [Task9 Deep Review] 1.18 Binder Freezer 与缓存进程冻结性能 — 2026-05-15
- **类型**：交叉引用/来源路径
- **位置**：L50 sources 与 L270 参考资料
- **问题**：frontmatter 写 DeepResearch/2026-05-08-binder-freezer-driver-cgroup-v2-coordination-mechanism.md，但该路径不在 Android-Internal-Wiki 项目根内；实测文件位于 Obsidian/DeepResearch/ 同级目录。
- **建议**：把来源路径改成可点击/可复核的 Obsidian 相对路径（如 ../DeepResearch/...）或在 sources 中标明它不是项目内路径。

## [Task9 Deep Review] 1.18 Binder Freezer 与缓存进程冻结性能 — 2026-05-15
- **类型**：源码准确性/观测点
- **位置**：L212 Perfetto Freezer track 事件名
- **问题**：正文写事件名包含 Freeze process:pid / Unfreeze process:pid reason；AOSP main traceAppFreeze() 实际写入 "Freeze " 或 "Unfreeze " + processName + ":" + pid + " " + reason，另有 reschedule 事件 "Reschedule freeze <process>:<pid> timeout=..., reason=..."。
- **建议**：按源码改成精确事件名模板，并补充 reschedule freeze 是 Binder outstanding transaction/新 pending transaction 场景的重要观察点。

## [Task9 Deep Review] 8.2 App 启动全流程 — 2026-05-16
- **类型**：数据缺失
- **位置**：L188 / L568 / L582 / L624 启动收益与 preload 覆盖率数字
- **问题**：16KB page size 3.16%、Baseline Profile 冷启动缩短 20%-40%、10 个 ContentProvider 50-100ms、Zygote preload 覆盖 80%+ 类加载需求都缺设备、应用规模、版本、样本量或官方原文口径。
- **建议**：给每组数字补来源链接、测试设备、Android 版本、App 规模和指标定义；无法补证的数字降级为定性描述或标 `[待验证]`。

## [Task9 Deep Review] 21.2 启动框架设计与任务编排 — 2026-05-16
- **类型**：数据缺失/原理边界
- **位置**：L388-L397 CPU 线程池配置与 CallerRunsPolicy
- **问题**：`cpuCount + 1`、队列 64、CallerRunsPolicy 被写成通用 CPU 线程池方案，但没有给 SoC/任务类型/提交线程口径；如果主线程提交任务且队列满，CallerRunsPolicy 会把 CPU 任务带回主线程执行，可能反向拉长 TTID。
- **建议**：把这组参数标为示例配置，补充“提交线程不能是首帧关键主线程”或增加专门 backpressure 策略；用 Perfetto sched、任务等待时间、TTID P90/P99 验证线程池参数。

## [Task9 Deep Review] 20.11 MTE memtagMode 与 Native 崩溃治理 — 2026-05-16
- **类型**：知识盲区/版本边界
- **位置**：L136/L148/L176 MTE 生效边界
- **问题**：正文覆盖硬件能力、manifest、compat change 和设备侧 mte_tcf_preferred，但没有把 64-bit/arm64 进程作为生效前提写进灰度筛选。AOSP Zygote.getMemorySafetyRuntimeFlags() 只有 instructionSet 为 null 或 arm64 时才合入 tagging level；32-bit 子进程不会启用 MTE。
- **建议**：在设备筛选和 APM 字段中补充 ABI/进程位数：只把 arm64 进程纳入 MTE 灰度；32-bit 进程单独标记为不可用或降级。

## [Task9 Deep Review] 20.11 MTE memtagMode 与 Native 崩溃治理 — 2026-05-16
- **类型**：数据缺失
- **位置**：L158 性能成本描述
- **问题**：正文判断 SYNC 成本高于 ASYNC，但没有给出设备、模式、allocator 栈记录开关、benchmark 类型和量化区间。读者无法据此制定灰度阈值。
- **建议**：补一组官方或自测数据：Pixel 8/9、Android 14-16、sync/async/asymm、启动/帧耗时/native 分配密集场景；无法补证时把“成本高于”保留为定性边界。

## [Task9 Deep Review] 20.11 MTE memtagMode 与 Native 崩溃治理 — 2026-05-16
- **类型**：交叉引用/证据路径
- **位置**：frontmatter sources + L119/L187 DeepResearch 引用
- **问题**：`DeepResearch/2026-05-13-android-mte-memtag-async-asymm-analysis.md` 在仓库中不存在，ASYMM 归因和 BIONIC_MEMTAG_UPGRADE_SECS 线索无法从本地材料复核。
- **建议**：恢复该材料文件，或把相关结论只锚到 source.android.com/AOSP 源码；BIONIC_MEMTAG_UPGRADE_SECS 保持 `[待验证]` 并补源码路径后再展开。

## [Task9 Deep Review] 22.11 AnimatedVectorDrawable 线程退化与动画卡顿 — 2026-05-16
- **类型**：知识盲区/源码边界
- **位置**：L82-L84 资源写法优化策略
- **问题**：正文提到 path、颜色、pathData、clipPath 成本，但没有覆盖 VectorDrawableAnimatorRT 的属性支持边界。AOSP parseAnimatorSet() 只处理 AnimatorSet/ObjectAnimator；ValueAnimator 会被忽略；group/path/root 支持的属性集合不同，部分非法属性在 targetSdk N+ 会抛异常。
- **建议**：补一张“RT 可支持/需验证/不支持”表：group transform、full path fill/stroke、pathData、root alpha、ValueAnimator、自定义属性；把资源审计和线程退化排查分开。

## [Task9 Deep Review] 22.11 AnimatedVectorDrawable 线程退化与动画卡顿 — 2026-05-16
- **类型**：数据缺失/Trace 观察点
- **位置**：L67-L72 Perfetto 识别步骤
- **问题**：观察步骤没有给出一条真实 trace 样本或稳定 slice 名映射；`ViewRootImpl#doTraversal` 与 Perfetto 常见 trace 名（`performTraversals`、RenderThread `DrawFrame`）需要对齐，否则读者按名称搜索可能找不到。
- **建议**：补一个最小复现实验：普通 ImageView vs Bitmap Canvas/software layer，列出 UI thread、RenderThread、FrameTimeline 的实际 slice 名和帧耗时对比。

## [Task9 Deep Review] 22.11 AnimatedVectorDrawable 线程退化与动画卡顿 — 2026-05-16
- **类型**：交叉引用/证据路径
- **位置**：frontmatter sources + 参考资料 DeepResearch 引用
- **问题**：`DeepResearch/2026-05-08-animatedvectordrawable-thread-degradation.md` 在仓库中不存在，线程退化材料链无法本地复核。
- **建议**：恢复该材料文件，或把对应结论直接锚到 AOSP `AnimatedVectorDrawable.java` 行为和 Android Developers 文档。

## [Task9 Deep Review] 25.11 ADPF Hint Session 与协程线程迁移 — 2026-05-16
- **类型**：源码/API 风险
- **位置**：L80-L83 示例 ThreadFactory 中 THREAD_PRIORITY_DISPLAY
- **问题**：示意代码直接调用 `Process.setThreadPriority(Process.THREAD_PRIORITY_DISPLAY)`。`Process.setThreadPriority()` 文档说明调用方没有权限修改线程或使用该优先级时会抛 `SecurityException`；普通 App 在部分设备/版本上可能不能提升到该优先级。
- **建议**：示例中去掉强行提升到 `THREAD_PRIORITY_DISPLAY`，或 catch `SecurityException` 后降级；若保留线程优先级讨论，单独说明它不是 ADPF 的替代品，也不能作为跨设备稳定收益假设。

## [Task9 Deep Review] 25.11 ADPF Hint Session 与协程线程迁移 — 2026-05-16
- **类型**：交叉引用/来源路径
- **位置**：frontmatter sources L34-L35 与 L43 结构参考
- **问题**：`Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md` 在当前 Obsidian vault 中未找到；可找到的相近材料是 `Cubox/速度优化：任务调度优化 - 掘金-2024-02-02.md`。结构参考路径失效会削弱材料链可复核性。
- **建议**：把 sources 和正文结构参考改成实际存在的 Cubox 路径，或恢复原 Clippings 材料；如果只是结构启发，标明它不是技术证据来源。

## [Task9 Deep Review] 26.10 Android 11 以下进程退出归因方案 — 2026-05-16
- **类型**：源码路径/版本锚点
- **位置**：frontmatter L9、L31-L32 `last_verified_against` 与 `system/core/lmkd/`
- **问题**：章节声明按 “AOSP master paths” 验证，但 `system/core/lmkd/` 是 Android 10 及更早分支常见路径；AOSP 当前主线/资料索引已迁到 `platform/system/memory/lmkd`。如果不标分支，读者按 master 复核会找不到路径。
- **建议**：把 source 写成版本化锚点，例如 “android10-release: system/core/lmkd/；current main: system/memory/lmkd/”，并把 `last_verified_against` 改成按 Android 5-10 分支验证，而不是泛称 master。

## [Task9 Deep Review] 26.10 Android 11 以下进程退出归因方案 — 2026-05-16
- **类型**：权限/API 边界
- **位置**：L144 JVMTI 段落
- **问题**：ART TI/JVMTI 在 Android 8.0+ 的 agent 接入受 debuggable 等限制；AOSP ART TI 文档明确 ActivityManager 和 runtime 只允许 agent attach 到 debuggable app。当前只写“可用于调试和监控类工具”，容易被理解成普通线上 APM SDK 可稳定使用 JVMTI 采集退出证据。
- **建议**：补一句生产边界：JVMTI 只放在 debuggable/profileable、实验室或厂商授权场景；普通发布包不要把 JVMTI 作为默认退出归因证据来源。

## [Task9 Deep Review] 26.10 Android 11 以下进程退出归因方案 — 2026-05-16
- **类型**：交叉引用/来源路径
- **位置**：frontmatter sources L33-L48 与正文结构参考 L74/L102/L128/L195
- **问题**：`DeepResearch/...` 相对 Android-Internal-Wiki 项目根目录不存在，实际文件位于 Obsidian 根目录的 `DeepResearch/`；列出的 `Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 *.md` 在当前 Obsidian vault 中未找到。材料链无法本地复核。
- **建议**：将 DeepResearch source 改成可解析的绝对路径或 vault-root 相对路径；恢复 Clippings 文件，或把这些引用标为“结构参考、非技术证据”，并为技术断言补官方/AOSP/开源项目锚点。

## [Task9 Deep Review] 1.19 Zygote 图形驱动预加载与启动性能 — 2026-05-16
- **类型**：版本差异
- **位置**：§AppProcess HAL 预加载当前落在 GraphicBufferMapper
- **问题**：正文引用 AOSP main 的 `GraphicBufferMapper::preloadHal()` 写 Gralloc 2/3/4/5，但 Android 13 tag 只有 Gralloc 2/3/4，Android 14+ 才包含 Gralloc 5。当前版本表只写“mapper 实现可能变化”，粒度偏粗。
- **建议**：补一行版本边界：Android 13 预加载 Gralloc 2/3/4；Android 14/15/16 与 AOSP main 预加载 Gralloc 2/3/4/5；设备最终版本仍以 vendor mapper 是否加载成功为准。

## [Task9 Deep Review] 1.19 Zygote 图形驱动预加载与启动性能 — 2026-05-16
- **类型**：数据缺失
- **位置**：§图形驱动预加载解决首帧前的冷路径成本 / §App 启动 trace 要拆成四段看
- **问题**：正文多次使用“首帧附近的抖动会小一些”“预热收益”等判断，但没有给出同一设备 boot trace、App trace 或属性开关对照样例。
- **建议**：补一个最小证据口径：同设备记录 `PreloadGraphicsDriver` boot trace 耗时、App 进程 `setupGpuLayers/setupAngle/chooseDriver` 与首次 EGL/Vulkan 调用耗时；如能安全切换 `ro.zygote.disable_gl_preload`，再给开启/关闭对照。没有实测时，把收益描述限制为“可能减少公共冷路径成本”。


## [Task14 参考书扫描] 23.4 Java Heap 优化策略 — 2026-05-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **建议补充**：冷热端分离 LruCache 策略——在缓存容量受限场景下（如低端设备），传统 LRU 可能淘汰高频使用数据。建议补充基于使用频率的冷热端分离缓存方案：将缓存分为热端（高频数据，按使用次数排序）和冷端（低频数据，LRU 淘汰），提升命中率。同时补充缓存命中率监控方法论：命中率 = 成功取到数据/请求次数。
- **参考书覆盖深度**：中等（有完整算法描述和图解，无代码实现）

## [Task14 参考书扫描] 21.1/25.6 启动分析/APK体积 — Dex 类文件重排序 — 2026-05-16
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]
- **建议补充**：Dex 类文件重排序优化——基于 CPU cache line（64字节）和空间局部性原理，通过 Facebook Redex 工具的 InterDexPass 对 dex 中类文件按启动加载顺序重排，提升高速缓存命中率从而加速启动。21.1 目前仅将 dex 重排作为 Baseline Profile 的对比项提及，建议补充完整的 Redex 使用流程（hprof 采集类加载顺序 → InterDexPass 重排）及 cache line 原理背景。
- **参考书覆盖深度**：中等（有完整 Redex 使用流程和 cache line 原理）

## [Task14 参考书扫描] 23.3/23.6 虚拟内存优化 — ART 备份栈释放（过时提醒） — 2026-05-16
- **类型**：版本更新
- **来源**：[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些“黑科技”优化手段.md]
- **过时内容**：释放 ART 备份栈空间方案（通过 GetPrimitiveArrayCritical 禁用 HomogeneousSpaceCompact GC 并 munmap 释放 main space 1 的 512M）仅适用于 Android 5-7，因为 Android 8+ 使用 ConcurrentCopying (CC) 回收器，不再创建 main space 1 备份空间。
- **建议更新至**：Android 16/17 标注该方案仅历史参考，现代 64 位设备虚拟内存空间充裕（128TB），32 位设备已极少。建议在 23.6 中仅作历史方案记录，重点转向多进程架构和线程治理等通用方案。

## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-05-16
- **类型**：数据缺失
- **位置**：L381/L389/L468/L499-L501
- **问题**：预览帧间隔标准差 2-3ms/5ms、TextureView 5-10ms 成本、CameraX 冷启动额外 80-150ms 与 “cameraserver 流程更简洁”均缺少设备型号、分辨率、刷新率、CameraX 版本和 Trace/benchmark 样本。
- **建议**：补 1-2 组同机 Camera2 vs CameraX / SurfaceView vs TextureView 的 Perfetto 样本；没有样本前，把数字降级为示例范围或删除，只保留观测方法。

## [Task9 Deep Review] 22.12 FragmentTransaction 提交链路与页面切换性能 — 2026-05-16
- **类型**：源码准确性 / 版本差异
- **位置**：L172/L180-L231
- **问题**：`executePendingTransactions()` 实际调用 `execPendingActions(true)` 后再 `forcePostponedTransactions()`；表格只写“会强制开始 postponed transaction”，没有说明它对已排队事务执行时会绕过 state-loss 检查，容易和 `commitNow()` 的 state-saved 行为混在一起。
- **建议**：在 API 边界表补一列或脚注：`executePendingTransactions()` 不新建事务，但会以 `allowStateLoss=true` 执行当前 pending actions，并强制开始 postponed transactions；不要把它当作安全的同步提交替代品。



## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-16
- **类型**：数据缺失 / 版本口径
- **位置**：src/part4-system/ch16-aosp/05-android17-api37-performance-changes.md:L231-L239、L559
- **问题**：`TRIGGER_TYPE_COLD_START` 的产物仍标为待验证，但 Android 17 features 页已给出公开口径：cold start 触发器返回 call stack sample 和 system trace。当前正文与附录的待验证标记会让发布稿留下已可核验的空洞。
- **建议**：把 cold start 产物写成“call stack sample + system trace”，并把待验证标记收敛为“最终字段名/交付文件形态以 API 37 SDK reference 为准”。

## [Task9 Deep Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-05-16
- **类型**：知识盲区 / 源码准确性
- **位置**：src/part4-system/ch16-aosp/05-android17-api37-performance-changes.md:L235、L553-L557
- **问题**：正文只说 `TRIGGER_TYPE_ANOMALY` 不要收窄成 Binder 或内存事件，缺少 Android 17 features 页已经公开的可执行口径：excessive binder calls、excessive memory usage、memory limit breach 对应 heap dump，binder spam 对应 stack sampling profile，且回调发生在系统强制处理前。
- **建议**：在主表或注册流程中补一行 anomaly：触发条件按“OS-defined/system-detected”表述，示例写 Binder spam / memory limit，产物写 heap dump 或 stack sampling profile；同时保留“内部阈值未公开”的边界。

## [Task9 Deep Review] 19.26 混合栈与跨平台 APM (WebView / Flutter) — 2026-05-16
- **类型**：源码准确性 / 版本口径
- **位置**：src/part3-tools/ch19-apm/26-hybrid-apm.md:L158
- **问题**：`WebViewClient.onPageCommitVisible()` 被写成“当前导航的新内容首次绘制到屏幕时回调”。官方语义是旧导航内容不再绘制，下一次 draw 可能显示 WebView 背景色或新内容；它不能证明有效新内容已经绘制。
- **建议**：改成“旧内容不再绘制 / 适合作为页面切换边界”，并明确白屏判断仍需 `postVisualStateCallback`、业务 ready、DOM 或 PixelCopy 继续确认有效内容。

## [Task9 Deep Review] 19.26 混合栈与跨平台 APM (WebView / Flutter) — 2026-05-16
- **类型**：数据缺失
- **位置**：src/part3-tools/ch19-apm/26-hybrid-apm.md:L268
- **问题**：MethodChannel 延迟“通常 1-5ms”、`addTimingsCallback` 批量延迟“50ms+”、常规误差“<20ms”等数字缺少设备、Flutter 版本、采样方式或 trace 证据。它们会被读者当成可复用误差边界。
- **建议**：补一组同设备 Flutter release/profile trace 或删除固定数字，改成“受 MethodChannel 排队、帧批量上报和主线程负载影响；只作为粗粒度 Session Timeline 锚点”。


## [Task9 Deep Review] 13.13 Perfetto CPU 频率与 DVFS 关联分析 — 2026-05-16
- **类型**：数据缺失
- **位置**：§端侧 AI 推理里的 governor 错配
- **问题**：正文引用 arXiv 2507.02135 的 40.4%、TTFT 7.0%-16.9%、TPOT 25.4%-36.8% 等数字，但只写了 Pixel 7 / Pixel 7 Pro 与 Tensor G2，缺少论文实验条件：Android 13、root/open 设备、battery bypass、Monsoon 0.2 ms 功耗采样、screen off、ShareGPT 数据集、模型/框架与固定频率搜索口径。
- **建议**：在数字前后补一行“实验条件与外推边界”；发布稿中不要把论文 controlled-frequency 结果写成普通用户态 App 可直接复现的收益。

## [Task9 Deep Review] 13.13 Perfetto CPU 频率与 DVFS 关联分析 — 2026-05-16
- **类型**：知识盲区 / 版本口径
- **位置**：§识别大小核和 cluster
- **问题**：正文主要靠 `cpu_freq` 频点集合识别 cluster。当前 Perfetto `cpu` 表已经暴露 `cluster_id` 与 `capacity`（有数据时），只靠频点集合在同频异构、厂商拆 policy 或频点裁剪场景下可能误分 cluster。
- **建议**：把识别顺序改成：优先读 `cpu.cluster_id` / `capacity`，再用 `cpu_freq` 频点集合和同步变频现象交叉验证；缺字段时退回 sysfs `policy*/affected_cpus`。

## [Task9 Deep Review] 5.1 Linux 进程调度基础 — 2026-05-16
- **类型**：数据缺失
- **位置**：L351 硬件迁移效率数据
- **问题**：`1.5μs - 3.5μs`、`10μs+` 是强量化断言，但正文没有给出 SoC、内核、测试方法、样本来源。
- **建议**：补 vendor / 论文 / 实测 Perfetto+ftrace 数据源；无法补证据时标为 `[待验证]` 并降低为定性描述。
- **类型**：Perfetto SQL 示例
- **位置**：L725-L732 RenderThread 大小核运行时间查询
- **问题**：SQL `GROUP BY core_type` 同时 `SELECT cpu`，SQLite 会返回任意 cpu，结果容易被误读。
- **建议**：若要按 big/LITTLE 汇总，去掉 `cpu` 字段；若要逐核展示，改为 `GROUP BY cpu, core_type`。
- **类型**：版本/默认值边界
- **位置**：L522-L526 `sched_base_slice_ns` 默认值
- **问题**：Linux v6.6 源码初始值为 750000ns，并按 tunable scaling 随 CPU 数缩放；正文直接写 3ms 容易被当成通用默认值。
- **建议**：写成“8 核设备 LOG scaling 下常见约 3ms；源码 normalized default 为 750µs”。

## [Task9 Deep Review] 5.7 CPU 相关的版本演进 — 2026-05-16
- **类型**：数据/案例支撑
- **位置**：L317-L327 Android 16 JobScheduler 配额优化
- **问题**：正文提到“API 查询 Job 为什么没执行或被停止”，但没有落到具体 API 和 trace 采集入口。
- **建议**：补 `JobScheduler.getPendingJobReasonsHistory()`，并给出 Perfetto `android.statsd` + `ATOM_SCHEDULED_JOB_STATE_CHANGED` / `android_job_scheduler_states` 的采集说明。
- **类型**：来源边界
- **位置**：L331-L341 Android 17 已确认变化来源
- **问题**：App memory limits 属于 behavior changes all-apps；Reduced Wakelocks for Idle Alarms 属于 features/release notes；Profiling trigger 属于 features/release notes。正文把来源合并成 behavior changes all-apps / target-37，证据边界不清。
- **建议**：按条目拆来源，避免把 feature/API 新增和 behavior change 强约束混在一个证据口径里。

## [Task6 Review] 5.1 Linux 进程调度基础 — 2026-05-16
- **类型**：需确认
- **位置**：UClamp per-task 示例、vlag 替代 SQL、`sched_base_slice_ns` 判断、UClamp/cpuset 生效验证
- **问题**：Task9 已指出源码/API、Perfetto SQL 和观察口径风险；Task6 不裁决技术真伪，已在正文加 `[存疑]` 标注。
- **建议**：Task2B 按 queue.json 中 `task9-5.1-uclamp-proc-perfetto-sql-20260516` 逐条修正；修完后重新进入 Task6/Task9。
- **review 日志**：logs/review/2026-05-16-12-review.md

## [Task6 Review] 5.7 CPU 相关的版本演进 — 2026-05-16
- **类型**：需确认
- **位置**：Android 9 App Standby Buckets 表、Android 17 Reduced Wakelocks for Idle Alarms
- **问题**：Task9 已指出版本边界与官方语义风险；Task6 不裁决技术真伪，已在正文加 `[存疑]` 标注。
- **建议**：Task2B 按 queue.json 中 `task9-5.7-standby-bucket-android17-wakelock-20260516` 修正版本拆分与官方语义；修完后重新进入 Task6/Task9。
- **review 日志**：logs/review/2026-05-16-12-review.md


## [Task9 Deep Review] 3.8 InputFlinger Rust 组件与自适应刷新率协同 — 2026-05-16
- **类型**：交叉引用一致性
- **位置**：3.8 关联 3.1；src/part1-fundamentals/ch03-input/01-input-dispatch.md:L251-L257、L1092-L1130
- **问题**：3.8 已把 InputFlinger Rust 与触摸驱动 ARR 拆成两条路径，但 3.1 仍写着“Rust 重构的 InputFlinger 为 ARR 提供更好支持”“无 GC 减少事件处理抖动”“input_filter_thread 减少主线程阻塞”，并出现 ARR 节省功耗 10-15% 的无来源数字。两节对 Rust/ARR 关系的描述不一致。
- **建议**：3.1 后续回炉时删除 Rust 直接支撑 ARR 的表述；改为引用 3.8 的边界：Rust InputFilter 主要处理键盘辅助功能 KeyEvent，触摸 ARR 走 user activity / Boost.INTERACTION / SurfaceFlinger Scheduler / FrameRate vote；功耗数字必须补来源或删除。

## [Task9 Deep Review] 3.8 InputFlinger Rust 组件与自适应刷新率协同 — 2026-05-16
- **类型**：源码锚点补强
- **位置**：src/part1-fundamentals/ch03-input/08-inputflinger-rust-arr.md:L155
- **问题**：正文说 PowerManagerService 发 `Boost.INTERACTION` 后 SurfaceFlinger 收到 `notifyPowerBoost()`，结论正确，但源码锚点缺少 native bridge：`PowerManagerService.setPowerBoostInternal()` 通过 `nativeSetPowerBoost()` 进入 `com_android_server_power_PowerManagerService.cpp::setPowerBoost()`，后者同时调用 Power HAL 和 `SurfaceComposerClient::notifyPowerBoost()`。
- **建议**：补两个锚点：`frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp` 与 `frameworks/native/libs/gui/SurfaceComposerClient.cpp`，避免读者误以为 Java `PowerManagerService` 直接调用 SurfaceFlinger。


## [Task6 Review] 3.8 InputFlinger Rust 组件与自适应刷新率协同 — 2026-05-16
- **类型**：需确认 / 源码准确性
- **位置**：桌面模式和外接输入设备的刷新率策略
- **问题**：Task9 已指出正文把 Sticky Keys、Bounce Keys、Slow Keys 的作用范围合并成 supported keyboard devices + `Source::KEYBOARD` 限制，存在源码准确性风险。Task6 不裁决技术真伪，已在正文加 `[存疑]`。
- **建议**：Task2B 按 queue.json `task9-3.8-sticky-keys-scope-20260516` 修正：Bounce / Slow Keys 与 Sticky Keys 分开描述，并保留 MotionEvent 不进入当前 Rust InputFilter 的边界。
- **review 日志**：logs/review/2026-05-16-13-review.md

## [Task9 Deep Review] 3.9 端到端输入延迟预算与感知阈值 — 2026-05-16
- **类型**：数据支撑/指标口径
- **位置**：L70-L82「一张预算表：从触摸到上屏」
- **问题**：表中 4-16ms、1-5ms、1-8ms、1-16ms 等预算值没有给出设备、刷新率、触控采样率、Trace 样本或 HCI 来源。虽然正文声明“不用于固定 SLO”，但这些数字仍会被读者当成通用经验阈值。
- **建议**：补 1 份同机 Perfetto/高速相机样本或公开资料出处；补不到时改成“按采样周期/刷新周期推导的估算范围”，并把 InputReader/InputDispatcher 阶段改为以 P50/P90 观察为主。

## [Task9 Deep Review] 3.9 端到端输入延迟预算与感知阈值 — 2026-05-16
- **类型**：数据支撑/HCI 引用边界
- **位置**：L87-L103「HCI 阈值和 Android 工程指标的换算」
- **问题**：2ms 级可感知、20-50ms、50-100ms 等阈值被整理成工程分层，但没有标注对应论文实验任务、设备、样本和交互类型。不同研究的 click、drag、stylus、touchscreen 条件不能直接合并成同一张阈值表。
- **建议**：给每个区间补来源脚注和适用条件；如果只作为产品排查启发，明确标为启发式分层，不要写成 Android 平台通用阈值。

## [Task9 Deep Review] 13.14 Perfetto DataGrid 与 Jank CUJ 标准库 — 2026-05-16
- **类型**：数据与案例支撑
- **位置**：L149-L175 / L220-L231 FrameTimeline + thread_state 联合分析与排障顺序
- **问题**：章节给出了 `android_jank_cuj_frame`、`thread_state`、`android_heap_graph_stats` 的排障顺序，但没有列出最小采集条件。缺少 `android.surfaceflinger.frametimeline`、sched/thread_state、CPU freq、Binder、gfx/view atrace、ART heap graph、DMA-BUF 等数据源的必选/可选边界时，示例 SQL 可能直接空表，读者无法判断是机制不适用还是 trace 缺采集。
- **建议**：补一个最小 TraceConfig / Perfetto UI recording preset checklist：逐项标明 CUJ counter、FrameTimeline、thread_state、GPU/HWC fence、heap_graph_stats、dmabuf 各自依赖的数据源；同时给一条“表为空时先检查什么”的排查清单。

## [Task6 Review] 20.1 应用稳定性全景 — 2026-05-16
- **类型**：需确认
- **位置**：ANR timeout 阈值表 / ANR 发生后的系统行为
- **问题**：Task6 复审确认正文仍保留 `[需确认]`：Android 14+ CPU-starved BroadcastReceiver timeout 版本口径与前台可见、后台、silent ANR 的弹窗/kill 边界未补齐。
- **建议**：按 Task9 技术结论和官方文档补齐版本、前后台和可见性边界；无法确认时降级为典型前台 ANR 场景并标注系统差异。
- **review 日志**：logs/review/2026-05-16-16-review.md

## [Task9 Deep Review] 11.5 Wakelock 机制与功耗分析 — 2026-05-16
- **类型**：源码准确性 / API 语义边界
- **位置**：`src/part2-performance/ch11-power/05-wakelock.md:L771-L773, L819-L823`
- **问题**：`setPreferPowerEfficiency(true)` 被写成系统会降低 CPU/GPU 频率、完整路径里也写成“系统调整 CPU/GPU 频率策略”。AOSP `PerformanceHintManager.Session#setPreferPowerEfficiency()` 注释只承诺“these threads can be safely scheduled to prefer power efficiency over performance”，是线程调度偏好，不是 CPU/GPU 降频保证。
- **建议**：改为“声明 hint session 关联线程可优先能效调度，具体是否迁移到效率核、降频或联动 GPU 由设备 Power HAL / scheduler 实现决定”；不要把 GPU 频率调整写成 API 直接语义。

## [Task2A Gap Mining] 2026-05-16 17:04 — 本轮未创建新章节

- **类型**：知识缺口挖掘记录
- **结论**：未发现去重后评分 ≥ 14 且适合独立成节的新缺口。
- **已检查方向**：ADPF Power Efficiency Mode + PowerMonitor、Android 版本化线上诊断能力、16KB Page Size 与 Hook / 三方 native 库、InputDispatcher / InputFlinger Rust / HCI 延迟、Perfetto SPAN_JOIN / DataGrid / Jank CUJ、WOOTdroid、McNdroid。
- **去重依据**：上述高分素材已被 3.7、3.8、3.9、4.7、5.9、8.10、11.1、11.5、13.11、13.14、14.11、26.5、26.9、26.10 等章节覆盖，或更适合作为 Task2B / Task6 的内容补强素材。
- **后续建议**：下轮缺口挖掘优先避开这些方向，除非出现新的官方 API、AOSP 入口或 ≥3 篇高质量独立素材支撑。

## [Task9 Deep Review] 2.3 VSync 机制 — 2026-05-16
- **类型**：数据缺失/Trace 支撑
- **位置**：6.3、9.5、10.1（Perfetto VSync 观察与 ARR 行为）
- **问题**：章节仍保留 `[待补充:Perfetto Trace 截图]`，ARR/刷新率切换部分也缺少可复核的 trace 或 dumpsys 样例。`VSYNC-app`/`VSYNC-sf` 周期变化、`HW_VSYNC` 重新采样、active mode / render rate 切换之间的对应关系没有数据支撑。
- **建议**：补一组 Android 15/16 设备上的 Perfetto + `dumpsys SurfaceFlinger` 样例：刷新率切换前后 VSYNC 间隔、phase/duration 配置、active mode/render rate、FrameTimeline expected present time；没有样例前避免写成确定的性能结论。

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-05-16
- **类型**：数据缺失/来源支撑
- **位置**：16KB Page Size、主流 Hook 库版本表与 Google Play 截止日期
- **问题**：章节列出 ByteHook/ShadowHook 版本、16KB `p_align`/compat mode、Google Play 2025-11-01 截止日期，但部分断言没有紧邻官方文档、release tag 或源码文件作为证据。
- **建议**：在该小节补官方 Android 16KB page-size 文档、ByteHook/ShadowHook release/CMakeLists、`linker_phdr_16kib_compat.cpp`、`readelf -l` 输出示例；若截止日期无法用官方来源复核，应降级为待验证。

## [Task9 Deep Review] 5.13 移动端 LLM 推理的 DVFS 与能效边界 — 2026-05-16
- **类型**：数据支撑 / Perfetto 采集口径
- **位置**：`src/part1-fundamentals/ch05-cpu-power/13-mobile-llm-dvfs-energy.md`「端侧 AI 推理的验证方法」TraceConfig 示例
- **问题**：正文说这段配置用于采集 Android 电源数据，但示例只设置了 `battery_poll_ms` 和 `collect_power_rails: true`，没有列出 `battery_counters`。Perfetto 官方样例中，电池电流/电压/电量计数器需要显式声明 `BATTERY_COUNTER_CURRENT`、`BATTERY_COUNTER_VOLTAGE`、`BATTERY_COUNTER_CHARGE` 等；`collect_power_rails` 只覆盖设备支持 ODPM/power rails 的路径。
- **建议**：如果目标是估算 energy-per-token，补齐 battery counters 或把示例语义收窄为“仅尝试采集 power rails”；同时说明外接功耗仪、power rails、电池计数器三种口径的优先级与误差边界。

## [Task9 Deep Review] 5.13 移动端 LLM 推理的 DVFS 与能效边界 — 2026-05-16
- **类型**：原理链 / Thermal 架构边界
- **位置**：`src/part1-fundamentals/ch05-cpu-power/13-mobile-llm-dvfs-energy.md`「DVFS governor 在 CPU、GPU、内存之间的独立决策」第一段
- **问题**：正文把 Thermal HAL 写成“把温度约束反馈给框架与内核”。Android Thermal HAL 的稳定职责更准确地说是向 framework thermal service 暴露温度、severity、cooling device 等状态/回调；实际限频、cooling device 生效通常在 kernel thermal framework、vendor thermal daemon 和 Power HAL/驱动策略侧完成。
- **建议**：改成“Thermal HAL 向框架暴露热状态与 cooling 信息，内核/vendor thermal 策略负责把温度约束落实到 cooling device、频率/功率限制”，避免读者误解为 HAL 直接向内核下发约束。

## [Task2A Gap Mining] 2026-05-16 20:04 — 无新章节创建
- **检查结论**：本轮未发现需要新建章节的知识缺口。评分 ≥14 的方向已被现有章节承接，适合进入回炉/补证据，而不是追加新小节。
- **已覆盖方向**：Android 17 Profiling Triggers → 8.10；端侧 AI 推理公开/preview 边界 → 5.11；Codec2 / tunneled playback / Media3 ABR → 8.8；Android 17 大屏 resizability/orientation → 2.20。
- **低分方向**：Android Studio Panda 内置泄漏检测、Android 恶意软件检测长期漂移、Android AI OS / Gemini API 趋势。低于 14 分，暂不创建章节。
- **后续建议**：`5.11`、`8.10`、`8.8` 按 Task 2B/Task 6 补源码、官方文档和版本边界证据。

## [2026-05-16 21:08] Task 2A 缺口挖掘：无新章节创建

本轮 Phase 0 未发现空 draft 章节。Phase 1 对 source-index 高分未映射素材、recent research-feeds、daily-info、research-gaps、AOSP / Android Developers 公开资料做了对照。

未创建新章节，原因如下：

- Perfetto v53/v54、SPAN_JOIN、Jank CUJ、Profile 导入等方向已由 13.8、13.11、13.12、13.14 承接。
- ProfilingManager / ProfilingTrigger / ApplicationExitInfo 版本边界已由 14.7、16.2、16.5、26.2、26.8、26.9、26.10 承接。
- BufferQueue dequeueBuffer 阻塞识别已由 2.13、2.16、7.15 承接。
- InputDispatcher 反压、InputFlinger Rust、输入延迟阈值已由 3.7、3.8、3.9 承接。
- ART Generational CMC / userfaultfd 已由 4.8 承接。
- McNdroid Android 恶意软件检测漂移基准偏安全研究，与本书性能优化主线相关性不足，未入队。

建议下一轮继续从 Android 17/18 官方性能行为变更和 Part 5 Clippings 未覆盖知识点中寻找真正独立的小节机会。

## [Task6 Review] 5.8 后台执行限制与优化 — 2026-05-16
- **类型**：需重写
- **位置**：源码调研补充（2026-04-27/04-28）与 AIW 注入标记附近
- **问题**：多段源码调研记录以时间戳和调研口吻直接进入正文，发布稿会显得像素材堆叠，影响主线阅读。
- **建议**：Task2B 将调研内容融合到“Android 16 的进程冻结流程”和“Binder Freezer Driver 协同机制”主线，删除编辑痕迹和重复调研标题。
- **review 日志**：logs/review/2026-05-16-23-review.md

## [Task6 Review] 5.9 ADPF 自适应性能框架 — 2026-05-16
- **类型**：需重写
- **位置**：源码调研补充（2026-05-01/05-07）与常见问题后半段
- **问题**：源码调研补充段落保留大量调研记录、版本修正和隐藏 API 说明，正文主线被素材块打断。
- **建议**：Task2B 先修 Task9 API/版本问题，再把可保留内容融合到 Performance Hint、Headroom、非游戏场景三个小节，删除调研记录口吻。
- **review 日志**：logs/review/2026-05-16-23-review.md

## [Task9 Deep Review] 5.14 Android 17 ML Runtime 与 NPU 访问边界 — 2026-05-17（Google Tensor / 厂商后端命名）
- **类型**：术语边界/来源边界
- **位置**：L63、L223-L231
- **问题**：正文同时出现 `QNN/Neuron`、`Google Tensor / EdgeTPU`。公开 LiteRT Next 页面当前写的是 Qualcomm AI Engine Direct、MediaTek NeuroPilot、Google Tensor SDK experimental access；“EdgeTPU”容易被理解成 Coral Edge TPU 或独立硬件路径，不应和 Pixel Tensor / Tensor ML SDK 混写。
- **建议**：把厂商后端统一改成 Qualcomm QNN / MediaTek NeuroPilot；Google 部分改为 “Google Tensor / Tensor ML SDK experimental access”，只有引用 Coral Edge TPU 文档时才使用 Edge TPU。

## [Task9 Deep Review] 26.11 eBPF 在线追踪与 Binder 语义重建 — 2026-05-17
- **类型**：数据缺失/来源路径
- **位置**：frontmatter sources；L94、L101、L191
- **问题**：`Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 6/13/35.md` 在当前 Obsidian `Clippings/` 下未找到，正文又把这些文件作为结构参考引用，导致相关判断无法复核到原始材料。
- **建议**：替换成实际存在的笔记路径，或把这些引用降级为非技术结构参考；与 eBPF/Binder 结论相关的依据保留论文、AOSP 文档和已有章节交叉引用。

## [Task2A Gap Mining] 2026-05-17 02:04 — 无新章节创建

- **检查结论**：Phase 0 未发现 `status: draft` 且正文实质内容 < 15 行的空草稿；Phase 1 未发现去重后评分 ≥ 14 且适合独立成节的新缺口。
- **已检查方向**：Android 17 ProfilingTrigger / memory limit anomaly、Android 17 desktop windowing / resizability、Android 17 lock-free MessageQueue / DeliQueue、16KB page size NDK 兼容、Perfetto v53/v54 SDK / pprof / DataGrid / Jank CUJ、WOOTdroid、Android Studio Panda 内置泄漏检测、AOSP packages/modules Wi-Fi / Bluetooth / Media 结构缺口。
- **去重依据**：上述方向已由 2.20、4.7、8.10、13.12、13.14、14.1、14.7、16.5、19.16、22.10、24.9、26.5、26.9、26.10 等章节承接，或更适合作为 Task2B / Task6 的证据补强素材。
- **低分方向**：Android Studio Panda 内置泄漏检测、Android AI OS / Gemini API 趋势、Android 恶意软件检测漂移基准与本书性能优化主线相关性不足，暂不创建章节。
- **后续建议**：下轮优先从官方 Android 17/18 性能行为变更、Part 5 Clippings 中尚未映射的实战知识点，以及 `packages/modules` 中与性能强相关但现有章节未覆盖的模块继续挖掘。

## [Task9 Deep Review] 1.20 App Archiving 机制与恢复性能 — 2026-05-17
- **类型**：交叉引用
- **位置**：frontmatter L11 / 正文 L88、L209
- **问题**：正文两次引用 4.2 Linux 内存回收，但 related_chapters 未列出 4.2；frontmatter 列出 16.2，正文版本表未显式回连 16.2。
- **建议**：补齐 related_chapters 与正文回跳：要么把 4.2 加入 related_chapters，要么减少正文引用；版本边界处建议显式回连 16.2。


## [Task6 Review] 1.20 App Archiving 机制与恢复性能 — 2026-05-17
- **类型**：需补充素材
- **位置**：「恢复链路的性能口径」开头与观测点表之前
- **问题**：章节已经拆出 Launcher 点击、ActivityStarter 归档分支、PackageArchiver、安装器、PackageInstaller session、恢复后首帧等环节，但缺少一张时序图或 Trace 对照说明。按 writing-guide.md，多组件交互和时序流程必须配图或 Trace 描述。
- **建议**：Task2B 先修 Task9 已登记的两个 P1 技术问题，再补一张“点击归档图标 → 归档分支 → 安装器恢复 → session commit → 首帧”的时序图，并在图后解释对应的 logcat / Perfetto 观察点。
- **review 日志**：logs/review/2026-05-17-05-review.md

## [Task9 Deep Review] 26.12 Android 版本化线上诊断能力：ApplicationExitInfo、ProfilingManager 与 ProfilingTrigger — 2026-05-17
- **类型**：源码准确性 / API 常量命名
- **位置**：L217、L221、L261 ProfilingTrigger 常量表
- **问题**：表格使用 `APP_REQUEST_RUNNING_TRACE`、`KILL_FORCE_STOP`、`KILL_RECENTS`、`KILL_TASK_MANAGER`、`APP_COMPAT`、`KILL_EXCESSIVE_CPU_USAGE`、`ANOMALY` 等短名；公开 API 常量全名是 `TRIGGER_TYPE_*`。
- **建议**：统一改成完整常量名，或在表头明确说明已省略 `TRIGGER_TYPE_` 前缀。

- **类型**：版本差异 / 接入边界
- **位置**：L219、L225 `TRIGGER_TYPE_OOM`
- **问题**：官方文档要求自定义 `Thread.UncaughtExceptionHandler` 必须继续调用默认 handler，否则 OOM trigger 不能生效；正文只写了 Java OOM 与 LMK 的区别。
- **建议**：在 OOM 行补接入前提，并和 8.10 / 14.7 的同类说明保持一致。

- **类型**：原理链 / Extension 36.1
- **位置**：L217 Extension 36.1 行；L253-L261 排障决策表
- **问题**：`TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE` 实际由 `ProfilingManager#requestRunningSystemTrace(String tag)` 触发，并要求先注册该 trigger 才能收到结果；当前只写“App 请求”，缺少入口方法和注册前提。
- **建议**：补 `requestRunningSystemTrace(tag)` 与 `TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE` 的关系，并区分它和 Android 15 `requestProfiling(PROFILING_TYPE_SYSTEM_TRACE)`。



## [Task14 参考书扫描] 23.6 大内存与多进程策略 — 2026-05-17
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些"黑科技"优化手段.md]
- **建议补充**：释放 WebView 预留虚拟内存的完整方案（32位设备可回收约130M）。方案1：Android 10+ 通过解析 /proc/self/maps 中 anon:libwebview reservation 获取首尾地址后 munmap；方案2：Android 9 以下通过 PLT Hook webviewchromium_loader.so 的 android_dlopen_ext，从 android_dlextinfo 结构体中提取 gReservedAddress 和 gReservedSize，然后 munmap。方案2 需要在 Native 层通过 JNI 反射调用 WebViewLibraryLoader.nativeLoadWithRelroFile 来触发 hook 点。微信已在线上验证此方案。
- **参考书覆盖深度**：深入（含完整代码流程和版本兼容方案）

## [Task14 参考书扫描] 23.6 大内存与多进程策略 — 2026-05-17
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（下）：一些"黑科技"优化手段.md]
- **建议补充**：释放 ART 虚拟机备份栈空间（main space 1，约512M）的方案。仅适用于 Android 5-7（ART 使用拷贝回收 GC）。原理：ART 创建 main space 和 main space 1 供 HomogeneousSpaceCompact 使用，通过主动调用 GetPrimitiveArrayCritical 而不调用 ReleasePrimitiveArrayCritical，使 disable_moving_gc_count_ 维持为1，禁用拷贝回收 GC，然后 munmap 未使用的那块 main space。抖音已在线上验证，OOM 率未升高。
- **参考书覆盖深度**：深入（含 AOSP 源码级分析，heap.cc PerformHomogeneousSpaceCompact 流程）

## [Task14 参考书扫描] 25.6 APK 体积分析与瘦身 — 2026-05-17
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md]
- **建议补充**：国内市场多 dpi 资源去重策略——只保留市占率最高的 xxhdpi 一套资源，低 dpi 手机通过系统自动缩放适配。海外市场通过 AAB 按设备 dpi 下发。这一策略在参考书中有完整的 dpi 概念解释和换算公式（px = dp * (dpi / 160)）以及各 dpi 级别对照表。
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 25.6 APK 体积分析与瘦身 — 2026-05-17
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md]
- **建议补充**：assets 目录资源压缩策略——音频、HTML、JS、数据文件等 assets 资源使用 7z 压缩（压缩率优于 zip），运行时通过 7z SDK（LZMA）解压使用。7z SDK 为开源库，可通过 NDK 编译集成。此外，低频 assets 资源可通过埋点统计使用频率后改为网络按需下载。
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] 25.7 R8 与资源优化 — 2026-05-17
- **类型**：内容补充
- **来源**：[结构参考: Clippings/Android 性能优化 - 资源文件的体积优化实战.md]
- **建议补充**：resources.arsc 二进制文件结构详解——6个 Chunk 数据段（RES_TABLE_TYPE 头部、RES_STRING_POOL_TYPE 字符串常量池、RES_TABLE_PACKAGE_TYPE 资源头、资源类型/名称字符串池、RES_TABLE_TYPE_SPEC_TYPE 类型规范、RES_TABLE_TYPE_TYPE 资源类型项）。参考书给出完整的 Kotlin 解析示例代码，引用 AOSP ResourceTypes.h 数据结构。理解此结构是图片去重（修改字符串常量池索引）和文件名混淆的技术基础。推荐开源工具 android-chunk-utils（Java）和 resourcesAnalyzer（Kotlin）。
- **参考书覆盖深度**：深入（含完整文件结构图和解析代码）

## [Task9 Deep Review] 13.16 Agent 辅助 Perfetto 分析协议 — 2026-05-17
- **类型**：来源路径/证据可复查性
- **位置**：frontmatter sources L18-L32；正文 L82、L112、L140；本地 source path
- **问题**：sources 使用 DeepResearch/... 相对路径，但该目录不在 Android-Internal-Wiki 根目录下；实际文件位于 Obsidian/DeepResearch/android-skills-profilers/...。当前路径从项目根解析会失败，影响已验证材料复查。
- **建议**：改成可解析的绝对路径，或统一成相对 Obsidian vault 根的约定并在项目规范中说明；至少把本节引用的两个 SKILL.md 和深度调研文件路径修正。

- **类型**：标准库模块名/SQL 可执行性
- **位置**：L148 stdlib 优先规则
- **问题**：表格写 android.startup、android.frames 作为“优先查”的模块名，容易被照抄成 INCLUDE PERFETTO MODULE android.frames；实际常用入口是 android.startup.startups、android.frames.timeline / android.frames.per_frame_metrics 等具体模块。
- **建议**：把这一行改成具体 include 示例，并说明 android.frames 是 package 名，不是可直接 include 的模块名。

- **类型**：交叉引用/目录一致性
- **位置**：src/part3-tools/ch13-perfetto/README.md “本章内容”
- **问题**：第 13 章 README 仍只列到 13.10，未纳入 13.11-13.16；本节已引用 13.15，但读者从章节入口无法发现本节和相邻新增章节。
- **建议**：更新 ch13 README 的本章内容和 related_chapters，补齐 13.11-13.16，并把 13.16 放到 13.10 SQL 与 13.15 BufferQueue 案例之后。



## [Task9 Deep Review] 4.3 ART 虚拟机内存管理 — 2026-05-17
- **类型**：数据缺失
- **位置**：L309-L324、L527-L545 GC pause / throughput / normal-vs-abnormal baseline
- **问题**：Young GC 1-3ms、Pause 1-5ms、GC 吞吐量 >98%/95%、Young GC 每 2-5 秒一次等基线缺设备、collector、刷新率、堆上限、采样窗口和 trace 样本。
- **建议**：补一组 Perfetto/GC log 样例，明确 Android 版本、collector、heap 上限、场景和刷新率；补不齐时把这些数值标为示例阈值，要求读者按业务基线重定。

## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-05-17
- **类型**：数据缺失 / 来源边界
- **位置**：L279、L293-L301、L455-L470 Periodic/Chained Work 开销与 excessive partial wake locks policy
- **问题**：周期/链式 Work 的“几十毫秒”“几十到几百毫秒”缺 WorkManager 版本、设备、数据库规模、任务数量和 trace 采样方法；WakeLock policy 段落没有给出可追溯 URL，且 24h/background/FGS/screen-off 与 beta/正式执行口径需要统一。
- **建议**：补 AndroidX WorkManager microbenchmark 或 trace；补 developer.android.com excessive-wakelock 与 Google blog 原文 URL。无数据时把调度开销改为定性描述。

## [Task9 Deep Review] 20.6 稳定性度量与指标体系 — 2026-05-17
- **类型**：来源路径
- **位置**：frontmatter sources、L115、L126 Android Vitals 文档
- **问题**：`support.google.com/googleplay/android-developer/answer/9844476` 当前不可访问；可验证页面是 `answer/9844486`，其中包含 user-perceived ANR/crash thresholds 与 input dispatching timed out 口径。
- **建议**：把来源 URL 改为 `https://support.google.com/googleplay/android-developer/answer/9844486`，并在引用处补 28 天窗口、overall/per-device threshold。

## [Task6 Review] 2.10 GPU 渲染深入 — 2026-05-17
- **类型**：需补充素材
- **位置**：实战案例：社交应用图片滚动中的 GPU 瓶颈定位
- **问题**：正文仍保留 [需补充素材] 标注；案例包含设备、帧耗时、帧率和优化收益，但缺真实 Perfetto/AGI 截图、采样条件或匿名复现说明。
- **建议**：补一手 Trace/AGI 证据与测试条件；如果只是示意案例，改成“示例场景”并删除固定收益数值。
- **review 日志**：logs/review/2026-05-17-12-review.md

## [Task6 Review] 20.6 稳定性度量与指标体系 — 2026-05-17
- **类型**：需补充素材
- **位置**：“行业参考值”“行业对标参考”两张表
- **问题**：正文仍保留 [需补充素材] 标注；“微信公开分享”“头部电商”等对标值缺具体出处，且容易被读者当成公开事实。
- **建议**：补公开演讲、官方文档或内部指标口径；补不到则删公司名和确定数值，改成匿名经验区间并标注适用边界。
- **review 日志**：logs/review/2026-05-17-12-review.md


## [Task9 Deep Review] 7.6 案例集 — 2026-05-17
- **类型**：数据缺失
- **位置**：L107-L569 多个案例的 Trace、耗时区间与效果对比
- **问题**：正文多处已标注“待验证”，但案例集的核心数值仍缺 trace 文件名、设备型号、Android 版本、刷新率、采样窗口、样本次数和统计口径。
- **建议**：发布前为每个案例至少归档一份可复核 trace/截图或把数值统一降级为“示例口径”，避免读者把 8-12ms、Jank 率 12%→3%、CLIENT 合成 6-10ms 等数字当成实测结论。

## [Task9 Deep Review] 8.2 App 启动全流程 — 2026-05-17
- **类型**：数据缺失
- **位置**：L624-L626 Zygote Preload 的贡献
- **问题**：正文写“Zygote preload 覆盖 80% 以上的类加载需求”，但未给出设备、Android 版本、类加载统计方法或官方来源；该数值容易被当成通用事实。
- **建议**：补基于 class loading trace / ART log / AOSP preload 列表的统计口径；补不到时删除 80% 数值，改成定性描述“覆盖大量 framework 常用类与资源”。

## [Task9 Deep Review] 14.1 Android Studio Profiler — 2026-05-17
- **类型**：数据缺失 / 来源口径
- **位置**：L195 `profileable` 相比 `debuggable` 约 28% 性能提升
- **问题**：正文把“28% 性能提升”写成 Google 测试数据，但本节参考资料没有给出对应 release note、benchmark 场景、设备、指标或链接。该数值会直接影响读者选择 profiling 构建类型。
- **建议**：补 Android Studio / Android Developers 原始出处和测试条件；若来源实际是 Koala Profiler 任务启动速度“up to 60% faster”等其他指标，应改成正确对象；补不齐则删除 28% 数值，只保留 profileable 低扰动的定性判断。


## [Task9 Deep Review] 13.3 Perfetto View 解读 — 2026-05-17
- **类型**：源码准确性
- **位置**：Counter Track（约第 238 行）
- **问题**：正文把 Counter Track 的 Java 侧来源写成 `Trace.traceCounter()`；在 AOSP android-16.0.0_r1 中该方法是 `@hide` / `@SystemApi(client = MODULE_LIBRARIES)`，普通 App 可用的公开入口是 `Trace.setCounter(String, long)`。
- **建议**：改成“App 侧用 `Trace.setCounter()`，平台/系统模块可见 `Trace.traceCounter()`，native 侧用 `ATRACE_INT` / `ATRACE_INT64`”，避免读者按隐藏 API 写示例。

## [Task9 Deep Review] 13.3 Perfetto View 解读 — 2026-05-17
- **类型**：版本差异
- **位置**：FrameTimeline Track（约第 201 行）
- **问题**：正文列举 `Jank Type` 时使用空格化名称，并把 `Dropped Frame` 与 jank type 并列；Perfetto 官方 FrameTimeline 文档中的类型名是 `AppDeadlineMissed`、`BufferStuffing`、`SurfaceFlingerCpuDeadlineMissed`、`SurfaceFlingerGpuDeadlineMissed`、`DisplayHAL`、`PredictionError`，蓝色 Dropped frame 明确标注为“Not related to jank”。
- **建议**：保留中文解释，但在括号中补官方枚举名；把 Dropped frame 单独放到“帧状态/颜色”说明里，不作为 `Jank Type` 枚举。

## [Task6 Review] 2.18 Adaptive Refresh Rate 与动态帧率控制 — 2026-05-17
- **类型**：需重写/素材整合
- **位置**：参考资料后的 DeepResearch 卡片与“附录：RefreshRateSelector 多维度评分算法”
- **问题**：该段仍是调研素材堆放/重复卡片，破坏参考资料收束；Task9 已标记其中的 FrameTimeline SQL、RefreshRateSelector 源码路径和 ARR 决策层归属风险。
- **建议**：Task2B 在 Task9 技术口径修正后，只保留可验证内容并融入“系统里谁在做什么 / SurfaceFlinger 怎样做刷新率选择”，删除重复 DeepResearch 卡片和 AIW 注入标记。
- **review 日志**：logs/review/2026-05-17-20-review.md

## [Task6 Review] 17.2 SoC 平台差异 — 2026-05-17
- **类型**：需重写/素材整合
- **位置**：常见问题之后的 AIW 源码调研补充与 Game Mode 素材块
- **问题**：该段仍是加工记录式素材块，未融入正文叙述；Task9 已标记 Dimensity vendor 路径和 sched_ext OEM 名称证据风险。
- **建议**：Task2B 在 Task9 技术复核后，把可用内容整合进“厂商调度策略差异”或“与其他机制的关系”，不可验证的 vendor 路径/OEM 名称降级为待验证或移出正文。
- **review 日志**：logs/review/2026-05-17-20-review.md

## [Task9 Idle Audit] 21.8 启动监控与度量 — 2026-05-17
- **类型**：源码引用 / 官方文档链接新鲜度
- **位置**：frontmatter `sources` L15-L16
- **问题**：`https://developer.android.com/topic/performance/appstartup` 当前返回 404；同一文档族的 `appstartup/analysis-optimization` 与 `appstartup/best-practices` 可访问。frontmatter 继续保留父路径会让后续复核无法定位官方证据。
- **建议**：把父路径替换为 `https://developer.android.com/topic/performance/appstartup/analysis-optimization`，如需最佳实践再补 `https://developer.android.com/topic/performance/appstartup/best-practices`；`vitals/launch-time` 继续保留用于 TTID 与 Vitals 阈值。

## [Task9 Deep Review] 20.2 Java Crash 治理 — 2026-05-18
- **类型**：源码准确性 / 异常类型边界
- **位置**：L104 `KillApplicationHandler` 通知 AMS 失败路径
- **问题**：正文把 “Binder buffer 已满或 AMS 异常” 归为 `DeadObjectException`。AOSP android-16.0.0_r1 `RuntimeInit.KillApplicationHandler` 是 `catch (Throwable t2)`，其中 `DeadObjectException` 只是 system_server 死亡时的特殊分支；其他 Binder/AMS 异常会进入日志记录后再执行 `finally` 杀进程。
- **建议**：改成“`handleApplicationCrash()` 可能抛 `RemoteException` / 运行时异常；`DeadObjectException` 只代表系统进程死亡场景，其他异常会被 RuntimeInit 记录后进入 kill 流程”。

## [Task9 Deep Review] 20.2 Java Crash 治理 — 2026-05-18
- **类型**：数据缺失
- **位置**：L154 Top 5 覆盖 80%+、L272 第三方 SDK crash 20-30%
- **问题**：两个比例会直接影响治理优先级判断，但正文只标注“待验证/待补充”，缺公开报告、业务样本窗口、App 类型、版本范围和统计口径。
- **建议**：补内部 crash 平台统计或公开稳定性报告；补不齐时把数值降级为“示例/常见经验”，并保留业务差异边界。



## [Task6 Review] 5.8 后台执行限制与优化 — 2026-05-18
- **类型**：需确认 / 版本差异
- **位置**：`16KB 页环境下的 GC 联动压缩`；版本演进 Android 17 行
- **问题**：Task9 2026-05-18 已指出该段把 GC/compaction 写成 Android 16/17 引入并绑定 16KB 页收益，缺少官方或源码锚点；本轮 Task6 已在正文加 `[存疑]` 标注，但不裁决技术口径。
- **建议**：Task2B 回炉时改成 Android 14+ cached app freezer 的 GC / compaction 配套机制；若确有 Android 16/17 或 16KB 专属增强，补 source.android / AOSP commit / CachedAppOptimizer 或 ART runtime 锚点。
- **review 日志**：logs/review/2026-05-18-02-review.md

- **类型**：需重写
- **位置**：`Android 16 的进程冻结流程` / `BINDER_FREEZE ioctl` / `Binder Freezer Driver 协同机制`
- **问题**：本轮只做了 L1/L2 小修，删除可见 AIW 注入标记并把调研口吻改成正文口吻；该区域仍是多个源码调研块串接，内容重复，主线会被实现细节打断。
- **建议**：Task2B 按“cached 进程进入 freezer → Binder 冻结 → cgroup.freeze → FrozenStateChangeCallback / RemoteCallbackList 策略”合并成一条叙述线，ioctl 结构体和 commit 细节只保留对排查有用的最小片段。
- **review 日志**：logs/review/2026-05-18-02-review.md

## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-05-18
- **类型**：源码准确性 / 原理边界
- **位置**：L178 `16KB Page Size` 与 fork/COW 描述
- **问题**：段落把 16KB 页导致 PTE/page-table 规模下降，进一步写成 “fork 期间需要遍历和复制的 VMA 链表条目减少”。VMA 数量由 `mmap` 区间决定，page size 不会直接减少 VMA 条目；`dup_mmap` 遍历 VMA 与复制 page table 是不同成本项。
- **建议**：改成“16KB 页减少 PTE/page-table 规模，可能降低页表相关开销和 TLB 压力”；同时补充边界：VMA 数量不因 page size 变化，COW 粒度增大也可能带来小对象/dirty page 放大。

## [Task9 Audit] 3.6 手势识别算法与性能优化 — 2026-05-18
- **类型**：源码准确性/版本差异
- **位置**：VelocityThreshold：Fling 判定的速度门槛
- **问题**：正文只摘了 `ViewConfiguration.MINIMUM_FLING_VELOCITY = 50` / `MAXIMUM_FLING_VELOCITY = 8000` 常量，容易让读者以为运行时阈值只由 Java 常量决定。Android 10-16 的实际构造路径会读取 `config_viewMinFlingVelocity` / `config_viewMaxFlingVelocity` dimen，Android 14+ 还提供 `getScaledMinimumFlingVelocity(inputDeviceId, axis, source)` / `getScaledMaximumFlingVelocity(...)`，对 `SOURCE_ROTARY_ENCODER` 会走 `config_viewMinRotaryEncoderFlingVelocity` / `config_viewMaxRotaryEncoderFlingVelocity`，默认 `-1dp` 表示不支持 fling。
- **建议**：把 Fling 阈值段落改成“fallback 常量 → framework config dimen → device overlay → Android 14+ inputDevice/axis/source overload”的层次，避免和 TouchSlop 段落的资源/overlay 解释不一致。

---

## [Task2A 缺口挖掘检查] 2026-05-18 05:15
- **结论**：本轮未发现评分 ≥ 14 且尚未覆盖的新增章节缺口，跳过新章节创建。
- **Phase 0**：`src/` 中 `status: draft` 章节数为 0；无空 draft 可加工。
- **已检查方向**：
  1. Android 17 App memory limits / `MemoryLimiter` / `TRIGGER_TYPE_ANOMALY`：已在 4.1、4.4、8.10、14.14、16.5、26.12 等章节覆盖，不作为新小节创建。
  2. Android 17 后台音频强化：已在 1.16、5.8、16.5 等章节覆盖，不作为新小节创建。
  3. Agent 辅助 Perfetto / `android/skills/profilers` / SmartPerfetto：13.16 已创建并成稿，不作为新小节创建。
  4. `ApplicationStartInfo` 启动归因：26.13 已创建并成稿，8.2/26.12 已交叉覆盖。
  5. ADPF Hint Session 与 Kotlin 协程线程迁移：25.11 已创建，8.6/5.9 已覆盖。
  6. Jetpack Telecom VoIP 原生可见性、Wear OS 跨设备发现、KMP 默认模块结构：与本书性能优化主线相关性不足，本轮评分未达 14。
  7. Intent-Driven Storage Systems 论文：存储调优思路有参考价值，但 Android 落地证据不足；本轮记录为观察方向，暂不创建章节。
  8. SELinux.isEnforced 机制：偏系统安全/调试链路，性能相关性不足，本轮评分未达 14。
- **建议**：下一轮优先继续从 `daily-info/2026-05-18.md` 和 Android 17 官方文档中筛选“已有官方 API/行为变更 + 尚无 AIW 小节”的主题，避免重复创建已覆盖章节。



## [Task14 参考书扫描] 4.1 Android 内存模型全景 — 2026-05-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：LPDDR RAM 特性与演进（LPDDR3→LPDDR4→LPDDR4X 带宽/功耗对比），手机 vs PC 内存差异（低功耗、体积约束），"内存越大越好"误区（需考虑 LPDDR 代际而非单纯容量）
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] 4.3 ART 虚拟机内存管理 — 2026-05-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：NativeAllocationRegistry 机制详解——如何同时满足"Native 内存分配+对象关联快速释放+GC 感知防滥用"三需求；Hardware Bitmap 减少内存并提升绘制效率
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 19.24 崩溃与ANR捕获机制 — 2026-05-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 2.md]
- **建议补充**：Breakpad 技术细节——重新封装 Linux Syscall Support 避免直接调 libc；fork 子进程/孙进程隔离策略；minidump 格式优缺点（含 gdb 调试、传参等高级特性）；Crashpad 作为继任者的定位
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 14.3 内存分析工具 — 2026-05-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：AS Allocation Tracker 三个缺点（信息分散、无法自动化、stop时卡死）及自定义 Allocation Tracker 思路；Android P+ Malloc 钩子（拦截所有分配/释放）；Android 8.0+ 非root Malloc 调试（wrap.sh）；AddressSanitize 在 Android 8.0+ 的使用
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 10.4 低内存对系统性能的影响 — 2026-05-18
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：内存问题的两类影响——异常（OOM/分配失败/被杀/重启）和卡顿（Java堆不足→频繁GC、物理内存不足→lmk→系统负载高）；"2GB以下设备崩溃率是2GB以上的数倍"的经验数据；ART vs Dalvik GC 性能提升 5-10 倍对比
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] 23.02 Bitmap与图片内存优化 — 2026-05-18
- **类型**：版本更新
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **过时内容**：Fresco 在 Android 5.0-7.0 通过 libandroid_runtime.so 构造 Native Bitmap 再"偷龙转凤"的黑科技方案（兼容性差、易内存抖动）
- **建议更新至**：Android 8.0+ 已通过 NativeAllocationRegistry 原生支持 Native Bitmap，无需此 hack；建议标注为"历史方案"或移除

## [Task14 参考书扫描] 多章节 — 2026-05-18
- **类型**：版本更新
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 1~4.md]
- **过时内容**：2018年设备数据（Mate 20 Pro 8GB作为高端标杆、512MB设备描述）、"Google Play 2019年8月要求64位"、Crashpad "too early to mobile"（现已成熟）
- **建议更新至**：更新为 2025-2026 年主流设备内存基准（8-16GB）；Google Play 64位要求已成历史；Crashpad 已被广泛采用


## [Task2A 知识缺口检查] 2026-05-18 08
- **类型**：知识缺口挖掘记录
- **结论**：未发现评分 ≥ 14 且尚未覆盖的新增章节缺口；本轮不创建新小节。
- **已检查方向**：Android 17 MemoryLimiter / excessive resource usage、Compose Pausable Composition、Android 16 云编译与 SDM、Android 17 DeliQueue + RecyclerView 预取、OkHttp Dns.lookup / HTTPDNS、MTE ASYMM memtagMode、SmartPerfetto / Agent 辅助 Perfetto。
- **处理建议**：上述方向均已有对应章节，后续进入 Task2B/Task14 补充或回炉即可，避免重复建节。


## [Task2A Gap Scan] 2026-05-18 09:04 — 无新增章节
- **类型**：知识缺口挖掘记录
- **检查范围**：src/SUMMARY.md、metadata/source-index.json、intake/research-feeds 最近 5 个文件、intake/daily-info 最近 3 天、research-gaps.md、AOSP/Android Developers 公开页面搜索
- **结果**：未发现评分 ≥ 14 且尚未被章节覆盖的新增小节缺口。
- **已覆盖但素材仍可用于回炉的方向**：Perfetto v53/v54、ApplicationStartInfo/ProfilingTrigger、Android 17 DeliQueue、Codec2/tunneled playback、Android 16 SDM/Cloud Compilation、OkHttp Dns、Compose Pausable Composition、sched_ext/EEVDF、MTE ASYMM。
- **建议**：本轮不创建新章节；后续由 Task 2B/Task 9 消化已有章节的证据补强项，避免重复建章。

## [Task2A Gap Scan] 2026-05-18 10:04 — 无新增章节
- **类型**：知识缺口挖掘记录
- **Phase 0**：`src/` 中未发现 `status: draft` 且正文实质内容 < 15 行的章节。
- **检查范围**：`src/SUMMARY.md`、`metadata/source-index.json` 高分未映射素材、`intake/research-feeds/` 最近 5 个文件、`intake/daily-info/` 最近 3 天、`intake/research-gaps.md`、Android 17 官方 behavior/features/release notes 搜索、AOSP 模块搜索。
- **结果**：未发现评分 ≥ 14 且尚未被章节覆盖的新增小节缺口，本轮不创建新章节。
- **已覆盖但可进入 Task2B/Task14 的方向**：Android 17 App memory limits / `MemoryLimiter:AnonSwap`、`ProfilingTrigger.TRIGGER_TYPE_ANOMALY`、Reduced Wakelocks for Idle Alarms、Perfetto v53/v54、SmartPerfetto / Agent 辅助 Perfetto、ApplicationStartInfo、Codec2 / tunneled playback / Media3 ABR、Compose Pausable Composition、Android 17 DeliQueue、MTE ASYMM、OkHttp Dns / HTTPDNS。
- **处理建议**：继续由 Task2B/Task9 修复已有章节证据与版本边界；Task2A 暂不重复建章。

## [Task6 Review] 9.5 案例集 — 2026-05-18

- **类型**：需确认

- **位置**：案例 4「进程冻结导致 Gesture Monitor 无法响应」版本边界段

- **问题**：Task9 已指出 Android 15+ 活跃 Input 连接冻结豁免、am_cached_process_freeze_status 日志口径，以及 Cached Apps Freezer 引入版本仍缺 AOSP 证据。Task6 不裁决技术真伪，只在正文加风险标记并保留回炉。

- **建议**：Task2B 按 Task9 queue 条目补 AOSP / OEM 分支证据，必要时改为 Android 11+ freezer 基线 + Android 14+ robust 行为，并把 OEM 策略单独标注。

- **review 日志**：logs/review/2026-05-18-12-review.md


## [Task6 Review] 19.13 androidx.tracing（Tracing SDK） — 2026-05-18

- **类型**：需确认

- **位置**：「AndroidX Tracing compat 行为」与版本差异表

- **问题**：Task9 已指出 traceAsync 起始版本、API 28 及以下 compat 实现、TraceEventCache 说法存在源码/版本风险。Task6 只追加风险标记，不改写技术结论。

- **建议**：Task2B 按 AndroidX Tracing 1.0/1.2/1.3 源码与 release note 重新核对版本表，删除未证实的 TraceEventCache 表述。

- **review 日志**：logs/review/2026-05-18-12-review.md


## [Task6 Review] 19.23 网络 APM 底层捕获原理 — 2026-05-18

- **类型**：需确认

- **位置**：指标模型「Response 接收」阶段

- **问题**：Task9 已指出 OkHttp responseBodyEnd 代表应用消费/关闭 ResponseBody 的边界尚未说明，可能把应用侧慢消费误归因到网络接收。Task6 只追加风险标记，不裁决指标口径。

- **建议**：Task2B 补 responseBodyStart/responseBodyEnd 的 OkHttp 语义边界，必要时拆分网络下载、应用消费、流式响应口径。

- **review 日志**：logs/review/2026-05-18-12-review.md



## [Task2A Gap Mining] 2026-05-18 13:04
- **类型**：知识缺口巡检记录
- **检查范围**：空 draft、source-index 高分未映射素材、research-feeds 最近 5 条、daily-info 最近 3 天、官方性能文档与 AOSP 结构方向
- **结论**：本轮未发现评分 ≥ 14 的新章节候选，未创建新章节。
- **已评估但未建节**：
  - SmartPerfetto 两周更新 / AI Trace 分析平台：已由 13.16「Agent 辅助 Perfetto 分析协议」覆盖，建议后续补充到现有章节。
  - App Performance Score 与 Vitals 质量建议：与 26.7「发版质量门禁」重合，建议 Task2B 回炉 26.7 时补官方链接 `https://developer.android.com/topic/performance/app-score`。
  - Android 16 power management resource limits / Job 配额：已由 1.8、5.10、11.x 覆盖。
  - Performance Class / Media Performance Class：19.21 已作为设备分层口径提及，暂不独立建节。
  - RK3562 Android 平板 Linux 工作站与 NPU 推理：更偏硬件改造/端侧 AI 资讯，暂不纳入 AIW 新章节。
- **报告**：`OpenClaw定时任务/知识加工/2026-05-18-13-知识加工(新).md`


## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-05-18
- **类型**：版本差异/源码准确性
- **位置**：L218 多显示 Pacesetter / FrameTargeter 段落
- **问题**：正文写 `composite()` “可能按 display 并行触发”，并说 Perfetto 主线程能看到按 display 分组的 commit/composite slice。AOSP android-16.0.0_r1 的 `SurfaceFlinger::composite(PhysicalDisplayId, const FrameTargeters&)` 是收集多个 output 后调用一次 `mCompositionEngine->present(refreshArgs)`；未见 SF 主路径按 display 并行触发的源码依据。Perfetto 中可能出现 CompositionEngine/output 级别信息，但不应写成主线程 commit/composite 按 display 并行。
- **建议**：改为“Android 15+ 使用 `FrameTargeter`/`FrameTargets` 为不同 physical display 计算目标；`composite()` 在一次 refreshArgs 中携带多个 output，分析时按 display/output 区分”，删除“并行触发”或补具体源码/trace 证据。

## [Task9 Deep Review] 5.3 大小核架构 — 2026-05-18
- **类型**：数据缺失/版本边界
- **位置**：L154 骁龙 8 Elite capacity≈837 / 18% 级差
- **问题**：`Performance 核 capacity≈837、Prime 核 1024、级差约 18%` 缺少设备 kernel `cpu_capacity` 输出、厂商公开资料或实机 trace 锚点。该数值可能来自单机型估算，不能直接写成骁龙 8 Elite 通用事实。
- **建议**：补目标设备 `/sys/devices/system/cpu/cpu*/cpu_capacity`、kernel DT/EM 或公开技术资料；补不到时改成“Prime 与 Performance 核仍有 capacity 级差，但远小于传统小核/大核差距”的定性描述。

## [Task6 Review] 5.3 大小核架构 — 2026-05-18
- **类型**：需补充素材
- **位置**：扩展：GPU + NPU 的协同调度概念
- **问题**：该扩展仍只有一条占位式 `[需补充素材]`，缺少任务卸载策略、GPU/NPU 在异构计算中的角色，以及这些任务对 CPU 调度影响的可靠素材，当前不能作为成稿小节。
- **建议**：Task2B 补充可靠素材后再决定保留、合并到 §5.11，或删除该扩展，避免空壳扩展留在发布稿。
- **review 日志**：logs/review/2026-05-18-16-review.md


## [Task2A Gap Mining] 2026-05-18 16:17 — 无新增章节
- **类型**：知识缺口巡检记录
- **检查范围**：空 draft 章节（0 个）、`src/SUMMARY.md`、`metadata/source-index.json` 高分未映射素材、`intake/research-feeds/` 最近 5 条、`intake/daily-info/` 最近 3 天、`intake/research-gaps.md`、Android Developers 官方性能/版本文档搜索、AOSP Code Search 方向搜索。
- **结论**：本轮未发现评分 ≥ 14 且尚未覆盖的新增章节候选，未创建新小节。
- **已覆盖但可进入 Task2B/Task14 的方向**：
  - App Performance Score / Android Vitals：官方文档已可补 26.7「发版质量门禁」、26.3「性能指标采集与上报」、15.5「线上性能监控」，不单独建章。
  - Android 17 `ProfilingManager` triggers、`TRIGGER_TYPE_ANOMALY`、OOM / excessive CPU 触发：已由 26.12、14.7、19.16、5.10、16.5 覆盖，后续只需补版本边界和官方链接。
  - Android 16/17 power management resource limits、JobScheduler / WorkManager quota：已由 5.10、25.4、11.x 覆盖，不重复建章。
  - Perfetto v53/v54 Data Explorer、Jank CUJ、pprof / Simpleperf、heap_graph_stats：已由 13.12、13.14、13.17 等章节覆盖，作为回炉素材处理。
  - SmartPerfetto / Agent 辅助 Trace 分析平台：已由 13.16「Agent 辅助 Perfetto 分析协议」覆盖。
  - Clippings 新增参考书知识点（Breakpad、ANR 监控、崩溃现场信息、Bitmap 版本演进、Allocation Tracker）：对应 ch20、ch23、ch26 的内容补强，不构成新章节。
- **处理建议**：本轮不创建章节；后续由 Task2B/Task14 消化上述补充项，避免重复建节。

## [Task9 Idle Audit] 9.7 ANR 非技术故障诊断 — 2026-05-18
- **类型**：源码锚点 / 版本差异
- **位置**：frontmatter sources / lines 40、116、334：InputDispatcher.cpp 路径
- **问题**：frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp 在 Android 11+ 标签存在；Android 8.1/10.0 的路径是 frameworks/native/services/inputflinger/InputDispatcher.cpp。正文引用明确标注 android-16，技术结论可用，但 applicable_versions 覆盖 Android 8-17，参考资料处缺少旧版本路径提示。
- **建议**：参考资料或脚注补一句：Android 8-10 请查 services/inputflinger/InputDispatcher.cpp，Android 11+ 查 services/inputflinger/dispatcher/InputDispatcher.cpp。


## [Task9 Deep Review] 2.14 图形 API 演进与选择策略 — 2026-05-19
- **类型**：原理边界/数据缺失
- **位置**：L270、L329-L345、L355
- **问题**：Command Buffer 复用被直接套到 Android View 静态 UI；ADPF thermal/headroom 信号与 ANGLE driver 选择的关系写成策略耦合；WebGPU 计算管线“开销比例较低”缺 Dawn/WebGPU benchmark 或官方实现证据；OpenGL ES driver“自动调整 GPU 频率”容易混淆 driver 与 PowerHAL/DVFS 职责。
- **建议**：把 Command Buffer 复用限定在自管 Vulkan renderer；ADPF 只作为热/功耗降级信号，不写成 ANGLE 选路依据；WebGPU 性能判断补设备/workload/库版本，补不到则改为定性边界；GPU 调频改为系统 DVFS/PowerHAL/driver hint 协同。

## [Task9 Deep Review] 2.13 图形缓冲区管理 (BufferQueue) — 2026-05-19
- **类型**：源码表述/观测口径
- **位置**：L303、L327、L416
- **问题**：`BufferQueueCore` 被标为“可跨进程共享”容易被读成共享内存对象；实际应强调 core 位于创建端进程，跨进程的是 producer/consumer Binder 端点与 native handle/fence。Perfetto slice/counter 名称也受 Android 版本和厂商 producer 影响，当前缺一组真实 trace 或 trace config 佐证。
- **建议**：把架构图注释改为“producer/consumer 可跨进程访问同一队列语义，core 不作为共享内存暴露”；Perfetto 小节补目标版本的 trace config、SQL 表名或截图，避免把 slice/counter 名称写成无条件稳定接口。

## [Task9 Deep Review] 20.5 OOM 治理 — 2026-05-19
- **类型**：源码准确性/术语边界
- **位置**：L328、L92
- **问题**：`mallopt(M_PURGE, 1)` 中 value 在 bionic `malloc.h` 注释里为 ignored，官方示例常写 `mallopt(M_PURGE, 0)`；`growth limit` 来源写成 ActivityManager 通过 processinfo 配置也偏粗，应回到 Zygote/Runtime heap 参数与 `largeHeap`/系统属性边界。
- **建议**：将示例改成 `mallopt(M_PURGE, 0)` 并标注只影响 RSS/dirty page；`growth limit` 改为“由进程启动时传入 ART 的 heap 参数决定，受设备配置与 largeHeap 影响”。

## [Task9 Idle Audit] 10.1 App 内存分析 — 2026-05-19
- **类型**：版本差异
- **位置**：line 279「Android 8.0 之前 Bitmap 像素数据存储在 Java Heap」
- **问题**：Android 官方 Bitmap 内存文档把历史分为三段：API 10 及以下 pixel data 在 native memory；API 11-25 在 Dalvik heap；API 26+ 在 native heap。当前“Android 8.0 之前”覆盖过宽，会把 API 10 及以下历史行为写错。
- **建议**：改为“API 11-25 的 Bitmap 像素数据在 Dalvik/ART heap；API 26+ 回到 native heap；API 10 及以下历史机型另行说明或直接标注不在本书适用版本范围内。”

## [Task 2A Gap Scan] 2026-05-19 02:04
- **模式**：Phase 1 知识缺口挖掘；未发现 `status: draft` 且正文实质内容 < 15 行的章节。
- **结论**：本轮未发现评分 ≥14 且尚未被目录覆盖的新章节候选，不创建章节。
- **已检查方向**：
  1. Scudo / native allocator 深挖：已有 4.6、20.11、23.3、14.3 覆盖，新增内容更适合回炉补强，不单独建节。
  2. ADPF Power Efficiency Mode / PowerMonitor：已有 5.9、11.5、14.11、25.11 覆盖，且部分已有 Task9 回炉记录，不单独建节。
  3. ApplicationExitInfo 低版本替代方案：已有 26.9、26.10、26.12、19.24 等覆盖，不单独建节。
  4. Android 17 NPU / LiteRT / AICore：已有 5.11、5.14、5.13 覆盖，不单独建节。
  5. Codec2 / tunneled playback / Media3 ABR：已有 8.8 覆盖，不单独建节。
  6. Perfetto v54 Data Explorer / Jank CUJ / heap_graph_stats：已有 13.14、13.12 覆盖，不单独建节。
  7. Android 17 ProfilingManager triggers / excessive CPU / OOM：已有 8.10、14.7、16.5、26.12 覆盖，不单独建节。
  8. Kernel 6.12 statsd/logd sendfile zero-copy、Microdroid Linux terminal：与当前 Android 性能优化主线相关性不足或素材支撑不足，评分未达 14。
- **后续处理**：上述方向若出现新的官方源码证据或真实案例，进入 Task 2B 回炉或对应章节扩展点，不重复创建新章节。

## [Task6 Idle Audit] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 2026-05-19
- **类型**：需确认
- **位置**：参考资料之后的 `<!-- AIW-源码调研-2026-05-07 -->` 块
- **问题**：该块位于参考资料之后，未纳入 outline 十个锚点覆盖范围；同时包含 Android OEM sched_ext 调度器源码路径、性能收益和 GKI 版本演进等具体断言。Task6 不裁决技术真伪，但该位置与内容形态不适合直接留在 finalized 发布稿。
- **建议**：Task9 先核实源码路径、版本边界与性能收益来源；Task2B 再决定删除、迁移到 sched_ext 正文，或作为待验证素材保留。
- **review 日志**：logs/review/2026-05-19-05-audit.md

## [Task2A Gap Mining] 本轮未创建新章节 — 2026-05-19 05
- **类型**：知识缺口挖掘记录
- **结论**：未发现评分 ≥14 且未被现有章节覆盖的新缺口。
- **检查范围**：source-index 高分未映射条目 116 个、research-feeds 最近 5 个文件、daily-info 最近 3 天、AOSP 结构对照、Android Developers 性能文档对照。
- **已检查方向**：
  - Perfetto SDK / SmartPerfetto / Data Explorer（来源：source-index 高分未映射）→ 已有 13.17、13.18、13.14 覆盖
  - BufferQueue 阻塞、HWC2、RenderEffect、AGSL、AnimatedVectorDrawable（来源：source-index 高分未映射）→ 已有 13.15、2.6、22.10、22.11、18.x 覆盖
  - 16KB Page Size、MTE、Native Crash、ApplicationExitInfo（来源：source-index 高分未映射）→ 已有 4.7、20.13、20.11、26.9、26.10、26.12 覆盖
  - MessageQueue / DeliQueue / RecyclerView 协同（来源：source-index 高分未映射）→ 已有 1.13、7.8、16.5 覆盖
  - Android 多媒体 Codec2 / tunneled playback / Media3 ABR（来源：source-index 高分未映射）→ 已有 8.8 覆盖
  - Android 17 ML Runtime / LiteRT / AICore / NPU（来源：source-index 高分未映射）→ 已有 5.11、5.14 覆盖
  - Android Studio Panda LeakCanary Profiler、ApplicationStartInfo、ProfilingTrigger（来源：daily-info 最近 3 天）→ 已有 14.1、14.14、26.12、26.13 覆盖
  - Improve performance / R8 / memory profiler / app-driven profiling（来源：官方文档对照）→ 已有 25.7、14.1、14.7、19.16 覆盖
  - BiometricService、TelephonyManager 等系统服务（来源：AOSP 结构对照）→ 与当前性能主线相关性不足且素材少，评分未达 14
- **后续建议**：下一轮优先查看新增 source-index 与 daily-info；本轮列出的方向不重复创建章节，除非后续出现新的官方文档、AOSP 源码证据或实测材料。



## [Task14 参考书扫描] 10.1 App 内存分析 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 5.md]
- **建议补充**：线上内存监控指标体系 — PSS异常率(>400MB的UV/采集UV)、触顶率(Java堆>85%最大堆限制的UV/采集UV)的具体定义和计算公式；GC监控通过Debug.getRuntimeStat("art.gc.blocking-gc-count/time")获取阻塞式GC次数和耗时
- **参考书覆盖深度**：中等（含具体阈值和代码示例，但部分API如Debug.startAllocCounting已deprecated）
- **过时风险**：Debug.startAllocCounting已标记deprecated，建议用Debug.getRuntimeStat替代

## [Task14 参考书扫描] 4.5 App 内存优化 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 5.md]
- **建议补充**：设备分级策略实践模式 — device-year-class按内存/CPU核数/频率分级，低端机关闭复杂动画/使用RGB_565/缩小缓存；统一缓存管理+OnTrimMemory回调按状态释放；安装包大小与内存占用的量化关系表；APK轻量版策略（Facebook Lite/今日头条极速版）
- **参考书覆盖深度**：概述（提供了框架性思路，但设备分级以2010-2013年标准举例，已过时）
- **过时风险**：device-year-class的年份分级标准基于2013年设备，当前应改为基于内存+SoC能力分级

## [Task14 参考书扫描] 10.2 内存泄漏 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 5.md]
- **建议补充**：Hprof文件裁剪优化技巧 — 裁剪大部分Bitmap对应的byte数组（100MB→30MB），7zip压缩后<10MB增加上传成功率；重复Bitmap像素数据检测方案（通过Hprof分析工具自动输出重复图片和引用链）；美团Probe组件OOM时生成Hprof快照（需注意二次崩溃风险）
- **参考书覆盖深度**：中等（含具体数据但未深入实现细节）
- **过时风险**：Probe的OOM快照方案在高版本有兼容性风险

## [Task14 参考书扫描] 7.3 卡顿分析方法论 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 6.md]
- **建议补充**：/proc文件系统卡顿分析参考 — /proc/[pid]/stat中utime/stime/majorFaults/minorFaults字段含义；/proc/[pid]/sched中nr_voluntary_switches/nr_involuntary_switches/iowait_count/iowait_sum用于分析上下文切换；CPU使用率>60%需关注用户/系统时间比例，系统时间>30%需排查IO/锁/系统调用
- **参考书覆盖深度**：中等（含具体字段和阈值判断标准）

## [Task14 参考书扫描] 15.5 线上性能监控 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md]
- **建议补充**：线上卡顿监控三代方案演进对比 — 第一代Looper Printer（字符串拼接性能差）；第二代监控线程空消息探针（1秒间隔，3秒卡顿在第4次轮询确认）；第三代编译时插桩（Matrix方案，包体积增1-2%，帧率降2帧以内）；Facebook Profilo方案（SIGPROF+ManagedStack unwind，近乎零性能损耗但兼容性风险）
- **参考书覆盖深度**：深入（含方案演进思路、性能数据和兼容性评估）

## [Task14 参考书扫描] 15.3 性能指标体系 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 7.md]
- **建议补充**：冻帧率定义与计算 — 连续丢帧>700ms（42帧+）为冻帧，冻帧率=冻帧时间/总时间；按Activity/Fragment/操作细化场景帧率；UV卡顿率(发生卡顿UV/采集UV)评估影响面，PV卡顿率(卡顿PV/启动采集PV)评估严重度
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 15.5 线上性能监控 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md]
- **建议补充**：卡顿树聚合方法 — 对超3秒卡顿抛弃具体耗时，按相同堆栈出现比例聚合为树结构，从全盘视角看Top卡顿问题的各分支；比传统堆栈聚合更适合十万级日志量的分析
- **参考书覆盖深度**：概述（提供了思路但未深入算法实现）

## [Task14 参考书扫描] 9.3 ANR 分析方法 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md]
- **建议补充**：主动获取ANR级日志的三种方法 — 1)Java层Thread.getState+getAllStackTraces获取线程状态和堆栈（Android 7.0不返回主线程堆栈）；2)主动发送SIGQUIT信号触发系统生成traces.txt（高版本无读取权限）；3)fork子进程+libart.so Hook调用ThreadList::ForEach+Thread::DumpState获取完整线程信息（"无损"方案，子进程崩溃不影响主进程）
- **参考书覆盖深度**：深入（含完整方案对比和兼容性分析）

## [Task14 参考书扫描] 14.13 Hook 基础设施 — 2026-05-19
- **类型**：版本更新
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 8.md]
- **过时内容**：Profilo快速获取Java堆栈功能不支持Android 8.0和9.0（2018年数据）
- **建议更新至**：核实Profilo/Facebook后续版本是否已支持Android 8-16的快速堆栈获取，或推荐使用Android 8.0+ JVMTI机制作为替代方案

## [Task14 参考书扫描] 5.1 Linux 进程调度基础 — 2026-05-19
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 6.md]
- **建议补充**：线程优先级对卡顿的影响 — nice+cgroup共同决定调度策略，高优先级线程空等低优先级线程锁（如主线程等后台线程）是常见卡顿模式；uptime命令load average应控制在0.7×核数以内
- **参考书覆盖深度**：概述


## [Task9 Deep Review] 4.8 ART 分代垃圾回收与 GC 暂停优化 — 2026-05-19
- **类型**：数据缺失
- **位置**：L619-L620 附录「对 Compose 性能的影响」
- **问题**：`young GC pause 低（10-50ms）`、`old GC pause 高（100-500ms）` 缺少设备、collector、负载、trace 样本和统计口径；同时正文前面使用 1-3ms/1-5ms 的 pause 口径，两组数字没有解释差异。
- **建议**：删除具体区间，或补充可复现实验条件和 Perfetto/ART 日志证据；若只是调研材料原文，应标注为待验证素材，避免进入正文结论。

## [Task9 Deep Review] 8.2 App 启动全流程 — 2026-05-19
- **类型**：数据缺失
- **位置**：L639「Zygote preload 的贡献」
- **问题**：`Zygote preload 覆盖了 80% 以上的类加载需求`、`如果每次都从零加载所有类，这个时间会翻好几倍` 缺少统计口径、Android 版本、设备样本和测量方法。
- **建议**：改成定性描述，或补充基于 preloaded-classes / arrays.xml 与真实启动 trace 的统计；没有数据前不要保留 80% 与“翻好几倍”的量化判断。


## [Task2A Gap Mining] 2026-05-19 12:04 — 无新增章节
- **结论**：未发现评分 ≥ 14 且尚未被目录或回炉队列覆盖的新增章节缺口。
- **已检查方向**：Android 17 ProfilingManager / ProfilingTrigger / Panda Profiler；Cached App Freezer + GC/compaction；DMA-BUF / Gralloc / 16KB 图形内存边界；DeliQueue + RecyclerView；Android 桌面模式；Android 17 侧载/应用认证。
- **处理理由**：前五项已被现有章节或 Task9/Task2B 队列覆盖，适合作为回炉补证据，不应重复创建新小节；侧载/应用认证与性能主线相关性不足，低于创建阈值。
- **日志**：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/知识加工/2026-05-19-12-知识加工(新).md`


## [Task9 Deep Review] 19.13 androidx.tracing（Tracing SDK） — 2026-05-19
- **类型**：版本差异/API 口径
- **位置**：L237、L246「AndroidX Tracing compat 行为 / 版本差异表」
- **问题**：正文已经把 pre-29 fallback 方法名修正为 `android.os.Trace.asyncTraceBegin/asyncTraceEnd`，但 1.2.0 的 lazy overload 仍写成 `trace(name) { }` / `traceAsync(name, cookie) { }`，容易让读者把 1.0.0 已存在的 eager string overload 误认为 1.2.0 新增能力。AndroidX 1.2.0 源码中新增的是 lambda 形式：`trace(lazyLabel: () -> String, block)` 与 `traceAsync(lazyMethodName: () -> String, lazyCookie: () -> Int, block)`。
- **建议**：把表述改成“1.2.0 新增 lambda 形式的 lazy label/cookie 重载”，并在必要时给出 `trace({ buildName() }) { ... }` / `traceAsync({ buildName() }, { cookie }) { ... }` 的示意，避免把普通字符串调用误写成 lazy。

## [Task9 Deep Review] 19.13 androidx.tracing（Tracing SDK） — 2026-05-19
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters`、L206-L217「和 btrace、Perfetto SDK 的区别」
- **问题**：正文已经把 `androidx.tracing` 与 Perfetto SDK 做边界区分，但 `related_chapters` 只列出 `19.0`；目录中已有 `13.17 Perfetto SDK 与应用内 Trace 数据源` 和 `13.9 Android Tracing 基础设施`。缺少交叉引用会让读者在 19.13 里寻找 Perfetto SDK producer / backend / data source 细节。
- **建议**：在 `related_chapters` 或工具边界段补 `13.17`（必要时补 `13.9`），并注明“Perfetto SDK 自定义 data source / in-process tracing 详见 13.17”。

## [Task9 Deep Review] 8.2 App 启动全流程 — 2026-05-19
- **类型**：交叉引用一致性 / 工程边界
- **位置**：L540 与 L630 App Startup / ContentProvider 边界
- **问题**：前文正确说明 App Startup 无法自动接管未适配的三方 ContentProvider，但后文又写可通过 App Startup 手动初始化模式接管已经通过 ContentProvider 初始化的第三方 SDK。官方 App Startup lazy initialization 只适用于已声明为 Initializer 的组件；未适配 SDK 的自有 provider 需要 manifest 排除、SDK 配置或等待 SDK 适配。
- **建议**：改成“已接入 App Startup 的 Initializer 可移除 meta-data 后手动 lazy initialize；未适配的三方 ContentProvider 不能被 App Startup 直接接管，只能通过 provider 移除/SDK 配置/延迟显式初始化处理”。

## [Task9 Deep Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-05-19
- **类型**：示例鲁棒性 / 数据支撑
- **位置**：L425 / L450-L456 Camera 启动拆解脚本
- **问题**：正文提示 `CameraHal::openSession` 是 Qualcomm vendor-specific，缺失时用 `connectDevice` 兜底；但 Python 示例无条件查询 vendor slice 并读取 `values[0]`，非高通或无 vendor slice 的 trace 会空表越界。
- **建议**：脚本按 `connectDevice` / vendor `openSession` 两级查询并补空结果判断；无法定位 vendor slice 时降级输出 AOSP 通用阶段。


## [Task9 Deep Review] 10.1 App 内存分析 — 2026-05-19
- **类型**：版本差异
- **位置**：L290-L294 / Bitmap 内存管理的关键变化
- **问题**：正文写“Android 8.0 之前 Bitmap 像素数据存储在 Java Heap”，遗漏官方分段：API 10 及更低在 native memory，API 11-25 在 Dalvik heap，API 26+ 回到 native heap。
- **建议**：把历史说明拆成 API ≤10、API 11-25、API 26+ 三段；本章适用 Android 8+ 时重点写 API 26+ 对 dumpsys/MAT 观察口径的影响。

## [Task9 Deep Review] 10.1 App 内存分析 — 2026-05-19
- **类型**：源码准确性
- **位置**：L476-L478 / 常见误区二
- **问题**：“Native 内存耗尽了 Java Heap 的预算空间”把 native 内存压力与 Java heap class 混在一起。Native 泄漏通常表现为进程 RSS/PSS/Private Dirty 增长、malloc 失败、系统内存压力或 LMK/OOM 路径，不是消耗 Java heap 预算。
- **建议**：改为“Native 内存会推高进程总内存与系统压力，可能触发 malloc 失败、native OOM、LMK 或进程被杀；Java heap 上限仍由 ART heap 预算单独约束”。

## [Task2A Gap Mining] 本轮未创建新章节 — 2026-05-19 23:04
- **类型**：知识缺口扫描记录
- **结论**：本轮未发现评分 ≥14 且未被现有章节覆盖的新增小节，跳过新章节创建。
- **已检查方向**：
  - 空 draft：`src/` 下未发现 `status: draft` 且正文实质内容 <15 行的章节；`metadata/progress.json` 当前 `draft=0`。
  - 高分素材：`metadata/source-index.json` 中 16 分以上素材多已映射到现有章节；重点复核了 WOOTdroid/eBPF、MediaCodec/Codec2 tunneled playback、Android Studio Panda LeakCanary、Hybrid/WebView 能耗、Android 17 MessageQueue、SurfaceFlinger FrontEnd、ADPF 协程线程迁移等方向，均已有对应章节或正在 Task2B/Task9 管线中。
  - 近期素材：`intake/research-feeds/` 最近 5 篇、`intake/daily-info/` 最近 3 天中的 Perfetto v53/v54、FrameTimeline、Compose Pausable Composition、View 层级、Android 17 适配、桌面窗口化等主题已被 2.4、7.12、13.x、14.14、16.5、22.3、22.14、26.12 等章节覆盖。
  - 官方/AOSP 对照：ProfilingManager 触发式采集、ApplicationStartInfo、Android 16/17 FGS/JobScheduler 行为、StorageStatsManager/installd quota、Media tunneling 等方向均已有主章节覆盖；本轮只记录，不拆新节。
- **下次建议**：优先从未被 source-index 正确映射的 AOSP 模块继续扫，例如 `vold`/`netd`/`installd` 的实战诊断边界；只有在现有章节无法容纳时再创建新节。

## Task2A 缺口挖掘记录 · 2026-05-20 00:11

- 结论：本轮未发现评分 ≥ 14 且未被现有章节覆盖的新增小节候选。
- Phase 0：`src/` 内 `status: draft` 且正文实质内容 < 15 行的章节为 0。
- 已检查方向：
  - `metadata/source-index.json` 高分素材：DeliQueue / MessageQueue、Android 17 App Memory Limits、WOOTdroid、ApplicationExitInfo legacy、16KB Page Size、AnimatedVectorDrawable、FragmentTransaction、RenderEffect、PowerMonitor 等高分素材均已映射到现有章节或已被正文覆盖。
  - 最近 `intake/daily-info/`：Android Studio Panda、Android 17 MessageQueue、Android 17 适配、桌面窗口化、Cached App Freezer、DMA-BUF/Gralloc 16KB、Perfetto DataGrid/Jank CUJ、Generational CMC、sched_ext/EEVDF 均已有对应章节或队列项。
  - 最近 `intake/research-feeds/`：Perfetto v53/v54、Frame Timeline、Compose Pausable Composition 等均已有 13.x / 22.3 / 2.4 等章节承接。
  - 官方文档/AOSP 方向：Android 17 behavior changes、MessageQueue guidance、App memory limits、Power / performance docs 已有 1.13、16.5、23.9、14.11、25.11 等章节覆盖。
- 下轮建议：优先等待 Task 2B / Task 9 清理既有 pending 队列；若继续挖掘，避开 Android 17 MessageQueue、App Memory Limits、ProfilingTrigger、WOOTdroid、16KB Page Size 这些已覆盖主题，改从官方文档中新发布且 `SUMMARY.md` 没有对应标题的 topic 入手。

## [Task9 Idle Audit] 12.2 网络性能优化 — 2026-05-20
- **类型**：源码引用/资料锚点
- **位置**：§网络性能指标，验证标注（原 L104）
- **问题**：`developer.android.com/reference/okhttp3/EventListener` 返回 404；OkHttp EventListener 官方文档在 Square 站点，例如 `https://square.github.io/okhttp/5.x/okhttp/okhttp3/-event-listener/`。
- **建议**：把验证标注改成 Square OkHttp EventListener 文档；Android Developers 只保留 Android 平台 API，例如 `ConnectivityManager` / `NetworkCapabilities`。



## [Task2A Gap Mining] 本轮未创建新章节 — 2026-05-20 05:13
- **类型**：知识缺口挖掘记录
- **结论**：未发现评分 ≥14 且未被现有章节覆盖的新缺口。
- **检查范围**：source-index 高分未映射条目 92 个、research-feeds 最近 5 个文件、daily-info 最近 3 天、AOSP 结构对照、Android Developers 性能文档对照。
- **已检查方向**：
  - SmartPerfetto / Perfetto SDK / Data Explorer → 已有 13.14、13.17、13.18 覆盖。
  - Android 17 MessageQueue / DeliQueue → 已有 1.13、16.5 覆盖，适合回炉校验。
  - Android 16/17 桌面窗口化、大屏 resize 与多窗口 → 已有 2.20、18.18、22.14、17.6 覆盖。
  - Android Studio Panda、Memory Profiler、LeakCanary Profiler → 已有 14.1、14.3、14.14 覆盖。
  - Scudo / native allocator / GWP-ASan → 已有 4.6、20.11、23.3、14.3、19.24 覆盖，适合 Task 2B 或 Task 9 回炉。
  - ProfilingManager 系统触发、Android 17 performance triggers → 已有 8.10、14.7、19.16、26.12 覆盖。
  - Android Bench、AI 写 Android、Skills、Gemini API 接入 → 与 Android 性能优化主线相关性不足，评分未达 14。
  - Linux Dirty Frag、Linux CVE、AI 漏洞报告治理 → 偏 Linux 安全与行业治理，缺少 Android 性能优化落点，评分未达 14。
  - BiometricService、TelephonyManager 等系统服务 → 可找到 AOSP 入口，但性能案例和读者需求支撑不足，评分未达 14。
- **落盘报告**：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/知识加工/2026-05-20-05-知识加工(新).md`
- **后续建议**：下一轮优先查看新增 DeepResearch、source-index 增量和 daily-info；上述方向若无新增官方证据或真实案例，不重复创建章节。


## [Task2A Gap Mining] 本轮未创建新章节 — 2026-05-20 06:04
- **类型**：知识缺口挖掘记录
- **结论**：未发现评分 ≥14 且未被现有章节或 Task2B/Task9 队列覆盖的新缺口。
- **检查范围**：空 draft 章节（0 个）、`src/SUMMARY.md`、`metadata/source-index.json` 16 分以上未映射/弱映射素材、`intake/daily-info/` 最近 3 天、`intake/research-feeds/` 最近 5 个文件、`intake/research-gaps.md`、Android Developers / Source.android.com 官方文档。
- **已检查方向**：SmartPerfetto / Perfetto SDK / Data Explorer、Android 17 MessageQueue / DeliQueue、Android Studio Panda / LeakCanary Profiler、Android 16/17 桌面窗口化、16KB Page Size / Scudo / GWP-ASan、ApplicationExitInfo / ApplicationStartInfo / ProfilingManager / ProfilingTrigger、Android 17 NPU / LiteRT / AICore、Codec2 / tunneled playback、sched_ext / OEM BPF、Cached App Freezer + GC。上述方向均已有对应章节或回炉队列承接。
- **未达阈值方向**：Android Bench / AI 写 Android / Skills / Gemini API 接入、Android 17 侧载与应用认证、Linux Dirty Frag / CVE / AI 漏洞报告治理、BiometricService / TelephonyManager 等系统服务。主要原因是与 Android 性能优化主线相关性不足、素材支撑不足或已被近期 Task2A 记录判定不建节。
- **落盘报告**：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/知识加工/2026-05-20-06-知识加工(新).md`
- **后续建议**：下一轮优先查看 source-index 增量和新增 DeepResearch；无新增官方证据或实测材料时，不重复扫描上述已覆盖方向。


## [Task14 参考书扫描] 21.01 启动全链路分析 — 2026-05-20
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md]
- **建议补充**：启动4阶段模型（T1预览窗口→T2闪屏→T3主页→T4可操作）及3个核心体验问题的分析框架
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] 21.08 启动监控与度量 — 2026-05-20
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]
- **建议补充**：线上监控指标体系（快开慢开比/P90/启动类型区分）、实验室视频录制+图像识别方案、Facebook Profilo 启动堆栈对比方案
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 21.09 启动优化案例集 — 2026-05-20
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 9.md]
- **建议补充**：微信合并闪屏Activity减少100ms、按需拉起进程优化3%-8%、线程池+DAG编排防主线程空转案例
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] 24.01 文件I/O优化 — 2026-05-20
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 11.md]
- **建议补充**：Linux I/O全链路架构图（VFS→文件系统→Page Cache→块层→调度→驱动）、闪存写入放大原理与fstrim缓解、文件损坏三视角分析
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] 24.01 文件I/O优化 — 2026-05-20
- **类型**：版本更新
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 11.md]
- **过时内容**：eMMC/UFS 2.0/2.1 闪存标准对比（2018年数据），文中提到 LPDDR5/UFS 3.0 "即将在2019年面世"
- **建议更新至**：当前主流 UFS 4.0/4.1 标准，eMMC 市场占比已极低可降级为历史背景

## [Task14 参考书扫描] 24.01 文件I/O优化 — 2026-05-20
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 12.md]
- **建议补充**：标准I/O/直接I/O/mmap三种方式对比与适用场景、多线程I/O实验数据、小文件系统设计（微信SFS）
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] 26.03 性能指标采集与上报 — 2026-05-20
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 13.md]
- **建议补充**：I/O线上监控四规则（主线程I/O/Buffer过小/重复读/资源泄漏）、Native Hook vs Java Hook方案对比、Matrix I/O Canary实现
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] 21.04 Baseline Profile — 2026-05-20
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 10.md]
- **建议补充**：类重排+资源重排作为 Baseline Profile 的历史前身和技术对照（ReDex Interdex → Android Baseline Profile）
- **参考书覆盖深度**：中等

## [Task9 Deep Review] 19.16 ProfilingManager — 2026-05-20 — 错误码、限流和重试策略
- **类型**：数据缺失/限流模型
- **位置**：错误码、限流和重试策略
- **问题**：官方 Profiling limitations 文档说明 app/system 两层 limiter 都按 profile type cost 计费，并有 per hour / per day / per week 三个窗口；正文只给出错误码处理，缺少预算模型。
- **建议**：补一段 cost 模型和三层窗口，说明不同 profile type 消耗不同，命中任一窗口都会返回 RATE_LIMIT_PROCESS 或 RATE_LIMIT_SYSTEM。

## [Task9 Deep Review] 19.16 ProfilingManager — 2026-05-20 — frontmatter sources 与参考资料 #4
- **类型**：交叉引用/资料链接
- **位置**：frontmatter sources 与参考资料 #4
- **问题**：https://developer.android.com/topic/performance/profiling-manager 当前返回 404；官方文档已拆到 /topic/performance/tracing/profiling-manager/overview、/how-to-capture、/trigger-based-capture、/retrieve-and-analyze、/will-my-profile-always-be-collected。
- **建议**：替换旧 URL，并按 app-driven / trigger-based / retrieval / limitations 拆成多条参考资料。

## [Task9 Deep Review] 17.4 sched_ext 与 OEM BPF 调度器 — 2026-05-20 — frontmatter sources / 可观测与验证方法
- **类型**：源码锚点补充
- **位置**：frontmatter sources / 可观测与验证方法
- **问题**：正文引用 Android common include/linux/sched/ext.h 与 sysfs state/root/ops/enable_seq，但 sources 未列 include/linux/sched/ext.h；验证清单也可补 switch_all、nr_rejected、hotplug_seq。
- **建议**：补 Android common include/linux/sched/ext.h 链接，并在命令清单中加入 /sys/kernel/sched_ext/switch_all、nr_rejected、hotplug_seq。

## [Task9 Deep Review] 17.4 sched_ext 与 OEM BPF 调度器 — 2026-05-20 — Android 17 之后会默认启用吗：OPPO 相关 scx tracepoint / symbol list
- **类型**：证据不足
- **位置**：Android 17 之后会默认启用吗：OPPO 相关 scx tracepoint / symbol list
- **问题**：“OPPO 相关 scx tracepoint / symbol list 线索”未给具体路径、commit、symbol 名，读者无法复核。
- **建议**：补具体证据；不能补时删掉该句或改为“公开证据不足”。


## [Task 2A Gap Mining] 2026-05-20 09:13 — 无新章节创建

- **结论**：本轮未发现评分 ≥ 14 且尚未被 AIW 章节或回炉队列覆盖的新知识缺口。
- **Phase 0**：`src/` 下 `status: draft` 且正文实质内容 < 15 行的章节数量为 0。
- **检查范围**：`src/SUMMARY.md`、`metadata/source-index.json`、最近 5 个 `intake/research-feeds/`、最近 3 天 `intake/daily-info/`、`intake/research-gaps.md`、`metadata/queue.json`、官方 Android 17 文档与 AOSP Code Search 检索。
- **已检查方向**：
  1. Android 17 JobScheduler excessive CPU / ProfilingTrigger KILL_EXCESSIVE_CPU_USAGE → 已有 5.10、26.12 承接，且 queue.json 已有 Power Check/ProfilingTrigger 回炉项；不新建。
  2. Android 16 SDM / Cloud Compilation 安装链路 → 已有 1.9、16.6 以及多条 Task2B 勘误/回炉记录；现阶段作为证据口径复核，不新建。
  3. SmartPerfetto 可复用 Trace 分析平台 → 已有 13.18；本轮日报素材作为回炉素材，不新建。
  4. Perfetto DataGrid / Jank CUJ / 第三方 App 适用范围 → 已有 13.14 与回炉队列；不新建。
  5. Android 17 桌面窗口化、orientation/resizability 限制变化 → 已有 2.20、18.18、22.14；不新建。
  6. Android 17 DeliQueue / MessageQueue → 已有 1.13、7.8、队列回炉项；不新建。
  7. Android Studio Panda / Memory Profiler / LeakCanary Profiler → 已有 14.1、14.3、14.14，并有素材注入队列；不新建。
  8. Cached App Freezer + GC / DMA-BUF + Gralloc + 16KB Page / ART Generational CMC → 已有 4.11、2.24、4.8 等章节或回炉队列；不新建。
  9. ADPF Power Efficiency Mode / PowerMonitor → 已有 5.9、11.5、14.11、25.11 覆盖，且已有回炉建议要求收窄 GameManager/ADPF 口径；不新建。
  10. Android 17 NPU / LiteRT / AICore 端侧 AI 推理 → 已有 5.11、5.14；不新建。
- **后续建议**：继续由 Task2B/Task9 处理已有章节中的源码口径、版本边界和待验证标注；Task2A 下轮优先从尚未进入 SUMMARY 的新官方性能 API 或新的 AOSP 模块结构变化中找缺口。

## [Task2A Gap Scan] 本轮无新增章节 — 2026-05-20 10:04
- **类型**：知识缺口挖掘记录
- **结论**：本轮未发现评分 ≥14 且未被现有章节覆盖的新增小节候选。
- **已检查方向**：
  1. 空 draft 扫描：`src/` 中 `status: draft` 数量为 0，`metadata/progress.json` 中 `draft=0`。
  2. 最近研究素材：`Perfetto v53/v54` 已对应 `13.12`、`13.14`、`13.17`；`Compose Pausable Composition` 已对应 `7.7`、`22.3`、`18.2`；`View hierarchy measure/layout` 已对应 `7.12`、`22.1`。
  3. 最近每日信息：`Android 17 ProfilingTrigger` 已覆盖 `8.10`、`14.7`、`19.16`、`26.12`；`Cached App Freezer + GC` 已覆盖 `4.11`；`DMA-BUF/Gralloc 16KB` 已覆盖 `2.15`、`13.15` 与相关 16KB 章节；`sched_ext/EEVDF` 已覆盖 `17.4`。
  4. 官方文档检查：Android 17 features/release notes 中的 `COLD_START`、`OOM`、`KILL_EXCESSIVE_CPU_USAGE` trigger 已在 `26.12` 和 `19.16` 形成版本边界说明。
  5. AOSP/模块结构检查：本轮看到的候选主要落在已有章节点位；`ConnectivityService/netd`、`SensorService`、`statsd`、`cached app freezer`、`PackageInstaller/SDM` 等已有对应章节。
- **低于录入线的候选**：
  - Android Studio Panda 1 工具体验：偏 IDE 使用体验，素材和系统性能关联不足，评分 10/20。
  - Linux Dirty Frag / CVE-2026-46333：偏安全漏洞，和本书性能主线距离较远，评分 8/20。
  - Android Bench / AI 写 Android：偏 AI 编程工具评测，非 Android 性能机制，评分 7/20。
  - Kotlin 2.3.0 语言更新：偏语言工具链，缺少明确性能切入点，评分 9/20。
- **下轮建议**：如果后续出现 3 篇以上高质量素材聚焦同一未覆盖主题，可优先复查 `ch06 存储与 I/O` 的 F2FS / dm-verity / fsync 深水位，以及 `ch12/ch24` 的 QUIC/HTTP3 真实线上指标。

## [Task9 Deep Review] 18.8 OpenGL ES 渲染链路 — 2026-05-20 — BufferQueue triple buffering 口径
- **类型**：源码准确性/数据支撑
- **位置**：Buffer 流转与 Triple Buffering L203
- **问题**：正文写“GLES 的 BufferQueue 通常配置为 3 个 Slot”。更稳的口径是“常见稳态会分配/使用 3 个 GraphicBuffer”，而不是 BufferQueue 固定只有 3 个 slot；实际 buffer 数受 max dequeued/acquired、async mode、producer/consumer 配置和 BLAST/传统 BufferQueue 路径影响。
- **建议**：补一段源码边界：slot 数是队列容量/索引空间，实际分配的 GraphicBuffer 数和 producer 可 dequeue 数由 BufferQueue 配置决定；Trace 中应结合 queue/dequeue 节奏与 acquired/dequeued 状态判断。

## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-05-20 — @CriticalNative public API 边界
- **类型**：源码准确性/API 边界
- **位置**：`@FastNative` 和 `@CriticalNative`，到底快在哪，边界又在哪 L187-L189
- **问题**：正文已收敛到 primitive 标量参数/返回值，但“数组不要写成稳定承诺；若要依赖数组语义需核对 ART 源码与测试”仍容易让应用侧读者理解成数组有条件可用。官方口径是 @CriticalNative 不能使用托管对象，数组也属于托管对象；非 static 的隐式 this 也属于托管对象。
- **建议**：面向应用侧直接写成“必须是 static native，且 public API 安全边界只接受 primitive 标量参数/返回值；数组、String、对象、隐式 this 都不作为 @CriticalNative 参数/返回值”。如讨论 ART 内部实验能力，单独放到待验证/源码研究段，不混入实践建议。

## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-05-20 — 16KB page size NDK 版本口径
- **类型**：版本差异
- **位置**：16KB page size：JNI/NDK 项目的上线门槛 L238
- **问题**：正文写“如果还在 NDK r27，需要按文档补充 linker flags”。官方迁移口径覆盖 NDK r27 及以下；只点名 r27 会漏掉仍停在更旧 NDK 的项目。
- **建议**：改为“NDK r28+ 默认支持；NDK r27 及以下需要按官方文档补充 linker flags（如 max-page-size/common-page-size 16KB）并重编所有自有与三方 native 库”。

## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-05-20 — Propeller 待验证段
- **类型**：数据缺失/版本边界
- **位置**：Post-Link 优化：Propeller L246-L252
- **问题**：章节已处于 finalized，但 Propeller 段仍以 `[待验证]` 开头，且明确说明 NDK r28 changelog 与 LLVM lld 官方文档未找到 `--propeller-order` flag，8% 收益来自 Google Propeller 论文的 warehouse-scale workload，不能直接作为 Android NDK 功能背书。
- **建议**：删除正文中的实践性启用路径，或降级为“延伸阅读/待验证素材”；只有在 NDK/LLVM 官方文档出现 Android 可用 flag 和采集流程后再恢复到正文实践建议。

## [Task9 Deep Review] 22.10 RenderEffect 与 RuntimeShader 性能实践 — 2026-05-20 — GPU Headroom 运行时降级边界
- **类型**：版本差异/API 边界
- **位置**：优化清单 L282
- **问题**：正文写 Android 16+ 可结合 GPU Headroom 做运行时质量降级，但 AOSP android-16.0.0_r1 的 `SystemHealthManager.getGpuHeadroom()` 仍带 `@FlaggedApi(android.os.Flags.FLAG_CPU_GPU_HEADROOMS)`，设备不支持时会抛 `UnsupportedOperationException`，并且必须遵守 `getGpuHeadroomMinIntervalMillis()`。
- **建议**：把这条改成“可选能力”：先检测 API/flag/设备支持，捕获 `UnsupportedOperationException`，遵守最小采样间隔；不满足时回退到帧耗时、温控、设备档位和灰度开关。

## [Task9 Deep Review] 22.10 RenderEffect 与 RuntimeShader 性能实践 — 2026-05-20 — GPU counter 与 2.10 交叉引用口径
- **类型**：交叉引用一致性
- **位置**：Perfetto 与 GPU 工具观测 L264；优化清单 L282
- **问题**：本节已经把 `gpu_busy` 写成“若存在则纳入对照，counter 名称和精度因厂商实现而异”，但相关章节 2.10 仍有“Android 16 统一 gpu_busy 轨道名称/百分比语义”的强断言。读者跨章阅读时会得到相反口径。
- **建议**：同步 2.10 或在本节引用 2.10 时加边界说明：Android CDD 要求支持 GPU profiling 的设备输出符合 GPU counter proto，但不保证所有设备都有统一可用的 `gpu_busy` 名称与精度。


## [Task9 Deep Review] 8.11 Native 库加载与动态链接性能 — 2026-05-20 — ART / NativeLoader 源码链路锚点
- **类型**：原理链/源码引用
- **位置**：Native 库加载在启动链路里的位置 L102-L111
- **问题**：正文概括 `System.loadLibrary()` 会从 Java 层进入运行时再到 Bionic `dlopen()` / `android_dlopen_ext()`，结论正确，但缺少 ART 与 libnativeloader 的源码锚点；读者容易把它理解成 Java 直接调用 Bionic，忽略 ClassLoader namespace、caller location、NativeBridge 等中间决策。
- **建议**：补一条源码链路：`libcore/ojluni/src/main/native/Runtime.c::Runtime_nativeLoad` → `art/openjdkjvm/OpenjdkJvm.cc::JVM_NativeLoad` → `art/runtime/jni/java_vm_ext.cc::JavaVMExt::LoadNativeLibrary` → `art/libnativeloader/native_loader.cpp::OpenNativeLibrary` / `NativeLoaderNamespace::Load()` → `android_dlopen_ext(..., ANDROID_DLEXT_USE_NAMESPACE)`；说明 namespace 不是 Bionic 单独决定，而是由 ClassLoader/native loader 共同传入。

## [Task9 Deep Review] 8.11 Native 库加载与动态链接性能 — 2026-05-20 — 厂商 linker config 样本缺口
- **类型**：知识盲区/版本差异
- **位置**：扩展：厂商配置与预装库差异 L218-L222
- **问题**：正文已指出厂商 linker config 会改变 namespace / public library / 预装库暴露边界，但只留下 `[待补充]`，没有给出 AOSP linkerconfig 产物、Pixel 样本或厂商 ROM 对照。这个缺口不影响主线结论，但会限制读者判断“某台设备能 dlopen 私有库”是不是平台契约。
- **建议**：补 1-2 个可复核样本：AOSP `system/linkerconfig` 生成规则、Pixel 设备上的 linker config 产物、至少一个厂商 ROM 差异；同时列出排查动作（收集 linker config、`dlopen failed` logcat、`/proc/<pid>/maps`）并标注“设备可访问 ≠ Android API 保证”。

## [2026-05-20 17:13] Task 2A 缺口挖掘记录：未创建新章节

本轮 Phase 0 未发现 `status: draft` 且正文实质内容少于 15 行的章节，因此进入缺口挖掘。检查结果如下：

- `source-index.json` 中高分未映射素材多数已被既有章节覆盖，或主题不属于 Android 性能知识体系。
- Perfetto v53 / v54 相关素材已覆盖到 13.12、13.14、13.17、13.18 等章节，不单独创建新小节。
- Startup Profile / DEX layout 官方文档已在 21.4「Baseline Profile 实战」的扩展段落中覆盖，不创建 21.x 新章节。
- Android 14–17 Foreground Service timeout / ANR 已在 9.2、9.4 中覆盖，不创建独立 9.x 新章节。
- Android 17 MessageQueue / DeliQueue、ProfilingManager system triggers、桌面窗口化、大屏渲染、ApplicationExitInfo、DMA-BUF / Gralloc 16KB page 等方向均已有对应章节或待回炉队列。
- 官方文档中 background location battery、background task battery optimization 等方向与 25.2、25.4、25.5 重合；本轮不拆新节。

结论：本轮未发现评分 ≥ 14 且尚未被 SUMMARY.md 覆盖的独立知识缺口。下一轮建议优先从 AOSP `packages/modules/` 中仍未系统化覆盖的模块（如 UWB、NFC、HealthFitness、OnDevicePersonalization）筛选，但只有能关联启动、功耗、内存、稳定性或可观测性时再建章节。



## [2026-05-20] Task 2A 挖掘模式复盘 — 未创建新章节

### 结论
本轮 Phase 0 未发现 `status: draft` 且正文实质内容 < 15 行的章节。进入 Phase 1 后，对 source-index 高分未映射素材、近 3 日 daily-info、research-gaps 与官方 Android 17 文档方向做交叉检查，未发现“尚未覆盖且适合独立成节”的 ≥14 分缺口。

### 已检查方向
- **Android 17 App Memory Limits / ANOMALY / ProfilingTrigger**：已覆盖于 23.9、26.12、8.8、14.7，不创建新节
- **Reduced Wakelocks for Idle Alarms / OnAlarmListener**：已覆盖于 11.5、25.3、5.10；5.7 的旧口径已存在 Task2B 修正线索，不作为新节
- **Android 16 SDM / Cloud Compilation 安装链路**：已覆盖于 1.9、1.21、16.6，并已有 2026-05-20 DeepResearch 素材挂入 1.9
- **SmartPerfetto 可复用 Trace 分析平台**：已覆盖于 13.18，不创建新节
- **Android Studio Panda / Layout Inspector / LeakCanary Profiler**：已覆盖于 14.14、14.16、23.9，不创建新节
- **Codec2 / Tunneled Playback / Media3 ABR、端侧 AI 推理、sched_ext OEM 调度**：已覆盖于 8.8、5.11/5.14、17.4，不创建新节
- **Linux Dirty Frag / CVE-2026-46333 / AI 漏洞报告洪流**：偏安全治理或行业资讯，与本书性能主线相关性不足，不创建新节

### 避免重复挖掘的判断
- 高分素材中多数已在 5.x、8.x、13.x、14.x、16.x、17.x、23.x、25.x、26.x 中形成独立小节或交叉引用。
- 今日新增 Android 17 官方文档线索以 App memory limits、ProfilingTrigger、OnAlarmListener 为主，均已有章节承接。
- Linux 安全新闻与 AI 开发资讯不进入本轮 Android 性能知识结构。
---

## Task 2A 知识缺口挖掘记录（2026-05-20 19:04）

- **结果**：未发现评分 ≥ 14 且尚未被现有章节或队列承接的新增知识缺口，本轮不创建章节。
- **已检查方向**：Perfetto v53/v54 Data Explorer / Jank CUJ / pprof / Simpleperf、Android 17 MessageQueue / DeliQueue、Cached App Freezer + GC、DMA-BUF / Gralloc / 16KB 图形内存、Android 17 JobScheduler Excessive CPU + ProfilingTrigger、ApplicationExitInfo / ApplicationStartInfo / ProfilingManager 版本化诊断、Android Studio Panda / LeakCanary Profiler、AOSP Wi-Fi / Bluetooth / Media / netd / Connectivity 结构缺口、Android AI OS / Android Bench。
- **覆盖判断**：上述方向分别已有 13.12、13.14、13.18、1.13、4.11、2.24、25.12、26.9、26.12、26.13、14.14、23.9、11.6、12.5、12.6、8.8、17.6 等章节或回炉队列承接。
- **落盘报告**：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/OpenClaw定时任务/知识加工/2026-05-20-19-知识加工(新).md`

## 2026-05-20 Task 2A 缺口挖掘记录（20:04）

本轮 Phase 0 未发现空 draft 章节。Phase 1 检查 source-index 高分未映射素材、最近 research-feeds / daily-info、AOSP 模块与官方性能文档后，未创建新章节。

已检查但不建章的方向：
- Android Vitals / Play 质量门禁：26.7、26.3、26.6 已覆盖，后续适合补 Task2B 口径。
- MediaProvider / MediaStore / FUSE：6.1、6.4 已覆盖，独立章信息增量不足。
- Android Studio Panda Memory Profiler / Leak Insight：14.14、14.16 已覆盖，适合工具章节增量更新。
- NFC / Telephony / Biometric：性能主线弱，素材不足。
- Linux Dirty Frag / CVE：偏安全资讯，不纳入性能书新章节。

落盘报告：`OpenClaw定时任务/知识加工/2026-05-20-20-知识加工(新).md`



## [Task6 Review] 19.09 Measure — 2026-05-20
- **类型**：需补充素材 / 需补充结构
- **位置**：§核心能力（L118-L129）、§和 Firebase、Sentry 的差别（L143-L153）
- **问题**：能力范围只列“能力/适合的问题”，缺 Crash、ANR、HTTP、启动、App size、CPU、内存、点击、页面导航的数据来源、关键字段和适用判断；平台对比仍是段落说明，缺 Firebase / Sentry / Measure 横向表格。
- **建议**：由 Task2B 补能力范围字段级表格与平台对比表；涉及官方能力边界时补验证来源或 `[待验证]` 标注。Task6 不裁决技术真伪，不在本轮补写新内容。
- **review 日志**：logs/review/2026-05-20-20-review.md

## [Task9 Deep Review] 19.09 Measure — 2026-05-20
- **类型**：版本差异/接入边界
- **位置**：frontmatter L6-L10；正文 §接入成本不只在 SDK L133-L143；§核心能力 L120-L129
- **问题**：章节没有写 Measure Android 的接入版本边界。当前官方文档写 Android minimum requirements 为 AGP 8.1.0、minSdk 21、targetSdk 35；网络自动采集对 OkHttp 仅标注 4.7.0-5.3.2，HttpURLConnection 需要 Android SDK 0.18.0，请求 timeline 需要 Android 0.16.2。frontmatter 仍泛写 Android 8-17，容易把平台版本和 Measure SDK 支持版本混在一起。
- **建议**：补“接入版本边界”小表：Measure SDK/Gradle plugin 版本、minSdk/targetSdk/AGP、自托管兼容版本、OkHttp/HttpURLConnection 自动采集边界；frontmatter 的 applicable_versions 改成章节关注的 Android 系统范围，并另设 SDK 版本来源，避免把 SDK 支持范围写成 Android 8-17。


## [Task9 Deep Review] 19.09 Measure — 2026-05-20
- **类型**：数据模型准确性
- **位置**：§平台型 APM 的数据模型 L167-L172
- **问题**：正文把 App size 放进 `resource`，与 HTTP、CPU、memory 一起描述成移动会话拆分对象。但官方 App Size Monitoring 是构建/发布级数据：Android 由 Gradle Plugin 在 assemble/bundle 成功后上传 APK/AAB size，iOS 由 dSYM 上传脚本带入 IPA size，不是 session timeline 内的资源事件。
- **建议**：把数据模型拆成 session-level（session/screen/event/span/error/http/cpu/memory）和 build-level（build/app_size/mapping/dSYM/版本信息）两层；App size 放到 build/release 维度，不要和会话资源事件混写。


## [Task9 Deep Review] 19.09 Measure — 2026-05-20
- **类型**：原理链/数据支撑
- **位置**：§和 OpenTelemetry 的关系 L231-L242
- **问题**：“网络请求携带 trace id，与服务端 trace 关联”方向正确，但缺少 Measure 官方实现锚点，容易被读成自定义 request id。官方 performance tracing 文档给的是 W3C Trace Context 的 `traceparent` header，并提供 `Measure.getTraceParentHeaderKey()` / `Measure.getTraceParentHeaderValue(span)`。
- **建议**：把这一节落到 `traceparent`：移动端先 `Measure.startSpan("http")`，再把 `Measure.getTraceParentHeaderKey()/Value(span)` 加到 OkHttp/URLSession/Dio 请求；服务端按 W3C Trace Context 继续 trace。说明这只是请求级关联，不等于把移动 session 完全建模成 OpenTelemetry trace。

## [Task6 Audit] 19.11 JankStats — 2026-05-20
- **类型**：需补充结构
- **位置**：§和 FrameMetrics 的分工 / 大纲锚点「工具分工」
- **问题**：大纲要求用表格说明 JankStats、FrameMetrics、Perfetto、Macrobenchmark、Firebase Performance 的数据边界。正文目前只有 JankStats 与 FrameMetrics 的分工说明，未覆盖 Perfetto、Macrobenchmark、Firebase Performance，读者无法判断线上指标、线下基准和 trace 根因分析之间如何分工。
- **建议**：保留现有 JankStats vs FrameMetrics 判断，并补一张横向表格。建议维度：数据粒度、线上/线下、是否能定位根因、适用场景、边界；涉及 Firebase Performance 具体字段或版本能力时加官方来源或待验证标注。
- **review 日志**：logs/review/2026-05-20-23-audit.md


## [Task9 Deep Review] 4.5 App 内存优化 — 2026-05-21
- **类型**：第三方库实现准确性
- **位置**：L343-L353、L924 图片加载库内存管理
- **问题**：正文写 Glide、Coil、Fresco “都内建 Bitmap Pool”，并在表格中写 Coil 的 Bitmap Pool 是“基于 Coroutine”。Coil 2.x 官方升级说明已经移除 BitmapPool，当前说法需要按 Coil 版本重写；否则会误导读者把 Glide 的复用池模型套到 Coil。
- **建议**：把 Glide、Coil、Fresco 分版本描述：Glide 保留 `LruBitmapPool`；Coil 1.x/2.x+ 分开，若目标是当前 Coil，应改成 memory cache / hardware bitmap / ImageDecoder 边界，不写 BitmapPool；Fresco 说明 CloseableReference 与 native/shared memory 口径。


## [Task9 Deep Review] 4.5 App 内存优化 — 2026-05-21
- **类型**：数据支撑/政策边界
- **位置**：L799、L848 16KB Page Size 与 Bitmap
- **问题**：“Google Play 已将 16KB 页对齐作为对所有应用的强制要求”缺少 targetSdk/新应用与更新/生效时间边界；“每个 Bitmap 最后一页浪费增加、Glide/Coil 已内部处理对齐问题”缺少官方或实测依据。
- **建议**：把 Play 要求改成带时间、targetSdk 和发布类型的政策表述；Bitmap 影响降级为“可能增加 native allocation/页粒度碎片，需以 heapprofd/meminfo 实测确认”，删除或补证 Glide/Coil 已处理对齐的断言。


## [Task9 Deep Review] 4.5 App 内存优化 — 2026-05-21
- **类型**：代码示例准确性
- **位置**：L393-L406 Activity 泄漏修复示例
- **问题**：`MyWorker` 被改成 `static class` 后，示例仍在 `run()` 中直接调用 `doSomethingSlow()`；如果该方法是 `Activity` 的实例方法，这段 Java 代码不能编译。
- **建议**：改为 `activity.doSomethingSlow()`，或把耗时任务抽到不依赖 Activity 的 worker/service；同时补充取消任务或检查生命周期的退出条件，避免 WeakReference 只是隐藏泄漏而不终止后台工作。


## [Task9 Audit] 15.3 性能指标体系 — 2026-05-21
- **类型**：指标定义准确性
- **位置**：L279 Crash Rate 分子定义
- **问题**：正文前半段已按 Android Vitals 写成“每日用户中至少一次崩溃的比例”，但随后又写成“受影响用户比例按会话占比计”。Play Console Help 的口径是 daily users / daily active users（按用户-设备-日期归一），不是 crash 次数，也不应简化成普通 session rate。
- **建议**：改为“用户感知崩溃率是每日用户/设备日中至少一次用户感知崩溃的比例；一个用户同一设备同一天多次崩溃仍算一个受影响 daily user。若平台内部另有 session 指标，应单独命名，不和 Android Vitals crash rate 混写。”


## [Task9 Audit] 15.3 性能指标体系 — 2026-05-21
- **类型**：Perfetto 数据源口径
- **位置**：L424-L430 Power Rails / Energy Consumer Track
- **问题**：正文把 Power Rails track 描述成“实时电流和电压，单位 mW”。Perfetto power rails / ODPM 口径更准确地说是硬件 rail 的能量计数器，依赖设备硬件与 IPowerStats HAL；功率通常由能量差分除以时间窗口得到，不是所有设备都有可用轨道。
- **建议**：改成“Power rails 提供 per-rail energy counters；在选定时间窗内计算能量差/时长得到平均功率。是否可见取决于设备硬件、PowerStats HAL 与 trace 配置 `collect_power_rails: true`。”

## [Task6 Review] 5.9 ADPF 自适应性能框架 — 2026-05-21
- **类型**：需重写
- **位置**：源码调研补充（2026-05-01/05-07）与参考资料 DeepResearch 连续摘要
- **问题**：正文仍保留 AIW 源码调研注释块、调研日期标题和重复 DeepResearch 摘要。它们提供了素材来源，但发布稿主线在“版本演进”后被打断，读者会从机制讲解切到内部加工记录。
- **建议**：由 Task2B 将可保留的 API/version 内容融入 Performance Hint、GameState、扩展/参考资料等主线段落；删除 AIW 注释、源码调研补充日期标题和重复摘要。Task9 已登记的 API level、源码入口和设备数据表问题需优先修正。
- **review 日志**：logs/review/2026-05-21-02-review.md



## [Task6 Review] 5.9 ADPF 自适应性能框架 — 2026-05-21
- **类型**：需重写
- **位置**：§源码调研补充（2026-05-01/05-07）与参考资料 DeepResearch 摘要
- **问题**：正文仍保留 AIW 源码调研注释、日期标题和“注入时间/价值”等加工痕迹；技术事实已修过一轮，但发布主线被素材块打断。
- **建议**：Task2B 将可保留内容融入 Performance Hint、GameState、版本演进或参考资料；删除 AIW 注释和重复摘要。
- **review 日志**：logs/review/2026-05-21-04-review.md

## [Task6 Review] 3.1 Input 事件分发全流程 — 2026-05-21
- **类型**：需重写
- **位置**：参考资料之后的 stale-event/WindowInfosListener、反压机制、Android 15/16 输入系统演进素材块
- **问题**：章节在参考资料后继续追加多个源码调研块，并保留 AIW 注释、注入时间和内部修正说明；内容像素材日志，影响发布稿收束。
- **建议**：Task2B 将有价值的源码信息融入已有小节或整理为正式附录；删除内部加工痕迹，只保留必要来源。
- **review 日志**：logs/review/2026-05-21-04-review.md

## [Task9 Deep Review] 5.9 ADPF 自适应性能框架 — 2026-05-21
- **类型**：数据缺失
- **位置**：5.9 L326 setPreferPowerEfficiency 非游戏场景收益
- **问题**：“后台 AI 推理批处理（功耗降低 15-30%）”没有设备、负载、统计口径或来源；当前只能算未验证收益数据。
- **建议**：删除百分比，或补实验条件：设备/系统 build、线程绑定、任务类型、功耗采样工具、样本数和对照组。

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-05-21
- **类型**：版本差异
- **位置**：3.1 L831 HwTimeoutMultiplier 版本口径
- **问题**：正文写 `HwTimeoutMultiplier()` 是 Android 14+ 引入；但 AOSP android-13.0.0_r1 `InputDispatcher.cpp` 的 `STALE_EVENT_TIMEOUT` 和 `DEFAULT_INPUT_DISPATCHING_TIMEOUT` 已使用 `HwTimeoutMultiplier()`。
- **建议**：把 stale/dispatch timeout 的 multiplier 口径改为 Android 13+；若只想强调某个具体路径，应按 Android 12/13/14 分别列源码差异。

## [Task6 Review] 19.09 Measure — 2026-05-21
- **类型**：需补充素材
- **位置**：§核心能力 / 大纲锚点「能力范围」
- **问题**：Task2B 标记完成后，正文仍只有“能力 / 适合的问题”二列表，未按 Crash、ANR、HTTP、启动、App size、CPU、内存、点击、页面导航拆出数据来源、关键字段和适用判断。
- **建议**：补一张字段级能力范围表，列出 Measure 事件/字段、端侧来源、适合判断、边界/不支持项和验证来源；与 Task9 的 native crash / ANR / 符号化边界问题合并处理。
- **review 日志**：logs/review/2026-05-21-08-review.md

## [Task9 Deep Review] 15.5 线上性能监控 — 2026-05-21
- **类型**：源码准确性 / FrameMetrics 指标口径
- **位置**：L150-L157 FrameMetrics 指标表
- **问题**：表格使用 `UNKNOWN_DELAY` / `INPUT_HANDLING` / `COMMAND_ISSUE` 等缩写，和公开 API 常量名不完全一致；其中 `COMMAND_ISSUE` 被写成 “GPU 命令执行耗时”。AOSP `FrameMetrics.java` 中公开常量是 `UNKNOWN_DELAY_DURATION`、`INPUT_HANDLING_DURATION`、`COMMAND_ISSUE_DURATION` 等；`COMMAND_ISSUE_DURATION` 表示 issuing draw commands to the GPU，GPU 完成耗时另有 `GPU_DURATION`。
- **建议**：把指标列改为公开常量名（`*_DURATION`）；将 `COMMAND_ISSUE_DURATION` 的含义改为 RenderThread/HWUI 向 GPU 提交 draw commands 的阶段。如果要讨论 GPU 执行耗时，单独补 `GPU_DURATION` 与对应 API 边界。
