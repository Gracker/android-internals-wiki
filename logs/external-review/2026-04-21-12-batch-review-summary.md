# AIW 批量 Review 总结报告 (第 15 章: 方法论)

## 一、本次批量 Review 范围
本次对 `src/part3-tools/ch15-methodology/` 目录下的 8 篇文章进行了全量逐篇 Review。

覆盖章节：
- `01-philosophy.md`
- `02-system-vs-app.md`
- `03-metrics.md`
- `04-competitive-analysis.md`
- `05-online-monitoring.md`
- `06-testing-best-practices.md`
- `07-aosp-reading.md`
- `08-empirical-performance-issues.md`

## 二、总体技术评价
- **总体结论**：第 15 章的总体质量极高，方法论总结得非常务实且贴近大规模工程化实战，大量引述了 AOSP、Perfetto、Android Vitals 等第一手工业界资料。
- **主要发现**：在 01 和 02 两篇中存在个别硬编码数值错误（如 API 引入版本、ANR 默认阈值）和一些已过时的 Hack 技巧；而 03 到 08 篇的技术准确度极高，尤其是指标阈值（如 Vitals 惩罚线）、工具限制（如 FPM 限额）等。
- **推荐动作**：01 和 04 需重点回炉修正底层原理错误；其他章节经过轻量修正后可直接发布。

## 三、高优回炉问题单合并汇总 (P0/P1)

### P0 (必须立刻修正的事实错误)
1. **`01-philosophy.md`**：
   - 将 ProfilingManager 错误地写成了 Android 8 引入，实际为 Android 15 (API 35) 引入。
   - 将 FrameMetrics API 错误地写成了 Android 11-13 引入，实际为 Android 7.0 (API 24) 引入。

### P1 (严重影响理解的缺失或错误)
1. **`01-philosophy.md`**：在讨论测试变量时，错误推荐了过时的 `always_finish_activities 1`，遗漏了 Macrobenchmark 最核心的 `CompilationMode`（AOT/JIT 对齐）机制。
2. **`02-system-vs-app.md`**：ANR 阈值表格中，将 `startForegroundService()` 的超时时限错写为 5 秒（AOSP 默认实为 10 秒）。
3. **`04-competitive-analysis.md`**：错误地将 `FrameMetrics.TOTAL_DURATION` 的起点定义为 `performTraversals()`（实际起点为预期 VSync 信号，包含了未在此刻执行前的卡顿延迟及 Input/Animation 耗时）。
4. **`06-testing-best-practices.md`**：在讨论 Benchmark 时，只覆盖了设备的“冷却峰值性能（Peak）”，遗漏了现代重载应用必须测量的“热稳定态性能（Steady-state）”。

## 四、核心知识盲区汇总
| 章节 | 盲区描述 | 重要程度 | 建议研究方向 |
|------|----------|----------|------------|
| `01-philosophy` | Macrobenchmark `CompilationMode` 控制变量的底层机制 | 高 | 研究 ART 在不同 CompilationMode 下的 JIT/AOT 行为表现。 |
| `06-testing-best-practices` | 稳态性能测试 (Steady-state Performance) | 高 | 明确区分微观峰值性能基准与宏观稳态性能基准的设计差异，尤其是持续负载下的掉帧表现。 |

## 五、一般建议汇总 (P2)
- **`01-philosophy.md`**：将“BlastBufferQueue 替代 BufferQueue”更准确地描述为“改变了事务提交模式（Producer 侧行为）”，因其底层跨进程流转仍基于 BufferQueue。
- **`03-metrics.md`**：Click-to-Display 的 100ms/200ms 阈值，建议引用业界成熟的 RAIL 模型以增强学术严谨性。
- **`06-testing-best-practices.md`**：在讲述固定 CPU 频率的 shell 命令时，建议补充 Jetpack Benchmark 内置的自动化 `LockClocks` 机制。
- **`08-empirical-performance-issues.md`**：进一步严谨化 `GlobalScope` 泄漏的条件（必须显式/隐式捕获外部 UI 生命周期引用）。

## 六、可复用知识资产提取 (高价值)
1. **指标阈值基线**：Android Vitals 2026 最新不良行为惩罚线（ANR ≥ 0.47%, Crash ≥ 1.09%），以及 24 小时持锁超过 2 小时的 Partial WakeLock 惩罚线。
2. **Trace 反向推导法**：Perfetto 中 Slice 名如果是 `ClassName::methodName` 必为 Native `ATRACE_CALL()` 宏生成；普通字符串则是 Java 层的 `Trace.traceBegin()` 或 Native 的 `ATRACE_NAME()`。这是顺藤摸瓜找 AOSP 源码的黄金法则。
3. **线上 ANR 监控迭代**：受限于 Android 10+ 权限与 SELinux，`FileObserver` 监听 `/data/anr` 彻底退场。现代标配是 API 30+ 走 `ApplicationExitInfo.getTraceInputStream()`，低版本用 Watchdog 轮询兜底。
4. **性能问题错位金字塔**：实证数据表明，性能优化优先级严重脱节——用户关心响应（62.3%），开发者死磕内存（80.6%），学术界水论文造能耗（81.18%）。工程排期应以此为戒。

## 七、落盘确认
所有单章节的 Review 报告均已成功生成在 `logs/external-review/` 目录下。本轮批量 Review 任务已完结。
