# 一般建议清单

- **类型**：版本差异

- **位置**：Android 12 InputFlinger 重构描述

- **问题**：Android 12 的 InputFlinger 重构描述过于简化，实际是代码抽取到独立服务但仍运行在同一进程内，而非真正的独立服务

- **建议**：修正描述，明确说明代码组织变化和运行时环境

- **类型**：版本差异

- **位置**：版本演进表

- **问题**：缺少 Android 15 Predictive Back 手势对 Input 分发路径的重大影响

- **建议**：补充 Android 15 版本变更，说明预测性返回手势的实现机制

- **类型**：数据缺失

- **位置**：ANR 超时机制部分

- **问题**：缺少实际 ANR Trace 分析案例，无法展示 wq 堆积到 ANR 触发的完整过程

- **建议**：添加一个具体的 Input ANR Trace 分析案例，包括 wq 堆积、ANR 触发、系统响应的完整时序

- **类型**：数据缺失

- **位置**：性能分析部分

- **问题**：缺少不同场景下的 Input 处理耗时基准数据

- **建议**：补充正常点击 vs 复杂手势处理的耗时对比数据，提供量化参考

- **类型**：回炉重修（技术细节验证）

- **位置**：全文多处关键技术点

- **问题**：
  - 1. ProfilingManager 触发器常量名需验证
  - 2. DeliQueue 性能改善需补充 Trace 截图
  - 3. 16KB 页面断言需提供具体案例

- **建议**：
  - 1. 检查 AOSP 源码中 ProfilingManager 触发器常量
  - 2. 补充真实的 Perfetto Trace 片段
  - 3. 提供具体的原生库名称和 AOSP 链接

- **review 日志**：logs/review/2026-04-15-17-review.md

- **类型**：数据缺失

- **位置**："120Hz 的屏幕功耗通常比 60Hz 高 20-40%"（扩展：120Hz 场景功耗权衡）

- **问题**：功耗差异数值缺少可追溯的来源，且未说明适用于哪种面板技术

- **建议**：标注为近似参考值，注明"具体功耗差异因面板技术和设备而异"

- **类型**：数据缺失

- **位置**："触摸停止后一段时间（通常 2-3 秒）"（Touch Boost 描述）

- **问题**：Touch Boost 超时是 OEM 可配置的，AOSP 默认值可能与"2-3 秒"不符

- **建议**：改为"OEM 可配置的触摸提升超时"或标注为近似值

- **类型**：数据缺失

- **位置**："Janky frames 比例超过 5% 时用户能明显感知到卡顿"

- **问题**：缺少来源

- **建议**：标注来源或改为更保守的表述

- **类型**：源码准确性

- **位置**：Perfetto SQL 查询刷新率变化事件

- **问题**：track_event 表名和 refreshRate 事件名可能与当前 Perfetto 版本不匹配

- **建议**：验证并更新 SQL 查询，或使用 Perfetto 的 display_refresh_rate track

- **类型**：数据缺失

- **位置**：全章节

- **问题**：作为工具使用章节，没有一处真实的 dumpsys 输出样例。读者无法对照自己的输出判断是否正常，也无法理解关键字段在实际输出中的位置和格式

- **建议**：每个核心子命令（activity、meminfo、gfxinfo、window、batterystats、SurfaceFlinger）至少添加一个精简的真实输出片段（10-20 行），标注关键字段

- **类型**：源码准确性

- **位置**：framestats 逐帧时间线说明

- **问题**：列名列表不完整，缺少 Flags、OldestInputEvent、NewestInputEvent、DequeueBufferDuration、QueueBufferDuration、GpuCompleted 等列。这些列在实战分析中都有用途（Flags 区分正常帧和异常帧，DequeueBufferDuration 反映 BufferQueue 等待时间）

- **建议**：补全列名列表，或至少标注"此处列出最关键的列，完整列表参见 AOSP Choreographer.java"

- **类型**：版本差异

- **位置**：batterystats --enable full-wake-history

- **问题**：该参数在 Android 13+ 可能已不工作或行为变更，章节未提及版本限制

- **建议**：标注该参数适用的 Android 版本范围，Android 13+ 推荐替代方案

- **类型**：版本差异

- **位置**：batterystats 功耗分析工作流

- **问题**：导出 bugreport 命令只提到 adb bugreport > bugreport.zip，未提及 Android 12+ 推荐使用 adb bugreportz（生成标准 zip 文件，速度更快）

- **建议**：补充 bugreportz 的用法说明和版本差异

- **类型**：知识盲区

- **位置**：进阶用法

- **问题**：未提及 dumpsys --proto 输出格式（protobuf），该格式在自动化性能测试 CI/CD 中广泛使用

- **建议**：在进阶用法或实战部分补充 --proto 的用法和典型场景（如自动解析 meminfo 数据入库）

- **类型**：交叉引用

- **位置**：gfxinfo 部分 JankStats 库提及

- **问题**：提到 JankStats 库（AndroidX）但未交叉引用 7.1 节（卡顿定义）或 7.5 节（优化策略），读者找不到后续阅读入口

- **建议**：添加"详见 §7.1 卡顿的定义与分类"和"§7.5 优化策略中 JankStats 的集成方法"

- **类型**：源码准确性

- **位置**：参考资料 AOSP 源码路径

- **问题**：f2fs ioctl 定义路径 `kernel/linux/fs/f2fs/f2fs.h` 不准确。`F2FS_IOC_START_ATOMIC_WRITE` 等 ioctl 常量定义在 `include/uapi/linux/f2fs.h`（用户空间 API 头文件），`fs/f2fs/f2fs.h` 是内核内部实现头文件。两者应区分。

- **建议**：修正为 `include/uapi/linux/f2fs.h`（ioctl 定义）+ `fs/f2fs/f2fs.h`（内核内部结构），分别说明用途

- **类型**：源码准确性

- **位置**：参考资料 VFS 层路径

- **问题**：`kernel/linux/fs/vfs.c` 过于简化。VFS 实现分散在 `fs/open.c`、`fs/read_write.c`、`fs/namei.c` 等多个文件中。

- **建议**：改为 `fs/*.c` + `include/linux/fs.h`，或直接引用 kernel.org VFS 文档链接（已存在）

- **类型**：源码准确性

- **位置**：参考资料 AOSP 源码路径前缀

- **问题**：所有内核源码路径使用 `kernel/linux/fs/` 前缀，非标准 AOSP 内核路径格式。

- **建议**：统一为 `fs/f2fs/`、`fs/ext4/` 等标准 Linux 内核路径格式（读者在 kernel.org 或 AOSP kernel 分支中查找时使用的路径）

- **类型**：源码准确性

- **位置**：参考资料 SQLite 编译选项路径

- **问题**：`external/sqlite/dist/Android.mk` 可能在 Android 14+ 中已迁移到 `Android.bp`（Soong 构建系统）。

- **建议**：标注"以实际 AOSP 版本构建系统为准，较新版本可能为 Android.bp"

- **类型**：原理断裂

- **位置**：SQLite 原子写优化章节

- **问题**：描述了 rollback journal 模式下的 atomic write 流程，但未提及 `SQLITE_ENABLE_BATCH_ATOMIC_WRITE` 在 WAL 模式下不生效这一关键限制。Android 上大量 App 使用 WAL 模式。

- **建议**：补充说明：batch atomic write 仅对 rollback journal 模式有效。WAL 模式下 SQLite 不走 journal + fsync 路径，因此不使用此优化。对大多数使用 WAL 模式的 App，f2fs 的优势主要体现在 fsync 本身的优化（逻辑日志 + CoW）而非 atomic write。

- **类型**：原理断裂

- **位置**：f2fs 的 fsync 优化章节

- **问题**：f2fs 的 fsync 优化描述为"logical logging"过于简化。实际是 roll-forward recovery 机制——fsync 时标记 direct node blocks，崩溃后通过 roll-forward 恢复。

- **建议**：将"逻辑日志（logical logging）"改为更精确的描述，如"f2fs 的 fsync 优化采用 roll-forward recovery 机制：fsync 时只需将数据块和 direct node 块写入，并通过特殊标记记录 fsync 意图。崩溃恢复时，f2fs 先回滚到最近 checkpoint，再通过标记的 node 块前滚恢复 fsync 的数据"

- **类型**：数据缺失

- **位置**：EROFS 性能提升数据

- **问题**："某些场景下可达 300%"的随机读性能提升数据来源不明确且过于夸张。华为官方数据约 25%，Google 测试为"much better"。

- **建议**：将"约 20%，某些场景下可达 300%"修正为"约 20%-25%"，并标注来源（如华为 EMUI 9.0.1 发布数据）。删除或修正 300% 数据。

- **类型**：数据缺失

- **位置**：SQLite batch atomic write "3 倍"性能数据

- **问题**："事务提交速度约为 ext4 上的 3 倍"缺乏测试条件说明。

- **建议**：补充测试条件（设备、存储类型、数据库大小、事务类型）或标注数据来源

- **类型**：数据缺失

- **位置**：ext4 fsync 延迟范围

- **问题**："几百毫秒甚至超过一秒"的 fsync 延迟描述缺少具体测试数据或 Trace 截图描述。

- **建议**：补充典型的 P99 延迟数据范围（如"在 Pixel 4 (ext4+UFS 2.1) 上实测，高负载场景下 SQLite fsync P99 延迟可达 200-500ms"）

- **类型**：数据缺失

- **位置**：碎片化性能退化数据

- **问题**："4KB 随机写延迟从 0.1ms 增加到 1-5ms"缺少使用时长、存储空间占用率、设备型号等条件。

- **建议**：补充条件说明（如"在 128GB UFS 3.1 设备上使用 18 个月、存储占用 90% 的情况下"）

- **类型**：版本差异

- **位置**：applicable_versions 覆盖范围

- **问题**：章节标注 `applicable_versions: "Android 10+"`，但内容从 Android 4.0 开始覆盖，且未覆盖 Android 15+ 的 16KB Page Size 对 f2fs 的影响细节。

- **建议**：在"版本演进"章节补充 Android 15 的 16KB Page Size 变更对 f2fs segment 管理和 GC 策略的影响（目前只有一行 [待验证] 标注）

- **类型**：知识盲区

- **位置**：f2fs Adaptive Logging

- **问题**：f2fs 在存储空间不足时从 normal logging 切换到 threaded logging，性能特征会显著不同，但章节未提及。

- **建议**：在"f2fs 的代价：垃圾回收"章节后补充 Adaptive Logging 的介绍，说明 f2fs 如何根据空间使用情况动态切换日志策略

- **类型**：版本差异

- **位置**：非 GMS 设备的 EROFS 采用情况

- **问题**：章节提到"不搭载 GMS 的设备 EROFS 不是强制要求"，但未进一步讨论中国市场的实际情况。

- **建议**：在"EROFS 与 OTA 升级"或厂商选型章节中补充：中国市场主流厂商（华为/Honor/小米/OPPO/vivo）在 EROFS 采用上的实际状态

- **类型**：源码准确性

- **位置**：ext4 ordered 模式 fsync 行为描述

- **问题**：文中说"日志只记录元数据（metadata），但保证在元数据提交到日志之前，对应的数据块已经写入磁盘"。实际上在 ordered 模式下，数据块直接写入最终位置（不是写入日志），然后在 journal 中记录元数据。这个区别虽然细微但对理解 fsync 延迟很重要。

- **建议**：明确说明"数据块直接写入其最终磁盘位置（不经过 journal），然后 journal 记录元数据变更"，以避免读者误以为数据也经过 journal

- **类型**：源码准确性

- **位置**：「AMS 入口和真正的计算路径不在同一层」小节，`mProcessStateController.runUpdate(...)` 委托链

- **问题**：`mProcessStateController` 确认存在（用于 setMaxAdj），但 `.runUpdate()` 方法未在公开 AOSP 中找到明确匹配。实际路径可能是 `AMS.updateOomAdjLocked()` 直接委托 `OomAdjuster.updateOomAdjLSP()`。

- **建议**：对照 AOSP android-16.0.0_r1 的 `ActivityManagerService.java` 确认确切委托链，修正中间环节。

- **类型**：源码准确性

- **位置**：DeathRecipient 代码示例

- **问题**：使用 `binderDied()` 无参形式。API 34 新增 `binderDied(IBinder who)` 重载。

- **建议**：标注 API 34+ 有更精确的重载可用，或更新代码示例使用新形式。

- **类型**：数据缺失

- **位置**：Perfetto SQL 查询部分

- **问题**：缺少 `oom_score_adj` 随时间变化的查询。判断进程是否在被推向可杀区，最直接的证据是 adj 值抬升轨迹。

- **建议**：补充查询 `linux.process_stats` 中的 `oom_score_adj` 变化，与 RSS、MemAvailable 放在同一时间窗分析。

- **类型**：数据缺失

- **位置**：Zygote COW 共享描述

- **问题**：「几十 MB Framework 代码」缺少精确数据支撑。

- **建议**：给出典型 Android 16 设备上 Zygote 预加载的 class 数量或内存占用参考值。

- **类型**：交叉引用

- **位置**：「与其他章节的关系」，"9.1 ANR 设计思想"

- **问题**：需确认该章节在项目实际文件结构中存在且标题匹配。

- **建议**：核实 9.1 的存在性和正确标题。

- **类型**：版本差异

- **位置**：后台限制时间线

- **问题**：遗漏 Android 11（后台位置限制）和 Android 15（前台 Service 类型收紧）。

- **建议**：补充这两个版本的要点。

- **类型**：事实错误

- **位置**：L293「Android 16 进一步强化了这一方向」

- **问题**：Baseline Profiles、JankStats、Macrobenchmark 均为 2022 年推出的 Jetpack 库，归入 Android 16 是事实错误

- **建议**：改为按工具演进时间线描述，明确各工具首次引入时间和 Android 16 具体新增内容

- **类型**：数据缺失

- **位置**：L164「冷启动时间不超过 1.5 秒」性能预算示例

- **问题**：缺少设备基线、App 类型上下文，读者无法判断预算是否合理

- **建议**：补充「在 2024 年中端设备（如 Snapdragon 7 Gen 1）上，社交类 App 的冷启动中位数约 1.2-1.8 秒」等参照数据

- **类型**：数据缺失

- **位置**：L265「5-10% 的基础设施成本下降」

- **问题**：数据来源准确（Brendan Gregg 2025），但直接套用到 Android App 性能场景缺少桥接

- **建议**：补充说明这是云基础设施成本指标，Android App 性能场景的度量维度（启动时间、帧率、ANR 率）与之不同，改为引用 Android 领域的优化 ROI 数据或弱化具体数字

- **类型**：源码准确性

- **位置**：L124 Macrobenchmark CI 使用描述

- **问题**：「可以在 CI 环境中自动测量」缺少关键前提：需要连接 Android 设备或模拟器

- **建议**：补充「在配置了 Android 模拟器或真机的 CI 环境中」作为前提条件

- **类型**：源码准确性

- **位置**：L56「BlastBufferQueue 替代 BufferQueue」

- **问题**：「替代」过于简化，BlastBufferQueue 是 BufferQueue 的包装层，底层机制仍存在

- **建议**：改为「引入 BlastBufferQueue 改变了 App 端与 BufferQueue 的交互模式（blast mode）」

- **类型**：数据缺失

- **位置**：Amazon/Google 性能数据引用

- **问题**：均为 Web 场景数据，用于佐证 Android App 性能优化必要性时缺少推理桥接

- **建议**：补充一句说明移动端场景有类似甚至更严格的约束（网络延迟、设备性能差异大、用户耐心更低）

- **类型**：交叉引用

- **位置**：全文多处章级引用

- **问题**：「第 4 章和第 10 章」「第 2 章」等均为章级引用，精度不够

- **建议**：改为节级引用如「§4.1 和 §10.1」「§2.1 和 §2.6」

- **类型**：知识盲区

- **位置**：数据驱动方法论

- **问题**：缺少统计严谨性讨论（方差、置信区间、最小运行次数）

- **建议**：补充一段讨论性能测量的统计方法，或引用 Android 官方 Macrobenchmark 文档中关于多次运行取中位数的建议

- **类型**：原理断裂 + 知识盲区

- **位置**：全文多处使用"首帧"，以及"效果量化"小节

- **问题**：全文未区分 TTID（Time to Initial Display，am start -W 的 TotalTime）和 TTFD（Time to Full Display，需要 reportFullyDrawn()）。不同定义影响优化策略方向——TTID 侧重减少 Activity 创建到第一帧的路径耗时，TTFD 侧重减少数据加载和内容就绪的耗时。

- **建议**：在"为什么要了解启动优化策略"小节后增加一段定义 TTID/TTFD，说明本节同时覆盖两者但侧重 TTID；在 Baseline Profile 效果量化部分区分展示两个指标；在总结部分提及 `reportFullyDrawn()` API 的使用。

- **类型**：源码准确性

- **位置**：Baseline Profile 制作 → 编写生成测试用例

- **问题**：`includeInStartupProfile = true` 参数在早期版本的 `benchmark-macro-junit4` 中不存在（该参数在 1.2.0+ 引入）。读者使用旧版本库会导致编译错误。

- **建议**：在代码示例旁标注最低依赖版本，或在 `build.gradle` 依赖声明后加注释说明版本要求。

- **类型**：源码准确性

- **位置**：SplashScreen API 核心使用小节

- **问题**：正文说"必须在 setContentView() 之前调用"，但 `installSplashScreen()` 实际要求在 `super.onCreate()` 之前调用。代码示例顺序正确，但文字说明可能导致读者遗漏。

- **建议**：修正为"installSplashScreen() 必须在 super.onCreate() 之前调用"。

- **类型**：原理断裂

- **位置**：多线程并行初始化框架 → DAG 模型与拓扑排序 → 自研框架

- **问题**：DAG 概念解释清楚后，直接跳到 App Startup 的 Initializer 接口，然后自研框架列出设计要点但没有展示"如何从 DAG 构建可执行调度计划"的实现路径。

- **建议**：在自研框架部分补充一段简要说明拓扑排序的实现思路（如 Kahn 算法或 DFS），或引用一个开源启动框架（如 Alibaba Alpha）作为实现参考。

- **类型**：数据缺失

- **位置**：延迟初始化策略 → 懒加载小节

- **问题**："将冷启动耗时从 2800ms 降到了 1800ms"来源于微信公众号文章，具体条件（设备、Android 版本、SDK 组成）不透明。

- **建议**：标注为"行业公开案例，来自 XX 文章"，或改为更通用的表述"实践中，通过合理的任务分类通常可减少 30-50% 的 Application 初始化耗时"。

- **类型**：数据缺失

- **位置**：效果量化小节

- **问题**：归因于"Google 官方数据"但未给出具体来源（I/O 演讲？文档？case study？）。

- **建议**：引用具体来源，如 "根据 Google I/O 2022 演讲数据，XX 应用通过 Baseline Profile 实现了 XX% 的启动速度提升"。

- **类型**：数据缺失

- **位置**：布局优化 → AsyncLayoutInflater 小节

- **问题**："收益通常在 50-200ms 之间"为具体量化断言但无 benchmark 或引用支撑。

- **建议**：补充来源，或改为"根据布局复杂度，收益通常在数十到数百毫秒级别"并标注为经验估算。

- **类型**：交叉引用

- **位置**：启动速度线上监控 → 在 Perfetto 中定位启动耗时瓶颈；以及 frontmatter related_chapters

- **问题**：章节提到 Method Trace 追加分析但未交叉引用 8.8 节（ProfilingManager 系统触发式性能追踪）。frontmatter related_chapters 也未包含 8.8。另外 ch08 目录中存在两个 08 前缀文件（08-media-pipeline.md 和 08-system-triggered-profiling.md），后者未出现在 SUMMARY.md 中，可能存在章节号冲突。

- **建议**：在 Method Trace 相关段落添加交叉引用 8.8；在 related_chapters 中添加 "8.8"；与高爷确认 08-system-triggered-profiling.md 的章节归属。

- **类型**：原理描述不准确

- **位置**：「页面跳转优化策略」FragmentFactory 代码示例

- **问题**：PreloadFragmentFactory.instantiate() 中调用 fetchPreloadData() 是同步操作，如果涉及 IO 会阻塞主线程。代码示例没有说明该方法必须是非阻塞的。

- **建议**：在代码注释中明确标注 fetchPreloadData() 应从内存缓存读取，或改为在 Application.onCreate() 阶段预加载到静态变量中

- **类型**：原理描述不准确

- **位置**：「页面跳转优化策略」setReorderingAllowed(true) 说明

- **问题**：描述为「让系统并行处理多个 Fragment 操作」，实际 setReorderingAllowed(true) 的作用是允许 FragmentManager 重排操作顺序（如将 remove+add 优化为 replace），不是并行执行。

- **建议**：修正描述为「允许 FragmentManager 重新排列事务中的操作顺序，将多个操作合并优化（如 remove(A)+add(B) 合并为 replace），减少不必要的生命周期回调」

- **类型**：版本差异

- **位置**：版本演进段

- **问题**：1) ViewPager2 归入「Android 9.0」条目是误导，它是 AndroidX 库不与 OS 版本绑定。2) setMaxLifecycle() 在 Fragment 1.1.0 引入，非 1.2.0。

- **建议**：1) 将 ViewPager2 条目改为独立行「2019-02：ViewPager2 首个 alpha 发布（AndroidX），2019-11 稳定版 1.0.0」。2) 修正为「Fragment 1.1.0：引入 setMaxLifecycle()」

- **类型**：交叉引用

- **位置**：点击响应段 RAIL 模型引用

- **问题**：RAIL 模型是 Chrome 团队的 Web 性能模型（web.dev/rail），但链接指向 developer.android.com/topic/performance/vitals（Android Vitals）。两个概念不应混为一谈。

- **建议**：分别引用——RAIL 模型引用 web.dev/rail，Android 点击响应阈值引用 Android Vitals 的冻帧/慢帧定义

- **类型**：原理断裂

- **位置**：Binder 分析节"Binder 事务按耗时排序"SQL

- **问题**：声称分析 client_dur/server_dur/dispatch_dur 三个维度，但 SQL 只查 slice 总 dur，无法区分。三个维度的描述和实际查询能力脱节。

- **建议**：要么通过 ftrace binder_transaction 事件关联提取三阶段耗时（需要启用对应 ftrace event），要么修改文字描述，明确当前 SQL 只能查总耗时。

- **类型**：原理断裂

- **位置**：「调度延迟：Runnable → Running 的时间」节

- **问题**：标题描述调度延迟（Runnable 到获得 CPU 的时间），但 SQL 只列出主线程的 sched 记录。完全没有计算调度延迟。

- **建议**：重写 SQL，计算逻辑：找到 end_state IN ('R','R+') 的 sched 条目，到同一 utid 下一条 sched.ts 的差值即为调度延迟。示例：SELECT (next_sched.ts - curr_sched.ts) AS latency_ns FROM sched curr_sched JOIN sched next_sched ON curr_sched.utid = next_sched.utid AND next_sched.ts > curr_sched.ts WHERE curr_sched.end_state IN ('R','R+') ...

- **类型**：事实错误

- **位置**：「线程 CPU 时间统计」SQL

- **问题**：CPU 利用率分母使用 MAX(ts+dur)-MIN(ts)，这是该线程首次调度到末次调度的跨度，不是 Trace 总时长。空闲时间被排除，结果偏高。

- **建议**：分母改为 (SELECT end_ts - start_ts FROM trace_bounds)

- **类型**：版本差异

- **位置**：全文各 SQL 查询

- **问题**：章节声明 applicable_versions Android 10-17，但未标注各查询的最低版本要求。Frame Timeline (Android 12+)、android.frames 模块 (Perfetto v38+)、android.monitor 模块、Java Heap counter track 名称等在不同版本有差异。

- **建议**：在每个主要查询模板旁添加版本标注。如：「Frame Timeline 查询需要 Android 12+ 且 Trace 配置包含 track_event」。

- **类型**：源码不精确

- **位置**：冷启动查询中 'ZygoteInit.xxx'

- **问题**：'ZygoteInit.xxx' 是占位符不是实际 slice 名称。AOSP 实际名称为 'ZygoteInit.main' 或 'ZygoteInit.native'。章节标注 [已验证] 但实际未验证。

- **建议**：改为具体名称 'ZygoteInit.main'，并标注该名称对应 Android 10+ 的 ART 实现。去掉 [已验证] 标记或改为 [待验证]。

- **类型**：源码准确性

- **位置**：SurfaceControl.Transaction 伪代码段

- **问题**：`t.setSize(surfaceControl, width, height)` 方法不存在于 Transaction API。Surface 尺寸通过 Builder.setSize() 创建时设置，运行时用 setCrop() 或 setMatrix()。

- **建议**：改为 `t.setCrop(surfaceControl, new Rect(0, 0, width, height))` 或改用 setMatrix()，并加注说明哪些是简化。

- **类型**：原理断裂

- **位置**：WMS 定位节 → relayoutWindow 内部流程

- **问题**：缺少 DisplayContent → DisplayArea → WindowToken → WindowState 层级结构说明。读者无法理解 performLayout 如何遍历窗口树、Z-order 如何确定。

- **建议**：新增 1-2 段解释 WMS 的窗口组织树结构，配图说明层级关系。

- **类型**：原理断裂

- **位置**：StartingWindow 工作原理节（步骤 3）

- **问题**："WMS 立即创建 StartingWindow"跳过了关键中间对象 StartingData/SplashScreenStartingData/StartingSurfaceDrawer。读者无法理解为什么 StartingWindow 不需要 App 进程参与。

- **建议**：展开 StartingWindow 的创建链路，引用 StartingData、SplashScreenStartingData 类。

- **类型**：原理断裂

- **位置**：Window 动画与过渡性能节

- **问题**：缺少动画值计算原理——transform 值从哪来？WindowAnimator 使用 Animation 对象？SpringAnimation？Choreographer frame callback？

- **建议**：补充 WindowAnimator 如何获取每帧的 transform 值，引用 AppWindowAnimator 或 WindowContainerAnimator。

- **类型**：版本差异

- **位置**：版本演进表 Android 12 行

- **问题**：SurfaceControl.Transaction "成为标准 API" 描述不精确。公开 API 从 Android 9 开始，Transaction 从 Android 10 可用。

- **建议**：修正为"SurfaceControl.Transaction API 完善（合并、批量操作增强）"，并将"首次公开 API"前移到 Android 9/10 行。

- **类型**：版本差异

- **位置**：Surface 创建流程节

- **问题**：缺少 Android 12 BLASTBufferQueue 引入对 Surface 创建/传递方式的影响。章节标注 applicable_versions 为 12-17，此差异应覆盖。

- **建议**：在 Surface 创建流程后增加版本差异注释，说明 Android 12+ 使用 BLASTBufferQueue 替代传统 BufferQueue 的变化。

- **类型**：交叉引用

- **位置**：关键 Slice 和 Track 表

