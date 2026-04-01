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
