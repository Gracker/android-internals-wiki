## [Task9 Deep Review] 14.16 Layout Inspector 与 ViewDebug 布局调试 — 2026-06-28
- **类型**：原理链完整性
- **位置**：invalidate 与 measure/layout 关系说明
- **问题**：未充分解释 invalidate 触发后的完整调用链，特别是与 measure/layout 阶段的因果关系
- **建议**：补充 invalidate → PFLAG_DIRTY → Choreographer callback → scheduleTraversals → performMeasure/performLayout 的完整流程说明

## [Task9 Deep Review] 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源 — 2026-06-28
- **类型**：数据支撑
- **位置**：heap dump 性能影响数据
- **问题**：章节中提到的 heap dump 暂停时长和 I/O 压力数据缺少实际测量来源和实验条件说明
- **建议**：补充具体的测试环境、堆大小范围、实际测量数据来源，或注明数据来自第三方研究报告

## [Task9 Deep Review] 14.22 HPROF Heap Dump 管线与 Perfetto java_hprof 数据源 — 2026-06-28
- **类型**：交叉引用一致性
- **位置**：§19.3 章节引用
- **问题**：章节中引用 §19.3 讲述 KOOM fork-dump，但该章节编号可能不存在或内容不符
- **建议**：验证 §19.3 章节是否存在并包含相关内容，或修正为正确的章节编号## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：源码准确性
- **位置**：IPCThreadState.cpp:1056-1104 和 IPCThreadState.cpp:1246-1362
- **问题**：文中所引用的行号与 Android 17 实际源码位置不符，transact 函数实际在 1100-1150 行左右，talkWithDriver 函数在 1300-1420 行左右
- **建议**：修正源码引用行号以确保开发者能准确定位到对应代码

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：原理完整性
- **位置**：2.3 节冻结回执机制
- **问题**：缺少 BR_TRANSACTION_PENDING_FROZEN 投递后解冻时机的详细说明
- **建议**：补充解冻时机、内核队列管理机制、解冻后的投递优先级等完整流程说明

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：版本差异
- **位置**：7.1 节 Android 版本对比
- **问题**：Android 16 到 Android 17 的差异描述过于简略，缺少具体的 API 或行为变化
- **建议**：补充具体的 API 变化、默认配置调整、新引入的优化措施等详细对比

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：数据支撑
- **位置**：5.1 节性能特征表格
- **问题**：多个关键性能数据标注 "[待补充]"，影响技术结论可信度
- **建议**：补充 oneway vs 同步调用的实际延迟对比数据、批处理模式下 syscall 减少量、frozen sync 立即返回错误 vs 普通同步等待卡住的 ANR 次数对比等量化数据

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：数据支撑
- **位置**：8.1 节 Perfetto Trace 表现
- **问题**：缺少实际的 Perfetto Trace 截图案例
- **建议**：补充实际的 Perfetto Trace 截图，展示 oneway vs 同步调用的 trace 表现差异

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：知识盲区
- **位置**：章节整体
- **问题**：缺少 Binder 事务优先级机制在 Android 17 中的实现细节
- **建议**：补充事务优先级机制说明，包括高优先级事务的调度策略和低延迟保障措施

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28

- **类型**：知识盲区
- **位置**：章节整体
- **问题**：未讨论跨进程同步机制（如 Barrier/CountDownLatch）与 Binder oneway 的交互
- **建议**：补充跨进程同步机制与 Binder oneway 的交互说明，包括潜在的死锁风险和最佳实践## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：原理链完整性
- **位置**：第2节 oneway 调用与异步语义
- **问题**：解释了 oneway 调用如何工作，但未说明为什么 Android 系统需要同时支持 oneway 和同步调用
- **建议**：补充架构设计决策推理，说明同步和异步调用的适用场景、性能权衡和设计哲学

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：机制解释深度
- **位置**：第4节内核批处理流水线
- **问题**：批处理性能提升的解释过于表面，缺少对 syscall 开销的具体分析
- **建议**：深入分析 syscall 开销的构成，包括上下文切换、内核态/用户态切换成本，以及批处理如何减少这些开销

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：交叉引用一致性
- **位置**：第9节关联章节
- **问题**：文中提到章节 1.4 "Binder 基础架构"，但可能需要指向更具体的 BC/BR 协议章节
- **建议**：验证交叉引用的准确性，确保指向最相关的章节内容

