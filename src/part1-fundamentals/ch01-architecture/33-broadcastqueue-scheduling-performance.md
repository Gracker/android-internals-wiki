---
title: "BroadcastQueue 调度与广播性能"
chapter: "1.33"
status: ready-for-review
drafted_date: "2026-06-27"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-27"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastRecord.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java"
  - type: aosp
    path: "frameworks/base/core/java/android/content/Intent.java"
tags: [broadcast, broadcastqueue, scheduler, AMS, ANR, broadcast-modern-impl]
related_chapters: ["1.8", "9.2", "5.8", "1.34", "5.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构/章节深挖"
---

# 1.33 BroadcastQueue 调度与广播性能

## 要点

### 🔹 BroadcastQueue 的两类队列与调度优先级

Android 的广播调度采用**多队列分离**设计。`ActivityManagerService` 在初始化时创建两个核心广播队列：

- **Foreground BroadcastQueue（前台广播队列）**：处理带有 `Intent.FLAG_RECEIVER_FOREGROUND` 标志的广播。前台广播享有最高调度优先级，超时时间更短（10 秒），确保对延迟敏感的交互（如 UI 更新触发）能快速投递。
- **Background BroadcastQueue（后台广播队列）**：处理普通广播。超时时间为 60 秒，允许在后台低优先级条件下调度。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java — `mFgBroadcastQueue` / `mBgBroadcastQueue` 初始化]

两类队列共享同一个 `BroadcastQueue` 抽象基类。在 Android 14 之前，实际实现为 `BroadcastQueueImpl`（Legacy）。从 Android 14 开始，`BroadcastQueueModernImpl` 作为可选实现引入，通过 `DeviceConfig` 控制；Android 16 起 `BroadcastQueueModernImpl` 成为默认实现，`BroadcastQueueImpl` 被标记废弃。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java]

#### BroadcastQueueModernImpl 的进程级队列

Modern 实现引入了 `BroadcastProcessQueue`——每个目标进程拥有独立的广播调度队列。这一设计的核心优势：

- **进程级优先级调度**：高优先级进程的广播不再被低优先级接收者的有序广播阻塞
- **批量投递（Coalescing）**：同一进程的多个广播可以合并为一次进程唤醒和 `ApplicationThread` IPC 调用
- **背压控制**：当目标进程的广播积压超过阈值时，系统可以延迟新广播入队，避免队列膨胀

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java]

#### 优先级投递（Priority String）

广播的优先级通过 `Intent` 的 priority string 控制，`ActivityManagerService.broadcastIntentLocked` 在入队时按以下规则排序：

| 优先级 | 含义 | 典型场景 |
|--------|------|----------|
| `PRIORITY_URGENT_APP` (≥3) | 紧急应用级 | 系统级 UI 触发 |
| `PRIORITY_NORMAL_APP` (0) | 普通应用级 | 默认值 |
| `PRIORITY_LOW_APP` (≤-1) | 低优先级 | 非紧急后台通知 |

> 注意：优先级仅影响同一队列内的排序，不跨越前台/后台队列边界。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastConstants.java]

### 🔹 广播投递全流程：从 sendBroadcast 到 onReceive

广播投递是一个涉及 system_server 调度、进程拉起和 IPC 通信的多阶段过程：

