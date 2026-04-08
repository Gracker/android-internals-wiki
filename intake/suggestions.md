---
tags:
  - android
  - log


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


## [Task6 Review] 2.9 渲染机制的版本演进 — 2026-04-03
- **类型**：需补充素材 / 需确认 / 需重写
- **位置**：AOSP源码路径、版本时间线、4处图注、FrameMetrics段落
- **问题**：详见 logs/review/2026-04-03-03-review.md
- **建议**：task2 下一轮优先处理（priority: critical）
- **review 日志**：logs/review/2026-04-03-03-review.md

## 2026-04-03 07:00 前沿研究建议

1. **§5.7 CPU 相关的版本演进 — 优先级提升建议**：EEVDF 取代 CFS 是 Linux 调度器 10 年来最大的架构变化，Android 16 已默认使用。建议将 §5.7 中调度器演进部分提升为高优先级内容，覆盖三条主线：
   - EEVDF 取代 CFS（6.6→6.12）
   - sched_ext BPF 可扩展调度器（6.12 合入，Android 实验中）
   - PREEMPT_LAZY 懒抢占（6.13 引入）

2. **§5.1 Linux 进程调度基础 — 内容补充建议**：当前 §5.1 已 finalized，但 EEVDF 作为新默认调度器，其核心概念（lag、eligibility、virtual deadline）应作为基础知识补充。考虑在版本演进或附录中增加 EEVDF vs CFS 对比内容。

## [Task6 Review] 2.10 GPU 渲染深入 — 2026-04-03

- **类型**：需重写 / 需补充素材 / 存疑
- **位置**：全文
- **问题**：
  1. 大量段落使用列表格式（编号/要点列表），违反 writing-guide §三.1「叙述为主，列表为辅」要求，需转为连贯叙述
  2. 实战案例使用全伪代码，无真实 Perfetto Trace 分析描述，需按类型B模板重写
  3. 缺少「与其他机制的关系」小节（如 VSync→Choreographer→GPU 上下游关系）
  4. 缺少「在 Perfetto 中的具体表现」专节（当前散落各处）
  5. 缺少「常见问题与误区」小节
  6. 3处伪代码标为 AOSP 源码（GLESContext::compileShader / ANativeWindowBuffer 继承关系 / WindowManagerGlobal.trackGpuMemoryUsage）
- **建议**：参考 writing-guide.md 类型A模板和文体要求，重点修复叙述风格和结构缺失
- **review 日志**：logs/review/2026-04-03-0920-review.md


## [Task6 Review] 7.3 卡顿分析方法论 — 2026-04-04

### Issue 1: FrameMetrics.DEADLINE API 版本兼容性
- **类型**：存疑
- **位置**：FrameMetrics 代码示例（FrameMetrics API 小节）
- **问题**：代码使用 `FrameMetrics.DEADLINE` 常量（API 31+），但上下文描述为 "Android 7.0+, API 24"，存在版本兼容性矛盾
- **建议**：确认目标兼容版本：如需兼容 API 24-30，添加 `Build.VERSION.SDK_INT` 分支或硬编码 deadline；如仅面向 API 31+，更新描述
- **review 日志**：logs/review/2026-04-04-0120-review.md

### Issue 2: SQL 调度延迟查询语义
- **类型**：需确认
- **位置**：SQL 查询示例（"调度延迟最大的时刻"）
- **问题**：`sched.end_state = 'R'` 查询的是线程被抢占时仍为 Runnable 的时刻，不等同于"从唤醒到上 CPU 的调度延迟（wakeup latency）"
- **建议**：如需测量真正调度延迟，改用 `sched_wakeup` 事件计算 wakeup_ts → sched_switch(in) 的时间差；或明确注释当前查询的实际含义
- **review 日志**：logs/review/2026-04-04-0120-review.md

## [Task6 Review] 6.2 文件系统 — 2026-04-04

- **类型**：需补充素材
- **位置**：末尾（正文收尾后）
- **问题**：缺少 writing-guide Type A 模板要求的「版本演进」独立小节。当前版本信息散布在正文中，缺少集中梳理 ext4/f2fs/EROFS 在各 Android 版本中的变化时间线。
- **建议**：参考 writing-guide.md 类型 A 模板，新增"版本演进"小节，按时间线列出三个文件系统在 Android 各版本中的关键变化。
- **review 日志**：logs/review/2026-04-04-0333-review.md

## [Task6 Review] 6.2 文件系统 — 2026-04-04

- **类型**：需补充素材
- **位置**：末尾（正文收尾后）
- **问题**：缺少 writing-guide Type A 模板要求的「常见问题与误区」小节。
- **建议**：补充 3-5 个新手常见误解，如"f2fs 一定比 ext4 快"、"EROFS 可以用于 data 分区"、"fsync 在 f2fs 上完全没有开销"等。
- **review 日志**：logs/review/2026-04-04-0333-review.md

## [Task6 Review] 6.2 文件系统 — 2026-04-04

- **类型**：需补充素材
- **位置**：末尾（正文收尾后）
- **问题**：缺少 writing-guide Type A 模板要求的「参考资料」小节。正文引用了多个 AOSP 路径和官方文档，但未在末尾汇总。
- **建议**：汇总列出 AOSP 源码路径（Choreographer → f2fs/ioctl）、kernel.org 文档、SQLite 官方文档、esper.io 等外部参考。
- **review 日志**：logs/review/2026-04-04-0333-review.md



## [Task6 Review] 7.4 典型场景分析 — 2026-04-04
- **类型**：需修正（技术建议误导）
- **位置**：section 2.2 Fragment 切换优化建议（"使用 commitAllowingStateLoss() 替代 commit()"）
- **问题**：commitAllowingStateLoss() 的设计目的是避免 onSaveInstanceState() 后 commit 导致的 IllegalStateException，与"状态检查开销"无关。两者性能差异可忽略。使用不当可能导致 Fragment 状态不一致。
- **建议**：修正为更准确的优化方向：① 将 Fragment 事务提交时机与动画帧解耦；② 使用 commitNow() 在非动画期间同步执行；③ 延迟 commit 到动画结束后。
- **review 日志**：logs/review/2026-04-04-0525-review.md

## [Task6 Review] 7.5 优化策略 — 2026-04-04

- **类型**：需重写
- **位置**：减少层级的其他手段 / Binder 调用优化 / 合理的线程池配置 / 预渲染与预计算策略
- **问题**：4个段落使用纯列表格式，违反 writing-guide.md 叙述优先规范，应转为连贯叙述
- **建议**：每条策略按"为什么有效 + 怎么做 + 在Trace中怎么看"展开叙述
- **review 日志**：logs/review/2026-04-04-0626-review.md

- **类型**：需补充素材
- **位置**：布局优化/RecyclerView优化/线程优化段落
- **问题**：开头承诺了Trace验证方法，但主要段落缺少Perfetto定位描述
- **建议**：补充布局层级过深/RecyclerView滑动卡顿/Binder调用耗时的Trace特征描述
- **review 日志**：logs/review/2026-04-04-0626-review.md

- **类型**：需确认
- **位置**：常见误区第2条
- **问题**：Compose BOM 2025.12.00版本号和"性能对等"声明待确认
- **建议**：核实版本号和声明来源
- **review 日志**：logs/review/2026-04-04-0626-review.md

## [Task6 Review] 2.5 MainThread 与 RenderThread 协作 — 2026-04-04
- **类型**：需验证
- **位置**：版本演进表 — Android 15 (API 35) 行
- **问题**：原文写"ANGLE 强制采用"，已改为"ANGLE 推广加速"并加 [待验证] 标注。ANGLE 在 Android 15 中是否对所有 GPU 厂商（Qualcomm Adreno、ARM Mali、Imagination PowerVR）统一强制启用，需要进一步确认。根据已有信息，ANGLE 的启用策略因厂商和设备而异，并非全局一刀切。
- **建议**：查阅 AOSP android-15 分支的 release notes 和 `com.android.graphics.libgui.flags` 中的 ANGLE 相关 flag，确认实际启用条件后补充说明。
- **review 日志**：logs/review/2026-04-04-1920-review.md

## [Task2A 知识缺口挖掘] 2026-04-04 20:09

