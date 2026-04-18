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


## [Task9 Deep Review] 9.1 ANR 设计思想 — 2026-04-16

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

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-16
- **类型**：源码准确性
- **位置**：「在 Perfetto 中的表现」段 → RenderThread 的首次 DrawQL
- **问题**："DrawQL" 不是 AOSP 或 Perfetto 中的标准术语。RenderThread 的 Trace slice 名为 "DrawFrame"，子操作为 syncFrameData/computeOrdering/flush commands。
- **建议**：改为 "RenderThread 的首次 DrawFrame slice" 或描述具体的子操作名。

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-16
- **类型**：知识盲区（高）
- **位置**：全文
- **问题**：android:profileable 清单属性（Android 12+）完全未提及。此属性对基准测试准确性至关重要——未设置的 release 构建无法被完整追踪。
- **建议**：在 CI/CD 构建配置或 FAQ 中补充 profileable 属性说明

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-16
- **类型**：原理断裂
- **位置**：CompilationMode.Partial 讨论
- **问题**：BaselineProfileRule 完全未提及。缺少生成环节，原理链断裂。
- **建议**：补充 BaselineProfileRule 使用方法，或至少添加对 8.7 节的显式交叉引用

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-16
- **类型**：原理断裂
- **位置**：「在 Perfetto 中的表现」段
- **问题**：Macrobenchmark 如何捕获 Perfetto Trace 的机制未解释
- **建议**：补充说明 Macrobenchmark 通过 Perfetto SDK 配置 Trace 数据源

## [Task9 Deep Review] 14.6 自动化测试工具 — 2026-04-16
- **类型**：数据缺失
- **位置**：CompilationMode 节 + FAQ
- **问题**：Baseline Profile "30% 改善"无具体来源；"5-15% 波动"无数据支撑。全文无真实 benchmark 数值
- **建议**：补充数据来源链接，添加典型 benchmark 数值案例


## [Task6 Review] 9.3 ANR 分析方法 — 2026-04-16
- **类型**：内容深度建议
- **位置**：版本演进部分（"待验证"标注部分）
- **问题**：Android 13-15 的 ANR 分析机制变化描述为"以上基于公开 Release Notes 推断"，缺乏具体验证
- **建议**：确认版本差异是否真实影响 ANR 分析流程，如影响较大需补充具体案例；如无影响可简化描述
- **review 日志**：logs/review/2026-04-16-10-review.md


## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-16
- **类型**：源码准确性
- **位置**：ART GC 关键源码路径代码片段
- **问题**：CollectGarbageInternal() 代码是伪代码但标注为 AOSP 源码。实际 ART 不直接调用 collector->PausePhase()/ConcurrentPhase()，而是通过 collector->Run() 分阶段执行。且标注 @ android-15 但 frontmatter 声明 verified against android-14
- **建议**：替换为实际 AOSP 代码，或在代码注释中明确标注「简化示意，非实际 AOSP 代码」

## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-16
- **类型**：数据缺失
- **位置**：「STW 停顿的累积效应」段，「实测平均约 1.83ms」
- **问题**：GC STW 暂停数据缺少测量条件（设备型号、Android 版本、Heap 大小、GC 负载类型）
- **建议**：补充测量条件，或标注数据来源（如 Android 官方性能数据、某设备实测等）

## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-16
- **类型**：源码准确性
- **位置**：「Binder 线程池耗尽」段
- **问题**："Android 默认为每个进程分配最多 16 个 Binder 线程"无引用
- **建议**：补充引用 AOSP ProcessState.cpp 中 DEFAULT_MAX_BINDER_THREADS 定义

## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-16
- **类型**：原理断裂
- **位置**：「SQLite WAL 模式的四级锁」
- **问题**：称"四级文件锁"但实际描述了五个状态（UNLOCKED/SHARED/RESERVED/PENDING/EXCLUSIVE）。PENDING 在 SQLite 文档中是正式的锁状态，不是"过渡态"。SQLite 官方文档明确列出 5 个 locking levels
- **建议**：修正为"五级文件锁机制"，将 PENDING 作为正式锁级别描述而非过渡态

## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-16
- **类型**：原理断裂
- **位置**：「从 apply() 到 ANR 的完整链路」段
- **问题**：只提到 handlePauseActivity() 触发 waitToFinish()，未提及 handleStopActivity() 和 handleSleeping() 也会触发
- **建议**：补充其他触发点，帮助读者理解 apply() ANR 不仅发生在 Activity 切换时

## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-16
- **类型**：版本差异
- **位置**：版本演进节
- **问题**：Android 14 后台 broadcast 超时变化描述过于笼统（"后台 Broadcast 超时缩短"），实际 Android 14 引入了 CPU-starved 分级机制，60s 可扩展到 120s
- **建议**：补充 Android 14 的具体超时变化细节

## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-16
- **类型**：知识盲区
- **位置**：全文缺失
- **问题**：未提及 InputConnection ANR（5s 超时）和 Trampoline ANR 场景
- **建议**：在「常见问题与误区」中补充提及，或在扩展阅读中引用

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-16

### [P1] 源码路径错误：OpenGLRenderer.cpp
- **类型**：源码准确性
- **位置**：参考资料段 "frameworks/base/libs/hwui/renderthread/OpenGLRenderer.cpp"
- **问题**：Android 10+ HWUI 统一 Skia Pipeline 后，OpenGLRenderer 类已不存在。android-16.0.0_r1 中应引用 SkiaOpenGLPipeline 相关路径
- **建议**：更新为 frameworks/base/libs/hwui/pipeline/skia/ 或标注该路径适用于 Android 9 及之前版本

### [P1] Fence 伪代码误导
- **类型**：原理断裂
- **位置**："同步机制" 小节 Fence 伪代码
- **问题**：consumerReleaseFence->signal() 暗示 Fence 由消费者手动 signal。实际 Fence 由 GPU/驱动在操作完成时自动 signal，消费者只负责创建和等待
- **建议**：重写伪代码，体现 Fence 的创建者（生产者创建 acquire fence，消费者创建 release fence）和自动 signal 语义

### [P1] BufferQueue 节未区分 BlastBufferQueue
- **类型**：版本差异
- **位置**："BufferQueue 生产者-消费者模型" 全节
- **问题**：描述基于 Legacy BufferQueue 模型。Android 12+ 引入 BlastBufferQueue 后，App 与 SurfaceFlinger 间不再通过 Binder IPC 传递 buffer，改为共享内存 + fence。这是近 4 个版本最重要的图形架构变更
- **建议**：在节开头添加版本说明，描述 BlastBufferQueue 的关键差异（减少 Binder 开销），并在数据流图中区分两个版本

### [P1] SurfaceFlinger 惰性合成机制缺失
- **类型**：知识盲区
- **位置**："SurfaceFlinger 合成" 小节
- **问题**：未解释 SurfaceFlinger 只在有新 buffer 时才触发合成（vs. 每个 VSync 都合成）。这解释了 Trace 中 SurfaceFlinger 合成间隔不均匀的现象
- **建议**：补充 SurfaceFlinger 的合成触发条件（有 queued frame / VSync-sf 到来 + dirty region）

### [P2] 主线程-RenderThread syncFrameState 缺失
- **类型**：原理断裂
- **位置**："UI 线程与 RenderThread 的协作" 小节
- **问题**：未提及 syncFrameState 同步点，这是主线程可能阻塞等待 RenderThread 的关键位置
- **建议**：补充 syncFrameState 的作用和 Trace 中的表现

### [P2] 色域转换描述位置不当
- **类型**：原理断裂
- **位置**："显示输出" 小节最后一段
- **问题**：色域转换主要发生在 GPU 渲染或 SurfaceFlinger 合成阶段，不是显示硬件的最后一步
- **建议**：移至 SurfaceFlinger 合成节或删除，避免误导

