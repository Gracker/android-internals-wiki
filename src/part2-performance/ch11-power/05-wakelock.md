---
title: "Wakelock 机制与功耗分析"
section: "11.5"
chapter: "11.5"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [wakelock, power, battery, alarmmanager, doze, batterystats, kernel-wakelock]
related_chapters: ["5.6", "5.8", "11.1", "11.2", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
gap_source: "研究素材+AOSP结构+官方文档+读者需求"
last_verified: "2026-04-07"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerManager"
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: blog
    path: "intake/research-feeds/2026-04-06-07-android17-power-management-wakelock-policy-aod-minmode.md"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
  - type: official
    path: "https://developer.android.com/topic/libraries/workmanager"
reviewed_date: "2026-04-14"
reviewed_by: "openclaw-task6"
task6_result: needs-rework
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task2b_state: pending
task9_result: needs-rework
---

# 11.5 Wakelock 机制与功耗分析

当我们在 Perfetto 中看到一条横跨数秒甚至数分钟的 `WakeLock` 条目时，它背后通常藏着一个让电池加速耗尽的问题。Wakelock 是 Android 功耗分析中最常遇到的"嫌疑人"——它设计上是为了让 CPU 在需要时保持工作，但一旦使用不当（忘记释放、异常路径泄漏、在后台长期持有），就会成为电池消耗的头号来源。

2026 年 3 月，Play Store 正式上线了 wakelock 惩罚政策，对过度持有 wakelock 的 App 实施搜索降权和耗电警告标签。这已经不只是优化建议，而是会直接影响 App 的分发和用户信任。

这篇文章我们要搞清楚几件事：Wakelock 的底层机制是什么？App 层的 wakelock 怎么映射到内核？出了问题怎么诊断？以及最重要的——怎么避免 wakelock 变成功耗灾难。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 wakelock 为什么存在，以及 `PARTIAL_WAKE_LOCK` 为什么是功耗分析的重点
- 🔹 `PowerManager.WakeLock` 的获取、引用计数、`WorkSource` 与服务端处理
- 🔹 wakelock 在 Android 电源状态机中的位置，以及 Doze / App Standby 对它的约束
- 🔹 用户态 wakelock 与内核 `wakeup_source` 的关系
- 🔹 常见泄漏模式，以及用 Battery Historian、`dumpsys batterystats`、Perfetto 排查的方法
- 🔹 `AlarmManager`、`WorkManager`、`Foreground Service` 等调度框架与 wakelock 的关系
- 🔹 版本演进、常见误区与 Play Store 合规要求

### 扩展（可选深入）

- 🔸 Android 16+ 后台执行配额与 wakelock 的交互
- 🔸 Android 17 `OnAlarmListener` 回调变体的适用场景
- 🔸 内核 `wakeup_source` 观测与 `wakeup_sources` 文件解读

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 AOSP 或研究素材里发现与本节强相关、但大纲未列出的点，
> 可插入到最相关的锚点之后，并用 `[自动发现]` 标注来源。
> 涉及版本差异、内核接口、功耗策略阈值的表述，优先保守表述，拿不准就标 `[待验证]`。
<!-- outline-end -->

## Wakelock 的本质：为什么 Android 需要"阻止睡眠"

移动设备的 CPU 大部分时间应该处于低功耗状态。屏幕关闭后，如果没有任何工作要做，系统会在几百毫秒内依次进入浅度空闲、深度空闲，最终挂起（suspend）——此时 CPU 几乎不耗电，整机功耗可以降到 1mA 以下。

但有些场景 CPU 必须保持工作：音乐播放、GPS 持续定位、即时通讯的长连接心跳、正在进行的下载任务。如果 CPU 在这些任务完成之前就进入 suspend，任务会被中断，用户体验直接受损。

Wakelock 就是 Android 为此设计的机制：它允许 App 或内核组件向系统声明"我现在需要 CPU 保持工作"。只要还有活跃的 wakelock，系统就不会进入 suspend。

Android 提供了四种 wakelock 类型，但后三种已经废弃：

| 类型 | 效果 | 状态 |
|------|------|------|
| `PARTIAL_WAKE_LOCK` | CPU 保持运行，屏幕可关闭 | 推荐使用 |
| `SCREEN_DIM_WAKE_LOCK` | 屏幕保持暗亮 | API 17 废弃 |
| `SCREEN_BRIGHT_WAKE_LOCK` | 屏幕保持全亮 | API 13 废弃 |
| `FULL_WAKE_LOCK` | CPU + 屏幕全亮 | API 13 废弃 |

后三种废弃的原因很简单：屏幕是否点亮应该由系统电源策略统一管理，而不是让 App 自行决定。现在如果需要保持屏幕常亮，正确做法是使用 `FLAG_KEEP_SCREEN_ON`（Window Flag）或 `android:keepScreenOn`（XML 属性），由 WindowManager 统一处理。

真正需要开发者关注的只有 `PARTIAL_WAKE_LOCK`。它让 CPU 在屏幕关闭后仍然运行——这正是功耗问题的高发区，因为用户看不到屏幕亮着，不知道 App 还在消耗电量。

[已验证: 官方文档, developer.android.com/reference/android/os/PowerManager#PARTIAL_WAKE_LOCK]

## Wakelock 的获取、持有与释放

### 从 PowerManager 到 PowerManagerService

获取 wakelock 的入口是 `PowerManager`：

```java
// frameworks/base/core/java/android/os/PowerManager.java
PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
PowerManager.WakeLock wl = pm.newWakeLock(
    PowerManager.PARTIAL_WAKE_LOCK, "MyApp:MyTag");
wl.acquire();
// ... 执行需要 CPU 保持工作的任务 ...
wl.release();
```

这行 `acquire()` 背后的调用链是：

1. `PowerManager.WakeLock.acquire()` → 通过 Binder 调用到 `PowerManagerService.acquireWakeLock()`
2. `PowerManagerService` 在内部为这个 wakelock 创建一个 `WakeLockToken`（`IBinder` 对象），用于标识这个 wakelock 的持有者
3. 同时注册 `IBinder.DeathRecipient`：如果持有者的进程意外死亡，系统会自动释放对应的 wakelock，防止泄漏
4. `PowerManagerService` 更新全局电源状态，根据所有活跃 wakelock 的类型决定系统是否可以进入 suspend

[已验证: AOSP android-17-beta3, frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java]

### 引用计数模式：一个常见的坑

`WakeLock` 默认启用引用计数模式（reference-counted）：

```java
wl.acquire();  // 计数 = 1
wl.acquire();  // 计数 = 2
wl.release();  // 计数 = 1，wakelock 仍然持有
wl.release();  // 计数 = 0，wakelock 释放
```

如果调用 `release()` 时计数已经为 0，会抛出 `RuntimeException`。这个设计的本意是方便同一 wakelock 在多个代码路径中分别 acquire/release 而不互相干扰。但在实际开发中，它经常成为 bug 来源——比如在异常分支中多调用了一次 `release()`，或者在 `finally` 块中无条件 release 而没有判断是否已经 release 过。

如果不需要引用计数行为，可以关闭：

```java
wl.setReferenceCounted(false);
wl.acquire();
// 现在任何一次 release() 都会直接释放，不管 acquire 了多少次
wl.release();
```

更安全的做法是使用带超时的 `acquire(long timeout)`：

```java
wl.acquire(10 * 60 * 1000L); // 最多持有 10 分钟
```

超时后系统自动释放，即使代码逻辑出了问题忘记 release，也不会无限持有。

### WorkSource：标记 wakelock 归属

`WorkSource` 是 wakelock 的一个重要但容易被忽略的参数。它允许一个 wakelock 的持有成本归因到特定的 App（UID），而不是全部算在声明 wakelock 的进程头上。

这在系统服务中特别常见：比如 `AlarmManager` 触发了一个 App 的闹钟，系统服务会持有 wakelock，但通过 `WorkSource` 把功耗归因标记为该 App 的 UID。这样在 `dumpsys batterystats` 中，用户能准确看到是哪个 App 导致了耗电。

[已验证: AOSP android-17-beta3, frameworks/base/core/java/android/os/WorkSource.java]

## Android 电源状态机与 Wakelock 的位置

Android 的设备电源状态可以用一个简化的状态机来描述：

```
Awake（屏幕亮）
  ↓ 用户按电源键 / 超时
Screen Dim
  ↓ 超时
Screen Off（CPU 仍在运行）
  ↓ 无活跃 wakelock
Sleep / Suspend（CPU 停止，功耗极低）
```

`PARTIAL_WAKE_LOCK` 的作用点在"Screen Off → Sleep"这个转换上。只要还有活跃的 partial wakelock，系统就不会进入 Sleep 状态。屏幕可以正常关闭，但 CPU 继续运行。

在 Perfetto 中，我们可以在 Power 相关的 track 中看到这些状态变化：

- `Screen On/Off` track：屏幕亮灭
- `CPU Idle` track：CPU 是否进入低功耗 idle 状态
- `PowerManagerService` track：可以看到 wakelock 的 acquire/release 事件

[待补充：Perfetto 中 PowerManagerService wakelock track 的截图]

### Doze 模式对 Wakelock 的压制

Android 6.0（API 23）引入了 Doze 模式，它的核心思想是：设备静止不动 + 屏幕关闭 + 未充电 → 逐步限制后台活动。

在 Doze 的 maintenance window（维护窗口）之外，系统会**忽略大部分 wakelock**。因此即使 App 持有 partial wakelock，CPU 也不会被唤醒。只有以下情况例外：

- `setAndAllowWhileIdle()` / `setExactAndAllowWhileIdle()` 触发的 Alarm
- 来自高优先级 Firebase Cloud Message 的推送
- `setAlarmClock()` 设置的闹钟（系统保证在 Doze 中也能触发）

Doze 的维护窗口间隔随时间递增：初始约 10 分钟，然后逐步延长到 30 分钟、60 分钟……这种设计让后台 App 的功耗在长时间静置后趋近于零。

### App Standby Bucket 的影响

Android 9（API 28）引入了 App Standby Bucket，根据 App 的使用频率将其分为不同桶：

- **Active**：正在使用，无限制
- **Working Set**：经常使用，轻度限制
- **Frequent**：偶尔使用，中等限制
- **Rare**：极少使用，严格限制（包括 wakelock 配额）
- **Restricted**：行为异常的 App，极端限制

从 Rare 桶开始，系统会对 App 的 wakelock 行为施加配额限制。到了 Restricted 桶，App 持有 wakelock 的能力可能被大幅削减。这是 Android 功耗治理体系从"被动监控"到"主动配额"转变的关键一环。

[已验证: 官方文档, developer.android.com/topic/performance/appstandby]

## 内核 Wakelock 与用户态 Wakelock

Android 的 wakelock 有两层：用户态（App/Framework 层）和内核态（Kernel 层）。理解这两层的关系，是分析底层功耗问题的关键。

### 内核的 wakeup_sources 机制

Linux 内核本身没有 "wakelock" 这个概念——它用的是 `wakeup_sources`。每个 wakeup_source 代表一个可以阻止系统进入 suspend 的实体，记录了以下信息：

- 名称（name）
- 活跃时间（active_time / total_time）
- 阻止 suspend 的累计时间（prevent_sleep_time）
- 事件计数（event_count）

可以通过 `/sys/kernel/debug/wakeup_sources` 查看当前系统中所有 wakeup_source 的状态：

```bash
$ adb shell cat /sys/kernel/debug/wakeup_sources
name            active_count     event_count      wakeup_count     expire_count     active_since     total_time       max_time         last_change
eventlog        12345            12345            12345            0                0                123456.78        0.123            1234567890
alarmtimer      890              890              890              0                0                23456.78         0.456            1234567890
...
```

这个文件是分析内核级功耗问题的入口。如果某个 wakeup_source 的 `prevent_sleep_time` 异常大，说明它长时间阻止了系统进入 suspend。

[已验证: Linux kernel documentation, Documentation/ABI/testing/sysfs-kernel-wakeup_sources]

### 用户态 wakelock 到内核的映射

当 App 调用 `PowerManager.WakeLock.acquire()` 时，调用链经过 PowerManagerService 最终到达内核：

1. `PowerManagerService` 将 wakelock 信息写入 `/sys/power/wake_lock`
2. 内核创建对应的 wakeup_source
3. `release()` 时，PowerManagerService 写入 `/sys/power/wake_unlock`
4. 内核注销对应的 wakeup_source

所以用户态的每个 wakelock 在内核中都有对应的 wakeup_source。但反过来不成立——内核中很多 wakeup_source 是内核组件自己创建的，与用户态 wakelock 无关：

- **Binder 驱动**：等待 IPC 事务时持有
- **Alarm 驱动**：alarmtimer 触发时持有
- **Input 设备**：触摸屏 / 按键事件处理时持有
- **Modem / RIL**：通信模块工作时持有
- **USB / 蓝牙**：外设连接时持有

这些内核 wakeup_source 可以通过 `/sys/kernel/debug/wakeup_sources` 查看，但不会出现在 `dumpsys batterystats` 的用户态统计中。

### 用户态泄漏导致内核无法释放

一个常见的功耗问题链：App 持有 partial wakelock → App 进程卡死或泄漏 → wakelock 永远不释放 → 内核的 wakeup_source 一直活跃 → 系统 无法 suspend → 电池快速耗尽。

虽然 PowerManagerService 注册了 `DeathRecipient` 来在进程死亡时自动释放 wakelock，但如果进程还活着（只是逻辑上泄漏），系统不会自动干预。这就是为什么 Play Store 的惩罚政策关注的是"24 小时内累计超过 2 小时"这个指标，而不是单次持有时间——系统需要给合法使用留出空间，但累计时间过长几乎一定意味着问题。

## Wakelock 泄漏的常见模式与诊断

### 四种常见泄漏模式

**模式 1：异常路径未 release**

```java
WakeLock wl = pm.newWakeLock(PARTIAL_WAKE_LOCK, "MyApp:Sync");
wl.acquire();
try {
    doNetworkSync(); // 如果这里抛异常...
} finally {
    wl.release();    // ...finally 确保释放
}
```

这是最基本的防护——用 `try-finally` 确保任何路径都会 release。但在复杂代码中（多层回调、异步操作），`finally` 不一定覆盖所有路径。

**模式 2：异步回调未到达**

```java
wl.acquire();
networkClient.request(new Callback() {
    @Override public void onSuccess() {
        wl.release();  // 如果网络超时、服务器无响应，回调永远不来
    }
    @Override public void onFailure() {
        wl.release();  // 必须在 onFailure 中也 release
    }
});
```

网络请求的超时和错误处理必须覆盖 wakelock 的 release。

**模式 3：生命周期不匹配**

在 `Activity.onResume()` 中 acquire，在 `onPause()` 中 release。但如果 Activity 因为配置变更被重建，`onPause()` 中的 release 和新 Activity 的 `onResume()` 中的 acquire 之间可能出现间隙，或者重复 acquire 导致引用计数错误。

**模式 4：后台服务长期持有**

这是最严重也最常见的模式。App 进入后台后，Foreground Service 或后台 Service 持有 wakelock 不释放，导致设备在屏幕关闭后 CPU 仍然全速运行。

### Battery Historian 中的可视化

Battery Historian 是分析 wakelock 问题的第一站。使用流程：

```bash
# 1. 重置电池统计
adb shell dumpsys batterystats --reset

# 2. 复现问题场景（让设备运行一段时间）

# 3. 导出 bugreport
adb bugreport bugreport.zip

# 4. 上传到 Battery Historian（本地或 https://bathist.ef.lc/）
```

在 Battery Historian 的时间线上，wakelock 显示在 top bar 区域。如果某个 App 的 wakelock 条目在屏幕关闭后长时间存在（特别是整段时间都是连续的），几乎可以确定存在问题。

[待补充：Battery Historian wakelock 时间线截图]

### dumpsys batterystats 解读

`dumpsys batterystats` 输出中，wakelock 相关的关键信息：

```bash
$ adb shell dumpsys batterystats | grep -A5 "Wake lock"

# 每个 UID 的 partial wakelock 统计
UID u0a123:
  Wake lock MyApp:Sync: ACQUIRED 2026-04-07 01:23:45
  Total partial wakelock time: 2h 15m 30s    # ← 这个值是关键
  Full wakelock time total: 0ms
```

关注三个维度：
- **全量时间（Total partial wakelock time）**：该 wakelock 累计持有多久
- **持有次数**：acquire 被调用了多少次
- **后台时间**：在 App 处于后台时的 wakelock 时间——这是 Play Store 惩罚政策关注的指标

[已验证: 官方文档, developer.android.com/studio/profile/battery-historian]

### Perfetto 中的 wakelock 分析

Perfetto 可以捕获 wakelock 事件，提供比 Battery Historian 更精确的时间维度分析：

```bash
# 抓取包含 wakelock 事件的 trace
adb shell perfetto -c - --txt <<EOF
buffers: {
    size_kb: 63488
}
data_sources: {
    config {
        name: "android.power"
        android_power_config {
            battery_polls_ms: 1000
            collect_power_rails: true
        }
    }
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "power/wakeup_source_activate"
            ftrace_events: "power/wakeup_source_deactivate"
        }
    }
}
duration_ms: 60000
EOF
```

在 Perfetto UI 中：
- `android.power` track 显示 wakelock 的 activate/deactivate 事件
- 可以用 SQL 查询精确分析持有时间：

```sql
-- 查询所有 wakelock 的持有时长
SELECT
    name,
    COUNT(*) as acquire_count,
    SUM(dur) / 1e6 as total_ms
FROM track t
JOIN slice s ON s.track_id = t.id
WHERE t.name GLOB '*wakelock*'
GROUP BY name
ORDER BY total_ms DESC;
```

[待验证: Perfetto android.power data source 在 Android 17 中的完整支持情况]

## AlarmManager 与 Wakelock 的关系

### 每次 Alarm 触发都持有 Wakelock

AlarmManager 是 wakelock 的一个重要间接来源。当 Alarm 触发时：

1. 内核 alarmtimer 驱动产生中断，唤醒 CPU
2. AlarmManagerService 接收到事件，通过 `PendingIntent.send()` 发送广播
3. 系统持有 wakelock，直到 `BroadcastReceiver.onReceive()` 返回
4. `onReceive()` 返回后，系统释放 wakelock

这里有一个关键细节：`onReceive()` 在主线程执行，系统自动持有 wakelock 保证它运行完成。但如果 `onReceive()` 中启动了异步操作（如启动 Service），系统 wakelock 在 `onReceive()` 返回时就释放了，Service 可能还没来得及启动，CPU 就又睡了。

过去用 `WakefulBroadcastReceiver`（已废弃）来解决这个问题，现在推荐的做法是：

- 轻量操作：直接在 `onReceive()` 中完成
- 重操作：使用 `WorkManager`，让系统管理 wakelock 生命周期

### Android 17 的 OnAlarmListener 回调变体

Android 17 引入了 `AlarmManager.setExactAndAllowWhileIdle()` 的 `OnAlarmListener` 回调变体，与传统 `PendingIntent` 方式有本质区别：

| 维度 | PendingIntent | OnAlarmListener |
|------|--------------|-----------------|
| 调用方式 | 跨进程 IPC → 启动 Receiver/Service | 进程内直接回调 |
| 组件生命周期 | 需要 instantiate BroadcastReceiver 或 Service | 无组件启动开销 |
| Wakelock 时长 | 从 IPC 到 onReceive() 返回 | 仅回调函数执行期间 |
| 持久化 | 进程被杀后仍可触发（系统持有 PendingIntent） | 不持久化，进程被杀则丢失 |
| 实例规则 | 无限制 | 每个 OnAlarmListener 同一时刻只能关联一个 alarm |

OnAlarmListener 的功耗收益主要来自两点：
- 省去了跨进程 IPC 的开销（Binder 调用 + Intent 解析 + 组件实例化）
- 缩短了 wakelock 的持有窗口（只有回调执行期间，而不是整个组件生命周期）

适用场景：配合长期运行的 Foreground Service 使用（确保进程存活），如即时通讯的心跳、医疗设备的定时上报。

[已验证: 官方文档, android.com — AlarmManager OnAlarmListener API Android 17]

### Play Store 的 Wakelock 惩罚政策

2026 年 3 月 1 日生效，Google 与 Samsung 联合制定。核心规则：

- **阈值**：非豁免 partial wake lock 累计 > 2 小时/24 小时 AND 影响 > 5% 用户 session（28 天窗口）
- **惩罚**：Play Store 搜索/推荐降权 + App 详情页显示「可能加速耗电」警告标签
- **豁免类型**：音频播放、位置访问、用户主动发起的数据传输（通过 UIDT API 声明）
- **开发者工具**：Play Console → Android Vitals → Wake Lock 指标

这个政策的实质是：Google 从"建议最佳实践"转向"强制执行配额"。对于开发者来说，要么优化 wakelock 使用，要么面临分发量下降。

[已验证: googleblog.com + android.com — Play Store wakelock policy 2026-03-01]

## Wakelock 的替代方案与最佳实践

### WorkManager：系统管理的 Wakelock

WorkManager 是 Jetpack 提供的后台任务调度库，它内部管理 wakelock 的整个生命周期。开发者不需要手动 acquire/release：

```kotlin
val uploadWork = PeriodicWorkRequestBuilder<UploadWorker>(15, TimeUnit.MINUTES)
    .setConstraints(Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .setRequiresBatteryNotLow(true)
        .build())
    .build()

WorkManager.getInstance(context).enqueue(uploadWork)
```

WorkManager 会根据设备状态（电量、网络、Doze 模式、App Standby Bucket）自动选择最佳执行时机，并在任务执行期间持有必要的 wakelock，执行完毕后立即释放。

与手动管理 wakelock + AlarmManager 的组合相比，WorkManager 的优势：
- 自动处理 Doze 模式和 App Standby 的限制
- 任务持久化，设备重启后自动重新调度
- 内置退避策略和重试机制
- 系统可以根据整体负载做全局调度优化

[已验证: 官方文档, developer.android.com/topic/libraries/workmanager]

### Foreground Service 与 Wakelock

Android 12+ 对 Foreground Service 引入了严格的限制：
- 必须显示通知，让用户知道有前台任务在运行
- 从后台启动 Foreground Service 受到严格限制
- Android 14+ 进一步限制了前台服务类型

Foreground Service 本身会持有 wakelock（由 ActivityManagerService 管理），不需要 App 手动获取。如果在 Foreground Service 中又手动 acquire 了 partial wakelock，属于重复持有，反而增加了泄漏风险。

### Coroutine + Lifecycle-aware 封装

对于需要在组件生命周期内短暂持有 wakelock 的场景，可以用 lifecycle-aware 的封装：

```kotlin
class WakeLockManager(private val context: Context) {
    private val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
    private var wakeLock: PowerManager.WakeLock? = null

    fun withWakeLock(block: suspend () -> Unit) {
        val wl = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK, "MyApp::WakeLockManager"
        ).apply { acquire(10 * 60 * 1000L) /* 安全超时 */ }
        wakeLock = wl
        try {
            block()
        } finally {
            if (wl.isHeld) wl.release()
            wakeLock = null
        }
    }
}
```

这种模式用 `try-finally` 保证释放，设置超时作为兜底，且将 wakelock 的 acquire/release 与协程的生命周期绑定。

### Android 16+ 后台执行配额

Android 16 引入了更精细的后台执行配额系统，从多个维度限制 App 的后台行为：

- **Wakelock 配额**：每个 App Standby Bucket 有不同的 wakelock 时间窗口
- **Alarm 配额**：限制 `setExactAndAllowWhileIdle()` 的调用频率
- **Job 配额**：限制 JobScheduler 任务的执行时间和频率
- **网络配额**：限制后台网络访问的频率和带宽

这些配额由 `DeviceIdleController` 和 `AppStandbyController` 联合管理，在 `dumpsys deviceidle` 和 `dumpsys appstandby` 中可以查看当前状态。

[待验证: Android 16 后台执行配额的具体数值和阈值]

### 从显式 Wakelock 迁移到系统管理

Google 官方推荐的迁移路径：

1. **定时任务** → `WorkManager`（Jetpack）
2. **延迟任务** → `WorkManager` + 约束条件
3. **精确定时** → `AlarmManager.setExactAndAllowWhileIdle()`（Android 17+ 优先用 `OnAlarmListener`）
4. **长期运行任务** → `Foreground Service`（配合通知）
5. **用户主动的数据传输** → `UIDT (User-Initiated Data Transfer) API`

核心原则：**让系统管理 wakelock 生命周期，而不是 App 手动管理**。系统的全局视角可以做出比单个 App 更优的调度决策。

## 与其他章节的关系

Wakelock 不是一个孤立的话题，它与全书多个章节紧密关联：

- **§5.6 Android 功耗管理**：wakelock 是 Android 功耗管理体系的核心机制之一，与 Doze、App Standby、Battery Saver 共同组成系统的功耗防线
- **§5.8 后台执行限制与优化**：WorkManager、JobScheduler 等后台调度框架内部都管理了 wakelock，了解 wakelock 机制有助于理解这些框架为什么比手动管理更安全
- **§11.1 Android 功耗模型**：wakelock 直接影响功耗模型中的 CPU 活跃时间
- **§11.2 App 耗电优化**：Play Store 的惩罚政策是 App 层面优化的直接驱动力
- **§13.5 Perfetto 专题解读**：wakelock 的 Perfetto SQL 分析方法是 Trace 分析的常用技巧

## 版本演进

| 版本 | 变更 | 影响 |
|------|------|------|
| Android 1.5 | 引入 PowerManager.WakeLock | 基础 API |
| Android 6.0 (API 23) | Doze 模式 | maintenance window 外忽略 wakelock |
| Android 9 (API 28) | App Standby Bucket | 不同桶的 wakelock 配额不同 |
| Android 12 (API 31) | Foreground Service 限制 | FGS 启动受限，通知强制 |
| Android 12 (API 31) | `SCHEDULE_EXACT_ALARM` 权限 | 精确闹钟需要声明权限 |
| Android 14 (API 34) | 前台服务类型 | 必须声明服务类型 |
| Android 16 (API 36) | 后台执行配额细化 | 多维度限制后台行为 |
| Android 17 (API 37) | `OnAlarmListener` 回调变体 | 进程内回调，缩短 wakelock 持有时长 |
| 2026-03 | Play Store Wakelock 惩罚政策 | 2h/24h 阈值，搜索降权 |

## 常见问题与误区

**误区 1："wakelock 持有时间短就没事"**

即使每次只持有几秒，如果频率很高（每分钟触发一次），24 小时累计也可能超过 2 小时阈值。Play Store 的惩罚看的是累计值，不是单次时间。

**误区 2："Foreground Service 不需要 wakelock"**

正确。Foreground Service 本身由 AMS 管理了 wakelock，不需要 App 手动获取。如果同时手动持有 partial wakelock，属于冗余操作，还增加了泄漏风险。

**误区 3："用 WorkManager 就完全不用担心 wakelock 了"**

大部分情况下是这样，WorkManager 内部管理了 wakelock。但如果 WorkManager 的 Worker 内部又手动 acquire 了 wakelock（比如某个第三方 SDK 会这么做），还是需要关注。

**误区 4："PowerManagerService 持有的 wakelock 是系统问题"**

`dumpsys batterystats` 中看到 `PowerManagerService` 持有大量 wakelock 时间，常常会被误认为是系统 bug。很多时候 PowerManagerService 只是代理，它通过 WorkSource 代表其他 App 记账。需要进一步查看是哪个 App 的 wakelock 归因到了 PMS。

## 参考资料

### AOSP 源码路径
- `frameworks/base/core/java/android/os/PowerManager.java` — WakeLock API 定义
- `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java` — 服务端实现
- `frameworks/base/core/java/android/os/WorkSource.java` — 功耗归因
- `kernel/power/wakelock.c` — 内核 wakelock 实现（旧版）
- `kernel/drivers/base/power/wakeup.c` — 内核 wakeup_source 实现（当前）
- `frameworks/base/services/core/java/com/android/server/AlarmManagerService.java` — Alarm 触发与 wakelock

### 官方文档
- [PowerManager API Reference](https://developer.android.com/reference/android/os/PowerManager)
- [Doze 和 App Standby 优化](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [WorkManager 指南](https://developer.android.com/topic/libraries/workmanager)
- [Battery Historian](https://developer.android.com/studio/profile/battery-historian)
- [Android Vitals — Wake Locks](https://developer.android.com/topic/performance/vitals/wakelock)

### 研究素材
- `intake/research-feeds/2026-04-06-07-android17-power-management-wakelock-policy-aod-minmode.md` — Android 17 功耗新特性 + Play Store 政策
