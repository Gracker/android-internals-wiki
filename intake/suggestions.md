## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：版本差异
- **位置**：Android 12 InputFlinger 重构描述
- **问题**：Android 12 的 InputFlinger 重构描述过于简化，实际是代码抽取到独立服务但仍运行在同一进程内，而非真正的独立服务
- **建议**：修正描述，明确说明代码组织变化和运行时环境

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：版本差异
- **位置**：版本演进表
- **问题**：缺少 Android 15 Predictive Back 手势对 Input 分发路径的重大影响
- **建议**：补充 Android 15 版本变更，说明预测性返回手势的实现机制

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：数据缺失
- **位置**：ANR 超时机制部分
- **问题**：缺少实际 ANR Trace 分析案例，无法展示 wq 堆积到 ANR 触发的完整过程
- **建议**：添加一个具体的 Input ANR Trace 分析案例，包括 wq 堆积、ANR 触发、系统响应的完整时序

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-15
- **类型**：数据缺失
- **位置**：性能分析部分
- **问题**：缺少不同场景下的 Input 处理耗时基准数据
- **建议**：补充正常点击 vs 复杂手势处理的耗时对比数据，提供量化参考
## [Task6 Review] 16.5 Android 17 (API 37) 性能行为变更与适配方法 — 2026-04-15
- **类型**：回炉重修（技术细节验证）
- **位置**：全文多处关键技术点
- **问题**：
  1. ProfilingManager 触发器常量名需验证
  2. DeliQueue 性能改善需补充 Trace 截图
  3. 16KB 页面断言需提供具体案例
- **建议**：
  1. 检查 AOSP 源码中 ProfilingManager 触发器常量
  2. 补充真实的 Perfetto Trace 片段
  3. 提供具体的原生库名称和 AOSP 链接
- **review 日志**：logs/review/2026-04-15-17-review.md



## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：数据缺失
- **位置**："120Hz 的屏幕功耗通常比 60Hz 高 20-40%"（扩展：120Hz 场景功耗权衡）
- **问题**：功耗差异数值缺少可追溯的来源，且未说明适用于哪种面板技术
- **建议**：标注为近似参考值，注明"具体功耗差异因面板技术和设备而异"

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：数据缺失
- **位置**："触摸停止后一段时间（通常 2-3 秒）"（Touch Boost 描述）
- **问题**：Touch Boost 超时是 OEM 可配置的，AOSP 默认值可能与"2-3 秒"不符
- **建议**：改为"OEM 可配置的触摸提升超时"或标注为近似值

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：数据缺失
- **位置**："Janky frames 比例超过 5% 时用户能明显感知到卡顿"
- **问题**：缺少来源
- **建议**：标注来源或改为更保守的表述

## [Task9 Deep Review] 2.2 帧率与刷新率 — 2026-04-15
- **类型**：源码准确性
- **位置**：Perfetto SQL 查询刷新率变化事件
- **问题**：track_event 表名和 refreshRate 事件名可能与当前 Perfetto 版本不匹配
- **建议**：验证并更新 SQL 查询，或使用 Perfetto 的 display_refresh_rate track


## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：数据缺失
- **位置**：全章节
- **问题**：作为工具使用章节，没有一处真实的 dumpsys 输出样例。读者无法对照自己的输出判断是否正常，也无法理解关键字段在实际输出中的位置和格式
- **建议**：每个核心子命令（activity、meminfo、gfxinfo、window、batterystats、SurfaceFlinger）至少添加一个精简的真实输出片段（10-20 行），标注关键字段

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：源码准确性
- **位置**：framestats 逐帧时间线说明
- **问题**：列名列表不完整，缺少 Flags、OldestInputEvent、NewestInputEvent、DequeueBufferDuration、QueueBufferDuration、GpuCompleted 等列。这些列在实战分析中都有用途（Flags 区分正常帧和异常帧，DequeueBufferDuration 反映 BufferQueue 等待时间）
- **建议**：补全列名列表，或至少标注"此处列出最关键的列，完整列表参见 AOSP Choreographer.java"

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：版本差异
- **位置**：batterystats --enable full-wake-history
- **问题**：该参数在 Android 13+ 可能已不工作或行为变更，章节未提及版本限制
- **建议**：标注该参数适用的 Android 版本范围，Android 13+ 推荐替代方案

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：版本差异
- **位置**：batterystats 功耗分析工作流
- **问题**：导出 bugreport 命令只提到 adb bugreport > bugreport.zip，未提及 Android 12+ 推荐使用 adb bugreportz（生成标准 zip 文件，速度更快）
- **建议**：补充 bugreportz 的用法说明和版本差异

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：知识盲区
- **位置**：进阶用法
- **问题**：未提及 dumpsys --proto 输出格式（protobuf），该格式在自动化性能测试 CI/CD 中广泛使用
- **建议**：在进阶用法或实战部分补充 --proto 的用法和典型场景（如自动解析 meminfo 数据入库）