### [P2] 量化断言缺乏数据支撑
- **类型**：数据缺失
- **位置**：HWUI 概述段 "复杂 2D 图形渲染性能相比纯 CPU 软件渲染提升 5-10 倍"
- **问题**：无引用来源、无测量条件
- **建议**：补充引用或标注为[待验证：需实测数据]

### [P2] 版本演进节对核心机制版本差异覆盖不足
- **类型**：版本差异
- **位置**："版本演进" 节 + BufferQueue 节
- **问题**：三缓冲 maxBufferCount 在不同版本的默认值变化未说明；BlastBufferQueue 对 BufferQueue 接口的改变未在正文中体现
- **建议**：在 BufferQueue 节添加版本标注，说明 Android 12 前后的架构差异

### [P2] 总结段过于简化 SurfaceFlinger 合成
- **类型**：交叉引用
- **位置**：总结段 "SurfaceFlinger 把多个 App 的缓冲区按 Z-Order 叠加后交给 HWC 输出到屏幕"
- **问题**：忽略了 GPU 合成回退路径，与正文合成节描述不一致
- **建议**：改为 "SurfaceFlinger 优先通过 HWC 合成，必要时回退 GPU 合成，最终输出到屏幕"

## [Task6 Review] 7.14 GAPS：Android 动态分析目标可达性路径重建 — 2026-04-16
- **类型**：需补充素材
- **位置**：技术数据基准
- **问题**：AnodTest基准测试的具体定义和数据来源缺失
- **建议**：需要补充AnodTest基准测试的详细定义、测试方法、数据来源链接
- **review 日志**：logs/review/2026-04-16-17-review.md

## [Task6 Review] 7.14 GAPS：Android 动态分析目标可达性路径重建 — 2026-04-16
- **类型**：需补充素材
- **位置**：测试环境
- **问题**：GAPS测试的具体环境和配置参数不明确
- **建议**：需要补充GAPS测试的具体设备、Android版本、测试配置等环境参数
- **review 日志**：logs/review/2026-04-16-17-review.md

## [Task6 Review] 7.14 GAPS：Android 动态分析目标可达性路径重建 — 2026-04-16
- **类型**：需补充素材
- **位置**：数据对比
- **问题**：动态触达率57.44%缺少对比基线说明
- **建议**：需要补充动态触达率的对比基线，说明与之前方案的对比关系
- **review 日志**：logs/review/2026-04-16-17-review.md

## [Task9 Deep Review] 10.4 低内存对系统性能的影响 — 2026-04-16

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

## [Task9 Deep Review] 11.4 功耗案例集 — 2026-04-16
- **类型**：版本差异
- **位置**：案例四 AlarmManager 代码 — PendingIntent.FLAG_IMMUTABLE
- **问题**：代码使用 PendingIntent.FLAG_IMMUTABLE，但章节 applicable_versions 从 Android 8.0 开始。FLAG_IMMUTABLE 从 Android 12 (API 31) 起为必需标志，Android 8-11 可使用 FLAG_MUTABLE 或不设 flag。
- **建议**：在代码旁标注「Android 12 起必需 FLAG_IMMUTABLE」注释，或使用条件判断。

## [Task9 Deep Review] 11.4 功耗案例集 — 2026-04-16
- **类型**：数据缺失
- **位置**：案例一/二/三/五的效果对比表
- **问题**：多处效果对比数据缺少实验来源。如案例一「4h 待机耗电 40%→3%」、案例二「25%→3%」、案例三「15%→5%/3%」、案例五「15%→3%」。这些数据看起来是估算值而非实际测试结果。
- **建议**：标注为「典型值（基于 X 设备 Y 系统测试）」或改为定性描述（「从严重异常降至系统待机水平」）。

## [Task9 Deep Review] 11.4 功耗案例集 — 2026-04-16
- **类型**：知识盲区
- **位置**：案例三「长期：Push 替代 Pull」
- **问题**：推荐 FCM 作为长期方案，但未讨论 FCM 的局限性（消息大小限制 4KB、需要 Google Play Services、中国大陆不可用）以及何时选择 WebSocket 长连接替代。
- **建议**：补充 FCM 的适用场景和限制，提及国内需使用厂商推送通道或自建 WebSocket。

## [Task9 Deep Review] 11.4 功耗案例集 — 2026-04-16
- **类型**：知识盲区
- **位置**：案例三 Radio 状态机描述
- **问题**：描述基于 3G/LTE 模型（30-60秒不活动期进入 Standby）。5G NR 使用 DRX/CDRX 机制，状态转换时间和功耗特征不同，但未提及。
- **建议**：补充说明 Radio 状态机模型因网络技术而异，5G NR 场景下需要额外关注 CDRX 配置对功耗的影响。

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-17
- **类型**：版本差异
- **位置**：版本演进表 Android 4.1 条目
- **问题**：声称"Android 4.1 (API 16) 引入 InputFlinger 框架"，但 InputManager/InputReader/InputDispatcher 的分层设计在 Android 1.0 就存在。Android 4.1（Project Butter）引入的是 Choreographer 和 VSync 机制，不是 InputFlinger 重构。InputFlinger 的代码目录重组发生在更晚的版本。
- **建议**：核实此条目。如果指 InputManagerService 重构，明确标注；如果不确定来源，标注 [待验证] 或删除。

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-17
- **类型**：版本差异
- **位置**：版本演进表 Android 15 条目
- **问题**："输入法与 Input 系统交互优化，改善 IME 切换时的输入延迟"过于模糊，缺少具体 AOSP 变更或功能名称。
- **建议**：补充具体的 commit hash 或功能名称，或标注 [待验证]。

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-17
- **类型**：数据缺失
- **位置**："为什么是 5 秒"一节
- **问题**：ANR 超时机制一节纯原理描述，缺少 Perfetto Trace 数据支撑。缺少 wq 从正常值增长到触发 ANR 的数值描述。
- **建议**：补充一个 Perfetto Trace 场景描述：正常情况下 wq 在 0-2 波动；ANR 前兆时 wq 持续 >5 超过 5 秒；最终触发 ANR 时 wq 值突然归零并出现 ANR trace tag。给出具体数值范围。


## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-17
- **类型**：源码准确性+版本差异
- **位置**：Project Butter 节 Choreographer 回调序列
- **问题**：Android 4.1 段列出 INPUT→ANIMATION→INSETS_ANIMATION→TRAVERSAL→COMMIT 完整回调序列。INSETS_ANIMATION 为 API 30 新增，COMMIT 为 API 24 新增。Android 4.1 原始回调仅为 INPUT→ANIMATION→TRAVERSAL。
- **建议**：在 Android 4.1 段只列出 INPUT→ANIMATION→TRAVERSAL，在后续版本（如 Android 7.0 段和 Android 11 段）分别说明 COMMIT 和 INSETS_ANIMATION 的引入。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-17
- **类型**：原理断裂
- **位置**：RenderThread 段的 eglSwapBuffers/glFinish 描述
- **问题**：将 Android 4.x 主线程卡顿的核心原因归结为 glFinish 阻塞，但更根本的问题是 drawDisplayList() 整个 GPU 命令执行过程在主线程同步调用。
- **建议**：重写该段的因果链：Android 4.x 中 drawDisplayList() 在主线程同步执行 GPU 命令（包括命令提交和等待完成），这使得整个 GPU 工作时间都计入主线程。RenderThread 将全部 GPU 命令提交和执行移到独立线程，主线程只需录制 RenderNode。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-17
- **类型**：版本差异
- **位置**：版本演进时间线表
- **问题**：完全跳过 Android 6.0、11、14 三个大版本。Android 6.0 有 DisplayListCanvas→RecordingCanvas 更名和嵌套滑动机制；Android 11 有 BufferQueue 行为变更（BLASTBufferQueue 预演）；Android 14 有渲染行为变更。
- **建议**：补充 Android 6.0、11、14 三个版本的渲染相关关键变更到时间线表中。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-17
- **类型**：版本差异
- **位置**：Android 16 节 ANGLE 描述
- **问题**：称 Android 16 集成了 ANGLE 作为系统级驱动。实际上 ANGLE 在 Android 12 已可选集成，13 成部分 App 默认 OpenGL ES 实现，15 大幅扩展覆盖范围。Android 16 是进一步扩大而非首次集成。
- **建议**：改为「Android 12 开始可选集成 ANGLE 作为 OpenGL ES 到 Vulkan 的翻译层，此后逐步扩大覆盖范围。Android 16 将 ANGLE 作为所有 OpenGL ES 应用的默认实现，OpenGL ES 进入维护模式。」

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-17
- **类型**：原理断裂
- **位置**：first-stage init 段 — FirstStageMount 机制
- **问题**：提到 FirstStageMount::DoFirstStageMount() 挂载启动必需分区，但未解释它如何决定挂载哪些分区（A/B slot 选择逻辑、分区决策依据）。读者无法理解为什么某些设备 init 阶段特别慢（如 A/B slot 切换后需要验证新分区）。
- **建议**：补充 FirstStageMount 的决策逻辑简述：读取 boot control HAL 确定当前 active slot → 构建分区挂载列表 → 挂载 system/vendor/product 等分区。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-17
- **类型**：原理断裂
- **位置**：开机性能优化段 — task_profiles
- **问题**：提到 task_profiles 替代了 raw cpuset 写法，但未解释 task_profiles 的机制（它组合了调度策略、uclamp、cpuset 等）和与旧方式的对比。读者可能不清楚为什么新方案更好。
- **建议**：补充 task_profiles 的核心机制一句话说明（将调度相关策略组合为命名 profile，在 init rc 中通过 task_profiles 字段指定），或者标注交叉引用到 5.1 节（Linux 进程调度基础）。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-17
- **类型**：知识盲区
- **位置**：boot_progress 里程碑事件列表
- **问题**：列出的 boot_progress_* 事件不完整。缺少：boot_progress_preload_start / boot_progress_preload_end（Zygote 预加载起止）；boot_progress_pms_data_scan_start / boot_progress_pms_data_scan_end（PMS 数据扫描）。这些事件在 event log 中常见，用于定位 Zygote 和 PMS 阶段的子环节耗时。
- **建议**：在 boot_progress 事件列表中补充 preload_start/end 和 pms_data_scan 事件。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-17
- **类型**：源码准确性
- **位置**：「Zygote fork SystemServer 的触发机制」段 — ZygoteInit.java 行号
- **问题**：引用了非常具体的行号（行 844-850、行 902-912、行 693-801、行 780、行 792-798、行 893）。这些行号标注了 @ android-16.0.0_r1 但未实际验证，且代码行号在不同补丁版本间容易偏移。ZygoteServer.java 行 394 同样需要验证。
- **建议**：将行号标注改为范围描述（如「main() 方法后半段」）或在每处行号旁加 [待验证] 标注。已标注 last_verified_against android-16.0.0_r1，但行号级别的精度需要二次确认。

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-17
- **类型**：知识盲区
- **位置**：开机性能优化段 — APEX 激活
- **问题**：OTA 后首启卡在 APEX 激活的排查建议仅一笔带过（"检查 APEX 激活"），未解释 APEX 激活机制（apexd 在 first-stage init 后半段激活新 APEX 模块，涉及 dm-verity 校验和 loop 设备挂载）及对启动时间的具体影响路径。
- **建议**：在 init 阶段或扩展部分补充 apexd 激活的简要机制和典型耗时影响，或标注交叉引用到 1.7（ART 编译管线）的 APEX 相关内容。


## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-17
- **类型**：源码准确性
- **位置**：JIT 代码片段 — MaybeDoJitCompilation 方法名
- **问题**：`MaybeDoJitCompilation` 在 AOSP 中不存在。实际方法为 `Jit::MaybeCompileMethod(ArtMethod*, Thread*)`，位于 `art/runtime/jit/jit.cc`。`method->GetCounter()` 非标准 API。即使标注"简化示意"，方法名虚构仍会误导读者。
- **建议**：修正为 `MaybeCompileMethod`，或将注释改为 `[伪代码示意]`。

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-17
- **类型**：版本差异
- **位置**：全文 bg-dexopt 引用（至少 3 处）
- **问题**：bg-dexopt 是 Android 13 及以下的术语。Android 14+ 后台编译由 ART Service 的 MaintenanceJobs 管理。applicable_versions 声明 7.0-17。
- **建议**：首次出现 bg-dexopt 处加版本说明，后续使用保持一致。

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-17
- **类型**：版本差异
- **位置**：版本演进表
- **问题**：版本表仅 7 条但 applicable_versions 覆盖 7.0-17。遗漏 Android 8/10/11/13/15。
- **建议**：至少补充 Android 8（JIT code cache 调整）、10（hidden API 限制影响编译假设）、13（Baseline Profiles Mainline 推送能力）。

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-17
- **类型**：数据缺失
- **位置**：多个 [待验证] 标注处
- **问题**：冷启动差距 30%、Baseline Profiles 提升 30% 代码执行速度、JIT 代码缓存 4MB 三个核心量化断言均 [待验证]。这些数据支撑文章核心论点，不应长期悬置。
- **建议**：定位 Google 官方基准测试报告出处，替换 [待验证] 为具体引用。如确实无法找到精确来源，改为定性描述。

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-17
- **类型**：源码准确性
- **位置**：JIT 代码缓存默认值 — dalvik.vm.jitinitialsize/jitmaxsize
- **问题**：默认 64KB/64MB 缺少版本和设备条件标注。不同 SoC 和 Android 版本可能有不同默认值。
- **建议**：标注验证版本（如"基于 android-17-beta3 默认配置"），或改为"典型配置值"并说明来源。



## [Task9 Deep Review] 14.1 Android Studio Profiler — 2026-04-17

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


## [Task9 Deep Review] 18.2 Android View 标准链路（BLAST 深入）— 2026-04-17

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

## [Task6 Review] 18.5 Android View 多窗口链路 — 2026-04-17

- **类型**：需确认 + 需补充素材
- **位置**：优化策略 > 策略一：合并窗口
- **问题**：代码示例推荐 `BottomSheetDialogFragment`，注释称其为"View 级别的 BottomSheet"，但 `BottomSheetDialogFragment` 实际仍创建独立 Window（继承自 AppCompatDialogFragment → AppCompatDialog → Dialog），并不会合并到 Activity 的 Surface。真正 View 级别无额外 Window 的方案应使用 `BottomSheetBehavior` + `CoordinatorLayout`，或直接在 Activity 布局内用 View 实现。
- **建议**：将推荐方案改为使用 `BottomSheetBehavior` 绑定到 Activity 布局内的 View，或标注 `BottomSheetDialogFragment` 仍会创建独立 Window 但比普通 Dialog 轻量。
- **review 日志**：logs/review/2026-04-17-08-review.md

## [Task6 Review] 18.5 Android View 多窗口链路 — 2026-04-17

- **类型**：需确认
- **位置**：全链路执行流程 > 阶段三
- **问题**：文中描述"UI Thread 在 Sync A 时被阻塞（`syncFrameState`），直到 RenderThread 完成同步。这意味着 Window B 的 Traversal 可能需要等 Window A 的 Sync 完成后才能开始"。`syncFrameState` 的阻塞行为在不同 Android 版本中有差异——在某些版本中 UI Thread 仅短暂阻塞以交换 DisplayList 引用即返回，不会等到 DrawFrame 完成。需确认具体版本下的行为。
- **建议**：标注 `[待验证：syncFrameState 阻塞粒度在不同 Android 版本的表现]`，或明确说明此处描述适用于哪个 Android 版本范围。
- **review 日志**：logs/review/2026-04-17-08-review.md

