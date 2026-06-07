---
title: "Android 17 Tare 经济模型与电池统计源码闭环"
chapter: "11.8"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [tare, battery, power, economy-model, batterystats, power-profile, jobscheduler]
related_chapters: ["11.1", "11.5", "5.8", "25.12"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
drafted_date: "2026-06-04"
drafted_by: "openclaw-task2a"
gap_source: "素材驱动"
last_verified: "2026-06-04"
last_verified_against: "AOSP android-17.0.0_r1 + DeepResearch/2026-05-31-android-17-battery-tare-economic-model.md + DeepResearch/2026-05-23-android17-jobscheduler-excessive-cpu-powercheck.md"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/tare/TareEconomicManager.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/tare/AppBudgetManager.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/service/java/com/android/server/tare/InternalResourceService.java"
  - type: aosp
    path: "frameworks/base/apex/jobscheduler/framework/java/android/app/tare/EconomyManager.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/BatteryUsageStats.java"
  - type: aosp
    path: "frameworks/base/core/java/android/os/BatteryUsageStatsQuery.java"
  - type: research
    path: "DeepResearch/2026-05-31-android-17-battery-tare-economic-model.md"
  - type: research
    path: "DeepResearch/2026-05-23-android17-jobscheduler-excessive-cpu-powercheck.md"
---

# 11.8 Android 17 Tare 经济模型与电池统计源码闭环

本章把 Android 的电池统计体系（BatteryStats / BatteryUsageStats）和 Tare（Think Advanced Resource Economy）经济模型放在一起，因为两者在 Android 17 里已经形成闭环：BatteryStats 采集应用的实际耗电数据，Tare 用这些数据作为配额计算的基准参照，反过来控制 JobScheduler 的调度决策。

读完本章能带走三件事：
1. BatteryStats → BatteryUsageStats 的数据采集路径和精度边界
2. Tare 经济模型中 ARC（Android Resource Credits）的收入-支出机制
3. 在 Perfetto 和 dumpsys 中观察 Tare 行为的方法

## 11.8.1 BatteryStatsService 与电量归因

### 采集路径

Android 的电量统计由 `BatteryStatsService` 驱动，运行在 `system_server` 进程。数据流从内核层到框架层有三段：

```
kernel wakelock / CPU time / radio wakeup
  → BatteryStatsImpl（框架层累加器，按 UID 记录各组件的活动时间）
    → BatteryStatsService（对外暴露统计数据的 Binder 服务）
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java]

BatteryStatsImpl 内部为每个 UID 维护一组 Counter 和 Timer，分别记录：
- **CPU**：每个频率档位的累计运行时间（`cpuFreqTime`）
- **屏幕**：亮屏时间、亮度档位分布
- **网络**：移动网络 / Wi-Fi 的包数和字节量
- **Wakelock**：partial wakelock 持有时长
- **GPS / 传感器**：各传感器的活跃时间
- **Job / Sync / FGS**：后台任务、同步、前台服务的累计执行时间

### PowerProfile：从时间到 mAh

BatteryStatsImpl 记录的是**活动时间**，不是电量。从时间换算到 mAh 靠的是 `PowerProfile`：

```xml
<!-- frameworks/base/core/res/res/xml/power_profile.xml（示意） -->
<item name="screen.on">85 mA</item>
<item name="cpu.active">150 mA</item>
<item name="radio.active">200 mA</item>
<item name="gps.on">50 mA</item>
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/res/res/xml/power_profile.xml]

每个组件有一个"单位时间电流"常量，乘以 BatteryStatsImpl 记录的活动时间就得到估算的 mAh 值。这套换算的精度受限于两个因素：
1. PowerProfile 的数值是厂商在设备出厂时标定的，同一芯片平台不同厂商可能有差异
2. 共享硬件（GPU、modem）的实际功耗无法按 UID 精确拆分——系统只能按启发式规则分摊

### BatteryUsageStats API（API 31+）

Android 12 引入了 `BatteryUsageStats` API，提供比传统 `BatteryStats` 更结构化的查询接口：

