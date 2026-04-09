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
