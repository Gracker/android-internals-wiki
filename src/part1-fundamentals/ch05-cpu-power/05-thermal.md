---
title: "Thermal 管控"
chapter: "5.5"
section: "5.5"
status: "finalized"
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
applicable_versions_note: "已验证范围 Android 7-14；Android 15-17 为待验证"
last_verified: "2026-06-06"
last_verified_against: "PowerManager#getThermalHeadroom + #getThermalHeadroomThresholds docs + SystemHealthManager headroom docs + source.android.com thermal mitigation docs"
confidence: medium
consolidated_from:
  - "src/part1-fundamentals/ch05-cpu-power/12-thermal-management-deep-dive.md"
sources:
  - type: "official"
    path: "developer.android.com/games/optimize/adpf"
  - type: "official"
    path: "source.android.com/docs/core/thermal"
  - type: "official"
    path: "developer.android.com/reference/android/os/PowerManager"
tags: ["thermal", "power", "adpf", "perfetto", "cpu"]
related_chapters: ["5.1", "5.2", "5.3", "5.4", "5.6", "5.9", "7.3"]
drafted_date: "2026-04-01"
drafted_by: "openclaw-task2"
polish_count: 2
polish_date: "2026-04-08"
polish_by: "task2b-polish"
reviewed_date: 2026-06-23
reviewed_by: "openclaw-task6"
task6_state: reviewed
task6_result: pass-light-edit
task6_reviewed_date: 2026-06-23
last_task6_at: 2026-06-23T08:15:43+08:00
last_task6_audit: "2026-07-17"
last_task6_audit_log: "logs/review/2026-07-17-16-audit.md"
last_task6_review_log: "logs/review/2026-06-23-08-review.md"
task6_review_notes: "2026-06-23 Task6 复审(Task9 auto-fix 后回归):pass-light-edit。无禁用词/高频词命中。不是X而是Y 句式在限制内。无物理动作动词命中。L1/L2 全部通过,无 B 类问题。queue.json 无 pending。task9_result 为 auto-fixed(非 pass-tech-review),不可自动晋升,送回 Task9 确认。"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: 2026-06-23
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-23T08:34:43+08:00"
last_task9_review_log: "logs/deep-review/2026-06-23-08-deep-review.md"
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
repaired_date: "2026-04-24"
repaired_by: "openclaw-task2b"
last_task2b_at: '2026-05-08T05:42:56+08:00'
review_notes: "2026-05-02 task9 deep-review: needs-rework。本轮 P0 1，P1 1，P2 1；问题已写入 queue/suggestions/research-gaps。；2026-05-04 task6 re-review (revisiting→reviewed): pass-light-edit。无新增L1/L2问题。 | 2026-05-05 Task9 21:00：needs-rework。复核旧 P1：16KB/MMU 功耗→延迟 thermal throttling 仍缺设备/SoC/trace 数据证据；getThermalHeadroom >1.0 边界已有 suggestions，不新增 queue。 | 2026-05-08 Task6 05:05：发现 AIW 16KB thermal 残留确定性断言与已降级研究假设口径冲突，已标注并写入 Task2B queue；同步完成 L1/L2 小修。 | 2026-05-08 Task9 05:27：needs-rework。P0 1 / P1 1；AIW 16KB thermal 残留段仍包含不存在的 `thermal_monitor_notify()` / `update_libcache_stats()` 与无证据 Android 16/17 thermal 预测断言，已合并 queue。 | 2026-05-08 Task6 06:05：回炉复审通过。L1/L2 无新增问题，16KB thermal 段已保持研究假设口径；切回 Task9 复审。 | 2026-05-08 Task9 06:20：pass-tech-review。P0/P1 0，P2 1，P3 1；自动晋升 finalized。 | 2026-05-26 Task6 06:09：闲时抽检。L1 小修 2 处：删去冗余强调词，改写否定纠正式句式；frontmatter 完整，锚点覆盖完整。 | 2026-06-06 Task9 闲时抽检：auto-fixed。P1 1；补齐 Android 15/API 35 `PowerManager#getThermalHeadroomThresholds()` 版本差异，更新 Thermal API 与版本演进表，回到 Task6 复审。 | 2026-06-06 Task6 08:07：revisiting→reviewed。pass-light-edit。L1 小修 2 处：'需要注意几点'→'这个 API 有几条使用边界'，'下面按层拆解'→'逐层来看'。无 L3/L4 大问题。送回 Task9 确认 auto-fix。 | 2026-06-23 Task9 闲时抽检：auto-fixed。P0 1；补齐 Android 17 `ThermalManagerService` 源码路径迁移说明，回到 Task6 复审。"
task9_review_notes: "2026-05-08 Task9 05:27：needs-rework。P0 1 / P1 1；AIW 16KB thermal 残留段仍包含不存在的 `thermal_monitor_notify()` / `update_libcache_stats()` 与无证据 Android 16/17 thermal 预测断言，已合并 queue。 | 2026-05-08 Task9 06:20：pass-tech-review。P0/P1 0，P2 1，P3 1；自动晋升 finalized。 | 2026-06-06 Task9 闲时抽检：auto-fixed。P1 1；补齐 Android 15/API 35 `PowerManager#getThermalHeadroomThresholds()` 版本差异，更新 Thermal API 与版本演进表，回到 Task6 复审。 | 2026-06-06 10:21 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-23 Task9 闲时抽检：auto-fixed。P0 1；补齐 Android 17 `ThermalManagerService` 源码路径迁移说明，回到 Task6 复审。 | 2026-06-23 08:34 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Android 17 ThermalManagerService 路径迁移已按 android-17.0.0_r1 复核，Task6 已通过且 queue 无 pending，自动晋升 finalized。"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-23
last_task9_autofix_at: "2026-06-23"
last_task9_audit: "2026-06-23"
last_task9_audit_log: "logs/deep-review/2026-06-23-04-audit.md"
finalized_date: "2026-06-23"
finalized_by: "openclaw-task9-auto-promote"
---
# 5.5 Thermal 管控