## [Task9 Deep Review] 1.25 Android 17 Binder IPC 异步机制与批处理流水线 — 2026-06-28
- **类型**：术语一致性
- **位置**：全文
- **问题**：不同章节中对 "binder 线程" 和 "IPC 线程" 的术语使用可能存在差异
- **建议**：统一术语使用，明确 binder 线程和 IPC 线程的定义和关系
## [Task2A Gap Mining] 已检查方向记录 — 2026-06-28 09:11

**结论：本轮未发现评分 ≥ 14 的知识缺口，跳过新章节创建。**

### 已检查方向（避免重复挖掘）

#### AOSP 子系统覆盖检查
- ✅ frameworks/base/ 核心服务（AMS, PMS, WMS, InputFlinger, etc.）— 全部已覆盖
- ✅ system/ 核心组件（lmkd, vold, netd, installd）— 全部已覆盖
- ✅ packages/modules/（DNSResolver, Bluetooth, Media）— 主要模块已覆盖
- ✅ frameworks/native/（Binder, SurfaceFlinger, etc.）— 已覆盖

#### Android 17 新特性覆盖检查
- ✅ Binder 异步批处理（1.25/1.27）、DeliQueue（1.26/1.28）
- ✅ MemoryLimiter（4.17）、App Hibernation（5.24）
- ✅ 16KB Page Size（4.7/20.13）、Edge-to-Edge（2.26）
- ✅ Predictive Back（3.12/22.13）、Desktop Mode（2.20/22.14）
- ✅ Private Space（17.7）、App Archiving（1.20）
- ✅ AVF/pKVM（1.32）、MTE（20.11）
- ✅ JobScheduler 五维节流（5.23）、Low Power Standby（5.25）
- ✅ HWUI Vulkan 多队列（18.26）、WebGPU（18.27）

#### 官方文档覆盖检查
- ✅ ADPF（5.9/8.19/25.11/25.16）、Baseline Profiles（8.7/21.4/19.15）
- ✅ ProfilingManager（8.10/8.16/14.7/19.16）
- ✅ ApplicationExitInfo（26.9）、ApplicationStartInfo（26.13）
- ✅ Photo Picker（24.13）、MediaStore（24.12）
- ✅ Compose 性能（7.7/22.3/22.15-22.28/18.25）

#### 新兴方向评估（均 < 14 分）
- ❌ Wear OS 性能（8/20）— 素材不足，受众窄
- ❌ Android TV 性能（7/20）— 素材不足
- ❌ KMP 性能（12/20）— 素材丰富度不够
- ❌ io_uring on Android（10/20）— 缺 Android 特定素材
- ❌ VPN 性能（8/20）— 太窄
- ❌ OTA/Update Engine 性能（7/20）— 超出本书范围
- ❌ File-Based Encryption 性能（9/20）— 已有稳定文档，缺新素材
- ❌ Shader 编译/纹理流式传输性能（9/20）— 主要面向游戏开发者
- ❌ Kotlin Multiplatform 性能（12/20）— 最接近但素材不够

#### 参考书交叉验证
- ✅ 《Android 应用稳定性剖析与优化》15 篇 — 全部主题已映射到 ch20（18 节）
- ✅ 《Android 性能优化》16 篇 — 全部主题已映射到 ch21-ch25
- ✅ 《线上疑难问题》59 篇 — 全部主题已映射到 ch26 及各章节案例

### 当前全书规模
- 总小节：545（finalized: 334, ready-for-review: 144, draft: 40, 其他: 27）
- Part 5 覆盖：ch20(18) + ch21(17) + ch22(30) + ch23(17) + ch24(20) + ch25(23) + ch26(23) = 148 节
- 空 draft（<15行）：0 个
- 小 draft（<60行有 outline）：20 个 → 这些是 Phase 2 的加工目标

## [Task2A 知识缺口挖掘] 2026-06-28 缺口挖掘方向记录

**本轮扫描结果**: 无空 draft 章节需加工，Task2B backlog = 0，进入 Phase 1 缺口挖掘。
**本轮挖掘结论**: 未发现评分 ≥ 14 的知识缺口。

### 已检查方向（避免下轮重复）

