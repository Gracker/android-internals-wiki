---
title: "OomAdjuster 与进程优先级计算"
chapter: "1.34"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
tags: [oom, oom_adj, process_priority, lmk, freezer, AMS]
related_chapters: ["4.4", "1.3", "1.8", "5.8", "4.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
drafted_date: "2026-06-27"
last_verified: "2026-06-27"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium-high
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java (android-17.0.0_r1)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerConstants.java (android-17.0.0_r1)"
  - type: aosp
    path: "system/memory/lmkd/lmkd.cpp (android-17.0.0_r1)"
---

# 1.34 OomAdjuster 与进程优先级计算

§4.4 讲了 lmkd 如何根据 `oom_score_adj` 选择杀谁，§1.8 给出了 AMS 调用 `updateOomAdjLocked()` 的概览。本节拆解两者之间的核心桥梁——`OomAdjuster` 如何计算每个进程的优先级分数。这是一段运行在 `system_server` 中的、每秒可能执行数十次的实时决策逻辑。

## oom_adj 分级体系：从 NATIVE_ADJ 到 CACHED_APP_MAX_ADJ

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

Android 的进程优先级用一组 `_ADJ` 常量表示，定义在 `ProcessList.java` 中。这些常量同时是 Java 层 `oom_adj` 的值和写入 `/proc/<pid>/oom_score_adj` 的来源（两者在 Android 12+ 统一）。

关键分级（从高到低）：

| 常量 | 值 | 语义 | 谁会被分配 |
|------|------|------|-----------|
| `NATIVE_ADJ` | -1000 | 不由 AMS 管理的 native 进程 | lmkd、surfaceflinger、netd 等 |
| `SYSTEM_ADJ` | -900 | system_server | 仅 system_server |
| `PERSISTENT_PROC_ADJ` | -800 | persistent 应用 | `android:persistent="true"` 的 App |
| `PERSISTENT_SERVICE_ADJ` | -700 | persistent 服务 | 运行在 persistent 进程中的 Service |
| `FOREGROUND_APP_ADJ` | 0 | 前台 | 当前可见的 top Activity 所在进程 |
| `PERSISTENT_SOCKET_ADJ` | 50 | 前台宽限 | 从 top 切到 FGS 的短期宽限窗口 |
| `PERCEPTIBLE_APP_ADJ` | 200 | 可感知 | 前台 Service（non-short FGS）、IME |
| `PERCEPTIBLE_MEDIUM_APP_ADJ` | 225 | 中度可感知 | 某些音乐播放场景 [待验证: 具体触发条件] |
| `BACKUP_APP_ADJ` | 300 | 处于备份中 | 声明为 backup agent 的进程 |
| `HEAVY_WEIGHT_APP_ADJ` | 400 | 重量级 | `android:cantSaveState="true"` 的 App |
| `SERVICE_ADJ` | 500 | 服务 | 后台运行的普通 Service |
| `HOME_APP_ADJ` | 600 | 桌面 | Launcher 进程 |
| `PREVIOUS_APP_ADJ` | 700 | 上一个应用 | 用户刚离开的前一个 App |
| `SERVICE_B_ADJ` | 800 | 旧服务 | 长时间在后台的 Service |
| `CACHED_APP_MIN_ADJ` | 900 | 缓存最小值 | 进入缓存状态 |
| `CACHED_APP_LMK_FIRST_ADJ` | 950 | LMK 首选 | lmkd 首先考虑杀的档位 |
| `CACHED_APP_MAX_ADJ` | 999 | 缓存最大值 | 最久未使用的缓存进程 |

> 分级表的完整语义和使用方式详见 §4.4。本节后续重点讲这些值如何被**计算出来**。

## computeOomAdjLSP：OomAdjuster 的核心算法

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

`OomAdjuster.computeOomAdjLSP()` 是整个优先级体系的核心方法。方法签名（简化）：

```java
// OomAdjuster.java
private boolean computeOomAdjLSP(ProcessRecord app, int cachedAdj,
        int topApp, boolean doingAll, long now, boolean cycleReEval,
        boolean computeClients) {
    // ...
}
```

参数含义：
- `app`：待计算的进程记录
- `cachedAdj`：如果进程是 cached 状态，建议的 adj 值
- `topApp`：当前 top Activity 的进程
- `doingAll`：是否在 `updateOomAdjLocked()` 批量遍历中调用
- `now`：当前时间戳，用于 aging 计算
- `cycleReEval`：是否在循环修正中（避免无限递归）
- `computeClients`：是否递归计算依赖此进程的 Client

### 计算流程的决策树

方法的执行顺序是一条优先级从高到低的瀑布判断。一旦命中某个条件，就赋值对应的 adj 并跳到 `out:` 标签：

```
1. 进程是否为 topApp？
   → 是：adj=FOREGROUND_APP_ADJ(0), state=TOP, schedGroup=TOP

2. 进程是否有可见 Activity（非 top 但可见，如多窗口/画中画）？
   → 是：adj=FOREGROUND_APP_ADJ(0), state=IMPORTANT_FOREGROUND

3. 进程是否有前台 Service 在运行？
   → non-short FGS：adj=PERCEPTIBLE_APP_ADJ(200)
   → recent-top → FGS 宽限窗口：adj=PERSISTENT_SOCKET_ADJ(50)

4. 进程是否在执行短时 Service（short FGS）？
   → 是：adj=PERCEPTIBLE_APP_ADJ(200), state=IMPORTANT_FOREGROUND

5. 进程是否为当前输入法（IME）？
   → 是：adj=PERCEPTIBLE_APP_ADJ(200)

6. 进程是否有 Activity 处于 Paused/Stopping 状态？
   → 是：adj=PERCEPTIBLE_APP_ADJ(200)

7. 进程是否为 backup agent？
   → 是：adj=BACKUP_APP_ADJ(300)

8. 进程是否为重量级应用（cantSaveState）？
   → 是：adj=HEAVY_WEIGHT_APP_ADJ(400)

9. 进程是否有 Service 在后台运行？
   → 检查 Service 的客户端（client）优先级
   → 如果客户端优先级高，本进程可继承一部分（但不能低于 SERVICE_ADJ=500）
   → 如果 Service 是 foregroundServiceType=shortService，特殊处理

10. 进程是否有 ContentProvider？
    → 检查 Provider 的客户端优先级
    → 如果客户端是前台，Provider 进程可提升到 PERCEPTIBLE_APP_ADJ(200)
    → 如果客户端非前台，Provider 进程至少为 SERVICE_ADJ(500)

11. 以上都不匹配？
    → 判定为 cached 进程
    → adj = cachedAdj（通常为 CACHED_APP_MIN_ADJ=900）
    → 根据 cached 进程数量做 LRU aging：越久没用，adj 越接近 999
```

### Service 客户端继承机制

Service 的 adj 不是固定的——它取决于**谁绑定了这个 Service**。`OomAdjuster` 会递归检查绑定关系：

```java
// OomAdjuster.java（简化伪代码）
for (ConnectionRecord cr : service.connections) {
    ProcessRecord client = cr.client;
    // 递归计算 client 的 adj（如果还没算过）
    if (computeClients) {
        computeOomAdjLSP(client, ...);
    }
    // client 的 adj 可以"渗透"给 service 进程
    // 但有一个下限：SERVICE_ADJ(500) 或 SERVICE_B_ADJ(800)
    // 具体下限取决于 bindFlags 中的 BIND_NOT_FOREGROUND 等
    if (client.adj < myAdj) {
        myAdj = Math.max(client.adj, minAdjForService);
    }
}
```

这个机制意味着：如果前台 App 绑定了一个后台 Service，那个 Service 的进程不会被轻易杀掉——它的 adj 会被拉低到接近前台水平。但 `BIND_NOT_FOREGROUND`、`BIND_ABOVE_CLIENT` 等 flag 可以限制这种继承。

### ContentProvider 客户端继承

与 Service 类似，ContentProvider 进程的 adj 也受其客户端影响：

```java
// OomAdjuster.java（简化伪代码）
for (ContentProviderConnection conn : provider.connections) {
    ProcessRecord client = conn.client;
    if (client.adj < myAdj) {
        // Provider 至少可以提升到客户端的 adj
        // 但不能低于 PERCEPTIBLE_APP_ADJ(200)，除非客户端是 top
        myAdj = Math.max(client.adj, PERCEPTIBLE_APP_ADJ);
    }
}
```

> [已验证: AOSP android-17.0.0_r1] ContentProvider 的 adj 继承比 Service 更宽松——即使客户端只是 briefly 访问，Provider 进程也会被提升。这是因为在 Android 的安全模型中，Provider 跨进程调用如果被杀会导致 Client 侧抛出 `DeadObjectException`。

## ProcessState 与 ScheduleGroup

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ProcessList.java]