> [!NOTE] 源码锚点
> 平台实现以 AOSP `android-17.0.0_r1`（Android 17 / API 37）为准，内核机制以 `android17-6.18-2026-06_r6` 为准。温度阈值、传感器布局、降载幅度和恢复曲线属于设备配置，不能从 AOSP 推导出某款手机的具体行为。

## 温控改变的是可持续性能

CPU、GPU、显示、充电和无线子系统消耗的电能最终会有一部分转化为热。散热速度赶不上产热速度时，设备只能减少功率或关闭部分功能，以满足芯片、电池和用户接触面的安全约束。

这会形成常见的性能曲线：冷机阶段性能较高，温度上升后可用 CPU/GPU 容量逐步缩小，帧时间或任务时长随之增加。这里有两个容易混淆的目标：

- **峰值性能**关注短时间能跑多快。
- **可持续性能**关注达到热平衡后还能保持多少吞吐。

一次持续负载测试只报告开头几分钟，通常不能代表用户长时间使用时的性能。反过来，看到频率降低也不能立即归因于温控；正常 DVFS、任务等待、电池电流限制和固件策略都可能产生相似曲线。

## 从传感器到降载：两条相互关联的路径

手机温控常被画成“传感器 → HAL → Framework → 限频”的单链路。这个图便于入门，却会误导源码排查。Android 设备通常同时存在控制平面与报告平面。

### 控制平面：直接约束发热源

控制平面可以位于硬件、固件、Linux thermal core 或 vendor 进程中：

```text
温度/电流传感器
    → 硬件或固件保护
    → thermal zone / vendor thermal policy
    → cooling device、频率上限、功率预算、充电或功能限制
```

