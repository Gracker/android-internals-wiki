---
title: "OEM 厂商差异化后台限制与功耗诊断实战"
chapter: "25.14"
section: "25.14"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [oem-doze, background-restriction, power-optimization, vendor-doze, chinese-oem]
related_chapters: ["25.2", "25.3", "25.4", "25.15", "11.2", "11.3"]
last_verified: "2026-07-25"
confidence: medium-high
sources:
- type: deepresearch
  path: DeepResearch/2026-07-16-android17-oem-background-restriction.md
last_body_apply_at: "2026-07-25T15:18:53+08:00"
last_body_apply_run_id: "20260725-151525-21e58a30"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-07-25T16:05:49+08:00"
last_review_finalize_run_id: "20260725-160531-5200f347"
---

# OEM 厂商差异化后台限制与功耗诊断实战

平台基线为 Android 17（API 37，`android-17.0.0_r1`）。排查 OEM 后台问题时，不从“某厂商会杀应用”的传闻出发，而是先回答三个有证据可查的问题：

1. AOSP 当前如何评价这个 package/UID：限制等级、待机分组和豁免原因是什么？
2. Job、Alarm、前台服务、网络或进程生命周期中的哪一层没有按预期推进？
3. 两台设备的 AOSP 状态相同时，厂商侧又增加了什么设置、服务、冻结或清理动作？

先校正两个容易误导排查的细节。Android 17 的命令是 `cmd activity get-bg-restriction-level`，没有 `background get-restriction-level` 这一层子命令；`AppRestrictionController` 的 XML 位于每用户的 `/data/system_de/<userId>/apprestriction/settings.xml`，不是 `/data/system/apprestriction/settings.xml`。正文中的命令和路径均按源码校正后的形式给出。

## AOSP 后台限制不是一个总开关

“后台不工作”可能来自多套相互独立的机制：

| 层次 | 典型状态 | 主要影响 |
| --- | --- | --- |
| App Standby | active、working set、frequent、rare、restricted | Job、Alarm、网络等后台资源配额 |
| Background restriction | 用户或系统记录的后台限制状态 | 更严格的后台执行、Job、Alarm 和前台服务行为 |
| Doze / Battery Saver | 设备空闲、低电模式、临时白名单 | 全设备范围的网络、Alarm、Job 推迟 |
| FGS 与后台启动规则 | FGS 类型、启动豁免、运行时限 | Service 能否启动、晋升并持续运行 |
| 进程管理 | cached freezer、LMKD、force-stop、厂商清理 | 进程是否存在、何时可再次启动 |
| 任务自身 | WorkManager 约束、Job 配额、Alarm 类型 | 某项具体任务能否获得执行机会 |

这些状态可能同时出现，也可能只有一项变化。只看进程消失、`dumpsys deviceidle` 或设置页中的“允许后台活动”，都不足以确定原因。

## `AppRestrictionController` 怎样形成限制等级

Android 17 的入口位于 `frameworks/base/services/core/java/com/android/server/am/AppRestrictionController.java`。它维护持久化的 package/UID 限制设置，监听用户限制、App Standby、角色、DeviceConfig 和系统豁免，并汇总多个 `BaseAppStateTracker` 的建议。

下面是 Android 17 初始化 tracker 的源码骨架：

```java
void initAppStateTrackers(AppRestrictionController controller) {
    mAppBatteryTracker = new AppBatteryTracker(mContext, controller);
    mAppBatteryExemptionTracker = new AppBatteryExemptionTracker(mContext, controller);
    mAppFGSTracker = new AppFGSTracker(mContext, controller);
    mAppMediaSessionTracker = new AppMediaSessionTracker(mContext, controller);
    mAppPermissionTracker = new AppPermissionTracker(mContext, controller);
    controller.mAppStateTrackers.add(mAppBatteryTracker);
    controller.mAppStateTrackers.add(mAppBatteryExemptionTracker);
    controller.mAppStateTrackers.add(mAppFGSTracker);
    controller.mAppStateTrackers.add(mAppMediaSessionTracker);
    controller.mAppStateTrackers.add(mAppPermissionTracker);
    controller.mAppStateTrackers.add(new AppBroadcastEventsTracker(mContext, controller));
    controller.mAppStateTrackers.add(new AppBindServiceEventsTracker(mContext, controller));
}
```

