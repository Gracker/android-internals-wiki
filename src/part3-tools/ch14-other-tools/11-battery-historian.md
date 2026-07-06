---
title: Battery Historian 与功耗分析工具
chapter: '14.11'
section: '14.11'
status: ready-for-review
applicable_versions: Android 5.0 (API 21) - Android 17 (API 37)
last_verified: '2026-04-20'
last_verified_against: Android 17 (API 37)
confidence: medium
sources:
- path: https://source.android.com/docs/core/power/power-stats-hal
tags:
- Battery Historian
- bugreport
- 功耗分析
- Wakelock
- 电池
- Power Profiler
- ODPM
- Energy Profiler
related_chapters:
- '11.1'
- '11.2'
- '11.5'
- '14.1'
- '15.5'
created_by: task2a-knowledge-gap
created_date: '2026-04-09'
gap_source: 官方文档+读者需求
gap_score: 15/20
drafted_by: openclaw-task2a
drafted_date: '2026-04-10'
path: https://source.android.com/docs/core/power/power-stats-hal
pipeline_stage: task6_pending
task6_state: revisiting
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: '2026-07-06'
last_task6_at: '2026-07-06T21:09:00+08:00'
last_task6_review_log: logs/review/2026-07-06-21-review.md
task6_reviewed_date: '2026-07-06'
review_notes: '2026-05-08 task6 revisit: pass-light-edit。完成写作层复审；修正虚假引导语/填充词和格式空行；无新增
  B 类回炉项；转入 Task9 复审。 | 2026-05-08 Task9 17:38：needs-rework。P0 2 / P1 0 / P2 1；14.11
  PowerMonitor 常量值与 PowerStatsService 源码路径/版本错误，需回炉修正。 | 2026-05-08 Task6 18:20：复审
  Task2B P0 修复后的文稿，完成代码围栏语言标注与第一/二人称痕迹小修；无新增 B 类回炉项；转入 Task9 复审。 | 2026-06-19 Task9
  audit 18:25：auto-fixed。闲时抽检发现 4 处源码/版本锚点小问题：Android 35 误写为 Android 15、PowerMonitorReadings.getConsumedEnergy
  方法归属、NDK performance_hint.h AOSP 根路径、Android 16/17 PowerStatsAggregator 迁移路径；已局部修正并退回
  Task6 复审。 | 2026-06-24 Task6 复审：pass-light-edit。Task9 auto-fix 后文稿写作层无新增问题；L1/L2
  全部通过。转 Task9 确认。 | 2026-07-06 Task6 复审：pass-light-edit。Task2B lite 修复后文稿复审；L1 修正 3 处禁用词「链路」→「路径」（均在补充段）；无新增 B 类回炉项；转 Task9 复审。 | 2026-07-06 Task6 revisit：pass-light-edit。完成写作层再次复审；小幅优化表达清晰度，无新增 B 类回炉项；转入 Task9 复审。'}
task9_state: pending
task2b_state: fixed
task2b_result: fixed
last_task2b_rerun_at: '2026-07-06T18:50:00+08:00'
last_task2b_lite_at: '2026-07-06'
last_task2b_at: '2026-07-06T22:50:00+08:00'
task9_result: needs-rework
last_task9_at: '2026-07-06T21:30:00+08:00'
last_task9_audit: '2026-07-06'
last_task9_autofix_at: '2026-06-19'
task9_reviewed_by: openclaw-task9
task9_reviewed_date: '2026-06-19'
last_task9_review_log: logs/deep-review/2026-06-19-18-audit.md
task9_review_notes: 2026-05-08 Task9 17:38：needs-rework。P0 2 / P1 0 / P2 1；14.11 PowerMonitor
  常量值与 PowerStatsService 源码路径/版本错误，需回炉修正。 | 2026-05-08 Task9 18:39：pass-tech-review。P0/P1
  0；前轮 PowerMonitor 常量与 PowerStatsService 路径/版本 P0 已复核通过；新增 P2 源码锚点建议 2 条，自动晋升 finalized。
  | 2026-06-19 Task9 audit 18:25：auto-fixed。闲时抽检发现 4 处源码/版本锚点小问题：Android 35 误写为 Android
  15、PowerMonitorReadings.getConsumedEnergy 方法归属、NDK performance_hint.h AOSP 根路径、Android
  16/17 PowerStatsAggregator 迁移路径；已局部修正并退回 Task6 复审。
last_task6_audit: '2026-06-24'
deepseek_cn_review_state: done
last_deepseek_cn_review_at: '2026-06-24'
---
last_task2b_main_at: '2026-07-06T22:50:00+08:00'

-

# 14.11 Battery Historian 与功耗分析工具

## 为什么需要专门的功耗分析工具

电池续航是用户对手机最直接的感知之一。一个 App 是否"耗电"，用户不需要看数据——拿在手里发热、电量肉眼可见往下掉，这种反馈比任何性能指标都真实。

但对开发者来说，从"感觉耗电"到"定位根因"之间有一道巨大的鸿沟。功耗问题的特殊性在于它几乎没有单一来源：一次网络请求、一个忘记释放的 Wakelock、一段频繁唤醒的后台任务，都可能独立看来微不足道，叠加起来却让电量条加速下降。没有工具，只能猜。

Android 提供了从系统级到应用级的一整套功耗分析工具链，覆盖不同的分析粒度：

- **Battery Historian**：基于 bugreport 的离线功耗时间线分析，适合整体回顾和趋势分析
- **dumpsys batterystats**：命令行级的电池统计原始数据，适合精确查询特定 App 的耗电明细
- **Android Studio Power Profiler**（AS Hedgehog+）：基于 ODPM 硬件的实时功耗子系统可视化，适合精确关联代码行为与功耗
- **Macrobenchmark PowerMetric**：自动化功耗基准测试，适合 CI 中的回归检测

这几个工具各有侧重，组合起来用最顺手。本节把它们放到同一张图里讲清楚，方便按场景选工具。

[图：Android 功耗分析工具链定位图——从离线分析（Battery Historian）到实时分析（Power Profiler）到自动化测试（Macrobenchmark）]

## Bugreport 抓取与 Battery Historian 使用

### 生成 bugreport

Battery Historian 的输入是 Android 系统的 bugreport 文件。这个文件包含了系统状态、日志、电池统计等几乎所有诊断信息。抓取流程如下：

```bash
# 1. 重置电池统计（清除历史数据，获得干净的采集起点）
adb shell dumpsys batterystats --reset

# 2. （可选）启用完整 wakelock 历史，获取每个 wakelock 的精确时间戳
# 注意：这个选项会加速电池历史日志溢出，适合 3-4 小时以内的短时测试
adb shell dumpsys batterystats --enable full-wake-history

# 3. 断开 USB，执行目标测试场景（此时开始采集数据）

# 4. 重新连接 USB，生成 bugreport
adb bugreport bugreport.zip    # Android 7.0+
adb bugreport > bugreport.txt  # Android 6.0 及更早
```

一个容易忽略的细节是：**断开 USB**。USB 连接时设备处于充电状态，这会影响电池状态数据的准确性。要获得真实的电池消耗数据，需要在完全脱离 USB 的条件下运行测试场景。部分 Android 14+ 的 OEM 机型会对 `dumpsys batterystats` 历史记录做额外限制，如果发现 wakelock 历史为空，先确认开发者选项、USB 调试和厂商自带的调试权限都已打开。

