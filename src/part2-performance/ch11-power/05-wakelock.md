---
title: "WakeLock 机制与功耗分析"
section: "11.5"
chapter: "11.5"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [wakelock, power, battery, alarmmanager, doze, batterystats, kernel-wakelock]
related_chapters: ["5.6", "5.8", "11.1", "11.2", "11.3"]
last_verified: "2026-07-31"
last_verified_against: "AOSP android-17.0.0_r1；Android common kernel android17-6.18-2026-06_r6；Android Developers wake lock / Android vitals / AlarmManager docs 2026-07"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerManager"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals/excessive-wakelock"
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: blog
    path: "intake/research-feeds/2026-04-06-07-android17-power-management-wakelock-policy-aod-minmode.md"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/persistent"
  - type: official
    path: "https://developer.android.com/about/versions/14/changes/schedule-exact-alarms"
  - type: official
    path: "https://source.android.com/docs/core/power/systemsuspend"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/battery-counters"
  - type: aosp
    path: "hardware/libhardware_legacy/power.cpp"
  - type: aosp
    path: "system/hardware/interfaces/suspend/aidl/default/SystemSuspend.cpp"
  - type: kernel
    path: "drivers/base/power/wakeup.c"
  - type: kernel
    path: "drivers/base/power/wakeup_stats.c"
  - type: kernel
    path: "kernel/power/suspend.c"
status: "finalized"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
pipeline_stage: "ready-to-publish"
---

# 11.5 WakeLock 机制与功耗分析

WakeLock 解决一个很窄的问题：设备准备进入 system suspend（整机挂起）时，某段工作仍需要 CPU 继续执行。它不会让线程获得更多 CPU，也不会固定 CPU 频率，更不会替应用解决后台启动、网络访问或进程存活限制。

这组边界决定了排查方法。客户端对象显示 held（已持有），只能说明应用尚未调用 release（释放）；PowerManagerService 可能已经因电源策略禁用这把锁。BatteryStats 中的应用 tag（标签）、SystemSuspend 中的用户态锁和内核 `wakeup_source`（唤醒源）也属于不同的统计层级。

从 2026 年 3 月起，Google Play 已逐步依据 excessive partial wake lock（过度持有部分唤醒锁）指标调整应用在商店中的推荐和警告展示。排查功耗时还要关注线上质量指标，不能只看本地电流。

## 11.5.1 WakeLock 阻止的是哪一层睡眠

分析 CPU 低功耗状态时，至少要区分 CPU idle 与 system suspend：

- **CPU idle**：某个 CPU 没有 runnable task（已就绪、等待调度的任务）时进入 idle state（空闲状态）。持有 partial wake lock 不会强迫 CPU 持续执行指令。
- **System suspend**：整机经过设备挂起流程进入更深的低功耗状态。有效的 partial wake lock（只保持 CPU 可运行的唤醒锁）会阻止这一步。
- **硬件唤醒事件**：Alarm、按键、modem（蜂窝基带）、蓝牙或其他具备 wakeup 能力的设备可让系统从 suspend 返回。

下面的简图只表达 partial wake lock 的作用位置。

```text
屏幕关闭
   ↓
CPU 无任务时仍可进入各自的 idle state
   ↓
PowerManagerService 判断是否需要 CPU suspend blocker
   ├─ 需要：SystemSuspend 暂不发起 system suspend
   └─ 不需要：经过 wakeup_count 握手后进入 system suspend
```

图中的 suspend blocker 是用户态阻止整机挂起的计数锁，`wakeup_count` 握手用于确认准备挂起期间没有出现新的唤醒事件。

长时间持锁不代表 CPU 一直满负载，但会阻止整机进入更深的省电状态；锁内还有轮询、网络、定位或计算时，能耗会继续增加。即使单次持锁很短，触发过于频繁也可能让设备难以形成稳定的 suspend 区间。

### WakeLock level（级别）