- **问题**：`wm.pause_timeout` 是 AMS 的 Activity pause 超时机制，不是 WMS 的核心操作。放在 WMS Slice 表中容易误导。

- **建议**：移除此行，或在描述中标注"AMS 触发，间接影响 WMS 窗口切换"。

- **类型**：数据缺失

- **位置**：relayoutWindow 性能分析相关段落

- **问题**：缺少 relayoutWindow 的典型耗时数据（正常范围、异常阈值、不同类型的耗时差异）。

- **建议**：补充典型数据：纯属性更新型 1-5ms、Surface 创建型 10-50ms、performLayout 密集型 5-20ms。标注数据来源和测试条件。

- **类型**：元数据不一致

- **位置**：章节 frontmatter vs metadata/progress.json

- **问题**：frontmatter 标记 task9_state=reviewed/pipeline_stage=task6_pending，progress.json 标记 task9_state=pending/pipeline_stage=task9_pending。不同步。

- **建议**：同步 frontmatter 和 progress.json 的 pipeline 状态。

- **类型**：原理断裂

- **位置**：「Binder 跨层调用」小节

- **问题**：提及 Binder 线程池"内核唤醒空闲线程"但未解释线程池大小（默认 16 线程）和饱和行为。SystemServer 所有 Binder 线程忙时新请求排队，直接导致调用方阻塞——这是实际分析中常见但容易被忽略的瓶颈场景。

- **建议**：补充 Binder 线程池大小说明，增加一个"所有 Binder 线程忙导致 App 主线程阻塞"的 Trace 描述案例。

- **类型**：原理断裂

- **位置**：「Zygote：应用进程的孵化器」小节

- **问题**：描述了 fork 机制和 COW 但跳过了 fork 之后子进程如何从 native 进程进入 Java 世界的桥梁——`app_process` 二进制。读者无法理解从 fork 到 `ZygoteInit.main()` 之间发生了什么。

- **建议**：在 Zygote fork 段落后补充简短的 app_process 说明（1-2 句），或添加交叉引用到 1.2 系统启动全流程。

- **类型**：数据缺失

- **位置**：全文性能数据声明

- **问题**：Binder 延迟（10-100μs）、JNI 延迟（100-200ns / 1-5μs）、Zygote fork 时间（20-50ms）三项基础性能数据均标记 `[待验证]`。作为全书开篇章节，这些基线数据的可信度直接影响后续章节。

- **建议**：为每项数据至少提供一个具体来源（设备型号 + Android 版本 + 测量方法的引用），或将验证任务分配给下一个 research cycle。

- **类型**：交叉引用

- **位置**：全文

- **问题**：正文缺少对 1.2（系统启动全流程）的明确交叉引用。Zygote fork 和 SystemServer 启动流程与 1.2 高度相关，但读者只能通过 frontmatter 的 related_chapters 发现关联。

- **建议**：在 Zygote 和 SystemServer 段落后添加"详见 1.2 系统启动全流程"的交叉引用链接。

- **类型**：一致性

- **位置**：outline 扩展部分

- **问题**：outline 声明"与 iOS / HarmonyOS 分层架构的对比"为扩展内容，但正文完全未涉及。这属于 outline 与正文不一致。

- **建议**：如果不计划展开（合理选择），从 outline 扩展列表中移除该项；如果后续有素材，可补充简要对比表。

- **类型**：数据缺失

- **位置**：「ANR 在 Google Play Console 中的统计与影响」节，ANR 率阈值 0.38%/0.10%

- **问题**：Google Play Console 的 ANR 率阈值数字缺乏可追溯的官方来源链接。Android Vitals 的具体阈值可能随时间调整，需要标注数据来源和时效。

- **建议**：补充 Android Vitals 官方文档链接（https://developer.android.com/topic/performance/vitals/anr），并标注阈值查询日期。

- **类型**：交叉引用一致性

- **位置**：ContentProvider ANR 超时（1000ms）与 9.2 节的 ANR 触发条件

- **问题**：9.1 声称 ContentProvider 超时为 1000ms（已标记为 P0 错误），需确保 9.2 节不重复此错误。两节需要对 ContentProvider 超时的描述一致。

- **建议**：9.2 的 deep review 时重点检查 ContentProvider ANR 超时值是否准确。

- **类型**：知识盲区（低优先）

- **位置**：全文未提及 App 冷启动阶段 ContentProvider 初始化导致的 ANR

- **问题**：App 冷启动时 ContentProvider 的 onCreate() 在 Application.onCreate() 之前同步执行。如果 ContentProvider 初始化耗时，会阻塞应用启动，间接导致后续组件的 ANR。这是一个常见的实战场景。

- **建议**：在「常见问题与误区」节或版本演进节补充此场景的简要说明，交叉引用 8.2（App 启动全流程）。

- **类型**：源码准确性

- **位置**：「在 Perfetto 中的表现」段 → RenderThread 的首次 DrawQL

- **问题**："DrawQL" 不是 AOSP 或 Perfetto 中的标准术语。RenderThread 的 Trace slice 名为 "DrawFrame"，子操作为 syncFrameData/computeOrdering/flush commands。

- **建议**：改为 "RenderThread 的首次 DrawFrame slice" 或描述具体的子操作名。

- **类型**：知识盲区（高）

- **位置**：全文

- **问题**：android:profileable 清单属性（Android 12+）完全未提及。此属性对基准测试准确性至关重要——未设置的 release 构建无法被完整追踪。

- **建议**：在 CI/CD 构建配置或 FAQ 中补充 profileable 属性说明

- **类型**：原理断裂

- **位置**：CompilationMode.Partial 讨论

- **问题**：BaselineProfileRule 完全未提及。缺少生成环节，原理链断裂。

- **建议**：补充 BaselineProfileRule 使用方法，或至少添加对 8.7 节的显式交叉引用

- **类型**：原理断裂

- **位置**：「在 Perfetto 中的表现」段

- **问题**：Macrobenchmark 如何捕获 Perfetto Trace 的机制未解释

- **建议**：补充说明 Macrobenchmark 通过 Perfetto SDK 配置 Trace 数据源

- **类型**：数据缺失

- **位置**：CompilationMode 节 + FAQ

- **问题**：Baseline Profile "30% 改善"无具体来源；"5-15% 波动"无数据支撑。全文无真实 benchmark 数值

- **建议**：补充数据来源链接，添加典型 benchmark 数值案例

- **类型**：内容深度建议

- **位置**：版本演进部分（"待验证"标注部分）

- **问题**：Android 13-15 的 ANR 分析机制变化描述为"以上基于公开 Release Notes 推断"，缺乏具体验证

- **建议**：确认版本差异是否真实影响 ANR 分析流程，如影响较大需补充具体案例；如无影响可简化描述

- **review 日志**：logs/review/2026-04-16-10-review.md

- **类型**：源码准确性

- **位置**：ART GC 关键源码路径代码片段

- **问题**：CollectGarbageInternal() 代码是伪代码但标注为 AOSP 源码。实际 ART 不直接调用 collector->PausePhase()/ConcurrentPhase()，而是通过 collector->Run() 分阶段执行。且标注 @ android-15 但 frontmatter 声明 verified against android-14

- **建议**：替换为实际 AOSP 代码，或在代码注释中明确标注「简化示意，非实际 AOSP 代码」

- **类型**：数据缺失

- **位置**：「STW 停顿的累积效应」段，「实测平均约 1.83ms」

- **问题**：GC STW 暂停数据缺少测量条件（设备型号、Android 版本、Heap 大小、GC 负载类型）

- **建议**：补充测量条件，或标注数据来源（如 Android 官方性能数据、某设备实测等）

- **类型**：源码准确性

- **位置**：「Binder 线程池耗尽」段

- **问题**："Android 默认为每个进程分配最多 16 个 Binder 线程"无引用

- **建议**：补充引用 AOSP ProcessState.cpp 中 DEFAULT_MAX_BINDER_THREADS 定义

- **类型**：原理断裂

- **位置**：「SQLite WAL 模式的四级锁」

- **问题**：称"四级文件锁"但实际描述了五个状态（UNLOCKED/SHARED/RESERVED/PENDING/EXCLUSIVE）。PENDING 在 SQLite 文档中是正式的锁状态，不是"过渡态"。SQLite 官方文档明确列出 5 个 locking levels

- **建议**：修正为"五级文件锁机制"，将 PENDING 作为正式锁级别描述而非过渡态

- **类型**：原理断裂

- **位置**：「从 apply() 到 ANR 的完整链路」段

- **问题**：只提到 handlePauseActivity() 触发 waitToFinish()，未提及 handleStopActivity() 和 handleSleeping() 也会触发

- **建议**：补充其他触发点，帮助读者理解 apply() ANR 不仅发生在 Activity 切换时

- **类型**：版本差异

- **位置**：版本演进节

- **问题**：Android 14 后台 broadcast 超时变化描述过于笼统（"后台 Broadcast 超时缩短"），实际 Android 14 引入了 CPU-starved 分级机制，60s 可扩展到 120s

- **建议**：补充 Android 14 的具体超时变化细节

- **类型**：知识盲区

- **位置**：全文缺失

- **问题**：未提及 InputConnection ANR（5s 超时）和 Trampoline ANR 场景

- **建议**：在「常见问题与误区」中补充提及，或在扩展阅读中引用

- **类型**：源码准确性

- **位置**：参考资料段 "frameworks/base/libs/hwui/renderthread/OpenGLRenderer.cpp"

- **问题**：Android 10+ HWUI 统一 Skia Pipeline 后，OpenGLRenderer 类已不存在。android-16.0.0_r1 中应引用 SkiaOpenGLPipeline 相关路径

- **建议**：更新为 frameworks/base/libs/hwui/pipeline/skia/ 或标注该路径适用于 Android 9 及之前版本

- **类型**：原理断裂

- **位置**："同步机制" 小节 Fence 伪代码

- **问题**：consumerReleaseFence->signal() 暗示 Fence 由消费者手动 signal。实际 Fence 由 GPU/驱动在操作完成时自动 signal，消费者只负责创建和等待

- **建议**：重写伪代码，体现 Fence 的创建者（生产者创建 acquire fence，消费者创建 release fence）和自动 signal 语义

- **类型**：版本差异

- **位置**："BufferQueue 生产者-消费者模型" 全节

- **问题**：描述基于 Legacy BufferQueue 模型。Android 12+ 引入 BlastBufferQueue 后，App 与 SurfaceFlinger 间不再通过 Binder IPC 传递 buffer，改为共享内存 + fence。这是近 4 个版本最重要的图形架构变更

- **建议**：在节开头添加版本说明，描述 BlastBufferQueue 的关键差异（减少 Binder 开销），并在数据流图中区分两个版本

- **类型**：知识盲区

- **位置**："SurfaceFlinger 合成" 小节

- **问题**：未解释 SurfaceFlinger 只在有新 buffer 时才触发合成（vs. 每个 VSync 都合成）。这解释了 Trace 中 SurfaceFlinger 合成间隔不均匀的现象

- **建议**：补充 SurfaceFlinger 的合成触发条件（有 queued frame / VSync-sf 到来 + dirty region）

- **类型**：原理断裂

- **位置**："UI 线程与 RenderThread 的协作" 小节

- **问题**：未提及 syncFrameState 同步点，这是主线程可能阻塞等待 RenderThread 的关键位置

- **建议**：补充 syncFrameState 的作用和 Trace 中的表现

- **类型**：原理断裂

- **位置**："显示输出" 小节最后一段

- **问题**：色域转换主要发生在 GPU 渲染或 SurfaceFlinger 合成阶段，不是显示硬件的最后一步

- **建议**：移至 SurfaceFlinger 合成节或删除，避免误导

- **类型**：数据缺失

- **位置**：HWUI 概述段 "复杂 2D 图形渲染性能相比纯 CPU 软件渲染提升 5-10 倍"

- **问题**：无引用来源、无测量条件

- **建议**：补充引用或标注为[待验证：需实测数据]

- **类型**：版本差异

- **位置**："版本演进" 节 + BufferQueue 节

- **问题**：三缓冲 maxBufferCount 在不同版本的默认值变化未说明；BlastBufferQueue 对 BufferQueue 接口的改变未在正文中体现

- **建议**：在 BufferQueue 节添加版本标注，说明 Android 12 前后的架构差异

- **类型**：交叉引用

- **位置**：总结段 "SurfaceFlinger 把多个 App 的缓冲区按 Z-Order 叠加后交给 HWC 输出到屏幕"

- **问题**：忽略了 GPU 合成回退路径，与正文合成节描述不一致

- **建议**：改为 "SurfaceFlinger 优先通过 HWC 合成，必要时回退 GPU 合成，最终输出到屏幕"

- **类型**：需补充素材

- **位置**：技术数据基准

- **问题**：AnodTest基准测试的具体定义和数据来源缺失

- **建议**：需要补充AnodTest基准测试的详细定义、测试方法、数据来源链接

- **review 日志**：logs/review/2026-04-16-17-review.md

- **类型**：需补充素材

- **位置**：测试环境

- **问题**：GAPS测试的具体环境和配置参数不明确

- **建议**：需要补充GAPS测试的具体设备、Android版本、测试配置等环境参数

- **review 日志**：logs/review/2026-04-16-17-review.md

- **类型**：需补充素材

- **位置**：数据对比

- **问题**：动态触达率57.44%缺少对比基线说明

- **建议**：需要补充动态触达率的对比基线，说明与之前方案的对比关系

- **review 日志**：logs/review/2026-04-16-17-review.md

- **类型**：源码准确性

- **位置**：「lmkd 的杀进程策略」段，min_score_adj 描述

- **问题**：称"min_score_adj 通常设置为 201（即 PREVIOUS_APP_ADJ + 1）"。AOSP ProcessList.java 中 PREVIOUS_APP_ADJ = 201。201 就是 PREVIOUS_APP_ADJ 本身，不是 PREVIOUS_APP_ADJ + 1（那应该是 202）。数学关系错误。

- **建议**：改为"min_score_adj 通常设置为 201（即 PREVIOUS_APP_ADJ）"

- **类型**：版本差异

- **位置**：「PSI 信号与 lmkd 的触发机制」段

- **问题**：「在 Android 高版本上（默认启用 use_psi 属性为 true）」中"高版本"模糊。PSI 从 Android 10 开始作为 lmkd 默认信号源。

- **建议**：改为"从 Android 10 开始，PSI 已取代了早期的 vmpressure 机制成为 lmkd 的主要信号来源（ro.lmk.use_psi 默认为 true）"

- **类型**：版本差异

- **位置**：「ART GC 在低内存下的触发策略」段

- **问题**：「在 Android 8.0（Oreo）之后」表述模糊。"之后"通常不含 8.0 本身。CC collector 从 Android 8.0 起引入。

- **建议**：改为"从 Android 8.0 开始"

- **类型**：版本差异

- **位置**：mm_events 段 + frontmatter applicable_versions

- **问题**：mm_events 仅在 Android 12+ 可用，但 applicable_versions 声明 Android 10-16。未讨论 Android 10/11 如何追踪内存压力（这两版本依赖 vmscan ftrace + 自定义 mem_event，无 mm_events）。

- **建议**：在 mm_events 段开头添加版本适用说明，并在"综合判断"段中区分 10/11 和 12+ 的可用信号源

- **类型**：数据缺失

- **位置**：MGLRU 段末尾 [自动发现] 段落

- **问题**：「预示着未来的 Android 设备在同样 RAM 容量下将能维持更多的后台应用」是推测性结论，非可验证技术事实。

- **建议**：删除推测句，保留 MGLRU + ZRAM multi-comp 的具体技术收益（如减少 thrashing 比例、压缩比提升数据）

- **类型**：数据缺失

- **位置**：ZRAM 调优段 + 低端机优化段

- **问题**：(1) "Qualcomm 的调优指南建议设为物理 RAM 的 75%"缺少引用链接。(2) "后台进程上限从标准设备的 32 个降到 8-12 个"缺少来源和具体配置项名称。(3) "Android 16 Go 版本扩展到了 4GB RAM 设备"需要官方文档验证。

- **建议**：补充 Qualcomm 文档链接和年份；标注后台上限来源（ActivityManager 常量还是厂商自定义配置）；验证 Android 16 Go 的 RAM 上限变更并提供链接

- **类型**：交叉引用

- **位置**：lmkd 段落 vs §4.4 Low Memory Killer

- **问题**：本章节 lmkd 段落包含较多 lmkd 工作机制细节（PSI 监听、oom_score_adj 杀进程策略），与 §4.4 内容重叠。本章节应侧重"低内存的影响"而非 lmkd 机制。

- **建议**：精简本章节的 lmkd 机制描述，侧重"杀进程后的影响"（冷启动代价、恶性循环），机制细节指向 §4.4

- **类型**：版本差异

- **位置**：案例四 AlarmManager 代码 — PendingIntent.FLAG_IMMUTABLE

- **问题**：代码使用 PendingIntent.FLAG_IMMUTABLE，但章节 applicable_versions 从 Android 8.0 开始。FLAG_IMMUTABLE 从 Android 12 (API 31) 起为必需标志，Android 8-11 可使用 FLAG_MUTABLE 或不设 flag。

- **建议**：在代码旁标注「Android 12 起必需 FLAG_IMMUTABLE」注释，或使用条件判断。

- **类型**：数据缺失

- **位置**：案例一/二/三/五的效果对比表

- **问题**：多处效果对比数据缺少实验来源。如案例一「4h 待机耗电 40%→3%」、案例二「25%→3%」、案例三「15%→5%/3%」、案例五「15%→3%」。这些数据看起来是估算值而非实际测试结果。

- **建议**：标注为「典型值（基于 X 设备 Y 系统测试）」或改为定性描述（「从严重异常降至系统待机水平」）。

- **类型**：知识盲区

- **位置**：案例三「长期：Push 替代 Pull」

- **问题**：推荐 FCM 作为长期方案，但未讨论 FCM 的局限性（消息大小限制 4KB、需要 Google Play Services、中国大陆不可用）以及何时选择 WebSocket 长连接替代。

- **建议**：补充 FCM 的适用场景和限制，提及国内需使用厂商推送通道或自建 WebSocket。

- **类型**：知识盲区

- **位置**：案例三 Radio 状态机描述

- **问题**：描述基于 3G/LTE 模型（30-60秒不活动期进入 Standby）。5G NR 使用 DRX/CDRX 机制，状态转换时间和功耗特征不同，但未提及。

- **建议**：补充说明 Radio 状态机模型因网络技术而异，5G NR 场景下需要额外关注 CDRX 配置对功耗的影响。

- **类型**：版本差异

- **位置**：版本演进表 Android 4.1 条目

- **问题**：声称"Android 4.1 (API 16) 引入 InputFlinger 框架"，但 InputManager/InputReader/InputDispatcher 的分层设计在 Android 1.0 就存在。Android 4.1（Project Butter）引入的是 Choreographer 和 VSync 机制，不是 InputFlinger 重构。InputFlinger 的代码目录重组发生在更晚的版本。

- **建议**：核实此条目。如果指 InputManagerService 重构，明确标注；如果不确定来源，标注 [待验证] 或删除。

- **类型**：版本差异

- **位置**：版本演进表 Android 15 条目

- **问题**："输入法与 Input 系统交互优化，改善 IME 切换时的输入延迟"过于模糊，缺少具体 AOSP 变更或功能名称。

- **建议**：补充具体的 commit hash 或功能名称，或标注 [待验证]。

- **类型**：数据缺失

- **位置**："为什么是 5 秒"一节

- **问题**：ANR 超时机制一节纯原理描述，缺少 Perfetto Trace 数据支撑。缺少 wq 从正常值增长到触发 ANR 的数值描述。

- **建议**：补充一个 Perfetto Trace 场景描述：正常情况下 wq 在 0-2 波动；ANR 前兆时 wq 持续 >5 超过 5 秒；最终触发 ANR 时 wq 值突然归零并出现 ANR trace tag。给出具体数值范围。

- **类型**：源码准确性+版本差异

- **位置**：Project Butter 节 Choreographer 回调序列

- **问题**：Android 4.1 段列出 INPUT→ANIMATION→INSETS_ANIMATION→TRAVERSAL→COMMIT 完整回调序列。INSETS_ANIMATION 为 API 30 新增，COMMIT 为 API 24 新增。Android 4.1 原始回调仅为 INPUT→ANIMATION→TRAVERSAL。

- **建议**：在 Android 4.1 段只列出 INPUT→ANIMATION→TRAVERSAL，在后续版本（如 Android 7.0 段和 Android 11 段）分别说明 COMMIT 和 INSETS_ANIMATION 的引入。

- **类型**：原理断裂

- **位置**：RenderThread 段的 eglSwapBuffers/glFinish 描述

- **问题**：将 Android 4.x 主线程卡顿的核心原因归结为 glFinish 阻塞，但更根本的问题是 drawDisplayList() 整个 GPU 命令执行过程在主线程同步调用。

- **建议**：重写该段的因果链：Android 4.x 中 drawDisplayList() 在主线程同步执行 GPU 命令（包括命令提交和等待完成），这使得整个 GPU 工作时间都计入主线程。RenderThread 将全部 GPU 命令提交和执行移到独立线程，主线程只需录制 RenderNode。

- **类型**：版本差异

- **位置**：版本演进时间线表

- **问题**：完全跳过 Android 6.0、11、14 三个大版本。Android 6.0 有 DisplayListCanvas→RecordingCanvas 更名和嵌套滑动机制；Android 11 有 BufferQueue 行为变更（BLASTBufferQueue 预演）；Android 14 有渲染行为变更。

- **建议**：补充 Android 6.0、11、14 三个版本的渲染相关关键变更到时间线表中。

- **类型**：版本差异

- **位置**：Android 16 节 ANGLE 描述

- **问题**：称 Android 16 集成了 ANGLE 作为系统级驱动。实际上 ANGLE 在 Android 12 已可选集成，13 成部分 App 默认 OpenGL ES 实现，15 大幅扩展覆盖范围。Android 16 是进一步扩大而非首次集成。

- **建议**：改为「Android 12 开始可选集成 ANGLE 作为 OpenGL ES 到 Vulkan 的翻译层，此后逐步扩大覆盖范围。Android 16 将 ANGLE 作为所有 OpenGL ES 应用的默认实现，OpenGL ES 进入维护模式。」

- **类型**：原理断裂

- **位置**：first-stage init 段 — FirstStageMount 机制

- **问题**：提到 FirstStageMount::DoFirstStageMount() 挂载启动必需分区，但未解释它如何决定挂载哪些分区（A/B slot 选择逻辑、分区决策依据）。读者无法理解为什么某些设备 init 阶段特别慢（如 A/B slot 切换后需要验证新分区）。

- **建议**：补充 FirstStageMount 的决策逻辑简述：读取 boot control HAL 确定当前 active slot → 构建分区挂载列表 → 挂载 system/vendor/product 等分区。

- **类型**：原理断裂

- **位置**：开机性能优化段 — task_profiles

- **问题**：提到 task_profiles 替代了 raw cpuset 写法，但未解释 task_profiles 的机制（它组合了调度策略、uclamp、cpuset 等）和与旧方式的对比。读者可能不清楚为什么新方案更好。

- **建议**：补充 task_profiles 的核心机制一句话说明（将调度相关策略组合为命名 profile，在 init rc 中通过 task_profiles 字段指定），或者标注交叉引用到 5.1 节（Linux 进程调度基础）。

- **类型**：知识盲区

- **位置**：boot_progress 里程碑事件列表

- **问题**：列出的 boot_progress_* 事件不完整。缺少：boot_progress_preload_start / boot_progress_preload_end（Zygote 预加载起止）；boot_progress_pms_data_scan_start / boot_progress_pms_data_scan_end（PMS 数据扫描）。这些事件在 event log 中常见，用于定位 Zygote 和 PMS 阶段的子环节耗时。

- **建议**：在 boot_progress 事件列表中补充 preload_start/end 和 pms_data_scan 事件。

- **类型**：源码准确性

- **位置**：「Zygote fork SystemServer 的触发机制」段 — ZygoteInit.java 行号

- **问题**：引用了非常具体的行号（行 844-850、行 902-912、行 693-801、行 780、行 792-798、行 893）。这些行号标注了 @ android-16.0.0_r1 但未实际验证，且代码行号在不同补丁版本间容易偏移。ZygoteServer.java 行 394 同样需要验证。

- **建议**：将行号标注改为范围描述（如「main() 方法后半段」）或在每处行号旁加 [待验证] 标注。已标注 last_verified_against android-16.0.0_r1，但行号级别的精度需要二次确认。

- **类型**：知识盲区

- **位置**：开机性能优化段 — APEX 激活

- **问题**：OTA 后首启卡在 APEX 激活的排查建议仅一笔带过（"检查 APEX 激活"），未解释 APEX 激活机制（apexd 在 first-stage init 后半段激活新 APEX 模块，涉及 dm-verity 校验和 loop 设备挂载）及对启动时间的具体影响路径。

- **建议**：在 init 阶段或扩展部分补充 apexd 激活的简要机制和典型耗时影响，或标注交叉引用到 1.7（ART 编译管线）的 APEX 相关内容。

- **类型**：源码准确性

- **位置**：JIT 代码片段 — MaybeDoJitCompilation 方法名

- **问题**：`MaybeDoJitCompilation` 在 AOSP 中不存在。实际方法为 `Jit::MaybeCompileMethod(ArtMethod*, Thread*)`，位于 `art/runtime/jit/jit.cc`。`method->GetCounter()` 非标准 API。即使标注"简化示意"，方法名虚构仍会误导读者。

- **建议**：修正为 `MaybeCompileMethod`，或将注释改为 `[伪代码示意]`。

- **类型**：版本差异

- **位置**：全文 bg-dexopt 引用（至少 3 处）

- **问题**：bg-dexopt 是 Android 13 及以下的术语。Android 14+ 后台编译由 ART Service 的 MaintenanceJobs 管理。applicable_versions 声明 7.0-17。

- **建议**：首次出现 bg-dexopt 处加版本说明，后续使用保持一致。

- **类型**：版本差异

- **位置**：版本演进表

- **问题**：版本表仅 7 条但 applicable_versions 覆盖 7.0-17。遗漏 Android 8/10/11/13/15。

- **建议**：至少补充 Android 8（JIT code cache 调整）、10（hidden API 限制影响编译假设）、13（Baseline Profiles Mainline 推送能力）。

- **类型**：数据缺失

- **位置**：多个 [待验证] 标注处

- **问题**：冷启动差距 30%、Baseline Profiles 提升 30% 代码执行速度、JIT 代码缓存 4MB 三个核心量化断言均 [待验证]。这些数据支撑文章核心论点，不应长期悬置。

- **建议**：定位 Google 官方基准测试报告出处，替换 [待验证] 为具体引用。如确实无法找到精确来源，改为定性描述。

- **类型**：源码准确性