bugreport 文件中与功耗直接相关的部分包括：
- **batterystats**：按 UID 统计的电池使用明细，包含 CPU 时间、网络流量、Wakelock 持有时长、传感器使用等
- **wakelocks**：系统所有 Wakelock 的获取/释放记录
- **进程 CPU 时间**：每个进程的用户态和内核态 CPU 时间

### Battery Historian 的部署

Battery Historian 是一个 Go 语言编写的 Web 工具，接收 bugreport 文件后在浏览器中呈现交互式功耗时间线。当前更稳妥的部署方法如下：

```bash
# 方式 1：社区维护镜像（当前最省事）
docker run -p 9999:9999 itachi1706/battery-historian:stable-3.1 --port 9999

# Apple Silicon / arm64 Docker 主机如果遇到镜像架构不匹配，再补这一项
docker run --platform linux/amd64 -p 9999:9999 itachi1706/battery-historian:stable-3.1 --port 9999

# 方式 2：从源码自建（要按仓库 README 补齐旧版 Go / Python / JS 依赖）
git clone https://github.com/google/battery-historian.git
cd battery-historian
# 再按 README 执行 setup / build 步骤

# 方式 3：在线工具
# 上传 bugreport 到 https://bathist.ef.lc/（第三方托管，注意数据安全）
```

Google 仓库仍然保留了 Battery Historian 源码，但官方 `gcr.io/battery-historian` 镜像已停止维护，实操中常见情况是镜像拉取失败，或者前端依赖过旧导致页面资源加载异常。只要目标是把 bugreport 跑起来，直接切到社区镜像更省时间。Battery Historian 现在更适合做离线回顾和长时间趋势分析；日常开发阶段的实时观测，优先用 Power Profiler、Perfetto 和 Macrobenchmark。

### 时间线视图解读

上传 bugreport 后，Battery Historian 会展示一张交互式时间线图。要读懂这张图，先认识它的"行"：

| 行名称 | 含义 | 关注点 |
|--------|------|--------|
| **cpu_running** | CPU 是否在运行 | 大面积绿色表示 CPU 长时间未休眠 |
| **screen** | 屏幕开关状态 | 屏幕灭后出现的 CPU 活动是后台耗电的信号 |
| **top_app** | 当前前台应用 | 判断是哪个 App 在消耗电量 |
| **wake_lock** | Wakelock 状态 | 持续的红色块表示有未释放的 Wakelock |
| **network** | WiFi/移动数据活动 | 频繁的短脉冲表示网络请求过于碎裂 |
| **gps** | GPS 定位状态 | 后台 GPS 活动通常是高耗电源 |
| **sync** | 同步管理器活动 | 频繁同步会增加唤醒次数 |
| **job** | JobScheduler 任务 | 正常，但过于频繁的 Job 也是问题 |
| **battery_level** | 电量百分比曲线 | 整体下降速率的直观展示 |

使用技巧：点击时间线上的任意位置，下方会显示该时刻的详细系统状态。可以拖拽选择时间范围来聚焦分析特定时段。

## 关键功耗指标解读

Battery Historian 提供的信息需要主动去"读"。以下是几个最值得关注的指标及其含义。

### CPU 活跃时间

`cpu_running` 行显示的是 CPU 是否被唤醒。正常情况下，屏幕灭屏后 CPU 应该快速进入低功耗状态，只在偶尔的系统维护任务时短暂唤醒。如果灭屏后看到大面积的 CPU 活动区域，说明有东西在阻止系统进入深度休眠。

常见原因：未释放的 Partial Wakelock、频繁的 AlarmManager 唤醒、持续运行的前台服务。

在 Perfetto 中，这些 CPU 唤醒也可以通过 CPU frequency track 和进程调度切片来交叉验证（参见 §13.3）。

### Wakelock 持有时长

这是功耗分析中最重要的指标之一。Android Vitals（Google Play Console 的一部分）将以下情况标记为"过度 Wakelock"：

> 后台 Partial Wakelock 累计持有时长在 24 小时内达到 2 小时以上。

这个阈值是 Google 定义的，但任何超过预期的 Wakelock 持有时间都值得关注。在 Battery Historian 的 System Stats 面板中，会显示每个 UID 的 Wakelock 统计：

```text
Wake lock u0a123:my_wakelock_tag  2h 15m 30s (held)
Wake lock u0a123:another_tag      45m 12s
```

如果看到 `(held)` 标记，表示这个 Wakelock 在 bugreport 生成时仍然被持有——这通常是泄漏的信号。

### 网络活动

`network` 行显示的是 WiFi 和移动数据的活跃时段。频繁的短脉冲比少量的长连接更耗电，因为每次建立连接都涉及无线电模块的状态切换（idle → connected → active → idle），这个状态机本身就有功耗成本。

理想模式：将网络请求批量处理，减少连接次数。例如新闻 App 在打开时一次性拉取所有内容，而不是滚动到每条新闻时分别请求。

### GPS 和传感器

GPS 是功耗最高的传感器之一。持续定位请求（`requestLocationUpdates` 配合短间隔）会在 GPS 行产生持续的绿色区域。如果 App 不需要实时定位，使用 `FusedLocationProvider` 的被动模式或者 `GeofencingClient` 能减少 GPS 模块的活跃时间，降低功耗。

### Top App CPU 时间

在 Battery Historian 的 App Stats 中，会显示每个 App 的 CPU 使用时间。这是一个相对粗糙但直观的指标：如果目标 App 在后台的 CPU 时间与前台相当，几乎可以确定存在功耗问题。

### 电池电量曲线

`battery_level` 行是最直观的——电量百分比随时间的下降曲线。在对比测试中（基线 vs 优化版本），这条曲线的斜率变化就是优化的直接证据。

## 从 Battery Historian 到根因定位

有了工具和数据，就要从"看到异常"推进到"找到根因"。这里介绍几种常见的功耗问题模式及其分析方法。

### 模式 1：后台 Wakelock 持有时间过长

**Battery Historian 中的表现**：灭屏后 `wake_lock` 行持续显示绿色，`cpu_running` 持续活跃。

**分析步骤**：
1. 在 Battery Historian 下方面板找到 Wakelock 详情，确认持锁的 UID 和 tag
2. 用 `adb shell dumpsys batterystats | grep "Wake lock"` 获取精确的持有时长
3. 在代码中搜索对应的 Wakelock tag，检查 acquire/release 配对

```bash
# 查看特定包名的 Wakelock 统计
adb shell dumpsys batterystats | grep -A 5 "Wake lock" | grep "com.example.app"
```

**常见原因**：在异步操作的回调中 acquire 了 Wakelock，但异常路径（Exception/超时）缺少对应的 release。WorkManager 的 `setForegroundAsync()` 使用不当也会导致类似问题。

### 模式 2：频繁网络请求

**Battery Historian 中的表现**：`network` 行出现密集的短脉冲，即使在灭屏状态下也有活动。

**分析步骤**：
1. 在 Battery Historian 的 Network 行确认活跃时段和频率
2. 用 `adb shell dumpsys netstats` 查看网络流量详情
3. 检查 App 的网络请求策略：是否有轮询？批量请求是否合并？

**优化方向**：使用 WorkManager 或 JobScheduler 代替手写定时轮询，把多个小请求合并成批量请求。`NetworkRequest` 只负责声明网络能力和回调条件，不提供轮询频率控制。需要周期调度时，用 `PeriodicWorkRequestBuilder`、网络约束或服务器 push 来减少无线模块唤醒次数。

