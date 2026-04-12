

## [Task9 Deep Review] 1.10 ContentProvider 性能与优化 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 234 App Startup 量化收益
- **问题**："冷启动时间可减少 35% 到 42%"已标注 [待验证]，但仍以量化结论形式呈现，读者可能忽略待验证标注
- **建议**：降级为"实测项目可减少 30%-40%，具体收益视 SDK 数量和初始化复杂度而定"，或将 [待验证] 标注升级为更醒目的 [数据来源: 待补充]

- **类型**：源码准确性
- **位置**：行 160 Binder 缓冲区 1MB
- **问题**："[已验证：AOSP Binder 驱动默认配置]"未给出精确源码路径。Binder buffer size 在不同 Android 版本中配置来源不同（kernel binder driver vs system property）
- **建议**：补充精确路径，如 `kernel/msm-5.4/drivers/android/binder.c` 中的 `binder_proc_dir_entry_default` 或 `system/core/binder/` 相关配置

- **类型**：知识盲区
- **位置**：行 144-154 SQLiteCursor 分页机制
- **问题**：描述为"LIMIT windowSize OFFSET currentPos"，但 AOSP 实际实现是通过 native `movePosition()` 重新执行查询并逐行跳过，不是直接用 SQL OFFSET 语义
- **建议**：修正分页实现描述，补充 native 层 `fillWindow()` 的实际行为，或标注为"[待验证：SQLiteCursor.fillWindow() 的具体实现机制]"

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

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-10
- **类型**：源码准确性（[待验证]遗留）
- **位置**：HWUI 架构 → RenderNode 内部结构
- **问题**：正文标注 `[待验证: RenderNode 内部结构在 AOSP android-16.0.0_r1 中可能有调整，以下为概念性描述]`。RenderNode staging 机制设计思路正确，但 Android 16 HWUI 重构后的具体字段名和方法名未确认。
- **建议**：AOSP frameworks/base/libs/hwui/RenderNode.h 调研，确认 Android 16 staging 机制的字段名。

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-10
- **类型**：数据缺失
- **位置**：HWUI 概述章节（L"硬件加速渲染相比纯 CPU 软件渲染提升 5-10 倍"）
- **问题**：5-10x 性能提升断言未注明来源和测试条件（工作负载类型？设备规格？Android 版本？），读者无法验证或复现。
- **建议**：补充具体测试来源（Google 官方 benchmark 或学术论文），或降级为"业界普遍认为"并注明近似值。

## [Task9 Deep Review] 2.1 Android 渲染架构全景 — 2026-04-10
- **类型**：版本差异
- **位置**：BufferQueue 生产者-消费者章节
- **问题**：章节标注了 `[待验证: 以下 dequeueBuffer/queueBuffer 实现在 Android 16 BlastBufferQueue 重构后可能有变化]`，但未补充 BlastBufferQueue（Android 12）的存在及其与旧版 BufferQueue 的关键差异。BlastBufferQueue 改变了 App↔SurfaceFlinger 的通信方式，对多窗口和游戏渲染性能分析很重要。
- **建议**：补充 BlastBufferQueue 基本原理及其与旧版 BufferQueue 的区别说明。


## [Task6 Review] 1.8 Activity Manager Service 与性能分析 — 2026-04-10
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与锚点设计，Task 6 无法按规范做锚点覆盖检查。
- **建议**：按 writing-guide.md 补齐 outline 块，并让每个锚点至少对应 1 个完整段落。
- **review 日志**：logs/review/2026-04-10-2359-review.md

- **类型**：需确认
- **位置**：AMS 的 Activity 管理 → Activity 栈与 Task 管理
- **问题**：`TaskStack` / `Task` 的叙述存在版本与术语风险，可能与现代 Android 任务模型不一致。
- **建议**：交给 Task 9 核对当前 AOSP 中 `Task`、`RootWindowContainer`、`TaskDisplayArea` 相关实现后再修订。
- **review 日志**：logs/review/2026-04-10-2359-review.md

- **类型**：需补充素材
- **位置**：Android 17 的 `recreateOnConfigChanges`、Android 14+ 的广播限制
- **问题**：两节目前只有占位式 `[待验证]`，不足以支撑成章。
- **建议**：补充官方文档或源码依据，至少说明行为变化、影响范围和适用版本。
- **review 日志**：logs/review/2026-04-10-2359-review.md


## [Task9 Deep Review] 1.8 Activity Manager Service 与性能分析 — 2026-04-11
- **类型**：版本差异
- **位置**：AMS 的 Service 管理 → 前台服务的演进 / 版本演进表
- **问题**：Android 15 的 FGS 限制被写成“dataSync 最长 6 小时”，遗漏了 per-type 的 rolling 24h 预算、`mediaProcessing` 共享同类预算，以及超时后 `Service.onTimeout()` / `stopSelf()` 这条关键收口路径。
- **建议**：把表述改成“`dataSync` / `mediaProcessing` 类型前台服务在后台场景下各自受 24 小时滚动窗口内 6 小时预算限制；超时会回调 `Service.onTimeout()`，服务需尽快 `stopSelf()`”。

## [Task9 Deep Review] 1.8 Activity Manager Service 与性能分析 — 2026-04-11
- **类型**：版本差异
- **位置**：AMS 的 Service 管理 → 前台服务的演进 / 版本演进表
- **问题**：Android 16 被概括为“后台 Job（包括通过 FGS 启动的）遵守各自运行配额”，但没有说明 user-initiated data transfer jobs（UIDT）是重要例外，容易把约束讲成绝对规则。
- **建议**：补一句“Android 16 开始，从 FGS 发起的普通 Job 也受 runtime quota 约束，但 UIDT jobs 是官方给出的长时用户触发传输例外路径”。

## [Task6 Review] 1.9 Package Manager Service 与应用安装性能 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与锚点设计，Task 6 无法按规范检查锚点覆盖。
- **建议**：按 writing-guide.md 补齐 outline 块，并让每个锚点至少对应 1 个完整段落。
- **review 日志**：logs/review/2026-04-11-01-review.md

## [Task6 Review] 1.9 Package Manager Service 与应用安装性能 — 2026-04-11
- **类型**：需补充素材
- **位置**：`Baseline Profiles 与安装时优化` → 量化数据段落
- **问题**：`约 30%` 与 `15-30%` 两组量化数据缺少可追溯的官方来源。
- **建议**：补充 Google 官方文档或博客原始链接；若暂时无法确认，则降级为非量化表述或改为 `[待验证]`。
- **review 日志**：logs/review/2026-04-11-01-review.md

## [Task6 Review] 1.10 ContentProvider 性能与优化 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与锚点设计，Task 6 无法按规范检查锚点覆盖。
- **建议**：按 writing-guide.md 补齐 outline 块，并让每个锚点至少对应 1 个完整段落。
- **review 日志**：logs/review/2026-04-11-02-review.md


## [Task6 Review] 1.12 AutoFDO 反馈导向编译优化 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与锚点设计，Task 6 无法按规范检查锚点覆盖。
- **建议**：按 writing-guide.md 补齐 outline 块，并让每个锚点至少对应 1 个完整段落。
- **review 日志**：logs/review/2026-04-11-03-review.md

## [Task9 Deep Review] 1.12 AutoFDO 反馈导向编译优化 — 2026-04-11
- **类型**：版本差异
- **位置**：frontmatter `applicable_versions` + 版本演进表（行 10, 276-285）
- **问题**：文章用单一范围 `Android 12-17` 覆盖两条不同落地线：Android 12+ 的 userspace/native AutoFDO 和 Android 15/16 起的 kernel GKI AutoFDO。读者容易误读成“Android 12-14 已经有 kernel AutoFDO”。
- **建议**：把支持矩阵拆成 `userspace/native` 与 `kernel/GKI` 两列，单独列出 android15-6.6 / android16-6.12 / android17-6.18（计划）的分支映射。

## [Task9 Deep Review] 1.12 AutoFDO 反馈导向编译优化 — 2026-04-11
- **类型**：交叉引用
- **位置**：与 §8.7 的交叉引用（行 184-201；目标章节 8.7 行 254-268）
- **问题**：本章把 Android/ARM 场景下的 AutoFDO 采集基础写成 ETM/Coresight，而 §8.7 当前写成“基于 CPU 的 LBR 收集热路径信息”。两章对同一机制的硬件基础描述不一致。
- **建议**：统一改成“x86 常见 LBR，Android ARM64 内核场景以 ETM/ETE 为主”，避免读者把 x86 术语直接套到 Android GKI。

## [Task9 Deep Review] 1.12 AutoFDO 反馈导向编译优化 — 2026-04-11
- **类型**：数据缺失
- **位置**：`实测性能数据` + `在 Perfetto 中的观测`（行 160-176, 251-272）
- **问题**：给出了 10.5% 几何平均、26.4% 峰值和 Binder 受益明显等结论，但没有标注这些数字对应的 benchmark/case，也没有给出一个最小 Perfetto/simpleperf 对照样例。
- **建议**：至少补 1 个官方 benchmark 名称或截图占位，并把“Binder 受益明显”绑定到具体计数器/benchmark（如 IPC、cache miss、binder microbenchmark）。


## [Task6 Review] 1.14 锁竞争与同步性能分析 — 2026-04-11
- **类型**：需重写
- **位置**：文末结构
- **问题**：outline 中的「常见问题与误区 / 与其他机制的关系 / 读者诊断清单」未在正文展开，正文停在版本演进表后，收尾不完整。
- **建议**：按 writing-guide.md 补齐这 3 个小节，每节至少 1 段，并补一个简短收尾。
- **review 日志**：logs/review/2026-04-11-04-review.md

- **类型**：需确认
- **位置**：`PI-futex` 版本演进与优先级继承相关表述
- **问题**：正文与版本演进表多次写到“Android 12 统一启用 Binder 和 ART monitor 的 PI-futex”，但缺少精确源码或版本依据，Task 6 不做技术裁决。
- **建议**：交给 Task 9 核实版本范围与 AOSP 依据，再决定是否保留统一表述。
- **review 日志**：logs/review/2026-04-11-04-review.md

- **类型**：需补充素材
- **位置**：量化数据与 frontmatter metadata
- **问题**：`PI-futex` wake 路径“多约 15% 开销”和 DeliQueue “主线程锁竞争时间减少 15%”缺少明确来源，frontmatter 也未列主要 `sources`。
- **建议**：补充原始素材/链接与 `sources` 字段，再决定保留或降级为定性表述。
- **review 日志**：logs/review/2026-04-11-04-review.md

## [Task9 Deep Review] 1.14 锁竞争与同步性能分析 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 42, 57, 158-166, 186, 258
- **问题**：`<10ns`、`1-10μs`、`PI-futex 多约 15% 开销`、`DeliQueue 主线程锁竞争减少 15%` 等数字没有绑定到具体设备、内核版本、benchmark 或 trace。对“锁开销”这类强依赖硬件/调度器/竞争模式的主题，这种裸数字会误导读者把样本值当通用结论。
- **建议**：每个数字至少补 1 个来源锚点（官方博客 / AOSP 注释 / benchmark 名称 / Trace 截图占位）；补不上的全部降级为定性表述。

## [Task9 Deep Review] 1.14 锁竞争与同步性能分析 — 2026-04-11
- **类型**：交叉引用
- **位置**：行 61, 192, 255 与 §1.4（行 42, 151）
- **问题**：本章把 Binder 线程池写成“默认最大 16 个线程”，版本表又写成“Android 8.0 从 8 扩展到 16”；而 §1.4 写的是“默认最大 15 个 binder worker threads（不含主线程）”。两章实际在“总线程数”与“worker 线程数”之间切换，但正文没有说明，读者会以为全书自相矛盾。
- **建议**：统一改成“默认上限 15 个 binder worker threads；常见总线程数上限为 16（含启动/join 线程）”，并删除“Android 8.0 从 8→16”的表述。



## [Task6 Review] 1.11 Zygote 机制与启动性能优化 — 2026-04-11
- **类型**：需确认
- **位置**：开头第 1 段（system_server → Zygote 请求链路）
- **问题**：system_server 向 Zygote 发起创建进程请求的通信机制写成了 Binder，存在技术事实风险。
- **建议**：由 Task 9 核对 AOSP 调用链，再由 Task 2B 回写为准确表述。
- **review 日志**：logs/review/2026-04-11-05-review.md

- **类型**：存疑
- **位置**：“preloadOpenGL” 段
- **问题**：把 `preloadOpenGL()` 直接等同于“每个 App 的 GPU 上下文初始化已完成”，表述边界过宽。
- **建议**：区分驱动/EGL 预热与 App 侧 GPU context 创建，必要时降级为更保守的描述。
- **review 日志**：logs/review/2026-04-11-05-review.md

- **类型**：需补充素材
- **位置**：Android 17 版本演进表（DeliQueue 量化收益）
- **问题**：“P95 冷启动首帧时间改善约 9%”缺少可追溯来源。
- **建议**：补充 Google 官方博客、实验记录或原始研究素材；若找不到，则改成定性描述。
- **review 日志**：logs/review/2026-04-11-05-review.md

- **类型**：需确认
- **位置**：Perfetto SQL 段的验证标注（2 处）
- **问题**：`[已验证: L2]` 不是可追溯验证来源，当前验证标注不完整。
- **建议**：补充具体 Trace、SQL 运行结果截图或官方文档出处，再保留 [已验证]。
- **review 日志**：logs/review/2026-04-11-05-review.md

## [Task9 Deep Review] 1.11 Zygote 机制与启动性能优化 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 101, 182, 239, 271, 297, 356, 429, 449, 459, 483, 491 多处量化断言
- **问题**：5-15ms、1-3s、50-100MB、20-40%、80%+ 等数字都没有绑定设备、版本、Trace 或 benchmark。
- **建议**：至少补一组可复现样本（设备型号、Android 版本、Trace/命令、原始耗时），否则统一降级为定性描述。

- **类型**：交叉引用
- **位置**：行 101, 186, 192, 289, 483 与 §1.3 行 72-79、§8.2 行 142
- **问题**：本章写 Binder IPC，相关章节写 Local Socket/zygote socket，同一启动链路口径冲突。
- **建议**：统一全书描述为“Launcher/App ↔ system_server 走 Binder，system_server ↔ Zygote 走 LocalSocket/zygote socket”，并在 1.11 反链到 1.3/8.2。

## [Task6 Review] 1.15 JNI/NDK 性能优化 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与锚点映射，Task 6 无法按结构锚点检查覆盖率。
- **建议**：先按 writing-guide.md 补齐结构骨架，再进入深修。
- **review 日志**：logs/review/2026-04-11-0608-review.md

- **类型**：需确认
- **位置**：L48、L108-L126
- **问题**：JNI transition、`@FastNative`、`@CriticalNative` 的量化数据缺少精确 benchmark 来源、设备条件和测试方法。
- **建议**：补充原始 benchmark 链接与测试条件，或把数字降级为更保守的范围表述。
- **review 日志**：logs/review/2026-04-11-0608-review.md

- **类型**：需确认
- **位置**：L165-L169、L241
- **问题**：`@FastNative` / `@CriticalNative` 的 GC suspend 风险、阈值，以及 `GetPrimitiveArrayCritical()` 对 GC 的影响范围，验证链不完整。
- **建议**：补充 AOSP / 官方文档或实验依据，避免对阈值和影响范围做过强断言。
- **review 日志**：logs/review/2026-04-11-0608-review.md

- **类型**：需补充素材
- **位置**：L52-L60
- **问题**：Perfetto 中的 JNI 表现只有概述，没有真实 Trace 截图或更具体的 slice 示例。
- **建议**：补一张 Trace 截图，或给出明确的 trace category / slice 名称来源。
- **review 日志**：logs/review/2026-04-11-0608-review.md


## [Task9 Deep Review] 1.15 JNI/NDK 性能优化 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 388-390
- **问题**：`libbinder_ndk` 比 Java Binder 快 20-40% 的结论没有绑定 workload、payload 大小、序列化路径和测试设备，当前只是社区估算，不能直接作为书中定量结论。
- **建议**：补一个可复现实验场景（例如同 payload 的 Java AIDL vs NDK AIDL 往返延迟/吞吐），或者降级为“可减少 Java ↔ native 桥接与部分序列化栈开销”的定性表述。

- **类型**：交叉引用
- **位置**：行 258-317，行 429-441
- **问题**：16KB page size 与 Simpleperf 在全书已有专章（§4.7、§14.2），本章却独立展开且没有回链，工具路径和官方来源也已开始出现漂移风险。
- **建议**：本章保留“与 JNI 直接相关的判断准则”，把 16KB page size、Simpleperf 的通用方法显式交叉引用到 §4.7 / §14.2，避免多处并行维护同一事实表。


## [Task9 Deep Review] 1.16 Audio Pipeline 延迟与性能 — 2026-04-11
- **类型**：源码准确性
- **位置**：行 193 AAudio 段落验证链接
- **问题**：`https://developer.android.com/ndk/guides/audio/aaudio` 当前返回 404，但正文标成了 `[已验证]`
- **建议**：改成有效地址 `https://developer.android.com/ndk/guides/audio/aaudio/aaudio`，或退回到父级目录 `https://developer.android.com/ndk/guides/audio`

- **类型**：数据缺失
- **位置**：行 238-259 Perfetto / underrun SQL
- **问题**：当前 SQL 用 `%Audio%` / `%underrun%` 占位，正文没有给出一份真实 trace 中验证过的 track 名和 slice 名，读者落地时还要二次猜测
- **建议**：补一份实测设备（例如 Pixel）的真实线程名、slice 名、筛选 SQL 和截图说明，至少固定一个可复用样例