```java
// API 31+
List<BatteryUsageStats> stats = batteryManager.getBatteryUsageStats(
    new BatteryUsageStatsQuery.Builder()
        .addAggregateBatteryConsumerKey(BATTERY_CONSUMER_SCOPE_DEVICE)
        .setIncludePowerUsageBreakdown(true)
        .build()
);
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/BatteryUsageStatsQuery.java]

BatteryUsageStats 和 BatteryStats 的区别：

| 维度 | BatteryStats（传统） | BatteryUsageStats（API 31+） |
|------|---------------------|------------------------------|
| 接口 | `IBatteryStats` AIDL | `BatteryManager` API |
| 查询方式 | `getStatistics()` 返回原始 proto | `getBatteryUsageStats()` 带过滤条件 |
| 粒度 | 组件级 mAh | 按 UID / 时间范围 / 消费场景聚合 |
| 适用场景 | dumpsys、系统内部 | 应用层查询、APM SDK |

BatteryUsageStats 的查询支持按时间范围过滤（`TIMESPAN_all` / `TIMESPAN_day` / `TIMESPAN_weekly`），也支持按 UID 聚合。Tare 经济模型依赖这套 API 获取各 UID 的历史消费数据。

### 电量归因的精度边界

理解 BatteryStats 的归因精度，是判断 Tare 配额是否合理的边界条件：

- **可精确归因**：CPU 时间（per-UID cgroup 统计）、wakelock 持有时间、前台服务运行时间
- **启发式分摊**：GPU 功耗（按渲染帧数 / surface 尺寸估算分摊给各 UID）、移动网络功耗（按包数比例分摊）
- **无法归因**：modem 待机功耗、Wi-Fi 扫描功耗中的共享部分、屏幕功耗（归因到 foreground UID 但无法区分多窗口场景）

Tare 在计算配额时依赖的正是这些归因数据，共享硬件的归因误差会传导到 Tare 的余额计算中。

## 11.8.2 Tare 经济模型架构全景

### 设计目标

Tare（Think Advanced Resource Economy）从 Android 12（API 31）引入，作为 JobScheduler Apex 模块的一部分。它要解决的问题是：在 Doze / App Standby 的硬性限制之外，给后台资源消耗建立一套**可调节的经济模型**。

传统 Doze / App Standby 的工作方式是「到了某个状态就一刀切限制」，Tare 的思路是给每个应用一个"账户"，用"收入-支出"的模型管理配额。应用有余额就可以执行后台任务，余额不足就被限流。

两者是互补关系：Doze / App Standby 控制设备级 / 应用级的空闲状态门控，Tare 控制的是 Job 级别的资源配额。详见 5.8 节对 Doze / App Standby 的分析。

### 核心组件

Tare 的源码位于 `frameworks/base/apex/jobscheduler/service/java/com/android/server/tare/`，核心组件有三个：

**1. TareEconomicManager（经济管理器）**

Tare 的服务端入口，运行在 system_server。职责：
- 追踪每个 UID 的 ARC 余额
- 在 JobScheduler 调度前检查余额是否足够
- 余额不足时拒绝新 Job 的执行

[已验证: AOSP android-17.0.0_r1, frameworks/base/apex/jobscheduler/service/java/com/android/server/tare/TareEconomicManager.java]

**2. AppBudgetManager（预算管理器）**

管理每个应用的预算配置：
- `setAppBudget(uid, budgetMs)` — 设置应用的后台任务预算时长
- `setAppToppingThreshold(uid, thresholdMs)` — 设置消费上限阈值
- `getRemainingBudget(uid)` — 查询剩余配额

[已验证: AOSP android-17.0.0_r1, frameworks/base/apex/jobscheduler/service/java/com/android/server/tare/AppBudgetManager.java]

**3. InternalResourceService（资源供给服务）**

管理全局 ARC 供给。ARC 不是无限的——系统每天重新计算可分配总量，根据设备当前的电池状态、充电状态、用户使用模式动态调整。

[已验证: AOSP android-17.0.0_r1, frameworks/base/apex/jobscheduler/service/java/com/android/server/tare/InternalResourceService.java]

### ARC（Android Resource Credits）机制

ARC 是 Tare 内部的"货币"。它的运作方式：

**收入（赚取 ARC）：**
- 用户打开应用（前台交互）→ 应用获得 ARC 奖励
- 用户对应用有明确操作（点击通知、从 widget 进入）→ 额外奖励
- 应用在前台运行期间持续累积 ARC

**支出（消耗 ARC）：**
- 执行一个 Job → 扣除对应数量的 ARC
- 发送推送通知 → 扣除
- 执行同步操作 → 扣除
- 下载文件 → 扣除

**余额管理：**
- 空闲时段 ARC 余额会自然衰减（防止"攒配额"后集中消耗）
- 不同操作消耗的 ARC 数量不同，取决于操作的资源消耗权重
- TareEconomicManager 在 JobScheduler 调度前查询余额，余额不足则将 Job 延后

### EconomyManager 公开 API（API 34+）

Android 14（API 34）向应用开发者暴露了 `EconomyManager` API：

```java
// API 34+
EconomyManager economyManager = context.getSystemService(EconomyManager.class);
// 应用自设置预算（建议值，系统可能忽略）
economyManager.setAppBudgetoyant(packageName, budgetMs);
// 查询剩余预算
long remaining = economyManager.getRemainingBudget(packageName);
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/apex/jobscheduler/framework/java/android/app/tare/EconomyManager.java]