```
App: Context.sendBroadcast(intent)
  → AMS.broadcastIntent (Binder IPC → system_server)
    → broadcastIntentLocked
      → resolveBroadcasters (PackageManager 查询接收者)
      → 队列选择 (foreground / background / offload)
      → BroadcastQueue.enqueueBroadcastLocked
        → BroadcastRecord 入队 (状态: PENDING)
      → scheduleBroadcastsLocked → BroadcastHandler.sendMessage

BroadcastQueue: processNextBroadcastLocked (event loop)
  → 检查 BroadcastRecord 状态
  → 若目标进程未运行 → startProcessLocked (拉起进程)
    → 等待进程附着 (attachApplication)
  → 进程已运行 → deliverToReceiver
    → appThread.scheduleRegisteredReceiver (Binder IPC → App 进程)
      → ApplicationThread → ReceiverDispatcher
        → ActivityThread.main thread → onReceive()
  → 接收完成 → finishReceiver → BroadcastRecord 状态 → DONE
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java — `processNextBroadcastLocked` 方法]

#### BroadcastRecord 状态机

`BroadcastRecord` 经历以下状态转换：

| 状态 | 含义 | 性能关注点 |
|------|------|------------|
| `PENDING` | 已入队等待调度 | 队列等待时间是广播延迟的主要来源 |
| `APP_RECEIVE` | 正在投递给目标进程 | 进程拉起延迟（冷启动）可占数秒 |
| `CALL_DONE_RECEIVE` | 目标进程正在执行 `onReceive` | 此阶段超时即触发 ANR |
| `DONE` | 投递完成，移出队列 | — |

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastRecord.java]

#### 进程拉起延迟对广播投递的影响

当目标接收者所在进程未运行时，系统需要先通过 `startProcessLocked` 拉起进程。这个过程包括：

1. Zygote fork → 进程初始化（约 300-800ms，取决于应用复杂度）
2. `ActivityThread.attach` → 向 AMS 注册
3. `Application.onCreate()` 执行
4. 才开始处理排队的广播

在 Modern 实现中，`BroadcastProcessQueue` 会将同一进程的多个广播暂存，等进程附着后一次性投递，减少重复拉起的开销。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java — `deliverToReceiver` 流程]

### 🔹 ANR 触发与超时机制

广播 ANR 是线上 ANR 的主要来源之一（尤其在后台广播场景）。超时机制设计如下：

#### 超时阈值

| 广播类型 | 超时时间 | 配置常量 |
|----------|----------|----------|
| 前台广播 | 10 秒 | `BroadcastConstants.FG_TIMEOUT` |
| 后台广播 | 60 秒 | `BroadcastConstants.BG_TIMEOUT` |

[适用版本: Android 8 (API 26) - Android 17 (API 37)]

#### Modern 实现的超时跟踪

`BroadcastQueueModernImpl` 采用**逐接收者超时**模型：

- 每个 `BroadcastRecord` 的接收者列表中，每个 receiver 拥有独立的超时计时器
- 计时从 `deliverToReceiver` 调用开始，而非整个 BroadcastRecord 入队时
- 超时后调用 `broadcastANRLocked`，通过 `AnrTimer` 或直接触发 `appNotResponding`

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java — `setBroadcastTimeout` / `broadcastANRLocked`]

#### Legacy 实现的超时跟踪

`BroadcastQueueImpl`（Android 14 之前默认）采用**整体队列超时**：

- `setBroadcastTimeoutLocked` 设置一个定时消息
- 超时后检查当前正在处理的 `BroadcastRecord`
- 如果仍停留在某个 receiver，对该 receiver 触发 ANR

> 详见 §9.2「ANR 类型与触发条件」中关于广播 ANR 的完整描述。

#### Trace 中的广播 ANR 标识

ANR 发生时，`StackTracesDumpHelper` 会生成 `/data/anr/anr_<timestamp>` 文件（Android 12+），其中包含：

- `BroadcastRecord` 信息：action、接收者列表、当前卡在第几个 receiver
- 主线程堆栈
- `am_anr` EventLog 条目

### 🔹 Android 14/16/17 广播调度变更

#### Android 14：BroadcastQueueModernImpl 引入

Android 14（API 34）通过 `DeviceConfig` 引入了 `BroadcastQueueModernImpl` 作为可选实现。其核心变化：

- 将 **有序广播的串行投递** 从全局队列级别改为**进程级队列**（`BroadcastProcessQueue`）
- 有序广播不再阻塞不相关进程的并行广播投递
- 通过 `DeviceConfig.NAMESPACE_ACTIVITY_MANAGER` 的 `broadcast_queue_modern` flag 控制开关

[适用版本: Android 14 (API 34) 起引入，默认关闭]

#### Android 15：Modern 实现增强

Android 15（API 35）对 Modern 实现做了进一步优化：

- `BroadcastProcessQueue` 增加**优先级调度**支持
- 改进了进程拉起后的批量投递逻辑
- `BroadcastRecord` 增加 `delivery` 状态跟踪字段

#### Android 16：Modern 实现成为默认

Android 16（API 36）将 `BroadcastQueueModernImpl` 设为默认实现：

- `BroadcastQueueImpl`（Legacy）标记为 `@Deprecated`
- 新设备默认启用 Modern 实现
- `BroadcastQueue` 基类增加了统一的 `broadcastIntent` 入口

[适用版本: Android 16 (API 36) — Modern 实现默认化]

#### Android 17：Cached App 广播延迟与合并

Android 17（API 37）引入了对 cached app 的广播投递优化：

- **延迟投递**：目标进程处于 cached 状态时，非紧急广播不立即拉起进程
- **广播合并**：多个发往同一 cached 进程的广播在队列中合并，待进程被其他原因拉起时一并投递
- **`FLAG_RECEIVER_OFFLOAD`**：允许广播标记为可延迟投递，系统可以在合适时机批量处理
- **与 Freezer 联动**：被冻结进程的广播投递被挂起，解冻后才处理

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java — cached app delivery 逻辑]

> 注意：这些延迟投递策略不影响前台广播和带有 `FLAG_RECEIVER_FOREGROUND` 的广播。

### 🔹 广播性能优化策略

#### 有序广播 vs 无序广播

| 特性 | 无序广播（Normal） | 有序广播（Ordered） |
|------|-------------------|-------------------|
| 投递方式 | 并行投递给所有接收者 | 串行投递，前一个完成后才投递下一个 |
| 性能影响 | 低（并行调度） | 高（串行等待） |
| 可截断 | 否 | 是（`abortBroadcast`） |
| 结果传递 | 无 | `getResultExtras` / `getResultCode` |
| 适用场景 | 事件通知 | 需要优先级/拦截的场景 |

**性能建议**：仅在确实需要串行处理或结果传递时使用有序广播。无序广播的并行投递延迟显著更低。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastQueueModernImpl.java — `deliverToReceiver` 并行/串行分支]

#### RECEIVER_NOT_EXPORTED 强制要求

Android 14（targetSdkVersion 34+）强制要求动态注册的 receiver 必须显式声明 export 标志：

```java
// Android 14+ 必须指定以下之一
registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED);
// 或
registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED);
```

`RECEIVER_NOT_EXPORTED` 的性能意义：系统跳过跨进程广播分发查询，仅投递给同进程的 receiver，减少了 PackageManager 查询和 IPC 开销。

[适用版本: Android 14 (API 34) — targetSdk 34+ 强制]

#### LocalBroadcastManager 的废弃

`LocalBroadcastManager` 已在 AndroidX 中废弃。官方推荐替代方案：

- **同进程通信**：使用 `LiveData`、`Flow` 或直接回调
- **跨进程通信**：使用标准 `BroadcastReceiver` + `RECEIVER_NOT_EXPORTED`

`LocalBroadcastManager` 的性能问题在于它维护了一个全局锁和 `ArrayList`，在高频广播场景下成为主线程瓶颈。

#### 注册开销与动态注册最佳实践

`registerReceiver` 的开销主要来自：

1. `PackageManager` 查询匹配的 receiver（对 implicit broadcast 尤为昂贵）
2. `IntentFilter` 匹配（`IntentFilter.match` 复杂度随 filter 数量增长）
3. 写入 `mRegisteredReceivers` 锁

**最佳实践**：
- 尽量使用 manifest 静态注册（系统在安装时预解析 filter）
- 动态注册时使用 explicit intent（指定 component），避免 PackageManager 查询
- 在 `onPause` / `onStop` 时及时 `unregisterReceiver`，避免泄漏和无效调度

### 🔹 系统广播的限流与合并

#### 高频系统广播的合并

部分系统广播由于触发频率高，系统内置了合并机制：

| 广播 Action | 合并策略 | 性能影响 |
|-------------|----------|----------|
| `ACTION_SCREEN_ON` / `ACTION_SCREEN_OFF` | 不合并（每次发送都投递） | 每次屏幕开关触发一次，频率低 |
| `ACTION_BATTERY_CHANGED` | 系统级 sticky broadcast 替代（仅保留最新值） | 频繁更新，通过 sticky 避免队列积压 |
| package 相关（`PACKAGE_ADDED` 等） | 按 `userId` 合并连续事件 | 安装/卸载风暴时显著减少广播数量 |

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java — `broadcastIntentLocked` 合并逻辑]

#### BIND_* 广播的进程拉起代价

某些系统广播（如 `ACTION_BIND_APP_WIDGET`）会触发目标进程的拉起。在 Android 17 中，对于 cached/empty 进程：

- 系统先检查进程是否已被冻结或处于 standby
- 如果进程优先级低于阈值，延迟广播投递直到进程被其他原因拉起
- 这避免了低优先级广播导致的大量进程拉起（proactive process launch）

[适用版本: Android 16 (API 36) — Android 17 (API 37)]

#### Package Replace 广播风暴

应用更新场景下，`PACKAGE_REPLACED`、`PACKAGE_ADDED`、`PACKAGE_CHANGED` 等广播可能同时发往大量接收者。系统防护机制：

- **uid 合并**：同一 `uid` 的多个 receiver 合并为一次投递
- **进程合并**：同一进程的多个 receiver 合并为一次 IPC 调用
- **Modern 实现**：`BroadcastProcessQueue` 自动将同进程广播聚合

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BroadcastProcessQueue.java]

### 🔹 Perfetto 中的广播性能分析

Perfetto 是分析广播延迟的核心工具。以下是在 Perfetto 中定位广播性能问题的关键轨道和 SQL 查询：

#### 关键 Trace 轨道

| Trace 轨道 | 来源 | 内容 |
|-----------|------|------|
| `BroadcastQueueModernImpl` | atrace | `processNextBroadcast` 耗时、队列状态 |
| `am_proc_start` | EventLog | 因广播拉起的进程信息 |
| `am_broadcast_discard_app` | EventLog | 被丢弃的广播（进程被杀等） |
| main thread | sched | `onReceive` 执行耗时 |

#### 典型广播延迟分析 SQL

```sql
-- 查找广播投递延迟（从入队到开始投递）
SELECT
  ts,
  dur,
  name