| Level | 语义 | 应用建议 |
|---|---|---|
| `PARTIAL_WAKE_LOCK` | 屏幕可灭，CPU 不进入 system suspend | 只在专用 API 无法覆盖时短时使用 |
| `PROXIMITY_SCREEN_OFF_WAKE_LOCK` | 距离传感器靠近时控制屏幕关闭 | 通话等专用场景；先检查设备支持 |
| `SCREEN_DIM_WAKE_LOCK` | 保持屏幕暗亮 | API 17 废弃 |
| `SCREEN_BRIGHT_WAKE_LOCK` | 保持屏幕亮 | API 13 废弃 |
| `FULL_WAKE_LOCK` | 保持屏幕与设备唤醒 | API 17 废弃 |

需要让当前界面保持亮屏时，使用 `WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON` 或 View 的 `keepScreenOn`。这类状态会随窗口可见性由系统管理。`PROXIMITY_SCREEN_OFF_WAKE_LOCK` 主要控制显示，不应当作保持 CPU 唤醒的锁。

## 11.5.2 申请之前先检查专用 API

很多 Android API 已经在需要的执行窗口内代持 wake lock。应用额外申请一把锁，只会延长持有时间。

| 工作 | 优先机制 | wake lock 由谁管理 |
|---|---|---|
| 可延迟后台任务 | WorkManager / JobScheduler | 调度框架在 Job 执行期管理 |
| 用户发起的长时上传或下载 | user-initiated data transfer job（用户发起的数据传输任务） | JobScheduler |
| 普通下载 | DownloadManager | 系统 |
| 音频播放 | Media APIs；Media3 可配置 wake mode（唤醒模式） | 音频栈或播放器 |
| 定位 | LocationManager / Fused Location（融合定位） | 定位栈在采集与投递期管理 |
| 传感器批处理 | wake-up sensor（唤醒型传感器）或 batching（批量上报） | Sensor framework |
| 到点提醒 | AlarmManager | Alarm 投递期由系统管理 |
| 用户可见的连续自定义工作 | 合适类型的 Foreground Service；确需 CPU 连续运行时再配 partial wake lock | 应用负责显式锁 |

Foreground Service（前台服务，FGS）会提高进程重要性并展示通知，但不会自动阻止整机进入 suspend。直接持 partial wake lock 的后台工作通常也应处在用户可见的 FGS 中；若业务不适合 FGS，通常也不适合直接持锁。

## 11.5.3 应用层的安全持锁模式

应用必须在 Manifest（应用清单）中声明 `android.permission.WAKE_LOCK`。下面的同步工作示例使用稳定 tag、由单一对象负责申请和释放、设置超时保险，并在 `finally` 中释放锁。

```java
public final class CpuBoundExport {
    private static final String WAKE_LOCK_TAG =
            "com.example.export:CpuBoundExport";
    private static final long WAKE_LOCK_TIMEOUT_MS =
            TimeUnit.MINUTES.toMillis(10);

    public static void run(Context context) {
        PowerManager powerManager =
                context.getSystemService(PowerManager.class);
        PowerManager.WakeLock wakeLock = powerManager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                WAKE_LOCK_TAG);
        wakeLock.setReferenceCounted(false);
        wakeLock.acquire(WAKE_LOCK_TIMEOUT_MS);
        try {
            exportCurrentItem();
        } finally {
            if (wakeLock.isHeld()) {
                wakeLock.release();
            }
        }
    }
}
```

超时只用于限制故障时最长持锁多久，正常路径仍应尽早 release。超时时间需要覆盖合理的最慢执行时长；若任务经常接近超时，应改造成可恢复的分段任务，或改用调度 API。多个线程共享同一个非引用计数锁时，任意一次 release 都会解除此前的 acquire，因此这类封装必须由单一对象管理。

### 引用计数