这条路径的目标是及时降温。它不必等待 `ThermalManagerService` 再执行限频。量产设备可以组合多种机制，AOSP 也不规定厂商必须使用某个名为 `thermal-engine` 的守护进程或某个配置文件路径。

### 报告平面：把状态交给 Framework 与应用

报告平面把设备状态转换成 Android 定义的类型和严重程度：

```text
传感器与设备温控策略
    → Thermal HAL
    → ThermalManagerService
    → 系统监听者与 PowerManager API
    → 应用按状态主动减载
```

报告平面让 Framework 和应用知道设备正在接近或已经进入 throttling。它不包含厂商控制算法的全部细节，也不保证一次 severity 变化对应某个固定频率上限。

## Linux thermal core

### Thermal zone、trip 与 cooling device

Linux thermal core 位于 `drivers/thermal/`。三个基本对象分别负责不同职责：

| 对象 | 含义 |
| --- | --- |
| thermal zone | 一个可观测的热区域或传感器模型 |
| trip point | 该 zone 的温度条件及类型 |
| cooling device | 可以提供若干 cooling state 的执行对象 |

Cooling device 的 state 是抽象等级。对于 cpufreq cooling，更高 cooling state 通常映射到更低的最大频率；其他 cooling device 可以控制 devfreq、风扇或平台自定义资源。state 编号不等于温度，也不保证与 Android `ThrottlingSeverity` 一一对应。

`/sys/class/thermal/thermal_zone*/` 可以在允许访问的设备上提供 `type`、`temp`、trip 等信息。内核 thermal sysfs 约定的温度通常使用毫摄氏度，但节点是否存在、是否允许 adb shell 读取、zone 名称如何解释，都由内核配置与 SELinux 策略决定。分析时先把 `type` 和 `temp` 配对，不能按目录编号猜测 CPU、GPU 或电池。

### thermal governor 决定怎样调整 cooling state

内核 6.18 提供 `step_wise`、`power_allocator`、`fair_share`、`bang_bang` 和 `user_space` 等 governor。设备采用哪一个，应读取 zone 的 `policy` 或检查设备内核配置，不能假定 Android 默认使用 `step_wise`。

以精确 tag 中的 `drivers/thermal/gov_step_wise.c` 为例：

- 温度达到 trip threshold 后，算法结合升温或降温趋势计算目标 state；
- 升温且需要 throttle 时，目标通常增加一级；
- 降温时，目标可以逐级减少，并受 thermal instance 的上下界约束；
- `HOT` 和 `CRITICAL` trip 不走这段普通 cooling-state 管理逻辑。

这解释了某些设备上逐级降低上限的曲线，但 Perfetto 里出现阶梯频率仍不足以证明正在运行 `step_wise`。OPP 本身是离散的，schedutil 与固件也会生成阶梯变化。

### 限频只是 cooling action 的一种

`drivers/thermal/cpufreq_cooling.c` 将 cooling state 映射为 CPUFreq policy 的限制。设备还可以使用 GPU/devfreq 限制、CPU hotplug 或 isolation、调低显示功耗、限制充电和无线功能等动作。

“限核”不是所有 Android 设备在某个 severity 上必然执行的步骤。CPUFreq、hotplug、固件功率预算和 vendor 策略可能独立工作；它们的先后顺序也没有跨设备保证。

## Android 17 Thermal HAL

Android 17 的稳定 AIDL 接口位于 `hardware/interfaces/thermal/aidl/android/hardware/thermal/`。关键类型包括：

- `Temperature`：类型、名称、当前读数和 `throttlingStatus`；
- `TemperatureThreshold`：各 severity 的热/冷阈值，缺失项用 `NaN`；
- `CoolingDevice`：冷却设备类型、名称和当前值；
- `ThrottlingSeverity`：`NONE` 到 `SHUTDOWN` 七个等级。

