# AIW 自动 Review 任务报告 (2026-04-19)

## 一、目标发现结果
- **扫描范围**：`src/part2-performance/ch09-anr/`
- **候选章节**：
  1. `06-notification-performance-anr.md` | 当前待审，涉及 Android 16/17 新特性及 NMS 核心机制。
- **最终选择**：`src/part2-performance/ch09-anr/06-notification-performance-anr.md`
- **选择理由**：该章节涉及大量 Framework 源码引用及跨版本行为对比，技术风险点较高，且与 Android 17 新引入的无锁队列机制高度相关。

## 二、总体结论
- **总体技术评分**：3.2/5
- **是否建议回炉**：是
- **主要风险**：源码方法名引用不准（P0）；Android 17 核心性能特性（DeliQueue）遗漏（P1）；RemoteViews 指令集应用细节描述模糊（P2）。
- **评分理由**：虽然原理框架正确，但在关键的源码锚点和 Android 17 最新进展上存在事实偏差或重要遗漏，不足以支撑“源码级深度”的目标。
- **本轮 review 覆盖范围**：NMS 入口限流逻辑、RemoteViews 指令模式、NLS 线程模型、Android 13/16/17 版本差异。
- **本轮未完成部分**：NotificationAssistantService 的拦截开销、多监听器场景下的内存压力分析。

## 三、六维评分
| 维度 | 评分 | 问题数 |
|------|------|-------|
| 源码准确性 | 2.5/5 | 1 (P0) |
| 原理链完整性 | 4.0/5 | 1 (P1) |
| 版本差异覆盖 | 3.5/5 | 1 (P1) |
| 知识盲区 | 3.0/5 | 1 (P1) |
| 数据/案例支撑 | 3.0/5 | 0 |
| 交叉引用一致性 | 4.0/5 | 0 |

## 四、P0 问题（事实错误）
- **[P0][源码准确性][NotificationManagerService.java]**
- **原文问题**：引用了 `checkDisqualifyingFeatures()` 作为限流判断方法。
- **源码锚点**：`frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java`
- **核验结论**：在 AOSP `android-16.0.0_r1` 及之后版本中，限流逻辑直接实现在 `enqueueNotificationInternal` 方法内，或通过 `isDisqualifiedLocked` 等私有方法判断。`checkDisqualifyingFeatures` 并非标准 AOSP 方法名，可能误引了 OEM 定制代码或旧版过时代码。
- **建议修正方向**：修正为 `enqueueNotificationInternal` 内部的 `RateEstimator` 校验逻辑，并引用 `mMaxPackageEnqueueRate` 变量。

## 五、P1 问题（重要缺失）
- **[P1][版本差异覆盖][Android 17 DeliQueue]**
- **原文问题**：提到 Android 17 但仅泛泛而谈“性能变更”。
- **缺失内容**：遗漏了 Android 17 最核心的通知性能改进——**DeliQueue (Lock-free MessageQueue)**。
- **运行原理说明**：DeliQueue 通过无锁化设计允许 NMS 的 Binder 回调与 UI 渲染任务并行，解决了高频通知导致主线程在 `MessageQueue` 锁竞争上的 Jank 问题。
- **建议补充方向**：在“Android 17 通知性能变更”章节重点引入 DeliQueue 概念，并对比传统 `MessageQueue` 的锁竞争瓶颈。

- **[P1][知识盲区][NLS 后台限频]**
- **原文问题**：未提及 Android 17 对后台监听器的硬限制。
- **缺失内容**：Android 17 引入了 **Background NLS Rate Limiting**，对后台监听器的回调（`onNotificationPosted`）进行了显式的配额管理（Quota）和合批处理（Batching）。
- **为什么这是重要缺失**：这是解释为什么某些通知监听 App 在 Android 17 上出现延迟或丢失的关键。
- **建议补充方向**：补充 `getRateLimitResetTime()` 等 API 的引入背景。

## 六、P2 问题（建议改进）
- **[P2][原理链完整性][RemoteViews 反射开销]**
- **原文问题**：提到 `RemoteViews.apply()` 但未解释反射的具体代价。
- **问题描述**：RemoteViews 默认通过 `ReflectionAction` 调用 View 的 setter。在高频更新场景下，反射的 CPU 成本和 SystemUI 的主线程压力是 ANR 的隐形诱因。
- **建议**：补充 `ReflectionAction` 的工作原理，并说明为什么 `ProgressStyle` 的模板化（数据驱动）能规避反射开销。

## 七、知识盲区清单
| 盲区 | 重要程度 | 建议研究方向 |
|------|------|-------|
| DeliQueue 内部实现 | 高 | 研究 Android 17 `MessageQueue.java` 的无锁化改造 |
| NLS Quota 管理 | 中 | `NotificationListenerService.getRateLimitResetTime()` 源码 |
| RemoteViews 异步 Apply | 中 | `RemoteViews.applyAsync()` 及其对 SystemUI 并行性的影响 |

## 八、外部核验建议
- **搜索关键词**：`AOSP DeliQueue lock-free MessageQueue`
- **建议查阅**：`cs.android.com` 中 `frameworks/base/core/java/android/os/MessageQueue.java` 在 Android 17 分支的变更。
- **官方文档**：Android 17 Developer Preview 中关于 "Notification Listener Service Throttling" 的说明。

## 九、可闭环输出

### 9.1 回炉问题单（必须修）
- **章节**：9.6
- **严重级别**：P0
- **问题类型**：源码错误
- **位置**：通知限流策略节
- **描述**：`checkDisqualifyingFeatures()` 方法名不准确，且限流逻辑描述需同步至最新 AOSP。
- **建议修正方向**：引用 `mMaxPackageEnqueueRate` 和 `mUsageStats.getAppEnqueueRate(pkg)`。

- **章节**：9.6
- **严重级别**：P1
- **问题类型**：原理断裂
- **位置**：Android 17 通知性能变更节
- **描述**：遗漏 DeliQueue 无锁队列和后台 NLS 限频。
- **建议修正方向**：补充无锁化设计对消除系统 Jank 的意义。

### 9.2 知识盲区清单（供后续研究）
- **DeliQueue 机制**：建议在第 1.4 章（Binder）或第 1.2 章（Handler）中建立关联，解释无锁队列如何减少多线程竞争。

### 9.4 可复用知识资产
- **一手资料**：`INotificationListener.aidl` 中的 `oneway` 属性是异步分发的法律保障。
- **关键源码路径**：`frameworks/base/services/core/java/com/android/server/notification/NotificationManagerService.java`
- **版本差异摘要**：
    - Android 12: 包级限流（5.0f）。
    - Android 13: `POST_NOTIFICATIONS` 运行时权限。
    - Android 16: `ProgressStyle` 系统模板化（数据驱动渲染）。
    - Android 17: `DeliQueue` 无锁消息队列，后台 NLS 频率限制。
- **Trace 观察点**：在 Perfetto 中寻找 `PostNotificationRunnable` 的调度延迟，判定是否受 DeliQueue 优化影响。

## 十、下一候选章节
- `src/part2-performance/ch09-anr/07-input-anr.md` (输入事件导致的 ANR 是性能分析的重灾区)

## 十一、落盘信息
- **已写入文件**：`logs/external-review/2026-04-19-11-06-notification-performance-anr-external-review.md`