## [Task6 Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-04-11
- **类型**：需重写
- **位置**：§3-§5 多处
- **问题**：核心机制详解、性能对比表、选型决策树以表格和清单为主，缺少从原理到选型的连贯叙述，不符合 writing-guide.md 的“叙述为主，列表为辅”。
- **建议**：保留表格作摘要，但需补足叙述主线，把 Binder、Unix Domain Socket、Pipe、共享内存的取舍讲成连续说明。
- **review 日志**：logs/review/2026-04-11-09-review.md

- **类型**：需补充素材
- **位置**：§6 Perfetto 中的 IPC 分析
- **问题**：目前只有 SQL 片段，缺少 Binder、socket、共享内存在 Perfetto 中对应的 track、slice、正常/异常表现和截图占位。
- **建议**：补充可视化识别说明，并至少添加 2-3 个 [图：...] 截图标记。
- **review 日志**：logs/review/2026-04-11-09-review.md

- **类型**：需确认
- **位置**：§3.1 / §4.1 / §7 / frontmatter applicable_versions
- **问题**：多处延迟、占比、版本演进与 API 范围断言缺少逐项来源或验证标注，存在版本与数据漂移风险。
- **建议**：交由 Task 9 / Task 2B 核对原始来源；无法确认时降级为定性描述或补 [待验证]。
- **review 日志**：logs/review/2026-04-11-09-review.md

## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-04-11
- **类型**：数据缺失
- **位置**：§4.1-§4.2 定量对比与使用频率统计（行 296-318）
- **问题**：延迟表、吞吐量表和“Binder ~90% / Socket ~5% / 共享内存 ~3%”这些数字没有给出设备、Android 版本、负载模型、payload 大小或 Trace / benchmark 来源。当前写法是高精度数字，但没有实验边界。
- **建议**：要么补一个 benchmark 方法说明（设备 / payload / 单向或双向 / sync 或 async / 采样次数），要么把这些数字降级成定性排序。

## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-04-11
- **类型**：数据缺失
- **位置**：§6 Perfetto 中的 IPC 分析（行 357-388）
- **问题**：SQL 直接用 `slice.name GLOB "*binder*"`、`*sock*`、`*buffer*alloc*` 做匹配，但没有说明抓 trace 时启用了哪些 category，也没有说明 Binder 应该用 `android.binder` 模块还是哪张原始表。读者照抄后很可能查不到稳定结果。
- **建议**：补一份真实 trace 的配置 + 表映射，至少说明 Binder 走 `android.binder` / 对应数据源，socket / dmabuf 依赖哪些 tracepoint 或 slice 名，再给一条经过实测可跑通的 SQL。

## [Task9 Deep Review] 1.17 IPC 全景：Android 进程间通信机制对比与性能选型 — 2026-04-11
- **类型**：交叉引用错误
- **位置**：§3.2 / §3.3 / §3.7 与 §3.1 / §1.5 / §1.1
- **问题**：本章当前的 InputChannel、Looper wake fd、AIDL HAL 描述，分别和已审核章节《3.1 Input 事件分发全流程》《1.5 线程模型》《1.1 Android 分层架构》冲突。即使单章修正了，若不做一次全书一致性回扫，后面还是会出现“同一个机制在不同章节说法不同”的漂移。
- **建议**：Task 2B 回炉后，顺手做一次 IPC 相关章节的一致性回扫，至少对齐 InputChannel、Binder thread pool、AIDL / HIDL / hwbinder 三组表述。

## [Task6 Review] 2.3 VSync 机制 — 2026-04-11
- **类型**：需确认
- **位置**：9.6 Android 17：DeliQueue 无锁 MessageQueue
- **问题**：DeliQueue 段落把主线程 MessageQueue 变更直接归因到 VSync/Choreographer 的量化收益，并使用“Google 内部 Beta 测试数据”作为验证来源，但没有给出可公开复核的源码路径或数据出处；末尾验证路径还指向 `DispSync.cpp`，与正文讨论的机制不匹配。
- **建议**：交给 Task 9 / Task 2B 核实 MessageQueue/Looper 相关源码路径、量化数据来源，以及该段是否应改写为更谨慎的版本演进说明。
- **review 日志**：logs/review/2026-04-11-10-review.md


## [Task9 Deep Review] 2.3 VSync 机制 — 2026-04-11
- **类型**：数据缺失
- **位置**：§8.3 VSync 与 Input 事件（行 519）
- **问题**："120Hz 采样率的触摸屏，从中断处理到 App 收到 Input 事件大约需要半个 VSync 周期"没有设备、Trace、采样频率或测量方法支撑，当前只能算经验判断。
- **建议**：补一段 Perfetto/厂商 trace 的测量方法（InputReader/InputDispatcher/App 收到事件的时间点），或降级为定性表述。

- **类型**：交叉引用
- **位置**：§8.3 → §8.1 响应速度原理
- **问题**：本章与 §3.1 都把 Input 事件跨进程传输写成 `InputChannel/socketpair`，但 §8.1 第 132 行写成了 "InputDispatcher 通过 Binder IPC 将事件发送给目标 App 进程"，同一机制在相邻章节中出现冲突。
- **建议**：统一全书表述为 `InputChannel/socketpair`，如需提到 Binder，仅用于窗口创建时回传 `InputChannel` handle 的场景，不要写成运行时事件传输通道。


## [Task9 Deep Review] 16.1 Google 官方的性能优化思路 — 2026-04-11
- **类型**：数据缺失
- **位置**：frontmatter `last_verified_against` + 行 67-118 多个历史/框架小节
- **问题**：当前验证范围只覆盖 Android 17 release notes 与 DeliQueue blog，但正文横跨 Project Butter / Svelte / Treble / Mainline / Binder / BLAST 等多个时代，"[已验证]"覆盖面明显不足。
- **建议**：为 Project Butter / Svelte / Treble / Mainline / Binder 版本演进补充官方文档或源码依据；补不齐时把对应断言降级为“需进一步核对”，不要统一挂在 Android 17 验证范围下。

- **类型**：交叉引用
- **位置**：行 59、89、111、117
- **问题**：AutoFDO、DeliQueue、Kernel 6.12、Window 管线等内容已经在专章展开，但本章没有显式回链到 §1.12、§1.13、§16.4、§2.12，容易造成术语漂移与重复解释。
- **建议**：在对应段落追加明确交叉引用，把“总览章节”与“机制专章”绑紧，避免同一概念在不同章节出现不同口径。

- **类型**：交叉引用一致性
- **位置**：行 184-198 参考资料尾部
- **问题**：Gemma / Gemini Nano 条目与“Google 官方的性能优化思路”主题无直接关系，属于 AI 能力资讯，不应挂在本章参考资料中。
- **建议**：移出本章参考资料，改挂到 AI / Android AI 相关章节或独立资料池，避免引用域被污染。

## [Task6 Review] 2.13 图形缓冲区管理 (BufferQueue) — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与 `🔹` 锚点，Task 6 无法按统一大纲检查覆盖率。
- **建议**：按 writing-guide.md 补齐大纲块，并让每个锚点至少对应 1 个完整段落。
- **review 日志**：logs/review/2026-04-11-12-review.md

- **类型**：需补充素材
- **位置**："在 Perfetto 中的表现"
- **问题**：目前只有文字描述，没有正常/异常 BufferQueue 行为的 Trace 截图或标注图。
- **建议**：补 2 张 Perfetto 截图，至少覆盖 `dequeueBuffer` 阻塞和 `queueBuffer` → `acquireBuffer` 延迟两个场景。
- **review 日志**：logs/review/2026-04-11-12-review.md

- **类型**：需确认
- **位置**：BLASTBufferQueue 性能收益段落
- **问题**："延迟大幅降低"、"显著减少"属于量化结论，但正文没有给出同机型对比数据或 Trace 证据。
- **建议**：补充同机型 Android 10/12+ 对比 Trace，或改写为不带量化色彩的机制描述。
- **review 日志**：logs/review/2026-04-11-12-review.md

- **类型**：需确认
- **位置**：版本演进表（Android 13-17）
- **问题**：`frame rate override`、`maxBufferCount`、`无锁 MessageQueue + BlastBufferQueue 协同优化` 三处缺少可追溯来源。
- **建议**：补充 AOSP commit、官方文档或发布说明，再决定是否保留这些版本结论。
- **review 日志**：logs/review/2026-04-11-12-review.md

## [Task9 Deep Review] 2.13 图形缓冲区管理 (BufferQueue) — 2026-04-11
- **类型**：数据缺失
- **位置**：行 203-229 Perfetto 表现
- **问题**：`dequeueBuffer` “超过 3-4ms 就算异常”以及 `bufs_queued` 计数器的说法没有设备、刷新率、trace 配置前提。这个阈值在 60Hz / 120Hz、HWUI / SurfaceView、不同 GPU 驱动下差异很大。
- **建议**：补同机型 trace 样本或明确“示意阈值，仅适用于某设备/场景”；同时给出实际 track 名称或 SQL 观察方法。

- **类型**：交叉引用
- **位置**：frontmatter `related_chapters` + 正文行 238
- **问题**：frontmatter 只列了 `2.1/2.5/2.6/2.9/7.2`，正文却显式引用了 `§2.4 Choreographer`。同时 `04-choreographer.md` 目前在 progress 索引里表现为 `chapter: 2, section: 2.4`，自动校验容易把它误判成断链。
- **建议**：把 `2.4` 补进 `related_chapters`，并同步修正相关章节的 chapter/section 元数据，避免后续 Task 9 再次误报。

- **类型**：源码准确性
- **位置**：frontmatter `sources`
- **问题**：当前 sources 只有 `BufferQueue.cpp / BufferQueueCore.cpp / BLASTBufferQueue.cpp`，但正文两个关键结论实际依赖 `libs/gui/include/gui/BufferSlot.h` 与 `include/gui/IGraphicBufferProducer.h`。
- **建议**：把 `BufferSlot.h` 和 `IGraphicBufferProducer.h` 加进 sources，后续所有 slot 状态和 queue/request 语义都以这两个头文件为主锚点。
## 2026-04-11 - 无法匹配的素材

- **链接：<https://androidperformance.com/2026/04/10/SmartPerfetto-Architecture-Deep-Dive/>** (https://androidperformance.com/2026/04/10/SmartPerfetto-Architecture-Deep-Dive/>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://w2solo.com/topics/7184>** (https://w2solo.com/topics/7184>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<http://www.techmeme.com/260410/p8#a260410p8>** (http://www.techmeme.com/260410/p8#a260410p8>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://androidperformance.com/2026/04/10/SmartPerfetto-Architecture-Deep-Dive-QA/>** (https://androidperformance.com/2026/04/10/SmartPerfetto-Architecture-Deep-Dive-QA/>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://w2solo.com/topics/7186>** (https://w2solo.com/topics/7186>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<http://www.techmeme.com/260410/p12#a260410p12>** (http://www.techmeme.com/260410/p12#a260410p12>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://mp.weixin.qq.com/s?__biz=MzIzOTU0NTQ0MA==&mid=2247559481&idx=1&sn=ee2dd74d42080dcd8ae1024f3a46a480>** (https://mp.weixin.qq.com/s?__biz=MzIzOTU0NTQ0MA==&mid=2247559481&idx=1&sn=ee2dd74d42080dcd8ae1024f3a46a480>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://mp.weixin.qq.com/s?__biz=MzI2MzEwNTY3OQ==&mid=2648991546&idx=1&sn=eb4edcc29f05c9506117f5be663b38d0>** (https://mp.weixin.qq.com/s?__biz=MzI2MzEwNTY3OQ==&mid=2648991546&idx=1&sn=eb4edcc29f05c9506117f5be663b38d0>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://mp.weixin.qq.com/s?__biz=MjM5MzI5ODA4NQ==&mid=2453654000&idx=1&sn=3c69b5047d715f825d56f54514095036>** (https://mp.weixin.qq.com/s?__biz=MjM5MzI5ODA4NQ==&mid=2453654000&idx=1&sn=3c69b5047d715f825d56f54514095036>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://www.ccgxk.com/codeother/711.html>** (https://www.ccgxk.com/codeother/711.html>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://t.me/hyi0618/12042>** (https://t.me/hyi0618/12042>) - 原因: Chapter ch12-apk-network does not exist
- **链接：<https://t.me/reorx_share/6735>** (https://t.me/reorx_share/6735>) - 原因: Chapter ch12-apk-network does not exist
- **链接：https://github.com/google/perfetto/commit/d6d4e7f478503496c39188e37ea7ba6ddca46760** (https://github.com/google/perfetto/commit/d6d4e7f478503496c39188e37ea7ba6ddca46760) - 原因: Chapter ch12-apk-network does not exist
- **链接：https://github.com/google/perfetto/commit/341fda782494784844b77f1651d815ea08809075** (https://github.com/google/perfetto/commit/341fda782494784844b77f1651d815ea08809075) - 原因: Chapter ch12-apk-network does not exist
- **- **链接**：https://arxiv.org/abs/2502.04202** (https://arxiv.org/abs/2502.04202) - 原因: Chapter ch12-apk-network does not exist

## [Task9 Deep Review] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-04-11
- **类型**：数据缺失
- **位置**：行 130、218-228、343
- **问题**：`10-50μs vs 1-5μs`、`ANGLE 2-5% / 5-10% / 10-20%`、`Pipeline Cache 降低 95%` 都缺设备型号、GPU、驱动版本、工作负载和测试方法。当前写法像统一结论，读者无法判断哪些数字可迁移到自己的项目。
- **建议**：把量化结论改成“示例数据”，补设备/GPU/bench 场景；若拿不到同口径实验，改成趋势判断并保留来源限制。

## [Task9 Deep Review] 2.14 图形 API 演进与选择策略（OpenGL ES / Vulkan / ANGLE） — 2026-04-11
- **类型**：交叉引用
- **位置**：行 35、71-86，对照 §2.9 Android 16：Vulkan 统一渲染堆栈
- **问题**：§2.9 已把 Android 16 写成 Vulkan 成为官方图形 API 的平台转折点，但本章把 Vulkan 1.4 / AVP 2025 / 迁移背景整体后移到 Android 17，导致全书时间线不一致。
- **建议**：统一成“双阶段”叙述：Android 16 是平台基线抬升与 Vulkan 1.4 要求，Android 17 是 ANGLE denylist 扩大覆盖面；同步校正 §2.9 / §14.8 的相关描述。

## [Task6 Review] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-04-11
- **类型**：需确认
- **位置**：“从 AOSP 源码看分配链路”段末 [待验证]
- **问题**：“Gralloc Allocator AIDL 接口在 Android 16 中是否已完全替代 HIDL 接口” 仍缺明确版本线与接口证据。
- **建议**：由 Task9 核对 allocator/mapper HAL 的 AIDL/HIDL 演进，再由 Task2B 将结论收窄到已验证版本。
- **review 日志**：logs/review/2026-04-11-1406-review.md

## [Task6 Review] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-04-11
- **类型**：需确认
- **位置**：“Android 16/17：Gralloc AIDL 化”小节
- **问题**：“Android 16 开始将 Gralloc HAL 从 HIDL 迁移到 AIDL 接口”和“更少的 IPC 开销”属于版本差异与效果判断，当前来源不足。
- **建议**：由 Task9 复核 Android 16/17 官方文档与 AOSP 接口变更，必要时 Task2B 改成更保守的表述。
- **review 日志**：logs/review/2026-04-11-1406-review.md

## [Task9 Deep Review] 2.15 DMA-BUF、Gralloc 与跨进程图形内存共享 — 2026-04-11
- **类型**：交叉引用
- **位置**：行 190、220；参见 §2.13 行 134-154
- **问题**：本章把 slot 状态写成 `DEQUEUED / QUEUED / FREE / ACQUIRED` 的单态流转，而 §2.13 已明确当前 AOSP `BufferState` 是 counter-based，shared mode 下状态可叠加，应以 `isFree()` / `isDequeued()` / `isQueued()` / `isAcquired()` / `isShared()` 判断。前后文口径不一致。
- **建议**：在本章补一句“这里先按普通路径做简化，shared buffer mode 的计数语义详见 §2.13”，避免读者把单态流转当成当前源码事实。

## [Task6 Review] 2.16 Sync Fence 框架与帧同步机制 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与 `🔹` 锚点设计，Task 6 无法按统一大纲检查结构覆盖率。
- **建议**：按 writing-guide.md 补齐 outline 块，并让每个锚点至少对应 1 个完整段落。
- **review 日志**：logs/review/2026-04-11-15-review.md

- **类型**：需补充素材
- **位置**：`在 Perfetto 中的 Fence 表现`
- **问题**：虽然已有文字说明，但缺少正常 vs 异常的 Trace 截图占位与关键区域标注，和 writing-guide.md 的图文配合要求不够一致。
- **建议**：补 1-2 张 Perfetto 截图，至少覆盖 `latchBuffer` 等待和 BufferQueue 积压两个场景。
- **review 日志**：logs/review/2026-04-11-15-review.md

## [Task9 Deep Review] 2.16 Sync Fence 框架与帧同步机制 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 243-247 BufferQueue Track
- **问题**：正文把“60fps 正常 queued 数量在 0-1 之间波动，持续为 2 就说明 SurfaceFlinger 消费跟不上”写成通用判断，但没有给出设备、刷新率、BLAST / 非 BLAST 场景或真实 trace 证据，这个阈值结论容易被误用。
- **建议**：补 1 组真实 Perfetto 样例，明确设备、刷新率、窗口类型，并把结论改成“常见经验信号”而不是通用定律。