`WakeLock` 默认启用引用计数。两次 `acquire()` 需要两次 `release()` 才会解除锁；release 次数过多会产生 under-lock（释放次数超过申请次数）异常。适合共享锁的代码要明确记录每个 owner（所有者），普通单任务更适合关闭引用计数并集中管理生命周期。

### Tag

稳定 tag 便于 BatteryStats 和 Android vitals（Android 线上质量指标）聚合：

- 使用硬编码的包名、类名或操作名；
- 不放邮箱、账号、设备 ID 等个人信息；
- 不追加时间戳、随机数或递增序号；
- 同一持锁点每次使用同一 tag。

系统发现 tag 可能包含个人信息时，诊断工具可能只显示 `_UNKNOWN`。高基数 tag，也就是同一持锁点产生大量不同 tag，也会让线上数据无法聚合。

### WorkSource

`WorkSource` 表示“这份工作替哪个 UID（应用用户标识）执行”，常见于系统服务或中间层。Android 17 的 `PowerManagerService.BinderService.acquireWakeLock()` 会在非空 `WorkSource` 上校验 `UPDATE_DEVICE_STATS` 权限。普通应用不能靠它更改归因，也不应把成本转给其他 UID。

PowerManagerService 根据 owner 与 WorkSource 保存归因，Notifier（电源事件通知组件）再把 acquire/release 事件交给 BatteryStats。某个系统组件持有锁，不代表成本一定计在该系统组件名下；排查时要结合 WorkSource、UID 和 tag。

### held 与 enabled

Android 13 / API 33 增加 `WakeLockStateListener`。下面的监听只用于观察服务端是否仍尊重这把锁。

```java
if (Build.VERSION.SDK_INT >= 33) {
    wakeLock.setStateListener(
            context.getMainExecutor(),
            enabled -> Log.i(
                    "WakeLockState",
                    "serverEnabled=" + enabled
                            + ", clientHeld=" + wakeLock.isHeld()));
}
```

`isHeld()` 表示客户端尚未完成 release；`enabled=false` 表示 Framework 服务因电源 allowlist（允许列表）、配额、cached（缓存进程）/frozen（冻结进程）状态或其他策略暂时忽略这把锁。监听状态不能替代 release；策略重新允许后，仍处于 held 状态的锁可能再次生效。

## 11.5.4 Android 17 Framework 调用链

### PowerManager.WakeLock 到 PowerManagerService

下面的调用链省略日志与权限检查，只保留客户端和服务端如何创建、持有及删除锁记录。

```text
PowerManager.newWakeLock()
  → 客户端 WakeLock 创建 Binder token
WakeLock.acquire()
  → IPowerManager.acquireWakeLock(token, flags, tag, package, WorkSource, ...)
PowerManagerService.acquireWakeLockInternal()
  → 创建或更新服务端 WakeLock 记录
  → 对客户端 token 执行 linkToDeath()
  → 更新 WakeLock summary、Notifier 与 BatteryStats
WakeLock.release()
  → IPowerManager.releaseWakeLock(token, ...)
  → 删除服务端记录并重新计算电源状态
```

Binder token 是服务端识别某次持锁关系的令牌，`linkToDeath()` 用于注册客户端进程死亡回调，WakeLock summary 则是服务端汇总后的锁状态。客户端进程死亡时，Binder death 回调会清理服务端记录。这是故障清理机制，不能替代应用的正常 release。进程仍在但业务逻辑已经泄漏时，token 也仍有效，系统无法据此判断任务已经结束。

### PowerManagerService 会禁用已申请的锁

Android 17 的 `setWakeLockDisabledStateLocked()` 会检查：

- WorkSource 归因 UID 是否进入 cached 状态；
- owner 进程是否进入 frozen 状态；
- `NO_CACHED_WAKE_LOCKS` 策略与进程状态；
- deep idle（深度空闲），以及配置允许时的 light idle（轻度空闲）；
- device-idle allowlist 与临时 allowlist；
- Low Power Standby（低功耗待机）allowlist；
- force-suspend（强制挂起）或按 power group（电源组）强制禁用。