这七个 tracker 的职责并不相同。`AppBatteryTracker` 可以依据后台耗电提出限制等级；FGS、媒体会话、权限、广播和绑定服务 tracker 记录相应活动；`AppBatteryExemptionTracker` 用于核算应从后台耗电中排除的部分。不能把“在 tracker 列表中”直接解释为“每个 tracker 都会单独限制应用”。

当多个 policy 提出候选等级时，控制器选择数值更大的等级，并保留对应 tracker 信息：

```java
for (int i = mAppStateTrackers.size() - 1; i >= 0; i--) {
    final int proposed = mAppStateTrackers.get(i).getPolicy()
            .getProposedRestrictionLevel(packageName, uid, maxLevel);
    level = Math.max(level, proposed);
    if (level != previousLevel) {
        resultTracker = mAppStateTrackers.get(i);
        previousLevel = level;
    }
}
```

这是 tracker 汇总阶段的规则，不是完整决策。控制器还会先处理休眠、force-stop、系统豁免、用户后台限制和当前 standby bucket；其中 `BACKGROUND_RESTRICTED` 不能仅凭 tracker 自动进入，源码明确要求用户同意该级别。

### 限制等级要看名称和来源

Android 17 定义的主要等级如下：

| 数值 | 名称 | 源码语义 |
| ---: | --- | --- |
| 0 | `UNKNOWN` | 尚无有效等级 |
| 10 | `UNRESTRICTED` | 只为少量系统进程预留的最宽状态 |
| 20 | `EXEMPTED` | 用户或系统豁免状态，但不等于不受任何保护规则约束 |
| 30 | `ADAPTIVE_BUCKET` | 普通应用的默认层次，由待机分组继续细分 |
| 40 | `RESTRICTED_BUCKET` | 处于 restricted standby bucket |
| 50 | `BACKGROUND_RESTRICTED` | 用户启用的后台限制 |
| 60 | `FORCE_STOPPED` | 应用处于 force-stop 状态 |
| 70 | `USER_LAUNCH_ONLY` | 只有用户启动后才能恢复的更严格状态 |
| 90 | `CUSTOM` | 为定制限制保留的等级 |

数值可以帮助阅读源码的 `Math.max()`，诊断报告仍要记录名称、变更时间以及能够取得的 reason、subReason 和 source。`FORCE_STOPPED` 是生命周期状态，不能简单归因为耗电超限；`EXEMPTED` 也不是 CPU、网络和前台服务规则的通行证。

## OEM 可以改变哪些 AOSP 输入

### 静态 SystemConfig 豁免

`SystemConfig` 会从允许覆盖应用限制的系统分区配置中解析 `bg-restriction-exemption`。配置项的形式如下：

```xml
<permissions>
    <bg-restriction-exemption package="com.example.systemapp" />
</permissions>
```

`AppRestrictionController` 通过 `SystemConfig.getBgRestrictionExemption()` 读取这份集合。厂商预装应用若在此列表中，不能作为普通三方应用的对照样本。静态豁免可用 `cmd activity list-bg-exemptions-config` 查看，是否能修改取决于系统镜像和构建权限。

### DeviceConfig 与其他豁免来源

`activity_manager` 命名空间中的 `bg_restriction_exempted_packages` 提供运行时包名集合。除此之外，控制器还会检查 UID 和 package 级原因，包括：

- core UID、系统 Device Idle allowlist 和演示模式；
- 系统模块、运营商特权应用；
- DPC 保护应用、活动设备管理员；
- `OP_SYSTEM_EXEMPT_FROM_POWER_RESTRICTIONS`；
- VPN 相关 AppOp、拨号和紧急角色；
- 用户 Device Idle allowlist、关联的 Companion Device 应用。

这是后台限制控制器的豁免判断，不代表这些应用在 JobScheduler、AlarmManager、FGS 或网络子系统中处处免检。排查时应分别确认每套 allowlist 的适用范围。

下面的只读命令分别查看静态豁免、DeviceConfig 包集合和 Device Idle 白名单：

```bash
adb shell cmd activity list-bg-exemptions-config
adb shell device_config get \
  activity_manager bg_restriction_exempted_packages
adb shell dumpsys deviceidle whitelist
```

三条输出来自不同配置源。不要把某个包出现在 Device Idle 白名单中，写成它已经命中 `bg-restriction-exemption`。

## `AppBatteryExemptionTracker` 记录的是耗电扣除区间