`IThermal` 支持读取温度、阈值和 cooling device，也支持注册温度状态变化回调。它还定义了可选的 SKIN 温度预测接口 `forecastSkinTemperature()`。

AIDL 注释给出了一个重要边界：`getTemperatureThresholds()` 返回的是静态参考值，设备的 mitigation 算法可能包含动态模型、迟滞和多传感器关系，因此不能用静态阈值自行重建准确的 throttling 状态。应以 `Temperature.throttlingStatus` 或 HAL 回调为准。

Android 17 的 `ThermalManagerService` 位于：

```text
frameworks/base/services/core/java/com/android/server/power/thermal/
    ThermalManagerService.java
```

服务启动时优先连接 AIDL Thermal HAL，失败后仍保留 HIDL 2.0、1.1 和 1.0 的兼容回退。兼容路径说明旧 HAL 仍可能出现在升级设备上；新设备应以其 VINTF 与 HAL 声明为准。

### ThermalManagerService 做什么

源码中的主要职责包括：

1. 缓存 HAL 上报的 `Temperature`。
2. 把传感器状态变化发给内部 thermal event listener。
3. 维护面向公开 API 的整体 thermal status。
4. 为 thermal headroom 收集 SKIN 温度和阈值。
5. 对 CPU、GPU、NPU、SKIN 或 BATTERY 的 `SHUTDOWN` 状态发起相应关机流程。

Android 17 的整体 status 由 SKIN 类型传感器的最高 severity 计算。`PowerManager.getCurrentThermalStatus()` 表达的是面向用户体验的设备热状态，不是“所有芯片传感器中的最高温度”或“CPU 正在被限到几 GHz”。

### Framework 聚合状态与后台任务限制是两条消费路径

`ThermalManagerService` 把 HAL 的温度回调聚合成公开 thermal status 与 headroom；其他系统服务可以独立消费 thermal 状态。Android 17 的 JobScheduler 会在设备 thermal 压力上升时减少可运行后台工作，但具体 job 是否停止还取决于其优先级、当前执行阶段与其他约束。应用看到 job 因 thermal reason 挂起，只能说明调度政策在降载，不能据此推断某个 thermal zone、cooling device 或 CPU 频点。

排查时应把两条证据链分开：一条是 HAL temperature/status → framework status/headroom；另一条是 cooling device、CPU/GPU cap、JobScheduler 等消费者的实际动作。只有时间对齐后，才能说明某次性能下降由哪项 mitigation 造成。

## PowerManager Thermal API

### 当前状态与回调

公开状态从 `NONE` 到 `SHUTDOWN`，数值与 HAL severity 对齐：

| 状态 | 平台语义 |
| --- | --- |
| `NONE` | 未处于 thermal throttling |
| `LIGHT` | 轻度限制，用户体验预期不受影响 |
| `MODERATE` | 中度限制，用户体验预期不会受到很大影响 |
| `SEVERE` | 严重限制，用户体验会受到明显影响 |
| `CRITICAL` | 平台已采用其可用的主要降功率措施 |
| `EMERGENCY` | 关键组件开始关闭，设备功能受限 |
| `SHUTDOWN` | 需要立即关机 |

状态描述是级别语义，不是固定动作表。例如，`SEVERE` 不承诺一定关闭大核，`EMERGENCY` 也不承诺每台设备关闭同一组无线组件。

下面的代码用于监听状态并在组件停止时注销监听：

```java
private final PowerManager.OnThermalStatusChangedListener thermalListener =
        status -> adaptWorkload(status);

@Override
protected void onStart() {
    super.onStart();
    PowerManager pm = getSystemService(PowerManager.class);
    pm.addThermalStatusListener(getMainExecutor(), thermalListener);
}

@Override
protected void onStop() {
    getSystemService(PowerManager.class)
            .removeThermalStatusListener(thermalListener);
    super.onStop();
}
```

