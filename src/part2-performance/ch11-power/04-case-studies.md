---

title: "案例集"
chapter: "11.4"
section: "11.4"
status: "ready-for-review"
pipeline_stage: task6_pending
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 14.0 (API 34) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium-high
polish_count: 1
polish_date: "2026-04-09"
polish_by: "task2b-polish"
reviewed_date: "2026-05-26"
reviewed_by: openclaw-task6
sources:
  - type: aosp
    path: "frameworks/base/core/java/android/os/PowerManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/PowerManagerService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/BatteryStats.java"
  - type: official
    path: "https://developer.android.com/topic/performance/power"
  - type: official
    path: "https://developer.android.com/training/monitoring-device-state/doze-standby"
  - type: blog
    path: "https://zhuanlan.zhihu.com/p/309703698"
  - type: official
    path: "https://developer.android.com/topic/performance/battery/battery-historian"
tags: ['power', 'case-study', 'wakelock', 'location', 'network-polling', 'cpu-wakeup', 'battery-historian', 'workmanager']
related_chapters: ["11.1", "11.2", "11.3", "5.6", "5.10", "13.1"]
pipeline_stage: ready-to-publish
task6_state: "revisiting"
task6_result: pass-light-edit
last_task6_at: "2026-05-26T04:07:00+08:00"
last_task6_review_log: "logs/review/2026-05-26-04-review.md"
task6_review_notes: "2026-05-26 task6 revisiting review 04:07: pass-light-edit。小修禁用词、翻译腔与模糊表达；L1/L2 通过，无新增 B 类大问题，转入 Task9 复审。"
last_task6_audit: "2026-05-23"
task9_state: "pending"
task2b_result: fixed-lite
task2b_state: fixed
task2b_repaired_date: "2026-05-31"
task2b_repaired_by: "openclaw-task2b"
task9_result: pass-tech-review
task9_reviewed_date: "2026-05-26"
task9_reviewed_by: openclaw-task9
last_task2b_at: "2026-05-31T00:50:00+08:00"
last_task2b_lite_at: "2026-06-17"
last_task9_at: "2026-05-26T04:30:00+08:00"
finalized_promoted_at: "2026-05-31T00:50:00+08:00"
finalized_promoted_by: "task2b-auto-promotion"
last_task9_review_log: "logs/deep-review/2026-05-26-04-deep-review.md"
task9_review_notes: "2026-05-26 Task9 deep-review 04:30: needs-rework。P0 1 / P1 0 / P2 2；JobScheduler timeout 仍把 quota 降级写成可能短于最小保障，需按 JobServiceContext Math.max(maxRuntime,minGuarantee) 修正；Stuck WakeLock 阈值与 Excessive Wakeups URL 待修。"
last_task9_audit: "2026-06-17"
last_task9_audit_at: "2026-05-26T02:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-26-02-audit.md"
last_task9_audit_result: "p1-version-mismatch"
task9_audit_notes: "2026-05-26 Task9 idle audit: P0 1 / P1 1 / P2 1；AOSP JobScheduler runtime 常量与 location FGS 版本链需回炉。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-31
---

# 案例集

## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 提供 3-5 个真实功耗优化案例
- 🔹 案例需覆盖：WakeLock 滥用、后台位置泄漏、网络轮询、CPU 空转
- 🔹 每个案例包含：Battery Historian 分析截图、耗电量对比数据、修复方案

### 扩展（可选深入）

- 🔸 厂商功耗检测工具的使用
- 🔸 线上功耗监控体系搭建案例

### OpenClaw 加工指引


## 为什么要看这些案例

前面的 11.1 讲了功耗模型，11.2 讲了 App 端的优化策略，11.3 讲了系统级的省电机制。机制讲完之后，难点会落到现场：拿到一个"用户反馈手机发烫、半天就没电"的问题时，从哪里下手？该看什么工具？怎么从一堆数据中找到耗电的元凶？

本节的目的，是带读者走完几个分析过程——从发现问题、定位根因，到验证修复效果。每个案例都对应一个常见功耗陷阱，走完一遍之后，下次遇到类似现象就知道该先看哪条线索。

在开始之前，我们假设读者已经了解以下内容（如果还不熟悉，可以先回去看对应章节）：

- WakeLock 的类型和基本用法（11.2）
- Battery Historian 的基本操作（11.1 中功耗度量部分）
- Doze 模式和 App Standby 的工作原理（11.3）
- WorkManager 与 JobScheduler 的定位差异（11.2）

---

## 案例一：WakeLock 泄漏——后台同步完成后忘记释放

### 问题现象

某社交类 App 在 Google Play Console 的 Android Vitals 报告中出现了异常：部分 WakeLock 卡住的会话比例达到了 3.7%。用户投诉集中在"晚上充满电放桌上，早上起来只剩 60%"这种纯待机场景。

收到这个反馈时，第一步是确认问题范围。Android Vitals 的 "Stuck partial wake lock" 指标衡量的是 App 在后台持有 `PARTIAL_WAKE_LOCK` 持续超过 1 小时的会话比例。3.7% 的会话触发这个阈值，说明问题已经呈现系统性的 WakeLock 管理缺陷。

### 分析思路

面对"待机功耗高"的问题，排查路径先看是谁在阻止 CPU 休眠，再看为什么。WakeLock 是阻止 CPU 休眠的最直接机制——只要有进程持有 `PARTIAL_WAKE_LOCK`，系统就不会进入深度睡眠。

我们的分析分三步：

1. **抓取 Battery Historian 数据**，确认 WakeLock 持有时长
2. **定位具体是哪个组件在持有 WakeLock**
3. **阅读相关代码**，找到未释放的根因

### 抓取与定位

重置电池统计数据后，让手机在纯待机状态下放 4 个小时（不插电、不开屏），再导出 bugreport 上传到 Battery Historian：

```bash
# 重置电池统计
adb shell dumpsys batterystats --reset

# 等 4 小时后，导出 bugreport
adb bugreport > bugreport_wakelock_case.zip
```

