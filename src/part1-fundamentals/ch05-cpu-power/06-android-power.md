---
title: "Android 功耗管理"
chapter: "5.6"
section: "5.6"
status: ready-for-review
applicable_versions: "Android 6.0 (API 23) - Android 17 (API 37)"
last_verified: "2026-04-29"
last_verified_against: "AOSP android-16.0.0_r1, android-17-beta3"
confidence: medium
drafted_date: "2026-04-01"
drafted_by: openclaw-task2a
reviewed_date: "2026-05-05"
task6_reviewed_date: "2026-05-05"
task6_state: revisiting
task6_result: pass-light-edit
task9_state: pending
task9_result: needs-rework
task9_reviewed_date: "2026-05-14"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-14T11:34:00+08:00"
task2b_state: fixed
task2b_result: fixed
last_task2b_at: 2026-05-24T19:29:26+08:00
pipeline_stage: task6_pending
reviewed_by: openclaw-task6
review_round: 4
related_chapters:
  - "5.1"
  - "5.2"
  - "5.4"

---

# Android 功耗管理

<!-- outline-start -->
## 本节要点大纲

### 锚点(必须覆盖)

- 🔹 Android 功耗管理框架:PowerManagerService → WakeLock → Suspend
- 🔹 Doze 模式与 App Standby 的工作原理与影响
- 🔹 Battery Historian 工具与功耗分析方法
- 🔹 WakeLock 的种类与滥用检测
- 🔹 JobScheduler / WorkManager 的省电调度策略

### 扩展(可选深入)

- 🔸 Adaptive Battery 与 ML 预测
- 🔸 Background Restriction 对后台功耗的控制
- 🔸 RESTRICTED bucket 与 Exemption 机制

### OpenClaw 加工指引

> **锚点**是最低覆盖要求,加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点,
> 可**就地插入**最相关的锚点之后,并用 `[自动发现]` 标注,方便后续 review。
> 锚点内容需 L1/L2 验证,扩展内容至少 L2 验证,自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 功耗管理

当我们打开 Perfetto,选中一段时间范围,看到某个进程在灭屏状态下仍然持续占用 CPU,或者在 Battery Historian 中发现一个 App 后台持锁时间远超预期--这些现象背后,都是 Android 功耗管理框架在工作(或者该工作的时候没有工作)。

功耗管理覆盖的范围远不止省电。它是一套从硬件到软件的分层机制：从 Linux 内核的 Suspend/Resume（5.4 节讨论过 DVFS，5.5 节讨论过 Thermal），到 Android 框架层的 PowerManagerService，再到 Google 引入的 Doze 模式和 App Standby 分桶策略。理解这套机制后，分析功耗问题时才能定位：到底是 App 持了不该持的 WakeLock，还是后台任务调度不合理导致系统无法休眠，又或者是某个硬件器件被异常唤醒。

功耗和性能是一枚硬币的两面。我们在前面章节讨论的 CPU 调度(5.1)、大小核(5.3)、DVFS(5.4)、Thermal(5.5)都是从"怎么让系统跑得更快"的角度出发的。而这一节,我们从"怎么让系统在不该跑的时候停下来"的角度来看同一套硬件。

## Android 功耗管理框架:PowerManagerService → WakeLock → Suspend

### 从一个问题开始:手机灭屏之后,CPU 在干什么?

答案是:大部分时间什么也不做。理想情况下,灭屏后系统应该进入低功耗状态(Suspend),CPU 停止执行指令,内存进入自刷新模式,大多数外设被关闭。但总有例外:音乐播放需要在灭屏时持续运行;即时通讯需要维持长连接;导航需要持续获取 GPS--这些场景下,App 需要告诉系统"别睡,我还有事要做"。

这就是 WakeLock 存在的原因。

### PowerManagerService:功耗管理的总调度

PowerManagerService(简称 PMS)运行在 system_server 进程中,是 Android 功耗管理的核心调度者。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java]

PMS 的职责可以概括为三个:

**第一,管理 WakeLock。** 当 App 申请 WakeLock 时,请求会通过 PowerManager(客户端 API)经由 Binder IPC 到达 PMS。PMS 维护一张全局的 WakeLock 列表,记录每个锁的持有者、类型和状态。

**第二,决定设备的电源状态。** PMS 根据当前有效的 WakeLock、屏幕超时设置、Doze 状态等因素,计算出系统应该处于什么电源状态--屏幕亮还是灭、CPU 运行还是可以休眠。

**第三,协调 autosuspend、suspend blocker 和 Power HAL。** PMS 不再把"进入 Suspend"简化成直接写 `/sys/power/state`。在 android-16 的实现里,Java 层通过 JNI 调 `nativeSetAutoSuspend()`、`nativeAcquireSuspendBlocker()` / `nativeReleaseSuspendBlocker()` 和 `nativeSetPowerMode()`;对应的 native 层再调用 autosuspend 接口、维护本地 suspend blocker,并把 `Mode::INTERACTIVE` 这类模式透传给 Power HAL。[已验证: AOSP android-16.0.0_r1, services/core/jni/com_android_server_power_PowerManagerService.cpp; hardware/interfaces/power/aidl/android/hardware/power/IPower.aidl]

### WakeLock 的种类:不是所有锁都一样

WakeLock 是 Android 提供给 App 的一种"阻止系统休眠"的机制。在 `PowerManager.java` 中定义了多种类型:[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/PowerManager.java]

最关键的是 **PARTIAL_WAKE_LOCK**。它只保持 CPU 运行,允许屏幕和键盘背光关闭。这是音乐播放、后台下载、即时通讯心跳等场景下最常用的锁类型。如果持有了 PARTIAL_WAKE_LOCK,即使用户按下电源键灭屏,CPU 仍然会继续工作。

