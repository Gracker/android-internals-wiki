---
title: "Broadcast 性能与跨进程通信开销治理"
chapter: "8.21"
status: ready-for-review
drafted_date: "2026-07-17"
applicable_versions: "Android 14 (API 34) - Android 17 (API 37)"
last_verified: "2026-07-17"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/BroadcastReceiver.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/Context.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java"
tags: [broadcast, broadcast-receiver, ipc, ordered-broadcast, performance, goasync]
related_chapters: ["1.33", "9.02", "9.09", "9.11", "1.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "素材驱动"
---

# 8.21 Broadcast 性能与跨进程通信开销治理

## 要点

### 🔹 Broadcast 分发管线：ActivityManagerService → Binder → Receiver

广播是 Android 最常用的跨进程通信机制之一，但也是性能隐患最密集的 IPC 路径之一。一次 `sendBroadcast` 调用的实际开销远超开发者的直觉：

**投递链路的性能代价**：

1. **发送方 → system_server（Binder IPC）**：`Context.sendBroadcast` 通过 Binder 进入 AMS 的 `broadcastIntent` 方法。这一步是同步调用，但耗时通常 < 1ms（仅入队）。
2. **AMS 解析接收者（PackageManager 查询）**：对 implicit broadcast，AMS 需要通过 PackageManager 查询所有匹配的 receiver。查询复杂度随已安装应用数量和 IntentFilter 数量增长——在安装了 200+ 应用的设备上，单次查询可达 5-15ms。
3. **入队等待调度**：BroadcastRecord 进入 BroadcastQueue 后，需等待 `processNextBroadcastLocked` 轮询到该条目。前台队列调度快（通常 < 50ms），后台队列可能积压数秒。
4. **system_server → 接收进程（Binder IPC）**：通过 `IApplicationThread.scheduleRegisteredReceiver` 将广播投递到目标进程。每个 receiver 产生一次独立的 Binder 调用。
5. **接收进程内分发**：`ApplicationThread` → `ReceiverDispatcher` → 主线程 `MessageQueue` → `onReceive()`。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java — processNextBroadcastLocked 流程]

> BroadcastQueue 的调度机制（前台/后台队列分离、ModernImpl 进程级队列、优先级排序）详见 §1.33「BroadcastQueue 调度与广播性能」。

**性能关键指标**：

| 阶段 | 典型耗时 | 主要因素 |
|------|----------|----------|
| sendBroadcast 入队 | < 1ms | Binder oneway 调用 |
| PackageManager 查询 | 5-15ms（200+ 应用） | IntentFilter 匹配数量 |
| 队列等待 | 0ms（前台）- 数秒（后台） | 队列深度、调度优先级 |
| 进程拉起（如需） | 300-800ms | Zygote fork + Application 初始化 |
| Binder 投递到接收方 | 1-3ms | Binder 调用开销 |
| onReceive 执行 | 应用决定 | 业务逻辑耗时 |

### 🔹 有序广播（Ordered Broadcast）串行化延迟分析

有序广播是广播性能的主要"减速带"。其串行投递模型带来显著的延迟叠加效应：

**串行化机制**：

`sendOrderedBroadcast` 将所有接收者按 priority 排序，逐一投递。前一个 receiver 的 `onReceive` 执行完毕（或超时）后，才投递下一个。这意味着：

- N 个接收者的总延迟 = Σ(每个接收者的处理时间 + 投递 IPC 开销)
- 即使每个 receiver 只需 10ms，10 个 receiver 的总延迟也达 100ms+
- 如果中间某个 receiver 执行了同步 I/O 或 Binder 调用，整条链路被阻塞

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java — 有序广播的串行 deliverToReceiver 逻辑]

**Android 14+ ModernImpl 的改善**：

`BroadcastQueueModernImpl`（Android 16 起默认）通过 `BroadcastProcessQueue` 将有序广播的串行等待从全局级别改为进程级别：

- 不相关进程的并行广播不再被有序广播阻塞
- 同一进程内的有序广播仍按 priority 串行投递
- 但跨进程的有序广播链路仍然存在串行等待

[适用版本: Android 14 (API 34) 可选，Android 16 (API 36) 默认]

**性能建议**：

- 优先使用 `sendBroadcast`（无序），仅在需要结果传递或拦截时使用有序广播
- 如果必须用有序广播，将高 priority 分配给时间敏感的 receiver
- 避免在有序广播的 receiver 中执行耗时操作（会阻塞后续所有 receiver）

### 🔹 粘性广播（Sticky Broadcast）查找与内存开销

粘性广播已在 Android 5.0（API 21）废弃，但其性能影响在遗留代码中仍然存在：

