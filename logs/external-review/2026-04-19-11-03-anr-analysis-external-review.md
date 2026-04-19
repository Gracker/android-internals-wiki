# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch09-anr/`
- **候选章节**：
  1. `03-anr-analysis.md` | `status: ready-for-review`, `pipeline_stage: task9_pending`
- **最终选择**：`03-anr-analysis.md`
- **选择理由**：该章节是 ANR 专题的核心方法论篇，技术细节密集，且涉及大量 AOSP 源码锚点和跨版本行为，极需深度审计。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：严重遗漏了 Android 11+ 线上分析 ANR 的标准路径 `ApplicationExitInfo`；对 Android 16/17 的新特性描述停留于表面，缺乏实战指导意义；部分源码路径描述不够精确。
- **评分理由**：存在 2 个 P1 级知识缺失（ApplicationExitInfo、ProfilingManager 细节）及多个 P2 级源码准确性问题。
- **本轮 review 覆盖范围**：全文 review，重点核验了 AOSP 源码路径、线程状态含义、Android 14-17 版本演进、Perfetto 观察点。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 4/5 | 2 (P2) |
| 原理链完整性 | 3/5 | 1 (P1) |
| 版本差异覆盖 | 4/5 | 1 (P1) |
| 知识盲区 | 3/5 | 1 (P1) |
| 数据/案例支撑 | 4/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P1 问题（重要缺失）

- **[P1][原理链/知识盲区][线上分析流程] 遗漏现代线上 ANR 分析核心 API：ApplicationExitInfo**
  - **原文问题**：在“线上监控工具链”部分仅提到了 Watchdog 和 SIGQUIT 监听方案（XCrash等），完全未提及 `ApplicationExitInfo`。
  - **核验结论**：自 Android 11 起，由于 `/data/anr/` 权限收紧，`ApplicationExitInfo.getTraceInputStream()` 已成为生产环境获取系统级 ANR Trace 的唯一合规、标准路径。
  - **建议补充方向**：在“线上监控工具链”之后增加一个独立小节，讲解如何通过 `ActivityManager.getHistoricalProcessExitReasons()` 获取 `REASON_ANR` 的 `InputStream`，并对比其与三方 SIGQUIT 监听方案的优劣（系统截取 vs 自定义截取）。

- **[P1][版本差异][Android 16] ProfilingManager 触发机制描述过浅**
  - **原文问题**：仅提到“支持系统在检测到 ANR 时自动触发”，未说明开发者如何接入。
  - **源码锚点**：`android.os.ProfilingManager` (Android 15+) 及 `ProfilingTrigger.TRIGGER_TYPE_ANR` (Android 16+)。
  - **建议补充方向**：明确指出开发者需要通过 `addProfilingTriggers` 注册 `TRIGGER_TYPE_ANR` 类型的触发器，并强调这能捕捉到 ANR 发生“前”的历史 Trace，这是其核心价值。

## 五、P2 问题（建议改进）

- **[P2][源码准确性][CPU 使用率信息] ProcessCpuTracker 路径描述不严谨**
  - **原文位置**：CPU 使用率信息的解读部分。
  - **原文问题**：锚点指向了 `ActivityManagerService.java` 内部。
  - **核验结论**：`ProcessCpuTracker` 实际定义在 `com.android.internal.os.ProcessCpuTracker`。AMS 只是它的使用者。
  - **建议**：修正源码路径，并提及该类通过解析 `/proc/[pid]/stat` 和 `/proc/stat` 来获取数据。

- **[P2][源码准确性][线程状态] 状态含义补充**
  - **原文位置**：线程状态对照表。
  - **核验结论**：在 ART 源码 `art/runtime/thread_state.h` 中，`kNative` 状态非常关键，因为它代表线程不受 GC 挂起影响（Suspended=No）。
  - **建议**：在表中为 `Native` 状态增加注释：“不受 GC 挂起影响，可能在执行阻塞式 I/O 或系统调用”。

- **[P2][数据支撑][Perfetto] 缺少 Android 14+ 的 "ANR Trigger" 标记说明**
  - **核验结论**：Android 14+ 的 Perfetto Trace 在 `system_server` 的调度中会有明确的红色 "ANR Trigger" 视觉标记。
  - **建议**：在“在 Perfetto 中定位 ANR 时间窗口”部分补充该视觉特征的描述。

## 六、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|---|---|---|
| **AnrConsumer / AnrController** | 中 | Android 11+ 系统内部处理 ANR 的新链路（不再仅仅是直接写文件） |
| **Android 17 Lock-free MessageQueue** | 高 | Android 17 的无锁消息队列如何改变 `nativePollOnce` 的堆栈表现 |
| **Input ANR 5s 超时分档** | 中 | Android 15 对不同 Input 事件（点击 vs 手势）的超时判定差异 |

## 七、外部核验建议
- **搜索关键词**：`ProfilingTrigger.TRIGGER_TYPE_ANR` 使用示例
- **建议查阅**：`cs.android.com` 搜索 `ProfilingService` 在系统检测到 ANR 时的触发逻辑。
- **验证点**：`/proc/pressure/memory` 在 Android 13+ 是否有新的字段（如 `full` 之外的其他维度）。

## 八、可闭环输出

### 8.1 回炉问题单（必须修）
- **章节**：`src/part2-performance/ch09-anr/03-anr-analysis.md`
- **严重级别**：P1
- **问题类型**：原理断裂 / 知识缺失
- **位置**：## 线上 ANR 的分析流程与工具链
- **问题描述**：缺失 `ApplicationExitInfo` 这一现代 Android 核心 API。
- **建议修正方向**：增加“官方标准：ApplicationExitInfo”小节。

### 8.2 知识盲区清单
- **章节**：`src/part2-performance/ch09-anr/03-anr-analysis.md`
- **盲区描述**：Android 17 的 lock-free MessageQueue 对 ANR 分析的影响。
- **重要程度**：高
- **建议研究方向**：结合项目根目录的《Under the hood Android 17’s lock-free MessageQueue.md》进行交叉验证。

### 8.3 可复用知识资产
- **源码路径**：`art/runtime/thread_state.h`
- **关键结论**：`kNative` 状态的线程虽然在执行 Native 代码，但由于其不持有任何虚拟机内部锁（如 ThreadListLock），因此不会被 GC 暂停，这解释了为什么 GC 期间主线程若在 Native 阻塞仍会触发 ANR。
- **版本差异摘要**：Android 12+ `/data/anr/` 变为多文件带时间戳结构，权限收紧至仅 `adb bugreport` 或 `ApplicationExitInfo` 可访问。

## 九、下一候选章节
- `src/part2-performance/ch09-anr/04-special-anr-scenarios.md`（研究冻结、焦点丢失等特殊 ANR）

## 十、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-03-anr-analysis-external-review.md`