状态变化后，`updateWakeLockDisabledStatesLocked()` 会为禁用的锁发送逻辑 release 通知，为重新启用的锁发送逻辑 acquire 通知，再重算 `mWakeLockSummary`。这里的“逻辑通知”用于更新服务端状态和统计，不代表客户端调用了对应方法。App Standby bucket（应用待机分组）会限制 Job、Alarm 与网络入口；wake lock 在服务端是否有效，还要结合上述 UID 与电源状态判断，不能只凭 bucket 推断。

### 多把 App 锁会汇总成一个 suspend blocker

PMS（PowerManagerService）通过 `mWakeLockSummary & WAKE_LOCK_CPU` 判断是否需要 CPU suspend blocker。suspend blocker 是用户态用于阻止整机挂起的锁；PMS 需要它时会持有名为 `PowerManagerService.WakeLocks` 的 blocker，不再需要时则释放。应用的多个 tag 会留在 PMS 与 BatteryStats，但从 PMS 到 SystemSuspend 的这一段已经汇总。

下面的路径来自 `android-17.0.0_r1`。

```text
PowerManagerService.updateSuspendBlockerLocked()
  → mWakeLockSuspendBlocker.acquire()
  → JNI nativeAcquireSuspendBlocker("PowerManagerService.WakeLocks")
  → hardware/libhardware_legacy/power.cpp acquire_wake_lock()
  → ISystemSuspend.acquireWakeLock(PARTIAL, "PowerManagerService.WakeLocks")
  → SystemSuspend suspend counter 增加
```

这解释了诊断中的常见差异：BatteryStats 可以显示多个应用 tag，SystemSuspend 侧却只看到 `PowerManagerService.WakeLocks`。前者记录应用归因，后者记录汇总后的用户态挂起阻止项。

### SystemSuspend 的 wakeup_count 握手

Android 9 及更早版本由 libsuspend（旧的用户态挂起库）发起自动挂起。Android 10 起，SystemSuspend 负责管理用户态 suspend blocker 并协调系统挂起。

SystemSuspend 的 suspend 线程循环执行：

1. 读取 `/sys/power/wakeup_count`；
2. 等待用户态 suspend counter 归零；
3. 把先前读取的值写回 `/sys/power/wakeup_count`；
4. 写 `mem` 到 `/sys/power/state`；
5. 写回失败时放弃本轮，因为读取后出现了新的 wakeup event（唤醒事件）。

在默认 suspend-counter（挂起计数器）路径中，普通用户态锁通过计数阻止 suspend。`SystemSuspend.cpp` 仍会短暂写 `userspace-abort` 到 `/sys/power/wake_lock`，用于中止用户态锁变化与 suspend 同时发生的竞态。设备关闭 counter 路径后，才会按锁名使用 `/sys/power/wake_lock` 兼容接口。

## 11.5.5 内核 wakeup_source

Linux PM（电源管理子系统）使用 `struct wakeup_source` 记录可阻止或中断 suspend 的实体。`android17-6.18-2026-06_r6` 中的主要锚点是：

- `drivers/base/power/wakeup.c`：注册、激活、停用、tracepoint（内核跟踪点）与 debugfs（内核调试文件系统）统计；
- `drivers/base/power/wakeup_stats.c`：`/sys/class/wakeup/wakeupN/` 的统计属性；
- `kernel/power/suspend.c`：system suspend 主流程；
- `kernel/power/wakelock.c`：`CONFIG_PM_WAKELOCKS` 用户态兼容接口。

### 用户态锁与内核 source 没有逐把映射

App 的 `PowerManager.WakeLock` 会保留在 Framework 的 UID/tag 统计中，PMS 再把有效 CPU 锁汇总为 `PowerManagerService.WakeLocks`。内核还会有来自 alarmtimer（内核闹钟定时器）、输入、USB、蓝牙、modem 和各设备驱动的 wakeup source。看到某个 kernel source（内核唤醒源）时，不能只按名字寻找同名 App tag。

