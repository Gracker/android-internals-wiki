---
title: "ContentProvider ANR 双路径：Publish 超时与 Call Hang 检测"
chapter: "9.9"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [anr, content-provider, publish-timeout, call-hang, ams]
related_chapters: ["1.10", "9.2", "9.4", "9.7"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "素材驱动/DeepResearch"
drafted_date: "2026-06-07"
last_verified: "2026-06-07"
last_verified_against: "AOSP android-16.0.0_r1 ContentResolver / ContentProviderHelper / ContentProviderClient; 官方 ANR 文档 developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs"
confidence: medium
sources:
  - type: aosp
    path: frameworks/base/core/java/android/content/ContentResolver.java
  - type: aosp
    path: frameworks/base/core/java/android/content/ContentProviderClient.java
  - type: aosp
    path: frameworks/base/services/core/java/com/android/server/am/ContentProviderHelper.java
  - type: aosp
    path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java
  - type: official
    path: developer.android.com/topic/performance/anrs/diagnose-and-fix-anrs
---

# 9.9 ContentProvider ANR 双路径：Publish 超时与 Call Hang 检测

ContentProvider 在 AOSP 中存在两条独立的超时/ANR 路径，触发机制、超时常量、处理流程和 Perfetto 表现完全不同：

1. **Provider 进程 publish 注册超时**——进程启动后未在规定时间内向 AMS 注册 provider，结果是被杀，不弹 ANR 对话框
2. **已发布 provider 的 call hang 检测**——调用方主动开启超时监控，超时后走标准 ANR 流程，弹对话框

两条路径容易混淆，因为它们的 Reason 行都包含 "ContentProvider"，但根因和排查方向截然不同。

（ContentProvider 的基础架构、初始化时序和跨进程通信机制详见 §1.10；ANR 的四大类型概览详见 §9.2。）

## ContentProvider 超时常量定义

四个超时常量全部定义在 `ContentResolver`（`frameworks/base/core/java/android/content/ContentResolver.java`），而非 `ContentProviderHelper`。每个常量对应 AMS 中不同的 `what` 消息码和等待条件。

| 常量 | 基准值 | 含义 | AMS 消息码 |
|------|--------|------|-----------|
| `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS` | 10s × HW | Provider 进程 publish 注册超时 | `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG = 57` |
| `CONTENT_PROVIDER_READY_TIMEOUT_MILLIS` | 20s × HW | 调用方等待新启动 provider 发布 | `WAIT_FOR_CONTENT_PROVIDER_TIMEOUT_MSG = 73` |
| `CONTENT_PROVIDER_TIMEOUT_MILLIS` | 3s × HW | `getTypeAsync()`、`canonicalizeAsync()` 等异步回调超时 | — |
| `REMOTE_CONTENT_PROVIDER_TIMEOUT_MILLIS` | — | 远端 provider 操作超时 | — |

所有基准值都乘以 `Build.HW_TIMEOUT_MULTIPLIER`（§9.2 已提及该系数对各类型 ANR 超时的影响）。

[已验证: AOSP android-16.0.0_r1, ContentResolver.java l.786-806, ActivityManagerService.java:1551,1561]

## 路径 1：Provider Publish 超时

### 触发流程

当 AMS 拉起一个包含 ContentProvider 的进程后，该进程必须在 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`（默认 10s × HW multiplier）内向 AMS 注册其 provider。注册动作发生在 `ActivityThread.handleBindApplication()` → `installContentProviders()` 完成之后，通过 `IActivityManager.publishContentProviders()` 把 provider 的 `ContentProviderHolder` 放入 `mProviderMap`。

```
AMS.attachApplicationLocked()
  → 发送 CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG (what=57)
  → 等待进程调用 publishContentProviders()
```

[已验证: AOSP android-16.0.0_r1, ActivityManagerService.attachApplicationLocked()]

如果在超时窗口内进程未完成 publish，AMS 的 handler 收到 `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MSG` 后调用 `ContentProviderHelper.processContentProviderPublishTimedOutLocked()`，最终执行 `removeProcessLocked()` + `REASON_INITIALIZATION_FAILURE` 杀掉进程。

### 关键特征：不弹 ANR 对话框

这是路径 1 与路径 2 的根本区别。publish 超时直接杀进程，不会弹出 ANR 对话框，Perfetto 中不会出现 `am_anr` 事件。能观察到的是：

- `am_proc_died` 事件，附带 `SUBREASON_UNKNOWN` 或 `REASON_INITIALIZATION_FAILURE`
- 日志中出现 "Unable to launch app ... for provider ... launching app became null"

### publish 超时的常见根因

- `ContentProvider.onCreate()` 执行了同步数据库初始化、大文件读取、网络请求等耗时操作
- 多个 ContentProvider 顺序初始化，累计耗时超过 10s（关于 CP 初始化顺序的影响详见 §1.10）
- Provider 进程本身启动缓慢（Zygote fork + Application 初始化 + CP 初始化全部挤在同一个 10s 窗口内）
- 低端设备上 HW_TIMEOUT_MULTIPLIER 放大了基准超时，但实际初始化时间增长可能超过乘数补偿

## 路径 2：Provider Call Hang 检测

### 触发条件

路径 2 是调用方主动开启的。通过 `ContentProviderClient.setDetectNotResponding(timeoutMillis)` 设置超时阈值后，每次通过该 client 执行 CRUD 操作时，框架会在主线程 Looper 上投递一个延迟的 `NotRespondingRunnable`。如果在 `timeoutMillis` 内操作未完成，`NotRespondingRunnable` 被执行，进入 ANR 流程。

[已验证: AOSP android-11.0.0_r1, ContentProviderClient.setDetectNotResponding()]

**注意**：`setDetectNotResponding()` 是 `@hide` / `@SystemApi` / `@TestApi` 方法，并要求 `REMOVE_TASKS` 权限。普通应用编译时拿不到这个方法。它面向 framework 内部和系统测试场景，不是应用侧可直接使用的 API。

[已验证: AOSP android-11.0.0_r1, ContentProviderClient.setDetectNotResponding() 带 @hide / @SystemApi / @TestApi 标注]

### ANR 流程

路径 2 走标准 ANR 管线：

```
NotRespondingRunnable.run()
  → ContentResolver.appNotRespondingViaProvider()
    → ContentProviderHelper.appNotRespondingViaProvider(IBinder connection)
      → mAnrHelper.appNotResponding(proc, timeoutRecord)
        → ProcessErrorStateRecord.appNotResponding()
          → AppNotRespondingDialog
```

[已验证: AOSP, ContentProviderHelper.appNotRespondingViaProvider()]

Perfetto 中标记为 `am_anr` 事件，Reason 行包含 "ContentProvider" 和 "not responding"。

### 系统侧的使用场景

AOSP 中系统服务自身会调用 `setDetectNotResponding()`。例如 `ContentProviderHelper` 在获取远端 provider 连接时，如果需要同步等待 provider 发布和响应，会通过 client 设置 call hang 检测。这意味着即使是路径 2 的 ANR，触发方也可能是系统服务而非应用代码——排查时需要确认 `setDetectNotResponding` 的调用来源。

## 两条路径的对比

| 维度 | 路径 1：Publish 超时 | 路径 2：Call Hang 检测 |
|------|---------------------|----------------------|
| 触发条件 | Provider 进程未在 10s×HW 内完成 publish | `setDetectNotResponding()` 开启后，CRUD 操作超时 |
| 超时阈值 | `CONTENT_PROVIDER_PUBLISH_TIMEOUT_MILLIS`（10s×HW） | 由调用方通过 `setDetectNotResponding(timeout)` 指定 |
| 处理结果 | 杀进程（`removeProcessLocked`），不弹 ANR 对话框 | 标准ANR流程，弹出 AppNotRespondingDialog |
| Perfetto 表现 | `am_proc_died`，无 `am_anr` | `am_anr` 事件 |
| 日志关键词 | `REASON_INITIALIZATION_FAILURE` / `launching app became null` | `ContentProvider not responding` |
| 超时来源 | AMS handler 消息（what=57） | `NotRespondingRunnable`（主线程 Looper） |
| 谁会被杀/ANR | Provider 所在进程被杀 | Provider 所在进程被判定 ANR |
| 可见性 | 无对话框，用户感知为 App 闪退 | 有 ANR 对话框，用户明确看到 |

## HW_TIMEOUT_MULTIPLIER 的影响

所有 ContentProvider 超时基准都乘以 `Build.HW_TIMEOUT_MULTIPLIER`。这个系数的目的是给性能较低的硬件更多时间完成操作。Performance Class 低的设备 multiplier 通常 ≥ 1.5x，意味着 publish 超时实际可能 ≥ 15s。

分析 ContentProvider 相关的 trace 时，必须考虑目标设备的 HW_TIMEOUT_MULTIPLIER：

```bash
# 查询设备实际值
adb shell getprop ro.hw_timeout_multiplier
```

如果 multiplier = 2，那么 publish 超时实际是 20s 而非 10s。在 Perfetto 中测量时间间隔时，需要用实际超时值来判断是否真的触发了超时。

## Perfetto 调试方法

### 区分两条路径的 SQL 查询

**路径 1（publish 超时）——查 am_proc_died，无 am_anr：**

```sql
-- 查找 publish 超时导致的进程死亡
SELECT
  ts,
  process.name AS process_name,
  slice.name AS event
FROM slice
JOIN process_track ON slice.track_id = process_track.id
JOIN process USING (upid)
WHERE slice.name LIKE '%am_proc_died%'
  AND slice.name NOT LIKE '%am_anr%'
ORDER BY ts DESC
LIMIT 20;
```

**路径 2（call hang ANR）——查 am_anr 事件：**

```sql
-- 查找 ContentProvider call hang 导致的 ANR
SELECT
  ts,
  process.name AS process_name,
  slice.name AS event
FROM slice
JOIN process_track ON slice.track_id = process_track.id
JOIN process USING (upid)
WHERE slice.name LIKE '%am_anr%'
  AND (slice.name LIKE '%content_provider%'
    OR slice.name LIKE '%ContentProvider%')
ORDER BY ts DESC
LIMIT 20;
```

### 排查入口速查

| 观察到的现象 | 排查方向 |
|-------------|---------|
| `am_proc_died` + `REASON_INITIALIZATION_FAILURE`，无 `am_anr` | 路径 1：检查 Provider 进程的 `onCreate()` 耗时 |
| `am_anr` + "ContentProvider not responding" | 路径 2：检查远端 Provider 的 CRUD 操作耗时 + Binder 线程池状态 |
| 调用方主线程 WAITING，远端进程在 `handleBindApplication()` | 路径 1 的变体：远端进程冷启动慢导致调用方等待超过 ready 超时 |
| Binder 线程全部 BUSY + `ContentProvider$Transport.*` 栈帧 | Binder 线程耗尽，不是独立的 ContentProvider 超时路径（详见 §9.4） |

## 扩展

### ContentProvider ANR 与应用启动的关系

ContentProvider publish 超时频繁发生在应用冷启动阶段。在 multi-process 场景下，Provider 进程的初始化链路（Zygote fork → Application 创建 → CP 初始化 → publish）需要在 10s×HW 内全部完成，任何一个环节变慢都可能导致超时。

冷启动期间常见的叠加因素：

- 多个 SDK 通过 ContentProvider 自动初始化（详见 §1.10 的量化数据）
- Provider 进程是独立进程（`android:process=":remote"`），有独立的 Application 初始化开销
- Provider 的 `onCreate()` 内做了同步磁盘 I/O 或数据库 migration

Jetpack App Startup 通过合并多个 CP 为单个 `InitializationProvider` 来减轻初始化负担，每合并一个 CP 约节省 2ms 启动时间（§1.10 有详细的量化数据）。但 App Startup 只解决同进程内多个 CP 的累积耗时问题，不解决单个 CP 自身 `onCreate()` 过慢的根因。

### HW_TIMEOUT_MULTIPLIER 查询与关联分析

在 Perfetto 中关联分析 HW_TIMEOUT_MULTIPLIER 的步骤：

1. 从设备信息中获取 multiplier 值（`ro.hw_timeout_multiplier` 属性）
2. 计算实际超时阈值：`基准值 × multiplier`
3. 在 Perfetto 中测量从进程启动到 publish 完成（或超时）的时间间隔
4. 用实际超时阈值判断是否属于正常超时行为

如果设备 multiplier = 2 但 publish 仍在 15s 内完成，说明 publish 本身是成功的（实际超时阈值是 20s）。如果 multiplier = 1 但 publish 耗时 11s，则已超过 10s 阈值，进程会被杀。

### ContentProvider ANR 的治理策略

**应用侧：**

- 延迟初始化：将 `ContentProvider.onCreate()` 中的非关键操作延迟到首次使用时执行
- 异步化：数据库 migration、大文件读取等操作移到后台线程，`onCreate()` 尽快返回
- 合并 CP：用 Jetpack App Startup 减少 CP 数量
- 进程拆分：将重度初始化的 CP 放到独立进程，避免影响主进程启动

**系统侧（面向 ROM/系统应用开发者）：**

- 关注 HW_TIMEOUT_MULTIPLIER 对低端设备的实际影响
- `setDetectNotResponding()` 的超时值需根据设备性能等级动态调整
- 在系统应用中使用 `ContentProviderClient` 时考虑 call hang 检测的开启条件

> [自动发现] 路径 2 的 `setDetectNotResponding()` 在 Android 11（API 30）加入 AOSP，但始终是 hidden/system API。排查线上 ContentProvider ANR 时，如果 Reason 行包含 "ContentProvider not responding"，应优先检查系统框架或系统应用的调用链，而非应用代码。
