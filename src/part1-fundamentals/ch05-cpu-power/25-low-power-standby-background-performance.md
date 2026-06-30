---
title: "Android Low Power Standby 深度休眠与后台任务性能边界"
chapter: "5.25"
status: ready-for-review
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [low-power-standby, power-management, background-tasks, deep-sleep, android-tv, wakelock, network-block]
related_chapters: ["5.6", "5.8", "5.17", "5.21", "5.23", "5.24", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
drafted_date: "2026-07-01"
last_verified: "2026-07-01"
last_verified_against: "AOSP android-17.0.0_r1; Mishaal Rahman Android 13 Changelog; Android Developers official docs"
confidence: medium
sources:
  - type: blog
    path: "Obsidian/Cubox/Android 13 changelog- A deep dive by Mishaal Rahman-2022-08-22.md"
    note: "Android 13 Low Power Standby 首次发现与分析，确认 Android 13 引入"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
    note: "PowerManagerService 中 LowPowerStandby 状态管理逻辑"
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
    note: "PowerManager 公共 API — isLowPowerStandbyEnabled()"
  - type: aosp
    path: "frameworks/base/core/res/res/values/config.xml"
    note: "config_lowPowerStandbySupported / config_lowPowerStandbyEnabledByDefault 框架配置"
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerManager"
    note: "PowerManager 公共 API 参考"
  - type: official
    path: "https://source.android.com/docs/core/power"
    note: "AOSP 电源管理官方文档"
---

# 5.25 Android Low Power Standby 深度休眠与后台任务性能边界

## 概述

Low Power Standby（LPS）是 Android 13（API 33）引入的一种系统级深度省电模式。它的设计初衷是让**始终通电（always-on）设备**——如 Android TV、机顶盒、车载信息娱乐系统——在用户不主动操作时进入极低功耗的待机状态。与 Doze 不同，LPS 并不依赖设备运动状态判定，而是面向那些天然"静止"的设备形态。

到了 Android 15-17，LPS 的适用范围和 API 能力逐步扩展，部分 OEM 开始在手机形态上探索利用 LPS 限制长时间不活动的后台进程。理解 LPS 的触发机制、限制清单和调试方法，对于分析 IoT/TV 类设备的后台任务异常、消息延迟和功耗问题至关重要。

> ⚠️ **重要更正**：LPS 最初在 Android 13 引入，而非部分资料所称的 Android 15。大纲中"设备静止（加速度计判定）"的描述不准确——LPS 原始设计面向天然静止的 TV/STB 设备，不依赖运动传感器。[已验证: Mishaal Rahman Android 13 Changelog, 2022]

---

## 要点

### 🔹 Low Power Standby 定位与设计目标

#### 起源：EU 待机功耗法规

LPS 的设计直接呼应欧盟生态设计指令（Ecodesign Directive）对网络设备待机功耗的要求——该法规要求网络设备在待机模式下功耗不超过 2-8W（视具体设备类别）。Android TV 设备在用户关闭屏幕后仍可能因为后台 App 活动（同步、推送、传感器轮询）而消耗额外功耗，LPS 正是为了消除这部分"待机泄漏"。[已验证: EU Ecodesign Directive, mode-standby-and-networked-standby]

#### 与 Doze 的核心区别

| 维度 | Doze | Low Power Standby |
|------|------|-------------------|
| **引入版本** | Android 6.0 (API 23) | Android 13 (API 33) |
| **设计目标设备** | 所有手持设备 | 优先 TV/STB/IoT，可扩展 |
| **触发条件** | 屏幕关闭 + 设备静止 + 未充电 | 设备配置支持 + 屏幕关闭/进入待机 |
| **运动传感器依赖** | 是（加速度计判定静止） | 否（面向天然静止设备） |
| **网络限制** | 后台网络暂停（维护窗口放开） | 后台网络完全阻断（维护窗口放开） |
| **WakeLock** | 普通应用 wakelock 不能绕过 Doze | wakelock 被直接禁用 |
| **维护窗口** | 有，间隔逐渐拉长 | 有，与 Doze 维护窗口对齐 |
| **配置方式** | 系统自动触发 | 需要框架配置 `config_lowPowerStandbySupported=true` |

[已验证: Android Developers Doze/Standby 文档; Mishaal Rahman Android 13 Changelog]

#### 与 App Hibernation、App Standby 的层级关系

Android 的后台限制体系是一个多层叠加模型。由外到内：

1. **App Standby Bucket**（Android 9+）：根据应用使用频率分配配额（Active → Working Set → Frequent → Rare → Restricted）
2. **Doze**（Android 6+）：设备级状态机，灭屏+静止触发
3. **Low Power Standby**（Android 13+）：设备形态级开关，灭屏即触发（无需静止）
4. **App Hibernation**（Android 12+）：长时间未使用的应用被强制休眠（详见 5.24 节）

LPS 处于"Doze 之上"的限制层——当设备配置支持 LPS 时，它会在 Doze 的基础上施加额外限制。如果 LPS 和 Doze 同时激活，应用受到两者的叠加约束，限制更严格的生效。

---

### 🔹 触发条件与状态机

#### 框架配置层

LPS 默认在所有 Android 设备上**关闭**。启用需要两步：

**第一步：设备框架配置**

在 `frameworks/base/core/res/res/values/config.xml` 中设置：

```xml
<!-- 是否支持 Low Power Standby -->
<bool name="config_lowPowerStandbySupported">true</bool>
<!-- 是否默认开启（可选） -->
<bool name="config_lowPowerStandbyEnabledByDefault">false</bool>
```

通常通过 device overlay 覆盖此配置。Pixel 手机默认不启用 LPS；Android TV 和部分车载设备默认启用。

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/res/res/values/config.xml]