其他类型的锁(如 SCREEN_BRIGHT_WAKE_LOCK、FULL_WAKE_LOCK)在较新的 Android 版本中已经被废弃,因为它们强制保持屏幕点亮,功耗影响太大。如果代码中还在使用这些废弃的锁类型,应该迁移到 FLAG_KEEP_SCREEN_ON 或其他方式。

**WakeLock 事件如何流向 BatteryStats**：当 App 调用 PowerManager.newWakeLock() 时，请求经过 PowerManager(客户端) → Binder IPC → PowerManagerService(PMS)。PMS 在 acquireWakeLockInternal() 中完成 WakeLock 注册，随后通过 notifyWakeLockAcquiredLocked() → Notifier.onWakeLockAcquired() 把事件转发给 IBatteryStats（通过 noteStartWakelock() / noteStartWakelockFromSource()，携带 WorkSource、historyTag、lockFlags 等参数）。IBatteryStats 的实现类 BatteryStatsService 最终在 BatteryStatsImpl 中按 uid/pid 记录持锁时长和频次。释放流程对称：notifyWakeLockReleasedLocked() → Notifier → IBatteryStats.noteStopWakelock*()。Battery Historian 的 Userspace Wakelock Track 数据就来自这条统计路径。[已验证: AOSP android-16.0.0_r1, PowerManagerService.java / PowerManagerService.Notifier.java / BatteryStatsImpl.java]

```java
// frameworks/base/core/java/android/os/PowerManager.java
// WakeLock 类型定义(部分已废弃)
public static final int PARTIAL_WAKE_LOCK        = 0x00000001;  // CPU 运行,屏幕可关
public static final int SCREEN_DIM_WAKE_LOCK      = 0x00000006; // [已废弃] 屏幕暗光
public static final int SCREEN_BRIGHT_WAKE_LOCK   = 0x0000000a; // [已废弃] 屏幕全亮
public static final int FULL_WAKE_LOCK            = 0x0000001a; // [已废弃] 屏幕+键盘全亮
```

从 Android 8.0(API 26)开始,后台服务持有 PARTIAL_WAKE_LOCK 的行为受到了限制--如果 App 进入了缓存状态(cached),其持有的 WakeLock 可能会被系统回收。这是 Android 逐步收紧后台功耗控制的一部分。

### 从 WakeLock 到 Suspend:要分清四层边界

WakeLock、suspend blocker、autosuspend 和 Power HAL 处理的是同一套机制里的不同层次:

- **WakeLock**:框架层输入。App 通过 `PowerManager.WakeLock` 表达"这段时间 CPU 不要睡",PMS 把这些请求汇总成电源策略。
- **Suspend blocker**:system_server / native 层的本地保持唤醒机制。PMS 在更新电源状态、处理唤醒原因、切换显示状态时会短暂持有它,避免系统在关键路径中间睡下去。
- **Auto-suspend**:允许内核在没有 blocker、没有待处理唤醒源时自动进入 suspend。PMS 通过 `nativeSetAutoSuspend()` 开关这一能力。
- **Power HAL mode**:把交互态等高层状态通知到底层电源策略,例如 `Mode::INTERACTIVE`。它影响 SoC / 设备侧的功耗档位,不等同于 App 持有 WakeLock。

系统准备进入 suspend 时,常见顺序是:显示配置进入 all-off / inactive,PMS 关闭 interactive mode,再打开 autosuspend。此后只要没有新的 WakeLock、native suspend blocker 或硬件唤醒事件,内核就会在合适时机进入 suspend。这个时点不是 PMS"直接写一个节点就睡下去",而是内核根据 autosuspend 条件自行落到 suspend。

唤醒路径也要反过来看:电源键、RTC、调制解调器、中断控制器等硬件事件先把 SoC 拉回运行态;内核恢复驱动;system_server 里的 suspend blocker 保证恢复流程走完;PMS 再更新显示、电源模式和上层服务状态。

### HWC onVsyncIdle 与显示空闲检测

HWC（Hardware Composer）在显示内容持续不变时，可以通过 IComposerCallback.onVsyncIdle() 通知上层显示管线进入空闲态。在 AOSP 实现中，SurfaceFlinger 收到 onComposerHalVsyncIdle() 回调后，调用 Scheduler.forceNextResync() 触发一次重新同步——这个回调的语义是 display idle 导致 refresh/vsync cadence 发生变化，而不是直接驱动 PMS 进入 suspend。

注意：onVsyncIdle 是 HWC → SurfaceFlinger 的显示侧信号，不等于 PMS 收到后直接释放 WakeLock 或触发系统 suspend。系统从"屏幕静止"到"进入 Deep Sleep"的路径仍然由 PMS 的 WakeLock 汇总、用户超时设置、Doze 状态等因素决定。如果需要缩短灭屏到 suspend 的窗口，应从 PowerManagerService / DisplayPowerController / Power HAL 交互逻辑入手分析，而非依赖 onVsyncIdle 单信号。

对开发者而言，灭屏后的功耗分析不能只看 WakeLock 持有时长，还需要关注 App 是否在持续触发 invalidate / requestLayout 导致 SurfaceFlinger 无法判定"显示空闲"。如果在 Perfetto 中观察到灭屏后 SurfaceFlinger 仍然持续产生 VSync-surfaceflinger slice，且系统迟迟不进入 suspend，排查方向包括：持续动画、后台 Canvas 绘制、ViewRootImpl 的 dirty rect 提交等。

[已验证: AOSP android-16.0.0_r1, SurfaceFlinger.onComposerHalVsyncIdle() / Scheduler.forceNextResync(); hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/IComposerCallback.aidl]

[图:PowerManagerService → WakeLock / suspend blocker / autosuspend / Power HAL 的分层示意]

### 在 Perfetto 中的表现

如果我们在 Perfetto 中抓取了包含电源事件的 Trace,可以观察到以下信息:

