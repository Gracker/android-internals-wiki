## 2026-03-30 15:00 前沿研究建议

- 建议将 section 2.9「渲染机制的版本演进」的 priority 从 70 提升到 75
  - 原因：ARR (Adaptive Refresh Rate) 素材同时映射到 2.3 和 2.9，Android 15/16 的 VSync 变化对版本演进章节有重要补充
  - 新素材：2026-03-30-15-arr-vsync-android15-16.md

# 前沿研究建议 - 2026-03-30

## 章节优先级调整建议

### 8.1 响应速度原理
- **当前优先级**：90
- **建议状态**：保持90优先级
- **原因**：已获得高质量核心素材，特别是Android 16 VSync机制优化的详细技术支撑，完全覆盖章节所需的关键锚点
- **素材补充情况**：已获取Android 16 ARR优化、INP概念验证、系统性能改进等高质量素材

### 其他章节建议
- **2.3 VSync机制**：建议优先级从60提升至75，因8.1的研究素材中包含了大量VSync基础机制的内容，可作为2.3的重要补充
- **3.1 Input事件分发**：建议优先级从60提升至70，因响应速度研究中包含输入延迟优化内容，与Input分发机制直接相关

## 素材质量评估

### 高价值发现
1. **Android 16 VSync ARR优化**：官方源码级别的技术细节，稀缺性高，时效性强
2. **INP概念边界验证**：澄清了Web性能指标与Android原生应用的差异，解决了章节中的术语一致性问题
3. **系统级响应优化**：涵盖了从启动到UI响应的完整优化链条

### 后续研究方向建议
1. **ARR在不同SoC平台的表现差异**：可关注高通、联发科等平台的ARR实现差异
2. **Vulkan与VSync的协同优化**：Android 16对Vulkan渲染的进一步优化
3. **机器学习在响应预测中的应用**：Android系统级AI对用户行为的预测和优化

## [Task6 Review] 1.1 Android 分层架构 — 2026-03-30

- **类型**：需重写
- **位置**：全文多处（HAL 组件、Native Libraries、Binder 性能特点、JNI 开销等段落）
- **问题**：大量段落使用百科词条式列表罗列，违反 writing-guide "叙述为主，列表为辅"原则。读者读完知道各层有什么组件，但缺乏因果关系和上下文连贯性。
- **建议**：参考 writing-guide §三.1 的正确写法示例，将列表转为工程师对工程师的对话式叙述。每个组件的介绍要回答"为什么这样设计"和"对性能分析意味着什么"。
- **review 日志**：logs/review/2026-03-30-17-review.md

## [Task6 Review] 1.1 Android 分层架构 — 2026-03-30 (补充)

- **类型**：需补充素材
- **位置**：全文缺失
- **问题**：缺少"在 Perfetto/工具 中的表现"部分。writing-guide 类型 A 模板要求每个机制篇都要展示在 Trace 中的表现。
- **建议**：补充各架构层在 Perfetto 中的对应 Track/事件（如 SurfaceFlinger track、各进程的 CPU slice、Binder 调用事件等），以及正常 vs 异常表现对比。
- **review 日志**：logs/review/2026-03-30-17-review.md

## [Task6 Review] 1.1 Android 分层架构 — 2026-03-30 (补充2)

- **类型**：需补充素材
- **位置**：全文缺失
- **问题**：缺少"常见问题与误区"部分。作为全书第一章，这是读者建立正确认知的关键入口。
- **建议**：补充常见误解（如 SurfaceFlinger 在 Framework 进程中、Zygote fork 会复制 ART 堆、HAL 不影响性能等），以及面试易错点。
- **review 日志**：logs/review/2026-03-30-17-review.md

## [Task6 Review] 1.1 Android 分层架构 — 2026-03-30 (风格)