**第二步：运行时开关**

即使框架配置支持，LPS 也可以通过 Settings 数据库动态控制：

```
Settings.Global.LOW_POWER_STANDBY_ENABLED = 0 或 1
```

可通过 `adb` 命令切换：

```bash
# 查看当前状态
adb shell settings get global low_power_standby_enabled

# 开启 LPS
adb shell settings put global low_power_standby_enabled 1

# 关闭 LPS
adb shell settings put global low_power_standby_enabled 0
```

[已验证: AOSP android-17.0.0_r1, Settings.Global 字段定义]

#### PowerManagerService 状态管理

在 AOSP `android-17.0.0_r1` 中，LPS 的核心状态管理位于 `PowerManagerService.java`：

```java
// PowerManagerService.java (android-17.0.0_r1)
// 关键字段
private boolean mLowPowerStandbySupported;    // 从 config.xml 读取
private boolean mLowPowerStandbyEnabled;       // 运行时状态，同步自 Settings.Global

// 在 updatePowerStateLocked() 中，mLowPowerStandbyEnabled 会影响：
// 1. WakeLock 审批：如果 LPS 激活，新申请的 wakelock 被拒绝
// 2. 网络策略：通知 NetworkPolicyManager 对后台应用实施网络限制
// 3. 与 Doze 状态的交互：LPS 激活时不影响 Doze 自身的状态机
```

PMS 在 `updatePowerStateLocked()` 的主循环中检查 LPS 状态。如果 LPS 处于激活态，系统会在 Doze 维护窗口期间**临时放开** wakelock 和网络限制，允许应用执行必要的后台操作。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java]

#### 公共 API

应用可以通过 `PowerManager` 查询 LPS 状态：

```java
PowerManager pm = (PowerManager) context.getSystemService(Context.POWER_SERVICE);

// 查询 LPS 是否启用（API 33+）
boolean isLpsEnabled = pm.isLowPowerStandbyEnabled();
```

`isLowPowerStandbyEnabled()` 返回的是 `Settings.Global.LOW_POWER_STANDBY_ENABLED` 的值。注意：此方法返回的是系统全局 LPS 开关状态，不代表设备当前处于 LPS 活动态（LPS 活动还需要屏幕关闭等条件）。

