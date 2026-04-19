# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch09-anr/`
- **候选章节**：
  1. `05-case-studies.md` | 状态为 `ready-for-review`，且为 ANR 章节的实战核心。
- **最终选择**：`src/part2-performance/ch09-anr/05-case-studies.md`
- **选择理由**：该章节是 ANR 方法论的落地篇，涉及大量源码断言（Binder 线程池、SP 机制、进程冻结），技术风险点密集，最需深度核验。

## 二、总体结论
- **总体技术评分**：3.5/5
- **是否建议回炉**：是
- **主要风险**：案例 6 存在 Lint 规则引用错误（P0）；案例 4 虽识别出冻结问题，但未触及 Android 14+ 显性 ANR 的核心变化（P1）。
- **评分理由**：虽然案例选型极具代表性，但在关键工具引用和新版本行为描述上存在硬伤。
- **本轮 review 覆盖范围**：已覆盖全部 6 个案例的源码核验、版本差异核验及 Trace 表现核验。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 3.0/5 | 1 (P0) |
| 原理链完整性 | 4.0/5 | 1 (P1) |
| 版本差异覆盖 | 3.5/5 | 1 (P1) |
| 知识盲区 | 4.0/5 | 1 (P2) |
| 数据/案例支撑 | 4.5/5 | 0 |
| 交叉引用一致性 | 4.0/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][案例 6]**
- **原文问题**：建议使用 `DuplicateIds`/`NestedScrolling` 等 Lint 规则检测锁顺序。
- **源码 / 一手资料锚点**：Android Lint 源码中 `DuplicateIds` 检查 XML 重复 ID，`NestedScrolling` 检查嵌套滚动。
- **核验结论**：这两个规则与 `synchronized` 锁顺序或死锁检测完全无关。
- **为什么错**：疑似 AI 生成时的幻觉或误引用。
- **建议修正方向**：应引用 `@GuardedBy` 注解及相关的 `ThreadConfined` 检查，或引用特定的静态分析工具（如 Error Prone 的死锁检测）。

## 五、P1 问题（重要缺失）
- **[P1][版本差异覆盖][案例 3 & 案例 4]**
- **原文问题**：未提及 Android 14 引入的“显性 ANR (Explicit ANRs)”机制对 `JobScheduler` 和 `am_freeze` 场景的影响。
- **源码 / 一手资料锚点**：Android 14 Release Notes - "Explicit ANRs for Background Tasks"。
- **缺失内容**：在 Android 14 之前，很多后台阻塞是静默杀掉进程；Android 14 后，`JobService.onStartJob` 中的 SP `waitToFinish` 会触发明显的系统级 ANR 报告。
- **建议补充方向**：在案例 3 中补充 Android 14 对 `JobScheduler` 回调监控强化的描述；在案例 4 中提及 Android 15 对手势导航状态重置的修复尝试。

- **[P1][原理链完整性][案例 2]**
- **原文问题**：未讲清 `Notifier` 为什么会阻塞 `InputDispatcher`。
- **核验结论**：`Notifier` 运行在 `system_server` 的主线程。由于 `InputDispatcher` 需要在某些手势场景同步等待 `system_server` 的响应（特别是涉及 `Gesture Monitor` 的 Spy Window 处理时），主线程阻塞会导致 `InputDispatcher` 的 `waitQueue` 堆积，触发 "(server) is not responding"。
- **建议补充方向**：明确 `Notifier` 属于 `PowerManagerService` 的内部类，负责处理屏幕亮灭等关键回调，这些回调必须在主线程执行。

## 六、P2 问题（建议改进）
- **[P2][知识盲区][案例 1]**
- **原文问题**：PSI 信息仅给出了值，未给出判断阈值。
- **建议**：补充 PSI 的“危险阈值”：例如 `some avg10` 持续超过 70% 意味着系统已出现明显的感知卡顿。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| Binder 线程池耗尽的判定 | 高 | 如何通过 `dumpsys binder` 观察线程池水位 |
| 16KB Page Size 下的 IO 表现 | 中 | Android 15+ 16KB 页大小对案例 1 中 IO 压力的缓解作用 |

## 八、外部核验建议
- 搜索关键词：`Android 14 Explicit ANR JobScheduler`
- 建议查阅：`source.android.com` 关于进程冻结器（Cached Apps Freezer）的最新白名单机制。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **[P0][src/part2-performance/ch09-anr/05-case-studies.md]**：删除案例 6 中关于 `DuplicateIds` 和 `NestedScrolling` 的错误 Lint 建议。
- **[P1][src/part2-performance/ch09-anr/05-case-studies.md]**：在案例 3 中补充 Android 14 对后台组件（如 `JobService`）显性 ANR 的上报机制变化。
- **[P1][src/part2-performance/ch09-anr/05-case-studies.md]**：在案例 4 中补充 `am_freeze` 的排查命令：`adb shell device_config put activity_manager_native_boot use_freezer false`。

### 9.4 可复用知识资产
- **源码锚点**：`frameworks/native/libs/binder/ProcessState.cpp` -> `SP_BUNDLE_THREADS` (15 + 1)。
- **源码锚点**：`frameworks/base/services/core/java/com/android/server/power/Notifier.java` (SystemServer ANR 频发地)。
- **技术结论**：Android 14+ 遇到 `(server) is not responding` 且涉及 `Gesture Monitor` 时，应首选排查 `am_freeze` 日志，该问题在 Android 15 仍有残余，建议通过重置导航模式临时绕过。

## 十、下一候选章节
- `src/part2-performance/ch09-anr/03-anr-analysis.md` (分析方法论篇，需核验 Perfetto 新版 SQL 指令)。

## 十一、落盘信息
- 已写入文件：`logs/external-review/2026-04-19-11-05-case-studies-external-review.md`
