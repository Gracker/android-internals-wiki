## [Task6 Review] 1.23 Android Staged Install 与安装原子性性能 — 2026-06-30
- **类型**：需补充素材
- **位置**：锚点2（安装性能瓶颈定位）
- **问题**：性能数据缺少设备实测支撑，多处使用定性分析框架
- **建议**：在具体设备上采集完整的安装耗时分解数据，替换现有的定性分析框架
- **review 日志**：logs/review/2026-06-30-14-review.md

## [Task6 Review] 1.23 Android Staged Install 与安装原子性性能 — 2026-06-30
- **类型**：需确认
- **位置**：锚点4（安装性能的 ART/Profile 分发边界）
- **问题**：Cloud Profiles 在安装时的使用边界缺乏源码验证
- **建议**：在 AOSP android-17.0.0_r1 中查找相关实现代码，验证 Profile 引导编译的具体机制
- **review 日志**：logs/review/2026-06-30-14-review.md

## [Task6 Review] 1.24 ResourcesManager 与 Configuration 变更性能 — 2026-06-30
- **类型**：需补充素材
- **位置**：多处（recreate 工作量、内存占用估算）
- **问题**：Configuration 变更的性能量级和 Resources 内存占用缺少实测数据
- **建议**：在具体设备上采集完整的 Perfetto trace 和 heap dump 数据，支撑性能估算
- **review 日志**：logs/review/2026-06-30-14-review.md

## [Task6 Review] 1.24 ResourcesManager 与 Configuration 变更性能 — 2026-06-30
- **类型**：需重写
- **位置**：Compose 状态管理部分
- **问题**：Compose 状态管理边界描述不够清晰，缺少行为验证
- **建议**：通过具体代码示例验证不同边界的状态保留行为，增强描述的准确性
- **review 日志**：logs/review/2026-06-30-14-review.md

## [Task2B] 1.23 — blocked-need-measurement — 2026-06-30 14:54
- **状态**：blocked
- **来源**：logs/review/2026-06-30-14-review.md (L3 内容深度)
- **问题**：
  1. 锚点2 "安装性能瓶颈定位" — 性能数据为定性分析框架，缺少设备实测支撑
  2. 锚点4 "Cloud Profiles 分发边界" — 该段在 Task9 auto-fix 后已正确标注 Cloud Profiles 不属于 AOSP 安装框架内建能力，当前表述准确
- **阻塞原因**：需在目标设备上采集完整的 Perfetto trace（含 installPackage/dexopt commit 等 slice）后，用实测数据替换定性分析框架。AI 无法编造实测数据。
- **前端状态**：pipeline_stage: task6_pending, frontmatter 重复键已清理

## [Task2B] 1.24 — blocked-need-measurement — 2026-06-30 14:54
- **状态**：blocked
- **来源**：logs/review/2026-06-30-14-review.md (L3/L4 内容深度与活人感)
- **问题**：
  1. "Activity recreation 的性能代价"表格 — 数据为工程估算，缺少设备实测支撑
  2. "Resources 缓存与内存占用"内存估算是 — 缺少 heap dump 验证
  3. "Compose 状态管理边界" — 在 Task9 auto-fix 后已明确区分 recomposition/Activity recreate/process death 三个边界，当前表述准确
- **阻塞原因**：需在目标设备上采集 Perfetto trace + heap dump + Compose 实战验证。AI 无法编造实测数据。
- **前端状态**：pipeline_stage: task6_pending, frontmatter 重复键已清理


## [Task2A Gap Mining] 无合格候选 — 2026-07-01 01:12