- **Power 标签页**:在 system_server 进程下 WakeLock 的 acquire/release 事件,以及屏幕 on/off 的状态变化
- **CPU 状态**:当系统进入 Suspend 后,所有 CPU 的 idle 比例会接近 100%;如果某个 CPU 在灭屏期间仍然有活跃的执行段,说明有东西阻止了系统进入深度休眠
- **Wake reasons**:内核唤醒原因通常会记录在 `pm_wakeup` 事件中

如果我们发现灭屏后系统没有进入 Suspend(CPU 仍有活动),常见原因就是某个 App 持有了 PARTIAL_WAKE_LOCK 没有释放。通过 `adb shell dumpsys power` 可以查看当前所有活跃的 WakeLock:

```text
Wake Locks: size=2
  PARTIAL_WAKE_LOCK  'AudioMix' (uid=10125, pid=23456, ws=WorkSource{10125})  activated
  PARTIAL_WAKE_LOCK  'myapp:background_sync' (uid=10102, pid=12345, ws=null)  activated
```

[待补充:Perfetto 中 PowerManagerService 相关 slice 的截图]

## Doze 模式与 App Standby 的工作原理与影响

### Doze:让灭屏后的系统"逐渐安静下来"

Doze 模式在 Android 6.0(Marshmallow)引入,是 Google 解决"灭屏后 App 仍然在后台频繁活动"问题的方案。它的思路:设备灭屏静止一段时间后,逐步限制 App 的后台活动,直到系统几乎完全安静下来。

Doze 分为两个级别:

**Light Doze(Android 7.0 引入)** 在设备灭屏后(不要求静止)就会激活。系统会推迟非紧急的网络访问和 Job 执行,但仍然允许高优先级的通知和前台服务运行。Light Doze 的维护窗口间隔较短,App 有更多机会执行后台任务。

**Deep Doze** 要求设备灭屏、静止且未充电(至少 30 分钟后开始进入)。在这个状态下,系统会暂停普通应用的网络、Job、Sync 和大多数 Alarm,只在短暂的"维护窗口"里放开这些限制。加入电池优化豁免名单的应用是部分豁免:它们在 Doze / App Standby 中仍可使用网络并持有 partial wakelock,但常规 Alarm、Job、Sync 仍会继续受限。[已验证: Android Developers, Optimize for Doze and App Standby]

维护窗口的时间间隔会逐渐变长。刚开始可能是几分钟一个窗口,随着灭屏时间延长,窗口间隔可能扩展到几十分钟甚至更长。这种设计确保了灭屏时间越长,系统越安静,电池消耗越低。[已验证: 官方文档, developer.android.com/training/monitoring-device-state/doze-standby]

### Doze 对 App 行为的限制

进入 Doze 后,普通应用会面临这些限制:

- **网络访问暂停**:新的网络传输通常要等维护窗口;高优先级 FCM 和电池优化豁免应用属于例外路径
- **Alarm 被推迟**:常规 `AlarmManager` 任务不会按原计划触发;`setAndAllowWhileIdle()` 与 `setExactAndAllowWhileIdle()` 仍可用,但调用频率受限
- **JobScheduler / WorkManager / Sync 延后**:后台调度会推迟到维护窗口或更合适的系统时机
- **WakeLock 不能单独绕过 Doze**:普通应用即使持有 partial wakelock,也不能把 Doze 的网络和调度限制全部取消

音乐播放、导航等持续后台场景通常要组合前台服务、媒体/位置 API,以及系统允许的豁免能力来设计。是否能持续联网,仍取决于 Doze 状态、维护窗口和电池优化豁免,而不是"开了前台服务就完全不受限制"。

### App Standby Buckets:根据使用频率分配资源

Android 9(API 28)引入了 App Standby Buckets,把 App 按照使用频率和最近使用时间分为五个等级,不同等级享有不同的系统资源配额:

**Active(活跃)**:App 正在使用或刚使用过,或运行着前台服务。不受到任何后台限制。

**Working Set(工作集)**:App 经常使用但当前不在前台。受到轻微限制。

**Frequent(频繁使用)**:App 经常使用但不是每天都会用。后台访问受到较多限制。

**Rare(极少使用)**:App 很少使用。后台活动受到严格限制。

**Restricted(受限,Android 12 引入)**:App 消耗了过多系统资源或表现出不良行为。这个等级的限制最为严格--Job 每天只能在 10 分钟的批量会话中运行一次,Alarm 每天只能触发一次。[已验证: 官方文档, developer.android.com/topic/performance/appstandby]

系统会动态地将 App 分配到不同的 Bucket 中。分配依据包括 App 的使用频率、最近使用时间等。开发者可以通过 ADB 命令测试不同 Bucket 下的行为:

```bash
adb shell am set-standby-bucket com.example.app restricted
```

### Doze 与 App Standby 的协同

Doze 关注的是"设备层面的状态"--灭屏、静止、未充电。App Standby 关注的是"单个 App 的使用模式"--用得多还是用得少。两者可以叠加:一个 Rare Bucket 的 App 在灭屏状态下,受到的限制比一个 Active Bucket 的 App 严格得多。

功耗分析时，需要同时考虑设备当前是否处于 Doze 状态,以及目标 App 被分到了哪个 Standby Bucket。在 Battery Historian 中可以同时看到这两个维度的信息。

## Battery Historian 工具与功耗分析方法

### Battery Historian 解决什么问题

当收到一条用户反馈说"App 耗电太厉害了"时,我们需要一个能看到"过去几个小时系统到底发生了什么"的工具。Battery Historian 就是这个工具。

Battery Historian 是 Google 推出的开源工具,用于分析 Android 设备的电池使用历史。它不是一个实时监控工具,而是一个"事后分析"工具--我们先让设备正常运行一段时间,然后导出 bugreport,再用 Battery Historian 可视化分析。排查功耗问题的第一步几乎都是"先抓一份 bugreport 扔进 Battery Historian",比直接猜问题出在哪里要高效得多。[已验证: 来源见 obsidian/Cubox/BatteryHistorian Android手机耗电分析神器-2022-04-15.md]