**查找开销**：

发送粘性广播时，AMS 在 `broadcastIntentLocked` 中需要遍历已注册的 receiver 列表，检查是否与已存储的 sticky intent 匹配。每次 `sendStickyBroadcast` 都会：

1. 将 Intent 存储在 `mStickyBroadcasts` 列表中（按 userId 分组）
2. 立即向所有匹配的已注册 receiver 投递该广播
3. 后续新注册的 receiver（`registerReceiver`）需要与所有 sticky intent 匹配——O(N×M) 复杂度（N = sticky intent 数，M = 新 receiver 的 filter 数）

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java — sticky broadcast 存储与匹配逻辑]

**内存开销**：

每个 sticky broadcast 的 Intent 对象及其 extras 在 AMS 中常驻，直到被同 action 的广播覆盖或设备重启。在频繁使用 sticky broadcast 的应用中，可能累积数十个 Intent 对象。

**现代替代方案**：

| 场景 | 替代方案 | 性能优势 |
|------|----------|----------|
| 应用内状态广播 | `LiveData` / `StateFlow` | 无 IPC 开销，生命周期感知 |
| 跨进程状态共享 | `ContentProvider` + `ContentObserver` | 仅在数据变更时触发 |
| 持久化配置 | `DataStore` / `SharedPreferences` | 无 Binder 调用 |
| 电池状态等系统 sticky | 保持使用系统 API | 系统内部管理，无法替换 |

### 🔹 正常广播 vs 有序广播 vs 本地广播性能对比

| 维度 | 无序广播 | 有序广播 | 本地广播（已废弃） |
|------|----------|----------|---------------------|
| **投递方式** | 并行投递所有 receiver | 串行投递，逐个执行 | 同进程内分发，无 IPC |
| **IPC 次数** | N（每个 receiver 一次） | N + 调度开销 | 0 |
| **延迟特征** | 最后一个 receiver 的延迟 ≈ 队列等待 + 单次投递 | 最后一个 receiver 的延迟 = Σ 所有前序 receiver 处理时间 | < 1ms（直接回调） |
| **主线程影响** | 各 receiver 在各自进程主线程执行 | 串行阻塞，高 priority receiver 拖慢低 priority | 主线程同步执行 |
| **结果传递** | 无 | `getResultExtras` / `abortBroadcast` | 无 |
| **ANR 风险** | 每个 receiver 独立超时 | 链式超时，中间 receiver 卡住影响后续 | 无 ANR 风险 |
| **适用场景** | 事件通知（多数场景） | 需要优先级/拦截 | 已废弃，用 LiveData/Flow 替代 |

**性能选型决策树**：

```
需要跨进程通信？
├─ 否 → LiveData / Flow / 回调（无 IPC 开销）
├─ 是 → 需要结果传递或拦截？
│   ├─ 是 → sendOrderedBroadcast（注意串行延迟）
│   └─ 否 → 需要广播给未知数量的接收者？
│       ├─ 是 → sendBroadcast（无序，并行投递）
│       └─ 否 → AIDL / Messenger（点对点，更低开销）
```

### 🔹 BroadcastReceiver onReceive 执行时间预算与 ANR 边界

`onReceive` 在接收进程的主线程执行，这是广播性能模型中最关键的约束：

**超时阈值（Android 17）**：

| 广播类型 | 超时时间 | 触发条件 |
|----------|----------|----------|
| 前台广播 | 10 秒 | `BroadcastConstants.FG_TIMEOUT` |
| 后台广播 | 60 秒 | `BroadcastConstants.BG_TIMEOUT` |

[适用版本: Android 8 (API 26) - Android 17 (API 37)]

**实际安全预算远小于超时阈值**：

超时阈值是 ANR 触发线，不是性能目标。实际开发中应遵循更严格的预算：

| 广播类型 | ANR 阈值 | 推荐预算 | 原因 |
|----------|----------|----------|------|
| 前台广播 | 10s | < 200ms | 前台广播通常触发 UI 更新，> 200ms 影响用户感知 |
| 后台广播 | 60s | < 1s | 后台广播可能在低优先级进程执行，但 > 1s 影响后续广播调度 |

**goAsync() 的正确理解**：

`BroadcastReceiver.goAsync()` 并不增加超时预算——它只是允许将 `onReceive` 的工作转移到其他线程，但整个广播的超时窗口仍然从 `onReceive` 开始计时，到 `PendingResult.finish()` 被调用时结束。