## [Task6 Review] 18.5 Android View 多窗口链路 — 2026-04-17

- **类型**：需补充素材
- **位置**：全文
- **问题**：章节 applicable_versions 标注为 Android 9-16，但正文未讨论任何版本间的行为差异。例如：(1) Android 12 对 `BufferQueue` 和 `syncFrameState` 的改动；(2) Android 10 引入 Multi-resume 后 Choreographer 分发行为的变化；(3) Android 14+ 对分屏模式的渲染管线调整。
- **建议**：增加"版本演进"小节，或在各关键段落中补充版本差异标注。至少覆盖 Android 10（Multi-resume）、Android 12（RenderThread 改动）两个关键版本节点。
- **review 日志**：logs/review/2026-04-17-08-review.md

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-17

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


## [Task9 Deep Review] 9.4 特殊场景的 ANR — 2026-04-17

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


## [Task6 Review] 15.3 性能指标体系 — 2026-04-17
- **类型**：L4 活人感（无个人经验痕迹）
- **位置**：全文多处
- **问题**：章节整体为教科书/参考手册风格，无 Gracker 个人经验痕迹，缺少"我/我们曾经"的实战叙述
- **建议**：在关键位置穿插实战案例（如"我在分析 XX App 时，用 P99 而不是均值发现了..."），增强工程师经验感
- **review 日志**：logs/review/2026-04-17-10-review.md

---

## [Task6 Review] 15.3 性能指标体系 — 2026-04-17
- **类型**：L3 内容深度（Active/Idle Power 节单薄）
- **位置**：功耗指标 — Active/Idle Power 节
- **问题**：Active/Idle Power 功耗分析节内容单薄，全文有 `[待补充: Perfetto Power track 的具体使用方法和截图示例]` 标注
- **建议**：补充 Perfetto Power track 的使用方法，说明如何观察电流曲线和子系统功耗分布，给出实际 Trace 截图描述或标注 `[待补充：Trace 截图]`
- **review 日志**：logs/review/2026-04-17-10-review.md

---

## [Task6 Review] 15.3 性能指标体系 — 2026-04-17
- **类型**：L3 代码准确性（reportFullyDrawn 示例冗余）
- **位置**：TTFD 节 — reportFullyDrawn() 代码示例
- **问题**：if-else 两分支执行完全相同的 `reportFullyDrawn()` 调用，版本分支无实际差异。注释提到 API 31+ 可传更精确时间戳，但代码未使用
- **建议**：补充 `reportFullyDrawn(long duration)` API 31+ 用法，或简化为单行调用并调整注释
- **review 日志**：logs/review/2026-04-17-10-review.md




## [Task9 Deep Review] 15.3 性能指标体系 — 2026-04-17

- **类型**：源码准确性（API 归属错误）
- **位置**：流畅性指标 — Frame Time 与分位数节
- **问题**：FrameMetricsAggregator 被描述为"Android 9.0+, API 28"的平台 API，但实际是 AndroidX Jetpack 库（`androidx.metrics:metrics-performance`），最低支持 API 16。描述可能误导读者认为这是平台内置 API
- **建议**：修正为"Jetpack 的 FrameMetricsAggregator（需引入 `androidx.metrics:metrics-performance` 依赖，最低 API 16，API 24+ 可获取详细分阶段数据）"
- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md

---

- **类型**：源码准确性（适用版本不一致）
- **位置**：Frontmatter applicable_versions
- **问题**：applicable_versions 声明 "Android 8.0 (API 26) - Android 16 (API 36)"，但文中引用的 FrameMetrics API 自 API 24 (Android 7.0) 起可用
- **建议**：将下界调整为 API 24，或在文中注明 FrameMetrics 是 API 24+ 特性，章节主要讨论的内容适用 API 26+
- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md

---

- **类型**：原理链不完整
- **位置**：稳定性指标 — ANR Rate 节
- **问题**：ANR 触发条件仅提到"输入事件 5 秒超时"和"Service 规定时间"。缺少完整触发类型及对应超时值：Service（前台 20s/后台 200s）、BroadcastReceiver（前台 10s/后台 60s）、ContentProvider（10s）
- **建议**：列出完整 ANR 触发类型表格，或明确交叉引用 ch09.1 作为详细参考
- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md

---

- **类型**：数据支撑缺失
- **位置**：指标体系设计原则 — 分位数 vs 均值节 + 各指标节
- **问题**：缺少 Perfetto SQL 查询示例。同书 ch05.4 提供了频率分析 SQL，但本节作为指标体系章节反而没有。缺少从 Perfetto 计算 Frame Time P50/P90/P99、ANR 统计等常用 SQL
- **建议**：在"在 Perfetto 中观察"类段落或附录中补充核心指标的 Trace Processor SQL 查询示例
- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md

---

- **类型**：数据支撑缺失
- **位置**：全文各指标节
- **问题**：缺少统一的"指标-推荐目标值"速查表。Google Play 不良行为阈值已给出，但业界推荐基准（如 P99 Frame Time < 2x frame budget、TTID < 2s、TTFD < 5s 等）分散在各段中，不易查阅
- **建议**：在"指标体系设计原则"节或独立小节中增加一个速查表，按指标类别列出推荐目标值和 Google Play 不良行为阈值
- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md

---

- **类型**：知识盲区
- **位置**：全文
- **问题**：缺少网络性能指标（TTFB、下载吞吐量、连接延迟等）。对网络密集型 App（信息流、视频、社交），网络指标是性能体系的重要组成
- **建议**：补充一节"网络性能指标"，覆盖 TTFB、throughput、connection latency，或标注为扩展内容并交叉引用 ch12
- **review 日志**：logs/deep-review/2026-04-17-12-deep-review.md


---

[Task2B 回炉失败] 15.3 性能指标体系 — 原因：需要高爷确认

**Issue**: 活人感不足 — 章节整体为教科书/参考手册风格，缺少 Gracker 个人经验痕迹和实战叙述。

**已修复的其他 3 个 issue**：
1. ✅ system-triggered profiling 版本自相矛盾（Android 14+ → 16）
2. ✅ reportFullyDrawn() 代码 if-else 两分支相同 → 简化为单行调用
3. ✅ Active/Idle Power 缺 Perfetto Power track 使用说明 → 已补充

**需要 Gracker 做的事情**：
在以下关键位置补充实战经验（1-2 句即可）：
- FPS/Frame Time 节：一个用 P99 发现均值掩盖问题的真实案例
- TTID/TTFD 节：一次实际启动优化的经历
- 指标体系设计原则节：线上监控建设中的踩坑经验

标记时间：2026-04-17 12:44

## [Task6 Review] 15.6 性能测试最佳实践 — 2026-04-17
- **类型**：需确认
- **位置**：§消除测试干扰 > 固定CPU频率（进阶）
- **问题**：代码示例 `echo 0 > /sys/devices/system/cpu/cpu0/online` 是将CPU0下线（offline），而非锁定频率。下线CPU与"固定频率"的目的矛盾。
- **建议**：删除offline命令，保留governor设置命令；或改为 `echo 1 > online` 确保在线后再设governor。
- **review 日志**：logs/review/2026-04-17-13-review.md

## [Task6 Review] 15.6 性能测试最佳实践 — 2026-04-17
- **类型**：需确认
- **位置**：§消除测试干扰 > 固定CPU频率（进阶）
- **问题**：`adb shell cmd thermal thontrol disable` 中"thontrol"疑似拼写错误，正确可能是"control"或其他子命令。
- **建议**：验证 `cmd thermal` 的子命令列表，确认正确拼写。
- **review 日志**：logs/review/2026-04-17-13-review.md