[已验证: Android Developers, PowerManager 公共 API 参考]

#### 与 Doze 维护窗口的交互

LPS 的限制并非永久生效。当 Doze 进入维护窗口（maintenance window）时，LPS 的 wakelock 禁用和网络阻断会被**临时解除**，允许应用执行同步、Job 等操作。维护窗口结束后，限制恢复。

这意味着 LPS 实际上是"跟随 Doze 节奏"的——Doze 维护窗口的间隔会随着灭屏时间逐渐拉长（从几分钟到几十分钟），LPS 限制的"呼吸"节奏也跟随这个周期。

---

### 🔹 Low Power Standby 对后台任务的限制清单

LPS 激活时，后台应用面临以下限制：

| 子系统 | LPS 限制行为 | 与 Doze 对比 |
|--------|-------------|-------------|
| **WakeLock** | 被直接禁用，新申请的 wakelock 不生效 | Doze 不禁用 wakelock，但 wakelock 无法绕过 Doze 的网络/Job 限制 |
| **网络访问** | 后台网络完全阻断 | Doze 暂停后台网络，维护窗口放开 |
| **JobScheduler** | 非紧急 Job 被推迟到维护窗口 | 同 Doze |
| **AlarmManager** | 非精确闹钟被推迟；精确闹钟（setExact/setAlarmClock）不受影响 | 同 Doze |
| **前台服务（FGS）** | 已运行的 FGS 不被杀死，但受到网络限制影响 | Doze 不直接限制 FGS |
| **Sync（ContentResolver）** | 被推迟到维护窗口 | 同 Doze |
| **FCM（Firebase Cloud Messaging）** | 高优先级 FCM 可正常投递；普通优先级被推迟 | 同 Doze |

[已验证: Mishaal Rahman Android 13 Changelog; Android Developers Doze/Standby 文档]

**关键细节**：

1. **wakelock 禁用是 LPS 最显著的区别**。在 Doze 模式下，应用仍然可以持有 wakelock 保持 CPU 唤醒（虽然不能绕过网络限制）。但在 LPS 下，wakelock 本身就被禁用——这意味着应用无法通过持有 wakelock 来保持 CPU 活跃。

2. **网络阻断是硬性的**。Doze 的网络限制有维护窗口放开的机制，但 LPS 的网络阻断在维护窗口外是完全的。应用层无法通过任何 API 绕过。

3. **前台服务仍可运行**但功能受限。一个播放音乐的前台服务在 LPS 下不会被系统杀死，但由于网络被阻断，它无法从服务器拉取新的音频流数据。

4. **电池优化豁免名单的应用**部分豁免：它们可以使用网络并持有 wakelock，但仍然受到 Job/Sync 延迟的限制（与 Doze 下的豁免行为一致）。[已验证: Android Developers, Optimize for Doze and App Standby]

---

### 🔹 对应用性能的实际影响

#### 典型场景分析

**场景 1：Android TV 上的即时通讯 App**

设备：小米 TV Box（Android 13+，LPS 默认启用）
影响：用户关闭电视屏幕 10 分钟后，LPS 激活。IM App 的后台长连接被网络阻断切断，新消息无法推送到达。直到下一个 Doze 维护窗口（可能 15-30 分钟后），网络临时恢复，FCM 高优先级消息推送到达并唤醒 App。

实际延迟：消息延迟可达 15-30 分钟，取决于 Doze 维护窗口周期。
应对：使用 FCM 高优先级消息（`priority: high`），FCM 在 LPS 下不受网络阻断限制。

**场景 2：车载设备上的导航 App**

设备：车载信息娱乐系统（Android 14 Automotive，LPS 可能启用）
影响：车辆熄火后系统进入待机，LPS 激活。导航 App 的路况数据同步被阻断，交通事件实时推送不可用。

应对：在车辆唤醒事件（如 CAN bus 信号）上注册 `JobScheduler` 的 expedited job，利用维护窗口外的紧急执行通道。

**场景 3：手机上的邮件同步（OEM 扩展场景）**