1. **source-index.json 高质量未映射素材**: 0 条（索引为空）
2. **research-feeds 近期研究**: 检查 5 个文件，已全部映射到现有章节（Perfetto v53/v54, Compose Pausable, FrameTimeline）
3. **daily-info 近期信息**: 检查 suggestions.md 和 incremental-scan，无新缺口方向
4. **research-gaps.md 已知盲区**: 5 条记录，全部针对**已有章节的深化**（非新章节创建）
   - 15.x Perfetto 版本准确性
   - 6.5 SharedPreferences Android 17 验证
   - 16.8 AppFlow LMKD 兼容性
   - 16.7 系统启动 Android 17 新特性
   - 14.22/1.25 Deep Review 发现的细节
5. **AOSP 系统服务覆盖率**: 检查 frameworks/base/services/core 下核心服务
   - ActivityManagerService ✓, PackageManagerService ✓, WindowManagerService ✓
   - NotificationManagerService ✓ (partial), InputManagerService ✓
   - DisplayManagerService ✓, SensorService ✓, ConnectivityService ✓
   - AudioService ✓ (1.16), Keystore2 ✓ (8.12)
   - AppOpsService: 3 处提及（非核心性能瓶颈）
   - UsageStatsService: 低性能影响
6. **AOSP packages/modules 覆盖率**: Bluetooth ✓, WiFi ✓(partial), Media ✓, Networking ✓
7. **官方文档对照**: web_fetch 对 developer.android.com 不可达，基于已有知识分析
8. **章节稀疏度分析**: 
   - Ch6 (8节), Ch11 (8节), Ch12 (8节) — 但这些章节主题本身就相对集中
   - 所有章节均有足够覆盖
9. **Topic-level 覆盖率扫描**: 检查 200+ 技术关键词
   - 零覆盖项: AppSearch, Vulkan Pipeline Cache（概念已覆盖）, Speech/TTS（低影响）
   - 低覆盖项: BLE Scanning, AudioRecord, Protocol Buffers, kotlinx.serialization 等 — 均在现有章节有概念覆盖
10. **Clippings 参考书对照**: 三本参考书（稳定性15篇、性能优化16篇、线上疑难59篇）内容已全部映射到现有章节
11. **Android 17 新特性全覆盖检查**: 
    - DeliQueue ✓, Binder async ✓, MemoryLimiter ✓, App Hibernation ✓
    - Low Power Standby ✓, FGS Type ✓, Native DCL ✓, Keystore Quota ✓
    - Excessive CPU Kill ✓, Background Audio ✓, Network Quota ✓
    - ECH/DomainEncryption ✓, allow-while-idle Alarm ✓
12. **Draft 章节分析**: 39 个 draft 章节，其中 14 个 < 50 行 — 这些需要 Task2B 加工而非新建

### 统计
- 全书总小节: 521
- 已完成 (finalized): 296
- Ready for review: 141
- Draft: 43 (其中 14 个 < 50 行，0 个 < 15 行)
- 空章节: 0

### 建议下一步
1. 优先让 Task2B 处理 14 个 thin draft 章节（< 50 行内容）
2. 让 Task9 Deep Review 继续处理 ready-for-review 章节
3. 下一轮 Task2A 可探索: Android 18 预览特性（如公开）、或聚焦已有章节的扩展锚点深挖

## [Task2A Gap Mining] 已检查方向记录 — 2026-06-28 12:04

**结论：本轮未发现评分 ≥ 14 的知识缺口，跳过新章节创建。**

### 补充检查方向（在 09:11 轮基础上新增）

#### AOSP 系统服务零覆盖检查
对 frameworks/base/services/core 下 50+ 系统服务进行全库搜索，以下服务 mentions=0：
- ❌ VibratorService / Haptic Feedback Performance（9/20）— VibrationEffect/HapticGenerator 细分领域
- ❌ AccountManagerService（5/20）— 非性能瓶颈
- ❌ BackupManager / Backup/Restore（6/20）— 非性能关键路径
- ❌ VpnManagerService / VPN Performance（10/20）— 网络优化边缘
- ❌ StatusBarService（7/20）— SystemUI 覆盖在 7.13

#### 新兴主题零覆盖检查
- ❌ Terminal Emulator / Linux Terminal（8/20）— Android 16+ 新增但过于小众
- ❌ AppSearch / AppSearch API（9/20）— Jetpack 库，系统性能影响低
- ❌ Android Studio Bot / Gemini IDE（5/20）— 开发工具非运行时性能