- **类型**：需重写
- **位置**：开头 3 段
- **问题**：开头使用"精密的钟表"比喻，过于修辞化，不符合 writing-guide §六 的"现象驱动"风格。
- **建议**：从具体 Perfetto Trace 中的某一现象引入（如"打开 Perfetto，你看到的那些进程/线程/Track，就是 Android 分层架构的可视化"），直接把读者带入实战场景。
- **review 日志**：logs/review/2026-03-30-17-review.md

## [Task6 Review] 1.2 系统启动全流程 — 2026-03-31
- **类型**：需补充素材
- **位置**：启动时间的度量 章节
- **问题**：大纲锚点要求覆盖 BootTimingsTraceLog，但正文完全未涉及。该类是 AOSP 中 SystemServer 用来记录各阶段启动耗时的工具，是启动度量的重要一环。
- **建议**：补充一段 BootTimingsTraceLog 的说明，包括：1）它的作用和原理；2）如何通过 adb logcat 或 Perfetto 查看其输出；3）在 SystemServer 启动流程中的对应位置。参考 AOSP 路径：frameworks/base/services/core/java/com/android/server/BootTimingsTraceLog.java
- **review 日志**：logs/review/2026-03-31-13-review.md


## 2026-03-31 15:00 前沿研究建议

1. **1.2 BootTimingsTraceLog 回炉素材已到位**: 两篇研究素材已写入 intake/research-feeds/，覆盖 BootTimingsTraceLog + TimingsTraceAndSlog 双层追踪体系和 Android 16 启动优化新特性，建议 task4 加工时优先使用
2. **16.2 优先级建议**: 建议将 16.2（各 Android 版本性能变更追踪）priority 从 50 提升到 65，因 Android 16 并行模块加载和 AutoFDO 是高价值版本演进素材


## [Task6 Review] 4.5 App 内存优化 — 2026-04-01
- **类型**：需补充素材
- **位置**：全文缺失"常见问题与误区"部分
- **问题**：writing-guide.md Type A 模板明确要求"常见问题与误区"部分，当前草稿缺少此节。虽然内存泄漏的常见模式部分涵盖了部分常见问题，但没有独立的小节总结开发者对 App 内存优化的常见误解。
- **建议**：补充以下常见误区：
  1. "调用 System.gc() 能解决内存问题" — 实际上 Android 明确不建议手动触发 GC
  2. "Android 8.0+ 不需要 recycle Bitmap" — 适用条件并非"完全不需要"，而是 Native 回收时机不同
  3. "onTrimMemory 触发 = App 即将被杀" — 实际上有前台/后台多种级别，多数是预警而非死刑
  4. "申请 largeHeap 是解决内存不足的好办法" — largeHeap 有代价，会增加 LMK 优先级
  5. "内存抖动只发生在低端设备上" — 120Hz 设备因帧间隔更短反而更容易暴露
- **review 日志**：logs/review/2026-04-01-17-review.md


## [Task6 Review] 2.1 Android 渲染架构全景 — 2026-04-02

### B1: 需重写 — 文体违规（全文性，11+处列表罗列）
- **位置**：全文至少 11 处"关键机制/核心功能/优势/优缺点/合成层次/显示机制"列表块
- **问题**：违反 writing-guide "叙述为主，列表为辅"核心原则，属于"反面1: 百科词条式"。每个技术点都用 bullet list 罗列，缺少因果关系、上下文衔接、工程师对工程师的叙述语感。
- **建议**：参照 writing-guide.md 中 VSync 的"正确写法"示例，将每个列表块重写为连贯叙述。优先处理 Measure/Layout/Draw 三节的"关键机制"列表、三缓冲的"优势"列表、软件渲染的"优缺点"列表。
- **review 日志**：logs/review/2026-04-02-00-review.md

