## [Task9 Deep Review] 19.24 崩溃与 ANR 捕获机制 — 2026-07-15
- **类型**：知识盲区
- **位置**：§13.5 信号处理器的 async-signal-safe 限制边界
- **问题**：信号处理器的 async-signal-safe 限制边界没有明确列举禁用函数清单，缺少常见误用案例
- **建议**：补充 async-signal-safe 函数清单和常见误用案例，如 malloc、free、printf、fprintf、pthread_mutex_lock、sem_wait 等函数在信号处理器中的使用风险

## [Task9 Deep Review] 26.18 App Performance Score 与性能质量评分归因 — 2026-07-15
- **类型**：知识盲区
- **位置**：第7章"常见误用边界"
- **问题**：缺少对 App Performance Score 与 Vitals 口径不匹配场景的讨论，未说明如何处理交叉验证矛盾
- **建议**：补充当 App Performance Score 与 Android Vitals 口径不匹配时的处理流程，包括数据源差异、窗口期差异、设备覆盖差异的识别与协调方案

## [Task9 Deep Review] 19.24 崩溃与 ANR 捕获机制 — 2026-07-15
- **类型**：源码准确性
- **位置**：§13.1 交叉引用
- **问题**：§13.1 中提到的关联章节（§26.5、§26.2）在当前章节结构中不存在
- **建议**：确认章节号是否正确，或更新为实际存在的相关章节

## [Task9 Deep Review] 19.24 崩溃与 ANR 捕获机制 — 2026-07-15
- **类型**：数据缺失
- **位置**：GWP-ASan 灰度检测方案
- **问题**：缺少具体的线上应用效果数据
- **建议**：补充实际生产环境中 GWP-ASan 的应用效果数据，包括检测率、性能影响等量化指标

## [Task9 Deep Review] 26.18 App Performance Score 与性能质量评分归因 — 2026-07-15
- **类型**：数据缺失
- **位置**：性能提升数据引用
- **问题**：App Performance Score 的性能提升数据（如"30%性能提升"）缺乏具体测试条件和样本支撑
- **建议**：补充具体的测试条件、设备型号、样本数量等支撑数据

## [Task9 Deep Review] 26.18 App Performance Score 与性能质量评分归因 — 2026-07-15
- **类型**：数据缺失
- **位置**：低端机测试标准
- **问题**："最小要求"描述过于宽泛，缺少具体的量化指标
- **建议**：补充具体的量化指标，如内存阈值、存储空间要求、具体设备型号等
## [Task9 Deep Review] 19.24 崩溃与 ANR 捕获机制 — 2026-07-15
- **类型**：源码准确性 / 版本差异 / 知识盲区 / 数据支撑
- **位置**：§13.3 / §13.4 / §4.x / §12.5
- **问题**：
  1. §13.3 引入 "API 36.1" 概念分组（TRIGGER_TYPE_APP_REQUEST_RUNNING_TRACE / TRIGGER_TYPE_KILL_*），但 AOSP/SDK 中 API level 通常为整数，不存在标准 "API 36.1"。建议核实 android-17.0.0_r1 中 ProfilingTrigger.java 实际常量定义，确认是否系 SDK extension 命名误用，或合并到 API 36 / API 37 两层。
  2. §13.4 版本表 "Android 16-17 (API 36-37)" 一行粒度粗于 §13.3，建议同步为三层。
  3. §4 缺 ANR 阈值链路：输入事件 5s / 广播 10s / 前台服务 20s / ContentProvider 10s 与 AnrManager 触发链路未展开。
  4. StrictMode ANR 检测路径（disk read / network on main thread）与 APM 主动检测 ANR 紧密相关，建议补充。
  5. §12.5 KOOM fork-dump "冻结时间 < 20ms" 量化数据来源未在 frontmatter sources 中列出。
- **建议**：补充或修订对应子节，并在 frontmatter sources 增加 KOOM 官方文档/白皮书链接。
