# AIW 自动 Review 任务报告

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch09-anr/`
- **候选章节**：
  1. `07-non-technical-anr-diagnosis.md` | 本章节涉及大量 AOSP 底层机制，技术密度高，且处于 `ready-for-review` 状态。
- **最终选择**：`07-non-technical-anr-diagnosis.md`
- **选择理由**：该章节是 ANR 深度分析的进阶内容，涉及多处 AOSP 源码引用和版本差异（Android 14+），最能体现深度技术审计的价值。
- **排除的高频原因**：其他章节（如 9.1-9.3）多为基础概念或已完成初步 review。

## 二、总体结论
- **总体技术评分**：4.5/5
- **是否建议回炉**：否（建议在后续小修中补强部分 P1 缺失，无需大范围重写）
- **主要风险**：对 Android 14+ 引入的进程冻结（Freezer）与 ANR 耦合场景的描述略显单薄，可能导致读者在处理后台 ANR 时漏掉关键线索。
- **评分理由**：内容深度极佳，源码引用极度精准（准确匹配 Android 16 r1 的重构逻辑），推理链严密，是高质量的技术文档。
- **闭环建议**：直接进入结构化修正队列，补强 Freezer 机制和 Input 细分类型的解释。
- **本轮 review 覆盖范围**：全章核心知识点，包括超时预算、三层证据链、四类系统侧根因、工具边界及 InputTransport 案例。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 5/5 | 0 |
| 原理链完整性 | 4.5/5 | 1 |
| 版本差异覆盖 | 4.5/5 | 1 |
| 知识盲区 | 4/5 | 1 |
| 数据/案例支撑 | 5/5 | 0 |
| 交叉引用一致性 | 5/5 | 0 |

## 四、P0 问题（事实错误）
*未发现 P0 级别错误。*

## 五、P1 问题（重要缺失）

- **[P1][知识盲区][高发四类场景 - 3. Freezer 机制]**
  - **原文问题**：简单提到了 `am_freeze`，但未说明冻结状态如何导致“异步” ANR 误报。
  - **源码锚点**：`frameworks/base/services/core/java/com/android/server/am/CachedAppOptimizer.java`
  - **关键逻辑**：在 Android 13/14 中，如果进程在有待处理广播时被 Freezer 冻结，系统可能不会立即触发 ANR，而是在该进程下次尝试唤醒（如闹钟、JobScheduler）或强制分发超时后突发 ANR。
  - **建议补充方向**：说明在 Perfetto 中如何通过 `thread_state` 为 `Sleeping` 且伴随 `am_freeze` 事件来识别“被冻结导致的冤假错案”。

- **[P1][原理链完整性][第一步 - Input ANR 入口]**
  - **原文问题**：未细分 Input ANR 的两类核心原因及其对应的系统内部状态。
  - **源码锚点**：`frameworks/native/services/inputflinger/dispatcher/InputDispatcher.cpp` 中的 `isWindowReadyForMoreInputLocked`。
  - **关键逻辑**：`(server) is not responding`（窗口已拿走事件但没回 ack）与 `no focused window`（焦点切换或窗口未准备好接收事件）是两种截然不同的机制，前者通常涉及 App 侧阻塞，后者几乎纯属系统侧调度或状态同步问题。
  - **建议补充方向**：在 Input ANR 表格中补充这两类 Subject 的差异。

## 六、P2 问题（建议改进）

- **[P2][工具边界][Android 12-17 表格]**
  - **问题描述**：表格中提到“不要默认假设 `/proc/binder/stats` 在量产机可读”，建议更具体地指出 `binderfs` 的普及使得传统路径失效。
  - **建议**：补充 `adb shell ls -R /sys/kernel/debug/binder` 或 `binderfs` 节点的当前形态描述。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| 进程冻结（Freezer）与广播 ANR 的竞态 | 高 | 研究 `CachedAppOptimizer` 对 ANR 计时的暂停/继续逻辑 |
| InputDispatcher 焦点等待机制 | 中 | 研究 `mNoFocusedWindowTimeout` 常量与焦点窗口查找逻辑 |
| Android 14+ 广播超时动态倍增的阈值细节 | 中 | `BroadcastConstants` 中关于 `isCpuStarved` 的判断阈值 |

## 八、外部核验建议
- **搜索关键词**：`Android 14 BroadcastQueueModernImpl CPU starved extension`
- **建议查阅**：`cs.android.com` 下的 `BroadcastQueueModernImpl.java` 确认 `extendTimeout` 的具体实现。
- **搜索关键词**：`InputDispatcher::processAnrsLocked returning nextAnrCheck`
- **建议查阅**：Android 16 源码确认 native 层的 ANR 检查频率。

## 九、可闭环输出

### 9.1 回炉问题单（建议修）
- **章节**：9.7
- **严重级别**：P1
- **问题类型**：原理断裂/知识盲区
- **位置**：高发四类场景 - 3. Freezer 机制
- **问题描述**：缺乏对被冻结进程在“解冻瞬间”触发延迟 ANR 现象的描述。
- **建议修正方向**：引用 `am_freeze` / `am_unfreeze` 日志，并说明在 Perfetto 中识别该场景的方法。

### 9.2 知识盲区清单（供后续研究）
- **章节**：9.7
- **盲区描述**：Android 15+ 可能引入的针对 `binderfs` 的更严苛权限限制对 ANR 分析的影响。
- **建议研究方向**：调研新版本 `logd` 和 `dumpstate` 如何在没有 root 权限时导出 Binder 状态。

### 9.3 一般建议清单（非阻断）
- **建议**：在表格中明确区分 `am_anr` 里的 `subject` 和 `reason` 字段，方便新手对齐日志。

### 9.4 可复用知识资产（高价值新增知识）
- **一手资料**：`https://android-review.googlesource.com/c/platform/frameworks/native/+/396876`
- **关键源码路径**：`frameworks/native/libs/input/InputTransport.cpp`
- **关键调用链**：`InputConsumer::sendFinishedSignal` -> `mSeqChains` 维护逻辑。
- **技术结论**：确认了即使客户端发送 ACK 失败，通过 `seqChain` 的重构机制也能防止虚假 ANR，这一机制在 Android 系统底层极其稳定。
- **Trace 观察点**：在 Perfetto 中观察 `InputConsumer` 的 slice，如果频繁出现 `sendFinishedSignal` 失败且伴随 `mSeqChains.push`，说明 Socket 压力大。

## 十、下一候选章节
- `src/part2-performance/ch09-anr/08-anr-watcher-and-reporting.md`（如有）或返回 `metadata/queue.json` 检查其他 `task9_pending` 章节。

## 十一、落盘信息
- **已写入文件**：`logs/external-review/2026-04-19-11-07-non-technical-anr-diagnosis-external-review.md`