## [Task9 Deep Review] 14.4 dumpsys 系列命令 — 2026-04-15
- **类型**：交叉引用
- **位置**：gfxinfo 部分 JankStats 库提及
- **问题**：提到 JankStats 库（AndroidX）但未交叉引用 7.1 节（卡顿定义）或 7.5 节（优化策略），读者找不到后续阅读入口
- **建议**：添加"详见 §7.1 卡顿的定义与分类"和"§7.5 优化策略中 JankStats 的集成方法"

## [Task9 Deep Review] 6.2 文件系统 — 2026-04-15

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


## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-15

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

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15
- **类型**：事实错误
- **位置**：L293「Android 16 进一步强化了这一方向」
- **问题**：Baseline Profiles、JankStats、Macrobenchmark 均为 2022 年推出的 Jetpack 库，归入 Android 16 是事实错误
- **建议**：改为按工具演进时间线描述，明确各工具首次引入时间和 Android 16 具体新增内容

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15 #2
- **类型**：数据缺失
- **位置**：L164「冷启动时间不超过 1.5 秒」性能预算示例
- **问题**：缺少设备基线、App 类型上下文，读者无法判断预算是否合理
- **建议**：补充「在 2024 年中端设备（如 Snapdragon 7 Gen 1）上，社交类 App 的冷启动中位数约 1.2-1.8 秒」等参照数据

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15 #3
- **类型**：数据缺失
- **位置**：L265「5-10% 的基础设施成本下降」
- **问题**：数据来源准确（Brendan Gregg 2025），但直接套用到 Android App 性能场景缺少桥接
- **建议**：补充说明这是云基础设施成本指标，Android App 性能场景的度量维度（启动时间、帧率、ANR 率）与之不同，改为引用 Android 领域的优化 ROI 数据或弱化具体数字

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15 #4
- **类型**：源码准确性
- **位置**：L124 Macrobenchmark CI 使用描述
- **问题**：「可以在 CI 环境中自动测量」缺少关键前提：需要连接 Android 设备或模拟器
- **建议**：补充「在配置了 Android 模拟器或真机的 CI 环境中」作为前提条件

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15 #5
- **类型**：源码准确性
- **位置**：L56「BlastBufferQueue 替代 BufferQueue」
- **问题**：「替代」过于简化，BlastBufferQueue 是 BufferQueue 的包装层，底层机制仍存在
- **建议**：改为「引入 BlastBufferQueue 改变了 App 端与 BufferQueue 的交互模式（blast mode）」

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15 #6
- **类型**：数据缺失
- **位置**：Amazon/Google 性能数据引用
- **问题**：均为 Web 场景数据，用于佐证 Android App 性能优化必要性时缺少推理桥接
- **建议**：补充一句说明移动端场景有类似甚至更严格的约束（网络延迟、设备性能差异大、用户耐心更低）

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15 #7
- **类型**：交叉引用
- **位置**：全文多处章级引用
- **问题**：「第 4 章和第 10 章」「第 2 章」等均为章级引用，精度不够
- **建议**：改为节级引用如「§4.1 和 §10.1」「§2.1 和 §2.6」

## [Task9 Deep Review] 15.1 性能优化的术、道、器 — 2026-04-15 #8
- **类型**：知识盲区
- **位置**：数据驱动方法论
- **问题**：缺少统计严谨性讨论（方差、置信区间、最小运行次数）
- **建议**：补充一段讨论性能测量的统计方法，或引用 Android 官方 Macrobenchmark 文档中关于多次运行取中位数的建议

