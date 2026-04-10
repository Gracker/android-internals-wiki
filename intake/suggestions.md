
## [Task2A Gap Mining] 知识缺口挖掘记录 — 2026-04-10 06:05

- **Phase**: Phase 1（无空 draft，进入挖掘模式）
- **结论**: 本轮未发现评分 ≥ 14 的知识缺口
- **已检查方向**:
  1. source-index.json 839 条素材中 high-quality unmapped 仅 4 条（ANR系统问题→可映射ch9/Linux 6.14 I/O→可映射ch6/CPU利用率→可映射ch5/Android14发布→通用信息），均不足以支撑独立章节
  2. research-feeds 最近 14 份研究素材全部已映射到现有章节（1.16/5.9/5.12/7.10/7.12/8.9/12.2/16.5），包括：ADPF+AGDK(19分→8.9)、Hardware Bitmap(19分→7.10)、AudioTrack(18分→1.16)、ImageDecoder(18分→7.10)、Coil3(18分→7.10)、AudioFlinger(17分→1.16)、View层级(16分→7.12)、Android 17网络(16分→12.2)
  3. daily-info 最近 3 天（4/7-4/9）热点：DeliQueue/Android 17适配/Compose/AI编程/UI-Voyager/Flutter鸿蒙/Android Studio Panda，均已覆盖或为非性能话题
  4. AOSP frameworks/base 核心服务（AMS/PMS/WMS/SF/Input/Choreographer/DMS）全部已有对应章节
  5. 官方文档 Android 16/17 性能新特性（Generational GC/DeliQueue/static final/ProfilingManager triggers/ECH/Local Network/Battery Saver alarms/Large Screen mandatory）全部已有对应章节
  6. 已评估额外候选方向：Android 17 ProfilingManager triggers(→14.7已覆盖)、AVF虚拟化(相关度2分)、Encrypted Client Hello(→12.4已覆盖)、Notification渲染管线(素材不足3分)、Kernel 6.12 io_uring(→16.4已覆盖)、K2 Compose Compiler(→7.7已覆盖)，全部不满足 ≥14 分或与现有章节重叠
- **建议**: 
  - 全书已达到极高覆盖率（198小节），后续增量应关注：
    1. Google I/O 2026（5月）可能宣布的新性能 API
    2. Android 17 正式版发布后的行为变更补充
    3. 优先推进 28 个 draft → ready-for-review（重点是 ch18 渲染链路 20 个小节）
    4. queue.json 中 47 条 pending 任务的执行
## [Task2A Gap Mining] 知识缺口挖掘记录 — 2026-04-10 05:06

- **Phase**: Phase 1（无空 draft，进入挖掘模式）
- **结论**: 本轮未发现评分 ≥ 14 的知识缺口
- **已检查方向**:
  1. source-index.json 839 条素材中 high-quality unmapped 17 条（ANR系统问题→ch9/Fence同步→2.16/Input调试→ch3/Camera×2→14.9/支付宝度量→15.5/Android14→1.6/Linux I/O→6.3/Dalvik→4.3/Reddit Baseline→8.7/Proguard→12.1/CPU利用率→5.1/渲染管线→ch2/Binder→1.4/Camera内存→14.9/IO监控→6.3），全部可映射到已有章节
  2. research-feeds 最近 5 份研究素材（ADPF+AGDK 19分→8.9/View层级16分→7.12/AudioTrack 18分→1.16+16.5/AudioFlinger 17分→1.16/Hardware Bitmap 19分→7.10/ImageDecoder 18分→7.10/Coil3 18分→7.10）全部已映射
  3. daily-info 最近 3 天（4/7-4/9）热点：DeliQueue/Android 17适配/Compose/AI编程/UI-Voyager/Flutter鸿蒙，均已覆盖
  4. AOSP + 官方文档：Android 16/17 性能新特性（GenGC/DeliQueue/static final/ProfilingManager triggers/JobDebugInfo/Headroom APIs/Cloud Compilation）全部已有对应章节
  5. 扩展点检查：ApplicationStartInfo（14.7+8.2已覆盖）、WindowInsets Animation（评分约9分，不达标）、Performance Leveling Guide（评分约11分，不达标）
  6. 全部 20+ 候选方向最高评分 ≤ 13/20
- **建议**: 
  - 下轮优先处理 28 个 draft 状态章节（重点是 ch18 渲染链路全景的 20 个小节）
  - 关注 Google I/O 2026 新 announced 的性能 API
  - 关注 Android 17 正式版发布后的行为变更补充

## [Task6 Review] 1.3 进程模型与生命周期管理 — 2026-04-09
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少大纲结构和所有必需锚点（0/5 覆盖率）
- **建议**：按 writing-guide.md 要求添加 outline-start/outline-end 和 5 个必需锚点
- **review 日志**：logs/review/2026-04-09-16b-review.md

## [Task6 Review] 7.5 优化策略 — 2026-04-09
- **类型**：需补充素材/需重写/需验证/需确认
- **位置**：多处章节
- **问题**：多项大问题需要回炉处理
  1. 需补充4个Perfetto Trace截图（布局层级过深、RecyclerView卡顿、线程竞争、Binder调用耗时）
  2. 案例集部分仅有2个案例，需要补充3-5个真实优化案例
  3. 线程优化部分段落超过8行，需要拆分
  4. 预渲染断言缺少具体验证来源
  5. '数据绑定'和'onBindViewHolder'术语不统一