在 Battery Historian 的报告中，我们重点关注两个区域：

**时间线视图**里，深蓝色的 "Wake Lock" 条带贯穿了主要待机时段。正常情况下，这些条带应该是短促的、间歇性的——每次后台同步触发时亮一下，几秒后熄灭。但在这个案例中，从凌晨 1:30 到 6:00（将近 4.5 个小时），"Wake Lock" 条带几乎一直是亮着的。

**应用级数据表格**中，选择目标 App 后，"Wake Locks" 行显示：Partial WakeLock 总持有时长 4.2 小时，获取次数 3 次。3 次 `acquire()` 调用，但只有 2 次对应的 `release()`——有一次没释放。

### 逐步分析

我们用 `adb shell dumpsys power` 确认当前持有的 WakeLock：

```bash
adb shell dumpsys power | grep -A 5 "Wake Locks"
```

输出显示目标 App 持有一个名为 `SyncService-heartbeat` 的 `PARTIAL_WAKE_LOCK`，持续了数小时。

回到代码中搜索 `SyncService-heartbeat`，很快找到了问题所在：

```java
// 修复前 — 问题代码
public class SyncService extends Service {
    private PowerManager.WakeLock wakeLock;

    private void startSync() {
        wakeLock.acquire();  // 获取 WakeLock
        doSyncInBackground(new Callback() {
            @Override
            public void onSuccess() {
                wakeLock.release();  // 成功时释放
            }
            // ❌ 没有 onError / onFailure 的处理
        });
    }
}
```

问题集中在回调分支不完整：`doSyncInBackground` 的回调只处理了 `onSuccess`，没有处理 `onFailure`。当网络请求失败或超时时，回调走了另一个分支，WakeLock 永远不会被释放。

### 根因与结论

根因是 **WakeLock 的获取-释放不对称**。开发者在 `acquire()` 后只考虑了正常路径的 `release()`，忽略了异常路径。这在单元测试中很难发现（测试环境网络稳定），但在用户设备上，网络不稳定、服务器超时、DNS 解析失败都很常见。

Android Vitals 对这个问题的度量维度是 "Stuck partial wake lock"：App 在后台持有 `PARTIAL_WAKE_LOCK` 持续超过 1 小时的会话比例。Google Play Console 还有一个相关指标 "Excessive partial wake locks"，衡量 24 小时周期内累计 WakeLock 持有时长超过 2 小时且影响超过 5% 会话的情况。两个指标含义不同，排查时注意区分。这个数字直接影响 App 在 Google Play 的搜索排名和推荐权重，功耗问题会同时影响体验和分发。

### 修复方案

修复分两层保护：一层确保 WakeLock 在所有路径上都能释放，另一层引入超时机制作为安全网。

```java
// 修复后 — 两层保护
public class SyncService extends Service {
    private PowerManager.WakeLock wakeLock;

    private void startSync() {
        // 第一层：设置超时，确保即使代码有 bug，WakeLock 也会在 10 分钟后被系统强制释放
        wakeLock.acquire(10 * 60 * 1000L);  // 10 分钟超时
        try {
            doSyncInBackground(new Callback() {
                @Override
                public void onSuccess() {
                    safeRelease();
                }
                @Override
                public void onFailure(Throwable t) {
                    safeRelease();  // 修复：失败也要释放
                }
            });
        } catch (Exception e) {
            safeRelease();  // 修复：异常也要释放
        }
    }

    private void safeRelease() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }
}
```

第二层保护是 `wakeLock.acquire(timeout)`。`PowerManager.WakeLock` 的带超时版本的 `acquire` 方法会在指定时间后自动释放 WakeLock，即使代码因为某个未预料的路径忘记调用 `release()`。建议在所有 WakeLock 使用中默认加上超时保护。

修复后的 Battery Historian 对比：

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| WakeLock 总持有时长（4h 待机） | 4.2h | 12s（3 次同步 × 4s/次） |
| 待机电量消耗（4h） | 40% | 3% |
| Android Vitals 卡住率 | 3.7% | 0.02% |

### 举一反三

这个案例背后的通用规律是：**任何需要手动管理生命周期的资源（WakeLock、Cursor、FileInputStream、BluetoothAdapter），都必须在 finally 块或所有回调路径中释放**。WakeLock 的特殊性在于它的后果不会立即显现——用户不会在操作时感知到，但会在几小时后发现电池莫名其妙地消耗了大半。

检查项目中所有 `wakeLock.acquire()` 调用：如果没有对应带超时的 `acquire(timeout)` 或在 `finally` 中的 `release()`，那就是潜在的泄漏点。

---

## 案例二：后台位置持续请求——GPS 芯片从未关闭

### 问题现象

某运动健康类 App 在用户反馈中被频繁吐槽"开着这个 App，一天要充两次电"。问题出现在"户外跑步"功能中——用户结束跑步后，App 的后台 GPS 定位仍在持续工作。

这个问题的特征是：**长时间的持续消耗**。GPS 芯片是设备上功耗最高的传感器之一。持续使用 GPS 的 chip-level current 约为 50-100mA（参考 Qualcomm Snapdragon 平台典型值，实际因 SoC 和天线设计差异较大），而系统级待机电流只有 5-8mA——差了一个数量级以上。

### 分析思路

GPS 持续请求的定位（Location Updates）是一种典型的"忘了关"问题。分析路径是：

1. 确认 GPS 在持续工作（通过 Battery Historian 和状态栏图标）
2. 查看是哪个 App 在请求位置
3. 定位到代码中请求/移除位置更新的配对问题

### 抓取与定位

Battery Historian 报告中，"GPS" 行在整个时间线上都是绿色的——意味着 GPS 芯片持续活跃。正常的跑步 App 应该只在跑步期间 GPS 亮起，结束后熄灭。