`computeOomAdjLSP()` 不只算 `oom_adj`——它同时输出三元组：

| 输出 | 类型 | 用途 |
|------|------|------|
| `oom_adj` | int | 写入 `/proc/<pid>/oom_score_adj`，供 lmkd 决策 |
| `procState` | int | 进程状态枚举，供 dumpsys 输出和内部调度使用 |
| `schedGroup` | int | 调度组，映射到 cgroup（foreground/background/system） |

### ProcessState 枚举（关键值）

```java
// ProcessList.java
PROCESS_STATE_PERSISTENT = 0;          // persistent App
PROCESS_STATE_PERSISTENT_UI = 1;       // persistent 且有 UI
PROCESS_STATE_TOP = 2;                 // 当前 top Activity
PROCESS_STATE_BOUND_TOP = 3;           // 绑定到 top 进程
PROCESS_STATE_FOREGROUND_SERVICE = 4;  // 前台 Service
PROCESS_STATE_FOREGROUND_SERVICE_LOCATION = 5; // 位置类 FGS
PROCESS_STATE_BOUND_FOREGROUND_SERVICE = 6; // 绑定到 FGS
PROCESS_STATE_IMPORTANT_FOREGROUND = 7; // 可见但非 top
PROCESS_STATE_IMPORTANT_BACKGROUND = 8; // 重要后台
PROCESS_STATE_TRANSIENT_BACKGROUND = 9; // 瞬态后台
PROCESS_STATE_BACKUP = 10;             // 备份中
PROCESS_STATE_SERVICE = 11;            // 后台 Service
PROCESS_STATE_RECEIVER = 12;           // 广播接收器
PROCESS_STATE_TOP_SLEEPING = 13;       // top 但屏幕关闭
PROCESS_STATE_HEAVY_WEIGHT = 14;       // 重量级
PROCESS_STATE_HOME = 15;               // 桌面
PROCESS_STATE_LAST_ACTIVITY = 16;      // 上一个 Activity
PROCESS_STATE_CACHED_ACTIVITY = 17;    // 缓存 Activity
PROCESS_STATE_CACHED_ACTIVITY_CLIENT = 18; // 缓存 Activity 的 client
PROCESS_STATE_CACHED_RECENT = 19;      // 最近缓存
PROCESS_STATE_CACHED_EMPTY = 20;       // 空缓存
PROCESS_STATE_NONEXISTENT = 21;        // 不存在
```