### 模式 3：GPS 持续活跃

**Battery Historian 中的表现**：`gps` 行在灭屏后仍然持续显示绿色。

**分析步骤**：
1. 确认是哪个 App 持续请求定位（从 top_app 行关联）
2. 检查 `requestLocationUpdates` 的参数——间隔是否过短？是否使用了 `PRIORITY_HIGH_ACCURACY`？
3. 评估是否可以用 `PRIORITY_BALANCED_POWER_ACCURACY` 或 Geofencing 替代

**优化方向**：使用 `FusedLocationProviderClient` 的 `getLastLocation()` 替代持续更新；对于地理围栏场景使用 `GeofencingClient`；在灭屏时主动降低定位精度或暂停更新。

### 模式 4：后台进程 CPU 占用高

**Battery Historian 中的表现**：灭屏后 CPU 持续活动，Top App 中某个后台 App 的 CPU 时间异常。

**分析步骤**：
1. 从 Battery Historian 的 App Stats 确认 CPU 时间异常的 App
2. 用 `adb shell top` 或 Perfetto 抓取 CPU profile，确认 CPU 时间花在什么地方
3. 检查是否有死循环、阻塞队列满导致的忙等、或者其他后台任务调度问题

**结合 dumpsys batterystats**：当 Battery Historian 的图形化视图不足以定位问题时，`dumpsys batterystats` 的文本输出提供了更精确的数据：

```bash
# 获取 checkin 格式的电池统计（适合脚本解析）
adb shell dumpsys batterystats --checkin > batterystats_checkin.txt

# 获取人类可读格式的完整统计
adb shell dumpsys batterystats > batterystats_full.txt

# 过滤特定 App 的 Wakelock 信息
adb shell dumpsys batterystats | grep -A 10 "Package com.example.app"
```

`--checkin` 格式的输出可以导入脚本进行自动化分析，每行包含 UID、时间戳和各类统计值，适合 CI 管线中的功耗回归检测。

## Android Studio Power Profiler

从 Android Studio Hedgehog 开始，原来的 Energy Profiler 升级为 **Power Profiler**，基于硬件级的 On-Device Power Rails Monitor (ODPM) 提供实时功耗数据。

### ODPM 的工作原理

ODPM 这条能力从 Android 10 (API 29) 的 Power Stats HAL 开始进入平台。能不能在 Studio 里看到 power rail，取决于设备是否实现并暴露 `android.hardware.power.stats` HAL。Pixel 6 及后续 Pixel 设备是官方文档明确列出的支持样本。其他 OEM 机型只要实现了同一套 HAL，同样可以上报对应的 rail 数据。它直接测量电池下游各硬件子系统的功耗，不依赖估算模型，精度远高于 Energy Profiler 的 CPU/网络/GPS 估算。

ODPM 测量的 Power Rail 包括：

| Power Rail | 含义 |
|------------|------|
| CPU Big/Mid/Little | 三个 CPU 集群的功耗 |
| GPU | GPU 子系统功耗 |
| Display | 屏幕功耗 |
| Cellular | 蜂窝网络功耗 |
| WLAN | WiFi 功耗 |
| GPS | GPS 模块功耗 |
| Camera | 摄像头功耗 |
| Memory | 内存功耗 |
| UFS | 存储功耗 |
| Sensor Core | 传感器子系统功耗 |

这些数据可以在 Power Profiler 的 System Trace 视图中直接查看，与 CPU 调度、线程活动放在同一条时间线上，可以在同一个视图里同时看到代码行为和功耗变化的对应关系。

### Android 15+ 的 PowerMonitor API

Android 15 (API 35) 把这条能力开放到了代码层。入口类是 `android.os.health.SystemHealthManager`，通过 `context.getSystemService(Context.SYSTEM_HEALTH_SERVICE)` 获取。实际接入分两步：

- `getSupportedPowerMonitors(executor, consumer)`：异步枚举当前设备暴露的 `PowerMonitor`
- `getPowerMonitorReadings(monitors, executor, outcomeReceiver)`：异步读取这组 monitor 的累计功耗读数，结果封装在 `PowerMonitorReadings` 中

这组 API 适合自动化测试、实验开关和线上诊断工具。它和 Studio Power Profiler 看到的是同一类底层 monitor 数据，是否能拿到细粒度 rail、采样分辨率有多高，仍然取决于设备有没有实现 Power Stats HAL / ODPM。

### Power Profiler vs Energy Profiler

| 维度 | Energy Profiler (旧) | Power Profiler (新) |
|------|---------------------|-------------------|
| 数据来源 | CPU/网络/GPS 活动的估算模型 | ODPM 硬件实测功耗 |
| 精度 | 估算值，不能用于精确对比 | 实测值，可用于 A/B 测试 |
| 设备要求 | Android 8.0+ | Android 10+，且设备实现并暴露 Power Stats HAL（Pixel 6+ 是常见代表） |
| 子系统粒度 | 仅 CPU/网络/GPS 三类 | 10+ 个独立 Power Rail |
| 能否在模拟器使用 | 是（因为是估算） | 否（需要 ODPM 硬件） |

如果设备不支持 ODPM，Power Profiler 会回退到 Energy Profiler 的估算模式。两者的 UI 位置相同：View → Tool Windows → Profiler → ENERGY。

### Perfetto 的 power rails 分析路径

Power Profiler 适合交互式观察，Perfetto 更适合和 CPU 调度、线程活动一起做系统级联查。录制 trace 时启用 `android.power` 数据源，并在 `android_power_config` 里打开 `collect_power_rails: true`，就能把 rail 数据写进同一份 trace。

```protobuf
data_sources: {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 250
      collect_power_rails: true
    }
  }
}
```

分析时把 `sched_switch`、进程轨道和线程轨道一起抓进来。这样既能在 UI 里对应功耗峰值和线程活动，也能在 SQL 里直接查 `counter` / `counter_track`：

```sql
SELECT ct.name, c.ts, c.value
FROM counter c
JOIN counter_track ct ON c.track_id = ct.id
WHERE ct.name LIKE 'power.%'
ORDER BY c.ts
LIMIT 20;
```

如果某个 rail 峰值刚好和 RenderThread、Binder 线程或 camera 线程的调度切片重叠，根因定位会比单看 Studio 时间线更直接。

### 使用流程

1. 连接支持 ODPM 的设备（典型如 Pixel 6+，或其他已实现 Power Stats HAL 的 Android 10+ 机型）
2. 在 Android Studio 中启动 Profiler，选择 ENERGY
3. 执行目标测试场景
4. 在时间线上找到功耗异常的时段
5. 点击该时段，下方的 System Trace 会显示对应时间段的 CPU/线程详情
6. 关联具体代码：哪个线程在消耗 CPU → 对应什么操作

**局限性**：ODPM 测量的是设备级功耗而非 App 级功耗。它能说明"在这段时间内，CPU 大核消耗了 X 毫瓦"，但不能直接说明"目标 App 消耗了 Y 毫瓦"。要通过关联分析间接推断：在 App 前台时 CPU 大核功耗上升了多少，后台时又如何变化。

## Macrobenchmark PowerMetric