- **位置**：JIT 代码缓存默认值 — dalvik.vm.jitinitialsize/jitmaxsize

- **问题**：默认 64KB/64MB 缺少版本和设备条件标注。不同 SoC 和 Android 版本可能有不同默认值。

- **建议**：标注验证版本（如"基于 android-17-beta3 默认配置"），或改为"典型配置值"并说明来源。

- **类型**：版本差异

- **位置**：CPU Profiler 三模式对比表

- **问题**：Callstack Sample 底层工具标注为"Simpleperf"，缺少 ART Java frame unwinding 的语境说明。读者可能误以为 Simpleperf 只能做 native profiling。

- **建议**：将表格中 Callstack Sample 的底层工具改为"Simpleperf（含 ART Java frame unwinding）"，或在正文补充说明 Simpleperf 在 Android Studio 中的集成方式。

- **类型**：版本差异

- **位置**：全文 applicable_versions

- **问题**：applicable_versions 统一为 API 26-36，但各功能对最低 API 要求不同（System Trace 从 API 16+、JVMTI 从 API 26+、profileable 从 API 29+、Power Profiler 需要 Android 10+且硬件支持）。

- **建议**：在各模块描述处标注最低 API 要求，或在前言中用一个表格汇总各功能的最低版本。

- **类型**：版本差异

- **位置**：全文缺少 AS 版本维度覆盖

- **问题**：作为工具类章节，只提到 Koala 和 Hedgehog 两个 AS 版本，遗漏了多个重要 Profiler 变更。

- **建议**：新增"版本演进"小节或嵌入各模块中，覆盖至少 Flamingo/Giraffe/Iguana/Jellyfish/Koala 的 Profiler 关键变更。

- **类型**：数据缺失

- **位置**：「Profiler 的整体结构」段，"启动速度提升了约 60%"

- **问题**：60% 这个数字未标注来源。

- **建议**：补充引用来源（如 AS release notes 或 Google 官方博客），或改为更保守的"显著提升"并标注 [待验证]。

- **类型**：数据缺失

- **位置**：「各 Profiler 模式的性能开销」段，"约 28% 的性能提升"

- **问题**：表述为"根据 Google 的测试数据"过于笼统。

- **建议**：补充具体引用来源（如 Google I/O 2019 演讲或 Android Developers Blog 文章）。

- **类型**：交叉引用

- **位置**：frontmatter

- **问题**：related_chapters 字段完全缺失。正文引用了 §5.4、§13.5、§14.2、第 13 章但未在 frontmatter 声明。

- **建议**：添加 related_chapters: ["5.4", "13.3", "13.5", "13.7", "14.2", "14.11"]

- **类型**：交叉引用错误

- **位置**：文末交叉引用段

- **问题**：三处交叉引用的章节编号与实际内容不匹配：(1) "2.1 BufferQueue 机制"应为"2.13 图形缓冲区管理(BufferQueue)"；(2) "2.5 SurfaceFlinger"应为"2.6 SurfaceFlinger 与合成"；(3) "2.6 同步机制"应为"2.16 Sync Fence 框架与帧同步机制"。链接文件路径正确，仅显示文字中的章节号错误

- **建议**：将交叉引用文字修正为正确章节号+标题：(1) [2.13 图形缓冲区管理 (BufferQueue)]；(2) [2.6 SurfaceFlinger 与合成]；(3) [2.16 Sync Fence 框架与帧同步机制]

- **类型**：源码准确性

- **位置**：全文

- **问题**：涉及 Choreographer、RenderThread、BLASTBufferQueue、FrameTimeline 等核心类，但未标注任何 AOSP 源码路径（如 frameworks/base/libs/hwui/renderthread/RenderThread.cpp）或关键方法签名

- **建议**：在关键机制描述处补充 AOSP 路径和方法名。优先补充：RenderThread.syncFrameState()、BLASTBufferQueue.acquireNextBufferLocked()、SurfaceFlinger::latchBuffer

- **类型**：数据缺失

- **位置**："Trace 视角"段落中的耗时表格

- **问题**：表格中所有"正常耗时"值（doFrame < 8ms 等）隐含 60Hz 假设，90Hz 帧预算 11.1ms、120Hz 仅 8.3ms。未标注适用刷新率

- **建议**：表格增加"适用刷新率"列，或按 60/90/120Hz 分别给出参考值

- **类型**：原理断裂

- **位置**："第四阶段：BLAST 提交与 SurfaceFlinger 合成"小节

- **问题**：文章将 BLAST Transaction 称为"BLAST 模型的核心变化点"，但从未解释变化前的 Legacy 模型。读者无法理解"变了什么"

- **建议**：在第四阶段之前（或章节开头）增加一段"BLAST 之前的 Legacy 模型"作为背景铺垫：Legacy 模式下 BufferQueue 的 Consumer 端在 SF 进程，BLAST 将 Consumer 移入 App 进程（BBQ），App 直接构造 Transaction 异步发给 SF

- **类型**：版本差异

- **位置**：全文（frontmatter 标注 Android 11-16）

- **问题**：正文仅提到 FrameTimeline（Android 12）一个版本变化点。Android 11 的 BLAST 引入、Android 13 的渲染预测改进、Android 14 的 120Hz 优化和 FrameRateOverride 变更均未涉及

- **建议**：增加"版本演进"小节或在各阶段中穿插版本标注。最低要求：标注 BLAST 引入版本（Android 11）和 FrameTimeline 引入版本（Android 12）

- **类型**：数据缺失

- **位置**："第二阶段：Sync — 移交蓝图"

- **问题**："syncFrameState 正常情况下耗时在 1-2ms"无数据来源标注

- **建议**：补充数据来源（如"在 Pixel 7 Android 14 的实测中..."）或改为范围描述并标注 [待补充：实测数据]

- **类型**：需确认 + 需补充素材

- **位置**：优化策略 > 策略一：合并窗口

- **问题**：代码示例推荐 `BottomSheetDialogFragment`，注释称其为"View 级别的 BottomSheet"，但 `BottomSheetDialogFragment` 实际仍创建独立 Window（继承自 AppCompatDialogFragment → AppCompatDialog → Dialog），并不会合并到 Activity 的 Surface。真正 View 级别无额外 Window 的方案应使用 `BottomSheetBehavior` + `CoordinatorLayout`，或直接在 Activity 布局内用 View 实现。

- **建议**：将推荐方案改为使用 `BottomSheetBehavior` 绑定到 Activity 布局内的 View，或标注 `BottomSheetDialogFragment` 仍会创建独立 Window 但比普通 Dialog 轻量。

- **review 日志**：logs/review/2026-04-17-08-review.md

- **类型**：需确认

- **位置**：全链路执行流程 > 阶段三

- **问题**：文中描述"UI Thread 在 Sync A 时被阻塞（`syncFrameState`），直到 RenderThread 完成同步。这意味着 Window B 的 Traversal 可能需要等 Window A 的 Sync 完成后才能开始"。`syncFrameState` 的阻塞行为在不同 Android 版本中有差异——在某些版本中 UI Thread 仅短暂阻塞以交换 DisplayList 引用即返回，不会等到 DrawFrame 完成。需确认具体版本下的行为。

- **建议**：标注 `[待验证：syncFrameState 阻塞粒度在不同 Android 版本的表现]`，或明确说明此处描述适用于哪个 Android 版本范围。

- **review 日志**：logs/review/2026-04-17-08-review.md

- **类型**：需补充素材

- **位置**：全文

- **问题**：章节 applicable_versions 标注为 Android 9-16，但正文未讨论任何版本间的行为差异。例如：(1) Android 12 对 `BufferQueue` 和 `syncFrameState` 的改动；(2) Android 10 引入 Multi-resume 后 Choreographer 分发行为的变化；(3) Android 14+ 对分屏模式的渲染管线调整。

- **建议**：增加"版本演进"小节，或在各关键段落中补充版本差异标注。至少覆盖 Android 10（Multi-resume）、Android 12（RenderThread 改动）两个关键版本节点。

- **review 日志**：logs/review/2026-04-17-08-review.md

- **类型**：源码错误

- **位置**：L124-126 Layout 调用树

- **问题**：`ViewGroup.dispatchDraw()` 出现在 Layout 阶段调用树中。dispatchDraw() 是 Draw 阶段方法，不属于 Layout 流程。Layout 实际流程：View.layout() → View.onLayout() → ViewGroup.onLayout() 遍历子 View 调用 child.layout()

- **建议**：移除 dispatchDraw()，替换为 ViewGroup.onLayout() → child.layout() 的正确调用链

- **类型**：源码错误

- **位置**：L157-159 Choreographer 调用树

- **问题**：方法名 callInputCallbacks/callAnimationCallbacks/callTraversalCallbacks 不是 AOSP 实际方法名

- **建议**：修正为 doCallbacks(CALLBACK_INPUT, ...) / doCallbacks(CALLBACK_ANIMATION, ...) / doCallbacks(CALLBACK_TRAVERSAL, ...)

- **类型**：源码错误

- **位置**：L190-194, L204-205, L241-242 SurfaceFlinger DisplayHardware

- **问题**：DisplayHardware.composerCallback() / DisplayHardware.vsync() / DisplayHardware.flip() 不是现代 AOSP 中的标准方法。SurfaceFlinger 通过 HWComposer 和内部 MessageQueue 处理 VSync，不存在 DisplayHardware 类

- **建议**：替换为正确的 SurfaceFlinger 内部调用链：HWComposer::vsync() → SurfaceFlinger::onVsyncReceived() → MessageQueue::invalidate() → handleMessageRefresh()

- **类型**：源码错误

- **位置**：L367-368 OpenGLRenderer.cpp

- **问题**：Android 10+ HWUI 统一走 Skia Pipeline，OpenGLRenderer 独立类在 Android 16 中不存在

- **建议**：标注为历史版本代码示例，或更新为 SkiaOpenGLPipeline / SkiaVulkanPipeline 路径

- **类型**：原理断裂

- **位置**：BufferQueue 章节（L280-340 区域）

- **问题**：未说明 SurfaceFlinger 如何被通知有新帧可用

- **建议**：补充通知链：queueBuffer() → ConsumerListener.onFrameAvailable() → Layer::onFrameAvailable() → SurfaceFlinger::signalLayerUpdate()

- **类型**：原理断裂

- **位置**：BufferQueue 章节

- **问题**：缺少缓冲区状态转换说明

- **建议**：补充 Free → Dequeued → Queued → Acquired → Released → Free 的状态机描述

- **类型**：原理断裂

- **位置**：Draw 过程到 VSync 同步之间的衔接

- **问题**：未说明 invalidate() 如何最终触发 Choreographer 申请 VSync

- **建议**：补充 invalidate() → ViewRootImpl.scheduleTraversals() → Choreographer.postCallback() → scheduleFrameLocked() → scheduleVsync() 的完整链路

- **类型**：数据缺失

- **位置**：HWUI 概述段（L448 区域）

- **问题**："复杂 2D 图形渲染性能相比纯 CPU 软件渲染提升 5-10 倍"无数据来源

- **建议**：补充 benchmark 来源（官方博客/Google I/O 演讲），或改为更保守的定性描述

- **类型**：知识盲区

- **位置**：BufferQueue 与 App 之间的接口

- **问题**：缺少 Surface / SurfaceControl / SurfaceTexture 的介绍

- **建议**：在 BufferQueue 章节前或后增加一段说明这些 API 层封装与 BufferQueue 的关系

- **类型**：版本差异

- **位置**：版本演进段（L660 区域）

- **问题**：Android 8.0 "预合成重构"表述模糊；缺少 Android 7.0 Vulkan 引入和 Android 14/15 变更

- **建议**：将 Android 8.0 改为具体描述 HWC2 HAL 引入；补充 Android 7.0 Vulkan 引入里程碑

- **类型**：源码准确性

- **位置**：SQLite 锁级别描述段

- **问题**：PENDING 锁被描述为"RESERVED 到 EXCLUSIVE 的过渡态"，实际上 PENDING 是独立锁级别，用于防止 writer starvation（阻塞新读者但不阻塞现有读者）。

- **建议**：明确 PENDING 为 SQLite 五级锁中的独立一级，强调其防止写饥饿的作用。

- **类型**：交叉引用

- **位置**：frontmatter related_chapters

- **问题**：§9.3 列在 related_chapters 中但正文中未被引用。

- **建议**：在正文中适当位置添加对 §9.3 的引用，或将 §9.3 从 related_chapters 移除。

- **类型**：数据缺失

- **位置**：低内存 GC 段 — "STW 1-3ms（实测平均约 1.83ms）"

- **问题**：定量数据无测量条件（设备、堆大小、GC 类型、Android 版本、样本数）。

- **建议**：补充测量条件，或改为定性描述（"通常在 1-5ms 范围内"）并标注来源。

- **类型**：版本差异

- **位置**：版本演进段

- **问题**：缺少 Android 13 对 SCHEDULE_EXACT_ALARM 权限的收紧（从默认授予改为需用户授权或声明 USE_EXACT_ALARM）。

- **建议**：在 Android 12 条目后补充 Android 13 的权限收紧变更。

- **类型**：知识盲区

- **位置**：SharedPreferences apply() 段

- **问题**：缺少多进程 SharedPreferences ANR 场景。Google 已明确不建议多进程使用 SP，但实际项目中仍常见。

- **建议**：补充一段"多进程 SP 的额外风险"，并指向 Jetpack DataStore 作为替代方案。

- **类型**：知识盲区

- **位置**：缺失

- **问题**：缺少 StrictMode 作为 ANR 预防工具的提及。

- **建议**：在"预防方案"或"常见问题与误区"中添加 StrictMode 开发期检测的推荐。

- **类型**：数据缺失

- **位置**：Binder 线程池段

- **问题**："默认最多 16 个 Binder 线程"缺少典型使用模式数据和观察方法。

- **建议**：补充如何在 Perfetto 中观察 Binder 线程数（Binder thread track），以及正常 App 的典型占用范围。

- **类型**：原理断裂

- **位置**：SharedPreferences apply() → waitToFinish() 链路

- **问题**：未解释 WHY handlePauseActivity() 会调用 waitToFinish()。设计意图是确保 Activity 进入后台前数据持久化（进程可能被杀）。

- **建议**：补充一句设计意图说明，让读者理解这不是 bug 而是有意为之的数据安全机制。

- **类型**：L4 活人感（无个人经验痕迹）

- **位置**：全文多处

- **问题**：章节整体为教科书/参考手册风格，无 Gracker 个人经验痕迹，缺少"我/我们曾经"的实战叙述

- **建议**：在关键位置穿插实战案例（如"我在分析 XX App 时，用 P99 而不是均值发现了..."），增强工程师经验感

- **review 日志**：logs/review/2026-04-17-10-review.md
  - ---

- **类型**：L3 内容深度（Active/Idle Power 节单薄）

- **位置**：功耗指标 — Active/Idle Power 节

- **问题**：Active/Idle Power 功耗分析节内容单薄，全文有 `[待补充: Perfetto Power track 的具体使用方法和截图示例]` 标注

- **建议**：补充 Perfetto Power track 的使用方法，说明如何观察电流曲线和子系统功耗分布，给出实际 Trace 截图描述或标注 `[待补充：Trace 截图]`

- **review 日志**：logs/review/2026-04-17-10-review.md
  - ---

- **类型**：L3 代码准确性（reportFullyDrawn 示例冗余）

- **位置**：TTFD 节 — reportFullyDrawn() 代码示例

- **问题**：if-else 两分支执行完全相同的 `reportFullyDrawn()` 调用，版本分支无实际差异。注释提到 API 31+ 可传更精确时间戳，但代码未使用

- **建议**：补充 `reportFullyDrawn(long duration)` API 31+ 用法，或简化为单行调用并调整注释

- **review 日志**：logs/review/2026-04-17-10-review.md

- **类型**：源码准确性（API 归属错误）

- **位置**：流畅性指标 — Frame Time 与分位数节

- **问题**：FrameMetricsAggregator 被描述为"Android 9.0+, API 28"的平台 API，但实际是 AndroidX Jetpack 库（`androidx.metrics:metrics-performance`），最低支持 API 16。描述可能误导读者认为这是平台内置 API

- **建议**：修正为"Jetpack 的 FrameMetricsAggregator（需引入 `androidx.metrics:metrics-performance` 依赖，最低 API 16，API 24+ 可获取详细分阶段数据）"

- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md
  - ---

- **类型**：源码准确性（适用版本不一致）

- **位置**：Frontmatter applicable_versions

- **问题**：applicable_versions 声明 "Android 8.0 (API 26) - Android 16 (API 36)"，但文中引用的 FrameMetrics API 自 API 24 (Android 7.0) 起可用

- **建议**：将下界调整为 API 24，或在文中注明 FrameMetrics 是 API 24+ 特性，章节主要讨论的内容适用 API 26+

- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md
  - ---

- **类型**：原理链不完整

- **位置**：稳定性指标 — ANR Rate 节

- **问题**：ANR 触发条件仅提到"输入事件 5 秒超时"和"Service 规定时间"。缺少完整触发类型及对应超时值：Service（前台 20s/后台 200s）、BroadcastReceiver（前台 10s/后台 60s）、ContentProvider（10s）

- **建议**：列出完整 ANR 触发类型表格，或明确交叉引用 ch09.1 作为详细参考

- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md
  - ---

- **类型**：数据支撑缺失

- **位置**：指标体系设计原则 — 分位数 vs 均值节 + 各指标节

- **问题**：缺少 Perfetto SQL 查询示例。同书 ch05.4 提供了频率分析 SQL，但本节作为指标体系章节反而没有。缺少从 Perfetto 计算 Frame Time P50/P90/P99、ANR 统计等常用 SQL

- **建议**：在"在 Perfetto 中观察"类段落或附录中补充核心指标的 Trace Processor SQL 查询示例

- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md
  - ---

- **类型**：数据支撑缺失

- **位置**：全文各指标节

- **问题**：缺少统一的"指标-推荐目标值"速查表。Google Play 不良行为阈值已给出，但业界推荐基准（如 P99 Frame Time < 2x frame budget、TTID < 2s、TTFD < 5s 等）分散在各段中，不易查阅

- **建议**：在"指标体系设计原则"节或独立小节中增加一个速查表，按指标类别列出推荐目标值和 Google Play 不良行为阈值

- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md
  - ---

- **类型**：知识盲区

- **位置**：全文

- **问题**：缺少网络性能指标（TTFB、下载吞吐量、连接延迟等）。对网络密集型 App（信息流、视频、社交），网络指标是性能体系的重要组成

- **建议**：补充一节"网络性能指标"，覆盖 TTFB、throughput、connection latency，或标注为扩展内容并交叉引用 ch12

- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md
  - ---
  - [Task2B 回炉失败] 15.3 性能指标体系 — 原因：需要高爷确认
  - **Issue**: 活人感不足 — 章节整体为教科书/参考手册风格，缺少 Gracker 个人经验痕迹和实战叙述。
  - **已修复的其他 3 个 issue**：
  - 1. ✅ system-triggered profiling 版本自相矛盾（Android 14+ → 16）
  - 2. ✅ reportFullyDrawn() 代码 if-else 两分支相同 → 简化为单行调用
  - 3. ✅ Active/Idle Power 缺 Perfetto Power track 使用说明 → 已补充
  - **需要 Gracker 做的事情**：
  - 在以下关键位置补充实战经验（1-2 句即可）：

- FPS/Frame Time 节：一个用 P99 发现均值掩盖问题的真实案例

- TTID/TTFD 节：一次实际启动优化的经历

- 指标体系设计原则节：线上监控建设中的踩坑经验
  - 标记时间：2026-04-17 12:44

- **类型**：需确认

- **位置**：§消除测试干扰 > 固定CPU频率（进阶）

- **问题**：代码示例 `echo 0 > /sys/devices/system/cpu/cpu0/online` 是将CPU0下线（offline），而非锁定频率。下线CPU与"固定频率"的目的矛盾。

- **建议**：删除offline命令，保留governor设置命令；或改为 `echo 1 > online` 确保在线后再设governor。

- **review 日志**：logs/review/2026-04-17-13-review.md

- **类型**：需确认

- **位置**：§消除测试干扰 > 固定CPU频率（进阶）

- **问题**：`adb shell cmd thermal thontrol disable` 中"thontrol"疑似拼写错误，正确可能是"control"或其他子命令。

- **建议**：验证 `cmd thermal` 的子命令列表，确认正确拼写。

- **review 日志**：logs/review/2026-04-17-13-review.md

- **类型**：需确认

- **位置**：§测试环境标准化 > 网络环境

- **问题**：`adb shell ndc network create` 作为网络模拟方案，需要验证ndc（Native Daemon Connector）是否支持该子命令。

- **建议**：验证ndc命令族的实际可用参数，或替换为更通用的网络模拟方案。

- **review 日志**：logs/review/2026-04-17-13-review.md

- **类型**：原理断裂

- **位置**：「为什么 Binder 只需要"一次拷贝"」小节及 TransactionTooLargeException 相关段落

- **问题**：章节提到 ~1MB mmap 缓冲区限制和 TransactionTooLargeException，但未解释缓冲区的分配/回收机制。每次 Binder 事务从 mmap pool 动态分配 buffer，事务完成后释放；并发事务共享同一 pool。这导致 TransactionTooLargeException 的最常见原因并非单次数据过大，而是并发事务累积超限

- **建议**：在"一次拷贝"小节或新增"缓冲区管理"小节中补充：(1) binder_alloc 机制 — 从 mmap pool 分配 binder_buffer；(2) 并发事务共享 pool 的竞争关系；(3) 诊断 TransactionTooLargeException 时需关注并发事务数而非仅看单次数据量

- **类型**：源码准确性

- **位置**：「oneway 调用」小节，"调用方仍然可能阻塞"段落

- **问题**："Android 14+ 引入 Lazy Async" 的术语未在 AOSP 官方文档中确认

- **建议**：标注 [待验证]，或改为描述性说法（如"Android 14+ 对 oneway 投递策略的优化"）

- **类型**：源码准确性

- **位置**：「线程池是怎么工作的」小节

- **问题**：文中引用 `"%.*s:%d_%X"` 格式，AOSP 实际为 `String8::format("%s:%d_%X", driver, getpid(), seq)`

- **建议**：核对 ProcessState.cpp 原始代码，统一格式描述

- **类型**：原理断裂

- **位置**：「为什么 Binder 只需要"一次拷贝"」小节末尾

- **问题**："将原来需要三次拷贝的流程减少到一次"中的"三次拷贝"包含用户态序列化/反序列化，而前文刚说 Binder 是"一次拷贝"（指内核态），两种说法放在同一段会困惑读者

- **建议**：明确区分"内核态 IPC 拷贝"（Binder mmap 一直是单次）和"用户态数据整理"（scatter-gather 优化的是这一层），避免读者认为 Binder 从 3-copy 变成了 1-copy

- **类型**：数据缺失

- **位置**：「为什么要了解 Binder」段落

- **问题**："主线程可能发起 30-50 次同步 Binder 调用"为估计值，无来源

- **建议**：标注 [待验证] 或引用 Perfetto 实测数据

- **类型**：知识盲区

- **位置**：全文

- **问题**：linkToDeath/unlinkToDeath 机制未提及。高频进程崩溃场景下 death notification 风暴是生产环境偶发卡顿的来源

- **建议**：在"常见问题与误区"或"版本演进"节补充 brief 讨论

- **类型**：交叉引用错误

- **位置**：related_chapters 列表

- **问题**：正文中引用「本书第 2.6 节」讨论 SurfaceFlinger，但 related_chapters 中未包含「2.6」

- **建议**：在 related_chapters 中添加「2.6」

- **类型**：知识盲区

- **位置**：全文

- **问题**：完全未提及 AndroidX/Compose 代码不在 AOSP 中（在 GitHub google/design compose 仓库）。现代 Android 性能分析中 RecyclerView、Compose Runtime 等都在 AndroidX，而非 AOSP。方法论章节教人读源码却不告知这一分叉，可能导致读者在 AOSP 中找不到关键类。

- **建议**：在「AOSP 关键目录结构」节后或速查表中补充一段，说明 AndroidX 代码的定位方式（GitHub + cs.android.com 限定 androidx 目录）

- **类型**：知识盲区

- **位置**：全文

- **问题**：AOSP 分支命名规则未解释。读者不知道 android-16.0.0_r1 vs master vs android-16-release 的区别，这对版本精确分析至关重要。

- **建议**：在 cs.android.com 使用建议中补充一段分支命名规则说明（release tag vs development branch vs master）

- **类型**：数据缺失

- **位置**：全文

- **问题**：缺少一个端到端的实战示例，展示「在 Perfetto 中看到 X → 在 cs.android.com 搜索 Y → 找到源码 Z → 理解了问题」的完整链路。现有内容只有方法和工具介绍，没有串联的案例。

- **建议**：新增一个小节或扩展某个路径，给出一个 200-300 字的端到端示例（如从 Choreographer#doFrame 的长耗时追溯到 scheduleVsync 的具体源码）

- **类型**：数据缺失

- **位置**：「Thermal Mitigation 策略」节 — Severity → 频率上限对照表

- **问题**：表格使用了具体的频率值（如大核 3.0GHz → 2.6GHz → 2.0GHz → 1.4GHz），但未标注这些数值适用于哪款 SoC。不同 SoC 的频率范围差异极大（如 Snapdragon 8 Gen 3 大核最高 3.3GHz，Dimensity 9300 大核最高 2.6GHz），读者可能误将这些示例值当作通用标准。

- **建议**：在表格标题或注释中明确标注「以下为某高端 SoC 的典型示例，具体数值因 SoC 和 OEM 配置而异」，或改为相对比例描述（如「NONE 时为最高频率的 100%，SEVERE 时降至约 45%」）

- **类型**：数据缺失

- **位置**：全文 — 缺少实际 Perfetto Trace 数据

- **问题**：章节多次描述 Perfetto 中的温控表现（频率下降、帧渲染时间上升等），但全部为文字描述，没有实际 Trace 截图或 SQL 查询结果。与其他章节（如 5.4 DVFS）相比，缺少具体的量化数据支撑。

- **建议**：至少补充一处 Perfetto SQL 查询示例，展示如何量化 thermal throttling 对帧率的影响（如统计 THERMAL_STATUS_SEVERE 期间的帧渲染时间 vs NONE 期间）

- **类型**：版本差异

- **位置**：frontmatter confidence 字段

- **问题**：confidence 声明为 'high'，但 applicable_versions 覆盖到 Android 17 而 last_verified_against 仅为 android-14.0.0_r1。版本表中 Android 15-16 的条目标注为 [待验证]。

- **建议**：将 confidence 从 'high' 改为 'medium'，或在 frontmatter 中明确区分已验证版本范围（Android 7-14）和待验证范围（Android 15-17）

- **类型**：原理断裂

- **位置**：「核心架构」→ GLThread 生命周期