### 本轮统计
- 全书总小节：521（finalized: 329, ready-for-review: 141, draft: 43, 其他: 8）
- 空 draft（<15 有效行）：0 个
- Thin draft（15-60 行）：39 个 — 需 Task2B 加工
- Task2B backlog：0（已清空）
- 知识缺口 ≥14 分：0 个

### 建议
1. 下一轮可探索方向已趋枯竭，建议聚焦：
   a. Task2B 加工 39 个 thin draft（15-60 行）
   b. Task9 Deep Review 处理 ready-for-review 章节
   c. Part 5 参考书交叉验证已有章节
2. 如有新 DeepResearch 材料，可在后续轮次中重新评估

## [Task2A Gap Mining] 已检查方向记录 — 2026-06-28 13:12

**结论：本轮未发现评分 ≥ 14 的知识缺口，跳过新章节创建。**

### 本轮新增检查方向（在 12:04 轮基础上进一步扩展）

#### 深度零覆盖率扫描（100+ 关键词）
对全书 `src/` 全文进行 100+ 技术关键词的零覆盖率扫描，覆盖以下维度：

1. **Android 17 行为变更/新特性（补充检查）**
   - ✅ Notification trampoline restrictions — 非性能核心
   - ✅ FGS timeout/type — 已覆盖（5.17/25.13）
   - ✅ 3p-apps-standby — 已覆盖（5.21/5.23）

2. **AOSP 子系统零覆盖（补充检查）**
   - ❌ VibratorService（9/20）— 已评估
   - ❌ Dream Manager / Screensaver（6/20）— 过于小众
   - ❌ AccountManagerService（5/20）— 非性能瓶颈
   - ❌ StatusBarService（7/20）— 已在 7.13 SystemUI 覆盖

3. **Jetpack / SDK 库覆盖检查**
   - ✅ Paging 3 — 已在 RecyclerView/列表优化覆盖
   - ✅ Navigation Compose — 22.23 专门覆盖
   - ✅ WorkManager — 5.10/25.4/25.13 覆盖
   - ✅ Room / SQLite — 10.7/24.2/24.17 覆盖
   - ✅ DataStore — 6.5 专门覆盖
   - ✅ CameraX — 多章节覆盖
   - ❌ AppSearch（9/20）— 系统性能影响低
   - ❌ Companion Device Manager（8/20）— 素材不足

4. **Media / Codec 覆盖检查**
   - ✅ MediaCodec / Codec2 — 8.8/18.23 覆盖
   - ✅ Media3 / ExoPlayer — 18.23 覆盖
   - ✅ Audio Offload — 25.18 专门覆盖
   - ❌ AV1 Codec（8/20）— 编解码器细分
   - ❌ Spatializer（7/20）— 音频特效细分
   - ❌ Media DRM / Crypto（6/20）— 安全模块

5. **On-device ML 覆盖检查（深度验证）**
   - ✅ TFLite（65 mentions）/ LiteRT（188 mentions）— 5.11 覆盖
   - ✅ NNAPI（132 mentions）— 5.11/5.14 覆盖
   - ✅ Model quantization — 在 5.11/5.13 有技术讨论
   - ❌ Model distillation / pruning（7/20）— ML 工程话题
   - ❌ Executorch / PyTorch Mobile（8/20）— 框架选择，非系统性能

6. **Cross-cutting concern 检查**
   - ❌ Performance Regression Testing — ch15/ch27 已覆盖方法论
   - ❌ App Size vs Performance Trade-offs — ch12/ch25 已覆盖
   - ❌ Performance Incident Response — ch15.9 已覆盖
   - ❌ Canary Release / Feature Flag — ch15.6 已覆盖测试
   - ❌ Clean Architecture / MVI / MVP — 架构模式非系统性能

7. **新兴主题零覆盖检查（补充）**
   - ❌ Android Emulator / AVD Performance（8/20）— 开发工具非运行时
   - ❌ Dynamic Color / Material You（8/20）— 已在 1.24 ResourcesManager 概念覆盖
   - ❌ Trusted Web Activity / PWA（7/20）— 小众
   - ❌ Cuttlefish / crosvm（8/20）— 测试基础设施
   - ❌ Bazel / Build System（6/20）— 构建工具非运行时