### 挖掘结果
- 已检查方向：source-index（0 unmapped）、research-feeds（已映射）、AOSP WMS 结构、官方文档、现有章节扩展点
- 创建了 §2.12 Window Manager Service 与窗口管理（评分 18/20）
- 候选缺口评分 ≥14 共 2 个：
  1. WMS 与窗口管理 — 18/20 — 已创建为 §2.12
  2. AMS 深入（Activity Manager Service）— 17/20 — 建议未来轮次创建
- 其他候选（<14）：WebView 性能 13/20、SQLite 性能 11/20、PMS 12/20
- 已检查方向已记录，下次运行可探索不同方向

## [Task2A 知识缺口挖掘] 2026-04-04 23:02

### 挖掘结果
- 已检查方向：source-index（0 unmapped high-quality）、research-feeds（全部已映射）、AOSP AMS 结构、官方文档、现有章节扩展点、Web 搜索前沿
- 创建了 §1.8 Activity Manager Service 与性能分析（评分 17/20）
- 候选缺口评分 ≥14 共 1 个：
  1. AMS — 17/20 — 已创建为 §1.8
- 其他候选（<14）：WebView 性能 11/20、SQLite 性能 9/20、PMS 包管理 10/20
- 已检查方向已记录，下次运行可探索不同方向（如 Camera/Media 管线、Privacy Sandbox 性能开销）


## [Task6 Review] 2.1 Android 渲染架构全景 — 2026-04-05
- **类型**：存疑（技术准确性）
- **位置**："RenderEngine 与 GPU Composition 的区别"小节
- **问题**：文中描述 RenderEngine 运行在 RenderThread 中，负责 App 的 DisplayList 渲染。但在 AOSP 中 RenderEngine 运行在 SurfaceFlinger 进程中，App 的 RenderThread 使用 HWUI 的 Skia Pipeline。两者混淆。
- **建议**：重新组织此节，区分（1）App RenderThread 的 Skia 渲染管线和（2）SurfaceFlinger 的 RenderEngine/GPU Composition 管线
- **review 日志**：logs/review/2026-04-05-0220-review.md

## [Task6 Review] 13.4 命令行打开超大 Trace — 2026-04-05
- **类型**：存疑
- **位置**：EXTRACT_ARG 示例代码（「Perfetto SQL 查询基础」小节）
- **问题**：示例使用 `name = '低内存杀死'` 作为 slice name，但实际 Perfetto Trace 中 LMK 相关事件的 slice name 为英文（如 `lmk`、`kill_one_process`）。中文 slice name 不反映真实数据，可能误导读者认为 Perfetto 中有中文字段名。
- **建议**：将示例改为真实 slice name（如 `name = 'lmk'`），或改用其他更通用的 EXTRACT_ARG 使用场景。
- **review 日志**：logs/review/2026-04-05-1720-review.md

## [2026-04-05 19:00] task5 研究建议

1. **建议将 2.5 Choreographer 与渲染流水线的 priority 提升到 85**
   - 原因：Android 17 DeliQueue 无锁 MessageQueue 是重大架构变更，有具体性能数据支撑（掉帧减少 4-9.1%）
   - 素材：intake/research-feeds/2026-04-05-19-android17-deliqueue-lockfree-messagequeue.md

2. **建议为 2.2 BufferQueue 章节增加 Android 14 buffer cache purge 内容**
   - 原因：Android 14 引入的 per-layer buffer cache 强制清除直接影响 BufferQueue 内存管理
   - 素材：intake/research-feeds/2026-04-05-19-android14-buffer-cache-purge-graphics-memory.md


---

## Task8 归类 · 2026-04-06

### 聊聊2026年Android开发会是什么样
- 链接：https://juejin.cn/post/7589903499599347766
- 摘要：2026年初Android开发现状综述：Kotlin Multiplatform逐渐成熟、Compose稳定普及、AI辅助编码成为主流。
- 类型：技术文章
- 推荐章节：1.6（版本演进）
- 备注：finalized章节，新参考记录到suggestions.md
- 入库时间：2026-04-06

### Android全局悬浮拖拽视图
- 链接：https://juejin.cn/post/7582246395987148834
- 摘要：ViewDragHelper源码分析，全局拖拽悬浮窗实现，触摸事件拦截机制、WindowManager.LayoutParams配置。
- 类型：技术文章
- 推荐章节：3.2（触摸响应）
- 备注：ready-to-publish章节，记录到suggestions.md
- 入库时间：2026-04-06

### Android 嵌入式照片选择器
- 链接：https://juejin.cn/post/7599963665039081522
- 摘要：Android嵌入式Photo Picker API：无需存储权限、支持多选和视频、嵌入式Fragment集成。
- 类型：技术文章
- 备注：Photo Picker使用指南，非性能主题，无匹配章节
- 入库时间：2026-04-06

### Android 开发中准确判断应用前后台
- 链接：https://juejin.cn/post/7595108457496346639
- 摘要：前后台状态判断方案对比：ProcessLifecycleOwner、RunningAppProcessInfo、Activity回调计数。多进程场景分析。
- 类型：技术文章
- 推荐章节：1.3（进程模型）
- 备注：ready-to-publish章节，记录到suggestions.md
- 入库时间：2026-04-06



## 2026-04-06 素材索引化指令（高爷）

以下 4 个文件是新增的外部资源索引，需要被 task1 索引化后供 task2/2a/2b 加工使用：

1. `intake/external-resources/blog-gracker-series.md` — 高爷博客 42 篇（Perfetto/Systrace/ANR/Memory/CPU/独立文章）
2. `intake/external-resources/perfetto-official-docs-index.md` — Perfetto 官方文档 90 篇（全量纳入加工）
3. `intake/external-resources/google-official-docs-index.md` — Google 官方文档 70 篇（开发者指南/工具/Benchmark/Vitals）
4. `intake/external-resources/android-perf-optimization-resource-map.md` — 高爷精选资源 255 条（15 个分类）

**执行要求**：
- task1 下次盘点时，扫描这 4 个文件，将每条资源提取到 `metadata/source-index.json`
- 每条资源的 `mapped_chapters` 使用索引中已有的映射关系
- 质量评估：高爷原创 → 100 分，官方文档 → 80 分，大厂实践 → 60 分，一般参考 → 30 分
- task2/2a 加工时优先从 source-index 中匹配对应章节的素材
- task2b 精修时，为已有章节补充 sources 引用（frontmatter sources 字段）


## [Task6 Review] 8.6 Kotlin Coroutine 性能实践 — 2026-04-06
- **类型**：需确认
- **位置**：Coroutine 与 RxJava 的性能对比 [扩展] 小节
- **问题**：RxJava 对比的具体百分比数据（内存占用低 23%、冷启动快 40%、简单操作延迟低 15-20%）来源为「社区 benchmark 综合数据，2024-2025 多源交叉验证」，过于模糊。这些具体数字应该有可追溯的 benchmark 出处。
- **建议**：补充可追溯的 benchmark 链接（如 Kotlin benchmarks repo、Xamarin benchmark 套件等），或改为更审慎的表述（如「约 20-30%」配合「近似参考值」标注）
- **review 日志**：logs/review/2026-04-06-1730-review.md


### UI-Voyager: 4B 参数移动 GUI Agent 在 AndroidWorld 上超越人类水平
- 来源：https://arxiv.org/abs/2603.24533
- 类型：论文
- 摘要：腾讯混元团队提出两阶段自进化移动 GUI Agent（RFT + GRSD），4B 模型在 AndroidWorld 达到 81.0% 成功率，超越人类水平。核心技术包括种子任务参数扰动生成器、SSIM 截图比对管线、基于分叉点的自蒸馏训练范式。
- 推荐映射：ch01-architecture（Android 架构与自动化）或 AI×手机（不在当前 AIW 范围内）
- 入库时间：2026-04-07
- 归类原因：AI GUI Agent 测试工具，不直接涉及 Android 系统内部机制或性能优化，待高爷决策是否纳入


## [Task2A 知识缺口挖掘] 2026-04-07 11:44

### 挖掘结果：本轮未发现评分 ≥ 14 的知识缺口