## [Task9 Deep Review] 2.16 Sync Fence 框架与帧同步机制 — 2026-04-11
- **类型**：源码准确性
- **位置**：行 284-290 Fence 泄漏段落
- **问题**：把“fd 没关”直接推导成“buffer 永远不回到 free pool”过于绝对。fd 泄漏、slot 长时间占用、release fence 不 signal 是三类不同问题，当前表述把资源泄漏和 BufferQueue 生命周期混成一件事。
- **建议**：拆开写：一类是进程 fd 泄漏；另一类是 release fence / consumer 生命周期导致的 slot 不可复用，并分别给出 `dumpsys SurfaceFlinger` / BufferQueue / `/proc/<pid>/fd` 的定位方法。

## [Task9 Deep Review] 2.4 Choreographer 与渲染流水线 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 360-401 Frame Timeline Track 详解
- **问题**：这一节已经把 Expected / Actual、颜色和 JankType 讲到了，但仍只有占位图 `[图：...]` 和通用描述，没有 1 个真实 trace 片段或对应 SQL 表的例子。读者很难把文中的概念映射到 Perfetto 实际界面。
- **建议**：补一个真实 Perfetto 截图，或至少补一段基于 `actual_frame_timeline_slice` / `expected_frame_timeline_slice` 的 SQL 示例，把 `on_time_finish` / `jank_type` / `present_type` 对到图上。

## [Task9 Deep Review] 2.4 Choreographer 与渲染流水线 — 2026-04-11
- **类型**：源码准确性
- **位置**：行 531-533 “Choreographer 只管 UI 线程吗？”
- **问题**：当前回答把 `Choreographer.getInstance()` 写成“返回主线程 Looper 对应实例”，容易让读者误以为 Choreographer 天生只属于主线程。实际上它是 **per-calling-thread Looper**：任意已经准备好 Looper 的线程都能拿到自己的 Choreographer；`getSfInstance()` 还是隐藏且已 deprecated 的特殊入口。
- **建议**：把表述改成“默认 UI 场景通常在主线程使用，但只要线程有 Looper，`getInstance()` 就返回该线程自己的 Choreographer”，并把 `getSfInstance()` 降级成系统/历史背景说明。


## [Task6 Review] 2.17 Frame Pacing Library 与帧节奏控制 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与 `🔹` 锚点设计，Task 6 无法按统一大纲检查结构覆盖率。
- **建议**：按 writing-guide.md 补齐 outline 块，并让每个锚点至少对应 1 个完整段落。
- **review 日志**：logs/review/2026-04-11-17-review.md

- **类型**：需确认
- **位置**：版本演进 + 多处量化断言
- **问题**：`Android 9/10/12/16/17` 的演进描述，以及“帧间隔标准差 1ms→3ms”“Auto 模式 11ms/12-16ms/22ms 阈值”等断言缺少可追溯来源。
- **建议**：交给 Task 9 / Task 2B 核对官方文档、AOSP 和原始 benchmark；无法确认时降级为定性表述或补 `[待验证]`。
- **review 日志**：logs/review/2026-04-11-17-review.md

- **类型**：需补充素材
- **位置**：Perfetto / FrameTimeline 分析
- **问题**：目前只有文字说明和占位图，缺少至少一组真实 Trace、track 名称或可复用 SQL/截图标注，实操闭环不够。
- **建议**：补一组真实 Perfetto 样例，至少覆盖 FrameTimeline、Buffer stuffing 或帧间隔不均匀的可视化识别。
- **review 日志**：logs/review/2026-04-11-17-review.md


## [Task6 Review] 2.18 Adaptive Refresh Rate 与动态帧率控制 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构（L34）
- **问题**：缺少 `outline-start` / `outline-end` 大纲块，Task 6 无法按锚点逐项检查覆盖率。
- **建议**：按现有章节结构补齐大纲与锚点，再回到 Task 6 做覆盖检查。
- **review 日志**：logs/review/2026-04-11-18-review.md

- **类型**：需补充素材
- **位置**：开头 / Perfetto 分析 / Game Mode 扩展（L46-L48 等）
- **问题**：ARR 开启前后 VSYNC 间隔、模式切换卡顿、Game Mode 交互仍是占位符，没有真实 Trace 截图或等价图示。
- **建议**：补 2-4 张真实 Perfetto Trace 截图，至少覆盖 ARR 前后对比、模式切换、Game Mode 交互。
- **review 日志**：logs/review/2026-04-11-18-review.md

- **类型**：需确认
- **位置**：ARR 对功耗的影响（L257-L261）
- **问题**：60Hz 升到 120Hz 时功耗增加 20%-50%、1Hz 与 120Hz 功耗差 5-10 倍，这两组量化数据缺少明确来源和测试条件。
- **建议**：补官方文档或实测条件，若补不齐则下调为定性表述。
- **review 日志**：logs/review/2026-04-11-18-review.md

- **类型**：需确认
- **位置**：frontmatter applicable_versions + 版本演进表（L281-L290）
- **问题**：Android 16 / 17 的 API Level 标注需要和全书版本约定统一，当前写法存在版本风险。
- **建议**：交给 Task 9 统一核对版本号与 API Level，再决定是否保留 API 36 / 37。
- **review 日志**：logs/review/2026-04-11-18-review.md


## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 · 2026-04-11
- **类型**：数据缺失
- **位置**：行 59 帧间隔标准差 1ms→3ms 的感知结论
- **问题**：正文把“帧间隔标准差从 1ms 增加到 3ms，用户就能明显感知到不够流畅”写成定量结论，但没有给出论文、实验设置或原始 benchmark。这个数值很容易被读者当成通用阈值复用。
- **建议**：补 primary source；如果拿不出来源，就降级成“帧间隔波动增大时，主观流畅度会明显下降”的定性表述。

## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 · 2026-04-11
- **类型**：数据缺失
- **位置**：行 214-241 Perfetto / FrameTimeline 分析
- **问题**：这一节把 Expected / Actual Timeline、Buffer stuffing、红黄 jank 都提到了，但仍只有占位图和文字，没有 1 个真实 trace 截图、track 名称或 actual_frame_timeline_slice / expected_frame_timeline_slice 的 SQL 例子。
- **建议**：补 1 组真实 Perfetto 样例，至少覆盖 FrameTimeline 两条 track、1 个 jank_type 字段和 1 个实际 present 时间对比。

## [Task9 Deep Review] 2.17 Frame Pacing Library 与帧节奏控制 · 2026-04-11
- **类型**：交叉引用
- **位置**：行 206-210 游戏引擎集成
- **问题**：Unity 2019.2、Unreal 5.2 默认启用 Swappy 这类引擎版本线属于高风险生态断言，当前正文没有给出精确的 Epic / Unity 一手文档链接，读者难以判断“支持”与“默认启用”的边界。
- **建议**：把每条引擎版本结论都补到具体 release note / 官方文档；如果只有社区帖子或二手摘要，就把语气降到“已支持/可启用”，不要写成默认行为。


## [Task9 Deep Review] 2.19 刷新率切换与帧率适配性能 — 2026-04-11
- **类型**：数据缺失
- **位置**：L164-L170
- **问题**：高通 / 联发科 / 三星三组 PLL 重锁定耗时数字直接写成 5-15ms 等定量结论，但正文没有实验来源、平台型号或 trace 证据，紧接着又标了 `[待验证]`。
- **建议**：如果没有实测数据，删掉具体毫秒范围；如果要保留，补设备型号、模式切换条件和测量方法。

## [Task9 Deep Review] 2.19 刷新率切换与帧率适配性能 — 2026-04-11
- **类型**：数据缺失
- **位置**：L199-L239
- **问题**：Perfetto 章节给了 SQL 和 FrameTimeline 判读规则，但没有附一份真实 trace、查询结果或截图；当前 `track_event` / `VSYNC-app` 查询也没有给出已验证的 schema 依据。
- **建议**：补一份实际 trace 的截图和 SQL 结果，明确查询使用的表、track 名与 Android 版本，避免读者直接照抄后跑不出来。

## [Task9 Deep Review] 2.19 刷新率切换与帧率适配性能 — 2026-04-11
- **类型**：源码准确性
- **位置**：L233-L245
- **问题**：`ChooseRefreshRate: layers={...} -> chosen: 120Hz` 这组 SurfaceFlinger 日志示例更像解释性伪日志，当前章节没有给出对应 log tag、源码字符串或真实 logcat 样本。
- **建议**：如果只是说明思路，明确标成“示意日志”；如果要作为排查手段，补真实 logcat 片段和触发命令。

## [Task9 Deep Review] 2.18 Adaptive Refresh Rate 与动态帧率控制 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 46-48, 241, 332
- **问题**：ARR 开启前后 VSYNC 间隔、模式切换卡顿、Game Mode 交互仍然只有占位符，没有真实 Perfetto Trace、FrameTimeline 视图或等价图示，导致技术判断无法落到可观测证据。
- **建议**：至少补 2-4 组真实证据：ARR 前后对比、非 LTPO 模式切换、滚动场景刷新率回落、Game Mode/Swappy 场景中的 refresh-rate 变化。

- **类型**：数据缺失
- **位置**：行 257-261
- **问题**：`60Hz → 120Hz 功耗增加 20%-50%`、`1Hz 与 120Hz 功耗差 5-10 倍` 仍是无测试条件的量化断言，没有设备、亮度、面板、场景、测量工具说明。
- **建议**：补官方功耗资料或实测条件；若短期无法补证据，把量化值降级为定性描述。


## [Task6 Review] 3.4 输入延迟与预测输入技术 — 2026-04-11
- **类型**：需确认
- **位置**：游戏模式（Game Mode）的输入优化
- **问题**：正文把 Game Mode 直接写成“GameManagerService 通知 InputDispatcher 优先处理输入事件”，调用链和机制边界还不够清楚。
- **建议**：由 Task 9 核对 GameManagerService、Game Mode 与 InputDispatcher 之间的实际关系；若没有直接证据，改成更保守的策略描述。
- **review 日志**：logs/review/2026-04-11-21-review.md

- **类型**：需确认
- **位置**：InputTransport 的异步模式
- **问题**：同步/异步 InputChannel 模式、ACK 行为和 ANR 计时之间的关系仍停留在待验证状态，当前表述容易被读者当成确定结论。
- **建议**：核对 InputTransport / InputChannel 的实现与官方文档，明确异步模式的启用条件、行为边界，以及对 ANR 统计是否有影响。
- **review 日志**：logs/review/2026-04-11-21-review.md

- **类型**：需确认
- **位置**：VSync offset 调优
- **问题**：“主动通知 SurfaceFlinger 立即处理，节约一帧等待时间”来自厂商实践，但还没有补出公开可复核的 AOSP 路径或版本边界。
- **建议**：由 Task 9 核对该机制是否属于厂商定制还是 AOSP 主线能力；若无法确认，保留为厂商实践案例并弱化到定性描述。
- **review 日志**：logs/review/2026-04-11-21-review.md

- **类型**：需补充素材
- **位置**：输入延迟在 Perfetto 中的分析方法
- **问题**：目前只有 SQL 和文字说明，缺少一组真实 Trace 截图或查询结果示例，输入延迟的可观测证据链还不完整。
- **建议**：补 1 组真实 Perfetto Trace 截图，至少标出 InputReader、InputDispatcher、DeliverInputEvent 与 FrameTimeline 的对应关系。
- **review 日志**：logs/review/2026-04-11-21-review.md

## [Task9 Deep Review] 3.4 输入延迟与预测输入技术 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 134-147 120Hz 理想路径延迟表
- **问题**：`10-38ms` 的阶段分解没有设备型号、触控采样率、是否触摸/手写笔、trace 配置和测量来源，当前更像估算值。
- **建议**：把这张表降级为“示意量级”，或补一组真实设备的 Perfetto/FrameTimeline 数据作为基线。

## [Task9 Deep Review] 3.4 输入延迟与预测输入技术 — 2026-04-11
- **类型**：源码准确性
- **位置**：行 441-442 官方参考链接
- **问题**：`developer.android.com/develop/ui/views/graphics/low-latency-graphics` 和 `perfetto.dev/docs/analysis/sql-tables/android-input` 当前链接均返回 404/已迁移，和正文的“已验证”标注不匹配。
- **建议**：改成当前可访问的类级 reference / 新文档入口，避免后续 review 无法复核。


## [Task6 Review] 2.20 多窗口与桌面模式渲染性能 — 2026-04-11
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 outline-start / outline-end 与锚点设计，Task 6 无法按规范检查锚点覆盖。
- **建议**：按 writing-guide.md 补齐 outline 块，并让每个锚点至少对应 1 个完整段落。

- **类型**：需确认
- **位置**：桌面模式 / 大屏适配 / 版本演进表
- **问题**：Desktop Windowing 手机端发布时间、Pixel 8 机型支持、`recreateOnConfigChanges`、600dp+ 设备上的 manifest 限制等断言需要统一核对版本、API Level 和行为边界。
- **建议**：由 Task 9 对照官方文档和 AOSP 统一版本范围、适用设备与行为描述，再由 Task 2B 回写。

- **类型**：需补充素材
- **位置**：Perfetto / dumpsys 观测段
- **问题**：分屏 2-4ms、自由窗口 6-10ms、HWC/GLES 回退、Layer 列表对比等结论缺少对应的 Perfetto 或 dumpsys 证据。
- **建议**：补 2-4 张真实 Perfetto / dumpsys 截图，或把量化表述降为定性描述。

- **类型**：需确认
- **位置**：Perfetto SQL 与后台窗口节流说明
- **问题**：`surfaceflinger_layers` 表、`doCompose` slice 名称，以及非焦点 App VSync 节流的写法需要核对当前版本的数据表、slice 名和系统行为。
- **建议**：交给 Task 9 核对实际表名 / slice 名与系统行为，再决定正文是否保留当前写法。
- **review 日志**：logs/review/2026-04-11-22-review.md


## [Task9 Deep Review] 2.20 多窗口与桌面模式渲染性能 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 52-54、104-116、130-131 多处量化断言
- **问题**：`2-4ms`、`6-10ms`、`200-500ms`、`1-2 帧`、`每 2-3 帧一次` 这类结论缺少设备、刷新率、trace 或 dumpsys 条件，读者无法判断它们是通用规律还是单机样本。
- **建议**：补真实 Perfetto / dumpsys 证据并标注设备、Android 版本、刷新率；补不齐就降级为定性描述。

- **类型**：交叉引用
- **位置**：行 283 参考资料 Desktop windowing 链接
- **问题**：`https://developer.android.com/guide/topics/large-screens/desktop-windowing` 当前返回 404，和“已验证”章节状态不一致。
- **建议**：改用当前官方文档 `https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing`，并补 `support-connected-displays` 作为手机外接显示器场景的直接参考。

- **类型**：交叉引用
- **位置**：frontmatter `sources[2]`
- **问题**：`Android 16 Desktop Windowing — android.com` 只是标题字符串，不是可追溯 URL，后续无法复核发布时间、设备范围和原文措辞。
- **建议**：替换成精确 URL（博客 / release note / 官方文档）并补发布日期；拿不到可追溯来源就删掉这条 source。


## [Task6 Review] 2.21 文字渲染性能 — 2026-04-11
- **类型**：需补充素材
- **位置**：`Android 文字渲染管线全景`、`Minikin 与文字测量性能`、`Emoji 渲染性能`、`PrecomputedText：将测量移到后台线程`、`在 Perfetto 中识别文字渲染瓶颈`
- **问题**：多处性能倍数、耗时和收益数字没有绑定 benchmark、设备、Trace 或官方来源，当前写法更像通用结论。
- **建议**：为量化断言补充具体来源；补不齐时改成定性描述，或降级为 `[待验证]`。
- **review 日志**：logs/review/2026-04-11-23-review.md

- **类型**：需确认
- **位置**：`Bitmap Emoji vs 系统 glyph`、`版本演进`、`PrecomputedText：将测量移到后台线程`
- **问题**：Android 7.0 / 11 / 14 等版本变化与 API 行为写成了硬断言，但当前章节没有给出足够的官方文档或 AOSP 锚点。
- **建议**：逐条核对版本线，保留能验证的版本变化，无法确认的部分改为更保守的表述。
- **review 日志**：logs/review/2026-04-11-23-review.md

- **类型**：需补充素材
- **位置**：`Android 文字渲染管线全景`、`在 Perfetto 中识别文字渲染瓶颈`
- **问题**：架构图和 Perfetto 证据链仍是占位状态，读者只能看到结论，看不到对应的图示和 Trace 读法。
- **建议**：补 1 张文字渲染链路图，至少补 2 组真实 Perfetto 片段（measure jank、glyph upload / TextBlob 观察点）。
- **review 日志**：logs/review/2026-04-11-23-review.md

## [Task9 Deep Review] 2.21 文字渲染性能 — 2026-04-11
- **类型**：数据缺失
- **位置**：行 89、112、173、194-205、235、259、285
- **问题**：复杂文本 5-10 倍、Span 2-3 倍、EmojiCompat 5-15MB/50-200ms、Bitmap Emoji 10 倍、PrecomputedText 1-5ms→0.01ms、BoringLayout 1/10、IncludeFontPadding 20-30% 等数字都没有绑定设备、trace、benchmark 或官方来源。
- **建议**：给每组数字补测试条件和出处；拿不到证据时统一降级为定性描述，或标成 [待验证]。
- **review 日志**：logs/deep-review/2026-04-11-23-deep-review.md

