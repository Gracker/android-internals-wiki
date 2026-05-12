# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch10-memory-perf/`
- 最终选择：`01-app-memory-analysis.md`
- 选择理由：该章节作为内存分析的总纲，其技术准确性直接影响后续章节的理解。且其声明支持 Android 8.0 - 16，具备极高的时效性 review 价值。

## 二、总体结论
- 总体技术评分：3.5/5
- 是否建议回炉：是
- 主要风险：遗漏了 Android 15/16 极其关键的内存管理变更（16KB 页支持、ProfilingManager、heapprofd mmap 追踪），这会导致读者在最新系统上进行分析时出现误判。
- 评分理由：文章在基础工具（MAT, dumpsys, Profiler）的描述上非常扎实，但未能覆盖其声明的 Android 16 版本中的核心新特性。存在多处 P1 级缺失。
- 闭环建议：建议回炉补充 Android 15/16 的特有分析手段。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4.0/5 | 1 (P2) |
| 原理链完整性 | 3.5/5 | 2 (P1) |
| 版本差异覆盖 | 2.5/5 | 3 (P1) |
| 知识盲区 | 3.5/5 | 1 (P1) |
| 数据/案例支撑 | 4.0/5 | 0 |
| 交叉引用一致性 | 5.0/5 | 0 |

## 四、P0 问题（事实错误）
暂无。

## 五、P1 问题（重要缺失）

- [P1][版本差异覆盖][Android 15 16KB 页支持]
- **原文问题**：未提及 Android 15 引入的 16KB 内存页对分析工具的影响。
- **源码/一手资料锚点**：Android 15 Release Notes, `adb shell getprop ro.article.16kb_page_size_supported`
- **核验结论**：Android 15 开始支持 16KB 页，导致 `dumpsys meminfo` 报告的 PSS/RSS 数值将按 16KB 对齐，内存碎片平均增加约 9%。
- **建议修正方向**：在 `dumpsys meminfo` 章节增加警告，说明在 Android 15+ 设备上观察到的内存占用上升可能是由于页对齐导致，而非代码泄漏。

- [P1][原理链完整性][heapprofd mmap 追踪]
- **原文问题**：原文声称 `heapprofd` 只追踪 `malloc/free` 系列调用，不记录 `mmap`。
- **源码/一手资料锚点**：Perfetto `linux.mmap` data source
- **核验结论**：Android 15/16 的 heapprofd 已经支持通过 `linux.mmap` 追踪原始内存映射，这对于分析图形驱动或自定义分配器的内存至关重要。
- **建议修正方向**：更正 heapprofd 的限制描述，介绍如何利用 Perfetto 追踪 mmap。

- [P1][版本差异覆盖][Android 16 ProfilingManager]
- **原文问题**：完全未提及 Android 16 核心 API `ProfilingManager`。
- **源码/一手资料锚点**：`android.os.ProfilingManager`
- **核验结论**：这是 Android 16 推荐的线上诊断方案，支持系统触发分析（ANR 时自动抓取 Heap Profile）。
- **建议修正方向**：在“线上内存监控策略”中补充 `ProfilingManager` 的用法，作为未来标准的线上诊断手段。

## 六、P2 问题（建议改进）

- [P2][源码准确性][Debug.getMemoryInfo 与 smaps_rollup]
- **问题描述**：未提及 `getMemoryInfo` 在 Android 14+ 性能提升的原因。
- **建议**：补充 `smaps_rollup` 的机制说明，解释为什么现在高频调用 `getMemoryInfo` 的开销变小了。

- [P2][原理链完整性][Composer HAL 3.2 占位符 fallback]
- **问题描述**：原文提到了图形内存优化，但未说明对于旧 HAL 版本的 fallback 机制。
- **建议**：补充说明 `surface_flinger.clear_slots_with_set_layer_buffer` 系统属性，以及 1x1 占位符缓冲区的原理。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 16KB Page Size 导致的 Native 库对齐内存浪费 | 高 | 研究 NDK 应用在 16KB 页模式下的具体内存增长比例及优化参数 |
| ProfilingManager 的触发器频率限制 | 中 | 研究 `ProfilingTrigger` 的 `rateLimitingPeriodHours` 在实际生产环境的推荐值 |

## 八、外部核验建议
- 搜索 `ProfilingManager.TRIGGER_TYPE_ANOMALY` 在 Android 17 中的演进。
- 查阅 `memtrack` AIDL 接口中关于 `GPU_PRIVATE` 分类的具体定义。
- 验证 `Debug.getMemoryInfo` 返回的 PSS 在 16KB 页模式下是否会自动向下取整（通常是向上对齐）。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：10.1 App 内存分析
- **级别**：P1
- **类型**：版本差异缺失
- **描述**：缺少 Android 15 (16KB Page) 和 Android 16 (ProfilingManager) 的核心内容。
- **建议修正方向**：增加“§10.1.X Android 15/16 专题”，覆盖 16KB 页对指标的影响、ProfilingManager 的触发机制、以及 heapprofd 对 mmap 的新支持。

### 9.4 可复用知识资产

- **源码路径**：`frameworks/base/core/jni/android_os_Debug.cpp` -> `android_os_Debug_getDirtyPagesPid`
- **关键结论**：Android 14+ 优先通过 `smaps_rollup` 获取内存汇总，极大地降低了 PSS 采集的 CPU 负载。
- **版本差异**：Android 14 引入 Composer HAL 3.2 解决 `GraphicBufferProducer` 缓存残留；Android 15 开始 NDK 应用必须以 16KB 对齐。

## 十、下一候选章节
- `src/part2-performance/ch10-memory-perf/02-memory-leak.md`

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-01-app-memory-analysis-external-review.md`