### `/sys/kernel/debug/wakeup_sources`

在允许访问 debugfs 的设备上，下面的文件汇总全部 wakeup source：

```bash
adb root
adb shell cat /sys/kernel/debug/wakeup_sources
```

量产 user build（面向用户的系统构建）通常不允许 `adb root`，shell 也无法读取 debugfs。此命令适合已取得 root 权限或使用 userdebug 构建的实验机；量产问题优先依赖 bugreport（系统诊断包）、厂商日志和 SystemSuspend dumpsys（服务状态快照）。

Android 17 kernel 表头包括：

| 字段 | 含义 |
|---|---|
| `active_count` | 从 inactive 进入 active 的次数 |
| `event_count` | 上报 wakeup event 的次数 |
| `wakeup_count` | 被计入系统唤醒的次数 |
| `expire_count` | 定时激活到期次数 |
| `active_since` | 当前活跃持续时间；未活跃时为 0 |
| `total_time` | 累计活跃时间 |
| `max_time` | 单次最长活跃时间 |
| `last_change` | 最近一次状态变化时间 |
| `prevent_suspend_time` | autosleep（内核自动挂起）开启期间阻止 suspend 的累计时间 |

这些时间单位由该 debugfs 输出实现转换为毫秒。比较两次快照时应使用增量；设备运行很久后的绝对累计值不能直接归因到本次复现。

`wakeup_stats.c` 还会把各 source 注册到 `/sys/class/wakeup/wakeupN/`，并提供 `active_time_ms`、`total_time_ms`、`max_time_ms`、`prevent_suspend_time_ms` 等属性。sysfs（内核设备与驱动信息文件系统）的读取权限同样由设备构建与 SELinux 安全策略决定。

## 11.5.6 Doze、Low Power Standby 与 App Standby

### Doze

Doze（设备空闲省电模式）会在维护窗口之外限制网络、Job、Sync、普通 Alarm，并忽略非豁免应用的 wake lock。持锁不能获得 Doze 豁免。维护窗口时序由系统状态和设备实现决定，不应写死成固定的十分钟、三十分钟序列。

allow-while-idle Alarm（可在设备空闲时交付的闹钟）、高优先级且产生用户可见通知的 FCM 等机制会获得受控执行窗口。它们带有频率、配额或使用政策，不能充当持续占用 CPU 的通道。

### Low Power Standby

Low Power Standby（低功耗待机，LPS）开启且处于 active（生效）状态时，非交互、非维护窗口中的应用可能被禁用网络，持有的 wake lock 也会被忽略，Foreground Service 同样受影响。Android 14 起，应用可用 `isExemptFromLowPowerStandby()` 和 `isAllowedInLowPowerStandby()` 查询公开策略边界。

### App Standby

App Standby bucket（应用待机分组）直接影响 Job、Alarm、网络与后台运行机会。它不会给普通应用提供一个稳定公开的“每天可持锁多少分钟”契约。bucket 等级降低后，后台入口减少；进程进入 cached、Doze 或 LPS 后，PMS 又可能禁用已申请的 partial wake lock。这些状态需要联合检查。

## 11.5.7 由系统或库代持的 WakeLock

应用没有调用 `newWakeLock()`，Android vitals 中仍可能出现归因到该应用的锁。

| 来源 | 常见行为 | 排查方向 |
|---|---|---|
| JobScheduler | Job 执行期代持，归因给调度应用 | Job 是否完成、stop reason（停止原因）、超时与重试 |
| WorkManager | 通常经 JobScheduler 执行 | Worker 是否卡住、链是否重复、约束是否合适 |
| AlarmManager | Alarm 投递时持有 `*alarm*` | Alarm 频率、Receiver 时长、是否需要 exact（精确）闹钟 |
| FCM（Firebase Cloud Messaging） | 消息投递期间短时持有；名称随版本变化 | 优先级、投递频率、`onMessageReceived()` 时长 |
| Location | 获取和投递位置期间持有 | 精度、间隔、生命周期与后台资格 |
| Audio / Media | 播放栈或播放器管理 | 会话和 FGS 是否在播放结束后停止 |