已检查方向（评分均 < 14，无需创建新章节）：
- Media3/ExoPlayer 缓冲管理 → 已在 8.8/18.23/18.24 覆盖
- AlarmManager 精确闹钟功耗 → 已在 25.20/11.2/5.8 覆盖
- Foldable/Jetpack WindowManager → 已在 2.28/2.29/22.14/22.27 覆盖
- SystemUI/StatusBar/NavBar 渲染 → 已在 7.13 覆盖
- NotificationManagerService → 已在 8.14/9.6 覆盖
- HealthConnect → 非性能核心议题
- Notification Trampoline 限制 → 素材不足 (<14)
- Intent Resolution 性能 → 素材不足 + 读者需求低 (<14)
- APEX 模块化性能 → 素材不足 + 开发者不直接接触 (<14)
- Dream/Screensaver 性能 → 过于冷门 (<8)
- LiveData/DataBinding 性能 → 被 Compose 替代，时效性低 (<10)
- SyncAdapter 废弃迁移 → 已在 11.3/11.04 覆盖
- Per-app Language 性能 → 已在 1.24/8.3 覆盖
- ContentProvider applyBatch → 已在 1.10/1.30/1.31 覆盖
- Compose Multiplatform/KMP → 已在 22.15/24.17 覆盖
- Room KMP → 已在 24.17 覆盖
- Compose Stability Config → 已在 18.2/22.20 覆盖
- 76 项系统服务扫描（TelephonyManager/WifiManager/NFC/Matter/Thread/UWB 等）→ 大部分非性能核心议题

结论：全书 547 节，覆盖度已饱和。后续缺口挖掘应转向：
1. 已有章节的深度增强（Task 2B 职责）
2. 新版本发布后再行挖掘（如 Android 18 DP）
3. Clippings 参考书的知识点级缺口（比章节级更细粒度）


## [Task2A Gap Mining] 无合格候选 — 2026-07-01 03:08

本轮复查结果（基于上一轮 01:12 挖掘的二次验证）：

**Phase 0**: 10 个 draft 章节全部 >15 行有效内容，无空 draft 可加工
**Phase 0.5**: Task2B backlog = 0，允许挖掘
**Phase 1**: 复查 17 个方向，均 < 14 分

新增复查方向（Clippings 知识点级交叉验证）：
- FD 监控 / 线程监控 → 已在 ch20「线程与 FD 资源监控治理」覆盖
- ASM 字节码插桩 → 已在 ch26「编译期字节码插桩与监控自动化」覆盖
- Native Hook / Native Backtrace → 已在 ch20「Native 堆栈回溯与符号化机制」覆盖
- 虚拟内存 / 缓存优化 → 已在 ch23 各节覆盖
- dex/so 体积 / 插件化 → 已在 ch25 APK 瘦身系列覆盖
- ShareSheet 性能 → 素材不足 + 非性能核心 (<12)
- 截图检测性能 → 冷门 + 无 AOSP 公开 API 支撑 (<8)

结论：全书 510 节，覆盖度确认饱和。与上一轮结论一致。
下一可行动方向：等待 Android 18 DP 或针对已有章节做知识点级深度增强（Task 2B）。


## [Task2A Gap Mining] 无合格候选 — 2026-07-01 05:11

本轮第三轮复查（Phase 0 → 0.5 → 1 完整流程）：

**Phase 0**: 0 个空 draft（所有 9 个 draft 章节 >15 行有效内容）
**Phase 0.5**: Task2B backlog = 0，允许挖掘
**Phase 1**: 全书 495 节，覆盖度确认饱和

与前两轮（01:12, 03:08）结论一致：
- 无新增 research-feeds（最新仍为 2026-04-14）
- 无新增 daily-info 中的 Android 相关内容
- 无 Android 18 DP 或新版本素材
- Clippings 三本参考书的知识点已在 ch20-ch26 各节中结构化覆盖

结论：全书覆盖度三次确认饱和。可行动方向不变：
1. 已有章节深度增强（Task 2B）
2. 等待 Android 18 DP
3. Clippings 知识点级缺口（比章节级更细粒度，属于 Task 2B 职责）

## [Task6 Review] 1.4 Binder IPC 机制与性能影响 — 2026-07-01
- **类型**：需重写 / 需确认 / 需补充素材
- **位置**：参考资料之后的全部注入块（~234行）；全文源码锚点
- **问题**：
  1. 6个DeepResearch注入块以原始研究笔记形式堆叠在参考资料之后，含禁用词（闭环×5、链路×4）、DeepResearch元数据header（注入时间/价值/关联），风格与主体正文完全不一致
  2. 主体与注入块在oneway spam、frozen process、priority inheritance、事务队列等主题大量重复
  3. 源码锚点引用android-16.0.0_r1/r4，未锚定android-17.0.0_r1（版本基线要求）