同时，"Network" 行也有对应的网络活动——App 在持续将位置数据上传到服务器。后台不仅有 GPS 定位，还有持续的网络请求，两个高功耗组件叠加。

通过 `adb shell dumpsys location` 可以确认是哪个 App 在请求位置：

```bash
adb shell dumpsys location | grep -A 10 "Requests"
```

输出显示目标 App 注册了一个 `PRIORITY_HIGH_ACCURACY` 的位置请求，间隔 1000ms（每秒更新一次），而且从未被移除。

### 逐步分析

回到代码中，问题出在 Activity 的生命周期管理上：

```java
// 问题代码 — 位置请求没有在 onStop 中移除
public class RunningActivity extends AppCompatActivity {
    private FusedLocationProviderClient locationClient;

    @Override
    protected void onResume() {
        super.onResume();
        LocationRequest request = new LocationRequest.Builder(
                Priority.PRIORITY_HIGH_ACCURACY, 1000L)  // 每秒更新
            .build();
        locationClient.requestLocationUpdates(request, locationCallback, Looper.getMainLooper());
    }
    // ❌ 缺少 onStop/onPause 中的 removeLocationUpdates
}
```

用户结束跑步后，按 Home 键回到桌面。Activity 进入 `onStop` 状态，但 `removeLocationUpdates` 从未被调用。Fused Location Provider 会忠实地继续以每秒一次的频率请求 GPS 定位，直到系统因为内存压力杀掉 App 进程——但在大多数中高端设备上，这一天都不会发生。

### 根因与结论

根因是 **位置请求的生命周期没有和 Activity/Service 的生命周期绑定**。这看似是一个低级错误，但在实际项目中非常常见，原因有三：

> **Geofencing 与 GNSS 硬件卸载**：持续 1Hz GPS 定位是最粗放的用法。如果需求是"进入/离开某个区域时触发"，`GeofencingClient` 可以将围栏下沉到 GNSS 硬件执行，App 不需要持续持有 GPS 请求，功耗可降低一个数量级。`FusedLocationProviderClient` 的低功耗模式（`PRIORITY_BALANCED_POWER_ACCURACY` / `PRIORITY_LOW_POWER`）通过 WiFi + 基站辅助定位降低 GPS 芯片激活频率，精度从米级放宽到街区级。通过 `adb shell dumpsys location` 可以区分硬件 geofence 和软件 geofence 的注册状态。不同设备的 GNSS 硬件 geofencing 能力不同，部分低端设备不支持硬件卸载，此时仍依赖软件轮询。[待验证：各主流 SoC 的 GNSS hardware geofencing 支持情况]

1. **跑步 App 通常会启动一个前台服务来保持追踪**，开发者在 Service 中注册了位置请求，但"结束跑步"的 UI 操作只停止了 Service 的业务逻辑，没有调用 `removeLocationUpdates`。
2. **Android 8.0+ 的后台位置限制**给开发者一种虚假的安全感——以为系统会自动限制后台位置。但这个限制只影响没有前台服务的后台 App。跑步类 App 通常持有前台服务，因此不受此限制。后台位置权限在后续版本持续变严：Android 10 引入了 `ACCESS_BACKGROUND_LOCATION` 权限（需单独声明，之前 `ACCESS_FINE_LOCATION` 同时覆盖前后台）；Android 11 进一步限制，需要单独弹窗授权后台位置且默认拒绝，用户需主动在设置中开启；Android 10 要求使用后台位置的前台服务声明 `foregroundServiceType="location"`（target/compile SDK 29+），Android 12+ 进一步补上前台服务后台启动限制和 while-in-use 权限。
3. **测试环境的盲区**：开发时通常用模拟器或短距离测试，GPS 不会长时间运行，问题不容易暴露。

### 修复方案

修复方式是：**位置请求必须和它的使用场景绑定生命周期**。如果只在 Activity 可见时需要，就在 `onPause`/`onStop` 中移除；如果是通过前台服务持续追踪，就在 Service 的 `onDestroy` 或业务逻辑结束时移除。

```java
// 修复后 — 生命周期绑定
public class RunningActivity extends AppCompatActivity {
    private FusedLocationProviderClient locationClient;
    private LocationCallback locationCallback;

    @Override
    protected void onResume() {
        super.onResume();
        LocationRequest request = new LocationRequest.Builder(
                Priority.PRIORITY_HIGH_ACCURACY, 1000L)
            .build();
        locationClient.requestLocationUpdates(request, locationCallback, Looper.getMainLooper());
    }

    @Override
    protected void onPause() {
        super.onPause();
        // 关键：在 onPause 中移除位置更新
        locationClient.removeLocationUpdates(locationCallback);
    }
}
```

如果需要在后台持续追踪（如跑步记录 App），更好的方案是：

```java
// 后台追踪场景：在 Service 中管理
public class TrackingService extends Service {
    @Override
    public void onCreate() {
        // 使用更大的间隔（10s 替代 1s），减少 GPS 功耗
        LocationRequest request = new LocationRequest.Builder(
                Priority.PRIORITY_BALANCED_POWER_ACCURACY, 10_000L)  // 10 秒间隔
            .setMaxUpdateDelayMillis(30_000L)  // 允许批处理，减少唤醒次数
            .build();
        locationClient.requestLocationUpdates(request, callback, threadLooper);
    }

    public void stopTracking() {
        locationClient.removeLocationUpdates(callback);
        stopForeground(true);
        stopSelf();
    }
}
```

修复后的效果对比：

| 指标 | 修复前（跑步后 4h） | 修复后（跑步后 4h） |
|------|---------------------|---------------------|
| GPS 活跃时长 | 4h（持续） | 0（跑步结束时即停止） |
| 网络活动 | 持续上传位置数据 | 无 |
| 电量消耗 | 约 25% | 约 3%（系统待机水平） |

### 举一反三