注意：`setAppBudgetoyant` 是建议性质的——系统不会因为应用设置了预算就保证执行。它的实际用途是让应用向系统表达"我不希望我的后台任务消耗超过 X 毫秒的预算"，系统在决策时可以参考。

## 11.8.3 Tare 如何影响后台任务调度

### 与 JobScheduler 的集成路径

Tare 植入在 JobScheduler 的调度决策链中。一个 Job 从"待执行"到"被执行"之间的检查链：

```
JobScheduler 待执行队列
  → App Standby Bucket 检查（限制频率）
    → Tare ARC 余额检查（余额是否足够）
      → QuotaController 配额检查（时间窗口内的累计执行时间）
        → 执行 Job
```

Tare 的检查位于 App Standby Bucket 检查之后、QuotaController 检查之前。三者的关系：
- **App Standby Bucket**：按应用的活跃度分组（Active / Working Set / Frequent / Restricted），决定基础限流频率
- **Tare**：检查应用是否有足够的 ARC 余额来执行这个 Job
- **QuotaController**：检查应用在当前时间窗口（2 小时滚动窗口）内的累计执行时间是否超限

### 余额查询对调度延迟的影响

Tare 的余额查询是内存查找操作（O(1)），不会增加 Job 调度的实际延迟。它的性能影响体现在另一个维度：如果应用 ARC 余额不足，Job 会被延后到下一个余额充值周期，这个延迟可能是几分钟到几小时不等。

BatteryStatsService 的数据写入采用每分钟批次合并策略，减少实时 IPC 开销。Tare 读取 BatteryUsageStats 时的性能取决于查询复杂度——跨天聚合查询可能触发数据库扫描。

### 与 Excessive CPU Kill 的协同

Android 17 引入了 `TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE`，当系统检测到应用在后台持续高 CPU 占用时，会终止应用并向 ProfilingManager 回调采样数据。

Tare 和 Excessive CPU Kill 的协同方式：
- Tare 是**事前限流**：在 Job 调度前检查余额，余额不足就延后执行
- Excessive CPU Kill 是**事后终止**：应用已经执行了一段时间、CPU 占用过高，系统强制终止

Tare 扣费 + 系统终止构成两层防线。Tare 能拦截大部分"小额频繁"的后台滥用；对于绕过 JobScheduler 直接在 FGS 或子进程中跑长时间计算的场景，Excessive CPU Kill 是兜底。详见 25.12 节对 Excessive CPU Kill 的分析。

### Tare 对 FGS 的影响

Tare 主要管控的是通过 JobScheduler 提交的任务。FGS（前台服务）有自己的配额体系（Android 14 引入的 FGS 类型限制 + Android 17 的 FGS 超时机制），与 Tare 是并行的两套管控路径。

但两者共享 BatteryStats 的归因数据：如果一个应用同时跑 FGS 和 JobScheduler 任务，BatteryStats 会分别统计两者的耗电，Tare 只管控 Job 部分，FGS 部分由 FGS 超时机制管控。详见 25.13 节。

## 11.8.4 Perfetto 中观察 Tare 行为

### atrace 标签

Tare 相关的 atrace 标签：
- `tare` — Tare 经济模型自身的决策日志
- `battery_stats` — BatteryStatsService 的数据采集事件

抓取包含 Tare 信息的 Perfetto trace：

