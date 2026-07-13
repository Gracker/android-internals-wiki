## [Task9 Deep Review] 16.1 Google 官方的性能优化思路 — 2026-07-13
- **类型**：知识盲区
- **位置**：混合编译策略章节
- **问题**：未充分说明 JIT+AOT+Profile-Guided 混合编译在不同设备类型（旗舰机/中端机/低端机）上的效果差异
- **建议**：补充不同设备类型下各编译策略的适用场景、性能收益对比和配置建议

## [Task9 Deep Review] 16.6 Android 16 云端 Profile 与 dexopt 安装优化 — 2026-07-13
- **类型**：版本差异
- **位置**：System Dexopt Manager 的分发侧边界章节
- **问题**：未充分说明 Android 17 中 ART Service 相比 Android 16 的 SDM (Secure Dex Metadata) 完整性校验增强
- **建议**：补充 Android 17 中 SDM 校验机制的具体变化和对编译行为的影响

## [Task9 Deep Review] 16.6 Android 16 云端 Profile 与 dexopt 安装优化 — 2026-07-13
- **类型**：知识盲区
- **位置**：安装耗时和启动收益章节
- **问题**：未涵盖 Cloud Profile 与 Baseline Profile 在低端设备上的优先级冲突处理
- **建议**：补充当设备本地 profile 和云端 profile 同时存在时的处理机制、优先级规则和兼容性说明

## [Task9 Deep Review] 16.6 Android 16 云端 Profile 与 dexopt 安装优化 — 2026-07-13
- **类型**：数据支撑
- **位置**：安装耗时和启动收益章节
- **问题**："评价方案时不要只用'安装快了多少'概括整套 Profile 体系"缺少具体数据支撑
- **建议**：补充典型场景（游戏/电商/社交应用）的安装耗时、TTID、TTFD 基准数据对比
## [Task6 Review] ch15 Android 性能优化研究方法论 — 2026-07-13
- **类型**：需重写
- **位置**：文末 `<!-- AIW-源码调研-2026-07-07 -->` 标记之间的 section（### 最新源码进展：Android 17 Power HAL AIDL v7 电池架构）
- **问题**：该段为研究素材直接粘贴，未融入章节叙述风格。具体表现：①笔记式标题和列表堆叠（"关键代码路径"、"三层统一管理模型"），与全章工程师对话式叙述风格断裂；②裸行号引用（"第1560-1627行"、"第2021行"）未转化为函数名+行为描述；③内容与 section 4.1 SoC 分层讨论有重叠但未交叉引用。
- **建议**：方案A——将 Power HAL AIDL v7 / HintManagerService / BatteryStatsService 三层模型内容融入 section 4.1 的 SoC 讨论中，作为 Android 17 架构升级的补充说明；方案B——独立为 section 4.5 并按 writing-guide 叙述风格重写。行号引用全部改为函数名+行为描述。
- **review 日志**：logs/review/2026-07-13-20-review.md

## [Task6 Review] 16.9 Android 17 SDM 安装编译流程性能 — 2026-07-13

### P0: 代码块大规模虚构（§2.1, §3.1, §3.2, §4.2, §5.1, §5.2, §6.1, §6.2）

- **类型**：需重写
- **位置**：8处代码块（占全文代码块的89%）
- **问题**：代码块使用真实AOSP文件路径和行号作为锚点（如 `PrimaryDexopter.java (line 191-225)`），但代码内容完全虚构。具体：
  - §2.1: `processProfileBasedDexopt()`, `ProfileBasedDexopt`, `applyProfileBasedOptimizations()`, `cacheOptimizationResults()` — 在AOSP中不存在
  - §3.1: `processPrimaryDexFiles()`, `DeviceBasedDexopt` 类, `applyDeviceBasedOptimizations()`, `storeOptimizationResults()` — 不存在
  - §3.2: `ArtFileManager` 中的 `optimizeFileAccessPattern()`, `warmUpFileCache()` 方法 — 不存在
  - §4.2: `ArtManagedInstallFileHelper.processDexMetadataFiles()` 中的 `applyMetadataBasedOptimizations()` — 不存在
  - §5.1: `ArtDaemon` 类, `InstallProcessor`, `optimizeInstallProcess()`, `BackgroundCompiler`, `optimizeResourceAllocation()` — 全部不存在
  - §5.2: `FileUtils::OptimizeFileAccess()`, `OptimizeFileAccessPattern()`, `WarmUpFileCache()` — 不存在
  - §6.1: `InstallSessionOptimizer` 类, `applyInstallOptimizations()`, `InstallExecutor` — 不存在
  - §6.2: `DexoptManager`, `CompilationRequestOptimizer` — 不存在
- **建议**：逐个核验AOSP源码，删除所有虚构代码。仅保留经源码验证的真实片段（如§4.1 DexMetadataHelper 已由Task2B验证）。无法验证的标注 `[待验证]` 或删除。
- **review 日志**：logs/review/2026-07-13-21-review.md

### P0: 第7-10节为空壳padding（§7, §8, §9, §10）

- **类型**：需重写
- **位置**：§7 实际应用场景、§8 性能监控与调试、§9 最佳实践、§10 未来展望
- **问题**：四个章节共约60行，全是无技术深度的列表式padding。§7只有6条泛泛建议无案例；§8提到的 `artctl`/`dexoptctl`/`pmctl` 工具需验证；§9是通用建议；§10纯猜测（"AI驱动的编译优化"）。违反writing-guide §五 反面教材第3条"概述式"。
- **建议**：§7-8需补充真实调试方法和Perfetto观察点（或标注TBD）；§9-10大幅压缩或删除。
- **review 日志**：logs/review/2026-07-13-21-review.md

### P0: 章节结构违反writing-guide类型A要求（全文结构）

- **类型**：需重写
- **位置**：全文
- **问题**：章节应遵循writing-guide.md类型A（机制原理篇）结构，但缺失：
  - "为什么要了解SDM"动机段
  - "在Perfetto/工具中的表现"段
  - "与其他机制的关系"段
  - "常见问题与误区"段
  - 整体为列表式罗列而非叙述式讲解
- **建议**：按类型A重组结构。
- **review 日志**：logs/review/2026-07-13-21-review.md

### P1: 性能数据无来源（§2.2）

- **类型**：需补充素材
- **位置**：§2.2 云端编译性能提升
- **问题**：编译时间减少40-60%、安装大小减少15-25%、启动时间减少30-45%——无数据来源。Task2B已补充验证方法步骤（改进），但数据本身的出处仍未解决。
- **建议**：补充来源或标注为"预估值"。
- **review 日志**：logs/review/2026-07-13-21-review.md

### P1: 工具引用需验证（§8.2）

- **类型**：需确认
- **位置**：§8.2 调试工具
- **问题**：`dexoptctl` 和 `pmctl` 可能是虚构工具名。
- **建议**：验证工具是否存在；补充实际命令如 `pm art dump`、`dumpsys package dexopt`。
- **review 日志**：logs/review/2026-07-13-21-review.md

### L1: 禁用词"链路"（标题及正文）

- **类型**：禁用词
- **位置**：标题(×2)、正文(原4处，已修1处)
- **问题**：禁用词"链路"出现在章节标题和正文中。
- **建议**：标题中的"链路"→"流程"，同步更新SUMMARY.md。正文剩余3处（§1.3表格、§10.1列表项）一并修改。
- **处理状态**：正文已修1处，标题待Task2B处理（涉及SUMMARY.md交叉引用）。
- **review 日志**：logs/review/2026-07-13-21-review.md