- **建议**：补充Trace截图和实战案例，重写过长段落，完善验证来源，统一术语使用
- **review 日志**：logs/review/2026-04-09-18-review.md



## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-09

### 建议 1
- **类型**：源码准确性
- **位置**：JIT 编译器原理 - 代码注释
- **问题**：`dalvik.vm.jitthreshold` 是 Dalvik（Android 2.2-4.4）参数，ART 不读取此 property。会导致读者用错误参数调试。
- **建议**：改为"阈值由 ART 内部常量（如 kJitThreshold，art/runtime/jit/jit.cc）或 Mainline sysprop 配置"，并注明 dalvik.vm.jitthreshold 是 Dalvik 参数。

### 建议 2
- **类型**：版本差异
- **位置**：JIT 在 Perfetto 中的表现 / 版本演进表
- **问题**：称"首次安装后 JIT 多"，忽略了 Android 7-11 安装时执行 quicken 编译（部分 AOT）的事实。
- **建议**：修正表述："Android 7-11 安装时以 quicken 级别预编译，首次启动仍有部分 AOT 覆盖；Android 12+ 的 speed-profile 在无 Profile 时安装时完全不编译（等于 verify）"。

### 建议 3
- **类型**：版本差异
- **位置**：版本演进表
- **问题**：Android 10 的 JIT prewarming 行为和 compact DEX 引入等关键变化未覆盖。
- **建议**：在版本演进表中补充 Android 10（API 29）：JIT 预热机制引入（减少冷启动 JIT 开销）；compact DEX 格式引入。

### 建议 4
- **类型**：数据缺失
- **位置**：dex2oat 编译优化进展 / AutoFDO 量化数据
- **问题**：多个量化数据（18% dex2oat 提速、AutoFDO 量化效果）的 [已验证] 标注是否来自 Google 官方博客的具体报告存疑。
- **建议**：补充具体 Google Blog 链接，确认量化数字来源。

### 建议 5
- **类型**：知识盲区
- **位置**：Profile-Guided Optimization 体系
- **问题**：未覆盖 Compact DEX（cdex）格式对编译行为的影响。
- **建议**：在 PGO 体系中补充一段：cdex 格式下安装时必须有 AOT 编译，与 raw DEX 的行为差异。

## [Task9 Deep Review] 4.6 内存相关的版本演进 — 2026-04-09
- **类型**：源码准确性
- **位置**：AOSP 源码路径 — Scudo
- **问题**：Scudo AOSP 路径为 `system/memory/libmemunreachable/scudo/`，正确路径为 `external/scudo/standalone/`（Android 集成）和 `compiler-rt/lib/scudo/`（LLVM 上游）
- **建议**：修正为 `external/scudo/standalone/`

## [Task9 Deep Review] 4.6 内存相关的版本演进 — 2026-04-09
- **类型**：源码准确性
- **位置**：AOSP 源码路径 — CMC GC
- **问题**：CMC GC 路径 `art/runtime/gc/collector/concurrent_mark_compact.cc` 需核实；AOSP 实际文件名可能为 `mark_compact.cc`
- **建议**：核实 AOSP android-16 源码 `art/runtime/gc/collector/` 目录下的实际文件名

## [Task9 Deep Review] 4.6 内存相关的版本演进 — 2026-04-09
- **类型**：知识盲区
- **位置**：扩展 — MTE 在 Android 14+ 的推进
- **问题**：MTE 需要 ARMv8.5-A 硬件支持，并非所有 Android 14+ 设备都支持；章节未说明硬件依赖性
- **建议**：补充"MTE 需要 ARMv8.5-A 指令集，各芯片平台支持情况不一，建议 App 通过 `android.os.fea` API 检测"

## [Task9 Deep Review] 4.6 内存相关的版本演进 — 2026-04-09
- **类型**：版本差异覆盖
- **位置**：版本演进速查表 / 正文
- **问题**：Android 12/13 的内存管理变化（内存 reclaim 策略、background 进程内存限制强化）未覆盖
- **建议**：在速查表中补充 Android 12（内存 reclaim 优化）和 Android 13（更严格的 background 进程内存限制）相关变化

## [Task9 Deep Review] 4.6 内存相关的版本演进 — 2026-04-09
- **类型**：数据缺失
- **位置**：进程内存限制与 largeHeap 策略的版本演进 — largeHeap 表格
- **问题**：largeHeap 表格的具体数值（128-512MB 等）标注为"待验证"经验值，缺少权威来源
- **建议**：补充 `adb shell getprop dalvik.vm.heapsize` 在各版本实际设备的输出，或引用官方文档

## [Task9 Deep Review] 2.11 Flutter 渲染管线与性能 — 2026-04-09
- **类型**：版本差异
- **位置**：Flutter DevTools Performance 面板段落
- **问题**：章节称"从 Flutter 3.19 开始 Performance 面板已集成 Perfetto trace viewer"，实际集成时间约在 Flutter 3.13-3.16，3.19 的主要变化是 Impeller 默认化
- **建议**：修正为"Flutter 3.16 期间集成"，补充 [待验证：确认具体版本号]

## [Task9 Deep Review] 2.11 Flutter 渲染管线与性能 — 2026-04-09
- **类型**：数据缺失
- **位置**：Impeller 性能数据段落（帧率稳定性、内存改善数据）
- **问题**：30-50% 性能改善数据引用自"Flutter 团队 2025 年基准测试及第三方测试报告"，但章节自身已标注 [存疑: 非 Flutter 官方基准；HoldApp 报告待确认真实性]，形成数据可信度自相矛盾
- **建议**：将断言降级为"社区报告显示"，补充具体 Flutter 官方博客 post 或 conference session 编号，与存疑标注对齐；考虑将 HoldApp 报告替换为可验证来源