这个类按 UID 维护各 package 当前活跃的状态位。当同一 UID 中第一个 package 进入某类可豁免状态时，它为 UID 增加开始事件；同 UID 的 package 全部离开该状态时增加结束事件。

下面的源码片段展示了按 UID 合并状态的关键判断：

```java
if (start) {
    boolean alreadyStarted = false;
    for (int i = pkgsStates.size() - 1; i >= 0; i--) {
        if ((pkgsStates.valueAt(i) & stateType) != 0) {
            alreadyStarted = true;
            break;
        }
    }
    if (!alreadyStarted) {
        addEvent = true;
    }
} else {
    // 只有同 UID 的所有 package 都结束该 stateType，才记录 UID 结束事件。
}
```

这样可以避免共享 UID 的两个 package 让同一段状态被重复计时。事件还记录开始和结束时的 UID 电量快照；`getUidBatteryExemptedUsageSince()` 计算这些区间内的用量，`AppBatteryTracker` 再从总后台用量中扣除它。

这里的 “exemption” 是耗电归因豁免，不是给 UID 一个固定时长的后台执行许可。源码没有“16 ms 生效延迟”或统一“豁免窗口长度”的公共契约，诊断文档不应据此给出时间保证。

## 一轮可复现的诊断

### 固定设备和应用条件

每次采样都记录以下信息：

- build fingerprint、增量版本、安全补丁和厂商系统版本；
- 应用 versionCode、targetSdk、安装来源、用户 ID 与 UID；
- 电量、充电状态、Battery Saver、Doze、网络和屏幕状态；
- 厂商设置页中与自启动、后台活动、电池优化、锁屏清理相关的选项；
- 测试动作、进入后台时间、预期执行时间和观测窗口。

同一 APK 在两台设备上对比时，账号、网络、充电、屏幕、用户设置和测试时间线必须一致。否则差异可能来自输入条件，而不是 ROM。

### 读取 AOSP 限制状态

下面的命令获取限制等级、待机分组和三类豁免输入：

```bash
PACKAGE=com.example.app

adb shell cmd activity get-bg-restriction-level \
  --user current "$PACKAGE"
adb shell am get-standby-bucket \
  --user current "$PACKAGE"
adb shell cmd activity list-bg-exemptions-config
adb shell device_config get \
  activity_manager bg_restriction_exempted_packages
adb shell dumpsys deviceidle whitelist
```

`get-bg-restriction-level` 输出的是 `exempted`、`adaptive_bucket`、`restricted_bucket` 等名称。它和 App Standby bucket 相关但不相同；报告中应保留两项原始输出。

应用自身也可以记录公开 API 可见的两个状态：

```kotlin
val activityManager = getSystemService(ActivityManager::class.java)
val usageStatsManager = getSystemService(UsageStatsManager::class.java)

Log.i(
    "BgState",
    "backgroundRestricted=${activityManager.isBackgroundRestricted}, " +
        "standbyBucket=${usageStatsManager.appStandbyBucket}",
)
```

`isBackgroundRestricted` 只回答当前应用是否被用户置于后台限制状态，`appStandbyBucket` 返回本应用待机分组。它们不暴露系统服务内部的完整 restriction level、reason 或 tracker 详情。

### 保存控制器与子系统快照

Android 17 没有 `dumpsys activity bg-restriction exemption-reason`、`dumpsys activity restriction <package>` 或 `restriction trackers` 这些文本子命令。`AppRestrictionController.dump()` 会在完整 `dumpsys activity -a` 的末尾输出 `APP BACKGROUND RESTRICTIONS`，其中包含设置、policy 配置和各 tracker。

下面的命令保存 AMS、进程退出、Job、Alarm 和 Device Idle 证据：

```bash
PACKAGE=com.example.app

adb shell dumpsys activity -a > activity-full.txt
adb shell dumpsys activity exit-info "$PACKAGE" > exit-info.txt
adb shell dumpsys jobscheduler > jobscheduler.txt
adb shell dumpsys alarm > alarm.txt
adb shell dumpsys deviceidle > deviceidle.txt
adb shell dumpsys package "$PACKAGE" > package.txt
```

这些文件应在复现前、预期触发点和失败后各保存一次。`activity-full.txt` 很大，可以在主机上检索 `APP BACKGROUND RESTRICTIONS`、包名和 UID；不要依赖固定行号或把其他版本的私有 dumpsys 子命令当作 Android 17 接口。

### 确认进程为何退出

应用可通过 `ApplicationExitInfo` 记录近期进程退出原因：