### B2: 需补充素材 — 缺少 5 个 Type A 模板标准节
- **位置**：全文结构
- **问题**：缺少"在 Perfetto/工具中的表现"专节、"与其他机制的关系"专节、"版本演进"说明、"常见问题与误区"专节、"参考资料"列表。当前 Perfetto 内容仅在开头简略提及，无专节。
- **建议**：
  - Perfetto 专节：描述渲染管线各阶段在 Trace 中对应的 Track（Choreographer/RenderThread/SurfaceFlinger/GPU），正常vs异常表现
  - 关系节：ch2.3 VSync → ch2.4 Choreographer → ch2.5 MainThread/RenderThread → ch2.6 SurfaceFlinger 的上下游链路
  - 版本演进：Android 3.0(硬件加速引入) → 4.1(Project Butter/VSync) → 5.0(RenderThread) → 12(BlastBufferQueue) → 16(最新变化)
  - 常见误区：如"GPU渲染一定比CPU快"、"三缓冲越多越好"、"硬件加速解决一切"
  - 参考资料：AOSP 源码路径 + developer.android.com 链接
- **review 日志**：logs/review/2026-04-02-00-review.md

### B3: 需重写 — 源码引用过长（多处代码块）
- **位置**：getDefaultSize() (~15行)、dequeueBuffer() 签名 (~10行)、RenderNode class (~20行)、DisplayListData class (~15行)
- **问题**：违反 writing guide "只贴决定行为的那几行"原则。dequeueBuffer 签名块完全是函数签名，无实质内容。
- **建议**：每个代码块精简到关键 3-5 行，加上注释标注"这段代码在做什么"。删除纯签名代码块。前后必须有"这意味着什么"的解释。
- **review 日志**：logs/review/2026-04-02-00-review.md

### B4: 需重写 — 总结概述式
- **位置**：文末"总结"节
- **问题**：两个编号列表（5个要点 + 4个能力），符合"反面3: 概述式"特征。
- **建议**：重写为 2-3 段连贯叙述，回扣开头"为什么要了解渲染架构"的动机，自然引出下一节（VSync/Choreographer）。
- **review 日志**：logs/review/2026-04-02-00-review.md

### B5: 存疑 — 部分源码示例准确性
- **位置**：OpenGLCanvas 类、VulkanRenderer::drawRect、DisplayListData 类结构、RenderNode class 定义
- **问题**：这些代码示例可能是简化的伪代码，不完全反映 AOSP android-16.0.0_r1 的实际结构。Android 16 中 HWUI 已大幅重构，DisplayList 可能已不再以该类名存在。
- **建议**：task2 重新对照 AOSP android-16.0.0_r1 源码验证这些代码块，标注 [待验证] 或替换为准确的代码。
- **review 日志**：logs/review/2026-04-02-00-review.md

## [Task6 Review] 4.5 App 内存优化 — 2026-04-02 (二次 review)

### 问题 1
- **类型**：存疑
- **位置**：onTrimMemory 前台回调表
- **问题**：TRIM_MEMORY_RUNNING_MODERATE 常量值标注为 20，TRIM_MEMORY_RUNNING_CRITICAL 标注为 40。根据 AOSP ComponentCallbacks2.java 源码，实际值分别为 5 和 15。TRIM_MEMORY_RUNNING_LOW=10 正确。后台回调值（UI_HIDDEN=20, BACKGROUND=40, MODERATE=60, COMPLETE=80）均正确。
- **建议**：核实 AOSP 源码后修正运行级别回调的数值
- **review 日志**：logs/review/2026-04-02-0320-review.md

### 问题 2
- **类型**：需补充素材
- **位置**：Bitmap 优化、内存泄漏检测、监控兜底等小节
- **问题**：writing-guide.md 要求每节提供"在 Perfetto/工具中的实际表现"。当前仅 heapprofd 小节有 Perfetto 对照，其他小节缺少对应的 Track 描述或截图占位。
- **建议**：补充以下 Track 说明：① Java Heap Track 在 Perfetto 中的表现 ② GC Event Track 与内存抖动的对应关系 ③ dmabuf/GPU memory Track 的说明
- **review 日志**：logs/review/2026-04-02-0320-review.md


## [Task6 Review] 5.1 Linux 进程调度基础 — 2026-04-02