## [Task9 Deep Review] 2.11 Flutter 渲染管线与性能 — 2026-04-09
- **类型**：原理完整性
- **位置**：Shader 编译卡顿（Skia 时代）段落
- **问题**：Skia shader 编译卡顿仅解释了"Raster 线程编译耗时"，未说明移动 GPU driver shader compiler 性能远差于桌面 GPU 的底层原因
- **建议**：补充移动 GPU shader compiler vs 桌面 GPU 的性能差距背景，解释为什么这是 Skia 的 JIT 架构在移动端特有的瓶颈

## [Task9 Deep Review] 2.11 Flutter 渲染管线与性能 — 2026-04-09
- **类型**：交叉引用
- **位置**：与其他章节的关联部分 §2.3 VSync 机制
- **问题**：引用了 §2.3 VSync 机制，但 progress.json 和 src/ 中不存在 2.3 章节（相邻为 2.1 渲染架构全景、2.4 Choreographer）
- **建议**：修正引用目标为正确章节号，或若该 VSync 独立章节不存在则删除该引用行

## [Task9 Deep Review] 2.11 Flutter 渲染管线与性能 — 2026-04-09
- **类型**：知识盲区
- **位置**：Impeller 引擎部分 Vulkan 回退策略段落
- **问题**：章节说明 Impeller 对 Android API 28 及以下回退到 OpenGL ES，但未说明对 Android API 29-32（Vulkan 1.0/1.1 设备）的回退处理
- **建议**：补充 Vulkan 功能集级别（1.0/1.1/1.2+）与 Impeller 支持情况的说明

## [Task9 Deep Review] 2.11 Flutter 渲染管线与性能 — 2026-04-09
- **类型**：知识盲区
- **位置**：Impeller 引擎部分
- **问题**：Skia（immediate mode）与 Impeller（tile-based partial repaint）的渲染架构根本差异未展开，读者难以理解 Impeller 在复杂场景的优势来源
- **建议**：补充 Impeller tile-based 渲染策略与 Skia immediate mode 的架构对比，解释 partial repaint 对帧率的积极影响

## [Task9 Deep Review] 1.6 Android 版本演进中的架构变化 — 2026-04-10

- **类型**：版本差异 / 知识盲区
- **位置**：L113（hwbinder 描述）
- **问题**：章节称"hwbinder 调用通常涉及硬件操作，延迟更高"。hwbinder 的核心特征不是"高延迟"，而是"跨进程边界但比 binder 更轻量"。延迟特征取决于具体 HAL 操作，不能一概而论。
- **建议**：修正描述为"hwbinder 是 Framework 与 HAL 层之间的 IPC 机制，相比 binder 更轻量，适用于硬件操作的跨进程通信"

- **类型**：版本差异
- **位置**：L158（Perfetto 版本差异表）
- **问题**：Android 16 代号（"Baklava"）与 applicable_versions 中"Android 16 (API 36)"存在矛盾，且与正文 L152 "Baklava" vs "Vanilla Ice Cream" 的另一处引用形成内部不一致。API 36 尚未正式发布（Android 16 为 API 35）。
- **建议**：统一 Android 16 的代号标注（建议标注 [待验证]），修正 applicable_versions 为 API 35，并将两处代号引用合并为一致描述

- **类型**：数据缺失
- **位置**：L123（ART Mainline 模块存储节省数据）
- **问题**：章节引用"Google 称这些优化为全球超过 10 亿台设备节省了约 47-95 PB 的存储空间"，但来源是脚注 obsidian 素材而非原始 Google 博客链接。
- **建议**：补充原始 Google 官方博客链接，或添加 [待验证: 来源待查] 标注

- **类型**：交叉引用 / 元数据
- **位置**：frontmatter related_chapters
- **问题**：related_chapters 列出的 8 个章节中，1.4、1.7、5.6 仍为 ready-for-review 状态，2.9 已升至 ready-to-publish。出版前需确认这些章节的状态。
- **建议**：出版前逐一验证 related_chapters 中每个章节的实际状态和章节号/名称是否匹配


## [Task9 Deep Review] 2.12 Window Manager Service 与窗口管理 — 2026-04-10

- **类型**：版本差异
- **位置**：版本演进表（Android 10 → Android 12）
- **问题**：Android 11（API 30）版本变化完全缺失。Android 11 对 WMS 有重要变化：DisplayCutout API 完善（getDisplayCutout() 行为变化）、Bubbles 浮动窗口（涉及 WMS 窗口层级和 z-order 变化）、Shade 窗口变化
- **建议**：补充 Android 11（API 30）的 WMS 变化条目

- **类型**：版本差异
- **位置**：版本演进表（Android 12 → Android 14）
- **问题**：Android 13（API 33）版本变化完全缺失。Android 13 引入了 predictive back gesture developer options、Bubbles API 正式版，以及 Task bar 的引入（对 WMS 的系统栏窗口管理有影响）
- **建议**：补充 Android 13（API 33）的 WMS 变化条目