已检查方向：
1. **source-index.json**：0 未映射高质量素材（163 条全部已映射或 <16 分）
2. **research-feeds**（最近 5 篇）：全部映射到已有章节（4.8/1.15/4.7/8.7/ch6/ch16.1）
3. **daily-info**（最近 3 天）：无未被覆盖的性能主题（DeliQueue→1.13/Android 17 适配非性能）
4. **AOSP 对照**（frameworks/base/system/packages_modules/）：核心服务已全部覆盖（AMS/PMS/WMS/SF/Choreographer/Input/Display）
5. **官方文档对照**（developer.android.com）：Android 17 性能新特性（Generational GC/DeliQueue/ADPF/ProfilingManager）均已映射
6. **现有章节扩展点**：ch2/ch6/ch12 等薄章节的扩展方向在先前轮次已创建（2.12-2.18/3.4/14.8-14.10）

低于 14 分的候选（本轮跳过）：
- WebView/Chrome Custom Tabs 性能：素材 2/读者需求 3/相关性 3/时效 2 = 10/20
- Notification 性能/ANR 关联：素材 2/读者需求 3/相关性 3/时效 2 = 10/20
- Audio 管线延迟：素材 2/读者需求 2/相关性 2/时效 2 = 8/20
- Text/Font 渲染性能：素材 2/读者需求 3/相关性 4/时效 2 = 11/20（与 ch2 高度重叠）

### 全书状态
- 总章节：109 | 已完成：85（78%）| 待加工：~6（1.14/14.10 等 draft 状态）
- queue.json pending（非 FRESHNESS）：1.14（锁竞争）、8.7（Baseline Profiles）、4.7（16KB page size queue 标记 pending 但文件已 ready-for-review）
- FRESHNESS 条目：40+ 条 priority 95，由 Task 2B 处理


## [Task2A Gap Mining] 2026-04-07 12:57 已检查方向

本轮已完成全面缺口挖掘，以下方向已检查但候选评分均 < 14，下次可跳过：

1. **Android WebView 渲染性能** → 11/20（非核心系统内部性能，现有 Ch2 覆盖原生渲染管线）
2. **Android 网络协议栈深度** → 12/20（HTTP/3/QUIC/Cronet 素材丰富，但与全书系统内部定位匹配度一般，§12.2 已有基础覆盖）
3. **Android AI/ML 推理性能** → 11/20（NNAPI/TFLite 素材可用，但读者需求度偏低，非传统性能优化核心）
4. **Android Audio 延迟性能** → 11/20（Oboe/AAudio 素材丰富，但受众窄，非通用性能主题）
5. **Android Shader 性能** → 10/20（与 §2.10 GPU 渲染深入、§2.14 图形 API 演进重叠）
6. **AOSP 未覆盖组件**（NotificationManager/ConnectivityManager/BiometricService）→ 评分均 < 12（非性能核心组件）
7. **Part4 Ch16/Ch17 扩展** → 无独立高分候选（现有 3+3 节已覆盖主要方向）

**结论**：全书 124 个小节已覆盖 Android 性能优化的核心知识域，剩余候选均为边缘或重叠方向。建议后续优先处理 queue 中 46 个 pending 条目（含 41 个 FRESHNESS 时效性更新）。

## [Task6 Review] 4.6 内存相关的版本演进 — 2026-04-07
- **类型**：需确认
- **位置**：回收兜底策略的版本对照表格 → Android 7.0 / 7.1 行
- **问题**：表格标注回收策略为「引用机制（NativeAllocationRegistry）」，但 NativeAllocationRegistry 在 Android 8.0 (API 26) 才正式引入。文中也说"Android 8.0 正式采用 NativeAllocationRegistry"。7.0/7.1 的 Bitmap 像素数据仍在 Java 堆（byte[]），其实际回收机制是否是 NAR 的前身（如其他 Reference 类型），需核对源码确认。
- **建议**：比对 AOSP `frameworks/base/graphics/java/android/graphics/Bitmap.java` 在 API 24 (7.0)、API 25 (7.1)、API 26 (8.0) 三个版本的差异，确认 7.0/7.1 的回收策略具体实现。如确实不是 NAR，修正表格为准确的机制名称。
- **review 日志**：logs/review/2026-04-07-15-review.md
## [Task6 Review] 5.7 CPU 相关的版本演进 — 2026-04-07
- **类型**：需确认
- **位置**：Android 14 前台服务类型化段落（L211 附近）
- **问题**：文中称 Android 14 后台 Activity 启动需"显式声明 PendingIntent.FLAG_MUTABLE"，但 FLAG_MUTABLE 与此无关。实际机制是发送方需通过 `ActivityOptions.setPendingIntentCreatorBackgroundActivityStartAllowed(true)` opt-in 授予后台启动权限。
- **建议**：核对 Android 14 行为变更文档，修正 PendingIntent 相关描述为准确的 opt-in 机制说明
- **review 日志**：logs/review/2026-04-07-2048-review.md

## [Task6 Review] 5.7 CPU 相关的版本演进 — 2026-04-07
- **类型**：需确认
- **位置**：GKI 段落（L243 附近）
- **问题**：文中称"GKI 从 Android 11 开始引入，到 Android 15 成为强制要求"。GKI 自 Android 11 起已对新设备有要求，"Android 15 成为强制要求"的具体含义不明确。
- **建议**：明确区分 GKI 基础要求（Android 11+）与 Android 15 的增量变化（可能指 16KB page size 强制、GKI 2.0 内核版本升级等）
- **review 日志**：logs/review/2026-04-07-2048-review.md


## [Task2A 知识缺口挖掘] 2026-04-08 01:02 — 本轮无新合格缺口

**已检查方向**：
1. source-index.json: 4 篇 high quality 无映射素材已评估（Android 14 发布→已在版本章；ANR 不是你的错→已映射 6.5；未缓存缓冲 I/O→Linux 6.14 新特性，与 ch06 重叠度低；CPU 利用率/延迟/吞吐→与 ch05 重叠）
2. research-feeds 最近 10 篇：全部已映射到现有或 pending 章节
3. daily-info 最近 3 天：DeliQueue→1.13、Android 17 适配→16.2、AppJankStats→7.9、性能问题实证研究→参考素材非独立章节
4. AOSP frameworks/base 核心服务：AMS/PMS/WMS/SF/Choreographer/DisplayManager/InputDispatcher 全覆盖
5. system/ 级守护进程：lmkd→4.4；vold/netd/installd 评分均 <10（素材不足+读者需求低）
6. 官方文档 Android 16/17 新 API：ProfilingManager triggers→14.7、getCpuHeadroom/getGpuHeadroom→5.5 扩展、AppJankStats→7.9
7. 之前已评估且低于阈值的：WebView 10/20、Notification 10/20、Audio 8/20、Text/Font 11/20

**候选缺口评分（均 < 14）**：
- Android 端侧 AI/NPU 性能：素材 2 / 相关 3 / 需求 4 / 时效 5 = 14（但 AI 性能偏离全书系统机制+性能优化主线，且素材不足以支撑独立章节）→ **不录入**
- io_uring 在 Android 中的应用：素材 3 / 相关 3 / 需求 3 / 时效 5 = 14（但更适合作为 6.3 I/O 调度的更新而非独立章节）→ **不录入**
- HAL 性能分析：素材 2 / 相关 4 / 需求 3 / 时效 3 = 12 → 不录入

**结论**：全书 112 个小节已覆盖 Android 性能领域主要维度，queue 中仍有 5 个 pending 章节（1.14/1.15/8.7/14.10/7.10）待加工。下一轮挖掘可在新研究素材入库后重新评估。


## [Task6 Review] 9.4 特殊场景的 ANR — 2026-04-08

### 问题 1：低内存触发频繁 GC 导致的 ANR — 内容深度不足
- **类型**：需补充内容
- **位置**：「低内存触发频繁 GC 导致的 ANR」全文
- **问题**：仅约 150 字，缺少源码引用、具体 GC 触发阈值、STW 停顿数据、Trace 表现描述。其他小节普遍 500-800 字并含源码。
- **建议**：补充 ART GC 触发阈值数值、Perfetto 中 GC Track 的名称和表现形式、与 §4.3 的交叉引用、至少一个真实案例。目标篇幅 500+ 字。
- **review 日志**：logs/review/2026-04-08-01-review.md