### B1: 需补充素材 — EEVDF 调度器章节
- **类型**：需补充素材
- **位置**：「EEVDF：CFS 的下一代演进（Linux 6.6+）」章节
- **问题**：EEVDF 是 Linux 6.6+ 替代 CFS 的新调度器，引入了虚拟截止时间（virtual deadline）概念，使调度决策更加确定性。当前仅有 [待补充] 占位符和一句话概述，缺少：① 虚拟截止时间的计算机制 ② EEVDF 与 CFS 的核心区别（latency nose、eligibility 机制）③ 对 Android 延迟敏感型工作负载的影响分析 ④ 在 Perfetto 中的观察方法
- **建议**：参考 Linux kernel documentation (sched-design-EEVDF.html)、LWN 相关文章，补充完整内容。标注 [待验证: Android 17 是否默认启用 EEVDF] 保留。
- **review 日志**：logs/review/2026-04-02-0421-review.md

### B2: 需补充素材 — SchedTune 与 UClamp 章节
- **类型**：需补充素材
- **位置**：「SchedTune 与 UClamp：Android 的调度增强」章节
- **问题**：这两个机制直接影响 Android 的 CPU 选核和频率决策，对 MTK/高通平台性能优化至关重要。当前仅有 [待补充] 占位符。缺少：① SchedTune boost 机制（per-task boosting、cgroup 集成）② UClamp 的 min/max clamp 原理及其与 EAS 的配合 ③ MTK/高通平台上的厂商定制化差异 ④ 在 Perfetto 中的 Track 表现
- **建议**：参考 AOSP kernel/sched/ufreq.h（uclamp 定义）、Android 源码中 SchedTune cgroup 实现、高爷博客素材 Personal-Knowlodge/source/Android-Perfetto-09-CPU.md
- **review 日志**：logs/review/2026-04-02-0421-review.md

## [Task6 Review] 4.6 内存相关的版本演进 — 2026-04-02
- **类型**：存疑
- **位置**：章节标题「Android 8.0–10：GC 演进为 Concurrent Copying，暂停时间降至亚毫秒」
- **问题**：标题称降至亚毫秒，但正文数据显示 Young GC 暂停 1-3ms，均非亚毫秒（<1ms）
- **建议**：确认是否有 Google 官方数据支持；如无建议改为暂停时间大幅降低
- **review 日志**：logs/review/2026-04-02-0630-review.md

## [Task6 Review] 4.6 内存相关的版本演进 — 2026-04-02 (2)
- **类型**：待补充
- **位置**：速查表「Android 15 | 16KB Page Size 支持」
- **问题**：16KB Page Size 仅在速查表中出现，正文无对应说明
- **建议**：在正文增加 16KB Page Size 对内存管理影响的简要说明
- **review 日志**：logs/review/2026-04-02-0630-review.md

## [Task6 Review] 2.2 帧率与刷新率 — 2026-04-02

### 问题 1：API 33+ doFrame 回调签名不准确
- **类型**：存疑
- **位置**：Frame Pacing 章节 → "API 33+ 的 Frame Timeline 选择" → 代码示例
- **问题**：代码示例中的 `doFrame(long frameTimeNanos, int frameId, Map<String, Long> frameData, int[] preferredFrameTimelines)` 签名与 AOSP 实际 API 不符。实际 API 33+ 使用 `FrameData` 对象传递 VSync 信息和候选时间线。
- **建议**：查阅 AOSP `frameworks/base/core/java/android/view/Choreographer.java` 中 API 33+ 的 `FrameCallback` / `FrameData` 定义，替换为正确的代码示例。
- **review 日志**：logs/review/2026-04-02-0735-review.md

### 问题 2：FrameRateOverride 检测代码示例不准确
- **类型**：存疑
- **位置**：扩展 → Game Mode / Frame Rate → "Frame Rate Override（Android 14+）" → 代码示例
- **问题**：`Choreographer.getInstance().postFrameCallback(...)` 不是检测 Frame Rate Override 的正确方式。`postFrameCallback` 只是注册下一帧回调，无法检测帧率被覆盖的情况。
- **建议**：替换为 `Surface.OnFrameRateOverrideListener`（API 35+）或 `DisplayManager.DisplayListener` 的实际监听代码。
- **review 日志**：logs/review/2026-04-02-0735-review.md