```java
// 正确用法：goAsync + 后台线程 + 及时 finish
class MyReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pendingResult = goAsync()
        Thread {
            try {
                // 异步处理，但仍受广播超时约束
                doWork(intent)
            } finally {
                pendingResult.finish()  // 必须调用，否则触发 ANR
            }
        }.start()
    }
}
```

> 关于广播 ANR 的完整诊断方法，详见 §9.02「ANR 类型与触发条件」和 §9.09「ContentProvider ANR 双路径」。

### 🔹 Android 17 后台广播限制与性能影响

Android 14-17 对后台广播引入了多项限制，直接影响广播性能模型：

**1. 隐式广播清单限制（Android 8+，持续收紧）**

Android 8（API 26）起，大多数隐式广播无法通过 manifest 静态注册接收。Android 14-17 进一步收紧：

- 仅系统级隐式广播（如 `BOOT_COMPLETED`、`PACKAGE_REPLACED`）允许静态注册
- 应用级隐式广播必须通过运行时 `registerReceiver` 注册
- `RECEIVER_NOT_EXPORTED`（Android 14+ 强制）：系统跳过跨进程查询，仅投递同进程 receiver

[适用版本: Android 8 (API 26) 起逐步收紧，Android 14 (API 34) 强制导出声明]

**2. Cached App 广播延迟（Android 16-17）**

Android 17 对 cached 状态进程的广播投递做了延迟优化：

- 目标进程处于 cached（oom_adj ≥ CACHED_APP_MIN）时，非紧急广播不立即拉起进程
- 多个发往同一 cached 进程的广播在 `BroadcastProcessQueue` 中合并
- 被冻结（frozen）进程的广播投递挂起，解冻后才处理

这对广播发送方的意义：**不要依赖广播的实时投递来 cached 进程**。如果需要实时响应，使用 `FLAG_RECEIVER_FOREGROUND` 或改用 FGS + AIDL。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java — cached app delivery 延迟逻辑]

**3. 后台进程拉起限制（Android 14+）**

从后台广播启动 Activity 或 FGS 受到额外限制：

- `BAL`（Background Activity Launch）默认拒绝
- 通过广播启动 FGS 需要匹配的 FGS 类型声明
- 这些限制间接影响广播使用模式——不能再用广播作为"偷偷启动"的后门

> 详见 §5.17「Android 17 FGS 类型声明与后台执行性能边界」。

### 🔹 跨进程广播替代方案：Messenger / AIDL / ContentProvider

广播并非唯一甚至最佳的跨进程通信方式。在性能敏感场景下，应评估替代方案：

| 方案 | IPC 开销 | 延迟 | 适用场景 | 性能优势 |
|------|----------|------|----------|----------|
| **AIDL** | 1 次 Binder 调用 | < 1ms | 点对点 RPC | 无队列等待、无 PackageManager 查询 |
| **Messenger** | 1 次 Binder oneway | < 1ms | 单向消息传递 | 轻量、无需定义 AIDL 接口 |
| **ContentProvider** | 1 次 Binder 调用 | 1-3ms | 数据共享 + 变更通知 | 仅数据变更时触发，避免轮询 |
| **BroadcastReceiver** | 2 次 Binder + AMS 调度 | 5ms-数秒 | 一对多通知 | 解耦发送方和接收方 |
| **LiveData / Flow（同进程）** | 0 | < 1ms | 应用内状态分发 | 无 IPC 开销 |

**选型建议**：

- **一对一通信**：优先 AIDL。直接 Binder 调用，无队列等待，延迟 < 1ms
- **单向通知**：Messenger。Binder oneway 调用，发送方不阻塞
- **数据变更通知**：ContentProvider + ContentObserver。变更驱动，避免无效广播
- **一对多事件通知**：BroadcastReceiver（但评估是否真需要一对多）
- **应用内通信**：LiveData / StateFlow / SharedFlow。零 IPC 开销

> 详见 §1.17「IPC 全景：Android 进程间通信机制对比与性能选型」。

### 🔹 广播性能监控：goAsync 与 PendingResult 最佳实践

**线上广播监控的关键指标**：

| 指标 | 采集方法 | 告警阈值 |
|------|----------|----------|
| `onReceive` 执行耗时 | 主线程 Trace 插桩 | > 200ms（前台）/ > 1s（后台） |
| 广播调度延迟 | sendBroadcast → onReceive 时间差 | > 5s（后台队列） |
| goAsync 超时 | PendingResult.finish 未及时调用 | 接近广播超时阈值 |
| 广播 ANR 率 | 系统端 ANR 日志统计 | > 0.1% |

**goAsync 最佳实践**：

1. **始终在 finally 中调用 finish**：避免 ANR
2. **使用协程而非裸线程**：更可控的生命周期管理
3. **设置内部超时**：不依赖系统超时阈值，自行设置更短的工作超时