- **问题**：缺少 Surface 生命周期管理（onPause/onResume 时 EGL Surface 的销毁和重建）和 EGL Context Lost 处理。GLSurfaceView 的 onSurfaceCreated 回调就是为了处理 GPU context 丢失，这在实战中是最常见的 GLES 性能陷阱之一。

- **建议**：在 GLThread 生命周期节补充 Surface 重建和 Context Lost 的说明，标注在 Perfetto 中如何识别（GLThread 重建 EGL 时会有一段明显的初始化耗时）。

- **类型**：数据缺失

- **位置**：全文

- **问题**：无任何量化数据。缺少：典型 eglSwapBuffers 耗时分布、dequeueBuffer 等待时间参考值、Continuous vs Dirty 模式帧率差异、EGL Context switch 开销数据。

- **建议**：补充一组参考数据（如某设备上 eglSwapBuffers 典型耗时 1-8ms，其中 dequeueBuffer 占比 70-90%），标注设备和版本条件。

- **类型**：数据缺失

- **位置**：「Trace 视角」节

- **问题**：Trace 视角节只有文字描述，缺少具体的 Perfetto SQL 查询示例（对比 13.10 章有大量 SQL）。

- **建议**：补充至少一个 GLES 链路识别查询（如筛选 GLThread 的 eglSwapBuffers slice 并统计帧耗时分布）。

- **类型**：知识盲区

- **位置**：related_chapters

- **问题**：缺少 18.7（TextureView 合成链路）的交叉引用。GLSurfaceView 基于 SurfaceView 走独立 Surface，但 TextureView 也能承载 GLES 渲染。两者的性能差异是架构选型的关键判断。

- **建议**：在 related_chapters 中添加 '18.7'，在 GLSurfaceView vs 原生 EGL 节中提及 TextureView 的替代方案和性能权衡。

- **类型**：版本差异

- **位置**：「ANGLE 路径」节

- **问题**：ANGLE 描述说"Android 14+ / 15+ 上部分设备会更多采用 ANGLE"，未给出具体的版本里程碑。ANGLE 从 Android 12 开始可选，每个版本扩大覆盖设备范围。

- **建议**：补充 ANGLE 推进时间线（Android 12 可选 → 13 扩大 → 14/15 进一步推进），或引用 Google 的 ANGLE roadmap。

- **类型**：需清理 + 需补充素材 + 需确认

- **位置**：参考资料 section 末尾 / Samsung Max Boost 描述 / Rhea 开源状态描述

- **问题**：
  - 1. 参考资料末尾 5 条条目与本章节主题无关（豆包手机/Flutter适配鸿蒙/Android15适配/2026年Android趋势/AI写Android排名），疑似 intake 误关联
  - 2. Samsung Max Boost 模式缺少可验证的官方来源链接
  - 3. Rhea 工具的"开源社区发布了核心框架"描述不够准确，需确认实际开源范围

- **建议**：删除无关参考条目；补充 Samsung Max Boost 官方文档链接；核实 Rhea 开源状态后更新措辞

- **review 日志**：logs/review/2026-04-17-21-review.md

- **类型**：源码准确性

- **位置**：Perfetto GPU counter 配置示例

- **问题**：textproto 示例使用 `counter_ids: [1, 2, 3, ...]` 数组语法，这不是标准 protobuf text format。标准格式应为重复字段：`counter_ids: 1` / `counter_ids: 2`。

- **建议**：修正为标准 protobuf text format，或注明这是简化示意、实际配置建议通过 Perfetto UI 勾选生成。

- **类型**：数据缺失

- **位置**：全文（三个实战案例）

- **问题**：三个实战案例全部标注 [待验证]，缺少真实 Perfetto 数据/截图支撑。案例中的具体数值（如"Overdraw 从 4x 降到 1.5x"、"GPU 功耗降低约 40%"）无实测来源。

- **建议**：至少补充一个有 Perfetto SQL 查询或 GPU counter 截图的真实案例，其余可保留 [待补充：Trace 截图] 标记。

- **类型**：数据缺失

- **位置**：Perfetto GPU 分析能力节

- **问题**：缺少 Perfetto SQL 查询示例用于 GPU 性能分析。与 §13.10 的深度 SQL 教程风格不匹配。

- **建议**：补充至少 1-2 个 GPU 相关的 Perfetto SQL 查询（如查询 GPU frequency 变化、GPU utilization 均值、GPU activity slice 时长分布）。

- **类型**：交叉引用

- **位置**：related_chapters 和"与其他章节的关系"节

- **问题**：§2.10 GPU 渲染深入在 progress.json 中不存在（文件存在但未跟踪），引用可达性不确定。此外缺少与 §18.8 OpenGL ES 渲染链路、§18.6 SurfaceView 直出链路的交叉引用——这两个章节涉及 GPU profiling 的实际应用场景。

- **建议**：确认 §2.10 的跟踪状态；在 related_chapters 中补充 18.8、18.6 的引用。

- **类型**：源码准确性

- **位置**：Sokatoa 开源计划

- **问题**：声称"Samsung 计划在 2026 年内开源 Sokatoa"，当前已是 2026 年 4 月中旬，应确认最新开源状态。

- **建议**：检查 Samsung 开发者网站最新信息，更新开源状态描述（已开源/已发布时间表/延期）。

- **类型**：数据缺失

- **位置**：App Startup 优化策略段

- **问题**：「冷启动时间可减少 35% 到 42%」「每合并一个 ContentProvider 约节省 2ms」均无数据来源。虽已标注 [待验证]，但百分比过于精确却无出处，可能误导读者当作官方数据引用。

- **建议**：补充具体测试来源（如 Google I/O 演讲、Android 官方博客、或内部 A/B 测试数据），或改为范围表述（如「实测可减少 20-40%」）并注明条件。

- **类型**：版本差异

- **位置**：版本演进 → Android 9 CursorWindow 段

- **问题**：「可以通过 CursorWindow(int) 构造函数指定窗口大小，不再强制 2MB」——CursorWindow(String, int) 构造函数在 API 1 即已存在，非 Android 9 新增。需确认 Android 9 实际新增的是什么（可能是 fillWindowForwardOnly 或其他行为变更）。

- **建议**：核实 Android 9 CursorWindow API 实际变更内容，修正描述。

- **类型**：交叉引用

- **位置**：frontmatter

- **问题**：frontmatter 缺少 related_chapters 字段，但正文引用了 §1.3、§1.4、§8.3、§9.1-9.4。

- **建议**：添加 related_chapters: ['1.3', '1.4', '8.3', '9.1', '9.2', '9.3', '9.4']。

- **类型**：需修正 + 需补充素材

- **位置**：文末交叉引用 + §实战场景 + 全文验证标注 + frontmatter related_chapters

- **问题**：
  - 1. 交叉引用路径指向不存在的 `part1-foundation/ch02-graphics-foundation/`，正确路径为 `part1-fundamentals/ch02-rendering/`；且章节编号错误（2.1 是渲染概述非 BufferQueue，2.5 是主线程渲染线程非 SurfaceFlinger）
  - 2. 实战场景（WebView OOP / PiP / 自绘引擎）各仅 2-4 句话约 300 字，writing-guide 要求 1500-3000 字
  - 3. 全文仅 2 处 [已验证]，大量 API 版本引入、fence 语义、HWC 限制等技术断言缺少验证标注
  - 4. frontmatter related_chapters 编号与实际章节不匹配

- **建议**：
  - 1. 修正交叉引用路径和编号，同步修正 frontmatter
  - 2. 至少展开 WebView OOP 为完整实战案例
  - 3. 逐段补充验证标注

- **review 日志**：logs/review/2026-04-17-23-review.md

- **类型**：数据缺失

- **位置**：L171 GPU < 0.1ms / CPU > 10ms 的对比

- **问题**：数值没有设备型号、分辨率、图元复杂度、实现方式等上下文，容易被读者当成通用基线。

- **建议**：改成“示意量级”并补设备/场景前提，或替换为真实 benchmark / Perfetto 案例。

- **类型**：源码准确性

- **位置**：L43 / L187 “Toast、部分 Notification 使用软件渲染”

- **问题**：示例缺少 AOSP 路径或版本限定，且不同窗口类型、RemoteViews 实现和 OEM 定制差异很大，当前说法过于绝对。

- **建议**：给出具体 AOSP 证据和版本范围；如果没有可验证材料，删除这两个例子，改成更稳妥的“个别系统窗口或兼容性场景可能退回软件路径”。

- **类型**：交叉引用

- **位置**：frontmatter related_chapters

- **问题**：正文末尾显式交叉引用了 2.13 和 2.14，但 related_chapters 仅保留 2.1 / 2.5 / 18.2，元数据和正文不一致。

- **建议**：把 2.13、2.14 加入 related_chapters，避免后续目录/索引工具漏链。

- **类型**：源码准确性

- **位置**：L89 / L332 验证标注

- **问题**：两处 [已验证] 都把 OkHttp EventListener 指向 developer.android.com/reference/okhttp3/EventListener。OkHttp 不属于 Android SDK，该路径并不是官方 API 文档地址。

- **建议**：改为 Square OkHttp EventListener 官方文档（events/ 或 API reference），避免把不存在的 Android 文档当成验证来源。

- **类型**：数据缺失

- **位置**：L121 HTTP/3 性能收益数据

- **问题**：Google/Uber/Meta 的 15%、10-30%、20% 指标只给了公司名和博客域名，没有文章标题、年份、实验对象、网络条件或指标定义，读者无法追溯这些数字到底对应 buffering、tail latency 还是 error rate。

- **建议**：补充精确出处和测试上下文，或统一降级为 [待验证]，避免把营销级数字当成可复用基线。

- **类型**：数据缺失

- **位置**：L342 / L368 NetworkCapabilities 带宽描述

- **问题**：把 getLinkDownstreamBandwidthKbps() 近似写成“LinkSpeed/下行带宽”，但它是系统给出的能力估计值，不是实际下载吞吐。若直接拿它驱动画质切换，读者容易把“估计容量”误用成“实时测速结果”。

- **建议**：补一句“这是网络 agent 的估算值，不等于真实吞吐”，并说明需要结合 EventListener 或样本下载结果做校准。

- **类型**：源码准确性

- **位置**：heapprofd 配置示例

- **问题**：`name: "linux.heapprof"`、`heapprof_config`、`target_cmdline` 三处字段都与 Perfetto 官方 proto 不一致。

- **建议**：改为 `android.heapprofd`、`heapprofd_config`、`process_cmdline`，并把官方链接修正为 `https://perfetto.dev/docs/data-sources/native-heap-profiler`

- **类型**：实操错误

- **位置**：MAT 抓取 hprof / malloc_debug 命令示例

- **问题**：`kill -SIGHUP` 不能触发 GC；`backtrace_enable_on_signal` 使用的是 `SIGRTMAX - 19`，不是 `SIGUSR1`。

- **建议**：Java heap dump 示例改为 `adb shell am dumpheap -g <pid> ...`；malloc_debug 按 bionic README 使用实时信号。

- **类型**：版本差异

- **位置**：profileable / HWASAN / MTE 说明

- **问题**：`android:profileable="true"` 语法错误，且 HWASAN、MTE 的版本/设备边界写得过满。

- **建议**：改为 `<profileable android:shell="true"/>`，分别标注 HWASAN 的 Android 14+ wrap.sh 边界、MTE 的设备支持列表与 heap/stack 检测差异。

- **类型**：需补充素材 + 需重写

- **位置**：多处

- **问题**：
  - 1. 「常见性能问题」仅 4 条 1-2 句列表，缺少根因分析、Perfetto 表现、修复方案
  - 2. 「在 Perfetto 中识别 Camera 管线」仅 3 行 track 表，无具体分析方法
  - 3. 「关键组件」3 条项目符号无叙述展开，CameraService/HAL3/CaptureRequest 角色不清
  - 4. 缺少版本演进（Camera1→Camera2→CameraX、HAL 版本变化），applicable_versions 跨 5-16 但无差异说明
  - 5. 参考资料仅目录级路径，缺关键函数名和分支标注

- **建议**：参考 writing-guide.md 类型A（机制原理篇）模板，将列表式内容转为叙述体，补充 Trace 分析方法和版本演进

- **review 日志**：logs/review/2026-04-18-03-review.md

- **类型**：数据缺失

- **位置**：§18.10.5 Layer 数量与性能 + §18.10.8 实战场景

- **问题**：关于“HWC overlay 名额通常只有少数几个”“WebView 独立 SurfaceControl 后宿主 RenderThread 会明显减负”等判断都停留在经验描述，没有给出至少一组 Perfetto / dumpsys SurfaceFlinger 的真实观察样本。读者知道方向，但拿不到可验证的基线。

- **建议**：补一组最小证据链，至少包含 child layer 树、setTransactionState/latchBuffer 观察点，以及宿主 RenderThread 前后对比或 HWC/GPU 合成变化。

- **类型**：数据缺失

- **位置**：L39 开头段的“2-3x 内存带宽”“10-20% 功耗差异”

- **问题**：关键量化结论没有设备、分辨率、codec、刷新率或测试方法上下文，读者容易把它当成跨平台通用基线。

- **建议**：补至少一组具备条件说明的样本（设备 / Android 版本 / 1080p or 4K / 60Hz or 120Hz / 播放器实现），或者把这两句降级成定性表述。

- **类型**：源码准确性

- **位置**：L162-L180「在 Perfetto 和 dumpsys 中识别 Overlay」

- **问题**：当前诊断方法过于粗糙。`grep SurfaceView` 和“GPU Track 没额外任务”不能稳定证明 Overlay 成功，因为 App UI 本身仍可能在用 GPU。章节缺少真正的证据链：layer 的 composition type、client target 是否存在、presentDisplay / setClientTarget 的关系、sideband / DEVICE layer 的可观察字段。

- **建议**：补充更可执行的检查项，至少区分“App GPU 绘制”和“SurfaceFlinger client composition”，给出 dumpsys 字段名或一段更精确的 Perfetto 观察方法。

- **类型**：交叉引用

- **位置**：frontmatter related_chapters

- **问题**：正文多次依赖 BufferQueue、fence 和 Overlay/CLIENT 的判定，但 related_chapters 只列了 2.6 / 2.10 / 18.6，缺少最直接的 2.13（BufferQueue）和 2.16（Sync Fence）。

- **建议**：在 related_chapters 中补充 `2.13`、`2.16`，必要时增加 `18.10`（SurfaceControl / layer 管理）。

- **类型**：需验证 + 需补充素材

- **位置**：Swappy 代码块 + 参考资料 + Perfetto 描述

- **问题**：
  - 1. SwappyVk_setSwapIntervalNS 参数签名需验证（Android Game SDK 版本差异）
  - 2. 参考资料缺少 URL，AOSP 路径过于笼统
  - 3. Perfetto 中 Swappy Track/Slice 描述笼统，缺少具体名称

- **建议**：
  - 1. Task 9 验证 Swappy Vulkan API 最新签名
  - 2. 补充官方文档 URL
  - 3. 补充具体 Swappy Track/Slice 名称或 Trace 截图

- **review 日志**：logs/review/2026-04-18-05-review.md

- **类型**：数据缺失

- **位置**：L183 Overlay 数量判断

- **问题**：`HWC 支持的最大 Overlay 数量通常 4-8 个` 没有 SoC、Display Engine、HWC HAL 代际或 dumpsys / vendor 文档上下文，容易被读者误读成跨平台通用上限。

- **建议**：补一张 capability matrix，或者至少把表述降级为“Overlay 名额依平台而异”，再给一组设备级样本。

- **类型**：原理完整性

- **位置**：L78 Pipeline B 节奏描述

- **问题**：`帧率取决于视频源和解码速度，而不是系统的 VSync 频率` 说得过满。Producer cadence 的确独立于 Choreographer，但最终 present 仍受 SurfaceFlinger / HWC 的 VSync 节奏约束。

- **建议**：改成“生产节奏独立，显示节奏仍由 VSync-SF 驱动”，避免把 producer cadence 和 display cadence 混为一谈。

- **类型**：需重写 + 需补充内容

- **位置**：全文风格 + 多个章节

- **问题**：
  - 1. 文体问题：整体读起来像API参考文档（列表堆砌+代码片段），不符合writing-guide.md要求的engineer-to-engineer叙述风格。适用场景、核心架构、性能对比等章节都是列表/表格，缺少因果解释和连贯叙述。
  - 2. Perfetto识别章节（## 在 Perfetto 中识别）内容极薄，仅两行表格，缺少实际Track名称和Trace截图描述。
  - 3. 性能对比表的数据（15ms/8ms等）缺少测试条件（设备、Android版本、渲染场景）。
  - 4. 缺少writing-guide类型A模板要求的"常见问题与误区"章节。
  - 5. 缺少与RenderThread的关系说明（标准View渲染路径自动管理RenderThread，HBR需要手动管理）。

- **建议**：
  - 1. 将列表式章节改写为连贯叙述，参考writing-guide.md中"正确写法"示例。
  - 2. 为Perfetto章节补充实际Track定位方法。
  - 3. 性能数据补充测试条件，或改为定性描述。
  - 4. 新增"常见问题与误区"小节。
  - 5. 补充与RenderThread的对比说明。

- **review 日志**：logs/review/2026-04-18-06-review.md

- **类型**：数据缺失

- **位置**：性能对比表（L123-L129）

- **问题**：`1080p 全屏绘制 ~15ms vs ~8ms`、`内存带宽 2x vs 1x`、`120fps 离屏渲染` 都没有设备型号、Android 版本、渲染后端、绘制内容复杂度或 Trace/benchmark 依据。当前数字更像口径占位，不足以支撑章节核心判断。

- **建议**：补充至少一组真实设备 + API level + workload + Trace/benchmark 条件；如果暂时没有数据，就改成定性结论并保留 `[待验证]`。

- **类型**：数据缺失

- **位置**：在 Perfetto 中识别（L176-L183）

- **问题**：当前只写了“GPU Track”“SurfaceFlinger 额外 Layer”，没有给出 direct `setBuffer()` 路径在 App/SF 两侧的具体观察点，读者很容易把 §18.2 的 BLAST 轨迹生搬过来。

- **建议**：补一段真实 Trace 描述，至少说明 render callback 完成、`setTransactionState`/`latchBuffer`/present fence 这些证据分别出现在什么进程和什么 slice 上；如果还没抓到，就明确标 `[待补充：direct setBuffer Trace]`。

- **类型**：源码准确性

- **位置**：Java API 代码块（L92-L99）

- **问题**：示例拿到 `RenderResult` 后直接 `setBuffer()`，没有检查 `result.getStatus()`，也没有交代 `HardwareBufferRenderer.close()` 与 `HardwareBuffer.close()` 的生命周期边界。对读者来说，这会把错误处理和资源回收都隐掉。

- **建议**：在代码示例中先判断 `result.getStatus() == SUCCESS`，并补一句说明 renderer 关闭不会替调用方关闭 `HardwareBuffer`。

- **类型**：需补充素材

- **位置**：PIP 渲染流程（持续渲染 + 性能考量）

- **问题**：PIP 模式渲染流程仅一句话带过，性能考量为纯列表缺少深度，缺少 BufferQueue 行为、帧率变化、内存占用的具体分析

- **建议**：参照 writing-guide.md 类型A结构，将 PIP 渲染流程改写为连贯叙述，补充 BufferQueue 在 PIP 模式下的行为变化（如 min/max buffer count 变化、帧率限制策略）和 Perfetto Trace 对应表现

- **review 日志**：logs/review/2026-04-18-07-review.md

- **类型**：需补充素材

- **位置**：全文 Perfetto Trace 描述

- **问题**：除末尾一张表外，缺少 Perfetto Trace 截图描述或文字标注

- **建议**：在 Trace 定位节补充具体 slice 名称（如 SurfaceFlinger 的 Transaction apply、wm_task_moved）、track 名称和 `[待补充：Trace 截图]` 占位标记

- **review 日志**：logs/review/2026-04-18-07-review.md

- **类型**：需补充素材

- **位置**：BLAST Sync 解决方案

- **问题**：缺少 AOSP 源码路径（BLASTBufferQueue.java 等）

- **建议**：补充 frameworks/base/libs/gui/BLASTBufferQueue.cpp 及相关 Java 层路径

- **review 日志**：logs/review/2026-04-18-07-review.md

- **类型**：需补充素材

- **位置**：版本演进（整体缺失）

- **问题**：PIP 从 Android 8.0 引入、BLAST 从 Android 12 引入的关键变化未梳理

- **建议**：添加版本演进表格，标注各版本中 PIP/Freeform/BLAST 的关键变更

- **review 日志**：logs/review/2026-04-18-07-review.md

- **类型**：交叉引用

- **位置**：frontmatter `related_chapters` / 正文“与其他章节的关系”

- **问题**：正文显式引用了 `2.17 Frame Pacing Library`，但 `related_chapters` 没有包含 `2.17`，导航链会漏掉帧节奏主线。

- **建议**：在 `related_chapters` 中补上 `2.17`；如果要强化诊断路径，可再考虑补 `13.1 Perfetto 简介与演进`。

- **类型**：知识盲区

- **位置**：Unity / Unreal 线程模型表（L80-L94）

- **问题**：表格把 `UnityGfx` / `RHIThread` 写成固定拓扑，未标注 multithreaded rendering、graphics jobs、RHIThread 受引擎版本、后端和项目配置控制。读者可能因为某条线程在 trace 中缺席而误判“不是 Unity/Unreal”。

- **建议**：把表述改成“典型线程模型”，补一句线程是否存在取决于渲染后端和引擎配置。

- **类型**：需补充素材 + 需验证 + 需重写

- **位置**：全文多处

- **问题**：
  - 1. Perfetto 分析节仅3行表格，缺少具体分析流程（B1）
  - 2. Android 16 Enhanced ARR API 常量名/投票机制待验证（B2）
  - 3. 缺少 Android 11-16 版本演进段落（B3）
  - 4. 全文叙述风格偏参考文档，表格/代码为主骨架，缺少连贯技术叙述（B4）

- **建议**：

- B1: 参考 writing-guide 类型A"在 Perfetto 中的表现"要求，补充 VRR 场景 Perfetto 分析流程、SQL 查询示例、Trace 片段描述

- B2: 标注 [待验证]，Android 16 API 37 定稿后确认

- B3: 补充 Android 11(setFrameRate) → 13(ARR) → 15(LTPO优化) → 16(Enhanced ARR) 版本演进

- B4: 按叙述为主、列表为辅重写常见问题和 Perfetto 分析节

- **review 日志**：logs/review/2026-04-18-09-review.md

- **类型**：数据缺失

- **位置**：在 Perfetto 中识别 Camera 管线（L144-L159）

- **问题**：列出了 `queueBuffer`、`BufferTX - SurfaceView`、`binder transaction`、`dma_buf` 等观察点，但没有给一条可运行的 trace 配置、一个正常/异常样例或最小 SQL/时间基线。当前结论更多是经验列表，读者难以拿自己的 trace 逐项对照。

- **建议**：补一组最小抓取配置，加一条“稳定预览 vs Analysis 背压”的真实 case，至少给出一组帧间隔/回调归还节奏的判断基线；术语和查询口径尽量与 §14.9 对齐。

- **类型**：数据缺失

- **位置**：L121-L138 Trace 定位 / 在 Perfetto 中识别多窗口问题

- **问题**：Trace 指引只给出 `wm_task_moved`、`Transaction.apply`、`queueBuffer` 这类零散关键词，没有说明需要打开哪些数据源，也没有给出 App 主线程 Traversal、BufferQueue 背压、SurfaceFlinger FrameTimeline、WindowManager transition 等联合观察方法。读者很难凭这些描述真正复现 resize / PIP 卡顿分析。

- **建议**：补一组最小可执行分析路径，例如：WindowManager / SurfaceFlinger / FrameTimeline / app main thread / BufferQueue 各看什么 track；至少给 1 个正常案例和 1 个异常案例的文字版 Trace 描述。

- **类型**：数据缺失

- **位置**：L77-L79 / L128-L130

- **问题**：`系统通常限制 PIP 窗口的 CPU/GPU 优先级`、`Chrome 会预渲染几个常见尺寸的 Bitmap Cache` 两个判断没有版本、设备或源码依据，且都属于平台/应用特定策略，当前写法容易被读者误解为通用结论。

- **建议**：如果没有可验证材料，改成 `[待验证]` 或删去；更稳妥的写法应回到通用约束，如 HWC plane 竞争、resize 触发的重新 layout、BufferQueue 槽位背压。

- **类型**：数据缺失

- **位置**：`在 Perfetto 中识别 ANGLE` 小节

- **问题**：当前只给了一个 `LIKE '%vk%'` 的 SQL 和几条泛化判断，没有说明需要打开哪些 trace 数据源、如何限定目标进程、也没有给出 native Vulkan / ANGLE 的对照样例。读者即使拿到 trace，也很难复现“先确认 driver selection，再做归因”的流程。

- **建议**：补一个最小可执行案例：按包切 ANGLE，记录 gfx + GPU renderstages + Vulkan 相关数据源，给出限定目标进程的 SQL，并把 `GL_RENDERER` 与 trace 结果放在一起对照。
  - 经过 web search 验证，Android 17 EyeDropper API 确实存在，但章节中的实现描述**完全错误**。
  - **真实 API：**

- 基于 Intent：`Intent("android.intent.action.OPEN_EYE_DROPPER")`

- 通过 `registerForActivityResult` 接收结果

- 返回颜色通过 `intent.getIntExtra("android.intent.extra.COLOR", defaultColor)`

- 无需特殊权限（替代 MediaProjection 方案）
  - **章节中编造的内容：**

- `EyeDropper` 类及其 `pickColor()` 方法 → 编造

- `EyeDropper.OnColorPickedListener` 回调接口 → 编造

- `EyeDropperConfig` Builder 类 → 编造

- `CrossDeviceColorPicker` 跨设备拾取类 → 编造

- `IncrementalColorSync` 增量同步类 → 编造

- `ColorCompression` 颜色压缩类 → 编造

- `SamplingResolution.HIGH` 等枚举 → 编造

- SurfaceFlinger.pickColorAt() / Layer.pickColorAt() → 编造

- HWC GPU shader 采样代码 → 编造

- 所有性能数字（10-20x、60%、<5ms 等）→ 编造

- Android 18/19/20 功能规划 → 编造

- AOSP 源码路径 → 编造
  - **处理建议：**
  - 1. 全文重写，基于真实 API（Intent-based workflow）
  - 2. 删除所有编造的类、方法、代码
  - 3. 删除所有编造的性能数据
  - 4. 删除"计划中的版本"整节
  - 5. 补充与 MediaProjection 方案的真实对比
  - 6. 如需 Perfetto 分析，需基于实际 trace 数据

- **类型**：需重写（全文）

- **位置**：全文

- **问题**：章节基于 AI 编造的 API 实现，与真实 Android 17 EyeDropper API 完全不符

