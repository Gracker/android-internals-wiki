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