```kotlin
class MyAsyncReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pendingResult = goAsync()
        val scope = CoroutineScope(Dispatchers.IO)
        scope.launch {
            try {
                withTimeout(5_000) {  // 内部超时，远小于广播超时
                    handleIntent(intent)
                }
            } catch (e: Exception) {
                // 记录失败，但不阻塞 finish
            } finally {
                pendingResult.finish()
            }
        }
    }
}
```

**PendingResult 的性能陷阱**：

- `goAsync()` 持有的 `PendingResult` 会阻止系统回收该 receiver 的资源，直到 `finish()` 被调用
- 如果在 `goAsync` 中启动了长时间任务（如网络请求），整个广播超时窗口都在等待——系统无法调度下一个广播（有序广播场景）
- Android 14+ 的 ModernImpl 虽然将串行等待改为进程级，但同一进程内的下一个 receiver 仍被阻塞

## 扩展

### 🔸 系统广播性能影响（BOOT_COMPLETED, PACKAGE_*）

**BOOT_COMPLETED 广播风暴**：

设备启动时，`BOOT_COMPLETED` 广播会发往所有声明了该 action 的应用。在安装了 100+ 应用的设备上：

- 所有声明 receiver 的进程可能被拉起（每个 300-800ms）
- 总启动延迟增加可达数十秒
- Android 14+ 通过 UMS（Universal Migration System）和延迟广播缓解

**PACKAGE_* 广播**：

应用安装/卸载/更新时触发的广播（`PACKAGE_ADDED`、`PACKAGE_REPLACED`、`PACKAGE_CHANGED`）：

- Android 14+ 按进程合并：同一进程的多个 receiver 合并为一次 IPC
- Android 17 的 `BroadcastProcessQueue` 自动聚合同进程广播
- 但大型应用的 receiver 数量多，仍可能造成队列积压

**监控建议**：

在应用启动 Trace 中标记 `BOOT_COMPLETED` 的 `onReceive` 执行时间，作为冷启动性能的一部分。如果 > 100ms，考虑延迟初始化或使用 WorkManager 替代直接在 receiver 中执行。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java — package broadcast 合并逻辑]

### 🔸 广播队列拥塞诊断方法

**症状特征**：

- 广播投递延迟持续增大（> 10s）
- 多个广播在队列中积压
- 目标进程主线程频繁 ANR

**诊断工具链**：

**1. dumpsys activity broadcasts**

```bash
adb shell dumpsys activity broadcasts
```

输出包含：
- 当前队列状态（pending / active）
- 每个 BroadcastRecord 的状态、等待时间
- 队列深度和历史统计

**2. Perfetto Trace**

在 Perfetto 中关注：
- `BroadcastQueueModernImpl` 轨道：`processNextBroadcast` 耗时、队列状态变化
- `am_broadcast_discard_app` EventLog：被丢弃的广播（进程被杀等）
- 目标进程主线程：`onReceive` 执行耗时
- `am_proc_start`：因广播拉起的进程

**3. EventLog**

```
adb shell logcat -b events | grep "am_broadcast"
```

关键事件：
- `am_broadcast_discard_app`：接收进程被杀
- `am_broadcast_reschedule`：广播被重新调度
- `am_anr`：广播超时触发的 ANR

**4. 常见拥塞原因与解法**

| 原因 | 诊断方法 | 解法 |
|------|----------|------|
| 有序广播中间 receiver 卡住 | dumpsys 看当前活跃 BroadcastRecord 卡在哪个 receiver | 优化 receiver 处理逻辑，改用 goAsync |
| 后台队列积压 | dumpsys 看 background queue 深度 | 减少后台广播发送频率，改用 JobScheduler |
| 进程拉起延迟 | Perfetto 看 am_proc_start 到 attachApplication 耗时 | 避免对未运行进程发送非紧急广播 |
| PackageManager 查询慢 | Perfetto 看 broadcastIntentLocked 中 resolve 时间 | 使用 explicit intent，避免隐式查询 |

> 详细的广播性能 Perfetto 分析方法参见 §1.33 和 §13.10「Perfetto SQL 性能分析实战手册」。

---

**版本边界声明**：本节基于 AOSP `android-17.0.0_r1` 源码分析。`BroadcastQueueModernImpl` 自 Android 14 引入，Android 16 起为默认实现。广播投递的具体行为在 Android 14 以下设备（使用 Legacy `BroadcastQueueImpl`）存在差异。本节聚焦广播的性能开销和治理实践，BroadcastQueue 的内部调度机制详见 §1.33。
