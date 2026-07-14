## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15
- **类型**：版本差异覆盖
- **位置**：游戏引擎 API 支持情况
- **问题**：未明确说明兼容的 Unity/Unreal 版本范围，特别是 Android 17 对这些引擎 API 的限制或增强
- **建议**：补充 Unity/Unreal 在 Android 17 中的兼容性说明，包括 API 版本要求和新特性支持

## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15
- **类型**：知识盲区
- **位置**：GPU 计算任务调度优化
- **问题**：未讨论 Android 17 中的 GPU 计算任务调度优化，包括 compute shader 分时调度和后台计算任务管理
- **建议**：补充 Android 17 GPU 计算任务调度的优化机制，说明其对 GPU 性能监控的新影响

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-15

### 建议 1：IFUNC 绕过方式描述不准确
- **类型**：交叉引用准确性
- **位置**：PLT Hook vs Inline Hook 的选择表中 IFUNC 绕过方式描述
- **问题**：正文描述与前轮 Task6 复审指出的 IFUNC resolver 机制不完全一致
- **建议**：更新 IFUNC 绕过方式的准确描述，强调 linker resolver 机制而非简单的绕过方式

### 建议 2：Hook 性能开销缺乏实测数据支撑
- **类型**：数据缺失
- **位置**：Hook 性能测量方法论章节
- **问题**：提供了方法论但缺乏具体设备的实测基准数据
- **建议**：补充典型设备上的 Hook 延迟测试数据（如 P50/P99 开销、不同架构的对比）

### 建议 3：Hook 框架内存管理策略缺失
- **类型**：知识盲区
- **位置**：Hook 技术的最佳实践章节
- **问题**：未讨论 Hook 框架自身的内存管理策略（Trampoline 池的分配/回收）
- **建议**：补充 ShadowHook 的 sh_hub_trampo_mgr 和 sh_island_trampo_mgr 内存管理机制说明

### 建议 4：Android 17 MEMTAG globals 对 RELRO 的影响描述不足
- **类型**：版本差异
- **位置**：16KB Page Size 对 Hook 的影响章节
- **问题**：Android 17 MEMTAG globals 对 RELRO 段的影响仅在补充说明中提及
- **建议**：详细说明 MEMTAG globals 如何改写 RELRO 段字节，以及这对 Hook 框架的影响

## [Task14 参考书扫描] ch04 内存管理 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：Bitmap 内存分配的完整演进路径（Android 3.0 Native → 7.0 Java 堆 → 8.0 NativeAllocationRegistry 回归 Native + Hardware Bitmap），AIW ch04 应包含此历史脉络以解释当前 Android 17 的 Bitmap 内存策略
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] ch04 内存管理 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：GC 性能测量方法（通过 SIGQUIT 信号获取 ANR 日志中的 GC 吞吐量/暂停时间/99% C.I. 数据），AIW ch04 可补充此线上 GC 监控手段
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch04 内存管理 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：Native 内存分析工具链演进（AddressSanitize Android 8.0+ 支持、Malloc 调试 backtrace、Malloc 钩子 Android P+），需标注 Android 17 当前可用的方案及 scudo 分配器的影响
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch04 内存管理 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 4.md]
- **建议补充**：内存优化两大误区论述——"内存越少越好"（应为动态弹性策略）和"Native 内存不用管"（LMK 依然杀进程），AIW ch04 可引用此观点作为实践指导
- **参考书覆盖深度**：概述

## [Task14 参考书扫描] ch02 渲染管线 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 41.md]
- **建议补充**：MediaCodec + OpenGL ES 视频处理管线（Camera NV21 → YUV 转换 → 硬编/软编 → MediaMuxer），以及 Surface 作为 MediaCodec InputSource 的 OpenGL 滤镜/美颜架构，AIW ch02 可补充视频渲染的特殊管线
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] ch06 存储性能 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 41.md]
- **建议补充**：MP4 moov atom 位置对边下边播性能的影响（moov 在尾部需完整下载才能解码），以及 ffmpeg -movflags faststart 方案，AIW ch06 存储/网络章节可参考
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch05 CPU/功耗 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 42.md]
- **建议补充**：ARM NEON SIMD 指令优化方法论（128Bit 寄存器并行计算，单条指令处理 4×Float32 或 16×Int8），AIW ch05 CPU 优化章节可补充 NEON 在非 ML 场景下的通用加速思路
- **参考书覆盖深度**：深入

## [Task14 参考书扫描] ch01 架构 — 2026-07-15
- **类型**：内容补充
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 43.md]
- **建议补充**：JVM TI ClassTransform/Redefine 接口（Android 8.0+ 支持），可作为 AIW ch01 运行时架构中"动态字节码编织"能力的权威补充，关联 Apply Changes 实现
- **参考书覆盖深度**：中等

## [Task14 参考书扫描] ch01 架构 — 2026-07-15
- **类型**：版本更新
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 43.md]
- **过时内容**：热修复方案 Tinker 基于 PathClassLoader 插入的方式，Android P 私有 API 限制后大量兼容性问题（43% 兼容性问题由热修复/插件化/加固造成）
- **建议更新至**：Android 17 AppComponentFactory API（Android Q 新增 instantiateClassloader 接口）为官方热修复路径；Android Q+ 使用 Play Core Library / Android App Bundles 替代传统插件化

## [Task14 参考书扫描] ch01 架构 — 2026-07-15
- **类型**：版本更新
- **来源**：[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 43.md]
- **过时内容**：插件化框架（Atlas、RePlugin、VirtualAPK）在 Android P 后面临私有 API 限制；Android Q 后动态加载 Dex 只用解释模式执行，加剧启动性能影响
- **建议更新至**：Android 17 应以 Android App Bundles + Play Core Library（或国内 Qigsaw 方案）为推荐路径，传统插件化回归模块化/组件化

## [Task2A R121] 知识缺口挖掘 — 2026-07-15 07:12
- **已检查方向**：source-index (306 entries, 88 high-q unmapped all traced)、research-feeds (112 files, newest 2026-04-14)、daily-info (2026-07-15 recycled)、Clippings (108 files)、research-gaps (3 entries)、AOSP service coverage、official docs
- **结果**：0 candidates >=14。121st consecutive。Coverage saturated (765 sections)。
- **避免重复**：下次探索方向应聚焦于①Android 17后续版本特性（但不得超出android-17.0.0_r1）②新兴Clippings素材（如有更新）③新的research-feeds（如有更新）