- **类型**：版本差异
- **位置**：版本演进表（Android 14 → Android 16）
- **问题**：Android 15（API 35）Edge-to-Edge 强制执行对 WMS Insets 分发频率的影响未在版本表中单独列出。Edge-to-Edge 之前是可选行为，Android 15 强制执行后 WMS 的 Insets 计算和分发成为更频繁的操作
- **建议**：补充 Android 15（API 35）Edge-to-Edge 强制对 WMS Insets 分发的增量影响

- **类型**：数据缺失
- **位置**：StartingWindow 部分（「reportDrawFinished 信号来协调」）
- **问题**：「无缝切换」依赖 reportDrawFinished 信号，但没有量化数据：典型设备上从 App 调用 reportDrawFinished 到 WMS 实际移除 StartingWindow 的延迟是多少 ms？这个延迟是否在 VSync 边界上？
- **建议**：补充实测数据或 Perfetto Trace 片段，标注该延迟的典型值和影响因素

- **类型**：源码准确性
- **位置**：Surface 创建流程第5步注释 + 「[待验证] SurfaceControl.Transaction.apply() 是否同步等待」
- **问题**：`Transaction.apply()` 的同步等待行为在 Surface 首次创建时（SurfaceFlinger 完成 Layer 创建后）是否会有不同的行为？该问题标注为「待验证」但未给出验证路径，导致关键结论依赖未确认假设
- **建议**：补充 AOSP 源码路径（SurfaceComposerClient::apply 或 SurfaceControl::apply）并明确注释在何种条件下 apply 是异步的、何种条件下可能同步

- **类型**：知识盲区
- **位置**：relayoutWindow 部分（性能分析）
- **问题**：未覆盖 WMS 的 mGlobalLock 锁竞争机制——这是 WMS 性能问题的核心却未体现。Binder 线程上的 relayoutWindow 被 mGlobalLock 阻塞是常见场景，读者无法据此分析实际 trace
- **建议**：补充 mGlobalLock 的作用机制，说明 relayoutWindow 和 AMS 主线程操作在锁上的竞争关系，以及如何在 Perfetto 中识别此类问题

## [Task2A Gap Mining] 2026-04-10 02:00 缺口挖掘检查记录

- **已检查方向**：source-index 未映射素材、研究素材(research-feeds)、每日信息(daily-info)、AOSP frameworks/base 核心服务、system/ 核心组件、官方文档 Android 16/17 性能特性、已有章节扩展点
- **候选评估**：Display HAL(11)、进程冻结(11)、Accessibility(10)、Sensor(7)、Watchdog(7) — 全部 <14
- **结论**：全书 198 小节已极为全面，本轮无合格缺口
- **下次建议**：关注 Android 17 Beta 后续新特性发布、Google I/O 2026 新 announced 的性能 API


## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：版本差异
- **位置**：TimingsTraceAndSlog 段落 — startApexServices() 描述
- **问题**：声称 startApexServices() 是 Android 16 新增的 TimingsTraceAndSlog 追踪阶段。APEX 模块化架构自 Android 10 引入，startApexServices() 方法在 Android 10+ 已存在。此处应区分"APEX 架构"（Android 10+）和"startApexServices() 作为独立 TimingsTraceAndSlog 追踪 slice"（可能是 Android 14/15 新增）。需查 AOSP 源码确认追踪阶段引入版本。
- **建议**：查 system_server 源码（android-14/15/16 的 TimingsTraceAndSlog 调用），确认 startApexServices 作为独立追踪 slice 的引入版本，据实修正版本标注。

---
- **类型**：数据缺失
- **位置**："Android 16 的启动优化"实测效果段落
- **问题**：三组量化数据（Pixel 10 模块加载减少 30%、2023 Pixel Fold 减少 25%、整体启动时间减少 2.1%）仅有 [待验证] 标注，无任何来源。AutoFDO 声称"Android 16 引入"也有误（Android 15 已有实验支持）。
- **建议**：补充 AOSP Gerrit commit 或 Google 官方博客来源；若无法找到可靠来源，将百分比改为"据报道"或移除具体数字。

---
- **类型**：数据缺失
- **位置**：Zygote 预加载机制 — "3000-4000 个常用类"
- **问题**：preloaded-classes 文件数量在 Android 10+ APEX 模块化后有显著变化。当前 3000-4000 的范围可能引用自旧版 AOSP，Android 10+ 实际数量可能不同。
- **建议**：查 /apex/com.android.art/etc/preloaded-classes（Android 10+）的实际行数，补充版本差异说明。

---
- **类型**：数据/示例缺失
- **位置**：Perfetto 配置示例
- **问题**：提供的 atrace 配置语法为旧版 Systrace 格式，与当前 Perfetto protobuf text format 不兼容，读者复制无法直接运行。
- **建议**：更新为标准 Perfetto CLI 配置格式（buffer_size_kb / duration_ms / data_sources 等），或注明"为可读性简化的 atrace 格式示例"。

## [Task2A 知识缺口挖掘] 全书扫描 — 2026-04-10 03:08