WorkManager 管理锁的生命周期，不代表 Worker 可以无限执行。Android 16 的 Job runtime quota 会影响 WorkManager、JobScheduler 与 DownloadManager；应记录 `WorkInfo.getStopReason()` 或 `JobParameters.getStopReason()`。

### Alarm Receiver

AlarmManager 在 Alarm 投递时持锁，并在 `BroadcastReceiver.onReceive()` 完成后释放。Receiver 只做轻量工作；更多处理交给 Worker。`goAsync()` 会延长 broadcast（广播）的完成窗口，但仍有超时要求，完成后必须调用 `PendingResult.finish()`。

### Android 17 listener 型 allow-while-idle Alarm

`setExact(..., OnAlarmListener, Handler)` 从 API 24 起公开，进程终止后不再投递。使用 `OnAlarmListener` 设置 exact Alarm 时，不需要 `SCHEDULE_EXACT_ALARM`。

API 37 新增公开重载：

`setExactAndAllowWhileIdle(int, long, String, Executor, OnAlarmListener)`

它适合只有当前组件存活时才有意义的精确 idle（设备空闲期）回调。系统可在调用进程不再有 Activity、Service 或 ContentProvider 时取消 Alarm，组件结束时也要 `cancel(listener)`。需要在进程终止后继续投递的闹钟、日历提醒，仍使用合适的 `PendingIntent` 路径，并满足 exact Alarm 资格。

## 11.5.8 本地诊断

### 第一步：确认 Framework 记录

下面的命令分别查看当前 PMS 锁、UID 历史和 SystemSuspend 统计。

```bash
adb shell dumpsys power
adb shell dumpsys batterystats --history
adb shell dumpsys suspend_control_internal --wakelocks
adb shell dumpsys suspend_control_internal --wakeups
```

`dumpsys power` 回答“现在有哪些客户端记录”；BatteryStats 回答“谁在什么时间持有并被归因”；SystemSuspend 回答“用户态 suspend blocker 与唤醒统计”。`suspend_control_internal` 的可用选项和权限会随 build（系统构建）类型与厂商实现变化。

### 第二步：生成可复现的 Battery Historian 输入

下面的流程只应在专用测试设备上执行：重置统计，运行固定复现脚本并记录时间，再生成 bugreport。

```bash
adb shell dumpsys batterystats --reset
adb bugreport wake-lock-reproduction.zip
```

bugreport 可能包含账号、通知、网络和设备信息。应使用本地 Battery Historian 或受控分析环境，不要把未脱敏文件上传到未知第三方服务。时间线上要同时查看 screen（屏幕）、Doze、Job、Alarm、network（网络）、process state（进程状态）与 partial wake lock。

### 第三步：Perfetto 对齐 kernel 与能量

下面的 userdebug 配置采集 wakeup-source tracepoint，并在设备支持时采集电池与 power rail（电源轨）数据。

```textproto
buffers: {
  size_kb: 32768
  fill_policy: RING_BUFFER
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
```

tracepoint 会保留为原始 ftrace event（内核跟踪事件），分析时要按 source 名称和时间配对 activate/deactivate（激活/停用）事件。`android.power` 是否有 rail 数据取决于设备的 PowerStats HAL（电源统计硬件抽象层）；轨道缺失不能当成功耗为零。生产 user build 还可能禁止相关 ftrace 事件。

### 四层证据表