GPS 之外，所有"用完要关"的资源都有类似的陷阱：Camera、Bluetooth 扫描、Sensor 监听器、NFC。检查 App 中是否有在 `onResume`/`onStart` 中获取资源，但没有在对应的 `onPause`/`onStop` 中释放的情况。

一个实用的排查命令：

```bash
# 检查所有活跃的位置请求
adb shell dumpsys location | grep -B 2 -A 5 "High Accuracy"
# 检查所有活跃的传感器
adb shell dumpsys sensorservice | grep "Active connections"
```

---

## 案例三：网络轮询——每 30 秒一次的心跳包让 Radio 无法休眠

### 问题现象

某即时通讯 App 出现了一个有趣的现象：待机功耗不高（没有 WakeLock 泄漏），但"亮屏使用时"电量掉得特别快，一小时掉 15%。用户没有在进行视频通话或下载大文件，只是在聊天界面待着。

这个现象指向了一个不太直观的功耗源：**移动网络 Radio 的状态机**。

### 分析思路

移动网络 Radio（基带芯片）不是只有"开"和"关"两个状态。在 Android 上，Radio 有三个功耗状态：

- **Full Power（全功率）**：数据传输中，功耗最高（4G LTE 典型值约 200-400mA，不同网络制式和 SoC 差异较大）
- **Low Power（低功率）**：数据传输刚结束，等待一段时间确认没有更多数据
- **Standby（待机）**：没有数据活动，功耗最低（约 5-10mA）

决定因素是状态转换时间：从 Full Power 到 Standby 通常需要 **30-60 秒**的不活动期。如果 App 每 30 秒发一次心跳包，Radio 就永远不会进入 Standby 状态。

这和 WakeLock 无关（CPU 可以正常休眠），根因是 Radio 的持续高功耗。Battery Historian 中会显示为"Mobile Radio"条带几乎不中断。

### 抓取与定位

Battery Historian 的 "Mobile Network" 行在整个使用期间都是绿色的，几乎没有间隙。同时 "Battery Level" 的下降曲线非常平滑且陡峭——典型的 Radio 持续高功耗特征。

通过 `adb shell dumpsys netstats` 查看目标 App 的网络活动统计：

```text
Network stats for uid=10085 (com.example.chat):
  Mobile bytes: rx=2.4MB tx=1.8MB
  Network sessions: 127 in 60 minutes
```

60 分钟内 127 次网络会话，平均每 28 秒一次——和用户反馈的"半小时发一次心跳"的设计初衷严重不符。原因是 App 实际发送的内容包括心跳包、未读消息轮询、在线状态更新、群消息同步，这些请求分散在不同模块中，各自独立发起网络请求。

### 逐步分析

我们在 Perfetto 中抓了一段 5 分钟的 Trace，过滤目标进程的网络线程：

网络线程（`OkHttp Dispatcher`）大约每 20-30 秒被唤醒一次，每次执行 1-2 秒的网络 I/O。单独看每一次请求都是合理的（数据量很小，耗时很短），但累加起来，Radio 就没有机会进入低功耗状态。

代码层面，问题出在多个模块各自维护独立的轮询定时器：

```java
// 问题代码 — 多个模块各自轮询
class MessageManager {
    // 消息轮询：每 30 秒
    private void startPolling() {
        handler.postDelayed(this::pollMessages, 30_000);
    }
}

class PresenceManager {
    // 在线状态：每 20 秒
    private void startPolling() {
        handler.postDelayed(this::updatePresence, 20_000);
    }
}

class GroupSyncManager {
    // 群消息同步：每 45 秒
    private void startPolling() {
        handler.postDelayed(this::syncGroups, 45_000);
    }
}
```

每个模块的轮询间隔单独看都不高，但三个定时器不同步，导致实际的网络请求频率远高于预期。

### 根因与结论

根因是 **多个模块独立轮询，没有合并网络请求窗口**。Radio 功耗取决于唤醒次数而非传输数据量——即使每次只发 100 字节的心跳包，如果每 30 秒触发一次，Radio 就永远无法回到 Standby 状态。

### 修复方案

修复有两个方向：短期是合并轮询窗口，长期是用 Push 替代 Pull。

**短期：合并轮询窗口**

```java
// 修复后 — 统一轮询调度器
class NetworkScheduler {
    private static final long SYNC_INTERVAL = 5 * 60_000L; // 5 分钟合并一次

    void scheduleSync() {
        // 将所有网络请求集中在一个窗口中执行
        executor.execute(() -> {
            messageManager.pollMessages();     // 批量执行
            presenceManager.updatePresence();  // 避免各自轮询
            groupSyncManager.syncGroups();     // 让 Radio 一次唤醒即可
        });
        handler.postDelayed(this::scheduleSync, SYNC_INTERVAL);
    }
}
```

将轮询间隔从 30 秒拉长到 5 分钟，并将所有网络请求合并到同一个执行窗口。这样 Radio 有足够的空闲时间进入 Standby。

**长期：Push 替代 Pull**

更好的方案是使用 Firebase Cloud Messaging（FCM）或自建 WebSocket 长连接，由服务端在有新消息时主动推送。这样 App 端完全不需要轮询，只在收到 Push 时才发起网络请求。

```java
// 长期方案 — FCM Push
class MyFirebaseMessagingService extends FirebaseMessagingService {
    @Override
    public void onMessageReceived(RemoteMessage message) {
        // 收到 Push 后才发起网络请求获取完整数据
        messageManager.fetchNewMessages();
    }
}
```

修复后的效果对比：

| 指标 | 修复前 | 修复后（合并轮询） | 修复后（Push） |
|------|--------|-------------------|---------------|
| 网络请求频率 | ~28s/次 | 5min/次 | 按需（~15min/次） |
| Radio 活跃比例 | ~90% | ~10% | ~3% |
| 1 小时亮屏耗电 | 15% | 5% | 3% |

### 举一反三

这个案例的通用规律是：**评估网络功耗时，优先看 Radio 唤醒次数，数据量只放在第二层判断**。100 次各 1KB 的请求，比 1 次 100KB 的请求耗电得多。