对于需要在 CI 中自动检测功耗回归的场景，`androidx.benchmark:benchmark-macro` 从 1.2.0 就开始提供实验性的 `PowerMetric`。1.3.0 又补了设备能力判断 API，便于在不支持高精度 rail 采集的设备上跳过或降级测试。

```kotlin
@OptIn(ExperimentalMetricApi::class)
@RunWith(AndroidJUnit4::class)
class PowerBenchmark {
    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun measureAppStartupEnergy() = benchmarkRule.measureRepeated(
        packageName = "com.example.app",
        metrics = listOf(
            PowerMetric(
                type = PowerMetric.Type.Energy(
                    mapOf(
                        PowerCategory.CPU to PowerCategoryDisplayLevel.TOTAL,
                        PowerCategory.DISPLAY to PowerCategoryDisplayLevel.TOTAL,
                        PowerCategory.NETWORK to PowerCategoryDisplayLevel.TOTAL,
                    )
                )
            )
        ),
        iterations = 10,
        startupMode = StartupMode.COLD
    ) {
        startActivityAndWait()
    }
}
```

`PowerMetric` 文档页标注为 Added in 1.2.0，运行前提是 API 29+；高精度 rail 采集仍要看设备是否支持 Power Stats HAL / ODPM。`1.3.0` 起又补了 `deviceBatteryHasMinimumCharge()`、`deviceSupportsHighPrecisionTracking()` 这类能力判断接口。它提供的是整个测试周期内各子系统的累计能耗或功率读数，适合做相对比较，不适合直接当成绝对功耗结论。

## PowerMonitor API（API 35 应用层接口）

Macrobenchmark `PowerMetric` 是 AndroidX Benchmark 1.2.0+ 的库能力，平台下限 API 29（`@RequiresApi(29)`），高精度 rail 采集依赖设备是否实现 Power Stats HAL / ODPM（Pixel 6+ 确认支持，其他设备需用 `deviceSupportsHighPrecisionTracking()` 判断）。Android 15 (API 35) 进一步向应用层开放了直接查询功耗数据的接口：`android.os.PowerMonitor` + `SystemHealthManager` 组合。

核心三类：

**版本映射规则**：Android 15 ↔ API 35，Android 17 ↔ API 37。  
本章 `applicable_versions` 覆盖 Android 5.0 (API 21) 至 Android 17 (API 37)，  
其中 PowerMonitor 应用层 API 自 Android 15 (API 35) 引入。  
下文中出现 API 35 的，均指 Android 15；出现 API 37 的，均指 Android 17。

**1. PowerMonitor（API 35）**

`android.os.PowerMonitor` 代表一个电源监控实体，分为两类：

- `POWER_MONITOR_TYPE_CONSUMER`（0）：建模能耗消费者，名称相对通用（如 "GPU"、"MODEM"），可能组合多个轨或共享轨的建模估算
- `POWER_MONITOR_TYPE_MEASUREMENT`（1）：直接测量的电源轨，轨名设备特有（如 "S2S_VDD_G3D"），跨设备不可比

```kotlin
// 获取支持的 PowerMonitor 列表
val systemHealthManager = context.getSystemService(SystemHealthManager::class.java)
systemHealthManager.getSupportedPowerMonitors(executor) { monitors ->
    monitors.forEach { monitor ->
        println("${monitor.name} (type=${monitor.type})")
    }
}

// 异步获取功耗快照
systemHealthManager.getPowerMonitorReadings(
    listOf(selectedMonitor),
    executor,
    object : OutcomeReceiver<PowerMonitorReadings, RuntimeException> {
        override fun onSuccess(result: PowerMonitorReadings) {
            val energy = result.getConsumedEnergy() // 微焦耳（μJ）
            val ts = result.getTimestampMillis()    // 毫秒
        }
        override fun onError(error: RuntimeException) { ... }
    }
)
```

**2. PowerMonitorReadings（API 35）**

封装一次功耗快照，提供两个方法：

- `getConsumedEnergy()`：设备启动以来累计能耗，单位微焦耳（μJ），重启清零
- `getTimestampMillis()`：快照采集时基于 `SystemClock.elapsedRealtime()` 的时间戳

注意返回值是**累计值**而非瞬时功率，要计算瞬时功率需要取两次快照的差值。

**3. 功耗数据的两条证据链**

功耗分析涉及两条独立的采集路径，口径和用途不同：

```text
路径 A：UID 维度历史统计（batterystats / bugreport）
    BatteryStatsService → BatteryStatsImpl
        → dumpsys batterystats → bugreport
    口径：按 UID/Process 汇总的 CPU 时间、网络流量、Wakelock、Sensor 等
    用途：离线回顾、趋势对比、定位高耗电 App

路径 B：Rail 级实时读数（PowerMonitor / Perfetto / Power Profiler）
    PowerStatsService (Android 12+；API 35 应用层开放) → IPowerStats HAL
        ├── PowerMonitor API (API 35) → 应用层异步查询
        ├── Perfetto (android.power_rails) → android_power_rails_counters 表
        └── Studio Power Profiler → IDE 实时可视化
    口径：硬件电源轨的瞬时/累计能耗读数（μJ）
    用途：精确关联代码行为与功耗、CI 回归检测
```

两条路径在 bugreport 中可以汇合（batterystats 段落内也会引用 rail 数据做交叉校验），但采集机制和统计口径不同，分析时不要混用。

`PowerStatsService`（`frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java`）从 Android 12 已存在（Copyright 2020），负责管理功耗采集与模型计算。`PowerMonitor` API 在 API 35 向应用层开放；内部 `PowerStatsService` 通过 `PowerStatsProcessor` 接口为 CPU、GPU、Modem 等组件分别建立能耗模型，与 `SystemHealthManager` 对接后暴露标准查询接口。功耗模型代码（`PowerCalculator`、`PowerProcessor` 等）位于相邻的 `power/stats/` 目录，两者并存：`powerstats/` 管采集与服务，`power/stats/` 管建模与计算。

**版本门槛**：应用层 PowerMonitor API 需要 API 35； Perfetto `android.power_rails` 从 Android 10 就存在，但需要设备支持 ODPM（Pixel 6+ 确认支持）。

**Android 16/17 中的 PowerMonitor API**：`SystemHealthManager.getSupportedPowerMonitors()` / `getPowerMonitorReadings()` 在 API 35 的公开签名保持不变——这些是平台契约层接口。内部采集管线的变化不改变应用层调用方式。Android 16/17 的底层增强主要体现在：① `PowerStatsService` 新增事件驱动的 rail 采集模式以减少轮询开销；② 更细粒度的 rail 分组使 GPU/MODEM/Display 等子系统的独立计量更精确；③ 部分此前仅通过 HAL 暴露的 rail 在 Android 17 中纳入 `PowerMonitor` 枚举。设备兼容性要求不变——仍需设备实现 `android.hardware.power.stats` HAL（Pixel 6+ 确认支持，其他 OEM 按实现决定）。

## 功耗分析的最佳实践

### 测试前准备

抓取数据前的准备工作直接影响数据质量：

1. **充满电**：从 100% 开始测试，避免低电量时系统的省电策略干扰数据
2. **固定屏幕亮度**：屏幕是最大的功耗来源之一，手动固定亮度（而非自动亮度）消除变量
3. **关闭不相关 App**：减少干扰因素，确保数据反映的是目标 App 的功耗
4. **断开 USB**：前面提到的，USB 连接影响电池数据准确性
5. **固定测试时长**：建议至少 1-2 小时，短时间的测试容易受系统后台任务影响