- **已检查方向**：source-index 未映射素材、研究素材(research-feeds 4/7-4/8)、每日信息(daily-info 4/7-4/9)、AOSP frameworks/base + system/ 核心服务、官方文档 Android 17 性能特性、Compose 编译器优化、Cloud Compilation
- **候选评估**：Compose 编译器优化(15但与§7.7重合)、Cloud Compilation(15但跨多章节)、App Hibernation(11)、进程冻结(10)、Display HAL(8) — 2个15分候选与现有章节重叠，不适合新建
- **结论**：全书 163 小节已极为全面，本轮无合格缺口（无 ≥14 分且不重叠的候选）
- **下次建议**：关注 Google I/O 2026 新性能 API、Android 17 Beta 后续特性、优先推进 28 个 draft → ready-for-review

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：源码准确性
- **位置**：frontmatter last_verified_against
- **问题**：章节核心内容是 Android 17 DeliQueue，但验证依据标注为 android-16.0.0_r1（不含 DeliQueue）。读者会误以为 DeliQueue 源码已验证。
- **建议**：待 AOSP android-17 正式 tag 后补充源码路径；frontmatter 增加 DeliQueue 部分尚未 AOSP 源码验证的说明

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：原理断裂
- **位置**：DeliQueue 架构 → VSync 回调优先级
- **问题**：章节花了大量篇幅讲 VSync 依赖同步屏障保证优先级，但 DeliQueue 的 drain 机制（栈→堆）和同步屏障之间如何协同完全没有解释。VSync 异步消息是否仍然通过 tombstone 机制处理？drain 后同步屏障还按原有逻辑扫 mMessages 吗？
- **建议**：补充 DeliQueue 模式下同步屏障的处理逻辑，并标注待 AOSP android-17 源码验证

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：版本差异
- **位置**：版本演进表 + nativePollOnce/epoll 段
- **问题**：nativePollOnce 和 epoll 在 DeliQueue 架构下是否仍有相同作用？Looper 如何感知 Treiber 栈中有新消息从而触发 drain？
- **建议**：补充 Android 17 MessageQueue native 层变化的源码级分析

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：交叉引用
- **位置**：related_chapters: ["1.5", "1.14", "2.4", "2.5", "7.1"]
- **问题**：所有 5 个关联章节在 metadata/progress.json 中均不存在（状态 unknown），交叉引用无效
- **建议**：相关章节创建后逐一核对一致性；暂时在 related_chapters 中标注 [待创建]

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：数据缺失
- **位置**：VSync→doFrame 延迟改善
- **问题**：章节明确描述了 Android 16 vs 17 的 VSync→doFrame 延迟差异（更短、更一致），但标注 [待补充]，是最有说服力的 Trace 证据
- **建议**：补充实际 Trace 截图对比（Perfetto）

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：数据缺失
- **位置**：5000 倍合成基准
- **问题**："比旧实现快 5000 倍"数据没有说明并发线程数、消息插入频率等关键参数
- **建议**：补充基准测试的具体条件描述，或改为"在高竞争合成场景下快 5000 倍"

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：知识盲区
- **位置**：DeliQueue Treiber 栈 push 时序
- **问题**：消息 push 到 Treiber 栈时 when 字段是否已经设定？drain 到堆后排序是否依赖 push 时的 when？多线程并发 push 是否有时序竞争影响 when 正确性？
- **建议**：明确 when 的设置时机（应在 Handler.sendMessage→enqueueMessage 时已设定，栈只负责传消息不负责排序）

## [Task9 Deep Review] 1.13 MessageQueue 机制与 DeliQueue 无锁优化 — 2026-04-10
- **类型**：知识盲区
- **位置**：CPU 缓存行竞争
- **问题**：无锁 CAS 避免了锁阻塞，但 CAS retry 会造成缓存行竞争（cache line bouncing），高竞争下可能成为新瓶颈，章节没有提到
- **建议**：补充 CAS retry 导致的缓存行竞争隐患及其与 monitor lock 的取舍分析

## [Task2A Gap Mining] 知识缺口挖掘记录 — 2026-04-10
- **Phase**: Phase 1（无空 draft，进入挖掘模式）
- **结论**: 本轮未发现评分 ≥ 14 的知识缺口
- **已检查方向**:
  1. source-index.json 799 条素材中 high-quality unmapped 仅 4 条（Android 14 发布、ANR 系统问题、Linux 6.14 I/O、CPU 利用率），均不足以支撑独立章节
  2. research-feeds 最近 8 份研究素材全部已映射到现有章节（1.16/5.9/5.12/7.12/8.9/12.2/16.5）
  3. daily-info 最近 3 天热点（DeliQueue/Android 17 适配/Compose/AI 编程）均已覆盖
  4. AOSP frameworks/base 核心服务（AMS/PMS/WMS/SF/Input/Choreographer）全部已有对应章节
  5. 官方文档 Android 16/17 性能新特性（Generational GC/DeliQueue/static final/ProfilingManager/Vulkan mandatory/Cloud Compilation）均已映射
  6. 评估了 20+ 候选方向（Compose Profiling/Macrobenchmark/heapprofd/Display Pipeline/HAL/Logcat/Accessibility/Sensor/WearOS/Android Auto/KMP/R8/AGDK/DI performance 等），最高评分 13/20
- **Bug 修复**: 3.5 输入事件拦截与安全机制（已存在 src 文件但未录入 SUMMARY.md，已修复）
- **建议**: 下轮优先处理 queue.json 中 46 条 pending 项目（43 条 FRESHNESS + 1 条 priority 85 + 2 条 priority 80）


## [Task9 Deep Review] 2.4 Choreographer 与渲染流水线 — 2026-04-10

### 1. [P2] doFrame 时序固定值标注（行197-208）
- **类型**：数据缺失
- **位置**：行197-208，doFrame 执行时序 ASCII 图
- **问题**：INPUT(0-2ms)、ANIMATION(2-4ms)、INSETS_ANIMATION(4-6ms)、TRAVERSAL(6-15ms)、COMMIT(15-16ms) 以固定值呈现，实际上这些数字因帧复杂度、设备性能、Android 版本差异很大。60Hz 帧预算 16.6ms 是固定的，但各回调阶段耗时完全取决于 UI。
- **建议**：改为"典型值（实际变化）"形式，例如"TRAVERSAL：典型 60-70% 帧时间（变化很大）"，或补充"这些数字在简单帧（如静态界面）可能 <1ms，复杂帧可能 >20ms"