- **建议**：基于官方文档和真实 API 重写。正确用法见 https://developer.android.com/reference/android/content/Intent#ACTION_OPEN_EYE_DROPPER

- **review 日志**：logs/review/2026-04-18-13-review.md

- **类型**：数据缺失

- **位置**：L199-L201、L360-L362、L494-L496（3 处 Trace 占位图）

- **问题**：章节把 `oom_score_adj` 变化、冷启动关键节点、ANR Trace 特征都写成了口头描述，但三处核心位置只有“待补截图”占位，没有一段真实 Perfetto 片段或 SQL 输出。作为“与性能分析”章节，读者无法据此建立可复现的观察基线。

- **建议**：至少补 1 个冷启动 trace 和 1 个 ANR trace。每个例子给出 10-20 行 SQL 或关键 track 标注，包含 `android_logs` 的 `am_proc_start/am_anr` 与应用主线程 `bindApplication` / `doFrame` 的对照。

- **类型**：数据缺失 / 原理边界

- **位置**：L123-L125，L140-L141

- **问题**：`dur > 5000000` 与 `doFrame > 16.6ms` 被直接当作诊断阈值，但正文同时覆盖高刷与 VRR 场景。5ms/16.6ms 都缺少设备、刷新率和 Trace 版本边界，容易把 90Hz/120Hz 设备误判成“正常”。

- **建议**：把阈值改成“按当前刷新率/expected timeline 预算计算”，或明确标注“仅适用于 60Hz 固定刷新率示例”。

- **类型**：知识盲区

- **位置**：L176-L193「链路选型决策树」

- **问题**：决策树把 SurfaceView vs TextureView 的分叉压缩成“是否需要动画/变换/圆角”，遗漏了裁剪、滚动同步、Z 序、Inset、窗口 resize 同步等高频约束，容易把本该走 TextureView / SurfaceControl 的场景误导成 SurfaceView。

- **建议**：补一组“即使不要圆角也不该选 SurfaceView”的条件，或直接回连 §18.6 / §18.7 / §18.10 的选择矩阵。

- **类型**：交叉引用

- **位置**：frontmatter `related_chapters` / L216-L218

- **问题**：正文把 §18.1 写成“本章的索引和入口”，但 frontmatter `related_chapters` 未包含 18.1，元数据导航与正文关系不一致。

- **建议**：在 `related_chapters` 中补入 `18.1`，必要时再补入 18.6 / 18.7 / 18.14 / 18.19 这些正文高频回连章节。

- **类型**：技术核实

- **位置**：Stale Event 丢弃机制（AIW-源码调研-2026-04-17）代码段

- **问题**：代码示例中使用了 mInboundQueue.hasEvent()、peekEvent()、removeEvent()、dropInboundConnection() 等方法，这些方法名在 AOSP android-14 的 InputDispatcher 中可能不存在或名称不同。该代码段标记为 AIW-源码调研，可能是基于理解重写的简化版本而非实际源码摘录。

- **建议**：Task 9 对照 AOSP android-14.0.0_r1 frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp，核实 STALE_EVENT_TIMEOUT 常量、isStale() 函数签名、以及 dispatchOnce() 中 stale event 的实际处理流程。如方法名不准确，由 Task 2B 更正为实际源码。

- **review 日志**：logs/review/2026-04-18-15-review.md

- **类型**：数据缺失

- **位置**：L92-L94 / L197-L235

- **问题**：章节把 preload + COW 共享和“如何区分 Zygote 问题 / App 初始化问题”作为核心判断，但正文没有任何真实 Trace、event log 或 PSS/smaps 数据。读者看不到 `am_proc_start → PostFork → am_proc_bound → bindApplication` 的真实耗时，也看不到 COW 共享在内存上的可观测证据。

- **建议**：补 1 个真实冷启动案例，至少给出 `am_proc_start→PostFork`、`PostFork→am_proc_bound`、`bindApplication` 的耗时；再补 1 个 `smaps_rollup` / PSS / Shared_Clean 示例，证明 preload + COW 的收益。

- **类型**：交叉引用

- **位置**：frontmatter `related_chapters` / L283-L288

- **问题**：正文多次解释 Binder 与 zygote socket 的职责边界，但 related_chapters 没有回连 §1.4 Binder IPC 机制与性能影响 和 §1.17 IPC 全景；同时正文把 §8.2 写成“应用启动分析”，项目中的实际标题是“App 启动全流程”。

- **建议**：related_chapters 补 `1.4`、`1.17`；正文把 §8.2 的标题回连到项目中的实际名称，避免交叉引用口径漂移。

- **类型**：版本差异

- **位置**：L257-L259

- **问题**：正文把“Android 8 之后 WebViewZygote 成为重要角色”直接展开成“WebView 相关进程有自己的 child zygote 链路”。异步源码核验结果显示：android-8.0.0_r1 的 `android/webkit/WebViewZygote.java` 已存在 `webview_zygote32/64` 服务名，但未出现 `startChildZygote()`；android-9.0.0_r1 才出现 `startChildZygote()` 路径。当前表述把“专用 WebView zygote”与“child zygote 路由”压成了一个版本点。

- **建议**：把版本叙述拆开写，至少区分“Android 8 引入专用 WebView zygote”与“Android 9 起明确走 child zygote 路径”；如果后续还要继续写 `preloadApp()`，再单独标注更高版本的变化。

- **类型**：数据缺失

- **位置**：L60

- **问题**：`76.39%` 的“另一项研究”没有给出可追溯来源，仓内也没有对应素材。当前写法会让读者误以为该数字已被本项目核验。

- **建议**：补上可直接访问的论文/报告链接和标题；如果找不到稳定来源，删除该数字或改成 `[待验证]`。

- **类型**：数据缺失

- **位置**：L106

- **问题**：`启动时间每增加 100ms，转化率下降约 0.7%` 没有给出处，且回指的 §8.1 章节里找不到这个数字。

- **建议**：补充可核验来源；如果只是行业案例或特定业务数据，明确适用场景，不要写成 Android 通用结论。

- **类型**：数据缺失

- **位置**：L201-L205

- **问题**：`ANR 是用户卸载 App 的 Top 3 原因之一`、`工具已经相对成熟，因此学术研究的边际收益在降低` 都属于扩展判断，当前没有对应数据或案例支撑。

- **建议**：给出 Google Play Vitals、行业案例或研究原文证据；若无硬证据，改成更保守的工程判断。

- **类型**：版本差异

- **位置**：L72

- **问题**：把 ANR 写成统一的 `5 秒` 触发阈值，容易和 Input / Broadcast / Service / ContentProvider / `startForeground()` 的不同超时机制混淆。

- **建议**：把这里限定为 `Input ANR` 场景，或补一句“不同组件的 ANR 超时并不相同，详见 §9.1 / §9.2”。

- **类型**：数据缺失

- **位置**：L253-L264 / L275

- **问题**：Perfetto 部分仍然没有一份真实 trace 的线程名、slice 名或 SQL 结果闭环；`LIKE "%underrun%"` 这段 SQL 还停留在“需要按设备标签调整”的占位状态，读者没法直接复现。

- **建议**：补 1 份真实音频 trace，至少给出线程名（如 FastMixer / RecordThread / Mmap* / Offload*）、对应 slice 或 counter 名，以及可直接运行的 SQL；如果不同设备差异大，给一版 Pixel 基线和一版 OEM 注意事项。

- **类型**：数据缺失

- **位置**：L393

- **问题**：`JNI` 开销“约 100-200 微秒”没有给出处，也没有说明设备、buffer size、调用频率和测量方法。当前写法会被读者当成通用结论。

- **建议**：补 benchmark/trace/官方资料；如果暂时没有稳定数据，把这里降级成定性判断，不要保留具体数值。

- **类型**：源码准确性

- **位置**：L177-L179

- **问题**：正文把 Flutter 根视图 render mode 直接写成“SurfaceView 或 TextureView”两种，但 Flutter Android embedding 的 `RenderMode` 官方枚举还包含 `image`，其语义与 PlatformView 交互直接相关。当前写法会把“默认常见路径”和“完整 render mode 集合”混成一层。

- **建议**：补一句 `RenderMode.image` 的定位和适用边界，至少说明它不是常见默认值，但在 PlatformView 全交互场景里需要被单独区分。

- **类型**：数据缺失

- **位置**：L187-L205

- **问题**：Perfetto 节已经给出 `Engine::BeginFrame`、`Rasterizer::DrawToSurfaces` 等标签，但没有任何真实 trace、线程名、slice 截图或 SQL 结果闭环。读者无法判断这些标签在不同 engine 版本和 trace 配置下是否稳定可见。

- **建议**：补 1 份真实 Flutter trace，至少给出 Main/Raster/IO 的线程名、关键 slice、FrameTimeline 或 SurfaceFlinger 对应轨道，以及一条可复用的 SQL / 检查步骤。

- **类型**：交叉引用

- **位置**：L211 / frontmatter `related_chapters`

- **问题**：正文把 WebView 相关章节写成“13.8 WebView 渲染性能”，仓内实际存在的是 `7.11 WebView 渲染性能与优化`；frontmatter `related_chapters` 也没有回连 `7.11`。

- **建议**：把正文交叉引用修正为 `7.11 WebView 渲染性能与优化`，并在 `related_chapters` 补 `7.11`。

- **类型**：数据缺失

- **位置**：L195-L216 / L404-L494

- **问题**：安装耗时分析和 Perfetto 调试两节还停留在“待补充 Trace 截图”的占位状态，没有一份真实安装 trace 的线程名、slice 名、I/O 轨道或 SQL 闭环。读者知道要看 `system_server` / `installd` / `dex2oat`，但还不知道具体该抓到什么。

- **建议**：补 1 份真实安装 trace，至少标出 `PackageInstallerSession`、`installStage`、`artd` / `dex2oat*`、关键 I/O 轨道，以及一组可直接复用的 Perfetto SQL 或检索关键词。

- **类型**：数据缺失

- **位置**：L341-L343

- **问题**：“2GB 内存设备上大型应用 dex2oat 可能需要几分钟”“SDM 通常比 APK 本身小”这两句没有设备、应用规模、网络条件或来源。当前写法会被读者当成通用量化结论。

- **建议**：补实验条件和出处；如果暂时拿不到稳定数据，把这段降级成定性描述，不要保留具体量级。

- **类型**：交叉引用

- **位置**：L248 / L309

- **问题**：两处跨章节链接写成当前目录下的 `03-launch-optimization.md` 和 `07-baseline-profiles.md`，实际文件位于 `src/part2-performance/ch08-responsiveness/`，当前链接都会落空。

- **建议**：修正为 `../../part2-performance/ch08-responsiveness/03-launch-optimization.md` 和 `../../part2-performance/ch08-responsiveness/07-baseline-profiles.md`

- **类型**：数据缺失

- **位置**：L253-L255，DeliQueue 数据段

- **问题**：文中直接引用“主线程 lock contention time 下降 15%、应用 missed frames 下降 4%、SystemUI / Launcher 下降 7.7%-9.1%”，但没有交代测试边界、样本对象、版本条件或观察口径，读者无法判断这些数字能否外推到普通 App 场景。

- **建议**：补充数据来源的实验边界，例如 Android 17 beta/internal test、对象范围（App 还是 SystemUI/Launcher）、指标口径（missed frames/lock contention time 的采集方式），并给一条可在 Perfetto 中复核的观察点。

- **类型**：P2 建议

- **位置**：Data Source

- **问题**：

- **建议**：

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：模块加载与表查询不匹配

- **问题**：

- **建议**：

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Native 代码中的自定义标记

- **问题**：

- **建议**：

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Sleeping

- **问题**：

- **建议**：

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：冗余文本残留

- **问题**：

- **建议**：

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Wall 时间的构成

- **问题**：

- **建议**：

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Callstack Sample

- **问题**：“在 Android Studio 2025 的最新版本中，Google 引入了新的采样引擎”

- **建议**：建议明确指出是哪个具体版本（如 Android Studio Ladybug 或 Meerkat 等），或者用“较新的 Android Studio 版本中”进行模糊处理以防过时。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：`Callstack Sample` | 问题描述：“Android Studio 2025” 的表述不够精确 | 建议：替换为明确的 AS 动物代号版本（如 Ladybug/Meerkat 等），避免歧义。

- **问题**：“Android Studio 2025” 的表述不够精确 | 建议：替换为明确的 AS 动物代号版本（如 Ladybug/Meerkat 等），避免歧义。

- **建议**：替换为明确的 AS 动物代号版本（如 Ladybug/Meerkat 等），避免歧义。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Macrobenchmark PowerMetric

- **问题**：`PowerMetric(category = PowerMetric.Category.CPU)` 的构造函数签名

- **建议**：核实最新版 Macrobenchmark API 的 PowerMetric 构造函数签名并修正代码示例。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：bugreport 抓取

- **问题**：`adb bugreport > bugreport.txt  # Android 6.0 及更早`

- **建议**：可以考虑在 6.0 命令后补充说明"Android 6.0 及更早输出的是纯文本格式"。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Macrobenchmark PowerMetric | 问题描述：PowerMetric 构造函数签名可能不完全准确 | 建议：核实最新 API 并修正。

- **问题**：PowerMetric 构造函数签名可能不完全准确 | 建议：核实最新 API 并修正。

- **建议**：核实最新 API 并修正。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：heapprofd：Native 堆的实时采样分析

- **问题**：“Java 分配模式从 Android 12 开始支持... 它无法替代 MAT 的引用链分析。”

- **建议**：建议补充一句，说明如果需要分析引用链，Perfetto 提供了独立的 Java Heap Dumps (`art.heapprof` 数据源，Android 11+ 支持)。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：`heapprofd` | 问题描述：未提及 Perfetto 的 Java Heap Graph 功能。 | 建议：补充 Perfetto 从 Android 11 起支持抓取完整的 Java 堆快照并进行引用链分析，是 MAT 的有力现代替代品。

- **问题**：未提及 Perfetto 的 Java Heap Graph 功能。 | 建议：补充 Perfetto 从 Android 11 起支持抓取完整的 Java 堆快照并进行引用链分析，是 MAT 的有力现代替代品。

- **建议**：补充 Perfetto 从 Android 11 起支持抓取完整的 Java 堆快照并进行引用链分析，是 MAT 的有力现代替代品。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：关键指标：PSS、USS、Private Dirty

- **问题**：“Private Dirty 是已经被修改过的私有内存页。这部分内存不能被换出到磁盘（Android 默认不用 swap），必须常驻物理 RAM。”

- **建议**：补充说明 Private Dirty 内存虽然不能置换到磁盘，但会被系统压缩放入 ZRAM（仍占用 RAM，但体积缩小），以更精确地描述现代 Android 内存管理行为。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：dumpsys batterystats：电池使用与功耗分析

- **问题**：`adb bugreport > bugreport.zip`

- **建议**：修改为现代标准的命令语法。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：`关键指标：PSS、USS、Private Dirty` | 问题描述：未提及 ZRAM 对 Private Dirty 内存的影响。 | 建议：补充说明 Private Dirty 可以被压缩放入 ZRAM，而非完全 1:1 占用物理 RAM。

- **问题**：未提及 ZRAM 对 Private Dirty 内存的影响。 | 建议：补充说明 Private Dirty 可以被压缩放入 ZRAM，而非完全 1:1 占用物理 RAM。

- **建议**：补充说明 Private Dirty 可以被压缩放入 ZRAM，而非完全 1:1 占用物理 RAM。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：`功耗分析工作流` | 问题描述：`adb bugreport > bugreport.zip` 语法过时且有损坏风险。 | 建议：更新为 `adb bugreport bugreport.zip`。

- **问题**：`adb bugreport > bugreport.zip` 语法过时且有损坏风险。 | 建议：更新为 `adb bugreport bugreport.zip`。

- **建议**：更新为 `adb bugreport bugreport.zip`。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：CompilationMode：量化编译优化效果

- **问题**：`CompilationMode.Partial(CompilationMode.Partial.Mode.DEFAULT)`

- **建议**：修正代码示例中的 API 调用签名。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：`CompilationMode` 代码示例 | 问题描述：`CompilationMode.Partial(Mode.DEFAULT)` 不是有效 API 签名。 | 建议：更新为 `CompilationMode.Partial(baselineProfileMode = BaselineProfileMode.Require)`。

- **问题**：`CompilationMode.Partial(Mode.DEFAULT)` 不是有效 API 签名。 | 建议：更新为 `CompilationMode.Partial(baselineProfileMode = BaselineProfileMode.Require)`。

- **建议**：更新为 `CompilationMode.Partial(baselineProfileMode = BaselineProfileMode.Require)`。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Perfetto GPU Counter Track 的启用

- **问题**：配置示例中 `counter_ids: [1, 2, 3, ...]` 需要硬编码 counter ID

- **建议**：在代码注释中明确说明这些 ID 是设备相关的，推荐使用 `perfetto --query` 或 Perfetto UI 来获取设备支持的实际 counter ID 列表。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：`gpu.counters` 配置 | 问题描述：counter_ids 硬编码写法可能误导 | 建议：补充说明 ID 为设备相关值，推荐用工具查询。

- **问题**：counter_ids 硬编码写法可能误导 | 建议：补充说明 ID 为设备相关值，推荐用工具查询。

- **建议**：补充说明 ID 为设备相关值，推荐用工具查询。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Perfetto Trace 配置

- **问题**：`name: "android.trace_config"` 和 `atrace_config` 嵌套格式

- **建议**：考虑对齐到 Perfetto 官方文档推荐的标准 trace config 格式，或者在注释中说明这是简化格式。

- **来源**：外部 AI review

- **类型**：P2 建议

- **位置**：Perfetto Trace 抓取配置 | 问题描述：`android.trace_config` 数据源名称非标准推荐格式 | 建议：对齐到 `linux.ftrace` + `ftrace_config.atrace_categories` 标准格式。

- **问题**：`android.trace_config` 数据源名称非标准推荐格式 | 建议：对齐到 `linux.ftrace` + `ftrace_config.atrace_categories` 标准格式。

- **建议**：对齐到 `linux.ftrace` + `ftrace_config.atrace_categories` 标准格式。

- **来源**：外部 AI review

- **类型**：数据缺失

- **位置**：L173-L179 当前链路判断

- **问题**：只有口头 heuristic，没有最小 trace 抓取口径、provider 识别步骤和 `dumpsys SurfaceFlinger` 实操示例。现场读者即使知道四种模式，也很难把文章结论落到真实设备上验证。

- **建议**：补一个最小验证清单：`WebViewCompat.getCurrentWebViewPackage()` / `adb shell dumpsys webviewupdate`、Perfetto 中 functor / Viz / `updateTexImage` 的观察点、`dumpsys SurfaceFlinger` 中 child layer 的识别方法。

- **类型**：数据缺失

- **位置**：L293-L305 / L317-L323 常规堆限制与 largeHeap 策略

- **问题**：按 RAM 分档给出的 normal heap / largeHeap 数值区间，以及“Android 10+ 后台进程即使声明 largeHeap 可用堆空间也会被压缩”的说法，没有附设备 `getprop` / `getMemoryClass()` 样本，也没有给出 AOSP 或官方文档锚点，当前更像经验值汇总而不是可复核结论。

- **建议**：补 3-4 组真实设备样本（RAM、32/64 位、`dalvik.vm.heapgrowthlimit`、`getMemoryClass()` / `getLargeMemoryClass()` 输出），并把 Android 10+ 的后台限制改成有来源的机制描述；如果拿不到样本，就把表格明确降级为经验范围并标 `[待验证]`。

- **类型**：数据缺失

- **位置**：L228-L245 HWC 能力限制

- **问题**：`高端芯片通常支持 4-8 个 Overlay` 没有给出 SoC / 显示管线边界，紧接着给出的 `SELECT name, composition_type FROM layer` 仍是未验证 SQL。当前这组说法不足以支撑“如何复核 GPU 合成回退”的实操结论。

- **建议**：补至少 1 组真实设备或 trace_processor 验证材料，给出可执行的 `dumpsys SurfaceFlinger` / Perfetto SQL 口径；如果暂时拿不到验证样本，就删掉 4-8 的范围并把 SQL 明确降级为 `[待验证]`。

- **类型**：原理断裂

- **位置**：L393-L406 Frame Timeline 起点说明

- **问题**：Expected Timeline 的起点先被写成“Choreographer 收到 VSYNC-app 的时间”，后面又写成“比 VSYNC-app 更晚”。Perfetto 官方文档的口径是“the time the Choreographer callback was scheduled to run”，这里把 callback scheduled time、实际 `doFrame` 开始时间和 expected presentation time 混在了一起。

- **建议**：统一三组时间基准：callback scheduled time、实际 `Choreographer#doFrame` start、expected presentation time，并明确 Expected Timeline 不等于 Actual Timeline 的起点。

- **类型**：交叉引用

- **位置**：L109 / L248（关联 `§14.2 Simpleperf` L404-L408）

- **问题**：本节写的是 simpleperf `report-sample --protobuf` 后再导入 Perfetto，这和 Perfetto 官方 other-formats 文档一致；但被引用的 `§14.2` 目前写成“`perf.data` 可直接通过 Perfetto trace_processor 导入”，两节给出的工作流不一致，读者按交叉引用继续操作时会走到错误路径。

- **建议**：统一成一条已验证流程，优先采用 `simpleperf report-sample --protobuf --show-callchain -i perf.data -o simpleperf.proto` + Perfetto 导入；如果要保留其他导入方式，必须明确区分 raw perf / simpleperf protobuf，并补 perfetto.dev 官方锚点。

- **类型**：数据缺失

- **位置**：L218-L222 系统服务的设计启示

- **问题**：正文给出“native-only 的 Binder 栈可以减少 Java ↔ native 桥接和部分序列化层级”的判断，但没有配套 call stack、trace、simpleperf 样本或 AOSP 路径对照，当前更像经验判断，读者很难据此复核 `libbinder_ndk`、Java Binder、JNI bridge 三者的差异到底落在哪一层。

- **建议**：补 1 组最小证据链，至少包含 Java Binder → JNI bridge → native-only Binder 三种调用栈或序列化路径对照；如果暂时拿不到样本，就把结论收紧到“减少 Java ↔ native 桥接”，不要额外延伸到“部分序列化层级”。

- **类型**：交叉引用

- **位置**：L185-L197 在 Perfetto 中分析 VRR / 与其他章节的关系

- **问题**：Perfetto 观察点写成 `VSYNC` / `HW_VSYNC` / `FrameTimeline` 三行摘要，和 §2.3、§2.18 现有的 `VSYNC-app`、`VSYNC-sf`、`expected_frame_timeline_slice`、`actual_frame_timeline_slice` 口径不一致，读者无法直接按全书统一方法回溯

- **建议**：统一术语口径，并在本节明确 surface_frame_token / display_frame_token / jank_type 的实际观察入口

- **类型**：数据缺失

- **位置**：L145-L150 / L184 / L210 / L247 / L355

- **问题**：`90%+ 的 IPC 调用走 Binder` 以及多组延迟数字（Binder / socket / pipe / mmap）都没有给设备型号、负载条件、payload 大小或 Trace 样本。当前写法看起来像已验证的量化结论，但仓内没有对应 benchmark / Perfetto 证据。

- **建议**：补 1 组可复现的基准条件和观测方法；如果暂时没有实测，把这些数字降级成定性描述或标成 `[待验证]`。

- **类型**：交叉引用

- **位置**：L202-L204 / L513

- **问题**：正文已经明确 Android 8-17 的 Looper 唤醒路径应理解为 `eventfd + epoll`，但结尾交叉参考仍写成 `§1.13 MessageQueue 机制（Pipe + epoll 在 Looper 中的应用）`。这既和本章自己的结论冲突，也和项目中的实际章节名 `MessageQueue 机制与 DeliQueue 无锁优化` 不一致。另：L346 的“更准确的说法是”、L360 的“先别把”、L190/L310 的“本质上”仍命中 technical-writing SKILL 禁句式，但这不是本轮主审项。

- **建议**：把交叉参考改成项目中的实际标题，或改写为 `§1.13 MessageQueue / Looper 唤醒路径（eventfd + epoll）`；顺手清掉上述禁句式。

- **类型**：存疑

- **位置**：「为什么 Binder 只需要"一次拷贝"」段落，scatter-gather 描述

- **问题**：原文称 scatter-gather 将"原来需要三次拷贝的流程减少到一次"。标准 Binder 叙述是通过 mmap 实现一次拷贝（相比传统 IPC 的两次），scatter-gather 进一步优化事务结构。"三次拷贝"的说法来源不明。

- **建议**：对照 AOSP binder.c 中 scatter-gather patch（Android 8 引入）确认原始流程的拷贝次数，修正措辞

- **review 日志**：logs/review/2026-04-19-07-review.md

- **类型**：存疑

- **位置**：「用 SQL 统计锁竞争」段落

- **问题**：SQL 查询 GROUP BY s.slice_id 后 count(1) 恒为 1，无法真正统计"同一把锁上有多少线程在排队"。查询的实际用途是"按耗时排序的锁竞争事件列表"，与注释描述（统计锁竞争深度）不符。

- **建议**：重写 SQL 按锁标识 + 时间重叠范围计算真正的锁深度，或修改注释描述使其与查询实际行为一致

- **review 日志**：logs/review/2026-04-19-07-review.md

- **类型**：版本差异/交叉引用

- **位置**：Handler / MessageQueue 段（L153-L155）与参考资料（L223-L224）

- **问题**：正文和参考资料直接给出 master 分支的 `LockedMessageQueue/MessageQueue.java`，但 related chapter §1.13 以及 `android-16.0.0_r1` 公共 tag 仍使用 `LegacyMessageQueue/MessageQueue.java`。缺少 rename / tag 差异说明时，读者按章节交叉阅读会误以为有一处源码路径写错。

- **建议**：补一条版本说明，明确 `android-16.0.0_r1` 使用 `LegacyMessageQueue`，master / Android 17 代码树已切到 `LockedMessageQueue`，并在参考资料里给出对应 tag 的路径或说明。

- **类型**：源码准确性

- **位置**：BLASTBufferQueue 段（L169）与参考资料（L228）

- **问题**：`SurfaceControl.java` 被标成 “`mergeWithNextTransaction` Java 侧钩子”。AOSP master 里实际可见的方法名是 `onMergeWithNextTransaction()`，注释也说明它用于 BLAST 走 Java merge 路径时的 logging / callstack debugging，不是 BLAST 同步语义的主实现锚点。

- **建议**：把引用修正为 `onMergeWithNextTransaction()`，并把 `BLASTBufferQueue.cpp` / `BLASTBufferQueue.h` 作为同步语义的主锚点；如果保留 `SurfaceControl.java`，应明确它在这里主要用于调试路径说明。

- **类型**：数据缺失/知识盲区

- **位置**：Google 内部的性能测试基础设施（L202-L207）