部分 OEM（如某些国产厂商）可能在手机形态上启用 LPS 或类似的深度省电逻辑。夜间放置不动的手机在 LPS 激活后，邮件 App 的定期同步被推迟到维护窗口。

应对：使用 `WorkManager` 的 expedited job 或 `setExactAndAllowWhileIdle` 闹钟保障关键同步的准时性。

#### CPU 调度影响

LPS 激活后，系统进入极低功耗状态：

- **CPU 几乎完全进入 suspend**：除了 Doze 维护窗口期间的短暂活动，CPU 大核通常完全离线，小核运行在最低频率
- **传感器批处理退化**：SensorManager 的批处理间隔被强制拉长，从毫秒级退化到秒级甚至分钟级
- **TCP keepalive 失效**：长时间网络阻断后，TCP 连接可能因为 keepalive 超时而断开。App 需要在退出 LPS 后重建网络连接

#### 与 ADPF 的交互

ADPF（Android Dynamic Performance Framework）的 Hint Session 在 LPS 激活期间处于"挂起"状态——App 的 `PerformanceHintManager.Session` 不会被主动 update，因为 CPU 频率调度本身已不活跃。App 不需要特殊处理这一情况，但应在 LPS 退出后重新提交性能 hint，以便系统快速恢复到合适的 CPU 频率。

[待验证: ADPF Hint Session 在 LPS 下的确切行为，AOSP android-17.0.0_r1 源码未直接验证]

---

### 🔹 应用适配与最佳实践

#### 检测 LPS 状态

```java
PowerManager pm = getSystemService(PowerManager.class);

// 检查 LPS 是否启用（API 33+）
if (pm.isLowPowerStandbyEnabled()) {
    // LPS 已启用，但当前不一定处于 LPS 活动态
    // LPS 活动态 = LPS 启用 AND 屏幕关闭 AND 不在 Doze 维护窗口
}

// 结合 Doze 状态判断
if (pm.isDeviceIdleMode()) {
    // 设备处于 Doze 模式
    // 如果同时 isLowPowerStandbyEnabled() 返回 true，
    // 则应用受到 LPS + Doze 的叠加限制
}
```

注意：Android 目前没有提供"LPS 活动态"的直接查询 API。应用需要综合 `isLowPowerStandbyEnabled()` + 屏幕状态 + `isDeviceIdleMode()` 自行推断。

#### 关键任务的保障策略

| 任务类型 | Doze 下的保障方式 | LPS 下的额外保障 |
|---------|-------------------|-----------------|
| **精确闹钟** | `setExactAndAllowWhileIdle()` | 同左，LPS 不限制精确闹钟 |
| **紧急后台任务** | `WorkManager expedited job` | 同左，expedited job 有独立配额 |
| **推送消息** | FCM 高优先级 | 同左，FCM 高优先级在 LPS 下正常投递 |
| **前台服务** | FGS 持续运行 | FGS 不被杀死，但网络受限 |
| **定时同步** | JobScheduler + 维护窗口 | 同左，但同步频率受维护窗口间隔制约 |

#### 网络连接重建

LPS 退出后（用户操作设备、进入 Doze 维护窗口），应用应主动重建可能已断开的网络连接：

```java
// 注册 BroadcastReceiver 监听 LPS/Doze 状态变化
IntentFilter filter = new IntentFilter();
filter.addAction(PowerManager.ACTION_DEVICE_IDLE_MODE_CHANGED);
filter.addAction(ConnectivityManager.CONNECTIVITY_ACTION);
registerReceiver(new BroadcastReceiver() {
    @Override
    public void onReceive(Context context, Intent intent) {
        PowerManager pm = context.getSystemService(PowerManager.class);
        ConnectivityManager cm = context.getSystemService(ConnectivityManager.class);
        
        // 当从 Doze/LPS 维护窗口退出空闲态时，网络恢复
        if (!pm.isDeviceIdleMode() && cm.getActiveNetworkInfo() != null) {
            // 重建长连接、重试失败请求
            reconnectToServer();
        }
    }
}, filter);
```