### 2. [P2] 源码行号引用不可验证（行142、行212）
- **类型**：源码准确性
- **位置**：行142引用 `Choreographer.java:1248`；行212引用 `Choreographer.java:842`
- **问题**：android-16.0.0_r1 的 Choreographer.java 约 1500 行，这两个行号在公开代码索引中难以验证其准确性，且不同 AOSP 分支版本行号差异很大。
- **建议**：移除具体行号，改为引用方法名或代码块描述，例如"源码见 `doFrame()` 方法"或"见 CALLBACK_* 常量定义处"

### 3. [P2] FrameMetrics.GPU_DURATION 不可用情况未说明（行305-306）
- **类型**：版本差异
- **位置**：FrameMetrics API 代码示例（行290-315）
- **问题**：`FrameMetrics.METRIC_GPU_DURATION` 并非在所有设备上都可用。部分设备（早期联发科芯片、模拟器、部分定制 ROM）的 GPU 驱动不支持 GPU 时钟计数器，该 metric 返回 0。
- **建议**：补充条件性说明"需要 GPU 驱动支持（在不支持的设备上返回 0）"，并推荐替代方案：Perfetto 的 `gpu_freq` track

### 4. [P2] 4处交叉引用死链（参考资料节+正文§2.5）
- **类型**：交叉引用
- **位置**：参考资料节（行513-516）和正文§2.5交叉引用
- **问题**：
  - `05-mainthread-renderthread.md` → 实际文件名是 `05-main-render-thread.md`（缺少连字符）
  - `../ch03-input/01-input-pipeline.md` → 实际文件名是 `../ch03-input/01-input-dispatch.md`
  - `../../part4-responsiveness/ch08-startup/02-app-startup.md` → `part4-responsiveness` 不存在，应为 `../../part2-performance/ch08-responsiveness/02-app-launch.md`
  - 正文§2.5 引用 `2.5.md` → 实际文件名 `05-mainthread-renderthread.md`（同样死链）
- **建议**：修正为实际存在的文件名，其中 §2.5 参考资料和正文交叉引用均应改为 `05-main-render-thread.md`（并确保该文件存在）；§8.2 改为 `../../part2-performance/ch08-responsiveness/02-app-launch.md`；§3.1 改为 `../ch03-input/01-input-dispatch.md`

### 5. [P3] postFrameCallback 持续注册开销未量化（行317）
- **类型**：数据缺失
- **位置**：行317-319（FrameCallback 注意事项）
- **问题**：文中说"持续注册 postFrameCallback 会增加每帧的回调开销"，但没有给出具体数值（几纳秒？微秒？）。读者无法判断这个开销是否可忽略。
- **建议**：补充量化数据，例如"每次 postFrameCallback 在 doFrame 中增加约 100-200ns 开销（取决于注册次数）"，或给出业界经验值

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-10
- **类型**：数据缺失
- **位置**：Zygote预加载价值段落
- **问题**："几十MB的Framework代码"为模糊估算，缺乏实测数据支撑
- **建议**：补充Zygote fork后预加载的art/oat文件大小实测数据

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-10
- **类型**：数据缺失
- **位置**：oom_adj实时查看段落
- **问题**：章节已有[待补充]标注——Perfetto中oom_adj变化的具体Trace截图缺失
- **建议**：抓取包含"am" category的Perfetto trace，截取oom_adj变化的典型片段

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-10
- **类型**：数据缺失
- **位置**：前台Service oom_adj提升效果
- **问题**："从500提升到0~100"过于简化，实际提升效果取决于多种因素
- **建议**：补充Android 14下不同前台Service类型对应的实际adj值

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-10
- **类型**：知识盲区
- **位置**：Phantom Process Killer章节
- **问题**：32个子进程上限未标注来源和Android版本；Android 16是否有变化未知
- **建议**：补充settings命令说明及风险；标注32为Android 12初始值


## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-04-10
- **类型**：数据缺失
- **位置**：Line 275
- **问题**："Google 的数据是，正确配置 Baseline Profiles 可以提升约 30% 的代码执行速度"，无具体来源
- **建议**：补充来源 URL。实际数据为 Google Maps（30% 启动速度提升）和 Android Calendar（20% 启动 + 50% 慢帧减少），引用 Google Blog 或 android.com 官方文档 Baseline Profiles 概述页面

## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-04-10
- **类型**：源码准确性
- **位置**：Line 226
- **问题**：`art/dex2oat/dex2oat_options.cc` 作为源码引用路径粒度过粗
- **建议**：指向更具体的类文件，如 `art/dex2oat/dex2oat.cc` 中的编译过滤器处理逻辑，或 `CompilerOptions` 类

## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-04-10
- **类型**：版本差异
- **位置**：版本演进表格（Line 473-484）
- **问题**：Android 11 和 Android 15 在版本演进表格中缺失，而 Android 11 是 VDEX 广泛使用的关键版本
- **建议**：补充 Android 11（VDEX 文件验证效率提升）和 Android 15（Mainline dexopt 模块化推送成熟化）条目；若确认无重大变化则标注"无重大包管理变更"