- **建议**：
  1. 将注入块中有增量价值的技术内容（如tracepoints完整列表、red-black tree查找O(log n)开销量化、epoll worker显式唤醒机制、用户态批处理syscall开销数据）融入主体对应段落
  2. 删除注入块元数据header（注入时间/价值/关联DeepResearch等）
  3. 删除与主体重复的内容
  4. 由Task 9对照android-17.0.0_r1验证源码路径，更新frontmatter的last_verified_against
- **review 日志**：logs/review/2026-07-01-06-review.md

## [Task9 Deep Review] 1.4 Binder IPC 机制与性能影响 — 2026-07-01
- **类型**：数据缺失
- **位置**：参考资料后的 DeepResearch 注入块（用户态批处理、唤醒延迟、红黑树查找、surfaceflinger 线程池调优等量化段落）
- **问题**：多处给出 70-150ns、15-30ns、5-50μs、P99 1.5ms→200μs、syscall 100-400μs→~4μs 等数值，但没有设备型号、trace/benchmark、内核配置和复现方法。
- **建议**：整合正文时要么补充可复现测量条件和 trace 证据，要么降级为“源码路径提示/理论估算”，不要作为 Android 17 性能结论。
- **review 日志**：logs/deep-review/2026-07-01-06-deep-review.md


## [Task2A Gap Mining] 无合格候选 — 2026-07-01 08:09

本轮第四轮复查（Phase 0 → 0.5 → 1 完整流程）：

**Phase 0**: 0 个空 draft（所有 7 个 draft 章节 >15 行有效内容，最小 35 行）
**Phase 0.5**: Task2B backlog = 1，允许挖掘
**Phase 1**: 全书 510 节，覆盖度确认饱和

增量复查内容：
- daily-info 2026-07-01：7 条增量扫描全部已映射到现有章节（Binder IPC/SP ANR/bootanalyze/AppFlow/LMKD/Linux 6.10/Perfetto）
- Clippings 三本参考书（24+20+59=103 篇）知识点交叉验证：ch20-ch26 已结构化覆盖
- 25 个 unknown 状态文件检查：1 个 preface <15 行（target-audience，非性能章节），其余均有实质内容
- 无新增 research-feeds（最新仍为 2026-04-14）
- 无 Android 18 DP 或新版本素材

结论：全书覆盖度四轮确认饱和（与前序 01:12/03:08/05:11 一致）。可行动方向不变：
1. 已有章节深度增强（Task 2B）
2. 等待 Android 18 DP
3. Clippings 知识点级缺口（比章节级更细粒度，属于 Task 2B 职责）


## [Task2A Gap Mining] 无合格候选 — 2026-07-01 09:08

本轮第五轮复查（Phase 0 → 0.5 → 1 完整流程）：

**Phase 0**: 0 个空 draft（所有 7 个 draft 章节 >15 行有效内容，最小 35 行）
**Phase 0.5**: Task2B backlog = 1，允许挖掘
**Phase 1**: 全书 532 节，覆盖度确认饱和

增量复查内容：
- daily-info 2026-07-01 新增条目（代码坏味道重构对能耗影响论文、FlexServe TrustZone LLM）均已映射到现有章节（ch05 功耗/ch14 AI 移动端）
- 无新增 research-feeds（最新仍为 2026-04-14）
- 无 Android 18 DP 或新版本素材
- 前四轮（01:12/03:08/05:11/08:09）已覆盖 76+ 系统服务扫描、Clippings 103 篇交叉验证、25 个 unknown 文件检查

结论：全书覆盖度五轮确认饱和（532 节，334 finalized + 164 ready-for-review + 7 draft + 25 unknown + 2 其他）。
可行动方向不变：
1. 已有章节深度增强（Task 2B）
2. 等待 Android 18 DP
3. Clippings 知识点级缺口（比章节级更细粒度，属于 Task 2B 职责）

## [Task2A Gap Mining] 已检查方向记录 — 2026-07-01 19:16

本轮知识缺口挖掘已检查以下方向，未发现评分 ≥ 14 的合格候选：

### 素材驱动（source-index.json + research-feeds）
- Perfetto v53/v54 新特性 → 已覆盖于 13.14/13.17/13.20/13.21
- Frame Timeline API 33 → 已覆盖于 2.30/2.32
- Compose Pausable Composition → 已覆盖于 2.28
- AudioFlinger FAST Mixer / AAudio MMAP → 已覆盖于 1.16
- Android 17 后台音频强化 → 已覆盖于 25.17
- View hierarchy measure/layout → 已覆盖于 7.12