### 问题 2：文件锁竞争导致的 ANR — 内容深度不足
- **类型**：需补充内容
- **位置**：「文件锁竞争导致的 ANR」全文
- **问题**：仅约 130 字，缺少 SQLite WAL 四级锁的详细说明、源码引用、多进程场景示例、Trace 表现。
- **建议**：补充 SQLite WAL 锁机制（SHARED/RESERVED/PENDING/EXCLUSIVE）、Perfetto 中的表现形式（D 状态 syscall）、beginTransactionNonExclusive() 源码路径。目标篇幅 500+ 字。
- **review 日志**：logs/review/2026-04-08-01-review.md

### 问题 3：Perfetto/工具表现章节 — 场景覆盖不全
- **类型**：需补充内容
- **位置**：「在 Perfetto / 工具中的表现」全文
- **问题**：仅覆盖 3/7 场景的 Trace 描述。缺失：Broadcast 风暴、ContentProvider 冷启动、低内存/GC、文件锁竞争。
- **建议**：为每个缺失场景补充 2-3 句 Trace 表现描述。
- **review 日志**：logs/review/2026-04-08-01-review.md


## [Task6 Review] 14.7 ProfilingManager — 2026-04-08
- **类型**：需重写（代码示例虚构）+ 需验证（对比表格）
- **位置**：基本使用全节 / System Triggered Profiling / Android 17 增强 / 精确控制数据采集 / 实战案例 x3 / 对比表格
- **问题**：经联网搜索验证 AOSP 实际 API 后确认，本章代码示例使用的类名（ProfilingConfig/ProfilingStatus/ProfilingListener/TriggerCondition）和方法签名（registerProfilingListener()等）在 AOSP 中均不存在。实际 API 使用 RequestBuilder 子类 + Consumer<ProfilingResult> 回调模式。Android 17 新增触发器也与文中不同。
- **建议**：
  1. 对照 AOSP `packages/modules/Profiling/` 源码重写全部代码示例
  2. 参照 developer.android.com/guide/topics/profiling 官方文档
  3. Android 16 系统触发使用 `addProfilingTriggers()` + `ProfilingTrigger.Builder`
  4. Android 17 新增触发器：ANOMALY/APP_COMPAT/APP_REQUEST_RUNNING_TRACE（非文中的 WAKEUP_LATENCY 等）
  5. 保留业务场景描述，只替换代码部分
- **review 日志**：logs/review/2026-04-08-04-review.md

## [Task6 Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-08
- **类型**：需确认
- **位置**：全文 DeliQueue 架构描述 vs 掘金素材
- **问题**：掘金素材称 DeliQueue 使用"CLH 队列变体"，本章基于 Google 官方博客描述为 Treiber 栈 + 最小堆。两者是完全不同的数据结构，需确认哪个准确。另外素材摘要提及"重排任务等待队列"，与正文描述的无锁替换机制有概念差异，可能遗漏了任务优先级重排层面。
- **建议**：核实掘金文章原始来源；如果 DeliQueue 确实同时包含任务重排机制，需在正文中补充描述
- **review 日志**：logs/review/2026-04-08-0654-review.md

## [Task6 Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-08
- **类型**：需确认
- **位置**：frontmatter applicable_versions
- **问题**：标注为 API 1 - API 37，但章节核心是 Android 17 的 DeliQueue 变化，范围可能误导读者
- **建议**：考虑缩小范围或增加说明文字
- **review 日志**：logs/review/2026-04-08-0654-review.md


## [Task2A 缺口挖掘] 已检查方向 — 2026-04-08 07:02

### 挖掘结果：本轮未发现评分 ≥ 14 的知识缺口

全书 134 节已覆盖所有主要 Android 性能子系统。以下方向已检查并排除：

1. **AudioFlinger/音频延迟性能** — 评分 12/20
   - AOSP 源码和官方文档丰富，但 source-index 无音频专项素材
   - 音频性能读者面较窄（主要面向音频 App 开发和 OEM 音频调优）
   - 非 2025-2026 热点话题
   - 建议：如有音频专项素材输入可重新评估

2. **AI/ML 推理性能 (NNAPI/TFLite/LiteRT)** — 评分 13/20
   - NNAPI 已在 Android 15 废弃，LiteRT 刚起步
   - 与本书"系统内部机制"定位略有偏差，更偏应用层
   - 16.5 已涵盖 Android 17 行为变更中的 AI 相关内容

3. **SystemUI 性能 (Launcher/通知栏)** — 评分 11/20
   - AOSP SystemUI 源码复杂但非性能架构核心
   - 主要是 App 级优化技巧，非系统内部机制
   - 不足以独立成节

4. **Android HAL 性能抽象层** — 评分 10/20
   - HAL 贯穿全书多处提及，但作为独立性能主题偏窄
   - 无 source-index 素材支撑

5. **Android 虚拟化框架 (AVF)** — 评分 9/20
   - AVF 性能影响尚在早期阶段
   - 读者需求不明确

6. **显示硬件管线 (MIPI DSI/Panel/Display Controller)** — 评分 10/20
   - 过于硬件底层，超出本书"系统级性能分析"范围
   - 无 source-index 素材

7. **source-index 未映射高分素材复查** — 9 项 ≥ 14 分但全部为现有章节的补充素材
   - ANR 素材 → 已映射 ch09
   - Android 13/14 发布 → 已映射 ch16 版本演进
   - GPU counters/预测模型 → 已映射 ch02 渲染
   - Linux 6.14 I/O → 已映射 ch06
   - CPU 利用率 → 已映射 ch05

8. **研究素材复查** — 2026-04-05~07 全部 20 篇研究素材均已映射到现有章节
9. **AOSP 源码结构对照** — frameworks/base 核心服务、system/ 核心守护进程已全覆盖
10. **官方文档对照** — developer.android.com 性能相关 topic 页面已全覆盖

### 结论
全书知识覆盖度已趋于完备。建议后续关注：
- 新 Android 版本 Preview/Beta 带来的新知识点（由 Task5 研究管线驱动）
- 高爷读者反馈中的新需求（由 intake/suggestions.md 收集）
- OEM 厂商优化实践中的新案例（由 ch17 扩展驱动）


### 2026-04-08 08:00 知识缺口挖掘（Task 2A）

**检查方向**：
1. source-index.json 高质量未映射素材：9 项 ≥16 分，全部已映射现有章节（Camera Perfetto×2/Proguard/支付宝体验/Android14发布/ANR非App错/IO优化/CPU利用率）
2. 研究素材（2026-04-07 10篇）：全部映射到现有章节（§16.4/§6.x/§4.7/§8.7/§4.8/§1.15/§7.9/§14.10）
3. 每日信息（2026-04-07）：UI-Voyager(GUI Agent)/DeliQueue/Android17适配/Android15适配/性能问题实证论文 — 全部映射
4. AOSP 源码结构：frameworks/base 核心服务已全覆盖，system/ 守护进程已全覆盖
5. 官方文档：developer.android.com 性能 topic 页面已全覆盖
6. 已有章节扩展锚点：仅 1 个空扩展（§7.8 Compose LazyColumn vs RecyclerView），不足以独立成节
7. 候选缺口「Android On-Device AI/ML 推理性能 (NNAPI/LiteRT/NPU)」：评分 16/20（素材4+相关性3+需求4+时效5），但与全书 Perfetto/系统分析核心范式偏离较大（ML 推理在 Perfetto 中缺乏可视化追踪点），暂不录入
8. 候选缺口「Android 游戏性能综合优化」：评分 15/20，但核心内容已分散覆盖于 §5.9 ADPF/§2.17 Frame Pacing/§7.4 典型场景，独立成节价值有限

**结论**：本轮未发现评分 ≥ 14 且与全书定位高度匹配的新知识缺口。全书 148 个源文件、125 个已有实质内容，知识覆盖趋于完备。
**建议**：后续关注 Android 17 Beta/RC 阶段新披露的性能变更（由 Task5 研究管线驱动），以及高爷读者反馈中的新需求。


## 2026-04-08 15:00 Task2A 知识缺口挖掘报告 — 全覆盖确认

> 本轮检查方向：素材索引、研究素材、每日信息、AOSP 结构、官方文档、已有章节扩展
> 结论：无评分 >= 14 的知识缺口，项目已达到全面覆盖状态

### 已检查的候选缺口（均未达阈值）