## [Task2A Gap Mining] 知识缺口挖掘记录 — 2026-04-10 07:06

- **Phase**: Phase 0 无空 draft（28 个 draft 均 >50 行）→ Phase 1（Gap Mining 复检）
- **Gap Mining 结果**: 无新缺口（复检确认 05:06/06:05 结论仍然成立）
- **Queue 状态**: 6 个非 FRESHNESS pending 条目（1.14/2.18/13.8/4.8/14.9）均已存在文件且有实质内容（68-444 行），queue 条目为历史遗留
- **本轮处理**: 1.4 Binder IPC 草稿元数据补充 + 状态升级（draft → ready-for-review）
- **Git commit**: fb1e3eb
- **全书进度**: draft 27→26（1.4 已升级），ready-for-review 29→30
- **剩余工作**: 
  1. 其余 26 个 draft 章节（ch18 渲染链路 15 个 + ch02/03/06/13/17 各 1-3 个）
  2. queue.json 47 条 pending FRESHNESS 任务（Task 2B 范畴）
  3. 下轮可继续推进 draft→ready-for-review 转换


## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：原理断裂 + 版本差异
- **位置**：SystemServer 启动阶段正文/表格
- **问题**：WMS 和 InputManagerService 被列在"第三阶段（Other Services）"，但两者均在 SystemServer.startCoreServices() 阶段启动；servicemanager "最先启动" 描述不准确（ueventd/healthd/watchdog 更早）
- **建议**：将 WMS/IMS 移至 Core Services 阶段；补充 servicemanager "Binder 通信体系中" 最先启动的条件说明

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：版本差异 + 数据缺失
- **位置**：frontmatter applicable_versions + Android 16 启动优化段落
- **问题**：标注 Android 8 (API 26) - Android 16 (API 36)，但 AutoFDO 仅适用于 Android 16 (Kernel 6.12)，内容实质不适配；"Pixel 10 模块加载减少 30%" 无来源
- **建议**：修正 applicable_versions 或在 AutoFDO 段落加 [适用于: Android 15/16/17 beta] 标签；补充 AutoFDO 量化数据来源

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：知识盲区
- **位置**：Zygote → SystemServer 时序描述
- **问题**：未说明 Zygote fork SystemServer 几乎无耗时（fork 本身是内存页表复制，不复制数据）；Zygote fork 后 SystemServer 与 Zygote 预加载实际是并发的
- **建议**：补充 Zygote fork 机制说明（fork→copy-on-write 父子进程关系），说明为何 fork SystemServer 本身不耗时

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：数据缺失
- **位置**：boot_progress 里程碑事件段落
- **问题**：boot_progress_preload_start/end 等事件标注 [已验证: source.android.com]，但该文档是总览页，事件列表源码定义在 frameworks/base/core/java/com/android/server/am/ActivityManagerService.java 或 system/core/bootstat/
- **建议**：标注更精确的 AOSP 源码位置（如 AMS 中对应 boot_progress_* 输出的代码路径）

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：数据缺失
- **位置**：Zygote 预加载类数量描述
- **问题**：Zygote 预加载 "3000-4000 个常用类" 仅适用于 Android 10+（APEX 模块化后）；Android 8/9 版本 preloaded-classes 数量更多（约 5000+），未区分版本可能误导读者
- **建议**：在描述中加版本标签：[适用于: Android 10+]，旧版本数据另注说明

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：知识盲区
- **位置**：开机完成度量章节
- **问题**：提到了 locked_boot_completed 但未解释 Direct Boot 机制（Android 7.0 引入），读者无法理解其与一般"开机完成"的状态区别
- **建议**：在 boot_completed 广播段落增加 Direct Boot 机制说明（Credential-encrypted / Device-encrypted 存储区域）

## [Task9 Deep Review] 1.2 系统启动全流程 — 2026-04-10
- **类型**：原理断裂
- **位置**：Android 16 启动优化段落（AutoFDO 部分）
- **问题**：AutoFDO 描述缺少具体编译配置、内核优化指标和 Kernel 6.12 代码路径，读者无法在 AOSP 中验证
- **建议**：补充 AutoFDO 在 android-16.0.0_r1 内核中的关键源码路径（如 kernel config CONFIG_AUTOFDO）、Perfetto 中的验证方法

## [Task9 Deep Review] 3.1 Input 事件分发全流程 — 2026-04-10

### 建议 1
- **类型**：源码准确性
- **位置**：§5 秒超时的来源（line 370-372）
- **问题**：源码注释标注 `frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java`，但 DEFAULT_INPUT_DISPATCHING_TIMEOUT_NANOS 常量实际定义在 InputManagerService.java（或其常量定义类），WMS 只是引用方，注释指向不精准。
- **建议**：修正源码注释为 InputManagerService.java 中的常量定义位置。

### 建议 2
- **类型**：数据缺失
- **位置**：Perfetto 表现 - §wq Track 说明后（line 407）
- **问题**：章节已有 [待补充] 标注——Perfetto 中 iq/oq/wq Track 与 deliverInputEvent 的对应关系截图缺失。这是锚点要求"输入事件在 Perfetto/Systrace 中的完整追踪"的核心配套素材，缺失会显著降低本章作为实践指南的价值。
- **建议**：抓取包含 inputflinger（system_server）和 App 侧双进程的 Perfetto trace，截取 iq/oq/wq 队列堆积导致 ANR 的典型案例，逐 Track 标注含义和处理延迟的读法。