## [Task9 Deep Review] 2.21 文字渲染性能 — 2026-04-11
- **类型**：需补充素材
- **位置**：行 85、311、323
- **问题**：文字渲染架构图、measure jank 的 Perfetto 片段、TextBlob / glyph upload 观测说明仍是占位或空口说明，技术结论缺少可核对的图示证据。
- **建议**：至少补 1 张 TextView -> Layout -> HWUI/Skia 的结构图，补 2 组真实 trace 片段，并标注各自对应的线程/track/观测点。
- **review 日志**：logs/deep-review/2026-04-11-23-deep-review.md

## [Task9 Deep Review] 2.21 文字渲染性能 — 2026-04-11
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters`、参考资料
- **问题**：正文多次谈到 Perfetto 观测与 atrace，但 `related_chapters` 没有把 §13.9 tracing 基础设施纳入；参考资料里的 AOSP 链接又指向 `master`，和 frontmatter `last_verified_against: AOSP android-16.0.0_r1` 不一致。
- **建议**：把 tracing 基础设施章节加入相关章节；源码链接统一钉到 `android-16.0.0_r1` 或正文明确说明“master 仅作最新参考”。
- **review 日志**：logs/deep-review/2026-04-11-23-deep-review.md


## [Task6 Review] 3.5 输入事件拦截与安全机制 — 2026-04-12

- **类型**：需确认
- **位置**：AccessibilityService 与 Input 事件的关系（L153）
- **问题**：`FLAG_REQUEST_FILTER_KEY_EVENTS` 被写成声明在 `android:accessibilityEventTypes` 中，这里的字段位置与系统注册条件存在技术风险。
- **建议**：交给 Task 9 核对 `AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS` 的声明位置，以及 `AccessibilityManagerService` / `InputFilter` 的实际注册路径。
- **review 日志**：logs/review/2026-04-12-00-review.md

- **类型**：需确认
- **位置**：事件修改的安全限制（L188-L190）、Android 14+ 权限收紧（L420）、误区三（L473）
- **问题**：关于“可以修改按键事件的键码”、`MotionEvent.getSource()` / `MotionEvent.isFromSource()` / `InputEvent.getFlags()` 可直接识别 injected 或无障碍来源的说法过于绝对，API 可见性和行为边界需要核对。
- **建议**：交给 Task 9 核对 App 侧可观测的 flag/source 范围，再由 Task 2B 重写这组安全边界描述。
- **review 日志**：logs/review/2026-04-12-00-review.md

- **类型**：需确认
- **位置**：Instrumentation.sendPointerSync（L202-L214）与 uiautomator 对比（L234）
- **问题**：`sendPointerSync()` 的代码路径、是否“绕过 InputDispatcher”的结论，以及示例里的 `injectInputEventToInputFilter` 接口名都存在技术风险。
- **建议**：交给 Task 9 核对 `Instrumentation` / `UiAutomation` / `InputManagerService` 的真实注入路径，再由 Task 2B 改写该节。
- **review 日志**：logs/review/2026-04-12-00-review.md

- **类型**：需确认
- **位置**：安全策略的版本演进（L327-L333）
- **问题**：Android 9 / 10 / 13 / 14 这几行都给了很具体的权限或检测行为，但文内没有足够证据支撑，版本差异风险偏高。
- **建议**：交给 Task 9 逐条核对版本断言；补不齐来源时，改成更保守的定性表述。
- **review 日志**：logs/review/2026-04-12-00-review.md

- **类型**：需补充素材
- **位置**：在 Perfetto 中分析事件拦截问题（L427-L461）
- **问题**：分析步骤有用，但缺少真实 Trace 截图或等价图示，也没有给出更具体的 slice 名称或观察点，实操支撑偏弱。
- **建议**：交给 Task 2B 补 1-2 组真实 Trace 截图，至少覆盖 InputDispatcher Binder 阻塞和目标窗口 `deliverInputEvent` 对比。
- **review 日志**：logs/review/2026-04-12-00-review.md

## [Task9 Deep Review] 3.5 输入事件拦截与安全机制 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 365-370、399-405 延迟量化表
- **问题**：`InputFilter` / `AccessibilityService` / `Instrumentation` 的延迟数字都没有设备型号、trace 条件、采样率或 benchmark 来源支撑，当前量化表更像经验估计，不足以标成技术结论。
- **建议**：补至少 1 组真实设备 trace 或实验表，给出输入类型、服务是否启用、屏幕刷新率、统计口径，再决定是否保留这些数字。

- **类型**：数据缺失
- **位置**：行 448-476 Perfetto 分析流程
- **问题**：正文要求读者在 Perfetto 中搜索 `InputFilter` / Binder slice，并用 `dumpsys input` 验证，但没有给任何真实 trace 截图、slice 名称样例或 dumpsys 输出片段。加上前文对同步阻塞路径的判断本身就不准确，这一节可操作性偏弱。
- **建议**：补 1 组“无无障碍服务 / 开启按键过滤服务”的对比 trace，外加一段真实 `dumpsys input` 示例输出；如果拿不到证据，就把这节降级成“排查思路”，不要写成确定观测点。

- **类型**：源码准确性
- **位置**：行 482-484 误区一：App 可以注册自己的 InputFilter
- **问题**：正文把“普通 App 不能注册 InputFilter”的原因写成“需要 `INJECT_EVENTS` 权限”，但 AOSP 当前没有给 App 暴露 `setInputFilter()` 这样的公共 API；系统内部是 `WindowManagerService.setInputFilter()` / `InputManagerService.setInputFilter()` 路径。
- **建议**：改成“这是系统内部 API，普通 App 没有公开入口；不要把原因简化成单一权限判断”。

## [Task6 Review] 2.6 SurfaceFlinger 与合成 — 2026-04-12
- **类型**：需确认
- **位置**：`VSync 分发：管线的节拍器`
- **问题**：`DispSync（Android 12 之后为 VsyncModulator）` 把 Android 12+ 的 VSync 调度路径压成了单点替换，版本演进写得偏满，读者容易误以为 Android 12-16 只是换了一个模块名。
- **建议**：交给 Task 9 核对 Android 12-16 的 `Scheduler` / `EventThread` / `VSyncSchedule` 路径，再决定是否改成更保守的表述。
- **review 日志**：logs/review/2026-04-12-01-review.md

- **类型**：需确认
- **位置**：`BlastBufferQueue` 章节 + 版本演进 Android 12
- **问题**：`Buffer 状态管理移到了 App 进程内`、`acquire/release 不再需要跨进程` 这组表述过满，`BlastBufferQueue` 与传统 `BufferQueue` / `SurfaceControl Transaction` 的关系没有讲清，存在技术风险。
- **建议**：按 `frameworks/native/libs/gui/BlastBufferQueue.cpp` 重核一遍机制，再决定是保留“移到 App 进程内”，还是降级为“减少跨进程 Buffer 协调开销”。
- **review 日志**：logs/review/2026-04-12-01-review.md

- **类型**：需补充素材
- **位置**：`BufferQueue 的四步流转`、`HWC 合成 Track`
- **问题**：两个核心 Perfetto 分析段仍是 `[待补充：Trace 截图]` 占位，章节虽然讲了 Track 怎么看，但证据面还不够。
- **建议**：补 2 张真实或等价图示，至少覆盖 BufferQueue 四步流转，以及 Device/Client 合成切换的正常/异常对比。
- **review 日志**：logs/review/2026-04-12-01-review.md

- **类型**：需确认
- **位置**：版本演进 Android 13
- **问题**：`Vulkan 作为 RenderEngine 后端的支持逐步完善 [待验证...]` 仍未闭环，版本说明还不能作为稳定结论。
- **建议**：Task 9 核对引入版本和适用范围，再决定是保留版本断言还是改成更保守的表述。
- **review 日志**：logs/review/2026-04-12-01-review.md

## [Task6 Review] 3.6 手势识别算法与性能优化 — 2026-04-12
- **类型**：需确认
- **位置**：`VelocityTrackerFallbackStrategy` 段落 + 版本演进表
- **问题**：`Android 13 引入 FallbackStrategy`、`Android 14+ Impulse 优先` 这两组版本断言写得偏满，默认 strategy 与 fallback 路径需要 Task 9 再核一遍 AOSP。
- **建议**：按 `frameworks/base/core/jni/android_view_VelocityTracker.cpp`、`VelocityTracker.cpp` 和相关提交记录核对版本切换点，再决定是否保留当前表述。
- **review 日志**：logs/review/2026-04-12-02-review.md

- **类型**：需确认
- **位置**：`双击检测机制`
- **问题**：`单击事件至少有 300ms 延迟` 这段把延迟确认和具体回调语义压在一起写了，`onSingleTapUp()` / `onSingleTapConfirmed()` 的边界不够清楚。
- **建议**：交给 Task 9 核对 GestureDetector 回调链，再决定这里要保留哪一个 callback 作为解释中心。
- **review 日志**：logs/review/2026-04-12-02-review.md

- **类型**：需补充素材
- **位置**：`VelocityTracker 的 Perfetto 视角`、`NestedScroll 性能影响`
- **问题**：关键性能判断目前以定性描述为主，还缺真实 Trace 片段或等价图示，读者很难把结论映射回 Perfetto。
- **建议**：补 2-3 个 Trace 证据，至少覆盖 `dispatchTouchEvent`、嵌套滑动多层回调、Fling 判定前后的关键片段。
- **review 日志**：logs/review/2026-04-12-02-review.md

- **类型**：需补充素材
- **位置**：frontmatter `sources`、`厂商手势增强方案`、`Compose 手势系统的架构差异`
- **问题**：`frameworks/base/core/java/androidx/core/widget/NestedScrollView.java` 这条来源路径不够可靠，Compose 与厂商扩展段也缺精确来源，验证链不完整。
- **建议**：把 AOSP、AndroidX、Compose 官方文档分开列清楚，并为厂商扩展补具体资料或改成更保守的表述。
- **review 日志**：logs/review/2026-04-12-02-review.md

## [Task9 Deep Review] 3.6 手势识别算法与性能优化 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 198-200、353-355、518
- **问题**：`addMovement 1-5μs`、`computeCurrentVelocity 5-20μs`、`dispatchTouchEvent` / nested scroll 的 Perfetto 观察都属于定量或可观测结论，但正文没有给出设备、trace config、采样条件。默认 system trace 下也未必直接出现 `dispatchTouchEvent` 这种 Java 方法名 slice。
- **建议**：补设备型号、trace category、截图和 slice 名；如果补不齐，把这些量化数字和可观测结论降级成 `[待验证]` 或改成更保守的定性描述。

- **类型**：数据缺失
- **位置**：行 530-546 厂商手势增强方案
- **问题**：`边缘 2-3mm`、`TouchSlop 4-5dp`、`已验证: 部分厂商实现` 都没有具体厂商、机型、文档或实验来源。当前写法像经验猜测，不足以支撑“已验证”。
- **建议**：补 MTK / QCOM / 具体 ROM 文档或实测条件；补不齐就改成 `[待验证]`，并删掉具体数值。

- **类型**：源码准确性
- **位置**：行 548-567 Compose 手势系统
- **问题**：`手势判定逻辑运行在 Compose 的合成层中` 说法不准确，也没有给出 `AndroidComposeView`、`MotionEventAdapter`、`PointerInputEventProcessor` 等真实输入链路来源，容易把 pointer input 和 composition / recomposition 混成一件事。
- **建议**：补 Compose UI 输入管线与源码/官方 docs；如果暂时补不了，先收敛为“AndroidComposeView 接收 MotionEvent 并转换为 PointerInputEvent，再经 pointer input 节点分发”，不要写“合成层”。

- **类型**：交叉引用
- **位置**：frontmatter related_chapters
- **问题**：正文大量涉及 `onInterceptTouchEvent()`、`requestDisallowInterceptTouchEvent()` 和输入拦截边界，但 `related_chapters` 只列到 3.4 / 2.4，漏了 3.5《输入事件拦截与安全机制》。ch03 内部关联不完整。
- **建议**：补 `3.5` 到 `related_chapters`，保持输入分发、拦截、安全三章的互链一致。


## [Task6 Review] 4.8 ART 分代垃圾回收与 GC 暂停优化 — 2026-04-12
- **类型**：需确认
- **位置**：版本时间线 + Android 17 变化
- **问题**：Android 10 正式引入分代 GC、Android 17 将分代收集原生集成到 CMC、以及“可通过 Google Play System Updates 回推到 Android 12+”这组版本结论写得偏满，当前章节缺少逐项可追溯的版本证据。
- **建议**：由 Task 9 对照 AOSP / 官方发布说明核对版本线；无法确认时改成更保守的版本演进描述。
- **review 日志**：logs/review/2026-04-12-03-review.md

- **类型**：需确认
- **位置**：Write Barrier / Card Table / Young GC 执行流程
- **问题**：正文把 Write Barrier 入口、Remembered Set 构建流程和 Young GC 步骤写成确定结论，但当前引用主要是概括式路径，和 Android 17 实际实现之间还缺一层源码锚点。
- **建议**：补具体 AOSP 路径或代码片段；如果某些细节只是概念示意，应明确标注适用范围和待验证点。
- **review 日志**：logs/review/2026-04-12-03-review.md

- **类型**：需确认
- **位置**：Perfetto 分析章节
- **问题**：`android_garbage_collection_events` 表、`actual_frame_timeline` 表、`art_gc` counter track，以及 `adb shell heapprofd --pid=<PID> --java` 这组用法需要核对当前 Android / Perfetto 版本的可用性、表名和采集方式。
- **建议**：由 Task 9 复核 Perfetto stdlib、数据表和 heapprofd 命令；必要时改成已验证可运行的查询与抓取方法。
- **review 日志**：logs/review/2026-04-12-03-review.md

- **类型**：需补充素材
- **位置**：GC 与掉帧的 Perfetto 证据
- **问题**：GC pause 与 doFrame 冲突、正常 GC 模式 vs 内存抖动模式目前只有文字和 ASCII 示意，没有真实 Trace 截图或等价图示，证据链不完整。
- **建议**：补 2-3 张真实 Perfetto 片段，至少覆盖 GC pause 与 FrameTimeline 重叠，以及高频 Young GC 的典型图形。
- **review 日志**：logs/review/2026-04-12-03-review.md


## [Task9 Deep Review] 4.8 ART 分代垃圾回收与 GC 暂停优化 — 2026-04-12
- **类型**：交叉引用
- **位置**：行 60、437-439
- **问题**：正文把 §7.2 写成“滑动卡顿分析”，但 `src/SUMMARY.md` 中 7.2 实际标题是“卡顿原因体系”。
- **建议**：按真实意图改成 §7.2（卡顿原因体系）、§7.3（卡顿分析方法论）或 §7.8（RecyclerView 列表滑动性能深度优化）。

- **类型**：引用链失效
- **位置**：frontmatter `sources`、行 117、455、485
- **问题**：`https://source.android.com/docs/core/perf/art-management` 当前返回 404，和文中的 `[已验证]` 标注不一致。
- **建议**：更新为当前有效的 AOSP / Android 官方文档 URL，并重新核实依赖该链接的版本结论与性能数据。

- **类型**：数据支撑
- **位置**：行 96-97、251-258、317-318
- **问题**：GC jank 诊断段落把 `art_gc` counter、GC slice 颜色密度和 SQL 表可用性写成通用结论，但没有给出 trace config、版本前提或已跑通的样例 trace。
- **建议**：补一个已验证 trace 的截图 + SQL 结果，顺带说明使用的 Perfetto 版本、Android 版本和采集配置。

- **类型**：交叉引用/内容污染
- **位置**：行 497-500
- **问题**：参考资料摘要把 ART 分代 GC 与 `DeliQueue` 并列，主题发生串线。DeliQueue 属于 MessageQueue/Looper 方向，不是 GC 机制的一部分。
- **建议**：删除这句，或把该条研究摘要改回只描述 ART GC / MarkCompact / young generation 相关结论。


## [Task6 Review] 5.8 后台执行限制与优化 — 2026-04-12
- **类型**：需确认
- **位置**：App Standby Buckets：五级分类
- **问题**：Bucket 执行频率、Doze 维护窗口时长，以及 `DeviceIdleController` 作为核心代码路径的写法偏满，可能把 App Standby / bucket 管理链路写窄了。
- **建议**：由 Task 9 对照 UsageStatsService / AppStandbyController / JobScheduler 的实际实现核对 bucket 管理路径，并把频率结论收窄到有证据的范围。
- **review 日志**：logs/review/2026-04-12-04-review.md

- **类型**：需确认
- **位置**：前台服务类型体系 + 超时机制
- **问题**：FGS 类型列表与后文超时段落不完全一致，`mediaProcessing`、权限映射和 Android 14 / 15 的类型边界需要统一核对。
- **建议**：核对官方 FGS types 文档与 Android 15 行为变更，再统一类型矩阵、权限和 6 小时预算说明。
- **review 日志**：logs/review/2026-04-12-04-review.md

- **类型**：需确认
- **位置**：JobScheduler：系统级调度 + 版本演进 Android 16 / 17
- **问题**：`JobDebugInfo`、`getPendingJobReasonsHistory` 以及 Android 17 行为变化被写成了硬结论，当前来源链还不够完整。
- **建议**：由 Task 9 对照 Android 16 / 17 官方文档和 AOSP API 复核；无法确认时改成更保守的表述。
- **review 日志**：logs/review/2026-04-12-04-review.md