### 问题 3：缺少"常见问题与误区"独立小节
- **类型**：需补充素材
- **位置**：全文末尾、总结之前
- **问题**：writing-guide.md Type A 模板要求有"常见问题与误区"独立小节，本文缺失。文章虽然正文中散见一些误解澄清（如"同样的60 FPS流畅度可以天差地别"），但缺少系统性的误区梳理。
- **建议**：补充5个常见误解：(1) 高刷=更流畅 (2) FPS够就行 (3) 120Hz一定好 (4) 掉帧=主线程问题 (5) setFrameRate是命令
- **review 日志**：logs/review/2026-04-02-0735-review.md

### 问题 4：Swappy 刷新率选择表述需确认
- **类型**：存疑
- **位置**：Frame Pacing 章节 → "Android Frame Pacing Library（Swappy）" → 第4点
- **问题**：原文"Swappy 会...选择一个最佳的刷新率"表述暗示 Swappy 直接决策刷新率。实际上 Swappy 通过 setFrameRate() 向 SurfaceFlinger 传递偏好，由 SurfaceFlinger 做出最终决策。已在源文件中微调表述并标注，需高爷确认。
- **建议**：确认 Swappy 与 SurfaceFlinger 的刷新率决策分工是否准确。
- **review 日志**：logs/review/2026-04-02-0735-review.md

## [Task6 Review] 2.4 Choreographer 与渲染流水线 — 2026-04-02

- **类型**：存疑 + 需重写 + 需补充素材
- **位置**：doFrame()代码块 / 总结 / Compose扩展节 / 全文结构 / 厂商优化实践
- **问题**：
  1. doFrame() 为简化伪代码，方法签名与逻辑可能不反映 AOSP 实际实现
  2. 总结使用编号列表，违反 writing-guide 叙述要求
  3. Compose 节教程风格过重，缺少机制分析
  4. 缺少 Type A 必需节：版本演进/常见问题与误区/与其他机制的关系
  5. 厂商优化实践缺少可验证来源
- **建议**：
  1. 对照 AOSP Choreographer.java 重写 doFrame 关键代码引用
  2. 总结改为 2-3 段连贯叙述
  3. Compose 节转为分析式：内部调度机制、与 View 系统差异、Trace 影响
  4. 按 Type A 模板补充 3 个标准节
  5. 厂商优化补充来源或标注待验证
- **review 日志**：logs/review/2026-04-02-0920-review.md
## [Task6 Review] 2.6 SurfaceFlinger 与合成 — 2026-04-02

### B1: 需重写 — 全文文体
- **位置**：全文
- **问题**：整体呈百科词条+源码堆砌风格，违反 writing-guide.md §三核心要求。大量 bullet points 替代连贯叙述，代码前后缺少因果说明，Perfetto/Trace 关联几乎为零
- **建议**：参考 writing-guide §三写作手法要求，将列表段落改写为叙述段落

### B2: 需重写 — 多处 C++ 代码疑似编造
- **位置**：多处代码段
- **问题**：ClientCompositor/DeviceCompositor/DisplayManager 不存在于 AOSP；SurfaceFlinger::composite() 签名与实际不符；BlastBufferQueue 无公开 Java API
- **建议**：对照 AOSP android-16.0.0_r1 实际源码重写

### B3: 需补充素材 — Perfetto Trace 对照
- **位置**：全文
- **问题**：开头提到 Perfetto 但正文无 Trace 对照，未说明 SF track 等 Track 对应关系
- **建议**：增加“在 Perfetto 中的表现”小节

### B4: 需验证 — HWC 版本号
- **位置**：HWC 协议版本演进
- **问题**：声称 HWC 3.0 含 Vulkan 后端，但 AOSP 中 HWC HAL 为 2.x
- **建议**：核实 AOSP android-16 中的 HWC HAL 版本