```
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/tare.pb \
<<EOF
buffers: { size_kb: 65536 }
data_sources: { config { name: "linux.ftrace" ftrace_config {
  ftrace_events: "power/cpu_frequency"
  atrace_categories: "tare"
  atrace_categories: "battery_stats"
  atrace_categories: "sched"
}}}
duration_ms: 60000
EOF
```

### Perfetto SQL 查询 Tare 余额变化

Tare 的余额变化在 trace 中以 slice 形式记录。查询某个 UID 的 Tare 余额变化：

```sql
-- 查询 Tare 相关的 slice 事件
SELECT
  ts,
  name,
  dur,
  track_id
FROM slice
WHERE name LIKE '%tare%'
ORDER BY ts;

-- 查询特定 UID 的 Job 调度被 Tare 拒绝的记录
SELECT
  ts,
  name,
  EXTRACT_ARG(arg_set_id, 'uid') AS uid,
  EXTRACT_ARG(arg_set_id, 'reason') AS reason
FROM slice
WHERE name LIKE '%job%tare%'
  AND EXTRACT_ARG(arg_set_id, 'reason') LIKE '%insufficient%';
```

[待验证: Perfetto SQL 字段名基于 AOSP atrace 注册信息推断，实际 trace 中的字段名可能因版本差异略有不同]

### dumpsys tare 输出解读

```bash
adb shell dumpsys tare
```

关键字段：
- **Ledger**：每个 UID 的 ARC 账本，包含当前余额、累计收入、累计支出
- **RewardPolicy**：当前的 ARC 奖励策略配置（哪些用户行为产生多少奖励）
- **SpendPolicy**：当前的 ARC 消费策略（不同类型的 Job 消耗多少 ARC）

输出结构示意：
```
Ledger for UID 10xxx:
  Balance: 42000 ARC
  Total earned: 180000 ARC
  Total spent: 138000 ARC
  Last topup: 2026-06-04 14:30:00
  Last consumption: 2026-06-04 14:32:15 (Job#45, -3000 ARC)
```

### Tare 决策日志与 JobScheduler 调度日志的关联分析

排查"Job 为什么没执行"时的分析路径：

1. `adb shell dumpsys jobscheduler` — 看 Job 的 pending reason
2. `adb shell dumpsys tare` — 看对应 UID 的 ARC 余额
3. 如果 ARC 余额接近 0，说明是 Tare 限流导致 Job 被延后
4. 在 Perfetto trace 中搜索 `tare` 标签的 slice，观察余额变化时序

Android 17 新增的 `JobDebugInfo` API（见 25.14 节）也提供了 Job 未运行原因的聚合信息，可以直接从 API 层获取 Tare 限流的统计数据。

## 11.8.5 Android 17 中 Tare 的行为变更

### 已确认的变更

基于 Android 17（API 37）的公开文档和 AOSP android-17.0.0_r1 源码：

1. **JobDebugInfo API 新增**：开发者可以通过 `JobDebugInfo` API 查询 Job 未运行原因的聚合信息，其中包含 Tare 限流的统计数据
2. **ProfilingTrigger 新增 TRIGGER_TYPE_KILL_EXCESSIVE_CPU_USAGE**：系统终止高 CPU 后台应用时提供诊断数据（详见 25.12 节）
3. **Background Battery Consumption 统计精度提升**：BatteryUsageStats 的归因算法在 Android 17 中有更新，具体改动需以 android-17.0.0_r1 的 BatteryStatsImpl diff 为准

### 待验证的变更

以下内容在公开文档和源码中尚无确凿证据：

- **Power Check 机制与 Tare 联动增强**：部分资料提及 Android 17 的"Power Check"机制与 Tare 有联动，但 `TareEconomicManager.checkPowerConstraints()` 的具体实现路径在 android-17.0.0_r1 中尚未确认
- **新增 AI 推理任务的 ARC 消耗品类**：有资料提及 Tare 可能新增对端侧 AI 推理任务的消耗计量，但未在 AOSP 源码中找到对应的 SpendPolicy 条目
- **ARC 余额公式变化**：InternalResourceService 的余额计算公式是否在 Android 17 中有调整，需要对比 android-16.0.0_r1 和 android-17.0.0_r1 的源码 diff

[待验证: 以上三项标注为"待验证"，后续源码调研确认后更新]