#### 用户引导

如果应用的核心功能依赖后台持续运行（如即时通讯），应引导用户将应用加入电池优化豁免名单：

```java
Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
intent.setData(Uri.parse("package:" + context.getPackageName()));
startActivity(intent);
```

⚠️ 加入豁免名单会增加功耗，Google Play 对申请豁免有审核政策，仅限核心功能确实需要后台持续运行的应用。

---

### 🔹 调试与验证方法

#### adb 命令

```bash
# 1. 查看 LPS 当前状态
adb shell settings get global low_power_standby_enabled

# 2. 启用/禁用 LPS（需要框架配置支持）
adb shell settings put global low_power_standby_enabled 1
adb shell settings put global low_power_standby_enabled 0

# 3. 查看框架是否支持 LPS
adb shell dumpsys power | grep -i "low.power.standby"

# 4. 强制进入 Doze（LPS 限制跟随 Doze 维护窗口）
adb shell dumpsys deviceidle force-idle deep

# 5. 强制退出 Doze
adb shell dumpsys deviceidle unforce

# 6. 模拟维护窗口（步骤）
adb shell dumpsys deviceidle step
```

#### dumpsys power 关键字段

```
dumpsys power | grep -A5 -i "low_power_standby"
```

输出中关注：
- `mLowPowerStandbySupported`：设备是否支持 LPS
- `mLowPowerStandbyEnabled`：LPS 当前开关状态
- WakeLock 列表中是否出现 "disabled by low power standby" 标记

[已验证: AOSP android-17.0.0_r1, dumpsys power 输出格式]

#### Perfetto trace 分析

在 Perfetto trace 中，LPS 活动态表现为：

1. **PowerManagement track**：出现 `LowPowerStandby` 状态标记
2. **CPU track**：大核完全离线，小核长时间处于 idle（除维护窗口的短暂 spike）
3. **Network track**：后台应用无网络活动段（维护窗口出现短暂 burst）

搜索 trace 事件：
```sql
-- Perfetto SQL 查询：LPS 维护窗口期间的 CPU 活动
SELECT ts, dur, name
FROM slice
WHERE name LIKE '%low_power_standby%' OR name LIKE '%maintenance%'
ORDER BY ts
```

#### Battery Historian 分析

在 Battery Historian 中，LPS 活动期间的特征：

- CPU running 线段几乎消失（仅维护窗口有短暂 spike）
- Network 状态长时间为 "off" 或 "background restricted"
- Wakelock 线段消失（LPS 禁用 wakelock）

将 LPS 活动时段与同期的 `device_idle` 状态对照，可以确认 LPS 是否是功耗降低的主因。

---

## 扩展

### 🔸 OEM 实现差异

#### Pixel 设备

Pixel 手机系列默认不启用 LPS（`config_lowPowerStandbySupported=false`）。Pixel 的深度省电主要依赖 Doze + App Standby Bucket + Adaptive Battery 的组合。

#### Android TV / Google TV

Google TV 设备默认启用 LPS。这是 Android 13 引入 LPS 的主要场景。在 TV 设备上，LPS 的触发不需要设备静止判定——TV 天然是静止的，只需要屏幕关闭（或进入省电模式）。

#### OEM 定制扩展

部分 OEM 在自有省电框架中实现了类似 LPS 的"超级省电"模式，但可能不使用 AOSP 的 LPS 实现。例如：
- 小米的"神隐模式"在灭屏后对后台进程施加类似但不完全相同的限制
- 三星的"睡眠模式"在特定时段限制后台活动

这些 OEM 定制方案的技术细节不公开，调试时需要参考各厂商的开发者文档。

[待验证: 各 OEM 定制省电模式与 AOSP LPS 的具体差异]

#### CDD 要求

Android Compatibility Definition Document (CDD) 对 LPS 的要求：
- LPS 是**可选**功能，CDD 不强制所有设备支持
- 如果设备声明支持 LPS（`config_lowPowerStandbySupported=true`），则必须正确实现 wakelock 禁用和网络阻断行为
- TV 类设备（Android TV / Google TV）建议启用 LPS 以满足能效法规

