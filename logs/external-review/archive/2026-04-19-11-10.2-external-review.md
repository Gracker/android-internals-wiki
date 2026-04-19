# AIW 自动 Review 任务报告 (Gemini 专用)

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch10-memory-perf/`
- **候选章节**：
  1. `02-memory-leak.md` | `status: ready-for-review`, `pipeline_stage: task9_pending`
- **最终选择**：`02-memory-leak.md`
- **选择理由**：该章节是内存优化的核心篇章，且已被 Task 6 完成初步评审，目前处于技术深审（Task 9）挂起状态。章节内容涵盖了从 Java 到 Native 的全栈泄漏排查，技术点密集，亟需源码级核验和 Android 15/16/17 版本差异补强。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：对 Android 15/16 引入的现代分析框架（ProfilingManager）覆盖不足，导致“版本演进”部分具有明显滞后性；Native 工具链的原理描述略显简单，未能触及 `libmemunreachable` 的保守扫描限制及 Android 16 的采样增强。
- **评分理由**：存在 2 条 P1 级重要缺失（版本演进与 Native 深度）。虽然基础概念准确，但未能体现“让读者能独立分析同类系统机制”的目标。
- **本轮 review 覆盖范围**：GC Root 定义、LeakCanary 原理、常见泄漏模式、Native 排查工具（heapprofd/malloc debug/libmemunreachable）、Android 16 ProfilingManager 增强、Compose 泄漏场景。
- **本轮未完成部分**：对于“线上自动检测方案”中的 Koom/Matrix 源码实现未做逐行对齐，仅做了原理级核验。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.5/5 | 0 |
| 原理链完整性 | 4/5 | 1 |
| 版本差异覆盖 | 2/5 | 1 |
| 知识盲区 | 3.5/5 | 1 |
| 数据/案例支撑 | 3/5 | 1 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
暂无明确事实性错误，描述均在 AOSP 定义范围内。

## 五、P1 问题（重要缺失）

### [P1][版本差异覆盖][版本演进] 遗漏 Android 16 ProfilingManager 的重大增强
- **原文位置**：## 版本演进
- **原文问题**：仅提到 Android 16 的 heapprofd 增强，缺乏具体机制说明。
- **源码 / 一手资料锚点**：
    - `frameworks/base/core/java/android/app/ProfilingManager.java` (Android 15+)
    - `PROFILING_TYPE_HEAP_PROFILE` (API 36)
- **关键代码逻辑**：Android 16 引入了 `TRIGGER_TYPE_OOM` 和 `PROFILING_TYPE_HEAP_PROFILE`。前者允许系统在发生 OOM 时自动触发采样，后者允许基于 `heapprofd` 进行**采样式 Java 堆分析**（Sampling），而非传统的全量 Dump。
- **运行原理说明**：传统的 `Heap Dump` 是 STW (Stop The World) 的，且文件巨大。Android 16 的采样分析利用了 ART 的堆采样能力，开销极低，支持线上脱敏（Redaction）分发。
- **核验结论**：原文对 Android 16 的描述过于笼统，未能体现从“手动分析”到“系统自动/采样分析”的范式转变。
- **建议修正方向**：在版本演进中增加专门一段，详述 `ProfilingManager` 如何通过 Mainline APEX 更新实现跨版本的自动采样能力。

### [P1][知识盲区][Native 排查] libmemunreachable 的“保守性”及限制描述缺失
- **原文位置**：## Native 内存泄漏的排查 -> libmemunreachable
- **原文问题**：称其为“不精确”，但未解释为什么不精确，以及如何触发。
- **源码 / 一手资料锚点**：
    - `system/extras/libmemunreachable/`
    - 命令：`adb shell dumpsys meminfo --unreachable [package]`
- **运行原理说明**：该工具通过扫描内存页（栈、数据段）寻找 4/8 字节对齐的“指针状数据”。如果一个随机 long 值恰好指向了一块堆内存，该块会被判定为“存活”，产生**假阴性**。
- **为什么这是重要缺失**：读者如果不理解“保守扫描”，在排查时可能会因为工具未报告泄露而误以为代码安全。
- **建议补充方向**：明确其保守扫描原理，并给出具体的 `dumpsys` 触发命令。

## 六、P2 问题（建议改进）

### [P2][原理链完整性][Compose 场景] LaunchedEffect 与 DisposableEffect 的权责边界
- **原文位置**：## [自动发现] Compose 场景的内存泄漏特征
- **问题描述**：原文只列出了现象，没有从机制上说明为什么 `LaunchedEffect` 容易泄露非协程资源。
- **建议**：补充对比说明。`LaunchedEffect` 只管取消协程，不管取消“副作用”（如监听器）。建议强调对于非协程的回调注册必须使用 `DisposableEffect` 并在 `onDispose` 中清理。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
| :--- | :--- | :--- |
| **MTE (Memory Tagging Extension)** | 高 | Android 11+ 在 ARMv9 设备上通过硬件标签检测 Native 泄漏的机制 |
| **GWP-ASan** | 中 | 针对生产环境的低开销 Native 堆损坏检测 |
| **Heap Redaction** | 中 | Android 15+ 如何在 Dump 过程中移除 PII 隐私数据 |

## 八、外部核验建议
- **搜索关键词**：`Android 16 ProfilingManager TRIGGER_TYPE_OOM`
- **建议查 AOSP**：`frameworks/base/core/java/android/app/ProfilingManager.java` 查看新的 `TRIGGER_TYPE_*` 常量。
- **建议查文档**：`perfetto.dev` 搜索 `Java heap sampling` 了解其与 `heapprofd` 的集成细节。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
| 严重级别 | 位置 | 问题描述 | 建议修正方向 |
| :--- | :--- | :--- | :--- |
| **P1** | 版本演进 | 缺失 Android 16 `ProfilingManager` 对 OOM 自动触发和采样分析的支持说明 | 增加 Android 16 Profiling 模块新特性的深度解析 |
| **P1** | Native 排查 | `libmemunreachable` 原理描述不深，缺乏 `dumpsys` 指令 | 补充保守扫描原理及 `dumpsys meminfo --unreachable` 指令 |
| **P1** | Compose | Compose 泄漏仅为大纲式描述 | 细化 `LaunchedEffect` 与 `DisposableEffect` 的实战避坑指南 |

### 9.2 知识盲区清单（供后续研究）
- **章节**：10.2
- **盲区描述**：硬件级内存检测（MTE/HWASan）在内存泄漏排查中的角色。
- **重要程度**：高
- **可能关联章节**：4.2 Linux 内存管理, 4.6 内存版本演进

### 9.4 可复用知识资产
- **Android 16 ProfilingManager 采样配置**：
  - **路径**：`android.app.ProfilingManager`
  - **关键参数**：`KEY_SAMPLING_INTERVAL_BYTES` (默认 4096)
  - **技术结论**：Android 16 实现了 Java 堆的“采样分析”（Profiling）与“快照分析”（Dump）的解耦，大幅降低了线上生产环境的监控开销。
- **libmemunreachable 触发方式**：
  - **指令**：`dumpsys meminfo --unreachable <PID>`
  - **特征**：STW 操作，用于快速筛查 Native 堆中的“孤儿”内存块。

## 十、下一候选章节
- `src/part2-performance/ch10-memory-perf/01-app-memory-analysis.md` (作为 10.2 的前置基础，需要确保工具链描述的一致性)

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-02-memory-leak-external-review.md`