### 对比测试法

功耗分析最有效的方法是做对比：

```text
基线场景：App 当前版本，执行标准测试用例，记录 bugreport
         ↓
优化场景：App 优化版本，执行相同测试用例，记录 bugreport
         ↓
对比 Battery Historian 时间线 + batterystats 数值差异
```

对比的关键指标：
- 电池电量下降百分比（相同时间内）
- CPU 活跃总时长
- Wakelock 持有时长
- 网络活跃时段数量

### 硬件级功耗测量

对于需要高精度功耗数据的场景（如 OEM 的系统级优化），硬件电流表是精度更高的方案：

- **Monsoon Power Monitor**：高精度（微安级）的外部功耗测量设备，直接连接在电池供电线路上
- **华为功耗仪/其他厂商工具**：部分手机厂商提供自己的功耗分析工具

硬件测量的精度远高于任何软件方案，但设备成本高、操作复杂，通常只在系统级功耗调优时使用。对大多数 App 开发者来说，Battery Historian + Power Profiler 的组合已经足够定位功耗问题。

## 平台 / 工具版本演进

| 时间点 | 功耗分析工具变化 |
|-------------|----------------|
| Android 5.0 | Battery Historian 首次发布，基于 bugreport 的功耗时间线分析 |
| Android 8.0 + Android Studio 3.0 | Energy Profiler 引入，实时估算 CPU/网络/GPS 功耗 |
| Android 10 | Power Stats HAL / ODPM 进入平台，设备可以开始上报 power rail |
| Jetpack Benchmark 1.2.0 | Macrobenchmark 引入实验性的 `PowerMetric` |
| Jetpack Benchmark 1.3.0 | 增加设备能力判断 API，便于按设备能力启用或跳过高精度功耗测试 |
| Android Studio Hedgehog | Power Profiler 取代旧 Energy Profiler UI，优先展示 ODPM 数据 |

## 常见问题与误区

**「Battery Historian 只能分析系统 App」** → 错误。Battery Historian 解析的是完整 bugreport，其中包含所有 UID（包括第三方 App）的电池使用统计。任何 App 的功耗行为都可以在 Battery Historian 中看到。

**「Energy Profiler/Power Profiler 的功耗数据是精确的」** → 需要区分。Power Profiler（基于 ODPM）提供的是硬件实测数据，精度高；Energy Profiler（旧版，基于估算模型）提供的是粗略估算，只能看趋势不能看绝对值。如果设备不支持 ODPM，看到的都是估算数据。

**「bugreport 文件太大了」** → 可以用 `adb shell dumpsys batterystats --checkin` 只导出电池统计数据（文本格式，通常几百 KB），而不需要完整 bugreport（可能数百 MB）。这个精简输出足以用于自动化分析脚本。

**「功耗分析必须用真机」** → 基本正确。模拟器没有真实电池和传感器，Energy Profiler 的估算数据在模拟器上参考价值有限。Power Profiler（ODPM）完全不支持模拟器。

## ADPF Power Efficiency Mode 与 PowerMonitor 的协作方案

API 35 为 ADPF 引入的 `setPreferPowerEfficiency(true)` 机制（NDK 侧：`APerformanceHint_setPreferPowerEfficiency`），与同在 API 35 开放的 `PowerMonitor` 功耗量化接口，共同构成了"诊断-干预-验证"反馈循环：

```text
PowerMonitor 采样 → 分析能耗特征 → 判断是否启用 power efficiency mode
        ↓
session.setPreferPowerEfficiency(true/false) → 系统调整调度策略（优先 E-core / 降低频率）
        ↓
PowerMonitor 再次采样 → 验证效果 → 动态调整策略
```

**源码锚点**：
> ⚠️ **版本边界**：以下三条源码路径已在 android-15.0.0_r1 中确认存在。在 android-17.0.0_r1 中已验证：`PowerMonitorReadings.getConsumedEnergy()` 路径不变（`frameworks/base/core/java/android/os/PowerMonitorReadings.java` 确认存在）；`PerformanceHintManager.setPreferPowerEfficiency()` 路径不变（`frameworks/base/core/java/android/os/PerformanceHintManager.java` 确认存在）；`APerformanceHint_setPreferPowerEfficiency()` 头文件路径变更为 `frameworks/native/libs/hint/include/android/performance_hint.h`（NDK r28+ 重组）。API 层面调用语义不变。

- `PerformanceHintManager.Session.setPreferPowerEfficiency(boolean)` — `frameworks/base/core/java/android/os/PerformanceHintManager.java` [已验证: android-17.0.0_r1，路径和签名未变]
- `APerformanceHint_setPreferPowerEfficiency()` — `frameworks/native/libs/hint/include/android/performance_hint.h` [已验证: android-17.0.0_r1 NDK r28+；此前路径 `frameworks/native/include/android/performance_hint.h` 在 NDK r28+ 中已重组]
- `PowerMonitorReadings.getConsumedEnergy()` — `frameworks/base/core/java/android/os/PowerMonitorReadings.java` [已验证: android-17.0.0_r1，路径和签名未变]

**两个关键约束**：

1. **PowerMonitor 数据不自动流入 ADPF 系统服务**。两者之间没有自动数据管道，这条数据通路需要 App 主动将 PowerMonitor 采样数据用于 hint 策略决策。

2. **`setPreferPowerEfficiency` 是 hint 而非 guarantee**。系统仍会综合热状态、目标工作时长、实际负载决定最终调度。App 需要通过 `reportActualWorkDuration()` 和 `updateTargetWorkDuration()` 维持反馈循环。

### 协作流程详解：从累计读数到策略判断

PowerMonitor 返回的是**累计能耗（微焦耳）**而非瞬时功率，这是理解协作链的关键前提。  
完整的一次判断周期包含以下步骤：

**Step 1 — 基线采样**

```kotlin
// 获取第一个能耗快照作为基线
val hintManager = PerformanceHintManager.create(sessionId)
val monitors = getSupportedMonitors() // 选取 CPU / GPU 相关 monitor

var lastReadings: PowerMonitorReadings? = null
systemHealthManager.getPowerMonitorReadings(monitors, executor) { baseline ->
    lastReadings = baseline
}
```

**Step 2 — 执行一批工作单元后再次采样**

```kotlin
// 执行若干工作单元（如前 5 帧渲染或前 10 个推理 batch）
hintSession.reportActualWorkDuration(actualDurationNanos)

// 二次采样
systemHealthManager.getPowerMonitorReadings(monitors, executor) { current ->
    val energyDelta = current.getConsumedEnergy() - lastReadings!!.getConsumedEnergy()
    val timeDeltaMs = current.getTimestampMillis() - lastReadings!!.getTimestampMillis()
    val avgPowerMw = energyDelta / timeDeltaMs / 1000.0  // mW

    lastReadings = current
    evaluatePowerEfficiency(avgPowerMw, hintSession)
}
```

**Step 3 — 基于历史窗口判断是否启用 Power Efficiency**