---

### 🔸 Low Power Standby 与端侧 AI 推理

#### 端侧模型推理调度

端侧 AI 模型（如语音唤醒、人脸检测）在 LPS 下面临特殊挑战：

1. **语音唤醒（Hotword Detection）**：`HotwordDetectionService` 运行在前台服务中，LPS 不会杀死 FGS。但 LPS 的网络阻断可能影响依赖云端验证的热词流程。Android 的 `AlwaysOnHotwordDetector` 有离线验证路径，可绕过网络限制。

2. **NNAPI / TFLite 推理**：LPS 不直接限制 NNAPI 调用，但 CPU/GPU 处于极低频率时，推理延迟可能显著增加（10-100 倍）。建议在 LPS 期间推迟非紧急推理任务。

3. **ADPF Hint Session**：在 LPS 下，Hint Session 的 `reportActualWorkDuration()` 调用不会产生实际的 CPU 频率调整效果，因为系统已经决定了极低频率策略。App 不需要主动暂停 hint 上报，但应知道这些上报在 LPS 期间是"空转"的。

[待验证: 端侧 AI 推理在 LPS 下的具体性能退化数据，缺少实测 benchmark]

---

### 🔸 Android 14-17 演进路线

#### Android 14（API 34）

- LPS 继续主要面向 TV/STB 设备
- 内部实现优化：`PowerManagerService` 中 LPS 状态检查的性能开销降低
- NetworkPolicyManagerService 中增加了 LPS 专用的网络限制策略代码路径

#### Android 15（API 35）

- `PowerManager.isLowPowerStandbyEnabled()` 公共 API 正式稳定
- 开始有框架级别的支持将 LPS 扩展到非 TV 设备（但默认仍不启用）
- Battery Usage Stats 中新增 LPS 相关的功耗统计维度

#### Android 16-17（API 36-37）

- [待验证] 可能有针对 foldable 设备的 LPS 扩展（折叠屏合盖后进入深度省电）
- [待验证] 可能有光照传感器辅助判定——在暗光环境下提前进入 LPS
- Android 17 的 `PowerManagerService` 中 LPS 相关代码路径保持向后兼容，`config_lowPowerStandbySupported` 仍然是总开关

> 注意：Android 16/17 对 LPS 的具体变更因无法直接验证 `android-17.0.0_r1` 全部 diff，标注为待验证。核心行为（wakelock 禁用、网络阻断、维护窗口放开）在 Android 13-17 保持一致。

---

## 与其他章节的交叉引用

| 关联章节 | 关系 | 参考要点 |
|---------|------|---------|
| **5.6 Android 功耗管理** | 父章节 | Doze 模式、App Standby Bucket、WakeLock 机制的完整原理 |
| **5.8 后台执行限制** | 横向对比 | Doze 对后台任务的限制清单，与 LPS 限制对比 |
| **5.17 FGS 类型声明** | 交互关系 | 前台服务在 LPS 下的行为——FGS 不被杀死但网络受限 |
| **5.21 Adaptive Battery 与 App Standby** | 协同机制 | App Standby Bucket 在 LPS 激活时的配额调整 |
| **5.23 JobScheduler 系统级节流** | 叠加约束 | JobScheduler 五维节流在 LPS 下的额外限制 |
| **5.24 App Hibernation** | 层级关系 | App Hibernation（App 级休眠）与 LPS（设备级待机）的层级区别 |
| **11.3 SensorService** | 性能影响 | 传感器批处理在 LPS 下的间隔退化 |

---

> 📝 **置信度说明**：本章核心机制（LPS 的触发条件、限制行为、与 Doze 的关系）基于 Android 13 引入时的公开资料和 AOSP 源码验证，置信度高。Android 14-17 的演进路线因无法完整 diff AOSP 源码，部分标注为 [待验证]，置信度中等。OEM 定制差异为行业通用认知，需要参考各厂商文档确认。