- **review 日志**：logs/review/2026-04-02-1320-review.md

## 2026-04-02 15:00 前沿研究建议

### AppFlow 素材联动建议
- 8.2（App 启动全流程）当前 priority=55，鉴于 AppFlow（MobiCom '26）是 2026 年最新的冷启动优化前沿研究，建议将 8.2 的 priority 从 55 提升到 70
- AppFlow 的三大组件（Selective File Preloader / Adaptive Memory Reclaimer / Context-Aware Process Killer）覆盖了 8.2 启动流程和 4.4 内存管理两个章节的交叉内容

### sched_ext + EEVDF 素材联动建议
- 5.1 已完成加工，但 sched_ext（6.12 合并）和 EEVDF lag fix（6.13）是 2025 年的最新发展，建议在下次 review 时检查 5.1 中是否需要补充 sched_ext 的前瞻性讨论
- 5.7（CPU 相关的版本演进）建议补充 sched_ext 的 Android 前景分析


## [Task6 Review] 2.11 Flutter 渲染管线与性能 — 2026-04-02

- **类型**：需确认
- **位置**：frontmatter applicable_versions
- **问题**：`"Android 10 (API 29) - Android 17 (API 35)"` 中 Android 17 ≠ API 35。项目其他章节中 Android 16 = API 36，此版本号映射明显有误。
- **建议**：确认实际覆盖的 Android 版本范围，修正为类似 "Android 10 (API 29) - Android 16 (API 36)" 的格式。
- **review 日志**：logs/review/2026-04-02-1924-review.md

- **类型**：需补充素材
- **位置**：## Impeller 引擎 > ### Impeller 在 Android 上的表现
- **问题**："光栅化时间降低约 30%"和"内存使用比 Skia 低约 100MB"均缺乏具体来源。Flutter 官方 benchmark 链接或第三方测试报告均未引用。
- **建议**：补充 Flutter 官方性能基准测试页面或 GitHub issue/discussion 链接作为佐证。
- **review 日志**：logs/review/2026-04-02-1924-review.md

- **类型**：需补充
- **位置**：全文结构
- **问题**：本章缺少 `<!-- outline-start -->...<!-- outline-end -->` 大纲块，与项目大部分已加工章节的格式不统一。
- **建议**：task2 回炉时补充 outline 块，用 🔹 锚点标注每个子主题。
- **review 日志**：logs/review/2026-04-02-1924-review.md


## [Task6 Review] 2.9 渲染机制的版本演进 — 2026-04-02
- **类型**：需重写
- **位置**：Project Silk 的后续优化
- **问题**：本节仅有两句话概述 Project Silk，无具体版本号、技术改动点、Perfetto 对应变化。作为独立小节内容过于单薄。
- **建议**：补充 Project Silk 的具体改动内容（VSync offset 调优细节、帧率自适应策略等），或考虑合并入 Project Butter 节作为延续说明。如果确实无法找到足够素材，建议移除独立小节，在 Project Butter 节末尾加一句过渡即可。
- **review 日志**：logs/review/2026-04-02-2024-review.md


## [Task6 Review R2] 2.4 Choreographer 与渲染流水线 — 2026-04-02

- **类型**：需重写
- **位置**：扩展：自定义 FrameCallback 实现帧率监控的原理与实践（全文约120行代码）
- **问题**：本节包含3个完整类实现（FrameRateMonitor、AdvancedFrameRateMonitor、FrameTypeMonitor），属于教程风格代码堆砌，违反 writing-guide §三.2"只贴决定行为的那几行"和§五反面教材2（源码堆砌式）。作为扩展节，应以原理说明为主，辅以精简代码片段
- **建议**：保留核心原理说明（FrameCallback 基本原理 + frameTimeNanos 含量 + 帧率计算公式），保留1个精简代码片段（10-15行）展示 doFrame 计算帧间隔的要点，删除3个完整类实现，将"帧率趋势分析"和"帧类型分类"改为叙述式说明
- **review 日志**：logs/review/2026-04-02-2128-review.md