### 使用流程

完整的 Battery Historian 分析流程分为四步:

**第一步:重置电池统计数据。** 连接设备后,执行:

```bash
adb shell dumpsys batterystats --reset
```

这会清除旧的电池采集数据,确保接下来的分析基于一个干净的起点。

**第二步:复现问题场景。** 让用户(或我们自己)正常使用手机,复现耗电问题。这段时间内,系统在后台持续记录各种电源相关事件:WakeLock 持有/释放、网络访问、GPS 使用、Alarm 触发、屏幕亮度变化等。

**第三步:导出 bugreport。**

```bash
adb bugreport > bugreport.txt
```

这一步可能需要 2-5 分钟,期间不要断开 USB 连接。

**第四步:在 Battery Historian 中打开。** 我们可以使用本地 Docker 部署,也可以使用在线版本。打开后我们会看到一个时间轴视图,上面展示了各种电源相关事件的状态变化。

### Battery Historian 的分析维度

Battery Historian 提供了两个主要视图:

**System Stats(系统统计)**:展示整个设备的状态,包括信号强度、屏幕亮度、充电状态等。这个视图用于排除环境因素--如果系统统计显示在问题时段网络信号极差(射频模块会增大发射功率来维持连接),那高耗电可能并非 App 自身的问题。

**App Stats(应用统计)**:选中某个 App 后,它在这个时间段内的详细行为:WakeLock 持有时长、网络访问频率、Job 执行情况、前台/后台进程状态、SyncManager 活动等。

### 通用分析思路

在实际使用 Battery Historian 分析功耗问题时,可以按以下步骤排查:

**1. 检查亮灭屏耗电速率。** 通过 System Stats 中的 screen on/off rate 和电量消耗曲线,判断是亮屏还是灭屏阶段的耗电异常。亮屏耗电大通常和显示、GPU、网络相关;灭屏耗电大通常和 WakeLock、后台 Job、频繁唤醒相关。

**2. 定位异常时间段。** 观察 Battery Historian 时间轴上的电量百分比刻度,找到电量下降最快的区间。结合该时段的前台应用、网络状态、后台 Job 等信息,判断是什么导致了高耗电。

**3. 逐项排查。** 综合查看亮度状态、网络类型(5G > 4G > WiFi 的功耗递减)、后台 Job、前台应用,判断耗电是否符合预期。

Battery Historian 中的常见场景案例也很有参考价值:充电慢可能与异常 Job 有关;发热问题可能来自网络+高亮度+高耗电 App 的叠加;灭屏异常耗电可能是有 App 通过音频锁给自己保活,导致系统无法休眠。[已验证: 来源见 obsidian/Cubox/BatteryHistorian Android手机耗电分析神器-2022-04-15.md]

### 实战案例:灭屏后 GPS 持续定位导致的异常耗电

这是一个在 Battery Historian 中定位灭屏耗电问题的典型路径。

**现象**:用户反馈"App 安装后手机掉电明显加快",灭屏一晚上掉电 15%-20%,正常设备应该在 3% 以内。

**排查步骤**:

1. **重置 + 复现**。`adb shell dumpsys batterystats --reset`,然后让用户正常使用半天,复现耗电场景,再导出 bugreport。

2. **在 Battery Historian 中定位异常时间段**。打开时间轴,先看整体电量曲线。灭屏时段（深色背景区域）电量下降斜率明显大于正常水平。点击该时段,检查以下维度:

   - **Userspace Wakelock**:发现目标 App 持有 `myapp:location_update` WakeLock,覆盖了灭屏时段的 90% 以上。
   - **GPS 状态**:`GPS` 行在灭屏期间持续为 `active`(绿色条),说明 GPS 硬件没有被关闭。
   - **网络活动**:灭屏期间 App 仍在频繁发起网络请求,间隔约 30 秒。

3. **定位根因**。结合代码审查发现:App 注册了 `LocationManager.requestLocationUpdates(GPS_PROVIDER, 0, 0, listener)`,minTime 和 minDistance 都设为 0,意味着只要有 GPS 信号就持续回调。灭屏后没有取消注册,GPS 模块持续运行,App 通过 WakeLock 保持 CPU 活跃来处理位置更新并上报服务端。

4. **修复方案**:
   - 灭屏时取消 GPS 注册,改用 `PassiveProvider` 或降低更新频率（如 60 秒一次）
   - 位置上报改用 WorkManager 约束调度,替代 WakeLock + 定时器
   - 注册 `BroadcastReceiver` 监听 `ACTION_SCREEN_OFF/ON`,在灭屏时进入低功耗模式

5. **验证**:修复后重新跑 Battery Historian,灭屏时段 GPS active 消失,WakeLock 覆盖率降到 5% 以下,灭屏一晚掉电回到 2%-3%。

这个案例体现了 Battery Historian 排查的核心思路:**先锁定异常时段,再按维度（WakeLock、网络、GPS、CPU）逐一排查,找到维度之间的关联,最后回到代码定位根因。**

### 其他功耗分析工具

除了 Battery Historian,还有几个常用的功耗分析工具:

**Android Studio Energy Profiler**:Android Studio 内置的功耗分析器,可以在开发阶段实时查看 App 的功耗估算值(基于 GPS+网络+CPU 的拟合值,不是真实功耗)。在 Pixel 6 及之后的设备上,还可以通过 ODPM(On-Device Power Monitor)获取按电源轨(Power Rails)细分的真实功耗数据。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_借助_Android_Studio_中的功耗性能分析器进行_A_B_测试.md]