`adaptWorkload()` 应根据业务选择可逆的降载动作，例如降低内部渲染分辨率、减少特效、降低编码复杂度或延后非关键工作。回调经 Binder 和指定 `Executor` 分发，平台没有承诺“几百毫秒以内”等固定延迟。

### Thermal headroom

`getThermalHeadroom(forecastSeconds)` 返回非负浮点数，用来表示慢变化传感器距离 `SEVERE` 阈值的相对位置：

- `1.0` 对应 `SEVERE` 阈值；
- 数值可以大于 `1.0`，但 `1.0` 以上没有固定 severity 映射；
- `0.0` 不对应固定温度或 `NONE`；
- 不支持、调用过密等情况下可能返回 `NaN`；
- `forecastSeconds` 的公开参数范围是 0—60 秒。

该 API 主要跟踪 SKIN 一类慢变化传感器。源码文档建议不必高于约每秒一次；系统积累足够样本前，即使请求未来预测，也可能只返回当前 headroom。

下面的代码演示如何守住 `NaN` 和阈值边界：

```java
float forecast = powerManager.getThermalHeadroom(10);
if (!Float.isNaN(forecast)) {
    if (forecast >= 1.0f) {
        reduceWorkloadImmediately();
    } else if (forecast >= 0.8f) {
        prepareAReversibleQualityStep();
    }
}
```

`0.8f` 是应用自己的策略示例，不是 Android 定义的系统阈值。产品应根据帧时间、业务质量和设备实验调整，并使用迟滞避免画质在临界值附近反复切换。

### Headroom thresholds

支持该 API surface 时，`getThermalHeadroomThresholds()` 返回 thermal status 到 headroom 阈值的映射。只有厂商定义了相应阈值的状态才会出现在结果中。Android 17 源码还说明：

- 旧设备存在多个 SKIN 传感器时，Framework 会采用较保守的阈值；
- 当前 headroom 越过某阈值，不保证当前 status 已同步达到该等级；
- 阈值在 Android 17 上可以随调用变化；
- 功能未启用会抛出 `UnsupportedOperationException`，服务未就绪会抛出 `IllegalStateException`。

因此，status 适合响应已经发生的状态变化；forecast headroom 与 thresholds 适合提前准备降载。二者要分开记录。

## CPU/GPU headroom 与 thermal headroom 的区别

Android 16（API 36）增加了公开的 CPU/GPU headroom API；Android 17 源码中的实现位于 `android.os.health.SystemHealthManager`，支持情况仍由设备能力决定：

- `getCpuHeadroom(CpuHeadroomParams)` 估算可继续提供的 CPU 容量；
- `getGpuHeadroom(GpuHeadroomParams)` 估算可继续提供的 GPU 容量；
- 有效值范围为 0—100，越低表示可增加的容量越少；
- 暂时无法计算时可以返回 `Float.NaN`；
- 不支持时抛出 `UnsupportedOperationException`；
- 这是同步 Binder 调用，源码提示可能超过 1 毫秒，不应放在关键线程。

查询频率应遵守 `getCpuHeadroomMinIntervalMillis()` 和 `getGpuHeadroomMinIntervalMillis()`。这两个指标可用于判断工作是否接近 CPU/GPU 容量边界，但容量不足不一定由温度造成；thermal headroom 也不能指出瓶颈位于 CPU 还是 GPU。

## 温控怎样影响性能

### 频率、容量与并行度都会变化

温控可能降低 CPUFreq policy 上限、GPU 性能级别、内存带宽或可用 CPU 数，也可能把功率预算转移给另一个域。对应用可观察到的结果包括：

- 同一 CPU 工作量执行时间增长；
- GPU queue 或 fence 完成变慢；
- 主线程或 RenderThread 更容易错过帧 deadline；
- 编码、推理和编译吞吐随时间下降；
- 系统为了降低显示功耗而改变亮度或刷新相关策略。

