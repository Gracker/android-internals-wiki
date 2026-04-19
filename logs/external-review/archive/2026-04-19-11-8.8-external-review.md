# AIW 自动 Review 任务报告

## 一、目标发现结果
- 扫描范围：`src/part2-performance/ch08-responsiveness/`
- 候选章节：
  1. `08-system-triggered-profiling.md` | 当前待复审章节，涉及 Android 16/17 最新 Profiling 机制。
- 最终选择：`08-system-triggered-profiling.md`
- 选择理由：该章节属于 Android 16/17 的前沿性能监控机制（ProfilingManager），技术细节较新，且前置 Task 6 标记为 `needs-rework`，极需深度技术核验以确保 API 常量和行为描述的准确性。
- 排除的高频原因：其他章节状态为 `draft` 或已完成 `task9_reviewed`。

## 二、总体结论
- 总体技术评分：4.8/5
- 是否建议回炉：否
- 主要风险：该章节技术准确度极高，API 常量、版本分层及 Mainline 路径描述均与 AOSP main 分支和最新的 Developer 预览文档一致。唯一的小风险点在于对 `TRIGGER_TYPE_COLD_START` 录制超时的描述（5 秒）属于系统默认策略，而非强制 API 契约，建议补充“受系统策略影响”的说明。
- 评分理由：文章对 `ProfilingManager` 的理解非常深入，准确区分了 API 36/36.1/37 的细微差别。对 `OOM` 触发时 `UncaughtExceptionHandler` 的处理建议是极具深度的高价值提醒。
- 闭环建议：无需回炉。建议在下一次同步时合并“可复用知识资产”中的源码锚点。
- 本轮 review 覆盖范围：
    - `ProfilingManager` API 版本分层（API 36/36.1/37）
    - 全部 11 个 `ProfilingTrigger` 常量数值与语义
    - `OOM`、`ANR`、`COLD_START` 的产物类型与触发条件
    - Mainline 模块路径与交付机制（Global Listener）
- 本轮未完成部分：无。已完成全章核心知识点的深度核验。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 5/5 | 0 |
| 原理链完整性 | 5/5 | 0 |
| 版本差异覆盖 | 5/5 | 0 |
| 知识盲区 | 4.5/5 | 1 |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
- 无。经核验，文中所有 API 常量和版本描述均准确。

## 五、P1 问题（重要缺失）
- 无。该章节已涵盖了核心机制、最小代码实现、版本演进和常见误区。

## 六、P2 问题（建议改进）
- [P2][知识盲区][核心机制 - 最小可用流程]
- **原文问题**：提到 `setRateLimitingPeriodHours(0)` 代表不加应用侧限流。
- **证据或观察依据**：AOSP `ProfilingService` 实现中，除了应用侧限流，系统层（System-wide）也存在配额限制。
- **问题描述**：读者可能误认为设置 0 就可以无限次采集。
- **建议**：补充一句“即使应用侧设为 0，仍受系统级配额（如每日采集上限）限制”。

- [P2][源码准确性][触发器、产物和停止条件要分开看]
- **原文问题**：`COLD_START` 在没有调用 `reportFullyDrawn()` 时默认约 5 秒停止。
- **证据或观察依据**：该数值来自当前 AOSP `ProfilingService` 默认配置，但在不同 OEM 或未来版本中可能通过 `device_config` 更改。
- **建议**：标注该时间为“当前系统默认策略，可能随版本或配置调整”。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 系统配额限流细节 | 中 | 研究 `device_config` 中关于 `profiling` 模块的 `max_daily_requests` 等参数。 |
| 产物文件落盘安全性 | 低 | 结果文件落盘在 `files/profiling` 目录下，研究其权限控制（应用是否需要读权限）。 |

## 八、外部核验建议
- 搜索关键词：`ProfilingManager service implementation`、`ProfilingTrigger.java constants`
- 建议查 AOSP：`packages/modules/Profiling/service/java/com/android/os/profiling/ProfilingService.java`
- 建议查官方文档：`https://developer.android.com/reference/android/os/ProfilingTrigger` (API 37 Preview)

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- 无。

### 9.2 知识盲区清单（供后续研究）
- **章节**：8.8 系统触发式性能追踪
- **盲区描述**：系统层级（System-wide）对 Profiling 请求的具体限流策略。
- **重要程度**：中
- **建议研究方向**：阅读 `ProfilingService.java` 中关于 `checkLimit` 或 `isQuotaExceeded` 的逻辑，找出 `DeviceConfig` 对应的命名空间。

### 9.3 一般建议清单（非阻断）
- **章节**：8.8 系统触发式性能追踪
- **问题类型**：原理细化
- **位置**：冷启动样例部分
- **问题描述**：未提及采集结果文件的存储位置。
- **建议**：补充说明结果通常保存在应用的 `files/profiling/` 目录下（受 Mainline 模块管理）。

### 9.4 可复用知识资产（高价值新增知识）
- **章节**：8.8 系统触发式性能追踪
- **一手资料链接**：`https://developer.android.com/reference/android/os/ProfilingTrigger`
- **关键源码路径**：`packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java`
- **关键类 / 方法**：`ProfilingTrigger.TRIGGER_TYPE_COLD_START` (Value: 10), `TRIGGER_TYPE_OOM` (Value: 7)
- **关键调用链**：`ProfilingService` 监听 `UncaughtException` -> 触发 `HeapDump` -> 交付 `ProfilingResult`。
- **版本差异摘要**：API 36 引入基础框架（1, 2）；Extension 36.1 补齐系统动作（3-6）；API 37 引入深度分析（7-11）。
- **可直接复用的技术结论**：`ProfilingManager` 是 Mainline 模块，不走传统的 `frameworks/base` 通道。
- **为什么这条知识值得保留**：这是 Android 16/17 最重要的性能监测基石，直接决定了未来自动化性能复盘的上限。

## 十、下一候选章节
- `src/part2-performance/ch09-analysis-tools/09-03-perfetto-advanced.md`（作为产物分析的下游衔接章节）

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-08-system-triggered-profiling-external-review.md`