- **类型**：需补充素材
- **位置**：在 Perfetto 中的表现
- **问题**：`device_idle`、后台 Job 延迟和网络受限的章节仍缺真实 Trace 或等价图示，当前只有读法说明，没有可复核证据。
- **建议**：补 2 组真实 Perfetto / Battery Historian 片段，至少覆盖 Doze 状态切换与后台任务延迟两个场景。
- **review 日志**：logs/review/2026-04-12-04-review.md


## [Task9 Deep Review] 5.8 后台执行限制与优化 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 191-202 Perfetto 观测
- **问题**：`device_idle`、`am_proc_start` / `am_kill`、Network Track 仅给了读法说明，没有已跑通的 trace config、截图或 SQL 证据，当前读者无法复核这些观察点。
- **建议**：补 1 组 Doze 状态切换 + 1 组后台 Job 延迟/Alarm 受限的真实 Trace 或 Battery Historian / dumpsys 联合示例，并确认 Track 名称与抓取配置。

- **类型**：原理链
- **位置**：行 341-351 与 CPU / 响应速度章节的关系
- **问题**：`Restricted 桶降低 cgroup 优先级`、`从通知启动 Activity 需要通过 ActivityOptions 中的 BAL 权限` 两处结论都缺少当前章节内的代码或官方文档锚点，容易把经验判断写成硬规则。
- **建议**：补充对应代码路径 / 官方文档；如果证据链暂时不完整，就把表述收窄为“可能受版本与场景影响，需要结合具体系统验证”。

## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-12
- **类型**：数据缺失
- **位置**：在 Perfetto 中的表现（Lines 229, 237-239, 247-249）
- **问题**：正文直接给出 `dequeueBuffer > 2ms`、`doComposition < 1ms`、`Client 合成 3-8ms`、`异常场景 12ms` 这类阈值，但没有设备型号、刷新率、Layer 数量、trace config 或截图上下文。它们现在更像经验值而不是可复核证据。
- **建议**：补 1 组真实 Trace 或明确标注“示例范围，仅用于帮助理解”，同时给出设备/刷新率/场景条件。

## [Task9 Deep Review] 2.6 SurfaceFlinger 与合成 — 2026-04-12
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters` + Buffer 管理 / BlastBufferQueue 小节
- **问题**：正文大量依赖 BufferQueue、BLAST 与 fence 语义，但 `related_chapters` 只列了 `2.1/2.3/2.4/2.5/2.10/7.3`，没有把最直接相关的 `§2.13 BufferQueue`、`§2.16 Sync Fence` 挂出来。
- **建议**：把 `2.13` 和 `2.16` 加入 `related_chapters`，并在 BufferQueue / BLAST 小节正文里显式跳转。

## [Task9 Deep Review] 2.7 Hardware Layer — 2026-04-12
- **类型**：数据缺失
- **位置**：行 184-208 两组 gfxinfo 实验表
- **问题**：表格给出了 Janky Frames、99th percentile 和 High input latency，但没有设备型号、Android 版本、刷新率、View 尺寸、动画类型、采样轮次和 `dumpsys gfxinfo` / framestats 的采集命令。当前数字只能说明“某次实验如此”，不足以支持章节级结论。
- **建议**：补实验环境（设备/系统/刷新率）、测试脚本、样本量和采集命令；至少说明这些数据来自哪一版 demo、哪一台设备、跑了多少轮。

- **类型**：数据缺失
- **位置**：行 232-245 Perfetto / Show hardware layers updates 诊断方法
- **问题**：正文给了 `buildLayer` / `buildDrawingCache` 的读法，但没有任何真实 Trace、track 名称、slice 持续时间或 FrameTimeline 对照，读者很难判断“看到什么才算异常”。
- **建议**：补 1 组真实 Perfetto 截图或文字化 trace 片段，至少标出 MainThread、RenderThread、`buildLayer`、`buildDrawingCache/SW Layer`、FrameTimeline 或 SurfaceFlinger 相关轨道的位置。


## [Task6 Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-04-12
- **类型**：需确认
- **位置**：`Expedited Job` 段落
- **问题**：`WorkManager` 的 `setExpedited(ExistingWorkPolicy.APPEND)` 写法与常见 API 形态不一致，`Expedited` 配额耗尽后的降级路径也缺少更精确的源码或官方文档支撑。
- **建议**：交给 Task 9 核对 `setExpedited()` 的真实参数类型、WorkManager 到 JobScheduler 的映射方式，以及 out-of-quota 时的实际行为。
- **review 日志**：logs/review/2026-04-12-07-review.md

- **类型**：需确认
- **位置**：`Android 17 新增调试能力`、`版本差异与兼容性`
- **问题**：`JobDebugInfo`、`getPendingJobReasonStats()`、`AlarmManager.setExactAndAllowWhileIdle(OnAlarmListener)` 和 `Android 16 / 17` 的 API Level 归属写在一起，版本边界有混用风险。
- **建议**：交给 Task 9 统一核对 Android 16 / 17 的 API Level、类名、方法名和功能归属，再回写本章与相关章节。
- **review 日志**：logs/review/2026-04-12-07-review.md

- **类型**：需补充素材
- **位置**：`在 Perfetto 中分析 JobScheduler`、`JobDebugInfo API`
- **问题**：`Jobs` track、`android.job_scheduler` SQL module、`jobscheduler` atrace category 目前只有文字描述，没有配套 Trace 截图或更精确的验证来源，证据链偏薄。
- **建议**：补 1 组真实 Perfetto Trace 观察面，至少覆盖 Job 执行 slice、Device State / Jobs track 和 SQL 查询结果，再补回章节。
- **review 日志**：logs/review/2026-04-12-07-review.md

- **类型**：需补充素材
- **位置**：`WakeLock 惩罚政策`、`Android Vitals 监控指标`
- **问题**：`[已验证: googleblog.com + android.com, 2026-03-01]` 只有站点级来源，没有原始政策链接；`Android Vitals` 指标口径也没有落到具体页面或文档。
- **建议**：补 Google Play 政策原文、Android Developers / Play Console 指标页面链接；如果暂时补不齐，把强断言下调为 `[待验证]`。
- **review 日志**：logs/review/2026-04-12-07-review.md

- **类型**：需重写
- **位置**：`合规方案`、`最佳实践与优化策略`
- **问题**：后半段以清单为主，缺少一个从问题现象、调度选型到工具验证的完整案例，读起来更像汇总而不是工程师经验分享。
- **建议**：交给 Task 2B 用一个真实场景串起 `WorkManager`、`UIDT`、`Foreground Service` 的选择边界，再回扣 Perfetto / dumpsys 的观测方法。
- **review 日志**：logs/review/2026-04-12-07-review.md

## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 240 PeriodicWorkRequest 调度开销
- **问题**："写入 + 注册的开销大约是几十毫秒"没有实验条件、设备、Android 版本、样本数或源码依据，属于会被读者当成经验常量的量化断言。顺带一提，这一句还命中了 STYLE.md 禁词 `这意味着`。
- **建议**：改成明确的实验结论格式（设备/版本/trace 或 benchmark 方法/样本量），或者降级为"存在额外数据库写入与重新调度成本，量级需按设备实测"。

## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 400-419 Play Store 后台行为政策 / Android Vitals
- **问题**：2 小时 / 24 小时、5% session、WakeLock 指标等关键口径目前只挂了站点级来源，缺少原始 Play policy、Android Developers 或 Play Console 帮助页链接。
- **建议**：补原始政策页和指标定义页；如果暂时拿不到一手来源，把具体阈值降级为 `[待验证]`，不要保留硬数字。

## [Task9 Deep Review] 5.10 JobScheduler/WorkManager 调度与后台任务性能 — 2026-04-12
- **类型**：交叉引用
- **位置**：行 549 User-Initiated Data Transfer 参考链接
- **问题**：`https://developer.android.com/guide/background/persistent/user-initiated-data-transfer` 当前返回 404，参考资料区存在失效官方链接。
- **建议**：改成仍然在线的官方入口（如 `JobInfo.Builder#setUserInitiated(boolean)` reference 或新的 UIDT 指南页面），避免读者顺着参考资料跳到死链。


## [Task6 Review] 2.8 过度绘制 — 2026-04-12
- **类型**：需补充素材
- **位置**：Perfetto 分析（L99-L107）
- **问题**：只写了 GPU Track / RenderThread Track 级别的泛化描述，缺少具体 Track 名称、判断步骤和真实 Trace 证据；当前仍停在 `[待补充]`。
- **建议**：补 1-2 张真实 Perfetto 片段，明确对应 Track、观察点和过度绘制与 GPU 饱和的关联判断。
- **review 日志**：logs/review/2026-04-12-08-review.md

- **类型**：需确认
- **位置**：检测工具与验收标准（L93-L115）
- **问题**：`粉色区域不超过屏幕 1/4` 与 `Tracer for OpenGL ES` / `Android Device Monitor` 的推荐用法缺少可追溯来源，后者还存在版本时效性风险。
- **建议**：核对这些建议是否仍适用于当前 Android Studio / 平台版本；无可靠来源时改成经验性提示并明确适用范围。
- **review 日志**：logs/review/2026-04-12-08-review.md

- **类型**：需确认
- **位置**：版本演进 + frontmatter applicable_versions（L8, L251-L262）
- **问题**：Android 4.3 对 `clipRect` / `quickReject` 的硬件加速支持、Android 7 SurfaceFlinger 优化、Android 12 DisplayList 合并，以及 Android 16 API 级别写法都带版本风险。
- **建议**：由 Task 9 对照 AOSP / 官方文档逐条核对；不能确认的版本结论改成更保守的表述。
- **review 日志**：logs/review/2026-04-12-08-review.md

- **类型**：需重写
- **位置**：Jetpack Compose 扩展（L264-L288）
- **问题**：这一节和前文主线衔接偏硬，部分因果关系写得过满，例如 `drawBehind` 比 `background` 更高效、`derivedStateOf` 可间接减少过度绘制，容易把重组优化和像素重复绘制混在一起。
- **建议**：按“Compose 中怎么发现 overdraw / 哪些场景与 View 系统一样 / 哪些说法需要证据”重写成两个短块，并把能直接验证的结论和经验判断分开。
- **review 日志**：logs/review/2026-04-12-08-review.md


## [Task9 Deep Review] 2.8 过度绘制 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 100 / 行 102 验收标准与倍率显示
- **问题**：`粉色区域不超过屏幕 1/4` 与 `2.35x` 数值倍率历史都没有可追溯来源，但工具段落用了 `[已验证: 官方文档]` 口径，容易让读者以为这些阈值来自官方
- **建议**：如果拿不出官方文档或可复现实验来源，就改成经验性建议，并标出适用设备/场景

## [Task9 Deep Review] 2.8 过度绘制 — 2026-04-12
- **类型**：源码准确性
- **位置**：行 313 参考资料
- **问题**：参考资料只保留早期 `frameworks/base/libs/hwui/OpenGLRenderer.cpp`，与 `android-16.0.0_r1` 的校验口径不一致，也无法支撑现代 RenderThread / Skia / Compose 讨论
- **建议**：补当前版本源码路径，或在参考资料中明确该文件只用于早期历史实现

## [Task9 Deep Review] 1.9 Package Manager Service 与应用安装性能 — 2026-04-12
- **类型**：数据缺失
- **位置**：Android 16 云端编译（行 295-305）
- **问题**：`Cloud Compilation` / `Secure DEX Metadata (SDM)` 段落当前主要依赖二手新闻与大会口径，缺少可回溯的 AOSP / 官方文档锚点。对“设备端跳过 dex2oat”“SDM 与 APK 同签名”这类细节，章节写成了确定结论，但证据链不够硬。
- **建议**：补 Android 官方文档、AOSP 代码或正式发布材料；如果暂时只能拿到媒体报道，应把关键判断改成 `[待验证]`，并明确这是 Play 分发侧能力而不是通用 sideload 行为。



## [Task6 Review] 5.9 ADPF 自适应性能框架 — 2026-04-12
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `<!-- outline-start -->` / `<!-- outline-end -->` 大纲块，Task 6 无法按锚点检查覆盖率；`ADPF 的完整工作流` 到 `扩展` 一段也缺少可回溯锚点。
- **建议**：按 writing-guide.md 补齐大纲与锚点，再回到 Task 6 做覆盖检查。
- **review 日志**：logs/review/2026-04-12-1013-review.md

- **类型**：需确认
- **位置**：HintSession 示例代码（L61-L72）
- **问题**：`updateTargetWorkDuration()` 的注释写的是“从 60 fps 切到 120 fps”，但传入值 `16_666_000L` 对应 16.666 ms，更像 60 fps；注释和示例值不一致。
- **建议**：由 Task 9 核对 API 用法后，统一示例注释和数值。
- **review 日志**：logs/review/2026-04-12-1013-review.md

- **类型**：需确认
- **位置**：Game State 段落与版本演进表（L203-L218, L263）
- **问题**：正文使用 `GameStateManager` 与 `android/app/GameStateManager` 引用，需核对实际类名、调用入口和 Android 13 的 API surface。
- **建议**：交由 Task 9 核对官方 API；如果实际入口是 `GameManager#setGameState(GameState)`，同步改正文、代码示例与版本表。
- **review 日志**：logs/review/2026-04-12-1013-review.md

- **类型**：需确认
- **位置**：Android 16 的 Headroom API（L103-L111, L266）
- **问题**：`SystemHealthManager.getCpuHeadroom()` / `getGpuHeadroom()`、`AThermal_HeadroomCallback` 的引入版本和宿主类需要核对；版本演进表里的 API 边界也要和全书约定保持一致。
- **建议**：由 Task 9 统一核对类名、API level 和 Android 16/17 的版本写法。
- **review 日志**：logs/review/2026-04-12-1013-review.md

- **类型**：需补充素材
- **位置**：Perfetto 分析与结尾扩展（L231-L314）
- **问题**：`power.hint_session` / `power.thermal` 的观察点没有真实 Trace 截图或等价图示支撑，末尾两节也更像资料汇总，收尾偏空。
- **建议**：补 1-2 份真实 Trace 截图，至少覆盖 Hint Session 与 CPU frequency 的对应关系；结尾最好补一个真实接入或设备差异场景。
- **review 日志**：logs/review/2026-04-12-1013-review.md


## [Task6 Review] 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线 — 2026-04-12
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `<!-- outline-start -->` / `<!-- outline-end -->` 大纲块，Task 6 无法按锚点检查覆盖率。
- **建议**：按现有章节结构补齐大纲与锚点，再回到 Task 6 做覆盖检查。
- **review 日志**：logs/review/2026-04-12-1105-review.md

- **类型**：需补充素材
- **位置**：NPU 观察点与 Perfetto 分析（L67, L175-L185）
- **问题**：Perfetto 段只有通用描述，没有真实 trace 截图或等价图示，难以支撑“怎么在实际工作中排查”的主线。
- **建议**：补 1-2 份真实 trace，至少覆盖 CPU 推理、GPU Delegate、NPU/NNAPI Delegate 三种观察点。
- **review 日志**：logs/review/2026-04-12-1105-review.md

- **类型**：需确认
- **位置**：NPU/AICore/Gemini Nano 数据与版本边界（L61-L63, L119-L121, L141-L151）
- **问题**：TOPS、tokens/s、首 token 延迟、内存峰值、Nano v3/v4 时间线仍以确定口吻出现，但验证标注和来源不足。
- **建议**：由 Task 9 核对数据来源、测试条件和版本边界；补不齐时降级为定性表述。
- **review 日志**：logs/review/2026-04-12-1105-review.md

- **类型**：需重写
- **位置**：AICore 与 Gemini Nano / 模型优化技术（L131-L171）
- **问题**：两节更像资料汇总，和“性能工程师如何判断代价与收益”的主线衔接较弱，实战姿态不够。
- **建议**：收紧为工程判断视角，说明什么时候该关心 AICore、量化、Delegate 选择，以及这些选择怎样反映到 Trace、内存和热表现。
- **review 日志**：logs/review/2026-04-12-1105-review.md

## [Task9 Deep Review] 5.9 ADPF 自适应性能框架 — 2026-04-12

- **类型**：交叉引用
- **位置**：行 295 与其他章节的关系
- **问题**：`§14.7 Perfetto 高级分析` 与 SUMMARY.md 不一致。14.7 实际是 ProfilingManager，Perfetto 的高级用法在 13.7。
- **建议**：改成 `§13.7 Perfetto 的高级用法`，或直接写准确标题。

- **类型**：数据缺失
- **位置**：行 301-307 Unity/Unreal Engine 的 ADPF 集成
- **问题**：`Unity 从 2021.2 版本开始提供 ADPF 集成插件` 这种版本结论没有给出包名、Android provider 版本或官方文档。当前说法过于笼统，容易把 Unity 版本、Adaptive Performance 包版本、Android provider 版本混成一个数字。
- **建议**：补 Unity Adaptive Performance 包版本矩阵、Android provider 版本与官方链接；补不齐时降级为“Unity 通过 Adaptive Performance Android provider 支持 ADPF”。

- **类型**：数据缺失
- **位置**：行 311-317 OEM 对 ADPF 的定制
- **问题**：高通 PerfLock、联发科 Perfservice、Tensor 定制策略这些判断没有给出公开资料或 AOSP 锚点，当前更像经验判断。
- **建议**：补厂商公开文档 / 会议资料 / 可验证源码入口；补不齐时改成 `[待验证]`，避免把厂商实现细节写成确定事实。