## [Task9 Deep Review] 8.3 启动优化策略 — 2026-04-16

### [P1] 首帧定义缺失：TTID vs TTFD
- **类型**：原理断裂 + 知识盲区
- **位置**：全文多处使用"首帧"，以及"效果量化"小节
- **问题**：全文未区分 TTID（Time to Initial Display，am start -W 的 TotalTime）和 TTFD（Time to Full Display，需要 reportFullyDrawn()）。不同定义影响优化策略方向——TTID 侧重减少 Activity 创建到第一帧的路径耗时，TTFD 侧重减少数据加载和内容就绪的耗时。
- **建议**：在"为什么要了解启动优化策略"小节后增加一段定义 TTID/TTFD，说明本节同时覆盖两者但侧重 TTID；在 Baseline Profile 效果量化部分区分展示两个指标；在总结部分提及 `reportFullyDrawn()` API 的使用。

### [P1] BaselineProfileRule API 版本未标注
- **类型**：源码准确性
- **位置**：Baseline Profile 制作 → 编写生成测试用例
- **问题**：`includeInStartupProfile = true` 参数在早期版本的 `benchmark-macro-junit4` 中不存在（该参数在 1.2.0+ 引入）。读者使用旧版本库会导致编译错误。
- **建议**：在代码示例旁标注最低依赖版本，或在 `build.gradle` 依赖声明后加注释说明版本要求。

### [P2] installSplashScreen() 调用时机说明不精确
- **类型**：源码准确性
- **位置**：SplashScreen API 核心使用小节
- **问题**：正文说"必须在 setContentView() 之前调用"，但 `installSplashScreen()` 实际要求在 `super.onCreate()` 之前调用。代码示例顺序正确，但文字说明可能导致读者遗漏。
- **建议**：修正为"installSplashScreen() 必须在 super.onCreate() 之前调用"。

### [P2] DAG 到自研框架的实现路径跳跃
- **类型**：原理断裂
- **位置**：多线程并行初始化框架 → DAG 模型与拓扑排序 → 自研框架
- **问题**：DAG 概念解释清楚后，直接跳到 App Startup 的 Initializer 接口，然后自研框架列出设计要点但没有展示"如何从 DAG 构建可执行调度计划"的实现路径。
- **建议**：在自研框架部分补充一段简要说明拓扑排序的实现思路（如 Kahn 算法或 DFS），或引用一个开源启动框架（如 Alibaba Alpha）作为实现参考。

### [P2] "某内容类应用"案例数据不透明
- **类型**：数据缺失
- **位置**：延迟初始化策略 → 懒加载小节
- **问题**："将冷启动耗时从 2800ms 降到了 1800ms"来源于微信公众号文章，具体条件（设备、Android 版本、SDK 组成）不透明。
- **建议**：标注为"行业公开案例，来自 XX 文章"，或改为更通用的表述"实践中，通过合理的任务分类通常可减少 30-50% 的 Application 初始化耗时"。

### [P2] Baseline Profile 20-40% 提升无具体引用
- **类型**：数据缺失
- **位置**：效果量化小节
- **问题**：归因于"Google 官方数据"但未给出具体来源（I/O 演讲？文档？case study？）。
- **建议**：引用具体来源，如 "根据 Google I/O 2022 演讲数据，XX 应用通过 Baseline Profile 实现了 XX% 的启动速度提升"。

### [P2] AsyncLayoutInflater 收益 50-200ms 无来源
- **类型**：数据缺失
- **位置**：布局优化 → AsyncLayoutInflater 小节
- **问题**："收益通常在 50-200ms 之间"为具体量化断言但无 benchmark 或引用支撑。
- **建议**：补充来源，或改为"根据布局复杂度，收益通常在数十到数百毫秒级别"并标注为经验估算。