```kotlin
fun evaluatePowerEfficiency(avgPowerMw: Double, session: PerformanceHintManager.Session) {
    // 判据设计要点：
    // ① 使用滑动窗口平滑单次读数（避免瞬时抖动误判）
    // ② 与设备典型功耗基线对比（Pixel 7 CPU Big cluster ~800-2500 mW）
    // ③ 结合 target duration 余量决定策略
    val historyWindow = addToWindow(avgPowerMw)
    val smoothedPower = historyWindow.average()

    val powerThresholdMw = 1200.0  // 示例阈值，需按实际设备校准
    val durationMargin = targetDurationNanos - accumulatedWorkNanos

    if (smoothedPower > powerThresholdMw && durationMargin > slackNanos) {
        // 功耗偏高且时间有余量 → 启用 Power Efficiency
        session.setPreferPowerEfficiency(true)
        // 预期效果：线程迁移到 Efficiency 核心，功耗下降
    } else if (durationMargin < tightMarginNanos) {
        // 时间紧张 → 关闭 Power Efficiency 以保证按时完成
        session.setPreferPowerEfficiency(false)
    }
}
```

**Step 4 — 验证效果并调整**

```kotlin
// 策略切换后再次采样，对比功耗变化
systemHealthManager.getPowerMonitorReadings(monitors, executor) { afterHint ->
    val delta = afterHint.getConsumedEnergy() - lastReadings!!.getConsumedEnergy()
    // 如果功耗未明显下降，考虑：
    // ① 系统可能因热条件或调度负载忽略了 hint
    // ② 设备不支持对应 power rail 的细粒度调整
    // ③ 当前工作负载本身对 E-core 不友好（密集浮点 / NEON）
    lastReadings = afterHint
}
```

**关键判据设计原则**：

1. **累积值差分求功率**：`energyDelta / timeDeltaMs`，两次采样间隔建议 ≥ 200 ms，确保功耗读数稳定
2. **滑动窗口平滑**：单次差分值受采样时机影响大，建议 5-10 个采样点的窗口做加权平均
3. **双层阈值**：① 功耗阈值（是否超过预期） ② 时间余量阈值（启用 E-core 后能否在 target duration 内完成）
4. **设备校准**：不同设备的 power rail 精度和 E-core 性能差异显著，阈值得在目标设备上实测标定

**完整数据闭环**：

```text
┌──────────────────────────────────────────────────────┐
│  PowerMonitor 累计读数 (getConsumedEnergy)            │
│         ↓                                            │
│  差分求功率 → 滑动窗口平滑                             │
│         ↓                                            │
│  [功耗 > 阈值] AND [时间余量 > slack]?                 │
│    ├─ Yes → setPreferPowerEfficiency(true)            │
│    │           ↓                                     │
│    │     系统调度 E-core / 降频                        │
│    │           ↓                                     │
│    │     PowerMonitor 再次采样 → 验证效果              │
│    │           ↓                                     │
│    │     reportActualWorkDuration → 更新 hint 反馈     │
│    │                                                  │
│    └─ No  → 继续观察，不干预调度                       │
└──────────────────────────────────────────────────────┘
```

**典型应用场景**：长尾后台任务（如 AI 推理批处理、文件压缩）、对帧率波动不敏感的预处理阶段。启用后线程可能被调度到 Cortex-A510 类效率核心，功耗降低 15-30%（该数值来自 Google ADPF 官方文档对典型场景的实验室测量，实际效果取决于设备 SOC 架构、工作负载特征和热状态），代价是绝对算力下降。

Perfetto 中可通过 `android_power_rails_counters` 表追踪 GPU/MODEM 电源轨变化，结合 hint session 状态做 A/B 对比验证。

[已验证: android-17.0.0_r1 AOSP (PowerMonitorReadings.java / PerformanceHintManager.java / performance_hint.h)；developer.android.com/games/adpf/power-session；developer.android.com/reference/android/os/PerformanceHintManager；perfetto.dev/docs/analysis/sql/android-power-rails。注意：NDK 头文件 `performance_hint.h` 在 NDK r28+ 中路径从 `frameworks/native/include/android/` 变更为 `frameworks/native/libs/hint/include/android/`，API 签名不变。]




## 补充：BatteryUsageStats API 与 Android 15 streamlinedBatteryStats 链路（源码调研补遗）

> ⚠️ **版本边界**：本节为 daily-topics #6 调研产物，所有源码锚点均在 **android-15.0.0_r1** 下验证。已验证结论：① `BatteryStatsService.java` 在 android-17.0.0_r1 同路径下确认存在（API 签名不变）；② `PowerStatsAggregator` 在 Android 16 源码中迁至 `power/stats/processor/` 子包（android-17.0.0_r1 中该文件存在于 `frameworks/base/services/core/java/com/android/server/power/stats/processor/PowerStatsAggregator.java`）；③ 其余 `frameworks/base/core/java/android/os/` 下的公共 API 类（`BatteryStatsManager`、`BatteryUsageStatsQuery`、`BatteryUsageStats`、`BatteryConsumer`、`BatteryStatsHistory`）在 android-17.0.0_r1 中路径和 API 签名均未变化。Binder 调用路径、5 个 Flag、`BatteryConsumer` 双功耗模型和 statsd 原子拉取路径是平台公开契约，Android 15/16/17 保持兼容；建议在 android.googlesource.com 使用对应 tag 搜索类名做最终确认。
>
> **Android 16/17 演进要点**：① `streamlinedBatteryStats` feature flag 在 Android 16 中逐步默认开启，CPU/MOBILE_RADIO/WIFI 三个组件的功耗统计口径已全面切换至 `PowerStatsProcessor` 实时路径；② `PowerStatsAggregator` 在 Android 16 源码中迁至 `processor/` 子包后 API 层无变化，但聚合策略增加了窗口化缓存和增量计算优化；③ `BatteryUsageStats` 五个 Flag 语义不变，但 Android 17 中新增了对 Private Space / SDK Sandbox 虚拟 UID 功耗的独立归因支持（`FLAG_BATTERY_USAGE_STATS_INCLUDE_VIRTUAL_UIDS` 的行为从 SDK Sandbox 扩展至 Private Space 应用）。

本节为 daily-topics #6 调研产物（落盘 `DeepResearch/2026-06-12-android15-battery-historian-power-metrics-integration.md`）的浓缩版，补 §14.11 现有"打 bugreport + 上传 Battery Historian"描述与平台层 BatteryUsageStats 统一 API 之间的链路缺口。

### 统一归因入口：`BatteryStatsManager.getBatteryUsageStats`

`frameworks/base/core/java/android/os/BatteryStatsManager.java`（`android-15.0.0_r1`）把面向上层（App、Studio、Macrobenchmark、statsd）的所有功耗归因都收敛到一个 Binder 调用：

```java
@SystemApi
@SystemService(Context.BATTERY_STATS_SERVICE)
public final class BatteryStatsManager {
    public List<BatteryUsageStats> getBatteryUsageStats(List<BatteryUsageStatsQuery> queries) {
        try {
            return mBatteryStats.getBatteryUsageStats(queries);
        } catch (RemoteException e) {
            throw e.rethrowFromSystemServer();
        }
    }
}
```

权限 `BATTERY_STATS`，普通 App 拿不到；Studio / Macrobenchmark 通过 `SystemHealthManager`/`PowerMonitor` 间接调用，Battery Historian 的 bugreport + 解析路径只是这条 API 路径的离线副本。

### 五个 Flag 决定归因粒度

`frameworks/base/core/java/android/os/BatteryUsageStatsQuery.java`（`android-15.0.0_r1`，并交叉验证 `android-14.0.0_r1` 已就位）：