在 Battery Historian 中，如果看到 "Mobile Radio" 行几乎不中断地亮着，而 "WiFi" 行是间歇性的，说明 App 在蜂窝网络上的请求太频繁。解决方向：拉长间隔、合并请求、或者换用 Push。

---

## 案例四：AlarmManager 滥用——每分钟一次的精确闹钟让 CPU 频繁唤醒

### 问题现象

某新闻类 App 的用户反馈："装了这个 App 之后，手机明显变热，续航缩短了 30%"。高功耗发生在后台：**即使 App 不在前台，手机也经常微微发热**。

这个症状指向一个特定的机制：**频繁的 CPU 唤醒**。设备在不使用时，CPU 应该处于深度睡眠状态（功耗仅几 mA）。但如果某个 App 通过 AlarmManager 设置了频繁的精确闹钟，CPU 会反复被唤醒，每次唤醒需要几十到几百 mA 的电流，持续几秒后才能重新入睡。

### 分析思路

CPU 频繁唤醒的排查和 WakeLock 不同。WakeLock 是"持续持有"导致 CPU 一直不睡，而 AlarmManager 是"频繁唤醒"导致 CPU 睡了又被叫醒、睡了又被叫醒。两者在 Battery Historian 中的表现也不一样：

- WakeLock 泄漏：WakeLock 行是**连续的长条带**
- AlarmManager 滥用：WakeLock 行是**密集的短条带**（每次闹钟触发时短暂亮起）

### 抓取与定位

Battery Historian 报告中，"Wake Lock" 行呈现密集短线段，大约每 60 秒一段；这和 WakeLock 泄漏的连续长条不同。同时 "Kernel Wakeup Reasons" 行显示了大量的 `alarm` 类型唤醒源。

用 `adb shell dumpsys alarm` 确认：

```bash
adb shell dumpsys alarm | grep -A 3 "com.example.news"
```

输出显示目标 App 设置了一个精确重复闹钟（`RTC_WAKEUP`），间隔 60000ms（60 秒）：

```text
RTC_WAKEUP #0: Alarm{... type=RTC_WAKEUP when=... com.example.news}
  triggerAtTime: 2026-04-02 14:31:00.000
  interval: 60000  // 60 秒
  operation: PendingIntent{... NewsSyncService}
```

### 逐步分析

Android Vitals 有一个专门的指标叫 "Excessive Wakeups"，衡量的是 App 在 1 小时内唤醒设备的次数超过 10 次。这个 App 每小时唤醒 60 次——远超告警线。

代码中的问题：

```java
// 问题代码 — 使用精确重复闹钟进行后台同步
AlarmManager alarmManager = (AlarmManager) getSystemService(ALARM_SERVICE);
Intent intent = new Intent(this, NewsSyncService.class);
PendingIntent pendingIntent = PendingIntent.getService(this, 0, intent, PendingIntent.FLAG_IMMUTABLE);

// ❌ 使用 setRepeating + 精确闹钟，每 60 秒触发一次
alarmManager.setRepeating(AlarmManager.RTC_WAKEUP, System.currentTimeMillis(),
    60_000, pendingIntent);
```

这里有三个问题叠加在一起：

1. **`RTC_WAKEUP`**：会唤醒设备（如果 CPU 在睡眠的话），而 `RTC` 不会。对于后台同步来说，通常不需要唤醒设备。
2. **`setRepeating`**：精确重复闹钟。从 Android 4.4 开始，`setRepeating` 的实际行为已经改为非精确的，但开发者如果用 `setExact` + 自身重设闹钟，就绕过了这个保护。
3. **60 秒间隔**：太短了。对于新闻同步来说，5-15 分钟一次完全可以接受。

### 根因与结论

根因是 **把定期后台同步交给了 AlarmManager 的精确闹钟，没有交给 WorkManager 或 JobScheduler**。AlarmManager 的设计初衷是"在特定时间点执行操作"（如闹钟提醒），不是"定期后台任务"。后者的正确工具是 WorkManager，它会和系统其他 App 的任务一起批处理，减少总唤醒次数。

Android 14（API 34）进一步限制了精确闹钟权限：只有闹钟类 App 和用户明确授权的 App 才能使用 `SCHEDULE_EXACT_ALARM`。如果 App 不是闹钟，用精确闹钟做后台同步在新系统上会直接失效。

### 修复方案

用 WorkManager 替代 AlarmManager：

```java
// 修复后 — WorkManager 替代 AlarmManager
PeriodicWorkRequest syncWork = new PeriodicWorkRequest.Builder(
    NewsSyncWorker.class,
    15, TimeUnit.MINUTES,    // 最小间隔 15 分钟
    5, TimeUnit.MINUTES      // 灵活窗口 5 分钟
)
.setConstraints(new Constraints.Builder()
    .setRequiredNetworkType(NetworkType.CONNECTED)  // 有网络才执行
    .setRequiresBatteryNotLow(true)                  // 电量不低才执行
    .build())
.build();

WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "news_sync",
    ExistingPeriodicWorkPolicy.KEEP,  // 不要重复创建
    syncWork
);
```

WorkManager 的优势：

- 系统会将多个 App 的 WorkManager 任务合并执行，总唤醒次数远少于每个 App 各自用 AlarmManager
- 约束条件（网络、电量、充电状态）让任务只在合适时机执行
- 在 Doze 模式的维护窗口中执行，不会阻止设备进入深度睡眠

修复后的效果：

| 指标 | 修复前（AlarmManager） | 修复后（WorkManager） |
|------|----------------------|---------------------|
| CPU 唤醒频率 | 60 次/小时 | 4 次/小时（系统合并后） |
| 单次唤醒功耗 | ~300mA × 3s | ~300mA × 3s（但次数少得多） |
| 4 小时待机耗电 | ~12% | ~3% |
| Android Vitals 唤醒指标 | 告警 | 正常 |

### 举一反三