## [Task6 Review] 15.6 性能测试最佳实践 — 2026-04-17
- **类型**：需确认
- **位置**：§测试环境标准化 > 网络环境
- **问题**：`adb shell ndc network create` 作为网络模拟方案，需要验证ndc（Native Daemon Connector）是否支持该子命令。
- **建议**：验证ndc命令族的实际可用参数，或替换为更通用的网络模拟方案。
- **review 日志**：logs/review/2026-04-17-13-review.md

## [Task9 Deep Review] 1.4 Binder IPC 机制与性能影响 — 2026-04-17

### P1：Binder mmap 缓冲区生命周期缺失
- **类型**：原理断裂
- **位置**：「为什么 Binder 只需要"一次拷贝"」小节及 TransactionTooLargeException 相关段落
- **问题**：章节提到 ~1MB mmap 缓冲区限制和 TransactionTooLargeException，但未解释缓冲区的分配/回收机制。每次 Binder 事务从 mmap pool 动态分配 buffer，事务完成后释放；并发事务共享同一 pool。这导致 TransactionTooLargeException 的最常见原因并非单次数据过大，而是并发事务累积超限
- **建议**：在"一次拷贝"小节或新增"缓冲区管理"小节中补充：(1) binder_alloc 机制 — 从 mmap pool 分配 binder_buffer；(2) 并发事务共享 pool 的竞争关系；(3) 诊断 TransactionTooLargeException 时需关注并发事务数而非仅看单次数据量

### P2-1：oneway "Lazy Async" 术语需验证
- **类型**：源码准确性
- **位置**：「oneway 调用」小节，"调用方仍然可能阻塞"段落
- **问题**："Android 14+ 引入 Lazy Async" 的术语未在 AOSP 官方文档中确认
- **建议**：标注 [待验证]，或改为描述性说法（如"Android 14+ 对 oneway 投递策略的优化"）

### P2-2：Binder 线程名格式小差异
- **类型**：源码准确性
- **位置**：「线程池是怎么工作的」小节
- **问题**：文中引用 `"%.*s:%d_%X"` 格式，AOSP 实际为 `String8::format("%s:%d_%X", driver, getpid(), seq)`
- **建议**：核对 ProcessState.cpp 原始代码，统一格式描述

### P2-3：scatter-gather 拷贝数描述可能引起混淆
- **类型**：原理断裂
- **位置**：「为什么 Binder 只需要"一次拷贝"」小节末尾
- **问题**："将原来需要三次拷贝的流程减少到一次"中的"三次拷贝"包含用户态序列化/反序列化，而前文刚说 Binder 是"一次拷贝"（指内核态），两种说法放在同一段会困惑读者
- **建议**：明确区分"内核态 IPC 拷贝"（Binder mmap 一直是单次）和"用户态数据整理"（scatter-gather 优化的是这一层），避免读者认为 Binder 从 3-copy 变成了 1-copy

### P2-4：冷启动 Binder 调用次数缺乏数据支撑
- **类型**：数据缺失
- **位置**：「为什么要了解 Binder」段落
- **问题**："主线程可能发起 30-50 次同步 Binder 调用"为估计值，无来源
- **建议**：标注 [待验证] 或引用 Perfetto 实测数据

### P2-5：缺少 Binder death notification 讨论
- **类型**：知识盲区
- **位置**：全文
- **问题**：linkToDeath/unlinkToDeath 机制未提及。高频进程崩溃场景下 death notification 风暴是生产环境偶发卡顿的来源
- **建议**：在"常见问题与误区"或"版本演进"节补充 brief 讨论


## [Task9 Deep Review] 15.7 AOSP 代码阅读 — 2026-04-17

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

## [Task9 Deep Review] 5.5 Thermal 管控 — 2026-04-17

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


## [Task9 Deep Review] 18.8 OpenGL ES 渲染链路 — 2026-04-17

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

## [Task6 Review] 17.3 行业案例 — 2026-04-17

- **类型**：需清理 + 需补充素材 + 需确认
- **位置**：参考资料 section 末尾 / Samsung Max Boost 描述 / Rhea 开源状态描述
- **问题**：
  1. 参考资料末尾 5 条条目与本章节主题无关（豆包手机/Flutter适配鸿蒙/Android15适配/2026年Android趋势/AI写Android排名），疑似 intake 误关联
  2. Samsung Max Boost 模式缺少可验证的官方来源链接
  3. Rhea 工具的"开源社区发布了核心框架"描述不够准确，需确认实际开源范围
- **建议**：删除无关参考条目；补充 Samsung Max Boost 官方文档链接；核实 Rhea 开源状态后更新措辞
- **review 日志**：logs/review/2026-04-17-21-review.md


## [Task9 Deep Review] 14.8 GPU 图形调试与分析工具 — 2026-04-17

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

## [Task9 Deep Review] 1.10 ContentProvider 性能与优化 — 2026-04-17

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

## [Task6 Review] 18.10 SurfaceControl API 深入 — 2026-04-17

- **类型**：需修正 + 需补充素材
- **位置**：文末交叉引用 + §实战场景 + 全文验证标注 + frontmatter related_chapters
- **问题**：
  1. 交叉引用路径指向不存在的 `part1-foundation/ch02-graphics-foundation/`，正确路径为 `part1-fundamentals/ch02-rendering/`；且章节编号错误（2.1 是渲染概述非 BufferQueue，2.5 是主线程渲染线程非 SurfaceFlinger）
  2. 实战场景（WebView OOP / PiP / 自绘引擎）各仅 2-4 句话约 300 字，writing-guide 要求 1500-3000 字
  3. 全文仅 2 处 [已验证]，大量 API 版本引入、fence 语义、HWC 限制等技术断言缺少验证标注
  4. frontmatter related_chapters 编号与实际章节不匹配
- **建议**：
  1. 修正交叉引用路径和编号，同步修正 frontmatter
  2. 至少展开 WebView OOP 为完整实战案例
  3. 逐段补充验证标注
- **review 日志**：logs/review/2026-04-17-23-review.md


## [Task9 Deep Review] 18.3 Android View 软件渲染链路 — 2026-04-17
- **类型**：数据缺失
- **位置**：L171 GPU < 0.1ms / CPU > 10ms 的对比
- **问题**：数值没有设备型号、分辨率、图元复杂度、实现方式等上下文，容易被读者当成通用基线。
- **建议**：改成“示意量级”并补设备/场景前提，或替换为真实 benchmark / Perfetto 案例。


## [Task9 Deep Review] 18.3 Android View 软件渲染链路 — 2026-04-17
- **类型**：源码准确性
- **位置**：L43 / L187 “Toast、部分 Notification 使用软件渲染”
- **问题**：示例缺少 AOSP 路径或版本限定，且不同窗口类型、RemoteViews 实现和 OEM 定制差异很大，当前说法过于绝对。
- **建议**：给出具体 AOSP 证据和版本范围；如果没有可验证材料，删除这两个例子，改成更稳妥的“个别系统窗口或兼容性场景可能退回软件路径”。


## [Task9 Deep Review] 18.3 Android View 软件渲染链路 — 2026-04-17
- **类型**：交叉引用
- **位置**：frontmatter related_chapters
- **问题**：正文末尾显式交叉引用了 2.13 和 2.14，但 related_chapters 仅保留 2.1 / 2.5 / 18.2，元数据和正文不一致。
- **建议**：把 2.13、2.14 加入 related_chapters，避免后续目录/索引工具漏链。

## [Task9 Deep Review] 12.2 网络性能优化 — 2026-04-18
- **类型**：源码准确性
- **位置**：L89 / L332 验证标注
- **问题**：两处 [已验证] 都把 OkHttp EventListener 指向 developer.android.com/reference/okhttp3/EventListener。OkHttp 不属于 Android SDK，该路径并不是官方 API 文档地址。
- **建议**：改为 Square OkHttp EventListener 官方文档（events/ 或 API reference），避免把不存在的 Android 文档当成验证来源。