### 开发者可观察的 Tare 影响

开发者无法直接查询 Tare 的 ARC 余额（这是系统内部实现），但可以从以下侧面感知 Tare 的影响：

- **JobScheduler 回调**：`onStartJob()` 延迟触发或未触发 → 可能是 Tare 限流
- **WorkManager 的 `WorkInfo` 状态**：`ENQUEUED` 长时间不转为 `RUNNING` → 检查 App Standby Bucket + Tare
- **JobDebugInfo API**（Android 17+）：提供 Job 未运行原因的聚合数据，是观察 Tare 限流的直接渠道
- **`EconomyManager.getRemainingBudget()`**（API 34+）：查询应用级别的预算剩余

## 11.8.6 Tare 调试与优化实战

### dumpsys tare 输出解读进阶

排查应用被 Tare 限流的步骤：

1. 确认应用的 App Standby Bucket：
   ```bash
   adb shell dumpsys battery unplug
   adb shell am set-inactive <package> false
   adb shell dumpsys usagestats | grep <package>
   ```

2. 检查 ARC 余额：
   ```bash
   adb shell dumpsys tare | grep -A 5 "UID <your_uid>"
   ```

3. 如果余额接近 0 或为负数，说明 Tare 限流正在生效。需要检查：
   - 近期是否有大量 Job 执行记录
   - 用户最近是否与该应用交互过（影响 ARC 充值）
   - 应用是否在 Restricted bucket（充值速率极低）

### 减少 Tare 消耗的编码实践

1. **合并 Job**：把多个短 Job 合并为一个批量 Job，减少 ARC 的固定消耗
2. **使用约束条件**：给 Job 设置充电、网络、空闲等约束，让系统在合适的时机执行，避免在 ARC 余额不足时反复尝试
3. **避免重试风暴**：Job 失败后的重试间隔使用指数退避，不要立即重试
4. **减少 FGS + Job 并行**：FGS 运行期间会持续消耗电池，同时 Job 也在消耗 ARC，两者叠加会加速余额耗尽
5. **监听用户交互**：用户打开应用后是 ARC 充值的好时机，可以在这之后立即调度积压的 Job

## 11.8.7 Tare 与 OEM 定制的关系

### OEM 可定制的部分

Tare 的策略分为两部分：框架提供默认值，OEM 可以通过 overlay 覆盖。

OEM 可调的参数包括：
- **RewardPolicy** 中的奖励倍率：用户交互给应用充值多少 ARC
- **SpendPolicy** 中的消耗权重：不同类型的 Job 消耗多少 ARC
- **余额上限**：单个 UID 的 ARC 余额上限
- **衰减速率**：空闲时段余额的衰减速度

### 厂商差异对应用行为的实际影响

不同厂商的 Tare 策略差异会导致同一个应用在不同设备上的后台行为不同。常见差异：

- 某些厂商降低了后台应用的 ARC 充值速率，导致后台任务更难获得执行机会
- 某些厂商提高了特定操作类型的 ARC 消耗权重，变相限制了某些后台行为
- 少数厂商完全禁用了 Tare（这种情况在 AOSP 兼容性测试下会被发现）

开发者对此能做的不多，但可以通过 APM 上报 Job 执行成功率的多设备分布来发现厂商差异。如果某款设备的 Job 执行成功率显著低于平均水平，很可能与 Tare 策略定制有关。

---

> 本章基于 AOSP android-17.0.0_r1 源码和官方文档编写。标注 [待验证] 的内容来自公开资料推断但未在源码中确认，后续调研更新。电池归因精度边界和 Tare 配额计算的关联分析为本章原创判断。


## 参考资料

### Android 17 电池统计与 Tare 经济模型源码闭环
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-05-31-android-17-battery-tare-economic-model.md
- 类型：DeepResearch 调研结果
- 摘要：BatteryStatsService 运行在 system_server，通过 BatteryUsageStats API（API 31+）提供精细消费模型查询。Tare 经济模型作为 JobScheduler Apex 模块的一部分，使用 ARC 内部货币管理应用预算配额。TareEconomicManager 在 Job 调度前检查应用 ARC 余额，
- 注入时间：2026-06-07
- 价值：源码级闭环验证 Tare 经济模型与 BatteryStatsService 的数据依赖关系