### Clippings 参考书驱动
- 虚拟内存优化（线程栈/多进程 VSS） → 已覆盖于 23.6
- Native 内存优化（so 库/malloc） → 已覆盖于 23.3
- 缓存优化（冷热分离） → 已覆盖于 24.6/7.10
- GC 抑制提升启动速度 → 已覆盖于 21.13
- Java Heap 内存优化 → 已覆盖于 23.4
- CPU 优化/线程池 → 已覆盖于 5.18/21.16

### AOSP 结构对照
- TelephonyManager/Modem 交互 → 太边缘
- Drag-and-Drop → 素材不足
- Project Mainline/APEX 性能影响 → 素材不足
- Companion Device Manager → 素材不足

### 官方文档对照
- developer.android.com/topic/performance 全部 topic → 均有对应章节
- Android 17 行为变更 → 逐项对照均有覆盖

### 章节深挖
- Compose Navigation/Text/并发安全 → draft 已存在
- XTrace/内存跟踪 API → draft 已存在

### 下一轮建议探索方向
- Android 17 Compose Material 3 Expressive 组件性能特征
- Android XR 性能发展
- Kernel 6.12 新特性对性能的影响
- GenAI 应用端到端性能链路
- Compose Multiplatform Android 性能边界

## [Task2A Gap Mining] 无合格候选 — 2026-07-01 21:16

本轮第七轮复查（Phase 0 → 0.5 → 1 完整流程）：

**Phase 0**: 0 个空 draft（所有 19 个 draft 章节 >15 行有效内容，最小 35 行）
**Phase 0.5**: Task2B backlog = 1，允许挖掘
**Phase 1**: 全书 544 节，覆盖度七轮确认饱和

本轮专项评估上轮建议的 5 个新方向：
1. Compose Material 3 Expressive 组件性能特征 — 12/20 ❌（素材不足，与ch22重叠）
2. Android XR 性能发展 — 8/20 ❌（不在android-17版本边界内）
3. Kernel 6.12 新特性对性能的影响 — 13/20 ❌（Binder/memory/EAS/DVFS均已在各自领域章节覆盖，独立章节将违反深度原则）
4. GenAI 应用端到端性能链路 — 13/20 ❌（已被22.09+23.24+5.27三节联合覆盖）
5. Compose Multiplatform Android 性能边界 — 11/20 ❌（已在22.15/24.17覆盖）

结论：全书覆盖度七轮确认饱和（与前序 01:12/03:08/05:11/08:09/09:08/19:16 一致）。
可行动方向不变：
1. 已有章节深度增强（Task 2B）
2. 等待 Android 18 DP
3. Clippings 知识点级缺口（属于 Task 2B 职责）
4. 新设备实测数据补充（需人工采集）

## [Task6 Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-07-01

### Issue 1: [需重写] oneway 三路排队路由三处重复
- **类型**：需重写
- **位置**：Section 6 / Section 10.2 / Section 13.A.4
- **问题**：同一套三路排队路由机制（thread todo / proc->todo / node->async_todo）在三个位置重复展开，造成冗余。读者在不同位置读到相同内容会感到混乱。
- **建议**：在 section 6 保留完整首次描述，section 10.2 和 13.A.4 简化为引用 + 仅补充差异点。

### Issue 2: [存疑] 「Android 17 引入了...完整优先级调度体系」表述
- **类型**：存疑
- **位置**：Section 11.1
- **问题**：正文称「Android 17 引入了基于 FLAT_BINDER_FLAG 的完整优先级调度体系」，但附录 A.5 版本差异表显示该机制从 Android 12 起逐步演进（Android 12 引入 BR_FROZEN_REPLY，14 引入 TF_UPDATE_TXN 和三态状态机，16 引入 node->min_priority）。「引入了完整体系」的表述不够准确。
- **建议**：改为「Android 17 在既有优先级调度机制上强化了 vendor hook 介入和 binder_supported_policy 校验」。