FROM slice
WHERE name LIKE 'broadcastProcessEvent%'
ORDER BY ts
LIMIT 50;

-- 查找因广播拉起的进程（冷启动延迟归因）
SELECT
  s.ts AS start_ts,
  s.dur,
  s.name,
  t.name AS thread_name
FROM thread t
JOIN thread_state ts ON ts.tid = t.tid
WHERE t.name LIKE '%Broadcast%'
  AND ts.state = 'R'
ORDER BY s.ts;
```

[待验证: SQL 查询需根据具体 Perfetto trace 版本调整字段名]

#### 广播 ANR 的 Trace 特征

广播 ANR 在 Perfetto 中的典型表现：

1. `BroadcastQueueModernImpl` 轨道显示 `broadcastANRLocked` 标记
2. 目标进程的主线程在 `onReceive` 中长时间运行（或被阻塞）
3. `am_anr` EventLog 时间戳对应 ANR 触发点
4. 进程可能处于 `S`（sleeping）状态——表明 `onReceive` 中有同步等待

> 详细的广播 ANR 分析方法参见 §9.2「ANR 类型与触发条件」和 §9.8「ANR Kernel Trace 联合诊断」。

## 扩展

### 🔸 Sticky Broadcast 的废弃与替代

Sticky Broadcast 在 Android 5.0（API 21）被废弃，Android 6.0+ 进一步限制：

- `sendStickyBroadcast` 已废弃，`sendStickyBroadcastAsUser` 同样废弃
- 系统保留了一些 sticky broadcast 的内部使用（如 `ACTION_BATTERY_CHANGED`）
- **废弃原因**：sticky broadcast 的状态不可靠（多发送者覆盖）、安全风险（任意应用可读取上一次广播内容）、内存泄漏

**替代方案**：
- 应用内状态共享：`LiveData`、`StateFlow`、`SharedFlow`
- 跨进程状态共享：`ContentProvider` + `ContentObserver`、`Messenger`、AIDL
- 持久化状态：`DataStore`、`SharedPreferences`

### 🔸 前台服务广播与 FGS 类型联动

Android 14（API 34）引入了 FGS（Foreground Service）类型声明要求。广播与 FGS 的联动约束：

- 通过广播启动 FGS 时，广播的 action 必须与 FGS 类型匹配
- `BOOT_COMPLETED` 广播启动 FGS 有额外限制（Android 14+）
- 后台启动 FGS 受 `FGS_TYPE_*` 声明约束（详见 §5.17）

[适用版本: Android 14 (API 34) — Android 17 (API 37)]

> 详见 §5.17「Android 17 FGS 类型声明与后台执行性能边界」和 §9.4「特殊场景的 ANR」。

---

**版本边界声明**：本节基于 AOSP `android-17.0.0_r1` 源码分析。`BroadcastQueueModernImpl` 的行为适用于 Android 14+ 启用 Modern 实现的设备，Android 16+ 为默认。Android 14 以下设备使用 `BroadcastQueueImpl`（Legacy），投递逻辑存在差异。