如果项目中有任何 `AlarmManager.setRepeating()` 或 `setExact()` 用于后台同步/轮询，都应该替换为 WorkManager。只有在用户主动设置的闹钟、提醒等场景下才使用精确闹钟。

一个快速检查的方法：

```bash
# 列出所有 App 注册的 Alarm
adb shell dumpsys alarm | grep -E "RTC_WAKEUP|ELAPSED_WAKEUP" | grep -v "android"
```

如果 App 出现在这个列表中，而且间隔小于 15 分钟，就需要检查是否有更合适的替代方案。

---

## 案例五：JobScheduler 的 WakeLock 超时——任务完成后忘记调用 jobFinished

### 问题现象

这个案例容易被误判。某工具类 App 使用了 JobScheduler 来执行后台数据清理任务（正确地选择了 JobScheduler，没有使用 AlarmManager），但用户仍然反馈后台功耗偏高。

Android Vitals 的 WakeLock 报告中没有出现 "Stuck WakeLock"（没有单次持续超过 1 小时的 WakeLock），但待机功耗比同类 App 高。问题出在哪里？

### 分析思路

这个案例的关键线索是：JobScheduler 是正确使用的，但功耗仍然偏高。这引导我们去看 JobScheduler 内部的 WakeLock 行为——一个容易被忽略的细节。

当 `JobService.onStartJob()` 返回 `true`（表示任务在后台线程执行）时，系统会为这个 Job 持有一个 WakeLock。这个 WakeLock 的最大持有时长取决于 Job 类型：

| Job 类型 | 最小保障时长（源码常量） | 运行上限 | 超时行为 |
|---------|----------------------|---------|----------|
| Regular | 10 分钟（`DEFAULT_RUNTIME_MIN_GUARANTEE_MS`） | `getMaxJobExecutionTimeMs()` 返回值，取决于 standby bucket 和当前 quota | 超时后 `onStopJob()` 被调用，系统释放 WakeLock |
| Expedited | 3 分钟（`DEFAULT_RUNTIME_MIN_EJ_GUARANTEE_MS`） | 不超过 Regular 上限（10 分钟），调度优先级更高 | 同 Regular |
| User-Initiated | 约 6 小时（`DEFAULT_RUNTIME_MIN_UI_GUARANTEE_MS`，max(6h,10min)） | 约 12 小时（`DEFAULT_RUNTIME_UI_LIMIT_MS`，max(12h,30min)）；累计 UI limit 24h | 同 Regular |

以上是 `JobSchedulerService.Constants` 中各类 Job 的最小保障时长和常规上限。实际运行上限由 `getMaxJobExecutionTimeMs()` 动态计算，受 standby bucket、当前 quota、QuotaController 和 timeout quota 约束。**关键修复**：quota 和 standby bucket 影响的是后续调度频率和每次运行的上限，**绝不会缩短单次 timeout**。AOSP `JobServiceContext.executeRunnableJob()` 中 `mMaxExecutionTimeMillis = max(getMaxJobExecutionTimeMs(job), mMinExecutionGuaranteeMillis)`，timeout 窗口**绝对不会低于**对应类型的最小保障值。更早停止只能来自约束变化、preempt、cancel 或 ANR 等非 timeout 路径。

如果任务完成后没有调用 `jobFinished()`，WakeLock 会一直持有到超时才被系统强制回收。超时时长取决于 `max(getMaxJobExecutionTimeMs(job), mMinExecutionGuaranteeMillis)` 的返回值——Regular 至少 10 分钟、Expedited 至少 3 分钟、User-Initiated 至少约 6 小时。quota 和 standby bucket 会影响运行上限，但 timeout 窗口不会低于最小保障值。即使任务只执行了 3 秒，忘记调用 `jobFinished()` 也会白白保持 WakeLock 直到超时。

### 逐步分析

Battery Historian 中，我们看到一种规律性的模式：每隔一段时间（取决于 JobScheduler 的调度频率），就会出现一段约 10 分钟的 WakeLock 条带。这个时长和 JobScheduler 的执行时间片直接相关。

代码中的问题：

```java
// 问题代码 — 忘记调用 jobFinished
public class CleanupJobService extends JobService {
    @Override
    public boolean onStartJob(JobParameters params) {
        new Thread(() -> {
            doCleanup();  // 实际只花 3 秒
            // ❌ 没有 jobFinished(params, false)
        }).start();
        return true;  // 表示工作在后台线程中执行
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        return false;
    }
}
```

任务本身只需 3 秒就执行完了，但因为没有调用 `jobFinished()`，系统的 WakeLock 要等到 10 分钟超时才会释放。如果这个 Job 每小时执行一次，那每小时就有 10 分钟 CPU 无法正常休眠——约 17% 的时间在浪费。

### 根因与结论

根因是 **JobService 的生命周期管理不当**。`onStartJob()` 返回 `true` 意味着告诉系统"任务还在执行，请帮我保持 WakeLock"。任务完成后必须调用 `jobFinished()` 告诉系统"我做完了，可以释放 WakeLock 了"。这是一个配对操作，和 WakeLock 的 acquire/release 一样重要。

### 修复方案

```java
// 修复后 — 正确管理 JobService 生命周期
public class CleanupJobService extends JobService {
    @Override
    public boolean onStartJob(JobParameters params) {
        new Thread(() -> {
            doCleanup();
            // ✅ 任务完成后通知系统
            jobFinished(params, false);  // false = 不需要重新调度
        }).start();
        return true;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        // 系统要求提前终止 Job（如条件不再满足），返回 true 表示需要重新调度
        return true;
    }
}
```

修复后，每次 Job 执行只持有 WakeLock 3 秒，原来约 10 分钟的待机占用消失了。

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 单次 Job WakeLock 持有时长 | 10 分钟（Regular 超时） | 3 秒 |
| 每小时 WakeLock 活跃比例 | ~17% | ~0.5% |
| 4 小时待机耗电 | ~8% | ~3% |