```kotlin
val activityManager = getSystemService(ActivityManager::class.java)
val exits = activityManager.getHistoricalProcessExitReasons(
    packageName,
    0,
    20,
)

for (exit in exits) {
    Log.i(
        "ExitInfo",
        "time=${exit.timestamp}, reason=${exit.reason}, " +
            "status=${exit.status}, importance=${exit.importance}, " +
            "description=${exit.description}",
    )
}
```

`REASON_LOW_MEMORY`、`REASON_USER_REQUESTED`、`REASON_USER_STOPPED`、`REASON_EXCESSIVE_RESOURCE_USAGE` 和 `REASON_SIGNALED` 指向不同排查方向。`REASON_SIGNALED` 只能证明进程因信号退出，不能单独证明是某个厂商清理组件发起。

## 如何从证据定位层次

| 观察结果 | 下一步 |
| --- | --- |
| restriction level 已是 `background_restricted` 或 `force_stopped` | 核对用户设置、reason/source、设置变更时间，不先分析 Worker 代码 |
| 两台设备 restriction level 不同 | 对比 standby bucket、SystemConfig、DeviceConfig、Device Idle allowlist、DPC/角色和 AppOp |
| restriction level 相同，Job 状态不同 | 对比 `dumpsys jobscheduler` 的约束、配额、停止原因和 standby 信息 |
| Job 已启动但业务无结果 | 检查 Worker/Service 日志、超时、网络绑定、幂等和外部服务响应 |
| Alarm 未进入交付 | 对比 Alarm 类型、精确闹钟权限、Doze、配额与应用待机分组 |
| 进程退出但限制状态相同 | 查看 `ApplicationExitInfo`、LMKD、force-stop、ANR、crash、冻结和厂商进程管理日志 |
| AOSP 输出一致，厂商机仍稳定复现差异 | 再进入 bugreport 中的 vendor 服务、私有设置、属性和事件日志 |

“AOSP 输出一致”不等于“AOSP 没有影响”。JobScheduler、Alarm、网络和 FGS 都有自己的状态，需要在相同时间窗内一起对比。反过来，发现厂商服务包名也不能直接证明它执行了清理；需要对应的调用、事件或状态变化。

## XML 只用于系统侧复核

`RestrictionSettings.getXmlFileNameForUser()` 使用 `Environment.getDataSystemDeDirectory(userId)`，因此文件路径是：

```text
/data/system_de/<userId>/apprestriction/settings.xml
```

XML 保存 package、UID、当前限制等级、变更时间、组合后的 reason 以及通知时间等状态。普通 user build 通常不能直接读取该文件；root/userdebug 设备可以在复现前后比较，但不要修改它来模拟用户操作。控制器使用 `AtomicFile` 写入，绕过服务直接改文件还会与内存状态不一致。

## 应用侧怎样降低厂商差异

- 可延迟、需要持久化的工作使用 WorkManager，并把每次执行设计为幂等、可重入。
- 需要持续向用户提供能力时使用合法类型的前台服务，按 Android 17 的后台启动、权限和运行时限处理失败。
- 推送只用于提示应用有新工作，业务状态保存在服务端；不能假定每条消息都会在相同时间到达。
- 重要本地状态在产生时持久化，不依赖进程退出回调。
- 对外部副作用使用业务幂等键和检查点，进程被停止后可以从已确认位置继续。
- 只有核心功能确受影响时，才向用户解释具体系统设置；不要默认引导所有用户关闭电池优化，也不要跳转未经文档保证的厂商私有 Activity。

厂商限制无法由应用代码完全消除。可维护的目标是：在 AOSP 允许的执行窗口内完成尽量少的工作，任何中断都能恢复，并让诊断日志说明任务停在哪一层。

## 参考源码与官方文档

- [Android 17 `AppRestrictionController`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppRestrictionController.java)
- [Android 17 `AppBatteryExemptionTracker`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/AppBatteryExemptionTracker.java)
- [Android 17 `ActivityManager` 限制等级](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [Android 17 `ActivityManagerShellCommand`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)
- [Android 17 `SystemConfig`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/SystemConfig.java)
- [Android 后台优化总览](https://developer.android.com/topic/performance/background-optimization)
- [App Standby Buckets](https://developer.android.com/topic/performance/appstandby)
- [ApplicationExitInfo API](https://developer.android.com/reference/android/app/ApplicationExitInfo)