## [Task6 Review] 5.7 CPU 相关的版本演进 — 2026-04-12
- **类型**：需补充素材
- **位置**：`在 Perfetto 中的观察`
- **问题**：这一节目前只有泛化读法，没有真实 Trace 截图、具体 track / slice 样例或查询结果，读者很难把版本演进里的判断映射到实际证据。
- **建议**：补 1-2 组真实 Perfetto 片段，至少覆盖 Doze 空闲期、JobScheduler 调度间隔变化或 EAS 任务迁移中的一个具体案例。
- **review 日志**：logs/review/2026-04-12-12-review.md

- **类型**：需确认
- **位置**：`Android 15：后台网络访问受限`
- **问题**：`UnknownHostException` 和“后台网络操作必须通过 WorkManager 或前台服务”这组结论写得偏满，当前章节内没有给出足够清楚的版本边界和一手来源。
- **建议**：由 Task 9 核对 Android 15 官方行为变更与适用条件，再决定保留硬结论还是改成更保守的描述。
- **review 日志**：logs/review/2026-04-12-12-review.md

- **类型**：需确认
- **位置**：`GKI 对内核调度模块定制化的影响`
- **问题**：Android 12 强制、Google 签名 boot image、Android 15 与 16KB page size / Play 要求被写在同一段里，GKI、page size 和发布政策的边界不够清楚。
- **建议**：拆开核对 GKI 版本要求、16KB page size 与 Play 兼容政策的适用范围，再由 Task 2B 收窄表述。
- **review 日志**：logs/review/2026-04-12-12-review.md

## [Task9 Deep Review] 5.7 CPU 相关的版本演进 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 250-266 Android 15 / Android 16 小节
- **问题**：Android 15 的 `UnknownHostException`、Doze 50% / 最多 3 小时收益，以及 Android 16 JobScheduler 配额优化，当前缺少精确的一手来源与 API 锚点；尤其 Android 16 小节仍以 web search 摘要为主。
- **建议**：补官方页面或 blog 的精确链接，并把 API / adb 入口写实（如 `JobParameters.getStopReason()`、`JobScheduler#getPendingJobReasonsHistory()`）；如果一手来源拿不稳，就把结论收窄为更保守的行为描述。

## [Task9 Deep Review] 1.1 Android 分层架构 — 2026-04-12
- **类型**：数据缺失
- **位置**：Zygote / Binder / JNI / VNDK 的量化断言（如 20-50ms、10-100μs、100-200ns、30-50%）
- **问题**：章节给了多组很具体的时间和收益数字，但没有绑定设备、Android 版本、benchmark、Trace 或官方原始来源。当前写法更像经验值，不足以当成通用技术结论。
- **建议**：每组数字至少补 1 个来源锚点（官方文档、AOSP 注释、benchmark 名称、真实 Trace 截图）；补不齐时改成定性描述或明确标注“经验量级”。

- **类型**：原理完整性
- **位置**：`在 Perfetto 中的表现` → `三种数据源与三层架构的对应关系`
- **问题**：正文把 Perfetto 数据源写成与“Android 的三层结构”一一对应，但本章前文定义的是五层架构，而且现代 Perfetto 还包含 FrameTimeline、track_event、heapprofd 等数据源。当前写法会让读者把观测层和系统分层混成一张一一映射表。
- **建议**：改成“常见性能分析数据源的粗分类”，保留 ftrace / atrace / procfs 作为主线，同时注明 FrameTimeline / track_event 等补充来源，避免使用“一一对应”的硬表述。

## [Task6 Review] 7.8 RecyclerView 列表滑动性能深度优化 — 2026-04-12
- **类型**：需确认
- **位置**：GapWorker 预取机制（“从 Android 5.0 开始引入”/“COMMIT 阶段触发”/代码注释）
- **问题**：预取引入时间、触发时机，以及注释里的 API 名需要按 RecyclerView 版本和实际源码调用路径再核对。
- **建议**：回看 recyclerview-1.4.0 的 GapWorker/RecyclerView/LayoutManager 相关源码，修正版本表述和注释。
- **review 日志**：logs/review/2026-04-12-14-review.md

- **类型**：需确认
- **位置**：RecycledViewPool 共享示例
- **问题**：`setRecycleChildrenOnDetach(true)` 的调用对象需要按实际 API 所属类核对，当前示例有直接复制后编译失败的风险。
- **建议**：核对 API 所属类与调用位置，再给出可编译的共享 Pool 示例。
- **review 日志**：logs/review/2026-04-12-14-review.md

- **类型**：需确认
- **位置**：RecyclerView 1.4 与 ARR 小节
- **问题**：`hasArrSupport()`、`getSuggestedFrameRate(int)`、`getSupportedRefreshRates()` 需要再核对实际 API 名、所属类和版本边界。
- **建议**：按官方文档和 AOSP 实现逐项核对，避免把不存在或仅内部使用的接口写成公开 API。
- **review 日志**：logs/review/2026-04-12-14-review.md

- **类型**：需补充素材
- **位置**：在 Perfetto 中分析 RecyclerView 性能
- **问题**：当前只有通用 SQL 和截图占位，还缺 1 个真实滑动 trace 案例，把 RV Layout、RV OnBindView、RV Prefetch 的观察顺序落到实际问题上。
- **建议**：补 1 个真实 trace，按“现象 → Trace → 定位 → 修复”串联本章的缓存、预取和布局分析。
- **review 日志**：logs/review/2026-04-12-14-review.md

- **类型**：需重写
- **位置**：全章主线（尤其是 Perfetto 分析段）
- **问题**：当前更像机制清单，L4 活人感偏弱，缺少一个完整排查案例把缓存、预取、嵌套滑动和 trace 观察路径串起来。
- **建议**：在保留现有机制说明的前提下，追加或重写 1 个完整实战案例，增强章节推进线。
- **review 日志**：logs/review/2026-04-12-14-review.md

## [Task9 Deep Review] 6.5 SharedPreferences/DataStore 性能与 ANR 优化 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 104、281、322、334 文件大小 / 等待时长经验阈值
- **问题**：`几十 KB`、`50KB`、`500ms` 被当成接近定量阈值使用，但正文没有给设备类型、存储介质（UFS/eMMC）、文件大小分布、fsync 时延或 trace 样本。读者容易把经验值误读为通用结论。
- **建议**：改成“经验启发式”，或补一组明确数据条件（设备、Android 版本、SP 文件大小、平均/长尾写入耗时、触发 ANR 的案例）。

- **类型**：交叉引用
- **位置**：frontmatter `related_chapters`
- **问题**：当前列出的 `6.3`、`9.1` 在仓库里不存在，会导致索引和后续交叉引用失真。当前内容更接近 `6.2 文件系统`、`6.4 存储相关的版本演进`、`9.3 ANR 分析方法`、`9.4 特殊场景的 ANR`。
- **建议**：把不存在的章节号替换为实际存在的小节，并在正文相应位置补显式引用。

## [Task6 Review] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-04-12
- **类型**：需确认
- **位置**：Thermal HAL 小节 + 版本演进表
- **问题**：正文把 AIDL 接口、HIDL 2.0 和 Android 14 之后的迁移关系写在一起，版本边界不够清楚。
- **建议**：请 Task 9 核对 `hardware/interfaces/thermal/` 的接口演进，再统一正文和版本表。
- **review 日志**：logs/review/2026-04-12-15-review.md

- **类型**：需确认
- **位置**：Thermal Headroom 段 / 版本演进表 Android 16-17
- **问题**：`SystemHealthManager.getCpuHeadroom()`、`getGpuHeadroom()`、`AThermal_HeadroomCallback` 的 API 名称和首发版本存在风险。
- **建议**：请 Task 9 核对官方 API diff 和版本约定。
- **review 日志**：logs/review/2026-04-12-15-review.md

- **类型**：需确认
- **位置**：Perfetto SQL 示例
- **问题**：`cpu_frequency_scans` 表名和 thermal slice name 模式可能不是通用 schema，读者直接运行有失败风险。
- **建议**：请 Task 9 用标准 Perfetto schema 核对后再定稿。
- **review 日志**：logs/review/2026-04-12-15-review.md

- **类型**：需补充素材
- **位置**：MediaTek MAGT 案例数据
- **问题**：三组帧率、功耗和续航数字缺少精确文章标题、日期和测试条件。
- **建议**：请 Task 2B 补具体官方文章链接和测试条件，或改成定性表述。
- **review 日志**：logs/review/2026-04-12-15-review.md

## [Task9 Deep Review] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-04-12
- **类型**：交叉引用
- **位置**：行 669 官方文档链接
- **问题**：`https://source.android.com/docs/core/thermal` 当前返回 404，和正文标注的“[已验证]”不一致。
- **建议**：改成仍然有效的官方页面 `https://source.android.com/docs/core/power/thermal-mitigation`，并把引用说明和当前验证基线对齐。

## [Task9 Deep Review] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 605-613 测试方法
- **问题**：`环境温度每升高 5°C，thermal throttling 触发时间大约提前 20-30%` 是定量断言，但没有设备、环境舱、负载模型和样本数，当前证据不足以支撑全局经验值。
- **建议**：补测试条件和样本范围，或者降级成“环境温度升高会明显提前 throttling 触发时间，具体幅度依设备散热与负载而异”。

## [Task9 Deep Review] 5.12 Thermal 管控深度：从内核子系统到 ADPF 主动降频 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 640-647 常见误区 / OEM 软件策略收益
- **问题**：`多核中频 vs 单核高频功耗差异可达 30%`、`提前 30 秒降载可将持续性能窗口延长 40-60%` 都是强量化结论，但正文没有实验来源、机型、场景或官方材料。
- **建议**：为每组数字补精确来源；如果暂时拿不到实验数据，改成定性表述，避免给读者造成“这是通用结论”的错觉。



## [Task6 Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-04-12
- **类型**：需补充素材
- **位置**：各格式解码耗时对比
- **问题**：JPEG / PNG / WebP / AVIF 的耗时表以“典型中端设备”估算值直接给出，但缺少测试设备、图片样本、解码器实现和原始来源。当前 `[待验证]` 还不足以支撑这组表格进入定稿。
- **建议**：请 Task 2B 补充 benchmark 条件和原始来源；如果补不齐，就把表格降级为定性比较。
- **review 日志**：logs/review/2026-04-12-16-review.md

- **类型**：需确认
- **位置**：Coil 管线架构 / Coil vs Glide 的选择
- **问题**：正文把 Coil 的 Bitmap 管理概括成“复用系统 `inBitmap`”，但这一结论和 Coil 版本差异、Bitmap Pool 策略变化之间的关系没有交代清楚，容易让读者把不同版本的行为混在一起。
- **建议**：请 Task 9 按实际引用的 Coil 版本核对 Bitmap 复用策略，再决定正文和对比表怎么写。
- **review 日志**：logs/review/2026-04-12-16-review.md

- **类型**：需补充素材
- **位置**：在 Perfetto 中定位图片解码卡顿
- **问题**：这一节已经给了方法，但还缺 1 组真实 Trace 片段或等价图示，尤其是主线程解码、`Trace.beginSection()` 打点后在 Perfetto 中的观察顺序。
- **建议**：请 Task 2B 补 1-2 张真实 Perfetto 片段，至少覆盖主线程解码 slice 和对应卡顿帧的观察点。
- **review 日志**：logs/review/2026-04-12-16-review.md


## [Task9 Deep Review] 5.11 端侧 AI 推理性能：NPU/GPU 加速与 TFLite 管线 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 49、119-127、163-165
- **问题**：`30-100 ms`、`200-400 MB`、`8/5/2 ms`、`2-4 倍`、`<1% 精度损失` 等量化数字没有给出模型版本、输入尺寸、量化策略、batch size、设备型号和测试框架，当前只能当经验值，不能当通用结论。
- **建议**：把这些数字改成“示例 benchmark”，并补齐测试条件；没有条件时降级为定性描述。

- **类型**：数据缺失
- **位置**：行 147-151
- **问题**：Gemini Nano 的 `100 ms` 首 token、`93 tokens/s`、`1.2 GB / 3.4 GB` 内存数字没有一手来源，也没有说明是 prompt-prefill、decode 还是端到端场景。
- **建议**：补充原始 benchmark 来源与测试口径，区分 prefill / decode / end-to-end；没有一手来源就统一标记为 [待验证]。

- **类型**：交叉引用
- **位置**：行 207-210 + frontmatter related_chapters
- **问题**：正文明确引用了 `§4.4 Low Memory Killer`，但 frontmatter `related_chapters` 只有 `4.3`，缺少和 LMK 章节的显式关联。
- **建议**：把 `4.4` 加入 `related_chapters`，并检查 `4.3 / 4.4` 在本节中的角色是否需要拆分说明。


## [Task6 Review] 1.2 系统启动全流程 — 2026-04-12
- **类型**：需重写
- **位置**：开机性能优化的常见手段
- **问题**：这一节现在更像通用清单，缺少“看到什么启动瓶颈，再选什么优化动作”的分析路径。并行启动、延迟加载、cgroup、Zygote 优化和厂商案例被平铺在一起，读者能记住名词，但不容易形成排查顺序。
- **建议**：请 Task 2B 按“启动阶段/瓶颈信号 → 对应优化动作”的顺序重写这一节，把通用建议和厂商特定策略拆开。
- **review 日志**：logs/review/2026-04-12-17-review.md

- **类型**：需补充素材
- **位置**：厂商优化黑科技 + Android 16 的启动优化
- **问题**：小米、华为、三星和 Pixel 的案例里有多处定量或结论性表述，但正文缺少精确来源、设备条件和测试口径。当前 [待验证] 还不足以支撑这些段落进入定稿。
- **建议**：请 Task 2B 补充一手来源和测试条件；补不齐时，把定量表述降级为定性描述，并删掉宣传味较重的说法。
- **review 日志**：logs/review/2026-04-12-17-review.md

- **类型**：需确认
- **位置**：Launcher：最后的临门一脚 + boot_completed 广播
- **问题**：正文把“桌面可见”“Launcher 启动”“LOCKED_BOOT_COMPLETED / BOOT_COMPLETED”压在一段里，叙述过快，容易让读者把用户可见节点和广播节点当成同一个里程碑。
- **建议**：请 Task 9 先核对启动里程碑和发送主体，再由 Task 2B 把这几个节点拆开写清楚。
- **review 日志**：logs/review/2026-04-12-17-review.md


## [Task9 Deep Review] 7.8 RecyclerView 列表滑动性能深度优化 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 230-234 VSync 时间精度与步幅波动
- **问题**：`±1ms` 取整误差、`120Hz 下约 12%` 波动，以及“Perfetto FrameTimeline 不会标记为 Jank”的结论都属于强断言，但当前只挂了“高爷补充素材”，没有绑定 `OverScroller` / 时间源代码路径、实验 trace 或可复现实验条件。
- **建议**：补一条源码或实验链路（时间戳来源、位移计算公式、120Hz 设备 trace / screen recording 对照）；如果证据还不够，就把这段降级成待验证假设，不要直接写成结论。

- **类型**：数据缺失
- **位置**：行 264-283 Perfetto 分析实战
- **问题**：本节给了 SQL 和截图占位，但没有一条真实 trace、实际 slice 名命中结果、阈值样本或“现象 → Trace → 根因 → 修复”的闭环案例。读者即使知道概念，也很难复现整套排查流程。
- **建议**：补 1 个真实滑动 trace 案例，至少包含 `RV OnLayout` / `RV Prefetch` / `RV onBindViewHolder` 中的一组真实 slice，以及修复前后对比。

## [Task6 Review] 6.3 I/O 调度与性能 — 2026-04-12
- **类型**：需确认
- **位置**：Android 版本 / GKI / 默认调度器映射表
- **问题**：正文把 Android 版本、GKI 内核和默认调度器写成直接映射，但这件事会受厂商内核配置影响，当前缺少更精确的设备或配置证据。
- **建议**：由 Task 9 对照 GKI 配置和主流机型内核核一轮；如果覆盖不住，就改成更保守的版本说明。
- **review 日志**：logs/review/2026-04-12-18-review.md

- **类型**：需确认
- **位置**：Perfetto SQL 查询示例
- **问题**：正文直接使用 `block_io_events` 表名和对应字段；不同 Perfetto 版本、trace 配置、stdlib 预处理表是否存在，可能并不一致。
- **建议**：由 Task 9 按当前 trace processor schema 复核表名、字段和可运行查询，必要时换成实测可跑的 SQL。
- **review 日志**：logs/review/2026-04-12-18-review.md

- **类型**：需补充素材
- **位置**：Perfetto 观察章节
- **问题**：正文已经讲了主线程 D 状态、后台写入争抢和 fsync 拉长，但没有真实 trace 截图或等价图示，证据链还不完整。
- **建议**：请 Task 2B 补 2-3 个真实 Perfetto 片段，至少覆盖这三类典型信号。
- **review 日志**：logs/review/2026-04-12-18-review.md

## [Task9 Deep Review] 6.3 I/O 调度与性能 — 2026-04-12
- **类型**：源码准确性
- **位置**：行 330 Room 异步 API
- **问题**：正文写成“Room 默认使用 `Coroutine` 或 `RxJava` 在后台线程执行数据库操作”，但 Room 不会把所有 DAO 默认异步化。只有 `suspend` / `Flow` / `LiveData` / Rx 返回类型，或显式配置的 query/transaction executor，才有对应的异步执行路径；同步 DAO 在主线程上会直接抛异常，除非显式 `allowMainThreadQueries()`。
- **建议**：把这段改成“API 形态决定执行模型”，区分 `suspend` / `Flow` / Rx / 同步 DAO 与 `allowMainThreadQueries()` 的边界。

