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