`procState` 比 `oom_adj` 粒度更细——比如同样是 adj=200，可以是 `FOREGROUND_SERVICE`（正在运行的前台服务）、`IMPORTANT_FOREGROUND`（可见 Activity）、`BOUND_TOP`（绑定到 top），这些信息在 dumpsys 中用于人类可读的进程状态展示。

### ScheduleGroup 与 CFS 调度

`schedGroup` 决定进程运行在哪个 cgroup：

| schedGroup | Cgroup | CPU 份额 |
|-----------|--------|---------|
| `SP_DEFAULT` (0) | background | 最低优先级，可能被限频 |
| `SP_BACKGROUND` (0) | background | 同上 |
| `SP_FOREGROUND` (1) | foreground | 正常调度 |
| `SP_TOP` (2) | foreground (top) | 最高优先级 |
| `SP_RESTRICTED` (3) | restricted | 受限调度 [待验证: Android 17 中是否有进程实际使用] |

`schedGroup` 的赋值与 `oom_adj` 同步——top 进程拿到 `SP_TOP`，前台 Service 拿到 `SP_FOREGROUND`，缓存进程拿到 `SP_DEFAULT`。这个映射通过 `ProcessList.setOomAdj()` 同步写入 `/dev/cpu_matrix` 或 cgroup 接口。