## [Task9 Deep Review] 12.2 网络性能优化 — 2026-04-18
- **类型**：数据缺失
- **位置**：L121 HTTP/3 性能收益数据
- **问题**：Google/Uber/Meta 的 15%、10-30%、20% 指标只给了公司名和博客域名，没有文章标题、年份、实验对象、网络条件或指标定义，读者无法追溯这些数字到底对应 buffering、tail latency 还是 error rate。
- **建议**：补充精确出处和测试上下文，或统一降级为 [待验证]，避免把营销级数字当成可复用基线。

## [Task9 Deep Review] 12.2 网络性能优化 — 2026-04-18
- **类型**：数据缺失
- **位置**：L342 / L368 NetworkCapabilities 带宽描述
- **问题**：把 getLinkDownstreamBandwidthKbps() 近似写成“LinkSpeed/下行带宽”，但它是系统给出的能力估计值，不是实际下载吞吐。若直接拿它驱动画质切换，读者容易把“估计容量”误用成“实时测速结果”。
- **建议**：补一句“这是网络 agent 的估算值，不等于真实吞吐”，并说明需要结合 EventListener 或样本下载结果做校准。

## [Task9 Deep Review] 14.3 内存分析工具 — 2026-04-18
- **类型**：源码准确性
- **位置**：heapprofd 配置示例
- **问题**：`name: "linux.heapprof"`、`heapprof_config`、`target_cmdline` 三处字段都与 Perfetto 官方 proto 不一致。
- **建议**：改为 `android.heapprofd`、`heapprofd_config`、`process_cmdline`，并把官方链接修正为 `https://perfetto.dev/docs/data-sources/native-heap-profiler`

## [Task9 Deep Review] 14.3 内存分析工具 — 2026-04-18
- **类型**：实操错误
- **位置**：MAT 抓取 hprof / malloc_debug 命令示例
- **问题**：`kill -SIGHUP` 不能触发 GC；`backtrace_enable_on_signal` 使用的是 `SIGRTMAX - 19`，不是 `SIGUSR1`。
- **建议**：Java heap dump 示例改为 `adb shell am dumpheap -g <pid> ...`；malloc_debug 按 bionic README 使用实时信号。

## [Task9 Deep Review] 14.3 内存分析工具 — 2026-04-18
- **类型**：版本差异
- **位置**：profileable / HWASAN / MTE 说明
- **问题**：`android:profileable="true"` 语法错误，且 HWASAN、MTE 的版本/设备边界写得过满。
- **建议**：改为 `<profileable android:shell="true"/>`，分别标注 HWASAN 的 Android 14+ wrap.sh 边界、MTE 的设备支持列表与 heap/stack 检测差异。
## [Task6 Review] 18.14 Camera 渲染管线 — 2026-04-18

- **类型**：需补充素材 + 需重写
- **位置**：多处
- **问题**：
  1. 「常见性能问题」仅 4 条 1-2 句列表，缺少根因分析、Perfetto 表现、修复方案
  2. 「在 Perfetto 中识别 Camera 管线」仅 3 行 track 表，无具体分析方法
  3. 「关键组件」3 条项目符号无叙述展开，CameraService/HAL3/CaptureRequest 角色不清
  4. 缺少版本演进（Camera1→Camera2→CameraX、HAL 版本变化），applicable_versions 跨 5-16 但无差异说明
  5. 参考资料仅目录级路径，缺关键函数名和分支标注
- **建议**：参考 writing-guide.md 类型A（机制原理篇）模板，将列表式内容转为叙述体，补充 Trace 分析方法和版本演进
- **review 日志**：logs/review/2026-04-18-03-review.md

## [Task9 Deep Review] 18.10 SurfaceControl API 深入 — 2026-04-18
- **类型**：数据缺失
- **位置**：§18.10.5 Layer 数量与性能 + §18.10.8 实战场景
- **问题**：关于“HWC overlay 名额通常只有少数几个”“WebView 独立 SurfaceControl 后宿主 RenderThread 会明显减负”等判断都停留在经验描述，没有给出至少一组 Perfetto / dumpsys SurfaceFlinger 的真实观察样本。读者知道方向，但拿不到可验证的基线。
- **建议**：补一组最小证据链，至少包含 child layer 树、setTransactionState/latchBuffer 观察点，以及宿主 RenderThread 前后对比或 HWC/GPU 合成变化。



## [Task9 Deep Review] 18.15 视频叠加与 HWC — 2026-04-18
- **类型**：数据缺失
- **位置**：L39 开头段的“2-3x 内存带宽”“10-20% 功耗差异”
- **问题**：关键量化结论没有设备、分辨率、codec、刷新率或测试方法上下文，读者容易把它当成跨平台通用基线。
- **建议**：补至少一组具备条件说明的样本（设备 / Android 版本 / 1080p or 4K / 60Hz or 120Hz / 播放器实现），或者把这两句降级成定性表述。

## [Task9 Deep Review] 18.15 视频叠加与 HWC — 2026-04-18
- **类型**：源码准确性
- **位置**：L162-L180「在 Perfetto 和 dumpsys 中识别 Overlay」
- **问题**：当前诊断方法过于粗糙。`grep SurfaceView` 和“GPU Track 没额外任务”不能稳定证明 Overlay 成功，因为 App UI 本身仍可能在用 GPU。章节缺少真正的证据链：layer 的 composition type、client target 是否存在、presentDisplay / setClientTarget 的关系、sideband / DEVICE layer 的可观察字段。
- **建议**：补充更可执行的检查项，至少区分“App GPU 绘制”和“SurfaceFlinger client composition”，给出 dumpsys 字段名或一段更精确的 Perfetto 观察方法。

## [Task9 Deep Review] 18.15 视频叠加与 HWC — 2026-04-18
- **类型**：交叉引用
- **位置**：frontmatter related_chapters
- **问题**：正文多次依赖 BufferQueue、fence 和 Overlay/CLIENT 的判定，但 related_chapters 只列了 2.6 / 2.10 / 18.6，缺少最直接的 2.13（BufferQueue）和 2.16（Sync Fence）。
- **建议**：在 related_chapters 中补充 `2.13`、`2.16`，必要时增加 `18.10`（SurfaceControl / layer 管理）。

## [Task6 Review] 18.16 游戏引擎渲染链路 — 2026-04-18

- **类型**：需验证 + 需补充素材
- **位置**：Swappy 代码块 + 参考资料 + Perfetto 描述
- **问题**：
  1. SwappyVk_setSwapIntervalNS 参数签名需验证（Android Game SDK 版本差异）
  2. 参考资料缺少 URL，AOSP 路径过于笼统
  3. Perfetto 中 Swappy Track/Slice 描述笼统，缺少具体名称
- **建议**：
  1. Task 9 验证 Swappy Vulkan API 最新签名
  2. 补充官方文档 URL
  3. 补充具体 Swappy Track/Slice 名称或 Trace 截图
- **review 日志**：logs/review/2026-04-18-05-review.md

## [Task9 Deep Review] 18.4 Android View 混合渲染链路 — 2026-04-18
- **类型**：数据缺失
- **位置**：L183 Overlay 数量判断
- **问题**：`HWC 支持的最大 Overlay 数量通常 4-8 个` 没有 SoC、Display Engine、HWC HAL 代际或 dumpsys / vendor 文档上下文，容易被读者误读成跨平台通用上限。
- **建议**：补一张 capability matrix，或者至少把表述降级为“Overlay 名额依平台而异”，再给一组设备级样本。

- **类型**：原理完整性
- **位置**：L78 Pipeline B 节奏描述
- **问题**：`帧率取决于视频源和解码速度，而不是系统的 VSync 频率` 说得过满。Producer cadence 的确独立于 Choreographer，但最终 present 仍受 SurfaceFlinger / HWC 的 VSync 节奏约束。
- **建议**：改成“生产节奏独立，显示节奏仍由 VSync-SF 驱动”，避免把 producer cadence 和 display cadence 混为一谈。