热限制常有迟滞：达到阈值后开始降载，温度回落到更低位置才逐步恢复。测试要同时观察进入与恢复过程，不能只记录一次最高温度。

### 高负载加低频仍不是充分证据

下列组合能提高 thermal throttling 的可信度：

1. 关键工作在目标 CPU/GPU 上持续繁忙。
2. thermal status、SKIN headroom、thermal zone 或 cooling state 同期变化。
3. policy 频率上限降低、capacity 下降，或者设备功率约束增强。
4. 请求频率受上限压制，任务时长或帧时间随之恶化。
5. 冷却并恢复策略后，同一负载的限制解除。

若只有“CPU utilization 高、频率低”，还应排查共享 policy、功率限制、任务迁移、调频驱动和频率数据语义。

## 用 Perfetto 建立证据链

### 建议采集的数据

Perfetto 的 `linux.sys_stats` 数据源支持轮询 thermal zone 和 cpufreq sysfs。下面的片段用于一秒采样一次：

```protobuf
data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      thermal_period_ms: 1000
      cpufreq_period_ms: 1000
    }
  }
}
```

这适合观察分钟级热趋势。采样周期会影响时间精度，节点访问失败时也可能缺轨。

内核 6.18 定义了 `thermal/thermal_temperature`、`thermal/thermal_zone_trip` 和 `power/cpu_frequency` 等 ftrace 事件。下面的配置用于观察事件发生顺序：

```protobuf
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "thermal/thermal_temperature"
      ftrace_events: "thermal/thermal_zone_trip"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "sched/sched_switch"
      atrace_categories: "power"
    }
  }
}
```

设备内核可能关闭某个 tracepoint，vendor 也可能提供自己的 cooling、thermal pressure 或功率轨迹。采集后先确认轨迹确有数据，再做结论。

### 阅读顺序

1. 用 Frame Timeline、业务 slice 或任务完成时间标记性能退化点。
2. 检查 `ThermalManagerService.status`、thermal zone 温度与 trip 事件。
3. 检查 cooling state、CPUFreq policy 上限、CPU capacity/thermal pressure 和 GPU 限制轨迹。
4. 对齐目标线程的 running/runnable 时间及 CPU frequency。
5. 把进入 throttling、稳态和冷却恢复三个阶段分开统计。

`power/cpu_frequency` 或轮询到的 `scaling_cur_freq` 可能接近 CPUFreq 请求状态，不能自动视为片上计数器测得的物理实频。第 5.4 节已经说明这一数据边界。

## Thermal mitigation 的常见手段

| 手段 | 直接效果 | 应用侧可能看到的现象 |
| --- | --- | --- |
| CPU/GPU 限频或功率上限 | 降低计算域功率 | CPU/GPU 工作时长增加 |
| CPU hotplug/isolation | 减少可用并行度或高功耗核心 | runnable 等待、吞吐下降 |
| 降低显示亮度或刷新策略 | 降低显示与合成相关功率 | 亮度受限、帧率目标改变 |
| 限制充电 | 减少电池与充电 IC 发热 | 充电速度下降或暂停 |
| 限制相机、无线或其他功能 | 降低对应子系统功率 | 功能降级或暂时不可用 |
| 应用主动降载 | 提前减少产热 | 质量下降较平滑，避免被动超时 |

表中是可选动作集合，不是 severity 到动作的标准映射。具体设备要结合 Thermal HAL 状态、vendor 配置、系统日志和实机 Trace 确认。

### 应用如何主动降载

降载动作应满足三点：

- **可逆**：温度回落后能够逐步恢复；
- **有迟滞**：进入和退出使用不同阈值，避免频繁切换；
- **按瓶颈选择**：GPU 受限时优先减像素和特效，CPU 受限时减少模拟、脚本或编码复杂度。

可以按阶段设计：

- `LIGHT`：停止预取、遥测加工和非关键后台任务。
- `MODERATE`：降低渲染分辨率、特效、相机处理或编码档位。
- `SEVERE` 及以上：降低帧率目标，暂停高成本功能，保住交互和数据安全。