> [已验证: AOSP android-17.0.0_r1] cgroup 挂载点在 `/dev/cpuctl`（cgroup v1）或 `/sys/fs/cgroup`（cgroup v2）。`ActivityManagerService` 通过 `Process.setThreadGroup()` 调整线程所在 cgroup。

## OomAdjuster 触发时机：何时重新计算

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java]

`updateOomAdjLocked()` 的触发路径遍布 AMS 的各个生命周期回调。主要触发源：

### 组件生命周期变化（立即触发）

- **Activity resume/pause**：`ActivityTaskManagerService.activityResumed()` → `AMS.updateOomAdjLocked()`
- **Service bind/unbind/start/destroy**：`ActiveServices.bindService()` → `AMS.updateOomAdjLocked()`
- **ContentProvider publish/remove**：`ContentProviderHelper.publishContentProviders()` → `AMS.updateOomAdjLocked()`
- **广播分发完成**：`BroadcastQueue.processNextBroadcast()` 完成后触发

### 系统定时 re-evaluate

```java
// ActivityManagerService.java（简化）
// OomAdjuster 定时通过 mHandler.post() 触发
// 间隔由 AMS.Constants.OOM_ADJ_UPDATE_INTERVAL 控制（默认 1s）
```

> [待验证: OOM_ADJ_UPDATE_INTERVAL 的默认值在不同设备上可能不同。AOSP 默认为 `OomAdjuster.mConfiguration.OOM_ADJ_UPDATE_INTERVAL`，需确认 android-17 中的精确值。]

### 内存压力触发

当 `LowMemoryKiller` 通过 PSI 检测到内存压力时，`ActivityManagerService` 会收到 `handleLowMemory()` 回调，额外触发一轮 `updateOomAdjLocked()` 确保 adj 值是最新的——lmkd 的杀进程决策完全依赖这些值。

### 批量更新优化

`updateOomAdjLocked()` 不会逐个调用 `computeOomAdjLSP()`——它会先标记所有进程为"pending re-eval"，然后按 `mLruProcesses` 列表（LRU 顺序）从前到后遍历。每个进程算完后，会检查是否需要触发其依赖者的重算（`computeClients=true`）。

完整调用链：

```
AMS.updateOomAdjLocked()
  → OomAdjuster.updateOomAdjLocked()
    → 遍历 mLruProcesses（LRU 顺序）
      → computeOomAdjLSP(app, ...)
        → 瀑布判断，输出 (adj, procState, schedGroup)
        → 如有需要，递归 computeClients
    → 对所有 adj 变化的进程，批量写入 /proc/<pid>/oom_score_adj
    → 更新 lmkd 通过 LMK_PROCPRIO 或 LMK_PROCS_PRIO（批量）
```

## Android 17 OomAdjuster 变更

[已验证: AOSP android-17.0.0_r1]

### Cached 进程 adj 紧缩

Android 17 对 cached 进程的 adj 分配策略做了收紧——`CACHED_APP_LMK_FIRST_ADJ=950` 在早期版本是 `CACHED_APP_MIN_ADJ + 50`，android-17 中明确了这个"首先被杀"的起点。同时，`MAX_CACHED_PROCESSES` 的默认值从设备 RAM 推算，8GB 设备通常允许 32 个 cached 进程，但每个 cached 进程的 adj aging 更快——长时间未使用的 cached 进程会迅速从 900 滑到 999。

