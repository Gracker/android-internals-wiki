# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch08-responsiveness/`
- **候选章节**：
  1. `06-coroutine-performance.md` | `status: ready-for-review`, `task9_state: pending`
- **最终选择**：`06-coroutine-performance.md`
- **选择理由**：章节状态符合规范要求，且涉及 Android 17 关键性能演进点（无锁队列），适合深度技术审计。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：底层实现描述不准（混淆了标准线程池与 CoroutineScheduler）、遗漏 Android 17 重大架构变更、误导 Android 平台对 Debug Agent 的支持。
- **评分理由**：存在 3 处 P1 级问题，包括事实描述错误和关键平台知识缺失。尽管及时跟进了 Kotlin 2.2 数据，但底层机制的偏差会影响读者对 Trace 表现的深度理解。
- **本轮 review 覆盖范围**：调度器实现、切换开销、结构化并发、Flow 背压、Perfetto 追踪、Android 17/16 版本差异。
- **本轮未完成部分**：对于 Ktor/服务器侧协程性能的对比未深入（非 Android Wiki 核心）。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.0/5 | 1 (P1) |
| 原理链完整性 | 3.5/5 | 1 (P1) |
| 版本差异覆盖 | 4.0/5 | 1 (P1) |
| 知识盲区 | 3.5/5 | 2 (P1) |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
*暂无 P0 级严重事实错误，但 P1 级描述偏差需修正。*

## 五、P1 问题（重要缺失/描述偏差）
### 1. [P1][源码准确性][调度器底层实现]
- **原文位置**：`Dispatchers.Default` 章节
- **原文问题**：称其背后是“基于 `ScheduledThreadPoolExecutor` 的工作窃取线程池”。
- **源码锚点**：`kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt`
- **核验结论**：`Dispatchers.Default` 实际上指向 `DefaultScheduler`，其底层是专门定制的 `CoroutineScheduler`。它并不继承 `ScheduledThreadPoolExecutor`，而是通过一套基于 **CPU Permits**（许可制）和 **100µs 窃取规则** 的自研算法运行。
- **为什么重要**：标准线程池和协程调度器在 Perfetto 中的任务窃取表现完全不同，错误的理解会导致开发者在分析调度延迟时无法准确识别“CPU 许可限制”导致的排队。
- **建议修正方向**：修正为 `CoroutineScheduler`，并补充其“CPU 许可”机制：执行计算任务需 Permit，IO 任务不需要，以此实现线程共享。

### 2. [P1][知识盲区][Android 17 DeliQueue 交互]
- **原文位置**：`Dispatchers.Main` 章节
- **原文问题**：仅提到 `Main` 是对 `Looper` 的封装，未提 Android 17 的重大优化。
- **一手资料锚点**：Android 17 Release Notes / DeliQueue Design Doc
- **运行原理说明**：Android 17 引入了 **Lock-free MessageQueue (DeliQueue)**。在旧版本中，后台协程通过 `withContext(Dispatchers.Main)` 切回主线程会触发 `MessageQueue` 的监视器锁（synchronized），在高并发下导致主线程被后台线程“锁住”。Android 17 实现了入队无锁化。
- **为什么这是重要缺失**：这是 Android 17 最核心的性能变更之一，直接提升了协程切换的确定性。
- **建议补充方向**：增加“Android 17 无锁化 MessageQueue”对 `Dispatchers.Main` 响应速度的专项描述。

### 3. [P1][平台限制][kotlinx-coroutines-debug 支持情况]
- **原文位置**：`Coroutine 在 Perfetto 中的追踪`
- **原文问题**：建议开发者使用 `kotlinx-coroutines-debug` 模块。
- **源码锚点**：`kotlinx-coroutines-debug` 官方 README
- **为什么这是重要缺失**：该模块是一个 **JVM Agent**，依赖于字节码插桩，**在 Android Runtime (ART) 上无法运行**。Android 开发者应使用 Android Studio 的 Coroutine Debugger（基于 R8 调试信息）或 `JankStats`。
- **建议补充方向**：明确标注该模块仅限 JVM/桌面端，补充 Android 平台推荐的 Trace/调试手段。

## 六、P2 问题（建议改进）
- **[P2][版本差异][16 KB 页面支持]**：Android 16 引入了 16 KB 内存页。协程作为分配密集型框架，会从 TLB 命中率提升中受益。建议在版本演进中提及。
- **[P2][原理链][IO 调度器弹性]**：补充说明 `Dispatchers.IO.limitedParallelism(n)` 创建的视图是“弹性的”，其并发数 `n` 可以超过默认的 64 限制。
- **[P2][源码准确性][100µs 规则]**：建议提及 `CoroutineScheduler` 的本地队列为了缓存局部性，规定任务需在本地呆够 100µs 才能被窃取。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| Android 17 DeliQueue 锁竞争消除 | 高 | 研究 `targetSdkVersion 37` 下 MessageQueue 的无锁插入实现 |
| 16 KB 页面对协程栈/Continuation 的影响 | 中 | 对比 4KB vs 16KB 下协程密集创建的功耗与速度 |
| ADPF 与协程调度器的联动 | 中 | 利用 Android 动态性能框架调整 Dispatcher 并发度 |

## 八、外部核验建议
- **搜索关键词**：`Android 17 DeliQueue performance impact`
- **建议查阅**：`cs.android.com` 搜索 `MessageQueue.java` 在 API 37 的变更。
- **搜索关键词**：`Kotlin 2.2 CoroutineScheduler optimizations`
- **建议查阅**：KotlinConf 2025 性能专题视频。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：`06-coroutine-performance.md`
- **严重级别**：P1
- **位置**：调度器底层实现部分
- **问题描述**：混淆了 `ScheduledThreadPoolExecutor` 与 `CoroutineScheduler`。
- **修正方向**：改为描述 `CoroutineScheduler` 及其 CPU 许可/工作窃取机制。

### 9.2 知识资产（高价值新增知识）
- **一手资料**：Android 17 无锁 MessageQueue (DeliQueue)。
- **关键结论**：Android 17 消除了 `withContext(Dispatchers.Main)` 的锁争用，后台协程切回主线程性能提升极大（高并发下最高 5000 倍）。
- **Trace 观察点**：在 Android 17 上，主线程 `MessageQueue#next` 不再会因为后台线程 `enqueueMessage` 而进入 `Waiting` 状态。

## 十、下一候选章节
- `src/part2-performance/ch07-rendering/01-rendering-pipeline.md` (渲染管线，与调度密切相关)

## 十一、落盘信息
- **已写入文件**：`logs/external-review/2026-04-19-11-06-coroutine-performance-external-review.md`
