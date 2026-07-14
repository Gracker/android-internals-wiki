## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-15

- **类型**：源码准确性
- **位置**：`art/runtime/entrypoints/entrypoint_utils.h` 路径引用
- **问题**：该路径在 android-17.0.0_r1 中不存在，Task6 第8轮复审已指出但源码路径未更新
- **建议**：删除不存在的路径引用或替换为实际存在的路径，例如 `art/runtime/art_method.h` 中对应的 ArtMethod 入口点字段

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-15

- **类型**：版本差异覆盖
- **位置**：16KB Page Size 对齐计算节
- **问题**：正确覆盖了Android 16+的16KB page size影响，但对Android 17特有的backcompat模式说明不足
- **建议**：补充Android 17的backcompat机制说明，包括system property控制(`bionic.linker.16kb.app_compat.enabled`)和警告提示信息

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-15

- **类型**：版本差异覆盖
- **位置**：Mainline模块影响节
- **问题**：正确覆盖了路径变化，但对Android 17 ProfilingManager新增触发器类型(OOM=7、ANOMALY=8)的Hook影响分析不足
- **建议**：补充Android 17新增触发器类型对Hook工具的影响分析，特别是与自建Hook工具的插桩目标重叠风险

## [Task9 Deep Review] 14.13 Hook 基础设施与性能工具实现原理 — 2026-07-15

- **类型**：知识盲区
- **位置**：Hook技术在Android 17 SELinux政策收紧后的适配
- **问题**：缺少Android 17 bionic linker中RTLD_LAZY移除对PLT Hook时机窗口的影响分析
- **建议**：补充`bionic/linker/linker.cpp::soinfo::prelink_image()`中关于`DT_PLTGOT`和`R_GENERIC_JUMP_SLOT`处理的变化说明，以及这对PLT Hook工具的影响

## [Task6 抽检] 26.18 App Performance Score 与性能质量评分归因 — 2026-07-15
- **类型**：需确认
- **位置**：正文第3段（outline-end后第2段）
- **问题**：两处断裂交叉引用，原文 `…理解；、分别提供了启动与渲染问题的测量顺序；、提供了灰度验证和上报组件的组织方式。` 章节号丢失
- **建议**：确认引用指向（疑 26.3 和 26.15），补全章节号
- **review 日志**：logs/review/2026-07-15-03-audit.md

## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15

- **类型**：源码准确性
- **位置**：GraphicBuffer 分配与 GPU 内存生命周期
- **问题**：`frameworks/native/libs/ui/GraphicBuffer.cpp` 的 `initSize()` 方法不直接调用 `GraphicBufferAllocator::allocate()`，实际调用链为 `initSize() → GraphicBufferAllocator::alloc()`（不是 `allocate()`）
- **建议**：修正为正确的 `alloc()` 方法名

## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15

- **类型**：原理链完整性
- **位置**：GraphicBuffer 分配与 GPU 内存生命周期
- **问题**：GPU 内存泄漏检测原理链不完整，缺少对 BufferQueue buffer 回收时机的解释和 GraphicBuffer pool 机制的影响分析
- **建议**：补充 BufferQueue buffer 回收策略和 GPU memory pool 的影响说明

## [Task9 Deep Review] 13.25 源码调研：PerfDog 的 Android 平台 GPU/性能采集底层数据源 — 2026-07-15

- **类型**：数据与案例支撑
- **位置**：GPU 性能问题定位实战
- **问题**：缺少具体的 GPU 性能基准数据，缺少不同 GPU 架构（Adreno vs Mali）的性能对比数据和内存带宽瓶颈的具体阈值
- **建议**：补充主流 GPU 的性能基准数据，包括不同架构的性能对比和具体阈值
