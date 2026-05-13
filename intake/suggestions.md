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