## [Task9 Deep Review] 3.2 触摸响应的性能分析 — 2026-04-10
- **类型**：版本差异
- **位置**：L379 正文 + L383 待验证标注
- **问题**：正文说"从 Android 4.4（API 19）开始支持"（指平台 API android.view.MotionEventPredictor，正确），但 L383 待验证标注将 Jetpack 库 minSdk=21 与平台 API 范围混为一错，造成矛盾。MotionEventPredictor 平台 API 确实 API 19 引入，章节正文正确。
- **建议**：修正待验证标注，区分平台 API（API 19+）和 Jetpack 库（minSdk 21）的版本信息；同步修正 frontmatter applicable_versions 将 Motion Prediction 相关内容延伸至 API 19。

## [Task9 Deep Review] 3.2 触摸响应的性能分析 — 2026-04-10（续）
- **类型**：知识盲区
- **位置**：L339-346（Input Boost 章节）
- **问题**：Input Boost 仅描述为"系统标准机制"，但实际各厂商（高通/MTK/华为/三星）定制 ROM 的 Input Boost 策略（提频幅度/持续时间/核心绑定）差异显著，读者在多设备适配时缺乏判断依据。
- **建议**：在 Input Boost 段落补充 Perfetto CPU Frequency Track 观察方法，说明如何识别各厂商差异；在"常见触摸卡顿原因"第 4 点增加厂商定制差异导致的性能问题的排查思路。

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-04-10
- **类型**：原理描述精确性
- **位置**：L167（DisplayList同步机制）
- **问题**："通过引用计数和资源所有权转移来实现的"——AOSP中RenderNode通过引用传递（主线程持有RenderNode，RenderThread持有对同一对象的引用），并非"所有权转移"语义
- **建议**：改为"主线程将 RenderNode 引用传递给 RenderThread，RenderThread 持有只读访问权"，或标注[待验证：AOSP实际同步机制]

## [Task9 Deep Review] 2.5 MainThread 与 RenderThread 协作 — 2026-04-10
- **类型**：数据/案例支撑
- **位置**：L226-246（正常帧时序示意）
- **问题**："measure/layout (2-5ms)"、"draw (构建 DisplayList) (5-8ms)" 等具体数值是示意性数据，但未标注
- **建议**：在时序图下方加注"[示意数据，典型 60Hz 设备参考值，非实测]"

## [Task6 Review] 2.11 Flutter 渲染管线与性能 — 2026-04-10
- **类型**：需补充素材
- **位置**：DevTools版本段落
- **问题**：DevTools版本信息不准确，当前引用devtools.dart.dev发布记录，需要确认具体版本号
- **建议**：查阅Flutter官方发布记录确认DevTools 2.28与Flutter版本对应关系，补充准确版本号
- **review 日志**：logs/review/2026-04-10-16-review.md

## [Task6 Review] 2.11 Flutter 渲染管线与性能 — 2026-04-10
- **类型**：存疑
- **位置**：Impeller性能数据段落
- **问题**：30-50%性能改善数据来源为社区综合估算（多个第三方报告，2024-2025），非Flutter官方基准测试
- **建议**：读者应将此数据视为近似参考值，标注数据来源局限性
- **review 日志**：logs/review/2026-04-10-16-review.md

## [Task6 Review] 2.11 Flutter 渲染管线与性能 — 2026-04-10
- **类型**：需补充素材
- **位置**：PlatformView Hybrid Composition段落
- **问题**：缺少Android 14+上Hybrid Composition的优化信息
- **建议**：补充Android 14+对Hybrid Composition的进一步优化内容
- **review 日志**：logs/review/2026-04-10-16-review.md

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-10
- **类型**：数据缺失
- **位置**：L228
- **问题**："Google 官方数据表明，正确配置 Baseline Profiles 可以提升约 30% 的代码执行速度" — 标注了 [待验证]，但缺少 Google 官方基准测试报告出处
- **建议**：补充 Google 官方文档（如 Baseline Profiles overview 页面）或 Android Developers Blog 原文链接和具体数字

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-10
- **类型**：数据缺失
- **位置**：L254
- **问题**："使用 Startup Profiles + DEX Layout 后，冷启动速度比单独使用 Baseline Profiles 快 15-30%" — 缺少可验证来源
- **建议**：补充 AGP 官方文档或 Google 性能博客中的具体数据

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-10
- **类型**：数据缺失
- **位置**：L113
- **问题**："JIT 代码缓存的内存占用通常稳定在 4MB 左右" — 标注了 [待验证]，建议补充不同设备/应用规模的验证数据
- **建议**：补充在真实设备（低端/中端/高端）上的实测数据，或引用 Google 官方性能报告

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-10
- **类型**：版本差异
- **位置**：L181（编译级别表）
- **问题**：`quicken` 的定义"验证 + 部分 DEX 指令优化" 不够精确。quicken 实际执行的是 DEX 指令 quickening（运行时重写），不是提前优化
- **建议**：修正为"verify + DEX quickening（字节码即时重写，如 invoke-polymorphic 优化）"

## [Task9 Deep Review] 1.7 ART 编译管线与 dex2oat 优化 — 2026-04-10
- **类型**：交叉引用
- **位置**：L402（与其他机制的关系）
- **问题**：§1.6 引用名写作"版本演进"，实际章节名为"Android 版本演进中的架构变化"，描述不完全一致
- **建议**：统一引用名称，写全"§1.6 Android 版本演进中的架构变化"
