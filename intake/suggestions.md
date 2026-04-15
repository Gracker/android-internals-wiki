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