这些是应用策略示例。每个等级的动作要由产品质量要求和实测结果决定，不能把示例当作平台规范。

## Sustained 与 Fixed Performance Mode

### Sustained Performance Mode

Android 7.0（API 24）提供 Sustained Performance Mode。应用先用 `PowerManager.isSustainedPerformanceModeSupported()` 检查设备支持，再通过 `Window.setSustainedPerformanceMode(true)` 请求适合长时工作的性能策略。

下面的代码用于受支持设备上的长负载窗口：

```java
PowerManager pm = getSystemService(PowerManager.class);
if (pm.isSustainedPerformanceModeSupported()) {
    getWindow().setSustainedPerformanceMode(true);
}
```

Android 17 Power HAL AIDL 中仍有 `Mode.SUSTAINED_PERFORMANCE`。vendor 可以通过 CPU、GPU 或其他资源策略提供较稳定的长期性能，平台接口不规定固定频率，也不承诺某个 30 分钟波动百分比。此模式不会关闭 thermal protection；设备继续升温时仍可进一步降载。

### Fixed Performance Mode

`adb shell cmd power set-fixed-performance-mode-enabled true` 是面向测试的系统命令。它用于减少动态性能变化，方便在同一设备上比较实现差异。设备不支持时命令可能失败；thermal、功率和安全限制仍然有效，所以“fixed”不代表观测频率绝对不变。

实验结束后要恢复：

```bash
adb shell cmd power set-fixed-performance-mode-enabled false
```

公开应用不要把这个命令当成产品能力，也不要把 Fixed Performance Mode 与 ADPF hint session 混为同一接口。

## 如何控制性能测试中的热变量

### 先定义测试目标

- 测峰值：规定统一的起始温度和短测试窗口。
- 测持续性能：运行到热稳态，报告稳定阶段的吞吐与波动。
- 测真实体验：保留产品外壳、默认 thermal、亮度、网络和充电状态。

三种数据回答的问题不同，应分别命名，不能混在一张排行榜里。

### 记录环境与设备状态

每轮至少记录：

- 机型、系统构建、内核、应用版本；
- 环境温度、外壳和散热附件；
- 电量、是否充电、充电功率；
- 亮度、刷新率、网络和无线状态；
- `getCurrentThermalStatus()`、headroom、关键 thermal zone；
- CPU/GPU policy 上限以及测试开始/结束时间。

静置时间和“允许开始”的温度应来自该设备的预实验。固定写成 5—10 分钟或环境温度 ±2°C，可能对不同机身和传感器都不合适。

### 使用可复现的实验顺序

1. 预热应用与数据，排除首次编译、缓存和网络差异。
2. 等待设备回到预先定义的起始条件。
3. 随机或交错执行 A/B，避免方案 A 总在冷机、方案 B 总在热机。
4. 重复多轮，分别报告中位数、离散程度和 thermal 状态。
5. 持续性能测试要覆盖进入 throttling 和热稳态。
6. 物理风冷只用于明确标记的实验条件；它改变了产品散热边界。

不要关闭 thermal protection，也不要放宽 critical/shutdown 阈值。那会改变安全条件，并让测试结果失去产品意义。

## 厂商差异与散热硬件

AOSP 统一了 Thermal HAL 与应用 API，没有统一以下内容：

- 传感器的位置和热模型；
- SKIN 与内部热点之间的估算方式；
- trip、迟滞和控制周期；
- CPU/GPU/DDR/显示/充电之间的功率预算；
- severity 到 mitigation 动作的映射；
- VC、石墨片、机身结构和外接散热器的效果。

VC、热管和石墨材料主要改变热扩散与热容量，最终效果还受接触热阻、面积、机身材料和环境对流影响。只给出材料名称或面积，无法推导持续帧率；“导热效率是铜的固定倍数”也不适合跨产品比较。