8. **Kotlin 语言级性能检查**
   - ✅ Suspend function / Continuation — 8.6/8.17 覆盖
   - ✅ Value class / Inline class — 在 Compose 性能章节覆盖
   - ✅ Coroutine Dispatcher — 8.6/21.16 覆盖
   - ❌ Reified generics 开销（7/20）— 编译器层面

9. **Compose 工具链检查**
   - ✅ Compose Compiler Metrics — 22.28 专门覆盖
   - ✅ Recomposition 诊断 — 22.28 覆盖
   - ✅ Layout Inspector — 14.16 覆盖
   - ❌ Composition Tracer（8/20）— 已被 22.28 概念覆盖

10. **通知系统性能（补充检查）**
    - ✅ NotificationManagerService — 8.14/9.6 已覆盖
    - ✅ RemoteViews（132 mentions）— 多章节覆盖
    - ❌ HUN（Heads-Up Notification）渲染性能（9/20）— 子话题
    - ❌ Notification stacking / Smart Reply（7/20）— 子话题

### 本轮统计
- 全书总小节：521（finalized: 329, ready-for-review: 141, draft: 43, 其他: 8）
- 空 draft（<15 有效行）：0 个
- Thin draft（15-60 行）：21 个 — 需 Task2B 加工
- Task2B backlog：0（已清空）
- 知识缺口 ≥14 分：0 个
- 累计已检查关键词：300+

### 建议下一步
1. **优先处理 21 个 thin draft**（15-60 行）→ 需 Task2B 加工
2. **Task9 Deep Review** 继续 review ready-for-review 章节
3. **知识缺口挖掘已趋饱和** — 连续 3 轮（09:11/12:04/13:04）均无 ≥14 候选
4. 如有新 DeepResearch 或外部素材入库，可在后续轮次重新评估


## [Task6 Review] 1.26 DeliQueue 无锁队列源码解析 — 2026-06-28

本轮为 Task 2B android-16→android-17 结构性重写后的首次 Task 6 复检。

### 1. [需补充] MessageHeap min-heap 内部操作未展开
- **位置**：§1.26.3
- **问题**：仅展示了 `Message[] mHeap` 数组声明和排序比较器，未展示 bubble-up/bubble-down 的实际实现逻辑。作为"源码解析"章节，读者需要理解 min-heap 如何在插入和删除时维持堆性质。
- **建议**：补充 `MessageHeap.insert()` 和 `MessageHeap.poll()` 的关键代码路径（示意即可），说明 sift-up/sift-down 策略。

### 2. [需补充] heapSweep drainStack() 原子操作细节
- **位置**：§1.26.4
- **问题**：`heapSweep()` 的第一步 `drainStack()` 是整个无锁设计的关键——它需要原子性地排空整个栈。当前仅写 `Message drained = drainStack()` 一行，未说明内部 CAS 操作。
- **建议**：展开 drainStack() 的原子 swap 操作（HEAD.getAndSet(null) 或等价 CAS），解释为什么这一步是线程安全的。

### 3. [需补充] removeMessages() tombstone 延迟删除机制
- **位置**：§1.26.2（仅一句话提及）
- **问题**：`MessageStack.removeMessages()` 使用 tombstone 逻辑删除，但章节从未解释 tombstone 是什么、如何标记、何时清理。
- **建议**：补充 tombstone 的标记方式（compareAndSet 状态位？替换 Message 对象？）和 Looper 线程在 heapSweep 时的清理逻辑。

### 4. [需补充] Perfetto 集成部分过于简略
- **位置**：§1.26.7
- **问题**：仅一段文字提到 `message_queue_receive` trace slice，缺少：(1) 具体(track/counter 名称；(2) slice 的关键字段（cookie、msg_name 等）；(3) 可用的 SQL 查询示例（如统计消息处理延迟 P95）；(4) 正常 vs 异常 trace 图样描述。
- **建议**：按 writing-guide 要求补充 Perfetto 表现段——具体 track 名、SQL 查询模板、典型异常 pattern。

### 5. [需补充] 缺少"常见问题与误区"小节
- **位置**：全文末尾
- **问题**：writing-guide Type A 模板建议包含"常见问题与误区"小节。DeliQueue 场景下常见误区包括：误以为 CAS 队列在低竞争场景也更快、误以为 heapSweep 每消息成本恒定、混淆 targetSdk gating 与设备 Android 版本的关系。
- **建议**：补充 3-5 条 FAQ。

**review 日志**：logs/review/2026-06-28-15-review.md