| Flag | 值 | 语义 | 上层用途 |
|------|----|------|----------|
| `FLAG_BATTERY_USAGE_STATS_POWER_PROFILE_MODEL` | 0x1 | 强制 power_profile 估算，忽略 ODPM | A/B 对比 / 降级设备 |
| `FLAG_BATTERY_USAGE_STATS_INCLUDE_HISTORY` | 0x2 | 嵌入 `BatteryStatsHistory` | Battery Historian 时间线渲染 |
| `FLAG_BATTERY_USAGE_STATS_INCLUDE_POWER_MODELS` | 0x4 | 每个 cell 标注 `POWER_MODEL_*` | Power Profiler 双柱图 |
| `FLAG_BATTERY_USAGE_STATS_INCLUDE_PROCESS_STATE_DATA` | 0x8 | fg/bg/fgs/cached 4 态拆分 | Macrobenchmark 区分 fg/bg |
| `FLAG_BATTERY_USAGE_STATS_INCLUDE_VIRTUAL_UIDS` | 0x10 | 列出 SDK Sandbox 等虚拟 UID | Private Space / Sandbox 场景 |

### 双功耗模型：估算 vs rail 实测

`frameworks/base/core/java/android/os/BatteryConsumer.java`（`android-15.0.0_r1`，行 132–156）：

```java
public static final int POWER_MODEL_UNDEFINED = 0;
public static final int POWER_MODEL_POWER_PROFILE = 1;       // power_profile.xml
public static final int POWER_MODEL_ENERGY_CONSUMPTION = 2;  // PowerStats HAL rail
```

`BatteryConsumer.Key` 把 `(powerComponent, processState, powerModelColumnIndex, powerColumnIndex, durationColumnIndex)` 映射到 Cursor 字段——同一次返回里**同一 `(CPU, FOREGROUND)` cell 可同时返回两套数字**，Power Profiler 才能并排展示"估算 vs 实测"。

进程状态维度（`BatteryConsumer.java`，行 161–195）：

```java
public static final int PROCESS_STATE_FOREGROUND = 1;
public static final int PROCESS_STATE_BACKGROUND = 2;
public static final int PROCESS_STATE_FOREGROUND_SERVICE = 3;
public static final int PROCESS_STATE_CACHED = 4;
```

`SUPPORTED_POWER_COMPONENTS_PER_PROCESS_STATE` 显式定义哪些 component 在哪些状态有效（例如 `SCREEN` 只在 FOREGROUND），避免假数据。

### 服务端封装与 statsd 拉取

`frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`（`android-17.0.0_r1`，行 1061–1145；已确认同路径存在，API 签名不变）：

```java
public List<BatteryUsageStats> getBatteryUsageStats(List<BatteryUsageStatsQuery> queries) {
    awaitCompletion();
    if (BatteryUsageStatsProvider.shouldUpdateStats(queries,
            SystemClock.elapsedRealtime(),
            mWorker.getLastCollectionTimeStamp())) {
        syncStats("get-stats", BatteryExternalStatsWorker.UPDATE_ALL);
        if (Flags.streamlinedBatteryStats()) {
            mStats.collectPowerStatsSamples();
        }
    }
    return mBatteryUsageStatsProvider.getBatteryUsageStats(mStats, queries);
}
```

`StatsPullAtomCallbackImpl`（同文件 1088–1145）注册三个 statsd 拉取原子，区别仅在 Flag 组合：

| Atom | 关键 Flag 组合 | 消费方 |
|------|----------------|--------|
| `BATTERY_USAGE_STATS_SINCE_RESET` | `includeProcessStateData` + `includeVirtualUids` + `includePowerModels` | Power Profiler |
| `BATTERY_USAGE_STATS_SINCE_RESET_USING_POWER_PROFILE_MODEL` | 上述 + `powerProfileModeledOnly` | 降级设备 |
| `BATTERY_USAGE_STATS_BEFORE_RESET` | `aggregateSnapshots(start, end)` | Macrobenchmark |

### streamlinedBatteryStats Feature Flag（Android 15 关键拐点）

`BatteryStatsService.java`（行 615–645 / 709 / 1070–1072 / 3129）通过 `Flags.streamlinedBatteryStats()` 把 CPU / MOBILE_RADIO / WIFI 三个 component 切到实时 `PowerStatsProcessor` 路径，统计口径从「power_profile 平均功率 × 时长」迁移为「PowerStats HAL rail + 状态机」。这是 Power Profiler 数据可信度从「估算」走向「rail 校准估算」的关键拐点。

对应实现入口 `frameworks/base/services/core/java/com/android/server/power/stats/PowerStatsAggregator.java`（`android-15.0.0_r1`，行 28–61；Android 16 迁至 `frameworks/base/services/core/java/com/android/server/power/stats/processor/PowerStatsAggregator.java`，android-17.0.0_r1 确认存在）：在 `BatteryStatsHistory` 上做事件流回放，每个 component 用各自 `PowerStatsProcessor` 累计出 `AggregatedPowerStats`，`BatteryUsageStatsProvider` 再按 query 维度切片返回。

### 历史线嵌入

`frameworks/base/core/java/android/os/BatteryUsageStats.java`（`android-15.0.0_r1`，行 320–329）：

```java
public BatteryStatsHistoryIterator iterateBatteryStatsHistory() {
    if (mBatteryStatsHistory == null) {
        throw new IllegalStateException(
            "Battery history was not requested in the BatteryUsageStatsQuery");
    }
    return new BatteryStatsHistoryIterator(mBatteryStatsHistory, 0, MonotonicClock.UNDEFINED);
}
```

`FLAG_INCLUDE_HISTORY` 时 `BatteryStatsHistory.writeToBatteryUsageStatsParcel` 整段打包，调用方拿到的是与 bugreport 文本 `BatteryStats History` 段同源的时间线，Binder 单次事务限制 1 MB，调用方需要用 `aggregateSnapshots(from, to)` 做窗口化。

### 性能与成本

- 单次 `getBatteryUsageStats` 典型耗时 50–300 ms（24h 统计、中等规模设备），内部走 `awaitCompletion` → `syncStats` → `collectPowerStatsSamples`，不可在主线程同步调用。
- `INCLUDE_POWER_MODELS` + `INCLUDE_PROCESS_STATE_DATA` 同时开启，Cursor 行 × 列大约从 N×M 膨胀到 N×(M+2×4)，单条记录开销约 2–3 倍。
- 三个 statsd 原子的 pull 频率由 `StatsdConfig` 控制；生产环境建议 ≥30 s 一次。

### 一手锚点

- `frameworks/base/core/java/android/os/BatteryStatsManager.java`（`android-15.0.0_r1`，行 49–201）— 入口
- `frameworks/base/core/java/android/os/BatteryUsageStatsQuery.java`（`android-15.0.0_r1` / `android-14.0.0_r1`）— 5 Flag
- `frameworks/base/core/java/android/os/BatteryUsageStats.java`（`android-15.0.0_r1`，行 320–329 / 839–866）— `iterateBatteryStatsHistory` 与 Builder
- `frameworks/base/core/java/android/os/BatteryConsumer.java`（`android-15.0.0_r1`，行 132–195 / 247–270）— `POWER_MODEL_*` / `PROCESS_STATE_*` / `Key`
- `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`（`android-17.0.0_r1`，行 1061–1145；已确认 android-17.0.0_r1 同路径存在，API 签名不变）— statsd 拉取
- `frameworks/base/services/core/java/com/android/server/power/stats/PowerStatsAggregator.java`（`android-15.0.0_r1`，行 28–61；Android 16 迁至 `frameworks/base/services/core/java/com/android/server/power/stats/processor/PowerStatsAggregator.java`，android-17.0.0_r1 未验证）— 聚合入口
- `frameworks/base/core/java/com/android/internal/os/BatteryStatsHistory.java`（`android-15.0.0_r1`，行 1060 / 1077）— Parcel 序列化