**PowerMonitor 硬件功耗仪**:业界最通用的整机耗电评估方式,通过外接电量计高频率高精度采集电流。常用的是 Monsoon 公司的 PowerMonitor,电流精度 50μA,采样周期 200μs。缺点是需要拆机接线,适合线下精细测试。[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_抖音功耗优化实践.md]

**电池电量计 API**:通过 `BatteryManager` 接口可以读取电池电量计的统计结果,包括瞬时电流(BATTERY_PROPERTY_CURRENT_NOW)、平均电流(BATTERY_PROPERTY_CURRENT_AVERAGE)和剩余容量(BATTERY_PROPERTY_CHARGE_COUNTER)。这种方式精度取决于硬件电量计,但适合线上监控场景。

**dumpsys 命令系列**:
- `adb shell dumpsys batterystats`:查看电池统计信息
- `adb shell dumpsys power`:查看当前 WakeLock 状态
- `adb shell dumpsys jobscheduler`:查看 Job 执行统计

[自动发现: 来源 obsidian/Personal-Knowlodge/source/2026-03-08_wechat_抖音功耗优化实践.md - 器件功耗模型与 OEM 厂商 power_profile.xml]

功耗分析要把整机功耗拆到各个器件（CPU、GPU、Display、WiFi、Audio 等），再按使用比例归因到各个 App。Google 在 AOSP 中提供了一套通用的器件耗电模型和配置方案(`power_profile.xml`),OEM 厂商根据自己的硬件参数校准。以 WiFi 为例,模型按状态(on/active/scan/rx/tx/idle)分别配置基准电流,运行时统计各状态时长再乘以对应电流值,就得到 WiFi 器件的功耗估算。不过这套通用模型的精度有限,各 OEM 厂商通常还有基于自身硬件的更精准功耗统计方案。

## WakeLock 的种类与滥用检测

### WakeLock 的正确使用方式

前面我们介绍了 WakeLock 的类型和 PMS 的管理机制。这里我们聚焦到实际开发中最常见的使用场景和问题。

最常见的合理使用场景:

**音乐播放**:后台播放音乐时需要持有 PARTIAL_WAKE_LOCK,确保 CPU 持续运行以解码音频数据。Android 的 MediaPlayer 内部会自动管理音频相关的 WakeLock。

**后台下载/上传**:长时间的后台数据传输需要 WakeLock 保持网络连接。更好的做法是使用 WorkManager 替代手动管理 WakeLock。

**即时通讯长连接**:维持 TCP 长连接需要 CPU 定期处理心跳包。推荐使用 FCM(Firebase Cloud Messaging)等推送服务,由系统统一管理唤醒。

获取和释放 WakeLock 的标准写法:

```java
PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
PowerManager.WakeLock wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "myapp:background_sync");
wl.acquire(30 * 60 * 1000L); // 设置超时:最多持有 30 分钟
try {
    // 执行后台任务
    doBackgroundWork();
} finally {
    wl.release(); // 确保释放
}
```

这段代码中最容易被忽略的是 `acquire()` 中传入的超时参数。如果不设置超时,一旦异常路径没走到 `release()`--比如抛出了未捕获的异常--这个锁就会一直持有到 App 进程被杀掉。在这段时间内,系统无法进入 Suspend。

### WakeLock 滥用的常见模式

在实际分析中,最常见的 WakeLock 滥用有三种:

**1. 长时间持有不释放。** 这是最严重的问题。一个 PARTIAL_WAKE_LOCK 如果被持有了几个小时没释放,意味着 CPU 在这几个小时内都无法进入 Suspend。灭屏后系统完全不睡觉,功耗会从正常的每小时几 mAh 飙升到几十甚至上百 mAh。

**2. 在不需要的时候申请 WakeLock。** 比如只是在主线程做了一段轻量的计算,就申请了一个 WakeLock"以防万一"。这种做法完全没必要--前台 App 运行时系统本来就不会 Suspend,WakeLock 只有在灭屏后才有实际意义。

**3. 通过音频锁保活。** 一些 App 通过播放无声音频来持有音频 WakeLock,目的是在后台保活。这种做法在 Battery Historian 中表现为灭屏后 audio 状态持续为 active,对应的 WakeLock 也持续存在。现代 Android 版本(Android 12+)对这种行为已经有了检测和限制机制。

### 如何检测 WakeLock 滥用

**Battery Historian 是最直接的工具。** 在 App Stats 视图中选中目标 App,查看 "Userspace Wakelock" 行--如果看到某个 WakeLock 覆盖了很大比例的时间段,特别是在灭屏期间,那就是问题的信号。遇到灭屏掉电快,第一件事就是打开 Battery Historian 看 Userspace Wakelock 行,八九不离十能看到某个 App 的锁把灭屏时段填满了。关于 WakeLock 在 Perfetto 中的更详细分析,参见 §11.5 Wakelock 机制与功耗分析。

**adb 命令快速排查:**

```bash
# 查看所有活跃的 WakeLock
adb shell dumpsys power | grep "Wake Locks" -A 20

# 查看 App 的 Wakelock 统计
adb shell dumpsys batterystats | grep -A 5 "Wake lock"
```

公开可复核的风险口径更适合看 Android vitals、batterystats 和 Battery Historian,而不是某个"1 分钟系统阈值"。Android vitals 把 excessive partial wake lock 定义为:应用在后台或前台服务场景下,24 小时内累计 partial wakelock 达到 2 小时以上;Google Play 进一步看它在 28 天内影响的会话占比。线下定位时,可以先用 `dumpsys power` 看当前活跃锁,再用 `dumpsys batterystats --charged` 或 Battery Historian 看长时间累计行为,确认这些行为是否发生在灭屏、后台、非充电这些真实高风险场景。[已验证: Android vitals 官方说明, Battery Historian 官方文档]

[图:Battery Historian 中 WakeLock 持有时长的可视化示例]

## JobScheduler / WorkManager 的省电调度策略