- **问题**：这一节给了 “平台 benchmark 仓库 / 持续回归监控 / 多规格设备池” 三个判断，但没有任何公开锚点，正文还保留了 `[待补充]`。当前内容更像合理推断，读者无法区分哪些是公开可证实的信息，哪些只是工程常识。

- **建议**：补充至少 1-2 个公开锚点（例如 AOSP `platform_testing`、Perfetto 公开 benchmark / Android Dev Summit 公开演讲），或者把小节降格为 “公开可见部分”，只保留有来源的内容。

- **类型**：存疑

- **位置**：线程数量节

- **问题**：Binder pool "上限是 16 个"与 1.4 Binder 章 "默认上限 15 个"不一致。本章写"默认是 1 个已经启动的 pool thread，再加上内核按需追加的最多 15 个 pool threads，上限是 16 个"。1.4 章写"默认上限 15 个"。

- **建议**：对照 AOSP ProcessState.cpp 中 DEFAULT_MAX_BINDER_THREADS 的定义，确认总数是 15 还是 16，并统一两章表述

- **review 日志**：logs/review/2026-04-19-08-review.md

- **类型**：待验证

- **位置**：线程优先级节 cgroup 段

- **问题**："前台 cgroup 和后台 cgroup 的 CPU 时间分配比例大约是 95:5" 无具体验证来源或数据支撑

- **建议**：补充设备实测数据（读取 /dev/cpuctl 的 shares 值）或内核文档依据；如无法确认，标注 [待验证]

- **review 日志**：logs/review/2026-04-19-08-review.md

- **类型**：数据缺失/版本差异

- **位置**：L222-L224

- **问题**：把 `Displayed` 日志写成“从 API 24 开始包含 TTID 信息”，并紧接着给出 `Jetpack App Startup` “每个 ContentProvider 约 2ms” 的确定数值。官方启动文档确认 `Displayed` 可用于取 TTID，但未在该处给出 API 24 边界；App Startup 官方文档只说 ContentProvider 昂贵、合并到单一 InitializationProvider 可显著改善启动时间，没有给出 2ms 官方口径。

- **建议**：把 `Displayed` 改成 TTID 的检索方式说明，不额外绑定未经证实的 API 24 分界；把 `2ms` 改成非量化描述，或明确标注 `[待验证]` 并补一手来源。

- **类型**：交叉引用/来源准确性

- **位置**：frontmatter sources / L167 / L422

- **问题**：JankStats 的官方 release note 链接仍写成 `developer.android.com/jetpack/androidx/releases/jankstats`。当前该地址会跳转到通用 versions 页，稳定版 1.0.0 的有效发布说明位于 `developer.android.com/jetpack/androidx/releases/metrics`。

- **建议**：把 JankStats 的版本来源统一更新到 `androidx.metrics` 的 `metrics` 发布页，避免读者回源时落到无效锚点。

- **类型**：源码准确性

- **位置**：L414-L425 参考资料

- **问题**：参考资料把 `frameworks/base/services/core/java/com/android/server/am/ProcessRecord.java` 标成“ANR 检测与 traces 写入”主锚点。Android 16 的 ANR 入口和处理链已经主要落在 `ProcessErrorStateRecord.java` 与 `AnrHelper.java`，`ProcessRecord.java` 更多是承接 kill/exit record。

- **建议**：把 ANR 检测/trace 参考锚点改为 `ProcessErrorStateRecord.java`、`AnrHelper.java`，`ProcessRecord.java` 只在需要说明 killLocked/ApplicationExitInfo 记录时保留。

- **类型**：数据支撑

- **位置**：第 274 行 FrameMetrics TOTAL_DURATION 描述

- **问题**：TOTAL_DURATION 起点描述不够精确。文中说「从 performTraversals() 开始到帧提交到 BufferQueue 结束」，严格来说 TOTAL_DURATION 覆盖从 VSYNC 信号到 GPU 命令提交完成的全过程（SWAP_BUFFERS + COMMAND_ISSUE），包含 VSYNC 到 performTraversals 之间的 input handling 和 animation 时间。

- **建议**：改为「TOTAL_DURATION 覆盖从 VSync 信号到 GPU 命令提交完成的全过程」

- **来源**：Claude Opus 4.6 (Thinking) 外部 review

- **类型**：数据支撑

- **位置**：第 280 行 APK 体积转化率

- **问题**：「APK 体积每增加 10MB，安装转化率下降约 1.5%」——Google 确实公布过类似数据，但具体数字因年份、市场和 App 类型而异。建议标注数据来源和年份。

- **建议**：加注「来源: Google I/O 2019, "Size matters: Reduce your app size and increase installs"；该数据为全球平均，新兴市场的影响更大」

- **来源**：Claude Opus 4.6 (Thinking) 外部 review

- **类型**：原理完整性

- **位置**：第 92 行动画缩放建议值

- **问题**：建议「将动画缩放设为 0.5x 或关闭」，但设为 0x（关闭动画）会导致某些 App 的启动动画被跳过，可能改变启动流程的时序。设为 0.5x 则动画仍存在但更短。建议更明确地说明取舍。

- **建议**：修改为「设为 0.5x（保留动画但缩短时长）或 1x（保持默认，如果要对比真实用户体验）。不建议完全关闭（0x），因为某些 App 的启动流程可能依赖动画完成回调。」

- **来源**：Claude Opus 4.6 (Thinking) 外部 review

- **类型**：兼容性预警

- **位置**：mMessages 反射访问

- **问题**：mMessages == null 场景下，retarget 37 后的反射代码必崩，需提前告知读者

- **建议**：在涉及反射访问 MessageQueue 内部字段时增加兼容性警告说明，明确 targetSdkVersion 37+ 的限制

- **来源**：外部 AI review

- **类型**：源码准确性

- **位置**：L96-L108, L222-L224（`sw_sync` 边界）

- **问题**：AOSP `libsync/sw_sync.h` 的头注释只明确 `sw_sync` “mainly intended for testing and should not be compiled into production kernels”，但正文把它扩展成“测试和特定软件管线 / fallback 工具”的通用表述，证据链超出了当前引用源码能直接支撑的范围。

- **建议**：把正文收紧为“`sw_sync` 主要面向测试；是否在量产内核中可用取决于内核配置，不应默认当作生产路径 fallback”，如果要保留“特定软件管线”说法，补充实际 shipping 场景或内核配置依据。

- **类型**：数据缺失

- **位置**：L171-L187（Perfetto 诊断段）

- **问题**：Perfetto 诊断部分只有 `[图：...]` 占位，没有真实 trace 片段、slice 名称或最小案例，导致“acquire fence 等 producer”和“release fence 等 consumer”的判断缺少可复现证据。

- **建议**：至少补 1 组真实 trace 证据，给出同窗体 `queueBuffer()` / `latchBuffer` / `presentDisplay()` 的时间对齐关系，或附一段可直接复用的 Perfetto 观察 checklist。

- **类型**：需补充素材

- **位置**：第二代 Vulkan 段 / AVP 2025 说明区域

- **问题**：external-review P1 标记：AVP 2025 强制要求 VK_EXT_host_image_copy，目标是将纹理加载负载降低 50%。当前章节未提及此扩展。

- **建议**：在 AVP 2025 描述中补充此扩展的能力说明和性能影响数据。

- **review 日志**：logs/review/2026-04-19-10-review.md

- **类型**：需补充素材

- **位置**：缺失（目前无 WebGPU 相关内容）

- **问题**：external-review P1 标记：Dawn 库在 AOSP 16 中作为 WebView 高性能后端集成，支持"高级保护模式"安全隔离。这是图形 API 演进的重要方向，但章节完全未涉及。

- **建议**：在 ANGLE 段或新增小节中补充 WebGPU/Dawn 的定位，包括它与 ANGLE/Vulkan 的关系、性能影响和安全隔离模型。

- **review 日志**：logs/review/2026-04-19-10-review.md

- **类型**：需补充素材

- **位置**：缺失（ANGLE 角色段）

- **问题**：external-review P1 标记：GraphicsEnv 支持基于 ADPF 热状态动态降级驱动路径（如强制从 native GLES 切换至 ANGLE 以降低功耗）。这是 Android 15+ 图形栈收敛的重要维度。

- **建议**：在 ANGLE 角色与 Android 图形栈收敛段中补充"热管理选路"机制：性能优先 → 功耗优先(ANGLE) → 安全优先(禁用 WebGPU)。

- **review 日志**：logs/review/2026-04-19-10-review.md

- **类型**：需补充素材

- **位置**：迁移策略 → 验证层段落（第 5 条）

- **问题**："验证层会带来显著的性能开销"使用模糊形容词"显著"，未给出具体数据或参考来源。

- **建议**：补充大致的性能影响范围（如"2-5x CPU 开销"）或引用 Khronos Validation Layer 性能文档。

- **review 日志**：logs/review/2026-04-19-10-review.md

- **类型**：外部 review 建议

- **位置**：7.3

- **问题**：[FrameMetrics 判定细节]

- **原文问题**：建议补充 FrameMetrics 在 API 31 之前手动计算 deadline 的一个关键缺陷：它无法识别系统正在利用“三级缓冲”来消化瞬时波动的意图。

- **建议**：在对比 `DEADLINE` API 时，强调原生 `DEADLINE` 包含了 SurfaceFlinger 对 VSync Offset 的动态调整，这是手动计算 `1000/refreshRate` 永远无法覆盖的。

- **建议**：基于外部 AI review 建议改进

- **来源**：外部 AI review (2026-04-19-10-03-jank-methodology-external-review.md)

- **类型**：外部 review 建议

- **位置**：7.6

- **问题**：[案例二：Binder 调用]

- **问题描述**：原文列举了 I/O 阻塞来源，但遗漏了最隐蔽的 `SharedPreferences.getString()`。

- **证据依据**：`SharedPreferencesImpl.awaitLoadedLocked` 在冷启动或 SP 文件过大时会直接导致主线程 `wait()`，这是极高频的卡顿根因。

- **建议**：在“举一反三”中加入 SP 阻塞的说明，并推荐 MMKV 或 DataStore。

- **建议**：基于外部 AI review 建议改进

- **来源**：外部 AI review (2026-04-19-10-06-case-studies-external-review.md)

- **类型**：外部 review 建议

- **位置**：7.6

- **问题**：[案例三：内存压力]

- **原文问题**：代码示例 `LruCache<String, Bitmap>(Int.MAX_VALUE)`。

- **问题描述**：`LruCache` 的构造函数必须传入一个合理的 `maxSize`，传入 `MAX_VALUE` 虽技术可行但属于极差实践，且未说明 `sizeOf` 的计算逻辑。

- **建议**：修正示例代码，强调 `maxSize` 应基于 `Runtime.maxMemory()` 动态计算。

- **建议**：基于外部 AI review 建议改进

- **来源**：外部 AI review (2026-04-19-10-06-case-studies-external-review.md)

- **类型**：外部 review 建议

- **位置**：7.7

- **问题**：[重组本质]

- **原文位置**：`Greeting` 编译后代码示例。

- **建议**：建议补充 `$changed` 位运算的简要说明，说明 Compose 如何通过一个 `Int` 存储多个参数的变化状态，这是实现“智能重组”的高效底层设计。

- **建议**：基于外部 AI review 建议改进

- **来源**：外部 AI review (2026-04-19-10-07-compose-performance-external-review.md)

- **类型**：外部 review 建议

- **位置**：7.12

- **问题**：[通知内容绑定]

- 原文问题：提到 `applyAsync()` / `reapplyAsync()`，但未区分两者的性能差异。

- 证据或观察依据：`RemoteViews.reapplyAsync` 在通知更新（而非新增）时通过 `diff` 算法仅更新变化的 View，开销远小于 `applyAsync`。

- 建议：补充说明在 Trace 中如果看到频繁的 `apply`（全量绑定）而非 `reapply`，通常意味着 App 侧发送的通知数据结构发生了不必要的剧变。

- **建议**：基于外部 AI review 建议改进

- **来源**：外部 AI review (2026-04-19-10-13-systemui-performance-external-review.md)

- **类型**：外部 review 建议

- **位置**：unknown

- **问题**：[01-jank-definition.md]

- 原文问题：BufferStuffing 节缺少具体的 Latency 增加数据说明。

- 建议：补充 BufferStuffing 导致“画面流畅但输入极度不跟手”的 Perfetto 观察点（如 BufferQueue 深度 > 1 时 Latency 的阶梯式增长）。

- **建议**：基于外部 AI review 建议改进

- **来源**：外部 AI review (2026-04-19-10-README-external-review.md)

- **类型**：知识盲区

- **位置**：L108-L128 / L402-L416 `Dispatchers.IO` 与限制并发示例

- **问题**：正文解释了 `Dispatchers.IO` 的默认并发上限和与 `Dispatchers.Default` 共享线程的实现，但没有补上官方 `Dispatchers.IO.limitedParallelism(n)` 的弹性视图语义。后文直接给出 `Semaphore` 限流示例，容易让读者误以为限制阻塞并发只能靠手写同步器。

- **建议**：补充 `limitedParallelism`：它可以为特定阻塞资源创建独立并发视图，不受 IO 默认 64 限制约束，但仍与 IO / Default 共享线程资源；再说明它与 `Semaphore` / 自建 Executor 的适用边界。

- **类型**：数据缺失

- **位置**：L503-L506 版本演进

- **问题**：正文给出“多并发请求场景性能提升约 15%”这一量化结论，但紧接着又标注“官方 benchmark 数据待验证”，当前缺少能回溯到 release note / changelog / benchmark 的一手锚点。

- **建议**：补上具体版本号、基准场景和一手来源；如果暂时拿不到官方 benchmark，就把表述降级为“调度与上下文切换成本继续下降”，不要保留 15% 这个确定数字。

- **类型**：需确认

- **位置**：Gralloc HAL 版本描述（全文多处）

- **问题**：external-review P1 断言 Android 16 强制 Gralloc 5.0 AIDL、HIDL 4.0 实质性弃用。当前稿件基于源码观察为 AIDL 与 HIDL 并存。两者对版本状态描述不一致

- **建议**：Task 9 对照 AOSP 最终 tag 和 CDD 确认

- **review 日志**：logs/review/2026-04-19-11-review.md

- **类型**：需补充素材

- **位置**：全文缺失

- **问题**：16KB 页面模式下小尺寸 Buffer 的 Slack Space 导致显存利用率骤降，PSS 可能翻倍

- **建议**：Task 2B 补充 16KB 对齐影响、reservedSize 参数、BufferDescriptorInfo 新增字段

- **review 日志**：logs/review/2026-04-19-11-review.md

- **类型**：需补充素材

- **位置**：DMA-BUF fd 泄漏节

- **问题**：[待补充：Trace 截图] 为占位符

- **建议**：高爷补充实际 Trace 截图或详细描述

- **review 日志**：logs/review/2026-04-19-11-review.md

- **类型**：原理链完整性

- **位置**：首帧绘制路径

- **问题**：将 TTID 终点等同于 `queueBuffer`。

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：实战落地

- **位置**：reportFullyDrawn

- **问题**：建议手动调用 `reportFullyDrawn()`。

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：数据/案例支撑

- **位置**：点击延迟数据

- **问题**：点击响应延迟估算为 30-60ms，缺乏具体设备参考。

- **建议**：补充在 120Hz 设备上，一帧仅 8.33ms，若 onClick 阻塞 20ms 会导致丢 3 帧的量化说明，以强调“零阻塞”的紧迫性。

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：源码准确性

- **位置**：Trace 断面名称

- **问题**：文中提到 `RV onCreateViewHolder type=0x%X`。

- **建议**：加入该公式，并解释其在“性能感知与自我调节”中的设计意图。

- **来源**：Gemini 外部 review

- **类型**：知识盲区

- **位置**：Android 17 ART 优化

- **问题**：[P2 issue from external review]

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：原理链完整性

- **位置**：Coil 移除 BitmapPool 的深意

- **问题**：[P2 issue from external review]

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：数据/案例支撑

- **位置**：AndroTest 基准说明

- **问题**：[P2 issue from external review]

- **建议**：参考 `samudoria/GAPS` 源码，重写动态执行阶段逻辑，强调 LLM 在语义映射中的作用。

- **来源**：Gemini 外部 review

- **类型**：数据支撑

- **位置**：Perfetto 表现

- **问题**：[P2 issue from external review]

- **建议**：更新为 40s (30s+10s)，并引用 `ActivityManagerConstants`。

- **来源**：Gemini 外部 review

- **类型**：知识盲区

- **位置**：案例 1

- **问题**：PSI 信息仅给出了值，未给出判断阈值。

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：版本差异

- **位置**：16 KB 页面支持

- **问题**：[P2 issue from external review]

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：原理链

- **位置**：IO 调度器弹性

- **问题**：[P2 issue from external review]

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：源码准确性

- **位置**：100µs 规则

- **问题**：[P2 issue from external review]

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：原理链完整性

- **位置**：RemoteViews 反射开销

- **问题**：提到 `RemoteViews.apply()` 但未解释反射的具体代价。

- **建议**：引用 `mMaxPackageEnqueueRate` 和 `mUsageStats.getAppEnqueueRate(pkg)`。

- **来源**：Gemini 外部 review

- **类型**：知识盲区

- **位置**：ARMv9 AutoFDO 演进

- **问题**：[P2 issue from external review]

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：工具边界

- **位置**：Android 12-17 表格

- **问题**：[P2 issue from external review]

- **建议**：引用 `am_freeze` / `am_unfreeze` 日志，并说明在 Perfetto 中识别该场景的方法。

- **来源**：Gemini 外部 review

- **类型**：知识盲区

- **位置**：5. Perfetto 中的关键 Track

- **问题**：[P2 issue from external review]

- **建议**：基于外部 AI review 修正

- **来源**：Gemini 外部 review

- **类型**：数据/案例支撑

- **位置**：5.2 关键分析路径

- **问题**：[P2 issue from external review]

- **建议**：明确 5s 超时逻辑；新增 Android 17 帧率类别 API 说明。

- **来源**：Gemini 外部 review

- **类型**：术语校正

- **位置**：OPPO 反碎片技术段落

- **问题**：术语 MF/CSVM 的定义与 OPPO 公开资料有出入

- **建议**：核实缩写，若无明确证据改为更通用的"物理页迁移分组"和"虚拟地址重排"描述

- **来源**：Gemini 外部 review

- **类型**：数值修正

- **位置**：ART GC 暂停时间描述

- **问题**：描述 CC GC 暂停时间"在 1ms 以下"，实际 Minor GC 暂停目标为 1ms-3ms

- **建议**：修正数值，强调 1ms 是 Minor GC 理想目标，Major GC 在压力下仍可能达 10ms+

- **来源**：Gemini 外部 review

- **类型**：分析补充

- **位置**：案例四 - 内存突增

- **问题**：未说明如何区分"对象风暴"与"内存泄漏"的 Trace 表现

- **建议**：补充差异：对象风暴 GC 后基准线平稳；泄漏基准线阶梯式上升

- **来源**：Gemini 外部 review

- **类型**：源码补充

- **位置**：案例二 - Bitmap 泄漏

- **问题**：未详述 Android 8.0+ Bitmap Native 堆回收链路

- **建议**：补充 NativeAllocationRegistry + Cleaner 机制

- **来源**：Gemini 外部 review

- **类型**：知识补充

- **位置**：Kotlin value class 优化

- **问题**：未提及 Kotlin 对无符号类型（UIntArray 等）的特殊处理

- **建议**：补充避免 value class 数组装箱的工程实践

- **来源**：Gemini 外部 review

- **类型**：版本差异补充

- **位置**：CursorWindow 共享内存

- **问题**：仅提到 ashmem，未提及 Android 12+ memfd 迁移

- **建议**：增加 memfd 密封机制描述

- **来源**：Gemini 外部 review

- **类型**：数据补充

- **位置**：F2FS WAL 写入放大

- **问题**：未提及 synchronous=NORMAL 的收益原理

- **建议**：补充 WAL 下 NORMAL 仅在 checkpoint 时 sync

- **来源**：Gemini 外部 review

- **类型**：数据补充

- **位置**：Migration 耗时

- **问题**：缺乏量化参考

- **建议**：补充"5000 条记录下增加带索引的列可能导致 100ms+ 主线程卡顿"

- **来源**：Gemini 外部 review

- **类型**：术语一致性

- **位置**：CPU 功耗公式

- **问题**：getAveragePowerForCpuScalingStep() 在 Android 16 中已演进

- **建议**：指出 getAveragePowerForCpuScalingPolicy 是核心方法

- **来源**：Gemini 外部 review

- **类型**：原理补充

- **位置**：ODPM 章节

- **问题**：未明确 UC 如何从 HAL 的 uWs 转换

- **建议**：补充 Framework 读取平均电压完成能量到电荷的转换链

- **来源**：Gemini 外部 review

- **类型**：内容完整性

- **位置**：全章

- **问题**：存在多处 [待补充] 占位符

- **建议**：补齐关键截图或等效文本描述

- **来源**：Gemini 外部 review

- **类型**：概念澄清

- **位置**：Foreground Service 与 Wakelock

- **问题**：缺乏 FGS vs Wakelock 的源码支撑

- **建议**：补充 ActiveServices.java 中 FGS 仅提升 OOM 优先级

- **来源**：Gemini 外部 review

- **类型**：工具更新

- **位置**：Native 库瘦身

- **问题**：ANDROID_STRIP_DEBUG_SYMBOLS 是较旧方式

- **建议**：推荐 AGP 8.x packaging DSL 或 nativeSymbolTables 闭包

- **来源**：Gemini 外部 review

- **类型**：遗漏补充

- **位置**：assets/ 优化

- **问题**：未提及 Lottie 资源在 assets/ 中的体积优化

- **建议**：增加 Lottie 资源 zip 压缩或动态下发建议

- **来源**：Gemini 外部 review

- **类型**：交叉引用

- **位置**：L257-L260

- **问题**：`BufferQueue` 状态被写成互斥的 `DEQUEUED / QUEUED / FREE / ACQUIRED`，和 §2.13 当前 AOSP `BufferSlot::BufferState` 的 counter-based 表述不一致，shared mode 下状态可叠加。

- **建议**：这里改成“普通路径通常呈现这些状态，但源码判断以 `isFree()/isDequeued()/isQueued()/isAcquired()/isShared()` 为准”，并回链 §2.13 的源码段。

- **类型**：数据缺失

- **位置**：L314-L326

- **问题**：`[待补充：Trace 截图]` 仍未落地，且“Gralloc 分配延迟通常在 1-5ms 之间”缺少设备、SoC、分辨率、像素格式和 trace/benchmark 证据。

- **建议**：补一条真实 Perfetto / ftrace / benchmark 观测并标注测试条件；如果暂时没有实测，删掉“1-5ms”只保留定性判断。

- **类型**：知识盲区 / 数据支撑

- **位置**：OkHttp 连接池描述段

- **问题**：OkHttp 5 引入 ConnectionPool.setPolicy，允许针对特定地址配置最小连接数（proactive open），对冷启动极低延迟场景有实战价值

- **建议**：补充 OkHttp 5 setPolicy 预建连特性的说明和使用场景

- **来源**：外部 AI review（2026-04-19-12-03-network-performance-deep-external-review.md）

- **类型**：版本差异 / 数据支撑

- **位置**：网络请求对电池的影响段

- **问题**：原文仅提到 4G 状态机，缺少 5G RRC_INACTIVE 状态对功耗和延迟优化的说明

- **建议**：补充 5G RRC_INACTIVE 状态转换逻辑及 tail time 差异，参考 3GPP 文档和 Qualcomm 5G 白皮书

- **来源**：外部 AI review（2026-04-19-12-03-network-performance-deep-external-review.md）

- **类型**：版本差异补充

- **位置**：2.1/2.3 节 CursorWindow 共享内存

- **问题**：仅描述 ashmem FD 共享，未覆盖 Android 12+ memfd 迁移和 Android 15+ GKI 强制 memfd 路径

- **建议**：增加 ashmem → memfd 版本演进段落，说明 memfd 密封机制(Sealing)和 /proc/pid/maps 中的表现差异

- **来源**：外部 AI review

- **类型**：原理补充

- **位置**：1.1 节 F2FS WAL 写入放大

- **问题**：未解释 synchronous=NORMAL 在 WAL 模式下为何安全且高性能

- **建议**：补充说明 NORMAL 模式在 WAL 下仅在 checkpoint 时 sync，减少 F2FS 双重日志(Double Journaling)压力

- **来源**：外部 AI review

- **类型**：数据补充

- **位置**：3.4 节 Migration 耗时

- **问题**：Migration 耗时缺乏量化感知

- **建议**：补充基准参考，如"5000 条记录下增加带索引列可能导致 100ms+ 主线程卡顿"

- **来源**：外部 AI review

- **类型**：数据缺失

- **位置**：第 167-169 行（draw call CPU 开销对比）

- **问题**："OpenGL ES 10-50μs vs Vulkan 1-5μs" 只有宽泛来源，缺少 SoC/GPU、驱动版本、draw call 形态、采样方法和测试条件，当前写法会被读者误读成通用基线。

- **建议**：补上具体测试条件和原始出处；如果拿不到稳定对比数据，改成定性结论，只保留"Vulkan 通常能显著降低 CPU driver overhead"这一层。

- **类型**：需确认（技术事实准确性）

- **位置**：mm_events：内核内存事件的快照

- **问题**：原文描述 mm_events "不会持续记录，只在检测到压力时自动启动"，外部 review 指出它实际是常驻守护进程，通过 perf_event_open 监听内核 tracepoints。属于技术事实错误，需 Task 9 验证后由 Task 2B 修正。

- **建议**：明确 mm_events 的常驻工作模式，补充其依赖的内核 tracepoints（mm_vmscan_* 系列）

- **review 日志**：logs/review/2026-04-19-14-review.md

- **类型**：需补充素材

- **位置**：系统级内存优化 / 低端机专项优化

- **问题**：缺失 Android 15 的 16KB Page Size 对低内存场景的影响分析（RSS 通常增加约 9%，内存压力感知提前）；ZRAM recomp_algorithm sysfs 接口未覆盖具体配置方式；MGLRU 缺少 /sys/kernel/mm/lru_gen/enabled 配置值及 Perfetto 中的量化方法

- **建议**：在"系统级内存优化"章节新增"Android 15+ 专项演进"小节，覆盖 16KB Page 和 ZRAM 重压缩细节；补充 MGLRU 的 Trace 量化方法

- **review 日志**：logs/review/2026-04-19-14-review.md

- **类型**：需确认（数值准确性）

- **位置**：低内存下的 GC 行为变化 / ART GC 在低内存下的触发策略

- **问题**：原文称 CC GC Young GC 暂停时间"通常在 1ms 以下"，外部 review 指出 Android 15 Generational CC 的 Minor GC 暂停目标通常为 1ms-3ms，且 Major GC/Full GC 在压力下可达 10ms+。当前数值需 Task 9 验证后修正范围。