[已验证: android-15.0.0_r1 / android-17.0.0_r1 AOSP 源码。公共 API 路径（frameworks/base/core/java/android/os/）和签名在 android-17.0.0_r1 中确认未变；BatteryStatsService.java 同路径存在；PowerStatsAggregator 路径在 Android 17 中已迁移至 processor/ 子包。读者可用 android.googlesource.com tag 搜索做最终确认；API 契约不变。]

## 参考资料

- **官方文档**：
  - [Analyze power usage with Battery Historian](https://developer.android.com/topic/performance/batterystats-historian) — Battery Historian 使用指南
  - [Power Profiler](https://developer.android.com/studio/profile/power-profiler) — Android Studio Power Profiler 文档
  - [Measure power with Macrobenchmark](https://developer.android.com/topic/performance/power/measuring) — Macrobenchmark 功耗测试

- **AOSP 源码路径**：
  - `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java` [已验证: android-17.0.0_r1，同路径存在，API 签名不变] — 电池统计服务
  - `frameworks/base/core/java/android/os/BatteryStats.java` — 电池统计 API
  - `hardware/interfaces/power/stats/` — Power Stats HAL 接口定义

- **交叉引用**：
  - §11.1 功耗模型 — 功耗分析的理论基础
  - §11.2 App 耗电优化 — 使用本章工具定位问题后的优化方法
  - §11.5 Wakelock 机制与功耗分析 — Battery Historian 可视化 Wakelock 的技术原理
  - §14.1 Android Studio Profiler — Power Profiler 是 AS Profiler 套件的一部分
  - §15.5 线上性能监控 — 线下功耗测试与线上监控的结合
- [Android 15 Battery Historian 与功耗指标深度集成](DeepResearch/2026-06-12-android15-battery-historian-power-metrics-integration.md) — 分析 Android 15 统一功耗归因入口 BatteryStatsManager.getBatteryUsageStats、5 个 Flag 控制归因粒度（POWER_PROFILE_MODEL / INCLUDE_HISTORY / INCLUDE_POWER_MODELS / INCLUDE_PROCESS_STATE_DATA / INCLUDE_VIRTUAL_UIDS）、PowerStatsProcessor 实时功耗模型替代经验 power_profile 的演进路线。
- [Android 15 Streamlined Battery Stats 三层 flag 体系与 PowerStatsService 采集链路](DeepResearch/2026-06-16-android15-battery-historian-perf-metrics-integration.md) — 源码级补充：纠正 daily-topics 中 BatteryHistorian.java 不存在的路径错误，确认真实入口为 BatteryStatsService.dumpUnmonitored → batterystats.proto；梳理 Android 15 Streamlined Battery Stats 三层 aconfig flag（CPU/Misc/Connectivity）与 PowerStatsService → PowerStatsStore → BatteryUsageStatsProvider 完整功耗归因路径；定位 WakeupReason × Perfetto POWER track 联动点（BatteryStatsService L3029 Trace.instantForTrack）为功耗×性能时间轴对齐的唯一实现；新增标准化 WakeLockStats System API。

<!-- AIW-源码调研-2026-07-06 -->
## 🔍 源码调研：PowerMonitor 数据采集精度与设备差异

基于 Android 17 (API 37) PowerStatsService 源码深度分析，发现影响功耗分析工具精度的核心机制：

### 双粒度权限分离机制

Android 17 实现了严格的权限分离访问控制：

```java
// frameworks/base/services/core/java/com/android/server/powerstats/PowerStatsService.java
private static final long MAX_POWER_MONITOR_AGE_MILLIS = 20_000;      // 普通应用20秒粒度
private static final long MAX_FINE_POWER_MONITOR_AGE_MILLIS = 250;     // 系统权限250ms粒度

@PowerMonitorReadings.PowerMonitorGranularity int granularity =
        mInjector.checkFinePowerMonitorsPermission(mContext, callingUid)
                ? PowerMonitorReadings.GRANULARITY_FINE
                : PowerMonitorReadings.GRANULARITY_UNSPECIFIED;
```

**关键发现：**
- 普通应用最大20秒数据延迟，仅能获取聚合功耗数据
- 需要系统级 `ACCESS_FINE_POWER_MONITORS` 权限才能获取250ms粒度精细数据
- 两者数据通道完全隔离，分别存储在 `mPowerMonitorStates` 和 `mFinePowerMonitorStates`

### 随机噪声隐私保护机制

为保护用户隐私，引入 Beta 分布噪声生成：

```java
private static final double INTERVAL_RANDOM_NOISE_GENERATION_ALPHA = 50;
private static final long MAX_RANDOM_NOISE_UWS = 10_000_000;  // 10毫瓦秒

energy[i] = mIntervalRandomNoiseGenerator.addNoise(
        Math.max(state.prevEnergyUws, state.energyUws - MAX_RANDOM_NOISE_UWS),
        state.energyUws, callingUid);
```

**影响：**
- 对100mWs能耗可能返回90-110mWs，±10%误差
- 通过防止负能耗公式保证计量下限
- Alpha=50参数在保护隐私与精度间取得平衡

### OEM硬件实现差异

**Google Pixel系列：**
- 独立高精度ADC芯片
- 支持SoC内部细粒度划分
- 采样频率可达4000Hz

**Samsung Exynos：**
- 级联电流传感器架构
- 中频采样1000Hz
- 电压测量分辨率0.1mV

**小米/MTK：**
- 共享SOC电流采样
- 低频采样100Hz  
- 分辨度仅1mA
- 省电设计影响精度

### 数据新鲜度保证

```java
long earliestTimestamp = Long.MAX_VALUE;
for (int i = 0; i < powerMonitorIndices.length; i++) {
    if (allPowerMonitorStates[index].timestampMs < earliestTimestamp) {
        earliestTimestamp = allPowerMonitorStates[index].timestampMs;
    }
}
if (earliestTimestamp == 0 || mClock.elapsedRealtime() - earliestTimestamp > maxAge) {
    updateEnergyConsumers(powerMonitorStates);
    updateEnergyMeasurements(powerMonitorStates);
}
```

**技术约束：**
- 普通应用数据最大20秒延迟，系统应用250ms延迟
- 过时数据会触发实时更新
- 至少需要5mA电流监测才纳入统计轨道

### 跨设备分析影响

1. **功耗分析工具精度损失**：不同厂商硬件差异导致跨设备可比性降低
2. **调试工具受限**：开发者无法获取真实的瞬时功耗数据
3. **统计准确性差异**：采样频率影响峰值功耗捕获能力
4. **校准算法不同**：各厂商自研校准逻辑未开源，难于标准化

> **结论**：Android 17 在保障隐私和系统安全的同时，引入了显著的数据精度损失。功耗分析工具在不同OEM设备上的结果存在系统差异，开发者需理解这些底层机制来正确解读数据。
