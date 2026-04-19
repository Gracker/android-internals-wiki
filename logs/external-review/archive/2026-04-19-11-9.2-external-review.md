# AIW 自动 Review 任务报告 (2026-04-19)

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch09-anr/`
- **目标章节**：`src/part2-performance/ch09-anr/02-anr-types.md`
- **最终选择**：`02-anr-types.md`
- **选择理由**：该章节处于 `ready-for-review` 状态，且 `task9_state` 为 `pending`。ANR 类型与触发条件是性能优化的核心基础知识，其准确性直接影响后续所有 ANR 分析章节的质量。
- **排除原因**：无。

## 二、总体结论
- **总体技术评分**：2.5/5
- **是否建议回炉**：**是 (强制要求)**
- **主要风险**：文中多个核心阈值（特别是 FGS 启动超时）与 Android 14/15 真实行为存在显著偏差，且遗漏了 Android 14 引入的 `BroadcastQueueModernImpl` 对无序广播 ANR 行为的重大改变。
- **评分理由**：存在 P0 级别的事实错误（FGS 超时时间描述严重偏离 AOSP 现状）和 P1 级别的重大知识点缺失（Android 14 广播队列重构、ShortService 超时）。
- **闭环建议**：必须根据本报告提供的 AOSP 源码锚点和 Android 14+ 行为变更进行重修。
- **本轮 review 覆盖范围**：Input, Broadcast, Service, ContentProvider, FGS, ShortService, JobService。

## 三、六维评分
| 维度 | 评分 | 问题数 | 备注 |
|------|------|-------|------|
| 源码准确性 | 2.5/5 | 2 (P0) | FGS 超时、广播触发条件描述过时 |
| 原理链完整性 | 3.0/5 | 1 (P1) | 缺少 Android 14 广播队列重构逻辑 |
| 版本差异覆盖 | 2.0/5 | 2 (P1) | 遗漏 Android 14+ 关键变化 |
| 知识盲区 | 3.5/5 | 1 (P1) | ShortService 3min 超时未深入 |
| 数据/案例支撑 | 4.0/5 | 0 | 提供了 Logcat 样本，质量尚可 |
| 交叉引用一致性 | 5.0/5 | 0 | 引用链清晰 |

## 四、P0 问题（事实错误）

### 1. [P0][源码准确性][Service Timeout 章节]
- **原文位置**：`startForeground 的 5 秒超时` 小节
- **原文问题**：宣称 Service 必须在启动后 5 秒内调用 `startForeground()`。
- **源码锚点**：`com.android.server.am.ActivityManagerConstants.java` -> `DEFAULT_SERVICE_START_FOREGROUND_TIMEOUT_MS`
- **核查结论**：在 Android 14/15 AOSP 中，该基础超时已调整为 **30 秒**，另有 **10 秒** 的 ANR 缓冲延迟（`DEFAULT_SERVICE_START_FOREGROUND_ANR_DELAY_MS`），总计 **40 秒**。
- **为什么错**：原文引用了极早期版本（或某些 OEM 极度缩减版）的陈旧数据，严重误导开发者。
- **建议修正方向**：更新阈值为 30s+10s，并说明 Android 14+ 引入的 `ActivityManagerConstants` 动态配置机制。

### 2. [P0][源码准确性][BroadcastReceiver Timeout 章节]
- **原文位置**：`检测机制：BroadcastQueue 的超时 Handler`
- **原文问题**：宣称“只有有序广播（ordered broadcast）才会触发超时检测”。
- **源码锚点**：`com.android.server.am.BroadcastQueueModernImpl.java` (Android 14+)
- **核查结论**：从 Android 14 开始，默认启用的 `BroadcastQueueModernImpl` 对**所有**分发给进程的广播（包括无序/并行广播）都会启动 `AnrTimer` 监控。
- **为什么错**：未跟进 Android 14 广播系统的底层重构。现在的逻辑是“分进程队列监控”，而非单纯的“有序广播监控”。
- **建议修正方向**：明确区分旧版 `BroadcastQueueImpl` 和新版 `BroadcastQueueModernImpl` 的行为差异，强调 Android 14+ 下无序广播也会直接导致 "Broadcast of intent" ANR。

## 五、P1 问题（重要缺失）

### 1. [P1][知识盲区][版本演进中的变化]
- **原文问题**：对 Android 14+ 引入的 `shortService` 描述不够深入，未提及关键的 `onTimeout` 回调。
- **核查结论**：`shortService` 有严格的 **3 分钟** 硬性限制。
- **缺失内容**：
    1.  系统会回调 `Service.onTimeout`。
    2.  如果开发者不在 `onTimeout` 后的几秒钟宽限期内主动 `stopSelf()`，系统会**强制触发 ANR**，即使此时主线程并没有被阻塞。
- **建议补充方向**：补充 `shortService` 的“超时-回调-主动停止”链路，强调这是 Android 14+ 新增的“非阻塞型 ANR”典型案例。

### 2. [P1][源码准确性][Service Timeout 章节]
- **原文位置**：`检测机制：ActiveServices 的超时 Handler`
- **原文问题**：描述“如果进程本身还在启动（冷启动场景），进程启动时间也计算在内”不够精确。
- **核核结论**：在 `ActiveServices.realStartServiceLocked` 中，计时器是在 `app.thread.scheduleCreateService` 之前启动的。
- **运行原理说明**：计时器启动时，进程已经 attach 到 AMS，但尚未执行 `Application.onCreate`。因此，超时配额**包含 `Application.onCreate` 的执行时间**，但**不包含 fork 进程和 zygote 初始化**的耗时（那部分由进程启动超时监控）。
- **建议补充方向**：精准描述计时的起点是进程 attach 后。

## 六、P2 问题（建议改进）
- **[P2][数据支撑][Perfetto 表现]**：文中 [待补充] 部分需填充。建议提及在 Modern Queue 下，可以观察 `BroadcastProcessQueue` 的状态来分析无序广播的积压情况。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| BroadcastQueueModernImpl 的调度策略 | 高 | 研究广播折叠（Collapsing）如何影响超时判定 |
| shortService 在 OEM 上的差异 | 中 | 部分 OEM 可能对 3 分钟阈值有微调 |
| Android 15 FGS 累计运行限时 | 高 | 研究 `dataSync` 6 小时限制触发的不是 ANR 而是直接停止 |

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：`02-anr-types.md`
- **严重级别**：P0
- **位置**：FGS 启动超时小节
- **问题描述**：阈值描述为 5s，实际 AOSP Android 14+ 为 30s + 10s。
- **建议修正方向**：更新为 40s (30s+10s)，并引用 `ActivityManagerConstants`。

- **章节**：`02-anr-types.md`
- **严重级别**：P0
- **位置**：Broadcast 章节
- **问题描述**：宣称仅有序广播触发 ANR。
- **建议修正方向**：修正为 Android 14+ Modern Queue 下所有广播均受监控。

### 9.4 可复用知识资产
- **一手资料**：`com.android.server.am.BroadcastQueueModernImpl` 是 Android 14+ 性能分析的关键锚点。
- **关键路径**：`frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java` 定义了绝大多数 ANR 相关的动态阈值。
- **技术结论**：`shortService` 的 ANR 是由系统强制触发的（主动检测超时后抛出），与传统主线程卡死导致的 ANR 机制不同，属于“策略性 ANR”。

## 十、下一候选章节
- `src/part2-performance/ch09-anr/03-anr-analysis-pipeline.md`

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-02-anr-types-external-review.md`