- **建议**：修正数值范围，区分 Minor GC 与 Major/Full GC 的暂停时间差异

- **review 日志**：logs/review/2026-04-19-14-review.md

- **类型**：源码锚点补充

- **位置**：CT 验证机制段

- **问题**：未给出 Conscrypt CT 检查核心类源码锚点

- **建议**：补充 external/conscrypt/src/main/java/org/conscrypt/ct/CTVerifier.java 及 TrustManagerImpl.checkTrustedRecursive() 集成调用

- **来源**：Gemini 外部 review

- **类型**：数据量化

- **位置**：HTTP→HTTPS 重定向延迟

- **问题**："额外增加 1-2 个 RTT" 缺乏体感量化

- **建议**：补充弱网/4G 环境下重定向导致首屏 API 返回时间被拉长 100-300ms 的参考数据

- **来源**：Gemini 外部 review

- **类型**：原理链完善

- **位置**：ECH 性能影响段

- **问题**：对 DoH/DoT 依赖只写结论，未提降级攻击

- **建议**：补充一句话解释明文 DNS 下 HTTPS Record 被篡改/丢弃的降级攻击风险

- **来源**：Gemini 外部 review

- **类型**：关键 API 提示

- **位置**：典型模式对比 - Android View（软件）

- **问题**：缺乏 Trace 视角的关键 API 提示

- **建议**：补充 lockCanvas 和 unlockCanvasAndPost 的字眼，帮助分析人员在 Trace 中快速识别 UI 线程软件渲染

- **来源**：Gemini 外部 review

- **类型**：表述严谨性

- **位置**：Flutter 补充概览

- **问题**：线程合并描述缺乏场景前提

- **建议**：明确指出 Flutter UI/Platform 线程合并主要发生在依赖 Platform View 混合渲染的场景，以解决帧同步问题

- **来源**：Gemini 外部 review

- **类型**：版本差异覆盖

- **位置**：18.2.4 Trace 视角 - SF 端 Slice

- **问题**：仅列举 setTransactionState，未覆盖 Android 12+ 的新 Slice 名称

- **建议**：补充 commit、applyTransactionState 等现代版本 Slice 名称

- **来源**：Gemini 外部 review

- **类型**：描述严谨性

- **位置**：18.3.4 Trace 视角

- **问题**："几乎看不到 dequeueBuffer"表述不准

- **建议**：修正为"dequeueBuffer 和 queueBuffer 被转移到 UI Thread 执行，出现在 lockCanvas/unlockCanvasAndPost 调用栈内"

- **来源**：Gemini 外部 review

- **类型**：配图修正

- **位置**：渲染时序图

- **问题**：时序图中 UI->>UI: Draw（带裁剪区域）未能体现擦除/打洞

- **建议**：修改为 'Draw（在宿主 Buffer 中以透明色挖洞）'

- **来源**：Gemini 外部 review

- **类型**：数据支撑

- **位置**：Trace 视角 - eglMakeCurrent

- **问题**：eglMakeCurrent 耗时缺乏量化体感

- **建议**：补充低端机 2-5ms 耗时参考值，提示在 Trace 中搜索 eglMakeCurrent slice

- **来源**：Gemini 外部 review

- **类型**：数据缺失

- **位置**：§2.17.6 验证路径（Perfetto / FrameStatistics）

- **问题**：当前章节给了 SQL 和统计项名称，但仍停留在“应当看哪些轨道/直方图”的层面，没有给出一组真实 trace 截图、FrameStatistics logcat 样例或 SwappyStats 读数，读者很难校准 BufferStuffing、lateFrames、idleFrames 在真实样本里应该长什么样。

- **建议**：补 1 组最小证据链，至少包含一张启用前后对比图，或 1 段 FrameStatistics / SwappyStats 样例输出，并把结论回连到 buffered frames、jank_type 或某个 histogram 字段。

- **类型**：需重写

- **位置**：全文多处（四个 RequestBuilder 的讲解段落）

- **问题**：章节整体风格偏向 API 文档，像 Android Developers 官方文档的中文扩展版。四个 RequestBuilder（SystemTrace / JavaHeapDump / HeapProfile / StackSampling）的讲解方式几乎相同：建 Builder → 设参数 → 调 requestProfiling → 处理回调。缺少每个类型的独特实战视角和"为什么这样设计"的设计意图解读。

- **建议**：参考 writing-guide.md 类型 C（工具使用篇）结构，补充：(1) 每种 profiling 类型适合什么场景、不适合什么场景的判断框架；(2) RequestBuilder 为什么选择 Consumer 回调模式；(3) 精简重复的代码模板，只保留各类型的差异部分。

- **review 日志**：logs/review/2026-04-19-15-review.md

- **类型**：需重写

- **位置**：全文代码块（SystemTraceExample、HeapDump/HeapProfile/StackSampling 示例、ANR 触发器示例等）

- **问题**：多个代码示例包含完整的 import 语句、类定义、辅助方法，每个 30-50 行。按 writing-guide.md 规范，正文只保留骨架和关键路径，过长代码应放附录。连续多个长代码块导致节奏偏平，读者容易跳过。

- **建议**：精简代码到 10-15 行的核心逻辑，去掉 import 和样板代码。用注释标明省略部分。保留关键参数和调用逻辑即可。

- **review 日志**：logs/review/2026-04-19-15-review.md

- **类型**：需补充

- **位置**：frontmatter

- **问题**：缺少 section、section_title、applicable_versions、sources 字段。

- **建议**：补充 section: "14.7", section_title: "ProfilingManager", applicable_versions: "Android 15+（System Triggered Profiling 16+）", sources 列出主要素材来源。

- **review 日志**：logs/review/2026-04-19-15-review.md

- **类型**：实战指导

- **位置**：18.9.5 Presentation Mode

- **问题**：忽略了国内 OS 对呈现模式的强制覆写现象（IMMEDIATE 被降级为 FIFO）

- **建议**：增加关于 Android 厂商可能在 SF 层强行限制 IMMEDIATE 模式的提示，实际须通过 Trace 确认帧提交模式

- **来源**：Gemini 外部 review

- **类型**：数据支撑

- **位置**：18.9.5 Presentation Mode

- **问题**：MAILBOX 和 IMMEDIATE 缺少在 Android 实际设备上的表现支撑

- **建议**：补充实战提醒，说明大多数定制系统的 SurfaceFlinger 配置不支持真正的 IMMEDIATE 无撕裂

- **来源**：Gemini 外部 review

- **类型**：API 细节

- **位置**：4.4 Callback 及 4.3 Color Layer

- **问题**：ASurfaceTransactionStats_getAcquireTime 已被标记 deprecated；缺失对 Buffer Dataspace 的补充

- **建议**：补充 deprecated 提示，并提及 ASurfaceTransaction_setBufferDataSpace 使色彩管理更完整

- **来源**：Gemini 外部 review

- **类型**：追踪调试

- **位置**：在 Perfetto 中识别 ANGLE

- **问题**：缺乏 ANGLE 自有 trace marker 开启方式说明，仅通过 vk* 过滤容易和 Skia Vulkan 混淆

- **建议**：补充开启 ANGLE 内部 perfetto events 的方式，或通过调用栈特征区分 Skia 和 ANGLE

- **来源**：Gemini 外部 review

- **类型**：代码严谨性

- **位置**：A4A Rules JSON

- **问题**：附录中 a4a_rules.json 描述可能过于具体，存在 AI 脑补风险

- **建议**：融合到正文时只说明"可通过平台 rules 配置进行设备/驱动黑白名单控制"，避免硬编码 JSON 示例

- **来源**：Gemini 外部 review

- **类型**：数据支撑不足

- **位置**：在 Perfetto 中识别 Flutter 链路

- **问题**：仅有 [待补充...] 占位符，缺乏实际 Trace 截图或查询语句

- **建议**：补充 Perfetto SQL 的 Track 过滤查询语句（如 name LIKE '%Engine::BeginFrame%'）

- **来源**：Gemini 外部 review

- **类型**：细节补充

- **位置**：Trace 观察点

- **问题**：缺乏 Perfetto 中关键线程的实际命名说明

- **建议**：补充 Chrome_InProcGpu、CrRendererMain、VizCompositorThread 等真名与概念模型的对应关系

- **来源**：Gemini 外部 review

- **类型**：格式与阅读体验

- **位置**：参考资料部分

- **问题**：罗列大量未处理 URL，阅读体验差

- **建议**：正式定稿时剔除重复及低质量链接，提炼有效信息融入正文

- **来源**：Gemini 外部 review

- **类型**：数据缺失

- **位置**：§14.7 Consumer 回调 / 上线前检查清单（L141-L216）

- **问题**：章节强调 rate limiter、回调与落盘，但没有给出任何 `ProfilingResult` 失败样例，读者看不出 `ERROR_FAILED_RATE_LIMIT_PROCESS`、`ERROR_FAILED_RATE_LIMIT_SYSTEM`、`ERROR_FAILED_NO_DISK_SPACE`、`ERROR_FAILED_POST_PROCESSING` 分别该怎么判断。

- **建议**：补一个错误码对照表，至少覆盖 rate limit、磁盘不足、post-processing 失败，并给出一条 callback 失败日志样例。

- **类型**：交叉引用

- **位置**：frontmatter `related_chapters` / 文末“相关章节”

- **问题**：书内已存在 `src/part2-performance/ch08-responsiveness/08-system-triggered-profiling.md` 的 ProfilingManager system-triggered 专章，但本章没有建立交叉引用，导致 trigger 语义在两章里重复铺开且难以统一版本口径。

- **建议**：把该章节加入 `related_chapters` 与文末“相关章节”，同时把 trigger 细节收束到一处，避免两章各自维护一套版本矩阵。

- **类型**：数据支撑

- **位置**：通知内容绑定段落

- **问题**：提到 `applyAsync()` / `reapplyAsync()`，但未区分两者的性能差异。`RemoteViews.reapplyAsync` 在通知更新（而非新增）时通过 `diff` 算法仅更新变化的 View，开销远小于 `applyAsync`。

- **建议**：补充说明在 Trace 中如果看到频繁的 `apply`（全量绑定）而非 `reapply`，通常意味着 App 侧发送的通知数据结构发生了不必要的剧变。

- **来源**：Gemini 外部 review (2026-04-19-10-7.13-external-review.md)

- **类型**：数据支撑

- **位置**：CPU 三层模型 / Active Base Power 段

- **问题**：提到了 CPU 三层模型，但未明确指出 "Active Base Power"（即 `cpu.active`）的具体物理含义。在异构 SoC 中，只要任一核心唤醒，整个 SoC 的电源平面、内存总线、L3 Cache 都会从 LP 状态切回 Active 状态，这部分固定开销即为 `cpu.active`。

- **建议**：补充这一物理背景，帮助读者理解为什么"高频低负载"比"低频高负载"更费电。

- **来源**：Gemini 外部 review (2026-04-19-12-11.0-external-review.md)

- **类型**：数据缺失

- **位置**：Perfetto / 功耗段（L48、L148、L180、L184-L186）

- **问题**：章节多次用图位和定性判断说明“ARR 正常工作”“模式切换会有长间隔”“高刷驻留会增功耗”，但没有落一份真实 Trace 或电流样本。当前证据链不足以支撑读者复核 ARR 与传统 mode switching 的差异。

- **建议**：补 1 组真实 Perfetto 证据，至少同时展示 `VSYNC-app`、`VSYNC-sf`、FrameTimeline、refresh-rate selection / mode change 观察点；功耗段补测试条件（面板、亮度、分辨率、场景）和一组电流或功耗对比样本。

- **类型**：版本差异

- **位置**：§从多刷新率到 ARR / §Display 查询 API / §版本演进（L54-L56、L70-L87、L190-L194）

- **问题**：正文强调“检查设备是否公开支持 ARR，以及当前系统给出的刷新率范围”，但给出的公开查询手段全部落在 Android 16 `Display` API。对 Android 15-QPR1 支持设备，读者仍缺少一个可执行的能力确认路径，容易把“API 可调用”和“端到端 ARR 能力可用”混为一谈。

- **建议**：补一张版本矩阵，明确 API 35 与 API 36 的能力边界。对 Android 15-QPR1 设备补上 fallback 观察路径，例如 OEM 文档、`dumpsys display` / `SurfaceFlinger`、Trace 中的 mode switching 与 refresh-rate selection 行为特征。

- **类型**：数据缺失

- **位置**：Perfetto 观察表与 SQL 示例（L225, L321-L331）

- **问题**：`wm.pause_timeout`、`SurfaceControl.Transaction.apply`、`animator` 以及 `LIKE '%relayout%'` 被当作稳定切片名使用，但文中没有给出 trace 配置、Android 版本或 sample trace 佐证。不同 atrace category / Perfetto config 下这些名字并不稳定。

- **建议**：补一份可复现的 trace config + sample capture，或把表格改成“常见候选切片/需按版本核对”的写法，并给出至少一条已验证 SQL。

- **类型**：版本差异

- **位置**：版本演进表（L375-L383）

- **问题**：Android 16/17 的 Desktop Windowing、Adaptive Apps、`recreateOnConfigChanges`、Bubbles for all apps 等条目没有在 `sources:` 中挂官方 behavior/features 文档或对应 AOSP 变更，当前版本表可读但不可追溯。

- **建议**：为每一行补官方 features/behavior 文档或源码/commit 锚点；拿不准的 Beta 特性改成 `[待验证]` 并明确版本范围。

- **类型**：数据缺失

- **位置**：§SurfaceFlinger 在多窗口下多了什么工作（L104-L108）

- **问题**：整章还没有一个同设备 full-screen / split-screen / connected-display 的 `dumpsys SurfaceFlinger` 或 Perfetto 样例。当前结论停在定性层，读者看不到 layer 数、composition 路径和 jank_type 怎么随窗口形态变化。

- **建议**：补一组同机型对照样例，至少给出可见 layer 数、HWC/GPU composition 变化，以及主要 jank 类型。

- **类型**：交叉引用

- **位置**：L113 vs L177

- **问题**：同一章前面把 `wake_lock` 行描述为红色块，后面的模式 1 又写成持续绿色，章节内观察口径自相矛盾。

- **建议**：统一成“高亮块/持续占用块”，或明确说明不同 Historian 主题下的颜色差异。

- **类型**：数据缺失

- **位置**：L122-L126、L441（Compose vs View 性能对比）

- **问题**：`LazyColumn 约 43fps vs RecyclerView 60fps` 与“Canvas 绘制几乎一致”只引用社区对比，缺少设备型号、刷新率、Compose / RecyclerView 版本、测试场景和复现实验方法，读者容易把它当成通用结论。

- **建议**：补充 Macrobenchmark / FrameTimingMetric 或 Perfetto Trace 的复现实验，至少标出设备、刷新率、Compose 版本、滚动场景与样本次数；如果暂时没有可复现数据，改成“个别社区测试观察到”。

- **类型**：源码准确性

- **位置**：Android 15 能效模式（L109-L110）

- **问题**：正文把 `PerformanceHintManager.Session#setPreferPowerEfficiency(boolean)` 直接写成“把线程调度到 E-core”。官方公开 API 语义是偏向能效而非性能，没有承诺具体落到哪类 CPU 核心。

- **建议**：把表述收紧成“系统可按能效优先调度这些线程”，不要把公开 API 语义写成固定 E-core 行为。

- **类型**：知识盲区

- **位置**：Perfetto 识别 fsync（L249-L250, L285-L304）

- **问题**：正文只列 `ext4_sync_file_enter/exit`，但 Android 设备大量使用 F2FS；在 F2FS 机型上，读者需要改看 `f2fs_sync_file_enter/exit` 等 tracepoint。

- **建议**：在 fsync 观察点里补一条“文件系统相关”的提示，把 ext4 与 F2FS 的常见 tracepoint 一起列出，避免把 Android I/O 观测默认成 ext4 单一路径。

- **类型**：交叉引用

- **位置**：L137 交叉引用块

- **问题**：`[2.1 BufferQueue 机制]`、`[2.5 SurfaceFlinger]`、`[2.14 图形 API 演进]` 全部指向 `../../part2-performance/../part1-foundation/ch02-graphics-foundation/`，当前仓库不存在该目录，链接失效。

- **建议**：分别改成 `../../part1-fundamentals/ch02-rendering/13-buffer-queue.md`、`../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md`、`../../part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md`。

- **类型**：交叉引用

- **位置**：L239-L242 交叉引用块

- **问题**：`13-buffer-queue.md`、`06-surfaceflinger.md`、`16-sync-fence.md` 被写成当前目录相对路径，但这些文件实际位于 `src/part1-fundamentals/ch02-rendering/`，当前链接全部失效。

- **建议**：改成 `../../part1-fundamentals/ch02-rendering/13-buffer-queue.md`、`../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md`、`../../part1-fundamentals/ch02-rendering/16-sync-fence.md`。

- **类型**：交叉引用

- **位置**：L202-L205 交叉引用块

- **问题**：`13-buffer-queue.md` 与 `14-graphics-api-evolution.md` 被写成当前目录相对路径，无法跳到第 2 章对应章节。

- **建议**：改成 `../../part1-fundamentals/ch02-rendering/13-buffer-queue.md` 与 `../../part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md`。

- **类型**：版本差异

- **位置**：版本演进表 Android 8.0 行

- **问题**：版本表写 scatter-gather "将 Binder 数据拷贝从最多三次减少到一次"，但正文已解释 scatter-gather 是数据组织方式优化（省掉 gather-to-contiguous 中间整理步骤），不改变拷贝次数。基础 mmap 已是单次拷贝。两处表述矛盾。

- **建议**：重写版本表中 scatter-gather 行为"引入 scatter-gather 优化（BC_TRANSACTION_SG），省掉 Parcel 数据的 gather-to-contiguous 中间整理步骤"，避免与正文矛盾。

- **review 日志**：logs/review/2026-04-20-02-review.md

- **类型**：源码准确性

- **位置**：L45-L48 场景列表

- **问题**：Dialog / BottomSheetDialog / PopupWindow 被写成“不是独立 Window（在某些实现中）”。AOSP `Dialog` 直接创建 `PhoneWindow`，`PopupWindow` 也会通过 `WindowManager.LayoutParams` + `invokePopup()` 添加独立窗口。当前说法会把多窗口候选的定义讲混。

- **建议**：改成“它们都是独立窗口，只是 window type / sub-layer 不同”，不要再写“不是独立 Window”。

- **类型**：交叉引用

- **位置**：L269-L272 交叉引用块

- **问题**：`../../part1-foundation/ch02-graphics-foundation/` 路径不存在，且“2.5 SurfaceFlinger”与全书章节编号不一致（应为 2.6）。

- **建议**：分别改成 `../../part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md` 与 `../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md`，并把章节号修正为 2.6。

- **类型**：交叉引用

- **位置**：L315-L321 交叉引用块

- **问题**：`13-buffer-queue.md`、`06-surfaceflinger.md`、`14-graphics-api-evolution.md` 被写成当前目录相对路径，都会跳转失败。

- **建议**：改成 `../../part1-fundamentals/ch02-rendering/13-buffer-queue.md`、`../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md`、`../../part1-fundamentals/ch02-rendering/14-graphics-api-evolution.md`。

- **类型**：交叉引用

- **位置**：L308-L312 交叉引用块

- **问题**：底部把 BufferQueue 写成“2.1”，且 `../../part1-foundation/ch02-graphics-foundation/` 路径不存在，两个链接都会失效。

- **建议**：把章节号改成 2.13，并改用 `../../part1-fundamentals/ch02-rendering/13-buffer-queue.md` 与 `../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md`。

- **类型**：源码准确性

- **位置**：L424-L428 避免 finalize()

- **问题**：`Android 10+ 已经标记 finalize() 为 deprecated` 这一句没有对应到 Android API 参考或 AOSP libcore 的实际标注。当前 `Object#finalize()` 参考页仍只显示 Added in API 1，AOSP `libcore/.../java/lang/Object.java` 在 android-10.0.0_r1 与 android-16.0.0_r1 里也没有 `@Deprecated` 注解。把它写成 Android 10+ 的平台分界，容易让读者误以为这是 Android SDK 的明确弃用节点。

- **建议**：改成更稳的表述：`finalize()` 长期被认为有性能和资源回收问题，应避免在高频对象上使用；如果要写“deprecated”背景，明确说明这是更广义的 Java finalization 弃用语境，不要写成 Android 10+ 的 SDK 版本边界。

- **类型**：版本差异

- **位置**：L232-L243 Perfetto heapprofd

- **问题**：heapprofd 段把“追踪 Native 和 Java 堆分配栈”写成统一能力，但 Perfetto 官方文档区分得更细：Java heap dump 需要 Android 11+；Java heap sampling / `--heaps art` 需要 Android 12+。当前 CLI 示例 `adb shell heapprofd --pid=<PID> --java` 没有写版本边界，容易让读者在 Android 11 设备上把 heap dump 与 sampling 能力混为一谈。

- **建议**：把工具边界拆开写清：Android 11+ 可抓 Java heap dump；Android 12+ 才能用 heapprofd 的 Java sampling / `malloc,art`；Native heap profile 则是另一条 data source。必要时给出一行“这三类能力不要混用名词”的提示。

- **类型**：数据缺失

- **位置**：L86-L103，L167-L173，L202-L218

- **问题**：章节把“模式切换通常 1-3 帧”“Snapdragon PLL 5-15ms”“VSYNC-app 可直接用 `track_event` 查询”放在同一条观察链里，但没有给出设备样本、trace 片段或已验证的 trace schema。读者能理解机制，仍拿不到可复现的量化证据。

- **建议**：补一组真实设备样本（机型、刷新率组合、切换场景）和一段已跑通的 Perfetto 观察方法；如果暂时没有样本，把数值降级成“设备相关/待验证”，并说明 SQL 依赖的具体 trace 表结构。

- **类型**：数据缺失

- **位置**：L179-L194

- **问题**：`120Hz 理想路径约 10-38ms` 这张表没有交代触控采样率、batched input 是否开启、渲染路径（ThreadedRenderer / front buffer）、以及 App 负载条件。数字本身合理，但当前写法更像经验值，缺少复现实验前提。

- **建议**：把这组数字补成“示例测量条件 + 理论上界”两列，至少注明采样率、屏幕刷新率、是否 batching、是否含 SurfaceFlinger present 时间，避免读者把它当成所有设备的通用基线。

- **类型**：数据缺失

- **位置**：L187-L229 gfxinfo / Perfetto 对比实验

- **问题**：两组 LayerType 对比表没有设备型号、Android 版本、刷新率、动画脚本、样本量和采集命令。当前只能证明“曾做过实验”，不能支持读者复现实验或判断结论边界。

- **建议**：补完整实验条件，至少给出设备、系统版本、`adb shell dumpsys gfxinfo` 采集方式、样本帧数，以及对应 Trace 文件或截图。

- **类型**：数据缺失

- **位置**：L93 / L116 / L175 / L263 / L313

- **问题**：多处把 CJK/复杂脚本/Span/单行布局写成“耗时更高”“高出数倍”“数毫秒”，但没有 benchmark、设备、字体集、文本长度或 trace 配置。即使保留了 [待验证]，当前仍缺一组能落地的量化样本。

- **建议**：至少补 1 组可复现实验，覆盖纯文本 vs Span、Latin vs CJK、BoringLayout vs StaticLayout 的测量差异，并给出 Perfetto 配置或 benchmark 条件。

- **类型**：数据缺失

- **位置**：L43 开头转化率数据

- **问题**：“APK 每增加 6 MB，安装转化率下降约 1%”仍停留在 [待验证]。当前又被放在开场核心动机位置，读者容易把它当成 Google 官方可复用基线。

- **建议**：补准确出处与实验上下文；如果找不到可靠原始来源，建议删除具体数字，改用 Google Play / App Bundle 官方可核对的下载体积收益描述。

- **类型**：版本差异 / 数据缺失

- **位置**：L372-L378 Baseline Profile 扩展段

- **问题**：这一段把 Baseline Profile 写成“Android 从 7.0 开始引入”的机制，又给出“磁盘占用往往比对应 DEX 大 10%-30%”的范围，但没有区分 ART profile-guided compilation 的历史、Baseline Profile 作为现代构建产物的支持边界，也没有给任何设备或构建条件。

- **建议**：把“兼容 API 24+”和“Jetpack/AGP 时代的 Baseline Profile 交付方式”拆开描述，并补一组真实安装前后磁盘占用样本，或删除 10%-30% 这类无来源数字。

- **类型**：数据缺失

- **位置**：L330-L348（16KB 页面大小数据与兼容要求）

- **问题**：16KB page size 段引用了官方数字，但把系统开机改善写成约 0.8 秒，官方页面给的是约 950ms；同时漏掉“Google Play 要求同时适用于新 app 和已有 app 更新”的条件，还省略了相机 hot start 4.48% 的上下文。

- **建议**：把数据改回官方口径，并补一句这些数据来自 16KB 设备/内存压力场景下的测试条件。

- **类型**：知识盲区

- **位置**：L257-L261（系统级集成）

- **问题**：userspace native AutoFDO 只给出抽象描述，没有落到具体 AOSP 锚点。当前 AOSP 已有 `frameworks/base/libs/hwui/Android.bp` 的 `libhwui`、`art/libartbase/Android.bp` 的 `libartbase`、`art/runtime/Android.bp` 的 `libart` 直接配置 `afdo: true`，正文缺这层会让“Android 12+ userspace AutoFDO”难以复核。

- **建议**：在支持状态小节补 2-3 个代表性模块名和路径，给读者一个可复查的源码落点。

- **类型**：数据缺失

- **位置**：L423-L428（蓝牙音频延迟范围）

- **问题**：SBC / aptX / LDAC / LC3 的延迟范围都给了具体毫秒数，但没有设备、码率、packet size、head tracking 开关、链路质量或测量方法。当前写法更像经验值，不足以支撑“代表未来方向”的技术判断。

- **建议**：补一条测试条件说明，或把具体毫秒区间改成定性描述，并把 codec / transport / buffering 三层影响拆开写。

- **类型**：版本差异

- **位置**：L333 版本趋势总结

- **问题**：将 Android 15 总结成“后台网络异常提示”会把 lifecycle/network exception 误写成用户可见能力，和前文行为变化不一致。

- **建议**：改成“后台网络访问限制（valid process lifecycle）”，或直接删除这一条“用户可见性”演进。

- **类型**：数据缺失

- **位置**：L418-L432 Play Store 后台行为政策

- **问题**：该段使用了具体阈值、豁免项和分发惩罚，但 frontmatter sources 未收录对应一手来源，也没有把“Google Play 分发生态规则”和“Android 平台调度机制”分层。

- **建议**：补 Android vitals / Google Play 官方来源，并把该段明确标成 distribution policy，不要和平台调度行为混写。

- **类型**：数据缺失

- **位置**：L67-L71 + L107 + L203