### [P2] 8.8 ProfilingManager 交叉引用缺失
- **类型**：交叉引用
- **位置**：启动速度线上监控 → 在 Perfetto 中定位启动耗时瓶颈；以及 frontmatter related_chapters
- **问题**：章节提到 Method Trace 追加分析但未交叉引用 8.8 节（ProfilingManager 系统触发式性能追踪）。frontmatter related_chapters 也未包含 8.8。另外 ch08 目录中存在两个 08 前缀文件（08-media-pipeline.md 和 08-system-triggered-profiling.md），后者未出现在 SUMMARY.md 中，可能存在章节号冲突。
- **建议**：在 Method Trace 相关段落添加交叉引用 8.8；在 related_chapters 中添加 "8.8"；与高爷确认 08-system-triggered-profiling.md 的章节归属。

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-04-16

- **类型**：原理描述不准确
- **位置**：「页面跳转优化策略」FragmentFactory 代码示例
- **问题**：PreloadFragmentFactory.instantiate() 中调用 fetchPreloadData() 是同步操作，如果涉及 IO 会阻塞主线程。代码示例没有说明该方法必须是非阻塞的。
- **建议**：在代码注释中明确标注 fetchPreloadData() 应从内存缓存读取，或改为在 Application.onCreate() 阶段预加载到静态变量中

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-04-16

- **类型**：原理描述不准确
- **位置**：「页面跳转优化策略」setReorderingAllowed(true) 说明
- **问题**：描述为「让系统并行处理多个 Fragment 操作」，实际 setReorderingAllowed(true) 的作用是允许 FragmentManager 重排操作顺序（如将 remove+add 优化为 replace），不是并行执行。
- **建议**：修正描述为「允许 FragmentManager 重新排列事务中的操作顺序，将多个操作合并优化（如 remove(A)+add(B) 合并为 replace），减少不必要的生命周期回调」

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-04-16

- **类型**：版本差异
- **位置**：版本演进段
- **问题**：1) ViewPager2 归入「Android 9.0」条目是误导，它是 AndroidX 库不与 OS 版本绑定。2) setMaxLifecycle() 在 Fragment 1.1.0 引入，非 1.2.0。
- **建议**：1) 将 ViewPager2 条目改为独立行「2019-02：ViewPager2 首个 alpha 发布（AndroidX），2019-11 稳定版 1.0.0」。2) 修正为「Fragment 1.1.0：引入 setMaxLifecycle()」

## [Task9 Deep Review] 8.4 其他响应速度场景 — 2026-04-16

- **类型**：交叉引用
- **位置**：点击响应段 RAIL 模型引用
- **问题**：RAIL 模型是 Chrome 团队的 Web 性能模型（web.dev/rail），但链接指向 developer.android.com/topic/performance/vitals（Android Vitals）。两个概念不应混为一谈。
- **建议**：分别引用——RAIL 模型引用 web.dev/rail，Android 点击响应阈值引用 Android Vitals 的冻帧/慢帧定义

## [Task9 Deep Review] 13.10 Perfetto SQL 性能分析实战手册 — 2026-04-16

- **类型**：原理断裂
- **位置**：Binder 分析节"Binder 事务按耗时排序"SQL
- **问题**：声称分析 client_dur/server_dur/dispatch_dur 三个维度，但 SQL 只查 slice 总 dur，无法区分。三个维度的描述和实际查询能力脱节。
- **建议**：要么通过 ftrace binder_transaction 事件关联提取三阶段耗时（需要启用对应 ftrace event），要么修改文字描述，明确当前 SQL 只能查总耗时。

## [Task9 Deep Review] 13.10 Perfetto SQL 性能分析实战手册 — 2026-04-16

- **类型**：原理断裂
- **位置**：「调度延迟：Runnable → Running 的时间」节
- **问题**：标题描述调度延迟（Runnable 到获得 CPU 的时间），但 SQL 只列出主线程的 sched 记录。完全没有计算调度延迟。
- **建议**：重写 SQL，计算逻辑：找到 end_state IN ('R','R+') 的 sched 条目，到同一 utid 下一条 sched.ts 的差值即为调度延迟。示例：SELECT (next_sched.ts - curr_sched.ts) AS latency_ns FROM sched curr_sched JOIN sched next_sched ON curr_sched.utid = next_sched.utid AND next_sched.ts > curr_sched.ts WHERE curr_sched.end_state IN ('R','R+') ...