| 候选 | 素材 | 相关性 | 需求度 | 时效性 | 总分 | 不创建原因 |
|------|------|--------|--------|--------|------|------------|
| Font/Text Rendering | 2 | 4 | 3 | 2 | 11 | 素材不足，无 source-index 条目 |
| Analytics/SDK Performance | 2 | 3 | 4 | 2 | 11 | 话题过于广泛，非系统级机制 |
| Gradle Build Performance | 3 | 2 | 4 | 2 | 11 | 与全书"系统运行机制+性能优化"定位不匹配 |
| Notification Dispatch | 2 | 3 | 2 | 2 | 9 | 性能影响有限，非核心性能维度 |
| Process Death & SavedState | 2 | 3 | 2 | 2 | 9 | 素材不足，可归入现有章节扩展 |
| System UI Rendering | 2 | 3 | 2 | 2 | 9 | OEM 专属话题，受众窄 |
| Automotive/Wear | 1 | 2 | 2 | 3 | 8 | 超出全书范围 |
| Sensor Pipeline | 1 | 3 | 2 | 2 | 8 | 素材极度匮乏 |
| Accessibility Performance | 1 | 2 | 1 | 2 | 6 | 话题过窄 |
| OTA/Update Engine | 1 | 2 | 1 | 2 | 6 | 非应用/系统开发者关注焦点 |

### queue.json 状态漂移备注
以下 queue 条目标记为 pending 但实际已 ready-for-review（建议 Task2B 或 metadata 清理任务修正）：
- 4.7 16KB Page Size
- 8.7 Baseline Profiles
- 1.15 JNI/NDK
- 14.10 eBPF/BPF
- 2.19 刷新率切换
- 7.10 Bitmap
- 16.5 Android 17 变更
- 2.20 多窗口桌面
- 15.8 性能问题实证

### 下一步建议
- 聚焦现有 pending 章节的内容加工（1.14 锁竞争、7.11 WebView）
- 修正 queue.json 状态漂移
- 转向 task2b 精修 + task6 审校管线

## 2026-04-08 18:00 知识缺口挖掘记录（Task 2A）

### 检查范围
- source-index.json: 271 篇素材，9 篇高分无映射（均已有对应章节）
- 研究素材: 2026-04-08 最新 9 篇（Audio×3、Network×1、Image×3、Kernel×2）
- 每日信息: 2026-04-05~07 共 3 天
- AOSP 结构: frameworks/base/services（AMS/PMS/WMS/CP 已覆盖）
- 官方文档: Android 17 API 37 性能变更（DeliQueue/GenGC/static final/ProfilingManager 均已覆盖）
- 已有章节扩展: Ch3 Input 较薄但已有 3.5/3.6 待加工 draft

### 候选缺口评估（均未达 ≥14 分）
1. **Notification 性能与 ANR** — 素材 2/5 · 相关 3/5 · 需求 3/5 · 时效 2/5 = 10/20
2. **DisplayManagerService 性能** — 素材 2/5 · 相关 4/5 · 需求 3/5 · 时效 4/5 = 13/20
3. **SELinux 性能影响** — 素材 1/5 · 相关 2/5 · 需求 2/5 · 时效 1/5 = 6/20
4. **ConnectivityService 性能** — 素材 1/5 · 相关 2/5 · 需求 2/5 · 时效 2/5 = 7/20
5. **Kernel ftrace/perf_events** — 素材 2/5 · 相关 3/5 · 需求 2/5 · 时效 2/5 = 9/20

### 结论
全书 118+ 小节已覆盖 Android 性能分析核心知识体系。剩余工作集中在：
1. 已有 draft 章节的加工完善（10 个 draft）
2. FRESHNESS 时效性更新（54 条 pending）
3. 审校精修推进（Task 2B + Task 6）

## [Task6 Review] 8.5 案例集 — 2026-04-08
- **类型**：需确认
- **位置**：误区二段落（"Baseline Profiles 只对首次启动有效"的纠正段落末尾）
- **问题**："Android 13+ 引入了 ART Mainline 模块" — ART 作为 APEX Mainline 模块从 Android 12 (API 31) 起已存在。此处写 Android 13+ 可能不准确。如果是指特定的 Profile 命中率增强，需补充说明。
- **建议**：确认版本号后修正。若准确为 Android 12，改为 "Android 12+"；若 Android 13 确有相关增强，补充具体说明。
- **review 日志**：logs/review/2026-04-08-1920-review.md


## [Task2A Gap Mining] 2026-04-08 20:04 知识缺口挖掘记录

本轮挖掘已检查以下方向：
1. **AOSP 结构比对**：frameworks/base/ 核心服务 → AMS(1.8)/PMS(1.9)/CP(1.10)/WMS(2.12)/SF(2.6) 均已覆盖
2. **官方文档比对**：developer.android.com/performance 主要 topic 均已有对应章节
3. **source-index.json 未映射素材**：35 篇 Android 相关高质量未映射素材中，大部分实际已有对应章节（索引未更新），仅「支付宝 APM(17)」「GPU counter 优化(14)」等少数有延伸价值但不足以独立成节
4. **研究素材**：最近 5 个 research feed 均已映射到现有章节（8.9/7.12/1.16）
5. **每日信息**：2026-04-07/06 daily info 中 Android 相关话题均已有对应章节
6. **已有章节深挖**：现有章节扩展点素材不足，不建议拆分

创建新章节：
- ✅ 13.9 Android Tracing 基础设施（16/20）

已排除的候选（< 14 分）：
- Android GPU Hardware Counter 分析（12/20）→ 素材不足
- Android 网络栈系统服务（11/20）→ 与 12.2-12.4 重叠
- Android Display 管线内部（12/20）→ 与 2.18/2.19 重叠
- Android 信号处理与 Crash 性能（12/20）→ 过于狭窄
- Android Font/Text 渲染性能（11/20）→ 素材不足

## [Task2A 知识缺口挖掘] 2026-04-08 22:03 — 无合格候选

本轮已检查方向（避免重复挖掘）：

### 素材索引扫描
- source-index.json 中 high-quality unmapped (>=16分) 仅 4 条：ANR案例(18)、Android14发布(17)、Linux I/O(17)、CPU利用率(16)
- 4条均已映射到现有章节（Ch9 ANR / Ch16 版本 / Ch6 存储 / Ch5 调度）

### 研究素材扫描
- 最近 10 个 research-feeds 均已映射到现有章节：
  - Audio → 1.16 Audio Pipeline
  - ADPF/Game → 8.9 / 5.9
  - View hierarchy → 7.12
  - JNI optimization → 1.15
  - Network → 12.2 / 16.5

### 每日信息扫描
- 2026-04-06/07 daily-info 主题：
  - DeliQueue/MessageQueue → 已有 1.13
  - Android 17 适配/侧载 → 已有 16.5
  - Compose 性能 → 已有 7.7
  - 布局调试 → 已有 7.12 / 14.1
  - 协程 Semaphore → 已有 8.6
  - 前后台判断 → 已有 1.3 / 8.4

### AOSP 结构对比
- frameworks/base/services/ 核心服务覆盖：AMS(1.8)✓ PMS(1.9)✓ WMS(2.12)✓ SF(2.6)✓ IMS(Ch3)✓ PMS-Power(Ch5/11)✓
- 未覆盖但有性能相关的服务：NotificationManagerService、SensorService、ClipboardService
- 评估：均不足以独立成节（素材稀薄，读者需求低，总分 < 10）

### 已有章节扩展点
- 扫描 src/ 全部 158 个章节：无 [待补充] 扩展点残留

### 候选缺口评估（均未达标）
1. Android 构建与编译性能优化 → 素材1/5 + 相关性3 + 需求4 + 时效4 = 12/20
2. Notification 管线性能 → 素材2 + 相关性3 + 需求3 + 时效3 = 11/20
3. Android 权限/SELinux 性能 → 素材1 + 相关性2 + 需求2 + 时效3 = 8/20
4. OTA/A/B Partition 性能 → 素材1 + 相关性2 + 需求1 + 时效2 = 6/20
5. Accessibility 性能 → 素材2 + 相关性2 + 需求3 + 时效3 = 10/20
6. CI/CD 性能回归测试 → 素材3 + 相关性4 + 需求4 + 时效4 = 15/20（但与 15.6/14.6 重叠度高，实质是扩展而非新章节）
7. Sensor 管线性能 → 素材1 + 相关性2 + 需求1 + 时效2 = 6/20