## [Task6 Review] 18.17 Hardware Buffer Renderer — 2026-04-18
- **类型**：需重写 + 需补充内容
- **位置**：全文风格 + 多个章节
- **问题**：
  1. 文体问题：整体读起来像API参考文档（列表堆砌+代码片段），不符合writing-guide.md要求的engineer-to-engineer叙述风格。适用场景、核心架构、性能对比等章节都是列表/表格，缺少因果解释和连贯叙述。
  2. Perfetto识别章节（## 在 Perfetto 中识别）内容极薄，仅两行表格，缺少实际Track名称和Trace截图描述。
  3. 性能对比表的数据（15ms/8ms等）缺少测试条件（设备、Android版本、渲染场景）。
  4. 缺少writing-guide类型A模板要求的"常见问题与误区"章节。
  5. 缺少与RenderThread的关系说明（标准View渲染路径自动管理RenderThread，HBR需要手动管理）。
- **建议**：
  1. 将列表式章节改写为连贯叙述，参考writing-guide.md中"正确写法"示例。
  2. 为Perfetto章节补充实际Track定位方法。
  3. 性能数据补充测试条件，或改为定性描述。
  4. 新增"常见问题与误区"小节。
  5. 补充与RenderThread的对比说明。
- **review 日志**：logs/review/2026-04-18-06-review.md

## [Task9 Deep Review] 18.17 Hardware Buffer Renderer — 2026-04-18
- **类型**：数据缺失
- **位置**：性能对比表（L123-L129）
- **问题**：`1080p 全屏绘制 ~15ms vs ~8ms`、`内存带宽 2x vs 1x`、`120fps 离屏渲染` 都没有设备型号、Android 版本、渲染后端、绘制内容复杂度或 Trace/benchmark 依据。当前数字更像口径占位，不足以支撑章节核心判断。
- **建议**：补充至少一组真实设备 + API level + workload + Trace/benchmark 条件；如果暂时没有数据，就改成定性结论并保留 `[待验证]`。

## [Task9 Deep Review] 18.17 Hardware Buffer Renderer — 2026-04-18
- **类型**：数据缺失
- **位置**：在 Perfetto 中识别（L176-L183）
- **问题**：当前只写了“GPU Track”“SurfaceFlinger 额外 Layer”，没有给出 direct `setBuffer()` 路径在 App/SF 两侧的具体观察点，读者很容易把 §18.2 的 BLAST 轨迹生搬过来。
- **建议**：补一段真实 Trace 描述，至少说明 render callback 完成、`setTransactionState`/`latchBuffer`/present fence 这些证据分别出现在什么进程和什么 slice 上；如果还没抓到，就明确标 `[待补充：direct setBuffer Trace]`。

## [Task9 Deep Review] 18.17 Hardware Buffer Renderer — 2026-04-18
- **类型**：源码准确性
- **位置**：Java API 代码块（L92-L99）
- **问题**：示例拿到 `RenderResult` 后直接 `setBuffer()`，没有检查 `result.getStatus()`，也没有交代 `HardwareBufferRenderer.close()` 与 `HardwareBuffer.close()` 的生命周期边界。对读者来说，这会把错误处理和资源回收都隐掉。
- **建议**：在代码示例中先判断 `result.getStatus() == SUCCESS`，并补一句说明 renderer 关闭不会替调用方关闭 `HardwareBuffer`。


## [Task6 Review] 18.18 PIP 与自由窗口渲染 — 2026-04-18
- **类型**：需补充素材
- **位置**：PIP 渲染流程（持续渲染 + 性能考量）
- **问题**：PIP 模式渲染流程仅一句话带过，性能考量为纯列表缺少深度，缺少 BufferQueue 行为、帧率变化、内存占用的具体分析
- **建议**：参照 writing-guide.md 类型A结构，将 PIP 渲染流程改写为连贯叙述，补充 BufferQueue 在 PIP 模式下的行为变化（如 min/max buffer count 变化、帧率限制策略）和 Perfetto Trace 对应表现
- **review 日志**：logs/review/2026-04-18-07-review.md

## [Task6 Review] 18.18 PIP 与自由窗口渲染 — 2026-04-18
- **类型**：需补充素材
- **位置**：全文 Perfetto Trace 描述
- **问题**：除末尾一张表外，缺少 Perfetto Trace 截图描述或文字标注
- **建议**：在 Trace 定位节补充具体 slice 名称（如 SurfaceFlinger 的 Transaction apply、wm_task_moved）、track 名称和 `[待补充：Trace 截图]` 占位标记
- **review 日志**：logs/review/2026-04-18-07-review.md

## [Task6 Review] 18.18 PIP 与自由窗口渲染 — 2026-04-18
- **类型**：需补充素材
- **位置**：BLAST Sync 解决方案
- **问题**：缺少 AOSP 源码路径（BLASTBufferQueue.java 等）
- **建议**：补充 frameworks/base/libs/gui/BLASTBufferQueue.cpp 及相关 Java 层路径
- **review 日志**：logs/review/2026-04-18-07-review.md

## [Task6 Review] 18.18 PIP 与自由窗口渲染 — 2026-04-18
- **类型**：需补充素材
- **位置**：版本演进（整体缺失）
- **问题**：PIP 从 Android 8.0 引入、BLAST 从 Android 12 引入的关键变化未梳理
- **建议**：添加版本演进表格，标注各版本中 PIP/Freeform/BLAST 的关键变更
- **review 日志**：logs/review/2026-04-18-07-review.md