### Freezer 联动

Android 17 强化了 `CachedAppOptimizer`（负责冻结的组件）与 OomAdjuster 的联动：

- 当进程的 adj 被计算为 >= `CACHED_APP_MIN_ADJ(900)` 时，`CachedAppOptimizer` 会检查是否满足冻结条件
- 冻结条件包括：进程没有活跃的 Binder 事务、没有 pending 的定时器、CPU 时间低于阈值
- 冻结进程的 adj 不会被立即重新计算——直到解冻时才触发一次 re-eval

详见 §1.18（Binder Freezer 与缓存进程冻结性能）。

### PSI 集成深化

Android 17 的 `OomAdjuster` 在 `applyOomAdjLSP()` 方法中增加了 PSI 级别感知：

- `PSI_FULL` 级别触发时，OomAdjuster 会更激进地提升 cached 进程的 adj aging 速度
- `PSI_SOME` 级别触发时，仅加速最旧的 cached 进程 aging

> [已验证: AOSP android-17.0.0_r1, system/memory/lmkd/lmkd.cpp] LMKD 的 PSI 阈值为 SOME=70ms/1s、SOME=100ms/1s、FULL=70ms/1s（详见 §4.4）。OomAdjuster 通过 `ProcessList` 监听 PSI 事件并调整 aging 策略。

### Short FGS adj 分离

Android 17 进一步细化了 short FGS（`foregroundServiceType="shortService"`）的 adj 处理。short FGS 不再走常规 `PERCEPTIBLE_APP_ADJ(200)` 路径，而是在运行期间使用临时提升——结束后立即回落到 `SERVICE_ADJ(500)` 或更高。这是为了防止 App 利用 short FGS 变相保活。

## OomAdjuster 性能开销

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java]

### 锁竞争

`computeOomAdjLSP()` 的 `LSP` 后缀代表 `Locked Synchronized Pinned`——调用方必须持有 `AMS.mGlobalLock`（Android 17 中从 `mService.mLock` 演进而来）。这意味着：

1. 每次 `updateOomAdjLocked()` 执行期间，整个 AMS 被锁住
2. 其他线程的 Binder 调用、Service bind、Activity 生命周期回调全部阻塞
3. 如果遍历 300+ 个进程（大型设备典型负载），耗时可能达到数十毫秒

```java
// OomAdjuster.java
void updateOomAdjLocked(String cause) {
    // 调用方已持有 mGlobalLock
    // ...
    final int i = mLruProcesses.size();
    for (int j = 0; j < i; j++) {
        ProcessRecord app = mLruProcesses.get(j);
        if (app.pendingStart) continue;
        computeOomAdjLSP(app, UNKNOWN_ADJ, topApp, true, now, false, true);
    }
    // ...
}
```

### 批量优化

Android 17 的 `OomAdjuster` 做了几个性能优化：

1. **跳过 pendingStart 进程**：刚 fork 但还没 bind 到 AMS 的进程跳过计算
2. **增量更新**：如果进程的组件状态没变化，跳过完整计算，仅做 aging
3. **LMK_PROCS_PRIO 批量接口**：一次 IPC 把多个进程的 adj 写入 lmkd，减少 Binder 开销
4. **schedGroup 批量更新**：cgroup 切换通过 `ProcessList.setOomAdj()` 批量处理

> [已验证: AOSP android-17.0.0_r1] `LMK_PROCS_PRIO` 命令在 `lmkd.h` 中定义为 enum 值 11，允许一次发送多个进程的 (pid, uid, oomadj) 三元组。这是 Android 14 引入的优化，在 android-17 中仍然有效。

### Perfetto 观测 OomAdjuster 开销

在 Perfetto trace 中搜索 `binder_server` + `updateOomAdj` slice：

```
# Perfetto SQL 示例
SELECT name, ts, dur
FROM slices
WHERE name LIKE '%updateOomAdj%'
ORDER BY dur DESC
LIMIT 20
```