### 为什么要用调度框架而不是自己管 WakeLock

前面讲了 WakeLock 的滥用风险,那后台任务到底应该怎么做?答案是:不要直接操作 WakeLock,而是通过 JobScheduler 或 WorkManager 让系统代为调度。

这样做的好处是系统可以**批量执行**多个 App 的后台任务,而不是每个 App 各自唤醒系统--后者的代价是系统在 Suspend 和 Resume 之间反复切换,每次切换都需要重新初始化硬件外设。如果你在 Battery Historian 里看到灭屏期间系统被频繁唤醒（每隔几分钟就亮一次 CPU active 的短线段），大概率就是多个 App 各自设了独立的 Alarm，系统在反复进出 Suspend。换成 JobScheduler 调度后，这些零散的唤醒会被系统合并到少数几个窗口里。以 10 个 App 各自设置 Alarm 唤醒系统为例:系统要被唤醒 10 次,每次都要从 Suspend 恢复、执行任务、再回到 Suspend。而如果这 10 个 App 都通过 JobScheduler 调度,系统可以在一个维护窗口内批量执行所有任务,只经历一次唤醒-休眠周期。

### JobScheduler:系统级的任务调度

JobScheduler 在 Android 5.0(API 21)引入,允许定义带有约束条件的后台任务,由系统在合适的时机执行。约束条件包括:

- **网络条件**:只在 WiFi 下、只在非计费网络下、在任意网络下
- **充电状态**:只在充电时执行
- **设备空闲状态**:只在设备空闲时执行
- **存储空间**:只在设备有足够存储空间时执行
- **周期性执行**:设置最小间隔(最短 15 分钟)

```java
ComponentName service = new ComponentName(context, MyJobService.class);
JobInfo job = new JobInfo.Builder(JOB_ID, service)
    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_UNMETERED)  // 只在 WiFi 下
    .setRequiresCharging(true)                                // 只在充电时
    .setPeriodic(15 * 60 * 1000)                             // 每 15 分钟
    .build();

JobScheduler scheduler = (JobScheduler) context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
scheduler.schedule(job);
```

JobScheduler 的一个重要特性是:**Job 执行完必须调用 jobFinished()**。因为 JobScheduler 在执行 Job 时会持有一个以 `*job*` 开头的 WakeLock,最长执行时间 10 分钟。如果一直不结束,这个锁就不会释放,系统无法休眠。[已验证: 官方文档, developer.android.com/reference/android/app/job/JobScheduler]

### WorkManager:Jetpack 的调度方案

WorkManager 是 Jetpack 组件库中的后台任务调度方案,在底层根据 API level 自动选择使用 JobScheduler(API 23+)或 AlarmManager + BroadcastReceiver(旧版本)。相比直接使用 JobScheduler,WorkManager 提供了几个额外的好处:

**保证执行**:即使 App 进程被杀掉或设备重启,任务也会被重新调度执行。数据上传这类必须可靠完成的后台任务,正是 WorkManager 相比手动管理 WakeLock 的核心优势所在。

**约束条件组合**:可以灵活组合网络、充电、存储、电池状态等多种约束条件。

**链式任务**:可以把多个任务按先后顺序编排,依次执行。

**Expedited Job（加急任务）**：WorkManager 2.7+ 引入的机制，允许 App 请求系统尽快执行一个任务。Expedited job 使用独立的 expedited quota，但该配额仍与 App Standby Bucket 和前台状态相关；配额耗尽时按 OutOfQuotaPolicy（RUN_AS_NON_EXPEDITED_WORK_REQUEST / DROP）降级或丢弃。不能假设 expedited job 一定不受 Bucket 限制。[已验证: developer.android.com/topic/libraries/architecture/workmanager/advanced/custom-configuration]

```kotlin
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .setRequiresCharging(true)
    .build()

val uploadWork = OneTimeWorkRequestBuilder<UploadWorker>()
    .setConstraints(constraints)
    .build()

WorkManager.getInstance(context).enqueue(uploadWork)
```

[已验证: 官方文档, developer.android.com/topic/libraries/architecture/workmanager]

### 调度策略的最佳实践

**1. 优先选择充电 + WiFi 的约束组合。** 在充电状态下执行后台同步或上传,对用户体验完全没有影响。这是最"省电"的调度策略。

**2. 避免频繁的周期性任务。** JobScheduler 的最小周期是 15 分钟。如果设置了一个 15 分钟的周期任务来检查更新,考虑是否可以改用推送通知代替--由服务端在有更新时通知客户端,而不是客户端定时去拉取。

**3. 注意 Doze 和 App Standby 的交互。** 即使使用 JobScheduler 正确调度了任务,如果 App 被放到 Rare 或 Restricted Bucket,任务的执行频率仍然会被大幅降低。代码需要能够处理"任务很久没执行"的情况。

**4. 不要在 Job 中做无限期的工作。** Job 有执行时间限制(通常是 10 分钟),超时后系统会强制停止。如果任务需要更长时间,应该考虑使用前台服务,或者把大任务拆分成多个小任务。

### 在 Android 16 中的演进

Android 16 对 JobScheduler 的配额管理做了进一步优化:Active Bucket 的 App 将获得更宽裕的运行时配额;如果 App 在可见时发起的 Job 即使后来 App 不可见了,仍然按照 Active 配额执行;与前台服务同时运行的 Job 也享有更宽松的限制。[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16]

## Adaptive Battery 与 ML 预测

前面讨论的 Doze、App Standby、Background Restriction 都是基于规则的静态策略--系统根据设备状态和 App 行为套用预设的限制等级。但从 Android 9 开始,Google 引入了一种不同的思路:让系统学会预测用户行为,再据此分配资源。这就是 Adaptive Battery。

Adaptive Battery 在 Android 9(Pie)引入,是 Google 与 DeepMind 合作开发的智能功耗管理功能。它的核心思想是:用机器学习来预测用户接下来会使用哪些 App,然后据此分配系统资源。