- **类型**：数据缺失
- **位置**：行 281-343 Perfetto 观察阈值表
- **问题**：`UFS 4.0 随机读 < 1ms`、`fsync < 5ms`、`iowait > 5%` 这类数值被写成通用阈值，但缺设备、文件系统、工作负载和 trace 配置上下文。读者照搬这些数字，很容易把机型差异、F2FS/ext4 差异或采样方式差异误判成异常。
- **建议**：把数值改成“示例区间 + 测试条件”，至少补机型、存储介质、文件系统、trace 配置和 workload；拿不出统一基线时，就把这些阈值降级成经验值。



## [Task6 Review] 7.9 感知流畅性：步幅波动与无掉帧卡顿 — 2026-04-12
- **类型**：需补充素材
- **位置**：开头阈值说明、Chrome 经验、Frame Timeline 差值分析
- **问题**：文中有多处量化断言缺少可追溯来源，例如“相邻帧位移偏差超过 10% 就可能被察觉”、CV 0.05/0.1 阈值，以及 Chrome 时间精度优化经验。当前只有 `[待验证]` 占位，证据链还不够。
- **建议**：补论文、官方文档或 commit；如果找不到可靠来源，就把具体数值降级为经验描述。
- **review 日志**：logs/review/2026-04-12-19-review.md

- **类型**：需确认
- **位置**：Android 16 AppJankStats 与 RelativeFrameTimeHistogram、版本演进表、Perfetto SQL 示例
- **问题**：FrameTimeline、AppJankStats、RelativeFrameTimeHistogram 的平台版本和 API 归属存在核对风险，SQL 示例也还没有确认是否能在当前 Perfetto schema 下直接运行。
- **建议**：交给 Task 9 对照官方文档、AOSP 版本历史和 trace processor schema 复核。
- **review 日志**：logs/review/2026-04-12-19-review.md

- **类型**：需重写
- **位置**：优化策略（二）到（四）
- **问题**：后半段从问题分析切成了方案清单，和前文的 Trace 观察、真实场景回扣不够，读起来更像提纲。
- **建议**：Task 2B 收紧成 2-3 条有证据支撑的建议，最好每条都回扣到前面的症状或可观察信号。
- **review 日志**：logs/review/2026-04-12-19-review.md


## [Task9 Deep Review] 7.9 感知流畅性：步幅波动与无掉帧卡顿 — 2026-04-12
- **类型**：源码准确性
- **位置**：行 356-357 官方文档链接
- **问题**：`https://developer.android.com/develop/ui/performance/jankstats` 和 `https://developer.android.com/reference/android/view/FrameTimeline` 当前返回 404，引用链已经断掉，和“已验证”/“官方文档”定位不一致。
- **建议**：替换为可访问的 `android.app.jank.AppJankStats` / `RelativeFrameTimeHistogram` / `Choreographer.VsyncCallback` API 页面，以及 perfetto.dev 的 FrameTimeline 数据源文档。

## [Task9 Deep Review] 7.9 感知流畅性：步幅波动与无掉帧卡顿 — 2026-04-12
- **类型**：交叉引用
- **位置**：frontmatter / 与其他章节的关联
- **问题**：正文实际依赖 §7.1、§7.8、§2.4、§2.17、§3.2，但 frontmatter 没有 `related_chapters`。后续批量校验和知识图谱构建拿不到这些关联。
- **建议**：补齐 `related_chapters`，并确保章节号与现有 `src/` 文件一一对应。


## [Task6 Review] 7.11 WebView 渲染性能与优化 — 2026-04-12
- **类型**：需确认
- **位置**：预热策略 / 方案一代码示例
- **问题**：`webView.setData(null, null);` 不是标准 WebView API，当前预热示例存在接口风险。
- **建议**：由 Task 9 核对实际可用的预热调用，再由 Task 2B 回写成可运行示例。
- **review 日志**：logs/review/2026-04-12-20-review.md

- **类型**：需确认
- **位置**：双层渲染架构 / 关键认知 / 滚动性能小节
- **问题**：“不走 Android 的 Choreographer/VSync 体系”“滚动和动画由 cc 合成线程处理”等表述写得偏满，容易把 Chromium 内部调度和 Android 显示同步关系讲成绝对二分。
- **建议**：交给 Task 9 结合 Chromium 文档与 AOSP 显示链核对，再由 Task 2B 收紧表述边界。
- **review 日志**：logs/review/2026-04-12-20-review.md

- **类型**：需补充素材
- **位置**：初始化开销 / 混合渲染 / Perfetto 分析
- **问题**：双层渲染架构示意图、混合渲染 Trace、首次初始化分布仍缺真实图示或等价证据，实战链条不够完整。
- **建议**：补 2-3 份真实图示或 Perfetto 片段，至少覆盖架构图、混合渲染合成负担和首次初始化观察点。
- **review 日志**：logs/review/2026-04-12-20-review.md

- **类型**：需补充素材
- **位置**：初始化与内存量化数据
- **问题**：“200-500ms”“30-80MB”等量化描述没有同时给出设备条件、版本范围或直接来源。
- **建议**：补充测试条件或官方来源；补不齐时改成定性描述或更保守的范围表达。
- **review 日志**：logs/review/2026-04-12-20-review.md

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-04-12
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters`
- **问题**：`related_chapters` 中的 `2.10` 在 `progress.json`、`SUMMARY.md` 和 `src/` 里都找不到，对应章节不存在，当前交叉引用会把读者引向空目标。
- **建议**：核对原始意图后改成真实章节号，或直接删除 `2.10` 引用，避免出版时留下死链。

## [Task9 Deep Review] 7.10 图片加载与 Bitmap 性能优化 — 2026-04-12
- **类型**：数据缺失
- **位置**：L255、L448 AVIF 硬件解码
- **问题**：章节把“Android 14+ 设备支持硬件解码”写成普遍结论，但当前正文没有给出 CDD、codec capability 或官方文档证据，也没交代 SoC / 设备差异。
- **建议**：补官方来源并注明设备条件；如果暂时补不齐，把结论降级为“部分 Android 14+ 新设备可提供 AVIF 硬件解码，需以设备编解码能力为准”，并标 `[待验证]`。


## [Task9 Deep Review] 7.5 优化策略 — 2026-04-12
- **类型**：源码准确性
- **位置**：行 112，动态添加 View vs GONE View
- **问题**：“`GONE` 状态的 View 在 measure 阶段仍然会被遍历”这个表述过于绝对。多数 `ViewGroup.measureChildren()`/`measureChild()` 路径会跳过 `GONE` 子 View；真正稳定存在的成本是 inflate 已发生、对象常驻、父容器遍历与状态维护。
- **建议**：把结论改成“预置大量 GONE View 仍有 inflate/内存/遍历成本，但不是每次都会完整参与 measure”，避免把优化原因讲偏。


## [Task9 Deep Review] 7.5 优化策略 — 2026-04-12
- **类型**：数据缺失
- **位置**：行 165，SnapHelper 性能考量
- **问题**：“自定义 SnapHelper 要确保时间复杂度不超过 O(log n)”没有来源，也不符合 RecyclerView 实际热点。Snap 逻辑通常在已 attach 的少量 child 上线性扫描，真正要避免的是额外分配、重复布局请求和跨帧重算。
- **建议**：把要求改成“基于已 attach child 做轻量扫描，避免分配和额外 requestLayout”，不要给出缺少依据的 O(log n) 指标。


## [Task9 Deep Review] 7.5 优化策略 — 2026-04-12
- **类型**：交叉引用
- **位置**：正文多处相对链接（如 [2.4] / [2.8] / [1.4]）
- **问题**：当前 Markdown 链接写成 `part1-fundamentals/...`，从 `src/part2-performance/ch07-smoothness/05-optimization.md` 出发会解析到错误路径，实际在仓库内不可达。
- **建议**：改成正确的相对路径（如 `../../part1-fundamentals/...`），或统一改成 Obsidian wiki link，避免章节间跳转失效。

## [Task6 Review] 1.3 进程模型与生命周期管理 — 2026-04-12
- **类型**：需补充素材
- **位置**：`Binder IPC（主力通道）`
- **问题**："Binder 承担了系统中 90% 以上的跨进程调用"属于量化断言，但正文没有给出可追溯来源或适用范围。
- **建议**：补官方文档、AOSP 统计依据或实测来源；如果暂时补不齐，改成不带百分比的定性表述。
- **review 日志**：logs/review/2026-04-12-22-review.md

- **类型**：需确认
- **位置**：`Phantom Process Killer（Android 12+）`
- **问题**："每个 App 最多允许 32 个子进程"以及 `settings_enable_monitor_phantom_procs` 开关的写法带有版本和设备边界，当前缺少精确来源。
- **建议**：由 Task 9 对照官方文档和 AOSP 行为核对版本范围、默认值与设置项名称，再决定是否保留当前写法。
- **review 日志**：logs/review/2026-04-12-22-review.md

- **类型**：需补充素材
- **位置**：`在 Perfetto 中的表现` / `进程死亡回调：DeathRecipient`
- **问题**：当前只给了泛化描述，没有把 `lmkd` kill 事件、`oom_adj` 变化记录、`binderDied` 相关追踪方式落到可复现的 Trace / SQL / 截图锚点上。
- **建议**：补 2-3 个真实 Perfetto 片段或等价图示，并明确对应的数据源、track 名称或查询方式。
- **review 日志**：logs/review/2026-04-12-22-review.md

## [Task9 Deep Review] 7.11 WebView 渲染性能与优化 — 2026-04-12
- **类型**：数据缺失
- **位置**：L111-L119 / L179-L186 / L279-L284 初始化与内存量化
- **问题**：`30-50MB`、`200-500ms`、`30-80MB` 这几组数字都没有给设备型号、WebView/Android 版本、进程模式和测试方法，当前写法像“通用事实”。
- **建议**：补设备/版本/样本条件；补不齐就降级成定性表述或更保守的范围。

- **类型**：交叉引用错误
- **位置**：L507 交叉引用 §8.1 Android 功耗管理
- **问题**：仓库里的 `8.1` 实际是《响应速度原理》，当前引用标题与真实章节不一致。
- **建议**：改为真实章节号/标题；如果想引用功耗章节，需改指向正确目标。


## [Task6 Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-12
- **类型**：需确认
- **位置**：LayoutInflater.Factory2 / ComposeView 段落
- **问题**：把 ComposeView 直接归因为“跳过 XML inflate，因此创建 UI 有性能优势”，结论过满，缺少与 Compose 组合、测量和首次 composition 成本的边界说明。
- **建议**：收敛成“Compose 避开 XML inflate 固定开销”，并补充它引入的其他初始化成本；若暂时补不齐，交给 Task 9 核对后再写定性结论。
- **review 日志**：logs/review/2026-04-12-23-review.md

- **类型**：需确认
- **位置**：RelativeLayout 嵌套段（`$2^n$` 结论）
- **问题**：用“最终产生 `$2^n$` 轮”描述嵌套放大效应，结论过硬，当前没有对应源码或 trace 证据支撑严格指数关系。
- **建议**：改成定性描述，或补一段真实 trace / 源码说明两轮 measure 如何在嵌套场景放大。
- **review 日志**：logs/review/2026-04-12-23-review.md

- **类型**：需确认
- **位置**：ConstraintLayout benchmark 段
- **问题**：“一次遍历就能确定所有子 View 的位置”和“简单场景下差距在 5% 以内”都缺少明确出处和适用条件，读者容易把它们理解成普遍结论。
- **建议**：补 Google benchmark 的测试条件和来源；如果补不齐，就收敛成定性表述。
- **review 日志**：logs/review/2026-04-12-23-review.md

- **类型**：存疑
- **位置**：Perfetto 中定位具体 View 耗时段落
- **问题**：`View.setTransitionVisibility()`、`Window.setFrameContent()` 作为 trace 入口的表述不够稳，存在 API/trace tag 误导风险。
- **建议**：交给 Task 9 核对实际可用的 trace tag 或改成手动 `Trace.beginSection()` 的可验证方案。
- **review 日志**：logs/review/2026-04-12-23-review.md


## [Task9 Deep Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-12
- **类型**：数据缺失
- **位置**：L141 ComposeView 对比段
- **问题**：把 ComposeView 简化为“跳过 XML inflate，因此创建 UI 更有性能优势”，只写了省掉的成本，没有交代首次 composition、slot table、measure/layout 等新增成本边界。
- **建议**：收敛成“Compose 避开 XML inflate 固定开销”，并补一句“首帧成本要结合 composition / recomposition 一起评估”。

## [Task9 Deep Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-12
- **类型**：数据缺失
- **位置**：L292 `layout_optimizationLevel`
- **问题**：“复杂布局可减少约 20%-30% measure 时间”缺少来源、测试设备和 ConstraintLayout 版本信息。
- **建议**：补 AndroidX 官方文档或实测数据；补不齐就改成定性表述。

## [Task9 Deep Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-12
- **类型**：数据缺失
- **位置**：L448 ConstraintLayout vs LinearLayout 简单场景
- **问题**：“差距在 5% 以内”缺少 benchmark 条件与出处，当前属于裸数字。
- **建议**：补真实测试条件（节点数、层级、设备、刷新率、FrameMetrics 口径），或删除具体百分比。

## [Task9 Deep Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-12
- **类型**：数据缺失
- **位置**：L430-L434 Layout Inspector traffic light
- **问题**：把 Layout Inspector 颜色直接写成固定毫秒阈值（0.5ms / 1ms），当前缺少官方文档支撑，容易和旧版 Hierarchy Viewer 经验混淆。
- **建议**：核对当前 Android Studio 文档；若无权威阈值，就改成“颜色用于相对提示，不宜当成固定预算线”。

## [Task9 Deep Review] 7.12 View 体系性能优化：布局层级、inflate 与 measure/layout 开销 — 2026-04-12
- **类型**：交叉引用
- **位置**：L152 启动优化章节链接
- **问题**：正文链接到了不存在的 `../ch08-responsiveness/03-startup-optimization.md`。
- **建议**：修正为实际文件 `../ch08-responsiveness/03-launch-optimization.md`。


## [Task6 Review] 8.8 Android 多媒体管线性能 — 2026-04-13
- **类型**：需补充素材
- **位置**：HDR / AudioFlinger / Perfetto 小节（L167-L390)
- **问题**：HDR 渲染特征和 AudioFlinger underrun 观察点仍停留在 `[待补充]` 占位，Perfetto 小节缺少能对上正文结论的真实 trace 截图或等价图示。
- **建议**：补 2-3 个真实样例，至少覆盖 HDR tone mapping、AudioFlinger mixer/underrun、MediaCodec 解码阻塞三类观察点。
- **review 日志**：logs/review/2026-04-13-00-review.md

- **类型**：需确认
- **位置**：Media3 / 首帧延迟 / 多实例资源限制（L205-L427)
- **问题**：Reddit 缓冲策略、`80ms` 编解码器初始化、`20-30MB` Player 实例占用、`>200ms` 异常阈值等量化说法没有给出精确来源，容易把经验值写成结论。
- **建议**：交给 Task 9 对照官方文档、博客或实测数据核对；补不齐来源时，统一降级为经验描述。
- **review 日志**：logs/review/2026-04-13-00-review.md

- **类型**：需确认
- **位置**：Tunneled playback / Perfetto SQL / atrace / 版本演进（L151-L448)
- **问题**：SoC 支持差异、`EXTRACT_ARG` 参数名、atrace 示例命令、`low-latency decoding` 的版本演进都还带着明显的技术核对风险。
- **建议**：先由 Task 9 核对 AOSP / trace processor schema / 官方文档，再由 Task 2B 回写这些段落。
- **review 日志**：logs/review/2026-04-13-00-review.md

## [Task9 Deep Review] 8.8 Android 多媒体管线性能 — 2026-04-13
- **类型**：原理准确性
- **位置**：L228 Compose PlayerSurface 段落
- **问题**：把 `PlayerSurface` 写成“直接使用 ComposeView 管道”不准确。Media3 1.10 release notes 明确提到 `ContentFrame` / `PlayerSurface` 仍会受到 `SurfaceView inside a Compose AndroidView` 平台 bug 影响，说明它封装的是 `SurfaceView` / `TextureView` 这类平台 surface primitive，而不是脱离 surface 的纯 Compose 渲染路径。
- **建议**：改成“PlayerSurface 把 `SurfaceView` / `TextureView` 的管理封装进 Compose 组件”，并说明 zero-copy / overlay 是否成立仍取决于 surface type。

## [Task9 Deep Review] 8.8 Android 多媒体管线性能 — 2026-04-13
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters` + Tunneled playback / Camera → MediaCodec 小节
- **问题**：正文已经深入讨论 AudioFlinger / AAudio、Camera → Codec、HWC / tunneled，但 `related_chapters` 只列了 `2.6`、`2.13`、`2.15`、`2.16`、`8.4`、`14.9`，缺少已存在的 `1.16 Audio Pipeline 延迟与性能`、`18.14 Camera 渲染管线`、`18.15 视频叠加与 HWC`。
- **建议**：补齐这些交叉引用，避免本章与音频专题、Camera 渲染、Overlay/HWC 章节断开。

## [Task9 Deep Review] 8.8 Android 多媒体管线性能 — 2026-04-13
- **类型**：参考资料
- **位置**：frontmatter `sources`
- **问题**：AAudio 官方链接 `https://developer.android.com/ndk/guides/audio/aaudio/low-latency-audio` 当前返回 404；`https://android-developers.googleblog.com/ (Media3 1.10 Release)` 也只是首页占位，无法支撑精确溯源。
- **建议**：替换为当前可访问的官方文档或具体 release note / blog URL，避免后续复核时找不到原始依据。