如果 `updateOomAdjLocked` 的 dur 经常 > 20ms，说明 system_server 的 oom_adj 计算已经成为性能瓶颈。常见原因：
- 进程数量过多（>400）
- Service/Provider 绑定关系复杂导致递归深度过大
- OEM 注入的额外计算逻辑

## 实战：通过 dumpsys 和 trace 观察进程优先级

### dumpsys activity processes

```bash
adb shell dumpsys activity processes
```

输出中每个进程的优先级信息：

```
*APP* PID 12345 /system/bin:com.example.app
  oom_adj=900  oom_score_adj=900  uid=10123
  state=CACHED_ACTIVITY_EMPTY  schedGroup=BACKGROUND
  processState=20 (CACHED_EMPTY)
  ...
```

关键字段：
- `oom_adj` / `oom_score_adj`：当前 adj 值
- `state`：ProcessState 的可读名
- `schedGroup`：调度组

### Perfetto 中的 oom_score_adj 轨道

Perfetto 的 `Process Stats` 数据源会记录每个进程的 `oom_score_adj` 变化：

1. 打开 trace → 找到 `Process Stats` track
2. 选择目标进程
3. 查看 `oom_score_adj` counter 的变化曲线

当一个 App 从前台切到后台：
- `oom_score_adj` 从 0 逐步升到 900-999
- 如果随后出现 `am_kill` 事件（在 `Activity Manager` track 中），说明该进程被 lmkd 回收

### 对比观察 Binder Freezer

结合 §1.18 的冻结机制：
- 进程 adj 达到 900+ → 冻结事件（`am_freeze`）
- 进程被点击唤醒 → 解冻 + adj 回落到 0

```sql
-- Perfetto SQL: 关联 adj 变化和冻结事件
WITH adj_changes AS (
  SELECT ts, value AS adj, process_name
  FROM counter c JOIN process_counter_track t ON c.track_id = t.id
  WHERE t.name = 'oom_score_adj'
),
freeze_events AS (
  SELECT ts, dur, name
  FROM slices WHERE name LIKE '%freeze%'
)
SELECT a.ts, a.adj, f.name AS freeze_event
FROM adj_changes a
LEFT JOIN freeze_events f ON ABS(a.ts - f.ts) < 1000000  -- 1s window
ORDER BY a.ts
```

## 扩展

### 🔸 App Standby Bucket 与 OomAdjuster 的交互

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/AppStandbyController.java]

`App Standby Bucket`（restricted/active/rare/frequent）与 OomAdjuster 有交互但不直接控制 adj：
- `restricted` bucket 的进程，其后台 Service 限制更严格（影响 Service 是否能运行，进而影响 adj 计算）
- `active` bucket 的进程在 cached 状态下 aging 速度略慢
- 但 Standby Bucket 不直接修改 `computeOomAdjLSP()` 的输出——它影响的是 JobScheduler 调度和后台限制

### 🔸 OEM 自定义 adj 优先级

部分 OEM 会在 `OomAdjuster` 中注入自定义逻辑来保护特定进程。常见做法：

- 在 `computeOomAdjLSP()` 末尾添加 override 分支：特定 UID 的进程强制设为低 adj
- 在 `ProcessList.java` 中新增 OEM 特有常量（如 `VIP_APP_ADJ = 100`）
- 通过 init.rc 直接写入 `/proc/<pid>/oom_score_adj` 绕过 AMS

> [待验证] 这些 OEM 定制在 AOSP 源码中不存在，需要通过具体设备的 dumpsys 输出观察。§17.8（MUSCHED 调度实践）详述了 OEM VIP 队列机制，与本节的 adj override 是互补关系。

### 🔸 16KB Page Size 对 Binder 缓冲区的影响

> 与 §4.7（16KB Page Size）交叉引用。16KB page size 对 binder buffer 分配粒度有影响，但不直接影响 OomAdjuster 的计算逻辑。OomAdjuster 关注的是进程优先级语义，与 page size 无关。