Adaptive Battery 工作在设备端(on-device ML),不依赖云端。它观察用户的 App 使用模式--什么时候用、用多久、用完之后下一个是什么--然后把这些信息传递给 App Standby Buckets 系统,动态调整各 App 的 Bucket 分配。

实际效果方面,Google 声称 Adaptive Battery 帮助减少了约 30% 的 CPU 唤醒次数。大量用户很少使用的 App 被智能地归入 Rare 或 Restricted Bucket,它们的后台活动被大幅限制,从而减少了不必要的功耗。

在 Android 14 和 15 中,Adaptive Battery 的理念进一步演变为"Adaptive Battery 2.0"--系统不再仅仅依赖灭屏时间来判断是否限制后台活动,而是更多地依赖 ML 预测来动态调整限制策略。这标志着 Android 功耗管理从"基于规则的静态策略"向"基于学习的动态策略"的转变。[存疑: "Adaptive Battery 2.0"非 Google 官方术语,实为对 Android 14 行为变更的概括性描述][已验证: 官方文档, developer.android.com/about/versions/14/behavior-changes-14]

## Background Restriction 对后台功耗的控制

Adaptive Battery 从系统侧智能调整资源分配,而 Android 也为用户提供了手动限制 App 后台行为的机制。这两种方式互为补充:ML 预测处理大部分常见情况,用户手动干预则覆盖边缘场景。

用户侧的限制手段有三个层级,严格程度递增:

**电池优化白名单**:在 Settings > Battery > Battery optimization 中,用户可以指定哪些 App 进入电池优化豁免名单。它提供的是部分豁免,不是完全放开:这类 App 在 Doze / App Standby 中仍可使用网络并持有 partial wakelock,但常规 Alarm、Job、Sync 等后台调度限制并没有完全消失。

**后台限制开关**:Android 提供了 "Background restricted" 开关,用户可以为特定 App 禁止所有后台活动。这比 Doze 更严格--被限制的 App 不能运行 Job、不能触发 Alarm、不能访问网络(除非在前台)。

**自动限制**:从 Android 12 开始,如果系统检测到某个 App 在后台消耗了过多资源(如频繁唤醒、长时间持锁),会自动弹出通知提醒用户。如果用户确认,该 App 会被移入 Restricted Bucket。这标志着 Android 功耗管理从单纯的框架层策略转向了用户参与的"共治"模式。

### [自动发现] Android 17:能量限额制 (Energy Limiter) [待验证]

Android 17 (API 37) 公开资料提及 JobDebugInfo 等后台任务调试能力。当前可检索的官方文档未能支撑"按 App 统计后台 μJ 能量、超配额强杀进程"的完整调用链和 CDD/CTS 要求。以下内容为基于公开线索的研究假设，**发布前需要补齐 Android 17 CDD、AOSP PowerStats/ODPM 调用链或官方特性页证据**。

假设性机制：系统通过 ODPM(On-Device Power Monitor)或等效硬件计数器，按 App 统计后台运行期间消耗的微焦耳 (μJ) 能量。当累计值超过配额时，系统终止该 App 的后台进程。配额大小与 App 的 Standby Bucket 挂钩。

对开发者的潜在影响（待验证）：
- 长时间高 CPU 占用的后台同步可能需要拆分为短时间片
- 单位时间内的功耗密度可能成为新的管控维度
- 低电量模式下能量配额可能被动态压缩

[待验证: 需 Android 17 CDD、AOSP service/PowerStats/ODPM 调用链、CTS 证据补充]

## RESTRICTED Bucket 与 Exemption 机制

上面提到的自动限制机制,最终会把 App 推入一个最严格的 Standby 等级--Restricted Bucket(Android 12 引入)。它和普通的 Rare Bucket 不同,后者只是"少给资源",而 Restricted Bucket 是"几乎不给资源"。进入这个 Bucket 的 App 面临的限制包括:

- 每天只能在 10 分钟的批量会话中运行 Job
- 每天只能触发一次 Alarm
- 网络访问受到严格限制
- 前台服务启动受到限制

哪些 App 会被放入 Restricted Bucket?主要依据是 App 的后台行为:

- 长时间持有 PARTIAL_WAKE_LOCK
- 频繁触发 Alarm(特别是灭屏期间)
- 大量使用 JobScheduler 但任务执行时间过长
- 在后台运行不必要的长时间操作

不过,也有豁免(Exemption)机制。某些类型的 App 可以申请豁免:

- 设备管理员(Device Admin)App
- 正在运行前台服务的 App
- 用户手动设置为"不受优化"的 App

对于开发者来说，要确保 App 在后台行为良好,避免触发系统的自动限制。一旦 App 被放入 Restricted Bucket,它的后台功能基本就瘫痪了。

## 版本演进

Android 功耗管理框架经历了一个从"粗粒度管控"到"精细化、智能化管控"的演进过程:

| Android 版本 | 关键变更 | 影响 |
|:---|:---|:---|
| 5.0 (API 21) | JobScheduler 引入 | 首次提供系统级后台任务调度 |
| 6.0 (API 23) | Doze 模式 + App Standby | 灭屏后台活动首次被系统性限制 |
| 7.0 (API 24) | Light Doze | 不要求静止,灭屏即可触发轻度限制 |
| 8.0 (API 26) | 后台服务限制 + 后台执行收紧 | 后台组件更难长期维持活跃状态 |
| 9.0 (API 28) | App Standby Buckets + Adaptive Battery | 五级分桶 + ML 预测资源分配 |
| 12 (API 31) | Restricted Bucket + 自动限制通知 | 最严格 Standby 等级 + 用户参与共治 |
| 14 (API 34) | 前台服务类型强制化 | 后台启动前台服务需声明具体类型 |
| 16 (API 36) | JobScheduler 配额优化 | Active Bucket 配额更宽裕,可见时发起的 Job 更容易保留高配额 |
| 17 (API 37) | JobDebugInfo 调试能力 + onVsyncIdle 显示空闲回调 | 后台任务调试信息增强;HWC display idle 通知 SurfaceFlinger 重新同步 |

