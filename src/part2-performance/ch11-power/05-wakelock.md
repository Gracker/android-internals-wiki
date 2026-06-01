---
title: "Wakelock 机制与功耗分析"
section: "11.5"
chapter: "11.5"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [wakelock, power, battery, alarmmanager, doze, batterystats, kernel-wakelock]
related_chapters: ["5.6", "5.8", "11.1", "11.2", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
drafted_date: "2026-04-07"
drafted_by: "openclaw-task2a"
gap_source: "研究素材+AOSP结构+官方文档+读者需求"
last_verified: "2026-05-28"
last_verified_against: "AOSP android-17-beta3；Android Developers excessive partial wake locks docs 2026-05-19；Android Developers Blog 2025-10-02"
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
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/schedule-exact-alarms"
  - type: official
    path: "https://source.android.com/docs/core/power/systemsuspend"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/android-power-energy"
  - type: aosp
    path: "hardware/libhardware_legacy/power.cpp"
  - type: aosp
    path: "hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl"
reviewed_at: "2026-05-11T19:05:00+08:00"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-28"
last_task9_at: "2026-05-28T03:32:12+08:00"
last_task2b_at: "2026-05-28T00:50:00+08:00"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
task9_review_notes: "2026-04-28 task9 deep-review: needs-rework。P0 2 / P1 0 / P2 2。；2026-04-28 task6 re-review: pass-light-edit，L1/L2 通过，代码块语言标签系统性缺失已记录；2026-04-29 task9 re-review: needs-rework，P0 2 / P1 0 / P2 2。；2026-05-01 task9 re-review: needs-rework，P0 4 / P1 0 / P2 1。；2026-05-05 17:38 task9 deep-review: needs-rework。P0 2 / P1 1 / P2 0；详见 logs/deep-review/2026-05-05-17-deep-review.md。；2026-05-15 task9 deep-review: needs-rework。P0 1 / P1 0 / P2 0；新增问题已写入 queue，等待 Task2B 回炉。；2026-05-16 Task9 deep-review: needs-rework。P0 0 / P1 1 / P2 1；ADPF 非游戏场景中 GameManager/GameState.MODE_CONTENT 与 setPreferPowerEfficiency 语义边界需修正，详见 logs/deep-review/2026-05-16-16-deep-review.md。；2026-05-28 Task2B：已收窄 setPreferPowerEfficiency 与 GameManager/GameState 语义边界，等待 Task6/Task9 复审。；2026-05-28 Task9 auto-fix：收窄 Android Vitals excessive partial wake lock 豁免口径，移除搜索降权和 CPU 全速运行的过度表述；回到 Task6 复审。 | 2026-05-28 Task9 deep-review: pass-tech-review。复核 Task6 回流后的技术口径；P0 0 / P1 0 / P2 0；queue 无 pending，自动晋升 finalized。"
review_notes: "2026-05-05 17:19 Task6：revisiting 写作复审通过；修复 14 处 L1/L2 表达/代码围栏问题，未新增回炉项，转 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-05-28-03-deep-review.md"
status: finalized
reviewed_by: openclaw-task6
reviewed_date: "2026-05-28"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
task9_result: pass-tech-review
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
last_task6_at: "2026-05-28T03:16:00+08:00"
last_task6_review_log: "logs/review/2026-05-28-03-review.md"
task6_l1_l2_fixes: 1
task6_l3_l4_issues: 0
task6_review_notes: "2026-05-28 Task6：Task9/Task2B 回流后写作复审通过；L1/L2 小修 1 处；无 L3/L4 回炉项，送 Task9 复核。"
review_round: 6
last_task9_autofix_at: "2026-05-28"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: "2026-06-01"
---

# 11.5 Wakelock 机制与功耗分析

Wakelock 是 Android 功耗分析中最常见的"嫌疑人"——它设计上是让 CPU 在需要时保持工作，但使用不当（忘记释放、异常路径泄漏、后台长期持有）就会直接导致电池快速耗尽。

2026 年 3 月起，Play Store 会对 excessive partial wake lock 指标超阈值的 App 影响重要发现入口曝光，并可能在详情页显示耗电警告标签。这个惩罚政策已把 wakelock 优化从"建议"变成了"合规要求"。

本节要回答几件事：Wakelock 的底层机制是什么？App 层的 wakelock 怎么映射到内核？出了问题怎么诊断？以及怎么避免 wakelock 变成功耗灾难。

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
- 🔸 Android 14+ `OnAlarmListener` 进程内精确回调的适用场景
- 🔸 内核 `wakeup_source` 观测与 `wakeup_sources` 文件解读
<!-- outline-end -->

## Wakelock 为什么存在：Android 需要“阻止睡眠”的场景

移动设备的 CPU 大部分时间应该处于低功耗状态。屏幕关闭后，如果没有任何工作要做，系统会在几百毫秒内依次进入浅度空闲、深度空闲，最终挂起（suspend）。在屏幕、基带和后台任务都静默的测试条件下，整机功耗可能降到 mA 级；具体数值要以设备电源轨或外接电流计实测为准。

但有些场景 CPU 必须保持工作：音乐播放、GPS 持续定位、即时通讯的长连接心跳、正在进行的下载任务。如果 CPU 在这些任务完成之前就进入 suspend，任务会被中断，用户体验直接受损。

Wakelock 就是 Android 为此设计的机制：它允许 App 或内核组件向系统声明"我现在需要 CPU 保持工作"。只要还有活跃的 wakelock，系统就不会进入 suspend。

Android 提供了以下 CPU/屏幕类 wake-lock level，后三种屏幕相关的已废弃：

| 类型 | 效果 | 状态 |
|------|------|------|
| `PARTIAL_WAKE_LOCK` | CPU 保持运行，屏幕可关闭 | 推荐使用 |
| `SCREEN_DIM_WAKE_LOCK` | 屏幕保持暗亮 | API 17 废弃 |
| `SCREEN_BRIGHT_WAKE_LOCK` | 屏幕保持全亮 | API 13 废弃 |
| `FULL_WAKE_LOCK` | CPU + 屏幕全亮 | API 17 废弃 |
| `PROXIMITY_SCREEN_OFF_WAKE_LOCK` | 配合距离传感器控制屏幕开关 | 可用 |

`PROXIMITY_SCREEN_OFF_WAKE_LOCK` 用于通话等场景：距离传感器检测到物体靠近时关闭屏幕，远离时重新点亮。它不参与 CPU 保活，走的是屏幕/传感器控制路径。屏幕类 wake-lock（`SCREEN_DIM`、`SCREEN_BRIGHT`、`FULL`）废弃的原因是：屏幕是否点亮应该由系统电源策略统一管理，而不是让 App 自行决定。现在如果需要保持屏幕常亮，正确做法是使用 `FLAG_KEEP_SCREEN_ON`（Window Flag）或 `android:keepScreenOn`（XML 属性），由 WindowManager 统一处理。

开发者主要关注的是 `PARTIAL_WAKE_LOCK`。它让 CPU 在屏幕关闭后仍然运行——这正是功耗问题的高发区，因为用户看不到屏幕亮着，不知道 App 还在消耗电量。

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

`WakeLock.acquire()` 的调用链是：

1. 客户端 `WakeLock`（`PowerManager.WakeLock`）在构造时就创建了 `mToken = new Binder()`，这个 IBinder token 代表本地 wakelock 对象
2. 客户端调用 `mService.acquireWakeLock(mToken, ...)` 将 token 传入 PowerManagerService
3. PowerManagerService 构造服务端 `WakeLock` 记录：`new WakeLock(lock, displayId, flags, tag, packageName, ws, ...)`
4. 在构造函数中执行 `linkToDeath()`：对客户端传入的 lock（Binder）注册 DeathRecipient
5. PowerManagerService 更新全局电源状态，根据所有活跃 wakelock 类型决定是否允许系统进入 suspend

要区分两个角色：客户端 `WakeLock` 的 `mToken` 在客户端创建后传入服务端；服务端的 `WakeLock`（PMS 内部类）才是 PMS 持有的记录，它对客户端传入的 IBinder 执行 linkToDeath()，从而在客户端进程死亡时自动清理记录。

[已验证: AOSP android-17-beta3, frameworks/base/core/java/android/os/PowerManager.java WakeLock 类构造函数；frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java WakeLock 内部类（line 5383-5438）+ acquireWakeLockInternal（line 1615-1659）]

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

```text
Awake（屏幕亮）
  ↓ 用户按电源键 / 超时
Screen Dim
  ↓ 超时
Screen Off（CPU 仍在运行）
  ↓ 无活跃 wakelock
Sleep / Suspend（CPU 停止，功耗极低）
```

`PARTIAL_WAKE_LOCK` 的作用点在"Screen Off → Sleep"这个转换上。只要还有活跃的 partial wakelock，系统就不会进入 Sleep 状态。屏幕可以正常关闭，但 CPU 继续运行。

在 Perfetto 里，电源状态与 wakelock 需要分开看：

- `Screen On/Off` track：屏幕亮灭
- `CPU Idle` track：CPU 是否进入低功耗 idle 状态
- `linux.ftrace` 的 `power/wakeup_source_activate` / `power/wakeup_source_deactivate`：是谁在什么时刻阻止了 suspend

framework 层的 `PowerManagerService` 处理片段有时能在 system trace 的 slices 里看到，但更稳定的 wakelock 原始事件仍以 ftrace 为准。

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
- **Rare**：极少使用，Jobs / Alarms 进入更严格配额；wakelock 主要受 Doze 和后台入口间接约束
- **Restricted**：行为异常的 App，极端限制

从 Rare 桶开始，App 的后台执行受到严格限制，但 **wakelock 本身没有直接配额限制**。关键机制：

- **Jobs / Alarms**：有 `QuotaController` / `AlarmManagerService` 的明确配额系统（RESTRICTED bucket 约 10 分钟/天 Jobs，1 次/天 Alarm）
- **Wakelock**：**无等效配额机制**，RESTRICTED bucket 的限制主要通过：
  1. `enforceWakeLockTimeout()` 强制超时（单次持锁最长约 1 分钟，不是累计配额）
  2. Doze 模式下非白名单 App 的 partial wakelock 会被完全忽略
  3. Jobs 配额受限 → 后台工作量减少 → 持锁场景间接减少

> 源码核对后的结论：App Standby Bucket 对 wakelock 的限制是间接约束，不存在类似 Jobs `QuotaController` 的直接配额系统。`RESTRICTED_WAKELOCK_MAX_TIMEOUT` 是单次超时限制，不是累计配额限制。详见调研报告 `2026-04-22-app-standby-bucket-wakelock-restrictions.md`。

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

用户态 wakelock 到内核 wakeup_source 的映射路径随 Android 版本发生了变化，需要分开讨论：

**Android 10 之前（旧版路径）：**

`PowerManagerService` 直接通过 `libpower` 库向 `/sys/power/wake_lock` 写入 wakelock 名称，内核在 `kernel/power/wakelock.c` 中根据写入的字符串创建对应的 wakeup_source。`release()` 时向 `/sys/power/wake_unlock` 写入同一名称，内核注销对应的 wakeup_source。

**Android 10 起（现代路径）：**

Android 10 引入 `SystemSuspend` 服务（`system_suspend` HIDL/AIDL 服务），完全替代了旧的 libsuspend 直写路径。用户态进程不再直接操作 `/sys/power/wake_lock`，而是通过 `libpower` / `system_suspend` 申请和释放用户态 wakelock。`system_suspend` 有两个观察点：

- 主线程处理 Binder 请求，维护 suspend counter
- suspend 线程先读 `/sys/power/wakeup_count`，再拿锁并等待 counter 归零；随后把刚读到的 wakeup_count 原样写回，再写入 `"mem"` 到 `/sys/power/state`
- 如果写回 wakeup_count 失败，说明这一小段窗口里出现了新的唤醒事件，本轮 suspend 会被放弃，线程回到循环起点重试

这套 `wakeup_count` 握手机制就是为了避免"刚准备 suspend，硬件又来了一个 wakeup event"这种竞态。`SystemSuspend` 负责用户态 wakelock 的引用计数与进入 suspend 的时机协调，内核 `wakeup_source` 仍然继续记录最终阻止 suspend 的实体。

排查时可以先看 SystemSuspend 服务状态：

```bash
adb shell dumpsys suspend_control
```

输出能看到 active wakelock / suspend blocker 相关计数时，先把这些名字和 `/sys/kernel/debug/wakeup_sources`、`dumpsys batterystats --history` 放到同一时间窗口里比较。前者回答“用户态谁还在阻止 suspend”，后者回答“内核最终被哪个 wakeup_source 唤醒或阻止”。不同厂商可能裁剪字段名，字段缺失时回到 debugfs 和 bugreport。

**不需要 wakelock 的内核 wakeup_source：**

内核中许多 wakeup_source 由内核组件自行创建，与用户态 wakelock 完全无关：

- **Binder 驱动**：等待 IPC 事务时持有
- **Alarm 驱动**：alarmtimer 触发时持有
- **Input 设备**：触摸屏 / 按键事件处理时持有
- **Modem / RIL**：通信模块工作时持有
- **USB / 蓝牙**：外设连接时持有

这些内核 wakeup_source 可以通过 `/sys/kernel/debug/wakeup_sources` 查看，但不会出现在 `dumpsys batterystats` 的用户态统计中。

### 用户态泄漏导致内核无法释放

一个常见的功耗问题链：App 持有 partial wakelock → App 进程卡死或泄漏 → wakelock 永远不释放 → 内核的 wakeup_source 一直活跃 → 系统 无法 suspend → 电池快速耗尽。

虽然 PowerManagerService 注册了 `DeathRecipient` 来在进程死亡时自动释放 wakelock，但如果进程还活着（只是逻辑上泄漏），系统不会自动干预。这就是为什么 Play Store 的惩罚政策关注的是"24 小时内累计超过 2 小时"这个指标，而不是单次持有时间——系统需要给合法使用留出空间，但累计时间过长几乎一定意味着问题。

### PowerManagerService 功耗路径：WakeLock / SystemSuspend / Power HAL 的边界

Android 10 之后，PMS 的 suspend blocker 路径由 `SystemSuspend` 服务承接。PMS 仍在 Java 层维护 WakeLock 列表和 `mWakeLockSummary`，JNI 层仍暴露 `nativeAcquireSuspendBlocker()` / `nativeReleaseSuspendBlocker()`，但 `hardware/libhardware_legacy/power.cpp` 中的 `acquire_wake_lock()` 会通过 AIDL `android.system.suspend.ISystemSuspend/default` 获取 `IWakeLock`。旧版 `system/core/libsuspend/autosuspend.c` 只保留为 `autosuspend_ops` 包装，不再是现代 Android 中创建轮询线程并直接写 `/sys/power/state` 的实现入口。

这条路径要分成三件事看：App WakeLock 是否让 `PowerManagerService.WakeLocks` 这个 suspend blocker 活跃，系统是否允许 autosuspend，Power HAL 是否收到交互或性能 hint。三者相关，但不是同一条状态机。

#### Java WakeLock → SuspendBlocker → SystemSuspend

**源码位置**：
- `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java`
- `frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp`
- `hardware/libhardware_legacy/power.cpp`
- `system/hardware/interfaces/suspend/1.0/default/SystemSuspend.cpp`

应用调用 `PowerManager.WakeLock.acquire()` 后，PMS 内部的 `mWakeLockSummary` 会记录所有活跃 WakeLock 的摘要。状态变更时，PMS 持有或释放名为 `PowerManagerService.WakeLocks` 的 suspend blocker：

```cpp
// frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp
static void nativeAcquireSuspendBlocker(JNIEnv* env, jclass, jstring nameStr) {
    ScopedUtfChars name(env, nameStr);
    acquire_wake_lock(PARTIAL_WAKE_LOCK, name.c_str());
}

static void nativeReleaseSuspendBlocker(JNIEnv* env, jclass, jstring nameStr) {
    ScopedUtfChars name(env, nameStr);
    release_wake_lock(name.c_str());
}
```

当前实现里，`acquire_wake_lock()` 不再自己管理 `/sys/power/wake_lock` 文件，而是拿到 `ISystemSuspend` 服务并申请一个 AIDL `IWakeLock`：

```cpp
// hardware/libhardware_legacy/power.cpp
const auto suspendService = getSystemSuspendServiceOnce();
suspendService->acquireWakeLock(WakeLockType::PARTIAL, id, &wl);
```

`SystemSuspend` 维护用户态 wakelock 计数。只要计数不为 0，suspend 线程就不会进入写 `/sys/power/state` 的阶段。一个 App 的 partial WakeLock 在 PMS 侧合并成 `PowerManagerService.WakeLocks`，再通过 `SystemSuspend` 阻止 deep suspend；屏幕相关的 display blocker 仍由另一条路径管理。

#### SystemSuspend 的 autosuspend 线程

Android 10+ 的 autosuspend 主体在 `SystemSuspend.cpp`。它围绕 `wakeup_count` 做内核握手，取代旧文中“固定每 100ms 写一次 `/sys/power/state`”的简单轮询描述：

1. suspend 线程读取 `/sys/power/wakeup_count`。
2. 等待用户态 wakelock 计数归零。
3. 将之前读到的 `wakeup_count` 写回 `/sys/power/wakeup_count`。
4. 写入 `mem` 到 `/sys/power/state`，触发 suspend-to-RAM。
5. 如果第 3 步写回失败，说明窗口内出现了新的 wakeup event，本轮 suspend 放弃并重新开始。

这套握手避免了“刚准备 suspend，硬件唤醒事件已经到达”的竞态。调试时可以先看 SystemSuspend 服务：

```bash
adb shell dumpsys suspend_control
```

如果输出里能看到 active wakelock 或 suspend blocker 计数，把这些名称和 `/sys/kernel/debug/wakeup_sources`、`dumpsys batterystats --history` 放到同一时间窗口比较。SystemSuspend 回答“用户态谁还在阻止 suspend”，debugfs 回答“内核最终被哪个 wakeup_source 唤醒或阻止”。

#### nativeSetAutoSuspend 与 PowerManager.SuspendLockout

PMS 的 `nativeSetAutoSuspend()` 控制系统是否允许自动 suspend。当前 JNI 侧通过 `ISuspendControlServiceInternal` 启用 autosuspend；禁用 autosuspend 时，则通过 `ISystemSuspend` 持有一个内部 wakelock：

```cpp
// frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp
suspendControl->enableAutosuspend(autosuspendClientToken, &enabled);

suspendHal->acquireWakeLock(
    WakeLockType::PARTIAL,
    "PowerManager.SuspendLockout",
    &gSuspendBlocker);
```

`PowerManager.SuspendLockout` 是系统级 suspend 开关，不是某个 App 的 `PowerManager.WakeLock`。排查时看到这个名字，要先看屏幕状态、电源状态切换、启动阶段或系统服务逻辑，不要直接归因到业务 App 泄漏。

#### Power HAL 与 PowerHint 的版本边界

Power HAL 负责向厂商侧电源策略发送性能和模式 hint，和 wakelock 的“是否允许 deep suspend”不是同一件事。

| Android 版本 | Power HAL 入口 | 常见接口 | 说明 |
| --- | --- | --- | --- |
| Android 9 及之前 | HIDL `hardware/interfaces/power/1.0/IPower.hal` | `setInteractive()`、`powerHint()` | 旧接口，适合解释历史代码和旧设备行为 |
| Android 10-11 | HIDL 继续演进，PowerStats 逐步拆分 | `IPower`、`IPowerStats` | 功耗统计能力和性能 hint 开始分离 |
| Android 12+ | AIDL `hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl` | `setMode()`、`setBoost()`、`createHintSession()` | 当前主路径，ADPF / `PowerHintSession` 通过会话持续反馈工作负载 |

在现代 framework 里，PMS JNI 通过 `PowerHalController` 发送 `setMode(Mode::INTERACTIVE, ...)`、`setBoost(...)` 等调用。旧文档里的 `powerHint(INTERACTION, ...)` 仍有参考价值，但它描述的是 HIDL 时代的接口形态。分析 Android 14/16 设备时，应优先看 AIDL `IPower.aidl`、`IPowerHintSession.aidl` 与 `PowerHalController`。

#### 完整调用链总结

```text
App: PowerManager.newWakeLock(PARTIAL_WAKE_LOCK).acquire()
  ↓
PowerManagerService: 更新 WakeLock 记录和 mWakeLockSummary
  ↓
acquireSuspendBlockerLocked("PowerManagerService.WakeLocks")
  ↓
JNI: nativeAcquireSuspendBlocker("PowerManagerService.WakeLocks")
  ↓
hardware/libhardware_legacy/power.cpp: acquire_wake_lock()
  ↓
ISystemSuspend.acquireWakeLock(PARTIAL, "PowerManagerService.WakeLocks")
  ↓
SystemSuspend: 用户态 wakelock 计数增加
  ↓
计数归零之前，autosuspend 线程不会完成 wakeup_count 写回和 /sys/power/state=mem
```

屏幕关闭时还会并行发生两类动作：`nativeSetAutoSuspend(true)` 允许 autosuspend 工作；Power HAL 收到 `INTERACTIVE=false` 一类 mode/hint，用于调整 CPU/GPU/调度策略。前者决定系统能否进入 deep suspend，后者影响性能与功耗策略，不能混成一条 wakelock 调用链。

[已验证: AOSP `hardware/libhardware_legacy/power.cpp`、`SystemSuspend.cpp`、`IPower.aidl` 与 `PowerHalController` 路径]


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

这是最严重也最常见的模式。App 进入后台后，Foreground Service 或后台 Service 持有 wakelock 不释放，导致设备在屏幕关闭后仍无法进入 deep suspend；CPU 频率和 idle 深度仍由调度器、电源策略和实际负载决定。

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

Perfetto 可以从两个不同维度捕获电源相关事件，分别对应不同的数据源：

**数据源职责对比：**

| 数据源 | 用途 | 轨道/事件 |
|--------|------|-----------|
| `android.power` | 电池计数器与 power rail 功耗采样 | power rails 采样值（电压/电流/功率） |
| `linux.ftrace` + `power/wakeup_source_*` | 内核级 wakelock activate/deactivate 事件 | `power.wakeup_source_activate` / `power.wakeup_source_deactivate` |
| `linux.ftrace` + `power/wake_lock` | 内核 wakelock 直接操作（旧版路径） | `power.wake_lock` / `power.wake_unlock` ftrace 事件 |

wakelock activate/deactivate 事件（谁在什么时间持有/释放 wakelock）来自 `linux.ftrace` 的 ftrace 事件，不是 `android.power`。`android.power` 对应的是 battery counters / power rails 采样。

```bash
# 抓取内核 wakelock 事件 + power rail 采样的配置
adb shell perfetto -c - --txt <<EOF
buffers: {
    size_kb: 63488
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "power/wakeup_source_activate"
            ftrace_events: "power/wakeup_source_deactivate"
            buffer_size_kb: 4096
        }
    }
}
data_sources: {
    config {
        name: "android.power"
        android_power_config {
            battery_poll_ms: 1000
            collect_power_rails: true
        }
    }
}
duration_ms: 60000
EOF
```

在 Perfetto UI 中：
- `linux.ftrace` 的 `power.wakeup_source_activate` / `power.wakeup_source_deactivate` 事件出现在 ftrace 事件面板或 raw events 视图里，对应内核级 wakelock 的持有/释放时间
- `android.power` 的 battery poll 数据出现在 Power Rails 轨道中，显示各硬件模块的实时功耗
- 如果要算持有时长，需要在 SQL 层对 activate / deactivate 做配对；不要去 named slice 或 `android.power` 轨道里找 wakelock 事件

wakelock activate/deactivate 事件不会自动变成 named slice，而是保留为 ftrace 原始事件。分析时应该先用 ftrace 还原谁阻止了 suspend，再用 `android.power` 看功耗采样是否同步抬升。

[已验证: perfetto.dev/docs/data-sources/android-power-energy 等官方文档；android.power 对应 power rails 而非 wakelock 事件]

## AlarmManager 与 Wakelock 的关系

### 每次 Alarm 触发都持有 Wakelock

AlarmManager 是 wakelock 的一个重要间接来源。当 Alarm 触发时：

1. 内核 alarmtimer 驱动产生中断，唤醒 CPU
2. AlarmManagerService 接收到事件，通过 `PendingIntent.send()` 发送广播
3. 系统持有 wakelock，直到 `BroadcastReceiver.onReceive()` 返回
4. `onReceive()` 返回后，系统释放 wakelock

`onReceive()` 的关键点是：它在主线程执行，系统自动持有 wakelock 保证它运行完成。但如果 `onReceive()` 中启动了异步操作（如启动 Service），系统 wakelock 在 `onReceive()` 返回时就释放了，Service 可能还没来得及启动，CPU 就又睡了。

过去用 `WakefulBroadcastReceiver`（已废弃）来解决这个问题，现在推荐的做法是：

- 轻量操作：直接在 `onReceive()` 中完成
- 重操作：使用 `WorkManager`，让系统管理 wakelock 生命周期

### Android 14+ 的 OnAlarmListener 进程内精确回调

`OnAlarmListener` 这条 API 解决的是一类很具体的场景：调用方进程已经存活，只需要在本进程内收到一个精确回调，不需要系统替它冷启动组件，也不要求 alarm 在进程被杀后继续存在。

`AlarmManager.OnAlarmListener` 接口和 `setExact(int, long, String, OnAlarmListener, Handler)` 从 Android 7.0（API 24）起已在公开 SDK 中。Android 14（API 34）的变化在于精确闹钟权限口径：`SCHEDULE_EXACT_ALARM` 权限不适用于 `OnAlarmListener` 路径，这个例外在 Android 14 文档中被明确写入。`setExact(..., Executor, WorkSource, OnAlarmListener)` 与 `setExactAndAllowWhileIdle(..., Executor, WorkSource, OnAlarmListener)` 仍为 `@SystemApi`，需要 `UPDATE_DEVICE_STATS` 权限，普通 App 不可直接调用。

这条路径还有一个公开文档明确写出的权限例外：

> If the exact alarm is set using an `OnAlarmListener` object, the `SCHEDULE_EXACT_ALARM` permission isn't required.

这条例外成立的前提，正是 `OnAlarmListener` 只做进程内回调。系统不用替应用保管 `PendingIntent`，也不会在进程已经死亡时冷启动 `Receiver` / `Service`。因此，它适合"进程活着就回调，进程死了就算了"的精确定时；提醒、闹钟、日程这类要求持久化和冷启动的场景，仍然应该使用 `PendingIntent` 版本。

`setExactAndAllowWhileIdle(int, long, String, Executor, WorkSource, OnAlarmListener)` 在 Android 14/17 仍是 `@SystemApi`，面向系统应用，普通 App 不能直接调用。它把 `allowWhileIdle` 和 `OnAlarmListener` 放在同一个重载里，但约束没有变化：回调仍然发生在存活进程内。

| 维度 | PendingIntent | OnAlarmListener（公开 API） | setExactAndAllowWhileIdle + OnAlarmListener（@SystemApi） |
|------|--------------|----------------------------|--------------------------------------------------------|
| 触发方式 | 系统持有 `PendingIntent`，到点后分发组件 | 进程内直接回调 | 进程内直接回调 |
| 进程被杀后 | 仍可触发，系统可冷启动组件 | 直接丢失，不会冷启动进程 | 直接丢失，不会冷启动进程 |
| 持久化 | 有 | 无 | 无 |
| `SCHEDULE_EXACT_ALARM` | Android 12+ 通常需要 | 不需要 | 不需要该权限，但需要 `UPDATE_DEVICE_STATS` |
| 适用场景 | 闹钟、提醒、日程、需要冷启动的任务 | 进程内心跳、短周期采样、前台存活任务 | 系统级 idle 例外定时 |

适用公开 API 的判断标准很直接：进程必须大概率一直活着，回调逻辑必须够轻，业务也接受"进程被系统杀掉后这次 alarm 不补发"。

[已验证: developer.android.com/about/versions/14/changes/schedule-exact-alarms；AOSP android-17 `AlarmManager.java` 中 `OnAlarmListener` 与 `setExact(..., OnAlarmListener)` / `setExactAndAllowWhileIdle(..., OnAlarmListener)` 定义]

### Play Store 的 Wakelock 惩罚政策

2026 年 3 月正式生效。核心规则（来源：Android Vitals 官方文档）：

- **阈值**：非豁免 partial wake lock 在 24 小时内累计超过 2 小时，且超过 5% 的用户 session（28 天窗口）
- **惩罚**：Play Store 重要发现入口曝光受影响（如推荐位）+ App 详情页可能显示「可能加速耗电」警告标签
- **豁免类型**：音频播放、位置访问、JobScheduler user-initiated APIs；普通后台 Job / WorkManager 任务不能一概视为豁免
- **开发者工具**：Play Console → Android Vitals → Wake Lock 指标，可看各 wakelock 名称的 P90/P99 时长

这里"非豁免"的含义是：Android Vitals 明确豁免 audio、location、JobScheduler user-initiated APIs。App 自己通过 `PowerManager.WakeLock` 持有的 partial wakelock，以及未命中这些豁免条件的系统代持 wakelock，都要在 Play Console 里继续看 wakelock 名称、affected sessions 和持续时间。

[已验证: developer.android.com/topic/performance/vitals/wakelock（Android Vitals excessive wake lock 定义）；googleblog.com（Play Store 政策公告）]

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

关于 Foreground Service 是否持有 CPU wakelock，官方文档的表述是：Foreground Service 本身并不等同于持有 CPU wakelock。Foreground Service 向系统声明"有重要的用户可见任务在运行"，这提升了进程的存活优先级，但**不等同于阻止 CPU 进入 suspend**。

官方文档明确指出：

> If your app is running a foreground service and needs to keep the device awake, use a `PARTIAL_WAKE_LOCK` in conjunction with the foreground service.

即：如果 Foreground Service 需要在屏幕关闭后继续保持 CPU 运行，仍然需要显式获取 `PARTIAL_WAKE_LOCK`。

除了 wakelock 本身的生命周期管理，Android 15 还引入了更细粒度的功耗控制 API，让应用可以主动向系统声明能效偏好。两者解决的是不同问题——Foreground Service 解决的是进程被杀死的问题，wakelock 解决的是 CPU suspend 的问题。

因此，"Foreground Service 本身会持有 wakelock" 这个说法是不准确的。常见的使用方式是：Foreground Service + 通知 + 必要时显式获取 `PARTIAL_WAKE_LOCK`。

[已验证: developer.android.com — "Use wake locks" best practices: "If your app is running a foreground service and needs to keep the device awake, use a PARTIAL_WAKE_LOCK"]

### Coroutine + Lifecycle-aware 封装

对于需要在组件生命周期内短暂持有 wakelock 的场景，可以用 lifecycle-aware 的封装：

```kotlin
class WakeLockManager(private val context: Context) {
    private val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
    private var wakeLock: PowerManager.WakeLock? = null

    suspend fun withWakeLock(block: suspend () -> Unit) {
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

### Android 16+ 后台执行限制继续细化

Android 16 之后，后台执行限制继续细化，Alarm、Job、网络等后台入口的执行窗口和频率控制更严。对 wakelock 的约束，更多是通过 Doze、App Standby Bucket、后台启动限制、前台服务类型和 exact alarm 权限共同体现，而不是给应用一个单独可配置的 `wakelock quota` API。

排查这类问题时，`dumpsys deviceidle`、`dumpsys appstandby`、Alarm / Job 统计和 `batterystats` 需要一起看。

### 从显式 Wakelock 迁移到系统管理

Google 官方推荐的迁移路径：

1. **定时任务** → `WorkManager`（Jetpack）
2. **延迟任务** → `WorkManager` + 约束条件
3. **精确定时** → 需要持久化和冷启动时用 `PendingIntent` 版本；进程已存活且只要进程内回调时，可用 `setExact(..., OnAlarmListener)`
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
| Android 9 (API 28) | App Standby Bucket | 后台任务 / Alarm 配额更严；wakelock 受 Doze、单次超时和后台入口间接约束，无 Jobs 类累计配额 |
| Android 12 (API 31) | Foreground Service 限制 | FGS 启动受限，通知强制 |
| Android 12 (API 31) | `SCHEDULE_EXACT_ALARM` 权限 | 精确闹钟需要声明权限 |
| Android 14 (API 34) | 前台服务类型 | 必须声明服务类型 |
| Android 14 (API 34) | `OnAlarmListener` 精确闹钟权限例外明确写入文档 | `OnAlarmListener` 路径不需要 `SCHEDULE_EXACT_ALARM` 权限（API 24 即已存在），Android 14 在文档中正式明确了此例外；`setExactAndAllowWhileIdle` + `OnAlarmListener` 重载仍为 `@SystemApi` |
| Android 16 (API 36) | 后台执行限制继续细化 | Alarm / Job / 网络等后台入口约束更细 |
| 2026-03 | Play Store Wakelock 惩罚政策 | 2h/24h + 5% sessions / 28 天阈值，影响重要发现入口曝光 |

## 常见问题与误区

**误区 1："wakelock 持有时间短就没事"**

即使每次只持有几秒，如果频率很高（每分钟触发一次），24 小时累计也可能超过 2 小时阈值。Play Store 的惩罚看的是累计值，不是单次时间。

**误区 2："Foreground Service 不需要 wakelock"**

Foreground Service 提高的是进程存活优先级，不是 CPU 的唤醒状态。屏幕关闭后如果任务仍然需要持续运行，还是要显式获取 `PARTIAL_WAKE_LOCK`，或者把任务交给 WorkManager 等框架代持。只依赖 FGS，CPU 仍然可能进入 suspend。

**误区 3："用 WorkManager 就完全不用担心 wakelock 了"**

大部分情况下是这样，WorkManager 内部管理了 wakelock。但如果 WorkManager 的 Worker 内部又手动 acquire 了 wakelock（比如某个第三方 SDK 会这么做），还是需要关注。

**误区 4："PowerManagerService 持有的 wakelock 是系统问题"**

`dumpsys batterystats` 中看到 `PowerManagerService` 持有大量 wakelock 时间，常常会被误认为是系统 bug。很多时候 PowerManagerService 只是代理，它通过 WorkSource 代表其他 App 记账。需要进一步查看是哪个 App 的 wakelock 归因到了 PMS。


### Android 15 ADPF Power Efficiency Mode 与 PowerMonitor 能耗监测

Android 15（API 35）在 ADPF 中引入 **Power Efficiency Mode**，允许应用通过 `PerformanceHintSession` 声明线程应优先节能而非峰值性能。结合 `android.os.PowerMonitor` API，可以把性能提示和能耗观测放在同一条验证路径里。

#### PerformanceHintManager 与 Power Efficiency Mode

**源码位置**：`frameworks/base/core/java/android/os/PerformanceHintManager.java`（API 31+，Android 15 扩展）

`PerformanceHintManager`（Android 12 引入）允许应用向系统发送性能提示，辅助调度器和 Power HAL 估计工作负载。Android 15 新增 Power Efficiency Mode，通过 hint session 声明关联线程应优先节能，适用于长时后台工作负载。

核心 API：
- `createHintSession(int[] tids, long initialTargetNanos)` — 创建 hint session，`tids` 为关联线程 ID 数组（`int[]`，非 `long[]`），目标时长单位为纳秒
- `reportActualWorkDuration(long actualDurationNanos)` — 报告单次实际工作耗时（纳秒）
- `updateTargetWorkDuration(long targetDurationNanos)` — 更新目标工作时长（纳秒）
- `setPreferPowerEfficiency(boolean preferEfficiency)` — API 35 / `FLAG_ADPF_PREFER_POWER_EFFICIENCY`，声明会话线程可以按能效优先调度；是否迁移到效率核、降低频率或联动 GPU，由设备的 scheduler / Power HAL 实现决定。适用于后台长时工作负载（如同步、上传、压缩），不适合前台交互场景

Power Efficiency Mode 的语义是调度偏好：应用告诉系统，这组线程可以牺牲部分响应速度来换取能效。它的 API 契约不包含降频或 GPU 频率变化保证；实测时要同时看线程运行位置、CPU/GPU freq counter、rail 能耗和任务耗时。

#### PowerMonitor API（API 35 新增）

**源码位置**：`frameworks/base/core/java/android/os/PowerMonitor.java`

`PowerMonitor`（API 35）代表两类功耗监控实体：
- `POWER_MONITOR_TYPE_CONSUMER`（0）— 建模范畴，名称通用如 "GPU" / "MODEM"
- `POWER_MONITOR_TYPE_MEASUREMENT`（1）— 直接测量电源轨，设备特有，如 "S2S_VDD_G3D"

数据获取路径：
```text
SystemHealthManager.getSupportedPowerMonitors() → List<PowerMonitor>
SystemHealthManager.getPowerMonitorReadings(List<PowerMonitor>, OutcomeReceiver<PowerMonitorReadings>)
PowerMonitorReadings.getConsumedEnergy(PowerMonitor) → 微瓦秒（μWs）累计值
PowerMonitorReadings.getTimestampMillis(PowerMonitor) → 快照时刻的 elapsed realtime
```

`getConsumedEnergy()` 返回重启后累计能耗（μWs），不跨重启保留。测量的是 subsystem 级能耗，不受电池充放电状态影响。

#### IPowerStats HAL（Android 10+）

**源码位置**：`hardware/interfaces/power/stats/`（AOSP）

`IPowerStats HAL` 是底层数据源，替代旧版 `IPower.hal` 的统计功能。核心 API：
- `getRailInfo()` — 获取功耗轨元信息（名称、测量类型）
- `getEnergyData()` — 获取自启动以来的累计能耗数据

[已确认: 已按 Task9 结论修正——Perfetto 数据源名称统一为 `android.power` + `collect_power_rails: true`；`android_power_rails_counters` 仅作为 Trace Processor SQL 表名，不写成 data source name。]

主要消费者：Statsd（功耗归因）、Perfetto（`android.power` 数据源）、Batterystats（电池分析）。

#### Perfetto 端到端观测

Perfetto 通过 `android.power` 数据源暴露 rail 级功耗（trace processor SQL 表名为 `android_power_rails_counters`）：

```protobuf
android_power_config {
  battery_poll_ms: 1000
  collect_power_rails: true
}
```

数据存储为 PerfettoSQL 表 `android_power_rails_counters`。完整路径：

```text
应用调用 Power Efficiency Hint
  ↓
线程按能效优先调度；设备实现可能调整核心选择或频率
  ↓
IPowerStats HAL 累计能耗变化
  ↓
Perfetto android.power 数据源记录 rail 数据（SQL 表名 `android_power_rails_counters`）
  ↓
应用调用 SystemHealthManager.getPowerMonitorReadings()
  ↓
验证 Power Efficiency Mode 的实际效果
```


#### 非游戏场景的 ADPF 应用

ADPF 的适用范围包括游戏，也包括视频剪辑、AI 推理、后台批处理等 performance-intensive app。这类应用可以使用 hint session 描述工作负载：

| 场景 | 建议 API | 说明 |
|------|----------|------|
| 视频导出 | `createHintSession()` + `reportActualWorkDuration(...)` | 让系统看到周期性工作耗时，便于维持可持续吞吐 |
| 实时 AI 推理 | `reportActualWorkDuration(...)` / `reportActualWorkDuration(WorkDuration)` | Android 15 起可把 CPU/GPU 工作时长作为 hint session 输入，设备再决定是否联动调度 |
| 后台批处理 | `setPreferPowerEfficiency(true)` + `reportActualWorkDuration(...)` | 延迟不敏感时声明能效优先，再用耗时和能耗数据验证收益 |

`GameManager.setGameState(GameState)` 是游戏状态上报 API。`GameState.MODE_CONTENT` 表示游戏内当前展示的不是 gameplay 内容，例如广告、网页、文本或视频；普通视频、AI 推理和后台批处理应用不应把它当成通用内容类型声明。非游戏场景保留 `PerformanceHintManager`、Thermal API、PowerMonitor 和 Perfetto 观测路径即可。

> USB 充电场景下，电池计数器显示的是正向充电电流，不是设备真实功耗。官方建议使用专用 USB Hub 切断充电电路，以获得准确测量。

[已验证: developer.android.com — ADPF Power Efficiency Mode 官方文档；PerformanceHintManager.Session#setPreferPowerEfficiency；GameManager / GameState API Reference；PowerMonitor API Reference (API 35)；perfetto.dev/docs/analysis-sql/android-power-rails]

## 参考资料

### AOSP 源码路径
- `hardware/libhardware_legacy/power.cpp` — `acquire_wake_lock()` 到 `ISystemSuspend` 的桥接
- `frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp` — `nativeSetAutoSuspend()`、`PowerHalController` 调用入口
- `hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl` — 当前 Power HAL AIDL 接口
- `frameworks/base/core/java/android/os/PowerManager.java` — WakeLock API 定义
- `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java` — 服务端实现
- `frameworks/base/core/java/android/os/WorkSource.java` — 功耗归因
- `frameworks/base/core/java/android/app/AlarmManager.java` — `OnAlarmListener` 与 exact alarm 重载（Android 15+ 路径 `frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java`）
- `frameworks/base/services/core/java/com/android/server/AlarmManagerService.java` — Alarm 触发与 wakelock
- `kernel/power/wakelock.c` — 内核 wakelock 实现（旧版）
- `kernel/drivers/base/power/wakeup.c` — 内核 wakeup_source 实现（当前）
- `system/hardware/interfaces/suspend/1.0/default/SystemSuspend.cpp` — `SystemSuspend` 参考实现

### 官方文档
- [PowerManager API Reference](https://developer.android.com/reference/android/os/PowerManager)
- [Doze 和 App Standby 优化](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [WorkManager 指南](https://developer.android.com/topic/libraries/workmanager)
- [Android 14 精确闹钟变更](https://developer.android.com/about/versions/14/changes/schedule-exact-alarms)
- [SystemSuspend 文档](https://source.android.com/docs/core/power/systemsuspend)
- [Perfetto Android Power Energy](https://perfetto.dev/docs/data-sources/android-power-energy)
- [Battery Historian](https://developer.android.com/studio/profile/battery-historian)
- [Android Vitals — Wake Locks](https://developer.android.com/topic/performance/vitals/wakelock)

### 研究素材
- `intake/research-feeds/2026-04-06-07-android17-power-management-wakelock-policy-aod-minmode.md` — Android 17 功耗新特性 + Play Store 政策