| 层级 | 工具 | 能回答的问题 |
|---|---|---|
| 应用 | 日志、Background Task Inspector | 哪段业务申请、完成、取消或重试 |
| Framework | `dumpsys power`、BatteryStats、Historian | token、tag、UID、WorkSource、前后台时间 |
| SystemSuspend | `dumpsys suspend_control_internal` | 用户态 blocker 与 suspend/wakeup 统计 |
| Kernel/硬件 | wakeup sources、Perfetto、PowerMonitor、电源轨 | 哪个 source 活跃，整机能量是否变化 |

PowerMonitor 从 API 35 起可读取设备公开的累计 subsystem（子系统）能量。它适合验证修复是否改变对应 rail，不能识别是哪一行代码持锁。ADPF（Android Dynamic Performance Framework）的 power-efficiency hint（能效提示）只表达调度偏好，也不会替应用 release wake lock。

## 11.5.9 常见故障模式

### 异常路径没有 release

同步代码使用 `try/finally`。异步代码需要统一的完成状态，成功、失败、取消、超时和组件销毁都必须进入同一个 release 路径。若生命周期跨进程或可能持续很久，应改用 WorkManager、JobScheduler 或合适类型的 FGS，避免让一把手工管理的锁跨越复杂的回调状态机。

### acquire 与 release 所有者不同

若由 Activity 调用 acquire、由 Service 调用 release，或由多个 callback（回调）共同操作引用计数，容易出现重入（同一流程再次进入）和欠释放（申请次数多于释放次数）。锁对象、业务状态和释放权应交给同一个 owner 管理。

### 用 FGS 掩盖后台轮询

FGS 通知与 partial wake lock 都无法让高频轮询变得合理。实时下行优先共享推送通道，可延迟同步使用 Job/WorkManager。FGS 只用于用户正在感知的连续工作。

### 第三方 SDK 与框架代持

Android vitals 归因到应用的锁可能来自 SDK、WorkManager、JobScheduler、FCM 或 Location。按锁名与时间回查 API 调用，不能只搜索项目里的 `newWakeLock()`。

### 高基数 tag

把请求 ID 或用户 ID 放进 tag，会把同一持锁点分散成大量统计项，还可能触发 `_UNKNOWN` 脱敏。业务请求 ID 应留在应用日志中，wake-lock tag 保持稳定，两者通过时间戳关联。

### 只看持锁时长

持锁时长说明 suspend 机会被占用，不直接等于能量。修复评估还要看：

- 锁内 CPU running time（CPU 实际运行时间）与线程活动；
- 网络、定位、传感器和存储活动；
- suspend 成功次数与睡眠时长；
- 设备 power rail 或外接仪表数据；
- 业务成功率、端到端延迟与恢复行为。

## 11.5.10 Google Play excessive partial wake lock

Android vitals 在以下条件下把一次应用会话计入 excessive partial wake lock：

- 所有非豁免 partial wake lock 合计，在 24 小时内达到或超过 2 小时；
- 统计锁在应用后台或运行 Foreground Service 时的持有时间；
- 当前豁免包括 audio、location 和 JobScheduler user-initiated API 创建的锁。

若 28 天内超过 5% 的应用会话命中，可能影响 Google Play 可见性。2026 年 3 月 1 日起，Google Play 已逐步对持续超阈值的应用减少推荐等发现入口，并可能在商店详情页展示耗电警告。

5% 是命中该问题的会话比例门槛，不表示每个用户可以持锁 5% 的时间。两小时也不是应用的 system API quota（系统接口配额）；它是 Android vitals 汇总多把非豁免锁后的质量指标。Play Console 的 wake-lock name（锁名称）、affected sessions（受影响会话）和 P90/P99 时长（90/99 分位数）可用于定位来源，修复仍要回到具体业务与系统时间线。

## 11.5.11 版本边界