跨设备测试时，应把硬件散热和厂商策略视为被测系统的一部分。即使两台设备使用同一 SoC，也不能仅凭 SoC 型号解释持续性能差异。

## 常见误区

### “手机发热就表示应用有 bug”

高负载必然产热。可疑信号是超出业务需要的持续工作，例如忙循环、异常重试、频繁唤醒、无效 GPU overdraw 或后台定位。用 Trace 和功耗数据定位多余工作，再判断能否优化。

### “Root 后关闭温控可以保持峰值性能”

硬件、固件和内核可能有多层保护，关闭其中一层也不保证保持峰值。绕过 thermal protection 还会带来安全和寿命风险，也不能代表量产体验。

### “Thermal status 为 NONE 就没有热限制”

公开 status 以 SKIN severity 为主。芯片、充电或电源预算可能已经限制某个性能域，而整体 status 仍为 `NONE`。排障要结合域级频率、容量、温度和 vendor 数据。

### “Sustained Performance Mode 会固定频率”

它表达长期稳定性能需求，vendor 决定资源策略。Fixed Performance Mode 也仍受 thermal 和安全上限约束。两者都不能替代温控证据采集。

## 版本边界与源码索引

| Android 版本 | 关键变化 | 分析方式 |
| --- | --- | --- |
| Android 7 / API 24 | Sustained Performance Mode | 设备声明支持后使用 |
| Android 10 / API 29 | Thermal HAL 2.0 与公开 thermal status API | 状态监听成为应用减载入口 |
| Android 11 / API 30 | `getThermalHeadroom()` | 0—60 秒 SKIN 趋势预测 |
| Android 14 / API 34 | stable AIDL Thermal HAL | Android 17 优先连接的 HAL |
| Android 15 / API 35 | thermal headroom thresholds API 进入平台 API 线 | 运行时处理缺失阈值与不支持 |
| Android 16 / API 36 | CPU/GPU headroom 与 thermal headroom callback | 先检查设备支持，再避开关键线程调用 |
| Android 17 / API 37 | `ThermalManagerService` 位于 `server/power/thermal/` | 以 `android-17.0.0_r1` 源码为锚点 |

| 层次 | 精确源码 |
| --- | --- |
| Framework | `frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java` |
| App API | `frameworks/base/core/java/android/os/PowerManager.java`、`android/os/health/SystemHealthManager.java` |
| Thermal HAL | `hardware/interfaces/thermal/aidl/android/hardware/thermal/` |
| Kernel | `drivers/thermal/`、`Documentation/driver-api/thermal/sysfs-api.rst` |
| Perfetto | `SysStatsConfig.thermal_period_ms`、`SysStatsConfig.cpufreq_period_ms` |

## 参考资料

- AOSP `android-17.0.0_r1`：`PowerManager.java`、`SystemHealthManager.java`
- AOSP `android-17.0.0_r1`：`services/core/java/com/android/server/power/thermal/ThermalManagerService.java`
- AOSP `android-17.0.0_r1`：`hardware/interfaces/thermal/aidl/android/hardware/thermal/IThermal.aidl`、`Temperature.aidl`、`TemperatureThreshold.aidl`、`ThrottlingSeverity.aidl`
- Linux kernel `android17-6.18-2026-06_r6`：`drivers/thermal/gov_step_wise.c`、`drivers/thermal/cpufreq_cooling.c`
- Linux kernel：`Documentation/driver-api/thermal/sysfs-api.rst`
- Perfetto `android-17.0.0_r1`：`protos/perfetto/config/sys_stats/sys_stats_config.proto`
- [Android Thermal mitigation](https://source.android.com/docs/core/thermal)
- [PowerManager Thermal API](https://developer.android.com/reference/android/os/PowerManager)
- [Optimize games for thermal conditions](https://developer.android.com/games/optimize/thermal)