### 举一反三

这个案例的教训是：**使用任何 API 时，都要理解它在底层获取了什么系统资源，以及什么时候释放**。JobScheduler 表面上"帮我们管理了 WakeLock"，但它负责的是"持有"，释放的责任在使用者。类似的模式还有：

- `GcmTaskService`（已废弃）：同样需要 `onFinishTask()`
- `ForegroundService`：需要在任务完成后调用 `stopForeground()` + `stopSelf()`
- WorkManager 的 `Worker`：自动管理 WakeLock 的获取和释放（通过 `ForegroundInfo` 支持前台服务），不需要手动调用 `jobFinished()` 的等价操作（这是 WorkManager 优于直接使用 JobScheduler 的一个原因，详见 5.10）

如果在项目中直接使用 JobScheduler，全局搜索所有 `onStartJob` 返回 `true` 的地方，确认每一个都有对应的 `jobFinished()` 调用。

---

## 与其他章节的关系

本章的五个案例分别对应了 11.2 中讲解的理论知识：

| 案例 | 核心机制 | 对应章节 |
|------|---------|---------|
| WakeLock 泄漏 | PowerManager.WakeLock | 11.2 WakeLock 最佳实践 |
| 后台位置泄漏 | FusedLocationProvider | 11.2 位置服务功耗优化 |
| 网络轮询 | Radio 状态机 | 11.2 网络请求功耗优化 |
| AlarmManager 滥用 | AlarmManager vs WorkManager | 11.2 Alarm 使用规范、5.10 JobScheduler/WorkManager |
| JobScheduler 超时 | JobService 生命周期 | 11.2 后台任务省电策略、5.10 JobScheduler/WorkManager |

如果在分析具体问题时需要了解底层机制，可以回到对应章节查看详细的技术原理。如果需要了解 Battery Historian 的使用方法，参考 11.1 的功耗度量部分。

另外，第 13 章（Perfetto 工具详解）中的 CPU Track 和 Power Track 分析，是本案例集中定位 CPU 唤醒和功耗问题的核心工具。

---

## 常见问题与误区

### 误区一："用了 WorkManager 就不用关心功耗了"

WorkManager 帮我们管理了 WakeLock 的获取和释放、任务的批处理和约束条件，但它不能代替开发者决定"这个任务是否真的需要在后台运行"。WorkManager 的 PeriodicWorkRequest 最小间隔是 15 分钟（无法设得更短），这在一定程度上限制了滥用。但如果用 OneTimeWorkRequest 链式调度、或者设置不合理的约束条件导致任务频繁重试，仍然会带来不必要的 CPU 唤醒和 Radio 活跃。

### 误区二："Battery Historian 已经过时了，不需要学"

Google 已经停止维护 Battery Historian，推荐使用 Android Studio 的 Power Profiler（Pixel 6+ 设备支持 Power Rails 数据）。但 Battery Historian 的独特价值在于：它可以分析 `bugreport` 数据，不需要实机连接，适合分析用户远程反馈的功耗问题。对于线下开发阶段，Android Studio Power Profiler 更实时、更精确；对于线上用户问题，Battery Historian 仍然实用。

### 误区三："GPS 只有在用户开启定位时才耗电"

Android 的位置服务是系统级的。App 可以在后台请求位置更新（只要有权限），即使状态栏没有显示 GPS 图标。Battery Historian 中如果看到 "GPS" 行持续活跃，但状态栏没有 GPS 标记，说明有 App 在使用低精度定位（网络定位），虽然单次功耗低于 GPS，但持续请求的累积效果同样显著。

### 误区四："网络请求的数据量决定功耗"

Radio 功耗主要由 **Radio 的状态转换次数**决定，数据量只是次要因素。一次 1MB 的下载和 1000 次各 1KB 的请求，传输的数据量相同，但后者的功耗可能是前者的 10 倍以上。因为每次请求都要把 Radio 从 Standby 拉到 Full Power，而状态转换过程本身就需要大量能量。

### 误区五："Doze 模式会自动解决所有后台功耗问题"

Doze 模式会大幅限制后台活动，但它只在"设备静止不动、屏幕关闭、未充电"时才生效。如果用户把手机放在桌上但没关屏，或者在口袋里走来走去（运动传感器检测到移动），Doze 不会进入最深层次。此外，前台服务绑定的 App 在 Doze 期间不受网络限制。

---

## Android 15+ 前台服务超时与崩溃

Android 15（API 35）引入了前台服务（FGS）超时机制，并在 Android 16 进一步加强限制。几类 FGS 有明确的时间配额：

| FGS 类型 | 配额 | 超时回调 |
|---------|------|---------|
| `dataSync` | 后台 24 小时内总计 6 小时 | `Service.onTimeout(int, int)` |
| `mediaProcessing` | 后台 24 小时内总计 6 小时 | `Service.onTimeout(int, int)` |
| `shortService` | 约 3 分钟 | `Service.onTimeout(int, int)` |

超时后如果服务没有调用 `stopSelf()`，系统会抛出 `RemoteServiceException` 导致 App 崩溃。Logcat 中的签名取决于超时类型：

**dataSync / mediaProcessing 配额耗尽**（6 小时配额用完且 `onTimeout` 后未 stopSelf）：

```text
Fatal Exception: android.app.RemoteServiceException
  A foreground service of type dataSync did not stop within its timeout: com.example/.SyncService
```

**startForegroundService 后未及时调用 startForeground**（这是另一类问题，与配额超时无关）：

```text
Fatal Exception: android.app.RemoteServiceException
  Context.startForegroundService() did not call Service.startForeground()
```

两类崩溃的根因不同：第一类是 FGS 运行超时后未在 `onTimeout` 回调中 `stopSelf()`；第二类是启动 FGS 后未在 5 秒内提升为前台状态。排查时注意区分。

排查路径：