### Issue 3: [需确认] Section 11.3 标题与内容不匹配
- **类型**：需确认
- **位置**：Section 11.3「多进程路由策略优化」
- **问题**：标题为「多进程路由策略优化」，但正文内容是 BR_FAILED_REPLY / BR_DEAD_REPLY / BR_FROZEN_REPLY 错误码处理和线程池动态扩容（spawnPooledThread），与「路由策略」不匹配。
- **建议**：修正标题为「错误处理与线程池动态扩容」，或重写内容以匹配标题。

### Issue 4: [存疑] 内核代码注释格式
- **类型**：存疑
- **位置**：Section 11.1 / 11.2 代码块
- **问题**：C 代码块中带有「// 1. 优先级标志位解析」「// 2. 异步空间隔离检测」等编号注释，这些注释风格与 AOSP 源码不一致，疑似 Task 2 加工时添加。
- **建议**：核实是否为源码原文。如为加工添加，删除编号注释或改写为正文说明。

- **review 日志**：logs/review/2026-07-01-23-review.md

## [Task2A Gap Mining] 3 个合格候选已录入 — 2026-07-02 01:04

本轮第八轮挖掘，基于 2026-07-01 新注入的技术文章 intake（43 篇 Android 17 系统新特性）。

**与前 7 轮的区别**：前 7 轮（01:12~21:16）评估的方向是系统服务扫描、Clippings、XR/Kernel/GenAI 等。
本轮首次评估 21:16 注入的技术文章素材，发现 3 个前轮未检查的合格缺口：

1. ✅ **14.24 Android 17 simpleperf 微架构级性能采样与工作流增强** — 17/20
   - ARM SPE (SPERecorder/SPEDecoder), TRBE (TMRecorder), --background, --app, Qualcomm PMU, kernel module ETM AutoFDO
   - 素材：6 篇技术文章 | 现有 14.02-simpleperf.md (finalized) 未覆盖这些 Android 17 新特性

2. ✅ **14.25 Android 17 eBPF 性能可观测性程序矩阵扩展** — 15/20
   - cyclePerUid, dmabufIter, kernelwakelockduration, locks, cpucycleperuid Rust FFI
   - 素材：5 篇技术文章 | 现有 14.10-ebpf (finalized, verified against android-16) 未覆盖

3. ✅ **9.10 Android 17 ANR 预警回调与类型枚举** — 17/20
   - AnrTypes, AnrWarningResult, IAnrWarningCallback.aidl
   - 素材：1 篇技术文章（但 ANR 相关性极高）| ch09 全部 finalized，未覆盖预警系统

**已检查但 <14 分的方向**：
- pmgd 进程守护 → 系统守护进程，开发者不直接接触 (10/20)
- M_PURGE_FAST → bionic 细节，应更新 1.40-bionic (10/20)
- reallocarray/bionic env/wchar SIMD → bionic 内部变更 (8-10/20)
- SurfaceFlinger Lockless (MagicRingBuffer/RPointer/BitSet) → SF 内部基础设施 (12/20)
- RemoteCompose 进程外 UI → 太新，采用率低 (12/20)
- ProfilingTrigger → 已在 14.07/8.16 覆盖 (不单独计分)
- PCC 私有计算 → 非性能核心 (8/20)
- AppFunctions AI 调用 → 非性能核心 (8/20)
- Parcel targetSdk37 收紧 → 兼容性而非性能 (10/20)
- static final 不可修改 → 兼容性而非性能 (10/20)
- amemdiff 工具 → 工具使用，素材单一 (10/20)
- BinderObserver/BinderNetlink → 应更新 Binder 章节 (12/20)
- AppJankTest → 测试应用 (8/20)
- Winscope Angular 迁移 → 构建工具 (6/20)
- AISealHostService → 语义不明 (6/20)

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-07-02
- **类型**：源码准确性
- **位置**：要点 / Section 2 中“调用方线程零阻塞”
- **问题**：`waitForResponse(nullptr, nullptr)` 仍需等待内核返回 `BR_TRANSACTION_COMPLETE` / `BR_TRANSACTION_PENDING_FROZEN` 等回执；oneway 不等待对端执行和 `BR_REPLY`，但不宜写成绝对零阻塞。
- **建议**：后续精修时将“零阻塞”统一改为“不等待对端执行结果 / 不等待 `BR_REPLY`”，并保留 `BR_TRANSACTION_COMPLETE` 快路径边界。