### 结论
全书 158 节已覆盖 Android 性能领域绝大部分知识点。剩余候选缺口要么素材不足以支撑 3000-8000 字独立章节，要么与现有章节重叠严重。建议下一轮将重点转向：现有章节精修(Task 2B/6)、前沿研究素材持续积累(Task 5)、以及已有章节的深度扩展。

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-04-08
- **类型**：源码准确性
- **位置**：各层职责边界节 → SurfaceFlinger 部分
- **问题**：SurfaceFlinger 的 `handleMessageRefresh` → `doComposition` 调用链缺少中间步骤（`prepareFrame`/`postFrame`/`advanceFrame`），正文描述为"两个关键 CPU 切片"但实际 SurfaceFlinger 的内部处理有多个阶段，影响读者理解其合成管线的完整性
- **建议**：补充 SurfaceFlinger 合成管线的完整方法调用链，并说明每个阶段在 Perfetto 中的 Track 表现

- **类型**：版本差异
- **位置**：Ashmem 描述段落（"Linux 内核层"中的 Ashmem 说明）
- **问题**：Ashmem 在 Android 11 已废弃（被 ION/MemoryHeapAllocator 替代），正文描述未注明版本状态，可能让读者误以为当前系统仍在使用 Ashmem
- **建议**：补充"Ashmem 在 Android 11 已废弃"的版本说明，或补充 Ashmem → ION 的演进关系

- **类型**：版本差异
- **位置**：`applicable_versions: "Android 8 (API 26) - Android 16 (API 36)"`
- **问题**：正文声称覆盖 API 26-36，但 Android 16 架构变化仅有两个子节（Mainline + 16KB page size），16KB page size 实为 Android 15 引入。Android 8/9/10/11 等版本的重大架构变化（Treble、Android 9 Mainline、Android 10-12 GKI）在正文中仅有零散描述，缺乏系统梳理
- **建议**：为 `applicable_versions` 给出更准确的版本范围说明（如 API 26-35），或在正文补充各版本架构里程碑的系统对照表

- **类型**：数据缺失
- **位置**：Zygote fork 耗时 "20-50ms" 段落
- **问题**：该数据标注 `[待验证]` 但位于 ready-to-publish 章节，是正文唯一的量化性能数据，未经核实存在出版风险
- **建议**：移除具体数值区间，改为量级描述"通常在几十毫秒量级（取决于预加载资源量）"，附注"需多设备实测"

- **类型**：数据缺失
- **位置**：Binder 单次调用延迟 "约 10-100μs" 段落
- **问题**：同样标注 `[待验证]`，且 10-100μs 跨度达 10 倍，缺乏设备/数据大小条件
- **建议**：补充具体测量条件（如"无数据传输、Snapdragon 8 Gen 2 Android 14"），或标注为"量级估算"

- **类型**：数据缺失
- **位置**：Activity 冷启动 "可能包含 20-50 次 Binder 调用" 段落
- **问题**：来源标注"社区测量"，20-50 次跨度大，无版本/设备/场景说明
- **建议**：拆分为具体场景（zygote fork / AMS attach / Activity onCreate）分别估算，或补充来源链接

- **类型**：交叉引用
- **位置**：全文 related_chapters 元数据 vs 正文引用
- **问题**：`related_chapters: ["1.2", "1.3", "2.1", "3.1", "4.1", "5.1", "7.1"]` 在正文中一次都没有出现，读者不知道这些章节存在
- **建议**：在正文涉及相关章节的内容处插入交叉引用（如 SurfaceFlinger 处链接到 2.1，LMK 处链接到 4.4，Zygote 处链接到 1.11）

- **类型**：交叉引用
- **位置**：HAL 层零拷贝共享内存通道段落
- **问题**：提到"关键 HAL 设计了零拷贝的共享内存通道"，但未引向第 2.15 节（DMA-BUF/Gralloc）
- **建议**：添加"详见 2.15 节 DMA-BUF 与跨进程图形内存共享"的内联引用

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-08
- **类型**：源码准确性
- **位置**：ZygoteInit.java 的 startSystemServer() 引用
- **问题**：正文引用 `ZygoteInit.java` 中定义 `startSystemServer()` 方法，但该方法实际在 `Zygote.java` 中；ZygoteInit.java 仅包含入口和调用方。preloadClasses()/preloadResources() 方法同样位于 Zygote.java 而非 ZygoteInit.java
- **建议**：将所有预加载方法引用更正为 `Zygote.java`；ZygoteInit.java 的作用是入口（main 方法），不包含具体预加载实现

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-08
- **类型**：源码准确性
- **位置**：preloaded-classes 文件路径
- **问题**：`/apex/com.android.art/etc/preloaded-classes` 路径表述不够精确，实际 build 时该文件位于 `apex/com.android.art/etc/`（或经过裁剪），具体路径因 ART 模块实现而异
- **建议**：核实 AOSP android-16.0.0_r1 中 preloaded-classes 的精确 APEX 内路径

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-08
- **类型**：版本差异
- **位置**：Android 16 启动优化章节（并行内核模块加载、AutoFDO）
- **问题**：声称的 30%/25%/2.1% 性能数据均标注 `[待验证]`，applicable_versions 包含 API 36 但核心数据未经验证，作为 ready-to-publish 章节风险较高
- **建议**：找到 AOSP Gerrit commit 或 9to5Google/Android Police 原文，补充具体来源链接；或将百分比改为"实测减少约 X%"

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-08
- **类型**：数据缺失
- **位置**：cgroup CPU 核心分配示例
- **问题**：`write /dev/cpuset/foreground/cpus 4-7` 假设 8 核设备且配置固定，但不同 SoC（高通/MTK/Exynos）cpuset 配置差异很大，该示例可能误导读者
- **建议**：添加 `[设备相关]` 标注，说明这是高通平台的常见配置示例，或改为更通用的描述"通过 cgroup 设置系统服务 CPU 亲和性"

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-08
- **类型**：交叉引用
- **位置**：全文 related_chapters 声明但无正文引用
- **问题**：frontmatter related_chapters 列出 7 个章节，但正文一次也没有使用交叉引用语法（如 `[[1.1 Android 分层架构]]`），读者无法直接跳转
- **建议**：在 SurfaceFlinger（native 服务表格）、Zygote 预加载（可引用 1.3）等位置补充至少 3-5 处交叉引用

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-08
- **类型**：版本差异
- **位置**：startApexServices 引入版本标注
- **问题**：`[待验证: startApexServices 从 Android 10 引入]` 标注说明引入版本有争议，需确认 startApexServices 作为 TimingsTraceAndSlog 追踪阶段的添加版本
- **建议**：在 AOSP frameworks/base/services/java/com/android/server/SystemServer.java 中搜索 startApexServices 的 git log，确认该追踪阶段首次出现的版本

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-08
- **类型**：知识盲区
- **位置**：Direct Boot 机制
- **问题**：正文提到 `ACTION_LOCKED_BOOT_COMPLETED` 但没有解释 Direct Boot 机制（Android 7.0 引入，允许锁屏状态下特定组件启动），是重要知识空白
- **建议**：在"启动时间度量"或"误区"节补充 Direct Boot 说明（为什么需要、哪些组件支持、如何在 manifest 中声明）

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-09
- **类型**：版本差异
- **位置**：版本演进表 — sync barrier 引入版本
- **问题**：表格称'Android 4.1 (API 16) — 同步屏障用于 Choreographer VSync 优先级'。VSync 机制和 Choreographer 是在 Android 4.1（API 16）随 Project Butter 一起引入的，这个时间点基本正确。但同步屏障（target==null）本身在更早版本就存在（用于 MessageQueue 内部管理），正文没有区分这个细节
- **建议**：区分'同步屏障机制本身（API 1 就存在）'和'Choreographer 利用同步屏障实现 VSync 优先级（API 16）'

- **类型**：版本差异
- **位置**：Choreographer 协作章节
- **问题**：正文描述 VSync-app → doFrame 路径，但没有说明在 Android 17 之前，Choreographer 的 FrameDisplayEventReceiver.onVsync 是如何与 MessageQueue 交互的（即 enqueueMessage 的具体路径）。对比说明会让读者理解 DeliQueue 带来的具体改善
- **建议**：补充 Android 16 中 VSync 回调消息入队的具体路径（从 onVsync 到 enqueueMessage 到 next()），再与 Android 17 对比