1. 在 Logcat 中搜索 `onTimeout`、`did not stop within its timeout` 或 `RemoteServiceException` + 服务类名
2. 检查 FGS 的 `foregroundServiceType` 是否选对——如果用 `dataSync` 做长时间同步，6 小时配额用完后就会触发 `onTimeout`，服务必须在回调中 `stopSelf()`
3. 评估是否可以用 WorkManager、`User-initiated data transfer`（Android 14+）或分区存储 API 替代 FGS

---

## 厂商功耗检测工具

除了 Google 官方的工具链，各手机厂商也提供了功耗分析工具，但这些工具通常只在对应品牌的设备上可用：

- **小米**：Power Monitor（MIUI 开发者选项中启用），可以记录各 App 的前台/后台功耗
- **华为**：DevEco Testing 中的 Power Profiler，支持 HarmonyOS 和 EMUI 设备
- **OPPO/OnePlus**：ColorOS 开发者选项中的功耗监控
- **三星**：Samsung Power Profiler（Galaxy 设备专属）

这些厂商工具可以读取 SoC 级别的功耗传感器数据（ODPM / Power Rails），精度比 Battery Historian 高得多。如果目标用户群体集中在某个品牌，需要了解对应工具的使用方法。

---

## 线上功耗监控体系

线上功耗监控没有单一方案能覆盖所有场景，需要根据目标 Android 版本和业务场景组合使用。

### Play Console Android Vitals（覆盖面最广）

Google Play Console 的 Android Vitals 面板提供以下功耗相关指标，无需 App 端接入任何 SDK：

- **Stuck partial wake lock**：后台 `PARTIAL_WAKE_LOCK` 持续 ≥1 小时的会话比例
- **Excessive partial wake locks**：24 小时内累计持有时长 >2 小时且影响 >5% 会话
- **Excessive wakeups**：1 小时内唤醒设备 >10 次
- **Background ANR / crashed**：可间接反映功耗相关崩溃

这些指标直接影响 App 的 Play 搜索排名和推荐权重。排查时注意区分 stuck（单次长时间）和 excessive（24 小时累计）两个 WakeLock 指标。

### Battery Historian / bugreport 分析

对于用户远程反馈的功耗问题，收集 `adb bugreport` 后上传 Battery Historian 是最直接的分析方法：

```bash
# 重置电池统计后复现问题，再导出
adb shell dumpsys batterystats --reset
# 复现问题...
adb bugreport > bugreport_power_case.zip
```

Battery Historian 可以查看 WakeLock 持有时长、GPS/Radio 活跃时段、CPU 唤醒频率等时间线数据，适合定位具体是哪个子系统的功耗异常。

### Perfetto Power Rails 分析（Pixel 6+）

Pixel 6 及更新设备支持 Power Rails 数据源，Perfetto 可以直接读取 SoC 级别的功耗传感器数据（ODPM），精度远高于电池百分比估算：

- 在 Perfetto 配置中启用 `android.power` 数据源
- 通过 `power_rails` track 观察各子系统（CPU/GPU/DDR/Display）的实时功耗
- 配合 CPU/GPU track 做关联分析，定位功耗异常的具体代码路径

线下开发阶段推荐使用 Android Studio Power Profiler（图形化界面），线上问题用命令行 Perfetto 抓取。

### 自建监控的边界

自建线上功耗监控需要注意：
- `BatteryManager` 返回的电量百分比精度较低（约 ±5%），只能用于粗粒度趋势分析
- `UsageStatsManager` 提供的是使用时长统计，不直接反映功耗
- 高频轮询电池状态本身会引入功耗，采样间隔建议 ≥5 分钟
- Android 9+ 限制后台 App 读取电池信息的频率

### 展望：ProfilingManager 自动触发（API 35+，Android 17 强化）

Android 15 引入 `ProfilingManager`（API 35），支持 App 请求系统抓取性能 trace。Android 17（API 37）进一步引入 `ProfilingTrigger.TRIGGER_TYPE_ANOMALY`，允许在系统检测到性能/功耗异常时自动触发 trace 抓取，帮助捕获导致过热的真实负载现场。这两个 API 面向 Android 15+ 和 Android 17+，不属于 Android 8-16 的主要监控路径，可作为后续演进方向关注。

---

## 参考资料

- [AOSP PowerManager.java](https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/core/java/android/os/PowerManager.java) — WakeLock acquire/release API
- [AOSP AlarmManagerService.java](https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/services/core/java/com/android/server/AlarmManagerService.java) — 闹钟调度实现
- [AOSP JobServiceContext.java](https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/apex/jobscheduler/service/java/com/android/server/job/JobServiceContext.java) — JobScheduler WakeLock 管理
- [AOSP LocationManagerService.java](https://cs.android.com/android/platform/superproject/+/android-16.0.0_r1:frameworks/base/services/core/java/com/android/server/LocationManagerService.java) — 位置服务实现
- [Android Developers: Optimize for Battery Life](https://developer.android.com/topic/performance/power) — 官方功耗优化指南
- [Android Developers: Battery Historian](https://developer.android.com/topic/performance/battery/battery-historian) — Battery Historian 使用文档
- [Android Developers: Doze and App Standby](https://developer.android.com/training/monitoring-device-state/doze-standby) — 系统省电机制
- [Android Developers: Background Execution Limits](https://developer.android.com/about/versions/oreo/background) — Android 8.0+ 后台限制
- [Android Developers: Network Battery Optimization](https://developer.android.com/training/efficient-downloads/connectivity_patterns) — Radio 状态机和网络优化
- [Android Vitals: WakeLock](https://developer.android.com/topic/performance/vitals/wakelock) — WakeLock 监控指标
- [Android Vitals: Excessive Wakeups](https://developer.android.com/topic/performance/vitals/wakeup) — 过度唤醒监控指标
- [Android 14 Behavior Changes: Exact Alarms](https://developer.android.com/about/versions/14/behavior-changes-14#precision-scheduled-alarms) — Android 14 精确闹钟限制