## [Task9 Deep Review] 13.10 Perfetto SQL 性能分析实战手册 — 2026-04-16

- **类型**：事实错误
- **位置**：「线程 CPU 时间统计」SQL
- **问题**：CPU 利用率分母使用 MAX(ts+dur)-MIN(ts)，这是该线程首次调度到末次调度的跨度，不是 Trace 总时长。空闲时间被排除，结果偏高。
- **建议**：分母改为 (SELECT end_ts - start_ts FROM trace_bounds)

## [Task9 Deep Review] 13.10 Perfetto SQL 性能分析实战手册 — 2026-04-16

- **类型**：版本差异
- **位置**：全文各 SQL 查询
- **问题**：章节声明 applicable_versions Android 10-17，但未标注各查询的最低版本要求。Frame Timeline (Android 12+)、android.frames 模块 (Perfetto v38+)、android.monitor 模块、Java Heap counter track 名称等在不同版本有差异。
- **建议**：在每个主要查询模板旁添加版本标注。如：「Frame Timeline 查询需要 Android 12+ 且 Trace 配置包含 track_event」。

## [Task9 Deep Review] 13.10 Perfetto SQL 性能分析实战手册 — 2026-04-16

- **类型**：源码不精确
- **位置**：冷启动查询中 'ZygoteInit.xxx'
- **问题**：'ZygoteInit.xxx' 是占位符不是实际 slice 名称。AOSP 实际名称为 'ZygoteInit.main' 或 'ZygoteInit.native'。章节标注 [已验证] 但实际未验证。
- **建议**：改为具体名称 'ZygoteInit.main'，并标注该名称对应 Android 10+ 的 ART 实现。去掉 [已验证] 标记或改为 [待验证]。

## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-04-16

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

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-04-16

- **类型**：原理断裂
- **位置**：「Binder 跨层调用」小节
- **问题**：提及 Binder 线程池"内核唤醒空闲线程"但未解释线程池大小（默认 16 线程）和饱和行为。SystemServer 所有 Binder 线程忙时新请求排队，直接导致调用方阻塞——这是实际分析中常见但容易被忽略的瓶颈场景。
- **建议**：补充 Binder 线程池大小说明，增加一个"所有 Binder 线程忙导致 App 主线程阻塞"的 Trace 描述案例。

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-04-16

- **类型**：原理断裂
- **位置**：「Zygote：应用进程的孵化器」小节
- **问题**：描述了 fork 机制和 COW 但跳过了 fork 之后子进程如何从 native 进程进入 Java 世界的桥梁——`app_process` 二进制。读者无法理解从 fork 到 `ZygoteInit.main()` 之间发生了什么。
- **建议**：在 Zygote fork 段落后补充简短的 app_process 说明（1-2 句），或添加交叉引用到 1.2 系统启动全流程。

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-04-16

- **类型**：数据缺失
- **位置**：全文性能数据声明
- **问题**：Binder 延迟（10-100μs）、JNI 延迟（100-200ns / 1-5μs）、Zygote fork 时间（20-50ms）三项基础性能数据均标记 `[待验证]`。作为全书开篇章节，这些基线数据的可信度直接影响后续章节。
- **建议**：为每项数据至少提供一个具体来源（设备型号 + Android 版本 + 测量方法的引用），或将验证任务分配给下一个 research cycle。

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-04-16

- **类型**：交叉引用
- **位置**：全文
- **问题**：正文缺少对 1.2（系统启动全流程）的明确交叉引用。Zygote fork 和 SystemServer 启动流程与 1.2 高度相关，但读者只能通过 frontmatter 的 related_chapters 发现关联。
- **建议**：在 Zygote 和 SystemServer 段落后添加"详见 1.2 系统启动全流程"的交叉引用链接。

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-04-16

- **类型**：一致性
- **位置**：outline 扩展部分
- **问题**：outline 声明"与 iOS / HarmonyOS 分层架构的对比"为扩展内容，但正文完全未涉及。这属于 outline 与正文不一致。
- **建议**：如果不计划展开（合理选择），从 outline 扩展列表中移除该项；如果后续有素材，可补充简要对比表。