## [Task6 Review] 3.2 触摸响应的性能分析 — 2026-04-13
- **类型**：需补充素材
- **位置**：延迟全景图后的 PAMTD 数据段
- **问题**：PAMTD 11ms / 点击 263ms 目前只有二手笔记来源，没有原始论文标题、实验条件和适用场景。
- **建议**：补原始论文与实验上下文，若短期补不齐，改成定性结论并保留 `[待验证]`。
- **review 日志**：logs/review/2026-04-13-01-review.md

- **类型**：需确认
- **位置**：Motion Prediction：降低感知延迟
- **问题**："从 Android 4.4（API 19）开始支持"、Jetpack motionprediction 库、Android 13+ `WindowManager` 预测渲染三组表述混在一起，平台 API 与 Jetpack 库的版本边界不清。
- **建议**：交给 Task 9 核对平台 API、Jetpack 依赖和适用场景，再决定保留哪一套表述。
- **review 日志**：logs/review/2026-04-13-01-review.md

- **类型**：需补充素材
- **位置**：厂商触控优化方案 / Input Boost 策略
- **问题**：低延迟触控 IC、主线程绑定大核、Input Boost 持续时间等断言主要依赖泛化的 web research 和待验证标注，缺少厂商文档、具体设备案例或 Trace 证据。
- **建议**：补具体设备/厂商资料，或把这一节收缩成“常见做法概览”，避免写成确定结论。
- **review 日志**：logs/review/2026-04-13-01-review.md


## [Task9 Deep Review] 4.4 Low Memory Killer — 2026-04-13
- **类型**：数据与版本口径
- **位置**：行 365-373，16KB Page Size 小节
- **问题**：正文写“Google 声称冷启动速度提升 20%-40%”。developer.android.com 当前页面给出的口径是：内存压力下 app launch time 平均下降 3.16%，部分测试样本最高到 30%；同时还给出 camera launch / power draw / boot time 的独立数据。现有数字范围偏大，也没有交代实验条件。
- **建议**：按官方页面的条件和指标重写，不要把“部分样本最高到 30%”扩写成通用 20%-40%。

## [Task9 Deep Review] 4.4 Low Memory Killer — 2026-04-13
- **类型**：数据缺失
- **位置**：行 245-247、341-343，冷启动时延与 MemAvailable 阈值
- **问题**：`缓存恢复通常 < 100ms`、`MemAvailable 长期低于 500MB` 这两组判断都带强设备前提，但正文没有机型、RAM 档位、页大小、前台负载、trace 条件。直接给固定阈值，读者很容易把经验值当成通用判定线。
- **建议**：改成“示例机型/实验条件下的观测值”，或退回定性表述，不要给未经限定的固定阈值。

## [Task6 Review] 7.1 卡顿的定义与分类 — 2026-04-13
- **类型**：需确认
- **位置**：掉帧率、Frozen Frame 与可接受阈值一节
- **问题**：`掉帧率控制在 5% 以下`、`极端场景 3-5% 可接受` 写成了通用目标，但正文没有交代适用场景、刷新率条件和明确出处。
- **建议**：交给 Task 9 核对 Android Vitals / JankStats / 行业资料，确认是否保留量化阈值；若证据不足，改成条件化表述。
- **review 日志**：logs/review/2026-04-13-03-review.md

- **类型**：需确认
- **位置**：Display HAL Jank 段落
- **问题**：`App 开发者基本无法控制` 与 Perfetto 观察方式属于跨层结论，当前章节缺少清晰的 HAL / FrameTimeline 证据链。
- **建议**：交给 Task 9 补 HAL / FrameTimeline 证据链，Task 2B 再统一回写更稳妥的表述。
- **review 日志**：logs/review/2026-04-13-03-review.md
## [Task9 Deep Review] 1.4 Binder IPC 机制与性能影响 — 2026-04-13
- **类型**：数据缺失
- **位置**：L67，冷启动 Binder 调用次数
- **问题**：`典型冷启动流程主线程可能发起 30-50 次同步 Binder 调用` 属于量化判断，但正文没有给出机型、应用形态、系统版本、trace 抓取条件。这个范围可以作为经验值，不能直接写成通用事实。
- **建议**：补一条实际冷启动 trace 的统计口径，或改成“在某类冷启动样本中常见 30-50 次”这类带条件的表述。

## [Task9 Deep Review] 1.4 Binder IPC 机制与性能影响 — 2026-04-13
- **类型**：工具链精度
- **位置**：L277-L287，Binder 风暴 SQL
- **问题**：SQL 只用 `slice.name LIKE 'binder%'` 统计事务，没有限定 Android Binder / Transactions 轨道、请求/回复方向或版本口径。不同版本和不同 trace 配置下，这个条件可能漏算、误算，甚至把非 Binder slice 混进来。
- **建议**：改成和数据源绑定的版本化查询，至少补清楚依赖 `android.binder` 还是 `ftrace`，以及应该按哪个 track/table 过滤事务。



## [Task6 Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-04-13
- **类型**：需重写
- **位置**：全文结构
- **问题**：缺少 `outline-start` / `outline-end` 与 `🔹` 锚点，Task 6 无法按统一结构检查覆盖率。
- **建议**：按 writing-guide.md 补齐大纲与锚点，再把现有 H2/H3 映射到对应骨架。
- **review 日志**：logs/review/2026-04-13-05-review.md

- **类型**：需补充素材
- **位置**：`Perfetto 中的关键 Track` / `游戏卡顿分析方法论`
- **问题**：目前只有概述和 `[图：...]` 占位，缺少真实 Trace 截图、稳定的 track/slice 名以及可复用 SQL，工程可操作性不够。
- **建议**：补 2-3 组真实 Perfetto 片段，至少覆盖帧时间异常、频率变化、热状态或 Hint Session 的对应关系。
- **review 日志**：logs/review/2026-04-13-05-review.md

- **类型**：需确认
- **位置**：`Game State API` / `Android 16/17 的游戏性能新特性`
- **问题**：`GameStateManager`、`GameState.create(...)`、Game Mode Interventions、Vulkan 1.4 默认化等表述涉及 API 与版本边界，Task 6 不做技术裁决。
- **建议**：交给 Task 9 对照官方文档 / AOSP 核对 API 名称、版本范围和适用条件。
- **review 日志**：logs/review/2026-04-13-05-review.md

- **类型**：需重写
- **位置**：`AGDK 工具链` / `OEM 游戏模式与 Game Mode API 的关系`
- **问题**：两段偏资料罗列和一般性建议，第一手观察不足，读起来更像资料汇编而不是工程师复盘。
- **建议**：Task 2B 回炉时补实际分析路径或更具体的场景判断，压缩泛化表述。
- **review 日志**：logs/review/2026-04-13-05-review.md

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-04-13
- **类型**：数据缺失
- **位置**：L67，ADPF “最高 57% 帧率提升”
- **问题**：量化结论没有交代测试游戏、SoC、功耗/温度条件和基线。即使原始材料存在，这个数字也不能直接当成通用收益。
- **建议**：补原始测试上下文，至少写清设备、负载场景和“最高值/平均值”的区别；补不齐就降成条件化表述。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-04-13
- **类型**：数据与版本口径
- **位置**：L357-L365，Android 16 新特性
- **问题**：`SystemHealthManager#getCpuHeadroom()` / `getGpuHeadroom()` 属于 API 36 的真实接口，但同一段顺手写进了 “Vulkan 1.4 默认图形 API”“ANGLE 统一兼容层”“5-15% 开销”“Game Mode PERFORMANCE 会额外优化 ANGLE” 等结论，当前引用页并不能支撑这些说法。
- **建议**：把 Headroom API 与 Vulkan/ANGLE 路线拆开；每条版本/性能断言各自补官方来源或实测，否则降为 `[待验证]`。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-04-13
- **类型**：交叉引用与来源可验证性
- **位置**：frontmatter L14-L20；参考资料 L486-L487
- **问题**：`/games/gamemode/gamemode-api`、`/games/optimize/performance`、`/reference/android/app/GameStateManager` 当前都不可用或已迁移，导致正文中的“已验证”无法复核。
- **建议**：统一替换为当前有效页面，例如 `/games/optimize/adpf/gamemode/gamemode-api`、`/games/optimize/adpf/gamemode/gamemode-interventions`、`/reference/android/app/GameState` / `GameManager`。

## [Task9 Deep Review] 8.9 Android 游戏性能与 Game Mode/State API — 2026-04-13
- **类型**：工具链精度
- **位置**：L400-L417，Perfetto SQL
- **问题**：SQL 用 `slice.name LIKE 'Choreographer#doFrame%'` 和 `countif(dur > 16.666e6)` 统计“游戏掉帧”，但没有交代只适用于 doFrame 驱动路径，也没有把 90Hz/120Hz 目标帧周期区分开。这个查询可以当示例，不能直接写成通用游戏统计模板。
- **建议**：补“适用前提”说明，并按 60/90/120Hz 给不同阈值示例；native game 另给一套 query 或明确转到 FrameTimeline/SurfaceFlinger 口径。

## [Task6 Review] 9.6 Notification 性能与 ANR — 2026-04-13
- **类型**：需确认
- **位置**：Android 17 通知性能变更 + 版本演进表
- **问题**：Android 14 并行分发、Android 15 排名优化、Android 17 后台通知监听器限频等版本断言仍缺精确来源，当前 `[已验证]` / `[待验证]` 粒度不够。
- **建议**：由 Task 9 对照 AOSP 与官方文档统一核对版本边界，再由 Task 2B 回写。
- **review 日志**：logs/review/2026-04-13-06-review.md

- **类型**：需补充素材
- **位置**：在 Perfetto 中诊断通知 ANR
- **问题**：`notif-handler` 线程、`onNotificationPosted` slice、Binder SQL 示例和 `[待补充：Trace 截图]` 仍缺真实 trace 或已跑通的 schema 证据，当前实操闭环不完整。
- **建议**：补 1-2 份真实 Perfetto 片段或已验证 SQL，并固定对应的 track、slice、table 名称。
- **review 日志**：logs/review/2026-04-13-06-review.md

- **类型**：需补充素材
- **位置**：RemoteViews / 图片通知 / 通知限流的量化成本
- **问题**：`1-2ms`、`10-20ms`、`10-50ms`、`100ms+` 等耗时结论没有给出设备、图片尺寸、系统负载或原始 benchmark 条件。
- **建议**：补测试条件与原始来源；若短期补不齐，就降级为定性描述。
- **review 日志**：logs/review/2026-04-13-06-review.md

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-13
- **类型**：源码准确性
- **位置**：L241-L252 `android:process`
- **问题**：正文把“不以冒号开头”解释成“全局进程，可以被其他 App 通过显式 Intent 访问”。官方 manifest 文档的真实约束是：该进程名可以被其他应用共享，但前提是两边共享同一 UID 且使用同一证书；组件能否被其他 App 调起取决于 exported/permission，而不是进程名本身。
- **建议**：把这段改成“global process name 允许同 UID + 同签名应用共用进程”，并把跨 App 访问条件移回 exported/permission 语义。

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-13
- **类型**：源码准确性
- **位置**：L227-L229 `ActivityManagerService.updateOomAdjLocked()`
- **问题**：当前把 AMS 说成“核心实现”。在 android-16.0.0_r1 里，AMS 这里已经是 `mProcessStateController.runUpdate(...)` 的入口包装，真正的计算逻辑在 `OomAdjuster.updateOomAdjLSP()/computeOomAdjLSP()`。只给 AMS 会让读者顺源码时停在壳方法。
- **建议**：把源码锚点扩成 AMS 入口 + `OomAdjuster.java` 实际计算路径，至少补出委托关系。

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-13
- **类型**：源码准确性
- **位置**：L281-L284 共享内存（ashmem / memfd）
- **问题**：正文用 `GraphicBuffer` 作为 ashmem/memfd 例子，会把通用匿名共享内存和图形缓冲区分配路径混在一起。现代图形栈的 buffer 更接近 gralloc / dma-buf heaps 路径，而不是“GraphicBuffer 从 ashmem 迁到 memfd”。
- **建议**：把示例改成 `ASharedMemory` / 普通大块匿名共享内存；如果要讲图形缓冲区，单独说明 gralloc / dma-buf / HardwareBuffer 路径。

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-13
- **类型**：数据缺失
- **位置**：L395-L439 在 Perfetto 中的表现
- **问题**：本节已经给了通用 SQL，但还缺 1 个真实案例把“top-app→cached 降级”“lmkd kill”“am_crash”三类场景拆开。读者现在仍然缺少可复现的抓取配置、track 名称和截图锚点。
- **建议**：补 1 组真实 trace：同时打开 `android.log`、`linux.process_stats`、`linux.sys_stats`、`oom/oom_score_adj_update`，并给出一张截图 + 一条 SQL，分别说明 kill / crash / 仅降级三种判别信号。

## [Task9 Deep Review] 1.3 进程模型与生命周期管理 — 2026-04-13
- **类型**：交叉引用
- **位置**：frontmatter `related_chapters` + “与其他章节的关系”
- **问题**：正文大量讨论 LMK、后台限制和调度表现，但相关章节只列了 1.1/1.2/1.4/1.5，没有把已经修正了现代 lmkd 口径的 4.4《Low Memory Killer》、5.1《Linux 进程调度基础》、5.8《后台执行限制与优化》串起来。
- **建议**：把 4.4、5.1、5.8 补进 related_chapters 或正文“与其他章节的关系”，减少同一概念在不同章节里各说各话。


## [Task6 Review] 10.7 SQLite/Room 数据库性能优化 — 2026-04-13
- **类型**：需确认
- **位置**：1.1 WAL 模式段落（Compatibility WAL、ext4 4 倍写入收益）
- **问题**：Android 9 引入 Compatibility WAL、ext4 约 4 倍写入收益这两处结论都带有版本或量化断言，但当前 `[已验证]` 只落到 `SQLiteDatabase` 官方文档，证据链不够精确。
- **建议**：补充 `SQLiteCompatibilityWalFlags` / `enableWriteAheadLogging()` 的精确来源；如果拿不到可回溯数据，把 4 倍收益降级为定性表述。
- **review 日志**：logs/review/2026-04-13-07-review.md

- **类型**：需确认
- **位置**：2.4、3.3、6.2（Paging 3 / Keyset 分页）
- **问题**：正文多次把 "Paging 3 内部使用 Keyset 分页" 写成普遍结论，容易把 Paging 框架能力和具体 SQL 实现混在一起。
- **建议**：拆开说明 Paging 3 的分页框架与 Room 查询写法；确认是否真的基于 Keyset，再决定保留还是降级表述。
- **review 日志**：logs/review/2026-04-13-07-review.md

- **类型**：需确认
- **位置**：3.4 Migration 的性能风险
- **问题**："Migration 在主线程上执行"、"可用 Jetpack App Startup 在后台线程预执行" 这组说法牵涉 Room 打开时机和线程模型，当前没有给出源码或官方文档支撑。
- **建议**：补充 Room / `SQLiteOpenHelper` 的调用链依据；如果线程语义不能稳定复现，把这段改成条件化表述。
- **review 日志**：logs/review/2026-04-13-07-review.md

- **类型**：需确认
- **位置**：5.2、5.3（ContentProvider 死锁、Perfetto SQL）
- **问题**：`DatabaseConnectionPool`、`android_monitor_contention`、`android.monitor_contention` 这几处术语和表名混用，且正文没有给出对应 Android 版本或 Perfetto 证据。
- **建议**：核实 AOSP / Perfetto 中的真实类名、表名和适用版本，再决定保留哪一种写法。
- **review 日志**：logs/review/2026-04-13-07-review.md

- **类型**：需重写
- **位置**：6.2 最佳实践总结 + 扩展部分
- **问题**：结尾连续使用 checklist 式条目，和开头的 ANR 锁竞争场景没有回扣，收束偏平，活人感和章节记忆点不够。
- **建议**：等技术问题核实后，用一个真实排查场景或一条 Perfetto 观察路径把结尾收回来。
- **review 日志**：logs/review/2026-04-13-07-review.md

## [Task9 Deep Review] 3.2 触摸响应的性能分析 — 2026-04-13
- **类型**：数据缺失
- **位置**：L196
- **问题**："触摸采样率应该至少是渲染帧率的 2 倍" 被写成结论，但当前章节没有给设备、刷新率、交互类型或 trace 数据，且这个经验值不适用于所有场景。
- **建议**：降级为工程经验，并补充适用条件（滚动/绘图/游戏、60Hz/120Hz、是否启用 batching/resampling）。

- **类型**：数据缺失
- **位置**：L366
- **问题**：把 "deliverInputEvent → GPU Completion 超过 32ms" 直接判成渲染管线瓶颈，测量口径过粗。这个区间混合了输入排队、主线程逻辑、渲染、SurfaceFlinger 合成与 present。
- **建议**：改成“可疑信号”而不是直接定性，并补 FrameTimeline / INPUT_EVENT_ID / DISPLAY_PRESENT_TIME 的量化路径。

- **类型**：交叉引用
- **位置**：Motion Prediction 小节 / 与其他章节的关系
- **问题**：§3.2 单独展开了 Motion Prediction，但没有显式回链 §3.4，而且当前术语和版本口径已经与 §3.4 不一致，后续容易双写漂移。
- **建议**：在本节只保留摘要并明确回链 §3.4，统一使用“AndroidX MotionEventPredictor / platform MotionPredictor(API 34+)”口径。