- **类型**：知识盲区
- **位置**：Message 回收与对象池
- **问题**：DeliQueue 中消息从栈 drain 到堆后，原来的 Message 对象会被回收（Message.obtain() 从对象池获取）。但 DeliQueue 的无锁入队（push）意味着多个线程同时 obtain/push，回收池的并发访问是否也是 lock-free 的？这是理解 DeliQueue 完整性的关键一环
- **建议**：补充 Message.obtain() 对象池在多线程下的实现（是否 lock-free，或是否存在池竞争）

- **类型**：知识盲区
- **位置**：removeCallbacks / removeMessages 与 tombstoning 的交互
- **问题**：如果一个消息已经被 push 到 Treiber 栈，但还没被 drain 到堆，此时调用 removeCallbacks/removeMessages 能否正确移除？ tombstone 机制如何与消息取消操作协调？
- **建议**：补充消息取消（removeCallbacks/removeMessages）在 DeliQueue 中的具体行为

- **类型**：数据与案例支撑
- **位置**：drain 操作 — 批量转移的量化
- **问题**：正文称'drain 是批量操作，即使有 100 个线程同时 push 了 100 条消息，Looper 线程只需要一次 drain 就能全部转移'，但没有说明 drain 操作本身在 next() 中占用的时间量级。如果 drain 本身耗时较长（比如 1000 条消息的排序），是否会影响 next() 的响应延迟？
- **建议**：补充 drain 操作的预期时间复杂度（O(n) + 堆插入 O(log n)），并说明在最坏情况下（大量消息同时入队）的行为



## [Task6 Review] 9.5 ANR 案例集 — 2026-04-09
- **类型**：需补充素材
- **位置**：全文（案例覆盖范围）
- **问题**：outline 锚点要求覆盖「死锁」类 ANR 案例，当前 5 个案例（系统负载/SystemServer/SharedPreferences/进程冻结/启动超时）未包含明确的死锁场景
- **建议**：补充一个主线程死锁 ANR 案例（如 synchronized 锁顺序不当导致的死锁，或 Binder 线程池耗尽导致的隐式死锁），按现有案例格式（问题现象→分析过程→根因→修复→举一反三）编写
- **review 日志**：logs/review/2026-04-09-01-review.md

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-09
- **类型**：源码准确性
- **位置**：ZygoteInit 代码块
- **问题**：代码为伪代码而非真实 AOSP 源码片段，与 ZygoteInit.java 实际结构不符
- **建议**：移除代码块或改为正确引用实际代码路径/行号；或明确标注为示意代码
## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-09
- **类型**：版本差异
- **位置**：Phantom Process Killer 章节
- **问题**：32 子进程上限描述过于简化；AOSP 实际限制涉及 per-UID 和 per-app-per-boot 配置
- **建议**：补充说明为 AOSP 默认值，受厂商配置影响；更新[待验证]标注
## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-09
- **类型**：知识盲区
- **位置**：AMS 动态调整优先级章节
- **问题**：只列了触发因素，未说明 updateOomAdjLocked() 的具体调用路径
- **建议**：补充 startActivity/bindService/finishActivity 等场景对应的 oom_adj 变化链
## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-09
- **类型**：数据缺失
- **位置**：Binder IPC 章节
- **问题**：90% 是具体数据断言，无来源引用
- **建议**：补充数据来源或改为定性描述主力 IPC 机制
## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-09
- **类型**：源码准确性
- **位置**：oom_adj 表格 HOME_APP=600 行
- **问题**：该值需在 AOSP android-16.0.0_r1 ProcessList.java 中验证准确性
- **建议**：grep AOSP ProcessList.java 确认 HOME_APP 对应的 oom_adj 值

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-09
- **类型**：源码准确性
- **位置**：maxBufferCount 参数描述
- **问题**：三缓冲实现中，maxBufferCount=3 不是直接控制三缓冲的参数；更准确地说 maxDequeuedBuffers=1（生产者端）间接决定了三缓冲行为，两者需区分
- **建议**：修正参数描述，说明 maxBufferCount 是总 slot 数，maxDequeuedBuffers 控制生产者端可持有缓冲区数，两者共同决定缓冲效果
- **类型**：原理断裂
- **位置**：三缓冲机制 → 为什么是 3
- **问题**：只解释了"有缓冲可用"的优势，但未解释为什么选择 3 而不是 4 或 adaptive buffer；读者可能认为 3 是 magic number
- **建议**：补充说明"3 是系统延迟与内存占用的平衡点"的工程考量，或补充 Android 13/14 中是否可配置的说明
- **类型**：版本差异
- **位置**：AsyncBufferQueue 描述
- **问题**：文中介入"Android 16 中引入了 AsyncBufferQueue"，但 BlastBufferQueue 是 Android 12 引入的；AsyncBufferQueue 与 BlastBufferQueue 的关系（同一机制的新名字 vs 不同机制）未说明
- **建议**：补充说明 AsyncBufferQueue 是 BlastBufferQueue 的演进还是新机制，引用 AOSP 相关 change
- **类型**：数据缺失
- **位置**：GPU 渲染管线各阶段 / 三缓冲延迟优势 / Vulkan vs OpenGL ES 开销
- **问题**：多处关键断言缺少量化数据（GPU 各阶段典型耗时、三缓冲延迟具体值、Vulkan vs OpenGL 性能差异百分比）
- **建议**：补充 benchmark 数据或 Perfetto Trace 片段；如暂无数据，将模糊断言改为定性描述并标注 [待验证: 量化数据待补充]

---

## [2026-04-09 03:00] 缺口挖掘已检查方向（Task 2A）

以下方向已在本轮评估中检查并排除（评分 < 14），下一轮挖掘请跳过：

1. **素材索引未映射条目**：11 条 score≥14 的未映射文件已逐一评估，均为已有章节的补充素材（ANR案例、CPU理论、GPU counters）或泛主题（Android版本通稿、LLM书籍）
2. **研究素材**：5 篇最新（4/8）全部已映射到现有章节（8.9/7.12/1.16/16.5）
3. **每日信息**：4/5-4/7 三天内容无未覆盖热点
4. **AOSP 核心服务**：AMS/PMS/WMS/AudioFlinger/lmkd/installd/vold/NNAPI 全部已有章节覆盖
5. **候选方向排除**：HAL性能(10分)、安全性能(10分)、日志系统(9分)、OTA(7分)
6. **章节扩展点**：12 个章节的扩展锚点均为深入方向，不足以独立成节

结论：全书 144 节，覆盖率已达高饱和状态。新缺口需等待新版本/新技术出现。


## [Task9 Deep Review] 2.10 GPU 渲染深入 — 2026-04-09
- **类型**：源码准确性 + 原理断裂 + 数据缺失
- **位置**：GPU 内存管理章节 / Vertex Bound 章节 / ANGLE 性能章节 / 案例截图
- **问题**：
  1. VkShaderModuleCreateInfo Vulkan 示例代码无来源说明（可能是示意性代码而非 AOSP 源码）
  2. Skia Canvas → GPU 命令转换的中间层（DisplayList/SkSL 生成）未展开，RenderThread 行为的关键一环缺失
  3. ANGLE 性能数据"2-5%/5-10%/10-20%"未标注具体来源（哪一届 Google I/O 演讲）
  4. 案例中 4 处 `[待高爷补充：Perfetto Trace 截图]` 影响案例说服力
  5. GPU fillrate/带宽 bound 段落缺少典型移动 GPU 性能量化指标参考表
- **建议**：
  1. 为 Vulkan 示例补充标注（"以下为标准 Vulkan API 示意代码，非 AOSP 源码"）
  2. 在 Skia → GPU 转换段落补充 DisplayList/SkSL 生成机制简述（100-200 字）
  3. ANGLE 数据补充具体来源（建议 Google I/O 2022/2023 对应 session）
  4. 案例截图作为优先补充项（建议高爷提供 Trace 文件或截图）
  5. 在 fillrate/bandwidth bound 段落增加"主流移动 GPU 性能参考表"

## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-09
- **类型**：数据缺失
- **位置**：Line 100, Line 263
- **问题**：2 处 [待补充：Trace 截图] 占位符未替换为实际 Perfetto 截图（BufferQueue 四步操作 Perfetto 截图 + 正常/异常 SF Perfetto 对比截图）
- **建议**：补充 2 张实际 Perfetto Trace 截图，一张展示 dequeue→queue→acquire→release 在 App 和 SF 双进程的完整流转，另一张对比正常 SF REFRESH（约 3-5ms）和异常 SF REFRESH（>10ms）的实际 Trace 片段

## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-09
- **类型**：版本差异
- **位置**：版本演进章节 + 主循环章节
- **问题**：Vulkan RenderEngine 后端引入版本标注 [待验证]；Android 15/16 零覆盖；Android 14 架构重构仅一句带过
- **建议**：
  1. 验证 Vulkan RenderEngine 后端具体引入版本（Android 12L 为初始引入，Android 13 为默认后端切换）
  2. 补充 Android 15/16 SurfaceFlinger 相关变化（如有）
  3. Android 14 ICompositor 重构需在主循环节给出 Android 12-13 vs Android 14+ 流程对比

## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-09
- **类型**：知识盲区
- **位置**：VSync 分发一节
- **问题**：DispSync（Android 12 前）和 VsyncModulator（Android 12+）的内部机制未展开，仅一句话带过
- **建议**：补充 DispSync 的 refresh period 计算逻辑，以及 VsyncModulator 如何在 Android 12 后动态调整 offset 的机制

## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-09
- **类型**：知识盲区
- **位置**：Jank 与 SurfaceFlinger 关系章节 + 合成方式章节
- **问题**：FrameTimeline 深度不足（仅在版本演进和 Jank 节各一句话带过）；HWC Overlay Plane 数量"4-16"范围过宽
- **建议**：
  1. FrameTimeline：补充数据结构（FrameTimelineThread, VsyncId, FrameEvents）、VsyncSource 关系、在 Perfetto gfx/frame timeline track 中的实际体现
  2. HWC Overlay：补充具体范围说明（骁龙 8 Gen 1+ 可达 16-32 个，麒麟 9XXX 可达 8-16 个），并说明与中低端设备差异

## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-09
- **类型**：交叉引用
- **位置**：§7.3 引用
- **问题**：Jank 节引用§7.3（卡顿分析方法论）来引用 SurfaceFlinger 排查方法，但 7.3 章节较大（13 个子章节），未明确 SF 排查在 7.3 中的具体位置
- **建议**：明确引用§7.3 中的具体小节（如"详见 §7.3（卡顿分析方法论 → SF 卡顿排查）"），或在 7.3 的 03-jank-methodology.md 中增加对 2.6 的反向引用

## 2026-04-09 待分类/暂存

### Android 开发中，准确判断应用处于前台（Foreground）还是后台（Background）
- 链接：https://juejin.cn/post/7595108457496346639
- 类型：技术文章
- 摘要：详细解析Android应用前后台状态判断的多种方法，包括ActivityLifecycleCallbacks、ComponentCallbacks、ProcessLifecycleOwner等技术方案的优缺点分析。
- 推荐章节：ch04-activity
- 原因：无法匹配章节

### 什么 AI 写 Android 最好用？官方做了一个基准测试排名
- 链接：https://juejin.cn/post/7614897667961143347
- 类型：技术文章
- 摘要：解读谷歌Android Bench基准测试，对比主流AI编程助手在Android开发场景下的性能表现。
- 推荐章节：ch16-ai-mobile
- 原因：无法匹配章节



## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-09
- **类型**：源码准确性
- **位置**：RenderThread 章节（"主线程阻塞在 eglSwapBuffers 或 glFinish 上"）
- **问题**：eglSwapBuffers 本身不阻塞主线程——它将待显示帧入队后立即返回；真正阻塞主线程的是 glFinish（强制等待 GPU 完成所有 pending 命令）。错误地将 eglSwapBuffers 列为阻塞原因，会误导读者在实际分析中定位错误方向。
- **建议**：修正为"glFinish 强制等待 GPU 完成命令，阻塞主线程"。补充说明：Android 5.0 之前 GPU 命令提交在主线程，glFinish 是主线程卡顿的根因；Android 5.0 引入 RenderThread 后，GPU 命令提交与主线程分离，glFinish 的阻塞影响才被消除。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-09
- **类型**：数据缺失
- **位置**：SkiaVulkan 章节（"CPU 开销降低约 30–50%"）
- **问题**：具体数值没有来源标注，也无测试条件说明。读者无法判断数据的可信度和适用范围。
- **建议**：标注数据来源（skia.org benchmark 或 Khronos Vulkan performance paper），或降低表述精确度为"显著降低"。如无可靠来源，建议改为"Vulkan 的多线程命令构建减少了驱动层 overhead，实际 benchmark 因场景差异较大"。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-09
- **类型**：版本差异
- **位置**：Android 16 章节（"OpenGL ES 不再接受新特性开发，进入维护模式"）
- **问题**：ANGLE 在所有 Android 16 设备上默认启用，OpenGL ES App 实际上仍然完整可用。"进入维护模式"是战略层面，不是实际功能层面。读者可能误解为 OpenGL ES 在 Android 16 上已不可用。
- **建议**：修正表述为"Vulkan 成为官方推荐图形 API；ANGLE 层自动将 OpenGL ES 翻译为 Vulkan"；补充说明 ANGLE 翻译本身并非零成本，部分场景下 Vulkan 原生 API 仍有明显优势。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-09
- **类型**：数据缺失
- **位置**：Frame Pacing Library 章节（"Unreal Engine 已集成 Swappy"）
- **问题**：没有版本引用，也没有说具体是哪个版本的 Unreal Engine 集成了。读者无法核实。
- **建议**：补充具体版本引用（如 Unreal Engine 5.x 或具体发行版本），或改为"部分游戏引擎（如 Unreal Engine 5.x）已集成 Frame Pacing Library"，并给出官方文档链接。

## [Task9 Deep Review] 2.9 渲染机制的版本演进 — 2026-04-09
- **类型**：原理断裂
- **位置**：SkiaGL → SkiaVulkan 演进原因
- **问题**：SkiaVulkan 的优势描述中提到了"多线程并行构建和提交 GPU 命令"，但没有解释"为什么多线程构建命令缓冲区能提升帧率"——缺少从 GL ES 单线程提交到 Vulkan 多线程提交的因果链。
- **建议**：补充完整因果链：GL ES 驱动要求所有 GPU 命令从单一线程同步提交（驱动内部有隐式同步）→ Vulkan 允许多线程并行构建 command buffer → 主线程不再等待 GPU → 帧率更稳定，CPU 开销降低约 30–50%。


## [Task9 Deep Review] 1.5 线程模型 — 2026-04-09
- **类型**：源码准确性
- **位置**：RenderThread 创建时机描述（"当 Activity 第一次执行 draw 操作时"）
- **问题**：RenderThread 初始化时机描述不准确。android-16 中 ViewRootImpl 构造时即初始化 ThreadedRenderer（硬件加速时），并非延迟到首次 draw 调用。此描述反映的是 Android 8.x 以前的行为
- **建议**：修正为"在 ViewRootImpl 构造时（hardwareAccelerated=true 条件下）即初始化 ThreadedRenderer 和 RenderThread"

## [Task9 Deep Review] 1.5 线程模型 — 2026-04-09
- **类型**：数据缺失
- **位置**：cgroup CPU 分配比例（"前台 cgroup 和后台 cgroup 的 CPU 时间分配比例大约是 95:5"）
- **问题**：95:5 比例缺乏具体版本依据。Android 12+ 使用 cgroup v2，其 cpu.max 默认 enforcement 与 cgroup v1 的 cpu.shares 机制不同，实际比例在不同版本/设备上有差异
- **建议**：改为更精确的描述，例如"Android 12+ cgroup v2 下，后台 cgroup 的最大 CPU 占用受 cpu.max 配置限制，典型值为 1:1 或 2:1"，并补充 cgroup v1 和 v2 的差异对比

## [Task9 Deep Review] 1.5 线程模型 — 2026-04-09
- **类型**：交叉引用
- **位置**：章节正文引用"1.3 进程模型"；相关章节列表包含 1.4、5.1
- **问题**：正文引用"1.3 进程模型"，但 AIW 中 1.3 是"Zygote 与应用进程创建"；相关章节 1.4 对应章节名与线程模型关联度需确认；5.1 章节是否真实存在
- **建议**：核对 AIW 实际章节结构，修正交叉引用目标，确保引用的章节号与实际内容匹配