从这张表可以看出,Android 的功耗管理策略越来越依赖系统侧的主动管控,而非依赖 App 开发者的自觉行为。对于 App 开发者来说,趋势很明确:尽量少用直接 WakeLock,更多依赖 JobScheduler / WorkManager 的系统调度。对于系统开发者来说,理解 PMS 的决策逻辑和各版本的行为差异,是分析功耗问题的关键基础。

## 常见问题与误区

### 误区 1:"我的 App 没有申请 WakeLock,所以不会导致灭屏耗电"

不一定。WakeLock 只是阻止系统休眠的一种方式。其他方式包括:频繁的 Alarm 唤醒、JobScheduler 的频繁执行、持续的网络访问、音频播放等。在 Battery Historian 中,我们需要综合看所有维度,而不只是 Wakelock。

### 误区 2:"WorkManager 会保证我的任务在指定时间执行"

不会。WorkManager 的设计原则是"保证执行,但不保证时间"。它会尽量满足设置的约束条件,但最终执行时间由系统决定,可能会因为 Doze、App Standby、电池电量等因素被推迟。

### 误区 3:"App 进入 Doze 白名单就不用担心功耗了"

错误。进入白名单只意味着 App 获得了部分豁免,例如网络和 partial wakelock 能力;常规 Alarm、Job、Sync 仍可能继续受 Doze / App Standby 限制。它也不等于可以无限制地在后台运行。如果 App 在豁免状态下仍持续消耗资源,用户仍然可能手动开启"后台限制"。

### 误区 4:"CPU 空闲时就不耗电了"

CPU 空闲(idle)和系统休眠(suspend)是完全不同的状态。CPU idle 只是当前没有任务可执行,但 CPU 仍然在运行,仍然在消耗电量(虽然比满负荷时低得多)。只有系统进入 Suspend 后，CPU 才停止执行，功耗降到最低。一个持有 PARTIAL_WAKE_LOCK 的 App 即使什么也不做,也阻止了系统进入 Suspend。

## 与其他章节的关联

本节讨论的 Android 功耗管理框架,与前面几节形成了完整的功耗分析链条:

- **5.1 Linux 进程调度基础**:CPU 调度策略决定了哪些任务在运行,运行的任务决定了功耗
- **5.2 EAS 能量感知调度**:在任务必须运行时,EAS 选择能效比最高的 CPU 核心
- **5.3 大小核架构**:大小核的硬件设计为功耗优化提供了物理基础
- **5.4 DVFS 与功耗管理**:DVFS 根据负载动态调整频率和电压,是运行时功耗优化的核心
- **5.5 Thermal 管控**:高温时限制频率和任务,从另一个维度控制系统功耗
- **5.10 JobScheduler/WorkManager 调度与后台任务性能**:本节涉及的调度框架在 §5.10 有更深入的性能分析,包括 Android 17 新增的 JobDebugInfo API 和 Play Store wakelock 惩罚政策
- **11.5 Wakelock 机制与功耗分析**:从 Perfetto 视角详细分析 WakeLock 的持有时长、滥用检测与系统限制机制
- **11.1 Android 功耗模型** / **11.2 App 耗电优化**:从 App 视角更深入地讨论功耗优化策略

本章从底层 CPU 硬件架构和调度策略（5.1-5.3）讲到运行时频率电压控制（5.4）、热管理（5.5），再进入 Android 框架层的功耗管理（本节），构成一条从硬件到软件、从微观到宏观的功耗管理路径。

## 参考资料

- [AOSP PowerManagerService](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java)
- [AOSP PowerManager](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/java/android/os/PowerManager.java)
- [Android 官方文档: Optimize for Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby)
- [Android 官方文档: App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [Android 官方文档: Battery Historian](https://developer.android.com/topic/performance/power/setup-battery-historian)
- [Android 官方文档: WorkManager](https://developer.android.com/topic/libraries/architecture/workmanager)
- [Android 官方文档: Power Profiler](https://developer.android.com/studio/profile/power-profiler)
- [Android 官方文档: Power values configuration](https://source.android.com/docs/core/power)
- [Android 16 Behavior Changes: JobScheduler](https://developer.android.com/about/versions/16/behavior-changes-16)
- [Android 官方文档: PowerManager API reference](https://developer.android.com/reference/android/os/PowerManager)
- [抖音功耗优化实践](https://mp.weixin.qq.com/s/抖音功耗优化实践)
- [BatteryHistorian Android手机耗电分析神器](https://mp.weixin.qq.com/s/BatteryHistorian)
- [SoC低功耗问题定位及优化的10个思路](https://mp.weixin.qq.com/s/SoC低功耗问题定位)

### Android 16 Headroom API 的真相:一条走 Power HAL 而非 PSI 的 CPU/GPU 前瞻信号通道
- 来源:/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android 16 Headroom API 的真相:一条走 Power HAL 而非 PSI 的 CPU:GPU 前瞻信号通道.md
- 类型:DeepResearch 调研结果
- 摘要:基于 AOSP 16 逐层拆解 `getCpuHeadroom()/getGpuHeadroom()` 调用链,澄清它经 `SystemHealthManager → IHintManager → HintManagerService → Power HAL v6` 获取 CPU/GPU 产能余量,不走 PSI/lmkd,也不存在公开 memory headroom;适合做相机、游戏等重负载场景的前瞻降级信号。
- 注入时间:2026-04-23
- 价值:把 Headroom API 与 PSI/lmkd 边界说清楚,能避免把产能信号误当成内存压力接口。