## [Task9 Deep Review] 18.16 游戏引擎渲染链路 — 2026-04-18
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters` / 正文“与其他章节的关系”
- **问题**：正文显式引用了 `2.17 Frame Pacing Library`，但 `related_chapters` 没有包含 `2.17`，导航链会漏掉帧节奏主线。
- **建议**：在 `related_chapters` 中补上 `2.17`；如果要强化诊断路径，可再考虑补 `13.1 Perfetto 简介与演进`。

## [Task9 Deep Review] 18.16 游戏引擎渲染链路 — 2026-04-18
- **类型**：知识盲区
- **位置**：Unity / Unreal 线程模型表（L80-L94）
- **问题**：表格把 `UnityGfx` / `RHIThread` 写成固定拓扑，未标注 multithreaded rendering、graphics jobs、RHIThread 受引擎版本、后端和项目配置控制。读者可能因为某条线程在 trace 中缺席而误判“不是 Unity/Unreal”。
- **建议**：把表述改成“典型线程模型”，补一句线程是否存在取决于渲染后端和引擎配置。


## [Task6 Review] 18.19 可变刷新率渲染管线 — 2026-04-18

- **类型**：需补充素材 + 需验证 + 需重写
- **位置**：全文多处
- **问题**：
  1. Perfetto 分析节仅3行表格，缺少具体分析流程（B1）
  2. Android 16 Enhanced ARR API 常量名/投票机制待验证（B2）
  3. 缺少 Android 11-16 版本演进段落（B3）
  4. 全文叙述风格偏参考文档，表格/代码为主骨架，缺少连贯技术叙述（B4）
- **建议**：
  - B1: 参考 writing-guide 类型A"在 Perfetto 中的表现"要求，补充 VRR 场景 Perfetto 分析流程、SQL 查询示例、Trace 片段描述
  - B2: 标注 [待验证]，Android 16 API 37 定稿后确认
  - B3: 补充 Android 11(setFrameRate) → 13(ARR) → 15(LTPO优化) → 16(Enhanced ARR) 版本演进
  - B4: 按叙述为主、列表为辅重写常见问题和 Perfetto 分析节
- **review 日志**：logs/review/2026-04-18-09-review.md

## [Task9 Deep Review] 18.14 Camera 渲染管线 — 2026-04-18
- **类型**：数据缺失
- **位置**：在 Perfetto 中识别 Camera 管线（L144-L159）
- **问题**：列出了 `queueBuffer`、`BufferTX - SurfaceView`、`binder transaction`、`dma_buf` 等观察点，但没有给一条可运行的 trace 配置、一个正常/异常样例或最小 SQL/时间基线。当前结论更多是经验列表，读者难以拿自己的 trace 逐项对照。
- **建议**：补一组最小抓取配置，加一条“稳定预览 vs Analysis 背压”的真实 case，至少给出一组帧间隔/回调归还节奏的判断基线；术语和查询口径尽量与 §14.9 对齐。

## [Task9 Deep Review] 18.18 PIP 与自由窗口渲染 — 2026-04-18
- **类型**：数据缺失
- **位置**：L121-L138 Trace 定位 / 在 Perfetto 中识别多窗口问题
- **问题**：Trace 指引只给出 `wm_task_moved`、`Transaction.apply`、`queueBuffer` 这类零散关键词，没有说明需要打开哪些数据源，也没有给出 App 主线程 Traversal、BufferQueue 背压、SurfaceFlinger FrameTimeline、WindowManager transition 等联合观察方法。读者很难凭这些描述真正复现 resize / PIP 卡顿分析。
- **建议**：补一组最小可执行分析路径，例如：WindowManager / SurfaceFlinger / FrameTimeline / app main thread / BufferQueue 各看什么 track；至少给 1 个正常案例和 1 个异常案例的文字版 Trace 描述。

## [Task9 Deep Review] 18.18 PIP 与自由窗口渲染 — 2026-04-18
- **类型**：数据缺失
- **位置**：L77-L79 / L128-L130
- **问题**：`系统通常限制 PIP 窗口的 CPU/GPU 优先级`、`Chrome 会预渲染几个常见尺寸的 Bitmap Cache` 两个判断没有版本、设备或源码依据，且都属于平台/应用特定策略，当前写法容易被读者误解为通用结论。
- **建议**：如果没有可验证材料，改成 `[待验证]` 或删去；更稳妥的写法应回到通用约束，如 HWC plane 竞争、resize 触发的重新 layout、BufferQueue 槽位背压。

## [Task9 Deep Review] 18.11 ANGLE（GLES-over-Vulkan 翻译层） — 2026-04-18
- **类型**：数据缺失
- **位置**：`在 Perfetto 中识别 ANGLE` 小节
- **问题**：当前只给了一个 `LIKE '%vk%'` 的 SQL 和几条泛化判断，没有说明需要打开哪些 trace 数据源、如何限定目标进程、也没有给出 native Vulkan / ANGLE 的对照样例。读者即使拿到 trace，也很难复现“先确认 driver selection，再做归因”的流程。
- **建议**：补一个最小可执行案例：按包切 ANGLE，记录 gfx + GPU renderstages + Vulkan 相关数据源，给出限定目标进程的 SQL，并把 `GL_RENDERER` 与 trace 结果放在一起对照。



## [Task6 Review] 18.21 EyeDropper API 与跨设备协作性能 — 2026-04-18

### ⚠️ 严重问题：全文 API 实现与真实 API 严重不符

经过 web search 验证，Android 17 EyeDropper API 确实存在，但章节中的实现描述**完全错误**。

**真实 API：**
- 基于 Intent：`Intent("android.intent.action.OPEN_EYE_DROPPER")`
- 通过 `registerForActivityResult` 接收结果
- 返回颜色通过 `intent.getIntExtra("android.intent.extra.COLOR", defaultColor)`
- 无需特殊权限（替代 MediaProjection 方案）

**章节中编造的内容：**
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

**处理建议：**
1. 全文重写，基于真实 API（Intent-based workflow）
2. 删除所有编造的类、方法、代码
3. 删除所有编造的性能数据
4. 删除"计划中的版本"整节
5. 补充与 MediaProjection 方案的真实对比
6. 如需 Perfetto 分析，需基于实际 trace 数据

- **类型**：需重写（全文）
- **位置**：全文
- **问题**：章节基于 AI 编造的 API 实现，与真实 Android 17 EyeDropper API 完全不符
- **建议**：基于官方文档和真实 API 重写。正确用法见 https://developer.android.com/reference/android/content/Intent#ACTION_OPEN_EYE_DROPPER
- **review 日志**：logs/review/2026-04-18-13-review.md

## [Task9 Deep Review] 1.8 Activity Manager Service 与性能分析 — 2026-04-18
- **类型**：数据缺失
- **位置**：L199-L201、L360-L362、L494-L496（3 处 Trace 占位图）
- **问题**：章节把 `oom_score_adj` 变化、冷启动关键节点、ANR Trace 特征都写成了口头描述，但三处核心位置只有“待补截图”占位，没有一段真实 Perfetto 片段或 SQL 输出。作为“与性能分析”章节，读者无法据此建立可复现的观察基线。
- **建议**：至少补 1 个冷启动 trace 和 1 个 ANR trace。每个例子给出 10-20 行 SQL 或关键 track 标注，包含 `android_logs` 的 `am_proc_start/am_anr` 与应用主线程 `bindApplication` / `doFrame` 的对照。

## [Task9 Deep Review] 18.20 链路分析方法论 — 2026-04-18
- **类型**：数据缺失 / 原理边界
- **位置**：L123-L125，L140-L141
- **问题**：`dur > 5000000` 与 `doFrame > 16.6ms` 被直接当作诊断阈值，但正文同时覆盖高刷与 VRR 场景。5ms/16.6ms 都缺少设备、刷新率和 Trace 版本边界，容易把 90Hz/120Hz 设备误判成“正常”。
- **建议**：把阈值改成“按当前刷新率/expected timeline 预算计算”，或明确标注“仅适用于 60Hz 固定刷新率示例”。

## [Task9 Deep Review] 18.20 链路分析方法论 — 2026-04-18
- **类型**：知识盲区
- **位置**：L176-L193「链路选型决策树」
- **问题**：决策树把 SurfaceView vs TextureView 的分叉压缩成“是否需要动画/变换/圆角”，遗漏了裁剪、滚动同步、Z 序、Inset、窗口 resize 同步等高频约束，容易把本该走 TextureView / SurfaceControl 的场景误导成 SurfaceView。
- **建议**：补一组“即使不要圆角也不该选 SurfaceView”的条件，或直接回连 §18.6 / §18.7 / §18.10 的选择矩阵。

## [Task9 Deep Review] 18.20 链路分析方法论 — 2026-04-18
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters` / L216-L218
- **问题**：正文把 §18.1 写成“本章的索引和入口”，但 frontmatter `related_chapters` 未包含 18.1，元数据导航与正文关系不一致。
- **建议**：在 `related_chapters` 中补入 `18.1`，必要时再补入 18.6 / 18.7 / 18.14 / 18.19 这些正文高频回连章节。


## [Task6 Review] 3.1 Input 事件分发全流程 — 2026-04-18
- **类型**：技术核实
- **位置**：Stale Event 丢弃机制（AIW-源码调研-2026-04-17）代码段
- **问题**：代码示例中使用了 mInboundQueue.hasEvent()、peekEvent()、removeEvent()、dropInboundConnection() 等方法，这些方法名在 AOSP android-14 的 InputDispatcher 中可能不存在或名称不同。该代码段标记为 AIW-源码调研，可能是基于理解重写的简化版本而非实际源码摘录。
- **建议**：Task 9 对照 AOSP android-14.0.0_r1 frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp，核实 STALE_EVENT_TIMEOUT 常量、isStale() 函数签名、以及 dispatchOnce() 中 stale event 的实际处理流程。如方法名不准确，由 Task 2B 更正为实际源码。
- **review 日志**：logs/review/2026-04-18-15-review.md