| 版本 | 相关变化 |
|---|---|
| Android 8 / API 26 | 兼容范围起点；后台执行与位置限制已开始影响持锁场景 |
| Android 9 / API 28 | App Standby buckets；SystemSuspend 迁移前的历史分界 |
| Android 10 / API 29 | SystemSuspend 取代 libsuspend 成为现代用户态挂起协调路径 |
| Android 12 / API 31 | 后台 FGS 启动限制；exact-alarm 权限 |
| Android 13 / API 33 | `WakeLockStateListener`、Low Power Standby；`ACQUIRE_CAUSES_WAKEUP` 废弃 |
| Android 14 / API 34 | LPS policy 查询能力；FGS 类型与 while-in-use 权限检查范围扩大 |
| Android 15 / API 35 | PowerMonitor；限时 FGS 行为 |
| Android 16 / API 36 | Job runtime quota 变化影响 WorkManager、JobScheduler、DownloadManager |
| Android 17 / API 37 | 公开 listener 版 `setExactAndAllowWhileIdle()`；平台源码锚点 `android-17.0.0_r1` |
| 2026-03 | Google Play excessive partial wake lock 可见性处理开始执行 |

## 11.5.12 复核清单

- [ ] 是否存在专用 API，可省去手工 partial wake lock？
- [ ] Manifest 是否只在确有需要时声明 `WAKE_LOCK`？
- [ ] tag 是否稳定、可定位且不含个人信息或唯一 ID？
- [ ] acquire/release 是否由同一 owner 管理？
- [ ] 是否覆盖成功、失败、取消、超时和组件销毁？
- [ ] 超时是否只作为保险，正常路径是否主动 release？
- [ ] 是否区分客户端 held 与服务端 enabled？
- [ ] 是否同时检查 Doze、LPS、cached/frozen、FGS 和 App Standby？
- [ ] 是否区分 BatteryStats tag、SystemSuspend blocker 与 kernel wakeup source？
- [ ] 框架或 SDK 代持的锁是否按 Job、Alarm、FCM、Location、Audio 分别回查？
- [ ] 修复是否同时验证功能 SLA（服务时限承诺）、suspend 时间与设备能量？
- [ ] 平台引用是否来自 `android-17.0.0_r1`，kernel 引用是否来自 `android17-6.18-2026-06_r6`？

## 参考资料

### Android Developers

- [Choose the right API to keep the device awake](https://developer.android.com/develop/background-work/background-tasks/awake)
- [Use wake locks](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock)
- [Follow wake lock best practices](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/best-practices)
- [Debug wake locks locally](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/debug-locally)
- [Identify and optimize wake lock use cases](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls)
- [Task scheduling and WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent)
- [Excessive partial wake locks](https://developer.android.com/topic/performance/vitals/excessive-wakelock)
- [PowerManager API](https://developer.android.com/reference/android/os/PowerManager)
- [AlarmManager API](https://developer.android.com/reference/android/app/AlarmManager)
- [PowerMonitor API](https://developer.android.com/reference/android/os/PowerMonitor)
- [Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Android 16 JobScheduler quota changes](https://developer.android.com/about/versions/16/behavior-changes-all#job-scheduler-quota)

### AOSP `android-17.0.0_r1`

- `frameworks/base/core/java/android/os/PowerManager.java`
- `frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java`
- `frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp`
- `frameworks/base/apex/jobscheduler/framework/java/android/app/AlarmManager.java`
- `frameworks/base/apex/jobscheduler/service/java/com/android/server/alarm/AlarmManagerService.java`
- `hardware/libhardware_legacy/power.cpp`
- `system/hardware/interfaces/suspend/aidl/default/SystemSuspend.cpp`

### Android common kernel `android17-6.18-2026-06_r6`

- `drivers/base/power/wakeup.c`
- `drivers/base/power/wakeup_stats.c`
- `kernel/power/suspend.c`
- `kernel/power/wakelock.c`

### 官方系统资料

- [SystemSuspend service](https://source.android.com/docs/core/power/systemsuspend)
- [Perfetto power data sources](https://perfetto.dev/docs/data-sources/battery-counters)
- [Battery Historian](https://developer.android.com/topic/performance/power/setup-battery-historian)