- **问题**：多处把 GPU delegate 公开路径写成“OpenCL / OpenGL ES 为主”，但当前 cited `ai.google.dev/edge/litert/android/gpu` 页面并未给出稳定 backend 合约。

- **建议**：补能明确说明 backend 的一手资料；如果拿不到，降级成“具体 backend 取决于 delegate/runtime/driver 实现”。

- **类型**：数据缺失

- **位置**：L290-L300 参考基线数据表

- **问题**：Pixel 8 各阶段耗时标注为"基于公开 bootstat 输出和 AOSP 默认配置的估算值"，但未给出具体来源链接或 bootstat 输出样本。读者无法复现或验证这些数字。

- **建议**：补具体 Pixel 8 bootstat 输出截图或公开 Benchmark 来源，或把表头改为"分段比例示意（非实测值）"。

- **类型**：数据缺失

- **位置**：L79-L80 outline 扩展

- **问题**：大纲扩展提到 Phantom Process Killer 和 SDK Sandbox，但正文对 SDK Sandbox 的覆盖极轻。SDK Sandbox 是 Android 14 引入的重要进程隔离机制，影响广告 SDK 和第三方 SDK 的进程模型。

- **建议**：补 SDK Sandbox 对进程模型的影响（独立进程、内存隔离、与 phantom process killer 的交互）。

- **类型**：知识盲区

- **位置**：全局

- **问题**：章节 confidence 为 medium，未覆盖 binder fd leak 检测（`binder_stats`）、RPC 回调线程模型（`IBinder.DeathRecipient` 虽然提到但未展开 binder 死亡通知的调度路径）、以及 vendor binder domain 的差异。

- **建议**：P3 级别，不阻塞当前 review，可作为后续增强素材。

- **类型**：源码准确性

- **位置**：L189-L197（`nativePollOnce` / epoll 解释）

- **问题**：正文已正确说明主线程在 native 层通过 epoll 等待消息与 fd 事件，但当前证据只挂到 `MessageQueue` 官方 reference，缺少对应的 native 源码锚点，读者不容易继续向下追到 `android_os_MessageQueue.cpp` / `Looper.cpp`。

- **建议**：补一条 native 路径级来源，明确 Java `MessageQueue.next()` 到 native poll 的落点。

- **类型**：数据缺失

- **位置**：L463-L465（RenderThread 延迟分析）

- **问题**：章节已经给出“主线程 `syncAndDrawFrame` 对比 RenderThread `DrawFrame`”的诊断方法，但这里仍停在占位符，没有真实 Perfetto 截图或最小判读样例。

- **建议**：补一张 60Hz/120Hz 任一真实 trace 截图，标出 UI 线程同步等待段和 RenderThread 长帧段的对应关系。

- **类型**：数据缺失

- **位置**：L181-L183（VelocityTracker 微秒级耗时）

- **问题**：`addMovement()` 1-5μs、`computeCurrentVelocity()` 5-20μs 属于量化结论，但没有设备型号、采样频率、trace 方法或 benchmark 条件。

- **建议**：补充测试环境，或把数值改成“参考量级”，避免被误读成跨设备通用结论。

- **类型**：数据缺失

- **位置**：L372（`requestDisallowInterceptTouchEvent(true)` 深层级开销）

- **问题**：正文提醒了深层 Parent 链递归的成本，但“20+ 层会有不可忽视开销”还缺少 method trace / systrace 量化支撑。

- **建议**：补一个深层嵌套样例或 trace 截图，说明开销出现在哪段调用链上。

- **类型**：数据缺失

- **位置**：L199-L215 / L287-L295（Doze 观测路径与 JobScheduler pending reason API）

- **问题**：观测顺序和 API 口径已经正确，但缺少一个最小可复现样例，读者还看不到 `dumpsys jobscheduler` 字段、`PendingJobReasonsInfo` 返回值和 pre-36 fallback 的并排对照。

- **建议**：补一个 API 36+ 代码片段和一段 `dumpsys jobscheduler` 真实输出，顺带标清旧版本仍需走 shell/bugreport 的回退路径。

- **类型**：数据缺失

- **位置**：L257-L271

- **问题**：Perfetto 观察部分仍停留在 `[图：...]` 和 `[待验证]` 占位，缺少最小可复现的 trace config，以及 legacy / predictive back 的对照样例。

- **建议**：补一套最小抓取配置（至少说明 input / wm / surfaceflinger 相关数据源），并给出一组能看到 cancel、back progress 或目标层预览时间关系的真实 trace 判读样例。

- **类型**：数据缺失

- **位置**：L476-L495

- **问题**：MAGT 案例给出了 FPS、功耗和续航提升数字，但缺少测试时长、环境温度、分辨率/帧率档位与 baseline 条件，当前只能当厂商案例引用，不能直接支撑通用结论。

- **建议**：补厂商原始链接或把这些数字降格为 vendor case study，并显式列出 workload、环境温度、测试时长和对照组。

- **类型**：版本差异

- **位置**：frontmatter L7

- **问题**：`applicable_versions` 写到了 Android 17 / API 37，但正文和 `last_verified_against` 只核到 android-16.0.0_r1，版本边界比证据链多了一代。

- **建议**：要么把适用版本收窄到 Android 16 / API 36，要么补齐 Android 17 上 SharedPreferences / DataStore 行为变化与官方锚点后再放开范围。

- **类型**：原理边界

- **位置**：L279-L300

- **问题**：“DataStore 的所有 I/O 都必须在 `Dispatchers.IO` 上执行”表述过满。`preferencesDataStore` 委托默认用 IO scope，但 `DataStoreFactory` / `MultiProcessDataStoreFactory` 可以传自定义 scope；真正要强调的是单写者模型和不要在主线程做 blocking read / `first()`。

- **建议**：改成“默认委托使用 IO scope，手工创建时应提供合适的后台 scope”，并补一句调用方若在主线程做阻塞式读取，仍可能把等待带回主线程。

- **类型**：数据缺失

- **位置**：L133 Overlay plane 数量说明

- **问题**：`4-16` 个 Overlay plane 的数字没有 SoC、Display Engine、Android 版本或 dumpsys 样本上下文，容易被读者误读成跨平台通用基线。

- **建议**：补一组设备级样本，或者降级为“Overlay plane 数量强依赖 SoC / DPU 实现，需以 dumpsys SurfaceFlinger 和厂商文档为准”。

- **类型**：交叉引用

- **位置**：frontmatter `related_chapters`

- **问题**：正文已经把 backpressure、release fence、BufferQueue 周转写成主解释链，但 `related_chapters` 仍缺 `2.13`（BufferQueue）和 `2.16`（Sync Fence）。

- **建议**：在 frontmatter 中补上 `2.13`、`2.16`，让章节跳转和正文依赖保持一致。

- **类型**：数据缺失

- **位置**：L70 “Vulkan 的 CPU 开销比 GLES 低 20-40%”

- **问题**：量化结论没有设备型号、驱动版本、渲染负载、采样方法或基准场景说明，读者无法判断该数字适用于 draw-call 受限场景、driver-bound 场景，还是某篇特定 benchmark。

- **建议**：补充至少一组可复查的 benchmark 条件，或者把表述降级为“在 driver-bound 的移动图形负载里通常可见更低 CPU 开销”。

- **类型**：数据缺失

- **位置**：L220-L247 在 Perfetto 中的表现

- **问题**：`%eyedropper%` / `%cross_device%` 这类 SQL 关键字和 `<5ms`、`<50ms` 延迟数据没有真实 trace、数据源或官方 trace marker 依据，当前属于伪造的观测口径。

- **建议**：重写为真实可抓取的证据链，例如 ActivityResult 启动到返回的时序、SystemUI 进程的渲染 slice，以及是否存在公开 trace marker 的核验结果。

- **类型**：结构层级

- **位置**：「本章内容」列表 — BLASTBufferQueue 条目

- **问题**：BLAST 深入仅作为 Android View 标准链路的括号补充，层级偏低。BLAST 架构改动极大，涉及 SurfaceControl 事务处理和客户端合并提交，作为括号补充容易被轻视。

- **建议**：将 BLASTBufferQueue 独立为一个小节，如「BLASTBufferQueue 与现代事务同步链路」。

- **来源**：Gemini 外部 review (2026-04-20-11-18.0-external-review.md)

- **类型**：交叉引用

- **位置**：「本章内容」和「阅读建议」

- **问题**：阅读建议中的数字引用（如 18.20、18.7）在无序列表中无法被定位，索引标号与列表结构不对应。

- **建议**：为「本章内容」列表添加明确的 18.X 序号结构，确保上下文引用精准。

- **来源**：Gemini 外部 review (2026-04-20-11-18.0-external-review.md)

- **类型**：交叉引用

- **位置**：L81 / L182 / L197 / L229 / L385

- **问题**：跨章节链接使用同目录相对路径，指向 `04-choreographer.md`、`08-overdraw.md`、`07-hardware-layer.md`、`04-binder.md` 等当前目录下不存在的文件，读者无法跳转到 2.x/1.4 章节。

- **建议**：统一改为实际相对路径，例如 `../../part1-fundamentals/ch02-rendering/04-choreographer.md`、`../../part1-fundamentals/ch02-rendering/08-overdraw.md`、`../../part1-fundamentals/ch02-rendering/07-hardware-layer.md`、`../../part1-fundamentals/ch01-architecture/04-binder.md`，并复核引用标题与目标章节一致。

- **类型**：数据缺失

- **位置**：L255（AVIF 小节）

- **问题**：用“AVIF 同等画质约小 50%”作为结论时，没有给出测试图片集、质量目标和设备条件；随后又用 HEIC 降本案例为 AVIF 背书，证据对象并不一致。

- **建议**：补一组 AVIF vs JPEG 的同条件样本数据，或把这段降格为趋势性描述，并把 HEIC 案例单独标成“相邻格式实践”

- **类型**：数据缺失

- **位置**：L458（检查清单第 8 条）

- **问题**：“WebP 有损替代 JPEG 同等画质下体积小 25-35%”缺少来源、编码参数和图片语料边界。

- **建议**：补充 encoder、quality、样本类型与测试条件；如果没有统一基准，把结论改成“通常更小，但幅度依内容而异”

- **类型**：交叉引用

- **位置**：L470 / related_chapters

- **问题**：正文把“渲染机制版本演进”指到 §2.10，但 §2.10 实际是《GPU 渲染深入》，版本演进章节是 §2.9。

- **建议**：把正文与 frontmatter 的相关章节统一改成 §2.9，并核对引用标题

- **类型**：交叉引用

- **位置**：L472 / related_chapters

- **问题**：正文把“功耗管理”指到 §8.1，但 §8.1 实际是《响应速度原理》，不是功耗章节。

- **建议**：改到真正的功耗章节（如 §11.1 Android 功耗模型或更贴切的功耗分析章节），并同步 frontmatter

- **类型**：交叉引用

- **位置**：L154

- **问题**：文中链接到 `../ch08-responsiveness/03-startup-optimization.md`，仓库内不存在该文件；实际章节文件为 `03-launch-optimization.md`。

- **建议**：修正为真实文件路径，并确认标题仍对应 §8.3《启动优化策略》


## [Task9 Deep Review] 11.2 App 耗电优化 — 2026-04-20
- **类型**：数据缺失
- **位置**：L402-L404
- **问题**：`44.1kHz` 与 `96kHz` 的对比被直接写成通用结论，但没有说明输出链路、codec、设备能力和业务场景边界，容易把普通媒体播放和专业音频采集/回放混成一类。
- **建议**：降格为“多数普通播放场景通常不需要更高采样率”，并补一组设备 / codec / latency 前提或实测例子。

## [Task9 Deep Review] 11.3 系统级功耗优化 — 2026-04-20
- **类型**：数据缺失
- **位置**：L340
- **问题**：`PowerGenie` 小节把“通过 ADB 卸载是唯一绕过方式”写成确定事实，缺少可追溯来源，也把厂商设置策略和系统包改动混成了单一路径。
- **建议**：改成 `dontkillmyapp` / 机型经验口径，明确这是 OEM 行为案例而不是 Android 官方机制，不要写“唯一”。


## [Task9 Deep Review] 10.2 内存泄漏 — 2026-04-20
- **类型**：原理断裂
- **位置**：L178-L180
- **问题**：把 Listener / Callback 的解绑时机统一建议为 `onStop()` 过于绝对。真实工程里应按监听对象绑定到“可见性”“View 生命周期”还是“宿主销毁”来决定使用 `onPause()`、`onStop()`、`onDestroyView()` 还是 `onDestroy()`。
- **建议**：把这里改成生命周期分层建议，至少区分 Activity 可见性级监听器与 Fragment View 级监听器。

- **类型**：数据缺失
- **位置**：L259-L263
- **问题**：把 `dumpsys meminfo` 里的 `Activities` / `Views` 数量直接当成泄漏判据会误报。返回栈、多窗口、透明 Activity、预加载页面等场景都可能让计数大于 1。
- **建议**：改成“可疑信号”表述，并要求结合 LeakCanary、Heap Dump 或固定复现场景交叉验证。

- **类型**：版本差异 / 数据缺失
- **位置**：L281-L288
- **问题**：版本演进里把“Android 16：Perfetto 增强 heapprofd 的 Java 堆采样能力”写成事实条目，但正文只给出 `[待验证]`，缺少 Perfetto 文档或 AOSP 依据。
- **建议**：在拿到一手来源前，把这条移出正式版本演进，改成 research gap 或待核实备注。


## [Task9 Deep Review] 4.4 Low Memory Killer — 2026-04-20
- **类型**：数据缺失
- **位置**：L382-L390
- **问题**：16KB Page Size 小节引用“冷启动速度提升 20%-40%”，但没有给出测试设备、工作负载和与 LMK 行为之间的因果边界。
- **建议**：把数值改成带条件的官方结论，并补一句“这是平台级冷启动收益，不直接等价于 LMK 杀进程频率下降”。

## [Task9 Deep Review] 8.7 Baseline Profiles 与编译优化实践 — 2026-04-20
- **类型**：版本差异
- **位置**：L230
- **问题**：Startup Profile DEX layout 优化的描述缺少 R8 `isMinifyEnabled=true` 前提，也没有说明 Startup Profiles 不能由库贡献。
- **建议**：补上“AGP 8.3 默认开启 dex layout optimization 仍以 R8 打开为前提”，并补一行库 profile 与 startup profile 的边界。

## [Task9 Deep Review] 9.6 Notification 性能与 ANR — 2026-04-20
- **类型**：交叉引用
- **位置**：L453
- **问题**：Perfetto SQL 分析指向 §13.7，但书内 SQL 实战手册是 §13.10。
- **建议**：改成 §13.10，或同时标出 §13.7（高级用法）与 §13.10（SQL 手册）的分工。

## [Task9 Deep Review] 9.6 Notification 性能与 ANR — 2026-04-20
- **类型**：版本差异
- **位置**：L459
- **问题**：版本演进表把包级通知速率限制放在 Android 12 项里，容易误读为 Android 12 新增；相同常量和 `mUsageStats.getAppEnqueueRate()` 路径在 android-10.0.0_r1 已存在。
- **建议**：改成“Android 10+ 延续到 Android 16 的限制”，或把它挪出版本增量表，改成跨版本通用边界说明。

## [Task9 Deep Review] 8.10 ProfilingManager 系统触发式性能追踪 — 2026-04-20
- **类型**：版本差异
- **位置**：L73-L76 / L254-L259
- **问题**：章节列出了 extension 36.1 的 trigger 常量，但没有补 runtime gating 入口。读者容易把 36.1 扩展能力误读成“只要 API 36 就稳定可用”，从而漏掉 Extension SDK 检查。
- **建议**：补一句“36.1 trigger 需要按 extension version 判定，不应只看 API level”，并给出运行时 gating 提示。

## [Task9 Deep Review] 13.6 线程 CPU 状态分析 — 2026-04-20
- **类型**：原理边界/数据缺失
- **位置**：L252-L260
- **问题**：唤醒关系段把 `sched_waking` 近似写成“资源释放后 T1 直接唤醒 T2”，且只笼统提示 `wakeup from` 可能不准，没有交代“wakeup 只代表线程变为 runnable，不代表立刻拿到 CPU”这条边界。
- **建议**：补一句“`sched_waking` 记录的是 runnable 时刻与 waker 线程，后续仍可能有 runqueue 排队、迁核和优先级竞争”，避免把 wake source 当成完整依赖图。

## [Task9 Deep Review] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 2026-04-20
- **类型**：数据缺失
- **位置**：L399-L400
- **问题**：`单次执行 <100ns` 与“100 万次调用≈100ms/s”这组数字没有测试条件、内核版本、probe 类型和设备环境，当前写法像通用事实。
- **建议**：如果拿不出可复现 benchmark，就把数字降格为经验量级，并标清“不同 helper / map 访问 / ringbuf 写入路径开销差异很大”。

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-21
- **类型**：源码准确性 / 工具边界
- **位置**：L260-L265 / L365-L370
- **问题**：Perfetto SQL 示例直接查询 `track_event` 并匹配 `refreshRate` / `FrameTimeline` 名称，但这不是稳定的标准分析入口。常规 trace 往往查不到这组事件名，读者会把查询无结果误判成抓 trace 失败。
- **建议**：改成基于 FrameTimeline 标准表 / 轨道和 display refresh-rate 轨道的观察路径，注明对应 data source 与可运行 SQL。

## [Task9 Deep Review] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-04-21
- **类型**：版本差异
- **位置**：frontmatter `applicable_versions`
- **问题**：frontmatter 把适用范围写到 Android 17，但正文与验证锚点实际停在 Android 16 / Android 15 图形说明页，没有给出 Android 17 的新增图形栈变化或验证来源。
- **建议**：如果暂无 Android 17 的公开差异结论，把范围收窄到 Android 16；如果要继续保留 Android 17，需补一手 release note / AOSP 锚点。

## [Task9 Deep Review] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-04-21
- **类型**：数据缺失
- **位置**：L362
- **问题**：AGI “2026 H1 / H2” 路线图仍是 `[待验证]`，正文没有官方 roadmap 或 release note 链接支撑。
- **建议**：删除未来 roadmap 数字，或改成已发布版本能力与公开 release note。

## [Task9 Deep Review] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-04-21
- **类型**：数据缺失 / 工具边界
- **位置**：L289-L305
- **问题**：`android_dmabuf_allocs` 与 `dmabuf_heap/dma_heap_stat` 的 Perfetto 路径没有写清前置条件。若 trace 没录到相应 ftrace 事件或缺少 binder-to-gralloc 上下文，读者会拿不到可归因的分配结果。
- **建议**：在示例前补充 trace config 前提，区分“能看到 dmabuf 事件”和“能把分配归因回 Gralloc / 调用线程”这两个层次。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-04-21
- **类型**：数据缺失
- **位置**：L187-L187 / L235-L235
- **问题**：正文只写“受限时长”与 `Mode.GAME_LOADING` boost，但没把 AOSP `GameManagerService` 里的 `LOADING_BOOST_MAX_DURATION = 5 * 1000` 默认上限写出来。长加载场景下，读者不容易判断 boost 何时会自动退场。
- **建议**：补一句 AOSP 默认上限 5 秒，并注明超出 5 秒的加载流程需要分段上报 loading，或接受 boost 超时后回落。



## [External Review] 14.8 GPU 图形调试与分析工具 — 2026-04-21
- **类型**：数据支撑
- **位置**：案例 1：UI 渲染中的 GPU 带宽瓶颈
- **问题**：使用"待验证：具体优化数据来自类似场景的经验，非本案例实测"的编造数据降低可信度
- **建议**：使用真实开源项目（如 Plaid 或 Now in Android）的真实 trace 截图和带宽降低比例
- **来源**：Gemini 外部 review

## [External Review] 14.9 Android Camera 性能与 Perfetto 分析 — 2026-04-21
- **类型**：数据缺失
- **位置**：HAL3 管线延迟段落（待验证标记处）
- **问题**：缺少不同 SoC 平台（高通/联发科/三星）上 HAL3 管线延迟的典型值
- **建议**：补充参考值——ZSL 开启时约 2-3 帧（66-100ms），关闭 ZSL 更长，ISP 处理约 10-20ms
- **来源**：Gemini 外部 review

## [External Review] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 2026-04-21
- **类型**：原理链完整性
- **位置**：UprobeStats 工作原理段落
- **问题**：未提及 RingBuf 在高频触发方法时可能丢失事件以保护内核性能
- **建议**：补充说明 UprobeStats 中 eBPF 程序通过 RingBuf 送数据给用户态 Collector 时的高频 drop 风险
- **来源**：Gemini 外部 review

## [External Review] 14.10 eBPF/BPF 在 Android 性能分析中的应用 — 2026-04-21
- **类型**：事实修正
- **位置**：bpftrace 可用性描述
- **问题**：断言 bpftrace 不是 Android 标准工具链一部分，但 AOSP external/bpftrace 自 Android 12/13 已引入
- **建议**：修正表述，说明 AOSP external/bpftrace 项目存在且 userdebug 环境下可编译使用
- **来源**：Gemini 外部 review


## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-04-21
- **类型**：源码准确性
- **位置**：L341-L351
- **问题**：两处排查结论写得过满。其一，“View 层级超过 10 层就会指数增长、每多一层 measure 次数就可能翻倍”更接近特定布局算法的最坏情况，不适合作为通用规律。其二，`adb shell dumpsys gfxinfo <package>` 被写成会直接列出“每个 View 的 DisplayList 大小和 command count”，这和常见 gfxinfo / framestats 输出不一致，读者按文操作很难得到文中描述的视图级命令统计。
- **建议**：把布局复杂度改成条件化描述，限定到特定 ViewGroup/重复测量场景；把 DisplayList 排查工具改成 Layout Inspector / Perfetto / gfxinfo framestats 的组合，并说明各自能看到什么。

## [Task9 Deep Review] 3.2 触摸响应的性能分析 — 2026-04-21
- **类型**：数据缺失
- **位置**：L76，L164-L173，L285
- **问题**：30-80ms 总时延、各阶段典型耗时表，以及“120Hz 应该每 8.3ms 一个 Slice”都以通用基线口径出现，但没有绑定设备、触控控制器、刷新率、trace 配置和 batching 状态。对不同面板 / SoC / trace 采样配置，这些数字只能当经验区间，不能直接当判定阈值。
- **建议**：给一组可复现样例，补充设备刷新率、触控采样率、trace categories 和 batching / unbuffered 状态；正文把这些数字改写为“经验区间”而不是固定基线。

## [Task9 Deep Review] 8.8 Android 多媒体管线性能 — 2026-04-21
- **类型**：数据缺失
- **位置**：L255-L256，L445-L449
- **问题**：`Normal Mixer Thread` “每约 20ms 执行一次混合”和“端到端 40-80ms”被写成跨版本、跨设备稳定数值，但实际还受 HAL period size、fast path 命中、buffer depth 和厂商实现影响。当前写法容易让读者把经验值误读为固定平台常量。
- **建议**：保留 20ms 作为常见设计量级或 AOSP 经验值，同时补充“不同设备需结合 HAL/trace 实测”的边界说明；如果要保留 40-80ms 区间，最好补一组设备条件。


## [Task6 Review] 2.10 GPU 渲染深入 — 2026-04-21
- **类型**：需确认
- **位置**：实战案例「社交应用图片滚动中的 GPU 瓶颈定位」→ 第一步「降低渲染分辨率」
- **问题**：文中「GPU 性能瓶颈分析」一节明确写了"降低渲染分辨率判断瓶颈类型的方法不适用于标准 Android UI 渲染"，但实战案例的第一步就是"将渲染分辨率降到 720p 重新测试"。案例描述的是社交 App 图片滚动（标准 Android UI），方法论自相矛盾。读者会困惑：到底能不能用降分辨率的方法？
- **建议**：二选一修复——（1）案例中改为使用 AGI GPU 性能计数器确认 fillrate bound（与前面的方法论一致）；（2）在前面的注意事项中补充说明某些设备可通过开发者选项或 SurfaceView 控制渲染分辨率。推荐方案 (1)。
- **review 日志**：logs/review/2026-04-21-03-review.md

## [Task6 Review] 4.4 Low Memory Killer — 2026-04-21
- **类型**：需确认
- **位置**：扩展四「Android 12+ CachedAppOptimizer 与 cgroup v2 Freezer」
- **问题**：本节「扩展四」包含较详细的 CachedAppOptimizer 源码级补充（freezeBinderThreads、解冻原因码、Perfetto 区分方法等），但 1.3 节「进程模型与生命周期管理」中已有完整的 CachedAppOptimizer/Freezer 机制章节（含架构设计、实现机制、Perfetto 表现、版本演进），两处内容高度重叠。读者在两处看到类似内容会产生困惑，维护时也容易版本不一致。
- **建议**：本节（4.4）的 CachedAppOptimizer 补充应缩减为"此处仅说明 Freezer 与 LMK kill 的区别，详细机制见 1.3 节"的交叉引用，避免重复展开。具体执行由 task2b 完成。
- **review 日志**：logs/review/2026-04-21-03-review.md


## [Task9 Deep Review] 12.3 网络性能深入：连接池、TLS 与传输优化 — 2026-04-21
- **类型**：版本差异
- **位置**：L235-L256
- **问题**：DNS Resolver 模块被写成“从 Android 11 开始作为独立 Mainline 模块”，但公开口径更接近“Android 10 引入、Android 11 起强制模块化”；DoH3 rollout 也不只覆盖 Android 11+，还包括部分 Android 10 设备。
- **建议**：把版本线改成“Android 10 引入 Mainline DNS Resolver，Android 11 起强制；2022 年 DoH3 通过 Google Play system update rollout 到 Android 11-13 与部分 Android 10 设备”。

## [Task9 Deep Review] 13.3 Perfetto View 解读 — 2026-04-21
- **类型**：版本差异
- **位置**：L356 / L459
- **问题**：暗色主题被写成 “Perfetto v52 起成为一等公民功能（不再是实验性的）”，并给出命令面板切换路径。Perfetto release notes 口径更接近 v52/v53 阶段仍是 Settings 里的 `[Experimental] UI Theme`。
- **建议**：改成“v52 左右引入暗色主题，早期 release 仍以实验性设置项出现；具体入口以当前 UI 版本为准”，不要把切换入口写死成命令面板。

## [Task9 Deep Review] 13.3 Perfetto View 解读 — 2026-04-21
- **类型**：源码准确性
- **位置**：L460
- **问题**：`slice_self_dur()` 被写成可直接调用的函数。当前公开口径更常见的是 `slice_self_dur` 表 / `slices.self_dur` 标准库模块，不宜写成顶层函数名。
- **建议**：改成“Perfetto v52 引入 `slice_self_dur` 相关标准库能力”，并给出可运行示例，如 `INCLUDE PERFETTO MODULE slices.self_dur; ... JOIN slice_self_dur ...`。
