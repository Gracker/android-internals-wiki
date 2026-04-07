---
tags:
  - android
  - npu
  - blog
---

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
